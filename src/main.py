import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import BacktestConfig, CommissionConfig, SlippageConfig
from src.broker.broker import Broker
from src.broker.commission import CommissionModel
from src.broker.slippage import SlippageModel
from src.core.engine import BacktestEngine
from src.data.data_feed import DailyBarFeed
from src.data.data_source import BaostockDataSource
from src.analysis.performance import PerformanceAnalyzer
from src.analysis.reports import ReportGenerator
from src.portfolio.portfolio import Portfolio
from src.strategy.examples.ma_crossover import MACrossoverStrategy
from src.utils.logger import setup_logger


from config.settings import BENCHMARKS as BENCHMARK_MAP


def parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y%m%d")


def fetch_benchmark(source: BaostockDataSource, benchmark_code: str,
                    start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    df = source.load_symbol(benchmark_code, start_dt.date(), end_dt.date())
    return df.reset_index()[["date", "close"]]


def main():
    parser = argparse.ArgumentParser(description="A-Share Quant Backtesting System")
    parser.add_argument("--start", default="20240101", help="Start date YYYYMMDD")
    parser.add_argument("--end", default="20241231", help="End date YYYYMMDD")
    parser.add_argument("--cash", type=float, default=1_000_000, help="Initial cash")
    parser.add_argument("--strategy", default="ma_crossover",
                        choices=["ma_crossover", "multi_factor"],
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

    source = BaostockDataSource()
    data_feed = DailyBarFeed(source, symbols, start_dt.date(), end_dt.date())

    # Benchmark
    bm_code, bm_name = BENCHMARK_MAP[args.benchmark]
    print(f"  Benchmark: {bm_name} ({bm_code})")
    benchmark_df = fetch_benchmark(source, bm_code, start_dt, end_dt)
    print(f"  Benchmark data: {len(benchmark_df)} rows")

    if args.strategy == "ma_crossover":
        strategy = MACrossoverStrategy(symbols, fast=5, slow=20, data_feed=data_feed)
    else:
        from src.factors.composite import MultiFactorModel
        from src.factors.technical import MomentumFactor, VolumeRatioFactor
        from src.strategy.examples.multi_factor import MultiFactorStrategy

        model = MultiFactorModel([
            (MomentumFactor(20), 0.6),
            (VolumeRatioFactor(20), 0.4),
        ])
        strategy = MultiFactorStrategy(symbols, model, data_feed=data_feed)

    portfolio = Portfolio(initial_cash=args.cash)
    comm_cfg = CommissionConfig()
    slip_cfg = SlippageConfig()
    broker = Broker(
        commission=CommissionModel(
            rate=comm_cfg.rate,
            min_per_trade=comm_cfg.min_commission,
            stamp_duty_rate=comm_cfg.stamp_duty_rate,
        ),
        slippage=SlippageModel(
            method=slip_cfg.method,
            value=slip_cfg.value,
        ),
    )

    engine = BacktestEngine(
        data_feed=data_feed,
        strategy=strategy,
        portfolio=portfolio,
        broker=broker,
    )

    result = engine.run()

    analyzer = PerformanceAnalyzer(result.equity_curve, result.trades, benchmark_df)
    summary = analyzer.summary()

    # --- Print results ---
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

    ReportGenerator.equity_and_drawdown(
        analyzer.equity,
        benchmark_df=benchmark_df,
        benchmark_label=bm_name,
        save_path="outputs/plots/equity_curve.png",
    )
    ReportGenerator.pnl_histogram(
        analyzer.trades_df,
        save_path="outputs/plots/trade_pnl.png",
    )
    print("\n  Charts saved to outputs/plots/")


if __name__ == "__main__":
    main()
