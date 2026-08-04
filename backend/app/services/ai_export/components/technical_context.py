"""Focused backend-owned technical projections for non-technical AI Export analyses."""

from __future__ import annotations

import calendar
import math
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from decimal import Decimal
from statistics import pstdev

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.prices import FAPriceQueryResult
from backend.app.schemas.signals import SignalBandSeries, SignalResult, SignalScalarSeriesBase, SignalStatus
from backend.app.services.ai_export.components.envelope import SectionEnvelope
from backend.app.services.ai_export.components.resources import FxRateSeriesResource
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.technical_shared import (
    BROKER_TECHNICAL_UNIVERSE_KWARGS,
    PORTFOLIO_TECHNICAL_UNIVERSE_KWARGS,
    TechnicalUniverseBundle,
    classify_reference_level_state,
    coherent_price_currency,
    load_asset_price_results,
    load_fx_technical_bundle,
    load_technical_universe_bundle,
    signal_results_to_discrete_events,
)
from backend.app.services.ai_export.components.types import DetailLevel, Domain, PeriodBehavior
from backend.app.services.ai_export.dependencies import BuildContext
from backend.app.services.ai_export.temporal import ObservedPoint, uniform_observed_buckets
from backend.app.services.provider_registry import SignalPluginRegistry

_ASSET_CONTEXT_EVENT_KEYS = frozenset(
    {
        "price_ema_20",
        "ema_20_ema_50",
        "ema_50_ema_200",
        "rsi_14_oversold_30",
        "rsi_14_overbought_70",
        "macd_histogram_zero",
        "adx_14_trend_25",
    }
)
_FX_CONTEXT_EVENT_KEYS = frozenset(
    {
        "rate_ema_20",
        "ema_20_ema_50",
        "ema_50_ema_200",
        "rsi_14_oversold_30",
        "rsi_14_overbought_70",
        "ppo_histogram_zero",
        "roc_20_zero",
    }
)
_UNIVERSE_HISTORY_BUCKET_COUNTS = {
    DetailLevel.COMPACT: 6,
    DetailLevel.STANDARD: 12,
    DetailLevel.FULL: 24,
}
_SINGLE_ENTITY_HISTORY_BUCKET_COUNTS = {
    DetailLevel.COMPACT: 8,
    DetailLevel.STANDARD: 16,
    DetailLevel.FULL: 30,
}


class SignalCoverageAggregate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instance_id: str
    signal_code: str
    ok_count: int = Field(..., ge=0)
    partial_count: int = Field(..., ge=0)
    unavailable_count: int = Field(..., ge=0)
    failed_count: int = Field(..., ge=0)
    omission_reasons: dict[str, int] = Field(default_factory=dict)
    partial_reasons: dict[str, int] = Field(
        default_factory=dict,
        description=("Reason-code counts for INCLUDED PARTIAL results only (e.g. 'incomplete_warmup'), kept " "separate from omission_reasons (which counts omitted/unavailable/failed signals). A PARTIAL " "result is a usable-but-incomplete signal, never equivalent to a complete OK result."),
    )


class TechnicalEntityCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: str
    observation_count: int = Field(..., ge=0)
    available_start: date | None = None
    available_end: date | None = None
    staleness_days: int | None = Field(None, ge=0)
    requested_signal_count: int = Field(..., ge=0)
    included_signal_count: int = Field(..., ge=0)
    included_partial_signal_count: int = Field(
        default=0,
        ge=0,
        description="Subset of included_signal_count whose status is PARTIAL (usable but incomplete, e.g. warm-up not yet fully satisfied). Never counted as complete.",
    )
    omitted_signal_count: int = Field(..., ge=0)
    omission_reasons: dict[str, int] = Field(default_factory=dict)
    partial_reasons: dict[str, int] = Field(
        default_factory=dict,
        description="Reason-code counts for the included PARTIAL signals only, separate from omission_reasons.",
    )


class TechnicalExcludedEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: str
    reason_code: str


class TechnicalUniverseCoveragePayload(BaseModel):
    """`portfolio.technical_coverage` / `broker.technical_coverage`: multi-asset universe coverage.

    Counts describe the eligible held-asset universe (broker-deduplicated), the
    raw pre-eligibility period legs, and Signal data coverage over that universe.
    Weight ratios use gross absolute open-position value (see field descriptions).
    """

    model_config = ConfigDict(extra="forbid")

    period_position_leg_count: int = Field(
        ...,
        ge=0,
        description="Period (broker_id, asset_id) position-contribution legs before eligibility, including legs fully sold inside the period. NOT a unique-asset count. Unit: legs.",
    )
    period_contributor_asset_count: int = Field(
        ...,
        ge=0,
        description="Unique asset IDs across ALL period contribution legs before eligibility (broker-deduplicated, includes fully-sold-in-period assets). Unit: assets.",
    )
    eligible_asset_count: int = Field(
        ...,
        ge=0,
        description="Unique eligible currently-held (not fully sold, non-zero end value) assets, broker-deduplicated. Unit: assets.",
    )
    covered_asset_count: int = Field(
        ...,
        ge=0,
        description="Eligible assets with at least one included Signal (subset of eligible_asset_count). Unit: assets.",
    )
    eligible_portfolio_weight_ratio: float | None = Field(
        None,
        description="Sum of weights normalized inside the technically eligible universe; normally 1 when that universe has value. Fraction in [0,1].",
    )
    covered_portfolio_weight_ratio: float | None = Field(
        None,
        description="Covered weight normalized inside the technically eligible universe. Fraction in [0,1].",
    )
    covered_weight_ratio: float | None = Field(
        None,
        description="covered_portfolio_weight_ratio / eligible_portfolio_weight_ratio. Fraction in [0,1].",
    )
    entities: tuple[TechnicalEntityCoverage, ...]
    current_position_asset_count: int = Field(..., ge=0)
    current_scope_valued_asset_count: int = Field(..., ge=0)
    current_scope_unvalued_asset_count: int = Field(..., ge=0)
    eligible_current_scope_weight_ratio: float | None = Field(None, description="Technically eligible current-position value / all valued current-position value. Fraction in [0,1].")
    covered_current_scope_weight_ratio: float | None = Field(None, description="Signal-covered current-position value / all valued current-position value. Fraction in [0,1].")
    excluded_current_scope_weight_ratio: float | None = Field(None, description="Technically excluded current-position value / all valued current-position value. Fraction in [0,1].")
    excluded_current_asset_count: int = Field(..., ge=0)
    excluded_current_entities: tuple[TechnicalExcludedEntity, ...] = ()
    signals: tuple[SignalCoverageAggregate, ...]


