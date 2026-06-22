import streamlit as st
import uuid
import importlib
import datetime

# Force reload sub-modules so Streamlit picks up changes dynamically
import razorpay_handler
import prompt_builder
import recommendation_engine
import qa_handler
import rag_pipeline

importlib.reload(razorpay_handler)
importlib.reload(prompt_builder)
importlib.reload(recommendation_engine)
importlib.reload(qa_handler)
importlib.reload(rag_pipeline)

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

if "submitted_val" not in st.session_state:
    st.session_state.submitted_val = None

user_id = st.session_state.user_id

# ---------------------------------------------------
# HELPER
# ---------------------------------------------------

def fmt_time():
    now = datetime.datetime.now()
    return now.strftime("%I:%M %p").lstrip("0")

# ---------------------------------------------------
# INITIAL BOT MESSAGE
# ---------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "🙏 Namaste! Welcome to NAMAN DARSHAN\n\n"
                "I'm your AI Sales Assistant.\n"
                "How can I help you plan your spiritual journey today?"
            ),
            "time": fmt_time()
        }
    ]

# ---------------------------------------------------
# BUILD MESSAGES HTML
# ---------------------------------------------------

def build_messages_html(messages):
    parts = []
    for msg in messages:
        t = msg.get("time", fmt_time())
        if msg["role"] == "user":
            content = (
                msg['content']
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('\n', '<br>')
            )
            parts.append(f"""
<div class="user-row">
  <div class="user-col">
    <div class="user-bubble">
      <div class="msg-content">{content}</div>
      <div class="msg-meta">{t} <span class="user-tick">&#10003;&#10003;</span></div>
    </div>
  </div>
</div>""")
        else:
            content = (
                msg['content'].strip()
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('\n', '<br>')
            )
            parts.append(f"""
<div class="bot-row">
  <div class="bot-av">
    <svg viewBox="0 0 24 24" width="20" height="20" fill="#FF6B00">
      <path d="M12 2L2 9h20L12 2zm0 3.3L17.2 9H6.8L12 5.3zM4 10v9h16v-9H4zm3 2h2v5H7v-5zm4 0h2v5h-2v-5zm4 0h2v5h-2v-5zM2 20v2h20v-2H2z"/>
    </svg>
  </div>
  <div class="bot-col">
    <div class="bot-bubble">
      <div class="msg-content">{content}</div>
      <div class="msg-meta">{t}</div>
    </div>
  </div>
</div>""")
    return "\n".join(parts)

# ---------------------------------------------------
# CSS — COMPLETE REDESIGN
# The key: we DON'T fight stBottom, we STYLE it.
# stBottom contains stChatInput which we fully restyle.
# ---------------------------------------------------

msgs_html = build_messages_html(st.session_state.messages)

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ══ PAGE BACKGROUND ══ */
html, body {{
  margin: 0; padding: 0;
  overflow: hidden !important;
  height: 100% !important;
  max-height: 100vh !important;
}}
.stApp {{
  background: #F6F2ED !important;
  font-family: 'Inter', sans-serif !important;
  overflow: hidden !important;
  height: 100vh !important;
  max-height: 100vh !important;
}}

.main, [data-testid="stMain"] {{
  overflow: hidden !important;
  height: 100vh !important;
}}

/* ══ HIDE STREAMLIT CHROME ══ */
header, footer, #MainMenu,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] {{
  display: none !important;
}}

/* ══ RESET BLOCK CONTAINER ══ */
.block-container {{
  padding: 0 !important;
  max-width: 100% !important;
  margin: 0 !important;
}}

.element-container, .stMarkdown {{
  margin: 0 !important;
  padding: 0 !important;
}}

.stVerticalBlock {{
  gap: 0 !important;
}}

