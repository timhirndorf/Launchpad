import math

import pandas as pd

from launchpad.panels.base import Panel
from launchpad.sources.base import Quote
from launchpad.sources.yahoo import parse_quote

TZ = "Europe/Berlin"


def closes(values: list[float]) -> pd.Series:
    index = pd.DatetimeIndex(["2026-10-21", "2026-10-22", "2026-10-23"]).tz_localize(TZ)
    return pd.Series(values, index=index, dtype=float)


def meta(price, prev=None, time="2026-10-23 18:00"):
    return {"regularMarketPrice": price, "regularMarketTime": pd.Timestamp(time, tz=TZ),
            "chartPreviousClose": prev}


def test_previous_close_is_last_daily_close_before_session():
    q = parse_quote("^GDAXI", closes([100, 110, 112]), meta(115))
    assert q.last == 115 and q.prev_close == 110 and q.as_of == "2026-10-23"


def test_empty_close_for_current_session_is_ignored():
    # Yahoo often has the latest European bar with an empty close.
    q = parse_quote("^GDAXI", closes([100, 110, math.nan]), meta(115))
    assert q.last == 115 and q.prev_close == 110


def test_falls_back_to_chart_previous_close_without_earlier_bars():
    q = parse_quote("EURUSD=X", pd.Series(dtype=float), meta(1.12, prev=1.10))
    assert q.prev_close == 1.10


def test_no_price_means_no_quote():
    assert parse_quote("X", closes([1, 2, 3]), {}) is None
    assert parse_quote("X", pd.Series(dtype=float), meta(5, prev=None)) is None


def test_price_panel_shows_percent_change():
    panel = Panel(id="p", title="P", instruments={"A": "Alpha"})
    row = panel.render({"A": Quote("A", last=110, prev_close=100, as_of="2026-10-23")})["rows"][0]
    assert row["change"] == 10 and row["pct_change"] == 10


def test_yield_panel_shows_change_in_bp():
    panel = Panel(id="r", title="R", instruments={"^TNX": "10Y"}, kind="yield", decimals=3)
    row = panel.render({"^TNX": Quote("^TNX", last=4.988, prev_close=4.953, as_of="2026-10-23")})["rows"][0]
    assert row["change"] == 3.5 and row["pct_change"] is None


def test_grouped_panel_keeps_group_order():
    panel = Panel(id="i", title="I", groups={"Americas": {"A": "a", "B": "b"}, "EMEA": {"C": "c"}})
    assert panel.symbols == ["A", "B", "C"]
    assert [r["group"] for r in panel.render({})["rows"]] == ["Americas", "Americas", "EMEA"]


def test_missing_quote_renders_empty_row():
    panel = Panel(id="p", title="P", instruments={"A": "Alpha"})
    assert panel.render({})["rows"][0]["last"] is None


def test_precision_overrides_panel_decimals():
    panel = Panel(id="fx", title="FX", instruments={"EURUSD=X": "EUR/USD", "USDJPY=X": "USD/JPY"},
                  decimals=4, precision={"USDJPY=X": 2})
    rows = panel.render({
        "EURUSD=X": Quote("EURUSD=X", last=1.12044, prev_close=1.1222, as_of="2026-10-23"),
        "USDJPY=X": Quote("USDJPY=X", last=156.8143, prev_close=156.775, as_of="2026-10-23"),
    })["rows"]
    assert [(r["decimals"], r["last"]) for r in rows] == [(4, 1.1204), (2, 156.81)]
