import pandas as pd

def detect_setup_16_reversal_signal(df):
    """
    Setup 16 Logic (False Breakout Reversal):
    1. Box 1: 2 to 3 consecutive Green candles creating a Resistance Level.
    2. Pullback: Market drops down with 1 or more candles.
    3. Candle 2: Green candle breaking above Box 1's Resistance level.
    4. Trigger: Next Candle DOWN (SELL / PUT).
    """
    # 1. Define Candle Colors
    is_green = df['Close'] > df['Open']
    is_red = df['Close'] < df['Open']

    # 2. Check for 2 or 3 Green Candles in Box 1 (placed earlier in history, e.g., shift 3 to 6)
    box_1_3_greens = is_green.shift(4) & is_green.shift(5) & is_green.shift(6)
    box_1_2_greens = is_green.shift(4) & is_green.shift(5)
    
    box_1_valid = box_1_3_greens | box_1_2_greens

    # Calculate Resistance Level from Box 1 (Max High/Close of those candles)
    box_1_resistance = df['Close'].shift(4).combine(df['Close'].shift(5), max)

    # 3. Pullback Period (at least 1-2 candles moving down or staying below resistance)
    pullback_valid = (df['Close'].shift(1) < box_1_resistance) & \
                     (df['Close'].shift(2) < box_1_resistance)

    # 4. Candle 2: Green Breakout Candle closing ABOVE Box 1 Resistance
    candle_2_breakout = is_green & (df['Close'] > box_1_resistance) & (df['Open'] < box_1_resistance)

    # 5. Full Pattern Match
    pattern_matched = box_1_valid & pullback_valid & candle_2_breakout

    # 6. Generate Trade Signal
    df['Signal'] = 'HOLD'
    df.loc[pattern_matched, 'Signal'] = 'SURE SHOT DOWN (SELL)'

    return df


# --- Testing with Sample Market Data ---
market_data = {
    'Open':  [100.0, 102.0, 104.0, 105.0, 102.0, 101.0, 103.0, 108.0],
    'High':  [102.0, 104.0, 106.0, 105.5, 103.0, 103.0, 105.0, 109.0],
    'Low':   [ 99.5, 101.5, 103.5, 101.5, 100.0, 100.5, 102.0, 102.5],
    'Close': [102.0, 104.0, 106.0, 102.0, 101.0, 103.0, 105.0, 108.5] # Breakout above 106.0
}

df = pd.DataFrame(market_data)

result = detect_setup_16_reversal_signal(df)
print(result[['Open', 'High', 'Low', 'Close', 'Signal']])
  
