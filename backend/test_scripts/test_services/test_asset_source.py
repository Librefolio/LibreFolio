"""
Test asset source service (provider assignment and helper functions).

Tests:
- Helper functions (truncation, ACT/365 calculation)
- Synthetic yield calculation
- Provider assignment (bulk and single)
- Provider removal (bulk and single)

TODO: Add tests for price CRUD and refresh when implemented.
"""
import asyncio
from datetime import date, datetime
from decimal import Decimal
import sys

from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import async_engine
from backend.app.db.models import (
    Asset,
    AssetProviderAssignment,
    AssetType,
    ValuationModel,
)
from backend.app.services.asset_source import (
    AssetSourceManager,
    calculate_days_between_act365,
    truncate_price_to_db_precision,
    get_price_column_precision,
)


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================


def test_price_column_precision():
    """Test get_price_column_precision() helper."""
    print("=" * 60)
    print("Test 1: Price Column Precision")
    print("=" * 60)

    columns = ["open", "high", "low", "close", "adjusted_close"]
    for col in columns:
        precision, scale = get_price_column_precision(col)
        print(f"✅ {col}: NUMERIC({precision}, {scale})")
        assert precision == 18
        assert scale == 6

    print("✅ All price columns have correct precision\n")


def test_truncate_price():
    """Test truncate_price_to_db_precision() helper."""
    print("=" * 60)
    print("Test 2: Price Truncation")
    print("=" * 60)

    test_cases = [
        ("175.1234567890", "175.123456"),  # Truncate extra decimals
        ("175.123456", "175.123456"),      # Already at precision
        ("175.12", "175.120000"),          # Pad to 6 decimals
        ("1000.9999999", "1000.999999"),   # Large number
    ]

    for input_str, expected_str in test_cases:
        input_val = Decimal(input_str)
        result = truncate_price_to_db_precision(input_val)
        expected = Decimal(expected_str)

        print(f"ℹ️  Input:    {input_val}")
        print(f"   Expected: {expected}")
        print(f"   Result:   {result}")
        assert result == expected, f"Mismatch: {result} != {expected}"
        print("✅ Truncation correct\n")

    print("✅ All truncation tests passed\n")


def test_act365_calculation():
    """Test calculate_days_between_act365() helper."""
    print("=" * 60)
    print("Test 3: ACT/365 Day Count")
    print("=" * 60)

    test_cases = [
        (date(2025, 1, 1), date(2025, 1, 31), Decimal("30") / Decimal("365")),  # 30 days
        (date(2025, 1, 1), date(2025, 12, 31), Decimal("364") / Decimal("365")),  # 364 days
        (date(2025, 1, 1), date(2026, 1, 1), Decimal("365") / Decimal("365")),  # Exactly 1 year
    ]

    for start, end, expected in test_cases:
        result = calculate_days_between_act365(start, end)
        days = (end - start).days

        print(f"ℹ️  Period: {start} to {end} ({days} days)")
        print(f"   Expected: {expected}")
        print(f"   Result:   {result}")
        assert result == expected, f"Mismatch: {result} != {expected}"
        print("✅ Calculation correct\n")

    print("✅ All ACT/365 tests passed\n")


# ============================================================================
# PROVIDER ASSIGNMENT TESTS
# ============================================================================


