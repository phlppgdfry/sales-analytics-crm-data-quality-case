-- 04_views.sql — the reporting layer. One view per question the sales team asks.
-- KPI definitions: docs/01-business-questions/kpi-catalog.md. The same definitions exist as DAX
-- measures in powerbi/ (e.g. [Netto-omzet]); tests/test_kpis.py checks the views against each other.
-- "Commercial" always means: internal staff shop excluded (dim_customer.is_internal = 0).

DROP VIEW IF EXISTS v_sales;
CREATE VIEW v_sales AS
SELECT f.*, d.date, d.year, d.quarter, d.month, d.year_month,
       c.customer_no, c.customer_name, c.segment, c.territory, c.country, c.language,
       r.rep_code, r.rep_name, r.team,
       p.sku, p.category, p.brand
FROM fact_sales f
JOIN dim_date d     ON d.date_key = f.date_key
JOIN dim_customer c ON c.customer_key = f.customer_key
JOIN dim_rep r      ON r.rep_key = f.rep_key
JOIN dim_product p  ON p.product_key = f.product_key
WHERE c.is_internal = 0;

-- KPI-01..04 per month
DROP VIEW IF EXISTS v_sales_monthly;
CREATE VIEW v_sales_monthly AS
SELECT year_month,
       round(sum(net_amount), 2)                                         AS net_revenue,
       round(sum(gross_margin), 2)                                       AS gross_margin,
       round(100.0 * sum(gross_margin) / nullif(sum(net_amount), 0), 1)  AS margin_pct,
       count(DISTINCT CASE WHEN doc_type = 'F' THEN invoice_no END)      AS invoices,
       count(DISTINCT customer_no)                                       AS active_customers
FROM v_sales
GROUP BY year_month;

-- KPI-05 year-to-date vs the same months last year
DROP VIEW IF EXISTS v_kpi_ytd;
CREATE VIEW v_kpi_ytd AS
WITH p AS (
  SELECT CAST(strftime('%Y', as_of_date) AS INTEGER) AS y, CAST(strftime('%m', as_of_date) AS INTEGER) AS m FROM meta
), cur AS (
  SELECT sum(net_amount) AS rev, sum(gross_margin) AS gm, count(DISTINCT customer_no) AS cust,
         count(DISTINCT CASE WHEN doc_type = 'F' THEN invoice_no END) AS inv
  FROM v_sales, p WHERE year = p.y AND month <= p.m
), prev AS (
  SELECT sum(net_amount) AS rev, sum(gross_margin) AS gm
  FROM v_sales, p WHERE year = p.y - 1 AND month <= p.m
), tgt AS (
  SELECT sum(t.target_amount) AS target FROM fact_target t, p
  WHERE CAST(substr(t.year_month, 1, 4) AS INTEGER) = p.y AND CAST(substr(t.year_month, 6, 2) AS INTEGER) <= p.m
)
SELECT round(cur.rev, 2)                               AS net_revenue_ytd,
       round(prev.rev, 2)                              AS net_revenue_ytd_prev,
       round(100.0 * (cur.rev - prev.rev) / prev.rev, 1) AS growth_pct,
       round(cur.gm, 2)                                AS gross_margin_ytd,
       round(100.0 * cur.gm / cur.rev, 1)              AS margin_pct_ytd,
       round(tgt.target, 2)                            AS target_ytd,
       round(100.0 * cur.rev / tgt.target, 1)          AS target_attainment_pct,
       cur.cust                                        AS active_customers_ytd,
       round(cur.rev / cur.inv, 2)                     AS avg_invoice_value_ytd
FROM cur, prev, tgt;

