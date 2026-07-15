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

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from backend.app.api.v1 import fx as fx_api
from backend.app.db.models import FxConversionRoute
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.fx import FXDeleteItem, FXUpsertItem
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


@pytest.mark.asyncio
async def test_list_routes_returns_deserialized_items():
    """list_routes should deserialize JSON chain_steps into schema items."""
    print_section("list_routes")

    session = AsyncMock()
    session.execute = AsyncMock(
        return_value=_mock_scalar_result(
            [
                FxConversionRoute(
                    base="GHS",
                    quote="KRW",
                    priority=1,
                    chain_steps=json.dumps(
                        [
                            {"from": "GHS", "to": "EUR", "provider": "MOCKFX"},
                            {"from": "EUR", "to": "KRW", "provider": "MOCKFX_FAIL"},
                        ]
                    ),
                ),
                FxConversionRoute(
                    base="GHS",
                    quote="KRW",
                    priority=2,
                    chain_steps=json.dumps(
                        [
                            {"from": "GHS", "to": "KRW", "provider": "MOCKFX"},
                        ]
                    ),
                ),
            ]
        )
    )

    response = await fx_api.list_routes(session=session, _current_user=Mock())

    assert len(response.items) == 2
    assert [item.priority for item in response.items] == [1, 2]
    assert len(response.items[0].chain_steps) == 2
    assert response.items[0].chain_steps[1].provider == "MOCKFX_FAIL"
    assert len(response.items[1].chain_steps) == 1
    print_success("Route list deserialized chain steps correctly")
