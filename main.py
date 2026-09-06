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
    return "Bot is active & scanning every 5 minutes!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- Binance Market Scanner & Technical Analysis ---
def fetch_and_analyze():
    exchange = ccxt.binance({'enableRateLimit': True})
    try:
        markets = exchange.load_markets()
        # ২০টি কয়েনের জায়গায় ৫০টি কয়েন স্ক্যান করার জন্য ফিল্টার অপটিমাইজ করা হলো
        symbols = [s for s in markets if s.endswith('/USDT') and markets[s].get('swap', False)][:50]
        
        for symbol in symbols:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            df['rsi'] = ta.momentum.rsi(df['close'], window=14)
            df['ema20'] = ta.trend.ema_indicator(df['close'], window=20)
            df['ema50'] = ta.trend.ema_indicator(df['close'], window=50)
            
            last_close = df['close'].iloc[-1]
            last_rsi = df['rsi'].iloc[-1]
            last_ema20 = df['ema20'].iloc[-1]
            last_ema50 = df['ema50'].iloc[-1]
            prev_ema20 = df['ema20'].iloc[-2]
            prev_ema50 = df['ema50'].iloc[-2]
            
            # Long Signal (RSI Oversold + Bullish Crossover)
            if last_rsi < 35 and prev_ema20 <= prev_ema50 and last_ema20 > last_ema50:
                if symbol not in active_trades:
                    tp = last_close * 1.015
                    sl = last_close * 0.99
                    active_trades[symbol] = {'side': 'LONG', 'tp': tp, 'sl': sl}
                    msg = f"🟢 *LONG SIGNAL*\n\nPair: `{symbol}`\nEntry: `{last_close:.4f}`\nTP: `{tp:.4f}`\nSL: `{sl:.4f}`"
                    send_telegram_msg(msg)
                    
            # Short Signal (RSI Overbought + Bearish Crossover)
            elif last_rsi > 65 and prev_ema20 >= prev_ema50 and last_ema20 < last_ema50:
                if symbol not in active_trades:
                    tp = last_close * 0.985
                    sl = last_close * 1.01
                    active_trades[symbol] = {'side': 'SHORT', 'tp': tp, 'sl': sl}
                    msg = f"🔴 *SHORT SIGNAL*\n\nPair: `{symbol}`\nEntry: `{last_close:.4f}`\nTP: `{tp:.4f}`\nSL: `{sl:.4f}`"
                    send_telegram_msg(msg)
                    
            # Track Active Trades (Win / Loss)
            if symbol in active_trades:
                trade = active_trades[symbol]
                if trade['side'] == 'LONG':
                    if last_close >= trade['tp']:
                        send_telegram_msg(f"✅ *TP HIT (WIN)*: `{symbol}`")
                        del active_trades[symbol]
                    elif last_close <= trade['sl']:
                        send_telegram_msg(f"❌ *SL HIT (LOSS)*: `{symbol}`")
                        del active_trades[symbol]
                elif trade['side'] == 'SHORT':
                    if last_close <= trade['tp']:
                        send_telegram_msg(f"✅ *TP HIT (WIN)*: `{symbol}`")
                        del active_trades[symbol]
                    elif last_close >= trade['sl']:
                        send_telegram_msg(f"❌ *SL HIT (LOSS)*: `{symbol}`")
                        del active_trades[symbol]
                        
    except Exception as e:
        print(f"Analysis Error: {e}")

# --- Main Automation Loop ---
def scanner_loop():
    time.sleep(3)
    send_telegram_msg("🚀 *5-Minute Binance Trading Scanner & Auto-Tracker Online!*")
    while True:
        print("--> Scanning Binance 5m Market...")
        fetch_and_analyze()
        time.sleep(300)

if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    scanner_loop()
            