/* ══ NAMAN DARSHAN HEADER — 85px, fixed top ══ */
.nd-header {{
  position: fixed;
  top: 0; left: 0; right: 0;
  height: 85px;
  background: linear-gradient(90deg, #FF6B00 0%, #FF9A3D 100%);
  display: flex;
  align-items: center;
  z-index: 2000;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(255, 107, 0, 0.12);
}}

.nd-header-inner {{
  display: flex; align-items: center;
  width: 100%; max-width: 1400px;
  padding: 0 48px;
  margin: 0 auto;
  position: relative; z-index: 2;
}}

.nd-logo {{
  display: flex; align-items: center; gap: 14px;
}}

.nd-logo-icon {{
  width: 48px; height: 48px;
  background: rgba(255,255,255,.95);
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 12px rgba(0,0,0,.1);
  flex-shrink: 0;
}}

.nd-logo-title {{
  font-size: 24px; font-weight: 800;
  color: #ffffff; letter-spacing: 1.5px;
  text-shadow: 0 1px 4px rgba(0,0,0,.12);
  line-height: 1.1;
  font-family: 'Inter', sans-serif;
}}

.nd-logo-tagline {{
  font-size: 12px; color: rgba(255,255,255,0.92);
  margin-top: 3px;
  font-weight: 500;
  font-family: 'Inter', sans-serif;
}}

.nd-om-wrap {{
  position: absolute; left: 50%; transform: translateX(-50%);
  display: flex; align-items: center; gap: 16px; z-index: 3;
}}

.nd-om-line {{
  width: 55px; height: 1.5px; background: rgba(255,255,255,.45);
}}

.nd-om-badge {{
  width: 46px; height: 46px;
  background: rgba(255,255,255,.95);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; font-weight: 700; color: #FF6B00;
  box-shadow: 0 4px 12px rgba(0,0,0,.1);
}}

.nd-skyline {{
  position: absolute; right: 0; bottom: 0;
  height: 100%; width: 380px; pointer-events: none;
  opacity: 0.32;
}}

/* ══ STREAMLIT WRAPPER: transparent, no visual styling ══ */
/* The visual card is composed of independently fixed elements */
.block-container div[data-testid="stVerticalBlock"]:first-child > div:has(.nd-card-head) {{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  position: static !important;
  display: block !important;
  width: auto !important;
  height: auto !important;
}}

.block-container div[data-testid="stVerticalBlock"]:first-child > div:has(.nd-card-head) > div[data-testid="stVerticalBlock"] {{
  display: block !important;
}}

.block-container div[data-testid="stVerticalBlock"]:first-child > div:has(.nd-card-head) > div[data-testid="stVerticalBlock"] > div {{
  display: block !important;
}}

.block-container div[data-testid="stVerticalBlock"]:first-child > div:has(.nd-card-head) > div[data-testid="stVerticalBlock"] > div > div[data-testid="stMarkdown"] {{
  display: block !important;
}}

/* ══ WHITE CARD BACKGROUND — visual card via nd-card-bg ══ */
.nd-card-bg {{
  position: fixed !important;
  top: 95px !important;
  left: 50% !important;
  transform: translateX(-50%) !important;
  width: min(1240px, calc(100vw - 80px)) !important;
  height: 522px !important;
  background: #ffffff !important;
  border-radius: 24px !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.08), 0 1px 4px rgba(0,0,0,0.03) !important;
  border: 1px solid #EFE7DE !important;
  z-index: 499 !important;
  pointer-events: none !important;
  box-sizing: border-box !important;
}}

