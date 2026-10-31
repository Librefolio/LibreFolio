"""
W6-12 — the batch balance validator walks the cash through the single home of cash maths, and a broker without the
overdraft flag may never hold a negative cash, not even the opening one (developer, 30/10/2026).

Module under test: ``backend/app/services/transactions/balances.py`` —
``TransactionBalancesMixin._validate_broker_balances(broker_id, from_date=None, batch_tx_ids=None)``, reached through
``TransactionService``. Its cash walk becomes ``native_cash.first_negative_cash`` over the movements of
``cash_movement_from_transaction`` (opening = the balances before ``from_date``, ``check_days = (from_date,)``); the
quantity walk stays; the error raised is the one of the LOWEST day between the cash hit and the asset hit, the CASH one
on a tie; every field, message, code and param of the errors stays identical.

THE RULE THAT CHANGES. Today ``if not txs: return`` ends the replay when no transaction is dated on or after
``from_date``, so the opening balance (the one before ``from_date``) is never checked. After W6-12 a broker WITHOUT
``allow_cash_overdraft`` refuses a negative opening cash on ``from_date`` even then. Example (the developer's): cash
-100 USD since 10/10, the only transaction of 15/10 deleted by the batch, validation from 15/10 -> today it passes, it
must be refused. With the overdraft flag set nothing changes; the asset path keeps today's behaviour (nothing to walk
without transactions).

Reds — fail today, pass after W6-12:

- ``TestOpeningCashWithNoTransactionsFromTheDate`` (without the flag): the refusals. Red reason: ``DID NOT RAISE
  BalanceValidationError`` (the early ``return``).
- ``TestDifferentialAgainstTheFrozenWalk::test_the_documented_difference_is_refused_on_the_from_date``: the seeded random
  ledgers of the documented difference are refused on ``from_date``; red today (the service accepts them).

Guards — green today and after:

- ``TestDifferentialAgainstTheFrozenWalk::test_everything_but_the_documented_difference_matches_the_frozen_walk``: every
  other seeded random ledger has exactly the frozen walk's outcome;
- the same cases with one later transaction that keeps the cash negative (red on ``from_date``), with the overdraft
  flag set, with the opening at exactly zero, or healed on ``from_date`` itself;
- a first movement that takes the cash below zero: code, day, currency, balance, params and the batch index;
- a same-day deposit and payment: no red in between; several currencies the same day: the first red in ``opening``'s
  order, then the walk's;
- cash against assets: the lowest day wins, a tie goes to the cash, and the flag combinations;
- the batch index: the last batch transaction that reduced that currency that day, else ``("create", -1)``;
- ``ledgerUnreadable`` (also when it meets the new rule), an unknown broker, a broker that allows both.

``TestDifferentialAgainstTheFrozenWalk`` keeps in this file a FROZEN COPY of today's walk
(``frozen_validate_broker_balances``) over plain in-memory rows, and compares the outcome of the service
(``None`` or code, day, currency-or-asset, balance, batch index and operation, message and params) over a few hundred
seeded random ledgers. The copy is deliberately independent of the code under test: it does not call
``native_cash``.

Private in-memory SQLite with the ORM schema (``create_all``), disposed at teardown: no lane database, no server, no
network.
"""

from __future__ import annotations

import random
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetType, Broker, Transaction, TransactionType
from backend.app.schemas.transactions.batch import TXValidationCode
from backend.app.services.transactions.transaction_batch_context import BalanceValidationError
from backend.app.services.transactions.transaction_service import TransactionService
from backend.app.utils.datetime_utils import utcnow

CASH_NEGATIVE = TXValidationCode.BALANCE_CASH_NEGATIVE.value
ASSET_NEGATIVE = TXValidationCode.BALANCE_ASSET_NEGATIVE.value
LEDGER_UNREADABLE = TXValidationCode.LEDGER_UNREADABLE.value

EUR, USD, GBP = "EUR", "USD", "GBP"
D1 = date(2026, 10, 1)
D10 = date(2026, 10, 10)
D15 = date(2026, 10, 15)

#: What the service answered: ``None`` when it accepted, else the fields of its ``BalanceValidationError``.
Outcome = Optional[tuple]


def day(n: int) -> date:
    """Day ``n`` of a month of the test's own (2026-11): small numbers, same-day collisions easy to write."""
    return date(2026, 11, 1) + timedelta(days=n - 1)


