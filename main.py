import os
import time
import requests
import ccxt
import pandas as pd
import ta

# Telegram Credentials (From Environment Variables)
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

# Initialize Bybit Futures Client (Bypasses Binance USA IP Block)
exchange = ccxt.bybit({
    'options': {'defaultType': 'future'},
    'enableRateLimit': True
})

def scan_market():
    print("Fetching top 50 USDT Futures pairs from Bybit...")
    try:
        markets = exchange.fetch_markets()
    except Exception as e:
        print(f"Market fetch error: {e}")
        return

    usdt_pairs = [m['symbol'] for m in markets if m['quote'] == 'USDT' and m['active']]
    top_50_pairs = usdt_pairs[:50]

    for symbol in top_50_pairs:
        try:
            # Fetch 15 Minute Candle Data
            bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
            df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            
            # Technical Indicators
            df['rsi'] = ta.momentum.rsi(df['close'], window=14)
            df['ema20'] = ta.trend.ema_indicator(df['close'], window=20)
            
            last_rsi = round(df['rsi'].iloc[-1], 2)
            entry_price = df['close'].iloc[-1]
            last_ema = df['ema20'].iloc[-1]

            # LONG (UP) SIGNAL LOGIC
            if last_rsi < 30 and entry_price > last_ema:
                tp = round(entry_price * 1.015, 4)  # 1.5% Target Profit
                sl = round(entry_price * 0.99, 4)    # 1.0% Stop Loss

                msg = (
                    f"🟢 **SIGNAL: LONG (UP)** | `{symbol}`\n\n"
                    f"🔹 **Entry Price:** `{entry_price}`\n"
                    f"🎯 **Target (TP 1.5%):** `{tp}`\n"
                    f"🛑 **Stop Loss (SL 1.0%):** `{sl}`\n"
                    f"📊 **RSI:** `{last_rsi}`\n\n"
                    f"⚡ *Action: Order Market/Limit Long*"
                )
                print(f"Signal Found: {symbol} LONG")
                send_telegram_msg(msg)
                
            # SHORT (DOWN) SIGNAL LOGIC
            elif last_rsi > 70 and entry_price < last_ema:
                tp = round(entry_price * 0.985, 4)  # 1.5% Target Profit
                sl = round(entry_price * 1.01, 4)   # 1.0% Stop Loss

                msg = (
                    f"🔴 **SIGNAL: SHORT (DOWN)** | `{symbol}`\n\n"
                    f"🔹 **Entry Price:** `{entry_price}`\n"
                    f"🎯 **Target (TP 1.5%):** `{tp}`\n"
                    f"🛑 **Stop Loss (SL 1.0%):** `{sl}`\n"
                    f"📊 **RSI:** `{last_rsi}`\n\n"
                    f"⚡ *Action: Order Market/Limit Short*"
                )
                print(f"Signal Found: {symbol} SHORT")
                send_telegram_msg(msg)

        except Exception as e:
            continue

# Continuous 24/7 Loop for Render Background Worker
if __name__ == "__main__":
    send_telegram_msg("🤖 **Trading Bot Started Successfully on Render!**")
    while True:
        try:
            scan_market()
        except Exception as e:
            print(f"Loop Error: {e}")
        
        # Wait 60 seconds before scanning top 50 coins again
        time.sleep(60)
        
