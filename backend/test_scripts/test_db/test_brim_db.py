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
from pathlib import Path
from typing import List

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetType, Broker, Transaction, TransactionType
from backend.app.db.session import get_async_engine
from backend.app.schemas.brim import BRIMDuplicateLevel, BRIMMatchConfidence
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.services.brim.candidates import search_asset_candidates
from backend.app.services.brim.duplicates import detect_tx_duplicates

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
    import uuid  # noqa: PLC0415 — test setup — imports after sys.path/db config

    unique_name = f"Test Broker BRIM {uuid.uuid4().hex[:8]}"
    broker = Broker(name=unique_name, description="Test broker for BRIM tests")
    async_session.add(broker)
    await async_session.commit()
    await async_session.refresh(broker)
    broker_id = broker.id
    yield broker_id
    # Cleanup - need to re-fetch the broker
    from sqlalchemy import select  # noqa: PLC0415 — test setup — imports after sys.path/db config

    result = await async_session.execute(select(Broker).where(Broker.id == broker_id))
    broker_to_delete = result.scalars().first()
    if broker_to_delete:
        await async_session.delete(broker_to_delete)
        await async_session.commit()


@pytest_asyncio.fixture
async def test_assets(async_session: AsyncSession) -> List[Asset]:
    """Create test assets with identifiers directly on Asset model."""
    import uuid  # noqa: PLC0415 — test setup — imports after sys.path/db config

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
            active=True,
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
        candidates, auto_selected = await search_asset_candidates(async_session, extracted_symbol=None, extracted_isin="US0378331005", extracted_name=None)

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
        candidates, auto_selected = await search_asset_candidates(async_session, extracted_symbol="MSFT", extracted_isin=None, extracted_name=None)

        assert len(candidates) >= 1, "Expected at least 1 candidate for symbol match"

        # Should be MEDIUM confidence for symbol match
        assert candidates[0].match_confidence == BRIMMatchConfidence.MEDIUM

    @pytest.mark.asyncio
    async def test_search_by_name_partial_match(self, async_session: AsyncSession, test_assets: List[Asset]):
        """
        AC-003: Name search.

        Expected: LOW confidence.
        """
        candidates, auto_selected = await search_asset_candidates(async_session, extracted_symbol=None, extracted_isin=None, extracted_name="Microsoft")

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
            extracted_name="NonExistent Company XYZ",
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
            extracted_name=None,
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
        candidates, auto_selected = await search_asset_candidates(async_session, extracted_symbol=None, extracted_isin=None, extracted_name="Apple")

        if len(candidates) > 1:
            assert auto_selected is None, "Should NOT auto-select when multiple candidates"

    @pytest.mark.asyncio
    async def test_search_by_soft_identifier_other(self, async_session: AsyncSession):
        """
        AC-008: Soft-identifier match against the identifier_other JSON list.

        An asset whose ISIN / soft broker label lives only in identifier_other (not in a
        dedicated column) is still detected — HIGH for an ISIN hit, and found for a soft
        name hit. Exercises the additive JSON-list search.
        """
        import uuid  # noqa: PLC0415 — test setup — imports after sys.path/db config

        suffix = uuid.uuid4().hex[:8].upper()
        soft_isin = f"SOFT{suffix}00"
        soft_name = f"BTP 1/12/2026 {suffix} 1.25%"
        asset = Asset(
            display_name=f"Opaque Bond {suffix}",
            asset_type=AssetType.BOND,
            currency="EUR",
            identifier_isin=None,
            identifier_ticker=None,
            identifier_other=[soft_name, soft_isin],
            active=True,
        )
        async_session.add(asset)
        await async_session.commit()
        await async_session.refresh(asset)

        try:
            # ISIN present only in identifier_other → HIGH soft match (P3/A-01: an ISIN
            # deliberately stored among the alternate identifiers outranks name similarity).
            candidates, auto_selected = await search_asset_candidates(async_session, extracted_symbol=None, extracted_isin=soft_isin, extracted_name=None)
            assert any(c.asset_id == asset.id for c in candidates), "ISIN in identifier_other should match"
            matched = next(c for c in candidates if c.asset_id == asset.id)
            assert matched.match_confidence == BRIMMatchConfidence.HIGH
            assert auto_selected == asset.id

            # Soft broker label present only in identifier_other → detected via the list search.
            candidates_name, _ = await search_asset_candidates(async_session, extracted_symbol=None, extracted_isin=None, extracted_name=soft_name)
            assert any(c.asset_id == asset.id for c in candidates_name), "Soft name in identifier_other should match"
        finally:
            await async_session.delete(asset)
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_soft_isin_is_not_shadowed_by_name_match(self, async_session: AsyncSession):
        """
        AC-009 (P3/A-01): an ISIN stored in identifier_other must win over a name match.

        This is the Italian BTP "CUM" scenario that broke beta testing. The security is
        issued with a non-tradeable ISIN (kept in identifier_other) and traded under a
        different, quoted one (identifier_isin). A reimport quotes the CUM ISIN plus a
        generic name.

        Before the fix the alternate-identifier lookup ran last and only ``if not
        candidates``, so the weak name match fired first, filled the list, and the correct
        asset was never even considered — the user was offered a wrong candidate instead.
        """
        import uuid  # noqa: PLC0415 — test setup — imports after sys.path/db config

        suffix = uuid.uuid4().hex[:8].upper()
        cum_isin = f"IT{suffix}CUM1"
        market_isin = f"IT{suffix}MKT1"
        shared_name_token = f"BTPTEST{suffix}"

        # The right asset: quoted ISIN primary, CUM ISIN kept as an alternate.
        target = Asset(
            display_name=f"{shared_name_token} Piu Scad Fb33",
            asset_type=AssetType.BOND,
            currency="EUR",
            identifier_isin=market_isin,
            identifier_other=[cum_isin],
            active=True,
        )
        # A decoy sharing the name token — enough to win a partial name match.
        decoy = Asset(
            display_name=f"{shared_name_token} Italia Nov30",
            asset_type=AssetType.BOND,
            currency="EUR",
            active=True,
        )
        async_session.add(target)
        async_session.add(decoy)
        await async_session.commit()
        await async_session.refresh(target)
        await async_session.refresh(decoy)

        try:
            candidates, auto_selected = await search_asset_candidates(
                async_session,
                extracted_symbol=None,
                extracted_isin=cum_isin,
                extracted_name=shared_name_token,
            )

            assert len(candidates) == 1, f"The alternate-ISIN hit must be the only candidate, got {[(c.asset_id, c.match_confidence) for c in candidates]}"
            assert candidates[0].asset_id == target.id
            assert candidates[0].match_confidence == BRIMMatchConfidence.HIGH
            assert auto_selected == target.id, "A single strong candidate must be auto-selected"
            assert all(c.asset_id != decoy.id for c in candidates), "The name-only decoy must not surface"
        finally:
            await async_session.delete(target)
            await async_session.delete(decoy)
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_primary_and_alternate_isin_both_surface(self, async_session: AsyncSession):
        """
        AC-010 (P3/A-01): the same ISIN primary on one asset and alternate on another
        surfaces **both** candidates — that pair is almost always a duplicate to merge.

        Priorities 1 and 2 deliberately run together (no ``if not candidates`` guard), so
        the user sees them side by side, which is where merging costs the fewest clicks.
        """
        import uuid  # noqa: PLC0415 — test setup — imports after sys.path/db config

        suffix = uuid.uuid4().hex[:8].upper()
        isin = f"IT{suffix}DUP1"

        primary = Asset(display_name=f"Dup Primary {suffix}", asset_type=AssetType.BOND, currency="EUR", identifier_isin=isin, active=True)
        alternate = Asset(display_name=f"Dup Alternate {suffix}", asset_type=AssetType.BOND, currency="EUR", identifier_other=[isin], active=True)
        async_session.add(primary)
        async_session.add(alternate)
        await async_session.commit()
        await async_session.refresh(primary)
        await async_session.refresh(alternate)

        try:
            candidates, auto_selected = await search_asset_candidates(async_session, extracted_symbol=None, extracted_isin=isin, extracted_name=None)

            by_id = {c.asset_id: c for c in candidates}
            assert primary.id in by_id, "Primary-column ISIN holder must be a candidate"
            assert alternate.id in by_id, "Alternate-list ISIN holder must be a candidate too"
            assert by_id[primary.id].match_confidence == BRIMMatchConfidence.EXACT
            assert by_id[alternate.id].match_confidence == BRIMMatchConfidence.HIGH
            assert auto_selected is None, "Two candidates → the user must choose (and can merge)"
        finally:
            await async_session.delete(primary)
            await async_session.delete(alternate)
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_ticker_still_wins_over_name(self, async_session: AsyncSession):
        """
        AC-011 (P3/A-01 regression guard): reordering the ISIN lookups must not disturb
        the ticker → name ordering below them.
        """
        import uuid  # noqa: PLC0415 — test setup — imports after sys.path/db config

        suffix = uuid.uuid4().hex[:8].upper()
        ticker = f"TK{suffix}"

        asset = Asset(display_name=f"Ticker Holder {suffix}", asset_type=AssetType.STOCK, currency="USD", identifier_ticker=ticker, active=True)
        async_session.add(asset)
        await async_session.commit()
        await async_session.refresh(asset)

        try:
            candidates, auto_selected = await search_asset_candidates(async_session, extracted_symbol=ticker, extracted_isin=None, extracted_name=f"Ticker Holder {suffix}")
            assert len(candidates) == 1
            assert candidates[0].asset_id == asset.id
            assert candidates[0].match_confidence == BRIMMatchConfidence.MEDIUM, "A ticker hit must stay MEDIUM and pre-empt the name search"
            assert auto_selected == asset.id
        finally:
            await async_session.delete(asset)
            await async_session.commit()


