"""Behavioral tests for the isolated ``portfolio.income_timeline`` component.

Covers the ``ai-adequacy-v1-remediate-portfolio`` contract: permission/broker
scoping and the accessible-broker intersection, ``(period_start,
snapshot_as_of]`` date bounds, income-type filtering (DIVIDEND/INTEREST/REWARD),
ownership-share application, native/target currency shape, deterministic
ordering, no future-dated rows, no raw DB identifiers, empty-vs-failed
distinction, surfaced conversion failure (per-row + summary status),
component-local monotonic detail policy (Compact aggregate / Standard bounded /
Full all), and multi-broker + duplicate-asset handling.

MF-F2 (D-MF3, backlog B9/O3): income keeps its sign and the report's share rule
(``native_cash.effective_share``: an owner's share, the whole broker for an
editor or a viewer), so a negative DIVIDEND/INTEREST correction lowers every
total exactly like the report's ``period_income``; the component is version 2.
Those tests drive the real loader through the stub session, and through the
real builder when a total is under test.

79 STK-5 (project 79, issue #90): the income types and values come from the one
income rule of ``financial_math.income`` (``INCOME_TYPES``, ``income_value``), so a
``REWARD`` (income in kind, e.g. staking) joins DIVIDEND/INTEREST at its value on
receipt (``cost_basis_override × quantity`` in ``cost_basis_currency``) times the
broker share, and its row adds ``units`` (``quantity × share``; absent for cash
income). A recorded income row whose value is unknown fails the section with
``income_value_missing``, never a zero; the component is version 3. The timeline
total equals the report's ``period_income`` computed by the engine's native cash
over the same ledger (the formula ``portfolio/summary.py`` sums).

The ledger loader and ``convert_bulk`` are exercised through targeted seams: the
permission/scope/date-bound/share tests drive the *real* ``_load_income_records``
loader against a stubbed session (asserting the compiled SQL and the resulting
records), while the assembly tests monkeypatch ``_load_income_records`` to inject
a fixed ledger snapshot and stub ``convert_bulk`` - mirroring the existing
``test_ai_export_components_portfolio_broker_financial`` DB-less pattern.
"""

from __future__ import annotations

