import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-MiniLM-L3-v2"
)

# Auto-build vectorstore if it doesn't exist (e.g. first run on HF Spaces)
if not os.path.exists("vectorstore/index.faiss"):
    print("⚙️ Vectorstore not found. Building from scratch...")
    import embedder  # runs the full embed + save pipeline
    print("✅ Vectorstore built successfully.")

vectorstore = FAISS.load_local(
    "vectorstore",
    embedding_model,
    allow_dangerous_deserialization=True
)


# ----------------------------------------
# RETRIEVE DOCS
# ----------------------------------------

def retrieve_docs(query):

    docs = vectorstore.max_marginal_relevance_search(

        query,

        k=3,

        fetch_k=10
    )

    unique_docs = []

    seen = set()

    for doc in docs:

        content = doc.page_content.strip()

        if content not in seen:

            seen.add(content)

            unique_docs.append(content)

    context = "\n".join(unique_docs)

    return context