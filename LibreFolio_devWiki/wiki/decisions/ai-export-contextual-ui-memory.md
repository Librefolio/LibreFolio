---
title: "AI Export drafts persist per authenticated user and UI context"
category: decision
status: resolved
date: 2026-07-27
updated: 2026-08-03
mkdocs: "developer/architecture/patterns/ai_export_snapshot.md"
tags: [frontend, ai-export, ui-memory, local-storage, auth, privacy, ux, async, e2e]
related:
  - sources/phase00-ai-export-backend-snapshot
  - decisions/ai-export-versioned-snapshot-boundary
  - entities/ai-export-snapshot-service
  - problems/ai-export-clipboard-fallback-unreachable
  - domains/auth
---

# Decision: AI Export drafts persist per authenticated user and UI context

## Context

The first Phase 0 options panel treated closing a modified draft as a discard event and asked for confirmation. Manual desktop/mobile review found that behavior disruptive: selection, detail, period, and notes are working context that users expect to recover when they reopen AI Export. A single browser-global draft was unsafe because the four surfaces represent different entities and the SPA can survive logout/login transitions between users.

The V2 cutover exposed two additional races. Client-session identity and the catalog resolve asynchronously, so a one-shot load during component creation could see an anonymous/empty state and fail to hydrate a valid `localStorage` draft after a fresh page load or navigation. Snapshot preparation also outlives its initiating UI context unless late results are explicitly invalidated: navigation, logout, selection changes, panel close, or component destruction could otherwise persist or copy stale output. Dataset selections hide Analysis notes, so visual hiding also had to remain separate from the effective request and prompt contract.

## Options Considered

1. **Keep drafts only while the panel is open and confirm discard on close** — explicit, but interrupts normal navigation and loses useful context.
2. **Use one browser-global AI Export draft** — simple, but leaks choices between Portfolio, Broker, Asset, and FX contexts and risks cross-account reuse.
3. **Persist drafts in backend user settings** — portable across devices, but turns transient prompt composition into a server contract, adds synchronization/privacy scope, and was unnecessary for Phase 0.
4. **Persist browser-local drafts by authenticated user and concrete UI context, rehydrate reactively, and bind async work to an invalidatable preparation context** — preserves continuity while preventing cross-user/context reuse and stale side effects. **Chosen.**

## Decision

### Reactive identity-bound memory

- AI Export stores a versioned, strictly validated V2 draft containing selection kind/ID, detail level, period, the raw Analysis note draft, and the accepted Copy Anyway fingerprint.
- Storage keys are namespaced with the resolved client-session user ID and one context key:
  - `portfolio`;
  - `broker:{broker_id}`;
  - `asset:{asset_id}`;
  - `fx:{canonical_slug}`.
- The persistent key shape is `lf_{userId}_ai_export_v2_{encodedContext}`. An in-memory cache mirrors valid entries; account transitions clear it through the shared client-session reset boundary.
- The menu subscribes to the client-session user store. When async identity first resolves or later changes, it reloads the active memory key instead of treating the initial anonymous fallback as final. Catalog resolution/reload also rehydrates without deleting a valid draft merely because compatibility is temporarily empty.
- If the user is unauthenticated, storage is unavailable, JSON/schema validation fails, or a stored selection/detail is no longer applicable, the panel uses safe defaults. Malformed or obsolete entries are removed. If `localStorage` rejects writes, valid state can still survive for the current SPA session in memory.
- Draft changes persist immediately; closing the panel has no destructive confirmation. Response language is never trusted from memory and is re-derived from the active UI locale.

### Raw notes are memory, not always export options

- The raw Analysis note draft is held as `userNotesDraft`, separately from the current effective `AiExportOptionsSelection.userNotes`.
- Switching to a Dataset hides but preserves the raw note draft. Switching back to a note-capable Analysis restores it.
- Dataset selections and Analysis entries with `supports_user_notes=false` receive no notes in their effective options, options fingerprint, request, rendered prompt, or clipboard output.

### In-flight preparation is context-bound

- Every preparation captures a monotonic context epoch, unique operation ID, client-session generation and user ID, active memory key, and effective options fingerprint.
- Navigation/context-key changes, logout or user changes, option changes, panel close, catalog/user reload, and component destruction invalidate the captured context. Reload/close paths also clear pending state and reset loading immediately.
- A late result is accepted only while every captured field is still current. Guards run before clipboard writing starts, again after the async clipboard write, and before persistence, callbacks, or panel completion. Stale successes and errors therefore become inert.

