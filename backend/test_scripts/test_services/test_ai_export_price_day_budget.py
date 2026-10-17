"""J-50 — an AI Export snapshot whose required price load exceeds the bulk day budget is refused as not applicable.

Workstream J «Numeri e analisi», release 1.3. Z-25 (N77) made ``AssetSourceManager.get_prices_bulk`` raise
``BulkTooManyDaysError`` (``backend/app/utils/date_range_limits.py``) when one request would build more than
``MAX_BULK_ITEM_DAYS`` per-day points. The AI Export's asset components call it: ``asset.market_snapshot``
(``components/asset_resources.py::load_asset_market_prices``) for the period, and the technical components
(``components/technical_shared.py``) with their signals' warm-up.

TODAY (base ``d67ac4603``) a REQUIRED component that raises it becomes ``RequiredComponentBuildError`` →
``AiExportSnapshotSourceError`` (``runtime_service.py``, ``build_snapshot``) → 503 ``snapshot_source_failure`` with
``reason_code`` None: «a source is unavailable, try again later», for a request that fails the same way every time.

THE RULE (coordinator, 17/10). In ``runtime_service.py`` a ``RequiredComponentBuildError`` whose root cause is a
``BulkTooManyDaysError`` raises ``AiExportSelectionNotApplicableError(<the selection's applicability_code>,
"too_many_price_days")`` → 422 ``selection_not_applicable`` with ``reason_code`` ``too_many_price_days``: a dataset
answers its own applicability code, an analysis its own (not its datasets'). GUARD: an OPTIONAL component over the budget is
left out as any failing optional component is (``Composer.compose_dataset``), and the snapshot builds.

THE BOOK. A user and an EUR asset with a close on every day from 1 January to 30 June 2024; the period is June 2024, in
EUR. The market snapshot loads the period: 30 points (1–30 June). The technical components load their signals' warm-up,
which reaches back to the first close: 182 points (1 January … 30 June). A budget of 10 stops the market snapshot; 100
lets it through and stops the technical load. The budget is lowered where the price query reads it,
``backend.app.services.assets.price_query.MAX_BULK_ITEM_DAYS`` (Z-25's seam). Every case first builds with the budget
untouched — the precondition, green today: the red is the budget's answer, not the book.

Isolation: a private SQLite file under ``tmp_path`` built by ``create_all`` (Z-25's pattern) — no lane database, no
server, no network; the market holiday table is an empty one (built for real, it takes a QuantLib process).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetType, PriceHistory, User
from backend.app.schemas.ai_export_runtime import (
    AI_EXPORT_CATALOG_VERSION,
    AiExportAnalysisSelection,
    AiExportAssetSnapshotRequest,
    AiExportDatasetSelection,
    AiExportDetailLevel,
    AiExportSnapshotResponse,
)
from backend.app.services.ai_export.analyses.catalog import build_analysis_registry
from backend.app.services.ai_export.datasets.catalog import build_dataset_registry
from backend.app.services.ai_export.runtime_service import AiExportSnapshotService
from backend.app.services.assets import price_query
from backend.app.services.risk import service as risk_service_module

PERIOD = {"start": date(2024, 6, 1), "end": date(2024, 6, 30)}
DATASETS = build_dataset_registry()
ANALYSES = build_analysis_registry(DATASETS)
# The two optional components of asset.position_and_history that load the technical price set.
TECHNICAL_OPTIONAL = ("asset.technical_coverage", "asset.position_market_context")


@dataclass(frozen=True)
class Book:
    user_id: int
    asset_id: int


# --------------------------------------------------------------------------- #
# The private database, the holiday table, the budget
# --------------------------------------------------------------------------- #


@pytest_asyncio.fixture
async def private_db(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file under tmp_path with the whole ORM schema, opened as production opens its own; disposed."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'ai_export_price_day_budget.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture(autouse=True)
def no_market_holidays(monkeypatch: pytest.MonkeyPatch) -> None:
    """The market holiday table, empty, wherever a snapshot awaits it (the prices' signals, the drawdown's risk run)."""

    async def _none() -> frozenset[date]:
        return frozenset()

    monkeypatch.setattr(price_query, "ensure_market_holidays", _none)
    monkeypatch.setattr(risk_service_module, "ensure_market_holidays", _none)


@pytest.fixture
def lower_budget(monkeypatch: pytest.MonkeyPatch) -> Callable[[int], None]:
    """Sets the item-day budget where ``get_prices_bulk`` reads it, for the test."""

    def lower(item_days: int) -> None:
        monkeypatch.setattr(price_query, "MAX_BULK_ITEM_DAYS", item_days)

    return lower


async def _book(engine: AsyncEngine) -> Book:
    """A user, and an EUR asset with a close on every day from 1 January to 30 June 2024, a different one each day."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username="j50_ai_export", email="j50_ai_export@test.com", hashed_password="fakehash", is_active=True)
        asset = Asset(display_name="J50 AI Export asset", currency="EUR", asset_type=AssetType.STOCK)
        session.add_all([user, asset])
        await session.flush()
        day, n = date(2024, 1, 1), 0
        while day <= date(2024, 6, 30):
            session.add(PriceHistory(asset_id=asset.id, date=day, close=Decimal(100) + Decimal(n % 7) + Decimal(n) / 10, currency="EUR", source_plugin_key="MANUAL"))
            day += timedelta(days=1)
            n += 1
        await session.commit()
        return Book(user_id=user.id, asset_id=asset.id)


