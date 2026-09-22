"""
Direct unit tests for FX API handlers.

Focus: happy-path/main-branch coverage in backend/app/api/v1/fx.py
without live server/network dependency.
"""

import json
import sys
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from backend.app.api.v1 import fx as fx_api
from backend.app.db.models import FxConversionRoute
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.fx import FXConversionRouteItem, FXConversionRouteReadItem, FXDeleteItem, FXUpsertItem
from backend.app.schemas.refresh import FXSyncBulkResponse, FXSyncPairRequest, FXSyncPairResult, SyncDateRangeModel, SyncStatus
from backend.test_scripts.test_utils import print_section, print_success


def _mock_scalar_result(items):
    result = Mock()
    result.scalars.return_value.all.return_value = items
    return result


def test_build_providers_description_lists_codes(monkeypatch):
    """Description helper should embed discovered provider codes."""
    print_section("_build_providers_description")

    monkeypatch.setattr(
        fx_api.FXProviderRegistry,
        "list_providers",
        lambda: [
            {"code": "ECB", "name": "European Central Bank"},
            {"code": "FED", "name": "Federal Reserve"},
        ],
    )

    description = fx_api._build_providers_description()

    assert "Installed providers: ECB, FED" in description
    assert "Get the list of available FX rate providers." in description
    print_success("Provider description lists installed codes")


@pytest.mark.asyncio
async def test_list_providers_filters_hidden_and_sorts_targets(monkeypatch):
    """list_providers should hide internal providers and sort target currencies."""
    print_section("list_providers")

    class _DummyProvider:
        base_currency = "USD"
        base_currencies = ["USD", "USN"]
        icon = "/icons/fed.svg"
        description = "Dummy provider"
        description_i18n = {"it": "Provider finto"}
        warning_i18n = {"en": "Testing only"}
        docs_url = "https://example.test/fed"

        async def get_supported_currencies(self):
            return ["JPY", "EUR", "USD"]

    monkeypatch.setattr(
        fx_api.FXProviderRegistry,
        "list_providers",
        lambda: [
            {"code": "MANUAL", "name": "Manual"},
            {"code": "MOCKFX", "name": "Mock"},
            {"code": "FED", "name": "Federal Reserve"},
        ],
    )
    monkeypatch.setattr(
        fx_api.FXProviderRegistry,
        "get_provider_instance",
        lambda _code: _DummyProvider(),
    )

    providers = await fx_api.list_providers(providers=["manual", "fed"])

    assert len(providers) == 1
    assert providers[0].code == "FED"
    assert providers[0].target_currencies == ["EUR", "JPY", "USD"]
    assert providers[0].docs_url == "https://example.test/fed"
    assert providers[0].description_i18n == {"it": "Provider finto"}
    assert providers[0].warning_i18n == {"en": "Testing only"}
    print_success("Hidden providers filtered; targets sorted")


@pytest.mark.asyncio
async def test_sync_rates_success_and_future_validation(monkeypatch):
    """sync_rates should reject future end date and return service result on success."""
    print_section("sync_rates")

    session = AsyncMock()
    expected = FXSyncBulkResponse(
        results=[
            FXSyncPairResult(
                pair="EUR-USD",
                status=SyncStatus.OK,
                provider_used="MOCKFX",
                points_fetched=1,
                points_changed=1,
                errors=[],
            )
        ],
        success_count=1,
        date_range=SyncDateRangeModel(start=date(2025, 1, 1), end=date(2025, 1, 1)),
        total_points_changed=1,
    )
    sync_mock = AsyncMock(return_value=expected)
    monkeypatch.setattr(fx_api, "sync_pairs_bulk", sync_mock)

    good_body = FXSyncPairRequest(
        pairs=["USD-EUR"],
        start=date(2025, 1, 1),
        end=date(2025, 1, 1),
    )
    result = await fx_api.sync_rates(good_body, session=session, _current_user=Mock())
    assert result == expected
    sync_mock.assert_awaited_once()
    assert sync_mock.await_args.kwargs["pairs"] == ["EUR-USD"]

    future_body = FXSyncPairRequest(
        pairs=["EUR-USD"],
        start=date.today(),
        end=date.today() + timedelta(days=1),
    )
    with pytest.raises(HTTPException, match="future"):
        await fx_api.sync_rates(future_body, session=session, _current_user=Mock())

    reversed_range_body = Mock(
        start=date(2025, 1, 3),
        end=date(2025, 1, 1),
        pairs=["EUR-USD"],
    )
    with pytest.raises(HTTPException, match="before or equal"):
        await fx_api.sync_rates(reversed_range_body, session=session, _current_user=Mock())

    print_success("Success path + future-date validation covered")


