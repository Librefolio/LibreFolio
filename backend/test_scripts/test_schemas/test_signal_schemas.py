"""Tests for library-independent technical signal contracts."""

from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from itertools import product
from typing import Any, Literal

import pytest
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator

from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.fx import FXConversionRequest
from backend.app.schemas.portfolio import DataQualityReport
from backend.app.schemas.prices import FAPriceQueryItem
from backend.app.schemas.risk import RiskResultMetadata, RiskReturnBasis
from backend.app.schemas.signals import (
    SignalAggregationProfile,
    SignalAiDescription,
    SignalAiOutputDescription,
    SignalAnnotationRequest,
    SignalAnnotationSampling,
    SignalAreaSeries,
    SignalAvailability,
    SignalAvailabilityReason,
    SignalAxisRole,
    SignalAxisSpec,
    SignalBandComponent,
    SignalBandPoint,
    SignalBandSeries,
    SignalBandValueSource,
    SignalCalendarReturnPointStatus,
    SignalCalendarReturnProvenance,
    SignalCalendarReturnValuePoint,
    SignalCatalogDefinition,
    SignalCatalogResponse,
    SignalCategory,
    SignalColorRole,
    SignalComputation,
    SignalDataPolicy,
    SignalDomain,
    SignalError,
    SignalErrorCode,
    SignalEventPoint,
    SignalExecutionContext,
    SignalInputCoverage,
    SignalInputData,
    SignalInputRequirements,
    SignalLineCrossoverRequest,
    SignalLinePattern,
    SignalLineSeries,
    SignalOutputSpec,
    SignalOutputStyle,
    SignalOutputValueSource,
    SignalPriceField,
    SignalPricePoint,
    SignalPriceValueSource,
    SignalReferenceLevel,
    SignalRegionLineStyle,
    SignalRequest,
    SignalResult,
    SignalSeries,
    SignalSeriesKind,
    SignalSourceCapability,
    SignalStatus,
    SignalThresholdCrossingRequest,
    SignalThresholdDirection,
    SignalUnit,
    SignalValuePoint,
    SignalValueRegion,
    SignalValueSource,
    SignalViewTransform,
    SignalVolumeKind,
    SignalWarmupMetadata,
    SignalWarmupRequirement,
    SignalWarning,
    SignalWarningCode,
)

DAY_1 = date(2026, 1, 1)
DAY_2 = date(2026, 1, 2)
DAY_3 = date(2026, 1, 3)
_DEFAULT = object()


def make_axis() -> SignalAxisSpec:
    return SignalAxisSpec(key="price", role=SignalAxisRole.PRICE)


def make_line_series(
    key: str = "ema",
    dates: tuple[date, ...] = (DAY_1, DAY_2),
    values: tuple[float | None, ...] = (100.0, 101.0),
) -> SignalLineSeries:
    return SignalLineSeries(
        key=key,
        label_key=f"signals.{key}.label",
        semantic_id=f"test.{key}",
        semantic_description=f"Test semantic value for {key}.",
        unit=SignalUnit.PRICE,
        axis=make_axis(),
        view_transform=SignalViewTransform.BASE_PERCENTAGE,
        points=[SignalValuePoint(date=point_date, value=value) for point_date, value in zip(dates, values, strict=True)],
    )


# I10 — additive, sparse provenance for ASSET_CALENDAR_ROLLING_RETURN. The
# public field names are pinned here on purpose: they are the wire contract the
# frontend and the AI Export layer read, and nothing else in the suite would
# notice a silent rename.
CALENDAR_PROVENANCE_FIELDS = (
    "status",
    "reference_target_date",
    "current_price_date",
    "current_price_days_back",
    "reference_price_date",
    "reference_price_days_back",
    "current_fx_date",
    "current_fx_days_back",
    "reference_fx_date",
    "reference_fx_days_back",
)


def make_calendar_provenance(
    status: SignalCalendarReturnPointStatus = SignalCalendarReturnPointStatus.AVAILABLE,
    *,
    reference_target_date: date = DAY_1,
    current_price_date: date = DAY_3,
    with_fx: bool = False,
) -> SignalCalendarReturnProvenance:
    fx_fields = (
        {
            "current_fx_date": DAY_2,
            "current_fx_days_back": 1,
            "reference_fx_date": DAY_1,
            "reference_fx_days_back": 2,
        }
        if with_fx
        else {}
    )
    return SignalCalendarReturnProvenance(
        status=status,
        reference_target_date=reference_target_date,
        current_price_date=current_price_date,
        current_price_days_back=0,
        reference_price_date=(None if status == SignalCalendarReturnPointStatus.MISSING_REFERENCE else reference_target_date),
        reference_price_days_back=(None if status == SignalCalendarReturnPointStatus.MISSING_REFERENCE else 0),
        **fx_fields,
    )


def make_calendar_series(
    key: str = "calendar_return",
    dates: tuple[date, ...] = (DAY_1, DAY_2),
    values: tuple[float | None, ...] = (None, 2.5),
) -> SignalLineSeries:
    return SignalLineSeries(
        key=key,
        label_key=f"signals.{key}.label",
        semantic_id=f"test.{key}",
        semantic_description=f"Test calendar semantic value for {key}.",
        unit=SignalUnit.PERCENTAGE,
        axis=SignalAxisSpec(key="calendar_return", role=SignalAxisRole.INDEPENDENT),
        points=[
            SignalCalendarReturnValuePoint(
                date=point_date,
                value=value,
                provenance=make_calendar_provenance(
                    status=(SignalCalendarReturnPointStatus.MISSING_REFERENCE if value is None else SignalCalendarReturnPointStatus.AVAILABLE),
                    reference_target_date=point_date - timedelta(days=30),
                    current_price_date=point_date,
                ),
            )
            for point_date, value in zip(dates, values, strict=True)
        ],
    )


def make_coverage(
    requested: int = 2,
    available: int = 2,
    contiguous: int = 2,
    observed: int = 2,
    backfilled: int = 0,
) -> SignalInputCoverage:
    return SignalInputCoverage(
        requested_points=requested,
        available_points=available,
        contiguous_points=contiguous,
        observed_points=observed,
        backfilled_points=backfilled,
        missing_points=requested - available,
        internal_gap_count=0,
        coverage_ratio=available / requested if requested else 0.0,
        field_coverage={SignalPriceField.CLOSE: available / requested if requested else 0.0},
        first_available_date=DAY_1 if available else None,
        last_available_date=DAY_2 if available else None,
    )


def make_requirement() -> SignalWarmupRequirement:
    return SignalWarmupRequirement(
        minimum_points=2,
        stabilization_points=1,
        total_points=3,
        normalized_tolerance=1e-6,
    )


def make_warmup(complete: bool = True) -> SignalWarmupMetadata:
    return SignalWarmupMetadata(
        requirement=make_requirement(),
        loaded_points=3 if complete else 2,
        used_points=3 if complete else 2,
        complete=complete,
    )


def make_availability(
    can_compute: bool = True,
    warmup_complete: bool = True,
    reason: SignalAvailabilityReason | None = None,
    partial_coverage_used: bool = False,
) -> SignalAvailability:
    coverage = make_coverage() if can_compute else make_coverage(requested=2, available=0, contiguous=0, observed=0)
    return SignalAvailability(
        domain_compatible=True,
        can_compute=can_compute,
        missing_price_fields=[] if can_compute else [SignalPriceField.CLOSE],
        input_coverage=coverage,
        required_points=3,
        warmup_complete=warmup_complete,
        partial_coverage_used=partial_coverage_used,
        reason_code=reason,
    )


def make_result(
    status: SignalStatus,
    *,
    series: list | None = None,
    availability: SignalAvailability | None | object = _DEFAULT,
    warmup: SignalWarmupMetadata | None | object = _DEFAULT,
    warnings: list[SignalWarning] | None = None,
    error: SignalError | None = None,
    risk_metadata: RiskResultMetadata | None = None,
    data_quality: DataQualityReport | None = None,
) -> SignalResult:
    return SignalResult(
        instance_id="signal-1",
        signal_code="ema",
        implementation_version="1.0.0",
        normalized_params={"length": 20},
        status=status,
        series=series or [],
        availability=make_availability() if availability is _DEFAULT else availability,
        warmup=make_warmup() if warmup is _DEFAULT else warmup,
        warnings=warnings or [],
        error=error,
        risk_metadata=risk_metadata,
        data_quality=data_quality,
    )


class DemoParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    length: int = Field(
        20,
        ge=2,
        le=500,
        json_schema_extra={
            "x-i18n-key": "signals.params.length",
            "x-control-order": 1,
            "x-step": 1,
            "x-tooltip-key": "signals.params.lengthTooltip",
        },
    )
    mode: Literal["fast", "slow"] = "fast"


def make_output_spec() -> SignalOutputSpec:
    return SignalOutputSpec(
        key="ema",
        label_key="signals.ema.output",
        semantic_id="exponential_moving_average.value",
        semantic_description="Exponentially weighted closing-price average.",
        kind=SignalSeriesKind.LINE,
        aggregation_profile=SignalAggregationProfile.LAST_WITH_RANGE,
        unit=SignalUnit.PRICE,
        axis=make_axis(),
        view_transform=SignalViewTransform.BASE_PERCENTAGE,
    )


def make_catalog() -> SignalCatalogDefinition:
    return SignalCatalogDefinition(
        signal_code="ema",
        implementation_version="1.0.0",
        category=SignalCategory.TREND,
        display_name_key="signals.ema.name",
        description_key="signals.ema.description",
        semantic_id="exponential_moving_average",
        semantic_description="Smooths prices with greater weight on recent observations.",
        icon="activity",
        docs_path="financial-theory/technical-analysis/indicators/ema/",
        params_schema=DemoParams.model_json_schema(),
        default_params=DemoParams().model_dump(mode="json"),
        input_requirements=SignalInputRequirements(price_fields=[SignalPriceField.CLOSE]),
        output_specs=[make_output_spec()],
        compatible_domains=[SignalDomain.ASSET, SignalDomain.FX],
    )


class TestNeutralInputs:
    @pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
    def test_price_point_rejects_non_finite_decimal(self, value: Decimal):
        with pytest.raises(ValidationError, match="finite"):
            SignalPricePoint(date=DAY_1, close=value)

    def test_event_metadata_must_be_json_safe(self):
        with pytest.raises(ValidationError, match="non-finite"):
            SignalEventPoint(date=DAY_1, type="DIVIDEND", metadata={"ratio": float("nan")})

    def test_input_dates_are_strictly_increasing(self):
        with pytest.raises(ValidationError, match="strictly increasing"):
            SignalInputData(
                price_points=[
                    SignalPricePoint(date=DAY_2, close=Decimal("2")),
                    SignalPricePoint(date=DAY_1, close=Decimal("1")),
                ]
            )

    def test_duplicate_price_dates_are_rejected(self):
        with pytest.raises(ValidationError, match="strictly increasing"):
            SignalInputData(
                price_points=[
                    SignalPricePoint(date=DAY_1, close=Decimal("1")),
                    SignalPricePoint(date=DAY_1, close=Decimal("2")),
                ]
            )

    def test_multiple_events_on_same_date_are_allowed(self):
        data = SignalInputData(
            event_points=[
                SignalEventPoint(date=DAY_1, type="DIVIDEND"),
                SignalEventPoint(date=DAY_1, type="SPLIT"),
            ]
        )
        assert len(data.event_points) == 2

    def test_execution_context_normalizes_currency(self):
        context = SignalExecutionContext(
            domain=SignalDomain.ASSET,
            requested_range=DateRangeModel(start=DAY_1, end=DAY_2),
            source_reference="asset:42",
            target_currency=" eur ",
            observed_only=True,
        )
        assert context.target_currency == "EUR"
        assert context.data_policy == SignalDataPolicy.STRICT_CONTIGUOUS

    def test_execution_context_defaults_to_unsupported_source_capability(self):
        """Safe-by-default: contexts built without an explicit capability
        never accidentally grant meaningful-volume trust."""
        context = SignalExecutionContext(
            domain=SignalDomain.ASSET,
            requested_range=DateRangeModel(start=DAY_1, end=DAY_2),
            source_reference="asset:42",
        )
        assert context.source_capability.supports_meaningful_volume is False
        assert context.source_capability.volume_kind == SignalVolumeKind.UNKNOWN


