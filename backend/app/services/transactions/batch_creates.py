"""
Batch stages that add rows, for ``TransactionService.execute_batch``: creates, promotes in place, and the links
between the legs of the pairs created together.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from backend.app.db.models import Asset, AssetType, Transaction, TransactionType
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions.batch import TXBatchResultItem, TXPromoteBatchItem, TXPromoteResolvedFields, TXValidationCode, TXValidationIssue
from backend.app.schemas.transactions.transactions import tags_to_csv, validate_transaction_business_rules
from backend.app.schemas.transactions.type_metadata import cost_basis_allowed
from backend.app.services.transactions.transaction_batch_context import TransactionBatchContext
from backend.app.utils.datetime_utils import utcnow

if TYPE_CHECKING:
    from backend.app.services.transactions.transaction_service import TransactionService


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
            context.created_by_index[original_index] = transaction
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

        rule_issues = _promoted_state_issues(context, original_index, target_type, transaction_a, transaction_b)
        rule_issues += _resolved_cost_issues(original_index, target_type, transaction_a, transaction_b, item)
        if rule_issues:
            context.issues.extend(rule_issues)
            continue

        transaction_a.type = target_type
        transaction_b.type = target_type
        transaction_a.related_transaction_id = transaction_b.id
        transaction_b.related_transaction_id = transaction_a.id
        for transaction in (transaction_a, transaction_b):
            # Decision 47: a side whose new type takes no cost basis (the giving side of a TRANSFER) drops the cost an
            # ADJUSTMENT-out carried.
            if not cost_basis_allowed(target_type, transaction.quantity):
                transaction.cost_basis_override = None
                transaction.cost_basis_currency = None
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


def _resolved_cost_issues(original_index: int, target_type: TransactionType, transaction_a: Transaction, transaction_b: Transaction, item: TXPromoteBatchItem) -> list[TXValidationIssue]:
    """N78 (W-B72): a cost basis the promotion resolves is refused when neither row can take one under the new type — a
    cash pair — instead of being written on both. Clearing it (null) is always allowed."""
    cost = item.resolved_fields.cost_basis_override if item.resolved_fields is not None else None
    if cost is None or any(cost_basis_allowed(target_type, transaction.quantity) for transaction in (transaction_a, transaction_b)):
        return []
    quantity = max(transaction_a.quantity or 0, transaction_b.quantity or 0)
    return [
        TXValidationIssue(
            operation="promote",
            index=original_index,
            ref_id=None,
            error=f"{target_type.value} with qty={quantity} takes no cost basis",
            code="costBasisNotAllowed",
            params={"type": target_type.value, "qty": str(quantity)},
            field="cost_basis_override",
        )
    ]


def _promoted_state_issues(
    context: TransactionBatchContext,
    original_index: int,
    target_type: TransactionType,
    transaction_a: Transaction,
    transaction_b: Transaction,
) -> list[TXValidationIssue]:
    """Business-rule issues of the two rows as they would be once promoted.

    A promote changes the type of two rows, so both must satisfy the rules of the new
    type like any created or updated row; a row linked to an asset event, for example,
    cannot become a TRANSFER. The changed type (``changed_fields``) holds the points of
    decision P6 on every field: a promote into a CASH_TRANSFER or an FX_CONVERSION of a
    row at 0 is refused (``cashNonzero``). Nothing is changed when an issue is returned.
    """
    issues: list[TXValidationIssue] = []
    for transaction in (transaction_a, transaction_b):
        cash = Currency(code=transaction.currency, amount=transaction.amount) if transaction.currency else None
        rule_errors = validate_transaction_business_rules(
            tx_type=target_type,
            asset_id=transaction.asset_id,
            quantity=transaction.quantity,
            cash=cash,
            asset_event_id=transaction.asset_event_id,
            cost_basis_mode=None,
            changed_fields=frozenset({"type"}),
        )
        for rule_error in rule_errors:
            issues.append(
                TXValidationIssue(
                    operation="promote",
                    index=original_index,
                    ref_id=transaction.id if transaction.id in context.existing_by_id else None,
                    error=rule_error.message(),
                    code=rule_error.type,
                    params=(dict(rule_error.context) if rule_error.context else None),
                )
            )
    return issues


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
    resolved_fields: TXPromoteResolvedFields | None,
) -> None:
    """Apply the user-resolved fields symmetrically where required: each field the request names
    (``model_fields_set``), an explicit null included where the field takes one (H-41: typed at the batch's parse)."""
    if resolved_fields is None:
        return
    chosen = resolved_fields.model_fields_set
    if "description" in chosen:
        description = resolved_fields.description
        transaction_a.description = description
        transaction_b.description = description
    if "cost_basis_override" in chosen:
        _apply_promote_cost_basis(
            transaction_a,
            transaction_b,
            resolved_fields.cost_basis_override,
        )
    if "tags" in chosen:
        csv_tags = tags_to_csv(resolved_fields.tags)
        transaction_a.tags = csv_tags
        transaction_b.tags = csv_tags
    if resolved_fields.date is not None:
        transaction_a.date = resolved_fields.date
        transaction_b.date = resolved_fields.date


def _apply_promote_cost_basis(
    transaction_a: Transaction,
    transaction_b: Transaction,
    cost_basis: Currency | None,
) -> None:
    """Apply resolved cost basis with receiver-only TRANSFER semantics."""
    amount = cost_basis.amount if cost_basis is not None else None
    currency_code = cost_basis.code if cost_basis is not None else None

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
