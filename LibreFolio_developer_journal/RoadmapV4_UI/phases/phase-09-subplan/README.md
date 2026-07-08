# Phase 9 — Sub-Plans Index (Milestone 1 & 2, archiviate)

Questa directory raccoglie i sotto-piani di implementazione **completati** per la **Phase 9 (Dashboard)** —
Milestone 1 (backend/API portfolio) e Milestone 2 (Dashboard Home, Portfolio Engine, Positions/Performance
panel). Archiviata il 2026-07-07, dopo verifica esaustiva di tutti gli item contro il codice attuale.

> **Milestone 3 ancora attiva**: il redesign UI Broker v2 (post Portfolio Engine unificato) è tuttora in corso
> e resta in [`../../phase-09-subplan/README.md`](../../phase-09-subplan/README.md) (fuori da questo archivio).

## Piano principale
→ [`../phase-09-dashboard.md`](../phase-09-dashboard.md) — Macro plan ufficiale di Phase 9.

## Documenti trasversali M1/M2 (root)

| File | Descrizione | Status |
|------|-------------|:------:|
| [`implementation_roadmap.md`](./implementation_roadmap.md) | Roadmap di implementazione M1/M2 | ✅ |
| [`plan_financial_algorithms.md`](./plan_financial_algorithms.md) | Algoritmi finanziari (TWRR, MWRR/XIRR, Simple ROI, WAC) | ✅ |
| [`plan_ui_dashboard.md`](./plan_ui_dashboard.md) | Design UI Dashboard Home (wireframe ASCII) | ✅ |
| [`report_dashboard_bottom_widgets_analysis.md`](./report_dashboard_bottom_widgets_analysis.md) | Analisi tecnica widget inferiori dashboard (26/06) — corretta dal report seguente | ✅ (superato) |
| [`report_asset_level_contribution_gap_analysis.md`](./report_asset_level_contribution_gap_analysis.md) | Gap analysis contribution per-asset (26/06) — corregge il report precedente | ✅ |
| [`plan-gallery-update.prompt.md`](./plan-gallery-update.prompt.md) | Aggiornamento Gallery Screenshot (Phase 07+08+09) | ✅ |

## Milestone 1 — Fondamenta Backend e API di Portafoglio

| File | Descrizione | Status |
|------|-------------|:------:|
| [`Milestone_1/implementation_plan.md`](./Milestone_1/implementation_plan.md) | M1: Piano di implementazione | ✅ |
| [`Milestone_1/detail_plan_execution.md`](./Milestone_1/detail_plan_execution.md) | M1: Dettaglio esecuzione | ✅ |
| [`Milestone_1/missing_tests_gap_analysis.md`](./Milestone_1/missing_tests_gap_analysis.md) | M1: Gap analysis test mancanti | ✅ |

## Milestone 2 — Dashboard Home, Portfolio Engine, Positions/Performance

| File | Descrizione | Status |
|------|-------------|:------:|
| [`Milestone_2/implementation-analysis-M2.md`](./Milestone_2/implementation-analysis-M2.md) | M2: Analisi implementazione | ✅ (`get_asset_history()` ROI/unit-mix deferred) |
| [`Milestone_2/analysis-portfolio-chart-bugs.prompt.md`](./Milestone_2/analysis-portfolio-chart-bugs.prompt.md) | Analisi bug grafici portfolio | ✅ |
| [`Milestone_2/mwrr-numerical-stability-analysis.md`](./Milestone_2/mwrr-numerical-stability-analysis.md) | Analisi stabilità numerica MWRR | ✅ (cap risultato e Newton-vs-Brent: scelte progettuali prese diversamente, non bug) |
| [`Milestone_2/plan_fix_portfolio_history.md`](./Milestone_2/plan_fix_portfolio_history.md) | Piano fix `/portfolio/history` | ✅ |
| [`Milestone_2/plan-phase09Step2-DashboardAndPatch.prompt.md`](./Milestone_2/plan-phase09Step2-DashboardAndPatch.prompt.md) | Round 2 patch: Dashboard + fix | ✅ |
| [`Milestone_2/plan-phase09Step2Round2-DailyTargetState.prompt.md`](./Milestone_2/plan-phase09Step2Round2-DailyTargetState.prompt.md) | Round 2.2: Daily Target State | ✅ |
| [`Milestone_2/plan-phase09Step2Round3-PortfolioRenameCurrencySeed.prompt.md`](./Milestone_2/plan-phase09Step2Round3-PortfolioRenameCurrencySeed.prompt.md) | Round 2.3: Rename + Currency Seed | ✅ |
| [`Milestone_2/plan-phase09Step2Round4-CashMtMTransparency.prompt.md`](./Milestone_2/plan-phase09Step2Round4-CashMtMTransparency.prompt.md) | Round 2.4: Cash Mark-to-Market Transparency | ✅ |

