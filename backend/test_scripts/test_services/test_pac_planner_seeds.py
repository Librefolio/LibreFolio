"""Lot SEEDS of project 67 (specification §16.11, §16.16; the consultant's definitions of 17/11): the Rebalancer's seeded
runs.

* ``seed_runs.run_seeds`` runs one task per seed, in processes (forked) or in the caller's process. A run that fails,
  dies or overruns is a run with no result.
* ``proof.merge_seeded_runs`` reads what the runs found, as a table: the lowest plan, «proven» only when two closed runs
  are equal to it, a prudent plan before a wide one, «impossible» only when two runs say so. It may only downgrade.
* ``planner.plan_exact_scenario`` with ``seeds`` plans three times in processes and publishes the chosen run, its seed on
  record. The other planner tests run once (``conftest.single_planner_run``).
"""

from __future__ import annotations

import multiprocessing
import os
import time
from fractions import Fraction

import pytest

from backend.app.config import planner as planner_config
from backend.app.config.planner import planner_fixed_seeds  # the real reader: the autouse fixture replaces the module's
from backend.app.services.pac_allocator import planner, seed_runs
from backend.app.services.pac_allocator.proof import PROOF_NOT_CONFIRMED_REASON, SeededRunVote, merge_seeded_runs, seeded_margin, seeded_runs_agree
from backend.app.services.tool_plugins.pac_allocator import plugin as pac_plugin
from backend.app.services.tools.base import ToolExecutionContext
from backend.test_scripts.test_services import _reb_small_cases as cases

# ---------------------------------------------------------------------------- the runs


@pytest.fixture(autouse=True)
def three_usable_cpus(monkeypatch):
    """The runs side by side, whatever machine runs the tests: the tests of SEEDS-c's scheduling set 1 or 2 themselves."""
    monkeypatch.setattr(seed_runs, "usable_cpus", lambda: 3)


def _echo(seed: int, progress, budget=None) -> int:
    if progress is not None:
        progress("search", step=1, total=2)
        progress("search", step=2, total=2)
    return seed * 10


def test_fresh_seeds_are_distinct_and_new_at_every_call() -> None:
    first, second = seed_runs.fresh_seeds(), seed_runs.fresh_seeds()
    assert len(first) == len(set(first)) == seed_runs.RUN_COUNT == 3
    assert first != second, "three fresh random seeds per request (the developer's decision of 17/11)"
    assert all(0 <= seed < 2**31 - 1 for seed in (*first, *second))


@pytest.mark.parametrize("mode", ["in_process", "processes"])
def test_each_seed_runs_the_task_and_comes_back_in_order(mode: str) -> None:
    runs = seed_runs.run_seeds(_echo, seeds=(7, 3, 11), time_budget_seconds=5, mode=mode)
    assert [(run.seed, run.result, run.failure) for run in runs] == [(7, 70, None), (3, 30, None), (11, 110, None)]


def test_processes_report_each_search_stage_once() -> None:
    """The search advances as with one run: the furthest stage any run has started, each once."""
    heard: list[tuple] = []
    seed_runs.run_seeds(_echo, seeds=(1, 2, 3), time_budget_seconds=5, progress=lambda phase, step=None, total=None: heard.append((phase, step, total)))
    assert heard == [("search", 1, 2), ("search", 2, 2)]


def test_a_run_that_raises_or_dies_is_a_run_with_no_result() -> None:
    def unreliable(seed: int, progress, budget=None) -> int:
        if seed == 2:
            raise RuntimeError("a run that fails")
        if seed == 3:
            os._exit(1)
        return seed

    runs = seed_runs.run_seeds(unreliable, seeds=(1, 2, 3), time_budget_seconds=5)
    assert [(run.seed, run.result, run.failure) for run in runs] == [(1, 1, None), (2, None, "RuntimeError"), (3, None, "RunProcessEnded")]


# A figure out of every source line of this file and of ``seed_runs.py``: found in the log, it can only be the message.
_PRIVATE_FIGURE = "8642.13"


def _refuses_an_amount(seed: int, progress, budget=None) -> int:
    raise ValueError(f"PRIVATE-{_PRIVATE_FIGURE}: a run refused an amount")


@pytest.mark.parametrize("path", ["here", "child"])
def test_a_failed_run_is_logged_by_class_and_code_site_never_its_message(path: str) -> None:
    """R1-B2 of project 67 (the LOGS rule, the coordinator's ruling of 20/11): a run that fails is logged by its class and
    where it was raised (``code_site``), never with ``exc_info``: a rendered traceback ends with the message, which can carry
    the user's amounts. Both places that log it: a run in the caller's process (``_run_here``) and a run in its own
    process (``_child``, called here in this process, so that its line is captured)."""
    from structlog.testing import capture_logs  # noqa: PLC0415 — beside its only use

    with capture_logs() as lines:
        if path == "here":
            run = seed_runs._run_here(_refuses_an_amount, 7, None, None, 5.0)
            assert (run.result, run.failure) == (None, "ValueError")
        else:
            receiver, sender = multiprocessing.Pipe(duplex=False)
            seed_runs._child(_refuses_an_amount, 7, sender, 5.0)
            assert receiver.recv()[:2] == ("failure", "ValueError")
            receiver.close()

    (line,) = [line for line in lines if line["event"] == "Planner run failed"]
    assert (line["seed"], line["error_type"]) == (7, "ValueError"), line
    assert "exc_info" not in line and "exception" not in line, f"a traceback would render the message: {line}"
    assert line["where"].endswith(":_refuses_an_amount"), line
    assert _PRIVATE_FIGURE not in repr(line), f"the message reached the log: {line}"


def test_a_run_past_the_deadline_is_stopped_and_has_no_result(monkeypatch) -> None:
    """No wait is unbounded: past the budget and the grace, a run still out is stopped."""
    monkeypatch.setattr(seed_runs, "_GRACE_SECONDS", 0.5)

    def slow(seed: int, progress, budget=None) -> int:
        if seed == 2:
            time.sleep(60)
        return seed

    started = time.monotonic()
    runs = seed_runs.run_seeds(slow, seeds=(1, 2), time_budget_seconds=0.5)
    assert time.monotonic() - started < 10
    assert [(run.seed, run.result, run.failure) for run in runs] == [(1, 1, None), (2, None, "RunPastDeadline")]


def test_a_cancellation_while_runs_are_out_stops_them_all_and_reaches_the_caller() -> None:
    """The caller's checkpoint raises between waits (a cancellation, the request's own deadline): the exception is the
    caller's, and no run survives it."""

    class Cancelled(Exception):
        pass

    calls = 0

    def cancel_on_the_third_wait() -> None:
        nonlocal calls
        calls += 1
        if calls >= 3:
            raise Cancelled

    def endless(seed: int, progress, budget=None) -> int:
        time.sleep(60)
        return seed

    started = time.monotonic()
    with pytest.raises(Cancelled):
        seed_runs.run_seeds(endless, seeds=(1, 2, 3), time_budget_seconds=60, checkpoint=cancel_on_the_third_wait)
    assert time.monotonic() - started < 10
    assert [process.name for process in multiprocessing.active_children() if process.name.startswith("planner-seed-")] == []


def _niceness(seed: int, progress, budget=None) -> int:
    return os.nice(0)


