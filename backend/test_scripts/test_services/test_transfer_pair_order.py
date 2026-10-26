"""
A linked TRANSFER or CASH_TRANSFER whose ARRIVAL is dated before its DEPARTURE is saved as sent, and the batch warns
(lot W5-3 / backlog B2, the developer's decision of 23/10/2026).

The example the developer gave: a transfer Directa -> Fineco, departing on the 5th and arriving on the 3rd. The units
(or the cash) would be at Fineco two days before they left Directa. That is almost surely a typo in a date, but the user
may know better (a stale statement, two time zones): so the batch NEVER blocks it and NEVER corrects a date. It saves the
rows exactly as sent and carries a NON-BLOCKING warning next to the blocking ``issues``.

The contract the cure implements (``TXBatchResponse``, ``batch.py``):

- a new field ``warnings: list[TXValidationIssue]`` (default ``[]``), present in EVERY response: committed, refused and
  validate-only. ``issues`` stays the blocking list.
- a warning is operation ``"create"`` or ``"update"``, ``code="pairArrivalBeforeDeparture"`` (new
  ``TXValidationCode.PAIR_ARRIVAL_BEFORE_DEPARTURE``), ``params`` with at least ``departureDate`` and ``arrivalDate`` (ISO
  strings), ``ref_id`` None for a create and the updated transaction's id for an update.
- departure = the leg with a negative quantity (TRANSFER) or a negative amount (CASH_TRANSFER); arrival = the positive one.
  Warning only when arrival date < departure date: equal dates and a normal order give none.
- FX_CONVERSION and ADJUSTMENT never warn; a plain unlinked row never warns.
- two places judge a pair: (1) creation, two creates under one ``link_uuid`` (``resolve_create_links``); (2) modification,
  an update that CHANGES the ``date`` of a leg of a stored linked pair (``validate_updated_pairs`` stage). An update that
  moves BOTH legs is judged on the final dates of both. An update that does not change a date (a description edit, or a date
  equal to the stored one) gives none even when the stored pair is already inverted: stored data is never judged.

Choices this module pins where the specification left room (change them with the cure if the developer decides otherwise):

- a create-time warning sits on the FIRST create of the link_uuid group (as every other pair issue does,
  ``resolve_create_links``), whatever the order the two legs were sent in; ``ref_id`` None.
- an update that moves both legs gives ONE warning for the pair, on one of the two updates (``ref_id`` is that update's id,
  ``index`` that update's index), not two.

Reds (fail before the cure, for the right reason — the response has no ``warnings`` field / the code does not exist):
every test that expects a warning, plus the field and the code themselves, plus the message in the four languages.
Guards (no warning expected): they assert first what is true today (committed, rows exactly as sent) and then read
``warnings``, so before the cure they fail on the missing field only; after it they must stay green. The ones that need
only the data (``TestTheDataIsExactlyWhatWasSent``) are green before the cure.

Why a separate file: its world (one asset, two brokers, a BUY that lets ``source`` give units away) is the one of
``test_linked_adjustment_pair.py``, copied minimal rather than imported.
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
from backend.app.schemas.transactions.batch import TXBatchResponse, TXValidationCode, TXValidationIssue
from backend.app.services.transactions.transaction_service import TransactionService
from backend.app.utils.datetime_utils import utcnow
from scripts.i18n_catalog import flatten, load_catalog

EUR = "EUR"
USD = "USD"
BUY_DAY = date(2025, 1, 6)
# The developer's example: Directa -> Fineco, departing on the 5th, arriving on the 3rd.
EARLY = date(2025, 2, 3)
LATE = date(2025, 2, 5)
LATER = date(2025, 2, 8)
LATEST = date(2025, 2, 10)
WARNING_CODE = "pairArrivalBeforeDeparture"
UI_LANGUAGES = ("en", "it", "fr", "es")
UNITS = Decimal("2")
CASH = Decimal("100")
COST = {"code": EUR, "amount": "100"}
STORED_COST = Decimal("42")
STORED_TAGS = "pair-order"


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
    """One test's own data: an asset, the broker it leaves (the departure), the broker it reaches (the arrival)."""

    session: AsyncSession
    marker: str
    asset_id: int
    source_id: int
    dest_id: int

    @property
    def description(self) -> str:
        """The one description both rows of a pair carry, as a pair requires."""
        return f"{self.marker} pair"


