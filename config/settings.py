from dataclasses import dataclass, field
from typing import List


@dataclass
class BacktestConfig:
    initial_cash: float = 1_000_000
    start_date: str = "20240101"
    end_date: str = "20241231"
    symbols: List[str] = field(default_factory=lambda: [
        "600519.SH",
        "000858.SZ",
        "000333.SZ",
        "601318.SH",
        "600036.SH",
    ])


@dataclass
class CommissionConfig:
    rate: float = 0.00025
    min_commission: float = 5.0
    stamp_duty_rate: float = 0.0005


@dataclass
class SlippageConfig:
    method: str = "percent"
    value: float = 0.001


@dataclass
class RiskConfig:
    max_position_weight: float = 0.20
    max_positions: int = 10
    stop_loss: float = 0.07
    take_profit: float = 0.0


BENCHMARKS = {
    "sh": ("000001.SH", "上证指数"),
    "hs300": ("000300.SH", "沪深300"),
    "sz50": ("000016.SH", "上证50"),
    "zz500": ("000905.SZ", "中证500"),
    "zz1000": ("000852.SH", "中证1000"),
    "cyb": ("399006.SZ", "创业板指"),
    "kc50": ("588000.SH", "科创50"),
    "szcz": ("399001.SZ", "深证成指"),
}
