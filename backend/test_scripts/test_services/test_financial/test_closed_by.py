"""MF-CB (developer request 31/10) — how a closed position closed: ``AssetPeriodContribution.closed_by`` and
``closed_to_broker_id``.

The Performance table shows a position closed in the period as «sold» from ``is_fully_sold``. After a TRANSFER of the
whole position from broker A to broker B the frontend cannot tell it from a sale. Two new fields of the row
(``PortfolioService.get_positions_contribution``, carried unchanged by ``get_report`` with
``include_positions_contribution=True``):

- ``closed_by``: ``"SELL" | "TRANSFER" | "ADJUSTMENT" | None`` — only on a row with ``is_fully_sold`` whose position was
  ever opened: the type of the movement after which the quantity (at the run's share, ``holding_window.quantity_moves``)
  fell to ``QUANTITY_DUST_THRESHOLD`` or below for the last time — ``holding_window.closing_move``, the move
  ``closed_position_window`` dates. None on a row still held, on an income/fees-only row, on a position never opened;
- ``closed_to_broker_id``: only with ``closed_by == "TRANSFER"``: the broker of the paired transaction
  (``related_transaction_id``) when the user has access to it, in the requested ``broker_ids`` or not; None when the
  pair is missing (an orphan) or its broker is not the user's (never another user's broker id).

No number changes: every row asserted here first equals the figures of HEAD bb6085662 (``_TODAY``, captured on HEAD from
these very books), the two new fields and the identity fields (ids, names) aside; only then are the new fields read, by
plain attribute access — so on HEAD every test is red on ``AttributeError: 'AssetPeriodContribution' object has no
attribute 'closed_by'`` (or ``closed_to_broker_id``), never on its setup.

- ``TestSell`` (a) — a full SELL in the period: ``"SELL"``, no broker.
- ``TestTransfer`` (b) — a full TRANSFER A → B, the pair linked both ways (as ``batch_creates`` links it), the user OWNER
  of both: row A ``"TRANSFER"`` to B, row B held (None, None); with ``broker_ids=[A]`` only, still B; through
  ``get_report`` the same.
- ``TestAdjustment`` (c) — an outgoing ADJUSTMENT to zero: ``"ADJUSTMENT"``, no broker.
- ``TestMixedExits`` (d) — 6 of 10 transferred to B, the other 4 sold: ``"SELL"``; 4 sold then 6 transferred:
  ``"TRANSFER"`` to B; both exits on the same day: the later by id (replay order).
- ``TestTransferOutOfReach`` (e) — the pair at broker C of ANOTHER user, no access for this one (written at the DB level):
  ``"TRANSFER"`` with no broker; an orphan TRANSFER (its pair deleted, ``related_transaction_id`` None): the same.
- ``TestNotClosed`` (f) — an open position: (None, None); an income-only row (a DIVIDEND on an asset the broker never
  held, the second loop of the service, ``is_fully_sold`` True): (None, None).
- ``TestClosedBeforeThePeriod`` (g) — sold before the period's start, listed because a DIVIDEND falls inside the period:
  ``"SELL"``, it says how the position closed.

The book, on a private SQLite file under ``tmp_path`` (the app schema, ``SQLModel.metadata.create_all``, an engine of its
own, NullPool, disposed at teardown): brokers A and B of the user (OWNER, 100 %), broker C of another user; X and Z EUR
stocks. Every book has DEPOSIT 10000 at A on 02-26 and BUY 10 X for 1000 at A on 02-27; each scenario adds its rows.
An arriving TRANSFER leg carries the frozen per-unit cost the product writes on it (``cost_basis_override`` 100 EUR):
without it the receiving row's cost is incomplete and its unrealized and period P&L are None. The period is
(03-04, 03-14].

Isolation: PURE with respect to the lane — no session on the lane's database, no server, no network. The engine's blob
cache and the report's L2 cache (process-global) are emptied around each test.

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory); alone:
``./dev.py test services closed-by``.

Reference: backend/app/services/portfolio/portfolio_service.py (get_positions_contribution), backend/app/schemas/portfolio.py
(AssetPeriodContribution), backend/app/services/financial_math/holding_window.py (quantity_moves, closed_position_window).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.base import SQLModel  # every model, for create_all; importing backend.app.db brings the session module and its PRAGMA listener
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.schemas.common import OpenDateRangeModel
from backend.app.schemas.portfolio import PortfolioReportQuery
from backend.app.services.portfolio import report as report_module
from backend.app.services.portfolio.portfolio_service import PortfolioService
from backend.test_scripts.test_utils import print_section, print_success

EUR = "EUR"

DEP = date(2024, 2, 26)
BUY = date(2024, 2, 27)
EARLY = date(2024, 2, 29)
START = date(2024, 3, 4)
D3 = date(2024, 3, 6)
D4 = date(2024, 3, 8)
LAST_QUOTE = date(2024, 3, 13)
END = date(2024, 3, 14)

#: How many differing fields an assertion message shows.
_DIFF_SHOWN = 12
#: The fields that name a row rather than measure it: the ids are asserted on their own, the names carry the book's tag.
_IDENTITY = {"asset_id", "broker_id", "asset_name", "broker_name", "asset_ticker"}
#: The fields MF-CB adds: excluded from the comparison with HEAD's figures (absent there).
_NEW_FIELDS = {"closed_by", "closed_to_broker_id"}

# (label, broker, asset, type, day, quantity, amount, currency)
_BASE_ROWS = (
    ("dep_A", "A", None, TransactionType.DEPOSIT, DEP, "0", "10000", EUR),
    ("buy_X", "A", "X", TransactionType.BUY, BUY, "10", "-1000", EUR),
)
#: The per-unit cost every arriving TRANSFER leg carries (``cost_basis_override``), as the product freezes it: the BUY's.
_TRANSFER_IN_UNIT_COST = Decimal("100")
# (asset, day, close)
_CLOSES = (("X", BUY, "100"), ("X", EARLY, "102"), ("X", START, "104"), ("X", D3, "110"), ("X", D4, "105"), ("X", LAST_QUOTE, "108"), ("Z", BUY, "50"), ("Z", LAST_QUOTE, "50"))


@dataclass(frozen=True)
class _Scenario:
    rows: tuple = ()
    #: label pairs linked both ways by related_transaction_id
    links: tuple = ()


_SCENARIOS: dict[str, _Scenario] = {
    # (a) a full SELL inside the period
    "sell": _Scenario(rows=(("sell_X", "A", "X", TransactionType.SELL, D3, "-10", "1100", EUR),)),
    # (b) a full TRANSFER A -> B, the pair linked both ways
    "transfer": _Scenario(
        rows=(("tr_out", "A", "X", TransactionType.TRANSFER, D3, "-10", "0", None), ("tr_in", "B", "X", TransactionType.TRANSFER, D3, "10", "0", None)),
        links=(("tr_out", "tr_in"),),
    ),
    # (c) an outgoing ADJUSTMENT to zero
    "adjustment": _Scenario(rows=(("adj_X", "A", "X", TransactionType.ADJUSTMENT, D3, "-10", "0", None),)),
    # (d) 6 transferred to B on D3, the other 4 sold on D4
    "transfer_then_sell": _Scenario(
        rows=(
            ("tr_out", "A", "X", TransactionType.TRANSFER, D3, "-6", "0", None),
            ("tr_in", "B", "X", TransactionType.TRANSFER, D3, "6", "0", None),
            ("sell_X", "A", "X", TransactionType.SELL, D4, "-4", "420", EUR),
        ),
        links=(("tr_out", "tr_in"),),
    ),
    # (d) 4 sold on D3, the other 6 transferred to B on D4
    "sell_then_transfer": _Scenario(
        rows=(
            ("sell_X", "A", "X", TransactionType.SELL, D3, "-4", "440", EUR),
            ("tr_out", "A", "X", TransactionType.TRANSFER, D4, "-6", "0", None),
            ("tr_in", "B", "X", TransactionType.TRANSFER, D4, "6", "0", None),
        ),
        links=(("tr_out", "tr_in"),),
    ),
    # (d) both exits on D3: the transfer written first (lower id), the sale after it
    "same_day_transfer_first": _Scenario(
        rows=(
            ("tr_out", "A", "X", TransactionType.TRANSFER, D3, "-6", "0", None),
            ("tr_in", "B", "X", TransactionType.TRANSFER, D3, "6", "0", None),
            ("sell_X", "A", "X", TransactionType.SELL, D3, "-4", "440", EUR),
        ),
        links=(("tr_out", "tr_in"),),
    ),
    # (d) both exits on D3: the sale written first (lower id), the transfer after it
    "same_day_sell_first": _Scenario(
        rows=(
            ("sell_X", "A", "X", TransactionType.SELL, D3, "-4", "440", EUR),
            ("tr_out", "A", "X", TransactionType.TRANSFER, D3, "-6", "0", None),
            ("tr_in", "B", "X", TransactionType.TRANSFER, D3, "6", "0", None),
        ),
        links=(("tr_out", "tr_in"),),
    ),
    # (e) the pair at broker C, another user's
    "transfer_to_stranger": _Scenario(
        rows=(("tr_out", "A", "X", TransactionType.TRANSFER, D3, "-10", "0", None), ("tr_in", "C", "X", TransactionType.TRANSFER, D3, "10", "0", None)),
        links=(("tr_out", "tr_in"),),
    ),
    # (e) an orphan TRANSFER: its pair was deleted with its broker, related_transaction_id None
    "orphan_transfer": _Scenario(rows=(("tr_out", "A", "X", TransactionType.TRANSFER, D3, "-10", "0", None),)),
    # (f) still open; and a DIVIDEND on Z, never held at A (the income-only row)
    "open_and_income_only": _Scenario(rows=(("div_Z", "A", "Z", TransactionType.DIVIDEND, D3, "0", "7", EUR),)),
    # (g) sold before the period's start, a DIVIDEND inside it
    "closed_before": _Scenario(rows=(("sell_X", "A", "X", TransactionType.SELL, EARLY, "-10", "1020", EUR), ("div_X", "A", "X", TransactionType.DIVIDEND, D3, "0", "5", EUR))),
}


# =============================================================================
# THE BOOK — a private SQLite file
# =============================================================================


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    user_id: int
    broker_ids: dict[str, int]
    asset_ids: dict[str, int]
    tx_ids: dict[str, int]

    def scope(self, labels: str) -> list[int]:
        return sorted(self.broker_ids[label] for label in labels)


async def _seed(engine: AsyncEngine, scenario: _Scenario) -> _Book:
    """The base rows and the scenario's; the user OWNER of A and B at 100 %, another user OWNER of C."""
    tag = uuid4().hex[:12]
    async with AsyncSession(engine, expire_on_commit=False) as session:
        me = User(username=f"mfcb_me_{tag}", email=f"mfcb_me_{tag}@test.com", hashed_password="fakehash", is_active=True)
        stranger = User(username=f"mfcb_other_{tag}", email=f"mfcb_other_{tag}@test.com", hashed_password="fakehash", is_active=True)
        brokers = {label: Broker(name=f"MF-CB closed by {label} {tag}") for label in ("A", "B", "C")}
        assets = {label: Asset(display_name=f"MF-CB closed by {label} {tag}", currency=EUR, asset_type=AssetType.STOCK) for label in ("X", "Z")}
        session.add_all([me, stranger, *brokers.values(), *assets.values()])
        await session.flush()
        session.add_all(
            [
                BrokerUserAccess(broker_id=brokers["A"].id, user_id=me.id, role=UserRole.OWNER, share_percentage=Decimal("1")),
                BrokerUserAccess(broker_id=brokers["B"].id, user_id=me.id, role=UserRole.OWNER, share_percentage=Decimal("1")),
                BrokerUserAccess(broker_id=brokers["C"].id, user_id=stranger.id, role=UserRole.OWNER, share_percentage=Decimal("1")),
                *(PriceHistory(asset_id=assets[asset].id, date=day, open=Decimal(close), high=Decimal(close), low=Decimal(close), close=Decimal(close), volume=Decimal("1"), currency=EUR, source_plugin_key="mfcb_closed_by_test") for asset, day, close in _CLOSES),
            ]
        )
        await session.flush()
        rows: dict[str, Transaction] = {}
        # One flush per row: the ids follow the order of the table, which the same-day cases rely on.
        for label, broker, asset, tx_type, day, quantity, amount, currency in (*_BASE_ROWS, *scenario.rows):
            rows[label] = Transaction(broker_id=brokers[broker].id, asset_id=assets[asset].id if asset else None, type=tx_type, date=day, quantity=Decimal(quantity), amount=Decimal(amount), currency=currency)
            if tx_type == TransactionType.TRANSFER and Decimal(quantity) > 0:
                # The frozen per-unit cost the product writes on an arriving leg (the BUY's 100 EUR a unit)
                rows[label].cost_basis_override = _TRANSFER_IN_UNIT_COST
                rows[label].cost_basis_currency = EUR
            session.add(rows[label])
            await session.flush()
        for left, right in scenario.links:
            rows[left].related_transaction_id = rows[right].id
            rows[right].related_transaction_id = rows[left].id
        await session.commit()
        return _Book(
            engine=engine,
            user_id=me.id,
            broker_ids={label: broker.id for label, broker in brokers.items()},
            asset_ids={label: asset.id for label, asset in assets.items()},
            tx_ids={label: row.id for label, row in rows.items()},
        )


