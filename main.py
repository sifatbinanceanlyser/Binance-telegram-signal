import os
import time
import json
import requests
import pandas as pd
import websocket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==========================================
# ১. Render Port Check Bypass Server
# ==========================================
class WebServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Quotex Trading Bot is Active & Running Live!")

    def log_message(self, format, *args):
        return

def run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), WebServerHandler)
    server.serve_forever()

threading.Thread(target=run_http_server, daemon=True).start()
print("=> Render Web Server Started Successfully.")

# ==========================================
# ২. স্ট্র্যাটেজি ফাইল ইমপোর্ট
# ==========================================
import Strategy1
import Strategy2
import Strategy3
import Strategy4
import Strategy5
import Strategy6
import Strategy7

ALL_STRATEGIES = [
    Strategy1, Strategy2, Strategy3, Strategy4,
    Strategy5, Strategy6, Strategy7
]

# ==========================================
# ৩. কনফিগারেশন
# ==========================================
# ব্রাউজারের Cookie থেকে নতুন Fresh SSID কপি করে এখানে দিন
QUOTEX_SSID = "eyJpd2lsIilJBYXJ6WDINb1p6L00ycTZ3cjgxS0E9PSIsInZhHVlljoiQ05mRE56TUl1aHVCN05yYm9VdXB1ck5xM2QvbHZOVDFDZkUvZTdyak1UZmNHVXpHYUhjWjdQnFWMm15iajlzRTIxWkdYb3JzS0ZTY2RwdjBVM2VVTJBFNGp4WGtucFBZMm1xcmTRncjNHM0IrajMwVIV3eXBzTWIFVS9BWUtNOHYiLCJtYWMiOiI4NjkwMDA3Yjc0ZjNiNTc3NjNmMJWJNjMwMzJjZTE2ZWxwZWU4MmVINzA3M2M2Y2YTI3OGY0ZjkzNGQ4ZTtk5liwidGfNljoiln0%3D"
TELEGRAM_BOT_TOKEN = "8447772474:AAF_CwpS1e3clYMEkuN0VZ6UTFqzTsnK2KE"
TELEGRAM_CHAT_ID = "6885238220"
ASSET = "EURUSD_fut"

# ==========================================
# ৪. টেলিগ্রাম সিগন্যাল সেন্ডার (Enhanced)
# ==========================================
def send_telegram_signal(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code != 200:
            print(f"Telegram Failed ({resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"Telegram Notification Error: {e}")

# ==========================================
# ৫. স্ট্র্যাটেজি অ্যানালাইসিস
# ==========================================
def analyze_strategies(df):
    for st in ALL_STRATEGIES:
        for func_name in ['detect_double_hammer_sell_signal', 'detect_signal', 'detect_setup_10_with_prior_green']:
            if hasattr(st, func_name):
                func = getattr(st, func_name)
                try:
                    res_df = func(df)
                    if res_df is not None and isinstance(res_df, pd.DataFrame) and 'Signal' in res_df.columns:
                        if not res_df['Signal'].empty:
                            signal = str(res_df['Signal'].iloc[-1]).upper()
                            if signal in ['BUY', 'SELL', 'CALL', 'PUT', 'SURE SHOT UP / CALL', 'SURE SHOT DOWN (SELL)']:
                                return signal, st.__name__
                except Exception as e:
                    print(f"Skipping strategy {st.__name__} due to error: {e}")
    return None, None

# ==========================================
# ৬. Quotex Direct WebSocket Client
# ==========================================
class QuotexDirectClient:
    def __init__(self, ssid, asset):
        self.ssid = ssid
        self.asset = asset
        self.ws = None
        self.is_connected = False
        self.candles_data = []

    def on_message(self, ws, message):
        if message == '2':
            ws.send('3')
            return

        if message.startswith('42'):
            try:
                data = json.loads(message[2:])
                topic = data[0] if len(data) > 0 else ""
                
                if topic in ["candles", "history", "candles/update"]:
                    raw_candles = data[1]
                    if isinstance(raw_candles, list) and len(raw_candles) > 0:
                        self.candles_data = raw_candles
                    elif isinstance(raw_candles, dict) and 'data' in raw_candles:
                        self.candles_data = raw_candles['data']
            except Exception:
                pass

    def on_open(self, ws):
        print("Connected directly to Quotex WebSocket!")
        self.is_connected = True
        
        auth_msg = f'42["authorization", {{"session": "{self.ssid}"}}]'
        ws.send(auth_msg)
        time.sleep(1)
        
        sub_msg = f'42["candles/subscribe", {{"asset": "{self.asset}", "period": 60}}]'
        ws.send(sub_msg)
        print(f"=> Subscribed to 1-Min candles for {self.asset}")

    def on_error(self, ws, error):
        print(f"WebSocket Error: {error}")

    def on_close(self, ws, status_code, msg):
        print("WebSocket Disconnected. Reconnecting...")
        self.is_connected = False

    def connect(self):
        ws_url = "wss://ws2.quotex.io/socket.io/?EIO=3&transport=websocket"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://quotex.com"
        }
        self.ws = websocket.WebSocketApp(
            ws_url,
            header=headers,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        wst = threading.Thread(target=self.ws.run_forever)
        wst.daemon = True
        wst.start()

# ==========================================
# ৭. মূল এক্সিকিউশন লুপ (With Startup Verification)
# ==========================================
client = QuotexDirectClient(QUOTEX_SSID, ASSET)
client.connect()

# ডিপ্লয় হলে টেলিগ্রামে টেস্ট মেসেজ পাঠানো
send_telegram_signal("🚀 *Quotex Signal Bot Deploy Successful!* System is online and monitoring market live.")

last_signal_time = 0
print("Trading Bot is running active & monitoring markets...")

while True:
    try:
        if not client.is_connected:
            print("Waiting for WebSocket connection...")
            time.sleep(2)
            continue

        if len(client.candles_data) > 0:
            df = pd.DataFrame(client.candles_data)

            rename_dict = {}
            for col in df.columns:
                c_str = str(col).lower()
                if c_str in ['open', 'o']: rename_dict[col] = 'Open'
                elif c_str in ['high', 'h']: rename_dict[col] = 'High'
                elif c_str in ['low', 'l']: rename_dict[col] = 'Low'
                elif c_str in ['close', 'c']: rename_dict[col] = 'Close'
                elif c_str in ['time', 't', 'timestamp']: rename_dict[col] = 'Time'

            df.rename(columns=rename_dict, inplace=True)

            required_cols = {'Open', 'High', 'Low', 'Close'}
            if required_cols.issubset(df.columns):
                current_time = df['Time'].iloc[-1] if 'Time' in df.columns else time.time()

                if current_time != last_signal_time:
                    signal, strategy_name = analyze_strategies(df)
                    
                    print(f"[{time.strftime('%H:%M:%S')}] Candle Processed. Signal: {signal if signal else 'No Pattern'}")

                    if signal:
                        last_signal_time = current_time
                        msg = (
                            f"🚨 *QUOTEX LIVE SIGNAL* 🚨\n\n"
                            f"📊 *Asset:* {ASSET}\n"
                            f"🎯 *Signal:* {signal}\n"
                            f"🛠️ *Strategy:* {strategy_name}\n"
                            f"⏰ *Timeframe:* 1 Min"
                        )
                        send_telegram_signal(msg)
                        print(f"✅ Signal Sent to Telegram: {signal} ({strategy_name})")
        else:
            print("Waiting for candle data from Quotex...")

        time.sleep(5)

    except Exception as e:
        print(f"Main Loop Error: {e}")
        time.sleep(5)
                        