# =============================================================================
# FIXTURES AND ROWS
# =============================================================================


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """This test's own in-memory database with the ORM schema: never the lane's database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as private_session:
            yield private_session
    finally:
        await engine.dispose()


async def new_broker(session: AsyncSession, *, overdraft: bool = False, shorting: bool = False) -> int:
    broker = Broker(name=f"W6-12 {uuid.uuid4().hex}", description="W6-12 cash rule", allow_cash_overdraft=overdraft, allow_asset_shorting=shorting, created_at=utcnow(), updated_at=utcnow())
    session.add(broker)
    await session.flush()
    return broker.id


async def new_asset(session: AsyncSession) -> int:
    asset = Asset(display_name=f"W6-12 asset {uuid.uuid4().hex}", asset_type=AssetType.STOCK, currency=EUR, created_at=utcnow(), updated_at=utcnow())
    session.add(asset)
    await session.flush()
    return asset.id


async def put(
    session: AsyncSession,
    broker_id: int,
    tx_type: TransactionType,
    on: date,
    *,
    amount: str = "0",
    currency: Optional[str] = None,
    asset_id: Optional[int] = None,
    quantity: str = "0",
) -> int:
    """A row written straight into the session, past the batch and its replay: what an older version, or a deletion, leaves. Its id."""
    row = Transaction(broker_id=broker_id, asset_id=asset_id, type=tx_type, date=on, quantity=Decimal(quantity), amount=Decimal(amount), currency=currency, created_at=utcnow(), updated_at=utcnow())
    session.add(row)
    await session.flush()
    return row.id


async def cash(session: AsyncSession, broker_id: int, on: date, amount: str, currency: str = EUR) -> int:
    """A DEPOSIT (amount > 0) or a WITHDRAWAL (amount < 0). Its id."""
    tx_type = TransactionType.DEPOSIT if Decimal(amount) > 0 else TransactionType.WITHDRAWAL
    return await put(session, broker_id, tx_type, on, amount=amount, currency=currency)


async def validate(session: AsyncSession, broker_id: int, from_date: Optional[date] = None, batch: Optional[dict[int, tuple]] = None) -> Outcome:
    """The outcome of the validator: ``None`` when it accepts, else (code, day, currency-or-asset, balance, batch index, batch operation, message, params)."""
    try:
        await TransactionService(session)._validate_broker_balances(broker_id, from_date, batch)
    except BalanceValidationError as error:
        return (error.code, error.date, error.currency_or_asset, error.balance, error.batch_index, error.batch_operation, str(error), error.params)
    return None


def cash_refusal(broker_id: int, on: date, currency: str, balance: str, index: int = -1, operation: str = "create") -> tuple:
    """The outcome of a refused cash balance, message and params included: they must not change."""
    balance_d = Decimal(balance)
    return (
        CASH_NEGATIVE,
        on,
        currency,
        balance_d,
        index,
        operation,
        f"Cash balance for {currency} goes negative ({balance_d}) on {on} for broker {broker_id}",
        {"brokerId": broker_id, "currency": currency, "balance": str(balance_d), "date": str(on)},
    )


def asset_refusal(broker_id: int, on: date, asset_id: int, balance: str, index: int = -1, operation: str = "create") -> tuple:
    balance_d = Decimal(balance)
    return (
        ASSET_NEGATIVE,
        on,
        f"asset:{asset_id}",
        balance_d,
        index,
        operation,
        f"Asset {asset_id} quantity goes negative ({balance_d}) on {on} for broker {broker_id}",
        {"brokerId": broker_id, "assetId": asset_id, "balance": str(balance_d), "date": str(on)},
    )


def same_outcome(got: Outcome, want: Outcome) -> bool:
    """Equal, the figures by value: ``Decimal('-100')`` and ``Decimal('-100.000000')`` are the same balance, in the field,
    the message and the params alike; everything else (code, day, name, batch index and operation, wording) as written."""
    if got is None or want is None:
        return got is want
    return got[:3] == want[:3] and got[3] == want[3] and got[4:6] == want[4:6] and _normalised(got[6], got[7]) == _normalised(want[6], want[7])


def _normalised(message: str, params: dict) -> tuple:
    """The message and params with the balance as a number: a Decimal's trailing zeros are a notation, not a figure."""
    head, _, tail = message.partition("(")
    figure, _, rest = tail.partition(")")
    shown = f"{head}({format(Decimal(figure).normalize(), 'f')}){rest}" if figure else message
    shaped = {key: (Decimal(value) if key == "balance" else value) for key, value in params.items()}
    return shown, shaped


def assert_outcome(got: Outcome, want: Outcome, why: str = "") -> None:
    assert same_outcome(got, want), f"{why}\n  got:  {got}\n  want: {want}"


async def make_unreadable(session: AsyncSession, row_id: int, column: str = "amount") -> None:
    """Overwrite ``column`` of the row by raw SQL with 'n/a': ``RealDecimal`` reads it back as None (W-B58)."""
    await session.execute(text(f"UPDATE transactions SET {column} = 'n/a' WHERE id = :id"), {"id": row_id})
    session.expire_all()


# =============================================================================
# THE RULE THAT CHANGES: THE OPENING CASH WITH NO TRANSACTION FROM THE DATE ON
# =============================================================================


class TestOpeningCashWithNoTransactionsFromTheDate:
    """RED today (``DID NOT RAISE``): a broker without the overdraft flag may never have a negative cash, not even the opening one."""

    @pytest.mark.asyncio
    async def test_the_developers_example_the_only_transaction_of_the_date_is_deleted(self, session):
        """Cash -100 USD since 10/10; a DEPOSIT of 15/10 is the only transaction from then on and the batch deletes it
        (it is gone from the session when the replay runs): validation from 15/10 must refuse, on 15/10, -100 USD."""
        broker_id = await new_broker(session)
        await put(session, broker_id, TransactionType.WITHDRAWAL, D10, amount="-100", currency=USD)
        deposit_id = await put(session, broker_id, TransactionType.DEPOSIT, D15, amount="100", currency=USD)
        # the batch deletes the 15/10 deposit
        await session.delete(await session.get(Transaction, deposit_id))
        await session.flush()

        outcome = await validate(session, broker_id, D15)

        assert_outcome(outcome, cash_refusal(broker_id, D15, USD, "-100"), "an opening of -100 USD, nothing dated from 15/10 on, no overdraft flag: refused on the from_date")

    @pytest.mark.asyncio
    async def test_a_negative_opening_and_nothing_after_it_is_refused(self, session):
        broker_id = await new_broker(session)
        await cash(session, broker_id, D1, "50")
        await cash(session, broker_id, D10, "-150")  # EUR -100 since 10/10

        outcome = await validate(session, broker_id, D15)

        assert_outcome(outcome, cash_refusal(broker_id, D15, EUR, "-100"), "the opening cash (before 15/10) is -100 EUR")

    @pytest.mark.asyncio
    async def test_the_batch_index_of_such_a_refusal_is_create_minus_one(self, session):
        """No transaction is dated on ``from_date``, so none reduced the cash that day: the ids of the batch (a stored
        row among them) change nothing."""
        broker_id = await new_broker(session)
        stored = await cash(session, broker_id, D10, "-100")

        outcome = await validate(session, broker_id, D15, batch={stored: ("update", 4), 999_999: ("create", 2)})

        assert_outcome(outcome, cash_refusal(broker_id, D15, EUR, "-100", -1, "create"), "no reducer on the from_date: ('create', -1)")

    @pytest.mark.asyncio
    async def test_the_negative_currency_is_named_among_positive_ones(self, session):
        broker_id = await new_broker(session)
        await cash(session, broker_id, D1, "80", EUR)
        await cash(session, broker_id, D1, "-20", USD)
        await cash(session, broker_id, D1, "5", GBP)

        outcome = await validate(session, broker_id, D15)

        assert_outcome(outcome, cash_refusal(broker_id, D15, USD, "-20"), "USD is the only currency below zero")

    @pytest.mark.asyncio
    async def test_a_negative_opening_with_a_later_movement_of_another_currency_is_refused_on_the_from_date(self, session):
        """A later transaction exists (so today the walk runs), but only in another currency: the refusal is on ``from_date``."""
        broker_id = await new_broker(session)
        await cash(session, broker_id, D10, "-100", USD)
        await cash(session, broker_id, day(20), "30", EUR)

        outcome = await validate(session, broker_id, D15)

        assert_outcome(outcome, cash_refusal(broker_id, D15, USD, "-100"), "the walk starts on from_date with the opening: USD -100")


