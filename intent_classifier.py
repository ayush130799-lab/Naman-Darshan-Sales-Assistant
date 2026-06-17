# intent_classifier.py
# LLM-based intent classifier — classifies every user message into 5 primary categories.
# Uses llama-3.1-8b-instant (fast, cheap) for classification.
# Falls back to keyword-based sales_logic.detect_user_intent() on any error.

from langchain_groq import ChatGroq
from config import GROQ_API_KEY
from sales_logic import detect_user_intent as keyword_classify

# --------------------------------------------------
# Classifier LLM — smallest/fastest Groq model
# Temperature=0 for deterministic classification
# max_tokens=20 — only needs to output one word
# --------------------------------------------------
_classifier_llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.0,
    max_tokens=20,
    api_key=GROQ_API_KEY
)

_INTENT_PROMPT = """You are a message classifier for a temple assisted darshan booking chatbot.

Classify the user's message into EXACTLY ONE of these categories:
- BOOKING_INFO: User is GIVING data needed for booking (saying a specific temple name to book, giving a date, giving a number of people, answering yes/no to elderly question)
- INFORMATION_REQUEST: User is ASKING a question about temples, travel recommendations, seasonal info, which temple to visit, accessibility, timings, documents, dress code, or general information
- SALES_OBJECTION: User has a CONCERN about payment fraud, company legitimacy, GST, price being too high, cancellation policy, or wants a refund
- CHITCHAT: Small talk, greetings, expressions of thanks
- HUMAN_AGENT: User explicitly wants to speak with a human representative

IMPORTANT RULES:
- 'Which temple is best?' or 'Which temple in July?' = INFORMATION_REQUEST (asking for recommendation)
- 'Is it safe for women?' or 'Is Kedarnath safe?' = INFORMATION_REQUEST (asking for information)
- 'I want to visit Tirupati' = BOOKING_INFO (naming a specific temple to book)
- 'Is it real or fraud?' or 'Is payment safe?' = SALES_OBJECTION (payment/trust concern)
- 'Are you safe to book from?' = SALES_OBJECTION (trust concern about the company)

Current booking flow state: {state}
User message: "{message}"

Respond with ONLY the category name. No explanation. No punctuation."""



# --------------------------------------------------
# Map of keyword-based sub_intents → primary categories
# Used as the fallback when LLM call fails
# --------------------------------------------------
_SUB_TO_PRIMARY = {
    # SALES_OBJECTION
    "TRUST":              "SALES_OBJECTION",
    "PRICE":              "SALES_OBJECTION",
    "PRICE_REPEAT":       "SALES_OBJECTION",
    "GUARANTEE":          "SALES_OBJECTION",
    "OFFICIAL":           "SALES_OBJECTION",
    "GST":                "SALES_OBJECTION",
    "COMPANY_NAME":       "SALES_OBJECTION",
    "DELAY":              "SALES_OBJECTION",
    "CANCELLATION_PLAN":  "SALES_OBJECTION",
    "AVAILABILITY":       "SALES_OBJECTION",

    # HUMAN_AGENT
    "HUMAN_AGENT":        "HUMAN_AGENT",

    # BOOKING_INFO
    "BOOKING":            "BOOKING_INFO",
    "CLOSE":              "BOOKING_INFO",
    "SEND_DETAILS":       "BOOKING_INFO",

    # INFORMATION_REQUEST
    "BOOKING_PROCESS":    "INFORMATION_REQUEST",
    "BENEFITS":           "INFORMATION_REQUEST",
    "COORDINATOR":        "INFORMATION_REQUEST",
    "ELDERLY_SUPPORT":    "INFORMATION_REQUEST",
    "SAFETY":             "INFORMATION_REQUEST",
    "TRAVEL_PLANNING":    "INFORMATION_REQUEST",
    "LANGUAGE_SUPPORT":   "INFORMATION_REQUEST",
    "TIMINGS":            "INFORMATION_REQUEST",
    "TEMPLE_LIST":        "INFORMATION_REQUEST",
    "PACKAGE_DISCOVERY":  "INFORMATION_REQUEST",
    "PAYMENT_METHOD":     "INFORMATION_REQUEST",
    "PAYMENT_TIMING":     "INFORMATION_REQUEST",

    # CHITCHAT
    "GENERAL":            "CHITCHAT",
}

_VALID_PRIMARY_INTENTS = {
    "BOOKING_INFO", "INFORMATION_REQUEST", "SALES_OBJECTION", "CHITCHAT", "HUMAN_AGENT"
}


def classify_intent(message: str, current_state: str = "GREETING") -> dict:
    """
    Classifies a user message into a primary intent category.

    Returns:
        dict with keys:
          - "primary"    : one of the 5 primary categories
          - "sub_intent" : fine-grained keyword-based category (from sales_logic.py)
    
    The sub_intent is always set from the keyword classifier for backward compatibility
    with existing prompt_builder.get_sales_instruction() routing.
    """
    # Always compute sub_intent via keyword classifier (fast, no API call)
    sub_intent = keyword_classify(message)

    # Attempt LLM-based primary classification
    try:
        prompt = _INTENT_PROMPT.format(state=current_state, message=message)
        result = _classifier_llm.invoke(prompt)

        # Guard: empty response from Groq
        content = (result.content or "").strip()
        if not content:
            raise ValueError("Empty response from classifier LLM")

        primary = content.upper().split()[0].rstrip(".").rstrip(",")

        if primary not in _VALID_PRIMARY_INTENTS:
            # LLM returned something unexpected — fall back to keyword map
            primary = _map_sub_to_primary(sub_intent)

    except Exception as e:
        print(f"[intent_classifier] LLM error, using keyword fallback: {e}")
        primary = _map_sub_to_primary(sub_intent)

    return {"primary": primary, "sub_intent": sub_intent}



def _map_sub_to_primary(sub_intent: str) -> str:
    """Maps keyword-based sub_intent → primary category using the lookup table."""
    return _SUB_TO_PRIMARY.get(sub_intent, "INFORMATION_REQUEST")
