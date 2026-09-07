---
title: "Backend-owned versioned AI snapshots with a frontend-owned safe prompt and clipboard boundary"
category: decision
status: resolved
date: 2026-07-26
updated: 2026-08-05
mkdocs: "developer/architecture/patterns/ai_export_snapshot.md"
tags: [ai-export, backend, frontend, architecture, snapshot, versioning, security, mcp, hard-cutover]
related:
  - sources/phase00-ai-export-backend-snapshot
  - decisions/ai-export-contextual-ui-memory
  - entities/ai-export-snapshot-service
  - problems/ai-export-cash-fx-valuation-basis-mismatch
  - problems/ai-export-drawdown-selected-history-fallback
  - problems/ai-export-clipboard-fallback-unreachable
  - decisions/ai-export-prompt-catalog
  - decisions/signal-backend-plugin-architecture
  - entities/portfolio-engine
  - entities/lots-analysis-service
  - decisions/fifo-runtime-decision
  - domains/auth
  - domains/brokers
  - features/F-010
  - concepts/ai-export-catalog-granularity-and-composition
---

# Decision: Backend-owned versioned AI snapshots with a frontend-owned safe prompt and clipboard boundary

## Context

The original AI Export assembled financial facts, technical indicators, compaction, and prompts in several TypeScript builders. That duplicated backend math, made Portfolio/Asset/FX paths drift independently, reused Portfolio behavior on Broker Detail, and could not be called safely by a future non-UI client such as MCP. At the same time, moving prompts and user-authored notes into the backend would have mixed factual APIs with presentation, localization, and an injection-sensitive clipboard boundary.

## Options Considered

1. **Keep frontend builders and only expand the prompt catalog** — lowest migration cost, but retains duplicated financial/technical logic, browser-only execution, and divergent domain implementations.
2. **Move both snapshot data and final prompts into the backend** — centralizes output, but couples backend contracts to localized presentation and requires user notes to cross an instruction boundary rather than remain serialized data.
3. **Split ownership at a versioned snapshot boundary** — backend owns authoritative facts, calculations, semantics, coverage, and profile selection; frontend owns trusted local instructions, response contracts, language, notes-as-data, safe rendering, and clipboard behavior. **Chosen.**

## Decision

LibreFolio exposes a backend-owned AI Export snapshot platform with these invariants:

- **Exact finite V1 catalog:** the first released contract exposes 8 public
  datasets and 11 public analyses over 67 components and 40 internal datasets.
  Snapshot, catalog, selection, instruction-template and response-contract
  versions start at V1; prior V2/V3 labels were unreleased iterations.
- **Single runtime:** `AiExportRuntimeService` + registries +
  `ComponentComposer` are the only production path. The intermediate
  profile/assembler runtime, V1 schema and internal legacy analyses were removed.
- **Fail closed:** frontend and backend catalogs form an explicit compatibility
  handshake. Unknown, internal, version-mismatched or unsupported selections
  are rejected; there is no compatibility fallback.
- **Backend factual ownership:** Portfolio Engine/Service, runtime FIFO,
  Asset/FX services and `SignalService` remain authoritative. Components map
  those outputs and declare period, unit, method, coverage, omissions and
  provenance rather than duplicating math.
- **Curated technical scope:** component/dataset specs explicitly select signal
  facts. New plugins do not auto-enrol into public AI Export; a contract and
  version change is required.
- **Server-owned security scope:** requests never accept `user_id`. Authentication supplies it, accessible broker IDs are loaded server-side, and any explicitly denied broker fails the whole request rather than being silently filtered.
- **Frontend presentation ownership:** task labels, local instruction templates, response contracts, locale-derived response language, user notes, safe rendering, and final prompt statistics stay in the browser. Web research is normalized off; response-language, render-mode, web, and compatibility-status controls are not exposed.
- **Final analysis model:** one custom select presents icon, localized name, and localized description. A synthetic **Data Snapshot** maps the domain's factual snapshot task to `data_only`; every real analysis maps to `full_prompt`.
- **Semantic composition remains modular:** analyses compose ordered
  required/optional datasets; public general/detailed exports hide internal
  fragmentation. `*.all_data` remains an internal canonical union. See
  [[concepts/ai-export-catalog-granularity-and-composition]].
