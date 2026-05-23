from abc import ABC, abstractmethod
from datetime import date
from typing import Union

import pandas as pd
from loguru import logger

from .cache_manager import CacheManager


class DataSource(ABC):
    @abstractmethod
    def load_symbol(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        ...


class AkShareDataSource(DataSource):
    COLUMN_MAP = {
        "日期": "date",
        "开盘": "open",
        "收盘": "close",
        "最高": "high",
        "最低": "low",
        "成交量": "volume",
        "成交额": "amount",
    }

    def __init__(self, cache_dir: str = "data/cache"):
        self.cache = CacheManager(cache_dir)

    def load_symbol(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        df = self.cache.read(symbol)
        if df is not None and self._covers(df, start, end):
            logger.debug(f"Cache hit: {symbol}")
            return self._slice(df, start, end)

        logger.info(f"Fetching {symbol} from AkShare: {start} ~ {end}")
        df = self._fetch(symbol, start, end)
        df = self._clean(df, symbol)
        self.cache.write(symbol, df)
        return df

    def _fetch(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        import akshare as ak

        raw_code = symbol.split(".")[0]
        return ak.stock_zh_a_hist(
            symbol=raw_code,
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="qfq",
        )

    def _clean(self, raw: pd.DataFrame, symbol: str) -> pd.DataFrame:
        df = raw.rename(columns=self.COLUMN_MAP)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").set_index("date")
        df["prev_close"] = df["close"].shift(1)
        df["symbol"] = symbol

        keep_cols = ["symbol", "open", "high", "low", "close", "volume", "amount", "prev_close"]
        return df[keep_cols]

    def _covers(self, df: pd.DataFrame, start: date, end: date) -> bool:
        idx = pd.to_datetime(df.index)
        return idx.min() <= pd.Timestamp(start) and idx.max() >= pd.Timestamp(end)

    def _slice(self, df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
        return df.loc[pd.Timestamp(start): pd.Timestamp(end)]


class BaostockDataSource(DataSource):
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache = CacheManager(cache_dir)

    def load_symbol(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        df = self.cache.read(symbol)
        if df is not None and self._covers(df, start, end):
            logger.debug(f"Cache hit: {symbol}")
            return self._slice(df, start, end)

        logger.info(f"Fetching {symbol} from Baostock: {start} ~ {end}")
        df = self._fetch(symbol, start, end)
        df = self._clean(df, symbol)
        self.cache.write(symbol, df)
        return df

    def _to_baostock_symbol(self, symbol: str) -> str:
        code, market = symbol.split(".")
        prefix = "sh" if market == "SH" else "sz"
        return f"{prefix}.{code}"

    def _fetch(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        import baostock as bs

        bs.login()
        bs_code = self._to_baostock_symbol(symbol)
        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,open,high,low,close,volume,amount,preclose",
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
            frequency="d",
            adjustflag="2",
        )

        rows = []
        while rs.next():
            rows.append(rs.get_row_data())
        bs.logout()

        return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume", "amount", "preclose"])

    def _clean(self, raw: pd.DataFrame, symbol: str) -> pd.DataFrame:
        df = raw.copy()
        for col in ["open", "high", "low", "close", "volume", "amount", "preclose"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").set_index("date")
        df = df[df["volume"] > 0]
        df["prev_close"] = df["preclose"].fillna(df["close"].shift(1))
        df["symbol"] = symbol

        keep_cols = ["symbol", "open", "high", "low", "close", "volume", "amount", "prev_close"]
        return df[keep_cols]

    def _covers(self, df: pd.DataFrame, start: date, end: date) -> bool:
        idx = pd.to_datetime(df.index)
        return idx.min() <= pd.Timestamp(start) and idx.max() >= pd.Timestamp(end)

    def _slice(self, df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
        return df.loc[pd.Timestamp(start): pd.Timestamp(end)]
