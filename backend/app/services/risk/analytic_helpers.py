"""Shared pure extraction helpers for RiskAnalytic plugins."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date

from backend.app.schemas.risk.outputs import RiskWorstHorizonWindow
from backend.app.schemas.risk.results import RiskWarning
from backend.app.schemas.risk.vocabulary import RiskErrorCode
from backend.app.services.risk.acquired import average_drawdown
from backend.app.services.risk.base import RiskExecutionContext, RiskUnavailableError
from backend.app.services.risk.metrics import HorizonWindow, ReturnShape, largest_rally, wealth_index


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


def dated_horizon_window(window: HorizonWindow | None, dates: Sequence[date]) -> RiskWorstHorizonWindow | None:
    """A worst or best compounded window on the wire, its positions turned into the dates of ``dates`` (the returns')."""
    if window is None:
        return None
    return RiskWorstHorizonWindow(compounded_return=window.compounded_return, start_date=dates[window.start_index], end_date=dates[window.end_index])


def rally_and_depth_fields(returns: Sequence[float], drawdowns: Sequence[float], *, baseline_date: date, dates: Sequence[date]) -> dict[str, object]:
    """RN-14, the twins of a drawdown episode: the largest rally, dated, and «below the peak, on average» (ADD).

    ``drawdowns`` is the baseline-inclusive underwater curve of the same ``returns``; the rally's positions are in the
    wealth index, whose first value sits on ``baseline_date``. No rise is no rally: a zero with no dates.
    """
    rally = largest_rally(wealth_index(returns))
    fields: dict[str, object] = {"average_drawdown": average_drawdown(drawdowns)}
    if rally.trough_index is None or rally.peak_index is None:
        return {**fields, "largest_rally": 0.0, "largest_rally_start_date": None, "largest_rally_end_date": None, "largest_rally_duration_days": 0}
    wealth_dates = (baseline_date, *dates)
    start, end = wealth_dates[rally.trough_index], wealth_dates[rally.peak_index]
    return {**fields, "largest_rally": rally.gain, "largest_rally_start_date": start, "largest_rally_end_date": end, "largest_rally_duration_days": (end - start).days}


# RN-14 — why a measure of the shape of the days is null, one condition per code (Q20: «—» with its reason). Each key
# is spelled out where the warning is built: the i18n gate reads it there (test_risk_warnings_i18n.py).
# None degrades the result (consultant, 16/11/2026): «partial» says the data are incomplete, and a series that never
# gained, never lost or never moved is complete — only made so. Its «—» carries the reason; every other figure stands.
def _undefined_return_shape(shape: ReturnShape) -> dict[str, bool]:
    return {
        "best_realization_undefined": shape.best_realization is None,
        "average_loss_undefined": shape.mean_negative_return is None,
        "omega_undefined": shape.omega_ratio is None,
        "extreme_day_ratio_undefined": shape.extreme_day_ratio is None,
    }


def return_shape_warnings(shape: ReturnShape) -> list[RiskWarning]:
    """The warnings of one series whose shape left a measure null."""
    undefined = _undefined_return_shape(shape)
    warnings: list[RiskWarning] = []
    if undefined["best_realization_undefined"]:
        warnings.append(RiskWarning(degrades_result=False, code="best_realization_undefined", message_i18n_key="risk.warnings.best_realization_undefined", message="No gaining observation in the selected window: no best day, average up day or positive streak."))
    if undefined["average_loss_undefined"]:
        warnings.append(RiskWarning(degrades_result=False, code="average_loss_undefined", message_i18n_key="risk.warnings.average_loss_undefined", message="No losing observation in the selected window: no average down day."))
    if undefined["omega_undefined"]:
        warnings.append(RiskWarning(degrades_result=False, code="omega_undefined", message_i18n_key="risk.warnings.omega_undefined", message="Gains against losses is undefined because no observation fell below the target return."))
    if undefined["extreme_day_ratio_undefined"]:
        warnings.append(RiskWarning(degrades_result=False, code="extreme_day_ratio_undefined", message_i18n_key="risk.warnings.extreme_day_ratio_undefined", message="The extreme-day ratio is undefined because the series does not move."))
    return warnings


def return_shape_set_warnings(shapes: Mapping[int, ReturnShape]) -> list[RiskWarning]:
    """One warning per condition naming the assets it is about, in the order of ``shapes``."""
    named: dict[str, list[int]] = {}
    for asset_id, shape in shapes.items():
        for code, missing in _undefined_return_shape(shape).items():
            if missing:
                named.setdefault(code, []).append(asset_id)
    warnings: list[RiskWarning] = []
    if "best_realization_undefined" in named:
        warnings.append(
            RiskWarning(degrades_result=False, code="best_realization_undefined", message_i18n_key="risk.warnings.best_realization_undefined_assets", message="One or more assets had no gaining observation in the selected window.", details={"asset_ids": named["best_realization_undefined"]})
        )
    if "average_loss_undefined" in named:
        warnings.append(RiskWarning(degrades_result=False, code="average_loss_undefined", message_i18n_key="risk.warnings.average_loss_undefined_assets", message="One or more assets had no losing observation in the selected window.", details={"asset_ids": named["average_loss_undefined"]}))
    if "omega_undefined" in named:
        warnings.append(
            RiskWarning(degrades_result=False, code="omega_undefined", message_i18n_key="risk.warnings.omega_undefined_assets", message="Gains against losses is undefined for one or more assets because no observation fell below the target return.", details={"asset_ids": named["omega_undefined"]})
        )
    if "extreme_day_ratio_undefined" in named:
        warnings.append(
            RiskWarning(
                degrades_result=False,
                code="extreme_day_ratio_undefined",
                message_i18n_key="risk.warnings.extreme_day_ratio_undefined_assets",
                message="The extreme-day ratio is undefined for one or more assets because their series does not move.",
                details={"asset_ids": named["extreme_day_ratio_undefined"]},
            )
        )
    return warnings


def return_shape_fields(shape: ReturnShape, dates: Sequence[date]) -> dict[str, object]:
    """The output fields of :class:`ReturnShape`, its positions turned into the dates of ``dates`` (the returns')."""
    run = shape.longest_positive_run
    return {
        "best_realization": shape.best_realization,
        "best_realization_date": None if shape.best_realization_index is None else dates[shape.best_realization_index],
        "positive_observation_share": shape.positive_observation_share,
        "mean_positive_return": shape.mean_positive_return,
        "mean_negative_return": shape.mean_negative_return,
        "longest_positive_run_observations": None if run is None else run.length,
        "longest_positive_run_start_date": None if run is None else dates[run.start_index],
        "longest_positive_run_end_date": None if run is None else dates[run.end_index],
        "omega_ratio": shape.omega_ratio,
        "downside_deviation": shape.downside_deviation,
        "extreme_day_ratio": shape.extreme_day_ratio,
    }


__all__ = [
    "dated_horizon_window",
    "elapsed_calendar_days",
    "joint_elapsed_calendar_days",
    "prepared_asset_return_points",
    "prepared_asset_returns",
    "prepared_scope_series",
    "rally_and_depth_fields",
    "require_annualization_factor",
    "require_joint_baseline",
    "require_joint_return_dates",
    "require_primary_returns",
    "return_shape_fields",
    "return_shape_set_warnings",
    "return_shape_warnings",
]
