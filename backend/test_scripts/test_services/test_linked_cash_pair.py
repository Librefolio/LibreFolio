"""
A linked cash pair that contradicts its own type is refused at entry (W6-7: C-42 + W-B46; the developer's decision, 23/10/2026).

Why. ``TX_TYPE_METADATA`` declares the ``pair_field_constraints`` of a pair: CASH_TRANSFER wants ONE currency, two
DIFFERENT brokers and OPPOSITE amounts; FX_CONVERSION wants two DIFFERENT currencies on ONE broker. The forms, the
promotion and the imports already write them so, but ``TransactionValidationMixin._validate_linked_pair``
(``validation.py``), the only judge of a ``link_uuid`` group of two creates, checked only the brokers of those two types.
A client of ``POST /transactions/commit`` could save a CASH_TRANSFER of -100 EUR against +90 USD (money that changes
currency and amount with no exchange), or an FX_CONVERSION from EUR to EUR.

The principle: protect the ENTRY of data. No cleanup of what is stored: a linked pair a database already holds is neither
judged nor changed by a batch that does not create it.

The cure: after the broker checks, ``_validate_linked_pair`` answers
- a CASH_TRANSFER pair in two currencies with ``pairCurrencyMismatch`` (``currencyA``, ``currencyB``);
- a CASH_TRANSFER pair whose amounts are not exactly opposite, in ``Decimal``, with ``pairAmountMismatch`` (``amountA``,
  ``amountB``);
- an FX_CONVERSION pair in one currency with ``pairCurrencySame`` (``currency``);
as a ``TXValidationIssue`` on the FIRST create of the group (``operation`` "create", ``ref_id`` None); the batch is not
committed, on /commit and on /validate, and nothing is written. The UI words each code from
``transactions.errors.<code>`` in EN, IT, FR and ES.

Reds — fail before the cure:

- ``TestTheRuleAlone``: ``_validate_linked_pair`` on two legs in memory answers each refusal (today ``None``).
- ``TestAnIncoherentPairIsRefused``: the same pairs through the batch, on /commit and on /validate: one issue on create 0,
  nothing written.
- ``TestTheTableAndTheRuleAgree`` (W-B46): the refusals follow ``TX_TYPE_METADATA``; a constraint of the table the rule
  does not know fails the test, so the two cannot drift apart unseen.
- ``TestTheMessagesExistInEveryLanguage``: the three codes are non-empty messages in the four languages, read without the
  English fallback.

Guards — green before the cure, and the cure must keep them green:

- ``TestWhatTheRuleLeavesAlone``: a coherent CASH_TRANSFER pair and a coherent FX_CONVERSION pair still commit, linked;
  amounts that differ by one decimal are refused, equal ones in a different notation (``100`` and ``-100.00``) are not.
- ``TestStoredPairsAreNotJudged``: a linked CASH_TRANSFER pair stored with different currencies (written straight into the
  session, as an old database holds one) is neither refused nor touched by a batch that edits the description of both rows.
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

from backend.app.db.models import Broker, Transaction, TransactionType
from backend.app.db.session import get_async_engine
from backend.app.schemas.transactions.batch import TXBatchResponse, TXValidationIssue
from backend.app.schemas.transactions.type_metadata import TX_TYPE_METADATA
from backend.app.services.transactions.transaction_service import TransactionService
from backend.app.utils.datetime_utils import utcnow
from scripts.i18n_catalog import flatten, load_catalog

EUR = "EUR"
USD = "USD"
DAY = date(2025, 2, 3)
AMOUNT = Decimal("100")
UI_LANGUAGES = ("en", "it", "fr", "es")
CURRENCY_CODE = "pairCurrencyMismatch"
AMOUNT_CODE = "pairAmountMismatch"
SAME_CURRENCY_CODE = "pairCurrencySame"
NEW_CODES = (CURRENCY_CODE, AMOUNT_CODE, SAME_CURRENCY_CODE)


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
    """One test's own data: two brokers that may go below zero, so no deposit is needed to move cash."""

    session: AsyncSession
    marker: str
    source_id: int
    dest_id: int

    @property
    def description(self) -> str:
        """The one description both rows of a pair carry, as a pair requires."""
        return f"{self.marker} pair"


