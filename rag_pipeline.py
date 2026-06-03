# rag_pipeline.py
# Handles the conversation flow:
#   - State machine collects temple, date, people, elderly (data gathering phase)
#   - After data is collected, ALL responses go through the Groq LLM using prompt_builder
#   - Intent detection routes the right sales guidance into each LLM call

from booking_flow import (
    get_booking,
    update_booking,
    set_state,
    get_state,
    increment_message_count
)

from sales_logic import detect_user_intent
from prompt_builder import build_prompt, get_sales_instruction

from langchain_groq import ChatGroq
from config import GROQ_API_KEY

import re
import time
from pymongo import MongoClient
import os

# ---------------------------------------------------
# LLM INIT
# ---------------------------------------------------

llm = ChatGroq(
    # llama-3.1-8b-instant: 131,072 TPM on free tier (vs 6,000 TPM for 70b)
    # Switched to eliminate 429 rate-limit errors under normal usage.
    model="llama-3.1-8b-instant",
    temperature=0.5,
    max_tokens=500,
    api_key=GROQ_API_KEY
)


# ---------------------------------------------------
# HELPERS
# ---------------------------------------------------

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
        r'(\d+)',                              # fallback: any number in text
    ]

    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return int(match.group(1))

    return None


def detect_elderly(text):
    """
    Returns True if text indicates elderly/children in the group.
    Handles affirmative words AND specific keywords.
    """
    text = text.lower().strip()

    # Affirmative single-word responses
    affirmatives = [
        "yes", "haan", "ha", "haa", "ji", "ji haan", "bilkul",
        "haan ji", "yes ji", "zaroor", "of course", "sure"
    ]
    if text in affirmatives or any(a == text for a in affirmatives):
        return True

    # Specific keywords
    keywords = [
        "elderly", "parents", "mother", "father", "children", "child",
        "senior citizen", "buzurg", "bujurg", "dadi", "dada", "nana",
        "nani", "grandma", "grandpa", "bacha", "bachche", "kids",
        "bade", "old", "aged", "uncle", "aunty", "maa", "papa", "baba"
    ]
    return any(k in text for k in keywords)


def detect_no(text):
    """Returns True if user said 'no' to elderly question."""
    text = text.lower().strip()
    negatives = ["no", "nahi", "nahin", "nope", "na", "nhi", "sirf adults", "only adults"]
    return text in negatives or any(n == text for n in negatives)


def detect_language(text):
    """
    Detects whether the user's message is in English or Hinglish.
    Returns 'english' or 'hinglish'.

    Only uses words that are EXCLUSIVELY Hindi/Urdu romanised —
    words that would never naturally appear in a pure English sentence.
    """
    text_lower = text.lower().strip()

    # Devanagari Unicode range: U+0900–U+097F → always Hinglish
    if any('\u0900' <= ch <= '\u097f' for ch in text):
        return "hinglish"

    # Words that are ONLY used in Hindi / Hinglish — never in plain English.
    # Deliberately excludes ambiguous/English words like:
    # "booking", "payment", "main", "ko", "ki", "ka", "se", "ji"
    hinglish_only = {
        "aap", "aapka", "aapki", "aapke",
        "hain", "hai", "tha", "thi",
        "kya", "kyun", "kyunki",
        "aur", "lekin", "magar",
        "nahi", "nahin", "nhi",
        "bahut", "bilkul", "zaroor", "sirf",
        "theek", "haan", "haa",
        "bhai", "yaar",
        "agar", "toh",
        "mujhe", "humara", "humari", "hamare",
        "kitna", "kitne", "kitni",
        "woh", "yeh", "iska", "uska",
        "karo", "karna", "karein", "karega",
        "batao", "bata", "batana",
        "milega", "milti", "milta",
        "chahiye", "chahte",
        "paise", "paisa",
        "soch", "abhi",
        "mandir", "darshan",
    }

    words = set(text_lower.split())
    matched = words & hinglish_only

    # 2+ exclusive Hindi words → definitely Hinglish
    if len(matched) >= 2:
        return "hinglish"

    # 1 exclusive Hindi word ONLY if the message is 1-2 words total.
    # This prevents temple names like "Ayodhya Ram Mandir" (3 words, 1 Hindi
    # marker) from being falsely classified as Hinglish.
    if len(matched) == 1 and len(words) <= 2:
        return "hinglish"

    return "english"


