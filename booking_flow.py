# booking_flow.py
# Manages the assisted darshan booking session state for each user.
#
# v2 changes:
#   - In-memory dict (booking_sessions) is still the fast cache layer
#   - session_store.py (MongoDB) is the persistence layer that survives restarts
#   - initialize_booking() checks MongoDB first, so returning users recover their state
#   - Every state/field update is written through to MongoDB

import session_store

# In-memory cache (fast read access during active session)
booking_sessions: dict = {}


# --------------------------------------------------
# Default session schema — all fields a session may contain
# --------------------------------------------------
def _default_session(user_id: str) -> dict:
    return {
        "user_id":              user_id,
        "temple":               None,
        "temple_location":      None,
        "date":                 None,
        "people":               None,
        "elderly":              False,
        "qualification":        None,
        "customer_name":        None,
        "phone":                None,

        # Extended fields — auto-extracted from natural conversation
        "budget":               None,   # e.g. "5000", "under 10k"
        "puja":                 None,   # e.g. "Rudrabhishek", "Satyanarayan Puja"
        "puja_mode":            None,   # "online" or "offline" — set when customer specifies puja type
        "package_type":         None,   # e.g. "darshan", "yatra", "prasadam", "puja"
        "adults_count":         None,
        "children_count":       None,
        "senior_count":         None,
        "preferred_time":       None,
        "quantity":             None,
        "delivery_address":     None,
        "offering_type":        None,
        "darshan_type":         None,

        # Lead Stage & Intent tracking (synced to Customer_Profile collection)
        "lead_stage":           "form_not_filled",  # form_not_filled | form_filled_no_payment | payment_confirmed
        "current_intent":       "main_booking",     # main_booking | puja_booking | abhishekam_booking |
                                                    # prasadam_booking | chadhava_booking | darshan_booking |
                                                    # accommodation_booking | transportation_booking

        # Additional customer profile fields
        "departure_city":       None,   # Customer's city of departure
        "special_requirements": None,   # Wheelchair, dietary needs, etc.

        "state":                "GREETING",

        "pricing_shared":       False,
        "booking_confirmed":    False,

        "handled_objections":   [],
        "used_ctas":            [],

        "message_count":        0,
        "price_asked_count":    0,

        "name_asked":           False,
        "phone_asked":          False,

        "social_proof_used":    False,

        "delay_count":          0,
        "whatsapp_trust_sent":  False,
        "neft_offered":         False,
        "lead_warm":            False,

        "human_agent_requested": False,

        # Conversation summary (updated periodically by memory.py)
        "conversation_summary": "",

        # Lead scoring (updated by lead_scoring.py after every response)
        "lead_score":           0,
        "lead_tier":            "COLD",

        # ── Razorpay Payment Fields ──────────────────────────────────────
        "payment_link":         None,   # Razorpay short URL sent to customer
        "payment_status":       None,   # pending | paid | failed | expired
        "booking_id":           None,   # ND-YYYY-XXXX unique booking reference
        "payment_link_id":      None,   # Razorpay plink_... ID (for webhook matching)
        "payment_asked":        False,  # True once AI has shared the payment link
        "amount":               None,   # Final amount in INR (integer)
    }



# --------------------------------------------------
# Core session management
# --------------------------------------------------

def initialize_booking(user_id: str):
    """
    Ensure the session exists in memory.
    1. If already in memory cache — done.
    2. Try to load from MongoDB (surviving Streamlit restarts).
    3. Otherwise create a fresh default session and persist it.
    """
    if user_id in booking_sessions:
        return

    # Try to recover from MongoDB
    persisted = session_store.load_session(user_id)
    if persisted:
        booking_sessions[user_id] = persisted
        return

    # Brand-new user
    session = _default_session(user_id)
    booking_sessions[user_id] = session
    session_store.save_session(user_id, session)


def get_booking(user_id: str) -> dict:
    initialize_booking(user_id)
    return booking_sessions[user_id]


def update_booking(user_id: str, key: str, value):
    initialize_booking(user_id)
    booking_sessions[user_id][key] = value
    # Write-through to MongoDB
    session_store.update_session_field(user_id, key, value)


def set_state(user_id: str, state: str):
    initialize_booking(user_id)
    booking_sessions[user_id]["state"] = state
    session_store.update_session_field(user_id, "state", state)


def get_state(user_id: str) -> str:
    initialize_booking(user_id)
    return booking_sessions[user_id]["state"]


def increment_message_count(user_id: str):
    initialize_booking(user_id)
    booking_sessions[user_id]["message_count"] += 1
    new_count = booking_sessions[user_id]["message_count"]
    session_store.update_session_field(user_id, "message_count", new_count)


# --------------------------------------------------
# Objection tracking
# --------------------------------------------------

def mark_objection_handled(user_id: str, objection: str):
    initialize_booking(user_id)
    if objection not in booking_sessions[user_id]["handled_objections"]:
        booking_sessions[user_id]["handled_objections"].append(objection)
        session_store.update_session_field(
            user_id,
            "handled_objections",
            booking_sessions[user_id]["handled_objections"]
        )


def was_objection_handled(user_id: str, objection: str) -> bool:
    initialize_booking(user_id)
    return objection in booking_sessions[user_id]["handled_objections"]