class TestOpeningCashWithLaterTransactions:
    """Guards, green today: the walk runs when a transaction is dated from ``from_date`` on, and the cure must keep it."""

    @pytest.mark.asyncio
    async def test_a_later_movement_that_keeps_the_cash_negative_is_refused_on_the_from_date(self, session):
        broker_id = await new_broker(session)
        await cash(session, broker_id, D10, "-100")
        await cash(session, broker_id, day(20), "-10")  # after the from_date

        outcome = await validate(session, broker_id, D15)

        assert_outcome(outcome, cash_refusal(broker_id, D15, EUR, "-100"), "the first red day is the from_date, with the opening balance, not the later movement's day")

    @pytest.mark.asyncio
    async def test_a_movement_on_the_from_date_that_keeps_it_negative_is_refused_with_the_end_of_day_balance(self, session):
        broker_id = await new_broker(session)
        await cash(session, broker_id, D10, "-100")
        later = await cash(session, broker_id, D15, "-10")

        outcome = await validate(session, broker_id, D15, batch={later: ("create", 0)})

        assert_outcome(outcome, cash_refusal(broker_id, D15, EUR, "-110", 0, "create"), "the red is the end of the from_date: -100 and the batch's -10")

    @pytest.mark.asyncio
    async def test_a_deposit_on_the_from_date_that_heals_the_opening_is_accepted(self, session):
        broker_id = await new_broker(session)
        await cash(session, broker_id, D10, "-100")
        await cash(session, broker_id, D15, "100")  # end of D15: 0

        assert await validate(session, broker_id, D15) is None

    @pytest.mark.asyncio
    async def test_a_deposit_after_the_from_date_does_not_heal_the_from_date(self, session):
        broker_id = await new_broker(session)
        await cash(session, broker_id, D10, "-100")
        await cash(session, broker_id, day(20), "500")

        outcome = await validate(session, broker_id, D15)

        assert_outcome(outcome, cash_refusal(broker_id, D15, EUR, "-100"), "the cash is below zero at the end of the from_date, whatever comes later")

    @pytest.mark.asyncio
    async def test_an_opening_of_exactly_zero_is_not_negative(self, session):
        broker_id = await new_broker(session)
        await cash(session, broker_id, D1, "100")
        await cash(session, broker_id, D10, "-100")

        assert await validate(session, broker_id, D15) is None, "zero is not below zero (no transaction from the date on)"

    @pytest.mark.asyncio
    async def test_a_broker_without_transactions_is_accepted(self, session):
        broker_id = await new_broker(session)

        assert await validate(session, broker_id, D15) is None
        assert await validate(session, broker_id, None) is None


