"""
Deleting and editing linked charges (lots R4 and R5 of project 66, linked charges).

Why. After R3 a batch can CREATE a charge linked to its parent. Two holes remain. Deleting a parent that still has charges
leaves them pointing at a vanished row: /validate answers ok and /commit dies of a foreign-key integrity error (R4). And a
SAVED charge can be neither linked, unlinked nor moved to another parent by an update (R5), which the Bulk editor needs the
moment a user attaches an existing FEE to a BUY.

The contract (``TXUpdateItem``, ``schemas/transactions/transactions.py``; the stage ``link_charges`` of ``charges.py``, on the
FINAL state of the batch, the same on /validate and /commit):

R5 — updates link and unlink:

- ``parent_transaction_id`` on an update: absent = unchanged; ``0`` = unlink (the row stays, as a row of its own; a no-op on
  a row without a parent; always allowed); ``n > 0`` = link to the saved parent ``n``. Negative: ``chargeParentIdInvalid``
  {parent_transaction_id}, at parse. ``parent_ref`` (max 36): link a SAVED charge to a parent CREATED in this batch; with
  ``parent_transaction_id`` (0 included): ``chargeParentTwice``, at parse.
- ``n`` is judged like a create's: a parent that is missing, deleted by the batch or on a broker the user cannot view is
  ``chargeParentNotFound`` {parentId} (never ``accessDenied``); then the R2 rule. An unknown ``parent_ref`` is
  ``chargeParentRefNotFound`` {parentRef}. Their issues are ``operation`` "update", ``index`` the position in
  ``updates[]``, ``ref_id`` the charge's id, ``field`` "parent_transaction_id" or "parent_ref".
- N saved charges linked to one parent in one batch work; a charge of parent A updated with B is re-linked to B.
- Rule 6 and rule 8 are ONE predicate: a saved row the batch touches (update, promote by id, split) that still has charges at
  the end of the batch (not deleted, not unlinked or re-linked by the same batch) and whose final type is not a parent type,
  OR that is a leg of a pair, is ``chargesBlockParentType`` {type, chargeIds sorted} on the operation that touched it
  (``ref_id`` the row id). Promoting a DEPOSIT with a FEE into a CASH_TRANSFER is refused; unlinking the FEE in the same
  batch lets it pass. Swaps BUY/SELL and DEPOSIT/WITHDRAWAL of a parent with charges stay valid.
  ``charges_parent_type_issue`` also refuses a paired parent (unit test in ``test_transaction_charges.py``).

R4 — deletes:

- A parent deleted while it still has charges at the end of the batch is ``chargesDeleteIncomplete`` {id, chargeIds sorted,
  the ones left}, on the delete (``operation`` "delete", ``index`` in ``deletes[]``, ``ref_id`` the parent id). Nothing is
  written, on /validate too. Accepted: parent and all charges deleted together (any order); parent deleted with the charges
  unlinked in the same batch; a mix. A charge deleted alone is always accepted.
- ``TransactionService.delete_by_broker`` removes a broker's linked rows without an integrity error.
- The new code has a message under ``transactions.errors.chargesDeleteIncomplete`` in EN, IT, FR and ES.

Reds — fail before R4/R5 (today the update schema forbids the new fields; the delete stage ignores links):

- ``TestAParentIsDeleted``: the refusal and every accepted shape of R4, and the broker delete.
- ``TestUpdatesLinkAndUnlink``: R5 link, unlink, relink, refusals, ``parent_ref``, parse errors.
- ``TestRuleSixOnSavedRows``: the promote of a parent with charges, a type swap.
- ``TestTheDeleteMessageExistsInEveryLanguage``.

Guards — green before R4/R5 and after them:

- ``test_a_charge_deleted_alone_keeps_its_parent_and_the_other_charge`` and ``test_a_linked_charge_edited_in_amount_only``
  (the cure must not narrow what is plainly allowed), and ``test_zero_on_a_row_without_parent_is_a_no_op`` is red only
  because the schema rejects the field today.

C22e (``TestASplitHalfSwappedAndLinkedInOneBatch``): one batch splits a saved CASH_TRANSFER, swaps its receiving half to a
WITHDRAWAL through an update that names the type, and links a FEE to it — accepted (a guard of the server side the Bulk's
C22e fix relies on); the same batch without the type, what the Bulk sends today, is refused (a characterization).

Its world (own brokers that may go below zero, own assets) follows ``test_transaction_charge_links.py``; ids are plain ints,
because a savepoint that rolls a refused batch back expires every ORM object. Linked rows of the setup are written straight
into the session (``parent_transaction_id`` on the ORM row), read back with ``populate_existing``.
"""

import sys
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