# =============================================================================
# CATEGORY 4: DUPLICATE DETECTION (DD-*)
# =============================================================================


class TestDuplicateDetection:
    """Tests for duplicate transaction detection."""

    @pytest.mark.asyncio
    async def test_detect_no_duplicates(self, async_session: AsyncSession, test_broker: int, test_date: date):
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
                description="Unique deposit 1",
            ),
            TXCreateItem(
                broker_id=test_broker,
                asset_id=None,
                type=TransactionType.DEPOSIT,
                date=test_date + timedelta(days=1),
                quantity=Decimal("0"),
                cash=Currency(code="EUR", amount=Decimal("2000")),
                description="Unique deposit 2",
            ),
        ]

        report = await detect_tx_duplicates(transactions=transactions, broker_id=test_broker, session=async_session)

        # All should be unique (no existing transactions in DB yet)
        assert len(report.tx_unique_indices) == len(transactions)
        assert len(report.tx_possible_duplicates) == 0
        assert len(report.tx_likely_duplicates) == 0

    @pytest.mark.asyncio
    async def test_detect_possible_duplicate(self, async_session: AsyncSession, test_broker: int, test_date: date):
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
            description="Original deposit",
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
                    description="Different deposit description",  # Different!
                ),
            ]

            report = await detect_tx_duplicates(transactions=transactions, broker_id=test_broker, session=async_session)

            # Should be flagged as possible duplicate
            assert len(report.tx_possible_duplicates) >= 1 or len(report.tx_likely_duplicates) >= 1, "Expected duplicate detection"

            if report.tx_possible_duplicates:
                candidate = report.tx_possible_duplicates[0]
                # Check the match level from the first match
                assert len(candidate.tx_existing_matches) > 0
                match = candidate.tx_existing_matches[0]
                assert match.match_level in [
                    BRIMDuplicateLevel.POSSIBLE,
                    BRIMDuplicateLevel.POSSIBLE_WITH_ASSET,
                ]

        finally:
            # Cleanup
            await async_session.delete(existing_tx)
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_row_already_imported_without_asset_is_still_a_duplicate(self, async_session: AsyncSession, test_broker: int, test_date: date, test_assets: List[Asset]):
        """The same movement, imported before the plugin could attach its instrument.

        Filtering candidates strictly by asset_id hides it, so the improved parse offers
        the identical row back as brand new — and every re-import silently doubles those
        fees. The row must still be found, and the exact description makes it certain.
        """
        description = "SPESE STACCO CEDOLA DEL 01/06/2026 TIT: IT0000000001"
        linked_asset_id = test_assets[0].id  # read before the commit expires the instance
        existing_tx = Transaction(
            broker_id=test_broker,
            asset_id=None,  # imported before the plugin learned to link charges
            type=TransactionType.FEE,
            date=test_date,
            quantity=Decimal("0"),
            amount=Decimal("-1.50"),
            currency="EUR",
            description=description,
        )
        async_session.add(existing_tx)
        await async_session.commit()

        try:
            transactions = [
                TXCreateItem(
                    broker_id=test_broker,
                    asset_id=linked_asset_id,  # now attached to the bond it was charged on
                    type=TransactionType.FEE,
                    date=test_date,
                    quantity=Decimal("0"),
                    cash=Currency(code="EUR", amount=Decimal("-1.50")),
                    description=description,
                ),
            ]

            report = await detect_tx_duplicates(transactions=transactions, broker_id=test_broker, session=async_session)

            assert len(report.tx_likely_duplicates) == 1, f"Expected a likely duplicate, got unique={len(report.tx_unique_indices)}, possible={len(report.tx_possible_duplicates)}"
            # LIKELY, not LIKELY_WITH_ASSET: the stored row carries no asset to agree on.
            assert report.tx_likely_duplicates[0].tx_existing_matches[0].match_level == BRIMDuplicateLevel.LIKELY

        finally:
            await async_session.delete(existing_tx)
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_detect_likely_duplicate_ignores_whitespace_in_description(self, async_session: AsyncSession, test_broker: int, test_date: date):
        """Re-wrapped text is the same text: whitespace must not demote a certain duplicate.

        Banks re-flow descriptions between exports (observed on Crédit Agricole:
        "DT EMISS." in one file, "DTEMISS." in another). Compared raw, the identical
        movement comes back as merely *possible* and the user is asked to arbitrate a
        difference that does not exist — the fastest way to make them stop reading.
        """
        existing_tx = Transaction(
            broker_id=test_broker,
            asset_id=None,
            type=TransactionType.WITHDRAWAL,
            date=test_date,
            quantity=Decimal("0"),
            amount=Decimal("-58.44"),
            currency="EUR",
            description="SDD A : AE S.P.A. FT NR. 0000822402279877 DTEMISS. 202411",
        )
        async_session.add(existing_tx)
        await async_session.commit()

        try:
            transactions = [
                TXCreateItem(
                    broker_id=test_broker,
                    asset_id=None,
                    type=TransactionType.WITHDRAWAL,
                    date=test_date,
                    quantity=Decimal("0"),
                    cash=Currency(code="EUR", amount=Decimal("-58.44")),
                    description="SDD A : AE S.P.A. FT NR. 0000822402279877 DT EMISS. 202411",
                ),
            ]

            report = await detect_tx_duplicates(transactions=transactions, broker_id=test_broker, session=async_session)

            assert len(report.tx_likely_duplicates) == 1, f"Expected a likely duplicate, got possible={len(report.tx_possible_duplicates)}"
            assert report.tx_likely_duplicates[0].tx_existing_matches[0].match_level in (
                BRIMDuplicateLevel.LIKELY,
                BRIMDuplicateLevel.LIKELY_WITH_ASSET,
            )

        finally:
            await async_session.delete(existing_tx)
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_detect_likely_duplicate(self, async_session: AsyncSession, test_broker: int, test_date: date):
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
            description=description,
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
                    description=description,  # SAME description
                ),
            ]

            report = await detect_tx_duplicates(transactions=transactions, broker_id=test_broker, session=async_session)

            # Should be flagged as likely duplicate
            assert len(report.tx_likely_duplicates) >= 1, f"Expected likely duplicate, got: unique={len(report.tx_unique_indices)}, possible={len(report.tx_possible_duplicates)}"

            if report.tx_likely_duplicates:
                candidate = report.tx_likely_duplicates[0]
                # Check the match level from the first match
                assert len(candidate.tx_existing_matches) > 0
                match = candidate.tx_existing_matches[0]
                assert match.match_level in [
                    BRIMDuplicateLevel.LIKELY,
                    BRIMDuplicateLevel.LIKELY_WITH_ASSET,
                ]

        finally:
            await async_session.delete(existing_tx)
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_different_broker_not_duplicate(self, async_session: AsyncSession, test_broker: int, test_date: date):
        """
        DD-004: Same data, different broker.

        Expected: Not flagged as duplicate.
        """
        # Create another broker
        import uuid  # noqa: PLC0415 — test setup — imports after sys.path/db config

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
            description="Deposit on other broker",
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
                    description="Deposit on other broker",
                ),
            ]

            report = await detect_tx_duplicates(
                transactions=transactions,
                broker_id=test_broker,  # Different broker!
                session=async_session,
            )

            # Should NOT be flagged as duplicate (different broker)
            assert len(report.tx_unique_indices) == 1, "Transaction on different broker should be unique"

        finally:
            # Delete transaction first (FK constraint)
            await async_session.delete(existing_tx)
            await async_session.commit()
            # Then delete the broker
            await async_session.delete(other_broker)
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_empty_description_not_likely(self, async_session: AsyncSession, test_broker: int, test_date: date):
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
            description="",  # Empty
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
                    description="",  # Also empty
                ),
            ]

            report = await detect_tx_duplicates(transactions=transactions, broker_id=test_broker, session=async_session)

            # Empty descriptions should NOT elevate to LIKELY
            # Should be flagged as POSSIBLE (same data) but not LIKELY
            assert len(report.tx_likely_duplicates) == 0, "Empty descriptions matching should NOT be LIKELY"
            assert len(report.tx_possible_duplicates) >= 1, "Should still be POSSIBLE duplicate (same type/date/amount)"

        finally:
            await async_session.delete(existing_tx)
            await async_session.commit()


