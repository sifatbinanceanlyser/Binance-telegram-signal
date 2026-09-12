import os
import time
import asyncio
import threading
import pandas as pd
import requests
from flask import Flask
from quotexpy import Quotex

# ==================== CONFIGURATION ====================
# Secrets / Environment Variables
EMAIL = os.getenv("QUOTEX_EMAIL", "your_email@gmail.com")
PASSWORD = os.getenv("QUOTEX_PASSWORD", "your_password")

# কুকি ভ্যালুগুলো Secrets থেকে নিয়ে আসবে
LARAVEL_SESSION = os.getenv("LARAVEL_SESSION", "")
CF_CLEARANCE = os.getenv("CF_CLEARANCE", "")
CF_BM = os.getenv("CF_BM", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

PAIRS = ["EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "AUDUSD_otc"]
TIMEFRAME = 60  # 1 Minute Candles (M1)

# Keep-Alive Server for Render Deployment
app = Flask(__name__)

@app.route('/')
def home():
    return "Quotex Live Data Analysis & Telegram Bot Running!"

# ==================== TELEGRAM SIGNAL SENDER ====================
def send_telegram_alert(pair, signal_type, strategy_name, entry_price):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[{strategy_name}] {signal_type} Signal for {pair} at {entry_price} (Telegram credentials missing)")
        return
        
    emoji = "🟢 CALL (BUY)" if signal_type == "CALL" else "🔴 PUT (SELL)"
    message = (
        f"🚨 *QUOTEX LIVE ANALYSIS SIGNAL* 🚨\n\n"
        f"📌 *Pair:* `{pair}`\n"
        f"📊 *Signal:* {emoji}\n"
        f"🎯 *Strategy:* `{strategy_name}`\n"
        f"💵 *Entry Price:* `{entry_price}`\n"
        f"⏱ *Timeframe:* M1 (1 Min)\n"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"})
        print(f"✅ Telegram signal sent: {pair} - {signal_type}")
    except Exception as e:
        print(f"❌ Telegram Alert Error: {e}")

# ==================== ANALYSIS & ENGINE ====================
def process_live_analysis(candles, pair):
    df = pd.DataFrame(candles)
    if len(df) < 10:
        return

    # ক্যান্ডেল ডাটা ফ্রেম
    last_candle = df.iloc[-1]
    prev_candle = df.iloc[-2]
    
    close_p = last_candle['close']
    open_p = last_candle['open']
    high_p = last_candle['high']
    low_p = last_candle['low']

    # আপনার ৭টি স্ট্র্যাটেজির রুলস এখানে যুক্ত হবে
    # Example Condition:
    if close_p > prev_candle['high']:
        send_telegram_alert(pair, "CALL", "Breakout Strategy", close_p)
    elif close_p < prev_candle['low']:
        send_telegram_alert(pair, "PUT", "Breakdown Strategy", close_p)

# ==================== QUOTEX WEBSOCKET ENGINE ====================
async def run_quotex_engine():
    print("Connecting to Quotex WebSocket...")
    
    client = Quotex(email=EMAIL, password=PASSWORD)

    # স্ক্রিনশটের ৩টি সেশন কুকি ইন্টিগ্রেশন
    cookies_str = ""
    if LARAVEL_SESSION:
        cookies_str += f"laravel_session={LARAVEL_SESSION}; "
    if CF_CLEARANCE:
        cookies_str += f"cf_clearance={CF_CLEARANCE}; "
    if CF_BM:
        cookies_str += f"__cf_bm={CF_BM}; "

    if cookies_str:
        # Client Headers বা Session Cookie-তে ইনজেক্ট করা
        client.headers = {
            "Cookie": cookies_str,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        client.ssid = LARAVEL_SESSION

    check_connect, reason = await client.connect()
    if not check_connect:
        print(f"❌ Connection Failed: {reason}")
        return

    print("🚀 Quotex Live Data Stream Active! Reading Candlesticks...")

    while True:
        try:
            for pair in PAIRS:
                candles = await client.get_candles(pair, time.time(), TIMEFRAME, 50)
                if candles:
                    process_live_analysis(candles, pair)
            
            await asyncio.sleep(60)  # প্রতি ১ মিনিট পর পর ক্যান্ডেল স্ক্যান করবে
        except Exception as e:
            print(f"Error in Live Stream Loop: {e}")
            await asyncio.sleep(10)

def start_async_loop():
    asyncio.run(run_quotex_engine())

# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    # Background Thread-এ Quotex Live Engine চালানো
    threading.Thread(target=start_async_loop, daemon=True).start()
    
    # Render Platform-এর জন্য Flask Web Port
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
