"""Contract tests for transaction-ledger Yield on Cost."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal
from uuid import uuid4

import pytest
import pytest_asyncio
from pydantic import ValidationError

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.services.financial_math.yield_on_cost as yoc_module
from backend.app.db.models import (
    Asset,
    AssetEvent,
    AssetEventType,
    AssetProviderAssignment,
    AssetType,
    Broker,
    BrokerUserAccess,
    FxRate,
    ProviderInputType,
    Transaction,
    TransactionType,
    User,
    UserRole,
)
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import (
    PortfolioHolding,
    YieldOnCostProvenance,
    YieldOnCostResult,
    YieldOnCostStatus,
    YieldOnCostUnavailableReason,
)
from backend.app.services.financial_math.yield_on_cost import (
    YieldOnCostPositionInput,
    calculate_yield_on_cost_for_positions,
    compute_yield_on_cost_dependency_identity,
)
from backend.app.services.portfolio_service import PortfolioService

AS_OF = date(2025, 12, 31)
WINDOW_START = AS_OF - timedelta(days=364)


@dataclass(frozen=True)
class Ledger:
    user_id: int
    broker_id: int
    asset_id: int


@dataclass(frozen=True)
class ReplayTopology:
    ledger: Ledger
    connected_broker_id: int
    isolated_broker_id: int


@pytest.fixture(scope="module")
def engine():
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    async with AsyncSession(engine, expire_on_commit=False) as db:
        yield db
        await db.rollback()


async def _make_ledger(
    session: AsyncSession,
    *,
    asset_type: AssetType = AssetType.STOCK,
    allow_asset_shorting: bool = False,
) -> Ledger:
    marker = uuid4().hex
    user = User(
        username=f"yoc_{marker}",
        email=f"yoc_{marker}@test.invalid",
        hashed_password="not-used",
        is_active=True,
    )
    broker = Broker(
        name=f"YOC broker {marker}",
        allow_asset_shorting=allow_asset_shorting,
    )
    asset = Asset(
        display_name=f"YOC asset {marker}",
        identifier_ticker=f"YOC{marker[:8]}",
        currency="EUR",
        asset_type=asset_type,
    )
    session.add_all([user, broker, asset])
    await session.flush()
    assert user.id is not None
    assert broker.id is not None
    assert asset.id is not None
    session.add(
        BrokerUserAccess(
            broker_id=broker.id,
            user_id=user.id,
            role=UserRole.OWNER,
            share_percentage=Decimal("1"),
        )
    )
    await session.flush()
    return Ledger(user_id=user.id, broker_id=broker.id, asset_id=asset.id)


async def _add_broker(
    session: AsyncSession,
    *,
    user_id: int,
    allow_asset_shorting: bool = False,
) -> int:
    broker = Broker(
        name=f"YOC broker {uuid4().hex}",
        allow_asset_shorting=allow_asset_shorting,
    )
    session.add(broker)
    await session.flush()
    assert broker.id is not None
    session.add(
        BrokerUserAccess(
            broker_id=broker.id,
            user_id=user_id,
            role=UserRole.OWNER,
            share_percentage=Decimal("1"),
        )
    )
    await session.flush()
    return broker.id


def _transaction(
    ledger: Ledger,
    tx_type: TransactionType,
    *,
    on: date,
    quantity: str = "0",
    amount: str = "0",
    currency: str | None = "EUR",
    broker_id: int | None = None,
    asset_linked: bool = True,
    related_transaction_id: int | None = None,
    asset_event_id: int | None = None,
) -> Transaction:
    return Transaction(
        broker_id=broker_id or ledger.broker_id,
        asset_id=ledger.asset_id if asset_linked else None,
        type=tx_type,
        date=on,
        quantity=Decimal(quantity),
        amount=Decimal(amount),
        currency=currency,
        related_transaction_id=related_transaction_id,
        asset_event_id=asset_event_id,
    )


async def _make_replay_topology(session: AsyncSession) -> ReplayTopology:
    """Create connected A-B and isolated C components for one asset."""
    ledger = await _make_ledger(session)
    connected_broker_id = await _add_broker(
        session,
        user_id=ledger.user_id,
    )
    isolated_broker_id = await _add_broker(
        session,
        user_id=ledger.user_id,
    )
    transfer_out = _transaction(
        ledger,
        TransactionType.TRANSFER,
        on=date(2025, 1, 10),
        quantity="-5",
        amount="0",
    )
    transfer_in = _transaction(
        ledger,
        TransactionType.TRANSFER,
        on=date(2025, 1, 15),
        quantity="5",
        amount="0",
        broker_id=connected_broker_id,
    )
    session.add_all(
        [
            _transaction(
                ledger,
                TransactionType.BUY,
                on=date(2024, 1, 1),
                quantity="10",
                amount="-100",
            ),
            transfer_out,
            transfer_in,
            _transaction(
                ledger,
                TransactionType.BUY,
                on=date(2024, 1, 1),
                quantity="10",
                amount="-100",
                broker_id=isolated_broker_id,
            ),
            _transaction(
                ledger,
                TransactionType.DIVIDEND,
                on=date(2025, 7, 1),
                amount="50",
                broker_id=connected_broker_id,
            ),
            _transaction(
                ledger,
                TransactionType.DIVIDEND,
                on=date(2025, 7, 1),
                amount="100",
                broker_id=isolated_broker_id,
            ),
        ]
    )
    await session.flush()
    assert transfer_out.id is not None
    assert transfer_in.id is not None
    transfer_out.related_transaction_id = transfer_in.id
    transfer_in.related_transaction_id = transfer_out.id
    await session.flush()
    return ReplayTopology(
        ledger=ledger,
        connected_broker_id=connected_broker_id,
        isolated_broker_id=isolated_broker_id,
    )


async def _calculate_replay_topology(
    session: AsyncSession,
    topology: ReplayTopology,
):
    return await calculate_yield_on_cost_for_positions(
        session,
        user_id=topology.ledger.user_id,
        positions=[
            YieldOnCostPositionInput(
                asset_id=topology.ledger.asset_id,
                broker_id=topology.connected_broker_id,
                wac_per_unit=Decimal("10"),
                wac_currency="EUR",
            ),
            YieldOnCostPositionInput(
                asset_id=topology.ledger.asset_id,
                broker_id=topology.isolated_broker_id,
                wac_per_unit=Decimal("10"),
                wac_currency="EUR",
            ),
        ],
        target_currency="EUR",
        as_of_date=AS_OF,
    )


async def _calculate(
    session: AsyncSession,
    ledger: Ledger,
    *,
    as_of: date = AS_OF,
    wac: Decimal | None = Decimal("10"),
    wac_currency: str | None = "EUR",
):
    calculations = await calculate_yield_on_cost_for_positions(
        session,
        user_id=ledger.user_id,
        positions=[
            YieldOnCostPositionInput(
                asset_id=ledger.asset_id,
                broker_id=ledger.broker_id,
                wac_per_unit=wac,
                wac_currency=wac_currency,
            )
        ],
        target_currency="EUR",
        as_of_date=as_of,
    )
    return calculations[(ledger.asset_id, ledger.broker_id)]


def _oracle_yoc(
    *,
    incomes: list[tuple[Decimal, Decimal, Decimal]],
    residual_wac_per_unit: Decimal,
) -> Decimal:
    """Independent contract oracle: sum(amount / eligible D-1 qty / later splits) / WAC."""
    gross_per_current_unit = sum(
        (amount / eligible_quantity / later_split_ratio for amount, eligible_quantity, later_split_ratio in incomes),
        Decimal("0"),
    )
    return gross_per_current_unit / residual_wac_per_unit


def _provenance(
    *,
    income_count: int,
    gross_income_per_unit: Decimal | None,
    net_zero: bool = False,
) -> YieldOnCostProvenance:
    return YieldOnCostProvenance(
        window_start=WINDOW_START,
        window_end=AS_OF,
        first_pair_transaction_date=WINDOW_START,
        gross_income_transaction_count=income_count,
        gross_income_per_unit=(Currency(code="EUR", amount=gross_income_per_unit) if gross_income_per_unit is not None else None),
        net_zero=net_zero,
    )


class TestYieldOnCostDependencyIdentity:
    """L2 identity for YOC's cross-broker replay universe."""

    @pytest.mark.asyncio
    async def test_identical_replay_input_is_stable(self, session):
        ledger = await _make_ledger(session)
        scope_buy = _transaction(
            ledger,
            TransactionType.BUY,
            on=date(2024, 1, 1),
            quantity="10",
            amount="-100",
        )
        session.add(scope_buy)
        await session.flush()

        first = await compute_yield_on_cost_dependency_identity(
            session,
            user_id=ledger.user_id,
            scope_transactions=[scope_buy],
            as_of_date=AS_OF,
        )
        second = await compute_yield_on_cost_dependency_identity(
            session,
            user_id=ledger.user_id,
            scope_transactions=[scope_buy],
            as_of_date=AS_OF,
        )

        assert first == second
        assert first != "no_yoc"

    @pytest.mark.asyncio
    async def test_visible_out_of_scope_same_asset_transfer_mutation_changes_identity(
        self,
        session,
    ):
        """Selected-scope tx stay unchanged; visible peer broker's arrival date moves."""
        ledger = await _make_ledger(session)
        peer_broker_id = await _add_broker(session, user_id=ledger.user_id)
        scope_buy = _transaction(
            ledger,
            TransactionType.BUY,
            on=date(2024, 1, 1),
            quantity="10",
            amount="-100",
        )
        transfer_out = _transaction(
            ledger,
            TransactionType.TRANSFER,
            on=date(2025, 3, 1),
            quantity="-4",
            amount="0",
        )
        peer_transfer_in = _transaction(
            ledger,
            TransactionType.TRANSFER,
            on=date(2025, 3, 5),
            quantity="4",
            amount="0",
            broker_id=peer_broker_id,
        )
        session.add_all([scope_buy, transfer_out, peer_transfer_in])
        await session.flush()
        assert transfer_out.id is not None
        assert peer_transfer_in.id is not None
        transfer_out.related_transaction_id = peer_transfer_in.id
        peer_transfer_in.related_transaction_id = transfer_out.id
        await session.flush()
        selected_scope_transactions = [scope_buy, transfer_out]

        baseline = await compute_yield_on_cost_dependency_identity(
            session,
            user_id=ledger.user_id,
            scope_transactions=selected_scope_transactions,
            as_of_date=AS_OF,
        )

        peer_transfer_in.date = date(2025, 3, 6)
        await session.flush()
        changed = await compute_yield_on_cost_dependency_identity(
            session,
            user_id=ledger.user_id,
            scope_transactions=selected_scope_transactions,
            as_of_date=AS_OF,
        )

        assert changed != baseline

    @pytest.mark.asyncio
    async def test_external_linked_transfer_leg_mutation_changes_identity(
        self,
        session,
    ):
        """A linked leg outside visible brokers still belongs to replay identity."""
        ledger = await _make_ledger(session)
        external_broker = Broker(name=f"YOC external broker {uuid4().hex}")
        session.add(external_broker)
        await session.flush()
        assert external_broker.id is not None

        scope_buy = _transaction(
            ledger,
            TransactionType.BUY,
            on=date(2024, 1, 1),
            quantity="10",
            amount="-100",
        )
        transfer_out = _transaction(
            ledger,
            TransactionType.TRANSFER,
            on=date(2025, 4, 1),
            quantity="-3",
            amount="0",
        )
        external_transfer_in = _transaction(
            ledger,
            TransactionType.TRANSFER,
            on=date(2025, 4, 10),
            quantity="3",
            amount="0",
            broker_id=external_broker.id,
        )
        session.add_all([scope_buy, transfer_out, external_transfer_in])
        await session.flush()
        assert transfer_out.id is not None
        assert external_transfer_in.id is not None
        transfer_out.related_transaction_id = external_transfer_in.id
        external_transfer_in.related_transaction_id = transfer_out.id
        await session.flush()
        selected_scope_transactions = [scope_buy, transfer_out]

        baseline = await compute_yield_on_cost_dependency_identity(
            session,
            user_id=ledger.user_id,
            scope_transactions=selected_scope_transactions,
            as_of_date=AS_OF,
        )

        external_transfer_in.date = date(2025, 4, 11)
        await session.flush()
        changed = await compute_yield_on_cost_dependency_identity(
            session,
            user_id=ledger.user_id,
            scope_transactions=selected_scope_transactions,
            as_of_date=AS_OF,
        )

        assert changed != baseline

    @pytest.mark.asyncio
    async def test_unrelated_asset_and_unlinked_invisible_broker_do_not_change_identity(
        self,
        session,
    ):
        ledger = await _make_ledger(session)
        scope_buy = _transaction(
            ledger,
            TransactionType.BUY,
            on=date(2024, 1, 1),
            quantity="10",
            amount="-100",
        )
        session.add(scope_buy)
        await session.flush()
        baseline = await compute_yield_on_cost_dependency_identity(
            session,
            user_id=ledger.user_id,
            scope_transactions=[scope_buy],
            as_of_date=AS_OF,
        )

        unrelated_visible_broker_id = await _add_broker(
            session,
            user_id=ledger.user_id,
        )
        marker = uuid4().hex
        unrelated_asset = Asset(
            display_name=f"Unrelated YOC asset {marker}",
            identifier_ticker=f"UYOC{marker[:8]}",
            currency="EUR",
            asset_type=AssetType.STOCK,
        )
        invisible_broker = Broker(name=f"YOC invisible broker {marker}")
        session.add_all([unrelated_asset, invisible_broker])
        await session.flush()
        assert unrelated_asset.id is not None
        assert invisible_broker.id is not None
        unrelated_transaction = Transaction(
            broker_id=unrelated_visible_broker_id,
            asset_id=unrelated_asset.id,
            type=TransactionType.BUY,
            date=date(2025, 1, 1),
            quantity=Decimal("5"),
            amount=Decimal("-50"),
            currency="EUR",
        )
        invisible_same_asset_transaction = Transaction(
            broker_id=invisible_broker.id,
            asset_id=ledger.asset_id,
            type=TransactionType.BUY,
            date=date(2025, 1, 1),
            quantity=Decimal("99"),
            amount=Decimal("-990"),
            currency="EUR",
        )
        session.add_all([unrelated_transaction, invisible_same_asset_transaction])
        await session.flush()

        unchanged = await compute_yield_on_cost_dependency_identity(
            session,
            user_id=ledger.user_id,
            scope_transactions=[scope_buy],
            as_of_date=AS_OF,
        )

        assert unchanged == baseline

        unrelated_transaction.quantity = Decimal("6")
        invisible_same_asset_transaction.quantity = Decimal("100")
        invisible_broker.allow_asset_shorting = True
        await session.flush()
        still_unchanged = await compute_yield_on_cost_dependency_identity(
            session,
            user_id=ledger.user_id,
            scope_transactions=[scope_buy],
            as_of_date=AS_OF,
        )

        assert still_unchanged == baseline

    @pytest.mark.asyncio
    async def test_split_ratio_and_type_each_change_identity(self, session):
        ledger = await _make_ledger(session)
        scope_buy = _transaction(
            ledger,
            TransactionType.BUY,
            on=date(2024, 1, 1),
            quantity="10",
            amount="-100",
        )
        split_event = AssetEvent(
            asset_id=ledger.asset_id,
            date=date(2025, 5, 1),
            type=AssetEventType.SPLIT,
            value=Decimal("2"),
            currency="EUR",
        )
        session.add_all([scope_buy, split_event])
        await session.flush()
        assert split_event.id is not None
        split_transaction = _transaction(
            ledger,
            TransactionType.ADJUSTMENT,
            on=split_event.date,
            quantity="10",
            amount="0",
            asset_event_id=split_event.id,
        )
        session.add(split_transaction)
        await session.flush()
        scope_transactions = [scope_buy, split_transaction]

        baseline = await compute_yield_on_cost_dependency_identity(
            session,
            user_id=ledger.user_id,
            scope_transactions=scope_transactions,
            as_of_date=AS_OF,
        )

        split_event.value = Decimal("3")
        await session.flush()
        changed_ratio = await compute_yield_on_cost_dependency_identity(
            session,
            user_id=ledger.user_id,
            scope_transactions=scope_transactions,
            as_of_date=AS_OF,
        )
        assert changed_ratio != baseline

        split_event.type = AssetEventType.DIVIDEND
        await session.flush()
        changed_type = await compute_yield_on_cost_dependency_identity(
            session,
            user_id=ledger.user_id,
            scope_transactions=scope_transactions,
            as_of_date=AS_OF,
        )

        assert changed_type != changed_ratio
        assert changed_type != baseline

    @pytest.mark.asyncio
    async def test_replay_broker_shorting_setting_changes_identity(self, session):
        ledger = await _make_ledger(session, allow_asset_shorting=False)
        scope_buy = _transaction(
            ledger,
            TransactionType.BUY,
            on=date(2024, 1, 1),
            quantity="10",
            amount="-100",
        )
        session.add(scope_buy)
        await session.flush()
        baseline = await compute_yield_on_cost_dependency_identity(
            session,
            user_id=ledger.user_id,
            scope_transactions=[scope_buy],
            as_of_date=AS_OF,
        )

        broker = await session.get(Broker, ledger.broker_id)
        assert broker is not None
        broker.allow_asset_shorting = True
        await session.flush()
        changed = await compute_yield_on_cost_dependency_identity(
            session,
            user_id=ledger.user_id,
            scope_transactions=[scope_buy],
            as_of_date=AS_OF,
        )

        assert changed != baseline


