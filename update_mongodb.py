"""
update_mongodb.py
-----------------
Updates the MongoDB Atlas database with data from the PDF sales script.
Run once: python update_mongodb.py

Updates:
  1. objections collection — full PDF objection handling scripts
  2. company_info collection — Traininglobe / Naman Darshan identity
"""

from pymongo import MongoClient, ReplaceOne
from datetime import datetime

MONGO_URI = "mongodb+srv://ayush:strongpassword123@sales-ai-backend.gofnxnk.mongodb.net/"
DB_NAME   = "temples_clone"

client = MongoClient(
    MONGO_URI,
    tls=True,
    tlsAllowInvalidCertificates=True,
    serverSelectionTimeoutMS=15_000,
)
db = client[DB_NAME]

# ── 1. Company Info ────────────────────────────────────────────────────────────
print("Updating company_info collection...")
company_info = {
    "brand_name":       "Naman Darshan",
    "legal_name":       "Traininglobe Consultancy Pvt Ltd",
    "website":          "namandarshan.com",
    "phone":            "+91 93119 73199",
    "office":           "Express Trade Tower, Sector 132, Noida",
    "community_size":   "40 lakh+ (40 million+) devotees",
    "rating":           "4.7 stars",
    "darshans_count":   "10,000–14,000+ successful darshans",
    "guarantee":        "100% Darshan Guarantee — full refund if darshan doesn't happen",
    "assisted_wait_time": "20–30 minutes",
    "gst_status":       "GST Exempt — Religious coordination services are exempt under Indian tax law",
    "payment_options":  ["UPI / QR Code", "NEFT / Bank Transfer to Traininglobe Consultancy Pvt Ltd"],
    "key_analogy":      "Brand vs Legal Name — like Zomato (Zomato Limited) or Swiggy (Bundl Technologies)",
    "trust_tagline":    "India's Largest Community for Devotees",
    "updated_at":       datetime.utcnow(),
}
db.company_info.replace_one({}, company_info, upsert=True)
print("  [OK] company_info updated.")

# ── 2. Objections Collection ──────────────────────────────────────────────────
print("Updating objections collection...")

