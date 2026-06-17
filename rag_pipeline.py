# rag_pipeline.py
# Central orchestrator for all conversation responses.
#
# v2 Architecture:
#   Every user message flows through:
#     1. message_router  → classifies intent, returns action
#     2. Based on action:
#        HUMAN_HANDOFF    → human_handoff.get_handoff_response()
#        ANSWER_AND_RESUME → qa_handler + optional resume question
#        OBJECTION         → call_llm with objection prompt (+ re-ask if mid-flow)
#        CONTINUE_FLOW     → existing state machine logic (unchanged)
#     3. lead_scoring.save_lead_score() after every response
#
# The booking state machine (GREETING → ASK_DATE → ASK_PEOPLE → ASK_ELDERLY
# → ASK_QUALIFICATION → SERVICE_INTRO → NORMAL_CHAT) is fully preserved.
# State only advances when action == CONTINUE_FLOW.

from booking_flow import (
    get_booking,
    update_booking,
    set_state,
    get_state,
    increment_message_count,
)

from sales_logic import detect_user_intent
from prompt_builder import build_prompt, get_sales_instruction
from message_router import route_message
from qa_handler import handle_information_request
from human_handoff import get_handoff_response
from lead_scoring import save_lead_score

from langchain_groq import ChatGroq
from config import GROQ_API_KEY

import re
import time
from difflib import get_close_matches
from pymongo import MongoClient
import os

from customer_profile import (
    upsert_customer_profile,
    get_customer_profile,
    compute_lead_stage,
    get_missing_fields,
    update_current_intent,
    INTENT_MAIN_BOOKING,
    INTENT_PUJA_BOOKING,
    INTENT_ABHISHEKAM_BOOKING,
    INTENT_PRASADAM_BOOKING,
    INTENT_CHADHAVA_BOOKING,
    INTENT_DARSHAN_BOOKING,
    INTENT_ACCOMMODATION_BOOKING,
    INTENT_TRANSPORTATION_BOOKING,
)

import razorpay_handler


# --------------------------------------------------
# LLM INIT — main response model
# --------------------------------------------------

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.7,
    max_tokens=800,
    api_key=GROQ_API_KEY
)


# --------------------------------------------------
# SMART EXTRACTION — auto-hydrate booking session
# from every customer message before routing.
# This is the core of "don't re-ask what you already know".
# --------------------------------------------------

# Known puja names for extraction
_PUJA_NAMES = [
    "rudrabhishek", "abhishek", "satyanarayan puja", "satyanarayan katha",
    "griha pravesh", "navchandi path", "sunderkand path", "sunderkand",
    "hanuman puja", "lakshmi puja", "ganesh puja", "durga puja",
    "kali puja", "navratri puja", "havan", "yagya", "yajna",
    "pitru tarpan", "mahamrityunjay", "mahamrityunjaya", "navagraha puja",
    "saraswati puja", "vishnu puja", "shiva puja", "ram puja",
]

# Package type keywords
_PACKAGE_KEYWORDS = {
    "darshan":  ["assisted darshan", "vip darshan", "darshan package", "darshan booking", "sugam pass", "darshan"],
    "yatra":    ["yatra package", "char dham", "do dham", "yatra tour", "pilgrimage package",
                 "full trip", "travel package", "complete tour", "group tour", "yatra"],
    "prasadam": ["prasad", "prasadam", "prasad delivery", "send prasad"],
    "puja":     ["online puja", "puja booking", "book puja", "puja service", "puja", "pooja", "pooja booking", "book pooja"],
    "chadhava": ["chadhava", "chadawa", "offering", "bhog", "online offering"],
    "astrology": ["astrology", "horoscope", "kundli", "astrologer", "jyotish"],
}

def detect_package_type_from_text(text: str) -> str:
    text_low = text.lower()
    
    # Strict keyword check
    # 1. Astrology
    astro_kws = ["astrology", "horoscope", "kundli", "astrologer", "jyotish", "future", "predict", "chart"]
    if any(kw in text_low for kw in astro_kws):
        return "astrology"
        
    # 2. Puja
    puja_kws = ["puja", "pooja", "abhishek", "abhishekam", "ritual", "havan", "yagya", "yajna", "path", "paath"]
    # Check if any specific puja name is in text
    for puja in _PUJA_NAMES:
        if puja in text_low:
            return "puja"
    if any(kw in text_low for kw in puja_kws):
        return "puja"
        
    # 3. Chadhava
    chadhava_kws = ["chadhava", "chadawa", "offering", "bhog"]
    if any(kw in text_low for kw in chadhava_kws):
        return "chadhava"
        
    # 4. Prasadam
    prasad_kws = ["prasad", "prasadam", "delivery"]
    if any(kw in text_low for kw in prasad_kws):
        return "prasadam"
        
    # 5. Yatra
    yatra_kws = ["yatra", "tour", "package", "char dham", "do dham", "pilgrimage"]
    if any(kw in text_low for kw in yatra_kws):
        return "yatra"
        
    # 6. Darshan
    darshan_kws = ["darshan", "visit", "temple", "mandir", "pass", "vip", "entry", "queue"]
    if any(kw in text_low for kw in darshan_kws):
        return "darshan"
        
    return None

def is_valid_preferred_time(val: str) -> bool:
    if not val:
        return False
    val_low = val.lower().strip()
    # General keywords
    time_keywords = {"morning", "afternoon", "evening", "night", "noon", "anytime", "any time", "am", "pm"}
    if any(kw in val_low for kw in time_keywords):
        return True
    # Check if it contains digits (like clock time)
    if any(c.isdigit() for c in val_low):
        # Make sure it's not a date (e.g. "10th", "2026")
        if "aug" in val_low or "202" in val_low or "date" in val_low:
            return False
        return True
    return False



_EXTRACTION_PROMPT = """You are a details extraction assistant for a temple assisted darshan booking chatbot.
Analyze the conversation history and the latest user message to extract booking details.

CURRENT BOOKING DATA (already saved — only extract NEW or CHANGED values):
Temple: {temple}
Date: {date}
People: {people}
Elderly: {elderly}
Name: {customer_name}
Phone: {phone}
Budget: {budget}
Puja: {puja}
Package Type: {package_type}
Qualification: {qualification}
Adults Count: {adults_count}
Children Count: {children_count}
Senior Count: {senior_count}
Preferred Time: {preferred_time}
Quantity: {quantity}
Delivery Address: {delivery_address}
Offering Type: {offering_type}
Darshan Type: {darshan_type}
Departure City: {departure_city}

CONVERSATION HISTORY:
{history}

LATEST USER MESSAGE:
"{query}"

CONTEXT-AWARE EXTRACTION RULES (read carefully before extracting):
1. Look at the LAST ASSISTANT MESSAGE in the conversation history. If the assistant asked for a specific field and the user's reply answers that question, extract the answer into THAT field — even if the value looks ambiguous.
   - If the assistant asked "What is your departure city?" and user says "Gujarat" → extract departure_city = "Gujarat"
   - If the assistant asked "Which temple?" and user says "Tirupati" → extract temple = "Tirupati Balaji Temple"
   - If the assistant asked "How many people?" and user says "5" → extract people = 5

2. TEMPLE EXTRACTION — STRICT RULES (CRITICAL):
   - Only extract "temple" if the user explicitly names a SPECIFIC TEMPLE (e.g., "Tirupati", "Kedarnath", "Kashi Vishwanath", "Mahakaleshwar", "Vaishno Devi", "Shirdi").
   - Indian STATES (Gujarat, Tamil Nadu, Rajasthan, Maharashtra, UP, Uttarakhand, J&K, etc.) are NOT temples. NEVER extract a state name as temple.
   - Indian CITIES (Mumbai, Delhi, Ahmedabad, Surat, Chennai, Hyderabad, etc.) are NOT temples. They are departure cities.
   - If a user mentions a state/region (e.g., "Gujarat", "Tamil Nadu") WITHOUT a specific temple name, do NOT extract it as temple. Extract it as departure_city if the context suggests they are answering a departure city question.
   - NEVER invent, assume, or guess a temple name from vague inputs, dates, group sizes, or questions containing the word "temple".
   - If the user's message does not explicitly name a temple, leave the "temple" field null.
   - If the user's message contains ONLY a date/time, ONLY extract "date". Do not infer or hallucinate any other fields.

3. DEPARTURE CITY vs TEMPLE disambiguation:
   - departure_city = the city the devotee is TRAVELLING FROM (e.g., "Delhi", "Mumbai", "Gujarat", "Ahmedabad", "Hyderabad", "Pune")
   - temple = the sacred site they want to VISIT (e.g., "Tirupati Balaji", "Kedarnath", "Ram Mandir")
   - A state name (Gujarat, Tamil Nadu, etc.) alone is NEVER a valid temple name.

4. Only return a JSON object with fields that were newly found or changed. Do not return unchanged or empty fields.
5. Return ONLY valid JSON. No explanation. No markdown. No code blocks.

JSON Schema:
{{
  "temple": string or null,          // SPECIFIC temple name ONLY. NEVER a state or city name, and NEVER a value not explicitly named by the user.
  "date": string or null,            // Travel date or month
  "people": integer or null,         // Total number of travelers
  "elderly": boolean or null,        // True if elderly/senior citizens/children are in the group
  "customer_name": string or null,   // Devotee's name
  "phone": string or null,           // WhatsApp phone number (10 digits)
  "budget": string or null,          // Budget
  "puja": string or null,            // Specific Puja name
  "package_type": string or null,    // One of: "darshan", "yatra", "prasadam", "puja", "chadhava", "astrology"
  "qualification": string or null,   // Local or out-of-state traveller
  "adults_count": integer or null,   // Number of adults
  "children_count": integer or null, // Number of children
  "senior_count": integer or null,   // Number of senior citizens
  "preferred_time": string or null,  // Preferred time
  "quantity": integer or null,       // Quantity of prasadam/chadhava items
  "delivery_address": string or null,// Delivery address for prasadam (full address)
  "offering_type": string or null,   // Type of chadhava/offering
  "darshan_type": string or null,    // Type of darshan
  "departure_city": string or null   // City/state the devotee is TRAVELLING FROM
}}
}}"""


