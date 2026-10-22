"""
Two ADJUSTMENTs cannot be linked: the batch refuses the pair at entry (the developer's decision, 22/10/2026).

Why. Two ADJUSTMENT creates that share a ``link_uuid`` and a description are SAVED LINKED today (``related_transaction_id``
both ways): ``TransactionValidationMixin._validate_linked_pair`` (``validation.py``), the only judge of a ``link_uuid``
group of two creates that no promote consumed (``resolve_create_links``, ``batch_creates.py``), only knows the TRANSFER,
FX_CONVERSION and CASH_TRANSFER rules. Units that move between brokers are an Asset Transfer, not two Adjustments that
claim to be one move: the engines (lots, WAC, the Dashboard) read a linked pair by its type.

The principle: protect the ENTRY of data. No cleanup of what is stored, no migration — a linked ADJUSTMENT pair an old
database holds is left as it is, and a batch that does not create one is not judged by the new rule.

The cure: after the «same type» check, ``_validate_linked_pair`` answers an ADJUSTMENT pair with
``("two Adjustments cannot be linked: use an Asset Transfer to move units between brokers", "pairAdjustmentNotAllowed",
{"type": "ADJUSTMENT"})``: a ``TXValidationIssue`` on the FIRST create of the group (``operation`` "create", ``ref_id``
None), the batch is not committed — on /commit and on /validate —, nothing is written. The UI words it from the code:
``transactions.errors.pairAdjustmentNotAllowed`` in EN, IT, FR and ES (``resolveValidationMessage.ts`` maps a plain code to
``transactions.errors.<code>``, and translates ``params.type`` into the type's name).

Reds — fail before the cure:

- ``TestAPairOfAdjustmentsIsRefused``: a pair of ADJUSTMENT creates (−2 at the source broker, +2 with a cost at the
  destination, one asset, date, description and ``link_uuid``) is refused with one issue on create 0, on /commit and on
  /validate, and nothing is written; the same when both rows are on ONE broker (the type rule comes before any broker
  rule), and when the descriptions differ (before the description rule). Today the pair commits, linked.
- ``TestTheRuleAlone``: ``_validate_linked_pair`` on two ADJUSTMENTs answers the refusal (today ``None``).
- ``TestTheMessageExistsInEveryLanguage``: ``transactions.errors.pairAdjustmentNotAllowed`` is a non-empty message in the
  four languages, read without the English fallback.

Guards — green before the cure, and the cure must keep them green:

- ``TestWhatTheRuleLeavesAlone``: (a) a TRANSFER pair under one ``link_uuid`` still commits, linked; (b) the promote of
  the Bulk — ONE new ADJUSTMENT carrying a ``link_uuid`` and a promote naming a saved ADJUSTMENT — is not refused (the
  promote consumes the ``link_uuid``, so the group is never judged, and the pair becomes a TRANSFER); (c) two UNLINKED
  ADJUSTMENTs still commit.
- ``TestStoredPairsAreNotJudged``: (d) a linked ADJUSTMENT pair a database already holds (written here directly, as an old
  one stores it) is neither refused nor touched by a batch that edits the description of both rows. A batch that edits
  only ONE of them is refused by the older rule of the pair (``pairDescriptionMismatch``, ``validate_updated_pairs``),
  never by this one.

Why a separate file: its world (one asset, two brokers, a BUY that lets ``source`` give units away) is
``test_transaction_cost_basis_rule.py``'s, copied minimal rather than imported, so that file stays the N2/N78 record.
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

from backend.app.db.models import Asset, AssetType, Broker, Transaction, TransactionType
from backend.app.db.session import get_async_engine
from backend.app.schemas.transactions.batch import TXBatchResponse, TXValidationIssue
from backend.app.services.transactions.transaction_service import TransactionService
from backend.app.utils.datetime_utils import utcnow
from scripts.i18n_catalog import flatten, load_catalog

EUR = "EUR"
MOVE_DAY = date(2025, 2, 3)
BUY_DAY = date(2025, 1, 6)
PAIR_CODE = "pairAdjustmentNotAllowed"
PAIR_PARAMS = {"type": "ADJUSTMENT"}
UI_LANGUAGES = ("en", "it", "fr", "es")
UNITS = Decimal("2")
COST = {"code": EUR, "amount": "100"}
STORED_COST = Decimal("42")
STORED_TAGS = "adjustment-pair"


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
    """One test's own data: an asset, the broker that holds it, the broker that could receive it."""

    session: AsyncSession
    marker: str
    asset_id: int
    source_id: int
    dest_id: int
    buy_id: int

    @property
    def description(self) -> str:
        """The one description both rows of a pair carry, as a pair requires."""
        return f"{self.marker} pair"


