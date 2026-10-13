---
title: "Since 2026-10-13 www.schwab.com answers headless Chromium with a bot check: its favicon is blocked (`ERR_BLOCKED_BY_ORB`) and the broker shows the fallback icon"
category: problem
status: open
date: 2026-10-13
tags: [frontend, broker-icon, third-party, chromium, orb, gallery, release-gate, workstream-m, release-1.2]
related:
  - problems/broker-icon-race-condition
  - decisions/gallery-is-a-release-gate-with-real-data
---

# Problem: a favicon that became a bot check

## Symptom

In M's full gallery run (I5 part two, 2026-10-13: 242 green, 9 red, four causes), four shots failed waiting for
`https://www.schwab.com/favicon.ico`. Users see the fallback icon for Charles Schwab. The same tests had passed in the
nightly and in a local run of 2026-10-12, so the block is new.

## Root Cause

www.schwab.com now answers headless Chromium — with its own user agent or a desktop Chrome one — with a 200 HTML page
of about 500 bytes, a bot check; as the source of an `<img>`, Chromium blocks that answer with
`net::ERR_BLOCKED_BY_ORB`. curl still gets the real icon. The broker's icon chain falls back
([[problems/broker-icon-race-condition]]); the gallery, a release gate, goes red
([[decisions/gallery-is-a-release-gate-with-real-data]]).

## Status

Open. The real cure is U-B3, the icon inside the plugin's folder — a bundled icon, as Scalable has — which waits for
the developer's answer (question 16).

## Source files

| Role | Path |
|------|------|
| The Schwab plugin | `backend/app/services/brim_providers/broker_schwab/` |
| A bundled broker icon, the precedent | `frontend/static/icons/brokers/scalable.png` |
