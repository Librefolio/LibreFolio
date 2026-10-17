from __future__ import annotations

from collections import defaultdict
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Iterable, Mapping, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType
from backend.app.schemas.portfolio import (
    DataQualityIssue,
    DataQualityReport,
    GanttSegmentSchema,
    IssueCode,
    IssueDomain,
    IssueSeverity,
    LotAnalysisStatus,
    LotAnalysisType,
    LotsAnalysisMetadata,
    LotsAnalysisResponse,
    LotSummarySchema,
    LotTimelineEventKind,
    LotTimelineEventSchema,
)
from backend.app.schemas.wac import WACMissingPairInfo
from backend.app.services.accounts.settings_service import get_effective_base_currency
from backend.app.services.financial_math.average_cost import AverageCost, CostPosition, compute_average_costs, cost_movement_from_transaction
from backend.app.services.financial_math.fifo.engine import run_fifo_lot_engine
from backend.app.services.financial_math.fifo.models import EconomicAllocationGroup, EconomicEvent, FifoDataQualityIssue, FifoEngineResult, FifoEvent, FifoInputTransaction, FifoLot, FragmentInterval, LotClosure, ReferencePriceResolution
from backend.app.services.financial_math.lots.average_cost_lines import ALL_BROKERS, build_broker_wac_history, build_cumulative_wac_history
from backend.app.services.financial_math.lots.conversions import FxRateResolver, collect_fx_needs, collect_performance_fx_needs, convert_closure, needs_market_series, unconvertible_ids
from backend.app.services.financial_math.lots.economic_events import NOTHING_WITHHELD, WithheldEconomics, build_cost_economic_events, build_engine_transactions, build_income_economic_events, extract_cost_outputs, extract_income_outputs, map_economic_groups, withheld_economics
from backend.app.services.financial_math.lots.histories import (
    PerformanceSourceContext,
    build_performance_history,
    build_price_history,
    build_return_history,
    build_value_history,
    fragment_active_on_date,
    group_closures,
    group_fragments,
    known_buyback_cost,
    known_cumulative_proceeds,
    known_realized_pnl,
    trim_dates,
)
from backend.app.services.financial_math.lots.prices import last_day_without_observation, opening_reference_price
from backend.app.services.financial_math.lots.summary import lot_summary_figures
from backend.app.services.financial_math.portfolio.data_quality import build_data_quality_report, load_configured_fx_pair_sets
from backend.app.services.financial_math.price_marks import AssetPriceSeries, MarkSource, build_asset_price_series
from backend.app.services.financial_math.splits import load_split_links
from backend.app.services.financial_math.valuation import normalize_quote_base_quantity
from backend.app.utils.datetime_utils import latest_range_end

_WARNING_ISSUE_CODES = {
    IssueCode.REFERENCE_PRICE_FALLBACK,
    IssueCode.REFERENCE_PRICE_UNAVAILABLE,
    IssueCode.CURRENT_PRICE_ASSUMED_AT_COST,
    IssueCode.ASSET_INCOME_NO_ELIGIBLE_LOTS,
    IssueCode.ASSET_COST_NO_ELIGIBLE_LOTS,
}

_ORPHAN_ISSUE_CODES = {
    IssueCode.ASSET_INCOME_NO_ELIGIBLE_LOTS,
    IssueCode.ASSET_COST_NO_ELIGIBLE_LOTS,
}

_CUSTODY_KINDS = {
    LotTimelineEventKind.BUY,
    LotTimelineEventKind.ADJUSTMENT_IN,
    LotTimelineEventKind.TRANSFER_DEPART,
    LotTimelineEventKind.TRANSFER_ARRIVE,
}


