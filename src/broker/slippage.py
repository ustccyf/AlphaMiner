from dataclasses import dataclass


@dataclass
class SlippageModel:
    method: str = "percent"  # percent | fixed
    value: float = 0.001  # 0.1%

    def apply(self, price: float, direction: int) -> float:
        if self.method == "percent":
            return price * (1 + direction * self.value)
        elif self.method == "fixed":
            return price + direction * self.value
        return price
