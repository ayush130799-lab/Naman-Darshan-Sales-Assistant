from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# Initialize embedding model
embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-MiniLM-L3-v2"
)

# Load FAISS vectorstore
vectorstore = FAISS.load_local(
    "vectorstore",
    embedding_model,
    allow_dangerous_deserialization=True
)

def retrieve_docs(query):
    """Retrieve top-k similar documents for a given query."""

    docs = vectorstore.similarity_search(
        query,
        k=5
    )

    if not docs:
        return ""

    context = "\n".join([
        doc.page_content for doc in docs
    ])

    return context