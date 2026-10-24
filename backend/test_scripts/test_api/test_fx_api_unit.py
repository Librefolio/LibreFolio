"""
Direct unit tests for FX API handlers.

Focus: happy-path/main-branch coverage in backend/app/api/v1/fx/
without live server/network dependency.

X-R38 (the FX side of W-B58): POST /fx/currencies/rate and a rate no column can keep, served in process
(``httpx.ASGITransport``) on the lane's test database: see its block at the end. X-R50 (E's review R13-SEC5 on X-R38): a
rate whose double is 1E+14 and an inverse that underflows to 0, in the same block. X-R46: the same endpoint names the rates
it refused, machine-readable (``rejected``; a 400 whose detail is an object): its block follows X-R38's. X-R41: POST
/fx/currencies/convert of an amount of 0, a 500 today, converted as one unit of its currency: its block follows X-R46's,
the handler called with ``convert_bulk`` patched, and one case on the wire.
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
from pydantic import ValidationError
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
from backend.app.db.precision import storable_fx_rate
from backend.app.db.session import get_async_engine
from backend.app.schemas import fx as fx_schemas
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.fx import FXConversionRequest, FXConversionRouteItem, FXConversionRouteReadItem, FXConvertResponse, FXDeleteItem, FXUpsertItem
from backend.app.schemas.refresh import FXSyncBulkResponse, FXSyncPairRequest, FXSyncPairResult, SyncDateRangeModel, SyncStatus
from backend.app.services.fx import catalog as fx_catalog
from backend.app.services.fx import storage as fx_storage
from backend.app.services.fx.storage import fx_rate_refusal, normalize_storable_rate
from backend.test_scripts.fx_steps_double import steps_double
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
# X-R50 (E's review R13-SEC5 on X-R38), measured before its cure. "99999999999999.995" (a JSON string: the JSON number
# arrives as the float 1E+14, which X-R38 refuses) has the 14 digits before the decimal point X-R38 lets through: 200, and
# stored as its double, 1E+14, which every conversion skips (convert_bulk reads only 1E-10 <= rate < 1E+14). "1E+1000030"
# typed MMK → KHR makes the endpoint's inversion underflow to 0 without an exception, and upsert_rates_bulk refuses that 0
# as «Rate must be positive (got 0E-1000026)»: a 400 that never names the limits. Contract (X-R50): both get the X-R38
# answer, 400 naming the limits, nothing stored.
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
async def test_xr50_upsert_rates_endpoint_answers_400_to_a_rate_whose_double_is_1E14():
    """Red today: KHR → MMK "99999999999999.995" has the 14 digits before the decimal point X-R38 lets through: 200,
    «inserted», and the rate stored as its double, ``1E+14``, which every conversion then skips (``convert_bulk`` reads
    only ``1E-10 <= rate < 1E+14``): the user is told the rate is saved, and no conversion will ever use it.

    Contract (X-R50): its only item refused, so 400, the detail naming the limits (14 digits before the decimal point, 10
    decimal places); nothing stored.
    """
    rate = "99999999999999.995"
    integer_digits, double = Decimal(rate).adjusted() + 1, float(Decimal(rate))
    assert integer_digits == 14 and double >= 1e14, f"barrier: {rate} has {integer_digits} digits before the decimal point and the double {double!r}: expected the 14 X-R38 lets through and a double of 1E+14"
    story = f'POST /fx/currencies/rate of KHR → MMK "{rate}" on {XR38_DAYS[0]} (its double {double!r})'

    response = await _xr38_post([_xr38_item(XR38_DAYS[0], "KHR", "MMK", f'"{rate}"')], story)

    stored = await _xr38_stored()
    assert response.status_code == 400, f"{story} answered {response.status_code} {response.text[:300]}, and stored {stored}: expected 400, its only item refused (X-R50)"
    detail = response.json().get("detail")
    assert {"14", "10"} <= _xr38_numbers(str(detail)), f"{story}: the 400 does not name the limits, 14 digits before the decimal point and 10 decimal places: {detail!r}"
    assert not stored, f"{story} was refused, yet rows were written: {stored}"


@pytest.mark.asyncio
@pytest.mark.usefixtures("xr38_khr_mmk")
async def test_xr50_upsert_rates_endpoint_names_the_limits_when_the_inverse_underflows_to_0():
    """Red today: MMK → KHR "1E+1000030" is stored KHR/MMK, inverted by the endpoint, and the inverse underflows to 0
    without an exception (``normalize_storable_rate`` answers ``0E-1000026``); ``upsert_rates_bulk`` refuses that 0 as
    «Rate must be positive (got 0E-1000026)»: a 400 telling the user that a rate far above 0 is not positive, never naming
    the limits.

    Contract (X-R50): 400, its only item refused, the detail naming the limits (14 digits before the decimal point, 10
    decimal places); nothing stored.
    """
    story = f'POST /fx/currencies/rate of MMK → KHR "1E+1000030" on {XR38_DAYS[0]} (KHR/MMK 1E-1000030 once normalized)'

    response = await _xr38_post([_xr38_item(XR38_DAYS[0], "MMK", "KHR", '"1E+1000030"')], story)

    stored = await _xr38_stored()
    assert response.status_code == 400, f"{story} answered {response.status_code} {response.text[:300]}, and stored {stored}: expected 400, its only item refused (X-R50)"
    detail = response.json().get("detail")
    assert {"14", "10"} <= _xr38_numbers(str(detail)), f"{story}: the 400 does not name the limits, 14 digits before the decimal point and 10 decimal places: {detail!r}"
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


# ============================================================================
# X-R46: POST /fx/currencies/rate names the rates it refused, machine-readable
# ============================================================================
#
# The defect, on HEAD 1c1456713: the endpoint tells a refused rate only as an English string of ``errors`` («Rate
# {idx}: …») and, when it refuses every rate, as the string ``detail`` of its 400 («All rates failed: …»). The FX data
# editor cannot tell which rows the server refused: it counts every row it sent as saved.
#
# Contract (X-R46): ``schemas.fx.FXRateRejection`` {``index``: the item's position in the request, ``date``: the item's
# date, ``reason``: ``same_currency`` | ``rate_not_storable`` | ``invalid_rate`` | ``internal_error``};
# ``FXBulkUpsertResponse.rejected``, ``[]`` by default, one entry per refused item, in request order: base == quote →
# ``same_currency``; a rate no column can keep → ``rate_not_storable``; any other ``ValueError`` → ``invalid_rate``; any
# other exception → ``internal_error``. A rate no column can keep is ``services.fx.storage.FXRateNotStorableError``, a
# ``ValueError`` with its text unchanged (decided 17/10): the endpoint raises it where its own ``normalize_storable_rate``
# answers None, ``upsert_rates_bulk`` at its X-R38 check (``storable_fx_rate``: more than 14 digits before the decimal
# point, 0 at 10 decimal places); the endpoint reads the class, never the text. The strings of ``errors`` stay as they
# are. Every item refused: still 400, its ``detail`` the object ``{"code": "fx_rates_refused", "message": the same «All
# rates failed: …» text, "rejected": the rejections, as JSON}``.
#
# The handler is called directly, ``upsert_rates_bulk`` patched where it reads it (``_xr46_store``): nothing reaches a
# database. The rate ``normalize_storable_rate`` refuses is a real one, not a patch: USD → EUR (or MMK → KHR)
# 1E-1000000, whose inverse, the rate the endpoint would store, overflows; each case checks it first, as a barrier. The
# store's own refusal is the patched store raising ``FXRateNotStorableError``. Three cases read the answer on the wire
# instead (``_xr38_post``), on X-R38's KHR/MMK window and its fixture, one of them the real store refusing KHR → MMK
# 1E-11. ``FXRateRejection`` and ``FXRateNotStorableError`` are read inside the cases (from ``schemas.fx`` and
# ``services.fx.storage``): before X-R46 they do not exist, and the cases fail on what the endpoint answered, or on the
# missing class, instead of breaking the module's import.

XR46_DAY = date(2024, 3, 4)
XR46_FX_REASONS = ("same_currency", "rate_not_storable", "invalid_rate", "internal_error")
XR46_UNSTORABLE = "1E-1000000"  # typed USD → EUR or MMK → KHR: the inverse the endpoint stores, 1E+1000000, overflows
XR46_STORE_REFUSAL = "X-R46: the store refuses this rate"
XR46_SECRET = "X-R46 internal detail: fx_rates_shadow is locked"


def _xr46_item(offset: int, base: str, quote: str, rate: str) -> FXUpsertItem:
    """One rate of the request: ``base`` → ``quote`` at ``rate``, on ``XR46_DAY`` plus ``offset`` days."""
    return FXUpsertItem(**{"date": XR46_DAY + timedelta(days=offset)}, base=base, quote=quote, rate=Decimal(rate), source="MANUAL")


def _xr46_store(monkeypatch: pytest.MonkeyPatch, refusals: dict[date, Exception] | None = None) -> AsyncMock:
    """``upsert_rates_bulk`` where the endpoint reads it, on no database: every rate handed to it is «inserted», but a
    rate dated as a key of ``refusals`` raises that exception. The mock keeps what reached it (``_xr46_handed``)."""
    refusals = refusals or {}

    async def _upsert(_session, rates):
        for rate_date, *_rest in rates:
            if rate_date in refusals:
                raise refusals[rate_date]
        return [(True, "inserted") for _rate in rates]

    store = AsyncMock(side_effect=_upsert)
    monkeypatch.setattr(fx_currencies_api, "upsert_rates_bulk", store)
    return store


def _xr46_handed(store: AsyncMock) -> list[date]:
    """The dates of the rates handed to the store, in order, a rate it refused included."""
    return [rate[0] for call in store.await_args_list for rate in call.args[1]]


async def _xr46_upsert(items: list[FXUpsertItem]):
    """``POST /fx/currencies/rate`` of ``items``: the handler called directly, its session and its user stubbed."""
    return await fx_currencies_api.upsert_rates_endpoint(items, session=AsyncMock(), _current_user=Mock())


def _xr46_kept(response) -> list[tuple[str, str, date]]:
    """The pair and the date of each result of the answer, in order."""
    return [(result.base, result.quote, result.date) for result in response.results]


def _xr46_rejected(response) -> list:
    """The ``rejected`` of a 200 as the wire carries it (by alias, the dates ISO); an answer without it fails the test,
    naming what it holds instead."""
    wire = response.model_dump(mode="json", by_alias=True)
    if "rejected" not in wire:
        pytest.fail(f"X-R46: the answer has no 'rejected', its refusals are only the English strings of 'errors': {wire}")
    return wire["rejected"]


def _xr46_unstorable_barrier(base: str, quote: str) -> None:
    """Barrier: ``normalize_storable_rate`` refuses ``base`` → ``quote`` at ``XR46_UNSTORABLE`` (its inverse overflows)."""
    assert normalize_storable_rate(base, quote, Decimal(XR46_UNSTORABLE)) is None, f"barrier: normalize_storable_rate keeps {base} → {quote} {XR46_UNSTORABLE}; the case needs a rate it refuses"


def _xr46_not_storable(message: str) -> ValueError:
    """``FXRateNotStorableError(message)``, the class read from ``services.fx.storage`` when the case runs: before X-R46
    it does not exist, and the case fails naming it instead of breaking the module's import."""
    error_class = getattr(fx_storage, "FXRateNotStorableError", None)
    if error_class is None:
        pytest.fail("X-R46: backend.app.services.fx.storage has no FXRateNotStorableError")
    assert issubclass(error_class, ValueError), f"X-R46: FXRateNotStorableError must be a ValueError, the endpoint's 'except ValueError' catching it: {error_class.__mro__}"
    return error_class(message)


