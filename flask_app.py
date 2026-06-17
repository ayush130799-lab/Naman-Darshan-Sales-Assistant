# flask_app.py
# Flask REST API — runs alongside the Streamlit app on port 5000.
#
# HOW TO RUN:
#   1. Activate your virtual environment first:
#        myenv\Scripts\activate          (Windows CMD)
#        myenv/scripts/activate.ps1     (PowerShell)
#   2. Then run:
#        python flask_app.py
#
# Routes:
#   POST /chat                 — AI chat endpoint (existing)
#   POST /razorpay/webhook     — Razorpay payment webhook (new)
#   GET  /payment/status/<uid> — Check payment status for a user (new)

from flask import Flask, request, jsonify
from flask_cors import CORS

# Only import the lightweight payment handler at module level.
# rag_pipeline (heavy ML imports) is loaded lazily inside the /chat route
# so the Flask server starts instantly without loading FAISS / sentence-transformers.
from razorpay_handler import (
    update_payment_status,
    get_payment_status,
    verify_webhook_signature,
)

app = Flask(__name__)
CORS(app)


# --------------------------------------------------
# Existing: /chat
# (rag_pipeline is imported lazily to keep Flask startup fast)
# --------------------------------------------------

@app.route("/chat", methods=["POST"])
def chat():
    try:
        # Lazy imports — loaded only on first request, not at startup
        from rag_pipeline import generate_response
        from memory import get_memory, save_memory

        data = request.json or {}
        user_id = data.get("user_id", "anonymous")
        query = data.get("query")

        if not query:
            return jsonify({"error": "Query is required"}), 400

        # Load memory
        history = get_memory(user_id)

        # Generate response
        response = generate_response(query, history, user_id)
        print("Pipeline raw response:", response)

        # Normalize response to plain string
        if isinstance(response, dict) and "content" in response:
            response_text = response["content"]
        else:
            response_text = str(response)

        # Save memory
        save_memory(user_id, query, response_text)

        return jsonify({
            "response": response_text,
            "history": get_memory(user_id)
        })

    except Exception as e:
        print("Error in /chat route:", e)
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------
# New: /razorpay/webhook
# Handles Razorpay payment events.
# Must respond 200 quickly — Razorpay retries on non-200.
# --------------------------------------------------

@app.route("/razorpay/webhook", methods=["POST"])
def razorpay_webhook():
    """
    Razorpay sends a POST to this endpoint when a payment event occurs.
    We handle: payment_link.paid
    """
    payload_body = request.get_data()  # raw bytes for HMAC verification
    signature = request.headers.get("X-Razorpay-Signature", "")
    event_str = ""

    try:
        # 1. Parse the event payload
        event_data = request.get_json(force=True) or {}
        event_str = event_data.get("event", "")
        print(f"[webhook] Received Razorpay event: {event_str}")

        # 2. Verify HMAC signature
        if not verify_webhook_signature(payload_body, signature):
            print(f"[webhook] Signature verification FAILED for event: {event_str}")
            return jsonify({"error": "Invalid signature"}), 400

        # 3. Handle payment_link.paid
        if event_str == "payment_link.paid":
            payload = event_data.get("payload", {})
            payment_link_entity = payload.get("payment_link", {}).get("entity", {})
            payment_entity = payload.get("payment", {}).get("entity", {})

            payment_link_id = payment_link_entity.get("id", "")
            razorpay_payment_id = payment_entity.get("id", "")

            print(f"[webhook] Payment confirmed: link_id={payment_link_id}, payment_id={razorpay_payment_id}")

            success = update_payment_status(
                payment_link_id=payment_link_id,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_signature=signature,
                event_type=event_str,
            )

            if success:
                print(f"[webhook] Payment status updated successfully for link_id={payment_link_id}")
                return jsonify({"status": "ok"}), 200
            else:
                print(f"[webhook] Payment status update FAILED for link_id={payment_link_id}")
                # Still return 200 to prevent Razorpay from retrying indefinitely
                return jsonify({"status": "error", "detail": "DB update failed"}), 200

        # 4. Acknowledge other events (we don't process them)
        print(f"[webhook] Unhandled event type: {event_str} — acknowledged.")
        return jsonify({"status": "ignored"}), 200

    except Exception as e:
        print(f"[webhook] Error processing event '{event_str}': {e}")
        # Return 200 so Razorpay doesn't retry — log the failure for manual review
        return jsonify({"status": "error", "detail": str(e)}), 200


# --------------------------------------------------
# New: /payment/status/<user_id>
# Convenience endpoint to check payment status for debugging / external use.
# --------------------------------------------------

@app.route("/payment/status/<user_id>", methods=["GET"])
def payment_status(user_id: str):
    """
    Returns the current payment status for a given user_id.
    Query param ?booking_id=ND-... can be used to look up a specific booking.
    """
    try:
        booking_id = request.args.get("booking_id")
        status = get_payment_status(user_id=user_id, booking_id=booking_id)
        return jsonify(status), 200
    except Exception as e:
        print(f"[/payment/status] Error: {e}")
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------
# Run
# --------------------------------------------------

if __name__ == "__main__":
    print("Starting Naman Darshan Flask server on http://127.0.0.1:5000")
    print("  POST /chat               — AI chat")
    print("  POST /razorpay/webhook   — Razorpay payment events")
    print("  GET  /payment/status/<id> — Payment status check")
    # use_reloader=False prevents Flask watchdog from restarting on every
    # torch/transformers library file change inside myenv (WinError 10038).
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
