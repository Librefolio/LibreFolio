# 20_performanceCharts — grafici di performance (SP06 G3/G1c, SP07 G1a/G1b)

> Archiviata da `Phase_0/20_performanceCharts/` il 2026-10-09, con un `mv` normale, dal workstream I. Ogni piano è
> stato riallineato al codice di `dev_release2` a `3cceb4f90`; il registro della verifica è in fondo al piano del
> round 4.

Il workstream I ha consegnato quattro grafici:

- il rendimento mobile su N giorni di calendario nel dettaglio asset (G3);
- gli istogrammi Proventi del portafoglio, cioè dividendi e interessi riconciliati con il KPI (G1c);
- la modalità P&L di GrowthChart (G1a);
- le candele sintetiche del portafoglio, composte prima per giorno e poi per settimana o mese (G1b).

Poi sono venuti il round 4, con le correzioni della review d'uso del 22/09, e quattro lotti seguiti.

| File | Descrizione | Stato |
|---|---|---|
| `plan-phase00PerformanceCharts.prompt.md` | Piano madre: contratto §3, fasi I10–I90, debiti (§6.0.11), seguiti (§6.0.20) | ✅ Contratto integrato in fast-forward (`22b82e3fb`); I60 accettata il 2026-09-22 |
| `plan-phase00PerformanceChartsRound4-PostMergeReview.prompt.md` | Round 4 (I90): review d'uso post-merge del 22/09, S1–S12, D1–D28; registro della verifica d'archivio | ✅ Integrato il 2026-10-02 (`975a115ae`) |
| `plan-phase00PerformanceChartsBugfix-EventsOnCacheHit.prompt.md` | I marcatori degli eventi spariscono con «Tutti» e i prezzi in cache | ✅ Treno 9 (`0a2359573`), 2026-10-07 |
| `plan-phase00PerformanceChartsIncomeColorsAxisLabels.prompt.md` | Proventi: dividendo oro, etichette per periodo sull'asse X di Candele e Proventi | ✅ Treno 13 (`ffda8fc84`, poi `c001c0968`), 2026-10-08 |
| `plan-phase00PerformanceChartsBugfix-AssetEvents.prompt.md` | Eventi degli asset nell'editor: modifica sul posto per id, cambio di tipo, alias `value` → `amount` nell'import CSV | ✅ Treno 19 (`5423c334f`), 2026-10-08 |
| `plan-phase00PerformanceChartsBugfix-TooltipI18nEscape.prompt.md` | Voce 10: il gate HTML controlla che i cataloghi si leggano come testo | ✅ Treno 23 (`2c382824d`), 2026-10-09 |

**Residui tracciati** in `Phase_0/38_postReleaseBacklog/README.md`:

- I-01 e I-02: i debiti DBT-A e DBT-B di `timeSeriesAggregation.ts`;
- I-03: `%` premuto ma disabilitato in GrowthChart;
- I-04: la risoluzione delle candele in `PriceChartFull`;
- I-06: `npx` nel runner;
- I-07: 2 errori di `tsc` negli E2E;
- I-08: il debito di traduzione MkDocs;
- da I-09 a I-12: i limiti residui degli eventi degli asset.

Un debito ha una casa diversa: DBT-D, la conversione dei test specchio, sta in P4-9
(`Phase_0/09_feedbackJobs/00_backlog_strutturale_P4.md`). I suoi 12 rossi sono chiusi da `2e4c8589f` (2026-09-28).
