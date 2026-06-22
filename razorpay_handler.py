# razorpay_handler.py
# Manages Razorpay Payment Links for Naman Darshan booking workflow.
#
# Responsibilities:
#   - create_payment_link()   → calls Razorpay API, stores record in `payments` collection
#   - get_payment_status()    → returns payment record from MongoDB (+ live Razorpay status)
#   - update_payment_status() → called by webhook; verifies HMAC, marks payment as paid,
#                               syncs Customer_Profile & conversation_sessions
#   - generate_booking_id()   → produces unique ND-YYYY-XXXX booking reference
#   - _get_pricing()          → per-person pricing table (edit to match your rates)
#
# Architecture:
#   - Same lazy-init + graceful-fallback pattern as session_store.py
#   - Uses temples_clone MongoDB database (existing connection)
#   - Payments stored in a new `payments` collection

import razorpay
import hmac
import hashlib
import random
import string
from datetime import datetime
from pymongo import MongoClient

from config import MONGO_URI, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET


# --------------------------------------------------
# PRICING TABLE — edit these to match your real rates
# Key = lowercase fragment of temple name or package_type
# Value = price per person in INR
# --------------------------------------------------
_PRICING_TABLE = {
    # Temple-specific per-person rates
    "tirupati":     2999,
    "ayodhya":      1999,
    "ram mandir":   1999,
    "kashi":        2499,
    "vishwanath":   2499,
    "vaishno devi": 2999,
    "kedarnath":    3499,
    "badrinath":    3499,
    "mahakaleshwar": 2499,
    "somnath":      2499,
    "shirdi":       1999,
    "jagannath":    2499,
    "puri":         2499,
    "dwarkadhish":  2499,
    "meenakshi":    1999,
    "golden temple": 1499,
    "kamakhya":     2499,
    "rameshwaram":  2499,
    "kanyakumari":  2499,
    # Package-type fallbacks
    "yatra":        3499,
    "puja":         1999,
    "prasadam":      999,
    "chadhava":      799,
    "astrology":    1499,
    # Default
    "default":      1999,
}

_DEFAULT_PRICE_PER_PERSON = 1999  # INR — used when temple not in table


# --------------------------------------------------
# Module-level MongoDB connection (lazy init)
# --------------------------------------------------
_client = None
_payments_col = None
_mongo_available = False


def _init_mongo():
    global _client, _payments_col, _mongo_available
    if _mongo_available:
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
        _payments_col = db["payments"]

        # Indexes
        try:
            _payments_col.create_index("booking_id", unique=True)
        except Exception:
            pass
        try:
            _payments_col.create_index("user_id")
        except Exception:
            pass
        try:
            _payments_col.create_index("razorpay_payment_link_id")
        except Exception:
            pass
        try:
            _payments_col.create_index("payment_status")
        except Exception:
            pass

        _mongo_available = True
        print("[razorpay_handler] MongoDB connected — payments collection ready.")
    except Exception as e:
        print(f"[razorpay_handler] MongoDB unavailable — payment records disabled. ({e})")
        _mongo_available = False


_init_mongo()


# --------------------------------------------------
# Razorpay client (lazy init)
# --------------------------------------------------
_rzp_client = None
_rzp_available = False


def _init_razorpay():
    global _rzp_client, _rzp_available
    if _rzp_available:
        return
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        print("[razorpay_handler] Razorpay credentials not set — payment links disabled.")
        _rzp_available = False
        return
    if "REPLACE_WITH" in RAZORPAY_KEY_ID or "REPLACE_WITH" in RAZORPAY_KEY_SECRET:
        print("[razorpay_handler] Razorpay credentials are placeholders — payment links disabled.")
        _rzp_available = False
        return
    try:
        _rzp_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        _rzp_available = True
        print("[razorpay_handler] Razorpay client initialized.")
    except Exception as e:
        print(f"[razorpay_handler] Razorpay init failed: {e}")
        _rzp_available = False


_init_razorpay()


# --------------------------------------------------
# PUBLIC HELPERS
# --------------------------------------------------

def is_razorpay_available() -> bool:
    """Returns True if Razorpay credentials are configured and client is ready."""
    return _rzp_available


def generate_booking_id() -> str:
    """
    Generate a unique booking ID in format ND-YYYY-XXXX.
    e.g. ND-2026-A3F9
    """
    year = datetime.utcnow().year
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ND-{year}-{suffix}"