class TestTheOverdraftFlagLeavesItAlone:
    """Guards, green today: with ``allow_cash_overdraft`` the cash is never checked, the opening one included."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shorting", [False, True])
    async def test_a_negative_opening_with_no_transactions_from_the_date_is_accepted(self, session, shorting):
        broker_id = await new_broker(session, overdraft=True, shorting=shorting)
        await cash(session, broker_id, D10, "-100")

        assert await validate(session, broker_id, D15) is None

    @pytest.mark.asyncio
    async def test_a_negative_opening_with_later_transactions_is_accepted(self, session):
        broker_id = await new_broker(session, overdraft=True)
        await cash(session, broker_id, D10, "-100")
        await cash(session, broker_id, D15, "-10")
        await cash(session, broker_id, day(20), "-10")

        assert await validate(session, broker_id, D15) is None
        assert await validate(session, broker_id, None) is None

    @pytest.mark.asyncio
    async def test_the_asset_path_with_no_transactions_from_the_date_keeps_its_behaviour(self, session):
        """The quantity walk is untouched: a negative opening QUANTITY with nothing to walk from ``from_date`` is not
        looked at (today ``return``), cash flag set or not."""
        asset_id = await new_asset(session)
        broker_id = await new_broker(session, overdraft=True, shorting=False)
        await put(session, broker_id, TransactionType.ADJUSTMENT, D10, asset_id=asset_id, quantity="-3")

        assert await validate(session, broker_id, D15) is None, "an asset short since 10/10 and nothing dated from 15/10 on: not walked, accepted"


# =============================================================================
# A FIRST MOVEMENT BELOW ZERO: THE FIELDS OF THE ERROR
# =============================================================================


class TestAFirstMovementBelowZero:
    """Guards, green today: a movement that takes the cash below zero is refused with the right code, day, currency, balance, params and batch index."""

    @pytest.mark.asyncio
    async def test_the_fields_of_the_cash_error(self, session):
        broker_id = await new_broker(session)
        await cash(session, broker_id, day(3), "-30", USD)

        assert_outcome(await validate(session, broker_id), cash_refusal(broker_id, day(3), USD, "-30"), "no batch: ('create', -1)")

    @pytest.mark.asyncio
    async def test_the_batch_transaction_that_made_it_negative_is_named(self, session):
        broker_id = await new_broker(session)
        await cash(session, broker_id, day(1), "100")
        stored_before = await cash(session, broker_id, day(2), "-20")
        reducer = await cash(session, broker_id, day(3), "-90")

        outcome = await validate(session, broker_id, None, batch={reducer: ("update", 3), stored_before: ("create", 0)})

        assert_outcome(outcome, cash_refusal(broker_id, day(3), EUR, "-10", 3, "update"), "the -90 of 03 is the batch transaction that reduced EUR on the day the cash went negative")

    @pytest.mark.asyncio
    async def test_the_last_batch_reducer_of_the_day_wins(self, session):
        broker_id = await new_broker(session)
        first = await cash(session, broker_id, day(3), "-40")
        second = await cash(session, broker_id, day(3), "-40")
        not_in_batch = await cash(session, broker_id, day(3), "-5")  # the last reducer by (date, id), but not the batch's
        assert first < second < not_in_batch

        outcome = await validate(session, broker_id, None, batch={first: ("create", 1), second: ("update", 7)})

        assert_outcome(outcome, cash_refusal(broker_id, day(3), EUR, "-85", 7, "update"), "the last of the batch's reducers in (date, id) order; the later one that is not in the batch does not steal it")

    @pytest.mark.asyncio
    async def test_a_batch_deposit_is_not_a_reducer(self, session):
        broker_id = await new_broker(session)
        deposit = await cash(session, broker_id, day(3), "10")
        await cash(session, broker_id, day(3), "-30")

        outcome = await validate(session, broker_id, None, batch={deposit: ("create", 0)})

        assert_outcome(outcome, cash_refusal(broker_id, day(3), EUR, "-20", -1, "create"), "the only batch transaction raised the cash: no batch reducer of EUR")

    @pytest.mark.asyncio
    async def test_a_batch_reducer_of_another_currency_or_another_day_is_ignored(self, session):
        broker_id = await new_broker(session)
        other_currency = await cash(session, broker_id, day(3), "-5", USD)
        await cash(session, broker_id, day(1), "20", USD)  # keeps the USD at +15
        other_day = await cash(session, broker_id, day(2), "-5", EUR)
        await cash(session, broker_id, day(2), "50", EUR)  # EUR +45 after 02
        await cash(session, broker_id, day(4), "-60", EUR)  # EUR -15 on 04, not a batch transaction

        outcome = await validate(session, broker_id, None, batch={other_currency: ("create", 0), other_day: ("update", 1)})

        assert_outcome(outcome, cash_refusal(broker_id, day(4), EUR, "-15", -1, "create"), "neither a USD reducer of 03 nor an EUR reducer of 02 is the reducer of EUR on 04")

    @pytest.mark.asyncio
    async def test_with_a_from_date_the_first_movement_on_it_is_named(self, session):
        broker_id = await new_broker(session)
        await cash(session, broker_id, day(1), "10")
        reducer = await cash(session, broker_id, day(5), "-25")

        outcome = await validate(session, broker_id, day(5), batch={reducer: ("create", 2)})

        assert_outcome(outcome, cash_refusal(broker_id, day(5), EUR, "-15", 2, "create"), "opening +10, the batch's -25 on the from_date")


# =============================================================================
# SAME DAY: END-OF-DAY BALANCE, SEVERAL CURRENCIES
# =============================================================================


class TestSameDay:
    @pytest.mark.asyncio
    async def test_a_payment_stored_before_the_deposit_of_the_same_day_is_no_red(self, session):
        """Guard: the check is at the end of the day, whatever the order inside it."""
        broker_id = await new_broker(session)
        await cash(session, broker_id, day(3), "-80")  # the payment has the lower id
        await cash(session, broker_id, day(3), "100")

        assert await validate(session, broker_id) is None
        assert await validate(session, broker_id, day(3)) is None

    @pytest.mark.asyncio
    async def test_a_payment_that_the_same_days_deposit_does_not_cover_is_refused_at_the_end_of_the_day(self, session):
        broker_id = await new_broker(session)
        await cash(session, broker_id, day(3), "50")
        payment = await cash(session, broker_id, day(3), "-80")

        outcome = await validate(session, broker_id, None, batch={payment: ("create", 1)})

        assert_outcome(outcome, cash_refusal(broker_id, day(3), EUR, "-30", 1, "create"), "the balance of the end of the day, -30")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("first_stored", [EUR, USD])
    async def test_several_currencies_below_zero_the_same_day_the_walks_order_decides(self, session, first_stored):
        """No opening: the first currency met in the day's rows (id order) is the one named. Compared with the frozen walk."""
        broker_id = await new_broker(session)
        second = USD if first_stored == EUR else EUR
        await cash(session, broker_id, day(3), "-5", first_stored)
        await cash(session, broker_id, day(3), "-7", second)

        outcome = await validate(session, broker_id)

        assert_outcome(outcome, cash_refusal(broker_id, day(3), first_stored, "-5"), f"{first_stored} met first")
        assert_outcome(outcome, await frozen_on_db(session, broker_id, None, None), "the frozen walk says the same")

    @pytest.mark.asyncio
    async def test_several_currencies_below_zero_the_same_day_the_openings_order_comes_first(self, session):
        """USD is the first currency of the opening, EUR the first of the day: both end the day below zero, USD is named."""
        broker_id = await new_broker(session)
        await cash(session, broker_id, day(1), "10", USD)
        await cash(session, broker_id, day(1), "10", EUR)
        await cash(session, broker_id, day(3), "-20", EUR)  # EUR first in the day's rows
        await cash(session, broker_id, day(3), "-20", USD)

        outcome = await validate(session, broker_id, day(3))

        assert_outcome(outcome, cash_refusal(broker_id, day(3), USD, "-10"), "opening's order (USD, EUR), then the walk's")
        assert_outcome(outcome, await frozen_on_db(session, broker_id, day(3), None), "the frozen walk says the same")

    @pytest.mark.asyncio
    async def test_a_currency_that_first_appears_in_the_walk_comes_after_the_openings_ones(self, session):
        broker_id = await new_broker(session)
        await cash(session, broker_id, day(1), "10", USD)
        await cash(session, broker_id, day(3), "-20", GBP)  # new in the walk, listed first in the day
        await cash(session, broker_id, day(3), "-20", USD)

        outcome = await validate(session, broker_id, day(3))

        assert_outcome(outcome, cash_refusal(broker_id, day(3), USD, "-10"), "USD is in the opening dict, GBP is added after it")
        assert_outcome(outcome, await frozen_on_db(session, broker_id, day(3), None), "the frozen walk says the same")


