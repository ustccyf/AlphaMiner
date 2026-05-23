from abc import ABC, abstractmethod
from typing import Dict

import pandas as pd


class Factor(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def compute(self, history: Dict[str, pd.DataFrame]) -> pd.Series:
        pass

    def winsorize(self, s: pd.Series, limits: tuple = (0.01, 0.01)) -> pd.Series:
        lower = s.quantile(limits[0])
        upper = s.quantile(1 - limits[1])
        return s.clip(lower, upper)

    def standardize(self, s: pd.Series) -> pd.Series:
        std = s.std()
        if std == 0:
            return pd.Series(0.0, index=s.index)
        return (s - s.mean()) / std
