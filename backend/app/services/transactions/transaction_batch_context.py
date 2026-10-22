"""Mutable state shared by the ordered transaction batch stages."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from backend.app.db.models import Transaction
from backend.app.schemas.transactions.batch import TXBatchResultItem, TXPromoteBatchItem, TXSplitBatchItem, TXValidationIssue
from backend.app.schemas.transactions.transactions import TXCreateItem, TXUpdateItem
from backend.app.schemas.wac import WACPreviewResultItem


class BalanceValidationError(Exception):
    """Raised when a broker balance replay fails."""

    def __init__(
        self,
        broker_id: int,
        date: date,
        currency_or_asset: str,
        balance: Decimal,
        message: str,
        code: str = "",
        params: dict | None = None,
        batch_index: int = -1,
        batch_operation: str = "create",
    ):
        self.broker_id = broker_id
        self.date = date
        self.currency_or_asset = currency_or_asset
        self.balance = balance
        self.code = code
        self.params = params or {}
        self.batch_index = batch_index
        self.batch_operation = batch_operation
        super().__init__(message)


@dataclass
class TransactionBatchContext:
    """Inputs and cross-stage state for one ``execute_batch`` invocation."""

    creates_raw: list[dict]
    updates_raw: list[dict]
    deletes: list[int]
    splits_raw: list[dict]
    promotes_raw: list[dict]
    user_id: int | None
    commit_requested: bool

    issues: list[TXValidationIssue] = field(default_factory=list)
    results: list[TXBatchResultItem] = field(default_factory=list)
    parsed_creates: list[tuple[int, TXCreateItem]] = field(default_factory=list)
    parsed_updates: list[tuple[int, TXUpdateItem]] = field(default_factory=list)
    parsed_splits: list[tuple[int, TXSplitBatchItem]] = field(default_factory=list)
    parsed_promotes: list[tuple[int, TXPromoteBatchItem]] = field(default_factory=list)
    touched_brokers: set[int] = field(default_factory=set)
    existing_by_id: dict[int, Transaction] = field(default_factory=dict)
    # What decided the cost basis of each preloaded row before the batch touched it (``cost_fields``).
    stored_cost_fields: dict[int, tuple] = field(default_factory=dict)
    # The type, quantity and cash of each preloaded row before the batch touched it (``rule_values``, decision P6).
    stored_rule_values: dict[int, tuple] = field(default_factory=dict)
    earliest_date_by_broker: dict[int, date] = field(default_factory=dict)
    # Every row ``apply_creates`` flushed, by create index: the row of a create, read by the Auto cost (W-B67).
    created_by_index: dict[int, Transaction] = field(default_factory=dict)
    link_uuid_map: dict[str, list[tuple[int, Transaction]]] = field(default_factory=lambda: defaultdict(list))
    consumed_link_uuids: set[str] = field(default_factory=set)
    wac_results: list[WACPreviewResultItem] | None = None

    @classmethod
    def from_inputs(
        cls,
        *,
        creates_raw: list[dict],
        updates_raw: list[dict],
        deletes: list[int],
        splits_raw: list[dict] | None,
        promotes_raw: list[dict] | None,
        user_id: int | None,
        commit_requested: bool,
    ) -> TransactionBatchContext:
        """Normalize optional operation lists at the batch boundary."""
        return cls(
            creates_raw=creates_raw,
            updates_raw=updates_raw,
            deletes=deletes,
            splits_raw=splits_raw or [],
            promotes_raw=promotes_raw or [],
            user_id=user_id,
            commit_requested=commit_requested,
        )


def cost_fields(transaction: Transaction) -> tuple:
    """What decides whether a row needs a cost basis, and whether it has one: its type, quantity, cost basis and asset
    event link — an ADJUSTMENT linked to a SPLIT takes its cost from the split, so unlinking it is a cost change."""
    return (transaction.type, transaction.quantity, transaction.cost_basis_override, transaction.cost_basis_currency, transaction.asset_event_id)


def rule_values(transaction: Transaction) -> tuple:
    """What the four points of decision P6 read on a row: its type, its quantity, and its cash (amount and currency)."""
    return (transaction.type, transaction.quantity, transaction.amount, transaction.currency)


def changed_rule_fields(stored: tuple | None, transaction: Transaction) -> frozenset[str]:
    """The fields of decision P6 an update changed, ``"type"``, ``"quantity"`` and ``"cash"``, for
    ``validate_transaction_business_rules``: compared by value with the row as stored before the batch
    (``rule_values``), so a value sent back as stored is no change. A row without stored values (every updated row is
    preloaded) counts as unchanged, as before P6."""
    if stored is None:
        return frozenset()
    tx_type, quantity, amount, currency = rule_values(transaction)
    changed: set[str] = set()
    if tx_type != stored[0]:
        changed.add("type")
    if quantity != stored[1]:
        changed.add("quantity")
    if (amount, currency) != stored[2:]:
        changed.add("cash")
    return frozenset(changed)