@pytest.mark.skipif(not hasattr(os, "nice"), reason="no priority to read")
def test_the_three_runs_run_at_the_caller_s_priority() -> None:
    """The three runs are equally important (the developer's decision of 17/11): none lowers its priority, whether they
    run side by side or in turn. SEEDS-b's lower priority for the second and third is gone with SEEDS-c's CPU count."""
    base = os.nice(0)
    assert [run.result for run in seed_runs.run_seeds(_niceness, seeds=(5, 6, 7), time_budget_seconds=5)] == [base, base, base]


def test_once_the_first_run_has_answered_the_others_are_stopped_soon_after_the_limit(monkeypatch) -> None:
    """The others are not waited for through the whole grace: once the first has a result, they have the limit and a short
    settle, then they are stopped and count as runs with no result."""
    monkeypatch.setattr(seed_runs, "_GRACE_SECONDS", 30.0)

    def second_never_ends(seed: int, progress, budget=None) -> int:
        if seed == 2:
            time.sleep(60)
        return seed

    started = time.monotonic()
    runs = seed_runs.run_seeds(second_never_ends, seeds=(1, 2), time_budget_seconds=0.5)
    assert time.monotonic() - started < 0.5 + seed_runs._SETTLE_SECONDS + 2.0
    assert [(run.seed, run.result, run.failure) for run in runs] == [(1, 1, None), (2, None, "RunPastDeadline")]


def test_a_run_answering_just_past_the_limit_still_votes(monkeypatch) -> None:
    """An unclosed run answers a little after its limit (0.05–0.17 s measured on free CPUs): inside the settle, it votes."""
    monkeypatch.setattr(seed_runs, "_GRACE_SECONDS", 30.0)
    # A wide settle, so a loaded machine does not decide the test: the late run answers 0.1 s past the limit.
    monkeypatch.setattr(seed_runs, "_SETTLE_SECONDS", 2.0)

    def second_just_late(seed: int, progress, budget=None) -> int:
        if seed == 2:
            time.sleep(0.6)
        return seed

    runs = seed_runs.run_seeds(second_just_late, seeds=(1, 2), time_budget_seconds=0.5)
    assert [(run.seed, run.result, run.failure) for run in runs] == [(1, 1, None), (2, 2, None)]


def test_when_the_first_run_fails_the_others_keep_the_whole_grace(monkeypatch) -> None:
    """With no first answer, the others are what the request has: they are waited for up to the limit and the grace."""
    monkeypatch.setattr(seed_runs, "_GRACE_SECONDS", 30.0)

    def first_fails(seed: int, progress, budget=None) -> int:
        if seed == 1:
            raise RuntimeError("a run that fails")
        time.sleep(0.5 + seed_runs._SETTLE_SECONDS + 0.5)
        return seed

    runs = seed_runs.run_seeds(first_fails, seeds=(1, 2), time_budget_seconds=0.5)
    assert [(run.seed, run.result, run.failure) for run in runs] == [(1, None, "RuntimeError"), (2, 2, None)]


# ---------------------------------------------------------------------------- SEEDS-c: never more runs than usable CPUs


def _cgroup_tree(tmp_path, proc: str, files: dict[str, str]):
    """A fake `/proc/self/cgroup` and `/sys/fs/cgroup`: `files` maps a path under the root to its text."""
    (tmp_path / "proc").write_text(proc)
    root = tmp_path / "cgroup"
    for path, text in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    return tmp_path / "proc", root


@pytest.mark.parametrize(
    ("proc", "files", "affinity", "usable"),
    [
        pytest.param("0::/a/b\n", {"a/b/cpu.max": "max 100000\n", "a/cpu.max": "150000 100000\n"}, 16, 1, id="v2-ancestor-1.5-rounds-down"),
        pytest.param("0::/a/b\n", {"a/b/cpu.max": "200000 100000\n"}, 16, 2, id="v2-quota-2"),
        pytest.param("0::/a/b\n", {"a/b/cpu.max": "200000 100000\n"}, 1, 1, id="v2-affinity-smaller"),
        pytest.param("0::/a\n", {"a/cpu.max": "50000 100000\n"}, 16, 1, id="v2-half-a-cpu-is-one"),
        pytest.param("0::/a\n", {"a/cpu.max": "max 100000\n"}, 16, 16, id="v2-no-quota"),
        pytest.param("0::/\n", {"cpu.max": "300000 100000\n"}, 16, 3, id="v2-container-root"),
        pytest.param("0::/a\n", {}, 4, 4, id="no-file"),
        pytest.param("0::/a\n", {"a/cpu.max": "unreadable\n"}, 4, 4, id="garbage"),
        pytest.param("4:cpu,cpuacct:/docker/x\n", {"cpu,cpuacct/docker/x/cpu.cfs_quota_us": "300000\n", "cpu,cpuacct/docker/x/cpu.cfs_period_us": "100000\n"}, 16, 3, id="v1-quota-3"),
        pytest.param("4:cpu,cpuacct:/docker/x\n", {"cpu,cpuacct/docker/x/cpu.cfs_quota_us": "-1\n", "cpu,cpuacct/docker/x/cpu.cfs_period_us": "100000\n"}, 16, 16, id="v1-no-quota"),
    ],
)
def test_usable_cpus_are_the_affinity_or_the_quota_s_whole_cpus(tmp_path, proc: str, files: dict, affinity: int, usable: int) -> None:
    """Lot SEEDS-c (the consultant's rule of 17/11): the smaller of the affinity's CPUs and the quota's whole CPUs
    (rounded down), never below 1; every ancestor of the process's cgroup counts; cgroup v2 `cpu.max` and v1
    `cpu.cfs_quota_us` over `cpu.cfs_period_us`; a file that cannot be read means no quota."""
    proc_file, root = _cgroup_tree(tmp_path, proc, files)
    assert seed_runs.cpu_count_usable(proc_cgroup=proc_file, cgroup_root=root, affinity=affinity) == usable


def _stamps(seed: int, progress, budget=None):
    started = time.monotonic()
    time.sleep(0.3)
    return (started, time.monotonic(), budget)


def test_one_usable_cpu_runs_one_at_a_time_each_with_the_time_left(monkeypatch) -> None:
    """One usable CPU: the runs go in turn. The first has the whole limit; each later one starts when the previous ends,
    with the time left."""
    monkeypatch.setattr(seed_runs, "usable_cpus", lambda: 1)
    runs = seed_runs.run_seeds(_stamps, seeds=(1, 2, 3), time_budget_seconds=5)
    (s1, e1, b1), (s2, e2, b2), (s3, _e3, b3) = (run.result for run in runs)
    assert s2 >= e1 and s3 >= e2, "never two runs at once"
    assert b1 == 5 and 4 < b3 < b2 < 5, "the first the whole limit, the others the time left"


def test_two_usable_cpus_run_two_at_once_the_third_when_one_ends(monkeypatch) -> None:
    monkeypatch.setattr(seed_runs, "usable_cpus", lambda: 2)
    runs = seed_runs.run_seeds(_stamps, seeds=(1, 2, 3), time_budget_seconds=5)
    (s1, e1, _b1), (s2, e2, _b2), (s3, _e3, b3) = (run.result for run in runs)
    assert s2 < e1 and s1 < e2, "the first two side by side"
    assert s3 >= min(e1, e2) and b3 < 5