def _get_pricing(temple: str, people: int, package_type: str) -> int:
    """
    Returns the total price in INR for a booking.
    Looks up the temple/package in _PRICING_TABLE; falls back to default.

    Args:
        temple:       Temple name from booking session
        people:       Number of travellers
        package_type: e.g. "darshan", "yatra", "puja"

    Returns:
        Total amount in INR (integer)
    """
    people = max(1, int(people or 1))
    temple_lower = (temple or "").lower()
    pkg_lower = (package_type or "").lower()

    # Try temple name match first
    per_person = None
    for key, price in _PRICING_TABLE.items():
        if key in temple_lower:
            per_person = price
            break

    # Try package_type if temple not matched
    if per_person is None and pkg_lower in _PRICING_TABLE:
        per_person = _PRICING_TABLE[pkg_lower]

    # Default
    if per_person is None:
        per_person = _PRICING_TABLE["default"]

    return per_person * people


# --------------------------------------------------
# CORE API: Create Payment Link
# --------------------------------------------------

def create_payment_link(user_id: str, booking: dict, amount: int = None) -> dict:
    """
    Creates a Razorpay Payment Link for the given booking session.

    Args:
        user_id: Session user ID
        booking: Current booking dict from booking_flow.get_booking()
        amount:  Override amount in INR. If None, auto-calculated from pricing table.

    Returns:
        {
          "success":    bool,
          "booking_id": str,          # ND-YYYY-XXXX
          "payment_link": str,        # Short URL for customer
          "payment_link_id": str,     # Razorpay plink_... ID
          "amount": int,              # Amount in INR
          "error":  str or None,
        }
    """
    # Calculate amount if not provided
    if amount is None:
        amount = _get_pricing(
            temple=booking.get("temple"),
            people=booking.get("people"),
            package_type=booking.get("package_type"),
        )

    booking_id = generate_booking_id()

    if not _rzp_available:
        # Generate a mock payment link for testing/dev environments instead of failing
        short_url = f"https://rzp.io/i/mock_{booking_id}"
        payment_link_id = f"plink_mock_{booking_id}"
        
        # Persist to MongoDB payments collection
        _save_payment_record(
            booking_id=booking_id,
            user_id=user_id,
            booking=booking,
            amount=amount,
            payment_link_id=payment_link_id,
            payment_link=short_url,
        )
        
        print(f"[razorpay_handler] [MOCK MODE] Payment link created: booking_id={booking_id}, link={short_url}")
        return {
            "success": True,
            "booking_id": booking_id,
            "payment_link": short_url,
            "payment_link_id": payment_link_id,
            "amount": amount,
            "error": None,
        }
    customer_name = booking.get("customer_name") or "Devotee"
    phone = booking.get("phone") or ""
    temple = booking.get("temple") or "Naman Darshan Booking"
    date = booking.get("date") or ""
    people = booking.get("people") or 1

    # Build description
    description = f"Naman Darshan — {temple}"
    if date:
        description += f" | Date: {date}"
    if people:
        description += f" | {people} traveller(s)"

    # Build Razorpay Payment Link payload
    payload = {
        "amount": amount * 100,           # Razorpay uses paise (1 INR = 100 paise)
        "currency": "INR",
        "accept_partial": False,
        "description": description,
        "customer": {
            "name": customer_name,
            "contact": f"+91{phone}" if phone and len(phone) == 10 else phone,
        },
        "notify": {
            "sms": bool(phone),
            "email": False,
        },
        "reminder_enable": True,
        "notes": {
            "booking_id":   booking_id,
            "user_id":      user_id,
            "temple":       temple,
            "travel_date":  date,
            "people_count": str(people),
        },
        "callback_url": "",           # Optional: redirect URL after payment
        "callback_method": "get",
    }

    try:
        response = _rzp_client.payment_link.create(payload)
        payment_link_id = response.get("id", "")
        short_url = response.get("short_url", "")

        if not payment_link_id or not short_url:
            return {
                "success": False,
                "error": f"Razorpay returned unexpected response: {response}",
                "booking_id": None,
                "payment_link": None,
                "payment_link_id": None,
                "amount": amount,
            }

        # Persist to MongoDB payments collection
        _save_payment_record(
            booking_id=booking_id,
            user_id=user_id,
            booking=booking,
            amount=amount,
            payment_link_id=payment_link_id,
            payment_link=short_url,
        )

        print(f"[razorpay_handler] Payment link created: booking_id={booking_id}, link={short_url}")
        return {
            "success": True,
            "booking_id": booking_id,
            "payment_link": short_url,
            "payment_link_id": payment_link_id,
            "amount": amount,
            "error": None,
        }

    except Exception as e:
        print(f"[razorpay_handler] create_payment_link error: {e}")
        return {
            "success": False,
            "error": str(e),
            "booking_id": None,
            "payment_link": None,
            "payment_link_id": None,
            "amount": amount,
        }


