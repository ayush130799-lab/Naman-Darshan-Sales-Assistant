# customer_profile.py
# Manages the Customer_Profile MongoDB collection for Naman Darshan Sales AI.
#
# Responsibilities:
#   - Upsert Customer_Profile whenever any customer detail is shared in conversation
#   - Track lead_stage: form_not_filled | form_filled_no_payment | payment_confirmed
#   - Track current_intent: main_booking | puja_booking | abhishekam_booking |
#                           prasadam_booking | chadhava_booking | darshan_booking |
#                           accommodation_booking | transportation_booking
#   - Compute which required profile fields are still missing (missing_fields)
#   - Provide customer notes for personalizing responses

from pymongo import MongoClient
from datetime import datetime
from config import MONGO_URI


# --------------------------------------------------
# Lead Stage Constants
# --------------------------------------------------
STAGE_FORM_NOT_FILLED      = "form_not_filled"
STAGE_FORM_FILLED_NO_PAY   = "form_filled_no_payment"
STAGE_PAYMENT_CONFIRMED    = "payment_confirmed"

# --------------------------------------------------
# Intent Constants
# --------------------------------------------------
INTENT_MAIN_BOOKING           = "main_booking"
INTENT_PUJA_BOOKING           = "puja_booking"
INTENT_ABHISHEKAM_BOOKING     = "abhishekam_booking"
INTENT_PRASADAM_BOOKING       = "prasadam_booking"
INTENT_CHADHAVA_BOOKING       = "chadhava_booking"
INTENT_DARSHAN_BOOKING        = "darshan_booking"
INTENT_ACCOMMODATION_BOOKING  = "accommodation_booking"
INTENT_TRANSPORTATION_BOOKING = "transportation_booking"

# --------------------------------------------------
# Core profile fields required to complete the customer profile form.
# These are the fields that determine form_not_filled vs form_filled_no_payment.
# --------------------------------------------------
_CORE_PROFILE_FIELDS = [
    "temple",
    "date",
    "people",
    "departure_city",
    "budget",
]

# --------------------------------------------------
# MongoDB connection — graceful fallback if unavailable
# --------------------------------------------------
_client = None
_profile_col = None
_available = False


def _init():
    global _client, _profile_col, _available
    if _available:
        return
    try:
        _client = MongoClient(
            MONGO_URI,
            tls=True,
            tlsAllowInvalidCertificates=True,
            serverSelectionTimeoutMS=5000,
        )
        _client.admin.command("ping")
        db = _client["temples_clone"]
        _profile_col = db["Customer_Profile"]

        # Create indexes for fast lookup — sparse so null user_id won't conflict
        try:
            _profile_col.create_index("user_id", unique=True, sparse=True)
        except Exception:
            pass  # Index may already exist — that's fine
        try:
            _profile_col.create_index("updated_at")
        except Exception:
            pass
        try:
            _profile_col.create_index("lead_stage")
        except Exception:
            pass

        _available = True
        print("[customer_profile] MongoDB connected — Customer_Profile ready.")
    except Exception as e:
        print(f"[customer_profile] MongoDB unavailable — Customer_Profile writes disabled. ({e})")
        _available = False


_init()


# --------------------------------------------------
# LEAD STAGE COMPUTATION
# --------------------------------------------------

def compute_lead_stage(session: dict) -> str:
    """
    Computes the lead stage based on current session data.

    Rules:
      form_not_filled      — any core profile field is missing
      form_filled_no_payment — all core fields present, booking not confirmed
      payment_confirmed    — booking_confirmed is True
    """
    if session.get("booking_confirmed"):
        return STAGE_PAYMENT_CONFIRMED

    # Check if all core profile fields are filled
    missing = get_missing_fields(session)
    if missing:
        return STAGE_FORM_NOT_FILLED

    return STAGE_FORM_FILLED_NO_PAY


