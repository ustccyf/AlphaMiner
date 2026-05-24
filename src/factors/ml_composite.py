from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from .base import Factor


class MLFactorModel:
    """Factor combination model using Ridge regression.

    Builds a training set of (factor_values → forward_return) pairs from past
    rebalance periods, trains a Ridge model on standardized features, and
    predicts expected returns for the current stock universe.
    """

    def __init__(self, factors: List[Factor], alpha: float = 10.0):
        self.factors = factors
        self.alpha = alpha
        self._records: List[dict] = []
        self._scaler = StandardScaler()

    def _standardize_vals(self, raw_vals: Dict[str, pd.Series]) -> Dict[str, pd.Series]:
        result = {}
        for f in self.factors:
            vals = raw_vals.get(f.name, pd.Series(dtype=float))
            if vals.empty:
                result[f.name] = vals
                continue
            vals = f.winsorize(vals)
            vals = f.standardize(vals)
            result[f.name] = vals
        return result

    def score(self, history: Dict[str, pd.DataFrame]) -> pd.Series:
        current_vals_raw: Dict[str, pd.Series] = {}
        current_prices: Dict[str, float] = {}
        for f in self.factors:
            current_vals_raw[f.name] = f.compute(history)
        for sym, df in history.items():
            if not df.empty:
                current_prices[sym] = float(df["close"].iloc[-1])

        current_vals_std = self._standardize_vals(current_vals_raw)

        # Update training data from the previous completed period
        if self._records:
            prev = self._records[-1]
            prev_prices = prev["prices"]
            returns = {}
            for sym in current_prices:
                if sym in prev_prices and prev_prices[sym] > 0:
                    returns[sym] = (current_prices[sym] - prev_prices[sym]) / prev_prices[sym]

            prev_vals = prev["vals_std"]
            syms = list(set.intersection(
                set(returns.keys()),
                *[set(prev_vals[f.name].index) for f in self.factors]
            ))
            if len(syms) >= 5:
                features = []
                targets = []
                for sym in syms:
                    feats = [prev_vals[f.name].get(sym, 0.0) for f in self.factors]
                    features.append(feats)
                    targets.append(returns[sym])
                self._records[-1]["features"] = np.array(features)
                self._records[-1]["targets"] = np.array(targets)

        # Also build training samples from daily data within the history window
        daily_features, daily_targets = self._build_daily_samples(history)

        # Save current state
        self._records.append({
            "vals": current_vals_raw,
            "vals_std": current_vals_std,
            "prices": current_prices,
        })
        if len(self._records) > 60:
            self._records = self._records[-60:]

        # Gather all training data: rebalance-period + daily samples
        all_X = list(daily_features) if len(daily_features) > 0 else []
        all_y = list(daily_targets) if len(daily_targets) > 0 else []
        for rec in self._records:
            if "features" in rec and len(rec["features"]) > 0:
                all_X.append(rec["features"])
                all_y.append(rec["targets"])

        total_samples = sum(len(arr) for arr in all_y)
        if total_samples < 20:
            return pd.Series(dtype=float)

        X = np.vstack(all_X)
        y = np.hstack(all_y)

        self._scaler.fit(X)
        X_scaled = self._scaler.transform(X)

        self._model = Ridge(alpha=self.alpha)
        self._model.fit(X_scaled, y)

        current_syms = list(set.intersection(
            *[set(current_vals_std[f.name].index) for f in self.factors]
        ))
        if not current_syms:
            return pd.Series(dtype=float)

        X_pred = np.array([
            [current_vals_std[f.name].get(sym, 0.0) for f in self.factors]
            for sym in current_syms
        ])
        X_pred_scaled = self._scaler.transform(X_pred)
        preds = self._model.predict(X_pred_scaled)

        result = pd.Series(preds, index=current_syms)
        return result.rank(ascending=True, pct=True)

    def _build_daily_samples(self, history: Dict[str, pd.DataFrame]):
        """Build training samples from daily data for a larger training set."""
        features_list = []
        targets_list = []
        forward_days = 5

        for sym, df in history.items():
            if len(df) < 30:
                continue
            for i in range(10, len(df) - forward_days):
                window = df.iloc[max(0, i - 30):i + 1]
                future_price = float(df["close"].iloc[i + forward_days])
                current_price = float(df["close"].iloc[i])
                if current_price <= 0:
                    continue
                fwd_return = (future_price - current_price) / current_price

                # Compute factor values on this window
                single_hist = {sym: window}
                vals = {}
                valid = True
                for f in self.factors:
                    fv = f.compute(single_hist)
                    if fv.empty or sym not in fv.index:
                        valid = False
                        break
                    vals[f.name] = fv[sym]
                if not valid:
                    continue

                # Standardize across all stocks isn't possible with single-stock
                # view, so store raw values — they'll be standardized globally
                feats = [vals.get(f.name, 0.0) for f in self.factors]
                features_list.append(feats)
                targets_list.append(fwd_return)

        if len(features_list) < 10:
            return [], []

        # Standardize features across the daily sample set
        X = np.array(features_list)
        y = np.array(targets_list)

        # Winsorize + standardize per factor
        for j, f in enumerate(self.factors):
            col = X[:, j]
            lower = np.percentile(col, 1)
            upper = np.percentile(col, 99)
            col = np.clip(col, lower, upper)
            std = np.std(col)
            if std > 0:
                col = (col - np.mean(col)) / std
            else:
                col = np.zeros_like(col)
            X[:, j] = col

        return [X], [y]

    def get_feature_importance(self) -> Dict[str, float]:
        return {f.name: float(c) for f, c in zip(self.factors, self._model.coef_)}