@pytest.mark.asyncio
async def test_upsert_rates_endpoint_keeps_valid_item_and_normalizes(monkeypatch):
    """Mixed batch should keep valid item, invert reversed pair, collect validation error."""
    print_section("upsert_rates_endpoint")

    session = AsyncMock()
    monkeypatch.setattr(
        fx_api,
        "upsert_rates_bulk",
        AsyncMock(side_effect=[[(True, "inserted")], [(True, "updated")]]),
    )

    today = date.today()
    response = await fx_api.upsert_rates_endpoint(
        [
            FXUpsertItem(**{"date": today}, base="USD", quote="EUR", rate=Decimal("0.80"), source="MANUAL"),
            FXUpsertItem(**{"date": today}, base="EUR", quote="GBP", rate=Decimal("0.90"), source="MANUAL"),
            FXUpsertItem(**{"date": today}, base="EUR", quote="EUR", rate=Decimal("1.00"), source="MANUAL"),
        ],
        session=session,
        _current_user=Mock(),
    )

    assert response.success_count == 2
    assert len(response.results) == 2
    assert response.errors and "different" in response.errors[0]
    inverted_result = response.results[0]
    assert inverted_result.base == "EUR"
    assert inverted_result.quote == "USD"
    assert inverted_result.rate == Decimal("1.25")

    direct_result = response.results[1]
    assert direct_result.base == "EUR"
    assert direct_result.quote == "GBP"
    assert direct_result.rate == Decimal("0.90")
    print_success("Mixed upsert kept valid normalized row")


@pytest.mark.asyncio
async def test_delete_rates_endpoint_covers_delete_all_bulk_and_invalid(monkeypatch):
    """delete_rates_endpoint should handle delete_all, bulk date-range, invalid item."""
    print_section("delete_rates_endpoint")

    session = AsyncMock()
    count_result = _mock_scalar_result([object(), object()])
    delete_result = Mock(rowcount=2)
    session.execute = AsyncMock(side_effect=[count_result, delete_result])
    session.commit = AsyncMock()

    monkeypatch.setattr(
        fx_api,
        "delete_rates_bulk",
        AsyncMock(return_value=[(True, 1, 1, None), (True, 2, 2, None)]),
    )

    today = date.today()
    response = await fx_api.delete_rates_endpoint(
        [
            FXDeleteItem(**{"from": "USD", "to": "CAD"}, delete_all=True),
            FXDeleteItem(**{"from": "USD", "to": "NZD"}, date_range=DateRangeModel(start=today)),
            FXDeleteItem(**{"from": "CHF", "to": "USD"}, date_range=DateRangeModel(start=today, end=today)),
            FXDeleteItem(**{"from": "EUR", "to": "EUR"}, date_range=DateRangeModel(start=today, end=today)),
        ],
        session=session,
        _current_user=Mock(),
    )

    assert response.success_count == 3
    assert response.total_deleted == 5
    assert len(response.results) == 3
    assert response.errors and "different" in response.errors[0]

    delete_all_result = response.results[0]
    assert delete_all_result.base == "CAD"
    assert delete_all_result.quote == "USD"
    assert delete_all_result.existing_count == 2
    assert delete_all_result.deleted_count == 2

    bulk_result = response.results[1]
    assert bulk_result.base == "NZD"
    assert bulk_result.quote == "USD"
    assert bulk_result.deleted_count == 1
    assert bulk_result.date_range.end is None

    normal_bulk_result = response.results[2]
    assert normal_bulk_result.base == "CHF"
    assert normal_bulk_result.quote == "USD"
    assert normal_bulk_result.deleted_count == 2
    print_success("Delete-all + bulk + invalid branch covered")


