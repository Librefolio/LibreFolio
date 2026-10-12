"""Relative performance against a real comparison asset."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.risk import (
    RiskComparisonHoldingItem,
    RiskComparisonOutput,
    RiskComparisonPoint,
    RiskErrorCode,
    RiskFreeReference,
    RiskMode,
    RiskOutputKind,
    RiskReturnBasis,
    RiskScopeKind,
    RiskWarning,
)
from backend.app.services.data_quality_thresholds import RISK_MIN_OBSERVATIONS
from backend.app.services.provider_registry import RiskAnalyticRegistry, register_plugin
from backend.app.services.risk.analytic_helpers import (
    prepared_asset_return_points,
    require_annualization_factor,
    require_primary_returns,
)
from backend.app.services.risk.base import (
    RiskAnalytic,
    RiskComputation,
    RiskExecutionContext,
    RiskSeriesInputs,
    RiskUnavailableError,
)
from backend.app.services.risk.metrics import (
    annualized_expected_return,
    annualized_sharpe,
    annualized_sortino,
    annualized_volatility,
    beta,
    comparison_summary,
    pearson_correlation,
)


@dataclass(frozen=True)
class _SpanPair:
    """One primary return and the benchmark's return over the same span."""

    point_date: date
    span_start: date
    primary_return: float
    comparison_return: float


def _compounded(values: Sequence[float]) -> float:
    """Compound simple returns, taking a single one as it is so no rounding is added."""
    if len(values) == 1:
        return values[0]
    growth = 1.0
    for value in values:
        growth *= 1.0 + value
    return growth - 1.0


def _pair_over_primary_spans(
    primary_dates: Sequence[date],
    primary_returns: Sequence[float],
    primary_baseline: date | None,
    benchmark_points: Sequence[tuple[date, date, float]],
) -> list[_SpanPair]:
    """Pair the two series over the same spans: between the dates they share.

    Each series is compounded from its own returns dated inside the span, so a benchmark
    quoted on days the primary skips keeps those moves: a portfolio is read only on the
    days its holdings are quoted, while a crypto benchmark also moves at weekends and a
    benchmark from another exchange trades on this one's holidays. A side with a single
    return in the span takes it as it is, so two series on one calendar pair exactly as
    a plain date match would.

    The first span starts at the primary's baseline. Until the first pair, a primary
    date the benchmark has no return on is dropped and the next span starts there, so a
    benchmark that starts late is joined from the last date it could not answer. After
    the first pair, such a date is no boundary: the span runs on from the last shared
    date, and both sides are compounded across it at the next one.
    """
    benchmark = sorted(benchmark_points, key=lambda point: point[0])
    pairs: list[_SpanPair] = []
    index = 0
    span_start = primary_baseline
    primary_inside: list[float] = []
    benchmark_inside: list[tuple[date, date, float]] = []
    for point_date, primary_return in zip(primary_dates, primary_returns, strict=True):
        primary_inside.append(primary_return)
        while index < len(benchmark) and benchmark[index][0] <= point_date:
            if span_start is None or benchmark[index][0] > span_start:
                benchmark_inside.append(benchmark[index])
            index += 1
        if benchmark_inside and benchmark_inside[-1][0] == point_date:
            pairs.append(
                _SpanPair(
                    point_date=point_date,
                    span_start=span_start if span_start is not None else benchmark_inside[0][1],
                    primary_return=_compounded(primary_inside),
                    comparison_return=_compounded([value for _benchmark_date, _previous_date, value in benchmark_inside]),
                )
            )
        elif pairs:
            continue
        span_start = point_date
        primary_inside = []
        benchmark_inside = []
    return pairs


