# Sales & CRM Data Quality — één salesrapport dat finance en sales allebei vertrouwen

**SQL-datawarehouse + Power BI-model + CRM-datakwaliteit + Excel-reconciliatie + IT-support**, voor een fictieve Belgische B2B-groothandel.

> Een Excel-rapport dat <!--m:recon_gap_pct|pct-->6,7 %<!--/m--> naast finance zat en een CRM vol dubbele klanten → de oorzaken op de cent verklaard, één definitie per KPI, en een CRM-gezondheid van <!--m:dq_health_before|pct-->75,0 %<!--/m--> naar <!--m:dq_health_after|pct-->98,0 %<!--/m--> zonder één record blind te verwijderen.

> *Independent portfolio case study based on a fictional organisation (Vennaert). It contains no confidential information from any real employer or the hiring company. Alle cijfers zijn illustratieve aannames — geen echte bedrijfsdata.*

**[Live site](https://phlppgdfry.github.io/sales-analytics-crm-data-quality-case/)** · **[Demo met rondleiding (2 min)](https://phlppgdfry.github.io/sales-analytics-crm-data-quality-case/demo/?tour)** · **[Start hier](START-HERE.md)** · **[Wat dit bewijst](EVIDENCE.md)** · **[Case study](CASE_STUDY.md)**

## Het traject

```text
01 Businessvragen & KPI-catalogus     wat wil sales weten, en wat betekent "omzet"?
   ↓
02 Bronnen profileren                  ERP, CRM, targets, de oude Excel-export
   ↓
03 Sterschema                          feiten en dimensies, korrel per tabel
   ↓
04 Pipeline                            staging → regels → correcties → model, elke run identiek
   ↓
05 CRM-kwaliteit                       13 regels, duplicaatscore, menselijke review, auditlog
   ↓
06 Power BI                            semantisch model als code (TMDL), 18 measures, RLS per verkoper
   ↓
07 Excel-reconciliatie                 de brug van rapport naar finance, met formules
   ↓
08 IT-support                          drie tickets: refresh, rijbeveiliging (FR), onboarding
   ↓
09 Testen                              data-, regel-, cijfer-, platform- en documenttests + UAT
   ↓
10 Verbeteren                          zeven voorstellen, geprioriteerd op "stopt het nieuwe fouten?"
```

## Het probleem

De sales manager van Vennaert vraagt drie dingen: waarom het wekelijkse Excel-rapport voor Q3 <!--m:recon_gap|eur0-->€ 397.834<!--/m--> meer omzet toont dan finance; hoe ze per verkoper kan zien waar die staat tegenover target zonder elke maandag te knippen en plakken; en wat er mis is met het CRM, waar klanten dubbel staan en <!--m:rule_crm05_before|int-->151<!--/m--> accounts nog op naam staan van een verkoper die in maart vertrok.

## Wat ik deed

- **Afspraken eerst:** één omzetdefinitie (die van finance), omzet op de verkoper van het moment, niets samenvoegen zonder beslissing — [businessvragen](docs/01-business-questions/README.md), [ADR's](docs/adr/README.md).
- **Bronnen geprofileerd** en elk probleem een regel met eigenaar gegeven — [bronnen](docs/02-sources/README.md), [regels](docs/05-crm-quality/rules.md).
- **Een sterschema gebouwd in SQL** met KPI-views, en dezelfde views in T-SQL die in CI op SQL Server 2022 dezelfde cijfers moeten geven — [model](docs/03-modelling/README.md), [`sql/`](sql/).
- **Duplicaten gevonden en laten beoordelen:** <!--m:dup_pairs_before|int-->165<!--/m--> paren gescoord, <!--m:review_samenvoegen|int-->145<!--/m--> samengevoegd, <!--m:review_geen_duplicaat|int-->15<!--/m--> bewust niet (multi-site klanten) — [duplicaten](docs/05-crm-quality/duplicates.md).
- **Een Power BI-model als code** met measures, een inactieve relatie voor de win rate en rijbeveiliging per verkoper — [rapportering](docs/06-reporting/README.md), [`powerbi/`](powerbi/Vennaert%20Sales.SemanticModel/definition/model.tmdl).
- **Het verschil met finance verklaard tot op de cent**, in SQL en in een Excel-werkboek dat zichzelf controleert — [reconciliatie](docs/07-excel/README.md).
- **Drie supporttickets** uitgewerkt met diagnose, communicatie en preventie — [IT-support](docs/08-it-support/README.md).

## Wat dit toont

| Taak van een data analyst | Bewijs |
|---|---|
| Dashboards met Power BI en SQL voor sales | [rapportontwerp](docs/06-reporting/README.md) · [measures](powerbi/Vennaert%20Sales.SemanticModel/definition/tables/Measures.tmdl) · [views](sql/04_views.sql) · demo-tabs Overzicht/Verkoop/Pipeline |
| Data uit het datawarehouse structureren | [sterschema](docs/03-modelling/README.md) · [pipeline](docs/04-pipeline/README.md) · [T-SQL](sql/tsql/01_schema.sql) |
| CRM beheren, datakwaliteit, workflows | [CRM-kwaliteit](docs/05-crm-quality/README.md) · demo-tab CRM-kwaliteit |
| Excel | [reconciliatiewerkboek](excel/reconciliatie-sales-finance-2026Q3.xlsx) |
| IT-support | [tickets + runbook](docs/08-it-support/README.md) |
| Verbeterprojecten | [verbeterplan](docs/10-improvement/README.md) |

Volledig, met "toont / claimt niet": [EVIDENCE.md](EVIDENCE.md).

## Belangrijkste beslissingen

1. **Omzet = de finance-definitie** — één cijfer in elke vergadering; finance is eigenaar van de definitie ([ADR-004](docs/adr/ADR-004-omzetdefinitie-finance.md)).
2. **Omzet hoort bij de verkoper op de factuurdatum** — de opvolger erft geen omzet die hij niet maakte ([ADR-002](docs/adr/ADR-002-omzet-op-verkoper-van-het-moment.md)).
3. **Nooit automatisch samenvoegen** — een zorggroep met drie campussen lijkt op een duplicaat maar is het niet ([ADR-003](docs/adr/ADR-003-samenvoegen-alleen-na-menselijke-beslissing.md)).

## Zelf draaien en controleren

| Wat | Hoe | Wat je moet zien |
|---|---|---|
| Demo openen | [demo/?tour](https://phlppgdfry.github.io/sales-analytics-crm-data-quality-case/demo/?tour) | rondleiding van 9 stappen |
| Alles opnieuw bouwen | `./scripts/build_all.sh` (Python 3.10+, alleen standaardbibliotheek + `openpyxl` voor Excel) | log per stap, eindigt met `unexplained € 0.00` |
| Tests | `pip install pytest openpyxl && python3 -m pytest -q` | alle tests groen |
| Docs = model | `python3 scripts/build_docs.py --check` | `0 file(s) stale` |
| Power BI-model valideren | `dotnet run --project tools/TmdlValidate -- "powerbi/Vennaert Sales.SemanticModel/definition"` (.NET 10) | `TMDL OK: 10 tables … 18 measures … 2 roles` |
| SQL Server-vergelijking | zie job `sqlserver` in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | 17 × `OK` |
| Site lokaal | `python3 -m http.server -d site 8000` → http://localhost:8000 | landingspagina + demo |
| Links | `python3 scripts/check-links.py` | `OK` |

## Repository

| Map | Inhoud |
|---|---|
| [`docs/`](docs/00-context/README.md) | de case per stap (00–10) + [ADR's](docs/adr/README.md) |
| [`generator/`](generator/generate_sources.py) | maakt de fictieve bronnen (vaste seed) en simuleert de review |
| [`etl/`](etl/pipeline.py) | pipeline en duplicaatdetectie (Python, standaardbibliotheek) |
| [`sql/`](sql/) | staging, regels, model, views, reconciliatie (SQLite) + [`sql/tsql/`](sql/tsql/) (SQL Server) |
| [`powerbi/`](powerbi/Vennaert%20Sales.SemanticModel/definition/model.tmdl) | semantisch model in TMDL |
| [`excel/`](excel/build_workbook.py) | reconciliatiewerkboek + bouwscript |
| [`data/`](data/metrics.json) | bronextracten, referentietabellen (regels, KPI's), reviewbeslissingen, `metrics.json` |
| [`tests/`](tests/) | pytest-suite |
| [`site/`](site/index.html) | GitHub Pages: landingspagina + demo |
| [`tools/TmdlValidate`](tools/TmdlValidate/Program.cs) | leest het model met Microsofts TMDL-serializer |

## Bronnen, data en licenties

| Bron / afhankelijkheid | Gebruik | Licentie |
|---|---|---|
| Alle data | zelf gegenereerd, fictief | CC BY 4.0 |
| [Microsoft Learn — star schema guidance](https://learn.microsoft.com/power-bi/guidance/star-schema) | modelkeuze | — |
| [sql.js](https://github.com/sql-js/sql.js) 1.10.3 via cdnjs | SQLite in de browser | MIT |
| [openpyxl](https://openpyxl.readthedocs.io/) | Excel-werkboek bouwen | MIT |
| Microsoft.AnalysisServices.NetCore.retail.amd64 (NuGet) | TMDL-validatie in CI | Microsoft-licentie (NuGet) |
| SQL Server 2022 container image | vergelijking in CI | Microsoft EULA (Developer) |

Deze repository: code (scripts, SQL, site-JS/CSS, workflows) onder MIT; documentatie, diagrammen en data onder CC BY 4.0 — zie [LICENSE](LICENSE).

## Beperkingen en aannames

- **Gesimuleerd:** het bedrijf, alle data, de reviewbeslissingen over duplicaten, de UAT en de tickets.
- **Niet uitgevoerd:** de DAX-measures in een Power BI-engine (geen Power BI Desktop in CI); het model is wel structureel gevalideerd en de SQL-tegenhanger van elke KPI is getest. Geen gepubliceerd rapport, geen echte gateway of planning.
- **Niet getoond:** configuratie in een echt CRM, prestaties op grote volumes, productiebeheer van een datawarehouse.
- De resultaten ("van 75 % naar 98 %", "€ 0,00 onverklaard") gelden voor deze gegenereerde data — geen resultaat bij een werkgever.
