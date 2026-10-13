---
title: "Python stays on 3.13 until a jump brings significant advantages; 3.14 is not scheduled; the 12/10 research report is the baseline of the next comparison (C-60)"
category: decision
status: accepted
date: 2026-10-13
tags: [backend, python, runtime, dependencies, wheels, free-threading, docker, upgrade, release-1.2]
related:
  - decisions/single-docker-image
  - features/F-062
  - problems/riskfolio-numpy-vectorbt-dependency-trap
---

# Decision: no Python jump without a reason

## Context

Python 3.15.0 came out on 2026-10-09. On 12/10 the developer asked for research (backlog C-60, «Python dopo la
3.13»), and the report of the same day, `research-python-3.15-20261012.md`, found:

- **What 3.15 brings**: explicit lazy imports (PEP 810, the `lazy import` keyword), which could start the workers that
  load QuantLib, cvxpy, matplotlib and TA-Lib faster; from 3.14, deferred annotations and interpreter improvements.
- **Free-threading** (no GIL) is still a separate build (`python3.15t`), not the default; officially supported but
  optional since 3.14 (PEP 779, phase II). It would not raise this server's throughput: the event loop stays one and
  SQLite has one writer; it would help only CPU work in threads.
- **Wheels**, checked package by package on PyPI at the pinned versions: on 12/10 cvxpy, riskfolio-lib, osqp, arch,
  ta-lib and PyYAML had none for 3.15. Readiness of the 360 most downloaded packages: 66.9 % for 3.14, 25.0 % for
  3.15, three days after its release.
- **The advice of 12/10**: 1.2 stays on 3.13 (security fixes until October 2029); after 1.2, 3.14 with the normal
  build; 3.15 towards the first quarter of 2027, after a new wheel check; free-threading later.

## Decision

The developer, on 13/10, as recorded in the backlog: «si resta sulla 3.13 finché un salto non porta vantaggi
significativi. Il passaggio alla 3.14 dopo la 1.2 non è in calendario.»

The report of 12/10 is **the starting point of the next comparisons**. Whoever reopens the question redoes its checks
and compares them with its tables:

| Check | In the report | What to look at |
|---|---|---|
| The wheels, package by package | §3, the compiled packages at the current pins, normal (`cpXY`) and free-threaded (`cpXYt`) builds; the pure-Python ones checked as `py3-none-any` | whether cvxpy, riskfolio-lib, osqp, arch, ta-lib and PyYAML publish wheels for the target |
| The state of free-threading | §2 (the phases of PEP 703 and 779, the overheads) and §4 (would it help this server?) | whether the build is still opt-in, and whether anything here would gain from it |
| The Docker images | §5 | an official `python:3.X-slim` image for the target (none existed for a free-threaded build); every stage of the `Dockerfile` moves together |

The report also lists the steps of a move: `python_version` in the `Pipfile`, every `FROM python:…` stage of the
`Dockerfile` at once, a CI run on the target version, ruff's target version, and a pass with
`-W error::DeprecationWarning`.

## Consequences

- Today the `Pipfile` pins `python_version = "3.13"` and the five stages of the `Dockerfile` start from
  `python:3.13-slim`; nothing changes in 1.2 or after it until a comparison shows a gain worth the move.
- 3.13 is in its security phase: patches only, from source, until October 2029.

## Source files

| Role | Path |
|------|------|
| The research report (12/10), the baseline | `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/research-python-3.15-20261012.md` |
| Backlog C-60, with the decision | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
| Python pin | `Pipfile` |
| Image stages | `Dockerfile` |
