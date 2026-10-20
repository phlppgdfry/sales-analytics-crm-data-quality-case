"""The weekly Excel vs finance difference is explained to the cent, by steps computed from the data."""


def bridge(con):
    return {step: amount for step, amount in con.execute("SELECT step, amount FROM v_reconciliation_2026q3")}


def test_bridge_closes_to_the_cent(con):
    b = bridge(con)
    assert b[8] == 0
    assert round(b[1] + b[2] + b[3] + b[4], 2) == b[6]


def test_warehouse_equals_finance(con):
    b = bridge(con)
    assert b[7] == b[6]


def test_duplicate_day_is_the_planted_day(con, planted):
    days = {r[0] for r in con.execute("SELECT DISTINCT invoice_date FROM v_legacy_duplicate_rows")}
    assert days == {planted["duplicate_export_day"]}


def test_each_month_matches_finance(con):
    rows = con.execute("""SELECT f.period, CAST(f.amount AS REAL), (SELECT round(sum(net_amount), 2) FROM v_sales s WHERE s.year_month = f.period)
                          FROM src_finance_revenue_2026q3 f""").fetchall()
    assert rows and all(round(a, 2) == round(b, 2) for _, a, b in rows)


def test_committed_workbook_carries_the_current_bridge(metrics):
    # the Excel formulas themselves are recalculated in CI (scripts/check_workbook.py); here: is the file current?
    from pathlib import Path

    from openpyxl import load_workbook

    book = load_workbook(Path(__file__).resolve().parent.parent / "excel" / "reconciliatie-sales-finance-2026Q3.xlsx")
    sql_column = [book["Brug"].cell(row=r, column=5).value for r in range(2, 9)]
    assert sql_column == [metrics[k] for k in ("recon_legacy", "recon_dup_day", "recon_credit", "recon_internal",
                                               "recon_explained", "recon_finance", "recon_unexplained")]
    assert book["Export"].max_row - 1 == metrics["n_legacy_rows"]