def reset_irrelevant_fields(user_id: str, new_pkg_type: str):
    """Resets booking fields that are not relevant to the new package type."""
    from booking_flow import update_booking
    
    # Define relevant fields for each package type
    relevant_map = {
        "astrology": ["customer_name", "phone", "package_type"],
        "prasadam":  ["customer_name", "phone", "package_type", "temple"],
        "chadhava":  ["customer_name", "phone", "package_type", "temple"],
        "puja":      ["customer_name", "phone", "package_type", "temple", "date", "puja"],
        "darshan":   ["customer_name", "phone", "package_type", "temple", "date", "people", "elderly", "qualification", "budget"],
        "yatra":     ["customer_name", "phone", "package_type", "temple", "date", "people", "elderly", "qualification", "budget"]
    }
    
    allowed_fields = relevant_map.get(new_pkg_type, [])
    if not allowed_fields:
        return
        
    all_resettable_fields = {
        "temple": None,
        "temple_location": None,
        "date": None,
        "people": None,
        "elderly": False,
        "qualification": None,
        "budget": None,
        "puja": None,
        "puja_mode": None,
    }
    
    for field, default_val in all_resettable_fields.items():
        if field not in allowed_fields:
            update_booking(user_id, field, default_val)


def _is_temple_name_mentioned(extracted_temple: str, user_message: str) -> bool:
    if not extracted_temple:
        return False
    msg_lower = user_message.lower()
    temp_lower = extracted_temple.lower()
    
    # Check alias keywords first to support variants (e.g. Mahakal/Ujjain -> Mahakaleshwar)
    try:
        for alias_entry in _TEMPLE_ALIASES:
            if alias_entry["entry"]["name"].lower() == temp_lower:
                if any(kw in msg_lower for kw in alias_entry["keywords"]):
                    return True
    except NameError:
        pass
    
    # Stopwords to filter out from temple name to get identifying words
    _TEMPLE_STOPWORDS = {
        "temple", "mandir", "dham", "peeth", "peetham", "shri", "shree", "sri", 
        "lord", "baba", "mata", "devi", "darshan", "yatra", "package",
        "abode", "abodes", "jyotirlinga", "jyotirling", "shiva", "shiv",
        "god", "goddess", "divine", "sacred", "the", "and", "for", "with",
        "at", "of", "in", "deity", "math", "matha", "kshetram"
    }
    
    # Split the extracted temple name into words
    temp_words = re.findall(r"\b\w+\b", temp_lower)
    # Filter out stopwords and very short words
    identifying_words = [
        w for w in temp_words 
        if w not in _TEMPLE_STOPWORDS and len(w) >= 3
    ]
    
    # If no identifying words remain, fall back to checking if any word >= 3 is in the message
    if not identifying_words:
        identifying_words = [w for w in temp_words if len(w) >= 3]
        
    # Check if at least one identifying word is in the user's message
    return any(w in msg_lower for w in identifying_words)