# =============================================================================
# CASH AGAINST ASSETS
# =============================================================================


class TestCashAgainstAssets:
    """Guards: the lowest day wins, a tie goes to the cash, and the flags choose what is checked."""

    @pytest.mark.asyncio
    async def test_the_asset_goes_negative_first(self, session):
        asset_id = await new_asset(session)
        broker_id = await new_broker(session)
        await put(session, broker_id, TransactionType.ADJUSTMENT, day(3), asset_id=asset_id, quantity="-1")
        await cash(session, broker_id, day(5), "-10")

        assert_outcome(await validate(session, broker_id), asset_refusal(broker_id, day(3), asset_id, "-1"), "03 < 05: the asset error")

    @pytest.mark.asyncio
    async def test_the_cash_goes_negative_first(self, session):
        asset_id = await new_asset(session)
        broker_id = await new_broker(session)
        await cash(session, broker_id, day(3), "-10")
        await put(session, broker_id, TransactionType.ADJUSTMENT, day(5), asset_id=asset_id, quantity="-1")

        assert_outcome(await validate(session, broker_id), cash_refusal(broker_id, day(3), EUR, "-10"), "03 < 05: the cash error")

    @pytest.mark.asyncio
    async def test_on_the_same_day_the_cash_error_wins(self, session):
        asset_id = await new_asset(session)
        broker_id = await new_broker(session)
        await put(session, broker_id, TransactionType.ADJUSTMENT, day(3), asset_id=asset_id, quantity="-1")  # stored first
        await cash(session, broker_id, day(3), "-10")

        assert_outcome(await validate(session, broker_id), cash_refusal(broker_id, day(3), EUR, "-10"), "a tie goes to the cash")

    @pytest.mark.asyncio
    async def test_overdraft_allowed_shorting_not_only_the_asset_is_checked(self, session):
        asset_id = await new_asset(session)
        broker_id = await new_broker(session, overdraft=True, shorting=False)
        await cash(session, broker_id, day(2), "-10")  # earlier, and invisible
        await put(session, broker_id, TransactionType.ADJUSTMENT, day(5), asset_id=asset_id, quantity="-1")

        assert_outcome(await validate(session, broker_id), asset_refusal(broker_id, day(5), asset_id, "-1"), "the earlier cash red is not looked at")

    @pytest.mark.asyncio
    async def test_shorting_allowed_overdraft_not_only_the_cash_is_checked(self, session):
        asset_id = await new_asset(session)
        broker_id = await new_broker(session, overdraft=False, shorting=True)
        await put(session, broker_id, TransactionType.ADJUSTMENT, day(2), asset_id=asset_id, quantity="-1")  # earlier, and invisible
        await cash(session, broker_id, day(5), "-10")

        assert_outcome(await validate(session, broker_id), cash_refusal(broker_id, day(5), EUR, "-10"), "the earlier asset red is not looked at")

    @pytest.mark.asyncio
    async def test_the_asset_reducer_of_the_batch_is_named(self, session):
        asset_id = await new_asset(session)
        broker_id = await new_broker(session)
        await put(session, broker_id, TransactionType.ADJUSTMENT, day(1), asset_id=asset_id, quantity="2")
        reducer = await put(session, broker_id, TransactionType.ADJUSTMENT, day(2), asset_id=asset_id, quantity="-5")

        outcome = await validate(session, broker_id, None, batch={reducer: ("update", 6)})

        assert_outcome(outcome, asset_refusal(broker_id, day(2), asset_id, "-3", 6, "update"), "the asset error names the batch transaction that reduced the quantity")

    @pytest.mark.asyncio
    async def test_a_cash_red_from_the_opening_is_found_before_a_later_asset_red(self, session):
        """With the new rule: the opening cash (red on ``from_date``) is earlier than an asset red two days later."""
        asset_id = await new_asset(session)
        broker_id = await new_broker(session)
        await cash(session, broker_id, day(1), "-10")
        await put(session, broker_id, TransactionType.ADJUSTMENT, day(8), asset_id=asset_id, quantity="-1")

        outcome = await validate(session, broker_id, day(5))

        assert_outcome(outcome, cash_refusal(broker_id, day(5), EUR, "-10"), "the check day is the from_date: the cash is red there, before the asset on 08")


# =============================================================================
# THE EARLY RETURNS AND THE UNREADABLE LEDGER
# =============================================================================


