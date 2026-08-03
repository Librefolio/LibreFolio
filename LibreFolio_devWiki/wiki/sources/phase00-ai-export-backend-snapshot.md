---
title: "Phase 0 — AI Export Backend Snapshot and Hard Cutover"
category: source
source_type: plan
date_ingested: 2026-07-26
date_updated: 2026-08-03
original_path: LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/plan-phase00AiExportBackendSnapshotImplementation.prompt.md
mkdocs: "developer/architecture/patterns/ai_export_snapshot.md"
tags: [phase0, ai-export, backend, frontend, snapshot, hard-cutover, mcp, security, ui-memory, accessibility, sampling, documentation]
related:
  - decisions/ai-export-versioned-snapshot-boundary
  - decisions/ai-export-contextual-ui-memory
  - decisions/ai-export-technical-series-and-density-contract
  - entities/ai-export-snapshot-service
  - problems/ai-export-cash-fx-valuation-basis-mismatch
  - problems/ai-export-drawdown-selected-history-fallback
  - problems/ai-export-clipboard-fallback-unreachable
  - decisions/ai-export-prompt-catalog
  - decisions/signal-backend-plugin-architecture
  - entities/portfolio-engine
  - decisions/fifo-runtime-decision
  - features/F-010
---

# Source: Phase 0 — AI Export Backend Snapshot and Hard Cutover

## Summary

The completed Phase 0 chain replaces the frontend-built AI Export with a typed, versioned backend snapshot platform spanning Portfolio, Asset, FX, and Broker. A frozen catalog composes 18 task specifications with three detail overlays into exactly 54 allow-listed profiles, while the frontend retains trusted prompt presentation, locale-derived response language, user notes, safe serialization, contextual draft memory, and clipboard UX. The four production surfaces made a hard cutover with no feature flag or runtime fallback, and the standalone service boundary is reusable by a future MCP transport without depending on FastAPI or browser state. Migration evidence distinguishes true legacy parity, deliberate semantic corrections, and greenfield contract conformance. After the 27 July desktop/mobile approval, the project owner closed the final hardening on 3 August: truly empty temporal rows are omitted without losing zero/economic state, Broker universes are named explicitly, Standard events use 21 calendar days plus minimum latest 10, and the final targeted/applied-policy evidence runs are recorded.

## Key Takeaways

- `AiExportSnapshotService` resolves exact versioned profiles, derives user/broker scope server-side, and dispatches to Portfolio, Broker, Asset, or FX assemblers.
- The catalog is fail-closed: any schema, profile, response-contract, support-flag, task, detail, scope, or target mismatch disables the choice or rejects the snapshot.
- Financial and technical facts are backend-owned; curated technical bundles reuse [[decisions/signal-backend-plugin-architecture]] and never auto-enrol new plugins.
- The final analysis control is a custom accessible select whose selected value and options show icon, localized name, and localized description.
- A synthetic **Data Snapshot** choice maps each domain to its factual snapshot task with `data_only`; every real analysis maps to `full_prompt`.
- Response language always follows the active UI locale. Render-mode, response-language, web-research, and compatibility-status controls are not exposed; web research is normalized off while compatibility still fails closed internally.
- [[decisions/ai-export-contextual-ui-memory]] records browser-local persistence by client-session user ID and concrete Portfolio/Broker/Asset/canonical-FX context. Snapshot preserves the hidden notes draft in memory but structurally excludes it from effective options and clipboard output.
- The options panel is portalized to `document.body` at a layer above chart controls, with fixed viewport-aware positioning, focus restoration, and keyboard-safe ownership of its portalized select.
- The book link is domain-aware for the four English manuals and uses the localized shared AI Export page as the IT/FR/ES fallback.
- The cutover removed the legacy frontend builders, custom serializer, duplicated technical-event calculations, and local EMA/RSI/MACD/Bollinger engines while preserving comparison, benchmark, Measure, and generic backend rendering.
- Live E2E exposed a false cash equality invariant: Portfolio Engine cash uses transaction-date FX, whereas native-currency exposure uses snapshot-date FX. The resolution is filed in [[problems/ai-export-cash-fx-valuation-basis-mismatch]] and deliberately leaves Portfolio Engine math unchanged.
- Final review decoupled Asset `drawdown_recovery` from a non-empty trailing technical window: market context prefers technical observations but falls back to selected observed history, while applicability remains two selected observations. See [[problems/ai-export-drawdown-selected-history-fallback]].
- Clipboard fallback is transport-only: retain the immediate `ClipboardItem(Promise<Blob>)` path when available; otherwise prepare V2 exactly once and write the same prompt through `writeText`/`execCommand`, never through legacy export logic. See [[problems/ai-export-clipboard-fallback-unreachable]].
- Canonical test-runner registration now includes the nine backend AI Export service files, AI Export schema/API tests, 16 explicit frontend AI Export+signal Vitest files, and the cross-domain E2E, so aggregate suites execute them. Unrelated pre-existing orphan tests remain outside this follow-up.
- The final 27 July gate completed the plan, approved representative desktop/mobile menu, layering, memory, manual-link, clipboard, and prompt behavior, and retained the chain in its existing archive rather than moving it into `RoadmapV4_UI/phases/`.
- The approved technical density contract keeps history at Compact 5, Standard 10,
  and Full all non-empty indicator rows. Event selection is Compact 7 calendar
  days/minimum latest 3, Standard 21 calendar days/minimum latest 10, and Full
  30 calendar days/minimum latest 20 per entity/annotation.
