---
title: "Onboarding progress is one versioned row per user and flow, with per-step rows for the two step-managed flows"
category: decision
status: resolved
date: 2026-09-10
updated: 2026-09-22
tags: [backend, frontend, onboarding, db, alembic, versioning, api, release-1.2, workstream-j]
related:
  - features/F-105
  - decisions/onboarding-existing-users-seeded-skipped
  - decisions/onboarding-positions-in-browser-per-account
  - sources/phase00-onboarding-2026-09
---

# Decision: versioned onboarding progress per flow

## Context

The brief of the onboarding (SP11/U8, handed to workstream J on 2026-09-10) asked for Welcome, tour and import states
**versioned separately**, not inferred from `login_count`. The dossier of the review calls the resulting model the
fork of Round 0: «Established the versioned-per-flow model instead of a single `onboarding_completed` boolean. This is
the decision that made everything after it possible — and expensive.»

## Decision

- **One row per user and flow** in `user_onboarding_progress`: `status` (`pending`, `completed`, `skipped`) and the
  `version` the user went through. `flow` is a plain string without a CHECK on its values, so a new flow needs no
  schema change.
- **A flow is due** while it is `pending` or older than its current version:
  `progress.status === 'pending' || progress.version < progress.current_version` (`isOnboardingProgressDue()` in
  `frontend/src/lib/types/onboarding.ts`). Bumping a flow in `ONBOARDING_FLOW_VERSIONS` therefore re-offers it to
  everybody, completed or skipped. All fifteen flows are at version 1.
- **Every transition carries `expected_version`.** The server answers 409 (`onboarding_version_mismatch`) when the
  client rendered other content, so content nobody saw cannot be recorded as seen.
- **Step-managed flows** (`import_guide`, `transaction_bulk_guide`) also keep one row per step in
  `user_onboarding_step_progress` (Round 5). X or a stall skips only the current step; the flow stays `pending` until
  every registered step is terminal, then becomes `skipped` if all steps were skipped and `completed` otherwise.
- **Missing rows are created lazily** as `pending` on the first progress read (`INSERT … ON CONFLICT DO NOTHING` in
  `get_onboarding_progress()`), never rewriting stored progress.

## Options Considered

| Option | Outcome |
|--------|---------|
| A single `onboarding_completed` boolean, or inferring from `login_count` | Rejected by the brief: the three surfaces must be versioned separately |
| One flow per Bulk milestone — `transaction_bulk_validation_guide`, `…_selection_guide`, `…_save_guide` (Round 4, the developer's choice «più guide Bulk persistite separate») | Reversed in Round 5 on the developer's feedback: «Import/Bulk tornano a un flow ciascuno con progresso durevole per-step», «X salta soltanto current step» |
| One flow per guided surface, with per-step rows where a component drives the steps | **Chosen** (Round 5) |

## The migration path

Rounds 0–5 kept the tables in an unpublished `003_user_onboarding_progress` and edited it in place, because onboarding
was never shipped (Round 2: «Non creare `004`»), and in Round 5 a developer correction removed every v1/v2
compatibility layer for the same reason. On 2026-09-22 (`22fa0aed7`) the unpublished `003` files were
consolidated into `004_release_1_2_0_schema.py`, which removed a fork that left a fresh database with two Alembic heads.
That is the released-phase rule applied as written: an existing file is edited only while it was never shipped
([[concepts/single-migration-strategy]] keeps the older rule as history).

## Consequences

- The version bump is the mechanism to re-show changed content; a wording fix leaves the version alone.
- Two lists must agree by convention: the TS flow list (`ONBOARDING_FLOWS`, the Zod schemas in `onboardingApi.ts`)
  and the Python registry. A flow unknown to the client makes the progress load fail. **Open**: no test compares the
  two, and the bump path has never run end to end (main plan, «Cosa resta aperto» 2 and 3).
- A step that a clean import never reaches (`import.assets`, `import.fix`, `import.duplicates`, `import.gapFix`) keeps
  its flow `pending`: Settings can show the Import guide as *Pending* after a first import.

## Source files

| Role | Path |
|------|------|
| Registry, transitions, lazy insert | `backend/app/services/accounts/onboarding_service.py` |
| Endpoints and 409/422 | `backend/app/api/v1/settings.py` |
| Tables | `backend/alembic/versions/004_release_1_2_0_schema.py` |
| Due predicates | `frontend/src/lib/types/onboarding.ts` |
| Client with strict schemas | `frontend/src/lib/features/onboarding/onboardingApi.ts` |
| Registry test | `backend/test_scripts/test_services/test_settings_service.py` |
| API test | `backend/test_scripts/test_api/test_settings_api.py` |
| Developer doc | `mkdocs_src/docs/developer/frontend/onboarding.md` |