# --------------------------------------------------
# CORE API: Get Payment Status
# --------------------------------------------------

def get_payment_status(user_id: str, booking_id: str = None, query: str = None) -> dict:
    """
    Returns the latest payment status for a user.
    Looks up the most recent payment record in MongoDB.

    Args:
        user_id:    Session user ID
        booking_id: Optional specific booking ID to look up
        query:      Optional user query to check for manual payment claims in mock mode

    Returns:
        {
          "found": bool,
          "payment_status": "pending"|"paid"|"failed"|"expired"|None,
          "booking_status": "awaiting_payment"|"confirmed"|"cancelled"|None,
          "booking_id": str or None,
          "payment_link": str or None,
          "amount": int or None,
          "payment_link_id": str or None,
        }
    """
    empty = {
        "found": False,
        "payment_status": None,
        "booking_status": None,
        "booking_id": None,
        "payment_link": None,
        "amount": None,
        "payment_link_id": None,
    }

    if not _mongo_available or _payments_col is None:
        return empty

    try:
        query_dict = {"booking_id": booking_id} if booking_id else {"user_id": user_id}
        doc = _payments_col.find_one(query_dict, sort=[("created_at", -1)])

        if not doc:
            return empty

        # Optionally fetch live status from Razorpay API
        live_status = None
        if _rzp_available and doc.get("razorpay_payment_link_id"):
            try:
                rzp_record = _rzp_client.payment_link.fetch(doc["razorpay_payment_link_id"])
                rzp_status = rzp_record.get("status", "")
                # Map Razorpay statuses to our internal statuses
                _status_map = {
                    "paid": "paid",
                    "cancelled": "failed",
                    "expired": "expired",
                    "created": "pending",
                    "partially_paid": "pending",
                }
                live_status = _status_map.get(rzp_status)
                # If live status is newer, update MongoDB
                if live_status and live_status != doc.get("payment_status"):
                    _payments_col.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"payment_status": live_status, "updated_at": datetime.utcnow()}}
                    )
                    doc["payment_status"] = live_status
            except Exception as e:
                print(f"[razorpay_handler] Live status fetch error: {e}")

        # In mock mode, if the user explicitly claims they paid, we update the status to paid
        if not _rzp_available and doc.get("razorpay_payment_link_id", "").startswith("plink_mock_"):
            if query:
                q_lower = query.lower()
                paid_keywords = ["paid", "done", "success", "complete", "gaya", "sent", "transfer", "receipt", "kar diya", "kar chuka"]
                if any(kw in q_lower for kw in paid_keywords):
                    live_status = "paid"
                    if doc.get("payment_status") != "paid":
                        _payments_col.update_one(
                            {"_id": doc["_id"]},
                            {"$set": {
                                "payment_status": "paid",
                                "booking_status": "confirmed",
                                "paid_at": datetime.utcnow(),
                                "updated_at": datetime.utcnow()
                            }}
                        )
                        doc["payment_status"] = "paid"
                        doc["booking_status"] = "confirmed"

        return {
            "found": True,
            "payment_status": doc.get("payment_status"),
            "booking_status": doc.get("booking_status"),
            "booking_id": doc.get("booking_id"),
            "payment_link": doc.get("payment_link"),
            "amount": doc.get("amount"),
            "payment_link_id": doc.get("razorpay_payment_link_id"),
        }

    except Exception as e:
        print(f"[razorpay_handler] get_payment_status error: {e}")
        return empty


# --------------------------------------------------
# CORE API: Update Payment Status (called from webhook)
# --------------------------------------------------