OBJECTIONS = [
    {
        "category":      "payment_trust",
        "intent":        "TRUST",
        "priority":      "critical",
        "main_question": "Online payment se darta hoon / QR code se nahi karunga",
        "main_answer": (
            "Aapki baat bilkul sahi hai. Aaj kal bahut saare fraud ho rahe hain online — "
            "aapka cautious rehna bilkul sahi hai. "
            "Humara payment Traininglobe Consultancy Pvt Ltd ke naam se aata hai — yahi hamara registered company ka naam hai. "
            "Brand naam Naman Darshan hai, legal name alag hai — jaise Swiggy ka legal naam Bundl Technologies hai, "
            "ya PhonePe ka Phonepe Private Limited — yeh bilkul normal hota hai sab companies mein. "
            "Payment ke baad aapko turant WhatsApp pe confirmation aata hai, booking ID aati hai, "
            "aur hamare coordinator ka number milta hai jo aapke temple visit ke din aapke saath rahega."
        ),
        "follow_up_questions": [
            {
                "question": "Can I pay through bank transfer?",
                "answer": (
                    "Haan bilkul — agar QR se comfortable nahi hain toh hum NEFT/bank transfer ka option bhi dete hain "
                    "— Traininglobe Consultancy Pvt Ltd ke account mein — jisse aapke paas bank record rehta hai."
                ),
            },
            {
                "question": "Will I get confirmation after payment?",
                "answer": (
                    "Haan — payment ke turant baad WhatsApp pe confirmation, booking ID, "
                    "aur coordinator ka personal number aata hai."
                ),
            },
            {
                "question": "Can I verify the company?",
                "answer": (
                    "Bilkul — main aapko WhatsApp pe company registration detail, bank account name proof bhej sakta hoon "
                    "taaki aap verify kar sakein pehle."
                ),
            },
        ],
        "key_tip": "Offer NEFT/bank transfer proactively. Offer to send company registration on WhatsApp before booking.",
        "updated_at": datetime.utcnow(),
    },
    {
        "category":      "company_trust",
        "intent":        "COMPANY_NAME",
        "priority":      "critical",
        "main_question": "Company ka naam alag kyun hai? 'Naman Darshan' toh website pe hai, payment kisi aur naam se kyun?",
        "main_answer": (
            "Bahut accha sawaal hai — aur main aapko clearly explain karta/karti hoon. "
            "Naman Darshan hamara brand naam hai — jaise aap 'Zomato' ko jaante hain, "
            "unka registered company naam 'Zomato Limited' hai. "
            "Hamara registered company naam Traininglobe Consultancy Pvt Ltd hai, "
            "aur 'Naman Darshan' hamara trade name / service brand hai jisse hum devotees tak pahunchte hain. "
            "Aap chahein toh main aapko abhi WhatsApp pe hamare company ka registration detail bhej sakta/sakti hoon "
            "— taaki aap verify kar sakein. Kya main bhejoon?"
        ),
        "follow_up_questions": [
            {
                "question": "Is this normal for companies?",
                "answer": (
                    "Haan bilkul — Swiggy ka legal naam Bundl Technologies hai, "
                    "PhonePe ka Phonepe Private Limited hai. "
                    "Har company ka ek registered legal naam hota hai aur ek brand naam — yeh normal practice hai."
                ),
            },
            {
                "question": "Can you share company details?",
                "answer": (
                    "Zaroor — Registered: Traininglobe Consultancy Pvt Ltd | "
                    "Office: Express Trade Tower, Sector 132, Noida | "
                    "Phone: +91 93119 73199 | Website: namandarshan.com"
                ),
            },
        ],
        "key_tip": "Always offer to send company registration details on WhatsApp BEFORE booking — dramatically builds trust.",
        "updated_at": datetime.utcnow(),
    },
    {
        "category":      "gst_invoice",
        "intent":        "GST",
        "priority":      "high",
        "main_question": "GST number kyun nahi hai? Invoice mein GST kyun nahi?",
        "main_answer": (
            "Bahut sahi sawaal hai. Religious coordination aur darshan services "
            "Indian tax law ke under GST se exempt hain — iska matlab hai ki hum aapko koi tax nahi charge kar rahe. "
            "Yeh actually aapke liye benefit hai — jo price aap pay kar rahe hain, "
            "woh mein koi hidden tax nahi joda hua. "
            "Yeh government ka provision hai jo religious services ko affordable rakhne ke liye hai."
        ),
        "follow_up_questions": [
            {
                "question": "So no receipt or invoice?",
                "answer": (
                    "Aapko WhatsApp pe booking confirmation milta hai jisme sab details hain — "
                    "temple, date, number of people, package. Yeh aapka booking proof hai."
                ),
            },
        ],
        "key_tip": "Turn this into a positive — No GST = more value for money. Government provision for religious services.",
        "updated_at": datetime.utcnow(),
    },
    {
        "category":      "price_objection",
        "intent":        "PRICE",
        "priority":      "critical",
        "main_question": "Price zyada lagta hai / main khud ja sakta hoon",
        "main_answer": (
            "Bilkul — aap khud ja sakte hain, aur darshan bilkul free hai agar queue mein khade rehte hain. "
            "Lekin kuch cheezein sochiye: "
            "Pehli baat — aap apne city se temple tak travel karke aaye hain. "
            "Agar temple mein 3-4 ghante queue mein khade rahein — woh energy aur time kaafi costly pad jaati hai. "
            "Doosri baat — hum sirf ticket nahi dete. Hamare coordinator ne us temple ke "
            "har gate, har timing, har shortcut ko jaana hua hai. "
            "Ek ghar tha jo Ram Mandir darshan ke liye Ayodhya gaya — 4.5 ghante queue mein khade rahe, "
            "darshan mein 45 seconds mile. Humari service lene wale ko 20-30 minute mein darshan hua. "
            "Aur teesri baat — agar kisi karan darshan nahi hota, hum 100% refund dete hain."
        ),
        "follow_up_questions": [
            {
                "question": "Can you give a discount?",
                "answer": (
                    "Per person calculate karein toh yeh bahut affordable banta hai — "
                    "ek cup chai se zyada nahi jitna aapne train pe kharch kiya. "
                    "Aur isme 100% Darshan Guarantee included hai."
                ),
            },
            {
                "question": "What exactly do I get for this price?",
                "answer": (
                    "assisted queue skip (20-30 min wait), dedicated on-ground coordinator, "
                    "Sugam Pass arrangement, WhatsApp confirmation, "
                    "coordinator's personal number for darshan day, and 100% Darshan Guarantee."
                ),
            },
        ],
        "key_tip": "Always anchor on PER-PERSON cost, never total. Use the Ram Mandir 4.5 hours story. Mention elderly angle if applicable.",
        "updated_at": datetime.utcnow(),
    },
    {
        "category":      "official_affiliation",
        "intent":        "OFFICIAL",
        "priority":      "high",
        "main_question": "Kya aap officially temple se connected hain?",
        "main_answer": (
            "Main aapke saath bilkul transparent rehna chahta/chahti hoon — "
            "hum temple ke official ticket portal nahi hain. "
            "Hum ek independent coordination aur logistics service hain — "
            "exactly jaise Ola/Uber car wale nahi hain, lekin service seamless dete hain. "
            "Jo official Sugam Pass ya slot booking hoti hai — woh hum aapki taraf se karte hain. "
            "Uske upar humari on-ground team aapko accompany karti hai, guide karti hai, "
            "aur ensure karti hai ki darshan smoothly ho. "
            "Yahi kaam aap khud bhi kar sakte hain — lekin jaise aap doctor ke paas jaate hain "
            "khud diagnose karne ki bajaye, hum woh expert coordination provide karte hain "
            "jo first-time ya busy devotees ko genuine peace of mind deti hai."
        ),
        "follow_up_questions": [
            {
                "question": "So how does booking actually happen?",
                "answer": (
                    "Hum aapki taraf se official Sugam Pass ya priority slot book karte hain, "
                    "uske upar hamare coordinator aapko temple mein personally guide karte hain."
                ),
            },
        ],
        "key_tip": "Be transparent first, then reframe with Ola/Uber analogy and Doctor analogy.",
        "updated_at": datetime.utcnow(),
    },
    {
        "category":      "delay_indecision",
        "intent":        "DELAY",
        "priority":      "critical",
        "main_question": "Pehle confirm karke batata/batati hoon / Sochna hai / Family se poochhna hai",
        "main_answer": (
            "Zaroor — aap apne ghar mein discuss kijiye. "
            "Ek cheez main batana chahta/chahti hoon: "
            "[temple name] ke slots, especially [upcoming festival / weekend], bahut jaldi bhar jaate hain. "
            "Agar [date] ka plan hai toh aaj ka slot kal guarantee nahi hota. "
            "Kya main aapka naam aur travel date note kar loon? "
            "Main ek WhatsApp message bhejta/bhejti hoon jisme haara poora detail ho "
            "— company details, bank account proof, aur customer reviews — "
            "taaki aap ghar pe baith ke sab verify kar sakein. Phir decide karein. Koi pressure nahi."
        ),
        "follow_up_questions": [
            {
                "question": "Can you send details on WhatsApp?",
                "answer": (
                    "Bilkul! Main abhi bhejta/bhejti hoon — "
                    "company name (Traininglobe Consultancy Pvt Ltd), office address (Noida), "
                    "phone number, rating, guarantee — sab included rahega."
                ),
            },
            {
                "question": "How long will slots stay available?",
                "answer": (
                    "Weekends aur festival dates pe slots bahut jaldi bhar jaate hain. "
                    "Aaj confirm karein toh guarantee rahega — kal availability uncertain hoti hai."
                ),
            },
        ],
        "key_tip": "Send WhatsApp trust message IMMEDIATELY. Callback within 3 hours for leads who said 'will confirm'. Never wait till next day.",
        "updated_at": datetime.utcnow(),
    },
    {
        "category":      "closing",
        "intent":        "CLOSE",
        "priority":      "high",
        "main_question": "How do I confirm my booking?",
        "main_answer": (
            "Bahut accha! Main aapki booking abhi confirm karta/karti hoon. "
            "Aapka naam, travel date, aur number of people le leta/leti hoon. "
            "Payment confirmation ke saath WhatsApp pe sab detail aa jaayegi — "
            "aur hamare coordinator ka number bhi, jo aapke darshan ke din personally available rahenge."
        ),
        "follow_up_questions": [
            {
                "question": "What happens after I pay?",
                "answer": (
                    "Turant WhatsApp pe booking confirmation + Booking ID + coordinator ka personal number. "
                    "Coordinator darshan ke din temple pe aapka wait karega."
                ),
            },
            {
                "question": "How will I receive my booking details?",
                "answer": "Booking details WhatsApp pe share ki jaati hain — including coordinator contact.",
            },
        ],
        "key_tip": "Progressive lead capture: Name first → Phone after rapport. Then payment link.",
        "updated_at": datetime.utcnow(),
    },
    {
        "category":      "timings",
        "intent":        "TIMINGS",
        "priority":      "medium",
        "main_question": "What are the darshan timings?",
        "main_answer": (
            "Darshan timings vary by temple, date, and festival schedule. "
            "Please share the temple name for exact timings. "
            "Hamare coordinator aapko best darshan time bhi guide karenge."
        ),
        "follow_up_questions": [
            {
                "question": "What is the best time to visit?",
                "answer": "Early morning darshan tends to be less crowded — coordinator will guide you on the best timing.",
            },
        ],
        "key_tip": "Pivot to assisted benefit: assisted wait time (20-30 min) vs general queue (2-8 hours).",
        "updated_at": datetime.utcnow(),
    },
    {
        "category":      "authority",
        "intent":        "OFFICIAL",
        "priority":      "high",
        "main_question": "Are you officially connected to the temple?",
        "main_answer": (
            "We are an independent darshan coordination and support service, not the official temple authority. "
            "We arrange official Sugam Pass/slots on your behalf and our on-ground team guides you through the process."
        ),
        "follow_up_questions": [
            {
                "question": "Then how does booking happen?",
                "answer": "We arrange official darshan slots/Sugam Pass on your behalf. Our team then accompanies you at the temple.",
            },
        ],
        "key_tip": "Transparent first, then Ola/Uber analogy. Doctor analogy for expertise.",
        "updated_at": datetime.utcnow(),
    },
    {
        "category":      "benefits",
        "intent":        "BENEFITS",
        "priority":      "high",
        "main_question": "What benefits do I get with assisted darshan?",
        "main_answer": (
            "assisted darshan mein aapko milta hai: "
            "Queue skip (20-30 min wait vs 2-8 hours general), "
            "dedicated on-ground coordinator who knows every gate/timing/shortcut, "
            "Sugam Pass arrangement, "
            "instant WhatsApp confirmation + Booking ID, "
            "coordinator's personal phone for darshan day, "
            "language support, "
            "and 100% Darshan Guarantee — full refund if darshan doesn't happen."
        ),
        "follow_up_questions": [],
        "key_tip": "Lead with queue time contrast. Mention elderly support if applicable.",
        "updated_at": datetime.utcnow(),
    },
    {
        "category":      "guarantee",
        "intent":        "GUARANTEE",
        "priority":      "high",
        "main_question": "What is the 100% Darshan Guarantee?",
        "main_answer": (
            "Hamaari 100% Darshan Guarantee hai — agar kisi bhi karan darshan nahi hota "
            "(temple closure, natural calamity, any unforeseen circumstance), "
            "hum POORA refund dete hain. "
            "Yeh guarantee seedhe queue mein khade rehne se nahi milti. "
            "Aap zero risk pe spiritual peace of mind le rahe hain."
        ),
        "follow_up_questions": [
            {
                "question": "What situations are covered?",
                "answer": "Temple closure, natural calamity, any unforeseen circumstance that prevents darshan.",
            },
        ],
        "key_tip": "Frame as risk-free — zero risk spiritual peace of mind.",
        "updated_at": datetime.utcnow(),
    },
    {
        "category":      "payment_method",
        "intent":        "PAYMENT_METHOD",
        "priority":      "high",
        "main_question": "How can I pay? What payment methods are available?",
        "main_answer": (
            "Do payment options available hain: "
            "1. UPI / QR Code — Traininglobe Consultancy Pvt Ltd ke registered account mein. "
            "2. NEFT / Bank Transfer — agar QR se comfortable nahi hain, "
            "bank transfer se bank record bhi rehta hai aapke paas. "
            "Jo bhi comfortable lage — dono available hain."
        ),
        "follow_up_questions": [
            {
                "question": "What is the account name?",
                "answer": "Account is in the name of Traininglobe Consultancy Pvt Ltd — registered company of Naman Darshan.",
            },
        ],
        "key_tip": "Offer bank transfer proactively — removes QR anxiety entirely.",
        "updated_at": datetime.utcnow(),
    },
]

