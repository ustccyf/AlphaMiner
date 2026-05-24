#!/usr/bin/env python
"""Compare multiple strategies on the same backtest period and generate a report."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.main import run_backtest, parse_date, get_all_factors
from config.settings import BacktestConfig, BENCHMARKS


STRATEGIES = [
    ("multi_factor", "固定权重(动量+量比)"),
    ("timing_multi_factor", "择时+固定权重"),
    ("ic_weighted", "IC动态权重"),
    ("ml_factor", "Ridge回归"),
]


def format_pct(v: float) -> str:
    return f"{v:+.2f}%"


def main():
    parser = argparse.ArgumentParser(description="Compare strategies")
    parser.add_argument("--start", default="20260223", help="Start date YYYYMMDD")
    parser.add_argument("--end", default="20260522", help="End date YYYYMMDD")
    parser.add_argument("--cash", type=float, default=1_000_000, help="Initial cash")
    parser.add_argument("--benchmark", default="hs300",
                        choices=list(BENCHMARKS.keys()))
    parser.add_argument("--symbols", nargs="*", default=None,
                        help="Stock symbols")
    args = parser.parse_args()

    symbols = args.symbols or BacktestConfig().symbols
    start_dt = parse_date(args.start)
    end_dt = parse_date(args.end)

    print(f"Comparing strategies: {start_dt.date()} ~ {end_dt.date()}")
    print(f"Stocks: {symbols}")
    print(f"Benchmark: {args.benchmark}")
    print()

    results = []
    for key, label in STRATEGIES:
        print(f"Running {label} ({key})...", end=" ", flush=True)
        try:
            summary, _, bm_name = run_backtest(
                key, symbols, start_dt, end_dt,
                initial_cash=args.cash, benchmark=args.benchmark,
            )
            results.append((key, label, summary))
            print(f"OK (return={format_pct(summary['total_return_pct'])})")
        except Exception as e:
            print(f"FAILED: {e}")

    # Console table
    header = f"{'Strategy':<22} {'Return':>8} {'Sharpe':>7} {'MaxDD':>7} {'Calmar':>7} {'Excess':>8} {'IR':>6} {'WinRate':>7} {'Trades':>6}"
    sep = "-" * len(header)

    print(f"\n{sep}")
    print(header)
    print(sep)
    for key, label, s in results:
        print(f"{label:<22} {format_pct(s['total_return_pct']):>8} "
              f"{s['sharpe_ratio']:>7} {s['max_drawdown_pct']:>7}% "
              f"{s['calmar_ratio']:>7} {format_pct(s['excess_return_pct']):>8} "
              f"{s['information_ratio']:>6} {s['win_rate_pct']:>7}% {s['num_trades']:>6}")
    print(sep)

    # Markdown report
    md_path = Path("outputs/strategy_comparison.md")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    bm_label = BENCHMARKS[args.benchmark][1]

    lines = [
        f"# 策略对比回测报告",
        "",
        f"> 回测区间：{start_dt.date()} ~ {end_dt.date()} | 股票池：{len(symbols)}只 | 基准：{bm_label}",
        "",
        "## 绩效对比",
        "",
        "| 策略 | 总收益 | Sharpe | 最大回撤 | Calmar | 超额收益(vs {}) | IR | 胜率 | 交易数 |".format(bm_label),
        "|------|--------|--------|----------|--------|-----------------|-----|------|--------|",
    ]
    for key, label, s in results:
        lines.append(
            f"| {label} | {format_pct(s['total_return_pct'])} | {s['sharpe_ratio']} | "
            f"{s['max_drawdown_pct']}% | {s['calmar_ratio']} | "
            f"{format_pct(s['excess_return_pct'])} | {s['information_ratio']} | "
            f"{s['win_rate_pct']}% | {s['num_trades']} |"
        )

    lines += [
        "",
        "## 策略说明",
        "",
        "| 策略 | 因子 | 权重 | 择时 |",
        "|------|------|------|------|",
        "| 固定权重 | 动量(20日) + 量比(20日) | 0.6 / 0.4 固定 | 无 |",
        "| 择时+固定权重 | 动量(20日) + 量比(20日) | 0.6 / 0.4 固定 | 沪深300 MA20 |",
        "| IC动态权重 | 全部8个因子 | 滚动IC动态调整 | 无 |",
        f"| Ridge回归 | 全部8个因子 | Ridge回归系数 | 无 |",
    ]

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nReport saved to {md_path}")


if __name__ == "__main__":
    main()