class TestSignalSourceCapability:
    def test_default_is_unsupported_and_unknown(self):
        capability = SignalSourceCapability()
        assert capability.supports_meaningful_volume is False
        assert capability.volume_kind == SignalVolumeKind.UNKNOWN

    def test_supported_capability_can_declare_traded_shares(self):
        capability = SignalSourceCapability(supports_meaningful_volume=True, volume_kind=SignalVolumeKind.TRADED_SHARES)
        assert capability.supports_meaningful_volume is True
        assert capability.volume_kind == SignalVolumeKind.TRADED_SHARES

    def test_unsupported_capability_rejects_a_declared_volume_kind(self):
        """A source that doesn't support meaningful volume can't claim a
        specific volume kind — prevents inconsistent half-declarations."""
        with pytest.raises(ValidationError, match="volume_kind"):
            SignalSourceCapability(supports_meaningful_volume=False, volume_kind=SignalVolumeKind.TRADED_SHARES)


class TestWarmupAndRequirements:
    def test_warmup_total_must_match_components(self):
        with pytest.raises(ValidationError, match="must equal"):
            SignalWarmupRequirement(minimum_points=20, stabilization_points=80, total_points=99)

    def test_complete_warmup_requires_enough_loaded_points(self):
        with pytest.raises(ValidationError, match="used_points"):
            SignalWarmupMetadata(requirement=make_requirement(), loaded_points=3, used_points=2, complete=True)

    def test_zero_point_warmup_supports_event_only_plugins(self):
        requirement = SignalWarmupRequirement(minimum_points=0, stabilization_points=0, total_points=0)
        metadata = SignalWarmupMetadata(requirement=requirement, loaded_points=0, used_points=0, complete=True)
        assert metadata.complete is True

    def test_required_price_fields_are_unique(self):
        with pytest.raises(ValidationError, match="duplicates"):
            SignalInputRequirements(price_fields=[SignalPriceField.CLOSE, SignalPriceField.CLOSE])

    def test_event_types_require_event_loading(self):
        with pytest.raises(ValidationError, match="requires_events"):
            SignalInputRequirements(price_fields=[SignalPriceField.CLOSE], event_types=["DIVIDEND"])

    def test_event_only_requirements_are_supported(self):
        requirements = SignalInputRequirements(requires_events=True, event_types=["DIVIDEND"])
        assert requirements.price_fields == []
        assert requirements.requires_events is True

    def test_requirements_need_prices_or_events(self):
        with pytest.raises(ValidationError, match="price fields and/or events"):
            SignalInputRequirements()

    def test_comparison_asset_dependency_requires_prepared_series(self):
        with pytest.raises(
            ValidationError,
            match="uses_prepared_asset_series",
        ):
            SignalInputRequirements(
                price_fields=[SignalPriceField.CLOSE],
                comparison_asset_param="comparison_asset_id",
            )

        requirements = SignalInputRequirements(
            price_fields=[SignalPriceField.CLOSE],
            uses_prepared_asset_series=True,
            comparison_asset_param="comparison_asset_id",
        )
        assert requirements.comparison_asset_param == "comparison_asset_id"

    def test_requires_meaningful_volume_needs_volume_price_field(self):
        with pytest.raises(ValidationError, match="requires_meaningful_volume"):
            SignalInputRequirements(
                price_fields=[SignalPriceField.CLOSE],
                requires_meaningful_volume=True,
            )

    def test_requires_meaningful_volume_is_accepted_with_volume_field(self):
        requirements = SignalInputRequirements(
            price_fields=[SignalPriceField.CLOSE, SignalPriceField.VOLUME],
            requires_meaningful_volume=True,
        )
        assert requirements.requires_meaningful_volume is True


class TestOutputContracts:
    @pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
    def test_output_points_reject_non_finite_float(self, value: float):
        with pytest.raises(ValidationError):
            SignalValuePoint(date=DAY_1, value=value)

    def test_axis_bounds_are_ordered(self):
        with pytest.raises(ValidationError, match="minimum"):
            SignalAxisSpec(key="oscillator", role=SignalAxisRole.INDEPENDENT, minimum=100, maximum=0)

    def test_region_requires_valid_bounds(self):
        with pytest.raises(ValidationError, match="requires lower"):
            SignalValueRegion(key="neutral", label_key="signals.neutral", semantic="neutral")
        with pytest.raises(ValidationError, match="lower bound"):
            SignalValueRegion(key="neutral", label_key="signals.neutral", semantic="neutral", lower=70, upper=30)

    def test_region_can_declare_line_style(self):
        region = SignalValueRegion(
            key="neutral",
            label_key="signals.neutral",
            semantic="neutral",
            lower=30,
            upper=70,
            line_style=SignalRegionLineStyle(
                pattern=SignalLinePattern.DASHED,
                width_delta=1,
            ),
        )

        assert region.line_style is not None
        assert region.line_style.pattern == SignalLinePattern.DASHED
        with pytest.raises(ValidationError):
            SignalRegionLineStyle(pattern=SignalLinePattern.SOLID, width_delta=4)

    def test_output_can_declare_plugin_owned_visual_style(self):
        output = SignalOutputSpec(
            key="plus_di",
            label_key="signals.adx.plusDi",
            description_key="signals.adx.plusDiDescription",
            semantic_id="average_directional_index.positive_directional_index",
            semantic_description="Positive directional movement relative to true range.",
            kind=SignalSeriesKind.LINE,
            aggregation_profile=SignalAggregationProfile.LAST_WITH_RANGE,
            unit=SignalUnit.INDEX,
            axis=SignalAxisSpec(key="adx", role=SignalAxisRole.INDEPENDENT),
            style=SignalOutputStyle(
                color_role=SignalColorRole.POSITIVE,
                line_pattern=SignalLinePattern.SOLID,
                width_delta=1,
                opacity=0.8,
            ),
        )

        assert output.style.color_role == SignalColorRole.POSITIVE
        assert output.style.line_pattern == SignalLinePattern.SOLID
        assert output.description_key == "signals.adx.plusDiDescription"

    def test_area_series_round_trips_through_discriminated_union(self):
        payload = make_line_series().model_dump(mode="json")
        payload["kind"] = SignalSeriesKind.AREA.value

        parsed = TypeAdapter(SignalSeries).validate_python(payload)

        assert isinstance(parsed, SignalAreaSeries)
        assert parsed.model_dump(mode="json")["kind"] == "area"

    @pytest.mark.parametrize("fill_opacity", [-0.01, 1.01])
    def test_output_style_rejects_invalid_fill_opacity(self, fill_opacity: float):
        with pytest.raises(ValidationError, match="fill_opacity"):
            SignalOutputStyle(fill_opacity=fill_opacity)

    def test_output_spec_rejects_incompatible_aggregation_profiles(self):
        band_payload = make_output_spec().model_dump(mode="python")
        band_payload["kind"] = SignalSeriesKind.BAND
        with pytest.raises(ValidationError, match="band outputs require"):
            SignalOutputSpec.model_validate(band_payload)

        line_payload = make_output_spec().model_dump(mode="python")
        line_payload["aggregation_profile"] = SignalAggregationProfile.BAND_ENVELOPE
        with pytest.raises(ValidationError, match="requires a band output"):
            SignalOutputSpec.model_validate(line_payload)

        event_payload = make_output_spec().model_dump(mode="python")
        event_payload["aggregation_profile"] = SignalAggregationProfile.EVENTS_VERBATIM
        with pytest.raises(ValidationError, match="reserved for annotations"):
            SignalOutputSpec.model_validate(event_payload)

    def test_aggregation_profile_enum_is_json_serializable(self):
        payload = make_output_spec().model_dump(mode="json")
        schema = SignalOutputSpec.model_json_schema()

        assert payload["aggregation_profile"] == "last_with_range"
        aggregation_schema = schema["properties"]["aggregation_profile"]
        enum_ref = aggregation_schema["$ref"].split("/")[-1]
        assert schema["$defs"][enum_ref]["enum"] == [
            "last_with_range",
            "first_with_range",
            "min_with_range",
            "max_with_range",
            "band_envelope",
            "events_verbatim",
        ]

    def test_output_semantics_are_required_and_canonical(self):
        payload = make_output_spec().model_dump(mode="python")
        payload.pop("semantic_id")
        with pytest.raises(ValidationError, match="semantic_id"):
            SignalOutputSpec.model_validate(payload)

        payload = make_output_spec().model_dump(mode="python")
        payload.pop("semantic_description")
        with pytest.raises(ValidationError, match="semantic_description"):
            SignalOutputSpec.model_validate(payload)

        for invalid_id in ("UpperCase", "contains space", "trailing.", ".leading", "double..dot"):
            payload = make_output_spec().model_dump(mode="python")
            payload["semantic_id"] = invalid_id
            with pytest.raises(ValidationError, match="semantic_id"):
                SignalOutputSpec.model_validate(payload)

    @pytest.mark.parametrize(
        "word",
        ["buy", "buys", "buying", "bought", "sell", "sells", "selling", "sold"],
    )
    def test_semantic_descriptions_reject_standalone_prescriptive_words(self, word: str):
        payload = make_output_spec().model_dump(mode="python")
        payload["semantic_description"] = f"Indicates when to {word}."
        with pytest.raises(ValidationError, match="neutral and non-prescriptive"):
            SignalOutputSpec.model_validate(payload)

        catalog = make_catalog().model_dump(mode="python")
        catalog["semantic_description"] = f"A {word} signal."
        with pytest.raises(ValidationError, match="neutral and non-prescriptive"):
            SignalCatalogDefinition.model_validate(catalog)

    def test_semantic_descriptions_allow_embedded_non_prescriptive_words(self):
        payload = make_output_spec().model_dump(mode="python")
        payload["semantic_description"] = "Describes buyer and seller pressure without instruction."
        output = SignalOutputSpec.model_validate(payload)
        assert output.semantic_description == payload["semantic_description"]

    def test_output_spec_rejects_unadvertised_defaults(self):
        with pytest.raises(ValidationError, match="supports_reference_levels"):
            SignalOutputSpec(
                key="rsi",
                label_key="signals.rsi.output",
                semantic_id="relative_strength_index.value",
                semantic_description="Bounded ratio of smoothed gains to total directional movement.",
                kind=SignalSeriesKind.LINE,
                aggregation_profile=SignalAggregationProfile.LAST_WITH_RANGE,
                unit=SignalUnit.INDEX,
                axis=SignalAxisSpec(key="rsi", role=SignalAxisRole.INDEPENDENT, minimum=0, maximum=100),
                default_reference_levels=[
                    SignalReferenceLevel(
                        key="overbought",
                        label_key="signals.rsi.overbought",
                        semantic="overbought",
                        value=70,
                    )
                ],
            )

    def test_scalar_series_requires_finite_output(self):
        with pytest.raises(ValidationError, match="at least one finite"):
            make_line_series(values=(None, None))

    def test_band_series_supports_optional_components_but_needs_a_value(self):
        band = SignalBandSeries(
            key="bollinger",
            label_key="signals.bollinger.output",
            semantic_id="bollinger_bands.envelope",
            semantic_description="Lower, middle, and upper bands around the moving average.",
            unit=SignalUnit.PRICE,
            axis=make_axis(),
            points=[
                SignalBandPoint(date=DAY_1, lower=None, middle=None, upper=None),
                SignalBandPoint(date=DAY_2, lower=90, middle=100, upper=110),
            ],
        )
        assert band.kind == "band"
        with pytest.raises(ValidationError, match="at least one finite"):
            SignalBandSeries(
                key="empty",
                label_key="signals.empty",
                semantic_id="test.empty_band",
                semantic_description="Test empty band.",
                unit=SignalUnit.PRICE,
                axis=make_axis(),
                points=[SignalBandPoint(date=DAY_1)],
            )

    def test_band_point_rejects_inverted_values(self):
        with pytest.raises(ValidationError, match="lower <= middle <= upper"):
            SignalBandPoint(date=DAY_1, lower=110, middle=100, upper=90)

    def test_discriminated_union_supports_line_bar_band_and_composite(self):
        payload = {
            "series": [
                make_line_series("macd").model_dump(mode="json"),
                {
                    **make_line_series("signal").model_dump(mode="json"),
                    "kind": "line",
                },
                {
                    **make_line_series("histogram").model_dump(mode="json"),
                    "kind": "bar",
                },
            ]
        }
        computation = SignalComputation.model_validate(payload)
        assert [series.kind for series in computation.series] == ["line", "line", "bar"]
        schema_text = json.dumps(SignalComputation.model_json_schema())
        assert '"discriminator"' in schema_text
        assert '"line"' in schema_text
        assert '"bar"' in schema_text
        assert '"band"' in schema_text

    def test_unknown_series_kind_is_rejected(self):
        payload = make_line_series().model_dump(mode="json")
        payload["kind"] = "candlestick"
        with pytest.raises(ValidationError, match="union_tag_invalid"):
            SignalComputation.model_validate({"series": [payload]})

    def test_composite_series_dates_and_cardinality_must_match(self):
        with pytest.raises(ValidationError, match="identical dates and cardinality"):
            SignalComputation(
                series=[
                    make_line_series("one"),
                    make_line_series("two", dates=(DAY_1, DAY_3)),
                ]
            )

    def test_composite_series_semantic_ids_must_be_unique(self):
        first = make_line_series("one")
        second = make_line_series("two").model_dump(mode="python")
        second["semantic_id"] = first.semantic_id
        with pytest.raises(ValidationError, match="series semantic_ids"):
            SignalComputation.model_validate(
                {
                    "series": [
                        first.model_dump(mode="python"),
                        second,
                    ]
                }
            )

    def test_effective_reference_levels_and_regions_are_in_result(self):
        series = make_line_series("rsi")
        series.reference_levels = [
            SignalReferenceLevel(
                key="overbought",
                label_key="signals.rsi.overbought",
                semantic="overbought",
                value=70,
            )
        ]
        series.value_regions = [
            SignalValueRegion(
                key="overbought",
                label_key="signals.rsi.overboughtRegion",
                semantic="overbought",
                lower=70,
            )
        ]
        result = make_result(SignalStatus.OK, series=[series])
        dumped = result.model_dump(mode="json")
        assert dumped["series"][0]["reference_levels"][0]["value"] == 70.0
        assert dumped["series"][0]["style"]["color_role"] == "primary"
        assert "#" not in json.dumps(dumped)