- Final public rendering omits only completely empty temporal rows. Observed zero,
  flow, P&L, extrema, reconciliation, economic dates, and explicit state remain;
  row diagnostics make the omission auditable.
- Broker terminology now distinguishes accessible, scoped, open-position, and
  period-contributor universes. The Entity Directory follows the effective scoped
  Brokers even when one has no current position row.
- The project owner designated `20260801T085820.657238Z` as final targeted
  evidence: 4/4 prompts, no failures/skips/regressions, UI/probe equivalence,
  passed secret scan, and unchanged source/production DBs.
- Applied-policy run `20260803T164514.504966Z` passed 7/7 prompts with zero
  failures/public violations, UI/probe equivalence, passed secret scan, and
  unchanged source/production DBs. Dense Portfolio/Broker cases can exceed 60k;
  the UI warning remains and no automatic cap is allowed.
- Documentation follow-ups are closed. `mkdocs_src/docs/developer/test-walkthrough/api.md`
  now lists `./dev.py test api ai-export`, `./dev.py test services ai-export`,
  `./dev.py test utils ai-export-probe`, `./dev.py test front-ai-export unit`,
  and the `panel`, `catalog`, `memory`, `contract`, `cutover`, and `all`
  Playwright actions.
  `.github/copilot-instructions.md` now states the AI Export product and
  backend/frontend boundary. User Guide translations for IT/FR/ES are explicitly
  deferred; English remains the current source.

## Source Chain

1. `README.md` — completed-chain index and archive-location decision.
2. `plan-phase00AiExportBackendSnapshotImplementation.prompt.md` — approved implementation plan, final UX rounds, manual approval, gates, and closure.
3. `contract-phase00AiExportTaskProfiles.md` — frozen 18-task, three-overlay, 54-profile contract.
4. `report-phase00AiExportMigrationEquivalence.md` — legacy parity, deliberate differences, greenfield conformance, and cutover evidence.
5. `report-phase00AiExportFinalHardeningAndDocumentationV1.md` — approved empty-row/Broker hardening, final targeted run, and documentation closure.
6. `report-phase00AiExportCrossDomainDensityAuditV1.md` — approved 21-day/minimum-10 Standard policy, counterfactuals, and applied-policy validation.

The original four journal files were untracked at final closure, so the registry records `untracked` rather than a git commit hash. The two follow-up reports are linked here as the current working-tree evidence for the 3 August closure.

## Wiki Pages Updated

- [[decisions/ai-export-versioned-snapshot-boundary]] — records the backend/frontend ownership boundary, exact profile catalog, fail-closed handshake, hard cutover, and MCP-ready service seam.
- [[decisions/ai-export-contextual-ui-memory]] — records user/context-keyed browser persistence, locale and web-control normalization, and the hidden-note/never-export invariant.
- [[decisions/ai-export-technical-series-and-density-contract]] — records the approved 5/10/all history policy, 7/3–21/10–30/20 event policy, evidence runs, and warning-without-cap boundary.
- [[entities/ai-export-snapshot-service]] — documents the service, resolver, assemblers, APIs, security scope, and frontend companion.
- [[problems/ai-export-cash-fx-valuation-basis-mismatch]] — preserves the live-E2E failure, root cause, and denominator correction.
- [[problems/ai-export-drawdown-selected-history-fallback]] — preserves the false 409 caused by coupling selected-period drawdown to trailing technical observations.
- [[problems/ai-export-clipboard-fallback-unreachable]] — preserves the unreachable non-modern clipboard transport and the activation-safe V2 fix.
- [[decisions/ai-export-prompt-catalog]] — marked as the historical frontend-only predecessor superseded by the Phase 0 snapshot platform.

