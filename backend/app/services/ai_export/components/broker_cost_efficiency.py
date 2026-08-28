"""Broker cost-efficiency adequacy evidence `ComponentSpec` builder (Phase 0 AI Export adequacy remediation).

A standalone, broker-owned ``broker.cost_efficiency`` component that adds the
deterministic *activity / turnover denominators* the cost-efficiency Analysis
needs on top of the recorded fee/tax figures that already exist verbatim in
``broker.flows_income_costs`` (the engine-computed ``period_fees`` /
``period_taxes`` / ``period_fees_taxes``, all already in ``target_currency``).

Design invariants (see the task hand-off notes; this module deliberately does
**not** touch any shared catalog/registry wiring):

- **Fees are never invented and never coerced to zero.** Recorded fee/tax amounts
  are read straight off the broker ``PortfolioReportResponse`` summary. A real
  zero is emitted only when at least one typed FEE/TAX source row exists and all
  its amounts are zero; no source rows remain ``unavailable``.

- **Turnover is deterministic and currency-honest.** Turnover is
  ``Σ |amount|`` over BUY/SELL settlement transactions in the inclusive period
  whose native ``currency`` equals the report ``target_currency`` - no FX
  conversion is ever performed here, so the number is fully deterministic.
  BUY (``amount < 0``) and SELL (``amount > 0``) magnitudes are summed by
  absolute value. Trades settled in a *different* currency are counted in an
  explicit coverage bucket but excluded from the turnover amount, and mark the
  turnover ``complete == False``.

- **Ratios only when numerator and denominator are both available.** The
  fees-to-turnover ratio is emitted only when fees are recorded, turnover is
  positive *and* currency-complete (so numerator and denominator share the same
  target-currency basis); the fees-to-invested and fees-to-average-NAV ratios
  only when their denominator is present and non-zero. Otherwise the ratio is
  ``None`` with a machine-readable reason, never a fabricated zero.

Transaction-type semantics used here are frozen as module constants
(``TRADE_TYPES``) so the turnover formula is explicit and testable; no ratio or
turnover is ever recomputed on the frontend.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date as Date
from decimal import Decimal
from enum import StrEnum

from pydantic import Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import BrokerUserAccess, Transaction, TransactionType
from backend.app.schemas.common import Currency, SafeDecimal, StrictModel
from backend.app.schemas.portfolio import PortfolioReportResponse, PortfolioSummary
from backend.app.services.ai_export.components.envelope import SectionEnvelope
from backend.app.services.ai_export.components.payloads.portfolio_broker import load_portfolio_report
from backend.app.services.ai_export.components.resources import BROKER_REPORT_RESOURCE
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.types import BuildScope, Domain, PeriodBehavior, ResourceKey
from backend.app.services.ai_export.dependencies import BuildContext

# Frozen transaction-type semantics: the only two types that count as a "trade"
# and therefore contribute to turnover. BUY settles with amount < 0 (cash out),
# SELL with amount > 0 (cash in); turnover sums their absolute magnitudes.
TRADE_TYPES: frozenset[TransactionType] = frozenset({TransactionType.BUY, TransactionType.SELL})

# Machine-readable reasons a value or ratio carries no value.
REASON_FEES_UNAVAILABLE = "fees_unavailable"
REASON_TURNOVER_ZERO = "turnover_nonpositive"
REASON_TURNOVER_INCOMPLETE = "turnover_currency_incomplete"
REASON_DENOMINATOR_UNAVAILABLE = "denominator_unavailable"
REASON_DENOMINATOR_NONPOSITIVE = "denominator_nonpositive"
REASON_COSTS_UNAVAILABLE = "recorded_costs_unavailable"
REASON_SUBTYPE_UNAVAILABLE = "cost_subtype_not_separately_classified"


class BrokerCostEfficiencyScopeError(RuntimeError):
    """Raised when the broker cost-efficiency builder is invoked without a matching `BuildScope`."""


class BrokerCostEfficiencyAccessError(RuntimeError):
    """Raised when the scoped user has no `BrokerUserAccess` row for the selected broker.

    Turnover must be share-adjusted to reconcile with the engine's already
    share-adjusted fee/invested/NAV figures, so a missing ownership share is a
    hard, explicit failure rather than a silent assumption of full ownership.
    """


def _require_broker_scope(context: BuildContext) -> BuildScope:
    scope = context.scope
    if scope is None:
        raise BrokerCostEfficiencyScopeError("broker.cost_efficiency requires BuildContext.scope")
    if scope.domain is not Domain.BROKER:
        raise BrokerCostEfficiencyScopeError(f"expected Domain.BROKER scope, got {scope.domain!r}")
    if scope.broker_id is None:
        raise BrokerCostEfficiencyScopeError("broker.cost_efficiency requires BuildScope.broker_id")
    return scope


# =============================================================================
# Deterministic period-activity resource (raw settlement transactions)
# =============================================================================


@dataclass(frozen=True, slots=True)
class TradeActivityRecord:
    """A single period transaction reduced to only what turnover/counts need.

    ``amount``/``currency`` are nullable exactly like ``Transaction.amount``/
    ``Transaction.currency``: a trade with a missing amount or currency cannot be
    turned into deterministic target-currency turnover, so it is counted as an
    explicit *unusable* trade rather than dropped or defaulted to zero.
    """

    type: TransactionType
    amount: Decimal | None
    currency: str | None


@dataclass(frozen=True, slots=True)
class BrokerPeriodActivity:
    """A broker's settlement transactions inside ``(period_start, period_end]`` plus ownership share.

    ``ownership_share`` is the scoped user's ``BrokerUserAccess.share_percentage``
    for this broker (0..1); turnover magnitudes are multiplied by it so the
    exposed turnover reconciles with the engine's share-adjusted fee/invested/NAV
    figures.
    """

    records: tuple[TradeActivityRecord, ...]
    ownership_share: Decimal


# `ResourceKey.expected_type` is validated by `BuildContext`; defined here now
# that the resource class exists so counts/turnover load once per request.
_BROKER_PERIOD_ACTIVITY_RESOURCE = ResourceKey("broker.period_activity", BrokerPeriodActivity)


async def _query_broker_period_transactions(session: AsyncSession, *, broker_id: int, period_start: Date, period_end: Date) -> Sequence[Transaction]:
    """Loads every settlement transaction for one broker within ``(period_start, period_end]``.

    The period is start-exclusive / end-inclusive to match exactly how
    ``PortfolioService`` accumulates period fees/flows (``tx.date > date_from and
    tx.date <= date_to``); an inclusive start would double-count a
    period-boundary trade against a fee numerator that excludes it. Isolated as a
    module-level function (not an inline closure) so it is the single
    deterministic DB seam the tests exercise/monkeypatch.
    """
    stmt = select(Transaction).where(Transaction.broker_id == broker_id).where(Transaction.date > period_start).where(Transaction.date <= period_end).order_by(Transaction.date, Transaction.id)
    return list((await session.execute(stmt)).scalars().all())


async def _load_broker_ownership_share(session: AsyncSession, *, user_id: int, broker_id: int) -> Decimal | None:
    """The scoped user's ownership share for ``broker_id``, or ``None`` when no access row exists."""
    stmt = select(BrokerUserAccess.share_percentage).where(BrokerUserAccess.user_id == user_id).where(BrokerUserAccess.broker_id == broker_id)
    share = (await session.execute(stmt)).scalars().first()
    if share is None:
        return None
    return share if isinstance(share, Decimal) else Decimal(str(share))