async def test_bulk_assign_providers():
    """Test bulk_assign_providers() method."""
    print("=" * 60)
    print("Test 4: Bulk Assign Providers")
    print("=" * 60)

    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        # Create test assets
        test_assets = [
            Asset(
                display_name=f"Test Asset {i}",
                identifier=f"TEST{i}",
                identifier_type="TICKER",
                currency="USD",
                asset_type=AssetType.STOCK,
                valuation_model=ValuationModel.MARKET_PRICE,
                active=True,
            )
            for i in range(1, 4)
        ]

        session.add_all(test_assets)
        await session.commit()

        # Refresh to get IDs
        for asset in test_assets:
            await session.refresh(asset)

        print(f"ℹ️  Created {len(test_assets)} test assets")

        # Bulk assign providers
        assignments = [
            {"asset_id": test_assets[0].id, "provider_code": "yfinance", "provider_params": '{"ticker": "TEST1"}'},
            {"asset_id": test_assets[1].id, "provider_code": "yfinance", "provider_params": '{"ticker": "TEST2"}'},
            {"asset_id": test_assets[2].id, "provider_code": "cssscraper", "provider_params": '{"url": "http://example.com"}'},
        ]

        results = await AssetSourceManager.bulk_assign_providers(assignments, session)

        print(f"✅ Bulk assigned {len(results)} providers")

        for result in results:
            assert result["success"], f"Assignment failed: {result}"
            print(f"   ✓ Asset {result['asset_id']}: {result['message']}")

        # Verify in DB
        for assignment in assignments:
            provider = await AssetSourceManager.get_asset_provider(assignment["asset_id"], session)
            assert provider is not None
            assert provider.provider_code == assignment["provider_code"]
            print(f"   ✓ Verified: Asset {assignment['asset_id']} → {provider.provider_code}")

        print("✅ All assignments verified in DB\n")

        return [a.id for a in test_assets]  # Return for cleanup


async def test_single_assign_provider(asset_ids: list[int]):
    """Test assign_provider() single method (calls bulk)."""
    print("=" * 60)
    print("Test 5: Single Assign Provider (calls bulk)")
    print("=" * 60)

    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        # Use first test asset
        asset_id = asset_ids[0]

        # Update provider (yfinance → cssscraper)
        result = await AssetSourceManager.assign_provider(
            asset_id=asset_id,
            provider_code="cssscraper",
            provider_params='{"url": "http://new-url.com"}',
            session=session,
        )

        assert result["success"]
        print(f"✅ Single assign: {result['message']}")

        # Verify update
        provider = await AssetSourceManager.get_asset_provider(asset_id, session)
        assert provider.provider_code == "cssscraper"
        print(f"✅ Verified: Asset {asset_id} updated to {provider.provider_code}\n")


async def test_bulk_remove_providers(asset_ids: list[int]):
    """Test bulk_remove_providers() method."""
    print("=" * 60)
    print("Test 6: Bulk Remove Providers")
    print("=" * 60)

    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        # Remove all providers
        results = await AssetSourceManager.bulk_remove_providers(asset_ids, session)

        print(f"✅ Bulk removed {len(results)} providers")

        for result in results:
            assert result["success"]
            print(f"   ✓ Asset {result['asset_id']}: {result['message']}")

        # Verify removal
        for asset_id in asset_ids:
            provider = await AssetSourceManager.get_asset_provider(asset_id, session)
            assert provider is None
            print(f"   ✓ Verified: Asset {asset_id} has no provider")

        print("✅ All removals verified\n")


async def test_single_remove_provider(asset_ids: list[int]):
    """Test remove_provider() single method (calls bulk)."""
    print("=" * 60)
    print("Test 7: Single Remove Provider (calls bulk)")
    print("=" * 60)

    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        # First assign a provider
        asset_id = asset_ids[1]
        await AssetSourceManager.assign_provider(
            asset_id=asset_id,
            provider_code="yfinance",
            provider_params='{"ticker": "TEST"}',
            session=session,
        )
        print(f"ℹ️  Re-assigned provider to asset {asset_id}")

        # Remove via single method
        result = await AssetSourceManager.remove_provider(asset_id, session)

        assert result["success"]
        print(f"✅ Single remove: {result['message']}")

        # Verify removal
        provider = await AssetSourceManager.get_asset_provider(asset_id, session)
        assert provider is None
        print(f"✅ Verified: Asset {asset_id} has no provider\n")


# ============================================================================
# TEST ORCHESTRATION
# ============================================================================


async def run_all_tests():
    """Run all tests in sequence."""
    print("\n" + "=" * 60)
    print(" Asset Source Service - Basic Tests")
    print("=" * 60 + "\n")

    # Helper function tests (synchronous)
    test_price_column_precision()
    test_truncate_price()
    test_act365_calculation()

    # Provider assignment tests (asynchronous)
    asset_ids = await test_bulk_assign_providers()
    await test_single_assign_provider(asset_ids)
    await test_bulk_remove_providers(asset_ids)
    await test_single_remove_provider(asset_ids)

    print("=" * 60)
    print("✅ All tests passed!")
    print("=" * 60 + "\n")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)