# Before any app module that reads DATABASE_URL: this lane's test database.
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.transactions.batch import TXBatchResponse, TXValidationIssue
from backend.app.services.transactions.transaction_service import TransactionService
from backend.app.utils.datetime_utils import utcnow
from scripts.i18n_catalog import flatten, load_catalog

EUR = "EUR"
DAY = date(2025, 2, 3)
UI_LANGUAGES = ("en", "it", "fr", "es")
T = TransactionType
COMMIT = pytest.mark.parametrize("commit", (True, False), ids=("commit", "validate"))


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
    """One test's own data: two assets and two brokers that may go below zero and short (cash and units are never the subject)."""

    session: AsyncSession
    marker: str
    asset_id: int
    other_asset_id: int
    a_id: int
    b_id: int


@pytest_asyncio.fixture
async def world(session) -> World:
    marker = f"charge-edit {uuid.uuid4().hex}"
    now = utcnow()
    assets = [Asset(display_name=f"{marker} asset {n}", asset_type=AssetType.STOCK, currency=EUR, created_at=now, updated_at=now) for n in (1, 2)]
    # Shorting allowed: the type swap BUY to SELL of a row with no holdings behind it must not be refused for its units.
    brokers = [Broker(name=f"{marker} {n}", description="charge edits: a broker of this test", allow_cash_overdraft=True, allow_asset_shorting=True, created_at=now, updated_at=now) for n in ("a", "b")]
    session.add_all([*assets, *brokers])
    await session.flush()
    return World(session=session, marker=marker, asset_id=assets[0].id, other_asset_id=assets[1].id, a_id=brokers[0].id, b_id=brokers[1].id)


# ============================================================================
# HELPERS
# ============================================================================


async def _save(world: World, tx_type: T, broker_id: int, *, asset_id: int | None, parent_id: int | None = None, quantity: str = "0", amount: str = "-5") -> int:
    """A row written straight into the session. Returns its id."""
    now = utcnow()
    row = Transaction(
        broker_id=broker_id,
        asset_id=asset_id,
        type=tx_type,
        date=DAY,
        quantity=Decimal(quantity),
        amount=Decimal(amount),
        currency=EUR,
        description=f"{world.marker} saved {tx_type.value.lower()}",
        parent_transaction_id=parent_id,
        created_at=now,
        updated_at=now,
    )
    world.session.add(row)
    await world.session.flush()
    return row.id


async def _save_buy(world: World, broker_id: int | None = None, asset_id: int | None = None) -> int:
    return await _save(world, T.BUY, broker_id or world.a_id, asset_id=asset_id or world.asset_id, quantity="10", amount="-100")


async def _save_charge(world: World, tx_type: T = T.FEE, *, parent_id: int | None = None, broker_id: int | None = None, asset_id=...) -> int:
    asset = world.asset_id if asset_id is ... else asset_id
    return await _save(world, tx_type, broker_id or world.a_id, asset_id=asset, parent_id=parent_id)


async def _family(world: World) -> tuple[int, int, int]:
    """A saved BUY with a linked FEE and a linked TAX: ``(buy_id, fee_id, tax_id)``."""
    buy_id = await _save_buy(world)
    fee_id = await _save_charge(world, T.FEE, parent_id=buy_id)
    tax_id = await _save_charge(world, T.TAX, parent_id=buy_id)
    return buy_id, fee_id, tax_id


async def _user(world: World, label: str, grants: dict[int, UserRole]) -> int:
    """A user of this test alone, with one access row per ``{broker_id: role}``."""
    tag = uuid.uuid4().hex[:16]
    user = User(username=f"r5_{label}_{tag}", email=f"r5_{label}_{tag}@example.test", hashed_password="not-a-real-hash", is_active=True)
    world.session.add(user)
    await world.session.flush()
    for broker_id, role in grants.items():
        world.session.add(BrokerUserAccess(broker_id=broker_id, user_id=user.id, role=role, share_percentage=Decimal("0")))
    await world.session.flush()
    return user.id


def _new_buy(world: World, *, ref: str) -> dict:
    return {"broker_id": world.a_id, "asset_id": world.asset_id, "type": "BUY", "date": DAY.isoformat(), "quantity": "10", "cash": {"code": EUR, "amount": "-100"}, "description": f"{world.marker} buy", "ref": ref}


async def _batch(
    world: World,
    *,
    commit: bool,
    creates: list[dict] | None = None,
    updates: list[dict] | None = None,
    deletes: list[int] | None = None,
    promotes: list[dict] | None = None,
    splits: list[dict] | None = None,
    user_id: int | None = None,
) -> TXBatchResponse:
    """The batch as ``POST /transactions/commit`` (``commit=True``) or ``/validate`` runs it, its transaction included.
    A savepoint stands in for the request's transaction; the session fixture still rolls everything back."""
    savepoint = await world.session.begin_nested()
    response = await TransactionService(world.session).execute_batch(
        creates_raw=creates or [],
        updates_raw=updates or [],
        deletes=deletes or [],
        promotes_raw=promotes or [],
        splits_raw=splits or [],
        user_id=user_id,
        commit=commit,
    )
    if commit and response.committed:
        await savepoint.commit()
    else:
        await savepoint.rollback()
    return response


