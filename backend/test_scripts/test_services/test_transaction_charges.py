"""
Linked charges: a FEE or a TAX points at the transaction it belongs to (project 66, issue #25, lot R2).

Why. A charge (FEE, TAX) can name its parent through ``transactions.parent_transaction_id`` (lot R1: column, index
``idx_transactions_parent``). R2 adds the rules that say which link is valid, the lists of types on each side, and the
one reader of the links. Nothing of this exists yet: the file is RED FIRST. The new code is imported INSIDE each test, so
a missing module or helper is one red per rule with a «red until R2» message, never one collection error.

The contract (developer decisions D2 and D6b):

A. ``type_metadata.py``: ``TXTypeMetadata.charge_role`` is ``"charge"`` for FEE and TAX, ``"parent"`` for BUY, SELL,
   DIVIDEND, INTEREST, DEPOSIT and WITHDRAWAL, None for every other type. ``charge_types()`` and ``charge_parent_types()``
   read the table at call time. The two lists are disjoint (no chain: a charge is never a parent).
B. ``TXValidationCode``: ``chargeNotACharge``, ``chargeParentNotFound``, ``chargeParentTypeNotAllowed``,
   ``chargeBrokerMismatch``, ``chargeAssetMismatch``, ``chargeAssetMissing``, ``chargesBlockParentType``, ``chargeRowIsPaired``, each with a
   message under ``transactions.errors.<code>`` in EN, IT, FR and ES.
C. ``services/transactions/charges.py``:
   - ``charge_link_issue(charge, parent, parent_id)``: pure, the FIRST violation as (message, code, params), in the order
     type of the charge, charge paired, parent found, type of the parent, parent paired, broker, asset missing, asset
     mismatch; None when valid. ``row_is_paired(row)`` is the FIELD ``related_transaction_id`` (not the type).
   - ``charges_parent_type_issue(parent, charge_ids)``: rule 6, a row with charges whose final type is not a parent type.
   - ``charge_ids_by_parent(session, parent_ids)``: the reader, every id asked a key, ids sorted, nothing else, no query
     for an empty input; its statement (``charge_ids_by_parent_statement``) is answered through ``idx_transactions_parent``.

Reds — fail before R2:

- ``TestTheTypeListsComeFromTheTable``: ``charge_role``, the two helpers, the literal lists (D2), the types payload.
- ``TestTheNewCodesAreSpeakable``: the eight members exist and have a message in four languages.
- ``TestAChargeLinkIsJudgedInOrder``: every refusal, its params, and the order when several rules break at once.
- ``TestAParentWithChargesKeepsAParentType``: rule 6.
- ``TestTheReaderOfTheLinks``: ``charge_ids_by_parent`` on the lane test database; its plan uses the partial index.

Guards — what the rules must ACCEPT (the cure must not narrow them):

- ``TestWhatALinkMayDifferIn``: another date (before or after) and another currency are valid.
- ``TestEveryChargeOnEveryParent``: FEE and TAX on each of the six parent types.
- ``TestSwapsOfAParentStayValid``: BUY to SELL, DEPOSIT to WITHDRAWAL, DIVIDEND to INTEREST keep their charges.
"""

import sys
import uuid
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

# Before any app module that reads DATABASE_URL: this lane's test database.
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Broker, Transaction, TransactionType
from backend.app.db.session import get_async_engine
from backend.app.schemas.transactions import type_metadata as type_metadata_module
from backend.app.schemas.transactions.batch import TXValidationCode
from backend.app.schemas.transactions.type_metadata import EVENT_TYPE_METADATA, TX_TYPE_METADATA, TXTypesResponse
from backend.app.utils.datetime_utils import utcnow
from scripts.i18n_catalog import flatten, load_catalog

T = TransactionType
UI_LANGUAGES = ("en", "it", "fr", "es")
NEW_CODES = (
    "chargeNotACharge",
    "chargeParentNotFound",
    "chargeParentTypeNotAllowed",
    "chargeBrokerMismatch",
    "chargeAssetMismatch",
    "chargeAssetMissing",
    "chargesBlockParentType",
    "chargeRowIsPaired",
)
# D2, pinned literally in ONE test; everything else derives from the table.
LITERAL_CHARGES = frozenset({T.FEE, T.TAX})
LITERAL_PARENTS = frozenset({T.BUY, T.SELL, T.DIVIDEND, T.INTEREST, T.DEPOSIT, T.WITHDRAWAL})
DAY = date(2025, 3, 4)


