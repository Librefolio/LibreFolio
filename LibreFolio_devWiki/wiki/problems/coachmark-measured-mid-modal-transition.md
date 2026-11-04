---
title: "The coachmark measured the Import CTA during the modal's scale transition; an unconditional scrollIntoView() hid the defect"
category: problem
status: resolved
date: 2026-09-11
tags: [frontend, onboarding, coachmark, geometry, modal, transitions, scroll, import-wizard, release-1.2, workstream-j]
related:
  - features/F-105
  - problems/guide-anchor-never-resolves
  - entities/import-wizard-modal
  - sources/phase00-onboarding-2026-09
---

# Problem: a target measured while it was still moving

## Symptom

At the Import Wizard's first mount the coachmark took a wrong measure of the footer CTA, and the position was corrected
only after a scroll (Round 4's list of review findings, 2026-09-11: «Import CTA misurata durante il primo mount e
corretta soltanto dopo scroll»).

## Root Cause

Round 4, confirmed: the footer CTA was measured during the `scale` transition of `ModalBase`. The motion root the
coachmark watched was the button itself, which does not see its ancestor's animation, so the first «stable» box was a
box in mid-scale. The coachmark also called `scrollIntoView()` unconditionally: the second layout it caused moved the
coachmark to the right place and **masked** the defect.

## Solution

Round 4, step 6 (2026-09-11):

- **Motion root** = the nearest `.modal-content` or `nav` ancestor, or the anchor itself
  (`anchor?.closest('.modal-content, nav') ?? anchor` in `OnboardingCoachmark.svelte`).
- **Settle, then two identical frames**: pointer and highlight wait for the transition to end and for the box to be
  identical on two consecutive frames.
- **No unconditional scroll**: the Import CTAs use `scrollPolicy: 'none'`; other targets scroll only when they are
  outside the declared scroll root (`data-guide-scroll-root`, published by the wizard body) or under the app header
  (`nearest-if-hidden`). Activating the Import guide changes neither `window.scrollY` nor the wizard's `scrollTop`.

Round 5 added the follow-up state: a settled target that scrolls, resizes or transitions is `revalidating`, keeping its
text and spotlight, instead of flickering back to *waiting*; only a target that loses its box returns to `waiting`.

## Prevention

- The coachmark root exposes `data-geometry-state` (`waiting`, `revalidating`, `stable`) for tests.
- An Import geometry test that read the state and the geometry in different frames was itself an assumption; Round 4
  replaced it with one atomic sample.
- General lesson: never measure a target inside an animating container without watching the container; and a scroll
  that «fixes» a position is evidence of a measuring bug, not a cure.

## Source files

| Role | Path |
|------|------|
| Geometry, motion root, scroll policy | `frontend/src/lib/features/onboarding/components/OnboardingCoachmark.svelte` |
| Modal transition and depth | `frontend/src/lib/components/ui/modals/ModalBase.svelte` |
| Import presentation (`scrollPolicy`) | `frontend/src/lib/features/onboarding/components/OnboardingOverlayHost.svelte` |
| Wizard scroll root | `frontend/src/lib/features/transactions/import/ImportWizardModal.svelte` |
| Coachmark tests | `frontend/src/lib/features/onboarding/components/OnboardingCoachmark.test.ts` |
| Tour and Import E2E | `frontend/e2e/onboarding-tour.spec.ts` |
