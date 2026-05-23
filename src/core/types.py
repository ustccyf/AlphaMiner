from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Bar:
    symbol: str
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float = 0.0
    prev_close: Optional[float] = None


@dataclass
class Position:
    symbol: str
    quantity: int = 0
    avg_cost: float = 0.0
    market_value: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    today_buy_qty: int = 0


@dataclass
class TradeRecord:
    time: datetime
    symbol: str
    direction: int  # 1=buy, -1=sell
    quantity: int
    price: float
    commission: float
    stamp_duty: float
    turnover: float
    pnl: float = 0.0


@dataclass
class EquityPoint:
    time: datetime
    cash: float
    holdings_value: float
    total: float
    returns: float = 0.0