from collections import namedtuple
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import backend.app.services.ai_export.components.portfolio_income as income_module
from backend.app.db.models import Transaction, TransactionType, UserRole
from backend.app.schemas.common import Currency
from backend.app.services.ai_export.components.catalog import build_component_registry
from backend.app.services.ai_export.components.portfolio_income import (
    REASON_CONVERSION_FAILED,
    REASON_INCOME_VALUE_MISSING,
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
from backend.app.services.financial_math.income import INCOME_TYPES
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.test_scripts.test_services._engine_native_cash import engine_native_cash

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


def _record(day: date, *, asset_id, broker_id, income_type=TransactionType.DIVIDEND, amount="10", currency="EUR", units=None) -> _IncomeRecord:
    return _IncomeRecord(
        date=day,
        asset_id=asset_id,
        broker_id=broker_id,
        income_type=income_type,
        amount=Decimal(str(amount)),
        currency=currency,
        units=None if units is None else Decimal(str(units)),
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
    """Records executed statements and returns queued results in order.

    A queued item may be a factory taking the executed statement, for a result
    whose shape depends on what the loader selected (see `_access_result`).
    """

    def __init__(self, queued):
        self._queued = list(queued)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        queued = self._queued.pop(0)
        return queued(statement) if callable(queued) else queued


def _access_result(accesses):
    """The broker-access query's result, shaped by the columns the loader actually selected.

    Rows are built from ``statement.selected_columns`` so the stub answers a
    ``(broker_id, share_percentage)`` select and a ``(broker_id, role,
    share_percentage)`` one alike, in any column order: these tests pin the
    recorded amounts, not the query's shape.
    """

    def _answer(statement):
        names = [getattr(column, "key", None) or column.name for column in statement.selected_columns]
        row_type = namedtuple("AccessRow", names, rename=True)
        rows = [row_type(*(access.get(name) for name in names)) for access in accesses]
        return _StubResult(rows=rows, scalar_items=[SimpleNamespace(**access) for access in accesses])

    return _answer


def _loader_context(monkeypatch, scope, *, accessible, shares, txns, roles=None, assets=None, brokers=None):
    """A context whose session answers the real loader's two queries from plain data.

    ``shares`` is ``[(broker_id, stored share_percentage)]``; every access is an
    ``OWNER`` unless ``roles`` (``{broker_id: UserRole}``) says otherwise.
    """

    async def _fake_accessible(session, user_id):  # noqa: ARG001
        return list(accessible)

    async def _fake_assets(session, asset_ids):  # noqa: ARG001
        return assets or {}

    async def _fake_brokers(session, broker_ids):  # noqa: ARG001
        return brokers or {}

    monkeypatch.setattr(income_module, "resolve_accessible_broker_ids", _fake_accessible)
    monkeypatch.setattr(income_module, "load_asset_metadata", _fake_assets)
    monkeypatch.setattr(income_module, "load_broker_metadata", _fake_brokers)

    roles = roles or {}
    accesses = [{"user_id": scope.user_id, "broker_id": broker_id, "role": roles.get(broker_id, UserRole.OWNER), "share_percentage": share} for broker_id, share in shares]
    stub = _StubSession([_access_result(accesses), _StubResult(scalar_items=txns)])
    context = _make_context(scope, session=_make_async_session())
    # Route the loader's own queries through the stub while keeping a real
    # AsyncSession for BuildContext's isinstance/db_resource plumbing.
    context._session.execute = stub.execute  # type: ignore[method-assign]
    return context, stub


async def _run_loader(monkeypatch, scope, *, accessible, shares, txns, roles=None, assets=None, brokers=None):
    context, stub = _loader_context(monkeypatch, scope, accessible=accessible, shares=shares, txns=txns, roles=roles, assets=assets, brokers=brokers)
    data = await _load_income_records(context, scope)
    return data, stub


def _tx(day, *, amount, broker_id=1, asset_id=5, income_type=TransactionType.DIVIDEND, currency="EUR"):
    return SimpleNamespace(date=day, asset_id=asset_id, broker_id=broker_id, type=income_type, amount=Decimal(str(amount)), currency=currency)


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
    assert "'REWARD'" in compiled  # 79 STK-5: income in kind is income too


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
    """A cash income row without a currency has no known value: the loader fails, never a zero.

    Before 79 STK-5: a plain ValueError ("missing amount or currency"), reported as
    ``income_ledger_query_failed``; now the cause says the value is missing."""
    scope = _scope()
    with pytest.raises(ResourceLoadError) as excinfo:
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
    assert isinstance(excinfo.value.cause, income_module._IncomeValueMissingError)


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


# =============================================================================
# MF-F2 — income keeps its sign and the report's share rule (D-MF3, B9/O3)
# =============================================================================

# A payment and a later legacy negative correction of the same kind, same broker,
# same month. EUR natives, converted to USD at 1.5, so the native and the target
# side are pinned separately.
_CORRECTIONS = [
    pytest.param(TransactionType.DIVIDEND, 5, "10", "-4", id="dividend"),
    pytest.param(TransactionType.INTEREST, None, "8", "-3", id="interest"),
]
# Net of each pair, as the report's `period_income` counts it: (native EUR, target USD).
_NET = {
    TransactionType.DIVIDEND: (Decimal("6"), Decimal("9")),
    TransactionType.INTEREST: (Decimal("5"), Decimal("7.5")),
}
_PAID_ON = date(2024, 3, 1)
_CORRECTED_ON = date(2024, 3, 15)
_EUR_USD = {("EUR", "USD"): (Decimal("1.5"), date(2024, 2, 29), False)}


def _correction_ledger(income_type, asset_id, paid, correction):
    return [
        _tx(_PAID_ON, income_type=income_type, asset_id=asset_id, amount=paid),
        _tx(_CORRECTED_ON, income_type=income_type, asset_id=asset_id, amount=correction),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(("income_type", "asset_id", "paid", "correction"), _CORRECTIONS)
async def test_negative_income_correction_keeps_its_sign(monkeypatch, income_type, asset_id, paid, correction):
    """Before MF-F2: ``abs(amount) * share`` — the correction was recorded as +4 (dividend) / +3 (interest)."""
    data, _stub = await _run_loader(monkeypatch, _scope(), accessible=[1], shares=[(1, Decimal("1"))], txns=_correction_ledger(income_type, asset_id, paid, correction))

    assert {record.date: record.amount for record in data.records} == {_PAID_ON: Decimal(paid), _CORRECTED_ON: Decimal(correction)}


@pytest.mark.asyncio
@pytest.mark.parametrize(("income_type", "asset_id", "paid", "correction"), _CORRECTIONS)
async def test_negative_income_correction_is_a_negative_dated_row(monkeypatch, income_type, asset_id, paid, correction):
    """Before MF-F2: the correction row read +4 EUR / +6 USD (dividend), +3 EUR / +4.5 USD (interest)."""
    context, _stub = _loader_context(monkeypatch, _scope(detail_level=DetailLevel.FULL), accessible=[1], shares=[(1, Decimal("1"))], txns=_correction_ledger(income_type, asset_id, paid, correction))
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert(_EUR_USD))

    payload = await _build_portfolio_income_timeline(context, {})

    rows = {row.date: (row.income_type, row.native_amount, row.target_amount) for row in payload.rows}
    assert rows == {
        _PAID_ON: (income_type.value, Currency(code="EUR", amount=Decimal(paid)), Currency(code="USD", amount=Decimal(paid) * Decimal("1.5"))),
        _CORRECTED_ON: (income_type.value, Currency(code="EUR", amount=Decimal(correction)), Currency(code="USD", amount=Decimal(correction) * Decimal("1.5"))),
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(("income_type", "asset_id", "paid", "correction"), _CORRECTIONS)
async def test_negative_income_correction_nets_every_total(monkeypatch, income_type, asset_id, paid, correction):
    """The summary (per period) and the COMPACT ``(month, asset, type)`` bucket (per asset) net the correction.

    Before MF-F2: the correction was added — 10 + 4 = 14 EUR / 21 USD (dividend), 8 + 3 = 11 EUR /
    16.5 USD (interest) — where the report's ``period_income`` nets it to 6 / 5.
    """
    net_native, net_target = _NET[income_type]
    context, _stub = _loader_context(monkeypatch, _scope(detail_level=DetailLevel.COMPACT), accessible=[1], shares=[(1, Decimal("1"))], txns=_correction_ledger(income_type, asset_id, paid, correction))
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert(_EUR_USD))

    payload = await _build_portfolio_income_timeline(context, {})

    assert payload.status is IncomeTimelineStatus.OK
    assert payload.summary.transaction_count == 2
    assert payload.summary.native_totals == (Currency(code="EUR", amount=net_native),)
    assert payload.summary.conversion_status is ConversionStatus.COMPLETE
    assert payload.summary.target_total == Currency(code="USD", amount=net_target)
    bucket = next(row for row in payload.aggregated_rows if (row.month, row.asset_id, row.income_type) == ("2024-03", asset_id, income_type.value))
    assert bucket.transaction_count == 2
    assert bucket.native_amounts == (Currency(code="EUR", amount=net_native),)
    assert bucket.target_amount == Currency(code="USD", amount=net_target)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "stored_share", "factor"),
    [
        pytest.param(UserRole.VIEWER, Decimal("0"), Decimal("1"), id="viewer-stored-zero-counts-whole-broker"),
        pytest.param(UserRole.EDITOR, Decimal("0.5"), Decimal("1"), id="editor-stored-half-counts-whole-broker"),
        pytest.param(UserRole.OWNER, Decimal("0.5"), Decimal("0.5"), id="control-owner-half"),
        pytest.param(UserRole.OWNER, None, Decimal("1"), id="control-owner-no-share-counts-whole-broker"),
        pytest.param(UserRole.OWNER, Decimal("0"), Decimal("0"), id="control-owner-zero"),
    ],
)
async def test_share_follows_the_report_rule(monkeypatch, role, stored_share, factor):
    """``native_cash.effective_share``: an owner counts its own share (the whole broker when none is
    recorded), an editor or a viewer the whole broker.

    Before MF-F2: the raw stored share for every role — the viewer counted × 0, the editor × 0.5.
    The three owner cases are controls, green before and after. Amounts are positive so the
    controls do not depend on the sign rule.
    """
    data, _stub = await _run_loader(
        monkeypatch,
        _scope(),
        accessible=[1],
        shares=[(1, stored_share)],
        roles={1: role},
        txns=[
            _tx(date(2024, 3, 1), amount="100"),
            _tx(date(2024, 4, 1), income_type=TransactionType.INTEREST, asset_id=None, amount="40"),
        ],
    )

    assert {record.income_type: record.amount for record in data.records} == {
        TransactionType.DIVIDEND: Decimal("100") * factor,
        TransactionType.INTEREST: Decimal("40") * factor,
    }