def _extract_and_hydrate(user_id: str, text: str, history: list = None) -> dict:
    """
    Scan every incoming customer message and extract all available details.
    Silently updates the booking session for any field found.
    Hybrid mode: runs regex checks first, then uses an LLM pass to scan context.
    """
    from booking_flow import get_booking, update_booking
    import json

    booking  = get_booking(user_id)
    text_low = text.lower().strip()
    extracted = {}

    # Check if this is a query asking for the list/types of pujas
    skip_puja_extraction = any(w in text_low for w in [
        "what pujas", "which pujas", "pujas list", "list of pujas",
        "pujas you offer", "pujas available", "available pujas",
        "listed pujas", "pujas on website", "pujas on the website",
        "pujas in naman darshan", "pujas of naman darshan",
        "what poojas", "which poojas", "poojas list", "list of poojas",
        "poojas you offer", "poojas available", "available poojas"
    ])

    # ---- 1. PHONE NUMBER ----
    if not booking.get("phone"):
        phone_match = re.search(r"\b([6-9]\d{9})\b", text)
        if phone_match:
            phone = phone_match.group(1)
            update_booking(user_id, "phone", phone)
            extracted["phone"] = phone

    # ---- 2. CUSTOMER NAME ----
    if not booking.get("customer_name"):
        name_patterns = [
            r"(?:i['\u2019]?m|i am|my name is|this is|naam hai|mera naam)\s+([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)",
        ]
        for pat in name_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                name = m.group(1).strip().title()
                _STOPWORDS = {"Interested", "Planning", "Looking", "Visiting", "Coming",
                              "Here", "Available", "There", "Calling", "Going"}
                if name not in _STOPWORDS and 2 < len(name) < 40:
                    update_booking(user_id, "customer_name", name)
                    extracted["customer_name"] = name
                    break

    # ---- 3. TRAVEL DATE ----
    if not booking.get("date"):
        date_patterns = [
            r"\b(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b",                       # 15/06, 15-06-2026
            r"\b(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*(?:\s+\d{4})?)\b",  # 15 June 2026
            r"\b((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}(?:\s+\d{4})?)\b",  # June 15
            r"\b(next\s+(?:month|week|weekend|saturday|sunday|monday))\b",       # next month
            r"\b(this\s+(?:month|week|weekend|saturday|sunday))\b",              # this weekend
        ]
        for pat in date_patterns:
            m = re.search(pat, text_low, re.IGNORECASE)
            if m:
                date_val = m.group(1).strip()
                update_booking(user_id, "date", date_val)
                extracted["date"] = date_val
                break

    # ---- 4. PEOPLE COUNT ----
    if not booking.get("people"):
        people = extract_people_count(text)
        if people and 1 <= people <= 200:
            update_booking(user_id, "people", people)
            extracted["people"] = people

    # ---- 5. ELDERLY / CHILDREN (upgrade only) ----
    if not booking.get("elderly"):
        if detect_elderly(text_low):
            update_booking(user_id, "elderly", True)
            extracted["elderly"] = True

    # ---- 6. BUDGET ----
    if not booking.get("budget"):
        budget_match = re.search(
            r"\b(?:budget|spend|within|under|upto|up to|around|max|maximum)\s*"
            r"(?:rs\.?|inr|rupees?)?\s*"
            r"(\d[\d,]*(?:\.\d+)?)\s*(?:k|thousand|lakh|lac)?\b|"
            r"\b(?:rs\.?|inr|rupees?)\s*(\d[\d,]*(?:\.\d+)?)\s*(?:k|thousand|lakh|lac)?\b|"
            r"\b(\d[\d,]*)\s*(?:k|thousand|lakh|lac)\b|"
            r"\b([1-9]\d{3,6})\b",
            text_low,
        )
        if budget_match:
            # Extract digits only to check if the matched value is a phone number
            matched_groups = [g for g in budget_match.groups() if g is not None]
            val = matched_groups[0].strip() if matched_groups else budget_match.group(0).strip()
            digits_only = "".join(filter(str.isdigit, val))
            
            if len(digits_only) < 10:
                # Avoid extracting years (2024-2035) as budget
                is_year = False
                if len(digits_only) == 4 and digits_only.startswith("20"):
                    try:
                        year_val = int(digits_only)
                        if 2024 <= year_val <= 2035:
                            is_year = True
                    except ValueError:
                        pass
                
                if not is_year:
                    raw = budget_match.group(0).strip()
                    if raw:
                        update_booking(user_id, "budget", raw)
                        extracted["budget"] = raw

    # ---- 7. PUJA TYPE ----
    if not booking.get("puja") and not skip_puja_extraction:
        for puja in _PUJA_NAMES:
            if puja in text_low:
                update_booking(user_id, "puja", puja.title())
                extracted["puja"] = puja.title()
                break

    # ---- 7b. PREFERRED TIME ----
    if not booking.get("preferred_time"):
        time_patterns = [
            r"\b((?:1[0-2]|0?[1-9])(?::|\.)[0-5]\d\s*(?:am|pm|a\.m\.|p\.m\.)?)\b",  # 11:30 am, 11.30pm
            r"\b((?:1[0-2]|0?[1-9])\s*(?:am|pm|a\.m\.|p\.m\.)\b)",                    # 11 am, 11 pm
            r"\b(morning|afternoon|evening|night|noon|anytime|any\s*time)\b",        # keywords
        ]
        for pat in time_patterns:
            m = re.search(pat, text_low, re.IGNORECASE)
            if m:
                time_val = m.group(1).strip()
                update_booking(user_id, "preferred_time", time_val)
                extracted["preferred_time"] = time_val
                break


    # ---- 8. PACKAGE TYPE ----
    detected_pkg = detect_package_type_from_text(text_low)
    if detected_pkg and booking.get("package_type") != detected_pkg:
        update_booking(user_id, "package_type", detected_pkg)
        extracted["package_type"] = detected_pkg
        reset_irrelevant_fields(user_id, detected_pkg)

    # ---- 8b. PUJA MODE (online / offline) ----
    # Detect whether the user explicitly chose online or offline puja.
    # We scan current message AND history user messages so a prior mention is honoured.
    if (detected_pkg == "puja" or booking.get("package_type") == "puja") and not booking.get("puja_mode"):
        history_text = " ".join(
            t.get("user", "").lower()
            for t in (history or [])
        )
        combined = text_low + " " + history_text

        _ONLINE_SIGNALS  = ["online puja", "online pooja", "virtual puja", "digital puja",
                            "puja online", "pooja online", "online ritual",
                            "online mode", "online service", "online only", "online"]
        _OFFLINE_SIGNALS = ["offline puja", "in-person puja", "physical puja",
                            "at the temple", "temple visit", "visit the temple",
                            "go to temple", "will attend", "will be there", "in person", "offline", "in-person"]

        is_online = any(re.search(r"\b" + re.escape(sig) + r"\b", combined) for sig in _ONLINE_SIGNALS)
        is_offline = any(re.search(r"\b" + re.escape(sig) + r"\b", combined) for sig in _OFFLINE_SIGNALS)

        if is_online:
            update_booking(user_id, "puja_mode", "online")
            extracted["puja_mode"] = "online"
        elif is_offline:
            update_booking(user_id, "puja_mode", "offline")
            extracted["puja_mode"] = "offline"

    # ---- 9. TEMPLE DETECTION ----
    # Raw-text temple detection bypassed to prevent departure cities (e.g. Bangalore)
    # from hijacking empty temple slots as false positives. Temple verification
    # is now handled strictly in the LLM extraction updates loop below.

    # ---- 10. LLM EXTRACTION PASS ----
    try:
        from langchain_groq import ChatGroq
        from config import GROQ_API_KEY

        extractor_llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0.0,
            max_tokens=200,
            api_key=GROQ_API_KEY
        )

        hist_str = ""
        if history:
            # Keep only the last 5 turns for extraction context to prevent token overflow
            for turn in history[-5:]:
                hist_str += f"User: {turn.get('user', '')}\nAssistant: {turn.get('assistant', '')}\n"
        else:
            hist_str = "No previous conversation."

        prompt_str = _EXTRACTION_PROMPT.format(
            temple=booking.get("temple") or "Not specified",
            date=booking.get("date") or "Not specified",
            people=booking.get("people") or "Not specified",
            elderly="Yes" if booking.get("elderly") else "No",
            customer_name=booking.get("customer_name") or "Not specified",
            phone=booking.get("phone") or "Not specified",
            budget=booking.get("budget") or "Not specified",
            puja=booking.get("puja") or "Not specified",
            package_type=booking.get("package_type") or "Not specified",
            qualification=booking.get("qualification") or "Not specified",
            adults_count=booking.get("adults_count") or "Not specified",
            children_count=booking.get("children_count") or "Not specified",
            senior_count=booking.get("senior_count") or "Not specified",
            preferred_time=booking.get("preferred_time") or "Not specified",
            quantity=booking.get("quantity") or "Not specified",
            delivery_address=booking.get("delivery_address") or "Not specified",
            offering_type=booking.get("offering_type") or "Not specified",
            darshan_type=booking.get("darshan_type") or "Not specified",
            departure_city=booking.get("departure_city") or "Not specified",
            history=hist_str,
            query=text
        )

        res = extractor_llm.invoke(prompt_str)
        content = (res.content or "").strip()

        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        updates = json.loads(content)
        if isinstance(updates, dict):
            # Process package_type first if present to reset other fields
            if "package_type" in updates and updates["package_type"] is not None:
                new_pt = updates["package_type"]
                # Trust query keywords over LLM package_type extraction to prevent hallucinations
                query_pkg = detect_package_type_from_text(text_low)
                if query_pkg and query_pkg != new_pt:
                    new_pt = query_pkg
                    print(f"[extract] Overrode LLM package_type '{updates['package_type']}' with query-detected '{query_pkg}'")
                
                # Safeguard: do not allow package_type to be forced/switched to astrology if a temple is set
                if new_pt == "astrology" and (booking.get("temple") or extracted.get("temple") or updates.get("temple")):
                    current_pt = booking.get("package_type")
                    if current_pt not in ("darshan", "yatra", "puja", "prasadam", "chadhava"):
                        new_pt = "darshan"
                    else:
                        new_pt = current_pt
                
                if new_pt and booking.get("package_type") != new_pt:
                    update_booking(user_id, "package_type", new_pt)
                    extracted["package_type"] = new_pt
                    reset_irrelevant_fields(user_id, new_pt)

            # Process other updates
            for k, v in updates.items():
                if k == "package_type":
                    continue
                if k == "puja" and skip_puja_extraction:
                    continue
                if k == "preferred_time" and v is not None:
                    if not is_valid_preferred_time(str(v)):
                        print(f"[extract] Ignored invalid/hallucinated preferred_time: '{v}'")
                        continue
                if v is not None:
                    if k in ("people", "adults_count", "children_count", "senior_count", "quantity"):
                        try:
                            v = int(v)
                        except ValueError:
                            continue
                    elif k == "elderly":
                        v = bool(v)
                    elif k == "temple":
                        temple_entry = detect_temple(v)
                        if temple_entry:
                            # Validate that the temple was actually mentioned in the user's message
                            # to prevent LLM extraction hallucinations from general queries.
                            if _is_temple_name_mentioned(temple_entry["name"], text):
                                v = temple_entry["name"]
                                update_booking(user_id, "temple_location", temple_entry.get("location", ""))
                            else:
                                print(f"[extract] Rejected hallucinated temple '{temple_entry['name']}' not mentioned in query '{text}'")
                                continue
                        else:
                            continue

                    if booking.get(k) != v:
                        update_booking(user_id, k, v)
                        extracted[k] = v
    except Exception as e:
        print(f"[extract] LLM extraction error: {e}")

    # Force package_type based on other key fields if not set
    pkg_type = booking.get("package_type") or extracted.get("package_type")
    if not pkg_type:
        if booking.get("puja") or extracted.get("puja"):
            pkg_type = "puja"
        elif booking.get("offering_type") or extracted.get("offering_type"):
            pkg_type = "chadhava"
        elif booking.get("delivery_address") or extracted.get("delivery_address"):
            pkg_type = "prasadam"
        elif (booking.get("preferred_time") or extracted.get("preferred_time")) and not (booking.get("temple") or extracted.get("temple")):
            # Only force to astrology if the text contains astrology keywords or is definitely not darshan/yatra
            if any(kw in text_low for kw in ["astrology", "horoscope", "kundli", "astrologer", "jyotish", "consultation", "session"]):
                pkg_type = "astrology"
        elif booking.get("darshan_type") or extracted.get("darshan_type"):
            pkg_type = "darshan"
        elif booking.get("temple") or extracted.get("temple"):
            pkg_type = "darshan"
            
    if pkg_type and booking.get("package_type") != pkg_type:
        update_booking(user_id, "package_type", pkg_type)
        extracted["package_type"] = pkg_type

    # ---- DEPARTURE CITY extraction ----
    if not booking.get("departure_city"):
        _city_patterns = [
            r"(?:from|departing from|travelling from|traveling from|starting from|base city|home city|city)\s+([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)",
        ]
        for pat in _city_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                city_val = m.group(1).strip().title()
                _CITY_STOPWORDS = {"Here", "There", "India", "Home", "My", "Our", "The"}
                if city_val not in _CITY_STOPWORDS and 2 < len(city_val) < 50:
                    update_booking(user_id, "departure_city", city_val)
                    extracted["departure_city"] = city_val
                    break

    # ---- SPECIAL REQUIREMENTS extraction ----
    if not booking.get("special_requirements"):
        _special_keywords = [
            "wheelchair", "special assistance", "vegetarian", "vegan",
            "medical condition", "mobility issue", "special need",
            "need help", "require assistance", "disabled", "physically challenged",
        ]
        text_low_sr = text.lower()
        found_reqs = [kw for kw in _special_keywords if kw in text_low_sr]
        if found_reqs:
            req_str = ", ".join(found_reqs)
            update_booking(user_id, "special_requirements", req_str)
            extracted["special_requirements"] = req_str

    if extracted:
        print(f"[extract] Auto-filled from message/history: {extracted}")

    return extracted


