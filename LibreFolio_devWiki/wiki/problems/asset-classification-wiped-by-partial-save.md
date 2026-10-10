---
title: "Saving an asset from the import wizard wiped its sector and geography"
category: problem
status: resolved
date: 2026-09-10
tags: [backend, frontend, assets, classification, pydantic, patch-semantics, import-wizard, exclude-none]
related: [entities/import-wizard-modal, features/F-024, features/F-029, decisions/auto-populate-removal, sources/phase00-feedback-import-urgent-2026-09]
---

# Problem: a save that only touched one field cleared the classification

## Symptom

Editing an asset from the import wizard (E1/E2 of the urgent import feedback, September 2026) and saving — even
without touching its classification — erased the asset's sector and geographic distribution.

## Root cause

Two independent faults, each enough on its own:

1. **The form started from a summary.** The wizard's edit form was filled from the `/assets/query` summary, which
   carries no classification; saving sent the whole form back, so `classification_params: null` — which the PATCH
   contract reads as "set the column to NULL".
2. **`exclude_none` on a nested model collapses intent.** Serialising the nested classification with
   `exclude_none=True` turned `{sector_area: null}` into `{}`, and the service treated an empty classification as
   "clear everything". A field explicitly set to `null` and a field never mentioned became indistinguishable.

## Solution

- The edit form loads the asset's **full** edit data, and the frontend PATCHes **only the blocks that changed**.
- The bulk PATCH distinguishes *absent* from *present*: `classification_params` is applied only when it is in the
  patch's `model_fields_set`, and then dumped with `exclude_unset=True` — only the nested fields the caller actually
  supplied (`backend/app/services/asset_sources/crud.py`, the patch loop).

## Prevention

- In a PATCH, "absent" (`model_fields_set`) and "null" are different requests; `exclude_none` erases the difference,
  `exclude_unset` keeps it.
- An edit form must start from the full resource, never from a list summary.
- Note for readers of the code: the method docstring above the loop still says `model_dump_json(exclude_none=True)`;
  the code uses `exclude_unset=True` (docstring drift, reported 2026-10-09).

## Impact

Silent loss of user-entered classification (sector and geography weights), visible only later in the allocation
charts.

## Source files

| Role | Path |
|------|------|
| Bulk asset PATCH (`model_fields_set`, `exclude_unset`) | `backend/app/services/asset_sources/crud.py` |
| Asset patch schema | `backend/app/schemas/assets.py` |
| Asset edit modal used by the wizard | `frontend/src/lib/components/assets/AssetModal.svelte` |
| Plan (E1/E2) | `LibreFolio_developer_journal/Release_2/phases/14_feedbackImportUrgent/plan-phase00FeedbackImportUrgent.prompt.md` |
