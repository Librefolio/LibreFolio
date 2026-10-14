---
title: "Deleting an account left its brokers, transactions and report files behind"
category: problem
status: resolved
date: 2026-10-08
tags: [backend, auth, users, brokers, data-integrity, orphans, transactions, brim]
related: [decisions/broker-last-owner-guard, features/F-002, features/F-003, features/F-010, problems/reused-ids-after-delete, sources/phase00-account-and-id-reuse-2026-10, sources/phase00-e2e-import-infra-2026-10]
---

# Problem: account deletion orphaned brokers

## Symptom

Deleting an account (`DELETE /auth/users/me`) removed the user and their settings, but a broker the user alone
owned stayed in the database with no owner — with its transactions and its uploaded broker reports on disk. Nobody
could see or delete it any more. Found while analysing flaky import E2E tests (plan 33), together with
[[problems/reused-ids-after-delete]].

## Root cause

`delete_user()` was a bare `session.delete(user)`. The `broker_user_access` rows cascade from the user
(`ON DELETE CASCADE`), but **`brokers` has no foreign key to `users`**: ownership lives only in the access rows, so
removing them left the broker ownerless instead of deleting it. The last-owner rule existed for *leaving* a broker
([[decisions/broker-last-owner-guard]]), not for deleting an account.

## Solution (train 12, merge `637c5d105`)

The developer's mandate: "apply the last-owner rule already in 1.2", with **one shared service function**.

- `delete_user()` (`backend/app/services/user_service.py`) calls `BrokerService.leave_broker()` for every broker the
  user can access: a broker whose last OWNER the user was is deleted with its transactions; elsewhere only the user's
  access goes. Then the user, and one commit.
- **All or nothing**: if a broker cannot be released, or anything fails, the session is rolled back and nothing is
  deleted (a `False` from `leave_broker` counts as an error, not only an exception) — the API answers 500 "nothing was
  deleted".
- **Files after the commit**: the deleted brokers' BRIM files live on disk and are removed after the commit
  (`brim_provider.delete_files_for_brokers`), as `DELETE /brokers` does.
- Refusing to delete the only active administrator is a product rule, not an error ([[features/F-003]]).

## Prevention

- When ownership is modelled only through an access table, every path that removes accesses must apply the
  ownership rule — and share its function.
- A destructive multi-row operation is one transaction; files outside the database go after the commit.

## Impact

Orphan brokers with their transactions and files, unreachable from the UI; with ids being reused at the time, a
new broker could even inherit the old one's report folder. No migration was written for existing orphans (none was
known in the field: the bug was "one nobody has lived yet", in the developer's words).

## Source files

| Role | Path |
|------|------|
| `delete_user` (last-owner rule per broker, all or nothing) | `backend/app/services/user_service.py` |
| `leave_broker` | `backend/app/services/broker_service.py` |
| `DELETE /auth/users/me` (only-admin refusal, file clean-up) | `backend/app/api/v1/auth.py` |
| File clean-up | `backend/app/services/brim_provider.py` |
| Account-deletion API tests | `backend/test_scripts/test_api/test_account_deletion_api.py` |
| Plan | `LibreFolio_developer_journal/Release_2/phases/34_accountAndIdReuse/plan-phase00AccountAndIdReuse.prompt.md` |
