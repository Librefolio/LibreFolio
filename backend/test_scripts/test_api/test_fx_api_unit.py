"""
Direct unit tests for FX API handlers.

Focus: happy-path/main-branch coverage in backend/app/api/v1/fx/
without live server/network dependency.

X-R38 (the FX side of W-B58): POST /fx/currencies/rate and a rate no column can keep, served in process
(``httpx.ASGITransport``) on the lane's test database: see its block at the end.
"""

import json
import re
import sys
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from backend.app.api.v1.auth import get_current_user
from backend.app.api.v1.fx import currencies as fx_currencies_api
from backend.app.api.v1.fx import providers as fx_providers_api
from backend.app.db.models import FxConversionRoute, FxRate
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.fx import FXConversionRouteItem, FXConversionRouteReadItem, FXDeleteItem, FXUpsertItem
from backend.app.schemas.refresh import FXSyncBulkResponse, FXSyncPairRequest, FXSyncPairResult, SyncDateRangeModel, SyncStatus
from backend.app.services.fx import catalog as fx_catalog
from backend.test_scripts.test_utils import print_section, print_success


def _mock_scalar_result(items):
    result = Mock()
    result.scalars.return_value.all.return_value = items
    return result


def _forget_catalog_currencies(code: str) -> None:
    fx_catalog._currencies_cache.delete(code)
    fx_catalog._last_known.pop(code, None)


@pytest.fixture
def fed_currencies_not_cached():
    """X-R8: list_providers reads target currencies through the process-wide catalog cache (services/fx/catalog.py).

    The FED entry and its last known list are dropped before the test, so an earlier call in this process cannot answer
    instead of the dummy provider, and after it, so the dummy list does not stay cached for 24 h in this pytest process.
    """
    _forget_catalog_currencies("FED")
    yield
    _forget_catalog_currencies("FED")


def test_build_providers_description_lists_codes(monkeypatch):
    """Description helper should embed discovered provider codes."""
    print_section("_build_providers_description")

    monkeypatch.setattr(
        fx_providers_api.FXProviderRegistry,
        "list_providers",
        lambda: [
            {"code": "ECB", "name": "European Central Bank"},
            {"code": "FED", "name": "Federal Reserve"},
        ],
    )

    description = fx_providers_api._build_providers_description()

    assert "Installed providers: ECB, FED" in description
    assert "Get the list of available FX rate providers." in description
    print_success("Provider description lists installed codes")


@pytest.mark.asyncio
@pytest.mark.usefixtures("fed_currencies_not_cached")
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
        fx_providers_api.FXProviderRegistry,
        "list_providers",
        lambda: [
            {"code": "MANUAL", "name": "Manual"},
            {"code": "MOCKFX", "name": "Mock"},
            {"code": "FED", "name": "Federal Reserve"},
        ],
    )
    monkeypatch.setattr(
        fx_providers_api.FXProviderRegistry,
        "get_provider_instance",
        lambda _code: _DummyProvider(),
    )

    providers = await fx_providers_api.list_providers(providers=["manual", "fed"])

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
    monkeypatch.setattr(fx_currencies_api, "sync_pairs_bulk", sync_mock)

    good_body = FXSyncPairRequest(
        pairs=["USD-EUR"],
        start=date(2025, 1, 1),
        end=date(2025, 1, 1),
    )
    result = await fx_currencies_api.sync_rates(good_body, session=session, _current_user=Mock())
    assert result == expected
    sync_mock.assert_awaited_once()
    assert sync_mock.await_args.kwargs["pairs"] == ["EUR-USD"]

    future_body = FXSyncPairRequest(
        pairs=["EUR-USD"],
        start=date.today(),
        end=date.today() + timedelta(days=1),
    )
    with pytest.raises(HTTPException, match="future"):
        await fx_currencies_api.sync_rates(future_body, session=session, _current_user=Mock())

    reversed_range_body = Mock(
        start=date(2025, 1, 3),
        end=date(2025, 1, 1),
        pairs=["EUR-USD"],
    )
    with pytest.raises(HTTPException, match="before or equal"):
        await fx_currencies_api.sync_rates(reversed_range_body, session=session, _current_user=Mock())

    print_success("Success path + future-date validation covered")


