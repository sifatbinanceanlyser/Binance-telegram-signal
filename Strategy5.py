import pandas as pd

def detect_setup_7_up_signal(df, snr_level):
    """
    Setup 7 Logic:
    1. Market Trend: Overall Uptrend.
    2. Candle 1: Green candle breaking above SNR Resistance line.
    3. Candle 2: Another Green continuation candle above SNR.
    4. Candle 3: Red candle engulfing Candle 2, touching/retesting SNR line, 
                 but body closes strictly ABOVE the SNR line.
    5. Signal: Next Candle UP (BUY / CALL).
    """
    # 1. Determine Candle Colors
    is_green = df['Close'] > df['Open']
    is_red = df['Close'] < df['Open']

    # 2. Uptrend Condition (Candles before Candle 1 were moving up)
    is_uptrend = (df['Close'].shift(3) > df['Open'].shift(3)) & \
                 (df['Close'].shift(4) > df['Open'].shift(4))

    # 3. Candle 1: Green breakout candle closing above SNR level
    candle_1_green = is_green.shift(2) & (df['Close'].shift(2) > snr_level)

    # 4. Candle 2: Green continuation candle above SNR level
    candle_2_green = is_green.shift(1) & (df['Close'].shift(1) > snr_level)

    # 5. Candle 3: Red Engulfing Candle (Retest)
    # - Red Candle
    # - Engulfs Candle 2 (Close < Open of Candle 2 and Open >= Close of Candle 2)
    # - Low touches SNR line (Low <= snr_level)
    # - Body closes ABOVE SNR line (Close > snr_level)
    candle_3_red = is_red & \
                   (df['Close'] < df['Open'].shift(1)) & \
                   (df['Open'] >= df['Close'].shift(1)) & \
                   (df['Low'] <= snr_level) & \
                   (df['Close'] > snr_level)

    # 6. Full Strategy Trigger
    pattern_triggered = is_uptrend & candle_1_green & candle_2_green & candle_3_red

    # 7. Generate Trade Signal
    df['Signal'] = 'HOLD'
    df.loc[pattern_triggered, 'Signal'] = 'SURE SHOT UP (BUY)'

    return df


# --- Testing with Sample Market Data ---
market_data = {
    'Open':  [100.0, 102.0, 104.0, 106.0, 109.0],
    'High':  [102.0, 104.0, 106.5, 110.0, 109.5],
    'Low':   [100.0, 102.0, 104.0, 106.0, 104.5], # Candle 3 Low touches 104.5 (SNR 105.0 area)
    'Close': [102.0, 104.0, 106.0, 109.0, 105.5]  # Candle 3 Closes at 105.5 (Above 105.0 SNR)
}

df = pd.DataFrame(market_data)

# SNR Level set at 105.0
SNR_LINE = 105.0

result = detect_setup_7_up_signal(df, snr_level=SNR_LINE)
print(result[['Open', 'High', 'Low', 'Close', 'Signal']])
