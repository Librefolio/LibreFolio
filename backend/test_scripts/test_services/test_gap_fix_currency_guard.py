"""
The gap-fix refuses a ledger whose cash is in no ISO 4217 code — lot E-19a (workstream E), item 5.

The gap-fix (``backend.app.services.brim.brim_gap_fix.compute_gap_fix``) compares the cash the bank states, per ISO 4217
code, with LibreFolio's balances at the same date, per stored currency. Before E-18 a transaction could be stored with
its cash in ``978``, ``eur`` or ``EURO``: the gap-fix then sees no EUR where the bank sees some, and proposes a
correction that duplicates a row LibreFolio already has. W-B74 refuses a ledger whose values are no number; E-19a, as
the release coordinator decided on 17/10, refuses one whose cash currency is no canonical ISO code in the same way:

- ``compute_gap_fix`` raises ``BRIMLedgerUnreadable`` (``backend.app.services.brim.brim_report_sets``: ``status_code``
  409, ``code`` ``ledger_unreadable``) when the broker's transactions it compares hold a ``Transaction.currency`` that
  is not canonical (``iso_currency_code(value) == value`` fails);
- the scope is the comparison's: the broker's own rows dated on or before the checkpoint's ``as_of``, without
  ``pending_delete_tx_ids``;
- the message contains ``ISO 4217`` and quotes each such code — at most 16 characters of it, ``…`` past them — with its
  suggestion (``'978' (EUR)``), or ``(no ISO code)`` without one. At most 5 codes, sorted, then ``and N more``;
- a ledger that W-B74 refuses already keeps W-B74's message (``not a number``).

Every test has a private in-memory SQLite database with the ORM schema, two brokers and two assets, as
``test_brim_gap_fix.py`` does: never the shared test database. The bad codes are written by raw SQL (``UPDATE``), as
``_make_unreadable`` writes W-B74's values, so no validator runs. The ledger of each test is the same small one;
expected values are written out.

"RED" tests (marked ``# red until E-19a``) fail before E-19a: the gap-fix answers, comparing the bank with balances
under the bad code. "GUARD (green today)" tests pass before and after: an ISO-only ledger answers as before, a bad
code the comparison never reaches refuses nothing, and W-B74's refusal keeps its message.

Pure: no server, no network, no shared database.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel

from backend.app.db.models import Asset, Broker, Transaction, TransactionType
from backend.app.schemas.brim import BRIMAbsorbed, BRIMCheckpoint, BRIMGapFixRequest, BRIMTruthCash, BRIMTruthPosition
from backend.app.services.brim import brim_report_sets
from backend.app.services.brim.brim_gap_fix import compute_gap_fix

BROKER_ID = 42
OTHER_BROKER_ID = 43
ASSET_A, ASSET_B = 101, 102
GENERIC_CODE = "broker_generic_csv"
LEDGER_UNREADABLE = ("ledger_unreadable", 409)

#: The checkpoint's day. The ledger's own broker holds, at its end: EUR 600, USD 50, CHF 25, A 10, B 3.
AS_OF = date(2024, 3, 31)
BANK_CASH = {"EUR": "600", "USD": "50", "CHF": "25"}
BANK_POSITIONS = {ASSET_A: "10", ASSET_B: "3"}

DEPOSIT, BUY, ADJUSTMENT = TransactionType.DEPOSIT, TransactionType.BUY, TransactionType.ADJUSTMENT

# =============================================================================
# THE PRIVATE DATABASE AND ITS LEDGER
# =============================================================================


@asynccontextmanager
async def _private_database() -> AsyncIterator[AsyncSession]:
    """A private in-memory SQLite database with the ORM schema, both brokers and both assets."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        session.add_all([Broker(id=broker_id, name=f"Gap-fix currency broker {broker_id}") for broker_id in (BROKER_ID, OTHER_BROKER_ID)])
        session.add_all([Asset(id=asset_id, display_name=f"Gap-fix currency asset {asset_id}", currency="EUR") for asset_id in (ASSET_A, ASSET_B)])
        await session.commit()
        yield session
    finally:
        await session.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """This test's own database: never the shared test database."""
    async with _private_database() as session:
        yield session


def _saved(tx_type: TransactionType, day: str, *, amount: str = "0", currency: Optional[str] = None, asset_id: Optional[int] = None, quantity: str = "0", broker_id: int = BROKER_ID) -> Transaction:
    return Transaction(broker_id=broker_id, type=tx_type, date=date.fromisoformat(day), amount=Decimal(amount), currency=currency, asset_id=asset_id, quantity=Decimal(quantity))