@asynccontextmanager
async def _private_book(directory: Path, scenario: str) -> AsyncIterator[_Book]:
    """The app schema and the scenario's ledger on a private SQLite file under ``directory``; the engine disposed after."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / 'mfcb_closed_by.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield await _seed(engine, _SCENARIOS[scenario])
    finally:
        await engine.dispose()


async def _contribution(book: _Book, labels: str = "AB"):
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioService(session).get_positions_contribution(book.user_id, broker_ids=book.scope(labels), date_from=START, date_to=END, target_currency_override=EUR)


async def _report(book: _Book, labels: str = "AB"):
    query = PortfolioReportQuery(
        broker_ids=book.scope(labels),
        date_range=OpenDateRangeModel(start=START, end=END),
        target_currency=EUR,
        include_summary=False,
        include_history=False,
        include_positions_contribution=True,
        include_pnl_candles=False,
    )
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioService(session).get_report(book.user_id, query)


# =============================================================================
# COMPARISONS
# =============================================================================


def _clear_caches() -> None:
    portfolio_engine_module._portfolio_blob_cache.clear()
    report_module._portfolio_l2_cache.clear()


@pytest.fixture(autouse=True)
def no_cached_portfolio(request):
    """No engine blob and no report crosses into or out of a test."""
    _clear_caches()
    request.addfinalizer(_clear_caches)


def _diff(old: Any, new: Any, path: str = "$") -> list[tuple[str, Any, Any]]:
    """Every leaf where two JSON trees differ, as (path, old, new)."""
    if isinstance(old, dict) and isinstance(new, dict):
        out: list[tuple[str, Any, Any]] = []
        for key in sorted(set(old) | set(new), key=str):
            if key not in old or key not in new:
                out.append((f"{path}.{key}", old.get(key, "<absent>"), new.get(key, "<absent>")))
            else:
                out.extend(_diff(old[key], new[key], f"{path}.{key}"))
        return out
    if isinstance(old, list) and isinstance(new, list):
        if len(old) != len(new):
            return [(f"{path}.length", len(old), len(new))]
        out = []
        for index, (left, right) in enumerate(zip(old, new, strict=True)):
            out.extend(_diff(left, right, f"{path}[{index}]"))
        return out
    return [] if old == new or _same_number(old, new) else [(path, old, new)]


def _same_number(old: Any, new: Any) -> bool:
    """Two JSON strings that are the same decimal number: equal (trailing zeros are representation, not contract)."""
    if not (isinstance(old, str) and isinstance(new, str)):
        return False
    try:
        left, right = Decimal(old), Decimal(new)
    except InvalidOperation:
        return False
    return left.is_finite() and right.is_finite() and left == right


def _row(contribution, book: _Book, asset: str, broker: str):
    asset_id, broker_id = book.asset_ids[asset], book.broker_ids[broker]
    found = [row for row in contribution.positions if row.asset_id == asset_id and row.broker_id == broker_id]
    assert len(found) == 1, f"{len(found)} contribution rows for asset {asset} at broker {broker}: {[(row.asset_id, row.broker_id) for row in contribution.positions]}"
    return found[0]


def _figures(row) -> dict[str, Any]:
    """The row's figures, the identity and the MF-CB fields aside."""
    return row.model_dump(mode="json", exclude=_IDENTITY | _NEW_FIELDS)


