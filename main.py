import sys
sys.path.append('.')

import os
import time
import requests
import pandas as pd
from quotexapi.stable_api import Quotex


# ==========================================
# ১. স্ট্র্যাটেজি ফাইলগুলো ইমপোর্ট করা
# ==========================================
import Strategy1
import Strategy2
import Strategy3
import Strategy4
import Strategy5
import Strategy6
import Strategy7

ALL_STRATEGIES = [
    Strategy1, Strategy2, Strategy3, Strategy4,
    Strategy5, Strategy6, Strategy7
]

# ==========================================
# ২. কনফিগারেশন (SSID এবং টেলিগ্রাম টোকেন)
# ==========================================
QUOTEX_SSID = "eyJpd2lsIilJBYXJ6WDINb1p6L00ycTZ3cjgxS0E9PSIsInZhHVlljoiQ05mRE56TUl1aHVCN05yYm9VdXB1ck5xM2QvbHZOVDFDZkUvZTdyak1UZmNHVXpHYUhjWjdQnFWMm15iajlzRTIxWkdYb3JzS0ZTY2RwdjBVM2VVTJBFNGp4WGtucFBZMm1xcmTRncjNHM0IrajMwVIV3eXBzTWIFVS9BWUtNOHYiLCJtYWMiOiI4NjkwMDA3Yjc0ZjNiNTc3NjNmMJWJNjMwMzJjZTE2ZWxwZWU4MmVINzA3M2M2Y2YTI3OGY0ZjkzNGQ4ZTtk5liwidGfNljoiln0%3D"

TELEGRAM_BOT_TOKEN = "8447772474:AAF_CwpS1e3clYMEkuN0VZ6UTFqzTsnK2KE"
TELEGRAM_CHAT_ID = "6885238220"

ASSET = "EURUSD_fut"  # ট্রেড করার কারেন্সি পেয়ার
TIMEFRAME = 60         # ১ মিনিটের ক্যান্ডেল

# ==========================================
# ৩. টেলিগ্রাম সিগন্যাল ফাংশন
# ==========================================
def send_telegram_signal(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

# ==========================================
# ৪. সব স্ট্র্যাটেজি রান করার লজিক
# ==========================================
def run_all_strategies(df):
    for st in ALL_STRATEGIES:
        for func_name in ['detect_double_hammer_sell_signal', 'detect_signal']:
            if hasattr(st, func_name):
                func = getattr(st, func_name)
                try:
                    res_df = func(df)
                    if res_df is not None and 'Signal' in res_df.columns:
                        signal = res_df['Signal'].iloc[-1]
                        if signal != 'HOLD':
                            return signal, st.__name__
                except Exception as e:
                    print(f"Error in {st.__name__}: {e}")
    return None, None

# ==========================================
# ৫. কোটেক্স লাইভ কানেকশন ও লুপ
# ==========================================
client = Quotex(ssid=QUOTEX_SSID)
check_connect, reason = client.connect()

if not check_connect:
    print(f"Quotex connection failed: {reason}")
    exit()

print("Quotex-এর সাথে লাইভ কানেকশন সফল হয়েছে!")

last_candle_time = 0

while True:
    try:
        # লাইভ ক্যান্ডেল ডেটা নেওয়া
        candles = client.get_candles(ASSET, TIMEFRAME, 10, time.time())
        
        if candles:
            df = pd.DataFrame(candles)
            df.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'time': 'Time'
            }, inplace=True)

            current_candle_time = df['Time'].iloc[-1]

            # নতুন ক্যান্ডেল ক্লোজ হলে এনালাইসিস করবে
            if current_candle_time != last_candle_time:
                last_candle_time = current_candle_time
                
                # সিগন্যাল এনালাইসিস (আপনার ৭টি স্ট্র্যাটেজি দিয়ে)
                signal, strategy_name = run_all_strategies(df)

                if signal:
                    msg = (
                        f"🚨 *QUOTEX LIVE SIGNAL* 🚨\n\n"
                        f"📊 *Asset:* {ASSET}\n"
                        f"🎯 *Signal:* {signal}\n"
                        f"🛠️ *Strategy:* {strategy_name}\n"
                        f"⏰ *Timeframe:* 1 Min"
                    )
                    send_telegram_signal(msg)
                    print(f"New Signal: {signal} from {strategy_name}")

        time.sleep(5)

    except Exception as e:
        print(f"Loop Error: {e}")
        time.sleep(5)
        
