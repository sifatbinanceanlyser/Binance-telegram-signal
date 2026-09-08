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
    return "Advanced SMC + Terms Strategy Engine Active!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def get_binance_ohlcv(symbol, interval='1m', limit=30):
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
            ohlcv = get_binance_ohlcv(symbol, interval='1m', limit=30)
            if not ohlcv or len(ohlcv) < 20:
                continue

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            close_p = df['close'].iloc[-1]
            open_p = df['open'].iloc[-1]
            high_p = df['high'].iloc[-1]
            low_p = df['low'].iloc[-1]

            prev_close = df['close'].iloc[-2]
            prev_open = df['open'].iloc[-2]
            prev_high = df['high'].iloc[-2]
            prev_low = df['low'].iloc[-2]

            # --- PREVIOUS STRATEGIES (Shot Pattern, Liquidity Sweeps) ---
            resistance = df['high'].iloc[-10:-1].max()
            support = df['low'].iloc[-10:-1].min()

            smc_bullish_sweep = (low_p < prev_low) and (close_p > open_p)
            smc_bearish_sweep = (high_p > prev_high) and (close_p < open_p)

            is_shot_bullish = (close_p > resistance) and (close_p > open_p)
            is_shot_bearish = (close_p < support) and (close_p < open_p)

            is_b2b_support_break = (prev_close > prev_open) and (close_p < open_p) and (close_p < df['low'].iloc[-2])

            red_count = (df['close'].iloc[-5:-2] < df['open'].iloc[-5:-2]).sum()
            is_rejection_bearish = (red_count >= 2) and (prev_close > prev_open) and (close_p < open_p) and (close_p < prev_open)

            # --- NEW SMC TERMS LOGIC (CHOCH, BOS, FVG, EQH/EQL) ---
            # 1. CHOCH & BOS (Change of Character / Break of Structure)
            recent_high = df['high'].iloc[-6:-1].max()
            recent_low = df['low'].iloc[-6:-1].min()
            
            is_bullish_choch = (close_p > recent_high) and (prev_close <= recent_high)
            is_bearish_choch = (close_p < recent_low) and (prev_close >= recent_low)

            # 2. FVG (Fair Value Gap) Detection
            c1_high = df['high'].iloc[-3]
            c1_low = df['low'].iloc[-3]
            c3_high = df['high'].iloc[-1]
            c3_low = df['low'].iloc[-1]
            
            is_bullish_fvg = c3_low > c1_high
            is_bearish_fvg = c3_high < c1_low

            # 3. EQH / EQL (Equal Highs / Equal Lows Breakout)
            h1 = df['high'].iloc[-3]
            h2 = df['high'].iloc[-2]
            l1 = df['low'].iloc[-3]
            l2 = df['low'].iloc[-2]
            
            eqh_breakout = (abs(h1 - h2) / h1 < 0.0005) and (close_p > h1)
            eql_breakout = (abs(l1 - l2) / l1 < 0.0005) and (close_p < l1)

            # --- SIGNAL EVALUATION ---
            signal_type = None
            reason = ""

            if is_bullish_choch or eqh_breakout:
                signal_type = "UP"
                reason = "CHOCH / EQH Breakout (Bullish)"
            elif is_bearish_choch or eql_breakout:
                signal_type = "DOWN"
                reason = "CHOCH / EQL Breakout (Bearish)"
            elif is_bullish_fvg:
                signal_type = "UP"
                reason = "Fair Value Gap (FVG) Imbalance"
            elif is_bearish_fvg:
                signal_type = "DOWN"
                reason = "Fair Value Gap (FVG) Imbalance"
            elif smc_bullish_sweep:
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

                msg = (f"{emoji} *ADVANCED SMC 1-MIN SIGNAL*\n\n"
                       f"🪙 *Asset:* `{symbol}`\n"
                       f"📈 *Direction:* `{action}`\n"
                       f"⏱️ *Timeframe:* `1 Minute`\n"
                       f"💵 *Exact Entry:* `{close_p:.4f}`\n"
                       f"⚡ *Strategy:* {reason}\n\n"
                       f"👉 *Action:* Place trade on Quotex now!")
                send_telegram_msg(msg)

            # Win/Loss Tracker
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
    send_telegram_msg("⚡ *Advanced SMC + Terms Strategy Engine Activated!*")
    while True:
        fetch_and_analyze()
        time.sleep(1)

if __name__ == "__main__":
    t_flask = threading.Thread(target=run_flask)
    t_flask.daemon = True
    t_flask.start()
    scanner_loop()
            
