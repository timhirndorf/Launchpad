"""The fixed panels for the first version. All data comes from Yahoo Finance."""

from launchpad.panels.base import Panel

# Same lineup as Bloomberg's WEI (World Equity Indices) default screen.
INDICES = Panel(
    id="indices",
    title="World Equity Indices",
    groups={
        "Americas": {
            "^DJI": "Dow Jones",
            "^GSPC": "S&P 500",
            "^IXIC": "Nasdaq",
            "^GSPTSE": "S&P/TSX Comp",
            "^MXX": "S&P/BMV IPC",
            "^BVSP": "Ibovespa",
        },
        "EMEA": {
            "^STOXX50E": "Euro Stoxx 50",
            "^FTSE": "FTSE 100",
            "^FCHI": "CAC 40",
            "^GDAXI": "DAX",
            "^IBEX": "IBEX 35",
            "FTSEMIB.MI": "FTSE MIB",
            "^AEX": "AEX",
            "^OMX": "OMX Stkh 30",
            "^SSMI": "SMI",
        },
        "Asia/Pacific": {
            "^N225": "Nikkei 225",
            "^HSI": "Hang Seng",
            "000300.SS": "CSI 300",
            "^AXJO": "S&P/ASX 200",
        },
    },
)

# G10 currencies against USD, quoted in market convention (EUR, GBP, AUD, NZD per USD
# as XXX/USD; the rest as USD/XXX).
FX = Panel(
    id="fx",
    title="G10 FX",
    decimals=4,
    precision={"USDJPY=X": 2, "DX-Y.NYB": 2},
    groups={
        "vs USD": {
            "EURUSD=X": "EUR/USD",
            "USDJPY=X": "USD/JPY",
            "GBPUSD=X": "GBP/USD",
            "USDCHF=X": "USD/CHF",
            "USDCAD=X": "USD/CAD",
            "AUDUSD=X": "AUD/USD",
            "NZDUSD=X": "NZD/USD",
            "USDSEK=X": "USD/SEK",
            "USDNOK=X": "USD/NOK",
        },
        "Index": {
            "DX-Y.NYB": "DXY",
        },
    },
)

# VSTOXX (^V2TX) isn't available on Yahoo.
VOL = Panel(
    id="vol",
    title="Volatility",
    instruments={
        "^VIX": "VIX",
        "^VVIX": "VVIX",
        "^MOVE": "MOVE",
    },
)

COMMODITIES = Panel(
    id="commodities",
    title="Commodities",
    instruments={
        "BZ=F": "Brent",
        "CL=F": "WTI",
        "NG=F": "Nat Gas",
        "GC=F": "Gold",
        "HG=F": "Copper",
    },
)

WATCHLIST = Panel(
    id="watchlist",
    title="Watchlist",
    instruments={
        "OWL": "BlueOwl",
        "ARES": "Ares Management",
        "NVDA": "Nvidia",
        "SAP.DE": "SAP",
        "DBK.DE": "Deutsche Bank",
        "BTC-USD": "Bitcoin",
    },
)