# --------------------------------------------------
# HELPERS — unchanged from v1
# --------------------------------------------------

def extract_people_count(text):
    """
    Extracts a number from various forms of people-count answers.
    Handles: "4", "4 log", "we are 4", "group of 4", "hum 4 hain", etc.
    """
    text = text.strip()

    patterns = [
        r'^\s*(\d+)\s*$',                      # bare number: "4"
        r'(\d+)\s*(log|people|person|members|adults|hain|hai)',  # "4 log", "4 hain"
        r'we\s+are\s+(\d+)',                   # "we are 4"
        r'hum\s+(\d+)',                        # "hum 4"
        r'group\s+of\s+(\d+)',                 # "group of 4"
        r'(\d+)\s+of\s+us',                    # "4 of us"
        r'total\s+(\d+)',                      # "total 4"
    ]

    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return int(match.group(1))

    return None


def detect_elderly(text):
    """
    Returns True if text indicates elderly/children in the group.
    """
    text = text.lower().strip()

    affirmatives = [
        "yes", "haan", "ha", "haa", "ji", "ji haan", "bilkul",
        "haan ji", "yes ji", "zaroor", "of course", "sure"
    ]
    if text in affirmatives or any(a == text for a in affirmatives):
        return True

    keywords = [
        "elderly", "parents", "mother", "father", "children", "child",
        "senior citizen", "buzurg", "bujurg", "dadi", "dada", "nana",
        "nani", "grandma", "grandpa", "bacha", "bachche", "kids",
        "bade", "old", "aged", "uncle", "aunty", "maa", "papa", "baba"
    ]
    return any(k in text for k in keywords)


# --------------------------------------------------
# TEMPLE LIST — loaded dynamically from MongoDB
# --------------------------------------------------

def _load_temples_from_mongo():
    """
    Fetches the authoritative list of temples Naman Darshan offers assisted darshan for.
    SOURCE: assisted_packages collection ONLY.
    Falls back to a hardcoded list if MongoDB is unavailable.
    """
    fallback = [
        {"name": "Tirupati Balaji Temple",   "location": "Tirumala, Andhra Pradesh, India"},
        {"name": "Ayodhya Ram Mandir",        "location": "Ayodhya, Uttar Pradesh, India"},
        {"name": "Kashi Vishwanath",          "location": "Varanasi (Kashi), Uttar Pradesh, India"},
        {"name": "Shri Mata Vaishno Devi",    "location": "Katra, Jammu & Kashmir"},
        {"name": "Kedarnath Dham",            "location": "Uttarakhand"},
        {"name": "Badrinath Temple Darshan",  "location": "Badrinath, Uttarakhand"},
        {"name": "Mahakaleshwar",             "location": "Ujjain, Madhya Pradesh, India"},
        {"name": "Somnath Temple",            "location": "Prabhas Patan, Veraval, Gujarat"},
        {"name": "Shirdi Sai Baba Temple",    "location": "Shirdi, Maharashtra"},
        {"name": "Puri Jagannath",            "location": "Puri, Odisha"},
        {"name": "Dwarkadhish",               "location": "Dwarka city, Devbhumi Dwarka district, Gujarat"},
        {"name": "Meenakshi Amman Darshan",   "location": "Madurai, Tamil Nadu"},
        {"name": "Golden Temple Amritsar",    "location": "Amritsar, Punjab"},
        {"name": "Kamakhya Temple",           "location": "Guwahati, Assam"},
    ]
    try:
        mongo_uri = os.getenv("MONGO_URI") or "mongodb+srv://ayush:strongpassword123@sales-ai-backend.gofnxnk.mongodb.net/"
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = client["temples_clone"]

        seen = set()
        results = []

        def _add(name, location):
            name     = (name     or "").strip()
            location = (location or "").strip()
            if not name:
                return
            key = (name.lower(), location.lower())
            if key not in seen:
                seen.add(key)
                results.append({"name": name, "location": location})

        # 1. Load from temples collection
        for doc in db.temples.find({}, {"name": 1, "location": 1, "_id": 0}):
            n = (doc.get("name") or "").strip()
            l = (doc.get("location") or "").strip()
            if n:
                _add(n, l)

        # 2. Load from darshans collection
        darshan_loc_map = {}
        for doc in db.darshans.find({}, {"name": 1, "temple_name": 1, "location": 1, "city": 1, "_id": 0}):
            n = (doc.get("name") or doc.get("temple_name") or "").strip()
            l = (doc.get("location") or doc.get("city") or "").strip()
            if n:
                darshan_loc_map[n.lower()] = l
                _add(n, l)

        # 3. Load from Yatra_packages collection
        for doc in db.Yatra_packages.find({}, {"temple_name": 1, "location": 1, "city": 1, "_id": 0}):
            name = (doc.get("temple_name") or "").strip()
            loc  = (doc.get("location") or doc.get("city") or "").strip()
            if not loc:
                loc = darshan_loc_map.get(name.lower(), "")
            _add(name, loc)

        return results if results else fallback

    except Exception:
        return fallback


_ALL_TEMPLES = _load_temples_from_mongo()


# --------------------------------------------------
# PUJA LIST — loaded dynamically from MongoDB
# --------------------------------------------------

def _load_pujas_from_mongo():
    """
    Fetches the list of all available pujas offered by Naman Darshan.
    SOURCE: pujas collection in MongoDB.
    Falls back to a hardcoded list if MongoDB is unavailable.
    """
    fallback = [
        "Shiv Rudrabhishek Puja",
        "Maha Laxmi Mata Puja",
        "Ram Raksha Stotra Puja",
        "Sunderkand Paath",
        "Satyanarayan Puja",
        "Panchamrut Abhishek Puja",
        "Khatu Shyam Ji Puja",
        "Shri Krishna Puja",
    ]
    try:
        mongo_uri = os.getenv("MONGO_URI") or "mongodb+srv://ayush:strongpassword123@sales-ai-backend.gofnxnk.mongodb.net/"
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = client["temples_clone"]
        results = []
        for doc in db.pujas.find({}, {"title": 1, "_id": 0}):
            title = doc.get("title")
            if title:
                results.append(title.strip())
        client.close()
        return results if results else fallback
    except Exception:
        return fallback


