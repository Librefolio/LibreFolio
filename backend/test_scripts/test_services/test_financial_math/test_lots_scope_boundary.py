"""J-10, decision N76 — the transfers read at the broker-scope boundary: the pure reading and the engine's own-cost handover.

Workstream J «Numeri e analisi», release 1.3. Pure: ``read_transfers_at_scope_boundary`` and ``partner_ids_to_load`` on
ORM-free stand-ins of ``Transaction`` rows (``SimpleNamespace`` with the model's attributes, ``type`` a
``TransactionType`` member as the ORM loads it), and ``run_fifo_lot_engine`` on hand-written ``FifoInputTransaction``
rows — no DB, no server, no FX. The service-level reds are in ``test_financial/test_lots_transfer_scope_boundary.py``.

THE RULES (decision N76, coordinator 17/10; home ``backend/app/services/financial_math/lots/scope_boundary.py``, new):

1. A TRANSFER leg of the scope is a BOUNDARY LEG when its partner (``related_transaction_id``) exists, sits at a broker
   OUTSIDE the scope and pairs back — the checks of ``FifoLotEngine._resolve_transfer_pair``: partner type TRANSFER,
   ``partner.related_transaction_id == leg.id``, same asset, opposite signs, same absolute quantity. Otherwise the row
   comes back as it is — the same object — and the engine still says TRANSFER_PAIR_MISSING.
2. IN (positive leg): a detached ``FifoInputTransaction`` ADJUSTMENT-in at the leg's OWN ``cost_basis_override`` /
   ``cost_basis_currency`` — the Auto cost the receiving leg carries — opening its lot on the leg's day.
3. OUT (negative leg): an ADJUSTMENT-out at the market of its own day — ``price_series.resolve(leg.date).unit_price``
   divided by ``quote_base_quantity``, in the mark's currency. With no observation on or before that day the copy has
   no cost and ``hands_over_at_own_cost=True``: the engine closes each fragment at its own FIFO cost (realized 0).
4. Of the partner only the pairing fields are read (``TransferPartner``: id, broker, asset, type, quantity, link). The
   copies have type ADJUSTMENT, no link, amount 0; the input rows are never mutated; the rows that are not boundary
   legs come back as the same objects, in the same order.
5. ``FifoInputTransaction.from_transaction`` hands a ``FifoInputTransaction`` back as it is, so the new flag survives
   ``build_engine_transactions`` (``financial_math/lots/economic_events.py``).

Today (base ``ba63b7b24``): the module does not exist — ModuleNotFoundError — and ``FifoInputTransaction`` has no
``hands_over_at_own_cost`` — TypeError. The module is imported inside each test (``_scope_boundary``), so that the
engine GUARD at the bottom — a costless ADJUSTMENT-out handed over at 0, green today and after — is collected and runs.
"""

import dataclasses
import importlib
from datetime import date
from decimal import Decimal
from types import ModuleType, SimpleNamespace

import pytest

from backend.app.db.models import TransactionType
from backend.app.services.financial_math.fifo.engine import run_fifo_lot_engine
from backend.app.services.financial_math.fifo.models import FifoEngineResult, FifoInputTransaction, ReferencePriceResolution
from backend.app.services.financial_math.price_marks import AssetPriceSeries, build_asset_price_series

D = Decimal
ASSET_ID = 7310
OTHER_ASSET_ID = 7311
BROKER_A = 1  # the sender
BROKER_B = 2  # the receiver
BROKER_C = 3  # another sender, outside every scope below
# Ledger L1's closes (EUR): the mark of the departure day, 12 Jan, is 130.
L1_PRICES = (("2025-01-10", "100", "EUR"), ("2025-01-11", "120", "EUR"), ("2025-01-12", "130", "EUR"), ("2025-01-13", "130", "EUR"), ("2025-01-14", "140", "EUR"), ("2025-01-15", "150", "EUR"))


def _scope_boundary() -> ModuleType:
    """The module under test, imported per test: before J-10 it does not exist, and a module-level import would make the
    engine GUARD below a collection error instead of a green."""
    return importlib.import_module("backend.app.services.financial_math.lots.scope_boundary")


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #


