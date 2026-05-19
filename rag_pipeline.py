from retriever import retrieve_docs
from prompt_builder import build_prompt
from sales_logic import sales_strategy

from langchain_groq import ChatGroq

from config import GROQ_API_KEY

llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile"
)

def generate_response(query, history):

    print("USER QUERY:", query)

    # Retrieve relevant docs
    context = retrieve_docs(query)

    print("CONTEXT:", context)

    if not context.strip():

        return "Sorry, I could not find verified information currently."

    # Sales strategy
    sales_instruction = sales_strategy(query)

    # Build prompt
    prompt = build_prompt(
        query,
        context,
        history,
        sales_instruction
    )

    # LLM response
    response = llm.invoke(prompt)

    print("LLM RESPONSE:", response.content)

    return response.content