class LotsAnalysisService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_lots_analysis(  # noqa: C901 — TODO(P2-refactor): long orchestrator; extract per-analysis stage helpers
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

        target_currency = target_currency or await self._get_base_currency(user_id)
        # R13-SEC7-1: the histories walk every day to actual_to, so it ends by latest_range_end()
        actual_to = min(date_to or date_type.today(), latest_range_end())
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
        quote_base_quantity = normalize_quote_base_quantity(asset.quote_base_quantity)
        # The unified price resolver is the SINGLE valuation brain for this asset: fed the
        # asset-system price rows AND every observed trade (BUY/SELL; an ADJUSTMENT is never a price)
        # in native currency, it resolves each day to a real quote (exact or carried/LOCF) or, when
        # none exists, to the same-day / last-observed trade mark. Built before the FIFO engine, it
        # gives a lot opened by an ADJUSTMENT its reference price (CP-7b), and after the engine it
        # values the open lots and draws the chart price line, so lots-analysis shares one price
        # model with the portfolio engine.
        price_series = build_asset_price_series(
            price_rows=[(row.date, row.close, row.currency) for row in prices],
            transactions=transactions,
            split_linked_tx_ids=set(split_ratios_by_tx_id),
            asset_currency=asset.currency,
            quote_base_quantity=quote_base_quantity,
        )
        income_transactions = await self._load_income_transactions(asset_id=asset_id, scope_broker_ids=scope_broker_ids, date_to=actual_to)
        cost_transactions = await self._load_cost_transactions(asset_id=asset_id, scope_broker_ids=scope_broker_ids, date_to=actual_to)

        def reference_price_lookup(resolved_asset_id: int, opened_at: date_type) -> ReferencePriceResolution | None:
            if resolved_asset_id != asset_id:
                return None
            mark = price_series.resolve(opened_at)
            if mark.is_missing:
                return None
            # ``exact`` only for a market quote of that day; a carried quote or a trade mark is a fallback.
            return ReferencePriceResolution(price=mark.unit_price, source="exact" if mark.source is MarkSource.MARKET else "fallback")

        # Resolve economic FX and build events BEFORE the engine run: the engine is target-value
        # aware (Option B), so it needs each event's pre-converted target amount and each trade's
        # target controvalue (FEE weights, §3.5). Eligibility (D-1 open quantity, broker-scoped,
        # transfer-aware) and matching are computed inside the engine from the replayed fragments.
        # Valuation FX is resolved after the run (below).
        fx_resolver = FxRateResolver(target_currency)
        needs_income_alloc = any(analysis in normalized_analyses for analysis in (LotAnalysisType.LOT_SUMMARY, LotAnalysisType.VALUE_HISTORY, LotAnalysisType.RETURN_HISTORY, LotAnalysisType.INCOME_EVENTS))
        income_events_input: list[EconomicEvent] = []
        cost_events_input: list[EconomicEvent] = []
        engine_transactions: Sequence[Transaction | FifoInputTransaction] = transactions
        unconvertible_event_ids: set[int] = set()
        unconvertible_trade_ids: set[int] = set()
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
            # An event or a trade weight without a rate still reaches the engine, which places it; every
            # figure of the pools it touches is withheld below (``withheld_economics``).
            unconvertible_event_ids = unconvertible_ids([*income_transactions, *cost_transactions], fx_resolver, asset.currency)
            if income_transactions:
                income_events_input = build_income_economic_events(
                    income_transactions=income_transactions,
                    fx_resolver=fx_resolver,
                    asset_currency=asset.currency,
                    target_currency=target_currency,
                )
            if cost_transactions:
                cost_events_input = build_cost_economic_events(
                    cost_transactions=cost_transactions,
                    fx_resolver=fx_resolver,
                    asset_currency=asset.currency,
                    target_currency=target_currency,
                )
                engine_transactions = build_engine_transactions(transactions, fx_resolver, asset.currency, target_currency)
                unconvertible_trade_ids = unconvertible_ids([tx for tx in transactions if tx.type in (TransactionType.BUY, TransactionType.SELL)], fx_resolver, asset.currency)

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
        fragments_by_lot = group_fragments(engine_result.fragment_intervals)
        closures_by_lot = group_closures(engine_result.closures)
        tx_by_id = {tx.id: tx for tx in transactions if tx.id is not None}
        withheld = withheld_economics(
            engine_result.economic_allocation_groups,
            unconvertible_event_ids=unconvertible_event_ids,
            unconvertible_trade_ids=unconvertible_trade_ids,
            trade_currency_by_id={tx_id: tx.currency or asset.currency for tx_id, tx in tx_by_id.items()},
        )
        display_from = date_from or computed_from
        history_dates = list(_date_range(computed_from, actual_to))
        # A day with no observation on or before it — no quote, no BUY or SELL — values the open lots at cost, as the
        # Dashboard values a holding (J-17). Those days run from the first transaction to the day before the first
        # observation, or to the end when the asset has none: then the current price too is assumed at cost.
        at_cost_until = last_day_without_observation(price_series, history_dates)

        performance_context = PerformanceSourceContext(
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
                    target_currency=target_currency,
                )
                performance_lots_by_id = {lot.lot_id: lot for lot in performance_engine_result.lots}
                performance_context = PerformanceSourceContext(
                    transactions=performance_transactions,
                    engine_result=performance_engine_result,
                    lots_by_id=performance_lots_by_id,
                    fragments_by_lot=group_fragments(performance_engine_result.fragment_intervals),
                    closures_by_lot=group_closures(performance_engine_result.closures),
                    tx_by_id={tx.id: tx for tx in performance_transactions if tx.id is not None},
                )

        collect_fx_needs(
            fx_resolver=fx_resolver,
            analyses=normalized_analyses,
            lots_by_id=lots_by_id,
            selected_ids=selected_ids,
            transactions=transactions,
            price_series=price_series,
            prices=prices,
            fragments=engine_result.fragment_intervals,
            events=engine_result.classified_events,
            closures=engine_result.closures,
            split_ratios_by_tx_id=split_ratios_by_tx_id,
            actual_to=actual_to,
            computed_from=computed_from,
            asset_currency=asset.currency,
        )
        collect_performance_fx_needs(
            fx_resolver=fx_resolver,
            analyses=normalized_analyses,
            transactions=performance_context.transactions,
            closures=performance_context.engine_result.closures,
            lots_by_id=performance_context.lots_by_id,
            asset_currency=asset.currency,
        )
        if needs_income_alloc and at_cost_until is not None:
            # Estimated-at-cost values the open portion at converted opening cost -> needs fx@opening.
            for lot in lots_by_id.values():
                fx_resolver.need(lot.currency, lot.opening_date)
        await fx_resolver.load(self.db)

        income_by_lot, income_prefix_by_lot, income_events_payload = extract_income_outputs(engine_result, income_events_input, withheld)
        fees_by_lot, taxes_by_lot, fees_prefix_by_lot, taxes_prefix_by_lot = extract_cost_outputs(engine_result)

        data_quality = self._build_data_quality_report(engine_result.issues, engine_result.economic_allocation_groups, withheld)
        if at_cost_until is not None and needs_market_series(normalized_analyses):
            # [computed_from, at_cost_until] has no observation (no quote, no BUY or SELL), so it is valued at
            # cost: the whole window when the asset has none. Surface it in the message so the user knows which
            # period is uncovered (per user feedback on delisted/matured titles).
            data_quality.issues.append(
                DataQualityIssue(
                    domain=IssueDomain.PORTFOLIO,
                    code=IssueCode.CURRENT_PRICE_ASSUMED_AT_COST,
                    severity=IssueSeverity.WARNING,
                    message_i18n_key="dataQuality.currentPriceAssumedAtCostRange",
                    message_params={"asset_id": asset_id, "date_from": computed_from.isoformat(), "date_to": at_cost_until.isoformat()},
                )
            )
        # The histories read every day's price, the summary only the last one: value no other day, so the
        # report never holds the gap of a day nobody reads.
        daily_series = any(analysis in normalized_analyses for analysis in (LotAnalysisType.VALUE_HISTORY, LotAnalysisType.RETURN_HISTORY, LotAnalysisType.PRICE_HISTORY, LotAnalysisType.PERFORMANCE_HISTORY))
        active_price_dates = history_dates if daily_series else ([actual_to] if LotAnalysisType.LOT_SUMMARY in normalized_analyses else [])
        # Both the open-lot valuation (``market_prices`` -> NAV / value / return / performance) and the
        # chart price line (``estimated_market_prices``) read the series built above. Each native mark is
        # converted to the target currency at *its own valuation date* (per-day FX, never frozen at the
        # observation date); ``None`` marks a day the resolver has no observation for (genuine MISSING),
        # or whose price cannot be converted: that day is not valued, never at the native price.
        # Downstream only a day with no observation on or before it (``at_cost_until``) falls back to cost.
        market_prices: dict[date_type, Decimal | None] = {}
        estimated_market_prices: dict[date_type, tuple[Decimal, bool]] = {}
        for current_date in active_price_dates:
            mark = price_series.resolve(current_date)
            if mark.is_missing:
                market_prices[current_date] = None
                continue
            converted = fx_resolver.convert(mark.unit_price, mark.currency, current_date)
            market_prices[current_date] = converted
            if converted is not None:
                estimated_market_prices[current_date] = (converted, mark.estimated)
        average_cost_lines: dict[int | str, AverageCost] = {}
        if LotAnalysisType.BROKER_WAC_HISTORY in normalized_analyses or LotAnalysisType.CUMULATIVE_WAC_HISTORY in normalized_analyses:
            average_cost_lines = await self._compute_average_cost_lines(
                transactions=transactions,
                split_ratios_by_tx_id=split_ratios_by_tx_id,
                asset_currency=asset.currency,
                target_currency=target_currency,
            )

        lots = None
        if LotAnalysisType.LOT_SUMMARY in normalized_analyses:
            lots = self._build_lot_summaries(
                engine_result=engine_result,
                lots_by_id=lots_by_id,
                selected_ids=selected_ids,
                fx_resolver=fx_resolver,
                market_prices=market_prices,
                price_series=price_series,
                closures_by_lot=closures_by_lot,
                income_by_lot=income_by_lot,
                fees_by_lot=fees_by_lot,
                taxes_by_lot=taxes_by_lot,
                estimated_mode=at_cost_until == actual_to,
                quote_base_quantity=quote_base_quantity,
                analysis_end=actual_to,
                withheld=withheld,
            )

        gantt_segments = None
        if LotAnalysisType.GANTT_TOPOLOGY in normalized_analyses:
            gantt_segments = self._build_gantt_segments(engine_result.fragment_intervals, selected_ids, lots_by_id, fx_resolver)

        # Event rows are built only when returned: the report holds no gap of a figure nobody asked for.
        lot_events: list[LotTimelineEventSchema] = []
        if LotAnalysisType.CUSTODY_HISTORY in normalized_analyses or LotAnalysisType.EVENT_HISTORY in normalized_analyses:
            lot_events = self._build_lot_event_rows(
                engine_result=engine_result,
                selected_ids=selected_ids,
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
            value_history = trim_dates(
                build_value_history(
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
                    at_cost_until=at_cost_until,
                    quote_base_quantity=quote_base_quantity,
                    withheld=withheld,
                ),
                display_from,
                actual_to,
            )

        return_history = None
        if LotAnalysisType.RETURN_HISTORY in normalized_analyses:
            return_history = trim_dates(
                build_return_history(
                    selected_ids=selected_ids,
                    lots_by_id=lots_by_id,
                    fragments_by_lot=fragments_by_lot,
                    market_prices=market_prices,
                    price_series=price_series,
                    fx_resolver=fx_resolver,
                    history_dates=history_dates,
                    closures_by_lot=closures_by_lot,
                    income_prefix_by_lot=income_prefix_by_lot,
                    fees_prefix_by_lot=fees_prefix_by_lot,
                    taxes_prefix_by_lot=taxes_prefix_by_lot,
                    at_cost_until=at_cost_until,
                    quote_base_quantity=quote_base_quantity,
                    withheld=withheld,
                ),
                display_from,
                actual_to,
            )

        price_history = None
        if LotAnalysisType.PRICE_HISTORY in normalized_analyses:
            price_history = trim_dates(
                build_price_history(
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
            broker_wac_history = trim_dates(
                build_broker_wac_history(scope_broker_ids, average_cost_lines, history_dates),
                display_from,
                actual_to,
            )

        cumulative_wac_history = None
        if LotAnalysisType.CUMULATIVE_WAC_HISTORY in normalized_analyses:
            cumulative_wac_history = trim_dates(
                build_cumulative_wac_history(average_cost_lines, history_dates),
                display_from,
                actual_to,
            )

        performance_history = None
        if LotAnalysisType.PERFORMANCE_HISTORY in normalized_analyses:
            performance_history = trim_dates(
                build_performance_history(
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
            economic_allocation_groups = map_economic_groups(engine_result.economic_allocation_groups, withheld)

        # Every builder has converted what it needed: report, once, what could not be converted or costed.
        conversion_gaps = fx_resolver.missing_pairs()
        await self._report_gaps(data_quality, average_cost_lines, conversion_gaps, target_currency, asset)

        return LotsAnalysisResponse(
            asset_id=asset_id,
            target_currency=target_currency,
            quote_base_quantity=quote_base_quantity,
            # A gap (a missing rate or cost basis) is isolable: DEGRADED.
            calculation_status=("DEGRADED" if engine_result.analysis_status == "COMPLETE" and (conversion_gaps or any(line.has_missing_report_fx or line.unknown_cost_movement_ids for line in average_cost_lines.values())) else engine_result.analysis_status),
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
            asset_orphan_income=None if "income" in withheld.orphan_unknown else engine_result.asset_orphan_income,
            asset_orphan_fees=None if "fees" in withheld.orphan_unknown else engine_result.asset_orphan_fees,
            asset_orphan_taxes=None if "taxes" in withheld.orphan_unknown else engine_result.asset_orphan_taxes,
        )

    async def _get_base_currency(self, user_id: int) -> str:
        """Effective base currency: per-user setting, global default, EUR (P0-1)."""
        return await get_effective_base_currency(self.db, user_id)

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
        ``FifoLotEngine._allocate_income_pools`` and ``build_income_economic_events``).
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
        (see ``FifoLotEngine._allocate_cost_pools`` and ``build_cost_economic_events``). FEE/TAX
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
        return {link.transaction_id: link.ratio for link in await load_split_links(self.db, transactions)}

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

    async def _compute_average_cost_lines(
        self,
        *,
        transactions: Sequence[Transaction],
        split_ratios_by_tx_id: dict[int, Decimal],
        asset_currency: str,
        target_currency: str,
    ) -> dict[int | str, AverageCost]:
        """Average cost per broker and for all the brokers together, in target currency.

        One financial_math.average_cost call: each acquisition converted at its own date,
        missing conversions reported instead of falling back to the unconverted cost.
        ``transactions`` arrive ordered by (date, id), the replay order of the pools.
        """
        movements_by_broker: dict[int, list] = defaultdict(list)
        all_movements: list = []
        for tx in transactions:
            movement = cost_movement_from_transaction(tx, asset_currency=asset_currency, split_linked=tx.id in split_ratios_by_tx_id)
            if movement is None:
                continue
            movements_by_broker[tx.broker_id].append(movement)
            all_movements.append(movement)
        positions = [CostPosition(key=broker_id, asset_currency=asset_currency, movements=tuple(movements)) for broker_id, movements in movements_by_broker.items()]
        positions.append(CostPosition(key=ALL_BROKERS, asset_currency=asset_currency, movements=tuple(all_movements)))
        return await compute_average_costs(self.db, positions, report_currency=target_currency, asset_leg=False)

    async def _report_gaps(
        self,
        data_quality: DataQualityReport,
        lines: dict[int | str, AverageCost],
        conversion_gaps: Sequence[WACMissingPairInfo],
        target_currency: str,
        asset: Asset,
    ) -> None:
        """Put what the analysis could not compute in the data quality, as the portfolio banner does.

        Conversions that could not be made — by the average-cost lines and by every other figure of the
        analysis — become ``missing_fx_pairs`` (pair and dates, merged) and their FX issues; an
        acquisition without a known cost becomes a ``MISSING_COST_BASIS`` issue.
        """
        dates_by_pair: dict[str, set[date_type]] = defaultdict(set)
        for line in lines.values():
            for missing in line.missing:
                if missing.leg == "report":
                    dates_by_pair[missing.pair].update(missing.dates)
        for gap in conversion_gaps:
            dates_by_pair[gap.pair].update(gap.dates)
        unknown_cost = any(line.unknown_cost_movement_ids for line in lines.values())
        if not dates_by_pair and not unknown_cost:
            return
        missing_pairs = [WACMissingPairInfo(pair=pair, dates=sorted(dates)) for pair, dates in sorted(dates_by_pair.items())]
        configured_pairs, real_provider_pairs = await load_configured_fx_pair_sets(self.db) if missing_pairs else (set(), set())
        gap_report = build_data_quality_report(
            [],
            missing_fx_pairs_dto=missing_pairs or None,
            missing_cost_basis_assets=[(asset.id, asset.display_name)] if unknown_cost else None,
            configured_fx_pairs=configured_pairs,
            real_provider_fx_pairs=real_provider_pairs,
        )
        data_quality.issues.extend(gap_report.issues)
        data_quality.missing_fx_pairs.extend(missing_pairs)

    def _build_lot_summaries(  # noqa: C901 — flat per-lot field packing, valuation-variant if/elif
        self,
        *,
        engine_result: FifoEngineResult,
        lots_by_id: dict[int, FifoLot],
        selected_ids: Sequence[int],
        fx_resolver: FxRateResolver,
        market_prices: dict[date_type, Decimal | None],
        price_series: AssetPriceSeries,
        closures_by_lot: dict[int, list[LotClosure]],
        income_by_lot: dict[int, Decimal],
        fees_by_lot: dict[int, Decimal],
        taxes_by_lot: dict[int, Decimal],
        estimated_mode: bool,
        quote_base_quantity: int,
        analysis_end: date_type,
        withheld: WithheldEconomics = NOTHING_WITHHELD,
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
            known_proceeds = known_cumulative_proceeds(lot, closures_by_lot.get(lot_id, []), fx_resolver)
            # A short lot's closing purchases (0 for a long lot): its P&L is what it sold minus what it bought back.
            known_buybacks = known_buyback_cost(lot, closures_by_lot.get(lot_id, []), fx_resolver)
            converted_original_cost = fx_resolver.convert(lot.original_cost, lot.currency, lot.opening_date)
            opening_unit_price = fx_resolver.convert(lot.opening_unit_price, lot.currency, lot.opening_date)
            raw_reference_price, raw_reference_currency, reference_date, reference_price_source = opening_reference_price(lot, price_series, quote_base_quantity)
            reference_unit_price = fx_resolver.convert(raw_reference_price, raw_reference_currency, reference_date)
            lot_realized_pnl = known_realized_pnl(lot, closures_by_lot.get(lot_id, []), fx_resolver)
            # A lot reached by an economic pool without a rate has that income, fee or tax unknown.
            asset_income = None if lot_id in withheld.income_from else income_by_lot.get(lot_id, Decimal("0"))
            allocated_fees = None if lot_id in withheld.fees_from else fees_by_lot.get(lot_id, Decimal("0"))
            allocated_taxes = None if lot_id in withheld.taxes_from else taxes_by_lot.get(lot_id, Decimal("0"))
            closing_date = None
            if lot.open_quantity == Decimal("0"):
                lot_closures = closures_by_lot.get(lot_id, [])
                if lot_closures:
                    closing_date = max(closure.close_date for closure in lot_closures)
            # Every figure reads converted amounts only (financial_math.lots.summary): a missing rate leaves it
            # unknown, never computed from the native cost, proceeds, realized P&L, income or costs.
            figures = lot_summary_figures(
                lot=lot,
                original_cost=converted_original_cost,
                known_proceeds=known_proceeds,
                known_buybacks=known_buybacks,
                realized_pnl=lot_realized_pnl,
                latest_market_price=latest_market_price,
                reference_unit_price=reference_unit_price,
                income=asset_income,
                fees=allocated_fees,
                taxes=allocated_taxes,
                estimated_mode=estimated_mode,
                quote_base_quantity=quote_base_quantity,
                closing_date=closing_date,
                analysis_end=analysis_end,
            )
            out.append(
                LotSummarySchema(
                    lot_id=lot.lot_id,
                    opening_transaction_id=lot.opening_transaction_id,
                    asset_id=lot.asset_id,
                    direction=lot.direction,
                    opening_broker_id=lot.opening_broker_id,
                    opening_date=lot.opening_date,
                    closing_date=closing_date,
                    opening_unit_price=opening_unit_price,
                    original_quantity=lot.original_quantity,
                    original_cost=converted_original_cost,
                    currency=lot.currency,
                    open_quantity=lot.open_quantity,
                    realized_quantity=lot.realized_quantity,
                    realized_pnl=lot_realized_pnl,
                    cumulative_proceeds=known_proceeds,
                    reference_unit_price=reference_unit_price,
                    # T-B6: a reference that could not be converted has no source, as in the return history.
                    reference_price_source=reference_price_source if reference_unit_price is not None else None,
                    states=sorted(engine_result.get_lot_states(lot_id)),
                    current_custody=current_custody,
                    open_value=figures.open_value,
                    total_value=figures.total_value,
                    pnl=figures.pnl,
                    relative_return=figures.relative_return,
                    asset_income=asset_income,
                    market_pnl=figures.market_pnl,
                    total_pnl=figures.total_pnl,
                    cash_yield=figures.cash_yield,
                    total_return=figures.total_return,
                    annualized_return=figures.annualized_return,
                    value_source=figures.value_source,
                    allocated_fees=allocated_fees,
                    allocated_taxes=allocated_taxes,
                    net_total_pnl=figures.net_total_pnl,
                    net_total_return=figures.net_total_return,
                    net_metrics_status="UNAVAILABLE" if withheld.reaches(lot_id) else "AVAILABLE",
                )
            )
        return out

    def _build_gantt_segments(
        self,
        fragments: Sequence[FragmentInterval],
        selected_ids: Sequence[int],
        lots_by_id: dict[int, FifoLot],
        fx_resolver: FxRateResolver,
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
                    unit_price=converted_unit_price,
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
        fx_resolver: FxRateResolver,
        lots_by_id: dict[int, FifoLot],
    ) -> list[LotTimelineEventSchema]:
        selected = set(selected_ids)
        rows: list[LotTimelineEventSchema] = []
        rows.extend(self._build_opening_and_split_rows(engine_result, selected, fx_resolver, lots_by_id))
        rows.extend(self._build_transfer_rows(engine_result.fragment_intervals, selected, lots_by_id, fx_resolver))
        rows.extend(self._build_closure_rows(engine_result.closures, selected, lots_by_id, fx_resolver))
        return sorted(rows, key=lambda row: (row.date, row.lot_id, row.transaction_id, row.kind))

    def _build_opening_and_split_rows(
        self,
        engine_result: FifoEngineResult,
        selected: set[int],
        fx_resolver: FxRateResolver,
        lots_by_id: dict[int, FifoLot],
    ) -> list[LotTimelineEventSchema]:
        rows: list[LotTimelineEventSchema] = []
        for event in engine_result.classified_events:
            if event.kind in {"BUY", "ADJUSTMENT_IN"}:
                lot_id = event.transaction_id
                if lot_id not in selected:
                    continue
                # The opening price is in the lot's currency: a BUY's own, the cost basis's for a priced ADJUSTMENT.
                lot = lots_by_id[lot_id]
                converted_unit_price = fx_resolver.convert(event.unit_price, lot.currency, event.date)
                # V11: the value the lot opened at, the summary's original cost, in the same currency as the price.
                opening_value = fx_resolver.convert(lot.original_cost, lot.currency, lot.opening_date)
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
                        opening_value=opening_value,
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
        fx_resolver: FxRateResolver,
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
        fx_resolver: FxRateResolver,
    ) -> list[LotTimelineEventSchema]:
        rows: list[LotTimelineEventSchema] = []
        for closure in closures:
            if closure.lot_id not in selected:
                continue
            lot = lots_by_id[closure.lot_id]
            converted = convert_closure(closure, lot, fx_resolver)
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
                    unit_price=converted.close_unit_price,
                    open_unit_price=converted.open_unit_price,
                    close_unit_price=converted.close_unit_price,
                    realized_pnl=converted.realized_pnl,
                    proceeds=converted.proceeds,
                    ratio=None,
                )
            )
        return rows

    def _build_data_quality_report(
        self,
        issues: Sequence[FifoDataQualityIssue],
        groups: Sequence[EconomicAllocationGroup] = (),
        withheld: WithheldEconomics = NOTHING_WITHHELD,
    ) -> DataQualityReport:
        mapped = []
        for issue in issues:
            code = IssueCode(issue.code)
            params = self._orphan_issue_params(issue, groups, withheld) if code in _ORPHAN_ISSUE_CODES else issue.params
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
                        **params,
                    },
                )
            )
        return DataQualityReport(issues=mapped)

    @staticmethod
    def _orphan_issue_params(issue: FifoDataQualityIssue, groups: Sequence[EconomicAllocationGroup], withheld: WithheldEconomics) -> Mapping[str, object]:
        """The params of an orphan issue, whose amount is never the native placeholder in the target currency.

        An orphan pool with an event without a rate has no target amount: the engine filled it with the native
        placeholder. Its issue then states the pool in its own currency, the one its amount is known in; the
        message keys keep their names. The issue's transaction is the pool's first source.
        """
        for index in withheld.amount_degraded:
            group = groups[index]
            if not group.operation_allocations and issue.transaction_id in group.source_transaction_ids:
                return {**issue.params, "target_amount": group.native_pool_total, "target_currency": group.native_currency}
        return issue.params

    def _impacted_lot_ids_for_split(self, event: FifoEvent, fragments: Sequence[FragmentInterval]) -> set[int]:
        impacted: set[int] = set()
        for fragment in fragments:
            if not fragment_active_on_date(fragment, event.date):
                continue
            if fragment.custody_type == "BROKER" and fragment.broker_id == event.broker_id:
                impacted.add(fragment.lot_id)
            elif fragment.custody_type == "IN_TRANSIT" and (fragment.source_broker_id == event.broker_id or fragment.destination_broker_id == event.broker_id):
                impacted.add(fragment.lot_id)
        return impacted


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