def _row(
    tx_id: int,
    tx_type: TransactionType,
    quantity: str,
    *,
    on: str,
    broker_id: int,
    related: int | None = None,
    amount: str = "0",
    currency: str | None = "EUR",
    cost: str | None = None,
    cost_currency: str | None = None,
    asset_id: int = ASSET_ID,
) -> SimpleNamespace:
    """An ORM-free stand-in of a ``Transaction`` row, with the attributes the lots analysis reads from one."""
    return SimpleNamespace(
        id=tx_id,
        broker_id=broker_id,
        asset_id=asset_id,
        date=date.fromisoformat(on),
        type=tx_type,
        quantity=D(quantity),
        amount=D(amount),
        currency=currency,
        cost_basis_override=None if cost is None else D(cost),
        cost_basis_currency=cost_currency,
        related_transaction_id=related,
    )


def _partner(sb: ModuleType, partner_id: int, *, broker_id: int, quantity: str, related: int | None, tx_type: str = "TRANSFER", asset_id: int = ASSET_ID):
    return sb.TransferPartner(id=partner_id, broker_id=broker_id, asset_id=asset_id, type=tx_type, quantity=D(quantity), related_transaction_id=related)


def _series(*rows: tuple[str, str, str], quote_base_quantity: int = 1) -> AssetPriceSeries:
    """The lots' unified price resolver, fed price rows only (a TRANSFER or an ADJUSTMENT is never an observation)."""
    return build_asset_price_series(
        price_rows=[(date.fromisoformat(day), D(close), currency) for day, close, currency in rows],
        transactions=[],
        split_linked_tx_ids=set(),
        asset_currency="EUR",
        quote_base_quantity=quote_base_quantity,
    )


def _copy(leg: SimpleNamespace, *, cost: Decimal | None, cost_currency: str | None, own_cost: bool) -> FifoInputTransaction:
    """The detached ADJUSTMENT a boundary leg reads as: the leg's id, broker, asset, day, quantity and currency; no link, amount 0."""
    return FifoInputTransaction(
        id=leg.id,
        broker_id=leg.broker_id,
        asset_id=leg.asset_id,
        date=leg.date,
        type="ADJUSTMENT",
        quantity=leg.quantity,
        amount=D("0"),
        currency=leg.currency,
        cost_basis_override=cost,
        cost_basis_currency=cost_currency,
        related_transaction_id=None,
        hands_over_at_own_cost=own_cost,
    )


def _as_read(reading_rows: list, input_rows: list) -> list:
    """Each row of a reading: ``"input row i"`` when it is that very input object (identity), otherwise the row itself."""
    return [next((f"input row {index}" for index, row in enumerate(input_rows) if out is row), out) for out in reading_rows]


def _columns(row: SimpleNamespace) -> dict:
    return dict(vars(row))


# --------------------------------------------------------------------------- #
# The reading
# --------------------------------------------------------------------------- #


def test_an_incoming_leg_from_outside_the_scope_reads_as_an_adjustment_in_at_its_own_cost():
    """Rules 1, 2: B, read alone, receives 10 from A. The leg reads as an ADJUSTMENT-in of 10 on its own day at ITS cost
    basis, 100 EUR a unit (never a figure of the partner); the sale beside it is the same object; legs = {leg: IN}.

    Today: ModuleNotFoundError — ``financial_math/lots/scope_boundary.py`` does not exist.
    """
    sb = _scope_boundary()
    arrival = _row(201, TransactionType.TRANSFER, "10", on="2025-01-13", broker_id=BROKER_B, related=102, currency=None, cost="100", cost_currency="EUR")
    sale = _row(202, TransactionType.SELL, "-4", on="2025-01-15", broker_id=BROKER_B, amount="600")
    rows = [arrival, sale]

    reading = sb.read_transfers_at_scope_boundary(
        rows,
        partners={102: _partner(sb, 102, broker_id=BROKER_A, quantity="-10", related=201)},
        scope_broker_ids={BROKER_B},
        price_series=_series(*L1_PRICES),
        quote_base_quantity=1,
    )

    assert {"rows": _as_read(reading.transactions, rows), "legs": reading.legs} == {
        "rows": [_copy(arrival, cost=D("100"), cost_currency="EUR", own_cost=False), "input row 1"],
        "legs": {201: sb.BoundaryLeg(transaction_id=201, direction="IN")},
    }