def test_with_no_time_left_the_later_runs_do_not_start(monkeypatch) -> None:
    """Three runs in all only while time is left: a run not started counts as a run with no result."""
    monkeypatch.setattr(seed_runs, "usable_cpus", lambda: 1)

    def first_takes_it_all(seed: int, progress, budget=None):
        time.sleep(0.6)
        return seed

    runs = seed_runs.run_seeds(first_takes_it_all, seeds=(1, 2, 3), time_budget_seconds=0.5)
    assert [(run.seed, run.result, run.failure) for run in runs] == [(1, 1, None), (2, None, "RunNotStarted"), (3, None, "RunNotStarted")]


def test_after_an_impossible_the_next_run_always_starts_with_a_bounded_wait(monkeypatch) -> None:
    """«Impossible» needs two runs (the consultant's rule of 17/11): once a run has answered it, the next one starts
    however little time is left, with a short budget of its own and a bounded wait. Once two have said it, no more."""
    monkeypatch.setattr(seed_runs, "usable_cpus", lambda: 1)

    def late_impossible(seed: int, progress, budget=None):
        if seed == 1:
            time.sleep(0.6)
            return ("impossible", budget)
        return ("none", budget)

    runs = seed_runs.run_seeds(late_impossible, seeds=(1, 2, 3), time_budget_seconds=0.5, start_next_after=lambda result: result[0] == "impossible")
    assert runs[0].result == ("impossible", 0.5)
    assert runs[1].result == ("none", seed_runs._FORCED_RUN_SECONDS), "started with no time left, its own short budget"
    assert runs[2].failure == "RunNotStarted", "not forced: the second did not answer «impossible»"

    def all_impossible(seed: int, progress, budget=None):
        time.sleep(0.6)
        return ("impossible", budget)

    runs = seed_runs.run_seeds(all_impossible, seeds=(1, 2, 3), time_budget_seconds=0.5, start_next_after=lambda result: result[0] == "impossible")
    assert [run.failure for run in runs] == [None, None, "RunNotStarted"], "two «impossible» agree: the third is not forced"

    def forced_never_ends(seed: int, progress, budget=None):
        if seed == 1:
            time.sleep(0.6)
            return ("impossible", budget)
        time.sleep(60)
        return ("none", budget)

    started = time.monotonic()
    runs = seed_runs.run_seeds(forced_never_ends, seeds=(1, 2, 3), time_budget_seconds=0.5, start_next_after=lambda result: result[0] == "impossible")
    # A forced run that overruns confirms nothing: the lone «impossible» still needs a second, so the third is forced too.
    assert time.monotonic() - started < 0.6 + 2 * (seed_runs._FORCED_RUN_SECONDS + seed_runs._SETTLE_SECONDS) + 2.0
    assert runs[1].failure == "RunPastDeadline"
    assert runs[2].failure == "RunPastDeadline", "forced in its turn, and stopped at its own bound"


# ---------------------------------------------------------------------------- TURNI step 1: a limit per run, a whole window
#
# The developer's decision of 19/11 (specification §16.22): each run has its whole limit, and a run that starts later starts
# with that limit, not with the time left. ``run_seeds`` takes both numbers: ``time_budget_seconds``, the limit of one run,
# and ``window_seconds``, the whole window the turns live in. A later run starts with the smaller of its limit and the time
# left in the window. Without a window it is the limit itself: today's rule, unchanged until the Tool passes one (step 4).


@pytest.mark.parametrize("cpus", [1, 2, 16])
def test_without_a_window_the_runs_keep_today_s_budgets(monkeypatch, cpus: int) -> None:
    """Step 1 changes nothing by itself: no window is the limit, so the first wave has the whole limit and a later run the
    time left, at 1, 2 and 16 usable CPUs alike."""
    monkeypatch.setattr(seed_runs, "usable_cpus", lambda: cpus)
    # Each run's own limit, as the scheduler records it (``_Entry.limit``), beside the first wave's (``_Runs.limit``).
    entries, limits = [], []
    real_entry, real_init = seed_runs._Entry, seed_runs._Runs.__init__

    def entry(**fields):
        entries.append(fields)
        return real_entry(**fields)

    def init(self, *args, **kwargs):
        real_init(self, *args, **kwargs)
        limits.append(self.limit)

    monkeypatch.setattr(seed_runs, "_Entry", entry)
    monkeypatch.setattr(seed_runs._Runs, "__init__", init)
    runs = seed_runs.run_seeds(_stamps, seeds=(1, 2, 3), time_budget_seconds=5)
    budgets = [run.result[2] for run in runs]
    first_wave = min(cpus, 3)
    assert budgets[:first_wave] == [5] * first_wave, "the first wave has the whole limit"
    assert all(4 < budget < 5 for budget in budgets[first_wave:]), "a later run has the time left"
    # And the stop time is today's: every run's limit is the first wave's, the later ones to the float's rounding.
    assert all(abs(fields["limit"] - limits[0]) < 1e-6 for fields in entries), [fields["limit"] - limits[0] for fields in entries]


def test_one_usable_cpu_gives_each_run_its_whole_limit(monkeypatch) -> None:
    """One usable CPU and a window of three turns: the runs go one after the other, each with the whole limit."""
    monkeypatch.setattr(seed_runs, "usable_cpus", lambda: 1)
    runs = seed_runs.run_seeds(_stamps, seeds=(1, 2, 3), time_budget_seconds=5, window_seconds=15)
    (s1, e1, b1), (s2, e2, b2), (s3, _e3, b3) = (run.result for run in runs)
    assert s2 >= e1 and s3 >= e2, "never two runs at once"
    assert (b1, b2, b3) == (5, 5, 5), "each run its whole limit, not the time left"


def test_two_usable_cpus_give_the_third_run_its_whole_limit(monkeypatch) -> None:
    """Two usable CPUs and a window of two turns: the third starts when one of the first two ends, with the whole limit."""
    monkeypatch.setattr(seed_runs, "usable_cpus", lambda: 2)
    runs = seed_runs.run_seeds(_stamps, seeds=(1, 2, 3), time_budget_seconds=5, window_seconds=10)
    (s1, e1, b1), (s2, e2, b2), (s3, _e3, b3) = (run.result for run in runs)
    assert s2 < e1 and s1 < e2, "the first two side by side"
    assert s3 >= min(e1, e2)
    assert (b1, b2, b3) == (5, 5, 5)


def test_a_run_never_starts_past_the_whole_window(monkeypatch) -> None:
    """A window shorter than the turns (the calculation sees fewer CPUs than the server counted): a later run has the time
    left in the window, never more, and none starts once the window is spent."""
    monkeypatch.setattr(seed_runs, "usable_cpus", lambda: 1)

    def one_second(seed: int, progress, budget=None):
        started = time.monotonic()
        time.sleep(1.0)
        return (started, time.monotonic(), budget)

    started = time.monotonic()
    # Each run takes about 1 s: the second starts with about 5.5 s left (its whole 5 s fit, 0.5 s to spare), the third
    # with about 4.5 s (0.5 s short of its limit). Half a second each way: a busy machine does not move the case.
    runs = seed_runs.run_seeds(one_second, seeds=(1, 2, 3), time_budget_seconds=5, window_seconds=6.5)
    (_s1, _e1, b1), (_s2, _e2, b2), (s3, _e3, b3) = (run.result for run in runs)
    assert b1 == 5 and b2 == 5, "the second still fits whole"
    assert 3.5 < b3 < 5, "the third has the time left in the window, not its whole limit"
    assert s3 + b3 <= started + 6.5 + 0.05, "no run's limit passes the window"

    def first_takes_the_window(seed: int, progress, budget=None):
        time.sleep(0.6)
        return seed

    runs = seed_runs.run_seeds(first_takes_the_window, seeds=(1, 2, 3), time_budget_seconds=0.5, window_seconds=0.5)
    assert [run.failure for run in runs] == [None, "RunNotStarted", "RunNotStarted"]


