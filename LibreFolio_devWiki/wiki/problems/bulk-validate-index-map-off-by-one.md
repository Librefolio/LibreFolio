---
title: "Two functions walking one list at different speeds: the WAC preview attached to the wrong transaction"
category: problem
status: resolved
date: 2026-08-29
tags: [frontend, transactions, bulk, validation, off-by-one, product-defect]
related: [concepts/discard-the-answer-not-the-question]
related_problems: [commit-reported-success-on-rolled-back-batch]
---

# Problem: the `"operation:index" → tempId` map was off by one

## How it was found

**By reading code**, in the pure-logic lane — not by a failing test, and not
under load. This matters enough to state up front: the defect lives in the same
file family as `useValidateScheduler`, which *was* a load-only red
([[concepts/load-only-red-is-a-product-defect]]), and the two are unrelated. Two
different defects that happened to share a neighbourhood.

## The defect

`TransactionBulkModal`, **validation** path only:

- line 1170 — `resolveOps({splitTxIds})` is called **without** `promoteTxIds`, so
  the edit rows trailing a promote stay in the resolved list;
- line 1116 — `buildOpsIndexMap` derives `promoteTxIds` **by itself** and
  **skips** those rows, without advancing its own cursor.

Two functions walk the same list at different speeds. From that point on the
`"operation:index" → tempId` map is **off by one**.

That map is what the WAC preview and the validation messages hang off. So a user
validating a bulk with a promote in the middle sees **the preview attached to the
wrong transaction** — a plausible number, on the wrong row.

The **commit** path (line 1397) passes both and is coherent. Only validation
diverged. Validation was also checking rows the commit does not send, which is
the wrong question asked twice:

> A preview must simulate the commit, not something that resembles it.

## Fix

The two traversals were aligned: validation now derives its operation set the
same way the commit does, so the index map cannot drift.

## The pattern it belongs to

It was the **fifth** defect found in this one file during the campaign, all of
the same family: **two paths that should say the same thing and do not**. The
sixth, found separately, is
[[problems/commit-reported-success-on-rolled-back-batch]] — the commit endpoint
reporting `success` on a rolled-back batch.

A sibling defect from the same lane, same flavour of "declared and not honoured":
`ColumnDef.sortFn` was declared and **never read**, so sorting the import wizard
by status produced alphabetical order — putting the rows that *require action*
last, which is the opposite of what sorting by status is for.

> When one file accumulates five defects of one shape, the shape is the finding.
> Duplicated traversal logic in a modal that both previews and commits is a
> structural invitation to divergence, and fixing instances one at a time will
> keep producing a sixth.

## Source files

| Role | Path |
|------|------|
| Validation path (1116, 1170) and commit path (1397) | `frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte` |
| Operation resolution | `frontend/src/lib/utils/transactions/txPayloadHelpers.ts` |
| Sibling defect (`sortFn`) | `frontend/src/lib/components/table/types.ts`, `TableBody.svelte` |
| Commit service | `backend/app/services/transaction_service.py` |
