"""Isolated Portfolio dated-income-evidence component (``portfolio.income_timeline``).

Motivation (``ai-adequacy-v1-remediate-portfolio``): the aggregate
``portfolio.flows_income`` component carries ``period_income`` plus per-asset
``Income`` effect rows. Baseline adequacy
rating flagged the absence of concrete, *dated* historical income evidence: an
analyst cannot see *when* each dividend/interest cash-flow actually landed, on
which broker/asset, in which native currency, and how it was converted to the
presentation currency. This component adds exactly that - a deterministic,
honestly-typed income *timeline* built from the recorded income transactions -
**without** re-deriving or replacing the retained aggregate.

Design invariants:

- **Realized history only.** Only ``DIVIDEND``/``INTEREST`` transactions that
  actually exist in the ledger are included. There is no bond forecast, no
  future coupon, no yield/accrual projection, no invented income.
- **Permissioned + windowed.** Rows are restricted to brokers the requesting
  user actually has access to (``resolve_accessible_broker_ids`` intersected
  with ``BuildScope.broker_scope``) and to the *selected period*. The period
  convention deliberately mirrors the retained aggregate
  ``PortfolioService.get_report`` income window - strictly after
  ``period_start`` and up to/including ``snapshot_as_of`` (``(start, end]``) -
  so this timeline and ``portfolio.flows_income`` cannot contradict each other.
  ``period_end`` is the upper bound, so a future-dated row can never appear.
- **Ownership-share aware.** Native amounts are ``abs(amount) * share_percentage``
  exactly like the report's ``period_income`` accumulation, so a co-owned
  broker contributes only the user's economic share.
- **Honest FX.** Conversion to the target currency uses the shared
  ``backend.app.services.fx.convert_bulk`` (unlimited backward-fill), preserving
  the rate date and backward-fill flag as provenance. A row whose rate is
  missing keeps its native amount, sets ``target_amount=None`` and carries a
  machine-readable ``conversion_reason`` - a missing rate is **never** coerced
  to zero and is surfaced through the summary ``conversion_status``.
- **Three honest statuses.** ``EMPTY`` (no recorded income - a valid success)
  is distinct from ``FAILED`` (the ledger query itself failed) and from a
  partial/absent *conversion* (data present, some/all target amounts absent).
- **No DB identifiers.** Only business identities (``asset_id``/``broker_id``
  and their names/tickers) are exposed - never ``Transaction.id``,
  ``related_transaction_id`` or ``asset_event_id``.

Detail policy is **component-local and monotonic** (it does not touch the global
Compact/P/M/K selection): ``COMPACT`` aggregates the timeline by
``(month, asset, income_type)``; ``STANDARD`` exposes the summary plus a bounded
set of the most recent dated rows; ``FULL`` exposes every dated row. The summary
totals are always computed over the *full* transaction set regardless of detail
level, so bounding never loses aggregate information.

This module is deliberately standalone: it exports a `ComponentSpec` tuple but is
**not** wired into ``components/catalog.py`` or any dataset/analysis registry -
that shared integration is left to the coordinator (see the module-level
integration notes returned to the task).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date as Date
from decimal import Decimal
from enum import StrEnum

from pydantic import Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import BrokerUserAccess, Transaction, TransactionType
from backend.app.schemas.common import Currency, CurrencyCode, StrictModel
from backend.app.services.ai_export.components.envelope import SectionEnvelope
from backend.app.services.ai_export.components.payloads.portfolio_broker import (
    load_asset_metadata,
    load_broker_metadata,
    resolve_accessible_broker_ids,
)
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.types import BuildScope, Domain, PeriodBehavior, ResourceKey
from backend.app.services.ai_export.dependencies import BuildContext, ResourceLoadError
from backend.app.services.fx import convert_bulk

# Only these two ledger types are realized cash income (see `TransactionType`).
_INCOME_TYPES: frozenset[TransactionType] = frozenset({TransactionType.DIVIDEND, TransactionType.INTEREST})

# Component-local bound for the STANDARD detail level's dated-row window: the most
# recent N income rows are exposed verbatim; older rows are summarised only
# through the always-complete summary block (never silently dropped).
_STANDARD_MAX_ROWS = 60

# Request-scoped memo keys (loaded at most once per request via `db_resource`).
# `_INCOME_RECORDS_RESOURCE` is typed against `_IncomeTimelineData` at its
# definition below (after the dataclass is declared), avoiding a forward reference.
_INCOME_CONVERSIONS_RESOURCE: ResourceKey[list] = ResourceKey("portfolio.income_timeline_conversions", list)

# Machine-readable reason a single row carries no deterministic target amount.
REASON_RATE_NOT_FOUND = "fx_rate_not_found"
# Machine-readable reason the whole timeline could not be sourced.
REASON_LEDGER_QUERY_FAILED = "income_ledger_query_failed"
REASON_CONVERSION_FAILED = "income_conversion_failed"

# Deterministic provenance source tag for a converted row.
CONVERSION_SOURCE = "fx_convert_bulk"


class IncomeTimelineScopeError(RuntimeError):
    """Raised when the income timeline builder is invoked without a Portfolio `BuildScope`."""


class IncomeTimelineStatus(StrEnum):
    """Honest lifecycle status of the income timeline section."""

    OK = "ok"  # at least one recorded income transaction in scope/period
    EMPTY = "empty"  # no recorded income - a valid, successful empty result
    FAILED = "failed"  # the ledger query itself failed (source/query error)


class ConversionStatus(StrEnum):
    """Whether the native->target conversion was deterministic for the whole set."""

    COMPLETE = "complete"  # every row converted (identity or a rate was found)
    PARTIAL = "partial"  # some rows converted, at least one rate was missing
    UNAVAILABLE = "unavailable"  # rows exist but not a single rate was found


# =============================================================================
# Internal (non-serialized) request-scoped ledger snapshot
# =============================================================================


@dataclass(frozen=True, slots=True)
class _IncomeRecord:
    """One realized income cash-flow, ownership-share-adjusted, native currency."""

    date: Date
    asset_id: int | None
    broker_id: int
    income_type: TransactionType
    amount: Decimal  # abs(amount) * share, in `currency`
    currency: str


@dataclass(frozen=True, slots=True)
class _IncomeTimelineData:
    """Everything the builder needs from the ledger, resolved once per request."""

    records: tuple[_IncomeRecord, ...] = ()
    asset_names: Mapping[int, str] = field(default_factory=dict)
    asset_tickers: Mapping[int, str | None] = field(default_factory=dict)
    broker_names: Mapping[int, str] = field(default_factory=dict)


# Typed request-scoped memo key for the ledger snapshot (declared here, after
# `_IncomeTimelineData`, so the expected type is the concrete dataclass rather
# than a bare `object` and without an awkward forward reference).
_INCOME_RECORDS_RESOURCE: ResourceKey[_IncomeTimelineData] = ResourceKey("portfolio.income_timeline_records", _IncomeTimelineData)


# =============================================================================
# Public payload models (extra="forbid")
# =============================================================================


class ConversionProvenance(StrictModel):
    """Deterministic FX provenance for one converted income row."""

    source: str = CONVERSION_SOURCE
    rate_date: Date
    backfill_applied: bool
    identity: bool = False


class IncomeTimelineRow(StrictModel):
    """One dated realized income cash-flow, currency-safe and self-describing.

    ``asset_id``/``broker_id`` are business identities (never the transaction DB
    id). ``target_amount``/``conversion`` are present together only when a
    deterministic rate exists; otherwise ``conversion_reason`` explains the gap
    and the native amount is retained unchanged.
    """

    date: Date
    income_type: str
    broker_id: int
    broker_name: str
    asset_id: int | None = None
    asset_name: str | None = None
    asset_ticker: str | None = None
    native_amount: Currency
    target_amount: Currency | None = None
    conversion: ConversionProvenance | None = None
    conversion_reason: str | None = None

    @model_validator(mode="after")
    def _validate_conversion(self) -> IncomeTimelineRow:
        converted = self.target_amount is not None
        if converted:
            if self.conversion is None:
                raise ValueError("a converted income row requires conversion provenance")
            if self.conversion_reason is not None:
                raise ValueError("a converted income row must not carry a conversion_reason")
        else:
            if self.conversion is not None:
                raise ValueError("an unconverted income row must not carry conversion provenance")
            if not self.conversion_reason:
                raise ValueError("an unconverted income row requires a conversion_reason")
        return self


class AggregatedIncomeRow(StrictModel):
    """One ``COMPACT`` bucket: recorded income grouped by ``(month, asset, type)``.

    ``month`` is the ``YYYY-MM`` settlement month. Native amounts are listed per
    distinct native currency (deterministic order). ``target_amount`` is present
    only when every transaction in the bucket converted deterministically.
    """

    month: str
    income_type: str
    asset_id: int | None = None
    asset_name: str | None = None
    asset_ticker: str | None = None
    transaction_count: int = Field(ge=1)
    native_amounts: tuple[Currency, ...]
    target_amount: Currency | None = None
    conversion_complete: bool


class IncomeTimelineSummary(StrictModel):
    """Aggregate income summary computed over the *full* transaction set.

    Always present for ``OK``/``EMPTY`` regardless of detail level, so bounding
    the dated rows never loses aggregate information. ``target_total`` is present
    only when ``conversion_status == COMPLETE`` (a partial/absent conversion is
    surfaced honestly rather than summed to a misleading subtotal).
    """

    target_currency: CurrencyCode
    transaction_count: int = Field(ge=0)
    dividend_count: int = Field(ge=0)
    interest_count: int = Field(ge=0)
    distinct_asset_count: int = Field(ge=0)
    distinct_broker_count: int = Field(ge=0)
    earliest_date: Date | None = None
    latest_date: Date | None = None
    native_totals: tuple[Currency, ...] = ()
    target_total: Currency | None = None
    conversion_status: ConversionStatus


class IncomeTimelinePayload(StrictModel):
    """Deterministic dated income evidence for one Portfolio scope/period.

    Statuses: ``OK`` (dated/aggregated income present + summary), ``EMPTY`` (no
    recorded income - valid success, zeroed summary), ``FAILED`` (ledger query
    failed - ``reason_code``/``message`` only). Detail policy is monotonic and
    local: ``COMPACT`` populates ``aggregated_rows`` only; ``STANDARD``/``FULL``
    populate ``rows`` only (``STANDARD`` bounded, ``rows_truncated`` /
    ``rows_omitted_count`` disclose any omission).
    """

    status: IncomeTimelineStatus
    detail_level: str
    period_convention: str = "exclusive_start_inclusive_end"
    reason_code: str | None = None
    message: str | None = None

    summary: IncomeTimelineSummary | None = None
    rows: tuple[IncomeTimelineRow, ...] = ()
    aggregated_rows: tuple[AggregatedIncomeRow, ...] = ()
    rows_truncated: bool = False
    rows_omitted_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _validate_status_invariants(self) -> IncomeTimelinePayload:  # noqa: C901 — flat status invariant raises
        if self.status is IncomeTimelineStatus.FAILED:
            if not self.reason_code or not self.message:
                raise ValueError("failed income timeline requires reason_code and message")
            if self.summary is not None or self.rows or self.aggregated_rows:
                raise ValueError("failed income timeline must not carry summary/rows")
            if self.rows_truncated or self.rows_omitted_count:
                raise ValueError("failed income timeline must not disclose truncation")
            return self

        if self.reason_code is not None or self.message is not None:
            raise ValueError("successful income timeline must not carry reason_code/message")
        if self.summary is None:
            raise ValueError("successful income timeline requires a summary")

        if self.status is IncomeTimelineStatus.EMPTY:
            if self.rows or self.aggregated_rows:
                raise ValueError("empty income timeline must not carry rows")
            if self.summary.transaction_count != 0:
                raise ValueError("empty income timeline requires a zero transaction_count")
            if self.rows_truncated or self.rows_omitted_count:
                raise ValueError("empty income timeline must not disclose truncation")
            return self

        # OK
        if self.summary.transaction_count == 0:
            raise ValueError("ok income timeline requires a non-zero transaction_count")
        if self.detail_level == "compact":
            if self.rows:
                raise ValueError("compact income timeline must not carry dated rows")
            if not self.aggregated_rows:
                raise ValueError("compact income timeline requires aggregated_rows")
            if self.rows_truncated or self.rows_omitted_count:
                raise ValueError("compact income timeline must not disclose row truncation")
        else:
            if self.aggregated_rows:
                raise ValueError("standard/full income timeline must not carry aggregated_rows")
            if not self.rows:
                raise ValueError("standard/full income timeline requires dated rows")
            if self.rows_truncated != (self.rows_omitted_count > 0):
                raise ValueError("rows_truncated must agree with rows_omitted_count")
        return self


# =============================================================================
# Scope / ledger loading
# =============================================================================


def _require_portfolio_scope(context: BuildContext) -> BuildScope:
    scope = context.scope
    if scope is None:
        raise IncomeTimelineScopeError("portfolio.income_timeline requires BuildContext.scope")
    if scope.domain is not Domain.PORTFOLIO:
        raise IncomeTimelineScopeError(f"expected Domain.PORTFOLIO scope, got {scope.domain!r}")
    return scope


async def _load_income_records(context: BuildContext, scope: BuildScope) -> _IncomeTimelineData:
    """Loads the realized income ledger snapshot for `scope`, memoized once per request.

    Permission + period semantics live entirely here: the query is intersected
    with the user's accessible brokers and filtered to ``(period_start,
    snapshot_as_of]``. Amounts are ``abs(amount) * share_percentage`` to mirror
    the retained ``period_income`` aggregate. An empty result is a valid,
    successfully-built empty snapshot (never a failure).
    """

    async def _loader(session: AsyncSession) -> _IncomeTimelineData:
        accessible = set(await resolve_accessible_broker_ids(session, scope.user_id))
        if scope.broker_scope:
            effective = sorted(b for b in scope.broker_scope if b in accessible)
        else:
            effective = sorted(accessible)
        if not effective:
            return _IncomeTimelineData()

        share_result = await session.execute(
            select(BrokerUserAccess.broker_id, BrokerUserAccess.share_percentage).where(
                BrokerUserAccess.user_id == scope.user_id,
                BrokerUserAccess.broker_id.in_(effective),
            )
        )
        shares: dict[int, Decimal] = {int(broker_id): (share if share is not None else Decimal("1")) for broker_id, share in share_result.all()}

        stmt = select(Transaction).where(
            Transaction.broker_id.in_(effective),
            Transaction.type.in_(_INCOME_TYPES),
            Transaction.date > scope.period_start,
            Transaction.date <= scope.snapshot_as_of,
        )
        txns = (await session.execute(stmt)).scalars().all()

        records: list[_IncomeRecord] = []
        asset_ids: set[int] = set()
        for tx in txns:
            if tx.currency is None or tx.amount is None:
                raise ValueError("recorded income transaction is missing amount or currency")
            share = shares.get(tx.broker_id)
            if share is None:
                raise ValueError("accessible income transaction has no ownership-share record")
            records.append(
                _IncomeRecord(
                    date=tx.date,
                    asset_id=tx.asset_id,
                    broker_id=tx.broker_id,
                    income_type=tx.type,
                    amount=abs(tx.amount) * share,
                    currency=tx.currency,
                )
            )
            if tx.asset_id is not None:
                asset_ids.add(tx.asset_id)

        assets = await load_asset_metadata(session, sorted(asset_ids))
        brokers = await load_broker_metadata(session, effective)
        return _IncomeTimelineData(
            records=tuple(records),
            asset_names={aid: asset.display_name for aid, asset in assets.items()},
            asset_tickers={aid: asset.identifier_ticker for aid, asset in assets.items()},
            broker_names={bid: broker.name for bid, broker in brokers.items()},
        )

    return await context.db_resource(_INCOME_RECORDS_RESOURCE, _loader)


async def _convert_income(context: BuildContext, records: Sequence[_IncomeRecord], target_currency: str) -> list:
    """Converts every native income amount to `target_currency`, memoized per request.

    Returns the raw ``convert_bulk`` result list (``(Currency, rate_date,
    backfill)`` or ``None`` per row, index-aligned to `records`). ``raise_on_error``
    is ``False`` so a missing rate yields ``None`` (surfaced per-row) rather than
    failing the whole section.
    """
    if not records:
        return []

    async def _loader(session: AsyncSession) -> list:
        conversions = [(Currency(code=rec.currency, amount=rec.amount), target_currency, rec.date) for rec in records]
        results, _errors = await convert_bulk(session, conversions, raise_on_error=False)
        return results

    return await context.db_resource(_INCOME_CONVERSIONS_RESOURCE, _loader)


# =============================================================================
# Pure row / summary assembly
# =============================================================================


def _record_sort_key(record: _IncomeRecord) -> tuple:
    return (
        record.date,
        record.income_type.value,
        record.broker_id,
        record.asset_id if record.asset_id is not None else -1,
        record.currency,
        record.amount,
    )


def _build_row(record: _IncomeRecord, data: _IncomeTimelineData, conversion: object) -> IncomeTimelineRow:
    native = Currency(code=record.currency, amount=record.amount)
    asset_name = data.asset_names.get(record.asset_id) if record.asset_id is not None else None
    asset_ticker = data.asset_tickers.get(record.asset_id) if record.asset_id is not None else None
    broker_name = data.broker_names.get(record.broker_id, "Unknown broker")

    if conversion is None:
        return IncomeTimelineRow(
            date=record.date,
            income_type=record.income_type.value,
            broker_id=record.broker_id,
            broker_name=broker_name,
            asset_id=record.asset_id,
            asset_name=asset_name,
            asset_ticker=asset_ticker,
            native_amount=native,
            conversion_reason=REASON_RATE_NOT_FOUND,
        )

    converted, rate_date, backfill = conversion
    return IncomeTimelineRow(
        date=record.date,
        income_type=record.income_type.value,
        broker_id=record.broker_id,
        broker_name=broker_name,
        asset_id=record.asset_id,
        asset_name=asset_name,
        asset_ticker=asset_ticker,
        native_amount=native,
        target_amount=Currency(code=converted.code, amount=converted.amount),
        conversion=ConversionProvenance(
            rate_date=rate_date,
            backfill_applied=bool(backfill),
            identity=(record.currency == converted.code),
        ),
    )


def _native_totals(records: Sequence[_IncomeRecord]) -> tuple[Currency, ...]:
    totals: dict[str, Decimal] = {}
    for record in records:
        totals[record.currency] = totals.get(record.currency, Decimal("0")) + record.amount
    return tuple(Currency(code=code, amount=amount) for code, amount in sorted(totals.items()))


def _conversion_status(records: Sequence[_IncomeRecord], conversions: Sequence[object]) -> ConversionStatus:
    if not records:
        return ConversionStatus.COMPLETE
    converted = sum(1 for item in conversions if item is not None)
    if converted == len(records):
        return ConversionStatus.COMPLETE
    if converted == 0:
        return ConversionStatus.UNAVAILABLE
    return ConversionStatus.PARTIAL


def _build_summary(
    records: Sequence[_IncomeRecord],
    conversions: Sequence[object],
    target_currency: str,
) -> IncomeTimelineSummary:
    status = _conversion_status(records, conversions)
    target_total: Currency | None = None
    if records and status is ConversionStatus.COMPLETE:
        total = sum((item[0].amount for item in conversions if item is not None), Decimal("0"))
        target_total = Currency(code=target_currency, amount=total)
    dates = [record.date for record in records]
    return IncomeTimelineSummary(
        target_currency=target_currency,
        transaction_count=len(records),
        dividend_count=sum(1 for r in records if r.income_type is TransactionType.DIVIDEND),
        interest_count=sum(1 for r in records if r.income_type is TransactionType.INTEREST),
        distinct_asset_count=len({r.asset_id for r in records if r.asset_id is not None}),
        distinct_broker_count=len({r.broker_id for r in records}),
        earliest_date=min(dates) if dates else None,
        latest_date=max(dates) if dates else None,
        native_totals=_native_totals(records),
        target_total=target_total,
        conversion_status=status,
    )


def _build_aggregated_rows(
    records: Sequence[_IncomeRecord],
    conversions: Sequence[object],
    data: _IncomeTimelineData,
    target_currency: str,
) -> tuple[AggregatedIncomeRow, ...]:
    """COMPACT view: group by ``(month, asset_id, income_type)`` deterministically."""

    @dataclass
    class _Bucket:
        count: int = 0
        native: dict[str, Decimal] = field(default_factory=dict)
        target_total: Decimal = Decimal("0")
        all_converted: bool = True

    buckets: dict[tuple[str, int, str], _Bucket] = {}
    for record, conversion in zip(records, conversions, strict=True):
        month = f"{record.date.year:04d}-{record.date.month:02d}"
        key = (month, record.asset_id if record.asset_id is not None else -1, record.income_type.value)
        bucket = buckets.setdefault(key, _Bucket())
        bucket.count += 1
        bucket.native[record.currency] = bucket.native.get(record.currency, Decimal("0")) + record.amount
        if conversion is None:
            bucket.all_converted = False
        else:
            bucket.target_total += conversion[0].amount

    rows: list[AggregatedIncomeRow] = []
    for (month, asset_key, income_type), bucket in sorted(buckets.items(), key=lambda item: item[0]):
        asset_id = asset_key if asset_key >= 0 else None
        rows.append(
            AggregatedIncomeRow(
                month=month,
                income_type=income_type,
                asset_id=asset_id,
                asset_name=data.asset_names.get(asset_id) if asset_id is not None else None,
                asset_ticker=data.asset_tickers.get(asset_id) if asset_id is not None else None,
                transaction_count=bucket.count,
                native_amounts=tuple(Currency(code=code, amount=amount) for code, amount in sorted(bucket.native.items())),
                target_amount=(Currency(code=target_currency, amount=bucket.target_total) if bucket.all_converted else None),
                conversion_complete=bucket.all_converted,
            )
        )
    return tuple(rows)


def _build_dated_rows(
    records: Sequence[_IncomeRecord],
    conversions: Sequence[object],
    data: _IncomeTimelineData,
    *,
    max_rows: int | None,
) -> tuple[tuple[IncomeTimelineRow, ...], int]:
    """STANDARD/FULL view: deterministic dated rows, optionally bounded to the most recent `max_rows`."""
    ordered = sorted(range(len(records)), key=lambda idx: _record_sort_key(records[idx]))
    omitted = 0
    if max_rows is not None and len(ordered) > max_rows:
        # Keep the most recent `max_rows` (tail of the ascending order), still
        # rendered ascending; disclose the omitted older count.
        omitted = len(ordered) - max_rows
        ordered = ordered[-max_rows:]
    rows = tuple(_build_row(records[idx], data, conversions[idx]) for idx in ordered)
    return rows, omitted


# =============================================================================
# Builder
# =============================================================================


async def _build_portfolio_income_timeline(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> IncomeTimelinePayload:
    scope = _require_portfolio_scope(context)
    detail = scope.detail_level.value

    try:
        data = await _load_income_records(context, scope)
    except ResourceLoadError:
        return IncomeTimelinePayload(
            status=IncomeTimelineStatus.FAILED,
            detail_level=detail,
            reason_code=REASON_LEDGER_QUERY_FAILED,
            message="The income ledger could not be queried for the selected portfolio scope and period.",
        )

    records = data.records
    if not records:
        return IncomeTimelinePayload(
            status=IncomeTimelineStatus.EMPTY,
            detail_level=detail,
            summary=_build_summary(records, [], scope.target_currency),
        )

    try:
        conversions = await _convert_income(context, records, scope.target_currency)
    except ResourceLoadError:
        return IncomeTimelinePayload(
            status=IncomeTimelineStatus.FAILED,
            detail_level=detail,
            reason_code=REASON_CONVERSION_FAILED,
            message="Income currency conversion could not be completed for the selected portfolio scope and period.",
        )

    summary = _build_summary(records, conversions, scope.target_currency)

    if detail == "compact":
        return IncomeTimelinePayload(
            status=IncomeTimelineStatus.OK,
            detail_level=detail,
            summary=summary,
            aggregated_rows=_build_aggregated_rows(records, conversions, data, scope.target_currency),
        )

    max_rows = _STANDARD_MAX_ROWS if detail == "standard" else None
    rows, omitted = _build_dated_rows(records, conversions, data, max_rows=max_rows)
    return IncomeTimelinePayload(
        status=IncomeTimelineStatus.OK,
        detail_level=detail,
        summary=summary,
        rows=rows,
        rows_truncated=omitted > 0,
        rows_omitted_count=omitted,
    )


# =============================================================================
# Component spec (exported, NOT wired into shared catalog/registries yet)
# =============================================================================


PORTFOLIO_INCOME_TIMELINE_COMPONENT = ComponentSpec(
    component_id="portfolio.income_timeline",
    version=1,
    domains=frozenset({Domain.PORTFOLIO}),
    output_model=IncomeTimelinePayload,
    builder=_build_portfolio_income_timeline,
    period_behavior=PeriodBehavior.WINDOWED,
)

PORTFOLIO_INCOME_TIMELINE_COMPONENTS: tuple[ComponentSpec, ...] = (PORTFOLIO_INCOME_TIMELINE_COMPONENT,)


__all__ = [
    "CONVERSION_SOURCE",
    "PORTFOLIO_INCOME_TIMELINE_COMPONENT",
    "PORTFOLIO_INCOME_TIMELINE_COMPONENTS",
    "REASON_CONVERSION_FAILED",
    "REASON_LEDGER_QUERY_FAILED",
    "REASON_RATE_NOT_FOUND",
    "AggregatedIncomeRow",
    "ConversionProvenance",
    "ConversionStatus",
    "IncomeTimelinePayload",
    "IncomeTimelineRow",
    "IncomeTimelineStatus",
    "IncomeTimelineSummary",
]