class TestCoverageAndAvailability:
    def test_valid_coverage_serializes_enum_keys(self):
        dumped = make_coverage().model_dump(mode="json")
        assert dumped["field_coverage"] == {"close": 1.0}

    def test_coverage_ratio_must_match_counts(self):
        with pytest.raises(ValidationError, match="coverage_ratio"):
            SignalInputCoverage(
                requested_points=10,
                available_points=5,
                contiguous_points=5,
                observed_points=5,
                backfilled_points=0,
                missing_points=5,
                internal_gap_count=1,
                coverage_ratio=0.9,
            )

    def test_observed_and_backfilled_must_match_available(self):
        with pytest.raises(ValidationError, match="must equal"):
            SignalInputCoverage(
                requested_points=10,
                available_points=5,
                contiguous_points=5,
                observed_points=3,
                backfilled_points=1,
                missing_points=5,
                internal_gap_count=1,
                coverage_ratio=0.5,
            )

    def test_missing_points_and_internal_gaps_are_consistent(self):
        with pytest.raises(ValidationError, match="missing_points"):
            SignalInputCoverage(
                requested_points=10,
                available_points=8,
                contiguous_points=8,
                observed_points=8,
                backfilled_points=0,
                missing_points=1,
                internal_gap_count=1,
                coverage_ratio=0.8,
            )
        with pytest.raises(ValidationError, match="internal_gap_count"):
            SignalInputCoverage(
                requested_points=10,
                available_points=8,
                contiguous_points=8,
                observed_points=8,
                backfilled_points=0,
                missing_points=2,
                internal_gap_count=3,
                coverage_ratio=0.8,
            )

    def test_full_coverage_must_be_contiguous(self):
        with pytest.raises(ValidationError, match="full coverage"):
            SignalInputCoverage(
                requested_points=10,
                available_points=10,
                contiguous_points=9,
                observed_points=10,
                backfilled_points=0,
                missing_points=0,
                internal_gap_count=0,
                coverage_ratio=1.0,
            )

    def test_event_counts_are_representable(self):
        coverage = make_coverage()
        coverage.event_type_counts = {"DIVIDEND": 2, "SPLIT": 1}
        assert coverage.model_dump(mode="json")["event_type_counts"] == {"DIVIDEND": 2, "SPLIT": 1}

    def test_unavailable_input_requires_reason(self):
        with pytest.raises(ValidationError, match="reason_code"):
            make_availability(can_compute=False)

    def test_computable_input_cannot_have_missing_fields(self):
        with pytest.raises(ValidationError, match="missing required inputs"):
            SignalAvailability(
                domain_compatible=True,
                can_compute=True,
                missing_price_fields=[SignalPriceField.CLOSE],
                input_coverage=make_coverage(),
                required_points=3,
                warmup_complete=True,
            )

    def test_event_only_unavailability_is_representable(self):
        availability = SignalAvailability(
            domain_compatible=True,
            can_compute=False,
            missing_event_types=["DIVIDEND"],
            input_coverage=SignalInputCoverage(
                requested_points=0,
                available_points=0,
                contiguous_points=0,
                observed_points=0,
                backfilled_points=0,
                missing_points=0,
                internal_gap_count=0,
                coverage_ratio=0,
                event_type_counts={},
            ),
            required_points=0,
            warmup_complete=True,
            reason_code=SignalAvailabilityReason.MISSING_EVENT_TYPES,
        )
        assert availability.missing_event_types == ["DIVIDEND"]

    def test_partial_coverage_flag_matches_reason(self):
        with pytest.raises(ValidationError, match="partial_coverage_used"):
            SignalAvailability(
                domain_compatible=True,
                can_compute=True,
                input_coverage=make_coverage(requested=2, available=1, contiguous=1, observed=1),
                required_points=3,
                warmup_complete=True,
                partial_coverage_used=False,
                reason_code=SignalAvailabilityReason.PARTIAL_INPUT_COVERAGE,
            )


class TestRequestAndCatalog:
    def test_request_normalizes_code_and_rejects_extra_fields(self):
        request = SignalRequest(instance_id=" signal-1 ", signal_code=" ema ", params={"length": 20})
        assert request.instance_id == "signal-1"
        assert request.signal_code == "EMA"
        with pytest.raises(ValidationError, match="extra_forbidden"):
            SignalRequest(instance_id="x", signal_code="EMA", params={}, style={"color": "red"})

    def test_request_rejects_non_json_params(self):
        with pytest.raises(ValidationError, match="non-finite"):
            SignalRequest(instance_id="x", signal_code="EMA", params={"length": float("nan")})

    def test_catalog_contains_schema_driven_metadata(self):
        catalog = make_catalog()
        dumped = catalog.model_dump(mode="json")
        length_schema = dumped["params_schema"]["properties"]["length"]
        assert catalog.signal_code == "EMA"
        assert length_schema["x-i18n-key"] == "signals.params.length"
        assert length_schema["x-control-order"] == 1
        assert dumped["compatible_domains"] == ["asset", "fx"]
        assert json.loads(catalog.model_dump_json()) == dumped

    def test_catalog_auto_populates_ai_description_when_omitted(self):
        """SignalCatalogDefinition derives ai_description from its own
        existing fields when the caller doesn't supply one — keeping the
        catalog the single source of truth without per-caller boilerplate."""
        catalog = make_catalog()
        assert catalog.ai_description is not None
        assert catalog.ai_description.signal_code == catalog.signal_code
        assert catalog.ai_description.semantic_id == catalog.semantic_id
        assert catalog.ai_description.semantic_description == catalog.semantic_description
        assert catalog.ai_description.category == catalog.category
        assert len(catalog.ai_description.outputs) == len(catalog.output_specs)
        assert catalog.ai_description.outputs[0].semantic_id == catalog.output_specs[0].semantic_id
        assert catalog.ai_events == []

    def test_catalog_preserves_explicit_ai_description(self):
        """An explicitly supplied ai_description is never overwritten by
        the auto-populate validator."""
        explicit = SignalAiDescription(
            signal_code="EMA",
            semantic_id="custom_semantic_id",
            semantic_description="Custom AI-facing description.",
            category=SignalCategory.TREND,
            outputs=(SignalAiOutputDescription(key="custom", semantic_id="custom.value", semantic_description="Custom output.", unit=SignalUnit.PRICE),),
        )
        catalog = SignalCatalogDefinition(
            signal_code="ema",
            implementation_version="1.0.0",
            category=SignalCategory.TREND,
            display_name_key="signals.ema.name",
            description_key="signals.ema.description",
            semantic_id="exponential_moving_average",
            semantic_description="Smooths prices with greater weight on recent observations.",
            icon="activity",
            docs_path="financial-theory/technical-analysis/indicators/ema/",
            params_schema=DemoParams.model_json_schema(),
            default_params=DemoParams().model_dump(mode="json"),
            input_requirements=SignalInputRequirements(price_fields=[SignalPriceField.CLOSE]),
            output_specs=[make_output_spec()],
            compatible_domains=[SignalDomain.ASSET, SignalDomain.FX],
            ai_description=explicit,
        )
        assert catalog.ai_description.semantic_id == "custom_semantic_id"
        assert catalog.ai_description.outputs[0].key == "custom"

    def test_catalog_rejects_duplicate_outputs_and_domains(self):
        catalog = make_catalog().model_dump()
        catalog["output_specs"] = [make_output_spec(), make_output_spec()]
        with pytest.raises(ValidationError, match="output spec keys"):
            SignalCatalogDefinition.model_validate(catalog)

        catalog = make_catalog().model_dump()
        catalog["compatible_domains"] = [SignalDomain.ASSET, SignalDomain.ASSET]
        with pytest.raises(ValidationError, match="compatible_domains"):
            SignalCatalogDefinition.model_validate(catalog)

    def test_catalog_rejects_duplicate_output_semantic_ids(self):
        catalog = make_catalog().model_dump(mode="python")
        duplicate = make_output_spec().model_dump(mode="python")
        duplicate["key"] = "ema_secondary"
        catalog["output_specs"] = [
            make_output_spec().model_dump(mode="python"),
            duplicate,
        ]
        with pytest.raises(ValidationError, match="output semantic_ids"):
            SignalCatalogDefinition.model_validate(catalog)

        catalog = make_catalog().model_dump(mode="python")
        catalog["output_specs"][0]["semantic_id"] = catalog["semantic_id"]
        with pytest.raises(ValidationError, match="signal and output semantic_ids"):
            SignalCatalogDefinition.model_validate(catalog)

    def test_catalog_response_rejects_duplicate_signal_or_output_semantic_ids(self):
        first = make_catalog().model_dump(mode="python")
        second = make_catalog().model_dump(mode="python")
        second["signal_code"] = "SMA"
        second["output_specs"][0]["key"] = "sma"
        with pytest.raises(ValidationError, match="signal semantic_ids"):
            SignalCatalogResponse.model_validate({"items": [first, second]})

        second["semantic_id"] = "simple_moving_average"
        with pytest.raises(ValidationError, match="catalog output semantic_ids"):
            SignalCatalogResponse.model_validate({"items": [first, second]})

        second["output_specs"][0]["semantic_id"] = second["semantic_id"]
        with pytest.raises(ValidationError, match="signal and output semantic_ids"):
            SignalCatalogResponse.model_validate({"items": [first, second]})

    def test_catalog_and_result_schemas_do_not_reference_third_party_types(self):
        schema_text = json.dumps(
            {
                "catalog": SignalCatalogDefinition.model_json_schema(),
                "result": SignalResult.model_json_schema(mode="serialization"),
            }
        ).lower()
        assert "pandas" not in schema_text
        assert "talib" not in schema_text


