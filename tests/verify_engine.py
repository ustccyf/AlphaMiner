"""Verify backtest engine works end-to-end using synthetic data (no network required)."""
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.types import Bar, Position
from src.core.engine import BacktestEngine, BacktestResult
from src.broker.broker import Broker, ExecutionContext
from src.broker.commission import CommissionModel
from src.broker.slippage import SlippageModel
from src.portfolio.portfolio import Portfolio
from src.strategy.base import Strategy
from src.data.data_feed import DailyBarFeed
from src.data.data_source import DataSource
from src.analysis.performance import PerformanceAnalyzer
from src.analysis.reports import ReportGenerator


class SyntheticDataSource(DataSource):
    """Generates synthetic price data without network."""
    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def load_symbol(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        days = pd.bdate_range(start, end)
        n = len(days)
        close = 100.0
        prices = []
        for i in range(n):
            daily_ret = self.rng.normal(0.0005, 0.015)
            close = close * (1 + daily_ret)
            o = close * (1 + self.rng.normal(0, 0.003))
            h = max(o, close) * (1 + abs(self.rng.normal(0, 0.005)))
            l = min(o, close) * (1 - abs(self.rng.normal(0, 0.005)))
            v = self.rng.integers(1_000_000, 10_000_000)
            amt = v * close
            prices.append({
                "symbol": symbol, "open": o, "high": h, "low": l,
                "close": close, "volume": v, "amount": amt,
                "prev_close": prices[-1]["close"] if prices else close,
            })

        df = pd.DataFrame(prices, index=days)
        df.index.name = "date"
        return df


class BuyAndHoldStrategy(Strategy):
    """Buys on first bar and holds."""
    def __init__(self, symbols):
        super().__init__("BuyAndHold")
        self.symbols = symbols
        self.bought = set()

    def init(self):
        self.bought.clear()

    def next(self, bars):
        signals = []
        for sym in self.symbols:
            if sym not in bars:
                continue
            if sym not in self.bought:
                self.bought.add(sym)
                from src.core.events import SignalEvent
                signals.append(SignalEvent(time=bars[sym].time, symbol=sym, direction=1, strength=1.0))
        return signals


def test_broker_t_plus_1():
    """Verify T+1: cannot sell shares bought on the same day."""
    broker = Broker(CommissionModel(), SlippageModel())

    bar = Bar(symbol="TEST", time=datetime(2024, 1, 2), open=10.0, high=10.5,
              low=9.8, close=10.2, volume=1000000, amount=10200000, prev_close=10.0)

    from src.core.events import OrderEvent
    ctx = ExecutionContext(cash=100000, positions={}, today_buys={})

    # Buy
    buy_order = OrderEvent(time=bar.time, symbol="TEST", direction=1, quantity=1000)
    result = broker.execute(buy_order, {"TEST": bar}, ctx)
    assert result.fill is not None, "Buy should succeed"
    assert result.cash < 100000, "Cash should decrease after buy"
    assert result.today_buys.get("TEST", 0) == 1000, "Should track today buys"

    # Try same-day sell -> should fail
    sell_order = OrderEvent(time=bar.time, symbol="TEST", direction=-1, quantity=1000)
    ctx2 = ExecutionContext(cash=result.cash, positions=result.positions, today_buys=result.today_buys)
    result2 = broker.execute(sell_order, {"TEST": bar}, ctx2)
    assert result2.fill is None, "Same-day sell should be rejected (T+1)"

    print("  [PASS] Broker T+1 test")


def test_commission():
    """Verify commission calculation."""
    model = CommissionModel(rate=0.00025, min_per_trade=5.0, stamp_duty_rate=0.0005)

    # Large trade (> 5 RMB commission)
    comm, stamp = model.calculate(10.0, 50000, is_buy=True)
    # turnover = 500000, rate = 0.00025, commission = 125
    assert comm == 125.0, f"Expected 125.0, got {comm}"
    assert stamp == 0.0, "Buy should have no stamp duty"

    # Sell should have stamp duty
    comm_s, stamp_s = model.calculate(10.0, 50000, is_buy=False)
    assert stamp_s == 250.0, f"Expected 250.0 stamp duty on sell, got {stamp_s}"

    # Small trade (minimum commission)
    comm_small, _ = model.calculate(10.0, 100, is_buy=True)  # turnover = 1000
    assert comm_small == 5.0, f"Expected min 5.0 commission, got {comm_small}"

    print("  [PASS] Commission test")


def test_price_limit():
    """Verify price limit clamping."""
    from src.broker.price_limit import PriceLimit

    prev_close = 10.0
    clamped = PriceLimit.clamp(12.0, prev_close)  # 20% -> should clamp to 11.0
    assert clamped == 11.0, f"Expected 11.0 (limit +10%), got {clamped}"

    clamped_low = PriceLimit.clamp(8.0, prev_close)  # -20% -> should clamp to 9.0
    assert clamped_low == 9.0, f"Expected 9.0 (limit -10%), got {clamped_low}"

    print("  [PASS] Price limit test")


def test_portfolio():
    """Verify portfolio signal -> order -> fill flow."""
    from src.core.events import SignalEvent, OrderEvent, FillEvent

    portfolio = Portfolio(initial_cash=100000)
    bar = Bar(symbol="TEST", time=datetime(2024, 1, 2), open=10.0, high=10.5,
              low=9.8, close=10.0, volume=1000000, amount=10000000, prev_close=10.0)

    # Buy signal
    sig = SignalEvent(time=bar.time, symbol="TEST", direction=1, strength=1.0)
    orders = portfolio.on_signal(sig, {"TEST": bar})
    assert len(orders) == 1, "Should generate one buy order"
    assert orders[0].direction == 1

    # Simulate fill
    portfolio.on_fill(
        FillEvent(time=bar.time, symbol="TEST", direction=1, quantity=orders[0].quantity,
                  price=10.0, commission=5.0, stamp_duty=0.0),
        new_cash=100000 - 10.0 * orders[0].quantity - 5.0,
        new_positions={"TEST": Position(symbol="TEST", quantity=orders[0].quantity, avg_cost=10.0)},
        new_today_buys={"TEST": orders[0].quantity},
    )

    portfolio.update(bar.time, {"TEST": bar})
    assert len(portfolio.equity_curve) == 1

    print("  [PASS] Portfolio test")


def test_end_to_end():
    """Full backtest with synthetic data."""
    symbols = ["TEST1.SH", "TEST2.SZ"]
    source = SyntheticDataSource()
    data_feed = DailyBarFeed(source, symbols, date(2024, 1, 1), date(2024, 12, 31))

    strategy = BuyAndHoldStrategy(symbols)
    portfolio = Portfolio(initial_cash=1_000_000)
    broker = Broker(CommissionModel(), SlippageModel())

    engine = BacktestEngine(
        data_feed=data_feed,
        strategy=strategy,
        portfolio=portfolio,
        broker=broker,
    )

    result = engine.run()

    analyzer = PerformanceAnalyzer(result.equity_curve, result.trades)
    summary = analyzer.summary()

    print("\n  Backtest Results (Synthetic Data):")
    for k, v in summary.items():
        if isinstance(v, float):
            print(f"    {k}: {v}")

    # Basic sanity checks
    assert len(result.equity_curve) > 0, "Should have equity curve"
    assert len(result.trades) == 0, "Buy-and-hold should have no sells"
    assert result.final_equity > 0, "Final equity should be positive"

    # Generate charts
    ReportGenerator.equity_and_drawdown(analyzer.equity, save_path="outputs/plots/equity_curve_test.png")
    ReportGenerator.pnl_histogram(analyzer.trades_df, save_path="outputs/plots/trade_pnl_test.png")
    print("  [PASS] End-to-end test")


if __name__ == "__main__":
    print("Running verification tests...\n")
    test_broker_t_plus_1()
    test_commission()
    test_price_limit()
    test_portfolio()
    test_end_to_end()
    print("\nAll tests passed!")
