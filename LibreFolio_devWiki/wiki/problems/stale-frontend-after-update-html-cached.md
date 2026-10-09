---
title: "After an update the browser kept running the old frontend: HTML entry points were cached heuristically"
category: problem
status: resolved
date: 2026-10-08
tags: [backend, frontend, http, caching, upgrade, sveltekit, deployment, issue-26]
related: [decisions/single-docker-image, problems/brim-compatible-plugins-frozen-at-upload, concepts/ci-release-pipeline, sources/phase00-brim-danske-bank-2026-10]
---

# Problem: a stale cached frontend after an upgrade

## Symptom

After upgrading the server, a Chromium user still saw the previous release's frontend until a manual reload. In
issue #26 it looked like a plugin bug: "Plugin does not work on Chromium — 2 file(s) could not be parsed", each
export answered "… is one export of a report set", while Firefox worked. The cached old frontend was parsing each
export on its own, which the new backend refuses by design (D-S4 of [[decisions/brim-report-sets]]).

## Root cause

FastAPI served the SvelteKit build's HTML entry points with no `Cache-Control`. Browsers then apply *heuristic
freshness* from `Last-Modified` and reuse their cached HTML — which names the hashed JS/CSS chunks of the **old**
build, still cached as immutable. Nothing told the browser to ask again.

## Solution (2026-10-08, `333bfc985`)

Every HTML document of a build is served with `Cache-Control: no-cache, must-revalidate` (`REVALIDATE_HTML`,
`_revalidated_file()` in `backend/app/main.py`): the browser revalidates the entry point on each load and picks up a
new build at once. The `/_app` chunks stay `public, max-age=31536000, immutable` — their names change with their
content, so caching them forever is safe.

## Prevention

In a single-image deployment ([[decisions/single-docker-image]]) the backend is the static server: the entry point
must revalidate, the content-hashed assets may be immutable. Any new route that serves HTML from the build must use
the same helper.

## Impact

Bug reports after upgrades that could not be reproduced on a fresh browser; a mismatched frontend and backend.

## Source files

| Role | Path |
|------|------|
| `REVALIDATE_HTML`, `_revalidated_file`, immutable `/_app` | `backend/app/main.py` |
| Plan (Step 9) | `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBankStep9StaleFrontend.prompt.md` |