- **Contextual UI memory:** task, detail, mode, and raw notes draft persist under a client-session user ID plus `portfolio`, `broker:{id}`, `asset:{id}`, or `fx:{canonical_slug}`. Response language is always refreshed from the current locale. Snapshot may preserve hidden notes in memory, but normalization removes them from the exported prompt and clipboard. See [[decisions/ai-export-contextual-ui-memory]].
- **Portal and documentation boundary:** the panel is appended to `document.body`, fixed and viewport-positioned above chart controls, while the book link targets the current domain's English manual or the localized shared fallback.
- **Safe rendering boundary:** snapshot values and user notes are normalized to JSON-safe data, deterministically serialized as YAML, and placed in dynamically sized Markdown fences. Untrusted values are never interpolated as raw instructions.
- **Empty temporal rows are a presentation-only omission:** the public renderer removes a temporal row only when it contains no observation, economic value, flow, P&L, extrema, reconciliation, economic date, or explicit state. Observed zero remains data, diagnostics report detected/omitted/rendered row counts, and backend buckets and calculations remain intact.
- **Broker universes use explicit names:** `accessible_broker_count` is the authorization universe, `scoped_broker_count`/`broker_scope` are the effective calculation universe, `position_broker_count` counts Brokers with open positions at snapshot date, and `period_contributor_broker_count` counts period-performance contributors. The Entity Directory uses the effective prepared scope, including a scoped Broker with no current position rows.
- **Selected-period applicability:** task applicability is evaluated from the task's selected observations. Trailing technical observations may enrich market context, but an empty technical window must not invalidate a historical `drawdown_recovery` request that has two selected observations and a measurable prior maximum.
- **Transport-only clipboard fallback:** preserve the immediate `ClipboardItem(Promise<Blob>)` route when supported; otherwise prepare the same V2 export once and use `writeText`/`execCommand`. Clipboard capability never permits fallback to legacy builders or prompt logic.
- **Standalone/MCP-ready service:** `AiExportRuntimeService` is not coupled to
  frontend state. HTTP is one adapter; a future authenticated transport can
  invoke the same typed snapshot path.
- **Hard cutover and cleanup:** Dashboard, Broker Detail, Asset Detail and FX
  Detail use only the public V1 path. Frontend legacy builders,
  local technical engines, backend profile/assembler runtime and parity fixtures
  are removed.
- **No Portfolio Engine rewrite:** AI Export consumes engine-owned accounting and decomposition as-is. Snapshot-specific exposure views may use their own explicitly declared valuation basis and denominator.

## Consequences

- All four domains share one registry/composer orchestration model while
  retaining domain-specific component builders.
- Backend snapshots are factual, versioned, deterministic, read-only, and usable without the UI; LibreFolio itself still calls no LLM.
- Frontend localization and prompt experimentation do not force financial API
  logic into presentation code, but public catalog changes remain coordinated
  across backend specs/schema, frontend catalog/templates, i18n and tests.
- Browser-local draft continuity is deliberately not a backend setting or export-history feature. It is isolated by authenticated user and concrete UI context, validated against the current catalog, and safe to discard when stale.
- Hiding controls does not weaken the underlying contracts: response language remains deterministic from locale, web research remains false, catalog compatibility still fails closed, and clipboard compatibility remains an internal transport choice.
- Portalization prevents Asset/FX chart overlays from covering the panel and keeps the task select and book link keyboard-operable.
- Required source failures produce typed non-success responses; a missing optional indicator is omitted or marked unavailable without fabricating data.
- Dense Portfolio/Broker output remains explicit rather than silently truncated: the 20k/60k frontend warning stays in place and no automatic token cap or detail downgrade is introduced.
- The old [[decisions/ai-export-prompt-catalog]] remains historical context but is superseded as the production architecture.
- The V1 public catalog hides internal dataset distinctions behind one general
  and one detailed export per domain while preserving granular composition
  internally. Position price, observed market price and price history remain
  distinct facts. See [[concepts/ai-export-catalog-granularity-and-composition]].
