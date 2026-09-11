"""Read-only OWNER/full-custody facts for allocation editors."""

from __future__ import annotations

from collections import defaultdict
from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, Broker, BrokerUserAccess, PriceHistory, Transaction, UserRole
from backend.app.schemas.portfolio import (
    PortfolioAllocationSource,
    PortfolioAllocationSourceAsset,
    PortfolioAllocationSourceContext,
    PortfolioAllocationSourceQuote,
)
from backend.app.utils.datetime_utils import utcnow


async def build_portfolio_allocation_source(
    session: AsyncSession,
    *,
    user_id: int,
    as_of_date: date_type,
) -> PortfolioAllocationSource:
    """Build one canonical asset group with every OWNER custody context."""
    access_rows = (
        await session.execute(
            select(BrokerUserAccess, Broker)
            .join(Broker, Broker.id == BrokerUserAccess.broker_id)
            .where(
                BrokerUserAccess.user_id == user_id,
                BrokerUserAccess.role == UserRole.OWNER,
            )
            .order_by(Broker.name, Broker.id)
        )
    ).all()
    if not access_rows:
        return PortfolioAllocationSource(
            generated_at=utcnow(),
            as_of_date=as_of_date,
            assets=[],
        )

    accesses: dict[int, tuple[BrokerUserAccess, Broker]] = {}
    for access, broker in access_rows:
        if broker.id is None:
            raise RuntimeError("Persisted broker is missing its id")
        accesses[broker.id] = (access, broker)

    quantity_sum = func.sum(Transaction.quantity)
    holding_rows = (
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
    if not holding_rows:
        return PortfolioAllocationSource(
            generated_at=utcnow(),
            as_of_date=as_of_date,
            assets=[],
        )

    asset_ids = {asset_id for _, asset_id, _ in holding_rows if asset_id is not None}
    assets = {asset.id: asset for asset in (await session.execute(select(Asset).where(Asset.id.in_(asset_ids)))).scalars() if asset.id is not None}
    missing_asset_ids = asset_ids - assets.keys()
    if missing_asset_ids:
        raise RuntimeError(f"Allocation source references missing assets: {sorted(missing_asset_ids)}")

    latest_price_dates = (
        select(
            PriceHistory.asset_id.label("asset_id"),
            func.max(PriceHistory.date).label("latest_date"),
        )
        .where(
            PriceHistory.asset_id.in_(asset_ids),
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
            )
        )
    ).scalars()
    prices = {price.asset_id: price for price in price_rows}

    contexts_by_asset: dict[int, list[PortfolioAllocationSourceContext]] = defaultdict(list)
    for broker_id, asset_id, custody_quantity in holding_rows:
        if asset_id is None:
            continue
        access, broker = accesses[broker_id]
        contexts_by_asset[asset_id].append(
            PortfolioAllocationSourceContext(
                context_key=f"asset:{asset_id}:broker:{broker_id}",
                broker_id=broker_id,
                broker_name=broker.name,
                ownership_share_percent=access.share_percentage * Decimal("100"),
                custody_quantity=custody_quantity,
            )
        )

    source_assets: list[PortfolioAllocationSourceAsset] = []
    for asset_id, contexts in contexts_by_asset.items():
        asset = assets[asset_id]
        price = prices.get(asset_id)
        reference_date = price.date if price else None
        source_assets.append(
            PortfolioAllocationSourceAsset(
                asset_id=asset_id,
                instrument_key=f"asset:{asset_id}",
                name=asset.display_name,
                ticker=asset.identifier_ticker,
                asset_type=asset.asset_type.value,
                icon_url=asset.icon_url,
                quote=PortfolioAllocationSourceQuote(
                    raw_price=price.close if price else None,
                    currency=price.currency if price else asset.currency,
                    quote_base_quantity=asset.quote_base_quantity or 1,
                    reference_date=reference_date,
                    source=price.source_plugin_key if price else None,
                    days_before_requested=(as_of_date - reference_date).days if reference_date else None,
                ),
                contexts=sorted(contexts, key=lambda item: (item.broker_name.casefold(), item.broker_id)),
            )
        )

    source_assets.sort(key=lambda item: (item.name.casefold(), item.asset_id))
    return PortfolioAllocationSource(
        generated_at=utcnow(),
        as_of_date=as_of_date,
        assets=source_assets,
    )
