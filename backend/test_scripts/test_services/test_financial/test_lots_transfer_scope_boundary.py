"""J-10, decision N76 — a lots analysis reads a TRANSFER whose other leg sits outside its broker scope at the boundary.

Workstream J «Numeri e analisi», release 1.3: the service-level reds R1–R12 of the lot, through
``lots_analysis_service.get_lots_analysis``. The pure reading and the engine flag are pinned in
``test_financial_math/test_lots_scope_boundary.py``; R13, the AI Export, beside the ``broker.fifo_summary`` tests
(``test_ai_export_broker_fifo_summary_scope_boundary.py``).

TODAY (base ``ba63b7b24``) the analysis replays only the transactions of the brokers in scope (``_load_transactions``):
scope = ``broker_ids`` ∩ the brokers the user can access, every accessible broker when ``broker_ids`` is None. A
TRANSFER whose other leg sits at a broker outside the scope cannot pair (``FifoLotEngine._resolve_transfer_pair``):
TRANSFER_PAIR_MISSING, a quantitative failure, so the whole asset is FAILED — for the owner who filters one broker as
for a co-owner who sees only one.

THE RULE (decision N76, coordinator 17/10; ``financial_math/lots/scope_boundary.py``). A TRANSFER leg in scope whose
partner exists at a broker OUTSIDE the scope and pairs back — TRANSFER, pointing back, same asset, opposite signs, same
absolute quantity — is a boundary leg, read through a detached copy (the ORM rows are never touched):
- IN: an ADJUSTMENT-in at the leg's own cost basis: its lot opens on the leg's day, ``lot_id`` the leg's id. Without a
  cost (legacy data) a costless ADJUSTMENT-in: MISSING_COST_BASIS, DEGRADED;
- OUT: an ADJUSTMENT-out at the market of its own day (the lots' unified price resolver, per unit): the scope realizes
  market − FIFO cost, the closure is an ADJUSTMENT_OUT. With no observation on or before that day each unit leaves at
  its own FIFO cost (realized 0);
- PERFORMANCE_HISTORY: the leg moves its market value of the day across the scope, as the external-transfer branch of
  the accessible re-run does (``financial_math/lots/histories.py``), so a co-owner who sees one broker gets the series
  of the owner who filters it.
A pair that does not pair back stays FAILED (GUARD R8), an internal pair stays a real transfer (GUARDS R3, R10), and the
ORM rows stay as they are (GUARD R9).

LEDGER L1 (``backend/test_scripts/test_services/_scope_boundary_books.py``): A buys 10 at 100 on 10 Jan 2025 and sends
them to B on 12 Jan (market 130); B receives them on 13 Jan at a cost basis of 100 a unit and sells 4 at 150 on 15 Jan;
read on 16 Jan (150, carried from 15 Jan). U owns A and B. Dates in 2025, so R13-SEC7-1's bound (``latest_range_end``,
tomorrow) never clamps them.

Rows are written straight into the session and rolled back; each test owns its users, brokers and asset. No FX:
everything is in EUR.
"""

from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, Transaction, TransactionType, User
from backend.app.db.session import get_async_engine
from backend.app.schemas.portfolio import LotAnalysisType, LotsAnalysisResponse
from backend.app.services.lots_analysis_service import get_lots_analysis
from backend.test_scripts.test_services._scope_boundary_books import (
    L1_ARRIVAL_DAY,
    L1_BUY_DAY,
    L1_DATE_TO,
    L1_DEPARTURE_DAY,
    L1_PRICES,
    LedgerL1,
    add_prices,
    asset_row,
    grant_owner,
    link,
    new_asset,
    new_broker,
    new_user,
    seed_l1,
)

D = Decimal
SUMMARY = LotAnalysisType.LOT_SUMMARY
EVENTS = LotAnalysisType.EVENT_HISTORY
PERFORMANCE = LotAnalysisType.PERFORMANCE_HISTORY
_CLOSURE_KINDS = {"SELL", "ADJUSTMENT_OUT"}
_TRANSFER_KINDS = {"TRANSFER_DEPART", "TRANSFER_ARRIVE"}
_ADJUSTMENT_KINDS = {"ADJUSTMENT_IN", "ADJUSTMENT_OUT"}


@pytest_asyncio.fixture
async def session():
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as s:
        yield s
        await s.rollback()


# --------------------------------------------------------------------------- #
# Readings
# --------------------------------------------------------------------------- #


