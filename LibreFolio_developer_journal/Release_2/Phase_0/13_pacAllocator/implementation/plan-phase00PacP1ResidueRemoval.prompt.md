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
7. **A gate you have never seen fail on a case built for it is not a gate, it is a habit.**
   Before trusting a green, manufacture the red. I proposed a command to measure a delivery
   before staging and verified it *in the worktree after the coordinator had already
   staged* — where zero untracked files remained, so the condition the command exists to
   handle was absent. It passed because it could not fail. Re-run in a scratch repository
   with one modified and one new file, it also falsified a reasonable guess:
   `git diff --stat HEAD` is **as blind as** `git diff --stat`, because an untracked file
   is in the diff of no comparison at all.

### 8.1 Two agreeing measurements, and the nine ways their independence fails

The rule underneath every item above was formulated by the coordinator:

> **Two equal numbers are worth as much as the ways of obtaining them differ.** If the
> method is the same, the agreement is tautological; if the methods are independent, the
> agreement is proof and a disagreement is a localised defect.

Its practical corollary, for a delivery:

> **`git diff` does not see what is born now, in any of its forms — with or without
> `HEAD`.** After staging, measure with `--cached --stat`; before staging, sum
> `diff --stat HEAD` and `ls-files --others --exclude-standard`. Whoever delivers measures
> the second, whoever stages verifies the first, and the two numbers must agree.

Independence failed nine distinct ways in one day. All nine were caught, none by a gate
that existed beforehand.

| # | mode | what it looks like |
|---|---|---|
| 1 | **instrument** | verifying a claim with the same command that produced it |
| 2 | **environment** | verifying where the case to be covered does not exist |
| 3 | **degraded** | the instrument silently became a different instrument |
| 4 | **homonym** | the argument is ambiguous and is resolved in silence |
| 5 | **temporal** | a declared state is a photograph, not the present |
| 6 | **label** | the number is verified, the noun beside it is not |
| 7 | **reading pruning** | the counterexample was printed and did not survive the summary |
| 8 | **reconstructed citation** | a text recalled from memory, presented as a re-reading |
| 9 | **expectation-as-prediction** | the expected outcome was derived, not measured |

Modes 1–3 are about the **instrument**, 4–5 about the **argument**, 6–8 about the
**passage from measurement to text**, and 9 about the **expectation itself**. Only 1–3
require something to malfunction.

**3 — degraded.** `declare -A` does not exist in bash 3.2 (macOS). Keys are then evaluated
as *arithmetic expressions*, an unset name is `0`, so every key writes `M[0]`: each write
overwrites, **each read succeeds**, and the result is internally consistent and wrong.
Three file lists came out as three identical counts of 13; the real ones were 42 / 103 / 13.
The obvious guard gives a **false green** — `P[k]=v; [ "${P[k]}" = v ]` passes, because
write and read collapse onto the same index. Only the **exit code** of `declare -A` tells
the truth.

**4 — homonym.** `origin/dev_release2` was nine days old and already an ancestor of `HEAD`,
so `git merge origin/dev_release2` prints `Already up to date.` at exit 0 and does nothing.
The difference from the right command is not *failure vs success*, it is **success vs
success** — and counting parents does not see it, because a no-op leaves one rather than
creating two. The same family as the four homonyms inside this package: a tool code vs an
issue namespace, a function vs a `str` parameter, a class vs prose in a `description=`,
a file vs a substring of another file's name.

**6 — label.** A `svelte-check` floor circulated all day as `3/41/4 hint`. The tool prints
`3 errors and 41 warnings in 4 files`. **No hints.** The numbers were right, the noun was
not — and a second agent had already ratified it, having compared the digits. It was broken
not by a check but by someone **transcribing the output instead of inheriting the formula**.

> **Abbreviating a measurement deletes the part that can be falsified and keeps the part
> that can only be copied.** A floor is written with the unit the tool prints.

The same defect then appeared four times inside this very plan, where `3` stood without its
noun — including in the paragraph arguing for units. The one number that lost its label was
the one whose label was disputed; the other two kept theirs because nobody contested them.

**7 — reading pruning.** `grep -n` returned five lines, one of which contradicted the thesis.
Four were reported, and the conclusion said "all four". The query was correct; the selection
happened **in the reading**. No gate on the query can catch this.

> **Count before listing.** `grep -c` before `grep -n` does not fix the search — it puts a
> number between the measurement and the summary, which is the point where a correct
> observation becomes a false statement, and the only link in the chain nobody treats as a
> measurement.

