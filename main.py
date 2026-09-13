import os
import time
import asyncio
import threading
import pandas as pd
import requests
from flask import Flask
from quotexpy import Client

# ==================== IMPORTS FROM YOUR STRATEGY FILES ====================
import Strategy1
import Strategy2
import Strategy3
import Strategy4
import Strategy5
import Strategy6
import Strategy7

# ==================== ENVIRONMENT CONFIGURATION ====================
EMAIL = os.getenv("QUOTEX_EMAIL", "")
PASSWORD = os.getenv("QUOTEX_PASSWORD", "")

LARAVEL_SESSION = os.getenv("LARAVEL_SESSION", "")
CF_CLEARANCE = os.getenv("CF_CLEARANCE", "")
CF_BM = os.getenv("CF_BM", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

PAIRS = ["EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "AUDUSD_otc"]
TIMEFRAME = 60  # 1 Minute Candles

app = Flask(__name__)

@app.route('/')
def home():
    return "Quotex Multi-Strategy Engine Active & Running!"

# ==================== TELEGRAM NOTIFIER ====================
def send_telegram_alert(pair, signal_type, strategy_name, entry_price):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[{strategy_name}] Signal: {signal_type} on {pair} at {entry_price}")
        return
        
    emoji = "🟢 CALL (BUY)" if signal_type in ["CALL", "BUY"] else "🔴 PUT (SELL)"
    message = (
        f"🚨 *QUOTEX LIVE SIGNAL* 🚨\n\n"
        f"📌 *Pair:* `{pair}`\n"
        f"📊 *Signal:* {emoji}\n"
        f"🎯 *Strategy:* `{strategy_name}`\n"
        f"💵 *Entry Price:* `{entry_price}`\n"
        f"⏱ *Timeframe:* M1 (1 Min)\n"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=5)
        print(f"✅ Alert sent for {pair} -> {signal_type} ({strategy_name})")
    except Exception as e:
        print(f"❌ Telegram Alert Error: {e}")

# ==================== EXECUTE ALL 7 CUSTOM STRATEGIES ====================
def run_custom_strategies(df, pair):
    if df is None or len(df) < 10:
        return

    curr_close = df.iloc[-1]['close']

    strategies = [
        ("Strategy 1", Strategy1),
        ("Strategy 2", Strategy2),
        ("Strategy 3", Strategy3),
        ("Strategy 4", Strategy4),
        ("Strategy 5", Strategy5),
        ("Strategy 6", Strategy6),
        ("Strategy 7", Strategy7),
    ]

    for name, module in strategies:
        try:
            signal = None
            for func_name in ['check_strategy1', 'check_strategy2', 'check_strategy3', 'check_strategy4', 'check_strategy5', 'check_strategy6', 'check_strategy7', 'check_signal', 'get_signal', 'analyze', 'run']:
                if hasattr(module, func_name):
                    signal = getattr(module, func_name)(df)
                    break
            
            if signal in ["CALL", "PUT", "BUY", "SELL"]:
                send_telegram_alert(pair, signal, name, curr_close)
        except Exception as e:
            print(f"Error running {name}: {e}")

# ==================== WEBSOCKET ENGINE LOOP ====================
async def run_quotex_engine():
    print("Connecting to Quotex Engine...")
    client = Client(email=EMAIL, password=PASSWORD)

    cookies_str = ""
    if LARAVEL_SESSION:
        cookies_str += f"laravel_session={LARAVEL_SESSION.strip()}; "
    if CF_CLEARANCE:
        cookies_str += f"cf_clearance={CF_CLEARANCE.strip()}; "
    if CF_BM:
        cookies_str += f"__cf_bm={CF_BM.strip()}; "

    if cookies_str:
        client.headers = {
            "Cookie": cookies_str,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        client.ssid = LARAVEL_SESSION.strip()

    check_connect, reason = await client.connect()
    if not check_connect:
        print(f"❌ Connection Failed: {reason}")
        return

    print("🚀 Quotex Connected! Running your 7 strategy files live...")

    while True:
        try:
            for pair in PAIRS:
                candles = await client.get_candles(pair, time.time(), TIMEFRAME, 50)
                if candles:
                    df = pd.DataFrame(candles)
                    run_custom_strategies(df, pair)
            
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Loop Error: {e}")
            await asyncio.sleep(10)

def start_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_quotex_engine())

if __name__ == "__main__":
    threading.Thread(target=start_async_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