def is_question_or_objection(text):
    """
    Returns True if the user's message is a question or objection
    rather than the expected sequential data (a date, a number, yes/no, etc.).

    Used to intercept mid-flow questions in data-collection states so the
    bot answers them instead of blindly advancing to the next state.
    """
    t = text.lower().strip()

    # Explicit question mark
    if t.endswith("?"):
        return True

    # Question starters
    question_starters = [
        "what", "how", "why", "when", "where", "who", "which",
        "can you", "will you", "is it", "are you", "do you", "does",
        "is there", "tell me", "explain", "i want to know",
    ]
    for starter in question_starters:
        if t.startswith(starter):
            return True

    # Objection / concern keywords anywhere in the message
    concern_keywords = [
        "cancel", "cancellation", "refund", "if my plan", "if plan",
        "price", "cost", "charges", "fees", "kitna", "expensive",
        "safe", "fraud", "fake", "trust", "scam", "payment",
        "official", "government", "authorized",
        "benefit", "advantage", "why vip", "difference",
        "process", "booking process", "how does",
        "guarantee", "money back", "paisa wapas",
        "delay", "postpone", "reschedule",
        "company", "traininglobe", "naman darshan",
        "gst", "invoice", "tax",
        "timing", "opening time", "closing time",
        "coordinate", "coordinator", "guide",
    ]
    for kw in concern_keywords:
        if kw in t:
            return True

    return False


def get_pending_question(state):
    """
    Returns the question the bot is currently waiting for an answer to,
    so it can be re-asked after handling an off-topic user question.
    """
    pending = {
        "ASK_DATE":          "Which date are you planning to travel?",
        "ASK_PEOPLE":        "How many people will be travelling?",
        "ASK_ELDERLY":       "Will there be any elderly members or children in the group?",
        "ASK_QUALIFICATION": "Are you travelling from the local area or from another state?",
    }
    return pending.get(state, "")


# ---------------------------------------------------
# TEMPLE LIST — loaded dynamically from MongoDB
# ---------------------------------------------------

def _load_temples_from_mongo():
    """
    Fetches temples from BOTH darshans and temples collections.
    Returns a list of dicts: [{"name": "...", "location": "..."}, ...]
    Deduplicates by normalized (name, location) key.
    Falls back to a hardcoded list if MongoDB is unavailable.
    """
    fallback = [
        {"name": "Tirupati Balaji Temple", "location": "Tirumala, Andhra Pradesh"},
        {"name": "Ram Mandir",             "location": "Ayodhya, Uttar Pradesh"},
        {"name": "Kashi Vishwanath Temple","location": "Varanasi, Uttar Pradesh"},
        {"name": "Vaishno Devi Temple",    "location": "Katra, Jammu & Kashmir"},
        {"name": "Kedarnath Temple",       "location": "Uttarakhand"},
        {"name": "Badrinath Temple",       "location": "Uttarakhand"},
        {"name": "Mahakaleshwar Jyotirlinga","location": "Ujjain, Madhya Pradesh"},
        {"name": "Somnath Jyotirlinga",    "location": "Gujarat"},
        {"name": "Shirdi Sai Baba Mandir", "location": "Shirdi, Maharashtra"},
        {"name": "Jagannath Temple",       "location": "Puri, Odisha"},
    ]
    try:
        mongo_uri = os.getenv("MONGO_URI") or "mongodb+srv://ayush:strongpassword123@sales-ai-backend.gofnxnk.mongodb.net/"
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = client["temples_clone"]

        seen = set()
        results = []

        def _add(name, location):
            """Normalize and deduplicate entries."""
            name     = (name     or "").strip()
            location = (location or "").strip()
            if not name:
                return
            key = (name.lower(), location.lower())
            if key not in seen:
                seen.add(key)
                results.append({"name": name, "location": location})

        # --- darshans collection ---
        for doc in db.darshans.find({}, {"temple_name": 1, "name": 1, "title": 1,
                                         "location": 1, "city": 1, "state": 1, "_id": 0}):
            name = doc.get("temple_name") or doc.get("name") or doc.get("title") or ""
            loc  = doc.get("location") or doc.get("city") or doc.get("state") or ""
            _add(name, loc)

        # --- temples collection ---
        for doc in db.temples.find({}, {"name": 1, "temple_name": 1,
                                        "location": 1, "city": 1, "address": 1, "_id": 0}):
            name = doc.get("name") or doc.get("temple_name") or ""
            loc  = doc.get("location") or doc.get("city") or ""
            _add(name, loc)

        return results if results else fallback

    except Exception:
        return fallback


