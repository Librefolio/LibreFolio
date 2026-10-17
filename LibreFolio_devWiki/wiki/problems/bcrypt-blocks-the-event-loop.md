---
title: "Login, registration and password change run bcrypt inside the event loop (V-16)"
category: problem
status: resolved
date: 2026-10-12
updated: 2026-10-12
tags: [backend, auth, bcrypt, async, event-loop, performance, fastapi, workstream-v]
related:
  - concepts/async-io-rule
  - problems/e2e-writes-leaked-into-shared-state
  - sources/phase00-data-quality-e2e-2026-10
---

# Problem: password hashing blocks the worker

## Symptom

Found by workstream V's test-author on 2026-10-12, while triaging reds of the E2E gate under load, and verified by V:
every login, registration and password change holds its uvicorn worker for the length of a bcrypt computation —
about 0.24 s per check at cost 12, measured — and for that time the worker serves no other request. At four E2E
workers the suite made about 51 logins in 67 s. No red has been proved to come from it; it may contribute to the 3 s
waits that fail under load (V-20).

## Root Cause

The bcrypt calls are synchronous and sit directly in `async def` handlers of `backend/app/api/v1/auth.py`:

- `login` calls `verify_password_or_dummy`, i.e. `bcrypt.checkpw` (`services/auth_service.py`);
- `register` reaches `hash_password` (`bcrypt.hashpw`) through `user_service.create_user`;
- `change_password` calls `verify_password` and `hash_password`.

bcrypt is CPU-bound rather than I/O, but the effect is the one [[concepts/async-io-rule]] forbids: a blocking call on
the event loop.

## Solution

Train 66, the same day (backlog V-16 closed; plan 46, §12.7):

- **Red first** (`0d6aee67c`): `TestPasswordWorkLeavesTheEventLoopFree` in `test_auth_api.py` calls each handler
  in-process on its own SQLite under `tmp_path`, with the password function replaced through `monkeypatch` by a
  stand-in that holds its thread for 0.4 s — no real bcrypt is measured. A heartbeat on the same loop beats every 10 ms,
  and the longest gap **during** the stand-in must stay under 0.15 s; outcomes are checked too (a 401, the stand-in's
  hash saved, the arguments), so a test cannot turn green by skipping the work. LOOP-000 checks the instrument itself.
  Red before the cure: gaps of 0.41 s (login), 0.40 s (register), 0.40 + 0.40 s (password change).
- **The cure** (`a9e0fe4d9`): `await asyncio.to_thread(...)` around `verify_password_or_dummy` in `login`, around
  `verify_password` and `hash_password` in `change_password`, and around `hash_password` in
  `user_service.create_user`, whose signature is unchanged because the CLI calls it under `asyncio.run`.
  `user_service.reset_password`, used only by the CLI, stays as it is.
- **Gates**: `api auth` 60/60, `api profile` 12/12, `api account-deletion` 6/6, and an E2E login at one and four workers.
- A review of every `async def` handler under `backend/app/api/v1` — direct bcrypt, file I/O, `shutil`, `subprocess`,
  `urlopen` — found only these three; it did not go down into the services.

## Prevention

Treat CPU-heavy library calls like blocking I/O in an `async def` handler: run them in a thread. A heartbeat on the
event loop proves it without timing the library itself.

## Source files

| Role | Path |
|------|------|
| Handlers (`login`, `register`, `change_password`) | `backend/app/api/v1/auth.py` |
| bcrypt calls (`hash_password`, `verify_password_or_dummy`) | `backend/app/services/accounts/auth_service.py` |
| Registration path (`create_user`) | `backend/app/services/accounts/user_service.py` |
| Event-loop tests (`TestPasswordWorkLeavesTheEventLoopFree`) | `backend/test_scripts/test_api/test_auth_api.py` |
| Backlog (V-16) | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
| Journal (§12.7) | `LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` |
