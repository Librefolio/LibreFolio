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


def prepared_scope_series(
    context: RiskExecutionContext,
) -> tuple[tuple[int, tuple[date, ...], tuple[float, ...]], ...]:
    """Return one ``(asset_id, dates, returns)`` triple per usable scope asset.

    For a scope that has no aggregate series of its own — an asset set has no
    weights, so there is no whole to reduce to — this is the counterpart of
    :func:`require_primary_returns`: it hands the analytic every series it is
    meant to describe, and nothing else.

    ⚠️ EVERY TRIPLE SHARES ONE CALENDAR, AND THAT IS NOT A COINCIDENCE.
    ``PreparedAssetSeriesSet`` validates that each series carries exactly the
    set's joint return dates, and the set is built once per request. So the
    points an analytic produces here are commensurable by construction: they are
    measured over the same days, with the same number of observations. Fanning
    the same work out across one request per asset would produce a different
    joint calendar each time and lose precisely that property.
    """
    if not context.scope_asset_ids:
        raise RiskUnavailableError(
            "No scope asset has a usable prepared return series",
            code=RiskErrorCode.DATA_UNAVAILABLE,
        )
    return tuple((asset_id, *prepared_asset_returns(context, asset_id)) for asset_id in context.scope_asset_ids)


def require_joint_baseline(context: RiskExecutionContext) -> date:
    """Return the prepared set's shared valuation baseline.

    ``primary_baseline_date`` is the baseline of a scope's own series, and a
    weightless scope has none. The joint baseline is the valuation date every
    asset's first return is measured against, which is the same thing one level
    down and is shared by all of them.
    """
    prepared = context.prepared_series
    if prepared is None or prepared.baseline_date is None or not prepared.joint_return_dates:
        raise RiskUnavailableError(
            "Prepared valuation baseline is unavailable",
            code=RiskErrorCode.DATA_UNAVAILABLE,
        )
    if prepared.baseline_date >= prepared.joint_return_dates[0]:
        raise RiskUnavailableError(
            "Prepared valuation baseline does not precede the first return",
            code=RiskErrorCode.DATA_UNAVAILABLE,
        )
    return prepared.baseline_date


def require_joint_return_dates(context: RiskExecutionContext) -> tuple[date, ...]:
    """Return the shared joint return calendar, refusing an empty one.

    A caller that indexes ``joint_return_dates[0]`` behind an ``if prepared else
    []`` fallback has written a guard its own next line contradicts: the empty
    branch can only raise ``IndexError``, which the service reports as an
    internal failure instead of a domain refusal. This states the requirement
    once, and states it as the domain error it actually is.
    """
    prepared = context.prepared_series
    if prepared is None or not prepared.joint_return_dates:
        raise RiskUnavailableError(
            "Prepared joint return calendar is unavailable",
            code=RiskErrorCode.DATA_UNAVAILABLE,
        )
    return tuple(prepared.joint_return_dates)


def joint_elapsed_calendar_days(context: RiskExecutionContext) -> tuple[int, ...]:
    """Return baseline-inclusive calendar offsets on the shared joint calendar."""
    baseline = require_joint_baseline(context)
    return (0, *((point_date - baseline).days for point_date in require_joint_return_dates(context)))


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
    "joint_elapsed_calendar_days",
    "prepared_asset_return_points",
    "prepared_asset_returns",
    "prepared_scope_series",
    "require_annualization_factor",
    "require_joint_baseline",
    "require_joint_return_dates",
    "require_primary_returns",
]