@pytest.mark.asyncio
async def test_summary_total_follows_the_report_period_income_rule(monkeypatch):
    """Sign and share together, as the report's ``period_income`` counts them: an owner at 0.5 on
    broker 1 (+100 → 50), a viewer with a stored 0 on broker 2 (+40 − 10 → 30): 80.

    Before MF-F2: 50 — the viewer's broker counted × 0, its payment and its correction alike.
    """
    context, _stub = _loader_context(
        monkeypatch,
        _scope(detail_level=DetailLevel.FULL),
        accessible=[1, 2],
        shares=[(1, Decimal("0.5")), (2, Decimal("0"))],
        roles={1: UserRole.OWNER, 2: UserRole.VIEWER},
        txns=[
            _tx(date(2024, 2, 1), broker_id=1, asset_id=5, amount="100", currency="USD"),
            _tx(date(2024, 2, 10), broker_id=2, asset_id=6, amount="40", currency="USD"),
            _tx(date(2024, 2, 20), broker_id=2, asset_id=6, amount="-10", currency="USD"),
        ],
    )
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert({}))

    payload = await _build_portfolio_income_timeline(context, {})

    assert {(row.broker_id, row.date): row.native_amount.amount for row in payload.rows} == {
        (1, date(2024, 2, 1)): Decimal("50"),
        (2, date(2024, 2, 10)): Decimal("40"),
        (2, date(2024, 2, 20)): Decimal("-10"),
    }
    assert payload.summary.native_totals == (Currency(code="USD", amount=Decimal("80")),)
    assert payload.summary.target_total == Currency(code="USD", amount=Decimal("80"))


