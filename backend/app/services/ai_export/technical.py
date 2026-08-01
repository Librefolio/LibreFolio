"""Domain-neutral AI Export technical planning and execution."""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from backend.app.schemas.ai_export import (
    AiExportAssetTargetReference,
    AiExportCoverage,
    AiExportDerivedState,
    AiExportEvent,
    AiExportEventDirection,
    AiExportFxPairTargetReference,
    AiExportSampledPoint,
    AiExportSignalSemantic,
    AiExportSignalStatus,
    AiExportTechnicalComponent,
    AiExportTechnicalSnapshot,
    AiExportTechnicalTarget,
    AiExportTechnicalTargetReference,
)
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.signals import (
    SignalAnnotation,
    SignalAreaSeries,
    SignalBandComponent,
    SignalBandSeries,
    SignalBandValueSource,
    SignalBarSeries,
    SignalCadence,
    SignalDataPolicy,
    SignalDomain,
    SignalEventPoint,
    SignalExecutionContext,
    SignalLineCrossoverRequest,
    SignalLineSeries,
    SignalOutputValueSource,
    SignalPriceField,
    SignalPricePoint,
    SignalPriceValueSource,
    SignalRequest,
    SignalResult,
    SignalSeries,
    SignalSourceCapability,
    SignalStatus,
    SignalThresholdCrossingRequest,
    SignalThresholdDirection,
    SignalUnit,
)
from backend.app.services.ai_export.coverage import TargetCoverage, aggregate_coverage
from backend.app.services.ai_export.models import (
    AnnotationDirection,
    AnnotationRequestKind,
    AnnotationRequestSpec,
    AnnotationSourceKind,
    AnnotationSourceSpec,
    ResolvedProfile,
    SignalEligibility,
    SignalInstanceSpec,
    SignalOutputMode,
    TechnicalDepth,
)
from backend.app.services.ai_export.sampling import (
    NumericPoint,
    round_asset_price,
    round_compact_volume,
    round_fx_rate,
    round_oscillator,
    round_percentage,
    sample_and_round_numeric_points,
)
from backend.app.services.signal_service import SignalExecutionPlan, SignalService

_OK_STATUSES = frozenset({SignalStatus.OK, SignalStatus.PARTIAL})
_BAND_COMPONENTS = (
    SignalBandComponent.LOWER,
    SignalBandComponent.MIDDLE,
    SignalBandComponent.UPPER,
)
_STATE_ONLY_DEPTHS = frozenset(
    {
        TechnicalDepth.LATEST_STATES,
        TechnicalDepth.LATEST_BREADTH,
        TechnicalDepth.BREADTH_ONLY,
    }
)
_LATEST_CONTEXT_DEPTHS = frozenset(
    {
        TechnicalDepth.STANDARD_SUMMARY,
        TechnicalDepth.LATEST_TREND_MOMENTUM_VOLATILITY,
        TechnicalDepth.LATEST_NEUTRAL_CONTEXT,
        TechnicalDepth.LATEST_DRAWDOWN_CONTEXT,
        TechnicalDepth.LATEST_RATE_AND_STATES,
        TechnicalDepth.LATEST_EXPOSURE_AND_STATES,
        TechnicalDepth.LATEST_TREND_AND_VOLATILITY,
    }
)
_BUNDLE_OUTPUT_DEPTHS = frozenset(
    {
        TechnicalDepth.STANDARD,
        TechnicalDepth.FULL,
        TechnicalDepth.SAMPLED_STANDARD,
        TechnicalDepth.STANDARD_WITH_SERIES,
        TechnicalDepth.STANDARD_WITH_SAMPLING,
        TechnicalDepth.STANDARD_WITH_RECOVERY_EVENTS,
    }
)
_EVENT_DEPTHS = (
    frozenset(
        {
            TechnicalDepth.LATEST_BREADTH,
            TechnicalDepth.BREADTH_ONLY,
        }
    )
    | _LATEST_CONTEXT_DEPTHS
    | _BUNDLE_OUTPUT_DEPTHS
)


@dataclass(frozen=True, slots=True)
class PreparedTechnicalTarget:
    """Immutable execution plan for one Asset or FX technical target."""

    resolved_profile: ResolvedProfile
    target: AiExportTechnicalTargetReference
    execution_plan: SignalExecutionPlan
    technical_window: DateRangeModel
    calculation_range: DateRangeModel
    calculation_warmup_start: date
    target_currency: str
    source_reference: str
    nav_weight_pct: Decimal = Decimal("0")

    @property
    def profile(self) -> ResolvedProfile:
        return self.resolved_profile

    @property
    def signal_plan(self) -> SignalExecutionPlan:
        return self.execution_plan

    @property
    def load_start(self) -> date:
        return self.calculation_warmup_start

    @property
    def warmup_start(self) -> date:
        return self.calculation_warmup_start

    @property
    def event_limit(self) -> int:
        return _profile_event_limit(self.resolved_profile)


