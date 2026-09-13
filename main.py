import os
import time
import asyncio
import threading
import pandas as pd
import requests
from flask import Flask
from quotexpy import Quotex

# ==================== IMPORTS FROM YOUR STRATEGY FILES ====================
try:
    from Strategy1 import check_strategy1
    from Strategy2 import check_strategy2
    from Strategy3 import check_strategy3
    from Strategy4 import check_strategy4
    from Strategy5 import check_strategy5
    from Strategy6 import check_strategy6
    from Strategy7 import check_strategy7
except ImportError as e:
    print(f"Strategy import warning: {e}")

# ==================== CONFIGURATION ====================
EMAIL = os.getenv("QUOTEX_EMAIL", "sifat07071234@gmail.com")
PASSWORD = os.getenv("QUOTEX_PASSWORD", "Ammu0707")

LARAVEL_SESSION = os.getenv("eyJpd2liImpYZ1I1ZU1NEdUSwVG8rTlVPSndRc0E9PSIsInZhbHVlIjoiNzA2MTM1MW0bEt02knqSFRWVS9fDE2oWdUK1AzK1J2dVpRa10bG5kRFdWM3THICWiZaWmEvbzZrbEJSbEdFYjJQdk15MW1YaiS5TTc3bngwK3GDmN0eXRqNm5QMnI0NDocDNrLUwwTFNFVhVmdDdlQ2pOSEkN2VXT2kLCXYWMGlJkMDYwMzM5N2Y21NGVZTXYjgMYW4MJSmtkZmRIZDMxYWZmZDk4MTc5ZW05ZTM4MzM2ZTAwOSJd
", "")
CF_CLEARANCE = os.getenv("IoHT.NfbnqOPX.w_N1.WL2bduS5kJ5EZJoGT5qyFeY-1789240098-1.2.1.1-yVVBBl3EYZRZzHbqbvwwLFGHy0TAk6217DgLRSxvUyw9F1nyX2GrVBEbTwTIZPtTcj_35_Ui7nnJsHuU1CMVTK0IAKAF28RanpkaBte_w4PuUt7cViAbrfwwtv8W0Tx6u7vQFr1kThaMZ1xSVSlthEpkFdub7dYA.afXtLxnhJNIBi30dLExjvQRmudGyBAFsE8l0WC8CD.SxFjy4IG535bxMz0uwY.uEpI0073D_fzha4_JluuJP2momMQs.beNgRMSpmlHALvqycMtcRDDPhes.NIVSLW.tdBFCJdCwqxG9v6NTpFNbQAEPpR25BAQd80PIMKWS3vCyF2wqlw38r8ktAXE14qGIj0hU
", "")
CF_BM = os.getenv("qJEZM7RBJc0Rs07fC1miDFfHdf9hX3FQAXIckM_8xk-1789240098.9263377-1.0.1.1-Gz8t7fpB0qVtEm4GPOzpZUIFVe0M5qAO1ujCt2d7DK2_RNXM9gw4SiSkrB4xxn7aWiAelRO3sBdaUgzRuTkGjPe4CEMKPq0xJRoBglVpTkXiNox5GdwdlkIXNDF6C
", "")

TELEGRAM_BOT_TOKEN = os.getenv("8447772474:AAF_CwpS1e3clYMEkuN0VZ6UTFqzTsnK2KE", "")
TELEGRAM_CHAT_ID = os.getenv("6885238220", "")

PAIRS = ["EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "AUDUSD_otc"]
TIMEFRAME = 60  # 1 Minute Candles

app = Flask(__name__)

@app.route('/')
def home():
    return "Quotex Multi-Strategy Custom Engine Active!"

# ==================== TELEGRAM NOTIFIER ====================
def send_telegram_alert(pair, signal_type, strategy_name, entry_price):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[{strategy_name}] Signal: {signal_type} on {pair} at {entry_price}")
        return
        
    emoji = "🟢 CALL (BUY)" if signal_type == "CALL" else "🔴 PUT (SELL)"
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
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"})
        print(f"✅ Alert sent for {pair} -> {signal_type}")
    except Exception as e:
        print(f"❌ Telegram Alert Error: {e}")

# ==================== EXECUTE ALL 7 CUSTOM STRATEGIES ====================
def run_custom_strategies(df, pair):
    if len(df) < 10:
        return

    curr_close = df.iloc[-1]['close']

    # আপনার ৭টি স্ট্র্যাটেজি ফাইল থেকে অ্যানালাইসিস কল করবে
    strategies = [
        ("Strategy 1", check_strategy1 if 'check_strategy1' in globals() else None),
        ("Strategy 2", check_strategy2 if 'check_strategy2' in globals() else None),
        ("Strategy 3", check_strategy3 if 'check_strategy3' in globals() else None),
        ("Strategy 4", check_strategy4 if 'check_strategy4' in globals() else None),
        ("Strategy 5", check_strategy5 if 'check_strategy5' in globals() else None),
        ("Strategy 6", check_strategy6 if 'check_strategy6' in globals() else None),
        ("Strategy 7", check_strategy7 if 'check_strategy7' in globals() else None),
    ]

    for name, func in strategies:
        if func:
            try:
                # যদি স্ট্র্যাটেজি ফাংশন CALL অথবা PUT রিটার্ন করে
                signal = func(df)
                if signal in ["CALL", "PUT"]:
                    send_telegram_alert(pair, signal, name, curr_close)
            except Exception as e:
                print(f"Error running {name}: {e}")

# ==================== WEBSOCKET ENGINE LOOP ====================
async def run_quotex_engine():
    print("Connecting to Quotex Engine...")
    client = Quotex(email=EMAIL, password=PASSWORD)

    cookies_str = ""
    if LARAVEL_SESSION:
        cookies_str += f"laravel_session={LARAVEL_SESSION}; "
    if CF_CLEARANCE:
        cookies_str += f"cf_clearance={CF_CLEARANCE}; "
    if CF_BM:
        cookies_str += f"__cf_bm={CF_BM}; "

    if cookies_str:
        client.headers = {
            "Cookie": cookies_str,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        client.ssid = LARAVEL_SESSION

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
    asyncio.run(run_quotex_engine())

if __name__ == "__main__":
    threading.Thread(target=start_async_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
