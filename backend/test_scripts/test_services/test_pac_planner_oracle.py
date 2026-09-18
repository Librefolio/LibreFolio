"""Contract tests for the zero-SCIP-dependency exhaustive PAC/Rebalancer oracle.

All scenarios are small, pure, in-memory witnesses built by hand (mostly by
reusing the frozen-record fixture helpers from
`test_pac_planner_evaluator.py`, its sibling suite). Nothing here touches
the database, server, clock, or network, and `oracle.py` itself is treated
as frozen: every assertion below is a read of its behaviour, never a patch
around it.

`run_exhaustive_oracle` explicitly promises to never re-derive feasibility
or objective values itself — it only replays `evaluate_exact_candidate`,
already exercised in full by the sibling suite, and then searches/compares.
So the tests here are deliberately not about re-proving the evaluator's
accounting; they are about the oracle's own three jobs: (1) enumerating
the right domain, (2) picking the lexicographically-best feasible
candidate out of it without silently re-deriving anything, and (3)
refusing to enumerate a domain that is too large rather than truncating it
silently.

Item 1's "exhaustive equality" test in particular builds its own
independent oracle-of-the-oracle: it collects every candidate's
`evaluate_exact_candidate` result itself and computes the expected
lexicographic best with its own, differently-written comparison — it does
not import or reuse `oracle.py`'s private `_lexicographic_key`.

Several monetary/FX fixtures in the sibling suite (e.g. `_funding_fx_scenario`)
use a `CENT` currency quantum and blow up combinatorially fast once funding
and FX decisions are free at the same time (`estimate_oracle_domain_size`
reaches roughly 1.2 billion for that one fixture) — exactly the case
`OracleDomainTooLargeError` exists to refuse. Any fixture below that needs
`run_exhaustive_oracle` to actually *finish* therefore uses a coarse,
whole-currency-unit quantum and small route caps to keep the domain in the
tens/low-hundreds, so the suite stays fast and deterministic.
"""

from __future__ import annotations

import time
from dataclasses import replace
from types import SimpleNamespace
from typing import Callable

import pytest

from backend.app.services.pac_allocator.evaluator import (
    ExactEvaluatorError,
    build_exact_policy_view,
    evaluate_exact_candidate,
    exact_decision_id,
)
from backend.app.services.pac_allocator.models import DecisionAccess, ExactPlannerScenario
from backend.app.services.pac_allocator.oracle import (
    MAX_EXHAUSTIVE_ORACLE_CANDIDATES,
    OracleDomainTooLargeError,
    estimate_oracle_domain_size,
    run_exhaustive_oracle,
)
from backend.test_scripts.test_services.test_pac_planner_evaluator import (
    ONE,
    ZERO,
    R,
    _asset,
    _broker,
    _candidate,
    _capability,
    _cash,
    _decision,
    _fee,
    _funding_fx_scenario,
    _funding_route,
    _fx_rate,
    _invest_and_sell_scenario,
    _invest_only_baseline,
    _min_fragmentation_scenario,
    _order_route,
    _pac_scenario,
    _scenario,
    _sell_extension,
)

# --------------------------------------------------------------------------
# Local scenario fixtures
# --------------------------------------------------------------------------


def _two_asset_pac_scenario() -> ExactPlannerScenario:
    """Two independent buy routes, each capped at 3 quanta (4 values: 0-3).

    Gives a small (16-candidate) but genuinely two-dimensional domain: one
    decision alone would not exercise the cartesian-product enumeration or
    give the lexicographic tie-break vector more than one component.
    """
    capability = _capability("capability:a")
    fee = _fee("fee:buy:a", capability.capability_id, "buy")
    broker = _broker("broker:a", (capability,), (fee,))
    return _scenario(
        "scenario:two-asset",
        product="pac",
        policy="proportional",
        assets=(
            _asset("asset:a", price=R(10)),
            _asset("asset:b", price=R(20)),
        ),
        brokers=(broker,),
        existing_cash=(_cash("cash:a", "broker:a", R(100)),),
        order_routes=(
            _order_route(
                "route:buy:a",
                broker_id="broker:a",
                asset_id="asset:a",
                capability=capability,
                fee_id=fee.fee_schedule_id,
                side="buy",
                cap=R(3),
                priority=1,
            ),
            _order_route(
                "route:buy:b",
                broker_id="broker:a",
                asset_id="asset:b",
                capability=capability,
                fee_id=fee.fee_schedule_id,
                side="buy",
                cap=R(3),
                priority=2,
            ),
        ),
    )


