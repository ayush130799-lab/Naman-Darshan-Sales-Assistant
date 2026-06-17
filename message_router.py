# message_router.py
# Central routing layer — classifies every user message and decides what to do
# BEFORE the booking state machine processes it.
#
# The key invariant:
#   - Booking state is NEVER modified during ANSWER_AND_RESUME or HUMAN_HANDOFF.
#   - State only advances during CONTINUE_FLOW (normal booking flow).
#
# Action types returned:
#   CONTINUE_FLOW    — pass message through to normal booking state machine
#   ANSWER_AND_RESUME — answer the question, then re-ask the pending booking question
#   OBJECTION        — handle as sales objection (LLM with objection prompt)
#   HUMAN_HANDOFF    — user wants a human agent; create handoff record

from intent_classifier import classify_intent
from booking_flow import get_booking, get_state

# --------------------------------------------------
# Sub-intents that ALWAYS route to ANSWER_AND_RESUME
# regardless of what the LLM primary classifier returns.
# These are all question/info patterns — the LLM sometimes
# misclassifies them as BOOKING_INFO because they mention 'temple'.
# --------------------------------------------------
_ALWAYS_INFORMATION = {
    "TEMPLE_LIST",        # 'Which temples do you cover?' / 'temples in Tamil Nadu'
    "PUJA_LIST",          # 'Which pujas are listed?' / 'pujas available'
    "PACKAGE_DISCOVERY",  # 'Which temple is best in June?' / 'best yatra for me'
    "TRAVEL_PLANNING",    # 'What documents do I need?' / 'best time to visit'
    "ELDERLY_SUPPORT",    # 'Is it suitable for elderly?'
    "SAFETY",             # 'Is it safe for women?'
    "COORDINATOR",        # 'Will someone guide us?'
    "LANGUAGE_SUPPORT",   # 'Do you assist in Hindi?'
    "TIMINGS",            # 'What are the darshan timings?'
    "BENEFITS",           # 'What is assisted darshan?'
    "BOOKING_PROCESS",    # 'How does booking work?'
    "AVAILABILITY",       # 'Are slots available?'
}

# --------------------------------------------------
# States where we're actively collecting structured data
# that should trigger ANSWER_AND_RESUME behaviour
# --------------------------------------------------
_DATA_COLLECTION_STATES = {
    "GREETING",
    "ASK_DATE",
    "ASK_PEOPLE",
    "ASK_ELDERLY",
    "ASK_QUALIFICATION",
}



# --------------------------------------------------
# Sub-intents that are sales objections and should
# ALWAYS route to objection handling regardless of primary classification
# --------------------------------------------------
_OBJECTION_SUB_INTENTS = {
    "TRUST", "COMPANY_NAME", "GST", "PRICE", "PRICE_REPEAT",
    "OFFICIAL", "DELAY", "GUARANTEE", "CANCELLATION_PLAN",
}


def route_message(query: str, history: list, user_id: str) -> dict:
    """
    Classify the user message and return a routing action dict.

    Returns:
        {
          "action":          "CONTINUE_FLOW" | "ANSWER_AND_RESUME" | "OBJECTION" | "HUMAN_HANDOFF",
          "primary_intent":  str,
          "sub_intent":      str,
          "resume_question": str | None,   # Set for ANSWER_AND_RESUME
          "booking":         dict,         # Current booking snapshot
        }
    """
    current_state = get_state(user_id)
    booking       = get_booking(user_id)

    classification = classify_intent(query, current_state)
    primary    = classification["primary"]
    sub_intent = classification["sub_intent"]

    # --------------------------------------------------
    # 1. Human agent request — always highest priority
    # --------------------------------------------------
    if primary == "HUMAN_AGENT" or sub_intent == "HUMAN_AGENT":
        from human_handoff import create_handoff_record
        create_handoff_record(user_id, booking)
        return _make_result("HUMAN_HANDOFF", primary, sub_intent, booking)

    # --------------------------------------------------
    # 2. HARDCODED override — these sub_intents are ALWAYS
    #    information requests, checked BEFORE objection detection.
    #    Reason: keyword classifier tags "Is Kedarnath safe?" as TRUST
    #    (because "safe" appears in trust keywords), but it's clearly
    #    an information question. The _ALWAYS_INFORMATION set wins.
    # --------------------------------------------------
    if sub_intent in _ALWAYS_INFORMATION:
        return _make_result("ANSWER_AND_RESUME", "INFORMATION_REQUEST", sub_intent, booking)

    # --------------------------------------------------
    # 3. Sales objections — genuine trust/price/fraud concerns.
    #    NOTE: We only use keyword sub_intent as an override when the
    #    LLM has NOT said INFORMATION_REQUEST. This prevents
    #    'Is Kedarnath safe in July?' (LLM→INFO, keyword→TRUST)
    #    from being misrouted to objection handling.
    #    But 'Is payment safe? Is it fraud?' (LLM→OBJECTION, keyword→TRUST)
    #    still correctly routes to objection handling.
    # --------------------------------------------------
    _keyword_objection = sub_intent in _OBJECTION_SUB_INTENTS and primary != "INFORMATION_REQUEST"
    if primary == "SALES_OBJECTION" or _keyword_objection:
        return _make_result("OBJECTION", primary, sub_intent, booking)

    # --------------------------------------------------
    # 4. Information requests (from LLM classifier)
    # --------------------------------------------------
    if primary == "INFORMATION_REQUEST":
        return _make_result("ANSWER_AND_RESUME", primary, sub_intent, booking)

    # --------------------------------------------------
    # 5. CHITCHAT — pass to normal flow
    # --------------------------------------------------
    if primary == "CHITCHAT":
        return _make_result("CONTINUE_FLOW", primary, sub_intent, booking)

    # --------------------------------------------------
    # 6. BOOKING_INFO or anything else → continue normal flow
    # --------------------------------------------------
    return _make_result("CONTINUE_FLOW", primary, sub_intent, booking)



def _make_result(
    action: str,
    primary_intent: str,
    sub_intent: str,
    booking: dict,
    resume_question: str | None = None,
) -> dict:
    """Helper to build a consistent result dict."""
    return {
        "action":          action,
        "primary_intent":  primary_intent,
        "sub_intent":      sub_intent,
        "resume_question": resume_question,
        "booking":         booking,
    }
