---
title: "Phase 0 / 21 — the guided onboarding (workstream J): the foundation, Rounds 1–8 and the review dossier"
category: source
source_type: plan
date_ingested: 2026-10-12
original_path: LibreFolio_developer_journal/Release_2/Phase_0/21_onboarding/plan-phase00Onboarding.prompt.md
tags: [phase0, release2, workstream-j, onboarding, coachmark, settings, layout, alembic, i18n, testing]
related:
  - features/F-105
  - decisions/onboarding-versioned-progress-per-flow
  - decisions/onboarding-existing-users-seeded-skipped
  - decisions/onboarding-guide-observes-never-acts
  - decisions/onboarding-positions-in-browser-per-account
  - decisions/guide-text-never-announces-another-guide
  - decisions/automatic-popups-wait-for-guides
  - problems/guide-anchor-never-resolves
  - problems/coachmark-measured-mid-modal-transition
  - problems/legacy-layout-gate-missed-runes-state
---

# Source: Phase 0 / 21 — the guided onboarding

## Summary

The folder holds ten files (about 313 KB): the main plan (743 lines), eight round plans and the review dossier. They
tell how SP11/U8 — «a welcome page, one tour and one import guide» — became [[features/F-105]]: fifteen versioned
flows, a coachmark engine, per-step progress, positions in the browser and a replay list in Settings.

