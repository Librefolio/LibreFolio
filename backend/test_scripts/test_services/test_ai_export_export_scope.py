"""78 L10 — the scope fact of a Portfolio export: which of the user's brokers it covers, when it leaves some out.

WHAT. ``AiExportSnapshotResponse.export_scope`` is present only when a Portfolio export leaves out at least one broker
the user owns, and then says which brokers it includes and which owned brokers stay out, by name (developer, D12 (b)).
Without it the prompt renders exactly as before L10.

WHY. The Dashboard sends its owned brokers when nothing is filtered, and since 78 L10b the backend reads a request
without brokers as the owned ones too (``prepare_request``; until then every accessible one). «The user's brokers» must
therefore be the OWNED ones, by the Dashboard's own
rule (``getOwnedBrokers``: role owner, share above zero): with «accessible», a user with a broker shared by someone
else would see the block with no filter at all, naming someone else's broker.

THE BOOK, on a private SQLite file under ``tmp_path``: user U with five brokers — B1 owner at share 1, B2 owner at share
0.5, B3 owner at share 0 (counts nothing: not U's), B4 viewer, B5 editor. Owned: B1 and B2. The snapshot is built by
the real ``AiExportSnapshotService`` with one stub component that names no broker, so the entity directory holds the
scope's brokers only.

- ES-01: the Dashboard's unfiltered list (B1, B2) → no fact.
- ES-02: a request with no brokers (78 L10b: the owned ones, B1 and B2) → no fact, and the entity directory names only
  B1 and B2.
- ES-03: a filter on B1 → included [B1], B2 left out by name; only B1 in the entity directory.
- ES-04: an API request including a shared broker (B1, B4) → included [B1, B4], B2 left out: a shared broker can be
  included, never listed as left out.
- ES-05: a request on a shared broker alone (B4) → both owned brokers left out.
- ES-06: the owned-broker rule itself — a zero share and a shared broker are not owned.
- ES-07: a Broker export never carries the fact.

Isolation: PURE with respect to the lane (private file, NullPool, the engine disposed at teardown). No lane database,
no server, no network, no sleep.

Runs in ``./dev.py test services ai-export``; alone:
``pipenv run python -m pytest -q backend/test_scripts/test_services/test_ai_export_export_scope.py``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel  # every model, for create_all
from backend.app.db.models import Broker, BrokerUserAccess, User, UserRole
from backend.app.schemas.ai_export_runtime import (
    AI_EXPORT_CATALOG_VERSION,
    AiExportBrokerSnapshotRequest,
    AiExportDatasetSelection,
    AiExportDetailLevel,
    AiExportPortfolioSnapshotRequest,
)
from backend.app.services.ai_export.analyses.spec import AnalysisRegistry
from backend.app.services.ai_export.catalog_visibility import CatalogVisibility
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.types import ALL_DETAIL_LEVELS, Domain, PeriodBehavior
from backend.app.services.ai_export.datasets.spec import DatasetRegistry, DatasetSpec
from backend.app.services.ai_export.runtime_service import AiExportSnapshotService

START = date(2026, 1, 1)
END = date(2026, 3, 31)

# (label, role, share)
_ACCESSES = (
    ("B1", UserRole.OWNER, Decimal("1")),
    ("B2", UserRole.OWNER, Decimal("0.5")),
    ("B3", UserRole.OWNER, Decimal("0")),
    ("B4", UserRole.VIEWER, Decimal("1")),
    ("B5", UserRole.EDITOR, Decimal("1")),
)


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    user_id: int
    brokers: dict[str, int]


class _Value(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: int


def _component(domain: Domain) -> ComponentSpec:
    def _build(context, dependencies):  # noqa: ARG001
        return _Value(value=1)

    return ComponentSpec(
        component_id=f"{domain.value}.value",
        version=1,
        domains=frozenset({domain}),
        output_model=_Value,
        builder=_build,
        period_behavior=PeriodBehavior.WINDOWED,
    )


def _dataset(domain: Domain) -> DatasetSpec:
    dataset_id = f"{domain.value}.values"
    return DatasetSpec(
        dataset_id=dataset_id,
        version=1,
        domain=domain,
        display_i18n_key=f"aiExport.dataset.{dataset_id}.display",
        description_i18n_key=f"aiExport.dataset.{dataset_id}.description",
        icon="database",
        applicability_code="always_applicable",
        applicable_pages=(domain.value,),
        required_component_ids=(f"{domain.value}.value",),
        optional_component_ids=(),
        section_order=(f"{domain.value}.value",),
        technical_requirements=(),
        period_semantics=PeriodBehavior.WINDOWED,
        supported_detail_levels=ALL_DETAIL_LEVELS,
        visibility=CatalogVisibility.PUBLIC,
    )


def _service(session: AsyncSession) -> AiExportSnapshotService:
    components = ComponentRegistry((_component(Domain.PORTFOLIO), _component(Domain.BROKER)))
    datasets = DatasetRegistry((_dataset(Domain.PORTFOLIO), _dataset(Domain.BROKER)), component_registry=components)
    return AiExportSnapshotService(session, component_registry=components, dataset_registry=datasets, analysis_registry=AnalysisRegistry((), dataset_registry=datasets))


def _common(domain: Domain) -> dict:
    return {
        "selection": AiExportDatasetSelection(kind="dataset", id=f"{domain.value}.values", version=1),
        "detail_level": AiExportDetailLevel.STANDARD,
        "period": {"start": START, "end": END},
        "target_currency": "EUR",
        "expected_catalog_version": AI_EXPORT_CATALOG_VERSION,
    }


def _portfolio_request(book: _Book, *labels: str) -> AiExportPortfolioSnapshotRequest:
    fields = {"broker_ids": [book.brokers[label] for label in labels]} if labels else {}
    return AiExportPortfolioSnapshotRequest(domain="portfolio", **fields, **_common(Domain.PORTFOLIO))


async def _snapshot(book: _Book, request):
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await _service(session).build_snapshot(book.user_id, request)


@pytest_asyncio.fixture
async def book(tmp_path: Path) -> AsyncIterator[_Book]:
    """U and its five brokers on a private SQLite file; the engine disposed after."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'l10_export_scope.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            user = User(username="l10_export_scope", email="l10_export_scope@test.com", hashed_password="fakehash", is_active=True)
            brokers = {label: Broker(name=f"L10 broker {label}") for label, _role, _share in _ACCESSES}
            session.add_all([user, *brokers.values()])
            await session.flush()
            session.add_all(BrokerUserAccess(broker_id=brokers[label].id, user_id=user.id, role=role, share_percentage=share) for label, role, share in _ACCESSES)
            await session.commit()
            yield _Book(engine=engine, user_id=user.id, brokers={label: broker.id for label, broker in brokers.items()})
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_es01_the_dashboards_unfiltered_list_carries_no_fact(book):
    response = await _snapshot(book, _portfolio_request(book, "B1", "B2"))
    assert response.export_scope is None