async def _load_broker_period_activity(context: BuildContext, scope: BuildScope) -> BrokerPeriodActivity:
    async def _loader(session: AsyncSession) -> BrokerPeriodActivity:
        share = await _load_broker_ownership_share(session, user_id=scope.user_id, broker_id=scope.broker_id)
        if share is None:
            raise BrokerCostEfficiencyAccessError(f"user {scope.user_id} has no BrokerUserAccess for broker {scope.broker_id}; cannot compute share-adjusted turnover")
        transactions = await _query_broker_period_transactions(session, broker_id=scope.broker_id, period_start=scope.period_start, period_end=scope.period_end)
        records = tuple(TradeActivityRecord(type=tx.type, amount=tx.amount, currency=tx.currency) for tx in transactions)
        return BrokerPeriodActivity(records=records, ownership_share=share)

    return await context.db_resource(_BROKER_PERIOD_ACTIVITY_RESOURCE, _loader)


# =============================================================================
# Payload models
# =============================================================================


class FeeStatus(StrEnum):
    """Availability semantics shared by recorded costs and derived ratios."""

    RECORDED = "recorded"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"


class TurnoverCoverage(StrictModel):
    """Explicit target-currency turnover coverage of the period's trades."""

    trade_count: int = Field(ge=0)
    target_currency_trade_count: int = Field(ge=0)
    other_currency_trade_count: int = Field(ge=0)
    unusable_trade_count: int = Field(ge=0, description="BUY/SELL trades with a missing amount or currency; excluded from turnover, never dropped or zeroed.")
    complete: bool = Field(description="True when every counted trade settled in the report target currency with a usable amount (nothing excluded from turnover).")


