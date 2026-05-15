"""
Transaction Service for LibreFolio.

Centralizes all transaction business logic:
- CRUD operations with validation
- Link resolution for paired transactions (TRANSFER, FX_CONVERSION)
- Balance validation (cash and asset positions)

Atomic multi-broker semantics (Part 3):
- All bulk endpoints accept items spanning multiple brokers in a single batch.
- Access check (EDITOR) is enforced once per distinct `broker_id` touched.
- Any exception, access denial, or balance violation → full session rollback,
  `rolled_back=True`, per-item `status` in {failed, simulated, not_attempted}.
- The router never commits when `rolled_back=True`.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetEvent, AssetEventType, AssetType, Broker, BrokerUserAccess, Transaction, TransactionType, UserRole
from backend.app.schemas.common import Currency
from backend.app.services.fx import convert_bulk
from backend.app.schemas.transactions import (
    EVENT_COMPATIBLE_TYPES,
    TX_TYPE_METADATA,
    PairFieldConstraint,
    TXBatchResponse,
    TXBatchResultItem,
    TXCreateItem,
    TXEventSuggestCandidate,
    TXEventSuggestRequestItem,
    TXEventSuggestResultItem,
    TXPromoteBatchItem,
    TXPromoteSuggestCandidate,
    TXPromoteSuggestResponse,
    TXQueryParams,
    TXReadItem,
    TXSplitBatchItem,
    TXTransferPromoteRequest,
    TXTransferPromoteResponse,
    TXUpdateItem,
    TXValidationCode,
    TXValidationIssue,
    WACConversionInfo,
    WACResult,
    get_swap_group,
    tags_to_csv,
)
from backend.app.utils.datetime_utils import parse_ISO_date, utcnow


async def compute_weighted_avg_cost(
    session: AsyncSession,
    broker_id: int,
    asset_id: int,
    as_of_date: date_type,
    asset_currency: str,
) -> WACResult:
    """Compute weighted average cost of an asset at a broker up to a given date.

    FX-aware: converts BUY/TRANSFER costs to a common target currency using
    convert_bulk(). Returns WACResult with conversion details and missing pairs.

    Target currency selection:
    1. Most frequent currency among qualifying TXs.
    2. On tie: asset_currency if it's among the tied currencies.
    3. Otherwise: first alphabetically.

    Edge cases:
    - No qualifying TXs or total_qty == 0 without FX errors →
      WACResult(wac=Currency(code=target, amount="0"))
    - Any FX conversion fails → WACResult(wac=None, missing_pairs=[...])
    """
    # 1. Query qualifying transactions: BUY + incoming TRANSFER (qty > 0)
    stmt = select(Transaction).where(
        Transaction.broker_id == broker_id,
        Transaction.asset_id == asset_id,
        Transaction.date <= as_of_date,
        or_(
            Transaction.type == TransactionType.BUY,
            and_(
                Transaction.type == TransactionType.TRANSFER,
                Transaction.quantity > 0,
            ),
        ),
    )
    rows = (await session.execute(stmt)).scalars().all()

    if not rows:
        return WACResult(wac=Currency(code=asset_currency, amount=Decimal("0")))

    # 2. Build per-row (qty, cost, currency, tx_id) tuples
    row_data: list[tuple[Decimal, Decimal, str, int, date_type]] = []
    for row in rows:
        if row.type == TransactionType.BUY:
            qty = abs(row.quantity) if row.quantity else Decimal("0")
            if qty == 0:
                continue
            unit_price = abs(row.amount) / qty if row.amount else Decimal("0")
            ccy = row.currency or asset_currency
            row_data.append((qty, qty * unit_price, ccy, row.id, row.date))
        else:
            # TRANSFER receiver
            qty = row.quantity if row.quantity else Decimal("0")
            if qty <= 0:
                continue
            if row.cost_basis_override is not None and row.cost_basis_currency is not None:
                # Has frozen cost basis
                cost = qty * row.cost_basis_override
                ccy = row.cost_basis_currency
            elif row.cost_basis_override is not None:
                # Legacy: override without currency — use asset_currency
                cost = qty * row.cost_basis_override
                ccy = asset_currency
            else:
                # No cost basis override — skip (cannot contribute to WAC)
                continue
            row_data.append((qty, cost, ccy, row.id, row.date))

    if not row_data:
        return WACResult(wac=Currency(code=asset_currency, amount=Decimal("0")))

    # 3. Determine target_currency
    ccy_counter = Counter(ccy for _, _, ccy, _, _ in row_data)
    max_count = max(ccy_counter.values())
    top_ccys = sorted(c for c, n in ccy_counter.items() if n == max_count)
    if len(top_ccys) == 1:
        target_currency = top_ccys[0]
    elif asset_currency in top_ccys:
        target_currency = asset_currency
    else:
        target_currency = top_ccys[0]  # first alphabetically

    # 4. Build conversion list for non-target currencies
    fx_needed: list[tuple[int, Currency, str, date_type, int]] = []  # (row_idx, amount_ccy, to_ccy, date, tx_id)
    for i, (qty, cost, ccy, tx_id, tx_date) in enumerate(row_data):
        if ccy != target_currency:
            fx_needed.append((i, Currency(code=ccy, amount=cost), target_currency, tx_date, tx_id))

    conversions_info: list[WACConversionInfo] = []
    missing_pairs: list[str] = []

    # Convert all non-target costs in one batch
    if fx_needed:
        bulk_input = [(amt_ccy, to_ccy, dt) for _, amt_ccy, to_ccy, dt, _ in fx_needed]
        fx_results, fx_errors = await convert_bulk(session, bulk_input, raise_on_error=False)

        for j, (row_idx, amt_ccy, to_ccy, dt, tx_id) in enumerate(fx_needed):
            result = fx_results[j] if j < len(fx_results) else None
            if result is None:
                # FX conversion failed
                pair_key = f"{amt_ccy.code}/{to_ccy}"
                if pair_key not in missing_pairs:
                    missing_pairs.append(pair_key)
            else:
                converted, rate_date, _bf = result
                stale_days = (dt - rate_date).days if rate_date < dt else 0
                # Figure out the rate: converted.amount / amt_ccy.amount
                rate = converted.amount / amt_ccy.amount if amt_ccy.amount != 0 else Decimal("0")
                conversions_info.append(WACConversionInfo(
                    tx_id=tx_id,
                    from_currency=amt_ccy.code,
                    to_currency=target_currency,
                    rate=rate,
                    rate_date=rate_date,
                    stale_days=stale_days,
                ))
                # Replace cost with converted amount
                qty_orig = row_data[row_idx][0]
                row_data[row_idx] = (qty_orig, converted.amount, target_currency, tx_id, dt)

    # 5. If any conversion failed → wac=None
    if missing_pairs:
        return WACResult(wac=None, conversions=conversions_info, missing_pairs=missing_pairs)

    # 6. Sum up
    total_qty = sum(rd[0] for rd in row_data)
    total_cost = sum(rd[1] for rd in row_data)

    if total_qty == 0:
        return WACResult(wac=Currency(code=target_currency, amount=Decimal("0")), conversions=conversions_info)

    wac_amount = total_cost / total_qty
    return WACResult(wac=Currency(code=target_currency, amount=wac_amount), conversions=conversions_info)


class BalanceValidationError(Exception):
    """Raised when a balance validation fails."""

    def __init__(
        self,
        broker_id: int,
        date: date_type,
        currency_or_asset: str,
        balance: Decimal,
        message: str,
        code: str = "",
        params: dict | None = None,
    ):
        self.broker_id = broker_id
        self.date = date
        self.currency_or_asset = currency_or_asset
        self.balance = balance
        self.code = code
        self.params = params or {}
        super().__init__(message)


class LinkedTransactionError(Exception):
    """Raised when linked transaction operations fail."""

    pass


from dataclasses import dataclass


@dataclass(frozen=True)
class _PromoteCandidate:
    """Lightweight duck-type-compatible object for _check_promote_constraints.
    Used by promote-suggest to validate constraints without a full Transaction."""

    broker_id: int
    asset_id: Optional[int]
    currency: Optional[str]
    amount: Optional[Decimal]
    quantity: Optional[Decimal]


def _loc_to_field(loc: tuple | list) -> Optional[str]:
    """Convert Pydantic loc tuple to a dotted field path string."""
    parts = [str(p) for p in loc if not isinstance(p, int)]
    return ".".join(parts) if parts else None


def _parse_lenient(
    raw_list: List[dict],
    model_class: type,
    operation: str,
) -> Tuple[List[Tuple[int, Any]], List[TXValidationIssue]]:
    """Per-row model_validate with error collection.

    Returns (parsed_items, issues) where parsed_items is a list of (index, model)
    tuples for successfully-parsed rows, and issues contains all schema/business
    errors from rows that failed validation.
    """
    parsed: List[Tuple[int, Any]] = []
    issues: List[TXValidationIssue] = []
    for idx, raw in enumerate(raw_list):
        try:
            parsed.append((idx, model_class.model_validate(raw)))
        except ValidationError as e:
            for err in e.errors():
                # Handle packed multi-error from model_validator
                if err.get("type") == "multipleBusinessRuleErrors":
                    ctx = err.get("ctx", {})
                    sub_errors = ctx.get("errors", [])
                    for sub in sub_errors:
                        # sub.ctx is always our own PydanticCustomError context
                        # (e.g. {"type": "BUY"}) — safe to pass as-is.
                        issues.append(
                            TXValidationIssue(
                                operation=operation,
                                index=idx,
                                error=sub.get("msg", ""),
                                code=sub.get("code"),
                                params=sub.get("ctx") or None,
                                field=None,
                            )
                        )
                    continue
                # Standard Pydantic errors: ctx can contain non-serializable
                # objects (e.g. {'error': ValueError('...')}), so we don't
                # forward it as params.  The error message already carries the
                # human-readable description; `code` = Pydantic error type
                # (e.g. "value_error", "missing"); `field` pinpoints the loc.
                issues.append(
                    TXValidationIssue(
                        operation=operation,
                        index=idx,
                        error=err.get("msg", str(err)),
                        code=err.get("type"),
                        params=None,
                        field=_loc_to_field(err.get("loc", ())),
                    )
                )
    return parsed, issues


class TransactionService:
    """
    Service for managing transactions.

    All methods are async and expect an AsyncSession.
    The caller is responsible for commit when `rolled_back=False`.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # ACCESS CONTROL
    # =========================================================================

    async def _check_broker_access(self, broker_id: int, user_id: int, min_role: UserRole = UserRole.VIEWER) -> Optional[UserRole]:
        """Return the user's role (≥ min_role) or None if access is denied."""
        stmt = select(BrokerUserAccess).where(and_(BrokerUserAccess.broker_id == broker_id, BrokerUserAccess.user_id == user_id))
        result = await self.session.execute(stmt)
        access = result.scalar_one_or_none()

        if not access:
            return None

        role_order = {UserRole.OWNER: 3, UserRole.EDITOR: 2, UserRole.VIEWER: 1}
        if role_order.get(access.role, 0) >= role_order.get(min_role, 0):
            return access.role
        return None

    async def _check_broker_access_or_raise(self, broker_id: int, user_id: int, min_role: UserRole = UserRole.EDITOR) -> UserRole:
        """Enforce broker access at batch boundary; raise HTTPException(403) on miss."""
        role = await self._check_broker_access(broker_id, user_id, min_role=min_role)
        if role is None:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: {min_role.value} role required for broker {broker_id}",
            )
        return role

    async def _get_accessible_broker_ids(self, user_id: int) -> Set[int]:
        """Return the set of broker IDs the user can at least VIEW."""
        stmt = select(BrokerUserAccess.broker_id).where(BrokerUserAccess.user_id == user_id)
        result = await self.session.execute(stmt)
        return {row[0] for row in result.all()}

    async def _enforce_batch_access(self, broker_ids: Set[int], user_id: Optional[int], min_role: UserRole = UserRole.EDITOR) -> None:
        """One access check per distinct broker_id touched by the batch."""
        if user_id is None:
            return
        for broker_id in broker_ids:
            await self._check_broker_access_or_raise(broker_id, user_id, min_role=min_role)

    async def _check_paired_access(self, tx: "Transaction", user_id: int) -> Optional[str]:
        """Check if user has EDITOR access on both sides of a paired tx.

        Returns None if OK (standalone or full access), or an error string
        like ``"paired_access_denied:<broker_id>"`` when the partner's broker
        is not editable by the user.
        """
        if tx.related_transaction_id is None:
            return None
        partner = await self.session.get(Transaction, tx.related_transaction_id)
        if partner is None:
            return None  # orphan — nothing to restrict
        role = await self._check_broker_access(partner.broker_id, user_id, min_role=UserRole.EDITOR)
        if role is None:
            return f"paired_access_denied:{partner.broker_id}"
        return None

    # =========================================================================
    # CROSS-RECORD VALIDATION HELPERS
    # =========================================================================

    async def _validate_asset_event_link(self, asset_event_id: int, expected_asset_id: int) -> None:
        """Verify the referenced AssetEvent exists and belongs to expected_asset_id."""
        event = await self.session.get(AssetEvent, asset_event_id)
        if event is None:
            raise ValueError(f"asset_event_id={asset_event_id} not found")
        if event.asset_id != expected_asset_id:
            raise ValueError(f"asset_event_id={asset_event_id} belongs to asset {event.asset_id}, not {expected_asset_id}")

    @staticmethod
    def _validate_linked_pair(a: Transaction, b: Transaction) -> Optional[tuple[str, str, dict]]:
        """
        Validate semantic coherence of a linked pair (Block H.1).

        Rules:
        - Both items must share the same `type` (no mixing e.g. TRANSFER + SELL).
        - TRANSFER requires distinct brokers (same-broker TRANSFER is a no-op).
        - FX_CONVERSION intra-broker is allowed (multi-currency account use case).
        - CASH_TRANSFER requires distinct brokers (same-broker is a no-op).

        Returns None when the pair is valid, otherwise a tuple of
        (error_message, code, params).
        """
        if a.type != b.type:
            return (
                f"linked pair must share the same type (got {a.type.value} + {b.type.value})",
                "pairTypeMismatch",
                {"typeA": a.type.value, "typeB": b.type.value},
            )
        if a.type == TransactionType.TRANSFER and a.broker_id == b.broker_id:
            return (
                f"TRANSFER requires distinct brokers (both on broker {a.broker_id})",
                "pairSameBroker",
                {"brokerId": a.broker_id},
            )
        if a.type == TransactionType.CASH_TRANSFER and a.broker_id == b.broker_id:
            return (
                f"CASH_TRANSFER requires distinct brokers (both on broker {a.broker_id})",
                "pairSameBroker",
                {"brokerId": a.broker_id},
            )
        return None

    @staticmethod
    def _validate_pair_description_tags(a: Transaction, b: Transaction) -> Optional[tuple[str, str, dict]]:
        """Validate that a linked pair has identical description and tags.

        Returns None when consistent, otherwise (error_message, code, params).
        """
        # Normalize None to "" for comparison
        desc_a = a.description or ""
        desc_b = b.description or ""
        if desc_a != desc_b:
            return (
                "Linked pair must have identical description",
                "pairDescriptionMismatch",
                {"descA": desc_a[:50], "descB": desc_b[:50]},
            )
        # Tags are stored as CSV strings; normalize None to ""
        tags_a = a.tags or ""
        tags_b = b.tags or ""
        if tags_a != tags_b:
            return (
                "Linked pair must have identical tags",
                "pairTagsMismatch",
                {"tagsA": tags_a, "tagsB": tags_b},
            )
        return None

    # =========================================================================
    # READ OPERATIONS
    # =========================================================================

    async def query(self, params: TXQueryParams, user_id: Optional[int] = None) -> List[TXReadItem]:
        """
        Query transactions with filters.

        When `user_id` is provided, the result is filtered to brokers the user
        can at least VIEW. When `params.ids` is set, results are returned in
        the exact input order (other filters besides access are ignored).
        """
        accessible_broker_ids: Optional[Set[int]] = None
        if user_id is not None:
            accessible_broker_ids = await self._get_accessible_broker_ids(user_id)
            if not accessible_broker_ids:
                return []

        if params.ids:
            stmt = select(Transaction).where(Transaction.id.in_(params.ids))
            if accessible_broker_ids is not None:
                stmt = stmt.where(Transaction.broker_id.in_(accessible_broker_ids))
            result = await self.session.execute(stmt)
            by_id = {tx.id: tx for tx in result.scalars().all()}
            ordered = [by_id[i] for i in params.ids if i in by_id]
            items = [TXReadItem.from_db_model(tx) for tx in ordered]
            return await self._enrich_partner_broker_ids(items)

        stmt = select(Transaction)

        if accessible_broker_ids is not None:
            stmt = stmt.where(Transaction.broker_id.in_(accessible_broker_ids))

        if params.broker_id:
            stmt = stmt.where(Transaction.broker_id == params.broker_id)
        if params.asset_id:
            stmt = stmt.where(Transaction.asset_id == params.asset_id)
        if params.types:
            stmt = stmt.where(Transaction.type.in_(params.types))
        if params.date_range:
            stmt = stmt.where(Transaction.date >= params.date_range.start)
            if params.date_range.end:
                stmt = stmt.where(Transaction.date <= params.date_range.end)
        if params.currency:
            stmt = stmt.where(Transaction.currency == params.currency)
        if params.tags:
            tag_conditions = [Transaction.tags.contains(tag) for tag in params.tags]
            stmt = stmt.where(or_(*tag_conditions))

        # H.3 — transfer-match helpers.
        if params.amount_abs_min is not None:
            stmt = stmt.where(func.abs(Transaction.amount) >= params.amount_abs_min)
        if params.amount_abs_max is not None:
            stmt = stmt.where(func.abs(Transaction.amount) <= params.amount_abs_max)
        if params.only_unlinked:
            stmt = stmt.where(Transaction.related_transaction_id.is_(None))
        if params.exclude_ids:
            stmt = stmt.where(Transaction.id.notin_(params.exclude_ids))

        stmt = stmt.order_by(Transaction.date.desc(), Transaction.id.desc())
        stmt = stmt.offset(params.offset).limit(params.limit)

        result = await self.session.execute(stmt)
        items = [TXReadItem.from_db_model(tx) for tx in result.scalars().all()]
        return await self._enrich_partner_broker_ids(items)

    async def _enrich_partner_broker_ids(self, items: List[TXReadItem]) -> List[TXReadItem]:
        """Batch-populate partner_broker_id for all items with related_transaction_id."""
        partner_ids = {item.related_transaction_id for item in items if item.related_transaction_id}
        if not partner_ids:
            return items
        stmt = select(Transaction.id, Transaction.broker_id).where(Transaction.id.in_(partner_ids))
        result = await self.session.execute(stmt)
        partner_map = {row.id: row.broker_id for row in result}
        for item in items:
            if item.related_transaction_id:
                item.partner_broker_id = partner_map.get(item.related_transaction_id)
        return items

    async def get_by_ids(self, tx_ids: List[int]) -> List[Transaction]:
        """Get multiple transactions by IDs (DB models, no access check)."""
        if not tx_ids:
            return []
        stmt = select(Transaction).where(Transaction.id.in_(tx_ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # =========================================================================
    # DELETE OPERATIONS (internal — delete_by_broker only)
    # =========================================================================

    async def delete_by_broker(self, broker_id: int) -> int:
        """
        Delete all transactions for a broker (internal helper for BrokerService).

        Skips access control and balance validation — caller is expected to have
        already verified OWNER permissions on the broker.
        """
        stmt = select(Transaction).where(Transaction.broker_id == broker_id)
        result = await self.session.execute(stmt)
        txs = result.scalars().all()

        count = 0
        for tx in txs:
            await self.session.delete(tx)
            count += 1

        return count

    # =========================================================================
    # BALANCE VALIDATION
    # =========================================================================

    async def _validate_broker_balances(self, broker_id: int, from_date: Optional[date_type] = None) -> None:
        """Validate cash and asset balances for a broker from a given date."""
        broker = await self.session.get(Broker, broker_id)
        if not broker:
            return

        if broker.allow_cash_overdraft and broker.allow_asset_shorting:
            return

        if from_date is None:
            cash_balances: Dict[str, Decimal] = {}
            asset_balances: Dict[int, Decimal] = {}
            stmt = select(Transaction).where(Transaction.broker_id == broker_id).order_by(Transaction.date, Transaction.id)
        else:
            cash_balances, asset_balances = await self._get_balances_before_date(broker_id, from_date)
            stmt = select(Transaction).where(Transaction.broker_id == broker_id).where(Transaction.date >= from_date).order_by(Transaction.date, Transaction.id)

        result = await self.session.execute(stmt)
        txs = list(result.scalars().all())

        if not txs:
            return

        txs_by_date: Dict[date_type, List[Transaction]] = defaultdict(list)
        for tx in txs:
            txs_by_date[tx.date].append(tx)

        current_date = min(txs_by_date.keys()) if from_date is None else from_date
        end_date = max(txs_by_date.keys())

        while current_date <= end_date:
            for tx in txs_by_date.get(current_date, []):
                if tx.amount != Decimal("0") and tx.currency:
                    cash_balances[tx.currency] = cash_balances.get(tx.currency, Decimal("0")) + tx.amount
                if tx.quantity != Decimal("0") and tx.asset_id:
                    asset_balances[tx.asset_id] = asset_balances.get(tx.asset_id, Decimal("0")) + tx.quantity

            if not broker.allow_cash_overdraft:
                for currency, balance in cash_balances.items():
                    if balance < Decimal("0"):
                        raise BalanceValidationError(
                            broker_id=broker_id,
                            date=current_date,
                            currency_or_asset=currency,
                            balance=balance,
                            message=f"Cash balance for {currency} goes negative ({balance}) on {current_date} for broker {broker_id}",
                            code=TXValidationCode.BALANCE_CASH_NEGATIVE.value,
                            params={"brokerId": broker_id, "currency": currency, "balance": str(balance), "date": str(current_date)},
                        )

            if not broker.allow_asset_shorting:
                for asset_id, balance in asset_balances.items():
                    if balance < Decimal("0"):
                        raise BalanceValidationError(
                            broker_id=broker_id,
                            date=current_date,
                            currency_or_asset=f"asset:{asset_id}",
                            balance=balance,
                            message=f"Asset {asset_id} quantity goes negative ({balance}) on {current_date} for broker {broker_id}",
                            code=TXValidationCode.BALANCE_ASSET_NEGATIVE.value,
                            params={"brokerId": broker_id, "assetId": asset_id, "balance": str(balance), "date": str(current_date)},
                        )

            current_date += timedelta(days=1)

    async def _get_balances_before_date(self, broker_id: int, before_date: date_type) -> Tuple[Dict[str, Decimal], Dict[int, Decimal]]:
        """Get cash and asset balances at end of day before the given date."""
        cash_stmt = select(Transaction.currency, func.sum(Transaction.amount)).where(Transaction.broker_id == broker_id).where(Transaction.date < before_date).where(Transaction.currency.isnot(None)).group_by(Transaction.currency)
        result = await self.session.execute(cash_stmt)
        cash_balances: Dict[str, Decimal] = {currency: amount for currency, amount in result.all() if currency}

        asset_stmt = select(Transaction.asset_id, func.sum(Transaction.quantity)).where(Transaction.broker_id == broker_id).where(Transaction.date < before_date).where(Transaction.asset_id.isnot(None)).group_by(Transaction.asset_id)
        result = await self.session.execute(asset_stmt)
        asset_balances: Dict[int, Decimal] = {asset_id: qty for asset_id, qty in result.all() if asset_id}

        return cash_balances, asset_balances

    # =========================================================================
    # BALANCE QUERIES (for BRSummary)
    # =========================================================================

    async def get_cash_balances(self, broker_id: int) -> Dict[str, Decimal]:
        """Get current cash balances for a broker (currency → balance)."""
        stmt = select(Transaction.currency, func.sum(Transaction.amount)).where(Transaction.broker_id == broker_id).where(Transaction.currency.isnot(None)).group_by(Transaction.currency)
        result = await self.session.execute(stmt)
        return {currency: amount for currency, amount in result.all() if currency}

    async def get_asset_holdings(self, broker_id: int) -> Dict[int, Decimal]:
        """Get current asset holdings for a broker (asset_id → quantity)."""
        stmt = select(Transaction.asset_id, func.sum(Transaction.quantity)).where(Transaction.broker_id == broker_id).where(Transaction.asset_id.isnot(None)).group_by(Transaction.asset_id)
        result = await self.session.execute(stmt)
        return {asset_id: qty for asset_id, qty in result.all() if asset_id}

    async def get_cost_basis(self, broker_id: int, asset_id: int) -> Decimal:
        """
        Get total cost basis for an asset holding (sum of BUY amounts, absolute).

        TODO: FIFO matching for accurate cost basis.
        """
        stmt = select(func.sum(Transaction.amount)).where(Transaction.broker_id == broker_id).where(Transaction.asset_id == asset_id).where(Transaction.type == TransactionType.BUY)
        result = await self.session.execute(stmt)
        value = result.scalar_one_or_none()
        return abs(value or Decimal("0"))

    # =========================================================================
    # EVENTS SUGGEST (Block C.2)
    # =========================================================================

    async def suggest_events_bulk(self, requests: List[TXEventSuggestRequestItem]) -> List[TXEventSuggestResultItem]:
        """
        For each (asset_id, date, type, tolerance_days), return candidate
        AssetEvent rows whose type maps to the tx.type and whose date is
        within ±tolerance_days. Candidates are sorted by ascending |Δdays|.

        Mapping (TransactionType → AssetEventType):
        - DIVIDEND  → {DIVIDEND}
        - INTEREST  → {INTEREST}
        - ADJUSTMENT → {PRICE_ADJUSTMENT, SPLIT}
        Any other tx.type → skipped_reason="type_not_event_compatible".

        No side effects. The caller is responsible for auth.
        """
        type_map = {
            TransactionType.DIVIDEND: {AssetEventType.DIVIDEND},
            TransactionType.INTEREST: {AssetEventType.INTEREST},
            TransactionType.ADJUSTMENT: {AssetEventType.PRICE_ADJUSTMENT, AssetEventType.SPLIT},
        }

        results: List[TXEventSuggestResultItem] = []
        for req in requests:
            if req.type not in EVENT_COMPATIBLE_TYPES:
                results.append(
                    TXEventSuggestResultItem(
                        asset_id=req.asset_id,
                        date=req.date,
                        type=req.type,
                        candidates=[],
                        skipped_reason="type_not_event_compatible",
                    )
                )
                continue

            event_types = type_map.get(req.type, set())
            lo = req.date - timedelta(days=req.tolerance_days)
            hi = req.date + timedelta(days=req.tolerance_days)

            stmt = select(AssetEvent).where(AssetEvent.asset_id == req.asset_id).where(AssetEvent.type.in_(event_types)).where(AssetEvent.date >= lo).where(AssetEvent.date <= hi)
            rows = (await self.session.execute(stmt)).scalars().all()

            candidates = [
                TXEventSuggestCandidate(
                    id=ev.id,
                    asset_id=ev.asset_id,
                    date=ev.date,
                    type=str(ev.type),
                    value=ev.value,
                    currency=ev.currency,
                    is_auto=ev.provider_assignment_id is not None,
                    distance_days=abs((ev.date - req.date).days),
                )
                for ev in rows
            ]
            candidates.sort(key=lambda c: c.distance_days)

            results.append(
                TXEventSuggestResultItem(
                    asset_id=req.asset_id,
                    date=req.date,
                    type=req.type,
                    candidates=candidates,
                    skipped_reason=None,
                )
            )

        return results

    # =========================================================================
    # TRANSFER PROMOTION (Block H.4)
    # =========================================================================

    async def promote_transfer(
        self,
        req: TXTransferPromoteRequest,
        user_id: Optional[int] = None,
    ) -> TXTransferPromoteResponse:
        """
        Promote a sciolta coppia DEPOSIT/WITHDRAWAL in TRANSFER or FX_CONVERSION.

        Atomic: delete the original pair + create the new pair in the same
        session. Any failure → rollback and `rolled_back=True`. Caller (router)
        commits only when `rolled_back=False`.
        """
        errors: List[str] = []

        from_tx = await self.session.get(Transaction, req.from_tx_id)
        to_tx = await self.session.get(Transaction, req.to_tx_id)

        if from_tx is None:
            errors.append(f"from_tx_id={req.from_tx_id} not found")
        if to_tx is None:
            errors.append(f"to_tx_id={req.to_tx_id} not found")
        if errors:
            return TXTransferPromoteResponse(rolled_back=True, errors=errors)

        # Access check EDITOR on both brokers (distinct).
        try:
            await self._enforce_batch_access({from_tx.broker_id, to_tx.broker_id}, user_id, min_role=UserRole.EDITOR)
        except HTTPException as e:
            return TXTransferPromoteResponse(rolled_back=True, errors=[e.detail if isinstance(e.detail, str) else str(e.detail)])

        # Pre-check: both current types must be in {DEPOSIT, WITHDRAWAL}.
        cash_pair = {TransactionType.DEPOSIT, TransactionType.WITHDRAWAL}
        if from_tx.type not in cash_pair or to_tx.type not in cash_pair:
            errors.append(f"promote supports only DEPOSIT/WITHDRAWAL pairs (got {from_tx.type.value}+{to_tx.type.value})")

        # new_type-specific checks.
        if req.new_type == TransactionType.TRANSFER:
            if req.asset_id is None or req.quantity is None:
                errors.append("TRANSFER promotion requires asset_id and quantity")
            if from_tx.broker_id == to_tx.broker_id:
                errors.append(f"TRANSFER requires distinct brokers (both on broker {from_tx.broker_id})")
        elif req.new_type == TransactionType.FX_CONVERSION:
            if from_tx.currency == to_tx.currency:
                errors.append(f"FX_CONVERSION requires different currencies (got {from_tx.currency}+{to_tx.currency})")
            if req.asset_id is not None:
                errors.append("FX_CONVERSION promotion must not set asset_id")

        if errors:
            return TXTransferPromoteResponse(rolled_back=True, errors=errors)

        # Snapshot originals before delete (we need broker/date/amount/currency).
        from_broker_id: int = from_tx.broker_id
        from_date: date_type = from_tx.date
        from_amount: Decimal = from_tx.amount
        from_currency: Optional[str] = from_tx.currency
        from_description: Optional[str] = from_tx.description
        from_tags_csv: Optional[str] = from_tx.tags

        to_broker_id: int = to_tx.broker_id
        to_date: date_type = to_tx.date
        to_amount: Decimal = to_tx.amount
        to_currency: Optional[str] = to_tx.currency
        to_description: Optional[str] = to_tx.description
        to_tags_csv: Optional[str] = to_tx.tags

        # Build the new pair.
        link_uuid = str(uuid4())
        from_tags = [t.strip() for t in from_tags_csv.split(",")] if from_tags_csv else None
        to_tags = [t.strip() for t in to_tags_csv.split(",")] if to_tags_csv else None

        if req.new_type == TransactionType.TRANSFER:
            qty = req.quantity
            assert qty is not None
            # Raw dicts (not TXCreateItem) because they go into execute_batch(creates_raw=...)
            # which does per-row model_validate() in try/except, collecting ALL errors
            # in one response instead of failing on the first one.
            create_from_dict = {
                "broker_id": from_broker_id,
                "asset_id": req.asset_id,
                "type": TransactionType.TRANSFER.value,
                "date": from_date.isoformat(),
                "quantity": format(-abs(qty), "f"),
                "link_uuid": link_uuid,
                "tags": from_tags,
                "description": from_description,
            }
            create_to_dict = {
                "broker_id": to_broker_id,
                "asset_id": req.asset_id,
                "type": TransactionType.TRANSFER.value,
                "date": to_date.isoformat(),
                "quantity": format(abs(qty), "f"),
                "link_uuid": link_uuid,
                "tags": to_tags,
                "description": to_description,
                "cost_basis_override": {"code": req.cost_basis_override.code, "amount": format(req.cost_basis_override.amount, "f")} if req.cost_basis_override is not None else None,
            }
        else:  # FX_CONVERSION
            if from_currency is None or to_currency is None:
                return TXTransferPromoteResponse(rolled_back=True, errors=["FX_CONVERSION requires both sides to have a currency"])
            # Raw dicts — same rationale: execute_batch collects all errors in bulk.
            create_from_dict = {
                "broker_id": from_broker_id,
                "type": TransactionType.FX_CONVERSION.value,
                "date": from_date.isoformat(),
                "cash": {"code": from_currency, "amount": format(from_amount, "f")},
                "link_uuid": link_uuid,
                "tags": from_tags,
                "description": from_description,
            }
            create_to_dict = {
                "broker_id": to_broker_id,
                "type": TransactionType.FX_CONVERSION.value,
                "date": to_date.isoformat(),
                "cash": {"code": to_currency, "amount": format(to_amount, "f")},
                "link_uuid": link_uuid,
                "tags": to_tags,
                "description": to_description,
            }

        # Atomic: delete originals + create new pair via unified pipeline.
        resp = await self.execute_batch(
            creates_raw=[create_from_dict, create_to_dict],
            updates_raw=[],
            deletes=[req.from_tx_id, req.to_tx_id],
            user_id=user_id,
            commit=True,
        )

        if resp.issues:
            err_msgs = [iss.error for iss in resp.issues]
            return TXTransferPromoteResponse(rolled_back=True, errors=err_msgs)

        # Extract IDs of the two created transactions.
        new_ids = [r.ids[0] for r in (resp.results or []) if r.operation == "create" and r.ids]
        return TXTransferPromoteResponse(
            rolled_back=False,
            new_from_tx_id=new_ids[0] if len(new_ids) > 0 else None,
            new_to_tx_id=new_ids[1] if len(new_ids) > 1 else None,
        )

    # =========================================================================
    # BULK SPLIT / PROMOTE (server-driven, immediate)
    # =========================================================================

    # Deterministic type mutation maps for split/promote.
    # Key: paired type → (from_type, to_type).
    # "from" = negative/source side, "to" = positive/destination side.
    SPLIT_TYPE_MAP: dict[TransactionType, tuple[TransactionType, TransactionType]] = {
        TransactionType.CASH_TRANSFER: (TransactionType.WITHDRAWAL, TransactionType.DEPOSIT),
        TransactionType.TRANSFER: (TransactionType.ADJUSTMENT, TransactionType.ADJUSTMENT),
        TransactionType.FX_CONVERSION: (TransactionType.WITHDRAWAL, TransactionType.DEPOSIT),
    }

    # Inverse: (type_a, type_b) → target paired type.
    # type_a/type_b ordering comes from promote_from metadata.
    # For WITHDRAWAL+DEPOSIT we need to distinguish CASH_TRANSFER vs FX_CONVERSION
    # using field constraints, so the service checks dynamically.

    @staticmethod
    def _find_promote_rule_match(tx_a, tx_b) -> Optional[TransactionType]:
        """Scan TX_TYPE_METADATA promote_from rules for a match between tx_a and tx_b."""
        for pair_type, meta in TX_TYPE_METADATA.items():
            if meta.promote_from is None:
                continue
            for rule in meta.promote_from:
                if (tx_a.type.value == rule.type_a and tx_b.type.value == rule.type_b) or (tx_a.type.value == rule.type_b and tx_b.type.value == rule.type_a):
                    if TransactionService._check_promote_constraints(tx_a, tx_b, rule.field_constraints):
                        return pair_type
        return None

    @staticmethod
    def _resolve_promote_ref(
        id_val: Optional[int],
        link_uuid_val: Optional[str],
        existing_by_id: Dict[int, Transaction],
        link_uuid_map: Dict[str, List[Tuple[int, Transaction]]],
    ) -> Optional[Transaction]:
        """Resolve a promote reference to a Transaction.

        - id_val > 0 → lookup in existing_by_id
        - link_uuid_val → lookup first TX in link_uuid_map[link_uuid_val]
        """
        if id_val is not None and id_val > 0:
            return existing_by_id.get(id_val)
        if link_uuid_val:
            entries = link_uuid_map.get(link_uuid_val, [])
            if entries:
                return entries[0][1]  # (idx, Transaction) → Transaction
        return None

    @staticmethod
    def _check_promote_constraints(tx_a: Transaction, tx_b: Transaction, constraints: list) -> bool:
        """Check if two transactions satisfy promote field constraints."""
        for c in constraints:
            assert isinstance(c, PairFieldConstraint)
            if c.field == "broker_id":
                if c.relation == "equal" and tx_a.broker_id != tx_b.broker_id:
                    return False
                if c.relation == "different" and tx_a.broker_id == tx_b.broker_id:
                    return False
            elif c.field == "asset_id":
                if c.relation == "equal" and tx_a.asset_id != tx_b.asset_id:
                    return False
                if c.relation == "different" and tx_a.asset_id == tx_b.asset_id:
                    return False
            elif c.field == "cash_currency":
                if c.relation == "equal" and tx_a.currency != tx_b.currency:
                    return False
                if c.relation == "different" and tx_a.currency == tx_b.currency:
                    return False
            elif c.field == "cash_amount":
                if c.relation == "opposite":
                    if tx_a.amount is None or tx_b.amount is None:
                        continue  # Cannot verify — skip constraint
                    if tx_a.amount != -tx_b.amount:
                        return False
            elif c.field == "quantity":
                if c.relation == "opposite":
                    if tx_a.quantity is None or tx_b.quantity is None:
                        continue  # Cannot verify — skip constraint
                    if tx_a.quantity != -tx_b.quantity:
                        return False
        return True

    async def promote_suggest_bulk(
        self,
        inputs: List,
        tolerance_days: int,
        user_id: int,
    ) -> TXPromoteSuggestResponse:
        """For each input TX, find DB transactions compatible for promote."""
        accessible = await self._get_accessible_broker_ids(user_id)
        if not accessible:
            return TXPromoteSuggestResponse(results={})

        # Collect all positive IDs from inputs to exclude self-match
        input_positive_ids: set[int] = {inp.id for inp in inputs if inp.id > 0}

        results: Dict[int, List[TXPromoteSuggestCandidate]] = {}

        for inp in inputs:
            # Determine complementary types from promote_from rules
            complementary: list[tuple[TransactionType, list]] = []
            for pair_type, meta in TX_TYPE_METADATA.items():
                if meta.promote_from is None:
                    continue
                for rule in meta.promote_from:
                    if inp.type.value == rule.type_a:
                        comp_type = TransactionType(rule.type_b)
                        complementary.append((comp_type, rule.field_constraints))
                    elif inp.type.value == rule.type_b:
                        comp_type = TransactionType(rule.type_a)
                        complementary.append((comp_type, rule.field_constraints))

            if not complementary:
                results[inp.id] = []
                continue

            # Query DB: standalone TX with complementary type, date ±tolerance, accessible broker
            comp_types = list({ct for ct, _ in complementary})
            lo = inp.date - timedelta(days=tolerance_days)
            hi = inp.date + timedelta(days=tolerance_days)

            stmt = select(Transaction).where(Transaction.type.in_(comp_types)).where(Transaction.related_transaction_id.is_(None)).where(Transaction.date >= lo).where(Transaction.date <= hi).where(Transaction.broker_id.in_(accessible))
            if input_positive_ids:
                stmt = stmt.where(Transaction.id.notin_(input_positive_ids))

            rows = (await self.session.execute(stmt)).scalars().all()

            # Build input as _PromoteCandidate for constraint checking
            inp_candidate = _PromoteCandidate(
                broker_id=inp.broker_id,
                asset_id=inp.asset_id,
                currency=inp.currency,
                amount=inp.amount,
                quantity=inp.quantity,
            )

            candidates: list[TXPromoteSuggestCandidate] = []
            for row in rows:
                matched = False
                for comp_type, constraints in complementary:
                    if row.type == comp_type:
                        if self._check_promote_constraints(inp_candidate, row, constraints):
                            matched = True
                            break
                if matched:
                    candidates.append(
                        TXPromoteSuggestCandidate(
                            id=row.id,
                            broker_id=row.broker_id,
                            date=row.date,
                            type=row.type.value,
                            currency=row.currency,
                            asset_id=row.asset_id,
                        )
                    )

            results[inp.id] = candidates

        return TXPromoteSuggestResponse(results=results)

    # =========================================================================
    # UNIFIED BATCH PIPELINE (replaces separate create/update/delete bulk)
    # =========================================================================

    async def execute_batch(
        self,
        creates_raw: List[dict],
        updates_raw: List[dict],
        deletes: List[int],
        splits_raw: List[dict] | None = None,
        promotes_raw: List[dict] | None = None,
        user_id: Optional[int] = None,
        commit: bool = False,
    ) -> TXBatchResponse:
        """Unified pipeline for both /validate (commit=False) and /commit (commit=True).

        Order: lenient parse → access check → deletes → updates → creates →
        link resolution → balance walk → commit/rollback.

        Always collects the full set of issues instead of failing fast.
        """
        issues: List[TXValidationIssue] = []
        results: List[TXBatchResultItem] = []

        # 1. Lenient per-row parse
        parsed_creates, create_issues = _parse_lenient(creates_raw, TXCreateItem, "create")
        parsed_updates, update_issues = _parse_lenient(updates_raw, TXUpdateItem, "update")
        parsed_splits, split_issues = _parse_lenient(splits_raw or [], TXSplitBatchItem, "split")
        parsed_promotes, promote_issues = _parse_lenient(promotes_raw or [], TXPromoteBatchItem, "promote")
        issues.extend(create_issues)
        issues.extend(update_issues)
        issues.extend(split_issues)
        issues.extend(promote_issues)

        # 2. Determine touched brokers for access check
        touched_brokers: Set[int] = set()
        for _, item in parsed_creates:
            touched_brokers.add(item.broker_id)

        # Lookup existing TXs for updates, deletes, splits, and promotes
        ids_to_lookup: Set[int] = set(deletes)
        for _, item in parsed_updates:
            ids_to_lookup.add(item.id)
        for _, item in parsed_splits:
            ids_to_lookup.add(item.id_a)
            ids_to_lookup.add(item.id_b)
        for _, item in parsed_promotes:
            if item.id_a is not None:
                ids_to_lookup.add(item.id_a)
            if item.id_b is not None:
                ids_to_lookup.add(item.id_b)
        existing_by_id: Dict[int, Transaction] = {}
        if ids_to_lookup:
            existing_txs = await self.get_by_ids(list(ids_to_lookup))
            existing_by_id = {tx.id: tx for tx in existing_txs}
            touched_brokers |= {tx.broker_id for tx in existing_txs}

        # Fetch split partners (both IDs now provided explicitly in id_a/id_b)
        for _, item in parsed_splits:
            for sid in (item.id_a, item.id_b):
                if sid not in existing_by_id:
                    ids_to_lookup.add(sid)
        # Re-fetch any missing IDs for splits
        missing_split_ids = {sid for _, item in parsed_splits for sid in (item.id_a, item.id_b) if sid not in existing_by_id}
        if missing_split_ids:
            partners = await self.get_by_ids(list(missing_split_ids))
            for tx in partners:
                existing_by_id[tx.id] = tx
            touched_brokers |= {tx.broker_id for tx in partners}

        # Access check (EDITOR) — report as issues, not HTTPException
        if user_id is not None:
            for broker_id in touched_brokers:
                role = await self._check_broker_access(broker_id, user_id, min_role=UserRole.EDITOR)
                if role is None:
                    issues.append(
                        TXValidationIssue(
                            operation="create",
                            index=0,
                            ref_id=None,
                            error=f"Access denied: EDITOR required for broker {broker_id}",
                            code=TXValidationCode.ACCESS_DENIED.value,
                            params={"brokerId": broker_id},
                        )
                    )

        # If access denied, stop early
        if any(i.code == "accessDenied" for i in issues):
            return TXBatchResponse(committed=False, issues=issues)

        earliest_date_by_broker: Dict[int, date_type] = {}

        # 3. Apply deletes
        id_set_deletes = set(deletes)
        for idx, tx_id in enumerate(deletes):
            tx = existing_by_id.get(tx_id)
            if tx is None:
                issues.append(TXValidationIssue(operation="delete", index=idx, ref_id=tx_id, error=f"Transaction {tx_id} not found", code=TXValidationCode.TX_NOT_FOUND.value, params={"id": tx_id}))
                continue
            # Linked-pair integrity check
            if tx.related_transaction_id and tx.related_transaction_id not in id_set_deletes:
                issues.append(
                    TXValidationIssue(
                        operation="delete",
                        index=idx,
                        ref_id=tx_id,
                        error=f"Cannot delete linked transaction {tx_id} without its pair {tx.related_transaction_id}",
                        code="pairDeleteIncomplete",
                        params={"id": tx_id, "partnerId": tx.related_transaction_id},
                    )
                )
                continue
            try:
                prev = earliest_date_by_broker.get(tx.broker_id)
                earliest_date_by_broker[tx.broker_id] = tx.date if prev is None else min(prev, tx.date)
                await self.session.delete(tx)
                results.append(TXBatchResultItem(operation="delete", index=idx, ids=[tx_id], status="success"))
            except Exception as e:  # noqa: BLE001
                issues.append(TXValidationIssue(operation="delete", index=idx, ref_id=tx_id, error=str(e)))

        # 3b. Apply splits (must run before updates so post-split edits apply correctly)
        for orig_idx, item in parsed_splits:
            tx_a = existing_by_id.get(item.id_a)
            tx_b = existing_by_id.get(item.id_b)
            if tx_a is None or tx_b is None:
                missing_id = item.id_a if tx_a is None else item.id_b
                issues.append(
                    TXValidationIssue(
                        operation="split",
                        index=orig_idx,
                        ref_id=missing_id,
                        error=f"Transaction {missing_id} not found",
                        code=TXValidationCode.TX_NOT_FOUND.value,
                    )
                )
                continue
            # Validate they are actually a linked pair
            if tx_a.related_transaction_id != item.id_b or tx_b.related_transaction_id != item.id_a:
                issues.append(
                    TXValidationIssue(
                        operation="split",
                        index=orig_idx,
                        ref_id=item.id_a,
                        error=f"Transactions {item.id_a} and {item.id_b} are not a linked pair",
                        code=TXValidationCode.SPLIT_IDS_MISMATCH.value,
                    )
                )
                continue
            # Use tx_a as the reference for type
            tx = tx_a
            partner = tx_b
            split_types = self.SPLIT_TYPE_MAP.get(tx.type)
            if split_types is None:
                issues.append(
                    TXValidationIssue(
                        operation="split",
                        index=orig_idx,
                        ref_id=item.id_a,
                        error=f"Type {tx.type.value} cannot be split",
                        code=TXValidationCode.TYPE_CANNOT_SPLIT.value,
                    )
                )
                continue

            from_type, to_type = split_types

            # Determine from/to by value signs
            if tx.type == TransactionType.TRANSFER:
                if tx.quantity < Decimal("0"):
                    tx_from, tx_to = tx, partner
                else:
                    tx_from, tx_to = partner, tx
            else:
                if tx.amount < Decimal("0"):
                    tx_from, tx_to = tx, partner
                else:
                    tx_from, tx_to = partner, tx

            # Mutate types
            tx_from.type = from_type
            tx_to.type = to_type

            # Remove link
            tx_from.related_transaction_id = None
            tx_to.related_transaction_id = None

            # TRANSFER→ADJUSTMENT: keep asset+qty. CASH→WITHDRAWAL/DEPOSIT: clear asset
            if split_types != (TransactionType.ADJUSTMENT, TransactionType.ADJUSTMENT):
                tx_from.asset_id = None
                tx_to.asset_id = None

            tx_from.updated_at = utcnow()
            tx_to.updated_at = utcnow()

            for t in (tx_from, tx_to):
                prev = earliest_date_by_broker.get(t.broker_id)
                earliest_date_by_broker[t.broker_id] = t.date if prev is None else min(prev, t.date)

            results.append(TXBatchResultItem(operation="split", index=orig_idx, ids=[tx_from.id, tx_to.id], status="success"))

        # 4. Apply updates (only successfully-parsed rows)
        for orig_idx, item in parsed_updates:
            tx = existing_by_id.get(item.id)
            if tx is None:
                issues.append(TXValidationIssue(operation="update", index=orig_idx, ref_id=item.id, error=f"Transaction {item.id} not found", code=TXValidationCode.TX_NOT_FOUND.value, params={"id": item.id}))
                continue
            try:
                check_date = tx.date
                # Step 15 (C5): type swap within swap group
                if item.type is not None and item.type != tx.type:
                    allowed = get_swap_group(tx.type)
                    if item.type not in allowed:
                        raise ValueError(f"Cannot change type from {tx.type.value} to {item.type.value} " f"(allowed swaps: {', '.join(t.value for t in allowed)})")
                    tx.type = item.type
                if item.date is not None:
                    check_date = min(check_date, item.date)
                    tx.date = item.date
                if item.quantity is not None:
                    tx.quantity = item.quantity
                if item.cash is not None:
                    tx.amount = item.cash.amount
                    tx.currency = item.cash.code
                if item.tags is not None:
                    tx.tags = tags_to_csv(item.tags)
                if item.description is not None:
                    tx.description = item.description
                if item.cost_basis_override is not None:
                    tx.cost_basis_override = item.cost_basis_override.amount
                    tx.cost_basis_currency = item.cost_basis_override.code
                if item.asset_event_id is not None:
                    if item.asset_event_id == 0:
                        tx.asset_event_id = None
                    else:
                        if tx.asset_id is None:
                            raise ValueError("Cannot link asset_event_id: transaction has no asset_id")
                        await self._validate_asset_event_link(item.asset_event_id, tx.asset_id)
                        tx.asset_event_id = item.asset_event_id
                tx.updated_at = utcnow()
                prev = earliest_date_by_broker.get(tx.broker_id)
                earliest_date_by_broker[tx.broker_id] = check_date if prev is None else min(prev, check_date)
                results.append(TXBatchResultItem(operation="update", index=orig_idx, ids=[item.id], status="success"))
            except Exception as e:  # noqa: BLE001
                issues.append(TXValidationIssue(operation="update", index=orig_idx, ref_id=item.id, error=str(e)))

        # 4b. Validate pair desc/tags consistency for updated linked TXs
        for orig_idx, item in parsed_updates:
            if item.tags is None and item.description is None:
                continue
            tx = existing_by_id.get(item.id)
            if not tx or not tx.related_transaction_id:
                continue
            partner = existing_by_id.get(tx.related_transaction_id)
            if partner is None:
                partner = await self.session.get(Transaction, tx.related_transaction_id)
            if partner is not None:
                desc_result = self._validate_pair_description_tags(tx, partner)
                if desc_result is not None:
                    err_msg, err_code, err_params = desc_result
                    issues.append(
                        TXValidationIssue(
                            operation="update",
                            index=orig_idx,
                            ref_id=item.id,
                            error=err_msg,
                            code=err_code,
                            params=err_params,
                        )
                    )

        # 5. Apply creates (only successfully-parsed rows)
        link_uuid_map: Dict[str, List[Tuple[int, Transaction]]] = defaultdict(list)
        for orig_idx, item in parsed_creates:
            try:
                if item.asset_id is not None:
                    asset_result = await self.session.execute(select(Asset.asset_type).where(Asset.id == item.asset_id))
                    if asset_result.scalar_one_or_none() == AssetType.INDEX:
                        raise ValueError("Cannot create transactions for INDEX assets")
                if item.asset_event_id is not None:
                    assert item.asset_id is not None
                    await self._validate_asset_event_link(item.asset_event_id, item.asset_id)
                tx = Transaction(
                    broker_id=item.broker_id,
                    asset_id=item.asset_id,
                    type=item.type,
                    date=item.date,
                    quantity=item.quantity,
                    amount=item.get_amount(),
                    currency=item.get_currency(),
                    tags=item.get_tags_csv(),
                    description=item.description,
                    cost_basis_override=item.cost_basis_override.amount if item.cost_basis_override else None,
                    cost_basis_currency=item.cost_basis_override.code if item.cost_basis_override else None,
                    asset_event_id=item.asset_event_id,
                    created_at=utcnow(),
                    updated_at=utcnow(),
                )
                self.session.add(tx)
                await self.session.flush()
                prev = earliest_date_by_broker.get(tx.broker_id)
                earliest_date_by_broker[tx.broker_id] = tx.date if prev is None else min(prev, tx.date)
                if item.link_uuid:
                    link_uuid_map[item.link_uuid].append((orig_idx, tx))
                results.append(TXBatchResultItem(operation="create", index=orig_idx, ids=[tx.id], link_uuid=item.link_uuid, status="success"))
            except Exception as e:  # noqa: BLE001
                issues.append(TXValidationIssue(operation="create", index=orig_idx, ref_id=None, error=str(e)))


        # 5c. Apply promotes
        consumed_link_uuids: Set[str] = set()

        for orig_idx, item in parsed_promotes:
            tx_a = self._resolve_promote_ref(item.id_a, item.link_uuid_a, existing_by_id, link_uuid_map)
            tx_b = self._resolve_promote_ref(item.id_b, item.link_uuid_b, existing_by_id, link_uuid_map)

            if tx_a is None:
                issues.append(
                    TXValidationIssue(
                        operation="promote",
                        index=orig_idx,
                        error="Cannot resolve TX A reference",
                        code=TXValidationCode.PROMOTE_REF_NOT_FOUND.value,
                    )
                )
                continue
            if tx_b is None:
                issues.append(
                    TXValidationIssue(
                        operation="promote",
                        index=orig_idx,
                        error="Cannot resolve TX B reference",
                        code=TXValidationCode.PROMOTE_REF_NOT_FOUND.value,
                    )
                )
                continue
            if tx_a.related_transaction_id is not None:
                issues.append(
                    TXValidationIssue(
                        operation="promote",
                        index=orig_idx,
                        ref_id=getattr(tx_a, "id", None),
                        error=f"TX A ({tx_a.id}) already paired",
                        code=TXValidationCode.ALREADY_PAIRED.value,
                    )
                )
                continue
            if tx_b.related_transaction_id is not None:
                issues.append(
                    TXValidationIssue(
                        operation="promote",
                        index=orig_idx,
                        ref_id=getattr(tx_b, "id", None),
                        error=f"TX B ({tx_b.id}) already paired",
                        code=TXValidationCode.ALREADY_PAIRED.value,
                    )
                )
                continue

            target_type = self._find_promote_rule_match(tx_a, tx_b)
            if target_type is None:
                issues.append(
                    TXValidationIssue(
                        operation="promote",
                        index=orig_idx,
                        error=f"No promote rule for {tx_a.type.value}+{tx_b.type.value}",
                        code=TXValidationCode.NO_PROMOTE_RULE.value,
                    )
                )
                continue

            # Mutate types + set bidirectional link
            tx_a.type = target_type
            tx_b.type = target_type
            tx_a.related_transaction_id = tx_b.id
            tx_b.related_transaction_id = tx_a.id

            # Apply resolved_fields
            if item.resolved_fields:
                for field_name in ("description",):
                    if field_name in item.resolved_fields:
                        val = item.resolved_fields[field_name]
                        setattr(tx_a, field_name, val)
                        setattr(tx_b, field_name, val)
                if "cost_basis_override" in item.resolved_fields:
                    cbo_raw = item.resolved_fields["cost_basis_override"]
                    if cbo_raw is not None:
                        # Parse as Currency dict {code, amount}
                        cbo_currency = Currency.model_validate(cbo_raw)
                        cbo_amount = cbo_currency.amount
                        cbo_code = cbo_currency.code
                    else:
                        cbo_amount = None
                        cbo_code = None
                    # Only apply to receiver (qty > 0); force null on sender
                    if tx_a.quantity and tx_a.quantity > 0:
                        tx_a.cost_basis_override = cbo_amount
                        tx_a.cost_basis_currency = cbo_code
                        tx_b.cost_basis_override = None
                        tx_b.cost_basis_currency = None
                    elif tx_b.quantity and tx_b.quantity > 0:
                        tx_b.cost_basis_override = cbo_amount
                        tx_b.cost_basis_currency = cbo_code
                        tx_a.cost_basis_override = None
                        tx_a.cost_basis_currency = None
                    else:
                        # Fallback: apply to both (non-TRANSFER promote)
                        tx_a.cost_basis_override = cbo_amount
                        tx_a.cost_basis_currency = cbo_code
                        tx_b.cost_basis_override = cbo_amount
                        tx_b.cost_basis_currency = cbo_code
                if "tags" in item.resolved_fields:
                    csv_tags = tags_to_csv(item.resolved_fields["tags"])
                    tx_a.tags = csv_tags
                    tx_b.tags = csv_tags
                if "date" in item.resolved_fields:
                    resolved_date = parse_ISO_date(item.resolved_fields["date"])
                    tx_a.date = resolved_date
                    tx_b.date = resolved_date

            tx_a.updated_at = utcnow()
            tx_b.updated_at = utcnow()

            # Auto-calc cost_basis_override for TRANSFER receiver if not set
            wac_result_for_promote: WACResult | None = None
            if target_type == TransactionType.TRANSFER:
                receiver = tx_a if (tx_a.quantity and tx_a.quantity > 0) else tx_b if (tx_b.quantity and tx_b.quantity > 0) else None
                sender = tx_b if receiver is tx_a else tx_a
                if receiver and receiver.cost_basis_override is None and sender.broker_id:
                    # Fetch asset currency for target_currency determination
                    asset_row = await self.session.execute(select(Asset.currency).where(Asset.id == receiver.asset_id))
                    asset_ccy = asset_row.scalar_one_or_none() or ""
                    wac_result_for_promote = await compute_weighted_avg_cost(self.session, sender.broker_id, receiver.asset_id, receiver.date, asset_ccy)
                    if wac_result_for_promote.wac is not None:
                        receiver.cost_basis_override = wac_result_for_promote.wac.amount
                        receiver.cost_basis_currency = wac_result_for_promote.wac.code
                    else:
                        receiver.cost_basis_override = None
                        receiver.cost_basis_currency = None
                # Force sender override to null
                if sender:
                    sender.cost_basis_override = None
                    sender.cost_basis_currency = None

            for t in (tx_a, tx_b):
                prev = earliest_date_by_broker.get(t.broker_id)
                earliest_date_by_broker[t.broker_id] = t.date if prev is None else min(prev, t.date)

            # Track consumed link_uuids so Step 6 doesn't re-process them
            if item.link_uuid_a:
                consumed_link_uuids.add(item.link_uuid_a)
            if item.link_uuid_b:
                consumed_link_uuids.add(item.link_uuid_b)

            results.append(TXBatchResultItem(operation="promote", index=orig_idx, ids=[tx_a.id, tx_b.id], status="success", wac_info=wac_result_for_promote))

        # 6. Link resolution
        for link_uuid, pairs in link_uuid_map.items():
            if link_uuid in consumed_link_uuids:
                continue  # Already consumed by a promote in Step 5c
            if len(pairs) == 2:
                pair_result = self._validate_linked_pair(pairs[0][1], pairs[1][1])
                if pair_result is not None:
                    pair_error, pair_code, pair_params = pair_result
                    issues.append(TXValidationIssue(operation="create", index=pairs[0][0], ref_id=None, error=pair_error, code=pair_code, params=pair_params))
                    continue
                # Validate description/tags consistency
                desc_result = self._validate_pair_description_tags(pairs[0][1], pairs[1][1])
                if desc_result is not None:
                    desc_error, desc_code, desc_params = desc_result
                    issues.append(TXValidationIssue(operation="create", index=pairs[0][0], ref_id=None, error=desc_error, code=desc_code, params=desc_params))
                    continue
                pairs[0][1].related_transaction_id = pairs[1][1].id
                pairs[1][1].related_transaction_id = pairs[0][1].id
            else:
                issues.append(
                    TXValidationIssue(
                        operation="create",
                        index=pairs[0][0] if pairs else 0,
                        ref_id=None,
                        error=f"link_uuid '{link_uuid}' has {len(pairs)} creates (expected 2)",
                        code=TXValidationCode.LINK_UUID_PAIR_COUNT.value,
                        params={"linkUuid": link_uuid, "count": len(pairs)},
                    )
                )

        # 6b. Auto-calc cost_basis_override on TRANSFER receivers
        for link_uuid, pairs in link_uuid_map.items():
            if link_uuid in consumed_link_uuids:
                continue
            if len(pairs) != 2:
                continue
            for _, tx in pairs:
                if tx.type == TransactionType.TRANSFER and tx.quantity and tx.quantity > 0 and tx.cost_basis_override is None:
                    # Find partner (the sender) in same link_uuid pair
                    partner = next((t for _, t in pairs if t.id != tx.id), None)
                    if partner and partner.broker_id:
                        # Fetch asset currency
                        asset_row = await self.session.execute(select(Asset.currency).where(Asset.id == tx.asset_id))
                        asset_ccy = asset_row.scalar_one_or_none() or ""
                        wac_result = await compute_weighted_avg_cost(self.session, partner.broker_id, tx.asset_id, tx.date, asset_ccy)
                        if wac_result.wac is not None:
                            tx.cost_basis_override = wac_result.wac.amount
                            tx.cost_basis_currency = wac_result.wac.code
                        # Propagate wac_info to the corresponding result item
                        for r in results:
                            if r.link_uuid == link_uuid and r.operation == "create":
                                r.wac_info = wac_result
                                break

        # 7. Balance walk per affected broker
        try:
            await self.session.flush()
            for broker_id, from_date in earliest_date_by_broker.items():
                await self._validate_broker_balances(broker_id, from_date)
        except BalanceValidationError as e:
            issues.append(TXValidationIssue(operation="create", index=-1, ref_id=None, error=str(e), code=e.code, params=e.params))
        except Exception as e:  # noqa: BLE001
            issues.append(TXValidationIssue(operation="create", index=-1, ref_id=None, error=f"Balance validation error: {e}"))

        # 8. Decision
        if issues:
            return TXBatchResponse(committed=False, issues=issues)
        elif not commit:
            # Dry-run: clean batch but caller requested validate-only
            return TXBatchResponse(committed=False, issues=[], results=results)
        else:
            # Commit: caller (router) will session.commit()
            return TXBatchResponse(committed=True, issues=[], results=results)
