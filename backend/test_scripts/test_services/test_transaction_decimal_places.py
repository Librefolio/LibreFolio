"""
C-97a — how many decimal places a transaction keeps, and where a batch refuses more (workstream W, GitHub issue #43:
crypto users need more decimal places).

Today. ``Transaction.quantity`` is ``Numeric(18, 6)``: SQLite stores the double the ORM binds, and SQLAlchemy rounds it
to 6 decimals when it reads it back, so a BUY of 0.12345678 BTC reads 0.123457, and nothing says so. Nothing limits the
decimal places of a value on input either: ``TXCreateItem`` and ``TXUpdateItem`` accept any, the batch saves them, the
read rounds them. The balances are SQL sums of those doubles, read back at 6 decimals too.

The contract (the developer's decisions, 16/10; D5 and D6 the coordinator's, 16/10 17:05):

1. A quantity keeps up to 10 decimal places and reads back exactly (``RealDecimal(22, 10)``: the shortest decimal of the
   stored double, at most 15 significant digits, padded to 6 decimals when it has fewer, so ``10`` still reads
   ``10.000000``). A cash amount stays at 6. The manual cost basis is a PER-UNIT price (``financial_math/average_cost.py``
   multiplies it by the quantity), so its column becomes ``RealDecimal(24, 12)`` and it keeps up to 12 decimal places
   (D5): a PEPE bought at 0.0000034573 EUR a unit keeps that cost.
2. Over the limit the batch refuses — it never rounds — at confirmation, ``POST /transactions/validate`` and ``/commit``
   (``execute_batch``), and not at BRIM parse (decision D2; a value a BRIM plugin computes is rounded by the plugin,
   D6, outside this file). The stage ``check_decimal_limits``, right after ``parse_inputs``, adds for each create and
   each update one issue per field over its limit, the scale read from the model — ``quantity`` (10), ``cash.amount``
   (6), ``cost_basis_override`` (its amount, 12): ``decimalPlacesExceeded`` with ``{"max": 10 | 6 | 12}`` when
   the decimals, trailing zeros not counted, exceed the field's max, otherwise ``significantDigitsExceeded`` with
   ``{"max": 15}`` past 15 significant digits (decision D1). On the row's ``operation`` and ``index``, ``ref_id`` the
   updated id (None for a create), with an English ``error`` that names the field. The batch is not committed, and the
   row stays in it, so a linked pair is not broken by the refusal. Both codes are members of ``TXValidationCode``, so
   ``GET /transactions/types`` lists them in ``validation_codes``.
3. The balances are summed in Python with exact ``Decimal`` (``financial_math``'s ``position_quantities`` and
   ``native_balances``): two BUYs of 99999.1234567891 hold exactly 199998.2469135782 in ``get_asset_holdings`` and in
   ``get_balances_at_end_of`` — today 199998.246914, and 199998.2469135780 with the new column under an SQL sum. The
   cash balances keep today's results.
4. The asset list reads an asset as held where the exact sum of its quantities on a broker exceeds
   ``QUANTITY_DUST_THRESHOLD``.

Reds — fail today, pass once the contract holds:

- ``TestQuantitiesKeepTenDecimals``: a BUY, a SELL and an ADJUSTMENT +q of 0.12345678 and of 0.1234567891 units created
  through the batch, and a quantity updated to 0.1234567891, read back from the database as sent (today 0.123457; the
  batch commits, which each test checks first, so the red is the read-back);
- ``TestOverTheLimitIsRefusedAtConfirmation``: a create over a limit is refused on its own row, on ``/validate`` and on
  ``/commit``, with the exact ``(operation, index, ref_id, code, field, params)``; an update too, ``ref_id`` its id;
  nothing is written or changed (today the batch commits and the read rounds). A linked pair one leg of which is over a
  limit is refused on that leg alone, both legs still in the batch, no broken pair reported — a RED, not a guard: before
  ``check_decimal_limits`` the pair committed whole, with no issue at all. A cost basis is over the limit at 13 decimals,
  ``{"max": 12}`` (D5): red until its column is ``RealDecimal(24, 12)``, the check reading 6 from today's model;
- ``TestAPerUnitCostKeepsTwelveDecimals`` (D5): a received TRANSFER and an ADJUSTMENT +1 at a manual per-unit cost of
  0.0000034573 EUR are saved, and the cost reads back exactly (today refused with ``{"max": 6}``; before the check,
  saved and read back 0.000003);
- ``TestBalancesAreSummedExactly.test_two_buys_of_ten_decimals_sum_exactly`` (today 199998.246914);
- ``TestTheCodesAreListed``: ``TXValidationCode`` and ``GET /transactions/types``'s ``validation_codes`` carry both codes.

Guards — green today, and the cure must keep them green:

- ``TestWhatTheLimitLeavesAlone``: trailing zeros are not counted (1.50000000000000 units, a cash amount of
  -150.1000000, a cost basis of 1.5000000000000 commit, and read back as their value); a whole and a 6-decimal quantity
  read back in today's form, ``10.000000`` and ``1.234567``;
- ``TestBalancesAreSummedExactly``: the cash at the end of a day keeps today's results, and the quantities their date
  bounds and exclusions (``as_of``, ``exclude_tx_ids``);
- ``TestTheAssetListReadsHoldingsExactly``: a position bought 0.1 + 0.2 and sold 0.3 is not held, one sold 0.2999 is;
- ``TestBrimParseDoesNotRefuse`` (D2): a BRIM row over a limit is not refused at parse (``BRIMProvider._create_transaction``,
  the constructor every plugin calls): the item is returned with its values as read, and no parse issue is recorded.
  The rounding of D6 is the plugin's, on the values it computes (``round_computed_value``), not this constructor's.

Derived — read from the contract's general rule, not in the brief's list; drop them if the rule was meant narrower: a
quantity over both limits gets ``decimalPlacesExceeded`` alone (the "otherwise"); a cash amount past 15 significant
digits gets ``significantDigitsExceeded``; a row over the limit on two fields gets one issue per field.

Ownership. Every test builds its own asset and brokers under a unique marker, in one session rolled back at the end. A
batch runs as the endpoint runs it, its transaction included (``_run_as_the_endpoint``), so a refused batch leaves the
database as it found it, and nothing reaches the lane's database.

Run: ``./dev.py test services transaction-decimal-places`` (the action ``services_transaction_decimal_places``).
"""

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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetType, Broker, Transaction, TransactionType
from backend.app.db.session import get_async_engine
from backend.app.schemas.assets.assets import FAAinfoFiltersRequest
from backend.app.schemas.brim import BRIMParseOutput
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions.batch import TXBatchResponse, TXValidationCode, TXValidationIssue
from backend.app.schemas.transactions.type_metadata import EVENT_TYPE_METADATA, TX_TYPE_METADATA, TXTypesResponse
from backend.app.services.assets.crud import AssetCRUDService
from backend.app.services.brim.brim_provider import BRIMProvider
from backend.app.services.platform.data_quality_thresholds import QUANTITY_DUST_THRESHOLD
from backend.app.services.transactions.transaction_service import TransactionService
from backend.app.utils.datetime_utils import utcnow

