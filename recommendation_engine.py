# recommendation_engine.py
# Answers temple recommendation questions using RAG (FAISS vectorstore) + LLM reasoning.
# The vectorstore contains rich seasonal, regional, and accessibility knowledge
# built by build_knowledge_base.py.
#
# Handles queries like:
#   "Which temple is best in June?"         → RAG retrieves June seasonal guide
#   "Which temples in Tamil Nadu?"          → RAG retrieves Tamil Nadu regional guide
#   "Which temple is best for elderly?"     → RAG retrieves accessibility guide
#   "Which Jyotirlinga should I visit first?" → RAG retrieves Jyotirlinga guide
#   "Which temple is good in monsoon?"      → RAG retrieves monsoon guide

from langchain_groq import ChatGroq
from config import GROQ_API_KEY, MONGO_URI
from pymongo import MongoClient

_rec_llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.5,   # Lower temperature = more factual, less hallucination
    max_tokens=500,
    api_key=GROQ_API_KEY
)

_RECOMMENDATION_PROMPT = """You are a knowledgeable temple travel expert at Naman Darshan — India's assisted Temple Darshan service.

A devotee is asking for a temple recommendation. Use the SEASONAL/REGIONAL KNOWLEDGE BASE below to give a SPECIFIC, ACCURATE recommendation. 

CRITICAL RULE: Your recommendation MUST be based on the SEASONAL/REGIONAL KNOWLEDGE BASE provided below. 
Do NOT ignore the seasonal context. If the user asks about monsoon, recommend temples specifically suited for monsoon.
If they ask about summer, recommend temples suited for summer. These should be DIFFERENT answers.

CRITICAL DEITY MATCHING RULE: If the devotee asks about temples dedicated to or best for a specific deity (e.g. Lord Shiva, Lord Krishna, Lord Ram, Lord Vishnu, Lord Ganesha, Goddess Durga/Shakti, Sai Baba, etc.), you MUST only recommend/mention temples associated with that specific deity. Never mix or include temples of unrelated deities in your response. For example, if they ask about Lord Shiva, you can recommend Kashi Vishwanath, Mahakaleshwar, Kedarnath, Somnath, Omkareshwar, Trimbakeshwar, Nageshwar, or Bhimashankar, but you must NEVER include or recommend Shirdi Sai Baba (saint/guru, not Shiva), Tirupati Balaji (Vishnu), Ayodhya Ram Mandir (Ram), or Siddhivinayak (Ganesha).

SEASONAL/REGIONAL KNOWLEDGE BASE (use this as your primary source):
{rag_context}

AVAILABLE TEMPLES (Naman Darshan offers assisted Darshan at these):
{temples_data}

DEVOTEE CONTEXT:
- Temple already selected: {selected_temple}
- Travel date / month: {date}
- Group size: {people}
- Elderly / children in group: {elderly}

RECENT CONVERSATION:
{history}

DEVOTEE'S QUESTION: {query}

PENDING QUESTION: {pending_question}

Instructions:
- If the user is asking about the total count or number of temples/packages we offer, look at the "Total Active Yatra Packages Available" count under AVAILABLE TEMPLES. You MUST state the exact number (69) and mention that Naman Darshan covers 69 sacred temples/abodes across India. Do NOT say "50+" if the exact count is 69.
- Base your answer STRICTLY on the SEASONAL/REGIONAL KNOWLEDGE BASE above
- Recommend 2-3 specific temples with clear reasons tied to the season/region/requirement
- For MONSOON: avoid hill temples (Kedarnath, Badrinath, Vaishno Devi — landslide risk), recommend plains/city temples
- For SUMMER (May-June): hill temples (Kedarnath, Badrinath) are actually good; plains are hot; South India is very hot
- For WINTER (Dec-Feb): South India excellent, hill temples closed
- For ELDERLY: flat terrain temples (Shirdi, Siddhivinayak, Golden Temple, Kashi Vishwanath)
- For TAMIL NADU: Meenakshi Amman Madurai is the primary recommendation
- Mention WHY each temple is good for that specific season/need
- Keep it under 120 words, specific and helpful
- End of Response:
  - If a PENDING QUESTION is provided above (not "None"), you MUST naturally transition to asking for that information (rephrase the pending question to fit context) at the very end of your response, rather than asking a generic question.
  - If no pending question is provided (e.g. "None"), end with a soft question like "Which of these interests you most?" or similar."""