/* ══ AI HEADER — fixed directly at card-top position ══ */
.nd-card-head {{
  position: fixed !important;
  top: 95px !important;
  left: 50% !important;
  transform: translateX(-50%) !important;
  width: min(1240px, calc(100vw - 80px)) !important;
  height: 70px !important;
  box-sizing: border-box !important;
  background: linear-gradient(90deg, #FF6B00 0%, #FF9A3D 100%) !important;
  display: flex !important;
  flex-direction: column !important;
  justify-content: center !important;
  padding: 0 28px !important;
  border-radius: 24px 24px 0 0 !important;
  overflow: hidden !important;
  z-index: 600 !important;
  flex-shrink: 0 !important;
}}

.nd-card-head-pattern {{
  position: absolute;
  top: -20px; right: -20px;
  width: 130px; height: 130px;
  opacity: 0.12;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ccircle cx='50' cy='50' r='40' stroke='white' stroke-width='0.5' fill='none'/%3E%3Ccircle cx='50' cy='50' r='30' stroke='white' stroke-width='0.5' fill='none'/%3E%3Ccircle cx='50' cy='50' r='20' stroke='white' stroke-width='0.5' fill='none'/%3E%3Cpath d='M50 0 L50 100 M0 50 L100 50 M15 15 L85 85 M15 85 L85 15' stroke='white' stroke-width='0.3'/%3E%3Cpath d='M50 10 Q60 50 50 90 Q40 50 50 10 M10 50 Q50 60 90 50 Q50 40 10 50' fill='white' opacity='0.5'/%3E%3Cpath d='M25 25 Q50 60 75 75 Q60 50 25 25 M25 75 Q60 50 75 25 Q50 60 25 75' fill='white' opacity='0.5'/%3E%3C/svg%3E");
  background-size: cover;
  pointer-events: none;
}}

.nd-card-head-row {{
  display: flex; align-items: center; gap: 12px;
  position: relative; z-index: 2;
}}

.nd-card-head-star {{ 
  display: flex;
  align-items: center;
  justify-content: center;
  animation: pulse 2s infinite ease-in-out;
}}

@keyframes pulse {{
  0% {{ transform: scale(1); opacity: 0.8; }}
  50% {{ transform: scale(1.1); opacity: 1; }}
  100% {{ transform: scale(1); opacity: 0.8; }}
}}

.nd-card-head-title {{ 
  font-size: 19px; 
  font-weight: 700; 
  color: #ffffff; 
  letter-spacing: .3px;
  line-height: 1.2;
  font-family: 'Inter', sans-serif;
}}

.nd-card-head-sub {{ 
  font-size: 12.5px; 
  color: rgba(255,255,255,0.88); 
  margin-top: 2px;
  font-family: 'Inter', sans-serif;
}}

/* ══ MESSAGES AREA — fixed, starts immediately below AI header ══ */
.nd-msgs {{
  position: fixed !important;
  top: calc(95px + 70px) !important;
  left: 50% !important;
  transform: translateX(-50%) !important;
  width: min(1240px, calc(100vw - 80px)) !important;
  height: 380px !important;
  overflow-y: auto !important;
  padding: 16px 24px !important;
  padding-bottom: 16px !important;
  box-sizing: border-box !important;
  background: #ffffff !important;
  z-index: 600 !important;
}}

.bot-row {{
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 18px;
  margin-top: 0;
}}

.bot-av {{
  width: 38px; height: 38px;
  background: #FFF3E8;
  border: 1px solid #EFE7DE;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; margin-top: 2px;
}}

.bot-col {{ max-width: 72%; }}

.bot-bubble {{
  background: #ffffff !important;
  border: 1px solid #EFE7DE !important;
  color: #222222 !important;
  padding: 14px 18px !important;
  border-radius: 18px !important;
  font-size: 14px !important;
  line-height: 1.6 !important;
  box-shadow: 0 2px 10px rgba(0,0,0,0.04) !important;
  word-break: break-word !important;
}}

.user-row {{
  display: flex;
  justify-content: flex-end;
  align-items: flex-end;
  margin-bottom: 18px;
  margin-top: 0;
}}

.user-col {{ max-width: 72%; }}

.user-bubble {{
  background: #FFF3E8 !important;
  border: 1px solid #F5D9BC !important;
  color: #222222 !important;
  padding: 14px 18px !important;
  border-radius: 18px !important;
  font-size: 14px !important;
  line-height: 1.6 !important;
  font-weight: 500 !important;
  box-shadow: 0 2px 10px rgba(255, 107, 0, 0.05) !important;
  word-break: break-word !important;
}}

.msg-content {{
  margin-bottom: 5px;
}}

.msg-meta {{
  font-size: 10px;
  color: #BBBBBB;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  margin-top: 2px;
}}

.user-tick {{
  color: #FF6B00;
  font-weight: bold;
  letter-spacing: -1.5px;
}}

.nd-msgs::-webkit-scrollbar {{ width: 4px; }}
.nd-msgs::-webkit-scrollbar-track {{ background: transparent; }}
.nd-msgs::-webkit-scrollbar-thumb {{ background: rgba(255, 107, 0, 0.18); border-radius: 4px; }}

/* ══ INPUT SECTION — positioned below the card as a separate bar ══ */
/* nd-input-marker identifies the input area in the DOM */
.nd-input-marker {{
  display: none !important;
}}

/* Target the input container: nested stVerticalBlock that contains nd-input-marker */
div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"]:has(.nd-input-marker) {{
  position: fixed !important;
  top: calc(95px + 70px + 380px) !important;
  left: 50% !important;
  transform: translateX(-50%) !important;
  width: min(1240px, calc(100vw - 80px)) !important;
  background: #FAFAF8 !important;
  border: 1px solid #EFE7DE !important;
  border-top: none !important;
  border-radius: 0 0 24px 24px !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.06) !important;
  z-index: 600 !important;
  box-sizing: border-box !important;
  padding: 0 !important;
  margin: 0 !important;
}}