@pytest_asyncio.fixture
async def world(session) -> World:
    marker = f"cash-pair {uuid.uuid4().hex}"
    now = utcnow()
    source = Broker(name=f"{marker} source", description="linked cash pair: the broker cash leaves", allow_cash_overdraft=True, allow_asset_shorting=False, created_at=now, updated_at=now)
    dest = Broker(name=f"{marker} dest", description="linked cash pair: the broker cash reaches", allow_cash_overdraft=True, allow_asset_shorting=False, created_at=now, updated_at=now)
    session.add_all([source, dest])
    await session.flush()
    # Plain ids: a savepoint that rolls a refused batch back expires every ORM object, and the tests read by id afterwards.
    return World(session=session, marker=marker, source_id=source.id, dest_id=dest.id)


# ============================================================================
# HELPERS
# ============================================================================


def _leg(world: World, tx_type: str, broker_id: int, currency: str, amount: str, link_uuid: str) -> dict:
    return {"broker_id": broker_id, "type": tx_type, "date": DAY.isoformat(), "quantity": "0", "cash": {"code": currency, "amount": amount}, "description": world.description, "link_uuid": link_uuid}


def _cash_pair(world: World, *, out_currency: str = EUR, out_amount: str = "-100", in_currency: str = EUR, in_amount: str = "100") -> list[dict]:
    """A CASH_TRANSFER pair across the two brokers: ``out`` at ``source``, ``in`` at ``dest``."""
    link_uuid = str(uuid.uuid4())
    return [
        _leg(world, "CASH_TRANSFER", world.source_id, out_currency, out_amount, link_uuid),
        _leg(world, "CASH_TRANSFER", world.dest_id, in_currency, in_amount, link_uuid),
    ]


def _fx_pair(world: World, *, out_currency: str = EUR, in_currency: str = USD) -> list[dict]:
    """An FX_CONVERSION pair on ONE broker: -100 out, +110 in."""
    link_uuid = str(uuid.uuid4())
    return [
        _leg(world, "FX_CONVERSION", world.source_id, out_currency, "-100", link_uuid),
        _leg(world, "FX_CONVERSION", world.source_id, in_currency, "110", link_uuid),
    ]


async def _batch(world: World, *, commit: bool, creates: list[dict] | None = None, updates: list[dict] | None = None) -> TXBatchResponse:
    """The batch as ``POST /transactions/commit`` (``commit=True``) or ``/validate`` runs it, its transaction included.
    A savepoint stands in for the request's transaction; the session fixture still rolls everything back."""
    savepoint = await world.session.begin_nested()
    response = await TransactionService(world.session).execute_batch(
        creates_raw=creates or [],
        updates_raw=updates or [],
        deletes=[],
        commit=commit,
    )
    if commit and response.committed:
        await savepoint.commit()
    else:
        await savepoint.rollback()
    return response


def _render(issues: list[TXValidationIssue]) -> str:
    return "; ".join(f"{issue.operation}[{issue.index}] ref_id={issue.ref_id} code={issue.code} params={issue.params} error={issue.error!r}" for issue in issues) or "none"


def _views(issues: list[TXValidationIssue]) -> list[tuple]:
    """What the contract fixes of an issue: where it is, its code and its params — never its text."""
    return [(issue.operation, issue.index, issue.ref_id, issue.code, issue.params) for issue in issues]


async def _rows(world: World) -> dict[int, tuple]:
    """Every row of the test's two brokers, re-read: ``{id: (broker_id, type, amount, currency, related_transaction_id, description)}``."""
    statement = select(Transaction).where(Transaction.broker_id.in_([world.source_id, world.dest_id])).execution_options(populate_existing=True)
    rows = (await world.session.execute(statement)).scalars().all()
    return {row.id: (row.broker_id, row.type, row.amount, row.currency, row.related_transaction_id, row.description) for row in rows}


def _created_ids(response: TXBatchResponse) -> list[int]:
    return [tx_id for result in sorted((r for r in response.results if r.operation == "create"), key=lambda r: r.index) for tx_id in result.ids]


def _memory_leg(tx_type: TransactionType, broker_id: int, currency: str, amount: str) -> Transaction:
    return Transaction(broker_id=broker_id, type=tx_type, date=DAY, quantity=Decimal("0"), amount=Decimal(amount), currency=currency)


