booking_sessions = {}

def update_booking(user_id, key, value):

    if user_id not in booking_sessions:

        booking_sessions[user_id] = {
            "state": "START"
        }

    booking_sessions[user_id][key] = value

def get_booking(user_id):

    return booking_sessions.get(user_id, {})

def set_booking_state(user_id, state):

    if user_id not in booking_sessions:

        booking_sessions[user_id] = {}

    booking_sessions[user_id]["state"] = state