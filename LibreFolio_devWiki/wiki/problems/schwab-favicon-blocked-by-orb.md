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

*Correction (2026-10-13, train 84, M's lot 35): the four reds were also our own.* Since `2412c3fe4` (2026-10-12,
[[problems/late-img-error-marked-the-visible-icon-failed]]) the
icon chain acknowledges a load or an error only when the image's `getAttribute('src')` equals its own URL
(`brokerIconChain.svelte.ts`). The gallery's favicon fix wrote the URL with a `?lf-gallery` mark, so in the gallery no
load and no error was ever acknowledged: every logo drawn from a favicon stayed a briefcase (eight on the brokers
list, where the published 1.1 gallery shows the logos), and Schwab's refused favicon never moved down its chain. The
cure, `6bb79fecd`: `keepFaviconImagesLoading` gives the URL back unmarked when it is read, while the stored attribute
keeps the mark, and `expectFaviconImagesLoading` checks both. The targeted rerun passed 42 of 42. M's eye check after
the cure: the other logos are back, and Schwab, whose favicon Chromium still refuses, falls down its chain to the
plugin's generic icon.

## Status

Open for Schwab itself. The real cure is U-B3, the icon inside the plugin's folder — a bundled icon, as Scalable
has — which waits for the developer's answer (question 16).

## Source files

| Role | Path |
|------|------|
| The Schwab plugin | `backend/app/services/brim_providers/broker_schwab/` |
| A bundled broker icon, the precedent | `frontend/static/icons/brokers/scalable.png` |
| The icon chain | `frontend/src/lib/utils/broker/brokerIconChain.svelte.ts` |
| The gallery's favicon mark | `frontend/e2e/fixtures/galleryReportSets.ts` (`FAVICON_MARK`, `keepFaviconImagesLoading`) |
| M's lot 35 | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` |