@pytest.mark.asyncio
async def test_positive_income_sources_window_inclusive_and_asset_linked_only(session):
    """Only asset-linked DIVIDEND/INTEREST rows inside [T-364, T] contribute (with their sign: D-MF3); FEE and TAX do not."""
    ledger = await _make_ledger(session)
    assignment = AssetProviderAssignment(
        asset_id=ledger.asset_id,
        provider_code="mockprov",
        identifier=f"YOC-{ledger.asset_id}",
        identifier_type=ProviderInputType.TICKER,
    )
    session.add(assignment)
    await session.flush()
    assert assignment.id is not None
    session.add_all(
        [
            _transaction(ledger, TransactionType.BUY, on=date(2024, 1, 1), quantity="10", amount="-100"),
            _transaction(ledger, TransactionType.DIVIDEND, on=WINDOW_START, amount="20"),
            _transaction(ledger, TransactionType.INTEREST, on=AS_OF, amount="10"),
            _transaction(ledger, TransactionType.DIVIDEND, on=date(2025, 6, 1), amount="5"),
            _transaction(ledger, TransactionType.DIVIDEND, on=WINDOW_START - timedelta(days=1), amount="700"),
            _transaction(ledger, TransactionType.FEE, on=date(2025, 6, 1), amount="-4"),
            _transaction(ledger, TransactionType.TAX, on=date(2025, 6, 1), amount="-6"),
            _transaction(
                ledger,
                TransactionType.INTEREST,
                on=date(2025, 6, 1),
                amount="900",
                asset_linked=False,
            ),
            AssetEvent(
                asset_id=ledger.asset_id,
                date=date(2025, 6, 1),
                type=AssetEventType.DIVIDEND,
                value=Decimal("1000"),
                currency="EUR",
                provider_assignment_id=assignment.id,
            ),
        ]
    )
    await session.flush()

    calculation = await _calculate(session, ledger)
    result = calculation.result

    expected = _oracle_yoc(
        incomes=[
            (Decimal("20"), Decimal("10"), Decimal("1")),
            (Decimal("5"), Decimal("10"), Decimal("1")),
            (Decimal("10"), Decimal("10"), Decimal("1")),
        ],
        residual_wac_per_unit=Decimal("10"),
    )
    assert result.status == YieldOnCostStatus.AVAILABLE
    assert result.value == expected == Decimal("0.35")
    assert result.reason is None
    assert result.provenance.window_start == WINDOW_START
    assert result.provenance.window_end == AS_OF
    assert result.provenance.gross_income_transaction_count == 3
    assert result.provenance.gross_income_per_unit is not None
    assert result.provenance.gross_income_per_unit.amount == Decimal("3.5")
    assert result.provenance.net_zero is False
    assert result.provenance.fx == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "income_type",
    [TransactionType.DIVIDEND, TransactionType.INTEREST],
    ids=["dividend", "interest"],
)
async def test_zero_valued_income_row_is_available_and_marked_net_zero(
    session,
    income_type,
):
    """A recorded zero income row is available, not synthetic no-income."""
    ledger = await _make_ledger(session)
    session.add_all(
        [
            _transaction(ledger, TransactionType.BUY, on=date(2024, 1, 1), quantity="10", amount="-100"),
            _transaction(ledger, income_type, on=date(2025, 6, 1), amount="0"),
        ]
    )
    await session.flush()

    result = (await _calculate(session, ledger)).result

    assert result.status == YieldOnCostStatus.AVAILABLE
    assert result.value == Decimal("0")
    assert result.reason is None
    assert result.provenance.gross_income_transaction_count == 1
    assert result.provenance.gross_income_per_unit is not None
    assert result.provenance.gross_income_per_unit.amount == Decimal("0")
    assert result.provenance.net_zero is True


