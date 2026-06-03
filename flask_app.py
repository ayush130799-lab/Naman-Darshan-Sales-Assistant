from flask import Flask, request, jsonify
from flask_cors import CORS

from rag_pipeline import generate_response
from memory import get_memory, save_memory

app = Flask(__name__)
CORS(app)

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json or {}
        user_id = data.get("user_id", "anonymous")
        query = data.get("query")

        if not query:
            return jsonify({"error": "Query is required"}), 400

        # Load memory
        history = get_memory(user_id)

        # Generate response
        response = generate_response(query, history)
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

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
