import os
import json
import time
import redis
import threading
import requests
from flask import Flask, request
from python_bitvavo_api.bitvavo import Bitvavo  # حسب مجلدك

# --- إعداد ---
app = Flask(__name__)
r = redis.from_url(os.getenv("REDIS_URL"))
bitvavo = Bitvavo({
    'APIKEY': os.getenv("BITVAVO_API_KEY"),
    'APISECRET': os.getenv("BITVAVO_API_SECRET"),
    'RESTURL': 'https://api.bitvavo.com/v2',
    'WSURL': 'wss://ws.bitvavo.com/v2/'
})
TOUTO_CHAT_ID = os.getenv("CHAT_ID")
BOT_TOKEN = os.getenv("BOT_TOKEN")

def send_to_touto(text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={
        "chat_id": TOUTO_CHAT_ID,
        "text": text
    })

def reset_memory():
    for key in r.scan_iter("*"):
        r.delete(key)

# --- جمع السوق الأوروبي كل 5 د ---
global_eur_symbols = []

def update_symbols_loop():
    global global_eur_symbols
    while True:
        try:
            markets = bitvavo.markets()
            global_eur_symbols = [m['market'] for m in markets if m['quote'] == 'EUR' and m['status'] == 'trading']
        except: pass
        time.sleep(300)

# --- سكور Ridder ---
def ridder_score(symbol):
    try:
        candles = bitvavo.candles(symbol, '1m', { 'limit': 3 })
        if len(candles) < 3:
            return 0
        change = (float(candles[-1][4]) - float(candles[0][1])) / float(candles[0][1]) * 100
        avg_range = sum([abs(float(c[2]) - float(c[3])) for c in candles]) / 3
        avg_volume = sum([float(c[5]) for c in candles]) / 3
        return change * avg_range * avg_volume
    except:
        return 0

# --- سكور Breakout ---
def breakout_score(symbol):
    try:
        candles = bitvavo.candles(symbol, '1h', { 'limit': 30 })
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

# --- Ridder Mode ---
def run_ridder_mode():
    while True:
        scored = []
        for s in global_eur_symbols:
            score = ridder_score(s)
            if score:
                scored.append((s, score))
            time.sleep(0.1)
        top25 = sorted(scored, key=lambda x: x[1], reverse=True)[:25]
        for symbol, _ in top25:
            key = f"ridder:{symbol}"
            if not r.exists(key):
                r.set(key, json.dumps({"start": time.time(), "expires": time.time() + 1800}))
        check_ridder_triggers()
        time.sleep(60)

# --- Bottom Mode ---
def run_bottom_mode():
    while True:
        for symbol in global_eur_symbols:
            score = breakout_score(symbol)
            if score >= 3:
                key = f"bottom:{symbol}"
                if not r.exists(key):
                    r.set(key, json.dumps({"start": time.time(), "expires": time.time() + 1800}))
                    send_to_touto(f"اشتري {symbol.split('-')[0]} يا توتو  Bottom")
            time.sleep(0.2)
        time.sleep(60)

def check_ridder_triggers():
    for key in r.scan_iter("ridder:*"):
        symbol = key.decode().split(":")[1]
        try:
            candles = bitvavo.candles(symbol, '1m', { 'limit': 2 })
            if len(candles) < 2:
                continue
            change = (float(candles[-1][4]) - float(candles[0][1])) / float(candles[0][1]) * 100
            if change > 2.0:
                send_to_touto(f"اشتري {symbol.split('-')[0]} يا توتو  Ridder")
                r.delete(key)
        except:
            continue

def cleanup_expired():
    while True:
        for key in r.scan_iter("*:*"):
            try:
                data = json.loads(r.get(key))
                if time.time() > data.get("expires", 0):
                    r.delete(key)
            except: continue
        time.sleep(60)

@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    msg = data.get("message", {}).get("text", "").lower()
    chat_id = data.get("message", {}).get("chat", {}).get("id", "")
    if msg == "شو عم تعمل":
        ridder = [k.decode().split(":")[1] for k in r.scan_iter("ridder:*")]
        bottom = [k.decode().split(":")[1] for k in r.scan_iter("bottom:*")]
        msg = "🚨 العملات تحت المراقبة (Ridder):\n"
        msg += "\n".join(f"• {s}" for s in ridder) if ridder else "لا شي حالياً"
        msg += "\n\n🔮 مرشحة للانفجار (Bottom):\n"
        msg += "\n".join(f"• {s}" for s in bottom) if bottom else "لا شي حالياً"
        send_to_touto(msg)
    return "ok"

if __name__ == "__main__":
    reset_memory()
    threading.Thread(target=update_symbols_loop).start()
    threading.Thread(target=run_ridder_mode).start()
    threading.Thread(target=run_bottom_mode).start()
    threading.Thread(target=cleanup_expired).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))