#!/usr/bin/env python3
"""Fill every number in the docs and on the site from data/metrics.json, so text and model cannot disagree.

Markers (invisible in rendered Markdown/HTML):
    <!--m:net_revenue_ytd|eur0-->€ 18.702.899<!--/m-->      one value, with a format
    <!--table:dq_rules-->…<!--/table-->                     a generated table

Formats: int (1.234), eur0 (€ 1.234), eur2 (€ 1.234,56), pct (98,0 %), raw.
`python3 scripts/build_docs.py --check` fails when a file is out of date (used in CI).
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARK = re.compile(r"<!--m:([a-z0-9_]+)(?:\|([a-z0-9]+))?-->(.*?)<!--/m-->", re.S)
TABLE = re.compile(r"(<!--table:([a-z_]+)-->)(.*?)(<!--/table-->)", re.S)
FILES = ["README.md", "EVIDENCE.md", "CASE_STUDY.md", "START-HERE.md", "docs/**/*.md", "site/**/*.html", "application-kit/**/*.md"]


def be_number(value: float, decimals: int) -> str:
    s = f"{abs(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-" if value < 0 else "") + s


def fmt(value, kind: str | None) -> str:
    if kind in (None, "raw"):
        return str(value)
    if kind == "int":
        return be_number(value, 0)
    if kind == "eur0":
        return ("-" if value < 0 else "") + "€ " + be_number(abs(value), 0)
    if kind == "eur2":
        return ("-" if value < 0 else "") + "€ " + be_number(abs(value), 2)
    if kind == "pct":
        return be_number(value, 1) + " %"
    raise ValueError(kind)


def table_dq_rules(m: dict) -> str:
    rows = list(csv.DictReader(open(ROOT / "data" / "reference" / "dq_rules.csv", encoding="utf-8")))
    out = ["| ID | Regel | Ernst | Eigenaar | Vóór | Na | Oplossing |", "|---|---|---|---|---:|---:|---|"]
    for r in rows:
        key = r["rule_id"].lower().replace("-", "")
        sev = "blokkerend" if r["severity"] == "blocking" else "waarschuwing"
        out.append(f"| {r['rule_id']} | {r['title']} | {sev} | {r['owner']} | {be_number(m[f'rule_{key}_before'], 0)} | "
                   f"{be_number(m[f'rule_{key}_after'], 0)} | {r['fix']} |")
    return "\n".join(out)


def table_kpi_catalog(m: dict) -> str:
    rows = list(csv.DictReader(open(ROOT / "data" / "reference" / "kpi_catalog.csv", encoding="utf-8")))
    out = ["| ID | KPI | Definitie | DAX-measure | SQL | Eigenaar | Frequentie |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['kpi_id']} | **{r['name']}** | {r['definition']} | `[{r['dax_measure']}]` | `{r['sql_object']}` | {r['owner']} | {r['frequency']} |")
    return "\n".join(out)


TABLES = {"dq_rules": table_dq_rules, "kpi_catalog": table_kpi_catalog}


def render(text: str, m: dict) -> str:
    def one(match):
        key, kind = match.group(1), match.group(2)
        if key not in m:
            raise KeyError(f"unknown metric '{key}'")
        return f"<!--m:{key}{'|' + kind if kind else ''}-->{fmt(m[key], kind)}<!--/m-->"

    text = MARK.sub(one, text)
    return TABLE.sub(lambda t: f"{t.group(1)}\n{TABLES[t.group(2)](m)}\n{t.group(4)}", text)


def main() -> int:
    check = "--check" in sys.argv
    m = json.loads((ROOT / "data" / "metrics.json").read_text(encoding="utf-8"))
    stale, markers = [], 0
    for pattern in FILES:
        for path in sorted(ROOT.glob(pattern)):
            if "node_modules" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            markers += len(MARK.findall(text)) + len(TABLE.findall(text))
            new = render(text, m)
            if new != text:
                stale.append(str(path.relative_to(ROOT)))
                if not check:
                    path.write_text(new, encoding="utf-8")
    if check and stale:
        print("out of date (run python3 scripts/build_docs.py):", *stale, sep="\n  ")
        return 1
    print(f"{markers} markers {'checked' if check else 'rendered'}; {len(stale)} file(s) {'stale' if check else 'updated'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