@pytest.mark.asyncio
async def test_upsert_rates_endpoint_keeps_valid_item_and_normalizes(monkeypatch):
    """Mixed batch should keep valid item, invert reversed pair, collect validation error."""
    print_section("upsert_rates_endpoint")

    session = AsyncMock()
    monkeypatch.setattr(
        fx_currencies_api,
        "upsert_rates_bulk",
        AsyncMock(side_effect=[[(True, "inserted")], [(True, "updated")]]),
    )

    today = date.today()
    response = await fx_currencies_api.upsert_rates_endpoint(
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
        fx_currencies_api,
        "delete_rates_bulk",
        AsyncMock(return_value=[(True, 1, 1, None), (True, 2, 2, None)]),
    )

    today = date.today()
    response = await fx_currencies_api.delete_rates_endpoint(
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
        fx_providers_api.FXProviderRegistry,
        "list_providers",
        lambda: [{"code": code} for code in ("MOCKFX", "MOCKFX_FAIL", "SNB", "ECB", "MANUAL")],
    )
    lookup = Mock(side_effect=AssertionError("Route configuration must not instantiate a provider"))
    monkeypatch.setattr(fx_providers_api.FXProviderRegistry, "get_provider_instance", lookup)
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

    response = await fx_providers_api.list_routes(session=session, _current_user=Mock())

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
    empty = await fx_providers_api.list_routes(session=_route_session(), _current_user=Mock())
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
    response = await fx_providers_api.list_routes(session=_route_session(listed_routes=routes), _current_user=Mock())
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

    response = await fx_providers_api.create_routes_bulk([request], session=session, _current_user=Mock())

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
        response = await fx_providers_api.create_routes_bulk([request], session=session, _current_user=Mock())
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
        await fx_providers_api.create_routes_bulk([requests[name] for name in order], session=session, _current_user=Mock())

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


# ============================================================================
# X-R38 (the FX side of W-B58): POST /fx/currencies/rate and a rate no column can keep
# ============================================================================
#
# Measured before the cure, in process on the lane's test database. The rate "1E+400" (a JSON string) is stored as a
# REAL inf, and typed MMK → KHR its inverse as 0; a JSON number 1E+15 is stored as it is, "1E-11" as 0: 200 each time. A
# JSON number 1E+400 reaches the schema as inf, which it refuses (not a finite number), and FastAPI's 422 carries it back
# as its input, which Starlette's JSON renderer refuses: the request ends in 500; so do a NaN literal and the string
# "Infinity". "1E-1000000" typed MMK → KHR makes the endpoint's own inversion raise decimal.Overflow, outside its
# per-item try: 500. A rate that is not a number at all ("abc", "0x10", the JSON boolean true) makes the schema's
# coerce_rate raise decimal.InvalidOperation, which is not a ValueError: Pydantic does not turn it into a validation
# error, it escapes the request: 500.
#
# Contract (X-R38): a 4xx, never a 500. A rate storable_fx_rate refuses once normalized (the endpoint inverts MMK → KHR
# itself) gets its item's error; all items refused → 400 naming the limits (14 digits before the decimal point, 10
# decimal places); nothing refused is stored, every other item of the request is. A rate that is not a number is the
# schema's to refuse: 422, its detail located on the item's rate.
#
# Isolation: the unit's default, write-scoped. KHR/MMK is this block's own (no seed and no other test uses the pair): its
# rates in the window are wiped before and after each test, and nothing else is read.

XR38_DAYS = (date(1986, 3, 3), date(1986, 3, 4), date(1986, 3, 5))
_XR38_RATE_URL = "/api/v1/fx/currencies/rate"


async def _xr38_wipe() -> None:
    """Drop the KHR/MMK rates of the window."""
    async with AsyncSession(get_async_engine()) as session:
        await session.execute(delete(FxRate).where(FxRate.base == "KHR", FxRate.quote == "MMK", FxRate.date >= XR38_DAYS[0], FxRate.date <= XR38_DAYS[-1]))
        await session.commit()


@pytest_asyncio.fixture
async def xr38_khr_mmk():
    """X-R38: no KHR/MMK rate in the window before and after the test."""
    await _xr38_wipe()
    yield
    await _xr38_wipe()


