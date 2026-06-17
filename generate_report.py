# generate_report.py
# Generates a PDF report of today's work on the Naman Darshan Sales AI backend.

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from datetime import date

OUTPUT = r"C:\Users\biswa\OneDrive\Desktop\AI_sales Agent\Naman_Darshan_Sales_AI_Work_Report.pdf"

# ── Colour palette ──────────────────────────────────────────────────────────
ORANGE      = colors.HexColor("#F97316")
DARK_BG     = colors.HexColor("#1C1108")
LIGHT_GREY  = colors.HexColor("#F5F0E8")
MID_GREY    = colors.HexColor("#D1D5DB")
GREEN       = colors.HexColor("#16A34A")
RED_SOFT    = colors.HexColor("#DC2626")
BLUE        = colors.HexColor("#2563EB")

# ── Document ────────────────────────────────────────────────────────────────
doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=A4,
    rightMargin=2*cm, leftMargin=2*cm,
    topMargin=2*cm,   bottomMargin=2*cm,
    title="Naman Darshan Sales AI — Work Report",
    author="Claude Code",
)

styles = getSampleStyleSheet()

# Custom styles
def S(name, **kw):
    base = kw.pop("parent", "Normal")
    s = ParagraphStyle(name, parent=styles[base], **kw)
    return s

TITLE   = S("TITLE",   fontSize=22, textColor=ORANGE,   spaceAfter=4,  alignment=TA_CENTER, fontName="Helvetica-Bold")
SUBTITLE= S("SUB",     fontSize=11, textColor=colors.grey, spaceAfter=16, alignment=TA_CENTER)
H1      = S("H1",      fontSize=15, textColor=ORANGE,   spaceBefore=18, spaceAfter=6,  fontName="Helvetica-Bold", borderPadding=(0,0,2,0))
H2      = S("H2",      fontSize=12, textColor=DARK_BG,  spaceBefore=12, spaceAfter=4,  fontName="Helvetica-Bold")
H3      = S("H3",      fontSize=10, textColor=BLUE,     spaceBefore=8,  spaceAfter=3,  fontName="Helvetica-Bold")
BODY    = S("BODY",    fontSize=9,  leading=14, spaceAfter=4, alignment=TA_JUSTIFY)
BULLET  = S("BULLET",  fontSize=9,  leading=13, spaceAfter=2, leftIndent=16, bulletIndent=6)
CODE    = S("CODE",    fontSize=8,  leading=12, fontName="Courier", backColor=colors.HexColor("#F3F4F6"),
            borderPadding=4, spaceAfter=4)
NOTE    = S("NOTE",    fontSize=8,  leading=12, textColor=colors.HexColor("#6B7280"), spaceAfter=3)
OK      = S("OK",      fontSize=9,  leading=13, textColor=GREEN, spaceAfter=2)
BAD     = S("BAD",     fontSize=9,  leading=13, textColor=RED_SOFT, spaceAfter=2)

def b(txt): return f"<b>{txt}</b>"
def i(txt): return f"<i>{txt}</i>"
def orange(txt): return f'<font color="#F97316">{txt}</font>'
def code(txt): return f'<font name="Courier" size="8">{txt}</font>'

story = []

# ═══════════════════════════════════════════════════════════════════════════
# COVER
# ═══════════════════════════════════════════════════════════════════════════
story += [
    Spacer(1, 1.2*cm),
    Paragraph("Naman Darshan", TITLE),
    Paragraph("Sales AI Agent — Backend Development Report", SUBTITLE),
    Paragraph(f"Date: {date.today().strftime('%B %d, %Y')}  |  Prepared by: Claude Code (Anthropic)", NOTE),
    HRFlowable(width="100%", thickness=2, color=ORANGE, spaceAfter=20),
]

# ═══════════════════════════════════════════════════════════════════════════
# 1. PROJECT OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════
story.append(Paragraph("1. Project Overview", H1))
story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY, spaceAfter=8))

story.append(Paragraph(
    "The Naman Darshan Sales AI Agent is a conversational AI chatbot that handles inbound "
    "VIP temple darshan booking enquiries. Built on Python with Streamlit (UI), Flask (REST API), "
    "Groq LLM (llama-3.3-70b-versatile), FAISS vectorstore (RAG), and MongoDB Atlas, "
    "it guides devotees through a 7-state booking flow and handles all major sales objections "
    "using scripts derived from the Naman Darshan inbound calling guide.", BODY))

