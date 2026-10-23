# Launchpad

A personal market overview inspired by the Bloomberg Launchpad: a single dark, dense page with the numbers I check every day.

## Panels

Fixed panels, refreshed every 60 seconds:

| Panel | Content | Source |
|---|---|---|
| World Equity Indices | Bloomberg WEI lineup, grouped: **Americas** (Dow, S&P 500, Nasdaq, TSX, IPC, Ibovespa), **EMEA** (Euro Stoxx 50, FTSE 100, CAC 40, DAX, IBEX 35, FTSE MIB, AEX, OMX 30, SMI), **Asia/Pacific** (Nikkei, Hang Seng, CSI 300, ASX 200) | Yahoo |
| G10 FX | EUR, JPY, GBP, CHF, CAD, AUD, NZD, SEK, NOK vs USD (market convention), plus DXY | Yahoo |
| US Treasury Yields | 1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y (change in bp) | CNBC (Tradeweb) |
| Euro Govt Yields | Germany, France, Italy: 6M (France 9M), 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y. CNBC has no 1M/3M euro yields | CNBC (Tradeweb) |
| Spreads & Curve | 2s10s and 5s30s for US/DE/FR/IT, US 3m10y; 10Y OAT–Bund, BTP–Bund, BTP–OAT, UST–Bund (bp) | derived from the yields above |
| US Real Yields & Breakevens | TIPS real yields 5Y–30Y, breakevens (nominal − real), 5y5y forward | US Treasury (official, end of day) |
| Yield Curves (chart) | US, DE, FR, IT nominal curves + US real curve; pick any combination from the dropdown, optionally with yesterday's close dashed | CNBC, US Treasury |
| Central Bank Rates | Fed target range, EFFR; ECB deposit, main refi, marginal lending, €STR, 3M Euribor | NY Fed, ECB, euribor-rates.eu |
| Fed: Market-Implied Path | Expected EFFR for the next 12 months, priced change in bp and in 25bp moves | Fed funds futures (Yahoo) |
| ECB: Market-Implied Path | Expected 3M Euribor for the next 12 contracts, priced change in bp and in 25bp moves | 3M Euribor futures (ICE) |
| Volatility | VIX, VVIX, MOVE | Yahoo |
| Commodities | Brent, WTI, Nat Gas, Gold, Copper | Yahoo |
| Watchlist | a few single names + Bitcoin | Yahoo |
| Economic Calendar | Releases for the US, Germany, France, Italy (+ euro area) from 2 days ago to 7 days ahead: actual, consensus, prior, period, importance | FXStreet |

