# 01 · Businessvragen — eerst de vraag, dan de data

> Wat is dit: de intake met sales en finance, vertaald naar vragen, KPI's en afspraken. Voor wie: sales manager, finance, en wie het rapport later onderhoudt. Waarom: een dashboard zonder afgesproken definities wordt een discussie over cijfers in plaats van over klanten.
> Vorige → [00 · Context](../00-context/README.md) · Volgende → [02 · Bronnen](../02-sources/README.md)

## Wie heeft wat nodig

| Stakeholder | Wil weten | Gebruikt het voor | Pijn vandaag |
|---|---|---|---|
| Sales manager | omzet en marge per verkoper tegenover target; pipeline; welke klanten zakken | maandelijks gesprek per verkoper, prognose voor directie | maandag een uur Excel bijwerken; cijfer verschilt van finance |
| Accountmanagers (buitendienst, NL en FR) | eigen klanten, eigen pipeline, wie al lang niets bestelde | klantbezoek voorbereiden | moeten het Excel-bestand van de manager vragen; zien collega's cijfers wel of niet |
| Finance controller | dat sales en finance hetzelfde getal gebruiken | maandafsluiting, commissieberekening | discussies over "welke omzet" |
| Directie | trend, groei vs vorig jaar, marge | kwartaalrapport aan de raad van bestuur | krijgt twee versies van de waarheid |
| Data analyst (deze rol) | waar de data vandaan komt en hoe betrouwbaar ze is | rapporten bouwen en verdedigen | geen afgesproken definities, vervuild CRM |

## De intake in vijf vragen

Uit het gesprek met de sales manager (fictief, 2 oktober 2026), letterlijk genoteerd en daarna vertaald:

| # | Wat ze zei | Wat de vraag eigenlijk is | Antwoord in deze case |
|---|---|---|---|
| V1 | "Excel zegt meer dan finance." | Welke omzetdefinitie gebruiken we, en waar zit het verschil? | [Reconciliatie](../07-excel/README.md): <!--m:recon_gap|eur2-->€ 397.833,90<!--/m--> verschil, volledig verklaard |
| V2 | "Ik wil zien waar elke verkoper staat." | Omzet en marge per verkoper per maand tegenover target, op de verkoper van dát moment | [Rapportpagina Verkoop](../06-reporting/README.md) + [ADR-002](../adr/ADR-002-omzet-op-verkoper-van-het-moment.md) |
| V3 | "Het CRM klopt niet." | Welke fouten, hoeveel, wat kost het, wie lost wat op? | [CRM-kwaliteit](../05-crm-quality/README.md): <!--m:dq_issues_before|int-->2.346<!--/m--> meldingen over 13 regels |
| V4 | "Welke deals zijn echt?" | Hoeveel van de pipeline is actueel, en hoeveel is vergeten? | [Pipeline](../06-reporting/README.md): <!--m:stale_opportunities|int-->80<!--/m--> open deals zonder update > 60 dagen |
| V5 | "Kan dat Excel weg?" | Kan een automatisch ververst rapport het wekelijkse handwerk vervangen, met dezelfde cijfers als finance? | [Verbetervoorstel](../10-improvement/README.md) |

## Afspraken die we eerst maakten