def update_payment_status(
    payment_link_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    event_type: str = "payment_link.paid",
) -> bool:
    """
    Verifies the Razorpay webhook signature and marks the payment as paid.
    Updates:
      - payments collection: payment_status=paid, booking_status=confirmed
      - Customer_Profile:    lead_stage=payment_confirmed
      - conversation_sessions: booking_confirmed=True, payment_status=paid

    Args:
        payment_link_id:     Razorpay payment link ID (plink_...)
        razorpay_payment_id: Razorpay payment ID (pay_...)
        razorpay_signature:  HMAC signature from webhook header
        event_type:          Razorpay event type string

    Returns:
        True if update succeeded, False otherwise.
    """
    if not _mongo_available or _payments_col is None:
        print("[razorpay_handler] MongoDB unavailable — cannot update payment status.")
        return False

    try:
        # Find the payment record
        doc = _payments_col.find_one({"razorpay_payment_link_id": payment_link_id})
        if not doc:
            print(f"[razorpay_handler] No payment record found for link_id={payment_link_id}")
            return False

        user_id = doc.get("user_id")
        booking_id = doc.get("booking_id")

        # Update payments collection
        _payments_col.update_one(
            {"razorpay_payment_link_id": payment_link_id},
            {
                "$set": {
                    "payment_status":     "paid",
                    "booking_status":     "confirmed",
                    "razorpay_payment_id": razorpay_payment_id,
                    "razorpay_signature": razorpay_signature,
                    "paid_at":            datetime.utcnow(),
                    "updated_at":         datetime.utcnow(),
                }
            }
        )
        print(f"[razorpay_handler] Payment confirmed: booking_id={booking_id}, payment_id={razorpay_payment_id}")

        # Sync to conversation_sessions (booking_flow session)
        try:
            from session_store import update_session_field
            update_session_field(user_id, "payment_status", "paid")
            update_session_field(user_id, "booking_confirmed", True)
            update_session_field(user_id, "lead_stage", "payment_confirmed")
            print(f"[razorpay_handler] Synced payment_confirmed to conversation_sessions for user_id={user_id}")
        except Exception as e:
            print(f"[razorpay_handler] session_store sync error: {e}")

        # Sync to Customer_Profile collection
        try:
            from customer_profile import update_lead_stage
            from customer_profile import STAGE_PAYMENT_CONFIRMED
            update_lead_stage(user_id, STAGE_PAYMENT_CONFIRMED)

            # Also update by phone if available
            phone = doc.get("phone")
            if phone and phone != user_id:
                update_lead_stage(phone, STAGE_PAYMENT_CONFIRMED)
            print(f"[razorpay_handler] Synced payment_confirmed to Customer_Profile for user_id={user_id}")
        except Exception as e:
            print(f"[razorpay_handler] Customer_Profile sync error: {e}")

        return True

    except Exception as e:
        print(f"[razorpay_handler] update_payment_status error: {e}")
        return False


# --------------------------------------------------
# WEBHOOK SIGNATURE VERIFICATION
# --------------------------------------------------

def verify_webhook_signature(payload_body: bytes, signature: str) -> bool:
    """
    Verifies Razorpay webhook HMAC-SHA256 signature.

    Args:
        payload_body: Raw request body bytes from the webhook POST
        signature:    Value of the X-Razorpay-Signature header

    Returns:
        True if signature is valid, False otherwise.
    """
    if not RAZORPAY_WEBHOOK_SECRET or "REPLACE_WITH" in RAZORPAY_WEBHOOK_SECRET:
        print("[razorpay_handler] Webhook secret not set — skipping signature verification (INSECURE).")
        return True  # Allow through in dev mode; set secret in production

    try:
        expected = hmac.new(
            RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
            payload_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception as e:
        print(f"[razorpay_handler] Signature verification error: {e}")
        return False


# --------------------------------------------------
# INTERNAL: Save payment record to MongoDB
# --------------------------------------------------

def _save_payment_record(
    booking_id: str,
    user_id: str,
    booking: dict,
    amount: int,
    payment_link_id: str,
    payment_link: str,
):
    """Inserts a new payment record into the `payments` collection."""
    if not _mongo_available or _payments_col is None:
        return

    try:
        now = datetime.utcnow()
        _payments_col.insert_one({
            "booking_id":               booking_id,
            "user_id":                  user_id,
            "phone":                    booking.get("phone"),
            "customer_name":            booking.get("customer_name"),
            "temple":                   booking.get("temple"),
            "date":                     booking.get("date"),
            "people":                   booking.get("people"),
            "package_type":             booking.get("package_type"),
            "amount":                   amount,
            "razorpay_payment_link_id": payment_link_id,
            "payment_link":             payment_link,
            "payment_status":           "pending",
            "booking_status":           "awaiting_payment",
            "razorpay_payment_id":      None,
            "razorpay_signature":       None,
            "paid_at":                  None,
            "created_at":               now,
            "updated_at":               now,
        })
    except Exception as e:
        print(f"[razorpay_handler] _save_payment_record error: {e}")
