---
title: "Two parallel passes lost all their coverage: a part renamed under `coverage combine`"
category: problem
status: resolved
date: 2026-10-08
tags: [testing, test-runner, coverage, python, multiprocessing, race, silent-failure]
related: [concepts/test-isolation-classes, entities/test-runner, problems/e2e-python-coverage-lost-above-two-workers, concepts/coverage-rate-vs-volume]
---

# Problem: a part renamed under `coverage combine` threw away whole parallel passes

## Symptom

The full coverage run of 2026-10-07 (`d07412899`, `--workers 2`) ended **green** with the backend at 36.8 %.
Two of its four parallel passes, the large ones with 111 and 54 units, had printed

```text
coverage combine failed: Couldn't combine from non-existent path
'…/.coverage_data/parts/.coverage.w1.<hostname>.pid10917.Xm9GZYYx'
```

The two small passes, with 24 and 11 units, had combined normally. Afterwards `parts/` still held
`….pid24531.X0pJBznx.HNQIp837rWOh`: the path coverage could not find, plus coverage's completion suffix.

## Root Cause

A race between a late writer and an explicit list of names, made silent by two other gaps.

1. **A late writer.** Under `--coverage` every interpreter of the venv starts a tracer: `COVERAGE_PROCESS_START`
   together with the venv's `a1_coverage.pth` and the project's `sitecustomize`. That includes multiprocessing's
   **resource tracker**, which the spawn context of `risk/quant/spawn_worker.py` starts. The tracker exits about
   10 ms after the pytest worker that started it, and only then saves its data.
2. **A name that changes.** coverage.py writes a parallel part under a transient name,
   `<base>.<host>.pid<N>.X<rand>x`. As the last step of `write()` it renames the file to `….X<rand>x.H<hash>h`.
3. **A snapshot of names.** `combine_coverage()` globbed `parts/.coverage.w*` the moment the workers returned.
   About a second later, after `pipenv run` had started, it passed every name it had seen to
   `coverage combine --append`. coverage.py refuses an explicit path that is no longer a file (`combinable_files`
   in `coverage/data.py`) and aborts the **whole** combine, so not one part is folded in.
4. **The parts did not survive.** The runner does not pass `--cov-append`, so pytest-cov erases
   `<COVERAGE_FILE>` and every `<COVERAGE_FILE>.*` when the next pass's workers start. They had the same names,
   so the uncombined parts were deleted before anything retried.
5. **Nobody turned red.** `_parallel_for_scope` ignored what `combine_coverage()` returned.

Replayed on a lane, the tracker's transient name appears 11 ms after its worker returns and is renamed at 34 ms,
with the same hash as on 2026-10-07: `HNQIp837rWOh`. The tracker's part lists 308 touched files and has
**0 arcs**. So it is the trigger, not the payload: what was lost was the whole pass. Small passes start no spawn
context, which is why they combined. The host name, with its spaces and parentheses, played no part: coverage
escapes its glob, and the runner passes argv without a shell.

## Solution

All of this landed on 2026-10-08.

- **Combine a directory, never a list.** coverage.py lists the directory in its own process and skips an entry
  that vanishes. `combine_coverage_dir()` is the single helper behind every combine of parallel data
  (`combine_coverage`, `_finalize_coverage`, `_coverage_combine_internal`):
  - it lists the directory again after each round, for parts that landed after coverage's own listing;
  - it runs at most three rounds, and stops early when a round changes nothing.
- **One directory per run, one name per pass.** Each runner process writes to
  `parts/run-<YYYYMMDD-HHMMSS>-<pid>/.coverage.p<pass>.w<N>`. Pytest-cov's `erase()` in one pass therefore cannot
  delete another pass's parts, and no run folds in another run's leftovers.
  - After a successful combine the run directory is removed.
  - After a failed one it stays, and the error names it together with the parts left in it.
- **A failed combine turns the parallel pass red.**
- **`.coverage` is copied back even on a failure.** Parts folded in before the failure exist only there.
- **`--cov-clean-backend` cleans `parts/`.** It removes loose `.coverage*` files and `run-*` directories, and
  keeps the JUnit reports.

### Second finding: empty parts

The first real pass after the fix went red on a single part, `….pid17336.XWmqACex.HuitnSoGmx4h`. It is a SQLite
file with every coverage table and **zero rows**, not even `coverage_schema`'s version row. coverage refuses it:
«isn't a coverage data file». Its `.H` hash is that of real data; an empty hasher would give `p11G0L8e12`.

**Why.** `Coverage._on_sigterm` (`coverage/control.py`) is not re-entrant. If a SIGTERM lands during the atexit
save, a nested save starts. It closes the outer save's connection in mid-transaction, renames the file to its
final name and kills the process. Two product paths send that signal:

- `spawn_worker.stop()` posts its sentinel, waits `join(1.0)`, then calls `terminate()`. Under load the child's
  coverage save outlasts that second; the `terminate()` line was covered in that very run.
- `ProcessTree._signal` sends `killpg(SIGTERM)` and then `terminate()` to the same processes.

The data is lost inside the child, beyond the reach of any combine. The old runner deleted such a part without a
word, because it removed every listed part after a combine that exited 0.

**The rule now:**

- A finished part (a `.H…h` name) whose `file` table is empty holds nothing to combine. It is removed and named
  with a warning, and does not turn the pass red.
- Any other unreadable part stays red, kept and named.
- A transient name is never judged empty: it may still be filling up.

The causes are in the backlog, not fixed here:

- give the child more time before SIGTERM in `spawn_worker.stop()`;
- stop signalling twice in `ProcessTree._signal`;
- report the re-entrance of `_on_sigterm` upstream to coverage.py.

## Prevention

- Never give coverage.py a snapshot of names from a directory that other processes still write into: give it the
  directory.
- The result of a combine is part of the verdict. Lost coverage that does not fail is the most expensive defect
  the runner can have.
- Any coverage artefact can be written empty (see [[problems/e2e-python-coverage-lost-above-two-workers]]). Count
  what was combined and name what was not.

## Impact

The 2026-10-07 full-coverage figure understated the backend: two of the four parallel passes were lost and the
run stayed green. The full coverage is to be re-measured once every branch has been integrated.

## Source files

| Role | Path |
|------|------|
| Per-run parts directory, combine, run-directory removal | `scripts/test_runner/_executor.py` |
| Combine helper, empty-part rule, clean-up of the parts directory | `scripts/test_runner/_coverage.py` |
| Verdict of the parallel pass | `scripts/test_runner/_cli.py` |
| `--cov-clean-backend` | `scripts/test_runner/_suites.py` |
| Contract tests | `backend/test_scripts/test_utilities/test_coverage_combine.py` |
| Registration (`utils coverage-combine`) | `scripts/test_runner/_backend_utils.py` |
| Spawn context that starts the resource tracker; `stop()` | `backend/app/services/risk/quant/spawn_worker.py` |
| Double SIGTERM | `backend/app/services/tools/process_tree.py` |
| Runner documentation | `mkdocs_src/docs/developer/test-walkthrough/runner_architecture.md` |
| Plan, analysis and evidence | `LibreFolio_developer_journal/Release_2/phases/28_fxDashboardSync/plan-phase00CoverageCombineRace.prompt.md` |
