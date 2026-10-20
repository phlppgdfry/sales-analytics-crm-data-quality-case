"""Every number in docs and site comes from data/metrics.json, and the site data agrees with it."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_docs_are_up_to_date():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_docs.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_site_data_matches_metrics(metrics):
    dash = json.loads((ROOT / "site" / "data" / "dashboard.json").read_text(encoding="utf-8"))
    dq = json.loads((ROOT / "site" / "data" / "dq.json").read_text(encoding="utf-8"))
    for key in ("net_revenue_ytd", "weighted_pipeline", "dq_health_after", "recon_gap"):
        assert dash["kpi"][key] == metrics[key]
    assert dq["health"]["after"][2] == metrics["dq_health_after"]
    assert len(dq["pairs"]) == metrics["dup_pairs_before"]
    ytd = sum(r[4] for r in dash["cube"] if "2026-01" <= r[0] <= "2026-09")
    assert round(ytd, 2) == metrics["net_revenue_ytd"]