def _assert_todays_figures(key: str, row) -> None:
    """MF-CB changes no number: the row's figures are HEAD bb6085662's (``_TODAY``)."""
    differences = _diff(_TODAY[key], _figures(row))
    shown = "\n".join(f"  {path}: HEAD={left!r} now={right!r}" for path, left, right in differences[:_DIFF_SHOWN])
    assert not differences, f"{key}: {len(differences)} figure(s) differ from HEAD's:\n{shown}"


def _assert_closed(row, closed_by: str | None, closed_to_broker_id: int | None) -> None:
    # Plain attribute access, never getattr with a default: a None expectation must not pass on a row that has no field.
    assert row.closed_by == closed_by, f"closed_by: {row.closed_by!r}, expected {closed_by!r}"
    assert row.closed_to_broker_id == closed_to_broker_id, f"closed_to_broker_id: {row.closed_to_broker_id!r}, expected {closed_to_broker_id!r}"


# =============================================================================
# HEAD bb6085662's FIGURES — captured on HEAD from the books above, period (03-04, 03-14], report in EUR
# =============================================================================

_TODAY: dict[str, dict[str, Any]] = {
    "sell.X@A": {
        "asset_type": "STOCK",
        "period_unrealized_delta": "-40.000000000000000000",
        "period_realized_gain_loss": "100.000000000000",
        "period_income": None,
        "period_fees_taxes": None,
        "period_pnl": "60.000000000000000000",
        "period_pnl_percent": "0.0577",
        "period_unrealized_delta_percent": "-0.0385",
        "period_realized_gain_loss_percent": "0.0962",
        "period_income_percent": None,
        "period_fees_taxes_percent": None,
        "annualized_return": None,
        "start_value": "1040.000000000000000000",
        "end_value": "0",
        "is_fully_sold": True,
        "oldest_open_lot_date": None,
    },
    "transfer.X@A": {
        "asset_type": "STOCK",
        "period_unrealized_delta": "60.000000000000000000",
        "period_realized_gain_loss": None,
        "period_income": None,
        "period_fees_taxes": None,
        "period_pnl": "60.000000000000000000",
        "period_pnl_percent": "0.0577",
        "period_unrealized_delta_percent": "0.0577",
        "period_realized_gain_loss_percent": None,
        "period_income_percent": None,
        "period_fees_taxes_percent": None,
        "annualized_return": None,
        "start_value": "1040.000000000000000000",
        "end_value": "0",
        "is_fully_sold": True,
        "oldest_open_lot_date": None,
    },
    "transfer.X@B": {
        "asset_type": "STOCK",
        "period_unrealized_delta": "-20.000000000000000000",
        "period_realized_gain_loss": None,
        "period_income": None,
        "period_fees_taxes": None,
        "period_pnl": "-20.000000000000000000",
        "period_pnl_percent": None,
        "period_unrealized_delta_percent": None,
        "period_realized_gain_loss_percent": None,
        "period_income_percent": None,
        "period_fees_taxes_percent": None,
        "annualized_return": None,
        "start_value": "0",
        "end_value": "1080.000000000000000000",
        "is_fully_sold": False,
        "oldest_open_lot_date": "2024-03-06",
    },
    "transfer_scope_A.X@A": {
        "asset_type": "STOCK",
        "period_unrealized_delta": "-40.000000000000000000",
        "period_realized_gain_loss": None,
        "period_income": None,
        "period_fees_taxes": None,
        "period_pnl": "-40.000000000000000000",
        "period_pnl_percent": "-0.0385",
        "period_unrealized_delta_percent": "-0.0385",
        "period_realized_gain_loss_percent": None,
        "period_income_percent": None,
        "period_fees_taxes_percent": None,
        "annualized_return": None,
        "start_value": "1040.000000000000000000",
        "end_value": "0",
        "is_fully_sold": True,
        "oldest_open_lot_date": None,
    },
    "adjustment.X@A": {
        "asset_type": "STOCK",
        "period_unrealized_delta": "-40.000000000000000000",
        "period_realized_gain_loss": "-1000.000000000000",
        "period_income": None,
        "period_fees_taxes": None,
        "period_pnl": "-1040.000000000000000000",
        "period_pnl_percent": "-1.0000",
        "period_unrealized_delta_percent": "-0.0385",
        "period_realized_gain_loss_percent": "-0.9615",
        "period_income_percent": None,
        "period_fees_taxes_percent": None,
        "annualized_return": None,
        "start_value": "1040.000000000000000000",
        "end_value": "0",
        "is_fully_sold": True,
        "oldest_open_lot_date": None,
    },
    "transfer_then_sell.X@A": {
        "asset_type": "STOCK",
        "period_unrealized_delta": "20.000000000000000000",
        "period_realized_gain_loss": "20.000000000000",
        "period_income": None,
        "period_fees_taxes": None,
        "period_pnl": "40.000000000000000000",
        "period_pnl_percent": "0.0385",
        "period_unrealized_delta_percent": "0.0192",
        "period_realized_gain_loss_percent": "0.0192",
        "period_income_percent": None,
        "period_fees_taxes_percent": None,
        "annualized_return": None,
        "start_value": "1040.000000000000000000",
        "end_value": "0",
        "is_fully_sold": True,
        "oldest_open_lot_date": None,
    },
    "sell_then_transfer.X@A": {
        "asset_type": "STOCK",
        "period_unrealized_delta": "-10.000000000000000000",
        "period_realized_gain_loss": "40.000000000000",
        "period_income": None,
        "period_fees_taxes": None,
        "period_pnl": "30.000000000000000000",
        "period_pnl_percent": "0.0288",
        "period_unrealized_delta_percent": "-0.0096",
        "period_realized_gain_loss_percent": "0.0385",
        "period_income_percent": None,
        "period_fees_taxes_percent": None,
        "annualized_return": None,
        "start_value": "1040.000000000000000000",
        "end_value": "0",
        "is_fully_sold": True,
        "oldest_open_lot_date": None,
    },
    "same_day_transfer_first.X@A": {
        "asset_type": "STOCK",
        "period_unrealized_delta": "20.000000000000000000",
        "period_realized_gain_loss": "40.000000000000",
        "period_income": None,
        "period_fees_taxes": None,
        "period_pnl": "60.000000000000000000",
        "period_pnl_percent": "0.0577",
        "period_unrealized_delta_percent": "0.0192",
        "period_realized_gain_loss_percent": "0.0385",
        "period_income_percent": None,
        "period_fees_taxes_percent": None,
        "annualized_return": None,
        "start_value": "1040.000000000000000000",
        "end_value": "0",
        "is_fully_sold": True,
        "oldest_open_lot_date": None,
    },
    "same_day_sell_first.X@A": {
        "asset_type": "STOCK",
        "period_unrealized_delta": "20.000000000000000000",
        "period_realized_gain_loss": "40.000000000000",
        "period_income": None,
        "period_fees_taxes": None,
        "period_pnl": "60.000000000000000000",
        "period_pnl_percent": "0.0577",
        "period_unrealized_delta_percent": "0.0192",
        "period_realized_gain_loss_percent": "0.0385",
        "period_income_percent": None,
        "period_fees_taxes_percent": None,
        "annualized_return": None,
        "start_value": "1040.000000000000000000",
        "end_value": "0",
        "is_fully_sold": True,
        "oldest_open_lot_date": None,
    },
    "transfer_to_stranger.X@A": {
        "asset_type": "STOCK",
        "period_unrealized_delta": "-40.000000000000000000",
        "period_realized_gain_loss": None,
        "period_income": None,
        "period_fees_taxes": None,
        "period_pnl": "-40.000000000000000000",
        "period_pnl_percent": "-0.0385",
        "period_unrealized_delta_percent": "-0.0385",
        "period_realized_gain_loss_percent": None,
        "period_income_percent": None,
        "period_fees_taxes_percent": None,
        "annualized_return": None,
        "start_value": "1040.000000000000000000",
        "end_value": "0",
        "is_fully_sold": True,
        "oldest_open_lot_date": None,
    },
    "orphan_transfer.X@A": {
        "asset_type": "STOCK",
        "period_unrealized_delta": "-40.000000000000000000",
        "period_realized_gain_loss": None,
        "period_income": None,
        "period_fees_taxes": None,
        "period_pnl": "-40.000000000000000000",
        "period_pnl_percent": "-0.0385",
        "period_unrealized_delta_percent": "-0.0385",
        "period_realized_gain_loss_percent": None,
        "period_income_percent": None,
        "period_fees_taxes_percent": None,
        "annualized_return": None,
        "start_value": "1040.000000000000000000",
        "end_value": "0",
        "is_fully_sold": True,
        "oldest_open_lot_date": None,
    },
    "open_and_income_only.X@A": {
        "asset_type": "STOCK",
        "period_unrealized_delta": "40.000000000000000000",
        "period_realized_gain_loss": None,
        "period_income": None,
        "period_fees_taxes": None,
        "period_pnl": "40.000000000000000000",
        "period_pnl_percent": "0.0385",
        "period_unrealized_delta_percent": "0.0385",
        "period_realized_gain_loss_percent": None,
        "period_income_percent": None,
        "period_fees_taxes_percent": None,
        "annualized_return": None,
        "start_value": "1040.000000000000000000",
        "end_value": "1080.000000000000000000",
        "is_fully_sold": False,
        "oldest_open_lot_date": "2024-02-27",
    },
    "open_and_income_only.Z@A": {
        "asset_type": "STOCK",
        "period_unrealized_delta": None,
        "period_realized_gain_loss": None,
        "period_income": "7.000000000000",
        "period_fees_taxes": None,
        "period_pnl": "7.000000000000",
        "period_pnl_percent": None,
        "period_unrealized_delta_percent": None,
        "period_realized_gain_loss_percent": None,
        "period_income_percent": None,
        "period_fees_taxes_percent": None,
        "annualized_return": None,
        "start_value": "0",
        "end_value": "0",
        "is_fully_sold": True,
        "oldest_open_lot_date": None,
    },
    "closed_before.X@A": {
        "asset_type": "STOCK",
        "period_unrealized_delta": None,
        "period_realized_gain_loss": None,
        "period_income": "5.000000000000",
        "period_fees_taxes": None,
        "period_pnl": "5.000000000000",
        "period_pnl_percent": None,
        "period_unrealized_delta_percent": None,
        "period_realized_gain_loss_percent": None,
        "period_income_percent": None,
        "period_fees_taxes_percent": None,
        "annualized_return": None,
        "start_value": "0",
        "end_value": "0",
        "is_fully_sold": True,
        "oldest_open_lot_date": None,
    },
}


