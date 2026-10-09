---
title: "PAC allocator: every booked amount rounds against the plan — no conversion may create value"
category: decision
status: resolved
date: 2026-10-09
tags: [backend, pac-allocator, tools, rounding, fx, scip, optimization, exact-arithmetic, invariant]
related: [decisions/financial-math-single-average-cost, decisions/wac-target-currency-last-acquisition, concepts/backend-only-calculations, problems/fx-backward-fill-unbounded-stale-rates, concepts/premise-gate-keyed-by-content]
---

# Decision: the PAC allocator rounds every posting against the plan

> The PAC allocator (Release 2 workstream D, a Tool in `backend/app/services/pac_allocator/`) plans which assets to
> buy with the available cash, across brokers and currencies, with SCIP as the search engine and a Decimal-exact
> replay (`evaluate_exact_candidate`) as the only referee of feasibility and of every reported number. This page
> records the rounding contract fixed on 2026-10-09 (plan *PacRoundingDirectionFix*, merged in `b81b92fd1`, train 26;
> the plan folder `Phase_0/13_pacAllocator/` is still active). Checked against the code at `083ed26dc`.

## Context — the optimizer was mining the rounding

With the gallery's external account back in USD, the plan computed but contained steps of a few cents: 0.01 USD
transferred and converted into "0.01 EUR" (0.00893 exact); a EUR→USD conversion split in two so that the posted
credits summed to 1,233.42 against an exact 1,233.4109; a round trip EUR→USD→EUR on the same broker; and a "Not
invested" card showing **Rounding ≈ −0.02 EUR** — value created by rounding. The causes:

1. every posting was HALF_UP (`ledger._validate_posting` demanded it, postings were built with `post_half_up`), so a
   credit could gain up to q/2 per posting;
2. the SCIP model encoded the same HALF_UP rows, so the solver *saw* the gain;
3. with spread 0 (and still with a 0.1 % spread) splitting a conversion was free, and paid;
4. the validator's `ROUNDING_BOUND` was Σ q/2, checked symmetrically: it accepted the gain.

## Decision

### Rule (a) — one table, one direction per posting family

| Families | Side | Rounding |
|---|---|---|
| `fx_credit`, `gross_sell_credit` | credit | **floor** |
| `buy_debit`, `buy_fee`, `sell_fee`, `broker_withheld_tax`, `self_reserved_tax` | debit | **ceiling** |
| `initial_selected`, `funding_in`, `funding_out`, `fx_debit` | — | exact flows, never rounded |

The table is `_PLAN_ROUNDING` in `ledger.py` (~`:50`). Every real movement (transfer, conversion, buy, fee) rounds
**once**, on its exact final amount, to the currency's minor unit, against the plan — what the broker executes;
intermediate values stay exact and are rounded only for display ("≈", `wire_numbers.py`). Each posting's adjustment
then lies in **[0, q)**: rounding never creates value. And because **Σ floor ≤ floor Σ** (Σ ceil ≥ ceil Σ),
**splitting a movement never pays** — the solver has no reason to split, although separately booked movements still
cannot be merged (one conversion per broker and pair, option (e), stays in the backlog).

### The same direction inside SCIP

`_posted_units_term` (`constraints.py`) receives the side: a credit is `q·u ≤ exact ≤ q·u + q`, a debit
`q·u − q ≤ exact ≤ q·u`, with `u` integer. Posted amounts enter no objective (`explicit_cost` uses the exact fee and
spread), so the model's feasible set is the exact one up to SCIP's tolerance. SCIP models only `fx_credit`,
`buy_debit` and `buy_fee` (`_MODELLED_ROUNDED_FAMILIES`); a scenario that would post another rounded family fails
closed before the model (`LedgerPostingScopeError`).

### The band — one minor unit per rounded posting

`rounding_bound` (`evaluator.py`) is **Σ val(qᵢ)** over the postings that carry a quantum — one minor unit each, valued
in the scenario currency (it was Σ q/2). Under rule (a) the aggregate adjustment lies in [0, Σq), so the band accepts
every normal rounding however many movements a plan has. The **strict** rule stays per posting:
`ledger._validate_posting` recomputes the floor or ceiling exactly and rejects any other posted amount. Beyond the
band there is only a defect, and the exact replay rejects it. A pool left a few minor units short is still published
with a top-up ("this broker/currency needs D more", at most N minor units for N rounded postings): top-ups stay as a
safety net.

### C-FXPOS — an active conversion must post a non-zero credit