# =============================================================================
# CATEGORY 4b: DUPLICATES OF A MERGED PAIR (DD-011 … DD-017)
# =============================================================================
#
# A WITHDRAWAL and a DEPOSIT merged by a promote become the two legs of a CASH_TRANSFER (two brokers) or of an
# FX_CONVERSION (two currencies), each leg carrying both descriptions joined by a newline (promoteHelpers.mergeStrings).
# An export "since the last one" re-delivers the last day it covered, so the same movement comes back as a plain
# DEPOSIT or WITHDRAWAL: found on its merged leg it is a duplicate; missed, it is offered back as new and the cash
# doubles (plan 37, §9). Red while candidates had to share the incoming type, except DD-016, the guard of the
# same-type rule, which is green on both sides of the change.

TRANSFER_OUT_TEXT = "Interner Übertrag · id SYNTHC0000000000000005"  # the sending account's side, as its export writes it
TRANSFER_IN_TEXT = "Interner Übertrag · id synthD0000000000000003"  # the receiving account's side
MERGED_TRANSFER_TEXT = f"{TRANSFER_OUT_TEXT}\n{TRANSFER_IN_TEXT}"  # what a merge leaves on both legs


def _cash_item(broker_id: int, tx_type: TransactionType, day: date, amount: str, description: str | None, currency: str = "EUR") -> TXCreateItem:
    """A parsed cash row without an instrument, as a plugin hands it to the duplicate check."""
    return TXCreateItem(broker_id=broker_id, asset_id=None, type=tx_type, date=day, quantity=Decimal("0"), cash=Currency(code=currency, amount=Decimal(amount)), description=description)


async def _save_merged_pair(session: AsyncSession, tx_type: TransactionType, day: date, legs: List[tuple]) -> List[int]:
    """Two saved legs of ``tx_type`` pointing at each other, as a promote leaves a merged pair; returns their ids.

    ``legs`` holds two ``(broker_id, amount, currency, description)``. Both links are written before the commit: the
    foreign key of ``related_transaction_id`` is deferred.
    """
    rows = [Transaction(broker_id=broker_id, asset_id=None, type=tx_type, date=day, quantity=Decimal("0"), amount=Decimal(amount), currency=currency, description=description, tags="import,scalable") for broker_id, amount, currency, description in legs]
    session.add_all(rows)
    await session.flush()
    rows[0].related_transaction_id, rows[1].related_transaction_id = rows[1].id, rows[0].id
    ids = [row.id for row in rows]  # read before the commit expires the instances
    await session.commit()
    return ids


async def _save_merged_transfer(session: AsyncSession, broker_id: int, partner_id: int, day: date, amount: str, description: str = MERGED_TRANSFER_TEXT) -> List[int]:
    """A merged CASH_TRANSFER: ``amount`` EUR on ``broker_id``, the opposite on ``partner_id``; returns [its leg, the partner's leg]."""
    return await _save_merged_pair(session, TransactionType.CASH_TRANSFER, day, [(broker_id, amount, "EUR", description), (partner_id, str(-Decimal(amount)), "EUR", description)])


async def _delete_transactions(session: AsyncSession, ids: List[int]) -> None:
    """Whoever writes cleans up: the links first, then the rows."""
    from sqlalchemy import delete, update  # noqa: PLC0415 — test setup — imports after sys.path/db config

    await session.execute(update(Transaction).where(Transaction.id.in_(ids)).values(related_transaction_id=None))
    await session.execute(delete(Transaction).where(Transaction.id.in_(ids)))
    await session.commit()


def _matches(candidate) -> list:
    """``(existing id, its type, level)`` of every saved row a parsed row was matched with."""
    return [(match.existing_tx_id, match.tx_type, match.match_level) for match in candidate.tx_existing_matches]


def _verdicts(report) -> dict:
    """``{row index: (category, matches)}`` for every row of a duplicate report: the whole verdict, in one comparable value."""
    verdicts = {index: ("unique", []) for index in report.tx_unique_indices}
    verdicts.update({candidate.tx_row_index: ("possible", _matches(candidate)) for candidate in report.tx_possible_duplicates})
    verdicts.update({candidate.tx_row_index: ("likely", _matches(candidate)) for candidate in report.tx_likely_duplicates})
    return verdicts


