---
title: "Backend-owned versioned AI snapshots with a frontend-owned safe prompt and clipboard boundary"
category: decision
status: resolved
date: 2026-07-26
updated: 2026-08-04
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

- **Exact finite catalog:** 18 frozen task specs × `compact`, `standard`, and `full` = **54** deterministic profiles. Every tuple has stable `profile_id`, `profile_version`, snapshot schema version, and frontend response-contract ID/version.
- **Fail closed:** the resolver performs exact lookup with no defaults or normalization. The frontend disables or rejects any catalog/schema/profile/contract/support mismatch; there is no compatibility fallback.
- **Backend factual ownership:** Portfolio Engine/Service, runtime FIFO, Asset/FX services, and `SignalService` remain the authoritative sources. Assemblers map those outputs and declare metric denominators, periods, units, methods, coverage, omissions, and provenance rather than duplicating math.
- **Curated technical scope:** profile bundles explicitly allow-list signal instances and parameters. New plugins do not auto-enrol; a contract and version change is required.
- **Server-owned security scope:** requests never accept `user_id`. Authentication supplies it, accessible broker IDs are loaded server-side, and any explicitly denied broker fails the whole request rather than being silently filtered.
- **Frontend presentation ownership:** task labels, local instruction templates, response contracts, locale-derived response language, user notes, safe rendering, and final prompt statistics stay in the browser. Web research is normalized off; response-language, render-mode, web, and compatibility-status controls are not exposed.
- **Final analysis model:** one custom select presents icon, localized name, and localized description. A synthetic **Data Snapshot** maps the domain's factual snapshot task to `data_only`; every real analysis maps to `full_prompt`.
- **Semantic composition remains modular:** the current public catalog contains 32 datasets and 17 analyses over 65 reusable components. Analyses compose the minimum required/optional datasets rather than routing through monolithic profiles, and `*.all_data` unions only canonical complete datasets while excluding focused projections/evidence that would duplicate them. See [[concepts/ai-export-catalog-granularity-and-composition]].
- **Contextual UI memory:** task, detail, mode, and raw notes draft persist under a client-session user ID plus `portfolio`, `broker:{id}`, `asset:{id}`, or `fx:{canonical_slug}`. Response language is always refreshed from the current locale. Snapshot may preserve hidden notes in memory, but normalization removes them from the exported prompt and clipboard. See [[decisions/ai-export-contextual-ui-memory]].
- **Portal and documentation boundary:** the panel is appended to `document.body`, fixed and viewport-positioned above chart controls, while the book link targets the current domain's English manual or the localized shared fallback.
- **Safe rendering boundary:** snapshot values and user notes are normalized to JSON-safe data, deterministically serialized as YAML, and placed in dynamically sized Markdown fences. Untrusted values are never interpolated as raw instructions.
- **Empty temporal rows are a presentation-only omission:** the public renderer removes a temporal row only when it contains no observation, economic value, flow, P&L, extrema, reconciliation, economic date, or explicit state. Observed zero remains data, diagnostics report detected/omitted/rendered row counts, and backend buckets and calculations remain intact.
- **Broker universes use explicit names:** `accessible_broker_count` is the authorization universe, `scoped_broker_count`/`broker_scope` are the effective calculation universe, `position_broker_count` counts Brokers with open positions at snapshot date, and `period_contributor_broker_count` counts period-performance contributors. The Entity Directory uses the effective prepared scope, including a scoped Broker with no current position rows.
- **Selected-period applicability:** task applicability is evaluated from the task's selected observations. Trailing technical observations may enrich market context, but an empty technical window must not invalidate a historical `drawdown_recovery` request that has two selected observations and a measurable prior maximum.
- **Transport-only clipboard fallback:** preserve the immediate `ClipboardItem(Promise<Blob>)` route when supported; otherwise prepare the same V2 export once and use `writeText`/`execCommand`. Clipboard capability never permits fallback to legacy builders or prompt logic.
- **Standalone/MCP-ready service:** `AiExportSnapshotService` has no FastAPI dependency. HTTP is one adapter; a future MCP server can invoke the same authenticated service and typed snapshots.
- **Hard cutover:** Dashboard, Broker Detail, Asset Detail, and FX Detail use only V2. Legacy builders and the four frontend technical engines were removed; parity fixtures remain only as an oracle.
- **No Portfolio Engine rewrite:** AI Export consumes engine-owned accounting and decomposition as-is. Snapshot-specific exposure views may use their own explicitly declared valuation basis and denominator.

