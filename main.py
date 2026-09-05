import os
import time
import threading
import requests
import pandas as pd
import yfinance as yf
from flask import Flask
from BpSifat import QuotexComplete12MasterBot

app = Flask(__name__)

@app.route('/')
def home():
    return "Quotex Live Market Signal Bot is Active!"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram_message(text):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send message: {e}")

def fetch_quotex_live_candles(symbol="EURUSD=X", interval="1m", period="1d"):
    """
    Quotex-এর ফরেক্স ও ক্রিপ্টো পেয়ারের লাইভ ক্যান্ডেল ডাটা আনার ফাংশন।
    - EUR/USD -> EURUSD=X
    - GBP/USD -> GBPUSD=X
    - USD/JPY -> JPY=X
    - BTC/USD -> BTC-USD
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        
        if df.empty:
            return None

        # Column নামগুলো lowercase করা হচ্ছে যাতে BpSifat.py-এর সাথে মেলে
        df = df.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })
        
        # সর্বশেষ ৩০টি ক্যান্ডেল ডাটা ফিল্টার করা
        return df[['open', 'high', 'low', 'close', 'volume']].tail(30)
    except Exception as e:
        print(f"Error fetching live data for {symbol}: {e}")
        return None

def signal_worker():
    print("🚀 Quotex Live Signal Engine Started!")
    send_telegram_message("📡 **Quotex Live Market Engine Connected!**\nScanning Forex & Crypto signals...")

    # Quotex-এ সবচেয়ে বেশি চলা কিছু জনপ্রিয় পেয়ারের তালিকা
    ASSETS = {
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "USD/JPY": "JPY=X",
        "BTC/USD": "BTC-USD"
    }

    while True:
        for pair_name, yahoo_symbol in ASSETS.items():
            try:
                # লাইভ মার্কেট ডাটা ফ্যাচ করা (১ মিনিটের ক্যান্ডেল)
                df = fetch_quotex_live_candles(symbol=yahoo_symbol, interval="1m")

                if df is not None and not df.empty:
                    master_bot = QuotexComplete12MasterBot(df)
                    signal = master_bot.execute_all_strategies()

                    if signal and "⏳" not in signal:
                        msg = f"📊 **QUOTEX LIVE SIGNAL** 📊\n\nAsset: {pair_name}\nTimeframe: 1M\nSignal: {signal}"
                        print(f"Signal Found [{pair_name}]: {signal}")
                        send_telegram_message(msg)
                        time.sleep(30) # সিগন্যাল পেলে ৩০ সেকেন্ড পজ

            except Exception as e:
                print(f"Error analyzing {pair_name}: {e}")

            time.sleep(2) # প্রতি পেয়ার চেকে ২ সেকেন্ড গ্যাপ

        time.sleep(5)

if __name__ == "__main__":
    t = threading.Thread(target=signal_worker, daemon=True)
    t.start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
                    
