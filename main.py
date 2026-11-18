import os
import requests
import logging
from flask import Flask, request, jsonify

app = Flask(__name__)

# LOGGING
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API SETTINGS
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")

# Yahan model name theek kar diya hai
GEMINI_MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
)

GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/"
    f"v1beta/models/{GEMINI_MODEL}:generateContent"
)

TELEGRAM_URL = (
    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
)

# USER MEMORY
user_memory = {}

# BOT SETTINGS
MAX_HISTORY = 10


def send_message(chat_id, text):
    try:
        response = requests.post(
            TELEGRAM_URL,
            json={
                "chat_id": chat_id,
                "text": text
            },
            timeout=20
        )

        if not response.ok:
            logger.error(
                "Telegram error: %s",
                response.text
            )

        return response.ok

    except Exception:
        logger.exception("Telegram send error")
        return False


def ask_gemini(user_id, user_text):

    if not GEMINI_KEY:
        logger.error("GEMINI_API_KEY missing")
        return "Bhai, Gemini API key set nahi hai."

    history = user_memory.get(user_id, [])

    history.append({
        "role": "user",
        "parts": [{"text": user_text}]
    })

    payload = {
        "contents": history,
        "generationConfig": {
            "maxOutputTokens": 1500
        }
    }

    try:
        response = requests.post(
            GEMINI_URL,
            params={"key": GEMINI_KEY},
            json=payload,
            timeout=60
        )

        if not response.ok:
            logger.error(
                "Gemini API error %s: %s",
                response.status_code,
                response.text
            )
            return f"Gemini API Error {response.status_code}: {response.text}"

        data = response.json()

        candidates = data.get("candidates", [])

        if not candidates:
            logger.error("Gemini returned no candidates: %s", data)
            return "Bhai, AI se response nahi mila. Dobara try karo."

        parts = candidates[0].get("content", {}).get("parts", [])

        answer = "".join(
            part.get("text", "")
            for part in parts
        ).strip()

        if not answer:
            return "Bhai, AI ka response empty aaya."

        history.append({
            "role": "model",
            "parts": [{"text": answer}]
        })

        user_memory[user_id] = history[-MAX_HISTORY:]

        return answer

    except requests.exceptions.Timeout:
        logger.exception("Gemini request timed out")
        return "Bhai, AI response dene mein time le raha hai. Dobara try karo."

    except Exception as e:
        logger.exception("Gemini request failed")
        return f"Error details: {str(e)}"


@app.route("/", methods=["GET"])
def home():
    return "XYREN AI is running!"


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "online",
        "bot": "XYREN AI"
    })


@app.route("/webhook", methods=["POST"])
def webhook():

    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN missing")
        return jsonify({"error": "Bot token missing"}), 500

    if WEBHOOK_SECRET:
        secret = request.headers.get(
            "X-Telegram-Bot-Api-Secret-Token"
        )

        if secret != WEBHOOK_SECRET:
            return jsonify({"error": "Unauthorized"}), 403

    try:
        update = request.get_json(silent=True) or {}

        message = update.get("message", {})

        if not message:
            return jsonify({"ok": True})

        chat_id = message.get("chat", {}).get("id")
        user_id = str(
            message.get("from", {}).get("id", chat_id)
        )

        text = message.get("text", "").strip()

        if not chat_id or not text:
            return jsonify({"ok": True})

        # START COMMAND
        if text == "/start":
            send_message(
                chat_id,
                "Namaste bhai! ❤️\n\n"
                "Main XYREN AI hoon, tumhara personal AI assistant.\n\n"
                "Mujhse kuch bhi pooch sakte ho!\n\n"
                "Commands:\n"
                "/start - Start bot\n"
                "/help - Help\n"
                "/reset - Reset memory"
            )
            return jsonify({"ok": True})

        # HELP COMMAND
        if text == "/help":
            send_message(
                chat_id,
                "XYREN AI Help 🤖\n\n"
                "Bas mujhe message bhejo aur main jawab dunga.\n\n"
                "/start - Start\n"
                "/help - Help\n"
                "/reset - Clear chat memory"
            )
            return jsonify({"ok": True})

        # RESET COMMAND
        if text == "/reset":
            user_memory.pop(user_id, None)

            send_message(
                chat_id,
                "Bhai, tumhari chat memory reset ho gayi! ❤️"
            )
            return jsonify({"ok": True})

        # IGNORE OTHER COMMANDS
        if text.startswith("/"):
            send_message(chat_id, "Unknown command. /help likho.")
            return jsonify({"ok": True})

        # GEMINI AI RESPONSE
        answer = ask_gemini(user_id, text)

        send_message(chat_id, answer)

        return jsonify({"ok": True})

    except Exception:
        logger.exception("Webhook error")
        return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
)
    
