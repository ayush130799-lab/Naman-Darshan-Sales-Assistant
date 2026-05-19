# data_loader.py

from pymongo import MongoClient

def doc_to_text(doc):
    """
    Convert a MongoDB document (dict) into a plain text string.
    Skips the '_id' field since it's just a technical identifier.
    """
    return " ".join([f"{k}: {v}" for k, v in doc.items() if k != "_id"])

def load_data():
    """
    Connect to MongoDB Atlas, fetch collections, and return them as text.
    """

    # 1. Connect to MongoDB Atlas
    client = MongoClient("mongodb+srv://ayush:strongpassword123@sales-ai-backend.gofnxnk.mongodb.net/")
    db = client["temples_clone"]   # replace with your database name

    # 2. Fetch collections
    temples = list(db.temples.find())
    darshans = list(db.darshans.find())
    vip_packages = list(db.vip_packages.find())
    objections = list(db.objections.find())

    # 3. Convert documents to plain text
    texts = []
    for collection in [temples, darshans, vip_packages, objections]:
        for doc in collection:
            texts.append(doc_to_text(doc))

    return texts

if __name__ == "__main__":
    # Quick test
    data = load_data()
    print(f"Loaded {len(data)} documents from MongoDB Atlas")
    print(data[:3])  # show first 3 as sample
