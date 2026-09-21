# Plan — PAC/Rebalancer: removal of the remaining P1 residue

> **Predecessor**: `plan-phase00PacRebalancerRemediation.prompt.md` (commit `c7e25da93`).
> **Baseline**: `b82e59ffa` — *refactor(pac): drop P1 prototype, wire planner v2* (33 files,
> +193 / −11 877). That commit removed the P1 **tool wiring**; this plan removes the P1
> **code** that the wiring left behind.
> **Lane**: test port `6152`, data dir `/tmp/librefolio-r2-d`.
> **Coordinator**: session `c8328a01-f208-4ade-a352-0486d1f14de2`.

---

## 1. Why this plan exists, and what the previous one got wrong

`b82e59ffa` deleted the P1 `analyze` services, their UI and their tests. It did **not**
delete the P1 arithmetic, dataclasses and schemas, because those are intertwined with the
v2 exact domain inside the same files.

The remediation plan assumed a contiguous P1 block with a clean frontier. Measured on the
real files, three of its assumptions are false:

| plan assumption | measured reality |
|---|---|
| `evaluator.py` holds a large P1 region | **6 symbols**, lines 90..177, 7 % of a 3843-line file |
| `Checkpoint` is a class in the P1 region | `Checkpoint = Callable[[], None]` — a **type alias** at `models.py:13`, shared header |
| P1 symbols have no consumers | `evaluate_pac_budget` / `evaluate_rebalancing` are imported and called by a **live registered test** |

The third one is the dangerous one, and it was hidden by a defect in the measurement, not
in the code. See §2.

## 2. The measurement defect that defined a false perimeter

```bash
grep -rn "\bevaluate_pac_budget\b" backend/ --include=*.py | grep -v "evaluator.py"
   →  0        # FALSE
```

`test_pac_planner_evaluator.py` **contains the substring** `evaluator.py`. The exclusion
filter was a substring where "this exact file" was meant, and it silently swallowed the
only consumer.

> **A substring exclusion is not a file exclusion.** `grep -v "x.py"` also removes
> `test_foo_x.py` — and the more descriptive the module name, the more likely its own
> tests contain it. The filter ate precisely the class of file most likely to be a
> consumer.

This one is **not** caught by a positive control on the pattern: the pattern was correct;
the *set of files interrogated* was mutilated. It was caught because package-level
reachability reported `ext=4 inside=1` against the grep's `0`, and the disagreement was
not resolved by preferring one method.

A second, smaller defect in the same analysis: the AST walker did not handle PEP 695
`type X = ...` (`ast.TypeAlias`, neither `Assign` nor `AnnAssign`). It missed 62 aliases
in the schemas and 44 in `models.py`, and produced **12 false orphans inside the v2
region** whose names were eloquent enough to look like a discovery.

## 3. The measured perimeter

Package-level reachability: roots are symbols cited **outside**
`services/pac_allocator/` + `schemas/pac_allocator.py`, then transitive closure over the
internal reference graph.

```
symbols in package    800
external roots        269
ORPHANS                83

   76 / 346   schemas/pac_allocator.py      lines 17..521   (v2 frontier: 534)
    6 /  14   normalize.py                  lines 85..90    (residue of b82e59ffa)
    1 / 106   models.py                     line 264        (RebalancerPolicy)
    0 / 110   evaluator.py                  none — the 6 P1 symbols have a test
```

A per-file analysis is **not** sufficient: dead code in one file keeps dead code in
another alive. `HoldingEvaluation` looks live because `evaluator.py` cites it, and the
citing code is itself P1.

## 4. Must survive

| symbol | location | consumers |
|---|---|---|
| `Checkpoint` | `models.py:13` — `Callable[[], None]` | planner, solver, ledger, oracle, evaluator + 1 test |
| `check_budget` | `models.py:244` | same five modules + 1 test |
| `AllocationStrictModel` | `schemas:46` | base model of the whole v2 contract |

