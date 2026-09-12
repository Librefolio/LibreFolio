"""Read-only Asset catalog and OWNER full-custody facts for allocation editors."""

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
    PortfolioAllocationSourceCashBalance,
    PortfolioAllocationSourceCashSource,
    PortfolioAllocationSourceContext,
    PortfolioAllocationSourceQuote,
)
from backend.app.utils.datetime_utils import utcnow


class PortfolioAllocationSourceAccessError(PermissionError):
    """Requested cash brokers are not OWNER-accessible to the caller."""

    def __init__(self, broker_ids: list[int]) -> None:
        self.broker_ids = tuple(sorted(broker_ids))
        super().__init__(f"Cash broker selection is not fully OWNER-accessible: {', '.join(map(str, self.broker_ids))}")


async def build_portfolio_allocation_source(
    session: AsyncSession,
    *,
    user_id: int,
    as_of_date: date_type,
    selected_cash_broker_ids: list[int],
) -> PortfolioAllocationSource:
    """Build catalog candidates, OWNER custody contexts, and native cash facts."""
    access_rows, accesses = await _load_owner_accesses(session, user_id=user_id)
    _ensure_cash_brokers_accessible(selected_cash_broker_ids=selected_cash_broker_ids, accesses=accesses)
    holding_rows = await _load_holding_rows(session, accesses=accesses, as_of_date=as_of_date)
    candidate_assets, candidate_asset_ids = await _load_candidate_assets(session, holding_rows=holding_rows)
    prices = await _load_latest_prices(session, candidate_asset_ids=candidate_asset_ids, as_of_date=as_of_date)
    total_counts, own_counts = await _load_usage_counts(
        session,
        accesses=accesses,
        candidate_asset_ids=candidate_asset_ids,
    )
    contexts_by_asset = _build_contexts_by_asset(holding_rows=holding_rows, accesses=accesses)
    source_assets = _build_source_assets(
        candidate_assets=candidate_assets,
        contexts_by_asset=contexts_by_asset,
        prices=prices,
        total_counts=total_counts,
        own_counts=own_counts,
        as_of_date=as_of_date,
    )
    cash_by_broker = await _load_cash_by_broker(session, accesses=accesses, as_of_date=as_of_date)
    cash_sources = _build_cash_sources(access_rows=access_rows, cash_by_broker=cash_by_broker)

    return PortfolioAllocationSource(
        generated_at=utcnow(),
        as_of_date=as_of_date,
        assets=source_assets,
        cash_sources=cash_sources,
        selected_cash_balances=_build_selected_cash_balances(
            selected_cash_broker_ids=selected_cash_broker_ids,
            cash_by_broker=cash_by_broker,
        ),
    )


async def _load_owner_accesses(
    session: AsyncSession,
    *,
    user_id: int,
) -> tuple[list, dict[int, tuple[BrokerUserAccess, Broker]]]:
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

    accesses: dict[int, tuple[BrokerUserAccess, Broker]] = {}
    for access, broker in access_rows:
        if broker.id is None:
            raise RuntimeError("Persisted broker is missing its id")
        accesses[broker.id] = (access, broker)
    return access_rows, accesses


def _ensure_cash_brokers_accessible(
    *,
    selected_cash_broker_ids: list[int],
    accesses: dict[int, tuple[BrokerUserAccess, Broker]],
) -> None:
    inaccessible_cash_broker_ids = sorted(set(selected_cash_broker_ids) - accesses.keys())
    if inaccessible_cash_broker_ids:
        raise PortfolioAllocationSourceAccessError(inaccessible_cash_broker_ids)


