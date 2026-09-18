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
* **``stop_reason`` is determined by the stage statuses**, and cross-section
  action sequences come from a single shared allocator so they are globally
  unique *and* each section stays internally ascending.

The headline gate is a genuine end-to-end assembly: a real
``build_exact_policy_view -> compile -> solve -> replay -> project`` run whose
output is judged by pydantic and the validators, with an uncategorised asset
deliberately present.

These are pure in-process tests (``isolation="pure"``): no server, no
database, no clock, no sleeps, no network. Exact domain values compare with
``==`` on ``ExactRatio``; SCIP floats are never compared exactly. Candidate
and stage counts are read off the live result objects, never hardcoded.
Fixtures are reused from the sibling suites exactly the way they already share
them, with exposure variants built via ``dataclasses.replace``.
"""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from backend.app.schemas.pac_allocator import (
    DeploymentUnavailable,
    NotProvenProof,
    PacIncumbentSolution,
    PacPlannerReadyIncumbentResult,
    _exact_fraction,
    _validate_weight_availability,
)
from backend.app.services.pac_allocator import planner_report as PR
from backend.app.services.pac_allocator.compiler import compile_policy_program
from backend.app.services.pac_allocator.evaluator import build_exact_policy_view, evaluate_exact_candidate
from backend.app.services.pac_allocator.models import CandidateActionVector, CandidateDecision, ExactExposure
from backend.app.services.pac_allocator.proof import conclude_without_proof
from backend.app.services.pac_allocator.solver import solve_policy_program
from backend.test_scripts.test_services.test_pac_planner_evaluator import PROVENANCE_ID, R
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

    Shares one ``_SequenceAllocator`` across the funding/FX/order builders so
    the produced sequences obey the schema's cross-section uniqueness and
    per-section ordering rules.
    """
    allocator = sequence or PR._SequenceAllocator()
    return PacIncumbentSolution(
        solution_id="solution:primary",
        solution_kind="primary",
        validation="decimal_verified",
        asset_rows=PR.build_asset_rows(scenario, evaluation),
        funding_actions=PR.build_funding_actions(scenario, evaluation, allocator),
        fx_actions=PR.build_fx_actions(scenario, evaluation, allocator),
        order_rows=PR.build_order_rows(scenario, evaluation, allocator),
        ledger_rows=PR.build_ledger_rows(evaluation),
        exposure_rows=PR.build_exposure_rows(scenario, evaluation),
        accounting=PR.build_accounting(scenario, evaluation),
        costs=PR.build_costs(scenario, evaluation),
        objectives=PR.build_objective_results(scenario, view, evaluation),
    )


def _referenced_provenance_ids(solution: PacIncumbentSolution) -> set[str]:
    rows = [*solution.funding_actions, *solution.fx_actions, *solution.order_rows, *solution.exposure_rows]
    return {provenance_id for row in rows for provenance_id in row.provenance_ids}


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


# --------------------------------------------------------------------------
# Cross-section sequence allocation — two properties at once
# --------------------------------------------------------------------------


def test_cross_section_sequences_are_globally_unique_and_densely_shared() -> None:
    """A single shared ``_SequenceAllocator`` across the funding/FX/order
    sections yields globally-unique sequences that are dense from one.

    Density is what distinguishes the shared allocator from three per-section
    counters: three counters would each start at one and collide on row one,
    producing ``[1, 1, 1]``; the shared allocator produces a contiguous
    ``[1, 2, ..., n]``. The coarse funding+FX+buy scenario exercises all three
    sections at once.
    """
    scenario = _coarse_funding_fx_scenario()
    view, evaluation = _evaluate(scenario)
    allocator = PR._SequenceAllocator()
    funding = PR.build_funding_actions(scenario, evaluation, allocator)
    fx = PR.build_fx_actions(scenario, evaluation, allocator)
    orders = PR.build_order_rows(scenario, evaluation, allocator)

    # All three sections are genuinely populated, so the cross-section rule has
    # something to prove.
    assert funding and fx and orders

    sequences = [row.sequence for row in (*funding, *fx, *orders)]
    assert len(sequences) == len(set(sequences)), "sequences collide across sections"
    assert sorted(sequences) == list(range(1, len(sequences) + 1)), "sequences are not the dense range a shared allocator produces"


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
    fx = PR.build_fx_actions(scenario, evaluation, allocator)
    orders = PR.build_order_rows(scenario, evaluation, allocator)

    assert len(orders) >= 2, "need a multi-row section for a non-vacuous ordering check"
    for section in (funding, fx, orders):
        section_sequences = [row.sequence for row in section]
        assert section_sequences == sorted(section_sequences)


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
    be meaningless. The end-to-end assertions (containment, residual present,
    tie filter, sequence uniqueness, closed accounting identity) all read
    their counts off the live objects.
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
        proof=NotProvenProof(kind="not_proven", reason_code=conclude_without_proof(result).reason_code),
        primary_solution=solution,
        deployment=DeploymentUnavailable(kind="unavailable", reason_code="allocation.deployment_omitted"),
    )

    # The uncategorised residual survived into the published solution.
    assert any(row.category_id == PR.UNCATEGORISED_EXPOSURE_CATEGORY_ID for row in full.primary_solution.exposure_rows)

    # Tie stages filtered; counts read off the live objects.
    assert len(full.solver_evidence.stages) == len(view.objectives)
    assert all(not stage.objective_code.startswith("tie") for stage in full.solver_evidence.stages)
    assert len(result.stages) > len(full.solver_evidence.stages)

    # Sequences globally unique across the action sections.
    sequences = [row.sequence for row in (*full.primary_solution.funding_actions, *full.primary_solution.fx_actions, *full.primary_solution.order_rows)]
    assert len(sequences) == len(set(sequences))

    # The accounting identity closes exactly.
    assert _exact_fraction(full.primary_solution.accounting.identity_delta.value) == Fraction(0)