# MF-O2 — signed window income (D-MF3). A legacy negative DIVIDEND/INTEREST row is a
# correction and lowers the income of the window. Each case below holds 10 units bought
# long before the window, so every income row divides by the same D-1 quantity of 10.


@pytest.mark.asyncio
async def test_corrections_exceeding_window_income_are_unavailable_negative_net_income(session):
    """+10 then a -30 correction: -2 EUR per unit, which has no yield to show.

    The holding is UNAVAILABLE with reason negative_net_income and keeps the negative
    gross income per unit as evidence; it must not be an AVAILABLE negative, which the
    result schema rejects and which takes the whole portfolio report down with it.
    """
    ledger = await _make_ledger(session)
    session.add_all(
        [
            _transaction(ledger, TransactionType.BUY, on=date(2024, 1, 1), quantity="10", amount="-100"),
            _transaction(ledger, TransactionType.DIVIDEND, on=date(2025, 3, 3), amount="10"),
            _transaction(ledger, TransactionType.DIVIDEND, on=date(2025, 9, 1), amount="-30"),
        ]
    )
    await session.flush()

    # A WAC other than the helper's default, so "returned as given" cannot pass by coincidence.
    calculation = await _calculate(session, ledger, wac=Decimal("12.5"))
    result = calculation.result

    assert result.status == YieldOnCostStatus.UNAVAILABLE
    assert result.reason == YieldOnCostUnavailableReason.NEGATIVE_NET_INCOME
    # The wire value the dashboard cell maps to its label.
    assert result.model_dump(mode="json")["reason"] == "negative_net_income"
    assert result.value is None
    assert result.provenance.gross_income_transaction_count == 2
    assert result.provenance.gross_income_per_unit is not None
    assert result.provenance.gross_income_per_unit.code == "EUR"
    assert result.provenance.gross_income_per_unit.amount == Decimal("-2")
    assert result.provenance.net_zero is False
    assert calculation.wac_per_unit == Decimal("12.5")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("income", "expected_gross_per_unit", "expected_value", "expected_net_zero"),
    [
        ("10", Decimal("0"), Decimal("0"), True),
        ("30", Decimal("2"), Decimal("0.2"), False),
    ],
    ids=["correction-cancels-income", "correction-below-income"],
)
async def test_corrections_within_window_income_net_to_a_non_negative_yield(
    session,
    income,
    expected_gross_per_unit,
    expected_value,
    expected_net_zero,
):
    """Controls: a correction up to the income stays AVAILABLE, netted with its sign.

    Exactly zero is an available known zero (net_zero), not negative_net_income; below
    the income the correction is subtracted, not dropped (dropping it would read 0.3).
    """
    ledger = await _make_ledger(session)
    session.add_all(
        [
            _transaction(ledger, TransactionType.BUY, on=date(2024, 1, 1), quantity="10", amount="-100"),
            _transaction(ledger, TransactionType.DIVIDEND, on=date(2025, 3, 3), amount=income),
            _transaction(ledger, TransactionType.DIVIDEND, on=date(2025, 9, 1), amount="-10"),
        ]
    )
    await session.flush()

    calculation = await _calculate(session, ledger)
    result = calculation.result

    expected = _oracle_yoc(
        incomes=[
            (Decimal(income), Decimal("10"), Decimal("1")),
            (Decimal("-10"), Decimal("10"), Decimal("1")),
        ],
        residual_wac_per_unit=Decimal("10"),
    )
    assert result.status == YieldOnCostStatus.AVAILABLE
    assert result.value == expected == expected_value
    assert result.reason is None
    assert result.provenance.gross_income_transaction_count == 2
    assert result.provenance.gross_income_per_unit is not None
    assert result.provenance.gross_income_per_unit.code == "EUR"
    assert result.provenance.gross_income_per_unit.amount == expected_gross_per_unit
    assert result.provenance.net_zero is expected_net_zero
    assert calculation.wac_per_unit == Decimal("10")


@pytest.mark.asyncio
async def test_d1_quantity_excludes_same_day_buy_and_includes_same_day_sell(session):
    ledger = await _make_ledger(session)
    income_date = date(2025, 6, 15)
    session.add_all(
        [
            _transaction(ledger, TransactionType.BUY, on=date(2024, 1, 1), quantity="10", amount="-100"),
            _transaction(ledger, TransactionType.DIVIDEND, on=income_date, amount="100"),
            _transaction(ledger, TransactionType.BUY, on=income_date, quantity="10", amount="-100"),
            _transaction(ledger, TransactionType.SELL, on=income_date, quantity="-4", amount="40"),
        ]
    )
    await session.flush()

    result = (await _calculate(session, ledger)).result

    assert result.status == YieldOnCostStatus.AVAILABLE
    assert result.value == _oracle_yoc(
        incomes=[(Decimal("100"), Decimal("10"), Decimal("1"))],
        residual_wac_per_unit=Decimal("10"),
    )


@pytest.mark.asyncio
async def test_income_is_rebased_by_same_day_and_later_splits(session):
    ledger = await _make_ledger(session)
    first_split = AssetEvent(
        asset_id=ledger.asset_id,
        date=date(2025, 1, 10),
        type=AssetEventType.SPLIT,
        value=Decimal("2"),
        currency="EUR",
    )
    second_split = AssetEvent(
        asset_id=ledger.asset_id,
        date=date(2025, 6, 1),
        type=AssetEventType.SPLIT,
        value=Decimal("3"),
        currency="EUR",
    )
    session.add_all([first_split, second_split])
    await session.flush()
    assert first_split.id is not None
    assert second_split.id is not None
    session.add_all(
        [
            _transaction(ledger, TransactionType.BUY, on=date(2024, 1, 1), quantity="10", amount="-1200"),
            _transaction(ledger, TransactionType.DIVIDEND, on=first_split.date, amount="120"),
            _transaction(
                ledger,
                TransactionType.ADJUSTMENT,
                on=first_split.date,
                quantity="10",
                asset_event_id=first_split.id,
            ),
            _transaction(
                ledger,
                TransactionType.ADJUSTMENT,
                on=second_split.date,
                quantity="40",
                asset_event_id=second_split.id,
            ),
        ]
    )
    await session.flush()

    result = (
        await _calculate(
            session,
            ledger,
            wac=Decimal("20"),
        )
    ).result

    assert result.status == YieldOnCostStatus.AVAILABLE
    assert result.value == _oracle_yoc(
        incomes=[(Decimal("120"), Decimal("10"), Decimal("6"))],
        residual_wac_per_unit=Decimal("20"),
    )
    assert result.value == Decimal("0.1")
    assert result.provenance.gross_income_per_unit is not None
    assert result.provenance.gross_income_per_unit.amount == Decimal("2")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("ratio", "adjustment_quantity", "residual_wac", "gross_per_unit"),
    [
        (Decimal("2"), "10", Decimal("50"), Decimal("5")),
        (Decimal("0.5"), "-5", Decimal("200"), Decimal("20")),
    ],
    ids=["forward", "reverse"],
)
async def test_coherent_split_quantity_keeps_yoc_available(
    session,
    ratio,
    adjustment_quantity,
    residual_wac,
    gross_per_unit,
):
    ledger = await _make_ledger(session)
    split_event = AssetEvent(
        asset_id=ledger.asset_id,
        date=date(2025, 6, 1),
        type=AssetEventType.SPLIT,
        value=ratio,
        currency="EUR",
    )
    session.add(split_event)
    await session.flush()
    assert split_event.id is not None
    session.add_all(
        [
            _transaction(
                ledger,
                TransactionType.BUY,
                on=date(2024, 1, 1),
                quantity="10",
                amount="-1000",
            ),
            _transaction(
                ledger,
                TransactionType.DIVIDEND,
                on=date(2025, 5, 1),
                amount="100",
            ),
            _transaction(
                ledger,
                TransactionType.ADJUSTMENT,
                on=split_event.date,
                quantity=adjustment_quantity,
                asset_event_id=split_event.id,
            ),
        ]
    )
    await session.flush()

    result = (
        await _calculate(
            session,
            ledger,
            wac=residual_wac,
        )
    ).result

    assert result.status == YieldOnCostStatus.AVAILABLE
    assert result.value == Decimal("0.1")
    assert result.reason is None
    assert result.provenance.gross_income_per_unit is not None
    assert result.provenance.gross_income_per_unit.amount == gross_per_unit


@pytest.mark.asyncio
async def test_edited_split_ratio_with_stale_adjustment_quantity_is_invalid(session):
    ledger = await _make_ledger(session)
    split_event = AssetEvent(
        asset_id=ledger.asset_id,
        date=date(2025, 6, 1),
        type=AssetEventType.SPLIT,
        value=Decimal("2"),
        currency="EUR",
    )
    session.add(split_event)
    await session.flush()
    assert split_event.id is not None
    session.add_all(
        [
            _transaction(
                ledger,
                TransactionType.BUY,
                on=date(2024, 1, 1),
                quantity="10",
                amount="-1000",
            ),
            _transaction(
                ledger,
                TransactionType.DIVIDEND,
                on=date(2025, 5, 1),
                amount="100",
            ),
            _transaction(
                ledger,
                TransactionType.ADJUSTMENT,
                on=split_event.date,
                quantity="10",
                asset_event_id=split_event.id,
            ),
        ]
    )
    await session.flush()

    coherent = (
        await _calculate(
            session,
            ledger,
            wac=Decimal("50"),
        )
    ).result
    assert coherent.status == YieldOnCostStatus.AVAILABLE
    assert coherent.value == Decimal("0.1")

    split_event.value = Decimal("3")
    await session.flush()

    mismatched = (
        await _calculate(
            session,
            ledger,
            wac=Decimal("50"),
        )
    ).result
    assert mismatched.status == YieldOnCostStatus.UNAVAILABLE
    assert mismatched.value is None
    assert mismatched.reason == YieldOnCostUnavailableReason.INVALID_SPLIT


