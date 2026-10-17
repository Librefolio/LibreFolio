"""
N2 — which rows need a cost basis, and when a batch holds them to it (workstream W, release 1.3).

The rule. A TRANSFER's receiving leg (quantity > 0) and an ADJUSTMENT adding quantity need a cost basis: a
``cost_basis_override``, or ``cost_basis_mode`` ``auto``/``auto-detail`` (the batch then writes the average itself).
``TX_TYPE_METADATA`` says so — TRANSFER ``cost_basis_pair = ["forbidden", "required_qty_pos"]``, ADJUSTMENT
``cost_basis_mode = "required_qty_pos"`` — and every batch path enforces it in ``validate_cost_basis``
(``batch_costs.py``): the issue ``costBasisRequired`` on ``cost_basis_override``, and the batch does not commit.

What N2 changes:

1. The rule is READ from ``TX_TYPE_METADATA`` — pair types ``cost_basis_pair[1 if quantity > 0 else 0]``, the
   others ``cost_basis_mode``; ``required_qty_pos`` with quantity > 0 means required — instead of being written by
   hand in ``TransactionValidationMixin._requires_cost_basis`` (``validation.py``).
2. An update is held to the rule only when it changes, compared with the stored row, the type, the quantity (its
   sign included), the cost (``cost_basis_override``, its currency, ``cost_basis_mode``) or the asset event link
   (``asset_event_id``: an ADJUSTMENT linked to a SPLIT takes its cost from the split's ratio, so the link stands
   for its cost). The comparison is on values, not on which keys the payload carries, so the app's diff payloads
   and a client sending the whole row are judged alike. Editing the notes (``description``, "Transaction notes") or
   the tags of a row an older version stored without a cost stays possible, and the row stays as it was: no repair.

Reds — fail before N2, pass after it:

- ``TestEditsOfARowStoredWithoutCost``: a notes-only or tags-only edit of a TRANSFER receiving leg (sent with its
  giving leg) or of an ADJUSTMENT +qty stored without a cost commits; today ``_check_update_cost_basis`` refuses any
  update of such a row. Plus a date-only edit, DERIVED from the same decision (a date is none of the changes the
  rule reads): it is what tells a cure that lists the changes that matter from one that lists the edits that are
  harmless.
- ``TestTheRuleReadsTheMetadata``: with an entry of ``TX_TYPE_METADATA`` patched in place, ``_requires_cost_basis``
  and a create follow the patch; today the hand-written rule ignores it.
- ``TestSplitLinkedAdjustment``: an update that only unlinks an ADJUSTMENT +qty linked to a SPLIT (stored without a
  cost by design), or re-links it to a PRICE_ADJUSTMENT, is refused. Not red before N2, which refused every update
  of that row, but red with the first N2 cure, whose ``cost_fields`` left the link out.

Guards — green before N2, and the cure must keep them green:

- ``TestCreatesNeedACost``: a create without a cost is refused, on its own row (index, field, params);
- ``TestUpdatesThatChangeWhatTheRuleReads``: a quantity change (a sign flip −5 → +5, or more units on a stored row
  without a cost), a type change into ADJUSTMENT, or ``cost_basis_mode: "manual"`` with no cost, is refused;
- ``TestEditsOfARowWithCost``: a notes-only or tags-only edit of a row that has its cost commits, cost untouched;
- ``TestAutoCost``: an Auto create with an average available commits, with that average written;
- ``TestPromoteOfARowStoredWithoutCost``: a promote that makes a stored ADJUSTMENT +5 without a cost the receiving
  leg of a TRANSFER stays refused when the same batch also edits that row's notes — today the update check refuses
  it, and ``_check_promoted_saved_cost_basis`` skips updated rows on the strength of that check;
- ``TestSplitLinkedAdjustment``: a notes-only or tags-only edit of the split-linked ADJUSTMENT commits, link and
  missing cost untouched; the same link changes made WITH a cost commit;
- ``TestTheRuleAgreesWithTheMetadata``: for every type and quantity sign, ``_requires_cost_basis`` says what the
  metadata says.

Not covered, on purpose:

- an update that REMOVES a cost, in N2: ``cost_basis_override: null`` is read as "unchanged" (``_apply_update_values``,
  ``batch_edits.py``), exactly like an absent key, until decision P5's cure makes it a removal where the type and side
  take a cost — ``TestDecisionP5AnExplicitNullEmptiesTheCost``, below;
- Auto with no average (P-1, ``auto_cost.py``) and SPLIT-linked ADJUSTMENTs: outside N2, unchanged.

Decision 47 (workstream W, release 1.3) — the giving leg of a TRANSFER, ``TestDecision47TheGivingLegOfATransfer``,
RED until its cure. J's CP-16 (``financial_math/fifo/engine.py``) reads a negative ADJUSTMENT carrying a
``cost_basis_override`` as units handed over at that cost; W's part writes that cost where a TRANSFER loses its giving
leg in a batch:

- a split of a TRANSFER pair hands its giving leg over at the Auto cost of the leg's OWN broker
  (``TransactionService._handover_cost``: its broker, up to its date, without itself), computed in the batch's WAC
  stage (``compute_wac_and_fx_issues``) after the other stages: an ADJUSTMENT −4 at ``source``'s 100 EUR — or 200 when
  the same batch adds a purchase before the move —, the receiving leg keeping its own cost. A cost an update of the
  same batch gives the giving leg stays (the coordinator's decision 4, 16/10: a guard, green today);
- a split whose giving leg's cost needs a conversion no rate gives is refused, on /commit and on /validate:
  ``WAC_FX_UNAVAILABLE`` on the split's index, ``ref_id`` the giving leg, ``field`` ``cost_basis_override``, params
  ``pairs`` and ``pair_details`` as for an Auto row;
- a promote of an ADJUSTMENT −4 carrying a cost and an ADJUSTMENT +4 into a TRANSFER takes the cost (and its currency)
  off the side whose new type takes none (``cost_basis_allowed``: the giving side); the receiving side keeps its own.

Why here: these are rules about where a batch writes or removes a cost basis — this file's subject, its ``World``
(``source`` holding 10 units at 100 EUR, the Auto cost), its stored pair (``_store``) and its vocabulary. The broker
deletion's side of decision 47 is pinned in ``test_broker_service.py`` (BR-U-073, 076, 078, 086–088), the lone legs a
1.2 deletion left in ``test_lone_transfer_legs.py``.

W-B69 (release 1.3; it blocks the release) — an Auto cost computed while skipping an unreadable row, the ``TestWB69…``
classes: W's half of it, RED until its cure but for the guards. A regression of W-B58: ``RealDecimal``
(``db/real_decimal.py``) reads a stored value that is no number — a text such as 'n/a', a REAL ±inf — as None instead of
raising. ``compute_wac_iterative`` (``portfolio_service.py``) still selects such a row — in SQLite 'n/a' is not NULL and
differs from 0 —, and ``cost_movement_from_transaction`` (``financial_math/average_cost.py``) skips it when its quantity
reads None, or takes a BUY whose amount reads None as a free acquisition: the Auto cost is computed without the row, or
lower, and saved for good. The cure (approved design): ``_auto_cost`` (``auto_cost.py``) raises
``UnreadablePoolError(count)`` when a row of its pool — the facade's filters, minus the rows left out — reads None in its
quantity, its amount, or a cost basis it stores (``cost_basis_override`` not NULL in SQL: the contract's addition of
17/10; a BUY's NULL cost basis is legitimate), ``count`` the number of such rows — a row unreadable in two columns counts
once —; and each caller refuses. That core — the guard in ``_auto_cost``, ``UnreadablePoolError``, the broker deletion
(``delete_by_broker``) and the lone legs — is the MF workstream's (the coordinator's assignment, 17/10), pinned in MF's own
``test_auto_cost_unreadable_pool.py``. W's half, the batch's, is pinned here:

- a batch's Auto row (a create or an update in ``auto`` or ``auto-detail``), on /commit and on /validate: one issue
  ``autoCostUnreadable`` on its operation and index, ``field`` ``cost_basis_override``, ``params`` ``{"count": N}``, and no
  transaction id anywhere in it (the pool may be another user's broker); nothing committed, nothing saved, nothing raised;
- the split of a TRANSFER pair whose giving leg's handover pool holds such a row: one ``autoCostUnreadable`` on the split's
  index, ``ref_id`` the giving leg (as ``wacFxUnavailable`` on a split); not committed, the pair intact;
- ``TXValidationCode.AUTO_COST_UNREADABLE`` exists and ``GET /transactions/types`` lists it; a gate, green today, holds
  every code to its ``transactions.errors.<code>`` message in EN, IT, FR and ES.

The pool is ``source``'s: the ``world``'s BUY (10 units for 1 000 EUR) and the row ``_plant`` adds a week later — a BUY of
10 units for 3 000 EUR, or an incoming row that takes a cost basis, an ADJUSTMENT +10 or a receiving TRANSFER +10 (its
giving leg on a third broker of the test's), stored at 300 EUR a unit —, its quantity, its amount or its cost basis then
overwritten with 'n/a' by raw SQL. Readable, either averages (1 000 + 3 000) / 20 = 200 EUR; today, with the quantity
unreadable the average is 1 000 / 10 = 100, with the BUY's amount or the stored cost basis unreadable 1 000 / 20 = 50 (a
free acquisition, or one of unknown cost entering at zero). The planted row lies before the move, so today a batch's
balance replay reads it among the balances before its first day, which skip a None, and never in its day-by-day loop,
where a None raises (an uncoded "Balance validation error").

W-B74 (approved design, its cure pending; its own reds in test_transaction_service.py) makes the replay refuse a broker
whose rows hold a quantity or an amount that reads None, at every date: ``ledgerUnreadable`` ``{"brokerId": id, "count":
N}`` at index -1. So a W-B69 batch that replays ``source`` while it holds such a row — creating or updating the pair,
splitting it — gets that issue beside ``autoCostUnreadable``: exactly two, contract updates RED until W-B74's cure. A
stored cost basis is read by no balance: those reds keep exactly one issue. The guards that recompute the receiving leg
alone replay ``dest`` only, and refuse nothing; the row of another asset on ``source``, under a batch that creates the
pair, is refused by the replay alone (``test_unreadable_row_of_another_asset_is_refused_by_the_replay_alone``).

Ownership. Every test builds its own asset and brokers under a unique marker, in a session rolled back at the end:
``execute_batch`` never commits (its caller does), so nothing reaches the lane's database. The two scaffolds that
change module state — an entry of ``TX_TYPE_METADATA``, ``SWAP_GROUPS`` — go through ``monkeypatch``, which puts
them back. W-B69's plants are raw SQL in the same session, rolled back with it.

Run: ``./dev.py test services transaction-cost-basis-rule`` (the action ``services_transaction_cost_basis_rule``); W-B69's
cases alone: ``./dev.py test services transaction-cost-basis-rule WB69``.
"""

import re
import sys
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

# Before any app module that reads DATABASE_URL: this lane's test database.
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import and_, bindparam, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.schemas.transactions.transactions as transaction_schemas
import backend.app.schemas.transactions.type_metadata as type_metadata
from backend.app.db.models import Asset, AssetEvent, AssetEventType, AssetType, Broker, FxConversionRoute, FxRate, Transaction, TransactionType
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions.batch import TXBatchResponse, TXValidationCode, TXValidationIssue
from backend.app.schemas.transactions.type_metadata import EVENT_TYPE_METADATA, TX_TYPE_METADATA, TXTypesResponse, cost_basis_allowed
from backend.app.services.portfolio_service import compute_wac_iterative
from backend.app.services.transactions.transaction_service import TransactionService
from backend.app.utils.datetime_utils import utcnow
from scripts.i18n_catalog import flatten, load_catalog

EUR = "EUR"
BUY_DAY = date(2025, 1, 6)
MOVE_DAY = date(2025, 2, 3)
BUY_QUANTITY = Decimal("10")
# The BUY pays 1 000 EUR for 10 units: 100 EUR is the source broker's average, the cost an Auto row receives.
UNIT_COST = Decimal("100")
TRANSFER_QUANTITY = Decimal("4")
ADJUSTMENT_QUANTITY = Decimal("5")
# A cost basis a row was saved with, distinct from the average so that "unchanged" cannot be confused with "recomputed".
STORED_COST = Currency(code=EUR, amount=Decimal("42"))
STORED_TAGS = "n2-stored"
EDITED_TAGS = ["n2-edited"]
COST_BASIS_REQUIRED = TXValidationCode.COST_BASIS_REQUIRED.value

SHAPES = ("transfer_in", "adjustment_in")
SHAPE_LABELS = {
    "transfer_in": "TRANSFER receiving leg (quantity > 0, edited together with its giving leg)",
    "adjustment_in": "ADJUSTMENT adding quantity",
}
EDITS = ("notes", "tags")

SPLIT_RATIO = Decimal("2")
# A 2:1 split doubles the 10 units the BUY gave the source broker: the ADJUSTMENT that realizes it adds 10 more.
SPLIT_QUANTITY = BUY_QUANTITY * (SPLIT_RATIO - 1)
LINK_CHANGES = ("unlink", "relink-price-adjustment")

# Decision 47 — the giving leg of a TRANSFER (TestDecision47TheGivingLegOfATransfer).
WAC_FX_UNAVAILABLE = TXValidationCode.WAC_FX_UNAVAILABLE.value
PYG = "PYG"  # a currency no rate and no route reaches, proven before use
# 10 units bought in PYG a week before the EUR BUY: the EUR BUY stays the last acquisition, so the average is in EUR
# and PYG/EUR is the conversion it misses.
PYG_DAY = BUY_DAY - timedelta(days=7)
PYG_PAID = Decimal("-50000")
# 10 more units at 300 EUR that a split's own batch buys before the move: with the BUY's 1 000 for 10, the pool of
# the giving leg averages (1 000 + 3 000) / 20 = 200 EUR.
LATER_BUY_DAY = BUY_DAY + timedelta(days=7)
LATER_BUY_PAID = Decimal("-3000")


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def engine():
    """The app's async engine, on this lane's test database."""
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    """One session per test, rolled back at the end: ``execute_batch`` never commits, its caller does."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()


@dataclass
class World:
    """One test's own data: an asset, the broker that holds it, the broker that receives it."""

    session: AsyncSession
    marker: str
    asset: Asset
    source: Broker
    dest: Broker


