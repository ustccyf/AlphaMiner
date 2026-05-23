from dataclasses import dataclass
from typing import Dict, Optional

from ..core.events import OrderEvent, FillEvent
from ..core.types import Bar, Position
from .commission import CommissionModel
from .price_limit import PriceLimit
from .slippage import SlippageModel


@dataclass
class ExecutionContext:
    cash: float
    positions: Dict[str, Position]
    today_buys: Dict[str, int]


@dataclass
class ExecutionResult:
    fill: Optional[FillEvent]
    cash: float
    positions: Dict[str, Position]
    today_buys: Dict[str, int]
    trade_record: Optional = None  # TradeRecord for sells


class Broker:
    def __init__(
        self,
        commission: CommissionModel,
        slippage: SlippageModel,
    ):
        self.commission_model = commission
        self.slippage_model = slippage

    def execute(
        self, order: OrderEvent, bars: Dict[str, Bar], ctx: ExecutionContext
    ) -> ExecutionResult:
        bar = bars.get(order.symbol)
        if bar is None:
            return ExecutionResult(None, ctx.cash, ctx.positions, ctx.today_buys)

        exec_price = self.slippage_model.apply(bar.close, order.direction)
        exec_price = PriceLimit.clamp(exec_price, bar.prev_close or bar.close)

        if order.direction == 1:
            return self._execute_buy(order, exec_price, ctx)
        else:
            return self._execute_sell(order, exec_price, ctx)

    def _execute_buy(
        self, order: OrderEvent, exec_price: float, ctx: ExecutionContext
    ) -> ExecutionResult:
        exec_price = round(exec_price, 2)
        cost = exec_price * order.quantity
        comm, stamp = self.commission_model.calculate(exec_price, order.quantity, is_buy=True)
        total_cost = cost + comm + stamp

        if total_cost > ctx.cash:
            return ExecutionResult(None, ctx.cash, ctx.positions, ctx.today_buys)

        new_cash = ctx.cash - total_cost
        new_positions = dict(ctx.positions)
        pos = new_positions.get(order.symbol)

        if pos:
            total_shares = pos.quantity + order.quantity
            total_basis = pos.avg_cost * pos.quantity + exec_price * order.quantity
            new_avg = total_basis / total_shares
            new_positions[order.symbol] = Position(
                symbol=order.symbol, quantity=total_shares, avg_cost=new_avg
            )
        else:
            new_positions[order.symbol] = Position(
                symbol=order.symbol, quantity=order.quantity, avg_cost=exec_price
            )

        new_today_buys = dict(ctx.today_buys)
        new_today_buys[order.symbol] = new_today_buys.get(order.symbol, 0) + order.quantity

        fill = FillEvent(
            time=order.time,
            symbol=order.symbol,
            direction=1,
            quantity=order.quantity,
            price=exec_price,
            commission=comm,
            stamp_duty=stamp,
        )

        return ExecutionResult(fill, new_cash, new_positions, new_today_buys)

    def _execute_sell(
        self, order: OrderEvent, exec_price: float, ctx: ExecutionContext
    ) -> ExecutionResult:
        pos = ctx.positions.get(order.symbol)
        if not pos or pos.quantity < order.quantity:
            return ExecutionResult(None, ctx.cash, ctx.positions, ctx.today_buys)

        available = pos.quantity - ctx.today_buys.get(order.symbol, 0)
        max_sell = min(order.quantity, available)
        if max_sell <= 0:
            return ExecutionResult(None, ctx.cash, ctx.positions, ctx.today_buys)

        exec_price = round(exec_price, 2)
        comm, stamp = self.commission_model.calculate(exec_price, max_sell, is_buy=False)
        revenue = exec_price * max_sell - comm - stamp
        cost_basis = pos.avg_cost * max_sell
        realized_pnl = revenue - cost_basis

        new_cash = ctx.cash + revenue
        new_positions = dict(ctx.positions)

        remaining = pos.quantity - max_sell
        if remaining > 0:
            new_positions[order.symbol] = Position(
                symbol=order.symbol,
                quantity=remaining,
                avg_cost=pos.avg_cost,
                realized_pnl=pos.realized_pnl + realized_pnl,
            )
        else:
            new_positions.pop(order.symbol, None)

        from ..core.types import TradeRecord

        trade = TradeRecord(
            time=order.time,
            symbol=order.symbol,
            direction=-1,
            quantity=max_sell,
            price=exec_price,
            commission=comm,
            stamp_duty=stamp,
            turnover=exec_price * max_sell,
            pnl=realized_pnl,
        )

        fill = FillEvent(
            time=order.time,
            symbol=order.symbol,
            direction=-1,
            quantity=max_sell,
            price=exec_price,
            commission=comm,
            stamp_duty=stamp,
        )

        return ExecutionResult(fill, new_cash, new_positions, ctx.today_buys, trade)
