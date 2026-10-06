---
title: "A discarded risk answer rendered as «No results» — and the boot race it was blamed on"
category: problem
status: resolved
date: 2026-09-23
tags: [frontend, risk, async, races, session, auth, asset-set, testing, method]
related:
  - concepts/discard-the-answer-not-the-question
  - concepts/span-as-a-detector
  - problems/tab-writes-after-the-look
  - decisions/asset-global-page-shows-no-money
---

# Problem: a complete risk answer rendered as «No results»

> Declared in R2-101 as *"the boot identity–query race"* — round-2 devWiki debt that S5
> deferred rather than reopen a frozen tree. Filed 2026-09-23 from R2-62, R2-66, R2-93,
> R2-95 and S5's plan. **The rendering defect is real, fixed and verified in code. The
> boot race recorded as its trigger is not supported by the code** — see *Verification*.

## Symptom (R2-62, 18/09)

A request captured from the page's own XHR — not fabricated — on Asset Global:
`asset_set [1,2,6,7]`, `2026-08-18 → 2026-09-18`, `historical`. The response was
`partial` with **16 of 16 cells `status: "ok"`** (`0.9507 / 0.9647 / 0.9347`,
`observations 32`, `coverage 1`). On screen: `risk-correlation-empty` («No results») in
the new section **and** `risk-correlation-section-empty` in the legacy panel. Both fell,
so the cause sat upstream of both.

Not an empty result that looks like a fault: **a full result that declares itself
absent.** And no client-side threshold could have excused the message — a threshold would
have had to say "insufficient history", not "no results".

## Root cause

### Three outcomes, two handled (verified in code)

`queryRisk` (`riskStore.svelte.ts`) answers in three ways: a response, a throw, and a
**discard** — it returns `null` when the client-session generation *or* the risk cache
generation moved while the request was in flight. `loadBase`
(`riskPanelController.svelte.ts`) knew two: it did `historical?.items ?? []`, so the
discard became "no data" — *"a statement about the world, when the fact is about the
client."* The input signature had not changed, so nothing re-asked: the empty stayed until
the user changed dates or selection.

A second ambiguity lived in the same `null` (R2-93): inside `loadBase` it already meant
"not asked" (the ternaries on the analytics lists) as well as "asked and discarded". Only
the lengths of the analytics lists tell the two apart.

### The trigger, as recorded (R2-66 — S5's diagnosis)

Recorded as arming itself on every reload: `clientSession.transition` bumps the generation
on the **first** identity resolution without running the resetters; on a reload that first
resolution happens in `checkAuth()` (`auth.ts`), which awaits `GET /auth/me`; and — the premise —
`(app)/+layout.svelte` fires `checkAuth()` from `onMount` with *no auth guard in the
markup*, so the children mount and query at generation 0, and the answer is discarded when
`/auth/me` resolves. That was said to explain why the coordinator's first gate (after a
**login**) showed the matrix and the second (after a **reload**) did not.

The recorded proof: `riskStore.test.ts` › *"drops stale responses after an account
transition"* passes — the discard works — but every test in the file establishes identity
**first** and queries **after**: *"nobody had tested the moment in which the identity does
not exist yet."* Level of proof declared by S5: structural elimination plus a live read of
payload and catalogue, **not reproduced in a browser**. Three falsifiable five-second
predictions were written; no record of their execution exists.

## ⚠️ Verification (2026-09-23 — reading, not execution)

The recorded premise does not match the code, at S5's baseline `7d75a9c6c` or at
`f1047f766` (neither `auth.ts` nor `clientSession.ts` changed in between):

- `(app)/+layout.svelte` renders `<slot />` only inside `{:else if $isAuthenticated}`.
  `{#if $i18nLoading}` is indeed the only top-level `{#if}` — but it is the head of a chain,
  and the chain's next branch is the auth guard.
- `isAuthenticated` is `user !== null` (`auth.ts`), and both `checkAuth()` and `login()` call
  `transitionClientSession(user.id)` **before** they set `user`.

So a child of `(app)` cannot query at generation 0 on this path. F's plan reached the same
reading on 23/09 (F-2, *"reading, not execution"*). The recorded mechanism is nevertheless
written into two source comments: the discard branch of `loadBase`, and the unit test *"discards
an answer to a question asked before the identity existed"*.

