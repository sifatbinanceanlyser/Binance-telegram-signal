import os
import requests
import ccxt
import pandas as pd
import ta

# Telegram Credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")

def send_telegram_msg(message):
    if TELEGRAM_BOT_TOKEN != "YOUR_BOT_TOKEN_HERE":
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload)
        except Exception as e:
            print(f"Telegram alert error: {e}")

# Initialize Binance Futures Client
exchange = ccxt.binance({
    'options': {'defaultType': 'future'},
    'enableRateLimit': True
})

def scan_market():
    print("Fetching top 50 USDT Futures pairs...")
    markets = exchange.fetch_markets()
    usdt_pairs = [m['symbol'] for m in markets if m['quote'] == 'USDT' and m['active']]
    top_50_pairs = usdt_pairs[:50]

    for symbol in top_50_pairs:
        try:
            # 15 Minute timeframe data
            bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
            df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            
            df['rsi'] = ta.momentum.rsi(df['close'], window=14)
            df['ema20'] = ta.trend.ema_indicator(df['close'], window=20)
            
            last_rsi = round(df['rsi'].iloc[-1], 2)
            entry_price = df['close'].iloc[-1]
            last_ema = df['ema20'].iloc[-1]
            
            # Previous candle for tracking outcome
            prev_high = df['high'].iloc[-1]
            prev_low = df['low'].iloc[-1]

            # LONG (UP) SIGNAL
            if last_rsi < 30 and entry_price > last_ema:
                tp = round(entry_price * 1.015, 4)  # 1.5% Target Profit
                sl = round(entry_price * 0.99, 4)    # 1.0% Stop Loss
                
                # Simple tracking logic based on candle move
                status = "🟢 WIN" if prev_high >= tp else ("🔴 LOSS" if prev_low <= sl else "⏳ PENDING")

                msg = (
                    f"🟢 **SIGNAL: LONG (UP)** | `{symbol}`\n\n"
                    f"🔹 **Entry Price:** `{entry_price}`\n"
                    f"🎯 **Target (TP):** `{tp}`\n"
                    f"🛑 **Stop Loss (SL):** `{sl}`\n"
                    f"📊 **RSI:** `{last_rsi}`\n\n"
                    f"🏆 **Status:** {status}"
                )
                send_telegram_msg(msg)
                
            # SHORT (DOWN) SIGNAL
            elif last_rsi > 70 and entry_price < last_ema:
                tp = round(entry_price * 0.985, 4) # 1.5% Target Profit
                sl = round(entry_price * 1.01, 4)   # 1.0% Stop Loss
                
                status = "🟢 WIN" if prev_low <= tp else ("🔴 LOSS" if prev_high >= sl else "⏳ PENDING")

                msg = (
                    f"🔴 **SIGNAL: SHORT (DOWN)** | `{symbol}`\n\n"
                    f"🔹 **Entry Price:** `{entry_price}`\n"
                    f"🎯 **Target (TP):** `{tp}`\n"
                    f"🛑 **Stop Loss (SL):** `{sl}`\n"
                    f"📊 **RSI:** `{last_rsi}`\n\n"
                    f"🏆 **Status:** {status}"
                )
                send_telegram_msg(msg)

        except Exception as e:
            continue

if __name__ == "__main__":
    scan_market()
                