class TestMergedPairDuplicates:
    """A deposit or a withdrawal imported again after a promote merged it into a pair (plan 37, §9)."""

    @pytest_asyncio.fixture
    async def partner_broker(self, async_session: AsyncSession) -> int:
        """The other broker of a cash transfer, where the leg that is not on ``test_broker`` lives."""
        import uuid  # noqa: PLC0415 — test setup — imports after sys.path/db config

        broker = Broker(name=f"Partner Broker BRIM {uuid.uuid4().hex[:8]}", description="The other side of a cash transfer")
        async_session.add(broker)
        await async_session.commit()
        await async_session.refresh(broker)
        broker_id = broker.id
        yield broker_id
        leftover = await async_session.get(Broker, broker_id)
        if leftover:
            await async_session.delete(leftover)
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_each_side_is_a_likely_duplicate_of_its_merged_cash_transfer_leg(self, async_session: AsyncSession, test_broker: int, partner_broker: int, test_date: date):
        """DD-011: the two sides of a merged transfer, exported again, each on its own broker.

        The withdrawal comes back on the broker the money left, with the first text of the merged description; the
        deposit on the broker it reached, with the second. Each finds its own leg, and only it, as LIKELY: the text it
        brings is contained in the joined one.
        """
        out_id, in_id = await _save_merged_transfer(async_session, test_broker, partner_broker, test_date, "-1000")
        try:
            sent = await detect_tx_duplicates(transactions=[_cash_item(test_broker, TransactionType.WITHDRAWAL, test_date, "-1000", TRANSFER_OUT_TEXT)], broker_id=test_broker, session=async_session)
            received = await detect_tx_duplicates(transactions=[_cash_item(partner_broker, TransactionType.DEPOSIT, test_date, "1000", TRANSFER_IN_TEXT)], broker_id=partner_broker, session=async_session)

            assert _verdicts(sent) == {0: ("likely", [(out_id, TransactionType.CASH_TRANSFER, BRIMDuplicateLevel.LIKELY)])}
            assert _verdicts(received) == {0: ("likely", [(in_id, TransactionType.CASH_TRANSFER, BRIMDuplicateLevel.LIKELY)])}
        finally:
            await _delete_transactions(async_session, [out_id, in_id])

    @pytest.mark.asyncio
    async def test_a_merged_leg_whose_text_was_rewritten_is_only_a_possible_duplicate(self, async_session: AsyncSession, test_broker: int, partner_broker: int, test_date: date):
        """DD-012: the user rewrote the merged description. Day, amount and sign still match, the text no longer does:
        POSSIBLE — still flagged, no longer certain."""
        rewritten = "Transfer to the overnight account"
        out_id, in_id = await _save_merged_transfer(async_session, test_broker, partner_broker, test_date, "-1000", rewritten)
        try:
            report = await detect_tx_duplicates(transactions=[_cash_item(test_broker, TransactionType.WITHDRAWAL, test_date, "-1000", TRANSFER_OUT_TEXT)], broker_id=test_broker, session=async_session)

            assert _verdicts(report) == {0: ("possible", [(out_id, TransactionType.CASH_TRANSFER, BRIMDuplicateLevel.POSSIBLE)])}
        finally:
            await _delete_transactions(async_session, [out_id, in_id])

    @pytest.mark.asyncio
    async def test_a_deposit_never_matches_a_merged_leg_of_the_opposite_sign(self, async_session: AsyncSession, test_broker: int, partner_broker: int, test_date: date):
        """DD-013: +1000 coming in is not the −1000 that left, whatever its text.

        Row 1, the withdrawal of that same −1000, is the presence barrier: it proves the leg is within the check's
        reach, so row 0 is new because of its sign alone. (The +1000 leg exists — on the other broker.)
        """
        out_id, in_id = await _save_merged_transfer(async_session, test_broker, partner_broker, test_date, "-1000")
        try:
            report = await detect_tx_duplicates(
                transactions=[
                    _cash_item(test_broker, TransactionType.DEPOSIT, test_date, "1000", TRANSFER_OUT_TEXT),
                    _cash_item(test_broker, TransactionType.WITHDRAWAL, test_date, "-1000", TRANSFER_OUT_TEXT),
                ],
                broker_id=test_broker,
                session=async_session,
            )

            assert _verdicts(report) == {0: ("unique", []), 1: ("likely", [(out_id, TransactionType.CASH_TRANSFER, BRIMDuplicateLevel.LIKELY)])}
        finally:
            await _delete_transactions(async_session, [out_id, in_id])

    @pytest.mark.asyncio
    async def test_both_sides_of_a_merged_fx_conversion_find_their_own_leg(self, async_session: AsyncSession, test_broker: int, test_date: date):
        """DD-014: a conversion merged from a EUR withdrawal and a USD deposit of one broker, exported again.

        The deposit finds the USD leg, the withdrawal the EUR one: currency and amount pick the leg, the joined text
        makes each LIKELY.
        """
        sold, bought = "Currency exchange EUR/USD · id FX0001", "Currency exchange EUR/USD · id FX0002"
        merged = f"{sold}\n{bought}"
        eur_id, usd_id = await _save_merged_pair(async_session, TransactionType.FX_CONVERSION, test_date, [(test_broker, "-920", "EUR", merged), (test_broker, "1000", "USD", merged)])
        try:
            report = await detect_tx_duplicates(
                transactions=[
                    _cash_item(test_broker, TransactionType.DEPOSIT, test_date, "1000", bought, currency="USD"),
                    _cash_item(test_broker, TransactionType.WITHDRAWAL, test_date, "-920", sold),
                ],
                broker_id=test_broker,
                session=async_session,
            )

            assert _verdicts(report) == {
                0: ("likely", [(usd_id, TransactionType.FX_CONVERSION, BRIMDuplicateLevel.LIKELY)]),
                1: ("likely", [(eur_id, TransactionType.FX_CONVERSION, BRIMDuplicateLevel.LIKELY)]),
            }
        finally:
            await _delete_transactions(async_session, [eur_id, usd_id])

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("other_type", "amount", "same_movement"),
        [
            (TransactionType.FEE, "-1000", TransactionType.WITHDRAWAL),
            (TransactionType.TAX, "-1000", TransactionType.WITHDRAWAL),
            (TransactionType.INTEREST, "1000", TransactionType.DEPOSIT),
        ],
        ids=["fee", "tax", "interest"],
    )
    async def test_other_cash_types_do_not_look_at_merged_legs(self, async_session: AsyncSession, test_broker: int, partner_broker: int, test_date: date, other_type: TransactionType, amount: str, same_movement: TransactionType):
        """DD-015: only a deposit or a withdrawal can be the re-export of a merged leg; every other type is unchanged.

        A fee, a tax or an interest of the leg's amount, day and text stays new. Row 1, the deposit or withdrawal of
        that amount, is the presence barrier. A BUY or a SELL needs no case: it moves a quantity, which a leg never has.
        """
        leg_id, partner_leg_id = await _save_merged_transfer(async_session, test_broker, partner_broker, test_date, amount)
        try:
            report = await detect_tx_duplicates(
                transactions=[
                    _cash_item(test_broker, other_type, test_date, amount, TRANSFER_OUT_TEXT),
                    _cash_item(test_broker, same_movement, test_date, amount, TRANSFER_OUT_TEXT),
                ],
                broker_id=test_broker,
                session=async_session,
            )

            assert _verdicts(report) == {0: ("unique", []), 1: ("likely", [(leg_id, TransactionType.CASH_TRANSFER, BRIMDuplicateLevel.LIKELY)])}
        finally:
            await _delete_transactions(async_session, [leg_id, partner_leg_id])

    @pytest.mark.asyncio
    async def test_the_same_type_still_needs_the_same_text(self, async_session: AsyncSession, test_broker: int, test_date: date):
        """DD-016 — regression guard, green before and after the change: containment is for merged legs only.

        A plain DEPOSIT whose text merely contains the incoming one stays a POSSIBLE duplicate: between rows of the
        same type, only the same text (whitespace and case aside) makes a LIKELY one.
        """
        saved = Transaction(broker_id=test_broker, asset_id=None, type=TransactionType.DEPOSIT, date=test_date, quantity=Decimal("0"), amount=Decimal("1000"), currency="EUR", description=MERGED_TRANSFER_TEXT)
        async_session.add(saved)
        await async_session.flush()
        saved_id = saved.id  # read before the commit expires the instance
        await async_session.commit()
        try:
            report = await detect_tx_duplicates(transactions=[_cash_item(test_broker, TransactionType.DEPOSIT, test_date, "1000", TRANSFER_IN_TEXT)], broker_id=test_broker, session=async_session)

            assert _verdicts(report) == {0: ("possible", [(saved_id, TransactionType.DEPOSIT, BRIMDuplicateLevel.POSSIBLE)])}
        finally:
            await _delete_transactions(async_session, [saved_id])

    @pytest.mark.asyncio
    @pytest.mark.parametrize("description", [None, "", " \n "], ids=["none", "empty", "blank"])
    async def test_a_row_without_text_is_never_a_likely_duplicate_of_a_merged_leg(self, async_session: AsyncSession, test_broker: int, partner_broker: int, test_date: date, description: str | None):
        """DD-017: an empty text is contained in every text, so it must not make a LIKELY duplicate of every merged leg.

        DD-007's rule, on a merged leg: no text, no certainty. The key fields still make it POSSIBLE.
        """
        out_id, in_id = await _save_merged_transfer(async_session, test_broker, partner_broker, test_date, "-1000")
        try:
            report = await detect_tx_duplicates(transactions=[_cash_item(test_broker, TransactionType.WITHDRAWAL, test_date, "-1000", description)], broker_id=test_broker, session=async_session)

            assert _verdicts(report) == {0: ("possible", [(out_id, TransactionType.CASH_TRANSFER, BRIMDuplicateLevel.POSSIBLE)])}
        finally:
            await _delete_transactions(async_session, [out_id, in_id])