/* The actual horizontal block inside the input container */
div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"]:has(.nd-input-marker) div[data-testid="stHorizontalBlock"] {{
  width: 100% !important;
  padding: 12px 24px !important;
  margin: 0 !important;
  background: transparent !important;
  box-sizing: border-box !important;
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  gap: 14px !important;
}}

div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"]:has(.nd-input-marker) div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {{
  background: transparent !important;
  background-color: transparent !important;
  padding: 0 !important;
  margin: 0 !important;
  min-width: 0 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}}

div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"]:has(.nd-input-marker) div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:first-child {{
  flex: 1 1 auto !important;
  width: auto !important;
}}

div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"]:has(.nd-input-marker) div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:last-child {{
  flex: 0 0 48px !important;
  width: 48px !important;
  min-width: 48px !important;
  max-width: 48px !important;
}}

div[data-testid="stTextInput"] {{
  width: 100% !important;
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  margin: 0 !important;
}}

div[data-testid="stTextInput"] div {{
  border: none !important;
  background-color: transparent !important;
  background: transparent !important;
  box-shadow: none !important;
  outline: none !important;
}}

div[data-testid="stTextInput"] input {{
  background: #ffffff !important;
  border: 1px solid #EFE7DE !important;
  border-radius: 30px !important;
  color: #333333 !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 14px !important;
  padding: 0 24px !important;
  height: 56px !important;
  min-height: 56px !important;
  max-height: 56px !important;
  outline: none !important;
  line-height: 56px !important;
  transition: all .2s ease !important;
  box-shadow: 0 2px 10px rgba(0,0,0,0.04) !important;
  box-sizing: border-box !important;
  width: 100% !important;
}}

div[data-testid="stTextInput"] input:focus {{
  border-color: #FF6B00 !important;
  box-shadow: 0 0 0 3px rgba(255, 107, 0, 0.07) !important;
}}

div[data-testid="stTextInput"] input::placeholder {{
  color: #C0C0C0 !important;
  white-space: nowrap !important;
  text-overflow: ellipsis !important;
  overflow: hidden !important;
}}

div[data-testid="stButton"] {{
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  margin: 0 !important;
  height: 56px !important;
}}