@pytest_asyncio.fixture
async def world(session) -> World:
    """An asset and two brokers of this test alone, and the BUY that gives ``source`` 10 units at 100 EUR.

    The BUY is what lets ``source`` give units away without going short — the balance replay of every batch re-reads
    those days — and what an Auto cost averages. Both brokers allow a cash overdraft (the BUY spends cash no DEPOSIT
    brought) and refuse shorting, as a broker does by default.
    """
    marker = f"N2-cost-rule {uuid.uuid4().hex}"
    now = utcnow()
    asset = Asset(display_name=f"{marker} asset", asset_type=AssetType.STOCK, currency=EUR, created_at=now, updated_at=now)
    source = Broker(name=f"{marker} source", description="N2 cost basis rule: the broker units leave", allow_cash_overdraft=True, allow_asset_shorting=False, created_at=now, updated_at=now)
    dest = Broker(name=f"{marker} dest", description="N2 cost basis rule: the broker units reach", allow_cash_overdraft=True, allow_asset_shorting=False, created_at=now, updated_at=now)
    session.add_all([asset, source, dest])
    await session.flush()
    session.add(
        Transaction(
            broker_id=source.id,
            asset_id=asset.id,
            type=TransactionType.BUY,
            date=BUY_DAY,
            quantity=BUY_QUANTITY,
            amount=-(BUY_QUANTITY * UNIT_COST),
            currency=EUR,
            description=f"{marker} buy",
            created_at=now,
            updated_at=now,
        )
    )
    await session.flush()
    return World(session=session, marker=marker, asset=asset, source=source, dest=dest)


# ============================================================================
# HELPERS
# ============================================================================


def _stored_row(
    world: World,
    *,
    broker: Broker,
    tx_type: TransactionType,
    quantity: Decimal,
    cost: Currency | None = None,
    amount: Decimal = Decimal("0"),
    currency: str | None = None,
) -> Transaction:
    """A row as the database holds it, written without the batch and its checks.

    Without ``cost`` it is the shape ``test_db/legacy_cost_rows.py`` writes for data an older version left behind:
    amount 0, no currency, no cost basis, no asset event. Every row of a test carries the same description and tags,
    as both legs of a pair must.
    """
    now = utcnow()
    return Transaction(
        broker_id=broker.id,
        asset_id=world.asset.id,
        type=tx_type,
        date=MOVE_DAY,
        quantity=quantity,
        amount=amount,
        currency=currency,
        cost_basis_override=cost.amount if cost is not None else None,
        cost_basis_currency=cost.code if cost is not None else None,
        asset_event_id=None,
        description=f"{world.marker} stored",
        tags=STORED_TAGS,
        created_at=now,
        updated_at=now,
    )


@dataclass
class Stored:
    """A stored row that needs a cost basis, and the rows an edit of it sends.

    The receiving leg of a TRANSFER goes with its giving leg — a pair keeps one description and one set of tags, so
    the app edits both — and an ADJUSTMENT goes alone. ``subject_index`` is the subject's index in the edit.
    """

    subject: Transaction
    rows: list[Transaction]

    @property
    def subject_index(self) -> int:
        return next(index for index, row in enumerate(self.rows) if row is self.subject)


async def _store(world: World, shape: str, *, cost: Currency | None) -> Stored:
    """Store the row ``shape`` names — ``transfer_in`` (a linked pair source → dest) or ``adjustment_in`` (on dest)."""
    session = world.session
    if shape == "transfer_in":
        giving = _stored_row(world, broker=world.source, tx_type=TransactionType.TRANSFER, quantity=-TRANSFER_QUANTITY)
        receiving = _stored_row(world, broker=world.dest, tx_type=TransactionType.TRANSFER, quantity=TRANSFER_QUANTITY, cost=cost)
        session.add_all([giving, receiving])
        await session.flush()
        # A pair points both ways, and the ids exist only after the first flush (as legacy_cost_rows.py does it).
        giving.related_transaction_id = receiving.id
        receiving.related_transaction_id = giving.id
        await session.flush()
        return Stored(subject=receiving, rows=[giving, receiving])
    if shape == "adjustment_in":
        added = _stored_row(world, broker=world.dest, tx_type=TransactionType.ADJUSTMENT, quantity=ADJUSTMENT_QUANTITY, cost=cost)
        session.add(added)
        await session.flush()
        return Stored(subject=added, rows=[added])
    raise ValueError(f"unknown shape {shape!r}")


def _created_pair(world: World, *, cost_basis_mode: str | None = None) -> list[dict]:
    """A TRANSFER pair to create, source → dest, the receiving leg at index 1 and without a cost basis."""
    link_uuid = str(uuid.uuid4())
    giving = {"broker_id": world.source.id, "asset_id": world.asset.id, "type": "TRANSFER", "date": MOVE_DAY.isoformat(), "quantity": str(-TRANSFER_QUANTITY), "link_uuid": link_uuid}
    receiving = {"broker_id": world.dest.id, "asset_id": world.asset.id, "type": "TRANSFER", "date": MOVE_DAY.isoformat(), "quantity": str(TRANSFER_QUANTITY), "link_uuid": link_uuid}
    if cost_basis_mode is not None:
        receiving["cost_basis_mode"] = cost_basis_mode
    return [giving, receiving]


def _created_adjustment(world: World, *, broker: Broker, quantity: Decimal, cost_basis_mode: str | None = None) -> dict:
    """An ADJUSTMENT to create, without a cost basis."""
    created = {"broker_id": broker.id, "asset_id": world.asset.id, "type": "ADJUSTMENT", "date": MOVE_DAY.isoformat(), "quantity": str(quantity)}
    if cost_basis_mode is not None:
        created["cost_basis_mode"] = cost_basis_mode
    return created


async def _event(world: World, event_type: AssetEventType, value: Decimal) -> AssetEvent:
    """A manual event of the test's asset on ``MOVE_DAY`` (``provider_assignment_id`` None, as a user creates one)."""
    now = utcnow()
    event = AssetEvent(asset_id=world.asset.id, date=MOVE_DAY, type=event_type, value=value, currency=EUR, notes=f"{world.marker} {event_type.value}", created_at=now, updated_at=now)
    world.session.add(event)
    await world.session.flush()
    return event


async def _split_linked_adjustment(world: World) -> tuple[Transaction, AssetEvent]:
    """The ADJUSTMENT +10 that realizes a 2:1 SPLIT on ``source``, saved as the app saves it: created in Auto, linked.

    The Auto cost of a split-linked ADJUSTMENT is no cost at all (``_compute_wac_for_auto_items``, ``auto_cost.py``):
    its units come from the split's ratio, which the average rescales when it is computed, so the row is stored
    without a cost basis by design. That is checked here, so no test edits a row it only assumes.
    """
    split = await _event(world, AssetEventType.SPLIT, SPLIT_RATIO)
    created = {**_created_adjustment(world, broker=world.source, quantity=SPLIT_QUANTITY, cost_basis_mode="auto"), "asset_event_id": split.id}

    response = await _commit(world, creates=[created])

    assert response.committed is True and response.issues == [], f"scaffold: the Auto create of an ADJUSTMENT +{SPLIT_QUANTITY} linked to SPLIT id={split.id} was refused: {_render(response.issues)}"
    row_id = next(result.ids[0] for result in response.results if result.operation == "create" and result.index == 0)
    row = await world.session.get(Transaction, row_id)
    assert row is not None, f"scaffold: the created row id={row_id} is not in the session"
    stored = (row.type, row.quantity, row.asset_event_id, row.cost_basis_override, row.cost_basis_currency)
    assert stored == (TransactionType.ADJUSTMENT, SPLIT_QUANTITY, split.id, None, None), f"scaffold: the split-linked ADJUSTMENT must be stored linked and without a cost basis; (type, quantity, asset_event_id, cost, currency) = {stored}"
    return row, split


async def _link_change(world: World, link_change: str) -> tuple[int, int | None]:
    """The ``asset_event_id`` an update sends for ``link_change``, and the link the row has once it is applied.

    ``unlink`` sends 0: the unlink sentinel of ``TXUpdateItem`` (None leaves the link as it is; ``_apply_update_event``
    in ``batch_edits.py``), and what the app's ``buildUpdateDiff`` sends when a link is removed.
    ``relink-price-adjustment`` sends a PRICE_ADJUSTMENT event of the same asset, the other event type an ADJUSTMENT
    may realize (``event_suggestions.py``).
    """
    if link_change == "unlink":
        return 0, None
    if link_change == "relink-price-adjustment":
        price_adjustment = await _event(world, AssetEventType.PRICE_ADJUSTMENT, Decimal("1.5"))
        return price_adjustment.id, price_adjustment.id
    raise ValueError(f"unknown link change {link_change!r}")


async def _commit(world: World, *, creates: list[dict] | None = None, updates: list[dict] | None = None, promotes: list[dict] | None = None) -> TXBatchResponse:
    """The batch as ``POST /transactions/commit`` runs it: commit requested, no user (so no access check)."""
    return await TransactionService(world.session).execute_batch(
        creates_raw=creates or [],
        updates_raw=updates or [],
        deletes=[],
        promotes_raw=promotes or [],
        commit=True,
    )


def _render(issues: list[TXValidationIssue]) -> str:
    """The issues, for a failure message."""
    return "; ".join(f"{issue.operation}[{issue.index}] ref_id={issue.ref_id} code={issue.code} field={issue.field} params={issue.params} error={issue.error!r}" for issue in issues) or "none"


def _cost_issues(response: TXBatchResponse) -> list[tuple]:
    """Every ``costBasisRequired`` issue, as ``(operation, index, ref_id, field, params)``."""
    return [(issue.operation, issue.index, issue.ref_id, issue.field, issue.params) for issue in response.issues if issue.code == COST_BASIS_REQUIRED]


def _update_results(response: TXBatchResponse) -> list[tuple]:
    """The update results, as ``(index, ids, status)`` in index order."""
    return sorted((result.index, tuple(result.ids), result.status) for result in response.results if result.operation == "update")


def _edit(rows: list[Transaction], edit: str, marker: str) -> list[dict]:
    """A notes-only or tags-only edit of every row given: what the app's diff sends when nothing else changed."""
    if edit == "notes":
        return [{"id": row.id, "description": f"{marker} notes edited"} for row in rows]
    if edit == "tags":
        return [{"id": row.id, "tags": EDITED_TAGS} for row in rows]
    raise ValueError(f"unknown edit {edit!r}")


def _assert_edit_landed(rows: list[Transaction], edit: str, marker: str) -> None:
    for row in rows:
        if edit == "notes":
            assert row.description == f"{marker} notes edited", f"row {row.id} ({row.type.value} {row.quantity}): notes {row.description!r} after a committed notes edit"
        else:
            assert row.tags == ",".join(EDITED_TAGS), f"row {row.id} ({row.type.value} {row.quantity}): tags {row.tags!r} after a committed tags edit"


def _requires_cost_basis(tx_type: TransactionType, quantity: Decimal) -> bool:
    """``_requires_cost_basis`` on an unsaved row of this type and quantity, called as the batch calls it.

    Through an instance without a session: the rule reads the row alone, and the call works whether it stays a
    staticmethod or not.
    """
    row = Transaction(broker_id=1, asset_id=1, type=tx_type, date=MOVE_DAY, quantity=quantity, amount=Decimal("0"))
    return bool(TransactionService(session=None)._requires_cost_basis(row))


def _metadata_says_required(tx_type: TransactionType, quantity: Decimal) -> bool:
    """What ``TX_TYPE_METADATA`` says, read the way N2 reads it: a pair type by its side, any other by its mode."""
    entry = TX_TYPE_METADATA[tx_type]
    mode = entry.cost_basis_mode if entry.cost_basis_pair is None else entry.cost_basis_pair[1 if quantity > 0 else 0]
    return mode == "required_qty_pos" and quantity > 0


def _patch_metadata(monkeypatch: pytest.MonkeyPatch, tx_type: TransactionType, attribute: str, value) -> None:
    """Patch one field of a ``TX_TYPE_METADATA`` entry IN PLACE, for this test only.

    The entry object itself is changed — not a copy put back in the dict — so whatever reads the metadata when it
    runs, through the dict or through the entry, sees the patch. A rule that copies the metadata at import time does
    not, and that is the defect these tests exist to refuse. ``monkeypatch`` restores the field at teardown.
    """
    monkeypatch.setattr(TX_TYPE_METADATA[tx_type], attribute, value)
    assert getattr(TX_TYPE_METADATA[tx_type], attribute) == value, f"scaffold: TX_TYPE_METADATA[{tx_type.value}].{attribute} does not show the patch"


# ============================================================================
# RED — EDITS OF A ROW STORED WITHOUT A COST
# ============================================================================