@pytest_asyncio.fixture
async def world(session) -> World:
    """An asset, two brokers of this test alone, and the BUY that gives ``source`` 10 units: it can give 2 away."""
    marker = f"adj-pair {uuid.uuid4().hex}"
    now = utcnow()
    asset = Asset(display_name=f"{marker} asset", asset_type=AssetType.STOCK, currency=EUR, created_at=now, updated_at=now)
    source = Broker(name=f"{marker} source", description="linked adjustment pair: the broker units leave", allow_cash_overdraft=True, allow_asset_shorting=False, created_at=now, updated_at=now)
    dest = Broker(name=f"{marker} dest", description="linked adjustment pair: the broker units reach", allow_cash_overdraft=True, allow_asset_shorting=False, created_at=now, updated_at=now)
    session.add_all([asset, source, dest])
    await session.flush()
    buy = Transaction(
        broker_id=source.id,
        asset_id=asset.id,
        type=TransactionType.BUY,
        date=BUY_DAY,
        quantity=Decimal("10"),
        amount=Decimal("-1000"),
        currency=EUR,
        description=f"{marker} buy",
        created_at=now,
        updated_at=now,
    )
    session.add(buy)
    await session.flush()
    # Plain ids: a savepoint that rolls a refused batch back expires every ORM object, and the tests read by id afterwards.
    return World(session=session, marker=marker, asset_id=asset.id, source_id=source.id, dest_id=dest.id, buy_id=buy.id)


# ============================================================================
# HELPERS
# ============================================================================


def _create(world: World, tx_type: str, broker_id: int, quantity: Decimal, *, link_uuid: str | None, description: str | None = None, cost: bool = False) -> dict:
    """One create of a pair: the receiving side (quantity > 0) of either type takes ``cost`` (``COST``), the giving side none."""
    item = {
        "broker_id": broker_id,
        "asset_id": world.asset_id,
        "type": tx_type,
        "date": MOVE_DAY.isoformat(),
        "quantity": str(quantity),
        "description": world.description if description is None else description,
    }
    if link_uuid is not None:
        item["link_uuid"] = link_uuid
    if cost:
        item["cost_basis_override"] = COST
    return item


def _pair(world: World, tx_type: str, *, same_broker: bool = False, link: bool = True, receiver_description: str | None = None) -> list[dict]:
    """The two creates of a pair of ``tx_type``: −2 at ``source``, +2 with a cost at ``dest`` (at ``source`` too when
    ``same_broker``), one asset, one date, one description (the receiver's own when ``receiver_description``), and one
    ``link_uuid`` unless ``link`` is False."""
    link_uuid = str(uuid.uuid4()) if link else None
    receiver = world.source_id if same_broker else world.dest_id
    return [
        _create(world, tx_type, world.source_id, -UNITS, link_uuid=link_uuid),
        _create(world, tx_type, receiver, UNITS, link_uuid=link_uuid, description=receiver_description, cost=True),
    ]


async def _batch(world: World, *, commit: bool, creates: list[dict] | None = None, updates: list[dict] | None = None, promotes: list[dict] | None = None) -> TXBatchResponse:
    """The batch as ``POST /transactions/commit`` (``commit=True``) or ``/validate`` runs it, its transaction included:
    /commit keeps what the service answers committed and rolls back the rest, /validate always rolls back
    (``api/v1/transactions.py``). No user, so no access check. A savepoint stands in for the request's transaction; the
    session fixture still rolls everything back. Read the rows back by id afterwards (``_rows``), never through an ORM
    copy the rollback expired."""
    savepoint = await world.session.begin_nested()
    response = await TransactionService(world.session).execute_batch(
        creates_raw=creates or [],
        updates_raw=updates or [],
        deletes=[],
        promotes_raw=promotes or [],
        commit=commit,
    )
    if commit and response.committed:
        await savepoint.commit()
    else:
        await savepoint.rollback()
    return response


def _render(issues: list[TXValidationIssue]) -> str:
    """The issues, for a failure message."""
    return "; ".join(f"{issue.operation}[{issue.index}] ref_id={issue.ref_id} code={issue.code} field={issue.field} params={issue.params} error={issue.error!r}" for issue in issues) or "none"