def test_an_outgoing_leg_to_outside_the_scope_reads_as_an_adjustment_out_at_the_market_of_its_day():
    """Rules 1, 3: A, read alone, sends 10 to B on 12 Jan. The leg reads as an ADJUSTMENT-out of 10 at the mark of
    12 Jan, 130 EUR a unit — the scope realizes market − FIFO cost —, no own-cost flag; the BUY is the same object.

    Today: ModuleNotFoundError — ``financial_math/lots/scope_boundary.py`` does not exist.
    """
    sb = _scope_boundary()
    purchase = _row(101, TransactionType.BUY, "10", on="2025-01-10", broker_id=BROKER_A, amount="-1000")
    departure = _row(102, TransactionType.TRANSFER, "-10", on="2025-01-12", broker_id=BROKER_A, related=201)
    rows = [purchase, departure]

    reading = sb.read_transfers_at_scope_boundary(
        rows,
        partners={201: _partner(sb, 201, broker_id=BROKER_B, quantity="10", related=102)},
        scope_broker_ids={BROKER_A},
        price_series=_series(*L1_PRICES),
        quote_base_quantity=1,
    )

    assert {"rows": _as_read(reading.transactions, rows), "legs": reading.legs} == {
        "rows": ["input row 0", _copy(departure, cost=D("130"), cost_currency="EUR", own_cost=False)],
        "legs": {102: sb.BoundaryLeg(transaction_id=102, direction="OUT")},
    }


def test_the_outgoing_mark_is_brought_to_the_unit_by_quote_base_quantity():
    """Rule 3: a bond quoted per 100 units, close 13000 on the departure day: the leg leaves at 13000 / 100 = 130 a unit.

    Today: ModuleNotFoundError — ``financial_math/lots/scope_boundary.py`` does not exist.
    """
    sb = _scope_boundary()
    departure = _row(102, TransactionType.TRANSFER, "-10", on="2025-01-12", broker_id=BROKER_A, related=201)

    reading = sb.read_transfers_at_scope_boundary(
        [departure],
        partners={201: _partner(sb, 201, broker_id=BROKER_B, quantity="10", related=102)},
        scope_broker_ids={BROKER_A},
        price_series=_series(("2025-01-12", "13000", "EUR"), quote_base_quantity=100),
        quote_base_quantity=100,
    )

    assert {"rows": reading.transactions, "legs": reading.legs} == {
        "rows": [_copy(departure, cost=D("130"), cost_currency="EUR", own_cost=False)],
        "legs": {102: sb.BoundaryLeg(transaction_id=102, direction="OUT")},
    }


def test_the_outgoing_mark_is_the_resolvers_carried_mark_in_its_own_currency():
    """Rule 3: the mark is whatever the resolver gives on the leg's day — here the last close, 125 USD on 10 Jan,
    carried to 12 Jan — and the copy's cost is in the MARK's currency, USD, not in the leg's EUR.

    Today: ModuleNotFoundError — ``financial_math/lots/scope_boundary.py`` does not exist.
    """
    sb = _scope_boundary()
    departure = _row(102, TransactionType.TRANSFER, "-10", on="2025-01-12", broker_id=BROKER_A, related=201, currency="EUR")

    reading = sb.read_transfers_at_scope_boundary(
        [departure],
        partners={201: _partner(sb, 201, broker_id=BROKER_B, quantity="10", related=102)},
        scope_broker_ids=[BROKER_A],  # any collection of broker ids
        price_series=_series(("2025-01-10", "125", "USD")),
        quote_base_quantity=1,
    )

    assert {"rows": reading.transactions, "legs": reading.legs} == {
        "rows": [_copy(departure, cost=D("125"), cost_currency="USD", own_cost=False)],
        "legs": {102: sb.BoundaryLeg(transaction_id=102, direction="OUT")},
    }


@pytest.mark.parametrize(
    "price_rows",
    [
        pytest.param((), id="no-price-at-all"),
        pytest.param((("2025-01-14", "140", "EUR"),), id="first-price-after-the-leg"),
    ],
)
def test_an_outgoing_leg_with_no_observation_on_or_before_its_day_hands_its_units_over_at_their_own_cost(price_rows):
    """Rule 3: no observation on or before 12 Jan — the resolver has no mark — so the copy carries no cost and
    ``hands_over_at_own_cost=True``: each unit leaves at its own FIFO cost. Still a boundary leg (legs = {leg: OUT}).

    Today: ModuleNotFoundError — ``financial_math/lots/scope_boundary.py`` does not exist.
    """
    sb = _scope_boundary()
    departure = _row(102, TransactionType.TRANSFER, "-10", on="2025-01-12", broker_id=BROKER_A, related=201)

    reading = sb.read_transfers_at_scope_boundary(
        [departure],
        partners={201: _partner(sb, 201, broker_id=BROKER_B, quantity="10", related=102)},
        scope_broker_ids={BROKER_A},
        price_series=_series(*price_rows),
        quote_base_quantity=1,
    )

    assert {"rows": reading.transactions, "legs": reading.legs} == {
        "rows": [_copy(departure, cost=None, cost_currency=None, own_cost=True)],
        "legs": {102: sb.BoundaryLeg(transaction_id=102, direction="OUT")},
    }