class TestEditsOfARowStoredWithoutCost:
    """RED before N2: the edits that change no type, quantity or cost of a row stored without a cost commit.

    Today ``_check_update_cost_basis`` checks the final state of EVERY update, so any edit of such a row is refused
    with ``costBasisRequired`` on the row — the subject's index, ``ref_id`` the row — and the batch does not commit.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", SHAPES)
    @pytest.mark.parametrize("edit", EDITS)
    async def test_notes_or_tags_edit_of_row_stored_without_cost_commits(self, world, edit, shape):
        """RED before N2: a notes-only or tags-only edit of a row stored without a cost commits, and repairs nothing."""
        stored = await _store(world, shape, cost=None)

        response = await _commit(world, updates=_edit(stored.rows, edit, world.marker))

        assert response.committed is True and response.issues == [], f"N2: a {edit}-only edit of a {SHAPE_LABELS[shape]} stored without a cost basis changes no type, quantity or cost, so it must commit and leave the row as it is. It was refused: {_render(response.issues)}"
        assert _update_results(response) == [(index, (row.id,), "success") for index, row in enumerate(stored.rows)], f"Committed, but not every row was updated: {response.results}"
        _assert_edit_landed(stored.rows, edit, world.marker)
        assert (stored.subject.cost_basis_override, stored.subject.cost_basis_currency) == (None, None), f"N2 repairs nothing: id={stored.subject.id} must keep no cost basis after a {edit} edit, it now has {stored.subject.cost_basis_override} {stored.subject.cost_basis_currency}"

    @pytest.mark.asyncio
    async def test_date_only_edit_of_adjustment_stored_without_cost_commits(self, world):
        """RED before N2, DERIVED: a date is none of the three changes the rule reads, so a date-only edit commits.

        Not in the coordinator's list: it follows from the decision «the rule applies to updates that change type,
        quantity or cost». It is the test that tells a cure listing what matters (type, quantity, cost, event link)
        from one listing what is harmless (notes, tags): the second refuses this edit. Drop it if a date was meant to
        count.
        """
        stored = await _store(world, "adjustment_in", cost=None)
        new_day = MOVE_DAY + timedelta(days=1)

        response = await _commit(world, updates=[{"id": stored.subject.id, "date": new_day.isoformat()}])

        assert response.committed is True and response.issues == [], f"N2: a date-only edit of an ADJUSTMENT +{ADJUSTMENT_QUANTITY} stored without a cost basis changes no type, quantity or cost, so it must commit. It was refused: {_render(response.issues)}"
        assert stored.subject.date == new_day, f"Committed, but the row's date is {stored.subject.date}, not {new_day}"
        assert (stored.subject.cost_basis_override, stored.subject.cost_basis_currency) == (None, None), f"N2 repairs nothing: the row now has {stored.subject.cost_basis_override} {stored.subject.cost_basis_currency}"


# ============================================================================
# RED — THE RULE READS THE METADATA
# ============================================================================


class TestTheRuleReadsTheMetadata:
    """RED before N2: the rule follows ``TX_TYPE_METADATA``, so a patched entry changes the answer.

    Today ``_requires_cost_basis`` is written by hand (TRANSFER and ADJUSTMENT with quantity > 0) and ignores the
    patch: it answers what it always answered.
    """

    @pytest.mark.parametrize(
        ("tx_type", "attribute", "patched", "quantity", "required"),
        [
            (TransactionType.ADJUSTMENT, "cost_basis_mode", "optional", ADJUSTMENT_QUANTITY, False),
            (TransactionType.TRANSFER, "cost_basis_pair", ["forbidden", "optional"], TRANSFER_QUANTITY, False),
            (TransactionType.BUY, "cost_basis_mode", "required_qty_pos", Decimal("3"), True),
        ],
        ids=["adjustment-made-optional", "transfer-receiver-made-optional", "buy-made-required"],
    )
    def test_requires_cost_basis_follows_patched_metadata(self, monkeypatch, tx_type, attribute, patched, quantity, required):
        """RED before N2: ``_requires_cost_basis`` answers what the patched metadata says, for any type."""
        _patch_metadata(monkeypatch, tx_type, attribute, patched)

        answer = _requires_cost_basis(tx_type, quantity)

        assert answer is required, f"N2: with TX_TYPE_METADATA[{tx_type.value}].{attribute} patched to {patched!r}, _requires_cost_basis({tx_type.value}, quantity={quantity}) must follow the metadata and answer {required}; it answered {answer}, so the rule is still written by hand"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", SHAPES)
    async def test_create_without_cost_commits_when_metadata_makes_it_optional(self, world, monkeypatch, shape):
        """RED before N2: a create without a cost commits once the metadata makes its cost basis optional.

        The ADJUSTMENT goes through ``_check_result_create_cost_basis``, the TRANSFER pair through
        ``_check_linked_create_cost_basis``: both ask ``_requires_cost_basis``.
        """
        if shape == "transfer_in":
            _patch_metadata(monkeypatch, TransactionType.TRANSFER, "cost_basis_pair", ["forbidden", "optional"])
            creates, subject_index = _created_pair(world), 1
        else:
            _patch_metadata(monkeypatch, TransactionType.ADJUSTMENT, "cost_basis_mode", "optional")
            creates, subject_index = [_created_adjustment(world, broker=world.dest, quantity=ADJUSTMENT_QUANTITY)], 0

        response = await _commit(world, creates=creates)

        assert response.committed is True and response.issues == [], f"N2: with TX_TYPE_METADATA patched to make its cost basis optional, a {SHAPE_LABELS[shape]} created without a cost must commit; it was refused, so the hand-written rule still decides: {_render(response.issues)}"
        created_id = next(result.ids[0] for result in response.results if result.operation == "create" and result.index == subject_index)
        created = await world.session.get(Transaction, created_id)
        assert created is not None and created.cost_basis_override is None, f"The {SHAPE_LABELS[shape]} id={created_id} was committed with a cost basis nobody gave: {created}"


# ============================================================================
# GUARDS — CREATES NEED A COST
# ============================================================================


class TestCreatesNeedACost:
    """Guard, green before and after N2: a create without a cost is refused on its own row."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", SHAPES)
    async def test_create_without_cost_is_refused_on_its_row(self, world, shape):
        """Guard: ``costBasisRequired`` on the create's index, field ``cost_basis_override``, ``params.type``; not committed.

        The row that needs the cost sits at index 1 behind a row that needs none — the pair's giving leg, or an
        ADJUSTMENT taking one unit away — so the index is the row's own, not a default.
        """
        if shape == "transfer_in":
            creates, expected_type = _created_pair(world), "TRANSFER"
        else:
            creates = [
                _created_adjustment(world, broker=world.source, quantity=Decimal("-1")),
                _created_adjustment(world, broker=world.dest, quantity=ADJUSTMENT_QUANTITY),
            ]
            expected_type = "ADJUSTMENT"

        response = await _commit(world, creates=creates)

        assert response.committed is False, f"A {SHAPE_LABELS[shape]} created without a cost basis was committed: {response.results}"
        assert _cost_issues(response) == [("create", 1, None, "cost_basis_override", {"type": expected_type})], f"Expected one costBasisRequired on create 1 alone: {_render(response.issues)}"
        assert [issue for issue in response.issues if issue.code != COST_BASIS_REQUIRED] == [], f"Only the cost basis may refuse this batch: {_render(response.issues)}"


# ============================================================================
# GUARDS — UPDATES THAT CHANGE WHAT THE RULE READS
# ============================================================================


class TestUpdatesThatChangeWhatTheRuleReads:
    """Guard, green before and after N2: an update that changes the quantity or the type, or names a cost basis mode,
    without a cost, is refused.

    Today every update is checked; after N2 these still are, because each changes the quantity or the type of the
    stored row, or names the mode.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", ["adjustment-out-flipped-in", "adjustment-in-more-units", "transfer-in-more-units"])
    async def test_quantity_change_without_cost_is_refused(self, world, case):
        """Guard: −5 → +5 on an ADJUSTMENT (the sign), or more units on a row stored without a cost, is refused."""
        session = world.session
        if case == "adjustment-out-flipped-in":
            # An ADJUSTMENT taking 5 units away needs no cost; flipped to +5, it adds units and does.
            subject = _stored_row(world, broker=world.source, tx_type=TransactionType.ADJUSTMENT, quantity=Decimal("-5"))
            session.add(subject)
            await session.flush()
            updates, subject_index = [{"id": subject.id, "quantity": "5"}], 0
        elif case == "adjustment-in-more-units":
            stored = await _store(world, "adjustment_in", cost=None)
            subject = stored.subject
            updates, subject_index = [{"id": subject.id, "quantity": "7"}], 0
        else:
            stored = await _store(world, "transfer_in", cost=None)
            giving, subject = stored.rows
            updates, subject_index = [{"id": giving.id, "quantity": "-6"}, {"id": subject.id, "quantity": "6"}], stored.subject_index

        response = await _commit(world, updates=updates)

        assert response.committed is False, f"{case}: an update changing the quantity of a row without a cost basis was committed: {response.results}"
        assert _cost_issues(response) == [("update", subject_index, subject.id, "cost_basis_override", {"type": subject.type.value})], f"{case}: expected one costBasisRequired on update {subject_index} (id={subject.id}): {_render(response.issues)}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", SHAPES)
    async def test_manual_mode_without_cost_is_refused(self, world, shape):
        """Guard: ``cost_basis_mode: "manual"`` with no ``cost_basis_override``, on a row stored without a cost, is refused.

        The update names a cost basis mode — one of the cost fields of the decision — and gives no cost: the rule
        applies and the row has none. The app never sends it (``buildUpdateDiff`` sends a mode only for Auto); a
        client can. The mode is not stored, so it cannot be compared with the row: naming it is the change.
        """
        stored = await _store(world, shape, cost=None)

        response = await _commit(world, updates=[{"id": stored.subject.id, "cost_basis_mode": "manual"}])

        assert response.committed is False, f"cost_basis_mode=manual without a cost basis on the {SHAPE_LABELS[shape]} id={stored.subject.id} was committed: {response.results}"
        assert _cost_issues(response) == [("update", 0, stored.subject.id, "cost_basis_override", {"type": stored.subject.type.value})], f"Expected one costBasisRequired on update 0 (id={stored.subject.id}): {_render(response.issues)}"

    @pytest.mark.asyncio
    async def test_type_change_into_adjustment_without_cost_is_refused(self, world, monkeypatch):
        """Guard: a BUY +3 turned into an ADJUSTMENT +3 without a cost is refused — the type alone changed the answer.

        Scaffold. No real swap group reaches a type that needs a cost: TRANSFER and ADJUSTMENT are singletons, and
        BUY↔SELL, DEPOSIT↔WITHDRAWAL, DIVIDEND↔INTEREST, TAX↔FEE are all ``forbidden`` in the metadata. So the test
        lets BUY swap with ADJUSTMENT, through ``SWAP_GROUPS`` (read by ``get_swap_group`` when it runs). The
        quantity stays +3 and no cost is sent: only the type can make the rule apply. The cash goes to 0, as an
        ADJUSTMENT has none; cash is not one of the changes the rule reads.
        """
        session = world.session
        other_groups = [group for group in type_metadata.SWAP_GROUPS if TransactionType.BUY not in group]
        monkeypatch.setattr(type_metadata, "SWAP_GROUPS", [frozenset({TransactionType.BUY, TransactionType.SELL, TransactionType.ADJUSTMENT}), *other_groups])
        bought = _stored_row(world, broker=world.dest, tx_type=TransactionType.BUY, quantity=Decimal("3"), amount=Decimal("-300"), currency=EUR)
        session.add(bought)
        await session.flush()

        response = await _commit(world, updates=[{"id": bought.id, "type": "ADJUSTMENT", "cash": {"code": EUR, "amount": "0"}}])

        uncoded = [issue for issue in response.issues if issue.code is None]
        assert uncoded == [], f"scaffold: the BUY → ADJUSTMENT swap did not get through (SWAP_GROUPS patch not read?), so this proves nothing about the rule: {_render(uncoded)}"
        assert response.committed is False, f"A BUY +3 turned into an ADJUSTMENT +3 without a cost basis was committed: {response.results}"
        assert _cost_issues(response) == [("update", 0, bought.id, "cost_basis_override", {"type": "ADJUSTMENT"})], f"Expected one costBasisRequired on update 0 (id={bought.id}): {_render(response.issues)}"


# ============================================================================
# GUARDS — EDITS OF A ROW WITH ITS COST
# ============================================================================


class TestEditsOfARowWithCost:
    """Guard, green before and after N2: a notes-only or tags-only edit of a row that has its cost commits."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", SHAPES)
    @pytest.mark.parametrize("edit", EDITS)
    async def test_notes_or_tags_edit_of_row_with_cost_commits(self, world, edit, shape):
        """Guard: committed, the edit landed, the cost basis is the one the row was saved with."""
        stored = await _store(world, shape, cost=STORED_COST)

        response = await _commit(world, updates=_edit(stored.rows, edit, world.marker))

        assert response.committed is True and response.issues == [], f"A {edit}-only edit of a {SHAPE_LABELS[shape]} with its cost basis was refused: {_render(response.issues)}"
        assert _update_results(response) == [(index, (row.id,), "success") for index, row in enumerate(stored.rows)], f"Committed, but not every row was updated: {response.results}"
        _assert_edit_landed(stored.rows, edit, world.marker)
        assert (stored.subject.cost_basis_override, stored.subject.cost_basis_currency) == (STORED_COST.amount, STORED_COST.code), f"A {edit} edit changed the cost basis of id={stored.subject.id}: {stored.subject.cost_basis_override} {stored.subject.cost_basis_currency}"


# ============================================================================
# RED AND GUARDS — DECISION P5: AN EXPLICIT NULL EMPTIES A MANUAL COST
# ============================================================================


async def _commit_as_the_endpoint(world: World, *, updates: list[dict]) -> TXBatchResponse:
    """The batch as ``POST /transactions/commit`` runs it, its transaction included: kept when the service answers
    committed, rolled back otherwise (``commit_transactions``, ``api/v1/transactions.py``).

    ``execute_batch`` applies an update to the row and flushes it before its checks can refuse it, and leaves the commit
    or the rollback to its caller: what a refused batch applied stays in the session until the caller rolls it back. A
    savepoint stands in for the request's transaction, as ``test_transaction_service.py``'s W-B17 test does: the test's
    rows, flushed before it, survive its rollback — their flush opened SQLite's transaction, so the savepoint nests in it
    (``begin_writes``, ``db/session.py``) — and the session fixture still rolls everything back: a savepoint released
    inside its transaction commits nothing.

    After a rollback the rows the batch touched are expired: read them back with ``_stored_cost``, which re-reads them,
    never through the attributes of an expired copy, which would load lazily outside the event loop.
    """
    savepoint = await world.session.begin_nested()
    response = await _commit(world, updates=updates)
    if response.committed:
        await savepoint.commit()
    else:
        await savepoint.rollback()
    return response


async def _stored_cost(world: World, tx_id: int) -> tuple[Decimal | None, str | None]:
    """``(cost_basis_override, cost_basis_currency)`` of row ``tx_id`` as the database holds it: what the user finds once
    the request is over. ``populate_existing`` makes ``get`` emit its SELECT even for a row the session holds, and
    overwrite that copy with what it reads."""
    row = await world.session.get(Transaction, tx_id, populate_existing=True)
    assert row is not None, f"scaffold: row id={tx_id} is not in the database"
    return row.cost_basis_override, row.cost_basis_currency


def _show(cost: tuple[Decimal | None, str | None]) -> str:
    """A stored cost basis, for a failure message."""
    amount, code = cost
    return "no cost basis" if (amount, code) == (None, None) else f"{amount} {code}"


def _sends_the_cost(update: dict) -> bool:
    """Whether the batch reads ``cost_basis_override`` as SENT in ``update``: in ``model_fields_set`` once parsed, as
    ``_parse_lenient`` parses it. An explicit null is sent; a key left out is not."""
    return "cost_basis_override" in transaction_schemas.TXUpdateItem.model_validate(update).model_fields_set


async def _legacy_row_with_cost(world: World, shape: str) -> Transaction:
    """A row stored with a cost basis of 42 EUR although its type and side take none: the handover cost decision 47
    writes on a giving leg, or what an older version or an API client left — no rule refuses a ``cost_basis_override``
    sent where none is allowed (rule 12 reads only ``cost_basis_mode``), on a create or on an update.

    ``buy``: a BUY +3 on ``dest`` paying 300 EUR (``dest`` allows a cash overdraft). ``adjustment_out``: an ADJUSTMENT −4
    on ``source``, which holds the BUY's 10 units, so it does not go short — the shape of a split TRANSFER's giving leg.
    """
    if shape == "buy":
        row = _stored_row(world, broker=world.dest, tx_type=TransactionType.BUY, quantity=Decimal("3"), cost=STORED_COST, amount=Decimal("-300"), currency=EUR)
    elif shape == "adjustment_out":
        row = _stored_row(world, broker=world.source, tx_type=TransactionType.ADJUSTMENT, quantity=-TRANSFER_QUANTITY, cost=STORED_COST)
    else:
        raise ValueError(f"unknown legacy shape {shape!r}")
    world.session.add(row)
    await world.session.flush()
    return row


# Decision P5 — an explicit null empties a manual cost where one is taken (TestDecisionP5AnExplicitNullEmptiesTheCost).
# The rows that carry a cost basis although their type and side take none, where the null is ignored (_legacy_row_with_cost).
LEGACY_SHAPES = ("buy", "adjustment_out")
LEGACY_LABELS = {"buy": "BUY +3", "adjustment_out": f"ADJUSTMENT -{TRANSFER_QUANTITY}"}
AUTO_MODES = ("auto", "auto-detail")


