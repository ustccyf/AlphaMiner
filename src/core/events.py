from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Dict, Optional

from .types import Bar


class EventType(Enum):
    MARKET = auto()
    SIGNAL = auto()
    ORDER = auto()
    FILL = auto()


@dataclass
class Event:
    type: EventType
    time: datetime


@dataclass
class MarketEvent(Event):
    type: EventType = field(default=EventType.MARKET, init=False)
    bars: Dict[str, Bar] = field(default_factory=dict)


@dataclass
class SignalEvent(Event):
    type: EventType = field(default=EventType.SIGNAL, init=False)
    symbol: str = ""
    direction: int = 0  # 1=buy, -1=sell, 0=hold
    strength: float = 0.0
    meta: dict = field(default_factory=dict)


@dataclass
class OrderEvent(Event):
    type: EventType = field(default=EventType.ORDER, init=False)
    symbol: str = ""
    direction: int = 0
    quantity: int = 0
    order_type: str = "MARKET"
    limit_price: Optional[float] = None


@dataclass
class FillEvent(Event):
    type: EventType = field(default=EventType.FILL, init=False)
    symbol: str = ""
    direction: int = 0
    quantity: int = 0
    price: float = 0.0
    commission: float = 0.0
    stamp_duty: float = 0.0