_ALL_PUJAS = _load_pujas_from_mongo()

for _p in _ALL_PUJAS:
    _p_low = _p.lower()
    if _p_low not in _PUJA_NAMES:
        _PUJA_NAMES.append(_p_low)




# --------------------------------------------------
# CANONICAL TEMPLE ALIAS MAP
# --------------------------------------------------

_TEMPLE_ALIASES = [
    {"keywords": ["tirupati", "tirumala", "venkateswara", "balaji", "tirupathi"],
     "entry": {"name": "Tirupati Balaji Temple", "location": "Tirumala, Andhra Pradesh, India"}},
    {"keywords": ["ram mandir", "ram temple", "ayodhya", "ramlala", "ram lalla"],
     "entry": {"name": "Ayodhya Ram Mandir", "location": "Ayodhya, Uttar Pradesh, India"}},
    {"keywords": ["kashi vishwanath", "kashi", "vishwanath", "varanasi", "banaras", "benares"],
     "entry": {"name": "Kashi Vishwanath", "location": "Varanasi (Kashi), Uttar Pradesh, India"}},
    {"keywords": ["vaishno devi", "vaishnodevi", "mata vaishno", "katra", "vaishno"],
     "entry": {"name": "Shri Mata Vaishno Devi", "location": "Katra, Jammu & Kashmir"}},
    {"keywords": ["kedarnath", "kedar", "kedardham"],
     "entry": {"name": "Kedarnath Dham", "location": "Uttarakhand"}},
    {"keywords": ["badrinath", "badri", "badrinath temple", "badrinath dham"],
     "entry": {"name": "Badrinath Temple Darshan", "location": "Badrinath, Uttarakhand"}},
    {"keywords": ["mahakaleshwar", "mahakal", "ujjain", "mahakaal", "mahakaleshwar jyotirlinga"],
     "entry": {"name": "Mahakaleshwar", "location": "Ujjain, Madhya Pradesh, India"}},
    {"keywords": ["somnath", "somnatha", "somnath temple"],
     "entry": {"name": "Somnath Temple", "location": "Prabhas Patan, Veraval, Gujarat"}},
    {"keywords": ["shirdi", "sai baba", "saibaba", "shirdi sai"],
     "entry": {"name": "Shirdi Sai Baba Temple", "location": "Shirdi, Maharashtra"}},
    {"keywords": ["jagannath", "puri jagannath", "jagannatha", "puri temple"],
     "entry": {"name": "Puri Jagannath", "location": "Puri, Odisha"}},
    {"keywords": ["dwarkadhish", "dwarkadheesh", "dwarkadhish temple", "dwarkadish",
                  "dwarkdhish", "dwarkadhis", "dwaraka", "dwarka temple", "dwarka",
                  "dwarika", "dwarika temple", "dwarikadheesh"],
     "entry": {"name": "Dwarkadhish", "location": "Dwarka city, Devbhumi Dwarka district, Gujarat"}},
    {"keywords": ["meenakshi", "madurai", "meenakshi amman", "minakshi", "meenakshi temple"],
     "entry": {"name": "Meenakshi Amman Darshan", "location": "Madurai, Tamil Nadu"}},
    {"keywords": ["rameshwaram", "rameswaram", "ramanathaswamy", "ramanathaswamy temple", "rameshwaram temple"],
     "entry": {"name": "Ramanathaswamy Temple", "location": "Rameshwaram"}},
    {"keywords": ["kanyakumari", "kanya kumari", "bhagavathy amman", "kanyakumari temple", "kanyakumari bhagavathy amman temple"],
     "entry": {"name": "Kanyakumari Bhagavathy Amman Temple", "location": "Kanyakumari, Tamil Nadu"}},
    {"keywords": ["golden temple", "amritsar", "harmandir", "harmandir sahib"],
     "entry": {"name": "Golden Temple Amritsar", "location": "Amritsar, Punjab"}},
    {"keywords": ["kamakhya", "guwahati temple", "kamaksha", "kamakhya devi"],
     "entry": {"name": "Kamakhya Temple", "location": "Guwahati, Assam"}},
    {"keywords": ["banke bihari", "vrindavan", "vrindaban", "vrindavan temple"],
     "entry": {"name": "Shri Banke Bihari", "location": "Vrindavan, Mathura District, Uttar Pradesh"}},
    {"keywords": ["mathura", "krishna janmabhoomi", "janmabhoomi", "mathura temple"],
     "entry": {"name": "Divine Darshan at Shree Krishna Janmabhoomi", "location": "Mathura, Uttar Pradesh, India"}},
    {"keywords": ["nathdwara", "shrinathji", "srinathji", "shreenathji"],
     "entry": {"name": "Divine Darshan at Nathdwara Shrinathji Temple", "location": "Nathdwara, Rajasthan, India"}},
    {"keywords": ["omkareshwar", "omkar", "omkareshwar jyotirlinga"],
     "entry": {"name": "Omkareshwar Jyotirlinga", "location": "Mandhata Island, MP"}},
    {"keywords": ["trimbakeshwar", "trimbak", "nashik jyotirlinga", "trimbakeshwar jyotirlinga"],
     "entry": {"name": "Trimbakeshwar Jyotirlinga", "location": "Nashik, Maharashtra"}},
    {"keywords": ["nageshwar", "nagnath", "nageshwar jyotirlinga"],
     "entry": {"name": "Nageshwar Jyotirlinga", "location": "Dwarka-Mithapur Road, Devbhumi Dwarka District, Gujarat"}},
    {"keywords": ["bhimashankar", "bhima shankar", "bhimashankar jyotirlinga"],
     "entry": {"name": "Bhimashankar Temple", "location": "Pune, Maharashtra"}},
    {"keywords": ["siddhivinayak", "siddhi vinayak", "mumbai ganesh", "prabhadevi"],
     "entry": {"name": "Shri Siddhivinayak Ganapati Temple", "location": "Mumbai, Maharashtra"}},
    {"keywords": ["sabarimala", "ayyappa", "sabari mala", "pathanamthitta"],
     "entry": {"name": "Sabarimala Sastha Temple , Pathanamthitta", "location": "Kerala"}},
    {"keywords": ["padmanabhaswamy", "padmanabha", "thiruvananthapuram temple", "trivandrum temple"],
     "entry": {"name": "Padmanabhaswamy Temple", "location": "Thiruvananthapuram, Kerala"}},
    {"keywords": ["gangotri", "gangotri temple", "ganga origin"],
     "entry": {"name": "Gangotri Temple", "location": "Gangotri, Uttarakhand"}},
    {"keywords": ["yamunotri", "yamuna origin", "yamunotri temple"],
     "entry": {"name": "Yamunotri Temple", "location": "Uttarkashi, Uttarakhand"}},
    {"keywords": ["khatu shyam", "khatu shyamji", "shyam baba", "khatu"],
     "entry": {"name": "Khatu Shyam Ji Temple", "location": "Sikar, Rajasthan"}},
    {"keywords": ["dakshineswar", "dakshineshwar", "dakshineswar kali"],
     "entry": {"name": "Dakshineswar Kali Temple Darshan", "location": "Kolkata, West Bengal"}},
    {"keywords": ["kalighat", "kalighat kali", "kalighat temple"],
     "entry": {"name": "Kalighat Kali Temple Darshan", "location": "Kolkata, West Bengal"}},
    {"keywords": ["akshardham", "swaminarayan akshardham", "akshardham delhi"],
     "entry": {"name": "Swaminarayan Akshardham", "location": "New Delhi"}},
]


# --------------------------------------------------
# TEMPLE-MENTION DETECTION — checks if user is clearly naming/requesting a temple
# Used to distinguish "I want Mallikarjun Jyotirlinga" (temple mention, not in DB)
# from completely generic messages like "hi" or "tell me more"
# --------------------------------------------------

