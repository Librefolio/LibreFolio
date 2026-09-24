"""Focused ASGI tests for deterministic risk endpoints."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.api.v1.risk import (
    get_risk_scenario_catalog,
    get_risk_service,
    router,
)
from backend.app.config import set_test_mode
from backend.app.db.models import Asset, AssetType, PriceHistory, User
from backend.app.db.session import get_async_engine
from backend.app.schemas.risk import (
    RiskAnalyticResult,
    RiskError,
    RiskErrorCode,
    RiskQueryResponse,
    RiskResultStatus,
)
from backend.app.services.data_quality_thresholds import RISK_MIN_OBSERVATIONS, STALE_PRICE_THRESHOLD_DAYS
from backend.app.services.risk.quant.workers import (
    shutdown_quant_worker_pools,
)
from backend.app.services.risk.scenario_catalog import (
    load_risk_scenario_catalog,
)
from backend.app.services.risk.service import (
    RiskScopeAccessError,
    RiskScopeNotFoundError,
    RiskService,
)

API_BASE = "/api/v1/risk"
USER_ID = 41

FIXTURE_USERNAME = "e2e_test_user"


async def fixture_user_id() -> int:
    """Resolve the seeded fixture user, failing with an actionable message.

    These tests assert against the mock portfolio created by `db populate`.
    A bare scalar_one() raises NoResultFound from deep inside SQLAlchemy, which
    says nothing about the missing precondition, so state it explicitly.
    """
    set_test_mode(True)
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        user_id = (await session.execute(select(User.id).where(User.username == FIXTURE_USERNAME))).scalar_one_or_none()

    if user_id is None:
        pytest.fail(
            f"Test database is not populated: user '{FIXTURE_USERNAME}' is missing.\n" "These tests run real analytics against the mock portfolio, so they need the fixtures.\n" "Seed them with: ./dev.py test db populate --force",
        )
    return user_id


def app_with_service(
    service: RiskService,
    *,
    authenticated: bool,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    if authenticated:

        async def current_user():
            return SimpleNamespace(id=USER_ID)

    else:

        async def current_user():
            raise HTTPException(status_code=401, detail="Not authenticated")

    def risk_service():
        return service

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_risk_service] = risk_service
    return app


def query_payload() -> dict[str, object]:
    return {
        "scope": {
            "kind": "asset_set",
            "asset_ids": [1, 2],
        },
        "date_range": {
            "start": "2026-01-01",
            "end": "2026-01-31",
        },
        "target_currency": "EUR",
        "mode": "historical",
        "analytics": [
            {
                "instance_id": "matrix",
                "analytic_code": "correlation",
            }
        ],
    }


@pytest.mark.asyncio
async def test_risk_catalog_requires_auth_and_lists_plugins():
    service = AsyncMock(spec=RiskService)
    unauthenticated = app_with_service(service, authenticated=False)
    authenticated = app_with_service(service, authenticated=True)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=unauthenticated),
        base_url="http://test",
    ) as client:
        response = await client.get(f"{API_BASE}/catalog")
        assert response.status_code == 401

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=authenticated),
        base_url="http://test",
    ) as client:
        response = await client.get(f"{API_BASE}/catalog")
        assert response.status_code == 200
        assert [item["analytic_code"] for item in response.json()["items"]] == [
            "asset_risk_return",
            # The weightless multi-asset family: one scope, one mode each, so the
            # catalogue cross-product offers no pair that has never been run.
            "asset_set_comparison",
            "asset_set_drawdown",
            "asset_set_kpi",
            "asset_set_risk_return",
            "asset_set_var",
            "comparison",
            "correlation",
            "drawdown_summary",
            "historical_kpi",
            "historical_var",
            "portfolio_optimization",
            "risk_contribution",
            "simulation",
            "stress",
        ]
        historical_kpi = next(item for item in response.json()["items"] if item["analytic_code"] == "historical_kpi")
        assert historical_kpi["supported_scopes"] == ["asset", "portfolio"]
        # Both modes: the same arithmetic over either the portfolio's real history or
        # today's composition replayed. L3 needs the second so its Sharpe, Sortino and
        # beta share one perimeter; `method` and `return_basis` keep the two apart.
        assert historical_kpi["supported_modes"] == ["historical", "current_composition"]


@pytest.mark.asyncio
async def test_scenario_catalog_requires_auth_and_publishes_typed_entries(tmp_path):
    catalog = load_risk_scenario_catalog(host_dir=tmp_path / "host")
    service = AsyncMock(spec=RiskService)
    unauthenticated = app_with_service(service, authenticated=False)
    authenticated = app_with_service(service, authenticated=True)
    unauthenticated.dependency_overrides[get_risk_scenario_catalog] = lambda: catalog
    authenticated.dependency_overrides[get_risk_scenario_catalog] = lambda: catalog

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=unauthenticated),
        base_url="http://test",
    ) as client:
        response = await client.get(f"{API_BASE}/scenario-catalog")
        assert response.status_code == 401

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=authenticated),
        base_url="http://test",
    ) as client:
        response = await client.get(f"{API_BASE}/scenario-catalog")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"]["schema_version"] == 1
    assert payload["status"]["built_in_count"] == 8
    assert payload["status"]["host_count"] == 0
    assert payload["status"]["warning_count"] == 0
    assert {item["scenario"]["id"] for item in payload["items"]} >= {
        "covid_crash_2020",
        "european_union_shock",
    }
    assert payload["geography_groups"][0]["id"] == "european_union"


@pytest.mark.asyncio
async def test_risk_query_delegates_authenticated_bulk_request():
    service = AsyncMock(spec=RiskService)
    service.execute.return_value = RiskQueryResponse(
        items=[
            RiskAnalyticResult(
                instance_id="matrix",
                analytic_code="correlation",
                status=RiskResultStatus.UNAVAILABLE,
                error=RiskError(
                    code=RiskErrorCode.INSUFFICIENT_HISTORY,
                    message="Not enough observations",
                ),
            )
        ]
    )
    app = app_with_service(service, authenticated=True)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"{API_BASE}/query",
            json=query_payload(),
        )

    assert response.status_code == 200
    assert response.json()["items"][0]["status"] == "unavailable"
    service.execute.assert_awaited_once()
    call = service.execute.await_args.kwargs
    assert call["user_id"] == USER_ID
    assert call["request"].scope.kind.value == "asset_set"


@pytest.mark.asyncio
async def test_risk_query_accepts_typed_historical_replay_options():
    service = AsyncMock(spec=RiskService)
    service.execute.return_value = RiskQueryResponse(
        items=[
            RiskAnalyticResult(
                instance_id="replay",
                analytic_code="stress",
                status=RiskResultStatus.UNAVAILABLE,
                error=RiskError(
                    code=RiskErrorCode.INSUFFICIENT_HISTORY,
                    message="Fixture response",
                ),
            )
        ]
    )
    app = app_with_service(service, authenticated=True)
    payload = {
        "scope": {"kind": "asset_set", "asset_ids": [1, 2, 4]},
        "date_range": {
            "start": "2026-01-01",
            "end": "2026-01-31",
        },
        "target_currency": "EUR",
        "mode": "current_composition",
        "composition_policy": "current_buy_and_hold",
        "analytics": [
            {
                "instance_id": "replay",
                "analytic_code": "stress",
                "parameters": {
                    "method": "historical_replay",
                    "replay_range": {
                        "start": "2020-02-01",
                        "end": "2020-03-31",
                    },
                    "proxy_assets": [
                        {"asset_id": 4, "proxy_asset_id": 9},
                        {"asset_id": 1, "proxy_asset_id": 8},
                    ],
                    "excluded_assets": [2],
                },
            }
        ],
    }

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"{API_BASE}/query",
            json=payload,
        )

    assert response.status_code == 200
    request = service.execute.await_args.kwargs["request"]
    parameters = request.analytics[0].parameters
    assert parameters["proxy_assets"] == [
        {"asset_id": 4, "proxy_asset_id": 9},
        {"asset_id": 1, "proxy_asset_id": 8},
    ]
    assert parameters["excluded_assets"] == [2]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (RiskScopeAccessError("Broker is not accessible"), 403),
        (RiskScopeNotFoundError("Asset does not exist"), 404),
    ],
)
async def test_risk_query_maps_scope_errors(error, status_code):
    service = AsyncMock(spec=RiskService)
    service.execute.side_effect = error
    app = app_with_service(service, authenticated=True)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"{API_BASE}/query",
            json=query_payload(),
        )

    assert response.status_code == status_code


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scope",
    [
        {"kind": "unknown"},
        {"kind": "broker", "broker_id": 3},
    ],
)
async def test_risk_query_rejects_invalid_discriminator_before_service(scope):
    service = AsyncMock(spec=RiskService)
    app = app_with_service(service, authenticated=True)
    payload = query_payload()
    payload["scope"] = scope

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"{API_BASE}/query",
            json=payload,
        )

    assert response.status_code == 422
    service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_risk_query_runs_all_analytics_against_populated_test_database():
    user_id = await fixture_user_id()

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def current_user():
        return SimpleNamespace(id=user_id)

    app.dependency_overrides[get_current_user] = current_user
    end = date.today() - timedelta(days=3)
    start = end - timedelta(days=297)

    historical_payload = {
        "scope": {"kind": "portfolio", "broker_ids": [3]},
        "date_range": {
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "target_currency": "EUR",
        "mode": "historical",
        "analytics": [
            {"instance_id": "kpi", "analytic_code": "historical_kpi"},
            {"instance_id": "matrix", "analytic_code": "correlation"},
            {
                "instance_id": "var",
                "analytic_code": "historical_var",
                "parameters": {
                    "confidence_level": 0.95,
                    "horizon_days": 5,
                },
            },
            {
                "instance_id": "comparison",
                "analytic_code": "comparison",
                "parameters": {"comparison_asset_id": 1},
            },
            {
                "instance_id": "optimization",
                "analytic_code": "portfolio_optimization",
                "parameters": {
                    "strategy": "min_risk",
                    "include_frontier": True,
                    "frontier_points": 5,
                },
            },
        ],
    }
    current_payload = {
        "scope": {"kind": "portfolio", "broker_ids": [3]},
        "date_range": {
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "target_currency": "EUR",
        "mode": "current_composition",
        "composition_policy": "current_buy_and_hold",
        "analytics": [
            {
                "instance_id": "pctr",
                "analytic_code": "risk_contribution",
            },
            {
                "instance_id": "stress",
                "analytic_code": "stress",
                "parameters": {
                    "method": "hypothetical",
                    "dimension": "sector",
                    "bucket_shocks": {"Other": -0.2},
                },
            },
            {"instance_id": "var", "analytic_code": "historical_var"},
            {
                "instance_id": "simulation",
                "analytic_code": "simulation",
                "parameters": {
                    "horizon_days": 30,
                    "paths": 256,
                    "seed": 123,
                },
            },
        ],
    }

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            historical_response = await client.post(
                f"{API_BASE}/query",
                json=historical_payload,
            )
            current_response = await client.post(
                f"{API_BASE}/query",
                json=current_payload,
            )
    finally:
        await shutdown_quant_worker_pools()

    assert historical_response.status_code == 200
    assert current_response.status_code == 200
    historical_items = historical_response.json()["items"]
    current_items = current_response.json()["items"]
    assert all(item["status"] in {"ok", "partial"} and item["output"] is not None for item in [*historical_items, *current_items])
    for item in [*historical_items, *current_items]:
        assert item["metadata"]["scope"] == "portfolio"
        assert item["metadata"]["scope_reference"] == "portfolio:3"
        assert item["metadata"]["broker_ids"] == [3]
        assert item["metadata"]["composition_as_of"] == end.isoformat()
    historical_var = next(item["output"] for item in historical_items if item["analytic_code"] == "historical_var")
    assert historical_var["conditional_value_at_risk"] >= historical_var["value_at_risk"] >= 0
    optimization = next(item["output"] for item in historical_items if item["analytic_code"] == "portfolio_optimization")
    assert optimization["kind"] == "optimization"
    assert sum(item["weight"] for item in optimization["weights"]) == pytest.approx(1.0, abs=1e-6)
    assert len(optimization["frontier"]) == 5
    contribution = next(item["output"] for item in current_items if item["analytic_code"] == "risk_contribution")
    assert sum(item["percentage_contribution"] for item in contribution["items"]) == pytest.approx(1.0)
    stress_result = next(item for item in current_items if item["analytic_code"] == "stress")
    stress = stress_result["output"]
    assert stress["dimension"] == "sector"
    assert stress_result["metadata"]["params"]["bucket_shocks"] == {"Other": -0.2}
    assert all(impact["bucket_audit"] and impact["bucket_audit"][0]["applied_bucket_id"] == "Other" for impact in stress["impacts"])
    simulation = next(item["output"] for item in current_items if item["analytic_code"] == "simulation")
    simulation_result = next(item for item in current_items if item["analytic_code"] == "simulation")
    assert simulation["kind"] == "simulation"
    assert simulation["sampling_method"] == "mc"
    assert simulation["path_count"] == 256
    assert "sampling" not in simulation
    assert "paths" not in simulation
    assert simulation_result["metadata"]["random_seed"] == 123
    assert simulation_result["metadata"]["sobol_start_index"] is None
    assert simulation_result["metadata"]["params"]["random_seed"] == 123
    assert "seed" not in simulation_result["metadata"]["params"]
    assert simulation["percentile_bands"][0] == {
        "day": 0,
        "p05": pytest.approx(0),
        "p50": pytest.approx(0),
        "p95": pytest.approx(0),
    }
    assert len(simulation["percentile_bands"]) == 31


@pytest.mark.asyncio
async def test_risk_query_simulates_with_canonical_names_and_no_seed():
    """The canonical dialect, which no other API test speaks.

    Every other end-to-end simulation case sends the legacy aliases
    (``paths``/``seed``), and ``_infer_process`` deliberately routes legacy
    callers to GBM. That compatibility shield is correct policy — but it also
    exempted the whole suite from ever exercising the *default* engine, so a
    contradiction between the params validator (which forbids ``random_seed``
    under the block bootstrap) and the metadata validator (which used to
    require it) reached ``_success`` and returned 500 with every green gate
    still green. This test is that missing composition: canonical field names,
    no seed supplied, default process.
    """
    user_id = await fixture_user_id()

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def current_user():
        return SimpleNamespace(id=user_id)

    app.dependency_overrides[get_current_user] = current_user
    end = date.today() - timedelta(days=3)
    start = end - timedelta(days=297)

    payload = {
        "scope": {"kind": "portfolio", "broker_ids": [3]},
        "date_range": {"start": start.isoformat(), "end": end.isoformat()},
        "target_currency": "EUR",
        "mode": "current_composition",
        "composition_policy": "current_buy_and_hold",
        "analytics": [
            # The two controls travel in the same query as the subject. A lone
            # subject returning 200 proves only that it did not raise; sharing a
            # portfolio, a window and a response with two known-good dialects is
            # what makes its outcome comparable.
            {
                "instance_id": "control_legacy",
                "analytic_code": "simulation",
                "parameters": {"horizon_days": 30, "paths": 256, "seed": 123},
            },
            {
                "instance_id": "control_gbm",
                "analytic_code": "simulation",
                "parameters": {
                    "horizon_days": 30,
                    "path_count": 256,
                    "process": "gbm",
                    "random_seed": 123,
                },
            },
            {
                "instance_id": "subject_canonical",
                "analytic_code": "simulation",
                "parameters": {"horizon_days": 30, "path_count": 256},
            },
        ],
    }

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(f"{API_BASE}/query", json=payload)
    finally:
        await get_async_engine().dispose()

    assert response.status_code == 200, response.text
    items = {item["instance_id"]: item for item in response.json()["items"]}
    assert set(items) == {"control_legacy", "control_gbm", "subject_canonical"}
    # The subject must not merely succeed: it must degrade exactly as much as
    # the controls do. `partial` is a property of the fixture portfolio, so an
    # equality here stays honest if the fixtures change, while `== "ok"` would
    # be a false red on a correct product.
    statuses = {key: item["status"] for key, item in items.items()}
    assert statuses["subject_canonical"] == statuses["control_legacy"] == statuses["control_gbm"], statuses
    assert statuses["subject_canonical"] not in {"unavailable", "failed"}, items["subject_canonical"]

    # The legacy dialect is deliberately routed to GBM by `_infer_process`; that
    # policy is what kept the default engine out of every end-to-end test.
    assert items["control_legacy"]["output"]["process"] == "gbm"
    assert items["control_gbm"]["output"]["process"] == "gbm"

    output = items["subject_canonical"]["output"]
    metadata = items["subject_canonical"]["metadata"]
    assert output["process"] == "block_bootstrap"
    assert output["sampling_method"] == "mc"
    assert output["path_count"] == 256
    # The bootstrap discloses reproducibility through its own seed, never a
    # `random_seed`: the two are mutually exclusive by construction.
    assert metadata["bootstrap_seed"] is not None
    assert metadata["random_seed"] is None
    assert metadata["sobol_start_index"] is None
    assert output["block_length_days"] is not None
    assert len(output["percentile_bands"]) == 31


@pytest.mark.asyncio
async def test_portfolio_optimization_supports_all_scopes_and_strategies():
    user_id = await fixture_user_id()

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def current_user():
        return SimpleNamespace(id=user_id)

    app.dependency_overrides[get_current_user] = current_user
    end = date.today() - timedelta(days=3)
    start = end - timedelta(days=297)
    cases = [
        (
            {"kind": "portfolio", "broker_ids": [3]},
            "max_sharpe",
            {"ok", "partial"},
        ),
        (
            {"kind": "asset_set", "asset_ids": [1, 2]},
            "risk_parity",
            {"ok", "partial"},
        ),
        (
            # Asset 17 (Test KRW Stock) carries transactions but no price history by
            # design, so its series is unusable and the optimizer has nothing to work
            # with. This case exists to cover the unavailable branch; it used to point
            # at the whole portfolio, which was unavailable only because the seeded
            # history was too short to optimize — a defect the fixtures no longer have.
            {"kind": "asset_set", "asset_ids": [17]},
            "min_risk",
            {"unavailable"},
        ),
    ]

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            for scope, strategy, expected_statuses in cases:
                response = await client.post(
                    f"{API_BASE}/query",
                    json={
                        "scope": scope,
                        "date_range": {
                            "start": start.isoformat(),
                            "end": end.isoformat(),
                        },
                        "target_currency": "EUR",
                        "mode": "historical",
                        "analytics": [
                            {
                                "instance_id": strategy,
                                "analytic_code": ("portfolio_optimization"),
                                "parameters": {
                                    "strategy": strategy,
                                },
                            },
                        ],
                    },
                )
                assert response.status_code == 200
                item = response.json()["items"][0]
                assert item["status"] in expected_statuses, item.get("error")
                if item["output"] is not None:
                    assert item["output"]["strategy"] == strategy
                    assert sum(weight["weight"] for weight in item["output"]["weights"]) == pytest.approx(1.0, abs=1e-6)
                else:
                    assert item["error"]["code"] == "insufficient_history"

            invalid = await client.post(
                f"{API_BASE}/query",
                json={
                    "scope": {
                        "kind": "asset_set",
                        "asset_ids": [1, 2],
                    },
                    "date_range": {
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                    },
                    "target_currency": "EUR",
                    "mode": "historical",
                    "analytics": [
                        {
                            "instance_id": "invalid",
                            "analytic_code": ("portfolio_optimization"),
                            "parameters": {
                                "max_weight": 0.4,
                            },
                        },
                    ],
                },
            )
    finally:
        await shutdown_quant_worker_pools()

    assert invalid.status_code == 200
    invalid_item = invalid.json()["items"][0]
    assert invalid_item["status"] == "unavailable"
    assert invalid_item["error"]["code"] == "invalid_parameters"


# ---------------------------------------------------------------------------
# POST /risk/eligibility — whether each asset can take part in an analysis of a period
# (developer's decision of 24/09/2026)
# ---------------------------------------------------------------------------

ELIGIBILITY_START = date(2013, 1, 7)
ELIGIBILITY_END = date(2013, 3, 29)


def quote_days(first: date, last: date, *, step: int = 1) -> list[date]:
    return [first + timedelta(days=offset) for offset in range(0, (last - first).days + 1, step)]


def eligibility_payload(asset_ids: list[int], **overrides) -> dict[str, object]:
    return {
        "asset_ids": asset_ids,
        "date_range": {"start": ELIGIBILITY_START.isoformat(), "end": ELIGIBILITY_END.isoformat()},
        "target_currency": "EUR",
        **overrides,
    }


async def store_quoted_assets(specs: dict[str, tuple[str, list[date]]], marker: str) -> dict[str, int]:
    """Commit one asset per spec, with a price row on each of its days."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        assets = {key: Asset(display_name=f"Eligibility {key} {marker}", currency=currency, asset_type=AssetType.STOCK) for key, (currency, _days) in specs.items()}
        session.add_all(assets.values())
        await session.flush()
        session.add_all(PriceHistory(asset_id=assets[key].id, date=day, close=Decimal("100") + offset, currency=currency, source_plugin_key="eligibility_api_test") for key, (currency, days) in specs.items() for offset, day in enumerate(days))
        await session.commit()
        return {key: asset.id for key, asset in assets.items()}