@pytest.mark.asyncio
async def test_xr46_upsert_rates_endpoint_lists_a_rate_no_column_can_keep_in_rejected(monkeypatch):
    """X-R46: EUR → GBP 0.85, then USD → EUR 1E-1000000, which ``normalize_storable_rate`` refuses.

    Red on HEAD 1c1456713: ``FXBulkUpsertResponse`` has no ``rejected``; the refused rate is told only in ``errors``
    («Rate 1: Validation error: The rate of EUR/USD on … cannot be stored: …»), so the FX editor counts it as saved.
    Contract: 200; the first rate alone in ``results`` and handed to the store; ``rejected`` ``[{"index": 1, "date": its
    date, "reason": "rate_not_storable"}]`` -- the index is the item's position in the request, not among the refusals;
    ``errors`` the same one string as before.
    """
    _xr46_unstorable_barrier("USD", "EUR")
    store = _xr46_store(monkeypatch)
    kept, refused = _xr46_item(0, "EUR", "GBP", "0.85"), _xr46_item(1, "USD", "EUR", XR46_UNSTORABLE)

    response = await _xr46_upsert([kept, refused])

    assert _xr46_kept(response) == [("EUR", "GBP", kept.rate_date)], response.results
    assert response.errors == [f"Rate 1: Validation error: {fx_rate_refusal('USD', 'EUR', refused.rate_date)}"], response.errors
    assert _xr46_handed(store) == [kept.rate_date], "barrier: the refused rate reached the store"
    assert _xr46_rejected(response) == [{"index": 1, "date": refused.rate_date.isoformat(), "reason": "rate_not_storable"}]


