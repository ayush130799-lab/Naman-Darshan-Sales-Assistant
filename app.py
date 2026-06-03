import streamlit as st
import uuid

from rag_pipeline import generate_response
from memory import get_memory, save_memory

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------

st.set_page_config(
    page_title="Naman Darshan AI",
    page_icon="🙏",
    layout="wide"
)

# ---------------------------------------------------
# USER SESSION
# ---------------------------------------------------

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

user_id = st.session_state.user_id

# ---------------------------------------------------
# INITIAL BOT MESSAGE
# ---------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "🙏 Welcome to Naman Darshan! Which temple are you planning to visit?"
        }
    ]

# ---------------------------------------------------
# CUSTOM CSS — Naman Darshan Brand Theme
# ---------------------------------------------------

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');

/* ── Root variables (Naman Darshan palette) ── */
:root {
    --nd-orange:       #F97316;
    --nd-orange-dark:  #EA580C;
    --nd-orange-light: #FED7AA;
    --nd-bg:           #0F0A04;
    --nd-surface:      #1C1108;
    --nd-card:         rgba(255,255,255,0.07);
    --nd-border:       rgba(249,115,22,0.25);
    --nd-text:         #F5F0E8;
    --nd-text-muted:   rgba(245,240,232,0.6);
}

/* ── Full page background — temple ambiance ── */
.stApp {
    background:
        linear-gradient(
            180deg,
            rgba(15,10,4,0.88) 0%,
            rgba(28,17,8,0.82) 50%,
            rgba(15,10,4,0.90) 100%
        ),
        url("https://images.unsplash.com/photo-1544735716-392fe2489ffa?q=80&w=1920");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
    font-family: 'Inter', sans-serif;
}

/* ── Hide default Streamlit chrome ── */
header, footer, #MainMenu { visibility: hidden; }
.block-container {
    padding-top: 0 !important;
    max-width: 860px !important;
    margin: 0 auto;
}

/* ── TOP HEADER BAR (mimics Naman Darshan orange nav) ── */
.nd-header {
    background: linear-gradient(135deg, #F97316 0%, #EA580C 100%);
    padding: 0;
    margin: -1rem -1rem 0 -1rem;
    border-bottom: 2px solid #C2410C;
    box-shadow: 0 4px 20px rgba(249,115,22,0.4);
}

.nd-header-inner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 28px;
    max-width: 860px;
    margin: 0 auto;
}

.nd-logo {
    display: flex;
    align-items: center;
    gap: 10px;
}

.nd-logo-symbol {
    font-size: 28px;
    line-height: 1;
}

.nd-logo-text {
    font-family: 'Playfair Display', serif;
    font-size: 22px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 0.5px;
    line-height: 1.1;
}

.nd-logo-tagline {
    font-size: 10px;
    font-weight: 400;
    color: rgba(255,255,255,0.85);
    letter-spacing: 2px;
    text-transform: uppercase;
    font-family: 'Inter', sans-serif;
}

.nd-header-badge {
    background: rgba(255,255,255,0.18);
    border: 1px solid rgba(255,255,255,0.35);
    color: white;
    font-size: 12px;
    font-weight: 500;
    padding: 6px 14px;
    border-radius: 20px;
    display: flex;
    align-items: center;
    gap: 6px;
    backdrop-filter: blur(4px);
}

/* ── TICKER BAND (mimics "100% Darshan Guaranteed" scrolling band) ── */
.nd-ticker {
    background: #1C1108;
    border-bottom: 1px solid rgba(249,115,22,0.2);
    overflow: hidden;
    padding: 7px 0;
    margin: 0 -1rem;
}

.nd-ticker-inner {
    display: flex;
    gap: 40px;
    animation: tickerScroll 20s linear infinite;
    white-space: nowrap;
    width: max-content;
}

.nd-ticker-item {
    color: var(--nd-orange);
    font-size: 12px;
    font-weight: 500;
    display: inline-flex;
    align-items: center;
    gap: 8px;
}