# Replace entire objections collection with fresh data
db.objections.delete_many({})
result = db.objections.insert_many(OBJECTIONS)
print(f"  [OK] Inserted {len(result.inserted_ids)} objection documents.")

# ── 3. Update Yatra_packages with company info field ────────────────────────────
print("Updating Yatra_packages with company info...")
db.Yatra_packages.update_many(
    {},
    {
        "$set": {
            "service_provider":     "Traininglobe Consultancy Pvt Ltd",
            "brand":                "Naman Darshan",
            "payment_to":           "Traininglobe Consultancy Pvt Ltd",
            "assisted_wait_time":   "20–30 minutes",
            "guarantee":            "100% Darshan Guarantee",
            "updated_at":           datetime.utcnow(),
        },
        "$unset": {
            "vip_wait_time": "",
            "vip_benefits": "",
            "vip_time_estimate": "",
            "vip_fees": "",
        }
    },
)
print("  [OK] Yatra_packages updated.")

# ── 4. Update Agent Rules ──────────────────────────────────────────────────────
print("Updating agent_rules collection...")
rule_doc = db.agent_rules.find_one()
new_critical_rules = [
    "primary objective is to help devotees discover, understand, and book darshan, puja, yatra, prasadam, astrology, and other spiritual services while providing an excellent customer experience.",
    "Understand the user's intent.",
    "Extract all available information from the user's message.",
    "Maintain conversation context throughout the session.",
    "Never ask for information that has already been provided.",
    "Ask only the most relevant next question when required.",
    "Use retrieved knowledge from the RAG system whenever factual information is needed.",
    "Recommend suitable packages and services based on the customer's requirements.",
    "Guide the user naturally toward inquiry, booking, or lead generation.",
    "Always extract and remember any information mentioned by the user (Customer Name, Service Type, Destination, Travel Date, Group Size, Adults, Elders, Children, Wheelchair, Duration, Departure City, Budget, Accommodation, Special Requirements).",
    "Never ask again for information that has already been provided.",
    "Strictly prohibited: Asking the same question twice, repeating previously collected information, asking for details already present in memory, restarting the booking process.",
    "Identify user intent. Extract available information. Determine missing information. Ask ONLY ONE relevant follow-up question. Never ask multiple questions in a single message.",
    "When recommending yatra packages, prioritize information collection in the following order: 1. Destination, 2. Travel Date, 3. Group Size, 4. Elders / Children, 5. Departure City, 6. Duration. Only ask for missing fields.",
    "If sufficient information exists: Use retrieved package data, recommend the most relevant packages, explain why each package is suitable, mention inclusions, duration, pricing, and benefits if available. Never invent details.",
    "Use retrieved knowledge for package details, pricing, temple information, policies, refund, trust, company info, and service descriptions. Do not fabricate facts.",
    "If information is unavailable in retrieved knowledge, say: 'I do not have verified information regarding that at the moment. Let me connect you with our team for accurate assistance.'",
    "Assume conversation memory is available. Before responding, check existing customer info, update using latest message, determine missing info, continue from current stage. Never reset or forget.",
    "Response style must be Professional, Respectful, Devotional, Helpful, Sales-oriented but not pushy, Concise and conversational. Avoid robotic or form-like questioning. One question at a time.",
    "Once the customer shows interest in a package, collect: Name, Phone Number, Preferred Contact Method. Then guide them toward booking assistance.",
    "Never repeat questions.",
    "Never repeat answers.",
    "Never ask for information already provided.",
    "Always extract information from customer messages.",
    "Ask only the most relevant next question.",
    "Use RAG for factual information.",
    "Do not hallucinate package details.",
    "Maintain context across the entire conversation.",
    "Focus on helping the customer move toward a successful booking.",
    "Sound like an experienced pilgrimage travel consultant, not a chatbot.",
    "Do not give unnecessary information.",
    "Give concise information according to customers questions.",
    "Never assume the customer's name. Use it ONLY if explicitly provided or confirmed by the customer in the current conversation.",
    "Ignore names or booking details from previous conversations, session memory, or database records. Use only information explicitly provided in the current conversation.",
    "When a customer requests a booking, never immediately confirm it. Identify the service, check required fields, determine missing info, ask only for missing mandatory info, and proceed only after all required info is collected.",
    "Never claim booking confirmed, booking successful, representative will call, availability verified, payment completed, or booking created unless these actions have actually been performed by the system.",
    "Replace all promises of 'our representative will call you' with: 'Once the required details are provided, I can help you proceed with the booking process.'"
]