@dataclass(frozen=True, slots=True)
class TechnicalTargetResult:
    """AI Export artifacts produced for one prepared technical target."""

    resolved_profile: ResolvedProfile
    target: AiExportTechnicalTargetReference
    technical_target: AiExportTechnicalTarget | None
    states: tuple[AiExportDerivedState, ...]
    events: tuple[AiExportEvent, ...]
    signal_semantics: tuple[AiExportSignalSemantic, ...]
    target_coverage: TargetCoverage
    calculation_range: DateRangeModel
    calculation_warmup_start: date
    event_limit: int
    raw_signal_results: tuple[SignalResult, ...] = field(default=(), repr=False, compare=False)

    @property
    def coverage(self) -> TargetCoverage:
        return self.target_coverage

    @property
    def semantics(self) -> tuple[AiExportSignalSemantic, ...]:
        return self.signal_semantics

    @property
    def raw_results(self) -> tuple[SignalResult, ...]:
        return self.raw_signal_results

    @property
    def signal_results(self) -> tuple[SignalResult, ...]:
        return self.raw_signal_results

    @property
    def warmup_start(self) -> date:
        return self.calculation_warmup_start


@dataclass(frozen=True, slots=True)
class CombinedTechnicalResult:
    """Combined technical DTOs and coverage for an ordered target batch."""

    technical: AiExportTechnicalSnapshot | None
    states: tuple[AiExportDerivedState, ...]
    events: tuple[AiExportEvent, ...]
    signal_semantics: tuple[AiExportSignalSemantic, ...]
    coverage: AiExportCoverage

    @property
    def technical_snapshot(self) -> AiExportTechnicalSnapshot | None:
        return self.technical

    @property
    def semantics(self) -> tuple[AiExportSignalSemantic, ...]:
        return self.signal_semantics

    @property
    def aggregate_coverage(self) -> AiExportCoverage:
        return self.coverage


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _target_key(target: AiExportTechnicalTargetReference) -> str:
    if isinstance(target, AiExportAssetTargetReference):
        return f"asset:{target.asset_id}"
    if isinstance(target, AiExportFxPairTargetReference):
        return f"fx_pair:{target.base_currency}/{target.quote_currency}"
    raise TypeError("technical target must be an asset or fx_pair reference")


def _target_identity(target: AiExportTechnicalTargetReference) -> str:
    return target.model_dump_json()


def _resolved_profile_identity(profile: ResolvedProfile) -> tuple[str, int, int]:
    return (
        profile.profile_id,
        profile.profile_version,
        profile.schema_version,
    )


def _copy_target(target: AiExportTechnicalTargetReference) -> AiExportTechnicalTargetReference:
    return target.model_copy(deep=True)


def _validated_nav_weight(value: Decimal | int | str | None) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, bool):
        raise TypeError("nav_weight_pct must be numeric")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("nav_weight_pct must be a finite decimal") from exc
    if not result.is_finite():
        raise ValueError("nav_weight_pct must be finite")
    return abs(result)


def _profile_event_limit(profile: ResolvedProfile) -> int:
    override = profile.technical.event_limit_override
    if override is not None:
        return override
    limit = profile.detail_overlay.event_limits.max_events
    if limit is None:
        raise ValueError("resolved AI Export profile requires a fixed event limit")
    return limit


def _depth_allows_events(depth: TechnicalDepth) -> bool:
    if depth in _EVENT_DEPTHS:
        return True
    if depth in {TechnicalDepth.NONE, TechnicalDepth.LATEST_STATES}:
        return False
    raise ValueError(f"unsupported technical depth: {depth}")


def _effective_output_mode(
    depth: TechnicalDepth,
    spec: SignalInstanceSpec,
) -> SignalOutputMode:
    if depth == TechnicalDepth.NONE or depth in _STATE_ONLY_DEPTHS:
        return SignalOutputMode.STATE_EVENT_ONLY
    if spec.mode == SignalOutputMode.STATE_EVENT_ONLY:
        return spec.mode
    if depth in _LATEST_CONTEXT_DEPTHS:
        return SignalOutputMode.LATEST
    if depth in _BUNDLE_OUTPUT_DEPTHS:
        return spec.mode
    raise ValueError(f"unsupported technical depth: {depth}")


def _signal_domain(profile: ResolvedProfile, target: AiExportTechnicalTargetReference) -> SignalDomain:
    bundle = profile.technical_bundle
    if bundle is None:
        raise ValueError("resolved profile has no technical bundle")
    if bundle.target_domain.value == SignalDomain.ASSET.value:
        if not isinstance(target, AiExportAssetTargetReference):
            raise TypeError("asset technical bundle requires an asset target")
        return SignalDomain.ASSET
    if not isinstance(target, AiExportFxPairTargetReference):
        raise TypeError("FX technical bundle requires an fx_pair target")
    return SignalDomain.FX


def _signal_request(spec: SignalInstanceSpec) -> SignalRequest:
    return SignalRequest(
        instance_id=spec.instance_id,
        signal_code=spec.signal_code,
        params=_thaw_json(spec.params),
    )


def _annotation_source(source: AnnotationSourceSpec):
    if source.kind == AnnotationSourceKind.PRICE:
        return SignalPriceValueSource(field=SignalPriceField(source.price_field))
    if source.kind == AnnotationSourceKind.SIGNAL_COMPONENT:
        if source.band_component is not None:
            return SignalBandValueSource(
                instance_id=source.signal_instance_id,
                series_key=source.component,
                component=SignalBandComponent(source.band_component.value),
            )
        return SignalOutputValueSource(
            instance_id=source.signal_instance_id,
            series_key=source.component,
        )
    raise ValueError("constant annotation sources are not supported by SignalService")


