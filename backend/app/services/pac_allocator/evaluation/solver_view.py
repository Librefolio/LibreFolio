"""A plan's objectives «as the solver sees it» (row 6 of lot CR, project 67; specification §16.6–16.7).

The Rebalancer's model keeps money continuous: a buy's cost, its fee and a conversion's credit are their exact amounts, each
less the reserve the posting keeps back for its rounding (``posting_reserve``). The exact replay posts every amount rounded
against the plan, and its objectives are the ones the result publishes. The two differ by a few cents by construction.

The solver's cascade compares SCIP's numbers with exact ones: the pins of the stages, D4's «no worse before a tie-break» and
the bound check (``solver._exact_stage_values``). Those comparisons read this value: the replay's own postings, each taken
at its exact amount less its reserve instead of its posted amount, through the same score formula
(``facts.rebalancer_score_of``), in exact arithmetic. On the same plan it equals SCIP's value, so every rule of the cascade
stays exact. Nothing here is published.

The PAC keeps its rounded postings in the model, so its view is the replay's own objectives.
"""

from __future__ import annotations

from collections import defaultdict

from backend.app.services.pac_allocator.evaluation.facts import rebalancer_score_of
from backend.app.services.pac_allocator.evaluation.limits import plan_reference
from backend.app.services.pac_allocator.evaluation.scenario import build_scenario_index, to_valuation
from backend.app.services.pac_allocator.models import ExactEvaluation, ExactObjectiveCode, ExactPlannerScenario, ExactPolicyView
from backend.app.services.pac_allocator.numeric import ExactRatio
from backend.app.services.pac_allocator.posting_reserve import RESERVED_FAMILIES, posting_reserves

_EXACT_ZERO = ExactRatio(0)


def solver_view_objectives(scenario: ExactPlannerScenario, view: ExactPolicyView, evaluation: ExactEvaluation) -> dict[ExactObjectiveCode, ExactRatio]:
    """Every objective of ``view`` on the evaluated plan, the Rebalancer's money ones as the solver sees them.

    A posting that happens (its exact amount positive) is a debit taken out at ``exact + reserve`` or a credit coming in at
    ``exact − reserve``, instead of its posted amount; its reserve is ``posting_reserves``'s, zero where it cannot round.
    The difference moves its cell's final cash, and with it the cash items' residuals, the uninvested ``N`` and the final
    wealth ``W``; the Assets do not move.
    """
    by_ref = {item.ref_id: item.value for item in evaluation.objectives}
    values = {ref.code: by_ref[ref.ref_id] for ref in view.objectives}
    if scenario.product != "rebalancer" or evaluation.accounting is None:
        return values
    index = build_scenario_index(scenario)
    reserves = posting_reserves(scenario)
    moved: dict[tuple[str, str], ExactRatio] = defaultdict(lambda: _EXACT_ZERO)
    for posting in evaluation.postings:
        if posting.family not in RESERVED_FAMILIES or posting.exact_amount <= _EXACT_ZERO:
            continue
        reserve = reserves.get(posting.posting_id, _EXACT_ZERO)
        if posting.direction == "credit":
            seen = posting.exact_amount - reserve - posting.posted_amount
        else:
            seen = posting.posted_amount - posting.exact_amount - reserve
        moved[(posting.broker_id, posting.currency)] += to_valuation(index, seen, posting.currency)
    accounting = evaluation.accounting
    targeted = sum((moved[(row.broker_id, row.currency)] for row in evaluation.cash_targets), _EXACT_ZERO)
    residuals = (*(item.residual for item in evaluation.assets), *(row.residual + moved[(row.broker_id, row.currency)] for row in evaluation.cash_targets))
    wealth_loss = accounting.wealth_loss - sum(moved.values(), _EXACT_ZERO)
    seen = rebalancer_score_of(scenario.target_fidelity, residuals, uninvested=accounting.uninvested - targeted, wealth_loss=wealth_loss, reference=plan_reference(scenario, accounting))
    return values | {code: value for code, value in seen.items() if code in values}
