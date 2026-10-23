"""Daily par yield curves from the US Treasury (official, end of day, no key needed).

Used for real yields (TIPS), which no free source quotes intraday. The nominal curve
comes from the same file family, so breakevens (nominal - real) use one methodology.
"""

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime

from launchpad.cache import ttl_cache
from launchpad.sources.base import get

URL = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{year}/all"
NOMINAL = "daily_treasury_yield_curve"
REAL = "daily_treasury_real_yield_curve"


@dataclass
class Curve:
    date: str  # YYYY-MM-DD of the latest curve
    yields: dict[str, float]  # tenor ("5Y") -> yield in %
    prev: dict[str, float]  # same tenors, previous business day


def tenor(column: str) -> str:
    """'5 YR' -> '5Y', '1 Mo' -> '1M', '1.5 Month' -> '1.5M'."""
    number, unit = column.split(" ", 1)
    return number + ("Y" if unit.upper().startswith("Y") else "M")


def parse_curve(text: str) -> Curve:
    rows = list(csv.DictReader(io.StringIO(text)))
    rows.sort(key=lambda r: datetime.strptime(r["Date"], "%m/%d/%Y"), reverse=True)
    if len(rows) < 2:
        raise ValueError("need at least two days of curve data")

    def values(r: dict) -> dict[str, float]:
        return {tenor(k): float(v) for k, v in r.items() if k != "Date" and v not in ("", None)}

    latest = datetime.strptime(rows[0]["Date"], "%m/%d/%Y").date().isoformat()
    return Curve(date=latest, yields=values(rows[0]), prev=values(rows[1]))


@ttl_cache(seconds=3600)
def fetch_curve(kind: str) -> Curve:
    """Latest curve of `kind` (NOMINAL or REAL). Early January also reads last year's file."""
    def lines(year: int) -> list[str]:
        params = {"type": kind, "field_tdr_date_value": year, "_format": "csv"}
        return get(URL.format(year=year), params=params).text.strip().splitlines()

    year = date.today().year
    current = lines(year)
    if len(current) < 3:  # header + two days
        previous = lines(year - 1)
        current = previous[:1] + current[1:] + previous[1:]
    return parse_curve("\n".join(current))
