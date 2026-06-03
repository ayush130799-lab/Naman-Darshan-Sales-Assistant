booking_sessions = {}

def initialize_booking(user_id):

    if user_id not in booking_sessions:

        booking_sessions[user_id] = {

            "temple": None,
            "date": None,
            "people": None,
            "elderly": False,

            # Travel qualification answer (Step 5 of sales flow)
            "qualification": None,

            "customer_name": None,
            "phone": None,

            "state": "GREETING",

            "pricing_shared": False,
            "booking_confirmed": False,

            "handled_objections": [],
            "used_ctas": [],

            "message_count": 0,

            # Tracks how many times user has asked about pricing
            # Used to route PRICE vs PRICE_REPEAT intent
            "price_asked_count": 0,

            # Progressive lead capture flags
            "name_asked": False,
            "phone_asked": False,

            # Social proof usage tracker — once mentioned, never repeat
            "social_proof_used": False,
        }

def get_booking(user_id):
    initialize_booking(user_id)
    return booking_sessions[user_id]

def update_booking(user_id, key, value):
    initialize_booking(user_id)
    booking_sessions[user_id][key] = value

def increment_message_count(user_id):
    initialize_booking(user_id)
    booking_sessions[user_id]["message_count"] += 1

def set_state(user_id, state):
    initialize_booking(user_id)
    booking_sessions[user_id]["state"] = state

def get_state(user_id):
    initialize_booking(user_id)
    return booking_sessions[user_id]["state"]

def mark_objection_handled(user_id, objection):
    initialize_booking(user_id)

    if objection not in booking_sessions[user_id]["handled_objections"]:
        booking_sessions[user_id]["handled_objections"].append(objection)

def was_objection_handled(user_id, objection):
    initialize_booking(user_id)

    return objection in booking_sessions[user_id]["handled_objections"]