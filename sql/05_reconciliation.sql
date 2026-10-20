-- 05_reconciliation.sql — why the weekly sales Excel says more than finance for Q3 2026, to the cent.
-- Inputs: the legacy export the Excel is built on (src_legacy_sales_export_2026q3)
--         and the revenue finance booked on GL 700000 (src_finance_revenue_2026q3).
-- Each bridge step is computed from the data, never typed in. tests/test_reconciliation.py checks the bridge closes.

DROP TABLE IF EXISTS legacy_export;
CREATE TABLE legacy_export AS
SELECT row_number() OVER ()      AS row_id,
       date(Datum)               AS invoice_date,
       Factuur                   AS invoice_no,
       Klant                     AS customer_no,
       Artikel                   AS sku,
       nullif(Verkoper, '')      AS rep_code,
       CAST(Bedrag AS REAL)      AS amount
FROM src_legacy_sales_export_2026q3;

-- rows that occur more than once (same invoice, same article, same day): the export job ran twice on one day
DROP VIEW IF EXISTS v_legacy_duplicate_rows;
CREATE VIEW v_legacy_duplicate_rows AS
SELECT e.*
FROM legacy_export e
WHERE e.row_id NOT IN (SELECT min(row_id) FROM legacy_export GROUP BY invoice_no, sku, invoice_date, amount);

DROP VIEW IF EXISTS v_reconciliation_2026q3;
CREATE VIEW v_reconciliation_2026q3 AS
WITH legacy AS (SELECT round(sum(amount), 2) AS v FROM legacy_export),
dups AS (SELECT round(sum(amount), 2) AS v, count(*) AS n FROM v_legacy_duplicate_rows),
credit AS (
  SELECT round(sum(amount), 2) AS v, count(*) AS n FROM legacy_export
  WHERE invoice_no LIKE 'C%' AND row_id NOT IN (SELECT row_id FROM v_legacy_duplicate_rows)
),
internal AS (
  SELECT round(sum(CASE WHEN invoice_no LIKE 'C%' THEN -amount ELSE amount END), 2) AS v, count(*) AS n FROM legacy_export
  WHERE customer_no = 'C99999' AND row_id NOT IN (SELECT row_id FROM v_legacy_duplicate_rows)
),
finance AS (SELECT round(sum(CAST(amount AS REAL)), 2) AS v FROM src_finance_revenue_2026q3),
model AS (
  SELECT round(sum(net_amount), 2) AS v FROM v_sales WHERE date BETWEEN '2026-07-01' AND '2026-09-30'
)
SELECT 1 AS step, 'Wekelijks Excel-rapport (export, Q3 2026)' AS label, legacy.v AS amount, NULL AS lines FROM legacy
UNION ALL SELECT 2, 'Dubbel geëxporteerde dag eraf', -dups.v, dups.n FROM dups
UNION ALL SELECT 3, 'Creditnota''s: opgeteld i.p.v. afgetrokken (2×)', -2 * credit.v, credit.n FROM credit
UNION ALL SELECT 4, 'Personeelsshop (interne klant) eraf', -internal.v, internal.n FROM internal
UNION ALL SELECT 5, 'Verklaard totaal', round(legacy.v - dups.v - 2 * credit.v - internal.v, 2), NULL FROM legacy, dups, credit, internal
UNION ALL SELECT 6, 'Finance (grootboek 700000)', finance.v, NULL FROM finance
UNION ALL SELECT 7, 'Datawarehouse (v_sales, Netto-omzet)', model.v, NULL FROM model
UNION ALL SELECT 8, 'Onverklaard verschil', round(legacy.v - dups.v - 2 * credit.v - internal.v - finance.v, 2), NULL
          FROM legacy, dups, credit, internal, finance;
