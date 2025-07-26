import os, json, time, redis, threading, requests
from flask import Flask, request
from python_bitvavo_api.bitvavo import Bitvavo

app = Flask(__name__)
r = redis.from_url(os.getenv("REDIS_URL"))

bitvavo = Bitvavo({
    'APIKEY': os.getenv("BITVAVO_API_KEY"),
    'APISECRET': os.getenv("BITVAVO_API_SECRET"),
    'RESTURL': 'https://api.bitvavo.com/v2',
    'WSURL': 'wss://ws.bitvavo.com/v2/'
})

BOT_TOKEN = os.getenv("BOT_TOKEN")
TOUTO_CHAT_ID = os.getenv("CHAT_ID")
TOTO_WEBHOOK = "https://totozaghnot-production.up.railway.app/webhook"

SNIPER_MODE = {"active": False}
SNIPER_LAST_ALERT = {}  # NEW: Cooldown لكل عملة

# ========== أدوات أساسية ==========
def send_message(text):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={
            "chat_id": TOUTO_CHAT_ID,
            "text": text
        })
    except:
        pass

def send_to_toto(symbol, mode):
    try:
        base = symbol.split("-")[0]
        requests.post(TOTO_WEBHOOK, json={"message": {"text": f"اشتري {base} يا توتو {mode}"}})
    except Exception as e:
        print(f"[Webhook Error] {e}")

# ========== قبضة النمر (صعود 3%) ==========
def is_strong_uptrend(candles):
    try:
        if len(candles) < 5:
            return False
        prices = [float(c[4]) for c in candles]
        bodies = [abs(float(c[4]) - float(c[1])) for c in candles]
        ranges = [abs(float(c[2]) - float(c[3])) for c in candles]

        if prices[-1] < prices[0] * 1.03:
            return False

        bullish_count = sum(1 for c in candles if float(c[4]) > float(c[1]))
        if bullish_count < 4:
            return False

        body_strength = sum([b/r if r > 0 else 0 for b, r in zip(bodies, ranges)]) / 5
        if body_strength < 0.5:
            return False

        return True
    except:
        return False

# ========== Ridder Score ==========
def ridder_score(symbol):
    try:
        candles = bitvavo.candles(symbol, '1m', {'limit': 3})
        if len(candles) < 3: return 0
        change = (float(candles[-1][4]) - float(candles[0][1])) / float(candles[0][1]) * 100
        avg_range = sum([abs(float(c[2]) - float(c[3])) for c in candles]) / 3
        avg_volume = sum([float(c[5]) for c in candles]) / 3
        return change * avg_range * avg_volume
    except:
        return 0

# ========== الفلتر الذكي ==========
def smart_filter():
    while True:
        for key in list(r.scan_iter("ridder:*")):
            symbol = key.decode().split(":")[1]
            try:
                data = json.loads(r.get(key))
                if data.get("notified"): continue

                candles = bitvavo.candles(symbol, '1m', {'limit': 5})
                if len(candles) < 5: continue

                if is_strong_uptrend(candles):
                    data["notified"] = True
                    r.set(key, json.dumps(data))
                    send_message(f"🚀 اشترِ {symbol} يا توتو Ridder")
                    send_to_toto(symbol, "Ridder")

                elif SNIPER_MODE["active"]:
                    prices = [float(c[4]) for c in candles]
                    bodies = [abs(float(c[4]) - float(c[1])) for c in candles]
                    ranges = [abs(float(c[2]) - float(c[3])) for c in candles]

                    if prices[-1] > prices[0] * 1.007:
                        bullish_count = sum(1 for c in candles if float(c[4]) > float(c[1]))
                        body_strength = sum([b/r if r > 0 else 0 for b, r in zip(bodies, ranges)]) / len(candles)

                        if bullish_count >= 3 and body_strength > 0.35:
                            now = time.time()
                            last = SNIPER_LAST_ALERT.get(symbol, 0)
                            if now - last > 180:  # تهدئة 3 دقائق
                                SNIPER_LAST_ALERT[symbol] = now
                                send_message(f"👀 انفجار صغير محتمل: {symbol}")
            except Exception as e:
                print(f"[Smart Filter Error] {e}")
        time.sleep(2)

# ========== Ridder Loop ==========
def run_ridder_loop():
    while True:
        try:
            markets = bitvavo.markets()
            symbols = [m['market'] for m in markets if m['quote'] == 'EUR']
            scored = [(s, ridder_score(s)) for s in symbols]
            top = sorted(scored, key=lambda x: x[1], reverse=True)[:60]
            for key in r.scan_iter("ridder:*"): r.delete(key)
            for symbol, _ in top:
                r.set(f"ridder:{symbol}", json.dumps({"start": time.time(), "notified": False}))
        except Exception as e:
            print(f"[Ridder Error] {e}")
        time.sleep(300)

# ========== تنظيف ==========
def cleanup_expired():
    while True:
        for key in r.scan_iter("ridder:*"):
            try:
                data = json.loads(r.get(key))
                if time.time() - data["start"] > 300:
                    r.delete(key)
            except:
                continue
        time.sleep(60)

# ========== Telegram Webhook ==========
@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    msg = data.get("message", {}).get("text", "").lower()
    chat_id = str(data.get("message", {}).get("chat", {}).get("id", ""))
    if chat_id != str(TOUTO_CHAT_ID): return "ok"

    if msg == "شو عم تعمل":
        ridder = [k.decode().split(":")[1] for k in r.scan_iter("ridder:*")]
        reply = "🚨 Ridder:\n" + "\n".join(ridder) if ridder else "🚨 لا عملات في Ridder"
        send_message(reply)

    elif msg == "افتح الجدار":
        SNIPER_MODE["active"] = True
        send_message("✅ تم تفعيل Sniper Mode! أي حركة غير مؤكدة سيتم إرسالها لك مباشرة.")

    elif msg == "اغلق الجدار":
        SNIPER_MODE["active"] = False
        send_message("🔕 تم إغلاق Sniper Mode. توقفت إشعارات الحركات غير المؤكدة.")

    return "ok"

# ========== التشغيل ==========
if __name__ == "__main__":
    for key in r.scan_iter("*"): r.delete(key)
    threading.Thread(target=run_ridder_loop).start()
    threading.Thread(target=smart_filter).start()
    threading.Thread(target=cleanup_expired).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))