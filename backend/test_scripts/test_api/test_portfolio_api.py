"""Portfolio API tests for active /api/v1/portfolio endpoints."""

import json
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1 import portfolio_api
from backend.app.api.v1.auth import get_current_user
from backend.app.config import get_settings
from backend.app.db.models import Asset, Transaction, TransactionType, UserRole, UserSettings
from backend.app.db.session import get_async_engine, get_session_generator
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import (
    PortfolioPlannerSourceProvenance,
    PortfolioPlannerSourceResponse,
    PortfolioPlannerSourceSnapshot,
)
from backend.app.schemas.wac import WACPreviewResultItem, WACQualifyingTX
from backend.app.services.accounts import user_service
from backend.app.services.pac_allocator.source.portfolio_allocation_source import (
    PortfolioPlannerSourceAccessError,
    PortfolioPlannerSourceAssetNotFoundError,
    PortfolioPlannerSourceBrokerNotFoundError,
)
from backend.test_scripts.test_db_config import get_test_db_path, verify_test_database
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_services._lots_steps import expand_steps
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30
SOLE_ADMIN_DELETE_DETAIL = {"error_code": "LAST_ADMIN", "message": "Cannot delete account: you are the last active administrator"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def create_test_user(client: httpx.AsyncClient) -> str:
    username = f"pftest_{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": f"{username}@test.com", "password": "TestPass123!"},
        timeout=TIMEOUT,
    )
    assert resp.status_code == 201
    login_resp = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": "TestPass123!"},
        timeout=TIMEOUT,
    )
    if s := login_resp.cookies.get("session"):
        client.cookies.set("session", s)
    return username


async def delete_current_test_user(client: httpx.AsyncClient, user_id: int) -> None:
    """Delete only this test's authenticated account, with exact sole-admin fallback."""
    response = await client.delete(f"{API_BASE}/auth/users/me", timeout=TIMEOUT)
    if response.status_code == 400 and response.json().get("detail") == SOLE_ADMIN_DELETE_DETAIL:
        is_test_db, _ = verify_test_database()
        assert is_test_db, "Refusing sole-admin cleanup outside the test database"
        async with AsyncSession(get_async_engine()) as session:
            assert await user_service.delete_user(session, user_id)
        return
    assert response.status_code == 200, response.text


async def get_current_user_id(client: httpx.AsyncClient) -> int:
    resp = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return resp.json()["user"]["id"]


