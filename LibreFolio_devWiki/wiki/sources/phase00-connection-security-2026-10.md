---
title: "Phase 0 / 36 — connection security indicator and login without account enumeration"
category: source
source_type: plan
date_ingested: 2026-10-09
original_path: LibreFolio_developer_journal/Release_2/phases/36_connectionSecurity/plan-phase00ConnectionSecurity.prompt.md
tags: [phase0, release2, security, auth, https, enumeration, sidebar]
related:
  - decisions/connection-security-server-never-upgrades
  - problems/login-account-enumeration-before-password
  - features/F-102
  - features/F-001
  - features/F-065
---

# Source: Phase 0 / 36 — connection security

## Summary

One plan (~480 lines), merged in train 24 (`01da03047`, commits `3392c4f05`, `07da532fb`, `28c85d34f`) and archived on
2026-10-09. It added a shield in the sidebar that tells the user whether their connection is secure, local or
insecure — with the server's help but without the server ever upgrading the browser's verdict or revealing the
client address — and, on the way, closed an account-enumeration leak in the login.

## Key takeaways

- The verdict rule, the privacy of the client address, the admin cookie warning and the decisions D2/D3/D5:
  [[decisions/connection-security-server-never-upgrades]].
- The login checked `is_active` before the password and skipped bcrypt for unknown users; now password first,
  identical 401, a dummy hash, and 403 `ACCOUNT_DISABLED` only for the right password:
  [[problems/login-account-enumeration-before-password]].
- Gotcha: the axios interceptor reacts only to 401, so the new 403 reaches the login form untouched.
- Left for later: a warning on the login page itself (phase 2 of the plan).

## Wiki pages updated

- [[features/F-102]], [[decisions/connection-security-server-never-upgrades]],
  [[problems/login-account-enumeration-before-password]] — new.
- [[features/F-001]] — login answers; stale `get_admin_user`, UUID and passlib claims corrected.
- [[features/F-065]] — cookie `Secure` modes; stale `Secure=False`, UUID and passlib claims corrected.

## Source files

| Role | Path |
|------|------|
| Plan | `LibreFolio_developer_journal/Release_2/phases/36_connectionSecurity/plan-phase00ConnectionSecurity.prompt.md` |
| Verdict | `frontend/src/lib/utils/security/connectionSecurity.ts` |
| Indicator | `frontend/src/lib/components/layout/ConnectionSecurityIndicator.svelte` |
| Endpoint | `backend/app/api/v1/system.py` |
| Login | `backend/app/api/v1/auth.py` |
| User doc | `mkdocs_src/docs/user/connection-security.en.md` |
