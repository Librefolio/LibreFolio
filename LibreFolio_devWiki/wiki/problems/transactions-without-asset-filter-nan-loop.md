---
title: "Transactions without-Asset filter caused a NaN URL loop"
category: problem
status: resolved
date: 2026-08-03
tags: [frontend, transactions, datatable, filtering, url-state, nan]
related:
  - features/F-047
  - decisions/transactions-client-side-filtering
---

# Problem: Transactions without-Asset filter caused a NaN URL loop

## Symptom

Selecting the Transactions table filter for rows without an Asset froze the page.
The filter and URL synchronization kept navigating even when the user-visible
selection had not changed.

## Root Cause

DataTable represents the null Asset option with the `__null__` sentinel. The filter
adapter passed that sentinel through `Number()`, producing `NaN`. The no-op guard
then compared successive values with strict equality; because `NaN !== NaN`, every
reactive pass looked like a new filter and restarted URL/navigation synchronization.

## Solution

The filter state now models null selection explicitly as `without_asset: boolean`.
URL state uses `without_asset=true`; numeric `asset_id`/`asset_ids` contain only
real IDs. Mixed null-plus-ID selections preserve both fields, and identical
DataTable emissions return `null` rather than navigating again.

## Prevention

- Normalize null sentinels before numeric conversion.
- Keep semantic null state separate from numeric identifiers.
- Require URL/filter round-trip and repeated-no-op tests for reactive filters.
- Never rely on ordinary equality guards for values that may become `NaN`.

## Impact

The fix removes the navigation feedback loop without moving filtering to the
backend or changing the client-side filtering architecture.

## Source files

| Role | Path |
|------|------|
| Filter state and URL mapping | `frontend/src/routes/(app)/transactions/filterState.ts` |
| Page synchronization | `frontend/src/routes/(app)/transactions/+page.svelte` |
| Regression tests | `frontend/src/routes/(app)/transactions/filterState.test.ts` |
| Test registration | `scripts/test_runner/_frontend_transaction.py` |
