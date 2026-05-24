from typing import List, Optional

import numpy as np
import pandas as pd

from ..core.types import EquityPoint, TradeRecord


class PerformanceAnalyzer:
    def __init__(
        self,
        equity_curve: List[EquityPoint],
        trades: List[TradeRecord],
        benchmark: Optional[pd.DataFrame] = None,
        trading_days: int = 252,
    ):
        self.trading_days = trading_days
        self.equity = pd.DataFrame(
            [(e.time, e.total, e.returns) for e in equity_curve],
            columns=["time", "equity", "returns"],
        )
        self.trades_df = pd.DataFrame(
            [
                (t.time, t.symbol, t.direction, t.quantity, t.price, t.commission,
                 t.stamp_duty, t.pnl)
                for t in trades
            ],
            columns=["time", "symbol", "direction", "quantity", "price",
                     "commission", "stamp_duty", "pnl"],
        )
        self._benchmark = None
        if benchmark is not None and not benchmark.empty:
            self._align_benchmark(benchmark)

    def _align_benchmark(self, benchmark: pd.DataFrame):
        bm = benchmark.rename(columns={"date": "time"})
        bm["time"] = pd.to_datetime(bm["time"])
        merged = self.equity.merge(bm[["time", "close"]], on="time", how="left")
        merged["bm_return"] = merged["close"].pct_change()
        self._benchmark = merged.dropna(subset=["bm_return"])

    # --- Benchmark-relative metrics ---

    def excess_return(self) -> float:
        if self._benchmark is None:
            return 0.0
        strat_cum = (1 + self._benchmark["returns"]).prod()
        bench_cum = (1 + self._benchmark["bm_return"]).prod()
        return float(strat_cum - bench_cum)

    def annualized_excess_return(self) -> float:
        if self._benchmark is None:
            return 0.0
        n = len(self._benchmark)
        if n < 2:
            return 0.0
        return float((1 + self.excess_return()) ** (self.trading_days / n) - 1)

    def tracking_error(self) -> float:
        if self._benchmark is None:
            return 0.0
        diff = self._benchmark["returns"] - self._benchmark["bm_return"]
        return float(diff.std() * np.sqrt(self.trading_days))

    def information_ratio(self) -> float:
        if self._benchmark is None:
            return 0.0
        diff = self._benchmark["returns"] - self._benchmark["bm_return"]
        std_diff = diff.std()
        if std_diff < 1e-12:
            return 0.0
        return float(np.sqrt(self.trading_days) * diff.mean() / std_diff)

    def max_drawdown(self) -> float:
        if self.equity.empty:
            return 0.0
        cumulative = (1 + self.equity["returns"]).cumprod()
        peak = cumulative.cummax()
        dd = (cumulative - peak) / peak
        return float(dd.min())

    def benchmark_max_drawdown(self) -> float:
        if self._benchmark is None:
            return 0.0
        cumulative = (1 + self._benchmark["bm_return"]).cumprod()
        peak = cumulative.cummax()
        dd = (cumulative - peak) / peak
        return float(dd.min())

    # --- Standalone metrics ---

    def total_return(self) -> float:
        if self.equity.empty:
            return 0.0
        return float(self.equity["equity"].iloc[-1] / self.equity["equity"].iloc[0] - 1)

    def benchmark_total_return(self) -> float:
        if self._benchmark is None:
            return 0.0
        return float((1 + self._benchmark["bm_return"]).prod() - 1)

    def annualized_return(self) -> float:
        n = len(self.equity)
        if n < 2:
            return 0.0
        return float((1 + self.total_return()) ** (self.trading_days / n) - 1)

    def benchmark_annualized_return(self) -> float:
        if self._benchmark is None:
            return 0.0
        n = len(self._benchmark)
        if n < 2:
            return 0.0
        return float((1 + self.benchmark_total_return()) ** (self.trading_days / n) - 1)

    def annualized_volatility(self) -> float:
        if len(self.equity) < 2:
            return 0.0
        return float(self.equity["returns"].std() * np.sqrt(self.trading_days))

    def sharpe_ratio(self, risk_free: float = 0.02) -> float:
        if len(self.equity) < 2:
            return 0.0
        returns = self.equity["returns"]
        if returns.std() < 1e-12:
            return 0.0
        excess = returns - risk_free / self.trading_days
        std_excess = excess.std()
        if std_excess < 1e-12:
            return 0.0
        return float(np.sqrt(self.trading_days) * excess.mean() / std_excess)

    def calmar_ratio(self) -> float:
        mdd = self.max_drawdown()
        if abs(mdd) < 1e-12:
            return 0.0
        return self.annualized_return() / abs(mdd)

    def win_rate(self) -> float:
        if self.trades_df.empty:
            return 0.0
        wins = (self.trades_df["pnl"] > 0).sum()
        return float(wins / len(self.trades_df))

    def avg_win_loss_ratio(self) -> float:
        if self.trades_df.empty:
            return 0.0
        wins = self.trades_df[self.trades_df["pnl"] > 0]["pnl"]
        losses = self.trades_df[self.trades_df["pnl"] <= 0]["pnl"]
        if wins.empty or losses.empty:
            return 0.0
        return float(wins.mean() / abs(losses.mean()))

    def summary(self) -> dict:
        s = {
            "total_return_pct": round(self.total_return() * 100, 2),
            "annualized_return_pct": round(self.annualized_return() * 100, 2),
            "annualized_volatility_pct": round(self.annualized_volatility() * 100, 2),
            "sharpe_ratio": round(self.sharpe_ratio(), 3),
            "max_drawdown_pct": round(self.max_drawdown() * 100, 2),
            "calmar_ratio": round(self.calmar_ratio(), 3),
            "win_rate_pct": round(self.win_rate() * 100, 2),
            "avg_win_loss_ratio": round(self.avg_win_loss_ratio(), 3),
            "num_trades": len(self.trades_df),
        }
        if self._benchmark is not None:
            s["benchmark_return_pct"] = round(self.benchmark_total_return() * 100, 2)
            s["excess_return_pct"] = round(self.excess_return() * 100, 2)
            s["annualized_excess_pct"] = round(self.annualized_excess_return() * 100, 2)
            s["information_ratio"] = round(self.information_ratio(), 3)
            s["tracking_error_pct"] = round(self.tracking_error() * 100, 2)
        return s

    @property
    def has_benchmark(self) -> bool:
        return self._benchmark is not None
