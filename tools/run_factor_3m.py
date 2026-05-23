"""Backtest all factors for the last 3 months."""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.data_source import BaostockDataSource
from src.data.data_feed import DailyBarFeed
from src.broker.broker import Broker
from src.broker.commission import CommissionModel
from src.broker.slippage import SlippageModel
from src.core.engine import BacktestEngine
from src.portfolio.portfolio import Portfolio
from src.factors.composite import MultiFactorModel
from src.factors.technical import (
    MomentumFactor, VolumeRatioFactor, RsiFactor,
    VolatilityFactor, MADeviationFactor, PricePositionFactor,
    AmplitudeFactor, TurnoverFactor,
)
from src.strategy.examples.multi_factor import MultiFactorStrategy
from src.analysis.performance import PerformanceAnalyzer
from config.settings import BENCHMARKS

SYMBOLS = ["600519.SH", "000858.SZ", "000333.SZ", "601318.SH", "600036.SH",
           "600276.SH", "601166.SH", "600900.SH", "000001.SZ", "002415.SZ",
           "300750.SZ", "600030.SH", "000651.SZ", "601888.SH", "600887.SH"]

FACTORS = [
    (MomentumFactor(20), 1.0, "做多动量最强"),
    (VolumeRatioFactor(20), 1.0, "做多放量"),
    (RsiFactor(14), 1.0, "做多RSI高"),
    (VolatilityFactor(20), -1.0, "做多低波动"),
    (MADeviationFactor(20), 1.0, "做多偏离均线上方"),
    (PricePositionFactor(20), 1.0, "做多高位"),
    (AmplitudeFactor(20), -1.0, "做多低振幅"),
    (TurnoverFactor(20), 1.0, "做多高成交额"),
]


def run_one(factor, weight, start_dt, end_dt, cash):
    source = BaostockDataSource()
    data_feed = DailyBarFeed(source, SYMBOLS, start_dt.date(), end_dt.date())
    model = MultiFactorModel([(factor, weight)])
    strategy = MultiFactorStrategy(SYMBOLS, model, data_feed=data_feed, top_n=5, rebalance_days=10)
    portfolio = Portfolio(initial_cash=cash)
    broker = Broker(
        commission=CommissionModel(rate=0.00025, min_per_trade=5.0, stamp_duty_rate=0.0005),
        slippage=SlippageModel(method="percent", value=0.001),
    )
    engine = BacktestEngine(data_feed=data_feed, strategy=strategy,
                            portfolio=portfolio, broker=broker)
    result = engine.run()

    bm_results = {}
    for bm_key, (bm_code, bm_name) in BENCHMARKS.items():
        bm_df = source.load_symbol(bm_code, start_dt.date(), end_dt.date())
        bm_df = bm_df.reset_index()[["date", "close"]]
        analyzer = PerformanceAnalyzer(result.equity_curve, result.trades, bm_df)
        s = analyzer.summary()
        bm_results[bm_key] = {
            "name": bm_name,
            "benchmark_return_pct": s.get("benchmark_return_pct", 0),
            "excess_return_pct": s.get("excess_return_pct", 0),
            "information_ratio": s.get("information_ratio", 0),
        }

    analyzer = PerformanceAnalyzer(result.equity_curve, result.trades)
    s = analyzer.summary()
    return {
        "factor_name": factor.name,
        "description": "",
        "direction": "long" if weight > 0 else "short_low",
        "total_return_pct": s["total_return_pct"],
        "annualized_return_pct": s["annualized_return_pct"],
        "sharpe_ratio": s["sharpe_ratio"],
        "max_drawdown_pct": s["max_drawdown_pct"],
        "calmar_ratio": s["calmar_ratio"],
        "win_rate_pct": s["win_rate_pct"],
        "num_trades": s["num_trades"],
        "benchmarks": bm_results,
    }


def main():
    start_dt = datetime.strptime("20260223", "%Y%m%d")
    end_dt = datetime.strptime("20260522", "%Y%m%d")
    cash = 1_000_000

    results = []
    for factor, weight, desc in FACTORS:
        print(f"Testing: {factor.name} ...")
        r = run_one(factor, weight, start_dt, end_dt, cash)
        r["description"] = desc
        results.append(r)
        print(f"  Return: {r['total_return_pct']}%, Sharpe: {r['sharpe_ratio']}, "
              f"Excess(vs HS300): {r['benchmarks']['hs300']['excess_return_pct']}%")

    out_dir = Path(__file__).resolve().parent.parent / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "factor_results_3m.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Summary
    print("\n" + "=" * 70)
    print("  最近3个月因子回测排名 (2026-02-23 ~ 2026-05-22)")
    print("=" * 70)
    ranked = sorted(results, key=lambda r: r["total_return_pct"], reverse=True)
    print(f"  {'因子':<18} {'收益':>8} {'Sharpe':>8} {'回撤':>8} {'超额(HS300)':>12} {'IR':>6}")
    print("  " + "-" * 66)
    for r in ranked:
        print(f"  {r['factor_name']:<18} {r['total_return_pct']:>7.2f}% {r['sharpe_ratio']:>7.3f} "
              f"{r['max_drawdown_pct']:>7.2f}% {r['benchmarks']['hs300']['excess_return_pct']:>11.2f}% "
              f"{r['benchmarks']['hs300']['information_ratio']:>6.3f}")

    print(f"\n  Results saved to {out_dir / 'factor_results_3m.json'}")


if __name__ == "__main__":
    main()
