#!/usr/bin/env python3
"""Vennaert sales & CRM pipeline: raw extracts -> staging -> data quality -> corrections -> star schema -> reports.

    python3 etl/pipeline.py

Steps (each one logged, each one re-runnable from scratch):
  1. load      data/raw/*.csv                 -> src_* tables (as text, exactly as delivered)
  2. stage     sql/01_staging.sql             -> stg_* tables (types, signs, VAT notation)
  3. check     sql/02_dq_rules.sql + etl/duplicates.py   -> dq_issue / dq_duplicate_pair  (snapshot "before")
  4. correct   data/review/decisions.csv + two rule-based fixes -> crm_change_log  (nothing is deleted)
  5. re-check  same rules                     -> snapshot "after"
  6. model     sql/03_model.sql               -> dim_* / fact_*
  7. report    sql/04_views.sql, sql/05_reconciliation.sql
  8. publish   warehouse/vennaert.sqlite, data/metrics.json, site/data/*.json, site/data/warehouse.sqlite

Only the Python standard library is used, so it runs anywhere Python 3.10+ runs.
"""
from __future__ import annotations

import csv
import json
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
from duplicates import find_pairs, name_similarity, normalise_name  # noqa: E402

RAW = ROOT / "data" / "raw"
SQL = ROOT / "sql"
WAREHOUSE = ROOT / "warehouse" / "vennaert.sqlite"
DECISIONS = ROOT / "data" / "review" / "decisions.csv"
QUEUE = ROOT / "data" / "review" / "duplicate_queue.csv"
METRICS = ROOT / "data" / "metrics.json"
SITE_DATA = ROOT / "site" / "data"
AS_OF = "2026-09-30"


def log(step: str, msg: str) -> None:
    print(f"[{step:<8}] {msg}")


def run_sql(con: sqlite3.Connection, text: str) -> None:
    con.executescript(text)


def sql_file(name: str, **params: str) -> str:
    text = (SQL / name).read_text(encoding="utf-8")
    for k, v in params.items():
        text = text.replace("{" + k + "}", v)
    return text


# ----------------------------------------------------------------------------- 1. load

def load_raw(con: sqlite3.Connection) -> None:
    for path in sorted(RAW.glob("*.csv")):
        table = "src_" + path.stem.lower()
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            header = next(reader)
            rows = list(reader)
        cols = ", ".join(f'"{h}" TEXT' for h in header)
        con.execute(f'DROP TABLE IF EXISTS "{table}"')
        con.execute(f'CREATE TABLE "{table}" ({cols})')
        con.executemany(f'INSERT INTO "{table}" VALUES ({", ".join("?" * len(header))})', rows)
        log("load", f"{table:<38} {len(rows):>7} rows")


# ----------------------------------------------------------------------------- 3/5. checks

def create_dq_tables(con: sqlite3.Connection) -> None:
    con.executescript("""
        CREATE TABLE meta (as_of_date TEXT);
        CREATE TABLE dq_rule (rule_id TEXT PRIMARY KEY, title TEXT, severity TEXT, owner TEXT, fix TEXT);
        CREATE TABLE dq_issue (snapshot TEXT, rule_id TEXT, severity TEXT, entity TEXT, entity_id TEXT, detail TEXT);
        CREATE TABLE dq_duplicate_pair (snapshot TEXT, account_a TEXT, account_b TEXT, score INTEGER, band TEXT, evidence TEXT);
        CREATE TABLE dq_health (snapshot TEXT, accounts_in_scope INTEGER, accounts_clean INTEGER, health_pct REAL);
        CREATE TABLE crm_change_log (change_id INTEGER PRIMARY KEY, change_type TEXT, account_id TEXT, field TEXT,
                                     old_value TEXT, new_value TEXT, reason TEXT, decided_by TEXT);
    """)
    con.execute("INSERT INTO meta VALUES (?)", (AS_OF,))
    with open(ROOT / "data" / "reference" / "dq_rules.csv", newline="", encoding="utf-8") as fh:
        con.executemany("INSERT INTO dq_rule VALUES (:rule_id, :title, :severity, :owner, :fix)", list(csv.DictReader(fh)))


