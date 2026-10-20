-- 01_staging.sql — typed, cleaned copies of the raw extracts (src_* = everything TEXT, as loaded from CSV).
-- Rule of thumb: staging fixes *format* (types, trimming, VAT notation), never *meaning*.
-- Business corrections (merges, links, owner changes) happen later and are logged.

DROP TABLE IF EXISTS stg_sales_reps;
CREATE TABLE stg_sales_reps AS
SELECT trim(rep_code)                        AS rep_code,
       trim(name)                            AS rep_name,
       trim(region)                          AS region,
       trim(team)                            AS team,
       lower(trim(email))                    AS email,
       date(start_date)                      AS start_date,
       nullif(trim(end_date), '')            AS end_date
FROM src_erp_sales_reps;

DROP TABLE IF EXISTS stg_products;
CREATE TABLE stg_products AS
SELECT trim(sku)                             AS sku,
       trim(description)                     AS description,
       nullif(trim(category), '')            AS category,
       trim(brand)                           AS brand,
       CAST(unit_cost AS REAL)               AS unit_cost,
       CAST(list_price AS REAL)              AS list_price
FROM src_erp_products;

-- VAT numbers arrive as "BE 0412.345.678", "0412345678", "be0412345678" ... -> one notation: BE0412345678 / FR12345678901
DROP TABLE IF EXISTS stg_customers;
CREATE TABLE stg_customers AS
WITH c AS (
  SELECT *, upper(replace(replace(replace(replace(trim(vat_number), ' ', ''), '.', ''), '-', ''), '/', '')) AS vat_compact
  FROM src_erp_customers
)
SELECT trim(customer_no)                     AS customer_no,
       trim(name)                            AS customer_name,
       CASE WHEN vat_compact = ''                                   THEN NULL
            WHEN vat_compact LIKE 'BE%' OR vat_compact LIKE 'FR%'   THEN vat_compact
            WHEN length(vat_compact) = 10 AND country = 'BE'        THEN 'BE' || vat_compact
            WHEN length(vat_compact) = 9  AND country = 'BE'        THEN 'BE0' || vat_compact
            ELSE vat_compact END             AS vat_norm,
       trim(postcode)                        AS postcode,
       trim(city)                            AS city,
       trim(country)                         AS country,
       trim(language)                        AS language,
       trim(segment)                         AS segment,
       trim(territory)                       AS territory,
       date(created_on)                      AS created_on,
       CASE WHEN segment = 'Intern' THEN 1 ELSE 0 END AS is_internal
FROM c;

DROP TABLE IF EXISTS stg_customer_rep_history;
CREATE TABLE stg_customer_rep_history AS
SELECT trim(customer_no) AS customer_no, trim(rep_code) AS rep_code, date(valid_from) AS valid_from, date(valid_to) AS valid_to
FROM src_erp_customer_rep_history;

-- Credit notes (doc_type C) are exported with POSITIVE amounts. Staging adds the sign; that single line
-- is the difference between the sales report and finance (see sql/05_reconciliation.sql).
DROP TABLE IF EXISTS stg_invoice_lines;
CREATE TABLE stg_invoice_lines AS
SELECT trim(invoice_no)                                           AS invoice_no,
       trim(doc_type)                                             AS doc_type,
       date(invoice_date)                                         AS invoice_date,
       trim(customer_no)                                          AS customer_no,
       trim(sku)                                                  AS sku,
       CAST(qty AS INTEGER) * CASE WHEN doc_type = 'C' THEN -1 ELSE 1 END                    AS qty,
       CAST(unit_price AS REAL)                                   AS unit_price,
       CAST(discount_pct AS REAL)                                 AS discount_pct,
       CAST(line_amount AS REAL) * CASE WHEN doc_type = 'C' THEN -1 ELSE 1 END               AS net_amount,
       CAST(unit_cost AS REAL) * CAST(qty AS INTEGER) * CASE WHEN doc_type = 'C' THEN -1 ELSE 1 END AS cost_amount,
       nullif(trim(rep_code), '')                                 AS rep_code
FROM src_erp_invoice_lines;

DROP TABLE IF EXISTS stg_crm_accounts;
CREATE TABLE stg_crm_accounts AS
WITH a AS (
  SELECT *, upper(replace(replace(replace(replace(trim(vat_number), ' ', ''), '.', ''), '-', ''), '/', '')) AS vat_compact
  FROM src_crm_accounts
)
SELECT trim(account_id)                      AS account_id,
       trim(name)                            AS account_name,
       nullif(trim(vat_number), '')          AS vat_raw,
       CASE WHEN vat_compact = ''                                   THEN NULL
            WHEN vat_compact LIKE 'BE%' OR vat_compact LIKE 'FR%'   THEN vat_compact
            WHEN length(vat_compact) = 10 AND country = 'BE'        THEN 'BE' || vat_compact
            WHEN length(vat_compact) = 9  AND country = 'BE'        THEN 'BE0' || vat_compact
            ELSE vat_compact END             AS vat_norm,
       nullif(trim(erp_customer_no), '')     AS erp_customer_no,
       trim(owner_rep)                       AS owner_rep,
       trim(segment)                         AS segment,
       trim(region)                          AS region,
       trim(postcode)                        AS postcode,
       trim(city)                            AS city,
       trim(country)                         AS country,
       nullif(lower(trim(email)), '')        AS email,
       nullif(trim(phone), '')               AS phone,
       date(created_at)                      AS created_at,
       date(last_activity)                   AS last_activity
FROM a;

DROP TABLE IF EXISTS stg_crm_opportunities;
CREATE TABLE stg_crm_opportunities AS
SELECT trim(opportunity_id)                  AS opportunity_id,
       trim(account_id)                      AS account_id,
       trim(owner_rep)                       AS owner_rep,
       trim(stage)                           AS stage,
       CAST(nullif(trim(amount), '') AS REAL) AS amount,
       date(expected_close)                  AS expected_close,
       date(created_at)                      AS created_at,
       date(last_update)                     AS last_update,
       nullif(trim(lost_reason), '')         AS lost_reason
FROM src_crm_opportunities;

DROP TABLE IF EXISTS stg_targets;
CREATE TABLE stg_targets AS
SELECT CAST(year AS INTEGER) AS year, CAST(month AS INTEGER) AS month, trim(rep_code) AS rep_code,
       CAST(target_amount AS REAL) AS target_amount
FROM src_sales_targets_2026;
