"""Asset event persistence operations."""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Optional

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    AssetEvent,
    BrokerUserAccess,
    Transaction,
    User,
)
from backend.app.schemas.assets.events import FAAssetEventPoint, FAAssetEventPointOut, FAEventBulkDeleteResponse, FAEventDeleteItemResult, FAEventQueryResult, FAEventUpsertPoint
from backend.app.schemas.common import (
    Currency,
    FxBackwardFillInfo,
)
from backend.app.services.assets.base import AssetSourceError
from backend.app.services.assets.price_store import PRICE_UPSERT_CHUNK_SIZE
from backend.app.services.fx.fx import convert_bulk
from backend.app.utils.datetime_utils import utcnow

# The natural key of an asset event within one source: (date, type value).
_EventKey = tuple[date, str]


class EventStoreOperations:
    """Asset event persistence operations."""

    @staticmethod
    async def _upsert_asset_events(
        session: AsyncSession,
        asset_id: int,
        events: list[dict | FAAssetEventPoint],
        provider_assignment_id: Optional[int],
        default_currency: str,
    ) -> int:
        """Upsert the events of one source (a provider assignment, or manual) in place.

        Incoming events match the stored rows of the SAME source on (asset_id, date,
        type); rows of another source on that key are never touched. A matched row is
        updated in place and keeps its id, so the transactions realising it
        (``transactions.asset_event_id``) stay linked. DELETE + INSERT is not an
        option: that foreign key is ``ON DELETE RESTRICT``, so deleting a linked row
        fails (a provider refresh used to report "Event upsert failed").

        Per key, the stored rows end up as many as the incoming events, as with the
        former DELETE + INSERT:

        - stored rows, lowest id first, are paired with the incoming events and updated;
        - extra incoming events are inserted;
        - surplus stored rows (legacy same-key duplicates: no unique index forbids
          them) collapse onto the lowest id, after their transactions are re-pointed
          to it.

        Committed in slices of ``PRICE_UPSERT_CHUNK_SIZE`` keys for the same reason as
        bulk_upsert_prices: one transaction spanning every event would hold SQLite's
        single write lock for the whole loop.

        Args:
            session: Database session
            asset_id: Asset ID
            events: List of FAAssetEventPoint or dicts (parsed via Pydantic)
            provider_assignment_id: FK to asset_provider_assignments.id (None = manual)
            default_currency: Fallback currency

        Returns:
            Number of events upserted
        """
        if not events:
            return 0

        groups: dict[_EventKey, list[FAAssetEventPoint]] = {}
        for raw_evt in events:
            # Parse through Pydantic if raw dict; if already FAAssetEventPoint, use directly
            evt = raw_evt if isinstance(raw_evt, FAAssetEventPoint) else FAAssetEventPoint(**raw_evt)
            groups.setdefault((evt.date, str(evt.type)), []).append(evt)

        keys = list(groups)
        for chunk_start in range(0, len(keys), PRICE_UPSERT_CHUNK_SIZE):
            chunk_keys = keys[chunk_start : chunk_start + PRICE_UPSERT_CHUNK_SIZE]
            # When provider_assignment_id is None, SQLAlchemy generates IS NULL which is correct
            stored_stmt = (
                select(AssetEvent)
                .where(
                    AssetEvent.asset_id == asset_id,
                    AssetEvent.provider_assignment_id == provider_assignment_id,
                    AssetEvent.date.in_(sorted({day for day, _ in chunk_keys})),
                )
                .order_by(AssetEvent.id)
            )
            stored: dict[_EventKey, list[AssetEvent]] = {}
            for row in (await session.execute(stored_stmt)).scalars().all():
                stored.setdefault((row.date, str(row.type)), []).append(row)
            for key in chunk_keys:
                await EventStoreOperations._write_event_group(session, asset_id, provider_assignment_id, default_currency, groups[key], stored.get(key, []))
            await session.commit()

        return len(events)

    @staticmethod
    async def _write_event_group(
        session: AsyncSession,
        asset_id: int,
        provider_assignment_id: Optional[int],
        default_currency: str,
        incoming: list[FAAssetEventPoint],
        stored: list[AssetEvent],
    ) -> None:
        """Make the stored rows of one (date, type) key match ``incoming``, in place (see ``_upsert_asset_events``)."""
        now = utcnow()
        # AssetEvent has no before_update listener: updated_at is set here.
        for row, evt in zip(stored, incoming, strict=False):
            row.value = evt.value.amount
            row.currency = evt.value.code or default_currency
            row.notes = evt.notes
            row.updated_at = now
        session.add_all(
            [
                AssetEvent(
                    asset_id=asset_id,
                    date=evt.date,
                    type=evt.type,
                    value=evt.value.amount,
                    currency=evt.value.code or default_currency,
                    provider_assignment_id=provider_assignment_id,
                    notes=evt.notes,
                )
                for evt in incoming[len(stored) :]
            ]
        )
        surplus_ids = [row.id for row in stored[len(incoming) :]]
        if surplus_ids:
            # Re-point the links before deleting (ON DELETE RESTRICT). A bulk UPDATE
            # skips Transaction's before_update listener, hence the explicit updated_at.
            await session.execute(update(Transaction).where(Transaction.asset_event_id.in_(surplus_ids)).values(asset_event_id=stored[0].id, updated_at=now))
            await session.execute(delete(AssetEvent).where(AssetEvent.id.in_(surplus_ids)))

    @staticmethod
    async def bulk_upsert_events(data: list, session: AsyncSession) -> dict:
        """
        Bulk upsert manual events (provider_assignment_id = NULL).

        Per item, events carrying an ``id`` edit that manual row in place, every field
        included (date and type too: the row keeps its id, so a linked transaction
        stays linked). The whole item is validated before anything is written (see
        ``_apply_manual_event_edits``). Events without ``id`` go through
        ``_upsert_asset_events`` with provider_assignment_id=None: matched on
        (date, type) and updated in place. Each item is committed on its own.

        **R3-3 Policy D — hard-400 on currency mismatch**: every event must
        carry the same currency as its parent asset. Mixing currencies in
        ``asset_events`` would create the same kind of silent inconsistency
        already rejected for ``price_history`` (see ``bulk_upsert_prices``).
        If any event in ``data`` has ``value.code`` set to a code different
        from ``asset.currency`` we raise a 400 via ``AssetSourceError`` with
        the symmetric ``EVENT_CURRENCY_MISMATCH`` code; the caller
        (endpoint handler) re-raises it as ``HTTPException`` 400.

        Args:
            data: List of FAEventUpsert objects (asset_id + events[])
            session: Database session

        Returns:
            dict with results list and success_count

        Raises:
            AssetSourceError(code="EVENT_CURRENCY_MISMATCH"): when any
                submitted event has an explicit currency code that does not
                match the asset's currency.
            AssetSourceError(code="EVENT_NOT_EDITABLE"): an ``id`` that is
                unknown, belongs to another asset, or names a provider event.
            AssetSourceError(code="EVENT_KEY_CONFLICT"): an edit would move onto
                a (date, type) another manual event keeps, or an event without id
                would take the key an edit ends on (see ``_reject_event_key_conflicts``).
        """
        results = []
        total_count = 0

        for item in data:
            asset_id = item.asset_id

            # Verify asset exists
            asset_stmt = select(Asset).where(Asset.id == asset_id)
            asset_res = await session.execute(asset_stmt)
            asset = asset_res.scalar_one_or_none()
            if not asset:
                results.append(
                    {
                        "asset_id": asset_id,
                        "count": 0,
                        "message": f"Asset {asset_id} not found",
                    }
                )
                continue

            # Determine default currency from asset or 'USD'
            default_currency = asset.currency or "USD"

            # R3-3 Policy D: reject any event whose explicit currency does
            # not match the asset's currency. ``None`` / empty codes are
            # accepted (they'll inherit ``default_currency`` downstream).
            mismatches: list[tuple[int, str]] = []  # (event_index, code)
            for idx, raw_evt in enumerate(item.events or []):
                code = None
                value_obj = getattr(raw_evt, "value", None) if not isinstance(raw_evt, dict) else raw_evt.get("value")
                if isinstance(value_obj, dict):
                    code = value_obj.get("code")
                elif value_obj is not None:
                    code = getattr(value_obj, "code", None)
                if code and code != asset.currency:
                    mismatches.append((idx, code))

            if mismatches:
                mismatch_detail = ", ".join(f"#{i}={c}" for i, c in mismatches[:5])
                raise AssetSourceError(
                    f"EVENT_CURRENCY_MISMATCH: asset {asset_id} expects {asset.currency}, " f"got mismatched events [{mismatch_detail}]" + (f" (+{len(mismatches) - 5} more)" if len(mismatches) > 5 else ""),
                    "EVENT_CURRENCY_MISMATCH",
                )

            edits, new_events = EventStoreOperations._split_manual_events(item.events)
            await EventStoreOperations._apply_manual_event_edits(session, asset_id, edits, new_events, default_currency)
            count = len(edits) + await EventStoreOperations._upsert_asset_events(
                session=session,
                asset_id=asset_id,
                events=new_events,
                provider_assignment_id=None,  # manual events
                default_currency=default_currency,
            )
            # The edits are only flushed when the item has no event without id.
            await session.commit()

            total_count += count
            results.append(
                {
                    "asset_id": asset_id,
                    "count": count,
                    "message": f"Upserted {count} manual events",
                }
            )

        return {"results": results, "success_count": sum(1 for r in results if r["count"] > 0)}

    @staticmethod
    def _split_manual_events(events: Optional[list]) -> tuple[dict[int, FAEventUpsertPoint], list[FAEventUpsertPoint]]:
        """Split the events of one manual upsert item into edits by id and events without id."""
        points = [ev if isinstance(ev, FAEventUpsertPoint) else FAEventUpsertPoint.model_validate(ev) for ev in events or []]
        with_id = [p for p in points if p.id is not None]
        edits = {p.id: p for p in with_id}
        if len(edits) != len(with_id):
            # FAEventUpsert already answers 422; this guards callers that skip validation.
            raise AssetSourceError("EVENT_KEY_CONFLICT: the same event id appears twice in one upsert item", "EVENT_KEY_CONFLICT")
        return edits, [p for p in points if p.id is None]

    @staticmethod
    async def _apply_manual_event_edits(
        session: AsyncSession,
        asset_id: int,
        edits: dict[int, FAEventUpsertPoint],
        new_events: list[FAEventUpsertPoint],
        default_currency: str,
    ) -> None:
        """Validate the edits by id of one manual upsert item, then apply them in place.

        Every check runs before the first write, so a refused item writes nothing.
        The changes are flushed, not committed.

        Raises:
            AssetSourceError(code="EVENT_NOT_EDITABLE"): an id that is unknown,
                belongs to another asset, or names a provider event.
            AssetSourceError(code="EVENT_KEY_CONFLICT"): see ``_reject_event_key_conflicts``.
        """
        if not edits:
            return
        stmt = select(AssetEvent).where(AssetEvent.id.in_(list(edits)), AssetEvent.asset_id == asset_id, AssetEvent.provider_assignment_id.is_(None))
        rows = {row.id: row for row in (await session.execute(stmt)).scalars().all()}
        refused = sorted(set(edits) - set(rows))
        if refused:
            raise AssetSourceError(f"EVENT_NOT_EDITABLE: no manual event of asset {asset_id} has id {', '.join(str(i) for i in refused)}", "EVENT_NOT_EDITABLE")
        await EventStoreOperations._reject_event_key_conflicts(session, asset_id, edits, rows, new_events)

        now = utcnow()
        for event_id, point in edits.items():
            row = rows[event_id]
            row.date = point.date
            row.type = point.type
            row.value = point.value.amount
            row.currency = point.value.code or default_currency
            row.notes = point.notes
            # AssetEvent has no before_update listener: updated_at is set here.
            row.updated_at = now
        await session.flush()

    @staticmethod
    async def _reject_event_key_conflicts(
        session: AsyncSession,
        asset_id: int,
        edits: dict[int, FAEventUpsertPoint],
        rows: dict[int, AssetEvent],
        new_events: list[FAEventUpsertPoint],
    ) -> None:
        """Refuse an item whose edits would collide with another manual event on one (date, type).

        A *mover* is an edit whose (date, type) changes. A mover may not land on a key
        another edit of the item ends on, nor on a key held by a manual row the item
        does not edit. An event without id may not take a key an edit ends on.
        Allowed: swapping keys, edits that keep a shared key (legacy same-key
        duplicates stay editable), and an event without id on a key a mover vacates.

        Raises:
            AssetSourceError(code="EVENT_KEY_CONFLICT")
        """
        final_keys = {event_id: (point.date, str(point.type)) for event_id, point in edits.items()}
        movers = [key for event_id, key in final_keys.items() if key != (rows[event_id].date, str(rows[event_id].type))]
        ends_on = Counter(final_keys.values())
        conflicts = [key for key in movers if ends_on[key] > 1]
        if movers:
            held_stmt = select(AssetEvent.date, AssetEvent.type).where(
                AssetEvent.asset_id == asset_id,
                AssetEvent.provider_assignment_id.is_(None),
                AssetEvent.date.in_(sorted({day for day, _ in movers})),
                AssetEvent.id.not_in(list(edits)),
            )
            held = {(day, str(kind)) for day, kind in (await session.execute(held_stmt)).all()}
            conflicts += [key for key in movers if key in held]
        conflicts += [key for key in ((p.date, str(p.type)) for p in new_events) if key in ends_on]
        if conflicts:
            day, kind = conflicts[0]
            raise AssetSourceError(f"EVENT_KEY_CONFLICT: asset {asset_id} would have two manual {kind} events on {day.isoformat()}", "EVENT_KEY_CONFLICT")

    @staticmethod
    async def query_events_bulk(requests: list, session: AsyncSession) -> list:
        """
        Bulk query events for multiple assets, returning FAAssetEventPointOut with id + is_auto.

        Args:
            requests: List of FAEventQueryItem (asset_id + date_range + optional target_currency)
            session: Database session

        Returns:
            List of FAEventQueryResult

        E.8 — when ``target_currency`` is set on a request, ``event.value`` is
        converted to that currency via FX rates at the event's date. FX misses
        are surfaced as non-fatal warnings in ``FAEventQueryResult.errors``
        (the event is still returned, in its native currency).
        """
        from backend.app.schemas.assets.events import FAAssetEventPointOut, FAEventQueryResult  # noqa: PLC0415 — avoid circular import

        results = []

        for req in requests:
            asset_id = req.asset_id
            start = req.date_range.start
            end = req.date_range.end or start
            target_currency = getattr(req, "target_currency", None)

            stmt = (
                select(AssetEvent)
                .where(
                    and_(
                        AssetEvent.asset_id == asset_id,
                        AssetEvent.date >= start,
                        AssetEvent.date <= end,
                    )
                )
                .order_by(AssetEvent.date)
            )
            res = await session.execute(stmt)
            db_events = res.scalars().all()

            # Build native-currency event points first
            event_points: list = []
            for ev in db_events:
                event_points.append(
                    FAAssetEventPointOut(
                        date=ev.date,
                        type=ev.type.value if hasattr(ev.type, "value") else str(ev.type),
                        value=Currency(code=ev.currency, amount=ev.value),
                        notes=ev.notes,
                        id=ev.id,
                        is_auto=ev.provider_assignment_id is not None,
                    )
                )

            errors: list[str] = []

            # E.8 — optional target_currency conversion pass
            if target_currency and event_points:
                conversions = [(ep.value, target_currency, ep.date) for ep in event_points]
                conv_results, conv_errors = await convert_bulk(session, conversions, raise_on_error=False)

                for idx, (ep, conv) in enumerate(zip(event_points, conv_results, strict=True)):
                    if conv is None:
                        # FX miss — keep native currency value, surface as non-fatal warning.
                        # original_* stays None → frontend will hide the event marker (E.8.2).
                        errors.append(f"Missing FX rate {ep.value.code}->{target_currency} for event on {ep.date.isoformat()}")
                        continue
                    new_cur, rate_date, _bfill = conv
                    # Identity conversion (from == to) → no-op, don't populate original_*/fx_*
                    # so the FE can distinguish "converted" from "passthrough".
                    if ep.value.code == target_currency:
                        continue
                    # Compute days_back magnitude (0 for same-day, >0 for backward-fill).
                    days_back = (ep.date - rate_date).days if rate_date else 0
                    event_points[idx] = FAAssetEventPointOut(
                        date=ep.date,
                        type=ep.type,
                        value=new_cur,
                        notes=ep.notes,
                        id=ep.id,
                        is_auto=ep.is_auto,
                        original_value=ep.value,
                        fx_info=FxBackwardFillInfo(fx_rate_date=rate_date, fx_days_back=days_back),
                    )

                # Also include per-pair errors surfaced by convert_bulk (e.g. pair not registered)
                # (deduplicated against our per-event messages — convert_bulk errors are already
                # one per failed conversion, same index, so we skip duplicates by content).
                for err in conv_errors:
                    if err not in errors:
                        errors.append(err)

            results.append(
                FAEventQueryResult(
                    asset_id=asset_id,
                    events=event_points,
                    errors=errors,
                )
            )

        return results

    @staticmethod
    async def get_events_by_ids(event_ids: list[int], session: AsyncSession) -> list:
        """
        Fetch events by their primary-key IDs, grouped by asset_id.

        Returns the same FAEventQueryResult shape as query_events_bulk but
        with point selection instead of date-range filters.
        """
        if not event_ids:
            return []

        stmt = select(AssetEvent).where(AssetEvent.id.in_(event_ids)).order_by(AssetEvent.asset_id, AssetEvent.date)
        res = await session.execute(stmt)
        db_events = res.scalars().all()

        # Group by asset_id
        grouped: dict[int, list] = {}
        for ev in db_events:
            point = FAAssetEventPointOut(
                date=ev.date,
                type=ev.type.value if hasattr(ev.type, "value") else str(ev.type),
                value=Currency(code=ev.currency, amount=ev.value),
                notes=ev.notes,
                id=ev.id,
                is_auto=ev.provider_assignment_id is not None,
            )
            grouped.setdefault(ev.asset_id, []).append(point)

        return [FAEventQueryResult(asset_id=aid, events=evts, errors=[]) for aid, evts in grouped.items()]

    @staticmethod
    async def delete_events_bulk(
        event_ids: list[int],
        session: AsyncSession,
        current_user: User,
    ) -> FAEventBulkDeleteResponse:
        """
        Bulk delete asset events with RESTRICT-aware per-item result.

        For each requested id, returns one of:
        - ``deleted`` — event removed
        - ``not_found`` — id did not exist
        - ``in_use`` — referenced by one or more transactions; response exposes
          ``accessible_transactions`` (tx ids current user can see) and
          ``hidden_transactions_count`` (refs owned by other users).

        No partial rollback: deletable events are committed even if others are
        blocked. HTTP layer always returns 200 — inspect ``results`` for outcome.
        """
        results: list[FAEventDeleteItemResult] = []

        for event_id in event_ids:
            event = await session.get(AssetEvent, event_id)
            if event is None:
                results.append(FAEventDeleteItemResult(event_id=event_id, status="not_found"))
                continue

            # RESTRICT pre-check: enumerate transactions that reference this event.
            total_stmt = select(func.count(Transaction.id)).where(Transaction.asset_event_id == event_id)
            total_count_row = await session.execute(total_stmt)
            total_count = int(total_count_row.scalar_one() or 0)

            if total_count > 0:
                # Split by user accessibility via BrokerUserAccess join.
                accessible_stmt = (
                    select(Transaction.id)
                    .join(BrokerUserAccess, Transaction.broker_id == BrokerUserAccess.broker_id)
                    .where(
                        Transaction.asset_event_id == event_id,
                        BrokerUserAccess.user_id == current_user.id,
                    )
                )
                acc_rows = await session.execute(accessible_stmt)
                accessible_ids = [int(r[0]) for r in acc_rows.all()]
                hidden = total_count - len(accessible_ids)

                results.append(
                    FAEventDeleteItemResult(
                        event_id=event_id,
                        status="in_use",
                        accessible_transactions=accessible_ids,
                        hidden_transactions_count=hidden,
                    )
                )
                continue

            # Safe to delete
            await session.delete(event)
            results.append(FAEventDeleteItemResult(event_id=event_id, status="deleted"))

        await session.commit()

        return FAEventBulkDeleteResponse(
            results=results,
            deleted_count=sum(1 for r in results if r.status == "deleted"),
            not_found_count=sum(1 for r in results if r.status == "not_found"),
            in_use_count=sum(1 for r in results if r.status == "in_use"),
        )