def build_working_crm(con: sqlite3.Connection) -> None:
    con.executescript("""
        DROP TABLE IF EXISTS crm_acc;
        CREATE TABLE crm_acc AS SELECT *, CAST(NULL AS TEXT) AS name_norm, CAST(NULL AS TEXT) AS merged_into FROM stg_crm_accounts;
        DROP TABLE IF EXISTS crm_opp;
        CREATE TABLE crm_opp AS SELECT * FROM stg_crm_opportunities;
    """)
    names = con.execute("SELECT account_id, account_name FROM crm_acc").fetchall()
    con.executemany("UPDATE crm_acc SET name_norm = ? WHERE account_id = ?", [(normalise_name(n), i) for i, n in names])


def run_checks(con: sqlite3.Connection, snapshot: str) -> None:
    views, rules = sql_file("02_dq_rules.sql", snapshot=snapshot).split("-- @rules", 1)
    run_sql(con, views)
    pairs = find_pairs(con, snapshot)
    if snapshot == "after":
        # a pair judged "not a duplicate" is remembered, so it does not come back in next week's queue
        con.execute("""DELETE FROM dq_duplicate_pair WHERE snapshot = 'after' AND EXISTS (
                         SELECT 1 FROM review_decision d WHERE d.decision = 'geen duplicaat'
                           AND ((d.account_a = dq_duplicate_pair.account_a AND d.account_b = dq_duplicate_pair.account_b)
                                OR (d.account_a = dq_duplicate_pair.account_b AND d.account_b = dq_duplicate_pair.account_a)))""")
        pairs = con.execute("SELECT * FROM dq_duplicate_pair WHERE snapshot = 'after'").fetchall()
    run_sql(con, rules)
    # health score: share of customer accounts without a blocking issue (a duplicate pair counts for both records)
    con.execute("DELETE FROM dq_health WHERE snapshot = ?", (snapshot,))
    con.execute("""
        INSERT INTO dq_health
        SELECT ?, count(*), sum(CASE WHEN bad.account_id IS NULL THEN 1 ELSE 0 END),
               round(100.0 * sum(CASE WHEN bad.account_id IS NULL THEN 1 ELSE 0 END) / count(*), 1)
        FROM v_account_scope s
        LEFT JOIN (
            SELECT entity_id AS account_id FROM dq_issue WHERE snapshot = ? AND severity = 'blocking' AND entity = 'account'
            UNION SELECT account_a FROM dq_duplicate_pair WHERE snapshot = ?
        ) bad ON bad.account_id = s.account_id
        WHERE s.scope IN ('customer', 'customer-unlinked')
    """, (snapshot, snapshot, snapshot))
    issues = con.execute("SELECT count(*) FROM dq_issue WHERE snapshot = ?", (snapshot,)).fetchone()[0]
    health = con.execute("SELECT health_pct FROM dq_health WHERE snapshot = ?", (snapshot,)).fetchone()[0]
    log("check", f"{snapshot:<6} {issues} issues · {len(pairs)} duplicate pairs · health {health}%")


def export_queue(con: sqlite3.Connection) -> None:
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    rows = con.execute("""
        SELECT p.account_a, a.account_name, p.account_b, b.account_name, p.score, p.band, p.evidence
        FROM dq_duplicate_pair p JOIN crm_acc a ON a.account_id = p.account_a JOIN crm_acc b ON b.account_id = p.account_b
        WHERE p.snapshot = 'before' ORDER BY p.score DESC, p.account_a, p.account_b
    """).fetchall()
    with open(QUEUE, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["account_a", "name_a", "account_b", "name_b", "score", "band", "evidence"])
        w.writerows(rows)


# ----------------------------------------------------------------------------- 4. corrections

def change(con, change_type, account_id, field, old, new, reason, decided_by):
    con.execute("INSERT INTO crm_change_log (change_type, account_id, field, old_value, new_value, reason, decided_by) VALUES (?,?,?,?,?,?,?)",
                (change_type, account_id, field, old, new, reason, decided_by))


