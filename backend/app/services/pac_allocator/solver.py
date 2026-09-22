"""Lexicographic SCIP search adapter for the PAC/Rebalancer planner (Step 3, Stage 3).

Takes a ``CompiledProgram`` from ``compiler.py`` and runs the cascade
``fixed_l2 -> shortfall -> route_priority -> explicit_cost ->
active_order_rows -> canonical tie-breaks`` as a genuine lexicographic
search: solve stage *k*, freeze its optimum as a hard constraint, then
solve stage *k+1* on that face. The stage order is whatever
``compiler.build_objective_cascade`` produced from the view's own
``ordinal`` values — never re-sorted or hardcoded here.

**This module never decides anything about proof.** It returns a candidate
plus a pile of explicitly floating, explicitly non-authoritative facts.
Feasibility, every published number, and the lexicographic ranking that
actually counts all come from ``evaluate_exact_candidate`` replay, and any
promotion to ``optimal_proven``/``infeasibility_proven`` is ``proof.py``'s
job via ``oracle.py`` or a deterministic conflict. That separation is why
``SolverRunResult.outcome`` deliberately uses floating vocabulary
(``reported_infeasible``, never ``infeasible``).

Cancellation (Step3 §16.4 risk 1, measured 2026-09-16): a Python-thread
``interruptSolve()`` did **not** preempt ``optimize()``. The primary guard
is therefore SCIP-native ``limits/time``/``limits/nodes``, re-armed with the
remaining budget before every stage; the hard cancel remains the Tool
executor's process boundary. ``check_budget(checkpoint)`` is polled between
stages only, and is documented here as insufficient on its own rather than
quietly relied upon.

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

import time
from dataclasses import dataclass
from typing import Literal

from pyscipopt import Model

from backend.app.services.pac_allocator.compiler import CompiledProgram
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
]

ENGINE_NAME = "SCIP"

# Fallback budget for a caller with no engine window to claim — tests, probes,
# and the exhaustive-oracle path that never reaches here. **Not** the product
# budget: the Tool passes `engine_timeout_ms` (30 000 ms as of 2026-09-21) via
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

# Not an economic or policy epsilon. Its only job is to stop a stage pin from
# being *unsatisfiable by float re-evaluation of the very expression that
# produced the value*: float64 carries ~2.2e-16 relative error, and SCIP's own
# 1e-6 absolute ``numerics/feastol`` stops covering that once a stage value
# exceeds ~1e10 (``fixed_l2`` is money-*squared*, so that is reachable). The
# slack is relative, so it vanishes for small values, and it is never applied
# to a provably integral stage (see ``_is_integral_stage``).
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
    """Non-authoritative floating facts about one cascade stage.

    Mirrors ``schemas/pac_allocator.SolverStageEvidence`` field for field so
    ``proof.py`` can project it without re-deriving anything, but stays a
    plain dataclass: this module must not import wire schemas, and must not
    be able to express a *proven* claim at all.
    """

    stage: str
    objective_code: str
    ordinal: int
    status: Literal["finished", "unfinished"]
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
    """What the search found, in deliberately floating vocabulary.

    ``outcome`` is never a proof claim:

    * ``incumbent`` — a candidate was extracted; it still has to survive
      ``evaluate_exact_candidate`` replay before anyone may publish it.
    * ``reported_infeasible`` — SCIP reported infeasibility on the *first*,
      still-global stage. Only a ``deterministic_conflict`` or the exhaustive
      oracle may ever turn that into ``infeasibility_proven``; a later-stage
      infeasibility is an anomaly, never a scenario verdict (see
      ``_solve_stages``).
    * ``no_incumbent`` — limits were exhausted before any solution existed.

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
    instead, and ``proof.py`` is responsible for excluding them from
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
    """The right-hand side that freezes ``stage`` at its own optimum.

    Integral stages are pinned exactly (their expression cannot take a
    fractional value, so rounding is lossless and the lexicographic contract
    stays exact). Continuous stages get ``STAGE_PIN_RELATIVE_SLACK``, whose
    only purpose is float re-evaluation safety — see that constant's comment.
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
    every stage with that stage's remaining slice (`_solve_stages`), so a single
    value reported at the top would describe a configuration that was never
    executed. The overall budget is reported separately as ``time_budget``.
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


def _solve_stages(
    *,
    model: Model,
    program: CompiledProgram,
    time_budget_seconds: float,
    started: float,
    checkpoint: Checkpoint | None,
) -> tuple[list[SolverStageReport], CandidateActionVector | None, Literal["incumbent", "reported_infeasible", "no_incumbent"], str | None]:
    reports: list[SolverStageReport] = []
    candidate: CandidateActionVector | None = None
    anomaly: str | None = None
    outcome: Literal["incumbent", "reported_infeasible", "no_incumbent"] = "no_incumbent"
    pending_pin: tuple[ObjectiveStage, float] | None = None
    stages = program.objective_stages

    for index, stage in enumerate(stages):
        # Cooperative polling happens between stages only; it cannot preempt a
        # running optimize() (module docstring, Step3 §16.4 risk 1).
        check_budget(checkpoint)
        ordinal = index + 1
        scope: Literal["global", "incumbent_face"] = "global" if index == 0 else "incumbent_face"
        remaining = time_budget_seconds - (time.monotonic() - started)
        if remaining <= 0.0:
            reports.append(_unfinished_report(stage, ordinal, scope, "budget_exhausted"))
            continue

        if pending_pin is not None:
            pinned_stage, pinned_value = pending_pin
            model.freeTransform()
            model.addCons(pinned_stage.expression <= pinned_value, name=f"pin:{pinned_stage.code}")
            pending_pin = None

        model.setParam("limits/time", remaining)
        model.setObjective(stage.expression, "minimize")
        model.optimize()

        # Everything below is read before the next iteration's freeTransform
        # (trap 1) and gated on getNSols (trap 2).
        scip_status = model.getStatus()
        has_solution = model.getNSols() > 0
        primal = _finite_or_none(model, model.getPrimalbound()) if has_solution else None
        dual = _finite_or_none(model, model.getDualbound())
        absolute_gap = abs(primal - dual) if primal is not None and dual is not None else None
        relative_gap = _finite_or_none(model, model.getGap()) if has_solution else None
        solving_seconds = float(model.getSolvingTime())
        nodes = int(model.getNNodes())

        if has_solution:
            candidate = _extract_candidate(model, program, ordinal)
            outcome = "incumbent"

        finished = scip_status == "optimal" and has_solution
        reports.append(
            SolverStageReport(
                stage=stage.code,
                objective_code=_objective_code(stage),
                ordinal=ordinal,
                status="finished" if finished else "unfinished",
                scope=scope,
                sense="min",
                primal=primal,
                dual=dual,
                absolute_gap=absolute_gap,
                relative_gap=relative_gap,
                scip_status=scip_status,
                solving_seconds=solving_seconds,
                nodes=nodes,
            )
        )

        if finished:
            pending_pin = (stage, _pin_value(stage, primal))
            continue

        if scip_status == "infeasible":
            if index == 0:
                # Only the first, still-global stage can say anything about the
                # scenario itself — and even then only as a floating report.
                outcome = "reported_infeasible"
            else:
                # The face carved out by earlier pins came back empty. That is
                # a pin/tolerance anomaly, never a scenario verdict: the
                # previous stage's incumbent is still a valid candidate.
                anomaly = f"stage {stage.code!r} (ordinal {ordinal}) reported infeasible on a face that stage {stages[index - 1].code!r} had already satisfied"
        elif scip_status not in _LIMIT_STATUSES:
            anomaly = f"stage {stage.code!r} (ordinal {ordinal}) ended with unexpected solver status {scip_status!r}"

        reports.extend(_unfinished_report(later, later_index + 1, "incumbent_face", "not_reached") for later_index, later in enumerate(stages[index + 1 :], start=index + 1))
        break

    return reports, candidate, outcome, anomaly
