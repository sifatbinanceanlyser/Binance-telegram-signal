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
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Telegram Error: {e}")

app = Flask('')

@app.route('/')
def home():
    return "5-Pic Setup + Moderate SMC Engine Active on Free Render!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def get_binance_ohlcv(symbol, interval='1m', limit=25):
    formatted_symbol = symbol.replace('/', '')
    url = f"https://api.binance.com/api/v3/klines?symbol={formatted_symbol}&interval={interval}&limit={limit}"
    
    try:
        response = requests.get(url, timeout=4)
        data = response.json()
        if isinstance(data, list):
            parsed_data = []
            for item in data:
                parsed_data.append([
                    item[0], float(item[1]), float(item[2]), 
                    float(item[3]), float(item[4]), float(item[5])
                ])
            return parsed_data
    except Exception as e:
        print(f"Error on {symbol}: {e}")
    return []

def fetch_and_analyze():
    symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT']
    
    for symbol in symbols:
        try:
            ohlcv = get_binance_ohlcv(symbol, interval='1m', limit=25)
            if not ohlcv or len(ohlcv) < 15:
                continue

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            close_p = df['close'].iloc[-1]
            open_p = df['open'].iloc[-1]
            high_p = df['high'].iloc[-1]
            low_p = df['low'].iloc[-1]

            prev_close = df['close'].iloc[-2]
            prev_open = df['open'].iloc[-2]

            # --- MODERATE SMC & 5-PICTURE STRATEGIES ---
            
            # 1. SMC Liquidity Sweep & Reversal
            prev_high = df['high'].iloc[-2]
            prev_low = df['low'].iloc[-2]
            
            smc_bullish_sweep = (low_p < prev_low) and (close_p > open_p)
            smc_bearish_sweep = (high_p > prev_high) and (close_p < open_p)

            # 2. Support & Resistance Shot Pattern (Image 1 & 2)
            resistance = df['high'].iloc[-10:-1].max()
            support = df['low'].iloc[-10:-1].min()

            is_shot_bullish = (close_p > resistance) and (close_p > open_p)
            is_shot_bearish = (close_p < support) and (close_p < open_p)

            # 3. Back-to-Back Candle Breakout (Image 1)
            is_b2b_support_break = (prev_close > prev_open) and (close_p < open_p) and (close_p < df['low'].iloc[-2])

            # 4. Trend Continuation Rejection (Image 3)
            red_count = (df['close'].iloc[-5:-2] < df['open'].iloc[-5:-2]).sum()
            is_rejection_bearish = (red_count >= 2) and (prev_close > prev_open) and (close_p < open_p) and (close_p < prev_open)

            # --- SIGNAL SELECTION ---
            signal_type = None
            reason = ""

            if smc_bullish_sweep:
                signal_type = "UP"
                reason = "SMC Liquidity Sweep Reversal"
            elif is_shot_bullish:
                signal_type = "UP"
                reason = "Shot Pattern Resistance Breakout"
            elif smc_bearish_sweep:
                signal_type = "DOWN"
                reason = "SMC Liquidity Sweep Reversal"
            elif is_shot_bearish:
                signal_type = "DOWN"
                reason = "Shot Pattern Support Breakout"
            elif is_b2b_support_break:
                signal_type = "DOWN"
                reason = "Back-to-Back Support Break"
            elif is_rejection_bearish:
                signal_type = "DOWN"
                reason = "Trend Continuation Rejection"

            # Execute Signal
            if signal_type and symbol not in active_trades:
                active_trades[symbol] = {
                    'direction': signal_type,
                    'entry_price': close_p,
                    'expire_time': time.time() + 60
                }

                emoji = "🟢" if signal_type == "UP" else "🔴"
                action = "UP (Call)" if signal_type == "UP" else "DOWN (Put)"

                msg = (f"{emoji} *MODERATE 1-MIN LIVE SIGNAL*\n\n"
                       f"🪙 *Asset:* `{symbol}`\n"
                       f"📈 *Direction:* `{action}`\n"
                       f"⏱️ *Timeframe:* `1 Minute`\n"
                       f"💵 *Exact Entry:* `{close_p:.4f}`\n"
                       f"⚡ *Strategy:* {reason}\n\n"
                       f"👉 *Action:* Place trade on Quotex now!")
                send_telegram_msg(msg)

            # Win/Loss Tracker Result
            current_time = time.time()
            if symbol in active_trades:
                trade = active_trades[symbol]
                if current_time >= trade['expire_time']:
                    entry = trade['entry_price']
                    if trade['direction'] == 'UP':
                        if close_p > entry:
                            send_telegram_msg(f"✅ *WIN!* 🎉 (1-Min)\n🪙 `{symbol}`\n📈 Direction: `UP`\n💵 Entry: `{entry:.4f}` | Exit: `{close_p:.4f}`")
                        else:
                            send_telegram_msg(f"❌ *LOSS!* ⚠️ (1-Min)\n🪙 `{symbol}`\n📈 Direction: `UP`\n💵 Entry: `{entry:.4f}` | Exit: `{close_p:.4f}`")
                    elif trade['direction'] == 'DOWN':
                        if close_p < entry:
                            send_telegram_msg(f"✅ *WIN!* 🎉 (1-Min)\n🪙 `{symbol}`\n📉 Direction: `DOWN`\n💵 Entry: `{entry:.4f}` | Exit: `{close_p:.4f}`")
                        else:
                            send_telegram_msg(f"❌ *LOSS!* ⚠️ (1-Min)\n🪙 `{symbol}`\n📉 Direction: `DOWN`\n💵 Entry: `{entry:.4f}` | Exit: `{close_p:.4f}`")
                    
                    del active_trades[symbol]

            time.sleep(0.05)

        except Exception as e:
            print(f"Error on {symbol}: {e}")

def scanner_loop():
    time.sleep(3)
    send_telegram_msg("⚡ *Moderate SMC + 5-Pic Strategy Engine Activated!*")
    while True:
        fetch_and_analyze()
        time.sleep(1)

if __name__ == "__main__":
    t_flask = threading.Thread(target=run_flask)
    t_flask.daemon = True
    t_flask.start()
    scanner_loop()
            
