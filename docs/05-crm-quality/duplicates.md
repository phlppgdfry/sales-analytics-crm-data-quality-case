# Duplicaten — vinden, scoren, beslissen, samenvoegen

> Wat is dit: de methode achter de duplicatenwachtrij. Voor wie: de accounteigenaars die beslissen, en wie de drempels later wil bijstellen. Waarom: een te gretige merge maakt van twee klanten één klant, en dat is erger dan een dubbel record.
> Terug → [05 · CRM-kwaliteit](README.md) · Code: [`etl/duplicates.py`](../../etl/duplicates.py)

## 1. Namen vergelijkbaar maken

`"Schoonmaakbedrijf Declercq NV"`, `"SCHOONMAAKBEDRIJF DECLERCQ"` en `"Schoonmaakbedrijf Declercq bv"` worden allemaal `schoonmaakbedrijf declercq`: kleine letters, accenten weg, leestekens weg, rechtsvorm (nv, bv, srl, sa, vzw, asbl, …) weg, `&` → `en`.

## 2. Kandidaten zoeken (blocking, in SQL)

Elk account met elk ander vergelijken zijn ± 1,4 miljoen paren. Daarom eerst een goedkope voorselectie: alleen paren die
- hetzelfde btw-nummer hebben, **of**
- dezelfde postcode en dezelfde eerste of laatste 5 letters van de naam, **of**
- dezelfde gemeente en dezelfde eerste 8 letters.

## 3. Scoren

| Signaal | Punten | Waarom |
|---|---:|---|
| Zelfde btw-nummer | +45 | sterkste signaal, maar niet genoeg: één vennootschap kan meerdere leverplaatsen hebben |
| Allebei een **geldig** maar verschillend btw-nummer | −40 | twee rechtspersonen; bijna zeker geen duplicaat |
| Naam ≥ 95 % / ≥ 88 % / ≥ 80 % gelijk | +35 / +28 / +18 | typfouten en hoofdletters vangen zonder alles te laten matchen |
| Zelfde postcode (of anders: zelfde gemeente) | +15 (+5) | |
| Zelfde telefoon of e-maildomein | +5 | zwak signaal, alleen als extra |

**≥ 75 = waarschijnlijk** (één klik bevestigen) · **40–74 = beoordelen** · **< 40 = niet in de wachtrij**.

In deze run: <!--m:dup_pairs_likely_before|int-->109<!--/m--> paren "waarschijnlijk", <!--m:dup_pairs_review_before|int-->56<!--/m--> "beoordelen". De tests meten dat minstens 95 % van de geplante duplicaten in de wachtrij komt ([`tests/test_duplicates.py`](../../tests/test_duplicates.py)).

## 4. Een mens beslist

| Beslissing | Aantal | Voorbeeld |
|---|---:|---|
| samenvoegen | <!--m:review_samenvoegen|int-->145<!--/m--> | `Woonzorgcentrum De Kapel VZW` en `Woonzorgcentrum De Kapel Vzw` — zelfde btw, zelfde postcode, zelfde e-maildomein (score 100) |
| geen duplicaat | <!--m:review_geen_duplicaat|int-->15<!--/m--> | `Zorggroep Ter Wilgen – campus Noord` en `– campus Zuid` — één vennootschap, twee leverplaatsen, aparte facturatie (score 78!) |
| later | <!--m:review_later|int-->5<!--/m--> | `Vermeulen Metaal` in Brugge met postcode 8000 en een tweede record met 8790, zonder btw (score 40): de accounteigenaar vraagt het eerst na |

Het algoritme zet sommige multi-site paren zelfs in "waarschijnlijk" (zelfde btw, naam bijna gelijk, zelfde e-maildomein). Precies daarom voegt niets automatisch samen ([ADR-003](../adr/ADR-003-samenvoegen-alleen-na-menselijke-beslissing.md)). Een "geen duplicaat"-beslissing wordt onthouden, zodat het paar volgende week niet terugkomt.

## 5. Samenvoegen volgens overlevingsregels

1. **Wie overleeft:** het account dat aan het ERP gekoppeld is; anders het oudste.
2. **Velden:** lege velden van de overlevende worden aangevuld met die van het andere record (btw, e-mail, telefoon). Gevulde velden worden nooit overschreven — <!--m:changes_merge_fill|int-->7<!--/m--> keer aangevuld.
3. **Opportunities** verhuizen naar de overlevende; het andere record krijgt `merged_into` en blijft bestaan voor het auditspoor.
4. **Log:** elke merge en elke aanvulling staat in `crm_change_log` met reden en beslisser.

Een test bewaakt dat geen enkele multi-site klant samengevoegd werd en dat geen ERP-gekoppeld record ooit het verliezende record is.
