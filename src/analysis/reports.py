from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd


plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


class ReportGenerator:
    @staticmethod
    def equity_and_drawdown(
        equity_df: pd.DataFrame,
        benchmark_df: Optional[pd.DataFrame] = None,
        benchmark_label: str = "Benchmark",
        save_path: Optional[str] = None,
    ):
        fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

        strat_cum = equity_df["equity"] / equity_df["equity"].iloc[0]
        axes[0].plot(equity_df["time"], strat_cum, linewidth=1.2,
                     color="#1f77b4", label="Strategy")

        if benchmark_df is not None and not benchmark_df.empty:
            bm = benchmark_df.copy()
            bm["time"] = pd.to_datetime(bm["date"])
            bm = bm.sort_values("time")
            bm_cum = bm["close"] / bm["close"].iloc[0]
            axes[0].plot(bm["time"], bm_cum, linewidth=1.0,
                         color="#ff7f0e", linestyle="--", label=benchmark_label)

        axes[0].set_title("Cumulative Return", fontsize=13)
        axes[0].axhline(1.0, color="gray", linestyle="--", alpha=0.5)
        axes[0].set_ylabel("Cumulative Return")
        axes[0].legend(loc="upper left")
        axes[0].grid(True, alpha=0.3)

        peak = strat_cum.cummax()
        dd = (strat_cum - peak) / peak * 100
        axes[1].fill_between(equity_df["time"], dd, 0, color="#d62728", alpha=0.4)
        axes[1].set_title("Drawdown (%)", fontsize=13)
        axes[1].set_ylabel("%")
        axes[1].grid(True, alpha=0.3)

        axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        plt.xticks(rotation=45)
        plt.tight_layout()

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close()

    @staticmethod
    def pnl_histogram(
        trades_df: pd.DataFrame,
        save_path: Optional[str] = None,
    ):
        if trades_df.empty:
            return

        fig, ax = plt.subplots(figsize=(10, 5))
        pnl = trades_df["pnl"]
        colors = ["#d62728" if p < 0 else "#2ca02c" for p in pnl]
        ax.bar(range(len(pnl)), pnl, color=colors, alpha=0.7)
        ax.axhline(0, color="black", linewidth=0.5)
        ax.set_title("Trade P&L Distribution", fontsize=13)
        ax.set_xlabel("Trade #")
        ax.set_ylabel("P&L (RMB)")
        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close()