1. **Omzet = de finance-definitie** (grootboek 700000): facturen min creditnota's, excl. btw, excl. de personeelsshop. Finance is eigenaar van de definitie, sales van het gebruik. → [ADR-004](../adr/ADR-004-omzetdefinitie-finance.md)
2. **Omzet hoort bij de verkoper die de klant had op de factuurdatum**, niet bij de huidige eigenaar. Anders "erft" de opvolger van Koen zijn hele 2025. → [ADR-002](../adr/ADR-002-omzet-op-verkoper-van-het-moment.md)
3. **Niets in het CRM wordt automatisch samengevoegd of verwijderd.** De analist stelt voor, de accounteigenaar beslist, alles wordt gelogd. → [ADR-003](../adr/ADR-003-samenvoegen-alleen-na-menselijke-beslissing.md)
4. **Elke accountmanager ziet alleen zijn eigen klanten**; sales manager en finance zien alles. → [beveiliging op rijniveau](../06-reporting/README.md#beveiliging-per-verkoper-rls)
5. **Peildatum** van alle cijfers in de case: <!--m:as_of-->2026-09-30<!--/m-->.

## KPI-catalogus

Elke KPI heeft één definitie, één eigenaar, een DAX-measure in het Power BI-model en een SQL-tegenhanger die getest wordt. Bron: [`data/reference/kpi_catalog.csv`](../../data/reference/kpi_catalog.csv).

<!--table:kpi_catalog-->
| ID | KPI | Definitie | DAX-measure | SQL | Eigenaar | Frequentie |
|---|---|---|---|---|---|---|
| KPI-01 | **Netto-omzet** | Som van factuurlijnen min creditnota's, excl. btw, excl. interne klant (personeelsshop). Zelfde definitie als finance op grootboek 700000. | `[Netto-omzet]` | `v_sales_monthly.net_revenue` | Finance (definitie) / Sales manager (gebruik) | dagelijks |
| KPI-02 | **Brutomarge** | Netto-omzet min kostprijs (aantal × kostprijs uit de artikelfiche op het moment van de load). | `[Brutomarge]` | `v_sales_monthly.gross_margin` | Finance | dagelijks |
| KPI-03 | **Marge %** | Brutomarge / Netto-omzet. | `[Marge %]` | `v_sales_monthly.margin_pct` | Finance | dagelijks |
| KPI-04 | **Actieve klanten** | Aantal verschillende klanten met minstens één factuur of creditnota in de periode. | `[Actieve klanten]` | `v_sales_monthly.active_customers` | Sales manager | maandelijks |
| KPI-05 | **Groei % (vs vorig jaar)** | Netto-omzet periode t.o.v. dezelfde periode vorig jaar. | `[Groei %]` | `v_kpi_ytd.growth_pct` | Sales manager | maandelijks |
| KPI-06 | **Target-realisatie %** | Netto-omzet / target van de verkoper voor dezelfde maanden. Targets komen uit het Excel-bestand van de sales manager. | `[Target-realisatie %]` | `v_rep_month_vs_target.attainment_pct` | Sales manager | maandelijks |
| KPI-07 | **Gem. factuurwaarde** | Netto-omzet / aantal facturen (creditnota's tellen niet als factuur). | `[Gem. factuurwaarde]` | `v_kpi_ytd.avg_invoice_value_ytd` | Sales manager | maandelijks |
| KPI-08 | **Open pipeline** | Som van de bedragen van open opportunities (fase Prospectie t.e.m. Onderhandeling). | `[Open pipeline]` | `v_pipeline_by_stage.amount` | Sales manager | wekelijks |
| KPI-09 | **Gewogen pipeline** | Som van bedrag × slaagkans per fase (10/25/50/75 %). | `[Gewogen pipeline]` | `v_pipeline_by_stage.weighted_amount` | Sales manager | wekelijks |
| KPI-10 | **Win rate %** | Gewonnen / (gewonnen + verloren) voor opportunities afgesloten in de periode. | `[Win rate %]` | `v_win_rate_12m.win_rate_pct` | Sales manager | maandelijks |
| KPI-11 | **CRM-gezondheid %** | Aandeel klantaccounts zonder blokkerend datakwaliteitsprobleem (CRM-01/02/04/05). | `[CRM-gezondheid %]` | `dq_health.health_pct` | Data analyst | wekelijks |
| KPI-12 | **Verouderde deals** | Open opportunities zonder update in meer dan 60 dagen. | `[Verouderde deals]` | `v_pipeline_by_stage.stale` | Accounteigenaars | wekelijks |
<!--/table-->

## Wat ik bewust níet als KPI opnam

- **"Aantal klantbezoeken"** — staat niet betrouwbaar in het CRM; eerst de registratie afspreken, anders meet je wie het meest invult.
- **Marge per verkoper als rangschikking** — de verkoper kiest de klantmix niet altijd zelf (key accounts krijgen kortingen); tonen ja, rangschikken nee.
- **Prognose op basis van gewogen pipeline** — met <!--m:rule_opp02_before|int-->280<!--/m--> open deals waarvan de afsluitdatum voorbij is, is de pipeline eerst een opkuisproject.
