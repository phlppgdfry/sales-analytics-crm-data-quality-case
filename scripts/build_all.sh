#!/usr/bin/env bash
# Rebuild everything from scratch: sources -> pipeline -> review -> pipeline -> Power BI tables -> Excel -> docs.
# Deterministic: run it twice and `git status` shows no changes.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 generator/generate_sources.py
python3 etl/pipeline.py > /dev/null          # writes the duplicate queue
python3 generator/simulate_review.py          # the simulated reviewers decide
python3 etl/pipeline.py                       # applies the decisions
python3 scripts/build_tmdl.py
python3 excel/build_workbook.py
python3 scripts/build_docs.py