@pytest.mark.asyncio
async def test_xr46_upsert_rates_endpoint_lists_a_same_currency_pair_in_rejected(monkeypatch):
    """X-R46: EUR → GBP 0.85, then EUR → EUR 1.

    Red on HEAD 1c1456713: no ``rejected``; the refusal is only «Rate 1: Base and quote must be different (got EUR)».
    Contract: 200; the first rate alone in ``results`` and handed to the store; ``rejected`` ``[{"index": 1, "date": its
    date, "reason": "same_currency"}]``; ``errors`` the same one string as before.
    """
    store = _xr46_store(monkeypatch)
    kept, refused = _xr46_item(0, "EUR", "GBP", "0.85"), _xr46_item(1, "EUR", "EUR", "1")

    response = await _xr46_upsert([kept, refused])

    assert _xr46_kept(response) == [("EUR", "GBP", kept.rate_date)], response.results
    assert response.errors == ["Rate 1: Base and quote must be different (got EUR)"], response.errors
    assert _xr46_handed(store) == [kept.rate_date], "barrier: the refused rate reached the store"
    assert _xr46_rejected(response) == [{"index": 1, "date": refused.rate_date.isoformat(), "reason": "same_currency"}]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("refusal", "reason", "error"),
    [
        pytest.param(lambda: ValueError(XR46_STORE_REFUSAL), "invalid_rate", f"Rate 1: Validation error: {XR46_STORE_REFUSAL}", id="ValueError-invalid_rate"),
        pytest.param(lambda: _xr46_not_storable(XR46_STORE_REFUSAL), "rate_not_storable", f"Rate 1: Validation error: {XR46_STORE_REFUSAL}", id="FXRateNotStorableError-rate_not_storable"),
        pytest.param(lambda: RuntimeError(XR46_SECRET), "internal_error", "Rate 1: Failed: internal error", id="RuntimeError-internal_error"),
    ],
)
async def test_xr46_upsert_rates_endpoint_lists_a_rate_the_store_refuses_in_rejected(monkeypatch, refusal, reason, error):
    """X-R46: EUR → GBP 0.85, then EUR → JPY 160, on which ``upsert_rates_bulk`` raises what ``refusal`` builds, when the
    case runs.

    Red on HEAD 1c1456713: no ``rejected``; the refusal is only the string of ``errors``. The ``FXRateNotStorableError``
    case fails before the call: ``services.fx.storage`` has no such class.
    Contract: 200; the first rate alone in ``results``, both handed to the store; ``rejected`` ``[{"index": 1, "date": its
    date, "reason": reason}]``: ``FXRateNotStorableError`` (a ``ValueError``, the store's X-R38 refusal, decided 17/10)
    is ``rate_not_storable``, any other ``ValueError`` ``invalid_rate``, any other exception ``internal_error``. The
    first two carry the same text: the class decides the reason, never the text. ``errors`` the same one string as
    before, and the exception's own text of an internal error nowhere in the answer (MF-SEC9a).
    """
    kept, refused = _xr46_item(0, "EUR", "GBP", "0.85"), _xr46_item(1, "EUR", "JPY", "160")
    store = _xr46_store(monkeypatch, {refused.rate_date: refusal()})

    response = await _xr46_upsert([kept, refused])

    assert _xr46_kept(response) == [("EUR", "GBP", kept.rate_date)], response.results
    assert response.errors == [error], response.errors
    assert _xr46_handed(store) == [kept.rate_date, refused.rate_date], "barrier: both rates should reach the store, the second refused there"
    assert XR46_SECRET not in response.model_dump_json(), "MF-SEC9a: the answer echoes the internal error"
    assert _xr46_rejected(response) == [{"index": 1, "date": refused.rate_date.isoformat(), "reason": reason}]


