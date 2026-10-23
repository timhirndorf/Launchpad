"""Latest 3M Euribor fixing, scraped from euribor-rates.eu.

EMMI (the administrator) has no free API and the ECB only publishes Euribor monthly.
"""

import re
from datetime import datetime

from launchpad.cache import ttl_cache
from launchpad.sources.base import Observation, get

URL = "https://www.euribor-rates.eu/en/current-euribor-rates/2/euribor-rate-3-months/"
ROW = re.compile(r"<tr>\s*<td[^>]*>(\d{1,2}/\d{1,2}/\d{4})</td>\s*<td[^>]*>\s*(-?[\d.]+)\s*%")


def parse_fixings(html: str) -> Observation:
    rows = [(datetime.strptime(d, "%m/%d/%Y").date().isoformat(), float(v)) for d, v in ROW.findall(html)]
    if not rows:
        raise ValueError("no Euribor fixings found on page")
    rows.sort()
    prev = rows[-2][1] if len(rows) > 1 else None
    return Observation(rows[-1][1], rows[-1][0], prev)


@ttl_cache(seconds=3600)
def fetch_3m() -> Observation:
    return parse_fixings(get(URL).text)
