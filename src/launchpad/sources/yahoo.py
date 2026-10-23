"""Price data from Yahoo Finance via yfinance.

Yahoo's data has a few traps, which is why this isn't a single yf.download() call:
- Daily bars for non-US markets often have an empty close for the latest session,
  so the live/last price comes from the chart metadata (regularMarketPrice) instead.
- Daily FX bars are shifted by a day, so for FX the previous close is the chart's
  chartPreviousClose (of a 1-day range).
- chartPreviousClose is unreliable for futures (contract rolls), so everything else
  uses the last daily close before the current session.
"""

import logging
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import yfinance as yf

from launchpad.cache import ttl_cache
from launchpad.sources.base import Quote

log = logging.getLogger(__name__)


def is_fx(symbol: str) -> bool:
    return symbol.endswith("=X")


def parse_quote(symbol: str, closes: pd.Series, meta: dict) -> Quote | None:
    """Build a Quote from daily closes (indexed in exchange time) and chart metadata."""
    last = meta.get("regularMarketPrice")
    market_time = meta.get("regularMarketTime")
    if last is None or market_time is None:
        return None

    session = pd.Timestamp(market_time).date()
    prev = meta.get("chartPreviousClose")
    earlier = closes.dropna()
    if len(earlier):
        earlier = earlier[earlier.index.date < session]
        if len(earlier):
            prev = float(earlier.iloc[-1])
    if prev is None:
        return None

    return Quote(symbol=symbol, last=float(last), prev_close=float(prev), as_of=session.isoformat())


def fetch_quote(symbol: str) -> Quote | None:
    # A 1-day range makes chartPreviousClose the previous session's close (used for FX
    # and as a fallback). Other symbols need a few weeks of daily bars to find it.
    ticker = yf.Ticker(symbol)
    history = ticker.history(period="1d" if is_fx(symbol) else "1mo", interval="1d",
                             auto_adjust=False)
    closes = pd.Series(dtype=float) if is_fx(symbol) else history.get("Close", pd.Series(dtype=float))
    return parse_quote(symbol, closes, ticker.history_metadata or {})


def _safe_fetch(symbol: str) -> Quote | None:
    try:
        return fetch_quote(symbol)
    except Exception:
        log.exception("failed to fetch %s", symbol)
        return None


@ttl_cache(seconds=60)
def fetch_quotes(symbols: tuple[str, ...]) -> dict[str, Quote]:
    """Fetch quotes for all symbols in parallel (cached for 60s). Failures are skipped."""
    with ThreadPoolExecutor(max_workers=12) as pool:
        quotes = pool.map(_safe_fetch, symbols)
    return {q.symbol: q for q in quotes if q}