# =============================================================================
# CATEGORY 4c: W-B51 — THE QUANTITY OF A DUPLICATE
# =============================================================================
#
# A saved row stays a duplicate candidate while its quantity matches the incoming one. Until W-B51 that was a fixed
# tolerance, |a − b| ≤ 0.0001 (QUANTITY_TOLERANCE in detect_tx_duplicates), coarse for crypto: two recurring buys of the
# same 10 EUR of BTC on one day, 0.00015123 and 0.00015098, are 2.5e-7 apart, so the second comes back as a duplicate of
# the first — LIKELY when the texts agree, and a likely duplicate starts deselected in the import wizard
# (importDedup.duplicateStatusAllowsAutoSelect): a real buy is left out.
#
# D-W51-1 (coordinator, approved): two quantities match when, rounded half-up to the scale of the less precise of the two,
# they are equal, AND |a − b| ≤ 0.0001 (the bound of before: never looser). The scale is read on normalize()d values: the
# column reads a value back padded to 6 decimals (RealDecimal's READ_MIN_SCALE: 0.00015 reads 0.000150, 10 reads
# 10.000000), and a padding zero is no precision.
#
# Each case saves one BUY and offers one BUY of the same broker, day, asset, cash and text: the quantity alone decides, and
# a match is LIKELY_WITH_ASSET. RED until the cure: two quantities within 0.0001 that differ at their common scale, and a
# saved quantity that reads None (W-B51 (unreadable quantity)). Every other case is a guard, green before and after.

WB51_CASH = "-10.00"  # one cash on both sides: the quantity alone decides
WB51_TEXT = "Recurring buy BTC · W-B51"  # one text on both sides: a match is LIKELY_WITH_ASSET
WB51_BOUND = Decimal("0.0001")  # QUANTITY_TOLERANCE: the whole rule until W-B51, its outer bound after (D-W51-1)


def _wb51_buy(broker_id: int, asset_id: int, day: date, quantity: str) -> TXCreateItem:
    """A parsed BUY of ``quantity`` units for ``WB51_CASH`` EUR, as a plugin hands it to the duplicate check."""
    return TXCreateItem(broker_id=broker_id, asset_id=asset_id, type=TransactionType.BUY, date=day, quantity=Decimal(quantity), cash=Currency(code="EUR", amount=Decimal(WB51_CASH)), description=WB51_TEXT)


async def _wb51_save_buy(session: AsyncSession, broker_id: int, asset_id: int, day: date, quantity: str) -> int:
    """The same BUY saved, as an earlier import left it; its id."""
    row = Transaction(broker_id=broker_id, asset_id=asset_id, type=TransactionType.BUY, date=day, quantity=Decimal(quantity), amount=Decimal(WB51_CASH), currency="EUR", description=WB51_TEXT)
    session.add(row)
    await session.flush()
    row_id = row.id  # read before the commit expires the instance
    await session.commit()
    return row_id


async def _wb51_read_quantity(session: AsyncSession, row_id: int) -> Decimal | None:
    """The quantity of row ``row_id`` as the duplicate check loads it: through ``RealDecimal``, past the identity map."""
    from sqlalchemy import select  # noqa: PLC0415 — test setup — imports after sys.path/db config

    loaded = (await session.execute(select(Transaction).where(Transaction.id == row_id).execution_options(populate_existing=True))).scalar_one()
    return loaded.quantity


async def _wb51_make_quantity_unreadable(session: AsyncSession, row_id: int, literal: str, storage: str) -> None:
    """W-B74's plant on the quantity of row ``row_id``: the SQLite literal ``literal`` written by raw SQL, as an older version
    or another tool can leave it. Checks what the case rests on: SQLite keeps it as ``storage``, and the row loads None
    there (``RealDecimal``, W-B58)."""
    from sqlalchemy import text  # noqa: PLC0415 — test setup — imports after sys.path/db config

    await session.execute(text(f"UPDATE transactions SET quantity = {literal} WHERE id = :id"), {"id": row_id})
    await session.commit()
    kind = (await session.execute(text("SELECT typeof(quantity) FROM transactions WHERE id = :id"), {"id": row_id})).scalar_one()
    assert kind == storage, f"setup: row id={row_id} must hold {literal} as {storage} in quantity; typeof = {kind}"
    read = await _wb51_read_quantity(session, row_id)
    assert read is None, f"setup: RealDecimal must read the {literal} of id={row_id} as None (W-B58); it reads {read!r}"


async def _wb51_verdicts(session: AsyncSession, saved_id: int, reads_back: str, incoming: TXCreateItem, written: str) -> dict:
    """The duplicate check's verdicts on ``incoming`` alone, once what the case rests on is checked: the saved row
    ``saved_id`` reads back ``reads_back``, and the incoming BUY keeps ``written`` as written."""
    read = await _wb51_read_quantity(session, saved_id)
    assert (str(read), str(incoming.quantity)) == (reads_back, written), f"setup: the saved BUY id={saved_id} must read back {reads_back} and the incoming BUY keep {written}; they hold {read} and {incoming.quantity}"
    report = await detect_tx_duplicates(transactions=[incoming], broker_id=incoming.broker_id, session=session)
    return _verdicts(report)


def _wb51_before(saved: str, incoming: str) -> str:
    """What the fixed tolerance alone, the rule until W-B51, makes of the pair: for a failure message."""
    difference = abs(Decimal(saved) - Decimal(incoming))
    if difference <= WB51_BOUND:
        return f"the fixed tolerance alone (the rule until W-B51) keeps the saved BUY a candidate, |a − b| = {difference} ≤ {WB51_BOUND}"
    return f"the fixed tolerance alone (the rule until W-B51) drops the saved BUY too, |a − b| = {difference} > {WB51_BOUND}"


