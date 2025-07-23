import os
import sys
import requests
from flask import Flask

# أضف مجلد المكتبة لمسار الاستيراد
sys.path.append("python_bitvavo_api")
from bitvavo import Bitvavo

app = Flask(__name__)

BITVAVO_API_KEY = os.getenv("BITVAVO_API_KEY")
BITVAVO_API_SECRET = os.getenv("BITVAVO_API_SECRET")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bitvavo = Bitvavo({
    'APIKEY': BITVAVO_API_KEY,
    'APISECRET': BITVAVO_API_SECRET,
    'RESTURL': 'https://api.bitvavo.com/v2',
    'WSURL': 'wss://ws.bitvavo.com/v2/'
})

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

@app.route("/")
def fetch_and_notify():
    try:
        result = {}
        for symbol in ["ADA-EUR", "BTC-EUR", "ETH-EUR"]:
            candles = bitvavo.candles(symbol, '1m', {'limit': 3})
            result[symbol] = candles
        send_telegram_message("✅ تم جلب 3 شموع لكل عملة بنجاح!")
        return str(result)
    except Exception as e:
        send_telegram_message(f"❌ حدث خطأ أثناء جلب الشموع: {str(e)}")
        return f"Error: {str(e)}"

app.run(host="0.0.0.0", port=8080)