def _views(issues: list[TXValidationIssue]) -> list[tuple]:
    """What the contract fixes of an issue: where it is, its code and its params — never its text."""
    return [(issue.operation, issue.index, issue.ref_id, issue.code, issue.params) for issue in issues]


async def _rows(world: World) -> dict[int, tuple]:
    """Every row of the test's two brokers, re-read: ``{id: (broker_id, type, quantity, related_transaction_id, description)}``.

    Identified by the test's own brokers, never by position or by a count over the table."""
    statement = select(Transaction).where(Transaction.broker_id.in_([world.source_id, world.dest_id])).execution_options(populate_existing=True)
    rows = (await world.session.execute(statement)).scalars().all()
    return {row.id: (row.broker_id, row.type, row.quantity, row.related_transaction_id, row.description) for row in rows}


def _created_ids(response: TXBatchResponse) -> list[int]:
    """The ids the batch's create results name, in index order."""
    return [tx_id for result in sorted((r for r in response.results if r.operation == "create"), key=lambda r: r.index) for tx_id in result.ids]


async def _store_linked_adjustments(world: World) -> tuple[int, int]:
    """A linked ADJUSTMENT pair (−2 at ``source``, +2 at ``dest`` with a cost) written straight into the session, as an
    old database holds one — no batch, so no rule of the entry judges it. Both legs carry the pair's description and tags.
    Returns the two ids, ``(giving, receiving)``."""
    now = utcnow()
    common = {"asset_id": world.asset_id, "type": TransactionType.ADJUSTMENT, "date": MOVE_DAY, "amount": Decimal("0"), "currency": None, "description": world.description, "tags": STORED_TAGS, "created_at": now, "updated_at": now}
    giving = Transaction(broker_id=world.source_id, quantity=-UNITS, **common)
    receiving = Transaction(broker_id=world.dest_id, quantity=UNITS, cost_basis_override=STORED_COST, cost_basis_currency=EUR, **common)
    world.session.add_all([giving, receiving])
    await world.session.flush()
    # A pair points both ways, and the ids exist only after the first flush.
    giving.related_transaction_id = receiving.id
    receiving.related_transaction_id = giving.id
    await world.session.flush()
    return giving.id, receiving.id


# ============================================================================
# RED — THE PAIR OF ADJUSTMENTS IS REFUSED AT ENTRY
# ============================================================================

REFUSED_SHAPES = (
    pytest.param({"same_broker": False}, id="two-brokers"),
    pytest.param({"same_broker": True}, id="one-broker-the-type-rule-comes-before-any-broker-rule"),
    pytest.param({"same_broker": False, "receiver_description": "another description"}, id="descriptions-differ-the-type-rule-comes-before-the-description-rule"),
)


class TestAPairOfAdjustmentsIsRefused:
    """RED until the cure: today every one of these pairs is saved, linked both ways."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", REFUSED_SHAPES)
    @pytest.mark.parametrize("commit", (True, False), ids=("commit", "validate"))
    async def test_the_pair_is_refused_on_its_first_create(self, world, commit, shape):
        """One issue, ``pairAdjustmentNotAllowed`` on create 0 (``ref_id`` None, ``params`` ``{"type": "ADJUSTMENT"}``), none
        on the group's other create, the batch not committed, nothing written."""
        before = await _rows(world)

        response = await _batch(world, commit=commit, creates=_pair(world, "ADJUSTMENT", **shape))

        assert _views(response.issues) == [
            ("create", 0, None, PAIR_CODE, PAIR_PARAMS)
        ], f"a pair of ADJUSTMENTs under one link_uuid ({'/commit' if commit else '/validate'}, {shape}) must be refused with exactly one {PAIR_CODE} on create 0, and no issue on create 1; issues: {_render(response.issues)}"
        assert response.committed is False, f"the refused pair was committed ({'/commit' if commit else '/validate'}); issues: {_render(response.issues)}"
        after = await _rows(world)
        assert after == before, f"a refused batch wrote rows: new ids {sorted(set(after) - set(before))}, {_created_ids(response)} named by its results"

    @pytest.mark.asyncio
    async def test_the_refusal_names_the_unit_move_in_english(self, world):
        """The issue's own text is English and points at the right tool; the UI never shows it (it words the code)."""
        response = await _batch(world, commit=True, creates=_pair(world, "ADJUSTMENT"))

        refused = [issue for issue in response.issues if issue.code == PAIR_CODE]

        assert len(refused) == 1, f"expected one {PAIR_CODE} issue, got: {_render(response.issues)}"
        assert "Asset Transfer" in refused[0].error, f"the refusal text must point to the Asset Transfer: {refused[0].error!r}"


