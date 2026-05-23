from typing import Dict, List

import pandas as pd

from ...core.events import SignalEvent
from ...core.types import Bar
from ..base import Strategy


class MACrossoverStrategy(Strategy):
    def __init__(self, symbols: List[str], fast: int = 5, slow: int = 20, data_feed=None):
        super().__init__(f"MA_{fast}_{slow}")
        self.symbols = symbols
        self.fast = fast
        self.slow = slow
        self.data_feed = data_feed
        self.previous: Dict[str, str] = {}  # symbol -> "above"|"below"|None

    def init(self):
        self.previous.clear()

    def next(self, bars: Dict[str, Bar]) -> List[SignalEvent]:
        signals = []
        for sym in self.symbols:
            if sym not in bars:
                continue
            hist = self._get_history(sym)
            if len(hist) < self.slow + 1:
                continue

            fast_ma = hist["close"].iloc[-self.fast:].mean()
            slow_ma = hist["close"].iloc[-self.slow:].mean()
            prev_fast = hist["close"].iloc[-(self.fast + 1):-1].mean()
            prev_slow = hist["close"].iloc[-(self.slow + 1):-1].mean()

            prev_state = "above" if prev_fast > prev_slow else "below"
            curr_state = "above" if fast_ma > slow_ma else "below"

            if prev_state == "below" and curr_state == "above":
                signals.append(
                    SignalEvent(
                        time=bars[sym].time, symbol=sym, direction=1, strength=1.0
                    )
                )
            elif prev_state == "above" and curr_state == "below":
                signals.append(
                    SignalEvent(
                        time=bars[sym].time, symbol=sym, direction=-1, strength=1.0
                    )
                )

        return signals

    def _get_history(self, symbol: str) -> pd.DataFrame:
        if self.data_feed is None:
            return pd.DataFrame()
        return self.data_feed.get_history(symbol, window=self.slow + 5)
