import sys
import warnings
warnings.filterwarnings("ignore")

from rag_pipeline import generate_response
from booking_flow import update_booking

if __name__ == "__main__":
    uid = "test-puja-flow-001"
    
    query = "I want to book Rudrabhishek Puja."
    print("USER QUERY:", query)
    response = generate_response(query, [], uid)
    
    print("=" * 60)
    print("AI RESPONSE:")
    print(response)
    print("=" * 60)
