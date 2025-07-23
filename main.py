import os
from flask import Flask
from python_bitvavo_api.bitvavo import Bitvavo

app = Flask(__name__)

# إعداد API
bitvavo = Bitvavo({
    'APIKEY': os.getenv("BITVAVO_API_KEY"),
    'APISECRET': os.getenv("BITVAVO_API_SECRET")
})

@app.route('/')
def test_candle():
    try:
        candles = bitvavo.candles("BTC-EUR", "1m", { "limit": 1 })
        return f"Result: {candles}"
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)