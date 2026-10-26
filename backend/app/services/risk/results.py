"""From prepared series to analytic results: the execution context, the result envelopes, their metadata and warnings."""

from __future__ import annotations

import json
from collections.abc import Iterator
from collections.abc import Set as AbstractSet
from datetime import UTC, date, datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.portfolio import (
    DataQualityReport,
    DataQualityStatus,
    PortfolioReportResponse,
)
from backend.app.schemas.risk import (
    AssetRiskScope,
    PreparedAssetSeriesSet,
    RiskAnalyticRequest,
    RiskAnalyticResult,
    RiskError,
    RiskErrorCode,
    RiskExcludedAsset,
    RiskMode,
    RiskQueryRequest,
    RiskResultMetadata,
    RiskResultStatus,
    RiskReturnBasis,
    RiskScopeKind,
    RiskStressMethod,
    RiskWarning,
)
from backend.app.services.financial_math.returns import observed_annualization
from backend.app.services.financial_math.series_steps import value_at
from backend.app.services.risk.base import (
    RiskComputation,
    RiskExecutionContext,
)
from backend.app.services.risk.data_quality import data_quality_warnings, merge_data_quality, plan_data_quality
from backend.app.services.risk.metrics import (
    current_buy_and_hold_returns,
    period_returns_from_cumulative,
)
from backend.app.services.risk.plan import AnalyticPlan, is_hypothetical_plan, reads_the_twrr_alone
from backend.app.services.risk.scope import ScopeInputs, scope_exclusions, scope_reference

# What the scope says about its per-asset composition: the assets left without a series, and a
# zero-return residual that includes value in transit. Neither enters the portfolio TWRR.
_COMPOSITION_WARNING_CODES = frozenset({"assets_excluded", "zero_risk_residual_includes_in_transit"})


def _days(first: date, last: date) -> Iterator[date]:
    """The calendar days ``first``..``last``, both included."""
    for offset in range((last - first).days + 1):
        yield first + timedelta(days=offset)


def held_quote_dates(prepared: PreparedAssetSeriesSet, held_asset_ids: tuple[int, ...]) -> frozenset[date]:
    """The days on which at least one held asset has a quote of its own — a benchmark's quotes don't count."""
    held = set(held_asset_ids)
    return frozenset(quote_date for series in prepared.series if series.returns.asset_id in held for quote_date in series.quote_dates)


def portfolio_twrr_returns(
    report: Optional[PortfolioReportResponse],
    observation_dates: AbstractSet[date] = frozenset(),
) -> tuple[
    Optional[date],
    tuple[date, ...],
    tuple[float, ...],
    int,
    Optional[float],
    float,
]:
    """The portfolio TWRR as period returns, read on the observation days (developer's decision of 30/09/2026).

    The report gives its TWRR as steps (D-P4): a point holds from its ``date`` to its ``through``, and the cumulative TWRR of a
    day is the point's that holds it. A day on which nothing held was quoted is a zero return that no market produced. With
    `observation_dates` — the days a held asset was quoted — only those days are kept after the baseline, and each return is
    chain-linked from the cumulative TWRR across the days dropped, so the TWRR stays exact; coverage is then measured against
    those days, not against the calendar. With none (nothing held has a quote), every calendar day is kept.
    """
    if report is None or not report.history:
        return None, (), (), 0, None, 0.0
    with_twrr = [step for step in report.history if step.twrr is not None]
    if not with_twrr:
        return None, (), (), 0, None, 0.0
    baseline_day, last_day = with_twrr[0].date, with_twrr[-1].through
    if observation_dates:
        kept_days = [baseline_day, *(day for day in sorted(observation_dates) if baseline_day < day <= last_day and (step := value_at(report.history, day)) is not None and step.twrr is not None)]
        points = [(day, value_at(report.history, day).twrr) for day in kept_days]
    else:
        points = [(day, step.twrr) for step in with_twrr for day in _days(max(step.date, baseline_day), step.through)]
    if len(points) < 2:
        return None, (), (), 0, None, 0.0
    cumulative = [float(twrr) for _day, twrr in points]
    returns = tuple(period_returns_from_cumulative(cumulative))
    return_dates = tuple(day for day, _twrr in points[1:])
    baseline = points[0][0]
    calendar_days = (return_dates[-1] - baseline).days
    annualization_factor = observed_annualization(len(returns), baseline, return_dates[-1])[1] if calendar_days > 0 else None
    if observation_dates:
        candidates = sum(1 for quote_date in observation_dates if baseline < quote_date <= return_dates[-1])
        coverage = min(1.0, len(returns) / candidates) if candidates else 0.0
    else:
        coverage = min(1.0, len(returns) / calendar_days) if calendar_days > 0 else 0.0
    return (
        baseline,
        return_dates,
        returns,
        calendar_days,
        annualization_factor,
        coverage,
    )