`Checkpoint` is **not a class**. Searching for `class Checkpoint` returns zero, which
would read as "already gone" — a ninth false zero waiting for someone to find it.

## 5. Steps

### Step 1 — `registry.test.ts`

Owner: `test-author`. The file belongs to the Tool platform (group C), the `makeCatalog`
fixture belongs to this domain: its guard message says `both Round 4 allocator contracts`.

- fixture on `pac_allocator` **2.0.0** only;
- guard message rewritten without "Round 4";
- the test at line 110 asserts *both* renderer identities — its premise no longer exists;
- **verify** that the two type errors at `:90` and `:166` disappear; if they remain the
  cause is different.

Return threshold: `svelte-check` = **3 errors**, not 0 and not 5.

### Step 2 — `normalize.py`, six constants

`_FIXED_DECIMAL`, `_DATE`, `_CURRENCY`, `_MAX_DECIMAL_DIGITS`, `_MAX_QUOTE_BASE`, `_Path`
(lines 85..90). Materials of `_Normalizer`, removed in `b82e59ffa` — **residue of my own
edit**, not of the prototype. `ruff` and `py_compile` pass happily on orphan constants.

### Step 3 — `evaluator.py` + its two tests (ATOMIC)

Symbol and test are one unit: removing either alone produces a broken import or an orphan
function that no static gate sees.

```
evaluator.py:90..177     reporting_value, _sum_values, _money_total,
                         _evaluate_money, evaluate_pac_budget, evaluate_rebalancing

test_pac_planner_evaluator.py    4686 lines · 71 tests · registered
  1143  test_p1_evaluators_remain_callable_...      REMOVE — it is P1's guardian
  1127  test_exact_error_taxonomies_and_public_..   EDIT — mixed; the invariant
                                                    stays true, the set of entry
                                                    points changes
```

Also rewrite the module docstring at `evaluator.py:1`: it describes as P1 a file that is
93 % v2. It is the first thing read by whoever opens the file.

### Step 4 — schemas, orphans

**Re-measure after step 3.** The 76 are measured with the P1 test still alive; some
schemas may be held up by it alone. *A number expires when what it measures changes.*

### Step 5 — `models.py`, P1 dataclasses

Last of the code: the most cited by the previous steps.

### Step 6 — `RebalancerPolicy` — REMOVE

Decided by the coordinator with evidence, not preference. Measured in
`plan-phase00PacRebalancerArchitecture.prompt.md` (1226 lines):

```
RebalancerPolicy   0 occurrences
PlannerPolicy      0 occurrences
invest_and_sell    1 occurrence  → §12.4, name of a restricted solver program
```

The design that would have used it does not name it, and its two values are already fully
contained in `PlannerPolicy`. Third precedent for the declared-but-never-consumed gate,
next to `monetary_step` — recorded **with its proof**, so a later reader knows it was
measured rather than preferred.

## 6. Definition of done

```
package reachability    83 orphans → 0, RE-MEASURED not assumed
svelte-check            3 errors, each identified by file:line
tests                   69 v2 tests green in test_pac_planner_evaluator.py
catalog                 ['pac_allocator'] ['plan'], 0 failures
real module import      not just ruff / py_compile
check-orphans + git diff --check
Checkpoint + check_budget INTACT
```

---

## Progress

| step | state | date |
|---|---|---|
| 1 registry.test.ts | ✅ (`test-author`) | 2026-09-21 |
| 2 normalize.py | ✅ | 2026-09-21 |
| 3 evaluator.py + tests | ✅ (`test-author` for the tests) | 2026-09-21 |
| 4 schemas | ✅ | 2026-09-21 |
| 5 models.py | ✅ | 2026-09-21 |
| 6 RebalancerPolicy | ✅ | 2026-09-21 |
| 7 runner residue `pac-analyze` ×2 | ✅ (not in the original plan) | 2026-09-21 |

### Final gates