class TestEarlyReturnsAndUnreadableRows:
    """Guards, green today."""

    @pytest.mark.asyncio
    async def test_an_unknown_broker_is_accepted(self, session):
        assert await validate(session, 987_654_321, day(3)) is None
        assert await validate(session, 987_654_321) is None

    @pytest.mark.asyncio
    async def test_a_broker_that_allows_both_is_accepted_whatever_it_holds(self, session):
        asset_id = await new_asset(session)
        broker_id = await new_broker(session, overdraft=True, shorting=True)
        await cash(session, broker_id, day(1), "-500")
        await put(session, broker_id, TransactionType.ADJUSTMENT, day(2), asset_id=asset_id, quantity="-9")
        unreadable = await cash(session, broker_id, day(3), "-1")
        await make_unreadable(session, unreadable)

        assert await validate(session, broker_id, day(3)) is None, "the early return comes before the unreadable-rows check"
        assert await validate(session, broker_id) is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("from_date", [None, day(3)])
    async def test_an_unreadable_row_refuses_the_replay_with_its_code(self, session, from_date):
        broker_id = await new_broker(session)
        await cash(session, broker_id, day(1), "50")
        unreadable = await cash(session, broker_id, day(2), "-100")
        await make_unreadable(session, unreadable)

        outcome = await validate(session, broker_id, from_date)

        assert outcome is not None, "an unreadable row must refuse the replay"
        assert outcome[0] == LEDGER_UNREADABLE
        assert outcome[1] == (from_date if from_date is not None else date.min)
        assert outcome[2] == ""
        assert outcome[3] == Decimal("0")
        assert outcome[4:6] == (-1, "create")
        assert outcome[7] == {"brokerId": broker_id, "count": 1}

    @pytest.mark.asyncio
    async def test_the_unreadable_row_wins_over_the_new_rule_and_over_a_negative_opening(self, session):
        """Opening negative, nothing dated from ``from_date`` on, and an unreadable row before it: ``ledgerUnreadable``, not a cash error."""
        broker_id = await new_broker(session)
        await cash(session, broker_id, day(1), "-100")
        unreadable = await cash(session, broker_id, day(2), "-1")
        await make_unreadable(session, unreadable)

        outcome = await validate(session, broker_id, day(9))

        assert outcome is not None and outcome[0] == LEDGER_UNREADABLE
        assert outcome[1] == day(9)

    @pytest.mark.asyncio
    async def test_an_unreadable_row_refuses_even_with_the_overdraft_flag(self, session):
        broker_id = await new_broker(session, overdraft=True, shorting=False)
        unreadable = await cash(session, broker_id, day(2), "-1")
        await make_unreadable(session, unreadable)

        outcome = await validate(session, broker_id, day(3))

        assert outcome is not None and outcome[0] == LEDGER_UNREADABLE


# =============================================================================
# THE FROZEN COPY OF TODAY'S WALK, AND THE DIFFERENTIAL
# =============================================================================


@dataclass(frozen=True)
class Row:
    """A transaction as plain data: what the walk reads."""

    id: int
    date: date
    amount: Decimal
    currency: Optional[str]
    asset_id: Optional[int]
    quantity: Decimal


def frozen_validate_broker_balances(  # noqa: C901 — a verbatim copy of the walk it freezes
    *,
    broker_id: int,
    overdraft: bool,
    shorting: bool,
    rows: list[Row],
    from_date: Optional[date],
    batch: Optional[dict[int, tuple]],
) -> Outcome:
    """FROZEN COPY of ``_validate_broker_balances`` as it is before W6-12, over plain rows (unreadable ledgers aside):
    the outcome the walk had, ``None`` or (code, day, currency-or-asset, balance, batch index, batch operation, message,
    params). Do not edit it to follow the product: the differential exists to compare with THIS."""
    if overdraft and shorting:
        return None

    ordered = sorted(rows, key=lambda r: (r.date, r.id))
    cash_balances: dict[str, Decimal] = {}
    asset_balances: dict[int, Decimal] = {}
    if from_date is None:
        txs = ordered
    else:
        # the balances at the end of the day before from_date, as _get_balances_before_date built them: a currency with
        # rows keeps its line even at zero; an asset line needs a non-zero quantity
        for r in ordered:
            if r.date < from_date:
                if r.currency:
                    cash_balances[r.currency] = cash_balances.get(r.currency, Decimal("0")) + r.amount
                if r.asset_id is not None and r.quantity:
                    asset_balances[r.asset_id] = asset_balances.get(r.asset_id, Decimal("0")) + r.quantity
        txs = [r for r in ordered if r.date >= from_date]

    if not txs:
        return None

    _batch = batch or {}
    txs_by_date: dict[date, list[Row]] = {}
    for tx in txs:
        txs_by_date.setdefault(tx.date, []).append(tx)
    days = sorted(set(txs_by_date) | ({from_date} if from_date is not None else set()))

    for current_date in days:
        last_cash_reducer: dict[str, tuple] = {}
        last_asset_reducer: dict[int, tuple] = {}
        for tx in txs_by_date.get(current_date, []):
            if tx.amount != Decimal("0") and tx.currency:
                cash_balances[tx.currency] = cash_balances.get(tx.currency, Decimal("0")) + tx.amount
                if tx.amount < Decimal("0") and tx.id in _batch:
                    last_cash_reducer[tx.currency] = _batch[tx.id]
            if tx.quantity != Decimal("0") and tx.asset_id:
                asset_balances[tx.asset_id] = asset_balances.get(tx.asset_id, Decimal("0")) + tx.quantity
                if tx.quantity < Decimal("0") and tx.id in _batch:
                    last_asset_reducer[tx.asset_id] = _batch[tx.id]

        if not overdraft:
            for currency, balance in cash_balances.items():
                if balance < Decimal("0"):
                    b_op, b_idx = last_cash_reducer.get(currency, ("create", -1))
                    return (
                        CASH_NEGATIVE,
                        current_date,
                        currency,
                        balance,
                        b_idx,
                        b_op,
                        f"Cash balance for {currency} goes negative ({balance}) on {current_date} for broker {broker_id}",
                        {"brokerId": broker_id, "currency": currency, "balance": str(balance), "date": str(current_date)},
                    )

        if not shorting:
            for asset_id, balance in asset_balances.items():
                if balance < Decimal("0"):
                    b_op, b_idx = last_asset_reducer.get(asset_id, ("create", -1))
                    return (
                        ASSET_NEGATIVE,
                        current_date,
                        f"asset:{asset_id}",
                        balance,
                        b_idx,
                        b_op,
                        f"Asset {asset_id} quantity goes negative ({balance}) on {current_date} for broker {broker_id}",
                        {"brokerId": broker_id, "assetId": asset_id, "balance": str(balance), "date": str(current_date)},
                    )
    return None


def opening_cash_is_negative(rows: list[Row], from_date: date) -> Optional[tuple[str, Decimal]]:
    """The first currency, in the opening's order ((date, id) of the rows before ``from_date``), whose cash before ``from_date`` is below zero."""
    balances: dict[str, Decimal] = {}
    for r in sorted(rows, key=lambda r: (r.date, r.id)):
        if r.date < from_date and r.currency:
            balances[r.currency] = balances.get(r.currency, Decimal("0")) + r.amount
    return next(((currency, balance) for currency, balance in balances.items() if balance < 0), None)


