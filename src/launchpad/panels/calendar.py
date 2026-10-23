"""Economic calendar: recent and upcoming data releases (FXStreet)."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from launchpad.panels.base import cell, row, table
from launchpad.sources import fxstreet
from launchpad.sources.fxstreet import IMPORTANCE, Release

TIMEZONE = ZoneInfo("Europe/Berlin")
DAYS_BACK, DAYS_AHEAD = 2, 7

# FXStreet country code -> (display code, minimum importance shown)
COUNTRIES = {
    "US": ("US", "HIGH"),
    "EMU": ("EZ", "HIGH"),
    "DE": ("DE", "MEDIUM"),
    "FR": ("FR", "MEDIUM"),
    "IT": ("IT", "MEDIUM"),
}

DOTS = {"HIGH": "●●●", "MEDIUM": "●●", "LOW": "●", "NONE": ""}
COLUMNS = [
    {"label": "", "align": "left"},
    {"label": "", "align": "left"},
    {"label": "Event", "align": "left"},
    {"label": "Period", "align": "left"},
    "Actual", "Cons", "Prior",
]


def is_shown(r: Release) -> bool:
    _, minimum = COUNTRIES.get(r.country, (None, "HIGH"))
    return IMPORTANCE.index(r.importance) >= IMPORTANCE.index(minimum)


def decimals(*values: float | None) -> int:
    """Decimals needed to show all values of one release consistently (e.g. 50.0 and 50.5 -> 1)."""
    places = [len(f"{v:.3f}".rstrip("0").split(".")[1]) for v in values if v is not None]
    return max(places, default=0)


def format_value(value: float | None, unit: str | None, scale: str, places: int) -> str | None:
    if value is None:
        return None
    text = f"{value:,.{places}f}{scale}"
    if unit == "%":
        return text + "%"
    if unit:  # currency
        return ("-" if value < 0 else "") + unit + text.lstrip("-")
    return text


def surprise_class(r: Release) -> str:
    """Green if the actual came in above consensus, red if below (neutral, not 'good'/'bad')."""
    if r.actual is None or r.consensus is None or r.actual == r.consensus:
        return ""
    return "up" if r.actual > r.consensus else "down"


def release_row(r: Release, tz: ZoneInfo, today: date) -> dict:
    local = r.when.astimezone(tz)
    time = "All day" if r.all_day else "Tent." if r.tentative else local.strftime("%H:%M")
    places = decimals(r.actual, r.consensus, r.previous)
    if r.unit == "%":
        places = max(places, 1)  # 4.0%, not 4%

    def fmt(value: float | None) -> str | None:
        return format_value(value, r.unit, r.scale, places)

    return row(time, [
        cell(COUNTRIES.get(r.country, (r.country,))[0]),
        cell(DOTS[r.importance], cls="imp"),
        cell(r.name),
        cell(r.period),
        cell(fmt(r.actual), cls=surprise_class(r)),
        cell(fmt(r.consensus)),
        cell(fmt(r.previous)),
    ], group=day_label(local.date(), today))


def day_label(day: date, today: date) -> str:
    label = day.strftime("%a %d %b")
    return f"{label} · today" if day == today else label


def calendar_rows(releases: list[Release], tz: ZoneInfo, today: date) -> list[dict]:
    return [release_row(r, tz, today) for r in releases if is_shown(r)]


class EconomicCalendar:
    id = "eco-calendar"
    title = "Economic Calendar"

    def build(self) -> dict:
        today = datetime.now(TIMEZONE).date()
        start, end = today - timedelta(days=DAYS_BACK), today + timedelta(days=DAYS_AHEAD + 1)
        # Fetch a day extra on each side: the API works in UTC days, we group by local days.
        releases = fxstreet.fetch_calendar(start - timedelta(days=1), end + timedelta(days=1),
                                           tuple(COUNTRIES))
        releases = [r for r in releases if start <= r.when.astimezone(TIMEZONE).date() < end]
        note = (f"Times in {TIMEZONE.key}. Actual green/red = above/below consensus. "
                "US/EZ: high importance only; DE/FR/IT: medium and high. Source: FXStreet")
        return table(self.id, self.title, COLUMNS, calendar_rows(releases, TIMEZONE, today), note,
                     wide=True)


ECO_CALENDAR = EconomicCalendar()