def test_income_timeline_is_component_version_3_in_the_production_catalog():
    """Before MF-F2: version 1; MF-F2: version 2 (sign and share); 79 STK-5: version 3 (REWARD rows,
    ``units``, ``reward_count``, ``income_value_missing``). schema_version stays 1, which is what keeps
    the Snapshot Data renderer on its compact path for version 3 (``COMPACT_COMPONENT_VERSIONS``)."""
    spec = build_component_registry().get("portfolio.income_timeline")

    assert (spec.version, spec.schema_version, spec.output_model) == (3, 1, IncomeTimelinePayload)


@pytest.mark.asyncio
async def test_income_timeline_envelope_is_component_version_3_schema_version_1(monkeypatch):
    """Before MF-F2: component_version 1; before 79 STK-5: 2."""
    _patch_ledger(monkeypatch, _data([]))
    context = _make_context(_scope())

    envelope = await context.resolve("portfolio.income_timeline", required=True)

    assert (envelope.component_id, envelope.component_version, envelope.schema_version) == ("portfolio.income_timeline", 3, 1)


# =============================================================================
# 79 STK-5 — a REWARD is income at its value on receipt, with its units
# =============================================================================

_REWARD_DAY = date(2024, 5, 10)
_REWARD_QUANTITY = Decimal("4")
_REWARD_UNIT_VALUE = Decimal("2.5")
_REWARD_VALUE = _REWARD_QUANTITY * _REWARD_UNIT_VALUE  # 10 EUR, its value on receipt