def _annotation_request(spec: AnnotationRequestSpec, limit: int):
    common = {
        "key": spec.key,
        "attach_to_instance_id": spec.attach_to_instance_id,
        "observed_only": True,
        "min_gap_days": spec.min_gap_days,
        "limit": limit,
    }
    if spec.kind == AnnotationRequestKind.LINE_CROSSOVER:
        if spec.left is None or spec.right is None:
            raise ValueError(f"annotation '{spec.key}' has incomplete line sources")
        return SignalLineCrossoverRequest(
            **common,
            left=_annotation_source(spec.left),
            right=_annotation_source(spec.right),
        )
    if spec.source is None or spec.threshold is None:
        raise ValueError(f"annotation '{spec.key}' has incomplete threshold fields")
    direction = {
        AnnotationDirection.UP: SignalThresholdDirection.UP,
        AnnotationDirection.DOWN: SignalThresholdDirection.DOWN,
        AnnotationDirection.BOTH: SignalThresholdDirection.BOTH,
    }[spec.direction]
    return SignalThresholdCrossingRequest(
        **common,
        source=_annotation_source(spec.source),
        threshold=spec.threshold,
        direction=direction,
    )


def _clamped_history_start(start: date, history_points: int) -> date:
    if history_points < 0:
        raise ValueError("history_points must be non-negative")
    available_days = start.toordinal() - date.min.toordinal()
    return start - timedelta(days=min(history_points, available_days))


def prepare_technical_target(
    profile: ResolvedProfile,
    target: AiExportTechnicalTargetReference,
    technical_window: DateRangeModel,
    target_currency: str | None = None,
    source_reference: str | None = None,
    nav_weight_pct: Decimal | int | str | None = None,
    signal_service: SignalService | None = None,
) -> PreparedTechnicalTarget | None:
    """Resolve a static profile bundle into one plugin-derived execution plan."""

    if not isinstance(profile, ResolvedProfile):
        raise TypeError("profile must be a ResolvedProfile")
    bundle = profile.technical_bundle
    if bundle is None:
        return None
    if not isinstance(technical_window, DateRangeModel):
        raise TypeError("technical_window must be a DateRangeModel")

    domain = _signal_domain(profile, target)
    target_key = _target_key(target)
    if target_currency is None:
        if isinstance(target, AiExportFxPairTargetReference):
            target_currency = target.quote_currency
        else:
            raise ValueError("target_currency is required for asset technical targets")
    source_reference = source_reference or target_key
    event_limit = _profile_event_limit(profile)
    requests = tuple(_signal_request(spec) for spec in bundle.signals)
    annotations = tuple(_annotation_request(spec, event_limit) for spec in bundle.annotations) if _depth_allows_events(profile.technical_depth) else ()
    context = SignalExecutionContext(
        domain=domain,
        requested_range=technical_window.model_copy(deep=True),
        cadence=SignalCadence.DAILY,
        data_policy=SignalDataPolicy.STRICT_CONTIGUOUS,
        source_reference=source_reference,
        target_currency=target_currency,
        observed_only=True,
    )
    service = signal_service or SignalService()
    execution_plan = service.prepare_plan(
        requests,
        context,
        annotation_requests=annotations,
    )
    calculation_warmup_start = _clamped_history_start(
        technical_window.start,
        execution_plan.max_history_points_before_visible,
    )
    calculation_range = DateRangeModel(
        start=calculation_warmup_start,
        end=technical_window.end or technical_window.start,
    )
    return PreparedTechnicalTarget(
        resolved_profile=profile,
        target=_copy_target(target),
        execution_plan=execution_plan,
        technical_window=technical_window.model_copy(deep=True),
        calculation_range=calculation_range,
        calculation_warmup_start=calculation_warmup_start,
        target_currency=context.target_currency or target_currency,
        source_reference=context.source_reference,
        nav_weight_pct=_validated_nav_weight(nav_weight_pct),
    )


def _window_end(window: DateRangeModel) -> date:
    return window.end or window.start


def _in_window(value: date, window: DateRangeModel) -> bool:
    return window.start <= value <= _window_end(window)


def _is_observed(point: SignalPricePoint) -> bool:
    return point.backward_fill_info is None or point.backward_fill_info.days_back == 0


def _finite_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return result if result.is_finite() else None


def _rounder(unit: SignalUnit | str, target: AiExportTechnicalTargetReference) -> Callable[[Decimal], Decimal]:
    normalized = unit.value if isinstance(unit, SignalUnit) else str(unit)
    if normalized == SignalUnit.PRICE.value:
        return round_fx_rate if isinstance(target, AiExportFxPairTargetReference) else round_asset_price
    if normalized == SignalUnit.PERCENTAGE.value:
        return round_percentage
    if normalized == SignalUnit.INDEX.value:
        return round_oscillator
    if normalized == SignalUnit.VOLUME.value:
        return round_compact_volume
    return lambda value: value


def _series_by_key(result: SignalResult, key: str) -> SignalSeries | None:
    return next((series for series in result.series if series.key == key), None)


def _scalar_points(
    result: SignalResult,
    key: str,
    window: DateRangeModel,
    observed_dates: set[date],
) -> tuple[NumericPoint, ...]:
    series = _series_by_key(result, key)
    if not isinstance(series, (SignalLineSeries, SignalAreaSeries, SignalBarSeries)):
        return ()
    points: list[NumericPoint] = []
    for point in series.points:
        value = _finite_decimal(point.value)
        if value is None or not _in_window(point.date, window) or point.date not in observed_dates:
            continue
        points.append(NumericPoint(date=point.date, value=value))
    return tuple(points)