async def _analysis(session: AsyncSession, user: User, asset: Asset, *, broker_ids: list[int] | None, analyses: list[LotAnalysisType], date_to: date = L1_DATE_TO) -> LotsAnalysisResponse:
    return await get_lots_analysis(
        session=session,
        user_id=user.id,
        asset_id=asset.id,
        broker_ids=broker_ids,
        date_from=None,
        date_to=date_to,
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=analyses,
    )


def _issues(result: LotsAnalysisResponse) -> list:
    return list(result.data_quality.issues) if result.data_quality else []


def _issue_codes(result: LotsAnalysisResponse) -> list[str]:
    """The distinct issue codes of the analysis, sorted."""
    return sorted({str(issue.code) for issue in _issues(result)})


def _lots(result: LotsAnalysisResponse, *fields: str) -> list[dict]:
    """The lots of the analysis (the asset is the test's own: every lot is the test's), ``fields`` of each, by lot id."""
    return sorted(({name: getattr(lot, name) for name in fields} for lot in result.lots or []), key=lambda lot: lot["lot_id"])


def _closures(result: LotsAnalysisResponse) -> list[dict]:
    """The closure rows of the event history (SELL, ADJUSTMENT_OUT), by date and lot."""
    rows = [event for event in result.lot_events or [] if str(event.kind) in _CLOSURE_KINDS]
    return [
        {
            "lot_id": event.lot_id,
            "transaction_id": event.transaction_id,
            "date": event.date,
            "kind": str(event.kind),
            "quantity": event.quantity,
            "close_unit_price": event.close_unit_price,
            "realized_pnl": event.realized_pnl,
            "proceeds": event.proceeds,
        }
        for event in sorted(rows, key=lambda event: (event.date, event.lot_id))
    ]


def _event_kinds(result: LotsAnalysisResponse) -> set[str]:
    return {str(event.kind) for event in result.lot_events or []}


def _series(result: LotsAnalysisResponse) -> list[tuple]:
    return [(point.date, point.roi, point.twrr) for point in result.performance_history or []]


# --------------------------------------------------------------------------- #
# Expected readings of L1
# --------------------------------------------------------------------------- #

_RECEIVER_FIELDS = ("lot_id", "opening_broker_id", "opening_date", "original_quantity", "opening_unit_price", "realized_quantity", "realized_pnl", "open_quantity", "open_value")
_SENDER_FIELDS = ("lot_id", "opening_broker_id", "opening_date", "opening_unit_price", "original_quantity", "open_quantity", "realized_quantity", "realized_pnl", "cumulative_proceeds")


def _receiver_reading(book: LedgerL1) -> dict:
    """B alone: a lot of its own opened by B's leg on 13 Jan at its cost basis, 100 a unit; 4 sold at 150 realize
    4 × (150 − 100) = 200; 6 open, worth 6 × 150 = 900 on 16 Jan. COMPLETE, no issue."""
    return {
        "status": "COMPLETE",
        "issue codes": [],
        "lots": [
            {
                "lot_id": book.in_leg.id,
                "opening_broker_id": book.broker_b.id,
                "opening_date": L1_ARRIVAL_DAY,
                "original_quantity": D("10"),
                "opening_unit_price": D("100"),
                "realized_quantity": D("4"),
                "realized_pnl": D("200"),
                "open_quantity": D("6"),
                "open_value": D("900"),
            }
        ],
    }


def _sender_reading(book: LedgerL1) -> dict:
    """A alone: A's lot of 10 at 100 leaves whole on 12 Jan at that day's market, 130 — an ADJUSTMENT_OUT closure that
    realizes 10 × (130 − 100) = 300 and brings 1300 of proceeds. COMPLETE, no issue."""
    return {
        "status": "COMPLETE",
        "issue codes": [],
        "lots": [
            {
                "lot_id": book.buy.id,
                "opening_broker_id": book.broker_a.id,
                "opening_date": L1_BUY_DAY,
                "opening_unit_price": D("100"),
                "original_quantity": D("10"),
                "open_quantity": D("0"),
                "realized_quantity": D("10"),
                "realized_pnl": D("300"),
                "cumulative_proceeds": D("1300"),
            }
        ],
        "closures": [
            {
                "lot_id": book.buy.id,
                "transaction_id": book.out_leg.id,
                "date": L1_DEPARTURE_DAY,
                "kind": "ADJUSTMENT_OUT",
                "quantity": D("10"),
                "close_unit_price": D("130"),
                "realized_pnl": D("300"),
                "proceeds": D("1300"),
            }
        ],
    }