div[data-testid="stButton"] button {{
  width: 48px !important;
  height: 48px !important;
  min-width: 48px !important;
  max-width: 48px !important;
  border: none !important;
  border-radius: 50% !important;
  cursor: pointer !important;
  background:
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='white'%3E%3Cpath d='M2.01 21L23 12 2.01 3 2 10l15 2-15 2z'/%3E%3C/svg%3E") no-repeat center,
    linear-gradient(135deg, #FF6B00, #FF9A3D) !important;
  background-size: 18px, cover !important;
  box-shadow: 0 4px 16px rgba(255, 107, 0, 0.35) !important;
  transition: all .2s ease !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  opacity: 1 !important;
  visibility: visible !important;
  transform: rotate(-30deg) !important;
  color: transparent !important;
  font-size: 0 !important;
  padding: 0 !important;
}}

div[data-testid="stButton"] button:hover {{
  filter: brightness(1.08) !important;
  transform: scale(1.06) rotate(-30deg) !important;
  box-shadow: 0 6px 20px rgba(255, 107, 0, 0.45) !important;
  color: transparent !important;
}}

div[data-testid="stButton"] button:active,
div[data-testid="stButton"] button:focus {{
  background:
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='white'%3E%3Cpath d='M2.01 21L23 12 2.01 3 2 10l15 2-15 2z'/%3E%3C/svg%3E") no-repeat center,
    linear-gradient(135deg, #FF6B00, #FF9A3D) !important;
  background-size: 18px, cover !important;
  color: transparent !important;
  outline: none !important;
  border: none !important;
  box-shadow: 0 4px 16px rgba(255, 107, 0, 0.35) !important;
}}

div[data-testid="stButton"] button p {{
  display: none !important;
}}

/* ══ BOTTOM NAV — below chat card, same width ══ */
.nd-nav {{
  position: fixed !important;
  top: calc(95px + 70px + 380px + 72px + 10px) !important;
  left: 50% !important;
  transform: translateX(-50%) !important;
  width: min(1240px, calc(100vw - 80px)) !important;
  background: #ffffff !important;
  border-radius: 20px !important;
  border: 1px solid #EFE7DE !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-around !important;
  padding: 12px 12px !important;
  z-index: 1600 !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.05) !important;
  box-sizing: border-box !important;
}}

.nd-nav-item {{
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  gap: 8px !important;
  flex: 1 !important;
  padding: 4px 4px !important;
  cursor: pointer !important;
  transition: all 0.2s ease !important;
  border-right: 1px solid #EFE7DE !important;
}}

.nd-nav-item:last-child {{
  border-right: none !important;
}}

.nd-nav-item:hover {{
  background: #FFF8F2 !important;
  border-radius: 12px !important;
  transform: translateY(-2px) !important;
}}

.nd-nav-ic {{
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  height: 32px !important;
}}

.nd-nav-ic svg {{
  transition: transform 0.2s ease !important;
}}

.nd-nav-item:hover .nd-nav-ic svg {{
  transform: scale(1.1) !important;
}}

.nd-nav-lbl {{
  font-size: 12px !important;
  font-weight: 600 !important;
  color: #333333 !important;
  text-align: center !important;
  white-space: nowrap !important;
  font-family: 'Inter', sans-serif !important;
}}

/* ══ TABLET (768–1024px) ══ */
@media (max-width: 1024px) and (min-width: 641px) {{
  div[data-testid="stVerticalBlock"] > div:has(.nd-card-head) {{
    width: calc(100vw - 60px) !important;
    height: 680px !important;
  }}
  .nd-nav {{
    width: calc(100vw - 60px) !important;
  }}
  .nd-header-inner {{ padding: 0 30px; }}
}}

/* ══ MOBILE (≤640px) ══ */
@media (max-width: 640px) {{
  .nd-header {{ height: 70px !important; }}
  .nd-header-inner {{ padding: 0 14px; }}
  .nd-logo-title {{ font-size: 16px !important; letter-spacing: 0.8px !important; }}
  .nd-logo-tagline {{ font-size: 10px !important; }}
  .nd-om-line {{ width: 20px !important; }}
  .nd-om-badge {{ width: 34px !important; height: 34px !important; font-size: 14px !important; }}
  .nd-logo-icon {{ width: 36px !important; height: 36px !important; }}
  div[data-testid="stVerticalBlock"] > div:has(.nd-card-head) {{
    left: 0 !important;
    transform: none !important;
    width: 100vw !important;
    top: 78px !important;
    height: calc(100vh - 78px - 120px) !important;
    border-radius: 0 !important;
  }}
  .nd-nav {{
    left: 0 !important;
    transform: none !important;
    width: 100vw !important;
    top: auto !important;
    bottom: 0 !important;
    border-radius: 0 !important;
    padding: 10px 4px !important;
  }}
  .nd-nav-lbl {{ font-size: 10px !important; white-space: normal !important; text-align: center !important; }}
  .nd-card-head {{ height: 72px !important; padding: 0 16px !important; }}
  .nd-msgs {{ padding: 14px 14px !important; }}
  div[data-testid="stVerticalBlock"] > div:has(.nd-card-head) div[data-testid="stHorizontalBlock"] {{ padding: 12px 14px !important; }}
}}

/* ══ STREAMLIT COMPONENTS IFRAME FIX ══ */
div[data-testid="stHtml"] {{
  pointer-events: none !important;
  position: absolute !important;
  height: 0 !important;
  width: 0 !important;
  overflow: hidden !important;
  z-index: -1 !important;
}}
</style>

<!-- ══ NAMAN DARSHAN HEADER ══ -->
<div class="nd-header">
  <svg class="nd-skyline" viewBox="0 0 300 78" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMaxYMax meet">
    <g fill="rgba(255,255,255,0.15)">
      <rect x="130" y="22" width="30" height="56"/>
      <polygon points="130,22 145,3 160,22"/>
      <rect x="135" y="6" width="20" height="8"/>
      <circle cx="145" cy="3" r="3"/>
      <rect x="144" y="0" width="2" height="15" fill="rgba(255,255,255,0.22)"/>
      <rect x="85" y="32" width="24" height="46"/>
      <polygon points="85,32 97,14 109,32"/>
      <circle cx="97" cy="13" r="2"/>
      <rect x="96" y="9" width="2" height="14" fill="rgba(255,255,255,0.22)"/>
      <rect x="178" y="36" width="22" height="42"/>
      <polygon points="178,36 189,20 200,36"/>
      <circle cx="189" cy="19" r="2"/>
      <rect x="188" y="15" width="2" height="13" fill="rgba(255,255,255,0.22)"/>
      <rect x="215" y="44" width="16" height="34"/>
      <polygon points="215,44 223,31 231,44"/>
      <circle cx="223" cy="30" r="1.5"/>
      <rect x="55" y="50" width="14" height="28"/>
      <polygon points="55,50 62,38 69,50"/>
      <circle cx="62" cy="37" r="1.3"/>
      <rect x="243" y="52" width="13" height="26"/>
      <polygon points="243,52 249,42 255,52"/>
      <circle cx="249" cy="41" r="1.2"/>
      <path d="M262 14 Q265 11 268 14" stroke="rgba(255,255,255,0.2)" stroke-width="1.5" fill="none"/>
      <path d="M273 9 Q276 6 279 9" stroke="rgba(255,255,255,0.2)" stroke-width="1.5" fill="none"/>
      <path d="M285 17 Q287 14 289 17" stroke="rgba(255,255,255,0.2)" stroke-width="1.5" fill="none"/>
    </g>
  </svg>
  <div class="nd-header-inner">
    <div class="nd-logo">
      <div class="nd-logo-icon">
        <svg viewBox="0 0 24 24" width="28" height="28" fill="#FF6B00">
          <path d="M12 2.5l-9 6V10h18V8.5l-9-6zm-7 9v8h14v-8H5zm4 2h2v4H9v-4zm4 0h2v4h-2v-4z"/>
        </svg>
      </div>
      <div>
        <div class="nd-logo-title">NAMAN DARSHAN</div>
        <div class="nd-logo-tagline">Your Spiritual Journey, Our Priority</div>
      </div>
    </div>
    <div class="nd-om-wrap">
      <div class="nd-om-line"></div>
      <div class="nd-om-badge">&#2384;</div>
      <div class="nd-om-line"></div>
    </div>
  </div>
</div>

<!-- ══ WHITE CARD BACKGROUND ══ -->
<div class="nd-card-bg"></div>

<!-- ══ BOTTOM NAV ══ -->
<div class="nd-nav">
  <div class="nd-nav-item">
    <div class="nd-nav-ic">
      <svg viewBox="0 0 24 24" width="26" height="26" fill="#FF6B00">
        <path d="M12 2c-.6 0-1.1.4-1.3.9L8.2 9H4v2h3.5l1.6 4.8c.3.9 1.1 1.2 1.9 1.2.3 0 .6-.1.8-.2l3-1.5c.3-.1.5-.4.5-.8v-5.5h3c.6 0 1.1-.4 1.3-.9l2.5-6.1c.3-.6-.2-1.3-.9-1.3h-8.3zm0 2h6.1l-1.6 4H14V6.5c0-.6-.4-1-1-1s-1 .4-1 1V8h-1.6l-1.5-4.5c0-.3.3-.5.7-.5z"/>
      </svg>
    </div>
    <div class="nd-nav-lbl">Assisted Darshan</div>
  </div>
  <div class="nd-nav-item">
    <div class="nd-nav-ic">
      <svg viewBox="0 0 24 24" width="26" height="26" fill="#FF6B00">
        <path d="M12 2s-3 4-3 6c0 1.66 1.34 3 3 3s3-1.34 3-3c0-2-3-6-3-6zm-8 11c0 3.3 2.7 6 6 6h4c3.3 0 6-2.7 6-6H4z"/>
      </svg>
    </div>
    <div class="nd-nav-lbl">Puja</div>
  </div>
  <div class="nd-nav-item">
    <div class="nd-nav-ic">
      <svg viewBox="0 0 24 24" width="26" height="26" fill="#FF6B00">
        <path d="M12 3a3 3 0 0 0-3 3 3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0-3-3zm-4 6a2.5 2.5 0 0 0-2.5 2.5A2.5 2.5 0 0 0 8 14h8a2.5 2.5 0 0 0 2.5-2.5A2.5 2.5 0 0 0 16 9H8zm-6 7c0 2.8 2.2 5 5 5h10c2.8 0 5-2.2 5-5H2z"/>
      </svg>
    </div>
    <div class="nd-nav-lbl">Prasadam</div>
  </div>
  <div class="nd-nav-item">
    <div class="nd-nav-ic">
      <svg viewBox="0 0 24 24" width="26" height="26" fill="#FF6B00">
        <path d="M12 2a4 4 0 0 0-4 4c0 3 4 8 4 8s4-5 4-4a4 4 0 0 0-4-4zm-8 13c0 2.8 2.2 5 5 5h6c2.8 0 5-2.2 5-5a3 3 0 0 0-3-3h-10a3 3 0 0 0-3 3z"/>
      </svg>
    </div>
    <div class="nd-nav-lbl">Chadhava</div>
  </div>
  <div class="nd-nav-item">
    <div class="nd-nav-ic">
      <svg viewBox="0 0 24 24" width="26" height="26" fill="#FF6B00">
        <path d="M17 6h-2V4a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2v2H7a3 3 0 0 0-3 3v10a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3V9a3 3 0 0 0-3-3zm-6-2h2v2h-2V4zm7 15H6v-6h12v6zm0-8H6V9a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v2z"/>
      </svg>
    </div>
    <div class="nd-nav-lbl">Yatra Packages</div>
  </div>
  <div class="nd-nav-item">
    <div class="nd-nav-ic">
      <svg viewBox="0 0 24 24" width="26" height="26" fill="#FF6B00">
        <path d="M9 2L11 7L16 9L11 11L9 16L7 11L2 9L7 7L9 2zm8 10l1 2.5L21.5 15L19 16L18 18.5L17 16L14.5 15L17 14L18 11.5z"/>
      </svg>
    </div>
    <div class="nd-nav-lbl">Astro Services</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# CHAT CONTAINER & INPUT
# ---------------------------------------------------

def handle_submit():
    val = st.session_state.chat_input_val.strip()
    if val:
        st.session_state.submitted_val = val
        st.session_state.chat_input_val = ""

with st.container():
    msgs_html = build_messages_html(st.session_state.messages)
    
    st.markdown(f"""<!-- ══ CHAT CARD HEADER & MESSAGES ══ -->
<div class="nd-card-head">
  <div class="nd-card-head-pattern"></div>
  <div class="nd-card-head-row">
    <span class="nd-card-head-star">
      <svg viewBox="0 0 24 24" width="22" height="22" fill="white">
        <path d="M7 2L9 6.5L13.5 8.5L9 10.5L7 15L5 10.5L0.5 8.5L5 6.5L7 2zM17 12L18.2 14.8L21 16L18.2 17.2L17 20L15.8 17.2L13 16L15.8 14.8L17 12z"/>
      </svg>
    </span>
    <div>
      <div class="nd-card-head-title">AI Sales Assistant</div>
      <div class="nd-card-head-sub">Your personal spiritual journey expert</div>
    </div>
  </div>
</div>
<div class="nd-msgs" id="nd-msgs">
  {msgs_html}
</div>
""", unsafe_allow_html=True)

# Input section — in its own container so CSS can target it via nd-input-marker
with st.container():
    st.markdown('<div class="nd-input-marker"></div>', unsafe_allow_html=True)
    input_col, send_col = st.columns([12, 1])
    
    with input_col:
        st.text_input(
            label="Input",
            placeholder="Ask me anything about NAMAN DARSHAN...",
            label_visibility="collapsed",
            key="chat_input_val",
            on_change=handle_submit
        )
        
    with send_col:
        st.button(
            label="Send",
            key="chat_send_btn",
            on_click=handle_submit
        )


user_input = st.session_state.submitted_val
st.session_state.submitted_val = None

# ---------------------------------------------------
# RESPONSE HANDLING
# ---------------------------------------------------

if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "time": fmt_time()
    })

    history = []
    msgs = st.session_state.messages[:-1]
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

    save_memory(user_id, user_input, response)

    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
        "time": fmt_time()
    })

    st.rerun()

