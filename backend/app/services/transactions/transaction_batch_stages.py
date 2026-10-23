"""
The stages that open and close ``TransactionService.execute_batch``: parse the raw rows, load and authorize what
they touch, replay the balances, build the response. The stages in between live in ``batch_edits`` (deletes,
splits, updates), ``batch_creates`` (creates, promotes, links) and ``batch_costs`` (WAC, FX, cost basis).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Iterator, Optional, Tuple

from pydantic import ValidationError

from backend.app.db.models import Transaction, UserRole
from backend.app.db.precision import DECIMAL_PLACES_EXCEEDED, INTEGER_DIGITS_EXCEEDED, SIGNIFICANT_DIGITS_EXCEEDED, decimal_limit_issue, integer_digits_issue
from backend.app.schemas.transactions.batch import TXBatchOperation, TXBatchResponse, TXPromoteBatchItem, TXSplitBatchItem, TXValidationCode, TXValidationIssue
from backend.app.schemas.transactions.transactions import TXCreateItem, TXUpdateItem
from backend.app.services.transactions.transaction_batch_context import (
    BalanceValidationError,
    TransactionBatchContext,
    cost_fields,
    rule_values,
)
from backend.app.utils.datetime_utils import EARLIEST_RANGE_START, latest_range_end
from backend.app.utils.pydantic_errors import error_params, loc_to_field

if TYPE_CHECKING:
    from backend.app.services.transactions.transaction_service import TransactionService


def _parse_lenient(
    raw_list: list[dict],
    model_class: type,
    operation: str,
) -> Tuple[list[tuple[int, Any]], list[TXValidationIssue]]:
    """Validate each raw row independently and retain every row-level issue.

    Every error keeps its plain context as ``params`` (``error_params``): a business rule, packed
    (``multipleBusinessRuleErrors``) or alone (W-B72), and a field's constraint, ``{max_length}`` or ``{gt}`` (W-B70)."""
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
                                params=error_params(sub_error),
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
                        params=error_params(error),
                        field=loc_to_field(error.get("loc", ())),
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


# C-97: the fields of a create or an update whose digits are checked, with their labels in the English text.
_DECIMAL_LIMIT_LABELS = {"quantity": "Quantity", "cash.amount": "Cash amount", "cost_basis_override": "Cost basis override"}
# The limit each code names, in the English text.
_DECIMAL_LIMIT_UNITS = {DECIMAL_PLACES_EXCEEDED: "decimal places", SIGNIFICANT_DIGITS_EXCEEDED: "significant digits", INTEGER_DIGITS_EXCEEDED: "digits before the decimal point"}


def _decimal_limit_values(item: Any) -> Iterator[tuple[str, str, Decimal]]:
    """The checked values of ``item``: (issue field, column of ``transactions``, value); a field left out has none.

    An Auto cost basis (``cost_basis_mode`` "auto" or "auto-detail") is not checked: the batch recomputes its amount and
    reads only its currency (``auto_cost.py``), so the preview's average the Form sends back, 100 / 3 in full, is no
    value of the user's. A manual one is.
    """
    cash = item.cash
    cost = item.cost_basis_override if getattr(item, "cost_basis_mode", None) not in ("auto", "auto-detail") else None
    candidates = (("quantity", "quantity", item.quantity), ("cash.amount", "amount", cash.amount if cash is not None else None), ("cost_basis_override", "cost_basis_override", cost.amount if cost is not None else None))
    for field, column, value in candidates:
        if value is not None:
            yield field, column, value


def _promote_cost_amount(item: TXPromoteBatchItem) -> Optional[Decimal]:
    """The amount of the cost basis a promotion resolves (``resolved_fields.cost_basis_override``), or None.

    Typed since H-41: one the currency schema refuses — no number, or an exponent past ±100 (R13-SEC7-3) — never parses,
    and the batch's parse refuses it on ``cost_basis_override.amount``.
    """
    cost = item.resolved_fields.cost_basis_override if item.resolved_fields is not None else None
    return cost.amount if cost is not None else None


def check_decimal_limits(context: TransactionBatchContext) -> bool:
    """Refuse, never round, a quantity, cash amount or manual cost basis over its column's limit (C-97, issue #43).

    A quantity keeps 10 decimal places, an amount 6, a per-unit cost basis 12 (a price: decision D5), any of them
    15 significant digits; and 15 digits before the decimal point, 12 for a cost basis (W-B58, decision N63)
    (``db/precision.decimal_limit_issue``, from the model). Over the limit the row gets one issue per field —
    ``decimalPlacesExceeded``, ``significantDigitsExceeded`` or ``integerDigitsExceeded``, ``params`` ``{"max": N}`` —
    and the batch is not saved; the row stays in the batch, so a linked pair is not broken by it. Checked here, at
    confirmation, and not when a broker import builds its rows (decision D2): the import shows the refusal with the other
    issues of the batch. The cost basis a promotion resolves is a value of the user's too, checked on the same column
    (W-B58: it skipped the check, and the REAL rounded it in silence).

    Returns:
        True when a value is past its column's integer digits, whatever the code its issue got: ``execute_batch`` then
        stops after the access check. The stages after it compute with the values (products, averages, the double a
        REAL stores), and a value of a million digits overflows them: a 500, where the user is owed the issue (W-B58).
    """
    out_of_range = False
    for operation, parsed in (("create", context.parsed_creates), ("update", context.parsed_updates)):
        for index, item in parsed:
            for field, column, value in _decimal_limit_values(item):
                out_of_range |= _check_limit(context, operation, index, item.id if operation == "update" else None, field, column, value)
    for index, item in context.parsed_promotes:
        amount = _promote_cost_amount(item)
        if amount is not None:
            out_of_range |= _check_limit(context, "promote", index, None, "cost_basis_override", "cost_basis_override", amount)
    return out_of_range


