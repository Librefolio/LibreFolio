"""Asset CRUD and merge operations."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import List, Optional

import structlog
from sqlalchemy import String, and_, cast, func, or_, select, update
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
from backend.app.schemas.assets.assets import (
    FAAinfoFiltersRequest,
    FAAssetCreateItem,
    FAAssetCreateResult,
    FAAssetDeleteResult,
    FAAssetMergePreview,
    FAAssetMergeResponse,
    FAAssetPatchCode,
    FAAssetPatchIssue,
    FAAssetPatchItem,
    FAAssetPatchResult,
    FABulkAssetCreateResponse,
    FABulkAssetDeleteResponse,
    FABulkAssetPatchResponse,
    FAinfoResponse,
)
from backend.app.schemas.assets.metadata import FAClassificationParams
from backend.app.schemas.common import (
    OldNew,
)
from backend.app.services.assets.base import AssetSourceError, AssetSourceProvider
from backend.app.services.assets.type_rules import TypeChangeVerdict, classify_type_change
from backend.app.services.financial_math.ledger_totals import position_quantities
from backend.app.services.platform.data_quality_thresholds import QUANTITY_DUST_THRESHOLD
from backend.app.utils.asset.identifier import merge_other_identifiers

logger = structlog.get_logger(__name__)

#: The patch fields an explicit ``null`` clears: the nullable columns the edit modal can empty (the icon, the user's URL,
#: one identifier). An explicit ``null`` on any other field changes nothing: the name, the currency and the type cannot be
#: empty, the flags and the quote base keep their value, and ``identifier_other`` reads ``null`` as "leave unchanged" (an
#: explicit empty list clears it: the patch schema keeps ``[]``, and the loop below stores it as NULL).
#: ``classification_params`` has its own rule, below.
CLEARED_BY_NULL: frozenset[str] = frozenset(
    {
        "icon_url",
        "user_url",
        "identifier_isin",
        "identifier_ticker",
        "identifier_cusip",
        "identifier_sedol",
        "identifier_figi",
        "identifier_uuid",
    }
)


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
                    is_benchmark=item.is_benchmark,
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

        # Tri-state benchmark filter: None = no filter, True/False = exact match
        if filters.is_benchmark is not None:
            conditions.append(Asset.is_benchmark == filters.is_benchmark)

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

        # Open positions now: the signed quantities summed per broker and asset, the same reading
        # as the broker balances, through the portfolio's dust threshold, so a position closed but
        # for a redemption residue is not "held".
        held_own: set[int] = set()
        held_others: set[int] = set()
        if rows:
            own_broker_ids: set[int] = set()
            if user_id is not None:
                own_brokers_stmt = select(BrokerUserAccess.broker_id).where(
                    BrokerUserAccess.user_id == user_id,
                    BrokerUserAccess.role == UserRole.OWNER,
                    or_(BrokerUserAccess.share_percentage.is_(None), BrokerUserAccess.share_percentage > 0),
                )
                own_broker_ids = set((await session.execute(own_brokers_stmt)).scalars().all())
            # Summed by the layer, exactly (C-97), never with an SQL SUM of the stored doubles.
            holdings_stmt = select(Transaction.broker_id, Transaction.asset_id, Transaction.quantity).where(Transaction.asset_id.is_not(None))
            for broker_id, quantities in position_quantities((await session.execute(holdings_stmt)).all()).items():
                for asset_id, quantity in quantities.items():
                    if quantity > QUANTITY_DUST_THRESHOLD:
                        (held_own if broker_id in own_broker_ids else held_others).add(asset_id)

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
                    is_benchmark=asset.is_benchmark,
                    user_url=asset.user_url,
                    provider_code=provider_code,
                    has_metadata=asset.classification_params is not None,
                    tx_count=tx_total_by_asset.get(asset.id, 0),
                    tx_count_own=tx_own_by_asset.get(asset.id, 0),
                    held_by_me=asset.id in held_own,
                    held_by_others=asset.id in held_others,
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
    async def patch_assets_bulk(patches: List[FAAssetPatchItem], session: AsyncSession, commit: bool = True) -> FABulkAssetPatchResponse:
        """
        Patch multiple assets in bulk: all or nothing.

        1. **Check** every item before anything is written (``_check_patch_items``): a missing asset and an asset with
           transactions that would become an INDEX are issues; a change of type family is a warning, which never blocks.
        2. **Any issue**: rollback, nothing saved, ``committed=False``, and every ``results[i].success`` is False.
        3. **Apply** every item (``_apply_patch_item``, then a flush), and the currency change's wipe (N68). An exception
           here becomes the issue ``patchFailed``, with rollback.
        4. **Commit** once, then drop the provider caches of the assets whose currency changed. With ``commit=False``
           (the dry run of ``POST /assets/validate``) the batch is rolled back instead, the caches stay, and the results
           say what would have been saved.

        Merge logic of one item:
        - Field absent in patch: IGNORE (keep existing value)
        - Field present with a value: UPDATE; an empty string clears it
        - Field present as None: CLEAR for the fields of ``CLEARED_BY_NULL`` (the edit modal sends ``icon_url: null``
          to remove an icon), IGNORE for the others
        - ``identifier_other``: a list replaces the whole list, an empty one clears it (stored as NULL); None = IGNORE

        For classification_params:
        - If None or empty: Set DB column to NULL
        - If present: shallow merge of the blocks sent (``exclude_unset``), an explicit null block removes that block

        Args:
            patches: List of asset patches, each with its own fields
            session: Database session
            commit: True saves the batch; False checks and applies it, then always rolls back (dry run)

        Returns:
            FABulkAssetPatchResponse with ``committed``, ``issues``, ``warnings`` and per-item results
        """
        # P0-5 (audit 08): no N+1. Preload every patched asset in ONE query.
        patch_ids = [patch.asset_id for patch in patches]
        asset_rows = (await session.execute(select(Asset).where(Asset.id.in_(patch_ids)))).scalars().all() if patch_ids else []
        assets_by_id = {asset.id: asset for asset in asset_rows}
        prepared = AssetCRUDService._prepare_patch_payloads(patches)

        # 1. Check, before any setattr.
        issues, warnings = await AssetCRUDService._check_patch_items(prepared, assets_by_id, session)
        if issues:
            await session.rollback()
            logger.info("Asset patch batch refused, nothing saved", issues=[(issue.asset_id, issue.code.value) for issue in issues])
            return AssetCRUDService._unsaved_response(patches, issues, warnings)

        # N68 (developer decision of 19/10/2026): a currency change is never blocked. The prices and the events that are
        # not SPLITs carry the old currency, so they go with it, in the same transaction as the change; the SPLIT events
        # and the transactions linked to them stay. The interface shows the counts first
        # (``GET /assets/{id}/market-data/summary``) and asks.
        # Imported here, not at the top: ``currency_change`` imports ``core``, whose theine cache starts a thread at import, and this
        # module is in the import chain of the BRIM parse pool's forkserver preload, which must stay single-threaded.
        from backend.app.services.assets.currency_change import delete_market_data_of_assets, drop_provider_caches, provider_cache_keys  # noqa: PLC0415 — keeps the forkserver preload single-threaded

        # The currency each asset had before applying: the assets whose currency differs after it lose their prices and
        # non-SPLIT events (N68), whatever the later fields of the item did.
        currency_before = {asset_id: asset.currency for asset_id, asset in assets_by_id.items()}

        # 2. Apply. Results are built from plain values: a rollback expires the rows.
        results: list[FAAssetPatchResult] = []
        failing = (0, patches[0].asset_id) if patches else (0, 0)
        try:
            for index, (patch, patch_dict) in enumerate(prepared):
                failing = (index, patch.asset_id)
                updated_fields = AssetCRUDService._apply_patch_item(assets_by_id[patch.asset_id], patch_dict)
                await session.flush()
                results.append(FAAssetPatchResult(asset_id=patch.asset_id, success=True, message=f"Asset patched successfully ({len(updated_fields)} fields)", updated_fields=updated_fields))
                logger.info(f"Asset patched: id={patch.asset_id}, fields={updated_fields}")

            currency_changed_ids = [asset_id for asset_id, asset in assets_by_id.items() if asset.currency != currency_before[asset_id]]
            if currency_changed_ids:
                failing = next((index, patch.asset_id) for index, (patch, _) in enumerate(prepared) if patch.asset_id in currency_changed_ids)
            cache_keys = await provider_cache_keys(session, currency_changed_ids) if commit else []
            await delete_market_data_of_assets(session, currency_changed_ids)
        except Exception as exc:  # noqa: BLE001 — isolation boundary: any failure while applying rolls the whole batch back
            index, asset_id = failing
            logger.warning("Asset patch batch rolled back: applying an item failed", asset_id=asset_id, index=index, exc_info=exc)
            await session.rollback()
            issue = FAAssetPatchIssue(asset_id=asset_id, index=index, code=FAAssetPatchCode.PATCH_FAILED, message=f"Asset {asset_id} could not be saved ({type(exc).__name__})")
            return AssetCRUDService._unsaved_response(patches, [issue], warnings)

        if not commit:
            # Dry run: what would have been saved, nothing written, no cache touched.
            await session.rollback()
            return FABulkAssetPatchResponse(results=results, success_count=len(results), errors=[], committed=False, issues=[], warnings=warnings)

        # 3. The single commit of the batch.
        await session.commit()

        await drop_provider_caches(cache_keys, asset_ids=currency_changed_ids)

        return FABulkAssetPatchResponse(results=results, success_count=len(results), errors=[], committed=True, issues=[], warnings=warnings)

    @staticmethod
    def _prepare_patch_payloads(patches: List[FAAssetPatchItem]) -> list[tuple[FAAssetPatchItem, dict]]:
        """Each patch's payload, computed once (pure CPU), with the explicit-None clearing rules (T-2, classification)."""
        prepared: list[tuple[FAAssetPatchItem, dict]] = []
        for patch in patches:
            patch_dict = patch.model_dump(mode="json", exclude={"asset_id"}, exclude_unset=True, exclude_none=True)
            # An explicit null clears a nullable column (T-2: exclude_none above used to drop it, so removing an icon,
            # a user URL or an identifier answered success and changed nothing).
            for field in sorted(CLEARED_BY_NULL & patch.model_fields_set):
                if getattr(patch, field) is None:
                    patch_dict[field] = None
            # Preserve explicit clears inside the atomic classification blocks too.
            # exclude_none above would turn {"sector_area": None} into {}, clearing all.
            if "classification_params" in patch.model_fields_set:
                patch_dict["classification_params"] = patch.classification_params.model_dump(mode="json", exclude_unset=True) if patch.classification_params is not None else None
            prepared.append((patch, patch_dict))
        return prepared

    @staticmethod
    async def _check_patch_items(prepared: list[tuple[FAAssetPatchItem, dict]], assets_by_id: dict[int, Asset], session: AsyncSession) -> tuple[list[FAAssetPatchIssue], list[FAAssetPatchIssue]]:
        """Judge every item of the batch, writing nothing: ``(issues, warnings)``, each sorted by item index.

        - an asset that does not exist -> issue ``assetNotFound``;
        - a type that becomes INDEX on an asset that has transactions -> issue ``indexWithTransactions`` (``tx_count``);
          an asset that already is INDEX is never blocked and never cleaned up;
        - a name that another asset holds -> issue ``assetNameTaken`` (``name``), the clash ``uq_assets_display_name`` would
          raise at the flush. Names are judged item after item, as the apply step meets them: a name an earlier item of the
          batch has just left is free, a name still held (by an asset inside or outside the batch) is not, and an asset
          that keeps its own name is no clash. Two items taking the same new name: the second one is the issue;
        - a type that moves to another family -> warning ``assetFamilyChange`` (``from``, ``to``): it never blocks.

        The transactions are counted in one query, and only when an item turns an asset into an INDEX (P0-5); the names
        in one query too, and only when an item renames an asset.
        """
        issues: list[FAAssetPatchIssue] = []
        warnings: list[FAAssetPatchIssue] = []
        # The type each asset would have, item after item: one batch may patch the same asset twice.
        projected_type = {asset_id: AssetType(asset.asset_type) for asset_id, asset in assets_by_id.items()}
        type_changes: list[tuple[int, int, AssetType, AssetType]] = []
        # The asset that holds each name, item after item: the batch's assets by their loaded names, the others from one query.
        held_by = await AssetCRUDService._names_held(prepared, assets_by_id, session)
        for index, (patch, patch_dict) in enumerate(prepared):
            if patch.asset_id not in assets_by_id:
                issues.append(FAAssetPatchIssue(asset_id=patch.asset_id, index=index, code=FAAssetPatchCode.ASSET_NOT_FOUND, message=f"Asset {patch.asset_id} not found"))
                continue
            new_name = patch_dict.get("display_name")
            if new_name:
                holder = held_by.get(new_name)
                if holder is not None and holder != patch.asset_id:
                    issues.append(FAAssetPatchIssue(asset_id=patch.asset_id, index=index, code=FAAssetPatchCode.ASSET_NAME_TAKEN, message=f"The name '{new_name}' is already used by another asset", params={"name": new_name}, field="display_name"))
                else:
                    held_by = {name: owner for name, owner in held_by.items() if owner != patch.asset_id}
                    held_by[new_name] = patch.asset_id
            if patch_dict.get("asset_type") is None:
                continue
            old_type, new_type = projected_type[patch.asset_id], AssetType(patch_dict["asset_type"])
            projected_type[patch.asset_id] = new_type
            type_changes.append((index, patch.asset_id, old_type, new_type))

        to_index_ids = sorted({asset_id for _, asset_id, old_type, new_type in type_changes if new_type == AssetType.INDEX and old_type != AssetType.INDEX})
        tx_counts: dict[int, int] = {}
        if to_index_ids:
            tx_counts = dict((await session.execute(select(Transaction.asset_id, func.count()).where(Transaction.asset_id.in_(to_index_ids)).group_by(Transaction.asset_id))).all())

        for index, asset_id, old_type, new_type in type_changes:
            tx_count = tx_counts.get(asset_id, 0)
            verdict = classify_type_change(old_type, new_type, tx_count)
            if verdict == TypeChangeVerdict.INDEX_WITH_TRANSACTIONS:
                issues.append(FAAssetPatchIssue(asset_id=asset_id, index=index, code=FAAssetPatchCode.INDEX_WITH_TRANSACTIONS, message=f"Asset {asset_id} has {tx_count} transactions and cannot become an INDEX", params={"tx_count": tx_count}, field="asset_type"))
            elif verdict == TypeChangeVerdict.FAMILY_WARNING:
                warnings.append(FAAssetPatchIssue(asset_id=asset_id, index=index, code=FAAssetPatchCode.ASSET_FAMILY_CHANGE, message=f"Asset {asset_id} moves from {old_type.value} to {new_type.value}, another type family", params={"from": old_type.value, "to": new_type.value}, field="asset_type"))

        issues.sort(key=lambda issue: issue.index)
        return issues, warnings

    @staticmethod
    async def _names_held(prepared: list[tuple[FAAssetPatchItem, dict]], assets_by_id: dict[int, Asset], session: AsyncSession) -> dict[str, int]:
        """``{name: asset id}`` of the names the batch can clash with: the loaded names of the batch's assets, plus the
        holders outside the batch of the names the items ask for (one query, none when nobody renames)."""
        held_by = {asset.display_name: asset_id for asset_id, asset in assets_by_id.items()}
        wanted = {patch_dict["display_name"] for _, patch_dict in prepared if patch_dict.get("display_name")}
        if wanted:
            rows = (await session.execute(select(Asset.id, Asset.display_name).where(Asset.display_name.in_(wanted)))).all()
            held_by.update({name: asset_id for asset_id, name in rows if asset_id not in assets_by_id})
        return held_by

    @staticmethod
    def _unsaved_response(patches: List[FAAssetPatchItem], issues: list[FAAssetPatchIssue], warnings: list[FAAssetPatchIssue]) -> FABulkAssetPatchResponse:
        """The answer of a batch that saved nothing: every result failed, the item with an issue carries its message."""
        message_of = {}
        for issue in issues:
            message_of.setdefault(issue.index, issue.message)
        results = [FAAssetPatchResult(asset_id=patch.asset_id, success=False, message=message_of.get(index, "Not saved: another asset of the batch has an issue"), updated_fields=None) for index, patch in enumerate(patches)]
        return FABulkAssetPatchResponse(results=results, success_count=0, errors=[], committed=False, issues=issues, warnings=warnings)

    @staticmethod
    def _apply_patch_item(asset: Asset, patch_dict: dict) -> List[OldNew[str]]:  # noqa: C901 — per-field patch mapping, classification shallow-merge branch
        """Write one item's fields on its asset (``setattr``, no flush): the fields written, old and new."""
        asset_classification_params_before = json.loads(asset.classification_params) if asset.classification_params else {}
        logger.debug(f"Asset found for patching: id={asset.id}: {asset.model_dump_json()}")

        # Track updated fields
        updated_fields: List[OldNew[str]] = []

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

        return updated_fields

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
            # X-R74: the log keeps the error; the answer never echoes it (an SQL error names the schema)
            raise AssetSourceError("Merge failed: internal error", "MERGE_FAILED", {"source_asset_id": source_asset_id, "target_asset_id": target_asset_id}) from e

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
