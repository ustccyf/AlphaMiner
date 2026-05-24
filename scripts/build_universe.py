#!/usr/bin/env python
"""Build stock universes from Baostock index components and save to config."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import baostock as bs
from config.universe import CSI300_SYMBOLS


def bs_to_symbol(bs_code: str) -> str:
    """Convert baostock code (sh.600000) to project symbol (600000.SH)."""
    market, code = bs_code.split(".")
    return f"{code}.{'SH' if market == 'sh' else 'SZ'}"


def fetch_index_stocks(query_func, max_count: int = 20):
    """Fetch stock codes from a baostock index query function."""
    bs.login()
    rs = query_func()
    codes = []
    while rs.next():
        row = rs.get_row_data()
        codes.append(bs_to_symbol(row[1]))
        if len(codes) >= max_count:
            break
    bs.logout()
    return codes


def main():
    bs.login()

    # Large cap: sample from HS300
    print("Fetching HS300 components...")
    rs = bs.query_hs300_stocks()
    hs300_all = []
    while rs.next():
        hs300_all.append(bs_to_symbol(rs.get_row_data()[1]))
    print(f"  HS300 total: {len(hs300_all)}")

    # Mid cap: ZZ500 (not in HS300)
    print("Fetching ZZ500 components...")
    hs300_set = set(hs300_all)
    rs2 = bs.query_zz500_stocks()
    zz500 = []
    while rs2.next():
        sym = bs_to_symbol(rs2.get_row_data()[1])
        if sym not in hs300_set:
            zz500.append(sym)
        if len(zz500) >= 30:
            break
    print(f"  ZZ500 mid-cap (not in HS300): {len(zz500)}")

    # Small cap proxy: take stocks from later part of ZZ500 list
    # (ZZ500 index includes mid-to-small cap stocks)
    small_cap = zz500[15:30] if len(zz500) >= 30 else zz500[:15]

    # Save to config files
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)

    large_cap = hs300_all[:15]
    mid_cap = zz500[:15]
    micro_cap = zz500[15:30] if len(zz500) >= 30 else zz500[:15]

    for name, symbols in [("large_cap", large_cap), ("mid_cap", mid_cap), ("micro_cap", micro_cap)]:
        path = config_dir / f"universe_{name}.py"
        content = f"# Auto-generated universe: {name}\n{name.upper()}_SYMBOLS = {symbols!r}\n"
        path.write_text(content, encoding="utf-8")
        print(f"  Saved {path} ({len(symbols)} stocks)")

    # Also print the micro-cap list
    print(f"\nMicro-cap universe: {micro_cap}")
    print(f"Mid-cap universe: {mid_cap}")
    print(f"Large-cap universe: {large_cap}")

    bs.logout()


if __name__ == "__main__":
    main()
