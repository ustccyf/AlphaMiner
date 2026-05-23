from abc import ABC, abstractmethod
from typing import Dict, List

from ..core.events import SignalEvent
from ..core.types import Bar


class Strategy(ABC):
    def __init__(self, name: str = ""):
        self.name = name or self.__class__.__name__

    @abstractmethod
    def init(self):
        pass

    @abstractmethod
    def next(self, bars: Dict[str, Bar]) -> List[SignalEvent]:
        pass
