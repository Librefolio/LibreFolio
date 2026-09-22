# PAC Allocator — review dossier

**For:** the developer, before reviewing merge `3913fe217`.
**Author:** session D (`e-alfy-allocatore-pac`).
**Status as of writing:** 2026-09-19 ~01:10. Branch merged into `dev_release2`; my
four commits are `0088748a8`, `75309672e`, `9229085e9`, `c25c1e874`.

> **Read §2 and §6 first.** §2 says which of the merged work is mine, and §6 says
> where the model is narrower than reality. Everything else is detail.

---

## 1. The arc

The brief was one thing: an allocator that, given a budget and target weights,
proposes what to buy. What it became, across four commits, is a **small exact
optimiser with a proof layer** — and the interesting part of the story is the two
places the direction changed.

**Fork 1 — "compute it" became "prove it".** The original framing was a
calculator. Partway through Step 2 the question changed from *what does this
return* to *how do we know it is right*, because the natural implementation —
run a solver, publish its answer — has no way to distinguish "the best plan" from
"the best plan the solver happened to find before it ran out of time". That
produced the central design rule of the whole slice: a floating solver result is
**evidence, never a conclusion**. Everything published is re-derived in exact
rational arithmetic; the solver's own numbers never reach the wire.

**Fork 2 — FX stopped being a routing problem.** The original model had directed
FX routes with per-pair quotes, inversion flags and a per-broker `fx_mode`.
`0088748a8` replaced it with one canonical unordered pair map
(`fx_rates: {"AAA/BBB": rate}`) plus a single scenario-level spread. That removed
a whole class of arbitrage the old model made expressible — cycling cash through
inconsistent rate directions — by making it structurally impossible rather than
checking for it afterwards.

A third thing happened that was not a fork but is worth recording: **six defects
in this slice were invisible to every static gate** (`ruff`, `black`,
`py_compile` all green) and were caught only by running the code. Two were mine
and found by my own smoke tests; two were found by the test-author agent; one was
a wrong conclusion I had reported to the coordinator as fact. They are all
documented in the plan journal with their mechanisms.

---

## 2. Scope reality check — what is mine

The merge landed **three** workstreams. Only one is mine.

| Workstream | Mine? | Owner |
|---|---|---|
| PAC allocator (exact core, solver, proof, projection, plan service) | **yes** | this session |
| Exact-arithmetic transaction inputs | **yes** (`75309672e`) | this session |
| `/portfolio/allocation-source` + FX/funding redesign | **yes** (`0088748a8`) | this session |
| **Onboarding** (~37 files, `onboarding_service.py`, migration `003`, `/welcome`) | **no** | session J, `e-alfy-onboarding-foundation` |
| **Tool platform** (executor, quotas, resource budgets) | **no** | `e-alfy-tool-platform-c-r2` |
| **PAC + Rebalancer tool UI** (`PacAllocatorTool.svelte`, `PortfolioRebalancerTool.svelte`, `RebalanceHoldingEditor`, `RebalancerResultPanel`) | **no** | commit `d66f8e58e`, *"preserve Round 4 prototype"* |

My four commits touch **zero lines** in any of those UI files.

### 2.1 The fact that shapes tonight

**Nothing I built in `9229085e9` and `c25c1e874` is reachable from the running
application.**

```
plan_pac_allocation      → production callers: ZERO (only its own test file)
operation="plan"         → not registered in tool_plugins/, not exposed in api/
tool_plugins/pac_allocator.py:29   → operation="analyze"   (P1 only)
PacAllocatorTool.svelte:368        → operation: 'analyze'  (P1 only)
```

The Tool plugin registers only the **P1 `analyze`** operation. So if you open the
PAC tool and click, you exercise the Round 4 prototype over pre-existing P1
services — not the v2 planner. This is deliberate and was left unauthorised:
wiring `operation="plan"` needs a `ToolOperationPolicy` timeout envelope that has
never been measured at representative scale (see §7, DBT-1).

The substitute is **§8.4's driven harness**, which runs the planner directly and
prints each result state.

