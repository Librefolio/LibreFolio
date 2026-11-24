"""The value on receipt of a reward in kind, read from the stored price history (project 79, STK-4b).

One reader for every place that suggests it: the transaction form (STK-2a) and the bulk workspace's «fill from price
history» (STK-4b). The rule is the domain consultant's: the asset's close **of that very day**, never the day before or
after, in the price's own currency (never converted), per unit (the close divided by the quote base quantity, as every
valuation does: ``financial_math.valuation.compute_holding_value``). A day with no close says so; an asset with no stored
price at all says that instead, so the user knows why nothing was filled.
"""

from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Set, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, PriceHistory, Transaction
from backend.app.db.precision import round_computed_value
from backend.app.schemas.common import Currency
from backend.app.schemas.prices import FARewardValueItem, FARewardValueResult, RewardValueStatus
from backend.app.services.financial_math.valuation import compute_holding_value


def reward_unit_value_from_close(close: Optional[Decimal], quote_base_quantity: Optional[int]) -> Optional[Decimal]:
    """The value of one unit from a day's close: the close over the quote base, rounded to what a cost basis keeps.

    None for a missing close or one that is not positive: no price, never a value of 0 the history does not hold.
    """
    if close is None or not close.is_finite() or close <= 0:
        return None
    return round_computed_value(compute_holding_value(Decimal(1), close, quote_base_quantity), Transaction, "cost_basis_override")


async def reward_values_on_receipt(session: AsyncSession, items: Sequence[FARewardValueItem]) -> List[FARewardValueResult]:
    """The value on receipt of each reward asked for, in the order asked: one read of the prices, one of the assets."""
    if not items:
        return []
    asset_ids = sorted({item.asset_id for item in items})
    dates = sorted({item.date for item in items})

    asset_rows = await session.execute(select(Asset.id, Asset.quote_base_quantity).where(Asset.id.in_(asset_ids)))
    quote_bases: Dict[int, Optional[int]] = {row.id: row.quote_base_quantity for row in asset_rows}

    with_history_rows = await session.execute(select(PriceHistory.asset_id).where(PriceHistory.asset_id.in_(asset_ids)).distinct())
    with_history: Set[int] = {row.asset_id for row in with_history_rows}

    price_rows = await session.execute(select(PriceHistory.asset_id, PriceHistory.date, PriceHistory.close, PriceHistory.currency).where(PriceHistory.asset_id.in_(asset_ids), PriceHistory.date.in_(dates)))
    closes: Dict[Tuple[int, date_type], Tuple[Optional[Decimal], str]] = {(row.asset_id, row.date): (row.close, row.currency) for row in price_rows}

    results: List[FARewardValueResult] = []
    for item in items:
        if item.asset_id not in quote_bases or item.asset_id not in with_history:
            results.append(FARewardValueResult(asset_id=item.asset_id, date=item.date, status=RewardValueStatus.NO_HISTORY))
            continue
        close, currency = closes.get((item.asset_id, item.date), (None, ""))
        value = reward_unit_value_from_close(close, quote_bases[item.asset_id])
        if value is None or not currency:
            results.append(FARewardValueResult(asset_id=item.asset_id, date=item.date, status=RewardValueStatus.NO_PRICE_THAT_DAY))
            continue
        results.append(FARewardValueResult(asset_id=item.asset_id, date=item.date, status=RewardValueStatus.FILLED, value=Currency(code=currency, amount=value)))
    return results
