# sales_logic.py
# Detects user intent from their message.
# 8 major objection groups covered + high-value additional scenarios.


def detect_user_intent(query):

    query = query.lower().strip()

    # ---------------------------------------------------
    # CHECK PAYMENT STATUS — user asking about their payment
    # ---------------------------------------------------
    if any(w in query for w in [
        "check payment", "payment status", "payment done", "payment successful",
        "payment complete", "payment completed", "completed the payment", "completed payment",
        "payment received", "did my payment", "payment confirm",
        "payment ho gaya", "payment hua", "payment check", "payment pending",
        "payment failed", "payment ka status", "booking status", "check my booking",
        "booking confirm hua", "booking ho gaya", "mera payment", "payment verify",
        "is payment done", "has payment", "payment through", "went through",
        "payment link status", "payment link check", "paid already", "i have paid",
        "already paid", "payment kar diya", "payment kar chuka", "done the payment",
        "have completed", "has completed", "i paid", "i have paid"
    ]):
        return "CHECK_PAYMENT"

    # ---------------------------------------------------
    # PAYMENT CONFIRM — user agrees to proceed with payment
    # ---------------------------------------------------
    # Robust checks for payment link requests with word gaps
    contains_pay = any(w in query for w in ["payment", "pay", "link", "online"])
    contains_action = any(w in query for w in ["proceed", "confirm", "finalize", "complete", "yes", "do", "make", "now", "send", "share", "give", "get", "need", "want", "please", "provide", "karo", "bhejo", "finalise"])
    contains_info = any(w in query for w in ["when", "how", "where", "timing", "method", "option", "tax", "gst", "safe", "secure", "timing", "time", "date"])

    if contains_pay and contains_action and not contains_info:
        return "PAYMENT_CONFIRM"

    if any(w in query for w in [
        "yes pay", "proceed with payment", "generate payment link", "pay now",
        "ready to pay", "make payment", "do payment", "complete payment",
        "want to pay", "i want to pay", "payment karna hai", "payment kar do",
        "send payment link", "share payment link", "payment link bhejo",
        "payment link send", "payment link chahiye", "payment karo",
        "online payment karna", "pay online", "pay the amount", "pay amount",
        "yes proceed payment", "haan pay", "agree to pay", "ok to pay",
        "proceed to pay", "go ahead with payment", "confirm payment",
        "yes i'll pay", "yes i will pay", "i will pay", "let's pay",
        "send me the payment link", "send me payment link", "send the payment link",
        "please send the payment link", "please send me the payment link",
        "give me the payment link", "give me payment link", "give payment link",
        "share the payment link", "share me the payment link", "share me payment link",
        "send link", "send the link", "send me the link", "send me link",
        "payment link send", "payment link share"
    ]):
        return "PAYMENT_CONFIRM"

    # ---------------------------------------------------
    # TEMPLE LIST / PACKAGE COUNT — customer asking which temples or packages are covered, available, or their count
    # ---------------------------------------------------

    if any(w in query for w in [
        "which temples", "what temples", "which temple do you", "temples do you",
        "temples you cover", "temples you serve", "temples available",
        "how many temples", "list of temples", "temples you offer",
        "which mandir", "what mandir", "which places", "all temples",
        "temples covered", "supported temples", "temples you have",
        "darshan services for which", "assisted darshan for which", "vip darshan for which",
        "for which temples", "which all temples",
        "how many yatra", "how many packages", "how many abodes",
        "packages available", "packages you cover", "packages you offer",
        "number of yatra", "number of packages", "number of temples",
        "list of packages", "list of yatra", "which packages", "what packages"
    ]):
        return "TEMPLE_LIST"

    # ---------------------------------------------------
    # PUJA LIST — customer asking about listed pujas or available pujas
    # ---------------------------------------------------
    if any(w in query for w in [
        "what pujas", "which pujas", "pujas list", "list of pujas",
        "pujas you offer", "pujas available", "available pujas",
        "listed pujas", "pujas on website", "pujas on the website",
        "pujas in naman darshan", "pujas of naman darshan",
        "what poojas", "which poojas", "poojas list", "list of poojas",
        "poojas you offer", "poojas available", "available poojas"
    ]):
        return "PUJA_LIST"


    # ---------------------------------------------------
    # PACKAGE_DISCOVERY — user asking for a recommendation
    # without specifying a destination.
    # Rule: never assume a destination that was not provided.
    # ---------------------------------------------------

    _discovery_triggers = [
        "best yatra", "best package", "best darshan", "best pilgrimage",
        "best trip", "yatra package", "pilgrimage package",
        "recommend package", "suggest package", "suggest darshan",
        "recommend darshan", "suggest trip", "suggest yatra",
        "find package", "find best", "which package", "what package",
        "suitable package", "good package", "any package",
        "packages for me", "package for me", "yatra for me",
        "darshan package", "which yatra", "plan yatra",
        "plan pilgrimage", "plan darshan", "plan trip",
        "suggest me", "suggest some", "suggest a", "recommend me", "recommend some", "recommend a",
    ]
    
    _exclude_words = ["timing", "timings", "price", "cost", "charges", "fee", "cancel", "refund", "official", "safety", "safe", "wheelchair", "elderly", "document"]

    _has_discovery_keywords = (
        any(w in query for w in _discovery_triggers)
        and not any(exc in query for exc in _exclude_words)
    )
    
    # Generic word combination check
    _action_words = ["suggest", "recommend", "suggestion", "recommendation", "option", "choice"]
    _target_words = ["darshan", "yatra", "package", "trip", "pilgrimage", "temple", "mandir", "place", "destination", "abode"]
    
    _combined_match = (
        any(act in query for act in _action_words)
        and any(tgt in query for tgt in _target_words)
        and not any(exc in query for exc in _exclude_words)
    )
    
    if _has_discovery_keywords or _combined_match:
        return "PACKAGE_DISCOVERY"

    # ---------------------------------------------------
    # POSITIVE / READY TO BOOK
    # ---------------------------------------------------

    if any(w in query for w in [
        "book karo", "book kar do", "confirm kar do", "confirm karo",
        "booking confirm", "reserve kar", "yes please", "haan kar do",
        "theek hai book", "abhi book", "book now",
        "proceed with", "proceed booking", "please proceed", "want to proceed",
        "go ahead", "let's book", "lets book", "ready to book",
        "want to book", "i want to book", "book it", "book the slot",
        "confirm my booking", "confirm booking", "start my booking",
    ]):
        return "CLOSE"

    # ---------------------------------------------------
    # HUMAN AGENT REQUEST — strong buying signal
    # (check near top — this is NOT an objection)
    # ---------------------------------------------------

    if any(w in query for w in [
        "real person", "talk to someone", "speak to someone",
        "human agent", "talk to a person", "speak to a person",
        "connect me", "talk to your team", "speak to your team",
        "talk to representative", "speak to representative",
        "call me", "someone call", "agent call", "want to speak",
        "can i speak", "can i talk", "want to talk",
        "real agent", "actual person", "live person",
    ]):
        return "HUMAN_AGENT"

    # ---------------------------------------------------
    # CANCELLATION / RESCHEDULING PLAN
    # (check BEFORE payment to catch "what if plan cancelled")
    # ---------------------------------------------------

    if any(w in query for w in [
        "plan cancelled", "plan gets cancelled", "plan cancel",
        "train cancelled", "train cancel", "flight cancelled", "trip cancelled",
        "miss my slot", "missed slot", "miss the slot",
        "can i reschedule", "reschedule", "postpone booking",
        "cannot travel", "can't travel", "unable to travel",
        "change my date", "change date", "shift my booking",
        "what if i can't", "what if we can't", "what if plan",
        "if train", "if my train", "if flight",
    ]):
        return "CANCELLATION_PLAN"

    # ---------------------------------------------------
    # PAYMENT TIMING — when is payment due?
    # ---------------------------------------------------

    if any(w in query for w in [
        "before darshan", "after darshan", "advance payment", "pay before",
        "pay after", "when to pay", "payment before", "payment after",
        "pehle pay", "baad mein pay", "pehle dena", "kitne din pehle",
        "do i need to pay", "payment kab", "kab pay",
        "pay in advance", "pay upfront", "partial payment", "pay half",
        "pay some now", "deposit", "pay partially", "partially pay",
        "part payment", "half payment",
    ]):
        return "PAYMENT_TIMING"

    # ---------------------------------------------------
    # PAYMENT METHOD — how is payment done?
    # ---------------------------------------------------

    if any(w in query for w in [
        "payment online", "online payment", "payment offline", "offline payment",
        "payment mode", "how to pay", "payment method", "mode of payment",
        "will be done online", "done online", "payment process", "pay online",
        "payment kaise", "payment karna", "how do i pay", "how can i pay",
        "payment option", "payment type", "upi", "net banking", "card payment",
        "payment confirmation", "payment receipt", "will i get invoice",
        "payment proof", "payment secure",
    ]):
        return "PAYMENT_METHOD"

    # ---------------------------------------------------
    # AVAILABILITY — slots, same-day, urgent booking
    # ---------------------------------------------------

    if any(w in query for w in [
        "slot available", "slots available", "availability", "available slot",
        "is slot", "any slot", "slot milega", "slot hai",
        "same day", "same-day", "urgent booking", "last minute",
        "can you guarantee", "guarantee booking", "guarantee slot",
        "what if slots are full", "if full", "slots full",
        "book for tomorrow", "book for today", "immediate booking",
    ]):
        return "AVAILABILITY"

    # ---------------------------------------------------
    # COORDINATOR — on-ground support questions
    # ---------------------------------------------------

    if any(w in query for w in [
        "coordinator", "will someone meet", "someone come", "someone be there",
        "will someone be", "will you be", "guide us", "who will guide",
        "how to identify", "identify coordinator", "how will i know",
        "coordinator number", "coordinator contact", "coordinator call",
        "what if coordinator", "if coordinator doesn't", "coordinator not answering",
        "will coordinator stay", "coordinator with us", "stay with us",
        "guide throughout", "who will guide us", "on ground",
        "will someone actually", "actually meet", "someone actually",
        "meet us", "be there with", "come with us",
    ]):
        return "COORDINATOR"

    # ---------------------------------------------------
    # LANGUAGE SUPPORT
    # ---------------------------------------------------

    if any(w in query for w in [
        "in hindi", "in english", "assist in hindi", "assist in english",
        "hindi mein", "english mein", "regional language", "my language",
        "speak hindi", "speak english", "language support",
        "can you assist in hindi", "can you assist in english",
        "gujarati", "marathi", "tamil", "telugu", "bengali", "kannada",
        "kya aap hindi", "hindi bolta", "hindi jaanta",
        "language available", "which language",
    ]):
        return "LANGUAGE_SUPPORT"

    # ---------------------------------------------------
    # ELDERLY / ACCESSIBILITY SUPPORT
    # ---------------------------------------------------

    if any(w in query for w in [
        "wheelchair", "physically challenged", "disabled",
        "my parents are old", "parents old", "elderly parents",
        "senior citizen", "senior citizens", "old person", "aged person",
        "lot of walking", "too much walking", "how much walking",
        "can they manage", "will they manage", "manage for elderly",
        "help senior", "assist senior", "support elderly",
        "physically able", "mobility", "walking distance",
        "can old people", "old people manage",
    ]):
        return "ELDERLY_SUPPORT"

    # ---------------------------------------------------
    # SAFETY QUESTIONS
    # ---------------------------------------------------

    if any(w in query for w in [
        "safe for women", "is it safe", "women safety", "female safe",
        "solo traveller", "solo traveler", "travelling alone", "traveling alone",
        "akele ja sakte", "single person", "alone",
        "what if i reach late", "if i reach late", "late arrival",
        "heavy crowd", "too much crowd", "crowd management",
        "safe for solo", "is it secure", "security",
    ]):
        return "SAFETY"

    # ---------------------------------------------------
    # TRAVEL PLANNING — documents, dress code, what to carry, duration
    # ---------------------------------------------------

    if any(w in query for w in [
        "what documents", "documents required", "id proof", "aadhar",
        "what to carry", "what to bring", "what should i carry",
        "dress code", "what to wear", "what should i wear", "clothing", "attire",
        "how much time", "darshan duration", "how long does darshan",
        "how long will it take", "time for darshan",
        "what to eat", "food allowed", "prasad",
        "mobile allowed", "phone allowed", "camera allowed",
        "what to know", "things to know", "tips for visiting",
        "best time to visit", "when to visit", "which month",
        "what do i need", "what will i need", "what items",
    ]):
        return "TRAVEL_PLANNING"



    # ---------------------------------------------------
    # SEND DETAILS — user agrees to receive WhatsApp verification details
    # (must come BEFORE TRUST so "yes please send" doesn't get swallowed by TRUST)
    # ---------------------------------------------------


    if any(w in query for w in [
        "yes please send", "please send", "send it", "send details",
        "send verification", "send on whatsapp", "share on whatsapp",
        "yes send", "send the details", "send company details",
        "send company registration", "send proof", "share details",
        "send to whatsapp", "send me the details", "send registration",
    ]):
        return "SEND_DETAILS"

    # ---------------------------------------------------
    # TRUST / PAYMENT SAFETY (fear/fraud/concern words)
    # ---------------------------------------------------

    if any(w in query for w in [
        "safe", "fraud", "fake", "trust", "qr", "genuine",
        "real", "registered", "bharosa", "sach mein", "sach hai",
        "paise safe", "paisa safe", "money safe", "scam", "dhoka",
        "verified", "authentic", "proof", "traininglobe", "company naam",
        "company ka naam", "naam alag", "alag naam", "different name",
        "scared", "afraid", "worried", "concern", "nervous", "hesitant",
        "not comfortable", "uncomfortable", "suspicious", "doubt",
        "are you registered", "registration", "company registered",
        "customer reviews", "reviews", "testimonials", "feedback",
        "how many people", "how many customers", "have office",
        "your office", "visit office", "office address",
        "website", "do you have website", "namandarshan",
        "what if nobody responds", "nobody responds", "no response",
    ]):
        return "TRUST"

    # ---------------------------------------------------
    # COMPANY NAME MISMATCH
    # ---------------------------------------------------

    if any(w in query for w in [
        "naam alag kyun", "alag company", "naman darshan aur", "brand naam",
        "trade name", "legal name", "company name different", "naam different",
        "why different name", "different company name",
    ]):
        return "COMPANY_NAME"

    # ---------------------------------------------------
    # GST / INVOICE
    # ---------------------------------------------------

    if any(w in query for w in [
        "gst", "invoice", "tax", "receipt", "bill",
        "gst kyun nahi", "no gst", "gst number",
        "will i get invoice", "get receipt", "payment receipt",
    ]):
        return "GST"

    # ---------------------------------------------------
    # PRICE / COST OBJECTION
    # ---------------------------------------------------

    if any(w in query for w in [
        "price", "cost", "kitna", "charges", "fees", "expensive", "mahanga",
        "zyada hai", "bahut zyada", "costly", "kitne paise", "kitna paisa",
        "total kitna", "total cost", "khud ja sakte", "khud jaunga",
        "khud jaenge", "free mein", "without", "bina aapke", "akele",
        "discount", "offer", "any discount", "cheaper", "cheap option",
        "family package", "group discount", "per person", "per head",
        "what is included", "what's included", "included in price",
        "what do i get", "what will i get",
    ]):
        return "PRICE"

    # ---------------------------------------------------
    # TEMPLE AFFILIATION / OFFICIAL
    # ---------------------------------------------------

    if any(w in query for w in [
        "official", "temple se connected", "government", "temple ka",
        "mandir se", "authorized", "permit", "allowed", "permission",
        "officially", "affiliation", "temple affiliated",
        "government approved", "temple staff", "book directly",
        "directly from temple", "official website", "temple website",
        "why book through you", "why not book directly",
    ]):
        return "OFFICIAL"

    # BENEFITS / WHY ASSISTED / SERVICE VALUE
    # ---------------------------------------------------

    if any(w in query for w in [
        "benefit", "benefits", "fayda", "advantages", "why vip", "why assisted",
        "vip darshan", "assisted darshan", "special", "priority", "why should",
        "kyu", "difference", "kya milega", "kya hoga", "kya faida",
        "kya milta hai", "queue", "line", "bheed",
        "kitna time", "kitni der", "how long", "wait time",
        "what exactly do you do", "what do you do", "what is your service",
        "what makes you different", "why use your service",
        "can't i just go", "cant i go myself", "go on my own",
        "what benefit", "what advantage",
    ]):
        return "BENEFITS"

    # ---------------------------------------------------
    # BOOKING PROCESS (explicit question about how booking works)
    # ---------------------------------------------------

    if any(w in query for w in [
        "booking process", "process kya", "kaise book", "kaise hota hai",
        "steps kya hain", "how to book", "booking kaise hoti",
        "kya karna hoga", "process batao", "process bata", "kya process hai",
        "procedure", "steps"
    ]):
        return "BOOKING_PROCESS"

    # ---------------------------------------------------
    # TIMINGS
    # ---------------------------------------------------

    if any(w in query for w in [
        "timing", "timings", "darshan time", "opening", "closing", "schedule",
        "kitne baje", "kab se kab tak", "mandir kab khulta",
        "visit time",
    ]):
        return "TIMINGS"

    # ---------------------------------------------------
    # CANCELLATION / REFUND (darshan didn't happen, guarantee)
    # ---------------------------------------------------

    if any(w in query for w in [
        "cancel", "cancellation", "cancel karna", "booking cancel",
        "refund", "paisa wapas", "money back", "guarantee",
        "agar nahi hua", "darshan nahi hua", "darshan not happen",
        "if darshan doesn't", "what if darshan",
    ]):
        return "GUARANTEE"

    # ---------------------------------------------------
    # DELAY / FAMILY DECISION OBJECTIONS
    # ---------------------------------------------------

    if any(w in query for w in [
        "later", "soch", "discuss", "family se", "baad mein", "kal",
        "sochke batata", "sochke batati", "ghar pe puchna",
        "wife se puchna", "husband se", "parents se", "confirm karke",
        "thoda time", "time chahiye", "abhi nahi", "not now",
        "baad mein batata", "baad bolunga", "phir batata",
        "ask my family", "ask my spouse", "decide later",
        "confirm tomorrow", "comparing options", "still comparing",
        "let me think", "need to think",
    ]):
        return "DELAY"

    # ---------------------------------------------------
    # BOOKING INTENT (General interest)
    # ---------------------------------------------------

    if any(w in query for w in [
        "book", "booking", "confirm", "reserve", "slot book",
        "kar do", "karwa do", "slot chahiye", "darshan chahiye",
        "visit karna hai", "jana hai", "plan kar raha"
    ]):
        return "BOOKING"

    # ---------------------------------------------------
    # GREETING — pure greetings
    # ---------------------------------------------------
    cleaned_query = "".join(c for c in query if c.isalnum() or c.isspace()).strip()
    if cleaned_query in [
        "hello", "hi", "hey", "namaste", "good morning", "good afternoon", "good evening",
        "hii", "helo", "namaskar", "hey there", "hi there", "hello there", "namaste ji",
        "namaskar ji", "goodmorning", "goodevening", "goodafternoon"
    ]:
        return "GREETING"

    return "GENERAL"