Floors admit `u = 0` for any credit below one quantum, which would let the solver "convert" 0.01 USD into nothing.
`FX_CREDIT_POSITIVE` is now a live row of the model (`decision ≤ upper · units`, `active_decision` of
`_posted_units_term`) mirroring the evaluator's fact (`satisfied = action is None or posted_credit > 0`). **Residual
risk:** SCIP's tolerance can give `u = 1` where the exact replay posts 0; the replay then raises
`ExactReplayRejectedError` and the Tool reports **`execution_failed`** — never a wrong plan ("publishing an
unverified plan is the one outcome this package exists to prevent", `planner.py`).

### B1 (point 15) — a band for stored rates, and the triangle inside it

Rates are stored with ten decimals (`FxRate.rate`, `Numeric(24, 10)`), so three coherent rates can miss their
triangle by storage error. `normalize.validate_fx_coherence` refuses a BUY conversion c→q whose value through the
valuation currency V beats the direct rate beyond that error:
`rate(c→q)·(1−s)·rate(q→V) > rate(c→V)·(1+β)`, with **β = h·(1/R₁ + 1/R₂ + 1/R₃)** over the three stored values and
**h = 5·10⁻¹¹** (half a unit of the tenth decimal) → issue **`allocation.fx_rate_inconsistent`**. Inside the band
the cross rate is accepted and the conversion is **planned at the triangle**:
`calculate_planning_fx_rate()` (`numeric.py`) returns **min(spot·(1−s), val(origin)/val(destination))**, so even an
accepted cross rate creates no value; the published spot stays the user's, and `spread_loss` is 0 at the triangle.
The developer chose B1 ("band + the worse rate inside the band") over B2 (`spread_loss ≥ −band`, which kept the
incentive and the gains).

### Rejected options

| Option | Why not |
|---|---|
| (b) a minimum cost per step | a hidden coefficient |
| (c) a dust threshold | 8.7 % of the splits still gained; R4 (a debit of 10.004 posted 10.00) remained |
| (d) no reverse conversions on the same broker | cured only the round trip |
| (e) one conversion per broker and pair | kept in the backlog |
| (f) HALF_UP plus "shortfall ≥ 0" | pools cover each other |
| (a′) pessimism only in the solver | the proof and the exact replay would diverge |
| a user-selectable rule | refused |

## Consequences

- The gallery's dust steps disappear: a credit of 0.00893 floors to 0.00 and, with C-FXPOS, no conversion happens;
  a conversion is split only where it no longer gains (expected-value table in the plan, §2.9).
- No contract change (1.0.0), no new i18n key, no frontend change beyond a comment; `post_half_up` and the display
  formatter stay for display only.
- The user doc states the rule: amounts the plan receives round down, amounts it pays round up, and the rounding part
  of "Not invested" is never negative.

## Lesson — where the principle lives

The coordinator summarised the rule as "no conversion may create value", citing the *TargetDesign* plan §4.4. That
section is the lexicographic syntax of the objectives; the principle lives in the *MathematicalCore* plan, §7.3
("no rate inconsistency able to create synthetic arbitrage"), and the phrase itself appears in no plan. No test
states the whole principle as one assertion either: the suite pins its two halves separately — rounding against the
plan (`test_rounding_direction_*`, `test_rounding_tie_*`, the oracle's floor/ceiling re-derivation with `Fraction`)
and the rate triangle (`test_cross_rate_within_the_ten_decimal_band_of_the_triangle_is_coherent`,
`test_planning_fx_rate_caps_the_approved_rate_at_the_valuation_triangle`); since the fix, the docstrings of
`test_pac_planner_planner.py` and of the oracle test describe the rounding half ("rounding never creates value").
**When an invariant matters, cite the section that states it and give it a test named after it** — a principle
quoted from the wrong section is one nobody can check.

## Source files

| Role | Path |
|------|------|
| Posting families, `_PLAN_ROUNDING`, `_validate_posting` | `backend/app/services/pac_allocator/ledger.py` |
| SCIP rows (`_posted_units_term`, `FX_CREDIT_POSITIVE`, modelled families) | `backend/app/services/pac_allocator/constraints.py` |
| Exact replay, `rounding_bound`, top-ups | `backend/app/services/pac_allocator/evaluator.py` |
| Rate band β, `allocation.fx_rate_inconsistent` | `backend/app/services/pac_allocator/normalize.py` |
| `post_floor`, `post_ceiling`, `calculate_planning_fx_rate` | `backend/app/services/pac_allocator/numeric.py` |
| `ExactReplayRejectedError` → `execution_failed` | `backend/app/services/pac_allocator/planner.py` |
| Issue definitions | `backend/app/services/pac_allocator/issues.py` |
| `FxRate.rate` (`Numeric(24, 10)`) | `backend/app/db/models.py` |
| Planner tests (rounding direction and ties) | `backend/test_scripts/test_services/test_pac_planner_planner.py` |
| Oracle test (floor/ceiling re-derived) | `backend/test_scripts/test_services/test_pac_planner_oracle.py` |
| Rate band tests | `backend/test_scripts/test_services/test_pac_planner_normalize.py` |
| Planning-rate and posting tests | `backend/test_scripts/test_services/test_pac_planner_exact.py` |
| User doc (rounding, "Not invested") | `mkdocs_src/docs/user/tools/pac-allocator/index.en.md` |
| Plan (§0–§2, decisions and rejected options) | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacRoundingDirectionFix.prompt.md` |
| MathCore plan (§7.3) | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00PacRebalancerMathematicalCore.prompt.md` |