# Each case: the departing leg's own link, the partners the caller found, the scope. The partner of every case but the
# last would pair back from broker B if it were not for the one thing the case changes.
_PAIRED_BACK = {"partner_id": 201, "broker_id": BROKER_B, "quantity": "10", "related": 102}


@pytest.mark.parametrize(
    ("leg_related", "partner", "scope"),
    [
        pytest.param(201, None, {BROKER_A}, id="partner-absent"),
        pytest.param(201, _PAIRED_BACK, {BROKER_A, BROKER_B}, id="partner-broker-in-scope"),
        pytest.param(201, {**_PAIRED_BACK, "tx_type": "ADJUSTMENT"}, {BROKER_A}, id="partner-not-a-transfer"),
        pytest.param(201, {**_PAIRED_BACK, "related": None}, {BROKER_A}, id="partner-not-pointing-back"),
        pytest.param(201, {**_PAIRED_BACK, "related": 999}, {BROKER_A}, id="partner-pointing-elsewhere"),
        pytest.param(201, {**_PAIRED_BACK, "asset_id": OTHER_ASSET_ID}, {BROKER_A}, id="partner-of-another-asset"),
        pytest.param(201, {**_PAIRED_BACK, "quantity": "-10"}, {BROKER_A}, id="partner-of-the-same-sign"),
        pytest.param(201, {**_PAIRED_BACK, "quantity": "8"}, {BROKER_A}, id="partner-of-another-quantity"),
        pytest.param(None, _PAIRED_BACK, {BROKER_A}, id="leg-without-a-link"),
    ],
)
def test_a_leg_whose_partner_does_not_pair_back_from_outside_the_scope_comes_back_as_it_is(leg_related, partner, scope):
    """Rule 1: unless the partner exists, sits outside the scope and pairs back (TRANSFER, pointing back, same asset,
    opposite sign, same absolute quantity), the leg is no boundary leg: every row comes back as the same object and
    ``legs`` is empty — the engine will say TRANSFER_PAIR_MISSING, as today. The prices are L1's, so a mark exists: a
    wrong reading would show. A leg without a link is never looked up, even when some partner points at it.

    Today: ModuleNotFoundError — ``financial_math/lots/scope_boundary.py`` does not exist.
    """
    sb = _scope_boundary()
    purchase = _row(101, TransactionType.BUY, "10", on="2025-01-10", broker_id=BROKER_A, amount="-1000")
    departure = _row(102, TransactionType.TRANSFER, "-10", on="2025-01-12", broker_id=BROKER_A, related=leg_related)
    rows = [purchase, departure]
    partners = {} if partner is None else {partner["partner_id"]: _partner(sb, **partner)}

    reading = sb.read_transfers_at_scope_boundary(rows, partners=partners, scope_broker_ids=scope, price_series=_series(*L1_PRICES), quote_base_quantity=1)

    assert {"rows": _as_read(reading.transactions, rows), "legs": reading.legs} == {"rows": ["input row 0", "input row 1"], "legs": {}}