# =============================================================================
# (a) — A FULL SELL
# =============================================================================


class TestSell:
    @pytest.mark.asyncio
    async def test_a_full_sell_is_closed_by_sell(self, tmp_path):
        print_section("MF-CB (a): 10 X sold at A inside the period — closed_by SELL, no broker")
        async with _private_book(tmp_path, "sell") as book:
            contribution = await _contribution(book)
        row = _row(contribution, book, "X", "A")
        assert row.is_fully_sold is True
        _assert_todays_figures("sell.X@A", row)
        _assert_closed(row, "SELL", None)
        print_success("a full sale says SELL")


# =============================================================================
# (b) — A FULL TRANSFER A -> B
# =============================================================================


class TestTransfer:
    @pytest.mark.asyncio
    async def test_the_giving_row_names_the_receiving_broker(self, tmp_path):
        print_section("MF-CB (b): 10 X transferred A -> B, pair linked both ways — row A TRANSFER to B, row B held")
        async with _private_book(tmp_path, "transfer") as book:
            contribution = await _contribution(book, "AB")
        row_a, row_b = _row(contribution, book, "X", "A"), _row(contribution, book, "X", "B")
        assert row_a.is_fully_sold is True and row_b.is_fully_sold is False
        _assert_todays_figures("transfer.X@A", row_a)
        _assert_todays_figures("transfer.X@B", row_b)
        _assert_closed(row_a, "TRANSFER", book.broker_ids["B"])
        _assert_closed(row_b, None, None)
        print_success("the transfer's giving row says TRANSFER to B, the receiving row is held")

    @pytest.mark.asyncio
    async def test_with_the_giving_broker_alone_it_still_names_b(self, tmp_path):
        print_section("MF-CB (b): the same transfer, broker_ids=[A] — row A still TRANSFER to B (B is the user's)")
        async with _private_book(tmp_path, "transfer") as book:
            contribution = await _contribution(book, "A")
        assert all(row.broker_id == book.broker_ids["A"] for row in contribution.positions), "a row of a broker outside the scope"
        row_a = _row(contribution, book, "X", "A")
        assert row_a.is_fully_sold is True
        _assert_todays_figures("transfer_scope_A.X@A", row_a)
        _assert_closed(row_a, "TRANSFER", book.broker_ids["B"])
        print_success("outside the scope, the receiving broker is still named: the user has access to it")

    @pytest.mark.asyncio
    async def test_the_report_carries_the_same_fields(self, tmp_path):
        print_section("MF-CB (b): get_report(include_positions_contribution=True) — the same closed_by and closed_to_broker_id")
        async with _private_book(tmp_path, "transfer") as book:
            report = await _report(book, "AB")
        assert report.positions_contribution is not None, "the report has no positions contribution"
        row_a, row_b = _row(report.positions_contribution, book, "X", "A"), _row(report.positions_contribution, book, "X", "B")
        _assert_todays_figures("transfer.X@A", row_a)
        _assert_todays_figures("transfer.X@B", row_b)
        _assert_closed(row_a, "TRANSFER", book.broker_ids["B"])
        _assert_closed(row_b, None, None)
        print_success("the report's rows carry the fields")


