"""Isolated AI Export drawdown context components (Portfolio / Broker / Asset).

These components expose the canonical Risk `drawdown_summary` analytic as an
optional, honestly-typed AI Export section so drawdown-aware analyses
(``portfolio.rebalancing``, ``broker.review``, ``asset.position_review``) can
reason about the current and maximum peak-relative decline without re-deriving
any math. Every payload is produced by delegating to
``RiskService.execute(... drawdown_summary ...)``: the drawdown magnitudes,
episode dates and coverage are **never** recomputed here and **never** derived
from AI Export NAV buckets.

Scope/basis rules (see the ``ai-adequacy-v1-drawdown-export`` design):

- Drawdown is computed over the FULL available history (E1, 02/09): an export
  for an AI must carry the true historical peak, never a window-relative one.
  The requested start is ignored — ASSET scope loads from ``date.min`` (price
  loads are sparse-safe), PORTFOLIO scope from the user's earliest accessible
  transaction (the engine emits one history point per day in the range).

- ``portfolio.drawdown_summary``: Risk ``PortfolioRiskScope`` with
  ``broker_ids=None`` (whole portfolio) in the ``BuildScope`` target currency;
  the Risk service resolves this to a TWRR / ``historical_twrr`` basis.
- ``broker.drawdown_summary``: Risk ``PortfolioRiskScope`` restricted to the
  exact selected broker ID(s) (``BuildScope.broker_scope``), also TWRR /
  ``historical_twrr``.
- ``asset.drawdown_summary``: Risk ``AssetRiskScope`` computed in the asset's
  **native observed price currency** (declared dependency on
  ``asset.market_snapshot`` -> ``observed.native_price.code``) so the basis
  matches the technical native ``price_only`` / ``price_only_close`` semantics -
  never blindly the portfolio target currency. When no native observation
  exists, an explicit ``unavailable`` payload is returned rather than any
  approximation.

If the Risk result is ``unavailable``/``failed`` (or the whole call raises), the
component still builds an honest ``unavailable``/``failed`` payload carrying a
machine-readable ``reason_code`` and message so an *optional* analysis section
never fails - there is deliberately no success-shaped fallback.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date as Date
from enum import StrEnum

from pydantic import Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.common import DateRangeModel, OpenDateRangeModel, StrictModel
from backend.app.schemas.portfolio import DataQualityStatus
from backend.app.schemas.risk import (
    AssetRiskScope,
    PortfolioRiskScope,
    RiskAnalyticRequest,
    RiskAnalyticResult,
    RiskDrawdownOutput,
    RiskDrawdownRecoveryStatus,
    RiskMode,
    RiskQueryRequest,
    RiskResultStatus,
    RiskScopeKind,
)
from backend.app.services.ai_export.components.asset_payloads import AssetMarketSnapshotPayload
from backend.app.services.ai_export.components.envelope import SectionEnvelope
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.technical_shared import (
    PORTFOLIO_TECHNICAL_UNIVERSE_KWARGS,
    coherent_price_currency,
    load_technical_universe_bundle,
)
from backend.app.services.ai_export.components.types import BuildScope, Domain, PeriodBehavior, ResourceKey
from backend.app.services.ai_export.dependencies import BuildContext, ResourceLoadError
from backend.app.services.date_sentinel import resolve_date_sentinels
from backend.app.services.risk.metrics import drawdown_episodes
from backend.app.services.risk.service import RiskService

# Canonical Risk analytic delegated to by every drawdown context component.
_DRAWDOWN_ANALYTIC_CODE = "drawdown_summary"
_DRAWDOWN_INSTANCE_ID = "ai_export_drawdown_context"

# One request-scoped cached Risk result per domain: `BuildContext.db_resource`
# guarantees the underlying `RiskService.execute` runs at most once per request.
_PORTFOLIO_DRAWDOWN_RESULT_RESOURCE: ResourceKey[RiskAnalyticResult] = ResourceKey("portfolio.drawdown_summary_result", RiskAnalyticResult)
_BROKER_DRAWDOWN_RESULT_RESOURCE: ResourceKey[RiskAnalyticResult] = ResourceKey("broker.drawdown_summary_result", RiskAnalyticResult)
_ASSET_DRAWDOWN_RESULT_RESOURCE: ResourceKey[RiskAnalyticResult] = ResourceKey("asset.drawdown_summary_result", RiskAnalyticResult)


class DrawdownContextScopeError(RuntimeError):
    """Raised when a drawdown context builder is invoked without a matching `BuildScope`."""


class DrawdownContextStatus(StrEnum):
    """Honest lifecycle status of a drawdown context section, mirroring `RiskResultStatus`."""

    OK = "ok"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


# Machine-readable reasons a drawdown context section carries no metrics.
REASON_NO_NATIVE_PRICE = "no_native_price_observation"
REASON_RISK_UNAVAILABLE = "risk_result_unavailable"
REASON_RISK_FAILED = "risk_result_failed"
REASON_RISK_MISSING = "risk_result_missing"
REASON_RISK_ERROR = "risk_execution_error"
REASON_INSUFFICIENT_OBSERVED_PRICES = "insufficient_observed_prices"
REASON_INVALID_OBSERVED_PRICES = "invalid_observed_prices"


class DrawdownContextPayload(StrictModel):
    """Renderer-neutral current/maximum drawdown episode context for one AI Export scope.

    All magnitudes are decimal ratios (``-0.1`` == a 10% peak-relative decline);
    every ``*_ratio`` field is deliberately kept internal so the generic public
    snapshot renderer converts it to a percentage - this component never
    pre-formats percentages. On ``ok``/``partial`` the full deterministic episode
    (sourced verbatim from `RiskDrawdownOutput`) is present; on
    ``unavailable``/``failed`` every metric is ``None`` and ``reason_code`` /
    ``message`` explain why, so an optional analysis section degrades honestly.
    """

    status: DrawdownContextStatus
    reason_code: str | None = None
    message: str | None = None
    warnings: tuple[str, ...] = ()

    calculation_basis: str | None = None
    return_basis: str | None = None
    calculation_currency: str | None = None
    data_quality_status: str | None = None

    current_drawdown_ratio: float | None = Field(default=None, le=0)
    current_peak_date: Date | None = None
    current_drawdown_duration_days: int | None = Field(default=None, ge=0)

    maximum_drawdown_ratio: float | None = Field(default=None, le=0)
    maximum_drawdown_peak_date: Date | None = None
    maximum_drawdown_trough_date: Date | None = None
    maximum_drawdown_recovery_status: str | None = None
    maximum_drawdown_recovery_date: Date | None = None
    maximum_drawdown_duration_days: int | None = Field(default=None, ge=0)
    maximum_drawdown_recovered_ratio: float | None = Field(default=None, ge=0, le=1)
    remaining_to_peak_ratio: float | None = Field(default=None, ge=0)

    available_start: Date | None = None
    available_end: Date | None = None
    n_observations: int | None = Field(default=None, ge=0)
    coverage_ratio: float | None = Field(default=None, ge=0, le=1)

    _SUCCESS_REQUIRED_FIELDS = (
        "calculation_basis",
        "return_basis",
        "data_quality_status",
        "current_drawdown_ratio",
        "current_peak_date",
        "current_drawdown_duration_days",
        "maximum_drawdown_ratio",
        "maximum_drawdown_recovery_status",
        "maximum_drawdown_duration_days",
        "remaining_to_peak_ratio",
        "available_start",
        "available_end",
        "n_observations",
        "coverage_ratio",
    )
    _METRIC_FIELDS = (
        "calculation_basis",
        "return_basis",
        "calculation_currency",
        "data_quality_status",
        "current_drawdown_ratio",
        "current_peak_date",
        "current_drawdown_duration_days",
        "maximum_drawdown_ratio",
        "maximum_drawdown_peak_date",
        "maximum_drawdown_trough_date",
        "maximum_drawdown_recovery_status",
        "maximum_drawdown_recovery_date",
        "maximum_drawdown_duration_days",
        "maximum_drawdown_recovered_ratio",
        "remaining_to_peak_ratio",
        "available_start",
        "available_end",
        "n_observations",
        "coverage_ratio",
    )

    @model_validator(mode="after")
    def _validate_status_invariants(self) -> DrawdownContextPayload:
        if self.status in {DrawdownContextStatus.OK, DrawdownContextStatus.PARTIAL}:
            self._validate_success()
        else:
            self._validate_unavailable()
        return self

    def _validate_success(self) -> None:  # noqa: C901 — flat status invariant raises
        if self.reason_code is not None or self.message is not None:
            raise ValueError("successful drawdown context must not carry reason_code/message")
        missing = [name for name in self._SUCCESS_REQUIRED_FIELDS if getattr(self, name) is None]
        if missing:
            raise ValueError(f"successful drawdown context requires fields: {missing}")
        if self.available_end < self.available_start:
            raise ValueError("available_end must not precede available_start")
        status = self.maximum_drawdown_recovery_status
        if status == RiskDrawdownRecoveryStatus.NO_DRAWDOWN.value:
            if self.maximum_drawdown_ratio != 0:
                raise ValueError("no_drawdown requires a zero maximum_drawdown_ratio")
            if self.maximum_drawdown_peak_date is not None or self.maximum_drawdown_trough_date is not None or self.maximum_drawdown_recovery_date is not None:
                raise ValueError("no_drawdown must not expose episode dates")
            if self.maximum_drawdown_recovered_ratio is not None:
                raise ValueError("no_drawdown must not expose a recovered ratio")
            if self.maximum_drawdown_duration_days != 0:
                raise ValueError("no_drawdown must report a zero maximum duration")
        else:
            if self.maximum_drawdown_ratio >= 0:
                raise ValueError("a drawdown episode requires a negative maximum_drawdown_ratio")
            if self.maximum_drawdown_peak_date is None or self.maximum_drawdown_trough_date is None:
                raise ValueError("a drawdown episode requires peak and trough dates")
            if self.maximum_drawdown_trough_date < self.maximum_drawdown_peak_date:
                raise ValueError("maximum_drawdown_trough_date must not precede the peak date")
            if self.maximum_drawdown_recovered_ratio is None:
                raise ValueError("a drawdown episode requires a recovered ratio")
            if status == RiskDrawdownRecoveryStatus.RECOVERED.value:
                if self.maximum_drawdown_recovery_date is None:
                    raise ValueError("recovered episodes require a recovery date")
                if self.maximum_drawdown_recovery_date < self.maximum_drawdown_trough_date:
                    raise ValueError("recovery date must not precede the trough date")
            elif self.maximum_drawdown_recovery_date is not None:
                raise ValueError("open episodes must not expose a recovery date")

    def _validate_unavailable(self) -> None:
        if not self.reason_code or not self.message:
            raise ValueError("unavailable/failed drawdown context requires reason_code and message")
        populated = [name for name in self._METRIC_FIELDS if getattr(self, name) is not None]
        if populated:
            raise ValueError(f"unavailable/failed drawdown context must not carry metrics: {populated}")


def _require_scope(context: BuildContext, expected: Domain) -> BuildScope:
    scope = context.scope
    if scope is None:
        raise DrawdownContextScopeError("drawdown context components require BuildContext.scope")
    if scope.domain is not expected:
        raise DrawdownContextScopeError(f"expected Domain.{expected.name} scope, got {scope.domain!r}")
    return scope


def _warnings_from_result(result: RiskAnalyticResult) -> tuple[str, ...]:
    return tuple(f"{warning.code}: {warning.message}" for warning in result.warnings)


def _success_payload(result: RiskAnalyticResult, *, calculation_currency: str) -> DrawdownContextPayload:
    output = result.output
    if not isinstance(output, RiskDrawdownOutput):
        raise DrawdownContextScopeError(f"drawdown_summary returned unexpected output kind: {type(output).__name__}")
    if result.data_quality is None:
        raise DrawdownContextScopeError("successful drawdown_summary result is missing data_quality")
    recovered = output.maximum_drawdown_recovered_ratio
    return DrawdownContextPayload(
        status=DrawdownContextStatus(result.status.value),
        warnings=_warnings_from_result(result),
        calculation_basis=output.calculation_basis,
        return_basis=output.return_basis.value,
        calculation_currency=calculation_currency,
        data_quality_status=result.data_quality.data_quality_status.value,
        current_drawdown_ratio=output.current_drawdown,
        current_peak_date=output.current_peak_date,
        current_drawdown_duration_days=output.current_drawdown_duration_days,
        maximum_drawdown_ratio=output.maximum_drawdown,
        maximum_drawdown_peak_date=output.maximum_drawdown_peak_date,
        maximum_drawdown_trough_date=output.maximum_drawdown_trough_date,
        maximum_drawdown_recovery_status=output.maximum_drawdown_recovery_status.value,
        maximum_drawdown_recovery_date=output.maximum_drawdown_recovery_date,
        maximum_drawdown_duration_days=output.maximum_drawdown_duration_days,
        maximum_drawdown_recovered_ratio=recovered,
        remaining_to_peak_ratio=output.remaining_to_peak_ratio,
        available_start=output.available_start,
        available_end=output.available_end,
        n_observations=output.n_observations,
        coverage_ratio=output.coverage,
    )


def _unavailable_payload(*, status: DrawdownContextStatus, reason_code: str, message: str, warnings: tuple[str, ...] = ()) -> DrawdownContextPayload:
    return DrawdownContextPayload(status=status, reason_code=reason_code, message=message, warnings=warnings)


def _payload_from_result(result: RiskAnalyticResult, *, calculation_currency: str) -> DrawdownContextPayload:
    if result.status in {RiskResultStatus.OK, RiskResultStatus.PARTIAL}:
        return _success_payload(result, calculation_currency=calculation_currency)
    error = result.error
    reason_code = error.code.value if error is not None else REASON_RISK_MISSING
    status = DrawdownContextStatus.FAILED if result.status == RiskResultStatus.FAILED else DrawdownContextStatus.UNAVAILABLE
    message = "Drawdown calculation failed for the selected scope and period." if status == DrawdownContextStatus.FAILED else "Drawdown data is unavailable for the selected scope and period."
    return _unavailable_payload(status=status, reason_code=reason_code, message=message, warnings=_warnings_from_result(result))


async def _execute_drawdown(
    context: BuildContext,
    scope: BuildScope,
    *,
    resource_key: ResourceKey[RiskAnalyticResult],
    risk_scope: PortfolioRiskScope | AssetRiskScope,
    target_currency: str,
) -> DrawdownContextPayload:
    # E1 (02/09): AI Export always computes drawdown over the FULL available
    # history — an export for an AI must carry the true historical peak, never
    # a window-relative one. The start bound therefore ignores the build's
    # period:
    # - ASSET scope: date.min — price loads are sparse-safe (the prepared
    #   series starts at the first actual price, gaps are backward-filled
    #   only after a real seed).
    # - PORTFOLIO scope (whole or broker subset): the user's earliest
    #   accessible transaction — the portfolio engine emits one history point
    #   per day in the range, so date.min would materialize millennia of
    #   empty days.
    async def _loader(session: AsyncSession) -> RiskAnalyticResult:
        if isinstance(risk_scope, AssetRiskScope):
            start = Date.min
        else:
            resolved = await resolve_date_sentinels(
                OpenDateRangeModel(start="min", end=scope.period_end),
                scope.user_id,
                session,
                broker_ids=list(scope.broker_scope) or None,
            )
            inception = resolved.start if resolved is not None and isinstance(resolved.start, Date) else None
            start = min(inception, scope.period_start) if inception is not None else scope.period_start
        request = RiskQueryRequest(
            scope=risk_scope,
            date_range=DateRangeModel(start=start, end=scope.period_end),
            target_currency=target_currency,
            mode=RiskMode.HISTORICAL,
            analytics=[RiskAnalyticRequest(instance_id=_DRAWDOWN_INSTANCE_ID, analytic_code=_DRAWDOWN_ANALYTIC_CODE)],
        )
        response = await RiskService(session).execute(user_id=scope.user_id, request=request)
        if not response.items:
            raise DrawdownContextScopeError("Risk drawdown_summary returned no analytic result")
        return response.items[0]

    try:
        result = await context.db_resource(resource_key, _loader)
    except ResourceLoadError:
        return _unavailable_payload(
            status=DrawdownContextStatus.FAILED,
            reason_code=REASON_RISK_ERROR,
            message="Drawdown calculation could not be completed for the selected scope and period.",
        )
    return _payload_from_result(result, calculation_currency=target_currency)


# =============================================================================
# portfolio.drawdown_summary
# =============================================================================


async def _build_portfolio_drawdown(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> DrawdownContextPayload:
    scope = _require_scope(context, Domain.PORTFOLIO)
    return await _execute_drawdown(
        context,
        scope,
        resource_key=_PORTFOLIO_DRAWDOWN_RESULT_RESOURCE,
        risk_scope=PortfolioRiskScope(kind=RiskScopeKind.PORTFOLIO, broker_ids=None),
        target_currency=scope.target_currency,
    )


# =============================================================================
# broker.drawdown_summary
# =============================================================================


async def _build_broker_drawdown(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> DrawdownContextPayload:
    scope = _require_scope(context, Domain.BROKER)
    return await _execute_drawdown(
        context,
        scope,
        resource_key=_BROKER_DRAWDOWN_RESULT_RESOURCE,
        risk_scope=PortfolioRiskScope(kind=RiskScopeKind.PORTFOLIO, broker_ids=list(scope.broker_scope)),
        target_currency=scope.target_currency,
    )


# =============================================================================
# asset.drawdown_summary (depends on asset.market_snapshot for native currency)
# =============================================================================


def _native_currency_from_snapshot(dependencies: Mapping[str, SectionEnvelope]) -> str | None:
    envelope = dependencies.get("asset.market_snapshot")
    if envelope is None:
        return None
    snapshot = AssetMarketSnapshotPayload.model_validate(envelope.payload)
    if snapshot.observed is None:
        return None
    return snapshot.observed.native_price.code


async def _build_asset_drawdown(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> DrawdownContextPayload:
    scope = _require_scope(context, Domain.ASSET)
    native_currency = _native_currency_from_snapshot(dependencies)
    if native_currency is None:
        return _unavailable_payload(
            status=DrawdownContextStatus.UNAVAILABLE,
            reason_code=REASON_NO_NATIVE_PRICE,
            message="No native observed price for this asset; drawdown is not computed to avoid approximating a target-currency basis.",
        )
    return await _execute_drawdown(
        context,
        scope,
        resource_key=_ASSET_DRAWDOWN_RESULT_RESOURCE,
        risk_scope=AssetRiskScope(kind=RiskScopeKind.ASSET, asset_id=scope.asset_id),
        target_currency=native_currency,
    )


# =============================================================================
# portfolio.asset_drawdown_snapshot
# =============================================================================


class PortfolioAssetDrawdownRow(StrictModel):
    """Compact observed-price drawdown comparison for one held asset.

    No history is exported. The four decision fields requested by PAC are
    accompanied only by basis/coverage facts needed to avoid treating a sparse
    series as equivalent to a complete one.
    """

    asset_id: int
    status: DrawdownContextStatus
    reason_code: str | None = None
    calculation_basis: str | None = None
    calculation_currency: str | None = None
    data_quality_status: str | None = None
    current_drawdown_ratio: float | None = Field(default=None, le=0)
    maximum_drawdown_ratio: float | None = Field(default=None, le=0)
    maximum_drawdown_recovery_status: str | None = None
    remaining_to_peak_ratio: float | None = Field(default=None, ge=0)
    available_start: Date | None = None
    available_end: Date | None = None
    n_observations: int = Field(default=0, ge=0)
    coverage_ratio: float = Field(default=0, ge=0, le=1)

    @model_validator(mode="after")
    def _validate_row(self) -> PortfolioAssetDrawdownRow:
        metric_fields = (
            self.calculation_basis,
            self.calculation_currency,
            self.data_quality_status,
            self.current_drawdown_ratio,
            self.maximum_drawdown_ratio,
            self.maximum_drawdown_recovery_status,
            self.remaining_to_peak_ratio,
            self.available_start,
            self.available_end,
        )
        if self.status in {DrawdownContextStatus.OK, DrawdownContextStatus.PARTIAL}:
            if self.reason_code is not None or any(value is None for value in metric_fields):
                raise ValueError("available asset drawdown rows require all metrics and no reason_code")
            if self.n_observations < 2:
                raise ValueError("available asset drawdown rows require at least two observations")
        elif self.reason_code is None or any(value is not None for value in metric_fields):
            raise ValueError("unavailable asset drawdown rows require reason_code and no metrics")
        return self


class PortfolioAssetDrawdownSnapshotPayload(StrictModel):
    """No-history per-asset Drawdown comparison for PAC planning."""

    policy_code: str = "observed_price_drawdown_snapshot_v1"
    rows: tuple[PortfolioAssetDrawdownRow, ...]


def _observed_price_points(result, *, start: Date, end: Date) -> tuple[tuple[Date, float], ...]:
    if result is None or coherent_price_currency(result) is None:
        return ()
    return tuple((point.date, float(point.close)) for point in result.prices if start <= point.date <= end and (point.backward_fill_info is None or point.backward_fill_info.days_back == 0))


def _asset_drawdown_row(*, asset_id: int, points: tuple[tuple[Date, float], ...], scope: BuildScope, calculation_currency: str | None) -> PortfolioAssetDrawdownRow:
    if len(points) < 2 or calculation_currency is None:
        return PortfolioAssetDrawdownRow(
            asset_id=asset_id,
            status=DrawdownContextStatus.UNAVAILABLE,
            reason_code=REASON_INSUFFICIENT_OBSERVED_PRICES,
            n_observations=len(points),
        )
    if any(value <= 0 for _, value in points):
        return PortfolioAssetDrawdownRow(
            asset_id=asset_id,
            status=DrawdownContextStatus.UNAVAILABLE,
            reason_code=REASON_INVALID_OBSERVED_PRICES,
            n_observations=len(points),
        )

    returns = tuple(current_value / previous_value - 1 for (_, previous_value), (_, current_value) in zip(points, points[1:], strict=False))
    report = drawdown_episodes(
        returns,
        dates=tuple(point_date for point_date, _ in points[1:]),
        baseline_date=points[0][0],
    )
    requested_days = max(1, (scope.period_end - scope.period_start).days)
    available_days = max(0, (points[-1][0] - points[0][0]).days)
    coverage_ratio = min(1.0, available_days / requested_days)
    quality = DataQualityStatus.OK if points[0][0] <= scope.period_start and points[-1][0] >= scope.period_end else DataQualityStatus.PARTIAL
    status = DrawdownContextStatus.OK if quality is DataQualityStatus.OK else DrawdownContextStatus.PARTIAL
    return PortfolioAssetDrawdownRow(
        asset_id=asset_id,
        status=status,
        calculation_basis="observed_native_price_only_close",
        calculation_currency=calculation_currency,
        data_quality_status=quality.value,
        current_drawdown_ratio=report.current_drawdown,
        maximum_drawdown_ratio=report.maximum_drawdown,
        maximum_drawdown_recovery_status=report.maximum_drawdown_recovery_status,
        remaining_to_peak_ratio=report.remaining_to_peak_ratio,
        available_start=report.available_start,
        available_end=report.available_end,
        n_observations=len(points),
        coverage_ratio=coverage_ratio,
    )


async def _build_portfolio_asset_drawdown_snapshot(
    context: BuildContext,
    dependencies: Mapping[str, SectionEnvelope],
) -> PortfolioAssetDrawdownSnapshotPayload:
    scope = _require_scope(context, Domain.PORTFOLIO)
    universe = await load_technical_universe_bundle(context, **PORTFOLIO_TECHNICAL_UNIVERSE_KWARGS)
    rows = []
    for asset_id in universe.asset_ids:
        result = universe.price_results.by_asset_id.get(asset_id)
        rows.append(
            _asset_drawdown_row(
                asset_id=asset_id,
                points=_observed_price_points(result, start=scope.period_start, end=scope.period_end),
                scope=scope,
                calculation_currency=coherent_price_currency(result) if result is not None else None,
            )
        )
    return PortfolioAssetDrawdownSnapshotPayload(rows=tuple(rows))


# =============================================================================
# Component specs (real builders wired into the domain registries)
# =============================================================================


PORTFOLIO_DRAWDOWN_SUMMARY_COMPONENT = ComponentSpec(
    component_id="portfolio.drawdown_summary",
    version=1,
    domains=frozenset({Domain.PORTFOLIO}),
    output_model=DrawdownContextPayload,
    builder=_build_portfolio_drawdown,
    period_behavior=PeriodBehavior.WINDOWED,
)

PORTFOLIO_ASSET_DRAWDOWN_SNAPSHOT_COMPONENT = ComponentSpec(
    component_id="portfolio.asset_drawdown_snapshot",
    version=1,
    domains=frozenset({Domain.PORTFOLIO}),
    output_model=PortfolioAssetDrawdownSnapshotPayload,
    builder=_build_portfolio_asset_drawdown_snapshot,
    dependencies=("portfolio.asset_market_context",),
    period_behavior=PeriodBehavior.WINDOWED,
)

BROKER_DRAWDOWN_SUMMARY_COMPONENT = ComponentSpec(
    component_id="broker.drawdown_summary",
    version=1,
    domains=frozenset({Domain.BROKER}),
    output_model=DrawdownContextPayload,
    builder=_build_broker_drawdown,
    period_behavior=PeriodBehavior.WINDOWED,
)

ASSET_DRAWDOWN_SUMMARY_COMPONENT = ComponentSpec(
    component_id="asset.drawdown_summary",
    version=1,
    domains=frozenset({Domain.ASSET}),
    output_model=DrawdownContextPayload,
    builder=_build_asset_drawdown,
    dependencies=("asset.market_snapshot",),
    period_behavior=PeriodBehavior.WINDOWED,
)

PORTFOLIO_DRAWDOWN_CONTEXT_COMPONENTS: tuple[ComponentSpec, ...] = (
    PORTFOLIO_DRAWDOWN_SUMMARY_COMPONENT,
    PORTFOLIO_ASSET_DRAWDOWN_SNAPSHOT_COMPONENT,
)
BROKER_DRAWDOWN_CONTEXT_COMPONENTS: tuple[ComponentSpec, ...] = (BROKER_DRAWDOWN_SUMMARY_COMPONENT,)
ASSET_DRAWDOWN_CONTEXT_COMPONENTS: tuple[ComponentSpec, ...] = (ASSET_DRAWDOWN_SUMMARY_COMPONENT,)


__all__ = [
    "ASSET_DRAWDOWN_CONTEXT_COMPONENTS",
    "ASSET_DRAWDOWN_SUMMARY_COMPONENT",
    "BROKER_DRAWDOWN_CONTEXT_COMPONENTS",
    "BROKER_DRAWDOWN_SUMMARY_COMPONENT",
    "PORTFOLIO_ASSET_DRAWDOWN_SNAPSHOT_COMPONENT",
    "PORTFOLIO_DRAWDOWN_CONTEXT_COMPONENTS",
    "PORTFOLIO_DRAWDOWN_SUMMARY_COMPONENT",
    "DrawdownContextPayload",
    "DrawdownContextStatus",
    "PortfolioAssetDrawdownRow",
    "PortfolioAssetDrawdownSnapshotPayload",
    "REASON_INSUFFICIENT_OBSERVED_PRICES",
    "REASON_INVALID_OBSERVED_PRICES",
    "REASON_NO_NATIVE_PRICE",
    "REASON_RISK_ERROR",
    "REASON_RISK_FAILED",
    "REASON_RISK_MISSING",
    "REASON_RISK_UNAVAILABLE",
]