def _render(issues: list[TXValidationIssue]) -> str:
    return "; ".join(f"{issue.operation}[{issue.index}] ref_id={issue.ref_id} code={issue.code} field={issue.field} params={issue.params} error={issue.error!r}" for issue in issues) or "none"


def _views(issues: list[TXValidationIssue]) -> list[tuple]:
    """What the contract fixes of an issue: where it is, its code and its params — never its text."""
    return [(issue.operation, issue.index, issue.ref_id, issue.code, issue.params) for issue in issues]


def _fields(issues: list[TXValidationIssue]) -> list[str | None]:
    return [issue.field for issue in issues]


async def _rows(world: World) -> dict[int, tuple]:
    """Every row of the test's two brokers, re-read: ``{id: (broker_id, type, parent_transaction_id)}``."""
    statement = select(Transaction).where(Transaction.broker_id.in_([world.a_id, world.b_id])).execution_options(populate_existing=True)
    rows = (await world.session.execute(statement)).scalars().all()
    return {row.id: (row.broker_id, row.type, row.parent_transaction_id) for row in rows}


def _created_ids(response: TXBatchResponse) -> list[int]:
    return [tx_id for result in sorted((r for r in response.results if r.operation == "create"), key=lambda r: r.index) for tx_id in result.ids]


def _mode(commit: bool) -> str:
    return "/commit" if commit else "/validate"


async def _assert_refused(world: World, response: TXBatchResponse, before: dict, commit: bool, expected: list[tuple], fields: list[str | None] | None = None) -> None:
    assert _views(response.issues) == expected, f"{_mode(commit)}: expected exactly {expected}; issues: {_render(response.issues)}"
    if fields is not None:
        assert _fields(response.issues) == fields, f"{_mode(commit)}: expected the fields {fields}; issues: {_render(response.issues)}"
    assert response.committed is False, f"{_mode(commit)}: the refused batch was committed"
    assert await _rows(world) == before, f"{_mode(commit)}: a refused batch wrote rows"


async def _assert_accepted(world: World, response: TXBatchResponse, before: dict, commit: bool) -> dict[int, tuple]:
    """No issue; /validate writes nothing, /commit commits. Returns the rows now."""
    assert response.issues == [], f"{_mode(commit)}: the batch was refused: {_render(response.issues)}"
    rows = await _rows(world)
    if commit:
        assert response.committed is True, "/commit: the accepted batch was not committed"
    else:
        assert rows == before, "/validate wrote rows"
    return rows


# ============================================================================
# R4 — A PARENT IS DELETED
# ============================================================================


