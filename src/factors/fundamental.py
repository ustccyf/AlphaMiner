from typing import Dict

import numpy as np
import pandas as pd

from .base import Factor


class ValueFactor(Factor):
    """价值因子：低PE + 低PB 等权合成。Score越高 = 估值越低 = 越便宜。"""

    def __init__(self):
        super().__init__("价值_PE+PB")

    def compute(self, history: Dict[str, pd.DataFrame]) -> pd.Series:
        values = {}
        for sym, df in history.items():
            if df.empty:
                values[sym] = 0.0
                continue
            row = df.iloc[-1]
            pe = row.get("peTTM", np.nan)
            pb = row.get("pbMRQ", np.nan)

            score = 0.0
            count = 0
            if not pd.isna(pe) and pe > 0:
                score += 1.0 / pe
                count += 1
            if not pd.isna(pb) and pb > 0:
                score += 1.0 / pb
                count += 1

            values[sym] = score / count if count > 0 else 0.0
        return pd.Series(values)


class TurnoverRateFactor(Factor):
    """低换手率因子：换手率越低，股票越不受关注，可能存在低估机会。"""

    def __init__(self):
        super().__init__("换手率_低")

    def compute(self, history: Dict[str, pd.DataFrame]) -> pd.Series:
        values = {}
        for sym, df in history.items():
            if df.empty:
                values[sym] = 0.0
                continue
            turn = df["turn"].iloc[-20:].mean() if "turn" in df.columns else np.nan
            if pd.isna(turn):
                values[sym] = 0.0
            else:
                values[sym] = -turn  # negative: lower turnover = higher score
        return pd.Series(values)


class ShortTermReversalFactor(Factor):
    """短期反转因子：做多近期跌幅最大的股票（5日反转效应）。"""

    def __init__(self, window: int = 5):
        super().__init__(f"反转_{window}日")
        self.window = window

    def compute(self, history: Dict[str, pd.DataFrame]) -> pd.Series:
        values = {}
        for sym, df in history.items():
            if len(df) < self.window:
                values[sym] = 0.0
                continue
            ret = df["close"].iloc[-1] / df["close"].iloc[-self.window] - 1
            values[sym] = -ret  # negative: lower past return = higher expected reversal
        return pd.Series(values)


class MarketCapProxyFactor(Factor):
    """市值代理因子：用日均成交额作为市值代理。做多小市值（低成交额）。"""

    def __init__(self, window: int = 20):
        super().__init__(f"市值代理_{window}日")
        self.window = window

    def compute(self, history: Dict[str, pd.DataFrame]) -> pd.Series:
        values = {}
        for sym, df in history.items():
            if len(df) < self.window:
                values[sym] = 0.0
                continue
            avg_amount = df["amount"].iloc[-self.window:].mean()
            values[sym] = -float(avg_amount)
        return pd.Series(values)
