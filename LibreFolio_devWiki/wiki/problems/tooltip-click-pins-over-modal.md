---
title: "A button inside Tooltip pins its hint for 30 s over the modal it opens"
category: problem
status: resolved
date: 2026-09-24
tags: [frontend, tooltip, modal, ux]
related: [datatable-tooltip-custom-cell]
---

# Problem: A button inside Tooltip pins its hint for 30 s over the modal it opens

## Symptom
The toolbar's "Sync selection" button of the Asset Global lab, wrapped in `Tooltip.svelte` (`interactiveChild`),
opens the sync modal. A click on it would have left its hint floating over the modal.

## Root Cause
`Tooltip.svelte` treats a click on its trigger wrapper as a *pin*: a pinned tooltip stays open while the pointer is
over the trigger or the tooltip, then for `PINNED_LEAVE_GRACE_MS` (30 s). The wrapper listens to `click`, so the
child button's click bubbles up to it and pins the hint.

## Solution
The wrapped buttons stop the click before the wrapper: `onclick={(event) => { event.stopPropagation(); … }}`. The hint
still shows on hover. Applied to the lab's sync, reload and "+" buttons.

A chip's remove button (×) inside a chip-wide tooltip does the same, so removing an asset does not pin the reason.

## Prevention
When wrapping an **action** in `Tooltip`, decide whether a click should pin the hint. For a button that opens a modal
or a menu, it should not: stop propagation in its handler.

## Impact
Found while writing the feature (F-3b V1), before any review. No user impact.

## Source files
| Role | Path |
|------|------|
| Tooltip (pin on click) | `frontend/src/lib/components/ui/feedback/Tooltip.svelte` |
| Toolbar buttons | `frontend/src/routes/(app)/assets/+page.svelte` |
| "+" trigger | `frontend/src/lib/components/risk/LabAssetPicker.svelte` |
| Chip remove button | `frontend/src/lib/components/risk/AssetSetRiskPanel.svelte` |
