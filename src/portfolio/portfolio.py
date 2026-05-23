from datetime import datetime
from typing import Dict, List, Optional

from ..core.events import OrderEvent, SignalEvent, FillEvent
from ..core.types import Bar, EquityPoint, Position, TradeRecord
from ..utils.helpers import round_lot


class Portfolio:
    def __init__(self, initial_cash: float = 1_000_000):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}
        self.equity_curve: List[EquityPoint] = []
        self.trades: List[TradeRecord] = []
        self._today_buys: Dict[str, int] = {}

    def on_signal(self, signal: SignalEvent, bars: Dict[str, Bar]) -> List[OrderEvent]:
        if signal.direction == 0:
            return []

        bar = bars.get(signal.symbol)
        if bar is None:
            return []

        if signal.direction == 1:
            return self._buy_signal(signal, bar)
        elif signal.direction == -1:
            return self._sell_signal(signal, bar)
        return []

    def _buy_signal(self, signal: SignalEvent, bar: Bar) -> List[OrderEvent]:
        allocations = 0.20
        max_alloc = self.total_equity(bars={signal.symbol: bar}) * allocations
        price = bar.close
        qty = int(max_alloc // price) if price > 0 else 0
        qty = round_lot(qty)
        if qty <= 0:
            return []
        return [
            OrderEvent(
                time=signal.time,
                symbol=signal.symbol,
                direction=1,
                quantity=qty,
            )
        ]

    def _sell_signal(self, signal: SignalEvent, bar: Bar) -> List[OrderEvent]:
        pos = self.positions.get(signal.symbol)
        if not pos or pos.quantity <= 0:
            return []
        return [
            OrderEvent(
                time=signal.time,
                symbol=signal.symbol,
                direction=-1,
                quantity=pos.quantity,
            )
        ]

    def on_fill(self, fill: FillEvent, new_cash: float, new_positions: Dict[str, Position], new_today_buys: Dict[str, int], trade_record: Optional[TradeRecord] = None):
        self.cash = new_cash
        self.positions = new_positions
        self._today_buys = new_today_buys
        if trade_record:
            self.trades.append(trade_record)

    def update(self, time: datetime, bars: Dict[str, Bar]):
        holdings_value = sum(
            bars[sym].close * pos.quantity
            for sym, pos in self.positions.items()
            if sym in bars
        )
        total = self.cash + holdings_value
        prev_total = self.equity_curve[-1].total if self.equity_curve else self.initial_cash
        ret = (total / prev_total) - 1 if prev_total > 0 else 0.0

        self.equity_curve.append(
            EquityPoint(
                time=time,
                cash=self.cash,
                holdings_value=holdings_value,
                total=total,
                returns=ret,
            )
        )

    def total_equity(self, bars: Dict[str, Bar]) -> float:
        holdings_value = sum(
            bars[sym].close * pos.quantity
            for sym, pos in self.positions.items()
            if sym in bars
        )
        return self.cash + holdings_value

    def end_of_day(self):
        self._today_buys.clear()