@pytest.mark.asyncio
async def test_xr46_upsert_rates_endpoint_answers_400_with_an_object_naming_every_refused_rate(monkeypatch):
    """X-R46: four rates, each refused for its own reason, their dates going backwards: EUR → JPY 160, on which the
    store raises a ``RuntimeError``; EUR → EUR 1; EUR → GBP 0.85, on which the store raises a ``ValueError``; USD → EUR
    1E-1000000, which ``normalize_storable_rate`` refuses.

    Red on HEAD 1c1456713: 400 with a string ``detail``, «All rates failed: Rate 0: …; Rate 1: …; …»: the editor can show
    it whole, never say which row was refused and why.
    Contract: 400; ``detail`` exactly ``{"code", "message", "rejected"}``: ``code`` ``fx_rates_refused``; ``message`` the
    same «All rates failed: …» text, the four strings of ``errors`` joined by «; »; ``rejected`` the four as JSON, in
    request order (neither by date nor by reason), each with its index, date and reason. The detail is JSON as it
    stands (the renderer of the 400 answers 500 to a date or a model) and never holds the internal error's text
    (MF-SEC9a).
    """
    _xr46_unstorable_barrier("USD", "EUR")
    items = [_xr46_item(3, "EUR", "JPY", "160"), _xr46_item(2, "EUR", "EUR", "1"), _xr46_item(1, "EUR", "GBP", "0.85"), _xr46_item(0, "USD", "EUR", XR46_UNSTORABLE)]
    _xr46_store(monkeypatch, {items[0].rate_date: RuntimeError(XR46_SECRET), items[2].rate_date: ValueError(XR46_STORE_REFUSAL)})
    errors = [
        "Rate 0: Failed: internal error",
        "Rate 1: Base and quote must be different (got EUR)",
        f"Rate 2: Validation error: {XR46_STORE_REFUSAL}",
        f"Rate 3: Validation error: {fx_rate_refusal('USD', 'EUR', items[3].rate_date)}",
    ]
    reasons = ["internal_error", "same_currency", "invalid_rate", "rate_not_storable"]

    with pytest.raises(HTTPException) as exc:
        await _xr46_upsert(items)

    detail = exc.value.detail
    assert exc.value.status_code == 400, f"{exc.value.status_code}: {detail!r}"
    assert isinstance(detail, dict), f"X-R46: the 400's detail is a {type(detail).__name__}, not the object {{code, message, rejected}}: {detail!r}"
    try:
        written = json.loads(json.dumps(detail, allow_nan=False))
    except (TypeError, ValueError) as error:
        pytest.fail(f"X-R46: the 400's detail is not JSON as it stands ({error}): the server would answer 500 rendering it: {detail!r}")
    assert written == detail, f"the 400's detail changes once written as JSON: {detail!r}"
    assert set(detail) == {"code", "message", "rejected"}, detail
    assert detail["code"] == "fx_rates_refused", detail
    assert detail["message"] == f"All rates failed: {'; '.join(errors)}", detail["message"]
    assert detail["rejected"] == [{"index": index, "date": item.rate_date.isoformat(), "reason": reason} for index, (item, reason) in enumerate(zip(items, reasons, strict=True))], detail["rejected"]
    assert XR46_SECRET not in json.dumps(detail), "MF-SEC9a: the 400 echoes the internal error"


@pytest.mark.asyncio
async def test_xr46_guard_upsert_rates_endpoint_answers_an_empty_rejected_when_every_rate_is_kept(monkeypatch):
    """X-R46 guard of the cure: EUR → GBP 0.85 and USD → EUR 0.8 (stored EUR/USD 1.25), both kept.

    Red on HEAD 1c1456713 only because ``rejected`` does not exist; green once it does.
    Contract: 200; two results, both handed to the store, no error; ``rejected`` ``[]``.
    """
    store = _xr46_store(monkeypatch)
    items = [_xr46_item(0, "EUR", "GBP", "0.85"), _xr46_item(1, "USD", "EUR", "0.8")]

    response = await _xr46_upsert(items)

    assert (response.success_count, response.errors) == (2, []), response
    assert _xr46_handed(store) == [item.rate_date for item in items]
    assert _xr46_rejected(response) == []


def test_xr46_fx_rate_rejection_holds_one_of_four_reasons_and_the_answer_defaults_to_none():
    """X-R46, the schemas alone: ``FXRateRejection`` holds an index, a date and one of the four reasons, and refuses any
    other reason; an ``FXBulkUpsertResponse`` built without ``rejected`` answers ``[]``.

    Red on HEAD 1c1456713: ``schemas.fx`` has no ``FXRateRejection``.
    """
    rejection = getattr(fx_schemas, "FXRateRejection", None)
    assert rejection is not None, "X-R46: backend.app.schemas.fx has no FXRateRejection"
    for reason in XR46_FX_REASONS:
        assert rejection(index=2, date=XR46_DAY, reason=reason).model_dump(mode="json", by_alias=True) == {"index": 2, "date": XR46_DAY.isoformat(), "reason": reason}
    with pytest.raises(ValidationError):
        rejection(index=2, date=XR46_DAY, reason="not_a_reason")
    assert fx_schemas.FXBulkUpsertResponse(results=[], success_count=0).model_dump(mode="json", by_alias=True).get("rejected") == []


