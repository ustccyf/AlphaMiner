class PriceLimit:
    REGULAR = 0.10
    ST = 0.05

    @staticmethod
    def validate(price: float, prev_close: float, is_st: bool = False) -> bool:
        limit = PriceLimit.ST if is_st else PriceLimit.REGULAR
        lower = round(prev_close * (1 - limit), 2)
        upper = round(prev_close * (1 + limit), 2)
        return lower <= price <= upper

    @staticmethod
    def clamp(price: float, prev_close: float, is_st: bool = False) -> float:
        limit = PriceLimit.ST if is_st else PriceLimit.REGULAR
        lower = round(prev_close * (1 - limit), 2)
        upper = round(prev_close * (1 + limit), 2)
        return round(max(lower, min(price, upper)), 2)
