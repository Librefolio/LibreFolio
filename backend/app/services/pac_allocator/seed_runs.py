"""Several runs of one task, each with its own seed (lot SEEDS of project 67, specification §16.11 and §16.16).

The developer's rule for the Rebalancer: every request is planned three times, with three fresh random seeds, in parallel,
one process each, and all three are waited for up to the time limit. The planner hands this module the run (its whole
single-run path: the prudent model, the wide one if needed, the cascade, the replay, the result) and reads what came back
(``proof.merge_seeded_runs``).

How the runs execute:

* ``processes`` (the default): forked from the caller where the platform has ``fork`` (the Tool's worker is a fresh,
  single-threaded process per job, so a fork is cheap: 12 ms for three, measured), ``spawn`` elsewhere. Three processes
  side by side, each with the whole limit, which is wall-clock in SCIP. **The second and third run at the lowest
  priority** (lot SEEDS-b, the consultant's measured mechanism): the published plan is never worse than the first run
  alone on the same machine with the same limit, however few CPUs it has; with three free CPUs the priority changes
  nothing. No CPU is counted, so a container's quota needs no reading.
* **The wait:** once the first run has a result, the others have the limit and a short settle (an unclosed run answers
  a little after its limit), then they are stopped; while it has none, every run has the limit and the grace.
* ``in_process``: one after the other, in the caller's process. For tests that read what a run did through a patch.

A run that fails (an exception, a crash, a process that does not come back) is a run with no result: it never fails the
request by itself. No wait is unbounded: past the budget and a grace, the processes still running are stopped.
Cancellation stays with the caller: the checkpoint is checked between waits, never inside a run.
"""

from __future__ import annotations

import multiprocessing
import os
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from multiprocessing.connection import Connection, wait
from typing import Any, Literal

from backend.app.logging_config import get_logger
from backend.app.services.pac_allocator.models import Checkpoint, check_budget
from backend.app.services.pac_allocator.progress import ProgressReporter, report_phase

__all__ = ["RUN_COUNT", "SeedRun", "SeedRunMode", "fresh_seeds", "run_seeds"]

logger = get_logger(__name__)

#: Three runs per request (the developer's decision of 17/11, specification §16.16).
RUN_COUNT = 3

#: How long past its budget a run may take to come back (the exact replay, the report, the pipe) before it is stopped and
#: counted as a run with no result.
_GRACE_SECONDS = 5.0

#: How long past the limit (or past the first run's answer, if later) the others may still answer once the first has one:
#: an unclosed run answers 0.05–0.17 s after its limit on free CPUs (lot SEEDS measurement), so 0.5 s keeps their vote
#: there, while low-priority runs starved on one CPU are not waited for through the whole grace.
_SETTLE_SECONDS = 0.5

#: The priority of the second and third runs: the lowest (``os.nice``), where the platform has one.
_LOW_PRIORITY = 19

#: SCIP's ``randomization/randomseedshift`` accepts 0 .. INT_MAX.
_SEED_LIMIT = 2**31 - 1

type SeedRunMode = Literal["processes", "in_process"]
#: A run: its seed and a progress function (or None) in, its result out.
type SeedTask = Callable[[int, ProgressReporter | None], Any]


@dataclass(frozen=True, slots=True)
class SeedRun:
    """One run: its seed, what the task returned, its wall seconds, or why it returned nothing (``failure``, a class name
    only)."""

    seed: int
    result: Any = None
    failure: str | None = None
    seconds: float | None = None


def fresh_seeds(count: int = RUN_COUNT) -> tuple[int, ...]:
    """``count`` distinct random seeds for SCIP, new at every call."""
    seeds: list[int] = []
    while len(seeds) < count:
        seed = secrets.randbelow(_SEED_LIMIT)
        if seed not in seeds:
            seeds.append(seed)
    return tuple(seeds)


def run_seeds(
    task: SeedTask,
    *,
    seeds: tuple[int, ...],
    time_budget_seconds: float,
    mode: SeedRunMode = "processes",
    checkpoint: Checkpoint | None = None,
    progress: ProgressReporter | None = None,
) -> tuple[SeedRun, ...]:
    """Run ``task`` once per seed and return the runs in the order of ``seeds``.

    ``progress`` hears the furthest named search stage any run has started, each once, so the user sees the search advance
    as with one run. With ``fork`` the task needs no pickling; with ``spawn`` it and its result must pickle.
    """
    if mode == "in_process":
        return tuple(_run_here(task, seed, checkpoint, progress) for seed in seeds)
    return _run_in_processes(task, seeds, time_budget_seconds, checkpoint, progress)


