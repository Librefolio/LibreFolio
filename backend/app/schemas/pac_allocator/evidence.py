"""Objective codes and units, the floating solver evidence, and the proof of a ready plan."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field, model_validator

from backend.app.schemas.pac_allocator.base import AllocationStrictModel, CurrencyCode, NotProvenReasonCode, PlannerFixedDecimal, PlannerId, PlannerLabel, PlannerLongLabel, PlannerNonNegativeDecimal, PlannerPositiveInteger
from backend.app.schemas.pac_allocator.exact import fixed_fraction


class CountUnit(AllocationStrictModel):
    kind: Literal["count"]


class ValuationMoneyUnit(AllocationStrictModel):
    kind: Literal["valuation_money"]
    currency_code: CurrencyCode


class ValuationMoneySquaredUnit(AllocationStrictModel):
    kind: Literal["valuation_money_squared"]
    currency_code: CurrencyCode


class OrdinalPenaltyUnit(AllocationStrictModel):
    kind: Literal["ordinal_penalty"]


class CanonicalKeyUnit(AllocationStrictModel):
    kind: Literal["canonical_key"]


type NumericObjectiveUnit = Annotated[
    Union[CountUnit, ValuationMoneyUnit, ValuationMoneySquaredUnit, OrdinalPenaltyUnit],
    Field(discriminator="kind"),
]

ObjectiveCode = Literal[
    "fixed_l2",
    "shortfall",
    "turnover",
    "explicit_cost",
    "incremental_cost",
    "split_asset_count",
    "active_order_rows",
    "incremental_order_rows",
    "route_priority",
]
ObjectiveSense = Literal["min", "max"]

_ObjectiveSignDomain = Literal["signed", "nonnegative", "nonnegative_integer"]
# Keep this exhaustive: every future ObjectiveCode must choose its sign domain.
OBJECTIVE_SIGN_DOMAINS: dict[ObjectiveCode, _ObjectiveSignDomain] = {
    "fixed_l2": "nonnegative",
    "shortfall": "signed",
    "turnover": "nonnegative",
    "explicit_cost": "nonnegative",
    "incremental_cost": "nonnegative",
    "split_asset_count": "nonnegative_integer",
    "active_order_rows": "nonnegative_integer",
    "incremental_order_rows": "nonnegative_integer",
    "route_priority": "nonnegative_integer",
}


def objective_unit_kind(code: ObjectiveCode) -> str:
    if code == "fixed_l2":
        return "valuation_money_squared"
    if code in {"shortfall", "turnover", "explicit_cost", "incremental_cost"}:
        return "valuation_money"
    if code in {"split_asset_count", "active_order_rows", "incremental_order_rows"}:
        return "count"
    return "ordinal_penalty"


class SolverSettingEvidence(AllocationStrictModel):
    name: PlannerId
    value: PlannerLongLabel


class SolverToleranceEvidence(AllocationStrictModel):
    feasibility: PlannerNonNegativeDecimal
    integrality: PlannerNonNegativeDecimal
    absolute_gap: PlannerNonNegativeDecimal
    relative_gap: PlannerNonNegativeDecimal


class SolverStageEvidence(AllocationStrictModel):
    """Non-authoritative floating solver report; never an exact objective value.

    ``infeasible`` is SCIP's own verdict on the first, still-global stage, and
    it carries no observation: an infeasible solve has no primal, no dual and
    no gap. No later stage can carry it — a face emptied by earlier pins is an
    anomaly of the pins, not a statement about the scenario — so such a stage
    is reported ``unfinished``.
    """

    kind: Literal["reported_floating"]
    stage: PlannerId
    objective_code: ObjectiveCode
    ordinal: PlannerPositiveInteger
    status: Literal["finished", "unfinished", "infeasible"]
    scope: Literal["global", "incumbent_face"]
    sense: ObjectiveSense
    unit: NumericObjectiveUnit
    primal: PlannerFixedDecimal | None
    dual: PlannerFixedDecimal | None
    absolute_gap: PlannerNonNegativeDecimal | None
    relative_gap: PlannerNonNegativeDecimal | None
    tolerances: SolverToleranceEvidence
    engine: PlannerLabel
    version: PlannerLabel
    settings: list[SolverSettingEvidence]

    @model_validator(mode="after")
    def validate_objective_unit(self) -> SolverStageEvidence:
        if self.unit.kind != objective_unit_kind(self.objective_code):
            raise ValueError("Solver stage unit does not match objective code")
        observations = (self.primal, self.dual, self.absolute_gap, self.relative_gap)
        if self.status == "finished" and any(value is None for value in observations):
            raise ValueError("Finished solver stage evidence requires finite primal, dual, and gaps")
        if self.status == "infeasible":
            if self.ordinal != 1 or self.scope != "global":
                raise ValueError("Only the first, global solver stage can report infeasibility")
            if any(value is not None for value in observations):
                raise ValueError("An infeasible solver stage has no primal, dual, or gap")
        if self.primal is not None and self.dual is not None:
            primal = fixed_fraction(self.primal)
            dual = fixed_fraction(self.dual)
            if (self.sense == "min" and dual > primal) or (self.sense == "max" and primal > dual):
                raise ValueError("Reported bound ordering must match the objective sense")
            if self.absolute_gap is not None and fixed_fraction(self.absolute_gap) < abs(primal - dual):
                raise ValueError("Reported absolute gap must bound the primal-dual difference")
        return self


class ReportedFloatingSolverEvidence(AllocationStrictModel):
    """What SCIP did, stage by stage; every ready result carries it (D-X1)."""

    kind: Literal["reported_floating"]
    stages: Annotated[list[SolverStageEvidence], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_stage_order(self) -> ReportedFloatingSolverEvidence:
        ordinals = [stage.ordinal for stage in self.stages]
        codes = [stage.objective_code for stage in self.stages]
        if ordinals != sorted(ordinals) or len(ordinals) != len(set(ordinals)) or len(codes) != len(set(codes)):
            raise ValueError("Solver stages must have unique codes and ascending ordinals")
        statuses = [stage.status for stage in self.stages]
        if "infeasible" in statuses:
            # Nothing runs after an infeasible first stage, so nothing is reported after it.
            if len(statuses) != 1:
                raise ValueError("An infeasible solver stage must be the only reported stage")
            return self
        if statuses != sorted(statuses, key={"finished": 0, "unfinished": 1}.__getitem__):
            raise ValueError("Finished solver stages must precede unfinished stages")
        return self


class SolverStatusWitness(AllocationStrictModel):
    """SCIP's own status, which is the proof (D-X1).

    Names the objective stages the solver closed — at the optimum for
    ``optimal_proven``, as infeasible for ``infeasibility_proven``. Engine,
    version, tolerances and gaps already live on the solver evidence, which
    the ready result binds to this witness stage by stage.
    """

    kind: Literal["solver_status"]
    objective_codes: Annotated[list[ObjectiveCode], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_objective_codes(self) -> SolverStatusWitness:
        if len(self.objective_codes) != len(set(self.objective_codes)):
            raise ValueError("Solver-status witness objective codes must be unique")
        return self


class OptimalProvenProof(AllocationStrictModel):
    kind: Literal["optimal_proven"]
    proof_source: Literal["solver_status"]
    witness: SolverStatusWitness
    tie_break_closed: Literal[True]


class NotProvenProof(AllocationStrictModel):
    kind: Literal["not_proven"]
    reason_code: NotProvenReasonCode


class InfeasibilityProvenProof(AllocationStrictModel):
    kind: Literal["infeasibility_proven"]
    proof_source: Literal["solver_status"]
    witness: SolverStatusWitness

    @model_validator(mode="after")
    def validate_first_stage_only(self) -> InfeasibilityProvenProof:
        if len(self.witness.objective_codes) != 1:
            raise ValueError("An infeasibility proof names exactly the first objective stage")
        return self


type ReadyPlanProof = Annotated[
    Union[OptimalProvenProof, NotProvenProof],
    Field(discriminator="kind"),
]
