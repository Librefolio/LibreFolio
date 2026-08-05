---
title: "AI Export Runtime Service and Snapshot Platform"
category: entity
type: service
date: 2026-07-26
updated: 2026-08-05
mkdocs: "developer/architecture/patterns/ai_export_snapshot.md"
tags: [backend, frontend, ai-export, snapshot, service, components, datasets, analyses, mcp, security]
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

# AI Export Runtime Service and Snapshot Platform

## Role

`AiExportRuntimeService` is the sole backend orchestration boundary for AI Export.
It turns an authenticated V1 selection into a typed Snapshot V1 by validating
the public catalog choice, deriving broker scope, composing required/optional
datasets from reusable components, and returning deterministic facts and
metadata. The frontend owns trusted prompt rendering, localization, contextual
notes and clipboard transport.

## Location

`backend/app/services/ai_export/runtime_service.py`

## Key Interfaces

| Interface | Responsibility |
|---|---|
| `AiExportRuntimeService.get_catalog()` | Returns the cached static public catalog: 8 datasets and 11 analyses. |
| `AiExportRuntimeService.build_snapshot()` | Validates selection/scope and composes a Snapshot V1 through the component registries. |
| `ComponentComposer.compose()` | Builds each component once per request and enforces required/optional failure behavior. |
| Component/Dataset/Analysis registries | Define the finite 67/40/11 composition graph. |
| `GET /api/v1/ai-export/catalog` | HTTP catalog adapter. |
| `POST /api/v1/ai-export/snapshot` | Authenticated read-only HTTP snapshot adapter with typed problems. |

## Platform Components

```text
Strict request
  → public selection resolver
  → authenticated broker scope
  → AnalysisSpec or public DatasetSpec
  → DatasetSpec composition
  → ComponentComposer + request BuildContext
      → Portfolio Engine / PortfolioService / runtime FIFO
      → Asset and FX source services / SignalService
  → typed versioned snapshot
  → frontend contract verification
  → safe local YAML/Markdown prompt
  → Clipboard API
```

- The final registry has 67 `ComponentSpec`, 40 `DatasetSpec`, and 11 public
  `AnalysisSpec` entries. Only eight datasets are directly selectable.
- A request-scoped `BuildContext` memoizes components and typed resources so
  analyses reuse facts without duplicate I/O or signal calculation.
- Required datasets fail closed. Optional components degrade only with explicit
  omission/unavailable diagnostics.
- `*.all_data` entries remain internal computed unions, not special builders.
- Temporal policy lives under `temporal/`; `telemetry.py` contains only canonical
  JSON and chars/4 estimation.
- Registry/composer defaults and the public catalog are shared; response stats
  use one canonical dump plus integer fixed-point convergence.
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
- an activation-preserving `ClipboardItem(Promise<Blob>)` path when supported, otherwise one V1 preparation followed by the generic `writeText`/`execCommand` transport;
- a body-level fixed panel above chart controls and domain-aware book links to English manuals with a localized shared fallback.

## Design Notes

- Portfolio and Broker share authoritative report data but have separate request/response domains and task catalogs.
- PAC Planning and Rebalancing receive `portfolio.overview_and_history`, so
  their prompts include positions, prices, value, WAC, P&L, weights, cash,
  performance, flows, income, costs, economic FIFO summary and compact
  per-Asset market context. `portfolio.asset_history` is the denser optional
  follow-up.
- Position unit price, observed Asset market price, and bucketed price history are distinct data contracts. See [[concepts/ai-export-catalog-granularity-and-composition]].
- Asset and FX compose independently while sharing component, temporal and
  signal infrastructure.
- FIFO is queried at runtime through [[entities/lots-analysis-service]]; no AI-specific FIFO persistence is introduced.
- Portfolio cash decomposition remains engine-owned. Currency exposure uses factual native balances converted at snapshot time and declares a separate denominator; see [[problems/ai-export-cash-fx-valuation-basis-mismatch]].
- Asset drawdown market context uses technical-window observations when present, otherwise selected observed history. `drawdown_recovery` applicability remains based on two selected observations and a measurable prior maximum; see [[problems/ai-export-drawdown-selected-history-fallback]].
- Clipboard capability fallback never changes the export architecture: it transports the same prepared V1 prompt and never revives legacy builders; see [[problems/ai-export-clipboard-fallback-unreachable]].
- New tasks or plugins require explicit backend and frontend contract changes plus versioned tests; registry auto-enrolment is intentionally forbidden.
- AI Export service/schema/API/probe and frontend unit/E2E tests are explicitly
  registered in the canonical runner; the final orphan audit is zero.
