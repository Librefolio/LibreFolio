"""The scenario preview of both Tools (contract §11, decisioni-REB §11.2; B4 of project 67).

The numbers the screen shows **before** a plan is computed, from the backend (N1): the total of the plan; for the Rebalancer
today's value and weight of every target entry and the table «maximum acceptable cost» with the λ of the three levels and,
for the «custom» fidelity, λ and its euros side by side. No optimizer runs. A preview that cannot count (a missing price or
rate, no holdings, a portfolio worth nothing) answers ``needs_input`` or ``invalid`` with the codes of ``plan``. Limits that
contradict each other or the portfolio do not stop it: it stays ready and names them in ``limit_problems``.

Its result states are ``preview_*``, so that one discriminated union per service carries both operations' results.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Annotated, Literal, Union

from pydantic import Field, TypeAdapter, model_validator

from backend.app.schemas.pac_allocator.base import AllocationStrictModel, CurrencyCode, PlannerId
from backend.app.schemas.pac_allocator.exact import ExactMoney, ExactNumber, exact_fraction, money_fraction
from backend.app.schemas.pac_allocator.issues import PlannerIssue
from backend.app.schemas.pac_allocator.request import PacPlannerRequest, RebalancerPlannerRequest
from backend.app.schemas.pac_allocator.results import (
    PacPlannerInvalidResult,
    PacPlannerNeedsInputResult,
    PacPlannerReadyIncumbentResult,
    PacPlannerReadyInfeasibleResult,
    PacPlannerReadyNoIncumbentResult,
    PacPlannerReadyNoOpResult,
    PacPlannerUnsupportedResult,
    PlannerResultSnapshot,
    RebalancerPlannerInvalidResult,
    RebalancerPlannerNeedsInputResult,
    RebalancerPlannerReadyIncumbentResult,
    RebalancerPlannerReadyInfeasibleResult,
    RebalancerPlannerReadyNoIncumbentResult,
    RebalancerPlannerReadyNoOpResult,
    RebalancerPlannerUnsupportedResult,
)
from backend.app.services.financial_math.acceptable_cost import max_acceptable_cost


class PreviewAssetItem(AllocationStrictModel):
    """An Asset's value today and its weight on the total ``F``."""

    kind: Literal["asset"]
    asset_id: PlannerId
    value: ExactMoney
    weight: ExactNumber


class PreviewCashItem(AllocationStrictModel):
    """A cash entry's spendable cash today and its weight on the total ``F``."""

    kind: Literal["cash"]
    broker_id: PlannerId
    currency: CurrencyCode
    value: ExactMoney
    weight: ExactNumber


type PreviewItem = Annotated[Union[PreviewAssetItem, PreviewCashItem], Field(discriminator="kind")]


class FidelityLevelWeights(AllocationStrictModel):
    """The distance weight λ of each fidelity level (specifica §6.3): the table's three columns."""

    cost_aware: ExactNumber
    balanced: ExactNumber
    faithful: ExactNumber


class AcceptableCostRow(AllocationStrictModel):
    """One row: misplaced money, and the most a plan accepts to spend to put it back, ``2·λ·d²/F``, per level; ``custom``
    only when the «custom» fidelity has a λ."""

    misplaced: ExactMoney
    reference: bool
    cost_aware: ExactMoney
    balanced: ExactMoney
    faithful: ExactMoney
    custom: ExactMoney | None


class AcceptableCostTable(AllocationStrictModel):
    """The table «maximum acceptable cost» (decisioni-REB §7.3): four rows, 1 %, 2.5 %, 5 % and 10 % of ``F`` to two
    significant digits, ascending; the 5 % row is the reference. «Target first» has no column (M33)."""

    level_weights: FidelityLevelWeights
    rows: Annotated[list[AcceptableCostRow], Field(min_length=4, max_length=4)]

    @model_validator(mode="after")
    def validate_rows(self) -> AcceptableCostTable:
        if [row.reference for row in self.rows] != [False, False, True, False]:
            raise ValueError("The reference row is the third, the 5 % one")
        amounts = [money_fraction(row.misplaced) for row in self.rows]
        if any(amount <= 0 for amount in amounts) or amounts != sorted(set(amounts)):
            raise ValueError("The rows of misplaced money are positive and strictly ascending")
        if len({row.custom is None for row in self.rows}) != 1:
            raise ValueError("The custom column is in every row or in none")
        return self


class CustomFidelityPreview(AllocationStrictModel):
    """The «custom» fidelity both ways: ``λ``, and the euros the plan accepts to spend on the reference row."""

    distance_weight: ExactNumber
    reference_amount: ExactMoney

    @model_validator(mode="after")
    def validate_positive(self) -> CustomFidelityPreview:
        if exact_fraction(self.distance_weight) <= 0 or money_fraction(self.reference_amount) <= 0:
            raise ValueError("A custom fidelity has a positive λ and a positive reference amount")
        return self