# Load once at module startup
_ALL_TEMPLES = _load_temples_from_mongo()


# ---------------------------------------------------
# CANONICAL TEMPLE ALIAS MAP
# Maps popular names / spellings / keywords → correct temple entry.
# This runs BEFORE any fuzzy DB matching to prevent wrong matches.
# ---------------------------------------------------

_TEMPLE_ALIASES = [
    # Mallikarjuna Jyotirlinga, Srisailam
    {
        "keywords": ["mallikarjun", "mallikarjuna", "srisailam", "srisaila", "sri sailam"],
        "entry": {"name": "Mallikarjuna Jyotirlinga", "location": "Srisailam, Andhra Pradesh"}
    },
    # Tirupati Balaji
    {
        "keywords": ["tirupati", "tirumala", "venkateswara", "balaji", "tirupathi"],
        "entry": {"name": "Tirupati Balaji Temple", "location": "Tirumala, Andhra Pradesh"}
    },
    # Ram Mandir Ayodhya
    {
        "keywords": ["ram mandir", "ram temple", "ayodhya", "ramlala"],
        "entry": {"name": "Ram Mandir", "location": "Ayodhya, Uttar Pradesh"}
    },
    # Kashi Vishwanath
    {
        "keywords": ["kashi vishwanath", "kashi", "vishwanath", "varanasi", "banaras"],
        "entry": {"name": "Kashi Vishwanath Temple", "location": "Varanasi, Uttar Pradesh"}
    },
    # Vaishno Devi
    {
        "keywords": ["vaishno devi", "vaishnodevi", "mata vaishno", "katra"],
        "entry": {"name": "Vaishno Devi Temple", "location": "Katra, Jammu & Kashmir"}
    },
    # Kedarnath
    {
        "keywords": ["kedarnath", "kedar"],
        "entry": {"name": "Kedarnath Temple", "location": "Uttarakhand"}
    },
    # Badrinath
    {
        "keywords": ["badrinath", "badri"],
        "entry": {"name": "Badrinath Temple", "location": "Uttarakhand"}
    },
    # Mahakaleshwar / Ujjain
    {
        "keywords": ["mahakaleshwar", "mahakal", "ujjain", "mahakaal"],
        "entry": {"name": "Mahakaleshwar Jyotirlinga", "location": "Ujjain, Madhya Pradesh"}
    },
    # Somnath
    {
        "keywords": ["somnath", "somnatha"],
        "entry": {"name": "Somnath Jyotirlinga", "location": "Gujarat"}
    },
    # Shirdi
    {
        "keywords": ["shirdi", "sai baba", "saibaba"],
        "entry": {"name": "Shirdi Sai Baba Mandir", "location": "Shirdi, Maharashtra"}
    },
    # Jagannath Puri
    {
        "keywords": ["jagannath", "puri", "jagannatha"],
        "entry": {"name": "Jagannath Temple", "location": "Puri, Odisha"}
    },
]