### 2.2 The seam with the tool platform

My PAC work **consumes** the tool platform only through the existing P1
registration; the v2 planner consumes nothing from it yet, because it is not
registered. Concretely: I ship *service functions*; the platform owner owns
`ToolService`/`ToolOperationPolicy` wiring. I needed one thing the platform did
not yet provide — a policy envelope sized for a solver rather than an analysis —
and rather than invent one I left the operation unregistered. That is the whole
dependency.

### 2.3 Files I touched that belong to others

Two, both additive and both authorised:

- `scripts/test_runner/_backend_services.py` — test registrations only (+37, +48, +64 across three commits; zero deletions).
- `frontend/scripts/fix-openapi-discriminators.mjs` — +9 lines adding 9 schema names to the existing `discriminatedSchemas` allow-list.

I touched **no** onboarding file and **no** tool-platform file.

---

## 3. Backend

### 3.1 API surface

One new endpoint, `0088748a8`:

- `POST /api/v1/portfolio/allocation-source` — read-only. Returns a domain
  snapshot (assets, brokers, holdings, cash, prices, classifications, FX quotes)
  shaped for pre-filling an allocation request. Broker-scoped authorisation:
  OWNER-only, and it does **not** silently narrow the broker set when the caller
  lacks permission — it refuses.

No existing endpoint was modified. The −6 lines in `portfolio_api.py` are import
reflows and docstring rewrapping.

### 3.2 Services (`backend/app/services/pac_allocator/`)

| Module | Lines | Role |
|---|---|---|
| `numeric.py` | pre-existing | `ExactRatio`, `post_half_up`, fee maths. All exact, no float. |
| `models.py` | +809 | The exact domain: scenario, policy view, decisions, evaluations. |
| `normalize.py` | +345 | Wire request → `ExactPlannerScenario`, with typed issues. |
| `evaluator.py` | +3630 | **The authority.** Replays a candidate in exact arithmetic: ledger postings, constraints, objectives, conflicts. |
| `ledger.py` | +196 | Broker×currency posting and reconciliation, HALF_UP. |
| `oracle.py` | 212 | Exhaustive enumeration. Zero solver dependency. |
| `constraints.py` | 657 | Hard constraints as SCIP rows. |
| `objectives.py` | 246 | The five objective stages. |
| `compiler.py` | 178 | Builds one SCIP model. Never solves. |
| `solver.py` | 418 | Lexicographic search. Never concludes. |
| `proof.py` | 282 | Decides what is proven. Nothing else may. |
| `wire_numbers.py` | 235 | Exact rational → wire number. |
| `planner_report.py` | 886 | Exact evaluation → wire result rows. |
| `planner.py` | 401 | `plan_pac_allocation` — the one service entry. |

**Where the computation runs:** entirely in-process, synchronously, in pure
Python plus SCIP. It reads **nothing** — the planner takes a fully-specified wire
request and touches no database, no network, no clock. All portfolio data reaches
it via `/portfolio/allocation-source`, which the *caller* invokes separately.
That separation is deliberate: the optimiser is a pure function of its input.

### 3.3 Migration

**None of mine.** Migration `003_user_onboarding_progress` belongs to session J.
My work adds no table and no column.

---

## 4. Frontend

My only frontend work is `75309672e`:

- `ExactDecimalInput.svelte` (+313) — decimal input that never round-trips
  through a float.
- `ExactQuantityInput.svelte` (+231, new) — quantity input honouring an asset's
  fractional-quantity rules.
- `TransactionFormModal.svelte` (+172/−…) — rewired onto the exact inputs.
- `txPayloadHelpers.ts` (+145) — payload construction without float coercion.

Reachable at: any transaction create/edit form.

State persisted: none new. These are controlled inputs; the exactness is in how
the value is carried to the payload, not in new storage.

The **tools registry** (`frontend/src/lib/features/tools/registry.ts:241-249`)
maps `pac_allocator` to the Round 4 prototype components. Not mine, and unchanged
by me.

---

## 5. The mathematics

### 5.1 The problem

