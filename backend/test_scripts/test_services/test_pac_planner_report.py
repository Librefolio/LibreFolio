"""Contract tests for the PAC planner wire projection (Step 3, Stage 5a).

``planner_report.py`` re-expresses an already-exact evaluation as the frozen
wire contract in ``schemas/pac_allocator.py``. It computes no economics; its
one piece of arithmetic is the exposure projection, and even there it only
aggregates quantities the solve already decided. These tests lock the
non-obvious properties of that projection — the ones a reader of the code
could plausibly "simplify" away without a failing test to stop them:

* **Exposure closes to exactly one by identity, never by normalisation.** The
  schema validator (``_validate_weight_availability``), not the type union, is
  the specification: with a nonzero denominator every weight must be available
  and the dimension must sum to *exactly* 1; with a zero denominator every
  weight must be unavailable carrying ``zero_final_invested``. The
  uncategorised remainder is published as its own row so real categories keep
  their true weight and the gap becomes a named fact rather than an inferred
  absence.
* **Provenance is deduplicated in canonical order, contained by construction,
  and fails closed on an empty union naming the offending assets.**
* **Tie stages are filtered from solver evidence** because the wire objective
  enum cannot express them — a schema consequence, not a choice.
* **``stop_reason`` is determined by the stage statuses** (an ``infeasible``
  first stage is SCIP's verdict, so it ends a ``completed`` search), and
  cross-section action sequences come from a single shared allocator so they
  are globally unique *and* each section stays internally ascending.
* **FX actions are grouped into one conversion per (Broker, source,
  destination)**, in that canonical order whatever order the engine met the
  pairs in, with exact debit and spread sums and the *posted* credit sum. A
  manual conversion takes the next shared sequence, between funding and
  orders; an automatic one carries none and consumes none.

The headline gate is a genuine end-to-end assembly: a real
``build_exact_policy_view -> compile -> solve -> replay -> conclude -> project``
run whose output is judged by pydantic and the validators, with an
uncategorised asset deliberately present.

These are pure in-process tests (``isolation="pure"``): no server, no
database, no clock, no sleeps, no network. Exact domain values compare with
``==`` on ``ExactRatio``; SCIP floats are never compared exactly. Candidate
and stage counts are read off the live result objects, never hardcoded.
Fixtures are reused from the sibling suites exactly the way they already share
them, with exposure variants built via ``dataclasses.replace``.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from fractions import Fraction

import pytest

from backend.app.schemas.pac_allocator import (
    DeploymentUnavailable,
    OptimalProvenProof,
    PacIncumbentSolution,
    PacPlannerReadyIncumbentResult,
    PlannerFxAction,
    SolverStatusWitness,
    _exact_fraction,
    _validate_weight_availability,
)
from backend.app.services.pac_allocator import models as pac_models
from backend.app.services.pac_allocator import planner_report as PR
from backend.app.services.pac_allocator.compiler import compile_policy_program
from backend.app.services.pac_allocator.evaluator import _fx_debit_key, build_exact_policy_view, evaluate_exact_candidate, exact_decision_id
from backend.app.services.pac_allocator.models import CandidateActionVector, CandidateDecision, ExactExposure
from backend.app.services.pac_allocator.proof import OptimalProvenConclusion, conclude_with_solver
from backend.app.services.pac_allocator.solver import solve_policy_program
from backend.test_scripts.test_services.test_pac_planner_evaluator import (
    ONE,
    PROVENANCE_ID,
    R,
    _asset,
    _broker,
    _capability,
    _cash,
    _fee,
    _fx_rate,
    _order_route,
    _pac_scenario,
    _scenario,
)
from backend.test_scripts.test_services.test_pac_planner_oracle import _coarse_funding_fx_scenario, _two_asset_pac_scenario

# --------------------------------------------------------------------------
# Helpers — real pipeline, exposure variants via dataclasses.replace
# --------------------------------------------------------------------------


def _exposure(dimension: str, category: str, weight: R, *, label: str | None = None, provenance: str = PROVENANCE_ID) -> ExactExposure:
    return ExactExposure(dimension=dimension, category=category, label=label or category, weight=weight, provenance_id=provenance)


def _with_exposures(asset, *exposures: ExactExposure):
    """Attach exposures to a fixture asset, canonically ordered.

    ``ExactAsset`` requires its exposures tuple to be unique and sorted by
    ``(dimension, category)``, so this sorts rather than trusting call order.
    """
    ordered = tuple(sorted(exposures, key=lambda exposure: (exposure.dimension, exposure.category)))
    return replace(asset, exposures=ordered)


def _scenario_with_asset_exposures(exposures_a: tuple[ExactExposure, ...], exposures_b: tuple[ExactExposure, ...]):
    """Two-asset PAC scenario with per-asset sector exposures replaced.

    Asset ``asset:a`` and ``asset:b`` keep their identity, prices and target
    weights; only their exposure declarations change, which is exactly the
    dimension these tests vary.
    """
    base = _two_asset_pac_scenario()
    asset_a, asset_b = base.assets
    return replace(base, assets=(_with_exposures(asset_a, *exposures_a), _with_exposures(asset_b, *exposures_b)))


def _evaluate(scenario, *, quanta: dict[str, int] | None = None):
    """Replay a candidate through the real evaluator (no solver required).

    Defaults every decision to its ``upper_quanta`` — the maximal buy, which
    is feasible in these small scenarios — so the evaluation carries real
    orders, accounting and costs. ``quanta`` overrides specific decisions
    (used to force the all-zero, zero-denominator candidate).
    """
    view = build_exact_policy_view(scenario, purpose="primary")
    overrides = quanta or {}
    candidate = CandidateActionVector(
        view_id=view.view_id,
        candidate_id="candidate:test",
        decisions=tuple(CandidateDecision(decision_id=decision.decision_id, quanta=overrides.get(decision.decision_id, decision.upper_quanta)) for decision in view.decisions),
    )
    return view, evaluate_exact_candidate(scenario, view, candidate)


def _all_zero_quanta(scenario) -> dict[str, int]:
    view = build_exact_policy_view(scenario, purpose="primary")
    return {decision.decision_id: 0 for decision in view.decisions}


def _solve(scenario):
    """Compile and solve a fresh model — a genuine ``SolverRunResult``.

    A fresh ``compile_policy_program`` per call keeps every solve on its own
    ``Model`` (the PySCIPOpt reuse trap the sibling suites document).
    """
    view = build_exact_policy_view(scenario, purpose="primary")
    result = solve_policy_program(compile_policy_program(scenario, view))
    return view, result


def _dimension_rows(rows, dimension: str):
    return [row for row in rows if row.dimension == dimension]


def _exact_target_total(rows) -> R:
    return sum((PR._exact_of(row.target_weight) for row in rows), R(0))


def _exact_final_total(rows) -> R:
    return sum((PR._exact_of(row.final_weight.value) for row in rows), R(0))


def _assert_dimension_closes(rows, dimension: str, *, check_final: bool) -> None:
    """Assert the closure identity in exact ``ExactRatio`` arithmetic.

    This deliberately re-sums the *emitted* rows rather than trusting the
    production guard: a closure identity that silently passes because it never
    actually evaluates is the exact shape a regression would hide behind, so
    the assertion genuinely adds the projected weights and compares to one.
    """
    dim_rows = _dimension_rows(rows, dimension)
    assert dim_rows, f"expected exposure rows for dimension {dimension!r}"
    assert _exact_target_total(dim_rows) == R(1)
    if check_final:
        assert _exact_final_total(dim_rows) == R(1)


def _assert_schema_accepts_exposure(rows, final_invested: R) -> None:
    """Feed the emitted rows through the real schema validator.

    The validator is the specification, so this calls
    ``_validate_weight_availability`` directly (plus the unconditional
    ``target_weight`` closure the exposure projection validator imposes),
    exactly as the wire assembly would — a green here means the projection is
    emittable, not merely internally consistent.
    """
    dimensions: dict[str, list] = {}
    for row in rows:
        dimensions.setdefault(row.dimension, []).append(row)
    total = Fraction(final_invested.numerator, final_invested.denominator)
    for dimension, dim_rows in dimensions.items():
        target_sum = sum((_exact_fraction(row.target_weight) for row in dim_rows), Fraction())
        assert target_sum == 1, f"{dimension} targets sum to {target_sum}, not 1"
        _validate_weight_availability([row.final_weight for row in dim_rows], total, "zero_final_invested", f"{dimension} final exposure")


def _build_primary_solution(scenario, view, evaluation, *, sequence: PR._SequenceAllocator | None = None) -> PacIncumbentSolution:
    """Assemble every solution projection into the wire ``PacIncumbentSolution``.

    Shares one ``_SequenceAllocator`` across the funding/conversion/order
    builders, called in execution order exactly as ``_build_solution_parts``
    calls them, so the produced sequences obey the schema's cross-section
    uniqueness and per-section ordering rules. FX actions take no sequence:
    the user executes their conversion.
    """
    allocator = sequence or PR._SequenceAllocator()
    funding_actions = PR.build_funding_actions(scenario, evaluation, allocator)
    fx_actions = PR.build_fx_actions(scenario, evaluation)
    conversions = PR.build_conversions(scenario, evaluation, fx_actions, allocator)
    order_rows = PR.build_order_rows(scenario, evaluation, allocator)
    return PacIncumbentSolution(
        solution_id="solution:primary",
        solution_kind="primary",
        validation="decimal_verified",
        asset_rows=PR.build_asset_rows(scenario, evaluation),
        funding_actions=funding_actions,
        fx_actions=fx_actions,
        conversions=conversions,
        order_rows=order_rows,
        ledger_rows=PR.build_ledger_rows(evaluation),
        rounding_top_ups=[],  # every caller asserts a feasible replay, and a feasible replay has no top-up
        exposure_rows=PR.build_exposure_rows(scenario, evaluation),
        accounting=PR.build_accounting(scenario, evaluation),
        costs=PR.build_costs(scenario, evaluation),
        objectives=PR.build_objective_results(scenario, view, evaluation),
    )


def _referenced_provenance_ids(solution: PacIncumbentSolution) -> set[str]:
    rows = [*solution.funding_actions, *solution.fx_actions, *solution.conversions, *solution.order_rows, *solution.exposure_rows]
    return {provenance_id for row in rows for provenance_id in row.provenance_ids}


def _numbered_steps(funding, conversions, orders) -> list[int]:
    """The execution steps in section order: funding, manual conversions, orders.

    An automatic conversion carries no sequence (the Broker converts while the
    orders execute), so it is not a step the user numbers.
    """
    return [*(row.sequence for row in funding), *(row.sequence for row in conversions if row.sequence is not None), *(row.sequence for row in orders)]


def _with_conversion_mode(scenario, broker_id: str, mode: str):
    """The same scenario with one Broker's conversion mode replaced.

    ``ExactBroker.__post_init__`` runs again under ``dataclasses.replace``, so
    the mode is validated exactly as normalisation would validate it.
    """
    assert any(broker.broker_id == broker_id for broker in scenario.brokers), f"no Broker {broker_id!r} to switch"
    return replace(scenario, brokers=tuple(replace(broker, conversion_mode=mode) if broker.broker_id == broker_id else broker for broker in scenario.brokers))


# Concrete exposure scenarios, named for the shape they exercise.
def _coordinator_scenario():
    """Asset A fully Tech, asset B undeclared (the coordinator's case)."""
    return _scenario_with_asset_exposures((_exposure("sector", "tech", R(1)),), ())


def _partial_scenario():
    """Asset A declares 60% Tech and nothing else; asset B undeclared."""
    return _scenario_with_asset_exposures((_exposure("sector", "tech", R(3, 5)),), ())


def _uniform_scenario():
    """Nobody declares anything in any dimension."""
    return _scenario_with_asset_exposures((), ())


def _full_coverage_scenario():
    """Asset A fully Tech, asset B fully Health — the sector is fully covered."""
    return _scenario_with_asset_exposures((_exposure("sector", "tech", R(1)),), (_exposure("sector", "health", R(1)),))


# --------------------------------------------------------------------------
# Exposure — the five shapes, each judged by the schema validator
# --------------------------------------------------------------------------


def test_undeclared_asset_emits_uncategorised_residual_preserving_real_weight() -> None:
    """One asset fully Tech, one undeclared -> Tech keeps its true weight and
    the uncovered part becomes a named uncategorised residual row.

    Asset A is genuinely a real slice of the portfolio, so its Tech weight
    must be *preserved*, not rescaled away to make the numbers add up; the
    dimension closes to exactly one because the algebra says so, with the
    residual carrying asset B's whole contribution. Both the target and final
    vectors close in exact arithmetic, and the schema accepts the result.
    """
    scenario = _coordinator_scenario()
    view, evaluation = _evaluate(scenario)
    rows = PR.build_exposure_rows(scenario, evaluation)

    sector = _dimension_rows(rows, "sector")
    categories = {row.category_id for row in sector}
    assert "tech" in categories
    assert PR.UNCATEGORISED_EXPOSURE_CATEGORY_ID in categories

    _assert_dimension_closes(rows, "sector", check_final=True)

    tech_row = next(row for row in sector if row.category_id == "tech")
    assert PR._exact_of(tech_row.final_weight.value) > R(0), "Tech's real weight was destroyed, not preserved"

    # The residual row carries real, byte-reproducible provenance (asset B's
    # quote is the fact its weight was computed from): non-empty and
    # sorted-unique so the published row is stable across runs.
    residual_row = next(row for row in sector if row.category_id == PR.UNCATEGORISED_EXPOSURE_CATEGORY_ID)
    assert residual_row.provenance_ids
    assert residual_row.provenance_ids == sorted(set(residual_row.provenance_ids))

    _assert_schema_accepts_exposure(rows, evaluation.accounting.final_invested)


def test_partial_declaration_routes_the_undeclared_remainder_to_the_residual() -> None:
    """An asset declaring 60% Tech contributes 40%*w to the residual.

    ``normalize.py`` validates each exposure's range and ``(dimension,
    category)`` uniqueness but never requires a per-asset dimension to close,
    so a 60%-only declaration is real input, not a corner case. The Tech
    target is exactly ``w_A * 3/5`` and the residual is exactly
    ``w_A * 2/5 + w_B`` — asserted as an exact identity on the evaluation's own
    target weights, never on a float.
    """
    scenario = _partial_scenario()
    view, evaluation = _evaluate(scenario)
    rows = PR.build_exposure_rows(scenario, evaluation)

    sector = _dimension_rows(rows, "sector")
    assert {row.category_id for row in sector} == {"tech", PR.UNCATEGORISED_EXPOSURE_CATEGORY_ID}
    _assert_dimension_closes(rows, "sector", check_final=True)

    target_by_asset = {row.asset_id: row.target_weight for row in evaluation.assets}
    tech_row = next(row for row in sector if row.category_id == "tech")
    residual_row = next(row for row in sector if row.category_id == PR.UNCATEGORISED_EXPOSURE_CATEGORY_ID)
    assert PR._exact_of(tech_row.target_weight) == target_by_asset["asset:a"] * R(3, 5)
    assert PR._exact_of(residual_row.target_weight) == target_by_asset["asset:a"] * R(2, 5) + target_by_asset["asset:b"] * R(1)

    _assert_schema_accepts_exposure(rows, evaluation.accounting.final_invested)


def test_uniform_rule_emits_the_residual_alone_when_nobody_declares() -> None:
    """When no asset declares anything in a dimension, the residual is emitted
    *alone at weight one* — the same rule as every other case, with no special
    branch. Suppressing the dimension exactly when the data is at its worst
    (no classification at all) would invert the signal, turning "we know
    nothing" into "there is nothing".
    """
    scenario = _uniform_scenario()
    view, evaluation = _evaluate(scenario)
    rows = PR.build_exposure_rows(scenario, evaluation)

    sector = _dimension_rows(rows, "sector")
    assert len(sector) == 1
    assert sector[0].category_id == PR.UNCATEGORISED_EXPOSURE_CATEGORY_ID
    _assert_dimension_closes(rows, "sector", check_final=True)
    _assert_schema_accepts_exposure(rows, evaluation.accounting.final_invested)


def test_full_coverage_emits_no_residual_row() -> None:
    """When every asset's declarations already close the dimension, no residual
    row is emitted — the remainder is genuinely zero, so publishing an
    uncategorised slice would be noise.
    """
    scenario = _full_coverage_scenario()
    view, evaluation = _evaluate(scenario)
    rows = PR.build_exposure_rows(scenario, evaluation)

    sector = _dimension_rows(rows, "sector")
    assert {row.category_id for row in sector} == {"tech", "health"}
    assert PR.UNCATEGORISED_EXPOSURE_CATEGORY_ID not in {row.category_id for row in sector}
    _assert_dimension_closes(rows, "sector", check_final=True)
    _assert_schema_accepts_exposure(rows, evaluation.accounting.final_invested)


def test_zero_denominator_marks_every_weight_unavailable_yet_targets_still_close() -> None:
    """With nothing invested, *every* final weight is unavailable carrying
    ``zero_final_invested`` — a weight is genuinely undefined, not merely
    unknown, when the denominator is zero. Targets do not depend on the
    denominator, so they still close to exactly one, and the schema accepts
    the zero-invested world.
    """
    scenario = _coordinator_scenario()
    view, evaluation = _evaluate(scenario, quanta=_all_zero_quanta(scenario))
    assert evaluation.accounting.final_invested == R(0)

    rows = PR.build_exposure_rows(scenario, evaluation)
    sector = _dimension_rows(rows, "sector")
    assert sector, "the dimension must still be published when nothing is invested"
    assert all(row.final_weight.kind == "unavailable" for row in sector)
    assert all(row.final_weight.reason == "zero_final_invested" for row in sector)

    # Targets close even though every final weight is unavailable.
    assert _exact_target_total(sector) == R(1)
    _assert_schema_accepts_exposure(rows, evaluation.accounting.final_invested)


def test_exposure_closure_is_an_exact_identity_across_every_emitted_dimension() -> None:
    """The closure identity, asserted directly on the emitted rows for every
    dimension the projection produced.

    Σ_categories (Σ_assets w*e) + Σ_assets w*(1 - Σ_categories e) = Σ_assets w = 1

    holds by algebra, never by rescaling — rescaling is forbidden because it
    would convert a data-quality gap into an invisible one. This test exists
    specifically so that a change which breaks the identity (or a residual
    derivation that no longer accounts for the whole remainder) is caught here
    in exact arithmetic, independently of the production guard.
    """
    scenario = _coordinator_scenario()
    view, evaluation = _evaluate(scenario)
    rows = PR.build_exposure_rows(scenario, evaluation)

    emitted_dimensions = {row.dimension for row in rows}
    assert emitted_dimensions, "the projection emitted no exposure rows at all"
    for dimension in emitted_dimensions:
        _assert_dimension_closes(rows, dimension, check_final=True)


# --------------------------------------------------------------------------
# Provenance — dedup in canonical order, total containment, fail-closed
# --------------------------------------------------------------------------


def test_shared_provenance_records_are_deduplicated_in_canonical_order() -> None:
    """Two assets in one category with distinct provenance records -> the
    category row lists both, sorted; two assets sharing one record -> a single
    id. ``_validate_ready_solution`` enforces per-row uniqueness (several
    assets legitimately share one ``market_data``/``portfolio`` record), and
    sorting additionally makes the row byte-reproducible across runs rather
    than merely valid today.
    """
    distinct = _scenario_with_asset_exposures(
        (_exposure("sector", "tech", R(1), provenance="provenance:mmm"),),
        (_exposure("sector", "tech", R(1), provenance="provenance:aaa"),),
    )
    view, evaluation = _evaluate(distinct)
    tech_row = next(row for row in PR.build_exposure_rows(distinct, evaluation) if row.category_id == "tech")
    assert tech_row.provenance_ids == ["provenance:aaa", "provenance:mmm"]
    assert tech_row.provenance_ids == sorted(set(tech_row.provenance_ids))

    shared = _scenario_with_asset_exposures(
        (_exposure("sector", "tech", R(1), provenance="provenance:shared"),),
        (_exposure("sector", "tech", R(1), provenance="provenance:shared"),),
    )
    view2, evaluation2 = _evaluate(shared)
    shared_row = next(row for row in PR.build_exposure_rows(shared, evaluation2) if row.category_id == "tech")
    assert shared_row.provenance_ids == ["provenance:shared"]


def test_canonical_provenance_ids_sorts_the_union() -> None:
    """The canonicaliser returns a sorted, deduplicated list. Byte-reproducible
    ordering is the property under test: the same set of contributors must
    always yield the same row.
    """
    ids = {"provenance:c", "provenance:a", "provenance:b"}
    assert PR._canonical_provenance_ids(ids, context="unit", asset_ids=("asset:a",)) == ["provenance:a", "provenance:b", "provenance:c"]


def test_empty_provenance_union_fails_closed_naming_the_assets() -> None:
    """An empty provenance union raises ``ExposureProvenanceError`` and names
    the offending assets. ``min_length=1`` on the wire would catch the empty
    list too, but late and opaquely — pointing at a row rather than at the
    assets that produced it. The named exception is the legible diagnosis.
    """
    with pytest.raises(PR.ExposureProvenanceError) as excinfo:
        PR._canonical_provenance_ids(set(), context="sector uncategorised exposure residual", asset_ids=("asset:x", "asset:y"))
    message = str(excinfo.value)
    assert "asset:x" in message
    assert "asset:y" in message


def test_published_provenance_totally_contains_referenced_ids() -> None:
    """Containment is total *by construction*, and this asserts it directly.

    ``build_planner_provenance`` publishes the scenario's whole provenance
    list rather than a used-only subset, so every id any row references is
    necessarily present. That is a structural property, not a coincidence of
    this fixture: it deliberately replaced a conditional failure mode that
    only surfaced on scenarios with uncategorised assets. So this fixture
    keeps an uncategorised asset present and still expects containment to
    hold. A future "optimisation" that filters the published list back down to
    used-only would break this test — which is the point.
    """
    scenario = _coordinator_scenario()  # asset B is uncategorised
    view, evaluation = _evaluate(scenario)
    assert evaluation.feasible
    solution = _build_primary_solution(scenario, view, evaluation)

    published = {record.provenance_id for record in PR.build_planner_provenance(scenario)}
    referenced = _referenced_provenance_ids(solution)
    assert referenced, "the projected rows must reference some provenance"
    assert referenced <= published

    assert any(row.category_id == PR.UNCATEGORISED_EXPOSURE_CATEGORY_ID for row in solution.exposure_rows)


# --------------------------------------------------------------------------
# Solver evidence — tie stages filtered, tie-break published once
# --------------------------------------------------------------------------


def test_tie_stages_are_filtered_from_solver_evidence() -> None:
    """The solver runs one ``tie:<decision_id>`` stage per canonical tie-break
    entry, but the wire ``ObjectiveCode`` enum has no ``tie:*`` member, so
    those stages simply cannot be expressed as evidence. A reader seeing fewer
    evidence rows than the solver ran is *not* looking at data loss — the
    tie-break is published exactly once as ``objectives.tie_break``.

    Counts are read off the live objects: the solver ran strictly more stages
    than the evidence carries, and the evidence carries exactly one row per
    published objective.
    """
    view, result = _solve(_two_asset_pac_scenario())
    evidence = PR.build_solver_evidence(_two_asset_pac_scenario(), view, result)

    assert all(not stage.objective_code.startswith("tie") for stage in evidence.stages)
    objective_codes = {ref.code for ref in view.objectives}
    assert all(stage.objective_code in objective_codes for stage in evidence.stages)
    assert len(evidence.stages) == len(view.objectives)
    assert len(result.stages) > len(evidence.stages), "the solver ran no tie stages, so there is nothing to prove filtered"


def test_tie_break_is_published_exactly_once_in_objective_results() -> None:
    """The canonical tie-break vector lives on ``objectives.tie_break`` (the
    one place it is published), carrying the view's own ordered decision ids —
    not hidden inside the solver evidence stage list.
    """
    scenario = _two_asset_pac_scenario()
    view, evaluation = _evaluate(scenario)
    objectives = PR.build_objective_results(scenario, view, evaluation)

    assert objectives.tie_break.code == "canonical_key"
    assert objectives.tie_break.ordered_keys == list(view.tie_breaks[0].decision_ids)


# --------------------------------------------------------------------------
# stop_reason — determined by stage statuses, not chosen
# --------------------------------------------------------------------------


def test_stop_reason_is_completed_iff_no_stage_is_unfinished() -> None:
    """``_validate_stop_evidence`` requires ``completed`` iff no stage is
    unfinished, so ``build_stop_reason`` is a determined mapping, not a choice.
    A real fully-solved run reports ``completed``; forcing an unfinished stage
    (by doctoring a genuine result's stage status) flips the mapping, and
    *which* limit stopped it is read from the stage that actually stopped —
    never assumed to be the clock.
    """
    view, result = _solve(_two_asset_pac_scenario())
    assert all(stage.status == "finished" for stage in result.stages)
    assert PR.build_stop_reason(result) == "completed"

    node_limited = replace(result, stages=(replace(result.stages[0], status="unfinished", scip_status="nodelimit"), *result.stages[1:]))
    assert PR.build_stop_reason(node_limited) == "node_limit"

    time_limited = replace(result, stages=(replace(result.stages[0], status="unfinished", scip_status="timelimit"), *result.stages[1:]))
    assert PR.build_stop_reason(time_limited) == "time_limit"


def test_infeasible_first_stage_is_a_verdict_that_completes_the_search() -> None:
    """When SCIP closes the first, global stage ``infeasible`` (D-X1), that is
    a verdict, not an interruption. ``build_stop_reason`` must call the run
    ``completed``: ``_validate_stop_evidence`` keys ``completed`` on the
    absence of *unfinished* stages, and ``infeasible`` is not one. And
    ``build_solver_evidence`` must carry that single stage with none of the four
    observations filled in, because SCIP reported none.

    This is a real run, not a doctored one: the route cap (10) is below the
    required contribution (50), so no candidate can exist.
    """
    scenario = _pac_scenario(required=R(50), route_cap=R(10))
    view, result = _solve(scenario)
    assert result.outcome == "reported_infeasible"

    assert PR.build_stop_reason(result) == "completed"

    evidence = PR.build_solver_evidence(scenario, view, result)
    assert evidence.kind == "reported_floating"
    (stage,) = evidence.stages
    first = min(view.objectives, key=lambda ref: ref.ordinal)
    assert (stage.objective_code, stage.ordinal, stage.scope, stage.status) == (first.code, 1, "global", "infeasible")
    assert (stage.primal, stage.dual, stage.absolute_gap, stage.relative_gap) == (None, None, None, None)


# --------------------------------------------------------------------------
# Cross-section sequence allocation — two properties at once
# --------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["manual", "automatic"])
def test_cross_section_sequences_are_globally_unique_and_densely_shared(mode: str) -> None:
    """A single shared ``_SequenceAllocator`` across the funding/conversion/order
    sections yields globally-unique sequences that are dense from one, in
    execution order: funding, then manual conversions, then orders.

    Density is what distinguishes the shared allocator from per-section
    counters: those would each start at one and collide on row one, producing
    ``[1, 1, 1]``; the shared allocator produces a contiguous ``[1, 2, ..., n]``.
    The coarse funding+FX+buy scenario exercises every section at once. With
    its FX Broker in manual mode the conversion is a numbered step between
    funding and orders; in automatic mode the Broker converts while the orders
    execute, so the conversion carries no sequence, consumes none, and the
    orders follow funding directly.
    """
    scenario = _with_conversion_mode(_coarse_funding_fx_scenario(), "broker:destination", mode)
    view, evaluation = _evaluate(scenario)
    allocator = PR._SequenceAllocator()
    funding = PR.build_funding_actions(scenario, evaluation, allocator)
    fx = PR.build_fx_actions(scenario, evaluation)
    conversions = PR.build_conversions(scenario, evaluation, fx, allocator)
    orders = PR.build_order_rows(scenario, evaluation, allocator)

    # Every section is genuinely populated, so the cross-section rule has
    # something to prove.
    assert funding and fx and conversions and orders
    assert {conversion.mode for conversion in conversions} == {mode}
    if mode == "automatic":
        assert all(conversion.sequence is None for conversion in conversions)

    sequences = _numbered_steps(funding, conversions, orders)
    assert len(sequences) == len(set(sequences)), "sequences collide across sections"
    assert sequences == list(range(1, len(sequences) + 1)), "sequences are not the dense, execution-ordered range a shared allocator produces"


def test_each_action_section_is_internally_ascending() -> None:
    """Each section stays internally sequence-ordered. Proven on a section with
    more than one row (the two-asset scenario's two BUY orders) so the
    ordering is a real assertion, not vacuously true — a later change that
    renumbers per section would break exactly this while leaving global
    uniqueness intact.
    """
    scenario = _two_asset_pac_scenario()
    view, evaluation = _evaluate(scenario)
    allocator = PR._SequenceAllocator()
    funding = PR.build_funding_actions(scenario, evaluation, allocator)
    fx = PR.build_fx_actions(scenario, evaluation)
    conversions = PR.build_conversions(scenario, evaluation, fx, allocator)
    orders = PR.build_order_rows(scenario, evaluation, allocator)

    assert len(orders) >= 2, "need a multi-row section for a non-vacuous ordering check"
    for section in (funding, [row for row in conversions if row.sequence is not None], orders):
        section_sequences = [row.sequence for row in section]
        assert section_sequences == sorted(section_sequences)


# --------------------------------------------------------------------------
# Conversions — the engine's FX actions, one row per Broker and currency pair
# --------------------------------------------------------------------------

_ALPHA_BROKER_ID = "broker:alpha"
_BETA_BROKER_ID = "broker:beta"
_SECOND_ALPHA_USD_PROVENANCE_ID = "provenance:route:c:alpha"
# EUR debited per BUY route, in whole EUR (the scenario's EUR quantum is one).
_MULTI_CONVERSION_FX_DEBITS = {"route:a:beta": 4, "route:b:alpha": 2, "route:c:alpha": 2, "route:d:alpha": 5}


def _multi_conversion_scenario(*, alpha_mode: str = "manual", beta_mode: str = "manual"):
    """Four EUR-funded FX decisions that make three conversions.

    Broker alpha converts EUR into USD on two BUY routes (assets a and b) and
    into GBP on a third (asset c); Broker beta converts EUR into USD on its
    own route for asset a. Route IDs sort beta's route first, so the engine's
    (route, currency) order meets the pairs in the *reverse* of their canonical
    (Broker, source, destination) order. A whole-unit quantum makes a posted
    credit visibly differ from the exact one, and the second alpha USD route
    cites its own (published) provenance record so a conversion's provenance
    is a real union.
    """
    capability = _capability("capability:whole")
    usd_fee = _fee("fee:buy:usd", capability.capability_id, "buy", currency="USD")
    gbp_fee = _fee("fee:buy:gbp", capability.capability_id, "buy", currency="GBP")
    alpha = _broker(_ALPHA_BROKER_ID, (capability,), (usd_fee, gbp_fee), conversion_mode=alpha_mode)
    beta = _broker(_BETA_BROKER_ID, (capability,), (usd_fee,), conversion_mode=beta_mode)

    def buy(route_id: str, broker_id: str, asset_id: str, fee_id: str):
        return _order_route(route_id, broker_id=broker_id, asset_id=asset_id, capability=capability, fee_id=fee_id, side="buy")

    base = _scenario(
        "scenario:multi-conversion",
        product="pac",
        policy="proportional",
        assets=(
            _asset("asset:a", price=R(5), currency="USD"),
            _asset("asset:b", price=R(10), currency="USD"),
            _asset("asset:c", price=R(4), currency="GBP"),
        ),
        brokers=(alpha, beta),
        existing_cash=(_cash("cash:alpha", _ALPHA_BROKER_ID, R(20)), _cash("cash:beta", _BETA_BROKER_ID, R(20))),
        order_routes=(
            buy("route:a:beta", _BETA_BROKER_ID, "asset:a", usd_fee.fee_schedule_id),
            buy("route:b:alpha", _ALPHA_BROKER_ID, "asset:a", usd_fee.fee_schedule_id),
            replace(buy("route:c:alpha", _ALPHA_BROKER_ID, "asset:b", usd_fee.fee_schedule_id), provenance_id=_SECOND_ALPHA_USD_PROVENANCE_ID),
            buy("route:d:alpha", _ALPHA_BROKER_ID, "asset:c", gbp_fee.fee_schedule_id),
        ),
        fx_rates=(_fx_rate("EUR", "USD", R(5, 4)), _fx_rate("EUR", "GBP", R(4, 5))),
        fx_spread_rate=R(1, 10),
        currency_quantums=(("EUR", ONE), ("GBP", ONE), ("USD", ONE)),
    )
    second_record = replace(base.provenance[0], provenance_id=_SECOND_ALPHA_USD_PROVENANCE_ID, label="second alpha USD route")
    return replace(base, provenance=tuple(sorted((*base.provenance, second_record), key=lambda record: record.provenance_id)))


def _evaluate_multi_conversion(scenario):
    """Replay the candidate that debits only FX: every other decision is zero.

    The report builders read ``evaluation.fx`` whatever the candidate's
    feasibility, so no BUY is needed to exercise them; the guard proves every
    FX decision exists in the view and carried its quanta, so an override
    silently ignored by ``_evaluate`` cannot pass for a projection.
    """
    fx_quanta = {exact_decision_id("fx_debit", _fx_debit_key(route_id, "EUR")): debit for route_id, debit in _MULTI_CONVERSION_FX_DEBITS.items()}
    view, evaluation = _evaluate(scenario, quanta={**_all_zero_quanta(scenario), **fx_quanta})
    assert evaluation.candidate_valid
    assert {(exact.order_route_id, exact.quanta) for exact in evaluation.fx} == set(_MULTI_CONVERSION_FX_DEBITS.items())
    return evaluation


def _amount(money) -> R:
    """A wire fixed-decimal amount read back as an exact ratio."""
    return R.from_decimal(Decimal(str(money.amount)))


def test_fx_actions_carry_no_sequence_and_name_their_conversion() -> None:
    """An FX action is the engine's decision, not a step the user takes: it
    carries no sequence and names the conversion that aggregates it, keyed by
    its Broker and currency pair."""
    scenario = _multi_conversion_scenario()
    evaluation = _evaluate_multi_conversion(scenario)

    fx_actions = PR.build_fx_actions(scenario, evaluation)

    assert "sequence" not in PlannerFxAction.model_fields
    for exact, action in zip(evaluation.fx, fx_actions, strict=True):
        assert "sequence" not in action.model_dump(mode="json")
        assert action.action_id == f"fx:{exact.order_route_id}:{exact.source_currency}"
        assert action.conversion_id == f"conversion:{exact.broker_id}:{exact.source_currency}:{exact.destination_currency}"
        assert (action.order_route_id, action.broker_id) == (exact.order_route_id, exact.broker_id)
        assert _amount(action.destination_credit) == exact.posted_destination_credit


def test_conversions_group_fx_actions_by_broker_and_currency_pair() -> None:
    """One conversion per (Broker, source, destination), in that canonical
    order whatever order the engine met the pairs in.

    A conversion's debit and spread are the exact sums of its actions; its
    credit sums the *posted* credits the ledger reconciles against. Alpha's
    two USD actions each credit an exact 2.25 USD that posts as 2, so the
    conversion credits 4 USD — not the 4.5 exact sum, nor its HALF_UP
    rounding 5 — while beta's single 4.5 USD credit posts as 5. Rates are the
    pair's (global per pair), member IDs keep the action order, and the
    provenance is the canonical union of the members'.
    """
    scenario = _multi_conversion_scenario()
    evaluation = _evaluate_multi_conversion(scenario)
    fx_actions = PR.build_fx_actions(scenario, evaluation)

    conversions = PR.build_conversions(scenario, evaluation, fx_actions, PR._SequenceAllocator())

    canonical_pairs = [(_ALPHA_BROKER_ID, "EUR", "GBP"), (_ALPHA_BROKER_ID, "EUR", "USD"), (_BETA_BROKER_ID, "EUR", "USD")]
    engine_pairs = list(dict.fromkeys((exact.broker_id, exact.source_currency, exact.destination_currency) for exact in evaluation.fx))
    assert engine_pairs == list(reversed(canonical_pairs)), "precondition: the engine meets the pairs in reverse canonical order"
    assert [(row.broker_id, row.source_debit.currency, row.destination_credit.currency) for row in conversions] == canonical_pairs
    assert [row.conversion_id for row in conversions] == [f"conversion:{broker}:{source}:{destination}" for broker, source, destination in canonical_pairs]

    by_id = {row.conversion_id: row for row in conversions}
    expected = {
        # conversion_id: (fx_action_ids, debit EUR, posted credit, spread EUR)
        "conversion:broker:alpha:EUR:GBP": (["fx:route:d:alpha:EUR"], R(5), R(4), R(1, 2)),
        "conversion:broker:alpha:EUR:USD": (["fx:route:b:alpha:EUR", "fx:route:c:alpha:EUR"], R(4), R(4), R(2, 5)),
        "conversion:broker:beta:EUR:USD": (["fx:route:a:beta:EUR"], R(4), R(5), R(2, 5)),
    }
    for conversion_id, (action_ids, debit, credit, spread) in expected.items():
        row = by_id[conversion_id]
        assert row.fx_action_ids == action_ids
        assert _amount(row.source_debit) == debit
        assert _amount(row.destination_credit) == credit
        assert (PR._exact_of(row.spread_loss.value), row.spread_loss.currency) == (spread, scenario.valuation_currency)

    # Each figure is the members' own, so the aggregation adds nothing of its
    # own: exact sums for debit and spread, posted sum for the credit, and the
    # one rate every member of the pair shares.
    members_by_id: dict[str, list] = {}
    for exact, action in zip(evaluation.fx, fx_actions, strict=True):
        members_by_id.setdefault(action.conversion_id, []).append((exact, action))
    for row in conversions:
        members = members_by_id[row.conversion_id]
        assert _amount(row.source_debit) == sum((exact.source_debit for exact, _ in members), R(0))
        assert _amount(row.destination_credit) == sum((exact.posted_destination_credit for exact, _ in members), R(0))
        assert PR._exact_of(row.spread_loss.value) == sum((exact.spread_loss for exact, _ in members), R(0))
        assert {PR._exact_of(row.spot_rate.value)} == {exact.approved_rate for exact, _ in members}
        assert {PR._exact_of(row.effective_rate.value)} == {exact.effective_rate for exact, _ in members}
        assert (row.spot_rate.source_currency, row.spot_rate.destination_currency) == (row.source_debit.currency, row.destination_credit.currency)
        assert row.provenance_ids == sorted({provenance_id for _, action in members for provenance_id in action.provenance_ids})

    alpha_usd = members_by_id["conversion:broker:alpha:EUR:USD"]
    assert sum((exact.exact_destination_credit for exact, _ in alpha_usd), R(0)) == R(9, 2), "precondition: the exact credits do not sum to the posted ones"
    assert by_id["conversion:broker:alpha:EUR:USD"].provenance_ids == sorted({PROVENANCE_ID, _SECOND_ALPHA_USD_PROVENANCE_ID})


@pytest.mark.parametrize(
    ("alpha_mode", "beta_mode", "expected_sequences", "next_free"),
    [
        pytest.param("manual", "manual", [3, 4, 5], 6, id="all-manual"),
        pytest.param("automatic", "manual", [None, None, 3], 4, id="alpha-automatic"),
        pytest.param("manual", "automatic", [3, 4, None], 5, id="beta-automatic"),
        pytest.param("automatic", "automatic", [None, None, None], 3, id="all-automatic"),
    ],
)
def test_manual_conversions_take_the_next_step_and_automatic_ones_none(alpha_mode: str, beta_mode: str, expected_sequences: list[int | None], next_free: int) -> None:
    """A manual conversion is a step the user takes, so it draws the next
    sequence from the shared allocator; an automatic one happens inside the
    orders, carries none and consumes none. The allocator is primed as if two
    funding actions had been numbered already, and the canonical order is
    (alpha GBP, alpha USD, beta USD).

    The mode is presentation only: every figure of a conversion is the same
    whichever mode its Broker declares.
    """
    scenario = _multi_conversion_scenario(alpha_mode=alpha_mode, beta_mode=beta_mode)
    evaluation = _evaluate_multi_conversion(scenario)
    allocator = PR._SequenceAllocator()
    assert [allocator.next(), allocator.next()] == [1, 2]

    conversions = PR.build_conversions(scenario, evaluation, PR.build_fx_actions(scenario, evaluation), allocator)

    mode_by_broker = {_ALPHA_BROKER_ID: alpha_mode, _BETA_BROKER_ID: beta_mode}
    assert [row.mode for row in conversions] == [mode_by_broker[row.broker_id] for row in conversions]
    assert [row.sequence for row in conversions] == expected_sequences
    assert allocator.next() == next_free

    manual_scenario = _multi_conversion_scenario()
    manual_evaluation = _evaluate_multi_conversion(manual_scenario)
    manual = PR.build_conversions(manual_scenario, manual_evaluation, PR.build_fx_actions(manual_scenario, manual_evaluation), PR._SequenceAllocator())
    presentation = {"mode", "sequence"}
    assert [row.model_dump(mode="json", exclude=presentation) for row in conversions] == [row.model_dump(mode="json", exclude=presentation) for row in manual]


# --------------------------------------------------------------------------
# Rounding top-ups — a pure projection of what the classifier decided
# --------------------------------------------------------------------------


def test_rounding_top_ups_are_projected_not_recomputed() -> None:
    """``build_rounding_top_ups`` only re-expresses the classifier's dataclasses.

    The amount goes out as fixed-decimal text in the pool's own currency; the
    valuation, already computed by the classifier, as money in the scenario's
    valuation currency: ``finite_decimal`` when it terminates (EUR 1/100),
    ``exact_ratio`` when it does not (USD 0.01 valued at EUR 1/120). The input
    order is deliberately not the canonical (broker, currency) one, so "order
    preserved" is a real assertion: a projection never re-sorts.
    """
    scenario = _pac_scenario()
    assert scenario.valuation_currency == "EUR"
    top_ups = (
        pac_models.ExactRoundingTopUp(broker_id="broker:b", currency="USD", amount=R(1, 100), rounded_postings=2, valuation_amount=R(1, 120)),
        pac_models.ExactRoundingTopUp(broker_id="broker:a", currency="EUR", amount=R(1, 100), rounded_postings=1, valuation_amount=R(1, 100)),
    )

    rows = PR.build_rounding_top_ups(scenario, top_ups)

    assert [(row.broker_id, row.currency, row.rounded_postings) for row in rows] == [("broker:b", "USD", 2), ("broker:a", "EUR", 1)]
    assert [Decimal(row.amount) for row in rows] == [Decimal("0.01"), Decimal("0.01")]
    assert [row.model_dump(mode="json")["amount"] for row in rows] == ["0.01", "0.01"]
    usd, eur = rows
    assert (eur.valuation_amount.currency, eur.valuation_amount.value.kind) == ("EUR", "finite_decimal")
    assert _exact_fraction(eur.valuation_amount.value) == Fraction(1, 100)
    assert (usd.valuation_amount.currency, usd.valuation_amount.value.kind) == ("EUR", "exact_ratio")
    assert _exact_fraction(usd.valuation_amount.value) == Fraction(1, 120)


# --------------------------------------------------------------------------
# Full end-to-end assembly — the real gate
# --------------------------------------------------------------------------


def test_full_ready_incumbent_result_validates_end_to_end_with_uncategorised_asset() -> None:
    """Build a genuine ``PacPlannerReadyIncumbentResult`` from a real solve and
    let pydantic and the validators judge it.

    The fixture deliberately includes an uncategorised asset (asset B), so the
    exposure residual and its provenance must survive all the way into the
    published result. The candidate is asserted feasible on replay *before*
    anything is assembled — a projection built from an infeasible replay would
    be meaningless. The proof is derived exactly as the product derives it —
    SCIP's own statuses, read by ``conclude_with_solver`` for the candidate
    SCIP returned — and wired as a ``solver_status`` proof, so the validators
    check its witness against the real solver evidence and the published
    objectives. The end-to-end assertions (containment, residual present, tie
    filter, sequence uniqueness, closed accounting identity) all read their
    counts off the live objects.
    """
    base = _two_asset_pac_scenario()
    asset_a, asset_b = base.assets
    scenario = replace(
        base,
        assets=(_with_exposures(asset_a, _exposure("sector", "tech", R(1), label="Tech")), _with_exposures(asset_b)),
    )

    view = build_exact_policy_view(scenario, purpose="primary")
    result = solve_policy_program(compile_policy_program(scenario, view))
    assert result.outcome == "incumbent"
    evaluation = evaluate_exact_candidate(scenario, view, result.candidate)
    assert evaluation.feasible is True

    solution = _build_primary_solution(scenario, view, evaluation)

    # Containment asserted on the builder outputs before pydantic also enforces
    # it, so a regression in the published provenance list surfaces here.
    published = {record.provenance_id for record in PR.build_planner_provenance(scenario)}
    referenced = _referenced_provenance_ids(solution)
    assert referenced <= published, f"referenced provenance not published: {referenced - published}"

    # SCIP closed every stage optimal on the candidate it returned: the view's
    # objectives, in cascade order, are what that proof is about.
    objective_codes = [ref.code for ref in sorted(view.objectives, key=lambda ref: ref.ordinal)]
    conclusion = conclude_with_solver(result, objective_codes=objective_codes, published=result.candidate)
    assert isinstance(conclusion, OptimalProvenConclusion)
    proof = OptimalProvenProof(
        kind="optimal_proven",
        proof_source="solver_status",
        witness=SolverStatusWitness(kind="solver_status", objective_codes=list(conclusion.witness.objective_codes)),
        tie_break_closed=True,
    )

    full = PacPlannerReadyIncumbentResult(
        operation="plan",
        availability="ready",
        result_state="ready_incumbent",
        outcome="incumbent_found",
        snapshot=PR.build_result_snapshot(scenario, view),
        catalogs=PR.build_planner_catalogs(scenario),
        provenance=PR.build_planner_provenance(scenario),
        scenario_basis=PR.build_scenario_basis(scenario, evaluation),
        stop_reason=PR.build_stop_reason(result),
        solver_evidence=PR.build_solver_evidence(scenario, view, result),
        issues=[],
        proof=proof,
        primary_solution=solution,
        deployment=DeploymentUnavailable(kind="unavailable", reason_code="allocation.deployment_omitted"),
    )

    # The uncategorised residual survived into the published solution.
    assert any(row.category_id == PR.UNCATEGORISED_EXPOSURE_CATEGORY_ID for row in full.primary_solution.exposure_rows)

    # Tie stages filtered; counts read off the live objects.
    assert len(full.solver_evidence.stages) == len(view.objectives)
    assert all(not stage.objective_code.startswith("tie") for stage in full.solver_evidence.stages)
    assert len(result.stages) > len(full.solver_evidence.stages)

    # Sequences globally unique across the numbered action sections.
    published_solution = full.primary_solution
    sequences = _numbered_steps(published_solution.funding_actions, published_solution.conversions, published_solution.order_rows)
    assert len(sequences) == len(set(sequences))

    # The accounting identity closes exactly.
    assert _exact_fraction(full.primary_solution.accounting.identity_delta.value) == Fraction(0)