def _coarse_funding_fx_scenario() -> ExactPlannerScenario:
    """A funding+FX+buy scenario shaped like the sibling suite's
    `_funding_fx_scenario`, but deliberately detuned to keep the domain
    small: a whole-currency-unit quantum (`ONE`, not `CENT`) and a cheaper
    asset so the buy decision is not clamped to a single value by the
    resource constraint.

    `_funding_fx_scenario` itself has `estimate_oracle_domain_size` in the
    ~1.2 billion range (see the module docstring) precisely because it
    uses a cent quantum over ~200 currency units of funding/FX headroom;
    this local variant keeps the same three free decision families
    (funding_transfer, fx_debit, buy_quantum) but at a domain small enough
    to actually enumerate in a test.
    """
    capability = _capability("capability:usd")
    buy_fee = _fee("fee:buy:usd", capability.capability_id, "buy", currency="USD")
    destination = _broker("broker:destination", (capability,), (buy_fee,))
    source = _broker("broker:source")
    return _scenario(
        "scenario:coarse-funding-fx",
        product="pac",
        policy="proportional",
        assets=(_asset("asset:a", price=R(5), currency="USD"),),
        brokers=(destination, source),
        existing_cash=(_cash("cash:source", source.broker_id, R(12)),),
        funding_routes=(
            _funding_route(
                "route:funding:eur",
                broker_id=destination.broker_id,
                source_kind="existing_cash",
                source_id="cash:source",
                amount=R(12),
                priority=2,
            ),
        ),
        order_routes=(
            _order_route(
                "route:buy:usd",
                broker_id=destination.broker_id,
                asset_id="asset:a",
                capability=capability,
                fee_id=buy_fee.fee_schedule_id,
                side="buy",
                cap=R(2),
                priority=5,
            ),
        ),
        fx_rates=(_fx_rate("EUR", "USD", R(6, 5)),),
        fx_spread_rate=R(1, 100),
        currency_quantums=(("EUR", ONE), ("USD", ONE)),
    )


# --------------------------------------------------------------------------
# Local small helpers
# --------------------------------------------------------------------------


def _fake_view(*decisions: DecisionAccess) -> SimpleNamespace:
    """A minimal duck-typed stand-in for `ExactPolicyView`.

    `estimate_oracle_domain_size` only ever reads `view.decisions` (it is
    the only attribute it accesses; see `oracle.py`), so item 8's
    domain-size unit tests can probe `DecisionAccess` combinations
    directly without paying for a full scenario/view build.
    """
    return SimpleNamespace(decisions=tuple(decisions))


class _Cancelled(RuntimeError):
    """Local cooperative-cancellation sentinel for the checkpoint tests."""


