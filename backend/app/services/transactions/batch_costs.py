"""
Batch stages on costs, for ``TransactionService.execute_batch``: the Auto cost (WAC) and FX issues, and the check
that every row that needs a cost basis has one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from backend.app.db.models import Transaction
from backend.app.schemas.transactions.batch import TXValidationCode, TXValidationIssue
from backend.app.services.transactions.auto_cost import UnreadablePoolError
from backend.app.services.transactions.transaction_batch_context import TransactionBatchContext, cost_fields

if TYPE_CHECKING:
    from backend.app.services.transactions.transaction_service import TransactionService


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
        # W-B69: an Auto row whose pool holds rows that cannot be read is refused, never costed without them. N88 (J-57):
        # so is one whose average of 0 comes from a pool holding no units, or none at a known cost — never a free purchase.
        unreadable: list[tuple[str, int, int]] = []
        nothing_to_average: list[tuple[str, int, str]] = []
        context.wac_results = await service._compute_wac_for_auto_items(
            context.parsed_creates,
            context.parsed_updates,
            context.created_by_index,
            unreadable=unreadable,
            nothing_to_average=nothing_to_average,
        )
        for operation, index, count in unreadable:
            context.issues.append(_auto_cost_unreadable(operation, index, None, count))
        for operation, index, code in nothing_to_average:
            context.issues.append(_auto_cost_nothing_to_average(operation, index, code))
        await _cost_split_handovers(service, context)

    if context.wac_results:
        for wac_result in context.wac_results:
            if wac_result.wac is None and wac_result.wac_missing_pairs:
                operation = wac_result.operation or "create"
                index = wac_result.index if wac_result.index is not None else 0
                context.issues.append(_wac_fx_unavailable(operation, index, None, wac_result.wac_missing_pairs))


async def _cost_split_handovers(service: TransactionService, context: TransactionBatchContext) -> None:
    """Decision 47: the giving leg of a split TRANSFER pair leaves at its own broker's Auto cost, unless an update of the
    same batch gives it one. Without it the split is refused like an Auto row, rather than leave an ADJUSTMENT-out without
    a cost: a missing conversion (``wacFxUnavailable``), or a pool holding rows that cannot be read (``autoCostUnreadable``,
    W-B69)."""
    explicit = {item.id for _, item in context.parsed_updates if item.cost_basis_override is not None}
    for split_index, row in context.handover_rows:
        if row.id in explicit:
            continue  # an update of the same batch gave this leg its cost: it stays
        try:
            handover = await service._handover_cost(row)
        except UnreadablePoolError as exc:
            context.issues.append(_auto_cost_unreadable("split", split_index, row.id, exc.count))
            continue
        if handover.wac:
            service._write_auto_cost(row, handover)
        elif handover.wac_missing_pairs:
            context.issues.append(_wac_fx_unavailable("split", split_index, row.id, handover.wac_missing_pairs))


def _auto_cost_nothing_to_average(operation: Any, index: int, code: str) -> TXValidationIssue:
    """The issue of an Auto cost with nothing to average (N88, J-57): ``code`` — ``AUTO_COST_EMPTY_POOL`` or
    ``AUTO_COST_UNKNOWN_POOL`` — on ``cost_basis_override``, no ``params`` and no id: the pool can be another user's
    broker (the receiving side of a TRANSFER averages its partner's)."""
    reason = "holds no units on that date" if code == TXValidationCode.AUTO_COST_EMPTY_POOL.value else "holds no units of known cost on that date"
    return TXValidationIssue(
        operation=operation,
        index=index,
        ref_id=None,
        error=f"Auto cost: the pool it averages {reason}",
        code=code,
        field="cost_basis_override",
    )


def _auto_cost_unreadable(operation: Any, index: int, ref_id: int | None, count: int) -> TXValidationIssue:
    """The issue of an Auto cost whose pool holds rows that cannot be read (W-B69): ``AUTO_COST_UNREADABLE`` on
    ``cost_basis_override``, ``params`` ``{"count": N}``. No id of those rows: the pool can be another user's broker."""
    return TXValidationIssue(
        operation=operation,
        index=index,
        ref_id=ref_id,
        error=f"Auto cost: {count} transaction(s) of the pool it averages cannot be read",
        code=TXValidationCode.AUTO_COST_UNREADABLE.value,
        params={"count": count},
        field="cost_basis_override",
    )


def _wac_fx_unavailable(operation: Any, index: int, ref_id: int | None, missing_pairs: list) -> TXValidationIssue:
    """The issue of an Auto cost that needs a missing conversion: ``WAC_FX_UNAVAILABLE`` on ``cost_basis_override``."""
    pair_strings = [missing_pair.pair for missing_pair in missing_pairs]
    return TXValidationIssue(
        operation=operation,
        index=index,
        ref_id=ref_id,
        error=f"WAC calculation failed: missing FX pairs {', '.join(pair_strings)}",
        code=TXValidationCode.WAC_FX_UNAVAILABLE.value,
        params={
            "pairs": pair_strings,
            "pair_details": [
                {
                    "pair": missing_pair.pair,
                    "dates": [missing_date.isoformat() for missing_date in missing_pair.dates],
                }
                for missing_pair in missing_pairs
            ],
        },
        field="cost_basis_override",
    )


async def validate_cost_basis(
    service: TransactionService,
    context: TransactionBatchContext,
) -> None:
    """Verify required cost basis after auto-WAC and promote handling.

    A promote turns an incoming ADJUSTMENT into the receiving side of a TRANSFER, which
    needs a cost basis like any other: new promoted rows are checked as creates, saved
    ones on the promote that paired them.
    """
    await service.session.flush()

    auto_create_indices = _auto_mode_indices(context.parsed_creates)
    auto_update_indices = _auto_mode_indices(context.parsed_updates)

    checked_create_indices = _check_linked_create_cost_basis(
        service,
        context,
        auto_create_indices,
    )
    await _check_result_create_cost_basis(
        service,
        context,
        auto_create_indices,
        checked_create_indices,
    )
    await _check_update_cost_basis(
        service,
        context,
        auto_update_indices,
    )
    await _check_promoted_saved_cost_basis(service, context)


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
    checked_create_indices: set[int],
) -> None:
    """Check standalone and promoted creates represented by successful result rows."""
    for result in context.results:
        if result.operation != "create" or result.status != "success" or result.index in checked_create_indices:
            continue
        if result.index in auto_create_indices:
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
    """Check parsed updates not handled by auto WAC that touch what the cost basis depends on.

    An update is checked when it changes the row's type, quantity (its sign included), cost basis or asset event link,
    compared with the row as stored before the batch, or when it names a cost basis mode. Editing only the notes, tags or
    description of an older row saved without a cost basis stays allowed: nothing is repaired behind the user's back.
    """
    for original_index, item in context.parsed_updates:
        if original_index in auto_update_indices:
            continue
        transaction = await service.session.get(Transaction, item.id)
        if transaction is None or not service._requires_cost_basis(transaction) or transaction.cost_basis_override is not None:
            continue
        touches_cost = getattr(item, "cost_basis_mode", None) is not None or cost_fields(transaction) != context.stored_cost_fields.get(item.id)
        if touches_cost:
            _append_cost_basis_issue(
                context,
                operation="update",
                index=original_index,
                ref_id=item.id,
                transaction=transaction,
            )


async def _check_promoted_saved_cost_basis(
    service: TransactionService,
    context: TransactionBatchContext,
) -> None:
    """Check saved rows that a promote made the receiving side of a pair.

    New rows of a promote are creates, and updated rows are updates: both are checked there.
    """
    updated_ids = {item.id for _original_index, item in context.parsed_updates}
    for result in context.results:
        if result.operation != "promote" or result.status != "success":
            continue
        for transaction_id in result.ids or []:
            if transaction_id not in context.existing_by_id or transaction_id in updated_ids:
                continue
            transaction = await service.session.get(Transaction, transaction_id)
            if transaction and service._requires_cost_basis(transaction) and transaction.cost_basis_override is None:
                _append_cost_basis_issue(
                    context,
                    operation="promote",
                    index=result.index,
                    ref_id=transaction_id,
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
