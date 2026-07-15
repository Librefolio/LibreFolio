# Phase 9 — Sub-Plans Index (Milestone 1, 2 & 3 — archiviate)

Questa directory raccoglie i sotto-piani di implementazione **completati** per la **Phase 9 (Dashboard &
Broker)** — Milestone 1 (backend/API portfolio), Milestone 2 (Dashboard Home, Portfolio Engine,
Positions/Performance panel) e Milestone 3 (redesign UI Broker v2, post Portfolio Engine unificato).
M1/M2 archiviate il 2026-07-07 dopo verifica esaustiva di tutti gli item contro il codice attuale; M3
archiviata il 2026-07-15 (tutti i sotto-piani ✅, vedi nota di archiviazione in fondo).

## Piano principale
→ [`../phase-09-dashboard.md`](../phase-09-dashboard.md) — Macro plan ufficiale di Phase 9.

## Documenti trasversali M1/M2/M3 (root)

| File | Descrizione | Status |
|------|-------------|:------:|
| [`implementation_plan.md`](./implementation_plan.md) | Piano creativo di riprogettazione Dashboard & Broker (copre sia M1/M2 sia M3 — riferimento condiviso) | ✅ |
| [`implementation_roadmap.md`](./implementation_roadmap.md) | Roadmap di implementazione M1/M2 | ✅ |
| [`plan_financial_algorithms.md`](./plan_financial_algorithms.md) | Algoritmi finanziari (TWRR, MWRR/XIRR, Simple ROI, WAC) | ✅ |
| [`plan_ui_dashboard.md`](./plan_ui_dashboard.md) | Design UI Dashboard Home (wireframe ASCII) | ✅ |
| [`plan_ui_broker_holdings.md`](./plan_ui_broker_holdings.md) | UI Broker Holdings — disegno originale, **superato da** [`Milestone_3/plan_ui_broker_holdings.md`](./Milestone_3/plan_ui_broker_holdings.md) | ✅ (superato) |
| [`plan_ui_broker_overview.md`](./plan_ui_broker_overview.md) | UI Broker Overview — disegno originale, **superato da** [`Milestone_3/plan_ui_broker_overview.md`](./Milestone_3/plan_ui_broker_overview.md) | ✅ (superato) |
| [`plan_ui_broker_transactions.md`](./plan_ui_broker_transactions.md) | UI Broker Transactions — disegno originale, **superato da** [`Milestone_3/plan_ui_broker_transactions.md`](./Milestone_3/plan_ui_broker_transactions.md) | ✅ (superato) |
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

## Milestone 3 — Redesign UI Broker v2 (post Portfolio Engine unificato)

Redesign delle pagine Broker (lista globale + dettaglio a tab), aggiornato dopo il lavoro su Portfolio Engine
e Dashboard Home (Milestone 1/2). I 3 piani originali sotto "trasversali" (pre Portfolio Engine unificato)
sono superati dalle versioni v2 in [`Milestone_3/`](./Milestone_3/README.md). Indice completo, gap analysis e
studi trasversali: vedi [`Milestone_3/README.md`](./Milestone_3/README.md).

| File | Descrizione | Status |
|------|-------------|:------:|
| [`Milestone_3/README.md`](./Milestone_3/README.md) | Indice M3: gap analysis, studi trasversali, guide | ✅ |
| [`Milestone_3/plan_ui_broker_overview.md`](./Milestone_3/plan_ui_broker_overview.md) | Fase 1 — Lista Globale Brokers (+ Broker Discovery) e shell a tab del Broker Detail + Tab Panoramica | ✅ disegno · ✅ [impl](./Milestone_3/impl_plan_broker_overview.md) |
| [`Milestone_3/plan_ui_broker_holdings.md`](./Milestone_3/plan_ui_broker_holdings.md) | Fase 2 — Tab Posizioni (riuso `PositionsPanel`) + Pannello Inline Lotti FIFO multi-broker | ✅ disegno raffinato · ✅ [impl](./Milestone_3/impl_plan_broker_holdings.md) · ✅ implementato (2026-07-10) · ✅ evoluto multi-broker (2026-07-11, fleet) |
| [`Milestone_3/plan_ui_broker_transactions.md`](./Milestone_3/plan_ui_broker_transactions.md) | Fase 3 — Tab Transazioni (riuso `<TransactionsTable>`) + File Importati | ✅ disegno · ✅ implementato (recap in-doc, chiuso 2026-07-08) |
| [`Milestone_3/GUIDA-TOOLBAR-RESPONSIVE-v2.md`](./Milestone_3/GUIDA-TOOLBAR-RESPONSIVE-v2.md) | Guida taratura soglie responsive (`PageToolbar`/`DateRangePicker`) | ✅ |

