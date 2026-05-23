from typing import Dict, List, Tuple

import pandas as pd

from .base import Factor


class MultiFactorModel:
    def __init__(self, factors: List[Tuple[Factor, float]]):
        self.factors = factors

    def score(self, history: Dict[str, pd.DataFrame]) -> pd.Series:
        total = pd.Series(0.0, dtype=float)
        for factor, weight in self.factors:
            vals = factor.compute(history)
            vals = factor.winsorize(vals)
            vals = factor.standardize(vals)
            total = total.add(vals * weight, fill_value=0)
        if total.empty:
            return total
        ranked = total.rank(ascending=True, pct=True)
        return ranked