@pytest_asyncio.fixture
async def world(session) -> World:
    """An asset, two brokers of this test alone, and the BUY that gives ``source`` 10 units: it can give 2 away."""
    marker = f"pair-order {uuid.uuid4().hex}"
    now = utcnow()
    asset = Asset(display_name=f"{marker} asset", asset_type=AssetType.STOCK, currency=EUR, created_at=now, updated_at=now)
    source = Broker(name=f"{marker} source", description="transfer pair order: the broker the transfer leaves", allow_cash_overdraft=True, allow_asset_shorting=False, created_at=now, updated_at=now)
    dest = Broker(name=f"{marker} dest", description="transfer pair order: the broker the transfer reaches", allow_cash_overdraft=True, allow_asset_shorting=False, created_at=now, updated_at=now)
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
    return World(session=session, marker=marker, asset_id=asset.id, source_id=source.id, dest_id=dest.id)


# ============================================================================
# HELPERS
# ============================================================================


def _transfer_creates(world: World, dep: date, arr: date, *, arrival_first: bool = False) -> list[dict]:
    """A TRANSFER pair: −2 at ``source`` on ``dep`` (the departure), +2 with a cost at ``dest`` on ``arr`` (the arrival),
    one asset, one description, one ``link_uuid``. ``arrival_first`` sends the arrival as create 0."""
    link_uuid = str(uuid.uuid4())
    departure = {"broker_id": world.source_id, "asset_id": world.asset_id, "type": "TRANSFER", "date": dep.isoformat(), "quantity": str(-UNITS), "description": world.description, "link_uuid": link_uuid}
    arrival = {"broker_id": world.dest_id, "asset_id": world.asset_id, "type": "TRANSFER", "date": arr.isoformat(), "quantity": str(UNITS), "description": world.description, "link_uuid": link_uuid, "cost_basis_override": COST}
    return [arrival, departure] if arrival_first else [departure, arrival]


def _cash_creates(world: World, dep: date, arr: date, *, arrival_first: bool = False) -> list[dict]:
    """A CASH_TRANSFER pair: −100 EUR at ``source`` on ``dep``, +100 EUR at ``dest`` on ``arr``, one description, one ``link_uuid``."""
    link_uuid = str(uuid.uuid4())
    departure = {"broker_id": world.source_id, "type": "CASH_TRANSFER", "date": dep.isoformat(), "quantity": "0", "cash": {"code": EUR, "amount": str(-CASH)}, "description": world.description, "link_uuid": link_uuid}
    arrival = {"broker_id": world.dest_id, "type": "CASH_TRANSFER", "date": arr.isoformat(), "quantity": "0", "cash": {"code": EUR, "amount": str(CASH)}, "description": world.description, "link_uuid": link_uuid}
    return [arrival, departure] if arrival_first else [departure, arrival]


def _fx_creates(world: World, negative_day: date, positive_day: date) -> list[dict]:
    """An FX_CONVERSION pair on ONE broker: −100 EUR on ``negative_day``, +110 USD on ``positive_day``."""
    link_uuid = str(uuid.uuid4())
    out = {"broker_id": world.source_id, "type": "FX_CONVERSION", "date": negative_day.isoformat(), "quantity": "0", "cash": {"code": EUR, "amount": str(-CASH)}, "description": world.description, "link_uuid": link_uuid}
    into = {"broker_id": world.source_id, "type": "FX_CONVERSION", "date": positive_day.isoformat(), "quantity": "0", "cash": {"code": USD, "amount": "110"}, "description": world.description, "link_uuid": link_uuid}
    return [out, into]


