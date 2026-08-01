"""Pure normalized-return, valuation-reference, and relative-metric helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date as Date
from decimal import Decimal, localcontext

from backend.app.schemas.ai_export import (
    AiExportNormalizedReturn,
    AiExportNormalizedReturnBaseSource,
    AiExportNormalizedReturnPoint,
    AiExportValuationReference,
    AiExportValuationReferenceSource,
)
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.services.ai_export.models import SamplingSpec
from backend.app.services.ai_export.sampling import NumericPoint, round_percentage, sample_numeric_points

ONE = Decimal("1")
HUNDRED = Decimal("100")
SourceRoundingPolicy = Callable[[Decimal], Decimal]


def _require_finite_decimal(value: Decimal, name: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be a Decimal")
    if not value.is_finite():
        raise ValueError(f"{name} must be finite")
    return value


def _require_positive_decimal(value: Decimal, name: str) -> Decimal:
    value = _require_finite_decimal(value, name)
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _require_date(value: Date, name: str) -> Date:
    if type(value) is not Date:
        raise TypeError(f"{name} must be a datetime.date")
    return value


@dataclass(frozen=True, slots=True)
class ObservedSourcePoint:
    """Immutable observed source value before normalization or sampling."""

    date: Date
    source_value: Decimal

    def __post_init__(self) -> None:
        _require_date(self.date, "date")
        _require_positive_decimal(self.source_value, "source_value")


def _as_source_point(point: ObservedSourcePoint | NumericPoint) -> ObservedSourcePoint:
    if isinstance(point, ObservedSourcePoint):
        return point
    if isinstance(point, NumericPoint):
        return ObservedSourcePoint(date=point.date, source_value=point.value)
    raise TypeError("observed_history must contain ObservedSourcePoint or NumericPoint values")


def _validate_observed_history(points: Iterable[ObservedSourcePoint | NumericPoint]) -> tuple[ObservedSourcePoint, ...]:
    observed = tuple(_as_source_point(point) for point in points)
    if any(current.date >= following.date for current, following in zip(observed, observed[1:], strict=False)):
        raise ValueError("observed point dates must be strictly increasing and unique")
    return observed


def _requested_range_with_end(requested_range: DateRangeModel) -> DateRangeModel:
    if not isinstance(requested_range, DateRangeModel):
        raise TypeError("requested_range must be a DateRangeModel")
    return DateRangeModel(start=requested_range.start, end=requested_range.end or requested_range.start)


def _calculation_precision(*values: Decimal) -> int:
    highest_digit = max(value.adjusted() for value in values)
    lowest_digit = min(value.as_tuple().exponent for value in values)
    return max(34, highest_digit - lowest_digit + 17)


def _relative_pct(value: Decimal, reference: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = max(context.prec, _calculation_precision(value, reference))
        result = (value / reference - ONE) * HUNDRED
    return _require_finite_decimal(result, "percentage result")


def _bounded_pct(value: Decimal, lower: Decimal, upper: Decimal) -> Decimal | None:
    with localcontext() as context:
        context.prec = max(context.prec, _calculation_precision(value, lower, upper))
        denominator = upper - lower
        if denominator <= 0:
            return None
        result = ((value - lower) / denominator) * HUNDRED
    return _require_finite_decimal(result, "percentage result")


def build_normalized_return(
    observed_history: Iterable[ObservedSourcePoint | NumericPoint],
    requested_range: DateRangeModel,
    sampling: SamplingSpec,
    *,
    source_currency: str | None = None,
    source_rounding: SourceRoundingPolicy,
) -> AiExportNormalizedReturn | None:
    """Build an observed-only normalized-return series for an inclusive range."""

    requested = _requested_range_with_end(requested_range)
    if not isinstance(sampling, SamplingSpec):
        raise TypeError("sampling must be a SamplingSpec")
    if not callable(source_rounding):
        raise TypeError("source_rounding must be callable")

    normalized_currency = Currency.validate_code(source_currency) if source_currency is not None else None
    observed = _validate_observed_history(observed_history)
    in_window = tuple(point for point in observed if requested.start <= point.date <= requested.end)
    if not in_window or not sampling.include_series:
        return None

    base = in_window[0]
    exact_start = base.date == requested.start
    base_source = AiExportNormalizedReturnBaseSource.OBSERVED_MARKET_PRICE if exact_start else AiExportNormalizedReturnBaseSource.FIRST_OBSERVED_MARKET_PRICE_IN_WINDOW
    window_complete = exact_start or any(point.date < requested.start for point in observed)

    raw_by_date: dict[Date, tuple[Decimal, Decimal]] = {}
    raw_return_points: list[NumericPoint] = []
    for point in in_window:
        raw_return = _relative_pct(point.source_value, base.source_value)
        raw_by_date[point.date] = (point.source_value, raw_return)
        raw_return_points.append(NumericPoint(date=point.date, value=raw_return))

    sampled = sample_numeric_points(raw_return_points, sampling)
    if not sampled:
        return None
    if sampled[0].date != base.date or sampled[-1].date != in_window[-1].date:
        raise RuntimeError("sampling must retain normalized-return base and last point")

    points: list[AiExportNormalizedReturnPoint] = []
    for sampled_point in sampled:
        raw_source, raw_return = raw_by_date[sampled_point.date]
        rounded_source = _require_positive_decimal(source_rounding(raw_source), "rounded source_value")
        points.append(
            AiExportNormalizedReturnPoint(
                date=sampled_point.date,
                source_value=rounded_source,
                return_from_base_pct=round_percentage(raw_return),
            )
        )

    return AiExportNormalizedReturn(
        requested_range=requested,
        base_date=base.date,
        base_source=base_source,
        base_value=points[0].source_value,
        source_currency=normalized_currency,
        window_complete=window_complete,
        points=points,
    )


def _build_valuation_reference(
    date: Date,
    unit_price: Decimal,
    currency: str,
    source: AiExportValuationReferenceSource,
    *,
    effective_unit_price: Decimal | None = None,
    effective_currency: str | None = None,
    split_adjusted: bool = False,
) -> AiExportValuationReference:
    _require_date(date, "date")
    unit_price = _require_positive_decimal(unit_price, "unit_price")
    currency_code = Currency.validate_code(currency)
    effective_price_value: Currency | None = None
    if effective_currency is not None and effective_unit_price is None:
        raise ValueError("effective_currency requires effective_unit_price")
    if effective_unit_price is not None:
        effective_unit_price = _require_positive_decimal(effective_unit_price, "effective_unit_price")
        effective_currency_code = Currency.validate_code(effective_currency if effective_currency is not None else currency_code)
        effective_price_value = Currency(code=effective_currency_code, amount=effective_unit_price)
    if split_adjusted and effective_price_value is None:
        raise ValueError("split_adjusted requires effective_unit_price")
    semantics = "valuation_fallback_not_observed_market_return"
    return AiExportValuationReference(
        date=date,
        source=source,
        unit_price=Currency(code=currency_code, amount=unit_price),
        effective_unit_price=effective_price_value,
        split_adjusted=split_adjusted,
        semantics=semantics,
    )


def build_last_observed_trade_valuation_reference(
    date: Date,
    unit_price: Decimal,
    currency: str,
    *,
    effective_unit_price: Decimal | None = None,
    effective_currency: str | None = None,
    split_adjusted: bool = False,
) -> AiExportValuationReference:
    """Build a last-observed-trade valuation reference (a real BUY/SELL/ADJUSTMENT price carried forward), never a return series."""

    return _build_valuation_reference(
        date,
        unit_price,
        currency,
        AiExportValuationReferenceSource.LAST_OBSERVED_TRADE_PRICE,
        effective_unit_price=effective_unit_price,
        effective_currency=effective_currency,
        split_adjusted=split_adjusted,
    )


def relative_distance_pct(value: Decimal, reference: Decimal) -> Decimal | None:
    """Return relative distance from reference in percentage points."""

    value = _require_finite_decimal(value, "value")
    reference = _require_finite_decimal(reference, "reference")
    if reference.is_zero():
        return None
    return _relative_pct(value, reference)


def bounded_position_pct(value: Decimal, lower: Decimal, upper: Decimal) -> Decimal | None:
    """Return value position between ordered Donchian bounds in percentage points."""

    value = _require_finite_decimal(value, "value")
    lower = _require_finite_decimal(lower, "lower")
    upper = _require_finite_decimal(upper, "upper")
    return _bounded_pct(value, lower, upper)


def bollinger_percent_b(value: Decimal, lower: Decimal, upper: Decimal) -> Decimal | None:
    """Return Bollinger %B in percentage points using ordered band bounds."""

    value = _require_finite_decimal(value, "value")
    lower = _require_finite_decimal(lower, "lower")
    upper = _require_finite_decimal(upper, "upper")
    return _bounded_pct(value, lower, upper)