# ============================================================================
# LAZY ACCESS TO THE CODE THAT DOES NOT EXIST YET
# ============================================================================


def _charges():
    """The R2 module, or a clear red for the one rule under test."""
    try:
        from backend.app.services.transactions import charges  # noqa: PLC0415 — lazy: a missing module is one red per rule, not one collection error
    except ImportError as exc:
        pytest.fail(f"red until R2: backend/app/services/transactions/charges.py is missing ({exc})")
    return charges


def _helper(name: str):
    """A function of ``charges`` by name."""
    module = _charges()
    func = getattr(module, name, None)
    assert func is not None, f"red until R2: charges.{name} is missing"
    return func


def _type_lists() -> tuple[frozenset, frozenset]:
    """(charge_types(), charge_parent_types()) from type_metadata, or a red."""
    charge_types = getattr(type_metadata_module, "charge_types", None)
    parent_types = getattr(type_metadata_module, "charge_parent_types", None)
    assert charge_types is not None, "red until R2: type_metadata.charge_types() is missing"
    assert parent_types is not None, "red until R2: type_metadata.charge_parent_types() is missing"
    return charge_types(), parent_types()


def _code(name: str) -> str:
    """The value of a new TXValidationCode member, or a red naming it."""
    member = getattr(TXValidationCode, _member_name(name), None)
    assert member is not None, f"red until R2: TXValidationCode has no member for {name}"
    assert member.value == name
    return member.value


def _member_name(code: str) -> str:
    """camelCase value to the UPPER_SNAKE member name the enum uses (chargeNotACharge to CHARGE_NOT_A_CHARGE)."""
    out = []
    for i, ch in enumerate(code):
        if ch.isupper() and i and not (code[i - 1].isupper() and (i + 1 >= len(code) or code[i + 1].isupper())):
            out.append("_")
        out.append(ch.upper())
    return "".join(out)


def _code_members() -> dict[str, TXValidationCode]:
    """The new codes found in the enum BY VALUE, whatever the member names are."""
    by_value = {member.value: member for member in TXValidationCode}
    missing = [c for c in NEW_CODES if c not in by_value]
    assert not missing, f"red until R2: TXValidationCode lacks the values {missing}"
    return {c: by_value[c] for c in NEW_CODES}


def _tx(tx_type: TransactionType, *, broker_id: int = 1, asset_id: int | None = None, day: date = DAY, currency: str = "EUR", tx_id: int | None = None, related_id: int | None = None) -> Transaction:
    """An in-memory row: the pure rules never touch a session."""
    return Transaction(id=tx_id, broker_id=broker_id, asset_id=asset_id, type=tx_type, date=day, quantity=Decimal("0"), amount=Decimal("-5"), currency=currency, related_transaction_id=related_id)


def _issue(charge: Transaction, parent: Transaction | None, parent_id: int = 77):
    return _helper("charge_link_issue")(charge, parent, parent_id)


# ============================================================================
# A. THE TYPE LISTS
# ============================================================================


