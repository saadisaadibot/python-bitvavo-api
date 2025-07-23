import os
import requests
from flask import Flask
from python_bitvavo_api.bitvavo import Bitvavo

# إعداد التوكن والتشات ID من متغيرات البيئة
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# إرسال رسالة تيليغرام
def send_message(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": text}
        response = requests.post(url, data=data)
        print(f"Telegram Response: {response.text}")
    except Exception as e:
        print("Telegram Error:", str(e))

# تجربة مكتبة Bitvavo
def test_bitvavo():
    try:
        bitvavo = Bitvavo({
            'APIKEY': os.getenv("BITVAVO_API_KEY"),
            'APISECRET': os.getenv("BITVAVO_API_SECRET"),
            'RESTURL': 'https://api.bitvavo.com/v2'
        })
        markets = bitvavo.markets({})
        print("Bitvavo Connection OK ✅")
        send_message("✅ تم الاتصال مع Bitvavo بنجاح.")
    except Exception as e:
        print("Bitvavo Error:", str(e))
        send_message(f"❌ خطأ في Bitvavo:\n{str(e)}")

# Flask App لتشغيل البوت
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Running!"

if __name__ == "__main__":
    send_message("🚀 بوت كوكو بدأ التشغيل.")
    test_bitvavo()
    app.run(host="0.0.0.0", port=8080)