class TechnicalSingleEntityCoveragePayload(BaseModel):
    """`asset.technical_coverage` / `fx.technical_coverage`: single-entity coverage.

    A single Asset or FX pair is not a multi-asset universe, so counts are
    explicit single-entity tallies (never leg/asset universe names) and there
    are no portfolio weights (a lone entity carries no relative weight).
    """

    model_config = ConfigDict(extra="forbid")

    selected_entity_count: int = Field(
        ...,
        ge=0,
        description="Entities selected for this single-entity request (always 1 for a concrete Asset/FX target). Unit: entities.",
    )
    eligible_entity_count: int = Field(
        ...,
        ge=0,
        description="Selected entities that pass eligibility (always 1 for a concrete Asset/FX target). Unit: entities.",
    )
    covered_entity_count: int = Field(
        ...,
        ge=0,
        description="Eligible entities with at least one included Signal (0 or 1). Unit: entities.",
    )
    eligible_portfolio_weight_ratio: float | None = Field(
        None,
        description="Always None for single-entity coverage: a lone entity carries no relative portfolio weight.",
    )
    covered_portfolio_weight_ratio: float | None = Field(
        None,
        description="Always None for single-entity coverage.",
    )
    covered_weight_ratio: float | None = Field(
        None,
        description="Always None for single-entity coverage.",
    )
    entities: tuple[TechnicalEntityCoverage, ...]
    signals: tuple[SignalCoverageAggregate, ...]


class TechnicalMarketContextRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: str
    portfolio_weight_ratio: float | None = None
    value_unit: str
    observation_count: int = Field(..., ge=0)
    available_start: date | None = None
    available_end: date | None = None
    current_value: float | None = None
    current_date: date | None = None
    return_1m_ratio: float | None = None
    return_3m_ratio: float | None = None
    return_period_ratio: float | None = None
    minimum_value: float | None = None
    minimum_date: date | None = None
    maximum_value: float | None = None
    maximum_date: date | None = None
    ema_20: float | None = None
    ema_50: float | None = None
    ema_200: float | None = None
    kama_20: float | None = None
    rsi_14: float | None = None
    rsi_14_state: str | None = None
    natr_14_percent: float | None = None
    atr_14: float | None = None
    daily_return_volatility_ratio: float | None = None
    bollinger_lower: float | None = None
    bollinger_middle: float | None = None
    bollinger_upper: float | None = None
    ppo_12_26_9_percent: float | None = None
    roc_20_percent: float | None = None
    current_vs_ema_50: str | None = None
    current_vs_ema_200: str | None = None
    ema_50_vs_ema_200: str | None = None


class TechnicalContextHistoryRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: str
    bucket_start: date
    bucket_end: date
    observation_count: int = Field(..., ge=1)
    observed_date: date
    current_value: float
    normalized_index_base_100: float | None = None
    return_from_first_ratio: float | None = None


class TechnicalContextEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: str
    date: date
    key: str
    signal_code: str
    signal_category: str
    semantic_description: str
    direction: str | None = None
    values: dict[str, float]


class TechnicalMarketContextPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_code: str
    entities: tuple[TechnicalMarketContextRow, ...]
    history: tuple[TechnicalContextHistoryRow, ...] = ()
    events: tuple[TechnicalContextEvent, ...] = ()
    latest_events: tuple[TechnicalContextEvent, ...] = ()


class TechnicalContextEventsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_code: str
    detected_event_count: int = Field(..., ge=0)
    exported_event_count: int = Field(..., ge=0)
    events: tuple[TechnicalContextEvent, ...]


class TechnicalEventDigestRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_code: str
    signal_category: str
    key: str
    event_count: int = Field(..., ge=1)
    latest_date: date
    upward_count: int = Field(..., ge=0)
    downward_count: int = Field(..., ge=0)


class TechnicalEventDigestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_code: str
    detected_event_count: int = Field(..., ge=0)
    included_event_count: int = Field(..., ge=0)
    rows: tuple[TechnicalEventDigestRow, ...]


def _subtract_calendar_months(value: date, months: int) -> date:
    total_months = value.year * 12 + value.month - 1 - months
    year, month_index = divmod(total_months, 12)
    month = month_index + 1
    return value.replace(year=year, month=month, day=min(value.day, calendar.monthrange(year, month)[1]))