tbl_data = [
    [b("Component"), b("Technology")],
    ["Frontend UI",        "Streamlit 1.57"],
    ["REST API",           "Flask + Flask-CORS"],
    ["LLM",               "Groq — llama-3.3-70b-versatile"],
    ["Vector Search",      "FAISS + HuggingFace sentence-transformers"],
    ["Database",           "MongoDB Atlas (temples_clone)"],
    ["Intent Detection",   "Rule-based keyword matching + rapidfuzz"],
    ["Language",           "Python 3.14"],
]
t = Table(tbl_data, colWidths=[7*cm, 9*cm])
t.setStyle(TableStyle([
    ("BACKGROUND",   (0,0), (-1,0), ORANGE),
    ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
    ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
    ("FONTSIZE",     (0,0), (-1,-1), 9),
    ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, colors.HexColor("#FFF7ED")]),
    ("GRID",         (0,0), (-1,-1), 0.4, MID_GREY),
    ("LEFTPADDING",  (0,0), (-1,-1), 8),
    ("RIGHTPADDING", (0,0), (-1,-1), 8),
    ("TOPPADDING",   (0,0), (-1,-1), 5),
    ("BOTTOMPADDING",(0,0), (-1,-1), 5),
]))
story += [t, Spacer(1, 0.4*cm)]

# ═══════════════════════════════════════════════════════════════════════════
# 2. COMPANY / SERVICE DETAILS (from PDF)
# ═══════════════════════════════════════════════════════════════════════════
story.append(Paragraph("2. Company & Service Details (from Requirements PDF)", H1))
story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY, spaceAfter=8))

details = [
    [b("Field"), b("Value")],
    ["Brand Name",         "Naman Darshan"],
    ["Registered Company", "Traininglobe Consultancy Pvt Ltd"],
    ["Office",             "Express Trade Tower, Sector 132, Noida"],
    ["Phone",              "+91 93119 73199"],
    ["Website",            "namandarshan.com"],
    ["Community Size",     "40 lakh+ (40 million+) devotees"],
    ["Rating",             "4.7 stars"],
    ["Successful Darshans","10,000–14,000+"],
    ["VIP Wait Time",      "20–30 minutes (vs 2–8 hours general queue)"],
    ["Guarantee",          "100% Darshan Guarantee — full refund if darshan doesn't happen"],
    ["GST Status",         "GST-Exempt — religious coordination services under Indian tax law"],
    ["Payment Options",    "UPI / QR Code  |  NEFT / Bank Transfer (to Traininglobe Consultancy Pvt Ltd)"],
]
t2 = Table(details, colWidths=[5.5*cm, 10.5*cm])
t2.setStyle(TableStyle([
    ("BACKGROUND",   (0,0), (-1,0), DARK_BG),
    ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
    ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
    ("FONTSIZE",     (0,0), (-1,-1), 9),
    ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, colors.HexColor("#F9FAFB")]),
    ("GRID",         (0,0), (-1,-1), 0.4, MID_GREY),
    ("LEFTPADDING",  (0,0), (-1,-1), 8),
    ("RIGHTPADDING", (0,0), (-1,-1), 8),
    ("TOPPADDING",   (0,0), (-1,-1), 5),
    ("BOTTOMPADDING",(0,0), (-1,-1), 5),
    ("VALIGN",       (0,0), (-1,-1), "TOP"),
]))
story += [t2, Spacer(1, 0.4*cm)]

# ═══════════════════════════════════════════════════════════════════════════
# 3. FILES CREATED & UPDATED
# ═══════════════════════════════════════════════════════════════════════════
story.append(Paragraph("3. Files Created & Updated", H1))
story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY, spaceAfter=8))

story.append(Paragraph(b("3.1  New Files Created"), H2))

