"""Several runs of one task, each with its own seed (lot SEEDS of project 67, specification §16.11 and §16.16).

The developer's rule for the Rebalancer: every request is planned three times, with three fresh random seeds, one process
each, and all three are waited for up to the time limit. The planner hands this module the run (its whole single-run
path: the prudent model, the wide one if needed, the cascade, the replay, the result) and reads what came back
(``proof.merge_seeded_runs``).

The property the runs hold (the consultant's rule of 17/11): **the published plan is never worse than one run alone on
the same machine, with the same limit.** How:

* ``processes`` (the default): forked from the caller where the platform has ``fork`` (the Tool's worker is a fresh,
  single-threaded process per job, so a fork is cheap: 12 ms for three, measured), ``spawn`` elsewhere.
* **Never more runs at once than the usable CPUs** (lot SEEDS-c): the smaller of the affinity's CPUs and the CPU quota's
  whole CPUs (cgroup v2 ``cpu.max``, v1 ``cpu.cfs_quota_us``; every ancestor of the process's cgroup counts), never below
  1. A quota shares its CPUs among the group's processes whatever their priority, so three runs under a quota of one CPU
  would each get a third of it. The runs started first have the whole limit, which is wall-clock in SCIP; each later one
  starts when a run ends, with the smaller of the whole limit and the time left in the window, as long as time is left.
* **A limit per run, a whole window** (lot TURNI of project 67, specification §16.22): ``time_budget_seconds`` is the
  limit of one run, ``window_seconds`` the whole window the turns live in. With a window of as many turns as the machine
  needs, every run has its whole limit. Without a window it is the limit itself, so a later run has the time left, as
  in lot SEEDS-c; and a window shorter than the turns (a calculation that sees fewer CPUs than were counted) falls back
  to that rule instead of running past it.
* **«Impossible» needs two** (§16.17): once a run has answered «impossible», the next one starts however little time is
  left, with a short budget of its own, so one CPU never turns a lone «impossible» into a failure on every retry. Once two
  have said it, no further run is forced.
* **The three runs at the same priority**, the caller's: they are equally important (the developer's decision of 17/11,
  which removed SEEDS-b's lower priority for the second and third). The count of usable CPUs is what protects the first
  run on a small machine.
* **The wait** (one condition, ``_deadline``): a run has its budget and a grace. Once the first run has a result, the
  others have their own limit and a short settle (an unclosed run answers a little after its limit); a forced run has
  its own short budget and the settle. A run's limit runs from its own start: the first wave's limit for the first
  wave, the later run's own for a later one.
* **Progress** (lot V1; turns, TURNI 4d): ``progress`` hears the furthest named stage any run has started, as a step of the
  whole: turn × stages + stage, of turns × stages. A run in a later turn repeats the stages of the first, and the Tool
  forwards only new lines, so this keeps the stream speaking at every turn. With one turn the steps are a search's own.
* ``in_process``: one after the other, in the caller's process, each with the whole limit. For tests that read what a run
  did through a patch.

A run that fails (an exception, a crash, a process that does not come back) or does not start (no time left) is a run with
no result: it never fails the request by itself. Cancellation stays with the caller: the checkpoint is checked between
waits, never inside a run.
"""

from __future__ import annotations

import multiprocessing
import secrets
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from multiprocessing.connection import Connection, wait
from typing import Any, Literal

from backend.app.logging_config import get_logger
from backend.app.services.pac_allocator.models import Checkpoint, check_budget
from backend.app.services.pac_allocator.progress import ProgressReporter, report_phase
from backend.app.services.tools.cpus import cpu_count_usable
from backend.app.utils.runtime.errors import code_site

__all__ = ["RUN_COUNT", "RUN_GRACE_SECONDS", "SeedRun", "SeedRunMode", "cpu_count_usable", "fresh_seeds", "run_seeds", "usable_cpus"]

logger = get_logger(__name__)

#: Three runs per request (the developer's decision of 17/11, specification §16.16).
RUN_COUNT = 3