def _band_points(
    result: SignalResult,
    key: str,
    component: SignalBandComponent,
    window: DateRangeModel,
    observed_dates: set[date],
) -> tuple[NumericPoint, ...]:
    series = _series_by_key(result, key)
    if not isinstance(series, SignalBandSeries):
        return ()
    points: list[NumericPoint] = []
    for point in series.points:
        value = _finite_decimal(getattr(point, component.value))
        if value is None or not _in_window(point.date, window) or point.date not in observed_dates:
            continue
        points.append(NumericPoint(date=point.date, value=value))
    return tuple(points)


def _sampled_points(
    points: tuple[NumericPoint, ...],
    spec: SignalInstanceSpec,
    prepared: PreparedTechnicalTarget,
    unit: SignalUnit | str,
) -> tuple[AiExportSampledPoint, ...]:
    output_mode = _effective_output_mode(
        prepared.resolved_profile.technical_depth,
        spec,
    )
    if output_mode not in {SignalOutputMode.SAMPLED, SignalOutputMode.FULL_WINDOW}:
        return ()
    sampling = prepared.resolved_profile.detail_overlay.sampling
    if not sampling.include_series:
        return ()
    sampled = sample_and_round_numeric_points(
        points,
        sampling,
        _rounder(unit, prepared.target),
    )
    return tuple(AiExportSampledPoint(date=point.date, value=point.value) for point in sampled)


def _latest_point(
    points: tuple[NumericPoint, ...],
    prepared: PreparedTechnicalTarget,
    unit: SignalUnit | str,
) -> AiExportSampledPoint | None:
    if not points or not prepared.resolved_profile.detail_overlay.sampling.include_latest:
        return None
    point = points[-1]
    return AiExportSampledPoint(
        date=point.date,
        value=_rounder(unit, prepared.target)(point.value),
    )


def _technical_component(
    *,
    component_code: str,
    semantic_id: str,
    unit: SignalUnit | str,
    points: tuple[NumericPoint, ...],
    spec: SignalInstanceSpec,
    prepared: PreparedTechnicalTarget,
) -> AiExportTechnicalComponent | None:
    latest = _latest_point(points, prepared, unit)
    sampled = _sampled_points(points, spec, prepared, unit)
    if latest is None and not sampled:
        return None
    return AiExportTechnicalComponent(
        component_code=component_code,
        semantic_id=semantic_id,
        unit=unit.value if isinstance(unit, SignalUnit) else str(unit),
        latest=latest,
        sampled_points=list(sampled),
    )


def _technical_components(
    result: SignalResult,
    spec: SignalInstanceSpec,
    prepared: PreparedTechnicalTarget,
    observed_dates: set[date],
) -> tuple[AiExportTechnicalComponent, ...]:
    if (
        _effective_output_mode(
            prepared.resolved_profile.technical_depth,
            spec,
        )
        == SignalOutputMode.STATE_EVENT_ONLY
    ):
        return ()
    components: list[AiExportTechnicalComponent] = []
    for requested_key in spec.requested_components:
        series = _series_by_key(result, requested_key)
        if isinstance(series, (SignalLineSeries, SignalAreaSeries, SignalBarSeries)):
            component = _technical_component(
                component_code=series.key,
                semantic_id=series.semantic_id,
                unit=series.unit,
                points=_scalar_points(
                    result,
                    series.key,
                    prepared.technical_window,
                    observed_dates,
                ),
                spec=spec,
                prepared=prepared,
            )
            if component is not None:
                components.append(component)
        elif isinstance(series, SignalBandSeries):
            for band_component in _BAND_COMPONENTS:
                component = _technical_component(
                    component_code=f"{series.key}.{band_component.value}",
                    semantic_id=series.semantic_id,
                    unit=series.unit,
                    points=_band_points(
                        result,
                        series.key,
                        band_component,
                        prepared.technical_window,
                        observed_dates,
                    ),
                    spec=spec,
                    prepared=prepared,
                )
                if component is not None:
                    components.append(component)
    return tuple(components)


def _accepted_results(
    prepared: PreparedTechnicalTarget,
    raw_results: Sequence[SignalResult],
) -> dict[str, SignalResult]:
    result_by_instance = {result.instance_id: result for result in raw_results if isinstance(result, SignalResult) and result.status in _OK_STATUSES}
    bundle = prepared.resolved_profile.technical_bundle
    if bundle is None:
        return {}
    return {spec.instance_id: result_by_instance[spec.instance_id] for spec in bundle.signals if spec.instance_id in result_by_instance}


def _result_for_signal(
    specs: Sequence[SignalInstanceSpec],
    accepted: Mapping[str, SignalResult],
    signal_code: str,
    *,
    period: int | None = None,
) -> tuple[SignalInstanceSpec, SignalResult] | None:
    for spec in specs:
        result = accepted.get(spec.instance_id)
        if result is None or result.signal_code != signal_code:
            continue
        if period is not None:
            raw_period = result.normalized_params.get("period")
            try:
                if int(raw_period) != period:
                    continue
            except (TypeError, ValueError):
                continue
        return spec, result
    return None


