"""Pure sampling, Decimal precision, and technical omission helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date as Date
from decimal import ROUND_HALF_UP, Decimal, localcontext
from typing import Any

from backend.app.services.ai_export.models import SamplingSpec

ROUNDING_MODE = ROUND_HALF_UP


@dataclass(frozen=True, slots=True)
class NumericPoint:
    """Immutable observed numeric point used before snapshot DTO construction."""

    date: Date
    value: Decimal

    def __post_init__(self) -> None:
        if type(self.date) is not Date:
            raise TypeError("date must be a datetime.date")
        _require_finite_decimal(self.value)


ObservedPoint = NumericPoint


def _require_finite_decimal(value: Decimal) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError("value must be a Decimal")
    if not value.is_finite():
        raise ValueError("value must be finite")
    return value


def validate_numeric_points(points: Iterable[NumericPoint]) -> tuple[NumericPoint, ...]:
    """Freeze and validate an observed-only point sequence."""

    validated = tuple(points)
    if any(not isinstance(point, NumericPoint) for point in validated):
        raise TypeError("points must contain NumericPoint values")
    if any(current.date >= following.date for current, following in zip(validated, validated[1:], strict=False)):
        raise ValueError("point dates must be strictly increasing and unique")
    return validated


def _iso_week_last_points(points: Sequence[NumericPoint]) -> tuple[NumericPoint, ...]:
    weekly_last: dict[tuple[int, int], NumericPoint] = {}
    for point in points:
        iso_year, iso_week, _ = point.date.isocalendar()
        weekly_last[(iso_year, iso_week)] = point
    return tuple(weekly_last.values())


def _iso_week_key(point: NumericPoint) -> tuple[int, int]:
    iso_year, iso_week, _ = point.date.isocalendar()
    return iso_year, iso_week


def sample_numeric_points(points: Iterable[NumericPoint], sampling: SamplingSpec) -> tuple[NumericPoint, ...]:
    """Apply resolved-profile sampling to already sliced observed-only points."""

    if not isinstance(sampling, SamplingSpec):
        raise TypeError("sampling must be a SamplingSpec")

    observed = validate_numeric_points(points)
    if not sampling.include_series or not observed:
        return ()

    recent_count = min(sampling.recent_daily_points, len(observed))
    recent_start = len(observed) - recent_count if recent_count else len(observed)
    preceding = observed[:recent_start]
    recent = observed[recent_start:]

    if sampling.weekly_across_technical_window:
        weekly = _iso_week_last_points(observed)
    else:
        recent_weeks = {_iso_week_key(point) for point in recent}
        weekly = tuple(point for point in _iso_week_last_points(preceding) if _iso_week_key(point) not in recent_weeks)
        if sampling.preceding_weekly_points is None:
            weekly = ()
        else:
            weekly = weekly[-sampling.preceding_weekly_points :] if sampling.preceding_weekly_points else ()

    selected = {point.date: point for point in (*weekly, *recent)}
    selected[observed[0].date] = observed[0]
    selected[observed[-1].date] = observed[-1]
    return tuple(selected[point_date] for point_date in sorted(selected))


sample_observed_points = sample_numeric_points


def _quantize(value: Decimal, quantum: Decimal) -> Decimal:
    value = _require_finite_decimal(value)
    result_digits = max(1, value.adjusted() - quantum.as_tuple().exponent + 1)
    with localcontext() as context:
        context.prec = max(context.prec, len(value.as_tuple().digits), result_digits) + 4
        return value.quantize(quantum, rounding=ROUNDING_MODE)


def round_decimal_places(value: Decimal, decimal_places: int) -> Decimal:
    if isinstance(decimal_places, bool) or not isinstance(decimal_places, int):
        raise TypeError("decimal_places must be an integer")
    if decimal_places < 0:
        raise ValueError("decimal_places must be non-negative")
    return _quantize(value, Decimal(1).scaleb(-decimal_places))


def round_money(value: Decimal, minor_units: int = 2) -> Decimal:
    """Round money to currency minor units, defaulting to two."""

    return round_decimal_places(value, minor_units)


def round_asset_price(value: Decimal, max_decimal_places: int = 4) -> Decimal:
    """Keep native Asset price precision up to the configured maximum."""

    value = _require_finite_decimal(value)
    if isinstance(max_decimal_places, bool) or not isinstance(max_decimal_places, int):
        raise TypeError("max_decimal_places must be an integer")
    if max_decimal_places < 0:
        raise ValueError("max_decimal_places must be non-negative")
    if value.as_tuple().exponent >= -max_decimal_places:
        return value
    return round_decimal_places(value, max_decimal_places)


def round_fx_rate(value: Decimal) -> Decimal:
    return round_decimal_places(value, 6)


def round_percentage(value: Decimal) -> Decimal:
    return round_decimal_places(value, 2)


def round_oscillator(value: Decimal) -> Decimal:
    return round_decimal_places(value, 2)


def round_significant_digits(value: Decimal, significant_digits: int) -> Decimal:
    value = _require_finite_decimal(value)
    if isinstance(significant_digits, bool) or not isinstance(significant_digits, int):
        raise TypeError("significant_digits must be an integer")
    if significant_digits < 1:
        raise ValueError("significant_digits must be positive")
    if value.is_zero():
        return value
    quantum = Decimal(1).scaleb(value.copy_abs().adjusted() - significant_digits + 1)
    return _quantize(value, quantum)


def round_compact_volume(value: Decimal) -> Decimal:
    return round_significant_digits(value, 3)


def round_numeric_points(points: Iterable[NumericPoint], round_value: Callable[[Decimal], Decimal]) -> tuple[NumericPoint, ...]:
    """Round an already sampled point sequence without changing its dates."""

    sampled = validate_numeric_points(points)
    return tuple(NumericPoint(date=point.date, value=round_value(point.value)) for point in sampled)


def sample_and_round_numeric_points(
    points: Iterable[NumericPoint],
    sampling: SamplingSpec,
    round_value: Callable[[Decimal], Decimal],
) -> tuple[NumericPoint, ...]:
    """Make the required sampling-before-rounding order explicit."""

    return round_numeric_points(sample_numeric_points(points, sampling), round_value)


def _field(value: object, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def component_has_data(component: object) -> bool:
    """Return whether a component has latest or observed sampled data."""

    if _field(component, "latest") is not None:
        return True
    return any(bool(_field(component, key, ())) for key in ("sampled_points", "points", "series"))


def omit_empty_components[T](components: Iterable[T]) -> tuple[T, ...]:
    return tuple(component for component in components if component_has_data(component))


def omit_empty_signals(signals: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    kept: list[dict[str, Any]] = []
    for signal in signals:
        components = omit_empty_components(signal.get("components", ()))
        if not components:
            continue
        copied = dict(signal)
        copied["components"] = list(components)
        kept.append(copied)
    return tuple(kept)


def omit_empty_targets(targets: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    kept: list[dict[str, Any]] = []
    for target in targets:
        signals = omit_empty_signals(target.get("signals", ()))
        if not signals:
            continue
        copied = dict(target)
        copied["signals"] = list(signals)
        kept.append(copied)
    return tuple(kept)


def omit_empty_technical(
    domain_entity: Mapping[str, Any],
    *,
    technical_key: str = "technical",
) -> dict[str, Any]:
    """Prune empty technical branches while always retaining the domain entity."""

    result = dict(domain_entity)
    technical = result.get(technical_key)
    if technical is None:
        return result
    if not isinstance(technical, Mapping):
        raise TypeError(f"{technical_key} must be a mapping or None")

    targets = omit_empty_targets(technical.get("targets", ()))
    if not targets:
        result.pop(technical_key, None)
        return result

    copied_technical = dict(technical)
    copied_technical["targets"] = list(targets)
    result[technical_key] = copied_technical
    return result


prune_empty_technical = omit_empty_technical
