import os
import asyncio
import threading
import random
import pandas as pd
from flask import Flask
from telegram import Bot
from BpSifat import QuotexComplete12MasterBot

# Flask App (Render-এ পিং পাওয়ার জন্য)
app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Test Signal Bot is Active!"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID", "YOUR_TELEGRAM_CHAT_ID")

bot = Bot(token=TELEGRAM_TOKEN)

def generate_dummy_candle_data():
    """টেস্টিংয়ের জন্য র্যান্ডম ক্যান্ডেল ডাটা জেনারেট করা"""
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

async def start_telegram_signal_loop():
    print("Telegram Signal Engine Started...")
    
    while True:
        try:
            # ১. টেস্ট ডাটা জেনারেট করা
            df = generate_dummy_candle_data()

            # ২. BpSifat.py-এর ১২টি স্ট্র্যাটেজি রান করা
            master_bot = QuotexComplete12MasterBot(df)
            signal = master_bot.execute_all_strategies()

            # ৩. সিগন্যাল তৈরি হলে টেলিগ্রামে মেসেজ পাঠানো
            if signal and "⏳" not in signal:
                msg = f"🧪 **TEST SIGNAL DETECTED** 🧪\n\nAsset: EUR/USD (Simulation)\nSignal: {signal}"
                await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
                print(f"Sent Signal to Telegram: {signal}")
                
                # সিগন্যাল পাঠালে ১ মিনিট অপেক্ষা করবে
                await asyncio.sleep(60)

        except Exception as e:
            print(f"Error in Loop: {e}")

        # প্রতি ৫ সেকেন্ড পর পর নতুন ডাটা চেক করবে
        await asyncio.sleep(5)

def run_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_telegram_signal_loop())

# ব্যাকগ্রাউন্ড থ্রেডে ট্রেডিং লুপ রান করা
threading.Thread(target=run_async_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
