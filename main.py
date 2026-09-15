import os
import time
import datetime
import requests
import pandas as pd
from flask import Flask
from threading import Thread

# ==================== IMPORTS FROM YOUR STRATEGY FILES ====================
import Strategy1
import Strategy2
import Strategy3
import Strategy4
import Strategy5
import Strategy6
import Strategy7

# ==================== ENVIRONMENT CONFIGURATION ====================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Binance Public Pairs matching Quotex Real Crypto Candles
PAIRS = [
    "BTCUSDT", "ETHUSDT", "LTCUSDT", "XRPUSDT", "SOLUSDT",
    "DOGEUSDT", "BNBUSDT", "ADAUSDT", "DOTUSDT", "TRXUSDT"
]
TIMEFRAME = "1m"  # 1 Minute Candles

app = Flask(__name__)

@app.route('/')
def home():
    return "Binance-Quotex Signal Engine & Win/Loss Tracker Active!"

# ==================== TELEGRAM NOTIFIER ====================
def send_telegram_alert(pair, signal_type, strategy_name, entry_price):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[{strategy_name}] Signal: {signal_type} on {pair} at {entry_price}")
        return
        
    quotex_pair = f"{pair[:-4]}/{pair[-4:]}"
    
    # Signal Direction Checking
    sig_upper = str(signal_type).upper()
    if any(x in sig_upper for x in ["CALL", "BUY", "UP"]):
        direction = "🟢 NEXT CANDLE: CALL (UP)"
    else:
        direction = "🔴 NEXT CANDLE: PUT (DOWN)"
    
    message = (
        f"🚨 *QUOTEX LIVE SIGNAL (BINANCE DATA)* 🚨\n\n"
        f"📌 *Pair:* `{quotex_pair}`\n"
        f"📊 *Signal:* {direction}\n"
        f"🎯 *Strategy:* `{strategy_name}`\n"
        f"💵 *Current Price:* `{entry_price}`\n"
        f"⏱ *Timeframe:* M1 (1 Min)\n"
        f"⏳ *Entry Time:* 00s of Next Candle!"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=5)
        print(f"✅ Alert sent to Telegram for {quotex_pair} -> {signal_type} ({strategy_name})")
    except Exception as e:
        print(f"❌ Telegram Alert Error: {e}")

# ==================== WIN / LOSS TRACKER NOTIFIER ====================
def send_result_alert(pair, strategy_name, direction_type, result, entry_price, exit_price):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[{strategy_name}] Result: {result} on {pair} (Entry: {entry_price}, Exit: {exit_price})")
        return

    quotex_pair = f"{pair[:-4]}/{pair[-4:]}"
    
    if result == "WIN":
        result_msg = "✅ *RESULT: WIN (SURESHOT)* 🟢"
    elif result == "LOSS":
        result_msg = "❌ *RESULT: LOSS* 🔴"
    else:
        result_msg = "⚪ *RESULT: REFUND / DRAW* 🟡"

    message = (
        f"📊 *SIGNAL RESULT UPDATE* 📊\n\n"
        f"📌 *Pair:* `{quotex_pair}`\n"
        f"🎯 *Strategy:* `{strategy_name}`\n"
        f"➡️ *Direction:* `{direction_type}`\n"
        f"💵 *Entry Price:* `{entry_price}`\n"
        f"🏁 *Exit Price:* `{exit_price}`\n\n"
        f"{result_msg}"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=5)
        print(f"🎯 Result sent to Telegram for {quotex_pair} -> {result}")
    except Exception as e:
        print(f"❌ Telegram Result Error: {e}")

# ==================== PUBLIC BINANCE DATA FETCH ====================
def get_binance_candles(symbol, interval="1m", limit=50):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            return df
    except Exception as e:
        print(f"Binance Public Data Error ({symbol}): {e}")
    return None

