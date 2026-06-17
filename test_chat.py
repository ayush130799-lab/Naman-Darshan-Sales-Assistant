"""
test_chat.py — Quick end-to-end test of the chat pipeline.
Run: python test_chat.py
"""
import sys, os, warnings
warnings.filterwarnings("ignore")

from rag_pipeline import generate_response
from booking_flow import get_booking

SEPARATOR = "-" * 60

def test(label, query, uid, history=None):
    print(f"\n{SEPARATOR}")
    print(f"TEST: {label}")
    print(f"USER: {query}")
    response = generate_response(query, history or [], uid)
    safe_bot = response[:300].encode('ascii', 'ignore').decode('ascii')
    print(f"BOT:  {safe_bot}")
    session = get_booking(uid)
    print(f"STATE: {session['state']} | temple={session['temple']} | people={session['people']} | elderly={session['elderly']}")
    return response

if __name__ == "__main__":
    print("=== Naman Darshan AI — End-to-End Test ===")

    uid = "test-e2e-001"

    # --- Flow test: state machine ---
    test("1. Greeting + Temple Detection",
         "Tirupati ke darshan ke liye baat karna tha", uid)

    test("2. Date Collection",
         "October mein plan kar rahe hain, 15 October", uid)

    test("3. People Count",
         "Hum 4 log hain", uid)

    test("4. Elderly detection",
         "Haan mere dada dadi bhi aa rahe hain, wo elderly hain", uid)

    test("5. Qualification",
         "Hum Noida se aa rahe hain", uid)

    # After this, state should be NORMAL_CHAT
    # --- Objection tests (fresh sessions, no temple context) ---
    uid2 = "test-e2e-002"
    test("6. Trust Objection (payment fear) — fresh session",
         "Main online payment se thoda darta hoon, fraud ho jaata hai aajkal", uid2)

    uid3 = "test-e2e-003"
    test("7. Company Name Objection — fresh session",
         "Payment kisi aur naam se kyun aa raha hai? Company ka naam alag kyun hai?", uid3)

    uid4 = "test-e2e-004"
    test("8. GST Objection — fresh session",
         "GST number kyun nahi hai aapke invoice mein?", uid4)

    uid5 = "test-e2e-005"
    test("9. Price Objection — fresh session",
         "Price bahut zyada lagta hai, main khud ja sakta hoon free mein queue mein", uid5)

    uid6 = "test-e2e-006"
    test("10. Delay Objection — fresh session",
         "Abhi nahi, pehle ghar pe family se discuss karke batata hoon, thoda time chahiye", uid6)

    print(f"\n{SEPARATOR}")
    print("All tests completed!")