class TestTheTypeListsComeFromTheTable:
    """``charge_role`` in ``TX_TYPE_METADATA`` is the one place that says who is a charge and who may be a parent."""

    def test_the_two_lists_are_pinned_literally(self):
        """D2: FEE and TAX are the charges; BUY, SELL, DIVIDEND, INTEREST, DEPOSIT, WITHDRAWAL the parents."""
        charges, parents = _type_lists()

        assert charges == LITERAL_CHARGES
        assert parents == LITERAL_PARENTS

    def test_every_type_has_a_role_that_the_table_derives_the_lists_from(self):
        """The helpers are the table read back, not a second list."""
        charges, parents = _type_lists()
        for tx_type, meta in TX_TYPE_METADATA.items():
            assert hasattr(meta, "charge_role"), "red until R2: TXTypeMetadata.charge_role is missing"
            assert (tx_type in charges) == (meta.charge_role == "charge"), tx_type
            assert (tx_type in parents) == (meta.charge_role == "parent"), tx_type

    def test_the_other_types_have_no_role(self):
        """TRANSFER, FX_CONVERSION, CASH_TRANSFER, ADJUSTMENT are neither side."""
        charges, parents = _type_lists()
        for tx_type, meta in TX_TYPE_METADATA.items():
            if tx_type not in charges and tx_type not in parents:
                assert getattr(meta, "charge_role", "missing") is None, tx_type

    def test_the_lists_are_disjoint_so_no_chain_exists(self):
        charges, parents = _type_lists()

        assert not (charges & parents)

    def test_the_helpers_read_the_table_at_call_time(self, monkeypatch):
        """Change a role in the table, the answer follows: no list frozen at import."""
        charges, _ = _type_lists()
        assert T.BUY not in charges
        meta = TX_TYPE_METADATA[T.BUY]
        monkeypatch.setitem(TX_TYPE_METADATA, T.BUY, meta.model_copy(update={"charge_role": "charge"}))

        charges_now, parents_now = _type_lists()

        assert T.BUY in charges_now
        assert T.BUY not in parents_now

    def test_the_types_payload_carries_the_role_of_every_type(self):
        """What ``GET /transactions/types`` answers: ``charge_role`` for each type, as the table holds it."""
        payload = TXTypesResponse(transaction_types=list(TX_TYPE_METADATA.values()), event_types=EVENT_TYPE_METADATA).model_dump(mode="json")

        by_code = {item["code"]: item for item in payload["transaction_types"]}
        for tx_type, meta in TX_TYPE_METADATA.items():
            item = by_code[tx_type.value]
            assert "charge_role" in item, "red until R2: the types payload has no charge_role"
            assert item["charge_role"] == meta.charge_role, tx_type


# ============================================================================
# B. THE CODES
# ============================================================================


class TestTheNewCodesAreSpeakable:
    """The eight codes exist in the enum and the UI words each of them in four languages."""

    def test_the_enum_has_the_eight_members(self):
        assert set(_code_members()) == set(NEW_CODES)

    @pytest.mark.parametrize("language", UI_LANGUAGES)
    @pytest.mark.parametrize("code", NEW_CODES)
    def test_every_code_has_a_message_in_every_language(self, code, language):
        """Read without the English fallback: a missing translation is a red, not a quiet English line."""
        messages = flatten(load_catalog(language, fallback=False))

        message = str(messages.get(f"transactions.errors.{code}") or "").strip()

        assert message, f"transactions.errors.{code} has no {language} message"


# ============================================================================
# C1. THE RULES OF ONE LINK
# ============================================================================


