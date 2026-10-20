"""Duplicate detection for CRM accounts: normalise names, generate candidate pairs, score them.

Candidate pairs come from SQL (cheap "blocking": only compare accounts that share a VAT number,
or a postcode/city and the start or end of the name). Scoring happens here because string
similarity is easier to read in Python than in SQL. The weights are documented in
docs/05-crm-quality/duplicates.md and are deliberately simple enough to explain on a whiteboard.
"""
from __future__ import annotations

import re
import sqlite3
import unicodedata
from difflib import SequenceMatcher

LEGAL_FORMS = {"nv", "bv", "bvba", "vof", "cv", "vzw", "sa", "srl", "sprl", "asbl", "sas", "sarl", "sc"}

# weights (see docs/05-crm-quality/duplicates.md)
W_VAT_SAME = 45
W_VAT_CONFLICT = -40      # both VAT numbers valid and different -> two legal entities
W_NAME = [(0.95, 35), (0.88, 28), (0.80, 18)]
W_POSTCODE = 15
W_CITY = 5                # only when the postcode differs
W_CONTACT = 5             # same phone or same e-mail domain
BAND_LIKELY = 75
BAND_REVIEW = 40


def normalise_name(name: str) -> str:
    """'Schoonmaakbedrijf Declercq NV' -> 'schoonmaakbedrijf declercq'. Accents, case, punctuation, legal form removed."""
    text = unicodedata.normalize("NFKD", name or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = text.replace("&", " en ")
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    words = [w for w in text.split() if w not in LEGAL_FORMS]
    return " ".join(words)


def name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def digits(text: str | None) -> str:
    return "".join(ch for ch in (text or "") if ch.isdigit())


def email_domain(email: str | None) -> str | None:
    return email.split("@", 1)[1] if email and "@" in email else None


def score_pair(a: dict, b: dict) -> tuple[int, list[str]]:
    """Return (score 0..100, evidence) for two account rows (dicts with the crm_acc columns + vat_valid)."""
    score, evidence = 0, []
    if a["vat_norm"] and b["vat_norm"]:
        if a["vat_norm"] == b["vat_norm"]:
            score += W_VAT_SAME
            evidence.append("zelfde btw-nummer")
        elif a["vat_valid"] == 1 and b["vat_valid"] == 1:
            score += W_VAT_CONFLICT
            evidence.append("verschillend geldig btw-nummer")
    sim = name_similarity(a["name_norm"], b["name_norm"])
    for threshold, points in W_NAME:
        if sim >= threshold:
            score += points
            evidence.append(f"naam {round(sim * 100)}% gelijk")
            break
    if digits(a["postcode"]) and digits(a["postcode"]) == digits(b["postcode"]):
        score += W_POSTCODE
        evidence.append("zelfde postcode")
    elif (a["city"] or "").lower() == (b["city"] or "").lower():
        score += W_CITY
        evidence.append("zelfde gemeente")
    if (a["phone"] and a["phone"] == b["phone"]) or (email_domain(a["email"]) and email_domain(a["email"]) == email_domain(b["email"])):
        score += W_CONTACT
        evidence.append("zelfde telefoon of e-maildomein")
    return max(0, min(100, score)), evidence


CANDIDATES_SQL = """
WITH a AS (
  SELECT c.*, v.vat_valid,
         replace(replace(c.postcode, 'B-', ''), ' ', '') AS pc
  FROM crm_acc c JOIN v_vat_check v USING (account_id)
  WHERE c.merged_into IS NULL
)
SELECT DISTINCT x.account_id AS id_a, y.account_id AS id_b
FROM a x JOIN a y ON x.account_id < y.account_id
WHERE (x.vat_norm IS NOT NULL AND x.vat_norm = y.vat_norm)
   OR (x.pc = y.pc AND substr(x.name_norm, 1, 5) = substr(y.name_norm, 1, 5))
   OR (x.pc = y.pc AND substr(x.name_norm, -5) = substr(y.name_norm, -5))
   OR (lower(x.city) = lower(y.city) AND substr(x.name_norm, 1, 8) = substr(y.name_norm, 1, 8))
ORDER BY 1, 2
"""


def find_pairs(con: sqlite3.Connection, snapshot: str) -> list[tuple]:
    """Score all candidate pairs and store those >= BAND_REVIEW in dq_duplicate_pair."""
    con.row_factory = sqlite3.Row
    rows = {r["account_id"]: dict(r) for r in con.execute(
        "SELECT c.*, v.vat_valid FROM crm_acc c JOIN v_vat_check v USING (account_id) WHERE c.merged_into IS NULL")}
    out = []
    for cand in con.execute(CANDIDATES_SQL).fetchall():
        a, b = rows[cand["id_a"]], rows[cand["id_b"]]
        score, evidence = score_pair(a, b)
        if score < BAND_REVIEW:
            continue
        # account_a = the record that would survive a merge (ERP-linked first, then the oldest)
        first, second = sorted([a, b], key=lambda r: (r["erp_customer_no"] is None, r["created_at"], r["account_id"]))
        band = "waarschijnlijk" if score >= BAND_LIKELY else "beoordelen"
        out.append((snapshot, first["account_id"], second["account_id"], score, band, "; ".join(evidence)))
    con.row_factory = None
    con.execute("DELETE FROM dq_duplicate_pair WHERE snapshot = ?", (snapshot,))
    con.executemany("INSERT INTO dq_duplicate_pair (snapshot, account_a, account_b, score, band, evidence) VALUES (?,?,?,?,?,?)", out)
    return out