"Last" is the live price during the session, otherwise the latest close. "Chg" is versus the previous session's close. A greyed-out price means the latest quote isn't from today (market closed, or the source hasn't published it yet). Hover to see the date.

### How the implied rate paths work

- **Fed:** a 30-day fed funds future settles on the average EFFR of its month, so `100 − price` is the market's expected EFFR for that month. "Δ bp" is that minus today's EFFR, "# 25bp" the same in 25bp moves (+ = hikes).
- **ECB:** a 3M Euribor future settles on 3M Euribor at expiry, so `100 − price` is the expected 3M Euribor. Euribor trades a few bp above the ECB deposit rate, so the priced change is measured against today's 3M Euribor fixing (same basis), not against the deposit rate. This assumes the Euribor–deposit spread stays constant.

This is the same idea as Bloomberg's WIRP, but per contract month rather than per meeting.

### Rates analytics

- **Spreads** are computed from the same live yields as the curve panels: `long − short` in bp, and the daily change of that spread.
- **Breakevens** are `nominal − real` par yields from the same Treasury release, i.e. the inflation the market prices in. The 5y5y forward uses the usual approximation `2 × 10y − 5y`. There's no free daily source for euro inflation-linked bonds (Bundesbank and ECB only publish nominal curves), so real yields are US only.
- **Yield curve chart** (Chart.js): tenors are evenly spaced like on a Bloomberg curve chart, and only tenors that one of the selected curves has are shown. The selection is remembered in the browser.
- **CNBC gaps:** CNBC drops less liquid tenors (e.g. DE 3Y/7Y/20Y) for hours at a time, notably on weekends. The last good quote per symbol is stored in `data/cnbc_last_good.json` and used instead; it keeps its date, so the page greys it out as stale.

### Economic calendar

Like Bloomberg's ECO: grouped by day, times in Europe/Berlin (`TIMEZONE` in `panels/calendar.py`). The actual is green/red when it came in above/below consensus; that's the direction of the surprise, not a judgement of good or bad. To keep it readable, US and euro area show only high-importance releases, Germany/France/Italy medium and high (`COUNTRIES` in `panels/calendar.py`).

FXStreet was picked after comparing free sources: Nasdaq's calendar has dates shifted by one day and gives m/m and y/y releases the same name; Yahoo's has no consensus and misses payrolls, CPI, ISM and PMIs; ForexFactory only covers the current week and has no actuals.

## Run it

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run launchpad        # http://127.0.0.1:8000
uv run launchpad-cli    # same data as a table in the terminal
uv run pytest
```

## How it works

```
browser (static/app.js) ──every 60s──▶ FastAPI /api/panels ──▶ service (panels in parallel) ──▶ panels ──▶ sources (cached)
```

```
src/launchpad/
├── sources/              one module per data provider, each returns plain objects (Quote, Observation, ...)
│   ├── base.py           Quote / Observation model, shared HTTP helper
│   ├── yahoo.py          stocks, indices, FX, commodities, fed funds futures
│   ├── cnbc.py           government bond yields
│   ├── nyfed.py          EFFR + Fed target range
│   ├── ecb.py            ECB policy rates, €STR
│   ├── euribor.py        3M Euribor fixing
│   └── ice.py            Euribor futures curve
├── panels/
│   ├── base.py           Panel (quote list) + helpers for table panels
│   ├── markets.py        equities, FX, vol, commodities, watchlist
│   ├── rates.py          UST and euro govt yields
│   ├── rates_analytics.py spreads, real yields/breakevens, yield curve chart
│   ├── central_banks.py  policy rates + implied paths
│   ├── calendar.py       economic calendar
│   └── __init__.py       PANELS: the registry, i.e. what shows up on the page and in which order
├── service.py            builds all panels in parallel; a failing source only breaks its own panel
├── cache.py              tiny TTL cache (60s for prices, 5 min for the calendar, 1h for published rates)
├── app.py                FastAPI app (API + serves static/)
└── cli.py                terminal output
static/                   index.html, style.css, app.js (no framework, no build step; Chart.js from a CDN)
```

Every panel has an `id`, a `title` and a `build()` that returns JSON of one of three types: `quotes` (Last / Chg / %Chg rows), `table` (free-form columns) or `curves` (the yield curve chart). The front end has one renderer per type.

**Adding an instrument:** add a line to the panel in `panels/markets.py` or `panels/rates.py`. Grouped panels use `groups={...}` instead of `instruments={...}`; `source="cnbc"` switches the quote source.
**Adding a panel:** create an object with `id`, `title` and `build()` and add it to `PANELS` in `panels/__init__.py`.

## Roadmap

- [x] v0.1: fixed panels, Yahoo data, auto-refresh
- [x] Rates: full UST curve, Bunds/OATs/BTPs, Fed/ECB policy rates, market-implied paths
- [x] Spreads & curve, US real yields & breakevens, yield curve chart
- [ ] Implied path per meeting (FOMC / ECB dates) instead of per contract month
- [ ] History (SQLite snapshots): curves vs 1W / 1M ago, spread charts
- [ ] Sparklines / click-through charts
- [x] Economic calendar (US, DE, FR, IT, euro area)
- [ ] News (RSS)
- [ ] Panel config in a file (YAML/TOML) instead of Python, then user-arrangeable layout
- [ ] Better source (IBKR API) for live prices

## Known limitations

- yfinance, the CNBC quote service, ICE's product pages, euribor-rates.eu and the FXStreet calendar are all unofficial: they can change or block requests without notice. Each source only breaks its own panel. The NY Fed and ECB APIs are official.
- VSTOXX and TOPIX aren't available on Yahoo.
- Yahoo data quirks handled in `sources/yahoo.py`: daily bars for non-US markets often have an empty close for the latest session, daily FX bars are shifted by a day, and `chartPreviousClose` is unreliable for continuous futures. So the last price comes from the live quote, and the previous close from the daily bars (FX: from the chart metadata).
- ICE futures prices are delayed. Policy rates and fixings are published once a day (EFFR and €STR for the previous business day).
