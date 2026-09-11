"""Asset CRUD and merge operations."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import List, Optional

import structlog
from sqlalchemy import String, and_, case, cast, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    AssetEvent,
    AssetProviderAssignment,
    AssetType,
    BrokerUserAccess,
    IdentifierType,
    PriceHistory,
    Transaction,
    UserRole,
)
from backend.app.schemas.assets import (
    FAAinfoFiltersRequest,
    FAAssetCreateItem,
    FAAssetCreateResult,
    FAAssetDeleteResult,
    FAAssetMergePreview,
    FAAssetMergeResponse,
    FAAssetPatchItem,
    FAAssetPatchResult,
    FABulkAssetCreateResponse,
    FABulkAssetDeleteResponse,
    FABulkAssetPatchResponse,
    FAClassificationParams,
    FAinfoResponse,
)
from backend.app.schemas.common import (
    OldNew,
)
from backend.app.services.asset_sources.core import AssetSourceError, AssetSourceProvider
from backend.app.utils.identifier_utils import merge_other_identifiers

logger = structlog.get_logger(__name__)


class AssetCRUDService:
    """Service for asset CRUD operations."""

    @staticmethod
    async def create_assets_bulk(assets: List[FAAssetCreateItem], session: AsyncSession) -> FABulkAssetCreateResponse:
        """
        Create multiple assets in bulk (partial success allowed).

        Args:
            assets: List of assets to create
            session: Database session

        Returns:
            FABulkAssetCreateResponse with per-item results
        """
        results: list[FAAssetCreateResult] = []

        for item in assets:
            try:
                # Check if display_name already exists (UNIQUE constraint)
                stmt = select(Asset).where(Asset.display_name == item.display_name)
                existing = await session.execute(stmt)
                if existing.scalar_one_or_none():
                    results.append(
                        FAAssetCreateResult(
                            asset_id=None,
                            success=False,
                            message=f"Asset with display_name '{item.display_name}' already exists",
                            display_name=item.display_name,
                        )
                    )
                    continue

                # Create asset record
                asset = Asset(
                    display_name=item.display_name,
                    currency=item.currency,
                    asset_type=item.asset_type or AssetType.OTHER,
                    icon_url=item.icon_url,
                    quote_base_quantity=item.quote_base_quantity,
                    active=item.active,
                    user_url=item.user_url,
                    # Identifier fields
                    identifier_isin=item.identifier_isin,
                    identifier_ticker=item.identifier_ticker,
                    identifier_cusip=item.identifier_cusip,
                    identifier_sedol=item.identifier_sedol,
                    identifier_figi=item.identifier_figi,
                    identifier_uuid=item.identifier_uuid,
                    identifier_other=item.identifier_other,
                )

                # Handle classification_params
                if item.classification_params:
                    asset.classification_params = item.classification_params.model_dump_json(exclude_none=True)

                session.add(asset)
                await session.flush()  # Get ID without committing

                results.append(
                    FAAssetCreateResult(
                        asset_id=asset.id,
                        success=True,
                        message="Asset created successfully",
                        display_name=item.display_name,
                    )
                )

                logger.info(f"Asset created: id={asset.id}, display_name={item.display_name}")

            except Exception as e:
                logger.exception(f"Error creating asset {item.display_name}: {e}")
                results.append(
                    FAAssetCreateResult(
                        asset_id=None,
                        success=False,
                        message=f"Error: {e!s}",
                        display_name=item.display_name,
                    )
                )

        # Commit all successful creates
        try:
            await session.commit()
        except Exception as e:
            logger.exception(f"Error committing asset creation: {e}")
            await session.rollback()
            # Mark all as failed
            for result in results:
                if result.success:
                    result.success = False
                    result.message = f"Transaction failed: {e!s}"
                    result.asset_id = None

        success_count = sum(1 for r in results if r.success)
        return FABulkAssetCreateResponse(results=results, success_count=success_count, errors=[])

    @staticmethod
    async def list_assets(filters: FAAinfoFiltersRequest, session: AsyncSession, user_id: int | None = None) -> List[FAinfoResponse]:  # noqa: C901 — flat filter-chain query builder
        """
        List assets with optional filters - enhanced for BRIM asset matching.

        Supports filtering by:
        - currency, asset_type, active (existing)
        - search: partial match in display_name
        - Exact match on identifier columns: isin, ticker, cusip, sedol, figi, uuid
        - identifier_other: partial match (LIKE)
        - identifier_contains: partial match across ALL identifier columns

        Args:
            filters: Query filters (see FAAinfoFiltersRequest)
            session: Database session

        Returns:
            List of assets matching filters, with identifier info
        """
        # Build base query with LEFT JOIN to get provider assignment data
        stmt = select(
            Asset,
            AssetProviderAssignment.id.label("provider_id"),
            AssetProviderAssignment.provider_code.label("provider_code_col"),
            AssetProviderAssignment.identifier.label("provider_identifier"),
            AssetProviderAssignment.identifier_type.label("provider_identifier_type"),
        ).outerjoin(AssetProviderAssignment, Asset.id == AssetProviderAssignment.asset_id)

        # Apply filters
        conditions = []

        if filters.currency:
            conditions.append(Asset.currency == filters.currency)

        if filters.asset_type:
            conditions.append(Asset.asset_type == filters.asset_type)

        # Tri-state active filter: None = no filter, True/False = exact match
        if filters.active is not None:
            conditions.append(Asset.active == filters.active)

        if filters.search:
            search_pattern = f"%{filters.search}%"
            conditions.append(Asset.display_name.ilike(search_pattern))

        # Exact match on identifier columns (one per IdentifierType)
        if filters.isin:
            conditions.append(Asset.identifier_isin == filters.isin.upper())

        if filters.ticker:
            conditions.append(Asset.identifier_ticker == filters.ticker.upper())

        if filters.cusip:
            conditions.append(Asset.identifier_cusip == filters.cusip.upper())

        if filters.sedol:
            conditions.append(Asset.identifier_sedol == filters.sedol.upper())

        if filters.figi:
            conditions.append(Asset.identifier_figi == filters.figi.upper())

        if filters.uuid:
            conditions.append(Asset.identifier_uuid == filters.uuid)

        # identifier_other is a JSON list of soft identifiers: cast the column to text
        # and substring-match, so any element of the list can match.
        # NOTE: SQLite LIKE is case-insensitive for ASCII; on Postgres switch to .ilike().
        if filters.identifier_other:
            conditions.append(cast(Asset.identifier_other, String).like(f"%{filters.identifier_other}%"))

        # Partial identifier match (across all identifier columns)
        if filters.identifier_contains:
            pattern = f"%{filters.identifier_contains}%"
            conditions.append(
                or_(
                    Asset.identifier_isin.ilike(pattern),
                    Asset.identifier_ticker.ilike(pattern),
                    Asset.identifier_cusip.ilike(pattern),
                    Asset.identifier_sedol.ilike(pattern),
                    Asset.identifier_figi.ilike(pattern),
                    Asset.identifier_uuid.ilike(pattern),
                    cast(Asset.identifier_other, String).like(pattern),
                )
            )

        if conditions:
            stmt = stmt.where(and_(*conditions))

        # Order by display_name
        stmt = stmt.order_by(Asset.display_name.asc())

        # Execute query
        result = await session.execute(stmt)
        rows = result.all()

        # F15 usage counters: per-asset transaction totals (global) and "own"
        # totals (brokers the current user OWNs with a positive share; a NULL
        # share is the legacy unset value and counts as full ownership).
        tx_total_by_asset: dict[int, int] = {}
        tx_own_by_asset: dict[int, int] = {}
        if rows:
            total_stmt = select(Transaction.asset_id, func.count()).group_by(Transaction.asset_id)
            tx_total_by_asset = {asset_id: count for asset_id, count in (await session.execute(total_stmt)).all() if asset_id is not None}
        if rows and user_id is not None:
            own_brokers_sq = (
                select(BrokerUserAccess.broker_id)
                .where(
                    BrokerUserAccess.user_id == user_id,
                    BrokerUserAccess.role == UserRole.OWNER,
                    or_(BrokerUserAccess.share_percentage.is_(None), BrokerUserAccess.share_percentage > 0),
                )
                .scalar_subquery()
            )
            own_stmt = select(Transaction.asset_id, func.count()).where(Transaction.broker_id.in_(own_brokers_sq)).group_by(Transaction.asset_id)
            tx_own_by_asset = {asset_id: count for asset_id, count in (await session.execute(own_stmt)).all() if asset_id is not None}

        # Build response with identifier info
        assets = []
        for row in rows:
            asset = row[0]  # Asset object
            _provider_id = row[1]  # provider_id from join (unused, kept for positional access)
            provider_code = row[2]  # provider_code from join
            provider_identifier = row[3]  # identifier from provider assignment
            provider_identifier_type = row[4]  # identifier_type from provider assignment

            assets.append(
                FAinfoResponse(
                    id=asset.id,
                    display_name=asset.display_name,
                    currency=asset.currency,
                    icon_url=asset.icon_url,
                    asset_type=asset.asset_type,
                    quote_base_quantity=asset.quote_base_quantity,
                    active=asset.active,
                    user_url=asset.user_url,
                    provider_code=provider_code,
                    has_metadata=asset.classification_params is not None,
                    tx_count=tx_total_by_asset.get(asset.id, 0),
                    tx_count_own=tx_own_by_asset.get(asset.id, 0),
                    # Identifier columns from Asset
                    identifier_isin=asset.identifier_isin,
                    identifier_ticker=asset.identifier_ticker,
                    identifier_cusip=asset.identifier_cusip,
                    identifier_sedol=asset.identifier_sedol,
                    identifier_figi=asset.identifier_figi,
                    identifier_uuid=asset.identifier_uuid,
                    identifier_other=asset.identifier_other,
                    # Legacy fields from provider assignment
                    identifier=provider_identifier,
                    identifier_type=(AssetSourceProvider.map_input_type_to_identifier_type(provider_identifier_type) if provider_identifier_type else None),
                )
            )

        return assets

    @staticmethod
    async def delete_assets_bulk(asset_ids: List[int], session: AsyncSession) -> FABulkAssetDeleteResponse:
        """
        Delete multiple assets (partial success allowed).

        Blocks deletion if asset has transactions (FK constraint).
        CASCADE deletes provider_assignments and price_history.

        Args:
            asset_ids: List of asset IDs to delete
            session: Database session

        Returns:
            FABulkAssetDeleteResponse with per-item results
        """
        unique_ids = list(dict.fromkeys(asset_ids))
        asset_rows = await session.execute(select(Asset).where(Asset.id.in_(unique_ids)))
        assets_by_id = {asset.id: asset for asset in asset_rows.scalars().all()}
        count_rows = await session.execute(select(Transaction.asset_id, func.count(Transaction.id)).where(Transaction.asset_id.in_(unique_ids)).group_by(Transaction.asset_id))
        transaction_counts = dict(count_rows.all())

        # SQLite defers BEGIN across reads; without a write, releasing the first
        # SAVEPOINT commits it and a later outer rollback cannot undo the delete.
        await session.execute(update(Asset).where(Asset.id.in_([])).values(active=Asset.active))

        results: list[FAAssetDeleteResult] = []
        prior_results: dict[int, FAAssetDeleteResult] = {}
        for asset_id in asset_ids:
            prior = prior_results.get(asset_id)
            if prior is not None and not prior.success:
                results.append(prior.model_copy(deep=True))
                continue
            asset = assets_by_id.get(asset_id) if prior is None else None
            if asset is None:
                item_result = FAAssetDeleteResult(
                    asset_id=asset_id,
                    success=False,
                    deleted_count=0,
                    display_name=None,
                    error_code="NOT_FOUND",
                    message=f"Asset with ID {asset_id} not found",
                )
                results.append(item_result)
                prior_results[asset_id] = item_result
                continue

            asset_name = asset.display_name
            transaction_count = transaction_counts.get(asset_id, 0)
            if transaction_count:
                item_result = FAAssetDeleteResult(
                    asset_id=asset_id,
                    success=False,
                    deleted_count=0,
                    display_name=asset_name,
                    error_code="HAS_TRANSACTIONS",
                    transaction_count=transaction_count,
                    message=f"Cannot delete asset {asset_id}: has {transaction_count} existing transactions",
                )
                results.append(item_result)
                prior_results[asset_id] = item_result
                continue

            try:
                async with session.begin_nested():
                    await session.delete(asset)
                    await session.flush()

                item_result = FAAssetDeleteResult(
                    asset_id=asset_id,
                    success=True,
                    deleted_count=1,
                    display_name=asset_name,
                    message="Asset deleted successfully",
                )
                results.append(item_result)
                prior_results[asset_id] = item_result

                logger.info(f"Asset deleted: id={asset_id}")

            except IntegrityError as e:
                race_count = await session.scalar(select(func.count(Transaction.id)).where(Transaction.asset_id == asset_id))
                transaction_count = int(race_count or 0)
                blocked = transaction_count > 0
                item_result = FAAssetDeleteResult(
                    asset_id=asset_id,
                    success=False,
                    deleted_count=0,
                    display_name=asset_name,
                    error_code="HAS_TRANSACTIONS" if blocked else None,
                    transaction_count=transaction_count or None,
                    message=(f"Cannot delete asset {asset_id}: has {transaction_count} existing transactions" if blocked else f"Error deleting asset {asset_id}: {e}"),
                )
                results.append(item_result)
                prior_results[asset_id] = item_result
                logger.warning("Asset deletion blocked by integrity constraint", asset_id=asset_id, error=str(e))
            except Exception as e:
                item_result = FAAssetDeleteResult(
                    asset_id=asset_id,
                    success=False,
                    deleted_count=0,
                    display_name=asset_name,
                    message=f"Error deleting asset {asset_id}: {e}",
                )
                results.append(item_result)
                prior_results[asset_id] = item_result
                logger.exception(f"Error deleting asset {asset_id}: {e}")

        try:
            await session.commit()
        except Exception as e:
            logger.exception(f"Error committing asset deletion: {e}")
            await session.rollback()
            raise

        success_count = sum(1 for r in results if r.success)
        return FABulkAssetDeleteResponse(
            results=results,
            success_count=success_count,
            errors=[],  # Operation-level errors (none for now)
        )

    @staticmethod
    async def patch_assets_bulk(patches: List[FAAssetPatchItem], session: AsyncSession) -> FABulkAssetPatchResponse:  # noqa: C901 — per-field patch mapping, classification shallow-merge branch
        """
        Patch multiple assets in bulk (partial success allowed).

        Merge logic:
        - Field absent in patch or None: IGNORE (keep existing value)
        - Field present in patch: UPDATE or BLANK (to delete a string set to empty)

        For classification_params:
        - If None: Set DB column to NULL
        - If present: model_dump_json(exclude_none=True) to omit blank subfields

        Args:
            patches: List of asset patches
            session: Database session

        Returns:
            FABulkAssetPatchResponse with per-item results
        """

        results: list[FAAssetPatchResult] = []

        # P0-5 (audit 08): no N+1. Preload every patched asset in ONE query and
        # compute the currency-change guard data with per-asset aggregates.
        # Before: 1 SELECT per patch + up to 6 per currency-changing patch.
        # After: 1 SELECT + 3 constant aggregate queries.
        patch_ids = [patch.asset_id for patch in patches]
        asset_rows = (await session.execute(select(Asset).where(Asset.id.in_(patch_ids)))).scalars().all() if patch_ids else []
        assets_by_id = {asset.id: asset for asset in asset_rows}

        # Prepare each patch's payload once (pure CPU — same semantics as the
        # old in-loop computation, including the explicit-None clearing rule for
        # classification_params).
        prepared: list[tuple[FAAssetPatchItem, dict]] = []
        for patch in patches:
            patch_dict = patch.model_dump(mode="json", exclude={"asset_id"}, exclude_unset=True, exclude_none=True)
            # Preserve explicit clears inside the atomic classification blocks too.
            # exclude_none above would turn {"sector_area": None} into {}, clearing all.
            if "classification_params" in patch.model_fields_set:
                patch_dict["classification_params"] = patch.classification_params.model_dump(mode="json", exclude_unset=True) if patch.classification_params is not None else None
            prepared.append((patch, patch_dict))

        # Currency-change guard data (Policy D below), batched per asset.
        currency_change_ids = [patch.asset_id for patch, patch_dict in prepared if patch_dict.get("currency") and patch.asset_id in assets_by_id and patch_dict["currency"] != assets_by_id[patch.asset_id].currency]
        price_agg: dict[int, tuple[int, object, object]] = {}
        event_manual_agg: dict[int, int] = {}
        event_provider_agg: dict[int, int] = {}
        linked_tx_agg: dict[int, int] = {}
        if currency_change_ids:
            price_rows = (await session.execute(select(PriceHistory.asset_id, func.count(), func.min(PriceHistory.date), func.max(PriceHistory.date)).where(PriceHistory.asset_id.in_(currency_change_ids)).group_by(PriceHistory.asset_id))).all()
            price_agg = {row[0]: (int(row[1]), row[2], row[3]) for row in price_rows}

            event_rows = (
                await session.execute(
                    select(
                        AssetEvent.asset_id,
                        func.sum(case((AssetEvent.provider_assignment_id.is_(None), 1), else_=0)),
                        func.sum(case((AssetEvent.provider_assignment_id.is_not(None), 1), else_=0)),
                    )
                    .where(AssetEvent.asset_id.in_(currency_change_ids))
                    .group_by(AssetEvent.asset_id)
                )
            ).all()
            event_manual_agg = {row[0]: int(row[1] or 0) for row in event_rows}
            event_provider_agg = {row[0]: int(row[2] or 0) for row in event_rows}

            linked_rows = (await session.execute(select(AssetEvent.asset_id, func.count(Transaction.id)).join(Transaction, Transaction.asset_event_id == AssetEvent.id).where(AssetEvent.asset_id.in_(currency_change_ids)).group_by(AssetEvent.asset_id))).all()
            linked_tx_agg = {row[0]: int(row[1]) for row in linked_rows}

        for patch, patch_dict in prepared:
            try:
                # P0-5: the asset comes from the bulk preload above (identity map
                # keeps sequential patches on the same id consistent).
                asset = assets_by_id.get(patch.asset_id)

                if not asset:
                    results.append(
                        FAAssetPatchResult(
                            asset_id=patch.asset_id,
                            success=False,
                            message=f"Asset {patch.asset_id} not found",
                            updated_fields=None,
                        )
                    )
                    continue
                asset_classification_params_before = json.loads(asset.classification_params) if asset.classification_params else {}
                logger.debug(f"Asset found for patching: id={patch.asset_id}: {asset.model_dump_json()}")

                # Track updated fields
                updated_fields: List[OldNew[str]] = []

                # I.3 + R3-3 Policy D — guard against currency change on assets with
                # any residual market data (prices, events, or transactions still
                # linked to those events).
                #
                # Rationale: changing ``asset.currency`` while rows exist in any of
                # ``price_history`` / ``asset_events`` / ``transactions.asset_event_id``
                # creates a silent inconsistency — old-currency values would be
                # scaled against a new base via FX conversion producing wrong
                # numbers or semantically-mismatched displays. The agreed policy
                # is "wipe totally symmetric + disconnect linked transactions"
                # (see phase-07 closure plan, §"Issue #R3-3 Policy D"):
                # the frontend must POST to ``/assets/{id}/market-data/wipe``
                # first, then re-PATCH, then re-sync.
                #
                # Here we emit a structured failure so the frontend can parse it
                # and open the destructive-confirmation modal. Token format:
                #   CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA|
                #     prices=N|events_manual=M|events_provider=K|linked_tx=L|
                #     oldest=YYYY-MM-DD|newest=YYYY-MM-DD|from=X|to=Y
                # ``oldest``/``newest`` reflect the price range; they are empty
                # strings when only events exist. Parser must tolerate missing
                # fields.
                if "currency" in patch_dict:
                    new_currency = patch_dict["currency"]
                    if new_currency and new_currency != asset.currency:
                        # P0-5: all four counts + the price date range come from
                        # the batched aggregates computed before the loop.
                        price_count, oldest_date, newest_date = price_agg.get(patch.asset_id, (0, None, None))
                        event_manual_count = event_manual_agg.get(patch.asset_id, 0)
                        event_provider_count = event_provider_agg.get(patch.asset_id, 0)
                        linked_tx_count = linked_tx_agg.get(patch.asset_id, 0)

                        if price_count > 0 or event_manual_count > 0 or event_provider_count > 0:
                            blocker_msg = (
                                "CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA"
                                f"|prices={price_count}"
                                f"|events_manual={event_manual_count}"
                                f"|events_provider={event_provider_count}"
                                f"|linked_tx={linked_tx_count}"
                                f"|oldest={oldest_date.isoformat() if oldest_date else ''}"
                                f"|newest={newest_date.isoformat() if newest_date else ''}"
                                f"|from={asset.currency}"
                                f"|to={new_currency}"
                            )
                            results.append(
                                FAAssetPatchResult(
                                    asset_id=patch.asset_id,
                                    success=False,
                                    message=blocker_msg,
                                    updated_fields=None,
                                )
                            )
                            continue

                for field, value in patch_dict.items():
                    logger.debug(f"Patching field '{field}': '{value}'")
                    if field == "classification_params":
                        # None = clear all classification_params
                        if value is None:
                            value = None  # Will set classification_params to NULL in DB
                        elif not value:  # Empty dict = also clear
                            value = None
                        else:
                            # PATCH semantics for classification_params:
                            # - If a field (e.g., sector_area, geographic_area) is present in patch, replace it completely
                            # - If a field is absent from patch, keep the existing value
                            # NO deep merge: each field is atomic (sector_area.distribution is replaced as a whole)

                            # Start with existing values
                            merged = dict(asset_classification_params_before)

                            # Replace only the fields present in the patch (shallow merge, not deep)
                            for key, val in value.items():
                                if val is not None and val != "":
                                    merged[key] = val
                                else:
                                    # Explicit null/empty = remove field
                                    merged.pop(key, None)

                            # Validate and serialize
                            value = FAClassificationParams(**merged).model_dump(mode="json", exclude_none=True)
                            if not value:  # If result is empty dict, set to None
                                value = None

                    # Convert empty strings/dicts to None, but preserve boolean False
                    if not isinstance(value, bool) and not value:
                        value = None

                    if isinstance(value, dict):
                        value = json.dumps(value)  # Transform dict as serialized JSON
                    oldVal = getattr(asset, field)
                    setattr(asset, field, value)
                    updated_fields.append(OldNew(info=field, old=str(oldVal) if oldVal is not None else None, new=str(value) if value is not None else None))
                    logger.debug(f"updated field '{field}': '{oldVal}' -> '{value}'")

                await session.flush()

                results.append(
                    FAAssetPatchResult(
                        asset_id=patch.asset_id,
                        success=True,
                        message=f"Asset patched successfully ({len(updated_fields)} fields)",
                        updated_fields=updated_fields,
                    )
                )

                logger.info(f"Asset patched: id={patch.asset_id}, fields={updated_fields}")

            except Exception as e:
                logger.exception(f"Error patching asset {patch.asset_id}: {e}")
                results.append(
                    FAAssetPatchResult(
                        asset_id=patch.asset_id,
                        success=False,
                        message=f"Error: {e!s}",
                        updated_fields=None,
                    )
                )

        # Commit all successful patches
        await session.commit()

        success_count = sum(1 for r in results if r.success)

        return FABulkAssetPatchResponse(results=results, success_count=success_count, errors=[])

    @staticmethod
    async def merge_assets(  # noqa: C901 — sequential 5-stage merge, per-stage collision branches
        source_asset_id: int,
        target_asset_id: int,
        session: AsyncSession,
        identifier_primaries: Optional[dict[str, str]] = None,
        dry_run: bool = False,
    ) -> FAAssetMergeResponse:
        """Fold ``source_asset_id`` into ``target_asset_id``, then delete the source.

        Answers the duplicate-asset debt left behind whenever the same instrument was
        booked twice (typically an Italian BTP whose "CUM" placement ISIN and market
        ISIN were treated as two instruments). The target is *always* the asset the
        user wants to keep — this method never picks for them.

        Exactly four tables reference ``assets.id``; each gets an explicit policy:

        - ``Transaction.asset_id`` — reassigned (nullable FK, no unique constraint).
        - ``PriceHistory.asset_id`` — reassigned; on a ``(asset_id, date)`` collision
          the **target row wins** and the source row is discarded, because the target
          is the asset whose provider assignment will keep feeding it.
        - ``AssetEvent.asset_id`` — reassigned, de-duplicated on
          ``(date, type, value, currency)``. Transactions pointing at a discarded event
          are remapped onto the surviving one *before* the delete, since
          ``Transaction.asset_event_id`` is ``ondelete=RESTRICT``.
        - ``AssetProviderAssignment.asset_id`` — moved when the target has none,
          otherwise dropped. **Careful**: ``AssetEvent.provider_assignment_id`` is
          ``ondelete=CASCADE``, so events surviving on the target are re-pointed at the
          target's assignment before the source one is deleted — otherwise the merge
          would silently destroy the events it had just migrated.

        Identifiers are never lost: whatever does not stay primary is demoted into the
        target's ``identifier_other``.

        Args:
            source_asset_id: Asset to fold in and delete.
            target_asset_id: Asset to keep.
            session: Database session.
            identifier_primaries: Optional ``{"identifier_isin": "IT…"}`` decisions.
                A value must belong to one of the two assets (as primary or soft),
                otherwise the merge is refused.
            dry_run: Compute the plan and roll back without writing.

        Returns:
            FAAssetMergeResponse with the preview of what moved (or would move).

        Raises:
            AssetSourceError: NOT_FOUND, SAME_ASSET or INVALID_PRIMARY.
        """
        if source_asset_id == target_asset_id:
            raise AssetSourceError(
                "Source and target asset must be different",
                "SAME_ASSET",
                {"asset_id": source_asset_id},
            )

        source = (await session.execute(select(Asset).where(Asset.id == source_asset_id))).scalar_one_or_none()
        target = (await session.execute(select(Asset).where(Asset.id == target_asset_id))).scalar_one_or_none()
        if source is None:
            raise AssetSourceError(f"Asset with ID {source_asset_id} not found", "NOT_FOUND", {"asset_id": source_asset_id})
        if target is None:
            raise AssetSourceError(f"Asset with ID {target_asset_id} not found", "NOT_FOUND", {"asset_id": target_asset_id})

        preview = FAAssetMergePreview()
        # IdentifierType.OTHER maps onto ``identifier_other``, which is the JSON *list*
        # of soft identifiers, not a structured single-value column — it is the merge
        # destination, never a candidate primary.
        identifier_columns = [f"identifier_{t.value.lower()}" for t in IdentifierType if t != IdentifierType.OTHER]

        try:
            # ---------- identifiers: decide primaries, demote everything else ----------
            demoted: list[str] = []
            for column in identifier_columns:
                source_value = (getattr(source, column, None) or "").strip()
                target_value = (getattr(target, column, None) or "").strip()
                chosen = (identifier_primaries or {}).get(column)
                if chosen is not None:
                    chosen = chosen.strip()
                    known = {v.casefold() for v in (source_value, target_value) if v}
                    if chosen and chosen.casefold() not in known:
                        raise AssetSourceError(
                            f"'{chosen}' is not a {column} of asset {source_asset_id} or {target_asset_id}",
                            "INVALID_PRIMARY",
                            {"field": column, "value": chosen},
                        )
                else:
                    # Default: the target keeps its own value; the source's fills a gap.
                    chosen = target_value or source_value

                for value in (source_value, target_value):
                    if value and value.casefold() != (chosen or "").casefold():
                        demoted.append(value)
                setattr(target, column, chosen or None)

            merged_other = merge_other_identifiers(
                target.identifier_other,
                [*(source.identifier_other or []), *demoted],
            )
            before = {v.casefold() for v in (target.identifier_other or [])}
            # A demoted primary must not shadow the value that is now primary on the target.
            primaries_now = {(getattr(target, c, None) or "").casefold() for c in identifier_columns}
            merged_other = [v for v in (merged_other or []) if v.casefold() not in primaries_now] or None
            preview.identifiers_added = [v for v in (merged_other or []) if v.casefold() not in before]
            target.identifier_other = merged_other

            # ---------- price history: target wins on same date ----------
            target_dates = set((await session.execute(select(PriceHistory.date).where(PriceHistory.asset_id == target_asset_id))).scalars().all())
            source_prices = (await session.execute(select(PriceHistory).where(PriceHistory.asset_id == source_asset_id))).scalars().all()
            for row in source_prices:
                if row.date in target_dates:
                    await session.delete(row)
                    preview.prices_discarded += 1
                else:
                    row.asset_id = target_asset_id
                    target_dates.add(row.date)
                    preview.prices += 1

            # ---------- asset events: dedup, then remap the transactions ----------
            target_events = (await session.execute(select(AssetEvent).where(AssetEvent.asset_id == target_asset_id))).scalars().all()
            source_events = (await session.execute(select(AssetEvent).where(AssetEvent.asset_id == source_asset_id))).scalars().all()

            def _event_key(ev: AssetEvent) -> tuple:
                return (ev.date, str(ev.type), Decimal(str(ev.value)), (ev.currency or "").upper())

            surviving: dict[tuple, int] = {_event_key(ev): ev.id for ev in target_events if ev.id is not None}
            kept_source_events: list[AssetEvent] = []
            for ev in source_events:
                key = _event_key(ev)
                twin_id = surviving.get(key)
                if twin_id is not None:
                    relinked = await session.execute(update(Transaction).where(Transaction.asset_event_id == ev.id).values(asset_event_id=twin_id))
                    preview.transactions_relinked += relinked.rowcount or 0
                    await session.delete(ev)
                    preview.events_discarded += 1
                else:
                    ev.asset_id = target_asset_id
                    if ev.id is not None:
                        surviving[key] = ev.id
                    kept_source_events.append(ev)
                    preview.events += 1

            # ---------- provider assignment ----------
            target_assignment = (await session.execute(select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == target_asset_id))).scalar_one_or_none()
            source_assignment = (await session.execute(select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == source_asset_id))).scalar_one_or_none()
            if source_assignment is not None:
                if target_assignment is None:
                    source_assignment.asset_id = target_asset_id
                    preview.provider_assignment_moved = True
                else:
                    # CASCADE would wipe the events we just migrated → re-point them first.
                    for ev in kept_source_events:
                        if ev.provider_assignment_id == source_assignment.id:
                            ev.provider_assignment_id = target_assignment.id
                    await session.flush()
                    await session.delete(source_assignment)
                    preview.provider_assignment_dropped = True

            # ---------- transactions ----------
            moved = await session.execute(update(Transaction).where(Transaction.asset_id == source_asset_id).values(asset_id=target_asset_id))
            preview.transactions = moved.rowcount or 0

            await session.flush()
            await session.delete(source)
            await session.flush()

            if dry_run:
                await session.rollback()
                return FAAssetMergeResponse(
                    success=True,
                    source_asset_id=source_asset_id,
                    target_asset_id=target_asset_id,
                    dry_run=True,
                    preview=preview,
                    message="Dry run: nothing was written",
                )

            await session.commit()
        except AssetSourceError:
            await session.rollback()
            raise
        except Exception as e:
            await session.rollback()
            logger.exception(f"Error merging asset {source_asset_id} into {target_asset_id}: {e}")
            raise AssetSourceError(f"Merge failed: {e!s}", "MERGE_FAILED", {"source_asset_id": source_asset_id, "target_asset_id": target_asset_id}) from e

        logger.info(
            "assets merged: %d → %d (tx=%d, prices=%d/-%d, events=%d/-%d, relinked=%d)",
            source_asset_id,
            target_asset_id,
            preview.transactions,
            preview.prices,
            preview.prices_discarded,
            preview.events,
            preview.events_discarded,
            preview.transactions_relinked,
        )
        return FAAssetMergeResponse(
            success=True,
            source_asset_id=source_asset_id,
            target_asset_id=target_asset_id,
            dry_run=False,
            preview=preview,
            message=f"Asset {source_asset_id} merged into {target_asset_id}",
        )
