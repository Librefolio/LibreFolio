"""
Test Suite: scheduled_investment Param-Change Wipe (#R6-4)

Covers Phase 7 Part 3 Blocco G.13 — regression protection for the
symmetric wipe introduced by #R6-4 (2026-04-24) inside
``AssetSourceManager.bulk_assign_providers``.

Contract under test (``backend/app/services/asset_source.py`` L844 +
L869-946):

When a ``PARAMETRIC_GENERATION`` provider (currently only
``scheduled_investment``) already has an assignment and the caller
changes ``provider_params`` while keeping the ``provider_code`` stable,
the service MUST atomically:

1. Delete **all** ``PriceHistory`` rows of the asset (full wipe, not
   scoped by ``source_plugin_key`` — see #R4-3 rationale).
2. Delete **provider-generated events** (``AssetEvent`` rows with
   ``provider_assignment_id == existing.id``).
3. **Preserve manual events** (``provider_assignment_id IS NULL``).
4. **Disconnect linked transactions**: every ``Transaction`` whose
   ``asset_event_id`` pointed at a deleted event has it set to ``NULL``.
5. Invalidate the two in-memory caches for the old params hash.

Symmetric with the R3-3 currency-change Policy D: responsibility shifts
to the user (or the subsequent sync call) to re-materialize derived
data. The pre-#R6-4 bug left stale auto-events in place, contradicting
the regenerated schedule.

**Negative control**: same code re-assigned with the *same* params must
NOT trigger any deletion (the ``params_changed`` guard short-circuits).

Plan: ``plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md`` §G.13.
"""

from __future__ import annotations

import time
from datetime import date
from decimal import Decimal

import pytest

from backend.test_scripts.test_db_config import initialize_test_database, setup_test_database

setup_test_database()

from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from backend.app.db.models import (  # noqa: E402
    Asset,
    AssetEvent,
    AssetEventType,
    AssetProviderAssignment,
    AssetType,
    PriceHistory,
    ProviderInputType,
    Transaction,
    TransactionType,
)
from backend.app.db.session import get_async_engine  # noqa: E402
from backend.app.schemas.provider import FAProviderAssignmentItem  # noqa: E402
from backend.app.services.asset_source import AssetSourceManager  # noqa: E402
from backend.app.services.provider_registry import AssetProviderRegistry  # noqa: E402

# ============================================================================
# Fixtures & helpers
# ============================================================================


def _unique(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}"


def _params_v1() -> dict:
    """Initial scheduled_investment params — small 2026 schedule."""
    return {
        "initial_value": {"code": "EUR", "amount": "1000.00"},
        "schedule": [
            {
                "start_date": "2026-01-01",
                "end_date": "2026-06-30",
                "annual_rate": "0.04",
                "maturation_frequency": "MONTHLY",
            }
        ],
        "asset_events": [],
    }


def _params_v2() -> dict:
    """Structurally different params — same provider code."""
    return {
        "initial_value": {"code": "EUR", "amount": "1000.00"},
        "schedule": [
            {
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "annual_rate": "0.06",
                "maturation_frequency": "DAILY",
            }
        ],
        "asset_events": [],
    }


async def _create_asset_and_assign(
    session: AsyncSession,
    params: dict,
    *,
    name_prefix: str = "G13 Test",
) -> tuple[int, int]:
    """Create a fresh asset + assign scheduled_investment with ``params``.

    Returns ``(asset_id, assignment_id)``.
    """
    asset = Asset(
        display_name=_unique(name_prefix),
        currency="EUR",
        asset_type=AssetType.BOND,
        active=True,
    )
    session.add(asset)
    await session.commit()
    await session.refresh(asset)

    await AssetSourceManager.bulk_assign_providers(
        [
            FAProviderAssignmentItem(
                asset_id=asset.id,
                provider_code="scheduled_investment",
                # FAProviderAssignmentItem requires a str identifier; the service
                # converts empty → None when identifier_type=AUTO_GENERATED.
                identifier="",
                identifier_type=ProviderInputType.AUTO_GENERATED,
                provider_params=params,
            )
        ],
        session,
    )

    assignment_stmt = select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == asset.id)
    assignment = (await session.execute(assignment_stmt)).scalar_one()
    return asset.id, assignment.id


async def _seed_stale_data(
    session: AsyncSession,
    asset_id: int,
    assignment_id: int,
) -> dict[str, int]:
    """Directly insert prices + events + a transaction linked to an auto-event.

    Returns ``{auto_event_id, manual_event_id, tx_id}`` for later assertions.
    """
    # 3 prices — simulating a prior materialization.
    session.add_all(
        [
            PriceHistory(
                asset_id=asset_id,
                date=date(2026, 1, 15 + i),
                close=Decimal("1000.00") + Decimal(i),
                currency="EUR",
                source_plugin_key="MANUAL",
            )
            for i in range(3)
        ]
    )

    # 1 provider-generated event (will be wiped).
    auto_event = AssetEvent(
        asset_id=asset_id,
        date=date(2026, 2, 1),
        type=AssetEventType.INTEREST,
        value=Decimal("3.33"),
        currency="EUR",
        provider_assignment_id=assignment_id,
    )
    session.add(auto_event)

    # 1 manual event (must survive).
    manual_event = AssetEvent(
        asset_id=asset_id,
        date=date(2026, 3, 1),
        type=AssetEventType.PRICE_ADJUSTMENT,
        value=Decimal("5.00"),
        currency="EUR",
        provider_assignment_id=None,
    )
    session.add(manual_event)
    await session.flush()

    # Pure cash transaction won't do — tx must link an asset_event. We need
    # any tx of an EVENT_COMPATIBLE_TYPE (e.g. INTEREST) with asset_id set
    # and asset_event_id pointing to the auto event.
    tx = Transaction(
        broker_id=1,  # any broker; row stays invalid for balance purposes but DB accepts it (no FK check in test)
        asset_id=asset_id,
        type=TransactionType.INTEREST,
        date=date(2026, 2, 1),
        quantity=Decimal("0"),
        amount=Decimal("3.33"),
        currency="EUR",
        asset_event_id=auto_event.id,
    )
    session.add(tx)

    await session.commit()
    return {"auto_event_id": auto_event.id, "manual_event_id": manual_event.id, "tx_id": tx.id}