class TestAParentIsDeleted:
    """RED until R4 (today /validate answers ok and /commit dies of a foreign-key integrity error), except the guard."""

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_parent_deleted_with_its_charges_left_is_refused(self, world, commit):
        buy_id, fee_id, tax_id = await _family(world)
        before = await _rows(world)

        response = await _batch(world, commit=commit, deletes=[buy_id])

        await _assert_refused(world, response, before, commit, [("delete", 0, buy_id, "chargesDeleteIncomplete", {"id": buy_id, "chargeIds": sorted([fee_id, tax_id])})])

    @pytest.mark.asyncio
    @COMMIT
    @pytest.mark.parametrize("order", ("parent-first", "charges-first", "parent-between"))
    async def test_a_parent_deleted_with_all_its_charges_goes(self, world, commit, order):
        buy_id, fee_id, tax_id = await _family(world)
        before = await _rows(world)
        deletes = {"parent-first": [buy_id, fee_id, tax_id], "charges-first": [fee_id, tax_id, buy_id], "parent-between": [fee_id, buy_id, tax_id]}[order]

        response = await _batch(world, commit=commit, deletes=deletes)

        rows = await _assert_accepted(world, response, before, commit)
        if commit:
            assert not {buy_id, fee_id, tax_id} & set(rows), f"the three rows must be gone: {rows}"

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_parent_deleted_with_its_charges_unlinked_in_the_same_batch(self, world, commit):
        buy_id, fee_id, tax_id = await _family(world)
        before = await _rows(world)
        updates = [{"id": fee_id, "parent_transaction_id": 0}, {"id": tax_id, "parent_transaction_id": 0}]

        response = await _batch(world, commit=commit, deletes=[buy_id], updates=updates)

        rows = await _assert_accepted(world, response, before, commit)
        if commit:
            assert buy_id not in rows, "the parent must be gone"
            assert (rows[fee_id][2], rows[tax_id][2]) == (None, None), f"the charges must stay, with no parent: {rows.get(fee_id)} / {rows.get(tax_id)}"

    @pytest.mark.asyncio
    @COMMIT
    async def test_one_charge_deleted_and_the_other_unlinked(self, world, commit):
        buy_id, fee_id, tax_id = await _family(world)
        before = await _rows(world)

        response = await _batch(world, commit=commit, deletes=[buy_id, fee_id], updates=[{"id": tax_id, "parent_transaction_id": 0}])

        rows = await _assert_accepted(world, response, before, commit)
        if commit:
            assert (buy_id in rows, fee_id in rows) == (False, False), f"the parent and the deleted charge must be gone: {rows}"
            assert rows[tax_id][2] is None, "the unlinked charge must stay, with no parent"

    @pytest.mark.asyncio
    @COMMIT
    async def test_unlinking_only_one_charge_lists_the_other(self, world, commit):
        buy_id, fee_id, tax_id = await _family(world)
        before = await _rows(world)

        response = await _batch(world, commit=commit, deletes=[buy_id], updates=[{"id": fee_id, "parent_transaction_id": 0}])

        await _assert_refused(world, response, before, commit, [("delete", 0, buy_id, "chargesDeleteIncomplete", {"id": buy_id, "chargeIds": [tax_id]})])

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_charge_deleted_alone_keeps_its_parent_and_the_other_charge(self, world, commit):
        """Guard: green before R4 and after it."""
        buy_id, fee_id, tax_id = await _family(world)
        before = await _rows(world)

        response = await _batch(world, commit=commit, deletes=[fee_id])

        rows = await _assert_accepted(world, response, before, commit)
        if commit:
            assert fee_id not in rows, "the deleted charge must be gone"
            assert rows[buy_id][2] is None and rows[tax_id][2] == buy_id, f"the parent stays, the other charge stays linked: {rows.get(buy_id)} / {rows.get(tax_id)}"

    @pytest.mark.asyncio
    async def test_deleting_a_broker_removes_its_linked_rows(self, world):
        """``delete_by_broker`` (what ``BrokerService`` calls with force): the BUY and its charges go together, no integrity error."""
        buy_id, fee_id, tax_id = await _family(world)

        savepoint = await world.session.begin_nested()
        deleted = await TransactionService(world.session).delete_by_broker(world.a_id)
        await world.session.flush()
        await savepoint.commit()

        assert deleted == 3, f"the broker owns exactly the BUY, the FEE and the TAX: delete_by_broker returned {deleted}"
        rows = await _rows(world)
        assert not {buy_id, fee_id, tax_id} & set(rows), f"the broker's rows must be gone: {rows}"


# ============================================================================
# R5 — UPDATES LINK AND UNLINK
# ============================================================================


