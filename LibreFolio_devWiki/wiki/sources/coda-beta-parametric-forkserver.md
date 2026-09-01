---
title: "Beta coda — parametric providers, forkserver orphans, and four discarded questions"
category: source
source_type: plan
date_ingested: 2026-08-31
original_path: "LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/coda-beta-parametrici-forkserver.md"
tags: [testing, parallelism, backend, frontend, races, brim, method]
related:
  - concepts/discard-the-answer-not-the-question
  - concepts/transaction-hygiene-fixture
  - concepts/load-only-red-is-a-product-defect
  - problems/conftest-autouse-write-breaks-pure-class
  - problems/brim-file-store-rename-race
---

# Source: the beta coda — parametric providers and forkserver

## Summary

The tail of the campaign: four defects sharing one shape, a set of forkserver
orphans, the `conftest.py` purity exception, a BRIM file-store race, and the
measurements that settled how much parallelism actually buys.

## Key Takeaways

- **Four defects, one shape**: *discarding a stale answer is right; discarding
  the question with it is data loss*. The risk catalogue that never arrives, the
  comparison that vanishes between click and response, the distribution row that
  does not exist yet when you save, and the data editor that loses pending
  deletions. Full account in
  [[concepts/discard-the-answer-not-the-question]].
- **Forkserver orphans.** Processes surviving their parent, found by inventory
  rather than by failure.
- **`conftest.py` is an exception to the `PURE` proof** —
  [[problems/conftest-autouse-write-breaks-pure-class]], with its three sharp
  edges: no `busy_timeout`, a connection never closed, and a bare
  `except sqlite3.Error: pass`.
- **The BRIM file-store rename race** —
  [[problems/brim-file-store-rename-race]] — plus a non-atomic metadata write
  fixed with `_write_metadata_atomic()`.
- **`[tx-hygiene] disabled: …` is not an error.** It is the fixture announcing
  that its premise no longer holds above one worker —
  [[concepts/transaction-hygiene-fixture]]. It was being requested
  unconditionally by a five-worker pass, printing five warnings per invocation.

## The AI Export timeout, and how a slow endpoint is ruled out

A `waitForResponse: Timeout 30000ms` on `/api/v1/ai-export/snapshot`, with
`waitForRequest` already passed — the POST had left, the answer had not come
back. Three hypotheses were tested and all fell:

| hypothesis | evidence sought | outcome |
|---|---|---|
| listener registered late | line order in `helpers.ts` | **false** — both registered before the click |
| endpoint genuinely slow | direct measurement | **false** — 0,32 s alone, 1,06 s cold, 4,0 s with 8 concurrent callers |
| DB bloated by earlier categories | category order in the log | **false** — `populate_mock_data --force` runs first, on a fresh DB |

What remained was decisive: the **same spec costs 6,7 s bare and 44,8 s under
coverage**. Python plus JS tracing multiply every pure-Python path roughly 7×,
and at that factor a 30 s budget lands **inside the tail** of the distribution —
the two sibling specs passed at 36,2 s and 37,2 s.

The instrument that closed it was three lines of throwaway benchmark
(`ThreadPoolExecutor` at 1 / 3 / 8 ways, session cookie not bearer token),
against half a day of code reading.

> A timeout on a path you expect to succeed is never a performance assertion —
> and the enclosing `test.setTimeout` has to be raised with it, or the diagnosis
> degrades to "the test was too long".

## A note on `-q`

Running with `-q` preserves the red but loses the context of the greens that
preceded it — which is precisely what is needed when the suspicion is a cascade.

## Source files

| Role | Path |
|------|------|
| Session generation and in-flight slots | `frontend/src/lib/stores/app/clientSession.ts`, `frontend/src/lib/stores/risk/riskStore.svelte.ts` |
| BRIM file store | `backend/app/services/brim_provider.py` |
| Backend test conftest | `backend/test_scripts/conftest.py` |
| Hygiene fixture and gating | `frontend/e2e/fixtures/playwright.ts`, `scripts/test_runner/_consolidate.py` |
| AI Export endpoint | `backend/app/api/v1/ai_export.py` |
| Original plan | `LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/coda-beta-parametrici-forkserver.md` |
