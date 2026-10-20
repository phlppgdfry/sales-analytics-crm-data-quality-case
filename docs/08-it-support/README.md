# 08 · IT-support — drie tickets uit de week van een data analyst

> Wat is dit: drie uitgewerkte supportvragen van collega's, met diagnose, oplossing, communicatie en preventie. Voor wie: wie de analist vervangt tijdens verlof, en de sales manager. Waarom: in deze rol ben je ook de eerste hulp voor bedrijfssoftware en hardware — en de beste tickets eindigen met "dit gebeurt niet meer".
> Vorige → [07 · Excel](../07-excel/README.md) · Volgende → [09 · Testen](../09-testing/README.md)

Alle namen zijn fictief. Prioriteit: **P1** = meerdere mensen kunnen niet werken · **P2** = één persoon of één rapport geblokkeerd · **P3** = hinderlijk, er is een omweg.

---

## T1 — "Het salesrapport toont cijfers van gisteren"

| | |
|---|---|
| Melder | Sales manager, dinsdag 08:10, via Teams |
| Prioriteit | P2 — het maandgesprek met twee verkopers begint om 10:00 |
| Systeem | Power BI-dataset *Vennaert Sales*, gateway, SQL Server |

**Diagnose (in deze volgorde, want de goedkoopste controle eerst):**
1. Peildatum op het rapport: "Gegevens tot en met maandag". → de refresh van 06:30 is niet gelukt, het rapport zelf werkt.
2. Power BI-service → dataset → *Vernieuwingsgeschiedenis*: mislukt om 06:30, fout *"The credentials provided for the SQL source are invalid"*.
3. Is het de bron of de verbinding? Zelfde query in SQL Server Management Studio met het serviceaccount: aanmelden mislukt. → niet de data, wel het account.
4. IT-kalender: het wachtwoord van het serviceaccount `svc-pbi-dwh` werd maandagavond geroteerd volgens het beleid (elke 90 dagen). De gateway gebruikte nog het oude.

**Oplossing:** nieuwe referenties ingevuld in de gatewaygegevensbron (met de IT-beheerder die het wachtwoord in de kluis beheert) → handmatige refresh → 08:42 geslaagd, peildatum klopt.

**Communicatie (08:15 en 08:45):**
> "Het rapport staat nog op gisteren omdat de automatische verversing vannacht mislukte (wachtwoord van de koppeling verlopen). Ik verwacht het voor 9u op te lossen; ik laat het je weten." — "Opgelost, de cijfers staan op vandaag. Het gesprek van 10u kan met de juiste cijfers."

**Preventie:** rotatie van `svc-pbi-dwh` staat nu in dezelfde change als het bijwerken van de gateway; refreshfout stuurt een mail naar de analist én de sales manager; de peildatum blijft op elke pagina staan, zodat niemand op oude cijfers beslist zonder het te weten.

---

## T2 — "Je ne vois aucun client dans le rapport"

| | |
|---|---|
| Melder | Camille F., nieuwe accountmanager Hainaut (sinds juni), via mail in het Frans |
| Prioriteit | P2 — één persoon, geen omweg behalve de manager vragen |
| Systeem | Power BI-app, beveiliging op rijniveau (rol `Accountmanager`), ERP-verkoperstabel |

**Diagnose:**
1. Ziet ze het rapport maar is het leeg, of ziet ze niets? → de pagina's laden, alle visuals zijn leeg. Toegang tot de app is dus in orde; het is de rijfilter.
2. *Beveiliging → Testen als rol* `Accountmanager` met haar account → leeg. Met het adres van een collega → gevuld. Het model werkt.
3. De rol filtert op `dim_rep[email] = USERPRINCIPALNAME()`. Haar rij in `dim_rep`: het e-mailadres in de ERP-verkoperstabel was haar oude adres uit de sollicitatieprocedure, niet haar bedrijfsaccount.

**Oplossing:** de bron verbeteren, niet het rapport: HR/administratie past het e-mailadres aan in de ERP-verkoperstabel; na de volgende ETL en refresh test ik opnieuw als rol → haar klanten in Hainaut verschijnen (vanaf 1 juni, de datum van de overdracht van Julie H.).

**Antwoord aan de melder (eenvoudig Frans, met de essentie eerst):**
> Bonjour Camille, merci pour votre message. Le problème est trouvé : votre adresse e-mail n'était pas correcte dans notre système. C'est corrigé. Demain matin, après la mise à jour de 6h30, vous verrez vos clients du Hainaut. Je vérifie avec vous à 9h. Bonne journée !

**Preventie:** de onboardingchecklist (T3) heeft nu de stap "e-mail in ERP-verkoperstabel = bedrijfsaccount"; een datakwaliteitscontrole meldt actieve verkopers zonder bedrijfsadres (`email NOT LIKE '%@vennaert.example'`).

---

## T3 — "Bram begint maandag als accountmanager Antwerpen"

| | |
|---|---|
| Melder | Sales manager, woensdag, via het ticketportaal |
| Prioriteit | P3 — gepland, maar met een harde datum |
| Systeem | laptop, Microsoft 365, CRM, Power BI, ERP |

Een starter is ook een datakwaliteitsmoment: wat hier misgaat, komt drie maanden later terug als "omzet bij de verkeerde verkoper". Daarom één checklist voor IT én voor de data.

| # | Stap | Wie | Klaar |
|---|---|---|---|
| 1 | Laptop klaarzetten: image, encryptie aan, updates, docking + scherm testen | IT-support | ☐ |
| 2 | Microsoft 365-account, MFA ingesteld bij overhandiging (samen met de gebruiker, niet vooraf) | IT-support | ☐ |
| 3 | Verkoper aanmaken in ERP-verkoperstabel: code `AM11`, regio, **bedrijfse-mail**, startdatum | administratie, gecontroleerd door de analist | ☐ |
| 4 | CRM-licentie + rol "accountmanager" | analist | ☐ |
| 5 | Klanten overzetten in ERP **met ingangsdatum** (1 april), niet met terugwerkende kracht | sales manager beslist, analist voert uit | ☐ |
| 6 | CRM-accounts van de vorige eigenaar overzetten naar de nieuwe ERP-eigenaar | analist (zelfde regel als CRM-05) | ☐ |
| 7 | Toevoegen aan Entra-groep `PBI-Sales-Accountmanagers` → test *bekijken als* met zijn account | analist | ☐ |
| 8 | Eerste dag: 30 minuten uitleg rapport + CRM-afspraken (btw verplicht, opportunities bijwerken) | analist | ☐ |

**Offboarding is dezelfde lijst in omgekeerde volgorde.** Dat Koen B. op 31 maart vertrok en zijn <!--m:rule_crm05_before|int-->151<!--/m--> CRM-accounts op zijn naam bleven staan (CRM-05), is precies wat stap 6 voorkomt.

---

## Runbook: rapport toont geen of oude cijfers

| Symptoom | Eerste controle | Waarschijnlijke oorzaak | Zie |
|---|---|---|---|
| Peildatum is gisteren | vernieuwingsgeschiedenis dataset | referenties gateway, SQL Server onbereikbaar, ETL nog bezig | T1 |
| Eén gebruiker ziet niets | *testen als rol* | e-mail in `dim_rep`, niet in de Entra-groep | T2 |
| Totaal klopt niet met finance | `v_reconciliation_2026q3` | creditnota's, interne klant, dubbele load | [07 · Excel](../07-excel/README.md) |
| Omzet "Niet toegewezen" stijgt | `[Omzet zonder verkoper (afgeleid)]` | facturen zonder verkoper ingegeven | [regel ERP-01](../05-crm-quality/rules.md) |