def test_rows_come_back_in_order_the_others_as_the_same_objects_and_the_input_untouched():
    """Rules 1–4 together: A receives 5 from C (cost basis 90) and sends 10 to B, between a BUY and a SELL. The reading
    keeps the order, returns the BUY and the SELL as the same objects, puts a detached copy in each leg's place
    (IN at its own 90, OUT at the 130 of 12 Jan), names both legs — and leaves the input list and its rows as they were.

    Today: ModuleNotFoundError — ``financial_math/lots/scope_boundary.py`` does not exist.
    """
    sb = _scope_boundary()
    purchase = _row(101, TransactionType.BUY, "10", on="2025-01-10", broker_id=BROKER_A, amount="-1000")
    arrival = _row(103, TransactionType.TRANSFER, "5", on="2025-01-11", broker_id=BROKER_A, related=301, cost="90", cost_currency="EUR")
    departure = _row(102, TransactionType.TRANSFER, "-10", on="2025-01-12", broker_id=BROKER_A, related=201)
    sale = _row(104, TransactionType.SELL, "-2", on="2025-01-14", broker_id=BROKER_A, amount="280")
    rows = [purchase, arrival, departure, sale]
    rows_before = list(rows)
    columns_before = [_columns(row) for row in rows]

    reading = sb.read_transfers_at_scope_boundary(
        rows,
        partners={
            201: _partner(sb, 201, broker_id=BROKER_B, quantity="10", related=102),
            301: _partner(sb, 301, broker_id=BROKER_C, quantity="-5", related=103),
        },
        scope_broker_ids={BROKER_A},
        price_series=_series(*L1_PRICES),
        quote_base_quantity=1,
    )

    assert {
        "rows": _as_read(reading.transactions, rows),
        "legs": reading.legs,
        "input list": _as_read(rows, rows_before),
        "input rows": [_columns(row) for row in rows],
    } == {
        "rows": [
            "input row 0",
            _copy(arrival, cost=D("90"), cost_currency="EUR", own_cost=False),
            _copy(departure, cost=D("130"), cost_currency="EUR", own_cost=False),
            "input row 3",
        ],
        "legs": {103: sb.BoundaryLeg(transaction_id=103, direction="IN"), 102: sb.BoundaryLeg(transaction_id=102, direction="OUT")},
        "input list": ["input row 0", "input row 1", "input row 2", "input row 3"],
        "input rows": columns_before,
    }


def test_partner_ids_to_load_names_the_partners_the_transfers_miss_and_nothing_else():
    """``partner_ids_to_load``: the related ids named by the TRANSFER rows and not held by the list — not the link of a
    pair the list holds whole, not a TRANSFER without a link, not the link of a row of another type.

    Today: ModuleNotFoundError — ``financial_math/lots/scope_boundary.py`` does not exist.
    """
    sb = _scope_boundary()
    rows = [
        _row(101, TransactionType.BUY, "10", on="2025-01-10", broker_id=BROKER_A, amount="-1000"),
        _row(102, TransactionType.TRANSFER, "-10", on="2025-01-12", broker_id=BROKER_A, related=201),  # partner elsewhere
        _row(105, TransactionType.TRANSFER, "-3", on="2025-01-12", broker_id=BROKER_A, related=106),  # a pair held whole
        _row(106, TransactionType.TRANSFER, "3", on="2025-01-12", broker_id=BROKER_B, related=105),
        _row(107, TransactionType.TRANSFER, "-1", on="2025-01-13", broker_id=BROKER_A),  # no link
        _row(108, TransactionType.ADJUSTMENT, "2", on="2025-01-13", broker_id=BROKER_A, related=999),  # not a TRANSFER
        _row(109, TransactionType.TRANSFER, "4", on="2025-01-14", broker_id=BROKER_B, related=301),  # partner elsewhere
    ]

    assert sb.partner_ids_to_load(rows) == {201, 301}


def test_a_partner_carries_its_pairing_fields_only_and_the_reading_values_are_frozen():
    """Rule 4: of the partner only the pairing fields exist to be read — id, broker, asset, type, quantity, link —,
    never an amount or a cost; ``TransferPartner`` and ``BoundaryLeg`` are frozen dataclasses.

    Today: ModuleNotFoundError — ``financial_math/lots/scope_boundary.py`` does not exist.
    """
    sb = _scope_boundary()
    partner = _partner(sb, 201, broker_id=BROKER_B, quantity="10", related=102)
    leg = sb.BoundaryLeg(transaction_id=102, direction="OUT")

    assert [field.name for field in dataclasses.fields(sb.TransferPartner)] == ["id", "broker_id", "asset_id", "type", "quantity", "related_transaction_id"]
    assert [field.name for field in dataclasses.fields(sb.BoundaryLeg)] == ["transaction_id", "direction"]
    with pytest.raises(dataclasses.FrozenInstanceError):
        partner.quantity = D("8")
    with pytest.raises(dataclasses.FrozenInstanceError):
        leg.direction = "IN"


def test_from_transaction_hands_a_fifo_input_transaction_back_as_it_is():
    """Rule 5: a ``FifoInputTransaction`` given to ``from_transaction`` comes back as it is — itself, or an equal object
    — so a copy flagged ``hands_over_at_own_cost`` keeps the flag through ``build_engine_transactions``.

    Today: TypeError — ``FifoInputTransaction`` has no ``hands_over_at_own_cost``. (And ``from_transaction`` rebuilds
    its argument field by field, which would drop the new field.)
    """
    flagged = FifoInputTransaction(id=13, broker_id=BROKER_A, asset_id=ASSET_ID, date=date(2025, 1, 12), type="ADJUSTMENT", quantity=D("-10"), hands_over_at_own_cost=True)

    normalized = FifoInputTransaction.from_transaction(flagged)

    assert normalized is flagged or (normalized == flagged and normalized.hands_over_at_own_cost is True)


