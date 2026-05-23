from typing import Dict

from ..core.events import SignalEvent
from ..core.types import Bar, Position
from ..utils.helpers import round_lot


class RiskManager:
    def __init__(
        self,
        max_position_weight: float = 0.20,
        max_positions: int = 10,
        stop_loss: float = 0.07,
        take_profit: float = 0.0,
    ):
        self.max_position_weight = max_position_weight
        self.max_positions = max_positions
        self.stop_loss = stop_loss
        self.take_profit = take_profit

    def compute_target(
        self,
        signal: SignalEvent,
        cash: float,
        positions: Dict[str, Position],
        bars: Dict[str, Bar],
        total_equity: float,
    ) -> int:
        bar = bars.get(signal.symbol)
        if not bar or bar.close <= 0:
            return 0

        if signal.direction == 1:
            if len(positions) >= self.max_positions:
                return 0
            max_alloc = total_equity * self.max_position_weight
            qty = int(max_alloc // bar.close)
            return round_lot(qty)
        else:
            return 0

    def check_stop_loss(self, pos: Position, price: float) -> bool:
        if self.stop_loss <= 0 or pos.avg_cost <= 0:
            return False
        pnl_pct = (price - pos.avg_cost) / pos.avg_cost
        return pnl_pct <= -self.stop_loss

    def check_take_profit(self, pos: Position, price: float) -> bool:
        if self.take_profit <= 0 or pos.avg_cost <= 0:
            return False
        pnl_pct = (price - pos.avg_cost) / pos.avg_cost
        return pnl_pct >= self.take_profit
