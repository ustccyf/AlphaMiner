from typing import Dict, List, Optional

import pandas as pd

from ..core.events import SignalEvent
from ..core.types import Bar
from ..factors.composite import MultiFactorModel
from .base import Strategy
from .examples.multi_factor import MultiFactorStrategy


class MarketTimer:
    """Simple MA-based market timing filter using a benchmark index."""

    def __init__(self, benchmark_df: pd.DataFrame, ma_window: int = 20):
        bm = benchmark_df.copy()
        bm["date"] = pd.to_datetime(bm["date"])
        bm = bm.set_index("date").sort_index()
        bm["ma"] = bm["close"].rolling(ma_window).mean()
        self._data = bm

    def is_bullish(self, dt) -> bool:
        if dt not in self._data.index:
            return True
        row = self._data.loc[dt]
        ma_val = row.get("ma")
        if pd.isna(ma_val):
            return True
        return float(row["close"]) > float(ma_val)

    def position_scale(self, dt) -> float:
        return 1.0 if self.is_bullish(dt) else 0.0


class TimingMultiFactorStrategy(MultiFactorStrategy):
    """Multi-factor strategy with market timing overlay.

    On rebalance days, checks market regime via MarketTimer.
    Bear market → sell all, stay in cash.
    Bull market → normal multi-factor selection.
    """

    def __init__(
        self,
        symbols: List[str],
        model: MultiFactorModel,
        timer: MarketTimer,
        data_feed=None,
        top_n: int = 5,
        rebalance_days: int = 20,
    ):
        super().__init__(symbols, model, data_feed, top_n, rebalance_days)
        self.timer = timer

    def next(self, bars: Dict[str, Bar]) -> List[SignalEvent]:
        # Check timing before parent's day_count increment
        next_count = self._day_count + 1
        is_rebalance = (next_count % self.rebalance_days == 0)

        if is_rebalance:
            now = None
            for b in bars.values():
                now = b.time
                break

            if not self.timer.is_bullish(now):
                self._day_count = next_count
                signals: List[SignalEvent] = []
                for sym in self.symbols:
                    if sym in bars:
                        signals.append(SignalEvent(
                            time=bars[sym].time,
                            symbol=sym,
                            direction=-1,
                            strength=1.0,
                        ))
                return signals

        return super().next(bars)
