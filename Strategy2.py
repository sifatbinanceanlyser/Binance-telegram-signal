import pandas as pd

def detect_snr_breakout_up_signal(df, snr_resistance_level):
    """
    Detects SNR Breakout Setup-1 (UP / BUY Signal):
    1. Uptrend movement.
    2. Candle 1: A red pullback candle closing below SNR Resistance line.
    3. Candle 2: A green breakout candle that breaks and closes ABOVE SNR line.
    4. Signal: CALL / UP ENTRY for the next candle.
    """
    # 1. Identify Candle Colors
    is_green = df['Close'] > df['Open']
    is_red = df['Close'] < df['Open']

    # 2. Condition 1: Prior Uptrend (Candles before Candle 1 were green)
    prior_uptrend = (df['Close'].shift(2) > df['Open'].shift(2)) & \
                    (df['Close'].shift(3) > df['Open'].shift(3))

    # 3. Condition 2: Candle 1 is Red and closed BELOW the SNR Resistance line
    candle_1_red = is_red.shift(1) & (df['Close'].shift(1) < snr_resistance_level)

    # 4. Condition 3: Candle 2 is Green and BREAKS ABOVE the SNR Resistance line
    candle_2_breakout = is_green & (df['Close'] > snr_resistance_level) & (df['Open'] < snr_resistance_level)

    # 5. Full Pattern Match
    pattern_matched = prior_uptrend & candle_1_red & candle_2_breakout

    # 6. Signal Output
    df['Signal'] = 'HOLD'
    df.loc[pattern_matched, 'Signal'] = 'SURE SHOT UP / CALL'

    return df


# --- Testing Code with Sample Market Data ---
data = {
    'Open':  [100.0, 102.0, 104.0, 105.0, 103.0, 108.0],
    'High':  [102.0, 104.0, 105.0, 105.5, 107.0, 110.0],
    'Low':   [ 99.5, 101.5, 103.5, 102.0, 102.8, 107.0],
    'Close': [102.0, 104.0, 105.0, 103.0, 107.0, 109.0]
}

df = pd.DataFrame(data)

# SNR Resistance level defined at 105.0
SNR_LEVEL = 105.0

result = detect_snr_breakout_up_signal(df, snr_resistance_level=SNR_LEVEL)
print(result[['Open', 'High', 'Low', 'Close', 'Signal']])
