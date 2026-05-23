from dataclasses import dataclass, field
from typing import Dict, List, Optional, Type

from loguru import logger

from ..broker.broker import Broker, ExecutionContext
from ..data.data_feed import DailyBarFeed
from ..portfolio.portfolio import Portfolio
from ..strategy.base import Strategy
from .types import EquityPoint, TradeRecord


@dataclass
class BacktestResult:
    equity_curve: List[EquityPoint] = field(default_factory=list)
    trades: List[TradeRecord] = field(default_factory=list)
    initial_cash: float = 0.0
    final_cash: float = 0.0
    final_equity: float = 0.0


class BacktestEngine:
    def __init__(
        self,
        data_feed: DailyBarFeed,
        strategy: Strategy,
        portfolio: Portfolio,
        broker: Broker,
    ):
        self.data_feed = data_feed
        self.strategy = strategy
        self.portfolio = portfolio
        self.broker = broker
        self.result: Optional[BacktestResult] = None

    def run(self) -> BacktestResult:
        logger.info("Loading data...")
        self.data_feed.load()
        self.strategy.init()

        logger.info(f"Running backtest: {len(self.data_feed._dates)} trading days")
        while self.data_feed.has_next():
            bars = self.data_feed.next()
            now = self.data_feed.current_time()

            signals = self.strategy.next(bars)

            for signal in signals:
                orders = self.portfolio.on_signal(signal, bars)
                for order in orders:
                    ctx = ExecutionContext(
                        cash=self.portfolio.cash,
                        positions=self.portfolio.positions,
                        today_buys=self.portfolio._today_buys,
                    )
                    result = self.broker.execute(order, bars, ctx)
                    if result.fill:
                        self.portfolio.on_fill(
                            result.fill,
                            result.cash,
                            result.positions,
                            result.today_buys,
                            result.trade_record,
                        )

            self.portfolio.update(now, bars)
            self.portfolio.end_of_day()
            self.data_feed.advance()

        self.result = BacktestResult(
            equity_curve=self.portfolio.equity_curve,
            trades=self.portfolio.trades,
            initial_cash=self.portfolio.initial_cash,
            final_cash=self.portfolio.cash,
            final_equity=self.portfolio.equity_curve[-1].total if self.portfolio.equity_curve else self.portfolio.initial_cash,
        )
        logger.info("Backtest complete.")
        return self.result