EUR = "EUR"
USD = "USD"
# The days of a test: the rows written before the batch, the batch's, and the day after the one a balance is read at.
SEED_DAY = date(2025, 3, 3)
DAY = date(2025, 3, 10)
NEXT_DAY = DAY + timedelta(days=1)

# The two codes of C-97a, compared as strings: TXValidationCode has no member for them yet, and a red must fail when it
# runs, not when it is collected.
DECIMAL_PLACES_EXCEEDED = "decimalPlacesExceeded"
SIGNIFICANT_DIGITS_EXCEEDED = "significantDigitsExceeded"
DECIMAL_CODES = (DECIMAL_PLACES_EXCEEDED, SIGNIFICANT_DIGITS_EXCEEDED)
# The params of a refusal: 10 decimals for a quantity, 6 for a cash amount, 12 for a per-unit cost basis (D5), 15
# significant digits for any of them.
QUANTITY_MAX = {"max": 10}
CASH_MAX = {"max": 6}
COST_MAX = {"max": 12}
DIGITS_MAX = {"max": 15}
# A per-unit cost basis over D5's limit on its decimals alone: 13 decimals, 13 significant digits.
COST_13_DECIMALS = "0.1234567890123"
# A PEPE's per-unit cost: 10 decimals, within D5's 12, which a 6-decimal column reads 0.000003 and refuses.
PEPE_UNIT_COST = "0.0000034573"

ENDPOINTS = ("validate", "commit")
# What a test reads back, column by column: through each column's type, as the user finds the row once the request is over.
STORED_COLUMNS = (Transaction.quantity, Transaction.amount, Transaction.currency, Transaction.cost_basis_override, Transaction.cost_basis_currency, Transaction.description)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def engine():
    """The app's async engine, on this lane's test database."""
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    """One session per test, rolled back at the end: nothing a test writes reaches the lane's database."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()


@dataclass(frozen=True)
class World:
    """One test's own ground, by id — a rolled-back savepoint expires the objects it touched, and an expired attribute
    would load lazily outside the event loop: a crypto asset, the broker the tests buy on (``main``) and the broker a
    TRANSFER reaches (``other``). Both may overdraw their cash (a BUY spends cash no DEPOSIT brought) and may not go
    short, as a broker does by default, so every batch replays its balances."""

    session: AsyncSession
    marker: str
    asset_id: int
    main_id: int
    other_id: int

    @property
    def batch_description(self) -> str:
        """The description of every row a batch of this test sends: what finds those rows again, or proves them absent."""
        return f"{self.marker} batch"


@pytest_asyncio.fixture
async def world(session) -> World:
    """The test's asset and brokers, under a marker of its own."""
    marker = f"C97a-decimals {uuid.uuid4().hex}"
    now = utcnow()
    asset = Asset(display_name=f"{marker} coin", asset_type=AssetType.CRYPTO, currency=EUR, created_at=now, updated_at=now)
    main = Broker(name=f"{marker} main", description="C-97a: the broker the tests buy on", allow_cash_overdraft=True, allow_asset_shorting=False, created_at=now, updated_at=now)
    other = Broker(name=f"{marker} other", description="C-97a: the broker a TRANSFER reaches", allow_cash_overdraft=True, allow_asset_shorting=False, created_at=now, updated_at=now)
    session.add_all([asset, main, other])
    await session.flush()
    return World(session=session, marker=marker, asset_id=asset.id, main_id=main.id, other_id=other.id)


# ============================================================================
# HELPERS
# ============================================================================


async def _insert(world: World, **columns) -> int:
    """A row written with the ORM, without the batch and its checks; its id."""
    now = utcnow()
    row = Transaction(description=f"{world.marker} seed", created_at=now, updated_at=now, **columns)
    world.session.add(row)
    await world.session.flush()
    return row.id


async def _seed_position(world: World, tx_type: TransactionType, quantity: str, *, day: date = SEED_DAY, amount: str = "0", cost: str | None = None, asset_id: int | None = None) -> int:
    """A row of ``quantity`` units of the test's asset (or of ``asset_id``) on ``main``, moving ``amount`` EUR of cash,
    with a manual cost basis of ``cost`` EUR when given."""
    return await _insert(
        world,
        broker_id=world.main_id,
        asset_id=asset_id or world.asset_id,
        type=tx_type,
        date=day,
        quantity=Decimal(quantity),
        amount=Decimal(amount),
        currency=EUR if Decimal(amount) != 0 else None,
        cost_basis_override=Decimal(cost) if cost is not None else None,
        cost_basis_currency=EUR if cost is not None else None,
    )


async def _seed_cash(world: World, tx_type: TransactionType, amount: str, currency: str, *, day: date) -> int:
    """A cash row on ``main``, without an asset."""
    return await _insert(world, broker_id=world.main_id, asset_id=None, type=tx_type, date=day, quantity=Decimal("0"), amount=Decimal(amount), currency=currency)