Given a budget and target weights, choose whole-share purchases so the resulting
portfolio is as close as possible to the target — where "closest" is defined
precisely, and ties are broken deterministically.

This is a **mixed-integer program with a quadratic objective** (MIQCP). It is
integer because you buy whole shares (or whole multiples of an order step), and
quadratic because closeness is measured as a sum of squares.

### 5.2 Variables

One **integer** variable per decision, in units of that decision's *quantum*:

- `buy_quantum:<route>` — how many order-steps to buy on a route.
- `funding_transfer:<route>` — how many currency units to move between brokers.
- `fx_debit:<route>:<currency>` — how many units of a source currency to convert.

Everything is integral by construction. There is no rounding step at the end that
could produce a fractional share: fractionality is impossible to express.

### 5.3 Objective — lexicographic, not weighted

Five stages, optimised **in strict order**. Stage *k+1* is optimised only over
the set of solutions that are optimal for stage *k*:

1. **`fixed_l2`** — Σ over assets of (final_value − target_value)². The primary
   notion of "close to target".
2. **`shortfall`** — `fixed_reference − final_invested`. Prefer deploying more of
   the budget.
3. **`route_priority`** — Σ of the priority of each route actually used.
4. **`explicit_cost`** — fees + FX spread loss + execution-margin loss.
5. **`active_order_rows`** — number of distinct orders. Prefer fewer tickets.

Then a **canonical tie-break**: a fixed, deterministic ordering over decision ids.
Two runs on identical input always produce an identical plan.

There is **no weighted sum anywhere**, and that is deliberate: weights would let a
large gain on cost silently buy a loss on target accuracy, at an exchange rate
nobody chose.

`target_value_a = target_weight_a × fixed_reference`, where
`fixed_reference = current_invested + reachable_funding`. Note **reachable**, not
selected: money that no route can actually spend is reported as `trapped_funding`
and excluded from the denominator, so targets are measured against money that can
really be deployed.

### 5.4 Constraints

- **Funding pool** — the sum of transfers out of one cash pool cannot exceed what
  was selected from it.
- **Ledger balance** — every broker×currency cell ends non-negative. This is the
  no-short/no-leverage rule, and it also encodes "you cannot spend money you
  haven't moved there yet".
- **Order required minimum** — an unconditional per-route floor.
- **Order activation** — semi-continuous: a route buys either exactly zero or at
  least its active floor. This is the "no 0.3-share ticket" rule.
- **Fee epigraph** — a linearisation of `fixed + clamp(rate × notional, floor, cap)`.
- **Box bounds** — each decision's own reachable range, already cash-tightened.

### 5.5 How it is solved, and what happens when it cannot be

Two engines, and **the oracle is tried first**:

- **Exhaustive oracle** (`oracle.py`) — when the discrete domain is small enough
  (≤ 200 000 candidates), it enumerates *every* admissible candidate, replays each
  through the exact evaluator, and picks the lexicographic best. Its answer is
  **proven**: `optimal_proven`, or `infeasibility_proven` if nothing is feasible.
  No solver is run in this case.
- **SCIP** (`solver.py`) — for larger domains. Runs the five stages as a genuine
  lexicographic cascade: solve stage *k*, freeze its optimum as a hard constraint,
  solve stage *k+1* on that face. Guarded by SCIP-native time/node limits.

**What it does when no exact answer exists** — this is the part that matters:

| situation | result | proof |
|---|---|---|
| oracle enumerated, found a best | `ready_incumbent` | `optimal_proven` |
| oracle enumerated, nothing feasible | `ready_infeasible` | `infeasibility_proven` |
| oracle enumerated, best is do-nothing | `ready_no_op` | `optimal_proven` |
| solver found something, budget ran out | `ready_incumbent` | **`not_proven`** |
| solver found nothing in budget | `ready_no_incumbent` | `not_proven` |

A solver result is **never** promoted to "proven". `proof.py` makes that
structurally impossible rather than merely unwritten: the only function that
takes a solver result returns a type whose `kind` is the literal `"not_proven"`,
and the proven types require a witness object that can only be constructed from
an oracle result. A SCIP `infeasible` status does **not** produce
`ready_infeasible` — only the oracle can prove that.