def _latest_common(*point_groups: tuple[NumericPoint, ...]) -> tuple[date, tuple[Decimal, ...]] | None:
    if not point_groups or any(not points for points in point_groups):
        return None
    timelines = [{point.date: point.value for point in points} for points in point_groups]
    common_dates = set(timelines[0])
    for timeline in timelines[1:]:
        common_dates.intersection_update(timeline)
    if not common_dates:
        return None
    latest_date = max(common_dates)
    return latest_date, tuple(timeline[latest_date] for timeline in timelines)


def _state(
    prepared: PreparedTechnicalTarget,
    result: SignalResult,
    *,
    code: str,
    state: str,
    as_of: date,
    component_code: str,
    value: Decimal | None,
    unit: SignalUnit | str,
) -> AiExportDerivedState:
    return AiExportDerivedState(
        target=_copy_target(prepared.target),
        code=code,
        state=state,
        as_of=as_of,
        signal_instance_id=result.instance_id,
        signal_code=result.signal_code,
        component_code=component_code,
        value=None if value is None else _rounder(unit, prepared.target)(value),
    )


def _threshold_state(value: Decimal, oversold: Decimal, overbought: Decimal) -> str:
    if value >= overbought:
        return "overbought"
    if value <= oversold:
        return "oversold"
    return "neutral"


def _param_decimal(result: SignalResult, name: str) -> Decimal | None:
    return _finite_decimal(result.normalized_params.get(name))


def _derived_states(
    prepared: PreparedTechnicalTarget,
    price_points: Sequence[SignalPricePoint],
    accepted: Mapping[str, SignalResult],
    observed_dates: set[date],
) -> tuple[AiExportDerivedState, ...]:
    bundle = prepared.resolved_profile.technical_bundle
    if bundle is None:
        return ()
    specs = bundle.signals
    close_points = tuple(NumericPoint(date=point.date, value=value) for point in price_points if _in_window(point.date, prepared.technical_window) and _is_observed(point) and (value := _finite_decimal(point.close)) is not None)
    states: list[AiExportDerivedState] = []
    ema_results: dict[int, tuple[SignalInstanceSpec, SignalResult]] = {}

    for period in (20, 50, 200):
        match = _result_for_signal(specs, accepted, "EMA", period=period)
        if match is None:
            continue
        spec, result = match
        if "ema" not in spec.requested_components:
            continue
        ema_points = _scalar_points(
            result,
            "ema",
            prepared.technical_window,
            observed_dates,
        )
        latest = _latest_common(close_points, ema_points)
        if latest is None:
            continue
        as_of, (price, ema) = latest
        states.append(
            _state(
                prepared,
                result,
                code=f"price_vs_ema{period}",
                state="above" if price > ema else "below",
                as_of=as_of,
                component_code="ema",
                value=ema,
                unit=SignalUnit.PRICE,
            )
        )
        ema_results[period] = match

    if 20 in ema_results and 50 in ema_results:
        ema20_spec, ema20_result = ema_results[20]
        _ema50_spec, ema50_result = ema_results[50]
        latest = _latest_common(
            _scalar_points(
                ema20_result,
                "ema",
                prepared.technical_window,
                observed_dates,
            ),
            _scalar_points(
                ema50_result,
                "ema",
                prepared.technical_window,
                observed_dates,
            ),
        )
        if latest is not None and "ema" in ema20_spec.requested_components:
            as_of, (ema20, ema50) = latest
            states.append(
                _state(
                    prepared,
                    ema20_result,
                    code="ema20_vs_ema50",
                    state="above" if ema20 > ema50 else "below",
                    as_of=as_of,
                    component_code="ema",
                    value=ema20,
                    unit=SignalUnit.PRICE,
                )
            )

    scalar_state_specs = (
        ("ADX", "adx", "adx_strength"),
        ("RSI", "rsi", "rsi_state"),
        ("MFI", "mfi", "mfi_state"),
        ("STOCH_RSI", "k", "stochastic_rsi_k_state"),
    )
    for signal_code, component_code, state_code in scalar_state_specs:
        match = _result_for_signal(specs, accepted, signal_code)
        if match is None:
            continue
        spec, result = match
        if component_code not in spec.requested_components:
            continue
        series = _series_by_key(result, component_code)
        if series is None:
            continue
        points = _scalar_points(
            result,
            component_code,
            prepared.technical_window,
            observed_dates,
        )
        if not points:
            continue
        latest = points[-1]
        if signal_code == "ADX":
            state_value = "strong_trend" if latest.value >= Decimal("25") else "weak_trend"
        else:
            oversold = _param_decimal(result, "oversold")
            overbought = _param_decimal(result, "overbought")
            if oversold is None or overbought is None:
                continue
            state_value = _threshold_state(latest.value, oversold, overbought)
        states.append(
            _state(
                prepared,
                result,
                code=state_code,
                state=state_value,
                as_of=latest.date,
                component_code=component_code,
                value=latest.value,
                unit=series.unit,
            )
        )

    for histogram_code in ("MACD", "PPO"):
        histogram_match = _result_for_signal(specs, accepted, histogram_code)
        if histogram_match is None:
            continue
        spec, result = histogram_match
        series = _series_by_key(result, "histogram")
        if "histogram" not in spec.requested_components or series is None:
            continue
        points = _scalar_points(
            result,
            "histogram",
            prepared.technical_window,
            observed_dates,
        )
        if points:
            latest = points[-1]
            histogram_state = "positive" if latest.value > 0 else "negative" if latest.value < 0 else "neutral"
            states.append(
                _state(
                    prepared,
                    result,
                    code="macd_or_ppo_histogram",
                    state=histogram_state,
                    as_of=latest.date,
                    component_code="histogram",
                    value=latest.value,
                    unit=series.unit,
                )
            )
            break

    obv_match = _result_for_signal(specs, accepted, "OBV")
    if obv_match is not None:
        spec, result = obv_match
        series = _series_by_key(result, "obv")
        if "obv" in spec.requested_components and series is not None:
            points = _scalar_points(
                result,
                "obv",
                prepared.technical_window,
                observed_dates,
            )
            if len(points) >= 2:
                previous, latest = points[-2:]
                obv_state = "strengthening" if latest.value > previous.value else "weakening" if latest.value < previous.value else "unchanged"
                states.append(
                    _state(
                        prepared,
                        result,
                        code="obv_direction",
                        state=obv_state,
                        as_of=latest.date,
                        component_code="obv",
                        value=latest.value,
                        unit=series.unit,
                    )
                )

    for signal_code, series_key, state_code in (
        ("BOLLINGER", "bands", "price_vs_bollinger"),
        ("DONCHIAN", "channels", "price_vs_donchian"),
    ):
        match = _result_for_signal(specs, accepted, signal_code)
        if match is None:
            continue
        spec, result = match
        series = _series_by_key(result, series_key)
        if series_key not in spec.requested_components or not isinstance(series, SignalBandSeries):
            continue
        lower_points = _band_points(
            result,
            series_key,
            SignalBandComponent.LOWER,
            prepared.technical_window,
            observed_dates,
        )
        middle_points = _band_points(
            result,
            series_key,
            SignalBandComponent.MIDDLE,
            prepared.technical_window,
            observed_dates,
        )
        upper_points = _band_points(
            result,
            series_key,
            SignalBandComponent.UPPER,
            prepared.technical_window,
            observed_dates,
        )
        latest = _latest_common(close_points, lower_points, upper_points)
        if latest is None:
            continue
        as_of, (price, lower, upper) = latest
        middle_by_date = {point.date: point.value for point in middle_points}
        middle = middle_by_date.get(as_of)
        if price > upper:
            band_state = "above_upper"
            component_code = f"{series_key}.upper"
            state_value = upper
        elif price < lower:
            band_state = "below_lower"
            component_code = f"{series_key}.lower"
            state_value = lower
        else:
            band_state = "inside"
            if middle is None:
                component_code = f"{series_key}.lower"
                state_value = lower
            else:
                component_code = f"{series_key}.middle"
                state_value = middle
        states.append(
            _state(
                prepared,
                result,
                code=state_code,
                state=band_state,
                as_of=as_of,
                component_code=component_code,
                value=state_value,
                unit=series.unit,
            )
        )

    return tuple(states)


