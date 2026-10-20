# Datakwaliteitsregels

> Wat is dit: de catalogus van alle regels, met eigenaar en de telling vóór en na de correcties. Voor wie: wie wil weten waarom een account op de lijst staat. Waarom: een regel zonder eigenaar is een rapport dat niemand leest.
> Terug → [05 · CRM-kwaliteit](README.md) · SQL: [`sql/02_dq_rules.sql`](../../sql/02_dq_rules.sql) · bron van deze tabel: [`data/reference/dq_rules.csv`](../../data/reference/dq_rules.csv)

**Blokkerend** = maakt het rapport fout (omzet bij de verkeerde klant of verkoper, foute marge, onzichtbare pipeline). **Waarschuwing** = maakt opvolging moeilijker, maar het cijfer klopt.

<!--table:dq_rules-->
| ID | Regel | Ernst | Eigenaar | Vóór | Na | Oplossing |
|---|---|---|---|---:|---:|---|
| CRM-01 | Mogelijk dubbel account | blokkerend | Data analyst + accounteigenaar | 165 | 5 | Beoordelen in de duplicatenwachtrij; samenvoegen volgens de overlevingsregels |
| CRM-02 | Btw-nummer met foute controlecijfers | blokkerend | Accounteigenaar | 23 | 23 | Juist nummer opvragen of opzoeken in de KBO; nooit gokken |
| CRM-03 | Klant zonder btw-nummer | waarschuwing | Accounteigenaar | 18 | 18 | Btw-nummer aanvullen bij de volgende order |
| CRM-04 | ERP-klant niet gekoppeld aan CRM-account | blokkerend | Data analyst | 61 | 0 | Koppeling voorstellen als het btw-nummer uniek overeenkomt; anders manueel |
| CRM-05 | Eigenaar is uit dienst | blokkerend | Sales manager | 151 | 0 | Account overzetten naar de huidige ERP-verkoper van die klant |
| CRM-06 | Geen e-mail en geen telefoon | waarschuwing | Accounteigenaar | 95 | 74 | Contactgegevens aanvullen; anders account op inactief na 12 maanden |
| CRM-07 | Postcode past niet bij het land | waarschuwing | Data analyst | 14 | 14 | Formaat corrigeren (BE 4 cijfers / FR 5 cijfers) |
| OPP-01 | Open opportunity zonder update > 60 dagen | waarschuwing | Accounteigenaar | 80 | 80 | Bijwerken of afsluiten met reden |
| OPP-02 | Open opportunity met verlopen afsluitdatum | waarschuwing | Accounteigenaar | 280 | 280 | Nieuwe datum of afsluiten met reden |
| OPP-03 | Offerte of onderhandeling zonder bedrag | blokkerend | Accounteigenaar | 21 | 21 | Bedrag invullen; zonder bedrag telt de deal niet mee in de gewogen pipeline |
| ERP-01 | Factuurlijn zonder verkoper | waarschuwing | Data analyst | 1.431 | 0 | Opgelost in het model: verkoper op factuurdatum uit de ERP-historiek |
| ERP-02 | Artikel zonder categorie | waarschuwing | Aankoop | 6 | 6 | Categorie toekennen in de artikelfiche |
| ERP-03 | Artikel met kostprijs 0 | blokkerend | Aankoop | 1 | 1 | Kostprijs corrigeren; tot dan toont elke verkoop van dat artikel 100 % marge |
<!--/table-->

## CRM-gezondheid

> Aandeel klantaccounts (gekoppeld aan het ERP of het zouden moeten zijn) zonder blokkerend probleem. Bij een duplicaatpaar telt het probleem voor beide records.

Vóór: <!--m:dq_clean_before|int-->1.036<!--/m--> van <!--m:dq_scope_before|int-->1.382<!--/m--> = <!--m:dq_health_before|pct-->75,0 %<!--/m-->. Na: <!--m:dq_clean_after|int-->1.351<!--/m--> van <!--m:dq_scope_after|int-->1.379<!--/m--> = <!--m:dq_health_after|pct-->98,0 %<!--/m-->.

## Twee regels uitgelegd

**CRM-02 — btw-controlecijfers.** Een Belgisch ondernemingsnummer heeft 10 cijfers; de laatste twee zijn `97 − (eerste 8 cijfers mod 97)`. Eén verkeerd getypt cijfer en de controle faalt. In SQL:

```sql
CASE WHEN 97 - (CAST(substr(vat_norm, 3, 8) AS INTEGER) % 97) = CAST(substr(vat_norm, 11, 2) AS INTEGER)
     THEN 1 ELSE 0 END AS vat_valid
```

Voor Frankrijk: sleutel = `(12 + 3 × (SIREN mod 97)) mod 97`. Tests met handmatig nagerekende nummers: [`tests/test_vat.py`](../../tests/test_vat.py).

**CRM-04 — ontbrekende ERP-koppeling.** Een account zonder ERP-klantnummer is niet automatisch een fout: het kan een prospect zijn. De regel vuurt alleen als het btw-nummer overeenkomt met een ERP-klant waar nog geen enkel account aan hangt. Hangt er al een account aan, dan is het geen koppelprobleem maar een duplicaat (CRM-01). De correctie koppelt alleen als er precies één kandidaat is én de naam voor minstens 80 % gelijkt — <!--m:changes_link|int-->58<!--/m--> keer in deze run.
