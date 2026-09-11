import pandas as pd

def detect_setup_8_down_signal(df, snr_level):
    """
    Setup 8 Logic:
    1. Overall Downtrend.
    2. Candle 1: Red candle breaking below SNR Support line.
    3. Candle 2: Another Red candle continuing downward.
    4. Candle 3: Green candle engulfing Candle 2, touching SNR line, 
                 but closing strictly BELOW the SNR line.
    5. Trigger: Next Candle DOWN (SELL / PUT).
    """
    # 1. Determine Candle Colors
    is_red = df['Close'] < df['Open']
    is_green = df['Close'] > df['Open']

    # 2. Downtrend Condition (Candles before Candle 1 were moving down)
    is_downtrend = (df['Close'].shift(3) < df['Open'].shift(3)) & \
                   (df['Close'].shift(4) < df['Open'].shift(4))

    # 3. Candle 1: Red breakout candle closing below SNR level
    candle_1_red = is_red.shift(2) & (df['Close'].shift(2) < snr_level)

    # 4. Candle 2: Continuation Red candle below SNR level
    candle_2_red = is_red.shift(1) & (df['Close'].shift(1) < snr_level)

    # 5. Candle 3: Green Engulfing Candle
    # - Green Candle
    # - Engulfs Candle 2 (Close > Open of Candle 2 and Open < Close of Candle 2)
    # - High touches SNR line (High >= snr_level)
    # - Body closes BELOW SNR line (Close < snr_level)
    candle_3_green = is_green & \
                     (df['Close'] > df['Open'].shift(1)) & \
                     (df['Open'] <= df['Close'].shift(1)) & \
                     (df['High'] >= snr_level) & \
                     (df['Close'] < snr_level)

    # 6. Full Strategy Trigger
    pattern_triggered = is_downtrend & candle_1_red & candle_2_red & candle_3_green

    # 7. Generate Trade Signal
    df['Signal'] = 'HOLD'
    df.loc[pattern_triggered, 'Signal'] = 'SURE SHOT DOWN (SELL)'

    return df


# --- Testing with Sample Market Data ---
market_data = {
    'Open':  [108.0, 105.0, 102.0, 97.0,  95.0,  98.0],
    'High':  [108.0, 105.0, 102.0, 97.5,  95.5, 100.0],  # Candle 3 High touches 100.0 SNR
    'Low':   [105.0, 102.0,  97.0, 94.0,  93.0,  94.5],
    'Close': [105.0, 102.0,  97.0, 95.0,  94.0,  99.0]   # Candle 3 Closes at 99.0 (Below 100 SNR)
}

df = pd.DataFrame(market_data)

# SNR Level set at 100.0
SNR_LINE = 100.0

result = detect_setup_8_down_signal(df, snr_level=SNR_LINE)
print(result[['Open', 'High', 'Low', 'Close', 'Signal']])