- The live-E2E cash valuation-basis error established an explicit rule: never assert equality between metrics evaluated on different dates or denominators. See [[problems/ai-export-cash-fx-valuation-basis-mismatch]].
- Final review established two further boundary rules: presentation context cannot tighten task applicability ([[problems/ai-export-drawdown-selected-history-fallback]]), and transport compatibility cannot revive product-level legacy behavior ([[problems/ai-export-clipboard-fallback-unreachable]]).
- Shared immutable registries, cached catalog, one canonical stats dump and an
  integer fixed point reduce overhead without changing serialized output.
- Functional tests verify contracts, composition, safety and rendering
  structure; they do not freeze prompt wording. Real copied-DB probes,
  cross-run content review and Task Adequacy remain explicit skill workflows.
  UI/probe equivalence for the same current input is still byte-exact, while a
  cross-run SHA change is diagnostic rather than a functional failure.

## Validation / Success Criteria

- Registry counts are exactly 67 components, 40 datasets and 11 analyses;
  public catalog is exactly 8 datasets + 11 analyses.
- Four authenticated domains and typed 403/404/409/422/503 problems.
- No backend presentation text and no frontend financial or technical calculation.
- Safe adversarial serialization and clipboard behavior.
- No profile/assembler/V1-schema production imports or runtime fallback.
- Browser E2E across all four surfaces.
- Canonical runner registration for all AI Export service/schema/API/probe and
  frontend unit/E2E tests; zero backend/frontend orphan files.
- Manual desktop/mobile approval on 27 July 2026 covering Dashboard layout, custom task selection, chart-layer stacking, per-context memory, domain manual links, clipboard behavior, and representative prompts.
- On 3 August 2026 the project owner explicitly approved empty-temporal-row hardening, explicit Broker nomenclature, and `20260801T085820.657238Z` as final targeted evidence. The run passed 4/4 prompts with no failures, skips, or regressions; UI/probe matched 4/4, the secret scan passed, and source/production databases were unchanged.
- Applied Standard-policy run `20260803T164514.504966Z` passed 7/7 prompts with zero failures/public violations, UI/probe equivalence, a passed secret scan, and unchanged source/production databases.
- Catalog explanation run `20260804T085052.052297Z` generated and read five representative Portfolio prompts (Overview, Asset Snapshot, Asset Comparison, PAC, and Rebalancing): 5/5 passed with zero failures/public-output violations, UI/probe equivalence, a passed secret scan, and unchanged source/production databases. The accompanying report verified all 49 public choices against the current runtime declarations.
- Documentation closure is explicit: `mkdocs_src/docs/developer/test-walkthrough/api.md` lists AI Export API, service, probe, frontend-unit, and Playwright commands; `.github/copilot-instructions.md` states the AI Export product and backend/frontend boundary. User Guide IT/FR/ES translations remain deliberately deferred.
- Final baseline `20260804T214400.268752Z` and candidate
  `20260804T224056.073291Z` both completed 114/114 prompts. Comparison found
  114/114 unchanged stable keys and zero character, byte, composition, event or
  state deltas. Secret scan, UI/probe equivalence and DB immutability passed.
- Final gates: 835 service, 16 schema, 15 API, 56 probe utility, 199 frontend
  unit and 34 Playwright tests passed; typecheck 0/0, i18n 2,332/2,332 and zero
  orphan.
- Task Adequacy: 66/66 Analysis variants `OPTIMAL`; all 12 fiscal variants were
  reread after their contract refinement.

## Participants

The completed Phase 0 plan records approval by the project owner and implementation/review work across backend and frontend agents. The project owner manually approved the final desktop/mobile UX on 27 July 2026 and the final temporal-row/Broker hardening plus evidence designation on 3 August 2026. Individual participant names were not recorded in the source chain.

## Links

- [[sources/phase00-ai-export-backend-snapshot]]
- [[decisions/ai-export-contextual-ui-memory]]
- [[entities/ai-export-snapshot-service]]
- [[decisions/signal-backend-plugin-architecture]]
- [[entities/portfolio-engine]]
- [[decisions/fifo-runtime-decision]]
- [[problems/ai-export-drawdown-selected-history-fallback]]
- [[problems/ai-export-clipboard-fallback-unreachable]]
- [[domains/auth]]
- [[domains/brokers]]
- [[features/F-010]]
- [[concepts/ai-export-catalog-granularity-and-composition]]