def apply_corrections(con: sqlite3.Connection) -> None:
    con.row_factory = sqlite3.Row
    acc = {r["account_id"]: dict(r) for r in con.execute("SELECT * FROM crm_acc")}

    # 4a. merges approved in the review queue -> union-find, survivor = ERP-linked, else oldest record
    parent: dict[str, str] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    decisions = list(csv.DictReader(open(DECISIONS, encoding="utf-8"))) if DECISIONS.exists() else []
    for d in decisions:
        if d["decision"] == "samenvoegen":
            parent[find(d["account_b"])] = find(d["account_a"])
    clusters: dict[str, list[str]] = {}
    for x in list(parent):
        clusters.setdefault(find(x), []).append(x)
    for members in clusters.values():
        if len(members) < 2:
            continue
        members.sort(key=lambda i: (acc[i]["erp_customer_no"] is None, acc[i]["created_at"], i))
        survivor, losers = members[0], members[1:]
        for lost in losers:
            for field in ("vat_norm", "email", "phone"):  # fill gaps in the survivor, never overwrite
                if acc[survivor][field] is None and acc[lost][field] is not None:
                    acc[survivor][field] = acc[lost][field]
                    con.execute(f"UPDATE crm_acc SET {field} = ? WHERE account_id = ?", (acc[lost][field], survivor))
                    change(con, "merge-fill", survivor, field, None, acc[lost][field], f"overgenomen van {lost}", "review")
            moved = con.execute("UPDATE crm_opp SET account_id = ? WHERE account_id = ?", (survivor, lost)).rowcount
            con.execute("UPDATE crm_acc SET merged_into = ? WHERE account_id = ?", (survivor, lost))
            change(con, "merge", lost, "merged_into", None, survivor, f"duplicaat; {moved} opportunities verhuisd", "review")
    merges = sum(len(m) - 1 for m in clusters.values() if len(m) > 1)

    # 4b. missing ERP link: propose only when exactly one unlinked ERP customer has that VAT and the name matches
    linked = {r[0] for r in con.execute("SELECT erp_customer_no FROM crm_acc WHERE erp_customer_no IS NOT NULL AND merged_into IS NULL")}
    links = 0
    for r in con.execute("SELECT s.account_id FROM v_account_scope s WHERE s.scope = 'customer-unlinked' ORDER BY s.account_id").fetchall():
        a = acc[r["account_id"]]
        cands = [c for c in con.execute("SELECT customer_no, customer_name FROM stg_customers WHERE vat_norm = ? AND is_internal = 0",
                                        (a["vat_norm"],)) if c["customer_no"] not in linked]
        cands = [c for c in cands if name_similarity(normalise_name(c["customer_name"]), a["name_norm"]) >= 0.8]
        if len(cands) == 1:
            con.execute("UPDATE crm_acc SET erp_customer_no = ? WHERE account_id = ?", (cands[0]["customer_no"], a["account_id"]))
            change(con, "link", a["account_id"], "erp_customer_no", None, cands[0]["customer_no"], "btw uniek + naam ≥ 80 %", "batch, goedgekeurd door sales manager")
            linked.add(cands[0]["customer_no"])
            links += 1

    # 4c. owner left the company -> current ERP owner of the linked customer (ADR-002: ERP history is the source)
    reassigned = 0
    for r in con.execute("""
        SELECT a.account_id, a.owner_rep, h.rep_code AS erp_owner
        FROM crm_acc a JOIN stg_sales_reps r ON r.rep_code = a.owner_rep
        LEFT JOIN stg_customer_rep_history h ON h.customer_no = a.erp_customer_no AND h.valid_to = '9999-12-31'
        WHERE r.end_date < (SELECT as_of_date FROM meta) AND a.merged_into IS NULL
        ORDER BY a.account_id
    """).fetchall():
        new_owner = r["erp_owner"] or "AM11"  # prospects of the leaver go to the successor in the same region
        con.execute("UPDATE crm_acc SET owner_rep = ? WHERE account_id = ?", (new_owner, r["account_id"]))
        change(con, "reassign", r["account_id"], "owner_rep", r["owner_rep"], new_owner, "eigenaar uit dienst", "batch, goedgekeurd door sales manager")
        reassigned += 1
    con.row_factory = None
    log("correct", f"{merges} records merged · {links} ERP links · {reassigned} owners reassigned · {len(decisions)} review decisions read")


# ----------------------------------------------------------------------------- 8. publish

def q(con, sql, *args):
    return con.execute(sql, args).fetchall()


def q1(con, sql, *args):
    return con.execute(sql, args).fetchone()