def context_analyzed_range(
    context: RiskExecutionContext,
) -> DateRangeModel:
    if context.primary_return_dates:
        return DateRangeModel(
            start=context.primary_return_dates[0],
            end=context.primary_return_dates[-1],
        )
    if context.prepared_series is not None and context.prepared_series.effective_range is not None:
        return context.prepared_series.effective_range
    return context.requested_range


def warning_asset_ids(warning: RiskWarning) -> list[int]:
    """The assets a warning is about, from `details.asset_ids` or a single `details.asset_id`."""
    raw = warning.details.get("asset_ids")
    if raw is None and "asset_id" in warning.details:
        raw = [warning.details["asset_id"]]
    return [asset_id for asset_id in (raw or []) if isinstance(asset_id, int) and not isinstance(asset_id, bool)]


def assets_excluded_warnings(excluded_assets: tuple[RiskExcludedAsset, ...]) -> list[RiskWarning]:
    """One `assets_excluded` warning per reason, so the sentence can say why the assets are missing.

    Keys are written out branch by branch: the i18n audit reads backend keys from their literal
    assignments, and one built at runtime would look unused.
    """
    by_reason: dict[str, list[int]] = {}
    for item in excluded_assets:
        by_reason.setdefault(item.reason, []).append(item.asset_id)
    code = "assets_excluded"
    message = "One or more scope assets were excluded from risk calculations."
    warnings: list[RiskWarning] = []
    for reason, asset_ids in sorted(by_reason.items()):
        details: dict = {"asset_ids": asset_ids, "reason": reason}
        if reason == "missing_price":
            warnings.append(RiskWarning(code=code, message=message, details=details, message_i18n_key="risk.warnings.assets_excluded_missing_price"))
        elif reason == "no_price_source":
            warnings.append(RiskWarning(code=code, message=message, details=details, message_i18n_key="risk.warnings.assets_excluded_no_price_source"))
        elif reason == "missing_fx":
            warnings.append(RiskWarning(code=code, message=message, details=details, message_i18n_key="risk.warnings.assets_excluded_missing_fx"))
        elif reason == "invalid_currency":
            warnings.append(RiskWarning(code=code, message=message, details=details, message_i18n_key="risk.warnings.assets_excluded_invalid_currency"))
        else:
            warnings.append(RiskWarning(code=code, message=message, details=details, message_i18n_key="risk.warnings.assets_excluded_insufficient_history"))
    return warnings


def dedupe_warnings(
    warnings: tuple[RiskWarning, ...],
) -> tuple[RiskWarning, ...]:
    seen: set[str] = set()
    result: list[RiskWarning] = []
    for warning in warnings:
        key = json.dumps(
            warning.model_dump(mode="json"),
            sort_keys=True,
        )
        if key not in seen:
            seen.add(key)
            result.append(warning)
    return tuple(result)


def dedupe_exclusions(
    exclusions: tuple[RiskExcludedAsset, ...],
) -> tuple[RiskExcludedAsset, ...]:
    seen: set[tuple[int, str]] = set()
    result: list[RiskExcludedAsset] = []
    for exclusion in exclusions:
        key = (exclusion.asset_id, exclusion.reason)
        if key not in seen:
            seen.add(key)
            result.append(exclusion)
    return tuple(result)