### Milestone_2/lowDashboard/ — Refactor Holdings/Performance (Your Positions & Recent Transactions)

| File | Descrizione | Status |
|------|-------------|:------:|
| [`Milestone_2/lowDashboard/Low-dashboard_gap_analysis.md`](./Milestone_2/lowDashboard/Low-dashboard_gap_analysis.md) | Gap analysis preliminare | ✅ |
| [`Milestone_2/lowDashboard/Low-dashboard_refactor.md`](./Milestone_2/lowDashboard/Low-dashboard_refactor.md) | Design del refactor | ✅ |
| [`Milestone_2/lowDashboard/Low-dashboard_implementation_notes.md`](./Milestone_2/lowDashboard/Low-dashboard_implementation_notes.md) | Note implementazione (4 stage) | ✅ — 2 limiti residui: `test_transaction_implied.py` (6 test, bug pre-esistente non correlato), resize colonne DataTable non funzionante |
| [`Milestone_2/lowDashboard/dashboard-formulas-report.md`](./Milestone_2/lowDashboard/dashboard-formulas-report.md) | Report formule dashboard | ✅ |

### Milestone_2/portfolio_engine/ — Portfolio Calculation Engine

| File | Descrizione | Status |
|------|-------------|:------:|
| [`Milestone_2/portfolio_engine/gpt5.5_high_level_design.md`](./Milestone_2/portfolio_engine/gpt5.5_high_level_design.md) | Design alto livello v1 | ✅ |
| [`Milestone_2/portfolio_engine/gpt5.5_high_level_design_v2.md`](./Milestone_2/portfolio_engine/gpt5.5_high_level_design_v2.md) | Design alto livello v2 (riferimento) | ✅ |
| [`Milestone_2/portfolio_engine/gpt5.5_bannerSystem_high_level_design.md`](./Milestone_2/portfolio_engine/gpt5.5_bannerSystem_high_level_design.md) | Design sistema banner data-quality | ✅ |
| [`Milestone_2/portfolio_engine/ARCH_ANALYSIS_PORTFOLIO_ENGINE.md`](./Milestone_2/portfolio_engine/ARCH_ANALYSIS_PORTFOLIO_ENGINE.md) | Analisi architetturale (input per design) | ✅ |
| [`Milestone_2/portfolio_engine/code_agent_low_level_implementation_plan.md`](./Milestone_2/portfolio_engine/code_agent_low_level_implementation_plan.md) | Piano implementativo low-level | ✅ |
| [`Milestone_2/portfolio_engine/code_agent_coherence_review.md`](./Milestone_2/portfolio_engine/code_agent_coherence_review.md) | Review di coerenza piano/codice | ✅ |
| [`Milestone_2/portfolio_engine/code_agent_banner_and_valuation_analysis.md`](./Milestone_2/portfolio_engine/code_agent_banner_and_valuation_analysis.md) | Analisi banner e valutazione | ✅ |
| [`Milestone_2/portfolio_engine/code_agent_unified_banner_and_frontend_store_analysis.md`](./Milestone_2/portfolio_engine/code_agent_unified_banner_and_frontend_store_analysis.md) | Analisi banner unificato + store frontend | ✅ |
| [`Milestone_2/portfolio_engine/implementation_status_report.md`](./Milestone_2/portfolio_engine/implementation_status_report.md) | Status report vs design v2 (19/06) | ✅ — vedi nota sotto |
| [`Milestone_2/portfolio_engine/STATUS_REPORT_M2.md`](./Milestone_2/portfolio_engine/STATUS_REPORT_M2.md) | Status report full-picture per AI analytics (19/06) | ✅ — superato da lavoro successivo |
| [`Milestone_2/portfolio_engine/ARCHITECTURE_CURRENT_STATE.md`](./Milestone_2/portfolio_engine/ARCHITECTURE_CURRENT_STATE.md) | Stato architettura post Phase B (30/06) | ✅ — vedi nota sotto |
| [`Milestone_2/portfolio_engine/portfolio_engine_architecture_v2.md`](./Milestone_2/portfolio_engine/portfolio_engine_architecture_v2.md) | Architettura engine v2 | ✅ |
| [`Milestone_2/portfolio_engine/mwrr_analysis_report.md`](./Milestone_2/portfolio_engine/mwrr_analysis_report.md) | Analisi bug MWRR (double-counting) | ✅ risolto con formula diversa |
| [`Milestone_2/portfolio_engine/mwrr_boundary_anomaly_report.md`](./Milestone_2/portfolio_engine/mwrr_boundary_anomaly_report.md) | Anomalia boundary MWRR (warm-start) | ✅ risolto (guardia dedicata + test) |
| [`Milestone_2/portfolio_engine/pnl_breakdown_analysis.md`](./Milestone_2/portfolio_engine/pnl_breakdown_analysis.md) | Analisi breakdown P&L | ✅ |
| [`Milestone_2/portfolio_engine/external_cash_bridge_edge_case_report.md`](./Milestone_2/portfolio_engine/external_cash_bridge_edge_case_report.md) | Edge case cash bridge esterno | ⚠️ edge case "prelievo anticipato/look-ahead" ancora aperto per design |

