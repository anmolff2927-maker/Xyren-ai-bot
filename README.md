
# 🤖 Xyren AI

Welcome to **Xyren AI** – Your Personal AI Telegram Assistant!

Xyren AI is an intelligent Telegram chatbot powered by Google Gemini AI.

## ✨ Features

- 💬 Normal AI Chatting
- 🇮🇳 Hindi & Hinglish Support
- 🌍 English Support
- 🧠 Conversation Memory
- ⚡ Fast AI Responses
- 🔄 Reset Chat Command
- 🤖 Telegram Bot Integration

## 🛠️ Technologies Used

- Python
- Flask
- Google Gemini API
- Telegram Bot API
- Render Hosting
- GitHub

## 📋 Telegram Commands

| Command | Description |
|---|---|
| /start | Start the bot |
| /help | Show help |
| /reset | Clear chat memory |

## ⚙️ Environment Variables

Add these variables in Render:

- TELEGRAM_BOT_TOKEN
- GEMINI_API_KEY
- WEBHOOK_SECRET

Never share your API keys publicly.

## 🚀 Deployment

1. Upload the project to GitHub.
2. Connect GitHub to Render.
3. Select Web Service.
4. Set Build Command: `pip install -r requirements.txt`
5. Set Start Command: `gunicorn main:app`
6. Add environment variables.
7. Deploy your service.

## 👨‍💻 Developer

**Xyren AI**

Made with ❤️ using Python and Google Gemini.

---

⭐ Thanks for using Xyren AI!
