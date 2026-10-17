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
5. An Auto cost basis is not checked. With ``cost_basis_mode`` ``auto`` or ``auto-detail`` the backend recomputes the
   amount — the average of the source pool (``_compute_wac_for_auto_items``, ``auto_cost.py``) — and reads only the
   currency of the ``cost_basis_override`` sent, so ``check_decimal_limits`` leaves that amount out
   (``_decimal_limit_values``): an Auto create or update is accepted whatever amount it carries, and the row holds the
   Auto cost, not that amount. A manual cost basis — ``manual``, or no mode with an explicit override — stays checked:
   over the limit it is refused, never rounded (D2). Found by the E2E «TRANSFER (asset) create → commit (dual brokers +
   asset + qty)» (``frontend/e2e/transactions/tx-commit-all-types.spec.ts:532``): the Form sends back the preview's
   average, a repeating decimal (100 / 3) in full, and the commit was refused with ``decimalPlacesExceeded``
   ``{"max": 12}`` on ``cost_basis_override``.
6. R13-SEC2 (W-B58, E's security review of 17/10): the integer digits. A quantity and a cash amount keep at most 15
   digits before the decimal point (``REAL_SIGNIFICANT_DIGITS``: the coordinator's decision N63, 17/10), a manual cost
   basis — a per-unit price — the ``precision - scale`` of its column, 12 (``max_integer_digits``); past that
   ``check_decimal_limits`` adds ``integerDigitsExceeded`` with ``{"max": 15}`` or ``{"max": 12}`` on the field: the
   third check, after the decimal places and the significant digits, so a value over two limits keeps the code of the
   first. The promotion's ``resolved_fields.cost_basis_override`` (a ``{code, amount}`` currency dict) is checked against
   the column ``cost_basis_override`` too: the issue sits on ``operation="promote"``, the promote's index,
   ``field="cost_basis_override"``, with any of the three codes and its ``{"max": N}``. A checked value past its
   column's integer digits — whichever code it gets — stops the batch right after ``check_decimal_limits``: the later
   stages compute with the values (products, averages, the float a REAL takes), and a value of a million digits
   overflows them. So such a batch raises nothing (no 500), every issue it answers carries a code (none reads «Balance
   validation error»), and nothing is saved. ``TXValidationCode.INTEGER_DIGITS_EXCEEDED = "integerDigitsExceeded"``,
   listed by ``GET /transactions/types``.
7. R13-SEC2: a row the file holds as a REAL today's read cannot turn into a Decimal — a quantity of 1e60, an infinite one
   (SQLite reads the literal ``1e999`` as +inf), an infinite close — no longer breaks anyone: ``list_assets``, which reads
   every user's quantities, raises nothing; the infinite quantity loads as None and its row can be deleted through the
   batch; the quantity of 1e60 loads as 1E+60; the infinite close loads as None.
8. W-B60 (17/10, the follow-up of W-B58): a cash amount reads back exactly. ``Transaction.amount`` was a plain
   ``Numeric(18, 6)``, read through ``'%.6f'`` of the stored double, so from about 11 integer digits the double's noise
   landed in the 6 decimals; it becomes ``RealDecimal(18, 6)`` — same declaration, same DDL, no migration. A BUY committed
   through the batch with a cash amount of -123456789012.345 EUR (15 significant digits, 12 before the point: within
   N63's 15) reads back -123456789012.345000, column by column and through the service (``get_by_ids``), and the control
   totals (``compute_control_totals``: what a backup records and a restore checks) give its broker's EUR line as
   -123456789012.345. What reads well today keeps its form: -100 EUR reads -100.000000.

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
- ``TestAnAutoCostBasisIsNotChecked`` (rule 5): a received TRANSFER, an ADJUSTMENT +1 and an update of a stored
  ADJUSTMENT +1, in ``auto`` or ``auto-detail``, whose cost basis carries the pool's repeating average — 100 / 3 as the
  preview answers it (26 decimals), or 1000000 / 3 as a double prints it (16 significant digits) — are accepted on
  ``/validate`` and on ``/commit``; committed with an amount that is not the pool's average (125 / 3), the row holds the
  Auto cost, 100 / 3 read back 33.333333333333 EUR, not the amount sent (today refused on its row,
  ``decimalPlacesExceeded`` ``{"max": 12}`` or ``significantDigitsExceeded`` ``{"max": 15}``, and nothing is written);
- ``TestBalancesAreSummedExactly.test_two_buys_of_ten_decimals_sum_exactly`` (today 199998.246914);
- ``TestTheCodesAreListed``: ``TXValidationCode`` and ``GET /transactions/types``'s ``validation_codes`` carry both codes;
- ``TestTooManyIntegerDigitsAreRefused`` (rule 6, R13-SEC2): a create past its integer digits — a quantity of 1E+60,
  of 16 digits or of 1E+400, or a cash amount of -1E+15 (``{"max": 15}``), a cost basis of 1E+60 or of 13 digits
  (``{"max": 12}``) — is refused on its row with exactly ``integerDigitsExceeded`` on ``/validate`` and ``/commit``,
  nothing written; an update of a quantity to 1E+60 too (today the 16 digits, the -1E+15 EUR, the 13-digit cost and the
  update pass unrefused, and the creates of 1E+60 and 1E+400 make ``validate_cost_basis`` raise as it reloads the row: a
  500). On an ordinary broker (no overdraft, no shorting), through ``/validate`` and ``/commit``: a BUY of 1E+1000000
  units and one of -1E+1000000 EUR get ``integerDigitsExceeded`` ``{"max": 15}`` on their field and raise nothing
  (today ``decimal.Overflow`` in ``decimal_limit_issue``'s ``normalize``: a 500); a BUY of 400 ones keeps
  ``significantDigitsExceeded`` ``{"max": 15}`` on its quantity and gets no issue without a code (today the row goes on
  as a float inf, and ``validate_cost_basis`` raises ``TypeError`` reloading it, before the balance replay could add its
  raw «Balance validation error»); nothing is saved;
- ``TestAPromotedCostBasisIsChecked`` (rule 6): a promote whose resolved cost basis has 13 decimals, 16 significant
  digits, 13 integer digits, or is 1E+60, is refused on its own index (1, behind a valid promote) with the code and the
  ``{"max": N}`` of its limit (12 for the integer digits), nothing changed (today both promotes commit, the cost basis
  unchecked);
- ``TestCorruptRowsAreReadWithoutRaising`` (rule 7): today ``InvalidOperation`` (the REAL 1e60) and ``TypeError``
  (the REAL inf) on every read, the asset list's and the delete's included;
- ``TestACashAmountReadsBackExactly`` (rule 8, W-B60): today the BUY's cash amount reads back -123456789012.345001, and
  the control totals give -123456789012.345001: the double's noise;
- ``TestTheCodesAreListed``: ``TXValidationCode.INTEGER_DIGITS_EXCEEDED``, and ``validation_codes`` lists it.

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
- ``TestAnAutoCostBasisIsNotChecked``'s manual cases (rule 5, D2): the same amounts with ``cost_basis_mode`` ``manual``
  are refused on their row, ``decimalPlacesExceeded`` ``{"max": 12}`` or ``significantDigitsExceeded`` ``{"max": 15}``;
  no mode with an explicit override is pinned by ``TestOverTheLimitIsRefusedAtConfirmation``.
- ``TestTooManyIntegerDigitsAreRefused`` (rule 6): the integer limit is reached, not passed — a BUY of 999999999999999
  units for -999999999999999 EUR (15 digits each), one of 13-digit units for -1E+13 EUR (accepted under N63), a cost
  basis of 999999999999.999 (12 integer digits) commit;
- ``TestAPromotedCostBasisIsChecked`` (rule 6): a promote whose resolved cost basis keeps 12 decimals commits, and the
  receiving leg holds it exactly;
- ``TestACashAmountReadsBackExactly`` (rule 8): cash amounts of -100 and -1234.5 EUR read back -100.000000 and
  -1234.500000, column by column and through the service, as ``Numeric(18, 6)`` reads them today.

Derived — read from the contract's general rule, not in the brief's list; drop them if the rule was meant narrower: a
quantity over both limits gets ``decimalPlacesExceeded`` alone (the "otherwise"); a cash amount past 15 significant
digits gets ``significantDigitsExceeded``; a row over the limit on two fields gets one issue per field.

Ownership. Every test builds its own asset and brokers under a unique marker, in one session rolled back at the end. A
batch runs as the endpoint runs it, its transaction included (``_run_as_the_endpoint``), so a refused batch leaves the
database as it found it, and nothing reaches the lane's database. The corrupt rows of rule 7 are written the same way —
with the ORM, then overwritten by raw SQL — inside that session, and rolled back with it: no other connection ever sees
them.

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

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetType, Broker, PriceHistory, Transaction, TransactionType
from backend.app.db.session import get_async_engine
from backend.app.schemas.assets.assets import FAAinfoFiltersRequest
from backend.app.schemas.brim import BRIMParseOutput
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions.batch import TXBatchResponse, TXValidationCode, TXValidationIssue
from backend.app.schemas.transactions.type_metadata import EVENT_TYPE_METADATA, TX_TYPE_METADATA, TXTypesResponse
from backend.app.services.assets.crud import AssetCRUDService
from backend.app.services.brim.brim_provider import BRIMProvider
from backend.app.services.financial_math.ledger_totals import compute_control_totals
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
# R13-SEC2 (rule 6): the third code, past the digits a column keeps before the decimal point — compared as a string, as
# the two above. The coordinator's decision N63 (17/10): 15 for a quantity and a cash amount (REAL_SIGNIFICANT_DIGITS),
# 12 for a per-unit cost basis (precision - scale of (24, 12)).
INTEGER_DIGITS_EXCEEDED = "integerDigitsExceeded"
QUANTITY_INTEGER_MAX = {"max": 15}
CASH_INTEGER_MAX = {"max": 15}
COST_INTEGER_MAX = {"max": 12}
# Every code of a value over its column's limit: what _decimal_issues collects and _other_issues leaves out.
LIMIT_CODES = (*DECIMAL_CODES, INTEGER_DIGITS_EXCEEDED)
# R13-SEC2 (rule 7): what a corrupt file holds, as SQLite literals: a REAL of 1e60, and +inf (SQLite reads 1e999 as Inf).
HUGE_REAL = "1e60"
INFINITE_REAL = "1e999"

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


async def _run_as_the_endpoint(world: World, *, creates: list[dict] | None = None, updates: list[dict] | None = None, deletes: list[int] | None = None, promotes: list[dict] | None = None, endpoint: str = "commit") -> TXBatchResponse:
    """The batch as ``POST /transactions/<endpoint>`` runs it, its transaction included: ``/commit`` keeps it when the
    service answers committed and rolls it back otherwise, ``/validate`` always rolls it back (``api/v1/transactions.py``);
    no user, so no access check.

    ``execute_batch`` applies and flushes the rows it keeps, a refused one included, and leaves the commit or the
    rollback to its caller. A savepoint stands in for the request's transaction, as in
    ``test_transaction_cost_basis_rule.py``: the rows the test wrote before it survive its rollback (their flush opened
    SQLite's transaction, so the savepoint nests in it), and the session fixture still rolls everything back.
    """
    savepoint = await world.session.begin_nested()
    response = await TransactionService(world.session).execute_batch(creates_raw=creates or [], updates_raw=updates or [], deletes=deletes or [], promotes_raw=promotes or [], commit=endpoint == "commit")
    if endpoint == "commit" and response.committed:
        await savepoint.commit()
    else:
        await savepoint.rollback()
    return response


async def _run_never_raising(world: World, story: str, **batch) -> TXBatchResponse:
    """``_run_as_the_endpoint(world, **batch)``; an exception fails the test and names it: the endpoint would answer 500
    instead of a refusal (R13-SEC2). Whatever the batch left half-done goes with the session fixture's rollback."""
    try:
        return await _run_as_the_endpoint(world, **batch)
    except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
        pytest.fail(f"R13-SEC2: {story}: execute_batch raised {exc!r}, so /transactions/{batch.get('endpoint', 'commit')} answers 500 instead of a refusal")


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
    """The batch's refusals over a column's limit — decimal places, significant digits, integer digits (R13-SEC2) — as
    ``(operation, index, ref_id, code, field, params)``, sorted."""
    return sorted(((issue.operation, issue.index, issue.ref_id, issue.code, issue.field, issue.params) for issue in response.issues if issue.code in LIMIT_CODES), key=_issue_order)


def _other_issues(response: TXBatchResponse) -> list[TXValidationIssue]:
    """Every issue of the batch that is not a refusal over a column's limit."""
    return [issue for issue in response.issues if issue.code not in LIMIT_CODES]


def _render(issues: list[TXValidationIssue]) -> str:
    """The issues, for a failure message."""
    return "; ".join(f"{issue.operation}[{issue.index}] ref_id={issue.ref_id} code={issue.code} field={issue.field} params={issue.params} error={issue.error!r}" for issue in issues) or "none"


def _words(text: str) -> str:
    """``text`` as lower-case words: ``cash.amount`` and «Cash amount» read alike."""
    return " ".join(text.lower().replace(".", " ").replace("_", " ").split())


def _assert_errors_name_their_fields(response: TXBatchResponse) -> None:
    """Each refusal over a column's limit carries an English ``error`` that names its field, as sent (``cash.amount``) or
    in words."""
    for issue in response.issues:
        if issue.code in LIMIT_CODES:
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
# RED AND GUARDS — RULE 5: AN AUTO COST BASIS IS NOT CHECKED
# ============================================================================

# The modes in which the backend computes the cost basis itself, and reads only the currency of the one sent.
AUTO_MODES = ("auto", "auto-detail")


@dataclass(frozen=True)
class RepeatingAverage:
    """A pool whose average cost repeats forever — a BUY of 3 units on ``main`` for ``pool_cost`` EUR — and that average
    as a client sends it back in Auto (``sent``): over the limit of a manual cost basis, which refuses it with ``code``
    and ``params``."""

    pool_cost: str
    sent: str
    code: str
    params: dict


# 100 / 3 in full, as the batch's own preview answers it (``wac_results``) and the Bulk modal copies it back into an Auto
# row's cost basis (``TransactionBulkModal.svelte``): 28 significant digits, 26 decimals. The E2E's shape.
HUNDRED_OVER_THREE = RepeatingAverage(pool_cost="100", sent="33.33333333333333333333333333", code=DECIMAL_PLACES_EXCEEDED, params=COST_MAX)
# 1000000 / 3 as a double prints it: 10 decimals, within the 12, but 16 significant digits.
MILLION_OVER_THREE = RepeatingAverage(pool_cost="1000000", sent="333333.3333333333", code=SIGNIFICANT_DIGITS_EXCEEDED, params=DIGITS_MAX)
REPEATING_AVERAGES = [
    pytest.param(HUNDRED_OVER_THREE, id="100-over-3-26-decimals"),
    pytest.param(MILLION_OVER_THREE, id="1000000-over-3-16-significant-digits"),
]

# The Auto cost of HUNDRED_OVER_THREE's pool, 100 / 3, as ``RealDecimal(24, 12)`` reads it back: the double
# 33.333333333333336, cut to 15 significant digits, then to 12 decimals.
AUTO_COST_OF_HUNDRED_OVER_THREE = Decimal("33.333333333333")
# An amount over the limit that is not that pool's average — 125 / 3 in full, as a preview taken before the pool changed
# would answer — so the row tells the amount sent (it would read back 41.666666666667) from the Auto cost.
NOT_THE_POOLS_AVERAGE = "41.66666666666666666666666667"

# The rows the outcome is read on: the two creates of ``_per_unit_cost_batch``, and the update of a stored ADJUSTMENT +1.
AUTO_COST_SUBJECTS = [
    pytest.param("create", "transfer_received", id="create-transfer_received"),
    pytest.param("create", "adjustment_in", id="create-adjustment_in"),
    pytest.param("update", "adjustment_in", id="update-adjustment_in"),
]


async def _seed_pool(world: World, cost: str) -> int:
    """The pool every Auto cost of these tests averages, written before ``DAY``: a BUY of 3 units on ``main`` for ``cost``
    EUR; its id. A received TRANSFER averages its partner's broker, ``main``, before the transfer, an ADJUSTMENT its own
    broker without itself (``_auto_cost_source``, ``auto_cost.py``); the BUY also brings the unit a TRANSFER's giving
    leg moves (``main`` may not go short)."""
    return await _seed_position(world, TransactionType.BUY, "3", amount=f"-{cost}")


def _deposit(world: World) -> dict:
    """A create of a DEPOSIT of 100 EUR on ``main``: a row without an asset, so in no pool."""
    return {"broker_id": world.main_id, "type": "DEPOSIT", "date": DAY.isoformat(), "quantity": "0", "cash": {"code": EUR, "amount": "100"}, "description": world.batch_description}


def _cost_basis_creates(world: World, shape: str, mode: str, amount: str) -> tuple[list[dict], int]:
    """The creates of a ``shape`` row (``_per_unit_cost_batch``) receiving one unit with ``cost_basis_mode`` ``mode`` and a
    cost basis of ``amount`` EUR, and that row's index. Behind a DEPOSIT (``_deposit``): the row's index is not a
    default, and the pool its Auto cost averages stays the seeded one."""
    creates, subject_index = _per_unit_cost_batch(world, shape, amount)
    creates[subject_index] = {**creates[subject_index], "cost_basis_mode": mode}
    return [_deposit(world), *creates], subject_index + 1


async def _cost_basis_update(world: World, mode: str, amount: str) -> tuple[list[dict], int, int]:
    """The updates that set a stored ADJUSTMENT +1 (on ``DAY``, at a manual cost of 100 EUR) to ``cost_basis_mode``
    ``mode`` with a cost basis of ``amount`` EUR — sent at index 1, behind a notes edit of a stored DEPOSIT on ``main``,
    in no pool — then the ADJUSTMENT's id and the DEPOSIT's."""
    neighbour_id = await _seed_cash(world, TransactionType.DEPOSIT, "100", EUR, day=SEED_DAY)
    subject_id = await _seed_position(world, TransactionType.ADJUSTMENT, "1", day=DAY, cost="100")
    updates = [{"id": neighbour_id, "description": f"{world.marker} neighbour edited"}, {"id": subject_id, "cost_basis_mode": mode, "cost_basis_override": {"code": EUR, "amount": amount}}]
    return updates, subject_id, neighbour_id


class TestAnAutoCostBasisIsNotChecked:
    """Rule 5: an Auto cost basis is not checked. Found by the E2E «TRANSFER (asset) create → commit (dual brokers +
    asset + qty)» (``frontend/e2e/transactions/tx-commit-all-types.spec.ts:532``), whose commit was refused with
    ``decimalPlacesExceeded`` ``{"max": 12}`` on ``cost_basis_override``.

    With ``cost_basis_mode`` ``auto`` or ``auto-detail`` the amount of the ``cost_basis_override`` sent is not used:
    ``_compute_wac_for_auto_items`` (``auto_cost.py``) reads its currency alone, recomputes the average of the source
    pool and writes it on the row. The Form sends back the preview's average, which can repeat forever (100 / 3), and
    ``check_decimal_limits`` refuses it whatever the mode: an amount the batch would have discarded. The cure:
    ``_decimal_limit_values`` leaves out the cost basis of an Auto row.

    REDS: an Auto create or update carrying such an amount is accepted, and the row holds the Auto cost, not the amount
    sent. GUARDS: the same amounts as a ``manual`` cost basis stay refused on their row, never rounded (D2). No mode with
    an explicit override is a manual cost basis too: ``TestOverTheLimitIsRefusedAtConfirmation`` pins it.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    @pytest.mark.parametrize("average", REPEATING_AVERAGES)
    @pytest.mark.parametrize("mode", AUTO_MODES)
    @pytest.mark.parametrize("shape", PER_UNIT_COST_SHAPES)
    async def test_auto_create_carrying_the_previews_average_is_accepted(self, world, shape, mode, average, endpoint):
        """RED, the defect of ``tx-commit-all-types.spec.ts:532``: a received TRANSFER (the E2E's own row) or an
        ADJUSTMENT +1 in ``mode``, whose cost basis carries the pool's repeating average, gets no decimal issue on
        ``/validate`` nor on ``/commit``, nor any other issue, and ``/commit`` commits.

        Red today: ``check_decimal_limits`` checks the amount whatever the mode and refuses it on the row —
        ``decimalPlacesExceeded`` ``{"max": 12}`` for 100 / 3 in full, ``significantDigitsExceeded`` ``{"max": 15}`` for
        1000000 / 3 — so nothing is committed.
        """
        await _seed_pool(world, average.pool_cost)
        creates, subject_index = _cost_basis_creates(world, shape, mode, average.sent)

        response = await _run_as_the_endpoint(world, creates=creates, endpoint=endpoint)

        assert _decimal_issues(response) == [], f"C-97a rule 5, /{endpoint}: an {mode} cost basis is the backend's to compute, so the amount {average.sent} EUR of the {shape} (create {subject_index}) must not be checked; the batch answered: {_render(response.issues)}"
        assert response.issues == [], f"C-97a rule 5, /{endpoint}: nothing else may refuse the {mode} {shape}: {_render(response.issues)}"
        assert response.committed is (endpoint == "commit"), f"C-97a rule 5: /{endpoint} found no issue, so it must answer committed={endpoint == 'commit'}; it answered {response.committed}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    @pytest.mark.parametrize("average", REPEATING_AVERAGES)
    @pytest.mark.parametrize("mode", AUTO_MODES)
    async def test_auto_update_carrying_the_previews_average_is_accepted(self, world, mode, average, endpoint):
        """RED, the defect of ``tx-commit-all-types.spec.ts:532`` on an update: a stored ADJUSTMENT +1 set to ``mode``
        with the pool's repeating average as its cost basis, sent at index 1 behind a notes edit, gets no decimal issue —
        none on update 1, ``ref_id`` its id — on ``/validate`` nor on ``/commit``, nor any other issue, and ``/commit``
        commits.

        Red today: ``check_decimal_limits`` refuses the amount on update 1, ``ref_id`` the ADJUSTMENT's id, as if it were
        a manual cost basis.
        """
        await _seed_pool(world, average.pool_cost)
        updates, subject_id, _neighbour_id = await _cost_basis_update(world, mode, average.sent)

        response = await _run_as_the_endpoint(world, updates=updates, endpoint=endpoint)

        assert _decimal_issues(response) == [], f"C-97a rule 5, /{endpoint}: an {mode} cost basis is the backend's to compute, so the amount {average.sent} EUR of the update of ADJUSTMENT id={subject_id} must not be checked; the batch answered: {_render(response.issues)}"
        assert response.issues == [], f"C-97a rule 5, /{endpoint}: nothing else may refuse the {mode} update of id={subject_id}: {_render(response.issues)}"
        assert response.committed is (endpoint == "commit"), f"C-97a rule 5: /{endpoint} found no issue, so it must answer committed={endpoint == 'commit'}; it answered {response.committed}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("mode", AUTO_MODES)
    @pytest.mark.parametrize(("operation", "shape"), AUTO_COST_SUBJECTS)
    async def test_the_row_holds_the_auto_cost_not_the_amount_sent(self, world, operation, shape, mode):
        """RED, the outcome that proves the amount ignored, not merely tolerated (the defect of
        ``tx-commit-all-types.spec.ts:532``): a create or an update in ``mode`` carrying 125 / 3 in full — not the pool's
        average — commits through ``/commit``, and the row holds the Auto cost the backend computes: the pool's average,
        100 / 3, read back 33.333333333333, in EUR, the currency sent. Not the amount sent (read back 41.666666666667),
        nor, for the update, the 100 EUR the row was stored with. So the amount the cure leaves unchecked never reaches
        the database.

        Red today: the batch refuses the amount sent (``decimalPlacesExceeded`` ``{"max": 12}``) and writes nothing.
        """
        await _seed_pool(world, HUNDRED_OVER_THREE.pool_cost)
        if operation == "update":
            updates, subject_id, _neighbour_id = await _cost_basis_update(world, mode, NOT_THE_POOLS_AVERAGE)
            response = await _run_as_the_endpoint(world, updates=updates)
        else:
            creates, subject_index = _cost_basis_creates(world, shape, mode, NOT_THE_POOLS_AVERAGE)
            response = await _run_as_the_endpoint(world, creates=creates)
            subject_id = _created_ids(response).get(subject_index)

        assert response.committed is True and response.issues == [], f"C-97a rule 5: the {mode} {operation} of the {shape} carrying {NOT_THE_POOLS_AVERAGE} EUR must commit, its amount being the backend's to compute; it was refused: {_render(response.issues)}"
        stored = (await _stored(world, [subject_id]))[subject_id]
        cost, expected = (stored["cost_basis_override"], stored["cost_basis_currency"]), (AUTO_COST_OF_HUNDRED_OVER_THREE, EUR)
        assert cost == expected, f"C-97a rule 5: in {mode} the {shape} id={subject_id} must hold the Auto cost, the pool's 100 / 3 read back {expected[0]} {expected[1]}, not the {NOT_THE_POOLS_AVERAGE} sent; it holds {cost[0]} {cost[1]}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    @pytest.mark.parametrize("average", REPEATING_AVERAGES)
    @pytest.mark.parametrize("shape", PER_UNIT_COST_SHAPES)
    async def test_manual_create_carrying_the_same_amount_is_still_refused(self, world, shape, average, endpoint):
        """Guard (D2): the same amounts as a ``manual`` cost basis are the user's own, kept as sent, so over the limit
        they are refused on their row — exactly ``(create, index, None, code, cost_basis_override, params)`` — and never
        rounded: not committed, the row still in the batch, nothing written.

        Green today: ``check_decimal_limits`` checks every cost basis. A cure for ``tx-commit-all-types.spec.ts:532``
        that stops checking it whatever the mode turns it red.
        """
        barrier_id = await _seed_pool(world, average.pool_cost)
        creates, subject_index = _cost_basis_creates(world, shape, "manual", average.sent)

        response = await _run_as_the_endpoint(world, creates=creates, endpoint=endpoint)

        refusal = ("create", subject_index, None, average.code, "cost_basis_override", average.params)
        assert _decimal_issues(response) == [refusal], f"D2, /{endpoint}: a manual cost basis of {average.sent} EUR on the {shape} at create {subject_index} must be refused on its own row with exactly {refusal}; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        assert _other_issues(response) == [], f"D2, /{endpoint}: only the decimals may refuse this batch: {_render(_other_issues(response))}"
        assert response.committed is False, f"D2: /{endpoint} refused the batch, yet answered committed"
        _assert_errors_name_their_fields(response)
        assert ("create", subject_index) in _in_batch(response), f"D2: the refused row stays in the batch (applied and reported); the results are {response.results}"
        assert barrier_id in await _stored(world, [barrier_id]), f"scaffold: the read-back no longer sees row id={barrier_id}, written before the batch, so finding no row of the batch would prove nothing"
        written = await _batch_rows(world)
        assert written == [], f"D2: /{endpoint} refused the batch, yet the database holds its rows {written}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("average", REPEATING_AVERAGES)
    async def test_manual_update_carrying_the_same_amount_is_still_refused(self, world, average):
        """Guard (D2): an update setting a stored ADJUSTMENT +1 to a ``manual`` cost basis of the same amounts, sent at
        index 1 behind a notes edit, is refused on update 1 with ``ref_id`` its id; not committed; both rows read back as
        they were stored.

        Green today: ``check_decimal_limits`` checks every cost basis. A cure for ``tx-commit-all-types.spec.ts:532``
        that stops checking it whatever the mode turns it red.
        """
        await _seed_pool(world, average.pool_cost)
        updates, subject_id, neighbour_id = await _cost_basis_update(world, "manual", average.sent)
        before = await _stored(world, [neighbour_id, subject_id])

        response = await _run_as_the_endpoint(world, updates=updates)

        refusal = ("update", 1, subject_id, average.code, "cost_basis_override", average.params)
        assert _decimal_issues(response) == [refusal], f"D2: a manual cost basis of {average.sent} EUR on the update of ADJUSTMENT id={subject_id} must be refused on its own row with exactly {refusal}; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        assert _other_issues(response) == [], f"D2: only the decimals may refuse this batch: {_render(_other_issues(response))}"
        assert response.committed is False, "D2: /commit refused the batch, yet answered committed"
        _assert_errors_name_their_fields(response)
        assert ("update", 1) in _in_batch(response), f"D2: the refused update stays in the batch (applied and reported); the results are {response.results}"
        after = await _stored(world, [neighbour_id, subject_id])
        assert after == before, f"D2: the batch was refused, yet the stored rows changed: before {before}, after {after}"


# ============================================================================
# RED AND GUARDS — RULE 6 (R13-SEC2): THE INTEGER DIGITS
# ============================================================================

# A create past its integer digits on ``main`` — sent at index 1, behind a valid BUY — and the limit issues it gets, as
# (code, field, params): few digits and no decimal, so only the integer digits refuse it — 15 for a quantity and a cash
# amount, 12 for a cost basis (decision N63). 1E+400 is beyond a double too: before the cure it became a REAL inf.
INTEGER_CREATE_REFUSALS = [
    pytest.param({"tx_type": "BUY", "quantity": "1E+60", "cash": "-10"}, [(INTEGER_DIGITS_EXCEEDED, "quantity", QUANTITY_INTEGER_MAX)], id="quantity-1E+60"),
    pytest.param({"tx_type": "BUY", "quantity": "1000000000000000", "cash": "-10"}, [(INTEGER_DIGITS_EXCEEDED, "quantity", QUANTITY_INTEGER_MAX)], id="quantity-16-integer-digits"),
    pytest.param({"tx_type": "BUY", "quantity": "1E+400", "cash": "-10"}, [(INTEGER_DIGITS_EXCEEDED, "quantity", QUANTITY_INTEGER_MAX)], id="quantity-1E+400-beyond-a-double"),
    pytest.param({"tx_type": "BUY", "quantity": "1", "cash": "-1E+15"}, [(INTEGER_DIGITS_EXCEEDED, "cash.amount", CASH_INTEGER_MAX)], id="cash-amount--1E+15"),
    pytest.param({"tx_type": "ADJUSTMENT", "quantity": "1", "cost": "1E+60"}, [(INTEGER_DIGITS_EXCEEDED, "cost_basis_override", COST_INTEGER_MAX)], id="adjustment-in-cost-basis-1E+60"),
    pytest.param({"tx_type": "ADJUSTMENT", "quantity": "1", "cost": "1000000000000"}, [(INTEGER_DIGITS_EXCEEDED, "cost_basis_override", COST_INTEGER_MAX)], id="adjustment-in-cost-basis-13-integer-digits"),
]

# A value of a million digits, or of 400, on an ordinary broker: the subject's fields, and the limit issue its row gets
# as (code, field, params). The coordinator's (a) and (c); (b) has its own test.
MILLION_DIGIT_REFUSALS = [
    pytest.param({"quantity": "1E+1000000", "cash": "-10"}, (INTEGER_DIGITS_EXCEEDED, "quantity", QUANTITY_INTEGER_MAX), id="a-quantity-1E+1000000"),
    pytest.param({"quantity": "1", "cash": "-1E+1000000"}, (INTEGER_DIGITS_EXCEEDED, "cash.amount", CASH_INTEGER_MAX), id="c-cash-amount--1E+1000000"),
]
FOUR_HUNDRED_ONES = "1" * 400


async def _ordinary_broker(world: World) -> tuple[int, int]:
    """A broker of the test with the default settings — no cash overdraft, no asset shorting — holding a DEPOSIT of 100
    EUR on ``SEED_DAY``: a BUY of 10 EUR is valid there but for its digits, whatever ``main`` allows. Its id, and the
    deposit's (a row written before the batch, which the read-back must still see)."""
    now = utcnow()
    broker = Broker(name=f"{world.marker} ordinary", description="R13-SEC2: a broker with the default settings", created_at=now, updated_at=now)
    world.session.add(broker)
    await world.session.flush()
    assert (broker.allow_cash_overdraft, broker.allow_asset_shorting) == (False, False), f"scaffold: a broker's defaults changed, it allows (overdraft, shorting) = {(broker.allow_cash_overdraft, broker.allow_asset_shorting)}"
    broker_id = broker.id
    deposit_id = await _insert(world, broker_id=broker_id, asset_id=None, type=TransactionType.DEPOSIT, date=SEED_DAY, quantity=Decimal("0"), amount=Decimal("100"), currency=EUR)
    return broker_id, deposit_id


def _million_digit_batch(world: World, broker_id: int, subject: dict) -> list[dict]:
    """A valid BUY of 1 unit for 10 EUR on ``broker_id``, then the subject: a BUY of ``subject["quantity"]`` units for
    ``subject["cash"]`` EUR there, at index 1."""
    return [_row(world, "BUY", "1", cash="-10", broker_id=broker_id), _row(world, "BUY", subject["quantity"], cash=subject["cash"], broker_id=broker_id)]


class TestTooManyIntegerDigitsAreRefused:
    """Rule 6 (R13-SEC2): a quantity or a cash amount past 15 integer digits, a manual cost basis past 12 (decision N63),
    is refused at confirmation with ``integerDigitsExceeded`` and that ``{"max": N}``, never stored; and a checked value
    past its column's integer digits, whichever code it gets, stops the batch right after ``check_decimal_limits``.

    Today the limit has no magnitude, and the row goes on through the stages: created, flushed, then reloaded by
    ``validate_cost_basis`` (``_check_result_create_cost_basis``) through the column's type — a quantity or a cost basis
    of 1E+60 raises ``InvalidOperation`` there, one of 1E+400 or of 400 digits (a REAL inf) ``TypeError``: a 500 on
    ``/validate`` and ``/commit``; a quantity of 16 digits, a cash amount of -1E+15, a cost basis of 13 digits and an
    update to 1E+60 pass unrefused (``/commit`` commits them); ``decimal_limit_issue`` raises ``decimal.Overflow`` on
    ``1E+1000000``. The refused row is not asserted in the results: the batch stops before applying it.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    @pytest.mark.parametrize(("subject", "expected"), INTEGER_CREATE_REFUSALS)
    async def test_create_past_the_integer_digits_is_refused_on_its_row(self, world, subject, expected, endpoint):
        """Red today: nothing refuses it — a quantity of 16 digits, a cash amount of -1E+15 and a cost basis of 13 digits
        get no issue (``/commit`` commits them); a quantity or a cost basis of 1E+60 makes ``validate_cost_basis`` raise
        ``InvalidOperation`` as it reloads the row, 1E+400 ``TypeError`` (a REAL inf): a 500.

        Contract: exactly the expected issues on create 1 (``ref_id`` None), each with an English ``error`` naming its
        field, nothing else; not committed; no row of the batch in the database.
        """
        barrier_id = await _seed_position(world, TransactionType.BUY, "1", amount="-100")
        creates = [_row(world, "BUY", "1", cash="-100"), _row(world, **subject)]

        response = await _run_never_raising(world, f"the create {subject}", creates=creates, endpoint=endpoint)

        refusals = sorted((("create", 1, None, code, field, params) for code, field, params in expected), key=_issue_order)
        assert _decimal_issues(response) == refusals, f"R13-SEC2, /{endpoint}: the create {subject} must be refused on its own row with exactly {refusals}; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        assert _other_issues(response) == [], f"R13-SEC2, /{endpoint}: only the integer digits may refuse this batch: {_render(_other_issues(response))}"
        assert response.committed is False, f"R13-SEC2: /{endpoint} refused the batch, yet answered committed"
        _assert_errors_name_their_fields(response)
        assert barrier_id in await _stored(world, [barrier_id]), f"scaffold: the read-back no longer sees row id={barrier_id}, written before the batch, so finding no row of the batch would prove nothing"
        written = await _batch_rows(world)
        assert written == [], f"R13-SEC2: /{endpoint} refused the batch, yet the database holds its rows {written}"

    @pytest.mark.asyncio
    async def test_update_of_a_quantity_past_the_integer_digits_is_refused_on_its_row(self, world):
        """Red today: the update of a stored BUY's quantity to 1E+60 commits.

        Contract: refused on update 1 (behind a valid notes edit), ``ref_id`` its id, ``integerDigitsExceeded``
        ``{"max": 15}`` on ``quantity``, nothing else; not committed; both rows read back as they were stored.
        """
        neighbour_id = await _seed_position(world, TransactionType.BUY, "1", amount="-100")
        subject_id = await _seed_position(world, TransactionType.BUY, "1", amount="-100")
        before = await _stored(world, [neighbour_id, subject_id])
        updates = [{"id": neighbour_id, "description": f"{world.marker} neighbour edited"}, {"id": subject_id, "quantity": "1E+60"}]

        response = await _run_never_raising(world, f"the update of BUY id={subject_id} to 1E+60 units", updates=updates)

        refusal = ("update", 1, subject_id, INTEGER_DIGITS_EXCEEDED, "quantity", QUANTITY_INTEGER_MAX)
        assert _decimal_issues(response) == [refusal], f"R13-SEC2: the update of id={subject_id} to 1E+60 units must be refused on its own row with exactly {refusal}; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        assert _other_issues(response) == [], f"R13-SEC2: only the integer digits may refuse this batch: {_render(_other_issues(response))}"
        assert response.committed is False, "R13-SEC2: /commit refused the batch, yet answered committed"
        _assert_errors_name_their_fields(response)
        after = await _stored(world, [neighbour_id, subject_id])
        assert after == before, f"R13-SEC2: the batch was refused, yet the stored rows changed: before {before}, after {after}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    @pytest.mark.parametrize(("subject", "refusal"), MILLION_DIGIT_REFUSALS)
    async def test_a_value_of_a_million_digits_is_refused_without_raising(self, world, subject, refusal, endpoint):
        """Red today: ``decimal.Overflow`` in ``decimal_limit_issue``'s ``normalize`` (a context of 60 digits, ``Emax``
        999999): the endpoint answers 500.

        Contract (the coordinator's (a) and (c), on an ordinary broker — no overdraft, no shorting — so nothing but the
        digits can refuse the row): no exception; the subject's row, create 1, gets ``integerDigitsExceeded``
        ``{"max": 15}`` (decision N63) on its field (``quantity`` for a BUY of 1E+1000000 units, ``cash.amount`` for one
        of -1E+1000000 EUR), the only limit issue of the batch; not committed; nothing saved.
        """
        broker_id, deposit_id = await _ordinary_broker(world)
        code, field, params = refusal

        response = await _run_never_raising(world, f"a BUY of {subject['quantity']} units for {subject['cash']} EUR on an ordinary broker", creates=_million_digit_batch(world, broker_id, subject), endpoint=endpoint)

        expected = [("create", 1, None, code, field, params)]
        assert _decimal_issues(response) == expected, f"R13-SEC2, /{endpoint}: the BUY of {subject['quantity']} units for {subject['cash']} EUR must be refused on its own row with {expected}; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        assert response.committed is False, f"R13-SEC2: /{endpoint} refused the batch, yet answered committed"
        assert deposit_id in await _stored(world, [deposit_id]), f"scaffold: the read-back no longer sees the deposit id={deposit_id}, written before the batch, so finding no row of the batch would prove nothing"
        written = await _batch_rows(world)
        assert written == [], f"R13-SEC2: /{endpoint} refused the batch, yet the database holds its rows {written}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    async def test_a_quantity_of_400_digits_keeps_the_significant_digit_code_and_every_issue_has_a_code(self, world, endpoint):
        """Red today: the quantity gets ``significantDigitsExceeded``, then its row goes on through the stages as a float
        inf (a double holds no 400 digits): ``validate_cost_basis`` reloads it and raises ``TypeError`` (a 500) — measured
        in this worktree, before the balance replay, which would otherwise add «Balance validation error: …», an issue
        without a code that the app can only show as a raw English text.

        Contract (the coordinator's (b), on an ordinary broker): no exception; the issue on ``quantity`` keeps the first
        code in order, ``significantDigitsExceeded`` ``{"max": 15}`` (past 15 integer digits too, so the batch stops
        right after ``check_decimal_limits``); every issue of the response has a code, none reads «Balance validation
        error»; not committed; nothing saved.
        """
        broker_id, deposit_id = await _ordinary_broker(world)
        subject = {"quantity": FOUR_HUNDRED_ONES, "cash": "-10"}

        response = await _run_never_raising(world, "a BUY of 400 ones (a quantity of 400 digits) on an ordinary broker", creates=_million_digit_batch(world, broker_id, subject), endpoint=endpoint)

        expected = [("create", 1, None, SIGNIFICANT_DIGITS_EXCEEDED, "quantity", DIGITS_MAX)]
        assert _decimal_issues(response) == expected, f"R13-SEC2, /{endpoint}: a quantity of 400 digits must keep the first code in order, {expected}; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        without_code = [issue for issue in response.issues if issue.code is None]
        assert without_code == [], f"R13-SEC2, /{endpoint}: every issue must carry a code — the app translates the code, a raw text reaches the user in English; these have none: {_render(without_code)}"
        raw_balance = [issue for issue in response.issues if "Balance validation error" in (issue.error or "")]
        assert raw_balance == [], f"R13-SEC2, /{endpoint}: the batch must stop before the balance replay, which cannot replay a quantity of 400 digits: {_render(raw_balance)}"
        assert response.committed is False, f"R13-SEC2: /{endpoint} refused the batch, yet answered committed"
        assert deposit_id in await _stored(world, [deposit_id]), f"scaffold: the read-back no longer sees the deposit id={deposit_id}, written before the batch, so finding no row of the batch would prove nothing"
        written = await _batch_rows(world)
        assert written == [], f"R13-SEC2: /{endpoint} refused the batch, yet the database holds its rows {written}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "subject",
        [
            pytest.param({"tx_type": "BUY", "quantity": "999999999999999", "cash": "-999999999999999"}, id="quantity-and-cash-amount-15-integer-digits"),
            pytest.param({"tx_type": "BUY", "quantity": "1000000000000", "cash": "-1E+13"}, id="quantity-13-and-cash-amount-14-integer-digits"),
            pytest.param({"tx_type": "ADJUSTMENT", "quantity": "1", "cost": "999999999999.999"}, id="cost-basis-12-integer-digits-15-significant-digits"),
        ],
    )
    async def test_guard_the_integer_digits_at_the_limit_commit(self, world, subject):
        """Guard: green today and after. The integer limit is reached, not passed: 15 digits for a quantity and a cash
        amount (decision N63: 13 and 14 commit too), 12 for a cost basis; the create commits with no issue."""
        response = await _run_never_raising(world, f"the create {subject}", creates=[_row(world, **subject)])

        assert response.committed is True and response.issues == [], f"R13-SEC2: {subject} is within the integer digits of its fields (15 for a quantity and a cash amount, 12 for a cost basis), so it must commit; it was refused: {_render(response.issues)}"


# A promote's resolved cost basis over a limit of its column, ``cost_basis_override`` (24, 12): the code and params of
# its refusal. The first two leave the batch going to its end, uncommitted; the last two, past the integer digits,
# stop it right after ``check_decimal_limits``.
PROMOTED_COSTS_OVER_A_LIMIT = [
    pytest.param(COST_13_DECIMALS, DECIMAL_PLACES_EXCEEDED, COST_MAX, id="13-decimals"),
    pytest.param("3333.333333333333", SIGNIFICANT_DIGITS_EXCEEDED, DIGITS_MAX, id="16-significant-digits"),
    pytest.param("1000000000000", INTEGER_DIGITS_EXCEEDED, COST_INTEGER_MAX, id="13-integer-digits"),
    pytest.param("1E+60", INTEGER_DIGITS_EXCEEDED, COST_INTEGER_MAX, id="1E+60"),
]


async def _promotable_pair(world: World) -> tuple[int, int]:
    """A stored pair a promote turns into a TRANSFER (``promote_from``: same asset, other broker, opposite quantity): an
    ADJUSTMENT −1 on ``main`` and an ADJUSTMENT +1 on ``other`` at a manual cost of 100 EUR a unit. Their ids (giving,
    receiving); the caller seeds the unit ``main`` gives (it may not go short)."""
    giving_id = await _seed_position(world, TransactionType.ADJUSTMENT, "-1")
    receiving_id = await _insert(world, broker_id=world.other_id, asset_id=world.asset_id, type=TransactionType.ADJUSTMENT, date=SEED_DAY, quantity=Decimal("1"), amount=Decimal("0"), currency=None, cost_basis_override=Decimal("100"), cost_basis_currency=EUR)
    return giving_id, receiving_id


async def _pair_state(world: World, ids) -> dict[int, tuple]:
    """What a promote changes on the rows ``ids``, as the database holds them: (type, related id, cost basis, currency)."""
    statement = select(Transaction.id, Transaction.type, Transaction.related_transaction_id, Transaction.cost_basis_override, Transaction.cost_basis_currency).where(Transaction.id.in_(list(ids)))
    return {row.id: (row.type, row.related_transaction_id, row.cost_basis_override, row.cost_basis_currency) for row in await world.session.execute(statement)}


def _limit_issues_without_ref(response: TXBatchResponse) -> list[tuple]:
    """The batch's refusals over a column's limit as ``(operation, index, code, field, params)``, sorted: which row a
    promote's ``ref_id`` names is not the subject."""
    return sorted((operation, index, code, field, params) for operation, index, _ref_id, code, field, params in _decimal_issues(response))


class TestAPromotedCostBasisIsChecked:
    """Rule 6 (R13-SEC2): the cost basis a promote resolves (``resolved_fields.cost_basis_override``, the PromoteMergeModal's
    merged value) is checked against the column ``cost_basis_override`` like a create's.

    Today ``_apply_promote_cost_basis`` writes it without a check: the REAL rounds what it cannot keep, and nothing limits
    its magnitude.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    @pytest.mark.parametrize(("amount", "code", "params"), PROMOTED_COSTS_OVER_A_LIMIT)
    async def test_promote_with_a_resolved_cost_basis_over_a_limit_is_refused_on_its_index(self, world, amount, code, params, endpoint):
        """Red today: no issue — ``/commit`` commits both promotes, the second with that cost basis on its receiving leg.

        Contract: two promotes of stored pairs, the second (index 1) resolving a cost basis of ``amount`` EUR: exactly one
        limit issue, ``operation="promote"``, index 1, ``field="cost_basis_override"``, ``code`` with ``params``, its
        English ``error`` naming the field; nothing else; not committed; all four rows as they were stored.
        """
        await _seed_position(world, TransactionType.BUY, "2", amount="-200")
        first = await _promotable_pair(world)
        second = await _promotable_pair(world)
        before = await _pair_state(world, [*first, *second])
        promotes = [{"id_a": first[0], "id_b": first[1]}, {"id_a": second[0], "id_b": second[1], "resolved_fields": {"cost_basis_override": {"code": EUR, "amount": amount}}}]

        response = await _run_never_raising(world, f"a promote resolving a cost basis of {amount} EUR", promotes=promotes, endpoint=endpoint)

        expected = [("promote", 1, code, "cost_basis_override", params)]
        assert _limit_issues_without_ref(response) == expected, f"R13-SEC2, /{endpoint}: the promote resolving a cost basis of {amount} EUR must be refused on its own index with {expected}; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        assert _other_issues(response) == [], f"R13-SEC2, /{endpoint}: only the limit may refuse this batch: {_render(_other_issues(response))}"
        assert response.committed is False, f"R13-SEC2: /{endpoint} refused the batch, yet answered committed"
        _assert_errors_name_their_fields(response)
        after = await _pair_state(world, [*first, *second])
        assert after == before, f"R13-SEC2: the batch was refused, yet the stored rows changed: before {before}, after {after}"

    @pytest.mark.asyncio
    async def test_guard_a_promote_with_a_resolved_cost_basis_of_12_decimals_commits(self, world):
        """Guard: green today and after. A resolved cost basis of 0.000003457312 EUR (12 decimals, the maximum) commits,
        and the receiving leg holds it exactly; the giving leg holds none (decision 47)."""
        await _seed_position(world, TransactionType.BUY, "1", amount="-100")
        giving_id, receiving_id = await _promotable_pair(world)
        promotes = [{"id_a": giving_id, "id_b": receiving_id, "resolved_fields": {"cost_basis_override": {"code": EUR, "amount": "0.000003457312"}}}]

        response = await _run_never_raising(world, "a promote resolving a cost basis of 0.000003457312 EUR", promotes=promotes)

        assert response.committed is True and response.issues == [], f"R13-SEC2: a resolved cost basis of 12 decimals is within the limit, yet the promote was refused: {_render(response.issues)}"
        state = await _pair_state(world, [giving_id, receiving_id])
        expected = {giving_id: (TransactionType.TRANSFER, receiving_id, None, None), receiving_id: (TransactionType.TRANSFER, giving_id, Decimal("0.000003457312"), EUR)}
        assert state == expected, f"The promoted pair reads back {state}: expected {expected}"


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
# RED — RULE 7 (R13-SEC2): CORRUPT ROWS ARE READ WITHOUT RAISING
# ============================================================================


async def _raw(world: World, table: str, column: str, row_id: int) -> tuple[str, object]:
    """SQLite's storage class and the raw value of ``column`` of row ``row_id`` in ``table``, read past every column type."""
    row = (await world.session.execute(text(f"SELECT typeof({column}), {column} FROM {table} WHERE id = :id"), {"id": row_id})).one()
    return row[0], row[1]


async def _corrupt(world: World, row, table: str, column: str, literal: str) -> int:
    """Write ``row`` with the ORM, drop it from the session, and overwrite its ``column`` with the SQLite literal ``literal``
    by raw SQL — as an older version (nothing refused ``Decimal('1E+400')``) or another tool leaves it — so the next load
    reads the file. Its id, once the file is shown to hold that REAL."""
    world.session.add(row)
    await world.session.flush()
    row_id = row.id
    world.session.expunge(row)
    await world.session.execute(text(f"UPDATE {table} SET {column} = {literal} WHERE id = :id"), {"id": row_id})
    held = await _raw(world, table, column, row_id)
    assert held == ("real", float(literal)), f"scaffold: {table}.{column} of row {row_id} holds {held}, not the REAL {literal}"
    return row_id


async def _corrupt_quantity(world: World, broker_id: int, asset_id: int, literal: str) -> int:
    """A BUY of ``asset_id`` on ``broker_id`` whose quantity the file holds as the REAL ``literal``; its id."""
    now = utcnow()
    row = Transaction(broker_id=broker_id, asset_id=asset_id, type=TransactionType.BUY, date=SEED_DAY, quantity=Decimal("1"), amount=Decimal("-1"), currency=EUR, description=f"{world.marker} corrupt", created_at=now, updated_at=now)
    return await _corrupt(world, row, "transactions", "quantity", literal)


async def _corrupt_close(world: World, literal: str) -> int:
    """A price of the test's asset whose close the file holds as the REAL ``literal``; its id."""
    row = PriceHistory(asset_id=world.asset_id, date=SEED_DAY, close=Decimal("1"), currency=EUR, source_plugin_key="MANUAL", fetched_at=utcnow())
    return await _corrupt(world, row, "price_history", "close", literal)


class TestCorruptRowsAreReadWithoutRaising:
    """Rule 7 (R13-SEC2, E's attack): rows whose REAL today's read cannot turn into a Decimal — a quantity of 1e60
    (``InvalidOperation``: padded to 6 decimals in 60 digits), an infinite quantity or close (``TypeError``: the exponent
    ``'F'`` compared with an int). The asset list reads every user's quantities, so one such row answers 500 to every
    user, and the row cannot be deleted through the app, since deleting it loads it.
    """

    @pytest.mark.asyncio
    async def test_the_asset_list_reads_a_quantity_of_1e60_and_an_infinite_one_without_raising(self, world):
        """Red today: ``list_assets`` raises — ``InvalidOperation`` on the REAL 1e60, ``TypeError`` on the inf.

        Contract: no exception; the test's two assets are listed, and the one holding 1e60 on ``main`` reads as held (by
        others, no user being passed): its quantity reads 1E+60. The infinite one, read as None, is not asserted.
        """
        infinite_asset_id = await _new_asset(world, "infinite coin")
        await _corrupt_quantity(world, world.main_id, world.asset_id, HUGE_REAL)
        await _corrupt_quantity(world, world.other_id, infinite_asset_id, INFINITE_REAL)

        try:
            listed = await AssetCRUDService.list_assets(FAAinfoFiltersRequest(search=world.marker), world.session)
        except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
            pytest.fail(f"R13-SEC2: list_assets raised {exc!r} on a quantity the file holds as the REAL {HUGE_REAL} or {INFINITE_REAL}: GET /assets answers 500 to every user")

        flags = {asset.id: (asset.held_by_me, asset.held_by_others) for asset in listed}
        assert {world.asset_id, infinite_asset_id} <= set(flags), f"R13-SEC2: the list searched by the test's marker lacks its assets {world.asset_id} and {infinite_asset_id}: {sorted(flags)}"
        assert flags[world.asset_id] == (False, True), f"R13-SEC2: asset id={world.asset_id} holds a quantity of 1e60 on broker {world.main_id}, which reads 1E+60: held by others (no user being passed); (held_by_me, held_by_others) = {flags[world.asset_id]}"

    @pytest.mark.asyncio
    async def test_a_quantity_of_1e60_loads_as_1e60_and_an_infinite_one_as_none(self, world):
        """Red today: loading either row raises — ``InvalidOperation`` on 1e60, ``TypeError`` on the inf.

        Contract: through ``TransactionService.get_by_ids`` (what the batch loads), the 1e60 row's quantity reads
        ``1E+60`` and the infinite one's None.
        """
        huge_id = await _corrupt_quantity(world, world.main_id, world.asset_id, HUGE_REAL)
        infinite_id = await _corrupt_quantity(world, world.other_id, world.asset_id, INFINITE_REAL)

        try:
            loaded = {row.id: row.quantity for row in await TransactionService(world.session).get_by_ids([huge_id, infinite_id])}
        except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
            pytest.fail(f"R13-SEC2: loading the transactions id={huge_id} (quantity REAL {HUGE_REAL}) and id={infinite_id} (REAL {INFINITE_REAL}) raised {exc!r}")

        assert loaded == {huge_id: Decimal("1E+60"), infinite_id: None}, f"R13-SEC2: the quantities load as {loaded}: expected 1E+60 for id={huge_id} and None for id={infinite_id}"

    @pytest.mark.asyncio
    async def test_a_transaction_of_infinite_quantity_can_be_deleted_through_the_batch(self, world):
        """Red today: the delete loads the row first (``preload_and_authorize`` → ``get_by_ids``), and the load raises
        ``TypeError``: the row cannot leave the database through the app.

        Contract: ``/commit`` with the row's id in ``deletes`` commits with no issue, reports the delete, and the row is
        gone.
        """
        infinite_id = await _corrupt_quantity(world, world.other_id, world.asset_id, INFINITE_REAL)

        response = await _run_never_raising(world, f"the delete of transaction id={infinite_id}, whose quantity the file holds as the REAL {INFINITE_REAL}", deletes=[infinite_id])

        assert response.committed is True and response.issues == [], f"R13-SEC2: the delete of id={infinite_id} must commit; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        assert ("delete", 0) in _in_batch(response), f"R13-SEC2: the delete of id={infinite_id} is not reported: {response.results}"
        remaining = list((await world.session.execute(select(Transaction.id).where(Transaction.id == infinite_id))).scalars())
        assert remaining == [], f"R13-SEC2: the delete of id={infinite_id} was committed, yet the row is still there"

    @pytest.mark.asyncio
    async def test_a_price_whose_close_is_infinite_loads_without_one(self, world):
        """Red today: loading the row raises ``TypeError``.

        Contract: the price row loads, its close None.
        """
        price_id = await _corrupt_close(world, INFINITE_REAL)

        try:
            row = (await world.session.execute(select(PriceHistory).where(PriceHistory.id == price_id))).scalar_one()
        except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
            pytest.fail(f"R13-SEC2: loading the price id={price_id}, whose close the file holds as the REAL {INFINITE_REAL}, raised {exc!r}")

        assert row.close is None, f"R13-SEC2: the price id={price_id} loads a close of {row.close!r}: expected None"


# ============================================================================
# RED AND GUARD — RULE 8 (W-B60): A CASH AMOUNT READS BACK EXACTLY
# ============================================================================

# A cash amount of 15 significant digits, 12 of them before the point (within N63's 15): a double holds it exactly
# enough, and ``'%.6f'`` of that double reads -123456789012.345001.
TWELVE_INTEGER_DIGIT_AMOUNT = "-123456789012.345"


async def _loaded_amount(world: World, tx_id: int) -> object:
    """The amount of row ``tx_id`` as the service loads it (``get_by_ids``), from the database. The object the batch left
    in the session holds the value the batch assigned, not the one read back: it is expired first, so the load fills it
    from the file, through the column's type."""
    cached = await world.session.get(Transaction, tx_id)
    if cached is not None:
        world.session.expire(cached)
    loaded = await TransactionService(world.session).get_by_ids([tx_id])
    assert [row.id for row in loaded] == [tx_id], f"scaffold: get_by_ids([{tx_id}]) loaded {[row.id for row in loaded]}"
    return loaded[0].amount


async def _committed_buy(world: World, cash: str) -> int:
    """A BUY of one unit of the test's asset on ``main`` for ``cash`` EUR, committed through ``/commit``; its id."""
    response = await _run_as_the_endpoint(world, creates=[_row(world, "BUY", "1", cash=cash)])
    assert response.committed is True and response.issues == [], f"scaffold: a BUY of 1 unit for {cash} EUR, within every limit, was refused: {_render(response.issues)}"
    return _created_ids(response)[0]


class TestACashAmountReadsBackExactly:
    """Rule 8 (W-B60): ``Transaction.amount`` reads back the decimal written, with 6 decimals as today.

    Today it is a plain ``Numeric(18, 6)``: SQLAlchemy reads the stored double through ``'%.6f'``, and from about 11
    integer digits the double's noise lands in the 6 decimals. Compared as text, so the 6 decimals are pinned.
    """

    @pytest.mark.asyncio
    async def test_a_cash_amount_of_15_significant_digits_reads_back_exactly(self, world):
        """Red today: the BUY commits, and its cash amount of -123456789012.345 EUR reads back -123456789012.345001, column
        by column and through the service alike.

        Contract (W-B60): -123456789012.345000 both ways: the value sent, with 6 decimals.
        """
        tx_id = await _committed_buy(world, TWELVE_INTEGER_DIGIT_AMOUNT)

        stored = (await _stored(world, [tx_id]))[tx_id]["amount"]
        loaded = await _loaded_amount(world, tx_id)

        reads = {"column by column": str(stored), "through get_by_ids": str(loaded)}
        expected = dict.fromkeys(reads, "-123456789012.345000")
        assert reads == expected, f"W-B60: the BUY id={tx_id} was committed with a cash amount of {TWELVE_INTEGER_DIGIT_AMOUNT} EUR, and reads back {reads}: expected -123456789012.345000, the value sent with 6 decimals"

    @pytest.mark.asyncio
    async def test_the_control_totals_give_the_cash_amount_exactly(self, world):
        """Red today: the control totals read the amount through the column's type, so the broker's EUR line is the
        double's noise, -123456789012.345001 — what a backup would record, and a restore compare.

        Contract (W-B60): the line of the test's broker ``main`` — the only cash it holds is the BUY's — is
        -123456789012.345, in the canonical text of ``ControlTotals.to_json``. Only this broker's lines are read: the
        ledger is the whole lane's.
        """
        await _committed_buy(world, TWELVE_INTEGER_DIGIT_AMOUNT)

        totals = (await compute_control_totals(world.session)).to_json()

        lines = [line for line in totals["cash"] if line["broker_id"] == world.main_id]
        expected = [{"broker_id": world.main_id, "currency": EUR, "balance": "-123456789012.345"}]
        assert lines == expected, f"W-B60: the control totals of broker {world.main_id}, whose only cash is a BUY for {TWELVE_INTEGER_DIGIT_AMOUNT} EUR, give the cash lines {lines}: expected {expected}"

    @pytest.mark.asyncio
    async def test_guard_a_cash_amount_that_reads_well_today_keeps_its_form(self, world):
        """Guard: green today and after. Cash amounts of -100 and -1234.5 EUR read back -100.000000 and -1234.500000,
        column by column and through the service, as ``Numeric(18, 6)`` reads them today."""
        ids = {cash: await _committed_buy(world, cash) for cash in ("-100", "-1234.5")}

        stored = await _stored(world, ids.values())
        reads = {cash: (str(stored[tx_id]["amount"]), str(await _loaded_amount(world, tx_id))) for cash, tx_id in ids.items()}

        expected = {"-100": ("-100.000000",) * 2, "-1234.5": ("-1234.500000",) * 2}
        assert reads == expected, f"W-B60: cash amounts sent → (column by column, through get_by_ids): {reads}; expected {expected}, today's form"


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
    so ``GET /transactions/types`` lists them in ``validation_codes``; and so is the integer-digit code of R13-SEC2."""

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

    def test_validation_code_has_the_integer_digits_code(self):
        """Red today: ``TXValidationCode`` has no ``INTEGER_DIGITS_EXCEEDED`` (rule 6, R13-SEC2): the app could not map
        the refusal to ``transactions.errors.integerDigitsExceeded``."""
        member = getattr(TXValidationCode, "INTEGER_DIGITS_EXCEEDED", None)

        assert member is not None and member.value == INTEGER_DIGITS_EXCEEDED, f"R13-SEC2: TXValidationCode.INTEGER_DIGITS_EXCEEDED is {member!r}: expected the value {INTEGER_DIGITS_EXCEEDED!r}"

    def test_transaction_types_lists_the_integer_digits_code(self):
        """Red today: ``GET /transactions/types`` does not list ``integerDigitsExceeded`` in ``validation_codes``."""
        response = TXTypesResponse(transaction_types=list(TX_TYPE_METADATA.values()), event_types=EVENT_TYPE_METADATA)

        listed = {info.code for info in response.validation_codes}

        assert INTEGER_DIGITS_EXCEEDED in listed, f"R13-SEC2: GET /transactions/types does not list {INTEGER_DIGITS_EXCEEDED!r} in validation_codes"