async def with_warning_asset_names(db: AsyncSession, items: list[RiskAnalyticResult]) -> list[RiskAnalyticResult]:
    """Name the assets a warning is about, so its translated sentence can list them.

    Warnings carry asset ids in `details.asset_ids` (or a single `details.asset_id`); the display
    names are read once for the whole response and added to `message_params` as `names`
    (comma-separated) and `count`.
    """
    ids = sorted({asset_id for item in items for warning in item.warnings if warning.message_i18n_key for asset_id in warning_asset_ids(warning)})
    if not ids:
        return items
    names = dict((await db.execute(select(Asset.id, Asset.display_name).where(Asset.id.in_(ids)))).all())
    enriched: list[RiskAnalyticResult] = []
    for item in items:
        warnings = []
        for warning in item.warnings:
            asset_ids = warning_asset_ids(warning)
            if warning.message_i18n_key and asset_ids:
                params = {**warning.message_params, "names": ", ".join(names.get(asset_id, f"#{asset_id}") for asset_id in asset_ids), "count": len(asset_ids)}
                warning = warning.model_copy(update={"message_params": params})
            warnings.append(warning)
        enriched.append(item.model_copy(update={"warnings": warnings}))
    return enriched


def build_execution_context(
    *,
    request: RiskQueryRequest,
    scope_inputs: ScopeInputs,
    prepared: PreparedAssetSeriesSet,
    never_priced_asset_ids: frozenset[int] = frozenset(),
) -> RiskExecutionContext:
    prepared_by_asset = {item.returns.asset_id: item for item in prepared.series if item.returns.points}
    usable_scope_asset_ids = tuple(asset_id for asset_id in scope_inputs.requested_asset_ids if asset_id in prepared_by_asset)
    excluded_assets = scope_exclusions(scope_inputs.requested_asset_ids, prepared, never_priced_asset_ids)
    data_quality = merge_data_quality(
        scope_inputs.data_quality,
        prepared.data_quality,
    )
    execution_warnings = list(scope_inputs.warnings)
    execution_warnings.extend(assets_excluded_warnings(excluded_assets))

    primary_baseline_date: Optional[date] = None
    primary_return_dates: tuple[date, ...] = ()
    primary_returns: tuple[float, ...] = ()
    primary_return_basis = RiskReturnBasis.PRICE_ONLY
    annualization_factor = prepared.annualization_factor
    calendar_days = prepared.calendar_days
    coverage = prepared.calendar_coverage

    # Q-C1: a portfolio TWRR series cannot be sliced — the portfolio report filters by
    # broker only. A sliced scope therefore takes the weighted-composition branch even
    # in historical mode, which answers a different question and says so through
    # return_basis: not "what the portfolio did" but "what today's slice would have done".
    if request.scope.kind == RiskScopeKind.PORTFOLIO and request.mode == RiskMode.HISTORICAL and not scope_inputs.slice_asset_ids:
        (
            primary_baseline_date,
            primary_return_dates,
            primary_returns,
            calendar_days,
            annualization_factor,
            coverage,
        ) = portfolio_twrr_returns(
            scope_inputs.portfolio_report,
            observation_dates=held_quote_dates(prepared, scope_inputs.requested_asset_ids),
        )
        primary_return_basis = RiskReturnBasis.TWRR
    elif request.scope.kind == RiskScopeKind.PORTFOLIO:
        rows = {asset_id: tuple(float(point.value) for point in prepared_by_asset[asset_id].returns.points) for asset_id in usable_scope_asset_ids}
        usable_weights = {asset_id: scope_inputs.weights.get(asset_id, 0.0) for asset_id in usable_scope_asset_ids}
        usable_cash_weight = max(
            0.0,
            1.0 - sum(usable_weights.values()),
        )
        if rows and scope_inputs.composition_error is None:
            primary_returns = tuple(
                current_buy_and_hold_returns(
                    rows,
                    usable_weights,
                    cash_weight=usable_cash_weight,
                )
            )
            primary_return_dates = tuple(prepared.joint_return_dates)
            primary_baseline_date = prepared.baseline_date
            # The series is today's weights replayed over past asset returns, which is
            # neither a plain price series nor what the portfolio actually did. It is
            # declared as its own basis so the UI can say "backtest" as a fact read from
            # the result instead of inferring it from the request.
            primary_return_basis = RiskReturnBasis.CURRENT_COMPOSITION_BACKTEST
    elif isinstance(request.scope, AssetRiskScope):
        item = prepared_by_asset.get(request.scope.asset_id)
        if item is not None:
            primary_returns = tuple(float(point.value) for point in item.returns.points)
            primary_return_dates = tuple(point.date for point in item.returns.points)
            primary_baseline_date = item.returns.points[0].previous_valuation_date if item.returns.points else None

    usable_weights = {asset_id: scope_inputs.weights.get(asset_id, 0.0) for asset_id in usable_scope_asset_ids}
    usable_cash_weight = max(0.0, 1.0 - sum(usable_weights.values())) if scope_inputs.weights else scope_inputs.cash_weight
    return RiskExecutionContext(
        scope_kind=request.scope.kind,
        scope_reference=scope_reference(
            request,
            broker_ids=scope_inputs.broker_ids,
            slice_asset_ids=scope_inputs.slice_asset_ids,
        ),
        requested_range=request.date_range,
        target_currency=request.target_currency,
        mode=request.mode,
        composition_policy=request.composition_policy,
        scope_asset_ids=usable_scope_asset_ids,
        prepared_series=prepared,
        primary_baseline_date=primary_baseline_date,
        primary_return_dates=primary_return_dates,
        primary_returns=primary_returns,
        primary_return_basis=primary_return_basis,
        annualization_factor=annualization_factor,
        calendar_days=calendar_days,
        coverage=coverage,
        data_quality=data_quality,
        requested_scope_asset_ids=scope_inputs.requested_asset_ids,
        excluded_assets=excluded_assets,
        execution_warnings=tuple(execution_warnings),
        portfolio_data_quality=scope_inputs.data_quality,
        prepared_data_quality=prepared.data_quality,
        weights=scope_inputs.weights,
        asset_values=scope_inputs.asset_values,
        cash_weight=usable_cash_weight,
        excluded_weight=sum((scope_inputs.weights.get(item.asset_id, 0.0) for item in excluded_assets), 0.0),
        scope_value=scope_inputs.scope_value,
        broker_ids=scope_inputs.broker_ids,
        composition_as_of=scope_inputs.composition_as_of,
        sliced_asset_ids=scope_inputs.slice_asset_ids,
    )