class TestDecisionP5AnExplicitNullEmptiesTheCost:
    """Decision P5 — the developer's, 16/10: «se lo svuoto attivamente vuol dire che lo voglio cancellare» — read as the
    coordinator's option (B), 16/10 11:42, to be reviewed by the developer. In an update, ``cost_basis_override: null``
    SENT (the key in ``model_fields_set``) removes the manual cost basis — ``cost_basis_override`` and
    ``cost_basis_currency`` together — where the row's final type and side take one (``cost_basis_allowed``), and is
    refused there with ``costBasisRequired`` when one is required: on today's table every side that takes a cost requires
    one (TRANSFER and ADJUSTMENT with quantity > 0), so the null always ends in that refusal and never removes anything.
    Elsewhere the null is ignored, and with ``cost_basis_mode`` ``auto``/``auto-detail`` too (the Auto cost is computed);
    a key left out changes nothing.

    Before W-B30 ``_apply_update_values`` (``batch_edits.py``) wrote the cost only when it was not None, so an explicit
    null read as a key left out and was ignored everywhere, a side that requires a cost included:

    - red before W-B30, now its guard: emptying the manual cost of a TRANSFER's receiving leg, a side that needs one, is
      refused with ``costBasisRequired`` on the update — N2's update check, once the cost is gone — and the cost stays
      (before W-B30 the update committed);
    - guards, green before W-B30 and since: a null sent on a row whose type and side take no cost — a BUY, an
      ADJUSTMENT −q carrying the handover cost decision 47 writes on a giving leg — is ignored, the update commits and
      the cost stays; a notes-only edit of the pair, the key left out, keeps the receiving leg's cost; an Auto update
      sending the null, as the form does, writes the Auto cost.

    The row that needs a cost is the receiving leg of a stored TRANSFER pair (``_store``), saved with 42 EUR; its Auto
    cost is ``source``'s average, 100 EUR (``UNIT_COST``), so "kept" and "recomputed" cannot be confused. Each test runs
    the batch as ``POST /transactions/commit`` does, its transaction included (``_commit_as_the_endpoint``), and reads
    the row back from the database (``_stored_cost``).
    """

    @pytest.mark.asyncio
    async def test_emptying_the_manual_cost_of_a_received_transfer_is_refused(self, world):
        """Red before W-B30 (decision P5), now its guard: ``{id, cost_basis_override: null}`` on the receiving leg is
        refused — one issue, ``costBasisRequired`` on update 0, ``ref_id`` the leg — and the database keeps its 42 EUR.

        The cure clears both columns, and N2's update check (``_check_update_cost_basis``) then sees a row that needs a
        cost and lost the one it was stored with. Before W-B30 the null kept the cost, and the update committed with no
        issue.
        """
        stored = await _store(world, "transfer_in", cost=STORED_COST)
        subject_id = stored.subject.id
        update = {"id": subject_id, "cost_basis_override": None}
        assert _sends_the_cost(update), "scaffold: the update must SEND cost_basis_override (an explicit null), or this is the case of a key left out"

        response = await _commit_as_the_endpoint(world, updates=[update])

        stored_after = await _stored_cost(world, subject_id)
        assert response.committed is False, f"Decision P5: emptying the manual cost of a received TRANSFER is saved, and the receiving leg id={subject_id} holds {_show(stored_after)} — that leg needs a cost basis, so the update must be refused with costBasisRequired and the cost kept"
        assert [issue for issue in response.issues if issue.code != COST_BASIS_REQUIRED] == [], f"Only the missing cost basis may refuse this update: {_render(response.issues)}"
        assert _cost_issues(response) == [("update", 0, subject_id, "cost_basis_override", {"type": "TRANSFER"})], f"Expected one costBasisRequired on update 0 (id={subject_id}): {_render(response.issues)}"
        assert stored_after == (STORED_COST.amount, STORED_COST.code), f"The update was refused, yet the receiving leg id={subject_id} holds {_show(stored_after)} instead of the {STORED_COST.amount} {STORED_COST.code} it was saved with"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", LEGACY_SHAPES)
    async def test_a_null_where_no_cost_is_taken_is_ignored(self, world, shape):
        """Guard, green before W-B30 and since: ``{id, cost_basis_override: null}`` on a row whose type and side
        take no cost basis, yet carry one, is ignored — the update commits, and ``cost_basis_override`` and
        ``cost_basis_currency`` stay as stored, 42 EUR.

        The coordinator's decision (B), 16/10 11:42, to be reviewed by the developer: the null removes the MANUAL cost
        («toglie il costo manuale») where the type and side take one, and is ignored elsewhere. This protects the
        handover cost decision 47 writes on a giving leg — an ADJUSTMENT −q carrying its broker's Auto cost, the cost
        CP-16 hands its units over at — from a null sent with it; the BUY stands for any other side that takes none. The
        row neither allows nor requires a cost — checked first — and nothing else refuses the update: rule 12 reads only
        ``cost_basis_mode``, not sent, and the rest of the row is valid and unchanged. A cure that clears wherever the
        null is sent turns it red.
        """
        row = await _legacy_row_with_cost(world, shape)
        row_id = row.id
        sides = (type_metadata.cost_basis_allowed(row.type, row.quantity), _requires_cost_basis(row.type, row.quantity))
        assert sides == (False, False), f"precondition broken: a {LEGACY_LABELS[shape]} must neither allow nor require a cost basis; (cost_basis_allowed, _requires_cost_basis) = {sides}"
        stored_before = await _stored_cost(world, row_id)
        assert stored_before == (STORED_COST.amount, STORED_COST.code), f"scaffold: the {LEGACY_LABELS[shape]} id={row_id} must be stored with its cost basis, or a null that leaves it alone proves nothing; it holds {_show(stored_before)}"
        update = {"id": row_id, "cost_basis_override": None}
        assert _sends_the_cost(update), "scaffold: the update must SEND cost_basis_override (an explicit null), or this is the case of a key left out"

        response = await _commit_as_the_endpoint(world, updates=[update])

        stored_after = await _stored_cost(world, row_id)
        assert response.committed is True and response.issues == [], f"Decision P5 (B): a null cost sent on a {LEGACY_LABELS[shape]}, a side that takes no cost basis, must be ignored, yet the update was refused: {_render(response.issues)}"
        assert _update_results(response) == [(0, (row_id,), "success")], f"Committed, but the row was not updated: {response.results}"
        assert stored_after == stored_before, f"Decision P5 (B): a null sent on a {LEGACY_LABELS[shape]}, a side that takes no cost basis, changed its cost: id={row_id} held {_show(stored_before)}, now {_show(stored_after)} — on a giving leg, decision 47's handover cost"

    @pytest.mark.asyncio
    async def test_notes_edit_without_the_cost_key_keeps_the_cost(self, world):
        """Guard, green before W-B30 and since: a notes-only edit of the pair — what the app's diff sends, the cost
        key left out — commits, the notes land, and the receiving leg keeps its 42 EUR. A key left out is not a null.

        Both legs are edited, as the app edits them: a pair keeps one description.
        """
        stored = await _store(world, "transfer_in", cost=STORED_COST)
        subject_id = stored.subject.id
        updates = _edit(stored.rows, "notes", world.marker)
        assert not any(_sends_the_cost(update) for update in updates), f"scaffold: no update may send cost_basis_override, or this is the case of an explicit null: {updates}"

        response = await _commit_as_the_endpoint(world, updates=updates)

        assert response.committed is True and response.issues == [], f"A notes-only edit of a received TRANSFER with its manual cost, the cost key left out, was refused: {_render(response.issues)}"
        assert _update_results(response) == [(index, (row.id,), "success") for index, row in enumerate(stored.rows)], f"Committed, but not every row was updated: {response.results}"
        _assert_edit_landed(stored.rows, "notes", world.marker)
        stored_after = await _stored_cost(world, subject_id)
        assert stored_after == (STORED_COST.amount, STORED_COST.code), f"Decision P5: a cost key left out keeps the cost, yet after a notes-only edit the receiving leg id={subject_id} holds {_show(stored_after)} instead of {STORED_COST.amount} {STORED_COST.code}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("mode", AUTO_MODES)
    async def test_auto_update_sending_a_null_writes_the_auto_cost(self, world, mode):
        """Guard, green before W-B30 and since: ``{id, cost_basis_mode: auto, cost_basis_override: null}`` — what
        the form sends for a row in Auto (``buildUpdateDiff``, ``txPayloadHelpers.ts``) — is not refused for a missing
        cost, commits, and the receiving leg holds its Auto cost, ``source``'s average, 100 EUR: not the 42 it was saved
        with, not nothing. In Auto the null is ignored.
        """
        stored = await _store(world, "transfer_in", cost=STORED_COST)
        subject_id = stored.subject.id
        update = {"id": subject_id, "cost_basis_mode": mode, "cost_basis_override": None}
        assert _sends_the_cost(update), "scaffold: the update must SEND cost_basis_override null, as the form does in Auto"

        response = await _commit_as_the_endpoint(world, updates=[update])

        assert _cost_issues(response) == [], f"Decision P5: in {mode} the null is ignored, yet the update of the received TRANSFER id={subject_id} was refused for a missing cost: {_render(response.issues)}"
        assert response.committed is True and response.issues == [], f"An {mode} update of a received TRANSFER sending a null cost was refused: {_render(response.issues)}"
        stored_after = await _stored_cost(world, subject_id)
        assert stored_after == (UNIT_COST, EUR), f"{mode} cost of the received TRANSFER id={subject_id}: expected {UNIT_COST} {EUR}, the average of source's BUY; the row holds {_show(stored_after)} (wac_results={response.wac_results})"


# ============================================================================
# GUARDS — AUTO COST
# ============================================================================


class TestAutoCost:
    """Guard, green before and after N2: an Auto create with an average available commits, with that average."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", SHAPES)
    async def test_auto_create_with_an_average_commits(self, world, shape):
        """Guard: committed, and the row carries the average of the BUY, 100 EUR.

        The TRANSFER's receiving leg averages its partner's broker (``source``) before the transfer; the ADJUSTMENT,
        created on ``source``, averages its own broker without itself.
        """
        if shape == "transfer_in":
            creates, subject_index = _created_pair(world, cost_basis_mode="auto"), 1
        else:
            creates, subject_index = [_created_adjustment(world, broker=world.source, quantity=ADJUSTMENT_QUANTITY, cost_basis_mode="auto")], 0

        response = await _commit(world, creates=creates)

        assert response.committed is True and response.issues == [], f"An Auto {SHAPE_LABELS[shape]} with an average available was refused: {_render(response.issues)}"
        created_id = next(result.ids[0] for result in response.results if result.operation == "create" and result.index == subject_index)
        created = await world.session.get(Transaction, created_id)
        assert created is not None, f"Committed, but the created row id={created_id} is not in the session"
        assert (created.cost_basis_override, created.cost_basis_currency) == (UNIT_COST, EUR), f"Auto cost of id={created_id}: expected {UNIT_COST} {EUR}, the average of the BUY; got {created.cost_basis_override} {created.cost_basis_currency} (wac_results={response.wac_results})"


# ============================================================================
# GUARDS — PROMOTE OF A ROW STORED WITHOUT A COST
# ============================================================================


class TestPromoteOfARowStoredWithoutCost:
    """Guard, green before and after N2: a promote cannot carry a row without a cost into a pair behind a notes edit."""

    @pytest.mark.asyncio
    async def test_promote_of_legacy_row_edited_in_same_batch_is_refused(self, world):
        """Guard: promote a stored ADJUSTMENT −5 (source) with a stored ADJUSTMENT +5 without a cost (dest), and edit
        the +5's notes in the same batch → refused, ``costBasisRequired`` on the +5.

        The promote makes the +5 the receiving leg of a TRANSFER. ``_check_promoted_saved_cost_basis`` skips the
        rows the batch also updates, because the update check covers them; today it does, since it checks every
        update. A cure that skips notes-only updates must still see this one — its type changes, ADJUSTMENT to
        TRANSFER — or stop the promote check from skipping it. Either issue is accepted: on the update or on the
        promote, both at index 0, with ``ref_id`` the +5. Otherwise a TRANSFER without a cost is committed, the
        defect closed by d7c148564 (devWiki problems/promote-skipped-cost-basis-check).
        """
        session = world.session
        giving = _stored_row(world, broker=world.source, tx_type=TransactionType.ADJUSTMENT, quantity=Decimal("-5"))
        receiving = _stored_row(world, broker=world.dest, tx_type=TransactionType.ADJUSTMENT, quantity=Decimal("5"))
        session.add_all([giving, receiving])
        await session.flush()

        response = await _commit(
            world,
            updates=[{"id": receiving.id, "description": f"{world.marker} notes edited"}],
            promotes=[{"id_a": giving.id, "id_b": receiving.id}],
        )

        assert response.committed is False, f"A promote made the ADJUSTMENT +5 id={receiving.id}, stored without a cost basis, the receiving leg of a TRANSFER, and the batch was committed: {response.results}"
        on_receiver = [issue for issue in _cost_issues(response) if issue[2] == receiving.id]
        assert on_receiver in (
            [("update", 0, receiving.id, "cost_basis_override", {"type": "TRANSFER"})],
            [("promote", 0, receiving.id, "cost_basis_override", {"type": "TRANSFER"})],
        ), f"Expected one costBasisRequired on the receiving leg id={receiving.id}, on the update or on the promote: {_render(response.issues)}"


# ============================================================================
# RED AND GUARDS — THE SPLIT-LINKED ADJUSTMENT
# ============================================================================


class TestSplitLinkedAdjustment:
    """The ADJUSTMENT +qty that realizes a SPLIT: stored without a cost basis by design, its link standing for its cost.

    While the row points at a SPLIT event, the average reads its units as a rescale of the pool
    (``CostMovementKind.SPLIT``, ``financial_math/average_cost.py``). Unlinked, or linked to an event that is not a
    SPLIT, the same row is an acquisition of unknown cost. So an update that changes the link changes what the cost
    basis depends on, and is held to the rule like one that changes the type, the quantity or the cost.

    Before N2, every update of the row without Auto was refused. The first N2 cure let all of them through, link
    changes included, because its ``cost_fields`` compared type, quantity and cost only. The updates here carry no
    ``cost_basis_mode``, as an API client sends them: an Auto update is not checked here at all (its cost is
    recomputed), and the form opens a saved row without a manual cost in Auto.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("link_change", LINK_CHANGES)
    async def test_link_change_without_cost_is_refused(self, world, link_change):
        """RED with the first N2 cure, green once ``cost_fields`` carries ``asset_event_id``: ``costBasisRequired`` on
        update 0, ``ref_id`` the row, ``params.type`` ADJUSTMENT; not committed."""
        row, split = await _split_linked_adjustment(world)
        new_link, _linked_after = await _link_change(world, link_change)

        response = await _commit(world, updates=[{"id": row.id, "asset_event_id": new_link}])

        if response.committed:
            pytest.fail(
                f"{link_change}: the ADJUSTMENT +{SPLIT_QUANTITY} id={row.id}, linked to SPLIT id={split.id} and stored without a cost basis, was committed with asset_event_id={row.asset_event_id} and cost_basis_override={row.cost_basis_override}: "
                "an acquisition of unknown cost. Its link stands for its cost, so changing it must be held to the rule (cost_fields must carry asset_event_id)"
            )
        assert [issue for issue in response.issues if issue.code != COST_BASIS_REQUIRED] == [], f"{link_change}: only the cost basis may refuse this update: {_render(response.issues)}"
        assert _cost_issues(response) == [("update", 0, row.id, "cost_basis_override", {"type": "ADJUSTMENT"})], f"{link_change}: expected one costBasisRequired on update 0 (id={row.id}): {_render(response.issues)}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("edit", EDITS)
    async def test_notes_or_tags_edit_commits_and_keeps_the_link(self, world, edit):
        """Guard, green with the first N2 cure and after the fix: nothing the cost basis depends on changes, so a
        notes-only or tags-only edit commits, and the link and the missing cost stay as they are. (Before N2 it was
        refused, like any update of the row.)"""
        row, split = await _split_linked_adjustment(world)

        response = await _commit(world, updates=_edit([row], edit, world.marker))

        assert response.committed is True and response.issues == [], f"A {edit}-only edit of the split-linked ADJUSTMENT +{SPLIT_QUANTITY} id={row.id} changes nothing its cost basis depends on, and was refused: {_render(response.issues)}"
        assert _update_results(response) == [(0, (row.id,), "success")], f"Committed, but the row was not updated: {response.results}"
        _assert_edit_landed([row], edit, world.marker)
        assert (row.asset_event_id, row.cost_basis_override, row.cost_basis_currency) == (split.id, None, None), f"A {edit} edit changed what stands for the cost of id={row.id}: asset_event_id={row.asset_event_id}, cost {row.cost_basis_override} {row.cost_basis_currency}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("link_change", LINK_CHANGES)
    async def test_link_change_with_a_cost_commits(self, world, link_change):
        """Guard, green with the first N2 cure and after the fix: the same link change, with the row's cost in the same
        update, commits with that cost: the way out the refusal points to.

        The refusal is about the missing cost, never about the link. The keys are the ones the app's diff sends for
        it in manual mode: the link, and the cost (``buildUpdateDiff`` sends no mode for manual).
        """
        row, _split = await _split_linked_adjustment(world)
        new_link, linked_after = await _link_change(world, link_change)

        response = await _commit(world, updates=[{"id": row.id, "asset_event_id": new_link, "cost_basis_override": {"code": STORED_COST.code, "amount": str(STORED_COST.amount)}}])

        assert response.committed is True and response.issues == [], f"{link_change} with a cost basis on id={row.id} was refused: {_render(response.issues)}"
        assert _update_results(response) == [(0, (row.id,), "success")], f"Committed, but the row was not updated: {response.results}"
        assert (row.asset_event_id, row.cost_basis_override, row.cost_basis_currency) == (linked_after, STORED_COST.amount, STORED_COST.code), f"{link_change} with a cost: id={row.id} now has asset_event_id={row.asset_event_id}, cost {row.cost_basis_override} {row.cost_basis_currency}"