class TurnoverSummary(StrictModel):
    """Deterministic BUY/SELL turnover in the report target currency."""

    gross_turnover: Currency = Field(description="Σ |amount| over BUY+SELL trades settled in target_currency.")
    buy_turnover: Currency
    sell_turnover: Currency
    coverage: TurnoverCoverage


class RecordedCostAmount(StrictModel):
    """One typed recorded-cost category with explicit source-row evidence."""

    status: FeeStatus
    amount: Currency | None = None
    transaction_count: int = Field(ge=0)
    reason_code: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> RecordedCostAmount:
        if self.status is FeeStatus.RECORDED:
            if self.amount is None or self.reason_code is not None:
                raise ValueError("recorded cost amounts require amount and no reason_code")
        elif self.amount is not None or not self.reason_code:
            raise ValueError("unavailable/not-applicable cost amounts require reason_code and no amount")
        return self


class CostContributor(StrictModel):
    """Typed fee/tax contributor aggregate; no transaction row IDs or free text."""

    category: str
    amount: Currency
    transaction_count: int = Field(ge=1)


class CostSourceCoverage(StrictModel):
    """Coverage of the typed FEE/TAX source rows used by this component."""

    source_code: str = "portfolio_report_typed_fee_tax_transactions_v1"
    fee_transaction_count: int = Field(ge=0)
    tax_transaction_count: int = Field(ge=0)
    target_currency: str
    subtype_classification_status: FeeStatus = FeeStatus.UNAVAILABLE
    subtype_reason_code: str = REASON_SUBTYPE_UNAVAILABLE


class CostDenominators(StrictModel):
    """All deterministic denominators exposed alongside the ratios that use them."""

    gross_traded_amount: Currency
    average_nav: Currency | None = None
    average_nav_method: str | None = None
    average_nav_observation_count: int = Field(default=0, ge=0)
    average_nav_available_start: Date | None = None
    average_nav_available_end: Date | None = None
    total_invested: Currency | None = None
    period_income: Currency | None = None
    trade_count: int = Field(ge=0)


class CostRatio(StrictModel):
    """A single cost ratio with formula, operands, unit, coverage and status.

    ``recorded`` means a deterministic value is available; ``unavailable`` means
    required source evidence is missing/incomplete; ``not_applicable`` means the
    inputs exist but the denominator is non-positive, so the ratio has no useful
    meaning for this period.
    """

    status: FeeStatus
    formula: str
    numerator: Currency | None = None
    denominator: Currency | None = None
    value_ratio: SafeDecimal | None = None
    unit: str = "percent"
    coverage_status: str
    reason_code: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> CostRatio:
        if self.status is FeeStatus.RECORDED:
            if self.value_ratio is None or self.numerator is None or self.denominator is None or self.reason_code is not None:
                raise ValueError("recorded cost ratios require operands/value and no reason_code")
        elif self.value_ratio is not None or not self.reason_code:
            raise ValueError("unavailable/not-applicable ratios require reason_code and no value")
        return self


