"""Database reads behind the planner source: custody quantities, latest saved prices and cash balances of the selected brokers, up to the snapshot date."""

from __future__ import annotations

from collections import defaultdict
from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Broker, BrokerUserAccess, PriceHistory, Transaction
from backend.app.services.financial_math.ledger_totals import position_quantities
from backend.app.services.financial_math.native_cash import cash_movement_from_transaction, native_balances


async def load_holding_rows(
    session: AsyncSession,
    *,
    accesses: dict[int, tuple[BrokerUserAccess, Broker]],
    as_of_date: date_type,
) -> list[tuple[int, int, Decimal]]:
    """The custody quantity of every position of the accessible brokers on ``as_of_date``, without zero lines.

    The rows are summed in Python by ``ledger_totals.position_quantities``, never with ``SUM`` in SQL: a Numeric on
    SQLite goes through a float. Sorted by (broker, asset).
    """
    if not accesses:
        return []
    rows = (
        await session.execute(
            select(Transaction.broker_id, Transaction.asset_id, Transaction.quantity, Transaction.date).where(
                Transaction.broker_id.in_(accesses),
                Transaction.asset_id.is_not(None),
                Transaction.date <= as_of_date,
            )
        )
    ).all()
    return [(broker_id, asset_id, quantity) for broker_id, by_asset in sorted(position_quantities(rows).items()) for asset_id, quantity in sorted(by_asset.items()) if quantity != 0]


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
    """The cash of every accessible broker in each of its currencies on ``as_of_date``.

    The rows are summed in Python by ``native_cash.native_balances``, never with ``SUM`` in SQL; a currency whose rows
    cancel out keeps its line at zero.
    """
    cash_by_broker: dict[int, dict[str, Decimal]] = defaultdict(dict)
    if not accesses:
        return cash_by_broker

    rows = (
        await session.execute(
            select(Transaction.id, Transaction.type, Transaction.date, Transaction.broker_id, Transaction.asset_id, Transaction.currency, Transaction.amount).where(
                Transaction.broker_id.in_(accesses),
                Transaction.currency.is_not(None),
                Transaction.date <= as_of_date,
            )
        )
    ).all()
    movements = [movement for row in rows if (movement := cash_movement_from_transaction(row)) is not None]
    for broker_id, by_currency in native_balances(movements).items():
        cash_by_broker[broker_id].update(by_currency)
    return cash_by_broker