def _component_from_source(
    source: AnnotationSourceSpec | None,
    attached_instance_id: str,
) -> str | None:
    if source is None or source.kind != AnnotationSourceKind.SIGNAL_COMPONENT or source.signal_instance_id != attached_instance_id:
        return None
    if source.band_component is not None:
        return f"{source.component}.{source.band_component.value}"
    return source.component


def _annotation_component(
    annotation: SignalAnnotation,
    annotation_spec: AnnotationRequestSpec | None,
    result: SignalResult,
) -> str | None:
    candidates: list[str] = []
    if annotation_spec is not None:
        for source in (annotation_spec.left, annotation_spec.right, annotation_spec.source):
            component = _component_from_source(source, result.instance_id)
            if component is not None:
                candidates.append(component)
    if not candidates:
        for metadata_key in ("left", "right", "source"):
            source = annotation.metadata.get(metadata_key)
            if not isinstance(source, Mapping) or source.get("instance_id") != result.instance_id:
                continue
            series_key = source.get("series_key")
            if not isinstance(series_key, str):
                continue
            component = source.get("component")
            candidates.append(f"{series_key}.{component}" if isinstance(component, str) else series_key)
    unique = tuple(dict.fromkeys(candidates))
    if len(unique) == 1:
        return unique[0]
    if not unique and len(result.series) == 1:
        return result.series[0].key
    return None


def _event_unit(result: SignalResult, component_code: str | None) -> SignalUnit | str | None:
    if component_code is not None:
        series = _series_by_key(result, component_code.split(".", 1)[0])
        if series is not None:
            return series.unit
    units = tuple(dict.fromkeys(series.unit for series in result.series))
    return units[0] if len(units) == 1 else None


def _event_sort_key(event: AiExportEvent) -> tuple[Any, ...]:
    values = tuple(sorted((str(key), str(value)) for key, value in event.values.items()))
    return (
        event.date,
        event.code,
        _target_identity(event.target),
        event.signal_instance_id or "",
        event.signal_code or "",
        event.component_code or "",
        event.direction.value if event.direction is not None else "",
        values,
    )


def deduplicate_and_limit_events(
    events: Sequence[AiExportEvent],
    limit: int,
) -> tuple[AiExportEvent, ...]:
    """Deterministically deduplicate events and retain the most recent limit."""

    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("limit must be an integer")
    if limit < 1:
        raise ValueError("limit must be positive")
    deduplicated: dict[tuple[Any, ...], AiExportEvent] = {}
    for event in events:
        deduplicated.setdefault(_event_sort_key(event), event)
    ordered = sorted(deduplicated.values(), key=_event_sort_key)
    if len(ordered) > limit:
        ordered = ordered[-limit:]
    return tuple(sorted(ordered, key=_event_sort_key))