| File | Dates | What it adds |
|------|-------|--------------|
| `plan-phase00Onboarding.prompt.md` | 2026-09-10 → 10-11 | The foundation (steps 0–6) and the integration (steps 7–13); the developer's authorisation «Approva J fondazione indipendente (Consigliato)»; the UX OK of 2026-09-14; «Cosa resta aperto» |
| Round 1 — UX refinement | 2026-09-11 → 09-14 | Shared Skip/X/Back/Next, the intro scene, no Pause, no demo data, no automatic writes; `inert` shell during the tour |
| Round 2 — modular guides | 2026-09-11 | Flow registry and catalogue; due rule; Broker, FX and Asset as contextual guides started by a real click on Add (developer feedback); `003` edited in place, «Non creare `004`» |
| Round 3 — triggered tours | 2026-09-11 → 09-14 | One flow per trigger (page, Add, detail): 15 flows; an account-scoped queue |
| Round 4 — geometry and milestones | 2026-09-11 → 09-14 | Collision-safe placement, cursor, per-step presentation; three Bulk flows (the developer's choice); the Import first-mount fix |
| Round 5 — step progress | 2026-09-12 → 09-14 | `user_onboarding_step_progress` and the step endpoints; Import and Bulk back to one flow each; X skips the current step only; all compatibility layers removed |
| Round 6 — final UX | 2026-09-14 | Intro at 8 s, Bulk checkpoint navigation, the 3 s panel fade; the developer's OK «…mi piace!» |
| Round 7 — anchor stall | 2026-09-21 | The 3 s stall with **Continue anyway** (`1982c254b`); the dossier's grandfathering correction |
| Round 8 — post-review | 2026-09-23 → 10-11 | The requested update check, positions in `localStorage`, resume at the step, cross-tab close, the layout flash, hidden anchors, the copy gate, the skill; the developer's review of 2026-09-24 (points 11–17); C7 closed on 2026-10-11 |
| `onboarding-review-dossier.md` | 2026-09-21 → 10-09 | A standalone review written by J about `580bd504f` (`09c6171bc`): the arc, «the decisions nobody authorised» (§2), backend, frontend, coverage gaps, what is not done; partly superseded on 2026-10-09 |

## Key Takeaways

- **The arc.** Rounds 0–1 delivered the brief; Rounds 2–5 generalised it. Round 2's split of Broker, FX and Asset into
  contextual guides came from the developer's feedback; the dossier counts the rest as J's own judgement: «Rounds 2–5
  delivered a *platform* that nobody asked for … That judgement may be right. It was not authorised.» Its answer was to
  write every such choice down with **what was chosen, what was rejected, why, and how to reverse it** (§2) — Welcome
  as a full page, the order of the tour, the X asymmetry of the step-managed flows, Welcome Skip writing nothing, the
  popup lane, the `inert` shell. The developer reviewed it and approved the UX on 2026-09-14.
- **An approval covers what was read.** The grandfathering was approved on a paragraph that described the opposite
  behaviour; the dossier recorded it as «an unvalidated decision that happens to be correct» —
  [[decisions/onboarding-existing-users-seeded-skipped]].
- **The work entered `dev_release2` folded inside another branch**: the foundation and Rounds 1–6 arrived with the PAC
  merge `3913fe217` (2026-09-19), «which is why it has never been described on its own terms» (dossier).
- **Never-shipped migrations are edited, then consolidated**: `003_user_onboarding_progress` was edited in place
  through Round 5 and absorbed into `004_release_1_2_0_schema.py` on 2026-09-22 (`22fa0aed7`) —
  [[decisions/onboarding-versioned-progress-per-flow]].
- **Anchors are the fragile part** (dossier §4.3): a step must stall visibly rather than wait forever, and a hidden
  anchor is an absent one — [[problems/guide-anchor-never-resolves]]; measure only after the container stops moving —
  [[problems/coachmark-measured-mid-modal-transition]].
- **Legacy components and runes state**: the layout flash ([[problems/legacy-layout-gate-missed-runes-state]]) and the
  privacy toggle that legacy broker components ignored (R20, `64d78e244`) are one family —
  [[problems/legacy-component-language-untracked]].
- **The developer's review of 2026-09-24** fixed three product rules: positions survive logout (point 14, reversed),
  the cross-tab close stays («era più di quello che avevo chiesto, teniamola»), and no text announces another guide
  (point 12) — [[decisions/onboarding-positions-in-browser-per-account]],
  [[decisions/guide-text-never-announces-another-guide]].
- **Process detours worth keeping** (Round 7): a `| tee | tail` pipe returned a false exit 0 (the status was
  `tail`'s); a re-audit grep matched `completato` and missed the feminine `completata` — the same family as
  [[problems/testid-grep-false-negative]]; «130 errors» were phantoms of a stale ignored generated file
  (`generated-tools.ts`; 3 real ones), and the claim was retracted.

## Still open (main plan, «Cosa resta aperto», 2026-10-11)

1. ✅ The developer's review of the C7 fixes — closed 2026-10-11: «credo ti sei perso perchè tutte queste ricordo di
   averle testate, è tutto verde…»; point 7 verified by the coordinator («OB-9 contrast»,
   `onboarding-guides.spec.ts`).
2. No test compares the TS flow list with the Python registry.
3. The version-bump re-trigger has never run end to end.
4. The 641–1023 px band is untested (Playwright has desktop 1280 and mobile 430).
5. No admin or CLI reset of a user's onboarding.
6. No telemetry on completion and skip.
7. The `tools.hub` anchor is used by no guide.

The developer kept the folder in `Phase_0/` on 2026-10-09 because of these open items. Round 8 had also found the
it/fr/es user pages without the onboarding sections; today `getting-started` and `settings/preferences` have them in
all four languages.

## Wiki Pages Updated

Created: [[features/F-105]]; [[decisions/onboarding-versioned-progress-per-flow]],
[[decisions/onboarding-existing-users-seeded-skipped]], [[decisions/onboarding-guide-observes-never-acts]],
[[decisions/onboarding-positions-in-browser-per-account]], [[decisions/guide-text-never-announces-another-guide]],
[[decisions/automatic-popups-wait-for-guides]]; [[problems/guide-anchor-never-resolves]],
[[problems/coachmark-measured-mid-modal-transition]], [[problems/legacy-layout-gate-missed-runes-state]].

Updated: [[features/registry]], [[domains/layout-settings]], [[features/F-004]], [[features/F-005]],
[[features/F-092]], [[features/F-101]], [[features/F-104]], [[entities/import-wizard-modal]],
[[concepts/svelte5-runes]], [[problems/legacy-component-language-untracked]],
[[problems/i18n-loading-gate-remounts-app]].

## Source files

| Role | Path |
|------|------|
| Main plan | `LibreFolio_developer_journal/Release_2/Phase_0/21_onboarding/plan-phase00Onboarding.prompt.md` |
| Round 7 | `LibreFolio_developer_journal/Release_2/Phase_0/21_onboarding/plan-phase00OnboardingRound7-AnchorStall.prompt.md` |
| Round 8 | `LibreFolio_developer_journal/Release_2/Phase_0/21_onboarding/plan-phase00OnboardingRound8-PostReview.prompt.md` |
| Review dossier | `LibreFolio_developer_journal/Release_2/Phase_0/21_onboarding/onboarding-review-dossier.md` |
| Registry | `backend/app/services/accounts/onboarding_service.py` |
| Engine | `frontend/src/lib/features/onboarding/onboardingGuide.svelte.ts` |
| Developer doc | `mkdocs_src/docs/developer/frontend/onboarding.md` |
