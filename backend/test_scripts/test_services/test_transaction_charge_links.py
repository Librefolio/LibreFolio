"""
A FEE or TAX create can name its parent in the same batch (lot R3 of project 66, linked charges).

Why. R1 added ``transactions.parent_transaction_id`` and R2 the rules (``charge_link_issue``, ``services/transactions/charges.py``),
but nothing writes the link: a batch cannot say «this FEE belongs to that BUY». The Bulk editor creates both rows in one
batch, so the parent has no id yet; the create carries a NAME instead.

The contract (``TXCreateItem``, ``schemas/transactions/transactions.py``; the stage ``link_charges`` of ``charges.py``, after
``resolve_create_links``, the same on /validate and /commit):

- ``ref`` (any type, max 36 characters): the name of a row inside THIS batch. ``parent_ref``: the ``ref`` of the parent created
  in this batch. ``parent_transaction_id``: the id of a SAVED parent. An empty string is absent. ``ref`` and ``link_uuid``
  are separate name spaces.
- Refused when the create is parsed: ``parent_ref`` and ``parent_transaction_id`` together (``chargeParentTwice``), a
  ``parent_transaction_id`` <= 0 (``chargeParentIdInvalid`` {parent_transaction_id}).
- Refused by the stage, on the charge's create (``operation`` "create", ``ref_id`` None): a ``ref`` used twice
  (``chargeRefDuplicate`` {ref}, on every create after the first, ``field`` "ref"); a ``parent_ref`` that names no row
  created in the batch, or one refused for its own reason (``chargeParentRefNotFound`` {parentRef}, ``field`` "parent_ref");
  a saved parent that does not exist, that the user cannot at least VIEW, or that the same batch deletes
  (``chargeParentNotFound`` {parentId}, ``field`` "parent_transaction_id": the same answer for all three, no broker is
  leaked, and no ``accessDenied`` because of a parent); otherwise the R2 rule on the FINAL state of the batch, its params plus
  ``parentRef`` when the parent was named by ``parent_ref``.
- A create refused for its own reason gets no charge issue on top of it.
- Valid: the charge row's ``parent_transaction_id`` is the parent's id; nothing else changes on either row.
- The four new codes have a message under ``transactions.errors.<code>`` in EN, IT, FR and ES.

Reds — fail before R3 (today the schema forbids the three new fields, so a create that carries one is a parse issue; the
stage and the messages do not exist):

- ``TestAChargeIsLinked``: the link by ``parent_ref`` and by ``parent_transaction_id``, written on /commit, nothing written on
  /validate.
- ``TestTheLinkIsRefused``: every refusal above, on /commit and on /validate, with its exact issue and nothing written.
- ``TestTheParentASavedRowMayBe``: a saved parent the user cannot see answers like a missing one; one they can see but
  that sits on another broker is a broker mismatch.
- ``TestTheRulesOfR2FlowThrough`` and ``TestThePromotedParent``: the R2 rules judge the FINAL state (a promoted DEPOSIT is a
  CASH_TRANSFER; a pair leg is never a parent).
- ``TestARefusedCreateIsNotJudgedTwice``.
- ``TestTheMessagesExistInEveryLanguage``.

Guards — green before R3 and after it:

- ``TestRefAloneChangesNothing``: ``ref`` on rows with no link (any type) is plain; the empty string is absent. (Red today
  where the schema rejects the field: the same assertions hold after R3.)

Its world (own brokers that may go below zero, own assets) follows ``test_linked_cash_pair.py`` and
``test_linked_adjustment_pair.py``; ids are plain ints, because a savepoint that rolls a refused batch back expires every
ORM object.
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
NEW_CODES = ("chargeParentTwice", "chargeParentIdInvalid", "chargeRefDuplicate", "chargeParentRefNotFound")
NO_ASSET = None
OWN_ASSET = ...  # the charge takes the world's first asset
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
    """One test's own data: two assets and two brokers that may go below zero (cash and units are never the subject)."""

    session: AsyncSession
    marker: str
    asset_id: int
    other_asset_id: int
    a_id: int
    b_id: int