class TestAnnotationRequestSchemas:
    def test_discriminated_annotation_union_parses_cross_and_threshold(self):
        adapter = TypeAdapter(SignalAnnotationRequest)
        crossover = adapter.validate_python(
            {
                "kind": "line_crossover",
                "key": "ema-cross",
                "attach_to_instance_id": "ema-fast",
                "left": {
                    "kind": "price",
                    "field": "close",
                },
                "right": {
                    "kind": "signal",
                    "instance_id": "ema-fast",
                    "series_key": "ema",
                },
            }
        )
        threshold = adapter.validate_python(
            {
                "kind": "threshold_crossing",
                "key": "rsi-threshold",
                "attach_to_instance_id": "rsi",
                "source": {
                    "kind": "signal",
                    "instance_id": "rsi",
                    "series_key": "rsi",
                },
                "threshold": 70,
                "direction": "down",
                "limit": 20,
                "sampling": "uniform",
            }
        )

        assert isinstance(crossover, SignalLineCrossoverRequest)
        assert isinstance(crossover.left, SignalPriceValueSource)
        assert isinstance(crossover.right, SignalOutputValueSource)
        assert isinstance(threshold, SignalThresholdCrossingRequest)
        assert threshold.direction == SignalThresholdDirection.DOWN
        assert threshold.sampling == SignalAnnotationSampling.UNIFORM

    def test_band_value_source_is_discriminated_and_component_typed(self):
        adapter = TypeAdapter(SignalValueSource)
        source = adapter.validate_python(
            {
                "kind": "band",
                "instance_id": "bollinger",
                "series_key": "bands",
                "component": "upper",
            }
        )

        assert isinstance(source, SignalBandValueSource)
        assert source.component == SignalBandComponent.UPPER
        schema = adapter.json_schema()
        assert set(schema["discriminator"]["mapping"]) == {
            "band",
            "price",
            "signal",
        }
        assert schema["$defs"]["SignalBandValueSource"]["properties"]["kind"]["enum"] == ["band"]
        assert schema["$defs"]["SignalBandComponent"]["enum"] == [
            "lower",
            "middle",
            "upper",
        ]

        with pytest.raises(ValidationError, match="component"):
            adapter.validate_python(
                {
                    "kind": "band",
                    "instance_id": "bollinger",
                    "series_key": "bands",
                    "component": "median",
                }
            )

    def test_annotation_union_schema_has_discriminator(self):
        schema = TypeAdapter(SignalAnnotationRequest).json_schema()
        assert schema["discriminator"]["propertyName"] == "kind"
        assert set(schema["discriminator"]["mapping"]) == {
            "line_crossover",
            "threshold_crossing",
        }

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("epsilon", -0.1),
            ("min_gap_days", -1),
            ("limit", 0),
        ],
    )
    def test_annotation_request_rejects_invalid_limits(self, field, value):
        payload = {
            "kind": "threshold_crossing",
            "key": "threshold",
            "attach_to_instance_id": "rsi",
            "source": {
                "kind": "signal",
                "instance_id": "rsi",
                "series_key": "rsi",
            },
            "threshold": 70,
            field: value,
        }
        with pytest.raises(ValidationError):
            TypeAdapter(SignalAnnotationRequest).validate_python(payload)

    @pytest.mark.parametrize("request_model", [FAPriceQueryItem, FXConversionRequest])
    def test_domain_requests_reject_unknown_band_source_instance(self, request_model):
        common = {
            "date_range": {"start": DAY_1, "end": DAY_2},
            "signals": [
                {
                    "instance_id": "ema",
                    "signal_code": "EMA",
                    "params": {"period": 20},
                }
            ],
            "annotation_requests": [
                {
                    "kind": "threshold_crossing",
                    "key": "missing-band",
                    "attach_to_instance_id": "ema",
                    "source": {
                        "kind": "band",
                        "instance_id": "missing",
                        "series_key": "bands",
                        "component": "upper",
                    },
                    "threshold": 0,
                }
            ],
        }
        payload = (
            {"asset_id": 1, **common}
            if request_model is FAPriceQueryItem
            else {
                "from_amount": Currency(code="EUR", amount=1),
                "to": "USD",
                **common,
            }
        )

        with pytest.raises(ValidationError, match="annotation source 'missing'"):
            request_model.model_validate(payload)

    def test_annotation_request_rejects_frontend_style(self):
        with pytest.raises(ValidationError, match="extra_forbidden"):
            SignalThresholdCrossingRequest(
                key="threshold",
                attach_to_instance_id="rsi",
                source=SignalOutputValueSource(
                    instance_id="rsi",
                    series_key="rsi",
                ),
                threshold=70,
                color="red",
            )


class TestResultStatusMatrix:
    def test_ok_requires_series_complete_warmup_and_computable_input(self):
        result = make_result(SignalStatus.OK, series=[make_line_series()])
        assert result.status == SignalStatus.OK
        with pytest.raises(ValidationError, match="complete warm-up"):
            make_result(
                SignalStatus.OK,
                series=[make_line_series()],
                availability=make_availability(warmup_complete=False, reason=SignalAvailabilityReason.INCOMPLETE_WARMUP),
                warmup=make_warmup(complete=False),
            )

    def test_ok_rejects_missing_output_values(self):
        with pytest.raises(ValidationError, match="missing output"):
            make_result(
                SignalStatus.OK,
                series=[make_line_series(values=(None, 101.0))],
            )

    def test_partial_requires_output_and_warning(self):
        warning = SignalWarning(
            code=SignalWarningCode.INCOMPLETE_WARMUP,
            message="Warm-up incomplete",
            details={"loaded_points": 2},
        )
        result = make_result(
            SignalStatus.PARTIAL,
            series=[make_line_series()],
            availability=make_availability(warmup_complete=False, reason=SignalAvailabilityReason.INCOMPLETE_WARMUP),
            warmup=make_warmup(complete=False),
            warnings=[warning],
        )
        assert result.warnings[0].code == SignalWarningCode.INCOMPLETE_WARMUP
        with pytest.raises(ValidationError, match="at least one warning"):
            make_result(
                SignalStatus.PARTIAL,
                series=[make_line_series()],
                availability=make_availability(warmup_complete=False, reason=SignalAvailabilityReason.INCOMPLETE_WARMUP),
                warmup=make_warmup(complete=False),
            )

    def test_partial_requires_real_partial_state(self):
        warning = SignalWarning(
            code=SignalWarningCode.OUTPUT_TRUNCATED,
            message="Informational warning",
        )
        with pytest.raises(ValidationError, match="incomplete warm-up or partial coverage"):
            make_result(
                SignalStatus.PARTIAL,
                series=[make_line_series()],
                warnings=[warning],
            )

    def test_partial_coverage_is_explicit(self):
        warning = SignalWarning(
            code=SignalWarningCode.PARTIAL_INPUT_COVERAGE,
            message="Partial contiguous input used",
        )
        result = make_result(
            SignalStatus.PARTIAL,
            series=[make_line_series(values=(None, 101.0))],
            availability=make_availability(
                reason=SignalAvailabilityReason.PARTIAL_INPUT_COVERAGE,
                partial_coverage_used=True,
            ),
            warnings=[warning],
        )
        assert result.availability.partial_coverage_used is True

    def test_partial_undefined_metric_window_is_explicit(self):
        warning = SignalWarning(
            code=SignalWarningCode.UNDEFINED_METRIC_WINDOW,
            message="One rolling window is undefined",
        )
        result = make_result(
            SignalStatus.PARTIAL,
            series=[make_line_series(values=(None, 101.0))],
            availability=make_availability(
                reason=SignalAvailabilityReason.PARTIAL_UNDEFINED_METRIC,
            ),
            warnings=[warning],
        )
        assert result.availability.reason_code == SignalAvailabilityReason.PARTIAL_UNDEFINED_METRIC

    def test_unavailable_uses_availability_reason_without_error(self):
        result = make_result(
            SignalStatus.UNAVAILABLE,
            availability=make_availability(
                can_compute=False,
                warmup_complete=False,
                reason=SignalAvailabilityReason.MISSING_INPUT_FIELDS,
            ),
            warmup=make_warmup(complete=False),
        )
        assert result.series == []
        assert result.error is None
        with pytest.raises(ValidationError, match="uses availability reason"):
            make_result(
                SignalStatus.UNAVAILABLE,
                availability=make_availability(
                    can_compute=False,
                    warmup_complete=False,
                    reason=SignalAvailabilityReason.MISSING_INPUT_FIELDS,
                ),
                warmup=make_warmup(complete=False),
                error=SignalError(code=SignalErrorCode.COMPUTE_ERROR, message="Unexpected"),
            )

    def test_failed_requires_structured_error_and_no_series(self):
        error = SignalError(
            code=SignalErrorCode.COMPUTE_ERROR,
            message="TA-Lib failed",
            details={"exception_type": "RuntimeError"},
        )
        result = make_result(SignalStatus.FAILED, error=error)
        assert result.error.code == SignalErrorCode.COMPUTE_ERROR
        with pytest.raises(ValidationError, match="requires structured error"):
            make_result(SignalStatus.FAILED)
        with pytest.raises(ValidationError, match="cannot contain series"):
            make_result(SignalStatus.FAILED, series=[make_line_series()], error=error)

    def test_precompute_failure_needs_no_fabricated_runtime_metadata(self):
        result = make_result(
            SignalStatus.FAILED,
            availability=None,
            warmup=None,
            error=SignalError(
                code=SignalErrorCode.UNKNOWN_SIGNAL,
                message="Unknown signal",
            ),
        )
        assert result.availability is None
        assert result.warmup is None
        with pytest.raises(ValidationError, match="pre-compute failure"):
            make_result(
                SignalStatus.FAILED,
                error=SignalError(
                    code=SignalErrorCode.INVALID_PARAMS,
                    message="Invalid params",
                ),
            )

    def test_compute_failure_requires_runtime_metadata(self):
        with pytest.raises(ValidationError, match="requires availability"):
            make_result(
                SignalStatus.FAILED,
                availability=None,
                warmup=None,
                error=SignalError(
                    code=SignalErrorCode.COMPUTE_ERROR,
                    message="Library failed",
                ),
            )

    def test_result_rejects_inconsistent_warmup_metadata(self):
        availability = make_availability()
        availability.required_points = 4
        with pytest.raises(ValidationError, match="required_points"):
            make_result(
                SignalStatus.OK,
                series=[make_line_series()],
                availability=availability,
            )

    def test_risk_metadata_and_data_quality_are_paired(self):
        metadata = RiskResultMetadata(
            analyzed_range=DateRangeModel(start=DAY_1, end=DAY_2),
            n_observations=0,
            calendar_days=0,
            annualization_factor=None,
            coverage=0,
            currency="EUR",
            return_basis=RiskReturnBasis.PRICE_ONLY,
            algorithm_version="1.0.0",
            computed_at=datetime.now(UTC),
        )
        quality = DataQualityReport()
        result = make_result(
            SignalStatus.OK,
            series=[make_line_series()],
            risk_metadata=metadata,
            data_quality=quality,
        )
        assert result.risk_metadata == metadata
        assert result.data_quality == quality

        with pytest.raises(
            ValidationError,
            match="must be provided together",
        ):
            make_result(
                SignalStatus.OK,
                series=[make_line_series()],
                risk_metadata=metadata,
            )

    def test_error_details_must_be_json_safe(self):
        with pytest.raises(ValidationError, match="non-JSON"):
            SignalError(
                code=SignalErrorCode.CONTRACT_VIOLATION,
                message="Bad output",
                details={"value": object()},
            )