new_files = [
    ("sales_logic.py", "Intent detection engine",
     "25+ intents including TRUST, COMPANY_NAME, GST, PRICE, OFFICIAL, DELAY, GUARANTEE, "
     "PACKAGE_DISCOVERY, HUMAN_AGENT, BOOKING_PROCESS, TIMINGS, AVAILABILITY, COORDINATOR, "
     "LANGUAGE_SUPPORT, SAFETY, ELDERLY_SUPPORT, CANCELLATION_PLAN, TRAVEL_PLANNING, "
     "PAYMENT_METHOD, PAYMENT_TIMING, SEND_DETAILS, CLOSE, TEMPLE_LIST, BOOKING, GENERAL. "
     "Uses keyword + rapidfuzz matching with priority ordering."),
    ("prompt_builder.py", "C-A-R-E sales prompt builder",
     "Full objection-handling scripts from the inbound calling PDF: TRUST (5-step Traininglobe "
     "explanation + NEFT option), COMPANY_NAME (Zomato analogy), GST (religious exemption as "
     "positive), PRICE (per-person anchoring + Ram Mandir 4.5hr story), OFFICIAL (Ola/Uber + "
     "Doctor analogy), DELAY (slot urgency + WhatsApp trust message), PACKAGE_DISCOVERY "
     "(entity validation — asks for destination before any recommendation). Contains "
     "get_sales_instruction() and build_prompt() used by rag_pipeline."),
    ("retriever.py", "FAISS vectorstore retriever",
     "Lazy-loads the FAISS index from the vectorstore/ folder. Auto-rebuilds if missing. "
     "Uses max_marginal_relevance_search() for diverse top-3 results. Returns empty string "
     "on error for graceful degradation."),
    ("rag_pipeline.py", "Main response generation engine",
     "7-state machine: GREETING → ASK_DATE → ASK_PEOPLE → ASK_ELDERLY → ASK_QUALIFICATION "
     "→ SERVICE_INTRO → NORMAL_CHAT. Intent routing, LLM call via Groq with 3x retry on "
     "429 rate-limits, progressive lead capture (name → phone), social proof tracking, "
     "per-intent RAG skip for scripted objections, PACKAGE_DISCOVERY entity validation."),
    ("update_mongodb.py", "MongoDB seeding script",
     "One-time script to populate company_info and objections collections with data from "
     "the requirements PDF. Updates all vip_packages with Traininglobe company fields."),
    ("run.ps1", "PowerShell launcher",
     "Replaces the broken myenv Scripts/ launcher. Sets PYTHONPATH to myenv/Lib/site-packages "
     "and calls Python 3.14 directly with 'python -m streamlit run app.py'."),
    ("run.bat", "Batch file launcher",
     "Double-clickable Windows batch file that does the same as run.ps1 — for users who "
     "prefer Explorer over PowerShell."),
    ("live_test.py", "Quick smoke test",
     "Imports generate_response and runs the PACKAGE_DISCOVERY query to verify the fix."),
]

for fname, title, desc in new_files:
    story.append(KeepTogether([
        Paragraph(f'<font name="Courier" color="#F97316">{fname}</font>  —  {title}', H3),
        Paragraph(desc, BODY),
    ]))

story.append(Spacer(1, 0.2*cm))
story.append(Paragraph(b("3.2  Existing Files Updated"), H2))

updated_files = [
    ("booking_flow.py",
     "Added 5 new session fields: delay_count (tracks how many times user delays), "
     "whatsapp_trust_sent (flag after trust message is sent), neft_offered, "
     "lead_warm, qualification."),
    ("rag_pipeline.py (GREETING state)",
     "Added PACKAGE_DISCOVERY interception before detect_temple() runs. Added handling "
     "for 15 objection intents so they are answered even when no temple has been mentioned yet. "
     "Fixed fallback — unknown input now asks for temple instead of saying 'we don't offer services'."),
    ("rag_pipeline.py (detect_temple — Pass 5b)",
     "Raised fuzzy cutoff from 0.70 → 0.82. Added minimum token length guard of 6 characters. "
     "This prevents short generic words like 'yatra' (5 chars) from fuzzy-matching short location "
     "keywords like 'katra' (5 chars, Vaishno Devi base town) at 0.80 similarity."),
    ("rag_pipeline.py (detect_temple — Pass 5c)",
     "Removed entirely. Comparing the full user text as a single string against alias keywords "
     "caused false positives (e.g. 'darta hoon' → Dwarkadhish). Token-level 5a/5b is sufficient."),
    ("rag_pipeline.py (call_llm)",
     "Added _NO_RAG_INTENTS set — scripted objection intents (TRUST, COMPANY_NAME, GST, PRICE, "
     "OFFICIAL, DELAY, GUARANTEE, etc.) skip RAG retrieval entirely. This prevents temple-specific "
     "vectorstore content from overriding the carefully crafted sales scripts."),
    ("rag_pipeline.py (NORMAL_CHAT state)",
     "Added PACKAGE_DISCOVERY entity validation: if destination (temple) is not yet known, "
     "returns the clarification message instead of calling the LLM or querying MongoDB."),
    ("sales_logic.py",
     "Added PACKAGE_DISCOVERY intent as the very first check, before TEMPLE_LIST. "
     "Catches 20+ phrasings: 'best yatra package', 'recommend darshan', 'suggest trip', "
     "'find package for me', 'plan yatra', 'best pilgrimage trip', etc."),
    ("prompt_builder.py",
     "Added PACKAGE_DISCOVERY instruction block with the exact clarification message "
     "and explicit LLM instruction to never assume or retrieve a temple/package."),
]

