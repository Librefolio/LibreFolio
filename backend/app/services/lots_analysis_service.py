from __future__ import annotations

import bisect
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Iterable, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetEvent, AssetEventType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import (
    BrokerWACHistoryPoint,
    CumulativeWACHistoryPoint,
    DataQualityIssue,
    DataQualityReport,
    EconomicAllocationGroupSchema,
    EconomicLotAllocationSchema,
    GanttSegmentSchema,
    IssueCode,
    IssueDomain,
    IssueSeverity,
    LotAnalysisStatus,
    LotAnalysisType,
    LotIncomeEventKind,
    LotIncomeEventSchema,
    LotPriceHistoryPoint,
    LotReturnHistoryPoint,
    LotsAnalysisMetadata,
    LotsAnalysisResponse,
    LotSummarySchema,
    LotTimelineEventKind,
    LotTimelineEventSchema,
    LotValueHistoryPoint,
    PerformanceHistoryPoint,
    ReferencePriceSource,
    TargetOperationAllocationSchema,
)
from backend.app.services.fifo_lot_engine import (
    EconomicAllocationGroup,
    EconomicEvent,
    FifoDataQualityIssue,
    FifoEngineResult,
    FifoEvent,
    FifoInputTransaction,
    FifoLot,
    FragmentInterval,
    LotClosure,
    ReferencePriceResolution,
    run_fifo_lot_engine,
)
from backend.app.services.fx import convert_bulk
from backend.app.services.settings_service import get_global_setting
from backend.app.utils.financial.roi_utils import CashFlowInput, NAVSnapshot, calculate_simple_roi_series, calculate_twrr_series
from backend.app.utils.financial.valuation_utils import compute_holding_value, normalize_quote_base_quantity
from backend.app.utils.financial.wac_utils import WACInputTX, compute_wac_from_txlist

