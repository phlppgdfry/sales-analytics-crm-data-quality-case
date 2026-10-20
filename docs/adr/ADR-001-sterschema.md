# ADR-001 — Sterschema in plaats van één brede tabel

**Context.** Het oude Excel-rapport is één brede tabel: elke exportrij met klant-, artikel- en verkopersinfo erbij. In Power BI geeft dat trage visuals, dubbele tellingen bij combinaties (opportunities × facturen) en measures die per visual anders rekenen.

**Opties.**
1. Eén brede tabel (zoals het Excel) — snel gemaakt, moeilijk juist te houden.
2. Sterschema: smalle feitentabellen (`fact_sales`, `fact_opportunity`, `fact_target`) met dimensies (`dim_date`, `dim_customer`, `dim_product`, `dim_rep`).
3. Volledig genormaliseerd model zoals in het ERP — juist, maar onbruikbaar voor rapportgebruikers.

**Beslissing.** Optie 2, volgens de [Power BI-richtlijn van Microsoft](https://learn.microsoft.com/power-bi/guidance/star-schema).

**Gevolgen.** Filters lopen van dimensie naar feit; targets (per maand) en omzet (per dag) kunnen samen in één visual via de gedeelde dimensies. Wie een nieuwe vraag heeft, kijkt eerst naar de korrel: past ze in een bestaande feitentabel, of is een nieuwe nodig?
