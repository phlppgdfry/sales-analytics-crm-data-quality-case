#!/usr/bin/env python3
"""Export the model tables of the SQLite warehouse as CSV for the SQL Server load (sql/tsql/02_load.sql)."""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "warehouse" / "export"
TABLES = ["meta", "dim_date", "dim_rep", "dim_product", "dim_customer", "fact_sales", "fact_opportunity", "fact_target",
          "dq_rule", "dq_issue", "dq_health"]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ROOT / "warehouse" / "vennaert.sqlite")
    for t in TABLES:
        cur = con.execute(f"SELECT * FROM {t}")
        with open(OUT / f"{t}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
            w.writerow([d[0] for d in cur.description])
            for row in cur:
                w.writerow(["" if v is None else (f"{v:.2f}" if isinstance(v, float) else v) for v in row])
    print(f"{len(TABLES)} tables exported to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
