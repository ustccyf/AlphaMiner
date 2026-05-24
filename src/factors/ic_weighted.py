import warnings
from typing import Dict, List

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .base import Factor

warnings.filterwarnings("ignore", category=UserWarning, module="scipy.stats")


class ICWeightedModel:
    """Factor combination model that weights factors by rolling Information Coefficient.

    Each rebalance period, computes each factor's IC (rank correlation between
    factor values at the previous rebalance and subsequent forward returns), then
    weights factors proportionally to max(0, IC).
    """

    def __init__(self, factors: List[Factor]):
        self.factors = factors
        self._records: List[dict] = []
        self._ic_history: Dict[str, List[float]] = {f.name: [] for f in factors}

    def score(self, history: Dict[str, pd.DataFrame]) -> pd.Series:
        # Compute current factor values and prices
        current_vals: Dict[str, pd.Series] = {}
        current_prices: Dict[str, float] = {}
        for f in self.factors:
            current_vals[f.name] = f.compute(history)
        for sym, df in history.items():
            if not df.empty:
                current_prices[sym] = float(df["close"].iloc[-1])

        # Compute IC from the previous completed period
        if self._records:
            prev = self._records[-1]
            prev_prices = prev["prices"]
            returns = {}
            for sym in current_prices:
                if sym in prev_prices and prev_prices[sym] > 0:
                    returns[sym] = (current_prices[sym] - prev_prices[sym]) / prev_prices[sym]

            if len(returns) >= 5:
                prev_vals = prev["vals"]
                ret_series = pd.Series(returns)
                for f in self.factors:
                    fv = prev_vals.get(f.name, pd.Series(dtype=float))
                    common = fv.index.intersection(ret_series.index)
                    if len(common) >= 5:
                        fv_sub = fv[common]
                        if fv_sub.std() == 0:
                            continue
                        ic, _ = spearmanr(fv_sub, ret_series[common])
                        if not np.isnan(ic):
                            self._ic_history[f.name].append(ic)

        # Save current state for next period
        self._records.append({"vals": current_vals, "prices": current_prices})
        if len(self._records) > 10:
            self._records = self._records[-10:]

        # Weight factors by mean IC over recent periods (positive only)
        total = pd.Series(0.0, dtype=float)
        ic_weights = {}
        for f in self.factors:
            ics = self._ic_history.get(f.name, [])
            recent = ics[-3:] if len(ics) >= 3 else ics
            ic = np.mean(recent) if recent else 0.0
            ic_weights[f.name] = max(0.0, ic)

        total_w = sum(ic_weights.values())
        if total_w == 0:
            # Fall back to equal weight
            for f in self.factors:
                ic_weights[f.name] = 1.0 / len(self.factors)
            total_w = 1.0

        for f in self.factors:
            w = ic_weights[f.name] / total_w
            vals = current_vals.get(f.name, pd.Series(dtype=float))
            if vals.empty:
                continue
            vals = f.winsorize(vals)
            vals = f.standardize(vals)
            total = total.add(vals * w, fill_value=0)

        if total.empty:
            return total
        return total.rank(ascending=True, pct=True)

    def get_current_weights(self) -> Dict[str, float]:
        """Return the latest IC-based weights for inspection."""
        result = {}
        total_w = 0.0
        for f in self.factors:
            ics = self._ic_history.get(f.name, [])
            ic = max(0.0, ics[-1] if ics else 0.0)
            result[f.name] = ic
            total_w += ic
        if total_w == 0:
            return {f.name: 1.0 / len(self.factors) for f in self.factors}
        return {k: v / total_w for k, v in result.items()}