def _reward_tx(day, *, quantity=_REWARD_QUANTITY, unit_value=_REWARD_UNIT_VALUE, broker_id=1, asset_id=5, value_currency="EUR"):
    """A REWARD as the ledger stores it: units in, no cash (amount 0, no currency), its value per unit in
    ``cost_basis_override`` and that value's currency in ``cost_basis_currency``."""
    return SimpleNamespace(
        date=day,
        asset_id=asset_id,
        broker_id=broker_id,
        type=TransactionType.REWARD,
        quantity=None if quantity is None else Decimal(str(quantity)),
        amount=Decimal("0"),
        currency=None,
        cost_basis_override=None if unit_value is None else Decimal(str(unit_value)),
        cost_basis_currency=value_currency,
    )


def _row_of(payload, income_type: TransactionType):
    """The one dated row of ``income_type`` in a payload the test filled with one row per type."""
    rows = [row for row in payload.rows if row.income_type == income_type.value]
    assert len(rows) == 1, f"one {income_type.value} row expected, got {len(rows)}"
    return rows[0]


@pytest.mark.asyncio
async def test_reward_row_is_its_value_on_receipt_with_its_units(monkeypatch):
    """A REWARD row reads ``cost_basis_override × quantity`` in ``cost_basis_currency`` (4 × 2.5 = 10 EUR,
    15 USD at 1.5) and ``units`` 4; a DIVIDEND and an INTEREST row carry no units (None)."""
    context, _stub = _loader_context(
        monkeypatch,
        _scope(detail_level=DetailLevel.FULL),
        accessible=[1],
        shares=[(1, Decimal("1"))],
        txns=[
            _tx(date(2024, 5, 2), amount="6"),
            _reward_tx(_REWARD_DAY),
            _tx(date(2024, 5, 20), income_type=TransactionType.INTEREST, asset_id=None, amount="3"),
        ],
    )
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert(_EUR_USD))

    payload = await _build_portfolio_income_timeline(context, {})

    assert payload.status is IncomeTimelineStatus.OK
    reward = _row_of(payload, TransactionType.REWARD)
    assert (reward.date, reward.asset_id, reward.native_amount, reward.target_amount, reward.units) == (
        _REWARD_DAY,
        5,
        Currency(code="EUR", amount=_REWARD_VALUE),
        Currency(code="USD", amount=_REWARD_VALUE * Decimal("1.5")),
        _REWARD_QUANTITY,
    )
    assert _row_of(payload, TransactionType.DIVIDEND).units is None
    assert _row_of(payload, TransactionType.INTEREST).units is None


@pytest.mark.asyncio
async def test_reward_units_and_value_scale_by_the_same_owner_share(monkeypatch):
    """An owner at 0.4: the REWARD's units (4 → 1.6) and its value (10 → 4 EUR) are scaled by the same share,
    so the value per unit received stays the value on receipt (2.5)."""
    share = Decimal("0.4")
    data, _stub = await _run_loader(monkeypatch, _scope(), accessible=[1], shares=[(1, share)], txns=[_reward_tx(_REWARD_DAY)])

    (record,) = data.records
    assert (record.income_type, record.amount, record.currency, record.units) == (TransactionType.REWARD, _REWARD_VALUE * share, "EUR", _REWARD_QUANTITY * share)
    assert record.units / _REWARD_QUANTITY == record.amount / _REWARD_VALUE == share
    assert record.amount / record.units == _REWARD_UNIT_VALUE