-- Revenue per rep per month next to the target (KPI-06)
DROP VIEW IF EXISTS v_rep_month_vs_target;
CREATE VIEW v_rep_month_vs_target AS
WITH s AS (
  SELECT rep_key, year_month, sum(net_amount) AS net_revenue, sum(gross_margin) AS gross_margin
  FROM v_sales GROUP BY rep_key, year_month
)
SELECT r.rep_code, r.rep_name, r.team, r.is_active, k.year_month,
       round(coalesce(s.net_revenue, 0), 2)  AS net_revenue,
       round(coalesce(s.gross_margin, 0), 2) AS gross_margin,
       t.target_amount,
       round(100.0 * coalesce(s.net_revenue, 0) / nullif(t.target_amount, 0), 1) AS attainment_pct
FROM (SELECT rep_key, year_month FROM s UNION SELECT rep_key, year_month FROM fact_target) k
JOIN dim_rep r ON r.rep_key = k.rep_key
LEFT JOIN s ON s.rep_key = k.rep_key AND s.year_month = k.year_month
LEFT JOIN fact_target t ON t.rep_key = k.rep_key AND t.year_month = k.year_month;

DROP VIEW IF EXISTS v_sales_by_category;
CREATE VIEW v_sales_by_category AS
SELECT year, category, round(sum(net_amount), 2) AS net_revenue, round(sum(gross_margin), 2) AS gross_margin,
       round(100.0 * sum(gross_margin) / nullif(sum(net_amount), 0), 1) AS margin_pct
FROM v_sales GROUP BY year, category;

-- Top customers over the last 12 months (Oct last year .. as_of month)
DROP VIEW IF EXISTS v_top_customers_12m;
CREATE VIEW v_top_customers_12m AS
SELECT customer_no, customer_name, segment, territory,
       round(sum(net_amount), 2) AS net_revenue_12m,
       round(100.0 * sum(gross_margin) / nullif(sum(net_amount), 0), 1) AS margin_pct,
       count(DISTINCT CASE WHEN doc_type = 'F' THEN invoice_no END) AS invoices
FROM v_sales
WHERE date > date((SELECT as_of_date FROM meta), '-12 months')
GROUP BY customer_no, customer_name, segment, territory;

-- Pipeline (KPI-08/09): open amount and weighted amount per stage
DROP VIEW IF EXISTS v_pipeline_by_stage;
CREATE VIEW v_pipeline_by_stage AS
SELECT stage, stage_order, count(*) AS opportunities,
       sum(CASE WHEN amount IS NULL THEN 1 ELSE 0 END) AS without_amount,
       round(sum(coalesce(amount, 0)), 2) AS amount,
       round(sum(coalesce(amount, 0) * probability), 2) AS weighted_amount,
       sum(CASE WHEN days_since_update > 60 THEN 1 ELSE 0 END) AS stale
FROM fact_opportunity
WHERE is_open = 1
GROUP BY stage, stage_order;

-- Win rate (KPI-10) on opportunities closed in the last 12 months
DROP VIEW IF EXISTS v_win_rate_12m;
CREATE VIEW v_win_rate_12m AS
SELECT sum(CASE WHEN stage = 'Gewonnen' THEN 1 ELSE 0 END) AS won,
       sum(CASE WHEN stage = 'Verloren' THEN 1 ELSE 0 END) AS lost,
       round(100.0 * sum(CASE WHEN stage = 'Gewonnen' THEN 1 ELSE 0 END) / count(*), 1) AS win_rate_pct
FROM fact_opportunity f
JOIN dim_date d ON d.date_key = f.close_date_key
WHERE f.is_open = 0 AND d.date > date((SELECT as_of_date FROM meta), '-12 months');

-- Data quality per rule, before and after the corrections (KPI-11 health score lives in v_dq_health)
DROP VIEW IF EXISTS v_dq_rule_summary;
CREATE VIEW v_dq_rule_summary AS
SELECT r.rule_id, r.title, r.severity, r.owner,
       sum(CASE WHEN i.snapshot = 'before' THEN 1 ELSE 0 END) AS issues_before,
       sum(CASE WHEN i.snapshot = 'after'  THEN 1 ELSE 0 END) AS issues_after
FROM dq_rule r LEFT JOIN dq_issue i ON i.rule_id = r.rule_id
GROUP BY r.rule_id, r.title, r.severity, r.owner;
