import os
import time
import threading
import requests
import pandas as pd
from flask import Flask
from BpSifat import QuotexComplete12MasterBot

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

@app.route('/')
def home():
    return "Binance Live Signal & Win/Loss Tracker Engine Active!"

def send_telegram_message(text):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send message: {e}")

def fetch_binance_live_candles(symbol="BTCUSDT", interval="1m", limit=30):
    """Binance API থেকে রিয়েল-টাইম ক্যান্ডেল ডাটা নিয়ে আসা (কোনো API Key ছাড়াই কাজ করবে)"""
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if isinstance(data, dict) and "code" in data:
            print(f"Binance API Error [{symbol}]: {data.get('msg')}")
            return None

        candles = []
        for c in data:
            candles.append({
                'open': float(c[1]),
                'high': float(c[2]),
                'low': float(c[3]),
                'close': float(c[4]),
                'volume': float(c[5])
            })
        return pd.DataFrame(candles)
    except Exception as e:
        print(f"Error fetching Binance data for {symbol}: {e}")
        return None

def track_and_send_result(pair_name, binance_symbol, signal_type, entry_price):
    """১ মিনিট অপেক্ষা করে Binance প্রাইস চেক করে Win/Loss রেজাল্ট পাঠানো"""
    print(f"⏳ Tracking trade for {pair_name}... Entry: {entry_price}")
    
    # ১ মিনিটের ক্যান্ডেল ক্লোজ হওয়া পর্যন্ত ৬০ সেকেন্ড অপেক্ষা
    time.sleep(60)
    
    df = fetch_binance_live_candles(symbol=binance_symbol, interval="1m")
    if df is None or df.empty:
        send_telegram_message(f"⚠️ Could not track result for **{pair_name}**.")
        return

    exit_price = df['close'].iloc[-1]
    
    # Win / Loss ক্যালকুলেশন
    result = "DRAW 🟡"
    signal_upper = signal_type.upper()
    
    if "CALL" in signal_upper or "BUY" in signal_upper or "UP" in signal_upper:
        if exit_price > entry_price:
            result = "WIN ✅"
        elif exit_price < entry_price:
            result = "LOSS ❌"
    elif "PUT" in signal_upper or "SELL" in signal_upper or "DOWN" in signal_upper:
        if exit_price < entry_price:
            result = "WIN ✅"
        elif exit_price > entry_price:
            result = "LOSS ❌"

    result_msg = (
        f"📊 **BINANCE TRADE RESULT [{pair_name}]**\n\n"
        f"📍 Entry Price: `{entry_price:.2f}`\n"
        f"🏁 Exit Price: `{exit_price:.2f}`\n\n"
        f"🏆 Outcome: **{result}**"
    )
    
    send_telegram_message(result_msg)

def signal_worker():
    print("🚀 Binance Live Signal Engine Started!")
    send_telegram_message("📡 **Binance Engine Connected!**\nReal-Time Crypto Signals Active ✅")

    # Binance-এর ক্রিপ্টো পেয়ার তালিকা
    PAIRS = {
        "BTC/USDT": "BTCUSDT",
        "ETH/USDT": "ETHUSDT",
        "SOL/USDT": "SOLUSDT"
    }
    
    last_signal_time = {}

    while True:
        current_time = time.time()

        for pair_name, binance_symbol in PAIRS.items():
            # একই পেয়ারে বারবার সিগন্যাল যাওয়া বন্ধ করতে ২ মিনিটের কুলডাউন
            if pair_name in last_signal_time and (current_time - last_signal_time[pair_name]) < 120:
                continue

            try:
                df = fetch_binance_live_candles(symbol=binance_symbol, interval="1m")

                if df is not None and not df.empty:
                    master_bot = QuotexComplete12MasterBot(df)
                    signal = master_bot.execute_all_strategies()

                    if signal and "⏳" not in signal:
                        entry_price = df['close'].iloc[-1]
                        last_signal_time[pair_name] = current_time

                        msg = (
                            f"📊 **BINANCE LIVE SIGNAL** 📊\n\n"
                            f"Asset: **{pair_name}**\n"
                            f"Timeframe: **1M**\n"
                            f"Entry Price: `{entry_price:.2f}`\n"
                            f"Signal: {signal}\n\n"
                            f"⏳ *Tracking result in 1 minute...*"
                        )
                        send_telegram_message(msg)

                        # থ্রেডের মাধ্যমে ব্যাকগ্রাউন্ডে রেজাল্ট ট্র্যাক করা
                        tracker_thread = threading.Thread(
                            target=track_and_send_result,
                            args=(pair_name, binance_symbol, signal, entry_price)
                        )
                        tracker_thread.start()

            except Exception as e:
                print(f"Error analyzing {pair_name}: {e}")

            time.sleep(2)

        time.sleep(5)

if __name__ == "__main__":
    t = threading.Thread(target=signal_worker, daemon=True)
    t.start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
                