async def _add(session: AsyncSession, *rows: Transaction) -> list[Transaction]:
    session.add_all(rows)
    await session.commit()
    return list(rows)


async def _seed_ledger(session: AsyncSession) -> Dict[str, Transaction]:
    """The ledger, by name. Own broker at the end of ``AS_OF``: EUR 600, USD 50, CHF 25 (deposited on ``AS_OF`` itself),
    A 10, B 3 (an adjustment without cash: its currency is NULL). Later, on 2024-05-02, EUR 70 more. The other broker
    holds EUR 7777, which never reaches the own broker's balances."""
    rows = {
        "deposit_eur": _saved(DEPOSIT, "2024-01-10", amount="1000", currency="EUR"),
        "deposit_usd": _saved(DEPOSIT, "2024-02-01", amount="50", currency="USD"),
        "buy_a": _saved(BUY, "2024-02-15", amount="-400", currency="EUR", asset_id=ASSET_A, quantity="10"),
        "adjustment_b": _saved(ADJUSTMENT, "2024-03-01", asset_id=ASSET_B, quantity="3"),
        "deposit_chf": _saved(DEPOSIT, "2024-03-31", amount="25", currency="CHF"),
        "late_deposit": _saved(DEPOSIT, "2024-05-02", amount="70", currency="EUR"),
        "foreign_deposit": _saved(DEPOSIT, "2024-01-15", amount="7777", currency="EUR", broker_id=OTHER_BROKER_ID),
    }
    await _add(session, *rows.values())
    return rows


async def _write_raw(session: AsyncSession, row: Transaction, **columns: Any) -> None:
    """Overwrite ``columns`` of ``row`` by raw SQL, as an older version left them (no validator runs), and check what
    the case rests on: SQLite keeps each value as written, and the row reads it back. The row is expired, then re-read."""
    row_id = row.id
    assignments = ", ".join(f"{column} = :{column}" for column in columns)
    await session.execute(text(f"UPDATE transactions SET {assignments} WHERE id = :row_id"), {**columns, "row_id": row_id})
    await session.commit()
    stored = (await session.execute(text(f"SELECT {', '.join(columns)} FROM transactions WHERE id = :row_id"), {"row_id": row_id})).one()
    assert tuple(stored) == tuple(columns.values()), f"setup: row id={row_id} must hold {columns}, it holds {tuple(stored)}"
    session.expire(row)
    loaded = await session.get(Transaction, row_id, populate_existing=True)
    read = {column: getattr(loaded, column) for column in columns if column.endswith("currency")}
    assert read == {column: value for column, value in columns.items() if column.endswith("currency")}, f"setup: row id={row_id} must read back {columns}, it reads {read}"


async def _plant(session: AsyncSession, row: Transaction, code: str) -> None:
    """``row``'s cash currency becomes ``code``, stored as text."""
    row_id = row.id
    await _write_raw(session, row, currency=code)
    kind = (await session.execute(text("SELECT typeof(currency) FROM transactions WHERE id = :row_id"), {"row_id": row_id})).scalar_one()
    assert kind == "text", f"setup: the currency of id={row_id} must be stored as text, it is {kind}"


async def _make_unreadable(session: AsyncSession, row: Transaction, column: str) -> None:
    """W-B74's case, as ``test_brim_gap_fix.py`` writes it: ``column`` holds the text 'n/a', which reads None."""
    row_id = row.id
    await session.execute(text(f"UPDATE transactions SET {column} = 'n/a' WHERE id = :row_id"), {"row_id": row_id})
    await session.commit()
    session.expire(row)
    loaded = await session.get(Transaction, row_id, populate_existing=True)
    assert getattr(loaded, column) is None, f"setup: RealDecimal must read the 'n/a' of id={row_id} as None (W-B58)"


# =============================================================================
# THE REQUEST, THE ANSWER, THE REFUSAL
# =============================================================================


def _checkpoint(cash: Dict[str, str] = BANK_CASH) -> BRIMCheckpoint:
    """The bank's truth at the end of ``AS_OF``: ``cash`` and the positions the ledger holds."""
    return BRIMCheckpoint(
        as_of=AS_OF,
        kind="gap",
        cash=[BRIMTruthCash(currency=code, amount=Decimal(amount)) for code, amount in cash.items()],
        positions=[BRIMTruthPosition(asset_id=asset_id, quantity=Decimal(quantity), exactness="exact") for asset_id, quantity in BANK_POSITIONS.items()],
        absorbed=BRIMAbsorbed(),
    )


