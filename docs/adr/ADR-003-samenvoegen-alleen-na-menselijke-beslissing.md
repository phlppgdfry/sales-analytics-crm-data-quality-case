# ADR-003 — Nooit automatisch samenvoegen of verwijderen

**Context.** De duplicaatdetectie vindt <!--m:dup_pairs_before|int-->165<!--/m--> paren. Een deel daarvan is géén duplicaat: een zorggroep met drie campussen deelt één btw-nummer en lijkt in naam bijna identiek, maar heeft drie leveradressen en aparte facturatie. Sommige van die paren scoren zelfs in de band "waarschijnlijk".

**Opties.**
1. Alles boven score 75 automatisch samenvoegen — snel, maar voegt multi-site klanten samen; hun omzet en contactpersonen raken vermengd en dat is moeilijk terug te draaien.
2. Alles manueel, zonder score — juist, maar niemand gaat door 165 paren zonder hulp.
3. Score + bewijs tonen, de accounteigenaar beslist met één klik; "geen duplicaat" wordt onthouden.

**Beslissing.** Optie 3. Samenvoegen markeert het verliezende record met `merged_into` en verhuist zijn opportunities; er wordt niets verwijderd. Elke wijziging staat in `crm_change_log`.

**Gevolgen.** Twee reviewsessies van ± 1 uur. Resultaat: <!--m:review_samenvoegen|int-->145<!--/m--> keer samenvoegen, <!--m:review_geen_duplicaat|int-->15<!--/m--> keer "geen duplicaat", <!--m:review_later|int-->5<!--/m--> keer "later". De regelgebaseerde fixes (koppeling met ERP, eigenaar overzetten) lopen als batch met één goedkeuring van de sales manager — eenduidig, maar met gevolgen voor commissies, dus ook niet stil.