## Related Architecture

- [[decisions/signal-backend-plugin-architecture]] — shared `SignalService` numerical truth and curated plugin bundles.
- [[entities/portfolio-engine]] — authoritative NAV, cash decomposition, allocations, valuation, and contribution math.
- [[decisions/fifo-runtime-decision]] and [[entities/lots-analysis-service]] — runtime FIFO summaries reused without persistence.
- [[domains/auth]], [[domains/brokers]], and [[features/F-010]] — authenticated user scope and broker-level access control.
- [[decisions/ai-export-contextual-ui-memory]] — authenticated client-session isolation for browser-local draft state.

## Source files

| Role | Path |
|------|------|
| Completed chain index | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/README.md` |
| Implementation plan | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/plan-phase00AiExportBackendSnapshotImplementation.prompt.md` |
| Frozen task/profile contract | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/contract-phase00AiExportTaskProfiles.md` |
| Migration equivalence report | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/report-phase00AiExportMigrationEquivalence.md` |
| Final hardening and documentation report | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/report-phase00AiExportFinalHardeningAndDocumentationV1.md` |
| Cross-domain density audit | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/report-phase00AiExportCrossDomainDensityAuditV1.md` |
| Developer architecture | `mkdocs_src/docs/developer/architecture/patterns/ai_export_snapshot.md` |
| API contract | `backend/app/schemas/ai_export.py` |
| Snapshot platform | `backend/app/services/ai_export/` |
| API endpoints | `backend/app/api/v1/ai_export.py` |
| Frontend boundary | `frontend/src/lib/features/ai-export/` |
| Custom options UI and domain manuals | `frontend/src/lib/features/ai-export/AiExportOptionsPanel.svelte`, `frontend/src/lib/components/ui/DocsLink.svelte` |
| Contextual memory and client-session scope | `frontend/src/lib/features/ai-export/aiExportMemory.ts`, `frontend/src/lib/stores/app/clientSession.ts` |
| Snapshot/full-prompt and locale normalization | `frontend/src/lib/features/ai-export/aiExportOptions.ts`, `frontend/src/lib/features/ai-export/ui.ts` |
| Body portal and panel session | `frontend/src/lib/features/ai-export/AiExportMenuV2.svelte` |
| Drawdown regression | `backend/app/services/ai_export/assemblers/asset.py`, `backend/test_scripts/test_services/test_ai_export_asset_fx.py` |
| Clipboard regression | `frontend/src/lib/features/ai-export/aiExportClipboardV2.ts`, `frontend/src/lib/features/ai-export/__tests__/aiExportClipboardV2.test.ts` |
| Canonical backend registration | `scripts/test_runner/_backend_services.py`, `scripts/test_runner/_backend_schemas.py`, `scripts/test_runner/_backend_api.py` |
| Canonical frontend registration | `scripts/test_runner/_frontend_ai_export.py`, `scripts/test_runner/_registry.py`, `scripts/test_runner/_suites.py` |
| Browser E2E | `frontend/e2e/ai-export.spec.ts` |
| Applied event/history policy | `backend/app/services/ai_export/temporal/policy.py` |
| Empty temporal-row renderer | `frontend/src/lib/features/ai-export/templates/snapshotDataRenderer.ts` |
| Explicit Broker universe fields | `backend/app/services/ai_export/components/portfolio_financial.py`, `backend/app/services/ai_export/runtime_service.py` |
| Real-prompt validation probe | `backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py` |
| Prompt warning thresholds | `frontend/src/lib/features/ai-export/aiExportOptions.ts`, `frontend/src/lib/features/ai-export/AiExportOptionsPanel.svelte` |
| AI Export test commands | `mkdocs_src/docs/developer/test-walkthrough/api.md` |
| Repository product/boundary instructions | `.github/copilot-instructions.md` |
| English domain manuals | `mkdocs_src/docs/user/dashboard/ai-export.en.md`, `mkdocs_src/docs/user/brokers/ai-export.en.md`, `mkdocs_src/docs/user/assets/detail/ai-export.en.md`, `mkdocs_src/docs/user/fx/detail/ai-export.en.md` |
| Localized shared manual fallback | `mkdocs_src/docs/user/ai-export/index.it.md`, `mkdocs_src/docs/user/ai-export/index.fr.md`, `mkdocs_src/docs/user/ai-export/index.es.md` |