for fname, desc in updated_files:
    story.append(KeepTogether([
        Paragraph(f'<font name="Courier" color="#2563EB">{fname}</font>', H3),
        Paragraph(desc, BODY),
    ]))

# ═══════════════════════════════════════════════════════════════════════════
# 4. MONGODB UPDATES
# ═══════════════════════════════════════════════════════════════════════════
story.append(Paragraph("4. MongoDB Atlas Changes", H1))
story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY, spaceAfter=8))

story.append(Paragraph(
    f"Connection: {code('mongodb+srv://ayush:strongpassword123@sales-ai-backend.gofnxnk.mongodb.net/')}<br/>"
    f"Database: {code('temples_clone')}", BODY))

mongo_data = [
    [b("Collection"), b("Action"), b("Details")],
    ["company_info",  "Created",  "Brand name, legal name (Traininglobe Consultancy Pvt Ltd), "
                                  "office, phone, website, community size, rating, guarantee, "
                                  "GST status, payment options."],
    ["objections",    "Replaced", "12 comprehensive objection documents from the PDF calling script: "
                                  "TRUST, COMPANY_NAME, GST, PRICE, OFFICIAL, DELAY, CLOSE, "
                                  "TIMINGS, BENEFITS, GUARANTEE, PAYMENT_METHOD + authority."],
    ["vip_packages",  "Updated",  "All records updated with: service_provider, brand, payment_to "
                                  "(Traininglobe Consultancy Pvt Ltd), vip_wait_time, guarantee fields."],
    ["agent_rules",   "Created",  "Stores 8 critical bot rules, intent-entity validation config "
                                  "(PACKAGE_DISCOVERY requires destination), retrieval rules, "
                                  "follow-up trigger phrases, priority order."],
    ["chat_memory",   "Unchanged","Persists conversation history per user_id across sessions."],
    ["temples",       "Unchanged","General temple reference data."],
    ["darshans",      "Unchanged","Darshan-specific details per temple."],
]
t3 = Table(mongo_data, colWidths=[3.5*cm, 2.2*cm, 10.3*cm])
t3.setStyle(TableStyle([
    ("BACKGROUND",   (0,0), (-1,0), DARK_BG),
    ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
    ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
    ("FONTSIZE",     (0,0), (-1,-1), 8.5),
    ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, colors.HexColor("#F9FAFB")]),
    ("GRID",         (0,0), (-1,-1), 0.4, MID_GREY),
    ("LEFTPADDING",  (0,0), (-1,-1), 7),
    ("RIGHTPADDING", (0,0), (-1,-1), 7),
    ("TOPPADDING",   (0,0), (-1,-1), 5),
    ("BOTTOMPADDING",(0,0), (-1,-1), 5),
    ("VALIGN",       (0,0), (-1,-1), "TOP"),
]))
story += [t3, Spacer(1, 0.4*cm)]

# ═══════════════════════════════════════════════════════════════════════════
# 5. CONVERSATION STATE MACHINE
# ═══════════════════════════════════════════════════════════════════════════
story.append(Paragraph("5. Conversation State Machine", H1))
story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY, spaceAfter=8))