class TestTheRuleAlone:
    """RED until the cure: the function that judges a linked pair, on two rows in memory (no session, no database)."""

    @staticmethod
    def _leg(tx_type: TransactionType, broker_id: int, quantity: Decimal) -> Transaction:
        return Transaction(broker_id=broker_id, asset_id=1, type=tx_type, date=MOVE_DAY, quantity=quantity, amount=Decimal("0"))

    @pytest.mark.parametrize("brokers", ((1, 2), (1, 1)), ids=("two-brokers", "one-broker"))
    def test_two_adjustments_are_refused(self, brokers):
        a = self._leg(TransactionType.ADJUSTMENT, brokers[0], -UNITS)
        b = self._leg(TransactionType.ADJUSTMENT, brokers[1], UNITS)

        answer = TransactionService._validate_linked_pair(a, b)

        assert answer is not None, "_validate_linked_pair accepted two ADJUSTMENTs as a linked pair: it answered None"
        message, code, params = answer
        assert (code, params) == (PAIR_CODE, PAIR_PARAMS), f"expected the code {PAIR_CODE} with {PAIR_PARAMS}, got {code} with {params}: {message!r}"

    def test_a_transfer_pair_is_still_accepted(self):
        """Guard, green before and after: two TRANSFERs on two brokers, one asset, opposite quantities."""
        a = self._leg(TransactionType.TRANSFER, 1, -UNITS)
        b = self._leg(TransactionType.TRANSFER, 2, UNITS)

        assert TransactionService._validate_linked_pair(a, b) is None


class TestTheMessageExistsInEveryLanguage:
    """RED until the cure (the key is added with ``dev.py i18n add``)."""

    @pytest.mark.parametrize("language", UI_LANGUAGES)
    def test_the_code_has_its_message(self, language):
        """``transactions.errors.pairAdjustmentNotAllowed`` is non-empty in ``language``, read without the English fallback:
        without it the Bulk editor shows the raw English text of the issue."""
        messages = flatten(load_catalog(language, fallback=False))

        message = str(messages.get(f"transactions.errors.{PAIR_CODE}") or "").strip()

        assert message, f"transactions.errors.{PAIR_CODE} has no {language} message"


# ============================================================================
# GUARDS — WHAT THE RULE MUST LEAVE ALONE
# ============================================================================


