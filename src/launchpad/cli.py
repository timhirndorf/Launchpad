"""Print all panels in the terminal, handy for checking the data without the UI."""

import logging

from launchpad.service import build_panels


def fmt(value, width: int, decimals: int = 2, signed: bool = False) -> str:
    if value is None:
        return "-".rjust(width)
    if isinstance(value, str):
        return value.rjust(width)
    return f"{value:{'+' if signed else ''},.{decimals}f}".rjust(width)


def print_group(group: str | None, current: str | None) -> str | None:
    if group != current and group:
        print(f"  {group}")
    return group


def print_quotes(panel: dict) -> None:
    unit = "bp" if panel["kind"] == "yield" else "%"
    group = None
    for r in panel["rows"]:
        group = print_group(r["group"], group)
        move = r["change"] if panel["kind"] == "yield" else r["pct_change"]
        print(f"  {r['label']:<18}{fmt(r['last'], 12, r['decimals'])}{fmt(move, 9, signed=True)} {unit}")


def print_table(panel: dict) -> None:
    columns = panel["columns"]
    texts = [[fmt(c["v"], 0, c["d"], c["sign"]).strip() for c in r["cells"]] for r in panel["rows"]]
    widths = [max([len(col["label"])] + [len(t[i]) for t in texts]) + 2 for i, col in enumerate(columns)]

    def line(label: str, values: list[str]) -> str:
        parts = [v.ljust(w) if col.get("align") == "left" else v.rjust(w)
                 for v, w, col in zip(values, widths, columns)]
        return f"  {label:<18}" + "".join(parts)

    print(line("", [c["label"] for c in columns]))
    group = None
    for r, t in zip(panel["rows"], texts):
        group = print_group(r["group"], group)
        print(line(r["label"], t))
    if panel.get("note"):
        print(f"  ({panel['note']})")


def print_curves(panel: dict) -> None:
    curves = panel["curves"]
    print(f"  {'':<18}" + "".join(c["id"].rjust(9) for c in curves))
    for tenor in panel["tenors"]:
        values = [c["points"].get(tenor, {}).get("y") for c in curves]
        if any(v is not None for v in values):
            print(f"  {tenor:<18}" + "".join(fmt(v, 9, 3) for v in values))


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    data = build_panels()
    for panel in data["panels"]:
        print(f"\n{panel['title'].upper()}")
        if panel["type"] == "quotes":
            print_quotes(panel)
        elif panel["type"] == "table":
            print_table(panel)
        elif panel["type"] == "curves":
            print_curves(panel)
        else:
            print(f"  error: {panel['error']}")
    print(f"\nupdated {data['updated']}")


if __name__ == "__main__":
    main()
