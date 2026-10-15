"""Wipe of an asset's market data when its currency changes (Policy D)."""

from __future__ import annotations

import json
from typing import Optional

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    AssetEvent,
    PriceHistory,
    Transaction,
)
from backend.app.services.assets import core
from backend.app.services.assets.base import AssetSourceError

logger = structlog.get_logger(__name__)


class CurrencyChangeOperations:
    """Wipe of an asset's market data when its currency changes."""

    @staticmethod
    async def wipe_market_data_for_currency_change(  # noqa: C901 — sequential count-then-delete steps, guard ifs
        asset_id: int,
        session: AsyncSession,
        dry_run: bool = False,
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
                on the frontend.

        Returns:
            Dict with keys ``prices``, ``events_manual``, ``events_provider``,
            ``linked_tx``, ``oldest``, ``newest`` (ISO strings or ``None``),
            ``dry_run``.

        Raises:
            AssetSourceError: if ``asset_id`` does not exist.
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

        # 4. Cache invalidation — history + current. The cache key is
        # ``(provider_code, identifier, identifier_type, params_hash, settings part)`` so we
        # rebuild it from the asset's current provider config. If the asset
        # has no provider assigned the keys simply won't be in the cache;
        # ``.delete`` is a no-op in that case.
        try:
            if asset.provider_code:
                params_dict: Optional[dict] = None
                if asset.provider_params:
                    try:
                        params_dict = json.loads(asset.provider_params)
                    except Exception:  # noqa: BLE001 — params may be corrupted; just skip hashing
                        params_dict = None
                cache_key = (
                    asset.provider_code,
                    asset.identifier or "",
                    str(asset.identifier_type),
                    core._provider_params_hash(params_dict),
                    await core.settings_cache_part_for(asset.provider_code),
                )
                core._asset_history_cache.delete(cache_key)
                core._asset_current_cache.delete(cache_key)
        except Exception as cache_err:  # noqa: BLE001 — non-fatal
            logger.warning(
                "wipe_market_data: cache invalidation skipped",
                extra={"asset_id": asset_id, "error": str(cache_err)},
            )

        logger.info(
            "Market data wiped for currency change",
            extra={
                "asset_id": asset_id,
                "prices_deleted": prices_count,
                "events_manual_deleted": events_manual_count,
                "events_provider_deleted": events_provider_count,
                "transactions_disconnected": linked_tx_count,
            },
        )

        return summary