def build_metrics(con: sqlite3.Connection) -> dict:
    m: dict[str, object] = {"as_of": AS_OF}
    m["n_products"] = q1(con, "SELECT count(*) FROM stg_products")[0]
    m["n_customers"] = q1(con, "SELECT count(*) FROM stg_customers WHERE is_internal = 0")[0]
    m["n_invoice_lines"] = q1(con, "SELECT count(*) FROM stg_invoice_lines")[0]
    m["n_credit_lines"] = q1(con, "SELECT count(*) FROM stg_invoice_lines WHERE doc_type = 'C'")[0]
    m["n_crm_accounts"] = q1(con, "SELECT count(*) FROM stg_crm_accounts")[0]
    m["n_opportunities"] = q1(con, "SELECT count(*) FROM stg_crm_opportunities")[0]
    m["n_reps"] = q1(con, "SELECT count(*) FROM stg_sales_reps")[0]
    m["n_erp_customers_all"] = q1(con, "SELECT count(*) FROM stg_customers")[0]
    m["n_targets"] = q1(con, "SELECT count(*) FROM stg_targets")[0]
    m["n_legacy_rows"] = q1(con, "SELECT count(*) FROM legacy_export")[0]
    m["first_invoice"], m["last_invoice"] = q1(con, "SELECT min(invoice_date), max(invoice_date) FROM stg_invoice_lines")

    ytd = dict(zip([d[0] for d in con.execute("SELECT * FROM v_kpi_ytd").description], q1(con, "SELECT * FROM v_kpi_ytd")))
    m.update({k: v for k, v in ytd.items()})
    wr = q1(con, "SELECT won, lost, win_rate_pct FROM v_win_rate_12m")
    m["won_12m"], m["lost_12m"], m["win_rate_12m_pct"] = wr
    pipe = q1(con, "SELECT sum(opportunities), sum(amount), sum(weighted_amount), sum(stale), sum(without_amount) FROM v_pipeline_by_stage")
    m["open_opportunities"], m["open_pipeline"], m["weighted_pipeline"], m["stale_opportunities"], m["open_without_amount"] = pipe

    for snap in ("before", "after"):
        h = q1(con, "SELECT accounts_in_scope, accounts_clean, health_pct FROM dq_health WHERE snapshot = ?", snap)
        m[f"dq_scope_{snap}"], m[f"dq_clean_{snap}"], m[f"dq_health_{snap}"] = h
        m[f"dq_issues_{snap}"] = q1(con, "SELECT count(*) FROM dq_issue WHERE snapshot = ?", snap)[0]
        m[f"dup_pairs_{snap}"] = q1(con, "SELECT count(*) FROM dq_duplicate_pair WHERE snapshot = ?", snap)[0]
        for band, key in (("waarschijnlijk", "likely"), ("beoordelen", "review")):
            m[f"dup_pairs_{key}_{snap}"] = q1(con, "SELECT count(*) FROM dq_duplicate_pair WHERE snapshot = ? AND band = ?", snap, band)[0]
    for rule_id, before, after in q(con, "SELECT rule_id, issues_before, issues_after FROM v_dq_rule_summary ORDER BY rule_id"):
        key = rule_id.lower().replace("-", "")
        m[f"rule_{key}_before"], m[f"rule_{key}_after"] = before, after
    for ctype, n in q(con, "SELECT change_type, count(*) FROM crm_change_log GROUP BY change_type ORDER BY change_type"):
        m[f"changes_{ctype.replace('-', '_')}"] = n
    dec = q(con, "SELECT decision, count(*) FROM review_decision GROUP BY decision ORDER BY decision") if q1(con, "SELECT count(*) FROM sqlite_master WHERE name='review_decision'")[0] else []
    for d, n in dec:
        m[f"review_{d.replace(' ', '_')}"] = n
    m["review_total"] = sum(n for _, n in dec)
    m["accounts_after_merge"] = q1(con, "SELECT count(*) FROM crm_acc WHERE merged_into IS NULL")[0]

    m["credit_lines_leaver_after_exit"] = q1(con, """SELECT count(*) FROM fact_sales f JOIN dim_rep r USING (rep_key)
        WHERE r.end_date IS NOT NULL AND f.doc_type = 'C' AND f.date_key > CAST(replace(r.end_date, '-', '') AS INTEGER)""")[0]
    m["lines_rep_derived"] = q1(con, "SELECT count(*) FROM fact_sales WHERE rep_derived = 1")[0]
    m["unassigned_revenue_naive"] = round(q1(con, "SELECT coalesce(sum(net_amount), 0) FROM stg_invoice_lines WHERE rep_code IS NULL")[0], 2)

    recon = q(con, "SELECT step, label, amount, lines FROM v_reconciliation_2026q3 ORDER BY step")
    keys = ["legacy", "dup_day", "credit", "internal", "explained", "finance", "model", "unexplained"]
    for (step, label, amount, lines), key in zip(recon, keys):
        m[f"recon_{key}"] = amount
        if lines is not None:
            m[f"recon_{key}_lines"] = lines
    m["recon_gap"] = round(m["recon_legacy"] - m["recon_finance"], 2)
    m["recon_gap_pct"] = round(100 * m["recon_gap"] / m["recon_finance"], 1)
    return m


