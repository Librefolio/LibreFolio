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
from backend.app.services.pac_allocator.proof import PROOF_NOT_CONFIRMED_REASON, SeededRunVote, merge_seeded_runs, seeded_runs_agree
from backend.test_scripts.test_services import _reb_small_cases as cases

# ---------------------------------------------------------------------------- the runs


def _echo(seed: int, progress) -> int:
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
    def unreliable(seed: int, progress) -> int:
        if seed == 2:
            raise RuntimeError("a run that fails")
        if seed == 3:
            os._exit(1)
        return seed

    runs = seed_runs.run_seeds(unreliable, seeds=(1, 2, 3), time_budget_seconds=5)
    assert [(run.seed, run.result, run.failure) for run in runs] == [(1, 1, None), (2, None, "RuntimeError"), (3, None, "RunProcessEnded")]


def test_a_run_past_the_deadline_is_stopped_and_has_no_result(monkeypatch) -> None:
    """No wait is unbounded: past the budget and the grace, a run still out is stopped."""
    monkeypatch.setattr(seed_runs, "_GRACE_SECONDS", 0.5)

    def slow(seed: int, progress) -> int:
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

    def endless(seed: int, progress) -> int:
        time.sleep(60)
        return seed

    started = time.monotonic()
    with pytest.raises(Cancelled):
        seed_runs.run_seeds(endless, seeds=(1, 2, 3), time_budget_seconds=60, checkpoint=cancel_on_the_third_wait)
    assert time.monotonic() - started < 10
    assert [process.name for process in multiprocessing.active_children() if process.name.startswith("planner-seed-")] == []


def _niceness(seed: int, progress) -> int:
    return os.nice(0)


@pytest.mark.skipif(not hasattr(os, "nice"), reason="a platform without os.nice runs the three at one priority")
def test_the_second_and_third_runs_run_at_low_priority() -> None:
    """Lot SEEDS-b (the consultant's measured mechanism): the first run keeps the caller's priority, the other two run at
    the lowest (`nice` 19), so on a machine with fewer free CPUs than runs the first is never starved by the others."""
    base = os.nice(0)
    runs = seed_runs.run_seeds(_niceness, seeds=(5, 6, 7), time_budget_seconds=5)
    assert [run.result for run in runs] == [base, 19, 19]


@pytest.mark.skipif(not hasattr(os, "nice"), reason="no priority to change")
def test_runs_in_the_caller_s_process_never_change_its_priority() -> None:
    """A priority lowered in a process cannot be raised again: in process, the runs keep the caller's."""
    base = os.nice(0)
    runs = seed_runs.run_seeds(_niceness, seeds=(5, 6, 7), time_budget_seconds=5, mode="in_process")
    assert [run.result for run in runs] == [base, base, base]
    assert os.nice(0) == base


def test_once_the_first_run_has_answered_the_others_are_stopped_soon_after_the_limit(monkeypatch) -> None:
    """The others are not waited for through the whole grace: once the first has a result, they have the limit and a short
    settle, then they are stopped and count as runs with no result."""
    monkeypatch.setattr(seed_runs, "_GRACE_SECONDS", 30.0)

    def second_never_ends(seed: int, progress) -> int:
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

    def second_just_late(seed: int, progress) -> int:
        if seed == 2:
            time.sleep(0.6)
        return seed

    runs = seed_runs.run_seeds(second_just_late, seeds=(1, 2), time_budget_seconds=0.5)
    assert [(run.seed, run.result, run.failure) for run in runs] == [(1, 1, None), (2, 2, None)]


def test_when_the_first_run_fails_the_others_keep_the_whole_grace(monkeypatch) -> None:
    """With no first answer, the others are what the request has: they are waited for up to the limit and the grace."""
    monkeypatch.setattr(seed_runs, "_GRACE_SECONDS", 30.0)

    def first_fails(seed: int, progress) -> int:
        if seed == 1:
            raise RuntimeError("a run that fails")
        time.sleep(0.5 + seed_runs._SETTLE_SECONDS + 0.5)
        return seed

    runs = seed_runs.run_seeds(first_fails, seeds=(1, 2), time_budget_seconds=0.5)
    assert [(run.seed, run.result, run.failure) for run in runs] == [(1, None, "RuntimeError"), (2, 2, None)]


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


# ---------------------------------------------------------------------------- the planner, three runs in processes


def _settings(result) -> list[dict]:
    return [{setting.name: setting.value for setting in stage.settings} for stage in result.solver_evidence.stages]


def test_three_seeded_runs_of_t4_are_proven_with_the_chosen_seed_on_record() -> None:
    """T4 closes in milliseconds on every seed: three closed runs agree, the plan is proven, and every stage of its
    evidence records the seed of the run published (the lowest, on a tie)."""
    result = planner.plan_exact_scenario(cases.t4(), solver_time_budget_seconds=5, seeds=(31, 17, 23)).result
    assert (result.result_state, result.proof.kind) == ("ready_incumbent", "optimal_proven")
    assert {settings.get("randomization/randomseedshift") for settings in _settings(result)} == {"17"}


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