async def delete_quoted_assets(asset_ids: list[int]) -> None:
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await session.execute(delete(PriceHistory).where(PriceHistory.asset_id.in_(asset_ids)))
        await session.execute(delete(Asset).where(Asset.id.in_(asset_ids)))
        await session.commit()


@pytest.mark.asyncio
async def test_asset_eligibility_requires_auth_and_rejects_an_invalid_request_before_the_service():
    service = AsyncMock(spec=RiskService)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_with_service(service, authenticated=False)),
        base_url="http://test",
    ) as client:
        unauthenticated = await client.post(f"{API_BASE}/eligibility", json=eligibility_payload([1]))

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_with_service(service, authenticated=True)),
        base_url="http://test",
    ) as client:
        no_asset = await client.post(f"{API_BASE}/eligibility", json=eligibility_payload([]))
        bad_currency = await client.post(f"{API_BASE}/eligibility", json=eligibility_payload([1], target_currency="ZZZ"))

    assert unauthenticated.status_code == 401
    assert no_asset.status_code == 422
    assert bad_currency.status_code == 422
    service.asset_eligibility.assert_not_awaited()


@pytest.mark.asyncio
async def test_asset_eligibility_judges_each_asset_on_its_own_quotes_in_request_order():
    set_test_mode(True)
    start, end = ELIGIBILITY_START, ELIGIBILITY_END
    specs = {
        # Exactly the floor, spread over the whole period.
        "eligible": ("EUR", quote_days(start, start + timedelta(days=76), step=4)),
        "too_few": ("EUR", quote_days(start, start + timedelta(days=72), step=4)),
        # Quoted, but only before the period.
        "no_prices": ("EUR", quote_days(start - timedelta(days=30), start - timedelta(days=10))),
        "late": ("EUR", quote_days(start + timedelta(days=10), end)),
        "stale": ("EUR", quote_days(start, end - timedelta(days=10))),
        # A currency with no rate to the target anywhere in the suite.
        "no_fx": ("KES", quote_days(start, end)),
    }
    assert len(specs["eligible"][1]) == RISK_MIN_OBSERVATIONS
    assert len(specs["too_few"][1]) == RISK_MIN_OBSERVATIONS - 1

    ids = await store_quoted_assets(specs, uuid4().hex)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def current_user():
        return SimpleNamespace(id=USER_ID)

    app.dependency_overrides[get_current_user] = current_user
    requested = [ids["stale"], ids["eligible"], ids["no_fx"], ids["eligible"], ids["late"], ids["too_few"], ids["no_prices"], ids["stale"]]
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(f"{API_BASE}/eligibility", json=eligibility_payload(requested))
    finally:
        await delete_quoted_assets(list(ids.values()))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["min_quotes"] == RISK_MIN_OBSERVATIONS == 20
    assert body["stale_days"] == STALE_PRICE_THRESHOLD_DAYS == 7
    # Request order, first occurrence kept, duplicates dropped.
    assert [item["asset_id"] for item in body["items"]] == [ids["stale"], ids["eligible"], ids["no_fx"], ids["late"], ids["too_few"], ids["no_prices"]]

    by_key = {key: next(item for item in body["items"] if item["asset_id"] == asset_id) for key, asset_id in ids.items()}
    assert {key: (item["level"], item["reasons"]) for key, item in by_key.items()} == {
        "eligible": ("eligible", []),
        "too_few": ("ineligible", ["too_few_quotes"]),
        "no_prices": ("ineligible", ["no_prices"]),
        "no_fx": ("ineligible", ["missing_fx"]),
        "late": ("warning", ["starts_late"]),
        "stale": ("warning", ["stale_at_end"]),
    }
    # The facts behind each verdict travel with it.
    assert (by_key["eligible"]["quotes_in_period"], by_key["eligible"]["first_quote"], by_key["eligible"]["last_quote"]) == (20, start.isoformat(), (start + timedelta(days=76)).isoformat())
    assert (by_key["no_prices"]["quotes_in_period"], by_key["no_prices"]["first_quote"], by_key["no_prices"]["last_quote"]) == (0, (start - timedelta(days=30)).isoformat(), (start - timedelta(days=10)).isoformat())
    assert by_key["late"]["first_quote"] == (start + timedelta(days=10)).isoformat()
    assert by_key["stale"]["last_quote"] == (end - timedelta(days=10)).isoformat()