def _observed_asset_points(result: FAPriceQueryResult | None, *, start: date, end: date) -> tuple[tuple[date, float], ...]:
    if result is None or coherent_price_currency(result) is None:
        return ()
    return tuple((point.date, float(point.close)) for point in result.prices if start <= point.date <= end and (point.backward_fill_info is None or point.backward_fill_info.days_back == 0))


def _observed_fx_points(series: FxRateSeriesResource, *, start: date, end: date) -> tuple[tuple[date, float], ...]:
    return tuple((item.requested_date, float(item.rate)) for item in series.observations if start <= item.requested_date <= end and not item.backward_filled and item.actual_date == item.requested_date)


def _value_on_or_before(points: Sequence[tuple[date, float]], target: date) -> tuple[date, float] | None:
    candidates = [point for point in points if point[0] <= target]
    return candidates[-1] if candidates else None


def _return_ratio(points: Sequence[tuple[date, float]], target: date) -> float | None:
    if not points:
        return None
    start = _value_on_or_before(points, target)
    end = points[-1]
    if start is None or start[1] == 0 or start[0] >= end[0]:
        return None
    return end[1] / start[1] - 1


def _relation(left: float | None, right: float | None) -> str | None:
    if left is None or right is None:
        return None
    if math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12):
        return "at"
    return "above" if left > right else "below"


def _signal_map(results: Sequence[SignalResult]) -> dict[str, SignalResult]:
    return {result.instance_id: result for result in results}


def _scalar_series(result: SignalResult | None, key: str) -> SignalScalarSeriesBase | None:
    if result is None or result.status not in {SignalStatus.OK, SignalStatus.PARTIAL}:
        return None
    series = next((item for item in result.series if item.key == key), None)
    return series if isinstance(series, SignalScalarSeriesBase) else None


def _latest_scalar(result: SignalResult | None, key: str) -> tuple[date, float] | None:
    series = _scalar_series(result, key)
    if series is None:
        return None
    for point in reversed(series.points):
        if point.value is not None:
            return point.date, float(point.value)
    return None


def _latest_band(result: SignalResult | None, key: str) -> tuple[date, float | None, float | None, float | None] | None:
    if result is None or result.status not in {SignalStatus.OK, SignalStatus.PARTIAL}:
        return None
    series = next((item for item in result.series if item.key == key), None)
    if not isinstance(series, SignalBandSeries):
        return None
    for point in reversed(series.points):
        if any(value is not None for value in (point.lower, point.middle, point.upper)):
            return point.date, point.lower, point.middle, point.upper
    return None


def _reason_for_result(result: SignalResult) -> str | None:
    if result.status == SignalStatus.FAILED and result.error is not None:
        return result.error.code.value
    if result.availability is not None and result.availability.reason_code is not None:
        return result.availability.reason_code.value
    return None


def _partial_reason_for_result(result: SignalResult) -> str:
    """Reason code for an INCLUDED PARTIAL signal (e.g. 'incomplete_warmup').

    A PARTIAL result is usable-but-incomplete; it always carries either an
    explicit availability reason code or a partial-coverage flag (see
    `SignalResult` validation). Falls back to the plain status value only if no
    machine-readable reason is present, so the count is never silently dropped.
    """
    reason = _reason_for_result(result)
    if reason is not None:
        return reason
    return result.status.value


def _is_included(result: SignalResult) -> bool:
    return result.status in {SignalStatus.OK, SignalStatus.PARTIAL} and bool(result.series)


def _entity_coverage(entity_id: str, points: Sequence[tuple[date, float]], results: Sequence[SignalResult], snapshot_as_of: date) -> TechnicalEntityCoverage:
    included = sum(_is_included(result) for result in results)
    included_partial = sum(_is_included(result) and result.status == SignalStatus.PARTIAL for result in results)
    reasons: dict[str, int] = {}
    partial_reasons: dict[str, int] = {}
    for result in results:
        if _is_included(result):
            if result.status == SignalStatus.PARTIAL:
                reason = _partial_reason_for_result(result)
                partial_reasons[reason] = partial_reasons.get(reason, 0) + 1
            continue
        reason = _reason_for_result(result) or result.status.value
        reasons[reason] = reasons.get(reason, 0) + 1
    return TechnicalEntityCoverage(
        entity_id=entity_id,
        observation_count=len(points),
        available_start=points[0][0] if points else None,
        available_end=points[-1][0] if points else None,
        staleness_days=(snapshot_as_of - points[-1][0]).days if points else None,
        requested_signal_count=len(results),
        included_signal_count=included,
        included_partial_signal_count=included_partial,
        omitted_signal_count=len(results) - included,
        omission_reasons=dict(sorted(reasons.items())),
        partial_reasons=dict(sorted(partial_reasons.items())),
    )


