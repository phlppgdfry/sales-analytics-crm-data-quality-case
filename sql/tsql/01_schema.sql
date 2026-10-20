-- 01_schema.sql — the warehouse model on SQL Server (schema dwh), the source the Power BI model reads.
-- Same tables as sql/03_model.sql (SQLite, used for the browser demo), now with real types and keys.
-- CI loads the SQLite output into SQL Server 2022 and checks that every KPI comes out identical.
IF DB_ID('VennaertDWH') IS NULL CREATE DATABASE VennaertDWH;
GO
USE VennaertDWH;
GO
IF SCHEMA_ID('dwh') IS NULL EXEC('CREATE SCHEMA dwh');
GO
DROP TABLE IF EXISTS dwh.fact_sales, dwh.fact_opportunity, dwh.fact_target, dwh.dq_issue, dwh.dq_rule, dwh.dq_health, dwh.meta;
DROP TABLE IF EXISTS dwh.dim_customer, dwh.dim_product, dwh.dim_rep, dwh.dim_date;
GO
CREATE TABLE dwh.meta (as_of_date DATE NOT NULL);

CREATE TABLE dwh.dim_date (
  date_key       INT          NOT NULL PRIMARY KEY,
  [date]         DATE         NOT NULL,
  [year]         SMALLINT     NOT NULL,
  [quarter]      TINYINT      NOT NULL,
  [month]        TINYINT      NOT NULL,
  year_month     CHAR(7)      NOT NULL,
  month_short_nl NVARCHAR(3)  NOT NULL,
  is_weekday     BIT          NOT NULL
);

CREATE TABLE dwh.dim_rep (
  rep_key    INT          NOT NULL PRIMARY KEY,
  rep_code   VARCHAR(4)   NOT NULL UNIQUE,
  rep_name   NVARCHAR(60) NOT NULL,
  region     NVARCHAR(40) NOT NULL,
  team       NVARCHAR(20) NOT NULL,
  email      VARCHAR(120) NULL,
  start_date DATE         NULL,
  end_date   DATE         NULL,
  is_active  BIT          NOT NULL
);

CREATE TABLE dwh.dim_product (
  product_key INT           NOT NULL PRIMARY KEY,
  sku         VARCHAR(12)   NOT NULL UNIQUE,
  description NVARCHAR(80)  NOT NULL,
  category    NVARCHAR(40)  NOT NULL,
  brand       NVARCHAR(40)  NOT NULL,
  unit_cost   DECIMAL(12,2) NOT NULL,
  list_price  DECIMAL(12,2) NOT NULL
);

CREATE TABLE dwh.dim_customer (
  customer_key     INT           NOT NULL PRIMARY KEY,
  customer_no      VARCHAR(8)    NOT NULL UNIQUE,
  customer_name    NVARCHAR(120) NOT NULL,
  segment          NVARCHAR(40)  NOT NULL,
  territory        NVARCHAR(40)  NOT NULL,
  postcode         VARCHAR(10)   NOT NULL,
  city             NVARCHAR(60)  NOT NULL,
  country          CHAR(2)       NOT NULL,
  [language]       CHAR(2)       NOT NULL,
  is_internal      BIT           NOT NULL,
  current_rep_code VARCHAR(4)    NULL,
  crm_account_id   VARCHAR(12)   NULL
);

CREATE TABLE dwh.fact_sales (
  invoice_no   VARCHAR(10)   NOT NULL,
  doc_type     CHAR(1)       NOT NULL CHECK (doc_type IN ('F', 'C')),
  date_key     INT           NOT NULL REFERENCES dwh.dim_date (date_key),
  customer_key INT           NOT NULL REFERENCES dwh.dim_customer (customer_key),
  product_key  INT           NOT NULL REFERENCES dwh.dim_product (product_key),
  rep_key      INT           NOT NULL REFERENCES dwh.dim_rep (rep_key),
  rep_derived  BIT           NOT NULL,
  qty          INT           NOT NULL,
  net_amount   DECIMAL(14,2) NOT NULL,
  cost_amount  DECIMAL(14,2) NOT NULL,
  gross_margin DECIMAL(14,2) NOT NULL,
  CONSTRAINT pk_fact_sales PRIMARY KEY (invoice_no, product_key)
);

CREATE TABLE dwh.fact_opportunity (
  opportunity_id    VARCHAR(10)   NOT NULL PRIMARY KEY,
  account_id        VARCHAR(12)   NOT NULL,
  customer_key      INT           NULL REFERENCES dwh.dim_customer (customer_key),
  rep_key           INT           NOT NULL REFERENCES dwh.dim_rep (rep_key),
  stage             NVARCHAR(20)  NOT NULL,
  stage_order       TINYINT       NOT NULL,
  probability       DECIMAL(4,2)  NOT NULL,
  amount            DECIMAL(14,2) NULL,
  created_date_key  INT           NOT NULL REFERENCES dwh.dim_date (date_key),
  close_date_key    INT           NOT NULL,
  last_update       DATE          NOT NULL,
  is_open           BIT           NOT NULL,
  days_since_update INT           NOT NULL,
  lost_reason       NVARCHAR(40)  NULL
);

CREATE TABLE dwh.fact_target (
  rep_key       INT           NOT NULL REFERENCES dwh.dim_rep (rep_key),
  year_month    CHAR(7)       NOT NULL,
  date_key      INT           NOT NULL REFERENCES dwh.dim_date (date_key),
  target_amount DECIMAL(14,2) NOT NULL,
  CONSTRAINT pk_fact_target PRIMARY KEY (rep_key, year_month)
);

CREATE TABLE dwh.dq_rule (rule_id VARCHAR(6) NOT NULL PRIMARY KEY, title NVARCHAR(80) NOT NULL, severity VARCHAR(10) NOT NULL,
                          owner NVARCHAR(60) NOT NULL, fix NVARCHAR(200) NOT NULL);
CREATE TABLE dwh.dq_issue (snapshot VARCHAR(6) NOT NULL, rule_id VARCHAR(6) NOT NULL REFERENCES dwh.dq_rule (rule_id), severity VARCHAR(10) NOT NULL,
                           entity VARCHAR(20) NOT NULL, entity_id VARCHAR(40) NOT NULL, detail NVARCHAR(200) NOT NULL);
CREATE TABLE dwh.dq_health (snapshot VARCHAR(6) NOT NULL PRIMARY KEY, accounts_in_scope INT NOT NULL, accounts_clean INT NOT NULL, health_pct DECIMAL(5,1) NOT NULL);
GO