# --------------------------------------------------------------------------- #
# Requests and answers
# --------------------------------------------------------------------------- #


def _dataset_request(book: Book, dataset_id: str) -> AiExportAssetSnapshotRequest:
    return AiExportAssetSnapshotRequest(
        domain="asset",
        selection=AiExportDatasetSelection(kind="dataset", id=dataset_id, version=DATASETS.get(dataset_id).version),
        detail_level=AiExportDetailLevel.STANDARD,
        period=PERIOD,
        target_currency="EUR",
        expected_catalog_version=AI_EXPORT_CATALOG_VERSION,
        asset_id=book.asset_id,
    )


def _analysis_request(book: Book, analysis_id: str) -> AiExportAssetSnapshotRequest:
    analysis = ANALYSES.get(analysis_id)
    return AiExportAssetSnapshotRequest(
        domain="asset",
        selection=AiExportAnalysisSelection(
            kind="analysis",
            id=analysis_id,
            version=analysis.version,
            instruction_template_id=analysis.instruction_template_id,
            instruction_template_version=analysis.instruction_template_version,
            response_contract_id=analysis.response_contract_id,
            response_contract_version=analysis.response_contract_version,
        ),
        detail_level=AiExportDetailLevel.STANDARD,
        period=PERIOD,
        target_currency="EUR",
        expected_catalog_version=AI_EXPORT_CATALOG_VERSION,
        asset_id=book.asset_id,
    )


async def _build(engine: AsyncEngine, book: Book, request: AiExportAssetSnapshotRequest) -> AiExportSnapshotResponse:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await AiExportSnapshotService(session).build_snapshot(book.user_id, request)


async def _refusal(engine: AsyncEngine, book: Book, request: AiExportAssetSnapshotRequest) -> Exception:
    """What ``build_snapshot`` raises; when it raises nothing, the test fails saying what it built."""
    try:
        response = await _build(engine, book, request)
    except Exception as exc:  # noqa: BLE001 — the refusal is the subject: any type is read, then compared
        return exc
    pytest.fail(f"no refusal: the snapshot was built with sections {[section.component_id for section in response.sections]}")


def _root_cause(error: BaseException) -> BaseException:
    """The end of the chain: ``cause`` of the build errors, then ``__cause__``."""
    seen: set[int] = set()
    current = error
    while id(current) not in seen:
        seen.add(id(current))
        following = getattr(current, "cause", None) or current.__cause__
        if not isinstance(following, BaseException):
            break
        current = following
    return current


def _answer(error: Exception) -> dict:
    """What a refusal says: its type, its codes, the component it names (None where it names none)."""
    return {
        "error": type(error).__name__,
        "applicability_code": getattr(error, "applicability_code", None),
        "reason_code": getattr(error, "reason_code", None),
        "component_id": getattr(error, "component_id", None),
    }


