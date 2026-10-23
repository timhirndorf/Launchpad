"""Panel registry: the order here is the order on the page."""

from launchpad.panels.calendar import ECO_CALENDAR
from launchpad.panels.central_banks import ECB_PATH, FED_PATH, POLICY_RATES
from launchpad.panels.markets import COMMODITIES, FX, INDICES, VOL, WATCHLIST
from launchpad.panels.rates import EURO_GOVIES, US_TREASURIES
from launchpad.panels.rates_analytics import REAL_YIELDS, SPREADS_PANEL, YIELD_CURVES

PANELS = [
    INDICES, FX, US_TREASURIES, EURO_GOVIES, SPREADS_PANEL, REAL_YIELDS,
    POLICY_RATES, FED_PATH, ECB_PATH,
    VOL, COMMODITIES, WATCHLIST,
    # wide panels span the full width below the others
    YIELD_CURVES, ECO_CALENDAR,
]
