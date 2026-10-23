from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from launchpad.panels.calendar import calendar_rows, decimals, format_value, is_shown, surprise_class
from launchpad.sources.fxstreet import Release, parse_events, period_label

BERLIN = ZoneInfo("Europe/Berlin")


def release(**overrides) -> Release:
    defaults = dict(when=datetime(2026, 10, 30, 13, 0, tzinfo=timezone.utc), country="DE",
                    name="Consumer Price Index (YoY)", importance="HIGH", period="Oct",
                    actual=None, consensus=None, previous=3.3, unit="%", scale="",
                    all_day=False, tentative=False)
    return Release(**{**defaults, **overrides})


def test_parse_events_sorts_and_maps_fields():
    payload = [
        {"dateUtc": "2026-10-30T13:00:00Z", "countryCode": "DE", "name": "Consumer Price Index (YoY)",
         "volatility": "HIGH", "periodDateUtc": "2026-10-01T00:00:00Z", "periodType": "MONTH",
         "actual": None, "consensus": None, "previous": 3.3, "unit": "%", "potency": "ZERO",
         "isAllDay": False, "isTentative": False},
        {"dateUtc": "2026-10-02T12:30:00Z", "countryCode": "US", "name": "Nonfarm Payrolls",
         "volatility": "HIGH", "periodDateUtc": "2026-09-01T00:00:00Z", "periodType": "MONTH",
         "actual": 29.0, "consensus": 90.0, "previous": 162.0, "unit": None, "potency": "K"},
    ]
    nfp, cpi = parse_events(payload)
    assert nfp.name == "Nonfarm Payrolls" and nfp.scale == "K" and nfp.period == "Sep"
    assert cpi.scale == "" and cpi.period == "Oct"


def test_period_labels():
    assert period_label("2026-07-01T00:00:00Z", "QUARTER") == "Q3"
    assert period_label("2026-09-01T00:00:00Z", "MONTH") == "Sep"
    assert period_label(None, None) == ""


def test_importance_filter_per_country():
    assert is_shown(release(country="DE", importance="MEDIUM"))
    assert not is_shown(release(country="US", importance="MEDIUM"))
    assert not is_shown(release(country="DE", importance="LOW"))


def test_value_formatting():
    assert decimals(50.0, 50.5, None) == 1
    assert format_value(29.0, None, "K", 0) == "29K"
    assert format_value(-2.5, "€", "B", 1) == "-€2.5B"
    assert format_value(3.3, "%", "", 1) == "3.3%"
    assert format_value(None, "%", "", 1) is None


def test_surprise_is_direction_vs_consensus():
    assert surprise_class(release(actual=3.7, consensus=3.6)) == "up"
    assert surprise_class(release(actual=29.0, consensus=90.0)) == "down"
    assert surprise_class(release(actual=0.6, consensus=0.6)) == ""
    assert surprise_class(release(actual=0.6, consensus=None)) == ""


def test_rows_are_grouped_by_local_day_and_show_local_time():
    late_us = release(country="US", when=datetime(2026, 10, 28, 23, 30, tzinfo=timezone.utc))
    rows = calendar_rows([late_us], BERLIN, today=date(2026, 10, 29))
    assert rows[0]["label"] == "00:30"  # 23:30 UTC = 00:30 in Berlin, next day
    assert rows[0]["group"] == "Thu 29 Oct · today"


def test_percent_values_keep_one_decimal():
    rows = calendar_rows([release(consensus=4.0, previous=4.0)], BERLIN, today=date(2026, 10, 30))
    assert [c["v"] for c in rows[0]["cells"][5:]] == ["4.0%", "4.0%"]