def _not_applicable_for_size(applicability_code: str) -> dict:
    return {"error": "AiExportSelectionNotApplicableError", "applicability_code": applicability_code, "reason_code": "too_many_price_days", "component_id": None}


def _sections(response: AiExportSnapshotResponse) -> list[str]:
    return [section.component_id for section in response.sections]


# --------------------------------------------------------------------------- #
# A required component over the budget
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("budget", "stopped_component"),
    [
        pytest.param(10, "asset.market_snapshot", id="the-market-snapshot-over-the-budget"),
        pytest.param(100, "asset.technical_coverage", id="the-technical-load-over-the-budget"),
    ],
)
async def test_a_dataset_whose_required_price_load_exceeds_the_budget_is_not_applicable_for_too_many_price_days(private_db, lower_budget, budget, stopped_component):
    """The dataset ``asset.market_history`` (applicability ``always_applicable``), June 2024: with a budget of 10 the
    market snapshot's 30 points do not fit; with 100 they do, and the required technical load's 182 do not. Either way
    ``build_snapshot`` raises ``AiExportSelectionNotApplicableError("always_applicable", "too_many_price_days")``.

    Today: ``AiExportSnapshotSourceError`` naming ``asset.market_snapshot`` (budget 10) or ``asset.technical_coverage``
    (budget 100), ``reason_code`` None — 503 ``snapshot_source_failure`` — its root cause ``BulkTooManyDaysError`` (30
    points over 10, 182 over 100).
    """
    book = await _book(private_db)
    request = _dataset_request(book, "asset.market_history")
    assert stopped_component in _sections(await _build(private_db, book, request))  # precondition: the budget untouched, it builds
    lower_budget(budget)

    refusal = await _refusal(private_db, book, request)

    assert _answer(refusal) == _not_applicable_for_size(DATASETS.get("asset.market_history").applicability_code), f"root cause: {_root_cause(refusal)!r}"


@pytest.mark.asyncio
async def test_an_analysis_whose_required_price_load_exceeds_the_budget_is_not_applicable_under_its_own_code(private_db, lower_budget):
    """The analysis ``asset.position_review`` — applicability ``requires_position``, its required dataset's
    ``always_applicable`` — with a budget of 10: the market snapshot of its dataset does not fit, and ``build_snapshot``
    raises ``AiExportSelectionNotApplicableError("requires_position", "too_many_price_days")``: the selection's code, the
    analysis's own. (With the budget untouched the user holds no position: ``no_position``, the precondition.)

    Today: ``AiExportSnapshotSourceError`` naming ``asset.market_snapshot``, ``reason_code`` None (503), its root cause
    ``BulkTooManyDaysError`` (30 points over 10).
    """
    book = await _book(private_db)
    request = _analysis_request(book, "asset.position_review")
    untouched = await _refusal(private_db, book, request)
    assert _answer(untouched) == {"error": "AiExportSelectionNotApplicableError", "applicability_code": "requires_position", "reason_code": "no_position", "component_id": None}
    lower_budget(10)

    refusal = await _refusal(private_db, book, request)

    assert _answer(refusal) == _not_applicable_for_size(ANALYSES.get("asset.position_review").applicability_code), f"root cause: {_root_cause(refusal)!r}"


# --------------------------------------------------------------------------- #
# GUARD: an optional component over the budget
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_guard_an_optional_component_over_the_budget_is_left_out_and_the_snapshot_builds(private_db, lower_budget):
    """GUARD (today's behaviour, pinned): the dataset ``asset.position_and_history`` with a budget of 100. Its required
    components fit — the market snapshot's 30 points among them — and so does its optional drawdown (a risk run of June);
    its two optional components that load the technical price set (182 points) do not. The snapshot builds without those
    two sections and with every other one it has with the budget untouched.
    """
    book = await _book(private_db)
    request = _dataset_request(book, "asset.position_and_history")
    untouched = _sections(await _build(private_db, book, request))
    assert set(TECHNICAL_OPTIONAL) <= set(untouched), untouched  # precondition: with the budget untouched, they are there
    lower_budget(100)

    sections = _sections(await _build(private_db, book, request))

    assert sections == [component_id for component_id in untouched if component_id not in TECHNICAL_OPTIONAL]
