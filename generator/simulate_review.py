#!/usr/bin/env python3
"""Simulate the human review of the duplicate queue (data/review/duplicate_queue.csv).

In the case, the data analyst walks through the queue with each account owner in two sessions.
They know things the algorithm cannot: that "Zorggroep Ter Leie – campus Noord" and "– campus Zuid"
are one legal entity with two delivery sites, not a duplicate. This script plays that reviewer, using
the generator's ground truth, and writes data/review/decisions.csv, which the pipeline then applies.

Run order: generator -> pipeline (writes the queue) -> this script -> pipeline (applies decisions).
"""
from __future__ import annotations

import csv
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "data" / "review" / "duplicate_queue.csv"
OUT = ROOT / "data" / "review" / "decisions.csv"


def main() -> None:
    planted = json.load(open(ROOT / "data" / "raw" / "_planted.json", encoding="utf-8"))
    accounts = list(csv.DictReader(open(ROOT / "data" / "raw" / "crm_accounts.csv", encoding="utf-8")))
    cust_to_acc = {a["erp_customer_no"]: a["account_id"] for a in accounts if a["erp_customer_no"]}

    truth = {frozenset(p) for c in planted["duplicate_clusters"] for p in itertools.combinations(c, 2)}
    multi_site = {frozenset(p) for g in planted["multi_site_groups"]
                  for p in itertools.combinations([cust_to_acc[c] for c in g if c in cust_to_acc], 2)}

    queue = list(csv.DictReader(open(QUEUE, encoding="utf-8")))
    later_budget = 5  # weakest true matches: the owner wants to check with the customer first
    rows = []
    for i, q in enumerate(sorted(queue, key=lambda q: int(q["score"]))):
        pair = frozenset((q["account_a"], q["account_b"]))
        if pair in truth:
            if int(q["score"]) < 50 and later_budget > 0:
                decision, note = "later", "accounteigenaar bevestigt eerst bij de klant"
                later_budget -= 1
            else:
                decision, note = "samenvoegen", "zelfde klant"
        elif pair in multi_site:
            decision, note = "geen duplicaat", "multi-site: één vennootschap, aparte leverplaats"
        else:
            decision, note = "geen duplicaat", "andere klant; naam lijkt, gegevens verschillen"
        session = "2026-10-06" if q["band"] == "waarschijnlijk" else "2026-10-08"
        rows.append([q["account_a"], q["account_b"], decision, note, "data analyst + accounteigenaar", session])
    rows.sort(key=lambda r: (r[0], r[1]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["account_a", "account_b", "decision", "note", "reviewer", "decided_on"])
        w.writerows(rows)
    print(f"{len(rows)} decisions written")


if __name__ == "__main__":
    main()
