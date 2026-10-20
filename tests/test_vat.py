"""CRM-02: Belgian and French VAT check digits, tested on hand-checked numbers."""
import sqlite3

import pytest



def be_check(body8: int) -> int:
    return 97 - body8 % 97


def fr_key(siren: int) -> int:
    return (12 + 3 * (siren % 97)) % 97


@pytest.fixture()
def mem(con):
    m = sqlite3.connect(":memory:")
    view = [s for s in (con.execute("SELECT sql FROM sqlite_master WHERE name = 'v_vat_check'").fetchone()[0],)][0]
    m.execute("CREATE TABLE crm_acc (account_id TEXT, vat_norm TEXT)")
    m.execute(view)
    return m


def check(mem, vat):
    mem.execute("DELETE FROM crm_acc")
    mem.execute("INSERT INTO crm_acc VALUES ('x', ?)", (vat,))
    return mem.execute("SELECT vat_valid FROM v_vat_check").fetchone()[0]


def test_valid_belgian_number(mem):
    body = 4123456                     # 0412.345.6xx
    vat = f"BE0{body:07d}{be_check(body):02d}"
    assert check(mem, vat) == 1


def test_one_wrong_digit_fails(mem):
    body = 4123456
    vat = f"BE0{body:07d}{be_check(body):02d}"
    wrong = vat[:6] + str((int(vat[6]) + 1) % 10) + vat[7:]
    assert check(mem, wrong) == 0


def test_check_digit_97(mem):
    # a body that is a multiple of 97 has check digits 97, not 00
    body = 97 * 50000
    assert be_check(body) == 97
    assert check(mem, f"BE0{body:07d}97") == 1


def test_french_key(mem):
    siren = 404833048
    assert check(mem, f"FR{fr_key(siren):02d}{siren}") == 1
    assert check(mem, f"FR{(fr_key(siren) + 1) % 97:02d}{siren}") == 0


def test_garbage_is_invalid_and_empty_is_unknown(mem):
    assert check(mem, "BE04123") == 0
    assert check(mem, None) is None


def test_staging_normalises_notations(con):
    # "BE 0412.345.678", "0412345678", "be0412345678" all become BE0412345678
    rows = con.execute("SELECT vat_raw, vat_norm FROM stg_crm_accounts WHERE vat_raw LIKE 'BE %' OR vat_raw LIKE 'be%' OR vat_raw GLOB '[0-9]*' LIMIT 50").fetchall()
    assert rows, "the generator plants alternative notations"
    for raw, norm in rows:
        assert norm.startswith("BE0") and len(norm) == 12 and norm[2:] == "".join(c for c in raw if c.isdigit()).rjust(10, "0")
