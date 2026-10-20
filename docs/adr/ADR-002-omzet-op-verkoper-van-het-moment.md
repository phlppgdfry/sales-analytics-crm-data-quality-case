# ADR-002 — Omzet hoort bij de verkoper op de factuurdatum

**Context.** Koen B. (Antwerpen) vertrok op 31 maart 2026; zijn klanten gingen op 1 april naar Bram S. Camille F. nam op 1 juni Hainaut over van Julie H. Het ERP bewaart wie wanneer eigenaar was (`erp_customer_rep_history`). Het CRM kent alleen de huidige eigenaar — en die was voor Koens accounts nooit aangepast.

**Opties.**
1. Omzet op de huidige eigenaar van de klant: Bram "erft" heel 2025 en zijn target-realisatie is betekenisloos.
2. Omzet op de verkoper die op de factuurlijn staat; ontbrekende verkoper → eigenaar op factuurdatum uit de ERP-historiek.
3. Omzet op de CRM-eigenaar: dan staat er na april nog omzet op iemand die er niet meer werkt.

**Beslissing.** Optie 2. Een creditnota volgt de verkoper van de factuur die ze corrigeert (in de data: ze draagt dezelfde verkoperscode), ook als ze na zijn vertrek komt — <!--m:credit_lines_leaver_after_exit|int-->4<!--/m--> lijnen in deze data.

**Gevolgen.** `fact_sales.rep_key` per lijn; `dim_customer.current_rep_code` voor "wie heeft de klant nu". <!--m:lines_rep_derived|int-->1.431<!--/m--> lijnen zonder verkoper kregen er één via de historiek, met vlag `rep_derived = 1` en een eigen measure, zodat de afleiding zichtbaar blijft. De CRM-eigenaar wordt rechtgezet naar de ERP-eigenaar (regel CRM-05), niet omgekeerd: het ERP is de bron voor commissies.