@pytest.mark.asyncio
async def test_es02_a_request_without_brokers_carries_no_fact(book):
    response = await _snapshot(book, _portfolio_request(book))
    assert response.export_scope is None, "the owned brokers: no owned broker is left out"
    # 78 L10b: the owned brokers, never every accessible one (B3 at share 0, B4 viewer, B5 editor stay out)
    assert {entry.broker_id for entry in response.entity_directory.brokers} == {book.brokers["B1"], book.brokers["B2"]}


@pytest.mark.asyncio
async def test_es03_a_filter_says_what_it_includes_and_how_many_are_out(book):
    response = await _snapshot(book, _portfolio_request(book, "B1"))

    scope = response.export_scope
    assert scope is not None
    assert scope.included_broker_ids == (book.brokers["B1"],)
    assert [(entry.broker_id, entry.display_name) for entry in scope.excluded_brokers] == [(book.brokers["B2"], "L10 broker B2")]
    assert [entry.broker_id for entry in response.entity_directory.brokers] == [book.brokers["B1"]], "the directory names what the data covers only"


@pytest.mark.asyncio
async def test_es04_an_included_shared_broker_is_not_counted_among_the_users(book):
    response = await _snapshot(book, _portfolio_request(book, "B1", "B4"))

    scope = response.export_scope
    assert scope is not None
    assert scope.included_broker_ids == tuple(sorted((book.brokers["B1"], book.brokers["B4"])))
    assert [entry.broker_id for entry in scope.excluded_brokers] == [book.brokers["B2"]]


@pytest.mark.asyncio
async def test_es05_a_shared_broker_alone_leaves_out_every_owned_one(book):
    response = await _snapshot(book, _portfolio_request(book, "B4"))

    scope = response.export_scope
    assert scope is not None
    assert scope.included_broker_ids == (book.brokers["B4"],)
    # Only the owned brokers are named as left out: never B3 (zero share) nor B5 (editor), names of someone else's
    assert [entry.display_name for entry in scope.excluded_brokers] == ["L10 broker B1", "L10 broker B2"]


@pytest.mark.asyncio
async def test_es06_owned_means_role_owner_and_a_share_above_zero(book):
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        owned = await _service(session)._owned_broker_ids(book.user_id)

    assert owned == frozenset({book.brokers["B1"], book.brokers["B2"]}), "a zero share, a viewer and an editor are not the user's brokers"


@pytest.mark.asyncio
async def test_es07_a_broker_export_never_carries_the_fact(book):
    request = AiExportBrokerSnapshotRequest(domain="broker", broker_id=book.brokers["B1"], **_common(Domain.BROKER))

    response = await _snapshot(book, request)

    assert response.export_scope is None