# --------------------------------------------------------------------------- #
# The engine: hands_over_at_own_cost
# --------------------------------------------------------------------------- #


def _exact_reference(_asset_id: int, _day: date) -> ReferencePriceResolution:
    """A reference price for the ADJUSTMENT-in lots, so that a clean replay reads COMPLETE (the value is not the subject)."""
    return ReferencePriceResolution(price=D("100"), source="exact")


def _two_lots_then(handover: FifoInputTransaction) -> FifoEngineResult:
    """Broker A holds two lots opened by ADJUSTMENT-ins with a cost — 5 at 100 EUR on 10 Jan, 5 at 120 EUR on 11 Jan —
    and hands all 10 over on 12 Jan with ``handover``."""
    lots = [
        FifoInputTransaction(id=11, broker_id=BROKER_A, asset_id=ASSET_ID, date=date(2025, 1, 10), type="ADJUSTMENT", quantity=D("5"), cost_basis_override=D("100"), cost_basis_currency="EUR"),
        FifoInputTransaction(id=12, broker_id=BROKER_A, asset_id=ASSET_ID, date=date(2025, 1, 11), type="ADJUSTMENT", quantity=D("5"), cost_basis_override=D("120"), cost_basis_currency="EUR"),
    ]
    return run_fifo_lot_engine([*lots, handover], {BROKER_A: False}, reference_price_lookup=_exact_reference, target_currency="EUR")


def _closures_and_lots(result: FifoEngineResult) -> dict:
    return {
        "status": result.analysis_status,
        # (lot, reason, quantity, close unit price, realized, proceeds)
        "closures": sorted((c.lot_id, c.close_reason, c.quantity, c.close_unit_price, c.realized_pnl, c.proceeds) for c in result.closures),
        # (lot, open, realized quantity, realized P&L, cumulative proceeds)
        "lots": sorted((lot.lot_id, lot.open_quantity, lot.realized_quantity, lot.realized_pnl, lot.cumulative_proceeds) for lot in result.lots),
    }


def test_an_adjustment_out_flagged_hands_each_fragment_over_at_its_own_fifo_cost():
    """Rule 3, the engine's half: an ADJUSTMENT −10 with ``hands_over_at_own_cost=True`` and no cost closes each
    fragment at ITS OWN FIFO cost — 5 at 100 and 5 at 120, not one average —: realized 0 and 0, proceeds 500 and 600,
    both lots fully realized, close reason ADJUSTMENT_OUT.

    Today: TypeError — ``FifoInputTransaction.__init__`` has no ``hands_over_at_own_cost``.
    """
    result = _two_lots_then(FifoInputTransaction(id=13, broker_id=BROKER_A, asset_id=ASSET_ID, date=date(2025, 1, 12), type="ADJUSTMENT", quantity=D("-10"), hands_over_at_own_cost=True))

    assert _closures_and_lots(result) == {
        "status": "COMPLETE",
        "closures": [(11, "ADJUSTMENT_OUT", D("5"), D("100"), D("0"), D("500")), (12, "ADJUSTMENT_OUT", D("5"), D("120"), D("0"), D("600"))],
        "lots": [(11, D("0"), D("5"), D("0"), D("500")), (12, D("0"), D("5"), D("0"), D("600"))],
    }


def test_guard_an_unflagged_adjustment_out_without_cost_still_hands_its_units_over_at_zero():
    """GUARD (green today and after): the same ADJUSTMENT −10 without the flag and without a cost is today's quantity
    correction — every fragment closes at 0: realized −500 and −600, proceeds 0. The flag defaults to False and changes
    nothing for a row that does not carry it.
    """
    result = _two_lots_then(FifoInputTransaction(id=13, broker_id=BROKER_A, asset_id=ASSET_ID, date=date(2025, 1, 12), type="ADJUSTMENT", quantity=D("-10")))

    assert _closures_and_lots(result) == {
        "status": "COMPLETE",
        "closures": [(11, "ADJUSTMENT_OUT", D("5"), D("0"), D("-500"), D("0")), (12, "ADJUSTMENT_OUT", D("5"), D("0"), D("-600"), D("0"))],
        "lots": [(11, D("0"), D("5"), D("-500"), D("0")), (12, D("0"), D("5"), D("-600"), D("0"))],
    }
