"""J-12 (decision N81) — S4, pure: a transfer that cannot depart names its GIVING leg, whatever the ids and the dates.

Workstream J «Numeri e analisi», release 1.3. Pure: ``run_fifo_lot_engine`` on hand-written ``FifoInputTransaction`` rows —
no DB, no server, no FX. The service-level half (with ``transaction_date``) is in
``test_financial/test_lots_failed_analysis_withholding.py``.

THE RULE (journal of J, «J-12: contratto con Y», point (a)): an issue's ``transaction_id`` is always a real row of the
scope, the one to fix. A TRANSFER that departs with more than its broker holds (FIFO_SOURCE_QUANTITY_MISSING), or from a
short position (SHORT_TRANSFER_NOT_SUPPORTED), is the GIVING leg's fault: the issue names the out leg, the first of the
departure event's ``raw_transaction_ids``.

TODAY (base ``2f4ef68e6``) ``FifoLotEngine._apply_transfer_depart`` names ``event.transaction_id``, the departure event's
id: ``min(out, in)`` for a same-day pair, else the earlier-dated leg (``classify_events``). So the issue names the
receiving leg when that leg has the lower id, or carries the earlier date (the transit window is [min(dates), max(dates))
whichever leg is earlier). Each red says what it read.
"""

from datetime import date
from decimal import Decimal

import pytest

from backend.app.services.financial_math.fifo.engine import run_fifo_lot_engine
from backend.app.services.financial_math.fifo.models import FifoEngineResult, FifoInputTransaction

D = Decimal
ASSET_ID = 1212
BROKER_A = 1  # the sender: holds 5 (or −3, short)
BROKER_B = 2  # the receiver
OPENING_ID = 50
LOW_ID = 60
HIGH_ID = 70
OPENING_DAY = date(2025, 2, 3)
TRANSFER_DAY = date(2025, 2, 10)
LATER_DAY = date(2025, 2, 12)


def _opening(*, short: bool) -> FifoInputTransaction:
    """A buys 5 at 100 — or, ``short``, sells 3 at 100 and holds −3."""
    if short:
        return FifoInputTransaction(id=OPENING_ID, broker_id=BROKER_A, asset_id=ASSET_ID, date=OPENING_DAY, type="SELL", quantity=D("-3"), amount=D("300"), currency="EUR")
    return FifoInputTransaction(id=OPENING_ID, broker_id=BROKER_A, asset_id=ASSET_ID, date=OPENING_DAY, type="BUY", quantity=D("5"), amount=D("-500"), currency="EUR")


def _pair(*, out_id: int, in_id: int, quantity: str, out_day: date = TRANSFER_DAY, in_day: date = TRANSFER_DAY) -> list[FifoInputTransaction]:
    """A gives ``quantity`` to B: A's leg ``out_id`` on ``out_day``, B's ``in_id`` on ``in_day`` (with its Auto cost, 100 a unit)."""
    return [
        FifoInputTransaction(id=out_id, broker_id=BROKER_A, asset_id=ASSET_ID, date=out_day, type="TRANSFER", quantity=-D(quantity), currency="EUR", related_transaction_id=in_id),
        FifoInputTransaction(
            id=in_id,
            broker_id=BROKER_B,
            asset_id=ASSET_ID,
            date=in_day,
            type="TRANSFER",
            quantity=D(quantity),
            currency="EUR",
            cost_basis_override=D("100"),
            cost_basis_currency="EUR",
            related_transaction_id=out_id,
        ),
    ]


def _run(rows: list[FifoInputTransaction], *, short: bool = False) -> FifoEngineResult:
    return run_fifo_lot_engine(sorted(rows, key=lambda row: (row.date, row.id)), {BROKER_A: short, BROKER_B: False})


