# Phase 0 — Archived Sub-Plans Index

> Completed work-streams of Release 2, archived here once done. Active work stays in
> `Phase_0/`: `02_riskfolioIntegration` (paused, beta). Archiviata il 03/09: `06_betaTestingReportAndFixing` (beta feedback consolidation, chiusa).
> `Phase_0/04_webSearchEngine/` was fully archived on 2026-09-02 (ddgs suffices; SearXNG dropped). When a phase completes entirely, its folder moves under
> `phases/Phase_N/`.

| Archive | What it was | Outcome |
|---|---|---|
| `01_signalMigration/` | Backend Signals platform migration + AI Export V1 (incl. `02_aiExport/` subdir) | ✅ Shipped in 1.1.0 |
| `03_brokerImportRecovery/` | BRIM recovery: Crédit Agricole trades, import flow restructure | ✅ Shipped (Fase A+B) |
| `04_webSearchEngine/` | Web link-finder transport: raw DDG scraper → `ddgs` metasearch (+ SearXNG plan, not needed) | ✅ ddgs Steps 1–6; SearXNG dropped |
| `05_cleanAudit/` | Systematic dead-code/optimization audit (17 reports) + stabilization | ✅ Suite stabilized |
| `07_coverageAndConsolidationCampaign/` | Test runner parallelization, JS/Svelte coverage, 16 defects closed | ✅ Suite 15/15 green, 78% lines |
| `06_betaTestingReportAndFixing/` | Beta feedback consolidation (F1–F17, piani P1–P8) | ✅ Tutti i task eseguiti — archiviata il 03/09 (07/09: i residui P8 erano una scelta deliberata — le scritture restano seriali per la validità dei test; voce TODO rimossa) |
| `08_newCleanAndDocumentation_audit/` | Riverifica integrale dell'audit di agosto + esecuzione backlog (P0→P3), ondata docs/gallery/traduzioni, report 50 (gap v1.0.1→HEAD) | ✅ P0/P1/P2/P3 tutti chiusi e validati a zero; **residuo**: 8 task strutturali P4 → `Phase_0/09_feedbackJobs/` — archiviata il 07/09 |

**Not archived (still active / paused):**
- `../Phase_0/02_riskfolioIntegration/` — Risk Analysis subsystem, paused in beta per user decision.
- `../Phase_0/09_feedbackJobs/` — backlog strutturale P4 ereditato dall'audit 08 (attivo: si pesca da lì al prossimo round).
