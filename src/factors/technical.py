from typing import Dict

import numpy as np
import pandas as pd

from .base import Factor


class MomentumFactor(Factor):
    """动量因子：N日价格涨跌幅。正值表示上涨趋势。"""
    def __init__(self, window: int = 20):
        super().__init__(f"动量_{window}日")
        self.window = window

    def compute(self, history: Dict[str, pd.DataFrame]) -> pd.Series:
        values = {}
        for sym, df in history.items():
            if len(df) >= self.window:
                values[sym] = df["close"].iloc[-1] / df["close"].iloc[-self.window] - 1
            else:
                values[sym] = 0.0
        return pd.Series(values)


class VolumeRatioFactor(Factor):
    """量比因子：当日成交量 / N日均量。>1 放量，<1 缩量。"""
    def __init__(self, window: int = 20):
        super().__init__(f"量比_{window}日")
        self.window = window

    def compute(self, history: Dict[str, pd.DataFrame]) -> pd.Series:
        values = {}
        for sym, df in history.items():
            if len(df) >= self.window:
                avg_vol = df["volume"].iloc[-self.window:-1].mean()
                cur_vol = df["volume"].iloc[-1]
                values[sym] = cur_vol / avg_vol if avg_vol > 0 else 1.0
            else:
                values[sym] = 1.0
        return pd.Series(values)


class RsiFactor(Factor):
    """RSI因子：14日相对强弱指标。>70超买，<30超卖。"""
    def __init__(self, window: int = 14):
        super().__init__(f"RSI_{window}")
        self.window = window

    def compute(self, history: Dict[str, pd.DataFrame]) -> pd.Series:
        values = {}
        for sym, df in history.items():
            if len(df) < self.window + 1:
                values[sym] = 50.0
                continue
            delta = df["close"].diff()
            gain = delta.clip(lower=0).rolling(self.window).mean()
            loss = (-delta).clip(lower=0).rolling(self.window).mean()
            last_gain = gain.iloc[-1]
            last_loss = loss.iloc[-1]
            if last_loss == 0:
                values[sym] = 100.0
            else:
                rs = last_gain / last_loss
                values[sym] = 100.0 - (100.0 / (1.0 + rs))
        return pd.Series(values)


class VolatilityFactor(Factor):
    """波动率因子：N日收益率标准差。低波动股票常有更好的风险调整收益。"""
    def __init__(self, window: int = 20):
        super().__init__(f"波动率_{window}日")
        self.window = window

    def compute(self, history: Dict[str, pd.DataFrame]) -> pd.Series:
        values = {}
        for sym, df in history.items():
            if len(df) < self.window:
                values[sym] = 0.0
                continue
            returns = df["close"].pct_change().iloc[-self.window:]
            values[sym] = float(returns.std())
        return pd.Series(values)


class MADeviationFactor(Factor):
    """均线偏离因子：(收盘价 - MA) / MA。正值表示偏离均线上方。
    可用于均值回复策略——偏离过大时可能回调。"""
    def __init__(self, window: int = 20):
        super().__init__(f"均线偏离_{window}日")
        self.window = window

    def compute(self, history: Dict[str, pd.DataFrame]) -> pd.Series:
        values = {}
        for sym, df in history.items():
            if len(df) < self.window:
                values[sym] = 0.0
                continue
            ma = df["close"].iloc[-self.window:].mean()
            close = df["close"].iloc[-1]
            values[sym] = (close - ma) / ma if ma > 0 else 0.0
        return pd.Series(values)


class PricePositionFactor(Factor):
    """价格位置因子：(收盘价 - N日最低) / (N日最高 - N日最低)。
    0=在最低点，1=在最高点。衡量当前价格在近期区间中的相对位置。"""
    def __init__(self, window: int = 20):
        super().__init__(f"价格位置_{window}日")
        self.window = window

    def compute(self, history: Dict[str, pd.DataFrame]) -> pd.Series:
        values = {}
        for sym, df in history.items():
            if len(df) < self.window:
                values[sym] = 0.5
                continue
            h = df["high"].iloc[-self.window:].max()
            l = df["low"].iloc[-self.window:].min()
            c = df["close"].iloc[-1]
            rng = h - l
            values[sym] = (c - l) / rng if rng > 0 else 0.5
        return pd.Series(values)


class AmplitudeFactor(Factor):
    """振幅因子：N日(日内振幅=(高-低)/昨收)均值。高振幅意味着多空分歧大。"""
    def __init__(self, window: int = 20):
        super().__init__(f"振幅_{window}日")
        self.window = window

    def compute(self, history: Dict[str, pd.DataFrame]) -> pd.Series:
        values = {}
        for sym, df in history.items():
            if len(df) < self.window:
                values[sym] = 0.0
                continue
            prev_close = df["close"].shift(1)
            amp = (df["high"] - df["low"]) / prev_close.replace(0, np.nan)
            values[sym] = float(amp.iloc[-self.window:].mean())
        return pd.Series(values)


class TurnoverFactor(Factor):
    """成交额因子：N日成交额均值/总成交额排名。衡量资金关注度。"""
    def __init__(self, window: int = 20):
        super().__init__(f"成交额_{window}日")
        self.window = window

    def compute(self, history: Dict[str, pd.DataFrame]) -> pd.Series:
        values = {}
        for sym, df in history.items():
            if len(df) < self.window:
                values[sym] = 0.0
                continue
            values[sym] = float(df["amount"].iloc[-self.window:].mean())
        return pd.Series(values)
