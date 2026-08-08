"""
Asset merge tests (P3/A-02).

``AssetCRUDService.merge_assets`` folds one asset into another and deletes the
source. It exists to repay the duplicate-asset debt left by imports where the same
instrument was booked twice — canonically an Italian BTP whose placement ("CUM")
ISIN and market ISIN were treated as two different instruments.

The merge is destructive, so every referencing table gets an explicit, tested
policy. These tests pin exactly the four foreign keys to ``assets.id`` plus the two
traps hidden between them:

- ``Transaction.asset_event_id`` is ``ondelete=RESTRICT`` → discarding a duplicate
  event without first remapping its transactions raises an IntegrityError.
- ``AssetEvent.provider_assignment_id`` is ``ondelete=CASCADE`` → deleting the
  source's provider assignment would silently destroy the events just migrated.

Note on style: the service commits, which expires every ORM object attached to the
session. Tests therefore pass **integer ids** around and re-query whatever they need
to assert; touching a stale instance would trigger a lazy load and blow up with
``MissingGreenlet``.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    AssetEvent,
    AssetEventType,
    AssetProviderAssignment,
    AssetType,
    Broker,
    PriceHistory,
    ProviderInputType,
    Transaction,
    TransactionType,
)
from backend.app.db.session import get_async_engine
from backend.app.services.asset_source import AssetCRUDService, AssetSourceError

# =============================================================================
# FIXTURES
# =============================================================================


@pytest_asyncio.fixture
async def async_session():
    """Create an async session for database tests."""
    engine = get_async_engine()
    async with AsyncSession(engine) as session:
        yield session


@pytest_asyncio.fixture
async def merge_broker(async_session: AsyncSession) -> int:
    """Create a throwaway broker and return its ID.

    Request this fixture **before** ``btp_pair`` in a test signature: pytest tears
    fixtures down in reverse setup order, and a broker cannot be deleted while the
    asset fixture's transactions still point at it.
    """
    broker = Broker(name=f"Test Broker Merge {uuid.uuid4().hex[:8]}", description="Test broker for merge tests")
    async_session.add(broker)
    await async_session.commit()
    await async_session.refresh(broker)
    broker_id = broker.id

    yield broker_id

    leftover = (await async_session.execute(select(Broker).where(Broker.id == broker_id))).scalars().first()
    if leftover:
        await async_session.delete(leftover)
        await async_session.commit()


@pytest_asyncio.fixture
async def btp_pair(async_session: AsyncSession):
    """The real-world duplicate: the same BTP booked twice, CUM ISIN vs market ISIN.

    ``source`` is the accidental duplicate created from the placement report (CUM
    ISIN, not quoted). ``target`` is the asset the user wants to keep — the one
    carrying the tradeable ISIN that a price provider can actually index.

    Yields ``(source_id, target_id)``.
    """
    suffix = uuid.uuid4().hex[:6]
    source = Asset(
        display_name=f"BTP Piu Sc Fb33 CUM {suffix}",
        asset_type=AssetType.BOND,
        currency="EUR",
        identifier_isin="IT0005634792",
        active=True,
    )
    target = Asset(
        display_name=f"BTP Piu Sc Fb33 {suffix}",
        asset_type=AssetType.BOND,
        currency="EUR",
        identifier_isin="IT0005634800",
        active=True,
    )
    async_session.add(source)
    async_session.add(target)
    await async_session.commit()
    await async_session.refresh(source)
    await async_session.refresh(target)
    source_id, target_id = source.id, target.id

    yield source_id, target_id

    # Cleanup: children first. The merge usually removed the source already, and
    # transactions must let go of their event before the events can be deleted.
    for asset_id in (source_id, target_id):
        txs = (await async_session.execute(select(Transaction).where(Transaction.asset_id == asset_id))).scalars().all()
        for tx in txs:
            tx.asset_event_id = None
        await async_session.flush()
        for model in (Transaction, AssetEvent, PriceHistory, AssetProviderAssignment):
            rows = (await async_session.execute(select(model).where(model.asset_id == asset_id))).scalars().all()
            for row in rows:
                await async_session.delete(row)
        await async_session.flush()
        leftover = (await async_session.execute(select(Asset).where(Asset.id == asset_id))).scalars().first()
        if leftover:
            await async_session.delete(leftover)
    await async_session.commit()


# =============================================================================
# HELPERS
# =============================================================================


async def _get_asset(session: AsyncSession, asset_id: int) -> Asset | None:
    return (await session.execute(select(Asset).where(Asset.id == asset_id))).scalars().first()


# =============================================================================
# MERGE TESTS (AM-*)
# =============================================================================


class TestAssetMerge:
    """Tests for AssetCRUDService.merge_assets."""

    @pytest.mark.asyncio
    async def test_transactions_move_to_target(self, async_session: AsyncSession, merge_broker: int, btp_pair):
        """AM-001: transactions booked on the duplicate end up on the surviving asset."""
        source_id, target_id = btp_pair
        for day in (10, 11):
            async_session.add(
                Transaction(
                    broker_id=merge_broker,
                    asset_id=source_id,
                    type=TransactionType.BUY,
                    date=date(2025, 3, day),
                    quantity=Decimal("100"),
                    amount=Decimal("-10000"),
                    currency="EUR",
                )
            )
        await async_session.commit()

        result = await AssetCRUDService.merge_assets(source_id, target_id, async_session)

        assert result.success is True
        assert result.preview.transactions == 2
        moved = (await async_session.execute(select(Transaction).where(Transaction.asset_id == target_id))).scalars().all()
        assert len(moved) == 2
        assert await _get_asset(async_session, source_id) is None

    @pytest.mark.asyncio
    async def test_cum_isin_is_demoted_not_lost(self, async_session: AsyncSession, btp_pair):
        """AM-002: the CUM ISIN survives in identifier_other — this is the whole point.

        Losing it would break the next import that cites the placement ISIN, which is
        exactly the loop the beta tester got stuck in.
        """
        source_id, target_id = btp_pair
        source = await _get_asset(async_session, source_id)
        source.identifier_other = ["BTP PIU FB33"]
        await async_session.commit()

        result = await AssetCRUDService.merge_assets(source_id, target_id, async_session)

        target = await _get_asset(async_session, target_id)
        assert target.identifier_isin == "IT0005634800"
        assert "IT0005634792" in (target.identifier_other or [])
        assert "BTP PIU FB33" in (target.identifier_other or [])
        assert "IT0005634792" in result.preview.identifiers_added

    @pytest.mark.asyncio
    async def test_explicit_primary_swaps_the_isins(self, async_session: AsyncSession, btp_pair):
        """AM-003: the caller may keep the source's ISIN as primary; the other is demoted."""
        source_id, target_id = btp_pair

        await AssetCRUDService.merge_assets(
            source_id,
            target_id,
            async_session,
            identifier_primaries={"identifier_isin": "IT0005634792"},
        )

        target = await _get_asset(async_session, target_id)
        assert target.identifier_isin == "IT0005634792"
        assert "IT0005634800" in (target.identifier_other or [])

    @pytest.mark.asyncio
    async def test_unknown_primary_is_refused(self, async_session: AsyncSession, btp_pair):
        """AM-004: a primary that belongs to neither asset is a client bug, not a rename."""
        source_id, target_id = btp_pair

        with pytest.raises(AssetSourceError) as exc:
            await AssetCRUDService.merge_assets(
                source_id,
                target_id,
                async_session,
                identifier_primaries={"identifier_isin": "XX0000000000"},
            )
        assert exc.value.error_code == "INVALID_PRIMARY"
        assert await _get_asset(async_session, source_id) is not None

    @pytest.mark.asyncio
    async def test_price_collision_target_wins(self, async_session: AsyncSession, btp_pair):
        """AM-005: same date on both assets → the target row survives, the source row is dropped.

        ``uq_price_history_asset_date`` makes a blind reassignment an IntegrityError;
        the target wins because it is the asset whose provider keeps feeding prices.
        """
        source_id, target_id = btp_pair
        async_session.add(PriceHistory(asset_id=target_id, date=date(2025, 3, 10), close=Decimal("101"), currency="EUR", source_plugin_key="test"))
        async_session.add(PriceHistory(asset_id=source_id, date=date(2025, 3, 10), close=Decimal("99"), currency="EUR", source_plugin_key="test"))
        async_session.add(PriceHistory(asset_id=source_id, date=date(2025, 3, 11), close=Decimal("98"), currency="EUR", source_plugin_key="test"))
        await async_session.commit()

        result = await AssetCRUDService.merge_assets(source_id, target_id, async_session)

        assert result.preview.prices == 1
        assert result.preview.prices_discarded == 1
        rows = (await async_session.execute(select(PriceHistory).where(PriceHistory.asset_id == target_id))).scalars().all()
        by_date = {r.date: Decimal(str(r.close)) for r in rows}
        assert by_date[date(2025, 3, 10)] == Decimal("101")
        assert by_date[date(2025, 3, 11)] == Decimal("98")

    @pytest.mark.asyncio
    async def test_duplicate_event_is_deduped_and_transaction_relinked(self, async_session: AsyncSession, merge_broker: int, btp_pair):
        """AM-006: the RESTRICT trap.

        Both assets carry the same coupon event, and a transaction realizes the
        source's copy. Dropping that event without remapping the transaction first
        would raise a FK violation, so the remap is the load-bearing step here.
        """
        source_id, target_id = btp_pair
        target_event = AssetEvent(asset_id=target_id, date=date(2025, 3, 10), type=AssetEventType.INTEREST, value=Decimal("1.500000"), currency="EUR")
        source_event = AssetEvent(asset_id=source_id, date=date(2025, 3, 10), type=AssetEventType.INTEREST, value=Decimal("1.500000"), currency="EUR")
        async_session.add(target_event)
        async_session.add(source_event)
        await async_session.commit()
        await async_session.refresh(target_event)
        await async_session.refresh(source_event)
        surviving_event_id, source_event_id = target_event.id, source_event.id

        tx = Transaction(
            broker_id=merge_broker,
            asset_id=source_id,
            type=TransactionType.INTEREST,
            date=date(2025, 3, 10),
            quantity=Decimal("0"),
            amount=Decimal("150"),
            currency="EUR",
            asset_event_id=source_event_id,
        )
        async_session.add(tx)
        await async_session.commit()
        await async_session.refresh(tx)
        tx_id = tx.id

        result = await AssetCRUDService.merge_assets(source_id, target_id, async_session)

        assert result.preview.events_discarded == 1
        assert result.preview.transactions_relinked == 1
        moved_tx = (await async_session.execute(select(Transaction).where(Transaction.id == tx_id))).scalars().first()
        assert moved_tx.asset_event_id == surviving_event_id
        assert moved_tx.asset_id == target_id
        events = (await async_session.execute(select(AssetEvent).where(AssetEvent.asset_id == target_id))).scalars().all()
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_distinct_event_is_kept(self, async_session: AsyncSession, btp_pair):
        """AM-007: a coupon the target does not have must migrate, not vanish.

        The loyalty premium of a BTP is exactly this: an INTEREST event that only the
        placement asset knows about.
        """
        source_id, target_id = btp_pair
        async_session.add(AssetEvent(asset_id=target_id, date=date(2025, 3, 10), type=AssetEventType.INTEREST, value=Decimal("1.500000"), currency="EUR"))
        async_session.add(AssetEvent(asset_id=source_id, date=date(2033, 2, 28), type=AssetEventType.INTEREST, value=Decimal("8.000000"), currency="EUR"))
        await async_session.commit()

        result = await AssetCRUDService.merge_assets(source_id, target_id, async_session)

        assert result.preview.events == 1
        assert result.preview.events_discarded == 0
        events = (await async_session.execute(select(AssetEvent).where(AssetEvent.asset_id == target_id))).scalars().all()
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_provider_assignment_moves_when_target_has_none(self, async_session: AsyncSession, btp_pair):
        """AM-008: the target inherits pricing if it had none — a duplicate is often the configured one."""
        source_id, target_id = btp_pair
        async_session.add(
            AssetProviderAssignment(
                asset_id=source_id,
                provider_code="yfinance",
                identifier="BTP.MI",
                identifier_type=ProviderInputType.TICKER,
            )
        )
        await async_session.commit()

        result = await AssetCRUDService.merge_assets(source_id, target_id, async_session)

        assert result.preview.provider_assignment_moved is True
        assignment = (await async_session.execute(select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == target_id))).scalars().first()
        assert assignment is not None
        assert assignment.identifier == "BTP.MI"

    @pytest.mark.asyncio
    async def test_dropping_source_assignment_does_not_cascade_away_events(self, async_session: AsyncSession, btp_pair):
        """AM-009: the CASCADE trap.

        ``uq_asset_provider_asset_id`` forbids two assignments on the target, so the
        source's must go. But ``AssetEvent.provider_assignment_id`` cascades on delete:
        without re-pointing the migrated events first, the merge would destroy the very
        history it was asked to preserve.
        """
        source_id, target_id = btp_pair
        target_assignment = AssetProviderAssignment(asset_id=target_id, provider_code="yfinance", identifier="BTP.MI", identifier_type=ProviderInputType.TICKER)
        source_assignment = AssetProviderAssignment(asset_id=source_id, provider_code="yfinance", identifier="BTPCUM.MI", identifier_type=ProviderInputType.TICKER)
        async_session.add(target_assignment)
        async_session.add(source_assignment)
        await async_session.commit()
        await async_session.refresh(target_assignment)
        await async_session.refresh(source_assignment)
        kept_assignment_id, source_assignment_id = target_assignment.id, source_assignment.id

        async_session.add(
            AssetEvent(
                asset_id=source_id,
                date=date(2033, 2, 28),
                type=AssetEventType.INTEREST,
                value=Decimal("8.000000"),
                currency="EUR",
                provider_assignment_id=source_assignment_id,
            )
        )
        await async_session.commit()

        result = await AssetCRUDService.merge_assets(source_id, target_id, async_session)

        assert result.preview.provider_assignment_dropped is True
        events = (await async_session.execute(select(AssetEvent).where(AssetEvent.asset_id == target_id))).scalars().all()
        assert len(events) == 1, "the migrated event was cascade-deleted with the source assignment"
        assert events[0].provider_assignment_id == kept_assignment_id
        assignments = (await async_session.execute(select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id.in_([source_id, target_id])))).scalars().all()
        assert len(assignments) == 1

    @pytest.mark.asyncio
    async def test_dry_run_writes_nothing(self, async_session: AsyncSession, merge_broker: int, btp_pair):
        """AM-010: the confirmation dialog needs real counts before anything is destroyed."""
        source_id, target_id = btp_pair
        async_session.add(
            Transaction(
                broker_id=merge_broker,
                asset_id=source_id,
                type=TransactionType.BUY,
                date=date(2025, 3, 10),
                quantity=Decimal("100"),
                amount=Decimal("-10000"),
                currency="EUR",
            )
        )
        await async_session.commit()

        result = await AssetCRUDService.merge_assets(source_id, target_id, async_session, dry_run=True)

        assert result.dry_run is True
        assert result.preview.transactions == 1
        assert "IT0005634792" in result.preview.identifiers_added
        still_there = await _get_asset(async_session, source_id)
        assert still_there is not None
        assert still_there.identifier_isin == "IT0005634792"
        target = await _get_asset(async_session, target_id)
        assert target.identifier_other in (None, [])

    @pytest.mark.asyncio
    async def test_same_asset_is_refused(self, async_session: AsyncSession, btp_pair):
        """AM-011: merging an asset into itself would delete it — refuse outright."""
        _source_id, target_id = btp_pair

        with pytest.raises(AssetSourceError) as exc:
            await AssetCRUDService.merge_assets(target_id, target_id, async_session)
        assert exc.value.error_code == "SAME_ASSET"

    @pytest.mark.asyncio
    async def test_missing_asset_is_refused(self, async_session: AsyncSession, btp_pair):
        """AM-012: an unknown id must not partially apply the merge."""
        source_id, _target_id = btp_pair

        with pytest.raises(AssetSourceError) as exc:
            await AssetCRUDService.merge_assets(source_id, 99_999_999, async_session)
        assert exc.value.error_code == "NOT_FOUND"
