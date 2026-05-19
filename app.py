import streamlit as st

from rag_pipeline import generate_response
from memory import get_memory, save_memory

st.set_page_config(
    page_title="Naman Darshan AI",
    page_icon="🙏",
    layout="wide"
)

# Custom styling
st.markdown("""
<style>

.stApp {
    background: linear-gradient(
        rgba(0,0,0,0.75),
        rgba(0,0,0,0.75)
    ),
    url("https://images.unsplash.com/photo-1524492514790-831f5b0d6cfe?q=80&w=1920");

    background-size: cover;
}

.chat-container {
    padding: 20px;
}

.user-msg {

    background: #ff9933;

    color: white;

    padding: 12px;

    border-radius: 12px;

    margin: 10px 0;

    text-align: right;
}

.ai-msg {

    background: rgba(255,255,255,0.15);

    color: white;

    padding: 12px;

    border-radius: 12px;

    margin: 10px 0;
}

h1 {
    color: white;
    text-align: center;
}

</style>
""", unsafe_allow_html=True)

st.title("🙏 Naman Darshan AI Assistant")

if "history" not in st.session_state:
    st.session_state.history = []

user_input = st.chat_input(
    "Ask about VIP Darshan..."
)

if user_input:

    st.session_state.history.append({
        "role": "user",
        "content": user_input
    })

    history = get_memory("user_1")

    response = generate_response(
        user_input,
        history
    )

    save_memory(
        "user_1",
        user_input,
        response
    )

    st.session_state.history.append({
        "role": "assistant",
        "content": response
    })

for msg in st.session_state.history:

    if msg["role"] == "user":

        st.markdown(
            f"""
            <div class="user-msg">
            {msg['content']}
            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            f"""
            <div class="ai-msg">
            {msg['content']}
            </div>
            """,
            unsafe_allow_html=True
        )