### Milestone_2/Ai_consultant_engine/ — AI Portfolio Export

| File | Descrizione | Status |
|------|-------------|:------:|
| [`Milestone_2/Ai_consultant_engine/high_level_project.md`](./Milestone_2/Ai_consultant_engine/high_level_project.md) | Design AI Export MVP | ✅ |
| [`Milestone_2/Ai_consultant_engine/report_ai_export_mvp.md`](./Milestone_2/Ai_consultant_engine/report_ai_export_mvp.md) | Report MVP con limitazioni intenzionali documentate | ✅ (asimmetrie by design, non bug) |

---

## Nota di verifica (2026-07-07)

Prima dell'archiviazione è stata condotta una verifica **esaustiva** (non a campione) di tutti gli item
elencati nei documenti sopra contro il codice attuale (`backend/app/services/portfolio_engine.py`,
`portfolio_service.py`, `backend/app/utils/financial/roi_utils.py`, componenti frontend dashboard). Risultato:

- La maggior parte degli item marcati "mancanti" in `implementation_status_report.md` (19/06) e
  `ARCHITECTURE_CURRENT_STATE.md` (30/06) sono stati **implementati da lavoro successivo** (es.
  `get_summary()` wiring al nuovo engine, `build_data_quality_report()`, GrowthChart ABS stacked area,
  AllocationPanel toggle Now/History, DataQualityBanner unificato).
- Alcuni item (`internal_transfer_flow`/`scope_transfer_flow` diagnostici, sampling allocation history,
  WAC fallback in-transit, `get_asset_history()` ROI/unit-mix, edge case cash-bridge look-ahead) restano
  **genuinamente aperti**, a bassa priorità.
- Il cap sul risultato MWRR e la scelta Newton-vs-Brent, segnalati come "aperti" da un'analisi statica del
  codice, sono in realtà **scelte progettuali prese deliberatamente in modo diverso** dal design originale
  (non bug/lavoro mancante).
- 2 limiti residui noti nel refactor `lowDashboard` (dashboard "Your Positions"): test `test_transaction_implied.py`
  (bug pre-esistente non correlato) e resize colonne `DataTable.svelte` non funzionante.

Dettaglio completo della verifica: vedi il `plan.md` della sessione che ha condotto l'archiviazione
(riferimento storico, non incluso in questo archivio).