## Consequences

- All four domains share one contract and orchestration model while retaining domain-specific assemblers.
- Backend snapshots are factual, versioned, deterministic, read-only, and usable without the UI; LibreFolio itself still calls no LLM.
- Frontend localization and prompt experimentation do not force financial API logic into presentation code, but any task change must be coordinated across backend profiles/schemas/assemblers, API generation, frontend catalog/templates, i18n, and tests.
- Browser-local draft continuity is deliberately not a backend setting or export-history feature. It is isolated by authenticated user and concrete UI context, validated against the current catalog, and safe to discard when stale.
- Hiding controls does not weaken the underlying contracts: response language remains deterministic from locale, web research remains false, catalog compatibility still fails closed, and clipboard compatibility remains an internal transport choice.
- Portalization prevents Asset/FX chart overlays from covering the panel and keeps the task select and book link keyboard-operable.
- Required source failures produce typed non-success responses; a missing optional indicator is omitted or marked unavailable without fabricating data.
- Dense Portfolio/Broker output remains explicit rather than silently truncated: the 20k/60k frontend warning stays in place and no automatic token cap or detail downgrade is introduced.
- The old [[decisions/ai-export-prompt-catalog]] remains historical context but is superseded as the production architecture.
- The composition boundary is technically sound but the current UI exposes many internal distinctions without visible granularity badges. In particular, Technical Summary, Asset Snapshot, Asset Comparison, and Technical differ materially in aggregate/per-Asset/history shape; “price” can mean position unit price, observed market price, or price history. These are documented interpretation findings, not an approved redesign. See [[concepts/ai-export-catalog-granularity-and-composition]].
- The live-E2E cash valuation-basis error established an explicit rule: never assert equality between metrics evaluated on different dates or denominators. See [[problems/ai-export-cash-fx-valuation-basis-mismatch]].
- Final review established two further boundary rules: presentation context cannot tighten task applicability ([[problems/ai-export-drawdown-selected-history-fallback]]), and transport compatibility cannot revive product-level legacy behavior ([[problems/ai-export-clipboard-fallback-unreachable]]).

## Validation / Success Criteria

