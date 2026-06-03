from pymongo import MongoClient
from datetime import datetime
import ssl
from collections import defaultdict

from config import MONGO_URI

# ------------------------------------------------------------------
# MongoDB connection with Python 3.14 / OpenSSL 3.x SSL workaround
# ------------------------------------------------------------------
# TLSV1_ALERT_INTERNAL_ERROR occurs because OpenSSL 3.x tightened
# TLS negotiation in ways that conflict with MongoDB Atlas.
# Fix: custom SSLContext with OP_LEGACY_SERVER_CONNECT + SECLEVEL=1.
# ------------------------------------------------------------------

def _build_ssl_context():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    # OP_LEGACY_SERVER_CONNECT: OpenSSL 3.x flag that re-enables
    # connections to servers that don't support renegotiation info.
    ctx.options |= getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0)
    # Lower security level to allow older cipher suites.
    try:
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
    except ssl.SSLError:
        pass
    return ctx


# In-memory fallback used when MongoDB is unavailable.
_in_memory_history: dict = defaultdict(list)
MONGO_AVAILABLE = False
memory_collection = None

try:
    _ssl_ctx = _build_ssl_context()
    client = MongoClient(
        MONGO_URI,
        tls=True,
        tlsAllowInvalidCertificates=True,
        ssl_context=_ssl_ctx,
        serverSelectionTimeoutMS=10_000,
    )
    db = client["temples_clone"]
    memory_collection = db["chat_memory"]
    # Trigger an actual connection to catch errors early.
    client.admin.command("ping")
    MONGO_AVAILABLE = True
    print("[memory] MongoDB connected successfully.")
except Exception as _e:
    print(f"[memory] MongoDB unavailable — using in-memory fallback. ({_e})")
    MONGO_AVAILABLE = False


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def get_memory(user_id, limit=6):
    if MONGO_AVAILABLE and memory_collection is not None:
        try:
            chats = list(
                memory_collection.find({"user_id": user_id})
                .sort("_id", -1)
                .limit(limit)
            )
            chats.reverse()
            return [{"user": c["user"], "assistant": c["assistant"]} for c in chats]
        except Exception as e:
            print(f"[memory] get_memory error: {e}")

    # In-memory fallback
    history = _in_memory_history.get(user_id, [])
    return history[-limit:]


def save_memory(user_id, user_query, ai_response):
    if MONGO_AVAILABLE and memory_collection is not None:
        try:
            memory_collection.insert_one({
                "user_id": user_id,
                "user": user_query,
                "assistant": ai_response,
                "timestamp": datetime.utcnow(),
            })
            return
        except Exception as e:
            print(f"[memory] save_memory error: {e}")

    # In-memory fallback
    _in_memory_history[user_id].append({
        "user": user_query,
        "assistant": ai_response,
    })