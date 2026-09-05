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
    return "Quotex Live Signal & Win/Loss Tracker Bot is Active!"

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
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        
        if df.empty:
            return None

        df = df.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })
        
        return df[['open', 'high', 'low', 'close', 'volume']].tail(30)
    except Exception as e:
        print(f"Error fetching live data for {symbol}: {e}")
        return None

def track_and_send_result(pair_name, yahoo_symbol, signal_type, entry_price):
    """
    ১ মিনিট পর মার্কেটের লাইভ প্রাইস চেক করে Win/Loss ফলাফল টেলিগ্রামে জানাবে।
    """
    print(f"⏳ Tracking trade for {pair_name}... Entry: {entry_price}")
    
    # ১ মিনিটের ট্রেড শেষ হওয়ার জন্য ৬০ সেকেন্ড অপেক্ষা (ক্যান্ডেল ক্লোজ হওয়া পর্যন্ত)
    time.sleep(60)
    
    df = fetch_quotex_live_candles(symbol=yahoo_symbol, interval="1m")
    if df is None or df.empty:
        send_telegram_message(f"⚠️ Could not track result for **{pair_name}** (Data delay).")
        return

    exit_price = df['close'].iloc[-1]
    
    # Win / Loss লজিক ক্যালকুলেশন
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
        f"📊 **TRADE RESULT [{pair_name}]**\n\n"
        f"📍 Entry Price: `{entry_price:.5f}`\n"
        f"🏁 Exit Price: `{exit_price:.5f}`\n\n"
        f"🏆 Outcome: **{result}**"
    )
    
    send_telegram_message(result_msg)
    print(f"Result Sent: {result} for {pair_name}")

def signal_worker():
    print("🚀 Quotex Live Signal Engine Started!")
    send_telegram_message("📡 **Quotex Live Engine Connected!**\nAuto Win/Loss Tracker Enabled ✅")

    ASSETS = {
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "USD/JPY": "JPY=X",
        "BTC/USD": "BTC-USD"
    }

    while True:
        for pair_name, yahoo_symbol in ASSETS.items():
            try:
                df = fetch_quotex_live_candles(symbol=yahoo_symbol, interval="1m")

                if df is not None and not df.empty:
                    master_bot = QuotexComplete12MasterBot(df)
                    signal = master_bot.execute_all_strategies()

                    if signal and "⏳" not in signal:
                        entry_price = df['close'].iloc[-1]
                        
                        msg = (
                            f"📊 **QUOTEX LIVE SIGNAL** 📊\n\n"
                            f"Asset: **{pair_name}**\n"
                            f"Timeframe: **1M**\n"
                            f"Entry Price: `{entry_price:.5f}`\n"
                            f"Signal: {signal}\n\n"
                            f"⏳ *Tracking result in 1 minute...*"
                        )
                        send_telegram_message(msg)

                        # ফলাফল ট্র্যাকিংয়ের জন্য আলাদা থ্রেড চালানো (যাতে স্ক্যান আটকে না থাকে)
                        tracker_thread = threading.Thread(
                            target=track_and_send_result,
                            args=(pair_name, yahoo_symbol, signal, entry_price)
                        )
                        tracker_thread.start()

                        time.sleep(15) # রিপিটেড সিগন্যাল এড়াতে গ্যাপ

            except Exception as e:
                print(f"Error analyzing {pair_name}: {e}")

            time.sleep(2)

        time.sleep(5)

if __name__ == "__main__":
    t = threading.Thread(target=signal_worker, daemon=True)
    t.start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
