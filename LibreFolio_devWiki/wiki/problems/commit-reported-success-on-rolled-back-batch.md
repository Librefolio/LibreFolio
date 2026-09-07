---
title: "`/transactions/commit` reported success on a rolled-back batch"
category: problem
status: resolved
date: 2026-08-30
tags: [backend, transactions, api-contract, frontend, regression]
related: [concepts/discard-the-answer-not-the-question, concepts/load-only-red-is-a-product-defect]
---

# Problem: `status: "success"` with `committed: false`

## Symptom

`POST /api/v1/transactions/commit` answered **200** with per-operation
`status: "success"` and real ids (`[72]`, `[73]`) while the envelope carried
`committed: false` and a populated `issues[]`.

The batch had been rolled back. The ids in the response referred to rows that no
longer existed.

## Root cause

The service's own documentation defines `success` as *applied **and**
committed*. The implementation set `success` when the operation had been
**applied**, before the commit decision was taken, and never revisited it when
the transaction was rolled back.

Anything reading the per-operation status — a client, a test, a human — was
being told the opposite of what happened.

## Fix

In `transaction_service.py`: if `issues` is non-empty **or** `commit` is false,
every `success` is demoted to `simulated`. `success_count` is computed **before**
the demotion, so the summary still reports how many operations *would* have
applied.

Reproduced and fixed at **one worker** — it was never a concurrency bug. It was
found during a parallel run and would have been found by anybody reading the
envelope carefully.

## The regression it caused, and the second lesson

The first version of the demotion was **too broad**: it fired on dry-runs too.

`TransactionBulkModal.svelte` builds `pendingTxIds` from the operations marked
`success`. With dry-runs demoted, that list came back empty and the **● pending
indicator disappeared** from the bulk modal — for about a week, unnoticed,
because nothing tests the presence of a dot.

> Narrowing a status is an API change even when the status is internal. Every
> consumer that **filters** on that value silently changes behaviour, and
> filters do not fail — they return fewer rows.

The two together are one story: a contract that lied, and a correction that
broke a consumer nobody had enumerated. Enumerating consumers before changing a
discriminator is the same discipline recorded in
[[concepts/absence-sentinel-vs-nullable-type]], where widening the type first let
the compiler list the seven call sites.

## Source files

| Role | Path |
|------|------|
| Commit/simulate logic and demotion | `backend/app/services/transaction_service.py` |
| Endpoint | `backend/app/api/v1/transactions.py` — `POST /commit` |
| Consumer that filters on `success` | `frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte` |
| mkdocs | `mkdocs_src/docs/developer/backend/transactions/` |