states = [
    [b("State"), b("Purpose"), b("Bot Question / Action")],
    ["GREETING",           "Detect temple from user's first message",
                           "Listens for temple name. Handles objections even before temple is known. "
                           "Asks: 'Which temple are you planning to visit?'"],
    ["ASK_DATE",           "Collect travel date",
                           "'Which date are you planning to travel?'"],
    ["ASK_PEOPLE",         "Collect group size",
                           "'How many people will be travelling?'"],
    ["ASK_ELDERLY",        "Detect elderly / children in group",
                           "'Will there be any elderly members or children in the group?'"],
    ["ASK_QUALIFICATION",  "Local vs outstation traveller",
                           "'Are you travelling from the local area or from another state?'"],
    ["SERVICE_INTRO",      "Soft VIP service pitch (once per session)",
                           "Presents queue-time contrast, 40 lakh+ devotees, 100% guarantee."],
    ["NORMAL_CHAT",        "Full LLM-powered sales conversation",
                           "Intent-routed responses. Progressive lead capture. Objection handling."],
]
t4 = Table(states, colWidths=[3.5*cm, 3.5*cm, 9*cm])
t4.setStyle(TableStyle([
    ("BACKGROUND",   (0,0), (-1,0), ORANGE),
    ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
    ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
    ("FONTSIZE",     (0,0), (-1,-1), 8.5),
    ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, colors.HexColor("#FFF7ED")]),
    ("GRID",         (0,0), (-1,-1), 0.4, MID_GREY),
    ("LEFTPADDING",  (0,0), (-1,-1), 7),
    ("RIGHTPADDING", (0,0), (-1,-1), 7),
    ("TOPPADDING",   (0,0), (-1,-1), 5),
    ("BOTTOMPADDING",(0,0), (-1,-1), 5),
    ("VALIGN",       (0,0), (-1,-1), "TOP"),
]))
story += [t4, Spacer(1, 0.4*cm)]

# ═══════════════════════════════════════════════════════════════════════════
# 6. BUGS FOUND & FIXED
# ═══════════════════════════════════════════════════════════════════════════
story.append(Paragraph("6. Bugs Found & Fixed", H1))
story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY, spaceAfter=8))

bugs = [
    ("BUG 1", "Substring 'no' matched inside 'Noida'",
     "The objection signal list used plain substring matching. 'no' was in the list to detect "
     "negative replies, but it also matched inside the word 'Noida'. When a user said "
     "'Hum Noida se aa rahe hain', it was wrongly detected as an objection/question, "
     "causing the qualification state to stall and calling the LLM unnecessarily.",
     "Replaced the plain substring list with a compiled regex using \\b word-boundary anchors "
     "(_OBJECTION_SIGNAL_REGEX). Added 'confirm', 'pehle', 'sochna', 'later', 'baad' to "
     "the pattern for better delay/objection detection."),
    ("BUG 2", "Greeting state returned 'we don't offer services' for objections",
     "In the GREETING state, when a user sent an objection (TRUST, GST, PRICE, DELAY, etc.) "
     "without mentioning a temple first, detect_temple() returned None. The fallback code "
     "then returned 'we do not currently offer VIP Darshan services for this temple' — "
     "completely wrong for a trust or price question.",
     "Added an _GREETING_OBJECTION_INTENTS check before detect_temple(). If intent is a known "
     "objection, call_llm() is invoked directly with the correct sales script."),
    ("BUG 3", "RAG context poisoned LLM objection responses",
     "call_llm() always retrieved RAG context via retrieve_docs(). For objection intents like "
     "TRUST, COMPANY_NAME, GST, the vectorstore returned temple-specific content "
     "(e.g. 'we do not offer services for this temple') which the LLM prioritised over the "
     "carefully written sales scripts, producing completely wrong answers.",
     "Defined _NO_RAG_INTENTS set. For 14 scripted objection intents, context is set to '' "
     "and retrieve_docs() is not called. RAG is only used for BENEFITS, TIMINGS, COORDINATOR, "
     "GENERAL, and other intents where temple knowledge is genuinely useful."),
    ("BUG 4", "'yatra' fuzzy-matched 'katra' → wrong Vaishno Devi response",
     "When user asked 'can you find best yatra packages for me?', the token 'yatra' (5 chars) "
     "was fuzzy-matched against 'katra' (Katra, the base town keyword for Vaishno Devi, 5 chars). "
     "Both share 4 characters (a-t-r-a), giving a SequenceMatcher ratio of 0.80 — above the old "
     "cutoff of 0.70. The bot silently assumed Vaishno Devi and asked for a travel date.",
     "Three-part fix: (1) Added PACKAGE_DISCOVERY intent — checked first in detect_user_intent(), "
     "catches all recommendation queries before detect_temple() is ever called. "
     "(2) Raised Pass 5b fuzzy cutoff from 0.70 → 0.82. "
     "(3) Added minimum token length guard of 6 chars in Pass 5b — 'yatra' (5 chars) is "
     "excluded entirely from fuzzy matching."),
    ("BUG 5", "Pass 5c full-text fuzzy match caused false positives",
     "detect_temple() Pass 5c compared the entire user message as a single string against all "
     "alias keywords. This caused 'darta hoon' to match 'Dwarkadhish', producing the response "
     "'Wonderful Dwarkadhish...' for a payment-fear query.",
     "Removed Pass 5c entirely. Token-level matching in 5a and 5b is sufficient and safer."),
    ("BUG 6", "Broken venv launcher — 'cannot find the file specified'",
     "The myenv was created on a different machine at D:\\Desktop\\Sales-ai-backend\\. "
     "The Scripts\\streamlit.exe launcher had this path hardcoded. Running 'streamlit run app.py' "
     "from the current machine's path caused a fatal launcher error.",
     "Created run.ps1 and run.bat that bypass the broken launcher entirely. Both set PYTHONPATH "
     "to myenv\\Lib\\site-packages and invoke 'C:\\Python314\\python.exe -m streamlit run app.py' directly."),
]

