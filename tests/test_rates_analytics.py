import pytest

from launchpad.panels.rates_analytics import (
    SPREADS, curve_points, forward_5y5y, real_yield_rows, spread_bp, spread_rows,
)
from launchpad.sources.base import Quote
from launchpad.sources.treasury import Curve, parse_curve, tenor


def q(symbol, last, prev):
    return Quote(symbol, last=last, prev_close=prev, as_of="2026-10-23")


def test_spread_level_and_change_in_bp():
    level, change = spread_bp(q("IT10Y-IT", 4.587, 4.582), q("DE10Y-DE", 3.354, 3.343))
    assert level == pytest.approx(123.3)
    assert change == pytest.approx(-0.6)  # BTP +0.5bp, Bund +1.1bp -> spread tighter


def test_inverted_curve_is_negative():
    level, _ = spread_bp(q("US10Y", 4.0, 4.0), q("US2Y", 4.5, 4.5))
    assert level == pytest.approx(-50.0)


def test_spread_rows_keep_missing_legs_as_empty_rows():
    rows = spread_rows({"US10Y": q("US10Y", 5.0, 4.95), "US2Y": q("US2Y", 4.69, 4.64)})
    assert len(rows) == sum(len(g) for g in SPREADS.values())
    by_label = {r["label"]: r for r in rows}
    assert by_label["US 2s10s"]["cells"][0]["v"] == pytest.approx(31.0)
    assert by_label["BTP–Bund"]["cells"][0]["v"] is None


def test_treasury_csv_parsing():
    text = ('Date,"5 YR","10 YR","1 Mo"\n'
            "10/22/2026,2.33,2.64,4.11\n"
            "10/23/2026,2.34,2.66,\n")
    curve = parse_curve(text)
    assert curve.date == "2026-10-23"
    assert curve.yields == {"5Y": 2.34, "10Y": 2.66}  # empty cells are skipped
    assert curve.prev["1M"] == 4.11
    assert tenor("1.5 Month") == "1.5M"


def test_breakevens_and_5y5y_forward():
    nominal = Curve("2026-10-23", {"5Y": 4.82, "10Y": 5.00}, {"5Y": 4.78, "10Y": 4.96})
    real = Curve("2026-10-23", {"5Y": 2.34, "10Y": 2.66}, {"5Y": 2.33, "10Y": 2.64})
    rows = {r["label"]: [c["v"] for c in r["cells"]] for r in real_yield_rows(nominal, real)}
    real5, real5_chg, be5, be5_chg = rows["5Y"]
    assert (real5, be5) == (2.34, pytest.approx(2.48))
    assert be5_chg == pytest.approx(3.0)  # nominal +4bp, real +1bp
    assert rows["5y5y fwd"][2] == pytest.approx(2 * 2.34 - 2.48)  # 2 * BE10 - BE5
    assert rows["7Y"] == [None, None, None, None]  # tenor missing in both curves


def test_forward_needs_both_rates():
    assert forward_5y5y(None, 2.0) is None


def test_curve_points_only_for_available_quotes():
    points = curve_points({"DE2Y-DE": "2Y", "DE3Y-DE": "3Y"}, {"DE2Y-DE": q("DE2Y-DE", 3.05, 3.03)})
    assert points == {"2Y": {"y": 3.05, "prev": 3.03}}
