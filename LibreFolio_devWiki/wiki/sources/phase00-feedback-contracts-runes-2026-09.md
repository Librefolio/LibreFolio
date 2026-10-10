---
title: "Phase 0 / 11 — feedback group B: API contracts and Runes components (SP04–SP05), FX creation sync, entity links in toasts"
category: source
source_type: plan
date_ingested: 2026-10-09
original_path: LibreFolio_developer_journal/Release_2/phases/11_feedbackContractsRunes/
tags: [phase0, release2, api-contract, svelte5, runes, fx, toasts, ai-export, signals, workstream-b]
related:
  - features/F-016
  - concepts/svelte5-runes
  - decisions/broker-last-owner-guard
  - concepts/discard-the-answer-not-the-question
  - sources/phase00-fx-dashboard-sync-2026-10
---

# Source: Phase 0 / 11 — feedback group B

## Summary

Two plans, integrated by merge `514582a47` (2026-09-10; checkpoint `74bfd9cf0`, reconciled with the runtime lanes
in `d9e8f6d3b`) plus the compact-toast fix `00c469c3f`, archived on 2026-10-09. Group B of the Release 2 feedback
tightened several API contracts and migrated three settings components to Svelte 5 Runes; its bug-fix round (R1)
made FX pair creation close at once and sync in background, and put safe entity links in success toasts.

## Key takeaways

- **B02 — asserts are not validation**: 17 AI Export structural guards were `assert`s, which `python -O` strips; they
  became typed raises (`TypeError`/`ValueError`, e.g. `backend/app/services/ai_export/temporal/plan.py`). They check
  in-memory catalogues, not the database.
- **B03 — FX routes say what they are**: route responses gained a required, response-only `is_chain` and an ordered
  `providers_used` (`backend/app/schemas/fx.py`); nothing is persisted, so no migration. B04 regenerated the client
  and typed the FX consumers.
- **B05** — `SignalResult` validation became ordered, declarative rule tables with named predicates, with identical
  behaviour (`backend/app/schemas/signals.py`).
- **B06–B08** — `PreferencesTab`, `GlobalSettingsTab`, `BrokerSharingPanel` migrated to Runes with no UI change
  ([[concepts/svelte5-runes]]); B01 wrote characterisation tests first, independent of the new code.
- **R1-01** — locking Global Settings with unsaved edits opens the amber `ConfirmModal` instead of the browser's
  `confirm()`; Cancel/Escape keeps the draft.
- **R1-02** — tests pin that when the last OWNER leaves a broker that still has an EDITOR and a VIEWER, the broker and
  its grants are physically deleted (`ON DELETE CASCADE`); no policy change ([[decisions/broker-last-owner-guard]]).
- **R1-03 — FX pair creation**: the modal awaited the sync and read `result[0]` by position; it now closes at once,
  syncs in background and matches results **by pair** (`fxCreationSync.ts`) — see [[features/F-016]]. Auto-sync for
  direct and multi-hop real-provider routes, never for MANUAL routes or on edit. The background sync is a browser
  promise; closing the tab is not covered (a durable backend job was rejected).
- **R1-04 — entity links in toasts**: `entityDetailLinkHtml()` (`frontend/src/lib/utils/core/entityLink.ts`) builds
  safe internal links (escaped label, no raw URL) to `/fx/<pair>` or `/assets/<id>`. Swipe-to-dismiss swallowed the
  click on a link: `ToastContainer.svelte` now ignores pointer-downs that start on `button, a`. Gotcha: a linked
  toast must not claim "synced" before the request has finished.
- **Compact toast row**: in linked FX success/partial toasts the flagged pair, the `fetched↓ changed Δ` counters and
  the provider badges share one line (`syncToastHelpers.ts`); unlinked and MANUAL/skipped toasts keep three rows.
- Only the global asset page gets creation links; contextual creation (wizard, transaction form, import) gets none.

## Residuals (backlog 38)

O-19 — FX chains: the `leg_rates` key lacks the provider, inverted ends. O-20 — a duplicate sync when an asset is
created from the Assets page.

## Wiki pages updated

- [[features/F-016]] — creation sync, entity links.
- [[decisions/broker-last-owner-guard]] — R1-02 pinned.

## Source files

| Role | Path |
|------|------|
| Plan (B00–B10) | `LibreFolio_developer_journal/Release_2/phases/11_feedbackContractsRunes/plan-phase00FeedbackContractsRunes.prompt.md` |
| Plan (R1-01…06) | `LibreFolio_developer_journal/Release_2/phases/11_feedbackContractsRunes/plan-phase00FeedbackContractsRunesBugfixRound1.prompt.md` |
| FX route schema (`is_chain`, `providers_used`) | `backend/app/schemas/fx.py` |
| Signal result rule tables | `backend/app/schemas/signals.py` |
| AI Export typed guards (example) | `backend/app/services/ai_export/temporal/plan.py` |
| FX creation sync | `frontend/src/lib/services/fxCreationSync.ts` |
| Entity links | `frontend/src/lib/utils/core/entityLink.ts` |
| Toast container (links survive swipe) | `frontend/src/lib/components/ui/feedback/ToastContainer.svelte` |
| Sync toasts (compact row) | `frontend/src/lib/utils/sync/syncToastHelpers.ts` |