def get_missing_fields(session: dict) -> list:
    """
    Returns a list of core profile field names that are still empty.
    Used by the LLM to know exactly what to ask next (Missing Field Rule).
    """
    missing = []
    
    pkg_type = session.get("package_type")
    puja_val = session.get("puja")
    
    # If the user has a puja name but package_type is not puja, treat as puja
    if puja_val and pkg_type != "puja":
        pkg_type = "puja"

    if pkg_type == "puja" or puja_val:
        # Puja Flow
        if not session.get("puja_mode"):
            return ["Puja Mode (Online or Offline)"]
            
        puja_mode = session.get("puja_mode")
        field_labels = {
            "puja":           "Puja Name",
            "temple":         "Temple where puja is to be performed",
            "date":           "Preferred Date",
            "preferred_time": "Preferred Time",
        }
        if puja_mode == "offline":
            field_labels["people"] = "Number of Travellers (Adults + Children)"
            
        for field, label in field_labels.items():
            if not session.get(field):
                missing.append(label)
                
    elif pkg_type == "astrology":
        # Astrology Flow
        field_labels = {
            "date":           "Preferred Consultation Date",
            "preferred_time": "Preferred Time",
        }
        for field, label in field_labels.items():
            if not session.get(field):
                missing.append(label)
                
    elif pkg_type == "prasadam":
        # Prasadam Flow
        field_labels = {
            "temple":           "Temple / Destination",
            "quantity":         "Quantity of Prasadam",
            "delivery_address": "Delivery Address",
        }
        for field, label in field_labels.items():
            if not session.get(field):
                missing.append(label)
                
    elif pkg_type == "chadhava":
        # Chadhava Flow
        field_labels = {
            "temple":        "Temple / Destination",
            "offering_type": "Offering Type",
            "quantity":      "Quantity",
        }
        for field, label in field_labels.items():
            if not session.get(field):
                missing.append(label)
                
    else:
        # Default (Darshan / Yatra Booking Flow)
        field_labels = {
            "temple":         "Temple / Destination",
            "date":           "Travel Date",
            "people":         "Number of Travellers (Adults + Children)",
            "departure_city": "Departure City",
            "budget":         "Budget",
        }
        for field, label in field_labels.items():
            if not session.get(field):
                missing.append(label)
                
    return missing



# --------------------------------------------------
# PUBLIC API
# --------------------------------------------------

def upsert_customer_profile(user_id: str, session: dict):
    """
    Syncs the current session data into the Customer_Profile collection.
    Called after every _extract_and_hydrate() so the profile stays live.

    Maps session fields → Customer_Profile schema:
      customer_name   → customer_name
      phone           → phone
      temple          → temple
      date            → travel_date
      people          → total_travellers
      adults_count    → adults
      children_count  → children
      senior_count    → seniors
      departure_city  → departure_city
      budget          → budget
      special_requirements → special_requirements
      elderly         → has_elderly_or_children (bool)
      lead_stage      → lead_stage
      current_intent  → current_intent
      package_type    → service_type
      puja            → puja_name
    """
    if not _available or _profile_col is None:
        return

    try:
        stage = compute_lead_stage(session)
        missing = get_missing_fields(session)

        # Build notes from session data for personalization
        notes_parts = []
        if session.get("elderly"):
            notes_parts.append("Has elderly/children in group")
        if session.get("budget"):
            notes_parts.append(f"Budget: {session['budget']}")
        if session.get("special_requirements"):
            notes_parts.append(session["special_requirements"])
        if session.get("qualification"):
            notes_parts.append(f"Traveller type: {session['qualification']}")
        notes = "; ".join(notes_parts)

        payload = {
            "user_id":                user_id,
            "lead_stage":             stage,
            "current_intent":         session.get("current_intent") or INTENT_MAIN_BOOKING,
            "missing_fields":         missing,
            "notes":                  notes,

            # Customer identity
            "customer_name":          session.get("customer_name"),
            "phone":                  session.get("phone"),

            # Trip details
            "temple":                 session.get("temple"),
            "travel_date":            session.get("date"),
            "total_travellers":       session.get("people"),
            "adults":                 session.get("adults_count"),
            "children":               session.get("children_count"),
            "seniors":                session.get("senior_count"),
            "has_elderly_or_children": bool(session.get("elderly")),
            "departure_city":         session.get("departure_city"),
            "budget":                 session.get("budget"),
            "special_requirements":   session.get("special_requirements"),

            # Service context
            "service_type":           session.get("package_type"),
            "puja_name":              session.get("puja"),
            "puja_mode":              session.get("puja_mode"),

            # ── Payment info (synced from session) ──────────────────────
            "booking_id":             session.get("booking_id"),
            "amount":                 session.get("amount"),
            "payment_link":           session.get("payment_link"),
            "payment_status":         session.get("payment_status"),
            "booking_status":         "confirmed" if session.get("booking_confirmed") else (
                                          "awaiting_payment" if session.get("payment_link") else None
                                      ),

            # Timestamps
            "updated_at":             datetime.utcnow(),
        }

        # Remove None values to avoid overwriting real data with None on partial updates
        payload_clean = {k: v for k, v in payload.items() if v is not None or k in (
            "has_elderly_or_children",  # bool — keep even if False
        )}

        # Always keep these even if None (they are identity fields)
        for identity_field in ("customer_name", "phone", "temple", "travel_date",
                                "total_travellers", "departure_city", "budget"):
            if session.get(identity_field) is not None:
                payload_clean[identity_field] = session.get(identity_field)

        _profile_col.update_one(
            {"user_id": user_id},
            {"$set": payload_clean},
            upsert=True
        )

        # Also update the lead_stage in the session store (so booking_flow knows)
        try:
            from session_store import update_session_field
            update_session_field(user_id, "lead_stage", stage)
        except Exception:
            pass

        print(f"[customer_profile] Upserted profile for {user_id} — stage={stage}, missing={missing}")

    except Exception as e:
        print(f"[customer_profile] upsert_customer_profile error: {e}")