```
package orphans     83 → 113 → 96 → 0      re-measured at each step, never assumed
tests               1175 passed, 0 failed  (9 service suites + 2 schema suites)
vitest              registry.test.ts 7/7
svelte-check        3 errors — identical file:line to the certified target baseline
contract            169 schemas, 197 775 bytes — BYTE-IDENTICAL before and after
catalog             ['pac_allocator'] ['plan'], 0 failures
check-orphans       green, both directions
git diff --check    clean
Checkpoint (models.py:11) + check_budget (58)   INTACT
```

The contract gate is the strongest evidence in this plan: removing **96 schema symbols**
changed the generated contract by **zero bytes**. Not "no visible difference" — the same
byte count and the same schema count. That is what proves they were outside the contract,
rather than my reachability analysis saying so.

> **Note implementazione (step 2)** — removed the six constants at lines 85..90, and with
> them two imports they were the only consumers of: `import re` and `PathField` from the
> schemas import list. Verified by real module import (`_FIXED_DECIMAL` absent,
> `PlannerV2NormalizationResult` present, 74 symbols) and `dev.py lint --scope backend`
> green. `py_compile` would have passed before the change too — it always does on orphan
> constants.

> **⚠️ Fuori pista (step 2)** — `dev.py lint --dead-code` **already exists**
> (vulture + knip). The six constants I measured by hand were findable with a command.
> Worse: I did not know the tool existed while writing a bespoke reachability analysis
> for the same question.
>
> Run as an independent second method it **disagrees** with mine, and the disagreement is
> the valuable part. Vulture scans `backend/app` only; my roots included
> `backend/test_scripts`. So:
>
> | symbol | app/ | test_scripts/ | reading |
> |---|---|---|---|
> | `target_map` ×2 (`models.py:174,199`) | 2 **definitions**, 0 uses | 0 | **genuinely dead** — P1 region, goes in step 5 |
> | `evaluate_pac_budget`, `evaluate_rebalancing` | def only | 3 each | P1, step 3 |
> | `exact_number_to_ratio` (`normalize.py:103`) | def only | 2 | v2, test-only |
> | `normalize_rebalancer_plan` (`normalize.py:1091`) | def only | 3 | v2, test-only |
> | `to_decimal_exact`, `ceil_to_quantum_units`, `decimal_text`, `ratio_approximation` | def only | 2..4 | v2, test-only |
> | `describe_conclusion` (`proof.py:265`) | def only | 6 | v2, test-only |
>
> **Six v2 symbols are reachable only from tests, not from production.** They are not
> dead and they are not P1: they are engine surface awaiting a consumer.
> `normalize_rebalancer_plan` is the Rebalancer entry point the next feature will wire;
> `describe_conclusion` renders the proof layer's conclusion, tested but never shown to
> anyone. **Out of scope here — reported, not acted on.**
>
> A trap inside this very check: I first read `target_map` as "used in app" because it had
> 2 occurrences under `backend/app`. Both are **definitions** — two classes each declaring
> the method. *An occurrence count is not a usage count when the symbol is defined more
> than once.*

> **Note implementazione (step 3, product code)** — removed lines 90..273 of
> `evaluator.py`: the six P1 functions, 184 lines. `dev.py lint --scope backend` then
> reported **19 unused imports, all confined to that file**, removed with `--fix`:
> `Decimal`, `localcontext`, `HoldingEvaluation`, `InstrumentEvaluation`,
> `MoneyEvaluation`, `NormalizationResult`, `PacEvaluation`, `PacNormalizationResult`,
> `ParsedContributionVector`, `ParsedMoneyVector`, `ParsedValue`, `RebalanceEvaluation`,
> `RebalanceNormalizationResult`, `unavailable_reason`, `HUNDRED`, `ZERO`,
> `decimal_context`, `exact_holding_value`.
>
> `Checkpoint` and `check_budget` are **not** in that list — the v2 half genuinely uses
> them (`evaluator.py:530,534`). That is the measurement that proves they had to survive,
> and it came from the tool rather than from my assertion.
>
> Rewrote the module docstring, which described as P1 a file that is now entirely v2, and
> **removed the `# Planner v2 exact evaluator` section marker**: with the P1 region gone it
> implies a non-v2 region above itself that no longer exists. A frontier marker outlives
> its frontier the same way a documentation page outlives its feature.

