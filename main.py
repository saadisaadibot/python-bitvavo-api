import os
import time
import redis
import requests
from flask import Flask, request
from threading import Thread
from python_bitvavo_api.bitvavo import Bitvavo  # ✅ هذا التعديل الأساسي

# إعداد المفاتيح من المتغيرات البيئية
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
REDIS_URL = os.getenv("REDIS_URL")
BITVAVO_API_KEY = os.getenv("BITVAVO_API_KEY")
BITVAVO_API_SECRET = os.getenv("BITVAVO_API_SECRET")

# إعداد الاتصال بـ Redis و Flask و Bitvavo
r = redis.from_url(REDIS_URL)
app = Flask(__name__)
bitvavo = Bitvavo({ 'APIKEY': BITVAVO_API_KEY, 'APISECRET': BITVAVO_API_SECRET })

# إرسال إشعار Telegram
def send_message(text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text}
    )

# جلب وتحليل العملات
def get_top_25():
    try:
        markets = bitvavo.markets()
        tickers = bitvavo.ticker24h()

        active_eur = [m['market'] for m in markets if m['status'] == 'trading' and m['quote'] == 'EUR']
        filtered = [t for t in tickers if t['market'] in active_eur]

        for t in filtered:
            try:
                t['change'] = float(t['priceChangePercentage'])
            except:
                t['change'] = -999

        top = sorted(filtered, key=lambda x: x['change'], reverse=True)[:25]
        r.set("top25", ','.join([t['market'] for t in top]))
        return True

    except Exception as e:
        send_message(f"❌ فشل جلب العملات: {e}")
        return False

# مسار Webhook
@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    msg = data.get("message", {}).get("text", "")
    chat_id = data.get("message", {}).get("chat", {}).get("id", "")

    if str(chat_id) != CHAT_ID:
        return "unauthorized"

    if msg.strip().lower() == "شو عم تعمل":
        coins = r.get("top25")
        if coins:
            coins = coins.decode().split(",")
            text = "👀 العملات تحت المراقبة:\n" + "\n".join(coins)
        else:
            text = "🚫 لا توجد عملات تحت المراقبة حالياً"
        send_message(text)

    return "ok"

# بدء المهمة عند التشغيل
def start_analysis():
    r.delete("top25")
    ok = get_top_25()
    if ok:
        send_message("✅ تم اختيار أعلى 25 عملة للمراقبة.")
    else:
        send_message("❌ فشل في تحليل العملات.")

# تشغيل كل شيء
if __name__ == "__main__":
    Thread(target=start_analysis).start()
    app.run(host="0.0.0.0", port=8080)