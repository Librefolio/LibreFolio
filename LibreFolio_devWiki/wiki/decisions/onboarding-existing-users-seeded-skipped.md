---
title: "Accounts older than 1.2.0 get Welcome completed and every guide skipped — approved on a stale description"
category: decision
status: resolved
date: 2026-09-21
tags: [backend, onboarding, alembic, migration, grandfathering, upgrade, release-1.2, workstream-j, process]
related:
  - features/F-105
  - decisions/onboarding-versioned-progress-per-flow
  - features/F-103
  - sources/phase00-onboarding-2026-09
---

# Decision: existing users are seeded `skipped`, not taught again

## Context

When 1.2.0 upgrades an existing install, its users already configured the application. What should the onboarding
do with them?

## Decision

Migration `004_release_1_2_0_schema.py` seeds every user that exists when it runs:

- `welcome` as **`completed`** — their settings are demonstrably configured;
- the other fourteen flows as **`skipped`**, with `skipped` rows for the steps it lists (four Bulk steps, eight Import
  steps).

The migration's docstring gives the reason for `skipped` over `completed`: it «keeps "was never shown this" distinct
from "went through it", so the flows can still be offered retroactively» — by a version bump, for instance. Accounts
created afterwards get nothing from the migration: their rows appear as `pending` on the first progress read.

## How the approval was given

The review dossier (§3.3) records a correction written in Round 7, step 1 (2026-09-21):

- On J's branch head `580bd504f` the migration seeded every guide `pending`: «an existing user gets the full intro tour
  and every contextual guide on next use». The file changed on the way into `dev_release2` (28 insertions, 22
  deletions) to today's behaviour.
- The developer read the old paragraph and approved the upgrade path with «va bene che chi era già utente non riceva il
  tour» — which is what the **new** code does and the **opposite** of what the paragraph described.
- The dossier's verdict: «So this is not a validated decision. It is an unvalidated decision that happens to be
  correct. If it is ever revisited, revisit it on its merits.»

J's original reasoning for `pending` is kept there too: grandfather the *setup*, still offer the *education*. The
counter-argument that prevailed: a tour pushed at someone who has used the app for months is an interruption, and the
audience of the feature is new sign-ups.

## Consequences

- **A bump reaches everybody.** A bumped flow becomes due for every account at an older version, the grandfathered
  ones included (developer doc, «A version bump reaches every account»).
- **The seed lists are frozen.** The migration lists flows and steps in literal SQL. Anything registered later reaches
  older accounts as `pending` through the lazy insert: `import.gapFix`, added with the report sets
  ([[features/F-103]], `9336c0e9b`, 2026-10-01), is such a step. Keeping a later addition from older accounts takes a
  migration of its own.
  *2026-10-12 (developer, via the coordinator): the effect is accepted, not a defect — «Va bene così: lo step è una
  novità della 1.2 e il coachmark la presenta una volta sola». Migration 004 does not change: an account older than
  1.2.0 meets the `import.gapFix` coachmark once, the first time an import reaches the step.*
- **Test users are not real users.** `_grandfather_onboarding_for_test_users` marks the canonical E2E users
  `completed` on every flow and step, because they did go through the flows in earlier runs; its docstring, which
  described the migration backwards, was corrected in `1982c254b`. Seeding the step rows too fixed IWR-006 (pending
  step rows started the Import and Bulk guides in unrelated specs, `5e7ae336e`). Guide specs never walk the canonical
  users: `frontend/e2e/fixtures/onboarding-accounts.ts` registers a disposable account.

## Lesson

An approval is evidence only for the text that was read. When a description and the code diverge before a review, the
review validates the description; the dossier's habit — record the approval, and record what it did and did not cover
— is what kept this one honest.

## Source files

| Role | Path |
|------|------|
| Tables and seed | `backend/alembic/versions/004_release_1_2_0_schema.py` |
| Lazy `pending` rows | `backend/app/services/accounts/onboarding_service.py` |
| Test-user seeding | `backend/test_scripts/test_db/populate_mock_data.py` |
| Migration check | `backend/test_scripts/test_db/db_schema_validate.py` |
| Disposable E2E accounts | `frontend/e2e/fixtures/onboarding-accounts.ts` |
| Review dossier | `LibreFolio_developer_journal/Release_2/Phase_0/21_onboarding/onboarding-review-dossier.md` |
| User doc (older accounts) | `mkdocs_src/docs/user/getting-started.en.md` |