@pytest.mark.asyncio
@pytest.mark.usefixtures("xr38_khr_mmk")
async def test_xr46_wire_200_of_upsert_rates_carries_rejected():
    """X-R46 on the wire, on the lane's test database: KHR → MMK "1.5", then MMK → KHR "1E-1000000" (KHR/MMK
    1E+1000000 once inverted, which ``normalize_storable_rate`` refuses), as the FX editor posts them.

    Red on HEAD 1c1456713: the JSON of the 200 has no ``rejected``.
    Contract: 200; 1.5 stored alone; the body's ``errors`` one string, «Rate 1: …», and its ``rejected`` ``[{"index": 1,
    "date": "1986-03-04", "reason": "rate_not_storable"}]``.
    """
    _xr46_unstorable_barrier("MMK", "KHR")
    story = f'POST /fx/currencies/rate of KHR → MMK "1.5" on {XR38_DAYS[0]} and MMK → KHR "{XR46_UNSTORABLE}" on {XR38_DAYS[1]}'

    response = await _xr38_post([_xr38_item(XR38_DAYS[0], "KHR", "MMK", '"1.5"'), _xr38_item(XR38_DAYS[1], "MMK", "KHR", f'"{XR46_UNSTORABLE}"')], story)

    assert response.status_code == 200, f"{story} answered {response.status_code} {response.text[:300]}"
    stored = await _xr38_stored()
    assert stored == {XR38_DAYS[0]: Decimal("1.5")}, f"barrier: {story} stored {stored}, expected 1.5 alone"
    body = response.json()
    assert len(body["errors"]) == 1 and body["errors"][0].startswith("Rate 1:"), body["errors"]
    assert body.get("rejected") == [{"index": 1, "date": XR38_DAYS[1].isoformat(), "reason": "rate_not_storable"}], f"X-R46: {story}: the 200 does not say which rate it refused: {body}"


@pytest.mark.asyncio
@pytest.mark.usefixtures("xr38_khr_mmk")
async def test_xr46_wire_200_of_upsert_rates_lists_a_rate_0_at_10_decimal_places_as_rate_not_storable():
    """X-R46 on the wire, on the lane's test database: KHR → MMK "1.5", then KHR → MMK "1E-11", which the endpoint's own
    ``normalize_storable_rate`` keeps and the real ``upsert_rates_bulk`` refuses at its X-R38 check (0 once cut to the
    10 decimal places of ``fx_rates.rate``): the commonest refusal of the FX editor, made by the store, not the endpoint.

    Red on HEAD 1c1456713: the JSON of the 200 has no ``rejected``; the store's refusal is a plain ``ValueError``,
    which the contract read literally would call ``invalid_rate``.
    Contract (decided 17/10): the store raises ``FXRateNotStorableError``, its text unchanged, and the endpoint reads it
    as ``rate_not_storable``. 200; 1.5 stored alone; ``errors`` exactly as before, «Rate 1: Validation error: » and
    ``fx_rate_refusal``'s text for KHR/MMK on 1986-03-04; ``rejected`` ``[{"index": 1, "date": "1986-03-04", "reason":
    "rate_not_storable"}]``. The answer is what is pinned, not how the endpoint learns the reason.
    """
    rate = Decimal("1E-11")
    assert normalize_storable_rate("KHR", "MMK", rate) is not None and storable_fx_rate(rate) is None, f"barrier: KHR → MMK {rate} should pass the endpoint's normalize_storable_rate and be refused by storable_fx_rate, in the store"
    story = f'POST /fx/currencies/rate of KHR → MMK "1.5" on {XR38_DAYS[0]} and KHR → MMK "1E-11" on {XR38_DAYS[1]}'

    response = await _xr38_post([_xr38_item(XR38_DAYS[0], "KHR", "MMK", '"1.5"'), _xr38_item(XR38_DAYS[1], "KHR", "MMK", '"1E-11"')], story)

    assert response.status_code == 200, f"{story} answered {response.status_code} {response.text[:300]}"
    stored = await _xr38_stored()
    assert stored == {XR38_DAYS[0]: Decimal("1.5")}, f"barrier: {story} stored {stored}, expected 1.5 alone"
    body = response.json()
    assert body["errors"] == [f"Rate 1: Validation error: {fx_rate_refusal('KHR', 'MMK', XR38_DAYS[1])}"], body["errors"]
    assert body.get("rejected") == [{"index": 1, "date": XR38_DAYS[1].isoformat(), "reason": "rate_not_storable"}], f"X-R46: {story}: the 200 does not list the store's X-R38 refusal as rate_not_storable: {body}"


@pytest.mark.asyncio
@pytest.mark.usefixtures("xr38_khr_mmk")
async def test_xr46_wire_400_of_upsert_rates_carries_an_object_detail():
    """X-R46 on the wire, on the lane's test database: MMK → KHR "1E-1000000" alone, refused.

    Red on HEAD 1c1456713: 400 with ``{"detail": "All rates failed: Rate 0: …"}``, a string.
    Contract: 400; nothing stored; ``detail`` ``{"code": "fx_rates_refused", "message": "All rates failed: Rate 0: …",
    "rejected": [{"index": 0, "date": "1986-03-03", "reason": "rate_not_storable"}]}``.
    """
    _xr46_unstorable_barrier("MMK", "KHR")
    story = f'POST /fx/currencies/rate of MMK → KHR "{XR46_UNSTORABLE}" on {XR38_DAYS[0]}'

    response = await _xr38_post([_xr38_item(XR38_DAYS[0], "MMK", "KHR", f'"{XR46_UNSTORABLE}"')], story)

    assert response.status_code == 400, f"{story} answered {response.status_code} {response.text[:300]}"
    stored = await _xr38_stored()
    assert not stored, f"barrier: {story} was refused, yet rows were written: {stored}"
    detail = response.json().get("detail")
    assert isinstance(detail, dict), f"X-R46: {story}: the 400's detail is a {type(detail).__name__}, not the object {{code, message, rejected}}: {detail!r}"
    assert (detail.get("code"), detail.get("rejected")) == ("fx_rates_refused", [{"index": 0, "date": XR38_DAYS[0].isoformat(), "reason": "rate_not_storable"}]), detail
    assert str(detail.get("message")).startswith("All rates failed: Rate 0:"), detail