@pytest.fixture(params=["direct", "inverse", "repeated-provider", "ordered-distinct-providers", "manual"])
def route_case(request):
    cases = {
        "direct": ("EUR", "USD", [{"from": "EUR", "to": "USD", "provider": "MOCKFX"}], False, ["MOCKFX"]),
        "inverse": ("EUR", "USD", [{"from": "USD", "to": "EUR", "provider": "MOCKFX"}], False, ["MOCKFX"]),
        "repeated-provider": (
            "RON",
            "USD",
            [
                {"from": "RON", "to": "EUR", "provider": "MOCKFX"},
                {"from": "EUR", "to": "USD", "provider": "MOCKFX"},
            ],
            True,
            ["MOCKFX"],
        ),
        "ordered-distinct-providers": (
            "CHF",
            "USD",
            [
                {"from": "CHF", "to": "EUR", "provider": "SNB"},
                {"from": "EUR", "to": "USD", "provider": "ECB"},
            ],
            True,
            ["ECB", "SNB"],
        ),
        "manual": ("EUR", "USD", [{"from": "EUR", "to": "USD", "provider": "MANUAL"}], False, ["MANUAL"]),
    }
    return cases[request.param]


@pytest.fixture
def route_providers(monkeypatch):
    """Registry membership only: even SNB/ECB cases must never fetch anything."""
    monkeypatch.setattr(
        fx_api.FXProviderRegistry,
        "list_providers",
        lambda: [{"code": code} for code in ("MOCKFX", "MOCKFX_FAIL", "SNB", "ECB", "MANUAL")],
    )
    lookup = Mock(side_effect=AssertionError("Route configuration must not instantiate a provider"))
    monkeypatch.setattr(fx_api.FXProviderRegistry, "get_provider_instance", lookup)
    return lookup


def _route_session(*, existing=None, listed_routes=()):
    """No DB attachment or persistence: only handler control-flow is mocked."""
    result = _mock_scalar_result(list(listed_routes))
    result.scalar_one_or_none.return_value = existing
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = result
    # AsyncSession.add is synchronous; an AsyncMock here leaves an unawaited call.
    session.add = Mock()
    return session


def _assert_route_metadata(item, *, is_chain, providers, steps):
    assert type(item["is_chain"]) is bool
    assert item["is_chain"] is is_chain
    assert type(item["providers_used"]) is list
    assert item["providers_used"] == providers
    assert item["chain_steps"] == steps


@pytest.mark.asyncio
async def test_list_routes_returns_deserialized_items(route_case, route_providers):
    """Real ORM properties determine membership; traversal is never deduplicated."""
    base, quote, steps, is_chain, providers = route_case
    route = FxConversionRoute(base=base, quote=quote, priority=1, chain_steps=json.dumps(steps))
    session = _route_session(listed_routes=[route])

    response = await fx_api.list_routes(session=session, _current_user=Mock())

    (item,) = response.items
    assert isinstance(item, FXConversionRouteReadItem)
    assert (item.base, item.quote, item.priority) == (base, quote, 1)
    (wire,) = json.loads(response.model_dump_json(by_alias=True))["items"]
    _assert_route_metadata(wire, is_chain=is_chain, providers=providers, steps=steps)
    assert route.parsed_steps == steps
    session.add.assert_not_called()
    session.commit.assert_not_awaited()
    route_providers.assert_not_called()


