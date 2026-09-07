import os
import time
import threading
import requests
import pandas as pd
from flask import Flask

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8447772474:AAF_CwpS1e3clYMEkuN0VZ6UTFqzTsnK2KE")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "6885238220")

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
    return "SMC + Multi-Pattern 1-Min Signal Engine Active!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def get_binance_ohlcv(symbol, interval='1m', limit=35):
    formatted_symbol = symbol.replace('/', '')
    url = f"https://api.binance.com/api/v3/klines?symbol={formatted_symbol}&interval={interval}&limit={limit}"
    
    response = requests.get(url, timeout=10)
    data = response.json()
    
    if isinstance(data, list):
        parsed_data = []
        for item in data:
            parsed_data.append([
                item[0],                  # Open time
                float(item[1]),           # Open
                float(item[2]),           # High
                float(item[3]),           # Low
                float(item[4]),           # Close
                float(item[5])            # Volume
            ])
        return parsed_data
    else:
        raise Exception(f"API Error: {data}")

def fetch_and_analyze():
    symbols = [
        'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
        'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'DOT/USDT',
        'MATIC/USDT', 'LTC/USDT', 'TRX/USDT', 'NEAR/USDT', 'APT/USDT',
        'SHIB/USDT', 'ATOM/USDT', 'BCH/USDT', 'UNI/USDT', 'FIL/USDT',
        'INJ/USDT', 'OP/USDT', 'ARB/USDT', 'SUI/USDT', 'TIA/USDT',
        'SEI/USDT', 'FET/USDT', 'RNDR/USDT', 'GALA/USDT', 'PEPE/USDT',
        'SAND/USDT', 'MANA/USDT', 'FTM/USDT', 'ALGO/USDT', 'EGLD/USDT',
        'AAVE/USDT', 'THETA/USDT', 'AXS/USDT', 'EOS/USDT', 'KAVA/USDT'
    ]
    
    for symbol in symbols:
        try:
            ohlcv = get_binance_ohlcv(symbol, interval='1m', limit=35)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            last_close = df['close'].iloc[-1]
            last_open = df['open'].iloc[-1]
            last_high = df['high'].iloc[-1]
            last_low = df['low'].iloc[-1]

            # --- 1. SMC CALCULATIONS ---
            df['prev_high'] = df['high'].shift(1)
            df['prev_low'] = df['low'].shift(1)
            df['bullish_sweep'] = df['low'] < df['prev_low']  
            df['bearish_sweep'] = df['high'] > df['prev_high']
            df['bullish_fvg'] = df['low'] > df['high'].shift(2)
            df['bearish_fvg'] = df['high'] < df['low'].shift(2)

            is_smc_bullish = (df['bullish_sweep'].iloc[-2] or df['bullish_sweep'].iloc[-1]) and \
                             (df['bullish_fvg'].iloc[-1] or (last_close > df['high'].iloc[-2])) and \
                             (last_close > last_open)

            is_smc_bearish = (df['bearish_sweep'].iloc[-2] or df['bearish_sweep'].iloc[-1]) and \
                             (df['bearish_fvg'].iloc[-1] or (last_close < df['low'].iloc[-2])) and \
                             (last_close < last_open)

            # --- 2. SHOT PATTERN (IMAGE 1 & 2) ---
            resistance_level = df['high'].iloc[-10:-1].max()
            support_level = df['low'].iloc[-10:-1].min()

            is_shot_bullish = (last_close > resistance_level) and (last_close > last_open)
            is_shot_bearish = (last_close < support_level) and (last_close < last_open)

            # --- 3. TREND CONTINUATION & REJECTION (IMAGE 3) ---
            # Checks for 4+ consecutive red candles, then 1-2 green, then rejection
            red_count = (df['close'].iloc[-7:-3] < df['open'].iloc[-7:-3]).sum()
            is_rejection_bearish = (red_count >= 3) and \
                                   (df['close'].iloc[-3] > df['open'].iloc[-3]) and \
                                   (last_close < last_open) and \
                                   (last_close <= support_level)

            # --- SIGNAL SELECTION ---
            signal_type = None
            reason = ""

            if is_smc_bullish or is_shot_bullish:
                signal_type = "UP"
                reason = "SMC Imbalance / Breakout Setup"
            elif is_smc_bearish:
                signal_type = "DOWN"
                reason = "SMC Bearish Order Block"
            elif is_shot_bearish:
                signal_type = "DOWN"
                reason = "Shot Pattern Support Breakout"
            elif is_rejection_bearish:
                signal_type = "DOWN"
                reason = "Trend Continuation Rejection Setup"

            # Execute Signals (1-Minute Expiration)
            if signal_type == 'UP' and symbol not in active_trades:
                entry_time = time.time()
                active_trades[symbol] = {
                    'direction': 'UP',
                    'entry_price': last_close,
                    'expire_time': entry_time + 60
                }
                
                msg = (f"🟢 *1-MIN BUY/UP SIGNAL*\n\n"
                       f"🪙 *Asset:* `{symbol}`\n"
                       f"📈 *Direction:* `UP (Call)`\n"
                       f"⏱️ *Timeframe:* `1 Minute`\n"
                       f"💵 *Entry Price:* `{last_close:.4f}`\n"
                       f"⚡ *Reason:* {reason}!\n\n"
                       f"👉 *Action:* Place 1-Min UP trade on Quotex now!")
                send_telegram_msg(msg)

            elif signal_type == 'DOWN' and symbol not in active_trades:
                entry_time = time.time()
                active_trades[symbol] = {
                    'direction': 'DOWN',
                    'entry_price': last_close,
                    'expire_time': entry_time + 60
                }
                
                msg = (f"🔴 *1-MIN SELL/DOWN SIGNAL*\n\n"
                       f"🪙 *Asset:* `{symbol}`\n"
                       f"📉 *Direction:* `DOWN (Put)`\n"
                       f"⏱️ *Timeframe:* `1 Minute`\n"
                       f"💵 *Entry Price:* `{last_close:.4f}`\n"
                       f"⚡ *Reason:* {reason}!\n\n"
                       f"👉 *Action:* Place 1-Min DOWN trade on Quotex now!")
                send_telegram_msg(msg)

            # --- RESULT TRACKER ---
            current_time = time.time()
            if symbol in active_trades:
                trade = active_trades[symbol]
                if current_time >= trade['expire_time']:
                    entry = trade['entry_price']
                    if trade['direction'] == 'UP':
                        if last_close > entry:
                            send_telegram_msg(f"✅ *WIN!* 🎉 (1-Min)\n\n🪙 `{symbol}`\n📈 Direction: `UP`\n💵 Entry: `{entry:.4f}` | Exit: `{last_close:.4f}`")
                        else:
                            send_telegram_msg(f"❌ *LOSS!* ⚠️ (1-Min)\n\n🪙 `{symbol}`\n📈 Direction: `UP`\n💵 Entry: `{entry:.4f}` | Exit: `{last_close:.4f}`")
                    elif trade['direction'] == 'DOWN':
                        if last_close < entry:
                            send_telegram_msg(f"✅ *WIN!* 🎉 (1-Min)\n\n🪙 `{symbol}`\n📉 Direction: `DOWN`\n💵 Entry: `{entry:.4f}` | Exit: `{last_close:.4f}`")
                        else:
                            send_telegram_msg(f"❌ *LOSS!* ⚠️ (1-Min)\n\n🪙 `{symbol}`\n📉 Direction: `DOWN`\n💵 Entry: `{entry:.4f}` | Exit: `{last_close:.4f}`")
                    
                    del active_trades[symbol]
            
            time.sleep(0.05)
                        
        except Exception as e:
            print(f"Error on {symbol}: {e}")

def scanner_loop():
    time.sleep(3)
    send_telegram_msg("⚡ *High-Speed SMC + Multi-Pattern Scanner Activated!*")
    while True:
        fetch_and_analyze()
        time.sleep(3)

if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    scanner_loop()
            