class BrokerCostEfficiencyPayload(StrictModel):
    """Renderer-neutral broker cost-efficiency evidence: activity + turnover + recorded fees + ratios."""

    broker_id: int
    period_start: Date
    period_end: Date
    target_currency: str

    transaction_count: int = Field(ge=0, description="All settlement transactions for this broker in (period_start, period_end].")
    trade_count: int = Field(ge=0, description="BUY + SELL transactions in the period.")
    buy_count: int = Field(ge=0)
    sell_count: int = Field(ge=0)
    ownership_share_ratio: SafeDecimal = Field(description="Scoped user's BrokerUserAccess.share_percentage (0..1) applied to turnover magnitudes.")

    turnover: TurnoverSummary
    fees: RecordedCostAmount
    taxes: RecordedCostAmount
    total_costs: RecordedCostAmount
    trading_costs: RecordedCostAmount
    fx_costs: RecordedCostAmount
    other_costs: RecordedCostAmount
    cost_contributors: tuple[CostContributor, ...] = ()
    unallocated_costs: Currency | None = None
    source_coverage: CostSourceCoverage
    denominators: CostDenominators

    fees_to_turnover: CostRatio
    fees_to_invested: CostRatio
    fees_to_average_nav: CostRatio
    fees_to_income: CostRatio
    total_costs_to_average_nav: CostRatio


# =============================================================================
# Builder
# =============================================================================


def _abs(value: Decimal) -> Decimal:
    return -value if value < 0 else value


def _build_turnover(activity: BrokerPeriodActivity, *, target_currency: str) -> tuple[TurnoverSummary, int, int, int]:
    """Computes deterministic share-adjusted target-currency turnover and BUY/SELL counts.

    Turnover magnitudes are multiplied by ``activity.ownership_share`` so they sit
    on the same ownership basis as the engine's share-adjusted fee/invested/NAV
    figures. Trades with a missing amount or currency are counted as *unusable*
    (never crash, never silently omitted) and mark coverage incomplete. Returns
    ``(turnover_summary, trade_count, buy_count, sell_count)``.
    """
    share = activity.ownership_share
    buy_count = 0
    sell_count = 0
    target_trade_count = 0
    other_trade_count = 0
    unusable_trade_count = 0
    buy_turnover = Decimal("0")
    sell_turnover = Decimal("0")
    for record in activity.records:
        if record.type not in TRADE_TYPES:
            continue
        if record.type is TransactionType.BUY:
            buy_count += 1
        else:
            sell_count += 1
        if record.amount is None or record.currency is None:
            unusable_trade_count += 1
            continue
        if record.currency == target_currency:
            target_trade_count += 1
            magnitude = _abs(record.amount) * share
            if record.type is TransactionType.BUY:
                buy_turnover += magnitude
            else:
                sell_turnover += magnitude
        else:
            other_trade_count += 1

    trade_count = buy_count + sell_count
    coverage = TurnoverCoverage(
        trade_count=trade_count,
        target_currency_trade_count=target_trade_count,
        other_currency_trade_count=other_trade_count,
        unusable_trade_count=unusable_trade_count,
        complete=other_trade_count == 0 and unusable_trade_count == 0,
    )
    turnover = TurnoverSummary(
        gross_turnover=Currency(code=target_currency, amount=buy_turnover + sell_turnover),
        buy_turnover=Currency(code=target_currency, amount=buy_turnover),
        sell_turnover=Currency(code=target_currency, amount=sell_turnover),
        coverage=coverage,
    )
    return turnover, trade_count, buy_count, sell_count


def _records_for_type(activity: BrokerPeriodActivity, transaction_type: TransactionType) -> tuple[TradeActivityRecord, ...]:
    return tuple(record for record in activity.records if record.type is transaction_type)