def available_observations(
    plan: AnalyticPlan,
    context: RiskExecutionContext,
) -> Optional[int]:
    if plan.request.analytic_code == "correlation":
        return None
    if plan.request.analytic_code in {
        "risk_contribution",
        "portfolio_optimization",
        # The weightless multi-asset family. A scope with no weights has no
        # aggregate series, so `context.n_observations` — which counts the
        # scope's own primary returns — is zero for it. Left on that branch
        # these analytics are refused for insufficient history before their
        # compute() is ever called, whatever their declared minimum: the
        # gate would be measuring the absence of a series they never asked
        # for. What they consume is the prepared set, so that is what is
        # counted, exactly as it already is for the two analytics above.
        "asset_set_kpi",
        "asset_set_var",
        "asset_set_drawdown",
        "asset_set_risk_return",
        "asset_set_comparison",
    }:
        return context.prepared_series.n_observations if context.prepared_series is not None else 0
    if plan.request.analytic_code == "stress":
        if getattr(plan.params, "method", None) == RiskStressMethod.HYPOTHETICAL:
            return None
        if context.historical_replay is None:
            return 0
        if not context.historical_replay.source_asset_ids:
            return None
        return context.historical_replay.prepared_series.n_observations
    return context.n_observations


def requires_valid_composition(
    plan: AnalyticPlan,
    context: RiskExecutionContext,
) -> bool:
    if context.mode != RiskMode.CURRENT_COMPOSITION:
        return False
    if context.scope_kind != RiskScopeKind.PORTFOLIO:
        return False
    return plan.request.analytic_code in {
        "risk_contribution",
        "stress",
        "comparison",
        "historical_var",
        "simulation",
    }