def round_floats(obj):
    if isinstance(obj, float):
        return round(obj, 2)
    if isinstance(obj, dict):
        return {k: round_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [round_floats(v) for v in obj]
    return obj


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(round_floats(data), ensure_ascii=False, indent=1 if path.name == "metrics.json" else None,
                               separators=None if path.name == "metrics.json" else (",", ":")) + "\n", encoding="utf-8")


def site_exports(con: sqlite3.Connection, metrics: dict) -> None:
    reps = [dict(zip(["code", "name", "region", "team", "active"], r)) for r in
            q(con, "SELECT rep_code, rep_name, region, team, is_active FROM dim_rep ORDER BY rep_key")]
    cube = q(con, """SELECT year_month, rep_code, category, segment, round(sum(net_amount), 2), round(sum(gross_margin), 2),
                            count(DISTINCT CASE WHEN doc_type = 'F' THEN invoice_no END)
                     FROM v_sales GROUP BY 1, 2, 3, 4 ORDER BY 1, 2, 3, 4""")
    targets = q(con, "SELECT r.rep_code, t.year_month, t.target_amount FROM fact_target t JOIN dim_rep r USING (rep_key) ORDER BY 2, 1")
    periods = {"ytd": ("2026-01-01", AS_OF), "q3": ("2026-07-01", AS_OF), "12m": ("2025-10-01", AS_OF), "2025": ("2025-01-01", "2025-12-31")}
    customers = {}
    for key, (a, b) in periods.items():
        customers[key] = {seg: n for seg, n in q(con, "SELECT segment, count(DISTINCT customer_no) FROM v_sales WHERE date BETWEEN ? AND ? GROUP BY segment ORDER BY segment", a, b)}
        customers[key]["*"] = q1(con, "SELECT count(DISTINCT customer_no) FROM v_sales WHERE date BETWEEN ? AND ?", a, b)[0]
    top = q(con, "SELECT customer_no, customer_name, segment, territory, net_revenue_12m, margin_pct FROM v_top_customers_12m ORDER BY net_revenue_12m DESC, customer_no LIMIT 10")
    pipeline = q(con, "SELECT stage, opportunities, amount, weighted_amount, stale, without_amount FROM v_pipeline_by_stage ORDER BY stage_order")
    pipe_rep = q(con, """SELECT r.rep_code, count(*), round(sum(coalesce(amount,0)*probability),2), sum(CASE WHEN days_since_update > 60 THEN 1 ELSE 0 END)
                         FROM fact_opportunity f JOIN dim_rep r USING (rep_key) WHERE is_open = 1 GROUP BY 1 ORDER BY 3 DESC, 1""")
    stale = q(con, """SELECT f.opportunity_id, a.account_name, r.rep_code, f.stage, f.amount, f.days_since_update
                      FROM fact_opportunity f JOIN crm_acc a USING (account_id) JOIN dim_rep r USING (rep_key)
                      WHERE f.is_open = 1 AND f.days_since_update > 60 ORDER BY coalesce(f.amount, 0) DESC, f.opportunity_id LIMIT 8""")
    write_json(SITE_DATA / "dashboard.json", {
        "asOf": AS_OF, "reps": reps, "cube": cube, "targets": targets, "customers": customers, "top": top,
        "pipeline": pipeline, "pipelineByRep": pipe_rep, "stale": stale, "kpi": {k: metrics[k] for k in metrics if not k.startswith("rule_")},
    })

    rules = [dict(zip(["id", "title", "severity", "owner", "fix", "before", "after"], r)) for r in q(con, """
        SELECT r.rule_id, r.title, r.severity, r.owner, r.fix, s.issues_before, s.issues_after
        FROM dq_rule r JOIN v_dq_rule_summary s USING (rule_id) ORDER BY r.rule_id""")]
    cols = "account_id, account_name, vat_raw, erp_customer_no, owner_rep, postcode, city, email, phone, created_at"
    pairs = []
    for a_id, b_id, score, band, evidence in q(con, "SELECT account_a, account_b, score, band, evidence FROM dq_duplicate_pair WHERE snapshot = 'before' ORDER BY score DESC, account_a, account_b"):
        a = q1(con, f"SELECT {cols} FROM stg_crm_accounts WHERE account_id = ?", a_id)
        b = q1(con, f"SELECT {cols} FROM stg_crm_accounts WHERE account_id = ?", b_id)
        opp_b = q1(con, "SELECT count(*) FROM stg_crm_opportunities WHERE account_id = ?", b_id)[0]
        decision = q1(con, "SELECT decision, note FROM review_decision WHERE account_a = ? AND account_b = ?", a_id, b_id)
        pairs.append({"a": list(a), "b": list(b), "score": score, "band": band, "evidence": evidence, "oppB": opp_b,
                      "decision": decision[0] if decision else None, "note": decision[1] if decision else None})
    changes = q(con, "SELECT change_type, account_id, field, old_value, new_value, reason FROM crm_change_log ORDER BY change_id LIMIT 12")
    write_json(SITE_DATA / "dq.json", {"rules": rules, "pairs": pairs, "changes": changes,
                                       "health": {s: q1(con, "SELECT accounts_in_scope, accounts_clean, health_pct FROM dq_health WHERE snapshot = ?", s) for s in ("before", "after")}})

    bridge = q(con, "SELECT step, label, amount, lines FROM v_reconciliation_2026q3 ORDER BY step")
    monthly = q(con, """SELECT f.period, CAST(f.amount AS REAL), (SELECT round(sum(net_amount), 2) FROM v_sales s WHERE s.year_month = f.period)
                        FROM src_finance_revenue_2026q3 f ORDER BY 1""")
    dup_day = q1(con, "SELECT invoice_date, count(*) FROM v_legacy_duplicate_rows GROUP BY invoice_date ORDER BY 2 DESC LIMIT 1")
    write_json(SITE_DATA / "recon.json", {"bridge": bridge, "monthly": monthly, "dupDay": dup_day})