def _events(
    prepared: PreparedTechnicalTarget,
    accepted: Mapping[str, SignalResult],
) -> tuple[AiExportEvent, ...]:
    if not _depth_allows_events(prepared.resolved_profile.technical_depth):
        return ()
    bundle = prepared.resolved_profile.technical_bundle
    if bundle is None:
        return ()
    annotation_specs = {spec.key: spec for spec in bundle.annotations}
    events: list[AiExportEvent] = []
    for signal_spec in bundle.signals:
        result = accepted.get(signal_spec.instance_id)
        if result is None:
            continue
        for annotation in result.annotations:
            if not _in_window(annotation.date, prepared.technical_window):
                continue
            component_code = _annotation_component(
                annotation,
                annotation_specs.get(annotation.key),
                result,
            )
            unit = _event_unit(result, component_code)
            round_value = _rounder(unit, prepared.target) if unit is not None else lambda value: value
            values = {key: round_value(value) for key, raw_value in annotation.values.items() if (value := _finite_decimal(raw_value)) is not None}
            if not values:
                continue
            events.append(
                AiExportEvent(
                    target=_copy_target(prepared.target),
                    date=annotation.date,
                    code=annotation.key,
                    signal_instance_id=result.instance_id,
                    signal_code=result.signal_code,
                    component_code=component_code,
                    direction=(AiExportEventDirection(annotation.direction.value) if annotation.direction is not None else None),
                    values=values,
                )
            )
    return deduplicate_and_limit_events(events, prepared.event_limit)


def _plugin_classes_by_instance(plan: SignalExecutionPlan) -> dict[str, type]:
    return {instance_id: computation.plugin_class for computation in plan.computations for instance_id in computation.instance_ids}


def _present_series_keys(
    result: SignalResult,
    spec: SignalInstanceSpec,
    prepared: PreparedTechnicalTarget,
    observed_dates: set[date],
) -> tuple[str, ...]:
    keys: list[str] = []
    for key in spec.requested_components:
        series = _series_by_key(result, key)
        if isinstance(series, (SignalLineSeries, SignalAreaSeries, SignalBarSeries)):
            if _scalar_points(result, key, prepared.technical_window, observed_dates):
                keys.append(key)
        elif isinstance(series, SignalBandSeries):
            if any(
                _band_points(
                    result,
                    key,
                    component,
                    prepared.technical_window,
                    observed_dates,
                )
                for component in _BAND_COMPONENTS
            ):
                keys.append(key)
    return tuple(keys)


def _semantics(
    prepared: PreparedTechnicalTarget,
    accepted: Mapping[str, SignalResult],
    observed_dates: set[date],
    artifact_instances: set[str],
) -> tuple[AiExportSignalSemantic, ...]:
    bundle = prepared.resolved_profile.technical_bundle
    if bundle is None:
        return ()
    plugin_classes = _plugin_classes_by_instance(prepared.execution_plan)
    semantics: dict[str, AiExportSignalSemantic] = {}
    for spec in bundle.signals:
        if spec.instance_id not in artifact_instances:
            continue
        result = accepted.get(spec.instance_id)
        if result is None:
            continue
        plugin_class = plugin_classes.get(spec.instance_id)
        if plugin_class is not None:
            semantics.setdefault(
                plugin_class.semantic_id,
                AiExportSignalSemantic(
                    semantic_id=plugin_class.semantic_id,
                    description=plugin_class.semantic_description,
                ),
            )
        present_keys = set(
            _present_series_keys(
                result,
                spec,
                prepared,
                observed_dates,
            )
        )
        for series in result.series:
            if series.key not in present_keys:
                continue
            semantics.setdefault(
                series.semantic_id,
                AiExportSignalSemantic(
                    semantic_id=series.semantic_id,
                    description=series.semantic_description,
                ),
            )
    return tuple(semantics.values())


def _volume_available(
    price_points: Sequence[SignalPricePoint],
    technical_window: DateRangeModel,
) -> bool:
    return any(_in_window(point.date, technical_window) and _is_observed(point) and _finite_decimal(point.volume) is not None for point in price_points)


def _observed_close_dates(
    price_points: Sequence[SignalPricePoint],
    technical_window: DateRangeModel,
) -> set[date]:
    return {point.date for point in price_points if _in_window(point.date, technical_window) and _is_observed(point) and _finite_decimal(point.close) is not None}


