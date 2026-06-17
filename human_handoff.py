# human_handoff.py
# Creates and manages human agent handoff records in MongoDB `human_handoffs` collection.
# Called when a user explicitly requests to speak with a real person.
# Preserves all current booking context and lead score at the moment of handoff.

from pymongo import MongoClient
from datetime import datetime
from config import MONGO_URI
from lead_scoring import compute_lead_score


def create_handoff_record(user_id: str, booking: dict) -> bool:
    """
    Creates a handoff record in the `human_handoffs` MongoDB collection.
    Sets `human_agent_requested` flag in booking state for lead scoring.

    Args:
        user_id: Unique user identifier
        booking: Current booking session dict

    Returns:
        True on success, False on failure
    """
    # Flag the booking session so lead score includes this strong signal
    from booking_flow import update_booking
    update_booking(user_id, "human_agent_requested", True)

    # Recompute booking after flag update
    booking_snapshot = dict(booking)
    booking_snapshot["human_agent_requested"] = True

    score = compute_lead_score(booking_snapshot, booking_snapshot.get("message_count", 0))

    record = {
        "user_id":                  user_id,
        "status":                   "PENDING",          # PENDING → ASSIGNED → RESOLVED
        "lead_score":               score,
        "temple":                   booking.get("temple"),
        "date":                     booking.get("date"),
        "people":                   booking.get("people"),
        "elderly":                  booking.get("elderly", False),
        "customer_name":            booking.get("customer_name"),
        "phone":                    booking.get("phone"),
        "qualification":            booking.get("qualification"),
        "booking_state_at_handoff": booking.get("state"),
        "message_count":            booking.get("message_count", 0),
        "created_at":               datetime.utcnow(),
    }

    try:
        client = MongoClient(
            MONGO_URI,
            tls=True,
            tlsAllowInvalidCertificates=True,
            serverSelectionTimeoutMS=4000,
        )
        db = client["temples_clone"]
        db.human_handoffs.insert_one(record)
        print(f"[human_handoff] Record created — user={user_id[:8]}... score={score}")
        return True
    except Exception as e:
        print(f"[human_handoff] Failed to create record: {e}")
        return False


def get_handoff_response(booking: dict) -> str:
    """
    Returns the appropriate bot response for a human handoff request.
    Progressive: if name+phone known → guide to booking; if name only → ask phone;
    if neither → ask both.
    """
    name      = booking.get("customer_name")
    has_name  = bool(name)
    has_phone = bool(booking.get("phone"))

    if has_name and has_phone:
        return (
            f"Absolutely, {name}! 🙏\n\n"
            "Once the required details are provided, I can help you proceed with the booking process. "
            "You can also reach our team directly at +91 93119 73199 or visit namandarshan.com."
        )

    if has_name:
        return (
            f"Absolutely, {name}! 🙏\n\n"
            "To help you proceed with the booking process, could you please share your WhatsApp number?"
        )

    return (
        "Absolutely! 🙏\n\n"
        "To help you proceed with the booking process, could you please share your name and WhatsApp number?"
    )


def list_pending_handoffs(limit: int = 20) -> list:
    """
    Returns a list of pending handoff records (for admin use).
    Sorted by lead_score descending — hottest leads first.
    """
    try:
        client = MongoClient(
            MONGO_URI,
            tls=True,
            tlsAllowInvalidCertificates=True,
            serverSelectionTimeoutMS=4000,
        )
        db = client["temples_clone"]
        records = list(
            db.human_handoffs
            .find({"status": "PENDING"}, {"_id": 0})
            .sort("lead_score", -1)
            .limit(limit)
        )
        return records
    except Exception as e:
        print(f"[human_handoff] list_pending error: {e}")
        return []