# ---------------------------------------------------
# JAVASCRIPT INJECTION VIA SANDBOXED IFRAME
# ---------------------------------------------------
st.components.v1.html("""
<script>
(function() {
  var doc = window.parent.document;
  var win = window.parent;
  
  // Cleanup any leftover debug element
  var existingDiag = doc.getElementById('diag-box');
  if (existingDiag) existingDiag.remove();
  
  // Lock Streamlit containers to prevent page scroll
  function lockScrollContainers() {
    var selectors = [
      '.stApp', '.main',
      '[data-testid="stMain"]',
      '[data-testid="stAppViewContainer"]',
      '.block-container', '.appview-container'
    ];
    selectors.forEach(function(sel) {
      var el = doc.querySelector(sel);
      if (el) {
        el.style.overflow = 'hidden';
        el.style.height = '100vh';
        el.style.maxHeight = '100vh';
        el.scrollTop = 0;
      }
    });
    doc.body.scrollTop = 0;
    doc.documentElement.scrollTop = 0;
    win.scrollTo(0, 0);
  }
  
  // Reorder: put input section at BOTTOM of card
  function reorderCard() {
    // Commented out DOM mutation to prevent React DOM manipulation errors.
    // React loses references/event listeners when raw JS reparents/appends elements,
    // which caused the text input field to become completely non-responsive/un-typeable.
    /*
    var hBlock = doc.querySelector('[data-testid="stHorizontalBlock"]');
    if (!hBlock) return;
    var cardHead = doc.querySelector('.nd-card-head');
    if (!cardHead) return;
    var hBlockAncestor = hBlock;
    var targetParent = null;
    while (hBlockAncestor && hBlockAncestor !== doc.body) {
      var parent = hBlockAncestor.parentElement;
      if (!parent) break;
      if (parent.contains(cardHead) && parent.getAttribute('data-testid') === 'stVerticalBlock') {
        targetParent = parent;
        break;
      }
      hBlockAncestor = parent;
    }
    if (!targetParent) return;
    if (hBlockAncestor.parentElement === targetParent) {
      targetParent.appendChild(hBlockAncestor);
    }
    */
    scrollMsgs();
  }
  
  function scrollMsgs() {
    var msgs = doc.getElementById('nd-msgs');
    if (msgs) msgs.scrollTop = msgs.scrollHeight;
  }

  function init() {
    lockScrollContainers();
    reorderCard();
    scrollMsgs();
  }
  
  init();
  [50, 150, 350, 700, 1200, 2500].forEach(function(t) {
    win.setTimeout(init, t);
  });
  
  var pending = false;
  var observer = new win.MutationObserver(function() {
    lockScrollContainers();
    if (!pending) {
      pending = true;
      win.requestAnimationFrame(function() {
        reorderCard();
        scrollMsgs();
        pending = false;
      });
    }
  });
  observer.observe(doc.body, { childList: true, subtree: true });
  
  ['scroll', 'wheel', 'touchmove'].forEach(function(evt) {
    win.addEventListener(evt, function() {
      win.scrollTo(0, 0);
      doc.body.scrollTop = 0;
      doc.documentElement.scrollTop = 0;
    }, { passive: true });
  });
})();
</script>
""", height=0, width=0)