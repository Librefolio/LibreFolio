"""Wipe of an asset's market data when its currency changes (Policy D, N68: the splits stay)."""

from __future__ import annotations

from typing import Sequence

import structlog
from sqlalchemy import and_, delete, func, select
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
from backend.app.services.financial_math.splits import not_split_event_condition, split_event_condition

logger = structlog.get_logger(__name__)

#: What the provider cache of an asset is keyed by: ``core.drop_asset_cache_entries(*key)``.
ProviderCacheKey = tuple


def events_that_go(asset_ids: Sequence[int]):
    """The condition of the events a currency change deletes: every event of the assets except the SPLITs.

    A dividend or an interest carries a currency, a split is a ratio: it means the same in any currency, and the
    adjustments linked to it keep their meaning (N68, developer decision of 19/10/2026).
    """
    return and_(AssetEvent.asset_id.in_(list(asset_ids)), not_split_event_condition())


async def delete_market_data_of_assets(session: AsyncSession, asset_ids: Sequence[int]) -> None:
    """Delete the prices and the non-SPLIT events of ``asset_ids`` and disconnect the transactions linked to those events.

    Three statements whatever the number of assets, no commit (the caller's transaction): the transactions stay, with
    ``asset_event_id`` set to NULL first (pre-DELETE, the FK is RESTRICT); the SPLIT events and the transactions linked to
    them are not touched.
    """
    ids = list(asset_ids)
    if not ids:
        return
    event_ids = select(AssetEvent.id).where(events_that_go(ids))
    await session.execute(Transaction.__table__.update().where(Transaction.asset_event_id.in_(event_ids)).values(asset_event_id=None))
    await session.execute(delete(AssetEvent).where(events_that_go(ids)))
    await session.execute(delete(PriceHistory).where(PriceHistory.asset_id.in_(ids)))


async def provider_cache_keys(session: AsyncSession, asset_ids: Sequence[int]) -> list[ProviderCacheKey]:
    """The provider cache keys of the assets, as plain values: the commit that follows expires the rows' attributes.

    One query whatever the number of assets. An asset without a provider has nothing cached.
    """
    ids = list(asset_ids)
    if not ids:
        return []
    assignments = (await session.execute(select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id.in_(ids)))).scalars().all()
    return [(assignment.provider_code, assignment.identifier, assignment.identifier_type, assignment.provider_params) for assignment in assignments]


async def drop_provider_caches(keys: Sequence[ProviderCacheKey], *, asset_ids: Sequence[int] = ()) -> None:
    """Drop the history and current-price entries cached for ``keys``, keyed as a call keys them (``core.asset_cache_key``).

    Non-fatal: the data is already committed, a cache that stays only serves old values until it expires.
    """
    for key in keys:
        try:
            await core.drop_asset_cache_entries(*key)
        except Exception as cache_err:  # noqa: BLE001 — isolation boundary: the commit already happened
            logger.warning("wipe_market_data: cache invalidation skipped", asset_ids=list(asset_ids), error=str(cache_err), exc_info=cache_err)


class CurrencyChangeOperations:
    """Wipe of an asset's market data when its currency changes."""

    @staticmethod
    async def wipe_market_data_for_currency_change(  # noqa: C901 — sequential count-then-delete steps
        asset_id: int,
        session: AsyncSession,
        dry_run: bool = False,
    ) -> dict:
        """Wipe the market data an asset's currency change deletes, or count it (``dry_run``).

        Policy D (phase-07 closure plan §"Issue #R3-3"), as N68 (19/10/2026) changed it: the prices and every event
        that is not a SPLIT go, and the transactions still pointing at one of the deleted events are disconnected
        (``transactions.asset_event_id = NULL``). Transactions themselves are preserved, and so are the SPLIT events with
        the transactions linked to them (the adjustments of a split keep their link and their cost). The user can link
        the disconnected transactions again afterwards (``GET /transactions/event-reconciliation``).

        Rationale for deleting rather than converting:
        * Prices in the old currency would mix with new-currency data after the change → hard-to-debug reports.
        * Events (dividends, interest, ...) carry a ``currency`` field too; a residual old-currency event is as
          inconsistent as a residual old-currency price.
        * We don't try to convert values via FX (Policy C): double-conversion accumulates rounding, manual events would
          be silently altered without user consent.

        The same work is done, in the same call, by ``PATCH /assets`` when it changes a currency
        (``AssetCRUDService.patch_assets_bulk``): this endpoint stays for a caller who wants to wipe on its own, and its
        dry run is what the interface shows before the change.

        Operations (inside a single transaction, in order):

        1. ``UPDATE transactions SET asset_event_id = NULL`` for the events that go
        2. ``DELETE FROM asset_events`` for the events that go
        3. ``DELETE FROM price_history WHERE asset_id=?``
        4. Invalidate per-asset history + current-price caches.

        Args:
            asset_id: target asset.
            session: active DB session (committed on success).
            dry_run: when ``True``, run only the counts and skip the destructive SQL.

        Returns:
            Dict with keys ``prices``, ``events_manual``, ``events_provider`` (the events that go, SPLITs not counted),
            ``splits_kept`` (the SPLIT events that stay), ``linked_tx`` (transactions linked to the events that go),
            ``oldest``, ``newest`` (the price range, ISO strings or ``None``) and ``dry_run``.

        Raises:
            AssetSourceError: ``ASSET_NOT_FOUND`` if ``asset_id`` does not exist.
        """
        asset = (await session.execute(select(Asset).where(Asset.id == asset_id))).scalar_one_or_none()
        if not asset:
            raise AssetSourceError(f"Asset {asset_id} not found", "ASSET_NOT_FOUND")

        # --- Counters -------------------------------------------------------
        prices_res = await session.execute(select(func.count()).select_from(PriceHistory).where(PriceHistory.asset_id == asset_id))
        prices_count = int(prices_res.scalar() or 0)

        events_manual_res = await session.execute(select(func.count()).select_from(AssetEvent).where(events_that_go([asset_id]), AssetEvent.provider_assignment_id.is_(None)))
        events_manual_count = int(events_manual_res.scalar() or 0)

        events_provider_res = await session.execute(select(func.count()).select_from(AssetEvent).where(events_that_go([asset_id]), AssetEvent.provider_assignment_id.is_not(None)))
        events_provider_count = int(events_provider_res.scalar() or 0)

        splits_kept_res = await session.execute(select(func.count()).select_from(AssetEvent).where(AssetEvent.asset_id == asset_id, split_event_condition()))
        splits_kept_count = int(splits_kept_res.scalar() or 0)

        linked_tx_res = await session.execute(select(func.count()).select_from(Transaction).where(Transaction.asset_event_id.in_(select(AssetEvent.id).where(events_that_go([asset_id])))))
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
            "splits_kept": splits_kept_count,
            "linked_tx": linked_tx_count,
            "oldest": oldest_date.isoformat() if oldest_date else None,
            "newest": newest_date.isoformat() if newest_date else None,
            "dry_run": dry_run,
        }

        if dry_run:
            return summary

        cache_keys = await provider_cache_keys(session, [asset_id])

        await delete_market_data_of_assets(session, [asset_id])
        await session.commit()

        await drop_provider_caches(cache_keys, asset_ids=[asset_id])

        logger.info(
            "Market data wiped for currency change",
            asset_id=asset_id,
            prices_deleted=prices_count,
            events_manual_deleted=events_manual_count,
            events_provider_deleted=events_provider_count,
            splits_kept=splits_kept_count,
            transactions_disconnected=linked_tx_count,
        )

        return summary