**8 — reconstructed citation.** A block of "evidence" was quoted as *"verifiable in the
message I sent you"*; the message had contained four lines, the quotation five, with an
arrow marking the relevant one. Nobody annotates a line **before** knowing it matters: the
arrow is dated after. The thesis was true and proved by something else entirely — the block
had been ordered `388, 101, 157, 185`, an order raw `grep -n` output cannot have, which
demonstrates the pruning without asking anyone to be believed.

> **A citation is opened, always — including your own, and especially when it is recent.**
> Recency is exactly what makes opening it feel unnecessary, so it is the risk condition,
> not the guarantee. Reconstructing feels like remembering, and the reconstruction arrives
> *improved* by what was learned since.

The fabricated evidence was superfluous: **fabrication does not come from need, it comes
from the hurry to convince.**

**9 — expectation-as-prediction.** "This merge must stop on exactly 4 conflicts" was
announced as a gate. The merge passed clean, correctly: the two sides' hunks were two
thousand lines apart. *Same file* had been used as a proxy for *conflict*.

> **"Register the expectation first" is true and insufficient.** An expectation is a test
> only when it is a **repeated measurement** of a known state. When it is a prediction about
> a tool's behaviour on an input nobody examined, it is not a weaker test — it is a
> guaranteed false red, arriving with the authority of the pre-registered.

The contrast inside this plan is exact: §9's expectations — sha1 `1855648ef6b0`, 224 138
bytes, 169 schemas — are measurements of the previous state, and *"must not change"* cannot
be satisfied by accident.

### 8.2 What is verifiable, in three categories

```
verifiable        output reported intact, WITH THE COMMAND BESIDE IT
not verifiable    output reordered, filtered or paraphrased — even when true
not verifiable    a quotation of one's own message, absent re-opening
```

The middle category is the one that was missing. A reordered block is a true measurement
made unverifiable by its summary: not fabrication, but the same consequence — **nobody can
get back to the instrument**.

> A summarised output must carry the command that produced it. Without it, a summary is an
> assertion; with it, it is a pointer to a measurement.

### 8.3 A new countermeasure is the weakest part of the structure it protects

Against mode 5 we both adopted *"the time beside the SHA"*. Twenty minutes later:

```
adopted   ~19:00     occurrences 6     correct measurements 1
coordinator   3 timestamps declared, 0 measured; one asserting it had been read
D             3 timestamps with a constant, never-measured +1; one asserting it had
              been read — written in the message confessing the defect
              (`date` had printed 19:18:36; 19:19 was declared)
```

> **A countermeasure performed in form but not in substance is worse than its absence: it
> consumes the suspicion it would have raised.** A message with no time invites "when?". A
> message with a wrong time does not — it certifies that the author thought about it.

Three reasons it lands on the new datum specifically:

- **The part of a measurement that goes unmeasured is the part the countermeasure adds**,
  because it is the newest and nobody treats it as data yet. `d569b866d` was measured by
  three parties all day; the clock never, by anyone.
- **A new countermeasure has no known failure mode**, so there is nothing to recognise. A
  datum becomes reliable only after someone has seen how it breaks.
- **An estimate that corrects a measurement does not feel like a substitution, it feels
  like a refinement.** The `+1` modelled composition time — something the reading does not
  capture. This is the one case where opening the source is not enough, because the source
  was open.

And the sharpest of the three, because it disables the other party rather than merely
being wrong:

> **Claiming to have verified is itself an unverified claim.** "This time actually read"
> has the grammar of a gate and the substance of zero.
>
> **Do not write that you verified — write the command, or the field, the value came from.**
> `19:19:17 (command: date)` is checkable; "read" is not.

Finally, how a wrong value survives: the coordinator took `19:19` from *their own previous
message*, where they had invented it.

> **The first writing of an unmeasured value becomes its source**, and every later
> repetition feels like a confirmation. The value does not degrade with each hop — it
> **consolidates**, because each repetition adds an occurrence and none adds a check.

`3/41/4 hint` needed two people to survive a day. This needed one, re-reading themselves.

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

---

## 10. The user-facing slice

Executed after the combined revision was green. Order was fixed in advance and the last
item depends on all the others: **the CHANGELOG is written last, because before that point
it would describe an intention, and an intention is precisely what a changelog must not
contain.**

### Three pages, three fates (`docs-writer`)

