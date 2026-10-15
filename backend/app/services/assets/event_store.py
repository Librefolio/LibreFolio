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
from backend.app.services.fx.conversion import convert_bulk
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
        *,
        commit: bool = True,
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
        single write lock for the whole loop. ``commit=False`` leaves the transaction to
        the caller — each slice is flushed, none committed: the manual upsert, all or
        nothing.

        Args:
            session: Database session
            asset_id: Asset ID
            events: List of FAAssetEventPoint or dicts (parsed via Pydantic)
            provider_assignment_id: FK to asset_provider_assignments.id (None = manual)
            default_currency: Fallback currency
            commit: Commit each slice (the provider refresh) or leave it to the caller

        Returns:
            Number of events upserted
        """
        return len(await EventStoreOperations._write_asset_events(session, asset_id, events, provider_assignment_id, default_currency, commit=commit))

    @staticmethod
    async def _write_asset_events(
        session: AsyncSession,
        asset_id: int,
        events: list[dict | FAAssetEventPoint],
        provider_assignment_id: Optional[int],
        default_currency: str,
        *,
        commit: bool,
    ) -> list[int]:
        """``_upsert_asset_events``, answering the id of the row each event wrote, in the order of ``events``.

        The ids are read after each slice is flushed, before any commit expires the rows.
        """
        if not events:
            return []

        # Parse through Pydantic if raw dict; if already FAAssetEventPoint, use directly
        parsed = [raw if isinstance(raw, FAAssetEventPoint) else FAAssetEventPoint(**raw) for raw in events]
        groups: dict[_EventKey, list[int]] = {}
        for index, evt in enumerate(parsed):
            groups.setdefault((evt.date, str(evt.type)), []).append(index)

        ids: list[int] = [0] * len(parsed)
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
            written: list[tuple[int, AssetEvent]] = []
            for key in chunk_keys:
                indices = groups[key]
                rows = await EventStoreOperations._write_event_group(session, asset_id, provider_assignment_id, default_currency, [parsed[i] for i in indices], stored.get(key, []))
                written += zip(indices, rows, strict=True)
            await session.flush()
            for index, row in written:
                ids[index] = row.id
            if commit:
                await session.commit()

        return ids

    @staticmethod
    async def _write_event_group(
        session: AsyncSession,
        asset_id: int,
        provider_assignment_id: Optional[int],
        default_currency: str,
        incoming: list[FAAssetEventPoint],
        stored: list[AssetEvent],
    ) -> list[AssetEvent]:
        """Make the stored rows of one (date, type) key match ``incoming``, in place (see ``_upsert_asset_events``).

        Returns the row each incoming event wrote, in order: the stored rows it updated, then the rows it added.
        """
        now = utcnow()
        # AssetEvent has no before_update listener: updated_at is set here.
        for row, evt in zip(stored, incoming, strict=False):
            row.value = evt.value.amount
            row.currency = evt.value.code or default_currency
            row.notes = evt.notes
            row.updated_at = now
        added = [
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
        session.add_all(added)
        surplus_ids = [row.id for row in stored[len(incoming) :]]
        if surplus_ids:
            # Re-point the links before deleting (ON DELETE RESTRICT). A bulk UPDATE
            # skips Transaction's before_update listener, hence the explicit updated_at.
            await session.execute(update(Transaction).where(Transaction.asset_event_id.in_(surplus_ids)).values(asset_event_id=stored[0].id, updated_at=now))
            await session.execute(delete(AssetEvent).where(AssetEvent.id.in_(surplus_ids)))
        return [*stored[: len(incoming)], *added]

    @staticmethod
    async def bulk_upsert_events(data: list, session: AsyncSession) -> dict:
        """
        Bulk upsert manual events (provider_assignment_id = NULL), all or nothing.

        The items run in order in ONE transaction: each is checked, then written and
        flushed, and the request is committed at the end. A refusal rolls everything
        back, so a request is saved whole or not at all (decision 22 of release 1.3).
        Every refusal says where it is: ``AssetSourceError.details`` names the item
        (``item_index``, ``asset_id``) and, when it is about events, which ones.

        Per item, ``mode``:

        - ``"upsert"`` (default): events carrying an ``id`` edit that manual row in
          place, every field included (date and type too: the row keeps its id, so a
          linked transaction stays linked; see ``_apply_manual_event_edits``). Events
          without ``id`` go through ``_write_asset_events`` with
          provider_assignment_id=None: matched on (date, type) with the manual rows and
          updated in place — the event editor and its CSV import.
        - ``"create"``: events without ``id`` only («+ New event»). One on a (date, type)
          the asset already has, manual or from a provider, is refused with
          ``EVENT_EXISTS`` and the stored events on that key: a new event never
          overwrites (decision 20).

        **R3-3 Policy D — hard-400 on currency mismatch**: every event must carry the
        same currency as its parent asset (``EVENT_CURRENCY_MISMATCH``, symmetric to
        ``bulk_upsert_prices``). An event without a code inherits the asset currency.

        Args:
            data: List of FAEventUpsert objects (asset_id + mode + events[])
            session: Database session

        Returns:
            dict with results list (``event_ids``: the row each event wrote, in request
            order) and success_count

        Raises:
            AssetSourceError(code="EVENT_ASSET_NOT_FOUND"): an item names an asset that
                does not exist.
            AssetSourceError(code="EVENT_CURRENCY_MISMATCH"): see above.
            AssetSourceError(code="EVENT_NOT_EDITABLE"): an ``id`` that is unknown,
                belongs to another asset, or names a provider event.
            AssetSourceError(code="EVENT_KEY_CONFLICT"): an edit would move onto a
                (date, type) another manual event keeps, or an event without id would take
                the key an edit ends on (see ``_reject_event_key_conflicts``).
            AssetSourceError(code="EVENT_EXISTS"): ``create`` on a (date, type) already taken.
        """
        try:
            results = [await EventStoreOperations._write_manual_item(session, item_index, item) for item_index, item in enumerate(data)]
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        return {"results": results, "success_count": sum(1 for r in results if r["count"] > 0)}

    @staticmethod
    async def _write_manual_item(session: AsyncSession, item_index: int, item) -> dict:
        """Check one item of ``bulk_upsert_events``, then write and flush it. A refusal names the item."""
        asset_id = item.asset_id
        try:
            asset = (await session.execute(select(Asset).where(Asset.id == asset_id))).scalar_one_or_none()
            if asset is None:
                raise AssetSourceError(f"EVENT_ASSET_NOT_FOUND: asset {asset_id} does not exist", "EVENT_ASSET_NOT_FOUND")
            default_currency = asset.currency or "USD"
            EventStoreOperations._reject_currency_mismatches(asset, item.events)
            points = EventStoreOperations._as_upsert_points(item.events)
            edits, new_events = EventStoreOperations._split_manual_events(points)
            if getattr(item, "mode", "upsert") == "create":
                await EventStoreOperations._reject_existing_events(session, asset_id, new_events)
            await EventStoreOperations._apply_manual_event_edits(session, asset_id, edits, new_events, default_currency)
            new_ids = iter(await EventStoreOperations._write_asset_events(session, asset_id, new_events, None, default_currency, commit=False))
        except AssetSourceError as exc:
            exc.details = {"asset_id": asset_id, "item_index": item_index, **exc.details}
            raise
        # The row of each event, in request order: an edit keeps its id, the others take the one they wrote.
        event_ids = [point.id if point.id is not None else next(new_ids) for point in points]
        return {"asset_id": asset_id, "count": len(event_ids), "message": f"Upserted {len(event_ids)} manual events", "event_ids": event_ids}

    @staticmethod
    def _reject_currency_mismatches(asset: Asset, events: Optional[list]) -> None:
        """R3-3 Policy D: refuse an item whose events carry a currency other than the asset's, naming each one.

        ``None`` / empty codes are accepted: they inherit ``default_currency`` downstream.

        Raises:
            AssetSourceError(code="EVENT_CURRENCY_MISMATCH"): ``details`` holds the asset currency and, per
                mismatched event, its index, date, type and currency.
        """

        def field(raw: object, name: str) -> object:
            return raw.get(name) if isinstance(raw, dict) else getattr(raw, name, None)

        mismatches: list[dict] = []
        for index, raw_evt in enumerate(events or []):
            value_obj = field(raw_evt, "value")
            code = field(value_obj, "code") if value_obj is not None else None
            if code and code != asset.currency:
                mismatches.append({"event_index": index, "date": str(field(raw_evt, "date")), "type": str(field(raw_evt, "type")), "currency": code})
        if mismatches:
            mismatch_detail = ", ".join(f"#{m['event_index']}={m['currency']}" for m in mismatches[:5])
            raise AssetSourceError(
                f"EVENT_CURRENCY_MISMATCH: asset {asset.id} expects {asset.currency}, " f"got mismatched events [{mismatch_detail}]" + (f" (+{len(mismatches) - 5} more)" if len(mismatches) > 5 else ""),
                "EVENT_CURRENCY_MISMATCH",
                {"expected": asset.currency, "events": mismatches},
            )

    @staticmethod
    async def _reject_existing_events(session: AsyncSession, asset_id: int, new_events: list[FAEventUpsertPoint]) -> None:
        """A ``create`` item may not land on a (date, type) the asset already has, manual or from a provider (decision 20).

        Raises:
            AssetSourceError(code="EVENT_EXISTS"): ``details["existing"]`` lists the stored events on every such
                key, ordered by (date, type, id), each with the number of transactions linked to it.
        """
        keys = {(point.date, str(point.type)) for point in new_events}
        if not keys:
            return
        stmt = select(AssetEvent).where(AssetEvent.asset_id == asset_id, AssetEvent.date.in_(sorted({day for day, _ in keys}))).order_by(AssetEvent.date, AssetEvent.type, AssetEvent.id)
        existing = [row for row in (await session.execute(stmt)).scalars().all() if (row.date, str(row.type)) in keys]
        if not existing:
            return
        linked_stmt = select(Transaction.asset_event_id, func.count(Transaction.id)).where(Transaction.asset_event_id.in_([row.id for row in existing])).group_by(Transaction.asset_event_id)
        linked = dict((await session.execute(linked_stmt)).all())
        first = existing[0]
        raise AssetSourceError(
            f"EVENT_EXISTS: asset {asset_id} already has a {first.type} event on {first.date.isoformat()}" + (f" (+{len(existing) - 1} more)" if len(existing) > 1 else ""),
            "EVENT_EXISTS",
            {
                "existing": [
                    {
                        "id": row.id,
                        "date": row.date.isoformat(),
                        "type": str(row.type),
                        "value": Currency(code=row.currency, amount=row.value).model_dump(mode="json"),
                        "notes": row.notes,
                        "is_auto": row.provider_assignment_id is not None,
                        "linked_transactions": int(linked.get(row.id, 0)),
                    }
                    for row in existing
                ]
            },
        )

    @staticmethod
    def _as_upsert_points(events: Optional[list]) -> list[FAEventUpsertPoint]:
        """The events of one manual upsert item as ``FAEventUpsertPoint``s, in request order."""
        return [ev if isinstance(ev, FAEventUpsertPoint) else FAEventUpsertPoint.model_validate(ev) for ev in events or []]

    @staticmethod
    def _split_manual_events(events: Optional[list]) -> tuple[dict[int, FAEventUpsertPoint], list[FAEventUpsertPoint]]:
        """Split the events of one manual upsert item into edits by id and events without id."""
        points = EventStoreOperations._as_upsert_points(events)
        with_id = [p for p in points if p.id is not None]
        edits = {p.id: p for p in with_id}
        if len(edits) != len(with_id):
            # FAEventUpsert already answers 422; this guards callers that skip validation.
            repeated = sorted({p.id for p in with_id if sum(1 for q in with_id if q.id == p.id) > 1})
            raise AssetSourceError("EVENT_KEY_CONFLICT: the same event id appears twice in one upsert item", "EVENT_KEY_CONFLICT", {"ids": repeated})
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
            raise AssetSourceError(f"EVENT_NOT_EDITABLE: no manual event of asset {asset_id} has id {', '.join(str(i) for i in refused)}", "EVENT_NOT_EDITABLE", {"ids": refused})
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
            raise AssetSourceError(f"EVENT_KEY_CONFLICT: asset {asset_id} would have two manual {kind} events on {day.isoformat()}", "EVENT_KEY_CONFLICT", {"date": day.isoformat(), "type": kind})

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
        asset_id: int,
        event_ids: list[int],
        session: AsyncSession,
        current_user: User,
    ) -> FAEventBulkDeleteResponse:
        """
        Bulk delete events of one asset with RESTRICT-aware per-item result.

        Scoped by ``asset_id`` (decision 21): an id of another asset is ``not_found``
        and its event is left alone, so a wrong or crafted request cannot delete the
        events of other assets.

        For each requested id, returns one of:
        - ``deleted`` — event removed
        - ``not_found`` — id did not exist, or names an event of another asset
        - ``in_use`` — referenced by one or more transactions; response exposes
          ``accessible_transactions`` (tx ids current user can see) and
          ``hidden_transactions_count`` (refs owned by other users).

        No partial rollback: deletable events are committed even if others are
        blocked. HTTP layer always returns 200 — inspect ``results`` for outcome.
        """
        results: list[FAEventDeleteItemResult] = []

        for event_id in event_ids:
            event = await session.get(AssetEvent, event_id)
            if event is None or event.asset_id != asset_id:
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
