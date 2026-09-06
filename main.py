import os
import requests
import ccxt
import pandas as pd
import ta

# Telegram Credentials (Get from Telegram BotFather)
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

# Initialize Binance Futures Client via CCXT
exchange = ccxt.binance({
    'options': {'defaultType': 'future'},
    'enableRateLimit': True
})

def scan_market():
    print("Fetching top 50 USDT Futures pairs...")
    markets = exchange.fetch_markets()
    
    # Filter top 50 USDT Pairs
    usdt_pairs = [m['symbol'] for m in markets if m['quote'] == 'USDT' and m['active']]
    top_50_pairs = usdt_pairs[:50]
    
    signals = []

    for symbol in top_50_pairs:
        try:
            # Fetch last 100 candles (15-minute timeframe)
            bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
            df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            
            # Calculate Indicators (RSI & EMA)
            df['rsi'] = ta.momentum.rsi(df['close'], window=14)
            df['ema20'] = ta.trend.ema_indicator(df['close'], window=20)
            
            last_rsi = round(df['rsi'].iloc[-1], 2)
            last_close = df['close'].iloc[-1]
            last_ema = df['ema20'].iloc[-1]
            volume_spike = df['volume'].iloc[-1] > (df['volume'].mean() * 2)

            # Signal Logic
            if last_rsi < 30 and last_close > last_ema:
                msg = f"🟢 **BULLISH SIGNAL**: `{symbol}`\nPrice: {last_close}\nRSI: {last_rsi} (Oversold Bounce)"
                signals.append(msg)
                
            elif last_rsi > 70 and last_close < last_ema:
                msg = f"🔴 **BEARISH SIGNAL**: `{symbol}`\nPrice: {last_close}\nRSI: {last_rsi} (Overbought Drop)"
                signals.append(msg)

        except Exception as e:
            continue

    if signals:
        full_report = "🚀 **Binance 50 Coin Scanner Report** 🚀\n\n" + "\n\n".join(signals)
        print(full_report)
        send_telegram_msg(full_report)
    else:
        print("No strong signals found right now.")

if __name__ == "__main__":
    scan_market()
    