_TEMPLE_INTENT_KEYWORDS = [
    "jyotirlinga", "jyotirling", "temple", "mandir", "dham", "peeth",
    "tirth", "kshetra", "devasthan", "gurudwara",
]

# Known unsupported-temple keywords that should still trigger the "not in DB" message
_KNOWN_TEMPLE_FRAGMENTS = [
    "mallikarjun", "mallikarjuna", "srisailam", "grishneshwar", "ghrishneshwar",
    "vaidyanath", "baidyanath",
    "aundha nagnath", "aundha", "kedareshwar", "mukteswara", "amareshwar",
    "brihadeshwara", "brihadeeswarar",
    "murudeshwara", "murudeshwar",
    "lingaraj", "lingaraja",
    "ekambareshwar", "ekamranathar",
    "kapaleeshwarar", "kapaleeshwar",
    "nataraja", "chidambaram",
    "guruvayur", "tiruvannamalai", "annamalaiyar",
    "vittala", "vithoba", "pandharpur",
    "kalahasti", "srikalahasti",
    "tirupparankundram", "tiruchendur",
    "chengannur", "vaikom",
    "mahalaxmi", "mahalakshmi", "kolhapur",
    "tulja bhavani", "tuljapur",
    "saptashringi", "vani",
    "shani shingnapur",
    "jawala devi", "jwaladevi", "jwala devi",
    "chamunda", "chintpurni",
    "baglamukhi", "bagalamukhi",
    "vindhyavasini", "vindhyachal",
    "nandadevi", "nanda devi",
]


def _mentions_temple_not_in_db(text: str) -> bool:
    """
    Returns True if the user's message appears to be referring to a specific temple/pilgrimage
    that could NOT be matched by detect_temple() (i.e., not in the live DB).

    Strategy:
    1. If any _KNOWN_TEMPLE_FRAGMENTS word appears → True
    2. If any _TEMPLE_INTENT_KEYWORDS appears AND the message is NOT a pure greeting → True
    """
    text_lower = text.lower().strip()

    _PURE_GREETINGS = {
        "hi", "hello", "hey", "namaste", "hii", "helo",
        "good morning", "good afternoon", "good evening", "jai shri ram", "jai shri",
        "jai sai ram", "om namah shivay", "har har mahadev", "namaskar",
    }
    if text_lower in _PURE_GREETINGS:
        return False

    # Explicit known-fragment check (highest priority)
    if any(frag in text_lower for frag in _KNOWN_TEMPLE_FRAGMENTS):
        return True

    # Generic temple-intent keyword
    if any(kw in text_lower for kw in _TEMPLE_INTENT_KEYWORDS):
        return True

    return False





def detect_temple(text):
    """
    Detects which temple the user mentioned, with full typo/spelling tolerance.
    STRICT MODE: Only returns temples that exist in the live MongoDB database.
    """
    text_lower = text.lower().strip()
    _db_names = {entry["name"].lower() for entry in _ALL_TEMPLES}

    # Pass 0: canonical alias map
    for alias_entry in _TEMPLE_ALIASES:
        if any(kw in text_lower for kw in alias_entry["keywords"]):
            candidate = alias_entry["entry"]
            if candidate["name"].lower() in _db_names:
                return candidate
            return None

    _STOPWORDS = {
        "temple", "mandir", "devi", "mata", "maa", "shri", "shree", "sri",
        "baba", "gurudwara", "masjid", "church", "jyotirling", "jyotirlinga",
        "swami", "maharaj", "bhagwan", "kali", "dham", "tirth", "kshetra",
        "visit", "want", "plan", "going", "travel", "pilgrimage", "darshan",
        "sacred", "divine", "great", "holy",
    }

    for entry in _ALL_TEMPLES:
        if entry["name"].lower() == text_lower:
            return entry

    for entry in _ALL_TEMPLES:
        if len(text_lower) >= 4 and text_lower in entry["name"].lower():
            return entry

    for entry in _ALL_TEMPLES:
        if len(text_lower) >= 4 and entry["name"].lower() in text_lower:
            return entry

    candidates = []
    for entry in _ALL_TEMPLES:
        unique_words = [
            w for w in entry["name"].lower().split()
            if len(w) > 4 and w not in _STOPWORDS
        ]
        if unique_words and any(w in text_lower for w in unique_words):
            candidates.append(entry)

    if len(candidates) == 1:
        return candidates[0]

    if len(candidates) > 1:
        for entry in candidates:
            loc_words = [w for w in entry["location"].lower().split() if len(w) > 3]
            if loc_words and any(w in text_lower for w in loc_words):
                return entry
        return candidates[0]

    user_tokens = [t for t in re.split(r'\s+', text_lower) if len(t) >= 4]

    all_db_names_lower = [e["name"].lower() for e in _ALL_TEMPLES]
    for token in user_tokens:
        matches = get_close_matches(token, all_db_names_lower, n=1, cutoff=0.72)
        if matches:
            for entry in _ALL_TEMPLES:
                if entry["name"].lower() == matches[0]:
                    return entry

    for token in user_tokens:
        if len(token) < 6:
            continue
        for alias_entry in _TEMPLE_ALIASES:
            kw_matches = get_close_matches(token, alias_entry["keywords"], n=1, cutoff=0.82)
            if kw_matches:
                return alias_entry["entry"]

    return None


def _validate_and_sanitize_session_memory(user_id: str, booking: dict, history: list, query: str):
    """
    Ensures that customer information and booking details belong to the current conversation.
    Ignores and clears names/details from previous sessions if they are not in the current conversation.

    IMPORTANT: Phone number is the session identity anchor — it is NEVER cleared by this
    function. Once a user has shared their phone, it stays in the session so that
    _hydrate_from_customer_profile() can always look up their Customer_Profile.
    """
    import re
    from memory import get_memory
    from booking_flow import update_booking

    # Gather conversation history turns
    if user_id.startswith("test-"):
        current_turns = history or []
        db_history = get_memory(user_id, limit=100) or []
        merged_history = []
        seen_turns = set()
        for turn in current_turns + db_history:
            turn_key = (turn.get("user", ""), turn.get("assistant", ""))
            if turn_key not in seen_turns:
                seen_turns.add(turn_key)
                merged_history.append(turn)
    else:
        merged_history = history or []

    # Combine all text of the current conversation
    all_text = query.lower()
    for turn in merged_history:
        all_text += " " + turn.get("user", "").lower() + " " + turn.get("assistant", "").lower()

    # Check if a specific value is mentioned in the text
    def is_mentioned(val):
        if val is None or val == "":
            return False
        val_str = str(val).lower().strip()
        if not val_str:
            return False
        if val_str in ("true", "false"):
            return True
        if val_str.replace(" ", "").isalnum():
            # word boundary match to prevent false positives on short names
            return bool(re.search(r'\b' + re.escape(val_str) + r'\b', all_text))
        return val_str in all_text

    # 1. Customer Name identity rule — only clear name if it genuinely isn't in any turn
    #    AND the session has no phone anchor to recover it from Customer_Profile.
    name = booking.get("customer_name")
    phone = booking.get("phone")
    if name and not is_mentioned(name) and not phone:
        # Only clear name if we also have no phone to re-hydrate from Customer_Profile
        update_booking(user_id, "customer_name", None)
        print(f"[sanitize] Cleared customer_name '{name}' — not in conversation and no phone anchor.")

    # 2. Phone — NEVER cleared; it is the session identity anchor used for Customer_Profile
    #    lookup. Clearing it would make it impossible to recognise returning customers.
    #    (Previously this function cleared phone if not mentioned — that was the root cause
    #    of returning customers losing all their profile data.)

    # 3. New conversation reset rule — only reset if this is genuinely a brand-new user
    #    (no prior message_count AND no phone in session). If the session was recovered
    #    from MongoDB, message_count > 0 or phone is set, so we skip the reset.
    is_new_chat = (
        len(merged_history) == 0
        and booking.get("message_count", 0) <= 1
        and not booking.get("phone")
        and not booking.get("customer_name")
    )

    if is_new_chat and user_id.startswith("test-") and booking.get("message_count", 0) > 1:
        is_new_chat = False

    if is_new_chat:
        fields_to_reset = [
            "temple", "temple_location", "date", "people", "elderly", "qualification",
            "customer_name", "phone", "budget", "puja", "puja_mode", "package_type",
            "adults_count", "children_count", "senior_count", "preferred_time",
            "quantity", "delivery_address", "offering_type", "darshan_type",
            "booking_confirmed", "pricing_shared", "name_asked", "phone_asked"
        ]
        for key in fields_to_reset:
            default_val = False if key in ("elderly", "booking_confirmed", "pricing_shared", "name_asked", "phone_asked") else None
            if booking.get(key) != default_val:
                update_booking(user_id, key, default_val)
        print(f"[sanitize] Reset booking session for brand new conversation (user_id={user_id}).")


