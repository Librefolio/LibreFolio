"""Bulk orchestration for risk analytics."""

from __future__ import annotations

import json
from collections.abc import Set as AbstractSet
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ValidationError
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetProviderAssignment, BrokerUserAccess, PriceHistory
from backend.app.logging_config import get_logger
from backend.app.schemas.assets import FAClassificationParams
from backend.app.schemas.common import DateRangeModel, OpenDateRangeModel
from backend.app.schemas.portfolio import (
    DataQualityExclusionReason,
    DataQualityIssue,
    DataQualityReport,
    DataQualityStatus,
    IssueCode,
    IssueDomain,
    IssueSeverity,
    PortfolioReportQuery,
    PortfolioReportResponse,
)
from backend.app.schemas.prices import FAPriceQueryItem
from backend.app.schemas.risk import (
    AssetRiskScope,
    AssetSetRiskScope,
    PortfolioRiskScope,
    PreparedAssetSeriesSet,
    RiskAnalyticRequest,
    RiskAnalyticResult,
    RiskAssetEligibility,
    RiskEligibilityLevel,
    RiskEligibilityRequest,
    RiskEligibilityResponse,
    RiskError,
    RiskErrorCode,
    RiskExcludedAsset,
    RiskHistoricalReplayExclusionReason,
    RiskMode,
    RiskQueryRequest,
    RiskQueryResponse,
    RiskResultMetadata,
    RiskResultStatus,
    RiskReturnBasis,
    RiskScopeKind,
    RiskStressMethod,
    RiskWarning,
)
from backend.app.services.asset_source import AssetSourceManager
from backend.app.services.data_quality_thresholds import RISK_MIN_OBSERVATIONS, STALE_PRICE_THRESHOLD_DAYS
from backend.app.services.market_calendar import ensure_market_holidays
from backend.app.services.portfolio_service import PortfolioService
from backend.app.services.provider_registry import RiskAnalyticRegistry
from backend.app.services.risk.base import (
    RiskAnalytic,
    RiskAssetClassification,
    RiskComputation,
    RiskExecutionContext,
    RiskHistoricalReplayContext,
    RiskSeriesInputs,
    RiskUnavailableError,
)
from backend.app.services.risk.eligibility import (
    PriceWindowFacts,
    analysis_eligibility,
    common_quoted_range,
    load_price_window_facts,
    period_limits_coverage,
    replay_coverage,
    suggested_analysis_ranges,
    suggested_replay_range,
)
from backend.app.services.risk.metrics import (
    current_buy_and_hold_returns,
    period_returns_from_cumulative,
)
from backend.app.services.risk.scenario_catalog import (
    get_loaded_risk_scenario_catalog,
)
from backend.app.services.series_preparation import prepare_asset_series_set

logger = get_logger(__name__)


class RiskScopeNotFoundError(ValueError):
    """Requested risk scope does not exist."""


class RiskScopeAccessError(PermissionError):
    """Current user cannot access the requested risk scope."""


@dataclass(frozen=True, slots=True)
class _AnalyticPlan:
    request: RiskAnalyticRequest
    analytic_class: type[RiskAnalytic]
    analytic: RiskAnalytic
    params: BaseModel