- 54 unique profiles and complete catalog handshake.
- Four authenticated domain assemblers and typed 403/404/409/422/503 problems.
- No backend presentation text and no frontend financial or technical calculation.
- Safe adversarial serialization and clipboard behavior.
- No legacy production imports or runtime fallback.
- Browser E2E across all four surfaces.
- Canonical runner registration for AI Export service/schema/API tests and the explicit frontend AI Export+signal unit/E2E set, so aggregate suites execute them; unrelated pre-existing orphan tests remain outside this decision's scope.
- Manual desktop/mobile approval on 27 July 2026 covering Dashboard layout, custom task selection, chart-layer stacking, per-context memory, domain manual links, clipboard behavior, and representative prompts.
- On 3 August 2026 the project owner explicitly approved empty-temporal-row hardening, explicit Broker nomenclature, and `20260801T085820.657238Z` as final targeted evidence. The run passed 4/4 prompts with no failures, skips, or regressions; UI/probe matched 4/4, the secret scan passed, and source/production databases were unchanged.
- Applied Standard-policy run `20260803T164514.504966Z` passed 7/7 prompts with zero failures/public violations, UI/probe equivalence, a passed secret scan, and unchanged source/production databases.
- Catalog explanation run `20260804T085052.052297Z` generated and read five representative Portfolio prompts (Overview, Asset Snapshot, Asset Comparison, PAC, and Rebalancing): 5/5 passed with zero failures/public-output violations, UI/probe equivalence, a passed secret scan, and unchanged source/production databases. The accompanying report verified all 49 public choices against the current runtime declarations.
- Documentation closure is explicit: `mkdocs_src/docs/developer/test-walkthrough/api.md` lists AI Export API, service, probe, frontend-unit, and Playwright commands; `.github/copilot-instructions.md` states the AI Export product and backend/frontend boundary. User Guide IT/FR/ES translations remain deliberately deferred.

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
| Completed chain index | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/README.md` |
| Decision and implementation plan | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/plan-phase00AiExportBackendSnapshotImplementation.prompt.md` |
| Frozen task/profile contract | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/contract-phase00AiExportTaskProfiles.md` |
| Migration evidence | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/report-phase00AiExportMigrationEquivalence.md` |
| Final hardening approval and targeted evidence | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/report-phase00AiExportFinalHardeningAndDocumentationV1.md` |
| Applied density policy and validation evidence | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/report-phase00AiExportCrossDomainDensityAuditV1.md` |
| UI catalog explanation and prompt verification | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/report-phase00AiExportUiPromptCatalogExplainedV1.md` |
| Developer architecture | `mkdocs_src/docs/developer/architecture/patterns/ai_export_snapshot.md` |
| Composition and `all_data` semantics | `mkdocs_src/docs/developer/architecture/patterns/ai_export_composition.md` |
| Strict API schemas | `backend/app/schemas/ai_export.py` |
| Exact profile resolver | `backend/app/services/ai_export/resolver.py` |
| Standalone service | `backend/app/services/ai_export/service.py` |
| Domain assemblers | `backend/app/services/ai_export/assemblers/` |
| Frontend compatibility handshake | `frontend/src/lib/features/ai-export/catalog/compatibility.ts` |
| Analysis selection and Snapshot mapping | `frontend/src/lib/features/ai-export/AiExportOptionsPanel.svelte`, `frontend/src/lib/features/ai-export/aiExportOptions.ts` |
| Contextual UI memory | `frontend/src/lib/features/ai-export/aiExportMemory.ts`, `frontend/src/lib/stores/app/clientSession.ts` |
| Locale-derived response language | `frontend/src/lib/features/ai-export/AiExportMenuV2.svelte`, `frontend/src/lib/features/ai-export/ui.ts` |
| Body portal and focus/session ownership | `frontend/src/lib/features/ai-export/AiExportMenuV2.svelte` |
| Domain-aware manual link | `frontend/src/lib/features/ai-export/AiExportOptionsPanel.svelte`, `frontend/src/lib/components/ui/DocsLink.svelte` |
| Safe serialization | `frontend/src/lib/features/ai-export/serialization/` |
| Prompt renderer | `frontend/src/lib/features/ai-export/templates/promptRenderer.ts` |
| Empty temporal-row renderer and diagnostics | `frontend/src/lib/features/ai-export/templates/snapshotDataRenderer.ts` |
| Explicit Broker universe fields | `backend/app/services/ai_export/components/portfolio_financial.py`, `backend/app/services/ai_export/runtime_service.py` |
| Real-prompt evidence probe | `backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py` |
| Prompt-size warning boundary | `frontend/src/lib/features/ai-export/aiExportOptions.ts`, `frontend/src/lib/features/ai-export/AiExportOptionsPanel.svelte` |
| Clipboard orchestration | `frontend/src/lib/features/ai-export/aiExportClipboardV2.ts` |
| Drawdown applicability regression | `backend/app/services/ai_export/assemblers/asset.py`, `backend/test_scripts/test_services/test_ai_export_asset_fx.py` |
| Clipboard fallback regression | `frontend/src/lib/features/ai-export/__tests__/aiExportClipboardV2.test.ts` |
| Canonical test registration | `scripts/test_runner/_backend_services.py`, `scripts/test_runner/_backend_schemas.py`, `scripts/test_runner/_backend_api.py`, `scripts/test_runner/_frontend_ai_export.py`, `scripts/test_runner/_registry.py`, `scripts/test_runner/_suites.py` |
| Final UI unit coverage | `frontend/src/lib/features/ai-export/__tests__/aiExportMemory.test.ts`, `frontend/src/lib/features/ai-export/__tests__/aiExportOptions.test.ts`, `frontend/src/lib/features/ai-export/__tests__/aiExportUi.test.ts` |
| Final UI browser coverage | `frontend/e2e/ai-export.spec.ts` |
| AI Export test walkthrough | `mkdocs_src/docs/developer/test-walkthrough/api.md` |
| Repository product/boundary instructions | `.github/copilot-instructions.md` |
