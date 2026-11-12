"""Limits on entries (V5, A3 of project 67): resolving them, and the three checks before the calculation.

An entry is an Asset or a cash cell (Broker and currency). Each can carry a minimum and a maximum on its final value, as an
amount in the valuation currency or as a share of the Tool's reference (decisioni M17); in the PAC the reference is the money
the plan can reach, ``accounting.fixed_reference`` (specification §15 n. 17, D7).

Everything here is pure arithmetic on the exact scenario and answers with the entries it names, never with text:

* ``resolve_scenario_limits`` turns every limit into an amount against a reference;
* ``check_minimum_above_maximum``, ``check_minimums_exceed_reference`` and ``check_maximum_below_current`` are the three checks
  of M1, each returning ``LimitProblem`` rows that say which entries are the cause (T12). The public issue codes and the
  request fields come with contract 2.0.0 (A4): the ``code`` strings here are the names that A4 will publish;
* ``limited_entries`` lists every entry that carries a limit, for the planner's «no solution» rule after the calculation (M20).

``pa/normalize.py`` is not touched: it already has more than a thousand lines.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from backend.app.services.pac_allocator.evaluation.evaluator import build_exact_policy_view, evaluate_exact_candidate
from backend.app.services.pac_allocator.evaluation.limits import LimitEntry, ResolvedBounds, ResolvedLimits, entries_with_limits, limited_entries, resolve_limit, resolve_scenario_limits
from backend.app.services.pac_allocator.evaluation.scenario import ScenarioIndex, to_valuation
from backend.app.services.pac_allocator.models import CandidateActionVector, CandidateDecision, ExactPlannerScenario
from backend.app.services.pac_allocator.numeric import ExactRatio

__all__ = [
    "LimitEntry",
    "LimitProblem",
    "ResolvedBounds",
    "ResolvedLimits",
    "check_maximum_below_current",
    "check_minimum_above_maximum",
    "check_minimums_exceed_reference",
    "fixed_reference_of",
    "limited_entries",
    "resolve_limit",
    "resolve_scenario_limits",
]

type ProblemCode = Literal["bound_min_above_max", "bounds_min_sum_exceeds_reference", "bound_max_below_current"]


@dataclass(frozen=True, slots=True)
class LimitProblem:
    """A check that failed and the entries that cause it, in the order of ``LimitEntry.key``."""

    code: ProblemCode
    entries: tuple[LimitEntry, ...]


def fixed_reference_of(scenario: ExactPlannerScenario) -> ExactRatio:
    """The reference of the PAC, ``accounting.fixed_reference``, read off the do-nothing plan's exact replay.

    It does not depend on any decision (specification §15 n. 17): the money already invested plus the funding the plan can
    reach, so the do-nothing candidate gives it whatever the limits say.
    """
    view = build_exact_policy_view(scenario, purpose="primary")
    candidate = CandidateActionVector(
        view_id=view.view_id,
        candidate_id="limits:reference",
        decisions=tuple(CandidateDecision(decision_id=access.decision_id, quanta=access.frozen_quanta if access.mode == "frozen_exact" else access.baseline_quanta) for access in view.decisions),
    )
    evaluation = evaluate_exact_candidate(scenario, view, candidate)
    if evaluation.accounting is None:
        raise ValueError("the do-nothing plan was refused by the candidate contract: the reference is unknown")
    return evaluation.accounting.fixed_reference


def check_minimum_above_maximum(scenario: ExactPlannerScenario, reference: ExactRatio) -> tuple[LimitProblem, ...]:
    """Check 1 (M1): one problem per entry whose minimum exceeds its maximum, the two resolved against ``reference``."""
    problems = []
    for entry, minimum, maximum in entries_with_limits(scenario):
        low, high = resolve_limit(minimum, reference), resolve_limit(maximum, reference)
        if low is not None and high is not None and low > high:
            problems.append(LimitProblem("bound_min_above_max", (entry,)))
    return tuple(problems)


def check_minimums_exceed_reference(scenario: ExactPlannerScenario, reference: ExactRatio) -> tuple[LimitProblem, ...]:
    """Check 2 (M1, T12): the minimums of all entries, Assets and cash cells, add up to more than ``reference``.

    One problem naming every entry with a minimum, or none. The base is ``fixed_reference`` (D7), so that money which cannot
    reach a buy does not make the sum look smaller than the plan can honour.
    """
    named = [(entry, resolve_limit(minimum, reference)) for entry, minimum, _ in entries_with_limits(scenario) if minimum is not None]
    total = sum((value for _, value in named), ExactRatio(0))
    if total > reference:
        return (LimitProblem("bounds_min_sum_exceeds_reference", tuple(entry for entry, _ in named)),)
    return ()


def check_maximum_below_current(scenario: ExactPlannerScenario, index: ScenarioIndex, reference: ExactRatio) -> tuple[LimitProblem, ...]:
    """Check 3 (M1): an Asset's maximum is below what the plan already holds of it and sales are off.

    Holdings exist only outside the PAC (``ExactPlannerScenario`` refuses them there), so in a PAC this names nothing; it is
    here for the Rebalancer's «Invest only» (block B). Sales are off unless the policy is ``invest_and_sell``.
    """
    if scenario.policy == "invest_and_sell":
        return ()
    current_by_asset: dict[str, ExactRatio] = defaultdict(lambda: ExactRatio(0))
    for holding in scenario.holdings:
        asset = index.assets[holding.asset_id]
        unit = asset.quote.price.amount / asset.quote.quote_base_quantity
        current_by_asset[holding.asset_id] += to_valuation(index, holding.planning_quantity * unit, asset.quote.price.currency)
    problems = []
    for entry, _, maximum in entries_with_limits(scenario):
        high = resolve_limit(maximum, reference)
        if entry.kind == "asset" and high is not None and current_by_asset.get(entry.asset_id, ExactRatio(0)) > high:
            problems.append(LimitProblem("bound_max_below_current", (entry,)))
    return tuple(problems)