def success_result(
    *,
    plan: AnalyticPlan,
    context: RiskExecutionContext,
    computation: RiskComputation,
) -> RiskAnalyticResult:
    data_quality = plan_data_quality(plan, context)
    context_warnings = context.execution_warnings
    context_exclusions = context.excluded_assets
    if is_hypothetical_plan(plan):
        context_warnings = tuple(warning for warning in context_warnings if warning.code != "assets_excluded")
        context_exclusions = ()
    elif reads_the_twrr_alone(plan, context):
        context_warnings = tuple(warning for warning in context_warnings if warning.code not in _COMPOSITION_WARNING_CODES)
        context_exclusions = ()
    warnings = dedupe_warnings(
        (
            *context_warnings,
            *computation.warnings,
        )
    )
    if data_quality.data_quality_status != DataQualityStatus.OK:
        warnings = dedupe_warnings((*warnings, *data_quality_warnings(data_quality)))
    status = RiskResultStatus.PARTIAL if any(warning.degrades_result for warning in warnings) or context_exclusions or computation.excluded_assets or data_quality.data_quality_status != DataQualityStatus.OK else RiskResultStatus.OK
    return RiskAnalyticResult(
        instance_id=plan.request.instance_id,
        analytic_code=plan.request.analytic_code,
        status=status,
        output=computation.output,
        metadata=result_metadata(
            plan,
            context,
            computation=computation,
        ),
        data_quality=data_quality,
        warnings=list(warnings),
    )


def result_metadata(
    plan: AnalyticPlan,
    context: RiskExecutionContext,
    *,
    computation: Optional[RiskComputation] = None,
) -> RiskResultMetadata:
    n_observations = computation.n_observations if computation is not None and computation.n_observations is not None else context.n_observations
    calendar_days = computation.calendar_days if computation is not None and computation.calendar_days is not None else context.calendar_days
    annualization_factor = computation.annualization_factor if computation is not None and computation.annualization_factor is not None else context.annualization_factor
    coverage = computation.coverage if computation is not None and computation.coverage is not None else context.coverage
    if n_observations == 0:
        calendar_days = 0
        annualization_factor = None

    analyzed_range = computation.analyzed_range if computation is not None and computation.analyzed_range is not None else context_analyzed_range(context)
    context_exclusions = () if is_hypothetical_plan(plan) or reads_the_twrr_alone(plan, context) else context.excluded_assets
    computation_exclusions = computation.excluded_assets if computation is not None else ()
    exclusions = dedupe_exclusions(
        (
            *context_exclusions,
            *computation_exclusions,
        )
    )
    return RiskResultMetadata(
        analyzed_range=analyzed_range,
        n_observations=n_observations,
        calendar_days=calendar_days,
        annualization_factor=annualization_factor,
        coverage=max(0.0, min(1.0, coverage)),
        currency=context.target_currency,
        scope=context.scope_kind,
        scope_reference=context.scope_reference,
        broker_ids=(list(context.broker_ids) if context.scope_kind == RiskScopeKind.PORTFOLIO else None),
        sliced_asset_ids=(list(context.sliced_asset_ids) if context.scope_kind == RiskScopeKind.PORTFOLIO and context.sliced_asset_ids else None),
        composition_as_of=(context.composition_as_of if context.scope_kind == RiskScopeKind.PORTFOLIO else None),
        method=computation.method if computation is not None else None,
        params=plan.params.model_dump(mode="json", exclude_none=True),
        mode=context.mode,
        composition_policy=context.composition_policy,
        return_basis=(computation.return_basis if computation is not None and computation.return_basis is not None else context.primary_return_basis),
        comparison_asset_id=(computation.comparison_asset_id if computation is not None else getattr(plan.params, "comparison_asset_id", None)),
        risk_free=computation.risk_free if computation is not None else None,
        excluded_assets=list(exclusions),
        algorithm_version=plan.analytic_class.algorithm_version,
        computed_at=datetime.now(UTC),
        sampling_method=(computation.sampling_method if computation is not None else None),
        path_count=computation.path_count if computation is not None else None,
        random_seed=(computation.random_seed if computation is not None else None),
        sobol_start_index=(computation.sobol_start_index if computation is not None else None),
        bootstrap_seed=(computation.bootstrap_seed if computation is not None else None),
        historical_replay_audit=(computation.historical_replay_audit if computation is not None else None),
    )


def unavailable_result(
    request: RiskAnalyticRequest,
    code: RiskErrorCode,
    message: str,
    *,
    details: Optional[dict] = None,
    metadata: Optional[RiskResultMetadata] = None,
    data_quality: Optional[DataQualityReport] = None,
) -> RiskAnalyticResult:
    return RiskAnalyticResult(
        instance_id=request.instance_id,
        analytic_code=request.analytic_code,
        status=RiskResultStatus.UNAVAILABLE,
        metadata=metadata,
        data_quality=data_quality,
        error=RiskError(
            code=code,
            message=message,
            details=details or {},
        ),
    )
