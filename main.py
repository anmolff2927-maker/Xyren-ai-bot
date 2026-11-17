
import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# API SETTINGS
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")

# Temporary chat memory (per user)
chat_history = {}
MAX_HISTORY = 12

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"

    # Telegram message size limit
    chunks = [
        text[i:i + 4000]
        for i in range(0, len(text), 4000)
    ] or [""]

    for chunk in chunks:
        requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": chunk
            },
            timeout=20
        )


def send_typing(chat_id):
    requests.post(
        f"{TELEGRAM_API}/sendChatAction",
        json={
            "chat_id": chat_id,
            "action": "typing"
        },
        timeout=10
    )


def ask_gemini(chat_id, message):
    history = chat_history.get(chat_id, [])

    contents = history + [{
        "role": "user",
        "parts": [{"text": message}]
    }]

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{MODEL}:generateContent"
    )

    payload = {
        "systemInstruction": {
            "parts": [{
                "text": (
                    "Your name is Xyren AI. "
                    "You are a friendly, intelligent AI assistant. "
                    "Reply in the language used by the user. "
                    "Support Hindi, Hinglish and English. "
                    "Give accurate, clear and helpful answers. "
                    "Be natural and conversational."
                )
            }]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1500
        }
    }

    response = requests.post(
        url,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_KEY
        },
        json=payload,
        timeout=55
    )

    if not response.ok:
        print("Gemini error:", response.text)
        return "Sorry! AI server busy hai. Thodi der baad try karo."

    data = response.json()

    answer = "".join(
        part.get("text", "")
        for part in data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    ).strip()

    if not answer:
        return "Sorry! Mujhe answer nahi mila."

    # Save conversation
    history.append({
        "role": "user",
        "parts": [{"text": message}]
    })

    history.append({
        "role": "model",
        "parts": [{"text": answer}]
    })

    chat_history[chat_id] = history[-MAX_HISTORY:]

    return answer


@app.route("/", methods=["GET"])
def home():
    return "Xyren AI is Online! 🤖"


@app.route("/webhook", methods=["POST"])
def webhook():

    # Verify Telegram webhook secret
    if request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token"
    ) != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        update = request.get_json(silent=True) or {}
        message = update.get("message", {})

        if not message or "text" not in message:
            return "OK", 200

        chat_id = message["chat"]["id"]
        text = message["text"].strip()

        if text == "/start":
            send_message(
                chat_id,
                "👋 Welcome to XYREN AI!\n\n"
                "🤖 Your personal AI assistant.\n"
                "💬 Hindi + English support.\n\n"
                "Mujhse kuch bhi pucho!\n\n"
                "/help - Help\n"
                "/reset - Clear chat memory"
            )
            return "OK", 200

        if text == "/help":
            send_message(
                chat_id,
                "🤖 XYREN AI HELP\n\n"
                "Simply send me any question.\n"
                "I can chat in Hindi, Hinglish and English.\n\n"
                "/reset - Clear chat history"
            )
            return "OK", 200

        if text == "/reset":
            chat_history.pop(chat_id, None)
            send_message(chat_id, "✅ Chat memory cleared!")
            return "OK", 200

        if not text:
            return "OK", 200

        send_typing(chat_id)

        answer = ask_gemini(chat_id, text)
        send_message(chat_id, answer)

    except Exception as error:
        print("Bot error:", str(error))

        try:
            if "chat_id" in locals():
                send_message(
                    chat_id,
                    "⚠️ Something went wrong. Please try again."
                )
        except Exception:
            pass

    return "OK", 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "online",
        "bot": "Xyren AI"
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(
        host="0.0.0.0",
        port=port
  )
  