# ============================================================================
# GUARD — THE RULE AGREES WITH THE METADATA
# ============================================================================


class TestTheRuleAgreesWithTheMetadata:
    """Guard, green before and after N2: for every type and quantity sign, the rule says what the metadata says.

    Green today because the hand-written rule happens to match the metadata; after N2 because it reads it. A cure
    that reads it wrongly — the wrong side of a pair, the mode of a pair type — turns one of these red.
    """

    @pytest.mark.parametrize("quantity", [Decimal("-3"), Decimal("0"), Decimal("3")], ids=["qty-negative", "qty-zero", "qty-positive"])
    @pytest.mark.parametrize("tx_type", list(TransactionType), ids=lambda tx_type: tx_type.value)
    def test_requires_cost_basis_agrees_with_metadata(self, tx_type, quantity):
        """Guard: ``_requires_cost_basis(type, quantity)`` == the metadata's ``required_qty_pos`` with quantity > 0."""
        expected = _metadata_says_required(tx_type, quantity)

        answer = _requires_cost_basis(tx_type, quantity)

        entry = TX_TYPE_METADATA[tx_type]
        assert answer is expected, f"_requires_cost_basis({tx_type.value}, quantity={quantity}) answered {answer}; TX_TYPE_METADATA says {expected} (cost_basis_mode={entry.cost_basis_mode!r}, cost_basis_pair={entry.cost_basis_pair!r})"


# ============================================================================
# RED — DECISION 47: THE GIVING LEG OF A TRANSFER (SPLIT AND PROMOTE)
# ============================================================================


async def _run_batch(world: World, *, commit: bool, creates: list[dict] | None = None, updates: list[dict] | None = None, splits: list[dict] | None = None, promotes: list[dict] | None = None) -> TXBatchResponse:
    """The batch as ``POST /transactions/commit`` (``commit=True``) or ``/validate`` (``commit=False``) runs it, with
    splits; no user, so no access check. It never commits: the session fixture rolls everything back."""
    return await TransactionService(world.session).execute_batch(
        creates_raw=creates or [],
        updates_raw=updates or [],
        deletes=[],
        splits_raw=splits or [],
        promotes_raw=promotes or [],
        commit=commit,
    )


async def _legs_now(world: World, giving: Transaction, receiving: Transaction) -> dict[str, tuple]:
    """The two legs as the batch left them in the session's transaction — re-read, the in-memory copies refreshed —
    as ``(type, quantity, related_transaction_id, cost_basis_override, cost_basis_currency)``."""
    ids = {"giving": giving.id, "receiving": receiving.id}
    statement = select(Transaction).where(Transaction.id.in_(list(ids.values()))).execution_options(populate_existing=True)
    rows = {row.id: row for row in (await world.session.execute(statement)).scalars()}
    return {label: (rows[tx_id].type, rows[tx_id].quantity, rows[tx_id].related_transaction_id, rows[tx_id].cost_basis_override, rows[tx_id].cost_basis_currency) for label, tx_id in ids.items()}


async def _assert_no_rate_nor_route(session: AsyncSession, currency: str, other: str = EUR) -> None:
    """Precondition: no rate and no route for ``currency``/``other`` exist, committed by anyone (as test_broker_service.py's
    ``_assert_no_fx_data``): the conversion the case needs is really missing, not merely assumed so."""
    base, quote = sorted((currency, other))
    rates = (await session.execute(select(func.count()).select_from(FxRate).where(FxRate.base == base, FxRate.quote == quote))).scalar_one()
    routes = (await session.execute(select(func.count()).select_from(FxConversionRoute).where(or_(and_(FxConversionRoute.base == base, FxConversionRoute.quote == quote), and_(FxConversionRoute.base == quote, FxConversionRoute.quote == base))))).scalar_one()
    assert (rates, routes) == (0, 0), f"precondition broken: {base}/{quote} has {rates} rate(s) and {routes} route(s) — this case needs a pair nobody stores"


async def _fx_conversion_pair(world: World) -> tuple[Transaction, Transaction]:
    """An FX_CONVERSION pair on ``dest`` (−100 EUR → +110 USD), linked both ways: a pair whose split needs no cost."""
    now = utcnow()
    sold = Transaction(broker_id=world.dest.id, type=TransactionType.FX_CONVERSION, date=MOVE_DAY, quantity=Decimal("0"), amount=Decimal("-100"), currency=EUR, description=f"{world.marker} EUR sold", created_at=now, updated_at=now)
    bought = Transaction(broker_id=world.dest.id, type=TransactionType.FX_CONVERSION, date=MOVE_DAY, quantity=Decimal("0"), amount=Decimal("110"), currency="USD", description=f"{world.marker} USD bought", created_at=now, updated_at=now)
    world.session.add_all([sold, bought])
    await world.session.flush()
    sold.related_transaction_id, bought.related_transaction_id = bought.id, sold.id
    await world.session.flush()
    return sold, bought


def _issue_view(issue: TXValidationIssue) -> dict:
    """What decision 47 fixes of an issue: where it is, its code, its field and its params — never its text."""
    return {"operation": issue.operation, "index": issue.index, "ref_id": issue.ref_id, "code": issue.code, "field": issue.field, "params": issue.params}


class TestDecision47TheGivingLegOfATransfer:
    """RED until decision 47 (but for one guard): where a batch takes a TRANSFER's giving leg out of its pair, the leg
    leaves at its own broker's Auto cost — unless an update of the same batch gives it a cost of its own, which stays
    (the coordinator's decision 4, 16/10) —, and a promote that makes a leg the giving side of a TRANSFER takes its cost
    away.

    ``source`` holds 10 units bought for 1 000 EUR (the ``world`` fixture): 100 EUR is its Auto cost, the cost its
    giving leg is handed over at. The receiving leg carries 42 EUR (``STORED_COST``), never 100: a cure that copied the
    partner's cost, or averaged ``dest`` — whose only units are that leg's — would show.
    """

    @pytest.mark.asyncio
    async def test_split_keeps_the_cost_an_update_of_the_same_batch_gives_the_giving_leg(self, world):
        """Guard, green today and after decision 47 (decision 4): the batch splits the pair and, in an update, gives the
        giving leg a cost of 77 EUR — no ``cost_basis_mode``, as an API client sends a cost, the mode being refused on an
        ADJUSTMENT −4 (rule 12). It commits; the giving leg is an ADJUSTMENT −4 at 77 EUR, never overwritten with
        ``source``'s Auto cost, 100 EUR; the receiving leg keeps its 42.

        The update runs after the split (``execute_batch``: split, then update), on the ADJUSTMENT the split left; the
        handover cost is computed in the WAC stage, later still, and must leave a cost the batch wrote alone.
        """
        stored = await _store(world, "transfer_in", cost=STORED_COST)
        giving, receiving = stored.rows
        own_cost = Currency(code=EUR, amount=Decimal("77"))
        assert own_cost.amount not in (UNIT_COST, STORED_COST.amount), "scaffold: the update's cost must differ from the Auto cost and from the receiving leg's"

        response = await _run_batch(world, commit=True, splits=[{"id_a": giving.id, "id_b": receiving.id}], updates=[{"id": giving.id, "cost_basis_override": {"code": own_cost.code, "amount": str(own_cost.amount)}}])

        assert response.committed is True and response.issues == [], f"A split with an update giving its giving leg a cost was refused: {_render(response.issues)}"
        assert sorted((result.operation, result.index, result.status) for result in response.results) == [("split", 0, "success"), ("update", 0, "success")], f"results: {response.results}"
        assert await _legs_now(world, giving, receiving) == {
            "giving": (TransactionType.ADJUSTMENT, -TRANSFER_QUANTITY, None, own_cost.amount, own_cost.code),
            "receiving": (TransactionType.ADJUSTMENT, TRANSFER_QUANTITY, None, STORED_COST.amount, STORED_COST.code),
        }

    @pytest.mark.asyncio
    async def test_split_hands_the_giving_leg_over_at_its_own_brokers_auto_cost(self, world):
        """RED until decision 47: the split commits; the giving leg becomes an ADJUSTMENT −4 at ``source``'s Auto cost,
        100 EUR (its BUY, the leg left out), with its currency; the receiving leg an ADJUSTMENT +4 that keeps its 42 EUR.

        Today the giving leg is left without a cost: an ADJUSTMENT-out that CP-16 closes at price 0, its units read as
        destroyed.
        """
        stored = await _store(world, "transfer_in", cost=STORED_COST)
        giving, receiving = stored.rows

        response = await _run_batch(world, commit=True, splits=[{"id_a": giving.id, "id_b": receiving.id}])

        assert response.committed is True and response.issues == [], f"The split of the TRANSFER pair {giving.id}/{receiving.id} was refused: {_render(response.issues)}"
        assert [(result.operation, result.index, tuple(result.ids), result.status) for result in response.results] == [("split", 0, (giving.id, receiving.id), "success")]
        assert await _legs_now(world, giving, receiving) == {
            "giving": (TransactionType.ADJUSTMENT, -TRANSFER_QUANTITY, None, UNIT_COST, EUR),
            "receiving": (TransactionType.ADJUSTMENT, TRANSFER_QUANTITY, None, STORED_COST.amount, STORED_COST.code),
        }

    @pytest.mark.asyncio
    async def test_split_prices_the_giving_leg_after_the_rest_of_its_batch(self, world):
        """RED until decision 47: the giving leg's cost is computed in the batch's WAC stage, after the other stages, so it
        sees the batch's final state — the same batch buys 10 more units on ``source`` for 3 000 EUR before the move,
        and the leg leaves at (1 000 + 3 000) / 20 = 200 EUR, not at the 100 a cost computed in the split stage reads."""
        stored = await _store(world, "transfer_in", cost=STORED_COST)
        giving, receiving = stored.rows
        purchase = {
            "broker_id": world.source.id,
            "asset_id": world.asset.id,
            "type": "BUY",
            "date": LATER_BUY_DAY.isoformat(),
            "quantity": str(BUY_QUANTITY),
            "cash": {"code": EUR, "amount": str(LATER_BUY_PAID)},
            "description": f"{world.marker} buy in the split's batch",
        }
        expected_cost = (BUY_QUANTITY * UNIT_COST - LATER_BUY_PAID) / (2 * BUY_QUANTITY)
        assert expected_cost == Decimal("200"), "the oracle: (1 000 + 3 000) / 20"

        response = await _run_batch(world, commit=True, creates=[purchase], splits=[{"id_a": giving.id, "id_b": receiving.id}])

        assert response.committed is True and response.issues == [], f"A split beside a purchase was refused: {_render(response.issues)}"
        legs = await _legs_now(world, giving, receiving)
        assert legs["giving"] == (TransactionType.ADJUSTMENT, -TRANSFER_QUANTITY, None, expected_cost, EUR), f"The giving leg id={giving.id} must leave at the average of the batch's final state, {expected_cost} EUR: {legs['giving']}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", [pytest.param(True, id="commit"), pytest.param(False, id="validate")])
    async def test_split_whose_handover_cost_needs_a_missing_conversion_is_refused(self, world, commit):
        """RED until decision 47: part of ``source``'s units were paid in PYG, which no rate converts — the giving leg has
        no Auto cost to leave at, and the split is refused as an Auto row without one would be: one WAC_FX_UNAVAILABLE on
        split 1 (index 0 is the split of an FX_CONVERSION pair, which needs no cost), ``ref_id`` the giving leg,
        ``field`` ``cost_basis_override``, params ``pairs`` and ``pair_details``; nothing committed. /validate
        (``commit=False``) shows the same issue. Today the split goes through and leaves the giving leg without a cost.

        A real missing conversion: PYG is first proven absent from every rate and route, then the oracle — the call
        ``_handover_cost`` makes, ``compute_wac_iterative`` on ``source`` up to the move without the leg — confirms there
        is no average and names PYG/EUR on the PYG purchase's day.
        """
        await _assert_no_rate_nor_route(world.session, PYG)
        now = utcnow()
        world.session.add(Transaction(broker_id=world.source.id, asset_id=world.asset.id, type=TransactionType.BUY, date=PYG_DAY, quantity=BUY_QUANTITY, amount=PYG_PAID, currency=PYG, description=f"{world.marker} buy in PYG", created_at=now, updated_at=now))
        sold, bought = await _fx_conversion_pair(world)
        stored = await _store(world, "transfer_in", cost=STORED_COST)
        giving, receiving = stored.rows
        oracle = await compute_wac_iterative(world.session, broker_id=world.source.id, asset_id=world.asset.id, as_of_date=MOVE_DAY, asset_currency=EUR, excluded_tx_ids=[giving.id], use_cache=False)
        assert (oracle.wac, [(missing.pair, missing.dates) for missing in oracle.wac_missing_pairs]) == (None, [("PYG/EUR", [PYG_DAY])]), f"precondition broken: the giving leg's Auto cost must need PYG/EUR on {PYG_DAY}: {oracle}"

        response = await _run_batch(world, commit=commit, splits=[{"id_a": sold.id, "id_b": bought.id}, {"id_a": giving.id, "id_b": receiving.id}])

        assert response.committed is False, f"A split whose giving leg has no cost to leave at was committed: {response.results}"
        assert [_issue_view(issue) for issue in response.issues] == [
            {
                "operation": "split",
                "index": 1,
                "ref_id": giving.id,
                "code": WAC_FX_UNAVAILABLE,
                "field": "cost_basis_override",
                "params": {"pairs": ["PYG/EUR"], "pair_details": [{"pair": "PYG/EUR", "dates": [PYG_DAY.isoformat()]}]},
            }
        ], f"Expected one {WAC_FX_UNAVAILABLE} on split 1, the TRANSFER pair's: {_render(response.issues)}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("giving_first", [pytest.param(True, id="giving-side-as-id-a"), pytest.param(False, id="giving-side-as-id-b")])
    async def test_promote_into_a_transfer_takes_the_cost_off_the_giving_side(self, world, giving_first):
        """RED until decision 47: an ADJUSTMENT −4 on ``source`` carrying a cost — 100 EUR, as a split of decision 47
        leaves it — and an ADJUSTMENT +4 on ``dest`` carrying 42 EUR, promoted into a TRANSFER, in either order: the
        promote commits; the giving side loses ``cost_basis_override`` and ``cost_basis_currency`` — its new type takes
        no cost basis, ``cost_basis_allowed(TRANSFER, −4)`` is False — and the receiving side keeps its 42 EUR.

        Today the promote keeps both costs: a TRANSFER giving leg carrying a cost no screen can show or edit.
        """
        giving = _stored_row(world, broker=world.source, tx_type=TransactionType.ADJUSTMENT, quantity=-TRANSFER_QUANTITY, cost=Currency(code=EUR, amount=UNIT_COST))
        receiving = _stored_row(world, broker=world.dest, tx_type=TransactionType.ADJUSTMENT, quantity=TRANSFER_QUANTITY, cost=STORED_COST)
        world.session.add_all([giving, receiving])
        await world.session.flush()
        sides = (cost_basis_allowed(TransactionType.TRANSFER, -TRANSFER_QUANTITY), cost_basis_allowed(TransactionType.TRANSFER, TRANSFER_QUANTITY))
        assert sides == (False, True), f"precondition broken: TX_TYPE_METADATA must forbid a cost on a TRANSFER's giving side and allow it on its receiving side; cost_basis_allowed gives {sides}"
        first, second = (giving, receiving) if giving_first else (receiving, giving)

        response = await _run_batch(world, commit=True, promotes=[{"id_a": first.id, "id_b": second.id}])

        assert response.committed is True and response.issues == [], f"The promote of {first.id} and {second.id} into a TRANSFER was refused: {_render(response.issues)}"
        assert [(result.operation, result.index, tuple(result.ids), result.status) for result in response.results] == [("promote", 0, (first.id, second.id), "success")]
        assert await _legs_now(world, giving, receiving) == {
            "giving": (TransactionType.TRANSFER, -TRANSFER_QUANTITY, receiving.id, None, None),
            "receiving": (TransactionType.TRANSFER, TRANSFER_QUANTITY, giving.id, STORED_COST.amount, STORED_COST.code),
        }


