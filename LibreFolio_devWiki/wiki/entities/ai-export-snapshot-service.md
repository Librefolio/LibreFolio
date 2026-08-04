---
title: "AiExportSnapshotService and AI Export Snapshot Platform"
category: entity
type: service
date: 2026-07-26
updated: 2026-08-04
mkdocs: "developer/architecture/patterns/ai_export_snapshot.md"
tags: [backend, frontend, ai-export, snapshot, service, profiles, assemblers, mcp, security]
related:
  - sources/phase00-ai-export-backend-snapshot
  - decisions/ai-export-versioned-snapshot-boundary
  - decisions/ai-export-contextual-ui-memory
  - problems/ai-export-cash-fx-valuation-basis-mismatch
  - problems/ai-export-drawdown-selected-history-fallback
  - problems/ai-export-clipboard-fallback-unreachable
  - decisions/signal-backend-plugin-architecture
  - entities/portfolio-engine
  - entities/portfolio-service
  - entities/lots-analysis-service
  - decisions/fifo-runtime-decision
  - domains/auth
  - domains/brokers
  - features/F-010
  - concepts/ai-export-catalog-granularity-and-composition
---

# AiExportSnapshotService and AI Export Snapshot Platform

## Role

`AiExportSnapshotService` is the FastAPI-independent orchestration boundary for AI Export V2. It turns an authenticated, discriminated request into one typed, versioned Portfolio, Broker, Asset, or FX snapshot by resolving an exact profile, deriving broker scope, and dispatching to the appropriate assembler. The wider platform includes the static profile catalog, strict schemas, shared normalization/sampling/coverage/telemetry utilities, domain assemblers, and the frontend compatibility/rendering/clipboard boundary.

## Location

`backend/app/services/ai_export/service.py`

## Key Interfaces

| Interface | Responsibility |
|---|---|
| `AiExportSnapshotService.get_catalog()` | Returns the static, user-data-free 54-entry compatibility catalog. |
| `prepare_request(user_id, request)` | Resolves the exact profile, loads accessible broker IDs once, rejects denied explicit scope, and produces `AiExportPreparedRequest`. |
| `build_snapshot(user_id, request)` | Dispatches to the Asset, FX, Portfolio, or Broker assembler. |
| `resolve_profile(domain, task, detail)` | Exact allow-list lookup; raises an unsupported-profile error instead of defaulting. |
| `GET /api/v1/ai-export/catalog` | HTTP catalog adapter. |
| `POST /api/v1/ai-export/snapshot` | Authenticated read-only HTTP snapshot adapter with typed problems. |

## Platform Components

```text
Strict request
  → exact profile resolver
  → authenticated broker scope
  → domain assembler
      → Portfolio Engine / PortfolioService
      → LotsAnalysisService / runtime FIFO
      → Asset and FX source services
      → SignalService curated bundle
  → typed versioned snapshot
  → frontend contract verification
  → safe local YAML/Markdown prompt
  → Clipboard API
```

- The current semantic-composition layer exposes 32 `DatasetSpec` entries and 17 `AnalysisSpec` entries over 65 reviewed `ComponentSpec` builders. A request-scoped `BuildContext` memoizes components and raw typed resources so analyses can reuse facts without duplicate I/O or signal calculation.
- Analyses compose ordered required and optional datasets; required failures fail closed and optional failures degrade to omission. The complete `*.all_data` entries are computed unions of canonical complete datasets, not special builders and not unions of every focused public choice.
- `assemblers/` map authoritative domain services; they do not own independent portfolio, FIFO, FX, or signal mathematics.
- `technical.py` adapts profile-owned bundles to the shared [[decisions/signal-backend-plugin-architecture]].
- `normalization.py`, `sampling.py`, `coverage.py`, and `telemetry.py` provide deterministic shared policies.
- The frontend catalog intersects local presentation definitions with the backend catalog and fails closed before requesting or rendering a snapshot.

## Security and Failure Model

- `user_id` is supplied by authentication, never request JSON.
- Broker scope comes from `BrokerUserAccess`; explicit inaccessible IDs fail atomically with `broker_access_denied`.
- Strict Pydantic unions reject unknown fields and unsupported domain/task/detail tuples.
- Required source failures do not return success-shaped partial snapshots; they become typed `snapshot_source_failure` responses.
- Optional technical unavailability remains local to the affected signal and does not remove sibling facts.
- The service boundary can be reused by a future MCP transport, but MCP transport/server implementation is outside Phase 0.

