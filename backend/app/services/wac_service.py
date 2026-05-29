"""
WAC (Weighted Average Cost) Service for LibreFolio.

Contains the async computation function for WAC calculation:
- compute_wac_iterative(): Inventory-aware iterative WAC (PMC)

Standalone async function (not a class method) that operates
on a SQLAlchemy AsyncSession. Used by:
- TransactionService.execute_batch() (inline WAC for auto items)
- Future: /analytics/wac endpoint
"""

from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Transaction, TransactionType
from backend.app.schemas.common import Currency
from backend.app.schemas.wac import WACConversionInfo, WACPreviewResultItem, WACQualifyingTX
from backend.app.services.fx import convert_bulk
from backend.app.utils.financial_utils import WACInputTX, compute_wac_from_txlist, determine_target_currency

# =============================================================================
# WAC ITERATIVE — Inventory-aware iterative WAC (PMC)
# =============================================================================


async def compute_wac_iterative(
    session: AsyncSession,
    broker_id: int,
    asset_id: int,
    as_of_date: date_type,
    asset_currency: str,
    excluded_tx_ids: list[int] | None = None,
) -> WACPreviewResultItem:
    """Compute inventory-aware WAC (PMC) for an asset at a broker up to a date.

    Preparation layer: queries DB, handles FX conversion,
    then delegates to compute_wac_from_txlist() for pure math.
    """
    excluded = set(excluded_tx_ids or [])

    # 1. Query ALL transactions for this (broker, asset) with date <= as_of_date and qty != 0
    stmt = select(Transaction).where(
        Transaction.broker_id == broker_id,
        Transaction.asset_id == asset_id,
        Transaction.date <= as_of_date,
        Transaction.quantity.is_not(None),
        Transaction.quantity != 0,
    )
    db_rows = (await session.execute(stmt)).scalars().all()

    # 2. Build unified row tuples from DB rows (minus excluded)
    # Tuple: (tx_id, type_str, date, quantity, amount, currency, cbo_amount, cbo_ccy, is_pending, cbm)
    unified: list[tuple] = []

    for row in db_rows:
        if row.id in excluded:
            continue
        unified.append(
            (
                row.id,
                row.type.value if hasattr(row.type, "value") else str(row.type),
                row.date,
                row.quantity,
                row.amount,
                row.currency,
                row.cost_basis_override,
                row.cost_basis_currency,
                False,
                None,
            )
        )

    if not unified:
        return WACPreviewResultItem(
            wac=Currency(code=asset_currency, amount=Decimal("0")),
            wac_qualifying_txs=[],
            wac_missing_pairs=[],
        )

    # 3. Build WACInputTX list and determine target_currency
    #    First pass: determine currencies for target_currency selection
    pre_txs: list[WACInputTX] = []
    for tid, ttype, dt, qty, amount, ccy, cbo_amt, cbo_ccy, is_pend, cbm in unified:
        if qty > 0:
            orig_ccy = ccy if ttype == "BUY" else (cbo_ccy or asset_currency)
        else:
            orig_ccy = ccy or asset_currency
        pre_txs.append(
            WACInputTX(
                tx_id=tid,
                type=ttype,
                date=dt,
                quantity=qty,
                unit_cost_converted=None,
                original_currency=orig_ccy,
                is_pending=is_pend,
            )
        )

    target_currency = determine_target_currency(pre_txs, asset_currency)

    # 4. FX conversion for acquisitions with different currency
    fx_requests: list[tuple[int, Currency, str, date_type]] = []  # (idx, cost_ccy, target, date)

    for i, (tid, ttype, dt, qty, amount, ccy, cbo_amt, cbo_ccy, is_pend, cbm) in enumerate(unified):
        if qty <= 0:
            continue
        if ttype == "BUY":
            tx_ccy = ccy or asset_currency
            if tx_ccy != target_currency and amount:
                cost = abs(amount)
                fx_requests.append((i, Currency(code=tx_ccy, amount=cost), target_currency, dt))
        elif cbo_amt is not None:
            tx_ccy = cbo_ccy or asset_currency
            if tx_ccy != target_currency:
                cost = qty * cbo_amt
                fx_requests.append((i, Currency(code=tx_ccy, amount=cost), target_currency, dt))

    fx_converted: dict[int, Decimal] = {}
    missing_pairs: list[str] = []

    if fx_requests:
        bulk_input = [(amt, to_ccy, dt) for _, amt, to_ccy, dt in fx_requests]
        fx_results, _fx_errors = await convert_bulk(session, bulk_input, raise_on_error=False)
        for j, (unified_idx, amt_ccy, to_ccy, dt) in enumerate(fx_requests):
            result = fx_results[j] if j < len(fx_results) else None
            if result is None:
                pair_key = f"{amt_ccy.code}/{to_ccy}"
                if pair_key not in missing_pairs:
                    missing_pairs.append(pair_key)
            else:
                converted, _rate_date, _bf = result
                fx_converted[unified_idx] = converted.amount

    if missing_pairs:
        return WACPreviewResultItem(wac=None, wac_qualifying_txs=[], wac_missing_pairs=missing_pairs)

    # 5. Build final WACInputTX list with converted costs
    input_txs: list[WACInputTX] = []
    for i, (tid, ttype, dt, qty, amount, ccy, cbo_amt, cbo_ccy, is_pend, cbm) in enumerate(unified):
        unit_cost: Decimal | None = None
        orig_ccy = ccy or asset_currency

        if qty > 0:
            if ttype == "BUY":
                if i in fx_converted:
                    unit_cost = fx_converted[i] / qty
                elif amount:
                    unit_cost = abs(amount) / qty
                else:
                    unit_cost = Decimal("0")
                orig_ccy = ccy or asset_currency
            elif cbo_amt is not None:
                if i in fx_converted:
                    unit_cost = fx_converted[i] / qty
                else:
                    unit_cost = cbo_amt
                orig_ccy = cbo_ccy or asset_currency
            else:
                unit_cost = None  # will be treated as zero cost (or add_at_wac if cbm == "auto")
                orig_ccy = asset_currency
        # For reductions, unit_cost stays None — compute_wac_from_txlist uses current WAC

        input_txs.append(
            WACInputTX(
                tx_id=tid,
                type=ttype,
                date=dt,
                quantity=qty,
                unit_cost_converted=unit_cost,
                original_currency=orig_ccy,
                is_pending=is_pend,
                cost_basis_mode=cbm,
            )
        )

    # 6. Delegate to pure math function
    calc_result = compute_wac_from_txlist(input_txs, target_currency)

    # 7. Convert result to schema
    qualifying_txs = [
        WACQualifyingTX(
            tx_id=q.tx_id,
            type=q.type,
            date=q.date,
            quantity=q.quantity,
            unit_cost=q.unit_cost,
            currency=q.currency,
            effect=q.effect,
            running_wac=q.running_wac,
        )
        for q in calc_result.qualifying
    ]

    return WACPreviewResultItem(
        wac=Currency(code=target_currency, amount=calc_result.wac_amount) if calc_result.pool_qty >= 0 else None,
        wac_qualifying_txs=qualifying_txs,
        wac_missing_pairs=[],
    )
