     import os
import asyncio
import threading
from flask import Flask
from telegram import Bot
import pandas as pd
from quotexpy import Quotex
from BpSifat import QuotexComplete12MasterBot

app = Flask(__name__)

@app.route('/')
def home():
    return "Quotex Master Bot is Running!"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID", "YOUR_TELEGRAM_CHAT_ID")
QUOTEX_EMAIL = os.environ.get("QUOTEX_EMAIL", "your_email@example.com")
QUOTEX_PASSWORD = os.environ.get("QUOTEX_PASSWORD", "your_password")

bot = Bot(token=TELEGRAM_TOKEN)

async def start_trading_bot():
    client = Quotex(email=QUOTEX_EMAIL, password=QUOTEX_PASSWORD)
    check_connect, _ = await client.connect()
    asset = "EURUSD_otc"

    while True:
        try:
            if check_connect:
                candles = await client.get_candles(asset, 60)
                df = pd.DataFrame(candles)
                df = df.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'})
                df = df.tail(50)

                master_bot = QuotexComplete12MasterBot(df)
                signal = master_bot.execute_all_strategies()

                if signal and "⏳" not in signal:
                    msg = f"🚨 **QUOTEX LIVE SIGNAL** 🚨\n\nAsset: {asset}\nSignal: {signal}"
                    await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
                    await asyncio.sleep(55)

        except Exception as e:
            print(f"Error: {e}")

        await asyncio.sleep(3)

def run_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_trading_bot())

threading.Thread(target=run_async_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