# --------------------------------------------------------------------------- #
# R1–R5: the owner who filters, the co-owner who sees one broker, the owner who sees both
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_r1_the_owner_filtering_the_receiver_opens_a_lot_on_the_arrival_at_its_own_cost(session):
    """R1 — IN: U filters B (``broker_ids=[B]``). B's arrival reads as an ADJUSTMENT-in at its own cost basis: a lot of
    its own on 13 Jan, ``lot_id`` B's leg, at 100 a unit; the sale realizes 200; 6 open worth 900. COMPLETE, no issue.

    Today: FAILED — TRANSFER_PAIR_MISSING on B's leg and FIFO_SOURCE_QUANTITY_MISSING on the sale, which finds nothing
    to sell; no lot at all.
    """
    book = await seed_l1(session)

    result = await _analysis(session, book.owner, book.asset, broker_ids=[book.broker_b.id], analyses=[SUMMARY])

    assert {"status": result.calculation_status, "issue codes": _issue_codes(result), "lots": _lots(result, *_RECEIVER_FIELDS)} == _receiver_reading(book)


@pytest.mark.asyncio
async def test_r2_the_owner_filtering_the_sender_realizes_market_minus_cost_on_departure(session):
    """R2 — OUT: U filters A (``broker_ids=[A]``). A's departure reads as an ADJUSTMENT-out at the market of 12 Jan:
    the BUY lot closes whole on 12 Jan at 130 — realized 300, proceeds 1300 — with an ADJUSTMENT_OUT closure event.
    COMPLETE, no issue.

    Today: FAILED — TRANSFER_PAIR_MISSING on A's leg; the BUY lot stays open (10, nothing realized) and there is no
    closure.
    """
    book = await seed_l1(session)

    result = await _analysis(session, book.owner, book.asset, broker_ids=[book.broker_a.id], analyses=[SUMMARY, EVENTS])

    assert {
        "status": result.calculation_status,
        "issue codes": _issue_codes(result),
        "lots": _lots(result, *_SENDER_FIELDS),
        "closures": _closures(result),
    } == _sender_reading(book)


@pytest.mark.asyncio
async def test_r3_guard_the_owner_seeing_both_brokers_keeps_the_real_transfer(session):
    """R3 — GUARD (green today and after): U without a filter sees A and B, so the pair is inside the scope and stays a
    real transfer: one lot, A's BUY, carried to B (TRANSFER_DEPART, TRANSFER_ARRIVE), 6 open, 200 realized by the sale;
    no ADJUSTMENT_* event. COMPLETE, no issue.
    """
    book = await seed_l1(session)

    result = await _analysis(session, book.owner, book.asset, broker_ids=None, analyses=[SUMMARY, EVENTS])

    assert {
        "status": result.calculation_status,
        "issue codes": _issue_codes(result),
        "lots": _lots(result, "lot_id", "opening_broker_id", "open_quantity", "realized_pnl"),
        "transfer kinds": sorted(_event_kinds(result) & _TRANSFER_KINDS),
        "adjustment kinds": sorted(_event_kinds(result) & _ADJUSTMENT_KINDS),
    } == {
        "status": "COMPLETE",
        "issue codes": [],
        "lots": [{"lot_id": book.buy.id, "opening_broker_id": book.broker_a.id, "open_quantity": D("6"), "realized_pnl": D("200")}],
        "transfer kinds": ["TRANSFER_ARRIVE", "TRANSFER_DEPART"],
        "adjustment kinds": [],
    }


@pytest.mark.asyncio
async def test_r4_a_co_owner_who_sees_only_the_receiver_reads_what_the_owner_filtering_it_reads(session):
    """R4 — IN without a filter: V is an OWNER of B only (share 1) and asks for every broker it sees — B. The same lot
    as R1: B's leg at its own 100 a unit on 13 Jan, 200 realized, 6 open worth 900. COMPLETE, no issue. (Compared
    with R1's values, not with U's result: today both are FAILED alike.)

    Today: FAILED — TRANSFER_PAIR_MISSING and FIFO_SOURCE_QUANTITY_MISSING; no lot.
    """
    book = await seed_l1(session)
    co_owner = await new_user(session, "co_owner_of_b")
    await grant_owner(session, book.broker_b, co_owner)

    result = await _analysis(session, co_owner, book.asset, broker_ids=None, analyses=[SUMMARY])

    assert {"status": result.calculation_status, "issue codes": _issue_codes(result), "lots": _lots(result, *_RECEIVER_FIELDS)} == _receiver_reading(book)


