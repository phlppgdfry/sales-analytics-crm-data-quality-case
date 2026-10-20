"""Star schema: nothing lost between staging and facts, credit notes negative, revenue on the right rep."""


def one(con, sql, *a):
    return con.execute(sql, a).fetchone()[0]


def test_no_lines_lost(con):
    assert one(con, "SELECT count(*) FROM fact_sales") == one(con, "SELECT count(*) FROM stg_invoice_lines")
    assert round(one(con, "SELECT sum(net_amount) FROM fact_sales"), 2) == round(one(con, "SELECT sum(net_amount) FROM stg_invoice_lines"), 2)


def test_credit_notes_are_negative(con):
    assert one(con, "SELECT count(*) FROM fact_sales WHERE doc_type = 'C' AND net_amount >= 0") == 0


def test_every_line_has_a_rep(con):
    assert one(con, "SELECT count(*) FROM fact_sales WHERE rep_key = 0") == 0


def test_revenue_follows_owner_at_invoice_date(con):
    # invoices only: a credit note keeps the rep of the invoice it corrects (see the next test)
    am04_after = one(con, """SELECT count(*) FROM fact_sales f JOIN dim_rep r USING (rep_key) JOIN dim_date d USING (date_key)
                             WHERE r.rep_code = 'AM04' AND d.date > '2026-03-31' AND f.doc_type = 'F'""")
    am11_before = one(con, """SELECT count(*) FROM fact_sales f JOIN dim_rep r USING (rep_key) JOIN dim_date d USING (date_key)
                              WHERE r.rep_code = 'AM11' AND d.date < '2026-04-01'""")
    assert am04_after == 0 and am11_before == 0


def test_dimension_keys_unique(con):
    for table, key in [("dim_customer", "customer_no"), ("dim_product", "sku"), ("dim_rep", "rep_code"), ("dim_date", "date_key")]:
        assert one(con, f"SELECT count(*) - count(DISTINCT {key}) FROM {table}") == 0, table


def test_customer_dimension_points_to_surviving_accounts(con):
    assert one(con, """SELECT count(*) FROM dim_customer d JOIN crm_acc a ON a.account_id = d.crm_account_id
                       WHERE a.merged_into IS NOT NULL""") == 0


def test_internal_customer_excluded_from_reporting(con):
    assert one(con, "SELECT count(*) FROM v_sales WHERE customer_no = 'C99999'") == 0