## Source files

| Role | Path |
|------|------|
| Completed chain index | `LibreFolio_developer_journal/Release_2/phases/01_signalMigration/02_aiExport/README.md` |
| Final audit plan | `LibreFolio_developer_journal/Release_2/phases/01_signalMigration/02_aiExport/plan-phase00AiExportFinalAuditAndLegacyRemoval.prompt.md` |
| Final audit and closure | `LibreFolio_developer_journal/Release_2/phases/01_signalMigration/02_aiExport/report-phase00AiExportFinalAuditAndClosureV1.md` |
| Developer architecture | `mkdocs_src/docs/developer/architecture/patterns/ai_export_snapshot.md` |
| Composition and `all_data` semantics | `mkdocs_src/docs/developer/architecture/patterns/ai_export_composition.md` |
| Runtime schemas | `backend/app/schemas/ai_export_runtime.py` |
| Runtime service | `backend/app/services/ai_export/runtime_service.py` |
| Component/dataset/analysis specs | `backend/app/services/ai_export/components/`, `backend/app/services/ai_export/datasets/`, `backend/app/services/ai_export/analyses/` |
| Frontend compatibility handshake | `frontend/src/lib/features/ai-export/catalog/compatibility.ts` |
| Analysis selection and Snapshot mapping | `frontend/src/lib/features/ai-export/AiExportOptionsPanel.svelte`, `frontend/src/lib/features/ai-export/aiExportOptions.ts` |
| Contextual UI memory | `frontend/src/lib/features/ai-export/aiExportMemory.ts`, `frontend/src/lib/stores/app/clientSession.ts` |
| Locale-derived response language | `frontend/src/lib/features/ai-export/AiExportMenu.svelte`, `frontend/src/lib/features/ai-export/ui.ts` |
| Body portal and focus/session ownership | `frontend/src/lib/features/ai-export/AiExportMenu.svelte` |
| Domain-aware manual link | `frontend/src/lib/features/ai-export/AiExportOptionsPanel.svelte`, `frontend/src/lib/components/ui/DocsLink.svelte` |
| Safe serialization | `frontend/src/lib/features/ai-export/serialization/` |
| Prompt renderer | `frontend/src/lib/features/ai-export/templates/promptRenderer.ts` |
| Empty temporal-row renderer and diagnostics | `frontend/src/lib/features/ai-export/templates/snapshotDataRenderer.ts` |
| Explicit Broker universe fields | `backend/app/services/ai_export/components/portfolio_financial.py`, `backend/app/services/ai_export/runtime_service.py` |
| Real-prompt evidence probe | `backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py` |
| Prompt-size warning boundary | `frontend/src/lib/features/ai-export/aiExportOptions.ts`, `frontend/src/lib/features/ai-export/AiExportOptionsPanel.svelte` |
| Clipboard orchestration | `frontend/src/lib/features/ai-export/aiExportClipboard.ts` |
| Clipboard fallback regression | `frontend/src/lib/features/ai-export/__tests__/aiExportClipboard.test.ts` |
| Canonical test registration | `scripts/test_runner/_backend_services.py`, `scripts/test_runner/_backend_schemas.py`, `scripts/test_runner/_backend_api.py`, `scripts/test_runner/_frontend_ai_export.py`, `scripts/test_runner/_registry.py`, `scripts/test_runner/_suites.py` |
| Final UI unit coverage | `frontend/src/lib/features/ai-export/__tests__/aiExportMemory.test.ts`, `frontend/src/lib/features/ai-export/__tests__/aiExportOptions.test.ts`, `frontend/src/lib/features/ai-export/__tests__/aiExportUi.test.ts` |
| Final UI browser coverage | `frontend/e2e/ai-export/` |
| AI Export test walkthrough | `mkdocs_src/docs/developer/test-walkthrough/api.md` |
| Repository product/boundary instructions | `.github/copilot-instructions.md` |
