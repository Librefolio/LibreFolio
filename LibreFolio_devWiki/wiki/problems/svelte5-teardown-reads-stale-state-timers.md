---
title: "Svelte 5: a teardown reads `$state` as it was before its last write — timers survived the destroy"
category: problem
status: resolved
date: 2026-10-01
tags: [frontend, svelte5, runes, effects, teardown, timers, vitest, jsdom, flaky, silent-failure]
related: [concepts/svelte5-runes, problems/svelte5-effect-read-write-loop, concepts/discard-the-answer-not-the-question, concepts/load-only-red-is-a-product-defect, problems/tooltip-click-pins-over-modal, sources/phase00-taxonomy-select-2026-10]
---

# Problem: timer handles in `$state` escape the destroy cleanup

> Backlog **K-25** asked for this page (workstream K, steps 14 and 16 R1).

## Symptom

The `component-unit` Vitest suite passed every test and still **exited with code 1**: an unhandled
`ReferenceError: document is not defined`, blamed on a test file that had nothing to do with it
(`ChartSignalsSection.test.ts`). It came back on 2026-10-06 in another component: 2 276/2 276 green, exit 1, **only
under load** — never with the file alone. In a browser the same code is harmless, because `document` always exists;
under Vitest a timer fired after jsdom had been torn down.

## Root cause

1. **`Tooltip.svelte`** already cancelled its timers in a destroy cleanup, `$effect(() => () => {…})`, but the two
   timer handles were declared with `$state`. When a `$state` value is written, Svelte 5 (5.48) records the
   *previous* value; during an effect teardown, reading the state returns that recorded value, and the record is
   cleared only by an effect flush. Nothing read the handles reactively, so writing them never queued a flush: the
   teardown saw the old `null` and the live timer survived.
2. A `requestAnimationFrame` (`pendingPositionFrame`) was cancelled only by the teardown of the listeners effect —
   which never exists if the tooltip is destroyed synchronously before its first re-render.
3. **`TreeSelect.svelte`** (born 2026-09-24) deferred five steps with `setTimeout(0)` and never cancelled them; the
   chain `open()` → `setActiveIndex` → `scrollActiveEntryIntoView()` ended in a global `document.getElementById`.

Why it hid: `render(...).unmount()` from Testing Library runs `flushSync`, which clears the recorded values — so the
red test had to mount and unmount with Svelte's own `mount`/`unmount`, without a flush.

## Solution

- **Handles in plain variables.** `pendingHideTimer`, `pendingShowTimer` and `pendingPositionFrame` are plain `let`s
  (`Tooltip.svelte`, with a comment saying why); TreeSelect keeps its handles in a plain `Set` (`pendingSteps`), and
  each deferred step removes its own handle when it runs (`defer()`).
- **One destroy teardown cancels everything**, the animation frame included (`$effect(() => () => {…})`).
- **Look elements up inside the component**, not on the global `document`: `entryElement()` searches the picker's
  own dropdown (`querySelectorAll('[id]')` — jsdom lacks `CSS.escape`).
- Tests on fake timers assert **`vi.getTimerCount() === 0` after unmount**, with a positive check before it: four
  Tooltip cases (hover, pinned, touch, frame) and five TreeSelect rows were red on the baseline. One row was dropped
  on purpose: jsdom's own `selectionchange` timer cannot be cancelled by any component.
- Rejected: adding `afterEach(cleanup)` to the blamed test file — the `svelteTesting()` setup already unmounts after
  every test; the bug was in the components.

Commits `4b5feb227` (Tooltip, 2026-10-01) and `2575aeaf2` (TreeSelect, 2026-10-06).

## The rule

**A value that a teardown must read — a timer or frame handle, a subscription, a pending request — is not `$state`.**
Keep it in a plain variable (or a plain collection), cancel it in a destroy teardown, and never let a deferred
callback reach for the global `document`. Use `$state` only for what the template renders.

## Still open (backlog 38)

- **K-12** — handles still held in `$state`: `touchTimerId` in `DataTable.svelte` and `reloadTimer` on the Dashboard
  page (verified at `083ed26dc`).
- **C-13** — `SearchSelect.svelte` defers four `setTimeout`s it never cancels and uses the global
  `document.querySelectorAll`.
- A suite-wide "no timer alive at the end of a file" check is still only an idea.

## Impact

False reds that blamed innocent files, appearing only under load — the kind that teach people to rerun instead of
read ([[concepts/load-only-red-is-a-product-defect]]). In production: callbacks firing on destroyed components.

## Source files

| Role | Path |
|------|------|
| Tooltip (plain handles, destroy teardown) | `frontend/src/lib/components/ui/feedback/Tooltip.svelte` |
| Tooltip teardown tests | `frontend/src/lib/components/ui/feedback/Tooltip.test.ts` |
| TreeSelect (`pendingSteps`, `defer`, `entryElement`) | `frontend/src/lib/components/ui/select/TreeSelect.svelte` |
| TreeSelect teardown tests | `frontend/src/lib/components/ui/select/TreeSelect.test.ts` |
| Residual K-12 | `frontend/src/lib/components/table/DataTable.svelte` |
| Residual K-12 (Dashboard) | `frontend/src/routes/(app)/dashboard/+page.svelte` |
| Residual C-13 | `frontend/src/lib/components/ui/select/SearchSelect.svelte` |
| Plan (step 14) | `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep14TooltipTeardownFixture.prompt.md` |
| Plan (step 16, round 1) | `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep16Round1-TreeSelectTeardown.prompt.md` |