#: How long past its budget a run may take to come back (the exact replay, the report, the pipe) before it is stopped and
#: counted as a run with no result. Public: the Tool's limits keep it between turns (TURNI of project 67).
RUN_GRACE_SECONDS = 5.0
_GRACE_SECONDS = RUN_GRACE_SECONDS

#: How long past the limit (or past the first run's answer, if later) the others may still answer once the first has one:
#: an unclosed run answers 0.05–0.17 s after its limit on free CPUs (lot SEEDS measurement), so 0.5 s keeps their vote
#: there, while runs starved by other load are not waited for through the whole grace.
_SETTLE_SECONDS = 0.5

#: The budget of a run started after an «impossible» with no time left (lot SEEDS-c). Measured on 17/11: a run proves case
#: Y impossible, and closes T4, in 0.05 s; with 0.01 s it stops at its limit with no plan. One second leaves room for a
#: larger model, and bounds the wait: the run is stopped at its budget plus the settle.
_FORCED_RUN_SECONDS = 1.0

#: SCIP's ``randomization/randomseedshift`` accepts 0 .. INT_MAX.
_SEED_LIMIT = 2**31 - 1

type SeedRunMode = Literal["processes", "in_process"]
#: A run: its seed, a progress function (or None) and its time budget in seconds in, its result out.
type SeedTask = Callable[[int, ProgressReporter | None, float], Any]


@dataclass(frozen=True, slots=True)
class SeedRun:
    """One run: its seed, what the task returned, its wall seconds, or why it returned nothing (``failure``, a class name
    only; ``RunNotStarted`` when no time was left to start it)."""

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


# -- usable CPUs (lot SEEDS-c; counted by the Tool platform since TURNI of project 67) -------------------


def usable_cpus() -> int:
    """The usable CPUs of this process, read now (once per request, in the parent)."""
    return cpu_count_usable()


# -- the runs ------------------------------------------------------------------------------


def run_seeds(
    task: SeedTask,
    *,
    seeds: tuple[int, ...],
    time_budget_seconds: float,
    window_seconds: float | None = None,
    mode: SeedRunMode = "processes",
    checkpoint: Checkpoint | None = None,
    progress: ProgressReporter | None = None,
    start_next_after: Callable[[Any], bool] | None = None,
) -> tuple[SeedRun, ...]:
    """Run ``task`` once per seed and return the runs in the order of ``seeds``.

    ``time_budget_seconds`` is one run's limit and ``window_seconds`` the whole window (None: the limit itself, lot SEEDS-c's
    rule). ``progress`` hears the furthest named search stage any run has started, each once, so the user sees the search
    advance as with one run. ``start_next_after`` tells a result after which the next run starts even with no time left (the
    planner's «impossible»). With ``fork`` the task needs no pickling; with ``spawn`` it and its result must pickle.
    """
    if mode == "in_process":
        return tuple(_run_here(task, seed, checkpoint, progress, time_budget_seconds) for seed in seeds)
    return _run_in_processes(task, seeds, time_budget_seconds, time_budget_seconds if window_seconds is None else window_seconds, checkpoint, progress, start_next_after)


def _run_here(task: SeedTask, seed: int, checkpoint: Checkpoint | None, progress: ProgressReporter | None, budget: float) -> SeedRun:
    started = time.monotonic()
    try:
        return SeedRun(seed=seed, result=task(seed, progress, budget), seconds=time.monotonic() - started)
    except Exception as exc:  # an isolation boundary: a run that fails is a run with no result, never a failed request
        if checkpoint is not None:
            check_budget(checkpoint)  # a cancellation or the request's own deadline is the caller's, not the run's
        # The class and the code site, never ``exc_info``: a rendered traceback ends with the message, which can carry the
        # user's amounts (the LOGS rule; R1-B2 of project 67).
        logger.warning("Planner run failed", seed=seed, error_type=type(exc).__name__, **code_site(exc))
        return SeedRun(seed=seed, failure=type(exc).__name__, seconds=time.monotonic() - started)