async def _new_asset(world: World, label: str) -> int:
    """One more asset of the test, under its marker."""
    now = utcnow()
    asset = Asset(display_name=f"{world.marker} {label}", asset_type=AssetType.CRYPTO, currency=EUR, created_at=now, updated_at=now)
    world.session.add(asset)
    await world.session.flush()
    return asset.id


def _row(world: World, tx_type: str, quantity: str, *, cash: str | None = None, cost: str | None = None, broker_id: int | None = None) -> dict:
    """A create as the app sends it (``TXCreateItem``), every decimal a string: of the test's asset on ``DAY``, on ``main``
    unless ``broker_id`` says otherwise, moving ``cash`` EUR, with a manual cost basis of ``cost`` EUR."""
    row = {"broker_id": broker_id or world.main_id, "asset_id": world.asset_id, "type": tx_type, "date": DAY.isoformat(), "quantity": quantity, "description": world.batch_description}
    if cash is not None:
        row["cash"] = {"code": EUR, "amount": cash}
    if cost is not None:
        row["cost_basis_override"] = {"code": EUR, "amount": cost}
    return row


async def _run_as_the_endpoint(world: World, *, creates: list[dict] | None = None, updates: list[dict] | None = None, endpoint: str = "commit") -> TXBatchResponse:
    """The batch as ``POST /transactions/<endpoint>`` runs it, its transaction included: ``/commit`` keeps it when the
    service answers committed and rolls it back otherwise, ``/validate`` always rolls it back (``api/v1/transactions.py``);
    no user, so no access check.

    ``execute_batch`` applies and flushes the rows it keeps, a refused one included, and leaves the commit or the
    rollback to its caller. A savepoint stands in for the request's transaction, as in
    ``test_transaction_cost_basis_rule.py``: the rows the test wrote before it survive its rollback (their flush opened
    SQLite's transaction, so the savepoint nests in it), and the session fixture still rolls everything back.
    """
    savepoint = await world.session.begin_nested()
    response = await TransactionService(world.session).execute_batch(creates_raw=creates or [], updates_raw=updates or [], deletes=[], commit=endpoint == "commit")
    if endpoint == "commit" and response.committed:
        await savepoint.commit()
    else:
        await savepoint.rollback()
    return response


async def _stored(world: World, ids) -> dict[int, dict]:
    """The rows ``ids`` as the database holds them, by id, read column by column (``STORED_COLUMNS``). Never through the
    ORM objects, which a rolled-back savepoint leaves expired."""
    statement = select(Transaction.id, *STORED_COLUMNS).where(Transaction.id.in_(list(ids)))
    return {row["id"]: {column: value for column, value in row.items() if column != "id"} for row in (await world.session.execute(statement)).mappings()}


async def _batch_rows(world: World) -> list[int]:
    """The ids of the rows this test's batches sent that the database holds, found by their description."""
    statement = select(Transaction.id).where(Transaction.description == world.batch_description)
    return list((await world.session.execute(statement)).scalars())


def _created_ids(response: TXBatchResponse) -> dict[int, int]:
    """The id each create of the batch got, by its index."""
    return {result.index: result.ids[0] for result in response.results if result.operation == "create" and result.ids}


def _in_batch(response: TXBatchResponse) -> set[tuple[str, int]]:
    """The ``(operation, index)`` of every row the batch applied and reports: the rows it kept."""
    return {(result.operation, result.index) for result in response.results}


def _issue_order(issue: tuple) -> tuple:
    """A fixed order for ``(operation, index, ref_id, code, field, params)`` issues: their order is not the subject."""
    operation, index, ref_id, code, field, _params = issue
    return (operation, index, ref_id or 0, code or "", field or "")


def _decimal_issues(response: TXBatchResponse) -> list[tuple]:
    """The batch's decimal refusals, as ``(operation, index, ref_id, code, field, params)``, sorted."""
    return sorted(((issue.operation, issue.index, issue.ref_id, issue.code, issue.field, issue.params) for issue in response.issues if issue.code in DECIMAL_CODES), key=_issue_order)


def _other_issues(response: TXBatchResponse) -> list[TXValidationIssue]:
    """Every issue of the batch that is not a decimal refusal."""
    return [issue for issue in response.issues if issue.code not in DECIMAL_CODES]


def _render(issues: list[TXValidationIssue]) -> str:
    """The issues, for a failure message."""
    return "; ".join(f"{issue.operation}[{issue.index}] ref_id={issue.ref_id} code={issue.code} field={issue.field} params={issue.params} error={issue.error!r}" for issue in issues) or "none"


def _words(text: str) -> str:
    """``text`` as lower-case words: ``cash.amount`` and «Cash amount» read alike."""
    return " ".join(text.lower().replace(".", " ").replace("_", " ").split())


def _assert_errors_name_their_fields(response: TXBatchResponse) -> None:
    """Each decimal refusal carries an English ``error`` that names its field, as sent (``cash.amount``) or in words."""
    for issue in response.issues:
        if issue.code in DECIMAL_CODES:
            assert issue.error and _words(issue.field or "") in _words(issue.error), f"C-97a: the error of {issue.code} on {issue.operation}[{issue.index}] must be an English text naming its field {issue.field!r}; it reads {issue.error!r}"


# ============================================================================
# RED — A QUANTITY KEEPS 10 DECIMALS
# ============================================================================

SENT_QUANTITIES = ("0.12345678", "0.1234567891")
ROUND_TRIP_SHAPES = ("buy", "sell", "adjustment_in")


def _round_trip_batch(world: World, shape: str, quantity: str) -> tuple[list[dict], int]:
    """The creates that write a ``shape`` row of ``quantity`` units (that many leave on a SELL), and that row's index.

    The SELL sells units a BUY of the same batch and day brings, sent before it: ``main`` may not go short. The ADJUSTMENT
    adds units, so it carries the cost basis it needs.
    """
    if shape == "buy":
        return [_row(world, "BUY", quantity, cash="-10")], 0
    if shape == "sell":
        return [_row(world, "BUY", "1", cash="-100"), _row(world, "SELL", f"-{quantity}", cash="10")], 1
    if shape == "adjustment_in":
        return [_row(world, "ADJUSTMENT", quantity, cost="100")], 0
    raise ValueError(f"unknown shape {shape!r}")


