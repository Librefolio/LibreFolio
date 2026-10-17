---
title: "A transfer already merged came back as new on re-import, doubling the cash"
category: problem
status: resolved
date: 2026-10-09
tags: [brim, import, duplicates, cash-transfer, fx-conversion, backend, workstream-s, release-1.2]
related:
  - decisions/scalable-two-accounts-two-plugins
  - decisions/bulk-pairs-new-with-saved
  - decisions/cash-transfer-split-promote
  - sources/phase00-brim-scalable-2026-10
---

# Problem: a merged transfer was not recognised as a duplicate

## Symptom

An import «since the last» export restarts from the day of the last export, included. A DEPOSIT or WITHDRAWAL already
merged into a `CASH_TRANSFER` pair came back as new, and the cash of both brokers doubled. Found by plan 37's analysis
(fact F7).

## Root Cause

`detect_tx_duplicates` (`brim_provider.py`) looked for duplicates by broker, **same type**, date, quantity and amount.
After a promote the saved leg is a `CASH_TRANSFER` (or an `FX_CONVERSION`), no longer a DEPOSIT or a WITHDRAWAL, and its
description is the merge of the two sides' texts.

## Solution

Commit `305b80202` (2026-10-09, plan 37 §9, for every plugin): an incoming DEPOSIT or WITHDRAWAL also looks at the saved
`CASH_TRANSFER` and `FX_CONVERSION` legs (`_MERGED_LEG_TYPES`) with the same sign, date and amount. On a merged leg the
description matches when it *contains* the incoming one — merged texts are joined with a newline — and the match is
then **«probable»**. A «possible» duplicate stays selected for import by default, so it would still have doubled the
cash.

## Prevention

- `TestMergedPairDuplicates` (DD-011…DD-017): each side is probable against its merged leg; a rewritten description
  gives «possible»; the opposite sign is unique; an FX pair; FEE, TAX and INTEREST never look at merged legs; the same
  type with a merely contained text stays possible; an empty text is never probable.
- The API flow SC-A01: two brokers, the pairs merged, then a re-import whose transfers are probable duplicates of the
  merged legs.

## Impact

Every re-import over an internal transfer already merged would have doubled the cash, for any plugin. The fix shipped
with the Scalable importers (train 30), whose two-broker flow makes such re-imports routine.

## Source files

| Role | Path |
|------|------|
| `detect_tx_duplicates`, `_MERGED_LEG_TYPES` | `backend/app/services/brim/brim_provider.py` |
| `TestMergedPairDuplicates` | `backend/test_scripts/test_db/test_brim_db.py` |
| SC-A01, SC-B01 | `backend/test_scripts/test_api/test_brim_scalable_api.py` |