def _named(result: FifoEngineResult) -> dict:
    """The one transfer issue, by what it names; and the giving leg as the departure event carries it."""
    departs = [event for event in result.classified_events if event.kind == "TRANSFER_DEPART"]
    assert len(departs) == 1, [event.kind for event in result.classified_events]
    assert len(result.issues) == 1, [(issue.code, issue.transaction_id) for issue in result.issues]
    issue = result.issues[0]
    return {"code": issue.code, "transaction_id": issue.transaction_id, "broker_id": issue.broker_id, "giving leg of the departure": departs[0].raw_transaction_ids[0]}


@pytest.mark.parametrize(
    ("short", "quantity", "code"),
    [(False, "8", "FIFO_SOURCE_QUANTITY_MISSING"), (True, "2", "SHORT_TRANSFER_NOT_SUPPORTED")],
    ids=["beyond-holdings", "short"],
)
def test_same_day_pair_with_the_receiving_leg_lower_names_the_giving_leg(short, quantity, code):
    """RED. Same-day pair, B's receiving leg has the lower id (60), A's giving leg the higher (70). The issue names 70.

    Today: the issue names 60, B's receiving leg (the departure event's ``min(out, in)``), with ``broker_id`` A — for
    FIFO_SOURCE_QUANTITY_MISSING and SHORT_TRANSFER_NOT_SUPPORTED alike.
    """
    result = _run([_opening(short=short), *_pair(out_id=HIGH_ID, in_id=LOW_ID, quantity=quantity)], short=short)

    assert result.analysis_status == "FAILED"
    assert _named(result) == {"code": code, "transaction_id": HIGH_ID, "broker_id": BROKER_A, "giving leg of the departure": HIGH_ID}


@pytest.mark.parametrize(
    ("short", "quantity", "code"),
    [(False, "8", "FIFO_SOURCE_QUANTITY_MISSING"), (True, "2", "SHORT_TRANSFER_NOT_SUPPORTED")],
    ids=["beyond-holdings", "short"],
)
def test_pair_whose_receiving_leg_is_dated_first_names_the_giving_leg(short, quantity, code):
    """RED. B's receiving leg is dated 10 Feb, A's giving leg 12 Feb (the transit window opens on 10 Feb), and the giving
    leg has the lower id (60). The issue names 60, A's leg — not the leg that carries the earlier date.

    Today: the issue names 70, B's receiving leg (the leg dated at the start of the transit window), with ``broker_id`` A
    — for both codes.
    """
    result = _run([_opening(short=short), *_pair(out_id=LOW_ID, in_id=HIGH_ID, quantity=quantity, out_day=LATER_DAY, in_day=TRANSFER_DAY)], short=short)

    assert result.analysis_status == "FAILED"
    assert _named(result) == {"code": code, "transaction_id": LOW_ID, "broker_id": BROKER_A, "giving leg of the departure": LOW_ID}


@pytest.mark.parametrize(
    ("short", "quantity", "code"),
    [(False, "8", "FIFO_SOURCE_QUANTITY_MISSING"), (True, "2", "SHORT_TRANSFER_NOT_SUPPORTED")],
    ids=["beyond-holdings", "short"],
)
@pytest.mark.parametrize(("out_day", "in_day"), [(TRANSFER_DAY, TRANSFER_DAY), (TRANSFER_DAY, LATER_DAY)], ids=["same-day", "giving-leg-dated-first"])
def test_guard_giving_leg_with_the_lower_id_and_the_earlier_date_is_already_named(short, quantity, code, out_day, in_day):
    """GUARD (green today and after): the giving leg has the lower id (60) and is not dated after the receiving one — the
    usual order. The issue names it, today as after."""
    result = _run([_opening(short=short), *_pair(out_id=LOW_ID, in_id=HIGH_ID, quantity=quantity, out_day=out_day, in_day=in_day)], short=short)

    assert result.analysis_status == "FAILED"
    assert _named(result) == {"code": code, "transaction_id": LOW_ID, "broker_id": BROKER_A, "giving leg of the departure": LOW_ID}
