from __future__ import annotations

import bisect
from collections import defaultdict
from dataclasses import dataclass
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetEvent, AssetEventType, Broker, BrokerUserAccess, PriceHistory, Transaction
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import (
    BrokerWACHistoryPoint,
    CumulativeWACHistoryPoint,
    DataQualityIssue,
    DataQualityReport,
    GanttSegmentSchema,
    IssueCode,
    IssueDomain,
    IssueSeverity,
    LotAnalysisType,
    LotCalculationStatus,
    LotPriceHistoryPoint,
    LotReturnHistoryPoint,
    LotsAnalysisMetadata,
    LotsAnalysisResponse,
    LotSummarySchema,
    LotTimelineEventKind,
    LotTimelineEventSchema,
    LotValueHistoryPoint,
    ReferencePriceSource,
)
from backend.app.services.fifo_lot_engine import (
    FifoDataQualityIssue,
    FifoEngineResult,
    FifoEvent,
    FifoLot,
    FragmentInterval,
    LotClosure,
    ReferencePriceResolution,
    run_fifo_lot_engine,
)
from backend.app.services.fx import convert_bulk
from backend.app.services.settings_service import get_global_setting
from backend.app.utils.financial.wac_utils import WACInputTX, compute_wac_from_txlist

_WARNING_ISSUE_CODES = {
    IssueCode.REFERENCE_PRICE_FALLBACK,
    IssueCode.REFERENCE_PRICE_UNAVAILABLE,
}

_CUSTODY_KINDS = {
    LotTimelineEventKind.BUY,
    LotTimelineEventKind.ADJUSTMENT_IN,
    LotTimelineEventKind.TRANSFER_DEPART,
    LotTimelineEventKind.TRANSFER_ARRIVE,
}


@dataclass(frozen=True, slots=True)
class _PricePoint:
    price: Decimal
    currency: str
    resolved_date: date_type
    source: ReferencePriceSource


class _PriceHistoryLookup:
    def __init__(self, prices: Sequence[PriceHistory]) -> None:
        self._rows = sorted((row for row in prices if row.close is not None), key=lambda row: row.date)
        self._dates = [row.date for row in self._rows]

    def resolve(self, query_date: date_type) -> _PricePoint | None:
        if not self._rows:
            return None
        idx = bisect.bisect_right(self._dates, query_date) - 1
        if idx < 0:
            return None
        row = self._rows[idx]
        return _PricePoint(
            price=row.close if row.close is not None else Decimal("0"),
            currency=row.currency,
            resolved_date=row.date,
            source="exact" if row.date == query_date else "fallback",
        )

    def latest(self) -> _PricePoint | None:
        if not self._rows:
            return None
        last = self._rows[-1]
        return _PricePoint(price=last.close if last.close is not None else Decimal("0"), currency=last.currency, resolved_date=last.date, source="exact")


class _FxRateResolver:
    def __init__(self, target_currency: str) -> None:
        self.target_currency = target_currency
        self._needs: list[tuple[str, date_type]] = []
        self._seen: set[tuple[str, date_type]] = set()
        self._rates: dict[tuple[str, date_type], Decimal] = {}

    def need(self, currency: str | None, as_of_date: date_type) -> None:
        if not currency or currency == self.target_currency:
            return
        key = (currency, as_of_date)
        if key in self._seen:
            return
        self._seen.add(key)
        self._needs.append(key)

    async def load(self, session: AsyncSession) -> None:
        if not self._needs:
            return
        conversions = [(Currency(code=currency, amount=Decimal("1")), self.target_currency, as_of_date) for currency, as_of_date in self._needs]
        results, _errors = await convert_bulk(session, conversions, raise_on_error=False)
        for idx, key in enumerate(self._needs):
            result = results[idx] if idx < len(results) else None
            if result is None:
                continue
            converted, _rate_date, _backfilled = result
            self._rates[key] = converted.amount

    def convert(self, amount: Decimal | None, currency: str | None, as_of_date: date_type) -> Decimal | None:
        if amount is None:
            return None
        if not currency or currency == self.target_currency:
            return amount
        rate = self._rates.get((currency, as_of_date))
        if rate is None:
            return None
        return amount * rate