def _check_limit(context: TransactionBatchContext, operation: str, index: int, ref_id: Optional[int], field: str, column: str, value: Decimal) -> bool:
    """Add the issue of ``value`` over its column's limit, if any (``check_decimal_limits``); True when it is past the
    column's integer digits."""
    limit = decimal_limit_issue(value, Transaction, column)
    if limit is not None:
        code, maximum = limit
        context.issues.append(
            TXValidationIssue(
                operation=operation,
                index=index,
                ref_id=ref_id,
                error=f"{_DECIMAL_LIMIT_LABELS[field]}: at most {maximum} {_DECIMAL_LIMIT_UNITS[code]}",
                code=code,
                params={"max": maximum},
                field=field,
            )
        )
    return integer_digits_issue(value, Transaction, column) is not None


def check_cost_basis_sign(context: TransactionBatchContext) -> None:
    """Refuse a manual cost basis below 0 (J-60); 0 stays allowed — a gift, the new shares of a split.

    The cost is read where ``check_decimal_limits`` reads it: the manual cost of a create, or of an update that sends
    one (an Auto cost — ``cost_basis_mode`` "auto" or "auto-detail" — is the batch's own average, never the user's),
    and the cost a promotion resolves. An update that leaves the stored cost alone is not refused for it: a row an older
    version stored with a negative cost stays editable until its cost is touched. Below 0 the row gets
    ``costBasisNegative`` on ``cost_basis_override``, no params, and the batch is not saved (``finalize_response``: any
    issue). The batch goes on: a negative cost overflows nothing the later stages compute, so the user gets the row's
    other refusals in the same answer.
    """
    for operation, parsed in (("create", context.parsed_creates), ("update", context.parsed_updates)):
        for index, item in parsed:
            for field, _column, value in _decimal_limit_values(item):
                if field == "cost_basis_override" and value < 0:
                    context.issues.append(_cost_basis_negative(operation, index, item.id if operation == "update" else None))
    for index, item in context.parsed_promotes:
        amount = _promote_cost_amount(item)
        if amount is not None and amount < 0:
            context.issues.append(_cost_basis_negative("promote", index, None))


def _cost_basis_negative(operation: str, index: int, ref_id: Optional[int]) -> TXValidationIssue:
    """The issue of a manual cost basis below 0 (``check_cost_basis_sign``)."""
    return TXValidationIssue(
        operation=operation,
        index=index,
        ref_id=ref_id,
        error="Cost basis override: cannot be negative, 0 or more",
        code=TXValidationCode.COST_BASIS_NEGATIVE.value,
        field="cost_basis_override",
    )


def transaction_date_bounds() -> tuple[date, date]:
    """The first and the last date a transaction may carry (N74, R13-SEC7-3): ``EARLIEST_RANGE_START`` (1900-01-01, the
    floor of every replay and history walk too: MF-SEC8-2) and ``latest_range_end()``, tomorrow by the server's calendar —
    the last date of a price or a rate written by hand too (N83). One day past today is the slack for a user east of the
    server. The interface never offers a future date, and a broker import keeps only settled rows (the plugin guide's
    rule): a later date is a typing error."""
    return EARLIEST_RANGE_START, latest_range_end()


def _promote_date(item: TXPromoteBatchItem) -> Optional[date]:
    """The date a promotion resolves (``resolved_fields.date``), or None; typed since H-41, so one that is no date never
    parses."""
    return item.resolved_fields.date if item.resolved_fields is not None else None


