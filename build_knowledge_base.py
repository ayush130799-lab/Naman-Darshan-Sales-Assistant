# build_knowledge_base.py
# Creates a rich, structured knowledge base and rebuilds the FAISS vectorstore.
#
# Run this once (or whenever you update temple knowledge):
#   python build_knowledge_base.py
#
# This adds comprehensive temple knowledge:
#   - Seasonal visiting info (which months are best/worst)
#   - Regional groupings (by state)
#   - Visitor tips (crowd, clothing, documents, duration)
#   - Accessibility info (elderly, wheelchair, trekking required)
#   - Jyotirlinga and Char Dham circuit info
#   - Naman Darshan service info and FAQs
#
# The FAISS vectorstore is then used by retriever.py for every QA query.

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from data_loader import load_data

print("Loading existing MongoDB data...")
mongo_texts = load_data()
print(f"Loaded {len(mongo_texts)} docs from MongoDB.")

# ============================================================
# STRUCTURED TEMPLE KNOWLEDGE BASE
# This is the "global data" that makes recommendations smart.
# Add/edit entries here to update the bot's knowledge.
# ============================================================

TEMPLE_KNOWLEDGE = [

    # --------------------------------------------------------
    # SEASONAL GUIDE — Month by Month
    # --------------------------------------------------------
    """
    SEASONAL TEMPLE GUIDE — INDIA

    JANUARY (Winter, Cool): Best month for South India. Tirupati Balaji, Meenakshi Amman (Madurai),
    Padmanabhaswamy (Thiruvananthapuram), Guruvayur, Kashi Vishwanath (Varanasi), Ayodhya Ram Mandir.
    Avoid: Kedarnath and Yamunotri (closed in winter).

    FEBRUARY (Cool, Pleasant): Excellent for all plains and South India temples.
    Kashi Vishwanath, Ayodhya Ram Mandir, Tirupati Balaji, Shirdi, Somnath, Dwarka, Vaishno Devi.
    Good for Kedarnath trek preparation (temple opens in May).

    MARCH (Spring, Comfortable): Good for North India before summer heat.
    Ayodhya Ram Mandir, Kashi Vishwanath, Vrindavan, Mathura, Mahakaleshwar (Ujjain).
    Holi season — special celebrations at Vrindavan and Mathura.

    APRIL (Pre-summer, Good for hills): Kedarnath and Badrinath open (usually late April or May).
    Good for Vaishno Devi, Kedarnath trek start. Avoid South India (too hot).

    MAY (Summer, Hill temples excellent): Kedarnath, Badrinath, Gangotri, Yamunotri — all open.
    Char Dham Yatra season starts. Best time for Kedarnath (pre-monsoon).
    Vaishno Devi excellent. Avoid Tirupati and plains (very hot).

    JUNE (Early Monsoon, Selective): Kedarnath is open but monsoon begins.
    Best options: Kashi Vishwanath (Varanasi), Shirdi Sai Baba, Mahakaleshwar, Vaishno Devi.
    Tirupati accessible. Avoid Kedarnath after mid-June (landslide risk).
    Recommended for June: Kashi Vishwanath, Mahakaleshwar (Ujjain), Shirdi, Vaishno Devi.

    JULY (Monsoon): Most hill temples risky. Puri Jagannath Rath Yatra happens in July (huge festival).
    Best for: Shirdi Sai Baba, Kashi Vishwanath, Mahakaleshwar, Jagannath Puri (Rath Yatra).
    Avoid: Kedarnath, Badrinath, Vaishno Devi (heavy rain, landslide risk).
    Best temples in July: Shirdi Sai Baba, Kashi Vishwanath, Jagannath Puri Rath Yatra, Mahakaleshwar.

    AUGUST (Monsoon): Same as July. Janmashtami celebrations at Vrindavan and Mathura (major festival).
    Shirdi, Kashi Vishwanath, Siddhivinayak Mumbai (Ganesh Chaturthi coming up) are safe.
    Best temples in August: Vrindavan (Janmashtami), Shirdi, Kashi Vishwanath, Siddhivinayak.

    SEPTEMBER (Post-monsoon start): Kedarnath and Badrinath remain open but weather improves by end of September.
    Tirupati becomes pleasant. Navratri begins.
    Best: Vaishno Devi (Navratri rush but manageable), Tirupati, Shirdi, Kashi Vishwanath.

    OCTOBER (Post-monsoon, Excellent): One of the best months. Navratri, Dussehra season.
    All temples accessible. Kedarnath and Badrinath start closing in October-November.
    Highly recommended for: Tirupati, Vaishno Devi, Kashi Vishwanath, Ram Mandir Ayodhya, Shirdi.

    NOVEMBER (Winter begins): Last chance for Kedarnath and Badrinath (they close by November 15-17).
    Excellent for all other temples. Diwali season — Ayodhya illuminated.
    Highly recommended for: Ayodhya Ram Mandir (Diwali), Tirupati, Shirdi, Somnath, Dwarka.

    DECEMBER (Winter, Excellent for South India): All plains and South India temples excellent.
    North India is cold. Best for: Tirupati, Meenakshi Madurai, Golden Temple Amritsar (lohri coming up),
    Shirdi, Kashi Vishwanath (Maha Shivaratri planning), Somnath.
    Kedarnath and Badrinath closed.
    """,

    # --------------------------------------------------------
    # REGIONAL GUIDE — Temples by State
    # --------------------------------------------------------
    """
    TEMPLES BY STATE / REGION IN INDIA — Naman Darshan assisted Darshan Coverage

    UTTAR PRADESH:
    - Kashi Vishwanath (Varanasi / Kashi) — Most sacred Shiva temple, one of 12 Jyotirlingas
    - Ayodhya Ram Mandir (Ayodhya) — Lord Ram's birthplace, newly constructed grand temple
    - Shri Banke Bihari (Vrindavan) — Lord Krishna's beloved temple
    - Krishna Janmabhoomi (Mathura) — Lord Krishna's birthplace
    Best for UP: Kashi Vishwanath + Ram Mandir Ayodhya + Vrindavan/Mathura circuit

    UTTARAKHAND (Char Dham):
    - Kedarnath Dham — One of 12 Jyotirlingas, Himalayan temple, trek required, open May-Nov
    - Badrinath Temple — One of Char Dham, Lord Vishnu, open Apr-Nov
    - Gangotri Temple — Source of Ganga, Char Dham, open May-Nov
    - Yamunotri Temple — Source of Yamuna, Char Dham, open May-Nov
    Best season for Uttarakhand: May-June and September-October

    RAJASTHAN:
    - Khatu Shyam Ji Temple (Sikar) — Very popular, especially Monday and Falgun Mela
    - Nathdwara Shrinathji (Nathdwara) — Lord Krishna in Pushti Marg tradition
    Best: October to February

    GUJARAT:
    - Somnath Temple — First of 12 Jyotirlingas, by the sea, accessible year round
    - Dwarkadhish Temple — Lord Krishna's kingdom, Dwarka city
    - Nageshwar Jyotirlinga — One of 12 Jyotirlingas near Dwarka
    Gujarat temple circuit: Somnath + Dwarka + Nageshwar in one trip. Best October to March.

    MADHYA PRADESH:
    - Mahakaleshwar (Ujjain) — Jyotirlinga, famous Bhasma Aarti at 4 AM, accessible year round
    - Omkareshwar (Mandhata Island) — Jyotirlinga on an island in Narmada river
    - Trimbakeshwar (near Nashik, Maharashtra) — Jyotirlinga

    MAHARASHTRA:
    - Shirdi Sai Baba Temple — Highly accessible, flat terrain, excellent for elderly
    - Shri Siddhivinayak Ganapati Temple (Mumbai Prabhadevi) — Lord Ganesha, Mumbai
    - Bhimashankar Temple (Pune) — Jyotirlinga in the Sahyadri hills
    - Trimbakeshwar Jyotirlinga (Nashik) — Sacred Jyotirlinga

    ANDHRA PRADESH:
    - Tirupati Balaji Temple (Tirumala, Tirupati) — Most visited Hindu temple in the world
    - Sri Durga Malleswara Swamy Varla Devasthanam (Vijayawada) — Kanaka Durga temple

    TAMIL NADU:
    - Meenakshi Amman Darshan (Madurai) — Spectacular Dravidian architecture, Goddess Meenakshi
    - Kapaleeshwarar Temple (Chennai) — Lord Shiva temple in Mylapore
    Best Tamil Nadu temples: Meenakshi Amman Madurai, Brihadeeswarar Thanjavur, Kapaleeshwarar Chennai
    Best season for Tamil Nadu: October to March

    KERALA:
    - Sabarimala Sastha Temple — Lord Ayyappa, annual pilgrimage season November-January, significant trekking
    - Padmanabhaswamy Temple (Thiruvananthapuram) — Lord Vishnu, advance reservation required

    KARNATAKA:
    - Belur Chennakesava Temple (Belur) — Hoysala architecture, Lord Vishnu
    - Udupi Sri Krishna Temple

    ODISHA:
    - Puri Jagannath — Lord Jagannath, one of Char Dham of India, Rath Yatra in July is massive
    Best season: October to February. Avoid monsoon (heavy rains).

    PUNJAB:
    - Golden Temple Amritsar (Harmandir Sahib) — Sri Guru Granth Sahib Ji, open 24/7, most visited site in world
    Very accessible, wheelchairs available, no major seasonal restrictions.

    ASSAM:
    - Kamakhya Temple (Guwahati) — Shakti Peetha, Goddess Kamakhya, avoid monsoon (July-August)
    Best: October to April.

    WEST BENGAL:
    - Dakshineswar Kali Temple (Kolkata) — Ma Kali, very accessible
    - Kalighat Kali Temple (Kolkata) — One of 51 Shakti Peethas

    JAMMU & KASHMIR:
    - Shri Mata Vaishno Devi (Katra) — 14 km trek each way, helicopter available, open year round
    Avoid: Heavy monsoon (July-August). Best: March-June and September-November.
    """,

    # --------------------------------------------------------
    # ACCESSIBILITY GUIDE — For Elderly, Wheelchair, Families
    # --------------------------------------------------------
    """
    ACCESSIBILITY GUIDE — TEMPLES BY DIFFICULTY LEVEL

    EASY — Flat terrain, minimal walking, suitable for elderly and wheelchair users:
    - Shirdi Sai Baba Temple (Maharashtra) — Flat campus, wheelchair accessible, excellent for elderly
    - Tirupati Balaji Temple — assisted darshan bypasses most walking; temple has wheelchair ramps
    - Siddhivinayak Temple Mumbai — City temple, very accessible
    - Golden Temple Amritsar — Flat, wheelchair accessible, langar available
    - Dakshineswar Kali Temple Kolkata — Flat, accessible
    - Kashi Vishwanath (with assisted) — Short walk inside, manageable for elderly with coordinator
    - Mahakaleshwar Ujjain — Flat city temple, easy access
    - Ram Mandir Ayodhya — New temple, modern facilities, accessible
    - Meenakshi Amman Madurai — Flat city temple, manageable for elderly
    - Somnath Temple — Flat, sea-facing, accessible
    - Dwarkadhish Temple — Some steps but manageable

    MODERATE — Some steps or walking, manageable with assistance:
    - Vaishno Devi — 14 km trek, but helicopter/pony/palanquin available for elderly
    - Puri Jagannath — Temple has steps but assisted access reduces walking
    - Badrinath — High altitude (3133m), some walking, altitude sickness risk for elderly
    - Omkareshwar — Ferry + some steps, manageable

    DIFFICULT — Significant trekking, NOT recommended for elderly or those with mobility issues:
    - Kedarnath — 16-22 km trek (helicopter available but expensive and weather-dependent)
    - Yamunotri — 6 km trek from Janki Chatti
    - Gangotri — Accessible by road but high altitude
    - Bhimashankar — Forest trek required
    - Sabarimala — 4 km trek, 18 sacred steps

    FOR ELDERLY PARENTS — Top 5 Recommended:
    - Shirdi Sai Baba — Easiest, flat, peaceful
    - Tirupati Balaji — assisted darshan makes it very manageable
    - Kashi Vishwanath — Spiritually significant, manageable with coordinator
    - Ram Mandir Ayodhya — New modern facilities
    - Golden Temple Amritsar — Fully accessible, wheelchair available
    """,

    # --------------------------------------------------------
    # JYOTIRLINGA CIRCUIT GUIDE
    # --------------------------------------------------------
    """
    JYOTIRLINGA GUIDE — 12 Sacred Jyotirlingas of Lord Shiva

    The 12 Jyotirlingas are the most sacred abodes of Lord Shiva. Naman Darshan offers
    assisted Darshan coordination at all major Jyotirlingas.

    THE 12 JYOTIRLINGAS:
    1. Somnath (Prabhas Patan, Gujarat) — First Jyotirlinga, by the Arabian Sea
    2. Mallikarjuna (Srisailam, Andhra Pradesh) — On the banks of Krishna river
    3. Mahakaleshwar (Ujjain, MP) — Only Jyotirlinga facing south, famous Bhasma Aarti
    4. Omkareshwar (Mandhata Island, MP) — On an island in the Narmada river
    5. Kedarnath (Kedarnath, Uttarakhand) — In the Himalayas, open May-November
    6. Bhimashankar (Pune, Maharashtra) — In the Sahyadri hills, trek required
    7. Kashi Vishwanath (Varanasi, UP) — One of the most sacred, in the holy city of Kashi
    8. Trimbakeshwar (Nashik, MH) — Near Nashik, source of Godavari river
    9. Vaidyanath (Deoghar, Jharkhand) — Baidyanath Dham, also called Vaidyanatha
    10. Nageshwar (Dwarka, Gujarat) — Near Dwarka, in coastal Gujarat
    11. Rameshwaram (Tamil Nadu) — Southernmost Jyotirlinga, Char Dham of south
    12. Grishneshwar (Ellora, Maharashtra) — Last Jyotirlinga, near Ellora caves

    RECOMMENDED JYOTIRLINGA CIRCUITS:
    - Western Circuit: Somnath + Nageshwar + Trimbakeshwar + Bhimashankar + Grishneshwar (Gujarat + Maharashtra)
    - Northern Circuit: Kashi Vishwanath + Omkareshwar + Mahakaleshwar (UP + MP)
    - For first-time pilgrims: Mahakaleshwar (Ujjain) is the most accessible and famous for Bhasma Aarti
    - Best single Jyotirlinga to start with: Mahakaleshwar (Ujjain) or Kashi Vishwanath (Varanasi)

    Naman Darshan assisted Darshan covers: Somnath, Mahakaleshwar, Kashi Vishwanath, Trimbakeshwar,
    Omkareshwar, Nageshwar, Kedarnath.
    """,

    # --------------------------------------------------------
    # CHAR DHAM GUIDE
    # --------------------------------------------------------
    """
    CHAR DHAM YATRA GUIDE — Four Sacred Pilgrimages

    CHAR DHAM OF UTTARAKHAND (Chota Char Dham):
    1. Yamunotri — Source of Yamuna river. Open May-November. 6 km trek from Janki Chatti.
    2. Gangotri — Source of Ganga river. Open May-November. Accessible by road.
    3. Kedarnath — Jyotirlinga. Open May-November. 16-22 km trek or helicopter.
    4. Badrinath — Open April-November. Accessible by road. Lord Vishnu.

    TRADITIONAL CHAR DHAM (Adi Char Dham):
    1. Badrinath (Uttarakhand) — Lord Vishnu
    2. Dwarka (Gujarat) — Lord Krishna — Dwarkadhish Temple
    3. Puri (Odisha) — Lord Jagannath
    4. Rameshwaram (Tamil Nadu) — Lord Shiva

    BEST TIME FOR UTTARAKHAND CHAR DHAM YATRA: May-June and September-October
    Avoid: July-August (heavy monsoon, landslide risk), November+ (temples close)

    PLANNING TIPS:
    - Start from Haridwar or Rishikesh
    - Standard circuit: Yamunotri → Gangotri → Kedarnath → Badrinath
    - Helicopter packages available for all four dhams
    - Budget 7-10 days for complete Char Dham Yatra
    - Elderly or health concerns: helicopter recommended for Kedarnath
    """,

    # --------------------------------------------------------
    # NAMAN DARSHAN SERVICE KNOWLEDGE (FAQ)
    # --------------------------------------------------------
    """
    NAMAN DARSHAN — Complete Service Guide

    WHAT IS ASSISTED DARSHAN?
    Assisted Darshan is a priority queue bypass service. Instead of standing in the general queue
    for 2-8 hours at popular temples, Naman Darshan secures an official Sugam Pass or priority
    entry slot, so you complete darshan in 20-30 minutes. An on-ground coordinator guides your
    group from entry to exit.

    HOW IT WORKS (Step by Step):
    1. Share your name, WhatsApp number, temple, travel date, group size
    2. Once the required details are provided, Naman Darshan helps proceed with the booking process and slot verification
    3. You pay securely online (UPI / bank transfer) to Traininglobe Consultancy Pvt Ltd
    4. Instant WhatsApp confirmation with booking ID + coordinator's name and number
    5. On darshan day: coordinator is physically present with your group

    WHO IS THE COORDINATOR?
    - A trained on-ground guide physically present with your group on the darshan day
    - Knows every gate, entry timing, and shortcut at the temple
    - Available on call from morning to darshan completion
    - Their contact number is shared on WhatsApp before the darshan day

    PRICING:
    - Prices vary based on temple, date, group size, and slot availability
    - Per-person cost is typically very small compared to total travel expenses
    - No price is quoted by the chatbot — exact price is confirmed based on availability
    - Payment method: UPI, QR code, or NEFT bank transfer to Traininglobe Consultancy Pvt Ltd

    100% DARSHAN GUARANTEE:
    - If darshan does not happen for ANY reason — full refund
    - This guarantee is only available when you book through Naman Darshan
    - Does not apply to general queue bookings

    TRUST & COMPANY DETAILS:
    - Legal company: Traininglobe Consultancy Pvt Ltd
    - Brand name: Naman Darshan
    - Office: Express Trade Tower, Sector 132, Noida
    - Contact: +91 93119 73199 | namandarshan.com
    - 40 lakh+ devotees served, 4.7 star rating, 10,000-14,000+ darshans completed
    - Payment received under Traininglobe Consultancy Pvt Ltd (not a random name)

    DOCUMENTS REQUIRED (General):
    - Government photo ID: Aadhaar, Passport, Voter ID, PAN Card
    - Some temples have specific requirements (e.g., Tirupati dress code, Sabarimala initiation)

    DRESS CODE (General):
    - Modest, traditional clothing recommended at all temples
    - Some temples: cover your head (Golden Temple), remove shoes (all temples)
    - Tirupati: traditional Indian attire preferred; jeans sometimes not allowed in inner sanctum
    - Vaishno Devi trek: comfortable trekking shoes essential

    TEMPLE TIMINGS (General):
    - Most temples open at 5-6 AM and close around 9-10 PM with midday breaks
    - Bhasma Aarti at Mahakaleshwar Ujjain: 4 AM (very early, require special booking)
    - Vaishno Devi: 24/7 accessible (cave area)
    - Tirupati: assisted darshan times allocated by slot
    - Specific timings vary by season and special occasions

    CANCELLATION & RESCHEDULING:
    - If plans change, contact our team for rescheduling assistance
    - 100% Darshan Guarantee covers situations where darshan doesn't happen on the day
    - For reschedule terms, our team will explain options during the process
    """,

    # --------------------------------------------------------
    # POPULAR TEMPLE DETAILS
    # --------------------------------------------------------
    """
    TIRUPATI BALAJI TEMPLE — Detailed Guide
    Location: Tirumala, Tirupati, Andhra Pradesh
    Deity: Lord Venkateswara (Balaji)
    Altitude: 853 meters above sea level (Tirumala Hills)
    General queue wait: 4-8 hours (sometimes 12+ hours on weekends and festivals)
    With assisted Darshan: 20-30 minutes
    Best months: October to February (pleasant weather)
    Avoid: Summer (March-May) — very hot at Tirupati town though Tirumala is cooler
    Special: Head tonsuring (tonsure) is very common — separate queues for this
    Dress code: Traditional Indian attire; men in dhoti or formal pants; women in saree/salwar
    Elderly access: Good — assisted darshan minimizes walking; temple has wheelchair ramps
    Nearby temples: Padmavathi Temple (Tiruchanur), ISKCON Tirupati
    Special festivals: Brahmotsavam (September) — massive crowds
    """,

    """
    KASHI VISHWANATH — VARANASI — Detailed Guide
    Location: Varanasi (Kashi/Banaras), Uttar Pradesh
    Deity: Lord Shiva (Vishwanath = Lord of the Universe)
    Jyotirlinga: Yes — one of 12 Jyotirlingas
    General queue wait: 2-5 hours
    With assisted Darshan: 20-30 minutes
    Best months: October to March
    Special: New Kashi Vishwanath Corridor built in 2021 — modernized the temple complex
    Ganga Aarti: Must-see evening ritual at Dashashwamedh Ghat — 6:30-7:30 PM
    Nearby: Sankat Mochan (Hanuman), Durga Temple, Tulsi Manas Temple
    Elderly access: Good — flat temple corridor, manageable with coordinator
    DO: Visit early morning for least crowds
    """,

    """
    VAISHNO DEVI — Detailed Guide
    Location: Katra, Jammu & Kashmir (Trikuta Mountains)
    Deity: Mata Vaishno Devi (Adi Shakti)
    Trek distance: ~13-14 km one way (Katra to Bhavan)
    Helicopter: Available from Katra to Sanjichhat (saves 8-9 km of trek)
    Pony / Palanquin: Available for those who cannot trek
    General queue wait: 2-6 hours at Bhavan
    With assisted Darshan: Priority entry via Naman Darshan pass
    Best months: March to June, September to November
    Avoid: July-August (heavy rain, slippery paths), December-February (very cold, snow)
    Elderly: Helicopter + palanquin makes it feasible for elderly
    Special note: This is a sacred pilgrimage. Physical fitness recommended for trek.
    Navratri season (April and October): Extremely crowded — assisted pass essential
    """,

    """
    KEDARNATH DHAM — Detailed Guide
    Location: Rudraprayag, Uttarakhand (Himalayas)
    Deity: Lord Shiva (Kedarnath Jyotirlinga)
    Altitude: 3583 meters (11,755 feet) — high altitude
    Open season: May to November (usually opens Akshaya Tritiya, closes on Kartik Purnima)
    Trek: 16-22 km from Gaurikund (helicopter available from Phata/Guptkashi/Sitapur)
    Best months: May-June (post-opening), September-October (post-monsoon)
    Avoid: July-August (heavy rain, landslides), after mid-October (cold, closing time)
    Elderly: NOT recommended for trekking. Helicopter is the only suitable option.
    Altitude sickness: Real risk at 3583m — acclimatize at Haridwar/Rishikesh first
    Nearby: Chorabari Lake (Gandhi Sarovar), Shankaracharya Samadhi
    Important: Helicopter bookings fill up months in advance — book early
    """,

    """
    SHIRDI SAI BABA TEMPLE — Detailed Guide
    Location: Shirdi, Ahmednagar, Maharashtra
    Deity: Sai Baba of Shirdi
    General queue wait: 2-5 hours
    With assisted Darshan: 20-30 minutes
    Best months: Open and accessible all year round (no seasonal restrictions)
    Avoid: Major festivals (Ram Navami, Guru Purnima, Diwali) — extremely crowded
    Elderly access: EXCELLENT — flat campus, wheelchair accessible, very manageable
    THIS IS THE BEST TEMPLE FOR ELDERLY due to flat terrain and modern facilities
    Special: Kakad Aarti (5 AM), Dhoop Aarti (12 PM), Shej Aarti (10:30 PM) — all beautiful
    Nearby: Shani Shingnapur, Nasik (Trimbakeshwar), Aurangabad (Ellora-Ajanta)
    """,

    """
    MAHAKALESHWAR — UJJAIN — Detailed Guide
    Location: Ujjain, Madhya Pradesh
    Deity: Lord Shiva (Mahakaleshwar Jyotirlinga)
    Unique fact: Only Jyotirlinga facing south (Dakshinamukhi)
    Bhasma Aarti: Famous ritual at 4 AM using sacred ash — extremely rare and powerful
    General queue wait: 2-4 hours for darshan
    With assisted Darshan: 20-30 minutes
    Best months: All year accessible. October-March most pleasant.
    Elderly access: Good — flat city temple
    Special: Bhasma Aarti at 4 AM requires separate early booking and is a once-in-a-lifetime experience
    Nearby: Kal Bhairav Temple, Sandipani Ashram (where Krishna studied), Mangalnath Temple
    """,

    """
    RAM MANDIR AYODHYA — Detailed Guide
    Location: Ayodhya, Uttar Pradesh
    Deity: Lord Ram (Shri Ram Lalla)
    Inaugurated: January 22, 2024 — newly constructed grand temple
    Significance: Lord Ram's birthplace (Ram Janmabhoomi)
    General queue wait: 2-4 hours
    With assisted Darshan: 20-30 minutes
    Best months: October to March (pleasant weather). Diwali season (October-November) — special illuminations
    Elderly access: Good — new modern temple with good facilities
    Special: Diwali in Ayodhya — entire city illuminated, lakhs of earthen lamps on banks of Sarayu river
    Nearby: Hanuman Garhi, Kanak Bhavan, Saryu river ghat for aarti
    """,
]

# ============================================================
# BUILD THE VECTORSTORE
# ============================================================

def build_vectorstore():
    print("\nBuilding comprehensive knowledge base...")

    # Combine MongoDB data + structured knowledge
    all_texts = mongo_texts + TEMPLE_KNOWLEDGE
    print(f"Total knowledge chunks: {len(all_texts)}")

    # Chunk with overlap for better retrieval
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=80,
        separators=["\n\n", "\n", ".", " "]
    )
    docs = splitter.create_documents(all_texts)
    print(f"Split into {len(docs)} chunks.")

    # Embed
    print("Loading embedding model...")
    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-MiniLM-L3-v2"
    )

    print("Building FAISS index (this may take a minute)...")
    vectorstore = FAISS.from_documents(docs, embedding_model)

    # Save
    vectorstore.save_local("vectorstore")
    print(f"\nVectorstore saved with {len(docs)} chunks.")
    print("The chatbot now has comprehensive temple knowledge for better recommendations!")


if __name__ == "__main__":
    build_vectorstore()
