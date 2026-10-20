"""Traceability: every KPI in the catalog has a DAX measure and an existing SQL object; every column a measure uses exists."""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "powerbi" / "Vennaert Sales.SemanticModel" / "definition"
MEASURES = (MODEL / "tables" / "Measures.tmdl").read_text(encoding="utf-8")
CATALOG = list(csv.DictReader(open(ROOT / "data" / "reference" / "kpi_catalog.csv", encoding="utf-8")))


def measure_names():
    return {m.strip("'") for m in re.findall(r"^\tmeasure ('[^']+'|\S+)", MEASURES, re.M)}


def model_columns():
    cols = {}
    for f in (MODEL / "tables").glob("*.tmdl"):
        text = f.read_text(encoding="utf-8")
        table = re.search(r"^table (\S+)", text, re.M).group(1)
        cols[table] = set(re.findall(r"^\tcolumn (\S+)", text, re.M))
    return cols


def test_every_kpi_has_a_measure():
    names = measure_names()
    missing = [k["kpi_id"] for k in CATALOG if k["dax_measure"] not in names]
    assert not missing


def test_every_kpi_id_is_documented_in_the_model():
    for k in CATALOG:
        assert k["kpi_id"] in MEASURES, f"{k['kpi_id']} has no description line in Measures.tmdl"


def test_every_kpi_has_an_existing_sql_object(con):
    for k in CATALOG:
        obj, col = k["sql_object"].split(".")
        cols = [r[1] for r in con.execute(f"PRAGMA table_info({obj})")]
        assert col in cols, k["sql_object"]


def test_measures_only_use_existing_columns():
    cols = model_columns()
    for table, column in re.findall(r"(\w+)\[(\w+)\]", MEASURES):
        if table in cols:
            assert column in cols[table], f"{table}[{column}]"


def test_measures_reference_existing_measures():
    names = measure_names()
    body = re.sub(r"(\w+)\[\w+\]", "", MEASURES)  # drop Table[Column] references
    for ref in re.findall(r"\[([^\]]+)\]", body):
        if ref != "Placeholder":
            assert ref in names, ref


def test_rls_role_filters_on_rep_email():
    role = (MODEL / "roles" / "Accountmanager.tmdl").read_text(encoding="utf-8")
    assert "tablePermission dim_rep = dim_rep[email] = USERPRINCIPALNAME ()" in role
