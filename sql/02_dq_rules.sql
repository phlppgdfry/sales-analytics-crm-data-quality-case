-- 02_dq_rules.sql — data-quality rules on the CRM (and the ERP fields the sales report depends on).
-- Runs twice: once on the raw CRM ("before") and once after the approved corrections ("after").
-- The working tables are crm_acc and crm_opp; {snapshot} is filled in by etl/pipeline.py.
-- Every rule has an ID that is used in docs/05-crm-quality/rules.md, on the dashboard and in the tests.

DROP VIEW IF EXISTS v_vat_check;
CREATE VIEW v_vat_check AS
SELECT account_id, vat_norm,
       CASE WHEN vat_norm IS NULL THEN NULL
            WHEN vat_norm LIKE 'BE%' AND length(vat_norm) = 12 AND substr(vat_norm, 3) NOT GLOB '*[^0-9]*'
                 THEN CASE WHEN 97 - (CAST(substr(vat_norm, 3, 8) AS INTEGER) % 97) = CAST(substr(vat_norm, 11, 2) AS INTEGER) THEN 1 ELSE 0 END
            WHEN vat_norm LIKE 'FR%' AND length(vat_norm) = 13 AND substr(vat_norm, 3) NOT GLOB '*[^0-9]*'
                 THEN CASE WHEN CAST(substr(vat_norm, 3, 2) AS INTEGER) = (12 + 3 * (CAST(substr(vat_norm, 5, 9) AS INTEGER) % 97)) % 97 THEN 1 ELSE 0 END
            ELSE 0 END AS vat_valid
FROM crm_acc;

-- Which CRM accounts are (or should be) customers?
--   customer           linked to an ERP customer number
--   customer-unlinked  not linked, but its VAT matches an ERP customer that no CRM account is linked to
--   other              prospects, and duplicates of an account that is already linked (those are CRM-01)
DROP VIEW IF EXISTS v_account_scope;
CREATE VIEW v_account_scope AS
SELECT a.account_id,
       CASE WHEN a.erp_customer_no IS NOT NULL THEN 'customer'
            WHEN EXISTS (SELECT 1 FROM stg_customers c
                         WHERE c.vat_norm = a.vat_norm AND c.is_internal = 0
                           AND NOT EXISTS (SELECT 1 FROM crm_acc x
                                           WHERE x.erp_customer_no = c.customer_no AND x.merged_into IS NULL)) THEN 'customer-unlinked'
            ELSE 'other' END AS scope
FROM crm_acc a
WHERE a.merged_into IS NULL;

DELETE FROM dq_issue WHERE snapshot = '{snapshot}';

-- @rules
-- CRM-01  Possible duplicate account (pairs scored by etl/duplicates.py; only scores >= 40 are kept)
INSERT INTO dq_issue (snapshot, rule_id, severity, entity, entity_id, detail)
SELECT '{snapshot}', 'CRM-01', 'blocking', 'account', p.account_b,
       'mogelijk duplicaat van ' || p.account_a || ' (score ' || p.score || ')'
FROM dq_duplicate_pair p
WHERE p.snapshot = '{snapshot}';

-- CRM-02  VAT number present but check digits fail (typo)
INSERT INTO dq_issue (snapshot, rule_id, severity, entity, entity_id, detail)
SELECT '{snapshot}', 'CRM-02', 'blocking', 'account', v.account_id, 'btw-nummer ongeldig: ' || v.vat_norm
FROM v_vat_check v JOIN crm_acc a USING (account_id)
WHERE v.vat_valid = 0 AND a.merged_into IS NULL;

-- CRM-03  Customer account without VAT number (prospects may have none)
INSERT INTO dq_issue (snapshot, rule_id, severity, entity, entity_id, detail)
SELECT '{snapshot}', 'CRM-03', 'warning', 'account', a.account_id, 'klant zonder btw-nummer'
FROM crm_acc a JOIN v_account_scope s USING (account_id)
WHERE a.vat_norm IS NULL AND s.scope = 'customer';

-- CRM-04  Account is an ERP customer (VAT matches) but the link to the ERP customer number is missing
INSERT INTO dq_issue (snapshot, rule_id, severity, entity, entity_id, detail)
SELECT '{snapshot}', 'CRM-04', 'blocking', 'account', s.account_id, 'geen koppeling met ERP-klant (btw komt overeen)'
FROM v_account_scope s
WHERE s.scope = 'customer-unlinked';