class LotsAnalysisService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_lots_analysis(
        self,
        user_id: int,
        asset_id: int,
        broker_ids: list[int] | None,
        date_from: date_type | None,
        date_to: date_type | None,
        target_currency: str | None,
        selected_lot_ids: list[int] | None,
        requested_analyses: list[str | LotAnalysisType],
    ) -> LotsAnalysisResponse:
        normalized_analyses = [analysis if isinstance(analysis, LotAnalysisType) else LotAnalysisType(str(analysis)) for analysis in requested_analyses]
        if not normalized_analyses:
            raise ValueError("requested_analyses must not be empty")

        target_currency = target_currency or await self._get_base_currency()
        actual_to = date_to or date_type.today()
        asset = await self.db.get(Asset, asset_id)
        if asset is None:
            raise ValueError(f"Asset {asset_id} not found")

        scope_broker_ids = await self._get_scope_broker_ids(user_id=user_id, broker_ids=broker_ids)
        if not scope_broker_ids:
            return self._empty_response(
                asset_id=asset_id,
                target_currency=target_currency,
                requested_analyses=normalized_analyses,
                broker_ids=[],
                selected_lot_ids=selected_lot_ids,
                requested_date_from=date_from,
                requested_date_to=actual_to,
                computed_date_from=None,
                computed_date_to=actual_to,
                status="UNAVAILABLE",
            )

        transactions = await self._load_transactions(asset_id=asset_id, scope_broker_ids=scope_broker_ids, date_to=actual_to)
        if not transactions:
            return self._empty_response(
                asset_id=asset_id,
                target_currency=target_currency,
                requested_analyses=normalized_analyses,
                broker_ids=scope_broker_ids,
                selected_lot_ids=selected_lot_ids,
                requested_date_from=date_from,
                requested_date_to=actual_to,
                computed_date_from=None,
                computed_date_to=actual_to,
                status="UNAVAILABLE",
            )

        computed_from = transactions[0].date
        split_ratios_by_tx_id = await self._load_split_ratios(transactions)
        broker_shorting = await self._load_broker_shorting(scope_broker_ids)
        prices = await self._load_prices(asset_id=asset_id, date_to=actual_to)
        price_lookup = _PriceHistoryLookup(prices)

        def reference_price_lookup(resolved_asset_id: int, opened_at: date_type) -> ReferencePriceResolution | None:
            if resolved_asset_id != asset_id:
                return None
            resolved = price_lookup.resolve(opened_at)
            if resolved is None:
                return None
            return ReferencePriceResolution(price=resolved.price, source=resolved.source)

        engine_result = run_fifo_lot_engine(
            transactions=transactions,
            broker_shorting=broker_shorting,
            split_ratios_by_tx_id=split_ratios_by_tx_id,
            reference_price_lookup=reference_price_lookup,
        )

        lots_by_id = {lot.lot_id: lot for lot in engine_result.lots}
        selected_ids = self._resolve_selected_lot_ids(selected_lot_ids, lots_by_id)
        fragments_by_lot = self._group_fragments(engine_result.fragment_intervals)
        closures_by_lot = self._group_closures(engine_result.closures)
        tx_by_id = {tx.id: tx for tx in transactions if tx.id is not None}
        display_from = date_from or computed_from

        fx_resolver = _FxRateResolver(target_currency)
        self._collect_fx_needs(
            fx_resolver=fx_resolver,
            analyses=normalized_analyses,
            lots_by_id=lots_by_id,
            selected_ids=selected_ids,
            transactions=transactions,
            price_lookup=price_lookup,
            prices=prices,
            fragments=engine_result.fragment_intervals,
            events=engine_result.classified_events,
            closures=engine_result.closures,
            split_ratios_by_tx_id=split_ratios_by_tx_id,
            actual_to=actual_to,
            computed_from=computed_from,
        )
        await fx_resolver.load(self.db)

        data_quality = self._build_data_quality_report(engine_result.issues)
        history_dates = list(_date_range(computed_from, actual_to))
        active_price_dates = history_dates if self._needs_market_series(normalized_analyses) else [actual_to]
        market_prices = self._build_market_price_map(price_lookup, fx_resolver, active_price_dates)
        wac_context = self._build_wac_context(
            transactions=transactions,
            split_ratios_by_tx_id=split_ratios_by_tx_id,
            asset_currency=asset.currency,
            target_currency=target_currency,
            fx_resolver=fx_resolver,
        )

        lots = None
        if LotAnalysisType.LOT_SUMMARY in normalized_analyses:
            lots = self._build_lot_summaries(
                engine_result=engine_result,
                lots_by_id=lots_by_id,
                selected_ids=selected_ids,
                fx_resolver=fx_resolver,
                market_prices=market_prices,
                price_lookup=price_lookup,
                closures_by_lot=closures_by_lot,
            )

        gantt_segments = None
        if LotAnalysisType.GANTT_TOPOLOGY in normalized_analyses:
            gantt_segments = self._build_gantt_segments(engine_result.fragment_intervals, selected_ids, lots_by_id, fx_resolver)

        lot_events = self._build_lot_event_rows(
            engine_result=engine_result,
            selected_ids=selected_ids,
            tx_by_id=tx_by_id,
            fx_resolver=fx_resolver,
            lots_by_id=lots_by_id,
        )

        custody_history = None
        if LotAnalysisType.CUSTODY_HISTORY in normalized_analyses:
            custody_history = [row for row in lot_events if row.kind in _CUSTODY_KINDS]

        event_history = None
        if LotAnalysisType.EVENT_HISTORY in normalized_analyses:
            event_history = lot_events

        value_history = None
        if LotAnalysisType.VALUE_HISTORY in normalized_analyses:
            value_history = self._trim_dates(
                self._build_value_history(
                    selected_ids=selected_ids,
                    lots_by_id=lots_by_id,
                    fragments_by_lot=fragments_by_lot,
                    closures_by_lot=closures_by_lot,
                    market_prices=market_prices,
                    history_dates=history_dates,
                    fx_resolver=fx_resolver,
                ),
                display_from,
                actual_to,
            )

        return_history = None
        if LotAnalysisType.RETURN_HISTORY in normalized_analyses:
            return_history = self._trim_dates(
                self._build_return_history(
                    selected_ids=selected_ids,
                    lots_by_id=lots_by_id,
                    market_prices=market_prices,
                    price_lookup=price_lookup,
                    fx_resolver=fx_resolver,
                    history_dates=history_dates,
                    closures_by_lot=closures_by_lot,
                ),
                display_from,
                actual_to,
            )

        price_history = None
        if LotAnalysisType.PRICE_HISTORY in normalized_analyses:
            price_history = self._trim_dates(
                self._build_price_history(
                    selected_ids=selected_ids,
                    lots_by_id=lots_by_id,
                    market_prices=market_prices,
                    history_dates=history_dates,
                    target_currency=target_currency,
                    closures_by_lot=closures_by_lot,
                ),
                display_from,
                actual_to,
            )

        broker_wac_history = None
        if LotAnalysisType.BROKER_WAC_HISTORY in normalized_analyses:
            broker_wac_history = self._trim_dates(
                self._build_broker_wac_history(scope_broker_ids, wac_context, history_dates, target_currency),
                display_from,
                actual_to,
            )

        cumulative_wac_history = None
        if LotAnalysisType.CUMULATIVE_WAC_HISTORY in normalized_analyses:
            cumulative_wac_history = self._trim_dates(
                self._build_cumulative_wac_history(wac_context, history_dates, target_currency),
                display_from,
                actual_to,
            )

        return LotsAnalysisResponse(
            asset_id=asset_id,
            target_currency=target_currency,
            calculation_status=engine_result.calculation_status,
            calculation_metadata=LotsAnalysisMetadata(
                broker_ids=scope_broker_ids,
                selected_lot_ids=selected_ids if selected_lot_ids is not None else None,
                requested_analyses=normalized_analyses,
                requested_date_from=date_from,
                requested_date_to=actual_to,
                computed_date_from=computed_from,
                computed_date_to=actual_to,
                generated_at=date_type.today(),
            ),
            data_quality=data_quality,
            lots=lots,
            gantt_segments=gantt_segments,
            custody_history=custody_history,
            lot_events=event_history,
            value_history=value_history,
            return_history=return_history,
            price_history=price_history,
            broker_wac_history=broker_wac_history,
            cumulative_wac_history=cumulative_wac_history,
        )

    async def _get_base_currency(self) -> str:
        setting = await get_global_setting("base_currency", self.db)
        return setting.value if setting else "EUR"

    async def _get_scope_broker_ids(self, user_id: int, broker_ids: list[int] | None) -> list[int]:
        stmt = select(BrokerUserAccess.broker_id).where(BrokerUserAccess.user_id == user_id)
        if broker_ids:
            stmt = stmt.where(BrokerUserAccess.broker_id.in_(broker_ids))
        rows = (await self.db.execute(stmt)).scalars().all()
        return sorted(set(rows))

    async def _load_transactions(self, asset_id: int, scope_broker_ids: Sequence[int], date_to: date_type) -> list[Transaction]:
        stmt = select(Transaction).where(Transaction.asset_id == asset_id).where(Transaction.broker_id.in_(scope_broker_ids)).where(Transaction.date <= date_to).where(Transaction.quantity.is_not(None)).where(Transaction.quantity != 0).order_by(Transaction.date, Transaction.id)
        return list((await self.db.execute(stmt)).scalars().all())

    async def _load_split_ratios(self, transactions: Sequence[Transaction]) -> dict[int, Decimal]:
        split_candidate_ids = [tx.id for tx in transactions if tx.id is not None and tx.asset_event_id is not None]
        if not split_candidate_ids:
            return {}
        stmt = select(Transaction.id, AssetEvent.value).join(AssetEvent, Transaction.asset_event_id == AssetEvent.id).where(Transaction.id.in_(split_candidate_ids)).where(AssetEvent.type == AssetEventType.SPLIT)
        rows = (await self.db.execute(stmt)).all()
        return dict(rows)

    async def _load_broker_shorting(self, scope_broker_ids: Sequence[int]) -> dict[int, bool]:
        stmt = select(Broker.id, Broker.allow_asset_shorting).where(Broker.id.in_(scope_broker_ids))
        rows = (await self.db.execute(stmt)).all()
        return dict(rows)

    async def _load_prices(self, asset_id: int, date_to: date_type) -> list[PriceHistory]:
        stmt = select(PriceHistory).where(PriceHistory.asset_id == asset_id).where(PriceHistory.date <= date_to).where(PriceHistory.close.is_not(None)).order_by(PriceHistory.date)
        return list((await self.db.execute(stmt)).scalars().all())

    def _empty_response(
        self,
        *,
        asset_id: int,
        target_currency: str,
        requested_analyses: list[LotAnalysisType],
        broker_ids: list[int],
        selected_lot_ids: list[int] | None,
        requested_date_from: date_type | None,
        requested_date_to: date_type | None,
        computed_date_from: date_type | None,
        computed_date_to: date_type | None,
        status: LotCalculationStatus,
    ) -> LotsAnalysisResponse:
        return LotsAnalysisResponse(
            asset_id=asset_id,
            target_currency=target_currency,
            calculation_status=status,
            calculation_metadata=LotsAnalysisMetadata(
                broker_ids=broker_ids,
                selected_lot_ids=selected_lot_ids,
                requested_analyses=requested_analyses,
                requested_date_from=requested_date_from,
                requested_date_to=requested_date_to,
                computed_date_from=computed_date_from,
                computed_date_to=computed_date_to,
                generated_at=date_type.today(),
            ),
            data_quality=DataQualityReport(issues=[]),
        )

    def _resolve_selected_lot_ids(self, selected_lot_ids: list[int] | None, lots_by_id: dict[int, FifoLot]) -> list[int]:
        if selected_lot_ids is None:
            return list(lots_by_id)
        missing = [lot_id for lot_id in selected_lot_ids if lot_id not in lots_by_id]
        if missing:
            raise ValueError(f"Unknown lot ids requested: {missing}")
        return list(dict.fromkeys(selected_lot_ids))

    def _collect_fx_needs(
        self,
        *,
        fx_resolver: _FxRateResolver,
        analyses: Sequence[LotAnalysisType],
        lots_by_id: dict[int, FifoLot],
        selected_ids: Sequence[int],
        transactions: Sequence[Transaction],
        price_lookup: _PriceHistoryLookup,
        prices: Sequence[PriceHistory],
        fragments: Sequence[FragmentInterval],
        events: Sequence[FifoEvent],
        closures: Sequence[LotClosure],
        split_ratios_by_tx_id: dict[int, Decimal],
        actual_to: date_type,
        computed_from: date_type,
    ) -> None:
        tx_by_id = {tx.id: tx for tx in transactions if tx.id is not None}
        if LotAnalysisType.BROKER_WAC_HISTORY in analyses or LotAnalysisType.CUMULATIVE_WAC_HISTORY in analyses:
            for tx in transactions:
                if tx.id in split_ratios_by_tx_id or tx.quantity <= 0:
                    continue
                if str(getattr(tx.type, "value", tx.type)) == "BUY":
                    fx_resolver.need(tx.currency, tx.date)
                elif tx.cost_basis_override is not None:
                    fx_resolver.need(tx.cost_basis_currency, tx.date)

        if LotAnalysisType.LOT_SUMMARY in analyses:
            for lot_id in selected_ids:
                lot = lots_by_id[lot_id]
                fx_resolver.need(lot.currency, lot.opening_date)
                resolved_reference = price_lookup.resolve(lot.opening_date)
                if lot.reference_unit_price is not None and resolved_reference is not None:
                    fx_resolver.need(resolved_reference.currency, resolved_reference.resolved_date)
                for closure in [c for c in closures if c.lot_id == lot_id]:
                    fx_resolver.need(lot.currency, closure.close_date)

        if LotAnalysisType.GANTT_TOPOLOGY in analyses:
            for fragment in fragments:
                if fragment.lot_id in selected_ids:
                    lot = lots_by_id[fragment.lot_id]
                    fx_resolver.need(lot.currency, fragment.start_date)

        if LotAnalysisType.CUSTODY_HISTORY in analyses or LotAnalysisType.EVENT_HISTORY in analyses:
            for event in events:
                tx = tx_by_id.get(event.transaction_id)
                if tx is not None:
                    fx_resolver.need(tx.currency, event.date)
            for closure in closures:
                if closure.lot_id in selected_ids:
                    lot = lots_by_id[closure.lot_id]
                    fx_resolver.need(lot.currency, closure.close_date)

        if self._needs_market_series(analyses):
            current = computed_from
            currencies = {price.currency for price in prices}
            while current <= actual_to:
                for currency in currencies:
                    fx_resolver.need(currency, current)
                current += timedelta(days=1)

    def _needs_market_series(self, analyses: Sequence[LotAnalysisType]) -> bool:
        return any(
            analysis in analyses
            for analysis in (
                LotAnalysisType.LOT_SUMMARY,
                LotAnalysisType.VALUE_HISTORY,
                LotAnalysisType.RETURN_HISTORY,
                LotAnalysisType.PRICE_HISTORY,
            )
        )

    def _build_market_price_map(
        self,
        price_lookup: _PriceHistoryLookup,
        fx_resolver: _FxRateResolver,
        dates: Sequence[date_type],
    ) -> dict[date_type, Decimal | None]:
        market_prices: dict[date_type, Decimal | None] = {}
        for current_date in dates:
            resolved = price_lookup.resolve(current_date)
            if resolved is None:
                market_prices[current_date] = None
                continue
            market_prices[current_date] = fx_resolver.convert(resolved.price, resolved.currency, current_date)
        return market_prices

    def _build_wac_context(
        self,
        *,
        transactions: Sequence[Transaction],
        split_ratios_by_tx_id: dict[int, Decimal],
        asset_currency: str,
        target_currency: str,
        fx_resolver: _FxRateResolver,
    ) -> dict[int | str, list[WACInputTX]]:
        broker_rows: dict[int, list[WACInputTX]] = defaultdict(list)
        all_rows: list[WACInputTX] = []
        for tx in transactions:
            row = self._build_wac_row(
                tx=tx,
                split_linked=tx.id in split_ratios_by_tx_id,
                asset_currency=asset_currency,
                target_currency=target_currency,
                fx_resolver=fx_resolver,
            )
            broker_rows[tx.broker_id].append(row)
            all_rows.append(row)
        out: dict[int | str, list[WACInputTX]] = {broker_id: sorted(rows, key=lambda row: (row.date, row.tx_id or 0)) for broker_id, rows in broker_rows.items()}
        out["__all__"] = sorted(all_rows, key=lambda row: (row.date, row.tx_id or 0))
        return out

    def _build_wac_row(
        self,
        *,
        tx: Transaction,
        split_linked: bool,
        asset_currency: str,
        target_currency: str,
        fx_resolver: _FxRateResolver,
    ) -> WACInputTX:
        tx_type = str(getattr(tx.type, "value", tx.type))
        unit_cost: Decimal | None = None
        original_currency = tx.currency or asset_currency
        if split_linked:
            original_currency = asset_currency
        elif tx.quantity > 0:
            if tx_type == "BUY":
                original_currency = tx.currency or asset_currency
                if tx.amount:
                    total_cost = abs(tx.amount)
                    converted_total = fx_resolver.convert(total_cost, original_currency, tx.date)
                    unit_cost = (converted_total / tx.quantity) if converted_total is not None else (total_cost / tx.quantity)
                else:
                    unit_cost = Decimal("0")
            elif tx.cost_basis_override is not None:
                original_currency = tx.cost_basis_currency or asset_currency
                total_cost = tx.quantity * tx.cost_basis_override
                converted_total = fx_resolver.convert(total_cost, original_currency, tx.date)
                unit_cost = (converted_total / tx.quantity) if converted_total is not None else tx.cost_basis_override
        return WACInputTX(
            tx_id=tx.id,
            type=tx_type,
            date=tx.date,
            quantity=tx.quantity,
            unit_cost_converted=unit_cost,
            original_currency=original_currency,
            cost_basis_mode=None,
            is_split_linked=split_linked,
        )

    def _build_broker_wac_history(
        self,
        broker_ids: Sequence[int],
        wac_context: dict[int | str, list[WACInputTX]],
        history_dates: Sequence[date_type],
        target_currency: str,
    ) -> list[BrokerWACHistoryPoint]:
        points: list[BrokerWACHistoryPoint] = []
        for broker_id in broker_ids:
            txs = wac_context.get(broker_id, [])
            if not txs:
                continue
            points.extend(BrokerWACHistoryPoint(date=point_date, broker_id=broker_id, wac=wac_amount, pool_qty=pool_qty) for point_date, wac_amount, pool_qty in self._compute_wac_series(txs, history_dates, target_currency))
        return points

    def _build_cumulative_wac_history(
        self,
        wac_context: dict[int | str, list[WACInputTX]],
        history_dates: Sequence[date_type],
        target_currency: str,
    ) -> list[CumulativeWACHistoryPoint]:
        txs = wac_context.get("__all__", [])
        if not txs:
            return []
        return [CumulativeWACHistoryPoint(date=point_date, wac=wac_amount, pool_qty=pool_qty) for point_date, wac_amount, pool_qty in self._compute_wac_series(txs, history_dates, target_currency)]

    def _compute_wac_series(
        self,
        txs: Sequence[WACInputTX],
        history_dates: Sequence[date_type],
        target_currency: str,
    ) -> list[tuple[date_type, Decimal, Decimal]]:
        if not txs:
            return []
        txs_sorted = sorted(txs, key=lambda row: (row.date, row.tx_id or 0))
        first_date = txs_sorted[0].date
        prefix: list[WACInputTX] = []
        cursor = 0
        points: list[tuple[date_type, Decimal, Decimal]] = []
        for current_date in history_dates:
            if current_date < first_date:
                continue
            while cursor < len(txs_sorted) and txs_sorted[cursor].date <= current_date:
                prefix.append(txs_sorted[cursor])
                cursor += 1
            calc = compute_wac_from_txlist(prefix, target_currency)
            points.append((current_date, calc.wac_amount, calc.pool_qty))
        return points

    def _build_lot_summaries(
        self,
        *,
        engine_result: FifoEngineResult,
        lots_by_id: dict[int, FifoLot],
        selected_ids: Sequence[int],
        fx_resolver: _FxRateResolver,
        market_prices: dict[date_type, Decimal | None],
        price_lookup: _PriceHistoryLookup,
        closures_by_lot: dict[int, list[LotClosure]],
    ) -> list[LotSummarySchema]:
        latest_market_price = market_prices.get(max(market_prices)) if market_prices else None
        out: list[LotSummarySchema] = []
        for lot_id in selected_ids:
            lot = lots_by_id[lot_id]
            current_custody = [
                {
                    "broker_id": fragment.broker_id,
                    "custody_type": fragment.custody_type,
                    "quantity": fragment.quantity,
                }
                for fragment in engine_result.active_fragments(lot_id=lot_id)
            ]
            converted_proceeds = self._converted_cumulative_proceeds(lot, closures_by_lot.get(lot_id, []), fx_resolver)
            converted_original_cost = fx_resolver.convert(lot.original_cost, lot.currency, lot.opening_date)
            opening_unit_price = fx_resolver.convert(lot.opening_unit_price, lot.currency, lot.opening_date)
            reference_unit_price = None
            resolved_reference = price_lookup.resolve(lot.opening_date)
            if lot.reference_unit_price is not None and resolved_reference is not None:
                reference_unit_price = fx_resolver.convert(lot.reference_unit_price, resolved_reference.currency, resolved_reference.resolved_date)
            open_value = total_value = pnl = relative_return = None
            if latest_market_price is not None:
                open_value = lot.open_quantity * latest_market_price
                proceeds = converted_proceeds or Decimal("0")
                if lot.direction == "LONG":
                    total_value = open_value + proceeds
                    pnl = total_value - (converted_original_cost or Decimal("0"))
                else:
                    total_value = proceeds - open_value
                    pnl = total_value
                if reference_unit_price not in (None, Decimal("0")):
                    relative_return = (latest_market_price / reference_unit_price) - Decimal("1")
            out.append(
                LotSummarySchema(
                    lot_id=lot.lot_id,
                    opening_transaction_id=lot.opening_transaction_id,
                    asset_id=lot.asset_id,
                    direction=lot.direction,
                    opening_broker_id=lot.opening_broker_id,
                    opening_date=lot.opening_date,
                    opening_unit_price=opening_unit_price if opening_unit_price is not None else lot.opening_unit_price,
                    original_quantity=lot.original_quantity,
                    original_cost=converted_original_cost if converted_original_cost is not None else lot.original_cost,
                    currency=lot.currency,
                    open_quantity=lot.open_quantity,
                    realized_quantity=lot.realized_quantity,
                    realized_pnl=self._converted_realized_pnl(lot, closures_by_lot.get(lot_id, []), fx_resolver),
                    cumulative_proceeds=converted_proceeds if converted_proceeds is not None else lot.cumulative_proceeds,
                    reference_unit_price=reference_unit_price,
                    reference_price_source=lot.reference_price_source,
                    states=sorted(engine_result.get_lot_states(lot_id)),
                    current_custody=current_custody,
                    open_value=open_value,
                    total_value=total_value,
                    pnl=pnl,
                    relative_return=relative_return,
                )
            )
        return out

    def _converted_realized_pnl(self, lot: FifoLot, closures: Sequence[LotClosure], fx_resolver: _FxRateResolver) -> Decimal:
        if not closures:
            return Decimal("0")
        total = Decimal("0")
        for closure in closures:
            converted = fx_resolver.convert(closure.realized_pnl, lot.currency, closure.close_date)
            total += converted if converted is not None else closure.realized_pnl
        return total

    def _converted_cumulative_proceeds(self, lot: FifoLot, closures: Sequence[LotClosure], fx_resolver: _FxRateResolver) -> Decimal:
        if lot.direction == "SHORT":
            converted = fx_resolver.convert(lot.cumulative_proceeds, lot.currency, lot.opening_date)
            return converted if converted is not None else lot.cumulative_proceeds
        total = Decimal("0")
        for closure in closures:
            converted = fx_resolver.convert(closure.proceeds, lot.currency, closure.close_date)
            total += converted if converted is not None else closure.proceeds
        return total

    def _build_gantt_segments(
        self,
        fragments: Sequence[FragmentInterval],
        selected_ids: Sequence[int],
        lots_by_id: dict[int, FifoLot],
        fx_resolver: _FxRateResolver,
    ) -> list[GanttSegmentSchema]:
        out: list[GanttSegmentSchema] = []
        selected = set(selected_ids)
        for fragment in fragments:
            if fragment.lot_id not in selected:
                continue
            lot = lots_by_id[fragment.lot_id]
            converted_unit_price = fx_resolver.convert(fragment.unit_price, lot.currency, fragment.start_date)
            out.append(
                GanttSegmentSchema(
                    fragment_id=fragment.fragment_id,
                    lot_id=fragment.lot_id,
                    direction=fragment.direction,
                    custody_type=fragment.custody_type,
                    broker_id=fragment.broker_id,
                    source_broker_id=fragment.source_broker_id,
                    destination_broker_id=fragment.destination_broker_id,
                    quantity=fragment.quantity,
                    unit_price=converted_unit_price if converted_unit_price is not None else fragment.unit_price,
                    start_date=fragment.start_date,
                    end_date=fragment.end_date,
                )
            )
        return out

    def _build_lot_event_rows(
        self,
        *,
        engine_result: FifoEngineResult,
        selected_ids: Sequence[int],
        tx_by_id: dict[int, Transaction],
        fx_resolver: _FxRateResolver,
        lots_by_id: dict[int, FifoLot],
    ) -> list[LotTimelineEventSchema]:
        selected = set(selected_ids)
        rows: list[LotTimelineEventSchema] = []
        rows.extend(self._build_opening_and_split_rows(engine_result, selected, tx_by_id, fx_resolver, lots_by_id))
        rows.extend(self._build_transfer_rows(engine_result.fragment_intervals, selected, lots_by_id, fx_resolver))
        rows.extend(self._build_closure_rows(engine_result.closures, selected, lots_by_id, fx_resolver))
        return sorted(rows, key=lambda row: (row.date, row.lot_id, row.transaction_id, row.kind))

    def _build_opening_and_split_rows(
        self,
        engine_result: FifoEngineResult,
        selected: set[int],
        tx_by_id: dict[int, Transaction],
        fx_resolver: _FxRateResolver,
        lots_by_id: dict[int, FifoLot],
    ) -> list[LotTimelineEventSchema]:
        rows: list[LotTimelineEventSchema] = []
        for event in engine_result.classified_events:
            if event.kind in {"BUY", "ADJUSTMENT_IN"}:
                lot_id = event.transaction_id
                if lot_id not in selected:
                    continue
                tx = tx_by_id.get(event.transaction_id)
                event_currency = tx.currency if tx is not None else lots_by_id[lot_id].currency
                converted_unit_price = fx_resolver.convert(event.unit_price, event_currency, event.date)
                rows.append(
                    LotTimelineEventSchema(
                        lot_id=lot_id,
                        date=event.date,
                        kind=LotTimelineEventKind(event.kind),
                        transaction_id=event.transaction_id,
                        related_transaction_id=event.pair_id,
                        broker_id=event.broker_id,
                        source_broker_id=event.source_broker_id,
                        destination_broker_id=event.destination_broker_id,
                        fragment_id=None,
                        quantity=event.quantity or Decimal("0"),
                        unit_price=converted_unit_price,
                        open_unit_price=None,
                        close_unit_price=None,
                        realized_pnl=None,
                        proceeds=None,
                        ratio=event.ratio,
                    )
                )
            elif event.kind == "SPLIT":
                impacted_lot_ids = self._impacted_lot_ids_for_split(event, engine_result.fragment_intervals)
                for lot_id in sorted(impacted_lot_ids & selected):
                    rows.append(
                        LotTimelineEventSchema(
                            lot_id=lot_id,
                            date=event.date,
                            kind=LotTimelineEventKind.SPLIT,
                            transaction_id=event.transaction_id,
                            related_transaction_id=None,
                            broker_id=event.broker_id,
                            source_broker_id=None,
                            destination_broker_id=None,
                            fragment_id=None,
                            quantity=lots_by_id[lot_id].open_quantity,
                            unit_price=None,
                            open_unit_price=None,
                            close_unit_price=None,
                            realized_pnl=None,
                            proceeds=None,
                            ratio=event.ratio,
                        )
                    )
        return rows

    def _build_transfer_rows(
        self,
        fragments: Sequence[FragmentInterval],
        selected: set[int],
        lots_by_id: dict[int, FifoLot],
        fx_resolver: _FxRateResolver,
    ) -> list[LotTimelineEventSchema]:
        rows: list[LotTimelineEventSchema] = []
        earliest_by_fragment: dict[str, FragmentInterval] = {}
        for fragment in fragments:
            previous = earliest_by_fragment.get(fragment.fragment_id)
            if previous is None or fragment.start_date < previous.start_date:
                earliest_by_fragment[fragment.fragment_id] = fragment
        for fragment_id, fragment in earliest_by_fragment.items():
            if fragment.lot_id not in selected or "/transfer:" not in fragment_id:
                continue
            lot = lots_by_id[fragment.lot_id]
            converted_unit_price = fx_resolver.convert(fragment.unit_price, lot.currency, fragment.start_date)
            if fragment.custody_type == "IN_TRANSIT":
                transfer_pair_id = _parse_transfer_pair_id(fragment_id)
                rows.append(
                    LotTimelineEventSchema(
                        lot_id=fragment.lot_id,
                        date=fragment.start_date,
                        kind=LotTimelineEventKind.TRANSFER_DEPART,
                        transaction_id=transfer_pair_id,
                        related_transaction_id=transfer_pair_id,
                        broker_id=None,
                        source_broker_id=fragment.source_broker_id,
                        destination_broker_id=fragment.destination_broker_id,
                        fragment_id=fragment.fragment_id,
                        quantity=fragment.quantity,
                        unit_price=converted_unit_price,
                        open_unit_price=None,
                        close_unit_price=None,
                        realized_pnl=None,
                        proceeds=None,
                        ratio=None,
                    )
                )
                rows.append(
                    LotTimelineEventSchema(
                        lot_id=fragment.lot_id,
                        date=fragment.end_date if fragment.end_date is not None else fragment.start_date,
                        kind=LotTimelineEventKind.TRANSFER_ARRIVE,
                        transaction_id=transfer_pair_id,
                        related_transaction_id=transfer_pair_id,
                        broker_id=None,
                        source_broker_id=fragment.source_broker_id,
                        destination_broker_id=fragment.destination_broker_id,
                        fragment_id=fragment.fragment_id,
                        quantity=fragment.quantity,
                        unit_price=converted_unit_price,
                        open_unit_price=None,
                        close_unit_price=None,
                        realized_pnl=None,
                        proceeds=None,
                        ratio=None,
                    )
                )
            elif "/to:" in fragment_id and all(existing.fragment_id != f"lot:{fragment.lot_id}/transfer:{_parse_transfer_pair_id(fragment_id)}/transit" for existing in fragments):
                transfer_pair_id = _parse_transfer_pair_id(fragment_id)
                rows.append(
                    LotTimelineEventSchema(
                        lot_id=fragment.lot_id,
                        date=fragment.start_date,
                        kind=LotTimelineEventKind.TRANSFER_ARRIVE,
                        transaction_id=transfer_pair_id,
                        related_transaction_id=transfer_pair_id,
                        broker_id=fragment.broker_id,
                        source_broker_id=fragment.source_broker_id,
                        destination_broker_id=fragment.destination_broker_id,
                        fragment_id=fragment.fragment_id,
                        quantity=fragment.quantity,
                        unit_price=converted_unit_price,
                        open_unit_price=None,
                        close_unit_price=None,
                        realized_pnl=None,
                        proceeds=None,
                        ratio=None,
                    )
                )
        return rows

    def _build_closure_rows(
        self,
        closures: Sequence[LotClosure],
        selected: set[int],
        lots_by_id: dict[int, FifoLot],
        fx_resolver: _FxRateResolver,
    ) -> list[LotTimelineEventSchema]:
        rows: list[LotTimelineEventSchema] = []
        for closure in closures:
            if closure.lot_id not in selected:
                continue
            lot = lots_by_id[closure.lot_id]
            converted_open = fx_resolver.convert(closure.open_unit_price, lot.currency, closure.close_date)
            converted_close = fx_resolver.convert(closure.close_unit_price, lot.currency, closure.close_date)
            converted_pnl = fx_resolver.convert(closure.realized_pnl, lot.currency, closure.close_date)
            converted_proceeds = fx_resolver.convert(closure.proceeds, lot.currency, closure.close_date)
            rows.append(
                LotTimelineEventSchema(
                    lot_id=closure.lot_id,
                    date=closure.close_date,
                    kind=LotTimelineEventKind(closure.close_reason),
                    transaction_id=closure.transaction_id,
                    related_transaction_id=None,
                    broker_id=lot.opening_broker_id,
                    source_broker_id=None,
                    destination_broker_id=None,
                    fragment_id=closure.fragment_id,
                    quantity=closure.quantity,
                    unit_price=converted_close,
                    open_unit_price=converted_open,
                    close_unit_price=converted_close,
                    realized_pnl=converted_pnl,
                    proceeds=converted_proceeds,
                    ratio=None,
                )
            )
        return rows

    def _build_value_history(
        self,
        *,
        selected_ids: Sequence[int],
        lots_by_id: dict[int, FifoLot],
        fragments_by_lot: dict[int, list[FragmentInterval]],
        closures_by_lot: dict[int, list[LotClosure]],
        market_prices: dict[date_type, Decimal | None],
        history_dates: Sequence[date_type],
        fx_resolver: _FxRateResolver,
    ) -> list[LotValueHistoryPoint]:
        points: list[LotValueHistoryPoint] = []
        for lot_id in selected_ids:
            lot = lots_by_id[lot_id]
            last_date = self._lot_history_end_date(lot, closures_by_lot.get(lot_id, []), history_dates[-1])
            proceeds_by_day = self._closure_proceeds_prefix(lot, closures_by_lot.get(lot_id, []), fx_resolver)
            converted_original_cost = fx_resolver.convert(lot.original_cost, lot.currency, lot.opening_date) or lot.original_cost
            converted_short_proceeds = fx_resolver.convert(lot.cumulative_proceeds, lot.currency, lot.opening_date) or lot.cumulative_proceeds
            for current_date in history_dates:
                if current_date < lot.opening_date or current_date > last_date:
                    continue
                market_price = market_prices.get(current_date)
                if market_price is None:
                    continue
                open_quantity = self._open_quantity_on_date(fragments_by_lot.get(lot_id, []), current_date)
                open_value = open_quantity * market_price
                proceeds = self._prefix_value_on_date(proceeds_by_day, current_date)
                if lot.direction == "LONG":
                    total_value = open_value + proceeds
                    pnl = total_value - converted_original_cost
                else:
                    proceeds = converted_short_proceeds
                    total_value = proceeds - open_value
                    pnl = total_value
                points.append(
                    LotValueHistoryPoint(
                        lot_id=lot_id,
                        date=current_date,
                        open_value=open_value,
                        proceeds=proceeds,
                        total_value=total_value,
                        original_cost=converted_original_cost,
                        pnl=pnl,
                    )
                )
        return points

    def _build_return_history(
        self,
        *,
        selected_ids: Sequence[int],
        lots_by_id: dict[int, FifoLot],
        market_prices: dict[date_type, Decimal | None],
        price_lookup: _PriceHistoryLookup,
        fx_resolver: _FxRateResolver,
        history_dates: Sequence[date_type],
        closures_by_lot: dict[int, list[LotClosure]],
    ) -> list[LotReturnHistoryPoint]:
        points: list[LotReturnHistoryPoint] = []
        for lot_id in selected_ids:
            lot = lots_by_id[lot_id]
            if lot.reference_unit_price is None:
                continue
            resolved_reference = price_lookup.resolve(lot.opening_date)
            if resolved_reference is None:
                continue
            converted_reference = fx_resolver.convert(lot.reference_unit_price, resolved_reference.currency, resolved_reference.resolved_date)
            if converted_reference in (None, Decimal("0")):
                continue
            last_date = self._lot_history_end_date(lot, closures_by_lot.get(lot_id, []), history_dates[-1])
            for current_date in history_dates:
                if current_date < lot.opening_date or current_date > last_date:
                    continue
                market_price = market_prices.get(current_date)
                if market_price is None:
                    continue
                points.append(
                    LotReturnHistoryPoint(
                        lot_id=lot_id,
                        date=current_date,
                        relative_return=(market_price / converted_reference) - Decimal("1"),
                        reference_price_source=lot.reference_price_source,
                    )
                )
        return points

    def _build_price_history(
        self,
        *,
        selected_ids: Sequence[int],
        lots_by_id: dict[int, FifoLot],
        market_prices: dict[date_type, Decimal | None],
        history_dates: Sequence[date_type],
        target_currency: str,
        closures_by_lot: dict[int, list[LotClosure]],
    ) -> list[LotPriceHistoryPoint]:
        points: list[LotPriceHistoryPoint] = []
        for lot_id in selected_ids:
            lot = lots_by_id[lot_id]
            last_date = self._lot_history_end_date(lot, closures_by_lot.get(lot_id, []), history_dates[-1])
            for current_date in history_dates:
                if current_date < lot.opening_date or current_date > last_date:
                    continue
                market_price = market_prices.get(current_date)
                if market_price is None:
                    continue
                points.append(LotPriceHistoryPoint(lot_id=lot_id, date=current_date, market_price=market_price, currency=target_currency))
        return points

    def _build_data_quality_report(self, issues: Sequence[FifoDataQualityIssue]) -> DataQualityReport:
        mapped = []
        for issue in issues:
            code = IssueCode(issue.code)
            mapped.append(
                DataQualityIssue(
                    domain=IssueDomain.PORTFOLIO,
                    code=code,
                    severity=IssueSeverity.WARNING if code in _WARNING_ISSUE_CODES else IssueSeverity.ERROR,
                    message_i18n_key=_message_key_for_issue(code),
                    message_params={
                        "transaction_id": issue.transaction_id,
                        "lot_id": issue.lot_id,
                        "broker_id": issue.broker_id,
                        "related_transaction_id": issue.related_transaction_id,
                        **issue.params,
                    },
                )
            )
        return DataQualityReport(issues=mapped)

    def _group_fragments(self, fragments: Sequence[FragmentInterval]) -> dict[int, list[FragmentInterval]]:
        grouped: dict[int, list[FragmentInterval]] = defaultdict(list)
        for fragment in fragments:
            grouped[fragment.lot_id].append(fragment)
        return grouped

    def _group_closures(self, closures: Sequence[LotClosure]) -> dict[int, list[LotClosure]]:
        grouped: dict[int, list[LotClosure]] = defaultdict(list)
        for closure in closures:
            grouped[closure.lot_id].append(closure)
        return grouped

    def _impacted_lot_ids_for_split(self, event: FifoEvent, fragments: Sequence[FragmentInterval]) -> set[int]:
        impacted: set[int] = set()
        for fragment in fragments:
            if not _fragment_active_on_date(fragment, event.date):
                continue
            if fragment.custody_type == "BROKER" and fragment.broker_id == event.broker_id:
                impacted.add(fragment.lot_id)
            elif fragment.custody_type == "IN_TRANSIT" and (fragment.source_broker_id == event.broker_id or fragment.destination_broker_id == event.broker_id):
                impacted.add(fragment.lot_id)
        return impacted

    def _lot_history_end_date(self, lot: FifoLot, closures: Sequence[LotClosure], fallback_end: date_type) -> date_type:
        if lot.open_quantity > 0:
            return fallback_end
        if not closures:
            return lot.opening_date
        return max(closure.close_date for closure in closures)

    def _closure_proceeds_prefix(
        self,
        lot: FifoLot,
        closures: Sequence[LotClosure],
        fx_resolver: _FxRateResolver,
    ) -> dict[date_type, Decimal]:
        running = Decimal("0")
        out: dict[date_type, Decimal] = {}
        for closure in sorted(closures, key=lambda item: (item.close_date, item.transaction_id, item.lot_id)):
            running += fx_resolver.convert(closure.proceeds, lot.currency, closure.close_date) or closure.proceeds
            out[closure.close_date] = running
        return out

    def _prefix_value_on_date(self, values_by_date: dict[date_type, Decimal], query_date: date_type) -> Decimal:
        if not values_by_date:
            return Decimal("0")
        eligible_dates = [current_date for current_date in values_by_date if current_date <= query_date]
        if not eligible_dates:
            return Decimal("0")
        return values_by_date[max(eligible_dates)]

    def _open_quantity_on_date(self, fragments: Sequence[FragmentInterval], query_date: date_type) -> Decimal:
        return sum((fragment.quantity for fragment in fragments if _fragment_active_on_date(fragment, query_date)), Decimal("0"))

    def _trim_dates(self, rows: Sequence, start_date: date_type, end_date: date_type) -> list:
        return [row for row in rows if start_date <= row.date <= end_date]