class _CountingCheckpoint:
    """Records how many times it was called; never raises."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1


class _RaiseAfterCheckpoint:
    """Raises `_Cancelled` once it has been called more than `trigger_after` times."""

    def __init__(self, trigger_after: int) -> None:
        self.trigger_after = trigger_after
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1
        if self.calls > self.trigger_after:
            raise _Cancelled(f"cancelled after {self.calls} checkpoint call(s)")


def _unsafe_frozen_exact_access_missing_frozen_quanta() -> DecisionAccess:
    """Build a `frozen_exact` `DecisionAccess` with `frozen_quanta=None`.

    `DecisionAccess.__post_init__` (via `_validate_decision_mode`) forbids
    exactly this combination for any normally-constructed instance, so the
    only way to reach it is to bypass `__init__`/`__post_init__` the same
    way the sibling suite's own `_unsafe_candidate_decision` does. This
    exists to exercise `oracle.py`'s defensive
    `if access.frozen_quanta is None: raise OracleDomainTooLargeError(...)`
    branch, which is otherwise dead code reachable only through malformed
    data (see the "surprising finding" reported alongside this suite).
    """
    access = object.__new__(DecisionAccess)
    object.__setattr__(access, "decision_id", "funding:route:unsafe")
    object.__setattr__(access, "family", "funding_transfer")
    object.__setattr__(access, "mode", "frozen_exact")
    object.__setattr__(access, "entity_refs", ())
    object.__setattr__(access, "lower_quanta", 0)
    object.__setattr__(access, "upper_quanta", 100)
    object.__setattr__(access, "baseline_quanta", 0)
    object.__setattr__(access, "frozen_quanta", None)
    return access


# --------------------------------------------------------------------------
# Public API surface: constant + error taxonomy (bonus, ties to the task's
# "Public API surface to test" list)
# --------------------------------------------------------------------------


def test_oracle_public_constant_and_error_taxonomy_are_stable() -> None:
    assert MAX_EXHAUSTIVE_ORACLE_CANDIDATES == 200_000
    assert issubclass(OracleDomainTooLargeError, ExactEvaluatorError)


# --------------------------------------------------------------------------
# Item 8: estimate_oracle_domain_size, hand-built DecisionAccess combinations
# --------------------------------------------------------------------------


def test_estimate_oracle_domain_size_disabled_contributes_one() -> None:
    disabled = DecisionAccess(
        decision_id="disabled",
        family="buy_quantum",
        mode="disabled",
        entity_refs=(),
        lower_quanta=0,
        upper_quanta=0,
        baseline_quanta=0,
        frozen_quanta=None,
    )
    assert estimate_oracle_domain_size(_fake_view(disabled)) == 1


def test_estimate_oracle_domain_size_frozen_exact_contributes_one_regardless_of_bounds() -> None:
    # upper_quanta (2000) is far wider than the single frozen point (777):
    # a frozen_exact decision must contribute exactly one value, never the
    # naive upper-lower+1 span.
    frozen = DecisionAccess(
        decision_id="frozen",
        family="funding_transfer",
        mode="frozen_exact",
        entity_refs=(),
        lower_quanta=0,
        upper_quanta=2000,
        baseline_quanta=777,
        frozen_quanta=777,
    )
    assert estimate_oracle_domain_size(_fake_view(frozen)) == 1


def test_estimate_oracle_domain_size_mutable_is_upper_minus_lower_plus_one() -> None:
    mutable = DecisionAccess(
        decision_id="mutable",
        family="buy_quantum",
        mode="mutable",
        entity_refs=(),
        lower_quanta=0,
        upper_quanta=4,
        baseline_quanta=0,
        frozen_quanta=None,
    )
    assert estimate_oracle_domain_size(_fake_view(mutable)) == 5


def test_estimate_oracle_domain_size_additive_only_is_upper_minus_lower_plus_one() -> None:
    additive_only = DecisionAccess(
        decision_id="additive",
        family="buy_quantum",
        mode="additive_only",
        entity_refs=(),
        lower_quanta=2,
        upper_quanta=6,
        baseline_quanta=2,
        frozen_quanta=None,
    )
    assert estimate_oracle_domain_size(_fake_view(additive_only)) == 5


def test_estimate_oracle_domain_size_is_the_product_across_decisions() -> None:
    disabled = DecisionAccess(
        decision_id="disabled",
        family="buy_quantum",
        mode="disabled",
        entity_refs=(),
        lower_quanta=0,
        upper_quanta=0,
        baseline_quanta=0,
        frozen_quanta=None,
    )
    frozen = DecisionAccess(
        decision_id="frozen",
        family="funding_transfer",
        mode="frozen_exact",
        entity_refs=(),
        lower_quanta=0,
        upper_quanta=2000,
        baseline_quanta=777,
        frozen_quanta=777,
    )
    mutable = DecisionAccess(
        decision_id="mutable",
        family="buy_quantum",
        mode="mutable",
        entity_refs=(),
        lower_quanta=0,
        upper_quanta=4,
        baseline_quanta=0,
        frozen_quanta=None,
    )
    additive_only = DecisionAccess(
        decision_id="additive",
        family="buy_quantum",
        mode="additive_only",
        entity_refs=(),
        lower_quanta=2,
        upper_quanta=6,
        baseline_quanta=2,
        frozen_quanta=None,
    )
    # 1 (disabled) * 1 (frozen_exact) * 5 (mutable 0-4) * 5 (additive_only 2-6)
    assert estimate_oracle_domain_size(_fake_view(disabled, frozen, mutable, additive_only)) == 25


# --------------------------------------------------------------------------
# Item 2: objective ordering contract
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "build_scenario",
    [_pac_scenario, _min_fragmentation_scenario],
    ids=["proportional", "min_fragmentation"],
)
def test_objective_codes_match_view_objectives_sorted_by_ascending_ordinal(
    build_scenario: Callable[[], ExactPlannerScenario],
) -> None:
    """`result.objective_codes` must equal `view.objectives` sorted by
    ordinal — built from the view itself, never a hardcoded cascade
    string, so this stays correct if ordinals are ever renumbered.

    Parametrized across two different PAC policies (different cascades,
    different lengths) so the "sorted by ordinal" claim is not an
    accident of one particular objective list.
    """
    scenario = build_scenario()
    view = build_exact_policy_view(scenario)
    expected = tuple(objective.code for objective in sorted(view.objectives, key=lambda objective: objective.ordinal))
    result = run_exhaustive_oracle(scenario, view)
    assert result.objective_codes == expected


def test_pac_proportional_cascade_matches_documented_contract() -> None:
    """The PAC `proportional` cascade is a real, specific product contract
    (`plan-phase00PacRebalancerPolicies.prompt.md` §5-6), so unlike the
    test above, this one is allowed to hardcode it.
    """
    scenario = _pac_scenario()
    view = build_exact_policy_view(scenario)
    result = run_exhaustive_oracle(scenario, view)
    assert result.objective_codes == (
        "fixed_l2",
        "shortfall",
        "route_priority",
        "explicit_cost",
        "active_order_rows",
    )


# --------------------------------------------------------------------------
# Item 1: exhaustive equality, non-circular (independent oracle-of-the-oracle)
# --------------------------------------------------------------------------


def test_exhaustive_equality_matches_independent_lexicographic_scan() -> None:
    """Collect every candidate's evaluation independently (not via
    `run_exhaustive_oracle`), compute the expected lexicographic best with
    a differently-written comparison, and assert the oracle agrees.

    This intentionally does not import or call `oracle.py`'s private
    `_lexicographic_key`/`_ordered_objective_refs` — the sort key below is
    a separate implementation, so a bug shared between the module and a
    naive copy of its own logic could not hide from this test.
    """
    scenario = _two_asset_pac_scenario()
    view = build_exact_policy_view(scenario)
    decision_a = exact_decision_id("buy_quantum", "route:buy:a")
    decision_b = exact_decision_id("buy_quantum", "route:buy:b")

    # Independently enumerate the full 4x4 domain by hand.
    manual_evaluations = []
    for quanta_a in range(0, 4):
        for quanta_b in range(0, 4):
            candidate = _candidate(
                view,
                {decision_a: quanta_a, decision_b: quanta_b},
                candidate_id=f"manual:{quanta_a}:{quanta_b}",
            )
            evaluation = evaluate_exact_candidate(scenario, view, candidate)
            manual_evaluations.append((candidate, evaluation))

    feasible = [(candidate, evaluation) for candidate, evaluation in manual_evaluations if evaluation.feasible]
    assert len(manual_evaluations) == 16
    assert len(feasible) == 16  # every combination is feasible for this scenario

    ordered_ref_ids = tuple(objective.ref_id for objective in sorted(view.objectives, key=lambda objective: objective.ordinal))

    def independent_sort_key(item: tuple[object, object]) -> tuple[tuple, tuple[int, ...]]:
        _candidate_obj, evaluation = item
        values_by_ref_id = {objective.ref_id: objective.value for objective in evaluation.objectives}
        stage_values = tuple(values_by_ref_id[ref_id] for ref_id in ordered_ref_ids)
        return stage_values, evaluation.canonical_tie_quanta

    best_candidate, best_evaluation = min(feasible, key=independent_sort_key)

    result = run_exhaustive_oracle(scenario, view)
    assert result.enumerated_candidates == 16
    assert result.feasible_candidates == 16
    assert result.best_candidate is not None
    assert result.best_evaluation is not None

    expected_quanta = {decision.decision_id: decision.quanta for decision in best_candidate.decisions}
    actual_quanta = {decision.decision_id: decision.quanta for decision in result.best_candidate.decisions}
    assert actual_quanta == expected_quanta

    # Byte-identical frozen-dataclass equality once candidate_id (which
    # legitimately differs between a hand-built and an oracle-built
    # candidate) is normalized away.
    assert replace(result.best_evaluation, candidate_id="normalized") == replace(best_evaluation, candidate_id="normalized")


# --------------------------------------------------------------------------
# Item 4: domain-too-large
# --------------------------------------------------------------------------


def test_domain_too_large_raises_fast_for_the_funding_fx_scenario_at_default_cap() -> None:
    """The sibling suite's own `_funding_fx_scenario` (cent quantum, free
    funding+FX) has a domain in the ~1.2 billion range — the empirical
    finding this whole suite's coarse fixtures exist to avoid. At the
    default cap, `run_exhaustive_oracle` must refuse it instead of
    enumerating, and must do so fast (it can only be fast if the check
    happens before entering the cartesian-product loop).
    """
    scenario = _funding_fx_scenario()
    view = build_exact_policy_view(scenario)
    domain_size = estimate_oracle_domain_size(view)
    assert domain_size > MAX_EXHAUSTIVE_ORACLE_CANDIDATES
    assert domain_size > 1_000_000_000  # order-of-magnitude check on the ~1.2B empirical finding

    started_at = time.monotonic()
    with pytest.raises(OracleDomainTooLargeError):
        run_exhaustive_oracle(scenario, view)
    elapsed = time.monotonic() - started_at
    assert elapsed < 1.0, "the domain-size cap must be checked before enumeration, not discovered by exhausting it"


def test_domain_too_large_boundary_at_exact_candidate_count() -> None:
    """`max_candidates == domain_size` must succeed; `domain_size - 1` must raise."""
    scenario = _two_asset_pac_scenario()
    view = build_exact_policy_view(scenario)
    domain_size = estimate_oracle_domain_size(view)
    assert domain_size == 16

    result = run_exhaustive_oracle(scenario, view, max_candidates=domain_size)
    assert result.enumerated_candidates == domain_size

    with pytest.raises(OracleDomainTooLargeError):
        run_exhaustive_oracle(scenario, view, max_candidates=domain_size - 1)


# --------------------------------------------------------------------------
# Item 3: multi-decision composition (funding_transfer + fx_debit + buy_quantum)
# --------------------------------------------------------------------------


def test_multi_decision_composition_ties_are_full_length_and_best_is_never_rederived() -> None:
    scenario = _coarse_funding_fx_scenario()
    view = build_exact_policy_view(scenario)

    families = {decision.family for decision in view.decisions}
    assert families == {"funding_transfer", "fx_debit", "buy_quantum"}
    assert all(decision.mode == "mutable" for decision in view.decisions)

    domain_size = estimate_oracle_domain_size(view)
    assert domain_size == 585  # small enough to run in a fraction of a second

    result = run_exhaustive_oracle(scenario, view)
    assert result.enumerated_candidates == domain_size
    assert result.feasible_candidates > 0
    assert result.best_candidate is not None
    assert result.best_evaluation is not None

    # canonical_tie_quanta must be a full permutation of every decision's
    # quanta, for every candidate replayed against this view - not just
    # for the winner.
    zero_candidate = _candidate(view, {}, candidate_id="all-zero")
    upper_candidate = _candidate(
        view,
        {decision.decision_id: decision.upper_quanta for decision in view.decisions},
        candidate_id="all-upper",
    )
    for candidate in (zero_candidate, upper_candidate):
        evaluation = evaluate_exact_candidate(scenario, view, candidate)
        assert len(evaluation.canonical_tie_quanta) == len(view.decisions)
    assert len(result.best_evaluation.canonical_tie_quanta) == len(view.decisions)

    # "Never re-derive": replaying the oracle's own winner through a fresh,
    # direct evaluate_exact_candidate call must reproduce best_evaluation
    # byte-for-byte (same candidate object, so no normalization needed).
    fresh_replay = evaluate_exact_candidate(scenario, view, result.best_candidate)
    assert fresh_replay == result.best_evaluation


# --------------------------------------------------------------------------
# Item 5: no-op
# --------------------------------------------------------------------------


def test_no_op_scenario_best_candidate_is_all_zero() -> None:
    """Zero cash means the one buy decision's upper bound collapses to
    zero: the only feasible candidate is the all-zero one, and the domain
    is tiny enough that reaching this result can never trip
    `OracleDomainTooLargeError`.
    """
    scenario = _pac_scenario(cash=ZERO)
    view = build_exact_policy_view(scenario)
    assert len(view.decisions) == 1
    (only_decision,) = view.decisions
    assert only_decision.upper_quanta == 0

    domain_size = estimate_oracle_domain_size(view)
    assert domain_size == 1

    result = run_exhaustive_oracle(scenario, view)  # must not raise OracleDomainTooLargeError
    assert result.enumerated_candidates == 1
    assert result.feasible_candidates >= 1
    assert result.best_candidate is not None
    assert result.best_evaluation is not None
    assert result.best_evaluation.feasible is True

    for decision in result.best_candidate.decisions:
        access = _decision(view, decision.decision_id)
        assert decision.quanta == 0
        assert decision.quanta == access.baseline_quanta


# --------------------------------------------------------------------------
# Item 6: infeasible-exact (real research, not fabricated)
# --------------------------------------------------------------------------


def test_infeasible_exact_required_minimum_above_reachable_cap_rejects_every_candidate() -> None:
    """Research question: can a PAC-`proportional` *primary* view ever be
    exhaustively infeasible — i.e. is the all-zero/baseline candidate
    always trivially feasible?

    Answer: **no, it is not always trivially feasible.** `ORDER_REQUIRED_MIN`
    (see `evaluator.py::_order_route_constraint_facts`) is a hard floor on
    `measure = step * quanta` that, for a *buy* route on a `primary` view,
    is **not** relaxed to zero the way it is for sell-side routes on
    `primary`/`invest_only_baseline` purposes, and it is **not** gated by
    "is this decision active" the way `ORDER_MIN_IF_ACTIVE` is. So setting
    a route's `required_minimum` above the maximum measure the route can
    ever reach (its cap, here 3 quanta at a step of 1 = a measure of 3)
    makes every candidate in the domain infeasible, including zero -
    this is a genuine, reproducible construction, not a fabricated one:
    it reuses the exact same `_pac_scenario(required=..., route_cap=...)`
    knobs the sibling suite's own
    `test_order_minimum_required_and_cap_contracts` already exercises.
    """
    scenario = _pac_scenario(required=R(5), route_cap=R(3))
    view = build_exact_policy_view(scenario)
    assert view.purpose == "primary"
    assert scenario.policy == "proportional"
    assert len(view.decisions) == 1
    (only_decision,) = view.decisions
    assert only_decision.lower_quanta == 0
    assert only_decision.upper_quanta == 3

    domain_size = estimate_oracle_domain_size(view)
    assert domain_size == 4

    # Confirm, by direct replay, that every single candidate in the domain
    # (including the all-zero one) fails specifically because of
    # ORDER_REQUIRED_MIN - not some unrelated, incidental conflict.
    for quanta in range(0, 4):
        candidate = _candidate(view, {only_decision.decision_id: quanta}, candidate_id=f"manual:{quanta}")
        evaluation = evaluate_exact_candidate(scenario, view, candidate)
        assert evaluation.feasible is False
        assert "ORDER_REQUIRED_MIN" in evaluation.conflict_codes

    result = run_exhaustive_oracle(scenario, view)
    assert result.enumerated_candidates == 4
    assert result.feasible_candidates == 0
    assert result.best_candidate is None
    assert result.best_evaluation is None


# --------------------------------------------------------------------------
# Item 7: checkpoint threading
# --------------------------------------------------------------------------


def test_checkpoint_is_invoked_repeatedly_during_enumeration() -> None:
    scenario = _pac_scenario()
    view = build_exact_policy_view(scenario)
    checkpoint = _CountingCheckpoint()

    result = run_exhaustive_oracle(scenario, view, checkpoint=checkpoint)

    assert checkpoint.calls > 0
    # At least the top-of-function check plus one check per enumerated
    # candidate: proves the checkpoint is threaded through the enumeration
    # loop itself, not just accepted and checked once at entry.
    assert checkpoint.calls >= result.enumerated_candidates + 1


def test_checkpoint_cancellation_before_enumeration_propagates() -> None:
    scenario = _pac_scenario()
    view = build_exact_policy_view(scenario)
    checkpoint = _RaiseAfterCheckpoint(trigger_after=0)  # raises on the very first call

    with pytest.raises(_Cancelled):
        run_exhaustive_oracle(scenario, view, checkpoint=checkpoint)
    assert checkpoint.calls == 1


def test_checkpoint_cancellation_during_candidate_evaluation_propagates() -> None:
    """Raising deep inside the first candidate's `evaluate_exact_candidate`
    replay (not just at the oracle's own top-of-function/per-candidate
    checks) must still propagate all the way out of
    `run_exhaustive_oracle` - there is no try/except anywhere in the
    module that could swallow it.
    """
    scenario = _pac_scenario()
    view = build_exact_policy_view(scenario)
    checkpoint = _RaiseAfterCheckpoint(trigger_after=2)

    with pytest.raises(_Cancelled):
        run_exhaustive_oracle(scenario, view, checkpoint=checkpoint)
    assert checkpoint.calls == 3


# --------------------------------------------------------------------------
# Optional: frozen_exact decision (one value, not upper-lower+1)
# --------------------------------------------------------------------------


def test_frozen_exact_decision_contributes_one_value_not_its_theoretical_range() -> None:
    """`build_exact_policy_view(..., purpose="sell_extension")` freezes the
    funding decision to whatever the baseline consumed (per its docstring).
    The frozen decision's `upper_quanta` is *not* clamped down to the
    frozen point (it keeps the bound the decision would have had if it
    were still mutable), so a naive `upper - lower + 1` calculation and
    the oracle's real per-decision count diverge sharply here - this is
    exactly the gap `_decision_value_range`'s `frozen_exact` branch exists
    to close.

    The full `run_exhaustive_oracle` enumeration for this fixture (domain
    891) takes a couple of seconds, so this test only exercises
    `estimate_oracle_domain_size` — cheap, precise, and sufficient to
    prove the one-value-not-a-range contract.
    """
    scenario = _invest_and_sell_scenario()
    _baseline_view, baseline_candidate = _invest_only_baseline(scenario)
    sell_view = _sell_extension(scenario, baseline_candidate)

    funding_decision_id = exact_decision_id("funding_transfer", "route:funding")
    frozen_access = _decision(sell_view, funding_decision_id)
    assert frozen_access.mode == "frozen_exact"
    assert frozen_access.frozen_quanta is not None

    naive_span = frozen_access.upper_quanta - frozen_access.lower_quanta + 1
    real_contribution = estimate_oracle_domain_size(_fake_view(frozen_access))
    assert real_contribution == 1
    assert naive_span > 1  # the whole point: naive span and real contribution disagree
    assert naive_span != real_contribution


def test_frozen_exact_with_missing_frozen_quanta_is_unreachable_via_valid_construction() -> None:
    """`oracle.py`'s `_decision_value_range` defensively raises
    `OracleDomainTooLargeError` if a `frozen_exact` decision has
    `frozen_quanta is None`. `DecisionAccess.__post_init__` already
    forbids constructing exactly that combination normally, so this
    branch is dead code in production - reachable here only via the same
    `object.__new__`/`object.__setattr__` bypass the sibling suite uses
    for its own "unsafe" fixtures. See the surprising-finding note
    reported alongside this suite.
    """
    unsafe = _unsafe_frozen_exact_access_missing_frozen_quanta()
    with pytest.raises(OracleDomainTooLargeError, match="missing frozen_quanta"):
        estimate_oracle_domain_size(_fake_view(unsafe))