@pytest_asyncio.fixture
async def world(session) -> World:
    marker = f"charge-link {uuid.uuid4().hex}"
    now = utcnow()
    assets = [Asset(display_name=f"{marker} asset {n}", asset_type=AssetType.STOCK, currency=EUR, created_at=now, updated_at=now) for n in (1, 2)]
    brokers = [Broker(name=f"{marker} {n}", description="linked charge: a broker of this test", allow_cash_overdraft=True, allow_asset_shorting=False, created_at=now, updated_at=now) for n in ("a", "b")]
    session.add_all([*assets, *brokers])
    await session.flush()
    return World(session=session, marker=marker, asset_id=assets[0].id, other_asset_id=assets[1].id, a_id=brokers[0].id, b_id=brokers[1].id)


# ============================================================================
# HELPERS
# ============================================================================


def _buy(world: World, *, ref: str | None = None, broker_id: int | None = None, asset_id: int | None = None, quantity: str = "10", cash: str = "-100") -> dict:
    item = {"broker_id": broker_id or world.a_id, "asset_id": asset_id or world.asset_id, "type": "BUY", "date": DAY.isoformat(), "quantity": quantity, "cash": {"code": EUR, "amount": cash}, "description": f"{world.marker} buy"}
    if ref is not None:
        item["ref"] = ref
    return item


def _charge(world: World, *, tx_type: str = "FEE", broker_id: int | None = None, asset_id=OWN_ASSET, cash: str = "-5", **link) -> dict:
    """A FEE (or TAX) create; ``link`` is any of ``parent_ref``, ``parent_transaction_id``, ``ref``."""
    item = {"broker_id": broker_id or world.a_id, "type": tx_type, "date": DAY.isoformat(), "quantity": "0", "cash": {"code": EUR, "amount": cash}, "description": f"{world.marker} {tx_type.lower()}"}
    asset = world.asset_id if asset_id is OWN_ASSET else asset_id
    if asset is not None:
        item["asset_id"] = asset
    item.update(link)
    return item


def _cash_leg(world: World, tx_type: str, broker_id: int, amount: str, **extra) -> dict:
    return {"broker_id": broker_id, "type": tx_type, "date": DAY.isoformat(), "quantity": "0", "cash": {"code": EUR, "amount": amount}, "description": f"{world.marker} cash", **extra}


async def _save_buy(world: World, broker_id: int, asset_id: int | None = None) -> int:
    """A BUY written straight into the session: the saved parent of a charge. Returns its id."""
    now = utcnow()
    buy = Transaction(broker_id=broker_id, asset_id=asset_id or world.asset_id, type=TransactionType.BUY, date=DAY, quantity=Decimal("10"), amount=Decimal("-100"), currency=EUR, description=f"{world.marker} saved buy", created_at=now, updated_at=now)
    world.session.add(buy)
    await world.session.flush()
    return buy.id


async def _user(world: World, label: str, grants: dict[int, UserRole]) -> int:
    """A user of this test alone, with one access row per ``{broker_id: role}``."""
    tag = uuid.uuid4().hex[:16]
    user = User(username=f"r3_{label}_{tag}", email=f"r3_{label}_{tag}@example.test", hashed_password="not-a-real-hash", is_active=True)
    world.session.add(user)
    await world.session.flush()
    for broker_id, role in grants.items():
        world.session.add(BrokerUserAccess(broker_id=broker_id, user_id=user.id, role=role, share_percentage=Decimal("0")))
    await world.session.flush()
    return user.id


