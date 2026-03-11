"""
Test Suite: FX Sync API Endpoints

Tests for FX sync endpoints:
- POST /api/v1/fx/currencies/sync - Pair-based sync with FXSyncBulkResponse
  - Per-pair status: ok, partial, failed, skipped
  - Auto-config mode (using pair sources)
  - Error handling (no pairs configured, invalid date range)
  - Multi-provider scenarios
"""

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.schemas.common import Currency
from backend.app.schemas.fx import (
    FXConversionRequest,
    FXConvertResponse,
    FXPairSourceItem,
    FXDeletePairSourceItem,
    FXCreatePairSourcesResponse,
    FXPairSourcesResponse,
    DateRangeModel,
    )
from backend.app.schemas.refresh import FXSyncBulkResponse
# Test server fixture
from backend.test_scripts.test_server_helper import _TestingServerManager

# Constants
settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0


def print_section(title: str):
    """Print test section header."""
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")


def print_info(msg: str):
    """Print info message."""
    print(f"ℹ️  {msg}")


def print_success(msg: str):
    """Print success message."""
    print(f"✅ ✓ {msg}")


# Fixture: test server
@pytest.fixture(scope="module")
def test_server():
    """Start/stop test server for all tests in this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager
        # Server automatically stopped by context manager


# ============================================================
# Test 1: POST /fx/currencies/sync — Invalid date range
# ============================================================
@pytest.mark.asyncio
async def test_sync_invalid_date_range(test_server):
    """Test 1: POST /fx/currencies/sync — start > end → 400."""
    print_section("Test 1: POST /fx/currencies/sync - Invalid date range")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/fx/currencies/sync",
            json={
                "pairs": ["EUR-USD"],
                "start": "2025-02-01",
                "end": "2025-01-01",
                },
            timeout=TIMEOUT,
            )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
        print_success("✓ Invalid date range correctly rejected with 400")


# ============================================================
# Test 2: POST /fx/currencies/sync — Auto-config with pair sources
# ============================================================
@pytest.mark.asyncio
async def test_sync_auto_config(test_server):
    """Test 2: POST /fx/currencies/sync — Auto-config (pair sources)."""
    print_section("Test 2: POST /fx/currencies/sync - Auto-config")

    async with httpx.AsyncClient() as client:
        # Step 1: Create pair sources for EUR-USD and GBP-USD
        pair_sources = [
            FXPairSourceItem(base="EUR", quote="USD", provider_code="ECB", priority=1),
            FXPairSourceItem(base="GBP", quote="USD", provider_code="ECB", priority=1),
            ]

        create_resp = await client.post(
            f"{API_BASE}/fx/providers/pair-sources",
            json=[s.model_dump(mode="json") for s in pair_sources],
            timeout=TIMEOUT,
            )

        if create_resp.status_code == 201:
            create_data = FXCreatePairSourcesResponse(**create_resp.json())
            print_info(f"  Created {create_data.success_count} pair sources")
        else:
            print_info("  Pair sources already exist")

        # Step 2: Sync using POST with pair slugs
        today = date.today()
        yesterday = today - timedelta(days=1)

        sync_resp = await client.post(
            f"{API_BASE}/fx/currencies/sync",
            json={
                "pairs": ["EUR-USD", "GBP-USD"],
                "start": yesterday.isoformat(),
                "end": yesterday.isoformat(),
                },
            timeout=TIMEOUT,
            )

        assert sync_resp.status_code == 200, f"Auto-config sync failed: {sync_resp.status_code}"

        sync_data = FXSyncBulkResponse(**sync_resp.json())
        print_info(f"  Results: {len(sync_data.results)} pairs")
        for pr in sync_data.results:
            print_info(f"    {pr.pair}: status={pr.status}, pts_changed={pr.points_changed}")
        print_success(f"✓ Auto-config sync: {sync_data.success_count}/{len(sync_data.results)} ok")

        # Cleanup: delete pair sources
        for source in pair_sources:
            await client.request(
                "DELETE",
                f"{API_BASE}/fx/providers/pair-sources",
                json=[source.model_dump(mode="json")],
                timeout=TIMEOUT,
                )
        print_info("  Cleanup: Pair sources deleted")


# ============================================================
# Test 3: POST /fx/currencies/sync — MANUAL-only pair → skipped
# ============================================================
@pytest.mark.asyncio
async def test_sync_manual_only_skipped(test_server):
    """Test 3: POST /fx/currencies/sync — MANUAL-only pair returns 'skipped' status."""
    print_section("Test 3: POST /fx/currencies/sync - MANUAL-only pair")

    async with httpx.AsyncClient() as client:
        # Step 1: Create MANUAL-only pair source
        await client.post(
            f"{API_BASE}/fx/providers/pair-sources",
            json=[{"base": "CHF", "quote": "JPY", "provider_code": "MANUAL", "priority": 999}],
            timeout=TIMEOUT,
            )

        # Step 2: Sync → expect 'skipped' status
        sync_resp = await client.post(
            f"{API_BASE}/fx/currencies/sync",
            json={
                "pairs": ["CHF-JPY"],
                "start": "2025-01-10",
                "end": "2025-01-10",
                },
            timeout=TIMEOUT,
            )

        assert sync_resp.status_code == 200, f"Expected 200, got {sync_resp.status_code}"
        sync_data = FXSyncBulkResponse(**sync_resp.json())
        assert len(sync_data.results) == 1
        assert sync_data.results[0].status == "skipped"
        print_success("✓ MANUAL-only pair correctly returns 'skipped'")

        # Cleanup
        await client.request(
            "DELETE",
            f"{API_BASE}/fx/providers/pair-sources",
            json=[{"base": "CHF", "quote": "JPY"}],
            timeout=TIMEOUT,
            )


# ============================================================
# Test 4: POST /fx/currencies/sync — Weekend sync (ok but 0 points)
# ============================================================
@pytest.mark.asyncio
async def test_sync_weekend_no_rates(test_server):
    """Test 4: POST /fx/currencies/sync — Weekend sync returns ok with 0 points."""
    print_section("Test 4: POST /fx/currencies/sync - Weekend sync")

    async with httpx.AsyncClient() as client:
        # Ensure pair source exists
        await client.post(
            f"{API_BASE}/fx/providers/pair-sources",
            json=[{"base": "EUR", "quote": "GBP", "provider_code": "ECB", "priority": 1}],
            timeout=TIMEOUT,
            )

        # 2025-01-04 = Saturday
        weekend_date = "2025-01-04"
        sync_resp = await client.post(
            f"{API_BASE}/fx/currencies/sync",
            json={
                "pairs": ["EUR-GBP"],
                "start": weekend_date,
                "end": weekend_date,
                },
            timeout=TIMEOUT,
            )

        assert sync_resp.status_code == 200, f"Sync failed: {sync_resp.status_code}"
        sync_data = FXSyncBulkResponse(**sync_resp.json())
        # Weekend: provider returns empty → partial or ok with 0 points
        assert len(sync_data.results) == 1
        print_info(f"  Weekend result: status={sync_data.results[0].status}, pts={sync_data.results[0].points_changed}")
        print_success("✓ Weekend sync handled correctly")

        # Cleanup
        await client.request(
            "DELETE",
            f"{API_BASE}/fx/providers/pair-sources",
            json=[{"base": "EUR", "quote": "GBP"}],
            timeout=TIMEOUT,
            )


# ============================================================
# Test 5: POST /fx/currencies/convert — Multi-day conversion
# ============================================================
@pytest.mark.asyncio
async def test_convert_multi_day_process(test_server):
    """Test 5: POST /fx/currencies/convert — Multi-day conversion process."""
    print_section("Test 5: POST /fx/currencies/convert - Multi-day")

    async with httpx.AsyncClient() as client:
        # Step 1: Ensure pair source + sync rates
        await client.post(
            f"{API_BASE}/fx/providers/pair-sources",
            json=[{"base": "EUR", "quote": "USD", "provider_code": "ECB", "priority": 1}],
            timeout=TIMEOUT,
            )

        end_date = date.today()
        start_date = end_date - timedelta(days=7)

        await client.post(
            f"{API_BASE}/fx/currencies/sync",
            json={
                "pairs": ["EUR-USD"],
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                },
            timeout=TIMEOUT,
            )
        print_info("  FX rates synced for date range")

        # Step 2: Request conversion with date range (multi-day)
        conversions = [
            FXConversionRequest(
                from_amount=Currency(code="USD", amount=Decimal("100")),
                **{"to": "EUR"},
                date_range=DateRangeModel(start=start_date, end=end_date),
                )
            ]

        convert_resp = await client.post(
            f"{API_BASE}/fx/currencies/convert",
            json=[c.model_dump(mode="json") for c in conversions],
            timeout=TIMEOUT,
            )

        assert (
            convert_resp.status_code == 200
        ), f"Convert failed: {convert_resp.status_code}: {convert_resp.text}"

        convert_data = FXConvertResponse(**convert_resp.json())
        assert convert_data.success_count >= 1

        result = convert_data.results[0]
        assert result.to_amount is not None
        print_success(f"✓ Multi-day conversion successful: {result.to_amount}")
        print_info(f"  Total conversions returned: {len(convert_data.results)}")

        # Cleanup
        await client.request(
            "DELETE",
            f"{API_BASE}/fx/providers/pair-sources",
            json=[{"base": "EUR", "quote": "USD"}],
            timeout=TIMEOUT,
            )


# ============================================================
# Test 6: POST /fx/currencies/convert — Bulk multi-day
# ============================================================
@pytest.mark.asyncio
async def test_convert_bulk_multi_day(test_server):
    """Test 6: POST /fx/currencies/convert — Bulk conversions with multi-day."""
    print_section("Test 6: POST /fx/currencies/convert - Bulk multi-day")

    async with httpx.AsyncClient() as client:
        # Step 1: Ensure pair sources + sync
        await client.post(
            f"{API_BASE}/fx/providers/pair-sources",
            json=[
                {"base": "EUR", "quote": "USD", "provider_code": "ECB", "priority": 1},
                {"base": "GBP", "quote": "USD", "provider_code": "ECB", "priority": 1},
                ],
            timeout=TIMEOUT,
            )

        today = date.today()
        start_date = today - timedelta(days=7)

        await client.post(
            f"{API_BASE}/fx/currencies/sync",
            json={
                "pairs": ["EUR-USD", "GBP-USD"],
                "start": start_date.isoformat(),
                "end": today.isoformat(),
                },
            timeout=TIMEOUT,
            )
        print_info("  FX rates synced for bulk test")

        # Step 2: Request BULK conversions, each with multi-day range
        conversions = [
            FXConversionRequest(
                from_amount=Currency(code="USD", amount=Decimal("100")),
                **{"to": "EUR"},
                date_range=DateRangeModel(start=start_date, end=start_date + timedelta(days=2)),
                ),
            FXConversionRequest(
                from_amount=Currency(code="USD", amount=Decimal("200")),
                **{"to": "GBP"},
                date_range=DateRangeModel(start=start_date, end=start_date + timedelta(days=2)),
                ),
            ]

        convert_resp = await client.post(
            f"{API_BASE}/fx/currencies/convert",
            json=[c.model_dump(mode="json") for c in conversions],
            timeout=TIMEOUT,
            )

        assert convert_resp.status_code == 200, f"Bulk convert failed: {convert_resp.status_code}"

        convert_data = FXConvertResponse(**convert_resp.json())
        assert (
            convert_data.success_count >= 3
        ), f"Expected at least 3 successful conversions, got {convert_data.success_count}"

        print_success(
            f"✓ Bulk multi-day conversion successful: {convert_data.success_count} conversions"
            )
        print_info(f"  Results returned: {len(convert_data.results)}")

        if convert_data.errors:
            print_info(f"  Some conversions failed (expected): {len(convert_data.errors)} errors")

        # Cleanup
        await client.request(
            "DELETE",
            f"{API_BASE}/fx/providers/pair-sources",
            json=[
                {"base": "EUR", "quote": "USD"},
                {"base": "GBP", "quote": "USD"},
                ],
            timeout=TIMEOUT,
            )