- The backend/frontend public catalog duplication is intentional: it is the
  fail-closed compatibility handshake, not duplicate runtime logic.
- The legacy profile/assembler runtime, V1 schema and 11 internal Analysis specs
  were removed after a 114/114 exact-output comparison.
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
| 2026-08-05 | Final V3 closure reduced the public catalog to 8 datasets/11 analyses over 67 components and 40 internal datasets, removed the entire profile/assembler runtime and proved 114/114 prompt equivalence in candidate `20260804T224056.073291Z`. |
| 2026-08-05 | Before first release, public snapshot/catalog/selection/instruction/response versions were reset to V1. Probe helper tests stayed in the runner under an explicit helper-only action; real prompt and Task Adequacy runs remained separate. |

## Source files

| Role | Path |
|------|------|
| Completed chain index | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/README.md` |
| Final audit and closure | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/report-phase00AiExportFinalAuditAndClosureV1.md` |
| Runtime orchestration | `backend/app/services/ai_export/runtime_service.py` |
| Runtime schemas | `backend/app/schemas/ai_export_runtime.py` |
| Dataset/analysis composition | `backend/app/services/ai_export/datasets/`, `backend/app/services/ai_export/analyses/` |
| Component composition | `backend/app/services/ai_export/components/`, `backend/app/services/ai_export/dependencies.py`, `backend/app/services/ai_export/composer.py` |
| Temporal policy | `backend/app/services/ai_export/temporal/` |
| Canonical serialization utilities | `backend/app/services/ai_export/telemetry.py` |
| HTTP API | `backend/app/api/v1/ai_export.py` |
| Frontend platform | `frontend/src/lib/features/ai-export/` |
| Custom analysis panel and manual links | `frontend/src/lib/features/ai-export/AiExportOptionsPanel.svelte` |
| Snapshot/full-prompt normalization | `frontend/src/lib/features/ai-export/aiExportOptions.ts` |
| Short-lived contextual memory | `frontend/src/lib/features/ai-export/aiExportMemory.ts` |
| Body portal and locale-owned panel session | `frontend/src/lib/features/ai-export/AiExportMenuV2.svelte` |
| Locale mapping | `frontend/src/lib/features/ai-export/ui.ts` |
| Client-session user isolation | `frontend/src/lib/stores/app/clientSession.ts`, `frontend/src/lib/stores/app/auth.ts` |
| Shared book-link fallback | `frontend/src/lib/components/ui/DocsLink.svelte` |
| Clipboard orchestration/regression | `frontend/src/lib/features/ai-export/aiExportClipboard.ts`, `frontend/src/lib/features/ai-export/__tests__/aiExportClipboard.test.ts` |
| Backend tests | `backend/test_scripts/test_services/test_ai_export_*.py`, `backend/test_scripts/test_api/test_ai_export_api.py` |
| Frontend tests | `frontend/src/lib/features/ai-export/__tests__/` |
| UI memory/options regressions | `frontend/src/lib/features/ai-export/__tests__/aiExportMemory.test.ts`, `frontend/src/lib/features/ai-export/__tests__/aiExportOptions.test.ts`, `frontend/src/lib/features/ai-export/__tests__/aiExportUi.test.ts` |
| Canonical test registration | `scripts/test_runner/_backend_services.py`, `scripts/test_runner/_backend_schemas.py`, `scripts/test_runner/_backend_api.py`, `scripts/test_runner/_frontend_ai_export.py`, `scripts/test_runner/_registry.py`, `scripts/test_runner/_suites.py` |
| Browser E2E | `frontend/e2e/ai-export/` |
| Developer architecture | `mkdocs_src/docs/developer/architecture/patterns/ai_export_snapshot.md` |
| Composition architecture | `mkdocs_src/docs/developer/architecture/patterns/ai_export_composition.md` |