def get_recommendation(query: str, history: list, booking: dict, pending_question: str = None) -> str:
    """
    Generate a season/region-aware temple recommendation using:
    1. FAISS vectorstore RAG (seasonal/regional knowledge)
    2. MongoDB temple list (available temples)
    3. LLM reasoning (generate natural language response)
    """
    # Step 1: Retrieve seasonal/regional context from FAISS vectorstore
    rag_context = _retrieve_seasonal_context(query)

    # Step 2: Load temple names from MongoDB
    temples_data = _load_temple_metadata()

    # Step 3: Format history
    formatted_history = _format_history(history[-4:])

    # Step 4: Build and call LLM with RAG context
    prompt = _RECOMMENDATION_PROMPT.format(
        rag_context=rag_context,
        temples_data=temples_data,
        selected_temple=booking.get("temple") or "Not selected yet",
        date=booking.get("date") or "Not specified",
        people=booking.get("people") or "Not specified",
        elderly="Yes" if booking.get("elderly") else "No",
        history=formatted_history,
        query=query,
        pending_question=pending_question or "None",
    )

    try:
        response = _rec_llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        print(f"[recommendation_engine] LLM error: {e}")
        return _fallback_recommendation(query)


def _retrieve_seasonal_context(query: str) -> str:
    """
    Retrieves relevant seasonal/regional knowledge from the FAISS vectorstore.
    This is the key fix — the vectorstore has month-by-month seasonal guides,
    state-wise regional guides, accessibility guides, etc.
    """
    try:
        from retriever import retrieve_docs

        # Build a context-rich query for better retrieval
        enriched_query = _enrich_query(query)
        context = retrieve_docs(enriched_query)

        if context and len(context.strip()) > 50:
            return context
        return "No specific seasonal context retrieved."
    except Exception as e:
        print(f"[recommendation_engine] RAG retrieval error: {e}")
        return _get_fallback_context(query)


def _enrich_query(query: str) -> str:
    """
    Adds keywords to the retrieval query to help find the right vectorstore chunks.
    E.g. 'monsoon' → 'monsoon season July August temples safe accessible'
    """
    q = query.lower()
    enrichments = []

    # Season keywords
    if any(w in q for w in ["monsoon", "rainy", "rain", "july", "august"]):
        enrichments.append("monsoon July August temples accessible avoid landslide")
    elif any(w in q for w in ["summer", "may", "june", "april", "hot"]):
        enrichments.append("summer May June temples best accessible hill station")
    elif any(w in q for w in ["winter", "december", "january", "february", "cold"]):
        enrichments.append("winter December January South India temples accessible")
    elif any(w in q for w in ["october", "november", "navratri", "dussehra"]):
        enrichments.append("October November post-monsoon excellent temples")

    # Regional keywords
    if any(w in q for w in ["tamil nadu", "south india", "chennai", "madurai"]):
        enrichments.append("Tamil Nadu South India temples state regional guide")
    elif any(w in q for w in ["gujarat", "rajasthan", "western"]):
        enrichments.append("Gujarat Rajasthan western India temples jyotirlinga")
    elif any(w in q for w in ["uttarakhand", "char dham", "kedarnath", "badrinath"]):
        enrichments.append("Uttarakhand Char Dham seasonal guide open months")
    elif any(w in q for w in ["kerala", "karnataka", "south"]):
        enrichments.append("South India Kerala Karnataka temples")

    # Accessibility keywords
    if any(w in q for w in ["elderly", "old", "senior", "parents", "wheelchair"]):
        enrichments.append("elderly accessible flat terrain wheelchair senior citizens")

    # Jyotirlinga / Char Dham
    if any(w in q for w in ["jyotirlinga", "jyotirling", "shiva", "lingam"]):
        enrichments.append("12 jyotirlinga guide circuit first visit")
    if any(w in q for w in ["char dham", "chardham", "chota char dham"]):
        enrichments.append("Char Dham Yatra guide season months")

    base = f"{query} temple seasonal guide India"
    if enrichments:
        base += " " + " ".join(enrichments)
    return base


