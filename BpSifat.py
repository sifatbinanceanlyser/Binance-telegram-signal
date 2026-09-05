import pandas as pd
import pandas_ta as ta

class QuotexComplete12MasterBot:
    def __init__(self, df):
        """
        df layout expected columns: ['open', 'high', 'low', 'close', 'volume']
        """
        self.df = df.copy()

    def calculate_stochastic_k(self):
        try:
            stoch = ta.stoch(self.df['high'], self.df['low'], self.df['close'], k=14, d=3)
            if stoch is not None and not stoch.empty:
                return stoch.iloc[-1]['STOCHk_14_3_3']
        except Exception:
            pass
        return 50

    # =========================================================================
    # STRATEGY 1: Pattern 1 Buy Setup (Back-to-Back Red Level Breakout)
    # =========================================================================
    def check_strategy_1_pattern_1_buy(self):
        if len(self.df) < 10: return None
        c1 = self.df.iloc[-1]
        is_green = lambda c: c['close'] > c['open']
        is_red = lambda c: c['close'] < c['open']

        horizontal_line = None
        for i in range(len(self.df) - 3, 2, -1):
            p, c = self.df.iloc[i-1], self.df.iloc[i]
            if is_red(p) and is_red(c):
                horizontal_line = max(p['open'], c['open'])
                break

        if horizontal_line and is_green(c1):
            if (c1['close'] > horizontal_line) or (c1['high'] > horizontal_line):
                return "🟢 CALL / UP (Strategy 1: Pattern 1 Red Junction Breakout Buy)"
        return None

    # =========================================================================
    # STRATEGY 2: Pattern 1 Sell Setup (Back-to-Back Green Level Breakdown)
    # =========================================================================
    def check_strategy_2_pattern_1_sell(self):
        if len(self.df) < 10: return None
        c1 = self.df.iloc[-1]
        is_green = lambda c: c['close'] > c['open']
        is_red = lambda c: c['close'] < c['open']

        horizontal_line = None
        for i in range(len(self.df) - 3, 2, -1):
            p, c = self.df.iloc[i-1], self.df.iloc[i]
            if is_green(p) and is_green(c):
                horizontal_line = min(p['open'], c['open'])
                break

        if horizontal_line and is_red(c1):
            if (c1['close'] < horizontal_line) or (c1['low'] < horizontal_line):
                return "🔴 PUT / DOWN (Strategy 2: Pattern 1 Green Junction Breakdown Sell)"
        return None

    # =========================================================================
    # STRATEGY 3: Pattern 2 Magic V Breakout + Green Continuation
    # =========================================================================
    def check_strategy_3_magic_v_buy(self):
        if len(self.df) < 10: return None
        c1, c2 = self.df.iloc[-1], self.df.iloc[-2]
        is_green = lambda c: c['close'] > c['open']
        swing_high = self.df['high'].tail(10).iloc[:-2].max()

        if (c2['close'] > swing_high) and is_green(c1):
            return "🟢 CALL / UP (Strategy 3: Magic V Breakout + Green Continuation Buy)"
        return None

    # =========================================================================
    # STRATEGY 4: Pattern 2 Magic V Breakout + Red Reversal
    # =========================================================================
    def check_strategy_4_magic_v_sell(self):
        if len(self.df) < 10: return None
        c1, c2 = self.df.iloc[-1], self.df.iloc[-2]
        is_red = lambda c: c['close'] < c['open']
        swing_high = self.df['high'].tail(10).iloc[:-2].max()

        if (c2['close'] > swing_high) and is_red(c1):
            return "🔴 PUT / DOWN (Strategy 4: Magic V Breakout + Red Reversal Sell)"
        return None

    # =========================================================================
    # STRATEGY 5: Pattern 3 V/U Shape Curve Breakout Buy
    # =========================================================================
    def check_strategy_5_curve_buy(self):
        if len(self.df) < 10: return None
        c1, c2, c3 = self.df.iloc[-1], self.df.iloc[-2], self.df.iloc[-3]
        is_green = lambda c: c['close'] > c['open']
        is_red = lambda c: c['close'] < c['open']

        if is_red(c3) and is_green(c2) and is_green(c1):
            curve_peak = max(self.df['high'].tail(8).iloc[:-2])
            if c1['close'] > curve_peak:
                return "🟢 CALL / UP (Strategy 5: Pattern 3 V/U Curve Breakout Buy)"
        return None

    # =========================================================================
    # STRATEGY 6: Pattern 3 Inverted V/U Curve Breakdown Sell
    # =========================================================================
    def check_strategy_6_curve_sell(self):
        if len(self.df) < 10: return None
        c1, c2, c3 = self.df.iloc[-1], self.df.iloc[-2], self.df.iloc[-3]
        is_green = lambda c: c['close'] > c['open']
        is_red = lambda c: c['close'] < c['open']

        if is_green(c3) and is_red(c2) and is_red(c1):
            curve_trough = min(self.df['low'].tail(8).iloc[:-2])
            if c1['close'] < curve_trough:
                return "🔴 PUT / DOWN (Strategy 6: Pattern 3 Inverted V Breakdown Sell)"
        return None

    # =========================================================================
    # STRATEGY 7: Pattern 4 Bullish Engulfing + Tailless Top Buy
    # =========================================================================
    def check_strategy_7_engulfing_buy(self):
        if len(self.df) < 5: return None
        c1, c2, c3 = self.df.iloc[-1], self.df.iloc[-2], self.df.iloc[-3]
        is_green = lambda c: c['close'] > c['open']
        is_red = lambda c: c['close'] < c['open']

        engulfing = is_red(c3) and is_green(c2) and (c2['close'] >= c3['open']) and (c2['open'] <= c3['close'])
        c1_body = abs(c1['close'] - c1['open'])
        c1_upper_wick = c1['high'] - max(c1['close'], c1['open'])

        if engulfing and is_green(c1) and (c1_upper_wick <= c1_body * 0.02):
            return "🟢 CALL / UP (Strategy 7: Bullish Engulfing + Tailless Top Buy)"
        return None

    # =========================================================================
    # STRATEGY 8: Pattern 4 Bearish Engulfing + Tailless Bottom Sell
    # =========================================================================
    def check_strategy_8_engulfing_sell(self):
        if len(self.df) < 5: return None
        c1, c2, c3 = self.df.iloc[-1], self.df.iloc[-2], self.df.iloc[-3]
        is_green = lambda c: c['close'] > c['open']
        is_red = lambda c: c['close'] < c['open']

        engulfing = is_green(c3) and is_red(c2) and (c2['close'] <= c3['open']) and (c2['open'] >= c3['close'])
        c1_body = abs(c1['close'] - c1['open'])
        c1_lower_wick = min(c1['close'], c1['open']) - c1['low']

        if engulfing and is_red(c1) and (c1_lower_wick <= c1_body * 0.02):
            return "🔴 PUT / DOWN (Strategy 8: Bearish Engulfing + Tailless Bottom Sell)"
        return None

    # =========================================================================
    # STRATEGY 9: Pattern 5 Buy Setup (4+ Green + 1 Red Retracement)
    # =========================================================================
    def check_strategy_9_impulse_buy_1(self):
        if len(self.df) < 10: return None
        c1 = self.df.iloc[-1]
        is_green = lambda c: c['close'] > c['open']
        is_red = lambda c: c['close'] < c['open']
        candles = [self.df.iloc[-i] for i in range(1, 10)]

        if is_red(candles[1]) and not is_red(candles[2]):
            if all(is_green(candles[2 + k]) for k in range(4)):
                support = candles[2]['open']
                if is_green(c1) and (c1['close'] >= support) and (c1['low'] >= support):
                    if self.calculate_stochastic_k() < 80:
                        return "🟢 CALL / UP (Strategy 9: 4+ Green + 1 Red Retracement Buy)"
        return None

    # =========================================================================
    # STRATEGY 10: Pattern 5 Buy Setup (4+ Green + 2 Red Retracement)
    # =========================================================================
    def check_strategy_10_impulse_buy_2(self):
        if len(self.df) < 10: return None
        c1 = self.df.iloc[-1]
        is_green = lambda c: c['close'] > c['open']
        is_red = lambda c: c['close'] < c['open']
        candles = [self.df.iloc[-i] for i in range(1, 10)]

        if is_red(candles[1]) and is_red(candles[2]) and not is_red(candles[3]):
            if all(is_green(candles[3 + k]) for k in range(4)):
                support = candles[3]['open']
                if is_green(c1) and (c1['close'] >= support) and (c1['low'] >= support):
                    if self.calculate_stochastic_k() < 80:
                        return "🟢 CALL / UP (Strategy 10: 4+ Green + 2 Red Retracement Buy)"
        return None

    # =========================================================================
    # STRATEGY 11: Pattern 6 Sell Setup (4+ Red + 1 Green Retracement)
    # =========================================================================
    def check_strategy_11_impulse_sell_1(self):
        if len(self.df) < 10: return None
        c1 = self.df.iloc[-1]
        is_green = lambda c: c['close'] > c['open']
        is_red = lambda c: c['close'] < c['open']
        candles = [self.df.iloc[-i] for i in range(1, 10)]

        if is_green(candles[1]) and not is_green(candles[2]):
            if all(is_red(candles[2 + k]) for k in range(4)):
                resistance = candles[1]['high']
                if is_red(c1) and (c1['high'] <= resistance) and (c1['close'] <= resistance):
                    if self.calculate_stochastic_k() > 20:
                        return "🔴 PUT / DOWN (Strategy 11: 4+ Red + 1 Green Retracement Sell)"
        return None

    # =========================================================================
    # STRATEGY 12: Pattern 6 Sell Setup (4+ Red + 2 Green Retracement)
    # =========================================================================
    def check_strategy_12_impulse_sell_2(self):
        if len(self.df) < 10: return None
        c1 = self.df.iloc[-1]
        is_green = lambda c: c['close'] > c['open']
        is_red = lambda c: c['close'] < c['open']
        candles = [self.df.iloc[-i] for i in range(1, 10)]

        if is_green(candles[1]) and is_green(candles[2]) and not is_green(candles[3]):
            if all(is_red(candles[3 + k]) for k in range(4)):
                resistance = max(candles[1]['high'], candles[2]['high'])
                if is_red(c1) and (c1['high'] <= resistance) and (c1['close'] <= resistance):
                    if self.calculate_stochastic_k() > 20:
                        return "🔴 PUT / DOWN (Strategy 12: 4+ Red + 2 Green Retracement Sell)"
        return None

    # =========================================================================
    # MASTER EXECUTION ROUTINE
    # =========================================================================
    def execute_all_strategies(self):
        if len(self.df) < 15:
            return "⏳ পর্যাপ্ত ডাটা নেই (কমপক্ষে ১৫টি ক্যান্ডেল প্রয়োজন)"

        strategies = [
            self.check_strategy_1_pattern_1_buy,
            self.check_strategy_2_pattern_1_sell,
            self.check_strategy_3_magic_v_buy,
            self.check_strategy_4_magic_v_sell,
            self.check_strategy_5_curve_buy,
            self.check_strategy_6_curve_sell,
            self.check_strategy_7_engulfing_buy,
            self.check_strategy_8_engulfing_sell,
            self.check_strategy_9_impulse_buy_1,
            self.check_strategy_10_impulse_buy_2,
            self.check_strategy_11_impulse_sell_1,
            self.check_strategy_12_impulse_sell_2
        ]

        for strategy_func in strategies:
            result = strategy_func()
            if result:
                return result

        return "⏳ কোনো প্যাটার্ন সিগন্যাল পাওয়া যায়নি"