def _signal_coverage(results_by_entity: Sequence[Sequence[SignalResult]]) -> tuple[SignalCoverageAggregate, ...]:
    by_instance: dict[str, list[SignalResult]] = {}
    for results in results_by_entity:
        for result in results:
            by_instance.setdefault(result.instance_id, []).append(result)
    rows: list[SignalCoverageAggregate] = []
    for instance_id in sorted(by_instance):
        results = by_instance[instance_id]
        reasons: dict[str, int] = {}
        partial_reasons: dict[str, int] = {}
        for result in results:
            if _is_included(result):
                if result.status == SignalStatus.PARTIAL:
                    reason = _partial_reason_for_result(result)
                    partial_reasons[reason] = partial_reasons.get(reason, 0) + 1
                continue
            reason = _reason_for_result(result) or result.status.value
            reasons[reason] = reasons.get(reason, 0) + 1
        rows.append(
            SignalCoverageAggregate(
                instance_id=instance_id,
                signal_code=results[0].signal_code,
                ok_count=sum(result.status == SignalStatus.OK for result in results),
                partial_count=sum(result.status == SignalStatus.PARTIAL for result in results),
                unavailable_count=sum(result.status == SignalStatus.UNAVAILABLE for result in results),
                failed_count=sum(result.status == SignalStatus.FAILED for result in results),
                omission_reasons=dict(sorted(reasons.items())),
                partial_reasons=dict(sorted(partial_reasons.items())),
            )
        )
    return tuple(rows)


def _signal_category_for(signal_code: str) -> str:
    """Reads the plugin-owned Signal category, failing loudly for unknown plugins (requirement 2)."""
    plugin_class = SignalPluginRegistry.get_plugin(signal_code)
    if plugin_class is None:
        raise ValueError(f"unknown signal plugin for context event: {signal_code!r}")
    return plugin_class.category.value


def _context_event_from_discrete(event, *, signal_category: str | None = None) -> TechnicalContextEvent:
    payload = event.payload
    signal_code = str(payload["signal_code"])
    category = signal_category if signal_category is not None else _signal_category_for(signal_code)
    return TechnicalContextEvent(
        entity_id=str(payload["entity_id"]),
        date=event.date,
        key=str(payload["key"]),
        signal_code=signal_code,
        signal_category=category,
        semantic_description=str(payload["semantic_description"]),
        direction=str(payload["direction"]) if payload.get("direction") is not None else None,
        values={str(key): float(value) for key, value in dict(payload.get("values") or {}).items()},
    )


def _event_rows(events, *, allowed_keys: frozenset[str], max_per_entity: int | None) -> tuple[TechnicalContextEvent, ...]:
    filtered = [event for event in events if isinstance(event.payload, Mapping) and event.payload.get("key") in allowed_keys]
    deduplicated: dict[tuple[str, str], object] = {}
    for event in sorted(filtered, key=lambda item: (item.date, repr(item.dedup_key)), reverse=True):
        payload = event.payload
        entity_id = payload.get("entity_id")
        key = payload.get("key")
        if isinstance(entity_id, str) and isinstance(key, str):
            deduplicated.setdefault((entity_id, key), event)
    by_entity: dict[str, list[object]] = {}
    for event in deduplicated.values():
        by_entity.setdefault(str(event.payload["entity_id"]), []).append(event)
    selected = []
    for entity_id in sorted(by_entity):
        ordered = sorted(by_entity[entity_id], key=lambda item: (item.date, str(item.payload.get("key"))), reverse=True)
        selected.extend(ordered if max_per_entity is None else ordered[:max_per_entity])
    rows = []
    for event in sorted(selected, key=lambda item: (item.date, str(item.payload.get("entity_id")), str(item.payload.get("key")))):
        rows.append(_context_event_from_discrete(event))
    return tuple(rows)


def _latest_category_events(events, *, allowed_keys: frozenset[str]) -> tuple[TechnicalContextEvent, ...]:
    """Selects at most one latest event per ``(entity_id, signal_category)`` from all eligible context events.

    Candidates are the allowlist-filtered observation-level discrete events (never a
    max-one-per-entity truncation, requirement 4). Category is plugin-owned
    (requirement 2). Tie-break within a category is deterministic by
    ``(date, annotation key, signal code)`` (requirement 3); categories with no
    eligible event are simply omitted - never emitted as null rows.
    """
    best: dict[tuple[str, str], tuple[tuple[date, str, str], object, str]] = {}
    for event in events:
        payload = event.payload
        if not isinstance(payload, Mapping):
            continue
        entity_id = payload.get("entity_id")
        key = payload.get("key")
        signal_code = payload.get("signal_code")
        if not (isinstance(entity_id, str) and isinstance(key, str) and isinstance(signal_code, str)):
            continue
        if key not in allowed_keys:
            continue
        category = _signal_category_for(signal_code)
        sort_key = (event.date, key, signal_code)
        group = (entity_id, category)
        current = best.get(group)
        if current is None or sort_key > current[0]:
            best[group] = (sort_key, event, category)
    rows = [_context_event_from_discrete(event, signal_category=category) for _, event, category in best.values()]
    rows.sort(key=lambda row: (row.entity_id, row.signal_category, row.date, row.key, row.signal_code))
    return tuple(rows)


