"""Panels: everything on the page is a panel with an `id`, a `title` and a `build()`
that returns its JSON. Two kinds exist:

- Panel: a list of quoted instruments (Last / Chg / %Chg), from one quote source.
- Table panels (see `table()`): free-form rows/columns, e.g. policy rates.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Literal, TypeVar

from launchpad.sources import cnbc, yahoo
from launchpad.sources.base import Quote

log = logging.getLogger(__name__)
T = TypeVar("T")

# "price": show change in price units and %. "yield": quotes are in percent, show change in bp.
Kind = Literal["price", "yield"]

QUOTE_SOURCES: dict[str, Callable[[tuple[str, ...]], dict[str, Quote]]] = {
    "yahoo": yahoo.fetch_quotes,
    "cnbc": cnbc.fetch_quotes,
}


@dataclass(frozen=True)
class Panel:
    id: str
    title: str
    instruments: dict[str, str] = field(default_factory=dict)  # Yahoo symbol -> display label
    groups: dict[str, dict[str, str]] = field(default_factory=dict)  # group -> {symbol: label}
    kind: Kind = "price"
    decimals: int = 2
    precision: dict[str, int] = field(default_factory=dict)  # per-symbol override of `decimals`
    source: str = "yahoo"  # key in QUOTE_SOURCES

    def entries(self) -> list[tuple[str | None, str, str]]:
        """(group, symbol, label) for every instrument, in display order."""
        flat = [(None, s, label) for s, label in self.instruments.items()]
        grouped = [(g, s, label) for g, items in self.groups.items() for s, label in items.items()]
        return flat + grouped

    @property
    def symbols(self) -> list[str]:
        return [s for _, s, _ in self.entries()]

    def build(self) -> dict:
        return self.render(QUOTE_SOURCES[self.source](tuple(self.symbols)))

    def render(self, quotes: dict[str, Quote]) -> dict:
        rows = []
        for group, symbol, label in self.entries():
            q = quotes.get(symbol)
            decimals = self.precision.get(symbol, self.decimals)
            row = {"group": group, "symbol": symbol, "label": label, "decimals": decimals,
                   "last": None, "change": None, "pct_change": None, "as_of": None}
            if q:
                change = q.change * 100 if self.kind == "yield" else q.change
                row.update(
                    last=round(q.last, decimals),
                    change=round(change, 1 if self.kind == "yield" else decimals),
                    pct_change=None if self.kind == "yield" else round(q.pct_change, 2),
                    as_of=q.as_of,
                )
            rows.append(row)
        return {"id": self.id, "title": self.title, "type": "quotes", "kind": self.kind, "rows": rows}


# --- table panels -------------------------------------------------------------------

def safe(fetch: Callable[..., T], *args) -> T | None:
    """Run a fetch; on failure log it and return None so the rest of the panel still renders."""
    try:
        return fetch(*args)
    except Exception:
        log.exception("fetch failed: %s", getattr(fetch, "__name__", fetch))
        return None


def short_date(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%d %b")


def cell(value: float | str | None, decimals: int = 2, signed: bool = False,
         colored: bool = False, suffix: str = "", cls: str = "") -> dict:
    """One table cell. Numbers are formatted by the front end (same as quote panels).
    `colored` colors by the sign of the value; `cls` sets a CSS class explicitly."""
    return {"v": value, "d": decimals, "sign": signed, "color": colored, "suffix": suffix, "cls": cls}


def bp(value: float | None) -> dict:
    """A change in basis points: signed, colored, one decimal."""
    if value is not None:
        value = round(value, 1) + 0.0  # + 0.0 turns -0.0 into 0.0
    return cell(value, decimals=1, signed=True, colored=True)


def table(id: str, title: str, columns: list[str | dict], rows: list[dict], note: str = "",
          wide: bool = False) -> dict:
    """rows: [{"label": str, "group": str | None, "cells": [cell, ...]}]; columns exclude the label.
    A column is a header string, or {"label": str, "align": "left"} for text columns.
    `wide` makes the panel span the full page width."""
    columns = [c if isinstance(c, dict) else {"label": c} for c in columns]
    return {"id": id, "title": title, "type": "table", "columns": columns, "rows": rows,
            "note": note, "wide": wide}


def row(label: str, cells: list[dict], group: str | None = None) -> dict:
    return {"label": label, "group": group, "cells": cells}
