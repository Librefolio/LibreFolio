---
title: "Phase 0 / 14 — urgent import feedback: incremental plan and five rounds (review, share, social, boundaries, GHCR auth)"
category: source
source_type: plan
date_ingested: 2026-10-09
original_path: LibreFolio_developer_journal/Release_2/phases/14_feedbackImportUrgent/
tags: [phase0, release2, import-wizard, assets, classification, social-share, ghcr, integration, workstream-e]
related:
  - problems/asset-classification-wiped-by-partial-save
  - features/F-104
  - problems/ghcr-browser-cors-auth-flow
  - entities/import-wizard-modal
  - concepts/import-todo-signals
---

# Source: Phase 0 / 14 — urgent import feedback

## Summary

Eight files (an incremental plan, five rounds, a review checklist and an integration manifest), shipped in
`ef722b552` (2026-09-09, closed 2026-09-10) and archived on 2026-10-09. Group E fixed the import defects users hit
first, added a "recommend LibreFolio" share feature, and replaced the browser-side GHCR probe of the update check.

## Key takeaways

- **E1/E2 — classification wiped on save** (form built from a summary; `exclude_none` collapsing an explicit
  `null`): [[problems/asset-classification-wiped-by-partial-save]].
- **Currency confirmation unclickable**: it opened at z-index 50 under the asset inspector (90). Nested dialogs are now
  stacked relative to their parent (`zIndex + 20`, as in `AssetModal.svelte`).
- **E3** — the hidden FX destination broker was unset when the broker was chosen before the FX layout; it is now
  derived from the source broker (the two legs may legitimately carry different dates: `to.date || from.date`).
- **E4** — asset matching had no backend bug: the frontend overrode the backend's ambiguity rule and was realigned.
- **E5** — creating a broker with an existing name answers **409** with a recovery hint (`backend/app/api/v1/brokers.py`).
- **E7/E8** — the bulk shortfall warning points to every affected row; rows are sorted chronologically for display.
- **E9** — the "up to date" toast shows the remote version, not the installed one.
- **Rounds 2–4 — share LibreFolio**: [[features/F-104]] (copy-and-go, five platforms, platform boundaries).
- **Round 5 — GHCR**: [[problems/ghcr-browser-cors-auth-flow]] (filed 2026-09-09).
- **Integration rules** recorded by the manifest, still the practice of the release coordinator: integrate per file
  and per responsibility, never overwrite whole files on top of another group's work; coordinator-owned registers
  (feedback backlog, TODO files, wiki notes) are reconciled by the coordinator, not copied; never commit databases,
  WAL files, uploads, logs, private CSVs or regenerable outputs (build, generated client, MkDocs site); record the
  integration SHA and the archive status separately.

## Residuals

A pre-existing duplicate sync when an asset is created from the Assets page — now backlog O-20.

## Wiki pages updated

- [[problems/asset-classification-wiped-by-partial-save]], [[features/F-104]] — new.
- [[problems/ghcr-browser-cors-auth-flow]] — unchanged (already cites the archived Round 5 plan).

## Source files

| Role | Path |
|------|------|
| Incremental plan (E1–E9) | `LibreFolio_developer_journal/Release_2/phases/14_feedbackImportUrgent/plan-phase00FeedbackImportUrgent.prompt.md` |
| Round 1 — review | `LibreFolio_developer_journal/Release_2/phases/14_feedbackImportUrgent/plan-phase00FeedbackImportUrgentRound1-Review.prompt.md` |
| Round 2 — share | `LibreFolio_developer_journal/Release_2/phases/14_feedbackImportUrgent/plan-phase00FeedbackImportUrgentRound2-Share.prompt.md` |
| Round 3 — social feedback | `LibreFolio_developer_journal/Release_2/phases/14_feedbackImportUrgent/plan-phase00FeedbackImportUrgentRound3-SocialFeedback.prompt.md` |
| Round 4 — social boundaries | `LibreFolio_developer_journal/Release_2/phases/14_feedbackImportUrgent/plan-phase00FeedbackImportUrgentRound4-SocialBoundaries.prompt.md` |
| Round 5 — GHCR auth | `LibreFolio_developer_journal/Release_2/phases/14_feedbackImportUrgent/plan-phase00FeedbackImportUrgentRound5-GHCRAuth.prompt.md` |
| Integration manifest | `LibreFolio_developer_journal/Release_2/phases/14_feedbackImportUrgent/manifest-integrazione-E.md` |
| Asset PATCH | `backend/app/services/asset_sources/crud.py` |
| Broker 409 | `backend/app/api/v1/brokers.py` |
| Share feature | `frontend/src/lib/components/support/SocialShareModal.svelte` |