async def _batch(world: World, *, commit: bool, creates: list[dict] | None = None, updates: list[dict] | None = None) -> TXBatchResponse:
    """The batch as ``POST /transactions/commit`` (``commit=True``) or ``/validate`` runs it, its transaction included:
    /commit keeps what the service answers committed and rolls back the rest, /validate always rolls back. A savepoint
    stands in for the request's transaction; the session fixture still rolls everything back. Read the rows back by id
    afterwards (``_rows``), never through an ORM copy the rollback expired."""
    savepoint = await world.session.begin_nested()
    response = await TransactionService(world.session).execute_batch(
        creates_raw=creates or [],
        updates_raw=updates or [],
        deletes=[],
        promotes_raw=[],
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


def _warnings(response: TXBatchResponse) -> list[TXValidationIssue]:
    """The response's ``warnings``; a clear failure, not an ``AttributeError``, while the field does not exist."""
    assert "warnings" in TXBatchResponse.model_fields and hasattr(response, "warnings"), "TXBatchResponse has no `warnings` field: the batch has nowhere to carry a non-blocking warning"
    return list(response.warnings)


def _pair_warnings(response: TXBatchResponse) -> list[TXValidationIssue]:
    """The warnings of THIS rule only."""
    return [warning for warning in _warnings(response) if warning.code == WARNING_CODE]


def _assert_no_pair_warning(response: TXBatchResponse, what: str) -> None:
    found = _pair_warnings(response)
    assert found == [], f"{what}: expected no {WARNING_CODE} warning, got: {_render(found)}"
    assert WARNING_CODE not in {issue.code for issue in response.issues}, f"{what}: {WARNING_CODE} must never be a blocking issue: {_render(response.issues)}"


def _assert_one_pair_warning(response: TXBatchResponse, what: str, *, operation: str, departure: date, arrival: date, index: int | None = None, ref_id: int | None = None, ref_ids: set[int] | None = None) -> TXValidationIssue:
    """Exactly one ``pairArrivalBeforeDeparture`` warning, not among ``issues``, whose params carry both ISO dates.
    ``index`` / ``ref_id`` pin where it sits; ``ref_ids`` instead lets the warning sit on any one of the given ids."""
    found = _pair_warnings(response)
    assert len(found) == 1, f"{what}: expected exactly one {WARNING_CODE} warning, got {len(found)}: {_render(found)} (issues: {_render(response.issues)})"
    warning = found[0]
    assert warning.operation == operation, f"{what}: the warning's operation must be {operation!r}: {_render(found)}"
    if index is not None:
        assert warning.index == index, f"{what}: the warning must sit on {operation} index {index}: {_render(found)}"
    if ref_ids is not None:
        assert warning.ref_id in ref_ids, f"{what}: the warning's ref_id must be one of {sorted(ref_ids)}: {_render(found)}"
    else:
        assert warning.ref_id == ref_id, f"{what}: the warning's ref_id must be {ref_id}: {_render(found)}"
    params = warning.params or {}
    assert params.get("departureDate") == departure.isoformat(), f"{what}: params.departureDate must be {departure.isoformat()!r}: {params}"
    assert params.get("arrivalDate") == arrival.isoformat(), f"{what}: params.arrivalDate must be {arrival.isoformat()!r}: {params}"
    assert WARNING_CODE not in {issue.code for issue in response.issues}, f"{what}: the warning must not be a blocking issue: {_render(response.issues)}"
    return warning


async def _rows(world: World) -> dict[int, tuple]:
    """Every row of the test's two brokers, re-read: ``{id: (broker_id, type, quantity, amount, date, related_transaction_id, description)}``.

    Identified by the test's own brokers, never by position or by a count over the table."""
    statement = select(Transaction).where(Transaction.broker_id.in_([world.source_id, world.dest_id])).execution_options(populate_existing=True)
    rows = (await world.session.execute(statement)).scalars().all()
    return {row.id: (row.broker_id, row.type, row.quantity, row.amount, row.date, row.related_transaction_id, row.description) for row in rows}


def _created_ids(response: TXBatchResponse) -> list[int]:
    """The ids the batch's create results name, in create-index order."""
    return [tx_id for result in sorted((r for r in response.results if r.operation == "create"), key=lambda r: r.index) for tx_id in result.ids]


@dataclass
class Stored:
    """A linked pair a database already holds: the id of the departure (``dep``, the negative leg) and of the arrival."""

    dep: int
    arr: int


async def _store_pair(world: World, kind: str, dep_day: date, arr_day: date) -> Stored:
    """A linked pair of ``kind`` written straight into the session, as a database holds one: no batch judges it. ``dep``
    is the negative leg (quantity for TRANSFER and ADJUSTMENT, amount for CASH_TRANSFER, the EUR leg of an FX_CONVERSION), ``arr`` the
    positive one. Both carry the pair's description and tags. TRANSFER and ADJUSTMENT: −2 / +2 of the asset, the arrival
    with a cost; CASH_TRANSFER: −100 / +100 EUR across the two brokers; FX_CONVERSION: −100 EUR / +110 USD, both on ``source``."""
    now = utcnow()
    common = {"description": world.description, "tags": STORED_TAGS, "created_at": now, "updated_at": now}
    if kind in ("TRANSFER", "ADJUSTMENT"):
        tx_type = TransactionType(kind)
        giving = Transaction(broker_id=world.source_id, asset_id=world.asset_id, type=tx_type, date=dep_day, quantity=-UNITS, amount=Decimal("0"), currency=None, **common)
        receiving = Transaction(broker_id=world.dest_id, asset_id=world.asset_id, type=tx_type, date=arr_day, quantity=UNITS, amount=Decimal("0"), currency=None, cost_basis_override=STORED_COST, cost_basis_currency=EUR, **common)
    elif kind == "CASH_TRANSFER":
        giving = Transaction(broker_id=world.source_id, type=TransactionType.CASH_TRANSFER, date=dep_day, quantity=Decimal("0"), amount=-CASH, currency=EUR, **common)
        receiving = Transaction(broker_id=world.dest_id, type=TransactionType.CASH_TRANSFER, date=arr_day, quantity=Decimal("0"), amount=CASH, currency=EUR, **common)
    elif kind == "FX_CONVERSION":
        giving = Transaction(broker_id=world.source_id, type=TransactionType.FX_CONVERSION, date=dep_day, quantity=Decimal("0"), amount=-CASH, currency=EUR, **common)
        receiving = Transaction(broker_id=world.source_id, type=TransactionType.FX_CONVERSION, date=arr_day, quantity=Decimal("0"), amount=Decimal("110"), currency=USD, **common)
    else:  # pragma: no cover — a typo in a test
        raise AssertionError(f"unknown pair kind {kind}")
    world.session.add_all([giving, receiving])
    await world.session.flush()
    # A pair points both ways, and the ids exist only after the first flush.
    giving.related_transaction_id = receiving.id
    receiving.related_transaction_id = giving.id
    await world.session.flush()
    return Stored(dep=giving.id, arr=receiving.id)


CREATE_KINDS = (
    pytest.param(_transfer_creates, TransactionType.TRANSFER, id="TRANSFER"),
    pytest.param(_cash_creates, TransactionType.CASH_TRANSFER, id="CASH_TRANSFER"),
)
COMMIT_MODES = pytest.mark.parametrize("commit", (True, False), ids=("commit", "validate"))
ORDERS = pytest.mark.parametrize("arrival_first", (False, True), ids=("departure-sent-first", "arrival-sent-first"))


# ============================================================================
# RED — THE CONTRACT ITSELF: THE FIELD AND THE CODE
# ============================================================================


class TestTheContractExists:
    """RED until the cure: the field and the code do not exist."""

    def test_the_response_declares_warnings_defaulting_to_empty(self):
        """``TXBatchResponse.warnings``: a list of ``TXValidationIssue``, ``[]`` when nothing warns."""
        assert "warnings" in TXBatchResponse.model_fields, "TXBatchResponse has no `warnings` field"
        empty = TXBatchResponse(committed=False, results=[], success_count=0)
        assert empty.warnings == [], f"`warnings` must default to []: {empty.warnings!r}"

    def test_the_code_is_in_the_enum(self):
        """``TXValidationCode.PAIR_ARRIVAL_BEFORE_DEPARTURE == "pairArrivalBeforeDeparture"``, a plain string like every code."""
        member = getattr(TXValidationCode, "PAIR_ARRIVAL_BEFORE_DEPARTURE", None)
        assert member is not None, "TXValidationCode has no PAIR_ARRIVAL_BEFORE_DEPARTURE member"
        assert member.value == WARNING_CODE, f"the code must be {WARNING_CODE!r}: {member.value!r}"

    @pytest.mark.parametrize("language", UI_LANGUAGES)
    def test_every_code_has_its_message(self, language):
        """Every ``TXValidationCode`` (and the new code, even before the enum has it) has a non-empty message in ``language``,
        read without the English fallback, under ``transactions.errors.<code>``. Without it the Bulk editor shows the raw English text of the issue."""
        messages = flatten(load_catalog(language, fallback=False))
        codes = {code.value for code in TXValidationCode} | {WARNING_CODE}

        missing = sorted(code for code in codes if not str(messages.get(f"transactions.errors.{code}") or "").strip())

        assert missing == [], f"codes without a {language} message (transactions.errors.<code>): {missing}"

    @pytest.mark.parametrize("language", UI_LANGUAGES)
    def test_the_warning_is_worded_under_errors_with_its_two_dates(self, language):
        """The frontend maps a code to ``transactions.errors.<code>`` for issues and warnings alike (the W-B69 gate reads the same
        key): the message names both dates, the params ``departureDate`` and ``arrivalDate``."""
        messages = flatten(load_catalog(language, fallback=False))

        message = str(messages.get(f"transactions.errors.{WARNING_CODE}") or "").strip()

        assert message, f"transactions.errors.{WARNING_CODE} has no {language} message"
        assert "{departureDate}" in message and "{arrivalDate}" in message, f"the {language} message must carry both dates: {message!r}"


# ============================================================================
# RED — CREATION: TWO CREATES UNDER ONE link_uuid
# ============================================================================


class TestAnInvertedPairIsWarnedOnCreate:
    """RED until the cure: today the pair is saved and the response says nothing."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("make,tx_type", CREATE_KINDS)
    @ORDERS
    async def test_the_pair_is_saved_linked_and_the_batch_warns(self, world, make, tx_type, arrival_first):
        """Departure on the 5th, arrival on the 3rd (the developer's example): committed, no blocking issue, both rows saved
        linked and dated as sent, and ONE warning on the first create of the group, ``ref_id`` None, whatever order the legs
        were sent in."""
        response = await _batch(world, commit=True, creates=make(world, LATE, EARLY, arrival_first=arrival_first))

        assert response.committed is True and response.issues == [], f"an inverted {tx_type.value} pair must be saved, never blocked: committed={response.committed}, issues: {_render(response.issues)}"
        first_id, second_id = _created_ids(response)
        rows = await _rows(world)
        assert (rows[first_id][5], rows[second_id][5]) == (second_id, first_id), f"the legs must point at each other: {rows[first_id]} / {rows[second_id]}"
        assert {rows[first_id][1], rows[second_id][1]} == {tx_type}, f"both legs must be {tx_type.value}: {rows[first_id]} / {rows[second_id]}"
        _assert_one_pair_warning(response, f"inverted {tx_type.value} pair (arrival_first={arrival_first})", operation="create", index=0, ref_id=None, departure=LATE, arrival=EARLY)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("make,tx_type", CREATE_KINDS)
    async def test_validate_only_carries_the_warning_and_writes_nothing(self, world, make, tx_type):
        """``commit=False`` (``/validate``): the same warning, ``committed`` False, no blocking issue, nothing written."""
        before = await _rows(world)

        response = await _batch(world, commit=False, creates=make(world, LATE, EARLY))

        assert response.committed is False and response.issues == [], f"validate-only must not commit and must not block: committed={response.committed}, issues: {_render(response.issues)}"
        assert await _rows(world) == before, "validate-only wrote rows"
        _assert_one_pair_warning(response, f"validate-only inverted {tx_type.value} pair", operation="create", index=0, ref_id=None, departure=LATE, arrival=EARLY)

    @pytest.mark.asyncio
    async def test_only_the_inverted_pair_of_a_batch_is_warned(self, world):
        """Two pairs in one batch — a normal one at creates 0-1, an inverted one at creates 2-3: ONE warning, on create 2, the dates
        of the inverted pair. Identified by the pair, never by position of the batch."""
        normal = _transfer_creates(world, EARLY, LATE)
        inverted = _cash_creates(world, LATEST, LATER)

        response = await _batch(world, commit=True, creates=[*normal, *inverted])

        assert response.committed is True and response.issues == [], f"issues: {_render(response.issues)}"
        _assert_one_pair_warning(response, "one inverted pair among two", operation="create", index=2, ref_id=None, departure=LATEST, arrival=LATER)


# ============================================================================
# GUARDS — CREATION: WHEN THE BATCH MUST STAY SILENT
# ============================================================================


class TestNoWarningOnCreate:
    """Guards: before the cure they fail on the missing ``warnings`` field only (the data assertions come first and pass);
    after it they stay green."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("make,tx_type", CREATE_KINDS)
    @COMMIT_MODES
    @ORDERS
    async def test_a_normal_order_does_not_warn(self, world, make, tx_type, commit, arrival_first):
        """Departure on the 3rd, arrival on the 5th: saved, silent."""
        response = await _batch(world, commit=commit, creates=make(world, EARLY, LATE, arrival_first=arrival_first))

        assert response.issues == [], f"issues: {_render(response.issues)}"
        assert response.committed is commit, f"committed={response.committed} on a {'commit' if commit else 'validate'}"
        _assert_no_pair_warning(response, f"normal {tx_type.value} pair")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("make,tx_type", CREATE_KINDS)
    @COMMIT_MODES
    async def test_equal_dates_do_not_warn(self, world, make, tx_type, commit):
        """The same day on both legs is a normal same-day transfer: no warning (the rule is arrival STRICTLY before departure)."""
        response = await _batch(world, commit=commit, creates=make(world, LATE, LATE))

        assert response.issues == [], f"issues: {_render(response.issues)}"
        assert response.committed is commit
        _assert_no_pair_warning(response, f"same-day {tx_type.value} pair")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("positive_first_day", (EARLY, LATE), ids=("positive-leg-earlier", "positive-leg-later"))
    @COMMIT_MODES
    async def test_an_fx_conversion_never_warns(self, world, positive_first_day, commit):
        """An FX_CONVERSION has no departure and arrival: whichever leg is dated first, silent (both orders of the dates)."""
        negative_day = LATE if positive_first_day == EARLY else EARLY

        response = await _batch(world, commit=commit, creates=_fx_creates(world, negative_day, positive_first_day))

        assert response.issues == [], f"issues: {_render(response.issues)}"
        assert response.committed is commit
        _assert_no_pair_warning(response, "FX_CONVERSION pair")

    @pytest.mark.asyncio
    async def test_unlinked_rows_never_warn(self, world):
        """Rows that are not a linked pair, dated in the 'inverted' way: an unlinked WITHDRAWAL on the 5th at ``source`` and an
        unlinked DEPOSIT on the 3rd at ``dest``; and two unlinked ADJUSTMENTs, −2 on the 5th and +2 (with a cost) on the 3rd."""
        creates = [
            {"broker_id": world.source_id, "type": "WITHDRAWAL", "date": LATE.isoformat(), "quantity": "0", "cash": {"code": EUR, "amount": str(-CASH)}, "description": world.description},
            {"broker_id": world.dest_id, "type": "DEPOSIT", "date": EARLY.isoformat(), "quantity": "0", "cash": {"code": EUR, "amount": str(CASH)}, "description": world.description},
            {"broker_id": world.source_id, "asset_id": world.asset_id, "type": "ADJUSTMENT", "date": LATE.isoformat(), "quantity": str(-UNITS), "description": world.description},
            {"broker_id": world.dest_id, "asset_id": world.asset_id, "type": "ADJUSTMENT", "date": EARLY.isoformat(), "quantity": str(UNITS), "description": world.description, "cost_basis_override": COST},
        ]

        response = await _batch(world, commit=True, creates=creates)

        assert response.committed is True and response.issues == [], f"issues: {_render(response.issues)}"
        _assert_no_pair_warning(response, "unlinked rows")


class TestTheDataIsExactlyWhatWasSent:
    """The warning corrects nothing: the rows are saved with the dates the user typed. Green before the cure and after it."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("make,tx_type", CREATE_KINDS)
    @ORDERS
    async def test_an_inverted_pair_keeps_its_dates(self, world, make, tx_type, arrival_first):
        """Each leg is saved on the date it was sent with, on the broker it was sent with, with the quantity or amount sent;
        no leg is swapped, re-dated or re-signed."""
        creates = make(world, LATE, EARLY, arrival_first=arrival_first)

        response = await _batch(world, commit=True, creates=creates)

        assert response.committed is True and response.issues == [], f"the inverted pair was not saved as sent: {_render(response.issues)}"
        rows = await _rows(world)
        for create, tx_id in zip(creates, _created_ids(response), strict=True):
            broker_id, row_type, quantity, amount, row_date, related_id, description = rows[tx_id]
            assert broker_id == create["broker_id"], f"the leg {create} moved broker: {rows[tx_id]}"
            assert row_type == tx_type
            assert row_date.isoformat() == create["date"], f"the leg {create} was re-dated: saved on {row_date}"
            assert description == world.description
            if tx_type == TransactionType.TRANSFER:
                assert quantity == Decimal(create["quantity"]), f"the leg {create} changed quantity: {rows[tx_id]}"
            else:
                assert amount == Decimal(create["cash"]["amount"]), f"the leg {create} changed amount: {rows[tx_id]}"


# ============================================================================
# RED — MODIFICATION: AN UPDATE THAT CHANGES A DATE OF A STORED PAIR
# ============================================================================


class TestAnEditThatInvertsAStoredPairIsWarned:
    """RED until the cure: today the date moves and the response says nothing."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", ("TRANSFER", "CASH_TRANSFER"))
    @COMMIT_MODES
    async def test_moving_the_arrival_before_the_departure_warns(self, world, kind, commit):
        """Stored: departure on the 5th, arrival on the 8th. The arrival is moved to the 3rd: a warning on THAT update
        (``operation`` "update", ``index`` 0, ``ref_id`` the arrival's id), not blocking, and on /commit the date really moved while the
        departure did not."""
        pair = await _store_pair(world, kind, LATE, LATER)

        response = await _batch(world, commit=commit, updates=[{"id": pair.arr, "date": EARLY.isoformat()}])

        assert response.issues == [], f"moving a date was blocked: {_render(response.issues)}"
        assert response.committed is commit
        if commit:
            rows = await _rows(world)
            assert rows[pair.arr][4] == EARLY and rows[pair.dep][4] == LATE, f"the edit must move the arrival only, as asked: arrival {rows[pair.arr][4]}, departure {rows[pair.dep][4]}"
        _assert_one_pair_warning(response, f"{kind}: arrival moved before the departure", operation="update", index=0, ref_id=pair.arr, departure=LATE, arrival=EARLY)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", ("TRANSFER", "CASH_TRANSFER"))
    async def test_moving_the_departure_after_the_arrival_warns(self, world, kind):
        """Stored: departure on the 3rd, arrival on the 5th. The DEPARTURE is moved to the 8th: the arrival now precedes it —
        a warning on the departure's update (``ref_id`` its id), with the final dates."""
        pair = await _store_pair(world, kind, EARLY, LATE)

        response = await _batch(world, commit=True, updates=[{"id": pair.dep, "date": LATER.isoformat()}])

        assert response.committed is True and response.issues == [], f"issues: {_render(response.issues)}"
        _assert_one_pair_warning(response, f"{kind}: departure moved after the arrival", operation="update", index=0, ref_id=pair.dep, departure=LATER, arrival=LATE)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", ("TRANSFER", "CASH_TRANSFER"))
    @pytest.mark.parametrize("arrival_update_first", (False, True), ids=("departure-update-first", "arrival-update-first"))
    async def test_moving_both_legs_is_judged_on_the_final_dates(self, world, kind, arrival_update_first):
        """Stored: departure on the 3rd, arrival on the 10th. BOTH are moved in one batch — the departure to the 10th and the
        arrival to the 8th — so the final order is inverted: ONE warning for the pair (on one of the two updates,
        with its own ``ref_id`` and ``index``), final dates in the params; the order the two updates were listed in is irrelevant."""
        pair = await _store_pair(world, kind, EARLY, LATEST)
        dep_update = {"id": pair.dep, "date": LATEST.isoformat()}
        arr_update = {"id": pair.arr, "date": LATER.isoformat()}
        updates = [arr_update, dep_update] if arrival_update_first else [dep_update, arr_update]

        response = await _batch(world, commit=True, updates=updates)

        assert response.committed is True and response.issues == [], f"issues: {_render(response.issues)}"
        warning = _assert_one_pair_warning(response, f"{kind}: both legs moved, final order inverted", operation="update", ref_ids={pair.dep, pair.arr}, departure=LATEST, arrival=LATER)
        assert updates[warning.index]["id"] == warning.ref_id, f"the warning's index {warning.index} must be the index of the update of ref_id {warning.ref_id}: {_render([warning])}"
        rows = await _rows(world)
        assert (rows[pair.dep][4], rows[pair.arr][4]) == (LATEST, LATER), f"both dates must be saved as sent: {rows[pair.dep][4]}, {rows[pair.arr][4]}"


# ============================================================================
# GUARDS — MODIFICATION: WHEN THE BATCH MUST STAY SILENT
# ============================================================================


class TestNoWarningOnEdit:
    """Guards: before the cure they fail on the missing ``warnings`` field only; after it they stay green."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", ("TRANSFER", "CASH_TRANSFER"))
    @pytest.mark.parametrize("departure_first", (True, False), ids=("departure-update-first", "arrival-update-first"))
    async def test_moving_both_legs_to_a_normal_final_order_does_not_warn(self, world, kind, departure_first):
        """Stored: departure on the 3rd, arrival on the 5th. Both are moved later together — departure to the 8th, arrival to the 10th.
        Taken one after the other the first move would invert the pair for a moment (departure on the 8th, arrival still on the
        5th): the judge looks at the FINAL dates of both, so silent, whichever update is listed first."""
        pair = await _store_pair(world, kind, EARLY, LATE)
        dep_update = {"id": pair.dep, "date": LATER.isoformat()}
        arr_update = {"id": pair.arr, "date": LATEST.isoformat()}

        response = await _batch(world, commit=True, updates=[dep_update, arr_update] if departure_first else [arr_update, dep_update])

        assert response.committed is True and response.issues == [], f"issues: {_render(response.issues)}"
        rows = await _rows(world)
        assert (rows[pair.dep][4], rows[pair.arr][4]) == (LATER, LATEST), "both dates must be saved as sent"
        _assert_no_pair_warning(response, f"{kind}: both legs moved, final order normal")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", ("TRANSFER", "CASH_TRANSFER"))
    async def test_fixing_an_inverted_stored_pair_does_not_warn(self, world, kind):
        """Stored inverted (departure on the 5th, arrival on the 3rd); both legs moved so the order becomes normal: silent."""
        pair = await _store_pair(world, kind, LATE, EARLY)

        response = await _batch(world, commit=True, updates=[{"id": pair.dep, "date": EARLY.isoformat()}, {"id": pair.arr, "date": LATE.isoformat()}])

        assert response.committed is True and response.issues == [], f"issues: {_render(response.issues)}"
        _assert_no_pair_warning(response, f"{kind}: stored inverted pair fixed")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", ("TRANSFER", "CASH_TRANSFER"))
    @COMMIT_MODES
    async def test_an_edit_that_leaves_the_dates_alone_never_judges_a_stored_pair(self, world, kind, commit):
        """Stored inverted (departure on the 5th, arrival on the 3rd), e.g. by an old release or a CSV import. Editing the description of
        BOTH legs (as the app edits a pair) changes no date: no warning, the dates stay."""
        pair = await _store_pair(world, kind, LATE, EARLY)
        new_description = f"{world.marker} edited"

        response = await _batch(world, commit=commit, updates=[{"id": pair.dep, "description": new_description}, {"id": pair.arr, "description": new_description}])

        assert response.issues == [], f"editing the description of a stored pair was blocked: {_render(response.issues)}"
        assert response.committed is commit
        if commit:
            rows = await _rows(world)
            assert (rows[pair.dep][4], rows[pair.arr][4]) == (LATE, EARLY), "the stored dates must not be touched by a description edit"
            assert rows[pair.dep][6] == rows[pair.arr][6] == new_description
        _assert_no_pair_warning(response, f"{kind}: description edit of a stored inverted pair")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", ("TRANSFER", "CASH_TRANSFER"))
    async def test_an_update_carrying_the_stored_date_is_not_a_date_change(self, world, kind):
        """The Bulk editor may send every field of a row. A date equal to the stored one changes nothing: silent on an inverted stored
        pair. (Derived from the specification, "an update that does not change the date": the comparison is with the stored date.)"""
        pair = await _store_pair(world, kind, LATE, EARLY)
        new_description = f"{world.marker} edited"

        response = await _batch(
            world,
            commit=True,
            updates=[{"id": pair.dep, "date": LATE.isoformat(), "description": new_description}, {"id": pair.arr, "date": EARLY.isoformat(), "description": new_description}],
        )

        assert response.committed is True and response.issues == [], f"issues: {_render(response.issues)}"
        _assert_no_pair_warning(response, f"{kind}: update carrying the stored dates")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", ("FX_CONVERSION", "ADJUSTMENT"))
    @pytest.mark.parametrize("move", ("arr", "dep"))
    async def test_fx_conversion_and_adjustment_pairs_never_warn_on_edit(self, world, kind, move):
        """A stored linked FX_CONVERSION or ADJUSTMENT pair (the latter only an old database holds) whose one date is moved so
        the positive leg ends before the negative: never a warning, whichever leg moves."""
        pair = await _store_pair(world, kind, EARLY, LATE)
        # Stored: negative leg on the 3rd, positive on the 5th. Either move leaves the positive leg dated before the negative one.
        update = {"id": pair.arr, "date": date(2025, 2, 1).isoformat()} if move == "arr" else {"id": pair.dep, "date": LATER.isoformat()}

        response = await _batch(world, commit=True, updates=[update])

        assert response.committed is True and response.issues == [], f"issues: {_render(response.issues)}"
        _assert_no_pair_warning(response, f"{kind}: date moved ({move})")
