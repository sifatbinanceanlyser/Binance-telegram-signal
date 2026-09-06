import os
import time
import threading
import requests
import ccxt
import pandas as pd
import ta
from flask import Flask

# --- Telegram Credentials ---
TELEGRAM_BOT_TOKEN = "8447772474:AAF_CwpS1e3clYMEkuN0VZ6UTFqzTsnK2KE"
TELEGRAM_CHAT_ID = "6885238220"

active_trades = {}

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload, timeout=10)
        print(f"--> Telegram Status: {res.status_code} | Response: {res.text}")
    except Exception as e:
        print(f"--> Telegram Error: {e}")

# --- Keep-Alive Web Server ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is active & scanning real-time Binance 5m data!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- Real-Time Binance Advanced Analysis Engine ---
def fetch_and_analyze():
    # সরাসরি Binance API থেকে লাইভ ডেটা কানেক্ট করা হচ্ছে
    exchange = ccxt.binance({'enableRateLimit': True})
    try:
        markets = exchange.load_markets()
        # শুধু টপ ৫০টি এক্টিভ ও হাই-ভলিউম USDT পেয়ার স্ক্যান করবে
        symbols = [s for s in markets if s.endswith('/USDT') and markets[s].get('swap', False)][:50]
        
        for symbol in symbols:
            # ৫ মিনিটের লাইভ ১০০টি ক্যান্ডেল ডেটা
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # ইন্ডিকেটর হিসাব
            df['rsi'] = ta.momentum.rsi(df['close'], window=14)
            df['ema20'] = ta.trend.ema_indicator(df['close'], window=20)
            df['ema50'] = ta.trend.ema_indicator(df['close'], window=50)
            df['vol_sma'] = df['volume'].rolling(window=20).mean()
            
            last_close = df['close'].iloc[-1]
            last_rsi = df['rsi'].iloc[-1]
            last_vol = df['volume'].iloc[-1]
            avg_vol = df['vol_sma'].iloc[-1]
            
            last_ema20 = df['ema20'].iloc[-1]
            last_ema50 = df['ema50'].iloc[-1]
            prev_ema20 = df['ema20'].iloc[-2]
            prev_ema50 = df['ema50'].iloc[-2]
            
            # হাই ভলিউম কনফার্মেশন (ভলিউম গড়াভলিউমের চেয়ে বেশি হতে হবে)
            high_volume = last_vol > (avg_vol * 1.1)
            
            # --- LONG SIGNAL CONDITION ---
            # RSI oversold/moderate (RSI < 42), Bullish Cross & High Volume
            if last_rsi < 42 and prev_ema20 <= prev_ema50 and last_ema20 > last_ema50 and high_volume:
                if symbol not in active_trades:
                    tp = last_close * 1.015 # 1.5% Take Profit
                    sl = last_close * 0.990 # 1.0% Stop Loss
                    active_trades[symbol] = {'side': 'LONG', 'tp': tp, 'sl': sl}
                    
                    msg = (f"🎯 *PRO REAL-TIME LONG SIGNAL*\n\n"
                           f"🪙 *Pair:* `{symbol}`\n"
                           f"💵 *Entry Price:* `{last_close:.4f}`\n"
                           f"📊 *RSI:* `{last_rsi:.2f}`\n"
                           f"🎯 *Target (TP):* `{tp:.4f}` (+1.5%)\n"
                           f"🛑 *Stop Loss (SL):* `{sl:.4f}` (-1.0%)\n"
                           f"⚡ *Timeframe:* `5m Binance Futures`")
                    send_telegram_msg(msg)
                    
            # --- SHORT SIGNAL CONDITION ---
            # RSI overbought/moderate (RSI > 58), Bearish Cross & High Volume
            elif last_rsi > 58 and prev_ema20 >= prev_ema50 and last_ema20 < last_ema50 and high_volume:
                if symbol not in active_trades:
                    tp = last_close * 0.985 # 1.5% Take Profit
                    sl = last_close * 1.010 # 1.0% Stop Loss
                    active_trades[symbol] = {'side': 'SHORT', 'tp': tp, 'sl': sl}
                    
                    msg = (f"🎯 *PRO REAL-TIME SHORT SIGNAL*\n\n"
                           f"🪙 *Pair:* `{symbol}`\n"
                           f"💵 *Entry Price:* `{last_close:.4f}`\n"
                           f"📊 *RSI:* `{last_rsi:.2f}`\n"
                           f"🎯 *Target (TP):* `{tp:.4f}` (+1.5%)\n"
                           f"🛑 *Stop Loss (SL):* `{sl:.4f}` (-1.0%)\n"
                           f"⚡ *Timeframe:* `5m Binance Futures`")
                    send_telegram_msg(msg)
                    
            # --- REAL-TIME WIN / LOSS TRACKER ---
            if symbol in active_trades:
                trade = active_trades[symbol]
                if trade['side'] == 'LONG':
                    if last_close >= trade['tp']:
                        send_telegram_msg(f"✅ *WIN / TP HIT!* 🎉\n\nPair: `{symbol}`\nExit Price: `{last_close:.4f}`")
                        del active_trades[symbol]
                    elif last_close <= trade['sl']:
                        send_telegram_msg(f"❌ *LOSS / SL HIT!* ⚠️\n\nPair: `{symbol}`\nExit Price: `{last_close:.4f}`")
                        del active_trades[symbol]
                elif trade['side'] == 'SHORT':
                    if last_close <= trade['tp']:
                        send_telegram_msg(f"✅ *WIN / TP HIT!* 🎉\n\nPair: `{symbol}`\nExit Price: `{last_close:.4f}`")
                        del active_trades[symbol]
                    elif last_close >= trade['sl']:
                        send_telegram_msg(f"❌ *LOSS / SL HIT!* ⚠️\n\nPair: `{symbol}`\nExit Price: `{last_close:.4f}`")
                        del active_trades[symbol]
                        
    except Exception as e:
        print(f"Analysis Error: {e}")

# --- Main Automation Loop ---
def scanner_loop():
    time.sleep(3)
    send_telegram_msg("🚀 *Binance Real-Time Pro Signal Scanner Online!*")
    while True:
        print("--> Scanning Binance 5m Live Data...")
        fetch_and_analyze()
        time.sleep(300)

if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    scanner_loop()
                            
