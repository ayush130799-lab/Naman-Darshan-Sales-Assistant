# qa_handler.py
# Handles INFORMATION_REQUEST messages — answers questions using RAG + LLM.
# Does NOT modify booking state. Always returns a plain string answer.
# Routes recommendation-type queries to recommendation_engine.py.

from langchain_groq import ChatGroq
from config import GROQ_API_KEY

_qa_llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.7,
    max_tokens=400,
    api_key=GROQ_API_KEY,
    max_retries=5
)

# Sub-intents that should go to recommendation_engine instead of generic RAG QA
_RECOMMENDATION_SUB_INTENTS = {
    "PACKAGE_DISCOVERY",
    "TEMPLE_LIST",      # 'Which temples in Tamil Nadu?' → recommendation, not raw list
}

# Keywords that signal a recommendation request even if sub_intent is GENERAL
_RECOMMENDATION_KEYWORDS = [
    "best temple", "which temple", "recommend", "suggest", "good for",
    "near bangalore", "near mumbai", "near delhi", "near chennai", "near hyderabad",
    "near kolkata", "near pune", "near ahmedabad", "near jaipur",
    "in june", "in july", "in august", "in september", "in october",
    "in november", "in december", "in january", "in february", "in march",
    "in april", "in may", "in winter", "in summer", "in monsoon",
    "for elderly", "for old", "for parents", "for senior", "for family",
    "for women", "for solo", "for children", "for kids",
    "jyotirlinga", "char dham", "first time", "most popular",
    "suitable for", "which one should", "which is better",
    "in tamil nadu", "in karnataka", "in rajasthan", "in gujarat",
    "in kerala", "in odisha", "in maharashtra", "in uttar pradesh",
    "in uttarakhand", "in himachal", "in jammu", "in assam",
    "south india", "north india", "east india", "west india",
    "wheelchair", "accessible", "easy trek", "difficult",
]

_QA_PROMPT = """You are a knowledgeable assistant for Naman Darshan — India's trusted assisted Temple Darshan service.

Answer the user's question clearly, helpfully, and specifically.
Use the knowledge base below if relevant. Be factual and natural — like a helpful friend, not a sales bot.
Do NOT push a sale or ask for name/phone number in this response.

Temple context (if selected): {temple}

KNOWLEDGE BASE:
{context}

RECENT CONVERSATION:
{history}

USER'S QUESTION: {query}

PENDING QUESTION: {pending_question}

INSTRUCTION FOR PENDING QUESTION:
If a PENDING QUESTION is provided above, you MUST answer the user's question first, and then naturally transition to asking for that information (rephrase the pending question to fit context) at the very end of your response. 
The transition should feel smooth, conversational, and context-aware, rather than abrupt or copy-pasted verbatim. Do NOT ask for this information if it is already answered in the user's query or conversation history.
If no pending question is provided, just answer the user's question and close the message naturally.

Answer in 3-5 sentences. Be specific, helpful, and natural."""


def handle_information_request(
    query: str,
    history: list,
    booking: dict,
    sub_intent: str,
    pending_question: str = None,
) -> str:
    """
    Handle an INFORMATION_REQUEST message.

    Routing:
    - Recommendation queries → recommendation_engine.get_recommendation()
    - All other queries → RAG + LLM answer via _qa_llm

    Args:
        query:            User's message
        history:          Recent conversation turns
        booking:          Current booking session dict
        sub_intent:       Fine-grained sub-intent from intent_classifier
        pending_question: Suffix question from the booking flow to ask devotee next

    Returns:
        Answer string (does NOT include the resume question — that's added by message_router)
    """
    # Route to recommendation engine
    if sub_intent in _RECOMMENDATION_SUB_INTENTS or _is_recommendation_query(query):
        from recommendation_engine import get_recommendation
        return get_recommendation(query, history, booking, pending_question=pending_question)

    # General QA via RAG + LLM
    context = _retrieve_context(query)
    temple  = booking.get("temple", "Not specified yet")
    formatted_history = _format_history(history[-4:])

    prompt = _QA_PROMPT.format(
        temple=temple,
        context=context or "No specific context retrieved.",
        history=formatted_history,
        query=query,
        pending_question=pending_question or "None"
    )

    try:
        response = _qa_llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        print(f"[qa_handler] LLM error: {e}")
        return (
            "That's a great question. Once the required details are provided, "
            "I can help you proceed with the booking process and provide complete details. 🙏"
        )


def _is_recommendation_query(query: str) -> bool:
    """Returns True if the query is asking for a temple recommendation."""
    q = query.lower()
    return any(kw in q for kw in _RECOMMENDATION_KEYWORDS)


def _retrieve_context(query: str) -> str:
    """Retrieve RAG context from FAISS vectorstore. Returns empty string on error."""
    try:
        from retriever import retrieve_docs
        return retrieve_docs(query)
    except Exception as e:
        print(f"[qa_handler] RAG retrieval error: {e}")
        return ""


def _format_history(history: list) -> str:
    if not history:
        return "No previous conversation."
    return "\n".join(
        f"User: {h.get('user', '')}\nAssistant: {h.get('assistant', '')}"
        for h in history
    )
