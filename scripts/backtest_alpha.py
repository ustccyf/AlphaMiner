#!/usr/bin/env python
"""Backtest industry-standard alpha strategies and rank by excess return."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.main import run_backtest, parse_date
from config.settings import BENCHMARKS


def format_pct(v: float) -> str:
    return f"{v:+.2f}%"


def main():
    parser = argparse.ArgumentParser(description="Alpha strategy comparison")
    parser.add_argument("--start", default="20260223")
    parser.add_argument("--end", default="20260522")
    parser.add_argument("--cash", type=float, default=1_000_000)
    parser.add_argument("--benchmark", default="hs300")
    args = parser.parse_args()

    start_dt = parse_date(args.start)
    end_dt = parse_date(args.end)

    # Load universes
    from config.universe_large_cap import LARGE_CAP_SYMBOLS
    from config.universe_mid_cap import MID_CAP_SYMBOLS
    from config.universe_micro_cap import MICRO_CAP_SYMBOLS

    # Define all strategies: (key, label, symbols, strategy_func)
    # strategy_func will be called later with proper imports
    strategies = [
        ("large_baseline", "大盘基准(动量+量比)", LARGE_CAP_SYMBOLS, "multi_factor"),
        ("large_lowvol", "大盘低波", LARGE_CAP_SYMBOLS, "low_vol"),
        ("large_value", "大盘价值(低PE/PB)", LARGE_CAP_SYMBOLS, "value"),
        ("large_reversal", "大盘反转", LARGE_CAP_SYMBOLS, "reversal"),
        ("large_lowturn", "大盘低换手率", LARGE_CAP_SYMBOLS, "low_turnover"),
        ("mid_baseline", "中盘基准(动量+量比)", MID_CAP_SYMBOLS, "multi_factor"),
        ("mid_lowvol", "中盘低波", MID_CAP_SYMBOLS, "low_vol"),
        ("mid_reversal", "中盘反转", MID_CAP_SYMBOLS, "reversal"),
        ("mid_value", "中盘价值(低PE/PB)", MID_CAP_SYMBOLS, "value"),
        ("micro_baseline", "微盘基准(动量+量比)", MICRO_CAP_SYMBOLS, "multi_factor"),
        ("micro_reversal", "微盘反转", MICRO_CAP_SYMBOLS, "reversal"),
        ("micro_lowvol", "微盘低波", MICRO_CAP_SYMBOLS, "low_vol"),
        ("micro_cap", "微盘股(小市值因子)", MICRO_CAP_SYMBOLS, "micro_cap"),
        ("micro_reversal2", "微盘反转+市值", MICRO_CAP_SYMBOLS, "small_reversal"),
    ]

    print(f"Alpha Strategy Comparison")
    print(f"Period: {start_dt.date()} ~ {end_dt.date()}")
    print(f"Benchmark: {args.benchmark}\n")

    results = []
    for key, label, symbols, stype in strategies:
        print(f"  {label:<28}...", end=" ", flush=True)
        try:
            summary, _, _ = run_backtest(
                stype, symbols, start_dt, end_dt,
                initial_cash=args.cash, benchmark=args.benchmark,
            )
            results.append((label, symbols, summary))
            print(f"return={format_pct(summary['total_return_pct'])} "
                  f"excess={format_pct(summary['excess_return_pct'])} "
                  f"sharpe={summary['sharpe_ratio']:.2f}")
        except Exception as e:
            print(f"FAILED: {e}")

    # Sort by excess return
    results.sort(key=lambda x: x[2]["excess_return_pct"], reverse=True)

    bm_label = BENCHMARKS[args.benchmark][1]

    # Console
    header = f"{'Rank':<4} {'Strategy':<28} {'Return':>8} {'Excess':>8} {'Sharpe':>7} {'MaxDD':>7} {'WinRate':>7} {'Trades':>6}"
    sep = "-" * len(header)
    print(f"\n{sep}\n{header}\n{sep}")
    for i, (label, syms, s) in enumerate(results, 1):
        print(f"{i:<4} {label:<28} {format_pct(s['total_return_pct']):>8} "
              f"{format_pct(s['excess_return_pct']):>8} {s['sharpe_ratio']:>7.2f} "
              f"{s['max_drawdown_pct']:>7.2f}% {s['win_rate_pct']:>7.1f}% {s['num_trades']:>6}")
    print(sep)

    # Markdown
    md_path = Path("outputs/alpha_strategies.md")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Alpha策略超额收益排名",
        f"",
        f"> 回测区间：{start_dt.date()} ~ {end_dt.date()} | 基准：{bm_label}",
        f"",
        f"| 排名 | 策略 | 股票池 | 总收益 | 超额收益(vs {bm_label}) | Sharpe | 最大回撤 | 胜率 | 交易数 |",
        f"|------|------|--------|--------|--------------------------|--------|----------|------|--------|",
    ]
    for i, (label, syms, s) in enumerate(results, 1):
        universe = "大盘" if syms == LARGE_CAP_SYMBOLS else ("中盘" if syms == MID_CAP_SYMBOLS else "微盘")
        lines.append(
            f"| {i} | {label} | {universe}({len(syms)}只) | "
            f"{format_pct(s['total_return_pct'])} | {format_pct(s['excess_return_pct'])} | "
            f"{s['sharpe_ratio']:.2f} | {s['max_drawdown_pct']:.2f}% | "
            f"{s['win_rate_pct']:.1f}% | {s['num_trades']} |"
        )

    lines += [
        "",
        "## 策略说明",
        "",
        "| 策略 | 选股逻辑 | 数据 |",
        "|------|---------|------|",
        "| 大盘/中盘/微盘基准 | 动量(20日)+量比(20日)，固定权重0.6/0.4 | OHLCV |",
        "| 低波 | 做多20日波动率最低的股票 | OHLCV |",
        "| 反转 | 做多5日跌幅最大的股票（短期反转效应） | OHLCV |",
        "| 价值(低PE/PB) | 做多PE、PB最低的股票，1/PE+1/PB等权 | Baostock PE/PB |",
        "| 低换手率 | 做多20日均换手率最低的股票 | Baostock 换手率 |",
        "| 微盘股 | 做多20日均成交额最小的股票（市值代理因子） | OHLCV 成交额 |",
        "| 微盘反转+市值 | 微盘股universe + 5日反转因子选股 | OHLCV |",
        "",
        "## 数据说明",
        "",
        "- 大盘池：沪深300成分股（前15只）",
        "- 中盘池：中证500成分股，排除沪深300重叠（15只）",
        "- 微盘池：中证500偏小市值成分股（15只）",
        "- PE/PB/换手率数据来自 Baostock `query_history_k_data_plus`",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nReport saved to {md_path}")


if __name__ == "__main__":
    main()