## Frontend Companion Boundary

The service does not return prompt text, labels, translations, or user notes. `frontend/src/lib/features/ai-export/` owns:

- the local task catalog, instructions, and response contracts;
- fail-closed reconciliation against backend versions/support flags;
- a custom analysis select with icon, localized name, and localized description;
- the synthetic Data Snapshot → domain snapshot task + `data_only` mapping, while real analyses always use `full_prompt`;
- response language derived from the active UI locale, with response-language, render-mode, web-research, and compatibility-status controls hidden and web research forced off;
- user/context-keyed browser memory for task, detail, mode, and notes through the client-session user ID; see [[decisions/ai-export-contextual-ui-memory]];
- deterministic JSON-safe YAML and dynamic Markdown fences;
- strict removal of hidden notes from every Snapshot export while retaining the draft for a later analysis;
- Clipboard API orchestration that starts within the originating user gesture;
- an activation-preserving `ClipboardItem(Promise<Blob>)` path when supported, otherwise one V2 preparation followed by the generic `writeText`/`execCommand` transport;
- a body-level fixed panel above chart controls and domain-aware book links to English manuals with a localized shared fallback.

## Design Notes

- Portfolio and Broker share authoritative report data but have separate request/response domains and task catalogs.
- PAC Planning and Rebalancing both receive `portfolio.overview`, so their prompts already include per-position Asset/Broker rows with quantity, unit price, value, WAC, P&L, and weight. Their optional Asset Snapshot/Comparison datasets add per-Asset observed market context when available; they are not aggregate-only.
- Position unit price, observed Asset market price, and bucketed price history are distinct data contracts. See [[concepts/ai-export-catalog-granularity-and-composition]].
- `broker.technical` currently includes coverage, indicator history, events, and breadth but no raw technical-price/OHLC component. `asset.trend_analysis` currently composes Overview + Market Technical without `asset.drawdown_context`, despite the Italian UI description mentioning Drawdown. These are recorded gaps, not service changes.
- Asset and FX can assemble independently while sharing technical and normalized-return utilities.
- FIFO is queried at runtime through [[entities/lots-analysis-service]]; no AI-specific FIFO persistence is introduced.
- Portfolio cash decomposition remains engine-owned. Currency exposure uses factual native balances converted at snapshot time and declares a separate denominator; see [[problems/ai-export-cash-fx-valuation-basis-mismatch]].
- Asset drawdown market context uses technical-window observations when present, otherwise selected observed history. `drawdown_recovery` applicability remains based on two selected observations and a measurable prior maximum; see [[problems/ai-export-drawdown-selected-history-fallback]].
- Clipboard capability fallback never changes the export architecture: it transports the same prepared V2 prompt and never revives legacy builders; see [[problems/ai-export-clipboard-fallback-unreachable]].
- New tasks or plugins require explicit backend and frontend contract changes plus versioned tests; registry auto-enrolment is intentionally forbidden.
- AI Export service/schema/API tests and the frontend AI Export+signal unit/E2E set are explicitly registered in the canonical test runner, so backend, frontend, and complete aggregate suites execute them. Unrelated pre-existing orphan tests remain out of scope.
- The final UI intentionally separates remembered draft state from effective export state: response language is refreshed from locale, web research is false, and Snapshot notes are absent even when the raw draft remains stored.
- The panel is portalized to `document.body` with `z-index: 9000`; owned portalized select events, Escape behavior, outside-click closing, repositioning, and trigger-focus restoration are handled by the menu component rather than by the four routes.

## History

| Date | Change |
|---|---|
| 2026-07-26 | Static catalog, strict schemas, exact resolver, authenticated service skeleton, and typed API established. |
| 2026-07-26 | Asset and FX assemblers completed, followed by Portfolio and Broker; all 54 profiles became executable. |
| 2026-07-26 | Frontend V2 catalog, safe renderer, clipboard flow, and four-surface hard cutover completed; legacy builders and local technical engines removed. |
| 2026-07-26 | Live E2E corrected the false cash valuation-basis equality invariant without modifying Portfolio Engine math. |
| 2026-07-26 | Final review fixed selected-history drawdown fallback, made non-modern clipboard transport reachable without legacy logic, and registered the complete AI Export/current-signal test set in canonical suites. |
| 2026-07-27 | Final UX replaced exposed mode/language/web/compatibility controls with the custom analysis select and locale-owned defaults; added per-user/per-context persistent draft memory, Snapshot note non-export, body portal, and domain manual links. |
| 2026-07-27 | Project owner approved the desktop/mobile review; the completed plan chain was indexed by `Release_2/Phase_0/01_signalMigration/02_aiExport/README.md` in its nested migration location. |
| 2026-08-04 | A 49/49 catalog explanation documented the 32-dataset/17-analysis/65-component composition model, confirmed per-position/per-Asset facts in PAC and Rebalancing, clarified price and `all_data` semantics, and recorded two potential gaps. Real Portfolio probe `20260804T085052.052297Z` passed 5/5 with unchanged databases and a passed secret scan. |