def _request(*, cash: Dict[str, str] = BANK_CASH, pending_delete_tx_ids: Sequence[int] = ()) -> BRIMGapFixRequest:
    return BRIMGapFixRequest(broker_id=BROKER_ID, plugin_code=GENERIC_CODE, checkpoints=[_checkpoint(cash)], pending_delete_tx_ids=list(pending_delete_tx_ids))


def _cash_rows(response: Any) -> Dict[str, Tuple[Decimal, Decimal, Decimal]]:
    """``{currency: (bank, librefolio, difference)}`` of the one checkpoint result."""
    assert [item.as_of for item in response.checkpoints] == [AS_OF], f"one result expected, for {AS_OF}: {[item.as_of for item in response.checkpoints]}"
    return {row.currency: (row.bank, row.librefolio, row.difference) for row in response.checkpoints[0].cash}


def _agreeing(cash: Dict[str, str]) -> Dict[str, Tuple[Decimal, Decimal, Decimal]]:
    """The cash rows of a checkpoint where LibreFolio agrees with the bank."""
    return {code: (Decimal(amount), Decimal(amount), Decimal(0)) for code, amount in cash.items()}


def _answer_today(response: Any) -> str:
    """What the gap-fix answered, for a failure message: the cash compared and the corrections proposed."""
    proposed = [(item.type.value, item.cash.code if item.cash else None, item.cash.amount if item.cash else None) for result in response.checkpoints for item in result.proposals]
    return f"cash (bank, LibreFolio, difference) {_cash_rows(response)} and the proposals {proposed}"


async def _assert_answers(session: AsyncSession, cash: Dict[str, str] = BANK_CASH, pending_delete_tx_ids: Sequence[int] = ()) -> None:
    """The gap-fix answers — no refusal —, and LibreFolio agrees with the bank: nothing to propose."""
    try:
        response = await compute_gap_fix(session, _request(cash=cash, pending_delete_tx_ids=pending_delete_tx_ids))
    except brim_report_sets.BRIMSetError as exc:
        pytest.fail(f"the gap-fix must answer, the bad code is outside what it compares; it refused with {type(exc).__name__} ({exc.code}): {exc.message}", pytrace=False)
    assert _cash_rows(response) == _agreeing(cash)
    assert [result.proposals for result in response.checkpoints] == [[]]


async def _refusal(session: AsyncSession, why: str, pending_delete_tx_ids: Sequence[int] = ()) -> str:
    """The message of the gap-fix's ``BRIMLedgerUnreadable``; the test fails, red, when the gap-fix answers."""
    try:
        response = await compute_gap_fix(session, _request(pending_delete_tx_ids=pending_delete_tx_ids))
    except Exception as exc:  # the refusal, checked below
        raised = exc
    else:
        pytest.fail(f"red until E-19a: {why}, so compute_gap_fix must refuse with BRIMLedgerUnreadable (409, ledger_unreadable); today it answers {_answer_today(response)}", pytrace=False)
    found = (isinstance(raised, brim_report_sets.BRIMLedgerUnreadable), (getattr(raised, "code", None), getattr(raised, "status_code", None)))
    assert found == (True, LEDGER_UNREADABLE), f"BRIMLedgerUnreadable (ledger_unreadable, 409) expected, got {type(raised).__module__}.{type(raised).__qualname__} {found}: {raised!r}"
    message = getattr(raised, "message", str(raised))
    assert "ISO 4217" in message, f"the refusal must name the rule, ISO 4217: {message!r}"
    return message


# =============================================================================
# 1. REFUSED: a cash currency the comparison reaches is no canonical ISO code
# =============================================================================


@pytest.mark.asyncio
async def test_numeric_code_refuses_naming_eur(db_session: AsyncSession) -> None:  # red until E-19a
    """GFC-001 — RED: two rows of the broker hold their cash in ``978`` (EUR's numeric code): refused, quoting ``'978' (EUR)`` once.

    Today the gap-fix compares the bank's EUR 600 and USD 50 with balances that miss both rows (EUR −400, USD 0), and
    proposes deposits of cash the ledger already holds.
    """
    ledger = await _seed_ledger(db_session)
    await _plant(db_session, ledger["deposit_usd"], "978")
    await _plant(db_session, ledger["deposit_eur"], "978")
    message = await _refusal(db_session, "two rows of the broker hold their cash in '978'")
    assert "'978' (EUR)" in message, message
    assert message.count("'978'") == 1, f"a code is listed once, however many rows hold it: {message!r}"


