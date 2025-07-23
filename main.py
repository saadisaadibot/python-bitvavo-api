import os
import requests
from flask import Flask, request

# إعداد المفاتيح من Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# إعداد Flask
app = Flask(__name__)

# دالة إرسال رسالة تيليغرام
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"خطأ في إرسال الرسالة: {e}")

# إرسال إشعار عند بدء التشغيل
send_telegram_message("✅ السكربت اشتغل تمام")

# راوت استقبال الرسائل من تيليغرام
@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and "message" in data:
        text = data["message"].get("text", "").strip()
        chat_id = str(data["message"]["chat"]["id"])

        if text == "شو عم تعمل" and chat_id == CHAT_ID:
            send_telegram_message("عم اشرب متي 😎")

    return {"ok": True}

# تشغيل السيرفر
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080)