def get_customer_profile(user_id: str) -> dict:
    """
    Load the Customer_Profile for a user.

    Lookup strategy (in order):
      1. Exact match on user_id field (fastest — handles both UUID and phone-keyed records).
         Also check if user_id was stored as an integer.
      2. If user_id looks like a phone number (10 digits), also try matching on the
         `phone` field (supporting both string and integer phone numbers) — this catches
         records saved under a different user_id (e.g. a UUID) that still have the phone stored.

    Returns empty dict if not found or MongoDB unavailable.
    """
    if not _available or _profile_col is None:
        return {}
    try:
        docs = []

        # Step 1: direct user_id lookup (try string and integer)
        doc = _profile_col.find_one({"user_id": user_id})
        if doc:
            docs.append(doc)
        
        try:
            doc_int = _profile_col.find_one({"user_id": int(user_id)})
            if doc_int:
                docs.append(doc_int)
        except ValueError:
            pass

        # Step 2: if user_id is/looks like a phone number, search by phone field
        # (supporting both integer and string phone numbers)
        phone_digits = "".join(filter(str.isdigit, str(user_id)))
        if len(phone_digits) >= 10:
            last_10 = phone_digits[-10:]
            query_or = [
                {"phone": user_id},
                {"phone": phone_digits},
                {"phone": last_10},
            ]
            try:
                query_or.append({"phone": int(phone_digits)})
            except ValueError:
                pass
            try:
                query_or.append({"phone": int(last_10)})
            except ValueError:
                pass
            
            # Also add regex search for string field
            query_or.append({"phone": {"$regex": last_10 + "$"}})
            
            for d in _profile_col.find({"$or": query_or}):
                docs.append(d)

        if docs:
            # Score and select the best profile (prefer documents with names, customer_ids, and more fields)
            def score(doc):
                has_name = bool(doc.get("customer_name") or doc.get("name"))
                has_crm_id = bool(doc.get("customer_id"))
                num_fields = sum(1 for v in doc.values() if v is not None and v != "")
                updated = doc.get("updated_at")
                if isinstance(updated, datetime):
                    updated_ts = updated.timestamp()
                else:
                    updated_ts = 0.0
                return (has_name, has_crm_id, num_fields, updated_ts)

            docs_sorted = sorted(docs, key=score, reverse=True)
            best_doc = docs_sorted[0]
            best_doc.pop("_id", None)
            return best_doc

        return {}
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[customer_profile] get_customer_profile error: {e}")
        return {}



def update_lead_stage(user_id: str, stage: str):
    """
    Directly update the lead_stage for a user.
    Valid values: form_not_filled | form_filled_no_payment | payment_confirmed
    """
    if not _available or _profile_col is None:
        return
    try:
        _profile_col.update_one(
            {"user_id": user_id},
            {"$set": {"lead_stage": stage, "updated_at": datetime.utcnow()}},
            upsert=True
        )
        # Sync to session_store as well
        try:
            from session_store import update_session_field
            update_session_field(user_id, "lead_stage", stage)
        except Exception:
            pass
    except Exception as e:
        print(f"[customer_profile] update_lead_stage error: {e}")


def update_current_intent(user_id: str, intent: str):
    """
    Update the current_intent for a user.
    Valid values: main_booking | puja_booking | abhishekam_booking |
                  prasadam_booking | chadhava_booking | darshan_booking |
                  accommodation_booking | transportation_booking
    """
    if not _available or _profile_col is None:
        return
    try:
        _profile_col.update_one(
            {"user_id": user_id},
            {"$set": {"current_intent": intent, "updated_at": datetime.utcnow()}},
            upsert=True
        )
        try:
            from session_store import update_session_field
            update_session_field(user_id, "current_intent", intent)
        except Exception:
            pass
    except Exception as e:
        print(f"[customer_profile] update_current_intent error: {e}")


def is_available() -> bool:
    """Returns True if MongoDB Customer_Profile persistence is active."""
    return _available