class TestQuantitiesKeepTenDecimals:
    """RED: a quantity of up to 10 decimals reads back from the database as it was sent.

    Today ``Numeric(18, 6)`` rounds it to 6 decimals when it is read: 0.12345678 reads 0.123457, 0.1234567891 too. The
    batch commits — each test checks that first — so the red is the read-back alone.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("quantity", SENT_QUANTITIES)
    @pytest.mark.parametrize("shape", ROUND_TRIP_SHAPES)
    async def test_created_quantity_reads_back_as_sent(self, world, shape, quantity):
        """RED: committed through ``/commit``, and the row's quantity reads back equal to what the batch received."""
        creates, subject_index = _round_trip_batch(world, shape, quantity)
        sent = Decimal(creates[subject_index]["quantity"])

        response = await _run_as_the_endpoint(world, creates=creates)

        assert response.committed is True and response.issues == [], f"scaffold: a {shape} of {sent} units, within the limit of 10 decimals, was refused: {_render(response.issues)}"
        subject_id = _created_ids(response)[subject_index]
        stored = (await _stored(world, [subject_id]))[subject_id]["quantity"]
        assert stored == sent, f"C-97a: a {shape} of {sent} units (id={subject_id}) reads back {stored} from the database; a quantity keeps up to 10 decimal places and reads back exactly"

    @pytest.mark.asyncio
    async def test_updated_quantity_reads_back_as_sent(self, world):
        """RED: an update of a stored BUY's quantity to 0.1234567891 commits, and the row reads it back."""
        subject_id = await _seed_position(world, TransactionType.BUY, "1", amount="-100")
        sent = Decimal("0.1234567891")

        response = await _run_as_the_endpoint(world, updates=[{"id": subject_id, "quantity": str(sent)}])

        assert response.committed is True and response.issues == [], f"scaffold: an update of BUY id={subject_id} to {sent} units, within the limit of 10 decimals, was refused: {_render(response.issues)}"
        stored = (await _stored(world, [subject_id]))[subject_id]["quantity"]
        assert stored == sent, f"C-97a: BUY id={subject_id} updated to {sent} units reads back {stored} from the database; a quantity keeps up to 10 decimal places and reads back exactly"


# ============================================================================
# GUARDS — WHAT THE LIMIT LEAVES ALONE
# ============================================================================

# A create within the limits once its trailing zeros are dropped, though not before; the column it is read back from, and
# the value it must read back as.
TRAILING_ZEROS = [
    pytest.param({"tx_type": "BUY", "quantity": "1.50000000000000", "cash": "-150"}, "quantity", Decimal("1.5"), id="quantity-1.50000000000000"),
    pytest.param({"tx_type": "BUY", "quantity": "1", "cash": "-150.1000000"}, "amount", Decimal("-150.1"), id="cash-amount--150.1000000"),
    pytest.param({"tx_type": "ADJUSTMENT", "quantity": "1", "cost": "1.5000000000000"}, "cost_basis_override", Decimal("1.5"), id="cost-basis-1.5000000000000"),
]


