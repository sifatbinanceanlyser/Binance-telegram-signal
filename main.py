import os
import time
import threading
import requests
import pandas as pd
from flask import Flask
from BpSifat import QuotexComplete12MasterBot

app = Flask(__name__)

# Environment Variables থেকে ক্রেডেনশিয়াল নেওয়া
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TWELVE_DATA_API_KEY = os.environ.get("TWELVE_DATA_API_KEY")

@app.route('/')
def home():
    return "Quotex Live Signal & Win/Loss Tracker Engine Active!"

def send_telegram_message(text):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send message: {e}")

def fetch_quotex_live_candles(symbol="EUR/USD", interval="1min"):
    """Twelve Data API থেকে সরাসরি লাইভ ক্যান্ডেল ডাটা ফেচ করা"""
    if not TWELVE_DATA_API_KEY:
        print("Error: TWELVE_DATA_API_KEY Environment Variable missing!")
        return None

    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize=30&apikey={TWELVE_DATA_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if "values" not in data:
            print(f"API Error [{symbol}]: {data.get('message', 'Unknown error')}")
            return None

        candles = []
        for c in reversed(data["values"]):
            candles.append({
                'open': float(c['open']),
                'high': float(c['high']),
                'low': float(c['low']),
                'close': float(c['close']),
                'volume': float(c.get('volume', 0))
            })
        return pd.DataFrame(candles)
    except Exception as e:
        print(f"Error fetching live data for {symbol}: {e}")
        return None

def track_and_send_result(pair_name, signal_type, entry_price):
    """১ মিনিট অপেক্ষা করে ক্যান্ডেল ক্লোজ হওয়ার পর সঠিক Exit Price দিয়ে Win/Loss ক্যালকুলেট করা"""
    print(f"⏳ Tracking trade for {pair_name}... Entry: {entry_price}")
    
    # ১ মিনিটের ট্রেড ডিউরেশনের জন্য ৬০ সেকেন্ড বিরতি
    time.sleep(60)
    
    df = fetch_quotex_live_candles(symbol=pair_name, interval="1min")
    if df is None or df.empty:
        send_telegram_message(f"⚠️ Result tracking failed for **{pair_name}** (API Timeout).")
        return

    exit_price = df['close'].iloc[-1]

    # Win / Loss ক্যালকুলেশন
    result = "DRAW 🟡"
    if "CALL" in signal_type or "BUY" in signal_type or "UP" in signal_type:
        if exit_price > entry_price:
            result = "WIN ✅"
        elif exit_price < entry_price:
            result = "LOSS ❌"
    elif "PUT" in signal_type or "SELL" in signal_type or "DOWN" in signal_type:
        if exit_price < entry_price:
            result = "WIN ✅"
        elif exit_price > entry_price:
            result = "LOSS ❌"

    result_msg = (
        f"📊 **QUOTEX TRADE RESULT [{pair_name}]**\n\n"
        f"📍 Entry Price: `{entry_price:.5f}`\n"
        f"🏁 Exit Price: `{exit_price:.5f}`\n\n"
        f"🏆 Outcome: **{result}**"
    )
    
    send_telegram_message(result_msg)

def signal_worker():
    print("🚀 Quotex Real-Time Signal Engine Started!")
    send_telegram_message("📡 **Quotex Live Engine Connected!**\nTwelve Data Live Market & Auto Win/Loss Active ✅")

    # ১২ ডাটার সঠিক ফরেক্স পেয়ার সিম্বলসমূহ
    PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"]
    last_signal_time = {}

    while True:
        current_time = time.time()

        for pair in PAIRS:
            # একই পেয়ারে ২ মিনিটের আগে বারবার সিগন্যাল যাওয়া রদ করার ফিল্টার
            if pair in last_signal_time and (current_time - last_signal_time[pair]) < 120:
                continue

            try:
                df = fetch_quotex_live_candles(symbol=pair, interval="1min")

                if df is not None and not df.empty:
                    master_bot = QuotexComplete12MasterBot(df)
                    signal = master_bot.execute_all_strategies()

                    if signal and "⏳" not in signal:
                        entry_price = df['close'].iloc[-1]
                        last_signal_time[pair] = current_time

                        msg = (
                            f"📊 **QUOTEX LIVE SIGNAL** 📊\n\n"
                            f"Asset: **{pair}**\n"
                            f"Timeframe: **1M**\n"
                            f"Entry Price: `{entry_price:.5f}`\n"
                            f"Signal: {signal}\n\n"
                            f"⏳ *Tracking result in 1 minute...*"
                        )
                        send_telegram_message(msg)

                        # ব্যাকগ্রাউন্ডে রেজাল্ট ট্র্যাকার চালনা
                        tracker_thread = threading.Thread(
                            target=track_and_send_result,
                            args=(pair, signal, entry_price)
                        )
                        tracker_thread.start()

            except Exception as e:
                print(f"Error analyzing {pair}: {e}")

            time.sleep(8) # Twelve Data API Rate Limit (8 requests/min) বজায় রাখতে ডিলে

        time.sleep(10)

if __name__ == "__main__":
    t = threading.Thread(target=signal_worker, daemon=True)
    t.start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