def _market_context_row(
    *,
    entity_id: str,
    value_unit: str,
    points: Sequence[tuple[date, float]],
    results: Sequence[SignalResult],
    period_start: date,
    period_end: date,
    portfolio_weight_ratio: float | None = None,
    daily_return_volatility_ratio: float | None = None,
    include_short_trend: bool = False,
    include_position_volatility: bool = False,
    include_fx_momentum: bool = False,
) -> TechnicalMarketContextRow:
    signal_by_instance = _signal_map(results)
    latest = points[-1] if points else None
    minimum = min(points, key=lambda item: (item[1], item[0])) if points else None
    maximum = max(points, key=lambda item: (item[1], item[0])) if points else None
    ema_20 = _latest_scalar(signal_by_instance.get("ema_20"), "ema")
    ema_50 = _latest_scalar(signal_by_instance.get("ema_50"), "ema")
    ema_200 = _latest_scalar(signal_by_instance.get("ema_200"), "ema")
    kama_20 = _latest_scalar(signal_by_instance.get("kama_20"), "kama")
    rsi_14 = _latest_scalar(signal_by_instance.get("rsi_14"), "rsi")
    natr_14 = _latest_scalar(signal_by_instance.get("natr_14"), "natr")
    atr_14 = _latest_scalar(signal_by_instance.get("atr_14"), "atr")
    ppo = _latest_scalar(signal_by_instance.get("ppo_12_26_9"), "ppo")
    roc = _latest_scalar(signal_by_instance.get("roc_20"), "roc")
    bands = _latest_band(signal_by_instance.get("bollinger_20_2"), "bands")
    rsi_series = _scalar_series(signal_by_instance.get("rsi_14"), "rsi")
    current_value = latest[1] if latest else None
    ema_50_value = ema_50[1] if ema_50 else None
    ema_200_value = ema_200[1] if ema_200 else None
    rsi_state = classify_reference_level_state(rsi_14[1], rsi_series.reference_levels) if rsi_14 and rsi_series else None
    return TechnicalMarketContextRow(
        entity_id=entity_id,
        portfolio_weight_ratio=portfolio_weight_ratio,
        value_unit=value_unit,
        observation_count=len(points),
        available_start=points[0][0] if points else None,
        available_end=points[-1][0] if points else None,
        current_value=current_value,
        current_date=latest[0] if latest else None,
        return_1m_ratio=_return_ratio(points, _subtract_calendar_months(period_end, 1)),
        return_3m_ratio=_return_ratio(points, _subtract_calendar_months(period_end, 3)),
        return_period_ratio=_return_ratio(points, period_start),
        minimum_value=minimum[1] if minimum else None,
        minimum_date=minimum[0] if minimum else None,
        maximum_value=maximum[1] if maximum else None,
        maximum_date=maximum[0] if maximum else None,
        ema_20=ema_20[1] if include_short_trend and ema_20 else None,
        ema_50=ema_50_value,
        ema_200=ema_200_value,
        kama_20=kama_20[1] if kama_20 else None,
        rsi_14=rsi_14[1] if rsi_14 else None,
        rsi_14_state=rsi_state,
        natr_14_percent=natr_14[1] if natr_14 else None,
        atr_14=atr_14[1] if include_position_volatility and atr_14 else None,
        daily_return_volatility_ratio=daily_return_volatility_ratio,
        bollinger_lower=bands[1] if include_position_volatility and bands else None,
        bollinger_middle=bands[2] if include_position_volatility and bands else None,
        bollinger_upper=bands[3] if include_position_volatility and bands else None,
        ppo_12_26_9_percent=ppo[1] if include_fx_momentum and ppo else None,
        roc_20_percent=roc[1] if include_fx_momentum and roc else None,
        current_vs_ema_50=_relation(current_value, ema_50_value),
        current_vs_ema_200=_relation(current_value, ema_200_value),
        ema_50_vs_ema_200=_relation(ema_50_value, ema_200_value),
    )


def _history_rows(
    *,
    entity_id: str,
    points: Sequence[tuple[date, float]],
    bucket_count: int,
) -> tuple[TechnicalContextHistoryRow, ...]:
    if not points:
        return ()
    observed = tuple(ObservedPoint(date=day, value=Decimal(str(value))) for day, value in points)
    buckets = uniform_observed_buckets(observed, bucket_count)
    first_value = buckets[0].first.value
    return tuple(
        TechnicalContextHistoryRow(
            entity_id=entity_id,
            bucket_start=bucket.bucket.start_date,
            bucket_end=bucket.bucket.end_date,
            observation_count=bucket.observation_count,
            observed_date=bucket.representative.date,
            current_value=float(bucket.representative.value),
            normalized_index_base_100=(float(bucket.representative.value / first_value * Decimal(100)) if first_value else None),
            return_from_first_ratio=(float(bucket.representative.value / first_value - Decimal(1)) if first_value else None),
        )
        for bucket in buckets
    )


def _universe_coverage(universe: TechnicalUniverseBundle, *, period_start: date, period_end: date) -> TechnicalUniverseCoveragePayload:
    entities = []
    results_by_entity = []
    covered_ids = set()
    for asset_id in universe.asset_ids:
        result = universe.price_results.by_asset_id.get(asset_id)
        points = _observed_asset_points(result, start=period_start, end=period_end)
        signals = tuple(result.signals) if result is not None else ()
        coverage = _entity_coverage(f"asset:{asset_id}", points, signals, period_end)
        entities.append(coverage)
        results_by_entity.append(signals)
        if coverage.included_signal_count:
            covered_ids.add(asset_id)
    eligible_weight = float(sum(universe.weights.values(), Decimal(0)))
    covered_weight = float(sum((universe.weights.get(asset_id, Decimal(0)) for asset_id in covered_ids), Decimal(0)))
    eligible_scope_weight = float(sum((universe.current_scope_weights.get(asset_id, Decimal(0)) for asset_id in universe.asset_ids), Decimal(0)))
    covered_scope_weight = float(sum((universe.current_scope_weights.get(asset_id, Decimal(0)) for asset_id in covered_ids), Decimal(0)))
    excluded_scope_weight = float(sum((universe.current_scope_weights.get(asset_id, Decimal(0)) for asset_id in universe.excluded_current_assets), Decimal(0)))
    has_scope_weights = bool(universe.current_scope_weights)
    return TechnicalUniverseCoveragePayload(
        period_position_leg_count=universe.period_position_leg_count,
        period_contributor_asset_count=universe.period_contributor_asset_count,
        eligible_asset_count=len(universe.asset_ids),
        covered_asset_count=len(covered_ids),
        eligible_portfolio_weight_ratio=eligible_weight,
        covered_portfolio_weight_ratio=covered_weight,
        covered_weight_ratio=(covered_weight / eligible_weight if eligible_weight else 0.0),
        entities=tuple(entities),
        current_position_asset_count=len(universe.current_position_asset_ids),
        current_scope_valued_asset_count=len(universe.current_scope_weights),
        current_scope_unvalued_asset_count=len(universe.current_unvalued_asset_ids),
        eligible_current_scope_weight_ratio=eligible_scope_weight if has_scope_weights else None,
        covered_current_scope_weight_ratio=covered_scope_weight if has_scope_weights else None,
        excluded_current_scope_weight_ratio=excluded_scope_weight if has_scope_weights else None,
        excluded_current_asset_count=len(universe.excluded_current_assets),
        excluded_current_entities=tuple(TechnicalExcludedEntity(entity_id=f"asset:{asset_id}", reason_code=reason) for asset_id, reason in sorted(universe.excluded_current_assets.items())),
        signals=_signal_coverage(results_by_entity),
    )