@pytest.mark.asyncio
async def test_split_tolerance_is_scaled_per_scope_and_custody_candidate(session):
    """Huge transit scope must not hide a material error against tiny custody."""
    ledger = await _make_ledger(session)
    destination_broker_id = await _add_broker(
        session,
        user_id=ledger.user_id,
    )
    in_transit_quantity = Decimal("900000000000")
    total_quantity = in_transit_quantity + Decimal("1")
    split_event = AssetEvent(
        asset_id=ledger.asset_id,
        date=date(2025, 1, 7),
        type=AssetEventType.SPLIT,
        value=Decimal("2"),
        currency="EUR",
    )
    session.add(split_event)
    await session.flush()
    assert split_event.id is not None

    transfer_out = _transaction(
        ledger,
        TransactionType.TRANSFER,
        on=date(2025, 1, 5),
        quantity=str(-in_transit_quantity),
        amount="0",
    )
    transfer_in = _transaction(
        ledger,
        TransactionType.TRANSFER,
        on=date(2025, 1, 10),
        quantity=str(in_transit_quantity),
        amount="0",
        broker_id=destination_broker_id,
    )
    session.add_all(
        [
            _transaction(
                ledger,
                TransactionType.BUY,
                on=date(2024, 1, 1),
                quantity=str(total_quantity),
                amount=str(-total_quantity),
            ),
            transfer_out,
            transfer_in,
        ]
    )
    await session.flush()
    assert transfer_out.id is not None
    assert transfer_in.id is not None
    transfer_out.related_transaction_id = transfer_in.id
    transfer_in.related_transaction_id = transfer_out.id
    session.add_all(
        [
            _transaction(
                ledger,
                TransactionType.ADJUSTMENT,
                on=split_event.date,
                quantity="2",
                asset_event_id=split_event.id,
            ),
            _transaction(
                ledger,
                TransactionType.DIVIDEND,
                on=date(2025, 7, 1),
                amount="20",
            ),
        ]
    )
    await session.flush()

    result = (
        await _calculate(
            session,
            ledger,
            wac=Decimal("0.5"),
        )
    ).result

    assert result.status == YieldOnCostStatus.UNAVAILABLE
    assert result.value is None
    assert result.reason == YieldOnCostUnavailableReason.INVALID_SPLIT


@pytest.mark.asyncio
async def test_duplicate_global_split_rows_during_transit_remain_valid(session):
    """Each broker row validates against pre-event scope; event applies once."""
    ledger = await _make_ledger(session)
    destination_broker_id = await _add_broker(
        session,
        user_id=ledger.user_id,
    )
    split_event = AssetEvent(
        asset_id=ledger.asset_id,
        date=date(2025, 1, 7),
        type=AssetEventType.SPLIT,
        value=Decimal("2"),
        currency="EUR",
    )
    session.add(split_event)
    await session.flush()
    assert split_event.id is not None

    transfer_out = _transaction(
        ledger,
        TransactionType.TRANSFER,
        on=date(2025, 1, 5),
        quantity="-5",
        amount="0",
    )
    transfer_in = _transaction(
        ledger,
        TransactionType.TRANSFER,
        on=date(2025, 1, 10),
        quantity="5",
        amount="0",
        broker_id=destination_broker_id,
    )
    session.add_all(
        [
            _transaction(
                ledger,
                TransactionType.BUY,
                on=date(2024, 1, 1),
                quantity="10",
                amount="-1000",
            ),
            transfer_out,
            transfer_in,
        ]
    )
    await session.flush()
    assert transfer_out.id is not None
    assert transfer_in.id is not None
    transfer_out.related_transaction_id = transfer_in.id
    transfer_in.related_transaction_id = transfer_out.id
    session.add_all(
        [
            _transaction(
                ledger,
                TransactionType.DIVIDEND,
                on=date(2025, 1, 6),
                amount="100",
            ),
            _transaction(
                ledger,
                TransactionType.ADJUSTMENT,
                on=split_event.date,
                quantity="10",
                asset_event_id=split_event.id,
            ),
            _transaction(
                ledger,
                TransactionType.ADJUSTMENT,
                on=split_event.date,
                quantity="5",
                broker_id=destination_broker_id,
                asset_event_id=split_event.id,
            ),
        ]
    )
    await session.flush()

    result = (
        await _calculate(
            session,
            ledger,
            wac=Decimal("50"),
        )
    ).result

    assert result.status == YieldOnCostStatus.AVAILABLE
    assert result.value == Decimal("0.1")
    assert result.reason is None
    assert result.provenance.gross_income_per_unit is not None
    assert result.provenance.gross_income_per_unit.amount == Decimal("5")


@pytest.mark.asyncio
async def test_transfer_in_transit_counts_for_source_not_destination(session):
    ledger = await _make_ledger(session)
    destination_broker_id = await _add_broker(session, user_id=ledger.user_id)
    transfer_out = _transaction(
        ledger,
        TransactionType.TRANSFER,
        on=date(2025, 1, 5),
        quantity="-4",
        amount="0",
    )
    transfer_in = _transaction(
        ledger,
        TransactionType.TRANSFER,
        on=date(2025, 1, 10),
        quantity="4",
        amount="0",
        broker_id=destination_broker_id,
    )
    session.add_all(
        [
            _transaction(ledger, TransactionType.BUY, on=date(2024, 1, 1), quantity="10", amount="-100"),
            transfer_out,
            transfer_in,
        ]
    )
    await session.flush()
    assert transfer_out.id is not None
    assert transfer_in.id is not None
    transfer_out.related_transaction_id = transfer_in.id
    transfer_in.related_transaction_id = transfer_out.id
    session.add_all(
        [
            _transaction(
                ledger,
                TransactionType.DIVIDEND,
                on=date(2025, 1, 7),
                amount="100",
            ),
            _transaction(
                ledger,
                TransactionType.DIVIDEND,
                on=date(2025, 1, 7),
                amount="100",
                broker_id=destination_broker_id,
            ),
        ]
    )
    await session.flush()

    calculations = await calculate_yield_on_cost_for_positions(
        session,
        user_id=ledger.user_id,
        positions=[
            YieldOnCostPositionInput(
                asset_id=ledger.asset_id,
                broker_id=ledger.broker_id,
                wac_per_unit=Decimal("10"),
                wac_currency="EUR",
            ),
            YieldOnCostPositionInput(
                asset_id=ledger.asset_id,
                broker_id=destination_broker_id,
                wac_per_unit=Decimal("10"),
                wac_currency="EUR",
            ),
        ],
        target_currency="EUR",
        as_of_date=date(2025, 1, 31),
    )

    source = calculations[(ledger.asset_id, ledger.broker_id)].result
    destination = calculations[(ledger.asset_id, destination_broker_id)].result
    assert source.status == YieldOnCostStatus.AVAILABLE
    assert source.value == Decimal("1")
    assert destination.status == YieldOnCostStatus.UNAVAILABLE
    assert destination.value is None
    assert destination.reason == YieldOnCostUnavailableReason.INCOME_WITHOUT_ELIGIBLE_QUANTITY
    assert destination.provenance.issue_date == date(2025, 1, 7)


@pytest.mark.asyncio
async def test_one_orphan_income_invalidates_whole_position_without_partial_value(session):
    ledger = await _make_ledger(session)
    session.add_all(
        [
            _transaction(ledger, TransactionType.DIVIDEND, on=date(2025, 2, 1), amount="50"),
            _transaction(ledger, TransactionType.BUY, on=date(2025, 2, 2), quantity="10", amount="-100"),
            _transaction(ledger, TransactionType.DIVIDEND, on=date(2025, 3, 1), amount="100"),
        ]
    )
    await session.flush()

    result = (await _calculate(session, ledger)).result

    assert result.status == YieldOnCostStatus.UNAVAILABLE
    assert result.value is None
    assert result.reason == YieldOnCostUnavailableReason.INCOME_WITHOUT_ELIGIBLE_QUANTITY
    assert result.provenance.gross_income_transaction_count == 2
    assert result.provenance.gross_income_per_unit is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("first_date", "expected_status", "expected_reason"),
    [
        (WINDOW_START, YieldOnCostStatus.NO_INCOME, None),
        (
            WINDOW_START + timedelta(days=1),
            YieldOnCostStatus.UNAVAILABLE,
            YieldOnCostUnavailableReason.INSUFFICIENT_HISTORY,
        ),
    ],
)
async def test_no_income_age_boundary_is_anchored_at_t_minus_364(
    session,
    first_date,
    expected_status,
    expected_reason,
):
    ledger = await _make_ledger(session)
    session.add(
        _transaction(
            ledger,
            TransactionType.BUY,
            on=first_date,
            quantity="10",
            amount="-100",
        )
    )
    await session.flush()

    result = (await _calculate(session, ledger)).result

    assert result.status == expected_status
    assert result.reason == expected_reason
    assert result.value == (Decimal("0") if expected_status == YieldOnCostStatus.NO_INCOME else None)
    assert result.provenance.first_pair_transaction_date == first_date
    assert result.provenance.gross_income_transaction_count == 0
    if expected_status == YieldOnCostStatus.NO_INCOME:
        assert result.provenance.gross_income_per_unit is not None
        assert result.provenance.gross_income_per_unit.amount == Decimal("0")
        assert result.provenance.net_zero is False
    else:
        assert result.provenance.gross_income_per_unit is None


@pytest.mark.asyncio
async def test_young_pair_with_valid_ttm_income_is_available(session):
    """The 365-day age gate applies only to a synthetic no-income zero."""
    ledger = await _make_ledger(session)
    first_date = date(2025, 9, 1)
    session.add_all(
        [
            _transaction(
                ledger,
                TransactionType.BUY,
                on=first_date,
                quantity="10",
                amount="-100",
            ),
            _transaction(
                ledger,
                TransactionType.DIVIDEND,
                on=date(2025, 10, 1),
                amount="20",
            ),
        ]
    )
    await session.flush()

    result = (await _calculate(session, ledger)).result

    assert result.provenance.first_pair_transaction_date == first_date
    assert result.provenance.first_pair_transaction_date > WINDOW_START
    assert result.status == YieldOnCostStatus.AVAILABLE
    assert result.value == Decimal("0.2")
    assert result.reason is None


