#!/usr/bin/env python3
"""Generate the table definitions of the Power BI semantic model (TMDL) from the warehouse schema.

The columns in powerbi/…/definition/tables/*.tmdl are generated, so the model can never drift from
the SQL. The measures live in the hand-written Measures.tmdl; tests/test_powerbi.py checks that every
column a measure uses exists. Run after etl/pipeline.py:

    python3 scripts/build_tmdl.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WAREHOUSE = ROOT / "warehouse" / "vennaert.sqlite"
TABLES_DIR = ROOT / "powerbi" / "Vennaert Sales.SemanticModel" / "definition" / "tables"

# table in the model -> (object in the dwh schema, description)
TABLES = {
    "dim_date": ("dim_date", "Kalender 2025–2026; gemarkeerd als datumtabel"),
    "dim_customer": ("dim_customer", "ERP-klanten met huidige verkoper en gekoppeld CRM-account (na samenvoegen)"),
    "dim_product": ("dim_product", "Artikelen; ontbrekende categorie = 'Onbekend'"),
    "dim_rep": ("dim_rep", "Verkopers; rij 0 = 'Niet toegewezen'. E-mail stuurt de beveiliging op rijniveau"),
    "fact_sales": ("fact_sales", "Eén rij per factuur- of creditnotalijn; creditnota's negatief"),
    "fact_opportunity": ("fact_opportunity", "Eén rij per opportunity, huidige stand"),
    "fact_target": ("fact_target", "Target per verkoper per maand (uit het Excel-bestand van de sales manager)"),
    "dq_rule_summary": ("v_dq_rule_summary", "Datakwaliteit per regel, vóór en na de correcties"),
    "dq_health": ("dq_health", "CRM-gezondheid per momentopname"),
}
SUM_COLUMNS = {"net_amount", "cost_amount", "gross_margin", "qty", "amount", "target_amount", "issues_before", "issues_after"}
DATE_COLUMNS = {("dim_date", "date")}
DECIMAL_HINT = {"net_amount", "cost_amount", "gross_margin", "unit_cost", "list_price", "amount", "probability", "target_amount", "health_pct"}


def data_type(con, obj, col) -> str:
    if col in DECIMAL_HINT:
        return "decimal"
    value = con.execute(f'SELECT "{col}" FROM "{obj}" WHERE "{col}" IS NOT NULL LIMIT 1').fetchone()
    if value is None:
        return "string"
    v = value[0]
    if isinstance(v, int):
        return "int64"
    if isinstance(v, float):
        return "decimal"
    return "string"


def table_tmdl(con, name, obj, description) -> str:
    cols = [r[1] for r in con.execute(f'PRAGMA table_info("{obj}")')]
    out = [f"/// {description}", f"table {name}"]
    if name == "dim_date":
        out.append("\tdataCategory: Time")
    out.append("")
    for col in cols:
        dtype = "dateTime" if (name, col) in DATE_COLUMNS else data_type(con, obj, col)
        out.append(f"\tcolumn {col}")
        out.append(f"\t\tdataType: {dtype}")
        if (name, col) in DATE_COLUMNS:
            out.append("\t\tisKey")
            out.append("\t\tformatString: dd/mm/yyyy")
        if col.endswith("_key") or col in {"rep_derived", "is_internal", "is_open", "is_active", "is_weekday", "stage_order"}:
            out.append("\t\tisHidden")
        if dtype == "decimal" and col in SUM_COLUMNS:
            out.append("\t\tformatString: #,0.00")
        out.append(f"\t\tsummarizeBy: {'sum' if col in SUM_COLUMNS else 'none'}")
        out.append(f"\t\tsourceColumn: {col}")
        if name == "dim_date" and col == "month_short_nl":
            out.append("\t\tsortByColumn: month")
        out.append("")
    out += [
        f"\tpartition {name} = m",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\t\tlet",
        "\t\t\t\t    Source = Sql.Database(Server, Database),",
        f'\t\t\t\t    Data = Source{{[Schema = "dwh", Item = "{obj}"]}}[Data]',
        "\t\t\t\tin",
        "\t\t\t\t    Data",
        "",
    ]
    return "\n".join(out) + "\n"


def main() -> None:
    con = sqlite3.connect(WAREHOUSE)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    for name, (obj, description) in TABLES.items():
        (TABLES_DIR / f"{name}.tmdl").write_text(table_tmdl(con, name, obj, description), encoding="utf-8")
    print(f"{len(TABLES)} tables written to {TABLES_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
