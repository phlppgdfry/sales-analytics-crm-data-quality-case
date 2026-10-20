# ADR-005 — SQLite voor de demo, SQL Server als doelplatform

**Context.** Het interne datawarehouse draait op SQL Server en Power BI leest daaruit. De case moet ook zonder server te bekijken zijn: een recruiter klikt op een link en moet het model kunnen bevragen.

**Opties.**
1. Alleen SQL Server (Docker) — realistisch, maar niemand start een container om een portfolio te bekijken.
2. Alleen SQLite — draait overal, ook in de browser, maar zegt niets over SQL Server.
3. SQLite voor pipeline en demo; dezelfde tabellen en views in T-SQL; CI laadt de data in SQL Server 2022 en controleert dat de KPI's identiek zijn.

**Beslissing.** Optie 3.

**Gevolgen.** Twee dialecten onderhouden ([`sql/`](../../sql/04_views.sql) en [`sql/tsql/`](../../sql/tsql/03_views.sql)); de verschillen zijn klein (`DATEADD` vs `date(…, '-12 months')`, `TOP` vs `LIMIT`) en staan bovenaan elk T-SQL-bestand. Het Power BI-model wijst naar SQL Server (`Sql.Database(Server, Database)`), niet naar SQLite.
