---
title: "Account link tokens travel in the URL fragment"
category: decision
status: resolved
date: 2026-10-15
tags: [auth, security, frontend, backend, logging]
related: [domains/auth, domains/email, features/F-001, problems/login-account-enumeration-before-password]
---

# Decision: Account link tokens travel in the URL fragment

## Context

Release 1.3, workstream A, lot A5: invitations and password-reset links are single-use URLs built by
`token_service.token_path()`, which is shared by the CLI, the admin API and, later, the email workstream. The first
version put the token in the query (`/invite?token=…`). The plan's own rule says a token never reaches a log.

Reviewing the documentation (`docs-writer`, 15/10) showed that the query breaks that rule on every page load:
- the browser sends the query to the server;
- the Docker image starts uvicorn without `--no-access-log`, and `logging_config.py` does not silence
  `uvicorn.access`, so the access log records `GET /invite?token=…` in clear;
- a reverse proxy in front (Caddy, Traefik, nginx, Cloudflare) records the full request line too, out of the app's
  reach.

## Options Considered

1. **Filter the access log** (redact `token=` in `uvicorn.access`).
   - It covers the app's own log only: a proxy still records the token.
   - It is one more filter to keep in step with every new link.
2. **Token in the fragment** (`/invite#token=…`).
   - A browser never sends the fragment to the server, so no access log or proxy log ever holds it.
   - The page reads it with JavaScript and sends it in a POST body.
3. **Both.** Option 2 already removes the cause; a filter can still be added by the platform workstream for links
   typed by hand.

## Decision

Option 2.
- `token_path()` builds `<page>#token=<token>` with the same `urlencode`.
- The link pages (`routes/invite`, `routes/reset-password`):
  - read `location.hash` through `takeLinkToken()`; a `token` in the query is not read;
  - put the bare path back with SvelteKit's `replaceState`, falling back to `history`;
  - listen to `hashchange`, because a link pasted into a tab already on the page changes only the fragment and does
    not reload it;
  - send `<meta name="referrer" content="no-referrer">`.
- The token is spent by `POST /auth/tokens/inspect`, `/auth/register` and `/auth/password-reset`, always in the body.

## Consequences

- No change for callers of `token_path()` and `public_link()`, the email workstream included: the format is in one
  place.
- A5a was not integrated yet, so the switch cost one backend line, the schema descriptions of `path`, and the test
  expectations (written red-first).
- Server-side code can never see the token on page load. It never needed it: the app is a single-page app, and the
  fallback `200.html` serves the page.
- A hand-written `?token=` link is treated as a link without a token (`missing`).

## Links
- [[domains/auth]]
- [[features/F-001]]
- Source: `LibreFolio_developer_journal/Release_2/Phase_1/02_accounts/plan-phase01Accounts.prompt.md`, sections
  «A5b.3» and «A5b.1».

## Source files

| Role | Path |
|------|------|
| Link path builder | `backend/app/services/accounts/token_service.py` |
| Token reader | `frontend/src/lib/features/auth/linkToken.ts` |
| Address bar | `frontend/src/lib/features/auth/addressBar.ts` |
| Invitation page | `frontend/src/routes/invite/+page.svelte` |
| Password-reset page | `frontend/src/routes/reset-password/+page.svelte` |
| Security mkdocs | `mkdocs_src/docs/developer/architecture/security.md` |
