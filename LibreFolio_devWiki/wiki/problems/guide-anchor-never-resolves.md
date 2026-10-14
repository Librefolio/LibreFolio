---
title: "A guide waited forever on an anchor that never resolved, and a hidden anchor pinned the coachmark at (0,0)"
category: problem
status: resolved
date: 2026-09-21
updated: 2026-09-24
tags: [frontend, onboarding, coachmark, anchors, stall, svelte5, teardown, release-1.2, workstream-j]
related:
  - features/F-105
  - decisions/onboarding-guide-observes-never-acts
  - problems/coachmark-measured-mid-modal-transition
  - problems/svelte5-teardown-reads-stale-state-timers
  - sources/phase00-onboarding-2026-09
---

# Problem: a step whose target never appears

## Symptom

Two forms, found in turn:

1. **Waiting forever** — when a step's anchor never registered, never connected or never settled, the coachmark kept
   its centred *waiting* panel indefinitely, indistinguishable from ordinary loading. The review dossier ranked it
   first among the open items (§6 #1, «High — this is the one I would fix first»).
2. **A hidden anchor counted as present** — a mounted anchor that was not rendered (for example inside a collapsed
   panel or an inactive tab) measured 0×0, stayed «stable», and anchored the coachmark at (0,0) with no stall.

## Root Cause

The anchor registry knows which node carries an id, not whether the user can see it. The coachmark waited for a
settled box with no deadline, and «settled» was satisfied by an empty box.

## Solution

- **The stall** (Round 7, `1982c254b`, 2026-09-21). Developer decision, verbatim: «se dopo 3 secondi il componente non
  diventa disponibile, scriviamo di andare avanti che c'è stato un problema di caricamento». After `GUIDE_STALL_MS`
  (3 s) of absence the panel says the area did not load in time and the primary button becomes **Continue anyway**:
  `next()` or `finish()`, or, in a step-managed flow, a `skipped` step that was never really shown. The timer runs only
  while waiting, is paused while a nested dialog suspends the step, never coexists with the 3 s panel fade
  (`PANEL_FADE_MS`), and `error` takes precedence over `stalled`. A late anchor clears the stall by itself.
- **The hidden anchor** (Round 8, 6e, `f2abf9b47`, 2026-09-24). `isRendered()` treats a 0×0 box, or an element hidden
  per `checkVisibility({visibilityProperty: true})`, as absent: waiting, then the stall. **Opacity is ignored on
  purpose**: hover-revealed controls start transparent and are real targets.
- **The page-author rule**: put `use:guideAnchor` only on an element rendered for its step; when a view hides a region,
  unmount it or leave the anchor off — never hide a registered anchor (developer doc, skill `onboarding-guide`).

## A detour inside the fix

Round 7 first cleared the host's stalled step from the effect body. Component destroy is the one path the body cannot
reach, so a stale `stalledStepId` survived unmount: a replayed step lit up as stalled from its first frame and
persisted `skipped` without ever being attempted. The end of a stall is now announced from the effect **teardown**
(`onstallend`), following the coordinator's counter-proposal. Round 7 also set a rule for its tests: an optional
callback (`?.()` or a no-op default) is validated only by a positive assertion that it fired.

## Still open (Round 7, owner: the developer)

- Re-arming the timer on an anchor that connects and disconnects cyclically: «3 s from the last change» or «3 s from
  the step's activation» is a product decision.
- In an `error` state with no anchor only Close is offered.

## Prevention

- `OnboardingCoachmark.test.ts` covers waiting, stall, recovery and suspension with `advanceFakeClockTo()`;
  `onboarding-guides.spec.ts` walks the guides on desktop and mobile.
- For tests, the coachmark root exposes `data-guide-state` (`waiting`, `anchored`, `stalled`, `error`).

## Source files

| Role | Path |
|------|------|
| Stall, `isRendered()`, constants | `frontend/src/lib/features/onboarding/components/OnboardingCoachmark.svelte` |
| Stalled step in the host | `frontend/src/lib/features/onboarding/components/OnboardingOverlayHost.svelte` |
| Anchor registry | `frontend/src/lib/features/onboarding/guideAnchors.svelte.ts` |
| Coachmark tests | `frontend/src/lib/features/onboarding/components/OnboardingCoachmark.test.ts` |
| Page-author rule | `mkdocs_src/docs/developer/frontend/components/features/import-wizard.md` |
| Authoring rules | `.github/skills/onboarding-tools/onboarding-guide/SKILL.md` |
