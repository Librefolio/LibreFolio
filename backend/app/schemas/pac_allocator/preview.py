"""The scenario preview of both Tools (contract §11, decisioni-REB §11.2; B4 of project 67).

The numbers the screen shows **before** a plan is computed, from the backend (N1): the total of the plan; for the Rebalancer
today's value and weight of every target entry and the λ of the three fidelity levels. The table «maximum acceptable cost»
is the page's, on these numbers (R1-F (b) of project 67, developer decision of 21/11/2026): no figure of it, and no field
of the target fidelity, is in the preview. No optimizer runs. A preview that cannot count (a missing price or
rate, no holdings, a portfolio worth nothing) answers ``needs_input`` or ``invalid`` with the codes of ``plan``. Limits that
contradict each other or the portfolio do not stop it: it stays ready and names them in ``limit_problems``.

Its result states are ``preview_*``, so that one discriminated union per service carries both operations' results.
"""

from __future__ import annotations

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


class PreviewOtherCashItem(AllocationStrictModel):
    """«Other cash» (G5-2 of project 67): the cash outside the cash entries, today, and its weight on the total ``F``; zero
    when the entries cover it all. The frontend may not derive it by subtraction (N1)."""

    kind: Literal["other_cash"]
    value: ExactMoney
    weight: ExactNumber


type PreviewItem = Annotated[Union[PreviewAssetItem, PreviewCashItem, PreviewOtherCashItem], Field(discriminator="kind")]


class FidelityLevelWeights(AllocationStrictModel):
    """The distance weight λ of each fidelity level (specifica §6.3), as the normalizer reads it: the three columns of the
    page's table «maximum acceptable cost»."""

    cost_aware: ExactNumber
    balanced: ExactNumber
    faithful: ExactNumber

    @model_validator(mode="after")
    def validate_positive(self) -> FidelityLevelWeights:
        if any(exact_fraction(getattr(self, name)) <= 0 for name in ("cost_aware", "balanced", "faithful")):
            raise ValueError("A fidelity level's λ is positive")
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
    """The Rebalancer's preview: ``F``, today's items on it, and the λ of the three fidelity levels."""

    items: list[PreviewItem]
    fidelity_level_weights: FidelityLevelWeights = Field(description="The distance weight λ of each fidelity level, as the plan reads it: the page computes the table «maximum acceptable cost» from these and the total.")

    @model_validator(mode="after")
    def validate_items(self) -> RebalancerPreviewReadyResult:
        total = money_fraction(self.total)
        if total <= 0:
            raise ValueError("A ready Rebalancer preview has a positive total")
        if any(item.value.currency != self.valuation_currency for item in self.items):
            raise ValueError("Preview amounts must use the valuation currency")
        if any(exact_fraction(item.weight) * total != money_fraction(item.value) for item in self.items):
            raise ValueError("An item's weight must be its value over the total")
        return self


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