def detect_temple(text):
    """
    Detects which temple the user mentioned.

    Returns a dict {"name": ..., "location": ...} or None.

    Matching order:
      Pass 0 — canonical alias map (hardcoded, highest priority)
               BUT only if the resolved name exists in _ALL_TEMPLES (DB).
               This prevents aliases for temples not on the website from being accepted.
      Pass 1 — exact full-name match against DB
      Pass 2 — user input contained inside a DB temple name
      Pass 3 — DB temple name contained inside user input
      Pass 4 — keyword + location disambiguation against DB
    """
    text_lower = text.lower().strip()

    # Build a set of normalised DB temple names for O(1) lookup
    _db_names = {entry["name"].lower() for entry in _ALL_TEMPLES}

    # --- Pass 0: canonical alias map — only if temple exists in DB ---
    for alias_entry in _TEMPLE_ALIASES:
        if any(kw in text_lower for kw in alias_entry["keywords"]):
            candidate = alias_entry["entry"]
            # Validate: the resolved name must be in the live DB
            if candidate["name"].lower() in _db_names:
                return candidate
            # If not in DB, break out and let the "not found" flow handle it
            return None

    _STOPWORDS = {
        "temple", "mandir", "devi", "mata", "maa", "shri", "shree", "sri",
        "baba", "gurudwara", "masjid", "church", "jyotirling", "jyotirlinga",
        "swami", "maharaj", "bhagwan", "kali", "dham", "tirth", "kshetra",
        "visit", "want", "plan", "going", "travel", "pilgrimage", "darshan",
        "sacred", "divine", "great", "holy",
    }

    # --- Pass 1: exact name match ---
    for entry in _ALL_TEMPLES:
        if entry["name"].lower() == text_lower:
            return entry

    # --- Pass 2: user input is fully inside a temple name ---
    for entry in _ALL_TEMPLES:
        if text_lower in entry["name"].lower():
            return entry

    # --- Pass 3: temple name is fully inside user input ---
    for entry in _ALL_TEMPLES:
        if entry["name"].lower() in text_lower:
            return entry

    # --- Pass 4: keyword + location disambiguation ---
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
        # Try to narrow down using location words from the user's message
        for entry in candidates:
            loc_words = [w for w in entry["location"].lower().split()
                         if len(w) > 3]
            if loc_words and any(w in text_lower for w in loc_words):
                return entry
        # If still ambiguous, return the first candidate
        return candidates[0]

    return None



# ---------------------------------------------------
# LLM CALL
# ---------------------------------------------------