# =============================================================================
# (c) — AN ADJUSTMENT TO ZERO
# =============================================================================


class TestAdjustment:
    @pytest.mark.asyncio
    async def test_an_outgoing_adjustment_to_zero(self, tmp_path):
        print_section("MF-CB (c): an ADJUSTMENT of -10 X at A — closed_by ADJUSTMENT, no broker")
        async with _private_book(tmp_path, "adjustment") as book:
            contribution = await _contribution(book)
        row = _row(contribution, book, "X", "A")
        assert row.is_fully_sold is True
        _assert_todays_figures("adjustment.X@A", row)
        _assert_closed(row, "ADJUSTMENT", None)
        print_success("an adjustment to zero says ADJUSTMENT")


# =============================================================================
# (d) — TWO EXITS: THE LAST ONE NAMES THE CLOSE
# =============================================================================


class TestMixedExits:
    @pytest.mark.asyncio
    async def test_transfer_6_then_sell_4(self, tmp_path):
        print_section("MF-CB (d): 6 X to B on D3, the other 4 sold on D4 — SELL")
        async with _private_book(tmp_path, "transfer_then_sell") as book:
            contribution = await _contribution(book)
        row = _row(contribution, book, "X", "A")
        assert row.is_fully_sold is True
        _assert_todays_figures("transfer_then_sell.X@A", row)
        _assert_closed(row, "SELL", None)
        print_success("the sale after the transfer closes the position")

    @pytest.mark.asyncio
    async def test_sell_4_then_transfer_6(self, tmp_path):
        print_section("MF-CB (d): 4 X sold on D3, the other 6 to B on D4 — TRANSFER to B")
        async with _private_book(tmp_path, "sell_then_transfer") as book:
            contribution = await _contribution(book)
        row = _row(contribution, book, "X", "A")
        assert row.is_fully_sold is True
        _assert_todays_figures("sell_then_transfer.X@A", row)
        _assert_closed(row, "TRANSFER", book.broker_ids["B"])
        print_success("the transfer after the sale closes the position")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("scenario", "first", "last", "closed_by", "to_b"),
        [("same_day_transfer_first", "tr_out", "sell_X", "SELL", False), ("same_day_sell_first", "sell_X", "tr_out", "TRANSFER", True)],
        ids=["transfer-then-sell", "sell-then-transfer"],
    )
    async def test_same_day_exits_the_later_by_id(self, tmp_path, scenario, first, last, closed_by, to_b):
        print_section(f"MF-CB (d): both exits on D3 ({scenario}) — the later in replay order (date, id): {closed_by}")
        async with _private_book(tmp_path, scenario) as book:
            assert book.tx_ids[first] < book.tx_ids[last], f"precondition: {first} id {book.tx_ids[first]} is not before {last} id {book.tx_ids[last]}"
            contribution = await _contribution(book)
        row = _row(contribution, book, "X", "A")
        assert row.is_fully_sold is True
        _assert_todays_figures(f"{scenario}.X@A", row)
        _assert_closed(row, closed_by, book.broker_ids["B"] if to_b else None)
        print_success(f"on one day the later id closes: {closed_by}")


