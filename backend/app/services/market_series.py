"""Pure date and series-preparation primitives shared across analytics."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Protocol

from backend.app.schemas.common import Currency, DateRangeModel, DateSpan
from backend.app.schemas.portfolio import (
    DataQualityExcludedAsset,
    DataQualityExclusionReason,
    DataQualityReport,
)
from backend.app.schemas.prices import AssetBackwardFillInfo, FAPricePoint, FAPriceQueryResult
from backend.app.schemas.risk import (
    AssetReturnPoint,
    AssetReturnSeries,
    AssetValuationPoint,
    AssetValuationSeries,
    PreparedAssetSeries,
    PreparedAssetSeriesSet,
)
from backend.app.services.assets.market_calendar import is_market_closed_repeat
from backend.app.services.financial_math.returns import float_price_return, observed_annualization
from backend.app.services.financial_math.series_steps import merged_spans
from backend.app.services.platform.data_quality_thresholds import STALE_PRICE_THRESHOLD_DAYS


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
    quote_dates: tuple[date, ...] = ()


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


def mark_market_closed_carries(points: dict[date, FAPricePoint], market_holidays: AbstractSet[date]) -> dict[date, FAPricePoint]:
    """Turn every stored carry into a carried point (developer's decision of 30/09/2026).

    A stored row dated on a weekend or a market holiday whose native close repeats the row before it
    is not a quote: its date must not enter the calendar as an observation, and where another asset's
    quote puts that date in the calendar anyway, this asset's value there is carried from its last
    quote. See `market_calendar`.
    """
    marked: dict[date, FAPricePoint] = {}
    previous: FAPricePoint | None = None
    previous_effective: date | None = None
    for point_date, point in points.items():
        stored = point
        if (
            _price_is_fresh(point)
            and previous is not None
            and previous_effective is not None
            and (previous.original_currency or previous.currency) == (point.original_currency or point.currency)
            and is_market_closed_repeat(
                point_date,
                point.original_close if point.original_close is not None else point.close,
                previous.original_close if previous.original_close is not None else previous.close,
                market_holidays,
            )
        ):
            info = point.backward_fill_info
            carried = AssetBackwardFillInfo(
                actual_rate_date=previous_effective,
                days_back=(point_date - previous_effective).days,
                fx_rate_date=info.fx_rate_date if info is not None else None,
                fx_days_back=info.fx_days_back if info is not None else None,
            )
            point = point.model_copy(update={"backward_fill_info": carried})
        info = point.backward_fill_info
        previous_effective = info.actual_rate_date if info is not None and info.days_back else point_date
        previous = stored
        marked[point_date] = point
    return marked


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


def prepare_asset_series_set(  # noqa: C901 — sequential pipeline stages with early-return special cases
    price_results: Sequence[FAPriceQueryResult],
    *,
    requested_range: DateRangeModel,
    target_currency: str,
    market_holidays: AbstractSet[date] = frozenset(),
) -> PreparedAssetSeriesSet:
    """Build one converted-price joint calendar, then derive simple returns.

    A stored carry — a weekend or `market_holidays` row repeating the close before it — is read as a
    carried point, not a quote (see `market_calendar`); weekends apply even with no holiday table.
    """
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
        all_points = mark_market_closed_carries(_indexed_points(result, requested_end), market_holidays)
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
                quote_dates=tuple(point_date for point_date, point in target_points.items() if requested_range.start <= point_date <= requested_end and _price_is_fresh(point)),
            )
        )

    return _prepare_from_inputs(
        active,
        unusable_assets,
        warnings,
        missing_fx_pairs,
        requested_range=requested_range,
        requested_end=requested_end,
        target_currency=target_currency,
    )


class AssetPriceReading(Protocol):
    """What the price query answers for one asset when only its observations are read (``assets.observed_prices.ObservedPrices``).

    ``point_on(day)`` is the point the dense series has on ``day``: the close of the last observation up to it, converted at
    that day's rate, with the same ``backward_fill_info``; None before the first point. While the asset has no rate the
    point is in its own currency (not the target's). ``first_point_date`` is the first day with a point, in any currency,
    ``observation_dates`` the days of its stored rows inside the window read.
    """

    asset_id: int
    errors: Sequence[str]
    first_point_date: date | None
    observation_dates: Sequence[date]

    def point_on(self, day: date) -> FAPricePoint | None: ...


def _first_converted_day(reading: AssetPriceReading, target_currency: str, end: date) -> date | None:
    """The first day the asset has a point in the target currency: its series has none before its rate starts, so the days
    without a point in the target run from ``first_point_date`` up to the day before it. None when it never has one."""
    first = reading.first_point_date
    if first is None or first > end:
        return None
    last = reading.point_on(end)
    if last is None or last.currency != target_currency:
        return None
    low, high = first, end
    while low < high:
        middle = low + (high - low) // 2
        point = reading.point_on(middle)
        if point is not None and point.currency == target_currency:
            high = middle
        else:
            low = middle + timedelta(days=1)
    return low


def prepare_asset_series_set_from_readings(  # noqa: C901 — one pass per stage: stored rows, usable assets, the days the preparation needs
    readings: Sequence[AssetPriceReading],
    *,
    requested_range: DateRangeModel,
    target_currency: str,
    market_holidays: AbstractSet[date] = frozenset(),
) -> PreparedAssetSeriesSet:
    """``prepare_asset_series_set`` without a point for every calendar day: the same ``PreparedAssetSeriesSet``.

    The risk reads ``[start - 1, end]`` and the dense series gives one point a day, but the preparation uses only a few: the
    baseline day, the days some asset quotes, each asset's first day with a rate, and the stored rows with the day before
    each (the chain that reads a repeated close as a carry). Those are the only points built here, from each reading's
    ``point_on``; everything after is the dense preparation (``_prepare_from_inputs``).
    """
    target_currency = Currency.validate_code(target_currency)
    requested_end = requested_range.end or requested_range.start
    asset_ids = [reading.asset_id for reading in readings]
    if len(asset_ids) != len(set(asset_ids)):
        raise ValueError("price_results must contain unique asset IDs")
    load_start = requested_range.start - timedelta(days=1) if requested_range.start > date.min else requested_range.start

    warnings: set[str] = set()
    missing_fx_pairs: set[str] = set()
    unusable_assets: list[DataQualityExcludedAsset] = []
    stored_by_asset: dict[int, dict[date, FAPricePoint]] = {}
    first_converted_by_asset: dict[int, date] = {}
    usable: list[AssetPriceReading] = []
    for reading in readings:
        observed = sorted({day for day in reading.observation_dates if load_start <= day <= requested_end})
        wanted = set(observed) | {day - timedelta(days=1) for day in observed if day > load_start}
        stored = {day: point for day in sorted(wanted) if (point := reading.point_on(day)) is not None}
        marked = mark_market_closed_carries(stored, market_holidays)
        warnings.update(reading.errors)
        # A day of the range on which the asset has a point that is not in the target currency: its rate is missing until
        # it starts, so the days run from the first row to the day before its first converted point.
        probes = [requested_range.start, *observed[:1]] if requested_range.start <= requested_end else []
        for probe in probes:
            point = reading.point_on(probe) if requested_range.start <= probe <= requested_end else None
            if point is not None and point.currency is not None and point.currency != target_currency:
                missing_fx_pairs.add(f"{point.currency}/{target_currency}")
        first_converted = _first_converted_day(reading, target_currency, requested_end)
        if first_converted is None:
            last = reading.point_on(requested_end)
            if last is None:
                reason = DataQualityExclusionReason.MISSING_PRICE
            elif last.currency is None:
                reason = DataQualityExclusionReason.INVALID_CURRENCY
            elif last.currency != target_currency:
                reason = DataQualityExclusionReason.MISSING_FX
            else:
                reason = DataQualityExclusionReason.MISSING_PRICE
            unusable_assets.append(DataQualityExcludedAsset(asset_id=reading.asset_id, reason=reason))
            if reason == DataQualityExclusionReason.MISSING_FX:
                warnings.add(f"missing_fx:{reading.asset_id}")
            continue
        stored_by_asset[reading.asset_id] = marked
        first_converted_by_asset[reading.asset_id] = first_converted
        usable.append(reading)

    # The days the preparation reads a point on, besides the stored rows: the baseline candidate (the day before the range),
    # every day some asset quotes, and the day each asset gets its first converted point (the first day all of them have one).
    needed = {load_start}
    for reading in usable:
        needed.update(day for day, point in stored_by_asset[reading.asset_id].items() if requested_range.start <= day <= requested_end and _price_is_fresh(point))
    needed.update(max(requested_range.start, first_converted_by_asset[reading.asset_id]) for reading in usable)

    active: list[_AssetSeriesInput] = []
    for reading in usable:
        all_points = dict(stored_by_asset[reading.asset_id])
        for day in sorted(needed - set(all_points)):
            point = reading.point_on(day) if day <= requested_end else None
            if point is not None:
                all_points[day] = point
        all_points = dict(sorted(all_points.items()))
        target_points = {day: point for day, point in all_points.items() if point.currency == target_currency}
        active.append(
            _AssetSeriesInput(
                asset_id=reading.asset_id,
                all_points=all_points,
                target_points=target_points,
                warnings=tuple(reading.errors),
                quote_dates=tuple(day for day, point in target_points.items() if requested_range.start <= day <= requested_end and _price_is_fresh(point)),
            )
        )
    return _prepare_from_inputs(
        active,
        unusable_assets,
        warnings,
        missing_fx_pairs,
        requested_range=requested_range,
        requested_end=requested_end,
        target_currency=target_currency,
    )


def _prepare_from_inputs(  # noqa: C901 — sequential pipeline stages with early-return special cases
    active: list[_AssetSeriesInput],
    unusable_assets: list[DataQualityExcludedAsset],
    warnings: set[str],
    missing_fx_pairs: set[str],
    *,
    requested_range: DateRangeModel,
    requested_end: date,
    target_currency: str,
) -> PreparedAssetSeriesSet:
    """The joint calendar, the returns and the data quality of the assets that have a usable series.

    The stage both entry points share: one from the dense points of the price query, one from readings that hold only
    the observations. It reads, per asset, its marked points (``all_points``), those in the target currency
    (``target_points``) and its fresh quote days, and nothing between the days it needs.
    """
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
                quote_dates=list(item.quote_dates),
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
        # TODO(total return): these returns are price-only, so coupons and dividends never enter,
        # and an income-paying asset (a coupon bond) reads below its total return. The developer's
        # direction (05/10/2026): add the recorded income where its transactions exist, with the
        # price as the fallback and the basis declared per asset.
        return_points = [
            AssetReturnPoint(
                date=current.valuation_date,
                previous_valuation_date=previous.valuation_date,
                value=float_price_return(previous.target_close, current.target_close),
            )
            for previous, current in zip(
                valuation_points,
                valuation_points[1:],
                strict=False,
            )
        ]
        # A carried-forward price or rate is a data-quality problem only once it is older than
        # the project's staleness threshold: weekends, holidays and an instrument quoted on its
        # own market calendar are ordinary and must not degrade a result on their own
        # (developer's decision of 24/09/2026). The baseline is a reference, not an
        # observation, so it never counts — the same rule `fresh_quote_points` applies.
        for index, point in enumerate(valuation_points):
            if index == 0:
                continue
            if point.is_price_carried_forward and (point.valuation_date - point.effective_price_date).days > STALE_PRICE_THRESHOLD_DAYS:
                carried_price_points += 1
                carried_price_asset_ids.add(item.asset_id)
            if point.is_fx_carried_forward and point.fx_rate_date is not None and (point.valuation_date - point.fx_rate_date).days > STALE_PRICE_THRESHOLD_DAYS:
                carried_fx_points += 1
                carried_fx_pairs.add(f"{point.native_currency}/{point.target_currency}")
            if not point.is_price_carried_forward:
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
                quote_dates=list(item.quote_dates),
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
        incomplete_valuation_ranges=[DateSpan(start=first, end=last) for first, last in merged_spans((day, day) for day in incomplete_valuation_dates)],
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
    "mark_market_closed_carries",
    "prepare_asset_series_set",
    "prepare_asset_series_set_from_readings",
]