async def _load_holding_rows(
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


async def _load_candidate_assets(
    session: AsyncSession,
    *,
    holding_rows: list,
) -> tuple[list[Asset], set[int]]:
    all_assets = list((await session.execute(select(Asset).order_by(Asset.display_name, Asset.id))).scalars())
    assets_by_id = {asset.id: asset for asset in all_assets if asset.id is not None}
    current_asset_ids = {asset_id for _, asset_id, _ in holding_rows if asset_id is not None}
    missing_asset_ids = current_asset_ids - assets_by_id.keys()
    if missing_asset_ids:
        raise RuntimeError(f"Allocation source references missing assets: {sorted(missing_asset_ids)}")

    candidate_assets = [asset for asset in all_assets if asset.id is not None and (asset.active or asset.id in current_asset_ids)]
    candidate_asset_ids = {asset.id for asset in candidate_assets if asset.id is not None}
    return candidate_assets, candidate_asset_ids


async def _load_latest_prices(
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


async def _load_usage_counts(
    session: AsyncSession,
    *,
    accesses: dict[int, tuple[BrokerUserAccess, Broker]],
    candidate_asset_ids: set[int],
) -> tuple[dict[int, int], dict[int, int]]:
    total_counts: dict[int, int] = {}
    if candidate_asset_ids:
        total_counts = {asset_id: count for asset_id, count in (await session.execute(select(Transaction.asset_id, func.count(Transaction.id)).where(Transaction.asset_id.in_(candidate_asset_ids)).group_by(Transaction.asset_id))).all() if asset_id is not None}

    positive_owner_broker_ids = {broker_id for broker_id, (access, _broker) in accesses.items() if access.share_percentage > 0}
    own_counts: dict[int, int] = {}
    if candidate_asset_ids and positive_owner_broker_ids:
        own_counts = {
            asset_id: count
            for asset_id, count in (
                await session.execute(
                    select(Transaction.asset_id, func.count(Transaction.id))
                    .where(
                        Transaction.asset_id.in_(candidate_asset_ids),
                        Transaction.broker_id.in_(positive_owner_broker_ids),
                    )
                    .group_by(Transaction.asset_id)
                )
            ).all()
            if asset_id is not None
        }
    return total_counts, own_counts


def _build_contexts_by_asset(
    *,
    holding_rows: list,
    accesses: dict[int, tuple[BrokerUserAccess, Broker]],
) -> dict[int, list[PortfolioAllocationSourceContext]]:
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
                broker_icon_url=broker.icon_url,
                broker_portal_url=broker.portal_url,
                broker_default_import_plugin=broker.default_import_plugin,
                ownership_share_percent=access.share_percentage * Decimal("100"),
                custody_quantity=custody_quantity,
            )
        )
    return contexts_by_asset


def _build_source_assets(
    *,
    candidate_assets: list[Asset],
    contexts_by_asset: dict[int, list[PortfolioAllocationSourceContext]],
    prices: dict[int, PriceHistory],
    total_counts: dict[int, int],
    own_counts: dict[int, int],
    as_of_date: date_type,
) -> list[PortfolioAllocationSourceAsset]:
    source_assets: list[PortfolioAllocationSourceAsset] = []
    for asset in candidate_assets:
        if asset.id is None:
            continue
        asset_id = asset.id
        contexts = contexts_by_asset.get(asset_id, [])
        price = prices.get(asset_id)
        reference_date = price.date if price else None
        usage_scope = "owned" if own_counts.get(asset_id, 0) > 0 else "other_users" if total_counts.get(asset_id, 0) > 0 else "observed"
        source_assets.append(
            PortfolioAllocationSourceAsset(
                asset_id=asset_id,
                instrument_key=f"asset:{asset_id}",
                candidate_key=f"asset:{asset_id}:candidate",
                name=asset.display_name,
                ticker=asset.identifier_ticker,
                asset_type=asset.asset_type.value,
                icon_url=asset.icon_url,
                active=asset.active,
                usage_scope=usage_scope,
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
    return source_assets


async def _load_cash_by_broker(
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


def _build_cash_sources(
    *,
    access_rows: list,
    cash_by_broker: dict[int, dict[str, Decimal]],
) -> list[PortfolioAllocationSourceCashSource]:
    cash_sources: list[PortfolioAllocationSourceCashSource] = []
    for access, broker in access_rows:
        if broker.id is None:
            continue
        cash_sources.append(
            PortfolioAllocationSourceCashSource(
                broker_id=broker.id,
                broker_name=broker.name,
                broker_icon_url=broker.icon_url,
                broker_portal_url=broker.portal_url,
                broker_default_import_plugin=broker.default_import_plugin,
                ownership_share_percent=access.share_percentage * Decimal("100"),
                balances=[PortfolioAllocationSourceCashBalance(currency=currency, amount=amount) for currency, amount in sorted(cash_by_broker.get(broker.id, {}).items())],
            )
        )
    return cash_sources


def _build_selected_cash_balances(
    *,
    selected_cash_broker_ids: list[int],
    cash_by_broker: dict[int, dict[str, Decimal]],
) -> list[PortfolioAllocationSourceCashBalance]:
    selected_cash_by_currency: dict[str, Decimal] = {}
    for broker_id in selected_cash_broker_ids:
        for currency, amount in cash_by_broker.get(broker_id, {}).items():
            selected_cash_by_currency[currency] = selected_cash_by_currency.get(currency, Decimal("0")) + amount
    return [PortfolioAllocationSourceCashBalance(currency=currency, amount=amount) for currency, amount in sorted(selected_cash_by_currency.items())]
