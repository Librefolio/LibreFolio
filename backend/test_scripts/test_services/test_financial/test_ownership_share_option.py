"""MF6-3 (decision D4) — the report and the positions series «whole», the owner's share ignored: ``apply_ownership_share``.

Every figure of the Portfolio report is scaled today by ``native_cash.effective_share(role, share_percentage)``: an OWNER
counts its ``BrokerUserAccess.share_percentage``, an EDITOR or a VIEWER the whole broker. The broker page must show the
whole amounts, as an Editor sees them. The option: ``PortfolioReportQuery.apply_ownership_share`` and
``PositionsSeriesQuery.apply_ownership_share`` (default True: nothing changes for a caller that does not send it), passed
to ``PortfolioCalculationEngine.calculate(apply_ownership_share=…)`` through ``PortfolioService._engine_run``; the flag is
part of the engine's blob-cache key and of the report's L2 key. Design: ``MF6-3-design-bozza.md`` (ondata 6).

- ``TestOwnerWhole`` (a) — an owner at 100 %: report and series with ``apply_ownership_share=False`` are those of the
  default, field by field.
- ``TestOwnerShareIgnored`` (b) — an owner at 30 % of A and B: with the option False the whole report and series are the
  editor's default ones. The guard ``test_the_default_scales_the_amounts_and_keeps_the_ratios`` (green before MF6-3) pins
  what the option undoes: by default the owner's money is 0.3 × the editor's, its ratios (TWRR, simple ROI, a position's
  return) the editor's.
- ``TestOwnerZero`` (c) — an owner at 0 %: the option False gives the editor's figures; the guard
  ``test_the_default_is_zero`` keeps today's zeros.
- ``TestEditorAndViewer`` (d) — the option changes nothing for an editor or a viewer.
- ``TestTwoBrokersDifferentShares`` (e) — A at 30 %, B at 60 %, a TRANSFER of X and a CASH_TRANSFER A → B: the option False
  equals the editor-of-both view and has no share mismatch (J-43, ``data_quality.share_mismatch_warnings``), which the
  default reports.
- ``TestCaches`` (f) — default, then False, then default again, caches kept: three right answers (False ≠ default, third =
  first) for the report (L2 key) and the series (blob key); one engine build per flag value, the report and the series of
  one flag sharing it (FB-14).
- ``TestRiskScopeShareInvariant`` (g) — the risk scope of one broker, default path: its weights, cash weight and TWRR
  return series are the same for the 30 % owner and for the editor (whole broker, as an owner at 100 %). Its money
  (``scope_value``) does scale — what (h) is for.
- ``TestRiskScopeWholeBroker`` (h) — ``PortfolioRiskScope.apply_ownership_share=False`` (decision changed on 31/10: the
  option exists for the risk too, passed by ``risk/scope.py::load_scope_inputs`` to the report): the 30 % owner's
  ``scope_value`` and ``asset_values`` are the editor's, and so are the amounts of a hypothetical stress computed on them
  (``StressAnalytic`` on the context ``build_execution_context`` makes); by default they stay 0.3 ×. An owner at 0 %: the
  option gives the editor's composition; the default holds no asset (every quantity scaled to 0 falls under the dust
  threshold), so its scope value is 0 with no composition error.

Every comparison is ``model_dump(mode="json")`` diffed leaf by leaf, two decimal strings of the same number being equal
(a share of 1 read from the database, ``1.000000``, leaves more trailing zeros on the figures than the editor's whole
``1``: the guard ``test_the_default_of_an_owner_at_100_is_the_editors`` pins that only the representation differs); no
field of either response names the user, so nothing is excluded: a difference is a finding about the product. The 0.3 × checks read Decimals with a tolerance
(several outputs are quantized).

Red before MF6-3: every query that sends ``apply_ownership_share`` is refused by StrictModel («Extra inputs are not
permitted»). Each test first proves the book answers with data through a default call, so a red is never the book.

The book, on a private SQLite file under ``tmp_path`` (the app schema, ``SQLModel.metadata.create_all``, an engine of its
own, NullPool, disposed at teardown) — the ledger of ``test_engine_shared_run.py`` (FB-14): brokers A and B; X a EUR
stock, Y a USD stock; read in EUR:

- D0 03-04: DEPOSIT 10000 at A, 1000 at B;  D1 03-05: BUY 3 X for 1000 at A;
- D2 03-07: TRANSFER of 1 X A -> B (arrives D4); CASH_TRANSFER of 500 A -> B (arrives D3);
- D3 03-08: FX_CONVERSION at A, 1000 EUR into 1090 USD; BUY 2 Y for 500 USD at A;
- D4 03-11: SELL 1 X for 340 at A; DIVIDEND 12 on X, FEE 3, TAX 2 at A;  D5 03-12: WITHDRAWAL 100 at B.

Three users: the OWNER of A and B, at the shares each test asks; an EDITOR and a VIEWER of both (share 0, as the schema
rule gives them).

Isolation: PURE with respect to the lane — no session on the lane's database, no server, no network. The engine's blob
cache and the report's L2 cache (process-global) are emptied around each test.

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory); alone:
``./dev.py test services ownership-share-option``.

Reference: backend/app/services/portfolio/portfolio_service.py (_engine_run, get_report and its L2 key, get_positions_series),
backend/app/services/financial_math/portfolio/engine.py (calculate: broker_shares, the blob key),
backend/app/services/financial_math/native_cash.py (broker_shares), backend/app/services/risk/scope.py (load_scope_inputs).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
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
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, FxRate, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.schemas.common import DateRangeModel, OpenDateRangeModel
from backend.app.schemas.portfolio import PortfolioReportQuery, PositionKey, PositionsSeriesQuery
from backend.app.schemas.risk import PortfolioRiskScope, RiskAnalyticRequest, RiskCompositionPolicy, RiskMode, RiskQueryRequest, RiskScenarioDimension, RiskStressMethod
from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine
from backend.app.services.market_series import prepare_asset_series_set
from backend.app.services.portfolio import portfolio_service as portfolio_service_module
from backend.app.services.portfolio.portfolio_service import PortfolioService
from backend.app.services.risk.results import build_execution_context, portfolio_twrr_returns
from backend.app.services.risk.scope import load_asset_classifications, load_scope_inputs
from backend.app.services.risk_plugins.stress.plugin import StressAnalytic, StressParams
from backend.test_scripts.test_utils import print_section, print_success

EUR = "EUR"
USD = "USD"

D0 = date(2024, 3, 4)
D1 = date(2024, 3, 5)
D2 = date(2024, 3, 7)
D3 = date(2024, 3, 8)
D4 = date(2024, 3, 11)
D5 = date(2024, 3, 12)
LAST_QUOTE = date(2024, 3, 13)
END = date(2024, 3, 14)
WINDOW = (D2, END)

#: How many differing fields an assertion message shows.
_DIFF_SHOWN = 12
#: Tolerance of a money figure against share × the whole one, and of a ratio against the whole one's.
_MONEY_TOL = Decimal("0.01")
_RATIO_TOL = Decimal("0.0001")

THIRTY = Decimal("0.3")
SIXTY = Decimal("0.6")

# (label, broker, asset, type, day, quantity, amount, currency)
_ROWS = (
    ("dep_A", "A", None, TransactionType.DEPOSIT, D0, "0", "10000", EUR),
    ("dep_B", "B", None, TransactionType.DEPOSIT, D0, "0", "1000", EUR),
    ("buy_X", "A", "X", TransactionType.BUY, D1, "3", "-1000", EUR),
    ("tr_out", "A", "X", TransactionType.TRANSFER, D2, "-1", "0", None),
    ("ct_out", "A", None, TransactionType.CASH_TRANSFER, D2, "0", "-500", EUR),
    ("ct_in", "B", None, TransactionType.CASH_TRANSFER, D3, "0", "500", EUR),
    ("fx_out", "A", None, TransactionType.FX_CONVERSION, D3, "0", "-1000", EUR),
    ("fx_in", "A", None, TransactionType.FX_CONVERSION, D3, "0", "1090", USD),
    ("buy_Y", "A", "Y", TransactionType.BUY, D3, "2", "-500", USD),
    ("tr_in", "B", "X", TransactionType.TRANSFER, D4, "1", "0", None),
    ("sell_X", "A", "X", TransactionType.SELL, D4, "-1", "340", EUR),
    ("div_X", "A", "X", TransactionType.DIVIDEND, D4, "0", "12", EUR),
    ("fee_A", "A", None, TransactionType.FEE, D4, "0", "-3", EUR),
    ("tax_X", "A", "X", TransactionType.TAX, D4, "0", "-2", EUR),
    ("wd_B", "B", None, TransactionType.WITHDRAWAL, D5, "0", "-100", EUR),
)
_LINKED_PAIRS = (("tr_out", "tr_in"), ("ct_out", "ct_in"), ("fx_out", "fx_in"))
# (asset, day, close, currency)
_CLOSES = (("X", D1, "333.5", EUR), ("X", D4, "345.67", EUR), ("X", LAST_QUOTE, "350", EUR), ("Y", D3, "250", USD), ("Y", D5, "255", USD))
# 1 EUR = rate USD from that day (base EUR < quote USD, as FxRate's check requires)
_EUR_USD = ((D3, "1.09"), (D5, "1.1"))


# =============================================================================
# THE BOOK — a private SQLite file
# =============================================================================


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    owner_id: int
    editor_id: int
    viewer_id: int
    broker_ids: dict[str, int]
    asset_ids: dict[str, int]

    def scope(self, labels: str) -> list[int]:
        return sorted(self.broker_ids[label] for label in labels)


async def _seed(engine: AsyncEngine, share_a: Decimal, share_b: Decimal) -> _Book:
    """The module's ledger, an OWNER of A and B at ``share_a`` / ``share_b``, an EDITOR and a VIEWER of both."""
    tag = uuid4().hex[:12]
    async with AsyncSession(engine, expire_on_commit=False) as session:
        users = {role: User(username=f"mf63_{role}_{tag}", email=f"mf63_{role}_{tag}@test.com", hashed_password="fakehash", is_active=True) for role in ("owner", "editor", "viewer")}
        brokers = {label: Broker(name=f"MF6-3 share option {label} {tag}") for label in ("A", "B")}
        assets = {
            "X": Asset(display_name=f"MF6-3 share option X {tag}", currency=EUR, asset_type=AssetType.STOCK),
            "Y": Asset(display_name=f"MF6-3 share option Y {tag}", currency=USD, asset_type=AssetType.STOCK),
        }
        session.add_all([*users.values(), *brokers.values(), *assets.values()])
        await session.flush()
        owner_shares = {"A": share_a, "B": share_b}
        session.add_all(
            [
                *(BrokerUserAccess(broker_id=broker.id, user_id=users["owner"].id, role=UserRole.OWNER, share_percentage=owner_shares[label]) for label, broker in brokers.items()),
                *(BrokerUserAccess(broker_id=broker.id, user_id=users["editor"].id, role=UserRole.EDITOR, share_percentage=Decimal("0")) for broker in brokers.values()),
                *(BrokerUserAccess(broker_id=broker.id, user_id=users["viewer"].id, role=UserRole.VIEWER, share_percentage=Decimal("0")) for broker in brokers.values()),
            ]
        )
        session.add_all(
            [
                *(PriceHistory(asset_id=assets[asset].id, date=day, open=Decimal(close), high=Decimal(close), low=Decimal(close), close=Decimal(close), volume=Decimal("1"), currency=currency, source_plugin_key="mf63_share_option_test") for asset, day, close, currency in _CLOSES),
                *(FxRate(date=day, base=EUR, quote=USD, rate=Decimal(rate), source="TEST") for day, rate in _EUR_USD),
            ]
        )
        rows = {label: Transaction(broker_id=brokers[broker].id, asset_id=assets[asset].id if asset else None, type=tx_type, date=day, quantity=Decimal(quantity), amount=Decimal(amount), currency=currency) for label, broker, asset, tx_type, day, quantity, amount, currency in _ROWS}
        session.add_all(rows.values())
        await session.flush()
        for left, right in _LINKED_PAIRS:
            rows[left].related_transaction_id = rows[right].id
            rows[right].related_transaction_id = rows[left].id
        await session.commit()
        return _Book(
            engine=engine,
            owner_id=users["owner"].id,
            editor_id=users["editor"].id,
            viewer_id=users["viewer"].id,
            broker_ids={label: broker.id for label, broker in brokers.items()},
            asset_ids={label: asset.id for label, asset in assets.items()},
        )