# ============================================================================
# RED AND GUARDS — W-B69: AN AUTO COST OVER A POOL WITH AN UNREADABLE ROW
# ============================================================================

# The cure's TXValidationCode.AUTO_COST_UNREADABLE, as a literal: the member does not exist before it.
AUTO_COST_UNREADABLE = "autoCostUnreadable"
# W-B74's TXValidationCode.LEDGER_UNREADABLE, as a literal: the replay's refusal of a broker whose rows hold a quantity or
# an amount that reads None, which a W-B69 batch replaying source also gets once that cure is in.
LEDGER_UNREADABLE = "ledgerUnreadable"
# The two columns (a) and (d) plant 'n/a' in: RealDecimal reads either as None since W-B58.
UNREADABLE_COLUMNS = ("quantity", "amount")
# Every column a plant may overwrite: those two, and a stored cost basis (the contract's addition of 17/10).
PLANTABLE_COLUMNS = (*UNREADABLE_COLUMNS, "cost_basis_override")
AUTO_OPERATIONS = ("create", "update")
ENDPOINTS = (pytest.param(True, id="commit"), pytest.param(False, id="validate"))
# The incoming rows that take a cost basis, and the per-unit cost they are stored with: the 3 000 EUR the planted BUY pays
# for its 10 units, so that every readable plant averages the same.
INCOMING_KINDS = ("adjustment", "receiving-transfer")
PLANTED_COST = -LATER_BUY_PAID / BUY_QUANTITY
PLANT_LABELS = {
    "buy": f"BUY +{BUY_QUANTITY} for {-LATER_BUY_PAID} EUR",
    "adjustment": f"ADJUSTMENT +{BUY_QUANTITY} stored at {PLANTED_COST} EUR a unit",
    "receiving-transfer": f"receiving TRANSFER +{BUY_QUANTITY} stored at {PLANTED_COST} EUR a unit",
}
# source's pool with the planted row readable: (1 000 + 3 000) / 20.
READABLE_POOL_COST = (BUY_QUANTITY * UNIT_COST - LATER_BUY_PAID) / (2 * BUY_QUANTITY)
# What today's average makes of that pool with one column of the planted row unreadable: the defect, for the red messages.
TODAY_OVER_AN_UNREADABLE = {
    "quantity": "the average skips the row whose quantity reads None: 1 000 / 10 = 100, where the readable pool gives 200",
    "amount": "the average takes the BUY whose amount reads None as a free acquisition: 1 000 / 20 = 50, where the readable pool gives 200",
    "cost_basis_override": "the average takes the row whose cost basis reads None as an acquisition of unknown cost, entering at zero: 1 000 / 20 = 50, where the readable pool gives 200",
}
UI_LANGUAGES = ("en", "it", "fr", "es")
# What _raw_rows reads of a row: its raw values, and the storage class of the three columns a plant may overwrite.
_RAW_KINDS = ", ".join(f"typeof({column}) AS {column}_kind" for column in ("quantity", "amount", "cost_basis_override"))
_RAW_COLUMNS = f"id, type, date, quantity, amount, currency, related_transaction_id, cost_basis_override, cost_basis_currency, description, tags, {_RAW_KINDS}"
# A plant takes an id this far past every id in use, and the rows written after it the ids that follow: a number this large
# in an issue's text can only be one of them (``_ids_named``). Below it a number may be anything — the count, a day, an
# amount, or an id the lane reuses: each test rolls back, the AUTOINCREMENT counter with it, so the ``world``'s BUY is id 1
# in a fresh lane, as the count of an issue may be.
_ID_GAP = 1_000_000


async def _plant(world: World, *, kind: str = "buy", unreadable: tuple[str, ...] = (), day: date = LATER_BUY_DAY, asset_id: int | None = None) -> int:
    """A row of 10 units on ``source`` on ``day`` — of the ``world``'s asset, or ``asset_id`` — stored like any row, then
    each column of ``unreadable`` overwritten with 'n/a' through the same session; its id.

    ``kind``: ``buy``, a BUY paying 3 000 EUR, its cost basis NULL as a BUY's is; or an incoming row that takes a cost
    basis, stored at 300 EUR a unit (``PLANTED_COST``): ``adjustment``, an ADJUSTMENT +10, or ``receiving-transfer``, a
    TRANSFER +10 linked both ways to its giving leg on a third broker of the test's own, which no batch here touches.
    Readable, any of them is the second acquisition of ``source``'s pool, worth 3 000 EUR. Its id is ``_ID_GAP`` past every
    id in use, so that it, and every row written after it, can be told from any small number in an issue's text. Unreadable,
    what the case rests on is checked here, so no test refuses or accepts a row it only assumes unreadable: SQLite keeps the
    text (``typeof`` 'text', so not NULL: the cure's test for a stored cost basis); the facade's filters —
    ``compute_wac_iterative``: quantity not NULL and not 0 — still select the row; and its ORM copy, expired so that every
    later load re-reads it, loads with None in each overwritten column (``RealDecimal``, W-B58).
    """
    session = world.session
    now = utcnow()
    description = f"{world.marker} W-B69 planted {kind}"
    planted_id = ((await session.execute(select(func.max(Transaction.id)))).scalar_one() or 0) + _ID_GAP
    common = {"id": planted_id, "broker_id": world.source.id, "asset_id": asset_id or world.asset.id, "date": day, "quantity": BUY_QUANTITY, "description": description, "created_at": now, "updated_at": now}
    if kind == "buy":
        row = Transaction(type=TransactionType.BUY, amount=LATER_BUY_PAID, currency=EUR, **common)
    elif kind in INCOMING_KINDS:
        incoming_type = TransactionType.ADJUSTMENT if kind == "adjustment" else TransactionType.TRANSFER
        row = Transaction(type=incoming_type, amount=Decimal("0"), currency=None, cost_basis_override=PLANTED_COST, cost_basis_currency=EUR, **common)
    else:
        raise ValueError(f"unknown plant kind {kind!r}")
    session.add(row)
    await session.flush()
    row_id = row.id
    if kind == "receiving-transfer":
        # Its giving leg's broker allows shorting: it holds none of the units it gave, and none of these batches replays it.
        sender = Broker(name=f"{world.marker} W-B69 sender", description="W-B69: the broker the planted TRANSFER came from", allow_cash_overdraft=True, allow_asset_shorting=True, created_at=now, updated_at=now)
        session.add(sender)
        await session.flush()
        giving = Transaction(broker_id=sender.id, asset_id=row.asset_id, type=TransactionType.TRANSFER, date=day, quantity=-BUY_QUANTITY, amount=Decimal("0"), description=description, created_at=now, updated_at=now)
        session.add(giving)
        await session.flush()
        giving.related_transaction_id, row.related_transaction_id = row_id, giving.id
        await session.flush()
    if not unreadable:
        return row_id
    for column in unreadable:
        assert column in PLANTABLE_COLUMNS, f"scaffold: a plant overwrites {PLANTABLE_COLUMNS}, not {column!r}"
        await session.execute(text(f"UPDATE transactions SET {column} = 'n/a' WHERE id = :id"), {"id": row_id})
    kinds = (await session.execute(text(f"SELECT {', '.join(f'typeof({column}) AS {column}' for column in PLANTABLE_COLUMNS)} FROM transactions WHERE id = :id"), {"id": row_id})).one()._asdict()
    assert {column: kinds[column] for column in unreadable} == dict.fromkeys(unreadable, "text"), f"setup: the planted {kind} id={row_id} must hold 'n/a' as text in {unreadable}; typeof = {kinds}"
    selected = (await session.execute(select(func.count()).select_from(Transaction).where(Transaction.id == row_id, Transaction.quantity.is_not(None), Transaction.quantity != 0))).scalar_one()
    assert selected == 1, f"setup: the facade's filters (quantity IS NOT NULL, quantity != 0) must still select the planted {kind} id={row_id}, or it is not in the pool"
    session.expire(row)
    loaded = (await session.execute(select(Transaction).where(Transaction.id == row_id).execution_options(populate_existing=True))).scalar_one()
    read = {column: getattr(loaded, column) for column in PLANTABLE_COLUMNS}
    assert {column: read[column] for column in unreadable} == dict.fromkeys(unreadable), f"setup: RealDecimal must read the 'n/a' of id={row_id} as None (W-B58); the row loads {read}"
    return row_id


async def _world_brokers(world: World) -> list[int]:
    """Every broker of the test's own, by its marker: ``source``, ``dest``, and the one a ``receiving-transfer`` plant adds."""
    statement = select(Broker.id).where(Broker.name.startswith(world.marker, autoescape=True)).order_by(Broker.id)
    return list((await world.session.execute(statement)).scalars())


async def _other_asset(world: World) -> int:
    """A second asset of the test's own, in EUR: its rows lie outside every pool of the ``world``'s asset."""
    now = utcnow()
    other = Asset(display_name=f"{world.marker} other asset", asset_type=AssetType.STOCK, currency=EUR, created_at=now, updated_at=now)
    world.session.add(other)
    await world.session.flush()
    return other.id


@dataclass
class AutoBatch:
    """A batch whose row ``operation`` ``index`` asks for an Auto cost over ``source``'s pool (``_auto_batch``)."""

    operation: str
    index: int
    creates: list[dict]
    updates: list[dict]
    #: The stored row an update recomputes; None for a create, whose id the batch's results give (``_created_id``).
    row_id: int | None


async def _auto_batch(world: World, operation: str, mode: str, *, alone: bool = False) -> AutoBatch:
    """The Auto row, in ``mode``, and the rows its batch sends: the receiving leg of a TRANSFER pair source → dest, whose
    pool is its partner's broker, ``source``, up to the move, without the two legs (``_auto_cost_source``).

    ``create``: the pair (``_created_pair``), the receiving leg at index 1. ``update``: the stored pair (``_store``, the
    receiving leg at 42 EUR), both legs given the same new notes — a pair keeps one description — and the receiving leg
    the mode, at index 1. ``alone``: the receiving leg's update alone, at index 0 — the one batch that replays no day of
    ``source`` (the balance replay covers the brokers of the updated rows, ``earliest_date_by_broker``).
    """
    if operation == "create":
        assert not alone, "scaffold: a receiving leg is created with its giving leg"
        return AutoBatch(operation="create", index=1, creates=_created_pair(world, cost_basis_mode=mode), updates=[], row_id=None)
    stored = await _store(world, "transfer_in", cost=STORED_COST)
    giving, receiving = stored.rows
    if alone:
        return AutoBatch(operation="update", index=0, creates=[], updates=[{"id": receiving.id, "cost_basis_mode": mode}], row_id=receiving.id)
    notes = f"{world.marker} notes edited with the Auto cost"
    return AutoBatch(operation="update", index=1, creates=[], updates=[{"id": giving.id, "description": notes}, {"id": receiving.id, "description": notes, "cost_basis_mode": mode}], row_id=receiving.id)


