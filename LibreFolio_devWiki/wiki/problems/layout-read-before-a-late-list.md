---
title: "A layout read before a late list arrives"
category: problem
date: 2026-11-19
status: resolved
tags: [testing, e2e, playwright, layout, published-state]
related:
  - entities/asset-profile-enrichers
---

# A layout read before a late list arrives

## Summary

`asset-mobile-layout` failed at 360×640 («positive control B hits nothing of the form») in the whole spec and passed
alone. Lane 76's triage found two causes that hid each other:

- a probe at **one fixed point**, which fell in the 20 px gap between two blocks of the form;
- a layout read **before the provider chips arrived**. Those chips come from `GET /assets/provider` after the window
  opens, and push the form down by 102 px.

Alone, the server was cold, the chips were late, and the point landed on a field. In the whole spec they were already
there, and the point fell in the gap.

## Details

- **The stillness check was blind to the list.** `settleModal` declared the window still after two equal frames. A
  list that arrives later is not motion, so it was never waited for. The modal published no state for it (rule 4 of
  the frontend testing rules: a missing state is the product's to publish).
- **The fix (lane 68, MOB).** `AssetSearchAutocomplete` publishes `data-providers` (`pending`, `ready`, `failed`) on
  its root, and `settleModal` counts frames only when no search is `pending`.
  - Positive control B probes a column of points down the form's window and wants at least one hit.
  - Red first: once the list was waited for, the test alone became red like the whole spec, then green with the
    column.
- **The lesson.** A «two equal frames» settle does not cover data still loading. Publish the load, wait for it, and
  never prove "I can see X" with one point.

## Source files

| Role | Path |
|------|------|
| The published state | `frontend/src/lib/features/assets/AssetSearchAutocomplete.svelte` |
| The settle and the probe | `frontend/e2e/assets/asset-mobile-layout.spec.ts` |
| Its unit tests | `frontend/src/lib/features/assets/AssetSearchAutocomplete.test.ts` |
