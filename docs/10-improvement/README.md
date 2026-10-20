# 10 · Verbeteren — kleine projecten met grote hefboom

> Wat is dit: de verbetervoorstellen die uit de analyse kwamen, geprioriteerd. Voor wie: sales manager en IT-verantwoordelijke. Waarom: de vacature vraagt om "proactief mee te denken over kleine verbeterprojecten". Opkuisen zonder de oorzaak weg te nemen is volgende maand opnieuw beginnen.
> Vorige → [09 · Testen](../09-testing/README.md) · Terug naar het begin → [00 · Context](../00-context/README.md)

Inspanning en baten zijn **illustratieve inschattingen**, geen gemeten resultaten.

| ID | Voorstel | Probleem dat het wegneemt | Inspanning | Baat | Eigenaar | Prioriteit |
|---|---|---|---|---|---|---|
| V-01 | Wekelijks Excel-rapport vervangen door het Power BI-rapport | handwerk elke maandag; cijfer verschilde <!--m:recon_gap_pct|pct-->6,7 %<!--/m--> van finance | 3 dagen (rapport bestaat) + 1 uur uitleg | ± 1 uur per week voor de sales manager; één cijfer in elke vergadering | analist | **1** |
| V-02 | Btw-nummer verplicht en gevalideerd bij aanmaak klantaccount | foute en ontbrekende btw (CRM-02/03); zwakke duplicaatdetectie | ½ dag CRM-configuratie | nieuwe fouten bij de bron gestopt | analist + CRM-beheer | **1** |
| V-03 | Duplicaatcontrole bij invoer ("bestaat dit account al?") | nieuwe dubbels na elke beurs of webformulier | 1–2 dagen, afhankelijk van het CRM | wachtrij blijft klein | analist | 2 |
| V-04 | On- en offboarding van verkopers als checklist ([T3](../08-it-support/README.md#t3--bram-begint-maandag-als-accountmanager-antwerpen)) | accounts op naam van vertrokken verkopers (CRM-05), leeg rapport voor starters (T2) | 2 uur | geen "erfenis" van <!--m:rule_crm05_before|int-->151<!--/m--> accounts meer | sales manager + HR | **1** |
| V-05 | Controle op de exportjob: één run per dag, aantal rijen vergeleken met het ERP | de dubbele dag in Q3 | ½ dag | geen stille dubbeltelling | IT | 3 (vervalt met V-01) |
| V-06 | Pipeline-opkuis met elke accountmanager (30 min per persoon) | <!--m:rule_opp02_before|int-->280<!--/m--> open deals met verlopen afsluitdatum, <!--m:stale_opportunities|int-->80<!--/m--> zonder update | 1 dag verspreid | prognose op basis van de pipeline wordt bruikbaar | sales manager | 2 |
| V-07 | Facturen zonder verkoper blokkeren in het ERP | <!--m:rule_erp01_before|int-->1.431<!--/m--> lijnen moesten afgeleid worden | afhankelijk van ERP | minder afleiding in het model | finance | 3 |

## Hoe ik prioriteerde

1. **Wat stopt nieuwe fouten?** (V-02, V-04) gaat vóór wat oude fouten opkuist.
2. **Wat kost weinig en gebruikt wat er al is?** (V-01: het rapport bestaat al, alleen de gewoonte moet mee.)
3. **Wat hangt van anderen af?** (V-07 vraagt finance en het ERP-team; nuttig, maar niet in de eerste maand.)

## Adoptie van V-01: het Excel-bestand loslaten

De sales manager werkt al jaren met het bestand en vertrouwt het. Niet afpakken, wel naast elkaar leggen:
1. Vier weken lang beide versies; elke maandag vergelijk ik de twee samen met de manager (de [brug](../07-excel/README.md) verklaart elk verschil).
2. Wat het Excel-bestand kon en het rapport niet, komt op een lijst en wordt gebouwd of bewust geschrapt.
3. Pas als de manager zelf zegt "ik open het Excel niet meer", wordt het gearchiveerd.
