"""Signal outputs: axes, styles, regions, the output spec, calendar-return provenance and the series a signal draws."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any, List, Literal, Optional, Union

from pydantic import Field, FiniteFloat, model_validator

from backend.app.schemas.signals.base import _KEY_PATTERN, NonNegativeInt, SignalModel, SignalSemanticDescription, SignalSemanticId, _ensure_strictly_increasing, _ensure_unique, _inject_discriminator
from backend.app.schemas.signals.vocabulary import SignalAggregationProfile, SignalAxisRole, SignalCalendarReturnPointStatus, SignalColorRole, SignalLinePattern, SignalSeriesKind, SignalUnit, SignalViewTransform


class SignalAxisSpec(SignalModel):
    key: str = Field(..., pattern=_KEY_PATTERN)
    role: SignalAxisRole
    minimum: Optional[FiniteFloat] = None
    maximum: Optional[FiniteFloat] = None

    @model_validator(mode="after")
    def validate_bounds(self) -> SignalAxisSpec:
        if self.minimum is not None and self.maximum is not None and self.minimum >= self.maximum:
            raise ValueError("axis minimum must be lower than maximum")
        return self


class SignalReferenceLevel(SignalModel):
    key: str = Field(..., pattern=_KEY_PATTERN)
    label_key: str = Field(..., min_length=1)
    semantic: str = Field(..., min_length=1)
    value: FiniteFloat


class SignalOutputStyle(SignalModel):
    color_role: SignalColorRole = SignalColorRole.PRIMARY
    line_pattern: Optional[SignalLinePattern] = None
    width_delta: int = Field(0, ge=-3, le=3)
    opacity: FiniteFloat = Field(1.0, gt=0, le=1)
    fill_opacity: FiniteFloat = Field(
        0.2,
        ge=0,
        le=1,
        description="Area fill opacity; used only by area outputs.",
    )


class SignalRegionLineStyle(SignalModel):
    pattern: SignalLinePattern
    color_role: SignalColorRole = SignalColorRole.PRIMARY
    width_delta: int = Field(0, ge=-3, le=3)
    opacity: FiniteFloat = Field(1.0, gt=0, le=1)


class SignalValueRegion(SignalModel):
    key: str = Field(..., pattern=_KEY_PATTERN)
    label_key: str = Field(..., min_length=1)
    description_key: Optional[str] = Field(None, min_length=1)
    semantic: str = Field(..., min_length=1)
    lower: Optional[FiniteFloat] = None
    upper: Optional[FiniteFloat] = None
    include_lower: bool = True
    include_upper: bool = False
    line_style: Optional[SignalRegionLineStyle] = None

    @model_validator(mode="after")
    def validate_bounds(self) -> SignalValueRegion:
        if self.lower is None and self.upper is None:
            raise ValueError("value region requires lower and/or upper bound")
        if self.lower is not None and self.upper is not None and self.lower >= self.upper:
            raise ValueError("value region lower bound must be lower than upper bound")
        return self


class SignalOutputBase(SignalModel):
    key: str = Field(..., pattern=_KEY_PATTERN)
    label_key: str = Field(..., min_length=1)
    description_key: Optional[str] = Field(None, min_length=1)
    semantic_id: SignalSemanticId
    semantic_description: SignalSemanticDescription
    unit: SignalUnit
    axis: SignalAxisSpec
    view_transform: SignalViewTransform = SignalViewTransform.NONE
    style: SignalOutputStyle = Field(default_factory=SignalOutputStyle)


class SignalOutputSpec(SignalOutputBase):
    kind: SignalSeriesKind
    aggregation_profile: SignalAggregationProfile = SignalAggregationProfile.LAST_WITH_RANGE
    supports_reference_levels: bool = False
    supports_value_regions: bool = False
    default_reference_levels: List[SignalReferenceLevel] = Field(default_factory=list)
    default_value_regions: List[SignalValueRegion] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_capabilities(self) -> SignalOutputSpec:
        if self.kind == SignalSeriesKind.BAND and self.aggregation_profile != SignalAggregationProfile.BAND_ENVELOPE:
            raise ValueError("band outputs require aggregation_profile=band_envelope")
        if self.kind != SignalSeriesKind.BAND and self.aggregation_profile == SignalAggregationProfile.BAND_ENVELOPE:
            raise ValueError("aggregation_profile=band_envelope requires a band output")
        if self.aggregation_profile == SignalAggregationProfile.EVENTS_VERBATIM:
            raise ValueError("events_verbatim is reserved for annotations, not continuous output series")
        if self.default_reference_levels and not self.supports_reference_levels:
            raise ValueError("default reference levels require supports_reference_levels=true")
        if self.default_value_regions and not self.supports_value_regions:
            raise ValueError("default value regions require supports_value_regions=true")
        _ensure_unique([level.key for level in self.default_reference_levels], "reference level keys")
        _ensure_unique([region.key for region in self.default_value_regions], "value region keys")
        return self


class SignalCalendarReturnProvenance(SignalModel):
    """Resolved observation identity for one calendar-return comparison."""

    status: SignalCalendarReturnPointStatus
    reference_target_date: date
    current_price_date: date
    current_price_days_back: NonNegativeInt
    reference_price_date: Optional[date] = None
    reference_price_days_back: Optional[NonNegativeInt] = None
    current_fx_date: Optional[date] = None
    current_fx_days_back: Optional[NonNegativeInt] = None
    reference_fx_date: Optional[date] = None
    reference_fx_days_back: Optional[NonNegativeInt] = None

    @model_validator(mode="after")
    def validate_provenance(self) -> SignalCalendarReturnProvenance:
        for date_field, days_field in (
            ("reference_price_date", "reference_price_days_back"),
            ("current_fx_date", "current_fx_days_back"),
            ("reference_fx_date", "reference_fx_days_back"),
        ):
            if (getattr(self, date_field) is None) != (getattr(self, days_field) is None):
                raise ValueError(f"{date_field} and {days_field} must be set together")
        reference_present = self.reference_price_date is not None
        if self.status == SignalCalendarReturnPointStatus.MISSING_REFERENCE and reference_present:
            raise ValueError("missing_reference cannot carry a resolved reference price")
        if (
            self.status
            in (
                SignalCalendarReturnPointStatus.AVAILABLE,
                SignalCalendarReturnPointStatus.INVALID_REFERENCE_PRICE,
            )
            and not reference_present
        ):
            raise ValueError(f"{self.status.value} requires a resolved reference price")
        return self


class SignalValuePoint(SignalModel):
    date: date
    value: Optional[FiniteFloat] = None


class SignalCalendarReturnValuePoint(SignalValuePoint):
    """Calendar-return value with signal-owned, non-empty provenance."""

    provenance: SignalCalendarReturnProvenance


SignalScalarValuePoint = Union[
    SignalCalendarReturnValuePoint,
    SignalValuePoint,
]


class SignalBandPoint(SignalModel):
    date: date
    lower: Optional[FiniteFloat] = None
    middle: Optional[FiniteFloat] = None
    upper: Optional[FiniteFloat] = None

    @model_validator(mode="after")
    def validate_order(self) -> SignalBandPoint:
        present = [value for value in (self.lower, self.middle, self.upper) if value is not None]
        if any(current > following for current, following in zip(present, present[1:], strict=False)):
            raise ValueError("band values must satisfy lower <= middle <= upper")
        return self


class SignalSeriesBase(SignalOutputBase):
    reference_levels: List[SignalReferenceLevel] = Field(default_factory=list)
    value_regions: List[SignalValueRegion] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_semantic_keys(self) -> SignalSeriesBase:
        _ensure_unique([level.key for level in self.reference_levels], "reference level keys")
        _ensure_unique([region.key for region in self.value_regions], "value region keys")
        return self


class SignalScalarSeriesBase(SignalSeriesBase):
    points: List[SignalScalarValuePoint] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_points(self) -> SignalScalarSeriesBase:
        _ensure_strictly_increasing([point.date for point in self.points], "series point")
        if not any(point.value is not None for point in self.points):
            raise ValueError("series must contain at least one finite value")
        return self


class SignalLineSeries(SignalScalarSeriesBase):
    kind: Literal["line"] = Field(json_schema_extra={"enum": ["line"]})

    @model_validator(mode="before")
    @classmethod
    def default_kind(cls, value: Any) -> Any:
        return _inject_discriminator(value, kind="line")


class SignalAreaSeries(SignalScalarSeriesBase):
    kind: Literal["area"] = Field(json_schema_extra={"enum": ["area"]})

    @model_validator(mode="before")
    @classmethod
    def default_kind(cls, value: Any) -> Any:
        return _inject_discriminator(value, kind="area")


class SignalBarSeries(SignalScalarSeriesBase):
    kind: Literal["bar"] = Field(json_schema_extra={"enum": ["bar"]})

    @model_validator(mode="before")
    @classmethod
    def default_kind(cls, value: Any) -> Any:
        return _inject_discriminator(value, kind="bar")


class SignalBandSeries(SignalSeriesBase):
    kind: Literal["band"] = Field(json_schema_extra={"enum": ["band"]})
    points: List[SignalBandPoint] = Field(..., min_length=1)

    @model_validator(mode="before")
    @classmethod
    def default_kind(cls, value: Any) -> Any:
        return _inject_discriminator(value, kind="band")

    @model_validator(mode="after")
    def validate_points(self) -> SignalBandSeries:
        _ensure_strictly_increasing([point.date for point in self.points], "series point")
        if not any(point.lower is not None or point.middle is not None or point.upper is not None for point in self.points):
            raise ValueError("band series must contain at least one finite value")
        return self


SignalSeries = Annotated[
    Union[SignalLineSeries, SignalAreaSeries, SignalBarSeries, SignalBandSeries],
    Field(discriminator="kind"),
]