# Each refusal: (id, the pair's shape, the code and the params it must answer with).
CASH_REFUSALS = [
    pytest.param({"out_currency": EUR, "out_amount": "-100", "in_currency": USD, "in_amount": "100"}, CURRENCY_CODE, {"currencyA": EUR, "currencyB": USD}, id="two-currencies"),
    pytest.param({"out_currency": EUR, "out_amount": "-100", "in_currency": EUR, "in_amount": "90"}, AMOUNT_CODE, {"amountA": "-100", "amountB": "90"}, id="amounts-differ"),
    pytest.param({"out_currency": EUR, "out_amount": "-100", "in_currency": EUR, "in_amount": "-100"}, AMOUNT_CODE, {"amountA": "-100", "amountB": "-100"}, id="same-sign"),
    pytest.param({"out_currency": EUR, "out_amount": "-100.00", "in_currency": EUR, "in_amount": "100.01"}, AMOUNT_CODE, {"amountA": "-100.00", "amountB": "100.01"}, id="one-hundredth-off"),
]


# ============================================================================
# THE RULE ALONE
# ============================================================================


class TestTheRuleAlone:
    """RED until the cure: the function that judges a linked pair, on two legs in memory (no session, no database)."""

    @pytest.mark.parametrize(
        ("legs", "code", "params"),
        [
            pytest.param(((1, EUR, "-100"), (2, USD, "100")), CURRENCY_CODE, {"currencyA": EUR, "currencyB": USD}, id="cash-two-currencies"),
            pytest.param(((1, EUR, "-100"), (2, EUR, "90")), AMOUNT_CODE, {"amountA": "-100", "amountB": "90"}, id="cash-amounts-differ"),
            pytest.param(((1, EUR, "100"), (2, EUR, "100")), AMOUNT_CODE, {"amountA": "100", "amountB": "100"}, id="cash-same-sign"),
        ],
    )
    def test_an_incoherent_cash_transfer_is_refused(self, legs, code, params):
        a = _memory_leg(TransactionType.CASH_TRANSFER, legs[0][0], legs[0][1], legs[0][2])
        b = _memory_leg(TransactionType.CASH_TRANSFER, legs[1][0], legs[1][1], legs[1][2])

        answer = TransactionService._validate_linked_pair(a, b)

        assert answer is not None, f"_validate_linked_pair accepted a CASH_TRANSFER pair {legs}: it answered None"
        message, answered_code, answered_params = answer
        assert (answered_code, answered_params) == (code, params), f"expected {code} with {params}, got {answered_code} with {answered_params}: {message!r}"

    def test_an_fx_conversion_in_one_currency_is_refused(self):
        a = _memory_leg(TransactionType.FX_CONVERSION, 1, EUR, "-100")
        b = _memory_leg(TransactionType.FX_CONVERSION, 1, EUR, "100")

        answer = TransactionService._validate_linked_pair(a, b)

        assert answer is not None, "_validate_linked_pair accepted an FX_CONVERSION from EUR to EUR: it answered None"
        message, code, params = answer
        assert (code, params) == (SAME_CURRENCY_CODE, {"currency": EUR}), f"expected {SAME_CURRENCY_CODE} with the currency, got {code} with {params}: {message!r}"

    def test_the_older_rules_still_come_first(self):
        """Guard: two legs on ONE broker are refused for the broker (``pairSameBroker``), whatever their currencies."""
        a = _memory_leg(TransactionType.CASH_TRANSFER, 1, EUR, "-100")
        b = _memory_leg(TransactionType.CASH_TRANSFER, 1, USD, "90")

        answer = TransactionService._validate_linked_pair(a, b)

        assert answer is not None and answer[1] == "pairSameBroker", f"one broker is refused first, got {answer}"

    @pytest.mark.parametrize(
        ("tx_type", "legs"),
        [
            pytest.param(TransactionType.CASH_TRANSFER, ((1, EUR, "-100"), (2, EUR, "100")), id="cash"),
            pytest.param(TransactionType.CASH_TRANSFER, ((1, EUR, "-100.00"), (2, EUR, "100")), id="cash-other-notation"),
            pytest.param(TransactionType.FX_CONVERSION, ((1, EUR, "-100"), (1, USD, "110")), id="fx"),
        ],
    )
    def test_a_coherent_pair_is_accepted(self, tx_type, legs):
        """Guard, green before and after."""
        a = _memory_leg(tx_type, legs[0][0], legs[0][1], legs[0][2])
        b = _memory_leg(tx_type, legs[1][0], legs[1][1], legs[1][2])

        assert TransactionService._validate_linked_pair(a, b) is None


# ============================================================================
# THE BATCH
# ============================================================================