```
portfolio-rebalancer/index.en.md   269 lines   DELETED + nav entry removed
pac-allocator/index.en.md          238 -> 111  REWRITTEN to the real state
tools/index.en.md                  151 -> 161  REALIGNED to a one-tool catalogue
```

Measured before delegating: 3 `.en.md`, **0** `.it/.fr/.es`, **0** image references — so no
translation debt and no screenshot to regenerate. `mkdocs build` (strict) and
`check-links` both green; 0 `WARNING|ERROR|CRITICAL` in the build log.

Four things came back that the brief had wrong or did not know:

1. **`mkdocs.yml` needed four deletions, not one.** Nav titles are translated inline in
   `nav_translations`, so the removed page had three more stale entries (it/fr/es). Nav
   titles are the sanctioned four-language exception — they are never touched by the
   translation pipeline, so editing them is not a translation run.
2. **The old PAC page was inverted, not merely stale.** P1 promised the *opposite* of what
   v2 does: *"does not convert its monetary allocation into quantities"*, *"no solver,
   optimization, or optimality claim"*. v2 plans whole-unit purchases and carries
   `OptimalProvenProof` / `InfeasibilityProvenProof`. A stale page can be updated; an
   inverted one has to be rewritten, and the difference is not one of degree.
3. **My brief asserted a product behaviour I had not measured.** I wrote that the user
   "finds the tool in the catalogue, clicks it, and gets that state". `ToolsHub.svelte:258`
   gates the full-card `<a>` overlay and the arrow on `{#if entry.interfaceState ===
   'ready'}`, so the card **is not clickable at all**; the message is shown inline. Direct
   navigation reaches it via `ToolHost.svelte`. I stated it from my model of the product
   rather than from the code.
4. **The overview's capacity table was stale for an unrelated reason** — it carried the
   `ToolOperationPolicy` class defaults rather than the effective platform values, which
   were raised for the v2 planner. Replaced with measured values from
   `effective_catalog_entries`.

A fifth was a scope extension I did not request and kept after verifying it:
`developer/architecture/patterns/tool_plugins.en.md` claimed in four places that the plugin
ships **two** services and that the compiled registry **binds components for both**. The
plugin has exactly one `ToolService(`, and `compiledRendererRegistrations` is an empty
array. Both claims were falsified by this branch, and no link from the deleted page means
neither `build` nor `check-links` would ever have caught them.

### `ToolDocumentation.version` — nothing to change, and that is the finding

The descriptor declares `path="user/tools/pac-allocator/"`, `version="2.0.0"`. With the page
rewritten to describe the v2 state, the version is now accurate. The work was not changing
a number — it was **verifying that the declared reference resolves**, because nothing else
does:

```
site/user/tools/pac-allocator/index.html        OK  197 536 bytes
site/{it,fr,es}/user/tools/pac-allocator/…      OK  all three
find site -path '*portfolio-rebalancer*'        0   (positive control: removed page gone)
find site/user/fx -name index.html             15   (positive control: matcher works)
```

> ⚠️ **`check-links` cannot see this path, and never could.** `dev.py:1073-1195` scans
> frontend `.ts`/`.svelte` for literal `/mkdocs/` strings (Scope 1) and
> `fx_providers`/`asset_source_providers` for `docs_url` (Scope 2). The tool path lives in
> neither: it is `ToolDocumentation(path=…)` in `tool_plugins/`, read at runtime.
> `grep -rl 'user/tools' frontend/src` → **0**; `grep -c 'tool_plugins' dev.py` → **0**.
>
> So a deleted or renamed PAC page would have left `check-links` green while the product's
> Documentation button 404'd. This is the `ToolDocumentation.path` precedent with its
> consequence now measured: the gate exists, and the reference is outside it.

### CHANGELOG — last, and one of its two facts was already false

Both entries lived under `[Unreleased]` and had never appeared in a dated chapter, so they
could be rewritten in place rather than retracted in a new one.

```
'Portfolio Rebalancer'   1 -> 0    the tool does not exist
'(P1)'                   2 -> 0    the prototype was never released
'monetary step'          1 -> 0    FALSE FACT: monetary_step is gone from the backend
                                   (0 files), only quantity_step survives (4 files)
```

The rewritten entry names what ships (a planner that computes whole-unit purchase plans and
says whether its answer is proven optimal, proven infeasible, or merely the best found), and
names what does not (**the interactive interface is not ready yet**). No date is promised,
because no date is measurable.