class TestAChargeLinkIsJudgedInOrder:
    """``charge_link_issue``: None when valid, else the FIRST violation as (message, code, params)."""

    def test_a_valid_link_is_none(self):
        charge = _tx(T.FEE, asset_id=5)
        parent = _tx(T.BUY, asset_id=5)

        assert _issue(charge, parent) is None

    def test_a_charge_that_is_not_a_charge_is_refused(self):
        issue = _issue(_tx(T.BUY), _tx(T.BUY))

        assert issue is not None
        message, code, params = issue
        assert code == _code("chargeNotACharge")
        assert params == {"type": "BUY"}
        assert isinstance(message, str) and message

    def test_a_missing_parent_is_refused(self):
        """Missing and not visible to the user are the same answer: the caller passes None for both."""
        issue = _issue(_tx(T.FEE), None, parent_id=424242)

        assert issue is not None
        assert issue[1] == _code("chargeParentNotFound")
        assert issue[2] == {"parentId": 424242}

    def test_a_parent_of_a_type_that_cannot_have_charges_is_refused(self):
        issue = _issue(_tx(T.FEE), _tx(T.CASH_TRANSFER))

        assert issue is not None
        assert issue[1] == _code("chargeParentTypeNotAllowed")
        assert issue[2] == {"type": "CASH_TRANSFER"}

    def test_a_charge_cannot_be_the_parent_of_a_charge(self):
        """No chains: FEE to FEE is refused with the parent-type code."""
        issue = _issue(_tx(T.FEE), _tx(T.FEE))

        assert issue is not None
        assert issue[1] == _code("chargeParentTypeNotAllowed")
        assert issue[2] == {"type": "FEE"}

    def test_another_broker_is_refused(self):
        issue = _issue(_tx(T.FEE, broker_id=1), _tx(T.DEPOSIT, broker_id=2))

        assert issue is not None
        assert issue[1] == _code("chargeBrokerMismatch")
        assert issue[2] == {"brokerId": 1, "parentBrokerId": 2}

    def test_a_charge_without_asset_on_a_parent_with_one_is_missing_its_asset(self):
        """D6b: no clean-up, the user clones the charge with the right asset."""
        issue = _issue(_tx(T.FEE, asset_id=None), _tx(T.BUY, asset_id=9))

        assert issue is not None
        assert issue[1] == _code("chargeAssetMissing")
        assert issue[2] == {"parentAssetId": 9}

    def test_another_asset_is_refused(self):
        issue = _issue(_tx(T.TAX, asset_id=3), _tx(T.SELL, asset_id=9))

        assert issue is not None
        assert issue[1] == _code("chargeAssetMismatch")
        assert issue[2] == {"assetId": 3, "parentAssetId": 9}

    def test_a_charge_with_an_asset_on_a_parent_without_one_is_a_mismatch(self):
        issue = _issue(_tx(T.FEE, asset_id=3), _tx(T.DEPOSIT, asset_id=None))

        assert issue is not None
        assert issue[1] == _code("chargeAssetMismatch")
        assert issue[2] == {"assetId": 3, "parentAssetId": None}

    def test_two_cash_rows_without_asset_are_valid(self):
        assert _issue(_tx(T.FEE, asset_id=None), _tx(T.DEPOSIT, asset_id=None)) is None

    def test_a_paired_charge_is_refused_with_the_charge_role(self):
        """Rule 8: a row that is already half of a pair cannot be a charge, whatever its type (two FEEs linked by API)."""
        issue = _issue(_tx(T.FEE, related_id=55), _tx(T.BUY))

        assert issue is not None
        assert issue[1] == _code("chargeRowIsPaired")
        assert issue[2] == {"role": "charge"}

    def test_a_paired_parent_is_refused_with_the_parent_role(self):
        """A DEPOSIT or WITHDRAWAL of an «intent» pair (or a pair stored before R0) cannot be a parent: the field decides."""
        issue = _issue(_tx(T.FEE), _tx(T.DEPOSIT, related_id=56))

        assert issue is not None
        assert issue[1] == _code("chargeRowIsPaired")
        assert issue[2] == {"role": "parent"}

    def test_row_is_paired_reads_the_field_not_the_type(self):
        paired = _helper("row_is_paired")

        assert paired(_tx(T.DEPOSIT, related_id=1)) is True
        assert paired(_tx(T.FEE, related_id=1)) is True
        assert paired(_tx(T.CASH_TRANSFER)) is False
        assert paired(_tx(T.DEPOSIT)) is False

    def test_the_order_of_the_rules_is_the_contract(self):
        """Several rules break at once: the first of the list answers."""
        # wrong broker AND wrong asset: the broker first
        issue = _issue(_tx(T.FEE, broker_id=1, asset_id=3), _tx(T.BUY, broker_id=2, asset_id=9))
        assert issue is not None and issue[1] == _code("chargeBrokerMismatch")

        # wrong parent type AND wrong broker: the parent type first
        issue = _issue(_tx(T.FEE, broker_id=1), _tx(T.CASH_TRANSFER, broker_id=2))
        assert issue is not None and issue[1] == _code("chargeParentTypeNotAllowed")

        # not a charge AND no parent: the type of the charge first
        issue = _issue(_tx(T.SELL), None)
        assert issue is not None and issue[1] == _code("chargeNotACharge")

        # paired charge AND wrong broker: the pair code, role charge, first
        issue = _issue(_tx(T.FEE, broker_id=1, related_id=5), _tx(T.BUY, broker_id=2))
        assert issue is not None and issue[1] == _code("chargeRowIsPaired") and issue[2] == {"role": "charge"}

        # not a charge AND paired: the type first
        issue = _issue(_tx(T.BUY, related_id=5), _tx(T.BUY))
        assert issue is not None and issue[1] == _code("chargeNotACharge")

        # paired charge AND no parent: the pair code first
        issue = _issue(_tx(T.FEE, related_id=5), None)
        assert issue is not None and issue[1] == _code("chargeRowIsPaired")

        # wrong parent type AND parent paired: the parent type first
        issue = _issue(_tx(T.FEE), _tx(T.CASH_TRANSFER, related_id=6))
        assert issue is not None and issue[1] == _code("chargeParentTypeNotAllowed")

        # paired parent AND wrong broker: the pair code, role parent, first
        issue = _issue(_tx(T.FEE, broker_id=1), _tx(T.DEPOSIT, broker_id=2, related_id=6))
        assert issue is not None and issue[1] == _code("chargeRowIsPaired") and issue[2] == {"role": "parent"}

        # asset missing AND (by construction) not a mismatch: the missing code, not the mismatch one
        issue = _issue(_tx(T.FEE, asset_id=None), _tx(T.BUY, asset_id=9))
        assert issue is not None and issue[1] == _code("chargeAssetMissing")


