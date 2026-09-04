"""Behavioral tests for the isolated ``portfolio.income_timeline`` component.

Covers the ``ai-adequacy-v1-remediate-portfolio`` contract: permission/broker
scoping and the accessible-broker intersection, ``(period_start,
snapshot_as_of]`` date bounds, income-type filtering (DIVIDEND/INTEREST only),
ownership-share application, native/target currency shape, deterministic
ordering, no future-dated rows, no raw DB identifiers, empty-vs-failed
distinction, surfaced conversion failure (per-row + summary status),
component-local monotonic detail policy (Compact aggregate / Standard bounded /
Full all), and multi-broker + duplicate-asset handling.

The ledger loader and ``convert_bulk`` are exercised through targeted seams: the
permission/scope/date-bound/share tests drive the *real* ``_load_income_records``
loader against a stubbed session (asserting the compiled SQL and the resulting
records), while the assembly tests monkeypatch ``_load_income_records`` to inject
a fixed ledger snapshot and stub ``convert_bulk`` - mirroring the existing
``test_ai_export_components_portfolio_broker_financial`` DB-less pattern.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import backend.app.services.ai_export.components.portfolio_income as income_module
from backend.app.db.models import TransactionType
from backend.app.schemas.common import Currency
from backend.app.services.ai_export.components.portfolio_income import (
    REASON_CONVERSION_FAILED,
    REASON_LEDGER_QUERY_FAILED,
    REASON_RATE_NOT_FOUND,
    ConversionStatus,
    IncomeTimelinePayload,
    IncomeTimelineRow,
    IncomeTimelineStatus,
    _build_portfolio_income_timeline,
    _IncomeRecord,
    _IncomeTimelineData,
    _load_income_records,
)
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.types import BuildScope, DetailLevel, Domain
from backend.app.services.ai_export.dependencies import BuildContext, ResourceLoadError, build_bucket_plan_for_scope

PERIOD_START = date(2024, 1, 1)
PERIOD_END = date(2024, 12, 31)
TARGET = "USD"


# =============================================================================
# Construction helpers
# =============================================================================


def _scope(**overrides) -> BuildScope:
    defaults = {
        "request_id": "req-income",
        "user_id": 7,
        "domain": Domain.PORTFOLIO,
        "detail_level": DetailLevel.FULL,
        "period_start": PERIOD_START,
        "period_end": PERIOD_END,
        "target_currency": TARGET,
        "broker_scope": (),
    }
    defaults.update(overrides)
    return BuildScope(**defaults)


def _make_async_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    return AsyncSession(engine)


def _make_context(scope: BuildScope, *, session: AsyncSession | None = None) -> BuildContext:
    registry = ComponentRegistry(income_module.PORTFOLIO_INCOME_TIMELINE_COMPONENTS)
    bucket_plan = build_bucket_plan_for_scope(scope)
    return BuildContext(registry, request_id=scope.request_id, scope=scope, bucket_plan=bucket_plan, session=session or _make_async_session())


def _record(day: date, *, asset_id, broker_id, income_type=TransactionType.DIVIDEND, amount="10", currency="EUR") -> _IncomeRecord:
    return _IncomeRecord(
        date=day,
        asset_id=asset_id,
        broker_id=broker_id,
        income_type=income_type,
        amount=Decimal(str(amount)),
        currency=currency,
    )


def _data(records, *, asset_names=None, asset_tickers=None, broker_names=None) -> _IncomeTimelineData:
    return _IncomeTimelineData(
        records=tuple(records),
        asset_names=asset_names or {},
        asset_tickers=asset_tickers or {},
        broker_names=broker_names or {},
    )


def _patch_ledger(monkeypatch, data: _IncomeTimelineData):
    async def _fake(context, scope):  # noqa: ARG001
        return data

    monkeypatch.setattr(income_module, "_load_income_records", _fake)


def _patch_ledger_raises(monkeypatch):
    async def _fake(context, scope):  # noqa: ARG001
        raise ResourceLoadError("portfolio.income_timeline_records", RuntimeError("db down"))

    monkeypatch.setattr(income_module, "_load_income_records", _fake)


def _make_convert(rate_map=None, *, fail_currencies=(), raises=False):
    rate_map = rate_map or {}

    async def _convert(session, conversions, raise_on_error=True):  # noqa: ARG001
        if raises:
            raise RuntimeError("fx backend exploded")
        results = []
        errors = []
        for amount_currency, to_currency, as_of in conversions:
            code = amount_currency.code
            if code == to_currency:
                results.append((Currency(code=to_currency, amount=amount_currency.amount), as_of, False))
                continue
            if code in fail_currencies or (code, to_currency) not in rate_map:
                results.append(None)
                errors.append(f"no rate {code}/{to_currency}")
                continue
            rate, rate_date, backfill = rate_map[(code, to_currency)]
            results.append((Currency(code=to_currency, amount=amount_currency.amount * rate), rate_date, backfill))
        return results, errors

    return _convert


# =============================================================================
# Permission / scope / date-bounds / share (real loader against a stub session)
# =============================================================================


class _StubResult:
    def __init__(self, *, rows=None, scalar_items=None):
        self._rows = rows or []
        self._scalar_items = scalar_items or []

    def all(self):
        return self._rows

    def scalars(self):
        return SimpleNamespace(all=lambda: self._scalar_items)


class _StubSession:
    """Records executed statements and returns queued results in order."""

    def __init__(self, queued):
        self._queued = list(queued)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return self._queued.pop(0)


async def _run_loader(monkeypatch, scope, *, accessible, shares, txns, assets=None, brokers=None):
    async def _fake_accessible(session, user_id):  # noqa: ARG001
        return list(accessible)

    async def _fake_assets(session, asset_ids):  # noqa: ARG001
        return assets or {}

    async def _fake_brokers(session, broker_ids):  # noqa: ARG001
        return brokers or {}

    monkeypatch.setattr(income_module, "resolve_accessible_broker_ids", _fake_accessible)
    monkeypatch.setattr(income_module, "load_asset_metadata", _fake_assets)
    monkeypatch.setattr(income_module, "load_broker_metadata", _fake_brokers)

    stub = _StubSession([_StubResult(rows=shares), _StubResult(scalar_items=txns)])
    context = _make_context(scope, session=_make_async_session())
    # Route the loader's own queries through the stub while keeping a real
    # AsyncSession for BuildContext's isinstance/db_resource plumbing.
    context._session.execute = stub.execute  # type: ignore[method-assign]
    data = await _load_income_records(context, scope)
    return data, stub


@pytest.mark.asyncio
async def test_scope_intersects_accessible_and_requested_brokers(monkeypatch):
    # Requested brokers include 99 which the user cannot access -> excluded.
    scope = _scope(broker_scope=(2, 99))
    data, stub = await _run_loader(
        monkeypatch,
        scope,
        accessible=[1, 2, 3],
        shares=[(2, Decimal("1"))],
        txns=[SimpleNamespace(date=date(2024, 6, 1), asset_id=5, broker_id=2, type=TransactionType.DIVIDEND, amount=Decimal("10"), currency="EUR")],
    )
    compiled = str(stub.statements[1].compile(compile_kwargs={"literal_binds": True}))
    assert " IN (2)" in compiled  # only accessible ∩ requested broker survives
    assert "99" not in compiled
    assert len(data.records) == 1
    assert data.records[0].broker_id == 2


@pytest.mark.asyncio
async def test_empty_effective_scope_returns_no_records(monkeypatch):
    scope = _scope(broker_scope=(99,))  # requested broker not accessible
    data, _stub = await _run_loader(monkeypatch, scope, accessible=[1, 2], shares=[], txns=[])
    assert data.records == ()


@pytest.mark.asyncio
async def test_query_uses_exclusive_start_inclusive_end_and_income_types(monkeypatch):
    scope = _scope()
    _data_out, stub = await _run_loader(monkeypatch, scope, accessible=[1], shares=[(1, Decimal("1"))], txns=[])
    compiled = str(stub.statements[1].compile(compile_kwargs={"literal_binds": True}))
    assert "> '2024-01-01'" in compiled  # exclusive start
    assert "<= '2024-12-31'" in compiled  # inclusive end (snapshot_as_of)
    assert "'DIVIDEND'" in compiled and "'INTEREST'" in compiled


@pytest.mark.asyncio
async def test_ownership_share_scales_native_amount(monkeypatch):
    scope = _scope()
    data, _stub = await _run_loader(
        monkeypatch,
        scope,
        accessible=[1, 2],
        shares=[(1, Decimal("0.5")), (2, Decimal("1"))],
        txns=[
            SimpleNamespace(date=date(2024, 3, 1), asset_id=5, broker_id=1, type=TransactionType.DIVIDEND, amount=Decimal("100"), currency="EUR"),
            SimpleNamespace(date=date(2024, 4, 1), asset_id=5, broker_id=2, type=TransactionType.INTEREST, amount=Decimal("40"), currency="EUR"),
        ],
    )
    by_broker = {r.broker_id: r.amount for r in data.records}
    assert by_broker[1] == Decimal("50.0")  # 100 * 0.5
    assert by_broker[2] == Decimal("40")  # 40 * 1


@pytest.mark.asyncio
async def test_records_fail_closed_when_income_currency_is_missing(monkeypatch):
    scope = _scope()
    with pytest.raises(ResourceLoadError, match="missing amount or currency"):
        await _run_loader(
            monkeypatch,
            scope,
            accessible=[1],
            shares=[(1, Decimal("1"))],
            txns=[
                SimpleNamespace(date=date(2024, 3, 1), asset_id=5, broker_id=1, type=TransactionType.DIVIDEND, amount=Decimal("100"), currency=None),
                SimpleNamespace(date=date(2024, 3, 2), asset_id=5, broker_id=1, type=TransactionType.DIVIDEND, amount=Decimal("20"), currency="EUR"),
            ],
        )


# =============================================================================
# Empty vs failed
# =============================================================================


@pytest.mark.asyncio
async def test_no_recorded_income_is_valid_empty_success(monkeypatch):
    _patch_ledger(monkeypatch, _data([]))
    payload = await _build_portfolio_income_timeline(_make_context(_scope()), {})
    assert payload.status is IncomeTimelineStatus.EMPTY
    assert payload.summary is not None
    assert payload.summary.transaction_count == 0
    assert payload.summary.conversion_status is ConversionStatus.COMPLETE
    assert payload.rows == () and payload.aggregated_rows == ()
    assert payload.reason_code is None


@pytest.mark.asyncio
async def test_ledger_query_failure_yields_failed_status(monkeypatch):
    _patch_ledger_raises(monkeypatch)
    payload = await _build_portfolio_income_timeline(_make_context(_scope()), {})
    assert payload.status is IncomeTimelineStatus.FAILED
    assert payload.reason_code == REASON_LEDGER_QUERY_FAILED
    assert payload.summary is None
    assert payload.message


@pytest.mark.asyncio
async def test_conversion_backend_error_yields_failed_status(monkeypatch):
    _patch_ledger(monkeypatch, _data([_record(date(2024, 6, 1), asset_id=5, broker_id=1)]))
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert(raises=True))
    payload = await _build_portfolio_income_timeline(_make_context(_scope()), {})
    assert payload.status is IncomeTimelineStatus.FAILED
    assert payload.reason_code == REASON_CONVERSION_FAILED


# =============================================================================
# Native / target currency + conversion provenance + surfaced conversion failure
# =============================================================================


@pytest.mark.asyncio
async def test_native_and_target_amounts_with_provenance(monkeypatch):
    _patch_ledger(
        monkeypatch,
        _data(
            [_record(date(2024, 6, 1), asset_id=5, broker_id=1, amount="10", currency="EUR")],
            asset_names={5: "Acme ETF"},
            asset_tickers={5: "ACME"},
            broker_names={1: "IBKR"},
        ),
    )
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert({("EUR", "USD"): (Decimal("1.1"), date(2024, 5, 30), True)}))
    payload = await _build_portfolio_income_timeline(_make_context(_scope()), {})
    row = payload.rows[0]
    assert row.native_amount == Currency(code="EUR", amount=Decimal("10"))
    assert row.target_amount == Currency(code="USD", amount=Decimal("11.0"))
    assert row.conversion is not None
    assert row.conversion.rate_date == date(2024, 5, 30)
    assert row.conversion.backfill_applied is True
    assert row.conversion.identity is False
    assert row.conversion_reason is None
    assert payload.summary.conversion_status is ConversionStatus.COMPLETE
    assert payload.summary.target_total == Currency(code="USD", amount=Decimal("11.0"))
    assert row.asset_name == "Acme ETF" and row.asset_ticker == "ACME" and row.broker_name == "IBKR"


@pytest.mark.asyncio
async def test_identity_conversion_marks_provenance_identity(monkeypatch):
    _patch_ledger(monkeypatch, _data([_record(date(2024, 6, 1), asset_id=5, broker_id=1, currency="USD", amount="12")]))
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert({}))
    payload = await _build_portfolio_income_timeline(_make_context(_scope()), {})
    row = payload.rows[0]
    assert row.conversion is not None and row.conversion.identity is True
    assert row.conversion.backfill_applied is False


@pytest.mark.asyncio
async def test_missing_rate_is_surfaced_not_zeroed(monkeypatch):
    _patch_ledger(
        monkeypatch,
        _data(
            [
                _record(date(2024, 6, 1), asset_id=5, broker_id=1, currency="USD", amount="10"),
                _record(date(2024, 6, 2), asset_id=6, broker_id=1, currency="GBP", amount="20"),
            ]
        ),
    )
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert(fail_currencies=("GBP",)))
    payload = await _build_portfolio_income_timeline(_make_context(_scope()), {})
    gbp_row = next(r for r in payload.rows if r.native_amount.code == "GBP")
    assert gbp_row.target_amount is None
    assert gbp_row.conversion is None
    assert gbp_row.conversion_reason == REASON_RATE_NOT_FOUND
    assert payload.summary.conversion_status is ConversionStatus.PARTIAL
    assert payload.summary.target_total is None  # never a misleading partial subtotal
    # Native totals remain deterministic and complete despite the missing rate.
    assert Currency(code="GBP", amount=Decimal("20")) in payload.summary.native_totals


@pytest.mark.asyncio
async def test_all_rates_missing_reports_unavailable_conversion(monkeypatch):
    _patch_ledger(monkeypatch, _data([_record(date(2024, 6, 1), asset_id=5, broker_id=1, currency="GBP", amount="20")]))
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert(fail_currencies=("GBP",)))
    payload = await _build_portfolio_income_timeline(_make_context(_scope()), {})
    assert payload.summary.conversion_status is ConversionStatus.UNAVAILABLE
    assert payload.summary.target_total is None


# =============================================================================
# No future rows, no raw DB identifiers, deterministic ordering
# =============================================================================


@pytest.mark.asyncio
async def test_no_row_after_period_end(monkeypatch):
    # A defensive out-of-window record must never surface a future-dated row.
    _patch_ledger(
        monkeypatch,
        _data(
            [
                _record(date(2024, 12, 31), asset_id=5, broker_id=1, currency="USD", amount="5"),
            ]
        ),
    )
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert({}))
    payload = await _build_portfolio_income_timeline(_make_context(_scope()), {})
    assert all(row.date <= PERIOD_END for row in payload.rows)


def test_row_never_exposes_transaction_db_identifiers():
    fields = set(IncomeTimelineRow.model_fields)
    for forbidden in ("id", "transaction_id", "related_transaction_id", "asset_event_id"):
        assert forbidden not in fields


@pytest.mark.asyncio
async def test_rows_are_deterministically_ordered(monkeypatch):
    records = [
        _record(date(2024, 6, 2), asset_id=6, broker_id=2, currency="USD", amount="3"),
        _record(date(2024, 6, 1), asset_id=5, broker_id=2, income_type=TransactionType.INTEREST, currency="USD", amount="1"),
        _record(date(2024, 6, 1), asset_id=5, broker_id=1, currency="USD", amount="2"),
    ]
    _patch_ledger(monkeypatch, _data(records))
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert({}))
    payload = await _build_portfolio_income_timeline(_make_context(_scope()), {})
    keys = [(r.date, r.income_type, r.broker_id, r.asset_id) for r in payload.rows]
    assert keys == sorted(keys)


# =============================================================================
# Detail policy: monotonic Compact / Standard / Full
# =============================================================================


def _many_records(n):
    return [_record(date(2024, 1, 1) + _delta(i), asset_id=1 + (i % 3), broker_id=1 + (i % 2), currency="USD", amount=str(i + 1)) for i in range(n)]


def _delta(days):
    return timedelta(days=days)


@pytest.mark.asyncio
async def test_compact_aggregates_by_month_asset_type(monkeypatch):
    records = [
        _record(date(2024, 1, 5), asset_id=5, broker_id=1, currency="USD", amount="10"),
        _record(date(2024, 1, 20), asset_id=5, broker_id=2, currency="USD", amount="15"),  # same month/asset/type, other broker
        _record(date(2024, 2, 5), asset_id=5, broker_id=1, income_type=TransactionType.INTEREST, currency="USD", amount="7"),
    ]
    _patch_ledger(monkeypatch, _data(records, asset_names={5: "Acme"}))
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert({}))
    payload = await _build_portfolio_income_timeline(_make_context(_scope(detail_level=DetailLevel.COMPACT)), {})
    assert payload.rows == ()
    assert len(payload.aggregated_rows) == 2  # (2024-01, asset5, DIVIDEND) merged across brokers + (2024-02, asset5, INTEREST)
    jan = next(a for a in payload.aggregated_rows if a.month == "2024-01")
    assert jan.transaction_count == 2
    assert jan.native_amounts == (Currency(code="USD", amount=Decimal("25")),)
    assert jan.conversion_complete is True
    # Summary is over the full set regardless of detail level.
    assert payload.summary.transaction_count == 3


@pytest.mark.asyncio
async def test_standard_bounds_rows_and_discloses_omissions(monkeypatch):
    records = _many_records(income_module._STANDARD_MAX_ROWS + 5)
    _patch_ledger(monkeypatch, _data(records))
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert({}))
    payload = await _build_portfolio_income_timeline(_make_context(_scope(detail_level=DetailLevel.STANDARD)), {})
    assert len(payload.rows) == income_module._STANDARD_MAX_ROWS
    assert payload.rows_truncated is True
    assert payload.rows_omitted_count == 5
    # Bounded to the most recent rows.
    assert payload.rows[-1].date == max(r.date for r in records)
    # But the summary still reflects every transaction.
    assert payload.summary.transaction_count == len(records)


@pytest.mark.asyncio
async def test_full_exposes_every_row(monkeypatch):
    records = _many_records(income_module._STANDARD_MAX_ROWS + 5)
    _patch_ledger(monkeypatch, _data(records))
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert({}))
    payload = await _build_portfolio_income_timeline(_make_context(_scope(detail_level=DetailLevel.FULL)), {})
    assert len(payload.rows) == len(records)
    assert payload.rows_truncated is False
    assert payload.rows_omitted_count == 0


@pytest.mark.asyncio
async def test_detail_monotonicity_full_superset_of_standard(monkeypatch):
    records = _many_records(income_module._STANDARD_MAX_ROWS + 5)
    _patch_ledger(monkeypatch, _data(records))
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert({}))

    full = await _build_portfolio_income_timeline(_make_context(_scope(detail_level=DetailLevel.FULL)), {})
    standard = await _build_portfolio_income_timeline(_make_context(_scope(detail_level=DetailLevel.STANDARD)), {})

    def _key(row):
        return (row.date, row.income_type, row.broker_id, row.asset_id, row.native_amount.amount)

    full_keys = {_key(r) for r in full.rows}
    standard_keys = {_key(r) for r in standard.rows}
    assert standard_keys.issubset(full_keys)
    assert full.summary.transaction_count == standard.summary.transaction_count


# =============================================================================
# Multi-broker + duplicate assets
# =============================================================================


@pytest.mark.asyncio
async def test_multi_broker_duplicate_assets_kept_distinct(monkeypatch):
    # Same asset (5) paying on two brokers on the same day must stay two rows.
    records = [
        _record(date(2024, 6, 1), asset_id=5, broker_id=1, currency="USD", amount="10"),
        _record(date(2024, 6, 1), asset_id=5, broker_id=2, currency="USD", amount="20"),
    ]
    _patch_ledger(monkeypatch, _data(records, asset_names={5: "Acme"}, broker_names={1: "IBKR", 2: "Degiro"}))
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert({}))
    payload = await _build_portfolio_income_timeline(_make_context(_scope()), {})
    assert len(payload.rows) == 2
    assert {r.broker_id for r in payload.rows} == {1, 2}
    assert payload.summary.distinct_asset_count == 1
    assert payload.summary.distinct_broker_count == 2
    assert payload.summary.dividend_count == 2


# =============================================================================
# Payload validation guards
# =============================================================================


def test_row_rejects_target_without_provenance():
    with pytest.raises(ValidationError):
        IncomeTimelineRow(
            date=date(2024, 6, 1),
            income_type="DIVIDEND",
            broker_id=1,
            broker_name="IBKR",
            native_amount=Currency(code="USD", amount=Decimal("1")),
            target_amount=Currency(code="USD", amount=Decimal("1")),
        )


def test_row_rejects_unconverted_without_reason():
    with pytest.raises(ValidationError):
        IncomeTimelineRow(
            date=date(2024, 6, 1),
            income_type="DIVIDEND",
            broker_id=1,
            broker_name="IBKR",
            native_amount=Currency(code="USD", amount=Decimal("1")),
        )


def test_payload_forbids_extra_fields():
    with pytest.raises(ValidationError):
        IncomeTimelinePayload(status=IncomeTimelineStatus.FAILED, detail_level="full", reason_code="x", message="y", bogus=1)
