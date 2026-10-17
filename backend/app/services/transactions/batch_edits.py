"""
Batch stages on saved rows, for ``TransactionService.execute_batch``: deletes, splits of linked pairs, updates,
and the check of the pairs an update touched.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from backend.app.db.models import Transaction, TransactionType
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions.batch import TXBatchResultItem, TXValidationCode, TXValidationIssue
from backend.app.schemas.transactions.transactions import TXUpdateItem, tags_to_csv, validate_transaction_business_rules
from backend.app.schemas.transactions.type_metadata import cost_basis_allowed, get_swap_group
from backend.app.services.transactions.transaction_batch_context import TransactionBatchContext, changed_rule_fields
from backend.app.utils.datetime_utils import utcnow

if TYPE_CHECKING:
    from backend.app.services.transactions.transaction_service import TransactionService


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


def pair_sides(transaction_a: Transaction, transaction_b: Transaction) -> tuple[Transaction, Transaction]:
    """The (from, to) halves of a linked pair: the side giving the asset (TRANSFER, by quantity) or the cash (by amount)."""
    if transaction_a.type == TransactionType.TRANSFER:
        gives = transaction_a.quantity < Decimal("0")
    else:
        gives = transaction_a.amount < Decimal("0")
    return (transaction_a, transaction_b) if gives else (transaction_b, transaction_a)


def make_standalone(transaction: Transaction, standalone_type: TransactionType) -> None:
    """Turn one half of a linked pair into a standalone row, in place, as a split does.

    The row loses its link; a WITHDRAWAL or DEPOSIT also loses the asset (a cash row has none), an ADJUSTMENT
    keeps it. Every other column stays: date, quantity, amount, currency, cost basis, description, tags.
    """
    transaction.type = standalone_type
    transaction.related_transaction_id = None
    if standalone_type != TransactionType.ADJUSTMENT:
        transaction.asset_id = None
    transaction.updated_at = utcnow()


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
        pair_type = transaction_a.type
        transaction_from, transaction_to = pair_sides(transaction_a, transaction_b)
        make_standalone(transaction_from, from_type)
        make_standalone(transaction_to, to_type)
        if pair_type == TransactionType.TRANSFER:
            # Decision 47: the giving leg becomes an ADJUSTMENT-out at its own broker's Auto cost, computed with the
            # batch's other costs once every row of it is in place (compute_wac_and_fx_issues).
            context.handover_rows.append((original_index, transaction_from))

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
            rule_errors = _validate_updated_final_state(transaction, item, changed_rule_fields(context.stored_rule_values.get(item.id), transaction))
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
    """Apply optional scalar fields: a missing field leaves the stored value.

    An explicit null ``cost_basis_override`` removes the manual cost basis (decision P5, W-B30) where the row's final
    type and side take one (``cost_basis_allowed``); elsewhere it is ignored, so the handover cost decision 47 writes
    on a giving leg stays (coordinator decision B, 16/10). An update asking for an Auto cost (``cost_basis_mode`` auto
    or auto-detail) ignores it too and writes its own. Where a cost basis is required, the removal is refused later
    with ``costBasisRequired`` (N2's check of the changed cost fields).
    """
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
    elif "cost_basis_override" in item.model_fields_set and item.cost_basis_mode not in ("auto", "auto-detail") and cost_basis_allowed(transaction.type, transaction.quantity):
        transaction.cost_basis_override = None
        transaction.cost_basis_currency = None


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
    changed_fields: frozenset[str],
):
    """Run shared business rules against the merged ORM state; the points of decision P6 only on the fields the update
    changed (``changed_fields``, from ``changed_rule_fields``)."""
    final_cash = Currency(code=transaction.currency, amount=transaction.amount) if transaction.currency else None
    return validate_transaction_business_rules(
        tx_type=transaction.type,
        asset_id=transaction.asset_id,
        quantity=transaction.quantity,
        cash=final_cash,
        asset_event_id=transaction.asset_event_id,
        cost_basis_mode=item.cost_basis_mode,
        changed_fields=changed_fields,
        cost_basis_set=item.cost_basis_override is not None,
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
