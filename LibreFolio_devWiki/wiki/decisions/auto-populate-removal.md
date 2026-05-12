---
title: "Remove auto-populate — metadata flow is frontend-driven"
category: decision
status: resolved
date: 2026-05-11
tags: [backend, assets, providers, metadata, architecture]
related:
  - features/F-024
  - features/F-025
  - problems/classification-params-race-condition
---

# Decision: Remove Auto-Populate — Metadata Flow is Frontend-Driven

## Context

`bulk_assign_providers()` in `asset_source.py` had an implicit auto-populate block (lines 980-1062) that attempted to fill asset metadata from the assigned provider's response. This caused:
1. A **race condition** (A4 in Plan C2): if the user PATCH'd `classification_params.geographic_area` just before provider assignment, the auto-populate read stale data and overwrote the user's choice
2. **Unpredictable side-effects**: assigning a provider could silently mutate metadata fields the user hadn't consented to change
3. **Inconsistency**: the auto-populate path differed from the explicit refresh path

## Options Considered

1. **Fix the race with `session.refresh()`**: Keeps auto-populate but prevents stale reads. Partial fix — doesn't address consent issue.
2. **Remove auto-populate entirely**: Metadata flow becomes exclusively frontend-driven: provider probe → diff display → explicit user PATCH. User always sees and approves changes.
3. **Add a flag `auto_populate=False` default**: Opt-in only. Adds complexity for minimal benefit since frontend already has the diff UI.

## Decision

**Option 2**: Remove the entire auto-populate block. The metadata lifecycle is now:
1. Frontend calls `refresh_assets_from_provider()` which returns `refreshed_fields` (what the provider would set)
2. Frontend displays a diff modal showing current vs proposed values
3. User approves/declines each field
4. Frontend sends explicit `PATCH /assets/{id}` with only approved changes

## Consequences

- `bulk_assign_providers()` reduced to simple assignment + result building (no provider fetch, no metadata mutation)
- Race condition eliminated structurally (no implicit write path)
- User has full control over metadata changes
- Provider probing still works via explicit `refresh_assets_from_provider()` endpoint
- 6 new tests verify the decoupled behavior: assign doesn't modify, refresh returns fields, PATCH is the only write path

## Source files

| Role | Path |
|------|------|
| Asset source service | `backend/app/services/asset_source.py` |
| Test assign/refresh | `backend/test_scripts/test_services/test_asset_source.py` |