class TestWhatALinkMayDifferIn:
    """Guards: the date and the currency of a charge are free."""

    @pytest.mark.parametrize("charge_day", [date(2025, 3, 5), date(2025, 3, 3), date(2026, 1, 1)])
    def test_a_charge_on_another_day_is_valid(self, charge_day):
        """After the parent (a late fee) or before it: both accepted."""
        assert _issue(_tx(T.FEE, day=charge_day), _tx(T.DEPOSIT, day=DAY)) is None

    def test_a_charge_in_another_currency_is_valid(self):
        assert _issue(_tx(T.TAX, currency="USD"), _tx(T.DIVIDEND, currency="EUR")) is None


class TestEveryChargeOnEveryParent:
    """Guard (rule 1): FEE and TAX are accepted on each parent type of the table."""

    def test_every_charge_type_on_every_parent_type_is_valid(self):
        charges, parents = _type_lists()
        assert charges and parents

        for charge_type in sorted(charges):
            for parent_type in sorted(parents):
                issue = _issue(_tx(charge_type, asset_id=4), _tx(parent_type, asset_id=4))
                assert issue is None, f"{charge_type} on {parent_type}: {issue}"


# ============================================================================
# C2. RULE 6: A PARENT KEEPS A PARENT TYPE
# ============================================================================


class TestAParentWithChargesKeepsAParentType:
    """``charges_parent_type_issue``: a row with charges must still be a parent type after the change."""

    def _check(self, parent: Transaction, charge_ids):
        return _helper("charges_parent_type_issue")(parent, charge_ids)

    def test_a_deposit_with_charges_promoted_to_a_cash_transfer_is_refused(self):
        parent = _tx(T.DEPOSIT, tx_id=10)
        parent.type = T.CASH_TRANSFER

        issue = self._check(parent, [31, 12, 20])

        assert issue is not None
        message, code, params = issue
        assert code == _code("chargesBlockParentType")
        assert params == {"type": "CASH_TRANSFER", "chargeIds": [12, 20, 31]}
        assert isinstance(message, str) and message

    def test_no_charges_means_no_issue_for_any_type(self):
        for tx_type in T:
            assert self._check(_tx(tx_type), []) is None, tx_type

    def test_every_non_parent_type_with_charges_is_refused(self):
        _, parents = _type_lists()
        for tx_type in T:
            if tx_type in parents:
                continue
            issue = self._check(_tx(tx_type), [1])
            assert issue is not None and issue[1] == _code("chargesBlockParentType"), tx_type


class TestSwapsOfAParentStayValid:
    """Guards: the swap groups of type_metadata keep their charges (BUY/SELL, DEPOSIT/WITHDRAWAL, DIVIDEND/INTEREST)."""

    @pytest.mark.parametrize("before,after", [(T.BUY, T.SELL), (T.SELL, T.BUY), (T.DEPOSIT, T.WITHDRAWAL), (T.WITHDRAWAL, T.DEPOSIT), (T.DIVIDEND, T.INTEREST), (T.INTEREST, T.DIVIDEND)])
    def test_a_swap_inside_the_parent_types_is_valid(self, before, after):
        parent = _tx(before, tx_id=10)
        parent.type = after

        assert _helper("charges_parent_type_issue")(parent, [11, 12]) is None


# ============================================================================
# C3. THE READER
# ============================================================================