_WARNING_ISSUE_CODES = {
    IssueCode.REFERENCE_PRICE_FALLBACK,
    IssueCode.REFERENCE_PRICE_UNAVAILABLE,
    IssueCode.CURRENT_PRICE_ASSUMED_AT_COST,
    IssueCode.ASSET_INCOME_NO_ELIGIBLE_LOTS,
    IssueCode.ASSET_COST_NO_ELIGIBLE_LOTS,
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


@dataclass(frozen=True, slots=True)
class _PerformanceSourceContext:
    transactions: Sequence[Transaction]
    engine_result: FifoEngineResult
    lots_by_id: dict[int, FifoLot]
    fragments_by_lot: dict[int, list[FragmentInterval]]
    closures_by_lot: dict[int, list[LotClosure]]
    tx_by_id: dict[int, Transaction]


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
        self._loaded: set[tuple[str, date_type]] = set()
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
        pending = [key for key in self._needs if key not in self._loaded]
        if not pending:
            return
        conversions = [(Currency(code=currency, amount=Decimal("1")), self.target_currency, as_of_date) for currency, as_of_date in pending]
        results, _errors = await convert_bulk(session, conversions, raise_on_error=False)
        for idx, key in enumerate(pending):
            self._loaded.add(key)
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
                status="COMPLETE",
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
                status="COMPLETE",
            )

        computed_from = transactions[0].date
        split_ratios_by_tx_id = await self._load_split_ratios(transactions)
        broker_shorting = await self._load_broker_shorting(scope_broker_ids)
        prices = await self._load_prices(
            asset_id=asset_id,
            date_from=computed_from,
            date_to=actual_to,
        )
        price_lookup = _PriceHistoryLookup(prices)
        estimated_mode = price_lookup.latest() is None
        income_transactions = await self._load_income_transactions(asset_id=asset_id, scope_broker_ids=scope_broker_ids, date_to=actual_to)
        cost_transactions = await self._load_cost_transactions(asset_id=asset_id, scope_broker_ids=scope_broker_ids, date_to=actual_to)

        def reference_price_lookup(resolved_asset_id: int, opened_at: date_type) -> ReferencePriceResolution | None:
            if resolved_asset_id != asset_id:
                return None
            resolved = price_lookup.resolve(opened_at)
            if resolved is None:
                return None
            return ReferencePriceResolution(price=resolved.price, source=resolved.source)

        # Resolve economic FX and build events BEFORE the engine run: the engine is target-value
        # aware (Option B), so it needs each event's pre-converted target amount and each trade's
        # target controvalue (FEE weights, §3.5). Eligibility (D-1 open quantity, broker-scoped,
        # transfer-aware) and matching are computed inside the engine from the replayed fragments.
        # Valuation FX is resolved after the run (below).
        fx_resolver = _FxRateResolver(target_currency)
        needs_income_alloc = any(analysis in normalized_analyses for analysis in (LotAnalysisType.LOT_SUMMARY, LotAnalysisType.VALUE_HISTORY, LotAnalysisType.RETURN_HISTORY, LotAnalysisType.INCOME_EVENTS))
        income_events_input: list[EconomicEvent] = []
        cost_events_input: list[EconomicEvent] = []
        engine_transactions: Sequence[Transaction | FifoInputTransaction] = transactions
        if needs_income_alloc and (income_transactions or cost_transactions):
            for tx in income_transactions:
                fx_resolver.need(tx.currency or asset.currency, tx.date)
            for tx in cost_transactions:
                fx_resolver.need(tx.currency or asset.currency, tx.date)
            if cost_transactions:
                for tx in transactions:
                    if tx.type in (TransactionType.BUY, TransactionType.SELL):
                        fx_resolver.need(tx.currency or asset.currency, tx.date)
            await fx_resolver.load(self.db)
            if income_transactions:
                income_events_input = self._build_income_economic_events(
                    income_transactions=income_transactions,
                    fx_resolver=fx_resolver,
                    asset_currency=asset.currency,
                    target_currency=target_currency,
                )
            if cost_transactions:
                cost_events_input = self._build_cost_economic_events(
                    cost_transactions=cost_transactions,
                    fx_resolver=fx_resolver,
                    asset_currency=asset.currency,
                    target_currency=target_currency,
                )
                engine_transactions = self._build_engine_transactions(transactions, fx_resolver, asset.currency, target_currency)

        engine_result = run_fifo_lot_engine(
            transactions=engine_transactions,
            broker_shorting=broker_shorting,
            split_ratios_by_tx_id=split_ratios_by_tx_id,
            reference_price_lookup=reference_price_lookup,
            economic_events=[*income_events_input, *cost_events_input],
            target_currency=target_currency,
        )

        lots_by_id = {lot.lot_id: lot for lot in engine_result.lots}
        selected_ids = self._resolve_selected_lot_ids(selected_lot_ids, lots_by_id)
        fragments_by_lot = self._group_fragments(engine_result.fragment_intervals)
        closures_by_lot = self._group_closures(engine_result.closures)
        tx_by_id = {tx.id: tx for tx in transactions if tx.id is not None}
        display_from = date_from or computed_from
        history_dates = list(_date_range(computed_from, actual_to))

        performance_context = _PerformanceSourceContext(
            transactions=transactions,
            engine_result=engine_result,
            lots_by_id=lots_by_id,
            fragments_by_lot=fragments_by_lot,
            closures_by_lot=closures_by_lot,
            tx_by_id=tx_by_id,
        )
        if LotAnalysisType.PERFORMANCE_HISTORY in normalized_analyses and broker_ids is not None:
            accessible_broker_ids = await self._get_scope_broker_ids(user_id=user_id, broker_ids=None)
            if accessible_broker_ids != scope_broker_ids:
                performance_transactions = await self._load_transactions(asset_id=asset_id, scope_broker_ids=accessible_broker_ids, date_to=actual_to)
                performance_split_ratios = await self._load_split_ratios(performance_transactions)
                performance_broker_shorting = await self._load_broker_shorting(accessible_broker_ids)
                performance_engine_result = run_fifo_lot_engine(
                    transactions=performance_transactions,
                    broker_shorting=performance_broker_shorting,
                    split_ratios_by_tx_id=performance_split_ratios,
                    reference_price_lookup=reference_price_lookup,
                )
                performance_lots_by_id = {lot.lot_id: lot for lot in performance_engine_result.lots}
                performance_context = _PerformanceSourceContext(
                    transactions=performance_transactions,
                    engine_result=performance_engine_result,
                    lots_by_id=performance_lots_by_id,
                    fragments_by_lot=self._group_fragments(performance_engine_result.fragment_intervals),
                    closures_by_lot=self._group_closures(performance_engine_result.closures),
                    tx_by_id={tx.id: tx for tx in performance_transactions if tx.id is not None},
                )

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
        self._collect_performance_fx_needs(
            fx_resolver=fx_resolver,
            analyses=normalized_analyses,
            transactions=performance_context.transactions,
            closures=performance_context.engine_result.closures,
            lots_by_id=performance_context.lots_by_id,
            asset_currency=asset.currency,
        )
        if needs_income_alloc and estimated_mode:
            # Estimated-at-cost values the open portion at converted opening cost -> needs fx@opening.
            for lot in lots_by_id.values():
                fx_resolver.need(lot.currency, lot.opening_date)
        if self._needs_market_series(normalized_analyses):
            # The estimated market-price line (below) reads each trade's unit price at its own date;
            # register the fx@trade-date needs so foreign-currency trades convert to target (no-op EUR).
            for tx in transactions:
                fx_resolver.need(tx.currency or asset.currency, tx.date)
                if tx.cost_basis_override is not None:
                    fx_resolver.need(tx.cost_basis_currency or asset.currency, tx.date)
        await fx_resolver.load(self.db)

        income_by_lot, income_prefix_by_lot, income_events_payload = self._extract_income_outputs(engine_result, income_events_input)
        fees_by_lot, taxes_by_lot, fees_prefix_by_lot, taxes_prefix_by_lot = self._extract_cost_outputs(engine_result)

        data_quality = self._build_data_quality_report(engine_result.issues)
        if estimated_mode and self._needs_market_series(normalized_analyses):
            # estimated_mode == the asset has NO price points at all, so the whole analysis window
            # [computed_from, actual_to] is the range with no market price. Surface it in the message
            # so the user knows which period is uncovered (per user feedback on delisted/matured titles).
            data_quality.issues.append(
                DataQualityIssue(
                    domain=IssueDomain.PORTFOLIO,
                    code=IssueCode.CURRENT_PRICE_ASSUMED_AT_COST,
                    severity=IssueSeverity.WARNING,
                    message_i18n_key="dataQuality.currentPriceAssumedAtCostRange",
                    message_params={"asset_id": asset_id, "date_from": computed_from.isoformat(), "date_to": actual_to.isoformat()},
                )
            )
        active_price_dates = history_dates if self._needs_market_series(normalized_analyses) else [actual_to]
        market_prices = self._build_market_price_map(price_lookup, fx_resolver, active_price_dates)
        quote_base_quantity = normalize_quote_base_quantity(asset.quote_base_quantity)
        # Estimated market-price line (chart only): where no real quote exists, carry the last-known
        # trade price forward (BUY cost / SELL proceeds / priced ADJUSTMENT carryover) so a price-less
        # or partially-gapped asset still shows a "prezzo di mercato" curve that steps at each trade.
        # This never feeds valuation/return math (market_prices, above, is left untouched).
        trade_price_points = self._build_trade_price_points(
            transactions=transactions,
            split_ratios_by_tx_id=split_ratios_by_tx_id,
            asset_currency=asset.currency,
            fx_resolver=fx_resolver,
            quote_base_quantity=quote_base_quantity,
        )
        estimated_market_prices = self._build_estimated_market_price_map(
            price_lookup=price_lookup,
            trade_points=trade_price_points,
            fx_resolver=fx_resolver,
            dates=active_price_dates,
        )
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
                income_by_lot=income_by_lot,
                fees_by_lot=fees_by_lot,
                taxes_by_lot=taxes_by_lot,
                estimated_mode=estimated_mode,
                quote_base_quantity=quote_base_quantity,
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
                    income_prefix_by_lot=income_prefix_by_lot,
                    fees_prefix_by_lot=fees_prefix_by_lot,
                    taxes_prefix_by_lot=taxes_prefix_by_lot,
                    estimated_mode=estimated_mode,
                    quote_base_quantity=quote_base_quantity,
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
                    fragments_by_lot=fragments_by_lot,
                    market_prices=market_prices,
                    price_lookup=price_lookup,
                    fx_resolver=fx_resolver,
                    history_dates=history_dates,
                    closures_by_lot=closures_by_lot,
                    income_prefix_by_lot=income_prefix_by_lot,
                    fees_prefix_by_lot=fees_prefix_by_lot,
                    taxes_prefix_by_lot=taxes_prefix_by_lot,
                    estimated_mode=estimated_mode,
                    quote_base_quantity=quote_base_quantity,
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
                    estimated_market_prices=estimated_market_prices,
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

        performance_history = None
        if LotAnalysisType.PERFORMANCE_HISTORY in normalized_analyses:
            performance_history = self._trim_dates(
                self._build_performance_history(
                    scope_broker_ids=scope_broker_ids,
                    history_dates=history_dates,
                    market_prices=market_prices,
                    asset_currency=asset.currency,
                    fx_resolver=fx_resolver,
                    context=performance_context,
                    quote_base_quantity=quote_base_quantity,
                ),
                display_from,
                actual_to,
            )

        income_events = None
        if LotAnalysisType.INCOME_EVENTS in normalized_analyses:
            # Only markers within the visualized window; events before display_from already
            # contributed to the opening state and would clutter the chart.
            income_events = [event for event in income_events_payload if display_from <= event.date <= actual_to]

        economic_allocation_groups = None
        if LotAnalysisType.LOT_SUMMARY in normalized_analyses and engine_result.economic_allocation_groups:
            economic_allocation_groups = self._map_economic_groups(engine_result.economic_allocation_groups)

        return LotsAnalysisResponse(
            asset_id=asset_id,
            target_currency=target_currency,
            quote_base_quantity=quote_base_quantity,
            calculation_status=engine_result.analysis_status,
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
            performance_history=performance_history,
            income_events=income_events,
            economic_allocation_groups=economic_allocation_groups,
            asset_orphan_income=engine_result.asset_orphan_income,
            asset_orphan_fees=engine_result.asset_orphan_fees,
            asset_orphan_taxes=engine_result.asset_orphan_taxes,
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

    async def _load_income_transactions(self, asset_id: int, scope_broker_ids: Sequence[int], date_to: date_type) -> list[Transaction]:
        """Load asset-linked DIVIDEND/INTEREST cash transactions for pro-rata lot allocation.

        These are cash-only events (no quantity) so they never enter the FIFO engine load;
        they are attributed to open LONG lots as of ``transaction.date - 1`` (D-1 semantics), scoped
        to the paying broker and transfer-aware, by the engine economic stage (see
        ``FifoLotEngine._allocate_income_pools`` and ``_build_income_economic_events``).
        Income without ``asset_id`` is intentionally excluded here — it is handled broker-level
        by the Portfolio Engine ("Altri effetti del periodo").
        """
        stmt = (
            select(Transaction)
            .where(Transaction.asset_id == asset_id)
            .where(Transaction.broker_id.in_(scope_broker_ids))
            .where(Transaction.date <= date_to)
            .where(Transaction.type.in_([TransactionType.DIVIDEND, TransactionType.INTEREST]))
            .where(Transaction.amount != 0)
            .order_by(Transaction.date, Transaction.id)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def _load_cost_transactions(self, asset_id: int, scope_broker_ids: Sequence[int], date_to: date_type) -> list[Transaction]:
        """Load asset-linked FEE/TAX cash transactions for deterministic cost allocation.

        Like income these are cash-only events (no quantity) and never enter the FIFO quantitative
        load; they are pooled and matched to trades/income/holdings by the engine economic stage
        (see ``FifoLotEngine._allocate_cost_pools`` and ``_build_cost_economic_events``). FEE/TAX
        without ``asset_id`` are intentionally excluded — those are broker-level costs handled by the
        Portfolio Engine, not attributable to a specific lot.
        """
        stmt = (
            select(Transaction)
            .where(Transaction.asset_id == asset_id)
            .where(Transaction.broker_id.in_(scope_broker_ids))
            .where(Transaction.date <= date_to)
            .where(Transaction.type.in_([TransactionType.FEE, TransactionType.TAX]))
            .where(Transaction.amount != 0)
            .order_by(Transaction.date, Transaction.id)
        )
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

    async def _load_prices(
        self,
        asset_id: int,
        date_from: date_type,
        date_to: date_type,
    ) -> list[PriceHistory]:
        previous_price_date = select(func.max(PriceHistory.date)).where(PriceHistory.asset_id == asset_id).where(PriceHistory.date < date_from).where(PriceHistory.close.is_not(None)).scalar_subquery()
        stmt = (
            select(PriceHistory)
            .where(PriceHistory.asset_id == asset_id)
            .where(
                or_(
                    PriceHistory.date >= date_from,
                    PriceHistory.date == previous_price_date,
                )
            )
            .where(PriceHistory.date <= date_to)
            .where(PriceHistory.close.is_not(None))
            .order_by(PriceHistory.date)
        )
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
        status: LotAnalysisStatus,
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

        if LotAnalysisType.LOT_SUMMARY in analyses or LotAnalysisType.RETURN_HISTORY in analyses:
            for lot_id in selected_ids:
                lot = lots_by_id[lot_id]
                fx_resolver.need(lot.currency, lot.opening_date)
                raw_reference_price, raw_reference_currency, reference_date, _reference_source = self._opening_reference_price(lot, price_lookup)
                if raw_reference_price is not None and raw_reference_currency is not None:
                    fx_resolver.need(raw_reference_currency, reference_date)
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
                LotAnalysisType.PERFORMANCE_HISTORY,
            )
        )

    def _collect_performance_fx_needs(
        self,
        *,
        fx_resolver: _FxRateResolver,
        analyses: Sequence[LotAnalysisType],
        transactions: Sequence[Transaction],
        closures: Sequence[LotClosure],
        lots_by_id: dict[int, FifoLot],
        asset_currency: str,
    ) -> None:
        if LotAnalysisType.PERFORMANCE_HISTORY not in analyses:
            return
        for tx in transactions:
            tx_type = str(getattr(tx.type, "value", tx.type))
            if tx_type == "BUY":
                fx_resolver.need(tx.currency or asset_currency, tx.date)
                continue
            if tx_type == "ADJUSTMENT" and tx.quantity > 0:
                if tx.cost_basis_override not in (None, Decimal("0")):
                    fx_resolver.need(tx.cost_basis_currency or asset_currency, tx.date)
                elif tx.amount != Decimal("0"):
                    fx_resolver.need(tx.currency or asset_currency, tx.date)
        for closure in closures:
            lot = lots_by_id.get(closure.lot_id)
            if lot is not None and lot.direction == "LONG" and closure.close_reason == "SELL":
                fx_resolver.need(lot.currency or asset_currency, closure.close_date)

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

    def _build_trade_price_points(
        self,
        *,
        transactions: Sequence[Transaction],
        split_ratios_by_tx_id: dict[int, Decimal],
        asset_currency: str,
        fx_resolver: _FxRateResolver,
        quote_base_quantity: int,
    ) -> list[tuple[date_type, Decimal]]:
        """Last-known-trade price observations, in target currency at the per-quote_base_quantity
        market scale that ``price_history.close`` uses.

        Mirrors the value a market ticker carries: the unit price of the most recent trade — BUY
        cost, SELL proceeds, or a priced ADJUSTMENT carryover (in-kind transfer/succession cost) —
        divided by traded quantity and scaled ``× quote_base_quantity`` (so a qbq=100 bond lands on
        the ~100 par axis; no-op for qbq=1). Split-linked rows and pure quantity adjustments carry no
        price and are skipped. Consumed only to *estimate* the market-price line where no real quote
        exists (last-observation-carried-forward); it never feeds valuation/return math.
        """
        scale = Decimal(quote_base_quantity if quote_base_quantity > 0 else 1)
        points: list[tuple[date_type, Decimal]] = []
        for tx in sorted(transactions, key=lambda row: (row.date, row.id or 0)):
            if tx.id in split_ratios_by_tx_id:
                continue
            quantity = tx.quantity or Decimal("0")
            if quantity == Decimal("0"):
                continue
            tx_type = str(getattr(tx.type, "value", tx.type))
            unit_target: Decimal | None = None
            if tx_type in ("BUY", "SELL"):
                if tx.amount:
                    currency = tx.currency or asset_currency
                    converted = fx_resolver.convert(abs(tx.amount), currency, tx.date)
                    total = converted if converted is not None else abs(tx.amount)
                    unit_target = total / abs(quantity)
            elif tx_type == "ADJUSTMENT" and tx.cost_basis_override not in (None, Decimal("0")):
                currency = tx.cost_basis_currency or asset_currency
                converted = fx_resolver.convert(tx.cost_basis_override, currency, tx.date)
                unit_target = converted if converted is not None else tx.cost_basis_override
            if unit_target is None:
                continue
            points.append((tx.date, unit_target * scale))
        return points

    def _build_estimated_market_price_map(
        self,
        *,
        price_lookup: _PriceHistoryLookup,
        trade_points: Sequence[tuple[date_type, Decimal]],
        fx_resolver: _FxRateResolver,
        dates: Sequence[date_type],
    ) -> dict[date_type, tuple[Decimal, bool]]:
        """Estimated market price per date = the most recent observation among the real price
        history (carried forward, converted to target) and the last-known trade. A real quote wins
        ties (same observation date). The bool flag is ``True`` when the value is an estimate (came
        from a trade, not an actual quote). Dates with no observation at all are omitted.
        """
        trade_dates = [point[0] for point in trade_points]
        out: dict[date_type, tuple[Decimal, bool]] = {}
        for current_date in dates:
            resolved = price_lookup.resolve(current_date)
            real_value: Decimal | None = None
            real_date: date_type | None = None
            if resolved is not None:
                real_value = fx_resolver.convert(resolved.price, resolved.currency, current_date)
                real_date = resolved.resolved_date
            trade_value: Decimal | None = None
            trade_date: date_type | None = None
            idx = bisect.bisect_right(trade_dates, current_date) - 1
            if idx >= 0:
                trade_date = trade_points[idx][0]
                trade_value = trade_points[idx][1]
            if real_value is not None and (trade_date is None or (real_date is not None and real_date >= trade_date)):
                out[current_date] = (real_value, False)
            elif trade_value is not None:
                out[current_date] = (trade_value, True)
        return out

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

    def _build_performance_history(
        self,
        *,
        scope_broker_ids: Sequence[int],
        history_dates: Sequence[date_type],
        market_prices: dict[date_type, Decimal | None],
        asset_currency: str,
        fx_resolver: _FxRateResolver,
        context: _PerformanceSourceContext,
        quote_base_quantity: int,
    ) -> list[PerformanceHistoryPoint]:
        scope_set = set(scope_broker_ids)
        scoped_fragments_by_lot = {lot_id: [fragment for fragment in fragments if self._fragment_in_scope(fragment, scope_set)] for lot_id, fragments in context.fragments_by_lot.items()}

        nav_snapshots: list[NAVSnapshot] = []
        for current_date in history_dates:
            market_price = market_prices.get(current_date)
            if market_price is None:
                continue
            nav_amount = Decimal("0")
            for _lot_id, fragments in scoped_fragments_by_lot.items():
                if not fragments:
                    continue
                nav_amount += self._open_value_on_date(fragments, market_price, current_date, quote_base_quantity)
            nav_snapshots.append(NAVSnapshot(date=current_date, nav=nav_amount))

        cash_flows: list[CashFlowInput] = []
        invalid_external_flow_from: date_type | None = None

        for tx in sorted(context.transactions, key=lambda row: (row.date, row.id or 0)):
            if tx.broker_id not in scope_set:
                continue
            tx_type = str(getattr(tx.type, "value", tx.type))
            if tx_type == "BUY":
                cash_flows.append(CashFlowInput(date=tx.date, amount=-self._converted_external_amount(abs(tx.amount), tx.currency or asset_currency, tx.date, fx_resolver)))
                continue
            if tx_type == "ADJUSTMENT" and tx.quantity > 0:
                adjustment_cost = self._adjustment_cash_flow_cost(tx=tx, asset_currency=asset_currency, fx_resolver=fx_resolver)
                if adjustment_cost not in (None, Decimal("0")):
                    cash_flows.append(CashFlowInput(date=tx.date, amount=-adjustment_cost))

        for closure in sorted(context.engine_result.closures, key=lambda row: (row.close_date, row.transaction_id, row.lot_id)):
            if closure.close_reason != "SELL":
                continue
            lot = context.lots_by_id.get(closure.lot_id)
            tx = context.tx_by_id.get(closure.transaction_id)
            if lot is None or tx is None or lot.direction != "LONG" or tx.broker_id not in scope_set:
                continue
            proceeds = fx_resolver.convert(closure.proceeds, lot.currency or asset_currency, closure.close_date) or closure.proceeds
            cash_flows.append(CashFlowInput(date=closure.close_date, amount=proceeds))

        seen_external_transfers: set[tuple[int, str]] = set()
        for event in context.engine_result.classified_events:
            if event.kind not in {"TRANSFER_DEPART", "TRANSFER_ARRIVE"}:
                continue
            pair_id = event.pair_id or event.transaction_id
            dedupe_key = (pair_id, event.kind)
            if dedupe_key in seen_external_transfers:
                continue
            seen_external_transfers.add(dedupe_key)
            source_in_scope = event.source_broker_id in scope_set
            destination_in_scope = event.destination_broker_id in scope_set
            if source_in_scope == destination_in_scope:
                continue
            if source_in_scope and event.kind != "TRANSFER_DEPART":
                continue
            if destination_in_scope and event.kind != "TRANSFER_ARRIVE":
                continue
            market_price = market_prices.get(event.date)
            if market_price is None:
                invalid_external_flow_from = event.date if invalid_external_flow_from is None else min(invalid_external_flow_from, event.date)
                continue
            quantity = event.quantity or Decimal("0")
            amount = compute_holding_value(quantity, market_price, quote_base_quantity)
            cash_flows.append(CashFlowInput(date=event.date, amount=amount if source_in_scope else -amount))

        if invalid_external_flow_from is not None:
            nav_snapshots = [snapshot for snapshot in nav_snapshots if snapshot.date < invalid_external_flow_from]
            cash_flows = [flow for flow in cash_flows if flow.date < invalid_external_flow_from]

        if nav_snapshots:
            first_nav_date = nav_snapshots[0].date
            carried_cash_flow = sum((flow.amount for flow in cash_flows if flow.date < first_nav_date), Decimal("0"))
            cash_flows = [flow for flow in cash_flows if flow.date >= first_nav_date]
            if carried_cash_flow != Decimal("0"):
                cash_flows.insert(0, CashFlowInput(date=first_nav_date, amount=carried_cash_flow))

        first_cash_flow_date = min((flow.date for flow in cash_flows), default=None)
        roi_map: dict[date_type, Decimal] = {}
        twrr_map: dict[date_type, Decimal] = {}
        if first_cash_flow_date is not None and nav_snapshots:
            roi_map = {point.date: point.roi for point in calculate_simple_roi_series(nav_snapshots, cash_flows) if point.date >= first_cash_flow_date}
            twrr_map = {point.date: point.twrr for point in calculate_twrr_series(nav_snapshots, cash_flows) if point.date >= first_cash_flow_date}

        return [
            PerformanceHistoryPoint(
                date=current_date,
                roi=None if invalid_external_flow_from is not None and current_date >= invalid_external_flow_from else roi_map.get(current_date),
                twrr=None if invalid_external_flow_from is not None and current_date >= invalid_external_flow_from else twrr_map.get(current_date),
            )
            for current_date in history_dates
        ]

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

    def _build_income_economic_events(
        self,
        *,
        income_transactions: Sequence[Transaction],
        fx_resolver: _FxRateResolver,
        asset_currency: str,
        target_currency: str,
    ) -> list[EconomicEvent]:
        """Build target-value-aware DIVIDEND/INTEREST events for the engine economic stage.

        FX is resolved here (the service owns FX I/O): each event carries the native amount and the
        amount converted to ``target_currency`` at the transaction date. Eligibility, pooling and
        pro-rata allocation are performed by the engine from the replayed fragments (D-1 semantics,
        broker scoped, transfer aware).
        """
        events: list[EconomicEvent] = []
        for tx in income_transactions:
            if tx.id is None or tx.asset_id is None:
                continue
            native_currency = tx.currency or asset_currency
            target_amount = self._converted_external_amount(tx.amount, native_currency, tx.date, fx_resolver)
            events.append(
                EconomicEvent(
                    transaction_id=tx.id,
                    broker_id=tx.broker_id,
                    asset_id=tx.asset_id,
                    date=tx.date,
                    economic_type="DIVIDEND" if tx.type == TransactionType.DIVIDEND else "INTEREST",
                    native_amount=tx.amount,
                    native_currency=native_currency,
                    target_amount=target_amount,
                    target_currency=target_currency,
                )
            )
        return events

    def _build_cost_economic_events(
        self,
        *,
        cost_transactions: Sequence[Transaction],
        fx_resolver: _FxRateResolver,
        asset_currency: str,
        target_currency: str,
    ) -> list[EconomicEvent]:
        """Build target-value-aware FEE/TAX events for the engine economic stage.

        FX is resolved here (the service owns FX I/O): each event carries the native (negative)
        amount and the amount converted to ``target_currency`` at the transaction date. Pooling,
        matching (same-day/previous-day trades or income, holdings fallback) and orphan detection are
        performed by the engine.
        """
        events: list[EconomicEvent] = []
        for tx in cost_transactions:
            if tx.id is None or tx.asset_id is None or tx.amount is None:
                continue
            native_currency = tx.currency or asset_currency
            target_amount = self._converted_external_amount(tx.amount, native_currency, tx.date, fx_resolver)
            events.append(
                EconomicEvent(
                    transaction_id=tx.id,
                    broker_id=tx.broker_id,
                    asset_id=tx.asset_id,
                    date=tx.date,
                    economic_type="FEE" if tx.type == TransactionType.FEE else "TAX",
                    native_amount=tx.amount,
                    native_currency=native_currency,
                    target_amount=target_amount,
                    target_currency=target_currency,
                )
            )
        return events

    def _build_engine_transactions(
        self,
        transactions: Sequence[Transaction],
        fx_resolver: _FxRateResolver,
        asset_currency: str,
        target_currency: str,
    ) -> list[FifoInputTransaction]:
        """Normalize transactions for the engine, attaching each trade's target controvalue.

        Only BUY/SELL carry ``target_amount`` (the FEE/TAX pooling weight, §3.5); other kinds keep it
        ``None``. The quantitative replay is unchanged — only the economic stage reads the target.
        """
        engine_transactions: list[FifoInputTransaction] = []
        for tx in transactions:
            base = FifoInputTransaction.from_transaction(tx)
            if tx.type in (TransactionType.BUY, TransactionType.SELL) and tx.amount is not None:
                native_currency = tx.currency or asset_currency
                target_amount = self._converted_external_amount(tx.amount, native_currency, tx.date, fx_resolver)
                base = replace(base, target_amount=target_amount, target_currency=target_currency)
            engine_transactions.append(base)
        return engine_transactions

    def _extract_income_outputs(
        self,
        engine_result: FifoEngineResult,
        income_events: Sequence[EconomicEvent],
    ) -> tuple[dict[int, Decimal], dict[int, dict[date_type, Decimal]], list[LotIncomeEventSchema]]:
        """Derive the service-facing income views from the engine economic output.

        Returns ``(income_by_lot, income_prefix_by_lot, income_events_payload)``: cumulative income
        per lot (from the engine accumulators); a per-lot cumulative-by-date map for histories (from
        the audit groups, same shape as ``_closure_proceeds_prefix``); and one
        ``LotIncomeEventSchema`` per income transaction carrying the shared eligible lot ids (plan
        v3 §11 chart markers).
        """
        income_by_lot: dict[int, Decimal] = {lot_id: accumulator.gross_income for lot_id, accumulator in engine_result.economic_accumulators_by_lot.items() if accumulator.gross_income != Decimal("0")}

        per_lot_dated: dict[int, list[tuple[date_type, Decimal]]] = defaultdict(list)
        pool_lot_ids: dict[tuple[int, date_type, str, str | None, str], list[int]] = {}
        for group in engine_result.economic_allocation_groups:
            if group.economic_type not in ("DIVIDEND", "INTEREST"):
                continue
            eligible_ids: list[int] = []
            for operation in group.operation_allocations:
                for allocation in operation.lot_allocations:
                    per_lot_dated[allocation.lot_id].append((group.date, allocation.target_amount))
                    eligible_ids.append(allocation.lot_id)
            pool_lot_ids[(group.broker_id, group.date, group.economic_type, group.native_currency, group.target_currency)] = eligible_ids

        income_prefix_by_lot: dict[int, dict[date_type, Decimal]] = {}
        for lot_id, dated in per_lot_dated.items():
            running = Decimal("0")
            prefix: dict[date_type, Decimal] = {}
            for event_date, amount in sorted(dated, key=lambda item: item[0]):
                running += amount
                prefix[event_date] = running
            income_prefix_by_lot[lot_id] = prefix

        income_events_payload: list[LotIncomeEventSchema] = []
        for event in sorted(income_events, key=lambda item: (item.date, item.transaction_id)):
            eligible_ids = pool_lot_ids.get((event.broker_id, event.date, event.economic_type, event.native_currency, event.target_currency), [])
            income_events_payload.append(
                LotIncomeEventSchema(
                    type=LotIncomeEventKind.DIVIDEND if event.economic_type == "DIVIDEND" else LotIncomeEventKind.INTEREST,
                    date=event.date,
                    broker_id=event.broker_id,
                    transaction_id=event.transaction_id,
                    amount=event.target_amount,
                    lot_ids=list(eligible_ids),
                )
            )
        return income_by_lot, income_prefix_by_lot, income_events_payload

    def _extract_cost_outputs(
        self,
        engine_result: FifoEngineResult,
    ) -> tuple[dict[int, Decimal], dict[int, Decimal], dict[int, dict[date_type, Decimal]], dict[int, dict[date_type, Decimal]]]:
        """Derive the service-facing FEE/TAX views from the engine economic output.

        Returns ``(fees_by_lot, taxes_by_lot, fees_prefix_by_lot, taxes_prefix_by_lot)``: cumulative
        allocated FEE/TAX per lot (from the engine accumulators, positive magnitude) plus per-lot
        cumulative-by-date maps for the net history series (from the audit groups, same shape as
        ``income_prefix_by_lot``).
        """
        fees_by_lot: dict[int, Decimal] = {lot_id: accumulator.allocated_fees for lot_id, accumulator in engine_result.economic_accumulators_by_lot.items() if accumulator.allocated_fees != Decimal("0")}
        taxes_by_lot: dict[int, Decimal] = {lot_id: accumulator.allocated_taxes for lot_id, accumulator in engine_result.economic_accumulators_by_lot.items() if accumulator.allocated_taxes != Decimal("0")}

        fees_dated: dict[int, list[tuple[date_type, Decimal]]] = defaultdict(list)
        taxes_dated: dict[int, list[tuple[date_type, Decimal]]] = defaultdict(list)
        for group in engine_result.economic_allocation_groups:
            if group.economic_type == "FEE":
                sink = fees_dated
            elif group.economic_type == "TAX":
                sink = taxes_dated
            else:
                continue
            for operation in group.operation_allocations:
                for allocation in operation.lot_allocations:
                    sink[allocation.lot_id].append((group.date, allocation.target_amount))

        def _prefix(dated: dict[int, list[tuple[date_type, Decimal]]]) -> dict[int, dict[date_type, Decimal]]:
            out: dict[int, dict[date_type, Decimal]] = {}
            for lot_id, entries in dated.items():
                running = Decimal("0")
                prefix: dict[date_type, Decimal] = {}
                for event_date, amount in sorted(entries, key=lambda item: item[0]):
                    running += amount
                    prefix[event_date] = running
                out[lot_id] = prefix
            return out

        return fees_by_lot, taxes_by_lot, _prefix(fees_dated), _prefix(taxes_dated)

    def _map_economic_groups(self, groups: Sequence[EconomicAllocationGroup]) -> list[EconomicAllocationGroupSchema]:
        """Map engine economic audit dataclasses to their inline-response Pydantic mirrors."""
        mapped: list[EconomicAllocationGroupSchema] = []
        for group in groups:
            mapped.append(
                EconomicAllocationGroupSchema(
                    economic_type=group.economic_type,
                    asset_id=group.asset_id,
                    broker_id=group.broker_id,
                    date=group.date,
                    native_currency=group.native_currency,
                    target_currency=group.target_currency,
                    rule=group.rule,
                    source_transaction_ids=list(group.source_transaction_ids),
                    native_pool_total=group.native_pool_total,
                    target_pool_total=group.target_pool_total,
                    native_orphan=group.native_orphan,
                    target_orphan=group.target_orphan,
                    operation_allocations=[
                        TargetOperationAllocationSchema(
                            context=operation.context,
                            operation_transaction_id=operation.operation_transaction_id,
                            weight=operation.weight,
                            lot_allocations=[
                                EconomicLotAllocationSchema(
                                    lot_id=allocation.lot_id,
                                    weight=allocation.weight,
                                    native_amount=allocation.native_amount,
                                    target_amount=allocation.target_amount,
                                )
                                for allocation in operation.lot_allocations
                            ],
                        )
                        for operation in group.operation_allocations
                    ],
                )
            )
        return mapped

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
        income_by_lot: dict[int, Decimal],
        fees_by_lot: dict[int, Decimal],
        taxes_by_lot: dict[int, Decimal],
        estimated_mode: bool,
        quote_base_quantity: int,
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
            raw_reference_price, raw_reference_currency, reference_date, reference_price_source = self._opening_reference_price(lot, price_lookup, quote_base_quantity)
            reference_unit_price = fx_resolver.convert(raw_reference_price, raw_reference_currency, reference_date)
            realized_pnl = self._converted_realized_pnl(lot, closures_by_lot.get(lot_id, []), fx_resolver)
            asset_income = income_by_lot.get(lot_id, Decimal("0"))
            opening_value = converted_original_cost if converted_original_cost is not None else lot.original_cost
            open_value = total_value = pnl = relative_return = None
            market_pnl: Decimal | None = None
            value_source: str | None = None
            if latest_market_price is not None:
                value_source = "MARKET_PRICE"
                open_value = compute_holding_value(lot.open_quantity, latest_market_price, quote_base_quantity)
                proceeds = converted_proceeds or Decimal("0")
                if lot.direction == "LONG":
                    total_value = open_value + proceeds
                    pnl = total_value - (converted_original_cost or Decimal("0"))
                else:
                    total_value = proceeds - open_value
                    pnl = total_value
                market_pnl = pnl - realized_pnl
                if reference_unit_price not in (None, Decimal("0")):
                    relative_return = (latest_market_price / reference_unit_price) - Decimal("1")
            elif estimated_mode and lot.direction == "LONG" and lot.original_quantity != Decimal("0"):
                # No current price: value the open portion at cost. Market P&L is 0 until a real price exists.
                value_source = "ESTIMATED_AT_COST"
                open_value = (opening_value or Decimal("0")) * lot.open_quantity / lot.original_quantity
                proceeds = converted_proceeds or Decimal("0")
                total_value = open_value + proceeds
                pnl = total_value - (converted_original_cost or Decimal("0"))
                market_pnl = Decimal("0")
            total_pnl = None
            if market_pnl is not None:
                total_pnl = market_pnl + realized_pnl + asset_income
            cash_yield = None
            total_return = None
            if opening_value is not None and opening_value > Decimal("0"):
                cash_yield = asset_income / opening_value
                if total_pnl is not None:
                    total_return = total_pnl / opening_value
            allocated_fees = fees_by_lot.get(lot_id, Decimal("0"))
            allocated_taxes = taxes_by_lot.get(lot_id, Decimal("0"))
            net_total_pnl = None
            net_total_return = None
            if total_pnl is not None:
                net_total_pnl = total_pnl - allocated_fees - allocated_taxes
                if opening_value is not None and opening_value > Decimal("0"):
                    net_total_return = net_total_pnl / opening_value
            closing_date = None
            if lot.open_quantity == Decimal("0"):
                lot_closures = closures_by_lot.get(lot_id, [])
                if lot_closures:
                    closing_date = max(closure.close_date for closure in lot_closures)
            out.append(
                LotSummarySchema(
                    lot_id=lot.lot_id,
                    opening_transaction_id=lot.opening_transaction_id,
                    asset_id=lot.asset_id,
                    direction=lot.direction,
                    opening_broker_id=lot.opening_broker_id,
                    opening_date=lot.opening_date,
                    closing_date=closing_date,
                    opening_unit_price=opening_unit_price if opening_unit_price is not None else lot.opening_unit_price,
                    original_quantity=lot.original_quantity,
                    original_cost=converted_original_cost if converted_original_cost is not None else lot.original_cost,
                    currency=lot.currency,
                    open_quantity=lot.open_quantity,
                    realized_quantity=lot.realized_quantity,
                    realized_pnl=realized_pnl,
                    cumulative_proceeds=converted_proceeds if converted_proceeds is not None else lot.cumulative_proceeds,
                    reference_unit_price=reference_unit_price,
                    reference_price_source=reference_price_source,
                    states=sorted(engine_result.get_lot_states(lot_id)),
                    current_custody=current_custody,
                    open_value=open_value,
                    total_value=total_value,
                    pnl=pnl,
                    relative_return=relative_return,
                    asset_income=asset_income,
                    market_pnl=market_pnl,
                    total_pnl=total_pnl,
                    cash_yield=cash_yield,
                    total_return=total_return,
                    value_source=value_source,
                    allocated_fees=allocated_fees,
                    allocated_taxes=allocated_taxes,
                    net_total_pnl=net_total_pnl,
                    net_total_return=net_total_return,
                    net_metrics_status="AVAILABLE",
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
        income_prefix_by_lot: dict[int, dict[date_type, Decimal]],
        fees_prefix_by_lot: dict[int, dict[date_type, Decimal]],
        taxes_prefix_by_lot: dict[int, dict[date_type, Decimal]],
        estimated_mode: bool,
        quote_base_quantity: int,
    ) -> list[LotValueHistoryPoint]:
        points: list[LotValueHistoryPoint] = []
        for lot_id in selected_ids:
            lot = lots_by_id[lot_id]
            last_date = self._lot_history_end_date(lot, closures_by_lot.get(lot_id, []), history_dates[-1], extend_closed=True)
            proceeds_by_day = self._closure_proceeds_prefix(lot, closures_by_lot.get(lot_id, []), fx_resolver)
            converted_original_cost = fx_resolver.convert(lot.original_cost, lot.currency, lot.opening_date) or lot.original_cost
            converted_short_proceeds = fx_resolver.convert(lot.cumulative_proceeds, lot.currency, lot.opening_date) or lot.cumulative_proceeds
            income_prefix = income_prefix_by_lot.get(lot_id, {})
            fees_prefix = fees_prefix_by_lot.get(lot_id, {})
            taxes_prefix = taxes_prefix_by_lot.get(lot_id, {})
            estimated_unit_value = converted_original_cost / lot.original_quantity if lot.original_quantity != Decimal("0") else Decimal("0")
            fragments = fragments_by_lot.get(lot_id, [])
            for current_date in history_dates:
                if current_date < lot.opening_date or current_date > last_date:
                    continue
                market_price = market_prices.get(current_date)
                if market_price is None:
                    open_quantity = self._open_quantity_on_date(fragments, current_date)
                    if open_quantity == Decimal("0"):
                        open_value = Decimal("0")
                        proceeds = self._prefix_value_on_date(proceeds_by_day, current_date)
                        if lot.direction == "LONG":
                            total_value = open_value + proceeds
                            pnl = total_value - converted_original_cost
                        else:
                            proceeds = converted_short_proceeds
                            total_value = proceeds - open_value
                            pnl = total_value
                    elif estimated_mode and lot.direction == "LONG" and lot.original_quantity != Decimal("0"):
                        open_value = open_quantity * estimated_unit_value
                        proceeds = self._prefix_value_on_date(proceeds_by_day, current_date)
                        total_value = open_value + proceeds
                        pnl = total_value - converted_original_cost
                    else:
                        continue
                else:
                    open_value, proceeds, total_value, pnl = self._value_snapshot_on_date(
                        lot=lot,
                        fragments=fragments,
                        proceeds_by_day=proceeds_by_day,
                        market_price=market_price,
                        current_date=current_date,
                        converted_original_cost=converted_original_cost,
                        converted_short_proceeds=converted_short_proceeds,
                        quote_base_quantity=quote_base_quantity,
                    )
                income = self._prefix_value_on_date(income_prefix, current_date)
                allocated_fees = self._prefix_value_on_date(fees_prefix, current_date)
                allocated_taxes = self._prefix_value_on_date(taxes_prefix, current_date)
                points.append(
                    LotValueHistoryPoint(
                        lot_id=lot_id,
                        date=current_date,
                        open_value=open_value,
                        proceeds=proceeds,
                        total_value=total_value,
                        original_cost=converted_original_cost,
                        pnl=pnl,
                        income=income,
                        allocated_fees=allocated_fees,
                        allocated_taxes=allocated_taxes,
                        net_pnl=pnl - allocated_fees - allocated_taxes,
                    )
                )
        return points

    def _build_return_history(
        self,
        *,
        selected_ids: Sequence[int],
        lots_by_id: dict[int, FifoLot],
        fragments_by_lot: dict[int, list[FragmentInterval]],
        market_prices: dict[date_type, Decimal | None],
        price_lookup: _PriceHistoryLookup,
        fx_resolver: _FxRateResolver,
        history_dates: Sequence[date_type],
        closures_by_lot: dict[int, list[LotClosure]],
        income_prefix_by_lot: dict[int, dict[date_type, Decimal]],
        fees_prefix_by_lot: dict[int, dict[date_type, Decimal]],
        taxes_prefix_by_lot: dict[int, dict[date_type, Decimal]],
        estimated_mode: bool,
        quote_base_quantity: int,
    ) -> list[LotReturnHistoryPoint]:
        points: list[LotReturnHistoryPoint] = []
        for lot_id in selected_ids:
            lot = lots_by_id[lot_id]
            raw_reference_price, raw_reference_currency, reference_date, reference_price_source = self._opening_reference_price(lot, price_lookup, quote_base_quantity)
            converted_reference = fx_resolver.convert(raw_reference_price, raw_reference_currency, reference_date)
            last_date = self._lot_history_end_date(lot, closures_by_lot.get(lot_id, []), history_dates[-1], extend_closed=True)
            proceeds_by_day = self._closure_proceeds_prefix(lot, closures_by_lot.get(lot_id, []), fx_resolver)
            converted_original_cost = fx_resolver.convert(lot.original_cost, lot.currency, lot.opening_date) or lot.original_cost
            converted_short_proceeds = fx_resolver.convert(lot.cumulative_proceeds, lot.currency, lot.opening_date) or lot.cumulative_proceeds
            income_prefix = income_prefix_by_lot.get(lot_id, {})
            fees_prefix = fees_prefix_by_lot.get(lot_id, {})
            taxes_prefix = taxes_prefix_by_lot.get(lot_id, {})
            estimated_unit_value = converted_original_cost / lot.original_quantity if lot.original_quantity != Decimal("0") else Decimal("0")
            fragments = fragments_by_lot.get(lot_id, [])
            for current_date in history_dates:
                if current_date < lot.opening_date or current_date > last_date:
                    continue
                market_price = market_prices.get(current_date)
                relative_return = None
                if market_price is None:
                    open_quantity = self._open_quantity_on_date(fragments, current_date)
                    if open_quantity == Decimal("0"):
                        open_value = Decimal("0")
                        proceeds = self._prefix_value_on_date(proceeds_by_day, current_date)
                        if lot.direction == "LONG":
                            total_value = open_value + proceeds
                        else:
                            proceeds = converted_short_proceeds
                            total_value = proceeds - open_value
                    elif estimated_mode and lot.direction == "LONG" and lot.original_quantity != Decimal("0"):
                        open_value = open_quantity * estimated_unit_value
                        proceeds = self._prefix_value_on_date(proceeds_by_day, current_date)
                        total_value = open_value + proceeds
                    else:
                        continue
                else:
                    open_value, proceeds, total_value, _pnl = self._value_snapshot_on_date(
                        lot=lot,
                        fragments=fragments,
                        proceeds_by_day=proceeds_by_day,
                        market_price=market_price,
                        current_date=current_date,
                        converted_original_cost=converted_original_cost,
                        converted_short_proceeds=converted_short_proceeds,
                        quote_base_quantity=quote_base_quantity,
                    )
                    if converted_reference not in (None, Decimal("0")):
                        relative_return = (market_price / converted_reference) - Decimal("1")
                income = self._prefix_value_on_date(income_prefix, current_date)
                allocated_fees = self._prefix_value_on_date(fees_prefix, current_date)
                allocated_taxes = self._prefix_value_on_date(taxes_prefix, current_date)
                total_return = None
                net_total_return = None
                if converted_original_cost != Decimal("0"):
                    total_return = ((total_value + income) / converted_original_cost) - Decimal("1")
                    net_total_return = ((total_value + income - allocated_fees - allocated_taxes) / converted_original_cost) - Decimal("1")
                points.append(
                    LotReturnHistoryPoint(
                        lot_id=lot_id,
                        date=current_date,
                        total_return=total_return,
                        relative_return=relative_return,
                        reference_price_source=reference_price_source if relative_return is not None else None,
                        income=income,
                        net_total_return=net_total_return,
                    )
                )
        return points

    def _opening_reference_price(
        self,
        lot: FifoLot,
        price_lookup: _PriceHistoryLookup,
        quote_base_quantity: int = 1,
    ) -> tuple[Decimal | None, str | None, date_type, ReferencePriceSource | None]:
        if lot.reference_unit_price is not None:
            resolved_reference = price_lookup.resolve(lot.opening_date)
            if resolved_reference is None:
                return None, None, lot.opening_date, lot.reference_price_source
            return lot.reference_unit_price, resolved_reference.currency, resolved_reference.resolved_date, lot.reference_price_source
        # No market quote at the opening date (e.g. a bond bought at emission, before it started
        # trading) → fall back to the lot's own buy price. opening_unit_price is per-single-unit
        # (cost / raw quantity), whereas market_price is quoted per quote_base_quantity units, so
        # scale it up to keep relative_return (= market_price / reference − 1) on one axis; otherwise
        # a qbq=100 bond reports ~9687% instead of ~−2%. No-op for qbq=1 (stocks). The resolved
        # branches above already return a per-quote market reference, so they need no scaling.
        scale = quote_base_quantity if quote_base_quantity > 0 else 1
        return lot.opening_unit_price * scale, lot.currency, lot.opening_date, "exact"

    def _value_snapshot_on_date(
        self,
        *,
        lot: FifoLot,
        fragments: Sequence[FragmentInterval],
        proceeds_by_day: dict[date_type, Decimal],
        market_price: Decimal,
        current_date: date_type,
        converted_original_cost: Decimal,
        converted_short_proceeds: Decimal,
        quote_base_quantity: int,
    ) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        open_value = self._open_value_on_date(fragments, market_price, current_date, quote_base_quantity)
        proceeds = self._prefix_value_on_date(proceeds_by_day, current_date)
        if lot.direction == "LONG":
            total_value = open_value + proceeds
            pnl = total_value - converted_original_cost
        else:
            proceeds = converted_short_proceeds
            total_value = proceeds - open_value
            pnl = total_value
        return open_value, proceeds, total_value, pnl

    def _build_price_history(
        self,
        *,
        selected_ids: Sequence[int],
        lots_by_id: dict[int, FifoLot],
        estimated_market_prices: dict[date_type, tuple[Decimal, bool]],
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
                entry = estimated_market_prices.get(current_date)
                if entry is None:
                    continue
                market_price, is_estimated = entry
                points.append(LotPriceHistoryPoint(lot_id=lot_id, date=current_date, market_price=market_price, currency=target_currency, estimated=is_estimated))
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

    def _lot_history_end_date(
        self,
        lot: FifoLot,
        closures: Sequence[LotClosure],
        fallback_end: date_type,
        *,
        extend_closed: bool = False,
    ) -> date_type:
        if extend_closed or lot.open_quantity > 0:
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

    def _open_value_on_date(self, fragments: Sequence[FragmentInterval], market_price: Decimal, query_date: date_type, quote_base_quantity: int) -> Decimal:
        return compute_holding_value(self._open_quantity_on_date(fragments, query_date), market_price, quote_base_quantity)

    def _open_quantity_on_date(self, fragments: Sequence[FragmentInterval], query_date: date_type) -> Decimal:
        return sum((fragment.quantity for fragment in fragments if _fragment_active_on_date(fragment, query_date)), Decimal("0"))

    def _fragment_in_scope(self, fragment: FragmentInterval, scope_broker_ids: set[int]) -> bool:
        if fragment.custody_type == "BROKER":
            return fragment.broker_id in scope_broker_ids
        return fragment.source_broker_id in scope_broker_ids and fragment.destination_broker_id in scope_broker_ids

    def _converted_external_amount(
        self,
        amount: Decimal,
        currency: str,
        as_of_date: date_type,
        fx_resolver: _FxRateResolver,
    ) -> Decimal:
        return fx_resolver.convert(amount, currency, as_of_date) or amount

    def _adjustment_cash_flow_cost(
        self,
        *,
        tx: Transaction,
        asset_currency: str,
        fx_resolver: _FxRateResolver,
    ) -> Decimal | None:
        if tx.cost_basis_override not in (None, Decimal("0")):
            total_cost = tx.quantity * tx.cost_basis_override
            return self._converted_external_amount(total_cost, tx.cost_basis_currency or asset_currency, tx.date, fx_resolver)
        if tx.amount != Decimal("0"):
            return self._converted_external_amount(abs(tx.amount), tx.currency or asset_currency, tx.date, fx_resolver)
        return None

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
        IssueCode.CURRENT_PRICE_ASSUMED_AT_COST: "dataQuality.currentPriceAssumedAtCost",
        IssueCode.ASSET_INCOME_NO_ELIGIBLE_LOTS: "dataQuality.assetIncomeNoEligibleLots",
        IssueCode.ASSET_COST_NO_ELIGIBLE_LOTS: "dataQuality.assetCostNoEligibleLots",
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