def test_a_later_run_is_stopped_at_its_own_limit_not_the_first_wave_s(monkeypatch) -> None:
    """Once the first run has answered, the others stop at their limit and a settle. With turns a later run's limit runs
    from its own start: the first wave's limit must not cut it short."""
    monkeypatch.setattr(seed_runs, "usable_cpus", lambda: 1)
    monkeypatch.setattr(seed_runs, "_GRACE_SECONDS", 30.0)

    def first_quick_second_long(seed: int, progress, budget=None):
        time.sleep(0.8 if seed == 1 else 0.95 if seed == 2 else 0.0)
        return seed

    # The first answers at 0.8 s; the second starts then, with 1.0 s of its own, and answers at about 1.75 s: past the first
    # wave's limit and settle (1.0 + 0.5 s), inside its own (1.8 + 0.5 s).
    runs = seed_runs.run_seeds(first_quick_second_long, seeds=(1, 2, 3), time_budget_seconds=1.0, window_seconds=3.0)
    assert [(run.result, run.failure) for run in runs[:2]] == [(1, None), (2, None)]


# ---------------------------------------------------------------------------- the merge, as a table

V = Fraction(77600, 100)  # 776 €, about G5's score
TOLERANCE = 2 * Fraction(1, 10**6) * V  # the agreement rule at that value, with no band: 0.00155 €
BAND = Fraction(1, 10**5)  # the first stage's band of «Balanced», one quadratic row per target (`seeds_band.log`)


def _prudent(seed: int, value: Fraction, *, closed: bool = True, band: Fraction = Fraction(0)) -> SeededRunVote:
    return SeededRunVote(seed=seed, origin="prudent", closed=closed, value=value, band=band)


def test_two_values_agree_within_twice_the_engine_s_whole_band() -> None:
    """Lot SEEDS-b (the consultant's answer of 17/11): |a − b| ≤ 2 × (1e-6 × max(1, |lowest|) + band). Two plans, each
    within one band of the same closure, are at most two bands apart; the band is the bound check's relative tolerance plus
    the first stage's own band."""
    limit = 2 * (Fraction(1, 10**6) * V + BAND)
    assert seeded_runs_agree(V + limit, V, V, band=BAND)
    assert not seeded_runs_agree(V + limit + Fraction(1, 10**9), V, V, band=BAND)
    assert seeded_runs_agree(V + TOLERANCE, V, V)
    assert not seeded_runs_agree(V + TOLERANCE + Fraction(1, 10**9), V, V), "the factor is 2, no longer 5"
    assert seeded_runs_agree(Fraction(2, 10**6), Fraction(0), Fraction(0)), "below one, the rule reads one"
    assert not seeded_runs_agree(Fraction(2, 10**6) + Fraction(1, 10**12), Fraction(0), Fraction(0))


@pytest.mark.parametrize(
    ("value", "lowest", "band", "agree"),
    [
        pytest.param("46075417.2259534", "46075413.8988546", "0.594", True, id="targetfirst s3 and s1, both closed: 7.2e-8"),
        pytest.param("1125.7829371", "1125.7813537", "0.00001", True, id="cashmax, closed runs over a lower unclosed one: 1.4e-6"),
        pytest.param("775.8402125", "775.8364441", "0.00001", False, id="G5 seed 3, a different plan: 4.86e-6"),
    ],
)
def test_the_three_measured_gaps_fall_where_the_consultant_put_them(value: str, lowest: str, band: str, agree: bool) -> None:
    """The lane's exact figures (`seeds_measure2.log`, `seeds_band.log`), with their real bands: the two gaps between runs
    that closed on the same optimum agree, the different plan 0.0038 € above G5's optimum does not."""
    assert seeded_runs_agree(Fraction(value), Fraction(lowest), Fraction(lowest), band=Fraction(band)) is agree


def test_near_the_target_the_band_widens_the_rule() -> None:
    """A portfolio already near its target: the first stage is worth 1 €, so the relative part is 1e-6 € and the stage's
    band (1e-5 €) decides. Two runs closed within twice the whole band agree."""
    one = Fraction(1)
    limit = 2 * (Fraction(1, 10**6) + BAND)
    assert seeded_runs_agree(one + limit, one, one, band=BAND)
    assert not seeded_runs_agree(one + limit + Fraction(1, 10**9), one, one, band=BAND)
    assert not seeded_runs_agree(one + limit, one, one), "without the band, the relative rule alone"
    verdict = merge_seeded_runs([_prudent(1, one + limit, band=BAND), _prudent(2, one, band=BAND), SeededRunVote(seed=3, failed=True)])
    assert (verdict.index, verdict.downgrade) == (1, False)


@pytest.mark.parametrize(
    ("votes", "index", "downgrade", "state"),
    [
        pytest.param([_prudent(1, V), _prudent(2, V), _prudent(3, V)], 0, False, "plan", id="three-closed-equal: proven, the lowest seed"),
        pytest.param([_prudent(1, V + Fraction(9, 10)), _prudent(2, V), _prudent(3, V + TOLERANCE / 2)], 1, False, "plan", id="two-closed-on-the-lowest: proven, the lowest of them"),
        pytest.param([_prudent(1, V), _prudent(2, V), _prudent(3, V - 1, closed=False)], 2, False, "plan", id="two-equal-the-third-lower: the third, its own verdict (§16.11)"),
        pytest.param([_prudent(1, V), _prudent(2, V + 1), _prudent(3, V + 2)], 0, True, "plan", id="all-different: the lowest, its proof not confirmed"),
        pytest.param([_prudent(1, V, closed=False), _prudent(2, V, closed=False), _prudent(3, V + 1)], 0, False, "plan", id="lowest-unclosed: published as it is, never upgraded"),
        pytest.param([_prudent(1, V), SeededRunVote(seed=2, failed=True), SeededRunVote(seed=3, failed=True)], 0, True, "plan", id="one-plan-two-failures: not confirmed"),
        pytest.param([SeededRunVote(seed=1, origin="wide", value=V - 5), _prudent(2, V, closed=False), SeededRunVote(seed=3, infeasible=True)], 1, False, "plan", id="a-prudent-plan-beats-a-wide-one-and-an-impossible"),
        pytest.param([SeededRunVote(seed=1, origin="wide", value=V + 1), SeededRunVote(seed=2, origin="wide", value=V), SeededRunVote(seed=3, infeasible=True)], 1, False, "plan", id="wide-plans: the lowest, never proven"),
        pytest.param([SeededRunVote(seed=1, infeasible=True), SeededRunVote(seed=2, infeasible=True), SeededRunVote(seed=3)], 0, False, "infeasible", id="two-impossible: impossible, proven"),
        pytest.param([SeededRunVote(seed=1, infeasible=True), SeededRunVote(seed=2), SeededRunVote(seed=3)], 1, False, "no_plan", id="one-impossible: no plan found"),
        pytest.param([SeededRunVote(seed=1, infeasible=True), SeededRunVote(seed=2, failed=True), SeededRunVote(seed=3, failed=True)], None, False, "inconclusive", id="one-impossible-alone: inconclusive"),
        pytest.param([SeededRunVote(seed=1, failed=True), SeededRunVote(seed=2, failed=True), SeededRunVote(seed=3, failed=True)], None, False, "failed", id="three-failures"),
    ],
)
def test_the_merge_of_three_runs(votes, index, downgrade, state) -> None:
    verdict = merge_seeded_runs(votes)
    assert (verdict.index, verdict.downgrade, verdict.state) == (index, downgrade, state)


