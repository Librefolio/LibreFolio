"""Tests for library-independent technical signal contracts."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Literal

import pytest
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.signals import (
    SignalAnnotationRequest,
    SignalAnnotationSampling,
    SignalAvailability,
    SignalAvailabilityReason,
    SignalAxisRole,
    SignalAxisSpec,
    SignalBandPoint,
    SignalBandSeries,
    SignalCatalogDefinition,
    SignalCategory,
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
    SignalLineSeries,
    SignalOutputSpec,
    SignalOutputValueSource,
    SignalPriceField,
    SignalPricePoint,
    SignalPriceValueSource,
    SignalReferenceLevel,
    SignalRequest,
    SignalResult,
    SignalSeriesKind,
    SignalStatus,
    SignalThresholdCrossingRequest,
    SignalThresholdDirection,
    SignalUnit,
    SignalValuePoint,
    SignalValueRegion,
    SignalViewTransform,
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
        unit=SignalUnit.PRICE,
        axis=make_axis(),
        view_transform=SignalViewTransform.BASE_PERCENTAGE,
        points=[SignalValuePoint(date=point_date, value=value) for point_date, value in zip(dates, values, strict=True)],
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
        kind=SignalSeriesKind.LINE,
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

    def test_output_spec_rejects_unadvertised_defaults(self):
        with pytest.raises(ValidationError, match="supports_reference_levels"):
            SignalOutputSpec(
                key="rsi",
                label_key="signals.rsi.output",
                kind=SignalSeriesKind.LINE,
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
        payload["kind"] = "area"
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
        assert "color" not in json.dumps(dumped)


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

    def test_catalog_rejects_duplicate_outputs_and_domains(self):
        catalog = make_catalog().model_dump()
        catalog["output_specs"] = [make_output_spec(), make_output_spec()]
        with pytest.raises(ValidationError, match="output spec keys"):
            SignalCatalogDefinition.model_validate(catalog)

        catalog = make_catalog().model_dump()
        catalog["compatible_domains"] = [SignalDomain.ASSET, SignalDomain.ASSET]
        with pytest.raises(ValidationError, match="compatible_domains"):
            SignalCatalogDefinition.model_validate(catalog)

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

    def test_error_details_must_be_json_safe(self):
        with pytest.raises(ValidationError, match="non-JSON"):
            SignalError(
                code=SignalErrorCode.CONTRACT_VIOLATION,
                message="Bad output",
                details={"value": object()},
            )
