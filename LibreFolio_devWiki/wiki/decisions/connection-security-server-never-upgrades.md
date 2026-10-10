---
title: "Connection security: the server may confirm the browser's verdict or make it uncertain, never make it secure"
category: decision
status: resolved
date: 2026-10-09
tags: [frontend, backend, security, https, proxy, privacy, ux, auth, cookies]
related: [features/F-102, problems/login-account-enumeration-before-password, features/F-065, features/F-001, decisions/single-docker-image, sources/phase00-connection-security-2026-10]
---

# Decision: how the connection-security indicator reaches its verdict

## Context

Self-hosters reach LibreFolio over HTTPS, over a LAN, through a VPN (Tailscale/Headscale) or — by mistake — over
plain HTTP on the internet. A shield in the sidebar was to tell them which, and whether their session cookie travels
safely. The browser knows the protocol and the name it typed; only the server sees where the request came from, and
behind a reverse proxy even that is a header anyone can forge.

## Decision

- **Rule**: HTTPS and the loopback are the browser's call alone. Otherwise the server's view of the source can
  **confirm** the browser's verdict or turn it **uncertain** (a public source behind a local or VPN name, a local
  source behind a public name) — it never makes a connection secure.
- Levels: `secure` (HTTPS; `localhost`; a VPN name seen from a non-public source), `local` (LAN names; any
  uncertain case), `insecure` (a public name over plain HTTP, seen from a public source). Host classes in the
  browser: loopback, `.ts.net` and the VPN ranges, LAN suffixes and single-label names, public.
- **The endpoint returns only `{client_class, cookie_secure}`** (`GET /api/v1/system/connection`, login required).
  The client class comes from the **last** `X-Forwarded-For` value, else the TCP peer: `loopback`, `vpn` (CGNAT
  `100.64.0.0/10` and the Tailscale IPv6 prefix), `lan`, `public`. **The address itself is never returned or
  logged.** A forged header only misleads the sender's own indicator. `FORWARDED_ALLOW_IPS` was rejected.
- **Admins** see an extra line when the browser is on HTTPS but the cookie was set without `Secure`
  (`cookie_secure` false) — a proxy terminating TLS without telling the app. The cookie mode itself is
  `SESSION_COOKIE_SECURE = auto | always | never`: `auto` turns Secure on for HTTPS or when the first
  `X-Forwarded-Proto` value is `https`; the header can only turn it on, never off.
- D2: i18n keys in a `connectionSecurity.*` namespace (not `nav.*`); D3: clicking the shield on a closed sidebar
  opens the sidebar, then the details; D5: unknown logins are checked against a dummy hash
  ([[problems/login-account-enumeration-before-password]]). A login-page warning was left for a later phase.

## Consequences

- The indicator can be wrong only in the safe direction (`uncertain`), never by claiming security it cannot prove.
- No personal network data leaves the server.

## Links

- [[features/F-102]] · [[features/F-065]] (cookie auth) · Source: [[sources/phase00-connection-security-2026-10]].

## Source files

| Role | Path |
|------|------|
| Verdict (`assessConnection`, `classifyHost`) | `frontend/src/lib/utils/security/connectionSecurity.ts` |
| Store | `frontend/src/lib/stores/app/connectionSecurityStore.ts` |
| Indicator (sidebar shield, admin cookie line) | `frontend/src/lib/components/layout/ConnectionSecurityIndicator.svelte` |
| Endpoint `GET /system/connection` | `backend/app/api/v1/system.py` |
| Response schema | `backend/app/schemas/system.py` |
| Address classes (never returned) | `backend/app/utils/network_utils.py` |
| Cookie `Secure` decision | `backend/app/api/v1/auth.py` |
| Cookie mode setting | `backend/app/config.py` |
| E2E | `frontend/e2e/layout/connection-security.spec.ts` |
| User doc | `mkdocs_src/docs/user/connection-security.en.md` |
| Plan | `LibreFolio_developer_journal/Release_2/phases/36_connectionSecurity/plan-phase00ConnectionSecurity.prompt.md` |
