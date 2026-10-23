"""Economic calendar from FXStreet's calendar API (unofficial, no key needed).

Chosen over Nasdaq (dates shifted by a day, m/m and y/y releases share one name),
Yahoo (no consensus, misses payrolls/CPI/ISM/PMIs) and ForexFactory (current week
only, no actuals).
"""

from dataclasses import dataclass
from datetime import date, datetime

from launchpad.cache import ttl_cache
from launchpad.sources.base import get

URL = "https://calendar-api.fxstreet.com/en/api/v1/eventDates/{start}T00:00:00Z/{end}T00:00:00Z"
IMPORTANCE = ("NONE", "LOW", "MEDIUM", "HIGH")


@dataclass
class Release:
    when: datetime  # UTC
    country: str  # FXStreet code: US, DE, FR, IT, EMU, ...
    name: str
    importance: str  # one of IMPORTANCE
    period: str  # "Sep", "Q3", "" ...
    actual: float | None
    consensus: float | None
    previous: float | None
    unit: str | None  # "%", "$", "€" or None
    scale: str  # "", "K", "M", "B"
    all_day: bool
    tentative: bool


def period_label(period_utc: str | None, period_type: str | None) -> str:
    if not period_utc:
        return ""
    d = datetime.fromisoformat(period_utc.replace("Z", "+00:00"))
    if period_type == "QUARTER":
        return f"Q{(d.month - 1) // 3 + 1}"
    if period_type == "MONTH":
        return d.strftime("%b")
    return ""


def parse_events(payload: list[dict]) -> list[Release]:
    releases = []
    for e in payload:
        releases.append(Release(
            when=datetime.fromisoformat(e["dateUtc"].replace("Z", "+00:00")),
            country=e["countryCode"],
            name=e["name"],
            importance=e.get("volatility") or "NONE",
            period=period_label(e.get("periodDateUtc"), e.get("periodType")),
            actual=e.get("actual"),
            consensus=e.get("consensus"),
            previous=e.get("previous"),
            unit=e.get("unit"),
            scale="" if e.get("potency") in (None, "ZERO") else e["potency"],
            all_day=bool(e.get("isAllDay")),
            tentative=bool(e.get("isTentative")),
        ))
    releases.sort(key=lambda r: r.when)
    return releases


@ttl_cache(seconds=300)
def fetch_calendar(start: date, end: date, countries: tuple[str, ...]) -> list[Release]:
    """All releases in [start, end) for the given countries, oldest first (cached 5 min)."""
    params = [("volatilities", v) for v in IMPORTANCE] + [("countries", c) for c in countries]
    response = get(URL.format(start=start.isoformat(), end=end.isoformat()), params=params,
                   headers={"Referer": "https://www.fxstreet.com/"})
    return parse_events(response.json())