async def _as_the_endpoint(world: World, *, commit: bool, creates: list[dict] | None = None, updates: list[dict] | None = None, splits: list[dict] | None = None) -> TXBatchResponse:
    """The batch as ``POST /transactions/commit`` (``commit=True``) or ``/validate`` runs it, its transaction included:
    /commit keeps what the service answers committed and rolls back the rest, /validate always rolls back
    (``api/v1/transactions.py``). A savepoint stands in for the request's transaction, as in ``_commit_as_the_endpoint``;
    the session fixture still rolls everything back. Read the rows back by id afterwards (``_raw_rows``, ``_rows_by_id``),
    never through a copy the rollback expired. A batch refuses with issues: one that raises fails the test.
    """
    savepoint = await world.session.begin_nested()
    try:
        response = await _run_batch(world, commit=commit, creates=creates, updates=updates, splits=splits)
    except Exception as error:  # the contract: a refusal is an issue, nothing raises
        pytest.fail(f"W-B69: the batch must answer with its issues, never raise; it raised {type(error).__name__}: {error!r}")
    if commit and response.committed:
        await savepoint.commit()
    else:
        await savepoint.rollback()
    return response


async def _raw_rows(world: World, broker_ids: list[int]) -> dict[int, dict]:
    """Every row of ``broker_ids`` as SQLite holds it in the session's transaction, by id: raw values, and the storage class
    of the three columns a plant may overwrite — what the user finds once the request is over, the 'n/a' included."""
    statement = text(f"SELECT {_RAW_COLUMNS} FROM transactions WHERE broker_id IN :brokers ORDER BY id").bindparams(bindparam("brokers", expanding=True))
    return {row.id: row._asdict() for row in (await world.session.execute(statement, {"brokers": broker_ids})).all()}


def _changed(before: dict[int, dict], after: dict[int, dict]) -> dict[int, tuple]:
    """The rows two ``_raw_rows`` reads disagree on, by id: ``(before, after)``, None for a row absent on one side."""
    return {tx_id: (before.get(tx_id), after.get(tx_id)) for tx_id in sorted(set(before) | set(after)) if before.get(tx_id) != after.get(tx_id)}


async def _rows_by_id(world: World, ids: list[int]) -> dict[int, tuple]:
    """``(type, quantity, related_transaction_id, cost_basis_override, cost_basis_currency)`` of each row of ``ids`` the
    database still holds, re-read (``populate_existing``): a deleted row is absent."""
    statement = select(Transaction).where(Transaction.id.in_(ids)).execution_options(populate_existing=True)
    return {row.id: (row.type, row.quantity, row.related_transaction_id, row.cost_basis_override, row.cost_basis_currency) for row in (await world.session.execute(statement)).scalars()}


def _answered(response: TXBatchResponse, operation: str, index: int) -> tuple[Decimal, str] | None:
    """The Auto cost the batch answered for row ``operation`` ``index`` (``wac_results``), or None."""
    for item in response.wac_results or []:
        if item.operation == operation and item.index == index and item.wac is not None:
            return item.wac.amount, item.wac.code
    return None


def _created_id(response: TXBatchResponse, index: int) -> int:
    """The id of create ``index``, from the batch's results."""
    return next(result.ids[0] for result in response.results if result.operation == "create" and result.index == index)


def _endpoint(commit: bool) -> str:
    return "/commit" if commit else "/validate"


def _verdict(response: TXBatchResponse, operation: str, index: int) -> str:
    """What a batch did, for a failure message: committed, and with which Auto cost on row ``operation`` ``index``;
    validated clean with it; or refused, and for what."""
    cost = _show(_answered(response, operation, index) or (None, None))
    if response.committed:
        return f"the batch committed, saving an Auto cost of {cost} on {operation} {index}"
    if not response.issues:
        return f"the batch validated clean, answering an Auto cost of {cost} on {operation} {index}, the cost /commit saves"
    return f"the batch was refused with [{_render(response.issues)}] (Auto cost answered on {operation} {index}: {cost})"


async def _assert_refused_unreadable(world: World, response: TXBatchResponse, batch: AutoBatch, *, count: int, pool: str, mode: str, today: str, commit: bool, brokers: list[int], before: dict[int, dict], ledger: tuple[int, int] | None) -> None:
    """(a)'s assertions: one issue ``autoCostUnreadable`` ``{"count": count}`` on the Auto row's operation and index,
    ``ref_id`` None, ``field`` ``cost_basis_override`` — so no id in its ``ref_id`` or its ``params`` —; not committed; no
    transaction id in its text either (the pool may be another user's broker: ``_ids_named``); and every row of
    ``brokers`` as it was, the planted 'n/a' included. ``pool`` says what the pool holds, ``today`` what today's average
    makes of it.

    ``ledger`` is W-B74's part: ``(broker id, N)`` when the batch replays a broker whose rows hold N quantities or amounts
    that read None — then exactly two issues, the second ``ledgerUnreadable`` ``{brokerId, count: N}`` at index -1 —, None
    when it replays none: exactly one issue. Checked after W-B69's part, so a red names the missing half."""
    auto = _unreadable_issue(batch.operation, batch.index, ref_id=None, count=count)
    views = [_issue_view(issue) for issue in response.issues]
    where = f"{batch.operation} {batch.index} ({mode}, {_endpoint(commit)})"
    on_the_row = [view for view in views if view["code"] == AUTO_COST_UNREADABLE]
    assert (response.committed, on_the_row) == (False, [auto]), f"W-B69: an Auto cost over a pool with {pool} must be refused with {AUTO_COST_UNREADABLE} {{count: {count}}} on {where}; today {_verdict(response, batch.operation, batch.index)} — {today}"
    _assert_with_the_ledger(response, [auto], ledger, where)
    named = _ids_named(next(issue for issue in response.issues if issue.code == AUTO_COST_UNREADABLE), set(before) | {tx_id for result in response.results for tx_id in result.ids})
    assert named == [], f"W-B69: the pool may be another user's broker, so {AUTO_COST_UNREADABLE} names no transaction; it names {named}: {_render(response.issues)}"
    changed = _changed(before, await _raw_rows(world, brokers))
    assert changed == {}, f"W-B69: the refused batch changed rows of the test's brokers (before, after): {changed}"


def _ledger_issue(broker_id: int, count: int) -> dict:
    """The broker-level issue of W-B74's cure, as ``_issue_view`` shows it."""
    return {"operation": "create", "index": -1, "ref_id": None, "code": LEDGER_UNREADABLE, "field": None, "params": {"brokerId": broker_id, "count": count}}


def _in_order(views: list[dict]) -> list[dict]:
    """Issue views in a fixed order — by code, operation, index —: the contract counts the issues, it does not order them."""
    return sorted(views, key=lambda view: (view["code"] or "", view["operation"], view["index"]))


def _assert_with_the_ledger(response: TXBatchResponse, expected: list[dict], ledger: tuple[int, int] | None, where: str) -> None:
    """W-B74's part of a W-B69 refusal: the issues are exactly ``expected``, plus ``ledgerUnreadable`` ``{brokerId, count}``
    when ``ledger`` names the replayed broker and its count — and nothing else."""
    views = [_issue_view(issue) for issue in response.issues]
    if ledger is None:
        message = f"W-B74: the replay of source reads no quantity or amount that reads None — a stored cost basis is read by no balance —, so the batch keeps exactly its {len(expected)} W-B69 issue(s) on {where}, and no {LEDGER_UNREADABLE}; it answers [{_render(response.issues)}]"
        assert _in_order(views) == _in_order(expected), message
        return
    broker_id, count = ledger
    assert _in_order(views) == _in_order([*expected, _ledger_issue(broker_id, count)]), (
        f"W-B74: the batch replays broker {broker_id} (source), whose rows hold {count} quantity or amount that reads None, so beside its W-B69 issue on {where} it must carry "
        f"{LEDGER_UNREADABLE} {{brokerId: {broker_id}, count: {count}}} at index -1 — exactly these {len(expected) + 1} issues; today it answers [{_render(response.issues)}]"
    )


async def _assert_takes(world: World, response: TXBatchResponse, batch: AutoBatch, *, cost: Decimal, commit: bool, what: str) -> None:
    """A guard's assertions: no issue, committed on /commit; the Auto row answered ``cost`` EUR; and /commit saved it."""
    assert (response.committed, response.issues) == (commit, []), f"{what} was refused ({_endpoint(commit)}): {_render(response.issues)}"
    assert _answered(response, batch.operation, batch.index) == (cost, EUR), f"{what}: expected an Auto cost of {cost} {EUR}; {_verdict(response, batch.operation, batch.index)}"
    if commit:
        row_id = batch.row_id if batch.row_id is not None else _created_id(response, batch.index)
        stored = await _stored_cost(world, row_id)
        assert stored == (cost, EUR), f"{what}: the Auto row id={row_id} was committed with {_show(stored)}, not {cost} {EUR}"


def _leg_shown(raw: dict | None) -> str:
    """A row as ``_raw_rows`` reads it, for a failure message."""
    if raw is None:
        return "gone"
    return f"{raw['type']} {raw['quantity']} with cost {raw['cost_basis_override']} {raw['cost_basis_currency']}, linked to {raw['related_transaction_id']}"


def _unreadable_issue(operation: str, index: int, *, ref_id: int | None, count: int) -> dict:
    """The issue of W-B69's cure, as ``_issue_view`` shows it."""
    return {"operation": operation, "index": index, "ref_id": ref_id, "code": AUTO_COST_UNREADABLE, "field": "cost_basis_override", "params": {"count": count}}


def _ids_named(issue: TXValidationIssue, ids: set[int]) -> list[int]:
    """The ids of ``ids`` from ``_ID_GAP`` on — the planted rows and every row written after them — that the text of
    ``issue`` names. Its ``ref_id`` and its ``params`` the caller pins whole; below the gap a number of the text may be the
    count, a day or an amount, so the rows written before the plant (the ``world``'s) are not looked for."""
    named = {int(number) for number in re.findall(r"\d+", issue.error)}
    return sorted(named & {tx_id for tx_id in ids if tx_id >= _ID_GAP})


