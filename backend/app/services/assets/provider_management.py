"""Provider assignment and probe operations."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import date as date_type
from datetime import timedelta
from typing import Dict, List, Optional

import structlog
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    AssetEvent,
    AssetProviderAssignment,
    PriceHistory,
    ProviderInputType,
    Transaction,
)
from backend.app.schemas import (
    FABulkRemoveResponse,
    FAProviderAssignmentItem,
    FAProviderAssignmentResult,
    FAProviderRemovalResult,
)
from backend.app.schemas.provider import (
    FAProviderConfigBase,
    FAProviderKind,
    FAProviderProbeResponse,
    ProbeCurrentPriceResult,
    ProbeHistoryResult,
    ProbeMetadataResult,
    ProbeOperation,
)
from backend.app.services.assets import core
from backend.app.services.assets.base import (
    AssetSourceError,
    AssetSourceProvider,
)
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.assets.split_guard import adjustments_count, splits_with_costless_adjustments
from backend.app.utils.runtime.cooldown import RateLimitedError

logger = structlog.get_logger(__name__)

_PROVIDER_WIPE_REFUSAL = "PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST"


def _params_to_store(raw_params: object) -> object:
    """An item's ``provider_params`` as the assignment stores them: a dict as JSON text, anything else as it is."""
    return json.dumps(raw_params) if isinstance(raw_params, dict) else raw_params


def _is_parametric(code: str) -> bool:
    """Whether the provider ``code`` invents its series from the assignment's params (PARAMETRIC_GENERATION)."""
    inst = AssetProviderRegistry.get_provider_instance(code)
    return inst is not None and inst.provider_kind == FAProviderKind.PARAMETRIC_GENERATION


def _wipe_reason(stored_code: str, stored_params: object, code: str, params: object) -> str:
    """Why saving ``code`` with ``params`` over the stored assignment wipes the asset's prices and the events it generated
    (#R3-4), or "" when it keeps them: new params of a parametric provider, or leaving one. One answer for the write loop
    of ``bulk_assign_providers`` and for its check before it (X-R49)."""
    if stored_code == code:
        return "params changed" if (stored_params or "") != (params or "") and _is_parametric(code) else ""
    # Leaving a parametric provider is at least as invalidating as
    # changing its params: the whole series was *invented* from
    # provider_params, so under a market provider it is not history,
    # it is fiction. Keeping it also poisons the next sync, which
    # resumes from the day after the last stored price and therefore
    # never backfills the real past.
    return "provider changed" if _is_parametric(stored_code) else ""


def _probe_failure_fields(error: Exception) -> dict:
    """The failure fields of a probe operation: the message, the code, its parameters, and the wait of a pause.

    A ``RATE_LIMITED`` refusal (X8) carries ``retry_after``, the seconds before the provider may be called again: on
    the result and in ``error_details``, so the interface can show the local time the pause ends.
    """
    retry_after = error.retry_after if isinstance(error, RateLimitedError) else None
    details = dict(getattr(error, "details", None) or {})
    if retry_after is not None:
        details["retry_after"] = retry_after
    return {
        "error": str(error),
        "error_code": getattr(error, "error_code", None),
        "error_details": core._json_safe_details(details),
        "retry_after": retry_after,
    }


