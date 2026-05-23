from pathlib import Path
from typing import Optional

import pandas as pd


class CacheManager:
    def __init__(self, cache_dir: str = "data/cache"):
        self.root = Path(cache_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, symbol: str) -> Path:
        return self.root / f"{symbol.replace('.', '_')}.parquet"

    def read(self, symbol: str) -> Optional[pd.DataFrame]:
        path = self._path(symbol)
        if not path.exists():
            return None
        df = pd.read_parquet(path)
        df.index = pd.to_datetime(df.index)
        return df

    def write(self, symbol: str, df: pd.DataFrame) -> None:
        path = self._path(symbol)
        df.to_parquet(path, index=True)

    def exists(self, symbol: str) -> bool:
        return self._path(symbol).exists()