async def get_lots_analysis(
    session: AsyncSession,
    user_id: int,
    asset_id: int,
    broker_ids: list[int] | None,
    date_from: date_type | None,
    date_to: date_type | None,
    target_currency: str | None,
    selected_lot_ids: list[int] | None,
    requested_analyses: list[str | LotAnalysisType],
) -> LotsAnalysisResponse:
    return await LotsAnalysisService(session).get_lots_analysis(
        user_id=user_id,
        asset_id=asset_id,
        broker_ids=broker_ids,
        date_from=date_from,
        date_to=date_to,
        target_currency=target_currency,
        selected_lot_ids=selected_lot_ids,
        requested_analyses=requested_analyses,
    )


def _fragment_active_on_date(fragment: FragmentInterval, query_date: date_type) -> bool:
    return fragment.start_date <= query_date and (fragment.end_date is None or query_date < fragment.end_date)


def _message_key_for_issue(code: IssueCode) -> str:
    mapping = {
        IssueCode.REFERENCE_PRICE_FALLBACK: "dataQuality.referencePriceFallback",
        IssueCode.REFERENCE_PRICE_UNAVAILABLE: "dataQuality.referencePriceUnavailable",
        IssueCode.SHORT_TRANSFER_NOT_SUPPORTED: "dataQuality.shortTransferNotSupported",
        IssueCode.SHORT_ADJUSTMENT_NOT_SUPPORTED: "dataQuality.shortAdjustmentNotSupported",
        IssueCode.FIFO_SOURCE_QUANTITY_MISSING: "dataQuality.fifoSourceQuantityMissing",
        IssueCode.TRANSFER_PAIR_MISSING: "dataQuality.transferPairMissing",
    }
    return mapping[code]


def _parse_transfer_pair_id(fragment_id: str) -> int:
    marker = "/transfer:"
    if marker not in fragment_id:
        raise ValueError(f"Fragment id does not contain transfer pair marker: {fragment_id}")
    suffix = fragment_id.split(marker, maxsplit=1)[1]
    raw_pair_id = suffix.split("/", maxsplit=1)[0]
    return int(raw_pair_id)


def _date_range(start_date: date_type, end_date: date_type) -> Iterable[date_type]:
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)
