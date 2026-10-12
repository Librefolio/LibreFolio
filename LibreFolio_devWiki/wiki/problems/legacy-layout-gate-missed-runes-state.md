---
title: "The (app) layout's legacy $: gate never saw the runes bootstrap settle: the requested page flashed before the Welcome redirect"
category: problem
status: resolved
date: 2026-09-24
tags: [frontend, svelte5, legacy-mode, reactivity, layout, onboarding, privacy, testing, release-1.2, workstream-j]
related:
  - features/F-105
  - features/F-004
  - concepts/svelte5-runes
  - problems/legacy-component-language-untracked
  - sources/phase00-onboarding-2026-09
---

# Problem: a legacy `$:` statement does not track a runes field

## Symptom

With Welcome due, opening `/settings` or `/dashboard` directly painted the **whole app shell on the requested page**
for a moment, then went to `/welcome`. Found by a negative control of J's test author in Round 8 (2026-09-24), then
measured live (step 6d) with a throw-away Playwright probe recording every animation frame:

- the redirect placeholder `onboarding-redirecting` was mounted in **0** frames;
- the shell of the requested page showed for 1–5 frames (up to 36 ms);
- with a Welcome replay armed, the flashed page was the owner's own page; in one run of eight a new account's
  dashboard showed nine amounts (the zeros of an empty portfolio).

## Root Cause

`routes/(app)/+layout.svelte` is a legacy component (no runes). It computed `onboardingRouteReady` in `$:` statements
that read `appBootstrap.ready`, a runes field inside a module singleton — and a `$:` does not track it. When the
bootstrap settled, the template left its loading branch, but the `$:` gate kept its old value: the placeholder never
mounted and the requested page drew until the asynchronous redirect arrived. The plan calls it «la stessa famiglia di
R20», the privacy toggle that legacy broker components did not follow
([[problems/legacy-component-language-untracked]]).

## Solution

`cc20b8288` (2026-09-24): the layout reads the flag through `toStore(() => appBootstrap.ready)`, so the `$:` gate
re-runs when the bootstrap settles. While a redirect is pending the layout shows `onboarding-redirecting`, never the
requested page. The developer's review of the same day, point 17: «il redirect funziona bene».

## Prevention

- `routes/(app)/layout.gate.test.ts` (with a harness, a `$app/stores` mock and its `vitest.config.ts` alias) pins the
  gate: it follows the bootstrap.
- `onboardingRouteSettlement.ts` acts once per route snapshot; the initial load owns the settlement, and the reactive
  gate claims only snapshots not handled yet.
- The other legacy `$:` statements of the layout were left as they are, by decision (Round 8, residual findings).
- Rule of thumb, now in [[concepts/svelte5-runes]]: a legacy component that must react to runes state reads it through
  `toStore()` (or the code moves to runes).

## Source files

| Role | Path |
|------|------|
| The layout gate | `frontend/src/routes/(app)/+layout.svelte` |
| Bootstrap (runes singleton) | `frontend/src/lib/features/onboarding/appBootstrap.svelte.ts` |
| Route settlement | `frontend/src/lib/features/onboarding/onboardingRouteSettlement.ts` |
| Gate test | `frontend/src/routes/(app)/layout.gate.test.ts` |
| `$app/stores` mock | `frontend/src/__mocks__/$app/stores.ts` |
| Vitest alias | `frontend/vitest.config.ts` |
| Developer doc | `mkdocs_src/docs/developer/frontend/onboarding.md` |