class _PreviewFailureBase(AllocationStrictModel):
    operation: Literal["preview"]
    snapshot: PlannerResultSnapshot
    issues: Annotated[list[PlannerIssue], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_controlling_issue(self) -> _PreviewFailureBase:
        required_kind = "missing" if self.availability == "needs_input" else self.availability
        if not any(issue.kind == required_kind and issue.severity == "error" for issue in self.issues):
            raise ValueError("Failure result must include an error issue matching its availability")
        return self


class PlannerPreviewNeedsInputResult(_PreviewFailureBase):
    result_state: Literal["preview_needs_input"]
    availability: Literal["needs_input"]


class PlannerPreviewInvalidResult(_PreviewFailureBase):
    result_state: Literal["preview_invalid"]
    availability: Literal["invalid"]


class PlannerPreviewUnsupportedResult(_PreviewFailureBase):
    result_state: Literal["preview_unsupported"]
    availability: Literal["unsupported"]


# The limits' cross checks (M1, T12) that keep a plan from being computed but not a preview from counting (B4, Q2).
LIMIT_PROBLEM_CODES = frozenset({"allocation.bound_min_above_max", "allocation.bounds_min_sum_exceeds_reference", "allocation.bound_max_below_current"})


class _PreviewReadyBase(AllocationStrictModel):
    operation: Literal["preview"]
    result_state: Literal["preview_ready"]
    availability: Literal["ready"]
    snapshot: PlannerResultSnapshot
    valuation_currency: CurrencyCode
    total: ExactMoney = Field(description="The total of the plan in the valuation currency: F in the Rebalancer, the cash the PAC invests.")
    issues: list[PlannerIssue]
    limit_problems: list[PlannerIssue] = Field(description=("The cross checks of the limits the plan would refuse (a minimum above its maximum, minimums over the total, " "a maximum below today's value), each naming its entry: the preview still counts, the plan answers invalid."))

    @model_validator(mode="after")
    def validate_total(self) -> _PreviewReadyBase:
        if any(issue.severity == "error" for issue in self.issues):
            raise ValueError("Ready results cannot contain error-severity issues")
        if any(problem.code not in LIMIT_PROBLEM_CODES for problem in self.limit_problems):
            raise ValueError("limit_problems carries only the three cross checks of the limits")
        if self.total.currency != self.valuation_currency or money_fraction(self.total) < 0:
            raise ValueError("The total is a nonnegative amount in the valuation currency")
        return self


class PacPreviewReadyResult(_PreviewReadyBase):
    """The PAC's preview: the cash the plan invests."""


class RebalancerPreviewReadyResult(_PreviewReadyBase):
    """The Rebalancer's preview: ``F``, today's items on it, the table, and the «custom» fidelity when there is one."""

    items: list[PreviewItem]
    table: AcceptableCostTable
    custom: CustomFidelityPreview | None

    @model_validator(mode="after")
    def validate_items_and_table(self) -> RebalancerPreviewReadyResult:
        total = money_fraction(self.total)
        if total <= 0:
            raise ValueError("A ready Rebalancer preview has a positive total")
        money = [self.total, *(item.value for item in self.items)]
        money += [amount for row in self.table.rows for amount in (row.misplaced, row.cost_aware, row.balanced, row.faithful, row.custom) if amount is not None]
        money += [self.custom.reference_amount] if self.custom is not None else []
        if any(amount.currency != self.valuation_currency for amount in money):
            raise ValueError("Preview amounts must use the valuation currency")
        if any(exact_fraction(item.weight) * total != money_fraction(item.value) for item in self.items):
            raise ValueError("An item's weight must be its value over the total")
        if (self.custom is None) != (self.table.rows[0].custom is None):
            raise ValueError("The custom column is there exactly when the custom fidelity is")
        self._validate_costs(total)
        return self

    def _validate_costs(self, total: Fraction) -> None:
        """Every cell is ``2·λ·d²/F`` with the row's shown figure; the custom λ and its euros agree on the reference row."""
        weights = {name: exact_fraction(getattr(self.table.level_weights, name)) for name in ("cost_aware", "balanced", "faithful")}
        if self.custom is not None:
            weights["custom"] = exact_fraction(self.custom.distance_weight)
        for row in self.table.rows:
            misplaced = money_fraction(row.misplaced)
            for name, weight in weights.items():
                if money_fraction(getattr(row, name)) != max_acceptable_cost(weight, misplaced, total):
                    raise ValueError("A table cell must be 2·λ·d²/F of its row")
        if self.custom is not None and money_fraction(self.custom.reference_amount) != money_fraction(self.table.rows[2].custom):
            raise ValueError("The custom euros are the custom column on the reference row")


# What each service answers: the plan's seven states and the preview's four, told apart by ``result_state``.
type PacToolOutput = Annotated[
    Union[
        PacPlannerNeedsInputResult,
        PacPlannerInvalidResult,
        PacPlannerUnsupportedResult,
        PacPlannerReadyNoOpResult,
        PacPlannerReadyIncumbentResult,
        PacPlannerReadyInfeasibleResult,
        PacPlannerReadyNoIncumbentResult,
        PlannerPreviewNeedsInputResult,
        PlannerPreviewInvalidResult,
        PlannerPreviewUnsupportedResult,
        PacPreviewReadyResult,
    ],
    Field(discriminator="result_state"),
]
type RebalancerToolOutput = Annotated[
    Union[
        RebalancerPlannerNeedsInputResult,
        RebalancerPlannerInvalidResult,
        RebalancerPlannerUnsupportedResult,
        RebalancerPlannerReadyNoOpResult,
        RebalancerPlannerReadyIncumbentResult,
        RebalancerPlannerReadyInfeasibleResult,
        RebalancerPlannerReadyNoIncumbentResult,
        PlannerPreviewNeedsInputResult,
        PlannerPreviewInvalidResult,
        PlannerPreviewUnsupportedResult,
        RebalancerPreviewReadyResult,
    ],
    Field(discriminator="result_state"),
]

PAC_TOOL_INPUT_ADAPTER = TypeAdapter(PacPlannerRequest)
PAC_TOOL_OUTPUT_ADAPTER = TypeAdapter(PacToolOutput)
REBALANCER_TOOL_INPUT_ADAPTER = TypeAdapter(RebalancerPlannerRequest)
REBALANCER_TOOL_OUTPUT_ADAPTER = TypeAdapter(RebalancerToolOutput)