class TestAnIncoherentPairIsRefused:
    """RED until the cure: ``POST /transactions/commit`` and ``/validate`` on a pair that contradicts its type."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", (True, False), ids=("commit", "validate"))
    @pytest.mark.parametrize(("shape", "code", "params"), CASH_REFUSALS)
    async def test_a_cash_transfer_pair_is_refused_on_its_first_create(self, world, commit, shape, code, params):
        before = await _rows(world)

        response = await _batch(world, commit=commit, creates=_cash_pair(world, **shape))

        assert _views(response.issues) == [("create", 0, None, code, params)], f"a CASH_TRANSFER pair {shape} ({'/commit' if commit else '/validate'}) must be refused with exactly one {code} on create 0; issues: {_render(response.issues)}"
        assert response.committed is False, f"the refused pair was committed: {_render(response.issues)}"
        assert await _rows(world) == before, "a refused batch wrote rows"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", (True, False), ids=("commit", "validate"))
    async def test_an_fx_conversion_in_one_currency_is_refused_on_its_first_create(self, world, commit):
        before = await _rows(world)

        response = await _batch(world, commit=commit, creates=_fx_pair(world, out_currency=EUR, in_currency=EUR))

        assert _views(response.issues) == [("create", 0, None, SAME_CURRENCY_CODE, {"currency": EUR})], f"an FX_CONVERSION from EUR to EUR ({'/commit' if commit else '/validate'}) must be refused with exactly one {SAME_CURRENCY_CODE} on create 0; issues: {_render(response.issues)}"
        assert response.committed is False
        assert await _rows(world) == before, "a refused batch wrote rows"

    @pytest.mark.asyncio
    async def test_the_refusal_is_english_text_that_names_the_two_values(self, world):
        """The issue's own text is English; the UI never shows it (it words the code)."""
        response = await _batch(world, commit=True, creates=_cash_pair(world, in_currency=USD))

        refused = [issue for issue in response.issues if issue.code == CURRENCY_CODE]

        assert len(refused) == 1, f"expected one {CURRENCY_CODE} issue, got: {_render(response.issues)}"
        assert EUR in refused[0].error and USD in refused[0].error, f"the refusal must name both currencies: {refused[0].error!r}"


class TestTheTableAndTheRuleAgree:
    """W-B46: the rules the table declares are the rules the entry enforces."""

    # What the rule enforces for each pair type, by (field, relation) of ``pair_field_constraints``.
    ENFORCED = {
        TransactionType.TRANSFER: {("asset_id", "equal"), ("broker_id", "different"), ("quantity", "opposite")},
        TransactionType.CASH_TRANSFER: {("cash_currency", "equal"), ("broker_id", "different"), ("cash_amount", "opposite")},
        TransactionType.FX_CONVERSION: {("cash_currency", "different"), ("broker_id", "equal")},
    }

    def test_every_declared_constraint_of_a_pair_type_is_enforced(self):
        declared = {tx_type: {(c.field, c.relation) for c in meta.pair_field_constraints} for tx_type, meta in TX_TYPE_METADATA.items() if meta.pair_field_constraints and tx_type != TransactionType.ADJUSTMENT}

        assert declared == self.ENFORCED, f"TX_TYPE_METADATA declares pair constraints the entry rule (validation.py) does not know, or the reverse: declared {declared}, enforced {self.ENFORCED}. Teach _validate_linked_pair the new constraint, then this table."

    @pytest.mark.asyncio
    async def test_a_pair_that_breaks_a_declared_cash_constraint_is_refused_by_the_batch(self, world):
        """Each declared constraint of CASH_TRANSFER and FX_CONVERSION, broken alone, is a refusal of the batch."""
        broken = {
            ("cash_currency", "equal"): _cash_pair(world, in_currency=USD),
            ("cash_amount", "opposite"): _cash_pair(world, in_amount="99"),
            ("cash_currency", "different"): _fx_pair(world, in_currency=EUR),
        }
        for constraint, creates in broken.items():
            response = await _batch(world, commit=False, creates=creates)
            assert response.issues and response.issues[0].code in NEW_CODES, f"breaking {constraint} alone is not refused by a pair code: {_render(response.issues)}"


class TestTheMessagesExistInEveryLanguage:
    """RED until the cure (the keys are added with ``dev.py i18n add``)."""

    @pytest.mark.parametrize("language", UI_LANGUAGES)
    @pytest.mark.parametrize("code", NEW_CODES)
    def test_the_code_has_its_message(self, language, code):
        """``transactions.errors.<code>`` is non-empty in ``language``, read without the English fallback: without it the
        Bulk editor shows the raw English text of the issue."""
        messages = flatten(load_catalog(language, fallback=False))

        message = str(messages.get(f"transactions.errors.{code}") or "").strip()

        assert message, f"transactions.errors.{code} has no {language} message"