@pytest.mark.asyncio
async def test_list_routes_empty_and_fallback_alternatives():
    empty = await fx_api.list_routes(session=_route_session(), _current_user=Mock())
    assert json.loads(empty.model_dump_json())["items"] == []

    routes = [
        FxConversionRoute(
            base="EUR",
            quote="USD",
            priority=priority,
            chain_steps=json.dumps([{"from": "EUR", "to": "USD", "provider": provider}]),
        )
        for priority, provider in ((1, "MOCKFX_FAIL"), (2, "MOCKFX"))
    ]
    response = await fx_api.list_routes(session=_route_session(listed_routes=routes), _current_user=Mock())
    items = {item["priority"]: item for item in json.loads(response.model_dump_json(by_alias=True))["items"]}
    assert set(items) == {1, 2}
    for priority, provider in ((1, "MOCKFX_FAIL"), (2, "MOCKFX")):
        _assert_route_metadata(
            items[priority],
            is_chain=False,
            providers=[provider],
            steps=[{"from": "EUR", "to": "USD", "provider": provider}],
        )


@pytest.mark.asyncio
async def test_create_routes_derives_metadata_ignoring_spoofed_input(route_case, route_providers):
    base, quote, steps, is_chain, providers = route_case
    request = FXConversionRouteItem.model_validate(
        {
            "base": base,
            "quote": quote,
            "priority": 1,
            "chain_steps": steps,
            "is_chain": not is_chain,
            "providers_used": ["BOGUS"],
        }
    )
    assert {"is_chain", "providers_used"}.isdisjoint(request.model_dump())
    session = _route_session()

    response = await fx_api.create_routes_bulk([request], session=session, _current_user=Mock())

    assert response.success_count == 1
    assert response.error_count == 0
    (result,) = json.loads(response.model_dump_json(by_alias=True))["results"]
    assert (result["base"], result["quote"], result["priority"]) == (base, quote, 1)
    assert result["success"] is True
    assert result["action"] == "created"
    _assert_route_metadata(result, is_chain=is_chain, providers=providers, steps=steps)
    session.add.assert_called_once()
    (stored,) = session.add.call_args.args
    assert isinstance(stored, FxConversionRoute)
    assert stored.parsed_steps == steps
    assert stored.is_chain is is_chain
    assert stored.providers_used == set(providers)
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
    route_providers.assert_not_called()


@pytest.mark.asyncio
async def test_create_routes_same_priority_direct_chain_direct_updates_same_orm_object(route_providers):
    direct = [{"from": "RON", "to": "USD", "provider": "MOCKFX"}]
    chain = [
        {"from": "RON", "to": "EUR", "provider": "MOCKFX"},
        {"from": "EUR", "to": "USD", "provider": "MOCKFX"},
    ]
    existing = FxConversionRoute(id=701, base="RON", quote="USD", priority=3, chain_steps=json.dumps(direct))
    session = _route_session(existing=existing)
    snapshots = []

    for steps, is_chain in ((direct, False), (chain, True), (direct, False)):
        request = FXConversionRouteItem.model_validate(
            {
                "base": "RON",
                "quote": "USD",
                "priority": 3,
                "chain_steps": steps,
                "is_chain": not is_chain,
                "providers_used": ["BOGUS"],
            }
        )
        response = await fx_api.create_routes_bulk([request], session=session, _current_user=Mock())
        (result,) = json.loads(response.model_dump_json(by_alias=True))["results"]
        snapshots.append(result)
        assert response.success_count == 1
        assert response.error_count == 0
        assert result["success"] is True
        assert result["action"] == "updated"
        assert (result["base"], result["quote"], result["priority"]) == ("RON", "USD", 3)
        _assert_route_metadata(result, is_chain=is_chain, providers=["MOCKFX"], steps=steps)
        (added,) = session.add.call_args.args
        assert added is existing
        assert existing.id == 701
        assert existing.parsed_steps == steps
        assert existing.is_chain is is_chain
        assert existing.providers_used == {"MOCKFX"}

    assert [result["is_chain"] for result in snapshots] == [False, True, False]
    assert [result["chain_steps"] for result in snapshots] == [direct, chain, direct]
    assert session.add.call_count == 3
    assert session.commit.await_count == 3
    session.rollback.assert_not_awaited()
    route_providers.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("order", [("unknown",), ("valid", "unknown"), ("unknown", "valid")])
