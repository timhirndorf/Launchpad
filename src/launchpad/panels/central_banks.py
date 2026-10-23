"""Policy rates and market-implied rate paths for the Fed and the ECB.

Fed:  30-day fed funds futures (CBOT ZQ, via Yahoo). Each contract settles on the
      average EFFR of its month, so 100 - price is the market's expected EFFR for
      that month. Compared with today's EFFR, the difference is the priced change.
ECB:  3M Euribor futures (ICE). 100 - price is the expected 3M Euribor for the three
      months after expiry. Euribor trades a few bp above the deposit rate, so the
      priced ECB change is measured against today's 3M Euribor fixing (same basis)
      rather than against the deposit rate.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from launchpad.panels.base import bp, cell, row, safe, short_date, table
from launchpad.sources import ecb, euribor, ice, nyfed, yahoo
from launchpad.sources.base import Observation

MONTH_CODES = "FGHJKMNQUVXZ"  # futures month codes, Jan..Dec
EXPECTATION_COLUMNS = ["Implied", "Δ bp", "# 25bp", "1D bp"]


# --- policy rates -------------------------------------------------------------------

def observation_row(label: str, obs: Observation | None, group: str) -> dict:
    if obs is None:
        return row(label, [cell(None), cell(None), cell(None)], group)
    change = (obs.value - obs.prev) * 100 if obs.prev is not None else None
    return row(label, [cell(obs.value, 3), bp(change), cell(short_date(obs.date))], group)


class PolicyRates:
    id = "policy-rates"
    title = "Central Bank Rates"

    def build(self) -> dict:
        fed = safe(nyfed.fetch_fed_rates)
        target = f"{fed.target_low:.2f}–{fed.target_high:.2f}" if fed else None
        rows = [
            row("Target range", [cell(target), cell(None), cell(None)], "Fed"),
            observation_row("EFFR", fed.effr if fed else None, "Fed"),
            observation_row("Deposit rate", safe(ecb.fetch_series, ecb.DEPOSIT_RATE), "ECB"),
            observation_row("Main refi", safe(ecb.fetch_series, ecb.MRO_RATE), "ECB"),
            observation_row("Marginal lending", safe(ecb.fetch_series, ecb.MARGINAL_LENDING_RATE), "ECB"),
            observation_row("€STR", safe(ecb.fetch_series, ecb.ESTR), "ECB"),
            observation_row("3M Euribor", safe(euribor.fetch_3m), "ECB"),
        ]
        return table(self.id, self.title, ["Rate", "Chg bp", "As of"], rows)


# --- implied paths ------------------------------------------------------------------

def expectation_row(label: str, price: float, prev_price: float | None, anchor: float | None) -> dict:
    """Implied rate from a rate future (100 - price), vs the anchor rate, in bp and 25bp moves."""
    implied = 100 - price
    priced = (implied - anchor) * 100 if anchor is not None else None
    moves = priced / 25 if priced is not None else None
    day = -(price - prev_price) * 100 if prev_price is not None else None
    return row(label, [cell(implied, 3), bp(priced),
                       cell(moves, 2, signed=True, colored=True), bp(day)])


def fed_funds_contracts(start: date, months: int = 12) -> list[tuple[str, str]]:
    """(Yahoo symbol, label) for the next `months` fed funds futures, starting with `start`'s month."""
    contracts = []
    for i in range(months):
        year, month0 = divmod(start.month - 1 + i, 12)
        year += start.year
        symbol = f"ZQ{MONTH_CODES[month0]}{year % 100:02d}.CBT"
        contracts.append((symbol, date(year, month0 + 1, 1).strftime("%b %y")))
    return contracts


class FedExpectations:
    id = "fed-path"
    title = "Fed: Market-Implied Path"

    def build(self) -> dict:
        contracts = fed_funds_contracts(datetime.now(ZoneInfo("America/New_York")).date())
        quotes = yahoo.fetch_quotes(tuple(s for s, _ in contracts))
        fed = safe(nyfed.fetch_fed_rates)
        anchor = fed.effr.value if fed else None
        rows = [expectation_row(label, quotes[s].last, quotes[s].prev_close, anchor)
                for s, label in contracts if s in quotes]
        note = f"Fed funds futures (CBOT). Δ vs EFFR {anchor:.2f}%" if anchor else "Fed funds futures (CBOT)"
        return table(self.id, self.title, EXPECTATION_COLUMNS, rows, note)


class EcbExpectations:
    id = "ecb-path"
    title = "ECB: Market-Implied Path"

    def build(self) -> dict:
        contracts = ice.fetch_contracts(ice.EURIBOR_3M)[:12]
        fixing = safe(euribor.fetch_3m)
        anchor = fixing.value if fixing else None
        rows = [expectation_row(f"{c.strip[:3]} {c.strip[3:]}", c.last, c.prev, anchor) for c in contracts]
        note = (f"3M Euribor futures (ICE). Δ vs 3M Euribor fixing {anchor:.3f}%" if anchor
                else "3M Euribor futures (ICE)")
        return table(self.id, self.title, EXPECTATION_COLUMNS, rows, note)


POLICY_RATES = PolicyRates()
FED_PATH = FedExpectations()
ECB_PATH = EcbExpectations()