def _child(task: SeedTask, seed: int, connection: Connection, budget: float) -> None:
    """A run in its own process: search progress messages, then one result (or the class of what failed)."""

    def forward(phase: str, step: int | None = None, total: int | None = None) -> None:
        if phase == "search" and step is not None:
            connection.send(("progress", step, total))

    started = time.monotonic()
    try:
        result = task(seed, forward, budget)
        connection.send(("result", result, time.monotonic() - started))
    except Exception as exc:  # an isolation boundary: the parent counts it as a run with no result
        # The class and the code site, never ``exc_info``: a rendered traceback ends with the message, which can carry the
        # user's amounts (the LOGS rule; R1-B2 of project 67).
        logger.warning("Planner run failed", seed=seed, error_type=type(exc).__name__, **code_site(exc))
        connection.send(("failure", type(exc).__name__, time.monotonic() - started))
    finally:
        connection.close()


@dataclass(slots=True)
class _Entry:
    """A run out: its seed, its process, when it started, its budget, the end of its limit, and whether it was forced by an
    «impossible»."""

    seed: int
    process: multiprocessing.process.BaseProcess
    started: float
    budget: float
    limit: float
    forced: bool
    #: The turn the run started in (0 first): its stages are reported as steps of the whole (TURNI 4d of project 67).
    turn: int = 0