class TestWB51QuantityOfADuplicate:
    """W-B51: the quantity that keeps a saved BUY a duplicate candidate of an incoming one (D-W51-1)."""

    @pytest_asyncio.fixture
    async def wb51_asset(self, async_session: AsyncSession) -> int:
        """A crypto asset of the test's own, for its BUYs; deleted after them."""
        import uuid  # noqa: PLC0415 — test setup — imports after sys.path/db config

        asset = Asset(display_name=f"W-B51 Bitcoin {uuid.uuid4().hex}", asset_type=AssetType.CRYPTO, currency="EUR", active=True)
        async_session.add(asset)
        await async_session.commit()
        await async_session.refresh(asset)
        asset_id = asset.id
        yield asset_id
        leftover = await async_session.get(Asset, asset_id)
        if leftover:
            await async_session.delete(leftover)
            await async_session.commit()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("saved", "reads_back", "incoming", "why"),
        [
            # RED until the cure: within 0.0001 of each other, so today a LIKELY duplicate.
            pytest.param("0.00008", "0.000080", "0.00015", "both have 5 decimals, and 0.00008 ≠ 0.00015", id="apart-at-5-decimals"),
            pytest.param("0.00015098", "0.00015098", "0.00015123", "two recurring buys of the same 10 EUR: both have 8 decimals, and 0.00015098 ≠ 0.00015123", id="recurring-buys-at-8-decimals"),
            # Guard, green before and after: 0.0001 stays the outer bound.
            pytest.param("10", "10.000000", "10.4", "rounded half-up to 0 decimals, the scale of 10, both are 10, but |a − b| = 0.4 > 0.0001", id="integers-10-and-10.4"),
        ],
    )
    async def test_wb51_quantities_apart_are_not_duplicates(self, async_session: AsyncSession, test_broker: int, wb51_asset: int, test_date: date, saved: str, reads_back: str, incoming: str, why: str):
        """W-B51: a saved BUY whose quantity differs from the incoming one at the scale of the less precise of the two, or
        by more than 0.0001, is no candidate: the incoming BUY is new (D-W51-1).

        RED until the cure for the two pairs within 0.0001, which the fixed tolerance makes a LIKELY duplicate today. The
        integers 10 and 10.4 are a guard: equal at their common scale, more than 0.0001 apart.
        """
        saved_id = await _wb51_save_buy(async_session, test_broker, wb51_asset, test_date, saved)
        try:
            verdicts = await _wb51_verdicts(async_session, saved_id, reads_back, _wb51_buy(test_broker, wb51_asset, test_date, incoming), incoming)

            assert verdicts == {0: ("unique", [])}, f"W-B51: saved {saved} (it reads back {reads_back}) and incoming {incoming}: {why}, so the incoming BUY is new (D-W51-1); {_wb51_before(saved, incoming)}, and the check answers {verdicts}"
        finally:
            await _delete_transactions(async_session, [saved_id])

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("saved", "reads_back", "incoming", "why"),
        [
            pytest.param("0.000153", "0.000153", "0.00015", "a report rounding to 5 decimals: 0.000153 rounded half-up to 5 decimals is 0.00015, and |a − b| = 0.000003", id="report-rounded"),
            pytest.param("10", "10.000000", "10", "the same whole quantity: the padding of 10.000000 is no precision", id="integers-10"),
            pytest.param("0.1234567891", "0.1234567891", "0.1234567891", "the same file imported again: the quantity reads back as written, all 10 decimals", id="identical-reimport"),
            pytest.param("0.00015", "0.000150", "0.000153", "the column pads 0.00015 to 0.000150, but its scale stays 5 (normalize()): 0.000153 rounded half-up to 5 decimals is 0.00015", id="saved-read-back-padded"),
            pytest.param("0.000153", "0.000153", "0.000150", "a report writing 0.000150 means 0.00015, scale 5 (normalize()): 0.000153 rounded half-up to 5 decimals is 0.00015", id="incoming-padded"),
            pytest.param("0.000145", "0.000145", "0.00015", "a tie: 0.000145 rounded half-up to 5 decimals is 0.00015 (half-even would make it 0.00014)", id="half-up-tie"),
        ],
    )
    async def test_wb51_quantities_equal_at_the_coarser_scale_are_duplicates(self, async_session: AsyncSession, test_broker: int, wb51_asset: int, test_date: date, saved: str, reads_back: str, incoming: str, why: str):
        """W-B51, guards green before and after the cure: two quantities equal once rounded half-up to the scale of the
        less precise of the two, and within 0.0001 of each other, are the same BUY (D-W51-1), here a LIKELY duplicate.

        Each pins a part of the rule a cure could miss: rounding the more precise side (report-rounded), the integers,
        the exact re-import, a trailing zero on either side (normalize()), and half-up on a tie.
        """
        saved_id = await _wb51_save_buy(async_session, test_broker, wb51_asset, test_date, saved)
        try:
            verdicts = await _wb51_verdicts(async_session, saved_id, reads_back, _wb51_buy(test_broker, wb51_asset, test_date, incoming), incoming)

            expected = {0: ("likely", [(saved_id, TransactionType.BUY, BRIMDuplicateLevel.LIKELY_WITH_ASSET)])}
            assert verdicts == expected, f"W-B51: saved {saved} (it reads back {reads_back}) and incoming {incoming}: {why}, so the incoming BUY is the saved one again (D-W51-1); the check answers {verdicts}"
        finally:
            await _delete_transactions(async_session, [saved_id])

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("literal", "storage"), [("'n/a'", "text"), ("9e999", "real")], ids=["text", "inf"])
    async def test_wb51_an_unreadable_quantity_is_no_candidate(self, async_session: AsyncSession, test_broker: int, wb51_asset: int, test_date: date, literal: str, storage: str):
        """W-B51 (unreadable quantity): a saved BUY whose quantity reads None — a text, or a REAL +inf, planted in the
        column: W-B74's case, which ``RealDecimal`` reads as None (W-B58) — is no candidate, and the check does not raise.

        RED until the cure: ``abs(existing.quantity - tx.quantity)`` raises TypeError on it, where the cash side already
        skips a None. Two BUYs of 0.5 are saved, the first made unreadable. Row 0 (0.5) is the presence barrier: the check
        reaches the day and still matches the readable BUY, and it alone. Row 1 (0.7) finds the readable BUY 0.2 away and
        the unreadable one: it is new.
        """
        saved_ids: List[int] = []  # whoever writes cleans up: every row saved so far, whatever fails next
        try:
            for _ in range(2):
                saved_ids.append(await _wb51_save_buy(async_session, test_broker, wb51_asset, test_date, "0.5"))
            unreadable_id, readable_id = saved_ids
            await _wb51_make_quantity_unreadable(async_session, unreadable_id, literal, storage)
            transactions = [_wb51_buy(test_broker, wb51_asset, test_date, "0.5"), _wb51_buy(test_broker, wb51_asset, test_date, "0.7")]
            try:
                report = await detect_tx_duplicates(transactions=transactions, broker_id=test_broker, session=async_session)
            except Exception as error:  # the contract: a row that cannot be read is skipped, nothing raises
                pytest.fail(f"W-B51 (unreadable quantity): the saved BUY id={unreadable_id} holds {literal} ({storage}) in its quantity, which reads None: detect_tx_duplicates must skip it, not raise; today it raises {type(error).__name__}: {error}")

            verdicts = _verdicts(report)
            expected = {0: ("likely", [(readable_id, TransactionType.BUY, BRIMDuplicateLevel.LIKELY_WITH_ASSET)]), 1: ("unique", [])}
            assert verdicts == expected, f"W-B51 (unreadable quantity): the BUY id={unreadable_id}, whose quantity reads None, is no candidate, and the readable id={readable_id} still is: row 0 (0.5) a likely duplicate of {readable_id} alone, row 1 (0.7) new; the check answers {verdicts}"
        finally:
            await _delete_transactions(async_session, saved_ids)


# =============================================================================
# CATEGORY 4d: A REWARD IMPORTED AGAIN (project 79, STK-4a)
# =============================================================================
#
# Before 1.1.0 a reward in kind was stored with another type: Coinbase and Crypto.com wrote an ADJUSTMENT whose description
# carried the value, «… (Value: <total> <currency>)»; Freetrade wrote a free share as a BUY that took its cash. From 1.1.0
# the same row comes back as a REWARD with no cash and no «(Value: …)». ``detect_tx_duplicates`` looks at the older types
# for an incoming REWARD (and the other way round), and the level follows the merged-leg rule: the stored description must
# HOLD the incoming one, once the «(Value: …)» note of the older imports is set aside on both sides (between equivalent
# types only). So a re-imported reward is a LIKELY duplicate (it starts deselected in the wizard,
# importDedup.duplicateStatusAllowsAutoSelect), LIKELY_WITH_ASSET once its asset is resolved; texts that do not match make it
# POSSIBLE (it stays selected). An incoming BUY never matches a stored REWARD: its cash finds no cash there (deliberate).
#
# The stored rows carry the descriptions the 1.0.0 plugins really wrote (``git show`` of the plugins before 1.1.0); the
# incoming ones are parsed by the 1.1.0 plugins from a sample row. Quantities have at most 10 decimals, what the column keeps.

REWARD_SAMPLES = {
    "broker_coinbase": "coinbase-export.csv",
    "broker_cryptocom": "cryptocom-export.csv",
    "broker_freetrade": "freetrade-export.csv",
}


def _reward_sample_csv(tmp_path: Path, plugin_folder: str, starts_with: str, replace: tuple = (), name: str = "one-row") -> Path:
    """A one-row copy of a plugin's sample: its header and the line that starts with ``starts_with``, each ``(old, new)`` of
    ``replace`` applied to that line (``tmp_path``; the sample itself is never edited)."""
    from backend.test_scripts.brim_samples import plugin_samples_dir  # noqa: PLC0415 — test setup — imports after sys.path/db config

    sample = plugin_samples_dir(plugin_folder) / REWARD_SAMPLES[plugin_folder]
    header, *lines = sample.read_text(encoding="utf-8").splitlines()
    found = [line for line in lines if line.startswith(starts_with)]
    assert len(found) == 1, f"setup: {sample.name} must hold one line starting with {starts_with!r}, found {len(found)}"
    row = found[0]
    for old, new in replace:
        assert old in row, f"setup: {old!r} is not in the {sample.name} line {row!r}"
        row = row.replace(old, new)
    path = tmp_path / f"{plugin_folder}-{name}.csv"
    path.write_text(f"{header}\n{row}\n", encoding="utf-8")
    return path


