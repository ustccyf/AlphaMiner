from datetime import date, datetime
from typing import Dict, List, Optional, Set

import pandas as pd

from ..core.types import Bar
from .data_source import DataSource


class DailyBarFeed:
    def __init__(
        self,
        source: DataSource,
        symbols: List[str],
        start: date,
        end: date,
    ):
        self.source = source
        self.symbols = symbols
        self.start = start
        self.end = end
        self._data: Dict[str, pd.DataFrame] = {}
        self._dates: List[pd.Timestamp] = []
        self._idx: int = 0

    def load(self) -> None:
        for sym in self.symbols:
            df = self.source.load_symbol(sym, self.start, self.end)
            self._data[sym] = df

        date_sets: List[Set] = []
        for sym in self.symbols:
            if sym in self._data:
                date_sets.append(set(self._data[sym].index))
        self._dates = sorted(set.intersection(*date_sets)) if date_sets else []
        self._idx = 0

    def next(self) -> Dict[str, Bar]:
        dt = self._dates[self._idx]
        bars = {}
        for sym in self.symbols:
            df = self._data.get(sym)
            if df is None or dt not in df.index:
                continue
            row = df.loc[dt]
            bars[sym] = Bar(
                symbol=sym,
                time=dt.to_pydatetime(),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(row["volume"]),
                amount=float(row.get("amount", 0)),
                prev_close=float(row.get("prev_close", row["close"])),
            )
        return bars

    def has_next(self) -> bool:
        return self._idx < len(self._dates)

    def advance(self) -> None:
        self._idx += 1

    def current_time(self) -> Optional[datetime]:
        if self._idx < len(self._dates):
            return self._dates[self._idx].to_pydatetime()
        return None

    def get_history(self, symbol: str, window: int = 60) -> pd.DataFrame:
        df = self._data.get(symbol)
        if df is None:
            return pd.DataFrame()
        end_loc = self._idx
        start_loc = max(0, end_loc - window)
        return df.iloc[start_loc:end_loc]
