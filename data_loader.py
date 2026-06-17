# data_loader.py
#
# Loads ALL relevant collections from the MongoDB Atlas "temples_clone" database
# and converts every document into a structured plain-text chunk for embedding.
#
# Collections loaded (sales-relevant):
#   Core product data  : temples, darshans, Yatra_packages, aartis, chadhavas,
#                        prasadams, pujas, blogs
#   Company knowledge  : company_info, agent_rules, objections
#   Operational data   : ops_resources (coordinators / city resources)
#   Contextual         : panchangdatas, posts, polls
#
# Usage:
#   from data_loader import load_data
#   texts = load_data()   # returns List[str]

import os
import logging
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mongo connection
# ---------------------------------------------------------------------------

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://ayush:strongpassword123@sales-ai-backend.gofnxnk.mongodb.net/"
)
DB_NAME = "temples_clone"

# ---------------------------------------------------------------------------
# Field-level converters
# ---------------------------------------------------------------------------

def _stringify_value(v):
    """Recursively flatten any value to a readable string."""
    if isinstance(v, list):
        parts = []
        for item in v:
            parts.append(_stringify_value(item))
        return "; ".join(p for p in parts if p)
    if isinstance(v, dict):
        inner = " | ".join(
            f"{k}: {_stringify_value(val)}"
            for k, val in v.items()
            if k not in ("_id", "__v") and val not in (None, "", [], {})
        )
        return inner
    return str(v).strip() if v not in (None, "", [], {}) else ""


def _skip_key(k: str) -> bool:
    """Fields that add no semantic value for embeddings."""
    skip = {
        "_id", "__v", "structuredData", "seoTitle", "seoDescription",
        "seoKeywords", "slug", "image", "historyArchitectureImage",
        "religiousSignificanceImage", "festivalCelebrationsImage",
        "surroundingsDesc", "createdAt", "updatedAt", "updated_at",
        "ctaTitle", "ctaDescription", "ctaText", "ctaLink",
        "experienceTitle", "experienceDesc", "experienceSections",
        "structureTitle", "structureDesc", "structurePoints", "structureFooter",
        "visitorGuide", "visitorGuideFooter", "whyVisitTitle", "whyVisitFooter",
        "introHighlights", "subTitle", "notificationlogs", "devicetokens",
    }
    return k in skip


# ---------------------------------------------------------------------------
# Collection-specific formatters
# ---------------------------------------------------------------------------

def _format_generic(doc: dict, label: str = "") -> str:
    """Default formatter: key: value pairs, skipping noise fields."""
    parts = []
    if label:
        parts.append(f"[{label}]")
    for k, v in doc.items():
        if _skip_key(k):
            continue
        sv = _stringify_value(v)
        if sv:
            parts.append(f"{k}: {sv}")
    return " | ".join(parts)


def _format_temple(doc: dict) -> str:
    """Rich formatter for temples collection."""
    parts = [f"[TEMPLE] {doc.get('name', '')} — {doc.get('location', '')}"]
    
    for field in ["description", "darshanTimings", "entryFee", "address",
                  "connectivity", "historyArchitectureDesc",
                  "religiousSignificanceDesc", "festivalCelebrationsDesc",
                  "notableEvents", "darshan_cta_url"]:
        val = doc.get(field)
        if val and str(val).strip():
            parts.append(f"{field}: {str(val).strip()}")

    # Darshan schedule
    schedule = doc.get("darshanSchedule", [])
    if schedule:
        sched_str = "; ".join(
            f"{s.get('label','')} {s.get('time','')}".strip()
            for s in schedule if isinstance(s, dict)
        )
        if sched_str:
            parts.append(f"darshanSchedule: {sched_str}")

    # FAQs — very useful for sales retrieval
    faqs = doc.get("faqs", [])
    if faqs:
        faq_strs = []
        for faq in faqs:
            if isinstance(faq, dict):
                q = faq.get("question", "")
                a = faq.get("answer", "")
                if q and a:
                    faq_strs.append(f"Q: {q} A: {a}")
        if faq_strs:
            parts.append("FAQs: " + " || ".join(faq_strs))

    return " | ".join(p for p in parts if p)