def _recorded_cost_amount(
    *,
    summary_amount: Currency | None,
    records: Sequence[TradeActivityRecord],
    target_currency: str,
    unavailable_reason: str,
) -> RecordedCostAmount:
    if summary_amount is not None:
        return RecordedCostAmount(status=FeeStatus.RECORDED, amount=summary_amount, transaction_count=len(records))
    if records and all(record.amount is not None and record.amount == 0 for record in records):
        return RecordedCostAmount(
            status=FeeStatus.RECORDED,
            amount=Currency(code=target_currency, amount=Decimal("0")),
            transaction_count=len(records),
        )
    return RecordedCostAmount(
        status=FeeStatus.UNAVAILABLE,
        transaction_count=len(records),
        reason_code=unavailable_reason,
    )


def _unclassified_cost_category() -> RecordedCostAmount:
    return RecordedCostAmount(
        status=FeeStatus.UNAVAILABLE,
        transaction_count=0,
        reason_code=REASON_SUBTYPE_UNAVAILABLE,
    )


def _total_recorded_costs(
    *,
    summary: PortfolioSummary | None,
    fees: RecordedCostAmount,
    taxes: RecordedCostAmount,
    target_currency: str,
) -> RecordedCostAmount:
    transaction_count = fees.transaction_count + taxes.transaction_count
    if transaction_count == 0:
        return RecordedCostAmount(
            status=FeeStatus.UNAVAILABLE,
            transaction_count=0,
            reason_code=REASON_COSTS_UNAVAILABLE,
        )
    if summary is not None and summary.period_fees_taxes is not None:
        return RecordedCostAmount(
            status=FeeStatus.RECORDED,
            amount=summary.period_fees_taxes,
            transaction_count=transaction_count,
        )
    if fees.status is FeeStatus.RECORDED and taxes.status is FeeStatus.RECORDED:
        return RecordedCostAmount(
            status=FeeStatus.RECORDED,
            amount=Currency(code=target_currency, amount=fees.amount.amount + taxes.amount.amount),
            transaction_count=transaction_count,
        )
    return RecordedCostAmount(
        status=FeeStatus.UNAVAILABLE,
        transaction_count=transaction_count,
        reason_code=REASON_COSTS_UNAVAILABLE,
    )


def _available_ratio(*, formula: str, numerator: Currency, denominator: Currency, coverage_status: str = "complete") -> CostRatio:
    return CostRatio(
        status=FeeStatus.RECORDED,
        formula=formula,
        numerator=numerator,
        denominator=denominator,
        value_ratio=numerator.amount / denominator.amount,
        coverage_status=coverage_status,
    )


def _missing_ratio(
    *,
    formula: str,
    status: FeeStatus,
    reason_code: str,
    numerator: Currency | None = None,
    denominator: Currency | None = None,
    coverage_status: str,
) -> CostRatio:
    return CostRatio(
        status=status,
        formula=formula,
        numerator=numerator,
        denominator=denominator,
        coverage_status=coverage_status,
        reason_code=reason_code,
    )


def _cost_to_denominator(
    cost: RecordedCostAmount,
    denominator: Currency | None,
    *,
    formula: str,
    cost_unavailable_reason: str = REASON_FEES_UNAVAILABLE,
    unavailable_reason: str = REASON_DENOMINATOR_UNAVAILABLE,
    coverage_status: str = "complete",
) -> CostRatio:
    numerator = cost.amount
    if cost.status is not FeeStatus.RECORDED or numerator is None:
        return _missing_ratio(
            formula=formula,
            status=FeeStatus.UNAVAILABLE,
            reason_code=cost_unavailable_reason,
            denominator=denominator,
            coverage_status=coverage_status,
        )
    if denominator is None:
        return _missing_ratio(
            formula=formula,
            status=FeeStatus.UNAVAILABLE,
            reason_code=unavailable_reason,
            numerator=numerator,
            coverage_status="unavailable",
        )
    if denominator.amount <= 0:
        return _missing_ratio(
            formula=formula,
            status=FeeStatus.NOT_APPLICABLE,
            reason_code=REASON_DENOMINATOR_NONPOSITIVE,
            numerator=numerator,
            denominator=denominator,
            coverage_status=coverage_status,
        )
    return _available_ratio(
        formula=formula,
        numerator=numerator,
        denominator=denominator,
        coverage_status=coverage_status,
    )