def _parsed_rewards(plugin_folder: str, csv_path: Path, broker_id: int) -> List[TXCreateItem]:
    """The transactions the 1.1.0 plugin ``plugin_folder`` parses from ``csv_path``, all REWARDs with a value."""
    from backend.app.services.brim.registry import BRIMProviderRegistry  # noqa: PLC0415 — test setup — imports after sys.path/db config

    BRIMProviderRegistry.auto_discover()
    plugin = BRIMProviderRegistry.get_provider_instance(plugin_folder)
    assert plugin is not None and plugin.plugin_version == "1.1.0", f"setup: {plugin_folder} 1.1.0 is registered"
    output = plugin.parse(csv_path, broker_id=broker_id)
    assert output.transactions and all(tx.type == TransactionType.REWARD and tx.cost_basis_override is not None for tx in output.transactions), f"setup: {plugin_folder} parses REWARDs with a value: {[(tx.type, tx.cost_basis_override) for tx in output.transactions]}, {output.validation_issues}"
    return output.transactions


# The three rewards of the samples, as 1.1.0 parses them and as 1.0.0 stored them.
# Coinbase line 2, its 12-decimal quantity cut to 10 (the column keeps 10): «staking income: ETH» + « (Value: <Total> <currency>)».
COINBASE_REWARD_LINE = "678a8bdefcb176007bfdbXXX"
COINBASE_QUANTITY = "0.0000378357"
COINBASE_OLD_TEXT = "staking income: ETH (Value: 0.12649 EUR)"
# Crypto.com, 2024-11-11: «<description> (Value: <Native Amount> <Native Currency>)<hash suffix>», no hash on this row.
CRYPTOCOM_REWARD_LINE = "2024-11-11 00:33:50,Cardholder CRO Stake Reward"
CRYPTOCOM_QUANTITY = "9.9110424"
CRYPTOCOM_OLD_TEXT = "Cardholder CRO Stake Reward (Value: 1.06944518 EUR)"
# Freetrade line 13: a BUY of the free share for its Total, «freeshare_order: <Title>».
FREETRADE_REWARD_LINE = "FTSE All World,FREESHARE_ORDER"
FREETRADE_QUANTITY = "1"
FREETRADE_OLD_TEXT = "freeshare_order: FTSE All World"

REWARD_CASES = [
    pytest.param("broker_coinbase", COINBASE_REWARD_LINE, (("0.000037835729", COINBASE_QUANTITY),), date(2025, 1, 17), TransactionType.ADJUSTMENT, COINBASE_QUANTITY, None, COINBASE_OLD_TEXT, id="coinbase-staking-adjustment"),
    pytest.param("broker_cryptocom", CRYPTOCOM_REWARD_LINE, (), date(2024, 11, 11), TransactionType.ADJUSTMENT, CRYPTOCOM_QUANTITY, None, CRYPTOCOM_OLD_TEXT, id="cryptocom-stake-adjustment"),
    pytest.param("broker_freetrade", FREETRADE_REWARD_LINE, (), date(2024, 1, 21), TransactionType.BUY, FREETRADE_QUANTITY, ("-4.95", "GBP"), FREETRADE_OLD_TEXT, id="freetrade-free-share-buy"),
]


async def _save_rows(session: AsyncSession, rows: List[Transaction]) -> List[int]:
    """Rows saved as an earlier import left them; their ids, read before the commit expires the instances."""
    session.add_all(rows)
    await session.flush()
    ids = [row.id for row in rows]
    await session.commit()
    return ids


def _old_row(broker_id: int, asset_id: int, day: date, tx_type: TransactionType, quantity: str, cash: tuple | None, description: str) -> Transaction:
    """A reward as a 1.0.0 plugin stored it: an ADJUSTMENT with no cash, or a BUY with its cash."""
    amount, currency = cash if cash else ("0", None)
    return Transaction(broker_id=broker_id, asset_id=asset_id, type=tx_type, date=day, quantity=Decimal(quantity), amount=Decimal(amount), currency=currency, description=description, tags="import")


def _stored_reward(broker_id: int, asset_id: int, parsed: TXCreateItem) -> Transaction:
    """A REWARD saved as a 1.1.0 import commits it: no cash, its value per unit in cost_basis_override."""
    return Transaction(
        broker_id=broker_id,
        asset_id=asset_id,
        type=TransactionType.REWARD,
        date=parsed.date,
        quantity=parsed.quantity,
        amount=Decimal("0"),
        currency=None,
        cost_basis_override=parsed.cost_basis_override.amount,
        cost_basis_currency=parsed.cost_basis_override.code,
        description=parsed.description,
        tags="import",
    )


def _resolved(parsed: TXCreateItem, asset_id: int) -> list:
    """The asset mapping that resolves the parsed row's placeholder to ``asset_id``."""
    from backend.app.schemas.brim import BRIMAssetMapping  # noqa: PLC0415 — test setup — imports after sys.path/db config

    return [BRIMAssetMapping(fake_asset_id=parsed.asset_id, selected_asset_id=asset_id)]


