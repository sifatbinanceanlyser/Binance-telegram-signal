import os
import time
import random
import threading
import requests
import pandas as pd
from flask import Flask
from BpSifat import QuotexComplete12MasterBot

app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Test Signal Bot is Active!"

# Render Environment Variables থেকে ডাটা নেবে
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram_message(text):
    """মেসেজ পাঠানোর সবচেয়ে সহজ ও নিশ্চিত উপায়"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ TELEGRAM_TOKEN or CHAT_ID missing!")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload)
        print("Telegram Response:", res.json())
    except Exception as e:
        print(f"Failed to send message: {e}")

def generate_dummy_candle_data():
    open_p = 100.0
    candles = []
    for _ in range(30):
        close_p = open_p + random.uniform(-1.5, 1.5)
        high_p = max(open_p, close_p) + random.uniform(0.1, 0.5)
        low_p = min(open_p, close_p) - random.uniform(0.1, 0.5)
        volume = random.randint(1000, 3000)
        
        candles.append({
            'open': open_p,
            'high': high_p,
            'low': low_p,
            'close': close_p,
            'volume': volume
        })
        open_p = close_p
    return pd.DataFrame(candles)

def signal_worker():
    print("🚀 Signal Engine Worker Started Successfully!")
    
    # ব্যাকগ্রাউন্ড লুপ চালু হওয়ার সাথে সাথে টেস্ট মেসেজ পাঠাবে
    send_telegram_message("🤖 **Bot Engine Started & Connected!**\nScanning for signals...")

    while True:
        try:
            df = generate_dummy_candle_data()
            master_bot = QuotexComplete12MasterBot(df)
            signal = master_bot.execute_all_strategies()

            if signal and "⏳" not in signal:
                msg = f"🧪 **TEST SIGNAL DETECTED** 🧪\n\nAsset: EUR/USD (Simulation)\nSignal: {signal}"
                print(f"Sending Signal: {signal}")
                send_telegram_message(msg)
                time.sleep(60) # সিগন্যাল দিলে ১ মিনিট থামবে

        except Exception as e:
            print(f"Error in Loop: {e}")

        time.sleep(5) # প্রতি ৫ সেকেন্ড পর চেক করবে

if __name__ == "__main__":
    # ব্যাকগ্রাউন্ডে ডাইরেক্ট থ্রেড রান
    t = threading.Thread(target=signal_worker, daemon=True)
    t.start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