# ============================================================================
# X-R41: POST /fx/currencies/convert of an amount of 0
# ============================================================================
#
# The defect, on HEAD ab74aafbf: ``convert_currency_bulk`` gives each daily result between two currencies the rate
# ``converted / from_amount`` (``api/v1/fx/currencies.py`` ~582). ``convert_bulk`` converts 0 to 0 (0 × the rate), so an
# amount of 0 divides 0 by 0: ``decimal.InvalidOperation`` ([DivisionUndefined]) escapes the handler, which has no try
# around the division, and the server answers 500 to the whole request, its other conversions with it. An amount of 0 is
# not only typed: the asset detail converts its live native value as it is (``assetDetailLive.svelte.ts``).
#
# Contract (X-R41): a daily conversion of 0 reaches ``convert_bulk`` as one unit of its source currency,
# ``Currency(code=<source>, amount=Decimal("1"))``, as the signal blocks already do, the request's amount staying in the
# expansion. The answer: 200; each result's ``to_amount`` 0 in ``to_currency``, its ``from_amount`` the request's, its
# ``rate`` the unit's converted amount (the pair's rate on that day), its date and ``backward_fill_info`` as for any
# amount. Between the same currency: ``rate`` None and ``to_amount`` 0, as today. Any other amount is unchanged: handed to
# ``convert_bulk`` as it is, its ``rate`` converted / amount.
#
# The handler is called directly, ``convert_bulk`` patched where it reads it (``_xr41_convert_bulk``): a recording double
# that converts as the real one, the amount times its pair's fixed rate (the amount itself between the same currency), and
# fills back the days it is told to; nothing reaches a database. One case reads the answer on the wire instead
# (``_xr41_post``, as ``_xr38_post``), on the lane's test database and a BAM/SSP rate it stores.
#
# Isolation: the unit's default, write-scoped. BAM/SSP is this block's own (no seed and no other test uses either
# currency): every BAM/SSP rate is wiped before and after the wire case, and no other rate is read or written.

XR41_DAYS = (date(1987, 6, 1), date(1987, 6, 2))
XR41_EUR_USD = Decimal("1.1")  # the double's EUR → USD rate
XR41_PAIR = ("BAM", "SSP")  # the wire case's own pair, stored BAM/SSP (base < quote)
XR41_STORED_RATE = Decimal("2471.25")  # 1 BAM = 2471.25 SSP: a double exactly, so the column reads it back as written
_XR41_CONVERT_URL = "/api/v1/fx/currencies/convert"


def _xr41_request(code: str, amount: str, to: str, days: tuple[date, ...] = XR41_DAYS) -> FXConversionRequest:
    """One conversion of the request, as a client posts it: ``amount`` ``code`` → ``to``, from the first of ``days`` to the
    last."""
    return FXConversionRequest.model_validate({"from_amount": {"code": code, "amount": amount}, "to": to, "date_range": {"start": days[0].isoformat(), "end": days[-1].isoformat()}})


def _xr41_converted(amount: Currency, to: str, rates: dict[tuple[str, str], Decimal]) -> Decimal:
    """What the double converts ``amount`` to in ``to``, as ``convert_bulk`` does: the amount itself between the same
    currency, else the amount times its pair's rate in ``rates``."""
    return amount.amount if amount.code == to else amount.amount * rates[(amount.code, to)]


def _xr41_convert_bulk(monkeypatch: pytest.MonkeyPatch, rates: dict[tuple[str, str], Decimal], filled: dict[date, date] | None = None) -> AsyncMock:
    """``convert_bulk`` where the handler reads it, on no database: each conversion handed to it answered by
    ``_xr41_converted``, dated the day asked or, between two currencies, the day ``filled`` maps it to, backward-filled; no
    error. The mock keeps what reached it (``_xr41_handed``)."""
    filled = filled or {}

    async def _convert(_session, conversions, raise_on_error=True):
        results = []
        for amount, to, day in conversions:
            rate_day = day if amount.code == to else filled.get(day, day)
            results.append((Currency(code=to, amount=_xr41_converted(amount, to, rates)), rate_day, rate_day < day))
        return results, []

    double = AsyncMock(side_effect=_convert)
    monkeypatch.setattr(fx_currencies_api, "convert_bulk", double)
    monkeypatch.setattr(fx_currencies_api, "unit_rate_steps", steps_double(lambda source, destination, day: day if source == destination else filled.get(day, day)))
    return double


def _xr41_handed(double: AsyncMock) -> list[tuple[str, Decimal, str, date]]:
    """Every conversion handed to the double, in order: (source currency, amount, target currency, day)."""
    return [(amount.code, amount.amount, to, day) for call in double.await_args_list for amount, to, day in call.args[1]]


def _xr41_answers(response) -> list[tuple]:
    """The results of the answer in order, each as plain values: ``from_amount`` and ``to_amount`` as (code, amount), the
    conversion date, the rate, and the backward fill as (the rate's date, the days back), None without one."""

    def _plain(result) -> tuple:
        fill = result.backward_fill_info
        return ((result.from_amount.code, result.from_amount.amount), (result.to_amount.code, result.to_amount.amount), result.conversion_date, result.rate, None if fill is None else (fill.actual_rate_date, fill.days_back))

    return [_plain(result) for result in response.results]


