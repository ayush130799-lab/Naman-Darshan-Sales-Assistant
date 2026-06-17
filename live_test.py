import warnings
warnings.filterwarnings("ignore")

from sales_logic  import detect_user_intent
from rag_pipeline import generate_response

QUERY = "can you find best yatra packages for me?"
UID   = "live-test-pkg-001"

print("QUERY  :", QUERY)
print("INTENT :", detect_user_intent(QUERY))
print()
resp = generate_response(QUERY, [], UID)
print("RESPONSE:")
print(resp)