### 5.6 The invariants, and how they are checked

- **Exact replay is mandatory.** Every published number comes from
  `evaluate_exact_candidate`, in `Fraction`-style exact rationals. The solver's
  floating values appear only in a clearly-labelled non-authoritative evidence
  block. A candidate that fails replay is *not* published with a warning — it
  produces `ready_no_incumbent`.
- **Accounting identity:** `shortfall = free_cash + physical_reserves +
  economic_losses + rounding_delta`, with `identity_delta == 0` enforced by the
  wire schema on every result.
- **Ledger reconciliation:** each broker×currency row must balance its posted
  debits and credits exactly.
- **Exposure closure:** each exposure dimension must sum to exactly 1 — achieved
  as an algebraic identity, never by rescaling (see §6.7).
- **Oracle-agreement gate:** a permanent parametrised test asserts that, on every
  toy fixture, the solver's answer equals the oracle's proven optimum *exactly* —
  same quanta and same full lexicographic key. This is the test that caught the
  HALF_UP defect below.

### 5.7 Rounding, and where money could be created or lost

Money is posted to ledgers **rounded HALF_UP to the currency quantum** (cents,
typically) for three flows: `fx_credit`, `buy_debit`, `buy_fee`. Everything else
(`initial_selected`, `funding_in/out`, `fx_debit`) is exact.

This matters more than it sounds. **The single worst defect of the slice was
here**: the SCIP model summed *exact* amounts while the ledger posts *rounded*
ones. An FX credit of exactly €9.504 posts as €10. The model saw 9.504, believed
a genuinely affordable plan was unaffordable, and returned a worse answer. It was
found by the oracle-agreement gate and fixed by modelling the rounding explicitly
with integer quantum-unit variables.

The residue is not hidden. It is published as `rounding_delta`, and is bounded:
`|rounding_delta| ≤ rounding_bound`, checked by the schema. So rounding can move
money by at most a bounded amount, and that amount is on the face of the result.

**FX:** one canonical rate per unordered pair, one scenario-level spread applied
**exactly once** per actual conversion. Mark-to-market always uses the official
mid, never the spread rate. Funding transfers are strictly same-currency.
Conversions are one-hop only — you cannot cycle cash through a chain of pairs,
which is what makes rate-inconsistency arbitrage structurally impossible rather
than merely detected.

---

## 6. Simplifications — where the model is narrower than reality

This is the section to read with suspicion.

### 6.1 Only one policy actually works

`PAC proportional` is implemented. **`min_fragmentation` is not.**
**`invest_only` and `invest_and_sell` are not.** The compiler raises a scope
error rather than silently producing a wrong model — but the wire contract
*declares* those policies, so the vocabulary is wider than the implementation.

### 6.2 Selling does not exist

No SELL path at all. Rebalancing a portfolio that requires selling is out of
scope. The schema has SELL rows, cost basis, tax withholding and a SELL
irreducibility witness; **none of it is implemented**.

### 6.3 Taxes do not exist

Tax fields exist in the domain (`broker_withheld_tax`, `self_reserved_tax`,
`ExactAssetTax`, `ExactWithholding`) and are always zero, because they only apply
to SELL. A PAC plan never computes tax.

### 6.4 Fees: one known approximation

The fee epigraph ignores the fee **cap** in its internal upper-bound estimate.
Consequence: on a route with a binding maximum fee, the solver may *believe* a
plan costs more than it does, and therefore prefer a different plan. It can never
cause false infeasibility (the estimate is pessimistic, never optimistic) and the
fee actually reported is always the exact capped one. **This is a search-quality
limitation, not a reporting error.** It is documented in `compiler.py` and locked
by a regression test.

### 6.5 What is assumed about the user's world

- **Prices are given, not fetched.** The planner receives a price per asset and
  treats it as correct at the stated date. Staleness is carried as metadata; the
  planner does not refuse a stale price.