@pytest.mark.parametrize("update_existing", [False, True], ids=["create-valid", "update-valid"])
@pytest.mark.parametrize("unknown_chain", [False, True], ids=["unknown-direct", "unknown-chain"])
async def test_create_routes_atomic_error_preserves_every_result_metadata(order, update_existing, unknown_chain, route_providers):
    """Mock rollback proves invocation and retained detail, not DB persistence."""
    valid_steps = [
        {"from": "RON", "to": "EUR", "provider": "MOCKFX"},
        {"from": "EUR", "to": "USD", "provider": "MOCKFX"},
    ]
    unknown_steps = (
        [
            {"from": "CHF", "to": "EUR", "provider": "ZZ_UNKNOWN_FX"},
            {"from": "EUR", "to": "USD", "provider": "ECB"},
        ]
        if unknown_chain
        else [{"from": "CHF", "to": "USD", "provider": "ZZ_UNKNOWN_FX"}]
    )
    expected_providers = {"valid": ["MOCKFX"], "unknown": ["ECB", "ZZ_UNKNOWN_FX"] if unknown_chain else ["ZZ_UNKNOWN_FX"]}
    requests = {
        "valid": FXConversionRouteItem(base="RON", quote="USD", priority=2, chain_steps=valid_steps),
        "unknown": FXConversionRouteItem(base="CHF", quote="USD", priority=7, chain_steps=unknown_steps),
    }
    existing = (
        FxConversionRoute(
            base="RON",
            quote="USD",
            priority=2,
            chain_steps=json.dumps([{"from": "RON", "to": "USD", "provider": "MOCKFX"}]),
        )
        if update_existing
        else None
    )
    session = _route_session(existing=existing)

    with pytest.raises(HTTPException) as exc:
        await fx_api.create_routes_bulk([requests[name] for name in order], session=session, _current_user=Mock())

    assert exc.value.status_code == 400
    detail = exc.value.detail
    assert set(detail) == {"message", "results"}
    assert "Transaction rolled back" in detail["message"]
    assert len(detail["results"]) == len(order)
    assert [(item["base"], item["quote"], item["priority"]) for item in detail["results"]] == [(requests[name].base, requests[name].quote, requests[name].priority) for name in order]
    for name, result in zip(order, detail["results"], strict=True):
        # The 400 detail deliberately uses model_dump(), not by_alias JSON.
        _assert_route_metadata(
            result,
            is_chain=True if name == "valid" else unknown_chain,
            providers=expected_providers[name],
            steps=[{"from_currency": step["from"], "to_currency": step["to"], "provider": step["provider"]} for step in (valid_steps if name == "valid" else unknown_steps)],
        )
        assert result["success"] is (name == "valid")
        if name == "unknown":
            assert result["action"] == "error"
            assert "ZZ_UNKNOWN_FX" in result["message"]
        else:
            assert result["action"] == ("updated" if update_existing else "created")

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
    session.delete.assert_not_awaited()
    if "valid" in order:
        session.add.assert_called_once()
        session.execute.assert_awaited_once()
        (added,) = session.add.call_args.args
        assert isinstance(added, FxConversionRoute)
        assert (added.base, added.quote, added.priority) == ("RON", "USD", 2)
        assert added.parsed_steps == valid_steps
        if update_existing:
            assert added is existing
    else:
        session.add.assert_not_called()
        session.execute.assert_not_awaited()
    # No invalid candidate is ever handed to add(), even before the rollback.
    assert all("ZZ_UNKNOWN_FX" not in call.args[0].providers_used for call in session.add.call_args_list)
    route_providers.assert_not_called()
