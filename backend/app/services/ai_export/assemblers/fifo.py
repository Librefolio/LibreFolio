"""Shared FIFO per-lot row assembly for Broker and Portfolio AI Export tasks.

Discovers scoped transaction assets, maps authoritative ``LotSummarySchema`` rows to the
``AiExportFifoLotRow`` contract, filters eligibility (open/partial always; closed lots only
within the previous 3 calendar months relative to snapshot_as_of), and produces a
deterministic compact selection (7 largest open/partial by residual cost basis + 3 most
recently closed, backfilling unused quota from the other category up to a fixed limit of 10).

``lot_id`` is the internal FIFO engine identifier. It is carried on ``FifoLotCandidate`` only
to provide a stable deterministic tie-breaker during selection/sorting; it is never present on
``AiExportFifoLotRow`` and must never be serialized.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Transaction
from backend.app.schemas.ai_export import (
    AiExportFifoLotDirection,
    AiExportFifoLotRow,
    AiExportFifoLotStatus,
    AiExportFifoLotValueSource,
    AiExportSelectionMetadata,
)
from backend.app.schemas.common import Currency
from backend.app.services.ai_export.assemblers.shared import subtract_calendar_months
from backend.app.services.ai_export.sampling import round_percentage

TransactionAssetIdsLoader = Callable[[AsyncSession, Sequence[int], date], Awaitable[set[int]]]

#: Deterministic compact-selection tuning. Fixed by product decision (see task spec):
#: target the 7 largest open/partial lots by absolute residual cost basis plus the 3 most
#: recently closed lots, backfilling unused quota from the other category up to a limit of 10.
COMPACT_OPEN_QUOTA = 7
COMPACT_CLOSED_QUOTA = 3
COMPACT_TOTAL_LIMIT = 10
CLOSED_LOT_CUTOFF_MONTHS = 3

FIFO_LOT_SELECTION_RULE = "largest_open_residual_plus_most_recent_closed"


async def default_transaction_asset_ids_loader(
    session: AsyncSession,
    broker_ids: Sequence[int],
    snapshot_as_of: date,
) -> set[int]:
    """Bulk-discover every distinct transacted asset_id for the given brokers through snapshot_as_of.

    Single bulk query (no per-lot query) so historical assets no longer held are never
    silently omitted from FIFO lot scope discovery.
    """
    if not broker_ids:
        return set()
    result = await session.execute(
        select(Transaction.asset_id)
        .where(
            Transaction.broker_id.in_(sorted(set(broker_ids))),
            Transaction.date <= snapshot_as_of,
            Transaction.asset_id.is_not(None),
        )
        .distinct()
    )
    return {int(asset_id) for asset_id in result.scalars().all() if asset_id is not None}


def closed_lot_cutoff_date(snapshot_as_of: date) -> date:
    """Fully closed lots with closing_date on/after this date are eligible; earlier ones are excluded."""
    return subtract_calendar_months(snapshot_as_of, CLOSED_LOT_CUTOFF_MONTHS)


def _decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _optional_decimal(value: Any) -> Decimal | None:
    return None if value is None else _decimal(value)


def lot_status(lot: Any) -> AiExportFifoLotStatus:
    open_quantity = _decimal(getattr(lot, "open_quantity", None))
    realized_quantity = _decimal(getattr(lot, "realized_quantity", None))
    if open_quantity.is_zero():
        return AiExportFifoLotStatus.CLOSED
    if realized_quantity.is_zero():
        return AiExportFifoLotStatus.OPEN
    return AiExportFifoLotStatus.PARTIAL


def lot_residual_cost_basis(lot: Any) -> Decimal:
    """original_cost * open_quantity / original_quantity; 0 for fully closed lots."""
    open_quantity = abs(_decimal(getattr(lot, "open_quantity", None)))
    if open_quantity.is_zero():
        return Decimal("0")
    original_quantity = abs(_decimal(getattr(lot, "original_quantity", None)))
    if original_quantity.is_zero():
        return Decimal("0")
    return _decimal(getattr(lot, "original_cost", None)) * open_quantity / original_quantity


def asset_residual_cost_basis(lots: Sequence[Any]) -> Decimal:
    """Sum of ``lot_residual_cost_basis`` across every lot in the sequence (fully closed lots contribute 0)."""
    return sum((lot_residual_cost_basis(lot) for lot in lots), start=Decimal("0"))


def has_nonzero_open_lot(lots: Sequence[Any]) -> bool:
    """True if any lot in the sequence still carries a non-zero open (unrealized) quantity."""
    return any(not _decimal(getattr(lot, "open_quantity", None)).is_zero() for lot in lots)


def lot_is_eligible(lot: Any, *, cutoff: date) -> bool:
    """Open/partial lots are always eligible; closed lots are eligible only if closing_date >= cutoff."""
    if lot_status(lot) != AiExportFifoLotStatus.CLOSED:
        return True
    closing_date = getattr(lot, "closing_date", None)
    return closing_date is not None and closing_date >= cutoff


def _money(value: Any, currency_code: str) -> Currency:
    return Currency(code=currency_code, amount=_decimal(value))


def _optional_money(value: Any, currency_code: str) -> Currency | None:
    amount = _optional_decimal(value)
    return None if amount is None else Currency(code=currency_code, amount=amount)


@dataclass(frozen=True)
class FifoLotCandidate:
    """Internal selection candidate. ``lot_id`` is a final deterministic tie-breaker only and
    is never present on ``row``/serialized output."""

    lot_id: int
    asset_id: int
    status: AiExportFifoLotStatus
    residual_cost_basis: Decimal
    closing_date: date | None
    row: AiExportFifoLotRow


def build_fifo_lot_candidate(
    lot: Any,
    *,
    asset_id: int,
    currency_code: str,
    asset_name: str,
    asset_symbol: str | None,
    opening_broker_name: str | None,
) -> FifoLotCandidate:
    """Map one authoritative ``LotSummarySchema`` row to the AI row contract (no lot_id/opening_transaction_id).

    ``asset_id`` is supplied by the caller (the asset-scoped LotsAnalysisService query context)
    rather than read off ``lot`` so this stays robust to lightweight lot fakes/rows that omit it.
    """
    status = lot_status(lot)
    residual_cost_basis = lot_residual_cost_basis(lot)
    closing_date = lot.closing_date if status == AiExportFifoLotStatus.CLOSED else None
    value_source_raw = getattr(lot, "value_source", None)
    row = AiExportFifoLotRow(
        asset_id=asset_id,
        asset_name=asset_name,
        asset_symbol=asset_symbol,
        opening_broker_id=lot.opening_broker_id,
        opening_broker_name=opening_broker_name,
        opening_date=lot.opening_date,
        closing_date=closing_date,
        direction=AiExportFifoLotDirection(lot.direction),
        status=status,
        opening_unit_price=_money(lot.opening_unit_price, currency_code),
        original_quantity=_decimal(lot.original_quantity),
        open_quantity=_decimal(lot.open_quantity),
        realized_quantity=_decimal(lot.realized_quantity),
        original_cost=_money(lot.original_cost, currency_code),
        residual_cost_basis=Currency(code=currency_code, amount=residual_cost_basis),
        cumulative_proceeds=_money(lot.cumulative_proceeds, currency_code),
        open_value=_optional_money(getattr(lot, "open_value", None), currency_code),
        realized_pnl=_money(lot.realized_pnl, currency_code),
        unrealized_pnl=_optional_money(getattr(lot, "market_pnl", None), currency_code),
        total_pnl=_optional_money(getattr(lot, "total_pnl", None), currency_code),
        income=_money(getattr(lot, "asset_income", None), currency_code),
        fees=_money(getattr(lot, "allocated_fees", None), currency_code),
        taxes=_money(getattr(lot, "allocated_taxes", None), currency_code),
        net_total_pnl=_optional_money(getattr(lot, "net_total_pnl", None), currency_code),
        value_source=(AiExportFifoLotValueSource(value_source_raw) if value_source_raw is not None else None),
        states=list(getattr(lot, "states", None) or []),
    )
    return FifoLotCandidate(
        lot_id=int(lot.lot_id),
        asset_id=int(asset_id),
        status=status,
        residual_cost_basis=residual_cost_basis,
        closing_date=closing_date,
        row=row,
    )


def collect_fifo_candidates(
    lots_by_asset: Mapping[int, Sequence[Any]],
    *,
    currency_code: str,
    cutoff: date,
    assets: Mapping[int, Any],
    brokers: Mapping[int, Any],
) -> list[FifoLotCandidate]:
    """Map+filter every eligible lot across every asset into a deterministically sorted candidate list."""
    candidates: list[FifoLotCandidate] = []
    for asset_id in sorted(lots_by_asset):
        asset = assets.get(asset_id)
        asset_name = str(getattr(asset, "display_name", None) or f"Asset {asset_id}")
        asset_symbol = getattr(asset, "identifier_ticker", None)
        for lot in lots_by_asset[asset_id]:
            if not lot_is_eligible(lot, cutoff=cutoff):
                continue
            broker = brokers.get(lot.opening_broker_id)
            candidates.append(
                build_fifo_lot_candidate(
                    lot,
                    asset_id=asset_id,
                    currency_code=currency_code,
                    asset_name=asset_name,
                    asset_symbol=asset_symbol,
                    opening_broker_name=getattr(broker, "name", None),
                )
            )
    candidates.sort(key=lambda candidate: (candidate.asset_id, candidate.row.opening_date, candidate.lot_id))
    return candidates


def select_compact_fifo_lots(
    candidates: Sequence[FifoLotCandidate],
    *,
    limit: int = COMPACT_TOTAL_LIMIT,
    open_quota: int = COMPACT_OPEN_QUOTA,
    closed_quota: int = COMPACT_CLOSED_QUOTA,
) -> list[FifoLotCandidate]:
    """Deterministic 7 open/partial + 3 closed compact selection, backfilling unused quota
    from the other category up to ``limit`` where possible.

    Open/partial candidates are ranked by descending absolute residual cost basis; closed
    candidates are ranked by descending (most recent first) closing_date. ``lot_id`` is the
    final tie-breaker in both rankings for full determinism.
    """
    open_candidates = sorted(
        (candidate for candidate in candidates if candidate.status != AiExportFifoLotStatus.CLOSED),
        key=lambda candidate: (-abs(candidate.residual_cost_basis), candidate.lot_id),
    )
    closed_candidates = sorted(
        (candidate for candidate in candidates if candidate.status == AiExportFifoLotStatus.CLOSED),
        key=lambda candidate: (
            -(candidate.closing_date.toordinal() if candidate.closing_date is not None else 0),
            candidate.lot_id,
        ),
    )

    open_take = min(open_quota, len(open_candidates))
    closed_take = min(closed_quota, len(closed_candidates))
    selected_open = list(open_candidates[:open_take])
    selected_closed = list(closed_candidates[:closed_take])

    open_deficit = open_quota - open_take
    closed_deficit = closed_quota - closed_take
    if open_deficit > 0:
        selected_closed.extend(closed_candidates[closed_take : closed_take + open_deficit])
    elif closed_deficit > 0:
        selected_open.extend(open_candidates[open_take : open_take + closed_deficit])

    return (selected_open + selected_closed)[:limit]


def build_fifo_lot_selection_metadata(
    *,
    rule: str,
    limit: int,
    candidates: Sequence[FifoLotCandidate],
    selected: Sequence[FifoLotCandidate],
    asset_nav_weights: Mapping[int, Decimal],
) -> AiExportSelectionMetadata:
    """Selection metadata for the compact FIFO lot selection.

    Entity counts describe lot rows (matching entity_limit semantics: total/included eligible
    lot rows). NAV weight percentages are aggregated per unique asset (not per lot) to avoid
    double counting assets that contribute multiple lot rows, consistent with the NAV-weight
    convention used by other AI Export selection metadata.
    """
    total_asset_ids = {candidate.asset_id for candidate in candidates}
    included_asset_ids = {candidate.asset_id for candidate in selected}
    total_weight = sum((abs(asset_nav_weights.get(asset_id, Decimal("0"))) for asset_id in total_asset_ids), start=Decimal("0"))
    included_weight = sum((abs(asset_nav_weights.get(asset_id, Decimal("0"))) for asset_id in included_asset_ids), start=Decimal("0"))
    return AiExportSelectionMetadata(
        rule=rule,
        limit=limit,
        total_entity_count=len(candidates),
        included_entity_count=len(selected),
        total_nav_weight_pct=round_percentage(total_weight),
        included_nav_weight_pct=round_percentage(included_weight),
    )


__all__ = [
    "CLOSED_LOT_CUTOFF_MONTHS",
    "COMPACT_CLOSED_QUOTA",
    "COMPACT_OPEN_QUOTA",
    "COMPACT_TOTAL_LIMIT",
    "FIFO_LOT_SELECTION_RULE",
    "FifoLotCandidate",
    "TransactionAssetIdsLoader",
    "asset_residual_cost_basis",
    "build_fifo_lot_candidate",
    "build_fifo_lot_selection_metadata",
    "closed_lot_cutoff_date",
    "collect_fifo_candidates",
    "default_transaction_asset_ids_loader",
    "has_nonzero_open_lot",
    "lot_is_eligible",
    "lot_residual_cost_basis",
    "lot_status",
    "select_compact_fifo_lots",
]