async def _count_prices(session: AsyncSession, asset_id: int) -> int:
    return int(
        (
            await session.execute(
                select(func.count()).select_from(PriceHistory).where(PriceHistory.asset_id == asset_id)
            )
        ).scalar()
        or 0
    )


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.asyncio
async def test_param_change_wipes_prices_and_autoevents_and_disconnects_tx():
    """#R6-4 symmetric wipe: prices + auto events wiped, manual survives, tx disconnected."""
    assert initialize_test_database(), "Failed to initialize test database"
    AssetProviderRegistry.auto_discover()

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        asset_id, assignment_id = await _create_asset_and_assign(session, _params_v1())
        seed = await _seed_stale_data(session, asset_id, assignment_id)

        # Sanity: stale data is in place.
        assert await _count_prices(session, asset_id) == 3
        session.expire_all()
        tx_before = await session.get(Transaction, seed["tx_id"])
        assert tx_before is not None and tx_before.asset_event_id == seed["auto_event_id"]

        # Trigger param change (same provider_code, different params).
        await AssetSourceManager.bulk_assign_providers(
            [
                FAProviderAssignmentItem(
                    asset_id=asset_id,
                    provider_code="scheduled_investment",
                    identifier="",
                    identifier_type=ProviderInputType.AUTO_GENERATED,
                    provider_params=_params_v2(),
                )
            ],
            session,
        )

        session.expire_all()
        # 1. All prices wiped.
        assert await _count_prices(session, asset_id) == 0, "prices not fully wiped"
        # 2. Auto event gone.
        assert await session.get(AssetEvent, seed["auto_event_id"]) is None, "provider-generated event leaked"
        # 3. Manual event preserved.
        manual = await session.get(AssetEvent, seed["manual_event_id"])
        assert manual is not None, "manual event wrongly wiped"
        assert manual.provider_assignment_id is None
        # 4. Transaction disconnected (asset_event_id = NULL) but still exists.
        tx_after = await session.get(Transaction, seed["tx_id"])
        assert tx_after is not None, "transaction deleted — should only be disconnected"
        assert tx_after.asset_event_id is None, f"tx still linked: asset_event_id={tx_after.asset_event_id}"
        # 5. Assignment still present (UPDATE, not DELETE/INSERT).
        assignment_after = await session.get(AssetProviderAssignment, assignment_id)
        assert assignment_after is not None, "assignment unexpectedly replaced"
        assert assignment_after.id == assignment_id, "assignment id changed — FK would break"


@pytest.mark.asyncio
async def test_same_params_does_not_wipe():
    """Negative control: re-assigning the SAME params must not delete anything."""
    assert initialize_test_database(), "Failed to initialize test database"
    AssetProviderRegistry.auto_discover()

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        params = _params_v1()
        asset_id, assignment_id = await _create_asset_and_assign(session, params)
        seed = await _seed_stale_data(session, asset_id, assignment_id)

        # Re-assign with IDENTICAL params — short-circuit path.
        await AssetSourceManager.bulk_assign_providers(
            [
                FAProviderAssignmentItem(
                    asset_id=asset_id,
                    provider_code="scheduled_investment",
                    identifier="",
                    identifier_type=ProviderInputType.AUTO_GENERATED,
                    provider_params=params,
                )
            ],
            session,
        )

        session.expire_all()
        # Nothing should have been touched.
        assert await _count_prices(session, asset_id) == 3
        assert await session.get(AssetEvent, seed["auto_event_id"]) is not None
        assert await session.get(AssetEvent, seed["manual_event_id"]) is not None
        tx = await session.get(Transaction, seed["tx_id"])
        assert tx is not None and tx.asset_event_id == seed["auto_event_id"]


@pytest.mark.asyncio
async def test_param_change_does_not_touch_other_assets():
    """Wipe is scoped to the affected asset only — siblings are untouched."""
    assert initialize_test_database(), "Failed to initialize test database"
    AssetProviderRegistry.auto_discover()

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        a1_id, a1_assign = await _create_asset_and_assign(session, _params_v1(), name_prefix="G13 Target")
        a2_id, a2_assign = await _create_asset_and_assign(session, _params_v1(), name_prefix="G13 Sibling")
        await _seed_stale_data(session, a1_id, a1_assign)
        sibling = await _seed_stale_data(session, a2_id, a2_assign)

        # Trigger param change on asset #1 ONLY.
        await AssetSourceManager.bulk_assign_providers(
            [
                FAProviderAssignmentItem(
                    asset_id=a1_id,
                    provider_code="scheduled_investment",
                    identifier="",
                    identifier_type=ProviderInputType.AUTO_GENERATED,
                    provider_params=_params_v2(),
                )
            ],
            session,
        )

        session.expire_all()
        # Asset #1 wiped.
        assert await _count_prices(session, a1_id) == 0
        # Asset #2 fully intact.
        assert await _count_prices(session, a2_id) == 3
        sib_auto = await session.get(AssetEvent, sibling["auto_event_id"])
        assert sib_auto is not None, "sibling auto event wrongly wiped"
        sib_tx = await session.get(Transaction, sibling["tx_id"])
        assert sib_tx is not None and sib_tx.asset_event_id == sibling["auto_event_id"]


