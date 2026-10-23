"""Shared data model for all sources."""

import math
from dataclasses import dataclass

import httpx

# Some sites reject requests without a browser-like user agent.
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/130 Safari/537.36"}


def get(url: str, headers: dict | None = None, **kwargs) -> httpx.Response:
    response = httpx.get(url, headers={**HEADERS, **(headers or {})}, timeout=10,
                         follow_redirects=True, **kwargs)
    response.raise_for_status()
    return response


@dataclass
class Quote:
    symbol: str
    last: float
    prev_close: float
    as_of: str  # session date of `last` in the exchange's time zone, YYYY-MM-DD

    @property
    def change(self) -> float:
        return self.last - self.prev_close

    @property
    def pct_change(self) -> float:
        return self.change / self.prev_close * 100 if self.prev_close else math.nan


@dataclass
class Observation:
    """One value of a published rate (policy rate, fixing, ...)."""

    value: float
    date: str  # YYYY-MM-DD
    prev: float | None = None  # previous published value, for the daily change
