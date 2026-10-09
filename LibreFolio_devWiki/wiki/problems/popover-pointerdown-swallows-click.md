---
title: "A popover that closes on pointerdown swallows the next click"
category: problem
status: resolved
date: 2026-09-25
tags: [frontend, svelte, popover, events, ux]
related: [tooltip-click-pins-over-modal, lab-eligibility-from-risk-engine]
---

# Problem: A popover that closes on pointerdown swallows the next click

## Symptom
In the Asset Global lab's "+" picker, with the Type filter menu open and reaching below the viewport, and the page
scrolled into it, one press on the Currency menu button did nothing: the Type menu closed, the page jumped, and the
Currency menu stayed shut. A second press was needed. Found by test-author during F-6 (24/09), from the browser's
event log: `mousedown` on `risk-filter-currency-button`, then `mouseup` on another element.

## Root Cause
`LabPopover` closed on a `pointerdown` outside its root. The panel disappeared **between the press and the release**:
the page got shorter, the browser pulled the scroll back, and the release landed on whatever slid under the pointer.
A `click` fires only on the common ancestor of the press and release targets, so the button that was pressed never
received it. The deterministic test measured a 136 px jump, from scrollY 270 to 134, with the release on the card
(`risk-asset-set-controls`).

## Solution
Close on the **completed click**, not on the press (`LabPopover.svelte`):
- `onpointerdowncapture` only records whether the press began inside the popover;
- `onclickcapture` closes when the click lands outside, unless its press began inside (a text selection dragged out
  of the search box is not an outside click);
- a keyboard click (`event.detail === 0`) completes no press, so it ignores that flag;
- both listeners are in the capture phase, so a `stopPropagation` in the pressed button (the "+" trigger has one)
  cannot hide the click from an open menu.

Test first: `risk-lab.spec.ts`, "one press on the currency menu opens it, even with the type menu hanging below the
fold and the page scrolled into it". It was red twice on the old code and is green after the fix. Before the press it
checks that the scenario really exists (the menu overflows, the page is scrolled), so a later redesign that removes
the scenario fails loudly instead of passing without testing anything.

## Prevention
- Close "click outside" UI on `click`, not on `pointerdown` or `mousedown`, whenever closing changes the layout.
- If a press must close something at once (for example a context menu), make sure the removal cannot move the element
  under the pointer: fixed positioning, or no change in page height.

## Impact
One extra press when switching filter menus in an overflowing layout. No data impact.

## Source files
| Role | Path |
|------|------|
| Popover shell (LabPopover replaced 2026-10-05; the click-capture rule lives here now) | `frontend/src/lib/components/ui/select/SelectPopover.svelte` |
| Filter menus (LabCheckMenu, moved and renamed 2026-10-05) | `frontend/src/lib/components/ui/select/CheckMenu.svelte` |
| "+" picker | `frontend/src/lib/components/risk/LabAssetPicker.svelte` |
| Regression test | `frontend/e2e/portfolio/risk-lab.spec.ts` |