@asynccontextmanager
async def _private_book(directory: Path, share_a: Decimal, share_b: Decimal) -> AsyncIterator[_Book]:
    """The app schema and the module's ledger on a private SQLite file under ``directory``; the engine disposed after."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / 'mf63_share_option.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield await _seed(engine, share_a, share_b)
    finally:
        await engine.dispose()


# =============================================================================
# THE QUERIES — what the broker page and the Portfolio page ask
# =============================================================================


def _option(apply_ownership_share: bool | None) -> dict[str, bool]:
    """The option as the caller sends it; None = not sent (the default)."""
    return {} if apply_ownership_share is None else {"apply_ownership_share": apply_ownership_share}


def _report_query(book: _Book, labels: str, apply_ownership_share: bool | None = None) -> PortfolioReportQuery:
    """Every section of the page on the brokers ``labels``; the per-broker P&L history only with two brokers. No candles."""
    return PortfolioReportQuery(
        broker_ids=book.scope(labels),
        date_range=OpenDateRangeModel(start=WINDOW[0], end=WINDOW[1]),
        target_currency=EUR,
        include_summary=True,
        include_history=True,
        include_allocation_history=True,
        include_breakdown=True,
        include_positions_contribution=True,
        include_broker_pnl_history=len(labels) > 1,
        include_pnl_candles=False,
        include_income_history=True,
        include_cost_history=True,
        include_deposit_history=True,
        include_acquisition_funding=True,
        **_option(apply_ownership_share),
    )


def _series_query(book: _Book, labels: str, apply_ownership_share: bool | None = None) -> PositionsSeriesQuery:
    """X and Y at A, X summed over the scope; with B in the scope also X at B (it arrives by the transfer)."""
    x, y = book.asset_ids["X"], book.asset_ids["Y"]
    a, b = book.broker_ids["A"], book.broker_ids["B"]
    positions = [PositionKey(asset_id=x, broker_id=a), PositionKey(asset_id=y, broker_id=a), PositionKey(asset_id=x, broker_id=None)]
    if "B" in labels:
        positions.append(PositionKey(asset_id=x, broker_id=b))
    return PositionsSeriesQuery(broker_ids=book.scope(labels), date_range=OpenDateRangeModel(start=WINDOW[0], end=WINDOW[1]), target_currency=EUR, positions=positions, **_option(apply_ownership_share))


async def _report(book: _Book, user_id: int, query: PortfolioReportQuery):
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioService(session).get_report(user_id, query)


async def _series(book: _Book, user_id: int, query: PositionsSeriesQuery):
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioService(session).get_positions_series(user_id, query)


# =============================================================================
# COMPARISONS
# =============================================================================


def _clear_caches() -> None:
    portfolio_engine_module._portfolio_blob_cache.clear()
    portfolio_service_module._portfolio_l2_cache.clear()


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
    """Two JSON strings that are the same decimal number: equal. The share's exponent reaches the figures' trailing zeros
    (an owner's 1 read from ``Numeric(7, 6)`` is ``1.000000``, an editor's whole is ``1``: ``10000.000000000000`` against
    ``10000.000000``), and the contract compared here is the number, not its representation."""
    if not (isinstance(old, str) and isinstance(new, str)):
        return False
    try:
        left, right = Decimal(old), Decimal(new)
    except InvalidOperation:
        return False
    return left.is_finite() and right.is_finite() and left == right


def _differences(left: Any, right: Any) -> list[tuple[str, Any, Any]]:
    return _diff(left.model_dump(mode="json"), right.model_dump(mode="json"))


def _assert_same(label: str, expected: Any, actual: Any) -> None:
    differences = _differences(expected, actual)
    shown = "\n".join(f"  {path}: expected={left!r} actual={right!r}" for path, left, right in differences[:_DIFF_SHOWN])
    assert not differences, f"{label}: {len(differences)} field(s) differ:\n{shown}"


def _assert_report_has_data(report, *, brokers: int) -> None:
    assert report.summary is not None and report.summary.holdings, "the report has no summary or no holding"
    assert report.history, "the report has no history: the engine run answered empty"
    assert report.positions_contribution is not None and report.positions_contribution.positions, "the report has no positions contribution"
    assert report.acquisition_funding is not None and report.acquisition_funding.points, "the report has no BUY funding in the window"
    assert report.income_history is not None and report.cost_history is not None and report.deposit_history is not None
    if brokers > 1:
        assert report.broker_pnl_history is not None and len(report.broker_pnl_history) == brokers, "the report has not the P&L history of every broker"


def _assert_series_has_data(series, query: PositionsSeriesQuery) -> None:
    assert len(series.series) == len(query.positions), "the series do not answer every position asked"
    assert all(entry.points for entry in series.series), f"a position asked has no point: {[(entry.key, len(entry.points)) for entry in series.series]}"


def _point_at(history, day: date):
    found = [point for point in history if point.date <= day <= point.through]
    assert len(found) == 1, f"{len(found)} history points hold {day}"
    return found[0]


def _contribution_row(report, asset_id: int, broker_id: int):
    found = [row for row in report.positions_contribution.positions if row.asset_id == asset_id and row.broker_id == broker_id]
    assert len(found) == 1, f"{len(found)} contribution rows for asset {asset_id} at broker {broker_id}"
    return found[0]


def _assert_scaled(label: str, part: Decimal | None, whole: Decimal | None, share: Decimal) -> None:
    assert part is not None and whole is not None, f"{label}: part={part!r} whole={whole!r}"
    assert whole != 0, f"{label}: the whole figure is 0, the check would prove nothing"
    assert abs(part - share * whole) <= _MONEY_TOL, f"{label}: {part} is not {share} × {whole} (= {share * whole})"


def _assert_ratio_equal(label: str, owner: Decimal | None, whole: Decimal | None) -> None:
    assert owner is not None and whole is not None, f"{label}: owner={owner!r} whole={whole!r}"
    assert abs(owner - whole) <= _RATIO_TOL, f"{label}: the owner's {owner} differs from the whole broker's {whole}"


@pytest.fixture(autouse=True)
def no_cached_portfolio(request):
    """No engine blob and no report crosses into or out of a test."""
    _clear_caches()
    request.addfinalizer(_clear_caches)


_SCOPES = pytest.mark.parametrize("labels", ["A", "AB"], ids=["broker-A", "brokers-A-B"])


# =============================================================================
# (a) — AN OWNER AT 100 %: THE OPTION CHANGES NOTHING
# =============================================================================


class TestOwnerWhole:
    @pytest.mark.asyncio
    @_SCOPES
    async def test_the_report_without_the_share_is_the_default(self, tmp_path, labels):
        print_section(f"MF6-3 (a): owner 100 %, report on {labels} — apply_ownership_share=False equals the default")
        async with _private_book(tmp_path, Decimal("1"), Decimal("1")) as book:
            default = await _report(book, book.owner_id, _report_query(book, labels))
            _assert_report_has_data(default, brokers=len(labels))
            _clear_caches()
            whole = await _report(book, book.owner_id, _report_query(book, labels, apply_ownership_share=False))
        _assert_same("owner 100 %: report False vs default", default, whole)
        print_success("the 100 % owner's report is the same with and without the share")

    @pytest.mark.asyncio
    @_SCOPES
    async def test_the_series_without_the_share_are_the_default(self, tmp_path, labels):
        print_section(f"MF6-3 (a): owner 100 %, positions series on {labels} — apply_ownership_share=False equals the default")
        async with _private_book(tmp_path, Decimal("1"), Decimal("1")) as book:
            default = await _series(book, book.owner_id, _series_query(book, labels))
            _assert_series_has_data(default, _series_query(book, labels))
            _clear_caches()
            whole = await _series(book, book.owner_id, _series_query(book, labels, apply_ownership_share=False))
        _assert_same("owner 100 %: series False vs default", default, whole)
        print_success("the 100 % owner's series are the same with and without the share")

    @pytest.mark.asyncio
    async def test_the_default_of_an_owner_at_100_is_the_editors(self, tmp_path):
        """Guard, green before MF6-3: a share of 1 read from the database (``Numeric(7, 6)``: ``1.000000``) and the editor's
        whole ``1`` give the same JSON, exponents included — so the parity above compares numbers, not trailing zeros."""
        print_section("MF6-3 (a) guard: owner 100 % by default equals the editor's default, field by field")
        async with _private_book(tmp_path, Decimal("1"), Decimal("1")) as book:
            editor_report = await _report(book, book.editor_id, _report_query(book, "AB"))
            _assert_report_has_data(editor_report, brokers=2)
            owner_report = await _report(book, book.owner_id, _report_query(book, "AB"))
            editor_series = await _series(book, book.editor_id, _series_query(book, "AB"))
            owner_series = await _series(book, book.owner_id, _series_query(book, "AB"))
        _assert_same("owner 100 % default vs editor: report", editor_report, owner_report)
        _assert_same("owner 100 % default vs editor: series", editor_series, owner_series)
        print_success("a share of 1 from the database and the editor's whole give the same figures")


# =============================================================================
# (b) — AN OWNER AT 30 %: THE OPTION GIVES THE EDITOR'S WHOLE FIGURES
# =============================================================================


class TestOwnerShareIgnored:
    @pytest.mark.asyncio
    @_SCOPES
    async def test_the_report_without_the_share_is_the_editors(self, tmp_path, labels):
        print_section(f"MF6-3 (b): owner 30 %, report on {labels} — apply_ownership_share=False equals the editor's default")
        async with _private_book(tmp_path, THIRTY, THIRTY) as book:
            editor = await _report(book, book.editor_id, _report_query(book, labels))
            _assert_report_has_data(editor, brokers=len(labels))
            owner_whole = await _report(book, book.owner_id, _report_query(book, labels, apply_ownership_share=False))
        _assert_same("owner 30 % with False vs editor", editor, owner_whole)
        print_success("the 30 % owner's whole report is the editor's")

    @pytest.mark.asyncio
    @_SCOPES
    async def test_the_series_without_the_share_are_the_editors(self, tmp_path, labels):
        print_section(f"MF6-3 (b): owner 30 %, positions series on {labels} — apply_ownership_share=False equals the editor's default")
        async with _private_book(tmp_path, THIRTY, THIRTY) as book:
            editor = await _series(book, book.editor_id, _series_query(book, labels))
            _assert_series_has_data(editor, _series_query(book, labels))
            owner_whole = await _series(book, book.owner_id, _series_query(book, labels, apply_ownership_share=False))
        _assert_same("owner 30 % series with False vs editor", editor, owner_whole)
        print_success("the 30 % owner's whole series are the editor's")

    @pytest.mark.asyncio
    async def test_the_default_scales_the_amounts_and_keeps_the_ratios(self, tmp_path):
        """Guard, green before MF6-3: what the option undoes. Broker A alone, as the broker page asks it."""
        print_section("MF6-3 (b) guard: owner 30 % by default — money 0.3 × the editor's, ratios the editor's")
        async with _private_book(tmp_path, THIRTY, THIRTY) as book:
            editor = await _report(book, book.editor_id, _report_query(book, "A"))
            owner = await _report(book, book.owner_id, _report_query(book, "A"))
            x, a = book.asset_ids["X"], book.broker_ids["A"]
        _assert_report_has_data(editor, brokers=1)
        _assert_report_has_data(owner, brokers=1)
        # Money
        _assert_scaled("summary.net_worth", owner.summary.net_worth.amount, editor.summary.net_worth.amount, THIRTY)
        _assert_scaled("summary.cash_total", owner.summary.cash_total.amount, editor.summary.cash_total.amount, THIRTY)
        _assert_scaled("history NAV at D4", _point_at(owner.history, D4).nav_value.amount, _point_at(editor.history, D4).nav_value.amount, THIRTY)
        _assert_scaled("contribution period_pnl of X at A", _contribution_row(owner, x, a).period_pnl, _contribution_row(editor, x, a).period_pnl, THIRTY)
        # Ratios
        _assert_ratio_equal("summary.twrr_percent", owner.summary.twrr_percent, editor.summary.twrr_percent)
        _assert_ratio_equal("summary.simple_roi_percent", owner.summary.simple_roi_percent, editor.summary.simple_roi_percent)
        _assert_ratio_equal("history TWRR at D5", _point_at(owner.history, D5).twrr, _point_at(editor.history, D5).twrr)
        _assert_ratio_equal("contribution period_pnl_percent of X at A", _contribution_row(owner, x, a).period_pnl_percent, _contribution_row(editor, x, a).period_pnl_percent)
        print_success("by default the 30 % owner's money is 0.3 × the whole, its ratios the whole's")


# =============================================================================
# (c) — AN OWNER AT 0 %
# =============================================================================


class TestOwnerZero:
    @pytest.mark.asyncio
    async def test_without_the_share_the_figures_are_the_editors(self, tmp_path):
        print_section("MF6-3 (c): owner 0 % of A — apply_ownership_share=False gives the editor's figures")
        async with _private_book(tmp_path, Decimal("0"), Decimal("0")) as book:
            editor_report = await _report(book, book.editor_id, _report_query(book, "A"))
            _assert_report_has_data(editor_report, brokers=1)
            editor_series = await _series(book, book.editor_id, _series_query(book, "A"))
            owner_report = await _report(book, book.owner_id, _report_query(book, "A", apply_ownership_share=False))
            owner_series = await _series(book, book.owner_id, _series_query(book, "A", apply_ownership_share=False))
        _assert_same("owner 0 % report with False vs editor", editor_report, owner_report)
        _assert_same("owner 0 % series with False vs editor", editor_series, owner_series)
        print_success("the 0 % owner sees the whole broker with the option")

    @pytest.mark.asyncio
    async def test_the_default_is_zero(self, tmp_path):
        """Guard, green before MF6-3: the default keeps today's zeros."""
        print_section("MF6-3 (c) guard: owner 0 % of A by default — zero value")
        async with _private_book(tmp_path, Decimal("0"), Decimal("0")) as book:
            editor = await _report(book, book.editor_id, _report_query(book, "A"))
            owner = await _report(book, book.owner_id, _report_query(book, "A"))
        assert editor.summary.net_worth.amount != 0, "the whole broker is worth nothing: the guard would prove nothing"
        assert owner.summary.net_worth.amount == 0
        assert owner.summary.cash_total.amount == 0
        assert owner.history, "the 0 % owner's report has no history"
        assert all(point.nav_value.amount == 0 for point in owner.history), [(point.date, point.nav_value.amount) for point in owner.history if point.nav_value.amount != 0]
        print_success("the 0 % owner's default report is zero")


