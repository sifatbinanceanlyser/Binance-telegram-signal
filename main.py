import os
import time
import threading
import requests
import ccxt
import pandas as pd
from flask import Flask

# ⚠️ এনভায়রনমেন্ট ভেরিয়েবল থেকে কী নেওয়ার পরামর্শ দেওয়া হচ্ছে
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8447772474:AAF_CwpS1e3clYMEkuN0VZ6UTFqzTsnK2KE")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "6885238220")

BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "2GXZWhFhTrNvjClGETU8NJaBaFOs5gaj8m7JyElxJwLFSE1faMUym08EjYxDdjtu")
BINANCE_SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY", "XLJc1cH8TIkjlpx8Nh9Jfa9yjfIG0Pl59GQvBqXGnRPPrIs0vcfMtziOkVRcZOyV")

active_trades = {}

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

app = Flask('')

@app.route('/')
def home():
    return "SMC & Order Block Signal Engine Active!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def fetch_and_analyze():
    exchange = ccxt.binance({
        'apiKey': BINANCE_API_KEY,
        'secret': BINANCE_SECRET_KEY,
        'enableRateLimit': True
    })
    
    try:
        markets = exchange.load_markets()
        symbols = [s for s in markets if s.endswith('/USDT') and markets[s].get('swap', False)][:50]
        
        for symbol in symbols:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=50)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # --- SMC & ORDER BLOCK STRATEGY CALCULATIONS ---
            df['prev_high'] = df['high'].shift(1)
            df['prev_low'] = df['low'].shift(1)

            # 1. Liquidity Sweep Detection
            df['bullish_sweep'] = df['low'] < df['prev_low']  # Low sweep for BUY
            df['bearish_sweep'] = df['high'] > df['prev_high'] # High sweep for SELL

            # 2. Fair Value Gap (FVG) / Price Imbalance
            # Bullish FVG: 1st Candle High < 3rd Candle Low
            df['bullish_fvg'] = (df['high'].shift(2) < df['low']) & (df['close'].shift(1) > df['open'].shift(1))
            # Bearish FVG: 1st Candle Low > 3rd Candle High
            df['bearish_fvg'] = (df['low'].shift(2) > df['high']) & (df['close'].shift(1) < df['open'].shift(1))

            last_close = df['close'].iloc[-1]
            last_low = df['low'].iloc[-1]
            last_high = df['high'].iloc[-1]
            
            # Condition check for SMC Valid Setup
            is_bullish_ob = df['bullish_sweep'].iloc[-3] and df['bullish_fvg'].iloc[-1] and (df['close'].iloc[-1] > df['high'].iloc[-2])
            is_bearish_ob = df['bearish_sweep'].iloc[-3] and df['bearish_fvg'].iloc[-1] and (df['close'].iloc[-1] < df['low'].iloc[-2])

            # --- BULLISH ORDER BLOCK SIGNAL (CALL/UP) ---
            if is_bullish_ob:
                if symbol not in active_trades:
                    entry_time = time.time()
                    stop_loss = df['low'].iloc[-3]
                    active_trades[symbol] = {
                        'direction': 'UP',
                        'entry_price': last_close,
                        'expire_time': entry_time + 300
                    }
                    
                    msg = (f"🟢 *SMC ORDER BLOCK SIGNAL (BUY/UP)*\n\n"
                           f"🪙 *Asset:* `{symbol}`\n"
                           f"📈 *Direction:* `UP (Call)`\n"
                           f"⏱️ *Timeframe:* `5 Minutes`\n"
                           f"💵 *Entry Price:* `{last_close:.4f}`\n"
                           f"🛑 *Invalidation (SL):* `{stop_loss:.4f}`\n"
                           f"⚡ *Reason:* Liquidity Sweep + FVG Identified!\n\n"
                           f"👉 *Action:* Place UP trade now!")
                    send_telegram_msg(msg)

            # --- BEARISH ORDER BLOCK SIGNAL (PUT/DOWN) ---
            elif is_bearish_ob:
                if symbol not in active_trades:
                    entry_time = time.time()
                    stop_loss = df['high'].iloc[-3]
                    active_trades[symbol] = {
                        'direction': 'DOWN',
                        'entry_price': last_close,
                        'expire_time': entry_time + 300
                    }
                    
                    msg = (f"🔴 *SMC ORDER BLOCK SIGNAL (SELL/DOWN)*\n\n"
                           f"🪙 *Asset:* `{symbol}`\n"
                           f"📉 *Direction:* `DOWN (Put)`\n"
                           f"⏱️ *Timeframe:* `5 Minutes`\n"
                           f"💵 *Entry Price:* `{last_close:.4f}`\n"
                           f"🛑 *Invalidation (SL):* `{stop_loss:.4f}`\n"
                           f"⚡ *Reason:* Liquidity Sweep + FVG Identified!\n\n"
                           f"👉 *Action:* Place DOWN trade now!")
                    send_telegram_msg(msg)

            # --- RESULT TRACKER (WIN/LOSS CHECK) ---
            current_time = time.time()
            if symbol in active_trades:
                trade = active_trades[symbol]
                if current_time >= trade['expire_time']:
                    entry = trade['entry_price']
                    if trade['direction'] == 'UP':
                        if last_close > entry:
                            send_telegram_msg(f"✅ *WIN!* 🎉\n\n🪙 `{symbol}`\n📈 Direction: `UP`\n💵 Entry: `{entry:.4f}` | Exit: `{last_close:.4f}`")
                        else:
                            send_telegram_msg(f"❌ *LOSS!* ⚠️\n\n🪙 `{symbol}`\n📈 Direction: `UP`\n💵 Entry: `{entry:.4f}` | Exit: `{last_close:.4f}`")
                    elif trade['direction'] == 'DOWN':
                        if last_close < entry:
                            send_telegram_msg(f"✅ *WIN!* 🎉\n\n🪙 `{symbol}`\n📉 Direction: `DOWN`\n💵 Entry: `{entry:.4f}` | Exit: `{last_close:.4f}`")
                        else:
                            send_telegram_msg(f"❌ *LOSS!* ⚠️\n\n🪙 `{symbol}`\n📉 Direction: `DOWN`\n💵 Entry: `{entry:.4f}` | Exit: `{last_close:.4f}`")
                    
                    del active_trades[symbol]
                        
    except Exception as e:
        print(f"Error: {e}")

def scanner_loop():
    time.sleep(3)
    send_telegram_msg("⚡ *SMC & Order Block Engine Scanner Activated!*")
    while True:
        fetch_and_analyze()
        time.sleep(15)

if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    scanner_loop()
        