def slim_copy() -> None:
    """The browser SQL console gets the model and the DQ tables, not the raw extracts."""
    target = SITE_DATA / "warehouse.sqlite"
    if target.exists():
        target.unlink()
    shutil.copy(WAREHOUSE, target)
    con = sqlite3.connect(target)
    drop = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND (name LIKE 'src_%' OR name IN ('stg_invoice_lines', 'legacy_export'))")]
    keep_src = {"src_finance_revenue_2026q3"}
    for t in drop:
        if t not in keep_src:
            con.execute(f'DROP TABLE "{t}"')
    for (idx,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'index' AND sql IS NOT NULL").fetchall():
        con.execute(f'DROP INDEX "{idx}"')  # a read-only console on ± 76.000 rows does not need them
    # views that read dropped tables are removed too, so every view in the console works
    for v in ("v_legacy_duplicate_rows", "v_reconciliation_2026q3"):
        con.execute(f"DROP VIEW IF EXISTS {v}")
    con.commit()
    con.execute("VACUUM")
    con.close()


def main() -> None:
    WAREHOUSE.parent.mkdir(parents=True, exist_ok=True)
    if WAREHOUSE.exists():
        WAREHOUSE.unlink()
    con = sqlite3.connect(WAREHOUSE)

    load_raw(con)
    create_dq_tables(con)
    run_sql(con, sql_file("01_staging.sql"))
    log("stage", "staging tables built")

    build_working_crm(con)
    run_checks(con, "before")
    export_queue(con)

    con.execute("CREATE TABLE review_decision (account_a TEXT, account_b TEXT, decision TEXT, note TEXT, reviewer TEXT, decided_on TEXT)")
    if DECISIONS.exists():
        with open(DECISIONS, newline="", encoding="utf-8") as fh:
            con.executemany("INSERT INTO review_decision VALUES (:account_a, :account_b, :decision, :note, :reviewer, :decided_on)", list(csv.DictReader(fh)))
    apply_corrections(con)
    run_checks(con, "after")

    run_sql(con, sql_file("03_model.sql"))
    run_sql(con, sql_file("04_views.sql"))
    run_sql(con, sql_file("05_reconciliation.sql"))
    log("model", "star schema + views + reconciliation built")
    con.commit()

    metrics = build_metrics(con)
    write_json(METRICS, metrics)
    site_exports(con, metrics)
    con.close()
    slim_copy()
    log("publish", f"net revenue YTD € {metrics['net_revenue_ytd']:,.2f} · Q3 gap Excel vs finance € {metrics['recon_gap']:,.2f} · unexplained € {metrics['recon_unexplained']:,.2f}")


if __name__ == "__main__":
    main()