async def create_broker(
    client: httpx.AsyncClient,
    name: str | None = None,
    *,
    icon_url: str | None = None,
    portal_url: str | None = None,
    default_import_plugin: str | None = None,
) -> int:
    broker_payload = {
        "name": name or f"Bk_{uuid.uuid4().hex[:6]}",
        "allow_cash_overdraft": True,
    }
    if icon_url is not None:
        broker_payload["icon_url"] = icon_url
    if portal_url is not None:
        broker_payload["portal_url"] = portal_url
    if default_import_plugin is not None:
        broker_payload["default_import_plugin"] = default_import_plugin
    resp = await client.post(
        f"{API_BASE}/brokers",
        json=[broker_payload],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200
    return resp.json()["results"][0]["broker_id"]


async def create_asset(
    client: httpx.AsyncClient,
    currency: str = "EUR",
    quote_base_quantity: int | None = None,
    asset_type: str = "STOCK",
) -> int:
    resp = await client.post(
        f"{API_BASE}/assets",
        json=[
            {
                "display_name": f"As_{uuid.uuid4().hex[:6]}",
                "currency": currency,
                "asset_type": asset_type,
                **({"quote_base_quantity": quote_base_quantity} if quote_base_quantity is not None else {}),
            }
        ],
        timeout=TIMEOUT,
    )
    assert resp.status_code in (200, 201)
    return resp.json()["results"][0]["asset_id"]


async def commit_batch(client: httpx.AsyncClient, **kwargs) -> dict:
    resp = await client.post(f"{API_BASE}/transactions/commit", json=kwargs, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Commit failed: {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data.get("committed") is True, f"Not committed: {data.get('issues', [])}"
    return data


async def post_portfolio_report(client: httpx.AsyncClient, body: dict | None = None) -> httpx.Response:
    """Call unified /portfolio/report endpoint."""
    default_body = {"include_summary": True, "include_history": True, "include_allocation_history": True}
    if body:
        default_body.update(body)
    return await client.post(f"{API_BASE}/portfolio/report", json=default_body, timeout=TIMEOUT)


async def post_portfolio_summary(client: httpx.AsyncClient, body: dict | None = None) -> httpx.Response:
    """Get summary via /report endpoint. Returns a fake Response whose .json() = summary dict."""
    report_body = {"include_summary": True, "include_history": False, "include_allocation_history": False}
    if body:
        report_body.update(body)
    resp = await client.post(f"{API_BASE}/portfolio/report", json=report_body, timeout=TIMEOUT)
    # Wrap: inject summary-level data at top for backward compat with tests
    if resp.status_code == 200:
        report = resp.json()
        summary = report.get("summary") or {}
        # Monkey-patch the response to return summary directly
        resp._summary_data = summary

        def _patched_json(**kwargs):
            return resp._summary_data

        resp.json = _patched_json
    return resp


async def post_portfolio_history(client: httpx.AsyncClient, body: dict | None = None) -> httpx.Response:
    """Get history via /report endpoint. Returns a fake Response whose .json() = history list."""
    report_body = {"include_summary": False, "include_history": True, "include_allocation_history": False}
    if body:
        report_body.update(body)
    resp = await client.post(f"{API_BASE}/portfolio/report", json=report_body, timeout=TIMEOUT)
    if resp.status_code == 200:
        report = resp.json()
        history = report.get("history") or []

        def _patched_json(**kwargs):
            return history

        resp.json = _patched_json
    return resp


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as manager:
        if not manager.start_server():
            pytest.fail("Failed to start test server")
        yield manager


# ---------------------------------------------------------------------------
# TestPortfolioSummaryEndpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPortfolioSummaryEndpoint:
    async def test_unauthenticated(self, test_server):
        """POST /portfolio/summary without auth -> 401."""
        print_section("Portfolio Summary: unauthenticated")
        async with httpx.AsyncClient() as client:
            resp = await post_portfolio_summary(client)
        assert resp.status_code == 401
        print_success("401 as expected")

    async def test_empty_portfolio(self, test_server):
        """New user with no brokers → summary with zero values."""
        print_section("Portfolio Summary: empty portfolio")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            resp = await post_portfolio_summary(client)
        assert resp.status_code == 200
        data = resp.json()
        assert "net_worth" in data
        assert "total_invested" in data
        assert "twrr_percent" in data
        assert "allocation_by_type" in data
        assert "holdings" in data
        assert isinstance(data["holdings"], list)
        assert data["by_broker"] is None
        print_success(f"Empty summary OK, net_worth={data['net_worth']['amount']}")

    async def test_summary_structure_with_data(self, test_server):
        """User with broker + deposit → summary has expected structure."""
        print_section("Portfolio Summary: with deposit")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)

            # Deposit cash
            await commit_batch(
                client,
                creates=[
                    {
                        "broker_id": broker_id,
                        "type": "DEPOSIT",
                        "date": "2025-01-15",
                        "quantity": "0",
                        "cash": {"code": "EUR", "amount": "10000"},
                    }
                ],
            )

            resp = await post_portfolio_summary(client)
        assert resp.status_code == 200
        data = resp.json()
        assert "net_worth" in data
        assert "cash_total" in data
        assert "simple_roi_percent" in data
        assert "missing_fx_pairs" in data
        assert "missing_price_assets" in data
        print_success("Summary structure OK")

    async def test_summary_cash_uses_full_signed_ledger(self, test_server):
        """Cash total uses all signed transaction amounts and reports missing prices."""
        print_section("Portfolio Summary: signed cash ledger")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            asset_id = await create_asset(client)

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2025-01-15", "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2025-01-16", "quantity": "4", "cash": {"code": "EUR", "amount": "-400"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "DIVIDEND", "date": "2025-01-17", "quantity": "0", "cash": {"code": "EUR", "amount": "25"}},
                    {"broker_id": broker_id, "type": "FEE", "date": "2025-01-18", "quantity": "0", "cash": {"code": "EUR", "amount": "-10"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "SELL", "date": "2025-01-19", "quantity": "-1", "cash": {"code": "EUR", "amount": "150"}},
                ],
            )

            resp = await post_portfolio_summary(client)
        assert resp.status_code == 200
        data = resp.json()
        # Cash ledger: 1000 - 400 + 25 - 10 + 150 = 765
        assert data["cash_total"]["amount"].startswith("765")
        assert data["total_invested"]["amount"].startswith("1000")
        # Holdings: no market quote → the unified resolver marks at the most recent *observed trade*.
        # The last trade is the SELL @ 150 (2025-01-19); net qty = 3 → current_value = 450.
        # (The legacy LAST_BUY tier ignored SELLs and would have used the BUY @ 100 → 300.)
        holding = data["holdings"][0]
        assert holding["current_value"] is not None
        assert holding["current_value"].startswith("450")
        assert holding["valuation_source"] == "LAST_TRADE_PRICE"
        assert holding["valuation_effective_unit_price"].startswith("150")
        assert holding["valuation_effective_currency"] == "EUR"
        assert holding["valuation_reference_date"] == "2025-01-19"
        assert holding["valuation_reference_unit_price"].startswith("150")
        assert holding["valuation_reference_currency"] == "EUR"
        assert holding["valuation_split_adjusted"] is False
        assert holding["missing_fx_pair"] is None
        # Asset without market price does NOT appear in missing_price_assets
        # (the observed-trade mark gives it a value — appears in data_quality as warning instead)
        assert len(data["missing_price_assets"]) == 0
        print_success("Signed cash ledger and LAST_TRADE_PRICE reporting OK")

    async def test_summary_uses_quote_base_quantity(self, test_server):
        """Summary valuation honors quote_base_quantity for raw market quotes."""
        print_section("Portfolio Summary: quote base quantity")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            asset_id = await create_asset(client, currency="EUR", quote_base_quantity=100)

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2025-02-01", "quantity": "0", "cash": {"code": "EUR", "amount": "500"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2025-02-02", "quantity": "200", "cash": {"code": "EUR", "amount": "-200"}},
                ],
            )
            price_resp = await client.post(
                f"{API_BASE}/assets/prices",
                json=[
                    {
                        "asset_id": asset_id,
                        "prices": [
                            {
                                "date": "2025-02-03",
                                "close": "102.00",
                                "currency": "EUR",
                            }
                        ],
                    }
                ],
                timeout=TIMEOUT,
            )
            assert price_resp.status_code == 200, f"Price upsert failed: {price_resp.status_code}: {price_resp.text}"

            resp = await post_portfolio_summary(client)
        assert resp.status_code == 200
        data = resp.json()
        # qty=200, quote_base=100, price=102 → value = 200 * 102 / 100 = 204
        assert data["holdings"][0]["current_value"].startswith("204")
        assert data["net_worth"]["amount"].startswith("504")
        print_success("quote_base_quantity summary valuation OK")

    async def test_filter_by_broker(self, test_server):
        """broker_ids body field filters the response."""
        print_section("Portfolio Summary: filter by broker")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)

            resp = await post_portfolio_summary(client, {"broker_ids": [broker_id]})
        assert resp.status_code == 200
        print_success("Broker filter OK")

    async def test_include_breakdown(self, test_server):
        """include_breakdown=true in body -> by_broker is populated."""
        print_section("Portfolio Summary: include_breakdown")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            await create_broker(client)

            resp = await post_portfolio_summary(client, {"include_breakdown": True})
        assert resp.status_code == 200
        data = resp.json()
        # by_broker may be empty list if no accessible brokers, but must be a list
        assert data["by_broker"] is not None
        assert isinstance(data["by_broker"], list)
        print_success("include_breakdown OK")

    async def test_breakdown_scales_by_owner_share(self, test_server):
        """R2-F2b: the brokers LIST page cards read summary.by_broker from
        POST /portfolio/report (include_breakdown=true). A 30% OWNER must see
        30%-scaled, NON-ZERO numbers — an intermediate build served zeros there
        (the per-broker loop dropped the share application)."""
        print_section("Portfolio Summary: by_broker scaled by owner share")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            asset_id = await create_asset(client)

            # DEPOSIT 900 + DIVIDEND 90 → cash 990, net_worth 990, gain 90 at 100%.
            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2025-01-01", "cash": {"code": "EUR", "amount": "900"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "DIVIDEND", "date": "2025-01-02", "quantity": "0", "cash": {"code": "EUR", "amount": "90"}},
                ],
            )

            # Cut the caller's share to 30% via the production write path.
            me = (await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)).json()["user"]["id"]
            resp = await client.put(
                f"{API_BASE}/brokers/{broker_id}/access",
                json=[{"user_id": me, "role": "OWNER", "share_percentage": 0.3}],
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, resp.text

            resp = await post_portfolio_summary(client, {"include_breakdown": True})
            assert resp.status_code == 200, resp.text
            data = resp.json()

            mine = [b for b in data["by_broker"] if b["broker_id"] == broker_id]
            assert len(mine) == 1, f"my broker missing from by_broker: {data['by_broker']}"
            entry = mine[0]

            net_worth = Decimal(entry["net_worth"]["amount"])
            cash_total = Decimal(entry["cash_total"]["amount"])
            gain_loss = Decimal(entry["gain_loss"]["amount"])

            # Scaled to 30% — and non-zero, which is the actual regression guard.
            assert net_worth == Decimal("297"), f"net_worth must be 990×0.3=297, got {net_worth}"
            assert cash_total == Decimal("297"), f"cash_total must be 990×0.3=297, got {cash_total}"
            assert gain_loss == Decimal("27"), f"gain_loss must be 90×0.3=27, got {gain_loss}"
            assert net_worth != 0 and cash_total != 0 and gain_loss != 0, "by_broker served zeros for a 30% owner"

            # Cleanup: the broker (force-cascades its transactions), then the asset.
            await client.delete(f"{API_BASE}/brokers", params={"ids": [broker_id], "force": True}, timeout=TIMEOUT)
            await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
            print_success("by_broker scaled by owner share OK")

    async def test_invalid_broker_id_ignored(self, test_server):
        """Non-existent broker_id in body -> empty result (no 500)."""
        print_section("Portfolio Summary: nonexistent broker")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            resp = await post_portfolio_summary(client, {"broker_ids": [999999]})
        assert resp.status_code == 200
        print_success("Nonexistent broker handled gracefully")


# ---------------------------------------------------------------------------
# TestPortfolioHistoryEndpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPortfolioHistoryEndpoint:
    async def test_unauthenticated(self, test_server):
        """POST /portfolio/history without auth -> 401."""
        print_section("Portfolio History: unauthenticated")
        async with httpx.AsyncClient() as client:
            resp = await post_portfolio_history(client)
        assert resp.status_code == 401
        print_success("401 as expected")

    async def test_empty_history(self, test_server):
        """New user → history is empty array."""
        print_section("Portfolio History: empty")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            resp = await post_portfolio_history(client)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        print_success(f"History: {len(data)} points")

    async def test_history_with_transactions(self, test_server):
        """History with transactions returns points with correct structure."""
        print_section("Portfolio History: with transactions")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            await commit_batch(
                client,
                creates=[
                    {
                        "broker_id": broker_id,
                        "type": "DEPOSIT",
                        "date": "2025-03-01",
                        "quantity": "0",
                        "cash": {"code": "EUR", "amount": "5000"},
                    }
                ],
            )
            resp = await post_portfolio_history(client)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            point = data[0]
            assert "date" in point
            assert "cash_value" in point
            assert "market_value" in point
            assert "nav_value" in point
        print_success("History structure OK")

    async def test_history_date_range_filter(self, test_server):
        """date_range body filter narrows history."""
        print_section("Portfolio History: date range filter")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            await create_broker(client)
            resp = await post_portfolio_history(
                client,
                {"date_range": {"start": "2025-01-01", "end": "2025-06-30"}},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        print_success("Date range filter OK")

    async def test_history_cash_uses_all_signed_transactions(self, test_server):
        """History cash curve includes signed BUY/DIVIDEND/FEE events."""
        print_section("Portfolio History: signed cash ledger")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            asset_id = await create_asset(client)

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2025-03-01", "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2025-03-02", "quantity": "4", "cash": {"code": "EUR", "amount": "-400"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "DIVIDEND", "date": "2025-03-03", "quantity": "0", "cash": {"code": "EUR", "amount": "25"}},
                    {"broker_id": broker_id, "type": "FEE", "date": "2025-03-04", "quantity": "0", "cash": {"code": "EUR", "amount": "-10"}},
                ],
            )
            resp = await post_portfolio_history(
                client,
                {"date_range": {"start": "2025-03-01", "end": "2025-03-04"}},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert [point["date"] for point in data] == ["2025-03-01", "2025-03-02", "2025-03-03", "2025-03-04"]
        assert data[0]["cash_value"]["amount"].startswith("1000")
        assert data[1]["cash_value"]["amount"].startswith("600")
        assert data[2]["cash_value"]["amount"].startswith("625")
        assert data[3]["cash_value"]["amount"].startswith("615")
        print_success("Signed cash curve OK")

    async def test_history_uses_quote_base_quantity(self, test_server):
        """History mark-to-market uses quote_base_quantity for invested/nav values."""
        print_section("Portfolio History: quote base quantity")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            asset_id = await create_asset(client, currency="EUR", quote_base_quantity=100)

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2025-04-01", "quantity": "0", "cash": {"code": "EUR", "amount": "500"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2025-04-02", "quantity": "200", "cash": {"code": "EUR", "amount": "-200"}},
                ],
            )
            price_resp = await client.post(
                f"{API_BASE}/assets/prices",
                json=[
                    {
                        "asset_id": asset_id,
                        "prices": [
                            {
                                "date": "2025-04-03",
                                "close": "102.00",
                                "currency": "EUR",
                            }
                        ],
                    }
                ],
                timeout=TIMEOUT,
            )
            assert price_resp.status_code == 200, f"Price upsert failed: {price_resp.status_code}: {price_resp.text}"

            resp = await post_portfolio_history(
                client,
                {"date_range": {"start": "2025-04-03", "end": "2025-04-03"}},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["market_value"]["amount"].startswith("204")
        assert data[0]["nav_value"]["amount"].startswith("504")
        print_success("quote_base_quantity history valuation OK")


# ---------------------------------------------------------------------------
# TestPortfolioReportEndpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPortfolioReportEndpoint:
    async def test_report_response_has_exactly_fourteen_sections(self, test_server):
        """The report wire shape is exactly these fourteen sections: the twelve of before, plus ``range`` and
        ``mwrr_line`` of the series in steps (D-P4, cure B).

        A section removed from the report must leave the wire, not linger as a null
        key. The API serializes every unrequested section as null, so the default
        request is enough to see the complete set of top-level keys.
        """
        print_section("Portfolio Report: exactly fourteen sections")
        expected_sections = {
            "metadata",
            "range",
            "mwrr_line",
            "summary",
            "history",
            "allocation_history",
            "data_quality",
            "positions_contribution",
            "broker_pnl_history",
            "pnl_candles",
            "income_history",
            "cost_history",
            "deposit_history",
            "acquisition_funding",
        }

        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            user_id = await get_current_user_id(client)
            try:
                response = await post_portfolio_report(client)
                assert response.status_code == 200, response.text
                sections = set(response.json())
                assert sections == expected_sections, f"unexpected sections: {sorted(sections - expected_sections)}; missing sections: {sorted(expected_sections - sections)}"
            finally:
                await delete_current_test_user(client, user_id)

        print_success("Report carries exactly the twelve sections")

    async def test_report_rejects_allocation_source_field(self, test_server):
        """The report request has no allocation_source field.

        The strict request model rejects it with 422 extra_forbidden instead of
        silently ignoring it, so a stale client fails loudly. Planner data is served
        by POST /portfolio/allocation-source.
        """
        print_section("Portfolio Report: allocation_source field rejected")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            user_id = await get_current_user_id(client)
            try:
                response = await post_portfolio_report(client, {"allocation_source": {"as_of_date": "2026-08-20"}})
                assert response.status_code == 422, response.text
                assert [(error["loc"], error["type"]) for error in response.json()["detail"]] == [(["body", "allocation_source"], "extra_forbidden")]
            finally:
                await delete_current_test_user(client, user_id)

        print_success("allocation_source field rejected as extra_forbidden")

    async def test_report_serializes_typed_yield_on_cost_statuses_and_ignores_date_from(
        self,
        test_server,
    ):
        """Holding DTO exposes available/no-income/unavailable YOC without trimming its own window."""
        print_section("Portfolio Report: Yield on Cost serialization")
        broker_id = None
        asset_ids: list[int] = []
        user_id = None
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            me_response = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
            assert me_response.status_code == 200, me_response.text
            user_id = me_response.json()["user"]["id"]
            try:
                broker_id = await create_broker(client)
                available_asset_id = await create_asset(client, asset_type="BOND")
                asset_ids.append(available_asset_id)
                zero_available_asset_id = await create_asset(client, asset_type="STOCK")
                asset_ids.append(zero_available_asset_id)
                no_income_asset_id = await create_asset(client, asset_type="CRYPTO")
                asset_ids.append(no_income_asset_id)
                recent_asset_id = await create_asset(client, asset_type="HOLD")
                asset_ids.append(recent_asset_id)

                await commit_batch(
                    client,
                    creates=[
                        {
                            "broker_id": broker_id,
                            "asset_id": available_asset_id,
                            "type": "BUY",
                            "date": "2024-01-01",
                            "quantity": "10",
                            "cash": {"code": "EUR", "amount": "-100"},
                        },
                        {
                            "broker_id": broker_id,
                            "asset_id": available_asset_id,
                            "type": "DIVIDEND",
                            "date": "2025-01-01",
                            "quantity": "0",
                            "cash": {"code": "EUR", "amount": "20"},
                        },
                        {
                            "broker_id": broker_id,
                            "asset_id": zero_available_asset_id,
                            "type": "BUY",
                            "date": "2024-01-01",
                            "quantity": "5",
                            "cash": {"code": "EUR", "amount": "-50"},
                        },
                        {
                            "broker_id": broker_id,
                            "asset_id": zero_available_asset_id,
                            "type": "DIVIDEND",
                            "date": "2025-01-01",
                            "quantity": "0",
                            "cash": {"code": "EUR", "amount": "0"},
                        },
                        {
                            "broker_id": broker_id,
                            "asset_id": no_income_asset_id,
                            "type": "BUY",
                            "date": "2024-01-01",
                            "quantity": "2",
                            "cash": {"code": "EUR", "amount": "-20"},
                        },
                        {
                            "broker_id": broker_id,
                            "asset_id": recent_asset_id,
                            "type": "BUY",
                            "date": "2025-12-01",
                            "quantity": "4",
                            "cash": {"code": "EUR", "amount": "-40"},
                        },
                    ],
                )

                response = await post_portfolio_report(
                    client,
                    {
                        "broker_ids": [broker_id],
                        "date_range": {
                            "start": "2025-07-01",
                            "end": "2025-12-31",
                        },
                        "include_history": False,
                        "include_allocation_history": False,
                        "include_positions_contribution": False,
                    },
                )
                assert response.status_code == 200, response.text
                report = response.json()
                serialized_holdings = report["summary"]["holdings"]
                assert serialized_holdings
                for holding in serialized_holdings:
                    assert "yield_on_cost" in holding
                    assert holding["yield_on_cost"] is not None
                    assert "net_zero" in holding["yield_on_cost"]["provenance"]

                holdings = {(holding["asset_id"], holding["broker_id"]): holding for holding in serialized_holdings}

                available = holdings[(available_asset_id, broker_id)]["yield_on_cost"]
                assert available["status"] == "available"
                assert Decimal(available["value"]) == Decimal("0.2")
                assert available["reason"] is None
                assert available["provenance"]["source"] == "transactions"
                assert available["provenance"]["window_start"] == "2025-01-01"
                assert available["provenance"]["window_end"] == "2025-12-31"
                assert available["provenance"]["first_pair_transaction_date"] == "2024-01-01"
                assert available["provenance"]["gross_income_transaction_count"] == 1
                assert available["provenance"]["gross_income_per_unit"]["code"] == "EUR"
                assert Decimal(available["provenance"]["gross_income_per_unit"]["amount"]) == Decimal("2")
                assert available["provenance"]["net_zero"] is False

                zero_available = holdings[(zero_available_asset_id, broker_id)]["yield_on_cost"]
                assert zero_available["status"] == "available"
                assert Decimal(zero_available["value"]) == Decimal("0")
                assert zero_available["reason"] is None
                assert zero_available["provenance"]["gross_income_transaction_count"] == 1
                assert zero_available["provenance"]["gross_income_per_unit"]["code"] == "EUR"
                assert Decimal(zero_available["provenance"]["gross_income_per_unit"]["amount"]) == Decimal("0")
                assert zero_available["provenance"]["net_zero"] is True

                no_income = holdings[(no_income_asset_id, broker_id)]["yield_on_cost"]
                assert no_income["status"] == "no_income"
                assert Decimal(no_income["value"]) == Decimal("0")
                assert no_income["reason"] is None
                assert no_income["provenance"]["gross_income_transaction_count"] == 0
                assert Decimal(no_income["provenance"]["gross_income_per_unit"]["amount"]) == Decimal("0")
                assert no_income["provenance"]["net_zero"] is False

                unavailable = holdings[(recent_asset_id, broker_id)]["yield_on_cost"]
                assert unavailable["status"] == "unavailable"
                assert unavailable["value"] is None
                assert unavailable["reason"] == "insufficient_history"
                assert unavailable["provenance"]["first_pair_transaction_date"] == "2025-12-01"
                assert unavailable["provenance"]["net_zero"] is False
            finally:
                if broker_id is not None:
                    cleanup_broker = await client.delete(
                        f"{API_BASE}/brokers",
                        params={"ids": [broker_id], "force": True},
                        timeout=TIMEOUT,
                    )
                    assert cleanup_broker.status_code == 200, cleanup_broker.text
                if asset_ids:
                    cleanup_assets = await client.delete(
                        f"{API_BASE}/assets",
                        params={"asset_ids": asset_ids},
                        timeout=TIMEOUT,
                    )
                    assert cleanup_assets.status_code == 200, cleanup_assets.text
                if user_id is not None:
                    await delete_current_test_user(client, user_id)

        print_success("Yield on Cost statuses serialize with independent trailing window")

    async def test_report_positions_contribution_is_date_aware(self, test_server):
        """Report uses date_to snapshot for holdings and serializes performance rows + other effects.
        It owns and deletes its user, broker, asset, six transactions and one price, broker first:
        its force delete removes the transactions that would otherwise block the asset delete,
        and the asset delete removes the price by cascade."""
        print_section("Portfolio Report: date-aware holdings and contribution")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            user_id = await get_current_user_id(client)
            broker_id: int | None = None
            asset_id: int | None = None
            try:
                broker_id = await create_broker(client)
                asset_id = await create_asset(client)

                await commit_batch(
                    client,
                    creates=[
                        {"broker_id": broker_id, "type": "DEPOSIT", "date": "2025-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}},
                        {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2025-01-02", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                        {"broker_id": broker_id, "asset_id": asset_id, "type": "SELL", "date": "2025-02-15", "quantity": "-10", "cash": {"code": "EUR", "amount": "1200"}},
                        {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2025-03-10", "quantity": "5", "cash": {"code": "EUR", "amount": "-600"}},
                        {"broker_id": broker_id, "type": "INTEREST", "date": "2025-02-20", "quantity": "0", "cash": {"code": "EUR", "amount": "20"}},
                        {"broker_id": broker_id, "type": "FEE", "date": "2025-02-21", "quantity": "0", "cash": {"code": "EUR", "amount": "-5"}},
                    ],
                )

                price_resp = await client.post(
                    f"{API_BASE}/assets/prices",
                    json=[
                        {
                            "asset_id": asset_id,
                            "prices": [
                                {
                                    "date": "2025-01-31",
                                    "close": "110.00",
                                    "currency": "EUR",
                                }
                            ],
                        }
                    ],
                    timeout=TIMEOUT,
                )
                assert price_resp.status_code == 200, f"Price upsert failed: {price_resp.status_code}: {price_resp.text}"

                resp = await post_portfolio_report(
                    client,
                    {
                        "include_history": False,
                        "include_allocation_history": False,
                        "include_positions_contribution": True,
                        "date_range": {"start": "2025-01-31", "end": "2025-02-28"},
                    },
                )
            finally:
                if broker_id is not None:
                    cleanup_broker = await client.delete(
                        f"{API_BASE}/brokers",
                        params={"ids": [broker_id], "force": True},
                        timeout=TIMEOUT,
                    )
                    assert cleanup_broker.status_code == 200, cleanup_broker.text
                    broker_results = {item["id"]: item for item in cleanup_broker.json()["results"]}
                    assert broker_results[broker_id]["success"] is True, cleanup_broker.text
                if asset_id is not None:
                    cleanup_asset = await client.delete(
                        f"{API_BASE}/assets",
                        params={"asset_ids": [asset_id]},
                        timeout=TIMEOUT,
                    )
                    assert cleanup_asset.status_code == 200, cleanup_asset.text
                    asset_results = {item["asset_id"]: item for item in cleanup_asset.json()["results"]}
                    assert asset_results[asset_id]["success"] is True, cleanup_asset.text
                await delete_current_test_user(client, user_id)

        assert resp.status_code == 200
        report = resp.json()
        assert report["summary"]["holdings"] == []

        positions = report["positions_contribution"]["positions"]
        assert len(positions) == 1
        row = positions[0]
        assert row["is_fully_sold"] is True
        assert row["start_value"].startswith("1100")
        assert row["end_value"].startswith("0")
        assert row["period_realized_gain_loss"].startswith("200")
        assert row["period_unrealized_delta"].startswith("-100")
        assert row["period_pnl"].startswith("100")

        effects = report["positions_contribution"]["other_effects"]
        assert sorted((item["category"], item["description"], Decimal(item["period_pnl"]), item["broker_id"]) for item in effects) == [
            ("Cost", "Unallocated costs", Decimal("-5"), broker_id),
            ("Income", "Unallocated income", Decimal("20"), broker_id),
        ]

        total_positions = sum(Decimal(item["period_pnl"]) for item in positions if item["period_pnl"] is not None)
        total_other = sum(Decimal(item["period_pnl"]) for item in effects)
        assert total_positions + total_other == Decimal(report["summary"]["period_pnl"]["amount"])
        print_success("Date-aware report contribution OK")

    async def test_report_income_history_flag_gates_section_and_reconciles_with_summary(self, test_server):
        """G1c wiring, exercised through the real HTTP endpoint (not the service
        method directly): include_income_history=false (the default) omits the
        section entirely; =true adds signed per-day DIVIDEND/INTEREST points whose
        sum reconciles exactly with summary.period_income for the same window.
        It owns and deletes its user, broker, asset and three transactions, broker first:
        its force delete removes the DIVIDEND that would otherwise block the asset delete."""
        print_section("Portfolio Report: income history flag + reconciliation")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            user_id = await get_current_user_id(client)
            broker_id: int | None = None
            asset_id: int | None = None
            try:
                broker_id = await create_broker(client)
                asset_id = await create_asset(client)  # DIVIDEND requires asset_id at the schema layer; INTEREST does not

                await commit_batch(
                    client,
                    creates=[
                        {"broker_id": broker_id, "type": "DEPOSIT", "date": "2025-07-01", "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}},
                        {"broker_id": broker_id, "asset_id": asset_id, "type": "DIVIDEND", "date": "2025-07-10", "quantity": "0", "cash": {"code": "EUR", "amount": "40"}},
                        {"broker_id": broker_id, "type": "INTEREST", "date": "2025-07-20", "quantity": "0", "cash": {"code": "EUR", "amount": "5"}},
                    ],
                )

                off_resp = await post_portfolio_report(client, {"include_income_history": False, "date_range": {"start": "2025-07-01", "end": "2025-07-31"}})
                assert off_resp.status_code == 200
                off_report = off_resp.json()
                assert off_report.get("income_history") is None
                assert "income_history" not in off_report["metadata"]["included_features"]

                on_resp = await post_portfolio_report(client, {"include_income_history": True, "date_range": {"start": "2025-07-01", "end": "2025-07-31"}})
                assert on_resp.status_code == 200
                on_report = on_resp.json()
            finally:
                if broker_id is not None:
                    cleanup_broker = await client.delete(
                        f"{API_BASE}/brokers",
                        params={"ids": [broker_id], "force": True},
                        timeout=TIMEOUT,
                    )
                    assert cleanup_broker.status_code == 200, cleanup_broker.text
                    broker_results = {item["id"]: item for item in cleanup_broker.json()["results"]}
                    assert broker_results[broker_id]["success"] is True, cleanup_broker.text
                if asset_id is not None:
                    cleanup_asset = await client.delete(
                        f"{API_BASE}/assets",
                        params={"asset_ids": [asset_id]},
                        timeout=TIMEOUT,
                    )
                    assert cleanup_asset.status_code == 200, cleanup_asset.text
                    asset_results = {item["asset_id"]: item for item in cleanup_asset.json()["results"]}
                    assert asset_results[asset_id]["success"] is True, cleanup_asset.text
                await delete_current_test_user(client, user_id)

        assert "income_history" in on_report["metadata"]["included_features"]
        points = on_report["income_history"]["points"]
        assert [p["date"] for p in points] == ["2025-07-10", "2025-07-20"]
        by_date = {p["date"]: p for p in points}
        assert Decimal(by_date["2025-07-10"]["dividend"]["amount"]) == Decimal("40")
        assert Decimal(by_date["2025-07-10"]["interest"]["amount"]) == Decimal("0")
        assert Decimal(by_date["2025-07-20"]["interest"]["amount"]) == Decimal("5")
        assert on_report["income_history"]["missing_fx_pairs"] == []

        total = sum((Decimal(p["dividend"]["amount"]) + Decimal(p["interest"]["amount"]) for p in points), Decimal("0"))
        assert total == Decimal("45"), f"40 + 5 = 45, got {total}"
        assert Decimal(on_report["summary"]["period_income"]["amount"]) == Decimal("45"), "must reconcile exactly with income_history's own sum"
        print_success("income_history flag + reconciliation OK")

    @pytest.mark.parametrize(
        ("flag", "section"),
        [
            pytest.param("include_broker_pnl_history", "broker_pnl_history", id="broker_pnl_history"),
            pytest.param("include_pnl_candles", "pnl_candles", id="pnl_candles"),
            pytest.param("include_income_history", "income_history", id="income_history"),
            pytest.param("include_cost_history", "cost_history", id="cost_history"),
            pytest.param("include_deposit_history", "deposit_history", id="deposit_history"),
            pytest.param("include_acquisition_funding", "acquisition_funding", id="acquisition_funding"),
        ],
    )
    async def test_report_one_chart_flag_includes_exactly_that_section(
        self,
        test_server,
        flag,
        section,
    ):
        """Exactly one chart-section flag returns exactly that section.

        included_features is compared as an exact list, not by membership: the request
        turns on exactly one section, so a missing name means the flag was dropped and
        any extra name means a view ran that nobody asked for.
        """
        print_section(f"Portfolio Report: only {flag}")
        broker_id: int | None = None

        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            user_id = await get_current_user_id(client)
            try:
                broker_id = await create_broker(client, f"Chart Flag Broker {uuid.uuid4().hex}")
                await commit_batch(
                    client,
                    creates=[
                        {"broker_id": broker_id, "type": "DEPOSIT", "date": "2025-07-01", "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}},
                        {"broker_id": broker_id, "type": "INTEREST", "date": "2025-07-20", "quantity": "0", "cash": {"code": "EUR", "amount": "5"}},
                    ],
                )

                # Every section flag is explicit, so "exactly one chart flag on" is stated
                # by the request itself instead of inferred from the schema defaults.
                body = {
                    "include_summary": False,
                    "include_history": False,
                    "include_allocation_history": False,
                    "include_positions_contribution": False,
                    "include_broker_pnl_history": False,
                    "include_pnl_candles": False,
                    "include_income_history": False,
                    "include_cost_history": False,
                    "include_deposit_history": False,
                    "include_acquisition_funding": False,
                    "date_range": {"start": "2025-07-01", "end": "2025-07-31"},
                }
                body[flag] = True
                response = await post_portfolio_report(client, body)
                assert response.status_code == 200, response.text
                report = response.json()

                assert report[section] is not None, f"{flag}=true was ignored: included_features={report['metadata']['included_features']}"
                assert report["metadata"]["included_features"] == [section]
                # data_quality is deliberately not pinned: the engine path builds it as a by-product.
                assert report["summary"] is None
                assert report["history"] is None
                assert report["allocation_history"] is None
                assert report["positions_contribution"] is None
            finally:
                if broker_id is not None:
                    cleanup_broker = await client.delete(
                        f"{API_BASE}/brokers",
                        params={"ids": [broker_id], "force": True},
                        timeout=TIMEOUT,
                    )
                    assert cleanup_broker.status_code == 200, cleanup_broker.text
                    broker_results = {item["id"]: item for item in cleanup_broker.json()["results"]}
                    assert broker_results[broker_id]["success"] is True, cleanup_broker.text
                await delete_current_test_user(client, user_id)

        print_success(f"{section} returned alone")


@pytest.mark.asyncio
class TestLotsAnalysisEndpoint:
    """POST /portfolio/lots/analysis — FifoLotEngine bulk multi-analysis endpoint."""

    @pytest.fixture(autouse=True)
    def _server(self, test_server):
        pass

    async def test_unauthenticated(self, test_server):
        """POST without auth → 401."""
        print_section("Lots Analysis: unauthenticated")
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{API_BASE}/portfolio/lots/analysis", json={"asset_id": 1, "requested_analyses": ["LOT_SUMMARY"]}, timeout=TIMEOUT)
        assert resp.status_code == 401
        print_success("401 as expected")

    async def test_requested_analyses_required_non_empty(self, test_server):
        """requested_analyses must be present and non-empty."""
        print_section("Lots Analysis: requested_analyses validation")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            asset_id = await create_asset(client)

            resp = await client.post(f"{API_BASE}/portfolio/lots/analysis", json={"asset_id": asset_id, "requested_analyses": []}, timeout=TIMEOUT)
            assert resp.status_code == 422

            resp = await client.post(f"{API_BASE}/portfolio/lots/analysis", json={"asset_id": asset_id}, timeout=TIMEOUT)
            assert resp.status_code == 422
        print_success("Empty/missing requested_analyses rejected")

    async def test_lot_summary_and_gantt_for_buy_sell(self, test_server):
        """BUY then partial SELL -> one lot, LOT_SUMMARY + GANTT_TOPOLOGY populated, other sections absent."""
        print_section("Lots Analysis: LOT_SUMMARY + GANTT_TOPOLOGY")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            asset_id = await create_asset(client)
            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-10", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "SELL", "date": "2026-02-01", "quantity": "-4", "cash": {"code": "EUR", "amount": "480"}},
                ],
            )

            resp = await client.post(
                f"{API_BASE}/portfolio/lots/analysis",
                json={"asset_id": asset_id, "requested_analyses": ["LOT_SUMMARY", "GANTT_TOPOLOGY"]},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()

            assert data["calculation_status"] == "COMPLETE"
            assert data["target_currency"] == "EUR"
            # quote_base_quantity is echoed so the frontend can rescale per-quote unit prices
            # (opening_unit_price) onto the per-unit price axis. Default asset => 1.
            assert data["quote_base_quantity"] == 1
            assert len(data["lots"]) == 1
            lot = data["lots"][0]
            assert lot["direction"] == "LONG"
            assert Decimal(lot["original_quantity"]) == Decimal("10")
            assert Decimal(lot["open_quantity"]) == Decimal("6")
            assert Decimal(lot["realized_quantity"]) == Decimal("4")
            assert Decimal(lot["opening_unit_price"]) == Decimal("100")
            assert "OPEN" not in lot["states"] or "PARTIALLY_CLOSED" in lot["states"]

            # A partial SELL closes the current custody interval and opens a new one at the
            # reduced quantity WITHOUT changing the fragment's logical identity (Fase 0.5
            # spec) -- so the same fragment_id legitimately appears twice: one CLOSED
            # historical slice (qty=10, before the sell) and one still-OPEN slice (qty=6).
            segments = data["gantt_segments"]
            assert len(segments) == 2
            assert all(segment["custody_type"] == "BROKER" for segment in segments)
            assert all(segment["fragment_id"] == segments[0]["fragment_id"] for segment in segments)
            open_segments = [s for s in segments if s["end_date"] is None]
            closed_segments = [s for s in segments if s["end_date"] is not None]
            assert len(open_segments) == 1
            assert len(closed_segments) == 1
            assert Decimal(open_segments[0]["quantity"]) == Decimal("6")
            assert Decimal(closed_segments[0]["quantity"]) == Decimal("10")

            # Sections not requested must be absent (None), matching the include_* pattern.
            assert data["custody_history"] is None
            assert data["value_history"] is None
            assert data["broker_wac_history"] is None
        print_success("LOT_SUMMARY + GANTT_TOPOLOGY correct, other sections omitted")

    async def test_target_currency_conversion(self, test_server):
        """BUY 1000 EUR of an EUR asset, then ask for its lots in EUR and in USD.

        target_currency is accepted and echoed, and in EUR the cost is the 1000 the BUY paid. In USD the cost is
        converted at the EUR/USD rate of the BUY date; without one it is unknown (B3b): null -- never the native
        1000 read as dollars -- with the pair and the BUY date in data_quality.missing_fx_pairs, and DEGRADED.

        Which case applies is read from the response itself, not assumed. FX rates are global and the FX service
        backward-fills without limit, so any EUR/USD row on or before the BUY date -- seeded, or written by a
        concurrent FX unit -- makes the pair convertible. An API test can own neither case: it cannot delete a
        neighbour's committed rate, and a rate it wrote would change every neighbour's EUR/USD conversion from
        that date on. The response states, in one answer, whether the rate was there and what was computed with
        it: each case is asserted strictly, and an answer that contradicts itself is red.
        """
        print_section("Lots Analysis: target_currency conversion")
        buy_date = "2026-01-10"
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            asset_id = await create_asset(client, currency="EUR")
            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": buy_date, "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                ],
            )

            resp_eur = await client.post(
                f"{API_BASE}/portfolio/lots/analysis",
                json={"asset_id": asset_id, "requested_analyses": ["LOT_SUMMARY"], "target_currency": "EUR"},
                timeout=TIMEOUT,
            )
            resp_usd = await client.post(
                f"{API_BASE}/portfolio/lots/analysis",
                json={"asset_id": asset_id, "requested_analyses": ["LOT_SUMMARY"], "target_currency": "USD"},
                timeout=TIMEOUT,
            )
        assert resp_eur.status_code == 200, resp_eur.text
        assert resp_usd.status_code == 200, resp_usd.text
        eur, usd = resp_eur.json(), resp_usd.json()
        # This test's own asset, bought once: exactly one lot in each answer.
        (eur_lot,) = eur["lots"]
        (usd_lot,) = usd["lots"]

        # Accepted and echoed; in EUR the cost is what the BUY paid; in USD the lot itself is unchanged.
        assert (eur["target_currency"], usd["target_currency"]) == ("EUR", "USD")
        assert Decimal(eur_lot["original_cost"]) == Decimal("1000")
        assert (usd_lot["currency"], Decimal(usd_lot["original_quantity"])) == ("EUR", Decimal("10"))

        assert usd["data_quality"] is not None
        missing_dates = {item["pair"]: item["dates"] for item in usd["data_quality"]["missing_fx_pairs"]}
        if buy_date in missing_dates.get("EUR/USD", []):
            # No EUR/USD rate on or before the BUY date: the USD cost and unit price are unknown, and the
            # answer says why -- the pair and that date above -- and that it is DEGRADED.
            assert (usd_lot["original_cost"], usd_lot["opening_unit_price"], usd["calculation_status"]) == (None, None, "DEGRADED")
            case = "no EUR/USD rate: USD cost null, pair and BUY date reported, DEGRADED"
        else:
            # A rate exists: nothing is missing, and the cost is a number, converted with the same rate as the
            # unit price (both at the BUY date).
            assert (usd["data_quality"]["missing_fx_pairs"], usd["calculation_status"]) == ([], "COMPLETE")
            assert usd_lot["original_cost"] is not None and usd_lot["opening_unit_price"] is not None
            assert Decimal(usd_lot["original_cost"]) == 10 * Decimal(usd_lot["opening_unit_price"]) > 0
            case = "EUR/USD rate present: USD cost converted, nothing missing"
        print_success(f"target_currency accepted and echoed; EUR cost matches the transaction; {case}")

    async def test_return_history_for_plain_buy_populates_total_and_open_return(self, test_server):
        """Plain BUY lots expose non-empty return_history with total_return + relative_return."""
        print_section("Lots Analysis: return history for plain BUY")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            asset_id = await create_asset(client, currency="EUR")
            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-10", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                ],
            )
            price_resp = await client.post(
                f"{API_BASE}/assets/prices",
                json=[
                    {
                        "asset_id": asset_id,
                        "prices": [
                            {"date": "2026-01-10", "close": "100.00", "currency": "EUR"},
                            {"date": "2026-01-11", "close": "110.00", "currency": "EUR"},
                        ],
                    }
                ],
                timeout=TIMEOUT,
            )
            assert price_resp.status_code == 200, f"Price upsert failed: {price_resp.status_code}: {price_resp.text}"

            resp = await client.post(
                f"{API_BASE}/portfolio/lots/analysis",
                json={"asset_id": asset_id, "requested_analyses": ["LOT_SUMMARY", "RETURN_HISTORY"], "date_range": {"end": "2026-01-11"}},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()

            assert data["return_history"] is not None
            assert len(data["return_history"]) == 2
            assert Decimal(data["return_history"][0]["total_return"]) == Decimal("0")
            assert Decimal(data["return_history"][1]["total_return"]) == Decimal("0.1")
            assert Decimal(data["return_history"][1]["relative_return"]) == Decimal("0.1")
            assert data["return_history"][1]["reference_price_source"] == "exact"
            assert Decimal(data["lots"][0]["relative_return"]) == Decimal("0.1")
        print_success("Plain BUY return history populated")

    async def test_performance_history_contract(self, test_server):
        """PERFORMANCE_HISTORY returns asset-wide ROI/TWRR payload."""
        print_section("Lots Analysis: performance history contract")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            asset_id = await create_asset(client, currency="EUR")
            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-10", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                ],
            )
            price_resp = await client.post(
                f"{API_BASE}/assets/prices",
                json=[
                    {
                        "asset_id": asset_id,
                        "prices": [
                            {"date": "2026-01-10", "close": "100.00", "currency": "EUR"},
                            {"date": "2026-01-11", "close": "110.00", "currency": "EUR"},
                        ],
                    }
                ],
                timeout=TIMEOUT,
            )
            assert price_resp.status_code == 200, f"Price upsert failed: {price_resp.status_code}: {price_resp.text}"

            resp = await client.post(
                f"{API_BASE}/portfolio/lots/analysis",
                json={"asset_id": asset_id, "requested_analyses": ["PERFORMANCE_HISTORY"], "date_range": {"end": "2026-01-11"}},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()

            # J5-5 (steps, contract MF-P4b §1.3): a row holds from `date` to `through`, and the answer carries the `range` the rows lie in.
            # 10 Jan (ROI 0, no TWRR yet) and 11 Jan (ROI and TWRR 0.1) are different figures, so they are two steps of one day each.
            assert data["range"] == {"start": "2026-01-10", "end": "2026-01-11"}
            assert data["performance_history"] is not None
            assert len(data["performance_history"]) == 2
            assert set(data["performance_history"][0]) == {"date", "through", "roi", "twrr"}
            assert [(row["date"], row["through"]) for row in data["performance_history"]] == [("2026-01-10", "2026-01-10"), ("2026-01-11", "2026-01-11")]
            assert Decimal(data["performance_history"][0]["roi"]) == Decimal("0")
            assert data["performance_history"][0]["twrr"] is None
            assert Decimal(data["performance_history"][1]["roi"]) == Decimal("0.1")
            assert Decimal(data["performance_history"][1]["twrr"]) == Decimal("0.1")
        print_success("PERFORMANCE_HISTORY contract OK")

    async def test_nonexistent_asset_rejected(self, test_server):
        """Non-existent asset_id -> 4xx, not a 500."""
        print_section("Lots Analysis: nonexistent asset")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            resp = await client.post(
                f"{API_BASE}/portfolio/lots/analysis",
                json={"asset_id": 999999, "requested_analyses": ["LOT_SUMMARY"]},
                timeout=TIMEOUT,
            )
            assert resp.status_code in (400, 404, 422)
        print_success(f"Nonexistent asset rejected with {resp.status_code}")

    async def test_market_price_history_continues_after_the_last_sale(self, test_server):
        """Y-30 (N89): MARKET_PRICE_HISTORY, the market price line independent of the lots, alone.

        An EUR asset never quoted: BUY 10 for 1000 EUR on 10 Jan 2026, SELL all 10 for 1100 EUR on 15 Jan, read up to
        20 Jan. 200, and ``market_price_history`` is a list with a point on every day from the BUY to ``date_to`` — after
        the sale too, when no lot is open: the BUY's 100 on 10–14 Jan, the SELL's 110 on 15–20 Jan, each in EUR and
        estimated (a trade's mark, no quote). Nothing else was asked for, so ``price_history`` and ``lots`` are null. EUR
        only: the API cannot own the absence of a rate, so no FX here (the gaps are in the service tests).

        Today: 422 — 'MARKET_PRICE_HISTORY' is not a valid LotAnalysisType.

        The test's own user, broker and asset, deleted at the end (the broker with its transactions).
        """
        print_section("Lots Analysis: MARKET_PRICE_HISTORY after the last sale")
        broker_id: int | None = None
        asset_id: int | None = None
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            user_id = await get_current_user_id(client)
            try:
                broker_id = await create_broker(client, f"Y30 Market Price {uuid.uuid4().hex}")
                asset_id = await create_asset(client, currency="EUR")
                await commit_batch(
                    client,
                    creates=[
                        {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                        {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-10", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                        {"broker_id": broker_id, "asset_id": asset_id, "type": "SELL", "date": "2026-01-15", "quantity": "-10", "cash": {"code": "EUR", "amount": "1100"}},
                    ],
                )

                resp = await client.post(
                    f"{API_BASE}/portfolio/lots/analysis",
                    json={"asset_id": asset_id, "requested_analyses": ["MARKET_PRICE_HISTORY"], "target_currency": "EUR", "date_range": {"end": "2026-01-20"}},
                    timeout=TIMEOUT,
                )
                assert resp.status_code == 200, resp.text
                data = resp.json()

                assert isinstance(data["market_price_history"], list), data
                # J5-5 (steps): the line is two steps, the BUY's mark held 10-14 Jan and the SELL's 15-20 Jan; the days a client reads
                # from them (`expand_steps`: each step repeated from `date` to `through`) are the ones the test has always named.
                assert data["range"] == {"start": "2026-01-10", "end": "2026-01-20"}
                assert [(step["date"], step["through"], Decimal(step["market_price"])) for step in data["market_price_history"]] == [("2026-01-10", "2026-01-14", Decimal("100")), ("2026-01-15", "2026-01-20", Decimal("110"))]
                line = [(point["date"], Decimal(point["market_price"]), point["currency"], point["estimated"]) for point in expand_steps(data["market_price_history"], None)]
                expected = [(f"2026-01-{day:02d}", Decimal("100"), "EUR", True) for day in range(10, 15)] + [(f"2026-01-{day:02d}", Decimal("110"), "EUR", True) for day in range(15, 21)]
                assert line == expected
                assert (data["price_history"], data["lots"]) == (None, None)
            finally:
                if broker_id is not None:
                    cleanup_broker = await client.delete(f"{API_BASE}/brokers", params={"ids": [broker_id], "force": True}, timeout=TIMEOUT)
                    assert cleanup_broker.status_code == 200, cleanup_broker.text
                    broker_results = {item["id"]: item for item in cleanup_broker.json()["results"]}
                    assert broker_results[broker_id]["success"] is True, cleanup_broker.text
                if asset_id is not None:
                    cleanup_asset = await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
                    assert cleanup_asset.status_code == 200, cleanup_asset.text
                    asset_results = {item["asset_id"]: item for item in cleanup_asset.json()["results"]}
                    assert asset_results[asset_id]["success"] is True, cleanup_asset.text
                await delete_current_test_user(client, user_id)
        print_success("MARKET_PRICE_HISTORY: a point a day from the BUY to date_to, after the sale too")


# ---------------------------------------------------------------------------
# Focused ASGI compatibility tests for planner source and WAC authorization
# ---------------------------------------------------------------------------


class _ApiScalars:
    def __init__(self, values):
        self._values = list(values)

    def __iter__(self):
        return iter(self._values)

    def all(self):
        return list(self._values)


class _ApiRows:
    def __init__(self, values):
        self._values = list(values)

    def scalars(self):
        return _ApiScalars(self._values)


class _WacApiSession:
    """Two-read WAC boundary: Broker access first, Asset identities second."""

    def __init__(
        self,
        *,
        broker_id: int,
        accessible: bool,
        access_role: UserRole | None = None,
        accessible_ids=None,
        assets=(),
    ):
        self.broker_id = broker_id
        self.accessible = accessible
        self.access_role = access_role
        self.accessible_ids = list(accessible_ids) if accessible_ids is not None else ([broker_id] if accessible else [])
        self.assets = list(assets)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        if len(self.statements) == 1:
            assert "broker_user_access.role" not in str(statement)
            return _ApiRows(self.accessible_ids)
        if len(self.statements) == 2:
            return _ApiRows(self.assets)
        raise AssertionError("WAC endpoint performed an unexpected read")


# ---------------------------------------------------------------------------
# TestPositionsSeriesEndpoint — POST /portfolio/positions-series (J5-1, #48)
# ---------------------------------------------------------------------------


async def post_positions_series(client: httpx.AsyncClient, body: dict) -> httpx.Response:
    return await client.post(f"{API_BASE}/portfolio/positions-series", json=body, timeout=TIMEOUT)


@pytest.mark.asyncio
class TestPositionsSeriesEndpoint:
    async def test_unauthenticated(self, test_server):
        """POST /portfolio/positions-series without auth -> 401."""
        print_section("Positions series: unauthenticated")
        async with httpx.AsyncClient() as client:
            resp = await post_positions_series(client, {"positions": [{"asset_id": 1}]})
        assert resp.status_code == 401

    async def test_the_positions_asked_for_are_required_and_capped(self, test_server):
        print_section("Positions series: validation")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            user_id = await get_current_user_id(client)
            try:
                empty = await post_positions_series(client, {"positions": []})
                too_many = await post_positions_series(client, {"positions": [{"asset_id": index} for index in range(1, 52)]})
                unknown_field = await post_positions_series(client, {"positions": [{"asset_id": 1}], "include_everything": True})
            finally:
                await delete_current_test_user(client, user_id)
        assert (empty.status_code, too_many.status_code, unknown_field.status_code) == (422, 422, 422)

    async def test_the_series_of_a_position_ends_where_the_reports_contribution_row_does(self, test_server):
        """One position bought and sold out: the series is steps (``date``..``through``) contiguous from the window's first day to the day it
        closed, the response carries the window as ``range``, and the last step's pnl is the report's ``period_pnl`` for the same position
        and window. It owns and deletes its user, broker, asset, three transactions and
        one price, broker first (as the report's date-aware test does)."""
        print_section("Positions series: end to end")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            user_id = await get_current_user_id(client)
            broker_id: int | None = None
            asset_id: int | None = None
            try:
                broker_id = await create_broker(client)
                asset_id = await create_asset(client)
                await commit_batch(
                    client,
                    creates=[
                        {"broker_id": broker_id, "type": "DEPOSIT", "date": "2025-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}},
                        {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2025-01-02", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                        {"broker_id": broker_id, "asset_id": asset_id, "type": "SELL", "date": "2025-02-15", "quantity": "-10", "cash": {"code": "EUR", "amount": "1200"}},
                    ],
                )
                price_resp = await client.post(f"{API_BASE}/assets/prices", json=[{"asset_id": asset_id, "prices": [{"date": "2025-01-31", "close": "110.00", "currency": "EUR"}]}], timeout=TIMEOUT)
                assert price_resp.status_code == 200, price_resp.text
                window = {"start": "2025-01-31", "end": "2025-02-28"}
                series_resp = await post_positions_series(client, {"date_range": window, "positions": [{"asset_id": asset_id, "broker_id": broker_id}]})
                report_resp = await post_portfolio_report(client, {"include_summary": False, "include_history": False, "include_allocation_history": False, "include_positions_contribution": True, "date_range": window})
            finally:
                if broker_id is not None:
                    cleanup_broker = await client.delete(f"{API_BASE}/brokers", params={"ids": [broker_id], "force": True}, timeout=TIMEOUT)
                    assert cleanup_broker.status_code == 200, cleanup_broker.text
                if asset_id is not None:
                    cleanup_asset = await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
                    assert cleanup_asset.status_code == 200, cleanup_asset.text
                await delete_current_test_user(client, user_id)

        assert series_resp.status_code == 200, series_resp.text
        body = series_resp.json()
        assert (body["currency"], body["date_from"], body["date_to"]) == ("EUR", "2025-01-31", "2025-02-28")
        assert body["range"] == {"start": "2025-01-31", "end": "2025-02-28"}
        [series] = body["series"]
        assert (series["first_date"], series["last_date"], series["closed_on"], series["held_at_start"], series["held_at_end"]) == ("2025-01-31", "2025-02-15", "2025-02-15", True, False)
        points = series["points"]
        # Contiguous steps from first_date to last_date (16 calendar days) with fewer steps than days; the last one is the day it closed.
        assert (points[0]["date"], points[-1]["through"]) == ("2025-01-31", "2025-02-15")
        for before, after in zip(points, points[1:], strict=False):
            assert date.fromisoformat(after["date"]) == date.fromisoformat(before["through"]) + timedelta(days=1)
        assert all(date.fromisoformat(point["date"]) <= date.fromisoformat(point["through"]) for point in points)
        assert sum((date.fromisoformat(point["through"]) - date.fromisoformat(point["date"])).days + 1 for point in points) == 16
        assert len(points) < 16
        [row] = report_resp.json()["positions_contribution"]["positions"]
        assert Decimal(points[-1]["pnl"]) == Decimal(row["period_pnl"])
        assert (points[-1]["quantity"], points[-1]["market_value"]) == ("0", "0")


def _focused_portfolio_app(
    *,
    current_user,
    session,
) -> FastAPI:
    app = FastAPI()
    app.include_router(portfolio_api.portfolio_router, prefix="/api/v1")

    async def override_session():
        yield session

    async def override_current_user():
        if current_user is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return current_user

    app.dependency_overrides[get_session_generator] = override_session
    app.dependency_overrides[get_current_user] = override_current_user
    if current_user is not None:
        app.dependency_overrides[portfolio_api._get_allocation_source_user] = override_current_user
    return app


def _planner_source_payload() -> dict[str, object]:
    return {
        "as_of": "2026-09-15",
        "target_currency": "EUR",
        "requested_sections": ["assets"],
        "broker_ids": [7],
        "asset_ids": [],
        "fx_pairs": [],
    }


def _empty_planner_source_response() -> PortfolioPlannerSourceResponse:
    return PortfolioPlannerSourceResponse(
        snapshot=PortfolioPlannerSourceSnapshot(
            as_of=date(2026, 9, 15),
            target_currency="EUR",
            generated_at=datetime(2026, 9, 15, 12, 30, tzinfo=UTC),
            requested_sections=["assets"],
            source_revision="1.0.0",
        ),
        provenance=[
            PortfolioPlannerSourceProvenance(
                provenance_id="source:portfolio-ledger",
                kind="domain_copy",
                domain="portfolio",
                source_ref="transactions+broker_user_access",
                source_label=None,
                captured_at=datetime(2026, 9, 15, 12, 30, tzinfo=UTC),
            )
        ],
        assets=[],
        brokers=[],
        holdings=[],
        cash_balances=[],
        prices=[],
        classifications=[],
        wac_contexts=[],
        fx_quotes=[],
        issues=[],
    )


@pytest.mark.asyncio
async def test_allocation_source_post_returns_typed_uncached_response(
    monkeypatch,
):
    expected = _empty_planner_source_response()
    builder = AsyncMock(return_value=expected)
    monkeypatch.setattr(
        portfolio_api,
        "build_portfolio_planner_source",
        builder,
    )
    session = object()
    app = _focused_portfolio_app(
        current_user=SimpleNamespace(id=41, is_superuser=False),
        session=session,
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/portfolio/allocation-source",
            json=_planner_source_payload(),
        )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.content == expected.model_dump_json().encode()
    builder.assert_awaited_once()
    assert builder.await_args.args == (session,)
    assert builder.await_args.kwargs["user_id"] == 41
    assert builder.await_args.kwargs["request"].model_dump(mode="json") == _planner_source_payload()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "status_code", "error_code"),
    [
        pytest.param(
            PortfolioPlannerSourceBrokerNotFoundError("missing"),
            403,
            "portfolio_planner_source_broker_forbidden",
            id="missing-broker-indistinguishable",
        ),
        pytest.param(
            PortfolioPlannerSourceAccessError("forbidden"),
            403,
            "portfolio_planner_source_broker_forbidden",
            id="unauthorized-broker",
        ),
        pytest.param(
            PortfolioPlannerSourceAssetNotFoundError("missing"),
            404,
            "portfolio_planner_source_asset_not_found",
            id="missing-asset",
        ),
    ],
)
async def test_allocation_source_maps_focused_domain_errors(
    monkeypatch,
    error,
    status_code,
    error_code,
):
    builder = AsyncMock(side_effect=error)
    monkeypatch.setattr(
        portfolio_api,
        "build_portfolio_planner_source",
        builder,
    )
    app = _focused_portfolio_app(
        current_user=SimpleNamespace(id=41, is_superuser=False),
        session=object(),
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/portfolio/allocation-source",
            json=_planner_source_payload(),
        )

    assert response.status_code == status_code
    assert response.json() == {
        "detail": {
            "code": error_code,
        }
    }
    assert response.headers.get("cache-control") == "no-store"


@pytest.mark.asyncio
async def test_allocation_source_anonymous_is_401_before_service(
    monkeypatch,
):
    builder = AsyncMock(side_effect=AssertionError("Anonymous request reached source service"))
    monkeypatch.setattr(
        portfolio_api,
        "build_portfolio_planner_source",
        builder,
    )
    app = _focused_portfolio_app(
        current_user=None,
        session=object(),
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/portfolio/allocation-source",
            json=_planner_source_payload(),
        )

    assert response.status_code == 401
    assert response.headers.get("cache-control") == "no-store"
    builder.assert_not_awaited()


@pytest.mark.asyncio
async def test_allocation_source_superuser_has_no_implicit_broker_bypass(
    monkeypatch,
):
    builder = AsyncMock(side_effect=PortfolioPlannerSourceAccessError("forbidden"))
    monkeypatch.setattr(
        portfolio_api,
        "build_portfolio_planner_source",
        builder,
    )
    app = _focused_portfolio_app(
        current_user=SimpleNamespace(id=91, is_superuser=True),
        session=object(),
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/portfolio/allocation-source",
            json=_planner_source_payload(),
        )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == ("portfolio_planner_source_broker_forbidden")
    assert response.headers.get("cache-control") == "no-store"
    assert builder.await_args.kwargs["user_id"] == 91


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        pytest.param(UserRole.VIEWER, id="viewer"),
        pytest.param(UserRole.EDITOR, id="editor"),
        pytest.param(UserRole.OWNER, id="owner"),
    ],
)
async def test_legacy_wac_allows_every_authenticated_broker_access_role(role):
    broker_id = 7
    session = _WacApiSession(
        broker_id=broker_id,
        accessible=True,
        access_role=role,
    )
    app = _focused_portfolio_app(
        current_user=SimpleNamespace(id=41, is_superuser=False),
        session=session,
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/portfolio/wac",
            json={
                "queries": [
                    {
                        "broker_id": broker_id,
                        "asset_id": 11,
                    }
                ]
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {
                "broker_id": broker_id,
                "asset_id": 11,
                "currency": "USD",
                "series": [],
                "missing_fx_pairs": [],
            }
        ]
    }
    assert len(session.statements) == 2
    assert session.access_role == role


@pytest.mark.asyncio
async def test_legacy_wac_superuser_without_access_is_403_before_asset_read():
    session = _WacApiSession(
        broker_id=7,
        accessible=False,
    )
    app = _focused_portfolio_app(
        current_user=SimpleNamespace(id=91, is_superuser=True),
        session=session,
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/portfolio/wac",
            json={
                "queries": [
                    {
                        "broker_id": 7,
                        "asset_id": 11,
                    }
                ]
            },
        )

    assert response.status_code == 403
    assert response.json() == {
        "detail": {
            "code": "portfolio_wac_broker_forbidden",
        }
    }
    assert len(session.statements) == 1


@pytest.mark.asyncio
async def test_legacy_wac_mixed_access_scope_fails_atomically_before_asset_read():
    session = _WacApiSession(
        broker_id=7,
        accessible=True,
        accessible_ids=[7],
    )
    app = _focused_portfolio_app(
        current_user=SimpleNamespace(id=41, is_superuser=False),
        session=session,
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/portfolio/wac",
            json={
                "queries": [
                    {
                        "broker_id": 7,
                        "asset_id": 11,
                    },
                    {
                        "broker_id": 99,
                        "asset_id": 12,
                    },
                ]
            },
        )

    assert response.status_code == 403
    assert response.json() == {
        "detail": {
            "code": "portfolio_wac_broker_forbidden",
        }
    }
    assert len(session.statements) == 1


@pytest.mark.asyncio
async def test_legacy_wac_anonymous_is_401_before_any_portfolio_read():
    session = _WacApiSession(
        broker_id=7,
        accessible=True,
    )
    app = _focused_portfolio_app(
        current_user=None,
        session=session,
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/portfolio/wac",
            json={
                "queries": [
                    {
                        "broker_id": 7,
                        "asset_id": 11,
                    }
                ]
            },
        )

    assert response.status_code == 401
    assert session.statements == []


@pytest.mark.asyncio
async def test_legacy_wac_response_remains_byte_and_semantically_compatible(
    monkeypatch,
):
    broker_id = 7
    asset_id = 11
    session = _WacApiSession(
        broker_id=broker_id,
        accessible=True,
        assets=[SimpleNamespace(id=asset_id, currency="EUR")],
    )
    compute = AsyncMock(
        return_value=WACPreviewResultItem(
            wac=Currency(code="EUR", amount=Decimal("12.3400")),
            wac_qualifying_txs=[
                WACQualifyingTX(
                    tx_id=101,
                    type="BUY",
                    date=date(2026, 1, 2),
                    quantity=Decimal("2.500"),
                    unit_cost=Decimal("12.3400"),
                    currency="EUR",
                    effect="add",
                    running_wac=Decimal("12.3400"),
                )
            ],
            wac_missing_pairs=[],
        )
    )
    monkeypatch.setattr(
        portfolio_api,
        "compute_wac_iterative",
        compute,
    )
    app = _focused_portfolio_app(
        current_user=SimpleNamespace(id=41, is_superuser=False),
        session=session,
    )
    expected = {
        "results": [
            {
                "broker_id": broker_id,
                "asset_id": asset_id,
                "currency": "EUR",
                "series": [
                    {
                        "date": "2026-01-02",
                        "wac": "12.3400",
                        "pool_qty": "2.500",
                        "effect": "add",
                    }
                ],
                "missing_fx_pairs": [],
            }
        ]
    }

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/portfolio/wac",
            json={
                "queries": [
                    {
                        "broker_id": broker_id,
                        "asset_id": asset_id,
                        "date_range": {
                            "end": "2026-01-31",
                        },
                    }
                ]
            },
        )

    assert response.status_code == 200
    assert response.json() == expected
    assert (
        response.content
        == json.dumps(
            expected,
            separators=(",", ":"),
        ).encode()
    )
    compute.assert_awaited_once_with(
        session=session,
        broker_id=broker_id,
        asset_id=asset_id,
        as_of_date=date(2026, 1, 31),
        asset_currency="EUR",
    )


# ---------------------------------------------------------------------------
# Planner source on the live test server (C0b.4): the copy endpoint end to end,
# and current_distribution parity with the Allocation page's summary. Every row
# is created by the test that reads it and deleted before it returns.
# ---------------------------------------------------------------------------

PLANNER_SOURCE_URL = f"{API_BASE}/portfolio/allocation-source"
PLANNER_AS_OF = "2025-06-30"
PLANNER_PRICE_DATE = "2025-06-27"
# Far above any id a test campaign creates: stands for "does not exist".
MISSING_PLANNER_ID = 987_654_321


def _live_planner_source_body(
    *,
    broker_ids: list[int],
    asset_ids: list[int] | None,
    requested_sections: list[str],
) -> dict[str, object]:
    return {
        "as_of": PLANNER_AS_OF,
        "target_currency": "EUR",
        "requested_sections": requested_sections,
        "broker_ids": broker_ids,
        "asset_ids": asset_ids,
        "fx_pairs": [],
    }


async def _delete_planner_rows(
    client: httpx.AsyncClient,
    *,
    broker_ids: list[int],
    asset_ids: list[int],
) -> None:
    """Brokers first (force cascades their transactions), then the Assets."""
    if broker_ids:
        resp = await client.delete(f"{API_BASE}/brokers", params={"ids": broker_ids, "force": True}, timeout=TIMEOUT)
        assert resp.status_code == 200, resp.text
        assert all(row["success"] for row in resp.json()["results"]), resp.text
    if asset_ids:
        resp = await client.delete(f"{API_BASE}/assets", params={"asset_ids": asset_ids}, timeout=TIMEOUT)
        assert resp.status_code == 200, resp.text
        assert all(row["success"] for row in resp.json()["results"]), resp.text


@pytest.mark.asyncio
async def test_planner_source_live_requires_authentication(test_server):
    print_section("Planner source (live): unauthenticated")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            PLANNER_SOURCE_URL,
            json=_live_planner_source_body(broker_ids=[MISSING_PLANNER_ID], asset_ids=[], requested_sections=["assets"]),
            timeout=TIMEOUT,
        )

    assert resp.status_code == 401
    assert resp.headers.get("cache-control") == "no-store"
    print_success("401 no-store before any read")


@pytest.mark.asyncio
async def test_planner_source_live_scope_errors_are_typed_and_uncached(test_server):
    print_section("Planner source (live): non-OWNER, missing Broker/Asset, null scenario")
    broker_ids: list[int] = []
    asset_ids: list[int] = []
    owner_id = viewer_id = None
    async with httpx.AsyncClient() as owner, httpx.AsyncClient() as viewer:
        try:
            await create_test_user(owner)
            owner_id = await get_current_user_id(owner)
            await create_test_user(viewer)
            viewer_id = await get_current_user_id(viewer)
            broker_id = await create_broker(owner, f"Planner scope {uuid.uuid4().hex[:12]}")
            broker_ids.append(broker_id)
            asset_id = await create_asset(owner)
            asset_ids.append(asset_id)
            share = await owner.put(
                f"{API_BASE}/brokers/{broker_id}/access",
                json=[
                    {"user_id": owner_id, "role": "OWNER", "share_percentage": 1},
                    {"user_id": viewer_id, "role": "VIEWER", "share_percentage": 0},
                ],
                timeout=TIMEOUT,
            )
            assert share.status_code == 200, share.text
            body = _live_planner_source_body(broker_ids=[broker_id], asset_ids=[asset_id], requested_sections=["current_distribution"])

            owner_resp = await owner.post(PLANNER_SOURCE_URL, json=body, timeout=TIMEOUT)
            viewer_resp = await viewer.post(PLANNER_SOURCE_URL, json=body, timeout=TIMEOUT)
            missing_broker_resp = await viewer.post(PLANNER_SOURCE_URL, json={**body, "broker_ids": [MISSING_PLANNER_ID]}, timeout=TIMEOUT)
            missing_asset_resp = await owner.post(PLANNER_SOURCE_URL, json={**body, "asset_ids": [asset_id, MISSING_PLANNER_ID]}, timeout=TIMEOUT)
            null_scenario_resp = await owner.post(PLANNER_SOURCE_URL, json={**body, "asset_ids": None}, timeout=TIMEOUT)
        finally:
            await _delete_planner_rows(owner, broker_ids=broker_ids, asset_ids=asset_ids)
            if viewer_id is not None:
                await delete_current_test_user(viewer, viewer_id)
            if owner_id is not None:
                await delete_current_test_user(owner, owner_id)

    # The same body is valid for the OWNER: the refusals below are about scope.
    assert owner_resp.status_code == 200, owner_resp.text
    assert owner_resp.headers.get("cache-control") == "no-store"
    assert owner_resp.json()["current_distribution"]["status"] == "no_holdings"
    for refused in (viewer_resp, missing_broker_resp):
        assert refused.status_code == 403, refused.text
        assert refused.json() == {"detail": {"code": "portfolio_planner_source_broker_forbidden"}}
        assert refused.headers.get("cache-control") == "no-store"
    assert missing_asset_resp.status_code == 404, missing_asset_resp.text
    assert missing_asset_resp.json() == {"detail": {"code": "portfolio_planner_source_asset_not_found"}}
    assert missing_asset_resp.headers.get("cache-control") == "no-store"
    # current_distribution weighs an explicit scenario: a null one is a request error.
    assert null_scenario_resp.status_code == 422, null_scenario_resp.text
    print_success("403/404 typed and no-store; null scenario is 422")


@pytest.mark.asyncio
async def test_planner_source_live_current_distribution_matches_the_allocation_summary(test_server):
    print_section("Planner source (live): current_distribution parity with the summary")
    broker_ids: list[int] = []
    asset_ids: list[int] = []
    user_id = None
    async with httpx.AsyncClient() as client:
        try:
            await create_test_user(client)
            user_id = await get_current_user_id(client)
            marker = uuid.uuid4().hex[:12]
            broker_ids.extend([await create_broker(client, f"Planner parity A {marker}"), await create_broker(client, f"Planner parity B {marker}")])
            asset_ids.extend([await create_asset(client) for _ in range(3)])
            first, second = broker_ids
            held_twice, single, small = asset_ids
            # (broker, asset, quantity, cash): one Asset is held at both Brokers.
            buys = (
                (first, held_twice, "3", "-300"),
                (second, held_twice, "2", "-200"),
                (first, single, "7", "-420"),
                (second, small, "11", "-99"),
            )
            await commit_batch(
                client,
                creates=[
                    *({"broker_id": broker, "type": "DEPOSIT", "date": "2025-01-02", "quantity": "0", "cash": {"code": "EUR", "amount": "5000"}} for broker in broker_ids),
                    *({"broker_id": broker, "asset_id": asset, "type": "BUY", "date": "2025-01-06", "quantity": quantity, "cash": {"code": "EUR", "amount": cash}} for broker, asset, quantity, cash in buys),
                ],
            )
            closes = {held_twice: "123.45", single: "67.89", small: "10.01"}
            price_resp = await client.post(
                f"{API_BASE}/assets/prices",
                json=[{"asset_id": asset, "prices": [{"date": PLANNER_PRICE_DATE, "close": close, "currency": "EUR"}]} for asset, close in closes.items()],
                timeout=TIMEOUT,
            )
            assert price_resp.status_code == 200, price_resp.text

            copy_resp = await client.post(
                PLANNER_SOURCE_URL,
                json=_live_planner_source_body(broker_ids=broker_ids, asset_ids=asset_ids, requested_sections=["current_distribution"]),
                timeout=TIMEOUT,
            )
            not_requested_resp = await client.post(
                PLANNER_SOURCE_URL,
                json=_live_planner_source_body(broker_ids=broker_ids, asset_ids=asset_ids, requested_sections=["assets"]),
                timeout=TIMEOUT,
            )
            report_resp = await post_portfolio_report(
                client,
                {
                    "broker_ids": broker_ids,
                    "date_range": {"end": PLANNER_AS_OF},
                    "target_currency": "EUR",
                    "include_summary": True,
                    "include_history": False,
                    "include_allocation_history": False,
                },
            )
        finally:
            await _delete_planner_rows(client, broker_ids=broker_ids, asset_ids=asset_ids)
            if user_id is not None:
                await delete_current_test_user(client, user_id)

    assert copy_resp.status_code == 200, copy_resp.text
    assert copy_resp.headers.get("cache-control") == "no-store"
    copy = copy_resp.json()
    assert "currency_specs" not in copy
    distribution = copy["current_distribution"]
    assert distribution["status"] == "complete"
    assert distribution["provenance_id"] == "source:portfolio-engine"
    assert "source:portfolio-engine" in {row["provenance_id"] for row in copy["provenance"]}
    rows = {row["asset_id"]: row for row in distribution["rows"]}
    assert set(rows) == {f"asset:{asset}" for asset in asset_ids}
    weights = {asset: Decimal(rows[f"asset:{asset}"]["weight"]) for asset in asset_ids}
    assert sum(weights.values()) == 1
    # 617.25 / 475.23 / 110.11 of 1202.59, floored to 0.0001, two units by largest remainder.
    assert weights == {held_twice: Decimal("0.5133"), single: Decimal("0.3952"), small: Decimal("0.0915")}
    for row in rows.values():
        assert row["held"] is True
        assert row["valuation_source"] == "MARKET_PRICE"
        assert row["valuation_reference_date"] == PLANNER_PRICE_DATE
        assert row["valuation_days_before_requested"] == 3

    assert report_resp.status_code == 200, report_resp.text
    holdings = report_resp.json()["summary"]["holdings"]
    # The scenario covers every holding of these Brokers, so both denominators agree.
    assert {holding["asset_id"] for holding in holdings} == set(asset_ids)
    page_share: dict[int, Decimal] = defaultdict(Decimal)
    page_rows: dict[int, int] = defaultdict(int)
    for holding in holdings:
        page_share[holding["asset_id"]] += Decimal(holding["allocation_percent"]) / 100
        page_rows[holding["asset_id"]] += 1
    assert page_rows[held_twice] == 2
    for asset in asset_ids:
        # Each page row is rounded to 0.01 % (0.0001); the copy adds one weight quantum.
        tolerance = Decimal("0.0001") * page_rows[asset] + Decimal("0.0001")
        assert abs(weights[asset] - page_share[asset]) <= tolerance, (asset, weights[asset], page_share[asset])

    assert not_requested_resp.status_code == 200, not_requested_resp.text
    not_requested = not_requested_resp.json()
    assert "current_distribution" in not_requested
    assert not_requested["current_distribution"] is None
    assert "currency_specs" not in not_requested
    print_success("current_distribution equals the summary's allocation_percent per Asset")


# ---------------------------------------------------------------------------
# Issue #32 — purchase cost in the report currency (workstream P, red-first)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestIssue32PurchaseCostInReportCurrency:
    """POST /portfolio/report on an asset quoted in UZS and bought three times with EUR.

    Issue #32 end to end: 100 + 150 + 150 EUR paid for 20 units. Reported in EUR the purchase
    cost is exactly 400 (each payment is already in the report currency); reported in UZS it is
    each payment at its own date's rate, 15000 + 21000 + 24000.

    Everything goes through the API: user, broker, a deposit, the asset, the three BUYs, the
    EUR/UZS rates (/fx/currencies/rate) and the prices (/assets/prices). Each test owns one
    calendar year of EUR/UZS rates. Before writing, it proves no EUR/UZS rate exists on or before
    the end of that year (a 404 from /fx/currencies/convert, which backward-fills without limit);
    every upsert must answer "inserted"; and exactly those rows are deleted again, after the
    broker (force: its transactions) and the asset (its prices, by cascade), and before the user.

    UZS rather than the ISK of the service tests: these rows are committed, and test_fx_core.py
    purges every committed rate quoted in ISK before each of its tests.
    """

    CURRENCY = "UZS"
    RATES = {"03-01": "150", "06-03": "140", "09-02": "160", "12-31": "125"}  # 1 EUR = rate UZS
    BUYS = (("03-01", "10", "-100"), ("06-03", "5", "-150"), ("09-02", "5", "-150"))
    PRICES = {"09-02": "3000", "12-31": "3125"}

    async def _report(self, *, year: int, target_currency: str) -> httpx.Response:
        """Seed the #32 history in ``year``, ask for the report in ``target_currency``, delete everything it wrote."""
        rate_days = sorted(f"{year}-{month_day}" for month_day in self.RATES)
        inserted_days: list[str] = []
        cleanup_errors: list[str] = []
        broker_id: int | None = None
        asset_id: int | None = None
        response: httpx.Response | None = None
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            user_id = await get_current_user_id(client)
            try:
                probe = await client.post(
                    f"{API_BASE}/fx/currencies/convert",
                    json=[{"from_amount": {"code": "EUR", "amount": "1"}, "to": self.CURRENCY, "date_range": {"start": f"{year}-12-31"}}],
                    timeout=TIMEOUT,
                )
                assert probe.status_code == 404, f"precondition broken: an EUR/{self.CURRENCY} rate exists on or before {year}-12-31 ({probe.status_code}: {probe.text})"

                upsert = await client.post(
                    f"{API_BASE}/fx/currencies/rate",
                    json=[{"date": f"{year}-{month_day}", "base": "EUR", "quote": self.CURRENCY, "rate": rate, "source": "MANUAL"} for month_day, rate in self.RATES.items()],
                    timeout=TIMEOUT,
                )
                assert upsert.status_code == 200, upsert.text
                inserted_days = sorted(row["date"] for row in upsert.json()["results"] if row["action"] == "inserted")
                assert inserted_days == rate_days, f"every EUR/{self.CURRENCY} row must be this test's own: {upsert.text}"

                broker_id = await create_broker(client, f"Issue32 {uuid.uuid4().hex[:12]}")
                asset_id = await create_asset(client, currency=self.CURRENCY)
                await commit_batch(
                    client,
                    creates=[
                        {"broker_id": broker_id, "type": "DEPOSIT", "date": f"{year}-02-01", "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}},
                        *({"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": f"{year}-{month_day}", "quantity": quantity, "cash": {"code": "EUR", "amount": paid}} for month_day, quantity, paid in self.BUYS),
                    ],
                )
                prices = await client.post(
                    f"{API_BASE}/assets/prices",
                    json=[{"asset_id": asset_id, "prices": [{"date": f"{year}-{month_day}", "close": close, "currency": self.CURRENCY} for month_day, close in self.PRICES.items()]}],
                    timeout=TIMEOUT,
                )
                assert prices.status_code == 200, prices.text

                response = await post_portfolio_report(
                    client,
                    {
                        "broker_ids": [broker_id],
                        "target_currency": target_currency,
                        "date_range": {"start": f"{year}-01-01", "end": f"{year}-12-31"},
                        "include_history": False,
                        "include_allocation_history": False,
                    },
                )
            finally:
                if broker_id is not None:
                    deleted = await client.delete(f"{API_BASE}/brokers", params={"ids": [broker_id], "force": True}, timeout=TIMEOUT)
                    if deleted.status_code != 200 or not all(row["success"] for row in deleted.json()["results"]):
                        cleanup_errors.append(f"broker {broker_id}: {deleted.status_code} {deleted.text}")
                if asset_id is not None:
                    deleted = await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
                    if deleted.status_code != 200 or not all(row["success"] for row in deleted.json()["results"]):
                        cleanup_errors.append(f"asset {asset_id}: {deleted.status_code} {deleted.text}")
                if inserted_days:
                    deleted = await client.request(
                        "DELETE",
                        f"{API_BASE}/fx/currencies/rate",
                        json=[{"from": "EUR", "to": self.CURRENCY, "date_range": {"start": day, "end": day}} for day in inserted_days],
                        timeout=TIMEOUT,
                    )
                    if deleted.status_code != 200 or deleted.json()["total_deleted"] != len(inserted_days):
                        cleanup_errors.append(f"EUR/{self.CURRENCY} rates {inserted_days}: {deleted.status_code} {deleted.text}")
                await delete_current_test_user(client, user_id)
        assert cleanup_errors == [], f"cleanup left rows behind: {cleanup_errors}"
        assert response is not None
        return response

    @staticmethod
    def _mentions(report: dict, currency: str) -> list[str]:
        """Every FX diagnostic of the report that names ``currency``: missing pairs and data-quality issues."""
        summary = report["summary"]
        found = [f"summary.missing_fx_pairs {item['pair']}" for item in summary["missing_fx_pairs"] if currency in item["pair"]]
        for where, quality in (("summary.data_quality", summary.get("data_quality")), ("data_quality", report.get("data_quality"))):
            if not quality:
                continue
            found += [f"{where}.missing_fx_pairs {item['pair']}" for item in quality["missing_fx_pairs"] if currency in item["pair"]]
            for issue in quality["issues"]:
                texts = [*issue["affected_fx_pairs"], *(str(value) for value in issue["message_params"].values())]
                found += [f"{where} issue {issue['code']}: {text}" for text in texts if currency in text]
        return found

    async def test_report_in_the_payment_currency_costs_exactly_what_was_paid(self, test_server):
        """RED before the fix: Dashboard in EUR → purchase cost 400 EUR (not 0), and no FX warning about UZS."""
        print_section("Portfolio Report: #32 purchase cost in EUR")
        response = await self._report(year=2019, target_currency="EUR")

        assert response.status_code == 200, response.text
        report = response.json()
        observed = {
            "open_cost_basis": Decimal(report["summary"]["open_cost_basis"]["amount"]),
            "FX diagnostics naming UZS": self._mentions(report, self.CURRENCY),
        }
        assert observed == {"open_cost_basis": Decimal("400"), "FX diagnostics naming UZS": []}
        print_success("400 EUR, as paid")

    async def test_report_in_the_asset_currency_is_unchanged(self, test_server):
        """GREEN before and after: the same history in UZS costs each payment at its own date's rate."""
        print_section("Portfolio Report: #32 purchase cost in UZS")
        response = await self._report(year=2018, target_currency=self.CURRENCY)

        assert response.status_code == 200, response.text
        assert Decimal(response.json()["summary"]["open_cost_basis"]["amount"]) == Decimal("60000")
        print_success("60000 UZS = 100×150 + 150×140 + 150×160")


# ---------------------------------------------------------------------------
# MF-SEC8-2a — transactions dated before 1900 in the report's data quality
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestTransactionsBeforeFloorDataQuality:
    """POST /portfolio/report warns once about the scope's transactions dated before 1 January 1900 (MF-SEC8-2a).

    The engine replays such a row on its own date but emits no state before ``EARLIEST_RANGE_START`` (1900-01-01), so the
    histories start there; ``data_quality`` says so with one WARNING ``TRANSACTIONS_BEFORE_FLOOR`` — ``count`` and
    ``message_params`` ``{count, earliest}``, no CTA. Proven on the HTTP pass-through, both ways it is built: with the
    summary (``get_summary``: ``summary.data_quality``, repeated as the top-level ``data_quality``) and without it
    (``get_report`` builds the top-level ``data_quality`` itself).

    The rows before 1900 are seeded with the ORM, in the lane's test database only: since N74 (R13-SEC7-3) the API refuses
    dates before 1900, so the warning exists for rows written before that rule.

    One new user, two new brokers, reported in EUR (the rows' currency: no rate is asked) on 1900 alone (the engine runs
    from the floor to the range's end). ``floor``: a DEPOSIT on 1900-01-01 through the API, then two DEPOSITs seeded on
    1899-12-15 and 1899-03-01 (the earliest written last). ``control``: only the API DEPOSIT on 1900-01-01 — the floor's
    own day, not before it — and no such issue. Cleanup: the seeded rows by id with the ORM, then both brokers (force:
    their API rows), then the user.

    Red before 871f75a38: ``IssueCode`` has no ``TRANSACTIONS_BEFORE_FLOOR``, so ``floor``'s three ``data_quality``
    sections hold no such issue; the barriers and the control are green there too.
    """

    FLOOR_DAY = "1900-01-01"
    SEEDED = ((date(1899, 12, 15), "500"), (date(1899, 3, 1), "250"))  # (day, EUR amount), in writing order
    WHERE = ("summary.data_quality", "data_quality with the summary", "data_quality without the summary")

    @staticmethod
    def _lane_engine():
        """The engine of the runner's test database, never another: the seeded rows bypass every API check."""
        is_test_db, database_url = verify_test_database()
        assert is_test_db, f"Refusing to write transactions outside the test database ({database_url})"
        engine = get_async_engine()
        assert engine.url.database and Path(engine.url.database).resolve() == get_test_db_path().resolve(), f"Refusing to write through a non-test engine ({engine.url})"
        return engine

    async def _seed_before_floor(self, broker_id: int, marker: str) -> list[int]:
        """Write ``SEEDED`` on ``broker_id`` — the dates the API refuses; their ids, once committed."""
        async with AsyncSession(self._lane_engine()) as session:
            rows = [Transaction(broker_id=broker_id, type=TransactionType.DEPOSIT, date=day, quantity=Decimal("0"), amount=Decimal(amount), currency="EUR", description=marker) for day, amount in self.SEEDED]
            session.add_all(rows)
            await session.flush()
            ids = [row.id for row in rows]
            await session.commit()
        return ids

    async def _delete_seeded(self, ids: list[int]) -> int:
        """Delete the seeded rows by id; how many went."""
        async with AsyncSession(self._lane_engine()) as session:
            result = await session.execute(delete(Transaction).where(Transaction.id.in_(ids)))
            deleted = result.rowcount
            await session.commit()
        return deleted

    async def _cleanup(self, client: httpx.AsyncClient, seeded_ids: list[int], broker_ids: list[int], cleanup_errors: list[str]) -> None:
        """The seeded rows first, then the brokers (force: their API rows). A failure is recorded, never raised, so the
        brokers and the user are still deleted."""
        if seeded_ids:
            try:
                deleted = await self._delete_seeded(seeded_ids)
            except Exception as exc:  # recorded: the test fails on it after the rest of the cleanup ran
                cleanup_errors.append(f"seeded rows {seeded_ids}: {exc!r}")
            else:
                if deleted != len(seeded_ids):
                    cleanup_errors.append(f"seeded rows {seeded_ids}: {deleted} deleted")
        if broker_ids:
            response = await client.delete(f"{API_BASE}/brokers", params={"ids": broker_ids, "force": True}, timeout=TIMEOUT)
            if response.status_code != 200 or not all(row["success"] for row in response.json()["results"]):
                cleanup_errors.append(f"brokers {broker_ids}: {response.status_code} {response.text}")

    async def _data_quality(self, client: httpx.AsyncClient, broker_id: int) -> dict[str, dict | None]:
        """The scope's ``data_quality`` sections, keyed as ``WHERE``: one report with the summary, one without."""
        found: dict[str, dict | None] = {}
        for include_summary in (True, False):
            response = await post_portfolio_report(
                client,
                {
                    "broker_ids": [broker_id],
                    "target_currency": "EUR",
                    "date_range": {"start": self.FLOOR_DAY, "end": "1900-12-31"},
                    "include_summary": include_summary,
                    "include_history": False,
                    "include_allocation_history": False,
                },
            )
            assert response.status_code == 200, response.text
            report = response.json()
            # Presence barrier: the scope's rows were replayed, from the floor (a scope read empty has no first day).
            assert report["metadata"]["computed_date_from"] == self.FLOOR_DAY, report["metadata"]
            if include_summary:
                found["summary.data_quality"] = report["summary"]["data_quality"]
                found["data_quality with the summary"] = report["data_quality"]
            else:
                assert report["summary"] is None, "include_summary=False built a summary: the report's own data_quality path is not reached"
                found["data_quality without the summary"] = report["data_quality"]
        return found

    @staticmethod
    def _floor_issues(quality: dict | None) -> list[dict] | None:
        """The ``TRANSACTIONS_BEFORE_FLOOR`` issues of a section, reduced to the contract's fields (None: no section)."""
        if quality is None:
            return None
        return [{key: issue[key] for key in ("severity", "count", "message_params", "cta_action", "cta_target")} for issue in quality["issues"] if issue["code"] == "TRANSACTIONS_BEFORE_FLOOR"]

    async def test_rows_before_1900_give_one_warning_on_the_summary_and_the_report(self, test_server):
        """RED before 871f75a38: the floor scope gets one TRANSACTIONS_BEFORE_FLOOR (2 rows, earliest 1899-03-01) in each
        section; the control scope, from 1900-01-01 on, none."""
        print_section("Portfolio Report: transactions before 1900 (MF-SEC8-2a)")
        marker = f"MF-SEC8-2a {uuid.uuid4().hex}"
        cleanup_errors: list[str] = []
        broker_ids: list[int] = []
        seeded_ids: list[int] = []
        floor_quality: dict[str, dict | None] = {}
        control_quality: dict[str, dict | None] = {}
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            user_id = await get_current_user_id(client)
            try:
                floor_id = await create_broker(client, f"Floor {uuid.uuid4().hex[:12]}")
                broker_ids.append(floor_id)
                control_id = await create_broker(client, f"Floor control {uuid.uuid4().hex[:12]}")
                broker_ids.append(control_id)
                await commit_batch(client, creates=[{"broker_id": broker_id, "type": "DEPOSIT", "date": self.FLOOR_DAY, "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}} for broker_id in broker_ids])
                seeded_ids = await self._seed_before_floor(floor_id, marker)

                floor_quality = await self._data_quality(client, floor_id)
                control_quality = await self._data_quality(client, control_id)
            finally:
                await self._cleanup(client, seeded_ids, broker_ids, cleanup_errors)
                await delete_current_test_user(client, user_id)
        assert cleanup_errors == [], f"cleanup left rows behind: {cleanup_errors}"

        earliest = min(day for day, _ in self.SEEDED).isoformat()
        expected = {"severity": "warning", "count": len(self.SEEDED), "message_params": {"count": len(self.SEEDED), "earliest": earliest}, "cta_action": None, "cta_target": None}
        assert {where: self._floor_issues(quality) for where, quality in floor_quality.items()} == {where: [expected] for where in self.WHERE}
        assert {where: self._floor_issues(quality) for where, quality in control_quality.items()} == {where: [] for where in self.WHERE}
        print_success(f"{len(self.SEEDED)} rows before 1900 (earliest {earliest}): one warning in every data_quality section; none from the floor on")


# ---------------------------------------------------------------------------
# E-19b2 — currencies stored as no ISO 4217 code, named in the report's data quality
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestNonIsoCurrencyDataQuality:
    """POST /portfolio/report names a currency of its scope stored as no ISO 4217 code, instead of asking for an FX pair
    that cannot exist (E-19b2).

    Since E-18 a write takes only ISO 4217 alphabetic codes; an older version stored a numeric code or a name as written.
    Every conversion such a code needs fails, and the report listed ``978/EUR`` as a MISSING_FX_MARKET ``978-EUR`` whose
    «Add FX pair» gets a 422. Now each such value is one WARNING ``NON_ISO_CURRENCY`` — key and params by what the value
    stands for (``978``: the suggestion EUR; the report's own currency: ``dataQuality.nonIsoReportCurrency``), the held
    assets stored in it by id and name, no CTA, no pair, group ``non_iso_currency:<value>`` — and no MISSING_FX_* issue
    names a pair with such a side, while the raw ``missing_fx_pairs`` keeps every pair. ``PortfolioService`` lists the held
    assets from the facts it already reads (``_non_iso_currency_assets``) and passes ``report_currency=base_currency``, at
    both report call sites: proven on the HTTP pass-through, both ways the report builds ``data_quality`` — with the
    summary (``summary.data_quality``, repeated as the top-level one) and without it —, as
    ``TestTransactionsBeforeFloorDataQuality`` does. The other rules of the issue are pinned without a server, in
    ``test_data_quality_report.py::TestNonIsoCurrencyIssue``.

    The stored codes are written with the ORM, in the lane's test database only and on rows the test owns: since E-18 the
    API refuses them (asset, transaction, settings). Each test: one new user, its own brokers and EUR assets, reported over
    2025. Cleanup undoes the ORM writes first (the seeded rows deleted by id, the asset's currency and the base currency put
    back to EUR), then the brokers (force: their API rows), the assets, the user.

    Red on HEAD 2fbbf4c4c: no section holds a ``NON_ISO_CURRENCY`` issue, and MISSING_FX_MARKET lists ``978-EUR``; the
    barriers and the control are green there too.
    """

    START, END = "2025-01-01", "2025-12-31"
    DEPOSIT_DAY, BUY_DAY = "2025-03-01", "2025-03-03"
    #: The day of the cash deposited in the stored code: inside the period, after the purchase.
    STORED_CASH_DAY = date(2025, 4, 1)
    #: EUR's numeric code, as an older version stored it.
    STORED = "978"
    WHERE = ("summary.data_quality", "data_quality with the summary", "data_quality without the summary")
    FIELDS = ("domain", "severity", "message_i18n_key", "message_params", "count", "affected_asset_ids", "affected_asset_names", "affected_fx_pairs", "cta_action", "cta_target", "group_key")

    @staticmethod
    def _lane_engine():
        """The engine of the runner's test database, never another: the seeded values bypass every API check."""
        is_test_db, database_url = verify_test_database()
        assert is_test_db, f"Refusing to write outside the test database ({database_url})"
        engine = get_async_engine()
        assert engine.url.database and Path(engine.url.database).resolve() == get_test_db_path().resolve(), f"Refusing to write through a non-test engine ({engine.url})"
        return engine

    async def _create_assets(self, client: httpx.AsyncClient, roles: tuple[str, ...], created_ids: list[int]) -> dict[str, tuple[int, str]]:
        """One EUR asset per role, in one request, found back by name: ``{role: (asset id, name)}``; every id created goes
        into ``created_ids`` first, for the cleanup."""
        marker = uuid.uuid4().hex
        names = {role: f"E-19b2 {role} {marker}" for role in roles}
        payload = [{"display_name": name, "currency": "EUR", "asset_type": "STOCK"} for name in names.values()]
        resp = await client.post(f"{API_BASE}/assets", json=payload, timeout=TIMEOUT)
        created = {row["display_name"]: row["asset_id"] for row in resp.json().get("results", []) if row.get("success")} if resp.status_code in (200, 201) else {}
        created_ids.extend(created.values())
        assert set(created) == set(names.values()), f"setup: every asset created: {resp.status_code} {resp.text}"
        return {role: (created[name], name) for role, name in names.items()}

    async def _buy(self, client: httpx.AsyncClient, broker_id: int, asset_id: int) -> None:
        """10 000 EUR deposited, then 10 of ``asset_id`` bought for 1 000 EUR: ISO codes, through the API."""
        await commit_batch(
            client,
            creates=[
                {"broker_id": broker_id, "type": "DEPOSIT", "date": self.DEPOSIT_DAY, "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": self.BUY_DAY, "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
            ],
        )

    async def _seed_stored_asset_and_cash(self, asset_id: int, broker_id: int, marker: str) -> list[int]:
        """The asset's currency set to ``978``, and 500 deposited in ``978`` on the broker, with the ORM, in one commit: as
        an older version could store them. The seeded row's id, once committed."""
        async with AsyncSession(self._lane_engine()) as session:
            written = await session.execute(update(Asset).where(Asset.id == asset_id).values(currency=self.STORED))
            assert written.rowcount == 1, f"setup: asset {asset_id}: {written.rowcount} row(s)"
            row = Transaction(broker_id=broker_id, type=TransactionType.DEPOSIT, date=self.STORED_CASH_DAY, quantity=Decimal("0"), amount=Decimal("500"), currency=self.STORED, description=marker)
            session.add(row)
            await session.flush()
            seeded = [row.id]
            await session.commit()
        return seeded

    async def _seed_base_currency(self, client: httpx.AsyncClient, user_id: int) -> None:
        """The user's base currency set to ``978`` with the ORM, as an older version could store it; the settings row is
        created first, through the API (its GET creates it)."""
        response = await client.get(f"{API_BASE}/settings/user", timeout=TIMEOUT)
        assert response.status_code == 200, f"setup: GET /settings/user: {response.status_code} {response.text}"
        async with AsyncSession(self._lane_engine()) as session:
            written = await session.execute(update(UserSettings).where(UserSettings.user_id == user_id).values(base_currency=self.STORED))
            assert written.rowcount == 1, f"setup: user {user_id} has {written.rowcount} settings row(s)"
            await session.commit()

    async def _data_quality(self, client: httpx.AsyncClient, broker_ids: list[int], target_currency: str | None, held: set[int], reported_in: str) -> dict[str, dict | None]:
        """The scope's ``data_quality`` sections, keyed as ``WHERE``: one report with the summary, one without. Without a
        ``target_currency`` the report converts to the user's base currency."""
        found: dict[str, dict | None] = {}
        for include_summary in (True, False):
            body = {"broker_ids": broker_ids, "date_range": {"start": self.START, "end": self.END}, "include_summary": include_summary, "include_history": False, "include_allocation_history": False}
            if target_currency is not None:
                body["target_currency"] = target_currency
            response = await post_portfolio_report(client, body)
            assert response.status_code == 200, response.text
            report = response.json()
            # Presence barriers: the engine ran to the period's end, in the currency meant, and the summary holds exactly the assets held there.
            assert (report["metadata"]["computed_date_to"], report["metadata"]["target_currency"]) == (self.END, reported_in), report["metadata"]
            if include_summary:
                assert {holding["asset_id"] for holding in report["summary"]["holdings"]} == held, report["summary"]["holdings"]
                found["summary.data_quality"] = report["summary"]["data_quality"]
                found["data_quality with the summary"] = report["data_quality"]
            else:
                assert report["summary"] is None, "include_summary=False built a summary: the report's own data_quality path is not reached"
                found["data_quality without the summary"] = report["data_quality"]
        return found

    def _non_iso_issues(self, quality: dict | None) -> list[dict] | None:
        """The ``NON_ISO_CURRENCY`` issues of a section, reduced to the contract's fields (None: no section)."""
        if quality is None:
            return None
        return [{field: issue.get(field) for field in self.FIELDS} for issue in quality["issues"] if issue["code"] == "NON_ISO_CURRENCY"]

    @staticmethod
    def _fx_issues_naming(quality: dict | None, value: str) -> list[tuple[str, str]] | None:
        """(code, slug) of every pair a MISSING_FX_* issue of a section lists or targets with ``value`` as a side (None: no
        section)."""
        if quality is None:
            return None
        named: list[tuple[str, str]] = []
        for issue in quality["issues"]:
            if issue["code"] not in ("MISSING_FX_MARKET", "MISSING_FX_RATES"):
                continue
            for slug in [*issue["affected_fx_pairs"], *([issue["cta_target"]] if issue["cta_target"] else [])]:
                if value in slug.replace("/", "-").split("-"):
                    named.append((issue["code"], slug))
        return named

    @staticmethod
    def _raw_pairs_naming(quality: dict | None, value: str) -> list[str] | None:
        """The raw ``missing_fx_pairs`` of a section (``FROM/TO``, the codes as stored) with ``value`` as a side (None: no
        section)."""
        if quality is None:
            return None
        return [item["pair"] for item in quality["missing_fx_pairs"] if value in item["pair"].split("/")]

    async def _undo_orm_writes(self, seeded_ids: list[int], stored_asset_ids: list[int], settings_user_id: int | None, cleanup_errors: list[str]) -> None:
        """The seeded rows deleted by id, the asset's currency and the base currency put back to EUR, in one commit. A
        failure is recorded, never raised."""
        try:
            async with AsyncSession(self._lane_engine()) as session:
                if seeded_ids:
                    deleted = (await session.execute(delete(Transaction).where(Transaction.id.in_(seeded_ids)))).rowcount
                    if deleted != len(seeded_ids):
                        cleanup_errors.append(f"seeded rows {seeded_ids}: {deleted} deleted")
                if stored_asset_ids:
                    await session.execute(update(Asset).where(Asset.id.in_(stored_asset_ids)).values(currency="EUR"))
                if settings_user_id is not None:
                    await session.execute(update(UserSettings).where(UserSettings.user_id == settings_user_id).values(base_currency="EUR"))
                await session.commit()
        except Exception as exc:  # recorded: the test fails on it after the rest of the cleanup ran
            cleanup_errors.append(f"ORM writes (rows {seeded_ids}, assets {stored_asset_ids}, settings of user {settings_user_id}): {exc!r}")

    async def _cleanup(self, client: httpx.AsyncClient, seeded_ids: list[int], stored_asset_ids: list[int], settings_user_id: int | None, broker_ids: list[int], asset_ids: list[int], cleanup_errors: list[str]) -> None:
        """The ORM writes undone first, then the brokers (force: their API rows), then the assets. A failure is recorded,
        never raised, so the rest, and the user, still go."""
        if seeded_ids or stored_asset_ids or settings_user_id is not None:
            await self._undo_orm_writes(seeded_ids, stored_asset_ids, settings_user_id, cleanup_errors)
        if broker_ids:
            response = await client.delete(f"{API_BASE}/brokers", params={"ids": broker_ids, "force": True}, timeout=TIMEOUT)
            if response.status_code != 200 or not all(row["success"] for row in response.json()["results"]):
                cleanup_errors.append(f"brokers {broker_ids}: {response.status_code} {response.text}")
        if asset_ids:
            response = await client.delete(f"{API_BASE}/assets", params={"asset_ids": asset_ids}, timeout=TIMEOUT)
            if response.status_code != 200 or not all(row["success"] for row in response.json()["results"]):
                cleanup_errors.append(f"assets {asset_ids}: {response.status_code} {response.text}")

    async def test_a_held_asset_and_cash_stored_in_978_give_one_warning_and_no_fx_pair(self, test_server):
        """RED until E-19b2: the ``stored`` scope, reported in EUR — its held asset's currency stored as 978, and 500
        deposited in 978 — gets in each data_quality section one NON_ISO_CURRENCY for 978: the suggestion EUR, the asset by
        id and name, count 1, no CTA, no pair; and no MISSING_FX_* issue names 978, while the raw ``missing_fx_pairs`` does
        (the barrier: those conversions did fail). The ``control`` scope, ISO codes only, gets none."""
        print_section("Portfolio Report: a held asset and cash stored in 978 (E-19b2)")
        marker = f"E-19b2 {uuid.uuid4().hex}"
        cleanup_errors: list[str] = []
        broker_ids: list[int] = []
        asset_ids: list[int] = []
        stored_asset_ids: list[int] = []
        seeded_ids: list[int] = []
        assets: dict[str, tuple[int, str]] = {}
        stored_quality: dict[str, dict | None] = {}
        control_quality: dict[str, dict | None] = {}
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            user_id = await get_current_user_id(client)
            try:
                assets = await self._create_assets(client, ("stored", "control"), asset_ids)
                for role in ("stored", "control"):
                    broker_id = await create_broker(client, f"E-19b2 {role} {uuid.uuid4().hex[:12]}")
                    broker_ids.append(broker_id)
                    await self._buy(client, broker_id, assets[role][0])
                stored_broker_id, control_broker_id = broker_ids
                stored_asset_ids.append(assets["stored"][0])
                seeded_ids.extend(await self._seed_stored_asset_and_cash(assets["stored"][0], stored_broker_id, marker))

                stored_quality = await self._data_quality(client, [stored_broker_id], "EUR", {assets["stored"][0]}, "EUR")
                control_quality = await self._data_quality(client, [control_broker_id], "EUR", {assets["control"][0]}, "EUR")
            finally:
                await self._cleanup(client, seeded_ids, stored_asset_ids, None, broker_ids, asset_ids, cleanup_errors)
                await delete_current_test_user(client, user_id)
        assert cleanup_errors == [], f"cleanup left rows behind: {cleanup_errors}"

        # Barrier: the scope's conversions from 978 did fail, so each section's raw list names the code the issues must not ask for.
        assert {where: bool(self._raw_pairs_naming(quality, self.STORED)) for where, quality in stored_quality.items()} == dict.fromkeys(self.WHERE, True), {where: quality and quality["missing_fx_pairs"] for where, quality in stored_quality.items()}
        stored_id, stored_name = assets["stored"]
        expected = {
            "domain": "portfolio",
            "severity": "warning",
            "message_i18n_key": "dataQuality.nonIsoCurrencySuggestion",
            "message_params": {"value": self.STORED, "suggestion": "EUR"},
            "count": 1,
            "affected_asset_ids": [stored_id],
            "affected_asset_names": [stored_name],
            "affected_fx_pairs": [],
            "cta_action": None,
            "cta_target": None,
            "group_key": f"non_iso_currency:{self.STORED}",
        }
        assert {where: self._non_iso_issues(quality) for where, quality in stored_quality.items()} == {where: [expected] for where in self.WHERE}
        assert {where: self._fx_issues_naming(quality, self.STORED) for where, quality in stored_quality.items()} == {where: [] for where in self.WHERE}
        assert {where: self._non_iso_issues(quality) for where, quality in control_quality.items()} == {where: [] for where in self.WHERE}
        print_success("A held asset and cash stored in 978: one NON_ISO_CURRENCY naming 978 with the asset in every data_quality section, no FX pair asked for; none for the control")

    async def test_a_base_currency_stored_as_978_gives_the_report_currency_warning(self, test_server):
        """RED until E-19b2: the user's base currency stored as 978, a report without ``target_currency`` converts to 978 —
        every conversion of the scope's EUR into it fails — and each data_quality section gets one NON_ISO_CURRENCY for 978
        with the report currency's key, ``dataQuality.nonIsoReportCurrency``, and the suggestion EUR: no asset (the one held
        is in EUR), count None. No MISSING_FX_* issue names 978, while the raw ``missing_fx_pairs`` does (the barrier):
        ``report_currency`` reaches both call sites."""
        print_section("Portfolio Report: a base currency stored as 978 (E-19b2)")
        cleanup_errors: list[str] = []
        broker_ids: list[int] = []
        asset_ids: list[int] = []
        settings_user_id: int | None = None
        quality_by_where: dict[str, dict | None] = {}
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            user_id = await get_current_user_id(client)
            try:
                assets = await self._create_assets(client, ("euro",), asset_ids)
                broker_id = await create_broker(client, f"E-19b2 base {uuid.uuid4().hex[:12]}")
                broker_ids.append(broker_id)
                await self._buy(client, broker_id, assets["euro"][0])
                settings_user_id = user_id
                await self._seed_base_currency(client, user_id)

                quality_by_where = await self._data_quality(client, [broker_id], None, {assets["euro"][0]}, self.STORED)
            finally:
                await self._cleanup(client, [], [], settings_user_id, broker_ids, asset_ids, cleanup_errors)
                await delete_current_test_user(client, user_id)
        assert cleanup_errors == [], f"cleanup left rows behind: {cleanup_errors}"

        # Barrier: every conversion into 978 did fail, so each section's raw list names the code the issues must not ask for.
        assert {where: bool(self._raw_pairs_naming(quality, self.STORED)) for where, quality in quality_by_where.items()} == dict.fromkeys(self.WHERE, True), {where: quality and quality["missing_fx_pairs"] for where, quality in quality_by_where.items()}
        expected = {
            "domain": "portfolio",
            "severity": "warning",
            "message_i18n_key": "dataQuality.nonIsoReportCurrency",
            "message_params": {"value": self.STORED, "suggestion": "EUR"},
            "count": None,
            "affected_asset_ids": [],
            "affected_asset_names": [],
            "affected_fx_pairs": [],
            "cta_action": None,
            "cta_target": None,
            "group_key": f"non_iso_currency:{self.STORED}",
        }
        assert {where: self._non_iso_issues(quality) for where, quality in quality_by_where.items()} == {where: [expected] for where in self.WHERE}
        assert {where: self._fx_issues_naming(quality, self.STORED) for where, quality in quality_by_where.items()} == {where: [] for where in self.WHERE}
        print_success("A base currency stored as 978: one NON_ISO_CURRENCY with the report currency's key in every data_quality section, no FX pair asked for")
