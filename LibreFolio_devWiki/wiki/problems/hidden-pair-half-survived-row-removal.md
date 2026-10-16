---
title: "Removing a new pair from the bulk editor left its hidden other half: a false «Discard changes?» on an empty workspace (V-29, since 1.1.0)"
category: problem
status: resolved
date: 2026-10-13
tags: [frontend, transactions, bulk-editor, pairs, close-guard, ux, workstream-v, release-1.2]
related:
  - features/F-048
  - sources/phase00-data-quality-e2e-2026-10
---

# Problem: half a pair outlived the row

## Symptom

In the bulk editor, a new transfer marked for deletion, or removed with «Delete selected», disappeared from the grid;
closing the editor then asked «Discard changes?» on a workspace with nothing in it. No data was touched — the false
prompt shipped with 1.1.0, and workstream V's E2E found it (V-29).

## Root Cause

A pair entered through the form is two operations: the visible row, and its partner, created hidden by
`addDualRowFromForm`. `removeRow` filtered the operations by the removed row's `tempId` only, so the hidden partner
stayed. It was never saved, but `serializeOps` serialises every operation, so the close guard compared a non-empty
key with the one taken at opening and asked to discard changes.

## Solution

`e6019f349` («fix(transactions): remove both halves of a pair», train 82): `removeRow` also drops the operation whose
`pairedWith` is the removed row. The 1.2 CHANGELOG lists it as a fix (`ed8fc5cd7`).

## Prevention

- Whatever creates two linked records must remove both: a removal keyed on one id leaves the other behind.
- A close guard that compares serialised state sees hidden state too — which is how this one was noticed.

## Source files

| Role | Path |
|------|------|
| The bulk editor (`removeRow`, `addDualRowFromForm`) | `frontend/src/lib/features/transactions/bulk/TransactionBulkModal.svelte` |
| Plan 46 (§12.10) | `LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` |