class TestWhatTheLimitLeavesAlone:
    """Guards, green today and after C-97a: what the refusal must not catch, and the form a read keeps."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("subject", "column", "value"), TRAILING_ZEROS)
    async def test_trailing_zeros_are_not_counted(self, world, subject, column, value):
        """Guard: 1.50000000000000 units (14 decimals, 13 of them trailing zeros; 15 digits in all, so within D1 however
        they are counted), a cash amount of -150.1000000 (7 decimals, 6 of them zeros, over 6 only if they count) and a
        per-unit cost basis of 1.5000000000000 (13 decimals, 12 of them zeros: over D5's 12 only if they count; 14 digits
        in all) commit, and read back as their value. A cure that counts the trailing zeros refuses them."""
        response = await _run_as_the_endpoint(world, creates=[_row(world, **subject)])

        assert response.committed is True and response.issues == [], f"C-97a: trailing zeros are not decimal places, so {subject} is within the limits and must commit; it was refused: {_render(response.issues)}"
        tx_id = _created_ids(response)[0]
        stored = (await _stored(world, [tx_id]))[tx_id][column]
        assert stored == value, f"The create {subject} (id={tx_id}) reads back {column}={stored}, not {value}"

    @pytest.mark.asyncio
    async def test_whole_and_six_decimal_quantities_read_back_in_todays_form(self, world):
        """Guard: a quantity of 10 reads back ``10.000000`` and one of 1.234567 ``1.234567``, as ``Numeric(18, 6)`` reads
        them today; ``RealDecimal`` pads to 6 decimals a value that has fewer."""
        creates = [_row(world, "BUY", "10", cash="-100"), _row(world, "BUY", "1.234567", cash="-10")]

        response = await _run_as_the_endpoint(world, creates=creates)

        assert response.committed is True and response.issues == [], f"scaffold: two BUYs within the limits were refused: {_render(response.issues)}"
        created = _created_ids(response)
        stored = await _stored(world, created.values())
        forms = {creates[index]["quantity"]: str(stored[tx_id]["quantity"]) for index, tx_id in created.items()}
        assert forms == {"10": "10.000000", "1.234567": "1.234567"}, f"A quantity of 6 decimals or fewer reads back in today's form, padded to 6 decimals; sent → read: {forms}"


# ============================================================================
# RED — OVER THE LIMIT, REFUSED AT CONFIRMATION
# ============================================================================

# The create a refusal is about — sent at index 1, behind a valid BUY, so the refusal's index is its row's and not a
# default — and the decimal issues it gets, as (code, field, params). The three "derived" cases read the contract's
# general rule (decimals first, D1 on every field, one issue per field); they are not in the brief's list.
CREATE_REFUSALS = [
    pytest.param({"tx_type": "BUY", "quantity": "0.12345678901", "cash": "-10"}, [(DECIMAL_PLACES_EXCEEDED, "quantity", QUANTITY_MAX)], id="quantity-11-decimals"),
    pytest.param({"tx_type": "BUY", "quantity": "1234567890123.456", "cash": "-10"}, [(SIGNIFICANT_DIGITS_EXCEEDED, "quantity", DIGITS_MAX)], id="quantity-16-significant-digits"),
    pytest.param({"tx_type": "BUY", "quantity": "1", "cash": "-100.1234567"}, [(DECIMAL_PLACES_EXCEEDED, "cash.amount", CASH_MAX)], id="cash-amount-7-decimals"),
    pytest.param({"tx_type": "ADJUSTMENT", "quantity": "1", "cost": COST_13_DECIMALS}, [(DECIMAL_PLACES_EXCEEDED, "cost_basis_override", COST_MAX)], id="adjustment-in-cost-basis-13-decimals"),
    pytest.param({"tx_type": "BUY", "quantity": "12345678.123456789012", "cash": "-10"}, [(DECIMAL_PLACES_EXCEEDED, "quantity", QUANTITY_MAX)], id="derived-quantity-over-both-limits-decimals-first"),
    pytest.param({"tx_type": "BUY", "quantity": "1", "cash": "-12345678901234.56"}, [(SIGNIFICANT_DIGITS_EXCEEDED, "cash.amount", DIGITS_MAX)], id="derived-cash-amount-16-significant-digits"),
    pytest.param({"tx_type": "BUY", "quantity": "0.12345678901", "cash": "-100.1234567"}, [(DECIMAL_PLACES_EXCEEDED, "cash.amount", CASH_MAX), (DECIMAL_PLACES_EXCEEDED, "quantity", QUANTITY_MAX)], id="derived-one-issue-per-field"),
]

# The stored row an update over a limit edits (a BUY of 1 for 100 EUR, or an ADJUSTMENT +1 with its cost basis of 100
# EUR), the update's change, and the field and params of its refusal.
UPDATE_REFUSALS = [
    pytest.param("buy", {"quantity": "0.12345678901"}, "quantity", QUANTITY_MAX, id="quantity-11-decimals"),
    pytest.param("buy", {"cash": {"code": EUR, "amount": "-100.1234567"}}, "cash.amount", CASH_MAX, id="cash-amount-7-decimals"),
    pytest.param("adjustment_in", {"cost_basis_override": {"code": EUR, "amount": COST_13_DECIMALS}}, "cost_basis_override", COST_MAX, id="cost-basis-13-decimals"),
]

PAIR_SHAPES = ("transfer-received-cost-basis", "fx-conversion-cash-amount")


class TestOverTheLimitIsRefusedAtConfirmation:
    """RED: a value over its field's limit is refused at confirmation — never rounded — on its own row.

    Before ``check_decimal_limits`` nothing checked: the batch committed, and the read rounded the value. ``/validate``
    and ``/commit`` run the same ``execute_batch``, so a create is refused on both; the updates and the pairs run as
    ``/commit``. Each test asserts the refusal first, so a red names what is missing. A per-unit cost basis is checked
    against D5's 12 decimals, read from the model: red until its column is ``RealDecimal(24, 12)`` (the check reads 6
    from today's ``Numeric(18, 6)`` and answers ``{"max": 6}``).
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    @pytest.mark.parametrize(("subject", "expected"), CREATE_REFUSALS)
    async def test_create_over_the_limit_is_refused_on_its_row(self, world, subject, expected, endpoint):
        """RED: exactly the expected issues on create 1 (``ref_id`` None), nothing else; not committed; the row still in
        the batch; no row of the batch in the database."""
        barrier_id = await _seed_position(world, TransactionType.BUY, "1", amount="-100")
        creates = [_row(world, "BUY", "1", cash="-100"), _row(world, **subject)]

        response = await _run_as_the_endpoint(world, creates=creates, endpoint=endpoint)

        refusals = sorted((("create", 1, None, code, field, params) for code, field, params in expected), key=_issue_order)
        assert _decimal_issues(response) == refusals, f"C-97a, /{endpoint}: the create {subject} must be refused on its own row with exactly {refusals}; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        assert _other_issues(response) == [], f"C-97a, /{endpoint}: only the decimals may refuse this batch: {_render(_other_issues(response))}"
        assert response.committed is False, f"C-97a: /{endpoint} refused the batch, yet answered committed"
        _assert_errors_name_their_fields(response)
        assert ("create", 1) in _in_batch(response), f"C-97a: the refused row stays in the batch (applied and reported), so a pair it belongs to is not broken; the results are {response.results}"
        assert barrier_id in await _stored(world, [barrier_id]), f"scaffold: the read-back no longer sees row id={barrier_id}, written before the batch, so finding no row of the batch would prove nothing"
        written = await _batch_rows(world)
        assert written == [], f"C-97a: /{endpoint} refused the batch, yet the database holds its rows {written}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("stored_shape", "change", "field", "params"), UPDATE_REFUSALS)
    async def test_update_over_the_limit_is_refused_on_its_row(self, world, stored_shape, change, field, params):
        """RED: an update over a limit, sent at index 1 behind a valid notes edit of another row, is refused on update 1
        with ``ref_id`` its id; not committed; both rows read back as they were stored."""
        neighbour_id = await _seed_position(world, TransactionType.BUY, "1", amount="-100")
        if stored_shape == "buy":
            subject_id = await _seed_position(world, TransactionType.BUY, "1", amount="-100")
        else:
            subject_id = await _seed_position(world, TransactionType.ADJUSTMENT, "1", cost="100")
        before = await _stored(world, [neighbour_id, subject_id])
        updates = [{"id": neighbour_id, "description": f"{world.marker} neighbour edited"}, {"id": subject_id, **change}]

        response = await _run_as_the_endpoint(world, updates=updates)

        refusal = ("update", 1, subject_id, DECIMAL_PLACES_EXCEEDED, field, params)
        assert _decimal_issues(response) == [refusal], f"C-97a: the update {change} of id={subject_id} must be refused on its own row with exactly {refusal}; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        assert _other_issues(response) == [], f"C-97a: only the decimals may refuse this batch: {_render(_other_issues(response))}"
        assert response.committed is False, "C-97a: /commit refused the batch, yet answered committed"
        _assert_errors_name_their_fields(response)
        assert ("update", 1) in _in_batch(response), f"C-97a: the refused update stays in the batch (applied and reported); the results are {response.results}"
        after = await _stored(world, [neighbour_id, subject_id])
        assert after == before, f"C-97a: the batch was refused, yet the stored rows changed: before {before}, after {after}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("pair", PAIR_SHAPES)
    async def test_pair_with_one_leg_over_the_limit_is_refused_on_that_leg_alone(self, world, pair):
        """RED — not a guard: before ``check_decimal_limits`` the pair committed whole, with no issue at all; the cost
        basis case stays red until D5's column (13 decimals, ``{"max": 12}``).

        A linked pair one leg of which is over a limit — the received TRANSFER's cost basis, or one side of an exchange —
        gets the decimal issue on that leg (create 1) and nothing else: not also a broken pair (``linkUuidPairCount``),
        which a cure that drops the refused row before the link stage would add, nor a missing cost basis. Both legs stay
        in the batch; nothing is written.
        """
        link_uuid = str(uuid.uuid4())
        if pair == "transfer-received-cost-basis":
            # The units the giving leg moves: main may not go short.
            await _seed_position(world, TransactionType.BUY, "1", amount="-100")
            legs = [{**_row(world, "TRANSFER", "-1"), "link_uuid": link_uuid}, {**_row(world, "TRANSFER", "1", cost=COST_13_DECIMALS, broker_id=world.other_id), "link_uuid": link_uuid}]
            refusal = ("create", 1, None, DECIMAL_PLACES_EXCEEDED, "cost_basis_override", COST_MAX)
        else:
            giving = {"broker_id": world.main_id, "type": "FX_CONVERSION", "date": DAY.isoformat(), "quantity": "0", "cash": {"code": EUR, "amount": "-100"}, "link_uuid": link_uuid, "description": world.batch_description}
            legs = [giving, {**giving, "cash": {"code": USD, "amount": "107.1234567"}}]
            refusal = ("create", 1, None, DECIMAL_PLACES_EXCEEDED, "cash.amount", CASH_MAX)

        response = await _run_as_the_endpoint(world, creates=legs)

        assert _decimal_issues(response) == [refusal], f"C-97a: a {pair} pair must be refused on its leg over the limit with exactly {refusal}; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        assert _other_issues(response) == [], f"C-97a: the refusal of one leg must not also report the pair broken (linkUuidPairCount) or anything else: {_render(_other_issues(response))}"
        assert response.committed is False, "C-97a: /commit refused the pair, yet answered committed"
        assert {("create", 0), ("create", 1)} <= _in_batch(response), f"C-97a: both legs stay in the batch, the refused one included; the results are {response.results}"
        written = await _batch_rows(world)
        assert written == [], f"C-97a: the pair was refused, yet the database holds its rows {written}"


