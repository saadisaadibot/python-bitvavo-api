import os, time, json, hmac, hashlib, requests

# تحميل المفاتيح
BITVAVO_API_KEY = os.getenv("BITVAVO_API_KEY")
BITVAVO_API_SECRET = os.getenv("BITVAVO_API_SECRET")

def bitvavo_signed_get(path):
    timestamp = str(int(time.time() * 1000))
    method = "GET"
    body = ""
    msg = timestamp + method + path + body
    signature = hmac.new(BITVAVO_API_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()

    headers = {
        "Bitvavo-Access-Key": BITVAVO_API_KEY,
        "Bitvavo-Access-Signature": signature,
        "Bitvavo-Access-Timestamp": timestamp,
        "Bitvavo-Access-Window": "10000"
    }

    url = "https://api.bitvavo.com" + path
    print(f"\n🔍 طلب: {path}")
    try:
        response = requests.get(url, headers=headers)
        print(f"📡 كود الحالة: {response.status_code}")
        if response.status_code == 200:
            print("✅ نجاح ✅")
        else:
            print("⚠️ فشل، الرد:")
        print(response.text[:500])
        return response.status_code, response.text
    except Exception as e:
        print(f"❌ استثناء في الاتصال: {e}")
        return 0, str(e)

def run_tests():
    if not BITVAVO_API_KEY or not BITVAVO_API_SECRET:
        print("❌ تأكد من وجود BITVAVO_API_KEY و BITVAVO_API_SECRET في environment variables.")
        return

    print("✅ المفاتيح تم تحميلها بنجاح.")

    # 1. تجربة جلب الأسواق
    status_code, text = bitvavo_signed_get("/v2/markets")

    markets_supported = []
    if status_code == 200:
        try:
            markets = json.loads(text)
            print(f"\n📈 عدد الأسواق: {len(markets)}")
            for m in markets:
                if m["market"] == "BTC-EUR":
                    print("✅ BTC-EUR موجود في الأسواق 🎯")
                if m.get("supportsCandles"):
                    markets_supported.append(m["market"])
            print(f"🕯️ الأزواج التي تدعم الشموع: {len(markets_supported)}")
        except Exception as e:
            print(f"❌ فشل في تحليل بيانات الأسواق: {e}")
    else:
        print("❌ فشل في جلب الأسواق. لا يمكن الاستمرار بالتحقق.")

    # 2. تجربة جلب شموع BTC-EUR
    print("\n🕯️ تجربة جلب شموع BTC-EUR...")
    bitvavo_signed_get("/v2/market/BTC-EUR/candles?interval=1m&limit=3")

if __name__ == "__main__":
    run_tests()