def is_the_documented_difference(*, overdraft: bool, rows: list[Row], from_date: Optional[date]) -> bool:
    """No transaction dated on or after ``from_date``, no overdraft flag, and a negative opening cash: the one case W6-12 changes."""
    return from_date is not None and not overdraft and not any(r.date >= from_date for r in rows) and opening_cash_is_negative(rows, from_date) is not None


def expected_after_w6_12(*, broker_id: int, overdraft: bool, shorting: bool, rows: list[Row], from_date: Optional[date], batch: Optional[dict[int, tuple]]) -> Outcome:
    """The frozen walk's outcome, but for the documented difference, where the opening cash is refused on ``from_date``."""
    if overdraft and shorting:
        return None
    if is_the_documented_difference(overdraft=overdraft, rows=rows, from_date=from_date):
        currency, balance = opening_cash_is_negative(rows, from_date)  # type: ignore[arg-type,misc]
        return cash_refusal(broker_id, from_date, currency, str(balance))  # type: ignore[arg-type]
    return frozen_validate_broker_balances(broker_id=broker_id, overdraft=overdraft, shorting=shorting, rows=rows, from_date=from_date, batch=batch)


async def load_rows(session: AsyncSession, broker_id: int) -> list[Row]:
    """The broker's rows as the database holds them (re-read, so the figures are the stored decimals)."""
    result = await session.execute(select(Transaction).where(Transaction.broker_id == broker_id).execution_options(populate_existing=True))
    return [Row(id=t.id, date=t.date, amount=t.amount, currency=t.currency, asset_id=t.asset_id, quantity=t.quantity) for t in result.scalars().all()]


async def frozen_on_db(session: AsyncSession, broker_id: int, from_date: Optional[date], batch: Optional[dict[int, tuple]]) -> Outcome:
    """The frozen walk over the rows of ``broker_id`` as stored, with the broker's own flags."""
    broker = await session.get(Broker, broker_id)
    return frozen_validate_broker_balances(broker_id=broker_id, overdraft=broker.allow_cash_overdraft, shorting=broker.allow_asset_shorting, rows=await load_rows(session, broker_id), from_date=from_date, batch=batch)


# ----- the random ledgers ------------------------------------------------------------------------------------------

CASH_AMOUNTS = ["-60", "-30", "-12.5", "-10", "10", "12.5", "30", "60"]
TRADE_AMOUNTS = ["-40", "-20", "-5", "5", "20", "40"]
CURRENCIES = [EUR, USD, GBP]
DAYS = 7  # a week of the test's month: same-day rows are common
LEDGERS_PER_CHUNK = 40
CHUNKS = 8


@dataclass
class RowSpec:
    """A row to write: type, day, amount, currency, asset slot (0 or 1, or None), quantity."""

    tx_type: TransactionType
    on: date
    amount: str
    currency: Optional[str]
    asset_slot: Optional[int]
    quantity: str


@dataclass
class Case:
    overdraft: bool
    shorting: bool
    from_date: Optional[date]
    specs: list[RowSpec]
    batch_positions: dict[int, tuple]  # position in specs -> (operation, index)


def generate_case(rng: random.Random) -> Case:
    specs: list[RowSpec] = []
    for _ in range(rng.randint(0, 9)):
        kind = rng.choice(["cash", "cash", "trade", "adjustment", "zero"])
        on = day(rng.randint(1, DAYS))
        currency = rng.choice(CURRENCIES)
        if kind == "cash":
            amount = rng.choice(CASH_AMOUNTS)
            specs.append(RowSpec(TransactionType.DEPOSIT if Decimal(amount) > 0 else TransactionType.WITHDRAWAL, on, amount, currency, None, "0"))
        elif kind == "trade":
            quantity = rng.choice(["1", "2", "3"])
            if rng.random() < 0.5:
                specs.append(RowSpec(TransactionType.BUY, on, rng.choice([a for a in TRADE_AMOUNTS if a.startswith("-")]), currency, rng.randint(0, 1), quantity))
            else:
                specs.append(RowSpec(TransactionType.SELL, on, rng.choice([a for a in TRADE_AMOUNTS if not a.startswith("-")]), currency, rng.randint(0, 1), f"-{quantity}"))
        elif kind == "adjustment":
            specs.append(RowSpec(TransactionType.ADJUSTMENT, on, "0", None, rng.randint(0, 1), rng.choice(["-3", "-2", "-1", "1", "2", "3"])))
        else:
            # a fee of zero: no cash moves, but the currency still has a line in the opening balances
            specs.append(RowSpec(TransactionType.FEE, on, "0", currency, None, "0"))
    overdraft, shorting = rng.choice([(False, False), (False, False), (True, False), (False, True), (True, True)])
    from_date = None if rng.random() < 0.3 else day(rng.randint(1, DAYS + 2))
    batch_positions = {i: (rng.choice(["create", "update", "delete"]), rng.randint(0, 5)) for i in range(len(specs)) if rng.random() < 0.4}
    return Case(overdraft, shorting, from_date, specs, batch_positions)


def case_rows_without_a_database(case: Case) -> list[Row]:
    """The case's rows with ids = position + 1 and two fixed asset ids: for the pure statistics, no database."""
    return [Row(id=i + 1, date=s.on, amount=Decimal(s.amount), currency=s.currency, asset_id=None if s.asset_slot is None else 100 + s.asset_slot, quantity=Decimal(s.quantity)) for i, s in enumerate(case.specs)]


def describe(seed: str, index: int, case: Case) -> str:
    lines = [f"seed={seed!r} ledger #{index}: overdraft={case.overdraft} shorting={case.shorting} from_date={case.from_date} batch positions={case.batch_positions}"]
    lines += [f"  [{i}] {s.tx_type.value} {s.on} amount={s.amount} {s.currency} asset_slot={s.asset_slot} quantity={s.quantity}" for i, s in enumerate(case.specs)]
    return "\n".join(lines)