async def _build_universe_coverage(context: BuildContext, *, universe_kwargs: Mapping[str, object]) -> TechnicalUniverseCoveragePayload:
    scope = context.scope
    assert scope is not None
    universe = await load_technical_universe_bundle(context, **universe_kwargs)
    return _universe_coverage(universe, period_start=scope.period_start, period_end=scope.period_end)


async def _build_universe_market_context(context: BuildContext, *, universe_kwargs: Mapping[str, object], policy_code: str) -> TechnicalMarketContextPayload:
    scope = context.scope
    assert scope is not None
    universe = await load_technical_universe_bundle(context, **universe_kwargs)
    rows = []
    history = []
    detected = []
    for asset_id in universe.asset_ids:
        result = universe.price_results.by_asset_id.get(asset_id)
        points = _observed_asset_points(result, start=scope.period_start, end=scope.period_end)
        signals = tuple(result.signals) if result is not None else ()
        detected.extend(signal_results_to_discrete_events(signals, entity_id=f"asset:{asset_id}", asset_id=asset_id))
        rows.append(
            _market_context_row(
                entity_id=f"asset:{asset_id}",
                value_unit=coherent_price_currency(result) or "unavailable",
                points=points,
                results=signals,
                period_start=scope.period_start,
                period_end=scope.period_end,
                portfolio_weight_ratio=float(universe.weights.get(asset_id, Decimal(0))),
            )
        )
        history.extend(
            _history_rows(
                entity_id=f"asset:{asset_id}",
                points=points,
                bucket_count=_UNIVERSE_HISTORY_BUCKET_COUNTS[scope.detail_level],
            )
        )
    latest_events = _latest_category_events(detected, allowed_keys=_ASSET_CONTEXT_EVENT_KEYS)
    return TechnicalMarketContextPayload(
        policy_code=policy_code,
        entities=tuple(rows),
        history=tuple(history),
        latest_events=latest_events,
    )


async def _build_universe_context_events(context: BuildContext, *, universe_kwargs: Mapping[str, object], policy_code: str) -> TechnicalContextEventsPayload:
    scope = context.scope
    assert scope is not None
    universe = await load_technical_universe_bundle(context, **universe_kwargs)
    detected = []
    for asset_id in universe.asset_ids:
        result = universe.price_results.by_asset_id.get(asset_id)
        signals = tuple(result.signals) if result is not None else ()
        detected.extend(signal_results_to_discrete_events(signals, entity_id=f"asset:{asset_id}", asset_id=asset_id))
    events = _event_rows(detected, allowed_keys=_ASSET_CONTEXT_EVENT_KEYS, max_per_entity=4)
    return TechnicalContextEventsPayload(policy_code=policy_code, detected_event_count=len(detected), exported_event_count=len(events), events=events)