async def _xr38_stored() -> dict[date, Decimal]:
    """The KHR/MMK rates of the window by date, read through the model, as the app reads them."""
    async with AsyncSession(get_async_engine()) as session:
        rows = (await session.execute(select(FxRate.date, FxRate.rate).where(FxRate.base == "KHR", FxRate.quote == "MMK", FxRate.date >= XR38_DAYS[0], FxRate.date <= XR38_DAYS[-1]))).all()
    return {row.date: row.rate for row in rows}


def _xr38_numbers(message: str) -> set[str]:
    """The whole numbers ``message`` states, its ISO dates taken out first: a date cannot stand in for a limit."""
    return set(re.findall(r"\d+", re.sub(r"\d{4}-\d{2}-\d{2}", " ", message)))


def _xr38_item(day: date, base: str, quote: str, rate: str) -> str:
    """One item of the request body, its rate written as given: ``1E+400`` is a JSON number, ``"1E+400"`` a JSON string."""
    return f'{{"date": "{day.isoformat()}", "base": "{base}", "quote": "{quote}", "rate": {rate}, "source": "MANUAL"}}'


async def _xr38_signed_in_user():
    """The user ``get_current_user`` would give: the rate routes only require one."""
    return Mock(id=0)


async def _xr38_post(items: list[str], story: str) -> httpx.Response:
    """``POST /api/v1/fx/currencies/rate`` with ``items``, served in process by the FX rate routes on the lane's test
    database, a signed-in user stubbed. An exception escaping the app fails the test naming it: the server answers 500."""
    app = FastAPI()
    app.include_router(fx_currencies_api.router_currencies, prefix="/api/v1/fx")
    app.dependency_overrides[get_current_user] = _xr38_signed_in_user
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        try:
            return await client.post(_XR38_RATE_URL, content=f"[{', '.join(items)}]".encode(), headers={"content-type": "application/json"})
        except Exception as exc:  # noqa: BLE001 — what escapes the app is what the server answers 500 to
            pytest.fail(f"{story}: POST /fx/currencies/rate raised {exc!r}, the server answers 500 (X-R38: a 4xx, never a 500)")


@pytest.mark.asyncio
@pytest.mark.usefixtures("xr38_khr_mmk")
@pytest.mark.parametrize(
    ("base", "quote", "rate", "normalized"),
    [
        pytest.param("KHR", "MMK", '"1E+400"', "1E+400", id="string-1E+400"),
        pytest.param("MMK", "KHR", '"1E+400"', "1E-400", id="inverted-string-1E+400"),
        pytest.param("KHR", "MMK", "1E+15", "1E+15", id="number-1E+15"),
        pytest.param("KHR", "MMK", '"1E-11"', "1E-11", id="string-1E-11"),
        pytest.param("MMK", "KHR", '"1E-15"', "1E+15", id="inverted-string-1E-15"),
        pytest.param("MMK", "KHR", '"1E+11"', "1E-11", id="inverted-string-1E+11"),
        pytest.param("MMK", "KHR", '"1E-1000000"', "1E+1000000", id="derived-inverted-string-1E-1000000-the-inversion-overflows"),
    ],
)
async def test_xr38_upsert_rates_endpoint_answers_400_to_a_rate_no_column_can_keep(base, quote, rate, normalized):
    """Red today: 200 and the rate stored, 1E+400 as a REAL inf, its inverse, 1E-11 and the inverse of 1E+11 as 0, 1E+15
    and the inverse of 1E-15 as they are; the inverse of 1E-1000000 raises ``decimal.Overflow`` outside the item's try:
    500.

    Contract (X-R38): its only item refused, so 400, the detail naming the limits (14 digits before the decimal point, 10
    decimal places); nothing stored. The ``derived-`` case reads "never a 500".
    """
    story = f"POST /fx/currencies/rate of {base} → {quote} {rate} on {XR38_DAYS[0]} (KHR/MMK {normalized} once normalized)"

    response = await _xr38_post([_xr38_item(XR38_DAYS[0], base, quote, rate)], story)

    assert response.status_code == 400, f"{story} answered {response.status_code} {response.text[:300]}: expected 400, its only item refused (X-R38)"
    detail = response.json().get("detail")
    assert {"14", "10"} <= _xr38_numbers(str(detail)), f"{story}: the 400 does not name the limits, 14 digits before the decimal point and 10 decimal places: {detail!r}"
    stored = await _xr38_stored()
    assert not stored, f"{story} was refused, yet rows were written: {stored}"