# =============================================================================
# (d) — EDITOR AND VIEWER: THE OPTION CHANGES NOTHING
# =============================================================================


class TestEditorAndViewer:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("who", ["editor", "viewer"])
    async def test_the_option_changes_nothing(self, tmp_path, who):
        print_section(f"MF6-3 (d): {who} of A and B — apply_ownership_share=False equals the default")
        async with _private_book(tmp_path, THIRTY, SIXTY) as book:
            user_id = book.editor_id if who == "editor" else book.viewer_id
            default_report = await _report(book, user_id, _report_query(book, "AB"))
            _assert_report_has_data(default_report, brokers=2)
            default_series = await _series(book, user_id, _series_query(book, "AB"))
            _clear_caches()
            whole_report = await _report(book, user_id, _report_query(book, "AB", apply_ownership_share=False))
            whole_series = await _series(book, user_id, _series_query(book, "AB", apply_ownership_share=False))
        _assert_same(f"{who}: report False vs default", default_report, whole_report)
        _assert_same(f"{who}: series False vs default", default_series, whole_series)
        print_success(f"the {who}'s report and series are the same with the option")


# =============================================================================
# (e) — TWO BROKERS AT DIFFERENT SHARES, AN INTERNAL TRANSFER
# =============================================================================


class TestTwoBrokersDifferentShares:
    @pytest.mark.asyncio
    async def test_without_the_share_it_is_the_editor_of_both_and_no_mismatch(self, tmp_path):
        print_section("MF6-3 (e): owner 30 % of A, 60 % of B, transfers A -> B — False equals the editor of both, no share mismatch")
        async with _private_book(tmp_path, THIRTY, SIXTY) as book:
            editor_report = await _report(book, book.editor_id, _report_query(book, "AB"))
            _assert_report_has_data(editor_report, brokers=2)
            editor_series = await _series(book, book.editor_id, _series_query(book, "AB"))
            owner_default = await _report(book, book.owner_id, _report_query(book, "AB"))
            assert owner_default.data_quality is not None and owner_default.data_quality.share_mismatch_warnings, "the default report of the 30 %/60 % owner names no share mismatch: the guard would prove nothing"
            owner_whole = await _report(book, book.owner_id, _report_query(book, "AB", apply_ownership_share=False))
            owner_series = await _series(book, book.owner_id, _series_query(book, "AB", apply_ownership_share=False))
        assert owner_whole.data_quality is not None
        assert owner_whole.data_quality.share_mismatch_warnings == [], owner_whole.data_quality.share_mismatch_warnings
        assert not [issue for issue in owner_whole.data_quality.issues if getattr(issue, "group_key", None) == "transfer_share_mismatch"]
        _assert_same("owner 30 %/60 % report with False vs editor of both", editor_report, owner_whole)
        _assert_same("owner 30 %/60 % series with False vs editor of both", editor_series, owner_series)
        print_success("the whole view of two brokers at different shares is the editor's, with no share mismatch")