async def _xr41_convert(request: list[FXConversionRequest], double: AsyncMock, story: str):
    """``POST /fx/currencies/convert`` of ``request``: the handler called directly, its session and its user stubbed. What
    escapes it fails the test naming it, with what reached the double: an ``HTTPException`` its status, any other exception
    the 500 the server answers."""
    try:
        return await fx_currencies_api.convert_currency_bulk(request, session=AsyncMock(), _current_user=Mock())
    except HTTPException as exc:
        pytest.fail(f"{story} answered {exc.status_code} {exc.detail!r}, convert_bulk received {_xr41_handed(double)}: expected 200 (X-R41)")
    except Exception as exc:  # noqa: BLE001 — what escapes the handler is what the server answers 500 to
        pytest.fail(f"{story} raised {exc!r}, the server answers 500; convert_bulk received {_xr41_handed(double)} (X-R41: 200, an amount of 0 converted as one unit)")


@pytest.mark.asyncio
@pytest.mark.parametrize("zero", [pytest.param("0", id="0"), pytest.param("0.00", id="derived-0.00")])
async def test_xr41_convert_currency_bulk_converts_an_amount_of_0_as_one_unit(monkeypatch, zero):
    """X-R41: EUR ``zero`` → USD over two days, beside EUR 100 → USD over the same two days. The double converts EUR → USD
    at 1.1 and has no rate of its own on the second day: it fills the first day's back.

    Red on HEAD ab74aafbf: the double gets the 0 itself and answers USD 0; the handler divides that 0 by the amount, 0, and
    ``decimal.InvalidOperation`` escapes it: the server's 500, the 100's conversions lost with it.
    Contract: 200, no error. The double gets one unit, EUR 1 → USD, for the 0, and EUR 100 for the 100, each once (X-Q3: both
    days read the same rate row). The answer, in request order and days ascending: each day of the 0 is EUR 0 as requested → USD 0, at the rate of
    the double's unit, 1.1, with the backward fill of the 100's same day; the 100's are USD 110 at 1.1, the first day not
    filled, the second filled 1 day back. The ``derived-`` case reads the same rule with a 0 written 0.00.
    """
    rates = {("EUR", "USD"): XR41_EUR_USD}
    double = _xr41_convert_bulk(monkeypatch, rates, filled={XR41_DAYS[1]: XR41_DAYS[0]})
    unit = _xr41_converted(Currency(code="EUR", amount=Decimal("1")), "USD", rates)  # what the double answers one EUR: USD 1.1
    story = f"POST /fx/currencies/convert of EUR {zero} → USD and EUR 100 → USD, each from {XR41_DAYS[0]} to {XR41_DAYS[1]}"

    response = await _xr41_convert([_xr41_request("EUR", zero, "USD"), _xr41_request("EUR", "100", "USD")], double, story)

    handed = sorted(_xr41_handed(double))
    # X-Q3: both days read the first day's rate row (the double fills it back), so each amount is converted once, on the first day
    expected_handed = sorted(("EUR", amount, "USD", XR41_DAYS[0]) for amount in (Decimal("1"), Decimal("100")))
    assert handed == expected_handed, f"X-R41: {story}: convert_bulk received {handed}, expected one unit, EUR 1 → USD, for the {zero}, and EUR 100 for the 100, each once for the stretch of the two days"
    assert (response.success_count, response.errors) == (4, []), f"{story}: {response}"
    answers = _xr41_answers(response)
    filled_back = (XR41_DAYS[0], 1)
    expected = [
        (("EUR", Decimal(zero)), ("USD", Decimal("0")), XR41_DAYS[0], unit, None),
        (("EUR", Decimal(zero)), ("USD", Decimal("0")), XR41_DAYS[1], unit, filled_back),
        (("EUR", Decimal("100")), ("USD", Decimal("110")), XR41_DAYS[0], XR41_EUR_USD, None),
        (("EUR", Decimal("100")), ("USD", Decimal("110")), XR41_DAYS[1], XR41_EUR_USD, filled_back),
    ]
    assert answers == expected, f"X-R41: {story} answered {answers}, expected {expected}"


@pytest.mark.asyncio
async def test_xr41_guard_convert_currency_bulk_answers_0_and_no_rate_for_the_same_currency(monkeypatch):
    """X-R41 guard, green on HEAD ab74aafbf and after: EUR 0 → EUR on one day.

    Green today: between the same currency the handler never divides, the rate None. Pinned for the cure, which may send
    this 0 as a unit too (the double, as ``convert_bulk``, answers that unit EUR 1): 200, no error, one result, EUR 0 as
    requested → EUR 0, ``rate`` None, no backward fill.
    """
    double = _xr41_convert_bulk(monkeypatch, {})
    story = f"POST /fx/currencies/convert of EUR 0 → EUR on {XR41_DAYS[0]}"

    response = await _xr41_convert([_xr41_request("EUR", "0", "EUR", XR41_DAYS[:1])], double, story)

    assert (response.success_count, response.errors) == (1, []), f"{story}: {response}"
    answers = _xr41_answers(response)
    assert answers == [(("EUR", Decimal("0")), ("EUR", Decimal("0")), XR41_DAYS[0], None, None)], f"X-R41: {story} answered {answers}, expected EUR 0 and no rate"


