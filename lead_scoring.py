# lead_scoring.py
# Computes a lead engagement score (0–100) based on booking funnel signals.
# Scores are stored in the conversation_sessions collection alongside the session.

from datetime import datetime


# --------------------------------------------------
# Score weights
# --------------------------------------------------
_WEIGHTS = {
    "temple":            20,   # Temple selected
    "date":              15,   # Travel date given
    "people":            10,   # Group size given
    "elderly":            5,   # Elderly/children mentioned (more context = warmer lead)
    "customer_name":     20,   # Name collected (strong trust signal)
    "phone":             20,   # Phone collected (ready to be contacted)
    "price_inquiry":      5,   # Asked about price (serious buyer signal)
    "human_agent":        5,   # Asked for human (very strong buying signal)
    "engaged_user":       5,   # 5+ messages (committed to conversation)
}


def compute_lead_score(booking: dict, message_count: int = 0) -> int:
    """
    Compute a lead score from 0 to 100 based on booking funnel data.

    Args:
        booking: The booking session dict from booking_flow.get_booking()
        message_count: Total messages exchanged

    Returns:
        Integer score 0–100
    """
    score = 0

    if booking.get("temple"):
        score += _WEIGHTS["temple"]
    if booking.get("date"):
        score += _WEIGHTS["date"]
    if booking.get("people"):
        score += _WEIGHTS["people"]
    if booking.get("elderly"):
        score += _WEIGHTS["elderly"]
    if booking.get("customer_name"):
        score += _WEIGHTS["customer_name"]
    if booking.get("phone"):
        score += _WEIGHTS["phone"]
    if booking.get("price_asked_count", 0) >= 1:
        score += _WEIGHTS["price_inquiry"]
    if booking.get("human_agent_requested", False):
        score += _WEIGHTS["human_agent"]
    if message_count >= 5:
        score += _WEIGHTS["engaged_user"]

    return min(score, 100)


def get_lead_tier(score: int) -> str:
    """
    Maps a numeric score to a human-readable lead tier.

    Returns: "HOT" | "WARM" | "COLD"
    """
    if score >= 65:
        return "HOT"
    if score >= 30:
        return "WARM"
    return "COLD"


def save_lead_score(user_id: str, booking: dict):
    """
    Compute and persist lead score to the conversation_sessions collection.
    This is called after every bot response so scores stay current.
    Uses session_store to avoid a second MongoDB connection.
    """
    from session_store import update_session_field

    message_count = booking.get("message_count", 0)
    score = compute_lead_score(booking, message_count)
    tier = get_lead_tier(score)

    update_session_field(user_id, "lead_score", score)
    update_session_field(user_id, "lead_tier", tier)

    return score


def get_lead_score(user_id: str) -> int:
    """Retrieve the stored lead score for a user."""
    from session_store import load_session
    session = load_session(user_id)
    if session:
        return session.get("lead_score", 0)
    return 0