### E2E and runner cutover

- The former monolithic `frontend/e2e/ai-export.spec.ts` was removed. Coverage is split into panel, catalog, memory, and request/clipboard contract specs with shared helpers.
- The test runner exposes focused `panel`, `catalog`, `memory`, and `contract` actions. The `cutover` compatibility alias runs all four concern specs, while `all` runs unit coverage followed by the complete E2E set.

## Consequences

- Portfolio and each Broker, Asset, and canonical FX pair reopen with their own last selection, detail, period, and notes after fresh loads and navigation, even when identity resolves after the component's first render.
- Users can close by trigger, Escape, outside click, or navigation without a destructive confirmation.
- Drafts are device/browser-local rather than a cross-device account preference.
- Authentication changes cannot reuse another user's in-memory draft, and persistent entries are separated by user ID.
- Catalog/version drift fails closed to defaults instead of reviving an unsupported selection.
- Dataset and non-note-capable Analysis privacy is stronger than visual hiding alone: hidden notes remain useful UI memory but are structurally absent from export inputs and outputs.
- Slow snapshot or clipboard work cannot leak across routes, accounts, selections, closed panels, or destroyed components.
- Concern-based E2E files make failures and focused reruns easier to localize without weakening the canonical cutover gate.

## Validation / Success Criteria

- Unit coverage exercises V2 storage, hidden-note preservation with note-free Dataset fingerprints, delayed catalog hydration, stale schema/selection removal, async client-session publication, and session-generation invalidation.
- Browser E2E verifies per-user and Portfolio/Broker/Asset/canonical-FX isolation, navigation restoration, Dataset note exclusion, current request/clipboard contracts, and dropping a preparation after its panel context closes.
- Final canonical gate on 3 August 2026: **214 unit tests passed** and **32 Playwright E2E tests passed across desktop/mobile**.

## Links

- [[sources/phase00-ai-export-backend-snapshot]]
- [[decisions/ai-export-versioned-snapshot-boundary]]
- [[entities/ai-export-snapshot-service]]
- [[problems/ai-export-clipboard-fallback-unreachable]]
- [[domains/auth]]

## Source files

| Role | Path |
|------|------|
| Final plan and approval record | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/plan-phase00AiExportBackendSnapshotImplementation.prompt.md` |
| Completed chain index | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/README.md` |
| Versioned contextual storage | `frontend/src/lib/features/ai-export/aiExportMemory.ts` |
| Reactive hydration and stale-operation guards | `frontend/src/lib/features/ai-export/AiExportMenu.svelte` |
| Raw note draft / effective option separation | `frontend/src/lib/features/ai-export/AiExportOptionsPanel.svelte` |
| Dataset/Analysis normalization and fingerprint exclusion | `frontend/src/lib/features/ai-export/aiExportOptions.ts` |
| Prompt note capability boundary | `frontend/src/lib/features/ai-export/templates/promptRenderer.ts` |
| Client-session user boundary | `frontend/src/lib/stores/app/clientSession.ts` |
| Authentication transitions | `frontend/src/lib/stores/app/auth.ts` |
| Portfolio context integration | `frontend/src/routes/(app)/dashboard/+page.svelte` |
| Broker context integration | `frontend/src/routes/(app)/brokers/[id]/+page.svelte` |
| Asset context integration | `frontend/src/routes/(app)/assets/[id]/+page.svelte` |
| Canonical FX context integration | `frontend/src/routes/(app)/fx/[pair]/+page.svelte` |
| Memory unit coverage | `frontend/src/lib/features/ai-export/__tests__/aiExportMemory.test.ts` |
| Option/privacy unit coverage | `frontend/src/lib/features/ai-export/__tests__/aiExportOptions.test.ts` |
| Client-session unit coverage | `frontend/src/lib/stores/app/clientSession.test.ts` |
| Panel and stale-preparation E2E | `frontend/e2e/ai-export/ai-export-panel.spec.ts` |
| Catalog E2E | `frontend/e2e/ai-export/ai-export-catalog.spec.ts` |
| Contextual memory E2E | `frontend/e2e/ai-export/ai-export-memory.spec.ts` |
| Request/clipboard contract E2E | `frontend/e2e/ai-export/ai-export-contract.spec.ts` |
| Shared E2E helpers | `frontend/e2e/ai-export/helpers.ts` |
| Focused actions and cutover alias | `scripts/test_runner/_frontend_ai_export.py` |
| Developer architecture | `mkdocs_src/docs/developer/architecture/patterns/ai_export_snapshot.md` |