@pytest.mark.asyncio
async def test_r5_a_co_owner_who_sees_only_the_sender_reads_what_the_owner_filtering_it_reads(session):
    """R5 — OUT without a filter: W is an OWNER of A only and asks for every broker it sees — A. The same reading as
    R2: the BUY lot closes on 12 Jan at 130, realized 300, proceeds 1300, an ADJUSTMENT_OUT closure. COMPLETE.

    Today: FAILED — TRANSFER_PAIR_MISSING; the BUY lot stays open and there is no closure.
    """
    book = await seed_l1(session)
    co_owner = await new_user(session, "co_owner_of_a")
    await grant_owner(session, book.broker_a, co_owner)

    result = await _analysis(session, co_owner, book.asset, broker_ids=None, analyses=[SUMMARY, EVENTS])

    assert {
        "status": result.calculation_status,
        "issue codes": _issue_codes(result),
        "lots": _lots(result, *_SENDER_FIELDS),
        "closures": _closures(result),
    } == _sender_reading(book)


# --------------------------------------------------------------------------- #
# R6: PERFORMANCE_HISTORY of the co-owner = the owner's filtered series
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize("side", ["receiver", "sender"])
async def test_r6_a_co_owner_who_sees_one_broker_reads_the_performance_of_the_owner_filtering_it(session, side):
    """R6 — PERFORMANCE_HISTORY: a boundary leg moves its market value of the day across the scope (IN money in, OUT
    money out), as the external-transfer branch does. U filtering one broker goes through that branch today: U can
    access both, so the service re-runs the FIFO over A and B and books the pair at market (receiver: −1300 on 13 Jan;
    sender: +1300 on 12 Jan). The co-owner who sees only that broker reads the boundary leg and must get the very same
    series — same dates, every ``roi`` and ``twrr`` equal.

    Today: the series differ. Receiver: the co-owner's analysis is FAILED with no lot and no flow, so every point is
    None, while U's reads roi 0, 0.076923, 0.285714, 0.285714 and twrr None, 0.076923, 0.153846, 0.153846 from 13 to
    16 Jan. Sender: the co-owner's lot never leaves A (TRANSFER_PAIR_MISSING), so from 12 Jan its roi and twrr follow
    the price — 0.3, 0.3, 0.4, 0.5, 0.5 — where U's roi is 0 and its twrr stays 0.3.
    """
    book = await seed_l1(session)
    broker = book.broker_b if side == "receiver" else book.broker_a
    co_owner = await new_user(session, f"co_owner_{side}")
    await grant_owner(session, broker, co_owner)

    owners = _series(await _analysis(session, book.owner, book.asset, broker_ids=[broker.id], analyses=[PERFORMANCE]))
    co_owners = _series(await _analysis(session, co_owner, book.asset, broker_ids=None, analyses=[PERFORMANCE]))

    # Precondition, green today: the reference series has values, so the comparison is never between two empty series.
    assert any(roi is not None for _day, roi, _twrr in owners) and any(twrr is not None for _day, _roi, twrr in owners), owners
    assert co_owners == owners, f"co-owner {co_owners}\nowner    {owners}"


# --------------------------------------------------------------------------- #
# R7: no price at all — each unit leaves at its own cost
# --------------------------------------------------------------------------- #


