"""J-47 — the FIFO engine replays a ledger until a day: ``run_fifo_lot_engine(..., replay_until=...)``.

Workstream J «Numeri e analisi», release 1.3. Pure: ``run_fifo_lot_engine`` on hand-written ``FifoInputTransaction``
rows — no DB, no server, no FX. The service-level reds are in ``test_financial/test_lots_transfer_in_transit_at_date_to.py``.

THE BUG. ``LotsAnalysisService._load_transactions`` cuts the ledger at ``date_to``. A TRANSFER still in transit on that
day — departed on or before it, arriving after it — loses its arriving leg, and the engine answers TRANSFER_PAIR_MISSING
(a quantitative failure: FAILED), even over both brokers of the pair. The engine's transit window is
[min(dates), max(dates)) whichever leg carries the earlier date (``FifoLotEngine.classify_events``), so a pair whose
receiving leg is dated BEFORE its giving leg is cut the same way.

THE RULE (coordinator, 17/10; as the Dashboard, which loads the whole pair and keeps the units in transit from departure
to arrival). The service hands the engine the partner legs dated after ``date_to``, and the engine replays until
``date_to``: an event dated after ``replay_until`` is neither applied nor returned in ``classified_events``.

1. A pair departing on or before ``replay_until`` and arriving after it: TRANSFER_DEPART applied, TRANSFER_ARRIVE dropped
   — the units stay IN_TRANSIT (``end_date`` None) on ``replay_until``, and nothing is missing: COMPLETE.
2. Any other row dated after ``replay_until`` — a SELL, a pair that departs after it — is not applied: the result is the
   one of the rows dated on or before ``replay_until``.
3. GUARD: ``replay_until`` None, or on or after the last event, changes nothing. The bound is inclusive: an event dated
   ON ``replay_until`` is applied.

Today (base ``497aaa07c``): TypeError — ``run_fifo_lot_engine() got an unexpected keyword argument 'replay_until'`` — in
every test of this file, the guards included: the keyword does not exist yet. Each test computes what it can without it
first, so that a precondition read today stays green.
"""

import dataclasses
from datetime import date
from decimal import Decimal

import pytest

from backend.app.services.financial_math.fifo.engine import run_fifo_lot_engine
from backend.app.services.financial_math.fifo.models import FifoEngineResult, FifoInputTransaction

D = Decimal
ASSET_ID = 4747
BROKER_A = 1  # the sender
BROKER_B = 2  # the receiver
BUY_ID = 101
OUT_ID = 102  # A's TRANSFER −10, the giving leg
IN_ID = 201  # B's TRANSFER +10, the receiving leg
SELL_ID = 301
BUY_DAY = date(2025, 1, 10)


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #


def _day(iso: str) -> date:
    return date.fromisoformat(iso)


def _buy() -> FifoInputTransaction:
    """A buys 10 at 100 EUR on 10 Jan."""
    return FifoInputTransaction(id=BUY_ID, broker_id=BROKER_A, asset_id=ASSET_ID, date=BUY_DAY, type="BUY", quantity=D("10"), amount=D("-1000"), currency="EUR")


def _transfer_pair(*, out_day: str, in_day: str) -> list[FifoInputTransaction]:
    """10 units from A to B: A's leg dated ``out_day``, B's ``in_day`` (with its cost basis, which the engine never reads)."""
    return [
        FifoInputTransaction(id=OUT_ID, broker_id=BROKER_A, asset_id=ASSET_ID, date=_day(out_day), type="TRANSFER", quantity=D("-10"), currency="EUR", related_transaction_id=IN_ID),
        FifoInputTransaction(
            id=IN_ID,
            broker_id=BROKER_B,
            asset_id=ASSET_ID,
            date=_day(in_day),
            type="TRANSFER",
            quantity=D("10"),
            currency="EUR",
            cost_basis_override=D("100"),
            cost_basis_currency="EUR",
            related_transaction_id=OUT_ID,
        ),
    ]


def _sell(*, on: str, broker_id: int) -> FifoInputTransaction:
    """4 units sold at 140 EUR."""
    return FifoInputTransaction(id=SELL_ID, broker_id=broker_id, asset_id=ASSET_ID, date=_day(on), type="SELL", quantity=D("-4"), amount=D("560"), currency="EUR")


def _run(transactions: list[FifoInputTransaction], **options) -> FifoEngineResult:
    return run_fifo_lot_engine(transactions, {BROKER_A: False, BROKER_B: False}, target_currency="EUR", **options)


def _dated_after(result: FifoEngineResult, day: date) -> list[tuple]:
    """Whatever the result dates after ``day``: events, fragment bounds, closures."""
    return [
        *(("event", event.kind, event.date) for event in result.classified_events if event.date > day),
        *(("fragment", fragment.fragment_id, fragment.start_date, fragment.end_date) for fragment in result.fragment_intervals if fragment.start_date > day or (fragment.end_date is not None and fragment.end_date > day)),
        *(("closure", closure.transaction_id, closure.close_date) for closure in result.closures if closure.close_date > day),
    ]


