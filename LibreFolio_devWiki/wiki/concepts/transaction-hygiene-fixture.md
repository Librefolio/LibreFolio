---
title: "Transaction hygiene: cleanup between files, not between tests"
category: concept
date: 2026-08-31
tags: [testing, playwright, e2e, isolation, parallelism, frontend]
related: [concepts/playwright-run-consolidation, concepts/test-isolation-classes]
related_problems: [playwright-route-stub-is-per-context]
---

# Concept: the transaction hygiene net

## What it does

When several specs share one Playwright invocation
([[concepts/playwright-run-consolidation]]), they also share one database. Each
spec must therefore start from the transaction set that
`populate_mock_data` produced, not from whatever the previous spec left.

The fixture snapshots transaction ids when a spec **file** opens, and at the end
of the file deletes everything that appeared since. Where a spec destroys mock
rows outright, the recovery path goes as far as `populate_mock_data --force`.

Two design choices carry the whole thing:

- **Per file, not per test.** Cleaning between tests would fight the specs that
  build state across tests on purpose, and would multiply the cost by the test
  count instead of the file count.
- **Repopulate, not just delete.** Deleting restores the count; only
  repopulating restores the *content* a later spec reads as a precondition.

## The premise it rests on — and what removes it

The inference is *new ⇒ mine*. It holds only while **one worker runs one file
start to finish, alone**.

Per-test scheduling removes it. The moment two spec files interleave, "created
since I opened this file" also describes rows **another worker is using right
now**, and the repopulation path would empty the database underneath three
running tests.

So the fixture **disables itself above one worker** and says so:

```
[tx-hygiene] disabled: tests interleave across files at E2E_WORKERS>1, so
"created since I opened this file" would include other workers' rows.
```

Empirically it was no longer needed there: 216/216 and 298/298 green without it.

> Hygiene and cross-file interleaving are **mutually exclusive by
> construction**, and hygiene is the half that becomes unnecessary — it exists
> to protect tests from each other's leftovers, which interleaving already makes
> undecidable.

## The correct successor definition

`db-cleanup.ts` defines ownership as the **intersection of two facts**:

1. the id was returned by *my* commit, **and**
2. it was not in the initial snapshot.

That survives interleaving, because it never infers ownership from timing alone.
It is the same lesson as
[[problems/playwright-route-stub-is-per-context]]: on a table without a
`user_id`, "I did not see it before" is a statement about your own observation
window, never about the row.

## Asking for a feature that cannot fire is not free

`_consolidate.py` set `LF_TX_HYGIENE=1` **unconditionally** for the consolidated
pass, which runs at five or more workers — turning on a feature that in that mode
can never start, and printing one warning per worker per invocation.

Now gated on `E2E_WORKERS == 1`.

> The cost of an impossible request is not zero. It is paid in noise, and noise
> is paid again in the next diagnosis: five warning lines that look like a
> problem and are not, sitting on top of the run's real output.

## Source files

| Role | Path |
|------|------|
| Fixture, self-disabling guard, repopulate path | `frontend/e2e/fixtures/playwright.ts` |
| Ownership-by-intersection successor | `frontend/e2e/fixtures/db-cleanup.ts` |
| Flag gating | `scripts/test_runner/_consolidate.py` — `run_playwright_group` |
| Worker count injection | `scripts/test_runner/_common.py` — `apply_e2e_workers` |
| Mock data | `backend/test_scripts/test_db/populate_mock_data.py` |
