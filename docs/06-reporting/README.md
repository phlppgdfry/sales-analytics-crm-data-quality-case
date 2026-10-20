# 06 · Rapportering — vier pagina's in Power BI, één definitie per cijfer

> Wat is dit: het ontwerp van het salesrapport: pagina's, measures, beveiliging per verkoper en verversing. Voor wie: sales manager (wat staat waar), wie het rapport bouwt of onderhoudt. Waarom: de vacature draait om "dashboards afgestemd op de behoeften en resultaten van het Sales team".
> Vorige → [05 · CRM-kwaliteit](../05-crm-quality/README.md) · Volgende → [07 · Excel](../07-excel/README.md)

## Wat er in de repo staat

| Onderdeel | Pad | Status |
|---|---|---|
| Semantisch model als code (TMDL): 10 tabellen, relaties, 18 measures, 2 rollen | [`powerbi/Vennaert Sales.SemanticModel/`](../../powerbi/Vennaert%20Sales.SemanticModel/definition/model.tmdl) | wordt in CI ingelezen met Microsofts TMDL-serializer ([`tools/TmdlValidate`](../../tools/TmdlValidate/Program.cs)) |
| Measures (DAX) | [`definition/tables/Measures.tmdl`](../../powerbi/Vennaert%20Sales.SemanticModel/definition/tables/Measures.tmdl) | geschreven; **niet uitgevoerd in een Power BI-engine** — de SQL-tegenhanger van elke KPI is wel getest |
| Tabeldefinities | `definition/tables/*.tmdl` | gegenereerd uit het warehouse ([`scripts/build_tmdl.py`](../../scripts/build_tmdl.py)), dus altijd gelijk aan de SQL |
| Bron | SQL Server, schema `dwh` ([`sql/tsql/`](../../sql/tsql/01_schema.sql)) | in CI op SQL Server 2022 gedraaid en vergeleken met SQLite |
| Rapportpagina's | webdemo, tab **Dashboard** | dezelfde vier pagina's en dezelfde cijfers, in de browser |