# ============================================================================
# RED — D5: A PER-UNIT COST KEEPS 12 DECIMALS
# ============================================================================

PER_UNIT_COST_SHAPES = ("transfer_received", "adjustment_in")


def _per_unit_cost_batch(world: World, shape: str, cost: str) -> tuple[list[dict], int]:
    """The creates that write a ``shape`` row receiving one unit at a manual per-unit cost of ``cost`` EUR, and that
    row's index: the receiving leg of a TRANSFER ``main`` → ``other`` (the caller seeds the unit ``main`` gives), or an
    ADJUSTMENT +1 on ``main``."""
    if shape == "transfer_received":
        link_uuid = str(uuid.uuid4())
        return [{**_row(world, "TRANSFER", "-1"), "link_uuid": link_uuid}, {**_row(world, "TRANSFER", "1", cost=cost, broker_id=world.other_id), "link_uuid": link_uuid}], 1
    if shape == "adjustment_in":
        return [_row(world, "ADJUSTMENT", "1", cost=cost)], 0
    raise ValueError(f"unknown shape {shape!r}")


class TestAPerUnitCostKeepsTwelveDecimals:
    """RED (decision D5): ``cost_basis_override`` is a PER-UNIT price — ``financial_math/average_cost.py`` multiplies it
    by the quantity — so it keeps up to 12 decimal places (``RealDecimal(24, 12)``) and reads back exactly.

    Today the column is ``Numeric(18, 6)`` and ``check_decimal_limits`` reads its scale from the model, so a PEPE's
    0.0000034573 EUR a unit — 10 decimals — is refused with ``decimalPlacesExceeded`` ``{"max": 6}`` (before the check
    it was saved, and read back 0.000003: a cost of 3 EUR a million units instead of 3.4573).
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", PER_UNIT_COST_SHAPES)
    async def test_pepe_unit_cost_is_saved_and_reads_back_exactly(self, world, shape):
        """RED: committed through ``/commit`` with no issue, and the receiving row's cost basis reads back exactly
        0.0000034573 EUR from the database."""
        if shape == "transfer_received":
            # The unit the giving leg moves: main may not go short.
            await _seed_position(world, TransactionType.BUY, "1", amount="-100")
        creates, subject_index = _per_unit_cost_batch(world, shape, PEPE_UNIT_COST)

        response = await _run_as_the_endpoint(world, creates=creates)

        assert response.committed is True and response.issues == [], f"D5: a per-unit cost of {PEPE_UNIT_COST} EUR has 10 decimals, within the 12 a per-unit cost keeps, yet the {shape} was refused: {_render(response.issues)}"
        subject_id = _created_ids(response)[subject_index]
        stored = (await _stored(world, [subject_id]))[subject_id]
        cost = (stored["cost_basis_override"], stored["cost_basis_currency"])
        assert cost == (Decimal(PEPE_UNIT_COST), EUR), f"D5: the {shape} id={subject_id} was saved at {PEPE_UNIT_COST} EUR a unit and reads back a cost basis of {cost[0]} {cost[1]}"


# ============================================================================
# RED AND GUARDS — BALANCES SUMMED EXACTLY
# ============================================================================

TEN_DECIMALS_BUY = "99999.1234567891"
EXACT_HOLDING = Decimal("199998.2469135782")
HOLDING_READS = ("get_asset_holdings", "get_asset_holdings-as-of", "get_balances_at_end_of")


async def _read_quantities(service: TransactionService, broker_id: int, read: str) -> dict[int, Decimal]:
    """The quantity per asset of ``broker_id`` that ``read`` answers: over every row, or over the rows up to ``DAY``.
    ``get_asset_holdings`` feeds the broker summary, ``get_balances_at_end_of`` the BRIM gap-fix."""
    if read == "get_asset_holdings":
        return await service.get_asset_holdings(broker_id)
    if read == "get_asset_holdings-as-of":
        return await service.get_asset_holdings(broker_id, as_of=DAY)
    if read == "get_balances_at_end_of":
        return (await service.get_balances_at_end_of(broker_id, DAY))[1]
    raise ValueError(f"unknown read {read!r}")


class TestBalancesAreSummedExactly:
    """Rule 3: the balances are summed in Python with exact ``Decimal``, not by SQL over the stored doubles."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("read", HOLDING_READS)
    async def test_two_buys_of_ten_decimals_sum_exactly(self, world, read):
        """RED: two BUYs of 99999.1234567891 (15 significant digits, 10 decimals: within both limits) hold exactly
        199998.2469135782. Today the SQL sum, read through ``Numeric(18, 6)``, answers 199998.246914; with the new column
        and an SQL sum it would answer 199998.2469135780, the sum's double cut to 15 significant digits."""
        for _ in range(2):
            await _seed_position(world, TransactionType.BUY, TEN_DECIMALS_BUY, day=DAY, amount="-1000")

        held = (await _read_quantities(TransactionService(world.session), world.main_id, read)).get(world.asset_id)

        assert held == EXACT_HOLDING, f"C-97a rule 3: {read} on two BUYs of {TEN_DECIMALS_BUY} must answer their exact sum {EXACT_HOLDING}; it answers {held}"

    @pytest.mark.asyncio
    async def test_cash_balances_at_the_end_of_a_day_keep_todays_results(self, world):
        """Guard: the cash ``get_balances_at_end_of`` answers is today's — deposits of 0.1 and 0.2 EUR (a sum the doubles
        miss at the 17th digit), a deposit an exclusion leaves out, a currency whose movements cancel out (kept, at 0),
        a deposit the day after (not counted)."""
        await _seed_cash(world, TransactionType.DEPOSIT, "0.1", EUR, day=SEED_DAY)
        await _seed_cash(world, TransactionType.DEPOSIT, "0.2", EUR, day=SEED_DAY)
        excluded_id = await _seed_cash(world, TransactionType.DEPOSIT, "1000", EUR, day=DAY)
        await _seed_cash(world, TransactionType.DEPOSIT, "5", USD, day=DAY)
        await _seed_cash(world, TransactionType.WITHDRAWAL, "-5", USD, day=DAY)
        await _seed_cash(world, TransactionType.DEPOSIT, "7", EUR, day=NEXT_DAY)
        await _seed_position(world, TransactionType.BUY, "1", day=DAY, amount="-40.25")
        service = TransactionService(world.session)

        cash = (await service.get_balances_at_end_of(world.main_id, DAY))[0]
        cash_without = (await service.get_balances_at_end_of(world.main_id, DAY, exclude_tx_ids=[excluded_id]))[0]

        assert cash == {EUR: Decimal("960.05"), USD: Decimal("0")}, f"The cash of broker {world.main_id} at the end of {DAY}: expected 960.05 EUR and 0 USD, as today; got {cash}"
        assert cash_without == {EUR: Decimal("-39.95"), USD: Decimal("0")}, f"The same, without the deposit id={excluded_id}: expected -39.95 EUR and 0 USD, as today; got {cash_without}"

    @pytest.mark.asyncio
    async def test_quantities_keep_their_date_bounds_and_exclusions(self, world):
        """Guard: the quantities keep today's bounds — the day ``as_of`` included, the day after left out, the rows
        ``exclude_tx_ids`` names left out — in both reads; whole quantities, which the doubles sum exactly."""
        await _seed_position(world, TransactionType.BUY, "3", day=SEED_DAY, amount="-30")
        excluded_id = await _seed_position(world, TransactionType.BUY, "4", day=DAY, amount="-40")
        await _seed_position(world, TransactionType.SELL, "-2", day=DAY, amount="25")
        await _seed_position(world, TransactionType.BUY, "100", day=NEXT_DAY, amount="-1000")
        service = TransactionService(world.session)

        reads = {
            "get_balances_at_end_of(DAY)": (await service.get_balances_at_end_of(world.main_id, DAY))[1],
            "get_balances_at_end_of(DAY) without the BUY of 4": (await service.get_balances_at_end_of(world.main_id, DAY, exclude_tx_ids=[excluded_id]))[1],
            "get_asset_holdings(as_of=DAY)": await service.get_asset_holdings(world.main_id, as_of=DAY),
            "get_asset_holdings()": await service.get_asset_holdings(world.main_id),
        }

        expected = {
            "get_balances_at_end_of(DAY)": {world.asset_id: Decimal("5")},
            "get_balances_at_end_of(DAY) without the BUY of 4": {world.asset_id: Decimal("1")},
            "get_asset_holdings(as_of=DAY)": {world.asset_id: Decimal("5")},
            "get_asset_holdings()": {world.asset_id: Decimal("105")},
        }
        assert reads == expected, f"The quantities of broker {world.main_id} must keep today's date bounds and exclusions: expected {expected}, got {reads}"