## Source files

| Role | Path |
|------|------|
| Completed chain index | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/README.md` |
| UI catalog explanation and prompt verification | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/report-phase00AiExportUiPromptCatalogExplainedV1.md` |
| Service orchestration | `backend/app/services/ai_export/service.py` |
| Exact resolver/catalog | `backend/app/services/ai_export/resolver.py` |
| Profile composition models | `backend/app/services/ai_export/models.py` |
| Task and detail profiles | `backend/app/services/ai_export/profiles/` |
| Dataset/analysis composition | `backend/app/services/ai_export/datasets/`, `backend/app/services/ai_export/analyses/` |
| Component composition | `backend/app/services/ai_export/components/`, `backend/app/services/ai_export/dependencies.py`, `backend/app/services/ai_export/composer.py` |
| Domain assemblers | `backend/app/services/ai_export/assemblers/` |
| Shared technical runner | `backend/app/services/ai_export/technical.py` |
| Normalization/sampling/coverage/telemetry | `backend/app/services/ai_export/normalization.py`, `sampling.py`, `coverage.py`, `telemetry.py` |
| HTTP API | `backend/app/api/v1/ai_export.py` |
| Strict schemas | `backend/app/schemas/ai_export.py` |
| Frontend platform | `frontend/src/lib/features/ai-export/` |
| Custom analysis panel and manual links | `frontend/src/lib/features/ai-export/AiExportOptionsPanel.svelte` |
| Snapshot/full-prompt normalization | `frontend/src/lib/features/ai-export/aiExportOptions.ts` |
| Persistent contextual memory | `frontend/src/lib/features/ai-export/aiExportMemory.ts` |
| Body portal and locale-owned panel session | `frontend/src/lib/features/ai-export/AiExportMenuV2.svelte` |
| Locale mapping | `frontend/src/lib/features/ai-export/ui.ts` |
| Client-session user isolation | `frontend/src/lib/stores/app/clientSession.ts`, `frontend/src/lib/stores/app/auth.ts` |
| Shared book-link fallback | `frontend/src/lib/components/ui/DocsLink.svelte` |
| Asset drawdown assembler/regression | `backend/app/services/ai_export/assemblers/asset.py`, `backend/test_scripts/test_services/test_ai_export_asset_fx.py` |
| Clipboard orchestration/regression | `frontend/src/lib/features/ai-export/aiExportClipboardV2.ts`, `frontend/src/lib/features/ai-export/__tests__/aiExportClipboardV2.test.ts` |
| Backend tests | `backend/test_scripts/test_services/test_ai_export_*.py`, `backend/test_scripts/test_api/test_ai_export_api.py` |
| Frontend tests | `frontend/src/lib/features/ai-export/__tests__/` |
| UI memory/options regressions | `frontend/src/lib/features/ai-export/__tests__/aiExportMemory.test.ts`, `frontend/src/lib/features/ai-export/__tests__/aiExportOptions.test.ts`, `frontend/src/lib/features/ai-export/__tests__/aiExportUi.test.ts` |
| Canonical test registration | `scripts/test_runner/_backend_services.py`, `scripts/test_runner/_backend_schemas.py`, `scripts/test_runner/_backend_api.py`, `scripts/test_runner/_frontend_ai_export.py`, `scripts/test_runner/_registry.py`, `scripts/test_runner/_suites.py` |
| Browser E2E | `frontend/e2e/ai-export.spec.ts` |
| Developer architecture | `mkdocs_src/docs/developer/architecture/patterns/ai_export_snapshot.md` |
| Composition architecture | `mkdocs_src/docs/developer/architecture/patterns/ai_export_composition.md` |
