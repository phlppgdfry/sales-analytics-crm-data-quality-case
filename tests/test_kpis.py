"""KPI views agree with each other and with metrics.json (the single source for docs and site)."""


def one(con, sql, *a):
    return con.execute(sql, a).fetchone()[0]


def test_ytd_equals_sum_of_months(con, metrics):
    months = one(con, "SELECT round(sum(net_revenue), 2) FROM v_sales_monthly WHERE year_month BETWEEN '2026-01' AND '2026-09'")
    assert months == metrics["net_revenue_ytd"]


def test_rep_view_adds_up(con, metrics):
    reps = one(con, "SELECT round(sum(net_revenue), 2) FROM v_rep_month_vs_target WHERE year_month BETWEEN '2026-01' AND '2026-09'")
    assert reps == metrics["net_revenue_ytd"]


def test_margin_pct(metrics):
    assert round(100 * metrics["gross_margin_ytd"] / metrics["net_revenue_ytd"], 1) == metrics["margin_pct_ytd"]


def test_weighted_pipeline(con, metrics):
    w = one(con, "SELECT round(sum(coalesce(amount, 0) * probability), 2) FROM fact_opportunity WHERE is_open = 1")
    assert w == metrics["weighted_pipeline"]


def test_naive_report_would_show_unassigned_revenue(metrics):
    # before ERP-01 was fixed in the model, this revenue showed up as "Niet toegewezen"
    assert metrics["unassigned_revenue_naive"] > 0 and metrics["lines_rep_derived"] > 0