# ============================================================================
# GUARD — THE ASSET LIST READS HOLDINGS EXACTLY
# ============================================================================


class TestTheAssetListReadsHoldingsExactly:
    """Guard, green today and after C-97a (rule 4): an asset is held where the sum of its quantities on a broker exceeds
    ``QUANTITY_DUST_THRESHOLD`` (``AssetCRUDService.list_assets``, today an SQL ``HAVING`` over the doubles)."""

    @pytest.mark.asyncio
    async def test_bought_point_one_and_point_two_then_sold_point_three_is_not_held(self, world):
        """Guard: the test's asset, bought 0.1 + 0.2 and sold 0.3, is held by nobody — its doubles sum to about 5.6e-17,
        its exact sum to 0. The control asset, sold 0.2999, keeps 0.0001, above the threshold: held, which proves the
        list reads the holdings at all. No user is passed, so a holding reads as held by others."""
        control_id = await _new_asset(world, "control coin")
        sold = {world.asset_id: "-0.3", control_id: "-0.2999"}
        for asset_id, sold_quantity in sold.items():
            await _seed_position(world, TransactionType.BUY, "0.1", amount="-10", asset_id=asset_id)
            await _seed_position(world, TransactionType.BUY, "0.2", amount="-20", asset_id=asset_id)
            await _seed_position(world, TransactionType.SELL, sold_quantity, day=DAY, amount="30", asset_id=asset_id)
        control_residual = Decimal("0.1") + Decimal("0.2") + Decimal(sold[control_id])
        assert control_residual > QUANTITY_DUST_THRESHOLD, f"scaffold: the control keeps {control_residual}, not above the threshold {QUANTITY_DUST_THRESHOLD}"

        listed = await AssetCRUDService.list_assets(FAAinfoFiltersRequest(search=world.marker), world.session)

        flags = {asset.id: (asset.held_by_me, asset.held_by_others) for asset in listed}
        assert {world.asset_id, control_id} <= set(flags), f"scaffold: the list searched by the test's marker lacks its assets {world.asset_id} and {control_id}: {sorted(flags)}"
        assert flags[control_id] == (False, True), f"Presence control: the control asset id={control_id} keeps {control_residual}, so it is held (by others, no user being passed); (held_by_me, held_by_others) = {flags[control_id]}"
        assert flags[world.asset_id] == (False, False), f"C-97a rule 4: asset id={world.asset_id} was bought 0.1 + 0.2 and sold 0.3, so it is held by nobody; (held_by_me, held_by_others) = {flags[world.asset_id]}"


