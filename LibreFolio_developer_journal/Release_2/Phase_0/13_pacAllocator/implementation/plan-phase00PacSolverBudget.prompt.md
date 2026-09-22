# Plan — Propagate the real engine budget to the solver

> **Predecessor**: `plan-phase00PacP1ResidueRemoval.prompt.md` (`154182295`).
> **Baseline**: `154182295`. **Lane**: port 6152, `/tmp/librefolio-r2-d`.
> **Scope**: voice 1 of the remaining-work list, *narrowed by measurement*.

---

## 1. The assignment's premise was wrong, and so was mine

This work was opened as *"solver determinism: no seed, no thread policy"*. Probed against
the installed engine rather than read from documentation:

```
randomization/randomseedshift   0        already deterministic
randomization/permutationseed   0        already deterministic
randomization/lpseed            0        already deterministic
timing/clocktype                2        WALL CLOCK
limits/dettime                  ABSENT   SCIP 10.0 has no deterministic time limit
```

**Adding a seed fixes nothing: the seeds are already zero.** SCIP's search is
deterministic. What is not reproducible is **how much of the lexicographic cascade
completes**, because `solver.py:349` gives each stage a wall-clock slice:

```python
remaining = time_budget_seconds - (time.monotonic() - started)
model.setParam("limits/time", remaining)
```

> The cascade is what makes the answer unique. **Truncating it at a different point gives
> a different answer** — and where it truncates depends on how fast the machine was.

### Demonstrated, not deduced

6 runs per row, identical input, identical budget:

```
scenario            budget    finished stages   distinct candidates
two_asset_pac       0.004s    {0,2,3,4} / 7     2     <-- DIFFERENT
coarse_funding_fx   0.0025s   {3,4,5,7,8} / 8   2     <-- DIFFERENT
```

Control from the other side, full budget, 5 runs: **1** distinct candidate, 1 distinct node
vector, wall time varying 0.0073..0.0602s (8x) with an identical answer. The candidate
`(3,3)` matches the oracle's proven optimum.

## 2. What is actually wrong: the budget never arrives

```
pac_allocator.py:16    "only one number is a product decision — engine_timeout_ms"
pac_allocator.py:70    engine_timeout_ms = 30_000
planner.py:201         solve_policy_program(program, checkpoint=checkpoint)   <- no budget
solver.py:78           DEFAULT_SOLVER_TIME_BUDGET_SECONDS = 3.5
```

**The module docstring states the rule and the module breaks it fifty lines later.**
Measured effective value from the catalog, not assumed: `engine_timeout_ms = 30000`, not
clamped by `min(policy, platform, soft)`. The solver runs on **8.6x less** than the product
declares.

`solver.py:73-78` explains where 3.5 came from: a probe on 2026-09-16, inside a **4 s**
envelope. The envelope later became 30 000 for planner v2 and the default stayed tuned to
the previous world.

> A default outlives the reason it was chosen, and **the comment explaining it makes it
> harder to re-open** — whoever re-reads finds a measured justification and mistakes it for
> a still-valid decision. The comment here is *exact and obsolete at once*, which is the
> worst combination.

## 3. The platform already has the API for this, unused

```
ToolExecutionContext.engine_timeout_ms          base.py:44   (default 4_000)
ToolExecutionContext.claim_engine_window(...)   base.py:55
ToolEngineWindow(deadline, timeout_ms, …)       base.py:30

production consumers of claim_engine_window:    0
test consumers:                                 2
```

Designed for exactly this, tested, never called by a plugin. **Sixth precedent** for the
declared-but-unconsumed gate — and the first where the unused thing is a *capability*
rather than a field.

## 4. Steps

### Step 1 — propagate the budget

`pac_allocator.py` `compute()` claims an engine window and passes its budget;
`plan_pac_allocation` forwards it to `solve_policy_program`. Decide and record the
`post_engine_reserve_ms` — the planner still has to replay the candidate through the exact
evaluator and build the report after the solver returns.

### Step 2 — the comment at `solver.py:73-78`

Either retune the default or say which envelope it is tuned to **today**. A comment
documenting a superseded probe is worse than no comment.

### Step 3 — report the determinism condition

