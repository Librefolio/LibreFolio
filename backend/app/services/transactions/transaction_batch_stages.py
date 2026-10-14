"""
The stages that open and close ``TransactionService.execute_batch``: parse the raw rows, load and authorize what
they touch, replay the balances, build the response. The stages in between live in ``batch_edits`` (deletes,
splits, updates), ``batch_creates`` (creates, promotes, links) and ``batch_costs`` (WAC, FX, cost basis).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Tuple

from pydantic import ValidationError

from backend.app.db.models import UserRole
from backend.app.schemas.transactions import (
    TXBatchResponse,
    TXCreateItem,
    TXPromoteBatchItem,
    TXSplitBatchItem,
    TXUpdateItem,
    TXValidationCode,
    TXValidationIssue,
)
from backend.app.services.transactions.transaction_batch_context import (
    BalanceValidationError,
    TransactionBatchContext,
)

if TYPE_CHECKING:
    from backend.app.services.transactions.transaction_service import TransactionService


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