class TestRewardReimportDuplicates:
    """A reward stored by a 1.0.0 plugin with its older type, imported again as a REWARD (project 79, STK-4a)."""

    @pytest_asyncio.fixture
    async def reward_asset(self, async_session: AsyncSession) -> int:
        """An asset of the test's own for its rows; deleted after them."""
        import uuid  # noqa: PLC0415 — test setup — imports after sys.path/db config

        asset = Asset(display_name=f"STK-4a reward {uuid.uuid4().hex}", asset_type=AssetType.CRYPTO, currency="EUR", active=True)
        async_session.add(asset)
        await async_session.commit()
        await async_session.refresh(asset)
        asset_id = asset.id
        yield asset_id
        leftover = await async_session.get(Asset, asset_id)
        if leftover:
            await async_session.delete(leftover)
            await async_session.commit()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("plugin_folder", "line", "replace", "day", "old_type", "quantity", "old_cash", "old_text"), REWARD_CASES)
    async def test_a_reward_stored_with_its_old_type_is_a_likely_duplicate(self, async_session: AsyncSession, test_broker: int, reward_asset: int, tmp_path: Path, plugin_folder, line, replace, day, old_type, quantity, old_cash, old_text):
        """The old row's text holds the new one: LIKELY with the asset unresolved, LIKELY_WITH_ASSET once it is resolved."""
        (incoming,) = _parsed_rewards(plugin_folder, _reward_sample_csv(tmp_path, plugin_folder, line, replace), test_broker)
        assert (incoming.date, incoming.quantity) == (day, Decimal(quantity)), f"setup: {plugin_folder} parsed {incoming.date} {incoming.quantity}"
        assert incoming.description and incoming.description in old_text, f"setup: the 1.0.0 text {old_text!r} holds the 1.1.0 one {incoming.description!r}"

        saved_ids = await _save_rows(async_session, [_old_row(test_broker, reward_asset, day, old_type, quantity, old_cash, old_text)])
        try:
            (old_id,) = saved_ids
            unresolved = _verdicts(await detect_tx_duplicates(transactions=[incoming], broker_id=test_broker, session=async_session))
            resolved = _verdicts(await detect_tx_duplicates(transactions=[incoming], broker_id=test_broker, session=async_session, asset_mappings=_resolved(incoming, reward_asset)))

            assert unresolved == {0: ("likely", [(old_id, old_type, BRIMDuplicateLevel.LIKELY)])}, f"{plugin_folder}: the REWARD {incoming.description!r} is the {old_type} {old_text!r} (id={old_id}) again; the check answers {unresolved}"
            assert resolved == {0: ("likely", [(old_id, old_type, BRIMDuplicateLevel.LIKELY_WITH_ASSET)])}, f"{plugin_folder}, asset resolved: the check answers {resolved}"
        finally:
            await _delete_transactions(async_session, saved_ids)

    @pytest.mark.asyncio
    async def test_a_stored_reward_is_found_by_an_incoming_adjustment(self, async_session: AsyncSession, test_broker: int, reward_asset: int, tmp_path: Path):
        """The other way round: an ADJUSTMENT of the same units finds the stored REWARD, LIKELY with the same text and with the
        1.0.0 text too: its «(Value: …)» note is set aside between equivalent types."""
        (parsed,) = _parsed_rewards("broker_coinbase", _reward_sample_csv(tmp_path, "broker_coinbase", COINBASE_REWARD_LINE, (("0.000037835729", COINBASE_QUANTITY),)), test_broker)
        saved_ids = await _save_rows(async_session, [_stored_reward(test_broker, reward_asset, parsed)])
        try:
            (reward_id,) = saved_ids
            same_text = TXCreateItem(broker_id=test_broker, asset_id=parsed.asset_id, type=TransactionType.ADJUSTMENT, date=parsed.date, quantity=parsed.quantity, description=parsed.description)
            old_text = TXCreateItem(broker_id=test_broker, asset_id=parsed.asset_id, type=TransactionType.ADJUSTMENT, date=parsed.date, quantity=parsed.quantity, description=COINBASE_OLD_TEXT)

            verdicts = _verdicts(await detect_tx_duplicates(transactions=[same_text, old_text], broker_id=test_broker, session=async_session))

            expected = {0: ("likely", [(reward_id, TransactionType.REWARD, BRIMDuplicateLevel.LIKELY)]), 1: ("likely", [(reward_id, TransactionType.REWARD, BRIMDuplicateLevel.LIKELY)])}
            assert verdicts == expected, f"the stored REWARD id={reward_id} {parsed.description!r}: found by both ADJUSTMENTs, LIKELY with its own text and with {COINBASE_OLD_TEXT!r}; the check answers {verdicts}"
        finally:
            await _delete_transactions(async_session, saved_ids)

    @pytest.mark.asyncio
    async def test_texts_that_do_not_match_make_a_possible_duplicate(self, async_session: AsyncSession, test_broker: int, reward_asset: int, tmp_path: Path):
        """Same broker, day and units, an ADJUSTMENT whose text does not hold the REWARD's: POSSIBLE (it stays selected), the
        general rule for different texts."""
        (incoming,) = _parsed_rewards("broker_coinbase", _reward_sample_csv(tmp_path, "broker_coinbase", COINBASE_REWARD_LINE, (("0.000037835729", COINBASE_QUANTITY),)), test_broker)
        saved_ids = await _save_rows(async_session, [_old_row(test_broker, reward_asset, incoming.date, TransactionType.ADJUSTMENT, COINBASE_QUANTITY, None, "ETH received from a friend")])
        try:
            (old_id,) = saved_ids
            verdicts = _verdicts(await detect_tx_duplicates(transactions=[incoming], broker_id=test_broker, session=async_session))
            assert verdicts == {0: ("possible", [(old_id, TransactionType.ADJUSTMENT, BRIMDuplicateLevel.POSSIBLE)])}, f"the check answers {verdicts}"
        finally:
            await _delete_transactions(async_session, saved_ids)

    @pytest.mark.asyncio
    async def test_a_hashed_cryptocom_reward_is_likely_too(self, async_session: AsyncSession, test_broker: int, reward_asset: int, tmp_path: Path):
        """Crypto.com 1.0.0 wrote the hash AFTER the value, «<description> (Value: …) (<hash>)»; 1.1.0 writes «<description>
        (<hash>)». With the «(Value: …)» note set aside the old text holds the new one: a re-imported reward with a hash is a
        LIKELY duplicate, deselected in the wizard (found by test-author, fixed 24/11/2026)."""
        tx_hash = "0xabc123"
        csv_path = _reward_sample_csv(tmp_path, "broker_cryptocom", CRYPTOCOM_REWARD_LINE, (("crypto_wallet,", f"crypto_wallet,{tx_hash}"),))
        (incoming,) = _parsed_rewards("broker_cryptocom", csv_path, test_broker)
        assert incoming.description == f"Cardholder CRO Stake Reward ({tx_hash})", f"setup: {incoming.description!r}"
        old_text = f"Cardholder CRO Stake Reward (Value: 1.06944518 EUR) ({tx_hash})"
        saved_ids = await _save_rows(async_session, [_old_row(test_broker, reward_asset, incoming.date, TransactionType.ADJUSTMENT, CRYPTOCOM_QUANTITY, None, old_text)])
        try:
            (old_id,) = saved_ids
            verdicts = _verdicts(await detect_tx_duplicates(transactions=[incoming], broker_id=test_broker, session=async_session))
            assert verdicts == {0: ("likely", [(old_id, TransactionType.ADJUSTMENT, BRIMDuplicateLevel.LIKELY)])}, f"the check answers {verdicts}"
        finally:
            await _delete_transactions(async_session, saved_ids)

    @pytest.mark.asyncio
    async def test_an_incoming_buy_never_matches_a_stored_reward(self, async_session: AsyncSession, test_broker: int, reward_asset: int, tmp_path: Path):
        """Deliberate: a BUY's cash finds no cash on a REWARD. Row 0, the same REWARD, is the presence barrier: the stored row is
        reachable on that day; row 1, the free share as a 1.0.0 BUY, is new."""
        (parsed,) = _parsed_rewards("broker_freetrade", _reward_sample_csv(tmp_path, "broker_freetrade", FREETRADE_REWARD_LINE), test_broker)
        saved_ids = await _save_rows(async_session, [_stored_reward(test_broker, reward_asset, parsed)])
        try:
            (reward_id,) = saved_ids
            old_buy = TXCreateItem(broker_id=test_broker, asset_id=parsed.asset_id, type=TransactionType.BUY, date=parsed.date, quantity=parsed.quantity, cash=Currency(code="GBP", amount=Decimal("-4.95")), description=FREETRADE_OLD_TEXT)

            verdicts = _verdicts(await detect_tx_duplicates(transactions=[parsed, old_buy], broker_id=test_broker, session=async_session))

            expected = {0: ("likely", [(reward_id, TransactionType.REWARD, BRIMDuplicateLevel.LIKELY)]), 1: ("unique", [])}
            assert verdicts == expected, f"the stored REWARD id={reward_id}: found by the same REWARD, never by the BUY {FREETRADE_OLD_TEXT!r}; the check answers {verdicts}"
        finally:
            await _delete_transactions(async_session, saved_ids)

    @pytest.mark.asyncio
    async def test_a_different_quantity_is_not_the_same_reward(self, async_session: AsyncSession, test_broker: int, reward_asset: int, tmp_path: Path):
        """Row 0, the same units, is the presence barrier (LIKELY); row 1, another reward of the same day with other units, is new."""
        csv_path = _reward_sample_csv(tmp_path, "broker_coinbase", COINBASE_REWARD_LINE, (("0.000037835729", COINBASE_QUANTITY),))
        other_path = _reward_sample_csv(tmp_path, "broker_coinbase", COINBASE_REWARD_LINE, (("0.000037835729", "0.0000226522"),), name="other-units")
        (same,) = _parsed_rewards("broker_coinbase", csv_path, test_broker)
        (other,) = _parsed_rewards("broker_coinbase", other_path, test_broker)
        saved_ids = await _save_rows(async_session, [_old_row(test_broker, reward_asset, same.date, TransactionType.ADJUSTMENT, COINBASE_QUANTITY, None, COINBASE_OLD_TEXT)])
        try:
            (old_id,) = saved_ids
            verdicts = _verdicts(await detect_tx_duplicates(transactions=[same, other], broker_id=test_broker, session=async_session))
            expected = {0: ("likely", [(old_id, TransactionType.ADJUSTMENT, BRIMDuplicateLevel.LIKELY)]), 1: ("unique", [])}
            assert verdicts == expected, f"the ADJUSTMENT id={old_id} of {COINBASE_QUANTITY}: the REWARD of {same.quantity} is it again, the one of {other.quantity} is new; the check answers {verdicts}"
        finally:
            await _delete_transactions(async_session, saved_ids)
