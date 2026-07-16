"""
Financial utility functions — pure math, no I/O.

This module contains calculation functions that operate on pre-fetched data.
No database access, no async, no side effects.

Used by transaction_service.py (WAC preview) and portfolio calculations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as date_type
from decimal import Decimal
from itertools import groupby
from typing import Optional

from backend.app.schemas.wac import WACQualifyingTX


@dataclass
class WACInputTX:
    """A transaction ready for WAC calculation (pre-processed, FX-converted).

    All costs should already be in target_currency.
    This is an internal structure for the math layer — not an API schema.
    The preparation layer (in transaction_service.py) builds these from
    DB rows + pending TXs after FX conversion.
    """

    tx_id: Optional[int]  # None if pending without DB id
    type: str  # BUY, SELL, TRANSFER, ADJUSTMENT, etc.
    date: date_type
    quantity: Decimal  # signed: + for buy/in, - for sell/out
    unit_cost_converted: Optional[Decimal]  # per-unit cost in target_currency (None → zero cost)
    original_currency: Optional[str] = None
    is_pending: bool = False  # True if from workspace (not yet in DB)
    cost_basis_mode: Optional[str] = None  # "auto" | "manual" | None
    is_split_linked: bool = False  # True if this ADJUSTMENT is linked to an AssetEvent of type SPLIT


@dataclass
class WACCalcResult:
    """Result of pure WAC calculation."""

    wac_amount: Decimal  # per-unit WAC in target_currency
    wac_currency: str
    pool_qty: Decimal  # remaining quantity in pool
    qualifying: list[WACQualifyingTX] = field(default_factory=list)


def determine_target_currency(txs: list[WACInputTX], asset_currency: str) -> str:
    """Determine target currency from acquisition TXs.

    Rule: currency of the most recent acquisition (deterministic).
    Fallback: asset_currency when no acquisitions exist.
    """
    acquisitions = [tx for tx in txs if tx.quantity > 0]
    if not acquisitions:
        return asset_currency
    latest = max(acquisitions, key=lambda t: t.date)
    return latest.original_currency or asset_currency


def compute_wac_from_txlist(
    txs: list[WACInputTX],
    target_currency: str,
) -> WACCalcResult:
    """Compute inventory-aware WAC (PMC) from a pre-sorted list of transactions.

    Pure math — no I/O. Caller is responsible for:
    - Converting costs to target_currency
    - Providing all relevant TXs (DB + pending, minus excluded)

    Same-date handling:
    - Within the same date, additions (qty > 0) are processed FIRST,
      then reductions (qty < 0). This prevents transient negative qty.

    Formula (iterative per day-group):
        new_qty = qty + tx_qty
        if new_qty > 0:
            wac = ((wac * qty) + (tx_cost * tx_qty)) / new_qty
        elif new_qty == 0:
            wac = 0
        elif new_qty < 0:
            wac = 0, qty = 0 (clamp — rounding tolerance)

    For reductions: tx_cost = wac_current → WAC stays unchanged.
    """
    wac = Decimal("0")
    qty_pool = Decimal("0")
    qualifying: list[WACQualifyingTX] = []

    sorted_txs = sorted(txs, key=lambda t: (t.date, t.tx_id if t.tx_id is not None else 999_999_999))

    for _date, day_group in groupby(sorted_txs, key=lambda t: t.date):
        day_txs = list(day_group)
        # Additions first (qty > 0), then reductions (qty < 0)
        additions = [t for t in day_txs if t.quantity > 0]
        reductions = [t for t in day_txs if t.quantity < 0]

        for tx in additions + reductions:
            tx_qty = tx.quantity
            effect: str
            unit_cost: Decimal | None

            if tx.is_split_linked:
                # Split/reverse split: never adds or removes economic cost, only
                # redistributes existing total cost (wac * qty_pool) over a new
                # quantity. Bypasses the add/reduce dichotomy below entirely —
                # unlike a real BUY/SELL, unit_cost_converted is not consulted.
                new_qty = qty_pool + tx_qty
                if new_qty > 0:
                    wac = (wac * qty_pool) / new_qty
                else:
                    wac = Decimal("0")
                    new_qty = Decimal("0")
                qty_pool = new_qty
                unit_cost = wac
                effect = "split_rescale"

                qualifying.append(
                    WACQualifyingTX(
                        tx_id=tx.tx_id,
                        type=tx.type,
                        date=tx.date,
                        quantity=tx.quantity,
                        unit_cost=unit_cost,
                        currency=target_currency,
                        effect=effect,
                        running_wac=wac,
                    )
                )
                continue

            if tx_qty > 0:
                # Acquisition
                if tx.cost_basis_mode == "auto":
                    # Auto: shares arrive at current pool cost → pool WAC unchanged
                    unit_cost = wac if qty_pool > 0 else Decimal("0")
                    effect = "add_at_wac"
                elif tx.unit_cost_converted is not None and tx.unit_cost_converted > 0:
                    unit_cost = tx.unit_cost_converted
                    effect = "add"
                else:
                    unit_cost = Decimal("0")
                    effect = "add_zero_cost"
                tx_cost = unit_cost
            else:
                # Reduction — exits at current WAC
                tx_cost = wac
                unit_cost = wac
                effect = "reduce"

            # Update pool
            new_qty = qty_pool + tx_qty

            if new_qty > 0:
                wac = ((wac * qty_pool) + (tx_cost * tx_qty)) / new_qty
            elif new_qty == 0:
                wac = Decimal("0")
            else:
                # Negative (rounding error) → clamp to 0
                wac = Decimal("0")
                new_qty = Decimal("0")

            qty_pool = new_qty

            qualifying.append(
                WACQualifyingTX(
                    tx_id=tx.tx_id,
                    type=tx.type,
                    date=tx.date,
                    quantity=tx.quantity,
                    unit_cost=unit_cost,
                    currency=target_currency,
                    effect=effect,
                    running_wac=wac,
                )
            )

    return WACCalcResult(
        wac_amount=wac,
        wac_currency=target_currency,
        pool_qty=qty_pool,
        qualifying=qualifying,
    )