*"Deterministic if the cascade completes"* belongs in the **report**, not in a comment. If
the product publishes a plan, it must be able to say whether that plan is reproducible.
With 30 s the cascade probably always completes on current inputs — **measure it and say
so**, do not assume it.

### Step 4 — reported settings must be the applied ones

`_apply_engine_settings` (`solver.py:278`) builds `SolverSetting(name="limits/time",
value=budget)` while the real `setParam` happens per-stage with `remaining`. **A report
declaring a configuration other than the one executed is a false witness.**

### Step 5 — `limits/nodes`: DEFERRED, with its note found

Deferred by the coordinator: the value cannot be chosen without a realistic-scale scenario,
and none exists. The note the developer remembered **exists and was located** — it is point
13 of the Step 3 checklist, unticked in three documents:

```
plan-phase00PacRebalancerRemediation.prompt.md:105    "benchmark capacity no"
plan-phase00Step3PacRebalancerSolverPolicies.prompt.md:313   "- [ ] 13. Confrontare oracle e benchmark capacity."
plan-phase00Step6PacRebalancerIntegrationTestsDocs.prompt.md:279
```

No new note created. `stop_reason: "node_limit"` (`schemas/pac_allocator.py:2406,2469`,
produced at `planner_report.py:848`) is **unreachable** while nothing passes `node_limit`:
a declared contract value that cannot be produced. Deferred with this, registered as a
precedent.

## 5. Definition of done

```
budget            effective engine_timeout_ms reaches SCIP — measured, not asserted
determinism       repeated runs at the real budget produce one candidate
correctness       the candidate still matches the oracle where the oracle applies
settings          reported == applied
tests             pac-planner core+evaluator+service green
```

---

## Progress

| step | state | date |
|---|---|---|
| 1 propagate the budget | ✅ | 2026-09-21 |
| 2 comment at solver.py:73 | ✅ | 2026-09-21 |
| 3 report the condition | ✅ | 2026-09-21 |
| 4 settings = applied | ✅ | 2026-09-21 |
| 5 limits/nodes | ⏸ deferred, note located and linked | 2026-09-21 |

> **Note implementazione (step 1)** — the plugin claims the window rather than reading
> the constant: `context.claim_engine_window(post_engine_reserve_ms=2_000)`, then
> `window.timeout_ms / 1000` down through `plan_pac_allocation` → `_search` →
> `solve_policy_program`. That preserves `catalog.py:13`'s
> `engine = min(policy, platform, soft)`, so the budget stays correct if the policy
> changes. **Propagating the mechanism, not the number.** Verified end to end with a
> spy: the solver receives **30.0 s**, not 3.5. `claim_engine_window` had zero
> production consumers before this — a tested platform capability nobody called.
>
> `solver_time_budget_seconds` defaults to `None`, and `None` forwards nothing, so
> every existing caller keeps `solver.py`'s own default. The alternative — defaulting
> to 30.0 in the planner — would have put the product number in two places.

> **Note implementazione (step 3)** — no new field. `stop_reason == "completed"`
> **already is** the reproducibility condition; what was missing is that nobody said
> so. Documented at `planner_report.py:836` with the measurement: at the real
> 30 000 ms budget both reference scenarios complete their cascade in 8/8 runs using
> **0.016%** and **0.009%** of it, one distinct candidate. The truncated regime needed
> budgets near 3 ms to reproduce at all.

> **⚠️ Fuori pista (step 4)** — two solver tests went red, correctly: they asserted
> `"limits/time" in settings`, the name I removed because it lied. A third stale
> reference lived in a docstring and would have stayed green while misleading the
> reader. Repaired by `test-author`, which also added the absence assertion — the real
> regression risk is someone re-adding a top-level `limits/time`, and nothing would
> have caught it.

> **⚠️ Fuori pista (step 5)** — the coordinator observed that
> `_POST_ENGINE_RESERVE_MS = 2_000` is the **second** number depending on the scale
> benchmark, and that my comment justifying it has the same structure as the one that
> made `3.5` invisible for five days: accurate, measured, and ageing silently.
>
> Both numbers are now listed **inside checklist item 13** of
> `plan-phase00Step3PacRebalancerSolverPolicies.prompt.md`, with a back-pointer from
> the constant. The note existed and was located — no new one was created.