async def _build_portfolio_event_digest(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> TechnicalEventDigestPayload:
    scope = context.scope
    assert scope is not None
    universe = await load_technical_universe_bundle(context, **PORTFOLIO_TECHNICAL_UNIVERSE_KWARGS)
    detected = []
    for asset_id in universe.asset_ids:
        result = universe.price_results.by_asset_id.get(asset_id)
        signals = tuple(result.signals) if result is not None else ()
        detected.extend(signal_results_to_discrete_events(signals, entity_id=f"asset:{asset_id}", asset_id=asset_id))
    grouped: dict[tuple[str, str], list[object]] = {}
    for event in detected:
        if isinstance(event.payload, Mapping) and event.payload.get("key") in _ASSET_CONTEXT_EVENT_KEYS:
            grouped.setdefault((str(event.payload.get("signal_code")), str(event.payload.get("key"))), []).append(event)
    rows = []
    included_total = 0
    recent_boundary = scope.period_end - timedelta(days=30)
    for signal_code, key in sorted(grouped):
        events = grouped[(signal_code, key)]
        recent = [event for event in events if event.date >= recent_boundary]
        included = recent or [max(events, key=lambda event: (event.date, repr(event.dedup_key)))]
        included_total += len(included)
        rows.append(
            TechnicalEventDigestRow(
                signal_code=signal_code,
                signal_category=_signal_category_for(signal_code),
                key=key,
                event_count=len(included),
                latest_date=max(event.date for event in included),
                upward_count=sum(event.payload.get("direction") == "up" for event in included),
                downward_count=sum(event.payload.get("direction") == "down" for event in included),
            )
        )
    return TechnicalEventDigestPayload(
        policy_code="all_last_30d_else_latest_per_annotation_v1",
        detected_event_count=len(detected),
        included_event_count=included_total,
        rows=tuple(rows),
    )


async def _build_asset_coverage(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> TechnicalSingleEntityCoveragePayload:
    scope = context.scope
    assert scope is not None and scope.asset_id is not None
    price_results = await load_asset_price_results(context)
    result = price_results.by_asset_id.get(scope.asset_id)
    points = _observed_asset_points(result, start=scope.period_start, end=scope.period_end)
    signals = tuple(result.signals) if result is not None else ()
    coverage = _entity_coverage(f"asset:{scope.asset_id}", points, signals, scope.period_end)
    return TechnicalSingleEntityCoveragePayload(
        selected_entity_count=1,
        eligible_entity_count=1,
        covered_entity_count=int(coverage.included_signal_count > 0),
        entities=(coverage,),
        signals=_signal_coverage((signals,)),
    )


async def _build_asset_position_context(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> TechnicalMarketContextPayload:
    scope = context.scope
    assert scope is not None and scope.asset_id is not None
    price_results = await load_asset_price_results(context)
    result = price_results.by_asset_id.get(scope.asset_id)
    points = _observed_asset_points(result, start=scope.period_start, end=scope.period_end)
    signals = tuple(result.signals) if result is not None else ()
    discrete = signal_results_to_discrete_events(signals, entity_id=f"asset:{scope.asset_id}", asset_id=scope.asset_id)
    events = _event_rows(
        discrete,
        allowed_keys=_ASSET_CONTEXT_EVENT_KEYS,
        max_per_entity=12,
    )
    latest_events = _latest_category_events(discrete, allowed_keys=_ASSET_CONTEXT_EVENT_KEYS)
    row = _market_context_row(
        entity_id=f"asset:{scope.asset_id}",
        value_unit=coherent_price_currency(result) or "unavailable",
        points=points,
        results=signals,
        period_start=scope.period_start,
        period_end=scope.period_end,
        include_short_trend=True,
        include_position_volatility=True,
    )
    return TechnicalMarketContextPayload(
        policy_code="asset_position_context_v2",
        entities=(row,),
        history=_history_rows(
            entity_id=f"asset:{scope.asset_id}",
            points=points,
            bucket_count=_SINGLE_ENTITY_HISTORY_BUCKET_COUNTS[scope.detail_level],
        ),
        events=events,
        latest_events=latest_events,
    )


async def _build_fx_coverage(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> TechnicalSingleEntityCoveragePayload:
    scope = context.scope
    assert scope is not None and scope.base_currency is not None and scope.quote_currency is not None
    bundle = await load_fx_technical_bundle(context)
    points = _observed_fx_points(bundle.rate_series, start=scope.period_start, end=scope.period_end)
    entity_id = f"fx:{scope.base_currency}/{scope.quote_currency}"
    coverage = _entity_coverage(entity_id, points, bundle.signal_results, scope.period_end)
    return TechnicalSingleEntityCoveragePayload(
        selected_entity_count=1,
        eligible_entity_count=1,
        covered_entity_count=int(coverage.included_signal_count > 0),
        entities=(coverage,),
        signals=_signal_coverage((bundle.signal_results,)),
    )


async def _build_fx_market_summary(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> TechnicalMarketContextPayload:
    scope = context.scope
    assert scope is not None and scope.base_currency is not None and scope.quote_currency is not None
    bundle = await load_fx_technical_bundle(context)
    points = _observed_fx_points(bundle.rate_series, start=scope.period_start, end=scope.period_end)
    entity_id = f"fx:{scope.base_currency}/{scope.quote_currency}"
    discrete = signal_results_to_discrete_events(bundle.signal_results, entity_id=entity_id)
    events = _event_rows(
        discrete,
        allowed_keys=_FX_CONTEXT_EVENT_KEYS,
        max_per_entity=8,
    )
    latest_events = _latest_category_events(discrete, allowed_keys=_FX_CONTEXT_EVENT_KEYS)
    daily_returns = [current[1] / previous[1] - 1 for previous, current in zip(points, points[1:], strict=False) if previous[1] != 0]
    row = _market_context_row(
        entity_id=entity_id,
        value_unit=f"{scope.quote_currency}_per_{scope.base_currency}",
        points=points,
        results=bundle.signal_results,
        period_start=scope.period_start,
        period_end=scope.period_end,
        daily_return_volatility_ratio=pstdev(daily_returns) if len(daily_returns) >= 2 else None,
        include_short_trend=True,
        include_fx_momentum=True,
    )
    return TechnicalMarketContextPayload(
        policy_code="fx_market_context_v2",
        entities=(row,),
        history=_history_rows(
            entity_id=entity_id,
            points=points,
            bucket_count=_SINGLE_ENTITY_HISTORY_BUCKET_COUNTS[scope.detail_level],
        ),
        events=events,
        latest_events=latest_events,
    )


async def _build_portfolio_coverage(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> TechnicalUniverseCoveragePayload:
    return await _build_universe_coverage(context, universe_kwargs=PORTFOLIO_TECHNICAL_UNIVERSE_KWARGS)


async def _build_broker_coverage(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> TechnicalUniverseCoveragePayload:
    return await _build_universe_coverage(context, universe_kwargs=BROKER_TECHNICAL_UNIVERSE_KWARGS)


async def _build_portfolio_market_context(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> TechnicalMarketContextPayload:
    return await _build_universe_market_context(context, universe_kwargs=PORTFOLIO_TECHNICAL_UNIVERSE_KWARGS, policy_code="portfolio_asset_snapshot_v2")


async def _build_broker_market_context(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> TechnicalMarketContextPayload:
    return await _build_universe_market_context(context, universe_kwargs=BROKER_TECHNICAL_UNIVERSE_KWARGS, policy_code="broker_asset_comparison_v2")


async def _build_portfolio_context_events(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> TechnicalContextEventsPayload:
    return await _build_universe_context_events(context, universe_kwargs=PORTFOLIO_TECHNICAL_UNIVERSE_KWARGS, policy_code="latest_structural_per_asset_v1")


async def _build_broker_context_events(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> TechnicalContextEventsPayload:
    return await _build_universe_context_events(context, universe_kwargs=BROKER_TECHNICAL_UNIVERSE_KWARGS, policy_code="latest_structural_per_asset_v1")


PORTFOLIO_TECHNICAL_CONTEXT_COMPONENTS: tuple[ComponentSpec, ...] = (
    ComponentSpec("portfolio.technical_coverage", 1, frozenset({Domain.PORTFOLIO}), TechnicalUniverseCoveragePayload, _build_portfolio_coverage, period_behavior=PeriodBehavior.WINDOWED),
    ComponentSpec("portfolio.asset_market_context", 1, frozenset({Domain.PORTFOLIO}), TechnicalMarketContextPayload, _build_portfolio_market_context, period_behavior=PeriodBehavior.WINDOWED),
    ComponentSpec("portfolio.context_events", 1, frozenset({Domain.PORTFOLIO}), TechnicalContextEventsPayload, _build_portfolio_context_events, period_behavior=PeriodBehavior.WINDOWED),
    ComponentSpec("portfolio.event_digest", 1, frozenset({Domain.PORTFOLIO}), TechnicalEventDigestPayload, _build_portfolio_event_digest, period_behavior=PeriodBehavior.WINDOWED),
)

BROKER_TECHNICAL_CONTEXT_COMPONENTS: tuple[ComponentSpec, ...] = (
    ComponentSpec("broker.technical_coverage", 1, frozenset({Domain.BROKER}), TechnicalUniverseCoveragePayload, _build_broker_coverage, period_behavior=PeriodBehavior.WINDOWED),
    ComponentSpec("broker.asset_market_context", 1, frozenset({Domain.BROKER}), TechnicalMarketContextPayload, _build_broker_market_context, period_behavior=PeriodBehavior.WINDOWED),
    ComponentSpec("broker.context_events", 1, frozenset({Domain.BROKER}), TechnicalContextEventsPayload, _build_broker_context_events, period_behavior=PeriodBehavior.WINDOWED),
)

ASSET_TECHNICAL_CONTEXT_COMPONENTS: tuple[ComponentSpec, ...] = (
    ComponentSpec("asset.technical_coverage", 1, frozenset({Domain.ASSET}), TechnicalSingleEntityCoveragePayload, _build_asset_coverage, period_behavior=PeriodBehavior.WINDOWED),
    ComponentSpec("asset.position_market_context", 1, frozenset({Domain.ASSET}), TechnicalMarketContextPayload, _build_asset_position_context, period_behavior=PeriodBehavior.WINDOWED),
)

FX_TECHNICAL_CONTEXT_COMPONENTS: tuple[ComponentSpec, ...] = (
    ComponentSpec("fx.technical_coverage", 1, frozenset({Domain.FX}), TechnicalSingleEntityCoveragePayload, _build_fx_coverage, period_behavior=PeriodBehavior.WINDOWED),
    ComponentSpec("fx.market_summary", 1, frozenset({Domain.FX}), TechnicalMarketContextPayload, _build_fx_market_summary, period_behavior=PeriodBehavior.WINDOWED),
)

TECHNICAL_CONTEXT_COMPONENTS: tuple[ComponentSpec, ...] = (
    *PORTFOLIO_TECHNICAL_CONTEXT_COMPONENTS,
    *BROKER_TECHNICAL_CONTEXT_COMPONENTS,
    *ASSET_TECHNICAL_CONTEXT_COMPONENTS,
    *FX_TECHNICAL_CONTEXT_COMPONENTS,
)

__all__ = [
    "ASSET_TECHNICAL_CONTEXT_COMPONENTS",
    "BROKER_TECHNICAL_CONTEXT_COMPONENTS",
    "FX_TECHNICAL_CONTEXT_COMPONENTS",
    "PORTFOLIO_TECHNICAL_CONTEXT_COMPONENTS",
    "TECHNICAL_CONTEXT_COMPONENTS",
    "SignalCoverageAggregate",
    "TechnicalContextEvent",
    "TechnicalContextEventsPayload",
    "TechnicalContextHistoryRow",
    "TechnicalSingleEntityCoveragePayload",
    "TechnicalUniverseCoveragePayload",
    "TechnicalEntityCoverage",
    "TechnicalEventDigestPayload",
    "TechnicalEventDigestRow",
    "TechnicalMarketContextPayload",
    "TechnicalMarketContextRow",
]
