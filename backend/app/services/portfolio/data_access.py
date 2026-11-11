"""Data access and shared helpers of ``PortfolioService``: base currency, the engine run, brokers, transactions, assets and the data-quality lookups."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date as date_type
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    Broker,
    BrokerUserAccess,
    Transaction,
    TransactionType,
)
from backend.app.schemas.common import DateSpan, is_canonical_iso_currency
from backend.app.schemas.wac import WACMissingPairInfo
from backend.app.services.accounts.settings_service import get_effective_base_currency
from backend.app.services.financial_math.holding_window import closing_move
from backend.app.services.portfolio import engine_facts
from backend.app.utils.day_spans import merged_spans


class PortfolioDataMixin:
    """Data access and shared helpers of ``PortfolioService``: base currency, the engine run, brokers, transactions, assets and the data-quality lookups.

    Mixed into ``PortfolioService`` (``portfolio_service.py``), which provides ``db``.
    """

    db: AsyncSession

    async def _get_base_currency(self, user_id: int) -> str:
        """Effective base currency: per-user setting, global default, EUR (P0-1)."""
        return await get_effective_base_currency(self.db, user_id)

    async def _engine_run(
        self,
        *,
        user_id: int,
        broker_ids: list[int] | None,
        date_from: date_type | None,
        date_to: date_type | None,
        target_currency: str,
        include_candles: bool = False,
        apply_ownership_share: bool = True,
    ):
        """The one engine run of the report, the Performance table and the positions chart (FB-14).

        Every caller asks the same run — the replay from t=0, with the position frames, the BUY funding split and the
        positions at the end of ``date_from`` — so the requests of one page share the engine's blob-cache key: the first
        builds the run, the others read it, or wait on it (single-flight). Each caller serializes only what its query asks.
        The candles stay a flag of their own: their OHLC work is kept off the ordinary reports. ``apply_ownership_share``
        False counts every broker whole (the broker page, MF6-3): a run of its own, under its own key.
        """
        from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine  # noqa: PLC0415

        return await PortfolioCalculationEngine(self.db).calculate(
            user_id=user_id,
            broker_ids=broker_ids,
            date_from=None,  # always from t=0 for correct cumulative values
            date_to=date_to,
            target_currency=target_currency,
            include_candles=include_candles,
            include_acquisition_funding=True,
            period_start=date_from,
            include_positions=True,
            apply_ownership_share=apply_ownership_share,
        )

    async def _closing_transactions(
        self,
        user_id: int,
        lot_txns_by_key: Mapping[tuple[int, int], Sequence[Transaction]],
        lot_moves: Mapping[tuple[int, int], Sequence],
    ) -> dict[tuple[int, int], tuple[str, Optional[int]]]:
        """How each position that ever closed last closed (MF-CB): ``(type, destination broker)`` by position.

        The closing movement is ``holding_window.closing_move``'s; its type is the row's ``closed_by``. A TRANSFER names
        the broker of its paired leg (both legs carry ``related_transaction_id``) when the user can read that broker,
        whether or not the report asked for it; an orphan leg, or another user's broker, names none.
        """
        closing_txs: dict[tuple[int, int], Transaction] = {}
        for key, moves in lot_moves.items():
            move = closing_move(moves)
            if move is not None:
                closing_txs[key] = next(tx for tx in lot_txns_by_key[key] if (tx.id or 0) == move.order)
        partner_ids = {tx.related_transaction_id for tx in closing_txs.values() if tx.type == TransactionType.TRANSFER and tx.related_transaction_id is not None}
        partner_brokers: dict[int, int] = {}
        if partner_ids:
            readable = {access.broker_id for access in await self._get_user_broker_access(user_id, None)}
            rows = await self.db.execute(select(Transaction.id, Transaction.broker_id).where(Transaction.id.in_(partner_ids)))
            partner_brokers = {tx_id: broker_id for tx_id, broker_id in rows.all() if broker_id in readable}
        return {
            key: (
                str(getattr(tx.type, "value", tx.type)),
                partner_brokers.get(tx.related_transaction_id) if tx.type == TransactionType.TRANSFER and tx.related_transaction_id is not None else None,
            )
            for key, tx in closing_txs.items()
        }

    async def _get_user_broker_access(
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
    ) -> list[BrokerUserAccess]:
        """Return BrokerUserAccess rows for a user, optionally filtered by broker_ids."""
        stmt = select(BrokerUserAccess).where(BrokerUserAccess.user_id == user_id)
        if broker_ids:
            stmt = stmt.where(BrokerUserAccess.broker_id.in_(broker_ids))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _get_broker(self, broker_id: int) -> Broker | None:
        return await self.db.get(Broker, broker_id)

    async def _get_brokers_map(self, broker_ids: set[int]) -> dict[int, Broker]:
        if not broker_ids:
            return {}
        stmt = select(Broker).where(Broker.id.in_(broker_ids))
        result = await self.db.execute(stmt)
        return {broker.id: broker for broker in result.scalars().all()}

    async def _get_transactions(
        self,
        broker_id: int,
        tx_types: set[TransactionType] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
    ) -> list[Transaction]:
        stmt = select(Transaction).where(Transaction.broker_id == broker_id)
        if tx_types:
            stmt = stmt.where(Transaction.type.in_(tx_types))
        if date_from:
            stmt = stmt.where(Transaction.date >= date_from)
        if date_to:
            stmt = stmt.where(Transaction.date <= date_to)
        stmt = stmt.order_by(Transaction.date, Transaction.id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _get_asset(self, asset_id: int) -> Asset | None:
        return await self.db.get(Asset, asset_id)

    async def _get_assets_map(self, asset_ids: set[int]) -> dict[int, Asset]:
        if not asset_ids:
            return {}
        stmt = select(Asset).where(Asset.id.in_(asset_ids))
        result = await self.db.execute(stmt)
        return {asset.id: asset for asset in result.scalars().all()}

    async def _missing_cost_basis_assets(self, engine_result: Any) -> list[tuple[int, str]]:
        """(asset_id, name) of the assets with an acquisition of unknown cost in the engine's replay."""
        asset_ids = sorted({asset_id for (asset_id, _broker_id), average_cost in getattr(engine_result, "average_costs", {}).items() if average_cost.unknown_cost_movement_ids})
        if not asset_ids:
            return []
        assets = await self._get_assets_map(set(asset_ids))
        return [(asset_id, assets[asset_id].display_name if asset_id in assets else f"Asset {asset_id}") for asset_id in asset_ids]

    async def _invalid_split_assets(self, engine_result: Any) -> list[tuple[int, str]]:
        """(asset_id, name) of the assets with a SPLIT event whose stored ratio the engine counted as missing (MF-D4)."""
        asset_ids = sorted({event.asset_id for event in getattr(engine_result, "invalid_split_events", [])})
        if not asset_ids:
            return []
        assets = await self._get_assets_map(set(asset_ids))
        return [(asset_id, assets[asset_id].display_name if asset_id in assets else f"Asset {asset_id}") for asset_id in asset_ids]

    async def _held_asset_quote_facts(self, engine_result: Any) -> list[engine_facts.HeldAssetQuoteFacts]:
        """The assets held at the end of the period (a position above the dust threshold), each with its stored
        currency, read in one query: what the data-quality report's asset quote check needs (E-19b's NON_ISO_CURRENCY)."""
        asset_ids = sorted({ps.asset_id for ps in engine_result.position_states_end if ps.quantity > engine_facts._QUANTITY_DUST_THRESHOLD})
        if not asset_ids:
            return []
        assets = (await self.db.execute(select(Asset).where(Asset.id.in_(asset_ids)).order_by(Asset.id))).scalars().all()
        return [engine_facts.HeldAssetQuoteFacts(asset_id=asset.id, name=asset.display_name, currency=asset.currency) for asset in assets]

    @staticmethod
    def _non_iso_currency_assets(facts: Sequence[engine_facts.HeldAssetQuoteFacts]) -> list[tuple[int, str, str]]:
        """(asset_id, name, stored currency) of the held assets whose currency is not an ISO 4217 code as stored (E-19b):
        ``978``, ``EURO`` or ``eur``, which an earlier version saved as written."""
        return [(fact.asset_id, fact.name, fact.currency) for fact in facts if not is_canonical_iso_currency(fact.currency)]

    @staticmethod
    def _merge_missing_pairs(items: list[WACMissingPairInfo]) -> list[WACMissingPairInfo]:
        merged: dict[str, set[date_type]] = defaultdict(set)
        spans: dict[str, list[tuple[date_type, date_type]]] = defaultdict(list)
        for item in items:
            merged[item.pair].update(item.dates)
            spans[item.pair].extend((span.start, span.end) for span in item.ranges)
        return [WACMissingPairInfo(pair=pair, dates=sorted(dates), ranges=[DateSpan(start=first, end=last) for first, last in merged_spans(spans[pair])]) for pair, dates in sorted(merged.items())]

    async def _get_configured_fx_pair_sets(self) -> tuple[set[str], set[str]]:
        from backend.app.services.financial_math.portfolio.data_quality import load_configured_fx_pair_sets  # noqa: PLC0415 — same lazy engine import as the methods below

        return await load_configured_fx_pair_sets(self.db)
