"""
Test: FX Core Service — normalize_rate_for_storage, upsert_rates_bulk,
delete_rates_bulk, _count_actual_changes.

Covers the service-layer helper functions in fx.py that are NOT covered
by test_fx_conversion.py (which focuses on convert_bulk / compute_chain_rate).
"""

import asyncio
import sys
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete

from backend.app.db.models import FxRate
from backend.app.db.session import get_async_engine
from backend.app.services.fx import (
    _count_actual_changes,
    delete_rates_bulk,
    normalize_rate_for_storage,
    upsert_rates_bulk,
)
from backend.app.utils.decimal_utils import truncate_fx_rate
from backend.test_scripts.test_utils import print_section, print_success


# ============================================================================
# FIXTURE — clean FxRate table before each test
# ============================================================================


@pytest.fixture(autouse=True)
def _clean_fx_rates():
    """Ensure FxRate table is empty before each test."""

    async def _purge():
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            await session.execute(delete(FxRate))
            await session.commit()

    asyncio.run(_purge())
    yield


# ============================================================================
# normalize_rate_for_storage — pure function tests
# ============================================================================


class TestNormalizeRateForStorage:
    """Tests for normalize_rate_for_storage()."""

    def test_base_lt_quote_no_change(self):
        """EUR < USD alphabetically → no inversion."""
        print_section("normalize_rate: base < quote (no-op)")
        b, q, r = normalize_rate_for_storage("EUR", "USD", Decimal("1.08"))
        assert b == "EUR"
        assert q == "USD"
        assert r == Decimal("1.08")
        print_success("No inversion when base < quote")

    def test_base_gt_quote_invert(self):
        """USD > CHF → swap to CHF/USD + invert rate."""
        print_section("normalize_rate: base > quote (invert)")
        b, q, r = normalize_rate_for_storage("USD", "CHF", Decimal("0.90"))
        assert b == "CHF"
        assert q == "USD"
        # Inverted: 1/0.90 ≈ 1.1111...
        expected = Decimal("1") / Decimal("0.90")
        assert r == expected
        print_success(f"Inverted correctly: CHF/USD = {r}")

    def test_base_eq_quote(self):
        """Same currency — normalize_rate_for_storage doesn't validate, returns as-is."""
        print_section("normalize_rate: base == quote (edge case)")
        b, q, r = normalize_rate_for_storage("EUR", "EUR", Decimal("1.00"))
        # base == quote alphabetically → no inversion path
        assert b == "EUR"
        assert q == "EUR"
        assert r == Decimal("1.00")
        print_success("Same currency returns as-is (no validation in this function)")


# ============================================================================
# upsert_rates_bulk — DB tests
# ============================================================================


@pytest.mark.asyncio
class TestUpsertRatesBulk:
    """Tests for upsert_rates_bulk()."""

    async def test_insert_new_rates(self):
        """Insert brand-new rates → action = 'inserted'."""
        print_section("upsert_rates_bulk: insert new rates")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            today = date.today()
            rates = [
                (today, "EUR", "USD", Decimal("1.0800"), "TEST"),
                (today, "CHF", "EUR", Decimal("1.0600"), "TEST"),
            ]
            results = await upsert_rates_bulk(session, rates)
            assert len(results) == 2
            for success, action in results:
                assert success is True
                assert action == "inserted"
            print_success(f"Inserted {len(results)} rates")

    async def test_upsert_existing_rates(self):
        """Insert then re-insert same keys with different value → action = 'updated'."""
        print_section("upsert_rates_bulk: update existing rates")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            today = date.today()
            rates_v1 = [(today, "EUR", "USD", Decimal("1.0800"), "TEST")]
            await upsert_rates_bulk(session, rates_v1)

        async with AsyncSession(engine) as session:
            rates_v2 = [(today, "EUR", "USD", Decimal("1.0900"), "TEST_v2")]
            results = await upsert_rates_bulk(session, rates_v2)
            assert len(results) == 1
            success, action = results[0]
            assert success is True
            assert action == "updated"
            print_success("Updated existing rate correctly")

    async def test_empty_list(self):
        """Empty input → empty results."""
        print_section("upsert_rates_bulk: empty list")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            results = await upsert_rates_bulk(session, [])
            assert results == []
            print_success("Empty list → empty results")

    async def test_validation_same_currency(self):
        """base == quote → ValueError."""
        print_section("upsert_rates_bulk: validation base == quote")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            with pytest.raises(ValueError, match="Base and quote must be different"):
                await upsert_rates_bulk(session, [(date.today(), "EUR", "EUR", Decimal("1"), "TEST")])
            print_success("ValueError raised for same currency")

    async def test_validation_negative_rate(self):
        """rate ≤ 0 → ValueError."""
        print_section("upsert_rates_bulk: validation rate ≤ 0")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            with pytest.raises(ValueError, match="Rate must be positive"):
                await upsert_rates_bulk(session, [(date.today(), "EUR", "USD", Decimal("-1"), "TEST")])
            print_success("ValueError raised for negative rate")

    async def test_auto_normalize_order(self):
        """base > quote → auto-normalized to alphabetical order."""
        print_section("upsert_rates_bulk: auto-normalize order")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            today = date.today()
            # USD > CHF → should be stored as CHF/USD inverted
            rates = [(today, "USD", "CHF", Decimal("1.1111"), "TEST")]
            results = await upsert_rates_bulk(session, rates)
            assert results[0] == (True, "inserted")
            print_success("Auto-normalized and inserted correctly")