class TestWhatTheRuleLeavesAlone:
    """Green before the cure and after it."""

    @pytest.mark.asyncio
    async def test_a_transfer_pair_still_commits_linked(self, world):
        """(a) −2 / +2 with the receiver's cost under one ``link_uuid``: committed, both rows TRANSFER, linked both ways."""
        response = await _batch(world, commit=True, creates=_pair(world, "TRANSFER"))

        assert response.committed is True and response.issues == [], f"the TRANSFER pair was refused: {_render(response.issues)}"
        giving_id, receiving_id = _created_ids(response)
        rows = await _rows(world)
        assert rows[giving_id][1] == TransactionType.TRANSFER and rows[receiving_id][1] == TransactionType.TRANSFER, f"both legs must be TRANSFER: {rows[giving_id]} / {rows[receiving_id]}"
        assert (rows[giving_id][3], rows[receiving_id][3]) == (receiving_id, giving_id), f"the legs must point at each other: {rows[giving_id]} / {rows[receiving_id]}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", (True, False), ids=("commit", "validate"))
    async def test_the_promote_of_the_bulk_is_not_refused(self, world, commit):
        """(b) What the Bulk editor sends for a saved ADJUSTMENT promoted with a NEW one: the new row carries a ``link_uuid``,
        the promote names it (``link_uuid_b``) and the saved row (``id_a``). The promote consumes the ``link_uuid``, so the
        group is never judged by the pair rule; the two rows become a linked TRANSFER pair."""
        now = utcnow()
        saved = Transaction(
            broker_id=world.source_id,
            asset_id=world.asset_id,
            type=TransactionType.ADJUSTMENT,
            date=MOVE_DAY,
            quantity=-UNITS,
            amount=Decimal("0"),
            description=world.description,
            created_at=now,
            updated_at=now,
        )
        world.session.add(saved)
        await world.session.flush()
        saved_id = saved.id
        link_uuid = str(uuid.uuid4())
        created = _create(world, "ADJUSTMENT", world.dest_id, UNITS, link_uuid=link_uuid, cost=True)

        response = await _batch(world, commit=commit, creates=[created], promotes=[{"id_a": saved_id, "link_uuid_b": link_uuid}])

        assert response.issues == [], f"the promote of a saved ADJUSTMENT with a new one was refused ({'/commit' if commit else '/validate'}): {_render(response.issues)}"
        assert PAIR_CODE not in {issue.code for issue in response.issues}
        if commit:
            assert response.committed is True, "the promote was not committed"
            (new_id,) = _created_ids(response)
            rows = await _rows(world)
            assert rows[new_id][1] == TransactionType.TRANSFER and rows[saved_id][1] == TransactionType.TRANSFER, f"the promote makes both rows TRANSFER: {rows[new_id]} / {rows[saved_id]}"
            assert (rows[saved_id][3], rows[new_id][3]) == (new_id, saved_id), f"the promoted rows must point at each other: {rows[saved_id]} / {rows[new_id]}"

    @pytest.mark.asyncio
    async def test_two_unlinked_adjustments_still_commit(self, world):
        """(c) The same −2 / +2 without a ``link_uuid``: two plain ADJUSTMENTs, committed, linked to nothing."""
        response = await _batch(world, commit=True, creates=_pair(world, "ADJUSTMENT", link=False))

        assert response.committed is True and response.issues == [], f"two unlinked ADJUSTMENTs were refused: {_render(response.issues)}"
        giving_id, receiving_id = _created_ids(response)
        rows = await _rows(world)
        assert (rows[giving_id][1], rows[receiving_id][1]) == (TransactionType.ADJUSTMENT, TransactionType.ADJUSTMENT)
        assert (rows[giving_id][3], rows[receiving_id][3]) == (None, None), f"unlinked ADJUSTMENTs must stay unlinked: {rows[giving_id]} / {rows[receiving_id]}"


class TestStoredPairsAreNotJudged:
    """Green before the cure and after it: the rule refuses at entry only, it never reads what a database already holds."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", (True, False), ids=("commit", "validate"))
    async def test_editing_both_descriptions_of_a_stored_pair_commits_and_keeps_the_link(self, world, commit):
        """(d) A stored linked ADJUSTMENT pair, both descriptions edited together (as the app edits a pair): no refusal,
        and after the commit both rows are still ADJUSTMENT, still linked, with the new description."""
        giving_id, receiving_id = await _store_linked_adjustments(world)
        new_description = f"{world.marker} edited"

        response = await _batch(world, commit=commit, updates=[{"id": giving_id, "description": new_description}, {"id": receiving_id, "description": new_description}])

        assert response.issues == [], f"editing the description of both rows of a stored ADJUSTMENT pair was refused ({'/commit' if commit else '/validate'}): {_render(response.issues)}"
        if commit:
            assert response.committed is True
            rows = await _rows(world)
            assert rows[giving_id] == (world.source_id, TransactionType.ADJUSTMENT, -UNITS, receiving_id, new_description), f"giving leg after the edit: {rows[giving_id]}"
            assert rows[receiving_id] == (world.dest_id, TransactionType.ADJUSTMENT, UNITS, giving_id, new_description), f"receiving leg after the edit: {rows[receiving_id]}"

    @pytest.mark.asyncio
    async def test_editing_one_description_is_never_judged_by_the_new_rule(self, world):
        """(d) Only ONE description edited: the older pair rule speaks (``pairDescriptionMismatch``), never
        ``pairAdjustmentNotAllowed``; the stored pair is left exactly as it was."""
        giving_id, receiving_id = await _store_linked_adjustments(world)
        before = await _rows(world)

        response = await _batch(world, commit=True, updates=[{"id": receiving_id, "description": f"{world.marker} edited alone"}])

        assert PAIR_CODE not in {issue.code for issue in response.issues}, f"a stored ADJUSTMENT pair was judged by the entry rule on an update: {_render(response.issues)}"
        if response.committed is not True:
            assert await _rows(world) == before, "a refused batch changed the stored pair"
        assert before[giving_id][3] == receiving_id and before[receiving_id][3] == giving_id, "scaffold: the stored pair must be linked both ways"
