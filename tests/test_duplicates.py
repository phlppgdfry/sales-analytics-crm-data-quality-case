"""CRM-01: duplicate detection finds the planted duplicates, and the review step protects multi-site customers."""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "etl"))
from duplicates import BAND_LIKELY, normalise_name, score_pair  # noqa: E402

from conftest import ids  # noqa: E402


def row(**kw):
    base = {"vat_norm": None, "vat_valid": None, "name_norm": "", "postcode": "", "city": "", "phone": None, "email": None}
    base.update(kw)
    return base


def test_normalise_name():
    assert normalise_name("Schoonmaakbedrijf Declercq NV") == "schoonmaakbedrijf declercq"
    assert normalise_name("HÔTEL LE CLOS SRL") == "hotel le clos"
    assert normalise_name("Net & Proper  Maes bv") == "net en proper maes"


def test_same_vat_same_name_is_likely():
    a = row(vat_norm="BE0412345678", vat_valid=1, name_norm="hotel ter linde", postcode="8400", city="Oostende")
    s, ev = score_pair(a, dict(a))
    assert s >= BAND_LIKELY and "zelfde btw-nummer" in ev


def test_two_valid_different_vats_are_two_companies():
    a = row(vat_norm="BE0412345678", vat_valid=1, name_norm="hotel ter linde", postcode="8400")
    b = row(vat_norm="BE0499999999", vat_valid=1, name_norm="hotel ter linde", postcode="8400")
    s, _ = score_pair(a, b)
    assert s < 40


def test_recall_on_planted_duplicates(con, planted):
    found = {frozenset(r) for r in con.execute("SELECT account_a, account_b FROM dq_duplicate_pair WHERE snapshot = 'before'")}
    truth = {frozenset(p) for c in planted["duplicate_clusters"] for p in itertools.combinations(c, 2)}
    recall = len(truth & found) / len(truth)
    assert recall >= 0.95, f"recall {recall:.1%}"


def test_precision_is_reported_not_assumed(con, planted, metrics):
    # the queue contains pairs that are NOT duplicates; that is why nothing merges without a human decision
    assert metrics["review_geen_duplicaat"] > 0


def test_multi_site_customers_never_merged(con, planted):
    for group in planted["multi_site_groups"]:
        accounts = ids(con, f"SELECT account_id FROM crm_acc WHERE erp_customer_no IN ({','.join('?' * len(group))})", *group)
        merged = ids(con, f"SELECT account_id FROM crm_acc WHERE merged_into IS NOT NULL AND account_id IN ({','.join('?' * len(accounts))})", *accounts)
        assert not merged, f"multi-site group merged: {group}"


def test_merge_keeps_the_erp_linked_record(con):
    bad = con.execute("""
        SELECT l.account_id FROM crm_acc l JOIN crm_acc s ON s.account_id = l.merged_into
        WHERE l.erp_customer_no IS NOT NULL AND s.erp_customer_no IS NULL""").fetchall()
    assert not bad


def test_nothing_deleted_and_every_merge_logged(con, metrics):
    assert con.execute("SELECT count(*) FROM crm_acc").fetchone()[0] == metrics["n_crm_accounts"]
    merged = con.execute("SELECT count(*) FROM crm_acc WHERE merged_into IS NOT NULL").fetchone()[0]
    logged = con.execute("SELECT count(*) FROM crm_change_log WHERE change_type = 'merge'").fetchone()[0]
    assert merged == logged > 0


def test_opportunities_follow_the_survivor(con):
    orphans = con.execute("""SELECT count(*) FROM crm_opp o JOIN crm_acc a USING (account_id) WHERE a.merged_into IS NOT NULL""").fetchone()[0]
    assert orphans == 0


def test_deferred_pairs_stay_in_the_queue(con, metrics):
    assert metrics["dup_pairs_after"] == metrics["review_later"]
