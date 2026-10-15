"""Database reads behind the planner source: custody quantities, latest saved prices and cash balances of the selected brokers, up to the snapshot date."""

from __future__ import annotations

from collections import defaultdict
from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Broker, BrokerUserAccess, PriceHistory, Transaction


async def load_holding_rows(
    session: AsyncSession,
    *,
    accesses: dict[int, tuple[BrokerUserAccess, Broker]],
    as_of_date: date_type,
) -> list:
    quantity_sum = func.sum(Transaction.quantity)
    if not accesses:
        return []
    return (
        await session.execute(
            select(
                Transaction.broker_id,
                Transaction.asset_id,
                quantity_sum.label("custody_quantity"),
            )
            .where(
                Transaction.broker_id.in_(accesses),
                Transaction.asset_id.is_not(None),
                Transaction.date <= as_of_date,
            )
            .group_by(Transaction.broker_id, Transaction.asset_id)
            .having(quantity_sum != 0)
        )
    ).all()


async def load_latest_prices(
    session: AsyncSession,
    *,
    candidate_asset_ids: set[int],
    as_of_date: date_type,
) -> dict[int, PriceHistory]:
    prices: dict[int, PriceHistory] = {}
    if not candidate_asset_ids:
        return prices

    latest_price_dates = (
        select(
            PriceHistory.asset_id.label("asset_id"),
            func.max(PriceHistory.date).label("latest_date"),
        )
        .where(
            PriceHistory.asset_id.in_(candidate_asset_ids),
            PriceHistory.close.is_not(None),
            PriceHistory.date <= as_of_date,
        )
        .group_by(PriceHistory.asset_id)
        .subquery()
    )
    price_rows = (
        await session.execute(
            select(PriceHistory).join(
                latest_price_dates,
                and_(
                    PriceHistory.asset_id == latest_price_dates.c.asset_id,
                    PriceHistory.date == latest_price_dates.c.latest_date,
                ),
            ),
        )
    ).scalars()
    return {price.asset_id: price for price in price_rows}


async def load_cash_by_broker(
    session: AsyncSession,
    *,
    accesses: dict[int, tuple[BrokerUserAccess, Broker]],
    as_of_date: date_type,
) -> dict[int, dict[str, Decimal]]:
    cash_by_broker: dict[int, dict[str, Decimal]] = defaultdict(dict)
    if not accesses:
        return cash_by_broker

    cash_rows = (
        await session.execute(
            select(
                Transaction.broker_id,
                Transaction.currency,
                func.sum(Transaction.amount).label("cash_amount"),
            )
            .where(
                Transaction.broker_id.in_(accesses),
                Transaction.currency.is_not(None),
                Transaction.date <= as_of_date,
            )
            .group_by(Transaction.broker_id, Transaction.currency)
        )
    ).all()
    for broker_id, currency, amount in cash_rows:
        if currency is not None:
            cash_by_broker[broker_id][currency] = amount
    return cash_by_broker