# =============================================================================
# (e) — A TRANSFER OUT OF THE USER'S REACH
# =============================================================================


class TestTransferOutOfReach:
    @pytest.mark.asyncio
    async def test_to_another_users_broker_names_no_broker(self, tmp_path):
        print_section("MF-CB (e): 10 X transferred A -> C, C another user's — TRANSFER, closed_to_broker_id None")
        async with _private_book(tmp_path, "transfer_to_stranger") as book:
            contribution = await _contribution(book, "AB")
        assert book.broker_ids["C"] not in {row.broker_id for row in contribution.positions}, "a row of the stranger's broker"
        row = _row(contribution, book, "X", "A")
        assert row.is_fully_sold is True
        _assert_todays_figures("transfer_to_stranger.X@A", row)
        _assert_closed(row, "TRANSFER", None)
        print_success("another user's broker id never leaks")

    @pytest.mark.asyncio
    async def test_an_orphan_transfer_names_no_broker(self, tmp_path):
        print_section("MF-CB (e): an orphan TRANSFER of -10 X at A (no pair) — TRANSFER, closed_to_broker_id None")
        async with _private_book(tmp_path, "orphan_transfer") as book:
            contribution = await _contribution(book)
        row = _row(contribution, book, "X", "A")
        assert row.is_fully_sold is True
        _assert_todays_figures("orphan_transfer.X@A", row)
        _assert_closed(row, "TRANSFER", None)
        print_success("a transfer without its pair names no broker")