# --------------------------------------------------
# CUSTOMER PROFILE HYDRATION — loads known data for returning customers
# --------------------------------------------------

def _hydrate_from_customer_profile(user_id: str, booking: dict):
    """
    If the session already has a phone number but is missing the customer name
    (or other key profile fields), fetch the Customer_Profile keyed by that phone
    and backfill any gaps into the live session.

    This bridges the gap between app.py's random UUID-based user_id and the
    phone-keyed Customer_Profile records stored in MongoDB.
    """
    phone = booking.get("phone")
    if not phone:
        return  # Nothing to look up yet

    # Only bother if we're actually missing profile data
    _profile_fields_in_session = [
        "customer_name", "temple", "date", "people",
        "departure_city", "budget",
    ]
    all_present = all(booking.get(f) for f in _profile_fields_in_session)
    if all_present:
        return  # Session already fully populated

    try:
        # Look up by phone number (the canonical key in Customer_Profile)
        profile = get_customer_profile(phone)
        if not profile:
            return

        from datetime import datetime

        # Standardize the retrieved profile data into session key format, using CRM fallbacks
        standardized_profile = {}

        # 1. Customer Name
        name_val = profile.get("customer_name") or profile.get("name")
        if name_val:
            standardized_profile["customer_name"] = str(name_val).strip()

        # 2. Temple / Destination
        temple_val = profile.get("temple") or profile.get("destination")
        if temple_val:
            standardized_profile["temple"] = str(temple_val).strip()

        # 3. Travel Date
        date_val = profile.get("travel_date") or profile.get("date")
        if date_val:
            if isinstance(date_val, datetime):
                standardized_profile["date"] = date_val.strftime("%d %B %Y")
            else:
                standardized_profile["date"] = str(date_val).strip()

        # 4. Departure City
        dept_val = profile.get("departure_city")
        if dept_val:
            standardized_profile["departure_city"] = str(dept_val).strip()

        # 5. Budget
        budget_val = profile.get("budget")
        if budget_val is not None:
            if isinstance(budget_val, (int, float)):
                standardized_profile["budget"] = str(int(budget_val))
            else:
                standardized_profile["budget"] = str(budget_val).strip()

        # 6. Service Type / Package Type
        pkg_val = profile.get("service_type") or profile.get("package_type")
        if pkg_val:
            standardized_profile["package_type"] = str(pkg_val).strip()

        # 7. Puja Name
        puja_val = profile.get("puja_name") or profile.get("puja")
        if puja_val:
            standardized_profile["puja"] = str(puja_val).strip()

        # 8. Puja Mode
        pm_val = profile.get("puja_mode")
        if pm_val:
            standardized_profile["puja_mode"] = str(pm_val).strip()

        # 9. Adults Count
        adults_val = profile.get("adults")
        if adults_val is not None:
            try:
                standardized_profile["adults_count"] = int(float(adults_val))
            except (ValueError, TypeError):
                pass

        # 10. Children Count
        children_val = profile.get("children")
        if children_val is not None:
            try:
                standardized_profile["children_count"] = int(float(children_val))
            except (ValueError, TypeError):
                pass

        # 11. Seniors Count
        seniors_val = profile.get("seniors") or profile.get("senior_count")
        if seniors_val is not None:
            try:
                standardized_profile["senior_count"] = int(float(seniors_val))
            except (ValueError, TypeError):
                pass

        # 12. Total Travellers (people)
        people_val = profile.get("total_travellers") or profile.get("people")
        if people_val is not None:
            try:
                standardized_profile["people"] = int(float(people_val))
            except (ValueError, TypeError):
                pass
        else:
            # Try to sum adults + children
            ac = standardized_profile.get("adults_count", 0)
            cc = standardized_profile.get("children_count", 0)
            sc = standardized_profile.get("senior_count", 0)
            if ac + cc + sc > 0:
                standardized_profile["people"] = ac + cc + sc

        # 13. Special Requirements
        spec_val = profile.get("special_requirements")
        if spec_val:
            standardized_profile["special_requirements"] = str(spec_val).strip()

        merged = []
        for session_key, value in standardized_profile.items():
            # Only backfill if the session doesn't already have this value
            if not booking.get(session_key) and value:
                from booking_flow import update_booking
                update_booking(user_id, session_key, value)
                booking[session_key] = value  # keep local ref in sync
                merged.append(session_key)

        if merged:
            print(f"[rag_pipeline] Hydrated session from Customer_Profile (phone={phone}): {merged}")

    except Exception as e:
        print(f"[rag_pipeline] Customer_Profile hydration error: {e}")


# --------------------------------------------------
# MAIN RESPONSE GENERATOR — Unified RAG QA Architecture
# --------------------------------------------------

