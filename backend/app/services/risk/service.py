"""Bulk orchestration for risk analytics: the request's plans, run against one scope."""

from __future__ import annotations

from collections.abc import Set as AbstractSet
from dataclasses import replace
from datetime import date

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.logging_config import get_logger
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.portfolio import DataQualityExclusionReason
from backend.app.schemas.risk import (
    RiskAnalyticResult,
    RiskAssetEligibility,
    RiskEligibilityLevel,
    RiskEligibilityRequest,
    RiskEligibilityResponse,
    RiskError,
    RiskErrorCode,
    RiskQueryRequest,
    RiskQueryResponse,
    RiskResultStatus,
    RiskScopeKind,
)
from backend.app.services.assets.market_calendar import ensure_market_holidays
from backend.app.services.platform.data_quality_thresholds import RISK_MIN_OBSERVATIONS, STALE_PRICE_THRESHOLD_DAYS
from backend.app.services.risk.base import RiskUnavailableError
from backend.app.services.risk.data_quality import plan_data_quality, with_asset_set_quality_issues
from backend.app.services.risk.eligibility import (
    analysis_eligibility,
    common_quoted_range,
    load_price_window_facts,
    period_limits_coverage,
    suggested_analysis_ranges,
)
from backend.app.services.risk.plan import AnalyticPlan, is_geography_hypothetical_plan, is_historical_replay_plan, is_hypothetical_plan
from backend.app.services.risk.registry import RiskAnalyticRegistry
from backend.app.services.risk.replay import prepare_historical_replay_context
from backend.app.services.risk.results import available_observations, build_execution_context, requires_valid_composition, result_metadata, success_result, unavailable_result, with_warning_asset_names
from backend.app.services.risk.scope import RiskScopeNotFoundError, bounded_range, geography_group_members, load_asset_classifications, load_existing_asset_ids, load_never_priced_asset_ids, load_scope_inputs, prepare_asset_series, scope_exclusions

logger = get_logger(__name__)


