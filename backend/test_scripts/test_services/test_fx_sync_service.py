"""
FX sync service tests.

Focus: pair-sync orchestration branches in services/fx.py
- _is_date_within_sync_range
- sync_pairs_bulk._process_route
- sync_pairs_bulk._compute_multi_step
"""

import asyncio
import json
import sys
from datetime import date
from decimal import Decimal

import pytest

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, select

from backend.app.db.models import FxConversionRoute, FxRate
from backend.app.db.session import get_async_engine
from backend.app.services.fx import _is_date_within_sync_range, sync_pairs_bulk
from backend.app.services.fx_providers.mockfx import MOCKFX_FIXED_RATE
from backend.test_scripts.test_utils import print_section, print_success

# The two pairs this file works on, and the only rows it is entitled to remove.
#
# The fixture below used to be two DELETEs with no WHERE, committed: it emptied the
# whole `fx_rates` table *and every FX route in the database* before each of its
# tests. That took the mock's ECB series and every route another test had just
# configured with it, and a committed DELETE is not something a neighbour's rollback
# can put back.
#
# Scoping the rates by MOCKFX is enough because that provider only ever runs in
# tests: a real ECB or SNB row is never touched. The routes are scoped by pair.
FX_SYNC_PAIRS = (("EUR", "USD"), ("GBP", "JPY"))


@pytest.fixture(autouse=True)
def _clean_fx_tables():
    """Remove this file's own rates and routes, and nobody else's."""

    async def _purge():
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            await session.execute(delete(FxRate).where(FxRate.source == "MOCKFX"))
            for base, quote in FX_SYNC_PAIRS:
                await session.execute(delete(FxConversionRoute).where(FxConversionRoute.base == base, FxConversionRoute.quote == quote))
            await session.commit()

    asyncio.run(_purge())
    yield


class TestFXSyncHelpers:
    """Pure helper coverage for sync-range logic."""

    def test_is_date_within_sync_range_supports_min_and_explicit_start(self):
        """Cover both 'min' and explicit-date branches."""
        print_section("_is_date_within_sync_range")

        assert _is_date_within_sync_range(date(1900, 1, 1), "min", date(1900, 1, 3)) is True
        assert _is_date_within_sync_range(date(1900, 1, 4), "min", date(1900, 1, 3)) is False

        assert _is_date_within_sync_range(date(2025, 1, 2), date(2025, 1, 2), date(2025, 1, 3)) is True
        assert _is_date_within_sync_range(date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 3)) is False

        print_success("Covered min + explicit-date range branches")


@pytest.mark.asyncio
class TestSyncPairsBulk:
    """Deterministic sync_pairs_bulk coverage with mock providers."""

    async def test_sync_pairs_bulk_single_step_direct_route(self):
        """Single-step MOCKFX route should use direct _process_route branch."""
        print_section("sync_pairs_bulk: single-step direct route")

        engine = get_async_engine()
        start_date = date(2025, 1, 1)
        end_date = date(2025, 1, 2)

        async with AsyncSession(engine, expire_on_commit=False) as session:
            session.add(
                FxConversionRoute(
                    base="EUR",
                    quote="USD",
                    priority=1,
                    chain_steps=json.dumps(
                        [
                            {"from": "EUR", "to": "USD", "provider": "MOCKFX"},
                        ]
                    ),
                )
            )
            await session.commit()

            response = await sync_pairs_bulk(
                session,
                pairs=["EUR-USD"],
                date_range=(start_date, end_date),
            )

        result = response.results[0]
        assert result.status == "ok"
        assert result.provider_used == "MOCKFX"
        assert result.points_fetched == 2
        assert result.points_changed == 2

        async with AsyncSession(engine) as verify_session:
            # Filtered by source as well as pair: counting every EUR/USD row in the
            # table was a global count this test never created, and it only ever
            # worked because the fixture had just emptied the table for everyone.
            rows = (await verify_session.execute(select(FxRate).where(FxRate.base == "EUR", FxRate.quote == "USD", FxRate.source == "MOCKFX").order_by(FxRate.date))).scalars().all()

        assert len(rows) == 2
        assert all(row.rate == MOCKFX_FIXED_RATE for row in rows)
        assert all(row.source == "MOCKFX" for row in rows)
        print_success("Single-step route persisted direct MOCKFX rates")

    async def test_sync_pairs_bulk_multi_step_chain_with_min_start(self):
        """Multi-step MOCKFX chain should persist composite rates for 'min' range."""
        print_section("sync_pairs_bulk: multi-step chain with start='min'")

        engine = get_async_engine()
        end_date = date(1900, 1, 3)

        async with AsyncSession(engine, expire_on_commit=False) as session:
            session.add(
                FxConversionRoute(
                    base="GBP",
                    quote="JPY",
                    priority=1,
                    chain_steps=json.dumps(
                        [
                            {"from": "GBP", "to": "EUR", "provider": "MOCKFX"},
                            {"from": "EUR", "to": "JPY", "provider": "MOCKFX"},
                        ]
                    ),
                )
            )
            await session.commit()

            response = await sync_pairs_bulk(
                session,
                pairs=["GBP-JPY"],
                date_range=("min", end_date),
            )

        assert response.success_count == 1
        assert response.total_points_changed == 3
        assert len(response.results) == 1

        result = response.results[0]
        assert result.pair == "GBP-JPY"
        assert result.status == "ok"
        assert result.provider_used == "CHAIN:MOCKFX+MOCKFX"
        assert result.points_fetched == 3
        assert result.points_changed == 3
        assert result.errors == []
        assert result.detail is not None
        assert len(result.detail) == 2
        assert all(item.dates_available == 3 for item in result.detail)

        async with AsyncSession(engine) as verify_session:
            rows = (await verify_session.execute(select(FxRate).where(FxRate.base == "GBP", FxRate.quote == "JPY").order_by(FxRate.date))).scalars().all()

        assert len(rows) == 3
        assert all(row.source == "CHAIN:MOCKFX+MOCKFX" for row in rows)
        assert all(row.rate == Decimal("1") for row in rows)
        assert MOCKFX_FIXED_RATE == Decimal("1.234500")

        print_success("Multi-step chain persisted 3 composite GBP/JPY rates")