def generate_response(query: str, history: list, user_id: str) -> str:
    """
    Main entry point. Orchestrates the unified RAG flow:
      User Question -> Intent Detection -> DB/FAISS Retrieval -> Context Builder -> LLM -> Answer
    """
    # Ensure booking session is initialized
    booking = get_booking(user_id)
    increment_message_count(user_id)
    query_stripped = query.strip()

    # Save phone BEFORE sanitizer — the sanitizer used to clear it, which broke
    # hydration. We preserve it here so it's available for Customer_Profile lookup
    # even if the current message doesn't mention the phone explicitly.
    _phone_before_sanitize = booking.get("phone")
    _name_before_sanitize  = booking.get("customer_name")

    # Sanitize and validate session memory
    _validate_and_sanitize_session_memory(user_id, booking, history, query_stripped)
    booking = get_booking(user_id)

    # Restore phone/name if sanitizer cleared them — phone is the identity anchor
    # and must persist across messages so returning customers are recognised.
    if _phone_before_sanitize and not booking.get("phone"):
        from booking_flow import update_booking as _upd
        _upd(user_id, "phone", _phone_before_sanitize)
        booking["phone"] = _phone_before_sanitize
        print(f"[generate_response] Restored phone {_phone_before_sanitize} after sanitizer.")
    if _name_before_sanitize and not booking.get("customer_name"):
        from booking_flow import update_booking as _upd
        _upd(user_id, "customer_name", _name_before_sanitize)
        booking["customer_name"] = _name_before_sanitize
        print(f"[generate_response] Restored customer_name '{_name_before_sanitize}' after sanitizer.")

    # 1. Smart Extraction: Parse and save details (name, date, people, etc.) from the message
    _extract_and_hydrate(user_id, query_stripped, history)
    booking = get_booking(user_id)

    # 1a. Customer Profile Hydration — look up Customer_Profile by phone number and
    #     backfill any session fields that are still missing (people, date, budget, etc.).
    #     This runs AFTER extraction so a freshly-extracted phone is also usable.
    _hydrate_from_customer_profile(user_id, booking)
    booking = get_booking(user_id)  # refresh after hydration

    # 1b. Sync latest session → Customer_Profile collection in MongoDB
    #     Also infers current_intent from package_type so Customer_Profile stays accurate
    try:
        pkg = booking.get("package_type") or ""
        _intent_map = {
            "puja":      INTENT_PUJA_BOOKING,
            "prasadam":  INTENT_PRASADAM_BOOKING,
            "chadhava":  INTENT_CHADHAVA_BOOKING,
            "darshan":   INTENT_DARSHAN_BOOKING,
            "astrology":  INTENT_MAIN_BOOKING,
            "yatra":     INTENT_MAIN_BOOKING,
        }
        detected_intent = _intent_map.get(pkg, INTENT_MAIN_BOOKING)
        # Check for abhishekam keyword in query
        if any(kw in query_stripped.lower() for kw in ["abhishekam", "abhishek", "rudrabhishek"]):
            detected_intent = INTENT_ABHISHEKAM_BOOKING
        # Check for accommodation keywords
        elif any(kw in query_stripped.lower() for kw in ["hotel", "accommodation", "stay", "room", "lodge"]):
            detected_intent = INTENT_ACCOMMODATION_BOOKING
        # Check for transportation keywords
        elif any(kw in query_stripped.lower() for kw in ["transport", "cab", "taxi", "bus", "flight", "train"]):
            detected_intent = INTENT_TRANSPORTATION_BOOKING

        if booking.get("current_intent") != detected_intent:
            update_booking(user_id, "current_intent", detected_intent)
            booking = get_booking(user_id)

        # Sync to Customer_Profile (keyed by session user_id)
        upsert_customer_profile(user_id, booking)

        # Also upsert keyed by phone number so returning customers can be looked up
        # by phone across different Streamlit sessions (which get new random UUIDs).
        _phone = booking.get("phone")
        if _phone and _phone != user_id:
            upsert_customer_profile(_phone, booking)

        # Update lead_stage in booking session to keep it fresh
        new_stage = compute_lead_stage(booking)
        if booking.get("lead_stage") != new_stage:
            update_booking(user_id, "lead_stage", new_stage)
            booking = get_booking(user_id)
    except Exception as _cp_err:
        print(f"[rag_pipeline] Customer_Profile sync error: {_cp_err}")

    # 2. Intent Detection
    intent = detect_user_intent(query_stripped)

    # Check for unsupported temple mention
    if not booking.get("temple") and _mentions_temple_not_in_db(query_stripped):
        intent = "UNSUPPORTED_TEMPLE"

    # Human agent request — create handoff record but let LLM generate the response
    if intent == "HUMAN_AGENT":
        from human_handoff import create_handoff_record
        create_handoff_record(user_id, booking)

    # 3. MongoDB / FAISS Retrieval (skip for no-RAG intents)
    _NO_RAG_INTENTS = {
        "GREETING", "TRUST", "COMPANY_NAME", "GST", "PRICE", "PRICE_REPEAT", "OFFICIAL",
        "DELAY", "GUARANTEE", "HUMAN_AGENT", "SERVICE_INTRO", "CLOSE",
        "SEND_DETAILS", "PAYMENT_METHOD", "PAYMENT_TIMING", "CANCELLATION_PLAN",
        "NAME_CAPTURED", "PHONE_CAPTURED",
        # Payment intents — no FAISS retrieval needed
        "PAYMENT_CONFIRM", "CHECK_PAYMENT",
    }
    
    context = ""
    if intent not in _NO_RAG_INTENTS:
        try:
            from retriever import retrieve_docs
            context = retrieve_docs(query_stripped)
        except Exception:
            context = ""

    # --------------------------------------------------
    # 4a. PAYMENT HANDLING — runs before prompt building
    # --------------------------------------------------

    # ---- PAYMENT_CONFIRM: generate payment link ----
    if intent == "PAYMENT_CONFIRM":
        # Validate that we have the minimum required fields
        missing_payment_fields = []
        is_astrology_service = (booking.get("package_type") == "astrology")
        if is_astrology_service:
            if not booking.get("package_type"):
                missing_payment_fields.append("service type")
        else:
            if not booking.get("temple"):
                missing_payment_fields.append("temple name")
            if not booking.get("package_type"):
                missing_payment_fields.append("service type")

        if not booking.get("people") and booking.get("package_type") not in ("prasadam", "chadhava", "astrology"):
            missing_payment_fields.append("number of travellers")
        if not booking.get("customer_name"):
            missing_payment_fields.append("your name")
        if not booking.get("phone"):
            missing_payment_fields.append("WhatsApp number")

        if missing_payment_fields:
            # Redirect to a soft information-request — ask for missing fields first
            # Override intent so prompt_builder generates the right response
            intent = "GENERAL"
            booking["_payment_missing"] = missing_payment_fields
            print(f"[rag_pipeline] PAYMENT_CONFIRM blocked — missing: {missing_payment_fields}")
        elif not booking.get("payment_link"):  # Don’t re-generate if link already exists
            print(f"[rag_pipeline] Generating Razorpay payment link for user_id={user_id}")
            pay_result = razorpay_handler.create_payment_link(
                user_id=user_id,
                booking=booking,
                amount=None,  # Auto-calculate from pricing table
            )
            if pay_result["success"]:
                # Store in session (write-through to MongoDB)
                update_booking(user_id, "payment_link",    pay_result["payment_link"])
                update_booking(user_id, "booking_id",      pay_result["booking_id"])
                update_booking(user_id, "payment_link_id", pay_result["payment_link_id"])
                update_booking(user_id, "amount",          pay_result["amount"])
                update_booking(user_id, "payment_status",  "pending")
                update_booking(user_id, "payment_asked",   True)
                booking = get_booking(user_id)  # refresh
                print(f"[rag_pipeline] Payment link stored: booking_id={pay_result['booking_id']}")
            else:
                print(f"[rag_pipeline] Payment link creation FAILED: {pay_result.get('error')}")
                # booking["payment_link"] remains None — prompt_builder handles the fallback
        else:
            print(f"[rag_pipeline] Payment link already exists for user_id={user_id}, reusing.")

    # ---- CHECK_PAYMENT: fetch live payment status ----
    elif intent == "CHECK_PAYMENT":
        status_result = razorpay_handler.get_payment_status(
            user_id=user_id,
            booking_id=booking.get("booking_id"),
        )
        if status_result["found"]:
            live_pstatus = status_result["payment_status"]
            # Sync live status to session if it changed
            if live_pstatus and live_pstatus != booking.get("payment_status"):
                update_booking(user_id, "payment_status", live_pstatus)
                if live_pstatus == "paid":
                    update_booking(user_id, "booking_confirmed", True)
                    update_booking(user_id, "lead_stage", "payment_confirmed")
                booking = get_booking(user_id)
            print(f"[rag_pipeline] Live payment status for {user_id}: {live_pstatus}")
        else:
            print(f"[rag_pipeline] No payment record found for user_id={user_id}")


    # Ensure pricing is calculated and saved in session if the form is complete (form_filled_no_payment)
    if booking.get("lead_stage") == "form_filled_no_payment" and not booking.get("amount"):
        calculated_amount = razorpay_handler._get_pricing(
            temple=booking.get("temple"),
            people=booking.get("people"),
            package_type=booking.get("package_type"),
        )
        if calculated_amount:
            update_booking(user_id, "amount", calculated_amount)
            booking = get_booking(user_id)  # refresh
            print(f"[rag_pipeline] Auto-calculated amount for complete profile: {calculated_amount}")

    # 4. Context Builder & LLM Execution
    # Inject query into booking dict temporarily so intent handlers can read it
    # (not persisted — removed immediately after prompt is built)
    booking["_last_query"] = query_stripped
    booking["_all_pujas"] = _ALL_PUJAS
    sales_instruction = get_sales_instruction(intent, booking)

    prompt = build_prompt(
        query=query_stripped,
        context=context,
        history=history,
        sales_instruction=sales_instruction,
        booking_data=booking,
        intent=intent
    )
    # Clean up temporary key — do NOT persist this to MongoDB
    booking.pop("_last_query", None)
    booking.pop("_all_pujas", None)


    max_retries  = 3
    backoff_secs = 5
    response_text = ""

    for attempt in range(max_retries):
        try:
            response = llm.invoke(prompt)
            response_text = response.content.strip()

            # Handle social proof tracking
            if not booking.get("social_proof_used", False):
                social_proof_markers = ["40 lakh", "4.7", "lakh devotees", "lakh+ devotees"]
                if any(marker in response_text for marker in social_proof_markers):
                    update_booking(user_id, "social_proof_used", True)

            break
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate limit" in err_str.lower():
                if attempt < max_retries - 1:
                    wait = backoff_secs * (2 ** attempt)
                    time.sleep(wait)
                    continue
                response_text = "I'm experiencing high traffic right now. Please send your message again in a moment. 🙏"
            else:
                err_msg = err_str[:80]
                response_text = f"A technical issue occurred. Please try again. ({err_msg[:60]})"
            break

    # 5. Update lead score and return response
    _finalize(user_id)
    return response_text


def _finalize(user_id: str):
    """Called after generating a response — updates lead score."""
    try:
        save_lead_score(user_id, get_booking(user_id))
    except Exception as e:
        print(f"[rag_pipeline] Lead score update failed: {e}")