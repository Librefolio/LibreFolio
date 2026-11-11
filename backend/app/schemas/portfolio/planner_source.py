"""Planner source (``POST /portfolio/planner-source``): the request, the snapshot of the portfolio the PAC/Rebalancer plans from, its evidence and its issues."""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, List, Literal, Optional, Union

from pydantic import BeforeValidator, Field, field_validator, model_validator

from backend.app.schemas.common import Currency, CurrencyCode, SafeDecimal, StrictModel


class PlannerSourceSection(StrEnum):
    ASSETS = "assets"
    BROKERS = "brokers"
    HOLDINGS = "holdings"
    CASH_BALANCES = "cash_balances"
    PRICES = "prices"
    CLASSIFICATIONS = "classifications"
    WAC_CONTEXTS = "wac_contexts"
    FX_QUOTES = "fx_quotes"
    CURRENT_DISTRIBUTION = "current_distribution"


PlannerSourceResponseSection = Literal[
    "provenance",
    "assets",
    "brokers",
    "holdings",
    "cash_balances",
    "prices",
    "classifications",
    "wac_contexts",
    "fx_quotes",
    "current_distribution",
    "issues",
]


PlannerSourceEntityKind = Literal[
    "asset",
    "broker",
    "holding",
    "cash_balance",
    "price",
    "classification",
    "wac_context",
    "fx_quote",
    "current_weight",
]


PlannerSourceEntityId = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[!-~]+$")]


PlannerSourceProvenanceId = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[!-~]+$")]


PlannerSourceRef = Annotated[str, Field(min_length=1, max_length=256, pattern=r"^[!-~]+$")]


PlannerSourcePositiveInt = Annotated[int, Field(strict=True, gt=0)]


def _validate_canonical_fx_pair(value: str) -> str:
    """Normalize/validate one direct unordered FX pair, e.g. 'usd/eur' -> 'EUR/USD'."""
    if not isinstance(value, str):
        raise ValueError(f"FX pair must be a string, got {type(value)}")
    first_raw, separator, second_raw = value.partition("/")
    if separator != "/":
        raise ValueError("FX pair must have the form 'AAA/BBB'")
    first = Currency.validate_code(first_raw)
    second = Currency.validate_code(second_raw)
    if first >= second:
        raise ValueError("FX pair must name two distinct currencies in ascending alphabetical order")
    return f"{first}/{second}"


PortfolioPlannerSourceFxPair = Annotated[str, BeforeValidator(_validate_canonical_fx_pair)]


class PortfolioPlannerSourceRequest(StrictModel):
    """Select a read-only planner snapshot for an explicit OWNER Broker scope."""

    as_of: date_type
    target_currency: CurrencyCode
    requested_sections: List[PlannerSourceSection] = Field(..., min_length=1)
    broker_ids: List[PlannerSourcePositiveInt] = Field(..., min_length=1)
    asset_ids: Optional[List[PlannerSourcePositiveInt]]
    fx_pairs: List[PortfolioPlannerSourceFxPair]

    @field_validator("requested_sections")
    @classmethod
    def validate_requested_sections(cls, sections: List[PlannerSourceSection]) -> List[PlannerSourceSection]:
        if len(sections) != len(set(sections)):
            raise ValueError("requested_sections must not contain duplicates")
        return sections

    @field_validator("broker_ids")
    @classmethod
    def validate_broker_ids(cls, broker_ids: List[int]) -> List[int]:
        if len(broker_ids) != len(set(broker_ids)):
            raise ValueError("broker_ids must not contain duplicates")
        return broker_ids

    @field_validator("asset_ids")
    @classmethod
    def validate_asset_ids(cls, asset_ids: Optional[List[int]]) -> Optional[List[int]]:
        if asset_ids is not None and len(asset_ids) != len(set(asset_ids)):
            raise ValueError("asset_ids must not contain duplicates")
        return asset_ids

    @field_validator("fx_pairs")
    @classmethod
    def validate_fx_pairs(
        cls,
        pairs: List[str],
    ) -> List[str]:
        if len(pairs) != len(set(pairs)):
            raise ValueError("fx_pairs must not contain duplicate pairs")
        return pairs

    @model_validator(mode="after")
    def validate_current_distribution_scope(self) -> PortfolioPlannerSourceRequest:
        # The weight denominator is the scenario, so it must be named explicitly.
        if PlannerSourceSection.CURRENT_DISTRIBUTION in self.requested_sections and self.asset_ids is None:
            raise ValueError("current_distribution requires an explicit asset_ids scenario")
        return self