class _Runs:
    """The runs out and still to start, what came back, and the furthest stage reported (``_run_in_processes``)."""

    def __init__(self, task: SeedTask, seeds: tuple[int, ...], budget: float, window: float, progress: ProgressReporter | None, start_next_after: Callable[[Any], bool] | None) -> None:
        self.context = multiprocessing.get_context("fork" if "fork" in multiprocessing.get_all_start_methods() else "spawn")
        self.task = task
        self.seeds = seeds
        self.pending = deque(enumerate(seeds))
        self.running: dict[Connection, _Entry] = {}
        self.results: dict[int, SeedRun] = {}
        self.progress = progress
        self.furthest = 0
        self.start_next_after = start_next_after
        #: One run's limit, never more than the window.
        self.budget = min(budget, window)
        self.started = time.monotonic()
        #: The end of the first wave's limit, and of the whole window.
        self.limit = self.started + self.budget
        self.window_end = self.started + window
        #: Runs launched so far, and the turns all the runs need on the CPUs counted: a run's turn is its rank over the CPUs.
        self.launched = 0
        self.turns = 1
        #: When the first run came back with a result, or None.
        self.first_answered: float | None = None
        #: «Impossible» answers so far, and whether the next run starts even with no time left.
        self.impossible = 0
        self.force_next = False

    def start(self, concurrency: int, *, first_wave: bool = False) -> None:
        """Start runs while fewer than ``concurrency`` are out: the first wave with the whole limit, the later ones with the
        smaller of the whole limit and the time left in the window, or forced after an «impossible»."""
        if first_wave:
            self.turns = -(-len(self.seeds) // concurrency)
        while self.pending and len(self.running) < concurrency:
            now = time.monotonic()
            left = self.window_end - now
            forced = self.force_next and left <= 0
            if left <= 0 and not forced:
                return
            self.force_next = False
            _index, seed = self.pending.popleft()
            budget = self.budget if first_wave else _FORCED_RUN_SECONDS if forced else min(self.budget, left)
            limit = self.limit if first_wave else now + budget
            receiver, sender = self.context.Pipe(duplex=False)
            process = self.context.Process(target=_child, args=(self.task, seed, sender, budget), name=f"planner-seed-{seed}", daemon=True)
            process.start()
            sender.close()
            self.running[receiver] = _Entry(seed=seed, process=process, started=time.monotonic(), budget=budget, limit=limit, forced=forced, turn=self.launched // concurrency)
            self.launched += 1

    def deadline(self, entry: _Entry) -> float:
        """The one stop condition: a run's budget and a grace (a forced run, the settle); once the first run has a result,
        the others also stop at their own limit, or the first's answer if later, and the settle."""
        own = entry.started + entry.budget + (_SETTLE_SECONDS if entry.forced else _GRACE_SECONDS)
        if entry.forced or self.first_answered is None or entry.seed == self.seeds[0]:
            return own
        return min(own, max(entry.limit, self.first_answered) + _SETTLE_SECONDS)

    def finish(self, connection: Connection, run: SeedRun, *, stop: bool = False) -> None:
        entry = self.running.pop(connection)
        self.results[run.seed] = run
        if run.seed == self.seeds[0] and run.failure is None:
            self.first_answered = time.monotonic()
        if run.failure is None and self.start_next_after is not None and self.start_next_after(run.result):
            self.impossible += 1
            self.force_next = self.impossible < 2
        elif entry.forced and run.failure is not None:
            # A forced run that failed or overran answered nothing: a lone «impossible» still needs a second run, so the next
            # one is forced too. One that answers «no plan» has answered (the merge publishes «no plan found»).
            self.force_next = self.impossible == 1
        connection.close()
        if stop and entry.process.is_alive():
            entry.process.kill()
        entry.process.join(timeout=1.0)

    def receive(self, connection: Connection) -> None:
        seed = self.running[connection].seed
        try:
            kind, *payload = connection.recv()
        except (EOFError, OSError):  # the process died without a result: a crash, the memory limit
            self.finish(connection, SeedRun(seed=seed, failure="RunProcessEnded"))
            return
        if kind == "progress":
            # A run in a later turn repeats the stages of the first, and the Tool forwards a line only when it is new: the
            # stream would be silent for whole turns, which a reverse proxy can cut. So a stage is reported as a step of the
            # whole: turn × stages + stage, of turns × stages (TURNI 4d of project 67). One turn reports today's steps.
            step, total = payload
            turn = self.running[connection].turn
            whole = turn * total + step
            if whole > self.furthest:
                self.furthest = whole
                report_phase(self.progress, "search", whole, self.turns * total)
            return
        value, seconds = payload
        self.finish(connection, SeedRun(seed=seed, result=value, seconds=seconds) if kind == "result" else SeedRun(seed=seed, failure=value, seconds=seconds))

    def stop_overdue(self) -> None:
        now = time.monotonic()
        for connection, entry in list(self.running.items()):
            if now >= self.deadline(entry):
                self.finish(connection, SeedRun(seed=entry.seed, failure="RunPastDeadline"), stop=True)


def _run_in_processes(task: SeedTask, seeds: tuple[int, ...], time_budget_seconds: float, window_seconds: float, checkpoint: Checkpoint | None, progress: ProgressReporter | None, start_next_after: Callable[[Any], bool] | None) -> tuple[SeedRun, ...]:
    concurrency = max(1, min(len(seeds), usable_cpus()))
    runs = _Runs(task, seeds, time_budget_seconds, window_seconds, progress, start_next_after)
    try:
        runs.start(concurrency, first_wave=True)
        while runs.running:
            if checkpoint is not None:
                check_budget(checkpoint)
            nearest = min(runs.deadline(entry) for entry in runs.running.values())
            for connection in wait(list(runs.running), timeout=max(0.0, min(nearest - time.monotonic(), 0.2))):
                runs.receive(connection)
            runs.stop_overdue()
            runs.start(concurrency)
    finally:
        for connection, entry in list(runs.running.items()):
            runs.finish(connection, SeedRun(seed=entry.seed, failure="RunPastDeadline"), stop=True)
    for _index, seed in runs.pending:
        # Normal on a machine with fewer CPUs than runs: the time ran out before this one's turn.
        runs.results[seed] = SeedRun(seed=seed, failure="RunNotStarted")
    for run in runs.results.values():
        if run.failure is not None and run.failure != "RunNotStarted":
            logger.warning("Planner run returned no result", seed=run.seed, failure=run.failure)
    logger.info("Planner runs scheduled", usable_cpus=concurrency, not_started=sum(run.failure == "RunNotStarted" for run in runs.results.values()))
    return tuple(runs.results[seed] for seed in seeds)
