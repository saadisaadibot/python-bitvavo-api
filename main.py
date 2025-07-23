import os
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

@app.route("/", methods=["GET"])
def home():
    return "Toto Test Bot is running 🎯", 200

@app.route("/ping", methods=["GET"])
def ping():
    send_message("✅ البوت شغال من Railway!")
    return "Message sent!", 200

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)