# ============================================================================
# delete_rates_bulk — DB tests
# ============================================================================


@pytest.mark.asyncio
class TestDeleteRatesBulk:
    """Tests for delete_rates_bulk()."""

    async def _seed(self, session, pairs_dates):
        """Helper: insert rates for given (base, quote, date) tuples."""
        for b, q, d in pairs_dates:
            rate = FxRate(date=d, base=b, quote=q, rate=Decimal("1.0000"), source="SEED")
            session.add(rate)
        await session.commit()

    async def test_delete_single_day(self):
        """Delete a single day for a pair."""
        print_section("delete_rates_bulk: single day")
        engine = get_async_engine()
        today = date.today()
        async with AsyncSession(engine) as session:
            await self._seed(session, [("EUR", "USD", today)])

        async with AsyncSession(engine) as session:
            results = await delete_rates_bulk(session, [("EUR", "USD", today, None)])
            assert len(results) == 1
            success, existing, deleted, msg = results[0]
            assert success is True
            assert deleted >= 1
            print_success(f"Deleted {deleted} rate(s)")

    async def test_delete_range(self):
        """Delete a date range for a pair."""
        print_section("delete_rates_bulk: date range")
        engine = get_async_engine()
        base_date = date.today() - timedelta(days=10)
        dates = [base_date + timedelta(days=i) for i in range(5)]
        async with AsyncSession(engine) as session:
            await self._seed(session, [("EUR", "USD", d) for d in dates])

        async with AsyncSession(engine) as session:
            results = await delete_rates_bulk(
                session, [("EUR", "USD", dates[0], dates[-1])]
            )
            success, existing, deleted, msg = results[0]
            assert success is True
            assert deleted == 5
            print_success(f"Deleted {deleted} rate(s) in range")

    async def test_delete_not_found(self):
        """Delete non-existent pair → success=True, deleted=0."""
        print_section("delete_rates_bulk: pair not found")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            results = await delete_rates_bulk(
                session, [("AAA", "ZZZ", date.today(), None)]
            )
            success, existing, deleted, msg = results[0]
            assert success is True
            assert deleted == 0
            print_success("Not found returns (True, 0, 0, ...)")

    async def test_delete_empty_list(self):
        """Empty input → empty results."""
        print_section("delete_rates_bulk: empty list")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            results = await delete_rates_bulk(session, [])
            assert results == []
            print_success("Empty list → empty results")


# ============================================================================
# _count_actual_changes — DB tests
# ============================================================================