for tag, title, problem, solution in bugs:
    story.append(KeepTogether([
        Paragraph(f'{orange(b(tag))} — {b(title)}', H2),
        Paragraph(f'<font color="#DC2626">{b("Problem:")}</font> {problem}', BODY),
        Paragraph(f'<font color="#16A34A">{b("Fix:")}</font> {solution}', BODY),
        Spacer(1, 0.1*cm),
    ]))

# ═══════════════════════════════════════════════════════════════════════════
# 7. CRITICAL AGENT RULES IMPLEMENTED
# ═══════════════════════════════════════════════════════════════════════════
story.append(Paragraph("7. Critical Agent Rules Implemented", H1))
story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY, spaceAfter=8))

rules = [
    "Never assume any destination, temple, package, travel date, budget, number of travellers, or booking details that the user has not explicitly provided.",
    "Never select a temple or package on behalf of the user unless the user explicitly mentions it OR it is clearly identified from previous conversation context.",
    "If required information is missing, ask follow-up questions before answering.",
    "Do not retrieve or recommend packages until the destination is known.",
    "Use only information available in the retrieved knowledge base documents.",
    "If retrieved information is insufficient, ask clarifying questions instead of guessing.",
    "Never hallucinate package details, pricing, availability, discounts, refunds, offers, or policies.",
    "If multiple destinations match the user query, present available options and ask the user to choose.",
]
for i_r, rule in enumerate(rules, 1):
    story.append(Paragraph(f"{i_r}. {rule}", BULLET))

story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(b("PACKAGE_DISCOVERY Intent — Entity Validation Logic:"), H3))
story.append(Paragraph(
    "When intent == PACKAGE_DISCOVERY and destination is not yet known, the bot immediately "
    "returns this clarification message (no LLM call, no RAG retrieval):", BODY))
story.append(Paragraph(
    "\"I'd be happy to help you find the most suitable yatra package.\\n"
    "Please share: Preferred destination / Travel date / Number of travellers / Budget range.\\n"
    "Once I have these details, I'll recommend the best available options.\"", CODE))
story.append(Paragraph(
    "Priority order enforced: Accuracy > Clarification > Retrieval > Recommendation", NOTE))

# ═══════════════════════════════════════════════════════════════════════════
# 8. OBJECTION HANDLING SCRIPTS (C-A-R-E framework)
# ═══════════════════════════════════════════════════════════════════════════
story.append(Paragraph("8. Objection Handling Scripts (C-A-R-E Framework)", H1))
story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY, spaceAfter=8))

story.append(Paragraph(
    "All objection scripts were sourced from the Naman Darshan Inbound Darshan Calling Script & "
    "Closure Strategy PDF. The C-A-R-E framework: Connect (30s) → Acknowledge (60s) → "
    "Resolve (2–3 min) → Execute booking (60s). Target closure rate: 20%.", BODY))