@pytest.mark.asyncio
@pytest.mark.usefixtures("xr38_khr_mmk")
@pytest.mark.parametrize(
    ("base", "quote", "rate"),
    [
        pytest.param("KHR", "MMK", "1E+400", id="number-1E+400"),
        pytest.param("MMK", "KHR", "1E+400", id="inverted-number-1E+400"),
        pytest.param("KHR", "MMK", "NaN", id="derived-literal-NaN"),
        pytest.param("KHR", "MMK", '"Infinity"', id="derived-string-Infinity"),
    ],
)
async def test_xr38_upsert_rates_endpoint_answers_4xx_to_a_rate_that_is_not_a_finite_number(base, quote, rate):
    """Red today: the JSON number 1E+400 is parsed as inf (a NaN literal as nan; "Infinity" becomes Decimal('Infinity')),
    the schema refuses it, not a finite number, and FastAPI's 422 carries it back as its input, which Starlette's JSON
    renderer refuses (``allow_nan=False``): 500.

    Contract (X-R38): a 4xx, the endpoint's 400 or the schema's 422, never a 500; nothing stored. The ``derived-`` cases
    read the same rule.
    """
    story = f"POST /fx/currencies/rate of {base} → {quote} with the rate {rate} on {XR38_DAYS[0]}"

    response = await _xr38_post([_xr38_item(XR38_DAYS[0], base, quote, rate)], story)

    assert 400 <= response.status_code < 500, f"{story} answered {response.status_code} {response.text[:300]}: expected a 4xx (X-R38: never a 500)"
    stored = await _xr38_stored()
    assert not stored, f"{story} was refused, yet rows were written: {stored}"


@pytest.mark.asyncio
@pytest.mark.usefixtures("xr38_khr_mmk")
@pytest.mark.parametrize(
    "rate",
    [
        pytest.param('"abc"', id="string-abc"),
        pytest.param("true", id="derived-boolean-true"),
        pytest.param('"0x10"', id="derived-string-0x10"),
    ],
)
async def test_xr38_upsert_rates_endpoint_answers_422_to_a_rate_that_is_not_a_number(rate):
    """Red today: the schema's ``coerce_rate`` calls ``Decimal()`` itself, on "abc" and "0x10" as they are and on the JSON
    boolean true as "True" (a bool is an int), and ``Decimal()`` raises ``decimal.InvalidOperation``, which is not a
    ``ValueError``: Pydantic does not turn it into a validation error, it escapes the request and the server answers 500.

    Contract (X-R38): the schema refuses the item, 422, never a 500; the body is JSON and its detail locates the refusal
    on the item's rate; nothing stored. The ``derived-`` cases read the same rule.
    """
    story = f"POST /fx/currencies/rate of KHR → MMK with the rate {rate} on {XR38_DAYS[0]}"

    response = await _xr38_post([_xr38_item(XR38_DAYS[0], "KHR", "MMK", rate)], story)

    assert response.status_code == 422, f"{story} answered {response.status_code} {response.text[:300]}: expected 422, the schema refusing a rate that is not a number (X-R38: never a 500)"
    detail = response.json().get("detail")
    assert isinstance(detail, list) and any(isinstance(error, dict) and (error.get("loc") or [])[-1:] == ["rate"] for error in detail), f"{story}: the 422 does not tell the user the item's rate is what was refused: {detail!r}"
    stored = await _xr38_stored()
    assert not stored, f"{story} was refused, yet rows were written: {stored}"


