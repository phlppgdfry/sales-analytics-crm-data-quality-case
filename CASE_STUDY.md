# Case study — Vennaert: van twee waarheden naar één salesrapport

*Fictief bedrijf, gegenereerde data. ± 6 minuten lezen.*

## De situatie

Vennaert verkoopt schoonmaak- en hygiëneproducten aan <!--m:n_customers|int-->1.379<!--/m--> bedrijfsklanten in Vlaanderen, Wallonië en Noord-Frankrijk. Dertien verkopers, een ERP, een CRM, een datawarehouse op SQL Server, Power BI — en een Excel-bestand dat de sales manager elke maandag zelf bijwerkt, omdat "dat tenminste klopt".

Het klopte niet. Voor Q3 2026 toonde het <!--m:recon_legacy|eur0-->€ 6.339.278<!--/m--> omzet; finance boekte <!--m:recon_finance|eur0-->€ 5.941.444<!--/m-->.

## Eerst de vraag

Ik begon niet met een dashboard maar met een gesprek: wat wil de sales manager weten, wat doet ze met het antwoord, en wat bedoelt ze met "omzet"? Daaruit kwamen vijf vragen en drie afspraken die alles daarna bepaalden: omzet is de definitie van finance; omzet hoort bij de verkoper die de klant had op de factuurdatum; en niets in het CRM wordt automatisch samengevoegd of verwijderd. Elke KPI kreeg één definitie, één eigenaar, een DAX-measure en een geteste SQL-tegenhanger.

## Wat de data vertelde

Profiling van de bronnen leverde <!--m:dq_issues_before|int-->2.346<!--/m--> meldingen op over 13 regels. De belangrijkste:

- het Excel-rapport telde **creditnota's op** in plaats van ze af te trekken, rekende **één dag twee keer** en nam de **personeelsshop** mee — samen exact het verschil met finance;
- <!--m:rule_erp01_before|int-->1.431<!--/m--> factuurlijnen zonder verkoper: <!--m:unassigned_revenue_naive|eur0-->€ 774.605<!--/m--> omzet die als "niet toegewezen" zou verschijnen;
- <!--m:dup_pairs_before|int-->165<!--/m--> paren CRM-accounts die op elkaar leken, en <!--m:rule_crm05_before|int-->151<!--/m--> accounts op naam van een verkoper die in maart vertrok;
- <!--m:stale_opportunities|int-->80<!--/m--> open deals zonder update in meer dan 60 dagen.

## Wat ik bouwde

Een **pipeline** die elke keer vanaf de bron opnieuw opbouwt: staging herstelt formaten, regels vinden problemen, correcties worden gelogd, en pas dan wordt het **sterschema** gebouwd. Dezelfde tabellen en views bestaan in T-SQL; in CI worden ze in SQL Server 2022 geladen en moeten ze dezelfde cijfers geven.

Daarop een **Power BI-model als code**: vier rapportpagina's (overzicht, verkoop, pipeline, CRM-gezondheid), measures die op `[Netto-omzet]` verder bouwen, een inactieve relatie voor de win rate op afsluitdatum, en rijbeveiliging zodat elke accountmanager alleen zijn eigen klanten ziet.

Voor het CRM een **workflow** met drie soorten oplossing, omdat drie soorten problemen een andere beslisser hebben: duplicaten beoordeelt de accounteigenaar (met score en bewijs), eenduidige correcties keurt de sales manager in batch goed, en ontbrekende informatie wordt een taak voor de accounteigenaar.

## De moeilijkste beslissing

De duplicaatdetectie gaf sommige paren een hoge score die géén duplicaat waren: een zorggroep met drie campussen deelt één btw-nummer en bijna dezelfde naam. Automatisch samenvoegen boven een drempel zou die klanten vermengd hebben — met hun omzet, contactpersonen en leveradressen. Daarom beslist een mens, met het bewijs naast elkaar, en wordt "geen duplicaat" onthouden. Prijs: twee reviewsessies van een uur. Resultaat: <!--m:review_samenvoegen|int-->145<!--/m--> keer samenvoegen, <!--m:review_geen_duplicaat|int-->15<!--/m--> keer bewust niet.

## Resultaat (gesimuleerd)

- Onverklaard verschil tussen rapport en finance: **<!--m:recon_unexplained|eur2-->€ 0,00<!--/m-->**.
- CRM-gezondheid: **<!--m:dq_health_before|pct-->75,0 %<!--/m--> → <!--m:dq_health_after|pct-->98,0 %<!--/m-->**; wat overblijft vraagt informatie van de klant.
- Eén rapport met de finance-definitie, zodat het Excel-bestand met pensioen kan — na vier weken naast elkaar, op het tempo van de sales manager.

## Wat het zegt over hoe ik werk

Ik begin bij de vraag en de definitie, niet bij de tool. Ik maak fouten zichtbaar in plaats van ze weg te filteren. Ik laat mensen beslissen waar de data het niet weet, en ik schrijf op waarom — zodat een collega het kan overnemen.

**Beperkingen:** fictief bedrijf en data; reviewbeslissingen, UAT en tickets zijn gesimuleerd; de DAX is niet in Power BI uitgevoerd.
