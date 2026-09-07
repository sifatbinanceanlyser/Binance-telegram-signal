import os
import time
import threading
import requests
import ccxt
import pandas as pd
import ta
from flask import Flask

# --- Telegram API Settings ---
TELEGRAM_BOT_TOKEN = "8447772474:AAF_CwpS1e3clYMEkuN0VZ6UTFqzTsnK2KE"
TELEGRAM_CHAT_ID = "6885238220"

# --- Binance API Keys (আপনার আসল API ও Secret Key নিচে বসান) ---
BINANCE_API_KEY = "XURB6t8yOozDmM2YrRU6bZTjWl5X1ZuXCrNyDqE0otOszZ5oAupPZ16i3LCHVGgZ"
BINANCE_SECRET_KEY = "••••••••••••••••••••••••••••••••"

active_trades = {}

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload, timeout=10)
        print(f"--> Telegram Status: {res.status_code}")
    except Exception as e:
        print(f"--> Telegram Error: {e}")

# --- Keep-Alive Web Server for Render ---
app = Flask('')

@app.route('/')
def home():
    return "Binance 5-Minute High/Low Signal Engine Running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- Real-Time Analysis & Tracking Engine ---
def fetch_and_analyze():
    # Binance API এর মাধ্যমে ডাটা নেওয়া
    exchange = ccxt.binance({
        'apiKey': BINANCE_API_KEY,
        'secret': BINANCE_SECRET_KEY,
        'enableRateLimit': True
    })
    
    try:
        markets = exchange.load_markets()
        # ৫০টি শীর্ষ USDT ফিউচার্স পেয়ার স্ক্যান করবে
        symbols = [s for s in markets if s.endswith('/USDT') and markets[s].get('swap', False)][:50]
        
        for symbol in symbols:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Technical Indicators Setup
            df['rsi'] = ta.momentum.rsi(df['close'], window=14)
            df['ema20'] = ta.trend.ema_indicator(df['close'], window=20)
            df['ema50'] = ta.trend.ema_indicator(df['close'], window=50)
            
            last_close = df['close'].iloc[-1]
            last_rsi = df['rsi'].iloc[-1]
            last_ema20 = df['ema20'].iloc[-1]
            last_ema50 = df['ema50'].iloc[-1]
            
            # --- UP SIGNAL (CALL) ---
            if last_rsi < 45 and last_ema20 > last_ema50:
                if symbol not in active_trades:
                    entry_time = time.time()
                    active_trades[symbol] = {
                        'direction': 'UP',
                        'entry_price': last_close,
                        'expire_time': entry_time + 300 # ৩০০ সেকেন্ড = ৫ মিনিট
                    }
                    
                    msg = (f"🟢 *5-MIN HIGH/LOW SIGNAL (UP)*\n\n"
                           f"🪙 *Asset:* `{symbol}`\n"
                           f"📈 *Direction:* `UP (Opor/CALL)`\n"
                           f"⏱️ *Timeframe:* `5 Minutes`\n"
                           f"💵 *Entry Price:* `{last_close:.4f}`\n"
                           f"📊 *RSI:* `{last_rsi:.2f}`\n\n"
                           f"⚡ *Action:* Set 5m timer and trade UP now!")
                    send_telegram_msg(msg)

            # --- DOWN SIGNAL (PUT) ---
            elif last_rsi > 55 and last_ema20 < last_ema50:
                if symbol not in active_trades:
                    entry_time = time.time()
                    active_trades[symbol] = {
                        'direction': 'DOWN',
                        'entry_price': last_close,
                        'expire_time': entry_time + 300 # ৩০০ সেকেন্ড = ৫ মিনিট
                    }
                    
                    msg = (f"🔴 *5-MIN HIGH/LOW SIGNAL (DOWN)*\n\n"
                           f"🪙 *Asset:* `{symbol}`\n"
                           f"📉 *Direction:* `DOWN (Niche/PUT)`\n"
                           f"⏱️ *Timeframe:* `5 Minutes`\n"
                           f"💵 *Entry Price:* `{last_close:.4f}`\n"
                           f"📊 *RSI:* `{last_rsi:.2f}`\n\n"
                           f"⚡ *Action:* Set 5m timer and trade DOWN now!")
                    send_telegram_msg(msg)

            # --- 5-MINUTE AUTOMATED RESULT TRACKER ---
            current_time = time.time()
            if symbol in active_trades:
                trade = active_trades[symbol]
                
                # ৫ মিনিট পার হলে ফলাফল চেক করবে
                if current_time >= trade['expire_time']:
                    entry = trade['entry_price']
                    
                    if trade['direction'] == 'UP':
                        if last_close > entry:
                            send_telegram_msg(f"✅ *WIN!* 🎉\n\n🪙 Asset: `{symbol}`\n📈 Direction: `UP`\n💵 Entry: `{entry:.4f}`\n🏁 Exit: `{last_close:.4f}`\n📊 Status: *Price went UP after 5 minutes!*")
                        else:
                            send_telegram_msg(f"❌ *LOSS!* ⚠️\n\n🪙 Asset: `{symbol}`\n📈 Direction: `UP`\n💵 Entry: `{entry:.4f}`\n🏁 Exit: `{last_close:.4f}`\n📊 Status: *Price failed to stay UP.*")
                    
                    elif trade['direction'] == 'DOWN':
                        if last_close < entry:
                            send_telegram_msg(f"✅ *WIN!* 🎉\n\n🪙 Asset: `{symbol}`\n📉 Direction: `DOWN`\n💵 Entry: `{entry:.4f}`\n🏁 Exit: `{last_close:.4f}`\n📊 Status: *Price went DOWN after 5 minutes!*")
                        else:
                            send_telegram_msg(f"❌ *LOSS!* ⚠️\n\n🪙 Asset: `{symbol}`\n📉 Direction: `DOWN`\n💵 Entry: `{entry:.4f}`\n🏁 Exit: `{last_close:.4f}`\n📊 Status: *Price failed to stay DOWN.*")
                    
                    # ট্রেড হিসাব শেষ, লিস্ট থেকে মুছে ফেলা হলো
                    del active_trades[symbol]
                        
    except Exception as e:
        print(f"Fetch/Analysis Error: {e}")

# --- Scanning Loop ---
def scanner_loop():
    time.sleep(3)
    send_telegram_msg("🚀 *Binance API Connected & 5m Scanner Started!*")
    while True:
        print("--> Scanning 50 Binance pairs for 5m signals...")
        fetch_and_analyze()
        time.sleep(30) # প্রতি ৩০ সেকেন্ডে নতুন ক্যান্ডেল ডাটা আপডেট করবে

if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    scanner_loop()
    