### Milestone_3/chart_resolution/ — Risoluzione dinamica grafici (semantic zoom)

| File | Descrizione | Status |
|------|-------------|:------:|
| [`Milestone_3/chart_resolution/study_chart_dynamic_resolution.md`](./Milestone_3/chart_resolution/study_chart_dynamic_resolution.md) | Studio di fattibilità + raffinamento architetturale (semantic zoom daily→weekly→monthly) | ✅ |
| [`Milestone_3/chart_resolution/impl_plan_chart_resolution_00_foundation.md`](./Milestone_3/chart_resolution/impl_plan_chart_resolution_00_foundation.md) | `timeSeriesAggregation.ts` — bucketing, aggregazione, densità/isteresi, debounce (documento fondativo) | ✅ implementato |
| [`Milestone_3/chart_resolution/impl_plan_chart_resolution_01_price_candlestick.md`](./Milestone_3/chart_resolution/impl_plan_chart_resolution_01_price_candlestick.md) | `PriceChartFull` + `CandlestickChart` | ✅ implementato |
| [`Milestone_3/chart_resolution/impl_plan_chart_resolution_02_growth_chart.md`](./Milestone_3/chart_resolution/impl_plan_chart_resolution_02_growth_chart.md) | `GrowthChart` (5 serie EUR-mode + 3 serie %-mode) | ✅ implementato |
| [`Milestone_3/chart_resolution/impl_plan_chart_resolution_03_allocation_history.md`](./Milestone_3/chart_resolution/impl_plan_chart_resolution_03_allocation_history.md) | `AllocationHistoryChart` (serie stacked dinamiche) | ✅ implementato |
| [`Milestone_3/chart_resolution/impl_plan_chart_resolution_04_signals_overlay.md`](./Milestone_3/chart_resolution/impl_plan_chart_resolution_04_signals_overlay.md) | Dispatch downsample per i 9 tipi di segnale overlay | ✅ implementato |
| [`Milestone_3/chart_resolution/impl_plan_chart_resolution_05_badge_i18n.md`](./Milestone_3/chart_resolution/impl_plan_chart_resolution_05_badge_i18n.md) | `ResolutionBadge` + chiavi i18n (4 lingue) | ✅ implementato |
| [`Milestone_3/chart_resolution/impl_plan_chart_resolution_06_compact_cards.md`](./Milestone_3/chart_resolution/impl_plan_chart_resolution_06_compact_cards.md) | `PriceChartCompact`/`LineChart` rami compact (`/assets`, `/fx`) | ✅ implementato |

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

## Nota di archiviazione Milestone 3 (2026-07-15)

Tutti i sotto-piani di M3 risultavano ✅ (disegno, piano implementativo, implementazione) al momento
dell'archiviazione — nessun item aperto rilevato. Note aggiornate durante l'archiviazione:

- Le annotazioni "codice in working tree non ancora committato" (Fase 2 — holdings, 2026-07-11 fleet; Fase 3
  — transazioni, chiuso 2026-07-08) in `Milestone_3/README.md` sono state rimosse: `git status` alla data di
  archiviazione confermava che quel codice è già committato.
- **Issue pre-esistente segnalata, non corretta** (fuori scope di questa archiviazione): la sezione "Guide
  rapide" di [`Milestone_3/README.md`](./Milestone_3/README.md) linka `GUIDA-TOOLBAR-RESPONSIVE.md`, ma il
  file sul disco è `GUIDA-TOOLBAR-RESPONSIVE-v2.md` — link già rotto prima di questa archiviazione (non
  causato dallo spostamento). Segnalato per una correzione dedicata futura.
