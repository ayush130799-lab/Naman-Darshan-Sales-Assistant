# session_store.py
# Persists full conversation session state to MongoDB `conversation_sessions` collection.
# Replaces the in-memory-only booking_sessions dict so sessions survive Streamlit restarts.
# Gracefully falls back to in-memory operation when MongoDB is unavailable.

from pymongo import MongoClient
from datetime import datetime
from config import MONGO_URI

# --------------------------------------------------
# Module-level MongoDB connection (lazy init)
# --------------------------------------------------
_client = None
_sessions_col = None
_available = False


def _init():
    global _client, _sessions_col, _available
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
        _sessions_col = db["conversation_sessions"]

        # Create indexes for fast lookup
        _sessions_col.create_index("user_id", unique=True)
        _sessions_col.create_index("updated_at")

        _available = True
        print("[session_store] MongoDB connected.")
    except Exception as e:
        print(f"[session_store] MongoDB unavailable — sessions will be in-memory only. ({e})")
        _available = False


_init()


# --------------------------------------------------
# Public API
# --------------------------------------------------

def load_session(user_id: str) -> dict | None:
    """
    Load a session from MongoDB by user_id.
    Returns the session dict (without MongoDB _id) or None if not found.
    """
    if not _available or _sessions_col is None:
        return None
    try:
        doc = _sessions_col.find_one({"user_id": user_id})
        if doc:
            doc.pop("_id", None)
            return doc
        return None
    except Exception as e:
        print(f"[session_store] load_session error: {e}")
        return None


def save_session(user_id: str, session_data: dict):
    """
    Upsert the full session dict to MongoDB.
    Adds/updates `updated_at` timestamp automatically.
    """
    if not _available or _sessions_col is None:
        return
    try:
        payload = {k: v for k, v in session_data.items() if k != "_id"}
        payload["updated_at"] = datetime.utcnow()
        _sessions_col.update_one(
            {"user_id": user_id},
            {"$set": payload},
            upsert=True
        )
    except Exception as e:
        print(f"[session_store] save_session error: {e}")


def update_session_field(user_id: str, key: str, value):
    """
    Update a single field in the session without loading the entire document.
    Used for high-frequency updates (e.g. incrementing message_count).
    """
    if not _available or _sessions_col is None:
        return
    try:
        _sessions_col.update_one(
            {"user_id": user_id},
            {"$set": {key: value, "updated_at": datetime.utcnow()}},
            upsert=True
        )
    except Exception as e:
        print(f"[session_store] update_field error ({key}): {e}")


def append_conversation_summary(user_id: str, summary: str):
    """Update the rolling conversation summary field."""
    update_session_field(user_id, "conversation_summary", summary)


def is_available() -> bool:
    """Returns True if MongoDB session persistence is active."""
    return _available