objections_tbl = [
    [b("Intent"), b("Trigger"), b("Key Response Elements")],
    ["TRUST",         "fraud, fake, scared to pay, QR code",
     "1) Validate fear warmly  2) Explain Traininglobe Consultancy Pvt Ltd (like Swiggy=Bundl Technologies)  "
     "3) Post-payment WhatsApp confirmation + coordinator number  4) Offer NEFT/bank transfer  "
     "5) Offer to send company registration on WhatsApp"],
    ["COMPANY_NAME",  "naam alag kyun, payment different name",
     "Zomato analogy (Zomato brand = Zomato Limited legal). Offer WhatsApp verification."],
    ["GST",           "gst, invoice, tax receipt",
     "Religious services are GST-exempt under Indian tax law. Frame as benefit — no hidden tax."],
    ["PRICE",         "price zyada, khud ja sakta hoon, expensive",
     "Per-person anchoring. Ram Mandir story: 4.5hr queue → 45 sec darshan vs 20 min with us. "
     "100% Darshan Guarantee as risk-free closer."],
    ["OFFICIAL",      "officially connected, government, authorized",
     "Transparent: 'We are independent coordination service.' Ola/Uber analogy. Doctor analogy."],
    ["DELAY",         "pehle ghar confirm, sochna hai, family se",
     "Acknowledge → Gentle slot urgency → Offer WhatsApp trust message immediately → "
     "Collect name + date to keep lead warm. Callback within 3 hours."],
    ["GUARANTEE",     "100% guarantee, refund, paisa wapas",
     "Full refund if darshan doesn't happen for any reason. Zero risk."],
    ["HUMAN_AGENT",   "real person, speak to someone, call me",
     "Strong buying signal. Share +91 93119 73199. Collect remaining details while routing."],
    ["PACKAGE_DISCOVERY","best yatra, recommend package, find darshan",
     "Entity validation: ask for destination + date + travellers + budget. Never assume."],
]
t5 = Table(objections_tbl, colWidths=[2.8*cm, 3.5*cm, 9.7*cm])
t5.setStyle(TableStyle([
    ("BACKGROUND",   (0,0), (-1,0), ORANGE),
    ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
    ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
    ("FONTSIZE",     (0,0), (-1,-1), 8),
    ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, colors.HexColor("#FFF7ED")]),
    ("GRID",         (0,0), (-1,-1), 0.4, MID_GREY),
    ("LEFTPADDING",  (0,0), (-1,-1), 6),
    ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ("TOPPADDING",   (0,0), (-1,-1), 5),
    ("BOTTOMPADDING",(0,0), (-1,-1), 5),
    ("VALIGN",       (0,0), (-1,-1), "TOP"),
]))
story += [t5, Spacer(1, 0.4*cm)]

# ═══════════════════════════════════════════════════════════════════════════
# 9. TEST RESULTS
# ═══════════════════════════════════════════════════════════════════════════
story.append(Paragraph("9. Test Results", H1))
story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY, spaceAfter=8))

tests = [
    [b("Test"), b("Query"), b("Expected"), b("Result")],
    ["State 1", "Tirupati ke darshan ke liye baat karna tha",
     "Temple detected, ask date", "PASS"],
    ["State 2", "October mein 15 October",
     "Date stored, ask people count", "PASS"],
    ["State 3", "Hum 4 log hain",
     "People=4, ask elderly", "PASS"],
    ["State 4", "Haan dada dadi elderly hain",
     "elderly=True, ask qualification", "PASS"],
    ["State 5", "Hum Noida se aa rahe hain",
     "Service intro (queue contrast + guarantee)", "PASS"],
    ["TRUST", "Online payment se darta hoon, fraud ho jaata hai",
     "Validate + Traininglobe explanation + NEFT offer", "PASS"],
    ["COMPANY_NAME", "Payment kisi aur naam se kyun?",
     "Zomato analogy + offer WhatsApp verification", "PASS"],
    ["GST", "GST number kyun nahi hai invoice mein?",
     "Religious exemption explained as positive", "PASS"],
    ["PRICE", "Price zyada lagta hai, khud ja sakta hoon",
     "Per-person anchor + Ram Mandir story", "PASS"],
    ["DELAY", "Pehle ghar pe confirm karke batata hoon",
     "Acknowledge + slot urgency + WhatsApp offer", "PASS"],
    ["PACKAGE_DISCOVERY", "can you find best yatra packages for me?",
     "Ask for destination/date/travellers/budget", "PASS"],
    ["PACKAGE_DISCOVERY", "recommend me a darshan package",
     "Same clarification message", "PASS"],
    ["PACKAGE_DISCOVERY", "best pilgrimage trip for family",
     "Same clarification message", "PASS"],
    ["False +ve fix", "can you find best yatra packages for me?",
     "detect_temple() returns None (not Vaishno Devi)", "PASS"],
]

