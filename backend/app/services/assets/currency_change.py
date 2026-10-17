"""Wipe of an asset's market data when its currency changes (Policy D)."""

from __future__ import annotations

from typing import Optional

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    AssetEvent,
    AssetProviderAssignment,
    PriceHistory,
    Transaction,
)
from backend.app.services.assets import core
from backend.app.services.assets.base import AssetSourceError
from backend.app.services.assets.split_guard import adjustments_count, splits_with_costless_adjustments

logger = structlog.get_logger(__name__)


class CurrencyChangeOperations:
    """Wipe of an asset's market data when its currency changes."""

    @staticmethod
    async def wipe_market_data_for_currency_change(  # noqa: C901 — sequential count-then-delete steps, guard ifs
        asset_id: int,
        session: AsyncSession,
        dry_run: bool = False,
        *,
        current_user_id: Optional[int] = None,
    ) -> dict:
        """Wipe **all** market data for an asset before a currency change.

        Policy D (see phase-07 closure plan §"Issue #R3-3"): when the user
        confirms a currency change, we wipe every series that was denominated
        in the old currency — prices, all events (manual + provider) — and
        disconnect any transaction still pointing at one of the deleted
        events (``transactions.asset_event_id = NULL``). Transactions
        themselves are preserved; it is the user's responsibility to decide
        whether to re-associate them to new events after re-sync.

        Rationale for the "totally symmetric" choice:
        * Prices in the old currency would mix with new-currency data after
          the change → hard-to-debug reports.
        * Events (dividends, interest, splits, …) carry a ``currency`` field
          too; a residual old-currency event is as inconsistent as a
          residual old-currency price.
        * We don't try to convert values via FX (Policy C): double-conversion
          accumulates rounding, manual events would be silently altered
          without user consent.

        Operations (inside a single transaction, in order):

        1. ``UPDATE transactions SET asset_event_id = NULL WHERE
           asset_event_id IN (SELECT id FROM asset_events WHERE asset_id=?)``
        2. ``DELETE FROM asset_events WHERE asset_id=?``
        3. ``DELETE FROM price_history WHERE asset_id=?``
        4. Invalidate per-asset history + current-price caches.

        Args:
            asset_id: target asset.
            session: active DB session (committed on success).
            dry_run: when ``True``, run only the counts and skip the
                destructive SQL. Useful for the pre-confirm summary panel
                on the frontend. A dry run never refuses.
            current_user_id: the user the request answers (the route passes
                the caller): a refusal names only the transactions that user
                can see; without one it names none (X-R47b).

        Returns:
            Dict with keys ``prices``, ``events_manual``, ``events_provider``,
            ``linked_tx``, ``oldest``, ``newest`` (ISO strings or ``None``),
            ``dry_run``.

        Raises:
            AssetSourceError: if ``asset_id`` does not exist
                (``ASSET_NOT_FOUND``); ``MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST``
                when a SPLIT of the asset has incoming adjustments without a
                purchase cost (see ``_reject_wipe_of_costless_split_adjustments``):
                nothing is written.
        """
        asset = (await session.execute(select(Asset).where(Asset.id == asset_id))).scalar_one_or_none()
        if not asset:
            raise AssetSourceError(f"Asset {asset_id} not found", "ASSET_NOT_FOUND")

        # --- Counters -------------------------------------------------------
        prices_res = await session.execute(select(func.count()).select_from(PriceHistory).where(PriceHistory.asset_id == asset_id))
        prices_count = int(prices_res.scalar() or 0)

        events_manual_res = await session.execute(
            select(func.count())
            .select_from(AssetEvent)
            .where(
                AssetEvent.asset_id == asset_id,
                AssetEvent.provider_assignment_id.is_(None),
            )
        )
        events_manual_count = int(events_manual_res.scalar() or 0)

        events_provider_res = await session.execute(
            select(func.count())
            .select_from(AssetEvent)
            .where(
                AssetEvent.asset_id == asset_id,
                AssetEvent.provider_assignment_id.is_not(None),
            )
        )
        events_provider_count = int(events_provider_res.scalar() or 0)

        linked_tx_res = await session.execute(select(func.count()).select_from(Transaction).where(Transaction.asset_event_id.in_(select(AssetEvent.id).where(AssetEvent.asset_id == asset_id))))
        linked_tx_count = int(linked_tx_res.scalar() or 0)

        oldest_date = None
        newest_date = None
        if prices_count > 0:
            oldest_res = await session.execute(select(func.min(PriceHistory.date)).where(PriceHistory.asset_id == asset_id))
            newest_res = await session.execute(select(func.max(PriceHistory.date)).where(PriceHistory.asset_id == asset_id))
            oldest_date = oldest_res.scalar()
            newest_date = newest_res.scalar()

        summary = {
            "prices": prices_count,
            "events_manual": events_manual_count,
            "events_provider": events_provider_count,
            "linked_tx": linked_tx_count,
            "oldest": oldest_date.isoformat() if oldest_date else None,
            "newest": newest_date.isoformat() if newest_date else None,
            "dry_run": dry_run,
        }

        if dry_run:
            return summary

        await CurrencyChangeOperations._reject_wipe_of_costless_split_adjustments(session, asset_id, current_user_id)

        # The provider whose cached answers step 4 drops, as plain values: the commit below expires the row's attributes.
        assignment = (await session.execute(select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == asset_id))).scalar_one_or_none()
        cached_by = (assignment.provider_code, assignment.identifier, assignment.identifier_type, assignment.provider_params) if assignment else None

        # --- Destructive SQL (single transaction) ---------------------------
        # 1. Disconnect linked transactions first (pre-DELETE to avoid FK RESTRICT).
        if linked_tx_count > 0:
            await session.execute(Transaction.__table__.update().where(Transaction.asset_event_id.in_(select(AssetEvent.id).where(AssetEvent.asset_id == asset_id))).values(asset_event_id=None))

        # 2. Delete all events.
        if events_manual_count + events_provider_count > 0:
            await session.execute(delete(AssetEvent).where(AssetEvent.asset_id == asset_id))

        # 3. Delete all prices.
        if prices_count > 0:
            await session.execute(delete(PriceHistory).where(PriceHistory.asset_id == asset_id))

        await session.commit()

        # 4. Cache invalidation — history + current, keyed from the asset's provider assignment as a call keys them
        # (core.asset_cache_key). An asset without a provider has nothing cached.
        try:
            if cached_by is not None:
                await core.drop_asset_cache_entries(*cached_by)
        except Exception as cache_err:  # noqa: BLE001 — non-fatal
            logger.warning("wipe_market_data: cache invalidation skipped", asset_id=asset_id, error=str(cache_err))

        logger.info(
            "Market data wiped for currency change",
            asset_id=asset_id,
            prices_deleted=prices_count,
            events_manual_deleted=events_manual_count,
            events_provider_deleted=events_provider_count,
            transactions_disconnected=linked_tx_count,
        )

        return summary

    @staticmethod
    async def _reject_wipe_of_costless_split_adjustments(session: AsyncSession, asset_id: int, current_user_id: Optional[int]) -> None:
        """X-R48: refuse the wipe while a SPLIT of the asset has incoming adjustments without a purchase cost.

        The wipe deletes every event of the asset. Linked to a SPLIT, an incoming ADJUSTMENT without a cost only
        rescales the position; with the SPLIT gone it would be an acquisition of unknown cost (MISSING_COST_BASIS) — the
        rule of P-10, which refuses a retype of such a SPLIT; ``split_guard.splits_with_costless_adjustments`` finds them
        and names them as the caller may see them (R13-SEC7, X-R47b).

        Raises:
            AssetSourceError(code="MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST"): ``details["splits"]``, one per such
                SPLIT by date then id: ``event_id``, ``date``, ``transaction_ids`` (those the caller can see, sorted) and
                ``hidden_transactions_count``. The message gives the totals only.
        """
        event_rows = (await session.execute(select(AssetEvent.id, AssetEvent.date).where(AssetEvent.asset_id == asset_id))).all()
        splits = await splits_with_costless_adjustments(session, [(int(event_id), event_date) for event_id, event_date in event_rows], current_user_id)
        if not splits:
            return
        raise AssetSourceError(
            f"MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST: {len(splits)} split(s) of this asset have {adjustments_count(splits)} linked adjustment(s) without a purchase cost; give them a cost before deleting the asset's events",
            "MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST",
            {"splits": splits},
        )