# =============================================================================
# (f) — NOT CLOSED
# =============================================================================


class TestNotClosed:
    @pytest.mark.asyncio
    async def test_an_open_position_and_an_income_only_row(self, tmp_path):
        print_section("MF-CB (f): X still held at A, a DIVIDEND on Z never held — both rows (None, None)")
        async with _private_book(tmp_path, "open_and_income_only") as book:
            contribution = await _contribution(book)
        held, income_only = _row(contribution, book, "X", "A"), _row(contribution, book, "Z", "A")
        assert held.is_fully_sold is False
        assert income_only.is_fully_sold is True and income_only.start_value == 0 and income_only.end_value == 0
        _assert_todays_figures("open_and_income_only.X@A", held)
        _assert_todays_figures("open_and_income_only.Z@A", income_only)
        _assert_closed(held, None, None)
        _assert_closed(income_only, None, None)
        print_success("a held row and an income-only row have no close")


# =============================================================================
# (g) — CLOSED BEFORE THE PERIOD
# =============================================================================


class TestClosedBeforeThePeriod:
    @pytest.mark.asyncio
    async def test_a_position_sold_before_the_start_says_sell(self, tmp_path):
        print_section("MF-CB (g): 10 X sold on 02-29, before the period; a DIVIDEND inside it lists the row — SELL")
        async with _private_book(tmp_path, "closed_before") as book:
            contribution = await _contribution(book)
        row = _row(contribution, book, "X", "A")
        assert row.is_fully_sold is True and row.period_realized_gain_loss is None, "the sale is not before the period"
        _assert_todays_figures("closed_before.X@A", row)
        _assert_closed(row, "SELL", None)
        print_success("a row closed before the period says how it closed")