@keyframes tickerScroll {
    0%   { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}

/* ── CHAT CONTAINER ── */
.nd-chat-wrap {
    padding: 16px 0 90px 0;
}

/* ── USER MESSAGE ── */
.user-msg {
    display: flex;
    justify-content: flex-end;
    margin: 10px 0;
}

.user-bubble {
    background: linear-gradient(135deg, #F97316 0%, #EA580C 100%);
    color: #ffffff;
    padding: 12px 18px;
    border-radius: 20px 20px 4px 20px;
    max-width: 72%;
    font-size: 15px;
    line-height: 1.55;
    font-weight: 500;
    box-shadow: 0 4px 16px rgba(249,115,22,0.35);
    position: relative;
}

.user-avatar {
    width: 32px;
    height: 32px;
    background: rgba(249,115,22,0.25);
    border: 1.5px solid #F97316;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    flex-shrink: 0;
    margin-left: 10px;
    align-self: flex-end;
}

/* ── BOT MESSAGE ── */
.bot-msg {
    display: flex;
    justify-content: flex-start;
    margin: 10px 0;
    gap: 10px;
}

.bot-avatar {
    width: 36px;
    height: 36px;
    background: linear-gradient(135deg, #F97316, #EA580C);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
    align-self: flex-end;
    box-shadow: 0 2px 10px rgba(249,115,22,0.4);
}

.bot-bubble {
    background: rgba(28, 17, 8, 0.75);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    color: var(--nd-text);
    padding: 14px 18px;
    border-radius: 20px 20px 20px 4px;
    max-width: 76%;
    font-size: 15px;
    line-height: 1.65;
    border: 1px solid var(--nd-border);
    box-shadow: 0 4px 24px rgba(0,0,0,0.3), inset 0 1px 0 rgba(249,115,22,0.08);
    white-space: pre-wrap;
}

/* ── DIVIDER ── */
.nd-divider {
    border: none;
    border-top: 1px solid rgba(249,115,22,0.15);
    margin: 6px 0;
}

/* ── CHAT INPUT AREA (outer fixed wrapper) ── */
[data-testid="stChatInput"] {
    position: fixed !important;
    bottom: 0 !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    width: min(860px, 100vw) !important;
    padding: 16px 20px !important;
    background: linear-gradient(
        0deg,
        rgba(15,10,4,0.98) 0%,
        rgba(15,10,4,0.92) 80%,
        transparent 100%
    ) !important;
    border-top: 1px solid rgba(249,115,22,0.2) !important;
    backdrop-filter: blur(20px) !important;
    z-index: 999 !important;
    box-sizing: border-box !important;
}

/* ── INNER FLEX ROW (textarea + button side by side) ── */
.stChatInputContainer {
    display: flex !important;
    align-items: flex-end !important;
    gap: 10px !important;
    width: 100% !important;
    box-sizing: border-box !important;
}

[data-testid="stChatInput"] textarea {
    flex: 1 1 auto !important;
    min-width: 0 !important;
    background: rgba(28,17,8,0.9) !important;
    border: 1.5px solid rgba(249,115,22,0.4) !important;
    border-radius: 12px !important;
    color: var(--nd-text) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 15px !important;
    padding: 12px 16px !important;
    resize: none !important;
    transition: border-color 0.2s ease !important;
    box-sizing: border-box !important;
}

[data-testid="stChatInput"] textarea:focus {
    border-color: #F97316 !important;
    box-shadow: 0 0 0 3px rgba(249,115,22,0.15) !important;
    outline: none !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: rgba(245,240,232,0.4) !important;
}

[data-testid="stChatInput"] button,
[data-testid="stChatInputSubmitButton"] {
    flex: 0 0 44px !important;
    width: 44px !important;
    min-width: 44px !important;
    height: 44px !important;
    background: linear-gradient(135deg, #F97316, #EA580C) !important;
    border: none !important;
    border-radius: 10px !important;
    position: relative !important;
    overflow: visible !important;
    cursor: pointer !important;
    transition: opacity 0.2s ease, transform 0.1s ease !important;
}

[data-testid="stChatInput"] button:hover,
[data-testid="stChatInputSubmitButton"]:hover {
    opacity: 0.9 !important;
    transform: scale(1.05) !important;
}

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: rgba(249,115,22,0.4);
    border-radius: 4px;
}

/* ── GUARANTEE STAMP ── */
.nd-guarantee {
    display: flex;
    align-items: center;
    gap: 6px;
    background: rgba(249,115,22,0.1);
    border: 1px solid rgba(249,115,22,0.3);
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
    color: var(--nd-orange);
    font-weight: 600;
    width: fit-content;
    margin: 0 auto 12px auto;
}

/* ── SEND BUTTON — up arrow (absolute centered) ── */
[data-testid="stChatInput"] button svg,
[data-testid="stChatInputSubmitButton"] svg {
    opacity: 0 !important;
    position: absolute !important;
    width: 0 !important;
    height: 0 !important;
}
[data-testid="stChatInput"] button::after,
[data-testid="stChatInputSubmitButton"]::after {
    content: '↑';
    font-size: 22px;
    font-weight: 800;
    color: white !important;
    position: absolute !important;
    top: 50% !important;
    left: 50% !important;
    transform: translate(-50%, -50%) !important;
    line-height: 1;
    display: block !important;
    pointer-events: none;
}

/* ── MOBILE RESPONSIVE ── */
@media (max-width: 768px) {
    .block-container {
        padding: 0 6px !important;
    }
    .bot-bubble {
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
        background: rgba(20, 12, 4, 0.97) !important;
        max-width: 88% !important;
        font-size: 14px !important;
    }
    .user-bubble {
        max-width: 88% !important;
        font-size: 14px !important;
    }
    .stChatInputContainer, [data-testid="stChatInput"] {
        left: 0 !important;
        transform: none !important;
        width: 100vw !important;
        padding: 10px 12px !important;
        box-sizing: border-box !important;
    }
    .nd-header-inner {
        padding: 10px 14px;
    }
    .nd-logo-text {
        font-size: 17px !important;
    }
    .nd-logo-tagline {
        font-size: 9px !important;
    }
    .nd-ticker {
        display: none;
    }
    .nd-header-badge {
        font-size: 11px;
        padding: 4px 10px;
    }
    .bot-avatar {
        width: 30px !important;
        height: 30px !important;
        font-size: 14px !important;
    }
    .user-avatar {
        width: 26px !important;
        height: 26px !important;
        font-size: 12px !important;
    }
}

</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# HEADER — Naman Darshan branding
# ---------------------------------------------------

st.markdown("""
<div class="nd-header">
    <div class="nd-header-inner">
        <div class="nd-logo">
            <div class="nd-logo-symbol">🙏</div>
            <div>
                <div class="nd-logo-text">Naman Darshan</div>
                <div class="nd-logo-tagline">Seva · Suvidha · Samarpan</div>
            </div>
        </div>
        <div class="nd-header-badge">
            <span>✦</span> AI Darshan Assistant
        </div>
    </div>
</div>

<div class="nd-ticker">
    <div class="nd-ticker-inner">
        <span class="nd-ticker-item">✅ 100% Darshan Guaranteed</span>
        <span class="nd-ticker-item">🙏 India's Largest Community for Devotees</span>
        <span class="nd-ticker-item">⭐ 4.7 Stars · 40 Lakh+ Devotees Served</span>
        <span class="nd-ticker-item">🕌 VIP Darshan at 50+ Sacred Temples</span>
        <span class="nd-ticker-item">✅ 100% Darshan Guaranteed</span>
        <span class="nd-ticker-item">🙏 India's Largest Community for Devotees</span>
        <span class="nd-ticker-item">⭐ 4.7 Stars · 40 Lakh+ Devotees Served</span>
        <span class="nd-ticker-item">🕌 VIP Darshan at 50+ Sacred Temples</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# CHAT MESSAGES
# ---------------------------------------------------

st.markdown('<div class="nd-chat-wrap">', unsafe_allow_html=True)

for msg in st.session_state.messages:

    if msg["role"] == "user":
        content = msg['content'].replace('<', '&lt;').replace('>', '&gt;')
        st.markdown(
            f"""
            <div class="user-msg">
                <div class="user-bubble">🙋 {content}</div>
                <div class="user-avatar">👤</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        rendered = msg['content'].strip().replace('<', '&lt;').replace('>', '&gt;')
        st.markdown(
            f"""
            <div class="bot-msg">
                <div class="bot-avatar">🙏</div>
                <div class="bot-bubble">{rendered}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------
# CHAT INPUT
# ---------------------------------------------------

user_input = st.chat_input("Ask about VIP Darshan...")

# ---------------------------------------------------
# RESPONSE
# ---------------------------------------------------

if user_input:

    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    # Build history from session_state so ALL exchanges (including state-machine
    # turns for temple/date/people) are visible to the LLM — not just MongoDB turns.
    history = []
    msgs = st.session_state.messages[:-1]  # exclude current user message
    i = 0
    while i < len(msgs) - 1:
        if msgs[i]["role"] == "user" and msgs[i + 1]["role"] == "assistant":
            history.append({
                "user": msgs[i]["content"],
                "assistant": msgs[i + 1]["content"]
            })
            i += 2
        else:
            i += 1

    with st.spinner("🙏 Preparing your darshan details..."):
        response = generate_response(
            query=user_input,
            history=history,
            user_id=user_id
        )

    # Also save to MongoDB for persistence across sessions
    save_memory(
        user_id,
        user_input,
        response
    )

    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })

    st.rerun()