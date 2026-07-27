"""Pure date and series-preparation primitives shared across analytics."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.portfolio import (
    DataQualityExcludedAsset,
    DataQualityExclusionReason,
    DataQualityReport,
)
from backend.app.schemas.prices import FAPricePoint, FAPriceQueryResult
from backend.app.schemas.risk import (
    AssetReturnPoint,
    AssetReturnSeries,
    AssetValuationPoint,
    AssetValuationSeries,
    PreparedAssetSeries,
    PreparedAssetSeriesSet,
)


def date_is_within_range(
    value: date,
    start: date,
    end: date | None,
) -> bool:
    """Return whether a date is inside an inclusive range."""
    return start <= value <= (end or start)


def distance_slots(
    start: date,
    end: date,
    cadence: str,
) -> int:
    """Count cadence slots between two dates."""
    if cadence == "daily":
        return (end - start).days
    if cadence == "weekly":
        return math.ceil((end - start).days / 7)
    if cadence == "monthly":
        return (end.year - start.year) * 12 + end.month - start.month
    return 0


def gap_slots(
    previous: date,
    current: date,
    cadence: str,
) -> int:
    """Count missing cadence slots between two observed dates."""
    return max(0, distance_slots(previous, current, cadence) - 1)


def observed_annualization(
    n_observations: int,
    baseline_date: date | None,
    final_date: date | None,
) -> tuple[int, float | None]:
    """Return calendar span and observed annualization factor."""
    if n_observations < 0:
        raise ValueError("n_observations cannot be negative")
    if n_observations == 0:
        return 0, None
    if baseline_date is None or final_date is None:
        raise ValueError("non-empty observations require baseline and final dates")
    calendar_days = (final_date - baseline_date).days
    if calendar_days <= 0:
        raise ValueError("final_date must follow baseline_date")
    return calendar_days, n_observations * 365 / calendar_days


def fx_content_fingerprint(
    series: Sequence[PreparedAssetSeries],
) -> str:
    """Hash the FX observations actually consumed by prepared valuations."""
    entries = {
        (
            point.native_currency,
            point.target_currency,
            point.valuation_date.isoformat(),
            point.fx_rate_date.isoformat() if point.fx_rate_date else None,
            format(point.fx_rate, "f") if point.fx_rate is not None else None,
        )
        for item in series
        for point in item.valuations.points
        if point.native_currency != point.target_currency
    }
    payload = json.dumps(sorted(entries), separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _AssetSeriesInput:
    asset_id: int
    all_points: dict[date, FAPricePoint]
    target_points: dict[date, FAPricePoint]
    warnings: tuple[str, ...]


def _indexed_points(
    result: FAPriceQueryResult,
    end_date: date,
) -> dict[date, FAPricePoint]:
    points: dict[date, FAPricePoint] = {}
    for point in result.prices:
        if point.date > end_date:
            continue
        if point.date in points:
            raise ValueError(f"asset {result.asset_id} has duplicate price date {point.date.isoformat()}")
        points[point.date] = point
    return dict(sorted(points.items()))


def _price_is_fresh(point: FAPricePoint) -> bool:
    info = point.backward_fill_info
    return info is None or info.days_back == 0


def _valuation_point(
    point: FAPricePoint,
    target_currency: str,
) -> AssetValuationPoint:
    if point.currency != target_currency:
        raise ValueError("valuation point is not converted to target currency")

    info = point.backward_fill_info
    effective_price_date = info.actual_rate_date if info is not None else point.date
    native_currency = point.original_currency or point.currency
    native_close = point.original_close if point.original_close is not None else point.close
    converted = native_currency != target_currency
    fx_rate = point.close / native_close if converted else Decimal("1")
    fx_rate_date = (info.fx_rate_date if info is not None else None) or (point.date if converted else None)
    is_fx_carried_forward = bool(info is not None and info.fx_days_back is not None and info.fx_days_back > 0)
    warnings: list[str] = []
    if effective_price_date < point.date:
        warnings.append("price_carried_forward")
    if is_fx_carried_forward:
        warnings.append("fx_carried_forward")

    return AssetValuationPoint(
        valuation_date=point.date,
        effective_price_date=effective_price_date,
        is_price_carried_forward=effective_price_date < point.date,
        native_close=native_close,
        native_currency=native_currency,
        fx_rate=fx_rate,
        fx_rate_date=fx_rate_date,
        is_fx_carried_forward=is_fx_carried_forward,
        target_close=point.close,
        target_currency=target_currency,
        price_source=point.source_plugin_key,
        warnings=warnings,
    )


def _unusable_reason(
    points: dict[date, FAPricePoint],
    target_currency: str,
) -> DataQualityExclusionReason:
    if not points:
        return DataQualityExclusionReason.MISSING_PRICE
    if all(point.currency is None for point in points.values()):
        return DataQualityExclusionReason.INVALID_CURRENCY
    if any(point.currency != target_currency for point in points.values()):
        return DataQualityExclusionReason.MISSING_FX
    return DataQualityExclusionReason.MISSING_PRICE


def prepare_asset_series_set(
    price_results: Sequence[FAPriceQueryResult],
    *,
    requested_range: DateRangeModel,
    target_currency: str,
) -> PreparedAssetSeriesSet:
    """Build one converted-price joint calendar, then derive simple returns."""
    target_currency = Currency.validate_code(target_currency)
    requested_end = requested_range.end or requested_range.start
    asset_ids = [result.asset_id for result in price_results]
    if len(asset_ids) != len(set(asset_ids)):
        raise ValueError("price_results must contain unique asset IDs")

    active: list[_AssetSeriesInput] = []
    unusable_assets: list[DataQualityExcludedAsset] = []
    warnings: set[str] = set()
    missing_fx_pairs: set[str] = set()
    for result in price_results:
        all_points = _indexed_points(result, requested_end)
        target_points = {point_date: point for point_date, point in all_points.items() if point.currency == target_currency}
        warnings.update(result.errors)
        missing_fx_pairs.update(f"{point.currency}/{target_currency}" for point in all_points.values() if requested_range.start <= point.date <= requested_end and point.currency is not None and point.currency != target_currency)
        if not target_points:
            reason = _unusable_reason(all_points, target_currency)
            unusable_assets.append(
                DataQualityExcludedAsset(
                    asset_id=result.asset_id,
                    reason=reason,
                )
            )
            if reason == DataQualityExclusionReason.MISSING_FX:
                warnings.add(f"missing_fx:{result.asset_id}")
            continue
        active.append(
            _AssetSeriesInput(
                asset_id=result.asset_id,
                all_points=all_points,
                target_points=target_points,
                warnings=tuple(result.errors),
            )
        )

    if not active:
        data_quality = DataQualityReport(
            unusable_assets=sorted(unusable_assets, key=lambda item: item.asset_id),
            unresolved_fx_pairs=sorted(missing_fx_pairs),
            warnings=sorted(warnings),
        )
        empty_series: list[PreparedAssetSeries] = []
        return PreparedAssetSeriesSet(
            requested_range=requested_range,
            target_currency=target_currency,
            series=empty_series,
            fx_fingerprint=fx_content_fingerprint(empty_series),
            data_quality=data_quality,
            warnings=sorted(warnings),
        )

    candidate_quote_dates = sorted({point.date for item in active for point in item.all_points.values() if requested_range.start <= point.date <= requested_end and _price_is_fresh(point)})
    complete_dates = set(active[0].target_points)
    for item in active[1:]:
        complete_dates.intersection_update(item.target_points)
    complete_dates = {point_date for point_date in complete_dates if point_date <= requested_end}

    prior_baselines = [point_date for point_date in complete_dates if point_date < requested_range.start]
    if prior_baselines:
        baseline_date = max(prior_baselines)
    else:
        in_range_complete = [point_date for point_date in complete_dates if requested_range.start <= point_date <= requested_end]
        baseline_date = min(in_range_complete) if in_range_complete else None

    if baseline_date is None:
        warnings.add("no_common_valuation_baseline")
        data_quality = DataQualityReport(
            unusable_assets=sorted(unusable_assets, key=lambda item: item.asset_id),
            unresolved_fx_pairs=sorted(missing_fx_pairs),
            warnings=sorted(warnings),
        )
        prepared = [
            PreparedAssetSeries(
                valuations=AssetValuationSeries(
                    asset_id=item.asset_id,
                    target_currency=target_currency,
                    warnings=list(item.warnings),
                ),
                returns=AssetReturnSeries(
                    asset_id=item.asset_id,
                    target_currency=target_currency,
                    warnings=list(item.warnings),
                ),
            )
            for item in active
        ]
        return PreparedAssetSeriesSet(
            requested_range=requested_range,
            target_currency=target_currency,
            series=prepared,
            fx_fingerprint=fx_content_fingerprint(prepared),
            data_quality=data_quality,
            warnings=sorted(warnings),
        )

    if not prior_baselines:
        warnings.add("baseline_inside_requested_range")
        for item in active:
            if not any(point_date < requested_range.start for point_date in item.target_points):
                warnings.add(f"short_history:{item.asset_id}")

    return_candidates = [point_date for point_date in candidate_quote_dates if point_date > baseline_date]
    included_return_dates = [point_date for point_date in return_candidates if all(point_date in item.target_points for item in active)]
    incomplete_valuation_dates = sorted(set(return_candidates) - set(included_return_dates))
    joint_valuation_dates = [baseline_date, *included_return_dates]

    prepared_series: list[PreparedAssetSeries] = []
    carried_price_asset_ids: set[int] = set()
    carried_fx_pairs: set[str] = set()
    carried_price_points = 0
    carried_fx_points = 0
    fresh_quote_points = 0
    for item in active:
        valuation_points = [_valuation_point(item.target_points[point_date], target_currency) for point_date in joint_valuation_dates]
        return_points = [
            AssetReturnPoint(
                date=current.valuation_date,
                previous_valuation_date=previous.valuation_date,
                value=float(current.target_close / previous.target_close - Decimal("1")),
            )
            for previous, current in zip(
                valuation_points,
                valuation_points[1:],
                strict=False,
            )
        ]
        for index, point in enumerate(valuation_points):
            if point.is_price_carried_forward:
                carried_price_points += 1
                carried_price_asset_ids.add(item.asset_id)
            if point.is_fx_carried_forward:
                carried_fx_points += 1
                carried_fx_pairs.add(f"{point.native_currency}/{point.target_currency}")
            if index > 0 and not point.is_price_carried_forward:
                fresh_quote_points += 1
        prepared_series.append(
            PreparedAssetSeries(
                valuations=AssetValuationSeries(
                    asset_id=item.asset_id,
                    target_currency=target_currency,
                    points=valuation_points,
                    warnings=list(item.warnings),
                ),
                returns=AssetReturnSeries(
                    asset_id=item.asset_id,
                    target_currency=target_currency,
                    points=return_points,
                    warnings=list(item.warnings),
                ),
            )
        )

    n_observations = len(included_return_dates)
    final_date = included_return_dates[-1] if included_return_dates else None
    calendar_days, annualization_factor = observed_annualization(
        n_observations,
        baseline_date,
        final_date,
    )
    coverage_candidates = [point_date for point_date in candidate_quote_dates if point_date != baseline_date]
    calendar_coverage = n_observations / len(coverage_candidates) if coverage_candidates else 0.0
    fresh_quote_denominator = len(active) * n_observations
    fresh_quote_coverage = fresh_quote_points / fresh_quote_denominator if fresh_quote_denominator else 0.0

    data_quality = DataQualityReport(
        incomplete_valuation_dates=incomplete_valuation_dates,
        carried_forward_price_points=carried_price_points,
        carried_forward_fx_points=carried_fx_points,
        carried_forward_price_asset_ids=sorted(carried_price_asset_ids),
        carried_forward_fx_pairs=sorted(carried_fx_pairs),
        unresolved_fx_pairs=sorted(missing_fx_pairs),
        unusable_assets=sorted(unusable_assets, key=lambda item: item.asset_id),
        warnings=sorted(warnings),
    )
    effective_range = (
        DateRangeModel(
            start=included_return_dates[0],
            end=included_return_dates[-1],
        )
        if included_return_dates
        else None
    )
    return PreparedAssetSeriesSet(
        requested_range=requested_range,
        baseline_date=baseline_date,
        effective_range=effective_range,
        target_currency=target_currency,
        series=prepared_series,
        joint_valuation_dates=joint_valuation_dates,
        joint_return_dates=included_return_dates,
        n_observations=n_observations,
        calendar_days=calendar_days,
        annualization_factor=annualization_factor,
        calendar_coverage=calendar_coverage,
        fresh_quote_coverage=fresh_quote_coverage,
        data_quality=data_quality,
        fx_fingerprint=fx_content_fingerprint(prepared_series),
        warnings=sorted(warnings),
    )


__all__ = [
    "date_is_within_range",
    "distance_slots",
    "fx_content_fingerprint",
    "gap_slots",
    "observed_annualization",
    "prepare_asset_series_set",
]
