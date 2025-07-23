import os
import redis
import requests
from flask import Flask, request
from bitvavo_client.bitvavo import Bitvavo
from threading import Thread
from datetime import datetime

# إعداد Flask
app = Flask(__name__)

# المتغيرات البيئية
BITVAVO_API_KEY = os.getenv("BITVAVO_API_KEY")
BITVAVO_API_SECRET = os.getenv("BITVAVO_API_SECRET")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
REDIS_URL = os.getenv("REDIS_URL")

# Redis
r = redis.from_url(REDIS_URL)

# تهيئة Bitvavo
bitvavo = Bitvavo({
    'APIKEY': BITVAVO_API_KEY,
    'APISECRET': BITVAVO_API_SECRET
})

# إرسال رسالة Telegram
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# حساب سكور عملة بناءً على آخر 3 شموع
def calculate_score(candles):
    try:
        total_change = 0
        total_range = 0
        total_volume = 0
        for c in candles[-3:]:
            open_, high, low, close, volume = map(float, c[1:6])
            total_change += (close - open_) / open_
            total_range += (high - low) / open_
            total_volume += volume
        return (total_change * 100) + total_range + (total_volume / 10000)
    except:
        return -999

# جمع أفضل 25 عملة بناء على الشموع
def get_top_25():
    try:
        all_markets = bitvavo.markets()
        scores = []
        for market in all_markets:
            symbol = market['market']
            if not symbol.endswith('-EUR'):
                continue
            try:
                candles = bitvavo.candles(symbol, '1m', limit=3)
                if len(candles) >= 3:
                    score = calculate_score(candles)
                    scores.append((symbol, score))
            except:
                continue
        scores.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in scores[:25]]
    except Exception as e:
        send_telegram(f"حدث خطأ أثناء جمع العملات: {str(e)}")
        return []

# بدء مراقبة العملات
def monitor_coins():
    r.flushdb()
    r.set("state", "عم اشرب متي 🧉")
    send_telegram("🚀 KOKO بدأ العمل واختيار أفضل 25 عملة للمراقبة...")
    top_coins = get_top_25()
    for coin in top_coins:
        r.set(f"watch:{coin}", datetime.now().isoformat())
    send_telegram("✅ تم اختيار ومراقبة أفضل 25 عملة.")
    r.set("state", "🚨 تحت المراقبة: " + ", ".join(top_coins))

# أمر شو عم تعمل
@app.route('/', methods=["POST"])
def handle_msg():
    data = request.get_json()
    if "message" in data:
        text = data["message"].get("text", "")
        if text.strip() == "شو عم تعمل":
            state = r.get("state")
            if state:
                return state.decode()
            else:
                return "مافي شي حالياً"
    return "جاهز"

# تشغيل الخدمة
def start():
    Thread(target=monitor_coins).start()

if __name__ == '__main__':
    start()
    app.run(host='0.0.0.0', port=8080)