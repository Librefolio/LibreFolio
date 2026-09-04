---
title: "Accepted is not arrived: the option that defaults instead of failing"
category: concept
date: 2026-09-01
tags: [cli, argparse, env-vars, tooling, silent-failure, test-runner, python]
related:
  - problems/resume-mode-stale-import
  - problems/coverage-mode-stale-import
  - problems/coverage-report-category-dest-collision
  - problems/env-var-injection-point-duplicated
  - problems/registered-but-unreachable-test-actions
  - entities/test-runner
---

# Concept: accepted is not arrived

> **On the slug.** This page lives at `concepts/silent-no-op-option` because that is
> the name it was asked for and the one people will search. The title is the sharper
> statement of the same thing: the bug is not that an option does nothing, it is that
> **the option being accepted was mistaken for the option having arrived**. One of the
> four cases below is not a no-op at all — it worked, and destroyed something else.

## Definition

A tool declares an option. The parser accepts it. The user sees no error. And the
mechanism the option was supposed to reach never receives it.

The failure mode is not an exception. It is a **default** — and a default is
indistinguishable from a correct answer unless you happen to know what the answer
should have been.

> Registering an option and delivering it are two separate acts, and only the
> first one is visible.

## The four times we paid for it

| # | Option | Accepted at | Arrived at | What it cost |
|---|---|---|---|---|
| 1 | `--resume` | `_cli.py` set `_common._RESUME_MODE = True` | 13 modules had bound `False` at import time | every sub-suite re-ran inside a category that had to run at all — [[problems/resume-mode-stale-import]] |
| 2 | `--coverage` | `_cli.py` set `_common._COVERAGE_MODE = True` | `_suites.py` had bound `False` at import time | frontend E2E never instrumented; combined coverage silently under-counted every path only E2E exercised — [[problems/coverage-mode-stale-import]] |
| 3 | `coverage-report --category` | its own subparser | ...and **clobbered** `args.category`, the parent's dispatch key | subcommand dispatch misrouted/crashed — [[problems/coverage-report-category-dest-collision]] |
| 4 | `E2E_WORKERS` | `_common.apply_e2e_workers()`, called by one launcher | the second launcher never called it | the suite took **3×** as long, green throughout — [[problems/env-var-injection-point-duplicated]] |

Four incidents. The pattern was **named zero times** until this page.

A fifth, in the same family but about reachability rather than options, is
[[problems/registered-but-unreachable-test-actions]]: six registered actions,
~273 tests, green, reached by no suite. Same sentence, different noun —
*being declared is not being wired*.

## The two mechanisms underneath

**A. `from x import y` freezes a value.** Cases 1 and 2 are the same Python gotcha:

```python
# _common.py
_RESUME_MODE = False                    # default

# _cli.py, after argparse
_common._RESUME_MODE = resume           # mutates the module attribute — correct

# any module that did this at import time:
from ._common import _RESUME_MODE       # binds a LOCAL name to the CURRENT value
resume=_RESUME_MODE                     # forever False
```

`import module` then `module.FLAG` reads through. `from module import FLAG` takes a
copy. There is no warning, and the copy is taken at process start, before argparse
has run.

**B. Two paths where the design assumed one.** Cases 3 and 4. In 3 the two paths are
two argparse levels sharing a `dest`; in 4 they are two Playwright launchers, one of
which was extended and the other forgotten. Neither is detectable by reading either
path alone.

## How to not pay a fifth time

1. **Never `from module import FLAG` for anything argparse mutates.** Import the
   module and read the attribute. If a flag must be a value, pass it as a parameter
   through the call chain — an unpassed parameter is a `TypeError`, which is the
   whole point.
2. **One injection point, called by construction.** If an option travels by
   environment variable, extract the single function that injects it and make every
   launcher call it. `apply_e2e_workers()` is the shape.
3. **Assert on the receiving side.** The cheapest guard by far: the consumer reads
   the value back and fails loudly when it is absent. Turns a silent default into a
   red line.
4. **Give every `add_argument` an explicit `dest`** when a parser is nested inside
   another that already uses `dest`. Argparse's default `dest` is derived from the
   flag name and will happily collide across levels.
5. **Measure what the option is supposed to change.** Every one of the four was
   found by someone noticing a *quantity* — a wall-clock time, a coverage
   percentage, a test count — not by a failing assertion. If an option has no
   observable effect you can name, you cannot tell that it is working.

> The general rule: **an option that cannot fail loudly will fail quietly**, and
> quiet failure is bounded only by how long it takes someone to notice a number.

## Where it applies

Everywhere a value crosses a boundary it was not forced to cross: CLI → module
globals, parent parser → subparser, runner → subprocess environment, registry →
suite membership. In LibreFolio all five known instances are in
[[entities/test-runner]], which is simply where the boundaries are densest — not
evidence that the rest of the codebase is immune.

## Source files

| Role | Path |
|------|------|
| Flag definitions (`_RESUME_MODE` L44, `_COVERAGE_MODE` L31) | `scripts/test_runner/_common.py` |
| Flag mutation site (correct pattern) | `scripts/test_runner/_cli.py` — `_common._RESUME_MODE = ...` |
| Case 1 fix — 13 modules | `scripts/test_runner/_backend_api.py`, `_backend_db.py`, `_backend_external.py`, `_backend_schemas.py`, `_backend_services.py`, `_backend_utils.py`, `_frontend_asset.py`, `_frontend_broker.py`, `_frontend_fx.py`, `_frontend_portfolio.py`, `_frontend_transaction.py`, `_frontend_user.py`, `_frontend_utility.py` |
| Case 2 fix | `scripts/test_runner/_suites.py` |
| Case 3 — parent `dest` | `scripts/test_runner/_cli.py` — `add_subparsers(dest="category")` |
| Case 3 fix — `dest="cov_category"` | `scripts/coverage_analysis.py` (~L627), read at `scripts/test_runner/_cli.py` (~L604) |
| Case 4 — single injection point | `scripts/test_runner/_common.py` — `apply_e2e_workers()` (~L89) |
| Case 4 — the two launchers | `scripts/test_runner/_consolidate.py` (~L186), `scripts/test_runner/_frontend_common.py` (~L332) |
