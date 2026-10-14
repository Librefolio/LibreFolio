---
title: "Login told anyone that an account existed and was disabled, without its password"
category: problem
status: resolved
date: 2026-10-09
tags: [backend, auth, security, enumeration, timing, login, bcrypt]
related: [features/F-001, features/F-065, features/F-102, decisions/connection-security-server-never-upgrades, sources/phase00-connection-security-2026-10]
---

# Problem: account enumeration at login

## Symptom

`POST /api/v1/auth/login` answered differently depending on the account behind the username: an unknown user and a
wrong password got 401, but a **disabled** account got its own "disabled" answer **before the password was
checked**. Anyone could learn that an account existed — and that it was disabled — without knowing its password.
The response time leaked too: an unknown username skipped bcrypt and answered faster than a wrong password.

## Root cause

The login checked `is_active` before verifying the password, and verified a password only when an account was
found.

## Solution (train 24, merge `01da03047`)

- **The password comes first, whatever the account** (`backend/app/api/v1/auth.py`, login handler): a wrong
  password gets the same `401 "Invalid credentials"` for an unknown, an active or a disabled account.
- **An unknown account still costs a bcrypt check**: `verify_password_or_dummy()` checks the password against a
  dummy hash of the same cost, computed once (`_dummy_password_hash()`, `functools.cache`) and never matched
  (`backend/app/services/auth_service.py`). The test checks that the bcrypt check runs; it does not measure time.
- **Only the right password learns that the account is disabled**: `403` with
  `{"error_code": "ACCOUNT_DISABLED", "message": "Account is disabled"}`. The frontend's axios interceptor reacts
  only to 401, so the 403 reaches the login form's `catch` untouched.

Out of scope of the fix: registration and any password-reset path (the plan does not cover them).
`get_current_user` still answers 401 "User account is disabled" — harmless, because it requires a valid token.

## Prevention

- In an authentication path, decide on the secret first and on the account's state after.
- Every branch that rejects should cost the same work.

## Impact

Information disclosure (existence and state of accounts) to an unauthenticated caller, on any exposed instance.
Found together with the connection-security indicator: [[decisions/connection-security-server-never-upgrades]].

## Source files

| Role | Path |
|------|------|
| Login handler (password first, 401/403) | `backend/app/api/v1/auth.py` |
| `verify_password_or_dummy`, dummy hash | `backend/app/services/auth_service.py` |
| Plan | `LibreFolio_developer_journal/Release_2/phases/36_connectionSecurity/plan-phase00ConnectionSecurity.prompt.md` |
