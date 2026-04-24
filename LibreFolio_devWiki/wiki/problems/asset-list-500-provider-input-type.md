---
title: "list_assets 500 — ProviderInputType vs IdentifierType mismatch"
category: problem
status: resolved
date: 2026-03-31
tags: [backend, assets, providers, api, enum]
related: [features/F-033, features/F-034]
---

# Problem: list_assets 500 — ProviderInputType vs IdentifierType mismatch

## Symptom

`GET /assets/query` (list assets) returned HTTP 500 with validation error:

```
Error listing assets: 1 validation error for FAinfoResponse
identifier_type
  Input should be 'ISIN', 'TICKER', 'CUSIP', 'SEDOL', 'FIGI', 'UUID' or 'OTHER'
  [type=enum, input_value=<ProviderInputType.AUTO_GENERATED: 'AUTO_GENERATED'>]
```

Only triggered when at least one asset had a provider assignment with `identifier_type = AUTO_GENERATED` (used by the `scheduled_investment` provider, whose identifier is auto-generated UUID).

## Root Cause

`asset_source.py` L2065 (at the time) passed the raw `ProviderInputType` enum directly when constructing `FAinfoResponse`:

```python
identifier_type=provider_identifier_type,  # Wrong: ProviderInputType, not IdentifierType
```

`FAinfoResponse.identifier_type` is typed as `Optional[IdentifierType]`, which does not include `AUTO_GENERATED`. The same conversion function `AssetSourceProvider.map_input_type_to_identifier_type()` was already used correctly in two other places (L1204 and L1641) but was missed at L2065.

## Solution

Apply `map_input_type_to_identifier_type()` before constructing `FAinfoResponse`:

```python
identifier_type=(
    AssetSourceProvider.map_input_type_to_identifier_type(provider_identifier_type)
    if provider_identifier_type else None
),
```

`AUTO_GENERATED` maps to `None` (no public identifier type — the UUID is internal).

## Prevention

- Any new callsite that reads `identifier_type` from a provider assignment and maps it to `FAinfoResponse` must use `map_input_type_to_identifier_type()`.
- The two enum types serve different purposes: `ProviderInputType` describes how the provider accepts an identifier (TICKER, ISIN, URL, AUTO_GENERATED), while `IdentifierType` describes the publicly visible identifier on the asset.
- When `ScheduledInvestment` provider is involved, always expect `AUTO_GENERATED` in provider tables.

## Impact

Critical: the entire assets list page was broken as soon as any user had a scheduled investment configured. Discovered during Round 10 manual testing.

## Source files

| Role | Path |
|------|------|
| Fix location | `backend/app/services/asset_source.py` |
| Enum definitions | `backend/app/db/models.py` (ProviderInputType, IdentifierType) |
| Response schema | `backend/app/schemas/assets.py` (FAinfoResponse) |
