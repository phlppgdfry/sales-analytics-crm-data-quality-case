# 09 · Testen — hoe je weet dat de cijfers kloppen

> Wat is dit: wat er automatisch getest wordt, wat met de gebruikers, en wat bewust niet. Voor wie: wie het rapport moet vertrouwen of aanpassen. Waarom: "het dashboard ziet er goed uit" is geen test.
> Vorige → [08 · IT-support](../08-it-support/README.md) · Volgende → [10 · Verbeteren](../10-improvement/README.md)

## Drie lagen

| Laag | Wat | Waar | Wanneer |
|---|---|---|---|
| **Datatests** | totalen staging = feiten, creditnota's negatief, sleutels uniek, elke lijn een verkoper | [`tests/test_model.py`](../../tests/test_model.py) | elke push (CI) |
| **Regeltests** | elke geplante fout wordt door haar regel gevonden; regels vuren niet op prospects; btw-controle op nagerekende nummers | [`tests/test_rules.py`](../../tests/test_rules.py), [`tests/test_vat.py`](../../tests/test_vat.py), [`tests/test_duplicates.py`](../../tests/test_duplicates.py) | elke push |
| **Cijfertests** | KPI-views kloppen onderling; brug sluit op de cent; elke maand = finance | [`tests/test_kpis.py`](../../tests/test_kpis.py), [`tests/test_reconciliation.py`](../../tests/test_reconciliation.py) | elke push |
| **Platformtests** | hetzelfde model op SQL Server 2022 geeft dezelfde KPI's; het Power BI-model is geldige TMDL | [`scripts/sqlserver_check.py`](../../scripts/sqlserver_check.py), [`tools/TmdlValidate`](../../tools/TmdlValidate/Program.cs) | elke push |
| **Documenttests** | elk getal in docs en site = `data/metrics.json` | [`scripts/build_docs.py --check`](../../scripts/build_docs.py) | elke push |
| **UAT** | de sales manager en twee accountmanagers bevestigen dat het rapport hun vragen beantwoordt | hieronder | vóór livegang |

## De belangrijkste test in één zin

> De som van alle factuurlijnen in staging is gelijk aan de som in `fact_sales`, en de netto-omzet van Q3 is gelijk aan finance tot op de cent.

Lijnen die in een join verdwijnen (een klant die niet in de dimensie staat, een artikel zonder match) zijn de meest voorkomende stille fout in BI. Die test vangt ze.

## UAT met de business (scenario's)

Uitgevoerd met de sales manager, Lotte V. (accountmanager kust) en Camille F. (Hainaut, in het Frans). Fictief, maar zo zou het verlopen.

| ID | Wie | Gegeven / wanneer / dan | Resultaat |
|---|---|---|---|
| UAT-01 | Sales manager | Gegeven Q3 2026, wanneer ik netto-omzet open, dan zie ik hetzelfde bedrag als finance | ✅ <!--m:recon_finance|eur0-->€ 5.941.444<!--/m--> |
| UAT-02 | Sales manager | Gegeven Koen vertrok op 31/3, wanneer ik omzet per verkoper voor 2025 open, dan staat 2025 op Koen en niet op Bram | ✅ |
| UAT-03 | Sales manager | Gegeven een creditnota in april voor een factuur van maart, dan verlaagt ze de omzet van de verkoper van maart | ✅ (<!--m:credit_lines_leaver_after_exit|int-->4<!--/m--> lijnen) |
| UAT-04 | Lotte V. | Wanneer ik het rapport open, dan zie ik alleen mijn klanten en mijn pipeline | ✅ (RLS) |
| UAT-05 | Camille F. | Quand j'ouvre le rapport, je vois mes clients du Hainaut depuis le 1er juin | ❌ → ✅ na ticket T2 |
| UAT-06 | Sales manager | Gegeven een klant met twee CRM-records, na samenvoegen staat al zijn pipeline op één account | ✅ |
| UAT-07 | Sales manager | Gegeven de zorggroep met drie campussen, dan blijven het drie klanten met elk hun omzet | ✅ |
| UAT-08 | Lotte V. | Wanneer ik "vergeten deals" open, dan zie ik mijn deals zonder update > 60 dagen, grootste eerst | ✅ |
| UAT-09 | Sales manager | Gegeven een artikel zonder categorie, dan zie ik het als "Onbekend" en niet als ontbrekende omzet | ✅ |
| UAT-10 | Finance controller | Gegeven de personeelsshop, dan telt ze niet mee in omzet maar is ze wel terug te vinden | ✅ |

**Defect uit de UAT:** UAT-05 faalde (leeg rapport voor Camille). Oorzaak en oplossing: [T2](../08-it-support/README.md#t2--je-ne-vois-aucun-client-dans-le-rapport). Ernst: hoog voor één gebruiker; geen blokkade voor livegang omdat de oorzaak in de brondata zat en dezelfde dag opgelost werd.

## Wat niet getest is

- De DAX-measures in een echte Power BI-engine (geen Windows/Power BI Desktop in CI). De SQL-tegenhangers zijn wel getest en het model is structureel gevalideerd.
- Prestaties met meer data dan ± 76.000 lijnen.
- De nachtelijke planning en de gateway (bestaan in deze case alleen op papier).