def check_dates(context: TransactionBatchContext) -> bool:
    """Refuse a transaction date outside ``transaction_date_bounds`` (decision N74, R13-SEC7-3).

    Checked on a create, on an update that sets a date, and on the date a promotion resolves; an update that leaves an
    older row's date alone is not refused for it. Out of the bounds the row gets ``dateOutOfRange`` on ``date``,
    ``params`` ``{"min", "max"}`` (ISO dates), and the batch is not saved. A broker import confirms through this batch, so
    its rows are checked here too.

    Returns:
        True when a date is refused: ``execute_batch`` then stops after the access check, as for the integer digits —
        the stages after it replay a broker's days and look rates up at the row's date.
    """
    earliest, latest = transaction_date_bounds()
    candidates = [("create", index, None, item.date) for index, item in context.parsed_creates]
    candidates += [("update", index, item.id, item.date) for index, item in context.parsed_updates]
    candidates += [("promote", index, None, _promote_date(item)) for index, item in context.parsed_promotes]
    refused = False
    for operation, index, ref_id, value in candidates:
        if value is not None and not earliest <= value <= latest:
            refused = True
            context.issues.append(
                TXValidationIssue(
                    operation=operation,
                    index=index,
                    ref_id=ref_id,
                    error=f"Date: between {earliest.isoformat()} and {latest.isoformat()}",
                    code=TXValidationCode.DATE_OUT_OF_RANGE.value,
                    params={"min": earliest.isoformat(), "max": latest.isoformat()},
                    field="date",
                )
            )
    return refused


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
    denied = await _denied_brokers(service, context)
    _append_access_issues(context, denied)

    return bool(denied)


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
        context.stored_cost_fields = {tx.id: cost_fields(tx) for tx in existing_txs}
        context.stored_rule_values = {tx.id: rule_values(tx) for tx in existing_txs}
        context.stored_dates = {tx.id: tx.date for tx in existing_txs}
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


async def _denied_brokers(
    service: TransactionService,
    context: TransactionBatchContext,
) -> set[int]:
    """The touched brokers on which the user lacks EDITOR; none when the batch runs without a user."""
    denied: set[int] = set()
    if context.user_id is None:
        return denied
    for broker_id in sorted(context.touched_brokers):
        role = await service._check_broker_access(
            broker_id,
            context.user_id,
            min_role=UserRole.EDITOR,
        )
        if role is None:
            denied.add(broker_id)
    return denied


def _rows_touching_brokers(
    context: TransactionBatchContext,
) -> Iterator[tuple[TXBatchOperation, int, Optional[int], int]]:
    """Each row of the batch with each broker it touches: ``(operation, index, ref_id, broker_id)``.

    A create touches its own broker (``ref_id`` None). An update, a delete, a split or a promote touches
    the broker of every saved transaction it names, with ``ref_id`` that transaction. A promote naming a
    create by ``link_uuid`` reaches that broker through the create itself.
    """
    for index, item in context.parsed_creates:
        yield "create", index, None, item.broker_id
    saved_refs: list[tuple[TXBatchOperation, int, tuple[Optional[int], ...]]] = [
        *(("update", index, (item.id,)) for index, item in context.parsed_updates),
        *(("delete", index, (transaction_id,)) for index, transaction_id in enumerate(context.deletes)),
        *(("split", index, (item.id_a, item.id_b)) for index, item in context.parsed_splits),
        *(("promote", index, (item.id_a, item.id_b)) for index, item in context.parsed_promotes),
    ]
    for operation, index, transaction_ids in saved_refs:
        for transaction_id in transaction_ids:
            transaction = context.existing_by_id.get(transaction_id) if transaction_id is not None else None
            if transaction is not None:
                yield operation, index, transaction.id, transaction.broker_id


def _append_access_issues(context: TransactionBatchContext, denied: set[int]) -> None:
    """Refuse each row that touches a denied broker, on that row's coordinates.

    One ``accessDenied`` issue per row and denied broker: the editor marks the row its ``operation`` and
    ``index`` point at. A denied broker that no row explains still gets a broker-level issue
    (``index=-1``): a denial is never silent.
    """
    refused: set[tuple[str, int, int]] = set()
    for operation, index, ref_id, broker_id in _rows_touching_brokers(context):
        if broker_id in denied and (operation, index, broker_id) not in refused:
            refused.add((operation, index, broker_id))
            context.issues.append(_access_issue(operation, index, ref_id, broker_id))
    for broker_id in sorted(denied - {broker_id for _, _, broker_id in refused}):
        context.issues.append(_access_issue("create", -1, None, broker_id))


def _access_issue(operation: TXBatchOperation, index: int, ref_id: Optional[int], broker_id: int) -> TXValidationIssue:
    return TXValidationIssue(
        operation=operation,
        index=index,
        ref_id=ref_id,
        error=f"Access denied: EDITOR required for broker {broker_id}",
        code=TXValidationCode.ACCESS_DENIED.value,
        params={"brokerId": broker_id},
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
            warnings=context.warnings,
            results=context.results,
            success_count=success_count,
            wac_results=context.wac_results,
        )
    if not context.commit_requested:
        return TXBatchResponse(
            committed=False,
            issues=[],
            warnings=context.warnings,
            results=context.results,
            success_count=success_count,
            wac_results=context.wac_results,
        )
    return TXBatchResponse(
        committed=True,
        issues=[],
        warnings=context.warnings,
        results=context.results,
        success_count=success_count,
        wac_results=context.wac_results,
    )
