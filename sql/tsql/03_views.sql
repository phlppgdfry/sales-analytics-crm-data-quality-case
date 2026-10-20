-- 03_views.sql — the reporting views of sql/04_views.sql, translated to T-SQL.
-- Differences with the SQLite version are dialect only: DATEADD instead of date(x, '-12 months'),
-- CAST(... AS DECIMAL) before division, TOP instead of LIMIT. The definitions are the same.
USE VennaertDWH;
GO
CREATE OR ALTER VIEW dwh.v_sales AS
SELECT f.*, d.[date], d.[year], d.[quarter], d.[month], d.year_month,
       c.customer_no, c.customer_name, c.segment, c.territory, c.country, c.[language],
       r.rep_code, r.rep_name, r.team,
       p.sku, p.category, p.brand
FROM dwh.fact_sales f
JOIN dwh.dim_date d     ON d.date_key = f.date_key
JOIN dwh.dim_customer c ON c.customer_key = f.customer_key
JOIN dwh.dim_rep r      ON r.rep_key = f.rep_key
JOIN dwh.dim_product p  ON p.product_key = f.product_key
WHERE c.is_internal = 0;
GO
CREATE OR ALTER VIEW dwh.v_sales_monthly AS
SELECT year_month,
       SUM(net_amount)                                                         AS net_revenue,
       SUM(gross_margin)                                                       AS gross_margin,
       CAST(ROUND(100.0 * SUM(gross_margin) / NULLIF(SUM(net_amount), 0), 1) AS DECIMAL(5,1)) AS margin_pct,
       COUNT(DISTINCT CASE WHEN doc_type = 'F' THEN invoice_no END)            AS invoices,
       COUNT(DISTINCT customer_no)                                             AS active_customers
FROM dwh.v_sales
GROUP BY year_month;
GO
CREATE OR ALTER VIEW dwh.v_kpi_ytd AS
WITH p AS (SELECT YEAR(as_of_date) AS y, MONTH(as_of_date) AS m FROM dwh.meta),
cur AS (
  SELECT SUM(s.net_amount) AS rev, SUM(s.gross_margin) AS gm, COUNT(DISTINCT s.customer_no) AS cust,
         COUNT(DISTINCT CASE WHEN s.doc_type = 'F' THEN s.invoice_no END) AS inv
  FROM dwh.v_sales s CROSS JOIN p WHERE s.[year] = p.y AND s.[month] <= p.m
),
prev AS (SELECT SUM(s.net_amount) AS rev FROM dwh.v_sales s CROSS JOIN p WHERE s.[year] = p.y - 1 AND s.[month] <= p.m),
tgt AS (
  SELECT SUM(t.target_amount) AS target FROM dwh.fact_target t CROSS JOIN p
  WHERE CAST(LEFT(t.year_month, 4) AS INT) = p.y AND CAST(RIGHT(t.year_month, 2) AS INT) <= p.m
)
SELECT cur.rev                                                   AS net_revenue_ytd,
       prev.rev                                                  AS net_revenue_ytd_prev,
       CAST(ROUND(100.0 * (cur.rev - prev.rev) / prev.rev, 1) AS DECIMAL(6,1)) AS growth_pct,
       cur.gm                                                    AS gross_margin_ytd,
       CAST(ROUND(100.0 * cur.gm / cur.rev, 1) AS DECIMAL(5,1))  AS margin_pct_ytd,
       tgt.target                                                AS target_ytd,
       CAST(ROUND(100.0 * cur.rev / tgt.target, 1) AS DECIMAL(6,1)) AS target_attainment_pct,
       cur.cust                                                  AS active_customers_ytd,
       CAST(ROUND(cur.rev / cur.inv, 2) AS DECIMAL(14,2))        AS avg_invoice_value_ytd
FROM cur CROSS JOIN prev CROSS JOIN tgt;
GO
CREATE OR ALTER VIEW dwh.v_pipeline_by_stage AS
SELECT stage, stage_order, COUNT(*) AS opportunities,
       SUM(CASE WHEN amount IS NULL THEN 1 ELSE 0 END)   AS without_amount,
       SUM(COALESCE(amount, 0))                          AS amount,
       SUM(COALESCE(amount, 0) * probability)            AS weighted_amount,
       SUM(CASE WHEN days_since_update > 60 THEN 1 ELSE 0 END) AS stale
FROM dwh.fact_opportunity
WHERE is_open = 1
GROUP BY stage, stage_order;
GO
CREATE OR ALTER VIEW dwh.v_win_rate_12m AS
SELECT SUM(CASE WHEN f.stage = 'Gewonnen' THEN 1 ELSE 0 END) AS won,
       SUM(CASE WHEN f.stage = 'Verloren' THEN 1 ELSE 0 END) AS lost,
       CAST(ROUND(100.0 * SUM(CASE WHEN f.stage = 'Gewonnen' THEN 1 ELSE 0 END) / COUNT(*), 1) AS DECIMAL(5,1)) AS win_rate_pct
FROM dwh.fact_opportunity f
JOIN dwh.dim_date d ON d.date_key = f.close_date_key
WHERE f.is_open = 0 AND d.[date] > DATEADD(MONTH, -12, (SELECT as_of_date FROM dwh.meta));
GO
CREATE OR ALTER VIEW dwh.v_dq_rule_summary AS
SELECT r.rule_id, r.title, r.severity, r.owner,
       SUM(CASE WHEN i.snapshot = 'before' THEN 1 ELSE 0 END) AS issues_before,
       SUM(CASE WHEN i.snapshot = 'after'  THEN 1 ELSE 0 END) AS issues_after
FROM dwh.dq_rule r LEFT JOIN dwh.dq_issue i ON i.rule_id = r.rule_id
GROUP BY r.rule_id, r.title, r.severity, r.owner;
GO
