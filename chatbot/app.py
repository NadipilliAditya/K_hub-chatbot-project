import os
import json
import httpx
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

app = Flask(__name__, static_url_path='/static')

# File to store chats
CHAT_FILE = "chats.json"

# Load existing chats or initialize empty dict
if os.path.exists(CHAT_FILE):
    with open(CHAT_FILE, "r", encoding="utf-8") as f:
        chats = json.load(f)
else:
    chats = {}

def save_chats():
    with open(CHAT_FILE, "w", encoding="utf-8") as f:
        json.dump(chats, f, indent=2, ensure_ascii=False)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get("question", "").strip()
    chat_id = data.get("chatId")  # Optional: client sends active chat ID

    logger.info(f"➡️ Received question: {question} for chat ID: {chat_id}")

    if not question:
        return jsonify({"answer": "⚠️ Please enter a question."}), 400

    # If chat_id not sent or unknown, create a new one
    if not chat_id or chat_id not in chats:
        chat_id = str(int(os.times()[4]*1000))  # generate a unique id
        chats[chat_id] = {
            "messages": []
        }

    # Append user's message to chat
    chats[chat_id]["messages"].append({"sender": "user", "text": question})

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question}
        ]
    }

    try:
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        answer = data["choices"][0]["message"]["content"]

        # Append bot reply to chat
        chats[chat_id]["messages"].append({"sender": "bot", "text": answer})

        save_chats()

        return jsonify({
            "answer": answer,
            "chatId": chat_id,
            "messages": chats[chat_id]["messages"]
        })

    except Exception as e:
        logger.error(f"❌ Groq API Error: {e}")
        return jsonify({"answer": "❌ Error: Could not fetch answer."}), 500


if __name__ == '__main__':
    app.run(debug=True)