# Pinned from 4a73f5f63447e01b51993afb2e3c73e2c22a9a28, BEFORE the ordered-rule
# refactor. Do not replace this oracle with production predicates/tables. The
# SAME validator name overrides (rather than adds to) the inherited validator.
# Its two helpers are pinned locally too; nested field validators stay public.
def _ensure_unique(values: list[Any], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must not contain duplicates")


def _validate_series_alignment(series: list[SignalSeries]) -> None:
    _ensure_unique([item.key for item in series], "series keys")
    _ensure_unique([item.semantic_id for item in series], "series semantic_ids")
    reference_dates = [point.date for point in series[0].points]
    for item in series[1:]:
        if [point.date for point in item.points] != reference_dates:
            raise ValueError("all signal series must have identical dates and cardinality")


def _series_have_missing_values(series: list[SignalSeries]) -> bool:
    for item in series:
        if isinstance(item, SignalBandSeries):
            if any(point.lower is None or point.middle is None or point.upper is None for point in item.points):
                return True
        elif any(point.value is None for point in item.points):
            return True
    return False


class _BaselineSignalResult(SignalResult):
    @model_validator(mode="after")
    def validate_status_matrix(self) -> SignalResult:  # noqa: C901 — pinned imperative baseline oracle
        if self.series:
            _validate_series_alignment(self.series)

        if self.status == SignalStatus.OK:
            if self.availability is None or self.warmup is None:
                raise ValueError("ok result requires availability and warm-up metadata")
            if not self.series:
                raise ValueError("ok result requires series")
            if not self.availability.can_compute or not self.warmup.complete:
                raise ValueError("ok result requires computable input and complete warm-up")
            if self.availability.reason_code is not None or self.availability.partial_coverage_used:
                raise ValueError("ok result cannot use partial availability")
            if _series_have_missing_values(self.series):
                raise ValueError("ok result cannot contain missing output values")
            if self.error is not None:
                raise ValueError("ok result cannot contain error")
        elif self.status == SignalStatus.PARTIAL:
            if self.availability is None or self.warmup is None:
                raise ValueError("partial result requires availability and warm-up metadata")
            if not self.series:
                raise ValueError("partial result requires series")
            if not self.availability.can_compute:
                raise ValueError("partial result requires computable input")
            if not self.warnings:
                raise ValueError("partial result requires at least one warning")
            if self.warmup.complete and not self.availability.partial_coverage_used and self.availability.reason_code != SignalAvailabilityReason.PARTIAL_UNDEFINED_METRIC:
                raise ValueError("partial result requires incomplete warm-up or partial coverage")
            if self.error is not None:
                raise ValueError("partial result cannot contain error")
        elif self.status == SignalStatus.UNAVAILABLE:
            if self.availability is None or self.warmup is None:
                raise ValueError("unavailable result requires availability and warm-up metadata")
            if self.series or self.annotations:
                raise ValueError("unavailable result cannot contain series or annotations")
            if self.availability.can_compute:
                raise ValueError("unavailable result requires can_compute=false")
            if self.error is not None:
                raise ValueError("unavailable result uses availability reason, not error")
        elif self.status == SignalStatus.FAILED:
            if self.series or self.annotations:
                raise ValueError("failed result cannot contain series or annotations")
            if self.error is None:
                raise ValueError("failed result requires structured error")
            precompute_errors = {
                SignalErrorCode.UNKNOWN_SIGNAL,
                SignalErrorCode.INVALID_PARAMS,
                SignalErrorCode.PLANNING_ERROR,
            }
            if self.error.code in precompute_errors:
                if self.availability is not None or self.warmup is not None:
                    raise ValueError("pre-compute failure cannot contain availability or warm-up metadata")
            else:
                if self.availability is None or self.warmup is None:
                    raise ValueError("compute failure requires availability and warm-up metadata")
                if not self.availability.can_compute:
                    raise ValueError("compute failure requires computable input")

        if self.availability is not None and self.warmup is not None:
            if self.availability.required_points != self.warmup.requirement.total_points:
                raise ValueError("availability required_points must match warm-up total_points")
            if self.availability.warmup_complete != self.warmup.complete:
                raise ValueError("availability warmup_complete must match warm-up metadata")
        if (self.risk_metadata is None) != (self.data_quality is None):
            raise ValueError("risk_metadata and data_quality must be provided together")
        return self


_RawPayload = dict[str, Any]
_ValidationIssue = tuple[tuple[str | int, ...], str, str]
_PRECOMPUTE_CODES = (
    SignalErrorCode.UNKNOWN_SIGNAL,
    SignalErrorCode.INVALID_PARAMS,
    SignalErrorCode.PLANNING_ERROR,
)
_RUNTIME_CODES = (
    SignalErrorCode.COMPUTE_ERROR,
    SignalErrorCode.INVALID_OUTPUT,
    SignalErrorCode.CONTRACT_VIOLATION,
)
_ERROR_CHOICES = (None, *_PRECOMPUTE_CODES, *_RUNTIME_CODES)
_FIXED_TIMESTAMP = "2026-01-03T12:00:00Z"


def _raw_series(kind: str = "line", *, missing: bool = False) -> _RawPayload:
    """Raw public input, not a model dump or make_result's truthiness defaults."""
    points = (
        [
            {"date": "2026-01-01", "lower": None if missing else 0.0, "middle": 0.0, "upper": 0.0},
            {"date": "2026-01-02", "lower": 0.0, "middle": 1.0, "upper": 2.0},
        ]
        if kind == "band"
        else [
            {"date": "2026-01-01", "value": None if missing else 0.0},
            {"date": "2026-01-02", "value": 1.0},
        ]
    )
    return {
        "kind": kind,
        "key": "output",
        "label_key": "signals.test.output",
        "semantic_id": "test.output",
        "semantic_description": "A neutral output value.",
        "unit": "price",
        "axis": {"key": "price", "role": "price"},
        "points": points,
    }


def _raw_availability(
    can_compute: bool = True,
    warmup_complete: bool = True,
    partial_coverage_used: bool = False,
    reason: SignalAvailabilityReason | None = None,
) -> _RawPayload:
    return {
        "domain_compatible": True,
        "can_compute": can_compute,
        "missing_price_fields": [] if can_compute else ["close"],
        "input_coverage": {
            "requested_points": 2,
            "available_points": 2 if can_compute else 0,
            "contiguous_points": 2 if can_compute else 0,
            "observed_points": 2 if can_compute else 0,
            "backfilled_points": 0,
            "missing_points": 0 if can_compute else 2,
            "internal_gap_count": 0,
            "coverage_ratio": 1.0 if can_compute else 0.0,
            "first_available_date": "2026-01-01" if can_compute else None,
            "last_available_date": "2026-01-02" if can_compute else None,
        },
        "required_points": 3,
        "warmup_complete": warmup_complete,
        "partial_coverage_used": partial_coverage_used,
        "reason_code": reason,
    }


def _raw_warmup(complete: bool = True) -> _RawPayload:
    # complete=False need NOT imply used_points < total_points in the baseline.
    return {
        "requirement": {"minimum_points": 2, "stabilization_points": 1, "total_points": 3},
        "loaded_points": 3,
        "used_points": 3,
        "complete": complete,
    }


def _raw_warning(code: SignalWarningCode = SignalWarningCode.OUTPUT_TRUNCATED) -> _RawPayload:
    return {"code": code, "message": "Informational warning", "details": {"arbitrary": [None, 0, False]}}


def _raw_error(code: SignalErrorCode = SignalErrorCode.COMPUTE_ERROR) -> _RawPayload:
    return {"code": code, "message": "Characterization failure", "details": {"phase": "orchestration"}}


def _raw_annotation() -> _RawPayload:
    # Neither its key nor its date must coincide with an output series.
    return {"key": "unrelated", "annotation_type": "event", "date": "2026-01-03", "values": {"level": 0.0}}


def _raw_risk_metadata(*, populated: bool = False) -> _RawPayload:
    return {
        "analyzed_range": {"start": "2026-01-01", "end": "2026-01-02"},
        "n_observations": 5 if populated else 0,
        "calendar_days": 10 if populated else 0,
        "annualization_factor": 182.5 if populated else None,
        "coverage": 0.75 if populated else 0.0,
        "currency": "eur",
        "return_basis": "price_only",
        "algorithm_version": "1.0.0",
        "computed_at": _FIXED_TIMESTAMP,
    }


def _raw_result(
    status: SignalStatus = SignalStatus.OK,
    error_code: SignalErrorCode | None = None,
) -> _RawPayload:
    complete = status != SignalStatus.PARTIAL
    computable = status != SignalStatus.UNAVAILABLE
    reason = SignalAvailabilityReason.MISSING_INPUT_FIELDS if not computable else SignalAvailabilityReason.INCOMPLETE_WARMUP if not complete else None
    precompute = status == SignalStatus.FAILED and error_code in _PRECOMPUTE_CODES
    return {
        "instance_id": "characterization",
        "signal_code": "  ema  ",
        "implementation_version": None,
        "normalized_params": {"length": 2, "nested": [None, False, 0]},
        "status": status,
        "series": [_raw_series()] if status in (SignalStatus.OK, SignalStatus.PARTIAL) else [],
        "availability": None if precompute else _raw_availability(computable, complete, reason=reason),
        "warmup": None if precompute else _raw_warmup(complete),
        "annotations": [],
        "warnings": [_raw_warning()] if status == SignalStatus.PARTIAL else [],
        "error": _raw_error(error_code) if error_code is not None else None,
        "risk_metadata": None,
        "data_quality": None,
    }


def _validation_outcome(model: type[BaseModel], payload: _RawPayload, *, json_input: bool = False) -> tuple[BaseModel | None, list[_ValidationIssue]]:
    # No instance reuse: Pydantic is free to normalize/mutate its own input.
    raw = deepcopy(payload)
    try:
        result = model.model_validate_json(json.dumps(raw)) if json_input else model.model_validate(raw)
    except ValidationError as exc:
        return None, [(tuple(error["loc"]), error["type"], error["msg"]) for error in exc.errors()]
    return result, []


def _assert_equivalent(payload: _RawPayload) -> tuple[BaseModel | None, list[_ValidationIssue]]:
    python_outcome: tuple[BaseModel | None, list[_ValidationIssue]] = (None, [])
    for json_input in (False, True):
        reference, expected_errors = _validation_outcome(_BaselineSignalResult, payload, json_input=json_input)
        actual, errors = _validation_outcome(SignalResult, payload, json_input=json_input)
        context = f"json_input={json_input}, payload={payload!r}"
        assert errors == expected_errors, context
        assert (actual is None) == (reference is None), context
        if reference is not None:
            assert actual is not None
            assert actual.model_dump(mode="python") == reference.model_dump(mode="python"), context
            assert actual.model_dump(mode="json") == reference.model_dump(mode="json"), context
            assert actual.model_dump_json() == reference.model_dump_json(), context
        if not json_input:
            python_outcome = actual, errors
    return python_outcome


def _assert_root_error(payload: _RawPayload, message: str) -> None:
    result, errors = _assert_equivalent(payload)
    assert result is None
    assert errors == [((), "value_error", f"Value error, {message}")], payload


class TestResultDifferentialGrids:
    @pytest.mark.parametrize("status", tuple(SignalStatus))
    @pytest.mark.parametrize("error_code", _ERROR_CHOICES)
    def test_presence_grid(self, status: SignalStatus, error_code: SignalErrorCode | None) -> None:
        """28 groups x 128 raw cells = 3584; baseline accepts 8+4+4+12+12."""
        accepted = 0
        visited = 0
        for has_availability, has_warmup, has_series, has_annotations, has_warnings, has_risk, has_quality in product((False, True), repeat=7):
            payload = _raw_result(status, error_code)
            # Presence axes must use individually valid, status-appropriate
            # nested objects even when this particular error forbids them.
            canonical = _raw_result(status)
            payload.update(
                availability=canonical["availability"] if has_availability else None,
                warmup=canonical["warmup"] if has_warmup else None,
                series=[_raw_series()] if has_series else [],
                annotations=[_raw_annotation()] if has_annotations else [],
                warnings=[_raw_warning()] if has_warnings else [],
                risk_metadata=_raw_risk_metadata() if has_risk else None,
                data_quality={} if has_quality else None,
            )
            result, errors = _assert_equivalent(payload)
            # Every rejected cell reaches the result validator, not a broken
            # nested fixture (e.g. risk_metadata={} would invalidate the grid).
            assert all(loc == () for loc, _, _ in errors), payload
            accepted += result is not None
            visited += 1
        assert visited == 128
        expected = 0
        if status == SignalStatus.FAILED and error_code is not None:
            expected = 4
        elif error_code is None:
            expected = {SignalStatus.OK: 8, SignalStatus.PARTIAL: 4, SignalStatus.UNAVAILABLE: 4}.get(status, 0)
        assert accepted == expected

    @pytest.mark.parametrize(
        ("computable", "complete", "partial", "nested_count", "ok_count", "partial_count", "unavailable_count", "runtime_count"),
        [
            (False, False, False, 10, 0, 0, 10, 0),
            (False, False, True, 0, 0, 0, 0, 0),
            (False, True, False, 10, 0, 0, 10, 0),
            (False, True, True, 0, 0, 0, 0, 0),
            (True, False, False, 2, 0, 2, 0, 2),
            (True, False, True, 3, 0, 3, 0, 3),
            (True, True, False, 3, 1, 1, 0, 3),
            (True, True, True, 3, 0, 3, 0, 3),
        ],
    )
    def test_availability_grid(
        self,
        computable: bool,
        complete: bool,
        partial: bool,
        nested_count: int,
        ok_count: int,
        partial_count: int,
        unavailable_count: int,
        runtime_count: int,
    ) -> None:
        """128 nested cells: 31 valid, 97 invalid; runtime accepts 11/code."""
        accepted: Counter[str] = Counter()
        modes = (
            (SignalStatus.OK, None),
            (SignalStatus.PARTIAL, None),
            (SignalStatus.UNAVAILABLE, None),
            *((SignalStatus.FAILED, code) for code in _RUNTIME_CODES),
        )
        reasons = (None, *SignalAvailabilityReason)
        assert len(reasons) == 16
        for reason in reasons:
            availability = _raw_availability(computable, complete, partial, reason)
            nested, _ = _validation_outcome(SignalAvailability, availability)
            accepted["nested"] += nested is not None
            for status, error_code in modes:
                payload = _raw_result(status, error_code)
                payload.update(availability=availability, warmup=_raw_warmup(complete))
                result, errors = _assert_equivalent(payload)
                if nested is None:
                    assert errors and all(loc == ("availability",) for loc, _, _ in errors), payload
                accepted[error_code.value if error_code else status.value] += result is not None
        assert accepted == {
            "nested": nested_count,
            "ok": ok_count,
            "partial": partial_count,
            "unavailable": unavailable_count,
            **{code.value: runtime_count for code in _RUNTIME_CODES},
        }

    def test_missing_source_capability_remains_unclassified(self) -> None:
        availability = _raw_availability(reason=SignalAvailabilityReason.MISSING_SOURCE_CAPABILITY)
        assert SignalAvailability.model_validate(deepcopy(availability)).can_compute
        for code in _RUNTIME_CODES:
            payload = _raw_result(SignalStatus.FAILED, code)
            payload["availability"] = availability
            assert _assert_equivalent(payload)[0] is not None
        payload = _raw_result()
        payload["availability"] = availability
        _assert_root_error(payload, "ok result cannot use partial availability")
        payload.update(status=SignalStatus.PARTIAL, warnings=[_raw_warning()])
        _assert_root_error(payload, "partial result requires incomplete warm-up or partial coverage")


_STATUS_CASES = (
    (SignalStatus.OK, None),
    (SignalStatus.PARTIAL, None),
    (SignalStatus.UNAVAILABLE, None),
    *((SignalStatus.FAILED, code) for code in (*_PRECOMPUTE_CODES, *_RUNTIME_CODES)),
)


def _merge_raw(payload: _RawPayload, changes: _RawPayload) -> None:
    """Apply co-faults without replacing an unrelated nested mutation."""
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(payload.get(key), dict):
            _merge_raw(payload[key], value)
        else:
            payload[key] = deepcopy(value)


def _guard_chain(status: SignalStatus, code: SignalErrorCode | None) -> list[tuple[str, _RawPayload]]:
    """Reachable witnesses in baseline order, not production rule introspection."""
    required_points = (
        "availability required_points must match warm-up total_points",
        {"availability": {"required_points": 4}},
    )
    risk_pair = ("risk_metadata and data_quality must be provided together", {"data_quality": {}})
    if status == SignalStatus.OK:
        # An OK warmup-flag mismatch cannot reach the final equality guard:
        # incomplete availability requires a reason, which OK rejects earlier.
        return [
            ("ok result requires availability and warm-up metadata", {"availability": None}),
            ("ok result requires series", {"series": []}),
            ("ok result requires computable input and complete warm-up", {"warmup": {"complete": False}}),
            (
                "ok result cannot use partial availability",
                {"availability": {"reason_code": SignalAvailabilityReason.PARTIAL_UNDEFINED_METRIC}},
            ),
            ("ok result cannot contain missing output values", {"series": [_raw_series(missing=True)]}),
            ("ok result cannot contain error", {"error": _raw_error()}),
            required_points,
            risk_pair,
        ]
    if status == SignalStatus.PARTIAL:
        return [
            ("partial result requires availability and warm-up metadata", {"availability": None}),
            ("partial result requires series", {"series": []}),
            (
                "partial result requires computable input",
                {"availability": _raw_availability(False, False, reason=SignalAvailabilityReason.MISSING_INPUT_FIELDS)},
            ),
            ("partial result requires at least one warning", {"warnings": []}),
            (
                "partial result requires incomplete warm-up or partial coverage",
                {"availability": _raw_availability(), "warmup": _raw_warmup()},
            ),
            ("partial result cannot contain error", {"error": _raw_error()}),
            required_points,
            (
                "availability warmup_complete must match warm-up metadata",
                {"availability": {"warmup_complete": True, "reason_code": SignalAvailabilityReason.PARTIAL_UNDEFINED_METRIC}},
            ),
            risk_pair,
        ]
    if status == SignalStatus.UNAVAILABLE:
        return [
            ("unavailable result requires availability and warm-up metadata", {"availability": None}),
            ("unavailable result cannot contain series or annotations", {"annotations": [_raw_annotation()]}),
            ("unavailable result requires can_compute=false", {"availability": _raw_availability()}),
            ("unavailable result uses availability reason, not error", {"error": _raw_error()}),
            required_points,
            ("availability warmup_complete must match warm-up metadata", {"availability": {"warmup_complete": False}}),
            risk_pair,
        ]
    common = [
        ("failed result cannot contain series or annotations", {"annotations": [_raw_annotation()]}),
        ("failed result requires structured error", {"error": None}),
    ]
    if code in _PRECOMPUTE_CODES:
        return [
            *common,
            ("pre-compute failure cannot contain availability or warm-up metadata", {"warmup": _raw_warmup()}),
            risk_pair,
        ]
    return [
        *common,
        ("compute failure requires availability and warm-up metadata", {"warmup": None}),
        (
            "compute failure requires computable input",
            {"availability": _raw_availability(False, reason=SignalAvailabilityReason.MISSING_INPUT_FIELDS)},
        ),
        required_points,
        (
            "availability warmup_complete must match warm-up metadata",
            {"availability": {"warmup_complete": False, "reason_code": SignalAvailabilityReason.PARTIAL_UNDEFINED_METRIC}},
        ),
        risk_pair,
    ]


class TestResultValidationPrecedence:
    @pytest.mark.parametrize(("status", "error_code"), _STATUS_CASES)
    def test_adjacent_cofaults_keep_interleaved_guard_order(self, status: SignalStatus, error_code: SignalErrorCode | None) -> None:
        guards = _guard_chain(status, error_code)
        # Prove each fault alone actually reaches its claimed guard. A second
        # "fault" which is nested-invalid or silently legal is not precedence.
        for message, changes in guards:
            payload = _raw_result(status, error_code)
            _merge_raw(payload, changes)
            _assert_root_error(payload, message)
        for (first_message, first_changes), (_, second_changes) in zip(guards, guards[1:], strict=False):
            payload = _raw_result(status, error_code)
            _merge_raw(payload, first_changes)
            _merge_raw(payload, second_changes)
            _assert_root_error(payload, first_message)

    @pytest.mark.parametrize(("status", "error_code"), _STATUS_CASES)
    @pytest.mark.parametrize("misalignment", ("dates", "cardinality"))
    def test_alignment_precedes_status_even_when_output_is_forbidden(self, status: SignalStatus, error_code: SignalErrorCode | None, misalignment: str) -> None:
        payload = _raw_result(status, error_code)
        first = _raw_series()
        second = _raw_series("area")
        if misalignment == "dates":
            second["points"][1]["date"] = "2026-01-03"
        else:
            second["points"].pop()
        payload["series"] = [first, second]
        _assert_root_error(payload, "series keys must not contain duplicates")
        second["key"] = "second"
        _assert_root_error(payload, "series semantic_ids must not contain duplicates")
        second["semantic_id"] = "test.second"
        _assert_root_error(payload, "all signal series must have identical dates and cardinality")
        second["points"] = deepcopy(first["points"])
        if status in (SignalStatus.FAILED, SignalStatus.UNAVAILABLE):
            _assert_root_error(payload, f"{status.value} result cannot contain series or annotations")
        else:
            assert _assert_equivalent(payload)[0] is not None

    @pytest.mark.parametrize("required_points", (2, 4))
    @pytest.mark.parametrize("warmup_complete", (False, True))
    def test_metadata_equalities_both_directions_precede_risk_pairing(self, required_points: int, warmup_complete: bool) -> None:
        payload = _raw_result(SignalStatus.FAILED, SignalErrorCode.COMPUTE_ERROR)
        payload["availability"] = _raw_availability(
            warmup_complete=not warmup_complete,
            reason=SignalAvailabilityReason.PARTIAL_UNDEFINED_METRIC,
        )
        payload["warmup"] = _raw_warmup(warmup_complete)
        payload["availability"]["required_points"] = required_points
        payload["data_quality"] = {}
        _assert_root_error(payload, "availability required_points must match warm-up total_points")
        payload["availability"]["required_points"] = 3
        _assert_root_error(payload, "availability warmup_complete must match warm-up metadata")
        payload["availability"]["warmup_complete"] = warmup_complete
        _assert_root_error(payload, "risk_metadata and data_quality must be provided together")
        payload["risk_metadata"] = _raw_risk_metadata()
        assert _assert_equivalent(payload)[0] is not None


class TestResultRawBoundaries:
    @pytest.mark.parametrize(("status", "error_code"), _STATUS_CASES)
    @pytest.mark.parametrize("field", ("series", "annotations", "warnings"))
    @pytest.mark.parametrize("presence", ("omitted", "none", "empty", "nonempty"))
    def test_collection_omission_none_and_emptiness(self, status: SignalStatus, error_code: SignalErrorCode | None, field: str, presence: str) -> None:
        payload = _raw_result(status, error_code)
        if presence == "omitted":
            del payload[field]
        else:
            example = {"series": _raw_series(), "annotations": _raw_annotation(), "warnings": _raw_warning()}[field]
            payload[field] = None if presence == "none" else [example] if presence == "nonempty" else []
        result, errors = _assert_equivalent(payload)
        if presence == "none":
            assert result is None
            assert errors == [((field,), "list_type", "Input should be a valid list")]
            return
        has_values = presence == "nonempty"
        expected = True
        if field == "series":
            expected = has_values == (status in (SignalStatus.OK, SignalStatus.PARTIAL))
        elif field == "annotations":
            expected = not has_values or status in (SignalStatus.OK, SignalStatus.PARTIAL)
        elif status == SignalStatus.PARTIAL:
            expected = has_values
        assert (result is not None) == expected, payload
        if result is not None:
            assert bool(result.model_dump()[field]) == has_values

    @pytest.mark.parametrize(("status", "error_code"), _STATUS_CASES)
    @pytest.mark.parametrize("field", ("availability", "warmup"))
    @pytest.mark.parametrize("presence", ("omitted", "none", "empty_object"))
    def test_metadata_individual_absences_and_empty_objects(self, status: SignalStatus, error_code: SignalErrorCode | None, field: str, presence: str) -> None:
        payload = _raw_result(status, error_code)
        if presence == "omitted":
            del payload[field]
        else:
            payload[field] = {} if presence == "empty_object" else None
        result, errors = _assert_equivalent(payload)
        if presence == "empty_object":
            assert result is None
            assert errors and all(loc[0] == field and kind == "missing" for loc, kind, _ in errors)
        else:
            assert (result is not None) == (error_code in _PRECOMPUTE_CODES), payload

    @pytest.mark.parametrize("status", tuple(SignalStatus))
    @pytest.mark.parametrize("kind", ("line", "area", "bar", "band"))
    @pytest.mark.parametrize("points", ("zero", "some_none", "all_none", "empty"))
    def test_series_kinds_none_zero_and_nested_failures(self, status: SignalStatus, kind: str, points: str) -> None:
        payload = _raw_result(status, SignalErrorCode.COMPUTE_ERROR if status == SignalStatus.FAILED else None)
        series = _raw_series(kind, missing=points == "some_none")
        value_fields = ("lower", "middle", "upper") if kind == "band" else ("value",)
        if points in ("zero", "all_none"):
            for point in series["points"]:
                point.update(dict.fromkeys(value_fields, None if points == "all_none" else 0.0))
        elif points == "empty":
            series["points"] = []
        payload["series"] = [series]
        result, errors = _assert_equivalent(payload)
        if points == "all_none":
            prefix = "band series" if kind == "band" else "series"
            assert errors == [(("series", 0, kind), "value_error", f"Value error, {prefix} must contain at least one finite value")]
        elif points == "empty":
            assert errors and all(loc == ("series", 0, kind, "points") and error_type == "too_short" for loc, error_type, _ in errors)
        else:
            expected = status == SignalStatus.PARTIAL or (status == SignalStatus.OK and points == "zero")
            assert (result is not None) == expected
            assert all(loc == () for loc, _, _ in errors)

    @pytest.mark.parametrize("component", ("lower", "middle", "upper"))
    @pytest.mark.parametrize("status", (SignalStatus.OK, SignalStatus.PARTIAL))
    def test_each_missing_band_component(self, component: str, status: SignalStatus) -> None:
        payload = _raw_result(status)
        series = _raw_series("band")
        series["points"][0][component] = None
        payload["series"] = [series]
        if status == SignalStatus.OK:
            _assert_root_error(payload, "ok result cannot contain missing output values")
        else:
            assert _assert_equivalent(payload)[0] is not None

    @pytest.mark.parametrize("warning_code", tuple(SignalWarningCode))
    def test_partial_undefined_metric_allows_complete_warmup_and_any_warning(self, warning_code: SignalWarningCode) -> None:
        payload = _raw_result(SignalStatus.PARTIAL)
        payload.update(
            availability=_raw_availability(reason=SignalAvailabilityReason.PARTIAL_UNDEFINED_METRIC),
            warmup=_raw_warmup(),
            warnings=[_raw_warning(warning_code)],
            annotations=[_raw_annotation()],
        )
        result, _ = _assert_equivalent(payload)
        assert result is not None
        dumped = result.model_dump(mode="json")
        assert dumped["warmup"]["complete"] is True
        assert dumped["availability"]["partial_coverage_used"] is False
        assert dumped["warnings"][0]["code"] == warning_code.value
        assert dumped["annotations"][0]["date"] == "2026-01-03"

    @pytest.mark.parametrize("code", (*_PRECOMPUTE_CODES, *_RUNTIME_CODES))
    @pytest.mark.parametrize("phase", (None, "compute", "preflight", "orchestration", 0, ["arbitrary", False]))
    def test_failed_family_uses_error_code_not_details_phase(self, code: SignalErrorCode, phase: Any) -> None:
        payload = _raw_result(SignalStatus.FAILED, code)
        payload["error"]["details"]["phase"] = phase
        assert _assert_equivalent(payload)[0] is not None
        # Contradict the code family with metadata, keeping the phase unchanged.
        if code in _PRECOMPUTE_CODES:
            payload.update(availability=_raw_availability(), warmup=_raw_warmup())
            _assert_root_error(payload, "pre-compute failure cannot contain availability or warm-up metadata")
        else:
            payload.update(availability=None, warmup=None)
            _assert_root_error(payload, "compute failure requires availability and warm-up metadata")

    @pytest.mark.parametrize(("status", "error_code"), _STATUS_CASES)
    @pytest.mark.parametrize("populated", (False, True))
    def test_paired_risk_context_is_optional_even_for_precompute_failure(self, status: SignalStatus, error_code: SignalErrorCode | None, populated: bool) -> None:
        payload = _raw_result(status, error_code)
        metadata = _raw_risk_metadata(populated=populated)
        quality = {"carried_forward_price_points": 2, "warnings": ["Informational"]} if populated else {}
        payload.update(risk_metadata=metadata, data_quality=quality)
        result, _ = _assert_equivalent(payload)
        assert result is not None
        dumped = result.model_dump(mode="json")
        assert dumped["risk_metadata"]["n_observations"] == (5 if populated else 0)
        assert dumped["risk_metadata"]["computed_at"] == _FIXED_TIMESTAMP
        assert dumped["data_quality"]["data_quality_status"] == ("carried_forward" if populated else "ok")
        for absent_field in ("risk_metadata", "data_quality"):
            unpaired = deepcopy(payload)
            unpaired[absent_field] = None
            _assert_root_error(unpaired, "risk_metadata and data_quality must be provided together")

    def test_empty_risk_metadata_is_nested_invalid_but_empty_quality_is_present(self) -> None:
        payload = _raw_result()
        payload.update(risk_metadata={}, data_quality={})
        result, errors = _assert_equivalent(payload)
        assert result is None
        assert errors and all(loc[0] == "risk_metadata" and kind == "missing" for loc, kind, _ in errors)
        payload["risk_metadata"] = _raw_risk_metadata()
        assert _assert_equivalent(payload)[0] is not None
        payload["risk_metadata"] = None
        _assert_root_error(payload, "risk_metadata and data_quality must be provided together")

    def test_zero_required_points_are_values_not_absent_metadata(self) -> None:
        payload = _raw_result()
        payload["availability"]["required_points"] = 0
        payload["warmup"].update(
            requirement={"minimum_points": 0, "stabilization_points": 0, "total_points": 0},
            loaded_points=0,
            used_points=0,
        )
        assert _assert_equivalent(payload)[0] is not None
        payload["availability"]["required_points"] = None
        result, errors = _assert_equivalent(payload)
        assert result is None
        assert errors == [(("availability", "required_points"), "int_type", "Input should be a valid integer")]


def _without_schema_titles(value: Any) -> Any:
    """Titles are presentation, including the reference subclass's identity."""
    if isinstance(value, dict):
        return {key: _without_schema_titles(item) for key, item in value.items() if key != "title"}
    if isinstance(value, list):
        return [_without_schema_titles(item) for item in value]
    return value


def _pinned_result_properties() -> _RawPayload:
    """Public root field shape at 4a73f5f6, independent of inherited fields.

    Nested contracts are intentionally not reimplemented: the refactor owns
    only SignalResult. Both modes also compare the complete public/reference
    schema below, and explicitly protect the output-only quality property.
    """
    series_refs = {
        "line": "#/$defs/SignalLineSeries",
        "area": "#/$defs/SignalAreaSeries",
        "bar": "#/$defs/SignalBarSeries",
        "band": "#/$defs/SignalBandSeries",
    }
    return {
        "instance_id": {"type": "string", "minLength": 1, "maxLength": 128},
        "signal_code": {"type": "string", "minLength": 1, "maxLength": 64},
        "implementation_version": {
            "anyOf": [{"type": "string", "minLength": 1, "maxLength": 64}, {"type": "null"}],
            "default": None,
        },
        "normalized_params": {"type": "object", "additionalProperties": {"$ref": "#/$defs/JsonValue"}},
        "status": {"$ref": "#/$defs/SignalStatus"},
        "series": {
            "type": "array",
            "items": {
                "discriminator": {"propertyName": "kind", "mapping": series_refs},
                "oneOf": [{"$ref": ref} for ref in series_refs.values()],
            },
        },
        "annotations": {"type": "array", "items": {"$ref": "#/$defs/SignalAnnotation"}},
        "warnings": {"type": "array", "items": {"$ref": "#/$defs/SignalWarning"}},
        **{
            field: {"anyOf": [{"$ref": f"#/$defs/{model}"}, {"type": "null"}], "default": None}
            for field, model in (
                ("availability", "SignalAvailability"),
                ("warmup", "SignalWarmupMetadata"),
                ("error", "SignalError"),
                ("risk_metadata", "RiskResultMetadata"),
                ("data_quality", "DataQualityReport"),
            )
        },
    }


class TestResultPublicShape:
    @pytest.mark.parametrize("mode", ("validation", "serialization"))
    def test_public_schema_validation_and_serialization_shape(self, mode: Literal["validation", "serialization"]) -> None:
        schema = _without_schema_titles(SignalResult.model_json_schema(mode=mode))
        reference = _without_schema_titles(_BaselineSignalResult.model_json_schema(mode=mode))
        assert schema == reference
        # Unlike comparing only an inheriting subclass, these pinned properties
        # detect a new/removed field, constraint, default, union or discriminator.
        assert schema["properties"] == _pinned_result_properties()
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        assert schema["required"] == ["instance_id", "signal_code", "status"]
        assert schema["$defs"]["SignalStatus"]["enum"] == ["ok", "partial", "unavailable", "failed"]
        assert schema["$defs"]["SignalErrorCode"]["enum"] == ["unknown_signal", "invalid_params", "planning_error", "compute_error", "invalid_output", "contract_violation"]
        quality = schema["$defs"]["DataQualityReport"]
        if mode == "validation":
            assert "data_quality_status" not in quality["properties"]
            assert "data_quality_status" not in quality.get("required", [])
        else:
            assert quality["properties"]["data_quality_status"]["readOnly"] is True
            assert "data_quality_status" in quality["required"]

    @pytest.mark.parametrize(("status", "error_code"), _STATUS_CASES)
    def test_python_and_json_dumps_keep_defaults_and_computed_output(self, status: SignalStatus, error_code: SignalErrorCode | None) -> None:
        payload = _raw_result(status, error_code)
        payload.update(risk_metadata=_raw_risk_metadata(), data_quality={})
        untouched = deepcopy(payload)
        result, _ = _assert_equivalent(payload)
        assert payload == untouched
        assert result is not None
        python_dump = result.model_dump(mode="python")
        json_dump = result.model_dump(mode="json")
        assert set(python_dump) == set(json_dump) == set(_pinned_result_properties())
        assert python_dump["risk_metadata"]["computed_at"] == datetime(2026, 1, 3, 12, tzinfo=UTC)
        assert json_dump["risk_metadata"]["computed_at"] == _FIXED_TIMESTAMP
        assert json_dump["risk_metadata"]["currency"] == "EUR"
        assert json_dump["signal_code"] == "EMA"
        assert json_dump["implementation_version"] is None
        assert json_dump["normalized_params"] == {"length": 2, "nested": [None, False, 0]}
        assert json_dump["data_quality"]["data_quality_status"] == "ok"
        assert json_dump["data_quality"]["issues"] == []
        assert json.loads(result.model_dump_json()) == json_dump
        # Deliberately NOT model_validate(json_dump): output includes the
        # read-only computed data_quality_status, forbidden on public input.

    def test_defaulted_fields_can_be_omitted_without_serialization_shape_drift(self) -> None:
        payload = {
            "instance_id": "minimal-failure",
            "signal_code": "ema",
            "status": "failed",
            "error": _raw_error(SignalErrorCode.UNKNOWN_SIGNAL),
        }
        result, _ = _assert_equivalent(payload)
        assert result is not None
        dumped = result.model_dump(mode="json")
        assert set(dumped) == set(_pinned_result_properties())
        assert dumped["normalized_params"] == {}
        for field in ("series", "annotations", "warnings"):
            assert dumped[field] == []
        for field in ("availability", "warmup", "implementation_version", "risk_metadata", "data_quality"):
            assert dumped[field] is None

    def test_nested_errors_precede_result_guards_in_declared_field_order(self) -> None:
        payload = _raw_result(SignalStatus.FAILED)
        payload.update(
            series=[{**_raw_series(), "points": []}],
            availability={},
            warmup={},
            risk_metadata={},
            unexpected=True,
        )
        result, errors = _assert_equivalent(payload)
        assert result is None
        # Adjacent repeated fields are grouped, without discarding ordered
        # error details in the public/reference comparison.
        field_order = list(dict.fromkeys(loc[0] for loc, _, _ in errors))
        assert field_order == ["series", "availability", "warmup", "risk_metadata", "unexpected"]
        assert errors[-1] == (("unexpected",), "extra_forbidden", "Extra inputs are not permitted")


# =============================================================================
# I10 — typed, sparse calendar-return provenance
#
# The provenance is ADDITIVE: it exists only on the points of the calendar
# series. Every other point in the system must keep serializing as exactly
# `date` + `value`, with no null provenance field appearing anywhere — that is
# what "sparse" means on the wire, and it is the only reason the addition is
# backward compatible for existing consumers.
# =============================================================================


class TestCalendarReturnProvenance:
    def test_ordinary_value_point_wire_dump_stays_date_and_value_only(self) -> None:
        point = SignalValuePoint(date=DAY_1, value=100.0)

        assert point.model_dump(mode="json") == {"date": "2026-01-01", "value": 100.0}
        assert set(point.model_dump(mode="python")) == {"date", "value"}
        assert set(SignalValuePoint.model_fields) == {"date", "value"}
        # A null-valued legacy point stays two keys too — no empty metadata.
        assert SignalValuePoint(date=DAY_2, value=None).model_dump(mode="json") == {"date": "2026-01-02", "value": None}

    def test_calendar_provenance_pins_public_fields_and_statuses(self) -> None:
        assert set(SignalCalendarReturnProvenance.model_fields) == set(CALENDAR_PROVENANCE_FIELDS)
        assert {status.value for status in SignalCalendarReturnPointStatus} == {
            "available",
            "missing_reference",
            "invalid_current_price",
            "invalid_reference_price",
        }
        assert set(SignalCalendarReturnValuePoint.model_fields) == {"date", "value", "provenance"}

    def test_calendar_value_point_serializes_full_typed_provenance(self) -> None:
        point = SignalCalendarReturnValuePoint(
            date=DAY_3,
            value=2.5,
            provenance=make_calendar_provenance(with_fx=True),
        )

        assert point.model_dump(mode="json") == {
            "date": "2026-01-03",
            "value": 2.5,
            "provenance": {
                "status": "available",
                "reference_target_date": "2026-01-01",
                "current_price_date": "2026-01-03",
                "current_price_days_back": 0,
                "reference_price_date": "2026-01-01",
                "reference_price_days_back": 0,
                "current_fx_date": "2026-01-02",
                "current_fx_days_back": 1,
                "reference_fx_date": "2026-01-01",
                "reference_fx_days_back": 2,
            },
        }

    def test_calendar_value_point_keeps_fx_provenance_optional(self) -> None:
        """No conversion happened → the FX half is null, the price half is not.

        The point still carries a status and a reference target date: a null
        value without a reason is exactly what this contract removes.
        """
        point = SignalCalendarReturnValuePoint(
            date=DAY_3,
            value=None,
            provenance=SignalCalendarReturnProvenance(
                status=SignalCalendarReturnPointStatus.MISSING_REFERENCE,
                reference_target_date=DAY_1,
                current_price_date=DAY_3,
                current_price_days_back=0,
            ),
        )
        dumped = point.model_dump(mode="json")

        assert dumped["value"] is None
        assert dumped["provenance"]["status"] == "missing_reference"
        assert dumped["provenance"]["reference_target_date"] == "2026-01-01"
        assert dumped["provenance"]["current_price_date"] == "2026-01-03"
        assert dumped["provenance"]["current_price_days_back"] == 0
        assert set(dumped["provenance"]) == set(CALENDAR_PROVENANCE_FIELDS)
        assert all(
            dumped["provenance"][field] is None
            for field in (
                "reference_price_date",
                "reference_price_days_back",
                "current_fx_date",
                "current_fx_days_back",
                "reference_fx_date",
                "reference_fx_days_back",
            )
        )

    def test_calendar_provenance_rejects_unknown_fields_and_missing_identity(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden|Extra inputs"):
            SignalCalendarReturnProvenance(
                status=SignalCalendarReturnPointStatus.AVAILABLE,
                reference_target_date=DAY_1,
                current_price_lag=3,
            )
        with pytest.raises(ValidationError):
            SignalCalendarReturnProvenance(reference_target_date=DAY_1)
        with pytest.raises(ValidationError):
            SignalCalendarReturnProvenance(status=SignalCalendarReturnPointStatus.AVAILABLE)
        with pytest.raises(ValidationError):
            SignalCalendarReturnProvenance(
                status=SignalCalendarReturnPointStatus.AVAILABLE,
                reference_target_date=DAY_1,
                current_price_days_back=0,
            )
        with pytest.raises(ValidationError):
            SignalCalendarReturnProvenance(
                status=SignalCalendarReturnPointStatus.AVAILABLE,
                reference_target_date=DAY_1,
                current_price_date=DAY_3,
            )
        with pytest.raises(ValidationError):
            SignalCalendarReturnProvenance(
                status="stale_reference",
                reference_target_date=DAY_1,
                current_price_date=DAY_3,
                current_price_days_back=0,
            )
        with pytest.raises(ValidationError):
            SignalCalendarReturnValuePoint(date=DAY_1, value=1.0)

    def test_signal_result_round_trips_sparse_provenance_without_touching_legacy_points(self) -> None:
        """One result, two series: only the calendar one carries provenance.

        The service re-validates its own output (normalization, then
        `slice_signal_series`), so a union that silently degrades a calendar
        point back to `SignalValuePoint` would lose the provenance without
        raising anywhere. Round-tripping the public dump is what catches it.
        """
        result = make_result(
            SignalStatus.PARTIAL,
            series=[make_line_series(), make_calendar_series()],
            availability=make_availability(
                reason=SignalAvailabilityReason.PARTIAL_UNDEFINED_METRIC,
            ),
            warnings=[
                SignalWarning(
                    code=SignalWarningCode.UNDEFINED_METRIC_WINDOW,
                    message="One calendar-return reference is unavailable",
                )
            ],
        )
        dumped = result.model_dump(mode="json")
        legacy_dump = next(item for item in dumped["series"] if item["key"] == "ema")
        calendar_dump = next(item for item in dumped["series"] if item["key"] == "calendar_return")

        assert all(set(point) == {"date", "value"} for point in legacy_dump["points"])
        assert all(set(point) == {"date", "value", "provenance"} for point in calendar_dump["points"])
        first_calendar_point = next(point for point in calendar_dump["points"] if point["date"] == "2026-01-01")
        assert first_calendar_point["value"] is None
        assert first_calendar_point["provenance"]["status"] == "missing_reference"
        assert first_calendar_point["provenance"]["reference_target_date"] == "2025-12-02"

        reparsed = SignalResult.model_validate(dumped)
        reparsed_calendar = next(item for item in reparsed.series if item.key == "calendar_return")
        reparsed_legacy = next(item for item in reparsed.series if item.key == "ema")

        assert reparsed.model_dump(mode="json") == dumped
        assert all(isinstance(point, SignalCalendarReturnValuePoint) for point in reparsed_calendar.points)
        assert {point.date: point.provenance.status for point in reparsed_calendar.points} == {
            DAY_1: SignalCalendarReturnPointStatus.MISSING_REFERENCE,
            DAY_2: SignalCalendarReturnPointStatus.AVAILABLE,
        }
        assert all(not isinstance(point, SignalCalendarReturnValuePoint) for point in reparsed_legacy.points)
        assert json.loads(result.model_dump_json()) == dumped