@dataclass(frozen=True, slots=True)
class _ScopeInputs:
    requested_asset_ids: tuple[int, ...]
    weights: dict[int, float]
    asset_values: dict[int, Decimal]
    cash_weight: float
    scope_value: Optional[Decimal]
    portfolio_report: Optional[PortfolioReportResponse]
    data_quality: DataQualityReport
    warnings: tuple[RiskWarning, ...]
    composition_error: Optional[str] = None
    broker_ids: tuple[int, ...] = ()
    composition_as_of: Optional[date] = None
    slice_asset_ids: tuple[int, ...] = ()


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
        plans: dict[int, _AnalyticPlan] = {}
        results: dict[int, RiskAnalyticResult] = {}
        for index, analytic_request in enumerate(request.analytics):
            analytic_class = RiskAnalyticRegistry.get_plugin(analytic_request.analytic_code)
            if analytic_class is None:
                results[index] = self._unavailable(
                    analytic_request,
                    RiskErrorCode.ANALYTIC_NOT_FOUND,
                    f"Unknown risk analytic '{analytic_request.analytic_code}'",
                )
                continue
            if request.scope.kind not in analytic_class.supported_scopes:
                results[index] = self._unavailable(
                    analytic_request,
                    RiskErrorCode.INCOMPATIBLE_SCOPE,
                    f"Analytic '{analytic_request.analytic_code}' does not support scope '{request.scope.kind.value}'",
                )
                continue
            if request.mode not in analytic_class.supported_modes:
                results[index] = self._unavailable(
                    analytic_request,
                    RiskErrorCode.INCOMPATIBLE_MODE,
                    f"Analytic '{analytic_request.analytic_code}' does not support mode '{request.mode.value}'",
                )
                continue
            try:
                params = analytic_class.validate_params(analytic_request.parameters)
            except ValidationError as exc:
                results[index] = self._unavailable(
                    analytic_request,
                    RiskErrorCode.INVALID_PARAMETERS,
                    f"Invalid parameters for analytic '{analytic_request.analytic_code}'",
                    details={"validation_errors": [error["msg"] for error in exc.errors(include_url=False)]},
                )
                continue
            plans[index] = _AnalyticPlan(
                request=analytic_request,
                analytic_class=analytic_class,
                analytic=analytic_class(),
                params=params,
            )

        scope_inputs = await self._load_scope_inputs(
            user_id=user_id,
            request=request,
        )
        comparison_dependency_asset_ids = {int(comparison_asset_id) for plan in plans.values() if (comparison_asset_id := getattr(plan.params, "comparison_asset_id", None)) is not None}
        replay_proxy_asset_ids = {int(proxy.proxy_asset_id) for plan in plans.values() if _is_historical_replay_plan(plan) for proxy in getattr(plan.params, "proxy_assets", ())}
        existing_asset_ids = await self._existing_asset_ids(set(scope_inputs.requested_asset_ids) | comparison_dependency_asset_ids | replay_proxy_asset_ids)
        missing_scope_asset_ids = set(scope_inputs.requested_asset_ids) - existing_asset_ids
        if missing_scope_asset_ids:
            raise RiskScopeNotFoundError(f"Unknown asset IDs in risk scope: {sorted(missing_scope_asset_ids)}")

        # One holiday table per request, handed to every preparation and reading of it (see `market_calendar`).
        market_holidays = await ensure_market_holidays()
        prepared = await self._prepare_asset_series(
            asset_ids=tuple(sorted(set(scope_inputs.requested_asset_ids) | (comparison_dependency_asset_ids & existing_asset_ids))),
            date_range=request.date_range,
            target_currency=request.target_currency,
            market_holidays=market_holidays,
        )
        never_priced_asset_ids = await self._never_priced_asset_ids(
            tuple(item.asset_id for item in _scope_exclusions(scope_inputs.requested_asset_ids, prepared) if item.reason == DataQualityExclusionReason.MISSING_PRICE),
        )
        context = self._build_context(
            request=request,
            scope_inputs=scope_inputs,
            prepared=prepared,
            never_priced_asset_ids=never_priced_asset_ids,
        )
        if any(_is_hypothetical_plan(plan) for plan in plans.values()):
            context = replace(
                context,
                asset_classifications=await self._load_asset_classifications(scope_inputs.requested_asset_ids),
                geography_groups=(self._geography_group_members() if any(_is_geography_hypothetical_plan(plan) for plan in plans.values()) else {}),
            )

        for index, plan in plans.items():
            if index in results:
                continue
            comparison_asset_id = getattr(plan.params, "comparison_asset_id", None)
            if comparison_asset_id is not None and comparison_asset_id not in existing_asset_ids:
                results[index] = self._unavailable(
                    plan.request,
                    RiskErrorCode.INVALID_PARAMETERS,
                    f"Comparison asset {comparison_asset_id} does not exist",
                    details={"comparison_asset_id": comparison_asset_id},
                    metadata=self._metadata(plan, context),
                    data_quality=self._data_quality(plan, context),
                )
                continue
            if self._requires_valid_composition(plan, context) and scope_inputs.composition_error:
                results[index] = self._unavailable(
                    plan.request,
                    RiskErrorCode.DATA_UNAVAILABLE,
                    scope_inputs.composition_error,
                    metadata=self._metadata(plan, context),
                    data_quality=self._data_quality(plan, context),
                )
                continue
            plan_context = context
            if _is_historical_replay_plan(plan):
                try:
                    plan_context = await self._prepare_historical_replay_context(
                        plan=plan,
                        context=context,
                        scope_inputs=scope_inputs,
                        existing_asset_ids=existing_asset_ids,
                        target_currency=request.target_currency,
                        market_holidays=market_holidays,
                    )
                except RiskUnavailableError as exc:
                    results[index] = self._unavailable(
                        plan.request,
                        exc.code,
                        str(exc),
                        details=exc.details,
                        metadata=self._metadata(plan, context),
                        data_quality=self._data_quality(plan, context),
                    )
                    continue
            observations = self._available_observations(plan, plan_context)
            if observations is not None and observations < plan.analytic_class.min_observations:
                results[index] = self._unavailable(
                    plan.request,
                    RiskErrorCode.INSUFFICIENT_HISTORY,
                    f"Analytic '{plan.request.analytic_code}' requires at least {plan.analytic_class.min_observations} observations",
                    details={
                        "observations": observations,
                        "required": plan.analytic_class.min_observations,
                    },
                    metadata=self._metadata(plan, plan_context),
                    data_quality=self._data_quality(plan, plan_context),
                )
                continue
            try:
                computation = await plan.analytic.execute(
                    plan.params,
                    plan_context,
                )
            except RiskUnavailableError as exc:
                results[index] = self._unavailable(
                    plan.request,
                    exc.code,
                    str(exc),
                    details=exc.details,
                    metadata=self._metadata(plan, plan_context),
                    data_quality=self._data_quality(plan, plan_context),
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
                    metadata=self._metadata(plan, plan_context),
                    data_quality=self._data_quality(plan, plan_context),
                    error=RiskError(
                        code=RiskErrorCode.EXECUTION_FAILED,
                        message="Risk analytic execution failed",
                        details={"error_type": type(exc).__name__},
                    ),
                )
                continue
            results[index] = self._success(
                plan=plan,
                context=plan_context,
                computation=computation,
            )

        items = await self._with_warning_asset_names([results[index] for index in range(len(request.analytics))])
        if request.scope.kind == RiskScopeKind.ASSET_SET:
            items = await self._with_asset_set_quality_issues(items)
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

    async def _with_warning_asset_names(self, items: list[RiskAnalyticResult]) -> list[RiskAnalyticResult]:
        """Name the assets a warning is about, so its translated sentence can list them.

        Warnings carry asset ids in `details.asset_ids` (or a single `details.asset_id`); the display
        names are read once for the whole response and added to `message_params` as `names`
        (comma-separated) and `count`.
        """
        ids = sorted({asset_id for item in items for warning in item.warnings if warning.message_i18n_key for asset_id in _warning_asset_ids(warning)})
        if not ids:
            return items
        names = dict((await self.db.execute(select(Asset.id, Asset.display_name).where(Asset.id.in_(ids)))).all())
        enriched: list[RiskAnalyticResult] = []
        for item in items:
            warnings = []
            for warning in item.warnings:
                asset_ids = _warning_asset_ids(warning)
                if warning.message_i18n_key and asset_ids:
                    params = {**warning.message_params, "names": ", ".join(names.get(asset_id, f"#{asset_id}") for asset_id in asset_ids), "count": len(asset_ids)}
                    warning = warning.model_copy(update={"message_params": params})
                warnings.append(warning)
            enriched.append(item.model_copy(update={"warnings": warnings}))
        return enriched

    async def _with_asset_set_quality_issues(self, items: list[RiskAnalyticResult]) -> list[RiskAnalyticResult]:
        """Give an asset set's reports the banner's issues, which only the portfolio engine builds (D373).

        The Asset Global lab shows the data-quality banner, with its «Sync» actions, above its notice. A
        portfolio's report carries the engine's issues; an asset set's report comes from series
        preparation, which builds none, so the banner could never appear there. They are built here, one
        per category, from the same lists `_data_quality_warnings` words. Names are read once per
        response, and the FX routes only when some report names a pair.
        """
        reports = [item.data_quality for item in items if item.data_quality is not None]
        ids = sorted({asset_id for report in reports for asset_id in _issue_asset_ids(report)})
        names = dict((await self.db.execute(select(Asset.id, Asset.display_name).where(Asset.id.in_(ids)))).all()) if ids else {}
        configured: set[str] = set()
        with_provider: set[str] = set()
        if any(_issue_fx_pairs(report) for report in reports):
            # The portfolio's own reading of the routes, so the two banners split the pairs alike.
            configured, with_provider = await PortfolioService(self.db)._get_configured_fx_pair_sets()
        enriched: list[RiskAnalyticResult] = []
        for item in items:
            if item.data_quality is None:
                enriched.append(item)
                continue
            issues = _data_quality_issues(item.data_quality, names=names, configured_pairs=configured, provider_pairs=with_provider)
            enriched.append(item.model_copy(update={"data_quality": item.data_quality.model_copy(update={"issues": issues})}))
        return enriched

    async def _load_scope_inputs(  # noqa: C901 — scope-variant dispatch + sequential composition validation
        self,
        *,
        user_id: int,
        request: RiskQueryRequest,
    ) -> _ScopeInputs:
        scope = request.scope
        if isinstance(scope, AssetRiskScope):
            return _ScopeInputs(
                requested_asset_ids=(scope.asset_id,),
                weights={},
                asset_values={},
                cash_weight=0,
                scope_value=None,
                portfolio_report=None,
                data_quality=DataQualityReport(),
                warnings=(),
            )
        if isinstance(scope, AssetSetRiskScope):
            return _ScopeInputs(
                requested_asset_ids=tuple(scope.asset_ids),
                weights={},
                asset_values={},
                cash_weight=0,
                scope_value=None,
                portfolio_report=None,
                data_quality=DataQualityReport(),
                warnings=(),
            )

        if not isinstance(scope, PortfolioRiskScope):  # pragma: no cover - discriminated Pydantic union prevents this
            raise TypeError(f"Unsupported risk scope: {type(scope).__name__}")

        accessible_broker_ids = await self._accessible_broker_ids(user_id)
        requested_broker_ids = tuple(scope.broker_ids or ())
        if requested_broker_ids:
            inaccessible_broker_ids = tuple(sorted(set(requested_broker_ids) - set(accessible_broker_ids)))
            if inaccessible_broker_ids:
                broker_list = ", ".join(str(broker_id) for broker_id in inaccessible_broker_ids)
                raise RiskScopeAccessError(f"Broker subset is not fully accessible: {broker_list}")
            effective_broker_ids = requested_broker_ids
            report_broker_ids: Optional[list[int]] = list(effective_broker_ids)
        else:
            effective_broker_ids = accessible_broker_ids
            report_broker_ids = None

        date_end = request.date_range.end or request.date_range.start
        report = await PortfolioService(self.db).get_report(
            user_id=user_id,
            query=PortfolioReportQuery(
                broker_ids=report_broker_ids,
                date_range=OpenDateRangeModel(
                    start=request.date_range.start,
                    end=date_end,
                ),
                target_currency=request.target_currency,
                include_summary=True,
                include_history=True,
                include_allocation_history=False,
                include_breakdown=False,
                include_positions_contribution=False,
            ),
        )
        summary = report.summary
        if summary is None:
            raise RuntimeError("Portfolio report omitted required summary")

        requested_asset_ids = tuple(sorted({holding.asset_id for holding in summary.holdings}))
        warnings: list[RiskWarning] = []
        slice_asset_ids: tuple[int, ...] = ()
        if scope.asset_ids:
            held_asset_ids = set(requested_asset_ids)
            slice_asset_ids = tuple(asset_id for asset_id in scope.asset_ids if asset_id in held_asset_ids)
            if not slice_asset_ids:
                raise RiskScopeNotFoundError(f"No requested asset is held in the selected portfolio scope: {sorted(scope.asset_ids)}")
            unheld_asset_ids = tuple(asset_id for asset_id in scope.asset_ids if asset_id not in held_asset_ids)
            if unheld_asset_ids:
                warnings.append(
                    RiskWarning(
                        code="slice_assets_not_held",
                        message="Some requested assets are not held in the selected portfolio scope and were ignored.",
                        details={"asset_ids": list(unheld_asset_ids)},
                        message_i18n_key="risk.warnings.slice_assets_not_held",
                    )
                )
            requested_asset_ids = slice_asset_ids

        asset_values: dict[int, Decimal] = {asset_id: Decimal("0") for asset_id in requested_asset_ids}
        for holding in summary.holdings:
            if holding.asset_id in asset_values and holding.current_value is not None:
                asset_values[holding.asset_id] += holding.current_value

        # A slice is renormalized to 100% of itself (D59): its denominator is the slice
        # value, not net worth, so monetary outputs stay coherent with its weights.
        scope_value = sum(asset_values.values(), Decimal("0")) if slice_asset_ids else summary.net_worth.amount
        weights: dict[int, float] = {}
        composition_error: Optional[str] = None
        if scope_value > 0:
            weights = {asset_id: float(value / scope_value) for asset_id, value in asset_values.items() if value >= 0}
            if any(value < 0 for value in asset_values.values()):
                composition_error = "Negative asset values are outside the current-composition contract"
        elif requested_asset_ids:
            composition_error = "Current composition requires positive slice value" if slice_asset_ids else "Current composition requires positive scope NAV"

        asset_weight = sum(weights.values())
        if asset_weight > 1 + 1e-9:
            composition_error = "Negative cash or leveraged composition is outside the first-wave contract"
            cash_weight = 0.0
        else:
            cash_weight = max(0.0, 1.0 - asset_weight)

        # A slice carries no cash residual, so the in-transit comparison below — which
        # only describes the zero-return residual of a whole scope — does not apply.
        explicit_cash_weight = float(summary.cash_total.amount / scope_value) if scope_value > 0 else 0.0
        if not slice_asset_ids and summary.in_transit_market_value is not None and summary.in_transit_market_value.amount != 0 and not abs(cash_weight - explicit_cash_weight) < 1e-9:
            warnings.append(
                RiskWarning(
                    code="zero_risk_residual_includes_in_transit",
                    message="The zero-return residual includes in-transit value not represented by an asset return series.",
                    message_i18n_key="risk.warnings.zero_risk_residual_includes_in_transit",
                )
            )

        return _ScopeInputs(
            requested_asset_ids=requested_asset_ids,
            weights=weights,
            asset_values=asset_values,
            cash_weight=cash_weight,
            scope_value=scope_value,
            portfolio_report=report,
            data_quality=report.data_quality or DataQualityReport(),
            warnings=tuple(warnings),
            composition_error=composition_error,
            broker_ids=effective_broker_ids,
            composition_as_of=date_end,
            slice_asset_ids=slice_asset_ids,
        )

    async def _accessible_broker_ids(self, user_id: int) -> tuple[int, ...]:
        result = await self.db.execute(select(BrokerUserAccess.broker_id).where(BrokerUserAccess.user_id == user_id))
        return tuple(sorted(set(result.scalars().all())))

    async def _existing_asset_ids(self, asset_ids: set[int]) -> set[int]:
        if not asset_ids:
            return set()
        result = await self.db.execute(select(Asset.id).where(Asset.id.in_(asset_ids)))
        return set(result.scalars().all())

    async def _never_priced_asset_ids(self, asset_ids: tuple[int, ...]) -> frozenset[int]:
        """The assets among `asset_ids` that no provider is assigned to and no price was ever stored for.

        Nothing will price them, so their missing price is permanent (developer's decision of
        29/09/2026). Both facts are asked in one statement, issued only for a request that excludes
        some asset for a missing price.
        """
        if not asset_ids:
            return frozenset()
        sourced = exists().where(AssetProviderAssignment.asset_id == Asset.id)
        priced = exists().where(PriceHistory.asset_id == Asset.id)
        result = await self.db.execute(select(Asset.id).where(Asset.id.in_(asset_ids), ~sourced, ~priced))
        return frozenset(result.scalars().all())

    async def _load_asset_classifications(
        self,
        asset_ids: tuple[int, ...],
    ) -> dict[int, RiskAssetClassification]:
        if not asset_ids:
            return {}
        result = await self.db.execute(
            select(
                Asset.id,
                Asset.asset_type,
                Asset.classification_params,
            ).where(Asset.id.in_(asset_ids))
        )
        classifications: dict[int, RiskAssetClassification] = {}
        for asset_id, asset_type, raw_classification in result.all():
            parsed: Optional[FAClassificationParams] = None
            metadata_error: Optional[str] = None
            if raw_classification:
                try:
                    parsed = FAClassificationParams.model_validate_json(raw_classification) if isinstance(raw_classification, str) else FAClassificationParams.model_validate(raw_classification)
                except (TypeError, ValueError, ValidationError) as exc:
                    metadata_error = "invalid_classification_metadata"
                    logger.exception(
                        "Invalid asset classification metadata",
                        asset_id=asset_id,
                        error=str(exc),
                    )
            classifications[int(asset_id)] = RiskAssetClassification(
                asset_class=(asset_type.value if hasattr(asset_type, "value") else str(asset_type)),
                sector_exposures=({bucket: float(weight) for bucket, weight in parsed.sector_area.distribution.items()} if parsed is not None and parsed.sector_area is not None else None),
                geography_exposures=({bucket: float(weight) for bucket, weight in parsed.geographic_area.distribution.items()} if parsed is not None and parsed.geographic_area is not None else None),
                metadata_error=metadata_error,
            )
        return classifications

    @staticmethod
    def _geography_group_members() -> dict[str, frozenset[str]]:
        catalog = get_loaded_risk_scenario_catalog()
        return {group.id: frozenset(group.members) for group in catalog.geography_groups}

    async def _prepare_asset_series(
        self,
        *,
        asset_ids: tuple[int, ...],
        date_range: DateRangeModel,
        target_currency: str,
        market_holidays: AbstractSet[date] = frozenset(),
    ) -> PreparedAssetSeriesSet:
        if not asset_ids:
            return prepare_asset_series_set(
                [],
                requested_range=date_range,
                target_currency=target_currency,
                market_holidays=market_holidays,
            )
        date_end = date_range.end or date_range.start
        load_start = date_range.start
        if load_start > date.min:
            load_start -= timedelta(days=1)
        price_results = await AssetSourceManager.get_prices_bulk(
            [
                FAPriceQueryItem(
                    asset_id=asset_id,
                    date_range=DateRangeModel(
                        start=load_start,
                        end=date_end,
                    ),
                    target_currency=target_currency,
                )
                for asset_id in asset_ids
            ],
            self.db,
        )
        return prepare_asset_series_set(
            price_results,
            requested_range=date_range,
            target_currency=target_currency,
            market_holidays=market_holidays,
        )

    async def _prepare_historical_replay_context(
        self,
        *,
        plan: _AnalyticPlan,
        context: RiskExecutionContext,
        scope_inputs: _ScopeInputs,
        existing_asset_ids: set[int],
        target_currency: str,
        market_holidays: AbstractSet[date] = frozenset(),
    ) -> RiskExecutionContext:
        replay_range = getattr(plan.params, "replay_range", None)
        if not isinstance(replay_range, DateRangeModel):
            raise RiskUnavailableError(
                "Historical replay requires a valid replay range",
                code=RiskErrorCode.INVALID_PARAMETERS,
            )

        scope_asset_ids = set(scope_inputs.requested_asset_ids)
        proxy_assets = tuple(getattr(plan.params, "proxy_assets", ()))
        excluded_asset_ids = tuple(getattr(plan.params, "excluded_assets", ()))
        proxy_by_asset = {int(proxy.asset_id): int(proxy.proxy_asset_id) for proxy in proxy_assets}
        referenced_scope_asset_ids = set(proxy_by_asset) | set(excluded_asset_ids)
        outside_scope_asset_ids = sorted(referenced_scope_asset_ids - scope_asset_ids)
        if outside_scope_asset_ids:
            raise RiskUnavailableError(
                "Historical replay options reference assets outside the selected scope",
                code=RiskErrorCode.INVALID_PARAMETERS,
                details={"asset_ids": outside_scope_asset_ids},
            )

        missing_proxy_asset_ids = sorted(set(proxy_by_asset.values()) - existing_asset_ids)
        if missing_proxy_asset_ids:
            raise RiskUnavailableError(
                "One or more historical replay proxy assets do not exist",
                code=RiskErrorCode.INVALID_PARAMETERS,
                details={"proxy_asset_ids": missing_proxy_asset_ids},
            )

        excluded_set = set(excluded_asset_ids)
        candidate_ids = [asset_id for asset_id in scope_inputs.requested_asset_ids if asset_id not in excluded_set]
        # Automatic exclusion (developer's decision of 24/09/2026): an asset the user did not proxy,
        # whose own quotes do not cover the replay window at both ends, takes no part in the replay
        # instead of blocking it. It must be left out before the joint series is prepared: kept
        # in, a late starter moves the joint baseline and shortens the replay of every other asset.
        replay_end = replay_range.end or replay_range.start
        own_ids = [asset_id for asset_id in candidate_ids if asset_id not in proxy_by_asset]
        window_facts = await load_price_window_facts(
            self.db,
            asset_ids=own_ids,
            window_start=replay_range.start,
            window_end=replay_end,
            target_currency=target_currency,
            market_holidays=market_holidays,
        )
        auto_excluded = {asset_id: reason for asset_id in own_ids if (reason := replay_coverage(window_facts[asset_id], replay_range.start, replay_end)) is not None}
        suggested_range, recovers = await self._verified_replay_range(
            facts=window_facts,
            auto_excluded=auto_excluded,
            own_ids=own_ids,
            window=(replay_range.start, replay_end),
            target_currency=target_currency,
            market_holidays=market_holidays,
        )
        source_asset_ids = {asset_id: proxy_by_asset.get(asset_id, asset_id) for asset_id in candidate_ids if asset_id not in auto_excluded}
        prepared = await self._prepare_asset_series(
            asset_ids=tuple(sorted(set(source_asset_ids.values()))),
            date_range=replay_range,
            target_currency=target_currency,
            market_holidays=market_holidays,
        )
        replay_data_quality = _merge_data_quality(
            scope_inputs.data_quality,
            prepared.data_quality,
        )
        return replace(
            context,
            scope_asset_ids=scope_inputs.requested_asset_ids,
            excluded_assets=(),
            execution_warnings=scope_inputs.warnings,
            prepared_data_quality=prepared.data_quality,
            cash_weight=scope_inputs.cash_weight,
            historical_replay=RiskHistoricalReplayContext(
                prepared_series=prepared,
                source_asset_ids=source_asset_ids,
                excluded_asset_ids=tuple(sorted(excluded_asset_ids)),
                data_quality=replay_data_quality,
                auto_excluded_assets=auto_excluded,
                suggested_range=suggested_range,
                suggested_range_recovers=recovers,
            ),
        )

    async def _verified_replay_range(
        self,
        *,
        facts: dict[int, PriceWindowFacts],
        auto_excluded: dict[int, RiskHistoricalReplayExclusionReason],
        own_ids: list[int],
        window: tuple[date, date],
        target_currency: str,
        market_holidays: AbstractSet[date] = frozenset(),
    ) -> tuple[Optional[DateRangeModel], tuple[int, ...]]:
        """A part of the replay window that brings back the assets its edges exclude.

        Proposed only when a second reading of the facts confirms it: every asset it recovers, and
        every asset already covered, is priced at both of its ends. Assets excluded for other reasons
        stay out of the check, since no shorter window brings them back.
        """
        proposal = suggested_replay_range(facts, auto_excluded, window[0], window[1])
        if proposal is None:
            return None, ()
        (start, end), recovers = proposal
        kept = [asset_id for asset_id in own_ids if asset_id not in auto_excluded or asset_id in recovers]
        check = await load_price_window_facts(self.db, asset_ids=kept, window_start=start, window_end=end, target_currency=target_currency, market_holidays=market_holidays)
        if any(replay_coverage(check[asset_id], start, end) is not None for asset_id in kept):
            return None, ()
        return DateRangeModel(start=start, end=end), recovers

    def _build_context(
        self,
        *,
        request: RiskQueryRequest,
        scope_inputs: _ScopeInputs,
        prepared: PreparedAssetSeriesSet,
        never_priced_asset_ids: frozenset[int] = frozenset(),
    ) -> RiskExecutionContext:
        prepared_by_asset = {item.returns.asset_id: item for item in prepared.series if item.returns.points}
        usable_scope_asset_ids = tuple(asset_id for asset_id in scope_inputs.requested_asset_ids if asset_id in prepared_by_asset)
        excluded_assets = _scope_exclusions(scope_inputs.requested_asset_ids, prepared, never_priced_asset_ids)
        data_quality = _merge_data_quality(
            scope_inputs.data_quality,
            prepared.data_quality,
        )
        execution_warnings = list(scope_inputs.warnings)
        execution_warnings.extend(_assets_excluded_warnings(excluded_assets))

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
            ) = _portfolio_twrr_returns(
                scope_inputs.portfolio_report,
                observation_dates=_held_quote_dates(prepared, scope_inputs.requested_asset_ids),
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
            scope_reference=_scope_reference(
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

    @staticmethod
    def _available_observations(
        plan: _AnalyticPlan,
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

    @staticmethod
    def _requires_valid_composition(
        plan: _AnalyticPlan,
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

    def _success(
        self,
        *,
        plan: _AnalyticPlan,
        context: RiskExecutionContext,
        computation: RiskComputation,
    ) -> RiskAnalyticResult:
        data_quality = self._data_quality(plan, context)
        context_warnings = context.execution_warnings
        context_exclusions = context.excluded_assets
        if _is_hypothetical_plan(plan):
            context_warnings = tuple(warning for warning in context_warnings if warning.code != "assets_excluded")
            context_exclusions = ()
        elif _reads_the_twrr_alone(plan, context):
            context_warnings = tuple(warning for warning in context_warnings if warning.code not in _COMPOSITION_WARNING_CODES)
            context_exclusions = ()
        warnings = _dedupe_warnings(
            (
                *context_warnings,
                *computation.warnings,
            )
        )
        if data_quality.data_quality_status != DataQualityStatus.OK:
            warnings = _dedupe_warnings((*warnings, *_data_quality_warnings(data_quality)))
        status = RiskResultStatus.PARTIAL if any(warning.degrades_result for warning in warnings) or context_exclusions or computation.excluded_assets or data_quality.data_quality_status != DataQualityStatus.OK else RiskResultStatus.OK
        return RiskAnalyticResult(
            instance_id=plan.request.instance_id,
            analytic_code=plan.request.analytic_code,
            status=status,
            output=computation.output,
            metadata=self._metadata(
                plan,
                context,
                computation=computation,
            ),
            data_quality=data_quality,
            warnings=list(warnings),
        )

    @staticmethod
    def _data_quality(
        plan: _AnalyticPlan,
        context: RiskExecutionContext,
    ) -> DataQualityReport:
        if _is_historical_replay_plan(plan) and context.historical_replay is not None:
            return context.historical_replay.data_quality
        if _is_hypothetical_plan(plan):
            if context.scope_kind == RiskScopeKind.PORTFOLIO and context.portfolio_data_quality is not None:
                return context.portfolio_data_quality
            return DataQualityReport()
        if context.primary_return_basis == RiskReturnBasis.TWRR and context.portfolio_data_quality is not None:
            # Judged on the series it consumed. The TWRR is the portfolio's own, so its report is the
            # whole story for a PRIMARY reader. A benchmark is prepared on the scope's joint calendar,
            # which the assets excluded from the scope never entered: their entries are not its own.
            series_inputs = plan.analytic_class.series_inputs
            if series_inputs == RiskSeriesInputs.PRIMARY:
                return context.portfolio_data_quality
            if series_inputs == RiskSeriesInputs.PRIMARY_AND_BENCHMARK and context.prepared_data_quality is not None:
                benchmark_asset_id = getattr(plan.params, "comparison_asset_id", None)
                foreign_asset_ids = {item.asset_id for item in context.excluded_assets} - {benchmark_asset_id}
                prepared = context.prepared_data_quality
                return _merge_data_quality(
                    context.portfolio_data_quality,
                    prepared.model_copy(update={"unusable_assets": [item for item in prepared.unusable_assets if item.asset_id not in foreign_asset_ids]}),
                )
        return context.data_quality

    @staticmethod
    def _metadata(
        plan: _AnalyticPlan,
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

        analyzed_range = computation.analyzed_range if computation is not None and computation.analyzed_range is not None else _context_analyzed_range(context)
        context_exclusions = () if _is_hypothetical_plan(plan) or _reads_the_twrr_alone(plan, context) else context.excluded_assets
        computation_exclusions = computation.excluded_assets if computation is not None else ()
        exclusions = _dedupe_exclusions(
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

    @staticmethod
    def _unavailable(
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


def _held_quote_dates(prepared: PreparedAssetSeriesSet, held_asset_ids: tuple[int, ...]) -> frozenset[date]:
    """The days on which at least one held asset has a quote of its own — a benchmark's quotes don't count."""
    held = set(held_asset_ids)
    return frozenset(quote_date for series in prepared.series if series.returns.asset_id in held for quote_date in series.quote_dates)


def _portfolio_twrr_returns(
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

    The report has one TWRR point per calendar day, so a day on which nothing held was quoted is a
    zero return that no market produced. With `observation_dates` — the days a held asset was quoted —
    only those points are kept after the baseline, and each return is chain-linked from the cumulative
    TWRR across the days dropped, so the TWRR stays exact; coverage is then measured against those
    days, not against the calendar. With none (nothing held has a quote), every calendar day is kept.
    """
    if report is None or not report.history:
        return None, (), (), 0, None, 0.0
    points = [point for point in report.history if point.twrr is not None]
    if observation_dates:
        points = points[:1] + [point for point in points[1:] if point.date in observation_dates]
    if len(points) < 2:
        return None, (), (), 0, None, 0.0
    cumulative = [float(point.twrr) for point in points]
    returns = tuple(period_returns_from_cumulative(cumulative))
    return_dates = tuple(point.date for point in points[1:])
    baseline = points[0].date
    calendar_days = (return_dates[-1] - baseline).days
    annualization_factor = len(returns) * 365 / calendar_days if calendar_days > 0 else None
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


def _scope_reference(
    request: RiskQueryRequest,
    *,
    broker_ids: tuple[int, ...] = (),
    slice_asset_ids: tuple[int, ...] = (),
) -> str:
    scope = request.scope
    if isinstance(scope, AssetRiskScope):
        return f"asset:{scope.asset_id}"
    if isinstance(scope, AssetSetRiskScope):
        return "asset_set:" + ",".join(str(asset_id) for asset_id in scope.asset_ids)
    suffix = ",".join(str(broker_id) for broker_id in broker_ids) or "none"
    reference = f"portfolio:{suffix}"
    if slice_asset_ids:
        reference += "/assets:" + ",".join(str(asset_id) for asset_id in sorted(slice_asset_ids))
    return reference


def _context_analyzed_range(
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


def _is_historical_replay_plan(plan: _AnalyticPlan) -> bool:
    return plan.request.analytic_code == "stress" and getattr(plan.params, "method", None) == RiskStressMethod.HISTORICAL_REPLAY


def _is_hypothetical_plan(plan: _AnalyticPlan) -> bool:
    return plan.request.analytic_code == "stress" and getattr(plan.params, "method", None) == RiskStressMethod.HYPOTHETICAL


def _is_geography_hypothetical_plan(plan: _AnalyticPlan) -> bool:
    return _is_hypothetical_plan(plan) and getattr(getattr(plan, "params", None), "dimension", None).value == "geography"


# What the scope says about its per-asset composition: the assets left without a series, and a
# zero-return residual that includes value in transit. Neither enters the portfolio TWRR.
_COMPOSITION_WARNING_CODES = frozenset({"assets_excluded", "zero_risk_residual_includes_in_transit"})


def _reads_the_twrr_alone(plan: _AnalyticPlan, context: RiskExecutionContext) -> bool:
    """Whether the analytic reads the portfolio TWRR and no scope asset series (developer's decision of 29/09/2026).

    The TWRR already values every holding, so such a result loses nothing when a scope asset has no
    series of its own, and does not inherit the scope's exclusions.
    """
    return context.primary_return_basis == RiskReturnBasis.TWRR and plan.analytic_class.series_inputs != RiskSeriesInputs.SCOPE_ASSETS


def _scope_exclusions(
    scope_asset_ids: tuple[int, ...],
    prepared: PreparedAssetSeriesSet,
    never_priced_asset_ids: frozenset[int] = frozenset(),
) -> tuple[RiskExcludedAsset, ...]:
    """The scope assets left without a return series, each with the reason the preparation recorded.

    `insufficient_history` when it recorded none: the asset has prices, but no return series came out
    of them. A missing price is `no_price_source` for an asset nothing has ever priced — a permanent
    state, where `missing_price` is an occasional one.
    """
    usable_asset_ids = {item.returns.asset_id for item in prepared.series if item.returns.points}
    recorded = {item.asset_id: item.reason.value for item in prepared.data_quality.unusable_assets}
    exclusions: list[RiskExcludedAsset] = []
    for asset_id in scope_asset_ids:
        if asset_id in usable_asset_ids:
            continue
        reason = recorded.get(asset_id, "insufficient_history")
        if reason == DataQualityExclusionReason.MISSING_PRICE and asset_id in never_priced_asset_ids:
            reason = "no_price_source"
        exclusions.append(RiskExcludedAsset(asset_id=asset_id, reason=reason))
    return tuple(exclusions)


def _warning_asset_ids(warning: RiskWarning) -> list[int]:
    """The assets a warning is about, from `details.asset_ids` or a single `details.asset_id`."""
    raw = warning.details.get("asset_ids")
    if raw is None and "asset_id" in warning.details:
        raw = [warning.details["asset_id"]]
    return [asset_id for asset_id in (raw or []) if isinstance(asset_id, int) and not isinstance(asset_id, bool)]


def _assets_excluded_warnings(excluded_assets: tuple[RiskExcludedAsset, ...]) -> list[RiskWarning]:
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


_PRICE_EXCLUSION_REASONS = frozenset({DataQualityExclusionReason.MISSING_PRICE.value, "no_price_source"})


def _stale_price_ids(data_quality: DataQualityReport) -> list[int]:
    return sorted({item.asset_id for item in data_quality.stale_prices} | set(data_quality.carried_forward_price_asset_ids))


def _missing_price_ids(data_quality: DataQualityReport) -> list[int]:
    unusable = {item.asset_id for item in data_quality.unusable_assets if str(item.reason) in _PRICE_EXCLUSION_REASONS}
    return sorted({item.asset_id for item in data_quality.missing_price_assets} | unusable)


def _issue_asset_ids(data_quality: DataQualityReport) -> set[int]:
    return set(_stale_price_ids(data_quality)) | set(_missing_price_ids(data_quality))


def _issue_fx_pairs(data_quality: DataQualityReport) -> list[str]:
    """Every pair the report names, as the slug the FX pages and the banner's actions use."""
    raw = [*data_quality.unresolved_fx_pairs, *(item.pair for item in data_quality.missing_fx_pairs), *data_quality.carried_forward_fx_pairs]
    return sorted({PortfolioService._normalize_fx_pair_slug(pair) for pair in raw})


def _asset_issue(code: IssueCode, severity: IssueSeverity, *, message_i18n_key: str, action: str, group_key: str, ids: list[int], names: dict[int, str]) -> DataQualityIssue:
    return DataQualityIssue(
        domain=IssueDomain.ASSET,
        code=code,
        severity=severity,
        message_i18n_key=message_i18n_key,
        message_params={"count": len(ids)},
        count=len(ids),
        affected_asset_ids=ids,
        affected_asset_names=[names.get(asset_id, f"#{asset_id}") for asset_id in ids],
        cta_action=action,
        cta_target=str(ids[0]),
        group_key=group_key,
    )


def _fx_issue(code: IssueCode, *, message_i18n_key: str, action: str, group_key: str, pairs: list[str], target: bool, extra: dict | None = None) -> DataQualityIssue:
    return DataQualityIssue(
        domain=IssueDomain.FOREX,
        code=code,
        severity=IssueSeverity.WARNING,
        message_i18n_key=message_i18n_key,
        message_params={"count": len(pairs), **(extra or {})},
        count=len(pairs),
        affected_fx_pairs=pairs,
        cta_action=action,
        cta_target=pairs[0] if target else None,
        group_key=group_key,
    )


def _data_quality_issues(data_quality: DataQualityReport, *, names: dict[int, str], configured_pairs: AbstractSet[str], provider_pairs: AbstractSet[str]) -> list[DataQualityIssue]:
    """The banner's issues for an asset set's report: one per category, `code + group_key` unique.

    The categories and their actions are the portfolio engine's, so the lab's banner reads like the
    Dashboard's: stale prices sync, a missing price opens the asset, a pair with no route asks for one,
    a pair with a provider syncs, a manual pair opens the pair. The sentences are the lab's own where the
    portfolio's speak of a NAV or of dates this report does not carry.
    """
    issues: list[DataQualityIssue] = []
    stale = _stale_price_ids(data_quality)
    if stale:
        issues.append(_asset_issue(IssueCode.STALE_PRICE, IssueSeverity.WARNING, message_i18n_key="dataQuality.stalePrice", action="sync_asset_prices", group_key="stale_price", ids=stale, names=names))
    missing = _missing_price_ids(data_quality)
    if missing:
        issues.append(_asset_issue(IssueCode.MISSING_PRICE, IssueSeverity.ERROR, message_i18n_key="risk.quality.missingPrice", action="navigate_asset", group_key="missing_price", ids=missing, names=names))
    pairs = _issue_fx_pairs(data_quality)
    no_route = [pair for pair in pairs if pair not in configured_pairs]
    synced = [pair for pair in pairs if pair in configured_pairs and pair in provider_pairs]
    manual = [pair for pair in pairs if pair in configured_pairs and pair not in provider_pairs]
    if no_route:
        issues.append(_fx_issue(IssueCode.MISSING_FX_MARKET, message_i18n_key="risk.quality.missingFx", action="add_fx_pair", group_key="missing_fx", pairs=no_route, target=False))
    if synced:
        issues.append(_fx_issue(IssueCode.MISSING_FX_RATES, message_i18n_key="risk.quality.missingFxRates", action="sync_fx_pair", group_key="missing_fx_rates", pairs=synced, target=True, extra={"days": STALE_PRICE_THRESHOLD_DAYS}))
    if manual:
        issues.append(_fx_issue(IssueCode.MISSING_FX_RATES, message_i18n_key="risk.quality.missingFxRatesManual", action="navigate_fx", group_key="missing_fx_rates_manual", pairs=manual, target=True))
    return issues


def _data_quality_warnings(data_quality: DataQualityReport) -> list[RiskWarning]:
    """One `data_quality_degraded` warning per cause, each naming what is affected.

    Excluded assets are not repeated here: `assets_excluded` already names them. A degraded report
    with none of the causes below still says so, in a generic sentence.
    """
    code = "data_quality_degraded"
    message = "Risk result uses incomplete or carried-forward source data."
    status = data_quality.data_quality_status.value
    warnings: list[RiskWarning] = []
    stale_ids = sorted({item.asset_id for item in data_quality.stale_prices} | set(data_quality.carried_forward_price_asset_ids))
    if stale_ids:
        warnings.append(RiskWarning(code=code, message=message, details={"status": status, "cause": "stale_prices", "asset_ids": stale_ids}, message_i18n_key="risk.warnings.data_quality_stale_prices", message_params={"days": STALE_PRICE_THRESHOLD_DAYS}))
    if data_quality.carried_forward_fx_pairs:
        pairs = sorted(data_quality.carried_forward_fx_pairs)
        warnings.append(RiskWarning(code=code, message=message, details={"status": status, "cause": "stale_fx_rates", "pairs": pairs}, message_i18n_key="risk.warnings.data_quality_stale_fx_rates", message_params={"days": STALE_PRICE_THRESHOLD_DAYS, "pairs": ", ".join(pairs)}))
    missing_ids = sorted({item.asset_id for item in data_quality.missing_price_assets})
    if missing_ids:
        warnings.append(RiskWarning(code=code, message=message, details={"status": status, "cause": "missing_prices", "asset_ids": missing_ids}, message_i18n_key="risk.warnings.data_quality_missing_prices"))
    fx_pairs = sorted(set(data_quality.unresolved_fx_pairs) | {item.pair for item in data_quality.missing_fx_pairs})
    if fx_pairs:
        warnings.append(RiskWarning(code=code, message=message, details={"status": status, "cause": "missing_fx_rates", "pairs": fx_pairs}, message_i18n_key="risk.warnings.data_quality_missing_fx_rates", message_params={"pairs": ", ".join(fx_pairs)}))
    incomplete_dates = set(data_quality.incomplete_nav_dates) | set(data_quality.incomplete_book_value_dates) | set(data_quality.incomplete_allocation_dates) | set(data_quality.incomplete_valuation_dates)
    if incomplete_dates:
        warnings.append(RiskWarning(code=code, message=message, details={"status": status, "cause": "incomplete_dates", "count": len(incomplete_dates)}, message_i18n_key="risk.warnings.data_quality_incomplete_dates", message_params={"count": len(incomplete_dates)}))
    if not warnings and not data_quality.unusable_assets:
        warnings.append(RiskWarning(code=code, message=message, details={"status": status}, message_i18n_key="risk.warnings.data_quality_degraded"))
    return warnings


def _dedupe_warnings(
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


def _dedupe_exclusions(
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


def _merge_data_quality(
    left: DataQualityReport,
    right: DataQualityReport,
) -> DataQualityReport:
    payload: dict[str, object] = {}
    for field_name in DataQualityReport.model_fields:
        left_value = getattr(left, field_name)
        right_value = getattr(right, field_name)
        if isinstance(left_value, int):
            payload[field_name] = left_value + right_value
            continue
        combined = [*left_value, *right_value]
        seen: set[str] = set()
        deduped = []
        for item in combined:
            if isinstance(item, BaseModel):
                key = item.model_dump_json()
            else:
                key = json.dumps(item, default=str, sort_keys=True)
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        payload[field_name] = deduped
    return DataQualityReport.model_validate(payload)


__all__ = [
    "RiskScopeAccessError",
    "RiskScopeNotFoundError",
    "RiskService",
]
