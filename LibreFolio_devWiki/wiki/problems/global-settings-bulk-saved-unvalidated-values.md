---
title: "Global settings bulk PATCH stored unvalidated values and applied part of a refused batch"
category: problem
status: resolved
date: 2026-10-09
tags: [backend, settings, api-contract, validation, atomicity, silent-failure]
related: [decisions/settings-write-path-contract, features/F-006, sources/phase00-wac-unification-2026-10]
---

# Problem: the global settings bulk write trusted its input

## Symptom

`PATCH /api/v1/settings/global/bulk` — the endpoint the admin's Global Settings tab and the `globalSettings` store
write through — stored any string for any key. A negative session TTL, a non-numeric interval, `"maybe"` for a
boolean: all accepted with 200. The batch was also not atomic: an unknown key answered 404, but the items before it
had already been saved (per the plan's analysis).

The damage surfaced later and far away: the read side (`_convert_value()` in
`backend/app/services/global_settings_service.py`) turns an unreadable `int` into **0**, an unrecognised `bool`
into **False** and broken JSON into `{}` — silently. A typo in the admin tab became a zero timeout or a disabled
feature, with nothing in the logs.

## Root cause

The service wrote each item as it came, one key at a time, with no type or range check: the server had no notion of
a valid value for a global setting. The per-key limits (`SettingConstraint`, `GLOBAL_SETTINGS_CONSTRAINTS` — e.g.
`session_ttl_hours` 1…8760, `max_file_upload_mb` 1…1024) were introduced by the fix.

## Solution (2026-10-09, `84d9e3360`)

- `validate_global_setting_value(key, value, value_type)` (`backend/app/schemas/settings.py`) checks the storage
  type first, then the key's entry in `GLOBAL_SETTINGS_CONSTRAINTS`, and normalises what cannot change meaning:
  booleans as `true`/`false`, integers as plain digits, currencies upper-case, whitespace trimmed.
- `update_global_settings()` (`backend/app/services/settings_service.py`) is **all or nothing**: unknown keys are
  checked first (`GlobalSettingNotFoundError` → **404**), then every value (`GlobalSettingValueError`, listing
  **every** refusal → **422**); only then are the values written, in one commit.
- 363 lines of API tests in `test_settings_api.py`.

The read-side coercion is unchanged: it is now a fallback for rows written before the fix, not a path an admin can
reach through the bulk endpoint.

## Relation to the settings write-path contract

[[decisions/settings-write-path-contract]] (C3/C4) says a batch save must not stop at the first refusal and must
say what landed. The server now honours the first half by validating every item and naming every refusal; on the
second half it chose atomicity — a refused batch lands **nothing** — so the "partially applied batch" C3/C4
complained about cannot happen on this endpoint.

## Prevention

- Validate on the server what the server stores; a UI widget's limits are a convenience, not a rule.
- A bulk endpoint commits once, after validating everything.

## Impact

Admin-only, latent: an invalid value would have degraded a global setting to a zero/false default without warning.
Backlog 38 keeps **P-4** (the timezone check `_check_timezone` runs only when the server has the IANA database,
and `tzdata` is not in the `Pipfile`). Source: [[sources/phase00-wac-unification-2026-10]].

## Source files

| Role | Path |
|------|------|
| `validate_global_setting_value`, `GLOBAL_SETTINGS_CONSTRAINTS` | `backend/app/schemas/settings.py` |
| `update_global_settings` (all or nothing) | `backend/app/services/settings_service.py` |
| `PATCH /settings/global/bulk` (404 / 422) | `backend/app/api/v1/settings.py` |
| Read-side coercion `_convert_value` | `backend/app/services/global_settings_service.py` |
| API tests | `backend/test_scripts/test_api/test_settings_api.py` |
| Plan | `LibreFolio_developer_journal/Release_2/phases/30_wacUnification/plan-phase00SettingsBulkValidation.prompt.md` |
