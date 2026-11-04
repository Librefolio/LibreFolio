"""Planner issues: section, entity and field paths, typed parameters and the issue record."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field, model_validator

from backend.app.schemas.pac_allocator.base import AllocationStrictModel, CurrencyCode, PlannerCode, PlannerFixedDecimal, PlannerId, PlannerIssueCode, PlannerLongLabel, PlannerMessageKey, PlannerMoneyInput, PlannerSafeInteger, require_unique

PlannerIssueSection = Literal[
    "input",
    "assets",
    "brokers",
    "holdings",
    "cash",
    "contributions",
    "funding",
    "routing",
    "fx",
    "targets",
    "policy",
    "proof",
    "liquidity",
    "result",
]
PlannerIssueEntityKind = Literal[
    "scenario",
    "asset",
    "broker",
    "holding",
    "currency",
    "cash",
    "contribution",
    "funding_route",
    "fx_rate",
    "order_route",
    "order",
    "solution",
]


class SectionIssuePath(AllocationStrictModel):
    kind: Literal["section"]
    section: PlannerIssueSection


class EntityIssuePath(AllocationStrictModel):
    kind: Literal["entity"]
    section: PlannerIssueSection
    entity_kind: PlannerIssueEntityKind
    entity_id: PlannerId


class FieldIssuePath(AllocationStrictModel):
    kind: Literal["field"]
    section: PlannerIssueSection
    entity_kind: PlannerIssueEntityKind
    entity_id: PlannerId
    field: PlannerCode


type PlannerIssuePath = Annotated[
    Union[SectionIssuePath, EntityIssuePath, FieldIssuePath],
    Field(discriminator="kind"),
]


class TextIssueParam(AllocationStrictModel):
    kind: Literal["text"]
    name: PlannerId
    value: PlannerLongLabel


class IdIssueParam(AllocationStrictModel):
    kind: Literal["id"]
    name: PlannerId
    value: PlannerId


class CountIssueParam(AllocationStrictModel):
    kind: Literal["count"]
    name: PlannerId
    value: PlannerSafeInteger


class DecimalIssueParam(AllocationStrictModel):
    kind: Literal["decimal"]
    name: PlannerId
    value: PlannerFixedDecimal


class CurrencyIssueParam(AllocationStrictModel):
    kind: Literal["currency"]
    name: PlannerId
    value: CurrencyCode


class MoneyIssueParam(AllocationStrictModel):
    kind: Literal["money"]
    name: PlannerId
    value: PlannerMoneyInput


type PlannerIssueParam = Annotated[
    Union[TextIssueParam, IdIssueParam, CountIssueParam, DecimalIssueParam, CurrencyIssueParam, MoneyIssueParam],
    Field(discriminator="kind"),
]


class PlannerIssue(AllocationStrictModel):
    code: PlannerIssueCode
    severity: Literal["info", "warning", "error"]
    kind: Literal["missing", "invalid", "unsupported", "constraint", "proof", "info"]
    path: PlannerIssuePath
    message_key: PlannerMessageKey
    params: list[PlannerIssueParam]

    @model_validator(mode="after")
    def validate_param_names(self) -> PlannerIssue:
        require_unique([param.name for param in self.params], "Issue parameter names")
        return self
