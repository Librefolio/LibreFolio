"""The broker summary of ``BrokerService`` (``GET /brokers/{id}/summary``)."""

from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from typing import List, Literal, Optional, Union

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    Broker,
    BrokerUserAccess,
    PriceHistory,
    Transaction,
)
from backend.app.schemas.brokers import (
    BRAssetHolding,
    BRSummary,
)
from backend.app.schemas.common import Currency
from backend.app.schemas.wac import WACMissingPairInfo
from backend.app.services.financial_math.average_cost import AverageCost, CostPosition, compute_average_costs, cost_movement_from_transaction
from backend.app.services.financial_math.returns import gain_loss_ratio
from backend.app.services.financial_math.splits import split_linked_ids
from backend.app.services.financial_math.valuation import compute_holding_value
from backend.app.services.transactions.transaction_service import TransactionService


class BrokerSummaryMixin:
    """The broker summary: cash, holdings with their average cost and latest price, the caller's role and share.

    Mixed into ``BrokerService`` (``broker_service.py``), which provides ``session``, ``tx_service`` and, from
    ``BrokerAccessMixin``, ``_check_user_access``.
    """

    session: AsyncSession
    tx_service: TransactionService

    # =========================================================================
    # READ OPERATIONS
    # =========================================================================

    async def get_summary(self, broker_id: int, user_id: int, as_user_id: Union[int, Literal["all"], None] = None, as_of: Optional[date_type] = None) -> Optional[BRSummary]:  # noqa: C901 — sequential fetch/assemble with guard returns + per-holding loop
        """
        Get broker with full summary including balances and holdings.

        Args:
            broker_id: Broker ID
            user_id: Current user ID (always required)
            as_user_id: For superuser - impersonate (int) or "all" for no check
            as_of: The day the summary describes, the user's today; ``date.today()`` when omitted.
                A transaction dated later counts in none of the figures: cash, holdings, average cost.

        Returns:
            BRSummary with cash_balances and holdings, or None if not found
        """
        broker = await self.session.get(Broker, broker_id)
        if not broker:
            return None

        # Determine access check
        skip_access_check = as_user_id == "all"
        check_user_id = user_id if as_user_id is None else (None if skip_access_check else int(as_user_id))

        if not skip_access_check and check_user_id is not None:
            has_access = await self._check_user_access(broker_id, check_user_id)
            if not has_access:
                return None

        # The summary is the broker on the user's day: a transaction dated later counts in none of its figures.
        as_of = as_of or date_type.today()

        # Get cash balances. Currencies with a net-zero balance are still
        # included (as long as they have transaction history) — a currency
        # deposited and then fully invested should stay visible at 0, not
        # disappear entirely.
        cash_dict = await self.tx_service.get_cash_balances(broker_id, as_of=as_of)
        cash_balances = [Currency(code=code, amount=amount) for code, amount in cash_dict.items()]

        # Get asset holdings
        holdings_dict = await self.tx_service.get_asset_holdings(broker_id, as_of=as_of)
        holdings: List[BRAssetHolding] = []

        # Batch-fetch latest prices for all held assets in one query instead of
        # one query per holding (was the dominant N+1 cost of this endpoint).
        held_asset_ids = [asset_id for asset_id, quantity in holdings_dict.items() if quantity != Decimal("0")]
        latest_prices = await self._get_latest_prices_batch(held_asset_ids)
        # Average cost of each holding, in its asset currency (see _holding_average_costs)
        average_costs = await self._holding_average_costs(broker_id, held_asset_ids, as_of=as_of)
        missing_pairs: dict[str, set] = {}
        for average_cost in average_costs.values():
            for missing in average_cost.missing:
                if missing.leg == "report":
                    missing_pairs.setdefault(missing.pair, set()).update(missing.dates)

        for asset_id, quantity in holdings_dict.items():
            if quantity == Decimal("0"):
                continue

            # Get asset info
            asset = await self.session.get(Asset, asset_id)
            if not asset:
                continue

            # Historical cost of the quantity held, in the asset currency: None when part of
            # it is unknown (an unconvertible purchase or a transfer without cost basis).
            position_cost = average_costs.get(asset_id)
            total_cost_amount: Decimal | None = Decimal("0")
            if position_cost is not None and position_cost.steps:
                total_cost_amount = position_cost.steps[-1].cost_report_for(quantity) if position_cost.report_complete else None
            average_cost: Decimal | None = None
            if total_cost_amount is not None:
                average_cost = total_cost_amount / quantity
                # SafeDecimal in BRAssetHolding guarantees fixed-point JSON
                # serialization — no scientific notation reaches the frontend.
                if average_cost == 0:
                    average_cost = Decimal("0")

            # Get current price (from the batch lookup above)
            current_price = latest_prices.get(asset_id)
            current_value = None
            unrealized_pnl = None
            unrealized_pnl_percent = None

            if current_price is not None:
                current_value_amount = compute_holding_value(
                    quantity,
                    current_price,
                    asset.quote_base_quantity,
                )
                current_value = Currency(code=asset.currency, amount=current_value_amount)

                if total_cost_amount is not None:
                    unrealized_pnl_amount = current_value_amount - total_cost_amount
                    unrealized_pnl = Currency(code=asset.currency, amount=unrealized_pnl_amount)

                    unrealized_pnl_ratio = gain_loss_ratio(unrealized_pnl_amount, total_cost_amount, positive_base=False)
                    if unrealized_pnl_ratio is not None:
                        unrealized_pnl_percent = (unrealized_pnl_ratio * 100).quantize(Decimal("0.01"))

            holdings.append(
                BRAssetHolding(
                    asset_id=asset_id,
                    asset_name=asset.display_name,
                    quantity=quantity,
                    total_cost=Currency(code=asset.currency, amount=total_cost_amount) if total_cost_amount is not None else None,
                    average_cost_per_unit=average_cost,
                    current_price=current_price,
                    current_value=current_value,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_percent=unrealized_pnl_percent,
                )
            )

        # Get current user's role and share on this broker
        user_role_value = None
        user_share_value = None
        if not skip_access_check and check_user_id is not None:
            access_stmt = select(BrokerUserAccess).where(
                and_(
                    BrokerUserAccess.broker_id == broker_id,
                    BrokerUserAccess.user_id == check_user_id,
                )
            )
            access_result = await self.session.execute(access_stmt)
            user_access = access_result.scalar_one_or_none()
            if user_access:
                user_role_value = user_access.role.value
                user_share_value = user_access.share_percentage
        elif not skip_access_check:
            # user_id is the actual logged-in user
            access_stmt = select(BrokerUserAccess).where(
                and_(
                    BrokerUserAccess.broker_id == broker_id,
                    BrokerUserAccess.user_id == user_id,
                )
            )
            access_result = await self.session.execute(access_stmt)
            user_access = access_result.scalar_one_or_none()
            if user_access:
                user_role_value = user_access.role.value
                user_share_value = user_access.share_percentage

        return BRSummary(
            id=broker.id,
            name=broker.name,
            description=broker.description,
            portal_url=broker.portal_url,
            icon_url=broker.icon_url,
            default_import_plugin=broker.default_import_plugin,
            allow_cash_overdraft=broker.allow_cash_overdraft,
            allow_asset_shorting=broker.allow_asset_shorting,
            is_active=broker.is_active,
            opened_at=broker.opened_at,
            created_at=broker.created_at,
            updated_at=broker.updated_at,
            cash_balances=cash_balances,
            holdings=holdings,
            missing_fx_pairs=[WACMissingPairInfo(pair=pair, dates=sorted(dates)) for pair, dates in sorted(missing_pairs.items())],
            user_role=user_role_value,
            user_share_percentage=user_share_value,
        )

    async def _holding_average_costs(self, broker_id: int, asset_ids: List[int], as_of: Optional[date_type] = None) -> dict[int, AverageCost]:
        """Average cost of each held asset at this broker on ``as_of``, in the asset's own currency.

        One financial_math.average_cost call per asset currency; a purchase paid in another
        currency is converted at its date, and a missing rate is reported, never counted as zero.
        """
        if not asset_ids:
            return {}
        assets = (await self.session.execute(select(Asset).where(Asset.id.in_(asset_ids)))).scalars().all()
        currency_by_asset = {asset.id: asset.currency for asset in assets if asset.currency}
        stmt = select(Transaction).where(Transaction.broker_id == broker_id, Transaction.asset_id.in_(list(currency_by_asset)), Transaction.quantity.is_not(None), Transaction.quantity != 0)
        if as_of is not None:
            stmt = stmt.where(Transaction.date <= as_of)
        rows = (await self.session.execute(stmt.order_by(Transaction.date, Transaction.id))).scalars().all()
        split_linked = await split_linked_ids(self.session, rows)

        movements_by_asset: dict[int, list] = {}
        for row in rows:
            movement = cost_movement_from_transaction(row, asset_currency=currency_by_asset[row.asset_id], split_linked=row.id in split_linked)
            if movement is not None:
                movements_by_asset.setdefault(row.asset_id, []).append(movement)

        positions_by_currency: dict[str, list[CostPosition]] = {}
        for asset_id, movements in movements_by_asset.items():
            currency = currency_by_asset[asset_id]
            positions_by_currency.setdefault(currency, []).append(CostPosition(key=asset_id, asset_currency=currency, movements=tuple(movements)))
        average_costs: dict[int, AverageCost] = {}
        for currency, positions in positions_by_currency.items():
            average_costs.update(await compute_average_costs(self.session, positions, report_currency=currency, asset_leg=False))
        return average_costs

    async def _get_latest_prices_batch(self, asset_ids: List[int]) -> dict:
        """Batch lookup of the latest price per asset — a single query for N
        assets instead of N round-trips (avoids the N+1 pattern previously in
        `get_summary`'s per-holding loop, the dominant cost of
        GET /brokers/{id}/summary for brokers with many holdings)."""
        if not asset_ids:
            return {}
        latest_date_subq = select(PriceHistory.asset_id, func.max(PriceHistory.date).label("max_date")).where(PriceHistory.asset_id.in_(asset_ids)).group_by(PriceHistory.asset_id).subquery()
        stmt = select(PriceHistory.asset_id, PriceHistory.close).join(
            latest_date_subq,
            and_(PriceHistory.asset_id == latest_date_subq.c.asset_id, PriceHistory.date == latest_date_subq.c.max_date),
        )
        result = await self.session.execute(stmt)
        return {asset_id: close for asset_id, close in result.all() if close}