-- CRM-05  Account owner is no longer employed -> nobody follows up, and the sales report splits revenue
INSERT INTO dq_issue (snapshot, rule_id, severity, entity, entity_id, detail)
SELECT '{snapshot}', 'CRM-05', 'blocking', 'account', a.account_id, 'eigenaar ' || a.owner_rep || ' is uit dienst sinds ' || r.end_date
FROM crm_acc a JOIN stg_sales_reps r ON r.rep_code = a.owner_rep
WHERE r.end_date IS NOT NULL AND r.end_date < (SELECT as_of_date FROM meta) AND a.merged_into IS NULL;

-- CRM-06  No e-mail and no phone: the account cannot be contacted
INSERT INTO dq_issue (snapshot, rule_id, severity, entity, entity_id, detail)
SELECT '{snapshot}', 'CRM-06', 'warning', 'account', a.account_id, 'geen e-mail en geen telefoon'
FROM crm_acc a
WHERE a.email IS NULL AND a.phone IS NULL AND a.merged_into IS NULL;

-- CRM-07  Postcode does not match the country format (BE = 4 digits, FR = 5 digits)
INSERT INTO dq_issue (snapshot, rule_id, severity, entity, entity_id, detail)
SELECT '{snapshot}', 'CRM-07', 'warning', 'account', a.account_id, 'postcode "' || a.postcode || '" past niet bij ' || a.country
FROM crm_acc a
WHERE a.merged_into IS NULL
  AND NOT ((a.country = 'BE' AND length(a.postcode) = 4 AND a.postcode NOT GLOB '*[^0-9]*')
        OR (a.country = 'FR' AND length(a.postcode) = 5 AND a.postcode NOT GLOB '*[^0-9]*'));

-- OPP-01  Open opportunity without any update for more than 60 days
INSERT INTO dq_issue (snapshot, rule_id, severity, entity, entity_id, detail)
SELECT '{snapshot}', 'OPP-01', 'warning', 'opportunity', o.opportunity_id,
       CAST(julianday((SELECT as_of_date FROM meta)) - julianday(o.last_update) AS INTEGER) || ' dagen geen update'
FROM crm_opp o
WHERE o.stage NOT IN ('Gewonnen', 'Verloren')
  AND julianday((SELECT as_of_date FROM meta)) - julianday(o.last_update) > 60;

-- OPP-02  Open opportunity whose expected close date is in the past
INSERT INTO dq_issue (snapshot, rule_id, severity, entity, entity_id, detail)
SELECT '{snapshot}', 'OPP-02', 'warning', 'opportunity', o.opportunity_id, 'verwachte afsluitdatum ' || o.expected_close || ' is voorbij'
FROM crm_opp o
WHERE o.stage NOT IN ('Gewonnen', 'Verloren') AND o.expected_close < (SELECT as_of_date FROM meta);

-- OPP-03  Opportunity in quote or negotiation without an amount -> invisible in the weighted pipeline
INSERT INTO dq_issue (snapshot, rule_id, severity, entity, entity_id, detail)
SELECT '{snapshot}', 'OPP-03', 'blocking', 'opportunity', o.opportunity_id, 'fase ' || o.stage || ' zonder bedrag'
FROM crm_opp o
WHERE o.stage IN ('Offerte', 'Onderhandeling') AND o.amount IS NULL;

-- ERP-01  Invoice line without sales rep (fixed in the model by taking the owner at invoice date)
INSERT INTO dq_issue (snapshot, rule_id, severity, entity, entity_id, detail)
SELECT '{snapshot}', 'ERP-01', 'warning', 'invoice_line', l.invoice_no || '/' || l.sku, 'factuurlijn zonder verkoper'
FROM stg_invoice_lines l
WHERE l.rep_code IS NULL AND '{snapshot}' = 'before';

-- ERP-02  Product without category
INSERT INTO dq_issue (snapshot, rule_id, severity, entity, entity_id, detail)
SELECT '{snapshot}', 'ERP-02', 'warning', 'product', p.sku, 'artikel zonder categorie'
FROM stg_products p
WHERE p.category IS NULL;

-- ERP-03  Product with cost price 0 -> 100 % margin on every sale
INSERT INTO dq_issue (snapshot, rule_id, severity, entity, entity_id, detail)
SELECT '{snapshot}', 'ERP-03', 'blocking', 'product', p.sku, 'kostprijs = 0'
FROM stg_products p
WHERE p.unit_cost = 0;