if rule_doc:
    db.agent_rules.update_one(
        {"_id": rule_doc["_id"]},
        {"$set": {"critical_rules": new_critical_rules, "updated_at": datetime.utcnow()}}
    )
    print("  [OK] agent_rules updated.")
else:
    new_doc = {
        "version": "1.0",
        "critical_rules": new_critical_rules,
        "follow_up_triggers": [
            "best yatra package",
            "recommend a package",
            "suggest darshan",
            "best pilgrimage trip",
            "find package for me",
            "plan yatra"
        ],
        "intent_entity_validation": {
            "PACKAGE_DISCOVERY": {
                "action_if_missing": "return_clarification_message",
                "required_entity": "destination",
                "clarification_message": "I'd be happy to help you find the most suitable yatra package.\n\nPlease share:\n- Preferred destination\n- Travel date\n- Number of travellers\n\nOnce I have these details, I'll recommend the best available options."
            }
        },
        "retrieval_rules": {
            "metadata_based": True,
            "priority_order": ["Accuracy", "Clarification", "Retrieval", "Recommendation"],
            "query_temples_clone_only_after": "destination_known"
        },
        "updated_at": datetime.utcnow()
    }
    db.agent_rules.insert_one(new_doc)
    print("  [OK] agent_rules created.")

print("\n[DONE] All MongoDB updates completed successfully!")
client.close()
