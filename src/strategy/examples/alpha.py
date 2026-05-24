from typing import Dict, List

import pandas as pd

from ...core.events import SignalEvent
from ...core.types import Bar
from ...factors.base import Factor
from ...factors.fundamental import (
    ValueFactor, TurnoverRateFactor, ShortTermReversalFactor, MarketCapProxyFactor,
)
from ..base import Strategy


class _FactorStrategy(Strategy):
    """Base for single-factor ranking strategies."""

    def __init__(self, name: str, symbols: List[str], factor: Factor,
                 data_feed=None, top_n: int = 5, rebalance_days: int = 20,
                 ascending: bool = False):
        super().__init__(name)
        self.symbols = symbols
        self.factor = factor
        self.data_feed = data_feed
        self.top_n = top_n
        self.rebalance_days = rebalance_days
        self.ascending = ascending
        self._day_count = 0

    def init(self):
        self._day_count = 0

    def _build_history(self) -> Dict[str, pd.DataFrame]:
        history = {}
        for sym in self.symbols:
            if self.data_feed:
                hist = self.data_feed.get_history(sym, window=60)
                if not hist.empty:
                    history[sym] = hist
        return history

    def next(self, bars: Dict[str, Bar]) -> List[SignalEvent]:
        self._day_count += 1
        signals: List[SignalEvent] = []

        if self._day_count % self.rebalance_days != 0:
            return signals

        history = self._build_history()
        if len(history) < self.top_n:
            return signals

        scores = self.factor.compute(history)
        if scores.empty:
            return signals

        scores = self.factor.winsorize(scores)
        scores = self.factor.standardize(scores)

        if self.ascending:
            top = scores.nsmallest(self.top_n).index.tolist()
        else:
            top = scores.nlargest(self.top_n).index.tolist()

        for sym in top:
            if sym in bars:
                signals.append(SignalEvent(
                    time=bars[sym].time, symbol=sym, direction=1,
                    strength=float(scores.get(sym, 0.5)),
                ))

        for sym in self.symbols:
            if sym not in top:
                signals.append(SignalEvent(
                    time=bars[sym].time if sym in bars else pd.Timestamp.now(),
                    symbol=sym, direction=-1, strength=1.0,
                ))
        return signals


class MicroCapStrategy(_FactorStrategy):
    """微盘股策略：做多成交额最小的股票（市值代理因子）。"""

    def __init__(self, symbols: List[str], data_feed=None):
        super().__init__("微盘股", symbols, MarketCapProxyFactor(20),
                         data_feed=data_feed, ascending=True)


class LowVolStrategy(_FactorStrategy):
    """低波动策略：做多波动率最低的股票。"""
    def __init__(self, symbols: List[str], data_feed=None):
        from ...factors.technical import VolatilityFactor
        super().__init__("低波动", symbols, VolatilityFactor(20),
                         data_feed=data_feed, ascending=True)


class ReversalStrategy(_FactorStrategy):
    """反转策略：做多5日跌幅最大的股票。"""
    def __init__(self, symbols: List[str], data_feed=None):
        super().__init__("反转", symbols, ShortTermReversalFactor(5),
                         data_feed=data_feed, ascending=False)


class LowTurnoverStrategy(_FactorStrategy):
    """低换手率策略：做多换手率最低的股票。"""
    def __init__(self, symbols: List[str], data_feed=None):
        super().__init__("低换手率", symbols, TurnoverRateFactor(),
                         data_feed=data_feed, ascending=True)

    def _build_history(self) -> Dict[str, pd.DataFrame]:
        history = {}
        for sym in self.symbols:
            if self.data_feed:
                try:
                    hist = self.data_feed.source.load_fundamentals(
                        sym,
                        self.data_feed.start,
                        self.data_feed.end,
                    )
                    end_loc = self.data_feed._idx
                    start_loc = max(0, end_loc - 60)
                    hist = hist.iloc[start_loc:end_loc]
                    if not hist.empty:
                        history[sym] = hist
                except Exception:
                    pass
        return history


class ValueStrategy(_FactorStrategy):
    """价值策略：做多低PE低PB股票。"""
    def __init__(self, symbols: List[str], data_feed=None):
        super().__init__("价值", symbols, ValueFactor(),
                         data_feed=data_feed, ascending=False)

    def _build_history(self) -> Dict[str, pd.DataFrame]:
        history = {}
        for sym in self.symbols:
            if self.data_feed:
                try:
                    hist = self.data_feed.source.load_fundamentals(
                        sym,
                        self.data_feed.start,
                        self.data_feed.end,
                    )
                    end_loc = self.data_feed._idx
                    start_loc = max(0, end_loc - 60)
                    hist = hist.iloc[start_loc:end_loc]
                    if not hist.empty:
                        history[sym] = hist
                except Exception:
                    pass
        return history


class SmallCapReversalStrategy(_FactorStrategy):
    """小市值+反转：在小市值股票中做多反转因子。"""
    def __init__(self, symbols: List[str], data_feed=None):
        super().__init__("小市值反转", symbols, ShortTermReversalFactor(5),
                         data_feed=data_feed, ascending=False)
