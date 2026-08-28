"""Broker concentration adequacy evidence `ComponentSpec` builders (Phase 0 AI Export adequacy remediation).

Two standalone, broker-owned components that expose *already-computed*
deterministic concentration evidence inside the public Broker general snapshot,
without touching shared catalog/registry wiring:

- ``broker.concentration_context``: surfaces the existing broker report
  ``allocation_by_type``/``allocation_by_sector``/``allocation_by_geography``
  slices verbatim (mapped 1:1 through the shared ``map_allocation_slice``
  helper), plus a backend-owned ``allocation_by_currency`` breakdown computed
  from the very same ``PortfolioReportResponse`` holdings (native valuation
  currency + snapshot ``current_value``), and preserves the HHI-points /
  largest-position-weight concentration metrics already produced by
  ``broker.allocation_concentration``. Every dimension carries an explicit
  coverage/unknown bucket so an undetermined native currency or an
  unpriced position degrades honestly instead of being silently dropped or
  coerced.

- ``broker.concentration_comparison``: an optional broker-vs-whole-portfolio
  comparator. It loads the *unfiltered* whole-portfolio ``PortfolioReportResponse``
  through ``PortfolioService`` (memoized under a distinct broker-owned resource
  key, so it is loaded at most once and never duplicates the broker-filtered
  report load), enforcing user access exactly like every other report load
  (``PortfolioService.get_report(user_id, ...)`` resolves ``broker_ids=None`` to
  the caller's accessible brokers only). It emits broker/portfolio HHI points,
  largest position weight, position counts and market-value totals with deltas
  only when both sides are comparable, and an explicit typed ``unavailable``
  reason otherwise. It never exposes asset/lot/transaction row identifiers.

No financial formula is reimplemented here: allocation slices and HHI/largest
metrics come straight off the engine report, and the currency breakdown is a
pure deterministic regrouping of holding snapshot values already in the report.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date as Date
from decimal import Decimal
from enum import StrEnum

from pydantic import Field, model_validator

from backend.app.schemas.common import Currency, SafeDecimal, StrictModel
from backend.app.schemas.portfolio import PortfolioHolding, PortfolioReportResponse, PortfolioSummary
from backend.app.services.ai_export.components.envelope import SectionEnvelope
from backend.app.services.ai_export.components.payloads.portfolio_broker import (
    AllocationSlice,
    load_portfolio_report,
    map_allocation_slice,
)
from backend.app.services.ai_export.components.resources import BROKER_REPORT_RESOURCE
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.types import BuildScope, Domain, PeriodBehavior, ResourceKey
from backend.app.services.ai_export.dependencies import BuildContext, ResourceLoadError

# Whole-portfolio (unfiltered) report resource used only by the comparator. It is
# a *different* cache slot from `broker.report` (the broker-filtered load), so the
# two loads never collide and each is memoized exactly once per request.
_BROKER_WHOLE_PORTFOLIO_REPORT_RESOURCE: ResourceKey[PortfolioReportResponse] = ResourceKey("broker.whole_portfolio_report", PortfolioReportResponse)

# Machine-readable reasons the comparator carries no comparison metrics.
REASON_BROKER_EMPTY = "broker_summary_unavailable"
REASON_PORTFOLIO_EMPTY = "portfolio_summary_unavailable"
REASON_PORTFOLIO_LOAD_FAILED = "portfolio_report_load_failed"


class BrokerConcentrationContextScopeError(RuntimeError):
    """Raised when a broker concentration context builder is invoked without a matching `BuildScope`."""


def _require_broker_scope(context: BuildContext) -> BuildScope:
    scope = context.scope
    if scope is None:
        raise BrokerConcentrationContextScopeError("broker concentration components require BuildContext.scope")
    if scope.domain is not Domain.BROKER:
        raise BrokerConcentrationContextScopeError(f"expected Domain.BROKER scope, got {scope.domain!r}")
    if scope.broker_id is None:
        raise BrokerConcentrationContextScopeError("broker concentration components require BuildScope.broker_id")
    return scope


# =============================================================================
# Shared deterministic concentration math (read straight off the engine report)
# =============================================================================


def concentration_metrics(summary: PortfolioSummary | None) -> tuple[Decimal | None, Decimal | None, int]:
    """Largest position weight and Herfindahl points over the *entire* holding set.

    Mirrors `broker_financial._concentration_metrics` exactly (no top-N
    truncation) so the context/comparator numbers reconcile 1:1 with the frozen
    `broker.allocation_concentration` section.
    """
    if summary is None:
        return None, None, 0
    weights = [holding.nav_weight_percent for holding in summary.holdings if holding.nav_weight_percent is not None]
    position_count = len(summary.holdings)
    if not weights:
        return None, None, position_count
    largest = max(abs(weight) for weight in weights)
    herfindahl = sum(weight * weight for weight in weights)
    return largest, herfindahl, position_count


def _holding_native_currency(holding: PortfolioHolding) -> str | None:
    """The holding's native valuation currency, or ``None`` when undetermined.

    Uses the currency the engine actually valued the position in
    (``valuation_effective_currency``), falling back to the reference-price
    currency. ``None`` (e.g. an unpriced ``MISSING`` valuation) routes the
    position into the explicit unknown bucket rather than being dropped.
    """
    return holding.valuation_effective_currency or holding.valuation_reference_currency


# =============================================================================
# broker.concentration_context
# =============================================================================


class CurrencyAllocationSlice(StrictModel):
    """One native-currency allocation slice of the broker's snapshot market value.

    ``currency == None`` is the explicit *unknown* bucket (positions whose native
    valuation currency could not be determined, or which carry no snapshot
    value). ``amount`` is always expressed in the report ``target_currency``;
    ``percent`` is the slice's share of the total *valued* market value and is
    ``None`` only when there is no valued market value to divide by.
    """

    currency: str | None = Field(None, description="Native valuation currency; None == undetermined/unknown bucket.")
    amount: Currency
    percent: SafeDecimal | None = None
    position_count: int = Field(ge=0)


class ConcentrationCoverage(StrictModel):
    """Explicit covered/unknown split so undetermined-currency positions stay visible."""

    valued_market_value: Currency
    covered_market_value: Currency
    unknown_market_value: Currency
    position_count: int = Field(ge=0)
    covered_position_count: int = Field(ge=0)
    unknown_position_count: int = Field(ge=0)


class BrokerConcentrationContextPayload(StrictModel):
    """Renderer-neutral concentration evidence: existing dimensions + currency breakdown + preserved HHI."""

    broker_id: int
    as_of: Date
    target_currency: str
    position_count: int = Field(ge=0)
    market_value: Currency | None = None
    largest_position_weight_percent: SafeDecimal | None = None
    herfindahl_index_points: SafeDecimal | None = Field(
        None,
        description="Sum of squared nav_weight_percent across ALL positions (no top-N truncation); higher = more concentrated. 10000 == fully concentrated in one position.",
    )
    allocation_by_type: list[AllocationSlice] = Field(default_factory=list)
    allocation_by_sector: list[AllocationSlice] = Field(default_factory=list)
    allocation_by_geography: list[AllocationSlice] = Field(default_factory=list)
    allocation_by_currency: list[CurrencyAllocationSlice] = Field(default_factory=list)
    currency_coverage: ConcentrationCoverage
    allocation_dimension_semantics: str
    currency_allocation_semantics: str
    concentration_semantics: str


def _map_slices(items: Sequence, *, currency_code: str) -> list[AllocationSlice]:
    """Maps engine allocation items 1:1 and sorts deterministically (desc percent, then name)."""
    slices = [map_allocation_slice(item, currency_code=currency_code) for item in items]
    return sorted(slices, key=lambda slice_: (-slice_.percent, slice_.name))


def build_currency_allocation(summary: PortfolioSummary | None, *, currency_code: str) -> tuple[list[CurrencyAllocationSlice], ConcentrationCoverage]:
    """Backend-owned native-currency allocation with an explicit unknown bucket.

    Groups every holding's snapshot ``current_value`` (already in
    ``target_currency``) by its native valuation currency. Positions with an
    undetermined native currency, or with no snapshot value, are aggregated into
    a single ``currency == None`` unknown slice. Percentages are the slice share
    of the total *valued* market value (covered + unknown-but-valued), so they
    sum to 100 whenever any position carries value.
    """
    zero = Currency(code=currency_code, amount=Decimal("0"))
    if summary is None:
        empty_coverage = ConcentrationCoverage(valued_market_value=zero, covered_market_value=zero, unknown_market_value=zero, position_count=0, covered_position_count=0, unknown_position_count=0)
        return [], empty_coverage

    covered_amounts: dict[str, Decimal] = {}
    covered_counts: dict[str, int] = {}
    unknown_amount = Decimal("0")
    unknown_count = 0
    for holding in summary.holdings:
        native = _holding_native_currency(holding)
        value = holding.current_value
        if native is None or value is None:
            unknown_count += 1
            if value is not None:
                unknown_amount += value
            continue
        covered_amounts[native] = covered_amounts.get(native, Decimal("0")) + value
        covered_counts[native] = covered_counts.get(native, 0) + 1

    covered_total = sum(covered_amounts.values(), Decimal("0"))
    valued_total = covered_total + unknown_amount

    def _percent(value: Decimal) -> Decimal | None:
        if valued_total == 0:
            return None
        return value / valued_total * Decimal("100")

    slices: list[CurrencyAllocationSlice] = [
        CurrencyAllocationSlice(
            currency=code,
            amount=Currency(code=currency_code, amount=amount),
            percent=_percent(amount),
            position_count=covered_counts[code],
        )
        for code, amount in covered_amounts.items()
    ]
    # Deterministic order: known currencies by descending share then code; unknown last.
    slices.sort(key=lambda slice_: (-(slice_.percent if slice_.percent is not None else Decimal("0")), slice_.currency or ""))
    if unknown_count:
        slices.append(
            CurrencyAllocationSlice(
                currency=None,
                amount=Currency(code=currency_code, amount=unknown_amount),
                percent=_percent(unknown_amount),
                position_count=unknown_count,
            )
        )

    covered_count_total = sum(covered_counts.values())
    coverage = ConcentrationCoverage(
        valued_market_value=Currency(code=currency_code, amount=valued_total),
        covered_market_value=Currency(code=currency_code, amount=covered_total),
        unknown_market_value=Currency(code=currency_code, amount=unknown_amount),
        position_count=len(summary.holdings),
        covered_position_count=covered_count_total,
        unknown_position_count=unknown_count,
    )
    return slices, coverage


async def _build_broker_concentration_context(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> BrokerConcentrationContextPayload:
    scope = _require_broker_scope(context)
    # Loaded from the same shared (memoized) `broker.report` resource every other
    # broker financial component uses - no extra `get_report` call is triggered.
    report = await load_portfolio_report(context, scope, BROKER_REPORT_RESOURCE)
    summary = report.summary
    currency_code = scope.target_currency
    largest, herfindahl, position_count = concentration_metrics(summary)
    currency_slices, coverage = build_currency_allocation(summary, currency_code=currency_code)
    return BrokerConcentrationContextPayload(
        broker_id=scope.broker_id,
        as_of=scope.snapshot_as_of,
        target_currency=currency_code,
        position_count=position_count,
        market_value=summary.market_value if summary else None,
        largest_position_weight_percent=largest,
        herfindahl_index_points=herfindahl,
        allocation_by_type=_map_slices(summary.allocation_by_type if summary else (), currency_code=currency_code),
        allocation_by_sector=_map_slices(summary.allocation_by_sector if summary else (), currency_code=currency_code),
        allocation_by_geography=_map_slices(summary.allocation_by_geography if summary else (), currency_code=currency_code),
        allocation_by_currency=currency_slices,
        currency_coverage=coverage,
        allocation_dimension_semantics="Asset type, sector, and geography are engine allocation slices; an explicit Liquidity slice may include cash.",
        currency_allocation_semantics="Currency allocation groups current position market value by native valuation currency. Cash is excluded and remains in broker cash fields.",
        concentration_semantics="Largest-position weight and HHI use position nav_weight_percent: current position value / total NAV. Cash is included in the denominator but is not itself an HHI term.",
    )


# =============================================================================
# broker.concentration_comparison (broker vs whole portfolio)
# =============================================================================


class ConcentrationComparisonStatus(StrEnum):
    """Honest lifecycle status of the broker-vs-portfolio concentration comparison."""

    OK = "ok"
    UNAVAILABLE = "unavailable"


class BrokerConcentrationComparisonPayload(StrictModel):
    """Broker-vs-whole-portfolio concentration comparison, or an explicit unavailable reason.

    On ``ok`` every ``broker_*``/``portfolio_*`` metric and its ``*_delta`` is
    present (delta == broker - portfolio); on ``unavailable`` every metric is
    ``None`` and ``reason_code``/``message`` explain why, so an optional analysis
    section degrades honestly. Only the scoped ``broker_id`` entity identifier is
    exposed - never any asset/lot/transaction row identifier.
    """

    status: ConcentrationComparisonStatus
    reason_code: str | None = None
    message: str | None = None

    broker_id: int
    target_currency: str

    broker_position_count: int | None = Field(None, ge=0)
    portfolio_position_count: int | None = Field(None, ge=0)

    broker_herfindahl_index_points: SafeDecimal | None = None
    portfolio_herfindahl_index_points: SafeDecimal | None = None
    herfindahl_index_delta_points: SafeDecimal | None = None

    broker_largest_position_weight_percent: SafeDecimal | None = None
    portfolio_largest_position_weight_percent: SafeDecimal | None = None
    largest_position_weight_delta_percent: SafeDecimal | None = None

    broker_market_value: Currency | None = None
    portfolio_market_value: Currency | None = None
    broker_share_of_portfolio_market_value_percent: SafeDecimal | None = None

    _METRIC_FIELDS = (
        "broker_position_count",
        "portfolio_position_count",
        "broker_herfindahl_index_points",
        "portfolio_herfindahl_index_points",
        "herfindahl_index_delta_points",
        "broker_largest_position_weight_percent",
        "portfolio_largest_position_weight_percent",
        "largest_position_weight_delta_percent",
        "broker_market_value",
        "portfolio_market_value",
        "broker_share_of_portfolio_market_value_percent",
    )
    _REQUIRED_ON_OK = (
        "broker_position_count",
        "portfolio_position_count",
    )

    @model_validator(mode="after")
    def _validate_status_invariants(self) -> BrokerConcentrationComparisonPayload:
        if self.status is ConcentrationComparisonStatus.OK:
            if self.reason_code is not None or self.message is not None:
                raise ValueError("ok concentration comparison must not carry reason_code/message")
            missing = [name for name in self._REQUIRED_ON_OK if getattr(self, name) is None]
            if missing:
                raise ValueError(f"ok concentration comparison requires fields: {missing}")
        else:
            if not self.reason_code or not self.message:
                raise ValueError("unavailable concentration comparison requires reason_code and message")
            populated = [name for name in self._METRIC_FIELDS if getattr(self, name) is not None]
            if populated:
                raise ValueError(f"unavailable concentration comparison must not carry metrics: {populated}")
        return self


def _whole_portfolio_scope(scope: BuildScope) -> BuildScope:
    """Derives the unfiltered whole-portfolio scope (all accessible brokers) from a broker scope."""
    return BuildScope(
        request_id=scope.request_id,
        user_id=scope.user_id,
        domain=Domain.PORTFOLIO,
        detail_level=scope.detail_level,
        period_start=scope.period_start,
        period_end=scope.period_end,
        target_currency=scope.target_currency,
        broker_scope=(),
    )


def _unavailable_comparison(scope: BuildScope, *, reason_code: str, message: str) -> BrokerConcentrationComparisonPayload:
    return BrokerConcentrationComparisonPayload(
        status=ConcentrationComparisonStatus.UNAVAILABLE,
        reason_code=reason_code,
        message=message,
        broker_id=scope.broker_id,
        target_currency=scope.target_currency,
    )


def _delta(broker_value: Decimal | None, portfolio_value: Decimal | None) -> Decimal | None:
    if broker_value is None or portfolio_value is None:
        return None
    return broker_value - portfolio_value


async def _build_broker_concentration_comparison(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> BrokerConcentrationComparisonPayload:
    scope = _require_broker_scope(context)
    broker_report = await load_portfolio_report(context, scope, BROKER_REPORT_RESOURCE)
    broker_summary = broker_report.summary
    if broker_summary is None or not broker_summary.holdings:
        return _unavailable_comparison(scope, reason_code=REASON_BROKER_EMPTY, message="This broker has no valued positions in the selected period, so there is nothing to compare against the whole portfolio.")

    portfolio_scope = _whole_portfolio_scope(scope)
    try:
        portfolio_report = await load_portfolio_report(context, portfolio_scope, _BROKER_WHOLE_PORTFOLIO_REPORT_RESOURCE)
    except ResourceLoadError:
        return _unavailable_comparison(scope, reason_code=REASON_PORTFOLIO_LOAD_FAILED, message="The whole-portfolio report could not be loaded for the selected period, so the concentration comparison is unavailable.")
    portfolio_summary = portfolio_report.summary
    if portfolio_summary is None or not portfolio_summary.holdings:
        return _unavailable_comparison(scope, reason_code=REASON_PORTFOLIO_EMPTY, message="The whole portfolio has no valued positions in the selected period, so the concentration comparison is unavailable.")

    broker_largest, broker_hhi, broker_count = concentration_metrics(broker_summary)
    portfolio_largest, portfolio_hhi, portfolio_count = concentration_metrics(portfolio_summary)
    currency_code = scope.target_currency
    broker_market_value = broker_summary.market_value
    portfolio_market_value = portfolio_summary.market_value
    broker_share: Decimal | None = None
    if broker_market_value is not None and portfolio_market_value is not None and portfolio_market_value.amount != 0:
        broker_share = broker_market_value.amount / portfolio_market_value.amount * Decimal("100")

    return BrokerConcentrationComparisonPayload(
        status=ConcentrationComparisonStatus.OK,
        broker_id=scope.broker_id,
        target_currency=currency_code,
        broker_position_count=broker_count,
        portfolio_position_count=portfolio_count,
        broker_herfindahl_index_points=broker_hhi,
        portfolio_herfindahl_index_points=portfolio_hhi,
        herfindahl_index_delta_points=_delta(broker_hhi, portfolio_hhi),
        broker_largest_position_weight_percent=broker_largest,
        portfolio_largest_position_weight_percent=portfolio_largest,
        largest_position_weight_delta_percent=_delta(broker_largest, portfolio_largest),
        broker_market_value=broker_market_value,
        portfolio_market_value=portfolio_market_value,
        broker_share_of_portfolio_market_value_percent=broker_share,
    )


# =============================================================================
# Component specs (real builders ready for the coordinator integration gate)
# =============================================================================


BROKER_CONCENTRATION_CONTEXT_COMPONENT = ComponentSpec(
    component_id="broker.concentration_context",
    version=1,
    domains=frozenset({Domain.BROKER}),
    output_model=BrokerConcentrationContextPayload,
    builder=_build_broker_concentration_context,
    dependencies=("broker.allocation_concentration",),
    period_behavior=PeriodBehavior.AS_OF,
)

BROKER_CONCENTRATION_COMPARISON_COMPONENT = ComponentSpec(
    component_id="broker.concentration_comparison",
    version=1,
    domains=frozenset({Domain.BROKER}),
    output_model=BrokerConcentrationComparisonPayload,
    builder=_build_broker_concentration_comparison,
    period_behavior=PeriodBehavior.AS_OF,
)

BROKER_CONCENTRATION_COMPONENTS: tuple[ComponentSpec, ...] = (
    BROKER_CONCENTRATION_CONTEXT_COMPONENT,
    BROKER_CONCENTRATION_COMPARISON_COMPONENT,
)


__all__ = [
    "BROKER_CONCENTRATION_COMPARISON_COMPONENT",
    "BROKER_CONCENTRATION_COMPONENTS",
    "BROKER_CONCENTRATION_CONTEXT_COMPONENT",
    "REASON_BROKER_EMPTY",
    "REASON_PORTFOLIO_EMPTY",
    "REASON_PORTFOLIO_LOAD_FAILED",
    "BrokerConcentrationComparisonPayload",
    "BrokerConcentrationContextPayload",
    "BrokerConcentrationContextScopeError",
    "ConcentrationComparisonStatus",
    "ConcentrationCoverage",
    "CurrencyAllocationSlice",
    "build_currency_allocation",
    "concentration_metrics",
]
