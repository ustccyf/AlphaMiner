import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import BacktestConfig, CommissionConfig, SlippageConfig
from src.broker.broker import Broker
from src.broker.commission import CommissionModel
from src.broker.slippage import SlippageModel
from src.core.engine import BacktestEngine, BacktestResult
from src.data.data_feed import DailyBarFeed
from src.data.data_source import BaostockDataSource
from src.analysis.performance import PerformanceAnalyzer
from src.analysis.reports import ReportGenerator
from src.portfolio.portfolio import Portfolio
from src.strategy.base import Strategy
from src.strategy.examples.ma_crossover import MACrossoverStrategy
from src.utils.logger import setup_logger

from config.settings import BENCHMARKS as BENCHMARK_MAP


def parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y%m%d")


def fetch_benchmark(source: BaostockDataSource, benchmark_code: str,
                    start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    df = source.load_symbol(benchmark_code, start_dt.date(), end_dt.date())
    return df.reset_index()[["date", "close"]]


def get_all_factors():
    from src.factors.technical import (
        MomentumFactor, VolumeRatioFactor, RsiFactor, VolatilityFactor,
        MADeviationFactor, PricePositionFactor, AmplitudeFactor, TurnoverFactor,
    )
    return [
        MomentumFactor(20), VolumeRatioFactor(20), RsiFactor(14),
        VolatilityFactor(20), MADeviationFactor(20), PricePositionFactor(20),
        AmplitudeFactor(20), TurnoverFactor(20),
    ]


def create_strategy(
    strategy_name: str,
    symbols: List[str],
    data_feed: DailyBarFeed,
    benchmark_df: Optional[pd.DataFrame] = None,
) -> Strategy:
    if strategy_name == "ma_crossover":
        return MACrossoverStrategy(symbols, fast=5, slow=20, data_feed=data_feed)
    elif strategy_name == "multi_factor":
        from src.factors.composite import MultiFactorModel
        from src.factors.technical import MomentumFactor, VolumeRatioFactor
        from src.strategy.examples.multi_factor import MultiFactorStrategy

        model = MultiFactorModel([
            (MomentumFactor(20), 0.6),
            (VolumeRatioFactor(20), 0.4),
        ])
        return MultiFactorStrategy(symbols, model, data_feed=data_feed)
    elif strategy_name == "timing_multi_factor":
        from src.factors.composite import MultiFactorModel
        from src.factors.technical import MomentumFactor, VolumeRatioFactor
        from src.strategy.timing import MarketTimer, TimingMultiFactorStrategy

        timer = MarketTimer(benchmark_df, ma_window=20)
        model = MultiFactorModel([
            (MomentumFactor(20), 0.6),
            (VolumeRatioFactor(20), 0.4),
        ])
        return TimingMultiFactorStrategy(symbols, model, timer, data_feed=data_feed)
    elif strategy_name == "ic_weighted":
        from src.strategy.examples.advanced import ICWeightedStrategy
        return ICWeightedStrategy(symbols, get_all_factors(), data_feed=data_feed)
    elif strategy_name == "ml_factor":
        from src.strategy.examples.advanced import MLFactorStrategy
        return MLFactorStrategy(symbols, get_all_factors(), data_feed=data_feed)
    elif strategy_name in ("low_vol", "reversal", "micro_cap", "small_reversal",
                           "value", "low_turnover"):
        from src.strategy.examples.alpha import (
            LowVolStrategy, ReversalStrategy, MicroCapStrategy,
            SmallCapReversalStrategy, ValueStrategy, LowTurnoverStrategy,
        )
        mapping = {
            "low_vol": LowVolStrategy,
            "reversal": ReversalStrategy,
            "micro_cap": MicroCapStrategy,
            "small_reversal": SmallCapReversalStrategy,
            "value": ValueStrategy,
            "low_turnover": LowTurnoverStrategy,
        }
        return mapping[strategy_name](symbols, data_feed=data_feed)
    else:
        raise ValueError(f"Unknown strategy: {strategy_name}")


def run_backtest(
    strategy_name: str,
    symbols: List[str],
    start_dt: datetime,
    end_dt: datetime,
    initial_cash: float = 1_000_000,
    benchmark: str = "hs300",
    save_plots: bool = False,
) -> Tuple[dict, PerformanceAnalyzer, str]:
    source = BaostockDataSource()
    data_feed = DailyBarFeed(source, symbols, start_dt.date(), end_dt.date())

    bm_code, bm_name = BENCHMARK_MAP[benchmark]
    benchmark_df = fetch_benchmark(source, bm_code, start_dt, end_dt)

    strategy = create_strategy(strategy_name, symbols, data_feed, benchmark_df)

    comm_cfg = CommissionConfig()
    slip_cfg = SlippageConfig()
    broker = Broker(
        commission=CommissionModel(
            rate=comm_cfg.rate, min_per_trade=comm_cfg.min_commission,
            stamp_duty_rate=comm_cfg.stamp_duty_rate,
        ),
        slippage=SlippageModel(method=slip_cfg.method, value=slip_cfg.value),
    )

    engine = BacktestEngine(
        data_feed=data_feed, strategy=strategy,
        portfolio=Portfolio(initial_cash=initial_cash), broker=broker,
    )
    result = engine.run()

    analyzer = PerformanceAnalyzer(result.equity_curve, result.trades, benchmark_df)
    summary = analyzer.summary()

    if save_plots:
        ReportGenerator.equity_and_drawdown(
            analyzer.equity, benchmark_df=benchmark_df, benchmark_label=bm_name,
            save_path="outputs/plots/equity_curve.png",
        )
        ReportGenerator.pnl_histogram(
            analyzer.trades_df, save_path="outputs/plots/trade_pnl.png",
        )

    return summary, analyzer, bm_name


def print_results(summary: dict, bm_name: str):
    print("\n" + "=" * 55)
    print("  Backtest Results")
    print("=" * 55)
    print(f"  {'Total Return:':<28} {summary['total_return_pct']:>8}%")
    print(f"  {'Annualized Return:':<28} {summary['annualized_return_pct']:>8}%")
    print(f"  {'Annualized Volatility:':<28} {summary['annualized_volatility_pct']:>8}%")
    print(f"  {'Sharpe Ratio:':<28} {summary['sharpe_ratio']:>8}")
    print(f"  {'Max Drawdown:':<28} {summary['max_drawdown_pct']:>8}%")
    print(f"  {'Calmar Ratio:':<28} {summary['calmar_ratio']:>8}")
    print("-" * 55)
    print(f"  Benchmark: {bm_name}")
    print(f"  {'Benchmark Return:':<28} {summary['benchmark_return_pct']:>8}%")
    print(f"  {'Excess Return (超额收益):':<28} {summary['excess_return_pct']:>8}%")
    print(f"  {'Annualized Excess:':<28} {summary['annualized_excess_pct']:>8}%")
    print(f"  {'Information Ratio:':<28} {summary['information_ratio']:>8}")
    print(f"  {'Tracking Error:':<28} {summary['tracking_error_pct']:>8}%")
    print("-" * 55)
    print(f"  {'Win Rate:':<28} {summary['win_rate_pct']:>8}%")
    print(f"  {'Avg Win/Loss Ratio:':<28} {summary['avg_win_loss_ratio']:>8}")
    print(f"  {'Total Trades:':<28} {summary['num_trades']:>8}")
    print("=" * 55)


def main():
    parser = argparse.ArgumentParser(description="A-Share Quant Backtesting System")
    parser.add_argument("--start", default="20240101", help="Start date YYYYMMDD")
    parser.add_argument("--end", default="20241231", help="End date YYYYMMDD")
    parser.add_argument("--cash", type=float, default=1_000_000, help="Initial cash")
    parser.add_argument("--strategy", default="ma_crossover",
                        choices=["ma_crossover", "multi_factor",
                                 "timing_multi_factor", "ic_weighted", "ml_factor",
                                 "low_vol", "reversal", "micro_cap", "small_reversal",
                                 "value", "low_turnover"],
                        help="Strategy to run")
    parser.add_argument("--symbols", nargs="*", default=None,
                        help="Stock symbols (e.g. 600519.SH)")
    parser.add_argument("--benchmark", default="hs300",
                        choices=list(BENCHMARK_MAP.keys()),
                        help="Benchmark index (default: hs300)")
    args = parser.parse_args()

    setup_logger("INFO")

    symbols = args.symbols or BacktestConfig().symbols
    start_dt = parse_date(args.start)
    end_dt = parse_date(args.end)

    bm_code, bm_name = BENCHMARK_MAP[args.benchmark]
    print(f"  Benchmark: {bm_name} ({bm_code})")

    summary, analyzer, bm_name = run_backtest(
        args.strategy, symbols, start_dt, end_dt,
        initial_cash=args.cash, benchmark=args.benchmark, save_plots=True,
    )
    print_results(summary, bm_name)
    print("\n  Charts saved to outputs/plots/")


if __name__ == "__main__":
    main()
