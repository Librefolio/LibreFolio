"""
Batch stages on costs, for ``TransactionService.execute_batch``: the Auto cost (WAC) and FX issues, and the check
that every row that needs a cost basis has one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from backend.app.db.models import Transaction
from backend.app.schemas.transactions import (
    TXValidationCode,
    TXValidationIssue,
)
from backend.app.services.transactions.transaction_batch_context import TransactionBatchContext

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