green_rows = [i for i, row in enumerate(tests) if i > 0 and row[-1] == "PASS"]
t6 = Table(tests, colWidths=[3.2*cm, 5.5*cm, 5.3*cm, 2*cm])
style6 = [
    ("BACKGROUND",  (0,0),  (-1,0), DARK_BG),
    ("TEXTCOLOR",   (0,0),  (-1,0), colors.white),
    ("FONTNAME",    (0,0),  (-1,0), "Helvetica-Bold"),
    ("FONTSIZE",    (0,0),  (-1,-1), 8),
    ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, colors.HexColor("#F9FAFB")]),
    ("GRID",        (0,0),  (-1,-1), 0.4, MID_GREY),
    ("LEFTPADDING", (0,0),  (-1,-1), 6),
    ("RIGHTPADDING",(0,0),  (-1,-1), 6),
    ("TOPPADDING",  (0,0),  (-1,-1), 4),
    ("BOTTOMPADDING",(0,0), (-1,-1), 4),
    ("VALIGN",      (0,0),  (-1,-1), "TOP"),
]
for r in green_rows:
    style6.append(("TEXTCOLOR", (3, r), (3, r), GREEN))
    style6.append(("FONTNAME",  (3, r), (3, r), "Helvetica-Bold"))
t6.setStyle(TableStyle(style6))
story += [t6, Spacer(1, 0.4*cm)]

# ═══════════════════════════════════════════════════════════════════════════
# 10. HOW TO RUN
# ═══════════════════════════════════════════════════════════════════════════
story.append(Paragraph("10. How to Run the Application", H1))
story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY, spaceAfter=8))

story.append(Paragraph(b("Project folder:"), H3))
story.append(Paragraph(
    code(r"C:\Users\biswa\OneDrive\Desktop\AI_sales Agent\Sales-ai-backend"), BODY))

story.append(Paragraph(b("Option 1 — PowerShell (recommended):"), H3))
story.append(Paragraph(code(r"cd 'C:\Users\biswa\OneDrive\Desktop\AI_sales Agent\Sales-ai-backend'"
                             r"  then  .\run.ps1"), CODE))

story.append(Paragraph(b("Option 2 — Double-click:"), H3))
story.append(Paragraph(code("run.bat"), BODY))

story.append(Paragraph(b("Option 3 — Direct command:"), H3))
story.append(Paragraph(
    code(r'$env:PYTHONPATH="...\myenv\Lib\site-packages"  ;  '
         r'C:\Python314\python.exe -m streamlit run app.py'), CODE))

story.append(Paragraph(
    "The app opens at http://localhost:8501  |  REST API at http://localhost:5000/chat",
    NOTE))

story.append(Paragraph(b("Why NOT to use the old command:"), H3))
story.append(Paragraph(
    "The myenv was originally created on a machine at D:\\Desktop\\... — its Scripts\\streamlit.exe "
    "has that path hardcoded. Running 'streamlit run app.py' or activating the venv normally "
    "will fail with 'Unable to create process / The system cannot find the file specified'. "
    "run.ps1 and run.bat bypass this by calling Python 3.14 directly.", BODY))

# ═══════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════
story += [
    Spacer(1, 1*cm),
    HRFlowable(width="100%", thickness=1, color=ORANGE),
    Spacer(1, 0.2*cm),
    Paragraph(
        f"Generated on {date.today().strftime('%B %d, %Y')}  |  "
        "Naman Darshan Sales AI Agent  |  Traininglobe Consultancy Pvt Ltd  |  "
        "namandarshan.com  |  +91 93119 73199",
        NOTE),
]

# ── Build ────────────────────────────────────────────────────────────────────
doc.build(story)
print(f"PDF saved: {OUTPUT}")
