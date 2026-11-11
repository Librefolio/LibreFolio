"""Risk scopes, requests, catalog and eligibility: what an analytic is asked about, which analytics exist and which assets can enter them."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Annotated, Dict, List, Literal, Optional, Union

from pydantic import Field, JsonValue, PositiveInt, field_validator, model_validator

from backend.app.schemas.common import Currency, DateRangeModel, StrictModel
from backend.app.schemas.risk.vocabulary import RiskCompositionPolicy, RiskEligibilityLevel, RiskEligibilityReason, RiskMode, RiskOutputKind, RiskScopeKind
from backend.app.utils.json_utils import ensure_json_safe


class RiskScopeBase(StrictModel):
    """Base for the discriminated risk query scope."""

    kind: RiskScopeKind


class AssetRiskScope(RiskScopeBase):
    kind: Literal[RiskScopeKind.ASSET] = Field(json_schema_extra={"enum": ["asset"]})
    asset_id: PositiveInt


class AssetSetRiskScope(RiskScopeBase):
    kind: Literal[RiskScopeKind.ASSET_SET] = Field(json_schema_extra={"enum": ["asset_set"]})
    asset_ids: List[PositiveInt] = Field(..., min_length=1, max_length=100)

    @field_validator("asset_ids")
    @classmethod
    def validate_unique_asset_ids(cls, value: List[int]) -> List[int]:
        if len(value) != len(set(value)):
            raise ValueError("asset_ids must be unique")
        return value


class PortfolioRiskScope(RiskScopeBase):
    kind: Literal[RiskScopeKind.PORTFOLIO] = Field(json_schema_extra={"enum": ["portfolio"]})
    broker_ids: Optional[List[PositiveInt]] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Exact broker subset. None includes all brokers accessible to the user.",
    )
    asset_ids: Optional[List[PositiveInt]] = Field(
        None,
        min_length=1,
        max_length=100,
        description=("Exact asset subset of the portfolio. None includes every held asset. The scope stays 'portfolio', and weights are renormalized to 100% of the slice."),
    )
    apply_ownership_share: bool = Field(
        True,
        description="As the portfolio report's: True (default) an owner counts its share of each broker; False every broker counts whole, as an editor sees it — the broker page (D4), so its amounts (stress impacts, scope value) match the page's.",
    )

    @field_validator("broker_ids")
    @classmethod
    def normalize_broker_ids(cls, value: Optional[List[int]]) -> Optional[List[int]]:
        if value is None:
            return None
        if len(value) != len(set(value)):
            raise ValueError("broker_ids must be unique")
        return sorted(value)

    @field_validator("asset_ids")
    @classmethod
    def normalize_asset_ids(cls, value: Optional[List[int]]) -> Optional[List[int]]:
        if value is None:
            return None
        if len(value) != len(set(value)):
            raise ValueError("asset_ids must be unique")
        return sorted(value)


RiskScope = Annotated[
    Union[
        AssetRiskScope,
        AssetSetRiskScope,
        PortfolioRiskScope,
    ],
    Field(discriminator="kind"),
]


class RiskAnalyticRequest(StrictModel):
    """One independently executable analytic in a bulk risk query."""

    instance_id: str = Field(..., min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    analytic_code: str = Field(..., min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    parameters: Dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("parameters", mode="before")
    @classmethod
    def validate_parameters_json(cls, value: object) -> object:
        """A finite number wherever the parameters hold one (H-34): JsonValue alone lets a NaN or an Infinity through."""
        return ensure_json_safe(value, "parameters")


class RiskQueryRequest(StrictModel):
    """Bulk deterministic risk query sharing one scope and prepared data set."""

    scope: RiskScope
    date_range: DateRangeModel
    target_currency: str
    mode: RiskMode
    composition_policy: Optional[RiskCompositionPolicy] = None
    analytics: List[RiskAnalyticRequest] = Field(..., min_length=1, max_length=32)

    @field_validator("target_currency")
    @classmethod
    def validate_target_currency(cls, value: str) -> str:
        return Currency.validate_code(value)

    @model_validator(mode="after")
    def validate_query(self) -> RiskQueryRequest:
        instance_ids = [analytic.instance_id for analytic in self.analytics]
        if len(instance_ids) != len(set(instance_ids)):
            raise ValueError("analytic instance_id values must be unique")
        if self.mode == RiskMode.CURRENT_COMPOSITION:
            if self.composition_policy != RiskCompositionPolicy.CURRENT_BUY_AND_HOLD:
                raise ValueError("current_composition mode requires composition_policy='current_buy_and_hold'")
        elif self.composition_policy is not None:
            raise ValueError("composition_policy is only valid for current_composition mode")
        return self


class RiskCatalogDefinition(StrictModel):
    """Static definition published by one RiskAnalytic plugin."""

    analytic_code: str = Field(..., min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    name_i18n_key: str = Field(..., min_length=1)
    description_i18n_key: str = Field(..., min_length=1)
    output_kind: RiskOutputKind
    supported_scopes: List[RiskScopeKind] = Field(..., min_length=1)
    supported_modes: List[RiskMode] = Field(..., min_length=1)
    parameters_schema: Dict[str, JsonValue] = Field(default_factory=dict)
    min_observations: PositiveInt
    algorithm_version: str = Field(..., min_length=1)

    @field_validator("supported_scopes", "supported_modes")
    @classmethod
    def validate_unique_capabilities(cls, value: List[StrEnum]) -> List[StrEnum]:
        if len(value) != len(set(value)):
            raise ValueError("catalog capabilities must be unique")
        return value


class RiskCatalogResponse(StrictModel):
    items: List[RiskCatalogDefinition] = Field(default_factory=list)


class RiskEligibilityRequest(StrictModel):
    asset_ids: List[PositiveInt] = Field(..., min_length=1, max_length=500)
    date_range: DateRangeModel
    target_currency: str

    @field_validator("target_currency")
    @classmethod
    def validate_target_currency(cls, value: str) -> str:
        return Currency.validate_code(value)


class RiskAssetEligibility(StrictModel):
    asset_id: PositiveInt
    level: RiskEligibilityLevel
    reasons: List[RiskEligibilityReason] = Field(default_factory=list)
    first_quote: Optional[date] = Field(None, description="Earliest quote in the asset's history, up to the period end")
    last_quote: Optional[date] = Field(None, description="Latest quote on or before the period end")
    quotes_in_period: int = Field(..., ge=0)


class RiskEligibilityResponse(StrictModel):
    items: List[RiskAssetEligibility]
    min_quotes: int = Field(..., ge=1, description="Fewest quotes in the period an eligible asset needs")
    stale_days: int = Field(..., ge=1, description="Calendar days after which a start or an end counts as late")
    common_range: Optional[DateRangeModel] = Field(
        None,
        description="Span in which every requested asset with quotes is quoted, from the latest first quote to the earliest last quote; null when the spans do not overlap",
    )
    suggested_range: Optional[DateRangeModel] = Field(
        None,
        description=(
            "Period that makes every quoted asset eligible without warnings, offered only when the requested period starts before, ends after or misses the common span; "
            "it starts the day after the latest first quote, so that quote is the starting price. The requested period trimmed to the common span, or the common span itself"
        ),
    )