def _holding_items(
    comparison_asset_id: int,
    context: RiskExecutionContext,
    benchmark_points: Sequence[tuple[date, date, float]],
) -> list[RiskComparisonHoldingItem]:
    """Each holding of a portfolio scope against the reference, on the request's joint calendar.

    The holdings and the reference were prepared together, so each holding's returns sit on the
    reference's dates and pair with them date for date, through the same span rule as the primary.
    In current composition the portfolio is read on that calendar too, so the holdings and the
    portfolio pair over the same days; in historical mode the portfolio's TWRR is read on its own
    observation days, and the holdings keep the joint calendar. A held reference is the yardstick,
    not a subject (D371), so it gets no item; nor does a holding without a prepared series. An
    asset scope has no holdings to break down: its only subject is the asset itself.
    """
    if context.scope_kind != RiskScopeKind.PORTFOLIO or context.prepared_series is None:
        return []
    prepared = {item.returns.asset_id: item.returns.points for item in context.prepared_series.series}
    items: list[RiskComparisonHoldingItem] = []
    for asset_id in sorted(context.scope_asset_ids):
        points = prepared.get(asset_id)
        if asset_id == comparison_asset_id or not points:
            continue
        pairs = _pair_over_primary_spans(
            [point.date for point in points],
            [float(point.value) for point in points],
            points[0].previous_valuation_date,
            benchmark_points,
        )
        if len(pairs) < 2:
            # Beta and correlation need two pairs; a missing item says «not measured», a 0 would not.
            continue
        holding_returns = [pair.primary_return for pair in pairs]
        reference_returns = [pair.comparison_return for pair in pairs]
        items.append(
            RiskComparisonHoldingItem(
                asset_id=asset_id,
                beta=beta(holding_returns, reference_returns),
                correlation=pearson_correlation(holding_returns, reference_returns),
            )
        )
    return items


class ComparisonParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comparison_asset_id: int = Field(
        ge=1,
        json_schema_extra={
            "x-control": "comparison_asset",
            "x-i18n-key": "chartSettings.params.comparisonAsset",
            "x-control-order": 1,
        },
    )
    risk_free_annual_rate: float = Field(
        0.0,
        gt=-1,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.riskFreeAnnualRate",
            "x-control-order": 2,
            "x-step": 0.001,
        },
    )
    target_annual_return: float = Field(
        0.0,
        gt=-1,
        json_schema_extra={
            "x-i18n-key": "risk.params.targetAnnualReturn",
            "x-control-order": 3,
            "x-step": 0.001,
        },
    )