@pytest.mark.asyncio
async def test_lower_case_code_refuses_naming_eur(db_session: AsyncSession) -> None:  # red until E-19a
    """GFC-002 — RED: a row holding its cash in ``eur`` is refused, quoting ``'eur' (EUR)``: the code as stored, with its ISO code."""
    ledger = await _seed_ledger(db_session)
    await _plant(db_session, ledger["buy_a"], "eur")
    message = await _refusal(db_session, "a row of the broker holds its cash in 'eur'")
    assert "'eur' (EUR)" in message, message


@pytest.mark.asyncio
async def test_code_without_suggestion_refuses_saying_so(db_session: AsyncSession) -> None:  # red until E-19a
    """GFC-003 — RED: a row holding its cash in ``BTC`` (no ISO code at all) is refused, quoting ``'BTC' (no ISO code)``."""
    ledger = await _seed_ledger(db_session)
    await _plant(db_session, ledger["deposit_usd"], "BTC")
    message = await _refusal(db_session, "a row of the broker holds its cash in 'BTC'")
    assert "'BTC' (no ISO code)" in message, message


@pytest.mark.asyncio
async def test_code_dated_on_the_checkpoint_day_is_compared(db_session: AsyncSession) -> None:  # red until E-19a
    """GFC-004 — RED: the scope includes ``as_of`` itself: the CHF deposit of 2024-03-31, its cash in ``756`` (CHF's numeric code), is refused as ``'756' (CHF)``."""
    ledger = await _seed_ledger(db_session)
    await _plant(db_session, ledger["deposit_chf"], "756")
    message = await _refusal(db_session, "the row dated as_of itself holds its cash in '756'")
    assert "'756' (CHF)" in message, message


#: Seven numeric codes whose order is the same as their ISO codes': ALL, AUD, CAD, DKK, HUF, then JPY and USD.
SEVEN_CODES = (("008", "ALL"), ("036", "AUD"), ("124", "CAD"), ("208", "DKK"), ("348", "HUF"), ("392", "JPY"), ("840", "USD"))


@pytest.mark.asyncio
async def test_at_most_five_codes_then_how_many_more(db_session: AsyncSession) -> None:  # red until E-19a
    """GFC-005 — RED: seven distinct bad codes: the first five, sorted (``'008' (ALL)`` … ``'348' (HUF)``), in that order,
    then ``and 2 more``; ``'392'`` and ``'840'`` are not listed."""
    await _seed_ledger(db_session)
    extra = await _add(db_session, *[_saved(DEPOSIT, f"2024-03-{day:02d}", amount="1", currency="EUR") for day in range(10, 10 + len(SEVEN_CODES))])
    for row, (code, _) in zip(extra, reversed(SEVEN_CODES), strict=True):
        await _plant(db_session, row, code)
    message = await _refusal(db_session, "seven rows of the broker hold their cash in seven numeric codes")
    listed = [f"'{code}' ({iso})" for code, iso in SEVEN_CODES[:5]]
    positions = [message.find(item) for item in listed]
    assert all(position >= 0 for position in positions), f"the first five codes, with their ISO codes, must be listed: {listed} in {message!r}"
    assert positions == sorted(positions), f"the codes must be listed sorted: {message!r}"
    assert not [code for code, _ in SEVEN_CODES[5:] if f"'{code}'" in message], f"past five codes, none is listed: {message!r}"
    assert "and 2 more" in message, message


@pytest.mark.asyncio
async def test_long_code_is_quoted_on_16_characters(db_session: AsyncSession) -> None:  # red until E-19a
    """GFC-006 — RED: a cash currency of 40 characters is quoted on its first 16, then ``…``, with ``(no ISO code)``."""
    ledger = await _seed_ledger(db_session)
    await _plant(db_session, ledger["deposit_usd"], "Q" * 40)
    message = await _refusal(db_session, "a row of the broker holds its cash in a 40-character text")
    assert "Q" * 16 in message and "Q" * 17 not in message, f"16 characters of the code, never more: {message!r}"
    assert "…" in message and "(no ISO code)" in message, message


# =============================================================================
# 2. NOT REFUSED: what the comparison never reaches, and W-B74 first
# =============================================================================


