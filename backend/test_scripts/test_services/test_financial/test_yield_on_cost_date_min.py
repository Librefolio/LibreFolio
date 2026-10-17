"""Yield on Cost of an income dated date.min (MF-SEC8-2b). Pure: no database, no FX service, no server.

An income's eligible quantity is what the position held at the end of the day before it (D-1). An income stored on
date.min (0001-01-01: an older version or a hand edit; N74 refuses new rows before 1900) has no day before it: nothing
was held then, so its Yield on Cost is unavailable with INCOME_WITHOUT_ELIGIBLE_QUANTITY, as for any income with
nothing held the day before. On HEAD c0b4b6f05 ``_calculate_income_position`` subtracts a day from it: OverflowError.

The per-position seam ``_calculate_position`` is called with the contexts ``calculate_yield_on_cost_for_positions``
builds from the database, here in memory: the replay is the FIFO engine over the position's rows with a quantity, and
the income is already in the report currency. These cases use the report end 0001-12-31, the one whose trailing year
[as_of - 364 days, as_of] reaches date.min by plain arithmetic.

The trailing year itself is computed by ``calculate_yield_on_cost_for_positions``: for an as_of earlier in year 1 its
start falls before date.min, and on HEAD f4a1e374f ``as_of_date - timedelta(days=364)`` raises OverflowError before
anything is loaded. The last test pins that window through the entry, with the one loader that reads the database
replaced by a stub that records the window and returns an empty ledger.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

import backend.app.services.financial_math.yield_on_cost as yoc_module
from backend.app.db.models import Transaction, TransactionType
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import YieldOnCostStatus, YieldOnCostUnavailableReason
from backend.app.services.financial_math.fifo.engine import run_fifo_lot_engine
from backend.app.services.financial_math.yield_on_cost import YieldOnCostPositionInput

ASSET_ID = 501
BROKER_ID = 51
KEY = (ASSET_ID, BROKER_ID)
BUY_ID = 1
INCOME_ID = 2
INCOME_EUR = Decimal("5")
WAC_EUR = Decimal("10")

#: The last report end whose 365-day window still reaches date.min.
YEAR_ONE_END = date(1, 12, 31)


def _row(tx_id: int, tx_type: TransactionType, *, on: date, quantity: str = "0", amount: str = "0") -> Transaction:
    """A ledger row as YoC reads it: a ``Transaction`` that is never added to a session."""
    return Transaction(id=tx_id, broker_id=BROKER_ID, asset_id=ASSET_ID, type=tx_type, date=on, quantity=Decimal(quantity), amount=Decimal(amount), currency="EUR")


def _yield_on_cost(*, bought_on: date, income_on: date, as_of: date):
    """The YoC result of one position: 10 units bought for 100 EUR on ``bought_on``, a 5 EUR dividend on
    ``income_on``, a residual WAC of 10 EUR."""
    buy = _row(BUY_ID, TransactionType.BUY, on=bought_on, quantity="10", amount="-100")
    income = _row(INCOME_ID, TransactionType.DIVIDEND, on=income_on, amount=str(INCOME_EUR))
    replay = run_fifo_lot_engine(transactions=[buy], broker_shorting={BROKER_ID: False})
    calculation = yoc_module._calculate_position(
        key=KEY,
        position=YieldOnCostPositionInput(asset_id=ASSET_ID, broker_id=BROKER_ID, wac_per_unit=WAC_EUR, wac_currency="EUR"),
        transaction_context=yoc_module._TransactionContext(replay_transactions=[buy, income], first_pair_date={KEY: min(bought_on, income_on)}, income_by_key={KEY: [income]}),
        replay_context=yoc_module._ReplayContext(replay_by_key={KEY: replay}, invalid_keys=set(), failed_keys=set()),
        conversion_context=yoc_module._ConversionContext(income_by_transaction={INCOME_ID: INCOME_EUR}, provenance_by_key={}, missing_by_key={}, missing_pairs_by_key={}),
        target_currency="EUR",
        window_start=as_of - timedelta(days=364),
        as_of_date=as_of,
    )
    return calculation.result


@pytest.mark.parametrize(
    ("bought_on", "income_on", "as_of"),
    [
        pytest.param(date.min, date.min, YEAR_ONE_END, id="date_min"),
        pytest.param(date(2025, 6, 2), date(2025, 6, 2), date(2025, 12, 31), id="ordinary_day"),
    ],
)
def test_income_with_nothing_held_the_day_before_is_unavailable(bought_on, income_on, as_of):
    """Red on HEAD c0b4b6f05 for ``date_min`` (OverflowError). The only lot was bought on the income's day, so nothing
    was held the day before: unavailable, INCOME_WITHOUT_ELIGIBLE_QUANTITY, the issue dated on the income — for
    ``ordinary_day`` today, and for date.min, which has no day before at all."""
    result = _yield_on_cost(bought_on=bought_on, income_on=income_on, as_of=as_of)

    assert result.status == YieldOnCostStatus.UNAVAILABLE
    assert result.reason == YieldOnCostUnavailableReason.INCOME_WITHOUT_ELIGIBLE_QUANTITY
    assert result.value is None
    assert result.provenance.issue_date == income_on
    assert (result.provenance.gross_income_transaction_count, result.provenance.gross_income_per_unit) == (1, None)


@pytest.mark.parametrize(
    ("bought_on", "income_on", "as_of"),
    [
        pytest.param(date.min, date.min + timedelta(days=1), YEAR_ONE_END, id="day_after_date_min"),
        pytest.param(date(2025, 6, 1), date(2025, 6, 2), date(2025, 12, 31), id="ordinary_day"),
    ],
)
def test_income_with_a_lot_held_the_day_before_is_available(bought_on, income_on, as_of):
    """Guard (green on HEAD c0b4b6f05 and after). The 10 units were held the day before the income — date.min itself
    for ``day_after_date_min``: 5 EUR / 10 units = 0.5 EUR per unit, over a WAC of 10 EUR = 0.05."""
    result = _yield_on_cost(bought_on=bought_on, income_on=income_on, as_of=as_of)

    assert result.status == YieldOnCostStatus.AVAILABLE
    assert result.reason is None
    assert result.value == Decimal("0.05")
    assert result.provenance.gross_income_per_unit == Currency(code="EUR", amount=Decimal("0.5"))


#: Handed to ``calculate_yield_on_cost_for_positions`` as its session. Nothing reads it: the loader is stubbed, and with
#: no income the replay stage returns before its queries and ``convert_bulk`` before its own. A read would fail loudly.
_NO_DATABASE = object()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("as_of", "expected_window_start"),
    [
        pytest.param(date(1, 6, 1), date.min, id="as_of_in_year_one"),
        pytest.param(YEAR_ONE_END, date.min, id="as_of_on_the_last_day_of_year_one"),
        pytest.param(date(2025, 12, 31), date(2025, 1, 1), id="ordinary_as_of"),
    ],
)
async def test_trailing_year_starts_on_date_min_at_the_earliest(monkeypatch, as_of, expected_window_start):
    """Red on HEAD f4a1e374f for ``as_of_in_year_one`` (OverflowError: 0001-06-01 minus 364 days is before date.min,
    raised before the ledger is loaded). The trailing year is [as_of - 364 days, as_of], cut at date.min: the window
    handed to the loader and written in the provenance starts on date.min. ``as_of_on_the_last_day_of_year_one``
    (exactly date.min by plain arithmetic) and ``ordinary_as_of`` are the guards, as today.

    The stubbed loader returns an empty ledger, so the position has no income and no first transaction:
    INSUFFICIENT_HISTORY, whatever the window."""
    loads: list[dict[str, date]] = []

    async def record_the_window(db, *, window_start, as_of_date, **_scope):
        loads.append({"window_start": window_start, "as_of_date": as_of_date})
        return yoc_module._TransactionContext(replay_transactions=[], first_pair_date={}, income_by_key={})

    monkeypatch.setattr(yoc_module, "_load_transaction_context", record_the_window)

    calculations = await yoc_module.calculate_yield_on_cost_for_positions(
        _NO_DATABASE,
        user_id=1,
        positions=[YieldOnCostPositionInput(asset_id=ASSET_ID, broker_id=BROKER_ID, wac_per_unit=WAC_EUR, wac_currency="EUR")],
        target_currency="EUR",
        as_of_date=as_of,
    )

    assert loads == [{"window_start": expected_window_start, "as_of_date": as_of}]
    result = calculations[KEY].result
    assert (result.provenance.window_start, result.provenance.window_end) == (expected_window_start, as_of)
    assert (result.status, result.reason) == (YieldOnCostStatus.UNAVAILABLE, YieldOnCostUnavailableReason.INSUFFICIENT_HISTORY)
