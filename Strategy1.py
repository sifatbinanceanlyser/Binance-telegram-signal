import pandas as pd

def detect_double_hammer_sell_signal(df):
    """
    Detects a 'Sure Shot Down' signal when:
    1. Market is in a DOWN TREND.
    2. Followed by 2 CONSECUTIVE HAMMER candles.
    3. Triggers a DOWN / SELL entry on the next candle.
    """
    # 1. Calculate Candle Body and Wicks
    df['Body'] = (df['Close'] - df['Open']).abs()
    df['Upper_Wick'] = df['High'] - df[['Open', 'Close']].max(axis=1)
    df['Lower_Wick'] = df[['Open', 'Close']].min(axis=1) - df['Low']

    # Handle zero-body doji candles to avoid division errors
    df['Body'] = df['Body'].replace(0, 0.00001)

    # 2. Define Hammer Candlestick Structure
    # (Lower wick is at least 2x the body, Upper wick is small)
    is_hammer = (df['Lower_Wick'] >= 2 * df['Body']) & (df['Upper_Wick'] <= 0.5 * df['Body'])

    # 3. Define Prior Down Trend Condition
    # Checks if the two candles before the hammers are bearish (Red)
    prior_downtrend = (df['Close'].shift(2) < df['Open'].shift(2)) & \
                      (df['Close'].shift(3) < df['Open'].shift(3))

    # 4. Pattern Trigger: Downtrend + Hammer 1 + Hammer 2
    double_hammer_pattern = prior_downtrend & is_hammer.shift(1) & is_hammer

    # 5. Generate Trade Signals
    df['Signal'] = 'HOLD'
    df.loc[double_hammer_pattern, 'Signal'] = 'SURE SHOT DOWN'

    return df


# --- Example Market Data Testing ---
market_data = {
    'Open':  [100.0, 95.0, 90.0, 87.0, 84.0],
    'High':  [100.0, 95.0, 90.0, 88.0, 84.5],
    'Low':   [ 95.0, 90.0, 82.0, 80.0, 78.0],
    'Close': [ 95.0, 90.0, 86.0, 86.5, 79.0]
}

df = pd.DataFrame(market_data)
result_df = detect_double_hammer_sell_signal(df)

# Display relevant columns
print(result_df[['Open', 'High', 'Low', 'Close', 'Signal']])
