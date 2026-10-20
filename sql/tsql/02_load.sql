-- 02_load.sql — bulk load the CSV export of the SQLite warehouse (scripts/export_for_sqlserver.py).
-- The files are UTF-16 ('widechar'): SQL Server on Linux does not support CODEPAGE = '65001', and names contain é, ë, –.
-- In production the same tables would be filled by the nightly ETL from the ERP and CRM; the load
-- mechanism is not the point here, the identical numbers are.
USE VennaertDWH;
GO
BULK INSERT dwh.meta             FROM '/data/meta.csv'             WITH (FORMAT = 'CSV', FIRSTROW = 2, DATAFILETYPE = 'widechar');
BULK INSERT dwh.dim_date         FROM '/data/dim_date.csv'         WITH (FORMAT = 'CSV', FIRSTROW = 2, DATAFILETYPE = 'widechar');
BULK INSERT dwh.dim_rep          FROM '/data/dim_rep.csv'          WITH (FORMAT = 'CSV', FIRSTROW = 2, DATAFILETYPE = 'widechar');
BULK INSERT dwh.dim_product      FROM '/data/dim_product.csv'      WITH (FORMAT = 'CSV', FIRSTROW = 2, DATAFILETYPE = 'widechar');
BULK INSERT dwh.dim_customer     FROM '/data/dim_customer.csv'     WITH (FORMAT = 'CSV', FIRSTROW = 2, DATAFILETYPE = 'widechar');
BULK INSERT dwh.fact_sales       FROM '/data/fact_sales.csv'       WITH (FORMAT = 'CSV', FIRSTROW = 2, DATAFILETYPE = 'widechar', TABLOCK);
BULK INSERT dwh.fact_opportunity FROM '/data/fact_opportunity.csv' WITH (FORMAT = 'CSV', FIRSTROW = 2, DATAFILETYPE = 'widechar');
BULK INSERT dwh.fact_target      FROM '/data/fact_target.csv'      WITH (FORMAT = 'CSV', FIRSTROW = 2, DATAFILETYPE = 'widechar');
BULK INSERT dwh.dq_rule          FROM '/data/dq_rule.csv'          WITH (FORMAT = 'CSV', FIRSTROW = 2, DATAFILETYPE = 'widechar');
BULK INSERT dwh.dq_issue         FROM '/data/dq_issue.csv'         WITH (FORMAT = 'CSV', FIRSTROW = 2, DATAFILETYPE = 'widechar');
BULK INSERT dwh.dq_health        FROM '/data/dq_health.csv'        WITH (FORMAT = 'CSV', FIRSTROW = 2, DATAFILETYPE = 'widechar');
GO
