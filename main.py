import os
import time
import json
import threading
import requests
import websocket
import pandas as pd
from flask import Flask

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8447772474:AAF_CwpS1e3clYMEkuN0VZ6UTFqzTsnK2KE")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "6885238220")

candle_data = {}
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
    return "All 5 Strategies + Real-Time WebSocket Engine Active!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Complete Strategy Analysis Logic
def analyze_completed_candle(symbol, kline):
    open_p = float(kline['o'])
    close_p = float(kline['c'])
    high_p = float(kline['h'])
    low_p = float(kline['l'])
    is_closed = kline['x']

    if not is_closed:
        return

    if symbol not in candle_data:
        candle_data[symbol] = []

    candle_data[symbol].append({
        'open': open_p, 'close': close_p,
        'high': high_p, 'low': low_p
    })

    if len(candle_data[symbol]) > 30:
        candle_data[symbol].pop(0)

    df = pd.DataFrame(candle_data[symbol])
    if len(df) < 15:
        return

    # --- 1. SMC CALCULATIONS ---
    df['prev_high'] = df['high'].shift(1)
    df['prev_low'] = df['low'].shift(1)
    df['bullish_sweep'] = df['low'] < df['prev_low']
    df['bearish_sweep'] = df['high'] > df['prev_high']
    df['bullish_fvg'] = df['low'] > df['high'].shift(2)
    df['bearish_fvg'] = df['high'] < df['low'].shift(2)

    is_smc_bullish = (df['bullish_sweep'].iloc[-2] or df['bullish_sweep'].iloc[-1]) and \
                     (df['bullish_fvg'].iloc[-1] or (close_p > df['high'].iloc[-2])) and (close_p > open_p)

    is_smc_bearish = (df['bearish_sweep'].iloc[-2] or df['bearish_sweep'].iloc[-1]) and \
                     (df['bearish_fvg'].iloc[-1] or (close_p < df['low'].iloc[-2])) and (close_p < open_p)

    # --- 2. SHOT PATTERN & SUPPORT BREAKOUT (IMAGE 1 & 2) ---
    resistance = df['high'].iloc[-10:-1].max()
    support = df['low'].iloc[-10:-1].min()

    is_shot_bullish = (close_p > resistance) and (close_p > open_p)
    is_shot_bearish = (close_p < support) and (close_p < open_p)

    # --- 3. TREND CONTINUATION & REJECTION (IMAGE 3) ---
    red_count = (df['close'].iloc[-6:-2] < df['open'].iloc[-6:-2]).sum()
    is_rejection_bearish = (red_count >= 3) and \
                           (df['close'].iloc[-2] > df['open'].iloc[-2]) and \
                           (close_p < open_p) and (close_p <= support)

    # --- FINAL SIGNAL DECISION ---
    signal_type = None
    reason = ""

    if is_smc_bullish:
        signal_type = "UP"
        reason = "SMC Liquidity Sweep + FVG"
    elif is_shot_bullish:
        signal_type = "UP"
        reason = "Shot Pattern Resistance Breakout"
    elif is_smc_bearish:
        signal_type = "DOWN"
        reason = "SMC Liquidity Sweep + FVG"
    elif is_shot_bearish:
        signal_type = "DOWN"
        reason = "Shot Pattern Support Breakout"
    elif is_rejection_bearish:
        signal_type = "DOWN"
        reason = "Trend Continuation Rejection Setup"

    # --- SEND SIGNAL ---
    if signal_type and symbol not in active_trades:
        active_trades[symbol] = {
            'direction': signal_type,
            'entry_price': close_p,
            'expire_time': time.time() + 60
        }

        emoji = "🟢" if signal_type == "UP" else "🔴"
        action = "UP (Call)" if signal_type == "UP" else "DOWN (Put)"

        msg = (f"{emoji} *EXACT LIVE 1-MIN SIGNAL*\n\n"
               f"🪙 *Asset:* `{symbol.upper()}`\n"
               f"📈 *Direction:* `{action}`\n"
               f"⏱️ *Timeframe:* `1 Minute`\n"
               f"💵 *Exact Entry:* `{close_p:.4f}`\n"
               f"⚡ *Strategy:* {reason}\n\n"
               f"👉 *Action:* Place trade on Quotex right now!")
        send_telegram_msg(msg)

# Binance Live WebSocket Stream
def on_message(ws, message):
    data = json.loads(message)
    if 'data' in data and 'k' in data['data']:
        symbol = data['data']['s']
        kline = data['data']['k']
        analyze_completed_candle(symbol, kline)

def start_websocket():
    symbols = ['btcusdt', 'ethusdt', 'bnbusdt', 'solusdt', 'xrpusdt', 'adausdt', 'dogeusdt', 'avaxusdt', 'nearusdt', 'linkusdt']
    streams = "/".join([f"{s}@kline_1m" for s in symbols])
    socket_url = f"wss://stream.binance.com:9443/stream?streams={streams}"

    ws = websocket.WebSocketApp(
        socket_url,
        on_message=on_message,
        on_error=lambda ws, err: print(f"WS Error: {err}"),
        on_close=lambda ws, c, m: print("WS Closed. Reconnecting...")
    )
    ws.run_forever()

if __name__ == "__main__":
    t_flask = threading.Thread(target=run_flask)
    t_flask.daemon = True
    t_flask.start()

    send_telegram_msg("⚡ *All 5 Strategies + Live WebSocket Engine Connected!*")

    while True:
        try:
            start_websocket()
        except Exception as e:
            print(f"Connection lost, retrying... {e}")
            time.sleep(2)
            