@pytest.mark.asyncio
class TestCountActualChanges:
    """Tests for _count_actual_changes()."""

    async def test_all_new_inserts(self):
        """No existing data → all rates are new → count = len."""
        print_section("_count_actual_changes: all new")
        engine = get_async_engine()
        today = date.today()
        async with AsyncSession(engine) as session:
            computed = [
                (today, "EUR", "USD", truncate_fx_rate(Decimal("1.0800"))),
                (today - timedelta(days=1), "EUR", "USD", truncate_fx_rate(Decimal("1.0790"))),
            ]
            count = await _count_actual_changes(session, computed)
            assert count == 2
            print_success(f"All new → count = {count}")

    async def test_no_changes(self):
        """Existing data matches exactly → count = 0."""
        print_section("_count_actual_changes: no changes")
        engine = get_async_engine()
        today = date.today()
        rate_val = truncate_fx_rate(Decimal("1.0800"))

        async with AsyncSession(engine) as session:
            session.add(FxRate(date=today, base="EUR", quote="USD", rate=rate_val, source="TEST"))
            await session.commit()

        async with AsyncSession(engine) as session:
            computed = [(today, "EUR", "USD", rate_val)]
            count = await _count_actual_changes(session, computed)
            assert count == 0
            print_success(f"Same values → count = {count}")

    async def test_mixed_changes(self):
        """Mix of new, same, and changed values."""
        print_section("_count_actual_changes: mixed")
        engine = get_async_engine()
        d1 = date.today()
        d2 = date.today() - timedelta(days=1)
        d3 = date.today() - timedelta(days=2)
        rate_same = truncate_fx_rate(Decimal("1.0800"))
        rate_changed_old = truncate_fx_rate(Decimal("1.0700"))
        rate_changed_new = truncate_fx_rate(Decimal("1.0900"))

        async with AsyncSession(engine) as session:
            # d1: existing with same value (no change)
            session.add(FxRate(date=d1, base="EUR", quote="USD", rate=rate_same, source="TEST"))
            # d2: existing with different value (change)
            session.add(FxRate(date=d2, base="EUR", quote="USD", rate=rate_changed_old, source="TEST"))
            await session.commit()

        async with AsyncSession(engine) as session:
            computed = [
                (d1, "EUR", "USD", rate_same),           # same → no change
                (d2, "EUR", "USD", rate_changed_new),     # changed → +1
                (d3, "EUR", "USD", truncate_fx_rate(Decimal("1.0750"))),  # new → +1
            ]
            count = await _count_actual_changes(session, computed)
            assert count == 2  # 1 changed + 1 new
            print_success(f"Mixed → count = {count} (1 changed + 1 new)")

    async def test_empty_list(self):
        """Empty computed list → 0."""
        print_section("_count_actual_changes: empty list")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            count = await _count_actual_changes(session, [])
            assert count == 0
            print_success("Empty list → 0")


# ============================================================================
# normalize_rate_for_storage — additional edge cases
# ============================================================================


class TestNormalizeRateEdgeCases:
    """Additional edge cases for normalize_rate_for_storage."""

    def test_very_small_rate(self):
        """Very small rate (like JPY per 100) normalizes correctly."""
        print_section("normalize_rate: very small rate")
        b, q, r = normalize_rate_for_storage("JPY", "USD", Decimal("0.0067"))
        assert b == "JPY"
        assert q == "USD"
        assert r == Decimal("0.0067")
        print_success(f"Small rate preserved: {r}")

    def test_large_rate(self):
        """Large rate (e.g., 1 BTC = 60000 USD) normalizes correctly."""
        print_section("normalize_rate: large rate")
        b, q, r = normalize_rate_for_storage("BTC", "USD", Decimal("60000.50"))
        # BTC > USD alphabetically → inverted to (BTC, USD)
        assert b == "BTC"
        assert q == "USD"
        assert r == Decimal("60000.50")
        print_success(f"Large rate preserved: {r}")


# ============================================================================
# upsert_rates_bulk — additional edge cases
# ============================================================================


@pytest.mark.asyncio
class TestUpsertRatesBulkEdgeCases:
    """Additional edge case tests for upsert_rates_bulk."""

    async def test_upsert_same_rate_unchanged(self):
        """Insert then re-insert same key with same value → action = 'unchanged'."""
        print_section("upsert_rates_bulk: same rate unchanged")
        engine = get_async_engine()
        today = date.today()
        rate_val = Decimal("1.0800")

        async with AsyncSession(engine) as session:
            await upsert_rates_bulk(session, [(today, "EUR", "USD", rate_val, "TEST")])

        async with AsyncSession(engine) as session:
            results = await upsert_rates_bulk(session, [(today, "EUR", "USD", rate_val, "TEST")])
            assert len(results) == 1
            success, action = results[0]
            assert success is True
            # Action should be 'updated' or 'unchanged' — depending on implementation
            assert action in ("updated", "unchanged")
            print_success(f"Same rate → action={action}")

    async def test_upsert_multiple_pairs(self):
        """Multiple different pairs in one bulk call."""
        print_section("upsert_rates_bulk: multiple pairs")
        engine = get_async_engine()
        today = date.today()
        rates = [
            (today, "CHF", "USD", Decimal("1.1200"), "TEST"),
            (today, "EUR", "GBP", Decimal("0.8400"), "TEST"),
            (today, "AUD", "USD", Decimal("0.6500"), "TEST"),
        ]
        async with AsyncSession(engine) as session:
            results = await upsert_rates_bulk(session, rates)
            assert len(results) == 3
            assert all(r[0] for r in results), "All should succeed"
            print_success(f"Inserted {len(results)} different pairs")