async def _seed_no_price_sender(session: AsyncSession, *, with_fee: bool = False) -> dict:
    """An asset WITHOUT any price. A: ADJUSTMENT +5 on 10 Jan at a cost of 100 EUR, ADJUSTMENT +5 on 11 Jan at 120 EUR
    (an ADJUSTMENT is never a price), TRANSFER −10 on 12 Jan ↔ B: TRANSFER +10 on 13 Jan at a cost of 110 EUR. With
    ``with_fee`` an asset-linked FEE of 2 EUR at A on 11 Jan, which sends the analysis through
    ``build_engine_transactions``."""
    owner = await new_user(session, "owner")
    broker_a = await new_broker(session, "A", owner)
    broker_b = await new_broker(session, "B", owner)
    asset = await new_asset(session, "no-price")
    first = asset_row(broker_a, asset, TransactionType.ADJUSTMENT, date(2025, 1, 10), "5", currency=None, cost="100")
    second = asset_row(broker_a, asset, TransactionType.ADJUSTMENT, date(2025, 1, 11), "5", currency=None, cost="120")
    out_leg = asset_row(broker_a, asset, TransactionType.TRANSFER, L1_DEPARTURE_DAY, "-10")
    in_leg = asset_row(broker_b, asset, TransactionType.TRANSFER, L1_ARRIVAL_DAY, "10", cost="110")
    rows = [first, second, out_leg, in_leg]
    if with_fee:
        rows.append(asset_row(broker_a, asset, TransactionType.FEE, date(2025, 1, 11), "0", amount="-2"))
    session.add_all(rows)
    await session.flush()
    await link(session, out_leg, in_leg)
    return {"owner": owner, "broker_a": broker_a, "asset": asset, "first": first, "second": second, "out_leg": out_leg}


def _own_cost_closures(book: dict) -> list[dict]:
    """Each lot leaves at its own cost on 12 Jan: 5 at 100 and 5 at 120 — not one average —, realized 0, proceeds 500
    and 600."""
    return [
        {"lot_id": book["first"].id, "transaction_id": book["out_leg"].id, "date": L1_DEPARTURE_DAY, "kind": "ADJUSTMENT_OUT", "quantity": D("5"), "close_unit_price": D("100"), "realized_pnl": D("0"), "proceeds": D("500")},
        {"lot_id": book["second"].id, "transaction_id": book["out_leg"].id, "date": L1_DEPARTURE_DAY, "kind": "ADJUSTMENT_OUT", "quantity": D("5"), "close_unit_price": D("120"), "realized_pnl": D("0"), "proceeds": D("600")},
    ]


@pytest.mark.asyncio
async def test_r7_the_sender_without_any_price_hands_each_lot_over_at_its_own_cost(session):
    """R7 — OUT without a mark: no observation on or before 12 Jan (no price row, no BUY or SELL), so A's leg hands each
    unit over at its own FIFO cost: two closures at 100 and 120, realized 0 each, proceeds 500 and 600; both lots
    closed. DEGRADED by what was already there — REFERENCE_PRICE_UNAVAILABLE on the two adjustment lots and the
    J-17 CURRENT_PRICE_ASSUMED_AT_COST over the window —, no TRANSFER_PAIR_MISSING.

    Today: FAILED — TRANSFER_PAIR_MISSING besides those two; both lots stay open, no closure.
    """
    book = await _seed_no_price_sender(session)

    result = await _analysis(session, book["owner"], book["asset"], broker_ids=[book["broker_a"].id], analyses=[SUMMARY, EVENTS])

    unpriced_lots = sorted(issue.message_params.get("lot_id") for issue in _issues(result) if str(issue.code) == "REFERENCE_PRICE_UNAVAILABLE")
    assert {
        "status": result.calculation_status,
        "issue codes": _issue_codes(result),
        "lots without a reference price": unpriced_lots,
        "lots": _lots(result, "lot_id", "open_quantity", "realized_quantity", "realized_pnl", "cumulative_proceeds"),
        "closures": _closures(result),
    } == {
        "status": "DEGRADED",
        "issue codes": ["CURRENT_PRICE_ASSUMED_AT_COST", "REFERENCE_PRICE_UNAVAILABLE"],
        "lots without a reference price": sorted([book["first"].id, book["second"].id]),
        "lots": [
            {"lot_id": book["first"].id, "open_quantity": D("0"), "realized_quantity": D("5"), "realized_pnl": D("0"), "cumulative_proceeds": D("500")},
            {"lot_id": book["second"].id, "open_quantity": D("0"), "realized_quantity": D("5"), "realized_pnl": D("0"), "cumulative_proceeds": D("600")},
        ],
        "closures": _own_cost_closures(book),
    }