class RiskService:
    """Resolve one scope and execute multiple DB-free analytics in isolation."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def catalog():
        return RiskAnalyticRegistry.list_definitions()

    async def execute(  # noqa: C901 — per-analytic orchestration loop; branches are guard/exception continues
        self,
        *,
        user_id: int,
        request: RiskQueryRequest,
    ) -> RiskQueryResponse:
        # R13-SEC8-1b: the scope's prices and its report walk the range day by day, so every step reads it bounded.
        request = request.model_copy(update={"date_range": bounded_range(request.date_range)})
        plans: dict[int, AnalyticPlan] = {}
        results: dict[int, RiskAnalyticResult] = {}
        for index, analytic_request in enumerate(request.analytics):
            analytic_class = RiskAnalyticRegistry.get_plugin(analytic_request.analytic_code)
            if analytic_class is None:
                results[index] = unavailable_result(
                    analytic_request,
                    RiskErrorCode.ANALYTIC_NOT_FOUND,
                    f"Unknown risk analytic '{analytic_request.analytic_code}'",
                )
                continue
            if request.scope.kind not in analytic_class.supported_scopes:
                results[index] = unavailable_result(
                    analytic_request,
                    RiskErrorCode.INCOMPATIBLE_SCOPE,
                    f"Analytic '{analytic_request.analytic_code}' does not support scope '{request.scope.kind.value}'",
                )
                continue
            if request.mode not in analytic_class.supported_modes:
                results[index] = unavailable_result(
                    analytic_request,
                    RiskErrorCode.INCOMPATIBLE_MODE,
                    f"Analytic '{analytic_request.analytic_code}' does not support mode '{request.mode.value}'",
                )
                continue
            try:
                params = analytic_class.validate_params(analytic_request.parameters)
            except ValidationError as exc:
                results[index] = unavailable_result(
                    analytic_request,
                    RiskErrorCode.INVALID_PARAMETERS,
                    f"Invalid parameters for analytic '{analytic_request.analytic_code}'",
                    details={"validation_errors": [error["msg"] for error in exc.errors(include_url=False)]},
                )
                continue
            plans[index] = AnalyticPlan(
                request=analytic_request,
                analytic_class=analytic_class,
                analytic=analytic_class(),
                params=params,
            )

        scope_inputs = await load_scope_inputs(
            self.db,
            user_id=user_id,
            request=request,
        )
        comparison_dependency_asset_ids = {int(comparison_asset_id) for plan in plans.values() if (comparison_asset_id := getattr(plan.params, "comparison_asset_id", None)) is not None}
        replay_proxy_asset_ids = {int(proxy.proxy_asset_id) for plan in plans.values() if is_historical_replay_plan(plan) for proxy in getattr(plan.params, "proxy_assets", ())}
        existing_asset_ids = await load_existing_asset_ids(self.db, set(scope_inputs.requested_asset_ids) | comparison_dependency_asset_ids | replay_proxy_asset_ids)
        missing_scope_asset_ids = set(scope_inputs.requested_asset_ids) - existing_asset_ids
        if missing_scope_asset_ids:
            raise RiskScopeNotFoundError(f"Unknown asset IDs in risk scope: {sorted(missing_scope_asset_ids)}")

        # One holiday table per request, handed to every preparation and reading of it (see `market_calendar`).
        market_holidays = await ensure_market_holidays()
        try:
            prepared = await prepare_asset_series(
                self.db,
                asset_ids=tuple(sorted(set(scope_inputs.requested_asset_ids) | (comparison_dependency_asset_ids & existing_asset_ids))),
                date_range=request.date_range,
                target_currency=request.target_currency,
                market_holidays=market_holidays,
            )
        except RiskUnavailableError as exc:
            # J-50: a scope refused as a whole (its prices exceed a size limit) answers every planned analytic with that
            # refusal; one already answered (unknown, invalid parameters) keeps its own.
            for index, plan in plans.items():
                if index not in results:
                    results[index] = unavailable_result(plan.request, exc.code, str(exc), details=exc.details)
            return await self._response(request, results)
        never_priced_asset_ids = await load_never_priced_asset_ids(
            self.db,
            tuple(item.asset_id for item in scope_exclusions(scope_inputs.requested_asset_ids, prepared) if item.reason == DataQualityExclusionReason.MISSING_PRICE),
        )
        context = build_execution_context(
            request=request,
            scope_inputs=scope_inputs,
            prepared=prepared,
            never_priced_asset_ids=never_priced_asset_ids,
        )
        if any(is_hypothetical_plan(plan) for plan in plans.values()):
            context = replace(
                context,
                asset_classifications=await load_asset_classifications(self.db, scope_inputs.requested_asset_ids),
                geography_groups=(geography_group_members() if any(is_geography_hypothetical_plan(plan) for plan in plans.values()) else {}),
            )

        for index, plan in plans.items():
            if index in results:
                continue
            comparison_asset_id = getattr(plan.params, "comparison_asset_id", None)
            if comparison_asset_id is not None and comparison_asset_id not in existing_asset_ids:
                results[index] = unavailable_result(
                    plan.request,
                    RiskErrorCode.INVALID_PARAMETERS,
                    f"Comparison asset {comparison_asset_id} does not exist",
                    details={"comparison_asset_id": comparison_asset_id},
                    metadata=result_metadata(plan, context),
                    data_quality=plan_data_quality(plan, context),
                )
                continue
            if requires_valid_composition(plan, context) and scope_inputs.composition_error:
                results[index] = unavailable_result(
                    plan.request,
                    RiskErrorCode.DATA_UNAVAILABLE,
                    scope_inputs.composition_error,
                    metadata=result_metadata(plan, context),
                    data_quality=plan_data_quality(plan, context),
                )
                continue
            plan_context = context
            if is_historical_replay_plan(plan):
                try:
                    plan_context = await prepare_historical_replay_context(
                        self.db,
                        plan=plan,
                        context=context,
                        scope_inputs=scope_inputs,
                        existing_asset_ids=existing_asset_ids,
                        target_currency=request.target_currency,
                        market_holidays=market_holidays,
                    )
                except RiskUnavailableError as exc:
                    results[index] = unavailable_result(
                        plan.request,
                        exc.code,
                        str(exc),
                        details=exc.details,
                        metadata=result_metadata(plan, context),
                        data_quality=plan_data_quality(plan, context),
                    )
                    continue
            observations = available_observations(plan, plan_context)
            if observations is not None and observations < plan.analytic_class.min_observations:
                results[index] = unavailable_result(
                    plan.request,
                    RiskErrorCode.INSUFFICIENT_HISTORY,
                    f"Analytic '{plan.request.analytic_code}' requires at least {plan.analytic_class.min_observations} observations",
                    details={
                        "observations": observations,
                        "required": plan.analytic_class.min_observations,
                    },
                    metadata=result_metadata(plan, plan_context),
                    data_quality=plan_data_quality(plan, plan_context),
                )
                continue
            try:
                computation = await plan.analytic.execute(
                    plan.params,
                    plan_context,
                )
            except RiskUnavailableError as exc:
                results[index] = unavailable_result(
                    plan.request,
                    exc.code,
                    str(exc),
                    details=exc.details,
                    metadata=result_metadata(plan, plan_context),
                    data_quality=plan_data_quality(plan, plan_context),
                )
                continue
            except Exception as exc:
                # Every failure that a plugin did not DECLARE lands here, and it is
                # reported as ours rather than as a property of the user's data.
                #
                # This branch used to be preceded by `except (ValueError,
                # ArithmeticError)`, which answered the same class of event with
                # `UNDEFINED_METRIC` -- "The metric is undefined for these data." --
                # and, unlike this one, WITHOUT logging. Two consequences made that
                # the wrong pairing, and neither is a matter of taste:
                #
                #  * a violated internal invariant was delivered to the user as a
                #    verdict about their portfolio. Nobody reports a bug they have
                #    been told is a limitation of their own data, so the defect was
                #    both invisible to us (no log) and un-actionable for them;
                #  * an over-reported fault gets investigated and then narrowed into
                #    an explicit code; an under-reported one stays silent forever.
                #    The two errors are not symmetric, so the safe default is the
                #    one that says "we failed" rather than "your data cannot".
                #
                # A metric that is genuinely undefined for well-formed data is NOT
                # expressed by raising: it is a per-value `RiskValueStatus.UNDEFINED`
                # (see `correlation.py`), which keeps the rest of the result usable.
                # So an exception arriving here never meant "undefined metric" in the
                # first place. `UNDEFINED_METRIC` stays in the enum for a plugin that
                # declares it through `RiskUnavailableError`, caught above.
                #
                # `str(exc)` is deliberately NOT propagated: internal English prose
                # would reach the payload while the client renders only the code. The
                # detail belongs in the log, where it is actionable; the code is what
                # crosses the wire.
                logger.exception(
                    "Risk analytic execution failed",
                    analytic_code=plan.request.analytic_code,
                    error_type=type(exc).__name__,
                )
                results[index] = RiskAnalyticResult(
                    instance_id=plan.request.instance_id,
                    analytic_code=plan.request.analytic_code,
                    status=RiskResultStatus.FAILED,
                    metadata=result_metadata(plan, plan_context),
                    data_quality=plan_data_quality(plan, plan_context),
                    error=RiskError(
                        code=RiskErrorCode.EXECUTION_FAILED,
                        message="Risk analytic execution failed",
                        details={"error_type": type(exc).__name__},
                    ),
                )
                continue
            results[index] = success_result(
                plan=plan,
                context=plan_context,
                computation=computation,
            )

        return await self._response(request, results)

    async def _response(self, request: RiskQueryRequest, results: dict[int, RiskAnalyticResult]) -> RiskQueryResponse:
        """The response: one result per requested analytic, in request order, with its warnings' asset names."""
        items = await with_warning_asset_names(self.db, [results[index] for index in range(len(request.analytics))])
        if request.scope.kind == RiskScopeKind.ASSET_SET:
            items = await with_asset_set_quality_issues(self.db, items)
        return RiskQueryResponse(items=items)

    async def asset_eligibility(self, request: RiskEligibilityRequest) -> RiskEligibilityResponse:
        """Whether each asset can take part in a risk analysis of the requested period.

        Read from the asset's own quotes, not from a joint calendar, so the answer for one asset does
        not depend on what else is selected. An unknown asset has no quotes and is ineligible.
        """
        start = request.date_range.start
        end = request.date_range.end or start
        asset_ids = list(dict.fromkeys(request.asset_ids))
        market_holidays = await ensure_market_holidays()
        facts = await load_price_window_facts(self.db, asset_ids=asset_ids, window_start=start, window_end=end, target_currency=request.target_currency, market_holidays=market_holidays)
        items: list[RiskAssetEligibility] = []
        for asset_id in asset_ids:
            fact = facts[asset_id]
            level, reasons = analysis_eligibility(fact, start, end)
            items.append(
                RiskAssetEligibility(
                    asset_id=asset_id,
                    level=level,
                    reasons=list(reasons),
                    first_quote=fact.first_quote,
                    last_quote=fact.last_quote,
                    quotes_in_period=fact.quotes_in_window,
                )
            )
        # A common period is proposed only when the chosen period is what troubles a quoted asset —
        # it starts late, stops early or is quoted only outside the period (developer's decision of
        # 24/09/2026); an asset without any quote cannot be helped by any period.
        quoted_ids = [asset_id for asset_id in asset_ids if facts[asset_id].first_quote_ever is not None]
        common = common_quoted_range(facts[asset_id] for asset_id in quoted_ids)
        suggested = None
        if any(period_limits_coverage(facts[asset_id], start, end) for asset_id in quoted_ids):
            for candidate in suggested_analysis_ranges(common, start, end):
                if await self._every_asset_eligible(quoted_ids, candidate, request.target_currency, market_holidays):
                    suggested = candidate
                    break
        return RiskEligibilityResponse(
            items=items,
            min_quotes=RISK_MIN_OBSERVATIONS,
            stale_days=STALE_PRICE_THRESHOLD_DAYS,
            common_range=DateRangeModel(start=common[0], end=common[1]) if common else None,
            suggested_range=DateRangeModel(start=suggested[0], end=suggested[1]) if suggested else None,
        )

    async def _every_asset_eligible(self, asset_ids: list[int], window: tuple[date, date], target_currency: str, market_holidays: AbstractSet[date] = frozenset()) -> bool:
        """Whether every asset is eligible, without warnings, for an analysis of `window`."""
        start, end = window
        facts = await load_price_window_facts(self.db, asset_ids=asset_ids, window_start=start, window_end=end, target_currency=target_currency, market_holidays=market_holidays)
        return all(analysis_eligibility(facts[asset_id], start, end)[0] == RiskEligibilityLevel.ELIGIBLE for asset_id in asset_ids)


__all__ = [
    "RiskService",
]
