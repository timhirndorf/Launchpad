"""Derived rates views: spreads, US real yields / breakevens, yield curve chart."""

from launchpad.panels.base import bp, cell, row, safe, short_date, table
from launchpad.panels.rates import EURO_GOVIES, US_TREASURIES
from launchpad.sources import cnbc, treasury
from launchpad.sources.base import Quote
from launchpad.sources.treasury import Curve

# --- spreads ------------------------------------------------------------------------

# label -> (long leg, short leg) as CNBC symbols; spread = long - short
SPREADS: dict[str, dict[str, tuple[str, str]]] = {
    "Curve": {
        "US 3m10y": ("US10Y", "US3M"),
        "US 2s10s": ("US10Y", "US2Y"),
        "US 5s30s": ("US30Y", "US5Y"),
        "DE 2s10s": ("DE10Y-DE", "DE2Y-DE"),
        "DE 5s30s": ("DE30Y-DE", "DE5Y-DE"),
        "FR 2s10s": ("FR10Y-FR", "FR2Y-FR"),
        "FR 5s30s": ("FR30Y-FR", "FR5Y-FR"),
        "IT 2s10s": ("IT10Y-IT", "IT2Y-IT"),
        "IT 5s30s": ("IT30Y-IT", "IT5Y-IT"),
    },
    "10Y country spreads": {
        "OAT–Bund": ("FR10Y-FR", "DE10Y-DE"),
        "BTP–Bund": ("IT10Y-IT", "DE10Y-DE"),
        "BTP–OAT": ("IT10Y-IT", "FR10Y-FR"),
        "UST–Bund": ("US10Y", "DE10Y-DE"),
    },
}


def spread_bp(long: Quote, short: Quote) -> tuple[float, float]:
    """(spread, daily change of the spread), both in bp."""
    level = (long.last - short.last) * 100
    previous = (long.prev_close - short.prev_close) * 100
    return level, level - previous


def spread_rows(quotes: dict[str, Quote]) -> list[dict]:
    rows = []
    for group, spreads in SPREADS.items():
        for label, (long, short) in spreads.items():
            if long in quotes and short in quotes:
                level, change = spread_bp(quotes[long], quotes[short])
                rows.append(row(label, [cell(level, 1), bp(change)], group))
            else:
                rows.append(row(label, [cell(None), cell(None)], group))
    return rows


class Spreads:
    id = "spreads"
    title = "Spreads & Curve"

    def build(self) -> dict:
        symbols = tuple(dict.fromkeys(s for group in SPREADS.values() for pair in group.values() for s in pair))
        rows = spread_rows(cnbc.fetch_quotes(symbols))
        return table(self.id, self.title, ["bp", "Chg bp"], rows,
                     "Curve: long minus short tenor. Country: yield difference at 10Y.")


# --- real yields --------------------------------------------------------------------

REAL_TENORS = ["5Y", "7Y", "10Y", "20Y", "30Y"]


def diff_bp(a: float | None, b: float | None) -> float | None:
    return (a - b) * 100 if a is not None and b is not None else None


def minus(a: float | None, b: float | None) -> float | None:
    return a - b if a is not None and b is not None else None


def forward_5y5y(five: float | None, ten: float | None) -> float | None:
    """5y rate 5y forward from 5y and 10y rates (simple approximation: 2 * 10y - 5y)."""
    return 2 * ten - five if five is not None and ten is not None else None


def real_yield_rows(nominal: Curve, real: Curve) -> list[dict]:
    rows = []
    breakeven, breakeven_prev = {}, {}
    for t in REAL_TENORS:
        r, r_prev = real.yields.get(t), real.prev.get(t)
        breakeven[t] = minus(nominal.yields.get(t), r)
        breakeven_prev[t] = minus(nominal.prev.get(t), r_prev)
        rows.append(row(t, [cell(r, 2), bp(diff_bp(r, r_prev)),
                            cell(breakeven[t], 2), bp(diff_bp(breakeven[t], breakeven_prev[t]))], "TIPS"))
    fwd = forward_5y5y(breakeven["5Y"], breakeven["10Y"])
    fwd_prev = forward_5y5y(breakeven_prev["5Y"], breakeven_prev["10Y"])
    real_fwd = forward_5y5y(real.yields.get("5Y"), real.yields.get("10Y"))
    real_fwd_prev = forward_5y5y(real.prev.get("5Y"), real.prev.get("10Y"))
    rows.append(row("5y5y fwd", [cell(real_fwd, 2), bp(diff_bp(real_fwd, real_fwd_prev)),
                                 cell(fwd, 2), bp(diff_bp(fwd, fwd_prev))], "Forward"))
    return rows


class RealYields:
    id = "real-yields"
    title = "US Real Yields & Breakevens"

    def build(self) -> dict:
        nominal = treasury.fetch_curve(treasury.NOMINAL)
        real = treasury.fetch_curve(treasury.REAL)
        note = (f"US Treasury par yields, close {short_date(real.date)}. Breakeven = nominal − real "
                "(market-implied inflation). No free daily source for euro linkers.")
        return table(self.id, self.title, ["Real %", "Chg bp", "BE %", "Chg bp"],
                     real_yield_rows(nominal, real), note)


# --- yield curve chart --------------------------------------------------------------

TENORS = ["1M", "3M", "6M", "9M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y"]

# (id, legend label, {CNBC symbol: tenor})
CURVES = [
    ("US", "US Treasuries", US_TREASURIES.instruments),
    ("DE", "Germany", EURO_GOVIES.groups["Germany"]),
    ("FR", "France", EURO_GOVIES.groups["France"]),
    ("IT", "Italy", EURO_GOVIES.groups["Italy"]),
]


def curve_points(instruments: dict[str, str], quotes: dict[str, Quote]) -> dict[str, dict]:
    return {tenor: {"y": quotes[s].last, "prev": quotes[s].prev_close}
            for s, tenor in instruments.items() if s in quotes}


class YieldCurves:
    id = "yield-curves"
    title = "Yield Curves"

    def build(self) -> dict:
        symbols = tuple(s for _, _, instruments in CURVES for s in instruments)
        quotes = cnbc.fetch_quotes(symbols)
        curves = [{"id": cid, "label": label, "points": curve_points(instruments, quotes)}
                  for cid, label, instruments in CURVES]
        real = safe(treasury.fetch_curve, treasury.REAL)
        if real:
            curves.append({"id": "US-REAL", "label": "US Real (TIPS)",
                           "points": {t: {"y": y, "prev": real.prev.get(t)} for t, y in real.yields.items()}})
        note = "Nominal curves intraday (CNBC/Tradeweb); US real curve end of day (US Treasury)."
        return {"id": self.id, "title": self.title, "type": "curves", "wide": True,
                "tenors": TENORS, "curves": curves, "note": note}


SPREADS_PANEL = Spreads()
REAL_YIELDS = RealYields()
YIELD_CURVES = YieldCurves()
