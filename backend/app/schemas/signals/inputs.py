"""Signal inputs: price and event points, the input data, source capabilities, the execution context, warmup and input requirements, and the value sources."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import Field, FiniteFloat, JsonValue, field_validator, model_validator

from backend.app.schemas.common import BackwardFillInfo, DateRangeModel
from backend.app.schemas.risk.series import PreparedAssetSeries
from backend.app.schemas.signals.base import _KEY_PATTERN, SignalDecimal, SignalModel, _ensure_strictly_increasing, _ensure_unique, _inject_discriminator
from backend.app.schemas.signals.vocabulary import SignalBandComponent, SignalCadence, SignalDataPolicy, SignalDomain, SignalPriceField, SignalVolumeKind
from backend.app.utils.json_utils import ensure_json_safe


class SignalPricePoint(SignalModel):
    date: date
    open: Optional[SignalDecimal] = None
    high: Optional[SignalDecimal] = None
    low: Optional[SignalDecimal] = None
    close: SignalDecimal
    volume: Optional[SignalDecimal] = None
    backward_fill_info: Optional[BackwardFillInfo] = None


class SignalEventPoint(SignalModel):
    date: date
    type: str = Field(..., min_length=1)
    value: Optional[SignalDecimal] = None
    metadata: Dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, value: Any) -> Any:
        return ensure_json_safe(value, "metadata")


class SignalInputData(SignalModel):
    price_points: List[SignalPricePoint] = Field(default_factory=list)
    event_points: List[SignalEventPoint] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self) -> SignalInputData:
        _ensure_strictly_increasing([point.date for point in self.price_points], "price point")
        event_dates = [point.date for point in self.event_points]
        if any(current > following for current, following in zip(event_dates, event_dates[1:], strict=False)):
            raise ValueError("event point dates must be sorted")
        return self


class SignalSourceCapability(SignalModel):
    """Semantic capability declaration for the market-data source(s) backing
    the series a signal computes over.

    Distinct from `SignalInputCoverage` (which describes what data is
    *present*): this describes what the present data *means*. A source can
    have complete, finite, non-null volume and still fail
    `supports_meaningful_volume` — e.g. a source that never reports volume
    (`None` everywhere) trivially reports "complete" coverage of zero
    non-null values, while a source with unreliable/synthetic volume could
    still populate the field. Safe default: unknown/false, so callers that
    do not populate this (e.g. tests, FX contexts, ad-hoc scripts) never
    accidentally grant volume-dependent signals a capability nobody vouched
    for.
    """

    supports_meaningful_volume: bool = False
    volume_kind: SignalVolumeKind = SignalVolumeKind.UNKNOWN

    @model_validator(mode="after")
    def validate_capability(self) -> SignalSourceCapability:
        if not self.supports_meaningful_volume and self.volume_kind != SignalVolumeKind.UNKNOWN:
            raise ValueError("volume_kind requires supports_meaningful_volume=true")
        return self


class SignalExecutionContext(SignalModel):
    domain: SignalDomain
    requested_range: DateRangeModel
    cadence: SignalCadence = SignalCadence.DAILY
    data_policy: SignalDataPolicy = SignalDataPolicy.STRICT_CONTIGUOUS
    source_reference: str = Field(..., min_length=1)
    target_currency: Optional[str] = Field(None, min_length=3, max_length=3)
    observed_only: bool = False
    source_capability: SignalSourceCapability = Field(default_factory=SignalSourceCapability)
    primary_asset_series: Optional[PreparedAssetSeries] = Field(None, exclude=True)
    comparison_asset_series: Optional[PreparedAssetSeries] = Field(None, exclude=True)
    annualization_factor: Optional[FiniteFloat] = Field(None, gt=0, exclude=True)

    @field_validator("target_currency", mode="before")
    @classmethod
    def normalize_target_currency(cls, value: Any) -> Any:
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_prepared_series(self) -> SignalExecutionContext:
        if self.comparison_asset_series is not None and self.primary_asset_series is None:
            raise ValueError("comparison_asset_series requires primary_asset_series")
        if self.primary_asset_series is not None and self.target_currency is not None and self.primary_asset_series.valuations.target_currency != self.target_currency:
            raise ValueError("primary_asset_series currency must match target_currency")
        if self.comparison_asset_series is not None:
            if self.primary_asset_series is None:
                raise ValueError("comparison_asset_series requires primary_asset_series")
            if self.comparison_asset_series.valuations.target_currency != self.primary_asset_series.valuations.target_currency:
                raise ValueError("prepared asset series must use the same target currency")
        return self


class SignalWarmupRequirement(SignalModel):
    minimum_points: int = Field(..., ge=0, description="Minimum input units needed to produce the first valid output")
    stabilization_points: int = Field(..., ge=0, description="Additional pre-visible units required for numerical stabilization")
    total_points: int = Field(..., ge=0, description="Total input units requested before the visible range")
    normalized_tolerance: Optional[FiniteFloat] = Field(None, gt=0)
    # E1: indicators with unlimited memory (e.g. underwater drawdown — the
    # relevant peak may sit ANYWHERE in the past) cannot name a finite warm-up.
    # When True the fetch path loads from the beginning of the available
    # history instead of `total_points`-derived days, and the visible-range
    # slicing still happens after the computation.
    full_history: bool = Field(False, description="Load the entire available history before the visible range")

    @model_validator(mode="after")
    def validate_total(self) -> SignalWarmupRequirement:
        if self.total_points != self.minimum_points + self.stabilization_points:
            raise ValueError("total_points must equal minimum_points + stabilization_points")
        return self


class SignalWarmupMetadata(SignalModel):
    requirement: SignalWarmupRequirement
    loaded_points: int = Field(..., ge=0, description="Total price or event units loaded for the computation")
    used_points: int = Field(..., ge=0, description="Contiguous units before requested_start used as warm-up")
    complete: bool = Field(..., description="True when used_points satisfies total_points")

    @model_validator(mode="after")
    def validate_counts(self) -> SignalWarmupMetadata:
        if self.used_points > self.loaded_points:
            raise ValueError("used_points cannot exceed loaded_points")
        if self.complete and self.used_points < self.requirement.total_points:
            raise ValueError("complete warm-up requires used_points >= total_points")
        return self


class SignalInputRequirements(SignalModel):
    price_fields: List[SignalPriceField] = Field(default_factory=list)
    requires_events: bool = False
    event_types: List[str] = Field(default_factory=list)
    data_policy: SignalDataPolicy = SignalDataPolicy.STRICT_CONTIGUOUS
    minimum_coverage: FiniteFloat = Field(1.0, ge=0, le=1)
    uses_prepared_asset_series: bool = False
    comparison_asset_param: Optional[str] = Field(None, pattern=_KEY_PATTERN)
    requires_meaningful_volume: bool = Field(
        False,
        description=(
            "Declares that the plugin's semantics only hold when the source's volume "
            "field represents real, comparable trading activity (see "
            "SignalSourceCapability.supports_meaningful_volume) rather than being "
            "absent, synthetic, or of unverified origin. SignalService gates "
            "availability on this before invoking the plugin, independent of the "
            "structural presence/coverage of the volume field."
        ),
    )

    @model_validator(mode="after")
    def validate_requirements(self) -> SignalInputRequirements:
        _ensure_unique(self.price_fields, "price_fields")
        _ensure_unique(self.event_types, "event_types")
        if not self.price_fields and not self.requires_events:
            raise ValueError("signal requires price fields and/or events")
        if self.event_types and not self.requires_events:
            raise ValueError("event_types require requires_events=true")
        if self.comparison_asset_param is not None and not self.uses_prepared_asset_series:
            raise ValueError("comparison_asset_param requires uses_prepared_asset_series=true")
        if self.requires_meaningful_volume and SignalPriceField.VOLUME not in self.price_fields:
            raise ValueError("requires_meaningful_volume requires volume in price_fields")
        return self


class SignalPriceValueSource(SignalModel):
    kind: Literal["price"] = Field(json_schema_extra={"enum": ["price"]})
    field: SignalPriceField = SignalPriceField.CLOSE

    @model_validator(mode="before")
    @classmethod
    def default_kind(cls, value: Any) -> Any:
        return _inject_discriminator(value, kind="price")


class SignalOutputValueSource(SignalModel):
    kind: Literal["signal"] = Field(json_schema_extra={"enum": ["signal"]})
    instance_id: str = Field(..., min_length=1, max_length=128)
    series_key: str = Field(..., pattern=_KEY_PATTERN)

    @model_validator(mode="before")
    @classmethod
    def default_kind(cls, value: Any) -> Any:
        return _inject_discriminator(value, kind="signal")


class SignalBandValueSource(SignalModel):
    kind: Literal["band"] = Field(json_schema_extra={"enum": ["band"]})
    instance_id: str = Field(..., min_length=1, max_length=128)
    series_key: str = Field(..., pattern=_KEY_PATTERN)
    component: SignalBandComponent

    @model_validator(mode="before")
    @classmethod
    def default_kind(cls, value: Any) -> Any:
        return _inject_discriminator(value, kind="band")


SignalValueSource = Annotated[
    Union[SignalPriceValueSource, SignalOutputValueSource, SignalBandValueSource],
    Field(discriminator="kind"),
]