@pytest.mark.asyncio
async def test_xr41_guard_convert_currency_bulk_keeps_the_rate_of_an_amount_that_is_not_0(monkeypatch):
    """X-R41 guard, green on HEAD ab74aafbf and after: EUR 100 → USD on one day, the double converting at 1.1.

    Pinned for the cure: an amount that is not 0 is unchanged. The double gets EUR 100 itself and no unit beside it; the
    answer is 200, no error, EUR 100 → USD 110 at the rate converted / amount, 1.1, both exactly (``Decimal``), no
    backward fill.
    """
    double = _xr41_convert_bulk(monkeypatch, {("EUR", "USD"): XR41_EUR_USD})
    story = f"POST /fx/currencies/convert of EUR 100 → USD on {XR41_DAYS[0]}"

    response = await _xr41_convert([_xr41_request("EUR", "100", "USD", XR41_DAYS[:1])], double, story)

    handed = _xr41_handed(double)
    assert handed == [("EUR", Decimal("100"), "USD", XR41_DAYS[0])], f"X-R41: {story}: convert_bulk received {handed}, expected EUR 100 alone"
    assert (response.success_count, response.errors) == (1, []), f"{story}: {response}"
    answers = _xr41_answers(response)
    assert answers == [(("EUR", Decimal("100")), ("USD", Decimal("110")), XR41_DAYS[0], Decimal("1.1"), None)], f"X-R41: {story} answered {answers}, expected USD 110 at 1.1"


async def _xr41_wipe() -> None:
    """Drop every BAM/SSP rate: the pair is this block's own."""
    async with AsyncSession(get_async_engine()) as session:
        await session.execute(delete(FxRate).where(FxRate.base == XR41_PAIR[0], FxRate.quote == XR41_PAIR[1]))
        await session.commit()


@pytest_asyncio.fixture
async def xr41_bam_ssp_rate():
    """X-R41: during the test BAM/SSP holds one rate, ``XR41_STORED_RATE`` on the first of ``XR41_DAYS``; before and
    after it, none."""
    await _xr41_wipe()
    try:
        async with AsyncSession(get_async_engine()) as session:
            session.add(FxRate(date=XR41_DAYS[0], base=XR41_PAIR[0], quote=XR41_PAIR[1], rate=XR41_STORED_RATE, source="MANUAL"))
            await session.commit()
        yield
    finally:
        await _xr41_wipe()


async def _xr41_stored() -> dict[date, Decimal]:
    """The BAM/SSP rates by date, read through the model, as the app reads them."""
    async with AsyncSession(get_async_engine()) as session:
        rows = (await session.execute(select(FxRate.date, FxRate.rate).where(FxRate.base == XR41_PAIR[0], FxRate.quote == XR41_PAIR[1]))).all()
    return {row.date: row.rate for row in rows}


async def _xr41_post(conversions: list[dict], story: str) -> httpx.Response:
    """``POST /api/v1/fx/currencies/convert`` with ``conversions`` as JSON, served in process by the FX rate routes on the
    lane's test database, a signed-in user stubbed, as ``_xr38_post``. An exception escaping the app fails the test naming
    it: the server answers 500."""
    app = FastAPI()
    app.include_router(fx_currencies_api.router_currencies, prefix="/api/v1/fx")
    app.dependency_overrides[get_current_user] = _xr38_signed_in_user
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        try:
            return await client.post(_XR41_CONVERT_URL, json=conversions)
        except Exception as exc:  # noqa: BLE001 — what escapes the app is what the server answers 500 to
            pytest.fail(f"{story}: POST /fx/currencies/convert raised {exc!r}, the server answers 500 (X-R41: 200, an amount of 0 converted as one unit)")


@pytest.mark.asyncio
@pytest.mark.usefixtures("xr41_bam_ssp_rate")
async def test_xr41_wire_convert_of_0_answers_0_at_the_stored_rate():
    """X-R41 on the wire, on the lane's test database: BAM "0" → SSP over two days, as a client posts it, with one BAM/SSP
    rate stored, 2471.25 on the first day, none on the second (``xr41_bam_ssp_rate``).

    Red on HEAD ab74aafbf: the real ``convert_bulk`` converts the 0 to SSP 0 at the stored rate, the handler divides that 0
    by the amount, 0, and ``decimal.InvalidOperation`` escapes the app: the server answers 500.
    Contract: 200, no error; two results, days ascending, each BAM 0 → SSP 0 at the stored rate, which is what one BAM
    converts to on that day: the first day not filled, the second filled 1 day back from the first.
    """
    first, second = XR41_DAYS
    stored = await _xr41_stored()
    assert stored == {first: XR41_STORED_RATE}, f"barrier: BAM/SSP holds {stored}, expected {XR41_STORED_RATE} on {first} alone"
    story = f'POST /fx/currencies/convert of BAM "0" → SSP from {first} to {second}, BAM/SSP {XR41_STORED_RATE} stored on {first} alone'

    response = await _xr41_post([{"from_amount": {"code": "BAM", "amount": "0"}, "to": "SSP", "date_range": {"start": first.isoformat(), "end": second.isoformat()}}], story)

    assert response.status_code == 200, f"{story} answered {response.status_code} {response.text[:300]}: expected 200 (X-R41)"
    body = FXConvertResponse.model_validate(response.json())
    assert (body.success_count, body.errors) == (2, []), f"{story}: {response.text[:300]}"
    answers = _xr41_answers(body)
    expected = [
        (("BAM", Decimal("0")), ("SSP", Decimal("0")), first, stored[first], None),
        (("BAM", Decimal("0")), ("SSP", Decimal("0")), second, stored[first], (first, 1)),
    ]
    assert answers == expected, f"X-R41: {story} answered {answers}, expected SSP 0 on each day at the stored rate, the second day filled 1 day back"
