#!/usr/bin/env python3
"""Recalculate every formula in the reconciliation workbook (python `formulas`, no Excel needed)
and fail unless each check cell on tab "Brug" says OK. Proves the Excel bridge and the SQL bridge agree."""
from __future__ import annotations

import sys
from pathlib import Path

import formulas

ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / "excel" / "reconciliatie-sales-finance-2026Q3.xlsx"


def main() -> int:
    solution = formulas.ExcelModel().loads(str(BOOK)).finish().calculate()
    checks = {}
    for ref, value in solution.items():
        ref = str(ref).upper()
        if "]BRUG'!F" in ref and ":" not in ref and not ref.endswith("!F1"):
            checks[ref.split("!")[1]] = value.value[0][0]
    for cell in sorted(checks, key=lambda c: int(c[1:])):
        print(f"Brug!{cell}: {checks[cell]}")
    ok = len(checks) == 8 and all(v == "OK" for v in checks.values())
    print("workbook OK" if ok else "workbook FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
