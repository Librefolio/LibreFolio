"""Shared pure extraction helpers for RiskAnalytic plugins."""

from __future__ import annotations

from datetime import date

from backend.app.schemas.risk import RiskErrorCode
from backend.app.services.risk.base import RiskExecutionContext, RiskUnavailableError


def prepared_asset_returns(
    context: RiskExecutionContext,
    asset_id: int,
) -> tuple[tuple[date, ...], tuple[float, ...]]:
    """Extract one canonical return series from the shared prepared set."""
    if context.prepared_series is None:
        raise RiskUnavailableError(
            "Prepared asset returns are unavailable",
            code=RiskErrorCode.DATA_UNAVAILABLE,
        )
    for item in context.prepared_series.series:
        if item.returns.asset_id == asset_id:
            return (
                tuple(point.date for point in item.returns.points),
                tuple(float(point.value) for point in item.returns.points),
            )
    raise RiskUnavailableError(
        f"Asset {asset_id} has no usable prepared return series",
        code=RiskErrorCode.DATA_UNAVAILABLE,
        details={"asset_id": asset_id},
    )


def prepared_asset_return_points(
    context: RiskExecutionContext,
    asset_id: int,
) -> tuple[tuple[date, date, float], ...]:
    """Return date, previous valuation date, and value for one asset."""
    if context.prepared_series is None:
        raise RiskUnavailableError(
            "Prepared asset returns are unavailable",
            code=RiskErrorCode.DATA_UNAVAILABLE,
        )
    for item in context.prepared_series.series:
        if item.returns.asset_id == asset_id:
            return tuple(
                (
                    point.date,
                    point.previous_valuation_date,
                    float(point.value),
                )
                for point in item.returns.points
            )
    raise RiskUnavailableError(
        f"Asset {asset_id} has no usable prepared return series",
        code=RiskErrorCode.DATA_UNAVAILABLE,
        details={"asset_id": asset_id},
    )


def require_primary_returns(
    context: RiskExecutionContext,
) -> tuple[tuple[date, ...], tuple[float, ...]]:
    """Return the primary scope series or raise a domain unavailability."""
    if not context.primary_returns or len(context.primary_return_dates) != len(context.primary_returns):
        raise RiskUnavailableError(
            "Primary return series is unavailable",
            code=RiskErrorCode.DATA_UNAVAILABLE,
        )
    return context.primary_return_dates, context.primary_returns


def require_annualization_factor(context: RiskExecutionContext) -> float:
    """Return the observed factor required by annualized metrics."""
    if context.annualization_factor is None or context.annualization_factor <= 0:
        raise RiskUnavailableError(
            "Observed annualization factor is unavailable",
            code=RiskErrorCode.INSUFFICIENT_HISTORY,
        )
    return context.annualization_factor


def elapsed_calendar_days(context: RiskExecutionContext) -> tuple[int, ...]:
    """Return baseline-inclusive calendar offsets for drawdown duration."""
    dates, _returns = require_primary_returns(context)
    baseline = context.primary_baseline_date
    if baseline is None or baseline >= dates[0]:
        raise RiskUnavailableError(
            "Primary return baseline is unavailable",
            code=RiskErrorCode.DATA_UNAVAILABLE,
        )
    return (0, *((point_date - baseline).days for point_date in dates))


__all__ = [
    "elapsed_calendar_days",
    "prepared_asset_return_points",
    "prepared_asset_returns",
    "require_annualization_factor",
    "require_primary_returns",
]