def call_llm(query, history, booking_data, intent="GENERAL", pending_question="", user_id=None):
    """
    Calls the Groq LLM with a fully-built prompt.
    Returns the AI's response as a string.
    Always responds in English only.

    pending_question: if set, the LLM is instructed to answer the user's question
    and then re-ask this question at the end (used when user asks a question
    mid data-collection flow).

    user_id: if provided, used to set social_proof_used flag after first mention.

    Retries up to 3 times on Groq 429 rate-limit errors with exponential backoff.
    """
    # Retrieve RAG context once (outside retry loop)
    try:
        from retriever import retrieve_docs
        context = retrieve_docs(query)
    except Exception:
        context = ""

    sales_instruction = get_sales_instruction(intent, booking_data)

    prompt = build_prompt(
        query=query,
        context=context,
        history=history,
        sales_instruction=sales_instruction,
        booking_data=booking_data,
        pending_question=pending_question
    )

    # --- Retry loop with exponential backoff for 429 rate-limit errors ---
    max_retries  = 3
    backoff_secs = 5   # 5s → 10s → 20s

    for attempt in range(max_retries):
        try:
            response = llm.invoke(prompt)
            text = response.content.strip()

            # --- Social proof usage tracking ---
            # If the response mentions social proof for the first time, lock it.
            # This is deterministic — no reliance on LLM scanning history.
            if user_id and not booking_data.get("social_proof_used", False):
                social_proof_markers = ["40 lakh", "4.7", "lakh devotees", "lakh+ devotees"]
                if any(marker in text for marker in social_proof_markers):
                    update_booking(user_id, "social_proof_used", True)

            return text

        except Exception as e:
            err_str = str(e)

            # 429 Rate Limit — wait and retry
            if "429" in err_str or "rate limit" in err_str.lower():
                if attempt < max_retries - 1:
                    wait = backoff_secs * (2 ** attempt)  # 5s, 10s, 20s
                    print(f"[call_llm] Rate limit hit (attempt {attempt + 1}). Retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                # All retries exhausted
                return (
                    "I'm experiencing high traffic right now. "
                    "Please send your message again in a moment — I'll be right with you. 🙏"
                )

            # Any other error — fail immediately
            err_msg = err_str[:80]
            print(f"[call_llm] Non-rate-limit error: {err_msg}")
            return f"A technical issue occurred. Please try again. ({err_msg[:60]})"

    # Should never reach here
    return "Something went wrong. Please try again."


# ---------------------------------------------------
# MAIN RESPONSE GENERATOR
# ---------------------------------------------------

def generate_response(query, history, user_id):

    booking = get_booking(user_id)
    current_state = get_state(user_id)

    if not current_state:
        set_state(user_id, "GREETING")
        current_state = "GREETING"

    increment_message_count(user_id)

    query_stripped = query.strip()

    # ---------------------------------------------------
    # STATE: GREETING — detect temple
    # ---------------------------------------------------

    if current_state == "GREETING":

        temple_entry = detect_temple(query_stripped)

        if temple_entry:
            temple_name     = temple_entry["name"]
            temple_location = temple_entry.get("location", "")
            update_booking(user_id, "temple", temple_name)
            update_booking(user_id, "temple_location", temple_location)
            set_state(user_id, "ASK_DATE")
            location_str = f", {temple_location}" if temple_location else ""
            return f"Wonderful 🙏 {temple_name}{location_str} is a truly divine experience. Which date are you planning to travel?"

        # Temple not found — check if user seems to have typed a temple name
        greetings = {"hi", "hello", "hey", "namaste", "hii", "helo", "good morning", "good evening"}
        if query_stripped.lower() not in greetings:
            return (
                "🙏 Thank you for your interest. Unfortunately, we do not currently offer VIP Darshan services for this temple.\n\n"
                "We are continuously expanding our services to include more temples. "
                "If you are planning to visit another temple, I'd be happy to help you explore the available options."
            )

        # Generic greeting or unclear input — ask warmly
        return "🙏 Jai Shri Ram! Welcome to Naman Darshan. This is Priya speaking. Which temple are you planning to visit?"

    # ---------------------------------------------------
    # STATE: ASK_DATE — collect travel date
    # ---------------------------------------------------

    elif current_state == "ASK_DATE":

        # If user is asking a question instead of providing a date — answer it first
        if is_question_or_objection(query_stripped):
            intent  = detect_user_intent(query_stripped)
            pending = get_pending_question("ASK_DATE")
            booking = get_booking(user_id)
            return call_llm(query_stripped, history, booking, intent, pending_question=pending, user_id=user_id)

        update_booking(user_id, "date", query_stripped)
        set_state(user_id, "ASK_PEOPLE")
        return "How many people will be travelling?"

    # ---------------------------------------------------
    # STATE: ASK_PEOPLE — collect group size
    # ---------------------------------------------------

    elif current_state == "ASK_PEOPLE":

        # If user is asking a question instead of providing a number — answer it first
        if is_question_or_objection(query_stripped):
            intent  = detect_user_intent(query_stripped)
            pending = get_pending_question("ASK_PEOPLE")
            booking = get_booking(user_id)
            return call_llm(query_stripped, history, booking, intent, pending_question=pending, user_id=user_id)

        people = extract_people_count(query_stripped)

        if people:
            update_booking(user_id, "people", people)
            set_state(user_id, "ASK_ELDERLY")
            return "Will there be any elderly members or children in the group?"

        # Could not parse a number — ask clearly
        return "How many people will be travelling? Just send the number — e.g. '4' or '4 people'."

    # ---------------------------------------------------
    # STATE: ASK_ELDERLY — detect elderly/children
    # ---------------------------------------------------

    elif current_state == "ASK_ELDERLY":

        # If user is asking a question instead of answering yes/no — answer it first
        if is_question_or_objection(query_stripped):
            intent  = detect_user_intent(query_stripped)
            pending = get_pending_question("ASK_ELDERLY")
            booking = get_booking(user_id)
            return call_llm(query_stripped, history, booking, intent, pending_question=pending, user_id=user_id)

        elderly = detect_elderly(query_stripped)

        # If clearly 'no', also update
        if not elderly and detect_no(query_stripped):
            elderly = False

        update_booking(user_id, "elderly", elderly)
        set_state(user_id, "ASK_QUALIFICATION")

        # Ask the travel qualification question (Step 5 of sales flow)
        return "Are you travelling from the local area or from another state?"

    # ---------------------------------------------------
    # STATE: ASK_QUALIFICATION — Step 5: qualify the devotee
    # ---------------------------------------------------

    elif current_state == "ASK_QUALIFICATION":

        # If user is asking a question instead of answering — answer it first
        if is_question_or_objection(query_stripped):
            intent  = detect_user_intent(query_stripped)
            pending = get_pending_question("ASK_QUALIFICATION")
            booking = get_booking(user_id)
            return call_llm(query_stripped, history, booking, intent, pending_question=pending, user_id=user_id)

        # Store the answer and move to service intro
        update_booking(user_id, "qualification", query_stripped)
        set_state(user_id, "SERVICE_INTRO")

        # Refresh booking data after update
        booking = get_booking(user_id)

        # Trigger soft service introduction (Step 6) — no phone ask yet.
        # IMPORTANT: pass an empty internal query (not the user's raw answer like "Another state")
        # so the LLM has nothing to echo back. The booking_data already carries the qualification info.
        return call_llm("", history, booking, "SERVICE_INTRO", user_id=user_id)


    # ---------------------------------------------------
    # STATE: SERVICE_INTRO — Step 6: soft intro, then move to NORMAL_CHAT
    # ---------------------------------------------------

    elif current_state == "SERVICE_INTRO":

        # User replied to service intro — move to full LLM chat
        set_state(user_id, "NORMAL_CHAT")
        booking = get_booking(user_id)
        intent = detect_user_intent(query_stripped)
        return call_llm(query_stripped, history, booking, intent, user_id=user_id)

    # ---------------------------------------------------
    # STATE: NORMAL_CHAT — full LLM-powered responses
    # ---------------------------------------------------

    else:
        # Detect what the user is asking/objecting about
        intent = detect_user_intent(query_stripped)

        # Check if user is providing their name/phone (booking close)
        booking_data = get_booking(user_id)

        # --- PRICE_REPEAT routing ---
        # If PRICE intent and user has already asked about pricing before,
        # route to the softer PRICE_REPEAT response
        if intent == "PRICE":
            price_count = booking_data.get("price_asked_count", 0)
            update_booking(user_id, "price_asked_count", price_count + 1)
            if price_count >= 1:
                intent = "PRICE_REPEAT"

        # --- Progressive lead capture: collect name passively ---
        # If name not yet captured, message looks like a name response
        # (short, alpha-only, after enough conversation)
        if (
            booking_data.get("customer_name") is None
            and booking_data.get("message_count", 0) > 6
            and len(query_stripped.split()) <= 4
            and query_stripped.replace(" ", "").isalpha()
        ):
            captured_name = query_stripped.title()
            update_booking(user_id, "customer_name", captured_name)
            update_booking(user_id, "name_asked", True)
            # Return direct response — no LLM needed, prevents re-asking
            return (
                f"Thank you, {captured_name}! "
                f"Which WhatsApp number should we send the booking details to?"
            )

        # --- Progressive lead capture: collect phone passively ---
        # If name collected but phone not yet, and message looks like a phone number
        elif (
            booking_data.get("customer_name") is not None
            and booking_data.get("phone") is None
            and len(query_stripped.replace(" ", "").replace("+", "").replace("-", "")) >= 10
            and query_stripped.replace(" ", "").replace("+", "").replace("-", "").isdigit()
        ):
            captured_name = booking_data.get("customer_name", "")
            update_booking(user_id, "phone", query_stripped.strip())
            update_booking(user_id, "phone_asked", True)
            # Return direct confirmation — no LLM needed, prevents re-asking for phone
            return (
                f"Perfect, {captured_name}! 🙏 Our representative will call you shortly "
                f"to explain the details and confirm your slot. "
                f"Looking forward to a smooth and peaceful darshan for you."
            )

        # Route to LLM with the right intent guidance
        return call_llm(query_stripped, history, get_booking(user_id), intent, user_id=user_id)