@pytest.fixture(scope="module")
def engine():
    """The app's async engine, on this lane's test database."""
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    """One session per test, rolled back at the end: what a test writes never reaches a neighbour."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()


class _Ledger:
    """One test's own rows: a broker with a uuid marker, parents and charges written through the ORM."""

    def __init__(self, session: AsyncSession, broker_id: int):
        self.session = session
        self.broker_id = broker_id

    async def add(self, tx_type: TransactionType, *, parent_id: int | None = None) -> int:
        row = Transaction(
            broker_id=self.broker_id,
            type=tx_type,
            date=DAY,
            quantity=Decimal("0"),
            amount=Decimal("-5") if tx_type in (T.FEE, T.TAX, T.WITHDRAWAL) else Decimal("5"),
            currency="EUR",
            parent_transaction_id=parent_id,
        )
        self.session.add(row)
        await self.session.flush()
        return row.id


@pytest_asyncio.fixture
async def ledger(session) -> _Ledger:
    now = utcnow()
    broker = Broker(
        name=f"charges {uuid.uuid4().hex}",
        description="linked charges: the broker of one test",
        allow_cash_overdraft=True,
        allow_asset_shorting=False,
        created_at=now,
        updated_at=now,
    )
    session.add(broker)
    await session.flush()
    return _Ledger(session, broker.id)


class TestTheReaderOfTheLinks:
    """``charge_ids_by_parent``: every parent asked is a key, ids ascending, nothing else."""

    @pytest.mark.asyncio
    async def test_it_answers_every_parent_asked_with_its_charges_sorted(self, ledger, session):
        reader = _helper("charge_ids_by_parent")
        with_two = await ledger.add(T.DEPOSIT)
        with_none = await ledger.add(T.BUY)
        not_asked = await ledger.add(T.SELL)
        # written out of order on purpose: ids ascend, so creation order is also id order, the sort is on the ids
        first = await ledger.add(T.FEE, parent_id=with_two)
        second = await ledger.add(T.TAX, parent_id=with_two)
        stranger = await ledger.add(T.FEE, parent_id=not_asked)

        result = await reader(session, [with_two, with_none])

        assert result[with_two] == sorted([first, second])
        assert result[with_none] == []
        assert set(result) == {with_two, with_none}
        assert stranger not in {i for ids in result.values() for i in ids}

    @pytest.mark.asyncio
    async def test_an_unknown_parent_id_is_a_key_with_an_empty_list(self, session):
        """An id that matches no row at all is asked, so it appears."""
        reader = _helper("charge_ids_by_parent")

        result = await reader(session, [987654321])

        assert result == {987654321: []}

    @pytest.mark.asyncio
    async def test_a_generator_and_repeated_ids_work(self, ledger, session):
        reader = _helper("charge_ids_by_parent")
        parent = await ledger.add(T.INTEREST)
        charge = await ledger.add(T.FEE, parent_id=parent)

        result = await reader(session, (i for i in [parent, parent]))

        assert result == {parent: [charge]}

    @pytest.mark.asyncio
    async def test_an_empty_input_is_an_empty_answer_without_a_query(self):
        """No query: a session that would fail on use proves it."""
        reader = _helper("charge_ids_by_parent")

        class _NoQuerySession:
            async def execute(self, *args, **kwargs):  # pragma: no cover - reaching it is the failure
                raise AssertionError("an empty input must not query")

        assert await reader(_NoQuerySession(), []) == {}
        assert await reader(_NoQuerySession(), iter(())) == {}

    @pytest.mark.asyncio
    async def test_the_statement_is_answered_through_the_partial_index(self, ledger, session):
        """EXPLAIN QUERY PLAN of the very statement the function runs names ``idx_transactions_parent``."""
        statement_for = _helper("charge_ids_by_parent_statement")
        parent = await ledger.add(T.DEPOSIT)
        await ledger.add(T.FEE, parent_id=parent)
        statement = statement_for([parent])
        sql = str(statement.compile(compile_kwargs={"literal_binds": True}, dialect=session.bind.dialect))

        rows = (await session.execute(text(f"EXPLAIN QUERY PLAN {sql}"))).all()

        plan = " | ".join(str(row[-1]) for row in rows)
        assert "idx_transactions_parent" in plan, f"the plan does not use the index: {plan}"