def _run_here(task: SeedTask, seed: int, checkpoint: Checkpoint | None, progress: ProgressReporter | None) -> SeedRun:
    started = time.monotonic()
    try:
        return SeedRun(seed=seed, result=task(seed, progress), seconds=time.monotonic() - started)
    except Exception as exc:  # an isolation boundary: a run that fails is a run with no result, never a failed request
        if checkpoint is not None:
            check_budget(checkpoint)  # a cancellation or the request's own deadline is the caller's, not the run's
        logger.warning("Planner run failed", seed=seed, error_type=type(exc).__name__, exc_info=exc)
        return SeedRun(seed=seed, failure=type(exc).__name__, seconds=time.monotonic() - started)


def _child(task: SeedTask, seed: int, connection: Connection, low_priority: bool = False) -> None:
    """A run in its own process: search progress messages, then one result (or the class of what failed). A confirming
    run lowers its own priority first (never in the caller's process: a lowered priority cannot be raised again)."""
    if low_priority and hasattr(os, "nice"):
        os.nice(_LOW_PRIORITY)

    def forward(phase: str, step: int | None = None, total: int | None = None) -> None:
        if phase == "search" and step is not None:
            connection.send(("progress", step, total))

    started = time.monotonic()
    try:
        result = task(seed, forward)
        connection.send(("result", result, time.monotonic() - started))
    except Exception as exc:  # an isolation boundary: the parent counts it as a run with no result
        logger.warning("Planner run failed", seed=seed, error_type=type(exc).__name__, exc_info=exc)
        connection.send(("failure", type(exc).__name__, time.monotonic() - started))
    finally:
        connection.close()


class _Runs:
    """The runs still out, what came back, and the furthest stage reported (``_run_in_processes``)."""

    def __init__(self, progress: ProgressReporter | None, first: int) -> None:
        self.running: dict[Connection, tuple[int, multiprocessing.process.BaseProcess]] = {}
        self.results: dict[int, SeedRun] = {}
        self.progress = progress
        self.furthest = 0
        self.first = first
        #: When the first run came back with a result, or None.
        self.first_answered: float | None = None

    def finish(self, connection: Connection, run: SeedRun, *, stop: bool = False) -> None:
        _seed, process = self.running.pop(connection)
        self.results[run.seed] = run
        if run.seed == self.first and run.failure is None:
            self.first_answered = time.monotonic()
        connection.close()
        if stop and process.is_alive():
            process.kill()
        process.join(timeout=1.0)

    def receive(self, connection: Connection) -> None:
        seed, _process = self.running[connection]
        try:
            kind, *payload = connection.recv()
        except (EOFError, OSError):  # the process died without a result: a crash, the memory limit
            self.finish(connection, SeedRun(seed=seed, failure="RunProcessEnded"))
            return
        if kind == "progress":
            step, total = payload
            if step > self.furthest:
                self.furthest = step
                report_phase(self.progress, "search", step, total)
            return
        value, seconds = payload
        self.finish(connection, SeedRun(seed=seed, result=value, seconds=seconds) if kind == "result" else SeedRun(seed=seed, failure=value, seconds=seconds))


def _run_in_processes(task: SeedTask, seeds: tuple[int, ...], time_budget_seconds: float, checkpoint: Checkpoint | None, progress: ProgressReporter | None) -> tuple[SeedRun, ...]:
    context = multiprocessing.get_context("fork" if "fork" in multiprocessing.get_all_start_methods() else "spawn")
    runs = _Runs(progress, first=seeds[0])
    started = time.monotonic()
    for index, seed in enumerate(seeds):
        receiver, sender = context.Pipe(duplex=False)
        process = context.Process(target=_child, args=(task, seed, sender, index > 0), name=f"planner-seed-{seed}", daemon=True)
        process.start()
        sender.close()
        runs.running[receiver] = (seed, process)
    limit = started + time_budget_seconds
    deadline = limit + _GRACE_SECONDS
    try:
        while runs.running and time.monotonic() < deadline:
            if runs.first_answered is not None:
                deadline = min(deadline, max(limit, runs.first_answered) + _SETTLE_SECONDS)
            if checkpoint is not None:
                check_budget(checkpoint)
            for connection in wait(list(runs.running), timeout=max(0.0, min(deadline - time.monotonic(), 0.2))):
                runs.receive(connection)
    finally:
        for connection, (seed, _process) in list(runs.running.items()):
            runs.finish(connection, SeedRun(seed=seed, failure="RunPastDeadline"), stop=True)
    for run in runs.results.values():
        if run.failure is not None:
            logger.warning("Planner run returned no result", seed=run.seed, failure=run.failure)
    return tuple(runs.results[seed] for seed in seeds)