- **Liquidity is infinite.** If a route's cap allows 100 shares, the model assumes
  100 shares are buyable at the quoted price. No market impact, no partial fills.
- **One price, no spread on the instrument.** Execution margin is modelled as a
  rate, but there is no bid/ask.
- **Dividends do not exist.**
- **Existing holdings** are read for `current_invested` but never sold or
  rebalanced.
- **Minimum lot sizes** are modelled *only* as `order_step` and
  `minimum_if_active`. A broker rule not expressible in those terms is not
  expressible at all.

### 6.6 Boundary behaviour — what actually happens

| situation | behaviour |
|---|---|
| zero budget | `ready_no_op`, `optimal_proven`. Correct and honest. |
| one asset | works; the L2 objective degenerates to a single term. |
| asset with **zero price** | rejected at normalisation (`ExactAssetQuote` requires a positive price). |
| asset with **stale price** | **accepted only if the caller explicitly marks it accepted** (`accepted=True` + `age_days`), otherwise refused with `allocation.stale_observation_not_accepted`. Once accepted, the plan is computed as if fresh. See §6.8.1. |
| target unreachable (budget too small) | `ready_no_op` or a partial plan, with `shortfall` showing the gap. |
| conflicting constraints (min > cap) | `ready_infeasible` with `infeasibility_proven` — *if* the domain is small enough for the oracle. Otherwise `ready_no_incumbent`/`not_proven`. |
| FX pair missing | rejected at normalisation with a typed issue. |
| budget too small for one share | `ready_no_op`. This is the common first-of-month case, and it crashed until a few hours ago (§7). |

### 6.7 Exposure tables: the uncategorised residue

If assets carry no exposure declaration for a dimension, the schema still
requires that dimension's weights to sum to exactly 1. Rather than omit the
dimension or emit an empty table — both of which read as *"this portfolio has no
sector exposure"* rather than *"we could not compute it"* — the uncovered
fraction is published as its own explicit category,
`allocation.uncategorised`. So a portfolio half of which has no sector data shows
`Tech 50%, Uncategorised 50%`, not `Tech 100%`.

**A UI that renders these as a pie chart must render the uncategorised slice.**
Normalising it away would recreate exactly the deception this design removes.

### 6.8 ⚠️ Where a plausible-but-wrong answer is possible

Per the brief, the most important lines in this document.

1. **Stale prices: explicitly accepted on input, but faded on output.** This is
   subtler than "silently accepted", and I initially wrote it down wrong — the
   input contract is better than I first claimed. A stale price cannot just slip
   through: `ExactFreshness` requires `kind="stale"` to carry a non-negative
   `age_days` **and** `accepted=True`, and normalisation raises
   `allocation.stale_observation_not_accepted` otherwise. So the *caller* must
   consciously accept the staleness.
   The residual risk is on the **output** side. The published result carries
   provenance `captured_at`, and `allocation.provenance_stale_confirmed` exists
   as an issue code — but `age_days` does **not** appear in the result schema,
   and the plan itself is computed as if the price were current. So a
   three-week-old price yields a fully-formed, exact, `optimal_proven` plan whose
   proof is genuinely valid *with respect to the price supplied*. The number that
   would most quickly tell a human "this is old" — the age — is not on the face
   of the result. **This remains the most likely route to an answer that is
   correct and still misleading**, but the mechanism is "the caller accepted
   staleness and the UI must re-surface it", not "the backend ignored it".
2. **`stop_reason` can say `time_limit` when nothing timed out.** On the
   solver path with an infeasible model, the result honestly degrades to
   `not_proven`, but the wire enum offers only `completed | time_limit |
   node_limit`, and `completed` is forbidden when any stage is unfinished. So it
   reports `time_limit`. **A UI must not tell the user "the solver ran out of
   time" on this path** — that would turn a contract gap into a lie. Registered
   as DBT-5.
3. **`optimal_proven` means "optimal for this scenario as specified"** — not
   "the best thing you could do with your money". If the request omits a broker,
   a cash pool or an asset, the proof is still valid and still narrow.
