# 04 · Pipeline — van extract tot rapport, elke run hetzelfde

> Wat is dit: hoe de data van de bronnen in het model komt, en hoe je dat zelf draait. Voor wie: wie de pipeline onderhoudt of debugt. Waarom: een rapport is zo betrouwbaar als de stap die het minst gecontroleerd wordt.
> Vorige → [03 · Model](../03-modelling/README.md) · Volgende → [05 · CRM-kwaliteit](../05-crm-quality/README.md)

## Stappen

```text
data/raw/*.csv
   │ 1. load       alles als tekst in src_* — exact wat de bron leverde, zodat je altijd kan terugkijken
   ▼
src_*  ──2. stage──▶  stg_*         types, teken van creditnota's, btw-notatie (sql/01_staging.sql)
   │
   ├── 3. check      13 regels + duplicaatscore → dq_issue, dq_duplicate_pair (snapshot "before")
   ├── 4. correct    beslissingen uit de review + 2 regelgebaseerde fixes → crm_change_log (niets verwijderd)
   ├── 5. re-check   dezelfde regels → snapshot "after"
   ▼
6. model   dim_* + fact_* (sql/03_model.sql)
7. report  KPI-views + reconciliatie (sql/04_views.sql, sql/05_reconciliation.sql)
8. publish data/metrics.json · site/data/*.json · site/data/warehouse.sqlite
```

Code: [`etl/pipeline.py`](../../etl/pipeline.py) (orkestratie), [`etl/duplicates.py`](../../etl/duplicates.py) (namen normaliseren en paren scoren), [`sql/`](../../sql/) (alle transformaties). Alleen de standaardbibliotheek van Python; geen pandas nodig voor ± 76.000 rijen.

## Zelf draaien

```bash
python3 generator/generate_sources.py   # bronnen (vaste seed)
python3 etl/pipeline.py                 # ± 10 seconden
python3 -m pytest -q                    # tests
```

Een run logt per stap wat er gebeurde. Met de huidige data:

| Stap | Resultaat |
|---|---|
| check (vóór) | <!--m:dq_issues_before|int-->2.346<!--/m--> meldingen · <!--m:dup_pairs_before|int-->165<!--/m--> duplicaatparen · CRM-gezondheid <!--m:dq_health_before|pct-->75,0 %<!--/m--> |
| correct | <!--m:changes_merge|int-->136<!--/m--> records samengevoegd · <!--m:changes_link|int-->58<!--/m--> ERP-koppelingen · <!--m:changes_reassign|int-->151<!--/m--> eigenaars overgezet |
| check (na) | <!--m:dq_issues_after|int-->522<!--/m--> meldingen · <!--m:dup_pairs_after|int-->5<!--/m--> paren nog open · CRM-gezondheid <!--m:dq_health_after|pct-->98,0 %<!--/m--> |
| publish | netto-omzet jan–sep <!--m:net_revenue_ytd|eur2-->€ 18.702.899,03<!--/m--> · onverklaard verschil Excel ↔ finance <!--m:recon_unexplained|eur2-->€ 0,00<!--/m--> |

## Ontwerpregels

| Regel | Waarom |
|---|---|
| **Staging herstelt vorm, nooit betekenis.** Een btw-nummer krijgt één notatie; of het juist is, beslist een regel. | Zo blijft elke inhoudelijke correctie zichtbaar in `crm_change_log`. |
| **Idempotent:** de pipeline bouwt elke keer alles opnieuw vanaf de bron. | Geen "het werkte gisteren"-toestanden; dezelfde input geeft dezelfde output, ook in CI. |
| **Niets wordt verwijderd.** Een samengevoegd account krijgt `merged_into`, zijn opportunities verhuizen. | Auditspoor: wie, wat, waarom, wanneer. |
| **Totalen worden gecontroleerd.** Aantal en som van factuurlijnen in staging = in `fact_sales`. | Lijnen die in een join verdwijnen, zijn de klassieke stille fout. |
| **Elk getal in docs en site komt uit `data/metrics.json`.** | `scripts/build_docs.py --check` faalt in CI als tekst en model uit elkaar lopen. |

## Waar het in productie anders zou zijn

| Hier | In productie | Waarom hier zo |
|---|---|---|
| CSV-extracten | rechtstreekse lees-views op ERP en CRM, of een geplande export | geen echte systemen in een portfoliocase |
| SQLite-bestand | SQL Server-datawarehouse (schema `dwh`) — de T-SQL-versie draait in CI | SQLite draait in de browser voor de demo |
| `python3 etl/pipeline.py` met de hand | nachtelijke job (SQL Agent of Azure Data Factory) + Power BI-refresh om 06:30 | — |
| één run | logging per run in een tabel, mail bij falen ([ticket T1](../08-it-support/README.md)) | — |