class TestDifferentialAgainstTheFrozenWalk:
    """The service against the frozen copy of today's walk over seeded random ledgers (random days with same-day rows,
    three currencies, two assets, zero-amount rows, the four flag combinations, ``from_date`` or none, random batch ids).

    The expected outcome is the frozen walk's, EXCEPT the documented difference (no transaction from ``from_date`` on,
    no overdraft flag, negative opening cash): there it is the cash refusal on ``from_date``. The first test is green before and after; the second, which
    holds those ledgers, is red today.
    """

    @staticmethod
    async def _run_chunk(session: AsyncSession, chunk: int) -> tuple[list[str], list[str]]:
        """Every ledger of the chunk through the service: (the mismatches the documented difference does NOT explain, the
        ledgers of the documented difference the service did not refuse). The whole chunk runs: one mismatch must not hide the next."""
        seed = f"w6-12-differential-{chunk}"
        rng = random.Random(seed)
        asset_ids = [await new_asset(session), await new_asset(session)]
        unexpected: list[str] = []
        rule_misses: list[str] = []
        for index in range(LEDGERS_PER_CHUNK):
            case = generate_case(rng)
            broker_id = await new_broker(session, overdraft=case.overdraft, shorting=case.shorting)
            tx_ids: list[int] = []
            for spec in case.specs:
                asset_id = None if spec.asset_slot is None else asset_ids[spec.asset_slot]
                tx_ids.append(await put(session, broker_id, spec.tx_type, spec.on, amount=spec.amount, currency=spec.currency, asset_id=asset_id, quantity=spec.quantity))
            batch = {tx_ids[position]: marker for position, marker in case.batch_positions.items()}
            rows = await load_rows(session, broker_id)

            documented = is_the_documented_difference(overdraft=case.overdraft, rows=rows, from_date=case.from_date)
            want = expected_after_w6_12(broker_id=broker_id, overdraft=case.overdraft, shorting=case.shorting, rows=rows, from_date=case.from_date, batch=batch)
            got = await validate(session, broker_id, case.from_date, batch or None)
            if not same_outcome(got, want):
                report = f"{describe(seed, index, case)}\n  got:  {got}\n  want: {want}"
                (rule_misses if documented else unexpected).append(report)
        return unexpected, rule_misses

    @pytest.mark.asyncio
    @pytest.mark.parametrize("chunk", range(CHUNKS))
    async def test_everything_but_the_documented_difference_matches_the_frozen_walk(self, session, chunk):
        """Green before and after W6-12: every ledger the rule change does not touch has the frozen walk's outcome, field by field."""
        unexpected, _ = await self._run_chunk(session, chunk)

        assert not unexpected, f"{len(unexpected)} ledger(s) differ from the frozen walk outside the documented difference:\n" + "\n".join(unexpected[:3])

    @pytest.mark.asyncio
    @pytest.mark.parametrize("chunk", range(CHUNKS))
    async def test_the_documented_difference_is_refused_on_the_from_date(self, session, chunk):
        """RED today (the service accepts them): a ledger with no transaction from ``from_date`` on, no overdraft flag and a
        negative opening cash is refused on ``from_date`` with the first negative currency of the opening."""
        _, rule_misses = await self._run_chunk(session, chunk)

        assert not rule_misses, f"{len(rule_misses)} ledger(s) of the documented difference were not refused as the rule says:\n" + "\n".join(rule_misses[:3])

    def test_the_differential_has_teeth(self):
        """Over the same ledgers, without a database: the frozen walk accepts some and refuses with both codes, and the documented
        difference, the same-day multi-currency reds and the batch reducers all occur. A generator that stopped producing them
        would turn the differential into a comparison of nothing."""
        accepted = cash_red = asset_red = documented = batch_named = multi_red = 0
        for chunk in range(CHUNKS):
            rng = random.Random(f"w6-12-differential-{chunk}")
            for _ in range(LEDGERS_PER_CHUNK):
                case = generate_case(rng)
                rows = case_rows_without_a_database(case)
                batch = {i + 1: marker for i, marker in case.batch_positions.items()}
                outcome = frozen_validate_broker_balances(broker_id=1, overdraft=case.overdraft, shorting=case.shorting, rows=rows, from_date=case.from_date, batch=batch)
                if outcome is None:
                    accepted += 1
                elif outcome[0] == CASH_NEGATIVE:
                    cash_red += 1
                    batch_named += outcome[4] != -1
                else:
                    asset_red += 1
                    batch_named += outcome[4] != -1
                documented += is_the_documented_difference(overdraft=case.overdraft, rows=rows, from_date=case.from_date)
                multi_red += sum(1 for c in CURRENCIES if _currency_total(rows, c) < 0) > 1
        assert accepted >= 30, f"only {accepted} accepted ledgers"
        assert cash_red >= 30 and asset_red >= 5, f"cash reds {cash_red}, asset reds {asset_red}"
        assert documented >= 3, f"only {documented} ledgers hit the documented difference"
        assert batch_named >= 10, f"only {batch_named} refusals name a batch transaction"
        assert multi_red >= 10, f"only {multi_red} ledgers end with more than one currency below zero"


def _currency_total(rows: list[Row], currency: str) -> Decimal:
    return sum((r.amount for r in rows if r.currency == currency), Decimal("0"))


def test_the_frozen_walk_is_the_walk_of_the_issue_example() -> None:
    """Self-check of the frozen copy (pure): it accepts the developer's example (that is today's bug), and the rule helper refuses it."""
    rows = [Row(1, D10, Decimal("-100"), USD, None, Decimal("0"))]
    assert frozen_validate_broker_balances(broker_id=1, overdraft=False, shorting=False, rows=rows, from_date=D15, batch=None) is None
    assert is_the_documented_difference(overdraft=False, rows=rows, from_date=D15)
    assert not is_the_documented_difference(overdraft=True, rows=rows, from_date=D15)
    assert not is_the_documented_difference(overdraft=False, rows=rows, from_date=None)
    assert not is_the_documented_difference(overdraft=False, rows=rows + [Row(2, D15, Decimal("1"), USD, None, Decimal("0"))], from_date=D15)
