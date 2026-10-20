# ADR-004 — Eén omzetdefinitie: die van finance

**Context.** Het Excel-rapport van sales telde voor Q3 <!--m:recon_gap|eur0-->€ 397.834<!--/m--> meer dan finance ([reconciliatie](../07-excel/README.md)). Elke vergadering begon met de vraag welk cijfer juist was.

**Opties.**
1. Sales houdt een eigen "commerciële omzet" (bv. inclusief personeelsshop, vóór creditnota's).
2. Eén definitie, eigendom van finance: facturen min creditnota's, excl. btw, excl. interne klant (grootboek 700000).

**Beslissing.** Optie 2. Finance is eigenaar van de definitie, de sales manager van het gebruik. Afwijkende vragen ("hoeveel creditnota's had Lotte?") krijgen een eigen measure met een eigen naam, nooit een tweede "omzet".

**Gevolgen.** `[Netto-omzet]` is de enige omzet-measure waar andere op verder bouwen. Een test bewaakt dat de netto-omzet per maand in het datawarehouse gelijk is aan finance.
