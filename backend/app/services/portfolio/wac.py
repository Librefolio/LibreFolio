"""WAC (PMC) of one (broker, asset): ``compute_wac_iterative`` for the transaction preview, the WAC endpoint and the planner (a facade over
``financial_math.average_cost``), and ``wac_pool_holding`` (what that WAC's pool holds, N88)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Transaction,
)
from backend.app.db.precision import round_computed_value
from backend.app.schemas.common import Currency, FxBackwardFillInfo
from backend.app.schemas.wac import WACMissingPairInfo, WACPreviewResultItem, WACQualifyingTX
from backend.app.services.financial_math.average_cost import (
    CostEffect,
    CostPosition,
    CostStep,
    compute_average_costs,
    cost_movement_from_transaction,
    determine_target_currency,
    movement_unit_costs,
)
from backend.app.services.financial_math.splits import split_linked_ids
from backend.app.utils.runtime.cache import get_ttl_cache

# WAC computation cache: avoid re-querying DB for unchanged (broker, asset) pairs
_wac_cache = get_ttl_cache("portfolio_wac", maxsize=200, ttl=3600)  # 1h


async def compute_wac_iterative(
    session: AsyncSession,
    broker_id: int,
    asset_id: int,
    as_of_date: date_type,
    asset_currency: str,
    excluded_tx_ids: list[int] | None = None,
    target_currency_override: str | None = None,
    use_cache: bool = True,
) -> WACPreviewResultItem:
    """Compute inventory-aware WAC (PMC) for an asset at a broker up to a date.

    Facade over :func:`~backend.app.services.financial_math.average_cost.compute_average_costs`
    for the transaction preview and the planner: it loads the rows,
    detects split-linked adjustments, picks the target currency (the override, or the currency
    of the last acquisition) and maps the average-cost timeline to ``WACPreviewResultItem``.
    Each acquisition is converted into the target currency at its own date; when one
    conversion is missing the result is ``wac=None`` with the missing pairs and dates.

    By default, results are cached per (broker_id, asset_id, as_of_date) with a
    transaction fingerprint. Callers that need an uncached domain snapshot can
    set ``use_cache=False`` without mutating shared cache state.
    """
    excluded = set(excluded_tx_ids or [])

    # 1. The pool's rows, and the ones linked to a split
    db_rows, split_linked_row_ids = await _wac_pool_rows(session, broker_id, asset_id, as_of_date)

    # WAC cache check: fingerprint from transaction IDs + updated_at

    wac_h = hashlib.md5(usedforsecurity=False)
    for row in db_rows:
        wac_h.update(f"{row.id}:{row.updated_at.isoformat()}".encode())
    # split_linked_row_ids is queried live against AssetEvent.type (not reflected in
    # Transaction.updated_at), so it must contribute to the fingerprint separately.
    wac_h.update(str(tuple(sorted(split_linked_row_ids))).encode())
    wac_fp = wac_h.hexdigest()
    excluded_key = tuple(sorted(excluded)) if excluded else ()
    wac_cache_key = (broker_id, asset_id, as_of_date.isoformat(), asset_currency, target_currency_override, excluded_key, wac_fp)

    if use_cache:
        cached_wac, wac_hit = _wac_cache.get(wac_cache_key)
        if wac_hit:
            return cached_wac

    # 2. The rows in replay order, as average-cost movements
    rows = sorted((row for row in db_rows if row.id not in excluded), key=lambda row: (row.date, row.id))
    if not rows:
        return WACPreviewResultItem(
            wac=Currency(code=asset_currency, amount=Decimal("0")),
            wac_qualifying_txs=[],
            wac_missing_pairs=[],
        )
    movements = tuple(movement for row in rows if (movement := cost_movement_from_transaction(row, asset_currency=asset_currency, split_linked=row.id in split_linked_row_ids)) is not None)

    # 3. Target currency: the override, or the currency of the last acquisition
    target_currency = target_currency_override or determine_target_currency(movements, asset_currency)

    # 4. Average cost in the target currency, each acquisition converted at its own date
    position_key = (broker_id, asset_id)
    average_cost = (
        await compute_average_costs(
            session,
            [CostPosition(key=position_key, asset_currency=asset_currency, movements=movements)],
            report_currency=target_currency,
            asset_leg=False,
        )
    )[position_key]

    # 5. Fail-safe: one missing conversion and there is no average cost to give
    if average_cost.has_missing_report_fx:
        return WACPreviewResultItem(
            wac=None,
            wac_qualifying_txs=[],
            wac_missing_pairs=[WACMissingPairInfo(pair=item.pair, dates=list(item.dates)) for item in average_cost.missing if item.leg == "report"],
        )

    # The average stays exact in the house; here it leaves the calculation to become an input — a preview the user
    # freezes into a manual cost, an auto cost written on the row — so it is rounded to what that column keeps
    # (C-97 decision D6, MF-W56): a periodic quotient would otherwise be refused (D2) or stored past the limit.
    result = WACPreviewResultItem(
        wac=Currency(code=target_currency, amount=round_computed_value(average_cost.unit_cost_report, Transaction, "cost_basis_override")),
        wac_qualifying_txs=_wac_qualifying_txs(average_cost.steps, target_currency),
        wac_missing_pairs=[],
    )

    # Store in WAC cache
    if use_cache:
        _wac_cache.set(wac_cache_key, result)

    return result


async def _wac_pool_rows(session: AsyncSession, broker_id: int, asset_id: int, as_of_date: date_type) -> tuple[list[Transaction], set[int]]:
    """The rows of the pool a WAC averages — every transaction of ``(broker, asset)`` up to ``as_of_date`` with a quantity
    neither NULL nor zero — and those linked to a SPLIT AssetEvent, which rescale the pool (same cost, new quantity)
    instead of adding or reducing."""
    stmt = select(Transaction).where(
        Transaction.broker_id == broker_id,
        Transaction.asset_id == asset_id,
        Transaction.date <= as_of_date,
        Transaction.quantity.is_not(None),
        Transaction.quantity != 0,
    )
    db_rows = list((await session.execute(stmt)).scalars().all())
    return db_rows, await split_linked_ids(session, db_rows)


@dataclass(frozen=True, slots=True)
class WacPoolHolding:
    """What the pool of a WAC holds on its date (N88, J-57): the units, and whether their cost is wholly known."""

    quantity: Decimal
    cost_complete: bool


async def wac_pool_holding(
    session: AsyncSession,
    broker_id: int,
    asset_id: int,
    as_of_date: date_type,
    asset_currency: str,
    excluded_tx_ids: list[int] | None = None,
    target_currency_override: str | None = None,
) -> WacPoolHolding:
    """The average-cost engine's own quantity and cost completeness for the pool :func:`compute_wac_iterative` averages
    with the same arguments, uncached.

    An average of 0 is no cost when the pool holds no units (never held, or sold out: the engine resets a pool that
    empties) or holds only units of unknown cost (``ADD_UNKNOWN_COST`` counts at zero and leaves the cost incomplete);
    a pool of free units holds units at a known cost of 0. The batch's Auto step reads it only when the average is 0.
    """
    excluded = set(excluded_tx_ids or [])
    db_rows, split_linked_row_ids = await _wac_pool_rows(session, broker_id, asset_id, as_of_date)
    rows = sorted((row for row in db_rows if row.id not in excluded), key=lambda row: (row.date, row.id))
    movements = tuple(movement for row in rows if (movement := cost_movement_from_transaction(row, asset_currency=asset_currency, split_linked=row.id in split_linked_row_ids)) is not None)
    if not movements:
        return WacPoolHolding(quantity=Decimal("0"), cost_complete=True)
    position_key = (broker_id, asset_id)
    average_cost = (
        await compute_average_costs(
            session,
            [CostPosition(key=position_key, asset_currency=asset_currency, movements=movements)],
            report_currency=target_currency_override or determine_target_currency(movements, asset_currency),
            asset_leg=False,
        )
    )[position_key]
    return WacPoolHolding(quantity=average_cost.quantity, cost_complete=average_cost.report_complete)


# Effects of the average-cost steps in the vocabulary of WACQualifyingTX.effect, which the
# transaction preview and the planner read: an acquisition of unknown cost enters at zero.
_WAC_PREVIEW_EFFECTS = {
    CostEffect.ADD: "add",
    CostEffect.ADD_ZERO_COST: "add_zero_cost",
    CostEffect.ADD_UNKNOWN_COST: "add_zero_cost",
    CostEffect.REDUCE: "reduce",
    CostEffect.SPLIT_RESCALE: "split_rescale",
}


def _wac_qualifying_txs(steps: tuple[CostStep, ...], target_currency: str) -> list[WACQualifyingTX]:
    """One preview row per movement: unit cost, running WAC and conversion provenance."""
    rows: list[WACQualifyingTX] = []
    for step, unit_cost in zip(steps, movement_unit_costs(steps), strict=True):
        movement = step.movement
        conversion = step.conversion
        rows.append(
            WACQualifyingTX(
                tx_id=movement.movement_id,
                type=movement.transaction_type,
                date=movement.date,
                quantity=movement.quantity,
                unit_cost=unit_cost.report,
                currency=target_currency,
                effect=_WAC_PREVIEW_EFFECTS[step.effect],
                running_wac=step.unit_cost_report,
                fx_info=FxBackwardFillInfo(fx_rate_date=conversion.rate_date, fx_days_back=conversion.days_back) if conversion else None,
                original_unit_cost=unit_cost.original,
                original_currency=conversion.original_currency if conversion else None,
                fx_rate_used=conversion.rate if conversion else None,
            )
        )
    return rows
