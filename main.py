import os
import time
import threading
from datetime import datetime, timezone
import requests
from flask import Flask, jsonify

BINANCE_BASE = "https://api.binance.com"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT",
    "DOTUSDT", "LINKUSDT", "MATICUSDT", "NEARUSDT", "LTCUSDT", "SHIBUSDT", "TRXUSDT", "BCHUSDT",
    "ATOMUSDT", "UNIUSDT", "APTUSDT", "FILUSDT", "ETCUSDT", "XLMUSDT", "INJUSDT", "OPUSDT",
    "ARBUSDT", "TIAUSDT", "SUIUSDT", "SEIUSDT", "FETUSDT", "RNDRUSDT", "PEPEUSDT", "FLOKIUSDT",
    "WIFUSDT", "BONKUSDT", "ORDIUSDT", "GALAUSDT", "STXUSDT", "AAVEUSDT", "MKRUSDT", "SANDUSDT",
    "MANAUSDT", "AXSUSDT", "DYDXUSDT", "CRVUSDT", "LDOUSDT", "EGLDUSDT", "FTMUSDT", "THETAUSDT",
    "KASUSDT", "RUNEUSDT"
]

INTERVAL = "15m"
LIMIT = 100
SCAN_SECONDS = 15 * 60

app = Flask(__name__)

@app.get("/")
def health():
    return jsonify({
        "status": "ok",
        "bot": "Binance 50 Coins Scanner Bot",
        "time": datetime.now(timezone.utc).isoformat()
    })

def get_klines(symbol):
    r = requests.get(
        f"{BINANCE_BASE}/api/v3/klines",
        params={"symbol": symbol, "interval": INTERVAL, "limit": LIMIT},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()

def parse_klines(klines):
    highs = [float(row[2]) for row in klines]
    lows = [float(row[3]) for row in klines]
    closes = [float(row[4]) for row in klines]
    return highs, lows, closes

def calculate_ema(values, period):
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    val = sum(values[:period]) / period
    for p in values[period:]:
        val = p * k + val * (1 - k)
    return val

def calculate_rsi(closes, period=14):
    if len(closes) <= period:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_g = ((avg_g * (period - 1)) + gains[i]) / period
        avg_l = ((avg_l * (period - 1)) + losses[i]) / period
    if avg_l == 0:
        return 100.0
    return 100 - (100 / (1 + (avg_g / avg_l)))

def calculate_atr(highs, lows, closes, period=14):
    if len(closes) <= period:
        return None
    tr_list = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        tr_list.append(tr)
    return sum(tr_list[-period:]) / period

def analyze_symbol(symbol):
    klines = get_klines(symbol)
    highs, lows, closes = parse_klines(klines)

    ema_50 = calculate_ema(closes, 50)
    rsi_val = calculate_rsi(closes)
    atr_val = calculate_atr(highs, lows, closes)

    if None in (ema_50, rsi_val, atr_val):
        return None

    current_price = closes[-1]
    signal_type = None

    if current_price > ema_50 and rsi_val < 42:
        signal_type = "LONG"
    elif current_price < ema_50 and rsi_val > 58:
        signal_type = "SHORT"

    if not signal_type:
        return None

    if signal_type == "LONG":
        entry = current_price
        sl = entry - (atr_val * 1.5)
        tp1 = entry + (atr_val * 1.0)
        tp2 = entry + (atr_val * 2.0)
        tp3 = entry + (atr_val * 3.2)
    else:
        entry = current_price
        sl = entry + (atr_val * 1.5)
        tp1 = entry - (atr_val * 1.0)
        tp2 = entry - (atr_val * 2.0)
        tp3 = entry - (atr_val * 3.2)

    clean_coin = symbol.replace("USDT", "")

    return {
        "coin": clean_coin,
        "signal": signal_type,
        "leverage": 20,
        "entry": entry,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "sl": sl
    }

def format_telegram_message(data):
    coin_tag = f"#{data['coin']}/USDT"
    return f"""🟢 {coin_tag}

📊 Signal: {data['signal']} Leverage: Cross {data['leverage']}X

⚡ Entry Zone: {data['entry']:.6g}

🎯 Take Profit:
1️⃣ TP1: {data['tp1']:.6g}
2️⃣ TP2: {data['tp2']:.6g}
3️⃣ TP3: {data['tp3']:.6g}

⛔ Stop Loss: {data['sl']:.6g}

✅ Trailing Stop: Move SL to Breakeven after TP1 is hit.

📢 Trade Smart • Follow Risk"""

def telegram_send(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram configuration missing.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            timeout=15,
        )
        r.raise_for_status()
    except Exception as e:
        print(f"Telegram Send Error: {e}")

def scanner_loop():
    print("Futures 50 Coins Scanner Started...")
    while True:
        try:
            for symbol in SYMBOLS:
                try:
                    res = analyze_symbol(symbol)
                    if res:
                        msg = format_telegram_message(res)
                        telegram_send(msg)
                        print(f"Signal Generated for {symbol}")
                    time.sleep(0.5)
                except Exception as exc:
                    print(f"Error analyzing {symbol}: {exc}")

            time.sleep(SCAN_SECONDS)

        except Exception as exc:
            print(f"Scanner Loop Error: {exc}")
            time.sleep(30)

if __name__ == "__main__":
    thread = threading.Thread(target=scanner_loop, daemon=True)
    thread.start()

    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
