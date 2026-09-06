# --- Telegram Credentials (সরাসরি বসিয়ে দিন) ---
TELEGRAM_BOT_TOKEN = "8837833880:AAG7S5tpFiQ2WBwFZRBT5oZFlrQ9HI_yzrQ"
TELEGRAM_CHAT_ID = "6885238220"

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload)
        print(f"Telegram Response: {res.text}")
    except Exception as e:
        print(f"Telegram error: {e}")
        import os
import time
import threading
import requests
import ccxt
import pandas as pd
import ta
from flask import Flask

# --- Render Keep-Alive Flask Server ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is active & scanning every 5 minutes!"

def run_web():
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web, daemon=True).start()

# --- Credentials ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")

def send_telegram_msg(message):
    if TELEGRAM_BOT_TOKEN != "YOUR_BOT_TOKEN_HERE":
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload)
        except Exception as e:
            print(f"Telegram error: {e}")

# Initialize Exchange (Bybit Client used to bypass Binance Cloud IP Restrictions)
exchange = ccxt.bybit({
    'options': {'defaultType': 'future'},
    'enableRateLimit': True
})

# Active Trade Storage for Win/Loss Tracking
active_trades = {}

def scan_market():
    print("Scanning top pairs (5m timeframe)...")
    try:
        markets = exchange.fetch_markets()
        usdt_pairs = [m['symbol'] for m in markets if m['quote'] == 'USDT' and m['active']][:50]
    except Exception as e:
        print(f"Fetch markets error: {e}")
        return

    for symbol in usdt_pairs:
        try:
            bars = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=100)
            df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])

            # Technical Indicators
            df['rsi'] = ta.momentum.rsi(df['close'], window=14)
            df['ema20'] = ta.trend.ema_indicator(df['close'], window=20)
            df['ema50'] = ta.trend.ema_indicator(df['close'], window=50)

            last_rsi = round(df['rsi'].iloc[-1], 2)
            entry_price = df['close'].iloc[-1]
            last_ema20 = df['ema20'].iloc[-1]
            last_ema50 = df['ema50'].iloc[-1]

            # Already active trade skip
            if symbol in active_trades:
                continue

            # HIGH ACCURACY ACCORDING TO TREND (5m Logic)
            # LONG Signal: RSI < 35 & Price > EMA20 & EMA20 > EMA50
            if last_rsi < 35 and entry_price > last_ema20 and last_ema20 > last_ema50:
                tp = round(entry_price * 1.012, 4)  # 1.2% TP
                sl = round(entry_price * 0.992, 4)   # 0.8% SL

                active_trades[symbol] = {'type': 'LONG', 'entry': entry_price, 'tp': tp, 'sl': sl}

                msg = (
                    f"🟢 **SIGNAL: LONG (UP)** | `{symbol}`\n\n"
                    f"🔹 **Entry:** `{entry_price}`\n"
                    f"🎯 **Target (TP 1.2%):** `{tp}`\n"
                    f"🛑 **Stop Loss (SL 0.8%):** `{sl}`\n"
                    f"📊 **RSI:** `{last_rsi}`\n\n"
                    f"⏳ *Status: Pending Trade Tracking...*"
                )
                send_telegram_msg(msg)

            # SHORT Signal: RSI > 65 & Price < EMA20 & EMA20 < EMA50
            elif last_rsi > 65 and entry_price < last_ema20 and last_ema20 < last_ema50:
                tp = round(entry_price * 0.988, 4)  # 1.2% TP
                sl = round(entry_price * 1.008, 4)   # 0.8% SL

                active_trades[symbol] = {'type': 'SHORT', 'entry': entry_price, 'tp': tp, 'sl': sl}

                msg = (
                    f"🔴 **SIGNAL: SHORT (DOWN)** | `{symbol}`\n\n"
                    f"🔹 **Entry:** `{entry_price}`\n"
                    f"🎯 **Target (TP 1.2%):** `{tp}`\n"
                    f"🛑 **Stop Loss (SL 0.8%):** `{sl}`\n"
                    f"📊 **RSI:** `{last_rsi}`\n\n"
                    f"⏳ *Status: Pending Trade Tracking...*"
                )
                send_telegram_msg(msg)

        except Exception:
            continue

def track_trades():
    """Real-time Win/Loss Tracker"""
    for symbol in list(active_trades.keys()):
        try:
            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            trade = active_trades[symbol]

            if trade['type'] == 'LONG':
                if current_price >= trade['tp']:
                    send_telegram_msg(f"🟢 **WIN ALERT!** | `{symbol}`\n\nTarget Profit (TP) `{trade['tp']}` Hit Successfully! 🎯")
                    del active_trades[symbol]
                elif current_price <= trade['sl']:
                    send_telegram_msg(f"🔴 **LOSS ALERT!** | `{symbol}`\n\nStop Loss (SL) `{trade['sl']}` Hit. 🛑")
                    del active_trades[symbol]

            elif trade['type'] == 'SHORT':
                if current_price <= trade['tp']:
                    send_telegram_msg(f"🟢 **WIN ALERT!** | `{symbol}`\n\nTarget Profit (TP) `{trade['tp']}` Hit Successfully! 🎯")
                    del active_trades[symbol]
                elif current_price >= trade['sl']:
                    send_telegram_msg(f"🔴 **LOSS ALERT!** | `{symbol}`\n\nStop Loss (SL) `{trade['sl']}` Hit. 🛑")
                    del active_trades[symbol]

        except Exception as e:
            print(f"Tracking error for {symbol}: {e}")

if __name__ == "__main__":
    send_telegram_msg("🚀 **5-Minute Advanced Trading & Auto-Tracker Bot Online!**")
    
    last_scan_time = 0
    while True:
        # Every 5 minutes (300 seconds) Market Scan
        if time.time() - last_scan_time >= 300:
            scan_market()
            last_scan_time = time.time()

        # Track active trades continuous every minute
        track_trades()
        time.sleep(30)
        
