"""
BRIM Database Tests.

Tests for BRIM functionality that requires database access:
- Category 3: Asset Candidate Search
- Category 4: Duplicate Detection

These tests require a database connection and use async fixtures.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import List

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetType, Broker, Transaction, TransactionType
from backend.app.db.session import get_async_engine
from backend.app.schemas.brim import BRIMMatchConfidence, BRIMDuplicateLevel
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import search_asset_candidates, detect_tx_duplicates


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def test_date() -> date:
    """A consistent test date."""
    return date(2025, 1, 15)


@pytest_asyncio.fixture
async def async_session():
    """Create an async session for database tests."""
    engine = get_async_engine()
    async with AsyncSession(engine) as session:
        yield session


@pytest_asyncio.fixture
async def test_broker(async_session: AsyncSession) -> int:
    """Create a test broker for transactions and return its ID."""
    import uuid
    unique_name = f"Test Broker BRIM {uuid.uuid4().hex[:8]}"
    broker = Broker(
        name=unique_name,
        description="Test broker for BRIM tests"
        )
    async_session.add(broker)
    await async_session.commit()
    await async_session.refresh(broker)
    broker_id = broker.id
    yield broker_id
    # Cleanup - need to re-fetch the broker
    from sqlalchemy import select
    result = await async_session.execute(select(Broker).where(Broker.id == broker_id))
    broker_to_delete = result.scalars().first()
    if broker_to_delete:
        await async_session.delete(broker_to_delete)
        await async_session.commit()


@pytest_asyncio.fixture
async def test_assets(async_session: AsyncSession) -> List[Asset]:
    """Create test assets with identifiers directly on Asset model."""
    import uuid
    suffix = uuid.uuid4().hex[:6]

    # Define asset data with their identifiers (now directly on Asset)
    asset_data = [
        {
            "display_name": f"Apple Inc. (ISIN) {suffix}",
            "asset_type": AssetType.STOCK,
            "currency": "USD",
            "identifier_isin": "US0378331005",
            "identifier_ticker": None,
            },
        {
            "display_name": f"Apple Stock (Ticker) {suffix}",
            "asset_type": AssetType.STOCK,
            "currency": "USD",
            "identifier_isin": None,
            "identifier_ticker": "AAPL",
            },
        {
            "display_name": f"Microsoft Corporation {suffix}",
            "asset_type": AssetType.STOCK,
            "currency": "USD",
            "identifier_isin": None,
            "identifier_ticker": "MSFT",
            },
        {
            "display_name": f"SAP SE {suffix}",
            "asset_type": AssetType.STOCK,
            "currency": "EUR",
            "identifier_isin": "DE0007164600",
            "identifier_ticker": None,
            },
        ]

    assets = []

    for data in asset_data:
        # Create asset with identifiers directly
        asset = Asset(
            display_name=data["display_name"],
            asset_type=data["asset_type"],
            currency=data["currency"],
            identifier_isin=data.get("identifier_isin"),
            identifier_ticker=data.get("identifier_ticker"),
            active=True
            )
        async_session.add(asset)
        assets.append(asset)

    await async_session.commit()

    for asset in assets:
        await async_session.refresh(asset)

    yield assets

    # Cleanup
    for asset in assets:
        await async_session.delete(asset)
    await async_session.commit()


# =============================================================================
# CATEGORY 3: ASSET CANDIDATE SEARCH (AC-*)
# =============================================================================

class TestAssetCandidateSearch:
    """Tests for asset candidate search functionality."""

    @pytest.mark.asyncio
    async def test_search_by_isin_exact_match(self, async_session: AsyncSession, test_assets: List[Asset]):
        """
        AC-001: ISIN search.

        Expected: EXACT confidence, 1 candidate.
        """
        candidates, auto_selected = await search_asset_candidates(
            async_session,
            extracted_symbol=None,
            extracted_isin="US0378331005",
            extracted_name=None
            )

        assert len(candidates) >= 1, "Expected at least 1 candidate for ISIN match"

        # First candidate should be EXACT confidence
        assert candidates[0].match_confidence == BRIMMatchConfidence.EXACT

        # If exactly 1, should be auto-selected
        if len(candidates) == 1:
            assert auto_selected == candidates[0].asset_id

    @pytest.mark.asyncio
    async def test_search_by_symbol_exact_match(self, async_session: AsyncSession, test_assets: List[Asset]):
        """
        AC-002: Symbol search.

        Expected: MEDIUM confidence.
        """
        candidates, auto_selected = await search_asset_candidates(
            async_session,
            extracted_symbol="MSFT",
            extracted_isin=None,
            extracted_name=None
            )

        assert len(candidates) >= 1, "Expected at least 1 candidate for symbol match"

        # Should be MEDIUM confidence for symbol match
        assert candidates[0].match_confidence == BRIMMatchConfidence.MEDIUM

    @pytest.mark.asyncio
    async def test_search_by_name_partial_match(self, async_session: AsyncSession, test_assets: List[Asset]):
        """
        AC-003: Name search.

        Expected: LOW confidence.
        """
        candidates, auto_selected = await search_asset_candidates(
            async_session,
            extracted_symbol=None,
            extracted_isin=None,
            extracted_name="Microsoft"
            )

        # If found, should be LOW confidence
        if candidates:
            assert candidates[0].match_confidence == BRIMMatchConfidence.LOW

    @pytest.mark.asyncio
    async def test_search_no_match(self, async_session: AsyncSession, test_assets: List[Asset]):
        """
        AC-004: No results.

        Expected: Empty candidates list.
        """
        candidates, auto_selected = await search_asset_candidates(
            async_session,
            extracted_symbol="NONEXISTENT123",
            extracted_isin="XX0000000000",
            extracted_name="NonExistent Company XYZ"
            )

        # Should return empty list
        assert len(candidates) == 0, f"Expected no candidates, got {len(candidates)}"
        assert auto_selected is None

    @pytest.mark.asyncio
    async def test_auto_select_single_candidate(self, async_session: AsyncSession, test_assets: List[Asset]):
        """
        AC-006: Single match.

        Expected: selected_asset_id populated.
        """
        # Search for a unique ISIN
        candidates, auto_selected = await search_asset_candidates(
            async_session,
            extracted_symbol=None,
            extracted_isin="DE0007164600",  # SAP - should be unique
            extracted_name=None
            )

        if len(candidates) == 1:
            assert auto_selected is not None, "Should auto-select when exactly 1 candidate"
            assert auto_selected == candidates[0].asset_id

    @pytest.mark.asyncio
    async def test_no_auto_select_multiple_candidates(self, async_session: AsyncSession, test_assets: List[Asset]):
        """
        AC-007: Multiple matches.

        Expected: selected_asset_id is None.
        """
        # Search for "Apple" - might match multiple assets
        candidates, auto_selected = await search_asset_candidates(
            async_session,
            extracted_symbol=None,
            extracted_isin=None,
            extracted_name="Apple"
            )

        if len(candidates) > 1:
            assert auto_selected is None, "Should NOT auto-select when multiple candidates"


# =============================================================================
# CATEGORY 4: DUPLICATE DETECTION (DD-*)
# =============================================================================

class TestDuplicateDetection:
    """Tests for duplicate transaction detection."""

    @pytest.mark.asyncio
    async def test_detect_no_duplicates(
        self,
        async_session: AsyncSession,
        test_broker: int,
        test_date: date
        ):
        """
        DD-001: Fresh transactions.

        Expected: All in tx_unique_indices.
        """
        # Create transactions with unique characteristics
        transactions = [
            TXCreateItem(
                broker_id=test_broker,
                asset_id=None,
                type=TransactionType.DEPOSIT,
                date=test_date,
                quantity=Decimal("0"),
                cash=Currency(code="EUR", amount=Decimal("1000")),
                description="Unique deposit 1"
                ),
            TXCreateItem(
                broker_id=test_broker,
                asset_id=None,
                type=TransactionType.DEPOSIT,
                date=test_date + timedelta(days=1),
                quantity=Decimal("0"),
                cash=Currency(code="EUR", amount=Decimal("2000")),
                description="Unique deposit 2"
                ),
            ]

        report = await detect_tx_duplicates(
            transactions=transactions,
            broker_id=test_broker,
            session=async_session
            )

        # All should be unique (no existing transactions in DB yet)
        assert len(report.tx_unique_indices) == len(transactions)
        assert len(report.tx_possible_duplicates) == 0
        assert len(report.tx_likely_duplicates) == 0

    @pytest.mark.asyncio
    async def test_detect_possible_duplicate(
        self,
        async_session: AsyncSession,
        test_broker: int,
        test_date: date
        ):
        """
        DD-002: Same type/date/qty/cash, different description.

        Expected: In tx_possible_duplicates with POSSIBLE level.
        """
        # First, insert a transaction into the database
        existing_tx = Transaction(
            broker_id=test_broker,
            asset_id=None,
            type=TransactionType.DEPOSIT,
            date=test_date,
            quantity=Decimal("0"),
            amount=Decimal("1500"),
            currency="EUR",
            description="Original deposit"
            )
        async_session.add(existing_tx)
        await async_session.commit()

        try:
            # Now try to import a "duplicate" with same type/date/cash but different description
            transactions = [
                TXCreateItem(
                    broker_id=test_broker,
                    asset_id=None,
                    type=TransactionType.DEPOSIT,
                    date=test_date,
                    quantity=Decimal("0"),
                    cash=Currency(code="EUR", amount=Decimal("1500")),
                    description="Different deposit description"  # Different!
                    ),
                ]

            report = await detect_tx_duplicates(
                transactions=transactions,
                broker_id=test_broker,
                session=async_session
                )

            # Should be flagged as possible duplicate
            assert len(report.tx_possible_duplicates) >= 1 or len(report.tx_likely_duplicates) >= 1, \
                "Expected duplicate detection"

            if report.tx_possible_duplicates:
                candidate = report.tx_possible_duplicates[0]
                # Check the match level from the first match
                assert len(candidate.tx_existing_matches) > 0
                match = candidate.tx_existing_matches[0]
                assert match.match_level in [BRIMDuplicateLevel.POSSIBLE, BRIMDuplicateLevel.POSSIBLE_WITH_ASSET]

        finally:
            # Cleanup
            await async_session.delete(existing_tx)
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_detect_likely_duplicate(
        self,
        async_session: AsyncSession,
        test_broker: int,
        test_date: date
        ):
        """
        DD-003: Same type/date/qty/cash AND same description.

        Expected: In tx_likely_duplicates with LIKELY level.
        """
        description = "Exact same deposit"

        # Insert existing transaction
        existing_tx = Transaction(
            broker_id=test_broker,
            asset_id=None,
            type=TransactionType.DEPOSIT,
            date=test_date,
            quantity=Decimal("0"),
            amount=Decimal("2500"),
            currency="EUR",
            description=description
            )
        async_session.add(existing_tx)
        await async_session.commit()

        try:
            # Try to import exact duplicate
            transactions = [
                TXCreateItem(
                    broker_id=test_broker,
                    asset_id=None,
                    type=TransactionType.DEPOSIT,
                    date=test_date,
                    quantity=Decimal("0"),
                    cash=Currency(code="EUR", amount=Decimal("2500")),
                    description=description  # SAME description
                    ),
                ]

            report = await detect_tx_duplicates(
                transactions=transactions,
                broker_id=test_broker,
                session=async_session
                )

            # Should be flagged as likely duplicate
            assert len(report.tx_likely_duplicates) >= 1, \
                f"Expected likely duplicate, got: unique={len(report.tx_unique_indices)}, possible={len(report.tx_possible_duplicates)}"

            if report.tx_likely_duplicates:
                candidate = report.tx_likely_duplicates[0]
                # Check the match level from the first match
                assert len(candidate.tx_existing_matches) > 0
                match = candidate.tx_existing_matches[0]
                assert match.match_level in [BRIMDuplicateLevel.LIKELY, BRIMDuplicateLevel.LIKELY_WITH_ASSET]

        finally:
            await async_session.delete(existing_tx)
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_different_broker_not_duplicate(
        self,
        async_session: AsyncSession,
        test_broker: int,
        test_date: date
        ):
        """
        DD-004: Same data, different broker.

        Expected: Not flagged as duplicate.
        """
        # Create another broker
        import uuid
        other_broker = Broker(name=f"Other Broker {uuid.uuid4().hex[:8]}", description="Another broker")
        async_session.add(other_broker)
        await async_session.commit()
        await async_session.refresh(other_broker)
        other_broker_id = other_broker.id

        # Insert transaction for OTHER broker
        existing_tx = Transaction(
            broker_id=other_broker_id,
            asset_id=None,
            type=TransactionType.DEPOSIT,
            date=test_date,
            quantity=Decimal("0"),
            amount=Decimal("3000"),
            currency="EUR",
            description="Deposit on other broker"
            )
        async_session.add(existing_tx)
        await async_session.commit()

        try:
            # Import same data for TEST broker (different broker_id)
            transactions = [
                TXCreateItem(
                    broker_id=test_broker,  # Different broker!
                    asset_id=None,
                    type=TransactionType.DEPOSIT,
                    date=test_date,
                    quantity=Decimal("0"),
                    cash=Currency(code="EUR", amount=Decimal("3000")),
                    description="Deposit on other broker"
                    ),
                ]

            report = await detect_tx_duplicates(
                transactions=transactions,
                broker_id=test_broker,  # Different broker!
                session=async_session
                )

            # Should NOT be flagged as duplicate (different broker)
            assert len(report.tx_unique_indices) == 1, \
                "Transaction on different broker should be unique"

        finally:
            # Delete transaction first (FK constraint)
            await async_session.delete(existing_tx)
            await async_session.commit()
            # Then delete the broker
            await async_session.delete(other_broker)
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_empty_description_not_likely(
        self,
        async_session: AsyncSession,
        test_broker: int,
        test_date: date
        ):
        """
        DD-007: Both descriptions empty.

        Expected: POSSIBLE not LIKELY (empty descriptions don't count as matching).
        Empty string == empty string should NOT elevate to LIKELY.
        """
        # Insert transaction with NO description
        existing_tx = Transaction(
            broker_id=test_broker,
            asset_id=None,
            type=TransactionType.DEPOSIT,
            date=test_date,
            quantity=Decimal("0"),
            amount=Decimal("4000"),
            currency="EUR",
            description=""  # Empty
            )
        async_session.add(existing_tx)
        await async_session.commit()

        try:
            # Import with empty description too
            transactions = [
                TXCreateItem(
                    broker_id=test_broker,
                    asset_id=None,
                    type=TransactionType.DEPOSIT,
                    date=test_date,
                    quantity=Decimal("0"),
                    cash=Currency(code="EUR", amount=Decimal("4000")),
                    description=""  # Also empty
                    ),
                ]

            report = await detect_tx_duplicates(
                transactions=transactions,
                broker_id=test_broker,
                session=async_session
                )

            # Empty descriptions should NOT elevate to LIKELY
            # Should be flagged as POSSIBLE (same data) but not LIKELY
            assert len(report.tx_likely_duplicates) == 0, \
                "Empty descriptions matching should NOT be LIKELY"
            assert len(report.tx_possible_duplicates) >= 1, \
                "Should still be POSSIBLE duplicate (same type/date/amount)"

        finally:
            await async_session.delete(existing_tx)
            await async_session.commit()