class TestWB69AnAutoRowOverAnUnreadablePool:
    """W-B69 — cases (a), (d), the stored cost basis (the contract's addition of 17/10) and the count: an Auto row whose
    pool holds a row that reads None in its quantity, its amount or a cost basis it stores is refused on its own
    coordinates, and its batch saves nothing. Green since W-B69's cure, but where W-B74 adds its part: a batch replaying
    ``source`` while its rows hold a quantity or an amount that reads None also gets ``ledgerUnreadable`` — contract
    updates, RED until W-B74's cure.

    The Auto row is the receiving leg of a TRANSFER pair source → dest, at index 1 (``_auto_batch``): created, or stored at
    42 EUR and recomputed by an update that also gives both legs new notes. Either way its pool is ``source`` up to the
    move without the pair's two legs — the ``world``'s BUY and the planted row —, and the batch replays ``source`` (the
    giving leg's broker). Before W-B69's cure the batch committed (or validated) with the average of what reads: 100 EUR
    without the row of quantity 'n/a'; 50 with the BUY of amount 'n/a' taken as free, or with the row whose stored cost
    basis is 'n/a' taken at an unknown cost, entering at zero.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    @pytest.mark.parametrize("mode", AUTO_MODES)
    @pytest.mark.parametrize("operation", AUTO_OPERATIONS)
    @pytest.mark.parametrize("column", UNREADABLE_COLUMNS)
    async def test_auto_row_over_a_pool_with_an_unreadable_row_is_refused(self, world, column, operation, mode, commit):
        """W-B69 (a) — and (d) with ``column`` amount: ``autoCostUnreadable`` on the Auto row's operation and index,
        ``ref_id`` None, ``field`` ``cost_basis_override``, ``params`` ``{"count": 1}``; not committed; no transaction id in
        the issue, its params or its text (the pool may be another user's broker); and every row of the test's brokers as
        it was, the planted 'n/a' included: refused, nothing repaired (``_assert_refused_unreadable``).

        Contract update for W-B74, RED until its cure: the batch replays ``source``, whose planted BUY's quantity or amount
        reads None, so the issues are exactly two — that one, and ``ledgerUnreadable`` ``{brokerId: source, count: 1}`` at
        index -1."""
        await _plant(world, unreadable=(column,))
        batch = await _auto_batch(world, operation, mode)
        source_id, brokers = world.source.id, await _world_brokers(world)
        before = await _raw_rows(world, brokers)

        response = await _as_the_endpoint(world, commit=commit, creates=batch.creates, updates=batch.updates)

        pool = f"an unreadable row (a {PLANT_LABELS['buy']} of source whose {column} is 'n/a')"
        await _assert_refused_unreadable(world, response, batch, count=1, pool=pool, mode=mode, today=TODAY_OVER_AN_UNREADABLE[column], commit=commit, brokers=brokers, before=before, ledger=(source_id, 1))

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    @pytest.mark.parametrize("operation", AUTO_OPERATIONS)
    @pytest.mark.parametrize("kind", INCOMING_KINDS)
    async def test_auto_row_over_a_pool_with_an_unreadable_stored_cost_basis_is_refused(self, world, kind, operation, commit):
        """W-B69, the contract's addition of 17/10: a pool row that stores a cost basis — ``cost_basis_override`` not NULL
        in SQL — which reads None is unreadable like a quantity or an amount. (a)'s assertions, ``{"count": 1}``.

        The row is an incoming one that takes a cost basis, dated before the move: an ADJUSTMENT +10, or a receiving
        TRANSFER +10 (its giving leg on a third broker of the test's), stored at 300 EUR a unit, then 'n/a'; its quantity
        and its amount read. Before W-B69's cure the average took it as an acquisition of unknown cost, entering at zero:
        the Auto row got 1 000 / 20 = 50 EUR, saved by /commit and answered by /validate. A BUY's NULL cost basis is
        legitimate and refuses nothing: the readable guards hold that.

        W-B74, a guard of its own (green before and after its cure): the batch replays ``source``, but no balance reads a
        cost basis — the replay counts quantities and amounts —, so the issue stays exactly one, no ``ledgerUnreadable``.
        """
        await _plant(world, kind=kind, unreadable=("cost_basis_override",))
        batch = await _auto_batch(world, operation, "auto")
        brokers = await _world_brokers(world)
        before = await _raw_rows(world, brokers)

        response = await _as_the_endpoint(world, commit=commit, creates=batch.creates, updates=batch.updates)

        pool = f"an unreadable stored cost basis (a {PLANT_LABELS[kind]} on source, its cost_basis_override then 'n/a')"
        await _assert_refused_unreadable(world, response, batch, count=1, pool=pool, mode="auto", today=TODAY_OVER_AN_UNREADABLE["cost_basis_override"], commit=commit, brokers=brokers, before=before, ledger=None)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("plants", "count", "ledger", "today"),
        [
            pytest.param((("buy", ("quantity",)), ("buy", ("amount",))), 2, 2, "the average skips the first row and takes the second as a free acquisition: 1 000 / 20 = 50", id="two-rows"),
            pytest.param((("buy", ("quantity", "amount")),), 1, 1, "the average skips the row: 1 000 / 10 = 100", id="one-row-quantity-and-amount"),
            pytest.param((("adjustment", ("quantity", "cost_basis_override")),), 1, 1, "the average skips the row: 1 000 / 10 = 100", id="one-row-quantity-and-cost-basis"),
        ],
    )
    async def test_count_is_the_number_of_unreadable_rows(self, world, plants, count, ledger, today):
        """W-B69: ``count`` counts rows, not values. Two rows of the pool unreadable — a BUY by its quantity, the next day's
        BUY by its amount — give ``{"count": 2}``; one row unreadable in two columns gives ``{"count": 1}``: a BUY by its
        quantity and its amount, DERIVED from «the number of such rows», or an ADJUSTMENT +10 by its quantity and its stored
        cost basis, as the contract's addition of 17/10 says. (a)'s assertions, on the create of the pair on /commit. Before
        W-B69's cure the batch committed: at 50 EUR for the two rows (the first skipped, the second free: 1 000 / 20), at
        100 for the one (skipped: 1 000 / 10).

        Contract update for W-B74, RED until its cure: creating the pair replays ``source``, so beside that issue
        ``ledgerUnreadable`` ``{brokerId: source, count}`` at index -1 — ``count`` the rows whose quantity or amount reads
        None, the same rows here (2, 1, 1): the ADJUSTMENT's quantity reads None, its cost basis adds no row."""
        for offset, (kind, columns) in enumerate(plants):
            await _plant(world, kind=kind, unreadable=columns, day=LATER_BUY_DAY + timedelta(days=offset))
        batch = await _auto_batch(world, "create", "auto")
        source_id, brokers = world.source.id, await _world_brokers(world)
        before = await _raw_rows(world, brokers)

        response = await _as_the_endpoint(world, commit=True, creates=batch.creates)

        shape = " and ".join(f"a {PLANT_LABELS[kind]} whose {' and '.join(columns)} read 'n/a'" for kind, columns in plants)
        await _assert_refused_unreadable(world, response, batch, count=count, pool=f"{len(plants)} unreadable row(s) — {shape}", mode="auto", today=today, commit=True, brokers=brokers, before=before, ledger=(source_id, ledger))

    @pytest.mark.asyncio
    async def test_unreadable_row_of_another_asset_is_refused_by_the_replay_alone(self, world):
        """Contract update for W-B74, RED until its cure — formerly the case ``another-asset-create`` of the guard
        ``test_unreadable_row_outside_the_pool_refuses_nothing``. A BUY of quantity 'n/a' of another asset on ``source`` lies
        outside the Auto row's pool, so W-B69 refuses nothing: no ``autoCostUnreadable``. But creating the pair replays
        ``source``, whose rows hold it: exactly one issue, ``ledgerUnreadable`` ``{brokerId: source, count: 1}`` at index
        -1; not committed, nothing saved. Today the batch commits, the Auto row at the ``world``'s BUY alone, 100 EUR."""
        await _plant(world, unreadable=("quantity",), asset_id=await _other_asset(world))
        batch = await _auto_batch(world, "create", "auto")
        source_id, brokers = world.source.id, await _world_brokers(world)
        before = await _raw_rows(world, brokers)

        response = await _as_the_endpoint(world, commit=True, creates=batch.creates)

        views = [_issue_view(issue) for issue in response.issues]
        assert (response.committed, views) == (False, [_ledger_issue(source_id, 1)]), (
            f"W-B74: creating the pair replays source (broker {source_id}), whose rows hold a BUY of another asset whose quantity reads None: the batch must be refused by the replay alone — "
            f"exactly one issue, {LEDGER_UNREADABLE} {{brokerId: {source_id}, count: 1}} at index -1, and no {AUTO_COST_UNREADABLE}, the row lying outside the Auto row's pool; today {_verdict(response, batch.operation, batch.index)}"
        )
        changed = _changed(before, await _raw_rows(world, brokers))
        assert changed == {}, f"W-B74: the refused batch changed rows of the test's brokers (before, after): {changed}"


class TestWB69TheSplitOfATransferOverAnUnreadablePool:
    """W-B69 (b): the split of a TRANSFER pair hands its giving leg over at the Auto cost of ``source`` up to the move,
    without the leg (decision 47: ``_handover_cost``, in the batch's WAC stage). Refused since W-B69's cure when that pool
    holds an unreadable row — and, a contract update RED until W-B74's cure, with ``ledgerUnreadable`` too, the split
    replaying ``source``; a guard with every row readable."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    @pytest.mark.parametrize("column", UNREADABLE_COLUMNS)
    async def test_split_whose_handover_pool_holds_an_unreadable_row_is_refused(self, world, column, commit):
        """W-B69 (b): ``autoCostUnreadable`` on split 1 — index 0 is the split of an FX_CONVERSION pair, which needs no
        cost —, ``ref_id`` the giving leg (as ``wacFxUnavailable`` on a split), ``field`` ``cost_basis_override``,
        ``params`` ``{"count": 1}``; not committed; the pair intact — two TRANSFER legs linked both ways, the receiving one
        at its 42 EUR — and every other row as it was. Before W-B69's cure the split went through and handed the giving leg
        over at the average of what reads.

        Contract update for W-B74, RED until its cure: the split replays the brokers of its legs — ``dest``, then
        ``source`` —, and ``source`` holds the BUY whose quantity or amount reads None: the issues are exactly two, that
        one and ``ledgerUnreadable`` ``{brokerId: source, count: 1}`` at index -1."""
        await _plant(world, unreadable=(column,))
        sold, bought = await _fx_conversion_pair(world)
        stored = await _store(world, "transfer_in", cost=STORED_COST)
        giving, receiving = stored.rows
        giving_id, source_id, brokers = giving.id, world.source.id, [world.source.id, world.dest.id]
        before = await _raw_rows(world, brokers)

        response = await _as_the_endpoint(world, commit=commit, splits=[{"id_a": sold.id, "id_b": bought.id}, {"id_a": giving.id, "id_b": receiving.id}])

        after = await _raw_rows(world, brokers)
        expected = _unreadable_issue("split", 1, ref_id=giving_id, count=1)
        on_the_split = [view for view in (_issue_view(issue) for issue in response.issues) if view["code"] == AUTO_COST_UNREADABLE]
        assert (response.committed, on_the_split) == (False, [expected]), (
            f"W-B69: the split of a TRANSFER pair whose giving leg's handover pool holds an unreadable row (a BUY of source whose {column} is 'n/a') must be refused with "
            f"{AUTO_COST_UNREADABLE} {{count: 1}} on split 1, ref_id the giving leg id={giving_id} ({_endpoint(commit)}); today the batch answers committed={response.committed}, "
            f"issues [{_render(response.issues)}], and leaves the giving leg {_leg_shown(after.get(giving_id))} — {TODAY_OVER_AN_UNREADABLE[column]}"
        )
        _assert_with_the_ledger(response, [expected], (source_id, 1), f"split 1 ({_endpoint(commit)})")
        changed = _changed(before, after)
        assert changed == {}, f"W-B69: the refused split changed rows of source and dest (before, after): {changed}"

    @pytest.mark.asyncio
    async def test_split_over_a_readable_pool_hands_the_giving_leg_over_at_its_average(self, world):
        """Guard, green today and after W-B69: with the planted BUY readable the split commits; the giving leg leaves as an
        ADJUSTMENT −4 at ``source``'s average, (1 000 + 3 000) / 20 = 200 EUR, and the receiving leg becomes an ADJUSTMENT
        +4 that keeps its 42 EUR."""
        await _plant(world)
        stored = await _store(world, "transfer_in", cost=STORED_COST)
        giving_id, receiving_id = stored.rows[0].id, stored.rows[1].id

        response = await _as_the_endpoint(world, commit=True, splits=[{"id_a": giving_id, "id_b": receiving_id}])

        assert response.committed is True and response.issues == [], f"The split of a TRANSFER pair over a readable pool was refused: {_render(response.issues)}"
        assert await _rows_by_id(world, [giving_id, receiving_id]) == {
            giving_id: (TransactionType.ADJUSTMENT, -TRANSFER_QUANTITY, None, READABLE_POOL_COST, EUR),
            receiving_id: (TransactionType.ADJUSTMENT, TRANSFER_QUANTITY, None, STORED_COST.amount, STORED_COST.code),
        }


class TestWB69GuardsReadablePoolsAndRowsOutsideThePool:
    """Guards, green before and after W-B69's and W-B74's cures: an Auto row over a readable pool takes its average, and an
    unreadable row the pool does not hold refuses nothing in a batch that replays ``dest`` alone. Under a batch that
    replays ``source`` the same row is W-B74's to refuse: ``test_unreadable_row_of_another_asset_is_refused_by_the_replay_alone``."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    @pytest.mark.parametrize("mode", AUTO_MODES)
    @pytest.mark.parametrize("operation", AUTO_OPERATIONS)
    async def test_auto_row_over_a_readable_pool_takes_its_average(self, world, operation, mode, commit):
        """Guard: (a)'s batches with the planted BUY readable — its cost basis NULL, as a BUY's is: no issue, and the Auto
        row's cost is ``source``'s average, (1 000 + 3 000) / 20 = 200 EUR — answered on /validate, answered and saved on
        /commit."""
        await _plant(world)
        batch = await _auto_batch(world, operation, mode)

        response = await _as_the_endpoint(world, commit=commit, creates=batch.creates, updates=batch.updates)

        await _assert_takes(world, response, batch, cost=READABLE_POOL_COST, commit=commit, what=f"An Auto {operation} ({mode}) over a readable pool")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    @pytest.mark.parametrize("operation", AUTO_OPERATIONS)
    @pytest.mark.parametrize("kind", INCOMING_KINDS)
    async def test_auto_row_over_a_readable_stored_cost_basis_takes_its_average(self, world, kind, operation, commit):
        """Guard: the stored-cost-basis case with the planted row readable — an ADJUSTMENT +10 or a receiving TRANSFER +10
        at 300 EUR a unit: no issue, and the Auto row's cost is ``source``'s average, (1 000 + 10 × 300) / 20 = 200 EUR —
        answered on /validate, answered and saved on /commit. A cure that counted every stored cost basis, not only one that
        reads None, turns it red."""
        await _plant(world, kind=kind)
        batch = await _auto_batch(world, operation, "auto")

        response = await _as_the_endpoint(world, commit=commit, creates=batch.creates, updates=batch.updates)

        await _assert_takes(world, response, batch, cost=READABLE_POOL_COST, commit=commit, what=f"An Auto {operation} over a pool holding a readable {PLANT_LABELS[kind]}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("where", "operation"),
        [
            pytest.param("another-asset", "update", id="another-asset-update"),
            pytest.param("after-the-move", "update", id="after-the-move-update"),
        ],
    )
    async def test_unreadable_row_outside_the_pool_refuses_nothing(self, world, where, operation):
        """Guard: a BUY of quantity 'n/a' on ``source`` that the pool does not hold — of another asset, or dated a week
        after the move, past the pool's date — refuses nothing: the batch commits, and the Auto row takes the ``world``'s
        BUY alone, 100 EUR.

        The update recomputes the receiving leg alone (index 0), so the batch replays ``dest`` alone, never ``source``,
        which holds the row: W-B74's replay refuses a broker holding such a row at every date. The case
        ``another-asset-create`` this guard had replays ``source``, and is now
        ``test_unreadable_row_of_another_asset_is_refused_by_the_replay_alone``.
        """
        if where == "another-asset":
            await _plant(world, unreadable=("quantity",), asset_id=await _other_asset(world))
        else:
            await _plant(world, unreadable=("quantity",), day=MOVE_DAY + timedelta(days=7))
        batch = await _auto_batch(world, operation, "auto", alone=operation == "update")

        response = await _as_the_endpoint(world, commit=True, creates=batch.creates, updates=batch.updates)

        await _assert_takes(world, response, batch, cost=UNIT_COST, commit=True, what=f"An Auto {operation} beside an unreadable row outside the pool ({where}), its average the world's BUY alone,")


class TestWB69TheCodeAndItsMessages:
    """W-B69's code, listed since its cure: ``autoCostUnreadable``. And the gate that holds every code to its message in
    the app's four languages, green before and after each cure that adds a code, since it reads the enum: W-B74's
    ``ledgerUnreadable`` (its own reds in test_transaction_service.py) joins it with its cure."""

    def test_tx_validation_code_has_auto_cost_unreadable(self):
        """RED until W-B69: ``TXValidationCode.AUTO_COST_UNREADABLE == "autoCostUnreadable"`` — the app maps a refusal's code
        to ``transactions.errors.<code>``."""
        member = getattr(TXValidationCode, "AUTO_COST_UNREADABLE", None)

        assert member is not None and member.value == AUTO_COST_UNREADABLE, f"W-B69: TXValidationCode.AUTO_COST_UNREADABLE is {member!r}: expected a member of value {AUTO_COST_UNREADABLE!r}"

    def test_transaction_types_lists_auto_cost_unreadable(self):
        """RED until W-B69: the response ``GET /transactions/types`` builds (``get_transaction_types``) lists
        ``autoCostUnreadable`` in ``validation_codes`` (``VALIDATION_CODE_METADATA``)."""
        response = TXTypesResponse(transaction_types=list(TX_TYPE_METADATA.values()), event_types=EVENT_TYPE_METADATA)

        listed = sorted(info.code for info in response.validation_codes)

        assert AUTO_COST_UNREADABLE in listed, f"W-B69: GET /transactions/types does not list {AUTO_COST_UNREADABLE!r} in validation_codes: {listed}"

    @pytest.mark.parametrize("language", UI_LANGUAGES)
    def test_every_code_has_its_message_in_every_language(self, language):
        """Gate, green today and after W-B69: every ``TXValidationCode`` has a non-empty ``transactions.errors.<code>`` in
        ``language``, read without the English fallback (``load_catalog(language, fallback=False)``). A code without one is
        a refusal the app cannot put in the user's words."""
        messages = flatten(load_catalog(language, fallback=False))

        missing = [code.value for code in TXValidationCode if not str(messages.get(f"transactions.errors.{code.value}") or "").strip()]

        assert missing == [], f"transactions.errors has no {language} message for {missing}"
