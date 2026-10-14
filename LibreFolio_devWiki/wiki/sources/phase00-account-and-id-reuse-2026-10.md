---
title: "Phase 0 / 34 — account deletion, reused ids, the last administrator"
category: source
source_type: plan
date_ingested: 2026-10-09
original_path: LibreFolio_developer_journal/Release_2/phases/34_accountAndIdReuse/
tags: [phase0, release2, auth, users, brokers, sqlite, post-migration, cli, cookies, workstream-l]
related:
  - problems/account-deletion-orphaned-brokers
  - problems/reused-ids-after-delete
  - features/F-002
  - features/F-003
  - features/F-065
  - decisions/broker-last-owner-guard
  - sources/phase00-e2e-import-infra-2026-10
---

# Source: Phase 0 / 34 — account deletion and id reuse

## Summary

Two plans of workstream L, born from two defects that plan 33 found while chasing flaky import tests: deleting an
account orphaned the brokers it alone owned (A), and SQLite reused the ids of deleted rows (B). Step 1 (train 12,
merge `637c5d105`) fixed both at the root; step 2 (train 22, merge `47c56581b`) guarded the last active administrator
and closed three neighbouring defects of the CLI and the session.

## Key takeaways

- Account deletion applies the last-owner rule per broker through the same function as "leave a broker", all or
  nothing, files after the commit: [[problems/account-deletion-orphaned-brokers]].
- Ids that leave the backend are never reissued; existing databases are converted by a new post-migration fix
  subsystem with integrity check, backup, verification and a start-up that never blocks:
  [[problems/reused-ids-after-delete]].
- Step 2 (§0.1):
  - demoting or deactivating the last **active** administrator is refused, and so is deleting one's own account as
    the only one ([[features/F-003]]);
  - `dev.py user …` exits with status 1 when it fails;
  - an empty or blank `JWT_SECRET` counts as absent — each worker had been generating its own secret and logging
    users out at random ([[features/F-065]]);
  - the session cookie's `Secure` attribute follows `SESSION_COOKIE_SECURE = auto | always | never`
    ([[features/F-065]]).

## Residuals (backlog 38)

L12 — E2E users are created as administrators.

## Wiki pages updated

- [[problems/account-deletion-orphaned-brokers]], [[problems/reused-ids-after-delete]] — new.
- [[features/F-002]] — corrected: no admin CRUD API or Settings tab exists; administration is the CLI; self-deletion.
- [[features/F-003]] — corrected (`UserRole` is the broker role; `require_admin`); last-active-admin guard.
- [[features/F-001]], [[features/F-065]] — login, cookie and secret notes.
- [[decisions/broker-last-owner-guard]] — the rule's second caller.
- [[concepts/single-migration-strategy]] — marked superseded (incremental migrations since the release).

## Source files

| Role | Path |
|------|------|
| Plan, step 1 | `LibreFolio_developer_journal/Release_2/phases/34_accountAndIdReuse/plan-phase00AccountAndIdReuse.prompt.md` |
| Plan, step 2 (last admin) | `LibreFolio_developer_journal/Release_2/phases/34_accountAndIdReuse/plan-phase00AccountAndIdReuseStep2LastAdmin.prompt.md` |
| User service | `backend/app/services/user_service.py` |
| Post-migration fixes | `backend/app/db/post_migration/autoincrement.py` |
| User CLI | `scripts/user_cli.py` |
| Shared JWT secret | `dev.py` |