@pytest.mark.asyncio
async def test_close_and_rebuy_does_not_reset_pair_age(session):
    ledger = await _make_ledger(session)
    session.add_all(
        [
            _transaction(ledger, TransactionType.BUY, on=date(2023, 1, 1), quantity="10", amount="-100"),
            _transaction(ledger, TransactionType.SELL, on=date(2024, 1, 1), quantity="-10", amount="100"),
            _transaction(ledger, TransactionType.BUY, on=date(2025, 12, 1), quantity="5", amount="-50"),
        ]
    )
    await session.flush()

    result = (await _calculate(session, ledger)).result

    assert result.status == YieldOnCostStatus.NO_INCOME
    assert result.value == Decimal("0")
    assert result.provenance.first_pair_transaction_date == date(2023, 1, 1)


@pytest.mark.asyncio
async def test_each_income_uses_its_own_fx_date_and_wac_is_used_as_given(session):
    """Every income row is converted at its own date; the WAC, already in the report currency, is not converted at all.

    200 ZAR @ 20 + 300 ZAR @ 30 = 10 + 10 XTS over 10 units -> 2 XTS per unit; 2 / WAC 10 XTS = 0.2.
    """
    as_of = date(2042, 12, 31)
    ledger = await _make_ledger(session)
    first_income_date = date(2042, 3, 1)
    second_income_date = date(2042, 6, 1)
    session.add_all(
        [
            _transaction(ledger, TransactionType.BUY, on=date(2041, 1, 1), quantity="10", amount="-100"),
            _transaction(
                ledger,
                TransactionType.DIVIDEND,
                on=first_income_date,
                amount="200",
                currency="ZAR",
            ),
            _transaction(
                ledger,
                TransactionType.INTEREST,
                on=second_income_date,
                amount="300",
                currency="ZAR",
            ),
            FxRate(
                date=first_income_date,
                base="XTS",
                quote="ZAR",
                rate=Decimal("20"),
                source="TEST",
            ),
            FxRate(
                date=second_income_date,
                base="XTS",
                quote="ZAR",
                rate=Decimal("30"),
                source="TEST",
            ),
        ]
    )
    await session.flush()

    calculations = await calculate_yield_on_cost_for_positions(
        session,
        user_id=ledger.user_id,
        positions=[
            YieldOnCostPositionInput(
                asset_id=ledger.asset_id,
                broker_id=ledger.broker_id,
                wac_per_unit=Decimal("10"),
                wac_currency="XTS",
            )
        ],
        target_currency="XTS",
        as_of_date=as_of,
    )
    calculation = calculations[(ledger.asset_id, ledger.broker_id)]
    result = calculation.result

    assert result.status == YieldOnCostStatus.AVAILABLE
    assert result.value == Decimal("0.2")
    assert result.provenance.gross_income_per_unit is not None
    assert result.provenance.gross_income_per_unit.code == "XTS"
    assert result.provenance.gross_income_per_unit.amount == Decimal("2")
    assert calculation.wac_per_unit == Decimal("10")
    wac_entries = [entry for entry in result.provenance.fx if entry.purpose == "wac"]
    assert wac_entries == [], f"the WAC must not be converted, got FX provenance {wac_entries}"
    fx_by_purpose_and_date = {(entry.purpose, entry.requested_date): entry for entry in result.provenance.fx}
    assert set(fx_by_purpose_and_date) == {
        ("income", first_income_date),
        ("income", second_income_date),
    }
    assert fx_by_purpose_and_date[("income", first_income_date)].rate_date == first_income_date
    assert fx_by_purpose_and_date[("income", second_income_date)].rate_date == second_income_date


@pytest.mark.asyncio
async def test_wac_in_another_currency_than_report_currency_is_refused(session):
    """A WAC is a dateless historical average: it must arrive in the report currency, never be converted at as_of.

    The XTS/ZAR rate seeded on as_of is the trap: the pre-MF-O code used it to convert the
    ZAR WAC at that day's rate and returned a number instead of refusing the input. The
    valid XTS position alongside proves that one foreign WAC refuses the whole call.
    """
    as_of = date(2043, 12, 31)
    ledger = await _make_ledger(session)
    other_broker_id = await _add_broker(session, user_id=ledger.user_id)
    session.add_all(
        [
            _transaction(ledger, TransactionType.BUY, on=date(2042, 1, 1), quantity="10", amount="-100"),
            _transaction(
                ledger,
                TransactionType.DIVIDEND,
                on=date(2043, 6, 1),
                amount="20",
                currency="XTS",
            ),
            FxRate(
                date=as_of,
                base="XTS",
                quote="ZAR",
                rate=Decimal("40"),
                source="TEST",
            ),
        ]
    )
    await session.flush()

    with pytest.raises(ValueError, match="report currency"):
        await calculate_yield_on_cost_for_positions(
            session,
            user_id=ledger.user_id,
            positions=[
                YieldOnCostPositionInput(
                    asset_id=ledger.asset_id,
                    broker_id=other_broker_id,
                    wac_per_unit=Decimal("10"),
                    wac_currency="XTS",
                ),
                YieldOnCostPositionInput(
                    asset_id=ledger.asset_id,
                    broker_id=ledger.broker_id,
                    wac_per_unit=Decimal("400"),
                    wac_currency="ZAR",
                ),
            ],
            target_currency="XTS",
            as_of_date=as_of,
        )


@pytest.mark.asyncio
async def test_wac_in_report_currency_is_never_sent_to_fx_conversion(
    session,
    monkeypatch,
):
    """Only income rows reach convert_bulk; the WAC is used exactly as supplied.

    100 ZAR @ 25 = 4 XTS over 10 units -> 0.4 XTS per unit; 0.4 / WAC 8 XTS = 0.05.
    """
    as_of = date(2044, 12, 31)
    income_date = date(2044, 4, 1)
    wac = Decimal("8")
    ledger = await _make_ledger(session)
    session.add_all(
        [
            _transaction(ledger, TransactionType.BUY, on=date(2043, 1, 1), quantity="10", amount="-100"),
            _transaction(
                ledger,
                TransactionType.DIVIDEND,
                on=income_date,
                amount="100",
                currency="ZAR",
            ),
            FxRate(
                date=income_date,
                base="XTS",
                quote="ZAR",
                rate=Decimal("25"),
                source="TEST",
            ),
        ]
    )
    await session.flush()

    real_convert_bulk = yoc_module.convert_bulk
    sent: list[tuple[str, Decimal, str, date]] = []

    async def recording_convert_bulk(db, inputs, *, raise_on_error):
        sent.extend((amount.code, amount.amount, target_currency, requested_date) for amount, target_currency, requested_date in inputs)
        return await real_convert_bulk(db, inputs, raise_on_error=raise_on_error)

    monkeypatch.setattr(yoc_module, "convert_bulk", recording_convert_bulk)

    calculations = await calculate_yield_on_cost_for_positions(
        session,
        user_id=ledger.user_id,
        positions=[
            YieldOnCostPositionInput(
                asset_id=ledger.asset_id,
                broker_id=ledger.broker_id,
                wac_per_unit=wac,
                wac_currency="XTS",
            )
        ],
        target_currency="XTS",
        as_of_date=as_of,
    )
    calculation = calculations[(ledger.asset_id, ledger.broker_id)]
    result = calculation.result

    wac_inputs = [entry for entry in sent if entry[1] == wac or entry[3] == as_of]
    assert wac_inputs == [], f"the WAC reached convert_bulk: {wac_inputs}"
    assert sent == [("ZAR", Decimal("100"), "XTS", income_date)]
    assert result.status == YieldOnCostStatus.AVAILABLE
    assert result.value == Decimal("0.05")
    assert result.provenance.gross_income_per_unit is not None
    assert result.provenance.gross_income_per_unit.code == "XTS"
    assert result.provenance.gross_income_per_unit.amount == Decimal("0.4")
    assert [(entry.purpose, entry.requested_date, entry.rate_date) for entry in result.provenance.fx] == [
        ("income", income_date, income_date),
    ]
    assert calculation.wac_per_unit == wac


@pytest.mark.asyncio
async def test_missing_fx_invalidates_whole_position_without_partial_fallback(
    session,
    monkeypatch,
):
    ledger = await _make_ledger(session)
    missing_date = date(2025, 5, 2)
    session.add_all(
        [
            _transaction(ledger, TransactionType.BUY, on=date(2024, 1, 1), quantity="10", amount="-100"),
            _transaction(ledger, TransactionType.DIVIDEND, on=date(2025, 5, 1), amount="20"),
            _transaction(
                ledger,
                TransactionType.INTEREST,
                on=missing_date,
                amount="30",
                currency="USD",
            ),
        ]
    )
    await session.flush()

    async def deterministic_convert_bulk(_db, inputs, *, raise_on_error):
        assert raise_on_error is False
        results = [(amount, requested_date, False) if amount.code == target_currency else None for amount, target_currency, requested_date in inputs]
        return results, ["USD/EUR unavailable"]

    monkeypatch.setattr(yoc_module, "convert_bulk", deterministic_convert_bulk)

    calculation = await _calculate(session, ledger)
    result = calculation.result

    assert result.status == YieldOnCostStatus.UNAVAILABLE
    assert result.value is None
    assert result.reason == YieldOnCostUnavailableReason.MISSING_FX
    assert result.provenance.gross_income_transaction_count == 2
    assert result.provenance.gross_income_per_unit is None
    assert result.provenance.issue_pair == "USD/EUR"
    assert result.provenance.issue_date == missing_date
    assert calculation.missing_fx_pairs


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("wac", "wac_currency", "expected_reason"),
    [
        (None, "EUR", YieldOnCostUnavailableReason.MISSING_WAC),
        (Decimal("10"), None, YieldOnCostUnavailableReason.MISSING_WAC),
        (Decimal("0"), "EUR", YieldOnCostUnavailableReason.NON_POSITIVE_WAC),
        (Decimal("-1"), "EUR", YieldOnCostUnavailableReason.NON_POSITIVE_WAC),
    ],
)
async def test_missing_or_nonpositive_wac_is_unavailable(
    session,
    wac,
    wac_currency,
    expected_reason,
):
    ledger = await _make_ledger(session)
    session.add_all(
        [
            _transaction(ledger, TransactionType.BUY, on=date(2024, 1, 1), quantity="10", amount="-100"),
            _transaction(ledger, TransactionType.DIVIDEND, on=date(2025, 5, 1), amount="20"),
        ]
    )
    await session.flush()

    calculation = await _calculate(
        session,
        ledger,
        wac=wac,
        wac_currency=wac_currency,
    )

    assert calculation.result.status == YieldOnCostStatus.UNAVAILABLE
    assert calculation.result.value is None
    assert calculation.result.reason == expected_reason


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("wac", "wac_currency", "expected_status", "expected_value", "expected_reason", "expected_wac"),
    [
        (Decimal("10"), "eur", YieldOnCostStatus.AVAILABLE, Decimal("0.2"), None, Decimal("10")),
        (None, "USD", YieldOnCostStatus.UNAVAILABLE, None, YieldOnCostUnavailableReason.MISSING_WAC, None),
        (Decimal("10"), None, YieldOnCostStatus.UNAVAILABLE, None, YieldOnCostUnavailableReason.MISSING_WAC, None),
        (Decimal("10"), "", YieldOnCostStatus.UNAVAILABLE, None, YieldOnCostUnavailableReason.MISSING_WAC, None),
    ],
    ids=["lowercase-report-currency", "no-wac-in-foreign-currency", "no-currency", "empty-currency"],
)
async def test_wac_refusal_spares_normalized_report_currency_and_missing_wac(
    session,
    wac,
    wac_currency,
    expected_status,
    expected_value,
    expected_reason,
    expected_wac,
):
    """Only a priced WAC whose normalized code differs from the report currency is refused.

    Replaces test_converted_nonpositive_wac_is_typed_unavailable: nothing converts the WAC any
    more, so a positive WAC can no longer turn non-positive (pinned by
    test_wac_in_report_currency_is_never_sent_to_fx_conversion) and the foreign-WAC refusal is
    test_wac_in_another_currency_than_report_currency_is_refused; what is left to pin is where
    the refusal stops: codes compared after normalization, missing WAC still typed MISSING_WAC.
    """
    ledger = await _make_ledger(session)
    session.add_all(
        [
            _transaction(ledger, TransactionType.BUY, on=date(2024, 1, 1), quantity="10", amount="-100"),
            _transaction(ledger, TransactionType.DIVIDEND, on=date(2025, 5, 1), amount="20"),
        ]
    )
    await session.flush()

    calculation = await _calculate(
        session,
        ledger,
        wac=wac,
        wac_currency=wac_currency,
    )

    assert calculation.result.status == expected_status
    assert calculation.result.value == expected_value
    assert calculation.result.reason == expected_reason
    assert calculation.result.provenance.fx == []
    assert calculation.wac_per_unit == expected_wac