def _fees_to_turnover(fees: RecordedCostAmount, turnover: TurnoverSummary) -> CostRatio:
    formula = "recorded_fees / gross_traded_amount"
    denominator = turnover.gross_turnover
    if fees.status is not FeeStatus.RECORDED or fees.amount is None:
        return _missing_ratio(
            formula=formula,
            status=FeeStatus.UNAVAILABLE,
            reason_code=REASON_FEES_UNAVAILABLE,
            denominator=denominator,
            coverage_status="complete" if turnover.coverage.complete else "partial",
        )
    if not turnover.coverage.complete:
        return _missing_ratio(
            formula=formula,
            status=FeeStatus.UNAVAILABLE,
            reason_code=REASON_TURNOVER_INCOMPLETE,
            numerator=fees.amount,
            denominator=denominator,
            coverage_status="partial",
        )
    if denominator.amount <= 0:
        return _missing_ratio(
            formula=formula,
            status=FeeStatus.NOT_APPLICABLE,
            reason_code=REASON_TURNOVER_ZERO,
            numerator=fees.amount,
            denominator=denominator,
            coverage_status="complete",
        )
    return _available_ratio(formula=formula, numerator=fees.amount, denominator=denominator)


def _average_nav(
    report: PortfolioReportResponse,
    summary: PortfolioSummary | None,
    *,
    target_currency: str,
) -> tuple[Currency | None, str | None, int, Date | None, Date | None]:
    history = tuple(report.history or ())
    if history:
        values = tuple(point.nav_value.amount for point in history)
        return (
            Currency(code=target_currency, amount=sum(values, Decimal("0")) / Decimal(len(values))),
            "arithmetic_mean_of_available_daily_nav",
            len(values),
            history[0].date,
            history[-1].date,
        )
    if summary is not None and summary.period_nav_start is not None and summary.net_worth is not None:
        return (
            Currency(code=target_currency, amount=(summary.period_nav_start.amount + summary.net_worth.amount) / Decimal("2")),
            "endpoint_mean_nav_proxy",
            2,
            None,
            None,
        )
    return None, None, 0, None, None