async def execute_technical_target(
    prepared: PreparedTechnicalTarget,
    price_points: Sequence[SignalPricePoint],
    event_points: Sequence[SignalEventPoint] = (),
    signal_service: SignalService | None = None,
    events_loaded: bool = True,
    source_capability: SignalSourceCapability | None = None,
) -> TechnicalTargetResult:
    """Execute one prepared target against caller-owned bulk-loaded inputs.

    ``source_capability`` carries the authoritative volume-semantics
    verdict derived from the raw ``FAPricePoint`` series (via
    ``AssetSourceManager.derive_signal_source_capability``) *after* prices
    are loaded — the execution plan/context is frozen at
    ``prepare_technical_target()`` time, before source provenance is known,
    so it always defaults to unknown/false. Callers backed by real asset
    price data (asset/portfolio/broker) must pass the capability derived
    from that same series; FX targets have no meaningful volume source and
    should leave this ``None``.
    """

    if not isinstance(prepared, PreparedTechnicalTarget):
        raise TypeError("prepared must be a PreparedTechnicalTarget")
    service = signal_service or SignalService()
    raw_results = tuple(
        await service.execute(
            prepared.execution_plan,
            price_points,
            event_points,
            events_loaded=events_loaded,
            source_capability=source_capability,
        )
    )
    observed_dates = _observed_close_dates(
        price_points,
        prepared.technical_window,
    )
    technical_eligible = bool(observed_dates)
    accepted = _accepted_results(prepared, raw_results) if technical_eligible else {}
    bundle = prepared.resolved_profile.technical_bundle
    if bundle is None:
        raise ValueError("prepared technical target lost its bundle")

    technical_signals = []
    technical_instances: set[str] = set()
    for spec in bundle.signals:
        result = accepted.get(spec.instance_id)
        if result is None or result.implementation_version is None:
            continue
        components = _technical_components(
            result,
            spec,
            prepared,
            observed_dates,
        )
        if not components:
            continue
        technical_instances.add(spec.instance_id)
        technical_signals.append(
            {
                "instance_id": result.instance_id,
                "signal_code": result.signal_code,
                "implementation_version": result.implementation_version,
                "normalized_params": copy.deepcopy(result.normalized_params),
                "status": AiExportSignalStatus(result.status.value),
                "components": list(components),
            }
        )

    technical_target = (
        AiExportTechnicalTarget(
            target=_copy_target(prepared.target),
            signals=technical_signals,
        )
        if technical_signals
        else None
    )
    states = _derived_states(
        prepared,
        price_points,
        accepted,
        observed_dates,
    )
    events = _events(prepared, accepted)
    state_instances = {state.signal_instance_id for state in states if state.signal_instance_id is not None}
    event_instances = {event.signal_instance_id for event in events if event.signal_instance_id is not None}
    artifact_instances = technical_instances | state_instances | event_instances
    semantics = _semantics(
        prepared,
        accepted,
        observed_dates,
        artifact_instances,
    )

    volume_instances = {spec.instance_id for spec in bundle.signals if spec.eligibility == SignalEligibility.VOLUME_REQUIRED}
    volume_eligible = (
        technical_eligible
        and bool(volume_instances)
        and _volume_available(
            price_points,
            prepared.technical_window,
        )
    )
    volume_analyzed = volume_eligible and bool(volume_instances & artifact_instances)
    analyzed = technical_target is not None or bool(states) or bool(events)
    coverage = TargetCoverage(
        target_key=_target_key(prepared.target),
        eligible=technical_eligible,
        analyzed=analyzed,
        nav_weight_pct=prepared.nav_weight_pct,
        volume_eligible=volume_eligible,
        volume_analyzed=volume_analyzed,
        derived_states={state.code: state.state for state in states},
    )
    return TechnicalTargetResult(
        resolved_profile=prepared.resolved_profile,
        target=_copy_target(prepared.target),
        technical_target=technical_target,
        states=states,
        events=events,
        signal_semantics=semantics,
        target_coverage=coverage,
        calculation_range=prepared.calculation_range.model_copy(deep=True),
        calculation_warmup_start=prepared.calculation_warmup_start,
        event_limit=prepared.event_limit,
        raw_signal_results=raw_results,
    )


def combine_technical_results(
    results: Sequence[TechnicalTargetResult],
) -> CombinedTechnicalResult:
    """Combine ordered target artifacts, rejecting duplicate target references."""

    targets = tuple(results)
    if any(not isinstance(result, TechnicalTargetResult) for result in targets):
        raise TypeError("results must contain TechnicalTargetResult values")
    common_profile = targets[0].resolved_profile if targets else None
    if common_profile is not None:
        common_profile_identity = _resolved_profile_identity(common_profile)
        if any(_resolved_profile_identity(result.resolved_profile) != common_profile_identity for result in targets[1:]):
            raise ValueError("technical results must share exact profile_id, profile_version, and schema_version")
    identities = [_target_identity(result.target) for result in targets]
    if len(identities) != len(set(identities)):
        raise ValueError("technical target references must be unique")

    technical_targets = [result.technical_target for result in targets if result.technical_target is not None]
    technical = AiExportTechnicalSnapshot(targets=technical_targets) if technical_targets else None
    states = tuple(state for result in targets for state in result.states)
    all_events = tuple(event for result in targets for event in result.events)
    event_limit = _profile_event_limit(common_profile) if common_profile is not None else 1
    events = deduplicate_and_limit_events(all_events, event_limit) if all_events else ()
    semantics_by_id: dict[str, AiExportSignalSemantic] = {}
    for result in targets:
        for semantic in result.signal_semantics:
            semantics_by_id.setdefault(semantic.semantic_id, semantic)
    coverage = aggregate_coverage(result.target_coverage for result in targets)
    return CombinedTechnicalResult(
        technical=technical,
        states=states,
        events=events,
        signal_semantics=tuple(semantics_by_id.values()),
        coverage=coverage,
    )


combine_technical_target_results = combine_technical_results


__all__ = [
    "CombinedTechnicalResult",
    "PreparedTechnicalTarget",
    "TechnicalTargetResult",
    "combine_technical_results",
    "combine_technical_target_results",
    "deduplicate_and_limit_events",
    "execute_technical_target",
    "prepare_technical_target",
]
