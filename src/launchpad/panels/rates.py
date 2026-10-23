"""Government bond yields (CNBC / Tradeweb, intraday)."""

from launchpad.panels.base import Panel

US_TREASURIES = Panel(
    id="ust",
    title="US Treasury Yields",
    source="cnbc",
    kind="yield",
    decimals=3,
    instruments={
        "US1M": "1M",
        "US3M": "3M",
        "US6M": "6M",
        "US1Y": "1Y",
        "US2Y": "2Y",
        "US3Y": "3Y",
        "US5Y": "5Y",
        "US7Y": "7Y",
        "US10Y": "10Y",
        "US20Y": "20Y",
        "US30Y": "30Y",
    },
)


def curve(country: str, short_end: str = "6M") -> dict[str, str]:
    """CNBC symbols for one country's curve, same tenors as the US panel from 6M out.
    CNBC has no 1M/3M euro govt yields; France's shortest bill quote is 9M."""
    tenors = [short_end, "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y"]
    return {f"{country}{t}-{country}": t for t in tenors}


EURO_GOVIES = Panel(
    id="euro-govies",
    title="Euro Govt Yields",
    source="cnbc",
    kind="yield",
    decimals=3,
    groups={
        "Germany": curve("DE"),
        "France": curve("FR", short_end="9M"),
        "Italy": curve("IT"),
    },
)