4. **The fee cap approximation (§6.4)** can make the solver prefer plan B over
   plan A when A is genuinely cheaper. The reported cost is correct; the *choice*
   may be mildly suboptimal on capped-fee routes.

---

## 7. What is not done

| # | Item | Note |
|---|---|---|
| DBT-1 | `operation="plan"` not registered | Needs a measured timeout envelope; deliberately unauthorised. **This is why the feature has no UI.** |
| DBT-2 | Solver timeout envelope unmeasured at representative scale | Toy fixtures run in 3–8 ms. Extrapolating from that would be a guess. Needs the G5 campaign. |
| DBT-3 | `min_fragmentation`, `invest_only`, `invest_and_sell` | Not implemented. Scope guard refuses them. |
| DBT-4 | `score_lattice_closure` proof source | Not implemented; the oracle is the only proof route. |
| DBT-5 | `stop_reason="time_limit"` on infeasible solver path | Contract gap, no truthful enum value exists. See §6.8.2. |
| DBT-6 | `gap_bounded` proof never emitted | Would need a sound dual bound; deriving one from SCIP's floating dual is exactly the promotion `proof.py` forbids. |
| DBT-7 | `deterministic_conflict` proof source never emitted | The witness wants wire `PlannerIssueCode`s; the evaluator produces exact-domain constraint codes. Two vocabularies, no honest bridge. |
| — | Tool-platform fixture staleness in `PacAllocatorTool.test.ts` / `PortfolioRebalancerTool.test.ts` | Pre-existing, unmasked by my discriminator fix. **Not mine**; routed separately. |

---

## 8. Test scenarios for a human

**Server:** `http://127.0.0.1:6152`
**Login:** `e2e_test_user` / `E2eTestPass123!`
**Data:** `/tmp/librefolio-r2-d-review` (5610 records, freshly populated)

Each scenario says **whose code it exercises**, because a conclusion attached to
the wrong object is worse than no conclusion.

### 8.1 Regression first — does the app still work? *(exercises MY changed shared code)*

These matter most: unreachable new code cannot hurt you, changed shared code can.

| # | Do this | Correct result |
|---|---|---|
| R1 | Open the portfolio dashboard. | Loads. Totals, allocation and history identical to before the merge. |
| R2 | Open an asset detail page with transactions. | WAC/cost-basis values unchanged. **Specifically check this** — I added a `use_cache` parameter to `compute_wac_iterative`. It defaults to `True`, so all existing callers behave exactly as before; only the new allocation-source path opts out. If WAC numbers moved, that defaulting is wrong and it is mine. |
| R3 | Open the P&L / performance views. | Unchanged. |
| R4 | Anything reading `schemas/portfolio.py`. | Unchanged. The +421 lines there are **new `PortfolioPlannerSource*` classes only** — no existing model was modified. |

### 8.2 Exact-arithmetic transaction inputs *(mine, `75309672e`, genuinely clickable)*

The best review target of the night: cheap to test, obvious when wrong, and you
can check it against a calculator.

| # | Do this | Correct result |
|---|---|---|
| T1 | New transaction → quantity `0.1`, price `0.2`. | Total exactly `0.02`. Not `0.020000000000000004`. |
| T2 | Quantity `1/3`-ish: enter `0.3333333333333333`. | Preserved to the precision you typed; no silent truncation to 2 dp. |
| T3 | Enter a very long decimal, e.g. `123.456789012345678`. | Either preserved or refused. **Not silently rounded.** |
| T4 | Paste a value with a comma decimal separator. | Handled per locale or rejected — not misparsed by a factor of 1000. |
| T5 | Quantity on a whole-share asset: type `2.5`. | Rejected or stepped per the asset's rules. |
| T6 | Edit an existing transaction, save without changing anything. | Values identical after reload. No drift. |

**T3 and T6 are the ones I am least confident about** — long-decimal boundary
behaviour and edit-round-trip stability have unit coverage but little real-UI
mileage.

### 8.3 Allocation-source prefill *(mine, `0088748a8`)*