# ==================== WIN / LOSS TRACKER LOGIC ====================
def track_signal_result(pair, strategy_name, signal_type, entry_price):
    # সিগন্যাল ক্যান্ডেল শেষ হওয়া এবং ট্রেড ক্যান্ডেল সম্পূর্ণ (১ মিনিট) শেষ হওয়ার জন্য ৬০ সেকেন্ড অপেক্ষা
    time.sleep(62)
    
    df = get_binance_candles(pair, interval=TIMEFRAME, limit=2)
    if df is not None and len(df) >= 1:
        # ট্রেড ক্যান্ডেলের ক্লোজ প্রাইস চেক
        exit_price = df.iloc[-1]['close']
        sig_upper = str(signal_type).upper()
        
        is_call = any(x in sig_upper for x in ["CALL", "BUY", "UP"])
        direction_str = "CALL (UP)" if is_call else "PUT (DOWN)"

        if is_call:
            if exit_price > entry_price:
                result = "WIN"
            elif exit_price < entry_price:
                result = "LOSS"
            else:
                result = "DRAW"
        else: # PUT Signal
            if exit_price < entry_price:
                result = "WIN"
            elif exit_price > entry_price:
                result = "LOSS"
            else:
                result = "DRAW"

        send_result_alert(pair, strategy_name, direction_str, result, entry_price, exit_price)

# ==================== EXECUTE STRATEGIES ====================
def run_custom_strategies(df, pair):
    if df is None or len(df) < 10:
        return

    curr_close = df.iloc[-1]['close']

    strategies = [
        ("Strategy 1", Strategy1),
        ("Strategy 2", Strategy2),
        ("Strategy 3", Strategy3),
        ("Strategy 4", Strategy4),
        ("Strategy 5", Strategy5),
        ("Strategy 6", Strategy6),
        ("Strategy 7", Strategy7),
    ]

    for name, module in strategies:
        try:
            signal = None
            for func_name in ['check_strategy1', 'check_strategy2', 'check_strategy3', 'check_strategy4', 'check_strategy5', 'check_strategy6', 'check_strategy7', 'check_signal', 'get_signal', 'analyze', 'run']:
                if hasattr(module, func_name):
                    signal = getattr(module, func_name)(df)
                    break
            
            # Check if signal is valid
            if signal and isinstance(signal, str):
                sig_clean = signal.upper()
                if any(k in sig_clean for k in ["CALL", "BUY", "PUT", "SELL", "UP", "DOWN"]):
                    if "HOLD" not in sig_clean and "NONE" not in sig_clean:
                        # ১. সিগন্যাল অ্যালার্ট পাঠানো
                        send_telegram_alert(pair, signal, name, curr_close)
                        
                        # ২. ট্র্যাকিং চালু করা (ব্যাকগ্রাউন্ড থ্রেডে, যাতে মেইন স্ক্যান স্লো না হয়)
                        Thread(target=track_signal_result, args=(pair, name, signal, curr_close), daemon=True).start()
        except Exception as e:
            print(f"Error running {name}: {e}")

# ==================== MAIN ANALYSIS LOOP ====================
def binance_signal_engine():
    print("🚀 Binance Engine Active! Analyzing live candles and sending alerts...")
    
    # Startup Telegram Test Alert
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            test_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(test_url, json={
                "chat_id": TELEGRAM_CHAT_ID, 
                "text": "🤖 *Signal Engine & Win/Loss Tracker Started!*", 
                "parse_mode": "Markdown"
            }, timeout=5)
            print("✅ Startup test alert sent to Telegram.")
        except Exception as e:
            print(f"❌ Startup Telegram Alert Failed: {e}")

    while True:
        try:
            now = datetime.datetime.now()
            if now.second >= 58:
                for pair in PAIRS:
                    df = get_binance_candles(pair, interval=TIMEFRAME, limit=50)
                    if df is not None:
                        run_custom_strategies(df, pair)
                
                time.sleep(5)
            else:
                time.sleep(0.3)
        except Exception as e:
            print(f"Engine Loop Error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    Thread(target=binance_signal_engine, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
                                
