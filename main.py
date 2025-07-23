import os
from bitvavo import Bitvavo
import requests

# Telegram إعدادات
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(text):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": text})
    except Exception as e:
        print("Telegram error:", e)

# Bitvavo إعداد الاتصال
bitvavo = Bitvavo({
    'APIKEY': os.getenv("BITVAVO_API_KEY"),
    'APISECRET': os.getenv("BITVAVO_API_SECRET")
})

# تجربة طلب شموع لعملة BTC-EUR
try:
    candles = bitvavo.candles("BTC-EUR", "1m", { "limit": 5 })
    send_telegram("✅ تم الحصول على الشموع:\n\n" + str(candles))
    print("✅ Candles response:")
    print(candles)
except Exception as e:
    send_telegram("❌ خطأ في طلب الشموع:\n" + str(e))
    print("❌ Error:", e)