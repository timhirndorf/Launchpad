"""Fed policy rates from the New York Fed's markets API (official, no key needed)."""

from dataclasses import dataclass

from launchpad.cache import ttl_cache
from launchpad.sources.base import Observation, get

URL = "https://markets.newyorkfed.org/api/rates/unsecured/effr/last/2.json"


@dataclass
class FedRates:
    effr: Observation
    target_low: float
    target_high: float


def parse_effr(payload: dict) -> FedRates:
    latest, *rest = payload["refRates"]  # newest first
    return FedRates(
        effr=Observation(latest["percentRate"], latest["effectiveDate"],
                         rest[0]["percentRate"] if rest else None),
        target_low=latest["targetRateFrom"],
        target_high=latest["targetRateTo"],
    )


@ttl_cache(seconds=3600)
def fetch_fed_rates() -> FedRates:
    return parse_effr(get(URL).json())