def _format_darshan(doc: dict) -> str:
    """Formatter for darshans (assisted darshan listing per temple)."""
    parts = [f"[ASSISTED DARSHAN] {doc.get('temple_name', doc.get('name', ''))}"]
    for field in ["description", "price", "location", "duration",
                  "inclusions", "exclusions", "highlights",
                  "how_it_works", "guarantee", "booking_steps",
                  "darshan_time", "group_size", "temple_slug"]:
        val = doc.get(field)
        if val is not None:
            sv = _stringify_value(val)
            if sv:
                parts.append(f"{field}: {sv}")
    return " | ".join(parts)


def _format_yatra_package(doc: dict) -> str:
    """Formatter for Yatra_packages — core assisted product info."""
    parts = [f"[YATRA PACKAGE] {doc.get('temple_name', '')} — {doc.get('location', '')}"]
    for field in ["temple_slug", "active", "best_for", "pain_points",
                  "queue_time_general", "sales_pitch", "vip_benefits", "assisted_benefits",
                  "vip_time_estimate", "assisted_time_estimate", "vip_fees", "assisted_fees",
                  "brand", "guarantee", "payment_to", "service_provider", "vip_wait_time", "assisted_wait_time"]:
        val = doc.get(field)
        if val is not None:
            sv = _stringify_value(val)
            if sv:
                parts.append(f"{field}: {sv}")
    return " | ".join(parts)


def _format_aarti(doc: dict) -> str:
    """Formatter for aartis collection (aarti lyrics / bhajans)."""
    # title and deity may be dicts with 'english' / 'hindi' keys
    title = doc.get("title", "")
    if isinstance(title, dict):
        title = title.get("english") or title.get("hindi") or ""
    deity = doc.get("deity", "")
    if isinstance(deity, dict):
        deity = deity.get("english") or deity.get("hindi") or ""
    parts = [f"[AARTI/BHAJAN] {title}" + (f" — Deity: {deity}" if deity else "")]

    tags = doc.get("tags", [])
    if tags:
        parts.append(f"tags: {', '.join(tags)}")

    # Extract english lyrics / content from sections
    sections = doc.get("sections", [])
    for section in sections:
        if not isinstance(section, dict):
            continue
        heading = section.get("heading", "")
        if isinstance(heading, dict):
            heading = heading.get("english") or heading.get("hindi") or ""
        content = section.get("content", "")
        if isinstance(content, dict):
            # prefer english, fall back to hindi
            content = content.get("english") or content.get("hindi") or ""
        if isinstance(content, list):
            content = " ".join(str(c) for c in content)
        if content:
            parts.append(f"{heading}: {str(content)[:600]}")

    return " | ".join(p for p in parts if p)


def _format_chadhava(doc: dict) -> str:
    """Formatter for chadhavas (offerings)."""
    name = doc.get("name", "")
    parts = [f"[CHADHAVA/OFFERING] {name}"]
    for field in ["description", "price", "temple", "category",
                  "significance", "items_included"]:
        val = doc.get(field)
        if val:
            sv = _stringify_value(val)
            if sv:
                parts.append(f"{field}: {sv}")
    return " | ".join(parts)


def _format_prasadam(doc: dict) -> str:
    """Formatter for prasadams."""
    name = doc.get("name", "")
    parts = [f"[PRASADAM] {name}"]
    for field in ["description", "price", "temple", "category",
                  "weight", "delivery_info", "ingredients"]:
        val = doc.get(field)
        if val:
            sv = _stringify_value(val)
            if sv:
                parts.append(f"{field}: {sv}")
    return " | ".join(parts)


def _format_puja(doc: dict) -> str:
    """Formatter for pujas."""
    name = doc.get("name", doc.get("puja_name", ""))
    parts = [f"[PUJA] {name}"]
    for field in ["description", "price", "duration", "temple",
                  "benefits", "inclusions", "procedure", "significance",
                  "booking_info", "pandit_info"]:
        val = doc.get(field)
        if val:
            sv = _stringify_value(val)
            if sv:
                parts.append(f"{field}: {sv}")
    return " | ".join(parts)


def _format_blog(doc: dict) -> str:
    """Formatter for blogs — useful for Q&A and pilgrim tips."""
    title = doc.get("title", "")
    parts = [f"[BLOG] {title}"]
    for field in ["content", "summary", "excerpt", "category", "tags"]:
        val = doc.get(field)
        if val:
            sv = _stringify_value(val)
            if sv and len(sv) < 4000:   # cap very long blog bodies
                parts.append(f"{field}: {sv}")
    return " | ".join(parts)


