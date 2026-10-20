"""Every planted problem is caught by its rule (and the rule does not fire on clean data)."""
from conftest import ids


def issues(con, rule, snapshot="before"):
    return ids(con, "SELECT entity_id FROM dq_issue WHERE rule_id = ? AND snapshot = ?", rule, snapshot)


def test_crm02_invalid_vat(con, planted):
    assert issues(con, "CRM-02") == set(planted["invalid_vat"])


def test_crm03_customer_without_vat(con, planted):
    assert issues(con, "CRM-03") == set(planted["customer_without_vat"])


def test_crm04_missing_erp_link(con, planted):
    flagged_customers = ids(con, """SELECT c.customer_no FROM dq_issue i JOIN stg_crm_accounts a ON a.account_id = i.entity_id
                                    JOIN stg_customers c ON c.vat_norm = a.vat_norm
                                    WHERE i.rule_id = 'CRM-04' AND i.snapshot = 'before'""")
    # planted unlinked customers whose VAT is still readable must all be flagged
    readable = ids(con, f"""SELECT c.customer_no FROM stg_customers c JOIN stg_crm_accounts a ON a.vat_norm = c.vat_norm
                            WHERE a.erp_customer_no IS NULL AND c.customer_no IN ({','.join('?' * len(planted['missing_erp_link']))})""",
                   *planted["missing_erp_link"])
    assert readable and readable <= flagged_customers


def test_crm05_owner_left(con, planted):
    assert len(issues(con, "CRM-05")) == planted["inactive_owner_accounts"]
    assert not issues(con, "CRM-05", "after")


def test_crm07_postcode_format(con, planted):
    assert set(planted["wrong_postcode"]) <= issues(con, "CRM-07")


def test_erp_rules(con, planted):
    assert issues(con, "ERP-02") == set(planted["product_missing_category"])
    assert issues(con, "ERP-03") == set(planted["product_zero_cost"])
    assert len(issues(con, "ERP-01")) == planted["lines_missing_rep"]


def test_prospects_are_not_errors(con):
    # a prospect without VAT or ERP link is normal; no customer rule may fire on it
    hits = con.execute("""SELECT count(*) FROM dq_issue i JOIN v_account_scope s ON s.account_id = i.entity_id
                          WHERE i.snapshot = 'after' AND i.rule_id IN ('CRM-03', 'CRM-04') AND s.scope = 'other'""").fetchone()[0]
    assert hits == 0


def test_health_improves_but_is_not_perfect(metrics):
    # invalid VAT numbers need the customer; that cannot be fixed from behind a desk
    assert metrics["dq_health_after"] > metrics["dq_health_before"]
    assert metrics["dq_health_after"] < 100
