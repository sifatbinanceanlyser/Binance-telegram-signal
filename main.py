import os
import time
import threading
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify

BINANCE_BASE = "https://api.binance.com"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Educational signal bot only:
# - Uses public Binance market data.
# - Does NOT place orders.
# - Does NOT use Binance trading API keys.
# - Does NOT use leverage.
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT",
    "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT"
]
INTERVAL = "15m"
LIMIT = 120
SCAN_SECONDS = 15 * 60


app = Flask(__name__)


@app.get("/")
def health():
    return jsonify({
        "status": "ok",
        "bot": "Binance Telegram Educational Signal Bot",
        "time": datetime.now(timezone.utc).isoformat()
    })


def get_klines(symbol):
    r = requests.get(
        f"{BINANCE_BASE}/api/v3/klines",
        params={"symbol": symbol, "interval": INTERVAL, "limit": LIMIT},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def closes_from_klines(klines):
    return [float(row[4]) for row in klines]


def ema(values, period):
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    value = sum(values[:period]) / period
    for price in values[period:]:
        value = price * k + value * (1 - k)
    return value


def rsi(values, period=14):
    if len(values) <= period:
        return None

    gains = []
    losses = []
    for i in range(1, len(values)):
        change = values[i] - values[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(values):
    if len(values) < 35:
        return None, None
    fast = ema(values, 12)
    slow = ema(values, 26)
    if fast is None or slow is None:
        return None, None
    # For a lightweight first version, compare the current MACD value
    # with the previous approximate MACD value.
    prev = values[:-1]
    pfast = ema(prev, 12)
    pslow = ema(prev, 26)
    if pfast is None or pslow is None:
        return fast - slow, None
    current = fast - slow
    previous = pfast - pslow
    return current, previous


def strategy_ema(values):
    e9 = ema(values, 9)
    e21 = ema(values, 21)
    if e9 is None or e21 is None:
        return "NEUTRAL"
    if e9 > e21:
        return "BULLISH"
    if e9 < e21:
        return "BEARISH"
    return "NEUTRAL"


def strategy_rsi(values):
    value = rsi(values, 14)
    if value is None:
        return "NEUTRAL"
    if value >= 55:
        return "BULLISH"
    if value <= 45:
        return "BEARISH"
    return "NEUTRAL"


def strategy_macd(values):
    current, previous = macd(values)
    if current is None:
        return "NEUTRAL"
    if previous is not None and current > previous and current > 0:
        return "BULLISH"
    if previous is not None and current < previous and current < 0:
        return "BEARISH"
    return "NEUTRAL"


def strategy_breakout(values, lookback=20):
    if len(values) <= lookback:
        return "NEUTRAL"
    recent = values[-lookback - 1:-1]
    last = values[-1]
    high = max(recent)
    low = min(recent)
    if last > high:
        return "BULLISH"
    if last < low:
        return "BEARISH"
    return "NEUTRAL"


def analyze(symbol):
    klines = get_klines(symbol)
    closes = closes_from_klines(klines)

    results = {
        "EMA Trend": strategy_ema(closes),
        "RSI": strategy_rsi(closes),
        "MACD": strategy_macd(closes),
        "Breakout": strategy_breakout(closes),
    }

    bullish = sum(v == "BULLISH" for v in results.values())
    bearish = sum(v == "BEARISH" for v in results.values())

    if bullish >= 3:
        overall = "BULLISH"
    elif bearish >= 3:
        overall = "BEARISH"
    else:
        overall = "NEUTRAL"

    return {
        "symbol": symbol,
        "price": closes[-1],
        "strategies": results,
        "bullish": bullish,
        "bearish": bearish,
        "overall": overall,
    }


def telegram_send(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram variables are not configured.")
        print(text)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    r = requests.post(
        url,
        data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
        timeout=20,
    )
    r.raise_for_status()


def format_signal(result):
    lines = [
        "📊 Educational Market Signal",
        f"Coin: {result['symbol']}",
        f"Timeframe: {INTERVAL}",
        f"Price: {result['price']:.8g}",
        "",
        "Strategy results:",
    ]

    for name, value in result["strategies"].items():
        emoji = "🟢" if value == "BULLISH" else "🔴" if value == "BEARISH" else "⚪"
        lines.append(f"{emoji} {name}: {value}")

    lines += [
        "",
        f"Overall: {result['overall']}",
        f"Confirmation: {result['bullish']} bullish / {result['bearish']} bearish",
        "",
        "⚠️ Educational signal only — no trade/order is executed.",
    ]
    return "\n".join(lines)


def scanner_loop():
    print("Signal scanner started.")
    while True:
        try:
            for symbol in SYMBOLS:
                try:
                    result = analyze(symbol)
                    print(result)

                    # Only send a Telegram message when at least 3 strategies agree.
                    if result["overall"] in ("BULLISH", "BEARISH"):
                        telegram_send(format_signal(result))

                except Exception as exc:
                    print(f"{symbol} error: {exc}")

            time.sleep(SCAN_SECONDS)

        except Exception as exc:
            print(f"Scanner loop error: {exc}")
            time.sleep(30)


if __name__ == "__main__":
    thread = threading.Thread(target=scanner_loop, daemon=True)
    thread.start()

    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
