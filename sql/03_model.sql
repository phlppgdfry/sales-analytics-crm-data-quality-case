-- 03_model.sql — star schema for the sales report (the shape Power BI wants: facts in the middle, dimensions around).
-- Grain:
--   fact_sales        one row per invoice or credit-note line (credit notes negative)
--   fact_opportunity  one row per opportunity, current state as of meta.as_of_date
--   fact_target       one row per rep per month
-- Runs after the CRM corrections, so dim_customer and fact_opportunity use the cleaned CRM (crm_acc / crm_opp).

DROP TABLE IF EXISTS dim_date;
CREATE TABLE dim_date AS
WITH RECURSIVE d(day) AS (
  SELECT date('2025-01-01')
  UNION ALL SELECT date(day, '+1 day') FROM d WHERE day < date('2026-12-31')
)
SELECT CAST(strftime('%Y%m%d', day) AS INTEGER)                  AS date_key,
       day                                                       AS date,
       CAST(strftime('%Y', day) AS INTEGER)                      AS year,
       (CAST(strftime('%m', day) AS INTEGER) + 2) / 3            AS quarter,
       CAST(strftime('%m', day) AS INTEGER)                      AS month,
       strftime('%Y-%m', day)                                    AS year_month,
       CASE CAST(strftime('%m', day) AS INTEGER)
         WHEN 1 THEN 'jan' WHEN 2 THEN 'feb' WHEN 3 THEN 'mrt' WHEN 4 THEN 'apr' WHEN 5 THEN 'mei' WHEN 6 THEN 'jun'
         WHEN 7 THEN 'jul' WHEN 8 THEN 'aug' WHEN 9 THEN 'sep' WHEN 10 THEN 'okt' WHEN 11 THEN 'nov' ELSE 'dec' END AS month_short_nl,
       CASE WHEN strftime('%w', day) IN ('0', '6') THEN 0 ELSE 1 END AS is_weekday
FROM d;

DROP TABLE IF EXISTS dim_rep;
CREATE TABLE dim_rep AS
SELECT row_number() OVER (ORDER BY rep_code) AS rep_key, rep_code, rep_name, region, team, email, start_date, end_date,
       CASE WHEN end_date IS NULL OR end_date >= (SELECT as_of_date FROM meta) THEN 1 ELSE 0 END AS is_active
FROM stg_sales_reps
UNION ALL
SELECT 0, 'ONB', 'Niet toegewezen', 'Onbekend', 'Onbekend', NULL, NULL, NULL, 0;

DROP TABLE IF EXISTS dim_product;
CREATE TABLE dim_product AS
SELECT row_number() OVER (ORDER BY sku) AS product_key, sku, description,
       coalesce(category, 'Onbekend')  AS category, brand, unit_cost, list_price
FROM stg_products;

DROP TABLE IF EXISTS dim_customer;
CREATE TABLE dim_customer AS
SELECT row_number() OVER (ORDER BY c.customer_no) AS customer_key,
       c.customer_no, c.customer_name, c.segment, c.territory, c.postcode, c.city, c.country, c.language, c.is_internal,
       h.rep_code   AS current_rep_code,
       a.account_id AS crm_account_id
FROM stg_customers c
LEFT JOIN stg_customer_rep_history h ON h.customer_no = c.customer_no AND h.valid_to = '9999-12-31'
LEFT JOIN crm_acc a ON a.erp_customer_no = c.customer_no AND a.merged_into IS NULL;

-- Revenue belongs to the rep who owned the customer on the invoice date (ADR-002).
-- Lines without a rep code get the owner from the ERP history at that date; the flag keeps it visible.
DROP TABLE IF EXISTS fact_sales;
CREATE TABLE fact_sales AS
SELECT l.invoice_no,
       l.doc_type,
       CAST(strftime('%Y%m%d', l.invoice_date) AS INTEGER)  AS date_key,
       dc.customer_key,
       dp.product_key,
       coalesce(dr.rep_key, 0)                               AS rep_key,
       CASE WHEN l.rep_code IS NULL THEN 1 ELSE 0 END        AS rep_derived,
       l.qty,
       round(l.net_amount, 2)                                AS net_amount,
       round(l.cost_amount, 2)                               AS cost_amount,
       round(l.net_amount - l.cost_amount, 2)                AS gross_margin
FROM stg_invoice_lines l
JOIN dim_customer dc ON dc.customer_no = l.customer_no
JOIN dim_product  dp ON dp.sku = l.sku
LEFT JOIN stg_customer_rep_history h
       ON l.rep_code IS NULL AND h.customer_no = l.customer_no AND l.invoice_date BETWEEN h.valid_from AND h.valid_to
LEFT JOIN dim_rep dr ON dr.rep_code = coalesce(l.rep_code, h.rep_code);

DROP TABLE IF EXISTS fact_opportunity;
CREATE TABLE fact_opportunity AS
SELECT o.opportunity_id,
       o.account_id,
       dc.customer_key,
       coalesce(dr.rep_key, 0)                                 AS rep_key,
       o.stage,
       CASE o.stage WHEN 'Prospectie' THEN 1 WHEN 'Kwalificatie' THEN 2 WHEN 'Offerte' THEN 3
                    WHEN 'Onderhandeling' THEN 4 WHEN 'Gewonnen' THEN 5 ELSE 6 END AS stage_order,
       CASE o.stage WHEN 'Prospectie' THEN 0.10 WHEN 'Kwalificatie' THEN 0.25 WHEN 'Offerte' THEN 0.50
                    WHEN 'Onderhandeling' THEN 0.75 WHEN 'Gewonnen' THEN 1.0 ELSE 0.0 END AS probability,
       o.amount,
       CAST(strftime('%Y%m%d', o.created_at) AS INTEGER)      AS created_date_key,
       CAST(strftime('%Y%m%d', o.expected_close) AS INTEGER)  AS close_date_key,
       o.last_update,
       CASE WHEN o.stage IN ('Gewonnen', 'Verloren') THEN 0 ELSE 1 END AS is_open,
       CAST(julianday((SELECT as_of_date FROM meta)) - julianday(o.last_update) AS INTEGER) AS days_since_update,
       o.lost_reason
FROM crm_opp o
JOIN crm_acc a ON a.account_id = o.account_id
LEFT JOIN dim_customer dc ON dc.customer_no = a.erp_customer_no
LEFT JOIN dim_rep dr ON dr.rep_code = a.owner_rep;

DROP TABLE IF EXISTS fact_target;
CREATE TABLE fact_target AS
SELECT dr.rep_key,
       printf('%04d-%02d', t.year, t.month)                   AS year_month,
       CAST(printf('%04d%02d01', t.year, t.month) AS INTEGER) AS date_key,
       t.target_amount
FROM stg_targets t JOIN dim_rep dr ON dr.rep_code = t.rep_code;

CREATE INDEX ix_fact_sales_date ON fact_sales(date_key);
CREATE INDEX ix_fact_sales_customer ON fact_sales(customer_key);
CREATE INDEX ix_fact_sales_rep ON fact_sales(rep_key);