@pytest.mark.asyncio
async def test_replay_failure_is_unavailable_not_partial(
    session,
    monkeypatch,
):
    ledger = await _make_ledger(session)
    session.add_all(
        [
            _transaction(ledger, TransactionType.BUY, on=date(2024, 1, 1), quantity="10", amount="-100"),
            _transaction(ledger, TransactionType.DIVIDEND, on=date(2025, 5, 1), amount="20"),
        ]
    )
    await session.flush()
    monkeypatch.setattr(yoc_module, "_run_component_replay", lambda **_kwargs: None)

    result = (await _calculate(session, ledger)).result

    assert result.status == YieldOnCostStatus.UNAVAILABLE
    assert result.value is None
    assert result.reason == YieldOnCostUnavailableReason.REPLAY_INCONSISTENT
    assert result.provenance.gross_income_per_unit is None


@pytest.mark.asyncio
async def test_split_quantity_mismatch_fails_only_transfer_connected_component(
    session,
):
    topology = await _make_replay_topology(session)
    split_event = AssetEvent(
        asset_id=topology.ledger.asset_id,
        date=date(2025, 6, 1),
        type=AssetEventType.SPLIT,
        value=Decimal("2"),
        currency="EUR",
    )
    session.add(split_event)
    await session.flush()
    assert split_event.id is not None
    session.add(
        _transaction(
            topology.ledger,
            TransactionType.ADJUSTMENT,
            on=split_event.date,
            quantity="4",
            asset_event_id=split_event.id,
        )
    )
    await session.flush()

    calculations = await _calculate_replay_topology(session, topology)
    connected = calculations[(topology.ledger.asset_id, topology.connected_broker_id)].result
    isolated = calculations[(topology.ledger.asset_id, topology.isolated_broker_id)].result

    assert connected.status == YieldOnCostStatus.UNAVAILABLE
    assert connected.value is None
    assert connected.reason == YieldOnCostUnavailableReason.INVALID_SPLIT
    assert isolated.status == YieldOnCostStatus.AVAILABLE
    assert isolated.value == Decimal("1")
    assert isolated.reason is None


@pytest.mark.asyncio
async def test_post_income_split_only_on_connected_other_broker_is_invalid(
    session,
):
    """Income/current broker needs its own row for every later global split."""
    topology = await _make_replay_topology(session)
    other_broker_split = AssetEvent(
        asset_id=topology.ledger.asset_id,
        date=date(2025, 8, 1),
        type=AssetEventType.SPLIT,
        value=Decimal("2"),
        currency="EUR",
    )
    session.add(other_broker_split)
    await session.flush()
    assert other_broker_split.id is not None
    session.add(
        _transaction(
            topology.ledger,
            TransactionType.ADJUSTMENT,
            on=other_broker_split.date,
            quantity="5",
            broker_id=topology.ledger.broker_id,
            asset_event_id=other_broker_split.id,
        )
    )
    await session.flush()

    calculations = await _calculate_replay_topology(session, topology)
    income_broker = calculations[(topology.ledger.asset_id, topology.connected_broker_id)].result
    isolated = calculations[(topology.ledger.asset_id, topology.isolated_broker_id)].result

    assert income_broker.status == YieldOnCostStatus.UNAVAILABLE
    assert income_broker.value is None
    assert income_broker.reason == YieldOnCostUnavailableReason.INVALID_SPLIT
    assert isolated.status == YieldOnCostStatus.AVAILABLE
    assert isolated.value == Decimal("1")


@pytest.mark.asyncio
async def test_replay_failure_fails_only_transfer_connected_component(
    session,
    monkeypatch,
):
    topology = await _make_replay_topology(session)
    original_replay = yoc_module._run_component_replay

    def fail_connected_component(**kwargs):
        if topology.ledger.broker_id in kwargs["component"]:
            return None
        return original_replay(**kwargs)

    monkeypatch.setattr(
        yoc_module,
        "_run_component_replay",
        fail_connected_component,
    )

    calculations = await _calculate_replay_topology(session, topology)
    connected = calculations[(topology.ledger.asset_id, topology.connected_broker_id)].result
    isolated = calculations[(topology.ledger.asset_id, topology.isolated_broker_id)].result

    assert connected.status == YieldOnCostStatus.UNAVAILABLE
    assert connected.value is None
    assert connected.reason == YieldOnCostUnavailableReason.REPLAY_INCONSISTENT
    assert isolated.status == YieldOnCostStatus.AVAILABLE
    assert isolated.value == Decimal("1")
    assert isolated.reason is None


@pytest.mark.asyncio
async def test_malformed_linked_split_is_unavailable_not_partial(session):
    ledger = await _make_ledger(session)
    split_event = AssetEvent(
        asset_id=ledger.asset_id,
        date=date(2025, 6, 1),
        type=AssetEventType.SPLIT,
        value=Decimal("2"),
        currency="EUR",
    )
    session.add(split_event)
    await session.flush()
    assert split_event.id is not None
    session.add_all(
        [
            _transaction(ledger, TransactionType.BUY, on=date(2024, 1, 1), quantity="10", amount="-100"),
            _transaction(ledger, TransactionType.DIVIDEND, on=date(2025, 5, 1), amount="20"),
            _transaction(
                ledger,
                TransactionType.ADJUSTMENT,
                on=split_event.date + timedelta(days=1),
                quantity="10",
                asset_event_id=split_event.id,
            ),
        ]
    )
    await session.flush()

    result = (await _calculate(session, ledger)).result

    assert result.status == YieldOnCostStatus.UNAVAILABLE
    assert result.value is None
    assert result.reason == YieldOnCostUnavailableReason.INVALID_SPLIT
    assert result.provenance.gross_income_per_unit is None


@pytest.mark.asyncio
async def test_every_asset_type_uses_the_same_yield_on_cost_contract(session):
    asset_types = list(AssetType)
    ledgers = [await _make_ledger(session, asset_type=asset_types[0])]
    for asset_type in asset_types[1:]:
        marker = uuid4().hex
        asset = Asset(
            display_name=f"YOC asset {marker}",
            identifier_ticker=f"YOC{marker[:8]}",
            currency="EUR",
            asset_type=asset_type,
        )
        session.add(asset)
        await session.flush()
        assert asset.id is not None
        ledgers.append(
            Ledger(
                user_id=ledgers[0].user_id,
                broker_id=ledgers[0].broker_id,
                asset_id=asset.id,
            )
        )
    for ledger in ledgers:
        session.add_all(
            [
                _transaction(ledger, TransactionType.BUY, on=date(2024, 1, 1), quantity="10", amount="-100"),
                _transaction(ledger, TransactionType.DIVIDEND, on=date(2025, 5, 1), amount="10"),
            ]
        )
    await session.flush()

    calculations = await calculate_yield_on_cost_for_positions(
        session,
        user_id=ledgers[0].user_id,
        positions=[
            YieldOnCostPositionInput(
                asset_id=ledger.asset_id,
                broker_id=ledger.broker_id,
                wac_per_unit=Decimal("10"),
                wac_currency="EUR",
            )
            for ledger in ledgers
        ],
        target_currency="EUR",
        as_of_date=AS_OF,
    )

    for ledger in ledgers:
        result = calculations[(ledger.asset_id, ledger.broker_id)].result
        assert result.status == YieldOnCostStatus.AVAILABLE
        assert result.value == Decimal("0.1")


@pytest.mark.parametrize(
    ("value", "gross_income_per_unit", "net_zero"),
    [
        (Decimal("0.1"), Decimal("1"), False),
        (Decimal("0.1"), Decimal("0"), False),
        (Decimal("0"), Decimal("0"), True),
    ],
    ids=[
        "positive-value-positive-income",
        "positive-value-zero-income",
        "zero-value-zero-income",
    ],
)
def test_available_schema_accepts_non_negative_values_with_matching_net_zero(
    value,
    gross_income_per_unit,
    net_zero,
):
    result = YieldOnCostResult(
        status=YieldOnCostStatus.AVAILABLE,
        value=value,
        provenance=_provenance(
            income_count=1,
            gross_income_per_unit=gross_income_per_unit,
            net_zero=net_zero,
        ),
    )

    assert result.value == value
    assert result.provenance.net_zero is net_zero


