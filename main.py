import os, json, time, redis, threading, requests
from datetime import datetime
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

# حالة الجدار
SNIPER_MODE = {"active": False}

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

# ========== Ridder Scoring ==========
def ridder_score(symbol):
    try:
        candles = bitvavo.candles(symbol, '1m', {'limit': 3})
        if len(candles) < 3:
            return 0
        change = (float(candles[-1][4]) - float(candles[0][1])) / float(candles[0][1]) * 100
        avg_range = sum([abs(float(c[2]) - float(c[3])) for c in candles]) / 3
        avg_volume = sum([float(c[5]) for c in candles]) / 3
        return change * avg_range * avg_volume
    except:
        return 0

# ========== Bottom Scoring ==========
def breakout_score(symbol):
    try:
        candles = bitvavo.candles(symbol, '3m', {'limit': 3})
        if len(candles) < 3:
            return 0
        change = (float(candles[-1][4]) - float(candles[0][1])) / float(candles[0][1]) * 100
        avg_volume = sum([float(c[5]) for c in candles]) / 3
        return change * avg_volume
    except:
        return 0

# ========== فلتر ذكي ==========
def smart_filter():
    while True:
        for key in list(r.scan_iter("ridder:*")) + list(r.scan_iter("bottom:*")):
            symbol = key.decode().split(":")[1]
            try:
                data = json.loads(r.get(key))
                if data.get("notified"): continue

                candles = bitvavo.candles(symbol, '1m', {'limit': 5})
                if len(candles) < 5: continue
                prices = [float(c[4]) for c in candles]
                volumes = [float(c[5]) for c in candles]

                # شروط الإشارة المؤكدة
                if (prices[-1] > max(prices[:-1])
                    and prices[-1] > prices[0] * 1.01
                    and prices[-1] > prices[2]
                    and volumes[-1] > sum(volumes[:-1]) / 4):
                    
                    data["notified"] = True
                    r.set(key, json.dumps(data))
                    mode = "Ridder" if key.decode().startswith("ridder:") else "Bottom"
                    send_message(f"🚀 اشترِ {symbol} يا توتو {mode}")
                    send_to_toto(symbol, mode)

                # Sniper Mode - انفجار خفيف
                elif SNIPER_MODE["active"] and prices[-1] > prices[0] * 1.007:
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
            top = sorted(scored, key=lambda x: x[1], reverse=True)[:30]
            for key in r.scan_iter("ridder:*"): r.delete(key)
            for symbol, _ in top:
                r.set(f"ridder:{symbol}", json.dumps({"start": time.time(), "notified": False}))
        except Exception as e:
            print(f"[Ridder Error] {e}")
        time.sleep(300)

# ========== Bottom Loop ==========
def run_bottom_loop():
    while True:
        try:
            markets = bitvavo.markets()
            symbols = [m['market'] for m in markets if m['quote'] == 'EUR']
            scored = [(s, breakout_score(s)) for s in symbols]
            top = sorted(scored, key=lambda x: x[1], reverse=True)[:30]
            for key in r.scan_iter("bottom:*"): r.delete(key)
            for symbol, _ in top:
                r.set(f"bottom:{symbol}", json.dumps({"start": time.time(), "notified": False}))
        except Exception as e:
            print(f"[Bottom Error] {e}")
        time.sleep(300)

# ========== تنظيف ==========
def cleanup_expired():
    while True:
        for key in r.scan_iter("*:*"):
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
        bottom = [k.decode().split(":")[1] for k in r.scan_iter("bottom:*")]
        reply = "🚨 Ridder:\n" + "\n".join(ridder) if ridder else "🚨 لا عملات في Ridder\n"
        reply += "\n\n🔮 Bottom:\n" + "\n".join(bottom) if bottom else "\n🔮 لا عملات في Bottom"
        send_message(reply)

    elif msg == "افتح الجدار":
        SNIPER_MODE["active"] = True
        send_message("✅ تم تفعيل Sniper Mode! أي حركة غير مؤكدة سيتم إرسالها لك مباشرة.")

    elif msg == "اغلق الجدار":
        SNIPER_MODE["active"] = False
        send_message("🔕 تم إغلاق Sniper Mode. توقفت إشعارات الحركات غير المؤكدة.")

    return "ok"

# ========== تشغيل ==========
if __name__ == "__main__":
    for key in r.scan_iter("*"): r.delete(key)
    threading.Thread(target=run_ridder_loop).start()
    threading.Thread(target=run_bottom_loop).start()
    threading.Thread(target=smart_filter).start()
    threading.Thread(target=cleanup_expired).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))