def _get_fallback_context(query: str) -> str:
    """Hard-coded seasonal context when vectorstore is unavailable."""
    q = query.lower()

    if any(w in q for w in ["monsoon", "rainy", "july", "august"]):
        return """JULY-AUGUST MONSOON GUIDE:
AVOID: Kedarnath (landslides), Badrinath (heavy rain), Vaishno Devi (slippery), Yamunotri, Gangotri.
BEST FOR MONSOON: Shirdi Sai Baba (Maharashtra, flat, accessible), Kashi Vishwanath (Varanasi, city temple), 
Jagannath Puri (Rath Yatra happens in July - major festival), Mahakaleshwar Ujjain (city temple),
Tirupati Balaji (South India, accessible), Meenakshi Amman (Madurai, covered temple).
July special: Jagannath Puri Rath Yatra is a once-in-a-lifetime festival experience."""

    if any(w in q for w in ["summer", "may", "june", "april"]):
        return """MAY-JUNE SUMMER GUIDE:
BEST: Kedarnath (opens May, best before monsoon), Badrinath (open Apr-Nov), Vaishno Devi (pleasant).
FOR PLAINS SUMMER: Shirdi, Kashi Vishwanath, Mahakaleshwar Ujjain are accessible but hot.
AVOID: Tirupati in summer (very hot at base); South India plains are very hot.
HILL TEMPLES EXCELLENT: Kedarnath, Badrinath, Vaishno Devi - cool and open in May-June."""

    if any(w in q for w in ["winter", "december", "january", "february"]):
        return """DECEMBER-FEBRUARY WINTER GUIDE:
BEST: South India temples - Tirupati Balaji (most pleasant weather), Meenakshi Amman Madurai.
EXCELLENT: Shirdi Sai Baba, Golden Temple Amritsar (Lohri festival), Somnath Gujarat, Dwarka.
CLOSED: Kedarnath, Badrinath, Yamunotri, Gangotri (all closed in winter)."""

    if any(w in q for w in ["tamil", "south india"]):
        return """TAMIL NADU / SOUTH INDIA TEMPLES:
Primary: Meenakshi Amman Temple (Madurai) - spectacular Dravidian architecture.
Also: Kapaleeshwarar (Chennai), Brihadeeswarar (Thanjavur).
Best season: October to March. Avoid summer (very hot)."""

    return "Temple recommendation guide: Tirupati Balaji, Kashi Vishwanath, Shirdi Sai Baba, Vaishno Devi, Kedarnath (seasonal), Badrinath (seasonal), Mahakaleshwar, Ram Mandir Ayodhya."