A path that **is** reachable at page load produces the same `null`: the Assets page's
live-price `$effect` posts `/api/v1/assets/prices/current` on mount (then every 30 s while the
range ends today); the axios response interceptor classifies that as a portfolio mutation;
`riskStore` listens with `invalidateRisk()`, which bumps the cache generation; an in-flight
`queryRisk` whose answer lands afterwards returns `null`. Case 1b of
[[concepts/discard-the-answer-not-the-question]] recorded this mechanism for the risk
catalogue on 2026-08-31. **Whether it was the trigger of R2-62 was never measured.**

## Solution (S5, passo 1c, 18/09 — verified at `f1047f766`)

The guard was **not** touched: discarding another account's answer is correct. What changed
is that the discard can now say so.

- `loadBase` reads a `null` for a non-empty analytics list as a discard, **re-asks once**
  under the current generation, and if discarded again sets `loadDiscarded` — a state kept
  apart from `loadError` (nothing failed) and from an empty result (nothing is missing). The
  shape was already in the file: `catalogState` keeps "slow" apart from "failed".
- `AssetSetCorrelationSection` gained a fifth branch, `risk-correlation-discarded`, with a
  `risk-correlation-retry` button. No i18n key was created: asked for a message saying
  "reloading" *"because the cure is to retry, not to explain"*, S5 took the rule to its end —
  the branch needed a button, not a sentence, and `common.retry` exists in four languages
  (R2-95).
- Tests: one in `riskStore.test.ts` (the query asked before the identity), two in
  `riskPanelController.test.ts` (re-asks a discarded question; tells a discard from an empty
  answer).

The fix does not depend on the trigger: any discard, identity or cache generation, now
re-asks and then declares itself.

## Prevention

- **A guard that protects by discarding must be able to say it discarded**, or the
  protection is indistinguishable from an absence of data (R2-66).
- One value, one meaning: a `null` that can mean "not asked" and "discarded" needs the
  information that separates them carried next to it (R2-93).
- A test that always establishes the precondition first proves the guard, not the order in
  which the app meets it (R2-66). *Added on verification*: the converse also holds — before
  blaming an ordering, show that the app performs it. Here the unsafe order was inferred from
  the layout and never observed, and the layout does not perform it.

## Impact

A healthy 16/16 correlation matrix rendered as «No results» on round 2's visual gate, in the
new section and in the legacy one. No wrong number reached the screen — a wrong absence did.

## Source files

| Role | Path |
|------|------|
| `queryRisk` returns `null` on discard; `invalidateRisk` registered as session reset and portfolio-mutation listener | `frontend/src/lib/stores/risk/riskStore.svelte.ts` |
| `loadBase` — discard vs empty, re-ask once, `loadDiscarded`; `catalogState` precedent | `frontend/src/lib/stores/risk/riskPanelController.svelte.ts` |
| Fifth branch `risk-correlation-discarded` + `risk-correlation-retry` | `frontend/src/lib/components/risk/AssetSetCorrelationSection.svelte` |
| Generation bump on the first identity resolution, resetters skipped | `frontend/src/lib/stores/app/clientSession.ts` |
| `checkAuth` / `login` — transition before `user` is set; `isAuthenticated` | `frontend/src/lib/stores/app/auth.ts` |
| Markup guard `{:else if $isAuthenticated}` around `<slot />` | `frontend/src/routes/(app)/+layout.svelte` |
| Live-price `$effect` on the Assets page | `frontend/src/routes/(app)/assets/+page.svelte` |
| `POST /api/v1/assets/prices/current` from the client | `frontend/src/lib/services/livePriceService.ts` |
| Response interceptor → `notifyPortfolioMutation` | `frontend/src/lib/api/zodios-client.ts` |
| Which requests count as portfolio mutations | `frontend/src/lib/stores/portfolio/portfolioMutation.ts` |
| Unit tests — stale discard, first-identity order | `frontend/src/lib/stores/risk/riskStore.test.ts` |
| Unit tests — re-ask, discard vs empty | `frontend/src/lib/stores/risk/riskPanelController.test.ts` |
| Diagnosis (reperto R2) and repair (passo 1c) | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/progress/S5-esecuzione.md` |
| The 23/09 reading of the same race (F-2) | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/progress/F-laboratorio-postmerge.md` |
| Registry — R2-62, R2-66, R2-93, R2-95, R2-101 | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/REGISTRO.md` |
