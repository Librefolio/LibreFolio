---
title: "Guide positions live in this browser, per account, flow and version: resume at the step, survive logout, close in every tab"
category: decision
status: resolved
date: 2026-09-24
tags: [frontend, onboarding, localstorage, replay, cross-tab, session, release-1.2, workstream-j]
related:
  - features/F-105
  - decisions/onboarding-versioned-progress-per-flow
  - decisions/onboarding-guide-observes-never-acts
  - sources/phase00-onboarding-2026-09
---

# Decision: where an unfinished guide stopped is remembered in this browser

## Context

Two stores cooperate: the **server** knows whether a guide is still due ([[decisions/onboarding-versioned-progress-per-flow]]);
the **browser** knows where an unfinished guide or an armed replay currently is. Until Round 7 that position lived in
`sessionStorage`: a replay armed in one tab died with the tab, and the dossier (§2.5, §6 #2) listed it as «plausible
but wrong». Leaving a route mid-guide also restarted it at step 1. Round 7 deferred both to the sequence R7 → R8 → R9
that the developer confirmed on 2026-09-21; Round 8 took them up as OB-8 and OB-9.

## Decision

Approved with the Round 8 plan (2026-09-23, defaults Q5 and Q6), then corrected by the developer's live review of
2026-09-24 (points 13–16):

- **`localStorage`, one key per account, flow and content version** — `lf_{userId}_onboarding_replay_{flow}_v{version}`
  (`onboarding.svelte.ts`), holding the step id, the mode (`automatic` or `replay`), the steps left in a step-managed
  replay and the `returnTo`. Keys are never shared across accounts, browsers or devices.
- **A guide resumes at the step it left** (Q6, OB-9): a reload, a closed tab or a left route loses only the in-memory
  guide. Developer, point 16: «mi piace moltissimo». Closing an Add modal still restarts its guide at step 1
  (`dismissHost({restartAtFirst: true})`).
- **Logging out keeps it** — point 14, a reversal. Q5 said the keys were deleted at logout; the developer's decision on
  2026-09-24: an armed replay must still be armed after logging out and back in, in the same account on the same
  browser. `208296923` removed `clearAccountReplays`; an account change now resets only the in-memory state.
- **A guide that ends in one tab closes in the others.** Ending a guide deletes its key, and the `storage` listener
  (`createReplayStorageListener`) makes every other tab drop its copy and close the step, so a stale tab cannot write
  the key back. Point 15: «era più di quello che avevo chiesto, teniamola». There is no `BroadcastChannel`.
- **A version bump drops the old keys** of that flow on the next read or write.
- **The copy says «in this browser»**, not «on this device»: `localStorage` belongs to the browser profile. J changed
  Q5's wording; the developer did not contest it (point 13 was confirmed with that text).

## Detour

Dropping only the in-memory replay when another tab removed the key left the automatic guide blocked in that tab: the
listener now dismisses the host (`onDropped` → `dismissHost()`).

## Consequences

- A second browser or device sees the server status only: a guide finished there is not due here, an armed replay is
  not armed here.
- If the browser closes without a logout and another account signs in, the first account's keys stay under its own id
  until it returns; they are invisible to the others.

## Source files

| Role | Path |
|------|------|
| Keys, resume, storage listener | `frontend/src/lib/stores/app/onboarding.svelte.ts` |
| Listener registration | `frontend/src/lib/features/onboarding/onboardingGuide.svelte.ts` |
| Session reset | `frontend/src/lib/stores/app/clientSession.ts` |
| Controller tests | `frontend/src/lib/stores/app/onboarding.test.ts` |
| Resume, logout and cross-tab E2E | `frontend/e2e/onboarding-guides.spec.ts` |
| Replay list | `frontend/src/lib/features/onboarding/components/OnboardingReplaySection.svelte` |
| Developer doc | `mkdocs_src/docs/developer/frontend/onboarding.md` |