@pytest.mark.asyncio
async def test_r7b_the_own_cost_handover_survives_the_fee_path(session):
    """R7b — R7 with an asset-linked FEE at A on 11 Jan: the analysis then normalizes its rows with
    ``build_engine_transactions`` (``FifoInputTransaction.from_transaction``), and the own-cost flag of the boundary
    copy must survive it — each lot still realizes 0, the closures still at 100 and 120.

    Today: FAILED — TRANSFER_PAIR_MISSING; both lots stay open, no closure. (The FEE does reach the engine: its
    allocation group is there today and after — the precondition below.)
    """
    book = await _seed_no_price_sender(session, with_fee=True)

    result = await _analysis(session, book["owner"], book["asset"], broker_ids=[book["broker_a"].id], analyses=[SUMMARY, EVENTS])

    assert {
        "the FEE reached the engine": any(group.economic_type == "FEE" for group in result.economic_allocation_groups or []),
        "TRANSFER_PAIR_MISSING": "TRANSFER_PAIR_MISSING" in _issue_codes(result),
        "lots": _lots(result, "lot_id", "realized_pnl"),
        "closures": _closures(result),
    } == {
        "the FEE reached the engine": True,
        "TRANSFER_PAIR_MISSING": False,
        "lots": [{"lot_id": book["first"].id, "realized_pnl": D("0")}, {"lot_id": book["second"].id, "realized_pnl": D("0")}],
        "closures": _own_cost_closures(book),
    }


# --------------------------------------------------------------------------- #
# R8–R10: guards
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["lone-leg", "partner-not-pointing-back", "partner-of-another-quantity"])
async def test_r8_guard_a_leg_that_does_not_pair_back_stays_failed(session, case):
    """R8 — GUARD (green today and after): only a partner that pairs back makes a boundary leg. U filters A, whose
    TRANSFER −10 (12 Jan, after a BUY of 10) has (a) no link at all; (b) a partner at B that does not point back; (c) a
    partner at B of +8. The prices of L1 are there, so a wrong boundary reading would find a mark: the analysis must
    stay FAILED on TRANSFER_PAIR_MISSING.
    """
    owner = await new_user(session, "owner")
    broker_a = await new_broker(session, "A", owner)
    broker_b = await new_broker(session, "B", owner)
    asset = await new_asset(session, f"r8-{case}")
    add_prices(session, asset, L1_PRICES)
    buy = asset_row(broker_a, asset, TransactionType.BUY, L1_BUY_DAY, "10", amount="-1000")
    out_leg = asset_row(broker_a, asset, TransactionType.TRANSFER, L1_DEPARTURE_DAY, "-10")
    rows = [buy, out_leg]
    partner = None
    if case != "lone-leg":
        partner = asset_row(broker_b, asset, TransactionType.TRANSFER, L1_ARRIVAL_DAY, "8" if case == "partner-of-another-quantity" else "10", cost="100")
        rows.append(partner)
    session.add_all(rows)
    await session.flush()
    if partner is not None:
        await link(session, out_leg, partner, both_ways=case != "partner-not-pointing-back")

    result = await _analysis(session, owner, asset, broker_ids=[broker_a.id], analyses=[SUMMARY])

    assert {"status": result.calculation_status, "TRANSFER_PAIR_MISSING": "TRANSFER_PAIR_MISSING" in _issue_codes(result)} == {"status": "FAILED", "TRANSFER_PAIR_MISSING": True}


def _leg_columns(leg: Transaction) -> dict:
    return {
        "type": leg.type,
        "date": leg.date,
        "quantity": leg.quantity,
        "amount": leg.amount,
        "currency": leg.currency,
        "cost_basis_override": leg.cost_basis_override,
        "cost_basis_currency": leg.cost_basis_currency,
        "related_transaction_id": leg.related_transaction_id,
    }


@pytest.mark.asyncio
async def test_r9_guard_the_boundary_reading_never_touches_the_orm_rows(session):
    """R9 — GUARD (green today and after): the reading builds detached copies. After R2's analysis (U filtering A) A's
    leg is still a TRANSFER pointing at B's leg, with no cost basis, B's leg still points back with its 100 EUR, every
    column of both is as written, and the session holds no dirty and no new object.
    """
    book = await seed_l1(session)
    columns_before = {"A's leg": _leg_columns(book.out_leg), "B's leg": _leg_columns(book.in_leg)}
    assert not session.dirty and not session.new  # precondition: the book is flushed

    await _analysis(session, book.owner, book.asset, broker_ids=[book.broker_a.id], analyses=[SUMMARY, EVENTS])

    assert {
        "A's leg": {name: getattr(book.out_leg, name) for name in ("type", "related_transaction_id", "cost_basis_override")},
        "columns": {"A's leg": _leg_columns(book.out_leg), "B's leg": _leg_columns(book.in_leg)},
        "dirty": list(session.dirty),
        "new": list(session.new),
    } == {
        "A's leg": {"type": TransactionType.TRANSFER, "related_transaction_id": book.in_leg.id, "cost_basis_override": None},
        "columns": columns_before,
        "dirty": [],
        "new": [],
    }