class ProviderManagementOperations:
    """Provider assignment and probe operations."""

    @staticmethod
    async def bulk_assign_providers(
        assignments: List[FAProviderAssignmentItem],
        session: AsyncSession,
        *,
        current_user_id: Optional[int] = None,
    ) -> list[FAProviderAssignmentResult]:
        """
        Bulk assign/update providers to assets (PRIMARY bulk method).

        Args:
            assignments: List of FAProviderAssignmentItem
            session: AsyncSession
            current_user_id: the user the request answers (the route passes the caller): a refusal names only the
                transactions that user can see; without one it names none (X-R47b).

        Returns:
            List of FAProviderAssignmentResult

        Raises:
            AssetSourceError(code="PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST"): X-R49 — an item would wipe a parametric
                provider's events while a SPLIT among them has incoming adjustments without a purchase cost (the rule of
                P-10: they would become acquisitions of unknown cost). ``details`` = ``asset_id``, ``item_index`` and
                ``splits`` as ``split_guard`` names them. Checked before the request's first write: nothing is written.

        Optimized: 1 delete + 1 insert query
        """
        if not assignments:
            return []

        results = []
        asset_ids = [a.asset_id for a in assignments]

        # UPSERT pattern: SELECT existing, UPDATE if exists, INSERT if new
        # This preserves assignment IDs across reconfigurations,
        # keeping AssetEvent.provider_assignment_id FK valid.
        existing_stmt = select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id.in_(asset_ids))
        existing_result = await session.execute(existing_stmt)
        existing_map: Dict[int, AssetProviderAssignment] = {row.asset_id: row for row in existing_result.scalars().all()}

        # X-R49: the whole request is checked before its first write, so a refusal leaves nothing behind.
        await ProviderManagementOperations._reject_wipes_of_costless_split_adjustments(assignments, existing_map, session, current_user_id)

        for a in assignments:
            params_to_store = _params_to_store(a.provider_params)

            # Map identifier_type to valid ProviderInputType before storing
            # Handles both ProviderInputType values ("TICKER","URL","AUTO_GENERATED")
            # and IdentifierType values ("OTHER"→URL, "UUID"→AUTO_GENERATED)
            mapped_type = a.identifier_type
            try:
                ProviderInputType(mapped_type)
            except ValueError:
                pit = AssetSourceProvider.map_identifier_type_to_input_type(mapped_type)
                mapped_type = pit.value if pit else ProviderInputType.URL.value

            # Handle identifier: if AUTO_GENERATED and empty/None, leave None
            identifier_val = a.identifier
            if mapped_type == ProviderInputType.AUTO_GENERATED.value and not identifier_val:
                identifier_val = None

            existing = existing_map.get(a.asset_id)
            if existing:
                # #R3-4: for PARAMETRIC_GENERATION providers, changing provider_params
                # (schedule, maturation_frequency, annual_rate, …) invalidates the
                # generated price series deterministically — the FE shows an explicit
                # ConfirmDialog before sending the PATCH, so here we trust the incoming
                # request and atomically wipe the existing prices + invalidate the
                # in-memory caches. The subsequent sync call (triggered by the FE after
                # save) will regenerate with new params.
                #
                # Online scrapers (yfinance, justetf, cssscraper, …) are NOT affected:
                # their historical data came from an external source, so a params change
                # (e.g. renaming a secondary ticker) doesn't invalidate the past candles.
                # The gating is via ``provider_kind`` on the base class — no hardcoded
                # provider_code check.
                wipe_reason = _wipe_reason(existing.provider_code, existing.provider_params, a.provider_code, params_to_store)

                if wipe_reason:
                    # 1. Delete ALL prices for this asset (full wipe).
                    #
                    # #R4-3 (2026-04-23): previously we scoped by
                    # ``source_plugin_key == a.provider_code``, but
                    # ``bulk_upsert_prices`` unconditionally hardcoded
                    # ``source_plugin_key="MANUAL"`` for every inserted row
                    # (fixed 2026-07-14 — see its ``source_plugin_key`` param,
                    # L1207), so the DELETE matched **zero** rows and
                    # old stale points from a previous schedule survived the
                    # regen. The user observed weekly points (new regen) and
                    # daily leftovers (pre-existing rows) mixed in the same
                    # series, producing a misleading "flat line" chart.
                    #
                    # Semantically correct REGARDLESS of the above fix: an
                    # asset bound to a parametric provider derives its
                    # *entire* price series from the provider_params. A
                    # change of params invalidates the whole series,
                    # mirroring the R3-3 currency-change wipe policy.
                    # Manually imported points (if any) are also wiped —
                    # the user must re-import after the param change if
                    # needed (same responsibility model as R3-3).
                    deleted_rows_result = await session.execute(
                        delete(PriceHistory).where(
                            PriceHistory.asset_id == a.asset_id,
                        )
                    )
                    deleted_count = deleted_rows_result.rowcount or 0
                    # 1b. Symmetric wipe of **auto-generated** events
                    # (#R6-4, 2026-04-24): before this fix, a param change
                    # wiped only the prices but left the previously
                    # generated events in place. The result was an asset
                    # showing stale INTEREST / MATURITY_SETTLEMENT events
                    # computed from the *old* schedule, plus new events
                    # that will be regenerated on next sync — the two
                    # sets can overlap or contradict each other (e.g.
                    # an old coupon on Jul 1 at rate 0.05 vs a new one
                    # at rate 0.12), and ``get_current_value`` sees the
                    # stale subtractive events so its output is
                    # essentially undefined.
                    #
                    # Policy: mirror the R3-3 wipe for events too —
                    # delete all events generated by THIS provider
                    # assignment (``provider_assignment_id ==
                    # existing.id``). Manual events
                    # (``provider_assignment_id IS NULL``) are
                    # preserved: they are user-owned and survive param
                    # changes. Transactions linked to the deleted
                    # events are disconnected (SET asset_event_id =
                    # NULL) — same responsibility model as Policy D:
                    # the user can reattach them to the regenerated
                    # events if needed.
                    event_ids_subq = select(AssetEvent.id).where(
                        and_(
                            AssetEvent.asset_id == a.asset_id,
                            AssetEvent.provider_assignment_id == existing.id,
                        )
                    )
                    disconnect_result = await session.execute(Transaction.__table__.update().where(Transaction.asset_event_id.in_(event_ids_subq)).values(asset_event_id=None))
                    disconnected_tx = disconnect_result.rowcount or 0
                    deleted_events_result = await session.execute(
                        delete(AssetEvent).where(
                            and_(
                                AssetEvent.asset_id == a.asset_id,
                                AssetEvent.provider_assignment_id == existing.id,
                            )
                        )
                    )
                    deleted_events = deleted_events_result.rowcount or 0
                    # 2. Invalidate outer caches for the OLD params hash (the new
                    #    hash produces a different cache_key → natural MISS, but we
                    #    also drop the stale entry explicitly so it doesn't linger
                    #    for 15 min).
                    try:
                        await core.drop_asset_cache_entries(existing.provider_code, existing.identifier, existing.identifier_type, existing.provider_params)
                    except Exception as cache_err:
                        logger.debug(f"Cache invalidation skipped for asset {a.asset_id}: {cache_err}")
                    logger.info(
                        "parametric provider '%s' %s for asset %s — wiped %d price row(s), %d event row(s), disconnected %d transaction(s), invalidated cache",
                        existing.provider_code,
                        wipe_reason,
                        a.asset_id,
                        deleted_count,
                        deleted_events,
                        disconnected_tx,
                    )

                # UPDATE existing assignment (preserves id → FK stays valid)
                existing.provider_code = a.provider_code
                existing.identifier = identifier_val
                existing.identifier_type = mapped_type
                existing.provider_params = params_to_store
            else:
                # INSERT new assignment
                new_assignment = AssetProviderAssignment(
                    asset_id=a.asset_id,
                    provider_code=a.provider_code,
                    identifier=identifier_val,
                    identifier_type=mapped_type,
                    provider_params=params_to_store,
                    last_fetch_at=None,
                )
                session.add(new_assignment)

        # Remove assignments for asset_ids no longer in the batch
        # (only relevant when called from full-replace endpoints)
        await session.commit()

        # Build results (no auto-populate — metadata comes via explicit refresh/probe)
        for assignment in assignments:
            result = FAProviderAssignmentResult(
                asset_id=assignment.asset_id,
                success=True,
                message=f"Provider {assignment.provider_code} assigned",
                fields_detail=None,
            )

            results.append(result)

        return results

    @staticmethod
    async def _reject_wipes_of_costless_split_adjustments(
        assignments: List[FAProviderAssignmentItem],
        existing_map: Dict[int, AssetProviderAssignment],
        session: AsyncSession,
        current_user_id: Optional[int],
    ) -> None:
        """X-R49: refuse the request when an item would wipe the events a parametric provider generated
        (``_wipe_reason``) while a SPLIT among them has linked incoming adjustments without a purchase cost: with the
        SPLIT gone they would be acquisitions of unknown cost (the rule of P-10). Manual events survive the wipe, so
        they are not read.

        Run before the request's first write, so a refusal leaves nothing behind, the items before it included. The
        items are followed in order, as the write loop does: an asset named twice is compared with its previous item.

        Raises:
            AssetSourceError(code="PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST"): ``details`` = ``asset_id``,
                ``item_index`` (the item's position in the request) and ``splits`` as ``split_guard`` names them for
                ``current_user_id``; the message gives the totals only.
        """
        stored = {asset_id: (row.provider_code, row.provider_params) for asset_id, row in existing_map.items()}
        for item_index, item in enumerate(assignments):
            if item.asset_id not in stored:
                continue
            params = _params_to_store(item.provider_params)
            if _wipe_reason(*stored[item.asset_id], item.provider_code, params):
                assignment_id = existing_map[item.asset_id].id
                rows = (await session.execute(select(AssetEvent.id, AssetEvent.date).where(AssetEvent.asset_id == item.asset_id, AssetEvent.provider_assignment_id == assignment_id))).all()
                splits = await splits_with_costless_adjustments(session, [(int(event_id), event_date) for event_id, event_date in rows], current_user_id)
                if splits:
                    raise AssetSourceError(
                        f"{_PROVIDER_WIPE_REFUSAL}: this change would delete {len(splits)} split(s) the provider generated, with {adjustments_count(splits)} linked adjustment(s) without a purchase cost; give them a cost first",
                        _PROVIDER_WIPE_REFUSAL,
                        {"asset_id": item.asset_id, "item_index": item_index, "splits": splits},
                    )
            stored[item.asset_id] = (item.provider_code, params)

    @staticmethod
    async def bulk_remove_providers(asset_ids: list[int], session: AsyncSession) -> FABulkRemoveResponse:
        """
        Bulk remove provider assignments (PRIMARY bulk method).

        Args:
            asset_ids: List of asset IDs
            session: Database session

        Returns:
            FABulkRemoveResponse with results and success count

        Optimized: 1 DELETE query with WHERE IN
        """
        if not asset_ids:
            return FABulkRemoveResponse(results=[], success_count=0)
        await session.execute(delete(AssetProviderAssignment).where(AssetProviderAssignment.asset_id.in_(asset_ids)))
        await session.commit()
        results = [
            FAProviderRemovalResult(
                asset_id=aid,
                success=True,
                deleted_count=1,  # Always 1 for successful provider removal
                message="Provider removed",
            )
            for aid in asset_ids
        ]
        return FABulkRemoveResponse(results=results, success_count=len(results), errors=[])

    @staticmethod
    async def get_asset_provider(asset_id: int, session: AsyncSession) -> Optional[AssetProviderAssignment]:
        """
        Fetch provider assignment for asset.

        Args:
            asset_id: Asset ID
            session: Database session

        Returns:
            AssetProviderAssignment or None if not assigned
        """
        result = await session.execute(select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == asset_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def probe_provider_config(  # noqa: C901 — three parallel probe closures, duplicated try/except mapping
        config: FAProviderConfigBase,
        operations: list[ProbeOperation],
        *,
        user_id: int | None = None,
    ) -> FAProviderProbeResponse:
        """
        Probe a provider configuration without persisting anything.

        Executes requested operations in **parallel** via asyncio.gather
        and returns results with per-operation execution time.

        Accepts FAProviderConfigBase — child objects (FAProviderAssignmentItem,
        FAProviderProbeRequest) pass directly without field copying.

        ``user_id`` is the user who probes: the provider receives that user's settings too. A provider whose
        required settings are missing answers every operation with ``NOT_CONFIGURED``.
        """
        provider = await core.configured_provider(config.provider_code, user_id=user_id)
        if not provider:
            raise AssetSourceError(f"Unknown provider: {config.provider_code}", "UNKNOWN_PROVIDER")

        params = core._parse_provider_params(config.provider_params)
        total_start = time.monotonic_ns()

        # Map ProviderInputType (from frontend) to IdentifierType (for provider methods)
        mapped_id_type = AssetSourceProvider.map_input_type_to_identifier_type(config.identifier_type)
        # The part of the provider a pause after «too many requests» applies to (the host of a scraped site)
        scope = core.cooldown_scope_for(provider, config.identifier, mapped_id_type, params)

        # Provider URL (always computed, synchronous); withheld if the plugin put a secret in it (it is shown to the user)
        provider_url = core.public_asset_url(provider, provider.get_asset_url(config.identifier, mapped_id_type, params))

        # --- Build async tasks for each requested operation ---

        async def _probe_current_price() -> ProbeCurrentPriceResult:
            op_start = time.monotonic_ns()
            try:
                value = await core.call_provider(provider, lambda: provider.get_current_value(config.identifier, mapped_id_type, params), timeout=15.0, scope=scope)
                return ProbeCurrentPriceResult(
                    success=True,
                    value=value.value,
                    currency=value.currency,
                    as_of_date=str(value.as_of_date),
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )
            except TimeoutError:
                return ProbeCurrentPriceResult(
                    success=False,
                    error="Timeout after 15s",
                    error_code="TIMEOUT",
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )
            except Exception as e:
                return ProbeCurrentPriceResult(
                    success=False,
                    **_probe_failure_fields(e),
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )

        async def _probe_history() -> ProbeHistoryResult:
            op_start = time.monotonic_ns()
            try:
                end_date = date_type.today()
                start_date = end_date - timedelta(days=7)
                hist = await core.call_provider(provider, lambda: provider.get_history_value(config.identifier, mapped_id_type, params, start_date, end_date), timeout=15.0, scope=scope)
                points = hist.prices if hist else []
                date_range_str = None
                sample = None
                if points:
                    dates = [p.date for p in points]
                    date_range_str = f"{min(dates)} → {max(dates)}"
                    sample = [{"date": str(p.date), "close": round(float(p.close), 2)} for p in points[:10]]
                return ProbeHistoryResult(
                    success=True,
                    points_count=len(points),
                    date_range=date_range_str,
                    sample_prices=sample,
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )
            except TimeoutError:
                return ProbeHistoryResult(
                    success=False,
                    error="Timeout after 15s",
                    error_code="TIMEOUT",
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )
            except Exception as e:
                return ProbeHistoryResult(
                    success=False,
                    **_probe_failure_fields(e),
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )

        async def _probe_metadata() -> ProbeMetadataResult:
            op_start = time.monotonic_ns()
            try:
                patch = await core.call_provider(provider, lambda: provider.fetch_asset_metadata(config.identifier, mapped_id_type, params), timeout=15.0, scope=scope)
                return ProbeMetadataResult(
                    success=patch is not None,
                    patch_data=patch.model_dump(mode="json") if patch else None,
                    error=None if patch else "Provider returned no metadata",
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )
            except TimeoutError:
                return ProbeMetadataResult(
                    success=False,
                    error="Timeout after 15s",
                    error_code="TIMEOUT",
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )
            except Exception as e:
                return ProbeMetadataResult(
                    success=False,
                    **_probe_failure_fields(e),
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )

        # --- Schedule requested operations in parallel ---
        tasks: dict[str, asyncio.Task] = {}
        if ProbeOperation.CURRENT_PRICE in operations:
            tasks["current_price"] = asyncio.ensure_future(_probe_current_price())
        if ProbeOperation.HISTORY in operations:
            tasks["history"] = asyncio.ensure_future(_probe_history())
        if ProbeOperation.METADATA in operations:
            tasks["metadata"] = asyncio.ensure_future(_probe_metadata())

        # Await all tasks in parallel
        if tasks:
            await asyncio.gather(*tasks.values(), return_exceptions=True)

        total_ms = (time.monotonic_ns() - total_start) // 1_000_000

        return FAProviderProbeResponse(
            provider_code=config.provider_code,
            identifier=config.identifier,
            total_execution_time_ms=total_ms,
            provider_url=provider_url,
            current_price=tasks["current_price"].result() if "current_price" in tasks else None,
            history=tasks["history"].result() if "history" in tasks else None,
            metadata=tasks["metadata"].result() if "metadata" in tasks else None,
        )
