import pandas as pd

def detect_setup_2_exact(df, snr_support_level):
    """
    Setup 2 Exact Logic (3 Steps):
    Step 1: Market Position (Downtrend)
    Step 2: Candle 1 (Green pullback candle closing above SNR Support)
    Step 3: Candle 2 (Red breakout candle closing below SNR Support)
    Signal: Next Candle DOWN (SELL / PUT)
    """
    # Define candle colors
    is_green = df['Close'] > df['Open']
    is_red = df['Close'] < df['Open']

    # Step 1: Market Position (Downtrend) - At least 2 consecutive red candles before pattern
    downtrend_market = (is_red.shift(2)) & (is_red.shift(3))

    # Step 2: Candle 1 (Green pullback candle closing above SNR Support line)
    candle_1_green = is_green.shift(1) & (df['Close'].shift(1) > snr_support_level)

    # Step 3: Candle 2 (Red breakout candle breaking and closing below SNR Support line)
    candle_2_red_breakout = is_red & (df['Close'] < snr_support_level)

    # Combine all 3 conditions
    exact_pattern = downtrend_market & candle_1_green & candle_2_red_breakout

    # Generate Signal for the Next Candle
    df['Signal'] = 'HOLD'
    df.loc[exact_pattern, 'Signal'] = 'SURE SHOT DOWN (SELL)'

    return df


# --- Testing with Sample Market Data ---
market_data = {
    'Open':  [105.0, 103.0, 101.0, 100.2, 101.5, 97.0],
    'High':  [105.0, 103.0, 101.0, 101.8, 102.0, 97.5],
    'Low':   [103.0, 101.0, 100.0, 99.8,  98.0, 92.0],
    'Close': [103.0, 101.0, 100.0, 101.0, 97.0,  93.0]
}

df = pd.DataFrame(market_data)

# SNR Support Line set at 100.0
SNR_SUPPORT = 100.0

result = detect_setup_2_exact(df, snr_support_level=SNR_SUPPORT)
print(result[['Open', 'High', 'Low', 'Close', 'Signal']])