@pytest.mark.asyncio
async def test_r10_guard_a_pair_inside_the_filter_stays_a_real_transfer(session):
    """R10 — GUARD (green today and after): U owns A, B and an unrelated C, and filters A and B. The pair is inside the
    scope — a real transfer (TRANSFER_DEPART, TRANSFER_ARRIVE), no ADJUSTMENT_* event —, one lot, A's BUY, 6 open.
    COMPLETE, no issue.
    """
    book = await seed_l1(session)
    await new_broker(session, "C", book.owner)

    result = await _analysis(session, book.owner, book.asset, broker_ids=[book.broker_a.id, book.broker_b.id], analyses=[SUMMARY, EVENTS])

    assert {
        "status": result.calculation_status,
        "issue codes": _issue_codes(result),
        "lots": _lots(result, "lot_id", "open_quantity"),
        "transfer kinds": sorted(_event_kinds(result) & _TRANSFER_KINDS),
        "adjustment kinds": sorted(_event_kinds(result) & _ADJUSTMENT_KINDS),
    } == {
        "status": "COMPLETE",
        "issue codes": [],
        "lots": [{"lot_id": book.buy.id, "open_quantity": D("6")}],
        "transfer kinds": ["TRANSFER_ARRIVE", "TRANSFER_DEPART"],
        "adjustment kinds": [],
    }


# --------------------------------------------------------------------------- #
# R11, R12
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_r11_a_partner_after_date_to_outside_the_scope_is_still_read_at_the_boundary(session):
    """R11 — OUT, the partner after ``date_to``: U filters A and reads up to 12 Jan, the departure day; B's leg (13 Jan)
    is outside the scope and after the window — only its pairing fields are read, never its date — so A's leg is a
    boundary leg: the BUY lot closes at 130, realized 300. COMPLETE.

    Today: FAILED — TRANSFER_PAIR_MISSING; the lot stays open, nothing realized.
    """
    book = await seed_l1(session)

    result = await _analysis(session, book.owner, book.asset, broker_ids=[book.broker_a.id], analyses=[SUMMARY], date_to=L1_DEPARTURE_DAY)

    assert {"status": result.calculation_status, "lots": _lots(result, "lot_id", "open_quantity", "realized_pnl")} == {
        "status": "COMPLETE",
        "lots": [{"lot_id": book.buy.id, "open_quantity": D("0"), "realized_pnl": D("300")}],
    }


@pytest.mark.asyncio
async def test_r12_a_legacy_arrival_without_cost_is_degraded_not_failed(session):
    """R12 — IN without a cost: L1 with B's leg written without a cost basis (legacy data). U filters B: the leg reads as
    a costless ADJUSTMENT-in — a lot of its own at 0 a unit, 6 open after the sale — and the analysis is DEGRADED on the
    existing MISSING_COST_BASIS, never FAILED, never TRANSFER_PAIR_MISSING. The WAC analyses are asked for because
    MISSING_COST_BASIS comes from the average-cost lines (``LotsAnalysisService._report_gaps``), as V-3's orphan reads
    it (``test_orphan_transfer_after_broker_delete.py``).

    Today: FAILED — TRANSFER_PAIR_MISSING and FIFO_SOURCE_QUANTITY_MISSING beside MISSING_COST_BASIS; no lot.
    """
    book = await seed_l1(session, in_leg_cost=None)

    result = await _analysis(
        session,
        book.owner,
        book.asset,
        broker_ids=[book.broker_b.id],
        analyses=[SUMMARY, LotAnalysisType.BROKER_WAC_HISTORY, LotAnalysisType.CUMULATIVE_WAC_HISTORY],
    )

    codes = _issue_codes(result)
    assert {
        "status": result.calculation_status,
        "MISSING_COST_BASIS": "MISSING_COST_BASIS" in codes,
        "TRANSFER_PAIR_MISSING": "TRANSFER_PAIR_MISSING" in codes,
        "lots": _lots(result, "lot_id", "opening_unit_price", "open_quantity"),
    } == {
        "status": "DEGRADED",
        "MISSING_COST_BASIS": True,
        "TRANSFER_PAIR_MISSING": False,
        "lots": [{"lot_id": book.in_leg.id, "opening_unit_price": D("0"), "open_quantity": D("6")}],
    }