# =============================================================================
# RUNNER SCRIPT FOR TESTING
# =============================================================================
if __name__ == "__main__":
    print("==========================================================")
    print("   QUOTEX FULL 12-STRATEGY MASTER BOT SYSTEM RUNNING      ")
    print("==========================================================")

    test_data = {
        'open':  [105.0, 102.0, 101.0, 105.0, 107.0, 109.0, 108.0, 107.8, 109.5, 111.0, 110.5, 111.2, 112.0, 111.5, 112.5],
        'high':  [105.5, 102.5, 105.2, 107.2, 109.2, 109.5, 108.5, 109.8, 111.2, 111.2, 111.0, 112.5, 112.8, 112.0, 113.5],
        'low':   [101.8, 100.5, 100.8, 104.8, 106.8, 107.8, 107.5, 107.2, 109.0, 110.0, 109.8, 111.0, 111.2, 111.0, 112.0],
        'close': [102.0, 101.0, 105.0, 107.0, 109.0, 108.0, 107.8, 109.5, 111.0, 110.5, 111.2, 112.4, 111.5, 112.5, 113.2],
        'volume': [1200, 1100, 1500, 1600, 1700, 1300, 1200, 1800, 1900, 1400, 1500, 2000, 1800, 2100, 2200]
    }

    df = pd.DataFrame(test_data)
    bot = QuotexComplete12MasterBot(df)
    
    trade_signal = bot.execute_all_strategies()
    print("\nFINAL MARKET SIGNAL RESULT:")
    print("----------------------------------------------------------")
    print("SIGNAL:", trade_signal)
    print("----------------------------------------------------------")
