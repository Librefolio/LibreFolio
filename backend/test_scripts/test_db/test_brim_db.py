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
from backend.app.schemas.brim import BRIMDuplicateLevel, BRIMMatchConfidence
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import detect_tx_duplicates, search_asset_candidates

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