# --------------------------------------------------------------------------- #
# Rule 1: a pair arriving after replay_until stays in transit
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("out_day", "in_day", "replay_until", "departs_on"),
    [
        pytest.param("2025-01-12", "2025-01-16", "2025-01-14", "2025-01-12", id="departure-leg-dated-first"),
        pytest.param("2025-01-15", "2025-01-11", "2025-01-13", "2025-01-11", id="arrival-leg-dated-first"),
    ],
)
def test_a_transfer_arriving_after_replay_until_stays_in_transit(out_day, in_day, replay_until, departs_on):
    """Rule 1: A buys 10 on 10 Jan and sends them to B; the transit window opens on the earlier of the two legs' days and
    closes after ``replay_until``. COMPLETE, no issue: TRANSFER_DEPART on the window's first day, no TRANSFER_ARRIVE; the
    lot keeps its 10 units, nothing realized, all of them IN_TRANSIT from A to B with no end; nothing dated after
    ``replay_until``. The receiving leg dated first is the same pair, read in the same window.

    Today: TypeError — ``run_fifo_lot_engine() got an unexpected keyword argument 'replay_until'``. (Without the keyword
    the whole pair replays: the units arrive at B — the precondition below, green today.)
    """
    ledger = [_buy(), *_transfer_pair(out_day=out_day, in_day=in_day)]
    assert [event.kind for event in _run(ledger).classified_events] == ["BUY", "TRANSFER_DEPART", "TRANSFER_ARRIVE"]

    result = _run(ledger, replay_until=_day(replay_until))

    assert {
        "status": result.analysis_status,
        "issues": [issue.code for issue in result.issues],
        "events": [(event.kind, event.date) for event in result.classified_events],
        "lots": [(lot.lot_id, lot.open_quantity, lot.realized_quantity) for lot in result.lots],
        # (lot, custody, broker, source, destination, quantity, start, end)
        "open fragments": [(f.lot_id, f.custody_type, f.broker_id, f.source_broker_id, f.destination_broker_id, f.quantity, f.start_date, f.end_date) for f in result.active_fragments()],
        "states": sorted(result.get_lot_states(BUY_ID)),
        "dated after replay_until": _dated_after(result, _day(replay_until)),
    } == {
        "status": "COMPLETE",
        "issues": [],
        "events": [("BUY", BUY_DAY), ("TRANSFER_DEPART", _day(departs_on))],
        "lots": [(BUY_ID, D("10"), D("0"))],
        "open fragments": [(BUY_ID, "IN_TRANSIT", None, BROKER_A, BROKER_B, D("10"), _day(departs_on), None)],
        "states": ["IN_TRANSIT", "LONG", "OPEN"],
        "dated after replay_until": [],
    }


# --------------------------------------------------------------------------- #
# Rule 2: a row dated after replay_until is not applied
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "late_rows",
    [
        pytest.param([_sell(on="2025-01-15", broker_id=BROKER_A)], id="a-sell"),
        pytest.param(_transfer_pair(out_day="2025-01-15", in_day="2025-01-16"), id="a-pair-departing-after"),
    ],
)
def test_rows_dated_after_replay_until_are_not_applied(late_rows):
    """Rule 2: A buys 10 on 10 Jan; ``late_rows`` are dated after ``replay_until`` (14 Jan). Read until 14 Jan, the ledger
    is the BUY alone: no closure, the lot open with its 10 units at A, one BUY event — the very result, field by field,
    of the BUY replayed alone.

    Today: TypeError — ``run_fifo_lot_engine() got an unexpected keyword argument 'replay_until'``. (Without the keyword
    the late rows replay: the precondition below, green today.)
    """
    assert len(_run([_buy(), *late_rows]).classified_events) > 1

    result = _run([_buy(), *late_rows], replay_until=_day("2025-01-14"))

    assert {
        "events": [(event.kind, event.date) for event in result.classified_events],
        "closures": result.closures,
        "lots": [(lot.lot_id, lot.open_quantity, lot.realized_quantity) for lot in result.lots],
        "open fragments": [(f.custody_type, f.broker_id, f.quantity) for f in result.active_fragments()],
    } == {
        "events": [("BUY", BUY_DAY)],
        "closures": [],
        "lots": [(BUY_ID, D("10"), D("0"))],
        "open fragments": [("BROKER", BROKER_A, D("10"))],
    }
    assert dataclasses.asdict(result) == dataclasses.asdict(_run([_buy()]))


# --------------------------------------------------------------------------- #
# Rule 3: GUARD — None, or on or after the last event, changes nothing
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("replay_until", [None, "2025-01-16", "2025-01-20"], ids=["none", "on-the-last-day", "after-the-last-day"])
def test_guard_replay_until_none_or_on_or_after_the_last_event_changes_nothing(replay_until):
    """GUARD (after J-47): A buys 10 on 10 Jan and sends them to B (12 → 16 Jan); B sells 4 on 16 Jan, the arrival's day.
    With ``replay_until`` None, on 16 Jan or later, the result is today's, field by field: the bound is inclusive, so the
    arrival and the sale of 16 Jan are both applied on 16 Jan.

    Today: TypeError — ``run_fifo_lot_engine() got an unexpected keyword argument 'replay_until'``, even for None: the
    keyword does not exist yet. (Today's run, without it, has the arrival and the sale: the precondition, green.)
    """
    ledger = [_buy(), *_transfer_pair(out_day="2025-01-12", in_day="2025-01-16"), _sell(on="2025-01-16", broker_id=BROKER_B)]
    today = _run(ledger)
    assert [(event.kind, event.date) for event in today.classified_events] == [("BUY", BUY_DAY), ("TRANSFER_DEPART", _day("2025-01-12")), ("TRANSFER_ARRIVE", _day("2025-01-16")), ("SELL", _day("2025-01-16"))]

    result = _run(ledger, replay_until=None if replay_until is None else _day(replay_until))

    assert dataclasses.asdict(result) == dataclasses.asdict(today)