> **⚠️ Fuori pista (step 3)** — the removal orphaned `unavailable_reason`
> (`models.py:249`) as a side effect: `evaluator.py` was its only real consumer. The
> apparent second consumer,
> `ai_export/components/broker_cost_efficiency.py:387,400`, is the **homonym** — a `str`
> parameter, not this function. Moves to step 5.
>
> This is the cascade predicted in §5: *a number expires when what it measures changes.*
> Do **not** re-measure the schema perimeter until the two tests are repaired, because
> their imports still hold symbols alive.

> **Note implementazione (step 6)** — `RebalancerPolicy` removed from `models.py:264`.
> Verified independently of the coordinator: zero consumers in `backend/` and
> `frontend/src`, and the architecture plan (1226 lines) gives `RebalancerPolicy` 0,
> `PlannerPolicy` 0, `invest_and_sell` 1 — matching their measurement exactly.
> Positive control strengthened after a weak first attempt: `grep -rln PlannerPolicy`
> returned only `models.py`, which proves nothing on its own; the real evidence is
> `models.py:753,1042`, where it types the `policy` field of two dataclasses.
>
> Recorded in `TODO_FUTURI.md` as the **third precedent** of the declared-but-unconsumed
> gate, together with the **second** one that had been owed since this morning:
> `ToolDocumentation.path`, which is the mirror image — *consumed and never verified*
> against `monetary_step`'s *declared and never consumed*. Kept as a pair on purpose: two
> opposite cases show that the defect is **failing to check the extreme**, not a
> particular direction.


---

## 7. Two residues that were not in the plan

### `pac-analyze` registered twice, pointing at deleted files

`b82e59ffa` deleted `test_pac_analyze.py` and `test_pac_analyze_schemas.py` but left both
of their runner registrations alive:

```
scripts/test_runner/_backend_services.py:97,883   services_pac_analyze
scripts/test_runner/_backend_schemas.py:91,156    schemas_pac_analyze
```

Either would have failed for the next agent who ran it. Both removed.

**`dev.py test check-orphans` was green throughout**, and correctly so: it asks *"is every
registered test reachable from an `all` action?"* — registration → reachability. Nothing
asked the opposite question, *"does every registered action point at a file that exists?"*

> This is the same shape as `ToolDocumentation.path`, one gate apart: a **declared
> reference that nothing verifies**. Here the declaration is a hard-coded pytest path in
> the runner. A sweep of all 211 paths cited by `scripts/test_runner/` now finds zero
> missing (the two flagged are a comment example and a glob), so the check is cheap —
> it is simply not wired to anything.

### Test-only v2 surface, revealed by the removal

`dev.py lint --dead-code` went from 11 findings to 9 on this package, but **two are new**:
`decimal_context` (`numeric.py:364`) and `exact_holding_value` (377). The P1 evaluator was
their only production consumer; now only tests reach them.

Full list of symbols reachable from tests but not from `backend/app`:

```
normalize.py:103    exact_number_to_ratio
normalize.py:1091   normalize_rebalancer_plan     ← the Rebalancer v2 entry point
numeric.py:169      to_decimal_exact
numeric.py:256      ceil_to_quantum_units
numeric.py:364      decimal_context               ← new, cascade
numeric.py:368      decimal_text
numeric.py:377      exact_holding_value           ← new, cascade
numeric.py:386      ratio_approximation
proof.py:265        describe_conclusion           ← renders the proof conclusion
```