@pytest.mark.asyncio
async def test_summary_counts_rewards_beside_dividends_and_interest(monkeypatch):
    context, _stub = _loader_context(
        monkeypatch,
        _scope(detail_level=DetailLevel.FULL),
        accessible=[1],
        shares=[(1, Decimal("1"))],
        txns=[
            _tx(date(2024, 5, 2), amount="6"),
            _reward_tx(_REWARD_DAY),
            _reward_tx(date(2024, 6, 10), quantity="1", unit_value="3"),
            _tx(date(2024, 5, 20), income_type=TransactionType.INTEREST, asset_id=None, amount="3"),
        ],
    )
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert(_EUR_USD))

    payload = await _build_portfolio_income_timeline(context, {})

    summary = payload.summary
    assert (summary.transaction_count, summary.dividend_count, summary.interest_count, summary.reward_count) == (4, 1, 1, 2)


@pytest.mark.asyncio
async def test_summary_native_totals_include_the_reward_value(monkeypatch):
    """A dividend of 6 EUR and a REWARD worth 10 EUR: the native total is 16 EUR, the target total 24 USD."""
    context, _stub = _loader_context(
        monkeypatch,
        _scope(detail_level=DetailLevel.FULL),
        accessible=[1],
        shares=[(1, Decimal("1"))],
        txns=[_tx(date(2024, 5, 2), amount="6"), _reward_tx(_REWARD_DAY)],
    )
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert(_EUR_USD))

    payload = await _build_portfolio_income_timeline(context, {})

    assert payload.summary.native_totals == (Currency(code="EUR", amount=Decimal("6") + _REWARD_VALUE),)
    assert payload.summary.conversion_status is ConversionStatus.COMPLETE
    assert payload.summary.target_total == Currency(code="USD", amount=(Decimal("6") + _REWARD_VALUE) * Decimal("1.5"))


@pytest.mark.asyncio
async def test_compact_reward_bucket_sums_units_and_a_cash_bucket_has_none(monkeypatch):
    """COMPACT, one asset, one month: two REWARDs (4 and 6 units) and a DIVIDEND. The REWARD bucket sums the
    units (10) and the values (10 + 15 EUR); the DIVIDEND bucket of the same month and asset has no units."""
    context, _stub = _loader_context(
        monkeypatch,
        _scope(detail_level=DetailLevel.COMPACT),
        accessible=[1],
        shares=[(1, Decimal("1"))],
        txns=[
            _reward_tx(date(2024, 5, 10)),
            _reward_tx(date(2024, 5, 24), quantity="6"),
            _tx(date(2024, 5, 15), amount="6"),
        ],
    )
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert(_EUR_USD))

    payload = await _build_portfolio_income_timeline(context, {})

    buckets = {(row.month, row.asset_id, row.income_type): row for row in payload.aggregated_rows}
    reward = buckets[("2024-05", 5, "REWARD")]
    assert (reward.transaction_count, reward.units, reward.native_amounts) == (2, Decimal("10"), (Currency(code="EUR", amount=Decimal("25")),))
    assert reward.target_amount == Currency(code="USD", amount=Decimal("37.5"))
    dividend = buckets[("2024-05", 5, "DIVIDEND")]
    assert (dividend.transaction_count, dividend.units) == (1, None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reward",
    [
        pytest.param(_reward_tx(_REWARD_DAY, unit_value=None), id="no-value-on-receipt"),
        pytest.param(_reward_tx(_REWARD_DAY, value_currency=None), id="no-value-currency"),
    ],
)
async def test_reward_without_a_value_fails_the_section_never_a_zero(monkeypatch, reward):
    """A REWARD whose value on receipt is unknown fails the whole timeline with ``income_value_missing``:
    no row, no summary, no total that silently counts it as zero. The dividend beside it does not rescue it."""
    context, _stub = _loader_context(
        monkeypatch,
        _scope(detail_level=DetailLevel.FULL),
        accessible=[1],
        shares=[(1, Decimal("1"))],
        txns=[_tx(date(2024, 5, 2), amount="6"), reward],
    )
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert(_EUR_USD))

    payload = await _build_portfolio_income_timeline(context, {})

    assert payload.status is IncomeTimelineStatus.FAILED
    assert payload.reason_code == REASON_INCOME_VALUE_MISSING
    assert payload.reason_code != REASON_LEDGER_QUERY_FAILED
    assert payload.message
    assert payload.summary is None
    assert payload.rows == () and payload.aggregated_rows == ()