# ============================================================================
# GUARDS — WHAT THE RULE MUST LEAVE ALONE
# ============================================================================


class TestWhatTheRuleLeavesAlone:
    """Green before the cure and after it."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", (True, False), ids=("commit", "validate"))
    async def test_a_coherent_cash_transfer_pair_commits_linked(self, world, commit):
        response = await _batch(world, commit=commit, creates=_cash_pair(world))

        assert response.issues == [], f"a coherent CASH_TRANSFER pair was refused ({'/commit' if commit else '/validate'}): {_render(response.issues)}"
        if commit:
            assert response.committed is True
            giving_id, receiving_id = _created_ids(response)
            rows = await _rows(world)
            assert (rows[giving_id][4], rows[receiving_id][4]) == (receiving_id, giving_id), f"the legs must point at each other: {rows[giving_id]} / {rows[receiving_id]}"

    @pytest.mark.asyncio
    async def test_the_same_amount_in_another_notation_is_opposite(self, world):
        """``-100.00`` against ``100`` is one amount: the comparison is in ``Decimal``, never on the text."""
        response = await _batch(world, commit=True, creates=_cash_pair(world, out_amount="-100.00", in_amount="100"))

        assert response.committed is True and response.issues == [], f"opposite amounts in two notations were refused: {_render(response.issues)}"

    @pytest.mark.asyncio
    async def test_a_coherent_fx_conversion_commits_linked(self, world):
        response = await _batch(world, commit=True, creates=_fx_pair(world))

        assert response.committed is True and response.issues == [], f"a coherent FX_CONVERSION was refused: {_render(response.issues)}"
        giving_id, receiving_id = _created_ids(response)
        rows = await _rows(world)
        assert (rows[giving_id][4], rows[receiving_id][4]) == (receiving_id, giving_id)

    @pytest.mark.asyncio
    async def test_two_unlinked_cash_transfers_with_different_currencies_commit(self, world):
        """Only a LINKED group is a pair: the same two legs with no ``link_uuid`` are two plain rows, as today."""
        creates = [{key: value for key, value in leg.items() if key != "link_uuid"} for leg in _cash_pair(world, in_currency=USD)]

        response = await _batch(world, commit=True, creates=creates)

        assert CURRENCY_CODE not in {issue.code for issue in response.issues}, f"unlinked rows were judged as a pair: {_render(response.issues)}"


class TestStoredPairsAreNotJudged:
    """Green before the cure and after it: the rule refuses at entry only, it never reads what a database already holds."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", (True, False), ids=("commit", "validate"))
    async def test_editing_both_descriptions_of_a_stored_incoherent_pair_commits(self, world, commit):
        now = utcnow()
        common = {"type": TransactionType.CASH_TRANSFER, "date": DAY, "quantity": Decimal("0"), "description": world.description, "created_at": now, "updated_at": now}
        giving = Transaction(broker_id=world.source_id, amount=Decimal("-100"), currency=EUR, **common)
        receiving = Transaction(broker_id=world.dest_id, amount=Decimal("90"), currency=USD, **common)
        world.session.add_all([giving, receiving])
        await world.session.flush()
        giving.related_transaction_id, receiving.related_transaction_id = receiving.id, giving.id
        await world.session.flush()
        giving_id, receiving_id = giving.id, receiving.id
        new_description = f"{world.marker} edited"

        response = await _batch(world, commit=commit, updates=[{"id": giving_id, "description": new_description}, {"id": receiving_id, "description": new_description}])

        assert not {issue.code for issue in response.issues} & set(NEW_CODES), f"a stored pair was judged by the entry rule on an update ({'/commit' if commit else '/validate'}): {_render(response.issues)}"
        if commit:
            assert response.committed is True, f"editing both descriptions of a stored pair was refused: {_render(response.issues)}"
            rows = await _rows(world)
            assert rows[giving_id][2:5] == (Decimal("-100"), EUR, receiving_id), f"giving leg after the edit: {rows[giving_id]}"
            assert rows[receiving_id][2:5] == (Decimal("90"), USD, giving_id), f"receiving leg after the edit: {rows[receiving_id]}"
