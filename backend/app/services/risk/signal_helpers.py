"""Shared adapters from prepared risk series to signal-plugin output."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Optional

from backend.app.schemas.signals import (
    SignalAreaSeries,
    SignalAvailabilityReason,
    SignalComputation,
    SignalExecutionContext,
    SignalLineSeries,
    SignalOutputSpec,
    SignalPricePoint,
    SignalSeriesKind,
    SignalValuePoint,
    SignalWarning,
    SignalWarningCode,
)
from backend.app.services.signal_plugins.base import SignalUnavailableError


def prepared_primary_returns(
    context: SignalExecutionContext,
    price_points: Sequence[SignalPricePoint],
) -> list[float]:
    """Return prepared primary returns after checking orchestration alignment."""
    prepared = context.primary_asset_series
    if prepared is None:
        raise SignalUnavailableError(
            "Canonical prepared primary series is unavailable",
            reason_code=SignalAvailabilityReason.MISSING_PREPARED_SERIES,
        )
    valuation_dates = [point.valuation_date for point in prepared.valuations.points]
    if valuation_dates != [point.date for point in price_points]:
        raise ValueError("prepared primary valuations are not aligned to signal input")
    return [point.value for point in prepared.returns.points]


def prepared_comparison_returns(
    context: SignalExecutionContext,
    price_points: Sequence[SignalPricePoint],
) -> list[float]:
    """Return prepared comparison returns on the primary joint calendar."""
    prepared = context.comparison_asset_series
    if prepared is None:
        raise SignalUnavailableError(
            "Canonical prepared comparison series is unavailable",
            reason_code=SignalAvailabilityReason.MISSING_COMPARISON_SERIES,
        )
    valuation_dates = [point.valuation_date for point in prepared.valuations.points]
    if valuation_dates != [point.date for point in price_points]:
        raise ValueError("prepared comparison valuations are not aligned to signal input")
    return [point.value for point in prepared.returns.points]


def observed_annualization_factor(context: SignalExecutionContext) -> float:
    """Require the observed annualization factor prepared by the domain adapter."""
    factor = context.annualization_factor
    if factor is None:
        raise SignalUnavailableError(
            "Observed annualization factor is unavailable",
            reason_code=SignalAvailabilityReason.INSUFFICIENT_HISTORY,
        )
    return factor


def rolling_single_values(
    returns: Sequence[float],
    window: int,
    metric: Callable[[Sequence[float]], Optional[float]],
) -> tuple[list[Optional[float]], int]:
    """Evaluate a rolling metric and retain the initial valuation alignment."""
    values: list[Optional[float]] = [None]
    undefined_windows = 0
    for end_index in range(len(returns)):
        if end_index + 1 < window:
            values.append(None)
            continue
        value = metric(returns[end_index + 1 - window : end_index + 1])
        undefined_windows += value is None
        values.append(value)
    return values, undefined_windows


def rolling_pair_values(
    primary: Sequence[float],
    comparison: Sequence[float],
    window: int,
    metric: Callable[[Sequence[float], Sequence[float]], Optional[float]],
) -> tuple[list[Optional[float]], int]:
    """Evaluate a paired rolling metric on an already aligned joint calendar."""
    if len(primary) != len(comparison):
        raise ValueError("prepared primary and comparison returns are not aligned")
    values: list[Optional[float]] = [None]
    undefined_windows = 0
    for end_index in range(len(primary)):
        if end_index + 1 < window:
            values.append(None)
            continue
        value = metric(
            primary[end_index + 1 - window : end_index + 1],
            comparison[end_index + 1 - window : end_index + 1],
        )
        undefined_windows += value is None
        values.append(value)
    return values, undefined_windows


def undefined_window_warnings(undefined_windows: int) -> list[SignalWarning]:
    """Describe mathematically undefined rolling windows without fabricating values."""
    if not undefined_windows:
        return []
    return [
        SignalWarning(
            code=SignalWarningCode.UNDEFINED_METRIC_WINDOW,
            message="One or more rolling windows are mathematically undefined",
            details={"undefined_windows": undefined_windows},
        )
    ]


def build_line_computation(
    output_spec: SignalOutputSpec,
    price_points: Sequence[SignalPricePoint],
    values: Sequence[Optional[float]],
    *,
    warnings: Sequence[SignalWarning] = (),
) -> SignalComputation:
    """Build one line output while preserving the declared catalog contract."""
    if len(values) != len(price_points):
        raise ValueError("risk metric output must align exactly to signal input")
    if output_spec.kind not in (SignalSeriesKind.LINE, SignalSeriesKind.AREA):
        raise ValueError("build_line_computation requires a line or area output spec")
    series_type = SignalAreaSeries if output_spec.kind == SignalSeriesKind.AREA else SignalLineSeries
    return SignalComputation(
        series=[
            series_type(
                key=output_spec.key,
                label_key=output_spec.label_key,
                semantic_id=output_spec.semantic_id,
                semantic_description=output_spec.semantic_description,
                description_key=output_spec.description_key,
                unit=output_spec.unit,
                axis=output_spec.axis.model_copy(deep=True),
                view_transform=output_spec.view_transform,
                style=output_spec.style.model_copy(deep=True),
                points=[SignalValuePoint(date=point.date, value=value) for point, value in zip(price_points, values, strict=True)],
                reference_levels=[level.model_copy(deep=True) for level in output_spec.default_reference_levels],
                value_regions=[region.model_copy(deep=True) for region in output_spec.default_value_regions],
            )
        ],
        warnings=list(warnings),
    )


__all__ = [
    "build_line_computation",
    "observed_annualization_factor",
    "prepared_comparison_returns",
    "prepared_primary_returns",
    "rolling_pair_values",
    "rolling_single_values",
    "undefined_window_warnings",
]