def _fallback_recommendation(query: str) -> str:
    """Simple fallback answer when LLM is unavailable."""
    q = query.lower()

    if any(w in q for w in ["monsoon", "rainy", "july", "august"]):
        return (
            "For monsoon visits, I'd recommend Shirdi Sai Baba (fully covered, flat terrain), "
            "Kashi Vishwanath (Varanasi city temple), and Mahakaleshwar Ujjain — all safe and accessible during rains. "
            "Avoid Kedarnath, Badrinath, and Vaishno Devi in July-August due to landslide risk. "
            "If July, Jagannath Puri's Rath Yatra is a special once-in-a-lifetime experience. "
            "Which of these interests you most?"
        )
    if any(w in q for w in ["summer", "may", "june"]):
        return (
            "For summer, Kedarnath and Badrinath are actually excellent (cool, open May-June before monsoon). "
            "If you prefer plains temples: Shirdi Sai Baba and Kashi Vishwanath are accessible. "
            "Avoid South India in summer as it gets very hot. "
            "Which of these interests you most?"
        )
    if any(w in q for w in ["winter", "december", "january", "february"]):
        return (
            "For winter, South India is ideal — Tirupati Balaji and Meenakshi Amman (Madurai) have pleasant weather. "
            "Golden Temple Amritsar is beautiful in winter. "
            "Note: Kedarnath and Badrinath are closed in winter (open May-November only). "
            "Which of these interests you most?"
        )
    if any(w in q for w in ["elderly", "old", "parents", "senior"]):
        return (
            "For elderly devotees, I'd suggest Shirdi Sai Baba (flat campus, most accessible), "
            "Tirupati Balaji (assisted darshan minimises walking), and Ram Mandir Ayodhya (new modern facilities). "
            "All three have minimal trekking and are managed well for senior citizens. "
            "Which would suit your family best?"
        )
    if any(w in q for w in ["tamil", "karnataka", "south"]):
        return (
            "For South India, Meenakshi Amman Temple (Madurai) is the top recommendation — "
            "spectacular Dravidian architecture and one of India's most sacred temples. "
            "Best visited October to March. Which of these interests you?"
        )
    return (
        "Our most visited temples are Tirupati Balaji, Kashi Vishwanath, Vaishno Devi, "
        "Shirdi Sai Baba, and Ram Mandir Ayodhya. Could you tell me which month you plan to travel "
        "or what kind of experience you're looking for? That will help me give a better recommendation."
    )


def _load_temple_metadata() -> str:
    """Load temple names + locations from MongoDB for LLM context."""
    try:
        client = MongoClient(
            MONGO_URI,
            tls=True,
            tlsAllowInvalidCertificates=True,
            serverSelectionTimeoutMS=3000,
        )
        db = client["temples_clone"]
        
        # Load all active yatra packages (authorized temples)
        temples = list(
            db.Yatra_packages.find(
                {"active": True},
                {"temple_name": 1, "location": 1, "city": 1, "_id": 0}
            )
        )
        total_count = len(temples)
        
        if not temples:
            # Fall back to hardcoded count of 50+ and list
            return f"Total Active Yatra Packages: 50+\n\nList of Supported Abodes:\n{_FALLBACK_TEMPLE_LIST}"

        lines = [f"Total Active Yatra Packages Available: {total_count}", "\nList of Supported Abodes:"]
        for t in temples:
            name = (t.get("temple_name") or "").strip()
            loc  = (t.get("location") or t.get("city") or "").strip()
            if name:
                lines.append(f"- {name}" + (f" ({loc})" if loc else ""))

        return "\n".join(lines)

    except Exception as e:
        print(f"[recommendation_engine] MongoDB error: {e}")
        return f"Total Active Yatra Packages: 50+\n\nList of Supported Abodes:\n{_FALLBACK_TEMPLE_LIST}"


_FALLBACK_TEMPLE_LIST = """
- Tirupati Balaji Temple (Tirumala, Andhra Pradesh) — open year round
- Ayodhya Ram Mandir (Uttar Pradesh) — open year round
- Kashi Vishwanath (Varanasi, UP) — open year round
- Shri Mata Vaishno Devi (Katra, J&K) — open year round (avoid July-Aug monsoon)
- Kedarnath Dham (Uttarakhand) — OPEN MAY TO NOVEMBER ONLY
- Badrinath Temple (Uttarakhand) — OPEN APRIL TO NOVEMBER ONLY
- Mahakaleshwar (Ujjain, MP) — open year round
- Somnath Temple (Gujarat) — open year round
- Shirdi Sai Baba Temple (Maharashtra) — open year round, BEST FOR ELDERLY
- Puri Jagannath (Odisha) — open year round, RATH YATRA IN JULY
- Dwarkadhish (Gujarat) — open year round
- Meenakshi Amman Darshan (Madurai, Tamil Nadu) — open year round
- Golden Temple Amritsar (Punjab) — open 24/7, wheelchair accessible
- Kamakhya Temple (Guwahati, Assam) — best Oct-Apr
"""


def _format_history(history: list) -> str:
    if not history:
        return "No previous conversation."
    return "\n".join(
        f"User: {h.get('user', '')}\nAssistant: {h.get('assistant', '')}"
        for h in history
    )
