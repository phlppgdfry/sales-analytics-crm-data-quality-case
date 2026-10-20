# Wat deze case bewijst

> Van typische taken van een (junior) data analyst in een kmo — sales, CRM, datawarehouse, Power BI, Excel, IT-support — naar concreet bewijs in deze repository.
> **Toont / claimt niet** scheidt wat de case laat zien van productie-ervaring die niet geclaimd wordt.

| Taak | Bewijs in deze repository | In 30 seconden | Toont / claimt niet |
|---|---|---|---|
| Dashboards bouwen en onderhouden met **Power BI**, afgestemd op het salesteam | Semantisch model als code ([TMDL](powerbi/Vennaert%20Sales.SemanticModel/definition/model.tmdl)): 10 tabellen, 10 relaties (1 inactief), 18 [measures](powerbi/Vennaert%20Sales.SemanticModel/definition/tables/Measures.tmdl), 2 rollen; [rapportontwerp](docs/06-reporting/README.md) met vier pagina's | demo → tabs Overzicht, Verkoop, Pipeline | Toont: modelontwerp, DAX, RLS. Claimt niet: een gepubliceerd rapport; de DAX is niet in Power BI uitgevoerd (wel structureel gevalideerd met Microsofts TMDL-serializer) |
| **SQL**: databank aanspreken en ontwerpen | [sterschema](sql/03_model.sql), [KPI-views](sql/04_views.sql), [regels](sql/02_dq_rules.sql), [reconciliatie](sql/05_reconciliation.sql); [T-SQL-versie](sql/tsql/01_schema.sql) met sleutels, in CI vergeleken op SQL Server 2022 | demo → tab SQL, preset "KPI's dit jaar" | Toont: modelleren, joins, CTE's, window functions, views, twee dialecten. Claimt niet: beheer van een productiewarehouse |
| Gegevens **feilloos** verzamelen en structureren uit het datawarehouse | [pipeline](docs/04-pipeline/README.md) met totaalcontroles; [tests](tests/test_model.py): som staging = som feiten, Q3 = finance tot op de cent | demo → tab Reconciliatie | Toont: controleerbare pipeline, reconciliatie. Claimt niet: koppeling met echte ERP/CRM-systemen |
| **CRM beheren**, datakwaliteit bewaken, workflows opzetten | [13 regels met eigenaar](docs/05-crm-quality/rules.md), [duplicaatscore + review + overlevingsregels](docs/05-crm-quality/duplicates.md), auditlog, [preventie bij invoer](docs/10-improvement/README.md) | demo → tab CRM-kwaliteit → beslis zelf over een paar | Toont: methode, beslisregels, workflow. Claimt niet: configuratie in een specifiek CRM-pakket |
| **Excel** | [reconciliatiewerkboek](excel/reconciliatie-sales-finance-2026Q3.xlsx) met SUMIFS-brug, formule-draaitabel en controlekolom tegen SQL | [07 · Excel](docs/07-excel/README.md) | — |
| **Rapporteren** over de resultaten van een onderzoek | [reconciliatie](docs/07-excel/README.md) en [bronnenanalyse](docs/02-sources/README.md) in businesstaal | README → "Het probleem" | — |
| **Analytische berekeningen**, datamining | gewogen pipeline, win rate, groei vs vorig jaar; duplicaatdetectie met blocking + stringgelijkenis | [duplicaten](docs/05-crm-quality/duplicates.md) | Claimt niet: machine learning |
| **IT-support** bij bedrijfssoftware en hardware | [drie tickets](docs/08-it-support/README.md): refresh mislukt (gateway), leeg rapport door RLS (antwoord in het Frans), onboarding-checklist incl. laptop en MFA; runbook | demo → tab IT-support | Toont: diagnose in stappen, communicatie, preventie. Claimt niet: helpdeskervaring in een bedrijf |
| **Meedenken over verbeterprojecten** | [zeven voorstellen](docs/10-improvement/README.md) met inspanning, baat, eigenaar en prioritering | — | Baten zijn inschattingen |
| Business ↔ data vertalen | [intake → afspraken → KPI-catalogus](docs/01-business-questions/README.md), [ADR's](docs/adr/README.md) | — | Fictieve stakeholders |

## Hoe dit gecontroleerd wordt

Elke push draait in GitHub Actions: data genereren → pipeline → review → pipeline → tests → `build_docs --check` (elk getal in docs en site = model) → TMDL-validatie → laden in SQL Server 2022 en 17 KPI's vergelijken → links.
