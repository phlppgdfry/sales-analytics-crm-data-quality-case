# 07 · Excel — waarom het wekelijkse rapport niet klopte

> Wat is dit: de reconciliatie tussen het Excel-rapport van sales en de omzet van finance voor Q3 2026, in Excel én in SQL. Voor wie: sales manager en finance controller. Waarom: zolang twee cijfers circuleren, praat niemand over klanten.
> Vorige → [06 · Rapportering](../06-reporting/README.md) · Volgende → [08 · IT-support](../08-it-support/README.md)

**Werkboek:** [`excel/reconciliatie-sales-finance-2026Q3.xlsx`](../../excel/reconciliatie-sales-finance-2026Q3.xlsx) — met formules, geen geplakte resultaten. Gebouwd door [`excel/build_workbook.py`](../../excel/build_workbook.py). **SQL:** [`sql/05_reconciliation.sql`](../../sql/05_reconciliation.sql).

## De brug

| Stap | | Bedrag | Rijen |
|---:|---|---:|---:|
| 1 | Wekelijks Excel-rapport (export Q3) | <!--m:recon_legacy|eur2-->€ 6.339.277,96<!--/m--> | <!--m:n_legacy_rows|int-->10.446<!--/m--> |
| 2 | Dubbel geëxporteerde dag eraf | <!--m:recon_dup_day|eur2-->-€ 110.762,20<!--/m--> | <!--m:recon_dup_day_lines|int-->231<!--/m--> |
| 3 | Creditnota's opgeteld in plaats van afgetrokken (2×) | <!--m:recon_credit|eur2-->-€ 284.980,24<!--/m--> | <!--m:recon_credit_lines|int-->314<!--/m--> |
| 4 | Personeelsshop (interne klant) eraf | <!--m:recon_internal|eur2-->-€ 2.091,46<!--/m--> | <!--m:recon_internal_lines|int-->23<!--/m--> |
| 5 | **Verklaard totaal** | <!--m:recon_explained|eur2-->€ 5.941.444,06<!--/m--> | |
| 6 | Finance (grootboek 700000) | <!--m:recon_finance|eur2-->€ 5.941.444,06<!--/m--> | |
| 7 | Datawarehouse (`[Netto-omzet]`) | <!--m:recon_model|eur2-->€ 5.941.444,06<!--/m--> | |
| | **Onverklaard verschil** | <!--m:recon_unexplained|eur2-->€ 0,00<!--/m--> | |

Het rapport stond <!--m:recon_gap_pct|pct-->6,7 %<!--/m--> te hoog: <!--m:recon_gap|eur2-->€ 397.833,90<!--/m-->.

## De drie oorzaken

1. **Creditnota's.** De export zet creditnota's als positief bedrag met factuurnummer `C…`. Het rapport telde alles op. Een creditnota van € 100 verhoogde de omzet dus met € 100 in plaats van ze met € 100 te verlagen: het verschil is 2 × het bedrag. *Grootste oorzaak.*
2. **Een dag twee keer.** Op 14 augustus liep de exportjob twee keer en werd de dag opnieuw achteraan toegevoegd. Herkenbaar doordat dezelfde factuur, hetzelfde artikel en hetzelfde bedrag twee keer voorkomen.
3. **De personeelsshop.** Aankopen van personeel lopen via klant `C99999`. Finance boekt die niet op omzet handelsgoederen.

## Zo zit het werkboek in elkaar

| Tab | Wat |
|---|---|
| Lees mij | vraag, werkwijze, conclusie |
| Export | de ruwe export als tabel `tExport` + hulpkolommen: Soort (`=IF(LEFT(B2,1)="C",…)`), Dubbel (rij gelijk aan de rij erboven na sorteren), Intern, Netto met teken |
| Finance | de drie maanden van finance |
| Brug | elke stap als `SUMIFS` op de export, naast het SQL-resultaat; kolom **Controle** toont `OK` als Excel en SQL hetzelfde tellen |
| Per verkoper | draaitabel met formules (`SUMIFS` per verkoper per maand); lege verkoper apart zichtbaar |

Waarom een formule-draaitabel en geen echte draaitabel? Een draaitabel bewaart een cache die niet meeverandert als je de export vervangt; `SUMIFS` wel. Wie liever een echte draaitabel wil: *Invoegen → Draaitabel* op `tExport`, rijen = Verkoper, kolommen = maand, waarden = Netto.

## Wat er daarna veranderde

- Het nieuwe rapport gebruikt de finance-definitie ([KPI-01](../01-business-questions/README.md#kpi-catalogus), [ADR-004](../adr/ADR-004-omzetdefinitie-finance.md)). Het Excel-bestand gaat met pensioen ([verbetervoorstel V-01](../10-improvement/README.md)).
- De export krijgt een controle: één run per dag, en een telling van rijen die vergeleken wordt met het ERP.