def _format_company_info(doc: dict) -> str:
    """Company / brand information — critical for trust questions."""
    parts = ["[COMPANY INFO — NAMAN DARSHAN]"]
    for k, v in doc.items():
        if _skip_key(k):
            continue
        sv = _stringify_value(v)
        if sv:
            parts.append(f"{k}: {sv}")
    return " | ".join(parts)


def _format_agent_rules(doc: dict) -> str:
    """Agent rules / objection-handling guidelines."""
    parts = ["[AGENT RULES / SALES GUIDELINES]"]
    for field in ["critical_rules", "intent_entity_validation",
                  "retrieval_rules", "follow_up_triggers"]:
        val = doc.get(field)
        if val:
            sv = _stringify_value(val)
            if sv:
                parts.append(f"{field}: {sv}")
    return " | ".join(parts)


def _format_objection(doc: dict) -> str:
    """Formatter for objections collection — sales objection handling."""
    parts = ["[OBJECTION HANDLING]"]
    for k, v in doc.items():
        if _skip_key(k):
            continue
        sv = _stringify_value(v)
        if sv:
            parts.append(f"{k}: {sv}")
    return " | ".join(parts)


def _format_ops_resource(doc: dict) -> str:
    """On-ground coordinator / city resource info."""
    parts = ["[OPS RESOURCE]"]
    for k, v in doc.items():
        if _skip_key(k):
            continue
        sv = _stringify_value(v)
        if sv:
            parts.append(f"{k}: {sv}")
    return " | ".join(parts)


def _format_panchang(doc: dict) -> str:
    """Panchang data for auspicious dates."""
    parts = ["[PANCHANG / AUSPICIOUS DATES]"]
    for k, v in doc.items():
        if _skip_key(k):
            continue
        sv = _stringify_value(v)
        if sv:
            parts.append(f"{k}: {sv}")
    return " | ".join(parts)


# ---------------------------------------------------------------------------
# Master loader
# ---------------------------------------------------------------------------

COLLECTION_CONFIG = {
    # (collection_name): (formatter_fn, label_for_logging)
    "temples":          (_format_temple,         "temples"),
    "darshans":         (_format_darshan,        "darshans"),
    "Yatra_packages":   (_format_yatra_package,  "Yatra_packages"),
    "aartis":           (_format_aarti,          "aartis"),
    "chadhavas":        (_format_chadhava,       "chadhavas"),
    "prasadams":        (_format_prasadam,       "prasadams"),
    "pujas":            (_format_puja,           "pujas"),
    "blogs":            (_format_blog,           "blogs"),
    "company_info":     (_format_company_info,   "company_info"),
    "agent_rules":      (_format_agent_rules,    "agent_rules"),
    "objections":       (_format_objection,      "objections"),
    "ops_resources":    (_format_ops_resource,   "ops_resources"),
    "panchangdatas":    (_format_panchang,       "panchangdatas"),
}


def load_data() -> list:
    """
    Connect to MongoDB Atlas, load all sales-relevant collections,
    and return a flat list of plain-text strings ready for embedding.

    Returns:
        List[str]: Each string is a rich text representation of one document.
    """
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    available = set(db.list_collection_names())
    texts = []
    total_docs = 0

    for col_name, (formatter, label) in COLLECTION_CONFIG.items():
        if col_name not in available:
            logger.warning(f"Collection '{col_name}' not found in DB — skipping.")
            continue

        try:
            docs = list(db[col_name].find())
            loaded = 0
            for doc in docs:
                text = formatter(doc)
                if text and len(text.strip()) > 10:
                    texts.append(text)
                    loaded += 1
            total_docs += loaded
            logger.info(f"  [OK] {col_name}: {loaded}/{len(docs)} docs converted to text")
            print(f"  [OK] {label}: {loaded} documents loaded")
        except Exception as e:
            logger.error(f"  [ERR] Failed to load '{col_name}': {e}")
            print(f"  [ERR] {label}: ERROR - {e}")

    client.close()

    print(f"\nTotal text chunks from MongoDB: {total_docs}")
    return texts


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Loading ALL collections from MongoDB Atlas (temples_clone)")
    print("=" * 60)
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    data = load_data()
    print(f"\nTotal chunks ready for embedding: {len(data)}")
    print("\n--- Sample chunks ---")
    for chunk in data[:5]:
        print(f"\n{chunk[:300]}{'...' if len(chunk) > 300 else ''}")
        print("-" * 40)
