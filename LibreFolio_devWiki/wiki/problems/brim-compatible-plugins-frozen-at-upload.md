---
title: "A file's compatible plugins were frozen at upload: files uploaded before an update never offered the new plugin"
category: problem
status: resolved
date: 2026-10-06
tags: [backend, brim, plugins, detection, sidecar, concurrency, upgrade, issue-26]
related: [features/F-012, features/F-013, decisions/brim-report-sets, problems/brim-file-store-rename-race, problems/stale-frontend-after-update-html-cached, sources/phase00-brim-danske-bank-2026-10]
---

# Problem: `compatible_plugins` frozen at upload

## Symptom

After upgrading to 1.2, Danske Bank exports uploaded under 1.1 were still offered only the plugins of 1.1: the new
Danske plugin never appeared for them, and the user could not tell why.

## Root cause

BRIM detects which plugins can read a file (`can_parse` of every plugin) **once, at upload**, and stores the list in
the file's sidecar (`compatible_plugins`). A release that adds or changes a plugin's `can_parse`, the base reader or
the plugin list makes that stored list stale — and nothing ever re-detected it.

## Solution (2026-10-06, `b0abeb07d`, Step 5 of plan 26)

- The sidecar records the **signature** of the plugin catalogue that detected it: `plugins_signature =
  detection_signature()`, which is the **app version** (D2). `plugin_version` could not serve: its contract covers
  the parse output, not detection.
- On the first read of an original detected by another version, the file is detected again and the new list saved
  (D1); the one-off thread cost after an upgrade is accepted (D3). **Combined files** of a report set are never
  re-detected.
- Same step: sidecar writes are serialised **per broker** — a re-entrant lock in-process and an advisory
  `fcntl.flock` on `broker_reports/.locks/broker_<id>.lock` across processes (a test server may run several
  workers). Reads take no lock: every write is an atomic rename, so a reader sees the old sidecar or the new one, and
  a write never lands on a sidecar that moved meanwhile ([[problems/brim-file-store-rename-race]]).

## Prevention

Anything derived from the code and stored with data (a detection result, a capability list) needs the version of
the code that derived it, and a rule for when to derive it again.

## Impact

New plugins were invisible for existing files after every upgrade. Files from 1.1.0 also lack a `batch_id`, so to
form a report set they still have to be uploaded again together.

## Source files

| Role | Path |
|------|------|
| `detection_signature`, upload metadata, re-detection, per-broker sidecar lock | `backend/app/services/brim_provider.py` |
| Developer doc (lifecycle of `compatible_plugins`) | `mkdocs_src/docs/developer/backend/brim/architecture.md` |
| Plugin guide | `mkdocs_src/docs/developer/architecture/patterns/brim_plugin_guide.md` |
| Tests (signature, re-detection, sidecar races) | `backend/test_scripts/test_services/test_brim_parse_race.py` |
| Plan (Step 5) | `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBankStep5PluginRedetection.prompt.md` |