@pytest.mark.parametrize(
    ("value", "income_count", "gross_income_per_unit", "reason", "net_zero"),
    [
        (None, 1, Decimal("1"), None, False),
        (Decimal("-0.1"), 1, Decimal("1"), None, False),
        (Decimal("0.1"), 0, Decimal("1"), None, False),
        (Decimal("0.1"), 1, None, None, False),
        (Decimal("0.1"), 1, Decimal("-1"), None, False),
        (
            Decimal("0.1"),
            1,
            Decimal("1"),
            YieldOnCostUnavailableReason.MISSING_FX,
            False,
        ),
        (Decimal("0"), 1, Decimal("0"), None, False),
        (Decimal("0.1"), 1, Decimal("1"), None, True),
    ],
    ids=[
        "missing-value",
        "negative-value",
        "no-income-rows",
        "missing-income-per-unit",
        "negative-income-per-unit",
        "reason-present",
        "zero-value-without-net-zero",
        "positive-value-with-net-zero",
    ],
)
def test_available_schema_rejects_invalid_shape_or_net_zero_mismatch(
    value,
    income_count,
    gross_income_per_unit,
    reason,
    net_zero,
):
    with pytest.raises(ValidationError):
        YieldOnCostResult(
            status=YieldOnCostStatus.AVAILABLE,
            value=value,
            reason=reason,
            provenance=_provenance(
                income_count=income_count,
                gross_income_per_unit=gross_income_per_unit,
                net_zero=net_zero,
            ),
        )


@pytest.mark.parametrize(
    ("value", "income_count", "gross_income_per_unit", "reason"),
    [
        (None, 0, Decimal("0"), None),
        (Decimal("0.1"), 0, Decimal("0"), None),
        (Decimal("0"), 1, Decimal("0"), None),
        (Decimal("0"), 0, None, None),
        (Decimal("0"), 0, Decimal("1"), None),
        (
            Decimal("0"),
            0,
            Decimal("0"),
            YieldOnCostUnavailableReason.INSUFFICIENT_HISTORY,
        ),
    ],
    ids=[
        "missing-zero",
        "positive-value",
        "income-rows-present",
        "missing-income-per-unit",
        "positive-income-per-unit",
        "reason-present",
    ],
)
def test_no_income_schema_requires_known_zero_without_income(
    value,
    income_count,
    gross_income_per_unit,
    reason,
):
    with pytest.raises(ValidationError):
        YieldOnCostResult(
            status=YieldOnCostStatus.NO_INCOME,
            value=value,
            reason=reason,
            provenance=_provenance(
                income_count=income_count,
                gross_income_per_unit=gross_income_per_unit,
            ),
        )


@pytest.mark.parametrize(
    ("status", "value", "income_count", "gross_income_per_unit", "reason"),
    [
        (
            YieldOnCostStatus.NO_INCOME,
            Decimal("0"),
            0,
            Decimal("0"),
            None,
        ),
        (
            YieldOnCostStatus.UNAVAILABLE,
            None,
            0,
            None,
            YieldOnCostUnavailableReason.INSUFFICIENT_HISTORY,
        ),
    ],
    ids=["no-income", "unavailable"],
)
def test_non_available_schema_requires_net_zero_false(
    status,
    value,
    income_count,
    gross_income_per_unit,
    reason,
):
    result = YieldOnCostResult(
        status=status,
        value=value,
        reason=reason,
        provenance=_provenance(
            income_count=income_count,
            gross_income_per_unit=gross_income_per_unit,
            net_zero=False,
        ),
    )

    assert result.provenance.net_zero is False

    with pytest.raises(ValidationError):
        YieldOnCostResult(
            status=status,
            value=value,
            reason=reason,
            provenance=_provenance(
                income_count=income_count,
                gross_income_per_unit=gross_income_per_unit,
                net_zero=True,
            ),
        )


def test_portfolio_holding_requires_non_null_yield_on_cost():
    with pytest.raises(ValidationError):
        PortfolioHolding(
            asset_id=1,
            asset_name="Required YOC holding",
            asset_type="STOCK",
            quantity=Decimal("1"),
        )

    with pytest.raises(ValidationError):
        PortfolioHolding(
            asset_id=1,
            asset_name="Required YOC holding",
            asset_type="STOCK",
            quantity=Decimal("1"),
            yield_on_cost=None,
        )

    no_income = YieldOnCostResult(
        status=YieldOnCostStatus.NO_INCOME,
        value=Decimal("0"),
        provenance=_provenance(
            income_count=0,
            gross_income_per_unit=Decimal("0"),
        ),
    )
    holding = PortfolioHolding(
        asset_id=1,
        asset_name="Required YOC holding",
        asset_type="STOCK",
        quantity=Decimal("1"),
        yield_on_cost=no_income,
    )

    assert holding.yield_on_cost == no_income
    assert holding.yield_on_cost.status == YieldOnCostStatus.NO_INCOME
    assert holding.yield_on_cost.value == Decimal("0")
    assert "yield_on_cost" in holding.model_dump()
    assert holding.yield_on_cost.provenance.net_zero is False


# =============================================================================
# J-51 — a receiver whose units came from a broker the user cannot see
# =============================================================================
#
# Workstream J, lot J-51 (coordinator, 17/10). YoC replays the asset's rows at the brokers the user can see — their
# BrokerUserAccess rows plus the positions' brokers (_load_transaction_context) —, adds the partner of every TRANSFER
# whose partner was not loaded (_include_external_transfer_legs) and replays each transfer-connected component of
# brokers (_broker_components). For a RECEIVER the user can see (B) whose units came from a broker the user cannot see
# (A), the component {A, B} replays an A that holds only its departure — A's purchase is never loaded —: the FIFO engine
# reports FIFO_SOURCE_QUANTITY_MISSING on it, the replay is FAILED (_component_replay_failure), B's key is failed and
# _calculate_position returns REPLAY_INCONSISTENT. The SENDER side (A visible, B not) works and stays as it is.
#
# The fix: YoC replays with the arrivals read at the edge of the visible brokers (read_arrivals_at_scope_boundary,
# financial_math/lots/scope_boundary.py): J-10's reading of an arrival, an ADJUSTMENT-in of its units on its date at its
# own cost. The partner of a read arrival leaves the replay; a departure keeps its partner. The ledger as stored still
# feeds compute_yield_on_cost_dependency_identity and the split links.
#
# THE BOOK. A belongs to one user, B to another; the viewer owns one of the two and has no access to the other. A buys
# 10 X for 100 EUR on 1 Jan 2024 (10 EUR a unit) and sends 4 on 1 Mar 2025; B receives them on 5 Mar, its leg carrying
# a cost basis of 16 EUR a unit — its own, not A's 10, so that a figure taken from the leg shows. The pair is linked both
# ways; each test adds its income. Read on AS_OF, 31 Dec 2025: the trailing window starts on 1 Jan 2025.

J51_PURCHASE_DAY = date(2024, 1, 1)
J51_DEPARTURE_DAY = date(2025, 3, 1)  # A sends 4 X
J51_ARRIVAL_DAY = date(2025, 3, 5)  # B receives them
J51_INCOME_DAY = date(2025, 6, 1)
J51_ARRIVAL_COST_BASIS = Decimal("16")  # per unit, in EUR, on B's leg


@dataclass(frozen=True)
class ArrivalBook:
    ledger: Ledger  # broker A, asset X and A's owner
    viewer_id: int  # the user whose figures are read: the owner of A or of B
    receiver_broker_id: int  # B
    departure: Transaction  # A's leg
    arrival: Transaction  # B's leg


async def _add_user(session: AsyncSession) -> int:
    marker = uuid4().hex
    user = User(
        username=f"yoc_{marker}",
        email=f"yoc_{marker}@test.invalid",
        hashed_password="not-used",
        is_active=True,
    )
    session.add(user)
    await session.flush()
    assert user.id is not None
    return user.id


async def _arrival_book(
    session: AsyncSession,
    *,
    viewer: Literal["sender", "receiver"],
    departure_quantity: str = "-4",
    arrival_cost_basis: Decimal | None = J51_ARRIVAL_COST_BASIS,
) -> ArrivalBook:
    """THE BOOK above; ``viewer`` owns A (the sender) or B (the receiver) and cannot see the other broker."""
    ledger = await _make_ledger(session)
    receiver_owner_id = await _add_user(session)
    receiver_broker_id = await _add_broker(session, user_id=receiver_owner_id)
    departure = _transaction(ledger, TransactionType.TRANSFER, on=J51_DEPARTURE_DAY, quantity=departure_quantity)
    arrival = _transaction(ledger, TransactionType.TRANSFER, on=J51_ARRIVAL_DAY, quantity="4", broker_id=receiver_broker_id)
    # The model wants a cost basis and its currency together, or neither.
    arrival.cost_basis_override = arrival_cost_basis
    arrival.cost_basis_currency = None if arrival_cost_basis is None else "EUR"
    session.add_all(
        [
            _transaction(ledger, TransactionType.BUY, on=J51_PURCHASE_DAY, quantity="10", amount="-100"),
            departure,
            arrival,
        ]
    )
    await session.flush()
    assert departure.id is not None
    assert arrival.id is not None
    departure.related_transaction_id = arrival.id
    arrival.related_transaction_id = departure.id
    await session.flush()
    return ArrivalBook(
        ledger=ledger,
        viewer_id=ledger.user_id if viewer == "sender" else receiver_owner_id,
        receiver_broker_id=receiver_broker_id,
        departure=departure,
        arrival=arrival,
    )


async def _add_income(session: AsyncSession, book: ArrivalBook, *, broker_id: int, on: date, amount: str) -> Transaction:
    income = _transaction(book.ledger, TransactionType.DIVIDEND, on=on, amount=amount, broker_id=broker_id)
    session.add(income)
    await session.flush()
    return income


async def _yield_on_cost_of(session: AsyncSession, book: ArrivalBook, *, broker_id: int, wac: Decimal) -> YieldOnCostResult:
    """The viewer's YoC of X at ``broker_id``, with ``wac`` given in the report currency, EUR."""
    calculations = await calculate_yield_on_cost_for_positions(
        session,
        user_id=book.viewer_id,
        positions=[
            YieldOnCostPositionInput(
                asset_id=book.ledger.asset_id,
                broker_id=broker_id,
                wac_per_unit=wac,
                wac_currency="EUR",
            )
        ],
        target_currency="EUR",
        as_of_date=AS_OF,
    )
    return calculations[(book.ledger.asset_id, broker_id)].result


def _yield_view(result: YieldOnCostResult) -> dict:
    gross = result.provenance.gross_income_per_unit
    return {
        "status": result.status,
        "value": result.value,
        "reason": result.reason,
        "gross income per unit": None if gross is None else (gross.code, gross.amount),
    }


