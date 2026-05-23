from dataclasses import dataclass


@dataclass
class CommissionModel:
    rate: float = 0.00025  # 万2.5
    min_per_trade: float = 5.0  # Minimum 5 RMB per trade
    stamp_duty_rate: float = 0.0005  # 0.05% on sell only

    def calculate(self, price: float, quantity: int, is_buy: bool) -> tuple:
        turnover = price * quantity
        comm = max(turnover * self.rate, self.min_per_trade)
        stamp = turnover * self.stamp_duty_rate if not is_buy else 0.0
        return round(comm, 2), round(stamp, 2)
