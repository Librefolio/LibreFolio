---
title: "A broker without icon fields was re-fetched 40–60 times a second"
category: problem
status: resolved
date: 2026-09-25
first_seen: 2026-06-30
resolved: 2026-09-25
tags: [frontend, svelte5, stores, reactivity, performance, brokers, entity-store]
related: [concepts/entity-store-pattern, problems/svelte5-teardown-reads-stale-state-timers, sources/phase00-taxonomy-select-2026-10]
---

# Problem: a reactive loop between a store's version and an effect that fetches

## Symptom

With the Transactions page open, the browser sent 40–60 `GET /api/v1/brokers/{id}` per second for one broker —
close to 100 000 a day — whenever that broker had no icon, no portal and no default import plugin. Present in
v1.1.0 (origin `460f2a18a`, 2026-06-30). Measured on a copy of real data: 0 requests in 10 s with the plugin set,
587 in 10 s once it was cleared (one request per round trip).

## The chain (workstream K, step 10, issue C3)

1. `BrokerBadge`'s `resolvedBroker` is a `$derived.by` that reads `$brokerStoreVersion` and returns a **new object**
   on every bump.
2. `BrokerIcon` reads its props from that object. In Svelte 5 props are getters, so its `$effect` re-runs on every
   bump even when every value is still `null`.
3. The effect calls `ensureBrokerIconFieldsLoaded(id)`; `hasBrokerIconFields` stays false after the answer, because
   a broker with none of those fields legitimately has none.
4. `entityStore.merge` sets `changed = true` for **any** existing entry, identical data included, and bumps the
   version.
5. The loader's `finally` released the in-flight promise in the same tick as the bump, so the next effect found the
   road clear. Back to 1.

## Fix (`7000f8d02`)

`brokerStore.ts` keeps `settledIconFieldIds`: the first answer — success **or** error — settles the id for the
cache generation, because "no icon fields" is a valid state, not missing data. The id is added **before** the merge
(the merge's bump re-runs every icon effect, which must already find the broker answered). The session reset and
`refreshAllBrokers` empty the set; `invalidateBroker` releases its ids; an answer that lands after a client-session
change neither merges nor settles. A unit test pins "at most one request per broker per cache generation". In the measured session, API requests from login to the end of the window went from 604 to 18.

## What stays open

- **K-11**: `entityStore.merge` still bumps the version on identical data. The fix closed the loop at the loader;
  any other effect that both reads the version and merges can rebuild it. A merge that bumps only on a real change
  is the structural cure (see [[concepts/entity-store-pattern]]).
- **Lesson**: in Svelte 5, an effect that reads props derived from a versioned store re-runs on every bump; an
  effect that also *writes* to that store needs a "settled" memory that does not depend on the data it fetches.

## Source files

| Role | Path |
|------|------|
| The settled set and the loader | `frontend/src/lib/stores/reference/brokerStore.ts` |
| `merge` that bumps on identical data | `frontend/src/lib/stores/core/entityStore.ts` |
| Badge (derived object per bump) | `frontend/src/lib/components/ui/display/BrokerBadge.svelte` |
| Contract test | `frontend/src/lib/stores/reference/brokerStoreIconHydration.test.ts` |
| Icon effect | `frontend/src/lib/components/brokers/BrokerIcon.svelte` |
| Plan (step 10) | `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep10BrokerRequestBurst.prompt.md` |