# ---------------------------------------------------------------------------- MG: the margin of a plan not proven


def _run(seed: int, value: Fraction, bound: Fraction | None, *, closed: bool = False, origin: str = "prudent") -> SeededRunVote:
    return SeededRunVote(seed=seed, origin=origin, closed=closed, value=value, band=BAND, bound=bound)


@pytest.mark.parametrize(
    ("votes", "margin"),
    [
        pytest.param([_run(1, V, V, closed=True), _run(2, V, V, closed=True), _run(3, V, V - 1, closed=True)], None, id="proven: no margin"),
        pytest.param([_run(1, V, V, closed=True), _run(2, V + 1, V - Fraction(1, 2)), _run(3, V + 2, V - Fraction(1, 5))], Fraction(1, 5), id="one closed, two unfinished: the second-highest bound"),
        pytest.param([_run(1, V, V - Fraction(3, 10)), _run(2, V + 1, V + Fraction(1, 2)), _run(3, V + 2, V - Fraction(2, 5))], Fraction(2, 5), id="a bound above the plan beyond the band is refuted and dropped"),
        pytest.param([_run(1, V, V - Fraction(3, 10)), _run(2, V + 1, V + Fraction(1, 2)), _run(3, V + 2, None)], None, id="fewer than two usable bounds: no margin"),
        pytest.param([_run(1, V, V - Fraction(3, 10)), SeededRunVote(seed=2, failed=True), SeededRunVote(seed=3, failed=True)], None, id="two runs with no answer: one bound, no margin"),
        pytest.param([_run(1, V, V - 1, origin="wide"), _run(2, V + 1, V - 2, origin="wide"), SeededRunVote(seed=3, infeasible=True)], None, id="a plan of the wide model: no margin"),
        pytest.param([_run(1, V, V + TOLERANCE / 4), _run(2, V + 1, V + TOLERANCE / 8), _run(3, V + 2, None)], -(TOLERANCE / 8), id="bounds above the plan inside the band: a margin at most zero, one minor unit once posted"),
    ],
)
def test_the_margin_is_the_plan_less_the_second_highest_usable_bound(votes, margin) -> None:
    """Lot MG (the developer's «ottimo locale (entro X)», the consultant's rule of 17/11): the margin of a plan not proven
    is how far below it the best plan can still be, V − L. L is the second-highest of the runs' first-stage bounds that
    are usable: not above V beyond the agreement band. A bound counts when two searches say it, as the proof does. Fewer
    than two usable bounds, a proven plan, or a plan of the wide model: no margin."""
    assert seeded_margin(votes, merge_seeded_runs(votes)) == margin


@pytest.mark.parametrize(
    ("raw", "scale", "posted"),
    [
        pytest.param(Fraction(3, 1000), Fraction(1), Fraction(1, 100), id="0.003 EUR reads 0.01"),
        pytest.param(Fraction(1, 5), Fraction(1), Fraction(20, 100), id="0.20 stays 0.20"),
        pytest.param(Fraction(2001, 10000), Fraction(1), Fraction(21, 100), id="rounded up"),
        pytest.param(Fraction(-1, 10**6), Fraction(1), Fraction(1, 100), id="at most zero reads one minor unit, never 0.00"),
        pytest.param(Fraction(5000), Fraction(1, 10000), Fraction(50, 100), id="Target first: the distance over F, in euros"),
    ],
)
def test_the_margin_is_posted_up_to_the_minor_unit_never_zero(raw: Fraction, scale: Fraction, posted: Fraction) -> None:
    assert planner._margin_money(raw, scale, Fraction(1, 100)) == posted


def test_a_plan_not_confirmed_publishes_its_margin(monkeypatch) -> None:
    """Through the planner, three runs of T4 in processes: seed 1 closes; seeds 2 and 3 are made unfinished, with lower
    bounds of their own. The plan is seed 1's, «not confirmed», and its margin is V − the second-highest bound, in euros."""
    import dataclasses  # noqa: PLC0415

    real = planner._single_run

    def two_unfinished(scenario, view, issues, checkpoint, budget, product, progress, *, seed=None):
        outcome = real(scenario, view, issues, checkpoint, budget, product, progress, seed=seed)
        if seed == 1:
            return outcome
        offset = {2: Fraction(1, 2), 3: Fraction(1, 5)}[seed]
        return dataclasses.replace(outcome, closed=False, bound=outcome.value - offset)

    monkeypatch.setattr(planner, "_single_run", two_unfinished)
    result = planner.plan_exact_scenario(cases.t4(), solver_time_budget_seconds=5, seeds=(1, 2, 3)).result
    assert (result.result_state, result.proof.kind, result.proof.reason_code) == ("ready_incumbent", "not_proven", PROOF_NOT_CONFIRMED_REASON)
    assert (Fraction(result.proof.margin.amount), result.proof.margin.currency) == (Fraction(20, 100), "EUR")


def test_the_pac_publishes_no_margin_even_with_a_gap() -> None:
    """Lot MG, the consultant's ruling of 17/11: the PAC is one search, so it has one bound and never the second the
    margin needs. A PAC plan stopped at its limit with a positive first-stage gap is «not proven», with no margin; its own
    gap stays in the stage evidence (EUR², `fixed_l2`)."""
    from backend.app.schemas.pac_allocator.results import PAC_PLAN_INPUT_ADAPTER  # noqa: PLC0415
    from backend.app.services.pac_allocator.normalize import normalize_pac_plan  # noqa: PLC0415
    from backend.test_scripts.test_services import _pac_reference_values as reference  # noqa: PLC0415

    scenario = normalize_pac_plan(PAC_PLAN_INPUT_ADAPTER.validate_python(reference.CASES["m-1x2"]())).normalized
    stopped = []
    for budget in (0.01, 0.02, 0.03, 0.05, 0.08):
        result = planner.plan_exact_scenario(scenario, solver_time_budget_seconds=budget).result
        first = result.solver_evidence.stages[0]
        if result.result_state == "ready_incumbent" and result.proof.kind == "not_proven" and first.absolute_gap not in (None, "0"):
            stopped.append(result)
    assert stopped, "PREMISE: at some short budget the PAC stops with a plan and a first-stage gap (measured: 0.02 s)"
    assert all(result.proof.margin is None for result in stopped)


def test_a_proven_plan_carries_no_margin() -> None:
    proven = planner.plan_exact_scenario(cases.t4(), solver_time_budget_seconds=5, seeds=(1, 2, 3)).result
    assert (proven.proof.kind, getattr(proven.proof, "margin", None)) == ("optimal_proven", None)


