"""Bulk orchestration for deterministic risk analytics."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, BrokerUserAccess
from backend.app.logging_config import get_logger
from backend.app.schemas.common import DateRangeModel, OpenDateRangeModel
from backend.app.schemas.portfolio import (
    DataQualityReport,
    DataQualityStatus,
    PortfolioReportQuery,
    PortfolioReportResponse,
)
from backend.app.schemas.prices import FAPriceQueryItem
from backend.app.schemas.risk import (
    AssetRiskScope,
    AssetSetRiskScope,
    BrokerRiskScope,
    PortfolioRiskScope,
    PreparedAssetSeriesSet,
    RiskAnalyticRequest,
    RiskAnalyticResult,
    RiskError,
    RiskErrorCode,
    RiskExcludedAsset,
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
from backend.app.services.portfolio_service import PortfolioService
from backend.app.services.provider_registry import RiskAnalyticRegistry
from backend.app.services.risk.base import (
    RiskAnalytic,
    RiskComputation,
    RiskExecutionContext,
    RiskUnavailableError,
)
from backend.app.services.risk.metrics import (
    current_buy_and_hold_returns,
    period_returns_from_cumulative,
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


class RiskService:
    """Resolve one scope and execute multiple DB-free analytics in isolation."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def catalog():
        return RiskAnalyticRegistry.list_definitions()

    async def execute(
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
        dependency_asset_ids = {int(comparison_asset_id) for plan in plans.values() if (comparison_asset_id := getattr(plan.params, "comparison_asset_id", None)) is not None}
        existing_asset_ids = await self._existing_asset_ids(set(scope_inputs.requested_asset_ids) | dependency_asset_ids)
        missing_scope_asset_ids = set(scope_inputs.requested_asset_ids) - existing_asset_ids
        if missing_scope_asset_ids:
            raise RiskScopeNotFoundError(f"Unknown asset IDs in risk scope: {sorted(missing_scope_asset_ids)}")

        prepared = await self._prepare_asset_series(
            asset_ids=tuple(sorted(set(scope_inputs.requested_asset_ids) | (dependency_asset_ids & existing_asset_ids))),
            request=request,
        )
        context = self._build_context(
            request=request,
            scope_inputs=scope_inputs,
            prepared=prepared,
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
            observations = self._available_observations(plan, context)
            if observations is not None and observations < plan.analytic_class.min_observations:
                results[index] = self._unavailable(
                    plan.request,
                    RiskErrorCode.INSUFFICIENT_HISTORY,
                    f"Analytic '{plan.request.analytic_code}' requires at least {plan.analytic_class.min_observations} observations",
                    details={
                        "observations": observations,
                        "required": plan.analytic_class.min_observations,
                    },
                    metadata=self._metadata(plan, context),
                    data_quality=self._data_quality(plan, context),
                )
                continue
            try:
                computation = await asyncio.to_thread(
                    plan.analytic.compute,
                    plan.params,
                    context,
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
            except (ValueError, ArithmeticError) as exc:
                results[index] = self._unavailable(
                    plan.request,
                    RiskErrorCode.UNDEFINED_METRIC,
                    str(exc),
                    metadata=self._metadata(plan, context),
                    data_quality=self._data_quality(plan, context),
                )
                continue
            except Exception as exc:  # pragma: no cover - defensive isolation boundary
                logger.exception(
                    "Risk analytic execution failed",
                    analytic_code=plan.request.analytic_code,
                    error_type=type(exc).__name__,
                )
                results[index] = RiskAnalyticResult(
                    instance_id=plan.request.instance_id,
                    analytic_code=plan.request.analytic_code,
                    status=RiskResultStatus.FAILED,
                    metadata=self._metadata(plan, context),
                    data_quality=self._data_quality(plan, context),
                    error=RiskError(
                        code=RiskErrorCode.EXECUTION_FAILED,
                        message="Risk analytic execution failed",
                        details={"error_type": type(exc).__name__},
                    ),
                )
                continue
            results[index] = self._success(
                plan=plan,
                context=context,
                computation=computation,
            )

        return RiskQueryResponse(items=[results[index] for index in range(len(request.analytics))])

    async def _load_scope_inputs(
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

        broker_ids: Optional[list[int]]
        if isinstance(scope, BrokerRiskScope):
            access_stmt = select(BrokerUserAccess.id).where(
                BrokerUserAccess.user_id == user_id,
                BrokerUserAccess.broker_id == scope.broker_id,
            )
            if (await self.db.execute(access_stmt)).scalar_one_or_none() is None:
                raise RiskScopeAccessError(f"Broker {scope.broker_id} is not accessible")
            broker_ids = [scope.broker_id]
        elif isinstance(scope, PortfolioRiskScope):
            broker_ids = None
        else:  # pragma: no cover - discriminated Pydantic union prevents this
            raise TypeError(f"Unsupported risk scope: {type(scope).__name__}")

        date_end = request.date_range.end or request.date_range.start
        report = await PortfolioService(self.db).get_report(
            user_id=user_id,
            query=PortfolioReportQuery(
                broker_ids=broker_ids,
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
        asset_values: dict[int, Decimal] = {asset_id: Decimal("0") for asset_id in requested_asset_ids}
        for holding in summary.holdings:
            if holding.current_value is not None:
                asset_values[holding.asset_id] += holding.current_value

        scope_value = summary.net_worth.amount
        weights: dict[int, float] = {}
        composition_error: Optional[str] = None
        if scope_value > 0:
            weights = {asset_id: float(value / scope_value) for asset_id, value in asset_values.items() if value >= 0}
            if any(value < 0 for value in asset_values.values()):
                composition_error = "Negative asset values are outside the current-composition contract"
        elif requested_asset_ids:
            composition_error = "Current composition requires positive scope NAV"

        asset_weight = sum(weights.values())
        if asset_weight > 1 + 1e-9:
            composition_error = "Negative cash or leveraged composition is outside the first-wave contract"
            cash_weight = 0.0
        else:
            cash_weight = max(0.0, 1.0 - asset_weight)

        warnings: list[RiskWarning] = []
        explicit_cash_weight = float(summary.cash_total.amount / scope_value) if scope_value > 0 else 0.0
        if summary.in_transit_market_value is not None and summary.in_transit_market_value.amount != 0 and not abs(cash_weight - explicit_cash_weight) < 1e-9:
            warnings.append(
                RiskWarning(
                    code="zero_risk_residual_includes_in_transit",
                    message="The zero-return residual includes in-transit value not represented by an asset return series.",
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
        )

    async def _existing_asset_ids(self, asset_ids: set[int]) -> set[int]:
        if not asset_ids:
            return set()
        result = await self.db.execute(select(Asset.id).where(Asset.id.in_(asset_ids)))
        return set(result.scalars().all())

    async def _prepare_asset_series(
        self,
        *,
        asset_ids: tuple[int, ...],
        request: RiskQueryRequest,
    ) -> PreparedAssetSeriesSet:
        date_end = request.date_range.end or request.date_range.start
        load_start = request.date_range.start
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
                    target_currency=request.target_currency,
                )
                for asset_id in asset_ids
            ],
            self.db,
        )
        return prepare_asset_series_set(
            price_results,
            requested_range=request.date_range,
            target_currency=request.target_currency,
        )

    def _build_context(
        self,
        *,
        request: RiskQueryRequest,
        scope_inputs: _ScopeInputs,
        prepared: PreparedAssetSeriesSet,
    ) -> RiskExecutionContext:
        prepared_by_asset = {item.returns.asset_id: item for item in prepared.series if item.returns.points}
        usable_scope_asset_ids = tuple(asset_id for asset_id in scope_inputs.requested_asset_ids if asset_id in prepared_by_asset)
        unusable_reasons = {item.asset_id: item.reason.value for item in prepared.data_quality.unusable_assets}
        excluded_assets = tuple(
            RiskExcludedAsset(
                asset_id=asset_id,
                reason=unusable_reasons.get(asset_id, "insufficient_history"),
            )
            for asset_id in scope_inputs.requested_asset_ids
            if asset_id not in usable_scope_asset_ids
        )
        data_quality = _merge_data_quality(
            scope_inputs.data_quality,
            prepared.data_quality,
        )
        execution_warnings = list(scope_inputs.warnings)
        if excluded_assets:
            execution_warnings.append(
                RiskWarning(
                    code="assets_excluded",
                    message="One or more scope assets were excluded from risk calculations.",
                    details={"asset_ids": [item.asset_id for item in excluded_assets]},
                )
            )

        primary_baseline_date: Optional[date] = None
        primary_return_dates: tuple[date, ...] = ()
        primary_returns: tuple[float, ...] = ()
        primary_return_basis = RiskReturnBasis.PRICE_ONLY
        annualization_factor = prepared.annualization_factor
        calendar_days = prepared.calendar_days
        coverage = prepared.calendar_coverage

        if (
            request.scope.kind
            in {
                RiskScopeKind.PORTFOLIO,
                RiskScopeKind.BROKER,
            }
            and request.mode == RiskMode.HISTORICAL
        ):
            (
                primary_baseline_date,
                primary_return_dates,
                primary_returns,
                calendar_days,
                annualization_factor,
                coverage,
            ) = _portfolio_twrr_returns(scope_inputs.portfolio_report)
            primary_return_basis = RiskReturnBasis.TWRR
        elif request.scope.kind in {
            RiskScopeKind.PORTFOLIO,
            RiskScopeKind.BROKER,
        }:
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
            scope_reference=_scope_reference(request),
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
            scope_value=scope_inputs.scope_value,
        )

    @staticmethod
    def _available_observations(
        plan: _AnalyticPlan,
        context: RiskExecutionContext,
    ) -> Optional[int]:
        if plan.request.analytic_code == "correlation":
            return None
        if plan.request.analytic_code == "risk_contribution":
            return context.prepared_series.n_observations if context.prepared_series is not None else 0
        if plan.request.analytic_code == "stress":
            if getattr(plan.params, "method", None) == RiskStressMethod.HYPOTHETICAL:
                return None
            return context.prepared_series.n_observations if context.prepared_series is not None else 0
        return context.n_observations

    @staticmethod
    def _requires_valid_composition(
        plan: _AnalyticPlan,
        context: RiskExecutionContext,
    ) -> bool:
        if context.mode != RiskMode.CURRENT_COMPOSITION:
            return False
        if context.scope_kind not in {
            RiskScopeKind.PORTFOLIO,
            RiskScopeKind.BROKER,
        }:
            return False
        return plan.request.analytic_code in {
            "risk_contribution",
            "stress",
            "comparison",
            "historical_var",
        }

    def _success(
        self,
        *,
        plan: _AnalyticPlan,
        context: RiskExecutionContext,
        computation: RiskComputation,
    ) -> RiskAnalyticResult:
        data_quality = self._data_quality(plan, context)
        warnings = _dedupe_warnings(
            (
                *context.execution_warnings,
                *computation.warnings,
            )
        )
        if data_quality.data_quality_status != DataQualityStatus.OK:
            warnings = _dedupe_warnings(
                (
                    *warnings,
                    RiskWarning(
                        code="data_quality_degraded",
                        message="Risk result uses incomplete or carried-forward source data.",
                        details={"status": data_quality.data_quality_status.value},
                    ),
                )
            )
        status = RiskResultStatus.PARTIAL if warnings or context.excluded_assets or data_quality.data_quality_status != DataQualityStatus.OK else RiskResultStatus.OK
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
        if (
            context.mode == RiskMode.HISTORICAL
            and context.scope_kind
            in {
                RiskScopeKind.PORTFOLIO,
                RiskScopeKind.BROKER,
            }
            and plan.request.analytic_code
            in {
                "portfolio_kpi",
                "historical_var",
            }
            and context.portfolio_data_quality is not None
        ):
            return context.portfolio_data_quality
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
        computation_exclusions = computation.excluded_assets if computation is not None else ()
        exclusions = _dedupe_exclusions(
            (
                *context.excluded_assets,
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
            method=computation.method if computation is not None else None,
            params=plan.params.model_dump(mode="json"),
            mode=context.mode,
            composition_policy=context.composition_policy,
            return_basis=(computation.return_basis if computation is not None and computation.return_basis is not None else context.primary_return_basis),
            comparison_asset_id=(computation.comparison_asset_id if computation is not None else getattr(plan.params, "comparison_asset_id", None)),
            risk_free=computation.risk_free if computation is not None else None,
            excluded_assets=list(exclusions),
            algorithm_version=plan.analytic_class.algorithm_version,
            computed_at=datetime.now(UTC),
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


def _portfolio_twrr_returns(
    report: Optional[PortfolioReportResponse],
) -> tuple[
    Optional[date],
    tuple[date, ...],
    tuple[float, ...],
    int,
    Optional[float],
    float,
]:
    if report is None or not report.history:
        return None, (), (), 0, None, 0.0
    points = [point for point in report.history if point.twrr is not None]
    if len(points) < 2:
        return None, (), (), 0, None, 0.0
    cumulative = [float(point.twrr) for point in points]
    returns = tuple(period_returns_from_cumulative(cumulative))
    return_dates = tuple(point.date for point in points[1:])
    baseline = points[0].date
    calendar_days = (return_dates[-1] - baseline).days
    annualization_factor = len(returns) * 365 / calendar_days if calendar_days > 0 else None
    coverage = min(1.0, len(returns) / calendar_days) if calendar_days > 0 else 0.0
    return (
        baseline,
        return_dates,
        returns,
        calendar_days,
        annualization_factor,
        coverage,
    )


def _scope_reference(request: RiskQueryRequest) -> str:
    scope = request.scope
    if isinstance(scope, AssetRiskScope):
        return f"asset:{scope.asset_id}"
    if isinstance(scope, AssetSetRiskScope):
        return "asset_set:" + ",".join(str(asset_id) for asset_id in scope.asset_ids)
    if isinstance(scope, BrokerRiskScope):
        return f"broker:{scope.broker_id}"
    return "portfolio"


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
