"""BRIM duplicate detection: the extracted transactions that already stand in the database."""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, Optional

import structlog
from sqlalchemy import and_, or_, select

from backend.app.db.models import Transaction, TransactionType
from backend.app.schemas.brim import (
    BRIMAssetMapping,
    BRIMDuplicateLevel,
    BRIMDuplicateMatch,
    BRIMDuplicateReport,
    BRIMTXDuplicateCandidate,
    is_fake_asset_id,
)
from backend.app.schemas.transactions.transactions import TXCreateItem

logger = structlog.get_logger(__name__)


_WHITESPACE_RE = re.compile(r"\s+")


def _description_key(description: Optional[str]) -> str:
    """
    Comparison key for a transaction description.

    Bank exports wrap and re-wrap the same text, so the identical movement can come
    back as "DT EMISS." in one file and "DTEMISS." in another. Comparing raw strings
    demotes such a pair to a *possible* duplicate and asks the user to arbitrate a
    difference that is not there. Whitespace and case carry no meaning here.
    """
    if not description:
        return ""
    return _WHITESPACE_RE.sub("", description).upper()


# A deposit or a withdrawal that a promote merged into a pair is stored as one leg of a
# CASH_TRANSFER (two brokers) or of an FX_CONVERSION (two currencies). Exported again — an
# export "since the last one" starts on the last day it covered — the same movement comes back
# as a plain DEPOSIT or WITHDRAWAL and must still be recognised.
_MERGED_LEG_TYPES = (TransactionType.CASH_TRANSFER, TransactionType.FX_CONVERSION)


# The widest gap two quantities of one holding may have (the fixed tolerance before W-B51): the rule below is never looser.
QUANTITY_MATCH_BOUND = Decimal("0.0001")


def _decimal_places(value: Decimal) -> int:
    """The decimals ``value`` states, trailing zeros not counted: a stored ``0.000153000`` (a column pads its reads) states 6."""
    exponent = value.normalize().as_tuple().exponent
    return max(0, -exponent) if isinstance(exponent, int) else 0


def _same_quantity(stored: Optional[Decimal], incoming: Decimal) -> bool:
    """Whether a stored quantity and a report's are the same holding (W-B51, decision D-W51-1).

    Equal once both are rounded half-up to the decimals of the less precise one, and never further apart than
    ``QUANTITY_MATCH_BOUND``: a report that rounds (``0.00015``) still matches the value stored from another
    (``0.000153``), while two recurring crypto buys of one day (``0.00015123``, ``0.00015098``) stay two rows; ``10`` and
    ``10.4`` stay apart as before. A stored quantity that reads back unreadable (``None``, W-B74) matches nothing.
    """
    if stored is None or not stored.is_finite() or not incoming.is_finite():
        return False
    if abs(stored - incoming) > QUANTITY_MATCH_BOUND:
        return False
    unit = Decimal(1).scaleb(-min(_decimal_places(stored), _decimal_places(incoming)))
    return stored.quantize(unit, rounding=ROUND_HALF_UP) == incoming.quantize(unit, rounding=ROUND_HALF_UP)


