---
title: "Merging two assets: deleting the source's provider assignment cascaded onto the events just moved, and duplicate events could not be dropped before their transactions moved (AM-009, AM-006)"
category: problem
status: resolved
date: 2026-08-08
tags: [backend, database, foreign-keys, cascade, restrict, assets, merge, testing, release-1.1]
related:
  - decisions/asset-identity-quoted-code-leads
  - features/F-024
  - features/F-051
---

# Problem: a merge that destroyed the history it was asked to preserve

## Symptom

While `POST /assets/merge` was being written (P3, `0e07359b4`, 08/08/2026), its tests found two ways for the merge to
go wrong, both silent or fatal depending only on the **order** of the steps. Neither reached a user.

## Root Cause

A merge moves four kinds of rows from the source asset to the target — transactions, prices, events and the provider
assignment — then deletes the source. Two foreign keys make the order load-bearing:

- **CASCADE (AM-009).** `AssetEvent.provider_assignment_id` is `ondelete=CASCADE`. The target may hold only one
  provider assignment (`uq_asset_provider_asset_id`), so the source's has to go when the target already has one.
  Deleting it **before** the migrated events were re-pointed destroyed them with it, without an error.
- **RESTRICT (AM-006).** `Transaction.asset_event_id` is `ondelete=RESTRICT` (an event cannot be deleted while a
  transaction realizes it; see [[features/F-051]]). When both assets carry the same coupon, the source's copy is a
  duplicate to drop, but dropping it before remapping the transactions that point at it raises a foreign-key
  violation.

## Solution

The merge service orders its stages so that both keys are satisfied: events are re-pointed before the source's
provider assignment is deleted, and transactions are remapped onto the surviving event before a duplicate event is
dropped. The whole merge commits once, and `dry_run` rolls back after computing the counts. Tests AM-009 and AM-006
pin the two orders.

The plan lists two more traps closed in the same work: `identifier_other` is the JSON **list**, not a string column,
so any code that enumerates the identifier columns must leave it out; and the API client generator did not escape
double quotes inside a `Field(description=…)`, so a quote there produced invalid TypeScript (not re-tested since).

## Prevention

- Before moving or deleting rows, list every foreign key **to** the table and read its `ondelete`: a CASCADE can
  delete rows you have just moved; a RESTRICT dictates which remap must come first.
- Test the order, not only the outcome: AM-009 checks that the events survive, which is the part a CASCADE removes
  without a sound.

## Source files

| Role | Path |
|------|------|
| Merge service | `backend/app/services/assets/crud.py` (`merge_assets`) |
| Merge endpoint | `backend/app/api/v1/assets/crud.py` |
| Foreign keys | `backend/app/db/models.py` (`AssetEvent.provider_assignment_id`, `Transaction.asset_event_id`) |
| Tests AM-006, AM-009 | `backend/test_scripts/test_db/test_asset_merge.py` |
| Plan | `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/plan-phase00AssetIdentityAndIdentifiers.prompt.md` |
| Developer docs | `mkdocs_src/docs/developer/frontend/components/features/asset-identity.md` |