class TestUpdatesLinkAndUnlink:
    """RED until R5: today ``TXUpdateItem`` forbids ``parent_transaction_id`` and ``parent_ref``."""

    @pytest.mark.asyncio
    @COMMIT
    async def test_two_saved_charges_are_linked_to_one_parent(self, world, commit):
        buy_id = await _save_buy(world)
        fee1, fee2 = await _save_charge(world), await _save_charge(world)
        before = await _rows(world)

        response = await _batch(world, commit=commit, updates=[{"id": fee1, "parent_transaction_id": buy_id}, {"id": fee2, "parent_transaction_id": buy_id}])

        rows = await _assert_accepted(world, response, before, commit)
        if commit:
            assert (rows[fee1][2], rows[fee2][2], rows[buy_id][2]) == (buy_id, buy_id, None), f"both charges must point at the BUY: {rows}"

    @pytest.mark.asyncio
    @COMMIT
    async def test_zero_unlinks_and_keeps_the_row(self, world, commit):
        buy_id, fee_id, tax_id = await _family(world)
        before = await _rows(world)

        response = await _batch(world, commit=commit, updates=[{"id": fee_id, "parent_transaction_id": 0}])

        rows = await _assert_accepted(world, response, before, commit)
        if commit:
            assert rows[fee_id][2] is None, "the unlinked charge must have no parent"
            assert rows[tax_id][2] == buy_id, "the other charge must stay linked"

    @pytest.mark.asyncio
    @COMMIT
    async def test_zero_on_a_row_without_parent_is_a_no_op(self, world, commit):
        fee_id = await _save_charge(world)
        before = await _rows(world)

        response = await _batch(world, commit=commit, updates=[{"id": fee_id, "parent_transaction_id": 0}])

        rows = await _assert_accepted(world, response, before, commit)
        if commit:
            assert rows[fee_id] == before[fee_id], "a no-op must change nothing"

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_linked_charge_is_moved_to_another_parent(self, world, commit):
        buy_a, fee_id, _ = await _family(world)
        buy_b = await _save_buy(world)
        before = await _rows(world)

        response = await _batch(world, commit=commit, updates=[{"id": fee_id, "parent_transaction_id": buy_b}])

        rows = await _assert_accepted(world, response, before, commit)
        if commit:
            assert rows[fee_id][2] == buy_b and buy_a != buy_b, f"the charge must be linked to the second BUY: {rows[fee_id]}"

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_linked_charge_edited_in_amount_and_description_only(self, world, commit):
        """Guard: an update that says nothing of the link leaves it as it was."""
        buy_id, fee_id, _ = await _family(world)
        before = await _rows(world)

        response = await _batch(world, commit=commit, updates=[{"id": fee_id, "description": f"{world.marker} edited", "cash": {"code": EUR, "amount": "-7"}}])

        rows = await _assert_accepted(world, response, before, commit)
        if commit:
            assert rows[fee_id][2] == buy_id, "the link must not change"

    # --- refusals of the rules of R2, on an update -------------------------------------------------------------

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_parent_on_another_broker(self, world, commit):
        buy_id = await _save_buy(world, world.a_id)
        fee_id = await _save_charge(world, broker_id=world.b_id)
        before = await _rows(world)

        response = await _batch(world, commit=commit, updates=[{"id": fee_id, "parent_transaction_id": buy_id}])

        await _assert_refused(world, response, before, commit, [("update", 0, fee_id, "chargeBrokerMismatch", {"brokerId": world.b_id, "parentBrokerId": world.a_id})], ["parent_transaction_id"])

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_parent_of_another_asset(self, world, commit):
        buy_id = await _save_buy(world)
        fee_id = await _save_charge(world, asset_id=world.other_asset_id)
        before = await _rows(world)

        response = await _batch(world, commit=commit, updates=[{"id": fee_id, "parent_transaction_id": buy_id}])

        await _assert_refused(world, response, before, commit, [("update", 0, fee_id, "chargeAssetMismatch", {"assetId": world.other_asset_id, "parentAssetId": world.asset_id})], ["parent_transaction_id"])

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_charge_without_asset_on_a_parent_with_one(self, world, commit):
        buy_id = await _save_buy(world)
        fee_id = await _save_charge(world, asset_id=None)
        before = await _rows(world)

        response = await _batch(world, commit=commit, updates=[{"id": fee_id, "parent_transaction_id": buy_id}])

        await _assert_refused(world, response, before, commit, [("update", 0, fee_id, "chargeAssetMissing", {"parentAssetId": world.asset_id})], ["parent_transaction_id"])

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_parent_on_a_broker_the_user_cannot_see_is_not_found(self, world, commit):
        buy_id = await _save_buy(world, world.b_id)
        fee_id = await _save_charge(world, broker_id=world.a_id)
        user_id = await _user(world, "editor", {world.a_id: UserRole.EDITOR})
        before = await _rows(world)

        response = await _batch(world, commit=commit, updates=[{"id": fee_id, "parent_transaction_id": buy_id}], user_id=user_id)

        assert "accessDenied" not in {issue.code for issue in response.issues}, f"a parent must never add its broker to the access check: {_render(response.issues)}"
        await _assert_refused(world, response, before, commit, [("update", 0, fee_id, "chargeParentNotFound", {"parentId": buy_id})], ["parent_transaction_id"])

    # --- parent_ref ---------------------------------------------------------------------------------------------

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_saved_charge_is_linked_to_a_parent_created_in_the_batch(self, world, commit):
        fee_id = await _save_charge(world)
        before = await _rows(world)

        response = await _batch(world, commit=commit, creates=[_new_buy(world, ref="n1")], updates=[{"id": fee_id, "parent_ref": "n1"}])

        rows = await _assert_accepted(world, response, before, commit)
        if commit:
            (new_buy_id,) = _created_ids(response)
            assert rows[fee_id][2] == new_buy_id, f"the saved FEE must point at the BUY created by the batch: {rows[fee_id]} (new BUY {new_buy_id})"

    @pytest.mark.asyncio
    @COMMIT
    async def test_an_unknown_parent_ref_on_an_update(self, world, commit):
        fee_id = await _save_charge(world)
        before = await _rows(world)

        response = await _batch(world, commit=commit, creates=[_new_buy(world, ref="n1")], updates=[{"id": fee_id, "parent_ref": "nope"}])

        await _assert_refused(world, response, before, commit, [("update", 0, fee_id, "chargeParentRefNotFound", {"parentRef": "nope"})], ["parent_ref"])

    # --- parse level ----------------------------------------------------------------------------------------------

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_negative_parent_transaction_id(self, world, commit):
        fee_id = await _save_charge(world)
        before = await _rows(world)

        response = await _batch(world, commit=commit, updates=[{"id": fee_id, "parent_transaction_id": -3}])

        assert [(i.operation, i.index, i.code) for i in response.issues] == [("update", 0, "chargeParentIdInvalid")], f"expected one chargeParentIdInvalid on update 0; issues: {_render(response.issues)}"
        assert response.issues[0].params == {"parent_transaction_id": -3}, f"params: {response.issues[0].params}"
        assert response.committed is False
        assert await _rows(world) == before, "a refused batch wrote rows"

    @pytest.mark.asyncio
    @COMMIT
    @pytest.mark.parametrize("with_id", ("saved-parent", "zero"))
    async def test_parent_ref_and_parent_transaction_id_together(self, world, commit, with_id):
        buy_id = await _save_buy(world)
        fee_id = await _save_charge(world)
        before = await _rows(world)
        other = buy_id if with_id == "saved-parent" else 0

        response = await _batch(world, commit=commit, creates=[_new_buy(world, ref="n1")], updates=[{"id": fee_id, "parent_ref": "n1", "parent_transaction_id": other}])

        assert [(i.operation, i.index, i.code) for i in response.issues] == [("update", 0, "chargeParentTwice")], f"expected one chargeParentTwice on update 0; issues: {_render(response.issues)}"
        assert response.committed is False
        assert await _rows(world) == before, "a refused batch wrote rows"