# ============================================================================
# GUARD — D2: BRIM PARSE DOES NOT REFUSE
# ============================================================================


class _ParseOnlyProvider(BRIMProvider):
    """A BRIM plugin reduced to the parent's row constructor, ``_create_transaction``: what every plugin calls."""

    @property
    def provider_code(self) -> str:
        return "c97a_parse_only"

    @property
    def provider_name(self) -> str:
        return "C-97a parse-only"

    @property
    def description(self) -> str:
        return "Builds rows through BRIMProvider._create_transaction for the C-97a tests"

    def can_parse(self, file_path) -> bool:
        return False

    def parse(self, file_path, broker_id) -> BRIMParseOutput:
        return BRIMParseOutput()


# A row a broker's file can carry, over a limit of the batch, as a plugin hands it to _create_transaction.
BRIM_ROWS = [
    pytest.param({"type": "BUY", "quantity": Decimal("0.123456789012"), "cash": Currency(code=EUR, amount=Decimal("-100"))}, id="quantity-12-decimals"),
    pytest.param({"type": "BUY", "quantity": Decimal("1234567890123.456"), "cash": Currency(code=EUR, amount=Decimal("-100"))}, id="quantity-16-significant-digits"),
    pytest.param({"type": "BUY", "quantity": Decimal("1"), "cash": Currency(code=EUR, amount=Decimal("-100.1234567"))}, id="cash-amount-7-decimals"),
    pytest.param({"type": "ADJUSTMENT", "quantity": Decimal("1"), "cost_basis_override": Currency(code=EUR, amount=Decimal(COST_13_DECIMALS))}, id="cost-basis-13-decimals"),
]


class TestBrimParseDoesNotRefuse:
    """Guard (decision D2), green today and after C-97a: the limit is the batch's, at confirmation. A BRIM row over it is
    parsed — the import shows it, and its confirmation refuses it — so ``TXCreateItem`` must not refuse it, nor round it.
    """

    @pytest.mark.parametrize("fields", BRIM_ROWS)
    def test_brim_row_over_the_limit_is_parsed_as_it_reads(self, fields):
        """Guard: the item is returned and listed, its values as the file reads them, and no parse issue is recorded."""
        transactions: list = []
        issues: list = []

        item = _ParseOnlyProvider()._create_transaction(row_num=7, transactions=transactions, validation_issues=issues, context="C-97a", broker_id=1, asset_id=100, date=DAY, **fields)

        assert issues == [], f"D2: the decimal limit is checked at confirmation, not at BRIM parse; the row {fields} got parse issues {issues}"
        assert item is not None and transactions == [item], f"D2: the row {fields} must be parsed into an item and listed; got {item!r}, listed {transactions}"
        read = {name: getattr(item, name) for name in fields}
        assert read == fields, f"D2: the parse keeps the values as the file reads them, neither refused nor rounded: sent {fields}, parsed {read}"


# ============================================================================
# RED — THE CODES ARE LISTED
# ============================================================================


class TestTheCodesAreListed:
    """RED: both codes are members of ``TXValidationCode`` — the frontend maps a code to ``transactions.errors.<code>`` —
    so ``GET /transactions/types`` lists them in ``validation_codes``."""

    def test_validation_code_has_both_decimal_codes(self):
        """RED: today ``TXValidationCode`` has neither value."""
        values = {member.value for member in TXValidationCode}

        missing = sorted(set(DECIMAL_CODES) - values)

        assert missing == [], f"C-97a: TXValidationCode has no member of value {missing}"

    def test_transaction_types_lists_both_decimal_codes(self):
        """RED: the response ``GET /transactions/types`` builds (``get_transaction_types``) lists neither today."""
        response = TXTypesResponse(transaction_types=list(TX_TYPE_METADATA.values()), event_types=EVENT_TYPE_METADATA)

        missing = sorted(set(DECIMAL_CODES) - {info.code for info in response.validation_codes})

        assert missing == [], f"C-97a: GET /transactions/types does not list {missing} in validation_codes"