@register_plugin(RiskAnalyticRegistry)
class ComparisonAnalytic(RiskAnalytic):
    analytic_code = "comparison"
    # 1.1.0 — both series are compounded between the dates they share. A portfolio read
    # on its observation days skips days its benchmark may still be quoted on; 1.0.0
    # paired by date and dropped the benchmark's moves on those days.
    # 1.2.0 — the payload adds the reference's own Sharpe and Sortino, charged the rate and the
    # target the request gives (both 0 by default), and, on a portfolio, each holding's beta and
    # correlation against the same reference. The other numbers are unchanged.
    algorithm_version = "1.2.0"
    name_i18n_key = "risk.analytics.comparison.name"
    description_i18n_key = "risk.analytics.comparison.description"
    output_kind = RiskOutputKind.COMPARISON
    supported_scopes = (
        RiskScopeKind.ASSET,
        RiskScopeKind.PORTFOLIO,
    )
    supported_modes = (RiskMode.HISTORICAL, RiskMode.CURRENT_COMPOSITION)
    params_model = ComparisonParams
    min_observations = RISK_MIN_OBSERVATIONS
    series_inputs = RiskSeriesInputs.PRIMARY_AND_BENCHMARK

    def compute(self, params, context):
        primary_dates, primary_returns = require_primary_returns(context)
        benchmark_points = prepared_asset_return_points(context, params.comparison_asset_id)
        pairs = _pair_over_primary_spans(
            primary_dates,
            primary_returns,
            context.primary_baseline_date,
            benchmark_points,
        )
        common_dates = tuple(pair.point_date for pair in pairs)
        if len(common_dates) < self.min_observations:
            raise RiskUnavailableError(
                "Comparison has insufficient common observations",
                code=RiskErrorCode.INSUFFICIENT_HISTORY,
                details={
                    "observations": len(common_dates),
                    "required": self.min_observations,
                },
            )
        baseline_date = pairs[0].span_start
        calendar_days = (common_dates[-1] - baseline_date).days
        annualization_factor = len(common_dates) * 365 / calendar_days if calendar_days > 0 else require_annualization_factor(context)
        comparison_common_returns = [pair.comparison_return for pair in pairs]
        summary = comparison_summary(
            [pair.primary_return for pair in pairs],
            comparison_common_returns,
            annualization_factor,
        )
        warnings: list[RiskWarning] = []
        if summary.beta is None:
            warnings.append(
                RiskWarning(
                    code="comparison_beta_undefined",
                    message_i18n_key="risk.warnings.comparison_beta_undefined",
                    message="Beta is undefined because the comparison asset has zero variance.",
                )
            )
        if summary.correlation is None:
            warnings.append(
                RiskWarning(
                    code="comparison_correlation_undefined",
                    message_i18n_key="risk.warnings.comparison_correlation_undefined",
                    message="Correlation is undefined because at least one series has zero variance.",
                )
            )
        comparison_sharpe = annualized_sharpe(comparison_common_returns, annualization_factor, annual_risk_free_rate=params.risk_free_annual_rate)
        comparison_sortino = annualized_sortino(comparison_common_returns, annualization_factor, annual_target_return=params.target_annual_return)
        if comparison_sharpe is None:
            warnings.append(
                RiskWarning(
                    code="sharpe_undefined",
                    message_i18n_key="risk.warnings.sharpe_undefined_assets",
                    message="Sharpe is undefined for the comparison asset because its volatility is zero.",
                    details={"asset_ids": [params.comparison_asset_id]},
                )
            )
        if comparison_sortino is None:
            warnings.append(
                RiskWarning(
                    code="sortino_undefined",
                    message_i18n_key="risk.warnings.sortino_undefined_assets",
                    message="Sortino is undefined for the comparison asset because its downside deviation is zero.",
                    details={"asset_ids": [params.comparison_asset_id]},
                )
            )
        items = _holding_items(params.comparison_asset_id, context, benchmark_points)
        # A flat reference voids every beta and correlation at once, and the two warnings above
        # already say so for all of them. Otherwise each holding whose figure is undefined is named.
        if summary.beta is not None:
            undefined_beta = [item.asset_id for item in items if item.beta is None]
            undefined_correlation = [item.asset_id for item in items if item.correlation is None]
            if undefined_beta:
                warnings.append(
                    RiskWarning(
                        code="comparison_beta_undefined",
                        message_i18n_key="risk.warnings.comparison_beta_undefined_assets",
                        message="Beta is undefined for one or more holdings because the comparison asset has zero variance.",
                        details={"asset_ids": undefined_beta},
                    )
                )
            if undefined_correlation:
                warnings.append(
                    RiskWarning(
                        code="comparison_correlation_undefined",
                        message_i18n_key="risk.warnings.comparison_correlation_undefined_assets",
                        message="Correlation is undefined for one or more holdings because at least one series has zero variance.",
                        details={"asset_ids": undefined_correlation},
                    )
                )
        return RiskComputation(
            output=RiskComparisonOutput(
                comparison_asset_id=params.comparison_asset_id,
                active_return=summary.active_return,
                tracking_error=summary.tracking_error,
                information_ratio=summary.information_ratio,
                correlation=summary.correlation,
                beta=summary.beta,
                observations=len(common_dates),
                # The reference's own risk and reward, measured on the same common days
                # as everything above. A risk/return plot needs the benchmark placed
                # next to the holdings; computing it here costs one pass over a series
                # already in hand, and keeps the arithmetic convention in the backend
                # where the rest of it lives.
                comparison_volatility=annualized_volatility(comparison_common_returns, annualization_factor),
                comparison_expected_annual_return=annualized_expected_return(comparison_common_returns, annualization_factor),
                comparison_sharpe=comparison_sharpe,
                comparison_sortino=comparison_sortino,
                items=items,
                series=[
                    RiskComparisonPoint(
                        date=point_date,
                        primary_cumulative_return=primary_cumulative,
                        comparison_cumulative_return=comparison_cumulative,
                        primary_drawdown=primary_drawdown,
                        comparison_drawdown=comparison_drawdown,
                    )
                    for point_date, primary_cumulative, comparison_cumulative, primary_drawdown, comparison_drawdown in zip(
                        common_dates,
                        summary.primary_cumulative,
                        summary.comparison_cumulative,
                        summary.primary_drawdowns,
                        summary.comparison_drawdowns,
                        strict=True,
                    )
                ],
            ),
            method="comparison_asset",
            warnings=tuple(warnings),
            risk_free=RiskFreeReference(
                annual_rate=params.risk_free_annual_rate,
                source="analytic_param",
                currency=context.target_currency,
            ),
            comparison_asset_id=params.comparison_asset_id,
            n_observations=len(common_dates),
            calendar_days=calendar_days,
            annualization_factor=annualization_factor,
            coverage=len(common_dates) / len(primary_dates) if primary_dates else 0,
            return_basis=RiskReturnBasis.PRICE_ONLY if context.scope_kind == RiskScopeKind.ASSET else context.primary_return_basis,
        )