# ============================================================================
# RULE 6 ON SAVED ROWS
# ============================================================================


class TestRuleSixOnSavedRows:
    """RED until R5, except the swap guard: a saved parent with charges that the batch turns into a non-parent."""

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_deposit_with_a_charge_cannot_be_promoted_into_a_cash_transfer(self, world, commit):
        deposit_id = await _save(world, T.DEPOSIT, world.a_id, asset_id=None, quantity="0", amount="100")
        withdrawal_id = await _save(world, T.WITHDRAWAL, world.b_id, asset_id=None, quantity="0", amount="-100")
        fee_id = await _save_charge(world, parent_id=deposit_id, asset_id=None)
        before = await _rows(world)

        response = await _batch(world, commit=commit, promotes=[{"id_a": deposit_id, "id_b": withdrawal_id}])

        await _assert_refused(world, response, before, commit, [("promote", 0, deposit_id, "chargesBlockParentType", {"type": "CASH_TRANSFER", "chargeIds": [fee_id]})])

    @pytest.mark.asyncio
    @COMMIT
    async def test_unlinking_the_charge_in_the_same_batch_lets_the_promote_pass(self, world, commit):
        deposit_id = await _save(world, T.DEPOSIT, world.a_id, asset_id=None, quantity="0", amount="100")
        withdrawal_id = await _save(world, T.WITHDRAWAL, world.b_id, asset_id=None, quantity="0", amount="-100")
        fee_id = await _save_charge(world, parent_id=deposit_id, asset_id=None)
        before = await _rows(world)

        response = await _batch(world, commit=commit, promotes=[{"id_a": deposit_id, "id_b": withdrawal_id}], updates=[{"id": fee_id, "parent_transaction_id": 0}])

        rows = await _assert_accepted(world, response, before, commit)
        if commit:
            assert rows[deposit_id][1] == T.CASH_TRANSFER and rows[withdrawal_id][1] == T.CASH_TRANSFER, "both legs must be CASH_TRANSFER now"
            assert rows[fee_id][2] is None, "the unlinked FEE must stay, with no parent"

    @pytest.mark.asyncio
    @COMMIT
    async def test_deleting_the_charge_in_the_same_batch_lets_the_promote_pass(self, world, commit):
        """66 C21 guard (§1.1): a charge «del» does not count as linked — the Bulk offers the merge of its parent, and
        sends the delete of the charge and the promote in one batch. Rule 6 reads the charges after the batch's deletes."""
        deposit_id = await _save(world, T.DEPOSIT, world.a_id, asset_id=None, quantity="0", amount="100")
        withdrawal_id = await _save(world, T.WITHDRAWAL, world.b_id, asset_id=None, quantity="0", amount="-100")
        fee_id = await _save_charge(world, parent_id=deposit_id, asset_id=None)
        before = await _rows(world)
        assert before[fee_id][2] == deposit_id, f"premise: the FEE is saved linked to the DEPOSIT: {before[fee_id]}"

        response = await _batch(world, commit=commit, promotes=[{"id_a": deposit_id, "id_b": withdrawal_id}], deletes=[fee_id])

        rows = await _assert_accepted(world, response, before, commit)
        if commit:
            assert fee_id not in rows, f"the deleted FEE must be gone: {rows.get(fee_id)}"
            assert await _related_and_type(world, deposit_id) == (T.CASH_TRANSFER, withdrawal_id), "the DEPOSIT must be the CASH_TRANSFER leg paired with the WITHDRAWAL"
            assert await _related_and_type(world, withdrawal_id) == (T.CASH_TRANSFER, deposit_id), "the WITHDRAWAL must be the CASH_TRANSFER leg paired with the DEPOSIT"

    @pytest.mark.asyncio
    @COMMIT
    @pytest.mark.parametrize("before_type,after_type", ((T.BUY, "SELL"), (T.DEPOSIT, "WITHDRAWAL")), ids=("buy-sell", "deposit-withdrawal"))
    async def test_a_type_swap_of_a_parent_keeps_its_charges(self, world, commit, before_type, after_type):
        if before_type is T.BUY:
            parent_id, asset_id = await _save_buy(world), world.asset_id
        else:
            parent_id, asset_id = await _save(world, T.DEPOSIT, world.a_id, asset_id=None, amount="100"), None
        fee_id = await _save_charge(world, parent_id=parent_id, asset_id=asset_id)
        before = await _rows(world)

        # A swap flips the signs too: a SELL gives units and takes cash, a WITHDRAWAL takes cash out.
        flipped = {"quantity": "-10", "cash": {"code": "EUR", "amount": "100"}} if before_type is T.BUY else {"cash": {"code": "EUR", "amount": "-100"}}
        response = await _batch(world, commit=commit, updates=[{"id": parent_id, "type": after_type, **flipped}])

        rows = await _assert_accepted(world, response, before, commit)
        if commit:
            assert rows[parent_id][1].value == after_type and rows[fee_id][2] == parent_id, f"the swapped parent must keep its charge: {rows[parent_id]} / {rows[fee_id]}"