class PortfolioPlannerSourceSnapshot(StrictModel):
    """Request-bound metadata for one immutable domain-copy response."""

    as_of: date_type
    target_currency: CurrencyCode
    generated_at: datetime
    requested_sections: List[PlannerSourceSection]
    source_revision: Literal["1.0.0"]

    @field_validator("generated_at")
    @classmethod
    def validate_generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at must be timezone-aware")
        return value


class PortfolioPlannerSourceProvenance(StrictModel):
    """Stable non-financial provenance record referenced by source rows."""

    provenance_id: PlannerSourceProvenanceId
    kind: Literal["domain_copy"]
    domain: Literal["portfolio", "market_data", "broker", "fx", "wac"]
    source_ref: PlannerSourceRef
    source_label: Optional[Annotated[str, Field(min_length=1, max_length=128)]]
    captured_at: datetime

    @field_validator("source_label")
    @classmethod
    def validate_source_label(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise ValueError("source_label must contain Unicode scalar values")
        return value

    @field_validator("captured_at")
    @classmethod
    def validate_captured_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware")
        return value


class PortfolioPlannerSourceAsset(StrictModel):
    """Persisted Asset identity copied without planner policy."""

    asset_id: PlannerSourceEntityId
    source_asset_id: int
    name: str
    ticker: Optional[str]
    asset_class: str
    icon_url: Optional[str]
    active: bool
    provenance_id: PlannerSourceProvenanceId


class PortfolioPlannerSourceBroker(StrictModel):
    """Authorized OWNER Broker identity plus known account facts."""

    broker_id: PlannerSourceEntityId
    source_broker_id: int
    name: str
    icon_url: Optional[str]
    portal_url: Optional[str]
    default_import_plugin: Optional[str]
    access_role: Literal["OWNER"]
    ownership_share: SafeDecimal = Field(..., ge=0, le=1)
    observed_currencies: List[CurrencyCode]
    active: bool
    allow_cash_overdraft: bool
    allow_asset_shorting: bool
    execution_profile_status: Literal["not_available"]
    provenance_id: PlannerSourceProvenanceId


class PortfolioPlannerSourceHolding(StrictModel):
    """One exact Asset×Broker custody row and its personal economic share."""

    holding_id: PlannerSourceEntityId
    asset_id: PlannerSourceEntityId
    broker_id: PlannerSourceEntityId
    custody_quantity: SafeDecimal
    ownership_share: SafeDecimal = Field(..., ge=0, le=1)
    economic_quantity: SafeDecimal
    quantity_unit: Literal["asset_unit"]
    provenance_id: PlannerSourceProvenanceId


class PortfolioPlannerSourceCashBalance(StrictModel):
    """One native Broker×currency ledger balance and its economic share."""

    cash_id: PlannerSourceEntityId
    broker_id: PlannerSourceEntityId
    currency: CurrencyCode
    custody_amount: SafeDecimal
    ownership_share: SafeDecimal = Field(..., ge=0, le=1)
    economic_amount: SafeDecimal
    provenance_id: PlannerSourceProvenanceId


class PortfolioPlannerSourcePrice(StrictModel):
    """Latest saved raw Asset quote at or before the snapshot date."""

    price_id: PlannerSourceEntityId
    asset_id: PlannerSourceEntityId
    amount: Optional[SafeDecimal]
    currency: Optional[CurrencyCode]
    quote_base_quantity: Optional[SafeDecimal] = Field(..., gt=0)
    reference_date: Optional[date_type]
    source: Optional[str]
    days_before_requested: Optional[int] = Field(..., ge=0)
    provenance_id: PlannerSourceProvenanceId


class PortfolioPlannerSourceClassification(StrictModel):
    """One exact saved Asset classification row."""

    classification_id: PlannerSourceEntityId
    asset_id: PlannerSourceEntityId
    dimension: Literal["asset_type", "sector", "geography"]
    category_id: Optional[str]
    label: Optional[str]
    weight: Optional[SafeDecimal] = Field(..., ge=0, le=1)
    provenance_id: PlannerSourceProvenanceId


class PortfolioPlannerSourceWacFxEvidence(StrictModel):
    """Saved FX observation used by the canonical runtime WAC calculation."""

    source_currency: CurrencyCode
    destination_currency: CurrencyCode
    rate: Optional[SafeDecimal] = Field(..., gt=0)
    reference_date: Optional[date_type]
    source: Optional[str]
    inverted: bool
    status: Literal["available", "missing"]


class PortfolioPlannerWacContext(StrictModel):
    """Canonical per-holding WAC projected into the requested calculation currency."""

    wac_id: PlannerSourceEntityId
    holding_id: PlannerSourceEntityId
    asset_id: PlannerSourceEntityId
    broker_id: PlannerSourceEntityId
    method: Literal["runtime_wac"]
    unit_cost: Optional[SafeDecimal]
    fiscal_currency: Optional[CurrencyCode]
    target_currency: CurrencyCode
    as_of: date_type
    fx_evidence: List[PortfolioPlannerSourceWacFxEvidence]
    provenance_id: PlannerSourceProvenanceId


class PortfolioPlannerSourceFxQuote(StrictModel):
    """One canonical FX pair prefill row: the most recent saved rate LibreFolio holds for that pair, if any."""

    fx_quote_id: PlannerSourceEntityId
    pair: PortfolioPlannerSourceFxPair
    rate: Optional[SafeDecimal] = Field(..., gt=0)
    reference_date: Optional[date_type]
    source: Optional[str]
    days_before_requested: Optional[int] = Field(..., ge=0)
    provenance_id: PlannerSourceProvenanceId


PLANNER_CURRENT_WEIGHT_QUANTUM = Decimal("0.0001")


class PortfolioPlannerCurrentWeight(StrictModel):
    """One scenario Asset's current portfolio-engine weight; never an amount."""

    weight_id: PlannerSourceEntityId
    asset_id: PlannerSourceEntityId
    held: bool
    weight: Optional[SafeDecimal] = Field(..., ge=0, le=1)
    valuation_source: Optional[Literal["MARKET_PRICE", "LAST_TRADE_PRICE", "ESTIMATED_AT_COST", "MISSING"]]
    valuation_reference_date: Optional[date_type]
    valuation_days_before_requested: Optional[int] = Field(..., ge=0)
    valuation_stale: bool

    @field_validator("weight")
    @classmethod
    def validate_weight_quantum(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        if value is not None and value % PLANNER_CURRENT_WEIGHT_QUANTUM != 0:
            raise ValueError("weight must be a multiple of 0.0001")
        return value


class PortfolioPlannerCurrentDistribution(StrictModel):
    """Current portfolio-engine market-value weights over the scenario Assets.

    The denominator is the requested Asset scenario, cash excluded. Weights exist only
    when every held scenario Asset has a valuation and the total is positive.
    """

    status: Literal["complete", "incomplete", "no_holdings"]
    method: Literal["portfolio_engine_market_value"]
    rounding: Literal["largest_remainder"]
    weight_quantum: Literal["0.0001"]
    as_of: date_type
    provenance_id: PlannerSourceProvenanceId
    rows: List[PortfolioPlannerCurrentWeight]

    @model_validator(mode="after")
    def validate_weights(self) -> PortfolioPlannerCurrentDistribution:
        asset_ids = [row.asset_id for row in self.rows]
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError("current_distribution rows must name distinct Assets")
        weights = [row.weight for row in self.rows]
        if self.status == "complete":
            if not self.rows or any(weight is None for weight in weights):
                raise ValueError("a complete current_distribution must weight every row")
            if sum((weight for weight in weights if weight is not None), Decimal("0")) != 1:
                raise ValueError("current_distribution weights must sum to exactly 1")
        elif any(weight is not None for weight in weights):
            raise ValueError("only a complete current_distribution carries weights")
        return self


class PortfolioPlannerSourceRootPath(StrictModel):
    kind: Literal["root"] = Field(json_schema_extra={"enum": ["root"]})


class PortfolioPlannerSourceSectionPath(StrictModel):
    kind: Literal["section"] = Field(json_schema_extra={"enum": ["section"]})
    section: PlannerSourceResponseSection


class PortfolioPlannerSourceEntityPath(StrictModel):
    kind: Literal["entity"] = Field(json_schema_extra={"enum": ["entity"]})
    section: PlannerSourceResponseSection
    entity_kind: PlannerSourceEntityKind
    entity_id: PlannerSourceEntityId


class PortfolioPlannerSourceFieldPath(StrictModel):
    kind: Literal["field"] = Field(json_schema_extra={"enum": ["field"]})
    section: PlannerSourceResponseSection
    entity_kind: PlannerSourceEntityKind
    entity_id: PlannerSourceEntityId
    field: Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")]


PortfolioPlannerSourceIssuePath = Annotated[
    Union[
        PortfolioPlannerSourceRootPath,
        PortfolioPlannerSourceSectionPath,
        PortfolioPlannerSourceEntityPath,
        PortfolioPlannerSourceFieldPath,
    ],
    Field(discriminator="kind"),
]


class PortfolioPlannerSourceTextParam(StrictModel):
    kind: Literal["text"] = Field(json_schema_extra={"enum": ["text"]})
    name: Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")]
    value: Annotated[str, Field(max_length=256)]


class PortfolioPlannerSourceIntegerParam(StrictModel):
    kind: Literal["integer"] = Field(json_schema_extra={"enum": ["integer"]})
    name: Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")]
    value: int


class PortfolioPlannerSourceMoneyParam(StrictModel):
    kind: Literal["money"] = Field(json_schema_extra={"enum": ["money"]})
    name: Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")]
    amount: SafeDecimal
    currency: CurrencyCode


class PortfolioPlannerSourceDateParam(StrictModel):
    kind: Literal["date"] = Field(json_schema_extra={"enum": ["date"]})
    name: Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")]
    value: date_type


class PortfolioPlannerSourceEntityRefParam(StrictModel):
    kind: Literal["entity_ref"] = Field(json_schema_extra={"enum": ["entity_ref"]})
    name: Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")]
    entity_kind: PlannerSourceEntityKind
    entity_id: PlannerSourceEntityId


PortfolioPlannerSourceIssueParam = Annotated[
    Union[
        PortfolioPlannerSourceTextParam,
        PortfolioPlannerSourceIntegerParam,
        PortfolioPlannerSourceMoneyParam,
        PortfolioPlannerSourceDateParam,
        PortfolioPlannerSourceEntityRefParam,
    ],
    Field(discriminator="kind"),
]


PortfolioPlannerSourceIssueCode = Literal[
    "allocation.currency_spec_missing",
    "allocation.price_missing",
    "allocation.price_date_missing",
    "allocation.nonpositive_price",
    "allocation.quote_base_quantity_missing",
    "allocation.asset_type_missing",
    "allocation.classification_sector_missing",
    "allocation.classification_geography_missing",
    "allocation.classification_invalid",
    "allocation.wac_missing",
    "allocation.wac_fx_missing",
    "allocation.fiscal_currency_missing",
    "allocation.saved_fx_missing",
    "allocation.saved_fx_invalid",
    "allocation.saved_fx_skipped",
    "allocation.negative_inventory_unsupported",
    "allocation.negative_cash_unsupported",
    "allocation.broker_execution_profile_unsupported",
    "allocation.broker_inactive",
    "allocation.asset_inactive_not_buyable",
]


class PortfolioPlannerSourceIssue(StrictModel):
    """Typed source defect without raw personal financial values."""

    code: PortfolioPlannerSourceIssueCode
    kind: Literal["missing", "invalid", "unsupported", "info"]
    severity: Literal["error", "warning", "info"]
    path: PortfolioPlannerSourceIssuePath
    message_key: Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")]
    params: List[PortfolioPlannerSourceIssueParam] = Field(..., max_length=8)

    @field_validator("params")
    @classmethod
    def validate_param_names(
        cls,
        params: List[PortfolioPlannerSourceIssueParam],
    ) -> List[PortfolioPlannerSourceIssueParam]:
        names = [param.name for param in params]
        if len(names) != len(set(names)):
            raise ValueError("issue params must use unique names")
        return params


class PortfolioPlannerSourceResponse(StrictModel):
    """Independent, read-only domain facts for explicit planner copy actions."""

    snapshot: PortfolioPlannerSourceSnapshot
    provenance: List[PortfolioPlannerSourceProvenance] = Field(..., min_length=1)
    assets: List[PortfolioPlannerSourceAsset]
    brokers: List[PortfolioPlannerSourceBroker]
    holdings: List[PortfolioPlannerSourceHolding]
    cash_balances: List[PortfolioPlannerSourceCashBalance]
    prices: List[PortfolioPlannerSourcePrice]
    classifications: List[PortfolioPlannerSourceClassification]
    wac_contexts: List[PortfolioPlannerWacContext]
    fx_quotes: List[PortfolioPlannerSourceFxQuote]
    current_distribution: Optional[PortfolioPlannerCurrentDistribution] = Field(None, description="Current portfolio-engine weights over the scenario Assets. Only when the current_distribution section is requested.")
    issues: List[PortfolioPlannerSourceIssue]
