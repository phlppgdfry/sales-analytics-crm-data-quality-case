#!/usr/bin/env python3
"""Run sql/tsql/*.sql on a SQL Server container and check the KPIs against data/metrics.json.

Used in CI (job "sqlserver"). Expects a container named `mssql` with sql/tsql mounted on /sql and
warehouse/export on /data, and the sa password in $MSSQL_SA_PASSWORD.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SQLCMD = ["docker", "exec", "mssql", "/opt/mssql-tools18/bin/sqlcmd", "-C", "-S", "localhost", "-U", "sa",
          "-P", os.environ.get("MSSQL_SA_PASSWORD", ""), "-b"]


def run_file(name: str) -> None:
    r = subprocess.run(SQLCMD + ["-i", f"/sql/{name}"], capture_output=True, text=True)
    print(f"-- {name}: exit {r.returncode}")
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        sys.exit(1)


def query(sql: str) -> list[list[str]]:
    r = subprocess.run(SQLCMD + ["-d", "VennaertDWH", "-h", "-1", "-W", "-s", "|", "-Q", "SET NOCOUNT ON; " + sql],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        sys.exit(1)
    return [line.split("|") for line in r.stdout.strip().splitlines() if line.strip()]


def main() -> None:
    for f in ("01_schema.sql", "02_load.sql", "03_views.sql"):
        run_file(f)
    m = json.loads((ROOT / "data" / "metrics.json").read_text(encoding="utf-8"))
    counts = query("SELECT (SELECT COUNT(*) FROM dwh.fact_sales), (SELECT COUNT(*) FROM dwh.fact_opportunity)")[0]
    ytd = query("SELECT net_revenue_ytd, net_revenue_ytd_prev, growth_pct, gross_margin_ytd, margin_pct_ytd, target_ytd, "
                "target_attainment_pct, active_customers_ytd, avg_invoice_value_ytd FROM dwh.v_kpi_ytd")[0]
    pipe = query("SELECT SUM(opportunities), SUM(amount), SUM(weighted_amount), SUM(stale), SUM(without_amount) FROM dwh.v_pipeline_by_stage")[0]
    win = query("SELECT won, lost, win_rate_pct FROM dwh.v_win_rate_12m")[0]
    dq = query("SELECT SUM(issues_before), SUM(issues_after) FROM dwh.v_dq_rule_summary")[0]

    checks = [
        ("fact_sales rows", int(counts[0]), m["n_invoice_lines"]),
        ("net_revenue_ytd", float(ytd[0]), m["net_revenue_ytd"]),
        ("net_revenue_ytd_prev", float(ytd[1]), m["net_revenue_ytd_prev"]),
        ("growth_pct", float(ytd[2]), m["growth_pct"]),
        ("gross_margin_ytd", float(ytd[3]), m["gross_margin_ytd"]),
        ("margin_pct_ytd", float(ytd[4]), m["margin_pct_ytd"]),
        ("target_ytd", float(ytd[5]), m["target_ytd"]),
        ("target_attainment_pct", float(ytd[6]), m["target_attainment_pct"]),
        ("active_customers_ytd", int(ytd[7]), m["active_customers_ytd"]),
        ("avg_invoice_value_ytd", float(ytd[8]), m["avg_invoice_value_ytd"]),
        ("open_opportunities", int(pipe[0]), m["open_opportunities"]),
        ("open_pipeline", float(pipe[1]), m["open_pipeline"]),
        ("weighted_pipeline", float(pipe[2]), m["weighted_pipeline"]),
        ("stale_opportunities", int(pipe[3]), m["stale_opportunities"]),
        ("win_rate_12m_pct", float(win[2]), m["win_rate_12m_pct"]),
        ("dq_issues_before", int(dq[0]), m["dq_issues_before"]),
        ("dq_issues_after", int(dq[1]), m["dq_issues_after"]),
    ]
    failed = 0
    for name, got, want in checks:
        ok = abs(got - want) < 0.005
        failed += not ok
        print(f"{'OK  ' if ok else 'FAIL'} {name:<24} SQL Server {got:>16,.2f}   SQLite {want:>16,.2f}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