@pytest.mark.asyncio
@pytest.mark.usefixtures("xr38_khr_mmk")
async def test_xr38_upsert_rates_endpoint_keeps_the_valid_rate_and_reports_the_refused_one():
    """Red today: 200 and both rates stored, "1E+400" as a REAL inf; no error reported.

    Contract (X-R38): 200; the valid rate of 1.5 is stored and listed in the results; the rate no column can keep is not
    stored and has its item's error, "Rate 1: …", naming the limits (14 digits before the decimal point, 10 decimal
    places).
    """
    story = f'POST /fx/currencies/rate of KHR → MMK 1.5 on {XR38_DAYS[0]} and KHR → MMK "1E+400" on {XR38_DAYS[1]}'

    response = await _xr38_post([_xr38_item(XR38_DAYS[0], "KHR", "MMK", '"1.5"'), _xr38_item(XR38_DAYS[1], "KHR", "MMK", '"1E+400"')], story)

    assert response.status_code == 200, f"{story} answered {response.status_code} {response.text[:300]}: expected 200, one item stored"
    stored = await _xr38_stored()
    assert stored == {XR38_DAYS[0]: Decimal("1.5")}, f"{story} stored {stored}: expected the valid rate alone (X-R38)"
    body = response.json()
    listed = [(item["base"], item["quote"], item["date"]) for item in body["results"]]
    assert listed == [("KHR", "MMK", XR38_DAYS[0].isoformat())], f"{story} lists the results {listed}: expected the valid rate alone"
    errors = body["errors"]
    assert len(errors) == 1 and errors[0].startswith("Rate 1") and {"14", "10"} <= _xr38_numbers(errors[0]), f"{story} reports the errors {errors}: expected one, 'Rate 1: …', naming the limits 14 and 10 (X-R38)"


@pytest.mark.asyncio
@pytest.mark.usefixtures("xr38_khr_mmk")
async def test_xr38_guard_upsert_rates_endpoint_stores_a_rate_typed_as_a_json_number():
    """Guard: green today and after. A rate typed as a JSON number, the float 1.5 or the integer 2 (which the X-R38 cure
    of ``coerce_rate`` hands to Pydantic as it is), is read as the number it is: 200, no error, both stored as typed."""
    story = f"POST /fx/currencies/rate of KHR → MMK 1.5 on {XR38_DAYS[0]} and KHR → MMK 2 on {XR38_DAYS[1]}, both JSON numbers"

    response = await _xr38_post([_xr38_item(XR38_DAYS[0], "KHR", "MMK", "1.5"), _xr38_item(XR38_DAYS[1], "KHR", "MMK", "2")], story)

    assert response.status_code == 200 and response.json()["errors"] == [], f"{story} answered {response.status_code} {response.text[:300]}: expected 200, both rates stored and no error"
    stored = await _xr38_stored()
    assert stored == {XR38_DAYS[0]: Decimal("1.5"), XR38_DAYS[1]: Decimal("2")}, f"{story} stored {stored}: expected 1.5 and 2, as typed"


@pytest.mark.asyncio
@pytest.mark.usefixtures("xr38_khr_mmk")
async def test_xr38_guard_upsert_rates_endpoint_stores_rates_at_the_limits():
    """Guard: green today and after. 14 digits before the decimal point and 1E-10 are the limits, not past them, typed
    (KHR → MMK 99999999999999) or reached by the endpoint's inverse (MMK → KHR 1E+10 is KHR/MMK 1E-10); and the limit is
    checked on the rate stored, never on the rate typed (MMK → KHR 1E-13, which the column could not keep as it is, is
    KHR/MMK 1E+13): 200, all three stored."""
    story = f"POST /fx/currencies/rate of KHR → MMK 99999999999999 on {XR38_DAYS[0]}, MMK → KHR 1E+10 on {XR38_DAYS[1]} and MMK → KHR 1E-13 on {XR38_DAYS[2]}"
    items = [
        _xr38_item(XR38_DAYS[0], "KHR", "MMK", '"99999999999999"'),
        _xr38_item(XR38_DAYS[1], "MMK", "KHR", '"1E+10"'),
        _xr38_item(XR38_DAYS[2], "MMK", "KHR", '"1E-13"'),
    ]

    response = await _xr38_post(items, story)

    assert response.status_code == 200 and response.json()["errors"] == [], f"{story} answered {response.status_code} {response.text[:300]}"
    stored = await _xr38_stored()
    assert stored == {XR38_DAYS[0]: Decimal("99999999999999"), XR38_DAYS[1]: Decimal("1E-10"), XR38_DAYS[2]: Decimal("1E+13")}, f"{story} stored {stored}"