@pytest.mark.asyncio
async def test_iso_only_ledger_answers(db_session: AsyncSession) -> None:
    """GFC-010 — GUARD (green today): a ledger in ISO codes only (and a row without cash, its currency NULL) answers: the
    bank and LibreFolio agree, nothing to propose."""
    await _seed_ledger(db_session)
    await _assert_answers(db_session)


@pytest.mark.asyncio
@pytest.mark.parametrize("planted", ["late_deposit", "foreign_deposit"], ids=["dated-after-as_of", "of-another-broker"])
async def test_bad_code_outside_the_comparison_refuses_nothing(db_session: AsyncSession, planted: str) -> None:
    """GFC-011 — GUARD (green today): ``978`` on a row dated after ``as_of`` (2024-05-02), or on a row of another broker, refuses nothing."""
    ledger = await _seed_ledger(db_session)
    await _plant(db_session, ledger[planted], "978")
    await _assert_answers(db_session)


@pytest.mark.asyncio
async def test_bad_code_on_a_pending_delete_refuses_nothing(db_session: AsyncSession) -> None:
    """GFC-012 — GUARD (green today): ``978`` on the USD deposit, which the editor is deleting (``pending_delete_tx_ids``),
    refuses nothing: LibreFolio's state at ``as_of`` is without it, EUR 600 and CHF 25."""
    ledger = await _seed_ledger(db_session)
    deposit_usd_id = ledger["deposit_usd"].id
    await _plant(db_session, ledger["deposit_usd"], "978")
    await _assert_answers(db_session, cash={"EUR": "600", "CHF": "25"}, pending_delete_tx_ids=[deposit_usd_id])


@pytest.mark.asyncio
async def test_bad_cost_basis_currency_is_not_cash(db_session: AsyncSession) -> None:
    """GFC-013 — GUARD (green today): the guard reads the cash currency (``Transaction.currency``) only. A cost basis in
    ``978`` on the B adjustment (no cash, nothing the gap-fix compares) refuses nothing."""
    ledger = await _seed_ledger(db_session)
    await _write_raw(db_session, ledger["adjustment_b"], cost_basis_override=7, cost_basis_currency="978")
    await _assert_answers(db_session)


@pytest.mark.asyncio
async def test_value_that_is_no_number_keeps_its_own_refusal(db_session: AsyncSession) -> None:
    """GFC-014 — GUARD (green today): a ledger with a value that is no number (W-B74: the BUY's amount reads None) and a
    ``978`` cash currency is refused with W-B74's message, ``not a number``, not with the currency one."""
    ledger = await _seed_ledger(db_session)
    await _make_unreadable(db_session, ledger["buy_a"], "amount")
    await _plant(db_session, ledger["deposit_usd"], "978")
    with pytest.raises(brim_report_sets.BRIMLedgerUnreadable) as refused:
        await compute_gap_fix(db_session, _request())
    message = refused.value.message
    assert (refused.value.code, refused.value.status_code) == LEDGER_UNREADABLE
    assert "not a number" in message, message
    assert "ISO 4217" not in message and "'978'" not in message, f"W-B74's message, not the currency one: {message!r}"


@pytest.mark.asyncio
async def test_fixture_guard_planting(db_session: AsyncSession) -> None:
    """GFC-015 — GUARD (green today): this file's own setup works — the ledger holds what ``_seed_ledger`` says, and a
    planted code is stored and read back as written, the other rows untouched. Without it, a red could come from here."""
    ledger = await _seed_ledger(db_session)
    ids = {name: row.id for name, row in ledger.items()}
    await _plant(db_session, ledger["deposit_usd"], "Q" * 40)
    rows = (await db_session.execute(text("SELECT id, broker_id, date, currency FROM transactions ORDER BY id"))).all()
    assert len(rows) == len(ledger)
    by_id = {row_id: (broker_id, str(day), currency) for row_id, broker_id, day, currency in rows}
    assert by_id[ids["deposit_usd"]] == (BROKER_ID, "2024-02-01", "Q" * 40)
    assert by_id[ids["adjustment_b"]] == (BROKER_ID, "2024-03-01", None)
    assert by_id[ids["foreign_deposit"]] == (OTHER_BROKER_ID, "2024-01-15", "EUR")
    assert [by_id[ids[name]][2] for name in ("deposit_eur", "buy_a", "deposit_chf", "late_deposit")] == ["EUR", "EUR", "CHF", "EUR"]
