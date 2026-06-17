from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEY          = os.getenv("GROQ_API_KEY")
MONGO_URI             = os.getenv("MONGO_URI")
RAZORPAY_KEY_ID       = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET   = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")