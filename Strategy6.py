import pandas as pd
import numpy as np

def detect_setup_10_with_prior_green(df):
    """
    Setup 10 Exact Logic with Prior Green Candle:
    1. Candle 1: A Green candle (Prior support/base level).
    2. Candle 2 & 3: Two consecutive RED candles (Box 1).
    3. Candle 4: A big GREEN candle that engulfs BOTH previous red candles 
       and closes above their high levels.
    4. Signal: REVERSAL DOWN (SELL / PUT) on the next candle.
    """
    # Define Candle Colors
    is_green = df['Close'] > df['Open']
    is_red = df['Close'] < df['Open']

    # Step 1: Prior Green Candle (Candle before the 2 red candles)
    prior_green_candle = is_green.shift(3)

    # Step 2: Two Consecutive Red Candles
    red_candle_1 = is_red.shift(2)
    red_candle_2 = is_red.shift(1)

    # Get the highest price/open level between the 2 red candles (Fixed using numpy)
    high_shift1 = df[['High', 'Open']].shift(1).max(axis=1)
    high_shift2 = df[['High', 'Open']].shift(2).max(axis=1)
    two_reds_max_high = np.maximum(high_shift1, high_shift2)

    # Step 3: Big Green Engulfing Candle (Candle 4)
    # - Must be a Green Candle
    # - Opens at or below previous red close
    # - Closes strictly ABOVE the highest level of both red candles
    big_green_engulf = is_green & \
                       (df['Open'] <= df['Close'].shift(1)) & \
                       (df['Close'] > two_reds_max_high)

    # Combine All Conditions
    pattern_matched = prior_green_candle & red_candle_1 & red_candle_2 & big_green_engulf

    # Step 4: Generate Trade Signal for Next Candle
    df['Signal'] = 'HOLD'
    df.loc[pattern_matched, 'Signal'] = 'SURE SHOT DOWN (SELL)'

    return df


# --- Testing Code with Sample Market Data ---
market_data = {
    'Open':  [ 98.0, 100.0, 102.0, 100.0,  97.0],
    'High':  [100.5, 102.0, 102.5, 100.0, 103.5],
    'Low':   [ 97.5,  99.0, 100.0,  96.5,  96.0],
    'Close': [100.0, 102.0, 100.0,  97.0, 103.0] 
}

df = pd.DataFrame(market_data)

result = detect_setup_10_with_prior_green(df)
print(result[['Open', 'High', 'Low', 'Close', 'Signal']])
