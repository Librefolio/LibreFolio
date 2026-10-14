---
title: "Modal layers: one Escape closed two layers, and a `space-y` gap left the page clickable under a dialog"
category: problem
status: resolved
date: 2026-10-08
first_seen: 2026-10-07
resolved: 2026-10-08
tags: [frontend, modals, keyboard, escape, accessibility, tailwind, css, svelte]
related: [problems/popover-pointerdown-swallows-click, problems/tooltip-click-pins-over-modal, problems/svelte5-teardown-reads-stale-state-timers, sources/phase00-taxonomy-select-2026-10]
---

# Problem: modal layers that leaked through

Two defects of `ModalBase` stacking, found by workstream K during the coverage triage and the app-start lot
(steps 18–20, 2026-10-07/08).

## 1. One Escape closed the inner layer **and** the modal

**Symptom.** With a row menu open inside the transactions bulk editor, one `Escape` closed the menu and the editor
with it. Same with a select whose list was open over a form, and — in the import wizard — the "Read as" list of
`ReportSetCard`, where the Escape that reached the wizard asked to discard the whole import.

**Cause.** The inner layer handled the key and let it go on: `ContextMenu` from a capturing `keydown` listener on
`window` (with `preventDefault()` but no `stopPropagation()`), `SearchSelect` from the keydown of its search box or
of its trigger, `SimpleSelect` from its trigger (a combobox that keeps the focus there with
`aria-activedescendant`). The keydown then bubbled to `ModalBase`'s backdrop, which closes on any Escape and does not
look at `defaultPrevented`.

**Rule adopted: one Escape closes one layer — and the layer says so, not a global stack.** Each popup layer calls
`stopPropagation()` on the Escape it consumes, and only while it is open: `ContextMenu` (listener mounted only with
the menu), `SearchSelect` (search-box handler, and the trigger with the list open — reached after Shift+Tab from the
search box), `SimpleSelect` (trigger handler, list open). `ModalBase` itself did not change, so it remains correct
for nested modals: it stops the propagation of the Escape it uses. No global "layer stack" was introduced.

**Guard.** `ModalBase.escapeLayers.test.ts` (with `ModalEscapeLayersHarness.svelte`) delivers Escape the way a
browser does — to the focused element, bubbling, the window capture listener first — and for each layer proves the
inner layer really handled the key **before** asserting the modal is still open, then presses Escape again to prove
the layer let go of the key. Controls (nothing open, select closed) prove the modal still closes: a cure that
swallowed every Escape turns them red. `ReportSetCard.escape.test.ts` pins the wizard case.

**Still open: C-12** — `AiExportMenu` listens on `document` in the capture phase without `stopPropagation`, so an
Escape that closes a `SimpleSelect` inside the panel closes the panel too (after 1.2, by the developer's decision;
the menu is mounted only in page toolbars, never in a modal).

## 2. The backdrop stopped short of the viewport bottom

**Symptom.** In Settings → About, under the social-share dialog (`aria-modal`), the last ~32 px of the page stayed
clickable: the backdrop ended at 688 of 720 px.

**Cause.** `.modal-backdrop` is `position: fixed; inset: 0`, and a fixed box is shortened by its margins. Rendered
inside a `space-y-8` container where it is not the last child, it inherited Tailwind 4's
`:where(.space-y-8 > :not(:last-child)) { margin-block-end: 2rem }`.

**Fix.** `margin: 0` on `.modal-backdrop` — the scoped rule wins over `:where()`, whose specificity is 0. Covered in
`support-copy-and-go.spec.ts` (`elementFromPoint` in the last pixels finds the backdrop).

**Lesson.** A fixed overlay must reset the margins a layout utility can put on "every child but the last": in
Tailwind 4 `space-y-*` is a margin on siblings, not a gap.

## Source files

| Role | Path |
|------|------|
| Modal (Escape handler, backdrop CSS) | `frontend/src/lib/components/ui/modals/ModalBase.svelte` |
| Row menu | `frontend/src/lib/components/ui/ContextMenu.svelte` |
| Search select | `frontend/src/lib/components/ui/select/SearchSelect.svelte` |
| Simple select | `frontend/src/lib/components/ui/select/SimpleSelect.svelte` |
| Layer guard | `frontend/src/lib/components/ui/modals/ModalBase.escapeLayers.test.ts` |
| Test harness | `frontend/src/__tests__/harness/ModalEscapeLayersHarness.svelte` |
| Wizard case | `frontend/src/lib/components/transactions/import/ReportSetCard.escape.test.ts` |
| Backdrop E2E | `frontend/e2e/support-copy-and-go.spec.ts` |
| Plans (steps 18–20) | `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep18CoverageTriage.prompt.md` |
| | `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep19AppStartAuth.prompt.md` |
| | `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep20SimpleSelectEscape.prompt.md` |
