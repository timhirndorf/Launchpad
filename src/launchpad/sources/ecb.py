"""Series from the ECB Data Portal (official, no key needed)."""

import csv
import io

from launchpad.cache import ttl_cache
from launchpad.sources.base import Observation, get

URL = "https://data-api.ecb.europa.eu/service/data/{key}"

DEPOSIT_RATE = "FM/D.U2.EUR.4F.KR.DFR.LEV"
MRO_RATE = "FM/D.U2.EUR.4F.KR.MRR_FR.LEV"
MARGINAL_LENDING_RATE = "FM/D.U2.EUR.4F.KR.MLFR.LEV"
ESTR = "EST/B.EU000A2X2A25.WT"


def parse_series(text: str) -> Observation:
    rows = [r for r in csv.DictReader(io.StringIO(text)) if r.get("OBS_VALUE")]
    rows.sort(key=lambda r: r["TIME_PERIOD"])
    latest = rows[-1]
    prev = float(rows[-2]["OBS_VALUE"]) if len(rows) > 1 else None
    return Observation(float(latest["OBS_VALUE"]), latest["TIME_PERIOD"], prev)


@ttl_cache(seconds=3600)
def fetch_series(key: str) -> Observation:
    return parse_series(get(URL.format(key=key), params={"lastNObservations": 2, "format": "csvdata"}).text)