async def _batch(world: World, *, commit: bool, creates: list[dict], deletes: list[int] | None = None, promotes: list[dict] | None = None, user_id: int | None = None) -> TXBatchResponse:
    """The batch as ``POST /transactions/commit`` (``commit=True``) or ``/validate`` runs it, its transaction included.
    A savepoint stands in for the request's transaction; the session fixture still rolls everything back."""
    savepoint = await world.session.begin_nested()
    response = await TransactionService(world.session).execute_batch(
        creates_raw=creates,
        updates_raw=[],
        deletes=deletes or [],
        promotes_raw=promotes or [],
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
    """The ids the batch's create results name, in index order."""
    return [tx_id for result in sorted((r for r in response.results if r.operation == "create"), key=lambda r: r.index) for tx_id in result.ids]


async def _assert_refused(world: World, response: TXBatchResponse, before: dict, commit: bool, expected: list[tuple], fields: list[str | None]) -> None:
    mode = "/commit" if commit else "/validate"
    assert _views(response.issues) == expected, f"{mode}: expected exactly {expected}; issues: {_render(response.issues)}"
    assert _fields(response.issues) == fields, f"{mode}: expected the fields {fields}; issues: {_render(response.issues)}"
    assert response.committed is False, f"{mode}: the refused batch was committed"
    assert await _rows(world) == before, f"{mode}: a refused batch wrote rows"


# ============================================================================
# A CHARGE IS LINKED
# ============================================================================


class TestAChargeIsLinked:
    """RED until R3: the two ways to name a parent."""

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_fee_and_a_tax_name_their_buy_by_ref(self, world, commit):
        before = await _rows(world)
        creates = [_buy(world, ref="r1"), _charge(world, parent_ref="r1"), _charge(world, tx_type="TAX", parent_ref="r1")]

        response = await _batch(world, commit=commit, creates=creates)

        assert response.issues == [], f"a FEE and a TAX linked to their BUY by parent_ref were refused ({'/commit' if commit else '/validate'}): {_render(response.issues)}"
        rows = await _rows(world)
        if not commit:
            assert rows == before, "/validate wrote rows"
            return
        assert response.committed is True
        buy_id, fee_id, tax_id = _created_ids(response)
        assert (rows[buy_id][2], rows[fee_id][2], rows[tax_id][2]) == (None, buy_id, buy_id), f"parent_transaction_id of BUY, FEE, TAX: {rows[buy_id]} / {rows[fee_id]} / {rows[tax_id]}"

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_fee_names_a_saved_buy_by_id(self, world, commit):
        parent_id = await _save_buy(world, world.a_id)
        before = await _rows(world)

        response = await _batch(world, commit=commit, creates=[_charge(world, parent_transaction_id=parent_id)])

        assert response.issues == [], f"a FEE linked to a saved BUY by parent_transaction_id was refused ({'/commit' if commit else '/validate'}): {_render(response.issues)}"
        rows = await _rows(world)
        if not commit:
            assert rows == before, "/validate wrote rows"
            return
        (fee_id,) = _created_ids(response)
        assert rows[fee_id][2] == parent_id and rows[parent_id][2] is None, f"the FEE must point at the saved BUY, the BUY at none: {rows[fee_id]} / {rows[parent_id]}"


# ============================================================================
# THE LINK IS REFUSED
# ============================================================================


class TestTheLinkIsRefused:
    """RED until R3: the refusals of the stage and of the parse, on /commit and /validate, nothing written."""

    @pytest.mark.asyncio
    @COMMIT
    async def test_an_unknown_parent_ref(self, world, commit):
        before = await _rows(world)

        response = await _batch(world, commit=commit, creates=[_buy(world, ref="r1"), _charge(world, parent_ref="nope")])

        await _assert_refused(world, response, before, commit, [("create", 1, None, "chargeParentRefNotFound", {"parentRef": "nope"})], ["parent_ref"])

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_ref_used_twice_is_refused_on_the_second_only(self, world, commit):
        before = await _rows(world)
        creates = [_buy(world, ref="r1"), _buy(world, ref="r1"), _charge(world, parent_ref="r1")]

        response = await _batch(world, commit=commit, creates=creates)

        await _assert_refused(world, response, before, commit, [("create", 1, None, "chargeRefDuplicate", {"ref": "r1"})], ["ref"])

    @pytest.mark.asyncio
    @COMMIT
    async def test_parent_ref_and_parent_transaction_id_together(self, world, commit):
        parent_id = await _save_buy(world, world.a_id)
        before = await _rows(world)

        response = await _batch(world, commit=commit, creates=[_buy(world, ref="r1"), _charge(world, parent_ref="r1", parent_transaction_id=parent_id)])

        assert [(i.operation, i.index, i.code) for i in response.issues] == [("create", 1, "chargeParentTwice")], f"expected one chargeParentTwice on create 1; issues: {_render(response.issues)}"
        assert response.committed is False
        assert await _rows(world) == before, "a refused batch wrote rows"

    @pytest.mark.asyncio
    @COMMIT
    @pytest.mark.parametrize("bad_id", (0, -3), ids=("zero", "negative"))
    async def test_a_parent_transaction_id_that_is_not_positive(self, world, commit, bad_id):
        before = await _rows(world)

        response = await _batch(world, commit=commit, creates=[_charge(world, parent_transaction_id=bad_id)])

        assert [(i.operation, i.index, i.code) for i in response.issues] == [("create", 0, "chargeParentIdInvalid")], f"expected one chargeParentIdInvalid on create 0; issues: {_render(response.issues)}"
        assert response.issues[0].params == {"parent_transaction_id": bad_id}, f"params: {response.issues[0].params}"
        assert response.committed is False
        assert await _rows(world) == before, "a refused batch wrote rows"

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_missing_saved_parent(self, world, commit):
        parent_id = await _save_buy(world, world.a_id)
        missing = parent_id + 1_000_000_000
        before = await _rows(world)

        response = await _batch(world, commit=commit, creates=[_charge(world, parent_transaction_id=missing)])

        await _assert_refused(world, response, before, commit, [("create", 0, None, "chargeParentNotFound", {"parentId": missing})], ["parent_transaction_id"])

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_saved_parent_the_same_batch_deletes(self, world, commit):
        parent_id = await _save_buy(world, world.a_id)
        before = await _rows(world)

        response = await _batch(world, commit=commit, creates=[_charge(world, parent_transaction_id=parent_id)], deletes=[parent_id])

        await _assert_refused(world, response, before, commit, [("create", 0, None, "chargeParentNotFound", {"parentId": parent_id})], ["parent_transaction_id"])
        assert parent_id in await _rows(world), "the parent the refused batch deletes must still be there"

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_parent_ref_never_matches_a_link_uuid(self, world, commit):
        """``ref`` and ``link_uuid`` are separate name spaces: a DEPOSIT and a WITHDRAWAL promoted into a pair under a
        ``link_uuid`` X are not a parent named X."""
        uuid_a, uuid_b = str(uuid.uuid4()), str(uuid.uuid4())
        creates = [_cash_leg(world, "DEPOSIT", world.a_id, "100", link_uuid=uuid_a), _cash_leg(world, "WITHDRAWAL", world.b_id, "-100", link_uuid=uuid_b), _charge(world, asset_id=NO_ASSET, parent_ref=uuid_a)]
        before = await _rows(world)

        response = await _batch(world, commit=commit, creates=creates, promotes=[{"link_uuid_a": uuid_a, "link_uuid_b": uuid_b}])

        await _assert_refused(world, response, before, commit, [("create", 2, None, "chargeParentRefNotFound", {"parentRef": uuid_a})], ["parent_ref"])


# ============================================================================
# THE SAVED PARENT, SEEN BY A USER
# ============================================================================


class TestTheParentASavedRowMayBe:
    """RED until R3: a saved parent counts only if the user can at least VIEW its broker, and never leaks the broker."""

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_parent_on_a_broker_the_user_cannot_see_is_not_found(self, world, commit):
        parent_id = await _save_buy(world, world.b_id)
        user_id = await _user(world, "editor", {world.a_id: UserRole.EDITOR})
        before = await _rows(world)

        response = await _batch(world, commit=commit, creates=[_charge(world, parent_transaction_id=parent_id)], user_id=user_id)

        assert "accessDenied" not in {issue.code for issue in response.issues}, f"a parent must never add its broker to the access check: {_render(response.issues)}"
        await _assert_refused(world, response, before, commit, [("create", 0, None, "chargeParentNotFound", {"parentId": parent_id})], ["parent_transaction_id"])

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_parent_on_a_broker_the_user_can_only_view_is_a_broker_mismatch(self, world, commit):
        parent_id = await _save_buy(world, world.b_id)
        user_id = await _user(world, "viewer", {world.a_id: UserRole.EDITOR, world.b_id: UserRole.VIEWER})
        before = await _rows(world)

        response = await _batch(world, commit=commit, creates=[_charge(world, parent_transaction_id=parent_id)], user_id=user_id)

        assert "accessDenied" not in {issue.code for issue in response.issues}, f"a VIEWER of the parent's broker must not be denied for it: {_render(response.issues)}"
        await _assert_refused(world, response, before, commit, [("create", 0, None, "chargeBrokerMismatch", {"brokerId": world.a_id, "parentBrokerId": world.b_id})], ["parent_transaction_id"])

    @pytest.mark.asyncio
    async def test_a_parent_on_the_users_own_broker_is_linked(self, world):
        """Guard of the two refusals above: the same user, the parent on the broker they edit."""
        parent_id = await _save_buy(world, world.a_id)
        user_id = await _user(world, "owner", {world.a_id: UserRole.EDITOR})

        response = await _batch(world, commit=True, creates=[_charge(world, parent_transaction_id=parent_id)], user_id=user_id)

        assert response.issues == [] and response.committed is True, f"a visible parent on the charge's broker was refused: {_render(response.issues)}"
        (fee_id,) = _created_ids(response)
        assert (await _rows(world))[fee_id][2] == parent_id


# ============================================================================
# THE RULES OF R2 FLOW THROUGH
# ============================================================================


class TestTheRulesOfR2FlowThrough:
    """RED until R3: ``charge_link_issue`` judges the FINAL state; its params gain ``parentRef`` when the parent was named by one."""

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_fee_with_another_asset_than_its_buy(self, world, commit):
        before = await _rows(world)
        creates = [_buy(world, ref="r1"), _charge(world, asset_id=world.other_asset_id, parent_ref="r1")]

        response = await _batch(world, commit=commit, creates=creates)

        await _assert_refused(world, response, before, commit, [("create", 1, None, "chargeAssetMismatch", {"assetId": world.other_asset_id, "parentAssetId": world.asset_id, "parentRef": "r1"})], ["parent_ref"])

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_saved_parent_carries_no_parent_ref_in_its_params(self, world, commit):
        parent_id = await _save_buy(world, world.a_id)
        before = await _rows(world)

        response = await _batch(world, commit=commit, creates=[_charge(world, asset_id=world.other_asset_id, parent_transaction_id=parent_id)])

        await _assert_refused(world, response, before, commit, [("create", 0, None, "chargeAssetMismatch", {"assetId": world.other_asset_id, "parentAssetId": world.asset_id})], ["parent_transaction_id"])


class TestThePromotedParent:
    """RED until R3: the stage runs AFTER the promotes and the pair links, so it sees a row as it will be saved."""

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_deposit_promoted_into_a_cash_transfer_is_not_a_parent(self, world, commit):
        uuid_a, uuid_b = str(uuid.uuid4()), str(uuid.uuid4())
        creates = [
            _cash_leg(world, "DEPOSIT", world.a_id, "100", ref="d1", link_uuid=uuid_a),
            _cash_leg(world, "WITHDRAWAL", world.b_id, "-100", link_uuid=uuid_b),
            _charge(world, asset_id=NO_ASSET, parent_ref="d1"),
        ]
        before = await _rows(world)

        response = await _batch(world, commit=commit, creates=creates, promotes=[{"link_uuid_a": uuid_a, "link_uuid_b": uuid_b}])

        await _assert_refused(world, response, before, commit, [("create", 2, None, "chargeParentTypeNotAllowed", {"type": "CASH_TRANSFER", "parentRef": "d1"})], ["parent_ref"])

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_leg_of_a_transfer_pair_is_not_a_parent(self, world, commit):
        await _save_buy(world, world.a_id)  # the units the pair moves
        link = str(uuid.uuid4())
        legs = [
            {"broker_id": world.a_id, "asset_id": world.asset_id, "type": "TRANSFER", "date": DAY.isoformat(), "quantity": "-2", "description": f"{world.marker} move", "link_uuid": link, "ref": "t1"},
            {"broker_id": world.b_id, "asset_id": world.asset_id, "type": "TRANSFER", "date": DAY.isoformat(), "quantity": "2", "description": f"{world.marker} move", "link_uuid": link, "cost_basis_override": {"code": EUR, "amount": "100"}},
        ]
        before = await _rows(world)

        response = await _batch(world, commit=commit, creates=[*legs, _charge(world, parent_ref="t1")])

        await _assert_refused(world, response, before, commit, [("create", 2, None, "chargeParentTypeNotAllowed", {"type": "TRANSFER", "parentRef": "t1"})], ["parent_ref"])


# ============================================================================
# A REFUSED CREATE IS NOT JUDGED TWICE
# ============================================================================


class TestARefusedCreateIsNotJudgedTwice:
    """RED until R3 (today the new fields are a parse issue of their own)."""

    @pytest.mark.asyncio
    @COMMIT
    async def test_a_charge_refused_for_its_own_reason_gets_no_charge_issue(self, world, commit):
        """A FEE with a positive cash is refused by its type; it names a valid BUY, which changes nothing."""
        creates = [_buy(world, ref="r1"), _charge(world, cash="5", parent_ref="r1")]

        response = await _batch(world, commit=commit, creates=creates)

        own = [issue for issue in response.issues if issue.index == 1]
        assert own, f"the FEE with a positive cash must be refused for its own reason; issues: {_render(response.issues)}"
        assert not [issue for issue in response.issues if str(issue.code).startswith("charge")], f"a charge issue came on top of the create's own: {_render(response.issues)}"
        assert not [issue for issue in response.issues if issue.index == 0], f"the valid BUY must have no issue: {_render(response.issues)}"
        assert response.committed is False

    @pytest.mark.asyncio
    @COMMIT
    @pytest.mark.parametrize(
        "bad_buy",
        (
            pytest.param({"quantity": "-10"}, id="negative-quantity"),
            # Not an unknown asset id: its INSERT fails on the asset's foreign key at the flush and leaves the session in
            # need of a rollback, so every later create of the batch fails too (today's pipeline, before any charge
            # link): the FEE has no row and the stage has nothing to judge.
        ),
    )
    async def test_a_parent_refused_for_its_own_reason_is_not_found(self, world, commit, bad_buy):
        buy = {**_buy(world, ref="r1"), **bad_buy}
        before = await _rows(world)

        response = await _batch(world, commit=commit, creates=[buy, _charge(world, parent_ref="r1")])

        charge_issues = [(i.operation, i.index, i.ref_id, i.code, i.params, i.field) for i in response.issues if i.index == 1]
        assert charge_issues == [("create", 1, None, "chargeParentRefNotFound", {"parentRef": "r1"}, "parent_ref")], f"the FEE of a refused BUY must answer chargeParentRefNotFound; issues: {_render(response.issues)}"
        assert [issue for issue in response.issues if issue.index == 0], f"the bad BUY must be refused for its own reason; issues: {_render(response.issues)}"
        assert response.committed is False
        assert await _rows(world) == before, "a refused batch wrote rows"


# ============================================================================
# GUARDS — ref ALONE CHANGES NOTHING
# ============================================================================


class TestRefAloneChangesNothing:
    """A ``ref`` on a row with no link is a plain create, whatever its type; the empty string is absent."""

    @pytest.mark.asyncio
    @COMMIT
    async def test_ref_on_rows_nothing_points_at(self, world, commit):
        creates = [
            _buy(world, ref="b1"),
            _charge(world, ref="f1"),
            _cash_leg(world, "DEPOSIT", world.b_id, "50", ref="d1"),
        ]
        before = await _rows(world)

        response = await _batch(world, commit=commit, creates=creates)

        assert response.issues == [], f"ref on unlinked rows was refused ({'/commit' if commit else '/validate'}): {_render(response.issues)}"
        rows = await _rows(world)
        if not commit:
            assert rows == before
            return
        assert all(rows[tx_id][2] is None for tx_id in _created_ids(response)), "a ref alone must link nothing"

    @pytest.mark.asyncio
    @COMMIT
    async def test_an_empty_ref_and_an_empty_parent_ref_are_absent(self, world, commit):
        """Two creates with ``ref: ""`` are not a duplicate; ``parent_ref: ""`` names no parent."""
        creates = [_buy(world, ref=""), _buy(world, ref=""), _charge(world, parent_ref="")]

        response = await _batch(world, commit=commit, creates=creates)

        assert response.issues == [], f"empty strings must be absent ({'/commit' if commit else '/validate'}): {_render(response.issues)}"
        if commit:
            rows = await _rows(world)
            assert all(rows[tx_id][2] is None for tx_id in _created_ids(response)), "an empty parent_ref must link nothing"


# ============================================================================
# THE MESSAGES
# ============================================================================


class TestTheMessagesExistInEveryLanguage:
    """RED until R3 (the keys are added with ``dev.py i18n add``)."""

    @pytest.mark.parametrize("language", UI_LANGUAGES)
    @pytest.mark.parametrize("code", NEW_CODES)
    def test_the_code_has_its_message(self, language, code):
        """``transactions.errors.<code>`` is non-empty in ``language``, read without the English fallback."""
        messages = flatten(load_catalog(language, fallback=False))

        message = str(messages.get(f"transactions.errors.{code}") or "").strip()

        assert message, f"transactions.errors.{code} has no {language} message"
