def round_lot(qty: int) -> int:
    """Round down to nearest lot (100 shares)."""
    return (qty // 100) * 100


def date_range_intersection(ranges: list) -> list:
    """Return the intersection of multiple sorted date lists."""
    if not ranges:
        return []
    common = set(ranges[0])
    for r in ranges[1:]:
        common = common.intersection(r)
    return sorted(common)