@pytest.mark.asyncio
async def test_reward_of_explicit_zero_value_is_a_known_zero(monkeypatch):
    """Control: a value of 0 is a known value, not a missing one — the row is there, worth 0, with its units."""
    context, _stub = _loader_context(
        monkeypatch,
        _scope(detail_level=DetailLevel.FULL),
        accessible=[1],
        shares=[(1, Decimal("1"))],
        txns=[_reward_tx(_REWARD_DAY, unit_value="0")],
    )
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert(_EUR_USD))

    payload = await _build_portfolio_income_timeline(context, {})

    assert payload.status is IncomeTimelineStatus.OK
    reward = _row_of(payload, TransactionType.REWARD)
    assert (reward.native_amount.amount, reward.units) == (Decimal("0"), _REWARD_QUANTITY)
    assert payload.summary.reward_count == 1


@pytest.mark.asyncio
async def test_reward_units_serialize_and_cash_rows_carry_null_units(monkeypatch):
    """What the Snapshot Data renderer reads: the envelope payload holds ``units`` on every row, a value on the
    REWARD row and null on the cash one (the renderer drops a column null in every row: null-means-none)."""
    context, _stub = _loader_context(
        monkeypatch,
        _scope(detail_level=DetailLevel.FULL),
        accessible=[1],
        shares=[(1, Decimal("1"))],
        txns=[_tx(date(2024, 5, 2), amount="6"), _reward_tx(_REWARD_DAY)],
    )
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert(_EUR_USD))

    envelope = await context.resolve("portfolio.income_timeline", required=True)

    units = {row["income_type"]: row["units"] for row in envelope.payload["rows"]}
    assert units["DIVIDEND"] is None
    assert units["REWARD"] is not None and Decimal(str(units["REWARD"])) == _REWARD_QUANTITY
    assert envelope.payload["summary"]["reward_count"] == 1


# -----------------------------------------------------------------------------
# The release condition: the timeline total equals the report's period_income
# -----------------------------------------------------------------------------

_ID_BROKER = 1
_ID_ASSET = 5
_ID_START = date(2024, 3, 1)  # exclusive, on both sides
_ID_END = date(2024, 3, 31)  # inclusive, on both sides


def _ledger_tx(tx_id, tx_type, day, *, quantity="0", amount="0", currency=None, cbo=None, cbo_ccy=None, asset_id=_ID_ASSET) -> Transaction:
    """A ledger row as the engine reads it (``test_reward_equivalence._tx``'s shape)."""
    tx = Transaction()
    tx.id = tx_id
    tx.broker_id = _ID_BROKER
    tx.asset_id = asset_id
    tx.type = tx_type
    tx.date = day
    tx.quantity = Decimal(quantity)
    tx.amount = Decimal(amount)
    tx.currency = currency
    tx.cost_basis_override = None if cbo is None else Decimal(cbo)
    tx.cost_basis_currency = cbo_ccy
    tx.related_transaction_id = None
    tx.updated_at = day
    return tx


def _identity_ledger(ccy: str) -> list[Transaction]:
    """Deposit and buy before the window; inside it a dividend, its negative correction, a REWARD and interest on
    cash; an income row on the exclusive start and one after the end, which neither side counts."""
    return [
        _ledger_tx(1, TransactionType.DEPOSIT, date(2024, 2, 1), amount="1000", currency=ccy, asset_id=None),
        _ledger_tx(2, TransactionType.BUY, date(2024, 2, 2), quantity="100", amount="-300", currency=ccy),
        _ledger_tx(3, TransactionType.DIVIDEND, _ID_START, amount="50", currency=ccy),  # on the exclusive start: out
        _ledger_tx(4, TransactionType.DIVIDEND, date(2024, 3, 5), amount="12", currency=ccy),
        _ledger_tx(5, TransactionType.DIVIDEND, date(2024, 3, 9), amount="-2", currency=ccy),
        _ledger_tx(6, TransactionType.REWARD, date(2024, 3, 12), quantity="4", cbo="2.5", cbo_ccy=ccy),
        _ledger_tx(7, TransactionType.INTEREST, date(2024, 3, 20), amount="3", currency=ccy, asset_id=None),
        _ledger_tx(8, TransactionType.REWARD, date(2024, 4, 2), quantity="1", cbo="9", cbo_ccy=ccy),  # after the end: out
    ]


