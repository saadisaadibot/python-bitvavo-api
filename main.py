import os
from flask import Flask
from python_bitvavo_api.bitvavo import Bitvavo

app = Flask(__name__)

# إعداد المفاتيح من environment
bitvavo = Bitvavo({
  'APIKEY': os.getenv("BITVAVO_API_KEY"),
  'APISECRET': os.getenv("BITVAVO_API_SECRET"),
  'RESTURL': 'https://api.bitvavo.com/v2',
  'WSURL': 'wss://ws.bitvavo.com/v2/'
})

@app.route('/')
def get_candle():
    try:
        # طلب شمعة واحدة 1m لزوج ADA-EUR
        candles = bitvavo.candles("ADA-EUR", "1m", {"limit": 1})
        if candles:
            candle = candles[0]
            return f"""
                <h3>شمعة ADA-EUR</h3>
                <ul>
                    <li>الوقت: {candle[0]}</li>
                    <li>الفتح: {candle[1]}</li>
                    <li>الأعلى: {candle[2]}</li>
                    <li>الأدنى: {candle[3]}</li>
                    <li>الإغلاق: {candle[4]}</li>
                    <li>الحجم: {candle[5]}</li>
                </ul>
            """
        else:
            return "لم يتم استرجاع أي شموع"
    except Exception as e:
        return f"خطأ أثناء جلب الشمعة: {str(e)}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)