async def _dashboard_holding_at_b(session: AsyncSession, book: ArrivalBook) -> PortfolioHolding:
    """B's holding of X in the viewer's real Dashboard summary: PortfolioService.get_summary, in EUR, up to AS_OF."""
    summary = await PortfolioService(session).get_summary(user_id=book.viewer_id, target_currency_override="EUR", date_to=AS_OF)
    at_b = [holding for holding in summary.holdings if holding.asset_id == book.ledger.asset_id and holding.broker_id == book.receiver_broker_id]
    assert len(at_b) == 1, f"B's holding of X must be in the viewer's summary once: {at_b}"
    return at_b[0]


def _holding_view(holding: PortfolioHolding) -> dict:
    """What the Dashboard shows of B's holding: its quantity, its WAC and its YoC."""
    yield_on_cost = holding.yield_on_cost
    return {
        "quantity": holding.quantity,
        "wac_per_unit": holding.wac_per_unit,
        "yield_on_cost": {"status": yield_on_cost.status, "value": yield_on_cost.value, "reason": yield_on_cost.reason},
    }


@pytest.mark.asyncio
async def test_a_receiver_whose_units_came_from_a_broker_it_cannot_see_yields_on_the_units_that_arrived(session):
    """J-51 V1 (RED). The viewer sees B only. B's dividend of 8 EUR on 1 Jun is paid on the 4 X that arrived on 5 Mar:
    8 / 4 = 2 EUR a unit, over the WAC the Dashboard gives B — its leg's own cost basis, 16 EUR, pinned through the real
    path by test_dashboard_costs_the_arrived_units_at_their_legs_own_cost_basis_and_yields_on_them —: 2 / 16 = 0.125.

    Today: unavailable, REPLAY_INCONSISTENT, no value. The viewer cannot see A, so A's purchase is never loaded; A's
    departure is (the partner of B's arrival) and joins A to B's component, whose replay meets a departure from a
    broker that holds nothing: FIFO_SOURCE_QUANTITY_MISSING, FAILED.
    After: available, 0.125 — B's arrival read as an ADJUSTMENT-in of 4 on 5 Mar, A's departure out of the replay.
    """
    book = await _arrival_book(session, viewer="receiver")
    await _add_income(session, book, broker_id=book.receiver_broker_id, on=J51_INCOME_DAY, amount="8")

    result = await _yield_on_cost_of(session, book, broker_id=book.receiver_broker_id, wac=J51_ARRIVAL_COST_BASIS)

    assert _oracle_yoc(incomes=[(Decimal("8"), Decimal("4"), Decimal("1"))], residual_wac_per_unit=J51_ARRIVAL_COST_BASIS) == Decimal("0.125")
    assert _yield_view(result) == {
        "status": YieldOnCostStatus.AVAILABLE,
        "value": Decimal("0.125"),
        "reason": None,
        "gross income per unit": ("EUR", Decimal("2")),
    }


@pytest.mark.asyncio
async def test_guard_a_sender_whose_units_went_to_a_broker_it_cannot_see_keeps_counting_them_in_transit(session):
    """J-51 GUARD (green today and after). The viewer sees A only. A's dividend of 30 EUR on 3 Mar is paid during the
    transit — its day before, 2 Mar, falls between the departure of 1 Mar and the arrival of 5 Mar — and YoC counts the
    4 X in transit for the source: 30 / 10 = 3 EUR a unit. The dividend of 12 EUR on 1 Jun is paid on the 6 left:
    12 / 6 = 2. Over A's WAC, 10 EUR: (3 + 2) / 10 = 0.5. A's departure is no arrival: the fix leaves it, with its
    partner, in the replay (test_transfer_in_transit_counts_for_source_not_destination: the same rule, both brokers seen).
    """
    book = await _arrival_book(session, viewer="sender")
    await _add_income(session, book, broker_id=book.ledger.broker_id, on=date(2025, 3, 3), amount="30")
    await _add_income(session, book, broker_id=book.ledger.broker_id, on=J51_INCOME_DAY, amount="12")

    result = await _yield_on_cost_of(session, book, broker_id=book.ledger.broker_id, wac=Decimal("10"))

    assert _oracle_yoc(incomes=[(Decimal("30"), Decimal("10"), Decimal("1")), (Decimal("12"), Decimal("6"), Decimal("1"))], residual_wac_per_unit=Decimal("10")) == Decimal("0.5")
    assert _yield_view(result) == {
        "status": YieldOnCostStatus.AVAILABLE,
        "value": Decimal("0.5"),
        "reason": None,
        "gross income per unit": ("EUR", Decimal("5")),
    }


@pytest.mark.asyncio
async def test_guard_an_arrival_whose_invisible_partner_does_not_pair_back_stays_unavailable(session):
    """J-51 GUARD (green today and after). V1's book, but A's leg sends 3 for B's 4: the pair does not match — the same
    absolute quantity is one of the checks an arrival must pass to be read —, so the arrival is not read and the replay
    keeps the pair, which the FIFO engine rejects (TRANSFER_PAIR_MISSING on A's leg, FAILED): unavailable,
    REPLAY_INCONSISTENT, no value. Never a yield over 4 units no leg sent.
    """
    book = await _arrival_book(session, viewer="receiver", departure_quantity="-3")
    await _add_income(session, book, broker_id=book.receiver_broker_id, on=J51_INCOME_DAY, amount="8")

    result = await _yield_on_cost_of(session, book, broker_id=book.receiver_broker_id, wac=J51_ARRIVAL_COST_BASIS)

    assert _yield_view(result) == {
        "status": YieldOnCostStatus.UNAVAILABLE,
        "value": None,
        "reason": YieldOnCostUnavailableReason.REPLAY_INCONSISTENT,
        "gross income per unit": None,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("date", date(2025, 3, 2), id="partner-date"),
        pytest.param("quantity", Decimal("-3"), id="partner-quantity"),
    ],
)
@pytest.mark.asyncio
async def test_guard_the_invisible_partner_of_an_arrival_still_feeds_the_identity(session, field, value):
    """J-51 GUARD (green today and after): the arrival's case of test_external_linked_transfer_leg_mutation_changes_identity.
    The identity hashes the ledger as stored — the viewer's rows and the partners they name — whether or not YoC reads
    the arrival. V1's viewer sees B only; its identity changes when A's leg, which it cannot see, changes its date, or
    its quantity: the field that decides whether the arrival is read at all.
    """
    book = await _arrival_book(session, viewer="receiver")
    income = await _add_income(session, book, broker_id=book.receiver_broker_id, on=J51_INCOME_DAY, amount="8")

    async def identity() -> str:
        return await compute_yield_on_cost_dependency_identity(
            session,
            user_id=book.viewer_id,
            scope_transactions=[book.arrival, income],
            as_of_date=AS_OF,
        )

    baseline = await identity()
    assert await identity() == baseline, "precondition broken: the identity of an unchanged ledger must be stable"

    setattr(book.departure, field, value)
    await session.flush()

    assert await identity() != baseline


@pytest.mark.asyncio
async def test_dashboard_costs_the_arrived_units_at_their_legs_own_cost_basis_and_yields_on_them(session):
    """J-51 (RED), through the real Dashboard path. YoC's denominator is the Dashboard position's WAC
    (PortfolioService.get_summary builds YieldOnCostPositionInput(wac_per_unit=position.wac, ...)). V1's book: B's 4 X
    are costed at their leg's own cost basis, 16 EUR a unit — not A's 10, which the viewer cannot see — (the
    average-cost pool costs a TRANSFER-in at its cost_basis_override, financial_math/average_cost.py), and the dividend
    of 8 EUR yields 8 / 4 / 16 = 0.125 on them.

    Today: WAC 16 already; YoC unavailable, REPLAY_INCONSISTENT, no value — V1's failed replay.
    After: WAC 16; YoC available, 0.125.
    """
    book = await _arrival_book(session, viewer="receiver")
    await _add_income(session, book, broker_id=book.receiver_broker_id, on=J51_INCOME_DAY, amount="8")

    holding = await _dashboard_holding_at_b(session, book)

    assert _holding_view(holding) == {
        "quantity": Decimal("4"),
        "wac_per_unit": J51_ARRIVAL_COST_BASIS,
        "yield_on_cost": {"status": YieldOnCostStatus.AVAILABLE, "value": Decimal("0.125"), "reason": None},
    }


@pytest.mark.parametrize(
    ("own_purchase", "held"),
    [
        pytest.param(False, Decimal("4"), id="the-arrival-alone"),
        pytest.param(True, Decimal("10"), id="beside-a-purchase-of-6-at-B"),
    ],
)
@pytest.mark.asyncio
async def test_guard_dashboard_never_yields_over_the_cost_a_costless_arrival_leaves_unknown(session, own_purchase, held):
    """J-51 GUARD (green today and after), through the real Dashboard path: a costless arrival never gets a yield over a
    partial or zero cost. V1's book, but B's leg carries no cost basis (old data). The average-cost pool adds its 4 X at
    an unknown cost (financial_math/average_cost.py, ADD_UNKNOWN_COST) and stays incomplete while they are held, so B has
    no WAC (DailyStateBuilder._build_position_state) — alone, and beside B's own purchase of 6 X for 72 EUR on
    3 Jun 2024, whose cost covers only 6 of the 10. Without a WAC, YoC is unavailable, MISSING_WAC, with no value: no
    yield over a zero cost for the 4, nor over an average that knows the cost of the 6 only. The fix reads that arrival
    as a costless ADJUSTMENT-in — MISSING_COST_BASIS, a DEGRADED replay, not a FAILED one —: the missing WAC alone must
    keep the yield away.
    """
    book = await _arrival_book(session, viewer="receiver", arrival_cost_basis=None)
    if own_purchase:
        session.add(_transaction(book.ledger, TransactionType.BUY, on=date(2024, 6, 3), quantity="6", amount="-72", broker_id=book.receiver_broker_id))
    await _add_income(session, book, broker_id=book.receiver_broker_id, on=J51_INCOME_DAY, amount="8")

    holding = await _dashboard_holding_at_b(session, book)

    assert _holding_view(holding) == {
        "quantity": held,
        "wac_per_unit": None,
        "yield_on_cost": {"status": YieldOnCostStatus.UNAVAILABLE, "value": None, "reason": YieldOnCostUnavailableReason.MISSING_WAC},
    }