def _engine_period_income(ledger: list[Transaction], share: Decimal, fx_rate_map: dict) -> Decimal:
    """The report's ``period_income``: the engine's native cash flows over ``(start, end]``, signed, summed over
    ``INCOME_TYPES`` — the formula of ``PortfolioService`` (``portfolio/summary.py``, ``_income_accum``)."""
    classified = ScopeAwareTransactionClassifier(scope_broker_ids={_ID_BROKER}, all_transactions=ledger, broker_shares={_ID_BROKER: share}).classify().classified
    native_cash = engine_native_cash(classified, target_currency="EUR", fx_rate_map=fx_rate_map, date_to=_ID_END)
    signed = native_cash.flows(_ID_START, _ID_END).signed_by_type
    return sum((signed.get(income_type, Decimal("0")) for income_type in sorted(INCOME_TYPES)), Decimal("0"))


def _usd_eur_every_day(rate: Decimal) -> dict:
    day, rates = date(2024, 1, 1), {}
    while day <= _ID_END:
        rates[("USD", "EUR", day)] = rate
        day += timedelta(days=1)
    return rates


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("ccy", "fx_rate_map", "convert_rates"),
    [
        pytest.param("EUR", {}, {}, id="eur"),
        # One constant rate: `_make_convert` holds one rate per pair, the engine one per day.
        pytest.param("USD", _usd_eur_every_day(Decimal("0.9")), {("USD", "EUR"): (Decimal("0.9"), date(2024, 3, 1), False)}, id="usd-at-0.9"),
    ],
)
async def test_timeline_total_equals_the_report_period_income_with_a_reward(monkeypatch, ccy, fx_rate_map, convert_rates):
    """79 STK-5, the release condition: on the same ledger, at an owner's share of 0.4, the timeline's
    ``target_total`` equals the ``period_income`` the engine's native cash gives the report — the REWARD
    counted at its value on receipt on both sides, the negative correction netted, the bounds the same.

    Expected, native: (12 − 2 + 4 × 2.5 + 3) × 0.4 = 9.2. Pure: this pins the report's formula over the
    engine's native cash, not ``PortfolioService.get_report`` end to end (that one needs the database)."""
    share = Decimal("0.4")
    ledger = _identity_ledger(ccy)
    period_income = _engine_period_income(ledger, share, fx_rate_map)
    # What the loader's SQL selects: the income types, dated in (period_start, snapshot_as_of].
    selected = [tx for tx in ledger if tx.type.value in INCOME_TYPES and _ID_START < tx.date <= _ID_END]
    context, _stub = _loader_context(
        monkeypatch,
        _scope(detail_level=DetailLevel.FULL, period_start=_ID_START, period_end=_ID_END, target_currency="EUR"),
        accessible=[_ID_BROKER],
        shares=[(_ID_BROKER, share)],
        txns=selected,
    )
    monkeypatch.setattr(income_module, "convert_bulk", _make_convert(convert_rates))

    payload = await _build_portfolio_income_timeline(context, {})

    native_expected = (Decimal("12") - Decimal("2") + Decimal("4") * Decimal("2.5") + Decimal("3")) * share
    rate = convert_rates.get((ccy, "EUR"), (Decimal("1"),))[0]
    assert payload.status is IncomeTimelineStatus.OK
    assert payload.summary.reward_count == 1
    assert payload.summary.native_totals == (Currency(code=ccy, amount=native_expected),)
    # Control: the engine side counts the REWARD too (without it, 10 × 0.4 × rate less) and nets the correction.
    assert period_income == native_expected * rate
    # Subject: one figure.
    assert payload.summary.target_total == Currency(code="EUR", amount=period_income)
