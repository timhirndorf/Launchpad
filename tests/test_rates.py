from datetime import date

import pytest

from launchpad.panels.base import bp
from launchpad.panels.central_banks import expectation_row, fed_funds_contracts
from launchpad.sources import cnbc, ecb, euribor, ice, nyfed
from launchpad.sources.base import Quote


def test_cnbc_parses_yields_and_skips_unknown_symbols():
    payload = {"FormattedQuoteResult": {"FormattedQuote": [
        {"symbol": "US10Y", "code": 0, "last": "4.999%", "previous_day_closing": "4.953%",
         "change": "+0.046", "last_time": "2026-10-23T17:05:00.000-0400"},
        {"symbol": "DE3M-DE", "code": 1},
        {"symbol": "XX1Y", "code": 0, "last": "3.148%", "previous_day_closing": "UNCH"},
    ]}}
    quotes = cnbc.parse_quotes(payload)
    assert list(quotes) == ["US10Y"]
    assert quotes["US10Y"].last == 4.999 and quotes["US10Y"].as_of == "2026-10-23"
    assert quotes["US10Y"].change * 100 == pytest.approx(4.6)


def test_cnbc_previous_close_comes_from_change():
    # Real case (FR 9M): previous_day_closing is a copy of last, change is right.
    stale = {"last": "3.3314%", "previous_day_closing": "3.3314%", "change": "+0.0829"}
    assert cnbc.previous_close(stale, 3.3314) == pytest.approx(3.2485)
    assert cnbc.previous_close({"change": "UNCH", "previous_day_closing": "3.1%"}, 3.148) == 3.148
    assert cnbc.previous_close({"previous_day_closing": "4.953%"}, 4.999) == 4.953


def test_cnbc_falls_back_to_last_good_quote():
    old = Quote("DE7Y-DE", last=3.2, prev_close=3.19, as_of="2026-10-23")
    new = Quote("DE2Y-DE", last=3.05, prev_close=3.02, as_of="2026-10-26")
    stale_2y = Quote("DE2Y-DE", last=3.0, prev_close=3.0, as_of="2026-10-22")
    merged = cnbc.merge_last_good({"DE2Y-DE": new}, {"DE7Y-DE": old, "DE2Y-DE": stale_2y},
                                  ("DE2Y-DE", "DE7Y-DE", "DE30Y-DE"))
    assert merged == {"DE2Y-DE": new, "DE7Y-DE": old}


def test_nyfed_effr_and_target_range():
    payload = {"refRates": [
        {"effectiveDate": "2026-10-22", "percentRate": 3.88, "targetRateFrom": 3.75, "targetRateTo": 4.0},
        {"effectiveDate": "2026-10-21", "percentRate": 3.87, "targetRateFrom": 3.75, "targetRateTo": 4.0},
    ]}
    rates = nyfed.parse_effr(payload)
    assert (rates.effr.value, rates.effr.prev, rates.effr.date) == (3.88, 3.87, "2026-10-22")
    assert (rates.target_low, rates.target_high) == (3.75, 4.0)


def test_ecb_series_takes_latest_and_previous():
    text = "KEY,TIME_PERIOD,OBS_VALUE\nX,2026-10-23,2.5\nX,2026-10-22,2.25\n"
    obs = ecb.parse_series(text)
    assert (obs.value, obs.prev, obs.date) == (2.5, 2.25, "2026-10-23")


def test_euribor_fixings_from_html():
    html = """<tr><td>10/22/2026</td><td class="text-right">2.677 %</td></tr>
              <tr><td>10/21/2026</td><td class="text-right">2.670 %</td></tr>"""
    obs = euribor.parse_fixings(html)
    assert (obs.value, obs.prev, obs.date) == (2.677, 2.670, "2026-10-22")


def test_euribor_without_rows_raises():
    with pytest.raises(ValueError):
        euribor.parse_fixings("<html>changed layout</html>")


def test_ice_change_is_percent_of_price():
    contracts = ice.parse_contracts([
        {"marketStrip": "Nov26", "lastPrice": 97.245, "change": 0.010284362626631476},
        {"marketStrip": "Dec30", "lastPrice": None, "change": None},
    ])
    assert len(contracts) == 1
    assert contracts[0].last - contracts[0].prev == pytest.approx(0.01, abs=1e-6)


def test_fed_funds_contract_symbols_roll_over_year_end():
    contracts = fed_funds_contracts(date(2026, 11, 15), months=3)
    assert contracts == [("ZQX26.CBT", "Nov 26"), ("ZQZ26.CBT", "Dec 26"), ("ZQF27.CBT", "Jan 27")]


def test_expectation_row_implied_rate_and_priced_moves():
    implied, priced, moves, day = expectation_row("Dec 26", price=95.965, prev_price=95.97, anchor=3.88)["cells"]
    assert implied["v"] == pytest.approx(4.035)
    assert priced["v"] == pytest.approx(15.5)
    assert moves["v"] == pytest.approx(0.62)
    assert day["v"] == pytest.approx(0.5)  # price down 0.005 -> rate up 0.5bp


def test_expectation_row_without_anchor():
    _, priced, moves, _ = expectation_row("Nov 26", price=97.0, prev_price=None, anchor=None)["cells"]
    assert priced["v"] is None and moves["v"] is None


def test_bp_has_no_negative_zero():
    assert str(bp(-0.00001)["v"]) == "0.0"
