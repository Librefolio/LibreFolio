---
title: "AI Export drafts persist per authenticated user and UI context"
category: decision
status: resolved
date: 2026-07-27
mkdocs: "developer/architecture/patterns/ai_export_snapshot.md"
tags: [frontend, ai-export, ui-memory, local-storage, auth, privacy, ux]
related:
  - sources/phase00-ai-export-backend-snapshot
  - decisions/ai-export-versioned-snapshot-boundary
  - entities/ai-export-snapshot-service
  - problems/ai-export-clipboard-fallback-unreachable
  - domains/auth
---

# Decision: AI Export drafts persist per authenticated user and UI context

## Context

The first Phase 0 options panel treated closing a modified draft as a discard event and asked for confirmation. Manual desktop/mobile review found that behavior disruptive: task, detail, and notes are working context that users expect to recover when they reopen AI Export. A single browser-global draft was unsafe, however, because the four surfaces represent different entities and the SPA can survive logout/login transitions between users. Data Snapshot also hides the notes editor, so persistence had to retain an analysis draft without allowing those hidden notes into a data-only export.

## Options Considered

1. **Keep drafts only while the panel is open and confirm discard on close** — explicit, but interrupts normal navigation and loses useful context.
2. **Use one browser-global AI Export draft** — simple, but leaks choices between Portfolio, Broker, Asset, and FX contexts and risks cross-account reuse.
3. **Persist drafts in backend user settings** — portable across devices, but turns transient prompt composition into a server contract, adds synchronization/privacy scope, and was unnecessary for Phase 0.
4. **Persist browser-local drafts by authenticated user and concrete UI context** — preserves continuity while keeping prompt presentation state on the frontend. **Chosen.**

## Decision

- AI Export stores a versioned, strictly validated draft containing task, detail level, effective render mode, and the raw notes draft.
- Storage keys are namespaced with the current client-session user ID and one context key:
  - `portfolio`;
  - `broker:{broker_id}`;
  - `asset:{asset_id}`;
  - `fx:{canonical_slug}`.
- The persistent key shape is `lf_{userId}_ai_export_v1_{encodedContext}`. An in-memory cache mirrors valid entries; account transitions clear that cache through the shared client-session reset boundary. Browser storage remains user-namespaced rather than being shared between accounts.
- If the user is unauthenticated, storage is unavailable, JSON/schema validation fails, or a stored task/detail/mode is no longer applicable to the current catalog, the panel uses safe defaults. Malformed or obsolete entries are removed. If `localStorage` rejects writes, the draft can still survive for the current SPA session in memory.
- Draft changes persist immediately; closing the panel no longer opens a discard confirmation.
- Response language is never trusted from memory. It is always re-derived from the active UI locale when the draft is loaded or exported. Web research is always normalized to `false` and is not exposed as a control.
- The synthetic **Data Snapshot** choice stores/restores the domain's snapshot task with `data_only`; every real analysis uses `full_prompt`.
- The raw notes draft is preserved even while Snapshot hides the editor. Before export, `data_only` normalization removes notes from the effective options, fingerprint, rendered prompt, and clipboard. Switching back to an analysis restores the draft without having exported it.
- A panel session captures its context key, so a late save from an old Asset/FX route cannot overwrite the newly active context.

## Consequences

- Portfolio and each Broker, Asset, and canonical FX pair reopen with their own last task, detail, mode, and notes.
- Users can close by trigger, Escape, outside click, or navigation without a destructive confirmation.
- Drafts are device/browser-local rather than a cross-device account preference.
- Authentication changes cannot reuse another user's in-memory draft, and persistent entries are separated by user ID.
- Catalog/version drift fails closed to defaults instead of reviving an unsupported selection.
- Snapshot privacy is stronger than visual hiding alone: hidden notes remain useful UI memory but are structurally absent from exported data.

## Validation / Success Criteria

- Unit coverage exercises all four context-key forms, two authenticated users, storage reload, malformed/cross-domain values, Snapshot/full-prompt restoration, late old-context saves, locale replacement, and forced-disabled web research.
- Browser E2E verifies Dashboard draft restoration without a confirm modal, hidden-note exclusion from Snapshot clipboard, per-Asset/per-canonical-FX isolation, and restoration after route changes.
- The project owner approved the final desktop and mobile behavior on 27 July 2026.

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
| Panel session, persistence, locale, and portal ownership | `frontend/src/lib/features/ai-export/AiExportMenuV2.svelte` |
| Snapshot/analysis normalization and note exclusion | `frontend/src/lib/features/ai-export/aiExportOptions.ts` |
| Client-session user boundary | `frontend/src/lib/stores/app/clientSession.ts` |
| Authentication transitions | `frontend/src/lib/stores/app/auth.ts` |
| Portfolio context integration | `frontend/src/routes/(app)/dashboard/+page.svelte` |
| Broker context integration | `frontend/src/routes/(app)/brokers/[id]/+page.svelte` |
| Asset context integration | `frontend/src/routes/(app)/assets/[id]/+page.svelte` |
| Canonical FX context integration | `frontend/src/routes/(app)/fx/[pair]/+page.svelte` |
| Memory unit coverage | `frontend/src/lib/features/ai-export/__tests__/aiExportMemory.test.ts` |
| Option/privacy unit coverage | `frontend/src/lib/features/ai-export/__tests__/aiExportOptions.test.ts` |
| Cross-surface browser coverage | `frontend/e2e/ai-export.spec.ts` |
| Developer architecture | `mkdocs_src/docs/developer/architecture/patterns/ai_export_snapshot.md` |
