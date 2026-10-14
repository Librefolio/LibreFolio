---
title: "BRIM text exports were opened as UTF-8 only: Windows-1252 and Latin-1 CSVs failed to parse"
category: problem
status: resolved
date: 2026-09-28
tags: [backend, brim, csv, encoding, plugins, i18n, issue-26]
related: [features/F-013, features/F-012, decisions/brim-report-sets, sources/phase00-brim-danske-bank-2026-10]
---

# Problem: hard-coded `utf-8-sig` in the BRIM plugins

## Symptom

A broker export saved by a Windows bank portal (Windows-1252 / Latin-1: `€`, `ä`, `ö`, `é` in descriptions and
headers) failed to parse, or its header was not recognised, so no plugin claimed the file. First seen on the Danske
Bank exports of issue #26.

## Root cause

27 plugins (31 call sites) opened their files with a fixed `open(path, encoding="utf-8-sig")`. A byte that is not
valid UTF-8 raised a decode error, or a header with an accented column name no longer matched.

## Solution (2026-09-28, `6ea71ea8d`)

- One ordered list, `TEXT_ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")` in `backend/app/services/brim_provider.py`,
  and helpers built on it: `_read_text` (whole file), `_open_text` (a `StringIO` for `csv` readers),
  `_read_file_head`, `detect_csv_delimiter`. UTF-8 is tried first (with or without BOM), then Windows-1252, and
  **Latin-1 last, because it decodes any byte sequence** — it would mask every other choice if it came earlier.
- Every plugin reads through these helpers; a guard test fails if a plugin opens a file with a fixed encoding
  (`test_no_plugin_opens_files_with_a_fixed_encoding`).

## Prevention

Never assume an encoding for a file a user uploads. Read through the shared helpers; a new plugin that calls
`open(..., encoding=…)` turns the guard red.

## Impact

Imports of whole banks failed before the user could do anything; a user had to re-save the export as UTF-8 by hand.

## Source files

| Role | Path |
|------|------|
| `TEXT_ENCODINGS`, `_read_text`, `_open_text` | `backend/app/services/brim_provider.py` |
| Plugin readers that delegate to them | `backend/app/services/brim_providers/_brim_io.py` |
| Encoding tests (`TestTextEncodingFallback`) | `backend/test_scripts/test_services/test_brim_provider_base.py` |
| Guard against fixed encodings | `backend/test_scripts/test_external/test_brim_providers.py` |
| Plan (§4, CSV encoding) | `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBank.prompt.md` |
