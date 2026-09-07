import os
import time
import threading
import requests
import ccxt
import pandas as pd
import ta
from flask import Flask

TELEGRAM_BOT_TOKEN = "8447772474:AAF_CwpS1e3clYMEkuN0VZ6UTFqzTsnK2KE"
TELEGRAM_CHAT_ID = "6885238220"

BINANCE_API_KEY = "2GXZWhFhTrNvjClGETU8NJaBaFOs5gaj8m7JyElxJwLFSE1faMUym08EjYxDdjtu"
BINANCE_SECRET_KEY = "XLJc1cH8TIkjlpx8Nh9Jfa9yjfIG0Pl59GQvBqXGnRPPrIs0vcfMtziOkVRcZOyV"

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
    return "Fast Scan Signal Engine Active!"

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
            
            df['rsi'] = ta.momentum.rsi(df['close'], window=14)
            df['ema9'] = ta.trend.ema_indicator(df['close'], window=9)
            df['ema21'] = ta.trend.ema_indicator(df['close'], window=21)
            
            last_close = df['close'].iloc[-1]
            last_rsi = df['rsi'].iloc[-1]
            last_ema9 = df['ema9'].iloc[-1]
            last_ema21 = df['ema21'].iloc[-1]
            prev_ema9 = df['ema9'].iloc[-2]
            prev_ema21 = df['ema21'].iloc[-2]
            
            # --- UP SIGNAL (Quick Trigger) ---
            if (prev_ema9 <= prev_ema21 and last_ema9 > last_ema21) or (last_rsi < 48 and last_close > last_ema9):
                if symbol not in active_trades:
                    entry_time = time.time()
                    active_trades[symbol] = {
                        'direction': 'UP',
                        'entry_price': last_close,
                        'expire_time': entry_time + 300
                    }
                    
                    msg = (f"🟢 *5-MIN HIGH/LOW SIGNAL (UP)*\n\n"
                           f"🪙 *Asset:* `{symbol}`\n"
                           f"📈 *Direction:* `UP (Call)`\n"
                           f"⏱️ *Timeframe:* `5 Minutes`\n"
                           f"💵 *Entry:* `{last_close:.4f}`\n\n"
                           f"⚡ *Action:* Place UP trade on Quotex now!")
                    send_telegram_msg(msg)

            # --- DOWN SIGNAL (Quick Trigger) ---
            elif (prev_ema9 >= prev_ema21 and last_ema9 < last_ema21) or (last_rsi > 52 and last_close < last_ema9):
                if symbol not in active_trades:
                    entry_time = time.time()
                    active_trades[symbol] = {
                        'direction': 'DOWN',
                        'entry_price': last_close,
                        'expire_time': entry_time + 300
                    }
                    
                    msg = (f"🔴 *5-MIN HIGH/LOW SIGNAL (DOWN)*\n\n"
                           f"🪙 *Asset:* `{symbol}`\n"
                           f"📉 *Direction:* `DOWN (Put)`\n"
                           f"⏱️ *Timeframe:* `5 Minutes`\n"
                           f"💵 *Entry:* `{last_close:.4f}`\n\n"
                           f"⚡ *Action:* Place DOWN trade on Quotex now!")
                    send_telegram_msg(msg)

            # --- RESULT TRACKER ---
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
    send_telegram_msg("⚡ *Fast Signal Scanner Activated!*")
    while True:
        fetch_and_analyze()
        time.sleep(15)

if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    scanner_loop()
            
