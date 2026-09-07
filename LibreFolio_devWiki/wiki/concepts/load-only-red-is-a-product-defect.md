---
title: "A red that only appears under load is a product defect"
category: concept
date: 2026-08-31
tags: [testing, parallelism, triage, frontend, method]
related: [concepts/test-isolation-classes, concepts/discard-the-answer-not-the-question, concepts/playwright-run-consolidation]
related_problems: [playwright-route-stub-is-per-context, brim-file-store-rename-race, commit-reported-success-on-rolled-back-batch, bulk-validate-index-map-off-by-one]
---

# Concept: parallelism reveals defects, it does not create them

## The claim

> A red that appears only under load is a **product** defect, not a test defect.
> Parallelism did not create it; it widened the window enough to make it
> reproducible.

This was used as a triage rule at least four separate times during the
2026-08 campaign, and every time it held.

## The evidence that established it

**Consolidation, not concurrency, is what pollutes.** Four writing specs run
together produced **one red at one worker**, and the same one red at four
workers. Parallelism at 4 ways added 1,62× and **zero** failures. The pollution
came from putting four specs in one process, not from running them at once.

**The night run found three defects the day hid.** A run that finished at 01:00
went red on `tx-clone`. The cause was a UTC-vs-local calendar bug, and chasing it
found the same pattern in 18 places, of which **three were product defects** —
including a dashboard that opened on a range ending *yesterday*. It had survived
for months because for 22 hours a day UTC and the local calendar agree, and the
suite almost always runs inside those 22 hours. See
[[problems/utc-today-vs-user-calendar]].

**Under coverage, latent races become deterministic.** `asset-classification.spec.ts`
passed 3/3 **without** coverage and failed 3/3 **with** it. Python instrumentation
slows the backend just enough to turn two latent races into reliable errors.

> A coverage run should be treated as a **slow environment**, not as the
> reference run. It has already paid for itself twice: two genuine product
> defects were found exactly that way.

## The two canonical cases

Both are recorded verbatim in the project's own test-authoring instructions,
because both ended with **the fix in the product, not in the spec**.

### `AssetSearchAutocomplete` — green for months on a dead search box

> `AssetSearchAutocomplete` dropped any query typed before the provider list had
> loaded: the debounce had already fired and nothing retried, so the search box
> just sat there dead. At one worker the providers always won the race, so the
> suite had been green for months. Four workers made a rare condition normal, and
> a *user-facing* bug fell out of a test run.

The important word is **always**. At one worker the providers did not usually win
the race — they won it every time. The defect was therefore not *rare* at low
load, it was **unobservable**: no amount of re-running the sequential suite could
have produced it. Meanwhile a real user on a cold page, typing immediately, got a
search field that never answered and never explained itself.

> This is the strongest form of the rule. Concurrency was not a harsher
> environment that shook loose a flake — it was the **only** environment in which
> the bug existed as a visible event. A suite that cannot reach a state cannot
> defend it.

### `useValidateScheduler` — four reds that looked exactly like four flakes

> Four WAC tests were red only under load, always the same four, green in
> isolation. `useValidateScheduler` sampled its anti-bounce key **when the
> response arrived** instead of when the request left, so an edit made while the
> server was thinking got marked as already-validated and was never re-checked.
> For a user on a slow connection: *the change you make while it is loading is
> silently not verified.* Four tests waiting on a preview that would never update
> looked exactly like four flaky tests.

This is the more damaging of the two. Nothing fails, nothing warns: the user
edits a field during a pending validation, the edit is stamped with the key of
the response that is about to land, and the system concludes it has already
checked it. The user is shown a verified state for input that was never verified.

And the shape of the failure is the reason **"flaky" cannot be a verdict**: four
tests always red under load, always green alone, always the same four. That is
the exact signature people learn to dismiss. Re-running them would have
"confirmed" flakiness forever.

It is also the same family as
[[concepts/discard-the-answer-not-the-question]] — an identity sampled at the
wrong end of an async round trip, so a late arrival is allowed to speak for
something that happened after it.

## What the two have in common

Both sample or resolve something at the **wrong moment relative to an async
boundary**, and in both cases low load hid it by making the race deterministic in
the favourable direction. Neither is a write conflict; neither is a test
isolation problem; neither would have been found by making the specs stricter.

> Concurrency did not break them. It made a rare condition normal — and in the
> first case, it made an impossible condition merely rare.

## Where it does *not* apply

The rule is a triage **hypothesis**, not a verdict. It has to be falsified like
any other:

- `POST /transactions/commit` returning 200 `success` on a rolled-back batch
  failed identically **at one worker** — so it was never about concurrency at
  all. See [[problems/commit-reported-success-on-rolled-back-batch]].
- The AI Export timeout looked like a slow endpoint. Three hypotheses were
  tested and all fell; what remained was that the same spec costs 6,7 s bare and
  **44,8 s under coverage** — instrumentation, not the product.

The discipline that makes the rule usable is the same one that makes it
falsifiable: *before raising a timeout, measure the endpoint*.

And the converse trap: a defect found **by reading code** in the same area as a
load-only red is not thereby a load-only red. The bulk-validation index-map
off-by-one ([[problems/bulk-validate-index-map-off-by-one]]) lives in the same
file as `useValidateScheduler` and was found by the pure-logic lane, statically.
Filing it under this rule would have made the rule look better than it is.

> A timeout on a path you expect to succeed is never a performance assertion.
> You only wait on it when something is already broken, so raising it costs
> nothing when things work and only bounds how long it takes to **report** a
> real failure.

Its missing half, learned here: **the enclosing budget has to be raised too**. If
`test.setTimeout` fires before `waitForResponse`, the diagnosis degrades from
"this endpoint stopped" to "the test was too long" — which says nothing.

## Source files

| Role | Path |
|------|------|
| **Verbatim source of both cases** | `.github/agents/test-author.agent.md` (~538-552) |
| Reprise of the first case | `.github/skills/devpy-tools/testing-frontend/SKILL.md` (~313) |
| Triage protocol | `.github/skills/devpy-tools/test-triage/SKILL.md` |
| Isolation classes | `scripts/test_runner/_inventory.py` |
| Anti-bounce key sampling | `frontend/src/lib/utils/transactions/useValidateScheduler.svelte.ts` |
| Debounced query, provider list | `frontend/src/lib/components/assets/AssetSearchAutocomplete.svelte` |
| WAC preview consumer | `frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte` |
| Shared date helpers for specs | `frontend/e2e/fixtures/dates.ts` |
