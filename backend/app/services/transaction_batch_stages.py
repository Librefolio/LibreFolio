"""Ordered stages used by ``TransactionService.execute_batch``."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional, Tuple

from pydantic import ValidationError
from sqlalchemy import select

from backend.app.db.models import Asset, AssetType, Transaction, TransactionType, UserRole
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import (
    TXBatchResponse,
    TXBatchResultItem,
    TXCreateItem,
    TXPromoteBatchItem,
    TXSplitBatchItem,
    TXUpdateItem,
    TXValidationCode,
    TXValidationIssue,
    get_swap_group,
    tags_to_csv,
    validate_transaction_business_rules,
)
from backend.app.services.transaction_batch_context import (
    BalanceValidationError,
    TransactionBatchContext,
)
from backend.app.utils.datetime_utils import parse_ISO_date, utcnow

if TYPE_CHECKING:
    from backend.app.services.transaction_service import TransactionService


def _loc_to_field(loc: tuple | list) -> Optional[str]:
    """Convert a Pydantic location tuple to a dotted field path."""
    parts = [str(part) for part in loc if not isinstance(part, int)]
    return ".".join(parts) if parts else None


def _parse_lenient(
    raw_list: list[dict],
    model_class: type,
    operation: str,
) -> Tuple[list[tuple[int, Any]], list[TXValidationIssue]]:
    """Validate each raw row independently and retain every row-level issue."""
    parsed: list[tuple[int, Any]] = []
    issues: list[TXValidationIssue] = []
    for idx, raw in enumerate(raw_list):
        try:
            parsed.append((idx, model_class.model_validate(raw)))
        except ValidationError as exc:
            for error in exc.errors():
                if error.get("type") == "multipleBusinessRuleErrors":
                    context = error.get("ctx", {})
                    for sub_error in context.get("errors", []):
                        issues.append(
                            TXValidationIssue(
                                operation=operation,
                                index=idx,
                                error=sub_error.get("msg", ""),
                                code=sub_error.get("code"),
                                params=sub_error.get("ctx") or None,
                                field=None,
                            )
                        )
                    continue
                issues.append(
                    TXValidationIssue(
                        operation=operation,
                        index=idx,
                        error=error.get("msg", str(error)),
                        code=error.get("type"),
                        params=None,
                        field=_loc_to_field(error.get("loc", ())),
                    )
                )
    return parsed, issues


def parse_inputs(context: TransactionBatchContext) -> None:
    """Parse operation lists in their contractually visible issue order."""
    context.parsed_creates, create_issues = _parse_lenient(context.creates_raw, TXCreateItem, "create")
    context.parsed_updates, update_issues = _parse_lenient(context.updates_raw, TXUpdateItem, "update")
    context.parsed_splits, split_issues = _parse_lenient(context.splits_raw, TXSplitBatchItem, "split")
    context.parsed_promotes, promote_issues = _parse_lenient(context.promotes_raw, TXPromoteBatchItem, "promote")
    context.issues.extend(create_issues)
    context.issues.extend(update_issues)
    context.issues.extend(split_issues)
    context.issues.extend(promote_issues)


async def preload_and_authorize(
    service: TransactionService,
    context: TransactionBatchContext,
) -> bool:
    """Load referenced rows, collect touched brokers, and enforce EDITOR access."""
    for _, item in context.parsed_creates:
        context.touched_brokers.add(item.broker_id)

    ids_to_lookup = _referenced_existing_ids(context)
    await _load_existing_transactions(service, context, ids_to_lookup)
    await _load_missing_split_partners(service, context, ids_to_lookup)
    await _append_access_issues(service, context)

    return any(issue.code == "accessDenied" for issue in context.issues)


def _referenced_existing_ids(context: TransactionBatchContext) -> set[int]:
    """Collect database IDs referenced by mutation operations."""
    ids_to_lookup: set[int] = set(context.deletes)
    for _, item in context.parsed_updates:
        ids_to_lookup.add(item.id)
    for _, item in context.parsed_splits:
        ids_to_lookup.add(item.id_a)
        ids_to_lookup.add(item.id_b)
    for _, item in context.parsed_promotes:
        if item.id_a is not None:
            ids_to_lookup.add(item.id_a)
        if item.id_b is not None:
            ids_to_lookup.add(item.id_b)
    return ids_to_lookup


async def _load_existing_transactions(
    service: TransactionService,
    context: TransactionBatchContext,
    ids_to_lookup: set[int],
) -> None:
    """Load referenced rows once and include their brokers in access scope."""
    if ids_to_lookup:
        existing_txs = await service.get_by_ids(list(ids_to_lookup))
        context.existing_by_id = {tx.id: tx for tx in existing_txs}
        context.touched_brokers.update(tx.broker_id for tx in existing_txs)


async def _load_missing_split_partners(
    service: TransactionService,
    context: TransactionBatchContext,
    ids_to_lookup: set[int],
) -> None:
    """Preserve the defensive split-partner re-fetch."""
    for _, item in context.parsed_splits:
        for split_id in (item.id_a, item.id_b):
            if split_id not in context.existing_by_id:
                ids_to_lookup.add(split_id)

    missing_split_ids = {split_id for _, item in context.parsed_splits for split_id in (item.id_a, item.id_b) if split_id not in context.existing_by_id}
    if missing_split_ids:
        partners = await service.get_by_ids(list(missing_split_ids))
        for transaction in partners:
            context.existing_by_id[transaction.id] = transaction
        context.touched_brokers.update(transaction.broker_id for transaction in partners)


async def _append_access_issues(
    service: TransactionService,
    context: TransactionBatchContext,
) -> None:
    """Append one issue per touched broker lacking EDITOR access."""
    if context.user_id is not None:
        for broker_id in context.touched_brokers:
            role = await service._check_broker_access(
                broker_id,
                context.user_id,
                min_role=UserRole.EDITOR,
            )
            if role is None:
                context.issues.append(
                    TXValidationIssue(
                        operation="create",
                        index=0,
                        ref_id=None,
                        error=f"Access denied: EDITOR required for broker {broker_id}",
                        code=TXValidationCode.ACCESS_DENIED.value,
                        params={"brokerId": broker_id},
                    )
                )


async def apply_deletes(
    service: TransactionService,
    context: TransactionBatchContext,
) -> None:
    """Apply requested deletes while preserving linked-pair integrity."""
    id_set_deletes = set(context.deletes)
    for index, transaction_id in enumerate(context.deletes):
        transaction = context.existing_by_id.get(transaction_id)
        if transaction is None:
            context.issues.append(
                TXValidationIssue(
                    operation="delete",
                    index=index,
                    ref_id=transaction_id,
                    error=f"Transaction {transaction_id} not found",
                    code=TXValidationCode.TX_NOT_FOUND.value,
                    params={"id": transaction_id},
                )
            )
            continue
        if transaction.related_transaction_id and transaction.related_transaction_id not in id_set_deletes:
            context.issues.append(
                TXValidationIssue(
                    operation="delete",
                    index=index,
                    ref_id=transaction_id,
                    error=f"Cannot delete linked transaction {transaction_id} without its pair {transaction.related_transaction_id}",
                    code="pairDeleteIncomplete",
                    params={
                        "id": transaction_id,
                        "partnerId": transaction.related_transaction_id,
                    },
                )
            )
            continue
        try:
            previous = context.earliest_date_by_broker.get(transaction.broker_id)
            context.earliest_date_by_broker[transaction.broker_id] = transaction.date if previous is None else min(previous, transaction.date)
            await service.session.delete(transaction)
            context.results.append(
                TXBatchResultItem(
                    operation="delete",
                    index=index,
                    ids=[transaction_id],
                    status="success",
                )
            )
        except Exception as exc:  # noqa: BLE001
            context.issues.append(
                TXValidationIssue(
                    operation="delete",
                    index=index,
                    ref_id=transaction_id,
                    error=str(exc),
                )
            )


async def apply_splits(
    service: TransactionService,
    context: TransactionBatchContext,
) -> None:
    """Split linked pairs before dependent updates run."""
    for original_index, item in context.parsed_splits:
        transaction_a = context.existing_by_id.get(item.id_a)
        transaction_b = context.existing_by_id.get(item.id_b)
        if transaction_a is None or transaction_b is None:
            missing_id = item.id_a if transaction_a is None else item.id_b
            context.issues.append(
                TXValidationIssue(
                    operation="split",
                    index=original_index,
                    ref_id=missing_id,
                    error=f"Transaction {missing_id} not found",
                    code=TXValidationCode.TX_NOT_FOUND.value,
                )
            )
            continue
        if transaction_a.related_transaction_id != item.id_b or transaction_b.related_transaction_id != item.id_a:
            context.issues.append(
                TXValidationIssue(
                    operation="split",
                    index=original_index,
                    ref_id=item.id_a,
                    error=f"Transactions {item.id_a} and {item.id_b} are not a linked pair",
                    code=TXValidationCode.SPLIT_IDS_MISMATCH.value,
                )
            )
            continue

        split_types = service.SPLIT_TYPE_MAP.get(transaction_a.type)
        if split_types is None:
            context.issues.append(
                TXValidationIssue(
                    operation="split",
                    index=original_index,
                    ref_id=item.id_a,
                    error=f"Type {transaction_a.type.value} cannot be split",
                    code=TXValidationCode.TYPE_CANNOT_SPLIT.value,
                )
            )
            continue

        from_type, to_type = split_types
        if transaction_a.type == TransactionType.TRANSFER:
            if transaction_a.quantity < Decimal("0"):
                transaction_from, transaction_to = transaction_a, transaction_b
            else:
                transaction_from, transaction_to = transaction_b, transaction_a
        elif transaction_a.amount < Decimal("0"):
            transaction_from, transaction_to = transaction_a, transaction_b
        else:
            transaction_from, transaction_to = transaction_b, transaction_a

        transaction_from.type = from_type
        transaction_to.type = to_type
        transaction_from.related_transaction_id = None
        transaction_to.related_transaction_id = None

        if split_types != (
            TransactionType.ADJUSTMENT,
            TransactionType.ADJUSTMENT,
        ):
            transaction_from.asset_id = None
            transaction_to.asset_id = None

        transaction_from.updated_at = utcnow()
        transaction_to.updated_at = utcnow()

        for transaction in (transaction_from, transaction_to):
            previous = context.earliest_date_by_broker.get(transaction.broker_id)
            context.earliest_date_by_broker[transaction.broker_id] = transaction.date if previous is None else min(previous, transaction.date)

        context.results.append(
            TXBatchResultItem(
                operation="split",
                index=original_index,
                ids=[transaction_from.id, transaction_to.id],
                status="success",
            )
        )


async def apply_updates(
    service: TransactionService,
    context: TransactionBatchContext,
) -> None:
    """Apply parsed updates and validate each merged final state."""
    for original_index, item in context.parsed_updates:
        transaction = context.existing_by_id.get(item.id)
        if transaction is None:
            context.issues.append(
                TXValidationIssue(
                    operation="update",
                    index=original_index,
                    ref_id=item.id,
                    error=f"Transaction {item.id} not found",
                    code=TXValidationCode.TX_NOT_FOUND.value,
                    params={"id": item.id},
                )
            )
            continue
        try:
            check_date = _apply_update_type_and_date(transaction, item)
            _apply_update_values(transaction, item)
            await _apply_update_event(service, transaction, item)
            rule_errors = _validate_updated_final_state(transaction, item)
            if rule_errors:
                for rule_error in rule_errors:
                    context.issues.append(
                        TXValidationIssue(
                            operation="update",
                            index=original_index,
                            ref_id=item.id,
                            error=rule_error.message(),
                            code=rule_error.type,
                            params=(dict(rule_error.context) if rule_error.context else None),
                        )
                    )
                continue

            transaction.updated_at = utcnow()
            previous = context.earliest_date_by_broker.get(transaction.broker_id)
            context.earliest_date_by_broker[transaction.broker_id] = check_date if previous is None else min(previous, check_date)
            context.results.append(
                TXBatchResultItem(
                    operation="update",
                    index=original_index,
                    ids=[item.id],
                    status="success",
                )
            )
        except Exception as exc:  # noqa: BLE001
            context.issues.append(
                TXValidationIssue(
                    operation="update",
                    index=original_index,
                    ref_id=item.id,
                    error=str(exc),
                )
            )


def _apply_update_type_and_date(
    transaction: Transaction,
    item: TXUpdateItem,
):
    """Apply type/date fields and return the earliest replay date."""
    check_date = transaction.date
    if item.type is not None and item.type != transaction.type:
        allowed = get_swap_group(transaction.type)
        if item.type not in allowed:
            raise ValueError(f"Cannot change type from {transaction.type.value} to {item.type.value} (allowed swaps: {', '.join(tx_type.value for tx_type in allowed)})")
        transaction.type = item.type
    if item.date is not None:
        check_date = min(check_date, item.date)
        transaction.date = item.date
    return check_date


def _apply_update_values(
    transaction: Transaction,
    item: TXUpdateItem,
) -> None:
    """Apply optional scalar fields without changing their current semantics."""
    if item.quantity is not None:
        transaction.quantity = item.quantity
    if item.cash is not None:
        transaction.amount = item.cash.amount
        transaction.currency = item.cash.code
    if item.tags is not None:
        transaction.tags = tags_to_csv(item.tags)
    if item.description is not None:
        transaction.description = item.description
    if item.cost_basis_override is not None:
        transaction.cost_basis_override = item.cost_basis_override.amount
        transaction.cost_basis_currency = item.cost_basis_override.code


async def _apply_update_event(
    service: TransactionService,
    transaction: Transaction,
    item: TXUpdateItem,
) -> None:
    """Apply the event-link sentinel or validate a concrete event."""
    if item.asset_event_id is None:
        return
    if item.asset_event_id == 0:
        transaction.asset_event_id = None
        return
    if transaction.asset_id is None:
        raise ValueError("Cannot link asset_event_id: transaction has no asset_id")
    await service._validate_asset_event_link(
        item.asset_event_id,
        transaction.asset_id,
    )
    transaction.asset_event_id = item.asset_event_id


def _validate_updated_final_state(
    transaction: Transaction,
    item: TXUpdateItem,
):
    """Run shared business rules against the merged ORM state."""
    final_cash = Currency(code=transaction.currency, amount=transaction.amount) if transaction.currency else None
    return validate_transaction_business_rules(
        tx_type=transaction.type,
        asset_id=transaction.asset_id,
        quantity=transaction.quantity,
        cash=final_cash,
        asset_event_id=transaction.asset_event_id,
        cost_basis_mode=item.cost_basis_mode,
    )


async def validate_updated_pairs(
    service: TransactionService,
    context: TransactionBatchContext,
) -> None:
    """Validate pair description/tag equality after updates."""
    for original_index, item in context.parsed_updates:
        if item.tags is None and item.description is None:
            continue
        transaction = context.existing_by_id.get(item.id)
        if not transaction or not transaction.related_transaction_id:
            continue
        partner = context.existing_by_id.get(transaction.related_transaction_id)
        if partner is None:
            partner = await service.session.get(
                Transaction,
                transaction.related_transaction_id,
            )
        if partner is not None:
            description_result = service._validate_pair_description_tags(
                transaction,
                partner,
            )
            if description_result is not None:
                error_message, error_code, error_params = description_result
                context.issues.append(
                    TXValidationIssue(
                        operation="update",
                        index=original_index,
                        ref_id=item.id,
                        error=error_message,
                        code=error_code,
                        params=error_params,
                    )
                )


async def apply_creates(
    service: TransactionService,
    context: TransactionBatchContext,
) -> None:
    """Create valid rows, flushing each one to expose its generated ID."""
    for original_index, item in context.parsed_creates:
        try:
            if item.asset_id is not None:
                asset_result = await service.session.execute(select(Asset.asset_type).where(Asset.id == item.asset_id))
                if asset_result.scalar_one_or_none() == AssetType.INDEX:
                    raise ValueError("Cannot create transactions for INDEX assets")
            if item.asset_event_id is not None:
                assert item.asset_id is not None
                await service._validate_asset_event_link(
                    item.asset_event_id,
                    item.asset_id,
                )
            transaction = Transaction(
                broker_id=item.broker_id,
                asset_id=item.asset_id,
                type=item.type,
                date=item.date,
                quantity=item.quantity,
                amount=item.get_amount(),
                currency=item.get_currency(),
                tags=item.get_tags_csv(),
                description=item.description,
                cost_basis_override=(item.cost_basis_override.amount if item.cost_basis_override else None),
                cost_basis_currency=(item.cost_basis_override.code if item.cost_basis_override else None),
                asset_event_id=item.asset_event_id,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            service.session.add(transaction)
            await service.session.flush()
            previous = context.earliest_date_by_broker.get(transaction.broker_id)
            context.earliest_date_by_broker[transaction.broker_id] = transaction.date if previous is None else min(previous, transaction.date)
            if item.link_uuid:
                context.link_uuid_map[item.link_uuid].append((original_index, transaction))
            context.results.append(
                TXBatchResultItem(
                    operation="create",
                    index=original_index,
                    ids=[transaction.id],
                    link_uuid=item.link_uuid,
                    status="success",
                )
            )
        except Exception as exc:  # noqa: BLE001
            context.issues.append(
                TXValidationIssue(
                    operation="create",
                    index=original_index,
                    ref_id=None,
                    error=str(exc),
                )
            )


async def apply_promotes(
    service: TransactionService,
    context: TransactionBatchContext,
) -> None:
    """Promote compatible saved or same-batch rows into linked pairs."""
    for original_index, item in context.parsed_promotes:
        pair = _resolve_promote_pair(service, context, item, original_index)
        if pair is None:
            continue
        transaction_a, transaction_b = pair

        target_type = service._find_promote_rule_match(
            transaction_a,
            transaction_b,
        )
        if target_type is None:
            context.issues.append(
                TXValidationIssue(
                    operation="promote",
                    index=original_index,
                    error=f"No promote rule for {transaction_a.type.value}+{transaction_b.type.value}",
                    code=TXValidationCode.NO_PROMOTE_RULE.value,
                )
            )
            continue

        transaction_a.type = target_type
        transaction_b.type = target_type
        transaction_a.related_transaction_id = transaction_b.id
        transaction_b.related_transaction_id = transaction_a.id
        _apply_promote_resolved_fields(
            transaction_a,
            transaction_b,
            item.resolved_fields,
        )
        transaction_a.updated_at = utcnow()
        transaction_b.updated_at = utcnow()

        for transaction in (transaction_a, transaction_b):
            previous = context.earliest_date_by_broker.get(transaction.broker_id)
            context.earliest_date_by_broker[transaction.broker_id] = transaction.date if previous is None else min(previous, transaction.date)

        if item.link_uuid_a:
            context.consumed_link_uuids.add(item.link_uuid_a)
        if item.link_uuid_b:
            context.consumed_link_uuids.add(item.link_uuid_b)

        context.results.append(
            TXBatchResultItem(
                operation="promote",
                index=original_index,
                ids=[transaction_a.id, transaction_b.id],
                status="success",
            )
        )


def _resolve_promote_pair(
    service: TransactionService,
    context: TransactionBatchContext,
    item: TXPromoteBatchItem,
    original_index: int,
) -> tuple[Transaction, Transaction] | None:
    """Resolve and validate both promote references."""
    transaction_a = service._resolve_promote_ref(
        item.id_a,
        item.link_uuid_a,
        context.existing_by_id,
        context.link_uuid_map,
    )
    transaction_b = service._resolve_promote_ref(
        item.id_b,
        item.link_uuid_b,
        context.existing_by_id,
        context.link_uuid_map,
    )
    if transaction_a is None:
        context.issues.append(
            TXValidationIssue(
                operation="promote",
                index=original_index,
                error="Cannot resolve TX A reference",
                code=TXValidationCode.PROMOTE_REF_NOT_FOUND.value,
            )
        )
        return None
    if transaction_b is None:
        context.issues.append(
            TXValidationIssue(
                operation="promote",
                index=original_index,
                error="Cannot resolve TX B reference",
                code=TXValidationCode.PROMOTE_REF_NOT_FOUND.value,
            )
        )
        return None
    if transaction_a.related_transaction_id is not None:
        context.issues.append(
            TXValidationIssue(
                operation="promote",
                index=original_index,
                ref_id=getattr(transaction_a, "id", None),
                error=f"TX A ({transaction_a.id}) already paired",
                code=TXValidationCode.ALREADY_PAIRED.value,
            )
        )
        return None
    if transaction_b.related_transaction_id is not None:
        context.issues.append(
            TXValidationIssue(
                operation="promote",
                index=original_index,
                ref_id=getattr(transaction_b, "id", None),
                error=f"TX B ({transaction_b.id}) already paired",
                code=TXValidationCode.ALREADY_PAIRED.value,
            )
        )
        return None
    return transaction_a, transaction_b


def _apply_promote_resolved_fields(
    transaction_a: Transaction,
    transaction_b: Transaction,
    resolved_fields: dict[str, Any] | None,
) -> None:
    """Apply the user-resolved fields symmetrically where required."""
    if not resolved_fields:
        return
    if "description" in resolved_fields:
        description = resolved_fields["description"]
        transaction_a.description = description
        transaction_b.description = description
    if "cost_basis_override" in resolved_fields:
        _apply_promote_cost_basis(
            transaction_a,
            transaction_b,
            resolved_fields["cost_basis_override"],
        )
    if "tags" in resolved_fields:
        csv_tags = tags_to_csv(resolved_fields["tags"])
        transaction_a.tags = csv_tags
        transaction_b.tags = csv_tags
    if "date" in resolved_fields:
        resolved_date = parse_ISO_date(resolved_fields["date"])
        transaction_a.date = resolved_date
        transaction_b.date = resolved_date


def _apply_promote_cost_basis(
    transaction_a: Transaction,
    transaction_b: Transaction,
    raw_cost_basis: Any,
) -> None:
    """Apply resolved cost basis with receiver-only TRANSFER semantics."""
    if raw_cost_basis is not None:
        cost_basis = Currency.model_validate(raw_cost_basis)
        amount = cost_basis.amount
        currency_code = cost_basis.code
    else:
        amount = None
        currency_code = None

    if transaction_a.quantity and transaction_a.quantity > 0:
        transaction_a.cost_basis_override = amount
        transaction_a.cost_basis_currency = currency_code
        transaction_b.cost_basis_override = None
        transaction_b.cost_basis_currency = None
    elif transaction_b.quantity and transaction_b.quantity > 0:
        transaction_b.cost_basis_override = amount
        transaction_b.cost_basis_currency = currency_code
        transaction_a.cost_basis_override = None
        transaction_a.cost_basis_currency = None
    else:
        transaction_a.cost_basis_override = amount
        transaction_a.cost_basis_currency = currency_code
        transaction_b.cost_basis_override = amount
        transaction_b.cost_basis_currency = currency_code


def resolve_create_links(
    service: TransactionService,
    context: TransactionBatchContext,
) -> None:
    """Resolve unconsumed create UUID groups into validated reciprocal links."""
    for link_uuid, pairs in context.link_uuid_map.items():
        if link_uuid in context.consumed_link_uuids:
            continue
        if len(pairs) == 2:
            pair_result = service._validate_linked_pair(
                pairs[0][1],
                pairs[1][1],
            )
            if pair_result is not None:
                pair_error, pair_code, pair_params = pair_result
                context.issues.append(
                    TXValidationIssue(
                        operation="create",
                        index=pairs[0][0],
                        ref_id=None,
                        error=pair_error,
                        code=pair_code,
                        params=pair_params,
                    )
                )
                continue
            description_result = service._validate_pair_description_tags(
                pairs[0][1],
                pairs[1][1],
            )
            if description_result is not None:
                description_error, description_code, description_params = description_result
                context.issues.append(
                    TXValidationIssue(
                        operation="create",
                        index=pairs[0][0],
                        ref_id=None,
                        error=description_error,
                        code=description_code,
                        params=description_params,
                    )
                )
                continue
            pairs[0][1].related_transaction_id = pairs[1][1].id
            pairs[1][1].related_transaction_id = pairs[0][1].id
        else:
            context.issues.append(
                TXValidationIssue(
                    operation="create",
                    index=pairs[0][0] if pairs else 0,
                    ref_id=None,
                    error=f"link_uuid '{link_uuid}' has {len(pairs)} creates (expected 2)",
                    code=TXValidationCode.LINK_UUID_PAIR_COUNT.value,
                    params={"linkUuid": link_uuid, "count": len(pairs)},
                )
            )


async def compute_wac_and_fx_issues(
    service: TransactionService,
    context: TransactionBatchContext,
) -> None:
    """Compute inline WAC and translate missing FX into batch issues."""
    has_non_balance_issues = any(
        issue.code
        not in (
            TXValidationCode.BALANCE_ASSET_NEGATIVE.value,
            TXValidationCode.BALANCE_CASH_NEGATIVE.value,
        )
        for issue in context.issues
    )
    if not has_non_balance_issues:
        context.wac_results = await service._compute_wac_for_auto_items(
            context.parsed_creates,
            context.parsed_updates,
            context.link_uuid_map,
        )

    if context.wac_results:
        for wac_result in context.wac_results:
            if wac_result.wac is None and wac_result.wac_missing_pairs:
                pair_strings = [missing_pair.pair for missing_pair in wac_result.wac_missing_pairs]
                context.issues.append(
                    TXValidationIssue(
                        operation=wac_result.operation or "create",
                        index=(wac_result.index if wac_result.index is not None else 0),
                        ref_id=None,
                        error=f"WAC calculation failed: missing FX pairs {', '.join(pair_strings)}",
                        code=TXValidationCode.WAC_FX_UNAVAILABLE.value,
                        params={
                            "pairs": pair_strings,
                            "pair_details": [
                                {
                                    "pair": missing_pair.pair,
                                    "dates": [missing_date.isoformat() for missing_date in missing_pair.dates],
                                }
                                for missing_pair in wac_result.wac_missing_pairs
                            ],
                        },
                        field="cost_basis_override",
                    )
                )


async def validate_cost_basis(
    service: TransactionService,
    context: TransactionBatchContext,
) -> None:
    """Verify required cost basis after auto-WAC and promote handling."""
    await service.session.flush()

    auto_create_indices = _auto_mode_indices(context.parsed_creates)
    auto_update_indices = _auto_mode_indices(context.parsed_updates)
    promoted_create_indices = {
        original_index
        for link_uuid in context.consumed_link_uuids
        for original_index, _transaction in context.link_uuid_map.get(
            link_uuid,
            [],
        )
    }

    checked_create_indices = _check_linked_create_cost_basis(
        service,
        context,
        auto_create_indices,
    )
    await _check_result_create_cost_basis(
        service,
        context,
        auto_create_indices,
        promoted_create_indices,
        checked_create_indices,
    )
    await _check_update_cost_basis(
        service,
        context,
        auto_update_indices,
    )


def _auto_mode_indices(parsed_items: list[tuple[int, Any]]) -> set[int]:
    """Return original indices whose cost-basis mode uses auto WAC."""
    return {original_index for original_index, item in parsed_items if getattr(item, "cost_basis_mode", None) in ("auto", "auto-detail")}


def _check_linked_create_cost_basis(
    service: TransactionService,
    context: TransactionBatchContext,
    auto_create_indices: set[int],
) -> set[int]:
    """Check create rows retained in UUID groups."""
    checked_create_indices: set[int] = set()
    for link_uuid, pairs in context.link_uuid_map.items():
        if link_uuid in context.consumed_link_uuids:
            continue
        for original_index, transaction in pairs:
            if original_index in auto_create_indices:
                continue
            if service._requires_cost_basis(transaction) and transaction.cost_basis_override is None:
                checked_create_indices.add(original_index)
                _append_cost_basis_issue(
                    context,
                    operation="create",
                    index=original_index,
                    ref_id=None,
                    transaction=transaction,
                )
    return checked_create_indices


async def _check_result_create_cost_basis(
    service: TransactionService,
    context: TransactionBatchContext,
    auto_create_indices: set[int],
    promoted_create_indices: set[int],
    checked_create_indices: set[int],
) -> None:
    """Check standalone creates represented by successful result rows."""
    for result in context.results:
        if result.operation != "create" or result.status != "success" or result.index in checked_create_indices:
            continue
        if result.index in auto_create_indices or result.index in promoted_create_indices:
            continue
        for transaction_id in result.ids or []:
            transaction = await service.session.get(Transaction, transaction_id)
            if transaction and service._requires_cost_basis(transaction) and transaction.cost_basis_override is None:
                _append_cost_basis_issue(
                    context,
                    operation="create",
                    index=result.index,
                    ref_id=None,
                    transaction=transaction,
                )


async def _check_update_cost_basis(
    service: TransactionService,
    context: TransactionBatchContext,
    auto_update_indices: set[int],
) -> None:
    """Check parsed updates not handled by auto WAC."""
    for original_index, item in context.parsed_updates:
        if original_index in auto_update_indices:
            continue
        transaction = await service.session.get(Transaction, item.id)
        if transaction and service._requires_cost_basis(transaction) and transaction.cost_basis_override is None:
            _append_cost_basis_issue(
                context,
                operation="update",
                index=original_index,
                ref_id=item.id,
                transaction=transaction,
            )


def _append_cost_basis_issue(
    context: TransactionBatchContext,
    *,
    operation: str,
    index: int,
    ref_id: int | None,
    transaction: Transaction,
) -> None:
    """Append the stable required-cost-basis issue shape."""
    context.issues.append(
        TXValidationIssue(
            operation=operation,
            index=index,
            ref_id=ref_id,
            error=f"{transaction.type.value} with qty>0 requires cost_basis_override",
            code=TXValidationCode.COST_BASIS_REQUIRED.value,
            params={"type": transaction.type.value},
            field="cost_basis_override",
        )
    )


async def validate_balances(
    service: TransactionService,
    context: TransactionBatchContext,
) -> None:
    """Flush and replay balances for every affected broker."""
    try:
        await service.session.flush()
        batch_transaction_ids: dict[int, tuple] = {}
        for result in context.results:
            if result.status == "success" and result.ids:
                for transaction_id in result.ids:
                    batch_transaction_ids[transaction_id] = (
                        result.operation,
                        result.index,
                    )
        for broker_id, from_date in context.earliest_date_by_broker.items():
            await service._validate_broker_balances(
                broker_id,
                from_date,
                batch_tx_ids=batch_transaction_ids,
            )
    except BalanceValidationError as exc:
        context.issues.append(
            TXValidationIssue(
                operation=exc.batch_operation,
                index=exc.batch_index,
                ref_id=None,
                error=str(exc),
                code=exc.code,
                params=exc.params,
            )
        )
    except Exception as exc:  # noqa: BLE001
        context.issues.append(
            TXValidationIssue(
                operation="create",
                index=-1,
                ref_id=None,
                error=f"Balance validation error: {exc}",
            )
        )


def finalize_response(context: TransactionBatchContext) -> TXBatchResponse:
    """Build the response without committing or rolling back the session."""
    success_count = sum(1 for result in context.results if result.status == "success")
    if context.commit_requested and context.issues:
        for result in context.results:
            if result.status == "success":
                result.status = "simulated"

    if context.issues:
        return TXBatchResponse(
            committed=False,
            issues=context.issues,
            results=context.results,
            success_count=success_count,
            wac_results=context.wac_results,
        )
    if not context.commit_requested:
        return TXBatchResponse(
            committed=False,
            issues=[],
            results=context.results,
            success_count=success_count,
            wac_results=context.wac_results,
        )
    return TXBatchResponse(
        committed=True,
        issues=[],
        results=context.results,
        success_count=success_count,
        wac_results=context.wac_results,
    )
