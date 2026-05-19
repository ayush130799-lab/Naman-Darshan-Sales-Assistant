from pymongo import MongoClient
from config import MONGO_URI

client = MongoClient(MONGO_URI)

db = client["temples_clone"]

memory_collection = db["chat_memory"]

def get_memory(user_id):

    chats = memory_collection.find(
        {"user_id": user_id}
    )

    history = []

    for chat in chats:
        history.append({
            "user": chat["user"],
            "assistant": chat["assistant"]
        })

    return history

def save_memory(user_id, user_query, ai_response):

    memory_collection.insert_one({
        "user_id": user_id,
        "user": user_query,
        "assistant": ai_response
    })