Een `.pbix` of gepubliceerd rapport zit er niet in: Power BI Desktop draait alleen op Windows. Het [bouwplan onderaan](#het-rapport-bouwen-in-power-bi-desktop) beschrijft hoe het rapport op dit model gebouwd wordt.

## De vier pagina's

### 1. Overzicht — "hoe staan we ervoor?"
Voor de sales manager en de directie. Leest van links naar rechts: resultaat → vergelijking → trend.

| Visual | Measure(s) | Waarde nu (jan–sep 2026) |
|---|---|---|
| Kaart: netto-omzet YTD | `[Netto-omzet YTD]` | <!--m:net_revenue_ytd|eur0-->€ 18.702.899<!--/m--> |
| Kaart: groei vs vorig jaar | `[Groei %]` | <!--m:growth_pct|pct-->4,4 %<!--/m--> |
| Kaart: marge | `[Marge %]` | <!--m:margin_pct_ytd|pct-->40,4 %<!--/m--> |
| Kaart: target-realisatie | `[Target-realisatie %]` | <!--m:target_attainment_pct|pct-->98,5 %<!--/m--> |
| Lijn + kolom: omzet per maand tegenover target en vorig jaar | `[Netto-omzet]`, `[Target]`, `[Netto-omzet vorig jaar]` | |
| Kaart: CRM-gezondheid | `[CRM-gezondheid %]` | <!--m:dq_health_after|pct-->98,0 %<!--/m--> |

### 2. Verkoop — "wie, waar, wat?"
Voor de sales manager in het maandgesprek per verkoper.
- Staafdiagram omzet per verkoper met target als markering (`[Netto-omzet]`, `[Target]`, `[Target-realisatie %]`).
- Omzet en marge per productcategorie en per segment.
- Top 10 klanten van de laatste 12 maanden met marge.
- Slicers: periode, segment, verkoper. Accountmanagers zien automatisch alleen hun eigen rij (RLS).

### 3. Pipeline — "wat komt er aan, en wat is vergeten?"
- Trechter per fase met `[Open pipeline]` en `[Gewogen pipeline]`: <!--m:open_pipeline|eur0-->€ 2.316.000<!--/m--> open, <!--m:weighted_pipeline|eur0-->€ 1.017.906<!--/m--> gewogen.
- `[Win rate %]` op de afsluitdatum (inactieve relatie + `USERELATIONSHIP`): <!--m:win_rate_12m_pct|pct-->54,6 %<!--/m--> over de laatste 12 maanden.
- Tabel "vergeten deals": `[Verouderde deals]` = <!--m:stale_opportunities|int-->80<!--/m--> open opportunities zonder update in meer dan 60 dagen, gesorteerd op bedrag — het lijstje voor maandag.

### 4. CRM-gezondheid — "kunnen we de cijfers vertrouwen?"
- Score vóór en na: `[CRM-gezondheid % (voor)]` <!--m:dq_health_before|pct-->75,0 %<!--/m--> → `[CRM-gezondheid %]` <!--m:dq_health_after|pct-->98,0 %<!--/m-->.
- Matrix per regel (tabel `dq_rule_summary`): meldingen vóór/na, eigenaar.
- `[Omzet zonder verkoper (afgeleid)]`: hoeveel omzet het model zelf aan een verkoper moest toewijzen — gaat dit omhoog, dan typt de boekhouding weer facturen zonder verkoper.

## Drie measures uitgelegd

```dax
Netto-omzet = CALCULATE ( SUM ( fact_sales[net_amount] ), dim_customer[is_internal] = 0 )
```
Creditnota's zijn al negatief in de feitentabel, dus een gewone `SUM` is de finance-definitie. De filter op de personeelsshop staat hier, op één plek; elke andere omzet-measure bouwt op `[Netto-omzet]`.

```dax
Groei % = DIVIDE ( [Netto-omzet] - [Netto-omzet vorig jaar], [Netto-omzet vorig jaar] )
```
`DIVIDE` in plaats van `/`: geeft leeg in plaats van een fout als vorig jaar nul is (nieuwe verkoper, nieuwe categorie). `[Netto-omzet vorig jaar]` gebruikt `SAMEPERIODLASTYEAR`, wat werkt omdat `dim_date` als datumtabel gemarkeerd is.

```dax
Win rate % =
    VAR won    = CALCULATE ( COUNTROWS ( fact_opportunity ), fact_opportunity[stage] = "Gewonnen",
                             USERELATIONSHIP ( fact_opportunity[close_date_key], dim_date[date_key] ) )
    VAR closed = CALCULATE ( COUNTROWS ( fact_opportunity ), fact_opportunity[is_open] = 0,
                             USERELATIONSHIP ( fact_opportunity[close_date_key], dim_date[date_key] ) )
    RETURN DIVIDE ( won, closed )
```
De actieve relatie met de datum loopt via de aanmaakdatum. Voor de win rate wil je de deals die in de periode **afgesloten** werden; `USERELATIONSHIP` activeert de tweede relatie alleen binnen deze measure.

## Beveiliging per verkoper (RLS)

Rol `Accountmanager` in het model:

```dax
dim_rep[email] = USERPRINCIPALNAME ()
```

De filter op `dim_rep` loopt via de relaties door naar omzet, opportunities en targets. Leden worden in de Power BI-service toegewezen via een Entra ID-groep, niet in het model. Sales manager, finance en de analist zitten in rol `Sales management` (geen filter).

Valkuil die in [ticket T2](../08-it-support/README.md#t2--je-ne-vois-aucun-client-dans-le-rapport) echt gebeurt: een nieuwe verkoper zonder of met een fout e-mailadres in `dim_rep` ziet een leeg rapport, zonder foutmelding.

## Verversen

| Stap | Wanneer | Bij falen |
|---|---|---|
| ETL naar het datawarehouse | elke nacht 05:30 | mail naar de analist; rapport toont gisteren |
| Power BI-refresh (import) | 06:30 en 12:30 | mail naar de eigenaar van de dataset; zie [runbook T1](../08-it-support/README.md#t1--het-salesrapport-toont-cijfers-van-gisteren) |
| Peildatum op elke pagina | "Gegevens tot en met …" uit `meta.as_of_date` | gebruikers zien zelf of het rapport actueel is |

## Het rapport bouwen in Power BI Desktop

1. Maak in Power BI Desktop (Windows) een nieuw project en sla het op als Power BI-project (`.pbip`). Vervang de map `<naam>.SemanticModel/definition` door [`definition/`](../../powerbi/Vennaert%20Sales.SemanticModel/definition/model.tmdl) uit deze repo en open het project opnieuw. (Alternatief: Tabular Editor → *Open from folder*.)
2. Zet de parameters `Server` en `Database` naar de eigen SQL Server met het `dwh`-schema (eerst [`sql/tsql/`](../../sql/tsql/01_schema.sql) draaien en laden).
3. *Vernieuwen* → controleer: `[Netto-omzet]` voor sep 2026 = de waarde van `v_sales_monthly` voor `2026-09`.
4. Bouw de vier pagina's hierboven; gebruik alleen measures uit de map *Measures* (impliciete measures staan uit).
5. *Modellering → Rollen weergeven als* `Accountmanager` met `lotte.v@vennaert.example` → alleen haar klanten.
