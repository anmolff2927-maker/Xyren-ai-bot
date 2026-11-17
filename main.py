
import os
import logging
import requests
from flask import Flask, request, jsonify

# ---------------- CONFIGURATION ----------------

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

log = logging.getLogger("xyren-ai")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

if not TELEGRAM_TOKEN:
    log.error("TELEGRAM_BOT_TOKEN is missing!")

if not GEMINI_KEY:
    log.error("GEMINI_API_KEY is missing!")

TELEGRAM_API = (
    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    if TELEGRAM_TOKEN else ""
)

# ---------------- CHAT MEMORY ----------------

chat_history = {}
MAX_HISTORY = 12

# ---------------- TELEGRAM FUNCTIONS ----------------

def send_message(chat_id, text):
    if not TELEGRAM_API:
        log.error("Telegram token missing")
        return False

    url = f"{TELEGRAM_API}/sendMessage"

    chunks = [
        text[i:i + 4000]
        for i in range(0, len(text), 4000)
    ] or [""]

    success = True

    for chunk in chunks:
        try:
            response = requests.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": chunk
                },
                timeout=20
            )

            if not response.ok:
                log.error("Telegram send error: %s", response.text)
                success = False

        except requests.RequestException as error:
            log.error("Telegram connection error: %s", error)
            success = False

    return success


def send_typing(chat_id):
    try:
        requests.post(
            f"{TELEGRAM_API}/sendChatAction",
            json={
                "chat_id": chat_id,
                "action": "typing"
            },
            timeout=10
        )
    except requests.RequestException as error:
        log.warning("Typing error: %s", error)


# ---------------- GEMINI AI ----------------

def ask_gemini(chat_id, message):

    if not GEMINI_KEY:
        return "Gemini API key missing. Please contact the bot owner."

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
                    "Give accurate, useful and clear answers. "
                    "Be natural and conversational. "
                    "Do not claim to be ChatGPT."
                )
            }]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1500
        }
    }

    try:
        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": GEMINI_KEY
            },
            json=payload,
            timeout=50
        )

        if not response.ok:
            log.error(
                "GEMINI API ERROR %s: %s",
                response.status_code,
                response.text[:1500]
            )

            return (
                "Sorry bhai! AI service mein problem aa gayi. "
                "Thodi der baad try karo."
            )

        data = response.json()

        candidates = data.get("candidates", [])

        if not candidates:
            log.error("Gemini returned no candidates: %s", data)
            return "Sorry! AI abhi answer generate nahi kar paya."

        parts = candidates[0].get(
            "content", {}
        ).get("parts", [])

        answer = "".join(
            part.get("text", "")
            for part in parts
        ).strip()

        if not answer:
            log.error("Gemini returned empty response")
            return "Sorry! Mujhe answer nahi mila. Dobara try karo."

        # Save chat history only after successful response
        history.extend([
            {
                "role": "user",
                "parts": [{"text": message}]
            },
            {
                "role": "model",
                "parts": [{"text": answer}]
            }
        ])

        chat_history[chat_id] = history[-MAX_HISTORY:]

        return answer

    except requests.Timeout:
        log.error("Gemini request timed out")
        return "AI ko reply dene mein time lag raha hai. Dobara try karo."

    except requests.RequestException as error:
        log.exception("Gemini connection failed: %s", error)
        return "AI server connection problem. Please try again."

    except Exception as error:
        log.exception("Gemini unexpected error: %s", error)
        return "Sorry! Kuch technical problem aa gayi."


# ---------------- HOME PAGE ----------------

@app.route("/", methods=["GET"])
def home():
    return "Xyren AI is Online! 🤖"


# ---------------- TELEGRAM WEBHOOK ----------------

@app.route("/webhook", methods=["POST"])
def webhook():

    # Verify secret only when configured in Render.
    # Remove WEBHOOK_SECRET from Render to disable
    # verification while troubleshooting.
    if WEBHOOK_SECRET:
        import hmac

        received_secret = request.headers.get(
            "X-Telegram-Bot-Api-Secret-Token", ""
        )

        if not hmac.compare_digest(
            received_secret, WEBHOOK_SECRET
        ):
            log.error("Webhook secret verification failed")
            return "Unauthorized", 403

    try:
        update = request.get_json(silent=True) or {}

        message = update.get("message", {})

        if not message or "text" not in message:
            return "OK", 200

        chat_id = message["chat"]["id"]
        text = message["text"].strip()

        log.info(
            "Telegram message received: %s",
            text[:100]
        )

        # START COMMAND
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

        # HELP COMMAND
        if text == "/help":
            send_message(
                chat_id,
                "🤖 XYREN AI HELP\n\n"
                "Simply send me any question.\n"
                "I support Hindi, Hinglish and English.\n\n"
                "/reset - Clear chat history"
            )
            return "OK", 200

        # RESET COMMAND
        if text == "/reset":
            chat_history.pop(chat_id, None)
            send_message(chat_id, "✅ Chat memory cleared!")
            return "OK", 200

        if not text:
            return "OK", 200

        # AI CHAT
        send_typing(chat_id)

        answer = ask_gemini(chat_id, text)

        send_message(chat_id, answer)

    except Exception as error:
        log.exception("BOT ERROR: %s", error)

        try:
            if "chat_id" in locals():
                send_message(
                    chat_id,
                    "⚠️ Something went wrong. Please try again."
                )
        except Exception:
            log.exception("Error sending failure message")

    return "OK", 200


# ---------------- HEALTH CHECK ----------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "online",
        "bot": "Xyren AI",
        "model": MODEL
    })


# ---------------- START SERVER ----------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
        )
            
