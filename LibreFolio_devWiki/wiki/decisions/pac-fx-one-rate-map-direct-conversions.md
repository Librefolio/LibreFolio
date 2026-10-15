---
title: "PAC allocator: one map of exchange rates and one spread per scenario; every conversion is direct, and a broker's conversion mode changes only how the plan is presented"
category: decision
status: resolved
date: 2026-09-17
updated: 2026-10-09
tags: [backend, frontend, pac-allocator, fx, currency, spread, conversion, release-1.2, workstream-d]
related:
  - features/F-107
  - decisions/pac-rounding-against-the-plan
  - problems/pac-foreign-funding-calculation-failed
  - problems/pac-tool-error-instead-of-plan
  - sources/phase00-pac-implementation-2026-10
---

# Decision: a single rate map, direct conversions

## Context

The first planner contract modelled FX as routes: a valuation rate, quotes per pair, directed conversion routes, and
a `currency`/`fx_mode` capability per broker (`PlannerValuationRateInput`, `PlannerFxQuoteInput`,
`PlannerFxRouteInput`). Each broker could convert differently, and a conversion could chain through a third
currency.

## Decision

**The developer's redesign of 2026-09-17** (Step 1, «redesign FX/funding/conversion», implemented in `0088748a8` on
2026-09-18) replaced the route model with one canonical map, through a sequence of product decisions:

- **One unordered map** `fx_rates`, keyed `"AAA/BBB"`, and **one spread** for the whole scenario, `fx_spread_rate`
  (default `0`): «Single global adverse spread applied exactly once to every actual currency conversion; valuation
  always uses the official» rate (schema).
- **Every conversion is direct** — one hop, no cascade. Buying may draw on several sources; selling never converts.
- **The extras were dropped** on 2026-10-02: a spread per broker, a safety margin, a conversion fee, multi-hop
  chains — «❌ non più da fare (developer, 02/10/2026)». The UI target says it in one line: «Lo spread è uno solo, per
  scenario, e ogni conversione è diretta.» The spread's help text is the developer's own: «un sovrapprezzo di margine
  per coprire eventuali variazioni del tasso ufficiale o commissioni del broker».
- **A broker's conversion mode is presentation**, reopened in the review rounds (R4.9, 2026-09-30 → R11.12):
  `manual` shows numbered conversions the user performs before buying, `automatic` lets the broker convert when the
  orders execute — «It changes no figure of the plan» (schema). The engine decides FX per order route, but the credit
  lands in a cash pool every order of that broker and currency shares, so the plan shows one `PlannerConversion` per
  broker and currency pair.

## Rates must agree

A map of pairwise rates does not rule out a triangle that creates money: real data mixes the latest rates of
different dates and sources, and the spread defaults to zero. Since the FX fix of 2026-10-09 (`bffc634b0`) the
normalizer refuses a buy conversion whose path through the valuation currency beats the direct rate
(`validate_fx_coherence`, `allocation.fx_rate_inconsistent`), and since the rounding fix the same day a band of
ten-decimal storage error is tolerated and the conversion is planned at the triangle (B1) —
[[problems/pac-foreign-funding-calculation-failed]], [[decisions/pac-rounding-against-the-plan]].

## Options Considered

| Option | Outcome |
|--------|---------|
| Directed routes with quotes and an FX mode per broker | Replaced on 2026-09-17 by the developer |
| Multi-hop conversions through a third currency | Dropped (developer, 2026-10-02) |
| A spread per broker, a safety margin, a conversion fee | Dropped (developer, 2026-10-02) |
| One map, one spread, direct conversions | **Chosen** |

## Consequences

- Option (e) stays in the backlog: one conversion per broker and pair. Rounding against the plan makes splitting a
  conversion unprofitable, but the solver can still leave more than one.
- A manual conversion that reached an exact half-unit credit tie used to stop the calculation, until a guard was
  removed (R13.6) — [[problems/pac-tool-error-instead-of-plan]].
- `fx_cost` on an order row is always zero: its per-route roll-up was never implemented (Round 5 left the debt to the
  coordinator). The spread lost by each conversion is in `PlannerConversion.spread_loss`.

## Source files

| Role | Path |
|------|------|
| Rate map, spread, conversion mode, `PlannerConversion` | `backend/app/schemas/pac_allocator/request.py`, `backend/app/schemas/pac_allocator/rows.py` |
| Coherence check | `backend/app/services/pac_allocator/normalize.py` |
| Planning rate at the triangle | `backend/app/services/pac_allocator/numeric.py` |
| FX step of the planner | `frontend/src/lib/features/tools/pac-allocator/planner/steps/FxStep.svelte` |
| Pair added in place | `frontend/src/lib/features/tools/pac-allocator/planner/fxSetup.ts` |
| Normalizer tests | `backend/test_scripts/test_services/test_pac_planner_normalize.py` |
| Step 1 plan (the 2026-09-17 redesign) | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00Step1PacRebalancerContractsCapacity.prompt.md` |
| UI target (the 2026-10-02 strike-outs) | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00PacRebalancerUiTarget.prompt.md` |
