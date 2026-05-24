from typing import Dict, List, Optional

import pandas as pd

from ...core.events import SignalEvent
from ...core.types import Bar
from ...factors.base import Factor
from ...factors.ic_weighted import ICWeightedModel
from ...factors.ml_composite import MLFactorModel
from ..base import Strategy


class ICWeightedStrategy(Strategy):
    """Multi-factor strategy using IC-weighted dynamic factor combination.

    Factor weights are updated each rebalance period based on each factor's
    recent Information Coefficient (rank correlation with forward returns).
    """

    def __init__(
        self,
        symbols: List[str],
        factors: List[Factor],
        data_feed=None,
        top_n: int = 5,
        rebalance_days: int = 20,
    ):
        super().__init__("ICWeighted")
        self.symbols = symbols
        self.data_feed = data_feed
        self.top_n = top_n
        self.rebalance_days = rebalance_days
        self.model = ICWeightedModel(factors)
        self._day_count: int = 0

    def init(self):
        self._day_count = 0

    def next(self, bars: Dict[str, Bar]) -> List[SignalEvent]:
        self._day_count += 1
        signals: List[SignalEvent] = []

        if self._day_count % self.rebalance_days != 0:
            return signals

        history: Dict[str, pd.DataFrame] = {}
        for sym in self.symbols:
            if self.data_feed:
                hist = self.data_feed.get_history(sym, window=60)
                if not hist.empty:
                    history[sym] = hist

        if len(history) < self.top_n:
            return signals

        scores = self.model.score(history)
        if scores.empty:
            return signals

        top_symbols = scores.nlargest(self.top_n).index.tolist()

        for sym in top_symbols:
            if sym in bars:
                signals.append(SignalEvent(
                    time=bars[sym].time,
                    symbol=sym,
                    direction=1,
                    strength=scores.get(sym, 0.5),
                ))

        for sym in self.symbols:
            if sym not in top_symbols:
                signals.append(SignalEvent(
                    time=bars[sym].time if sym in bars else pd.Timestamp.now(),
                    symbol=sym,
                    direction=-1,
                    strength=1.0,
                ))

        return signals


class MLFactorStrategy(Strategy):
    """Multi-factor strategy using Ridge regression for factor combination.

    Trains a Ridge model on historical factor→return pairs and predicts
    expected returns for the current stock universe.
    """

    def __init__(
        self,
        symbols: List[str],
        factors: List[Factor],
        data_feed=None,
        top_n: int = 5,
        rebalance_days: int = 20,
    ):
        super().__init__("MLFactor")
        self.symbols = symbols
        self.data_feed = data_feed
        self.top_n = top_n
        self.rebalance_days = rebalance_days
        self.model = MLFactorModel(factors)
        self._day_count: int = 0

    def init(self):
        self._day_count = 0

    def next(self, bars: Dict[str, Bar]) -> List[SignalEvent]:
        self._day_count += 1
        signals: List[SignalEvent] = []

        if self._day_count % self.rebalance_days != 0:
            return signals

        history: Dict[str, pd.DataFrame] = {}
        for sym in self.symbols:
            if self.data_feed:
                hist = self.data_feed.get_history(sym, window=60)
                if not hist.empty:
                    history[sym] = hist

        if len(history) < self.top_n:
            return signals

        scores = self.model.score(history)
        if scores.empty:
            return signals

        top_symbols = scores.nlargest(self.top_n).index.tolist()

        for sym in top_symbols:
            if sym in bars:
                signals.append(SignalEvent(
                    time=bars[sym].time,
                    symbol=sym,
                    direction=1,
                    strength=scores.get(sym, 0.5),
                ))

        for sym in self.symbols:
            if sym not in top_symbols:
                signals.append(SignalEvent(
                    time=bars[sym].time if sym in bars else pd.Timestamp.now(),
                    symbol=sym,
                    direction=-1,
                    strength=1.0,
                ))

        return signals