async def detect_tx_duplicates(  # noqa: C901 — TODO(P2-refactor): extract per-tx match evaluation from loop
    transactions: List[TXCreateItem],
    broker_id: int,
    session,
    asset_mappings: Optional[List[BRIMAssetMapping]] = None,
) -> BRIMDuplicateReport:
    """
    Detect potential duplicate transactions in the database.

    For each parsed transaction, queries the DB for existing transactions with:
    - Same broker_id (scoped to broker)
    - Same type; a DEPOSIT or WITHDRAWAL also looks at the legs of CASH_TRANSFER and
      FX_CONVERSION pairs, where a promote stored the same movement
    - Same date
    - Same quantity, at the precision of the less precise of the two (``_same_quantity``, W-B51)
    - Same cash amount and currency (if present)
    - Same asset_id (only if asset was auto-resolved with 1 candidate)

    Match levels (ascending confidence):
    - POSSIBLE: key fields match, asset not resolved
    - POSSIBLE_WITH_ASSET: key fields match, asset auto-resolved and matches
    - LIKELY: key fields + description match, asset not resolved
    - LIKELY_WITH_ASSET: key fields + description match, asset auto-resolved

    On a merged leg the description matches when it contains the incoming one: merging a pair
    joins the descriptions of its two sides.

    Args:
        transactions: List of parsed TXCreateItem
        broker_id: Target broker ID
        session: AsyncSession for database queries
        asset_mappings: Optional list of BRIMAssetMapping for asset resolution

    Returns:
        BRIMDuplicateReport with categorized transactions
    """
    tx_unique_indices = []
    tx_possible_duplicates = []
    tx_likely_duplicates = []

    # Tolerance for the cash comparison (a currency's cents); quantities go through _same_quantity (W-B51)
    AMOUNT_TOLERANCE = Decimal("0.01")

    # Build fake_id -> real_asset_id mapping from asset_mappings
    # Only includes mappings where exactly 1 candidate was found (auto-resolved)
    resolved_assets: Dict[int, int] = {}
    if asset_mappings:
        for mapping in asset_mappings:
            if mapping.selected_asset_id is not None:
                resolved_assets[mapping.fake_asset_id] = mapping.selected_asset_id

    for idx, tx in enumerate(transactions):
        # Determine if this transaction has a resolved asset
        real_asset_id: Optional[int] = None
        asset_is_resolved = False

        if tx.asset_id is not None:
            if is_fake_asset_id(tx.asset_id):
                # Check if this fake ID was resolved to a real asset
                if tx.asset_id in resolved_assets:
                    real_asset_id = resolved_assets[tx.asset_id]
                    asset_is_resolved = True
            else:
                # Already a real asset ID
                real_asset_id = tx.asset_id
                asset_is_resolved = True

        # Build query conditions
        merged_leg_types = _MERGED_LEG_TYPES if tx.type in (TransactionType.DEPOSIT, TransactionType.WITHDRAWAL) else ()
        conditions = [
            Transaction.broker_id == broker_id,
            Transaction.type.in_([tx.type, *merged_leg_types]),
            Transaction.date == tx.date,
        ]

        # If asset is resolved, filter by asset_id for more precise matching. Rows with no
        # asset at all stay in scope: the same movement imported before a plugin learned to
        # attach its instrument sits in the DB unallocated, and excluding it would hand the
        # user that very row back as "new" on every single re-import.
        if asset_is_resolved and real_asset_id is not None:
            conditions.append(or_(Transaction.asset_id == real_asset_id, Transaction.asset_id.is_(None)))

        stmt = select(Transaction).where(and_(*conditions))
        result = await session.execute(stmt)
        existing_txs = result.scalars().all()

        matches = []
        for existing in existing_txs:
            if not _same_quantity(existing.quantity, tx.quantity):
                continue

            # Check cash match (if applicable)
            cash_match = True
            if tx.cash:
                if existing.amount is None or existing.currency is None:
                    cash_match = False
                elif existing.currency != tx.cash.code:
                    cash_match = False
                elif abs(existing.amount - tx.cash.amount) > AMOUNT_TOLERANCE:
                    cash_match = False

            if not cash_match:
                continue

            # Determine match level based on:
            # 1. Whether asset is resolved (more confident)
            # 2. Whether description matches (even more confident)
            tx_desc = _description_key(tx.description)
            existing_desc = _description_key(existing.description)
            merged_leg = existing.type != tx.type
            desc_matches = bool(tx_desc) and (tx_desc == existing_desc or (merged_leg and tx_desc in existing_desc))

            if asset_is_resolved and existing.asset_id is not None:
                # Asset resolved on both sides - use WITH_ASSET levels
                if desc_matches:
                    match_level = BRIMDuplicateLevel.LIKELY_WITH_ASSET
                else:
                    match_level = BRIMDuplicateLevel.POSSIBLE_WITH_ASSET
            else:
                # Asset not resolved - use base levels
                if desc_matches:
                    match_level = BRIMDuplicateLevel.LIKELY
                else:
                    match_level = BRIMDuplicateLevel.POSSIBLE

            matches.append(
                BRIMDuplicateMatch(
                    existing_tx_id=existing.id,
                    tx_date=existing.date,
                    tx_type=existing.type,
                    tx_quantity=existing.quantity,
                    tx_cash_amount=existing.amount,
                    tx_cash_currency=existing.currency,
                    tx_description=existing.description,
                    match_level=match_level,
                )
            )

        if not matches:
            tx_unique_indices.append(idx)
        else:
            # Categorize by highest match level found
            # Priority: LIKELY_WITH_ASSET > LIKELY > POSSIBLE_WITH_ASSET > POSSIBLE
            likely_with_asset = [m for m in matches if m.match_level == BRIMDuplicateLevel.LIKELY_WITH_ASSET]
            likely = [m for m in matches if m.match_level == BRIMDuplicateLevel.LIKELY]

            candidate = BRIMTXDuplicateCandidate(tx_row_index=idx, tx_parsed=tx, tx_existing_matches=matches)

            # If any LIKELY level match, put in likely_duplicates
            if likely_with_asset or likely:
                tx_likely_duplicates.append(candidate)
            else:
                tx_possible_duplicates.append(candidate)

    return BRIMDuplicateReport(
        tx_unique_indices=tx_unique_indices,
        tx_possible_duplicates=tx_possible_duplicates,
        tx_likely_duplicates=tx_likely_duplicates,
    )