# ============================================================================
# RULE 8 ON THE FINAL STATE: SPLIT A PAIR, THEN LINK, IN ONE BATCH
# ============================================================================


async def _save_pair(world: World) -> tuple[int, int]:
    """A saved CASH_TRANSFER pair on two brokers, each leg pointing at the other: ``(sending_id, receiving_id)``, -100 and +100 EUR."""
    sending = await _save(world, T.CASH_TRANSFER, world.a_id, asset_id=None, amount="-100")
    receiving = await _save(world, T.CASH_TRANSFER, world.b_id, asset_id=None, amount="100")
    for row_id, partner_id in ((sending, receiving), (receiving, sending)):
        row = await world.session.get(Transaction, row_id)
        row.related_transaction_id = partner_id
    await world.session.flush()
    return sending, receiving


async def _related_and_type(world: World, row_id: int) -> tuple[T, int | None]:
    """``(type, related_transaction_id)`` of a row, re-read."""
    statement = select(Transaction.type, Transaction.related_transaction_id).where(Transaction.id == row_id).execution_options(populate_existing=True)
    row_type, related = (await world.session.execute(statement)).one()
    return row_type, related


def _new_fee(world: World, *, parent_id: int) -> dict:
    return {"broker_id": world.b_id, "type": "FEE", "date": DAY.isoformat(), "cash": {"code": EUR, "amount": "-5"}, "description": f"{world.marker} fee", "parent_transaction_id": parent_id}


class TestSplitAPairThenLinkInOneBatch:
    """Rule 8 is judged on the final state: splitting a pair and linking a charge to one of its legs in the SAME batch works.
    Guards, green after R3-R5."""

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_created_charge_is_linked_to_a_leg_the_batch_splits(self, world, commit):
        sending, receiving = await _save_pair(world)
        before = await _rows(world)

        response = await _batch(world, commit=commit, splits=[{"id_a": sending, "id_b": receiving}], creates=[_new_fee(world, parent_id=receiving)])

        rows = await _assert_accepted(world, response, before, commit)
        if commit:
            assert await _related_and_type(world, receiving) == (T.DEPOSIT, None), "the receiving leg must be an unpaired DEPOSIT after the split"
            (fee_id,) = _created_ids(response)
            assert rows[fee_id][2] == receiving, f"the new FEE must point at the former leg: {rows[fee_id]}"

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_saved_charge_is_linked_to_a_leg_the_batch_splits(self, world, commit):
        sending, receiving = await _save_pair(world)
        fee_id = await _save_charge(world, broker_id=world.b_id, asset_id=None)
        before = await _rows(world)

        response = await _batch(world, commit=commit, splits=[{"id_a": sending, "id_b": receiving}], updates=[{"id": fee_id, "parent_transaction_id": receiving}])

        rows = await _assert_accepted(world, response, before, commit)
        if commit:
            assert await _related_and_type(world, receiving) == (T.DEPOSIT, None), "the receiving leg must be an unpaired DEPOSIT after the split"
            assert rows[fee_id][2] == receiving, f"the saved FEE must point at the former leg: {rows[fee_id]}"

    @pytest.mark.asyncio
    @COMMIT
    async def test_without_the_split_the_link_to_a_leg_is_refused_by_its_type(self, world, commit):
        """The type check comes before the paired check: the leg is still a CASH_TRANSFER."""
        _, receiving = await _save_pair(world)
        before = await _rows(world)

        response = await _batch(world, commit=commit, creates=[_new_fee(world, parent_id=receiving)])

        await _assert_refused(world, response, before, commit, [("create", 0, None, "chargeParentTypeNotAllowed", {"type": "CASH_TRANSFER"})], ["parent_transaction_id"])


