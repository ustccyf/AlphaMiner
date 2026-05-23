from typing import Dict, List, Optional

import pandas as pd

from ...core.events import SignalEvent
from ...core.types import Bar
from ...factors.base import Factor
from ...factors.composite import MultiFactorModel
from ..base import Strategy


class MultiFactorStrategy(Strategy):
    def __init__(
        self,
        symbols: List[str],
        model: MultiFactorModel,
        data_feed=None,
        top_n: int = 5,
        rebalance_days: int = 20,
    ):
        super().__init__("MultiFactor")
        self.symbols = symbols
        self.model = model
        self.data_feed = data_feed
        self.top_n = top_n
        self.rebalance_days = rebalance_days
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
