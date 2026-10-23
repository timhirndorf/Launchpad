"""Futures curves from ICE's public (delayed) product pages."""

from dataclasses import dataclass

from launchpad.cache import ttl_cache
from launchpad.sources.base import get

URL = "https://www.ice.com/marketdata/api/productguide/charting/contract-data"

# Three Month Euribor futures (ICE Futures Europe)
EURIBOR_3M = (15275, 17455)  # (productId, hubId)


@dataclass
class Contract:
    strip: str  # e.g. "Dec26"
    last: float
    prev: float  # previous settlement


def parse_contracts(payload: list[dict]) -> list[Contract]:
    contracts = []
    for c in payload:
        last = c.get("lastPrice")
        if last is None:
            continue
        # `change` is the percent change of the price, not the price change.
        prev = last / (1 + (c.get("change") or 0) / 100)
        contracts.append(Contract(strip=c["marketStrip"], last=last, prev=prev))
    return contracts


@ttl_cache(seconds=60)
def fetch_contracts(product: tuple[int, int]) -> list[Contract]:
    product_id, hub_id = product
    return parse_contracts(get(URL, params={"productId": product_id, "hubId": hub_id}).json())
