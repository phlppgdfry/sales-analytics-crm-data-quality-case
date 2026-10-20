# 02 · Bronnen — wat er binnenkomt en wat eraan schort

> Wat is dit: per bron wat ze bevat, wie eigenaar is, en welke problemen data profiling toonde. Voor wie: wie de pipeline onderhoudt of een cijfer moet verdedigen. Waarom: je kan een rapport pas vertrouwen als je weet waar het op rust.
> Vorige → [01 · Businessvragen](../01-business-questions/README.md) · Volgende → [03 · Model](../03-modelling/README.md)

## Overzicht

| Extract | Systeem | Eigenaar | Rijen | Korrel | Valkuil |
|---|---|---|---:|---|---|
| [`erp_invoice_lines.csv`](../../data/raw/erp_invoice_lines.csv) | ERP | Finance | <!--m:n_invoice_lines|int-->76.144<!--/m--> | factuur- of creditnotalijn | creditnota's staan er **positief** in, met `doc_type = C` |
| [`erp_customers.csv`](../../data/raw/erp_customers.csv) | ERP | Finance / administratie | <!--m:n_erp_customers_all|int-->1.380<!--/m--> | klant | de personeelsshop is ook een "klant" |
| [`erp_customer_rep_history.csv`](../../data/raw/erp_customer_rep_history.csv) | ERP | Sales manager | 1 rij per klant per periode | klant × geldigheidsperiode | de enige bron die weet wie wanneer eigenaar was |
| [`erp_products.csv`](../../data/raw/erp_products.csv) | ERP | Aankoop | <!--m:n_products|int-->385<!--/m--> | artikel | ontbrekende categorie, één kostprijs = 0 |
| [`erp_sales_reps.csv`](../../data/raw/erp_sales_reps.csv) | ERP / HR | Sales manager | <!--m:n_reps|int-->13<!--/m--> | verkoper | einddatum = uit dienst |
| [`crm_accounts.csv`](../../data/raw/crm_accounts.csv) | CRM | Accounteigenaars | <!--m:n_crm_accounts|int-->1.705<!--/m--> | account | dubbels, ontbrekende koppeling, vrije tekst voor btw |
| [`crm_opportunities.csv`](../../data/raw/crm_opportunities.csv) | CRM | Accounteigenaars | <!--m:n_opportunities|int-->1.649<!--/m--> | opportunity | vergeten deals, geen bedrag |
| [`sales_targets_2026.csv`](../../data/raw/sales_targets_2026.csv) | Excel sales manager | Sales manager | <!--m:n_targets|int-->139<!--/m--> | verkoper × maand | handmatig, alleen 2026 |
| [`legacy_sales_export_2026Q3.csv`](../../data/raw/legacy_sales_export_2026Q3.csv) | export voor het Excel-rapport | Sales manager | <!--m:n_legacy_rows|int-->10.446<!--/m--> | exportrij | één dag twee keer geëxporteerd |
| [`finance_revenue_2026Q3.csv`](../../data/raw/finance_revenue_2026Q3.csv) | boekhouding | Finance | 3 | maand | referentie voor de reconciliatie |

## Data profiling — wat opviel

Profiling = per kolom kijken naar lege waarden, formaten, uitschieters en dubbels, vóór je iets bouwt. De tellingen hieronder komen uit de pipeline (snapshot "vóór").

| Bevinding | Aantal | Waarom het ertoe doet | Regel |
|---|---:|---|---|
| CRM-accountparen die op elkaar lijken | <!--m:dup_pairs_before|int-->165<!--/m--> paren | omzet en pipeline van één klant staan verspreid over twee records | CRM-01 |
| Btw-nummer met foute controlecijfers | <!--m:rule_crm02_before|int-->23<!--/m--> | koppeling met ERP en duplicaatdetectie werken niet | CRM-02 |
| Klant zonder btw-nummer in het CRM | <!--m:rule_crm03_before|int-->18<!--/m--> | idem | CRM-03 |
| Account niet gekoppeld aan zijn ERP-klant | <!--m:rule_crm04_before|int-->61<!--/m--> | klant lijkt "prospect"; omzet zichtbaar in ERP maar niet bij het account | CRM-04 |
| Accounts op naam van een vertrokken verkoper | <!--m:rule_crm05_before|int-->151<!--/m--> | niemand volgt op | CRM-05 |
| Geen e-mail en geen telefoon | <!--m:rule_crm06_before|int-->95<!--/m--> | onbereikbaar | CRM-06 |
| Postcode in verkeerd formaat (`B-8800`) | <!--m:rule_crm07_before|int-->14<!--/m--> | filters per regio missen klanten | CRM-07 |
| Factuurlijnen zonder verkoper | <!--m:rule_erp01_before|int-->1.431<!--/m--> | <!--m:unassigned_revenue_naive|eur0-->€ 774.605<!--/m--> omzet zou als "niet toegewezen" verschijnen | ERP-01 |
| Artikelen zonder categorie / kostprijs 0 | <!--m:rule_erp02_before|int-->6<!--/m--> / <!--m:rule_erp03_before|int-->1<!--/m--> | omzet per categorie onvolledig; één artikel toont 100 % marge | ERP-02/03 |
| Open opportunities zonder update > 60 dagen | <!--m:rule_opp01_before|int-->80<!--/m--> | pipeline lijkt groter dan ze is | OPP-01 |
| Open opportunities met verlopen afsluitdatum | <!--m:rule_opp02_before|int-->280<!--/m--> | idem | OPP-02 |
| Offerte of onderhandeling zonder bedrag | <!--m:rule_opp03_before|int-->21<!--/m--> | telt niet mee in de gewogen pipeline | OPP-03 |

Alle regels met eigenaar en oplossing: [05 · regels](../05-crm-quality/rules.md).

## Wat níet fout is (en ook zo behandeld wordt)

- **Prospects zonder btw-nummer of ERP-koppeling** — normaal. De regels voor klanten (CRM-03, CRM-04) vuren niet op prospects; een test bewaakt dat.
- **Eén btw-nummer op meerdere ERP-klanten** — een zorggroep met drie campussen is één vennootschap met drie leveradressen. Dat is geen duplicaat, en precies daarom beslist een mens ([duplicaten](../05-crm-quality/duplicates.md)).
- **Creditnota's na het vertrek van een verkoper** — <!--m:credit_lines_leaver_after_exit|int-->4<!--/m--> lijnen corrigeren een factuur van vóór zijn vertrek en blijven bij hem ([ADR-002](../adr/ADR-002-omzet-op-verkoper-van-het-moment.md)).

## Hoe de data gemaakt is

[`generator/generate_sources.py`](../../generator/generate_sources.py) maakt alle extracten met vaste seed. Seizoenen (dip in augustus), groei (± 4,5 % per jaar), klantverloop, kortingen voor key accounts en de geplante fouten zitten erin. [`data/raw/_planted.json`](../../data/raw/_planted.json) somt de geplante fouten op — gebruikt door de tests, nooit door de pipeline.