async def _type_amount_related(world: World, row_id: int) -> tuple[T, Decimal, int | None]:
    """``(type, amount, related_transaction_id)`` of a row, re-read."""
    statement = select(Transaction.type, Transaction.amount, Transaction.related_transaction_id).where(Transaction.id == row_id).execution_options(populate_existing=True)
    row_type, amount, related = (await world.session.execute(statement)).one()
    return row_type, amount, related


class TestASplitHalfSwappedAndLinkedInOneBatch:
    """66 C22e: the server side of the Bulk's swapped split half. One batch splits a saved CASH_TRANSFER, turns its
    receiving half (a DEPOSIT once split, saved +100) into a WITHDRAWAL −100 through an update that names the type, and
    links a saved FEE to that half. ``apply_splits`` runs first (the half becomes a DEPOSIT, ``pair_sides`` on the saved
    sign), then the update swaps it (``SWAP_GROUPS``), then ``link_charges`` on the final state: a WITHDRAWAL is a parent.

    The guard is green before the Bulk's fix; the characterization pins what the Bulk sends today (the same batch with
    no ``type``): the update writes −100 on the DEPOSIT the split made, and the batch is refused."""

    @pytest.mark.asyncio
    @COMMIT
    async def test_the_receiving_half_swapped_to_withdrawal_with_a_fee_linked(self, world, commit):
        sending, receiving = await _save_pair(world)
        fee_id = await _save_charge(world, broker_id=world.b_id, asset_id=None)
        before = await _rows(world)

        response = await _batch(
            world,
            commit=commit,
            splits=[{"id_a": sending, "id_b": receiving}],
            updates=[{"id": receiving, "type": "WITHDRAWAL", "cash": {"code": EUR, "amount": "-100"}}, {"id": fee_id, "parent_transaction_id": receiving}],
        )

        rows = await _assert_accepted(world, response, before, commit)
        if commit:
            assert await _type_amount_related(world, receiving) == (T.WITHDRAWAL, Decimal("-100"), None), "the receiving half must be an unpaired WITHDRAWAL of -100"
            assert await _type_amount_related(world, sending) == (T.WITHDRAWAL, Decimal("-100"), None), "the sending half must be the split's unpaired WITHDRAWAL, untouched"
            assert rows[fee_id][2] == receiving, f"the saved FEE must point at the swapped half: {rows[fee_id]}"

    @pytest.mark.asyncio
    @COMMIT
    async def test_the_same_batch_without_the_type_is_refused(self, world, commit):
        """Characterization of today's Bulk payload: the split makes the receiving half a DEPOSIT, and an update that
        writes -100 on it without naming the type breaks the DEPOSIT's cash sign."""
        sending, receiving = await _save_pair(world)
        fee_id = await _save_charge(world, broker_id=world.b_id, asset_id=None)
        before = await _rows(world)

        response = await _batch(
            world,
            commit=commit,
            splits=[{"id_a": sending, "id_b": receiving}],
            updates=[{"id": receiving, "cash": {"code": EUR, "amount": "-100"}}, {"id": fee_id, "parent_transaction_id": receiving}],
        )

        assert response.committed is False, f"{_mode(commit)}: the batch without the type was committed"
        assert any(issue.operation == "update" and issue.ref_id == receiving for issue in response.issues), f"{_mode(commit)}: expected an issue on the update of #{receiving}; issues: {_render(response.issues)}"
        assert await _rows(world) == before, f"{_mode(commit)}: a refused batch wrote rows"


# ============================================================================
# THE MESSAGE
# ============================================================================


class TestTheDeleteMessageExistsInEveryLanguage:
    """RED until R4 (the key is added with ``dev.py i18n add``)."""

    @pytest.mark.parametrize("language", UI_LANGUAGES)
    def test_charges_delete_incomplete_has_its_message(self, language):
        """``transactions.errors.chargesDeleteIncomplete`` is non-empty in ``language``, read without the English fallback."""
        messages = flatten(load_catalog(language, fallback=False))

        message = str(messages.get("transactions.errors.chargesDeleteIncomplete") or "").strip()

        assert message, f"transactions.errors.chargesDeleteIncomplete has no {language} message"
