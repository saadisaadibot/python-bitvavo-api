import os
import json
import time
import redis
import threading
import requests
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

WEBHOOK_URL = "https://totozaghnot-production.up.railway.app"

def send_to_toto(text):
    try:
        requests.post(WEBHOOK_URL, json={"message": text})
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

# ========== Breakout Scoring ==========
def breakout_score(symbol):
    try:
        candles = bitvavo.candles(symbol, '1h', {'limit': 30})
        if len(candles) < 30:
            return 0
        highs = [float(c[2]) for c in candles[:-1]]
        volumes = [float(c[5]) for c in candles[:-1]]
        last = candles[-1]
        last_close = float(last[4])
        last_volume = float(last[5])
        max_high = max(highs)
        avg_volume = sum(volumes) / len(volumes)
        score = 0
        if last_close > max_high: score += 1
        if last_volume > avg_volume * 2: score += 1
        if last_close > float(last[1]): score += 1
        return score
    except:
        return 0

# ========== Ridder Loop ==========
def run_ridder_loop():
    while True:
        try:
            markets = bitvavo.markets()
            symbols = [m['market'] for m in markets if m['quote'] == 'EUR' and m['status'] == 'trading']
            scored = [(s, ridder_score(s)) for s in symbols]
            scored = [(s, sc) for s, sc in scored if sc > 0]
            top30 = sorted(scored, key=lambda x: x[1], reverse=True)[:30]

            for key in r.scan_iter("ridder:*"):
                r.delete(key)

            for symbol, _ in top30:
                r.set(f"ridder:{symbol}", json.dumps({
                    "start": time.time(),
                    "expires": time.time() + 1800,
                    "notified": False
                }))
        except Exception as e:
            print(f"[Ridder Error] {e}")
        time.sleep(1800)

# ========== Ridder Trigger ==========
def check_ridder_triggers():
    while True:
        for key in r.scan_iter("ridder:*"):
            symbol = key.decode().split(":")[1]
            try:
                data = json.loads(r.get(key))
                if data.get("notified") or time.time() - data["start"] < 180:
                    continue
                candles = bitvavo.candles(symbol, '1m', {'limit': 2})
                open_ = float(candles[0][1])
                close = float(candles[-1][4])
                volume = float(candles[-1][5])
                change = (close - open_) / open_ * 100
                if change > 2.0 and close > open_ and volume > 0:
                    data["notified"] = True
                    r.set(key, json.dumps(data))
                    send_to_toto(f"✅ Ridder اشتري {symbol} يا توتو 🚨")
            except:
                continue
        time.sleep(20)

# ========== Bottom Loop ==========
def run_bottom_loop():
    while True:
        try:
            markets = bitvavo.markets()
            symbols = [m['market'] for m in markets if m['quote'] == 'EUR' and m['status'] == 'trading']
            scored = [(s, breakout_score(s)) for s in symbols]
            top25 = [s for s, sc in scored if sc >= 2][:25]

            for symbol in top25:
                key = f"bottom:{symbol}"
                if not r.exists(key):
                    r.set(key, json.dumps({
                        "start": time.time(),
                        "expires": time.time() + 1800,
                        "notified": False
                    }))
        except Exception as e:
            print(f"[Bottom Error] {e}")
        time.sleep(600)

# ========== Bottom Trigger ==========
def check_bottom_triggers():
    while True:
        for key in r.scan_iter("bottom:*"):
            symbol = key.decode().split(":")[1]
            try:
                data = json.loads(r.get(key))
                if data.get("notified") or time.time() - data["start"] < 180:
                    continue
                candles = bitvavo.candles(symbol, '1m', {'limit': 2})
                open_ = float(candles[0][1])
                close = float(candles[-1][4])
                volume = float(candles[-1][5])
                change = (close - open_) / open_ * 100
                if change > 1.5 and close > open_ and volume > 0:
                    data["notified"] = True
                    r.set(key, json.dumps(data))
                    send_to_toto(f"✅ Bottom اشترِ {symbol} يا توتو 🔮")
            except:
                continue
        time.sleep(20)

# ========== تنظيف العملات المنتهية ==========
def cleanup_expired():
    while True:
        for key in r.scan_iter("*:*"):
            try:
                data = json.loads(r.get(key))
                if time.time() > data.get("expires", 0):
                    r.delete(key)
            except:
                continue
        time.sleep(60)

# ========== Webhook ==========
@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    msg = data.get("message", {}).get("text", "").lower()
    chat_id = str(data.get("message", {}).get("chat", {}).get("id", ""))
    if msg == "شو عم تعمل":
        ridder = [k.decode().split(":")[1] for k in r.scan_iter("ridder:*")]
        bottom = [k.decode().split(":")[1] for k in r.scan_iter("bottom:*")]

        now = datetime.now()
        remaining = (30 - (now.minute % 30)) % 30
        symbol = f"-{remaining}"

        reply = f"🚨 العملات تحت المراقبة (Ridder) {symbol}:\n"
        reply += "\n".join(f"• {s}" for s in ridder) if ridder else "لا شي حالياً"
        reply += "\n\n🔮 مرشحة للانفجار (Bottom):\n"
        reply += "\n".join(f"• {s}" for s in bottom) if bottom else "لا شي حالياً"
        send_to_toto(reply)
    return "ok"

# ========== التشغيل ==========
if __name__ == "__main__":
    for key in r.scan_iter("*"):
        r.delete(key)
    threading.Thread(target=run_ridder_loop).start()
    threading.Thread(target=check_ridder_triggers).start()
    threading.Thread(target=run_bottom_loop).start()
    threading.Thread(target=check_bottom_triggers).start()
    threading.Thread(target=cleanup_expired).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))