async def _build_broker_cost_efficiency(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> BrokerCostEfficiencyPayload:
    scope = _require_broker_scope(context)
    # Shared (memoized) `broker.report` load - no extra `get_report` call.
    report = await load_portfolio_report(context, scope, BROKER_REPORT_RESOURCE)
    summary = report.summary
    activity = await _load_broker_period_activity(context, scope)
    currency_code = scope.target_currency

    turnover, trade_count, buy_count, sell_count = _build_turnover(activity, target_currency=currency_code)
    fee_records = _records_for_type(activity, TransactionType.FEE)
    tax_records = _records_for_type(activity, TransactionType.TAX)
    fees = _recorded_cost_amount(
        summary_amount=summary.period_fees if summary else None,
        records=fee_records,
        target_currency=currency_code,
        unavailable_reason=REASON_FEES_UNAVAILABLE,
    )
    taxes = _recorded_cost_amount(
        summary_amount=summary.period_taxes if summary else None,
        records=tax_records,
        target_currency=currency_code,
        unavailable_reason=REASON_COSTS_UNAVAILABLE,
    )
    total_costs = _total_recorded_costs(
        summary=summary,
        fees=fees,
        taxes=taxes,
        target_currency=currency_code,
    )
    invested = summary.total_invested if summary else None
    income = summary.period_income if summary else None
    average_nav, average_nav_method, average_nav_count, average_nav_start, average_nav_end = _average_nav(
        report,
        summary,
        target_currency=currency_code,
    )
    contributors = tuple(CostContributor(category=category, amount=cost.amount, transaction_count=cost.transaction_count) for category, cost in (("fees", fees), ("taxes", taxes)) if cost.status is FeeStatus.RECORDED and cost.amount is not None and cost.transaction_count > 0)
    allocated_amount = sum((item.amount.amount for item in contributors), Decimal("0"))
    unallocated_costs = Currency(code=currency_code, amount=total_costs.amount.amount - allocated_amount) if total_costs.status is FeeStatus.RECORDED and total_costs.amount is not None else None
    denominators = CostDenominators(
        gross_traded_amount=turnover.gross_turnover,
        average_nav=average_nav,
        average_nav_method=average_nav_method,
        average_nav_observation_count=average_nav_count,
        average_nav_available_start=average_nav_start,
        average_nav_available_end=average_nav_end,
        total_invested=invested,
        period_income=income,
        trade_count=trade_count,
    )

    return BrokerCostEfficiencyPayload(
        broker_id=scope.broker_id,
        period_start=scope.period_start,
        period_end=scope.period_end,
        target_currency=currency_code,
        transaction_count=len(activity.records),
        trade_count=trade_count,
        buy_count=buy_count,
        sell_count=sell_count,
        ownership_share_ratio=activity.ownership_share,
        turnover=turnover,
        fees=fees,
        taxes=taxes,
        total_costs=total_costs,
        trading_costs=_unclassified_cost_category(),
        fx_costs=_unclassified_cost_category(),
        other_costs=_unclassified_cost_category(),
        cost_contributors=contributors,
        unallocated_costs=unallocated_costs,
        source_coverage=CostSourceCoverage(
            fee_transaction_count=len(fee_records),
            tax_transaction_count=len(tax_records),
            target_currency=currency_code,
        ),
        denominators=denominators,
        fees_to_turnover=_fees_to_turnover(fees, turnover),
        fees_to_invested=_cost_to_denominator(fees, invested, formula="recorded_fees / total_invested"),
        fees_to_average_nav=_cost_to_denominator(fees, average_nav, formula="recorded_fees / average_nav"),
        fees_to_income=_cost_to_denominator(fees, income, formula="recorded_fees / recorded_income"),
        total_costs_to_average_nav=_cost_to_denominator(
            total_costs,
            average_nav,
            formula="recorded_total_costs / average_nav",
            cost_unavailable_reason=REASON_COSTS_UNAVAILABLE,
        ),
    )


# =============================================================================
# Component spec (real builder ready for the coordinator integration gate)
# =============================================================================


BROKER_COST_EFFICIENCY_COMPONENT = ComponentSpec(
    component_id="broker.cost_efficiency",
    version=1,
    domains=frozenset({Domain.BROKER}),
    output_model=BrokerCostEfficiencyPayload,
    builder=_build_broker_cost_efficiency,
    dependencies=("broker.flows_income_costs",),
    period_behavior=PeriodBehavior.WINDOWED,
)

BROKER_COST_EFFICIENCY_COMPONENTS: tuple[ComponentSpec, ...] = (BROKER_COST_EFFICIENCY_COMPONENT,)


__all__ = [
    "BROKER_COST_EFFICIENCY_COMPONENT",
    "BROKER_COST_EFFICIENCY_COMPONENTS",
    "REASON_DENOMINATOR_UNAVAILABLE",
    "REASON_DENOMINATOR_NONPOSITIVE",
    "REASON_COSTS_UNAVAILABLE",
    "REASON_FEES_UNAVAILABLE",
    "REASON_SUBTYPE_UNAVAILABLE",
    "REASON_TURNOVER_INCOMPLETE",
    "REASON_TURNOVER_ZERO",
    "TRADE_TYPES",
    "BrokerCostEfficiencyAccessError",
    "BrokerCostEfficiencyPayload",
    "BrokerCostEfficiencyScopeError",
    "BrokerPeriodActivity",
    "CostContributor",
    "CostDenominators",
    "CostRatio",
    "CostSourceCoverage",
    "FeeStatus",
    "RecordedCostAmount",
    "TradeActivityRecord",
    "TurnoverCoverage",
    "TurnoverSummary",
]
