# Start hier

> Onafhankelijke portfoliocase — fictief bedrijf Vennaert. Kies het pad dat bij je tijd past.

## 2 minuten

1. [Demo met rondleiding](https://phlppgdfry.github.io/sales-analytics-crm-data-quality-case/demo/?tour) — 9 stappen langs het hele verhaal
2. [README](README.md) — probleem, aanpak, beslissingen

## 5 minuten

3. [Reconciliatie](docs/07-excel/README.md) — waarom het Excel-rapport <!--m:recon_gap|eur0-->€ 397.834<!--/m--> te hoog zat
4. [Sterschema](docs/03-modelling/README.md) — het model en de keuzes
5. [Wat dit bewijst](EVIDENCE.md)

## 15 minuten

6. [Businessvragen en KPI-catalogus](docs/01-business-questions/README.md)
7. [CRM-kwaliteit](docs/05-crm-quality/README.md) → [duplicaten](docs/05-crm-quality/duplicates.md)
8. [Power BI-rapportering](docs/06-reporting/README.md) → [measures](powerbi/Vennaert%20Sales.SemanticModel/definition/tables/Measures.tmdl)
9. [IT-support](docs/08-it-support/README.md)

## Alle details

| Stap | Beste documenten |
|---|---|
| Context | [00 · Context](docs/00-context/README.md) |
| Vragen | [01 · Businessvragen](docs/01-business-questions/README.md) |
| Bronnen | [02 · Bronnen](docs/02-sources/README.md) · [`generator/`](generator/generate_sources.py) |
| Model | [03 · Model](docs/03-modelling/README.md) · [`sql/03_model.sql`](sql/03_model.sql) · [`sql/tsql/`](sql/tsql/01_schema.sql) |
| Pipeline | [04 · Pipeline](docs/04-pipeline/README.md) · [`etl/pipeline.py`](etl/pipeline.py) |
| CRM | [05 · CRM-kwaliteit](docs/05-crm-quality/README.md) · [regels](docs/05-crm-quality/rules.md) · [`sql/02_dq_rules.sql`](sql/02_dq_rules.sql) |
| Rapport | [06 · Rapportering](docs/06-reporting/README.md) · [`powerbi/`](powerbi/Vennaert%20Sales.SemanticModel/definition/model.tmdl) |
| Excel | [07 · Excel](docs/07-excel/README.md) · [werkboek](excel/reconciliatie-sales-finance-2026Q3.xlsx) |
| Support | [08 · IT-support](docs/08-it-support/README.md) |
| Testen | [09 · Testen](docs/09-testing/README.md) · [`tests/`](tests/) |
| Verbeteren | [10 · Verbeteren](docs/10-improvement/README.md) |
| Beslissingen | [ADR's](docs/adr/README.md) |
