# memory.py
# Stores and retrieves per-user conversation history in MongoDB.
# v2 additions:
#   - save_summary() / get_summary() for rolling conversation summary
#   - Summary is stored in the conversation_sessions collection

from pymongo import MongoClient
from datetime import datetime
from collections import defaultdict

from config import MONGO_URI


# --------------------------------------------------
# MongoDB connection — with graceful in-memory fallback
# --------------------------------------------------
_in_memory_history: dict = defaultdict(list)
MONGO_AVAILABLE = False
memory_collection = None

try:
    client = MongoClient(
        MONGO_URI,
        tls=True,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=10_000,
    )
    db = client["temples_clone"]
    memory_collection = db["chat_memory"]
    client.admin.command("ping")
    MONGO_AVAILABLE = True
    print("[memory] MongoDB connected successfully.")
except Exception as _e:
    print(f"[memory] MongoDB unavailable — using in-memory fallback. ({_e})")
    MONGO_AVAILABLE = False


# --------------------------------------------------
# Public API — conversation history
# --------------------------------------------------

def get_memory(user_id: str, limit: int = 6) -> list:
    """
    Returns the last `limit` conversation turns for a user.
    Each turn is a dict: {"user": str, "assistant": str}
    """
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

    history = _in_memory_history.get(user_id, [])
    return history[-limit:]


def save_memory(user_id: str, user_query: str, ai_response: str):
    """
    Persists a single conversation turn (user message + AI response).
    Also triggers a rolling summary update every 10 messages.
    """
    if MONGO_AVAILABLE and memory_collection is not None:
        try:
            memory_collection.insert_one({
                "user_id":   user_id,
                "user":      user_query,
                "assistant": ai_response,
                "timestamp": datetime.utcnow(),
            })

            # Update rolling summary every 10 messages
            _maybe_update_summary(user_id)
            return
        except Exception as e:
            print(f"[memory] save_memory error: {e}")

    # In-memory fallback
    _in_memory_history[user_id].append({
        "user":      user_query,
        "assistant": ai_response,
    })


# --------------------------------------------------
# Public API — conversation summary
# --------------------------------------------------

def save_summary(user_id: str, summary: str):
    """
    Save/update the rolling conversation summary in conversation_sessions.
    Called by _maybe_update_summary() internally, and can be called externally.
    """
    try:
        from session_store import append_conversation_summary
        append_conversation_summary(user_id, summary)
    except Exception as e:
        print(f"[memory] save_summary error: {e}")


def get_summary(user_id: str) -> str:
    """
    Retrieve the stored conversation summary for a user.
    Returns empty string if not available.
    """
    try:
        from session_store import load_session
        session = load_session(user_id)
        if session:
            return session.get("conversation_summary", "")
    except Exception as e:
        print(f"[memory] get_summary error: {e}")
    return ""


# --------------------------------------------------
# Internal: rolling summary generation
# --------------------------------------------------

def _maybe_update_summary(user_id: str):
    """
    Every 10 messages, generate a concise summary of the conversation
    using the LLM and store it in the session. This gives the bot
    long-term context without passing the full history every time.
    """
    if not MONGO_AVAILABLE or memory_collection is None:
        return

    try:
        count = memory_collection.count_documents({"user_id": user_id})
        if count % 10 != 0:
            return  # Only run every 10 messages

        # Fetch last 20 turns for summarization
        recent = list(
            memory_collection.find({"user_id": user_id})
            .sort("_id", -1)
            .limit(20)
        )
        recent.reverse()

        conversation_text = "\n".join(
            f"User: {c['user']}\nAssistant: {c['assistant']}"
            for c in recent
        )

        summary = _generate_summary(conversation_text)
        if summary:
            save_summary(user_id, summary)

    except Exception as e:
        print(f"[memory] _maybe_update_summary error: {e}")


def _generate_summary(conversation_text: str) -> str:
    """Generate a concise summary of the conversation using the LLM."""
    try:
        from langchain_groq import ChatGroq
        from config import GROQ_API_KEY

        summary_llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=150,
            api_key=GROQ_API_KEY
        )

        prompt = f"""Summarize this temple booking chatbot conversation in 2-3 sentences.
Focus on: temple selected, travel date, group size, key concerns raised, and current booking stage.

CONVERSATION:
{conversation_text}

Summary (2-3 sentences only):"""

        response = summary_llm.invoke(prompt)
        return response.content.strip()

    except Exception as e:
        print(f"[memory] _generate_summary error: {e}")
        return ""