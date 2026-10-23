"""Government bond yields from CNBC's quote service (Tradeweb data, intraday).

Unofficial like yfinance, but the only free source with live yields for the full
US curve and for Bunds, OATs and BTPs.

CNBC drops less liquid tenors (e.g. DE 3Y/7Y/20Y, IT 6M) for hours at a time, e.g. on
weekends. The last good quote per symbol is therefore kept on disk and used when a
symbol comes back empty; its `as_of` date makes the page show it as stale.
"""

import json
import logging
import threading
from dataclasses import asdict
from pathlib import Path

from launchpad.cache import ttl_cache
from launchpad.sources.base import Quote, get

URL = "https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol"
LAST_GOOD_FILE = Path(__file__).resolve().parents[3] / "data" / "cnbc_last_good.json"

log = logging.getLogger(__name__)
_lock = threading.Lock()


def parse_number(text: str | None) -> float | None:
    """'4.999%' -> 4.999; 'UNCH', '' or None -> None."""
    try:
        return float(text.rstrip("%").replace(",", ""))
    except (AttributeError, ValueError):
        return None


def previous_close(item: dict, last: float) -> float | None:
    """last - change. For thinly traded bills `previous_day_closing` is sometimes just a
    copy of `last` while `change` is right, so `change` wins; "UNCH" means no change."""
    if item.get("change") == "UNCH":
        return last
    change = parse_number(item.get("change"))
    if change is not None:
        return last - change
    return parse_number(item.get("previous_day_closing"))


def parse_quotes(payload: dict) -> dict[str, Quote]:
    items = payload.get("FormattedQuoteResult", {}).get("FormattedQuote", [])
    quotes = {}
    for item in items:
        last = parse_number(item.get("last"))
        prev = previous_close(item, last) if last is not None else None
        if item.get("code") != 0 or last is None or prev is None:
            continue
        quotes[item["symbol"]] = Quote(
            symbol=item["symbol"],
            last=last,
            prev_close=prev,
            as_of=(item.get("last_time") or "")[:10],
        )
    return quotes


def merge_last_good(fresh: dict[str, Quote], stored: dict[str, Quote],
                    symbols: tuple[str, ...]) -> dict[str, Quote]:
    """Fresh quotes where available, otherwise the last good stored quote."""
    return {s: fresh.get(s) or stored[s] for s in symbols if s in fresh or s in stored}


def _load_last_good() -> dict[str, Quote]:
    try:
        return {s: Quote(**q) for s, q in json.loads(LAST_GOOD_FILE.read_text()).items()}
    except FileNotFoundError:
        return {}
    except Exception:
        log.exception("ignoring unreadable %s", LAST_GOOD_FILE)
        return {}


def _save_last_good(quotes: dict[str, Quote]) -> None:
    LAST_GOOD_FILE.parent.mkdir(exist_ok=True)
    LAST_GOOD_FILE.write_text(json.dumps({s: asdict(q) for s, q in quotes.items()}, indent=1))


@ttl_cache(seconds=60)
def fetch_quotes(symbols: tuple[str, ...]) -> dict[str, Quote]:
    params = {"symbols": "|".join(symbols), "requestMethod": "itv", "noform": 1,
              "partnerId": 2, "fund": 1, "exthrs": 1, "output": "json", "events": 1}
    fresh = parse_quotes(get(URL, params=params).json())
    with _lock:  # panels fetch in parallel and share the file
        stored = _load_last_good()
        if fresh:
            _save_last_good({**stored, **fresh})
    return merge_last_good(fresh, stored, symbols)