Not dead and not P1: engine surface with no consumer yet. **Out of scope — reported, not
acted on.** `describe_conclusion` deserves its own look later: the planner can explain its
conclusion and nothing asks it to.

## 8. What this plan taught about measuring

1. **A number expires when what it measures changes.** 83 orphans measured with the P1
   test alive became 113 once it was repaired. Acting on the first number would have left
   30 behind. Re-measured at every step, never carried forward.
2. **A substring exclusion is not a file exclusion.** `grep -v "evaluator.py"` swallowed
   `test_pac_planner_evaluator.py`, the only consumer of the code I was about to delete.
3. **An occurrence count is not a usage count** when a symbol is defined more than once:
   `target_map` read as "used" on 2 occurrences that were both definitions.
4. **A root count built from raw tokens counts prose.** `Holding`, `Target` and
   `Checkpoint` all appeared to have external consumers; every one was a comment or a
   `description="Target type…"` string. The orphan counts in this plan are therefore a
   **lower bound**, and the four were removed only after reading the actual lines.
5. **Two disagreeing methods are worth more than one confident method.** Vulture and the
   reachability analysis disagreed at every step, and the disagreement was always
   informative: vulture scans `backend/app`, the reachability roots include
   `backend/test_scripts`, so their difference *is* the test-only surface.
6. **`ruff` and `py_compile` pass on orphan module-level constants**, which is how the six
   in `normalize.py` survived a green gate. They do catch unused *imports* — which is why
   the import cascade after each removal was found by the tool rather than by me.

---

## 9. Re-validation on the combined revision `d569b866d`

> **Written before executing.** A prediction registered before the measurement is a test;
> the same observation made afterwards is an explanation. What follows was committed to
> the page while the gates were still unrun.

Merge verified first, with the gate that diagnosed the hazard rather than a new one:

```
git merge-base --is-ancestor d7c75d953 HEAD     before: false   after: TRUE
HEAD    d569b866d      HEAD^1 ef321160f (mine)      HEAD^2 d7c75d953 (target)
files brought by the merge        14      predicted 14       OK
intersection with my 42        EMPTY      predicted empty    OK
```

> ⚠️ `git merge origin/dev_release2` would have printed `Already up to date.` at exit 0
> and done nothing: that ref was nine days old and already an ancestor of HEAD. The
> difference between the right and the wrong command is not *failure vs success*, it is
> **success vs success** — and counting parents does not see it, because a no-op leaves
> one rather than creating two. Check **which**, not how many.

### Expected outcomes, fixed in advance

The merge brought exactly one file under `backend/`, an Alembic migration for onboarding.
No route, no model, no schema. Therefore:

```
generated-tools.ts sha1   1855648ef6b0…   MUST BE UNCHANGED
byte                      224 138          MUST BE UNCHANGED
tool contract             169 schemas, 197 775 bytes    UNCHANGED

4a  portfolio_rebalancer  hex, as tool_code      0      stays 0
4b  pac_allocator         hex                 1061      stays > 0
4c  portfolio_rebalancer  '.', as issue ns      37      stays 37 — v2 domain, correct

package orphans            0
tests                   1175 passed, 0 failed
svelte-check               3 errors / 41 warnings / 4 files — and the SAME file:line
catalog     ['pac_allocator'] ['plan'], 0 failures
```

**A changed contract would mean the empty intersection was false**, by a path `comm` cannot
see — a rename or a move, which `--name-only` reports as two distinct paths.

**Fewer than 3 svelte-check errors is a red, not an improvement**: it would mean a file
carrying one of them disappeared, or that the measurement did not run.

> ⚠️ Measured in **hex**. The tool names in `generated-tools.ts` are hex-encoded, so in
> plain text `4a` and `4b` both read 0 before *and* after, and would appear to confirm
> anything.
>
> ⚠️ `api sync` **before** reading any red. A merge aligns what is tracked; every ignored
> generated artifact stays at the age you left it and keeps answering.