# =============================================================================
# (f) — THE CACHES NEVER SWAP THE TWO ANSWERS
# =============================================================================


class _Builds:
    """Counts the calls of ``PortfolioCalculationEngine._compute_uncached``: one per replay."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.count = 0
        original = PortfolioCalculationEngine._compute_uncached

        async def counted(engine_self, **kwargs):
            self.count += 1
            return await original(engine_self, **kwargs)

        monkeypatch.setattr(PortfolioCalculationEngine, "_compute_uncached", counted)


class TestCaches:
    @pytest.mark.asyncio
    async def test_default_then_whole_then_default(self, tmp_path, monkeypatch):
        print_section("MF6-3 (f): owner 30 % of A — default, False, default again with the caches kept; one build per flag")
        builds = _Builds(monkeypatch)
        async with _private_book(tmp_path, THIRTY, THIRTY) as book:
            # The whole reference, before the count starts (the editor's run is a build of its own).
            editor_report = await _report(book, book.editor_id, _report_query(book, "A"))
            _assert_report_has_data(editor_report, brokers=1)
            editor_series = await _series(book, book.editor_id, _series_query(book, "A"))
            base = builds.count

            first_report = await _report(book, book.owner_id, _report_query(book, "A"))
            first_series = await _series(book, book.owner_id, _series_query(book, "A"))
            assert builds.count - base == 1, f"the default report and series made {builds.count - base} builds, not one (FB-14)"

            whole_report = await _report(book, book.owner_id, _report_query(book, "A", apply_ownership_share=False))
            whole_series = await _series(book, book.owner_id, _series_query(book, "A", apply_ownership_share=False))
            assert builds.count - base == 2, f"the whole report and series made {builds.count - base - 1} new builds, not one"

            third_report = await _report(book, book.owner_id, _report_query(book, "A"))
            third_series = await _series(book, book.owner_id, _series_query(book, "A", apply_ownership_share=True))
            assert builds.count - base == 2, f"the default asked again made {builds.count - base - 2} new builds: its cached answers were lost"

        assert _differences(first_report, whole_report), "the whole report equals the 30 % one: the L2 cache answered with the default"
        assert _differences(first_series, whole_series), "the whole series equal the 30 % ones: the blob cache answered with the default"
        _assert_same("report: False vs the editor's", editor_report, whole_report)
        _assert_same("series: False vs the editor's", editor_series, whole_series)
        _assert_same("report: the default asked again vs the first", first_report, third_report)
        _assert_same("series: the default asked again vs the first", first_series, third_series)
        print_success("three right answers, one build per flag value")

    @pytest.mark.asyncio
    async def test_the_engine_run_takes_the_flag(self, tmp_path):
        """The engine itself: two runs that differ only by the flag never share a blob."""
        print_section("MF6-3 (f): PortfolioCalculationEngine.calculate(apply_ownership_share=…) — the flag in the blob key")
        async with _private_book(tmp_path, THIRTY, THIRTY) as book:
            scope = book.scope("A")
            async with AsyncSession(book.engine, expire_on_commit=False) as session:
                default = await PortfolioCalculationEngine(session).calculate(user_id=book.owner_id, broker_ids=scope, target_currency=EUR, date_to=END)
                assert len(default.daily_states), "the default run has no daily state"
                whole = await PortfolioCalculationEngine(session).calculate(user_id=book.owner_id, broker_ids=scope, target_currency=EUR, date_to=END, apply_ownership_share=False)
                editor = await PortfolioCalculationEngine(session).calculate(user_id=book.editor_id, broker_ids=scope, target_currency=EUR, date_to=END)
        last_default = _last_nav(default)
        last_whole = _last_nav(whole)
        last_editor = _last_nav(editor)
        assert last_whole == last_editor, f"the whole run's last NAV {last_whole} is not the editor's {last_editor}"
        _assert_scaled("the default run's last NAV", last_default, last_editor, THIRTY)
        print_success("the engine's whole run is the editor's, the default stays scaled")


def _last_nav(result) -> Decimal:
    return result.daily_states[-1].nav_value


# =============================================================================
# (g) — THE RISK SCOPE OF ONE BROKER DOES NOT DEPEND ON THE SHARE
# =============================================================================


def _risk_request(book: _Book, apply_ownership_share: bool | None = None, *, stress: bool = False) -> RiskQueryRequest:
    """A PORTFOLIO scope on broker A: historical, or for the hypothetical stress the current composition."""
    if stress:
        mode_fields: dict[str, Any] = {"mode": RiskMode.CURRENT_COMPOSITION, "composition_policy": RiskCompositionPolicy.CURRENT_BUY_AND_HOLD}
        analytics = [RiskAnalyticRequest(instance_id="stress", analytic_code="stress", parameters=_STRESS_PARAMETERS)]
    else:
        mode_fields = {"mode": RiskMode.HISTORICAL}
        analytics = [RiskAnalyticRequest(instance_id="kpi", analytic_code="kpi")]
    return RiskQueryRequest(
        scope=PortfolioRiskScope(kind="portfolio", broker_ids=book.scope("A"), **_option(apply_ownership_share)),
        date_range=DateRangeModel(start=D0, end=END),
        target_currency=EUR,
        analytics=analytics,
        **mode_fields,
    )


async def _scope_inputs(book: _Book, user_id: int, apply_ownership_share: bool | None = None, *, stress: bool = False):
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await load_scope_inputs(session, user_id=user_id, request=_risk_request(book, apply_ownership_share, stress=stress))


class TestRiskScopeShareInvariant:
    @pytest.mark.asyncio
    async def test_weights_and_returns_are_the_whole_brokers(self, tmp_path):
        """The default path (no option sent). Broker A: the 30 % owner against the editor (whole)."""
        print_section("MF6-3 (g): risk scope of broker A — owner 30 % and editor: same weights, cash weight, TWRR returns")
        async with _private_book(tmp_path, THIRTY, THIRTY) as book:
            owner = await _scope_inputs(book, book.owner_id)
            editor = await _scope_inputs(book, book.editor_id)
        assert editor.requested_asset_ids and editor.weights, "the editor's scope holds no weighted asset: the check would prove nothing"
        assert owner.composition_error is None and editor.composition_error is None, (owner.composition_error, editor.composition_error)
        assert owner.requested_asset_ids == editor.requested_asset_ids
        assert owner.weights.keys() == editor.weights.keys()
        for asset_id, weight in editor.weights.items():
            assert owner.weights[asset_id] == pytest.approx(weight, rel=1e-9, abs=1e-12), f"asset {asset_id}: owner weight {owner.weights[asset_id]} vs editor {weight}"
        assert owner.cash_weight == pytest.approx(editor.cash_weight, rel=1e-9, abs=1e-12)

        owner_twrr = portfolio_twrr_returns(owner.portfolio_report, observation_dates=frozenset())
        editor_twrr = portfolio_twrr_returns(editor.portfolio_report, observation_dates=frozenset())
        baseline, dates, returns, calendar_days, _annualization, _coverage = editor_twrr
        assert returns, "the editor's portfolio TWRR has no return: the check would prove nothing"
        assert (owner_twrr[0], owner_twrr[1], owner_twrr[3]) == (baseline, dates, calendar_days)
        assert owner_twrr[2] == pytest.approx(returns, rel=1e-9, abs=1e-12)

        # Its money does scale: the stress plugin's impact amounts read scope_value and asset_values.
        _assert_scaled("risk scope_value", owner.scope_value, editor.scope_value, THIRTY)
        print_success("the risk scope of one broker has the same weights and returns at 30 % and whole")


# =============================================================================
# (h) — THE RISK SCOPE OF ONE BROKER, WHOLE: apply_ownership_share on PortfolioRiskScope
# =============================================================================

#: The hypothetical stress the test runs: every STOCK (X and Y are stocks) down 20 %.
_STRESS_PARAMETERS = {"method": "hypothetical", "dimension": "asset_class", "bucket_shocks": {"STOCK": -0.2}}


async def _stress(book: _Book, user_id: int, apply_ownership_share: bool | None = None):
    """The scope inputs and the hypothetical stress computed on them, by the path ``RiskService`` takes: ``load_scope_inputs``,
    ``build_execution_context``, the classifications of the scope's assets, ``StressAnalytic.compute``. The prepared series
    are the empty set ``prepare_asset_series`` returns for no asset: a hypothetical stress reads only the composition
    (``requested_scope_asset_ids``, weights, ``asset_values``, ``scope_value``), and no price query or market calendar is
    needed for it."""
    request = _risk_request(book, apply_ownership_share, stress=True)
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        inputs = await load_scope_inputs(session, user_id=user_id, request=request)
        classifications = await load_asset_classifications(session, inputs.requested_asset_ids)
    prepared = prepare_asset_series_set([], requested_range=request.date_range, target_currency=EUR)
    context = replace(build_execution_context(request=request, scope_inputs=inputs, prepared=prepared), asset_classifications=classifications)
    params = StressParams.model_validate(_STRESS_PARAMETERS)
    assert params.method == RiskStressMethod.HYPOTHETICAL and params.dimension == RiskScenarioDimension.ASSET_CLASS
    return inputs, context, StressAnalytic().compute(params, context).output


def _assert_same_values(label: str, owner: dict[int, Decimal], editor: dict[int, Decimal]) -> None:
    assert owner.keys() == editor.keys(), f"{label}: assets {sorted(owner)} vs {sorted(editor)}"
    for asset_id, value in editor.items():
        assert owner[asset_id] == value, f"{label}: asset {asset_id}: owner {owner[asset_id]} vs editor {value}"


class TestRiskScopeWholeBroker:
    @pytest.mark.asyncio
    async def test_the_whole_scope_and_its_stress_are_the_editors(self, tmp_path):
        print_section("MF6-3 (h): risk scope of broker A, owner 30 % with apply_ownership_share=False — the editor's scope value, asset values and stress amounts")
        async with _private_book(tmp_path, THIRTY, THIRTY) as book:
            editor_inputs, editor_context, editor_stress = await _stress(book, book.editor_id)
            assert editor_inputs.scope_value and editor_inputs.scope_value > 0 and editor_inputs.asset_values, "the editor's scope has no value: the check would prove nothing"
            assert editor_stress.impact_amount is not None and editor_stress.impact_amount != 0, "the editor's stress has no amount: the check would prove nothing"
            owner_default_inputs, _, owner_default_stress = await _stress(book, book.owner_id)
            owner_inputs, owner_context, owner_stress = await _stress(book, book.owner_id, apply_ownership_share=False)

        # The scope: the whole broker's money, the editor's weights.
        assert owner_inputs.composition_error is None, owner_inputs.composition_error
        assert owner_inputs.scope_value == editor_inputs.scope_value, f"scope_value: owner {owner_inputs.scope_value} vs editor {editor_inputs.scope_value}"
        _assert_same_values("asset_values", dict(owner_inputs.asset_values), dict(editor_inputs.asset_values))
        assert owner_inputs.weights.keys() == editor_inputs.weights.keys()
        for asset_id, weight in editor_inputs.weights.items():
            assert owner_inputs.weights[asset_id] == pytest.approx(weight, rel=1e-9, abs=1e-12)
        # What the plugin receives.
        assert owner_context.scope_value == editor_context.scope_value
        _assert_same_values("context.asset_values", dict(owner_context.asset_values), dict(editor_context.asset_values))
        # The stress: the same return, its amounts on the whole value.
        assert owner_stress.portfolio_return == pytest.approx(editor_stress.portfolio_return, rel=1e-9, abs=1e-12)
        assert owner_stress.impact_amount == editor_stress.impact_amount, f"stress impact_amount: owner {owner_stress.impact_amount} vs editor {editor_stress.impact_amount}"
        owner_impacts = {impact.asset_id: impact.impact_amount for impact in owner_stress.impacts}
        editor_impacts = {impact.asset_id: impact.impact_amount for impact in editor_stress.impacts}
        _assert_same_values("stress impacts", owner_impacts, editor_impacts)
        # The default keeps the share: 0.3 × the whole, the same return.
        _assert_scaled("default scope_value", owner_default_inputs.scope_value, editor_inputs.scope_value, THIRTY)
        _assert_scaled("default stress impact_amount", owner_default_stress.impact_amount, editor_stress.impact_amount, THIRTY)
        assert owner_default_stress.portfolio_return == pytest.approx(editor_stress.portfolio_return, rel=1e-9, abs=1e-12)
        print_success("with the option the 30 % owner's risk money is the whole broker's; by default it stays 0.3 ×")

    @pytest.mark.asyncio
    async def test_an_owner_at_zero_has_a_composition_with_the_option(self, tmp_path):
        print_section("MF6-3 (h): risk scope of broker A, owner 0 % — the option False gives the editor's composition, the default an empty one")
        async with _private_book(tmp_path, Decimal("0"), Decimal("0")) as book:
            editor = await _scope_inputs(book, book.editor_id)
            assert editor.composition_error is None and editor.scope_value and editor.scope_value > 0, (editor.composition_error, editor.scope_value)
            default = await _scope_inputs(book, book.owner_id)
            whole = await _scope_inputs(book, book.owner_id, apply_ownership_share=False)
        # Today's default: at 0 % every quantity is scaled to 0, under the dust threshold, so the summary holds no asset
        # — an empty composition (no asset, no weight, value 0), not the «requires positive scope NAV» error, which
        # load_scope_inputs sets only when the scope holds assets.
        assert default.requested_asset_ids == () and default.weights == {} and default.asset_values == {}, (default.requested_asset_ids, default.weights)
        assert default.scope_value == 0, default.scope_value
        assert default.composition_error is None, default.composition_error
        assert editor.requested_asset_ids, "the editor's scope holds no asset: the check would prove nothing"
        assert whole.requested_asset_ids == editor.requested_asset_ids
        assert whole.composition_error is None, whole.composition_error
        assert whole.scope_value is not None and whole.scope_value > 0
        assert whole.scope_value == editor.scope_value, f"scope_value: owner 0 % whole {whole.scope_value} vs editor {editor.scope_value}"
        _assert_same_values("asset_values", dict(whole.asset_values), dict(editor.asset_values))
        assert whole.weights.keys() == editor.weights.keys()
        for asset_id, weight in editor.weights.items():
            assert whole.weights[asset_id] == pytest.approx(weight, rel=1e-9, abs=1e-12)
        assert whole.cash_weight == pytest.approx(editor.cash_weight, rel=1e-9, abs=1e-12)
        print_success("the 0 % owner's whole risk scope is the editor's; the default holds no asset")
