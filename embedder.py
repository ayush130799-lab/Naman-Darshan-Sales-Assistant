# embedder.py

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# Import the data loader we wrote earlier
from data_loader import load_data

# 1. Load raw text data from MongoDB Atlas
texts = load_data()

# 2. Chunk the data into smaller pieces
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)

docs = splitter.create_documents(texts)

# 3. Initialize the embedding model
embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# 4. Build FAISS index from documents
vectorstore = FAISS.from_documents(
    docs,
    embedding_model
)

# 5. Save FAISS index locally
vectorstore.save_local("vectorstore")

print(f"✅ Successfully built FAISS index with {len(docs)} chunks.")
