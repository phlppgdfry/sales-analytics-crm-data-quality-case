# 00 · Context — Vennaert en de vraag van sales

> Wat is dit: het vertrekpunt van de case. Voor wie: iedereen die de case voor het eerst opent. Waarom: zonder context lijkt elk dashboard willekeurig.
> Volgende stap → [01 · Businessvragen](../01-business-questions/README.md)

*Onafhankelijke portfoliocase over een fictief bedrijf. Bevat geen vertrouwelijke informatie van een bestaande werkgever. Alle cijfers zijn illustratieve aannames — geen echte bedrijfsdata.*

## Het bedrijf (fictief)

**Vennaert** is een Belgische B2B-groothandel in professionele schoonmaak- en hygiëneproducten, met kantoor en magazijn in West-Vlaanderen. Klanten zijn schoonmaakbedrijven, zorginstellingen, horeca, industrie en scholen/gemeenten in Vlaanderen, Wallonië en Noord-Frankrijk.

| | Aanname |
|---|---|
| Klanten (ERP, commercieel) | <!--m:n_customers|int-->1.379<!--/m--> |
| Artikelen | <!--m:n_products|int-->385<!--/m--> in 7 categorieën |
| Verkopers | <!--m:n_reps|int-->13<!--/m--> (9 buitendienst, 2 binnendienst, 1 key accounts; één vertrokken, twee nieuw in 2026) |
| Factuurlijnen 2025 – sep 2026 | <!--m:n_invoice_lines|int-->76.144<!--/m--> (waarvan <!--m:n_credit_lines|int-->2.073<!--/m--> creditnotalijnen) |
| Netto-omzet jan–sep 2026 | <!--m:net_revenue_ytd|eur0-->€ 18.702.899<!--/m--> |
| CRM-accounts | <!--m:n_crm_accounts|int-->1.705<!--/m--> · opportunities: <!--m:n_opportunities|int-->1.649<!--/m--> |
| Taal klanten | Nederlands en Frans (Wallonië, Hauts-de-France) |

**Systemen:** een ERP (orders, facturen, artikelen, verkoper per klant met historiek), een CRM (accounts, contacten, opportunities), een intern datawarehouse op SQL Server, Power BI voor rapportering, en — nog altijd — een wekelijks Excel-bestand dat de sales manager zelf bijwerkt.

## Waarom nu

In oktober 2026 vraagt de sales manager drie dingen:

1. *"Ons Excel-rapport zegt voor Q3 bijna € 400.000 meer dan finance. Wie heeft gelijk?"* ([reconciliatie](../07-excel/README.md))
2. *"Ik wil per verkoper zien waar we staan tegenover target, zonder elke maandag een uur te knippen en plakken."* ([rapportering](../06-reporting/README.md))
3. *"Het CRM klopt niet: klanten staan er dubbel in, accounts van Koen staan nog op zijn naam terwijl hij in maart vertrok."* ([CRM-kwaliteit](../05-crm-quality/README.md))

Daarbovenop: de dagelijkse IT-vragen van collega's ([IT-support](../08-it-support/README.md)) en een paar kleine verbeterprojecten ([verbeteren](../10-improvement/README.md)).

## Scope

| In scope | Buiten scope |
|---|---|
| Bronnen begrijpen en profileren | Een nieuw CRM kiezen |
| Datakwaliteitsregels + correctieworkflow voor het CRM | Masterdata-governance voor het hele bedrijf |
| Sterschema + KPI-views in SQL, ook op SQL Server | Realtime rapportering |
| Power BI-model (TMDL) met measures en beveiliging per verkoper | Een gepubliceerd .pbix-rapport (zie beperkingen) |
| Excel-reconciliatie sales ↔ finance | De boekhouding zelf |
| Drie IT-supporttickets + runbook | Hardwarebeheer van het hele bedrijf |

## Aannames

- Alle bedrijfs-, klant- en persoonsnamen zijn verzonnen. Personeelsnamen zijn een voornaam + initiaal; e-mailadressen eindigen op `.example`.
- De data is gegenereerd door [`generator/generate_sources.py`](../../generator/generate_sources.py) met een vaste seed: elke run geeft exact dezelfde cijfers.
- De fouten in de data zijn **bewust geplant** (zie [02 · Bronnen](../02-sources/README.md)). De pipeline leest de lijst met geplante fouten niet; alleen de tests gebruiken ze om te bewijzen dat de regels ze vinden.
- De menselijke beoordeling van de duplicaten is gesimuleerd door [`generator/simulate_review.py`](../../generator/simulate_review.py). In de demo kan je zelf beslissen.

## Data en bronnen

| Bron | Herkomst |
|---|---|
| ERP- en CRM-extracten, targets, finance-cijfers | zelf gegenereerd, fictief |
| Btw-controle BE (mod 97) en FR (sleutel op SIREN) | publieke regels voor de opbouw van het ondernemingsnummer en het Franse btw-nummer |
| Sterschema-aanpak | [Microsoft Learn — Understand star schema and the importance for Power BI](https://learn.microsoft.com/power-bi/guidance/star-schema) |

## Beperkingen

- **Power BI:** het semantisch model staat als code (TMDL) in de repo en wordt in CI ingelezen met Microsofts eigen TMDL-serializer. De DAX-measures zijn **niet** uitgevoerd in een Power BI-engine; de SQL-tegenhanger van elke measure is wel getest. Er is geen gepubliceerd rapport. De webdemo toont dezelfde vier rapportpagina's met dezelfde cijfers.
- **SQL Server:** de T-SQL-versie van het model draait in CI op een SQL Server 2022-container en moet dezelfde KPI's geven als SQLite. Dat is geen productieomgeving.
- **Resultaten** zoals "CRM-gezondheid van <!--m:dq_health_before|pct-->75,0 %<!--/m--> naar <!--m:dq_health_after|pct-->98,0 %<!--/m-->" zijn gesimuleerd op gegenereerde data — geen resultaat bij een echte werkgever.
