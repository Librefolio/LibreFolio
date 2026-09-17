"""Mutable state shared by the ordered transaction batch stages."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from backend.app.db.models import Transaction
from backend.app.schemas.transactions import (
    TXBatchResultItem,
    TXCreateItem,
    TXPromoteBatchItem,
    TXSplitBatchItem,
    TXUpdateItem,
    TXValidationIssue,
)
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
    earliest_date_by_broker: dict[int, date] = field(default_factory=dict)
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