def test_the_seeded_runs_line_carries_no_amount() -> None:
    """Lot LOGS of project 67 (the coordinator's ruling on the log rule): the «Rebalancer seeded runs» line names each run's
    seed, origin, state, seconds and failure, never an amount of the plan. A run's value and bound, and the margin, are
    money of the user's portfolio, which the UI masks as personal. ``refused`` (R1-A): the run held only a plan the exact
    replay refuses, answered «no plan»."""
    from structlog.testing import capture_logs  # noqa: PLC0415 — beside its only use

    with capture_logs() as lines:
        planner.plan_exact_scenario(cases.t4(), solver_time_budget_seconds=5, seeds=(1, 2, 3))

    (line,) = [line for line in lines if line["event"] == "Rebalancer seeded runs"]
    assert set(line) == {"event", "log_level", "runs", "state", "chosen", "downgrade"}
    assert [set(run) for run in line["runs"]] == [{"seed", "origin", "closed", "infeasible", "refused", "seconds", "failure"}] * 3
    assert [run["seed"] for run in line["runs"]] == [1, 2, 3]
    assert [run["refused"] for run in line["runs"]] == [False] * 3


def test_three_runs_holding_only_a_refused_plan_answer_no_plan(monkeypatch) -> None:
    """R1-A of project 67 (the consultant's answer 2): a run whose search ended holding only a plan the exact replay
    refuses votes «no plan», never «failed», and passes no lower bound. Three such runs: «no plan» (before: no run could
    be published, ``SeededRunsFailedError``, «execution_failed»); the merge's line carries each run as ``refused``."""
    from structlog.testing import capture_logs  # noqa: PLC0415 — beside its only use

    from backend.test_scripts.test_services.test_pac_planner_cash_rule import _held_refused_search, _short_case  # noqa: PLC0415

    scenario, _product, quanta = _short_case("rebalancer")
    _held_refused_search(monkeypatch, stage_one="unfinished", quanta=quanta)
    with capture_logs() as lines:
        result = planner.plan_exact_scenario(scenario, solver_time_budget_seconds=5, seeds=(1, 2, 3)).result
    assert (result.result_state, result.proof.kind) == ("ready_no_incumbent", "not_proven")
    (line,) = [line for line in lines if line["event"] == "Rebalancer seeded runs"]
    assert [(run["refused"], run["failure"], run["origin"]) for run in line["runs"]] == [(True, None, "none")] * 3


# ---------------------------------------------------------------------------- the planner, three runs in processes


def _settings(result) -> list[dict]:
    return [{setting.name: setting.value for setting in stage.settings} for stage in result.solver_evidence.stages]


def test_three_seeded_runs_of_t4_are_proven_with_the_chosen_seed_on_record() -> None:
    """T4 closes in milliseconds on every seed: three closed runs agree, the plan is proven, and every stage of its
    evidence records the seed of the run published (the lowest, on a tie)."""
    result = planner.plan_exact_scenario(cases.t4(), solver_time_budget_seconds=5, seeds=(31, 17, 23)).result
    assert (result.result_state, result.proof.kind) == ("ready_incumbent", "optimal_proven")
    assert {settings.get("randomization/randomseedshift") for settings in _settings(result)} == {"17"}


def _two_stages(seed: int, progress, budget=None) -> int:
    """A search of two named stages, 0.4 s each: what a search reports, in miniature."""
    if progress is not None:
        progress("search", step=1, total=2)
    time.sleep(0.4)
    if progress is not None:
        progress("search", step=2, total=2)
    time.sleep(0.4)
    return seed


