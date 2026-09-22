"""Shared adapters from prepared risk series to signal-plugin output."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from typing import Optional

import numpy as np
import pandas as pd

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
from backend.app.services.risk.metrics import ZERO_TOLERANCE, daily_risk_free_rate
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
    """Evaluate a rolling metric and retain the initial valuation alignment.

    Kept after the vectorised helpers landed, deliberately. This loop is metric-agnostic
    and therefore cannot itself be vectorised — handing an arbitrary ``Callable`` to
    ``rolling().apply()`` leaves it interpreted. Its value now is as the **executable
    reference semantics**: the oracle drives the vectorised helpers and this loop over
    the same samples and asserts both the values and the undefined count agree. Delete
    it and the migration loses the only thing that proves it did not change behaviour.
    """
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
    """Evaluate a paired rolling metric on an already aligned joint calendar.

    Reference semantics for :func:`rolling_beta_values`; see :func:`rolling_single_values`.
    """
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


def _assemble_rolling_values(
    computed: np.ndarray,
    undefined: np.ndarray,
    window: int,
    observations: int,
) -> tuple[list[Optional[float]], int]:
    """Translate a vectorised result back into the ``(values, undefined_windows)`` contract.

    Three things happen here, and all three are the reason M1 is not a one-line swap.

    1. The leading ``None`` re-establishes the valuation baseline, so the output is
       one entry longer than the return series and aligns to the price points.
    2. Warm-up is decided **by index**, never by looking at the value. ``rolling``
       emits ``NaN`` both for a window that does not exist yet and for a window whose
       statistic is undefined; the two are the same float and cannot be told apart
       afterwards. Positions before ``window - 1`` are warm-up by construction.
    3. Only genuinely undefined full windows are counted, because that count drives a
       user-visible warning.
    """
    if observations < window:
        return [None] * (observations + 1), 0

    values: list[Optional[float]] = [None] * window
    undefined_windows = 0
    for index in range(window - 1, observations):
        if bool(undefined[index]):
            values.append(None)
            undefined_windows += 1
        else:
            values.append(float(computed[index]))
    return values, undefined_windows


def _require_dispersion_window(window: int) -> None:
    """Reject a window too narrow for a ``ddof=1`` statistic, exactly as the loop does.

    The scalar path reaches ``sample_variance``, which refuses a single observation. The
    vectorised path would instead reach pandas, whose ``calc_var`` needs ``nobs > ddof``
    and answers ``NaN`` — and ``NaN`` is not what the undefined test inspects, because
    that test correctly looks at the denominator. Every cell would therefore be published
    as a value, with an undefined count of zero, and the ``NaN`` would only surface much
    later as a Pydantic failure against ``SignalValuePoint.value`` (``FiniteFloat``).
    Raising here keeps the two paths on the same behaviour and the error at the cause.
    """
    if window < 2:
        raise ValueError("sample variance requires at least two observations")


def rolling_compounded_return_values(
    returns: Sequence[float],
    window: int,
    *,
    scale: float = 1.0,
) -> tuple[list[Optional[float]], int]:
    """Compound simple returns inside each rolling window, vectorised.

    Uses ``expm1(log1p(r).rolling(w).sum())`` rather than a rolling product. A rolling
    ``apply(prod)`` would stay interpreted and defeat the migration, and a cumulative
    product divided by its own lag propagates ``nan`` forever once a window contains a
    total loss. The log form degrades gracefully instead.

    Never undefined: compounding is defined for every finite window, so the returned
    count is always zero.

    Rejects a return of exactly ``-1`` where the scalar metric tolerates it. A total loss
    is ``log1p(-1) == -inf``, and a rolling accumulator that adds then removes ``-inf``
    is left with ``NaN`` for every later window, so the damage would outlive the window
    that caused it. ``AssetReturnPoint.value`` is already declared ``gt=-1``, so the
    narrowing is unobservable on prepared series and only guards direct callers.
    """
    observations = len(returns)
    if observations < window:
        return [None] * (observations + 1), 0
    series = pd.Series(returns, dtype="float64")
    sample = series.to_numpy()
    if not np.all(np.isfinite(sample)) or np.any(sample <= -1.0):
        raise ValueError("simple returns must be finite and greater than -1")
    compounded = np.expm1(np.log1p(series).rolling(window).sum()) * scale
    return _assemble_rolling_values(
        compounded.to_numpy(),
        np.zeros(observations, dtype=bool),
        window,
        observations,
    )


def rolling_annualized_volatility_values(
    returns: Sequence[float],
    window: int,
    annualization_factor: float,
    *,
    scale: float = 1.0,
) -> tuple[list[Optional[float]], int]:
    """Annualize rolling sample volatility (``ddof=1``), vectorised.

    Never undefined: a zero-dispersion window has zero volatility, which is a perfectly
    defined answer. Only ratios that divide by it become undefined.
    """
    observations = len(returns)
    if observations < window:
        return [None] * (observations + 1), 0
    _require_dispersion_window(window)
    factor = float(annualization_factor)
    if factor <= 0 or not math.isfinite(factor):
        raise ValueError("annualization_factor must be finite and positive")
    series = pd.Series(returns, dtype="float64")
    volatility = series.rolling(window).std(ddof=1) * math.sqrt(factor) * scale
    return _assemble_rolling_values(
        volatility.to_numpy(),
        np.zeros(observations, dtype=bool),
        window,
        observations,
    )


def rolling_annualized_sharpe_values(
    returns: Sequence[float],
    window: int,
    annualization_factor: float,
    *,
    annual_risk_free_rate: float = 0.0,
) -> tuple[list[Optional[float]], int]:
    """Annualize the rolling Sharpe ratio, vectorised, preserving the undefined windows.

    The undefined test is applied to the rolling standard deviation with the same
    absolute tolerance the scalar metric uses, so the two paths place the boundary in
    exactly the same spot. Reading the output ``NaN`` instead would conflate warm-up
    with undefined and silently drop a user-visible warning.
    """
    observations = len(returns)
    if observations < window:
        return [None] * (observations + 1), 0
    _require_dispersion_window(window)
    factor = float(annualization_factor)
    if factor <= 0 or not math.isfinite(factor):
        raise ValueError("annualization_factor must be finite and positive")
    period_risk_free_rate = daily_risk_free_rate(annual_risk_free_rate, factor)
    series = pd.Series(returns, dtype="float64")
    deviation = series.rolling(window).std(ddof=1)
    excess_mean = (series - period_risk_free_rate).rolling(window).mean()
    sharpe = excess_mean / deviation * math.sqrt(factor)
    undefined = np.abs(deviation.to_numpy()) <= ZERO_TOLERANCE
    return _assemble_rolling_values(sharpe.to_numpy(), undefined, window, observations)


def rolling_beta_values(
    primary: Sequence[float],
    comparison: Sequence[float],
    window: int,
) -> tuple[list[Optional[float]], int]:
    """Compute rolling sample beta on an aligned joint calendar, vectorised.

    Undefined exactly where the scalar metric is: when the comparison variance
    vanishes. The test is on the variance, matching the scalar tolerance, not on the
    resulting ``NaN``.
    """
    if len(primary) != len(comparison):
        raise ValueError("prepared primary and comparison returns are not aligned")
    observations = len(primary)
    if observations < window:
        return [None] * (observations + 1), 0
    _require_dispersion_window(window)
    primary_series = pd.Series(primary, dtype="float64")
    comparison_series = pd.Series(comparison, dtype="float64")
    comparison_variance = comparison_series.rolling(window).var(ddof=1)
    covariance = primary_series.rolling(window).cov(comparison_series, ddof=1)
    values = covariance / comparison_variance
    undefined = np.abs(comparison_variance.to_numpy()) <= ZERO_TOLERANCE
    return _assemble_rolling_values(values.to_numpy(), undefined, window, observations)


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
    "rolling_annualized_sharpe_values",
    "rolling_annualized_volatility_values",
    "rolling_beta_values",
    "rolling_compounded_return_values",
    "rolling_pair_values",
    "rolling_single_values",
    "undefined_window_warnings",
]
