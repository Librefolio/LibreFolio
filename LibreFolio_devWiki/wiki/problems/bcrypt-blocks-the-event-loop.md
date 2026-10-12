---
title: "Login, registration and password change run bcrypt inside the event loop (V-16)"
category: problem
status: open
date: 2026-10-12
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

Not decided yet: backlog V-16 (medium, «serve una decisione»). The likely cure is `await asyncio.to_thread(...)` around
the hashing and the verification. The coordinator will signal it to the wiki when the code enters.

## Prevention

Treat CPU-heavy library calls like blocking I/O in an `async def` handler: run them in a thread. A load test on the
login path would show the stall that a single test cannot.

## Source files

| Role | Path |
|------|------|
| Handlers (`login`, `register`, `change_password`) | `backend/app/api/v1/auth.py` |
| bcrypt calls (`hash_password`, `verify_password_or_dummy`) | `backend/app/services/auth_service.py` |
| Registration path (`create_user`) | `backend/app/services/user_service.py` |
| Backlog (V-16) | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