@pytest.mark.parametrize("cpus", [1, 2, 3])
def test_every_turn_reports_its_search_so_the_stream_is_never_silent_long(monkeypatch, cpus: int) -> None:
    """TURNI step 4d (the coordinator's merge condition, 21/11): the Tool's stream forwards a progress line only when it is
    new, so later turns repeating stages already reported were silent, for minutes on one CPU, which a reverse proxy can cut
    (Nginx: 60 s). Each turn now reports its stages as steps of the whole: turn × stages + stage, of turns × stages. Every
    line is new, the steps only go up, and no gap between two lines exceeds one search's stage plus a margin. With one turn
    (three CPUs) the steps are today's."""
    monkeypatch.setattr(seed_runs, "usable_cpus", lambda: cpus)
    heard: list[tuple[float, int, int]] = []

    def listen(phase: str, step: int | None = None, total: int | None = None) -> None:
        assert phase == "search"
        heard.append((time.monotonic(), step, total))

    started = time.monotonic()
    seed_runs.run_seeds(_two_stages, seeds=(1, 2, 3), time_budget_seconds=5, window_seconds=15, progress=listen)
    turns = -(-3 // cpus)
    assert [(step, total) for _at, step, total in heard] == [(step, 2 * turns) for step in range(1, 2 * turns + 1)]
    instants = [started, *(at for at, _step, _total in heard)]
    assert max(later - earlier for earlier, later in zip(instants, instants[1:], strict=False)) < 0.4 + 0.5, "no long silence"


def test_searches_that_close_early_wait_no_longer_with_turns(monkeypatch) -> None:
    """TURNI «done when» 3: a request whose searches close early lasts as today. The window of three turns only lets a
    search use its whole limit; it never makes the others wait for it."""
    monkeypatch.setattr(seed_runs, "usable_cpus", lambda: 1)
    started = time.monotonic()
    runs = seed_runs.run_seeds(_echo, seeds=(1, 2, 3), time_budget_seconds=30, window_seconds=100)
    assert [run.result for run in runs] == [10, 20, 30]
    assert time.monotonic() - started < 5, "three quick searches, one CPU: done in moments, not in their limits"


def test_soft_deadline_does_not_stop_the_last_turn(monkeypatch) -> None:
    """TURNI step 4 (the plan's test): on one usable CPU, the three searches go in three turns inside the Tool's soft
    deadline, as the rule of limits sets it. The rule takes its numbers as arguments, so the turns are short here: searches
    of 1 s that each answer 0.25 s late (inside the runs' own grace), a grace of 1 s between turns, 1 s past the window.
    The third search starts at about 2.5 s with 2.5 s of the 5 s window left, so it keeps its whole limit; the last turn
    ends at about 3.75 s, and the soft deadline is at 6 s. The planner's checkpoint stops nothing."""
    monkeypatch.setattr(seed_runs, "usable_cpus", lambda: 1)
    policy = pac_plugin.plan_policy(3, run_limit_ms=1_000, grace_ms=1_000, past_window_ms=1_000)
    started = time.monotonic()
    context = ToolExecutionContext(execution_id="turns", soft_deadline=started + policy.soft_timeout_ms / 1000, hard_deadline=started + policy.job_timeout_ms / 1000, cancelled=lambda: False)

    def a_little_late(seed: int, progress, budget=None):
        time.sleep(1.25)
        return (seed, budget)

    runs = seed_runs.run_seeds(a_little_late, seeds=(1, 2, 3), time_budget_seconds=1.0, window_seconds=policy.engine_timeout_ms / 1000, checkpoint=context.checkpoint)
    assert [run.result for run in runs] == [(1, 1.0), (2, 1.0), (3, 1.0)], "every turn ran, each search with its whole limit"


@pytest.mark.parametrize(("window", "expected"), [(None, None), (15.0, 15.0)])
def test_the_planner_hands_the_runs_their_limit_and_the_whole_window(monkeypatch, window, expected) -> None:
    """TURNI step 1: the planner passes both numbers to the runs, the window as the caller gives it (None until the Tool
    passes one, step 4), and still publishes a proven T4."""
    seen = []
    real = planner.run_seeds

    def spy(task, **kwargs):
        seen.append((kwargs["time_budget_seconds"], kwargs["window_seconds"]))
        return real(task, **kwargs)

    monkeypatch.setattr(planner, "run_seeds", spy)
    result = planner.plan_exact_scenario(cases.t4(), solver_time_budget_seconds=5, solver_window_seconds=window, seeds=(31, 17, 23)).result
    assert seen == [(5, expected)]
    assert (result.result_state, result.proof.kind) == ("ready_incumbent", "optimal_proven")


@pytest.mark.parametrize(("window", "whole"), [(15.0, True), (None, False)], ids=["a-window-of-three-turns", "no-window"])
def test_the_published_time_budget_is_the_time_the_run_was_given(monkeypatch, window, whole) -> None:
    """TURNI step 2, check 7 (the coordinator's rule of 21/11): the evidence publishes the time the run was really given.
    On one usable CPU the published run of T4 is the one started last (the lowest seed, 17, chosen on a tie). With a window
    of three turns it was given its whole limit, and every stage says 5 s; with no window it had the time left, a little
    less, and every stage says that."""
    monkeypatch.setattr(seed_runs, "usable_cpus", lambda: 1)
    # The budget the scheduler gave each run, as it records it (``_Entry.budget``).
    given: dict[int, float] = {}
    real_entry = seed_runs._Entry

    def entry(**fields):
        given[fields["seed"]] = fields["budget"]
        return real_entry(**fields)

    monkeypatch.setattr(seed_runs, "_Entry", entry)
    result = planner.plan_exact_scenario(cases.t4(), solver_time_budget_seconds=5, solver_window_seconds=window, seeds=(31, 23, 17)).result
    assert (result.result_state, result.proof.kind) == ("ready_incumbent", "optimal_proven")
    assert {settings.get("randomization/randomseedshift") for settings in _settings(result)} == {"17"}, "the run started last is published"
    # Every stage of the published run says exactly the time that run was given, formatted as the solver writes it.
    assert {settings.get("time_budget") for settings in _settings(result)} == {f"{given[17]:g}"}
    assert given[17] == 5 if whole else given[17] < 5


def test_a_run_carries_its_first_stage_band_in_the_unit_of_its_value() -> None:
    """«Target first»: SCIP minimizes D/F, the run's value is D, so the stage's band is divided by its scale (1/F) before
    the merge compares it with the value."""
    from backend.app.services.pac_allocator import models as pac_models  # noqa: PLC0415
    from backend.app.services.pac_allocator.compiler import compile_policy_program  # noqa: PLC0415
    from backend.app.services.pac_allocator.evaluation.evaluator import build_exact_policy_view  # noqa: PLC0415

    scenario = cases.t4(target_fidelity=pac_models.ExactTargetFidelity(kind="target_first", distance_weight=None))
    view = build_exact_policy_view(scenario, purpose="primary")
    stage = compile_policy_program(scenario, view).objective_stages[0]
    assert (stage.code, stage.scale < 1, stage.band > 0) == ("target_distance", True, True)
    outcome = planner._single_run(scenario, view, (), None, 5, planner._rebalancer_product(None), None, seed=1)
    assert (outcome.origin, outcome.band) == ("prudent", Fraction(stage.band) / stage.scale)


def test_a_proof_no_second_run_confirms_is_downgraded_with_its_reason(monkeypatch) -> None:
    """Two of the three runs fail (forked children inherit the patch): the third proved T4 by itself, which no second run
    confirms. Published, ``not_proven``, with the new reason; the plan is the run's own."""
    real = planner._single_run

    def two_fail(scenario, view, issues, checkpoint, budget, product, progress, *, seed=None):
        if seed in (2, 3):
            raise RuntimeError("a run that fails")
        return real(scenario, view, issues, checkpoint, budget, product, progress, seed=seed)

    monkeypatch.setattr(planner, "_single_run", two_fail)
    result = planner.plan_exact_scenario(cases.t4(), solver_time_budget_seconds=5, seeds=(1, 2, 3)).result
    assert (result.result_state, result.proof.kind, result.proof.reason_code) == ("ready_incumbent", "not_proven", PROOF_NOT_CONFIRMED_REASON)


def _impossible_y():
    """Case Y with its cash held between 0.01 and 0.01 EUR: no plan ends there (the ZB-c grid's «min=max=0.01»)."""
    from backend.app.services.pac_allocator import models as pac_models  # noqa: PLC0415

    R = cases.R
    entry = pac_models.ExactCashEntry(broker_id=cases.BROKER, currency="EUR", minimum=pac_models.ExactLimit(kind="amount", value=R(1, 100)), maximum=pac_models.ExactLimit(kind="amount", value=R(1, 100)), weight=R(0))
    return cases.scenario("around-y", holdings={"asset:b": R(480), "asset:c": R(480)}, cash=R(2999, 100), weights={"asset:b": cases.HALF, "asset:c": cases.HALF}, prices={"asset:b": R(1999, 200), "asset:c": R(1999, 200)}, whole_units=frozenset({"asset:b", "asset:c"}), cash_entries=(entry,))


@pytest.mark.parametrize("second", ["real", "no-time"])
def test_one_cpu_a_late_impossible_and_a_second_run_with_almost_no_time_is_never_a_failure(monkeypatch, second: str) -> None:
    """Lot SEEDS-c, the consultant's test: one usable CPU, the first run answers «impossible» after the limit, so the
    second starts with almost no time. It confirms («impossible, proven») or stops at its limit («no plan found»): either
    way the request answers. With a second run given no time at all, exactly «no plan found», from that run."""
    monkeypatch.setattr(seed_runs, "usable_cpus", lambda: 1)
    real = planner._single_run

    def late_first(scenario, view, issues, checkpoint, budget, product, progress, *, seed=None):
        if seed == 1:
            outcome = real(scenario, view, issues, checkpoint, budget, product, progress, seed=seed)
            time.sleep(budget + 0.1)
            return outcome
        return real(scenario, view, issues, checkpoint, 0.0 if second == "no-time" else budget, product, progress, seed=seed)

    monkeypatch.setattr(planner, "_single_run", late_first)
    result = planner.plan_exact_scenario(_impossible_y(), solver_time_budget_seconds=0.5, seeds=(1, 2, 3)).result
    if second == "no-time":
        assert (result.result_state, result.proof.kind) == ("ready_no_incumbent", "not_proven")
    else:
        assert result.result_state in {"ready_infeasible", "ready_no_incumbent"}


def test_three_failed_runs_fail_the_request(monkeypatch) -> None:
    def failing(*args, **kwargs):
        raise RuntimeError("a run that fails")

    monkeypatch.setattr(planner, "_single_run", failing)
    with pytest.raises(planner.SeededRunsFailedError):
        planner.plan_exact_scenario(cases.t4(), solver_time_budget_seconds=5, seeds=(1, 2, 3))


@pytest.mark.parametrize(
    ("raw", "seeds"),
    [
        pytest.param("11,22,33", (11, 22, 33), id="a-list"),
        pytest.param(" 7 ", (7,), id="one-seed"),
        pytest.param("single", (), id="single: SCIP's own seed"),
        pytest.param("", None, id="blank"),
        pytest.param("1,1,2", None, id="repeated"),
        pytest.param("1,x", None, id="not-a-number"),
        pytest.param("-1", None, id="below-zero"),
        pytest.param(str(2**31 - 1), None, id="above-scip-s-range"),
    ],
)
def test_the_test_configuration_fixes_the_seeds_in_test_mode_only(monkeypatch, raw: str, seeds) -> None:
    monkeypatch.setenv("LIBREFOLIO_PLANNER_SEEDS", raw)
    monkeypatch.setattr(planner_config, "is_test_mode", lambda: True)
    assert planner_fixed_seeds() == seeds
    monkeypatch.setattr(planner_config, "is_test_mode", lambda: False)
    assert planner_fixed_seeds() is None, "outside test mode the seeds are always random"


def test_without_a_test_configuration_each_request_draws_three_fresh_seeds_and_runs_them(monkeypatch) -> None:
    """The production path: no fixed seeds, so three fresh random ones per request, run in three processes; the published
    plan records one of them."""
    monkeypatch.setattr(planner_config, "planner_fixed_seeds", lambda: None)
    heard: list[tuple[int, ...]] = []
    real = planner.run_seeds

    def spy(task, *, seeds, **kwargs):
        heard.append(seeds)
        return real(task, seeds=seeds, **kwargs)

    monkeypatch.setattr(planner, "run_seeds", spy)
    first = planner.plan_exact_scenario(cases.t4(), solver_time_budget_seconds=5).result
    planner.plan_exact_scenario(cases.t4(), solver_time_budget_seconds=5)
    assert [len(set(seeds)) for seeds in heard] == [3, 3] and heard[0] != heard[1]
    assert (first.result_state, first.proof.kind) == ("ready_incumbent", "optimal_proven")
    assert {int(settings["randomization/randomseedshift"]) for settings in _settings(first)} <= set(heard[0])


def test_the_pac_stays_one_run_with_scip_s_own_seed() -> None:
    """The developer's rule is the Rebalancer's: the PAC plans once, and no seed is set or published, whatever the caller
    passes; the Rebalancer takes the caller's seeds."""
    assert planner._seeds_for(cases.t4(), (1, 2, 3)) == (1, 2, 3)
    from backend.app.schemas.pac_allocator.results import PAC_PLAN_INPUT_ADAPTER  # noqa: PLC0415
    from backend.app.services.pac_allocator.normalize import normalize_pac_plan  # noqa: PLC0415
    from backend.test_scripts.test_services import _pac_reference_values as reference  # noqa: PLC0415

    scenario = normalize_pac_plan(PAC_PLAN_INPUT_ADAPTER.validate_python(reference.CASES["r-3x3"]())).normalized
    assert planner._seeds_for(scenario, (1, 2, 3)) == ()


# ---------------------------------------------------------------------------- through the Tool


def _through_the_tool(request: dict) -> dict:
    """The worker's own execution of a Rebalancer request, in this process, with the real registry definition: the frame
    the platform sends back."""
    import json  # noqa: PLC0415

    from backend.app.services.tools import worker as worker_module  # noqa: PLC0415
    from backend.app.services.tools.registry import ToolPluginRegistry  # noqa: PLC0415

    descriptor = ToolPluginRegistry.get_definition("portfolio_rebalancer").descriptor
    now = time.monotonic()
    job = worker_module.ToolWorkerJob(
        execution_id="seeds-b-" + "0" * 24,
        tool_code="portfolio_rebalancer",
        contract_version=descriptor.contract_version,
        implementation_version=descriptor.implementation_version,
        schema_fingerprint=descriptor.schema_fingerprint,
        parameters=json.dumps(request).encode(),
        soft_deadline=now + 30,
        hard_deadline=now + 40,
        max_parameter_bytes=1_000_000,
        max_result_bytes=10_000_000,
        max_json_depth=64,
        engine_timeout_ms=5_000,
    )

    class NeverCancelled:
        def is_set(self) -> bool:
            return False

    return worker_module._execute(job, NeverCancelled(), ToolPluginRegistry)


def test_three_failed_runs_reach_the_user_as_a_failure_they_may_retry(monkeypatch) -> None:
    """Lot SEEDS-b: no run answered (three crashes or three runs past the deadline). Through the Tool's worker, the request
    ends `execution_failed`, retryable (three processes failing at once is the platform's trouble, not the request's: the
    user sees «Retry» beside «Edit configuration»), and the failure is logged once with its class, never its amounts."""
    from backend.test_scripts.test_services import _reb_small_requests as requests  # noqa: PLC0415

    def failing(*args, **kwargs):
        raise RuntimeError("a run that fails")

    monkeypatch.setattr(planner, "_single_run", failing)
    monkeypatch.setattr(planner_config, "planner_fixed_seeds", lambda: (1, 2, 3))
    frame = _through_the_tool(requests.t4())
    assert (frame["status"], frame["error"]["code"], frame["error"]["retryable"]) == ("error", "execution_failed", True)


def test_a_lone_impossible_with_two_failed_runs_is_a_failure_they_may_retry(monkeypatch) -> None:
    """Lot SEEDS-b, the consultant's corner: one run proves the request impossible and the other two fail. «Impossible,
    proven» needs two runs, and the contract refuses «no plan» built from an infeasible run
    (`results._validate_solver_status_proof`), so the request fails, retryable, through the Tool."""
    from copy import deepcopy  # noqa: PLC0415

    from backend.test_scripts.test_services import _reb_small_requests as requests  # noqa: PLC0415

    # Case Y with its cash held between 0.01 and 0.01 EUR: no plan ends there (the ZB-c grid's «min=max=0.01»).
    request = requests.y_top_up()
    entry = request["target_weights"][-1]
    cent = deepcopy(entry["maximum"])
    cent["amount"]["amount"] = "0.01"
    entry["minimum"], entry["maximum"] = cent, deepcopy(cent)
    real = planner._single_run

    def one_answers(scenario, view, issues, checkpoint, budget, product, progress, *, seed=None):
        if seed != 1:
            raise RuntimeError("a run that fails")
        return real(scenario, view, issues, checkpoint, budget, product, progress, seed=seed)

    monkeypatch.setattr(planner, "_single_run", one_answers)
    monkeypatch.setattr(planner_config, "planner_fixed_seeds", lambda: (1, 2, 3))
    # The runs are forked: what seed 1 finds is read here, by planning with it alone once.
    from backend.app.schemas.pac_allocator.preview import REBALANCER_TOOL_INPUT_ADAPTER  # noqa: PLC0415

    alone = planner.plan_rebalancing(REBALANCER_TOOL_INPUT_ADAPTER.validate_python(request), solver_time_budget_seconds=5, seeds=(1,))
    assert alone.result_state == "ready_infeasible", "PREMISE: the request is proven impossible by one run"
    frame = _through_the_tool(request)
    assert (frame["status"], frame["error"]["code"], frame["error"]["retryable"]) == ("error", "execution_failed", True)
