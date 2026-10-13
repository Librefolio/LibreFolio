---
title: "`POST /portfolio/wac` answered anyone who could reach the server, for any broker — closed on 2026-09-18 inside a PAC commit, and missing from the CHANGELOG until the 1.2 review"
category: problem
status: resolved
date: 2026-10-13
tags: [security, backend, api, authentication, broker-access, changelog, release-1.2]
related:
  - decisions/changelog-entry-rules
---

# Problem: an average-cost endpoint without a session

## Symptom

The line-by-line review of the 1.2 CHANGELOG ([[decisions/changelog-entry-rules]]) found that `POST /portfolio/wac` —
a broker's average purchase cost and quantity held over time — had answered without a session, for any broker, since
its first version.

## Solution

Closed on 2026-09-18 in `0088748a8`, a commit of the PAC work («feat(pac): redesign FX/funding to canonical rate
map»): `get_portfolio_wac` now takes the signed-in user and checks the brokers asked for. No CHANGELOG line said so;
since `60f734e08` the 🔒 section does: «The average purchase cost API now requires signing in».

## Prevention

- A security fix gets its own line in the CHANGELOG, whatever commit carries it.
- A release's notes are checked against the code and the last tag, line by line.

## Source files

| Role | Path |
|------|------|
| The endpoint (`get_portfolio_wac`) | `backend/app/api/v1/portfolio_api.py` |
| The 🔒 line | `CHANGELOG.md` |
