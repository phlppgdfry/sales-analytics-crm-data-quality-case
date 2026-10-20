"""Shared fixtures: the tests read the warehouse that etl/pipeline.py builds (and build it if it is missing)."""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WAREHOUSE = ROOT / "warehouse" / "vennaert.sqlite"


@pytest.fixture(scope="session")
def con():
    if not WAREHOUSE.exists():
        subprocess.run([sys.executable, str(ROOT / "etl" / "pipeline.py")], check=True, capture_output=True)
    c = sqlite3.connect(WAREHOUSE)
    yield c
    c.close()


@pytest.fixture(scope="session")
def planted():
    return json.loads((ROOT / "data" / "raw" / "_planted.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def metrics():
    return json.loads((ROOT / "data" / "metrics.json").read_text(encoding="utf-8"))


def ids(con, sql, *args) -> set:
    return {r[0] for r in con.execute(sql, args)}
