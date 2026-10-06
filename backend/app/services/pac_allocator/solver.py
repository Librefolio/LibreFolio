"""Lexicographic SCIP search adapter for the PAC/Rebalancer planner (Step 3, Stage 3).

Takes a ``CompiledProgram`` from ``compiler.py`` and runs the cascade
``fixed_l2 -> shortfall -> route_priority -> explicit_cost ->
active_order_rows -> canonical tie-breaks`` as a genuine lexicographic
search: solve stage *k*, freeze its optimum as a hard constraint, then
solve stage *k+1* on that face. The stage order is whatever
``compiler.build_objective_cascade`` produced from the view's own
``ordinal`` values — never re-sorted or hardcoded here.

**This module never decides anything about proof.** It returns a candidate
plus the solver's own, floating facts — per-stage statuses, bounds and gaps.
Feasibility and every published number come from ``evaluate_exact_candidate``
replay, and whether SCIP's statuses amount to a proof — ``optimal_proven``
when every stage closed at the optimum, ``infeasibility_proven`` when the
first stage closed infeasible (D-X1) — is ``proof.py``'s decision alone. That
separation is why ``SolverRunResult.outcome`` uses report vocabulary
(``reported_infeasible``, never ``infeasibility_proven``).

The search does replay its own candidates in exact arithmetic, for three
narrow jobs that need true values while it is still running. None of them
is a proof, and the planner still replays the returned candidate itself:

* **A pin never sits below the exact value.** A stage is frozen at the
  larger of SCIP's value and the exact value of the best plan so far. SCIP's
  float value can sit a hair *below* the true one, and a pin there cuts the
  best plan out of every later stage.
* **A limit does not end the search.** Stage 1 holds back a reserve
  (``stage_one_reserve_seconds``). When a stage stops on a limit with a plan
  in hand, that plan is pinned and the later stages still run inside the
  pins, each reported ``unfinished`` on the ``incumbent_face``. A plan they
  find replaces the best one only if it is at least as good, stage by stage
  in cascade order, in exact arithmetic. When stage 1 stops on the clock
  with no plan at all, the reserve pays for one more attempt at stage 1.
* **A contradiction is flagged.** At the end, the exact value of the
  returned candidate is checked against the bounds SCIP reported for every
  finished stage. A disagreement beyond SCIP's tolerance sets ``anomaly``,
  and ``proof.py`` then refuses to call the plan optimal.

Cancellation (Step3 §16.4 risk 1, measured 2026-09-16): a Python-thread
``interruptSolve()`` did **not** preempt ``optimize()``. The primary guard
is therefore SCIP-native ``limits/time``/``limits/nodes``, re-armed before
every stage with that stage's share of the remaining budget; the hard cancel
remains the Tool executor's process boundary. ``check_budget(checkpoint)`` is
polled only between ``optimize()`` calls — between stages, before the stage-1
retry and inside each exact replay — and is documented here as insufficient
on its own rather than quietly relied upon.

Three empirically-verified PySCIPOpt traps this module is built around
(probed against pyscipopt 6.2.1 / SCIP 10.0, not taken from documentation):

1. ``getVal(var)`` after ``freeTransform()`` silently returns the *previous*
   stage's value instead of raising. Every observation is therefore read
   immediately after its own ``optimize()``, before the next stage's
   ``freeTransform()``.
2. ``getObjVal()`` can return a finite but meaningless number when a stage
   stops on a limit with **zero** solutions (observed: ``134.0`` at
   ``status='timelimit'``, ``getNSols()==0``). ``getNSols() > 0`` is the only
   gate used here for "an incumbent exists".
3. Missing bounds are reported as ``±1e+20`` (``Model.infinity()``), not as
   ``None``/``inf``, so every bound is filtered through ``_finite_or_none``.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from fractions import Fraction
from typing import Literal

from pyscipopt import Model

from backend.app.services.pac_allocator.compiler import CompiledProgram
from backend.app.services.pac_allocator.evaluator import evaluate_exact_candidate
from backend.app.services.pac_allocator.models import (
    CandidateActionVector,
    CandidateDecision,
    Checkpoint,
    check_budget,
)
from backend.app.services.pac_allocator.objectives import ObjectiveStage

__all__ = [
    "DEFAULT_SOLVER_TIME_BUDGET_SECONDS",
    "ENGINE_NAME",
    "STAGE_PIN_RELATIVE_SLACK",
    "SolverRunResult",
    "SolverSetting",
    "SolverStageReport",
    "SolverTolerances",
    "solve_policy_program",
    "stage_one_reserve_seconds",
]

ENGINE_NAME = "SCIP"

# Fallback budget for a caller with no engine window to claim — tests and
# probes. **Not** the product budget: the Tool passes `engine_timeout_ms`
# (30 000 ms as of 2026-09-21) via
# `plan_pac_allocation(solver_time_budget_seconds=…)`, and that is the number
# that governs a user-facing plan.
#
# Historical note, because the value looks arbitrary and its old justification
# was exact but obsolete: 3.5 was tuned by the 2026-09-16 probe inside a **4 s**
# Tool envelope, where a 4 s budget produced a ~4.05-4.08 s wall and left too
# little room under a 5 s hard deadline once serialize/replay/report/cleanup
# were added. That envelope no longer exists — planner v2 raised it to 30 000 ms
# — so the number survives only as a conservative fallback, not as a measured
# optimum for today's system.
DEFAULT_SOLVER_TIME_BUDGET_SECONDS = 3.5

# Not an economic or policy epsilon. A stage pin must never fall below the
# exact value of the plan that produced it, and SCIP's own value is not safe
# for that. Each ``fixed_l2`` row ``residual_sq >= residual**2`` is nonlinear,
# and SCIP accepts it with an ABSOLUTE ``numerics/feastol`` (1e-6, unscaled),
# so the stage value can sit up to that much per target weight below the
# exact one: measured 474.9999988 for an exact 475, on 5 assets with 2
# brokers each. A pin there cuts equally good plans out, and in a
# path-dependent way: the final solution check accepts them, because it
# compares linear rows relatively, while the LP relaxation, which compares
# absolutely, prunes them. Hence the pin is the larger of SCIP's value and the
# exact value of the best plan (``_exact_pin_value``), plus this relative
# slack, which only covers the float rounding of that exact value. A later
# stage can still worsen a pinned one within the solver's tolerances. The
# slack is never applied to a provably integral stage (see
# ``_is_integral_stage``).
STAGE_PIN_RELATIVE_SLACK = 1e-12

# Stage codes whose expression is provably integral: ``route_priority`` sums
# ``int`` route priorities times binaries, ``active_order_rows`` sums binaries,
# and every ``tie:*`` stage is one integer decision variable. These are pinned
# at their exact rounded value, so the lexicographic contract is exact — not
# merely tolerant — for that part of the cascade.
_INTEGRAL_STAGE_CODES = frozenset({"route_priority", "active_order_rows"})
_TIE_STAGE_PREFIX = "tie:"

# A stage that ended on one of these ran out of its allowance rather than
# proving anything; it is always reported ``unfinished``.
_LIMIT_STATUSES = frozenset(
    {
        "timelimit",
        "nodelimit",
        "totalnodelimit",
        "stallnodelimit",
        "gaplimit",
        "sollimit",
        "bestsollimit",
        "memlimit",
        "restartlimit",
        "userinterrupt",
        "interrupted",
        "terminate",
        "unknown",
    }
)

# The share of the budget that stage 1 leaves unused, with a cap. If stage 1
# stops on a limit with a plan, the reserve pays for the later stages, which
# refine that plan inside its pins; if it stops on the clock with no plan at
# all, the reserve pays for one more attempt at stage 1.
#
# Why 3 s at the 30 s product budget (measured 2026-10-06): after a limit,
# the later stages wanted about 3.2 s, while a 5-asset scenario with 2 brokers
# per asset finished stage 1 at 23.5 s. A 6 s reserve left that stage 24 s —
# 0.49 s from losing its proof — and the machine's ordinary load lost it.
# 3 s leaves 27 s. Under 30 s the reserve shrinks with the budget, so a short
# budget is not eaten by it.
_STAGE_ONE_RESERVE_CAP_SECONDS = 3.0
_STAGE_ONE_RESERVE_SHARE = 0.1

# After a limit, each later objective stage gets half of what is left and
# each tie-break stage all of it: there are five objectives, but there can be
# dozens of tie-breaks, each a single integer variable (measured: the 30
# tie-breaks of a 10-asset, 3-broker scenario took 1.85 s together). The floor
# lets SCIP at least re-check the plans it carries over before it stops.
_TAIL_OBJECTIVE_SHARE = 0.5
_TAIL_MINIMUM_SECONDS = 0.05

# How far the exact value of the returned plan may stray from a bound SCIP
# reported before it counts as a contradiction: SCIP's default
# ``numerics/feastol``, which this module never changes, relative to the
# bound with a floor of 1. ``fixed_l2`` sums one squared term per target
# weight, each evaluated in float, so its band widens by one tolerance per
# term. Integral stages are compared exactly against the rounded bounds.
_BOUND_CHECK_TOLERANCE = 1e-6


@dataclass(frozen=True, slots=True)
class SolverSetting:
    """One solver setting actually applied, for the wire evidence block."""

    name: str
    value: str


@dataclass(frozen=True, slots=True)
class SolverTolerances:
    """The tolerances the engine actually ran with, read back from SCIP."""

    feasibility: float
    integrality: float
    absolute_gap: float
    relative_gap: float


@dataclass(frozen=True, slots=True)
class SolverStageReport:
    """Floating facts about one cascade stage, as SCIP reported them.

    Mirrors ``schemas/pac_allocator.SolverStageEvidence`` field for field so
    ``planner_report.py`` can project it without re-deriving anything, but
    stays a plain dataclass: this module must not import wire schemas.
    ``infeasible`` is reserved for SCIP's verdict on the first, still-global
    stage; a later empty face is ``unfinished`` plus an anomaly. A stage that
    runs after a limit is ``unfinished`` on the ``incumbent_face`` too, even
    when SCIP closes it: it closes only inside pins nobody proved.
    """

    stage: str
    objective_code: str
    ordinal: int
    status: Literal["finished", "unfinished", "infeasible"]
    scope: Literal["global", "incumbent_face"]
    sense: Literal["min"]
    primal: float | None
    dual: float | None
    absolute_gap: float | None
    relative_gap: float | None
    scip_status: str
    solving_seconds: float
    nodes: int


@dataclass(frozen=True, slots=True)
class SolverRunResult:
    """What the search found, in the solver's own vocabulary.

    ``outcome`` is never a proof claim; ``proof.py`` alone reads one out of it:

    * ``incumbent`` — a candidate was extracted: the best plan of the cascade
      (``_take_candidate``). It still has to survive
      ``evaluate_exact_candidate`` replay before anyone may publish it.
    * ``reported_infeasible`` — SCIP closed the *first*, still-global stage
      as infeasible: that stage is reported ``infeasible`` and nothing runs
      after it. A later-stage infeasibility is an anomaly of the pins, never
      a scenario verdict (see ``_stop_anomaly``).
    * ``no_incumbent`` — limits were exhausted before any solution existed,
      stage 1's one retry on its reserve included (``_run_stage``).

    ``anomaly`` keeps the first fact that contradicts the search: a later
    face that came back empty, an unexpected SCIP status, a plan that failed
    its exact replay, or an exact value outside the bounds SCIP reported for
    a finished stage. With an anomaly, ``proof.py`` never concludes
    ``optimal_proven``.

    ``exact_replay_required`` exists purely so a caller cannot forget: it is
    always ``True``.
    """

    view_id: str
    outcome: Literal["incumbent", "reported_infeasible", "no_incumbent"]
    candidate: CandidateActionVector | None
    stages: tuple[SolverStageReport, ...]
    engine: str
    version: str
    settings: tuple[SolverSetting, ...]
    tolerances: SolverTolerances
    wall_seconds: float
    finished_stage_count: int
    anomaly: str | None
    exact_replay_required: Literal[True] = True


def _is_integral_stage(stage: ObjectiveStage) -> bool:
    return stage.code in _INTEGRAL_STAGE_CODES or stage.code.startswith(_TIE_STAGE_PREFIX)


def _objective_code(stage: ObjectiveStage) -> str:
    """The wire ``ObjectiveCode`` a stage reports under.

    Tie-break stages are not wire objectives — they carry the decision id
    instead, and ``planner_report.build_solver_evidence`` excludes them from
    ``ReportedFloatingSolverEvidence.stages`` (which admits only real
    ``ObjectiveCode`` values).
    """
    return stage.code


def _finite_or_none(model: Model, value: float) -> float | None:
    """SCIP reports a missing bound as ``±1e+20``, never as ``None``."""
    if value is None:
        return None
    if model.isInfinity(value) or model.isInfinity(-value):
        return None
    return float(value)


def _read_tolerances(model: Model) -> SolverTolerances:
    return SolverTolerances(
        feasibility=float(model.getParam("numerics/feastol")),
        integrality=float(model.getParam("numerics/epsilon")),
        absolute_gap=float(model.getParam("limits/absgap")),
        relative_gap=float(model.getParam("limits/gap")),
    )


def _extract_candidate(model: Model, program: CompiledProgram, sequence: int) -> CandidateActionVector:
    """Read the incumbent's decision values *now*, before any
    ``freeTransform()`` makes ``getVal`` silently stale (trap 1).

    Values are rounded because SCIP returns integer variables within
    ``numerics/epsilon`` of an integer, not exactly on it. No clamping to the
    declared bounds is applied on purpose: if a rounded value ever escaped
    its own box, that is a real anomaly and
    ``evaluate_exact_candidate`` must be allowed to say so loudly rather than
    have it silently repaired here.
    """
    return CandidateActionVector(
        view_id=program.view.view_id,
        candidate_id=f"solver:{program.view.view_id}:{sequence}",
        decisions=tuple(CandidateDecision(decision_id=access.decision_id, quanta=round(model.getVal(program.variables.quanta[access.decision_id]))) for access in program.view.decisions),
    )


def _pin_value(stage: ObjectiveStage, value: float) -> float:
    """The pin of ``stage`` from SCIP's value alone: the fallback of ``_next_pin``.

    Used only when the best plan has no exact values because it failed its
    exact replay — already an anomaly, so that plan is never called optimal.
    Otherwise ``_exact_pin_value`` sets the pin. Integral stages are pinned
    exactly (their expression cannot take a fractional value, so rounding is
    lossless). Continuous stages get ``STAGE_PIN_RELATIVE_SLACK`` — see that
    constant's comment.
    """
    if _is_integral_stage(stage):
        return float(round(value))
    return value + abs(value) * STAGE_PIN_RELATIVE_SLACK


def _unfinished_report(stage: ObjectiveStage, ordinal: int, scope: Literal["global", "incumbent_face"], scip_status: str) -> SolverStageReport:
    """A stage that never ran: no observations at all, rather than zeros."""
    return SolverStageReport(
        stage=stage.code,
        objective_code=_objective_code(stage),
        ordinal=ordinal,
        status="unfinished",
        scope=scope,
        sense="min",
        primal=None,
        dual=None,
        absolute_gap=None,
        relative_gap=None,
        scip_status=scip_status,
        solving_seconds=0.0,
        nodes=0,
    )


def _apply_engine_settings(model: Model, time_budget_seconds: float, node_limit: int | None) -> list[SolverSetting]:
    """Apply the settings that survive the whole run, and report only those.

    ``limits/time`` is deliberately **not** listed here: it is re-armed before
    every stage with that stage's own share of the remaining budget
    (`_stage_time_limit`), so a single value reported at the top would
    describe a configuration that was never executed. The overall budget is
    reported separately as ``time_budget``.
    """
    settings = [SolverSetting(name="time_budget", value=f"{time_budget_seconds:g}")]
    if node_limit is not None:
        model.setParam("limits/nodes", node_limit)
        settings.append(SolverSetting(name="limits/nodes", value=str(node_limit)))
    return settings


def solve_policy_program(
    program: CompiledProgram,
    *,
    time_budget_seconds: float = DEFAULT_SOLVER_TIME_BUDGET_SECONDS,
    node_limit: int | None = None,
    checkpoint: Checkpoint | None = None,
) -> SolverRunResult:
    """Run the lexicographic cascade over ``program`` and return a candidate.

    The returned candidate is a *proposal*: it has not been checked in exact
    arithmetic and must be replayed through ``evaluate_exact_candidate``
    before any of it is published. Never raises on a solver outcome — a
    failed or limited search is data (``outcome``/``anomaly``), not an
    exception.
    """
    model = program.model
    settings = _apply_engine_settings(model, time_budget_seconds, node_limit)
    tolerances = _read_tolerances(model)
    started = time.monotonic()

    reports, candidate, outcome, anomaly = _solve_stages(
        model=model,
        program=program,
        time_budget_seconds=time_budget_seconds,
        started=started,
        checkpoint=checkpoint,
    )

    return SolverRunResult(
        view_id=program.view.view_id,
        outcome=outcome,
        candidate=candidate,
        stages=tuple(reports),
        engine=ENGINE_NAME,
        version=str(model.version()),
        settings=tuple(settings),
        tolerances=tolerances,
        wall_seconds=time.monotonic() - started,
        finished_stage_count=sum(1 for report in reports if report.status == "finished"),
        anomaly=anomaly,
    )


def stage_one_reserve_seconds(budget_seconds: float) -> float:
    """The seconds stage 1 leaves unused out of ``budget_seconds``.

    See ``_STAGE_ONE_RESERVE_CAP_SECONDS`` for why. Never negative: a zero
    or negative budget holds nothing back.
    """
    return max(0.0, min(_STAGE_ONE_RESERVE_CAP_SECONDS, _STAGE_ONE_RESERVE_SHARE * budget_seconds))


@dataclass(frozen=True, slots=True)
class _StageObservation:
    """What SCIP said about one stage, read right after its ``optimize()``."""

    scip_status: str
    has_solution: bool
    primal: float | None
    dual: float | None
    absolute_gap: float | None
    relative_gap: float | None
    solving_seconds: float
    nodes: int


@dataclass(slots=True)
class _Cascade:
    """The state of one run of the cascade, shared by its helpers."""

    program: CompiledProgram
    checkpoint: Checkpoint | None
    reports: list[SolverStageReport]
    best: CandidateActionVector | None = None
    # The exact value of every stage on ``best``, in cascade order. ``None``
    # when there is no best plan yet, or when it failed its exact replay.
    best_values: tuple[Fraction, ...] | None = None
    outcome: Literal["incumbent", "reported_infeasible", "no_incumbent"] = "no_incumbent"
    anomaly: str | None = None
    pending_pin: tuple[ObjectiveStage, float] | None = None
    # True from the first stage that stopped on a limit with a plan in hand.
    in_tail: bool = False

    def flag(self, anomaly: str) -> None:
        """Keep the first anomaly: every later fact descends from it."""
        if self.anomaly is None:
            self.anomaly = anomaly


def _observe(model: Model) -> _StageObservation:
    """Read a stage before the next ``freeTransform()`` (trap 1), gated on ``getNSols`` (trap 2)."""
    has_solution = model.getNSols() > 0
    primal = _finite_or_none(model, model.getPrimalbound()) if has_solution else None
    dual = _finite_or_none(model, model.getDualbound())
    return _StageObservation(
        scip_status=model.getStatus(),
        has_solution=has_solution,
        primal=primal,
        dual=dual,
        absolute_gap=abs(primal - dual) if primal is not None and dual is not None else None,
        relative_gap=_finite_or_none(model, model.getGap()) if has_solution else None,
        solving_seconds=float(model.getSolvingTime()),
        nodes=int(model.getNNodes()),
    )


def _exact_stage_values(cascade: _Cascade, candidate: CandidateActionVector) -> tuple[Fraction, ...] | None:
    """The exact value of every stage's expression on ``candidate``, in cascade order.

    ``None`` when the candidate fails its exact replay *as a candidate* —
    outside its own box or its view — so it has no values to pin or compare
    with. A plan that merely breaks a rule is still valid here: the planner
    decides later whether rounding explains it. A named stage takes its
    objective's exact value; a tie-break stage is the quanta of one decision,
    which is all its expression is.
    """
    program = cascade.program
    evaluation = evaluate_exact_candidate(program.scenario, program.view, candidate, checkpoint=cascade.checkpoint)
    if not evaluation.candidate_valid:
        return None
    value_by_ref = {item.ref_id: item.value for item in evaluation.objectives}
    value_by_code = {ref.code: value_by_ref[ref.ref_id] for ref in program.view.objectives}
    quanta = {decision.decision_id: decision.quanta for decision in candidate.decisions}
    values = []
    for stage in program.objective_stages:
        if stage.code.startswith(_TIE_STAGE_PREFIX):
            values.append(Fraction(quanta[stage.code.removeprefix(_TIE_STAGE_PREFIX)]))
        else:
            ratio = value_by_code[stage.code]
            values.append(Fraction(ratio.numerator, ratio.denominator))
    return tuple(values)


def _take_candidate(cascade: _Cascade, candidate: CandidateActionVector, ordinal: int) -> None:
    """Make ``candidate`` the best plan, or keep the current one.

    Up to the first stage stopped by a limit, each stage's plan replaces the
    previous one, as it always has: it was found inside every earlier pin.
    After that, a plan replaces the best one only if its exact stage values
    are no worse, compared one stage at a time in cascade order; a plan that
    fails its exact replay never does.
    """
    values = _exact_stage_values(cascade, candidate)
    if values is None:
        cascade.flag(f"the plan found at stage ordinal {ordinal} failed its exact replay")
        if cascade.in_tail:
            return
    elif cascade.in_tail and cascade.best_values is not None and values > cascade.best_values:
        return
    cascade.best = candidate
    cascade.best_values = values
    cascade.outcome = "incumbent"


def _exact_pin_value(stage: ObjectiveStage, primal: float | None, exact: Fraction) -> float:
    """The pin of ``stage``: ``_pin_value``, but never below the best plan's exact value.

    ``primal`` is SCIP's value for the stage, or ``None`` when the stage found
    no plan of its own. Integral stages stay exact; continuous ones keep the
    ``STAGE_PIN_RELATIVE_SLACK`` on top.
    """
    if _is_integral_stage(stage):
        pinned = math.ceil(exact) if primal is None else max(round(primal), math.ceil(exact))
        return float(pinned)
    anchor = float(exact) if primal is None else max(primal, float(exact))
    return anchor + abs(anchor) * STAGE_PIN_RELATIVE_SLACK


def _next_pin(cascade: _Cascade, stage: ObjectiveStage, index: int, primal: float | None) -> float:
    if cascade.best_values is None:
        # The best plan failed its exact replay, which is already an anomaly,
        # and only a finished stage gets here then: pin on SCIP's value, as before.
        return _pin_value(stage, primal)
    return _exact_pin_value(stage, primal, cascade.best_values[index])


def _stage_time_limit(cascade: _Cascade, stage: ObjectiveStage, index: int, remaining: float, reserve: float) -> float:
    if cascade.in_tail:
        share = remaining if stage.code.startswith(_TIE_STAGE_PREFIX) else remaining * _TAIL_OBJECTIVE_SHARE
        return max(share, _TAIL_MINIMUM_SECONDS)
    if index == 0 and remaining > reserve:
        return remaining - reserve
    # While stages finish, each gets everything that is left, as before.
    return remaining


def _run_stage(model: Model, stage: ObjectiveStage, limit: float, retry_limit: float | None, checkpoint: Checkpoint | None) -> _StageObservation:
    """Optimize one stage, and retry it once up to ``retry_limit`` if the clock stopped it with no plan.

    The retry is stage 1 spending its reserve. ``limits/time`` is measured
    on SCIP's solving clock, which starts again only when the problem is
    transformed again; nothing frees it in between, so the second
    ``optimize()`` carries on the same search, with the reserve as extra time.
    """
    model.setParam("limits/time", limit)
    model.setObjective(stage.expression, "minimize")
    model.optimize()
    observation = _observe(model)
    if retry_limit is not None and observation.scip_status == "timelimit" and not observation.has_solution:
        check_budget(checkpoint)
        model.setParam("limits/time", retry_limit)
        model.optimize()
        observation = _observe(model)
    return observation


def _scope(index: int) -> Literal["global", "incumbent_face"]:
    return "global" if index == 0 else "incumbent_face"


def _stage_report(stage: ObjectiveStage, index: int, observation: _StageObservation, status: Literal["finished", "unfinished", "infeasible"]) -> SolverStageReport:
    return SolverStageReport(
        stage=stage.code,
        objective_code=_objective_code(stage),
        ordinal=index + 1,
        status=status,
        scope=_scope(index),
        sense="min",
        primal=observation.primal,
        dual=observation.dual,
        absolute_gap=observation.absolute_gap,
        relative_gap=observation.relative_gap,
        scip_status=observation.scip_status,
        solving_seconds=observation.solving_seconds,
        nodes=observation.nodes,
    )


def _not_reached(stages: tuple[ObjectiveStage, ...], after_index: int) -> list[SolverStageReport]:
    return [_unfinished_report(later, later_index + 1, "incumbent_face", "not_reached") for later_index, later in enumerate(stages[after_index + 1 :], start=after_index + 1)]


def _stop_anomaly(cascade: _Cascade, stage: ObjectiveStage, index: int, scip_status: str) -> str | None:
    """Why an unfinished stage must end the cascade, or ``None`` when it may go on."""
    ordinal = index + 1
    if scip_status == "infeasible":
        # The face carved out by earlier pins came back empty. That is a
        # pin/tolerance anomaly, never a scenario verdict: the best plan so
        # far is still a valid candidate.
        previous = cascade.program.objective_stages[index - 1]
        return f"stage {stage.code!r} (ordinal {ordinal}) reported infeasible on a face that stage {previous.code!r} had already satisfied"
    if scip_status in _LIMIT_STATUSES or (cascade.in_tail and scip_status == "optimal"):
        return None
    return f"stage {stage.code!r} (ordinal {ordinal}) ended with unexpected solver status {scip_status!r}"


def _may_go_on(cascade: _Cascade, stage: ObjectiveStage, index: int, scip_status: str) -> bool:
    """Whether the cascade goes on after an unfinished stage, which puts it in the tail."""
    anomaly = _stop_anomaly(cascade, stage, index, scip_status)
    if anomaly is not None:
        cascade.flag(anomaly)
        return False
    if cascade.best_values is None:
        # No plan to refine, or one that failed its exact replay: the
        # cascade ends here, as it did before there was a tail.
        return False
    cascade.in_tail = True
    return True


def _close_stage(cascade: _Cascade, stage: ObjectiveStage, index: int, observation: _StageObservation) -> bool:
    """Report a stage that ran and queue its pin. ``False`` ends the cascade.

    A stage after a limit is never ``finished``: when SCIP closes it, it is
    closed only inside pins that were not proven, so it is reported
    ``unfinished`` on the ``incumbent_face``, with its real observations.
    """
    finished = not cascade.in_tail and observation.scip_status == "optimal" and observation.has_solution
    # Only the first, still-global stage can say anything about the scenario itself.
    verdict = index == 0 and observation.scip_status == "infeasible"
    cascade.reports.append(_stage_report(stage, index, observation, "finished" if finished else "infeasible" if verdict else "unfinished"))
    if verdict:
        # A verdict, not an interruption: no face exists for a later stage
        # to run on, so none is run and none is reported.
        cascade.outcome = "reported_infeasible"
        return False
    if not finished and not _may_go_on(cascade, stage, index, observation.scip_status):
        cascade.reports.extend(_not_reached(cascade.program.objective_stages, index))
        return False
    cascade.pending_pin = (stage, _next_pin(cascade, stage, index, observation.primal))
    return True


def _outside_reported_bounds(report: SolverStageReport, value: Fraction, weight_count: int) -> bool:
    if report.objective_code in _INTEGRAL_STAGE_CODES:
        below = report.dual is not None and value < math.ceil(report.dual - _BOUND_CHECK_TOLERANCE)
        above = report.primal is not None and value > round(report.primal)
        return below or above
    extra = weight_count * _BOUND_CHECK_TOLERANCE if report.objective_code == "fixed_l2" else 0.0
    below = report.dual is not None and value < Fraction(report.dual) - Fraction(_BOUND_CHECK_TOLERANCE * max(1.0, abs(report.dual)) + extra)
    above = report.primal is not None and value > Fraction(report.primal) + Fraction(_BOUND_CHECK_TOLERANCE * max(1.0, abs(report.primal)) + extra)
    return below or above


def _flag_contradicted_bounds(cascade: _Cascade) -> None:
    """Flag the first finished stage whose bounds the returned plan's exact value contradicts.

    Silent when there is no exact value to check. Tie-break stages are
    skipped: their value is one decision's quanta, read straight off the plan.
    """
    if cascade.best is None or cascade.best_values is None:
        return
    weight_count = len(cascade.program.scenario.target_weights)
    for report in cascade.reports:
        if report.status != "finished" or report.stage.startswith(_TIE_STAGE_PREFIX):
            continue
        if _outside_reported_bounds(report, cascade.best_values[report.ordinal - 1], weight_count):
            cascade.flag(f"stage {report.stage!r} (ordinal {report.ordinal}): the exact value of the returned plan lies outside the bounds the solver reported")
            return


def _solve_stages(
    *,
    model: Model,
    program: CompiledProgram,
    time_budget_seconds: float,
    started: float,
    checkpoint: Checkpoint | None,
) -> tuple[list[SolverStageReport], CandidateActionVector | None, Literal["incumbent", "reported_infeasible", "no_incumbent"], str | None]:
    cascade = _Cascade(program=program, checkpoint=checkpoint, reports=[])
    reserve = stage_one_reserve_seconds(time_budget_seconds)
    stages = program.objective_stages

    for index, stage in enumerate(stages):
        # Cooperative polling happens between stages only; it cannot preempt a
        # running optimize() (module docstring, Step3 §16.4 risk 1).
        check_budget(checkpoint)
        remaining = time_budget_seconds - (time.monotonic() - started)
        if remaining <= 0.0:
            cascade.reports.append(_unfinished_report(stage, index + 1, _scope(index), "budget_exhausted"))
            continue

        if cascade.pending_pin is not None:
            pinned_stage, pinned_value = cascade.pending_pin
            model.freeTransform()
            model.addCons(pinned_stage.expression <= pinned_value, name=f"pin:{pinned_stage.code}")
            cascade.pending_pin = None

        limit = _stage_time_limit(cascade, stage, index, remaining, reserve)
        observation = _run_stage(model, stage, limit, remaining if index == 0 and limit < remaining else None, checkpoint)
        if observation.has_solution:
            _take_candidate(cascade, _extract_candidate(model, program, index + 1), index + 1)
        if not _close_stage(cascade, stage, index, observation):
            break

    _flag_contradicted_bounds(cascade)
    return cascade.reports, cascade.best, cascade.outcome, cascade.anomaly
