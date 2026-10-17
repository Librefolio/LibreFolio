---
title: "Deduplicating FX errors went quadratic under a full-history load: minutes of CPU, a 30-second timeout, a stale-signals banner that a retry cleared (E1 follow-up)"
category: problem
status: resolved
date: 2026-09-02
tags: [backend, prices, fx, signals, drawdown, performance, event-loop, beta-testing, release-1.1]
related:
  - decisions/drawdown-full-history-warmup
  - sources/beta-testing-2026-08-05
---

# Problem: one membership test per failed point

## Symptom

On 02/09/2026, the first live run of the drawdown signal with its new full-history load (E1, see
[[decisions/drawdown-full-history-warmup]]) showed the banner saying the signals were not up to date. A retry cleared
it, which made it look like a transient.

## Root Cause

Not the drawdown itself. In `get_prices_bulk`, the loop over price points that failed FX conversion ran
`err not in result.errors` for every failed point against every error already collected: a list lookup inside a
loop, quadratic in the number of failures. Each error embeds the failing date, so an asset whose currency had no FX
coverage over a long history produced tens of thousands of **distinct** errors. A full-history load is exactly what
makes that history long: the worker spun at 100 % CPU for minutes, the frontend's 30-second request timeout fired,
and the banner appeared. The retry worked because the cache was warm by then.

## Solution

`59087c74a` (03/09/2026; its subject says «docs(journal)», but the commit carries this code):

- the conversion errors are deduplicated **once per job**, against a set;
- the list is **capped at ten**, followed by one summary line («… and N more FX conversion failures»); the frontend
  only ever shows the first error, and the uncapped list would have been a multi-megabyte payload nobody reads.

The plan records the in-process reproduction, before and after: from never finishing to 2.6 seconds on an asset with
46 000 prices. The fix shipped in 1.1.0.

## Prevention

- A list lookup inside a loop is quadratic; anything that can grow with history length must dedup through a set.
- An error message that embeds a date is unique per day: count those, never collect them all.
- The events path of the same function still dedups its conversion errors against the list, but there it is bounded
  by the number of events, not by the number of price days.

## Source files

| Role | Path |
|------|------|
| Dedup and cap | `backend/app/services/assets/price_query.py` (`get_prices_bulk`) |
| Plan (E1 detour) | `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/plan-phase00EngineAccountingAndSignals.prompt.md` |