| # | Do this | Correct result |
|---|---|---|
| A1 | `POST /api/v1/portfolio/allocation-source` (see `/api/v1/docs`). | Returns a snapshot of your own brokers only. |
| A2 | Request a broker you do not own. | **Refused.** Not silently narrowed to the permitted subset. |
| A3 | Inspect `fx_rate_prefill` rows. | One row per needed pair, alphabetical `AAA/BBB`. No inverse rows, no identity rows. |
| A4 | An asset with no saved price. | Reported as missing, **not omitted**. An absent asset would be a silent lie. |

### 8.4 The planner itself *(mine — code review + driven harness only)*

There is **no UI**. Run:

```bash
PYTHONPATH=. PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python \
  LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/review/drive_planner.py
```

It prints four result states with full accounting, orders, objective cascade and
exposure. What to check:

- **`identity_delta` is `0.00` in every state.** If it is not, money was created
  or destroyed.
- **State 1** (€5 cash, €10 share): `ready_no_op` + `optimal_proven`, `fixed_l2 = 25`
  — i.e. (0 − 5)². Doing nothing is genuinely optimal; verify that by hand.
- **State 2** (€50 cash): buys 5 shares for exactly €50, `fixed_l2 = 0`,
  `shortfall = 0`. A perfect fit — check the arithmetic.
- **State 3** (min 1 share, €5 cash): `ready_infeasible` + `infeasibility_proven`,
  and **no solution is published**. Nothing is claimed.
- **Every exposure dimension sums to exactly 1.**
- Note `solver: not_run` in all four — the oracle settled them, so SCIP never ran.

### 8.5 What you will *not* be testing

Opening the **PAC tool or Portfolio Rebalancer in the UI** exercises the Round 4
prototype over **P1 analyze** — not my v2 planner, and not my code. Judge that UI
on its own terms; it belongs to `d66f8e58e`.

---

## 9. Automated coverage

**907 tests** across the PAC suites and the planner schema suite. What they
actually assert:

| suite | tests | asserts |
|---|---|---|
| `pac-planner-core` | 135 | exact primitives, normalisation, issue precedence |
| `pac-planner-evaluator` | 140 | exact replay, ledger, constraints, conflicts |
| `pac-planner-oracle` | 20 | exhaustive enumeration, domain cap, lexicographic selection |
| `pac-planner-policies` | 34 | every hard-constraint boundary, objective values vs evaluator |
| `pac-planner-solver` | 12 | **oracle-agreement gate** + cascade structure + limit honesty |
| `pac-planner-proof` | 33 | unrepresentability of an unproven claim; 14 forgery paths |
| `pac-planner-wire-numbers` | 39 | lossless projection, canonical spelling, fail-closed limits |
| `pac-planner-report` | 16 | row projections, exposure closure, containment |
| `pac-planner-service` | 30 | all result states end-to-end from a wire request |
| `test_pac_planner_schemas` | 448 | the frozen wire contract |

### 9.1 What is **not** covered

- **No end-to-end HTTP test of the planner**, because there is no route.
- **`stop_reason` limit branches** are tested on a *doctored* solver stage, not a
  genuinely limit-terminated solve. Deterministically forcing SCIP to a limit on
  a toy scenario is not feasible; filed against G5.
- **Per-section sequence ordering** is proven non-vacuously only on the BUY
  section; the toy fixtures have single-row funding/FX sections.
- **No performance or scale testing whatsoever.** Everything runs on single-digit
  asset/broker fixtures. The 3–8 ms timings are meaningless for real portfolios.
- **The display-projection coarse-scale path** is covered only via its raise.
- **No frontend test of the planner UI**, because there is no planner UI.

### 9.2 One thing worth knowing about the tests

The oracle-agreement gate was **mutation-tested**: the HALF_UP fix was
deliberately reverted to confirm the gate goes red, then restored byte-identical.
A regression test that cannot fail is decoration. The same was done for the proof
layer's unrepresentability guarantees (3 mutations, all detected) and for the
exposure closure and provenance containment properties.

---

*Prepared by session D. Every claim above was checked against the repository at
`c25c1e874` rather than recalled; where I could not verify something I have said
so.*
