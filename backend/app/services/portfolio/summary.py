"""The portfolio summary of ``PortfolioService``: holdings, brokers, groups and performance."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Transaction,
    TransactionType,
)
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import (
    AllocationItem,
    AssetAllocationItem,
    BrokerBreakdown,
    HoldingGroupGainLoss,
    MissingPriceAsset,
    PortfolioHolding,
    PortfolioSummary,
    StalePriceAsset,
)
from backend.app.schemas.wac import WACMissingPairInfo
from backend.app.services.financial_math.holding_window import oldest_open_lot_date, quantity_moves
from backend.app.services.financial_math.portfolio import period as period_math
from backend.app.services.financial_math.returns import (
    annualized_to_cumulative,
    calculate_simple_roi,
    change_ratio,
    cumulative_to_annualized,
    gain_loss_ratio,
    group_gain_loss,
    net_holding_return,
    period_mwrr,
    period_twrr,
    realized_gain,
    rebase_to_period,
    timing_effect,
)
from backend.app.services.financial_math.splits import split_linked_ids
from backend.app.services.financial_math.valuation import compute_holding_value
from backend.app.services.financial_math.weights import percent_of
from backend.app.services.financial_math.yield_on_cost import (
    YieldOnCostPositionInput,
    calculate_yield_on_cost_for_positions,
)
from backend.app.services.portfolio import engine_facts
from backend.app.utils.datetime_utils import latest_range_end


class PortfolioSummaryMixin:
    """The portfolio summary of ``PortfolioService``: holdings, brokers, groups and performance.

    Mixed into ``PortfolioService`` (``portfolio_service.py``), which provides ``db``.
    """

    db: AsyncSession

    async def get_summary(  # noqa: C901 — TODO(P2-refactor): nested broker/tx/asset accumulation; extract per-position builder
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        include_breakdown: bool = False,
        target_currency_override: str | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        _precomputed_engine_result=None,
    ) -> PortfolioSummary:
        """Return aggregated portfolio summary via PortfolioCalculationEngine.

        Uses the new engine for aggregate values (NAV, market_value, book_value,
        allocation, performance) and derives holding rows from end-of-period
        position snapshots.

        _precomputed_engine_result: if provided by get_report(), skip engine re-run.
        """
        from backend.app.services.financial_math.portfolio.data_quality import transaction_implied_assets_to_report  # noqa: PLC0415
        from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder  # noqa: PLC0415
        from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine  # noqa: PLC0415
        from backend.app.services.financial_math.portfolio.models import ValuationSource  # noqa: PLC0415
        from backend.app.services.platform.data_quality_thresholds import TRANSACTION_IMPLIED_GRACE_DAYS  # noqa: PLC0415

        today = date_type.today()
        # R13-SEC7-1: the summary's whole horizon (engine run, MWRR, stale prices, annualization) ends by latest_range_end()
        if date_to is not None:
            date_to = min(date_to, latest_range_end())
        valuation_date = date_to or today
        if date_from is not None:
            date_from = min(date_from, valuation_date)
        base_currency = target_currency_override or await self._get_base_currency(user_id)

        # ── 1. Run engine for aggregate values + performance ──
        if _precomputed_engine_result is not None:
            engine_result = _precomputed_engine_result
        else:
            engine = PortfolioCalculationEngine(self.db)
            engine_result = await engine.calculate(
                user_id=user_id,
                broker_ids=broker_ids,
                date_from=None,
                date_to=date_to,
                target_currency=base_currency,
            )

        views = DerivedViewsBuilder(engine_result.daily_states, base_currency)

        # ── 2. Extract aggregate values from last daily state ──
        # Looked up by date (not blindly daily_states[-1]) as a guard against a
        # stale/wider cached blob leaking states beyond the requested valuation_date.
        last_state = period_math.state_as_of(engine_result.daily_states, valuation_date)
        engine_nav = last_state.nav_value if last_state else Decimal("0")
        engine_cash = last_state.cash_value if last_state else Decimal("0")
        engine_market_value = last_state.market_value if last_state else Decimal("0")

        # ── 3. Broker cash / realized P&L + end-of-period holdings snapshot ──
        accesses = await self._get_user_broker_access(user_id, broker_ids)

        total_invested = Decimal("0")
        all_cash_balances: dict[str, Decimal] = defaultdict(Decimal)
        all_holdings: list[PortfolioHolding] = []
        by_broker_list: list[BrokerBreakdown] = []
        all_missing_pairs: list[WACMissingPairInfo] = []
        missing_price_assets: list[MissingPriceAsset] = []
        broker_names: dict[int, str] = {}
        first_position_dates: dict[tuple[int, int], date_type] = {}
        # Holding-transaction streams per (broker, asset) for FIFO oldest-open-lot derivation.
        lot_txns_by_key: dict[tuple[int, int], list[Transaction]] = defaultdict(list)

        # Cash, deposits, income and costs come from the engine's native cash: the same
        # movements, each at its broker's share and converted at its own date. A movement
        # with no rate on its date is left out of values and flows, still counted in its own
        # currency, and reported as a missing pair with that date.
        native_cash = engine_facts._engine_native_cash(engine_result, base_currency)
        period_flows = native_cash.flows(date_from, valuation_date)
        # Per-position income and fee/tax totals over the position's whole life (<= valuation
        # date), used for the net holding return that feeds the annualized column.
        lifetime_flows = native_cash.flows(None, valuation_date)
        _total_deposited = period_flows.absolute_by_type.get(TransactionType.DEPOSIT, Decimal("0"))
        _total_withdrawn = period_flows.absolute_by_type.get(TransactionType.WITHDRAWAL, Decimal("0"))
        # Signed: a legacy negative DIVIDEND/INTEREST correction must reduce period_income,
        # not be folded into the "Other" reconciliation residual via abs() (plan §4.4).
        _income_accum = Decimal("0") + period_flows.signed_by_type.get(TransactionType.DIVIDEND, Decimal("0")) + period_flows.signed_by_type.get(TransactionType.INTEREST, Decimal("0"))
        _fees_accum = period_flows.absolute_by_type.get(TransactionType.FEE, Decimal("0"))
        _taxes_accum = period_flows.absolute_by_type.get(TransactionType.TAX, Decimal("0"))
        _fees_taxes_accum = Decimal("0") + _fees_accum + _taxes_accum
        income_by_pos = lifetime_flows.income_by_position
        fees_taxes_by_pos = lifetime_flows.costs_by_position
        all_missing_pairs.extend(WACMissingPairInfo(pair=missing.pair, dates=list(missing.dates)) for missing in native_cash.missing_conversions(None, valuation_date))

        for access in accesses:
            broker_id = access.broker_id
            broker = await self._get_broker(broker_id)
            broker_name = broker.name if broker else f"Broker {broker_id}"
            broker_names[broker_id] = broker_name

            # Same horizon as the engine: without date_to it stops at today, so a row dated
            # later must not reach the lots either.
            broker_txns = await self._get_transactions(broker_id, date_to=valuation_date)

            # Holding transactions — lot streams and first position dates
            for tx in broker_txns:
                if tx.asset_id is not None and tx.type in engine_facts._LOT_AFFECTING_TYPES:
                    lot_txns_by_key[(broker_id, tx.asset_id)].append(tx)
                if tx.type not in engine_facts._HOLDING_TYPES or tx.asset_id is None:
                    continue
                pos_key = (broker_id, tx.asset_id)
                if pos_key not in first_position_dates or tx.date < first_position_dates[pos_key]:
                    first_position_dates[pos_key] = tx.date

        # Realized G/L of the SELLs and outgoing ADJUSTMENTs (proceeds 0, N78-1) in the period: proceeds minus the
        # historical cost the engine's average-cost pool gave up, both in base currency with the owner's share.
        _realized_accum = sum((gain for sale in period_math.period_realized_sales(engine_result.realized_sales, date_from, date_to) if (gain := realized_gain(sale.proceeds, sale.cost)) is not None), Decimal("0"))

        lot_split_ids = await split_linked_ids(self.db, [tx for txns in lot_txns_by_key.values() for tx in txns])
        # MF-A10: the moves at the run's share (the owner's, or the whole broker: MF6-3), as the engine's quantities the rows
        # test against the dust threshold
        lot_shares = engine_result.broker_shares
        oldest_open_lot_dates: dict[tuple[int, int], Optional[date_type]] = {key: oldest_open_lot_date(quantity_moves(txns, lot_split_ids, share=lot_shares[key[0]])) for key, txns in lot_txns_by_key.items()}
        # First lot-affecting transaction per position (includes ADJUSTMENT/TRANSFER, so
        # in-kind/succession/snapshot-seeded positions get a real window start — unlike
        # first_position_dates which only tracks BUY/SELL). Anchors the net annualized window.
        first_lot_txn_dates: dict[tuple[int, int], date_type] = {key: min(t.date for t in txns) for key, txns in lot_txns_by_key.items() if txns}

        end_positions = [ps for ps in engine_result.position_states_end if ps.quantity > engine_facts._QUANTITY_DUST_THRESHOLD]
        marks = getattr(engine_result, "marks", None)
        yield_on_cost_by_position = await calculate_yield_on_cost_for_positions(
            self.db,
            user_id=user_id,
            positions=[
                YieldOnCostPositionInput(
                    asset_id=position.asset_id,
                    broker_id=position.broker_id,
                    wac_per_unit=position.wac,
                    wac_currency=position.wac_currency,
                )
                for position in end_positions
            ],
            target_currency=base_currency,
            as_of_date=valuation_date,
        )
        assets_map = await self._get_assets_map({ps.asset_id for ps in end_positions})
        brokers_map = await self._get_brokers_map({ps.broker_id for ps in end_positions})

        for ps in end_positions:
            asset = assets_map.get(ps.asset_id)
            if not asset:
                continue

            broker = brokers_map.get(ps.broker_id)
            broker_name = broker.name if broker else broker_names.get(ps.broker_id, f"Broker {ps.broker_id}")

            # MF6-1 (T-U5): the unit prices come from the engine's reader, as the replay valued them, converted at the
            # day's rate; a missing rate is the engine's to report (the position's missing_fx_pair)
            current_price: Decimal | None = None
            if ps.valuation_effective_unit_price is not None and ps.valuation_effective_currency is not None:
                if ps.valuation_effective_currency == base_currency:
                    current_price = ps.valuation_effective_unit_price
                elif marks is not None:
                    current_price = marks.in_target(ps.valuation_effective_unit_price, ps.valuation_effective_currency, ps.date)

            yield_on_cost_calculation = yield_on_cost_by_position[(ps.asset_id, ps.broker_id)]
            wac_per_unit = yield_on_cost_calculation.wac_per_unit
            all_missing_pairs.extend(yield_on_cost_calculation.missing_fx_pairs)

            current_value = ps.market_value

            gain_loss = ps.unrealized_pnl
            gain_loss_pct = gain_loss_ratio(gain_loss, ps.cost_basis, positive_base=False)

            price_change_1d: Decimal | None = None
            gain_loss_change_1d: Decimal | None = None
            gain_loss_change_1d_percent: Decimal | None = None
            if ps.valuation_source == "MARKET_PRICE" and current_price is not None and marks is not None:
                # The day before: the last market quote on or before it, converted at that day's rate (a mark is converted
                # on the day it is read); none on a day the engine did not replay
                day_before = ps.date - timedelta(days=1)
                previous = marks.last_market_price_at(ps.asset_id, day_before)
                if previous is not None:
                    prev_price_base = marks.in_target(previous.unit_price, previous.currency, day_before)
                    if prev_price_base is not None and prev_price_base != 0:
                        # MF-A12 (N92): the change over the size of the previous price, measured as the % column measures
                        # the value's (the same association: a tie rounds as before); a negative price's change keeps the
                        # move's sign, as the % column's does
                        price_ratio_1d = change_ratio(current_price - prev_price_base, prev_price_base)
                        price_change_1d = price_ratio_1d.quantize(Decimal("0.0001")) if price_ratio_1d is not None else None
                        # Bugfix: raw quoted prices (current_price/prev_price_base) are NOT
                        # 1 unit == 1 currency unit for every asset — e.g. bonds are quoted
                        # "per quote_base_quantity" (BTPs: quote_base_quantity=100, price=98.70
                        # means 98.70 per 100 nominal). market_value/gain_loss above already go
                        # through compute_holding_value() to apply that scaling; a naive
                        # `(current_price - prev_price_base) * ps.quantity` here skipped it,
                        # inflating the daily delta by quote_base_quantity× for such assets
                        # (reported: a BTP position showed a +93.60% "1-day" P&L swing).
                        # Reuse compute_holding_value for both legs so the scaling matches.
                        current_position_value = compute_holding_value(ps.quantity, current_price, asset.quote_base_quantity)
                        previous_position_value = compute_holding_value(ps.quantity, prev_price_base, asset.quote_base_quantity)
                        gain_loss_change_1d = current_position_value - previous_position_value
                        if abs(previous_position_value) > Decimal("0.01"):
                            value_ratio_1d = change_ratio(gain_loss_change_1d, previous_position_value)
                            gain_loss_change_1d_percent = (value_ratio_1d * 100).quantize(Decimal("0.01")) if value_ratio_1d is not None else None

            if ps.valuation_source == "MISSING":
                missing_price_assets.append(
                    MissingPriceAsset(
                        asset_id=ps.asset_id,
                        symbol=asset.identifier_ticker,
                        name=asset.display_name,
                        broker_id=ps.broker_id,
                        broker_name=broker_name,
                        first_position_date=first_position_dates.get((ps.broker_id, ps.asset_id)),
                        quantity=ps.quantity,
                        open_cost_basis=ps.cost_basis if ps.cost_basis != 0 else None,
                        currency=base_currency,
                    )
                )

            # Net annualized return of the still-open position over its full life
            # (first lot-affecting transaction -> valuation date). Net = unrealized
            # (valued at cost, i.e. 0 market P&L, when the price is missing) + income
            # (coupons/dividends) - fees/taxes, normalized by cost basis. This makes a
            # no-price position with coupons (e.g. an unquoted BTP) show an income-only
            # return instead of "—", and includes income/costs per the product rule.
            holding_first_tx = first_lot_txn_dates.get((ps.broker_id, ps.asset_id))
            holding_annualized = None
            if ps.cost_complete and ps.cost_basis and ps.cost_basis != 0 and holding_first_tx is not None:
                pos_income = income_by_pos.get((ps.broker_id, ps.asset_id), Decimal("0"))
                pos_fees = fees_taxes_by_pos.get((ps.broker_id, ps.asset_id), Decimal("0"))
                holding_return = net_holding_return(gain_loss, pos_income, pos_fees, ps.cost_basis)
                holding_annualized = cumulative_to_annualized(holding_return, (valuation_date - holding_first_tx).days)

            all_holdings.append(
                PortfolioHolding(
                    asset_id=ps.asset_id,
                    asset_name=asset.display_name,
                    asset_ticker=asset.identifier_ticker,
                    asset_type=asset.asset_type.value if asset.asset_type else "Unknown",
                    broker_id=ps.broker_id,
                    broker_name=broker_name,
                    quantity=ps.quantity,
                    wac_per_unit=wac_per_unit,
                    current_price=current_price,
                    current_value=current_value,
                    valuation_source=ps.valuation_source.value,
                    valuation_effective_unit_price=ps.valuation_effective_unit_price,
                    valuation_effective_currency=ps.valuation_effective_currency,
                    valuation_reference_date=ps.valuation_reference_date,
                    valuation_reference_unit_price=ps.valuation_reference_unit_price,
                    valuation_reference_currency=ps.valuation_reference_currency,
                    valuation_split_adjusted=ps.valuation_split_adjusted,
                    missing_fx_pair=ps.missing_fx_pair,
                    gain_loss=gain_loss,
                    gain_loss_percent=gain_loss_pct,
                    annualized_return=holding_annualized,
                    price_change_1d=price_change_1d,
                    gain_loss_change_1d=gain_loss_change_1d,
                    gain_loss_change_1d_percent=gain_loss_change_1d_percent,
                    oldest_open_lot_date=oldest_open_lot_dates.get((ps.broker_id, ps.asset_id)),
                    yield_on_cost=yield_on_cost_calculation.result if yield_on_cost_calculation is not None else None,
                    allocation_percent=None,
                )
            )

        # Each card's cash is its native balances valued at valuation_date's rates; the headline
        # lists every currency held, summed over the cards. A broker whose movements are all
        # zero has no value of its own: its cash is its report-currency balance.
        native_balances = native_cash.balances(valuation_date)
        cash_values = native_cash.value_at(valuation_date)
        broker_cash_base = {broker_id: cash_values.get(broker_id, native_balances.get(broker_id, {}).get(base_currency, Decimal("0"))) for broker_id in broker_names}
        for broker_id in broker_names:
            for ccy, amt in native_balances.get(broker_id, {}).items():
                all_cash_balances[ccy] += amt

        if include_breakdown:
            for broker_id, broker_name in broker_names.items():
                # Each card is the engine's per-broker slice of the headline on valuation_date
                # (the cards add up to it): market value, cash at that day's rates and the value
                # in transit, which stays on the sender's card; capital moves on arrival, so an
                # internal transfer never shows -X / +X.
                contribution = last_state.broker_contributions.get(broker_id) if last_state is not None else None
                broker_capital = contribution.capital_contribution if contribution is not None else Decimal("0")
                broker_nav = contribution.nav_contribution if contribution is not None else Decimal("0")
                broker_gain = contribution.pnl_contribution if contribution is not None else Decimal("0")
                broker_gl_ratio = gain_loss_ratio(broker_gain, broker_capital, positive_base=True)
                broker_gl_pct = broker_gl_ratio if broker_gl_ratio is not None else Decimal("0")
                by_broker_list.append(
                    BrokerBreakdown(
                        broker_id=broker_id,
                        broker_name=broker_name,
                        net_worth=Currency(code=base_currency, amount=broker_nav),
                        gain_loss=Currency(code=base_currency, amount=broker_gain),
                        gain_loss_percent=broker_gl_pct,
                        cash_total=Currency(code=base_currency, amount=broker_cash_base.get(broker_id, Decimal("0"))),
                        cash_balances=[Currency(code=ccy, amount=amt) for ccy, amt in native_balances.get(broker_id, {}).items()],
                    )
                )

        # ── 4. Allocation from engine (scope-aware, includes in-transit) ──
        alloc_type, alloc_sector, alloc_geo = views.build_allocation_current()
        last_by_asset = views.daily_states[-1].by_asset if views.daily_states else {}
        alloc_asset_rows = await self._get_assets_map(set(last_by_asset))
        alloc_asset_names = {asset_id: asset.display_name for asset_id, asset in alloc_asset_rows.items()}
        alloc_asset = views.build_asset_allocation_current(alloc_asset_names)
        # The pie draws each asset's icon (F-10): the asset's own, else its type's. Presentation only, no figure changes.
        for item in alloc_asset:
            row = alloc_asset_rows.get(item.get("id")) if item.get("id") is not None else None
            if row is not None:
                item["asset_type"] = row.asset_type.value if row.asset_type is not None else None
                item["icon_url"] = row.icon_url or None

        def _alloc_from_engine(items: list[dict]) -> list[AllocationItem]:
            return [AllocationItem(**item) for item in items]

        def _asset_alloc_from_engine(items: list[dict]) -> list[AssetAllocationItem]:
            return [AssetAllocationItem(**item) for item in items]

        # Weights from the house (D-MF7): no share of a total at or below zero — the field stays None («—»).
        total_market = sum((h.current_value for h in all_holdings if h.current_value), Decimal("0"))
        for h in all_holdings:
            if not h.current_value:
                continue
            allocation = percent_of(h.current_value, total_market)
            nav_weight = percent_of(h.current_value, engine_nav)
            object.__setattr__(h, "allocation_percent", allocation.quantize(Decimal("0.01")) if allocation is not None else None)
            object.__setattr__(h, "nav_weight_percent", nav_weight.quantize(Decimal("0.01")) if nav_weight is not None else None)

        # ── 5. Performance from engine (correct daily NAV) ──
        nav_snapshots, cash_flows_perf = views.build_performance_inputs(date_from)

        # Period re-basing: when date_from is set, compute metrics for that period only
        period = rebase_to_period(nav_snapshots, cash_flows_perf, date_from)
        period_cfs = list(period.cash_flows)
        period_navs = list(period.nav_snapshots)
        period_start_date_perf = period.start_date if period.start_date is not None else today

        # Net invested for the period (sum of deposits minus withdrawals), from the same flows as the ROI line (MF-K3)
        period_net_invested = sum(-cf.amount for cf in views.build_roi_cash_flows(date_from, nav_snapshots, cash_flows_perf))
        simple_roi = calculate_simple_roi(engine_nav, period_net_invested) if period_net_invested > 0 else Decimal("0")
        mwrr_result: Decimal | None = None
        # The Dashboard's TWRR rule lives in the house: the card is the last point of the line (MF-K3), «—» at a value at
        # or below zero
        twrr_result = period_twrr(period_navs, period_cfs)
        # The Dashboard's MWRR rule lives in the house: the card is the last point of the line by construction
        # (D-MF5): no rate without net invested capital or with a value at or below zero.
        mwrr_result = (await asyncio.to_thread(period_mwrr, period_navs, period_cfs, date_to or today, engine_nav)).mwrr

        # ── MWRR cumulative derivation ──
        mwrr_period_days: int | None = None
        mwrr_cumulative: Decimal | None = None
        if period_navs:
            mwrr_period_days = ((date_to or today) - period_start_date_perf).days
            mwrr_cumulative = annualized_to_cumulative(mwrr_result, mwrr_period_days) if mwrr_result is not None else None

        # Headline invested capital & P&L come from the engine's capital baseline
        # (cumulative_external_cash_flow), which folds in priced in-kind ADJUSTMENT
        # capital (opening equity / succession). Deriving total_gl from a cash-only
        # "invested" would treat that in-kind capital as pure profit, inflating the
        # headline gain to thousands of percent on in-kind-seeded portfolios. The
        # engine's total_pnl = NAV - capital_baseline is the authoritative figure.
        if last_state is not None:
            total_invested = last_state.cumulative_external_cash_flow
            total_gl = last_state.total_pnl
        else:
            total_gl = engine_nav - total_invested
        total_gl_ratio = gain_loss_ratio(total_gl, total_invested, positive_base=True)
        total_gl_pct = total_gl_ratio if total_gl_ratio is not None else Decimal("0")
        cash_balances_list = [Currency(code=ccy, amount=amt) for ccy, amt in all_cash_balances.items()]

        # ── Period P&L breakdown: NAV, unrealized delta, income, fees ──
        period_figures = period_math.period_pnl(getattr(engine_result, "daily_states", None) or [], date_from, valuation_date)
        period_nav_start_val = period_figures.nav_start if period_figures is not None else None
        period_net_flows_val = period_figures.net_flows if period_figures is not None else None
        period_pnl_val = period_figures.pnl if period_figures is not None else None
        period_ugl_start = period_figures.ugl_start if period_figures is not None else None
        period_ugl_end = period_figures.ugl_end if period_figures is not None else None
        period_ugl_delta = period_figures.ugl_delta if period_figures is not None else None
        period_book_value_start_val = period_figures.book_value_start if period_figures is not None else None
        period_market_value_start_val = period_figures.market_value_start if period_figures is not None else None
        period_realized_val: Decimal | None = None
        period_income_val: Decimal | None = None
        period_fees_taxes_val: Decimal | None = None
        period_other_result_val: Decimal | None = None

        if period_pnl_val is not None and period_ugl_delta is not None:
            # Realized, income, fees from accumulated values
            period_realized_val = _realized_accum
            period_income_val = _income_accum if _income_accum else Decimal("0")
            period_fees_taxes_val = _fees_taxes_accum if _fees_taxes_accum else Decimal("0")

            # Other result: residual that closes the identity
            # pnl = ugl_delta + realized + income - fees_taxes + other_result
            period_other_result_val = period_math.period_other_result(period_pnl_val, period_ugl_delta, period_realized_val, period_income_val, period_fees_taxes_val)

        # ── 6. Data quality report ──
        # "Valued at cost" is an *as-of* statement (dataQuality.transactionImplied:
        # "…as of {as_of_date}"): evaluate ONLY the valuation-date state, so an asset that
        # has since received a real market quote clears the warning even if it was
        # transaction-implied for most of its earlier history. The previous behaviour
        # unioned the flag across every day of the asset's lifetime, permanently flagging
        # any asset ever valued at cost — e.g. funds that only get quotes from their first
        # provider sync onward stayed flagged forever despite a fresh current price.
        # The grace period still suppresses a brand-new acquisition whose first market
        # price simply has not landed yet (e.g. BTP collocamento lag); it counts from the
        # last market quote (decision 30), see transaction_implied_assets_to_report.
        first_position_date_by_asset: dict[int, date_type] = {}
        for (_b_id, a_id), d in first_position_dates.items():
            if a_id not in first_position_date_by_asset or d < first_position_date_by_asset[a_id]:
                first_position_date_by_asset[a_id] = d
        # W-B94: an asset priced only by the cost of the transfer that brought it in has no BUY or SELL; its grace counts
        # from its first lot movement, the arrival, as the at-cost grace does
        first_lot_date_by_asset: dict[int, date_type] = {}
        for (_b_id, a_id), d in first_lot_txn_dates.items():
            if a_id not in first_lot_date_by_asset or d < first_lot_date_by_asset[a_id]:
                first_lot_date_by_asset[a_id] = d
        for a_id, d in first_lot_date_by_asset.items():
            first_position_date_by_asset.setdefault(a_id, d)

        implied_asset_ids: set[int] = set()
        if last_state is not None:
            implied_asset_ids = transaction_implied_assets_to_report(
                last_state.transaction_implied_asset_ids,
                last_state.transaction_implied_last_quote_dates,
                first_position_date_by_asset,
                last_state.date,
                TRANSACTION_IMPLIED_GRACE_DAYS,
            )

        transaction_implied_assets: list[MissingPriceAsset] = []
        for ps in end_positions:
            if ps.asset_id in implied_asset_ids:
                asset = assets_map.get(ps.asset_id)
                if not asset:
                    continue
                broker = brokers_map.get(ps.broker_id)
                transaction_implied_assets.append(
                    MissingPriceAsset(
                        asset_id=ps.asset_id,
                        symbol=asset.identifier_ticker,
                        name=asset.display_name,
                        broker_id=ps.broker_id,
                        broker_name=broker.name if broker else broker_names.get(ps.broker_id, f"Broker {ps.broker_id}"),
                        first_position_date=first_position_dates.get((ps.broker_id, ps.asset_id)),
                        quantity=ps.quantity,
                        open_cost_basis=ps.cost_basis if ps.cost_basis != 0 else None,
                        currency=base_currency,
                    )
                )

        # For manual assets (no provider, valued at cost): suppress MISSING_PRICE
        # They're already represented by TRANSACTION_IMPLIED which is expected behavior
        from backend.app.db.models import AssetProviderAssignment  # noqa: PLC0415

        provider_result = await self.db.execute(select(AssetProviderAssignment.asset_id))
        assets_with_provider = {row[0] for row in provider_result.fetchall()}
        # Remove from missing_price_assets if the asset is manual (no provider) AND implied (valued at cost)
        missing_price_assets = [a for a in missing_price_assets if a.asset_id in assets_with_provider or a.asset_id not in implied_asset_ids]
        # For truly manual assets (implied, no provider): suppress TRANSACTION_IMPLIED too
        # since cost valuation is their intended/permanent behavior
        manual_implied_ids = implied_asset_ids - assets_with_provider
        transaction_implied_assets = [a for a in transaction_implied_assets if a.asset_id not in manual_implied_ids]

        # VALUED_AT_COST: an open position with no price at all (no quote, no BUY or SELL, no transfer-cost estimate:
        # W-B94), counted at its book cost (J-17). Same grace as TRANSACTION_IMPLIED, counted from the asset's first
        # acquisition: it has no quote, and no BUY or SELL (an ADJUSTMENT or a TRANSFER opened it), so the BUY/SELL
        # first position date would list it at once. Only for an asset with a provider: for a manual
        # asset the cost is its intended value.
        first_acquisition_by_asset: dict[int, date_type] = {}
        for (_b_id, a_id), d in first_lot_txn_dates.items():
            if a_id not in first_acquisition_by_asset or d < first_acquisition_by_asset[a_id]:
                first_acquisition_by_asset[a_id] = d
        at_cost_ids = {ps.asset_id for ps in end_positions if ps.valuation_source == ValuationSource.ESTIMATED_AT_COST}
        at_cost_reported = transaction_implied_assets_to_report(at_cost_ids, {}, first_acquisition_by_asset, last_state.date, TRANSACTION_IMPLIED_GRACE_DAYS) if last_state is not None else set()
        valued_at_cost_assets: list[MissingPriceAsset] = []
        for ps in end_positions:
            if ps.asset_id not in at_cost_reported or ps.asset_id not in assets_with_provider:
                continue
            asset = assets_map.get(ps.asset_id)
            if not asset:
                continue
            broker = brokers_map.get(ps.broker_id)
            valued_at_cost_assets.append(
                MissingPriceAsset(
                    asset_id=ps.asset_id,
                    symbol=asset.identifier_ticker,
                    name=asset.display_name,
                    broker_id=ps.broker_id,
                    broker_name=broker.name if broker else broker_names.get(ps.broker_id, f"Broker {ps.broker_id}"),
                    first_position_date=first_lot_txn_dates.get((ps.broker_id, ps.asset_id)),
                    quantity=ps.quantity,
                    open_cost_basis=ps.cost_basis if ps.cost_basis != 0 else None,
                    currency=base_currency,
                )
            )

        # STALE_PRICE: an open position valued at a market price carried forward past the
        # threshold, for an asset with a provider — the case a price sync can fix. A manual
        # asset valued at its last trade price (crowdfunding, HOLD) is stale by design, and a
        # provider asset with no quote at all is TRANSACTION_IMPLIED's or VALUED_AT_COST's case. One entry per asset.
        stale_price_dates: dict[int, date_type] = {}
        for ps in end_positions:
            if not ps.valuation_stale or ps.valuation_source != ValuationSource.MARKET_PRICE:
                continue
            if ps.asset_id not in assets_with_provider or ps.valuation_reference_date is None:
                continue
            known = stale_price_dates.get(ps.asset_id)
            stale_price_dates[ps.asset_id] = ps.valuation_reference_date if known is None else max(known, ps.valuation_reference_date)
        stale_prices = [StalePriceAsset(asset_id=asset_id, name=assets_map[asset_id].display_name, last_price_date=last_date, stale_days=(valuation_date - last_date).days) for asset_id, last_date in sorted(stale_price_dates.items(), key=lambda item: (item[1], item[0])) if asset_id in assets_map]

        configured_fx_pairs, real_provider_fx_pairs = await self._get_configured_fx_pair_sets()
        all_missing_pairs.extend(engine_facts._engine_missing_fx_pairs(engine_result, date_from, valuation_date))
        merged_missing_fx_pairs = self._merge_missing_pairs(all_missing_pairs)
        held_quote_facts = await self._held_asset_quote_facts(engine_result)
        data_quality = views.build_data_quality_report(
            missing_price_assets_dto=missing_price_assets,
            stale_prices_dto=stale_prices or None,
            missing_fx_pairs_dto=merged_missing_fx_pairs,
            transaction_implied_assets_dto=transaction_implied_assets if transaction_implied_assets else None,
            missing_cost_basis_assets=await self._missing_cost_basis_assets(engine_result) or None,
            invalid_split_assets=await self._invalid_split_assets(engine_result) or None,
            non_iso_currency_assets=self._non_iso_currency_assets(held_quote_facts) or None,
            report_currency=base_currency,
            valued_at_cost_assets_dto=valued_at_cost_assets or None,
            mwrr_available=mwrr_result is not None,
            share_mismatches=engine_result.share_mismatches,
            configured_fx_pairs=configured_fx_pairs,
            real_provider_fx_pairs=real_provider_fx_pairs,
            period_from=date_from,
            period_to=valuation_date,
        )

        # The day's change of the total P&L, from the engine's states of the valuation date and of the calendar day before.
        day_change = period_math.day_change(engine_result.daily_states, valuation_date)

        # Unrealized G/L of each broker's holdings, and of each asset type at each broker (the Dashboard treemap's groups).
        group_members: dict[tuple[int, str | None], list[tuple[Decimal | None, Decimal | None]]] = defaultdict(list)
        for holding in all_holdings:
            group_members[(holding.broker_id, None)].append((holding.current_value, holding.gain_loss))
            group_members[(holding.broker_id, holding.asset_type)].append((holding.current_value, holding.gain_loss))
        holding_groups: list[HoldingGroupGainLoss] = []
        for (group_broker_id, group_asset_type), members in sorted(group_members.items(), key=lambda item: (item[0][0], item[0][1] is not None, item[0][1] or "")):
            group_gain, group_ratio = group_gain_loss(members)
            holding_groups.append(
                HoldingGroupGainLoss(
                    broker_id=group_broker_id,
                    asset_type=group_asset_type,
                    gain_loss=Currency(code=base_currency, amount=group_gain) if group_gain is not None else None,
                    gain_loss_percent=group_ratio,
                )
            )

        return PortfolioSummary(
            net_worth=Currency(code=base_currency, amount=engine_nav),
            total_invested=Currency(code=base_currency, amount=total_invested),
            total_gain_loss=Currency(code=base_currency, amount=total_gl),
            total_gain_loss_percent=total_gl_pct,
            cash_total=Currency(code=base_currency, amount=engine_cash),
            cash_balances=cash_balances_list,
            market_value=Currency(code=base_currency, amount=engine_market_value),
            broker_nav_value=Currency(code=base_currency, amount=last_state.broker_nav_value) if last_state else None,
            in_transit_market_value=Currency(code=base_currency, amount=last_state.in_transit_market_value) if last_state and last_state.in_transit_market_value else None,
            open_cost_basis=Currency(code=base_currency, amount=last_state.open_cost_basis) if last_state else None,
            in_transit_book_value=Currency(code=base_currency, amount=last_state.in_transit_book_value) if last_state and last_state.in_transit_book_value else None,
            book_value=Currency(code=base_currency, amount=last_state.book_value) if last_state else None,
            unrealized_gain_loss=Currency(code=base_currency, amount=last_state.unrealized_gain_loss) if last_state else None,
            total_deposited=Currency(code=base_currency, amount=_total_deposited) if _total_deposited else None,
            total_withdrawn=Currency(code=base_currency, amount=_total_withdrawn) if _total_withdrawn else None,
            net_deposited_capital=Currency(code=base_currency, amount=_total_deposited - _total_withdrawn),
            period_nav_start=Currency(code=base_currency, amount=period_nav_start_val) if period_nav_start_val is not None else None,
            period_market_value_start=Currency(code=base_currency, amount=period_market_value_start_val) if period_market_value_start_val is not None else None,
            period_book_value_start=Currency(code=base_currency, amount=period_book_value_start_val) if period_book_value_start_val is not None else None,
            period_net_flows=Currency(code=base_currency, amount=period_net_flows_val) if period_net_flows_val is not None else None,
            period_pnl=Currency(code=base_currency, amount=period_pnl_val) if period_pnl_val is not None else None,
            period_unrealized_gain_loss_start=Currency(code=base_currency, amount=period_ugl_start) if period_ugl_start is not None else None,
            period_unrealized_gain_loss_end=Currency(code=base_currency, amount=period_ugl_end) if period_ugl_end is not None else None,
            period_unrealized_gain_loss_delta=Currency(code=base_currency, amount=period_ugl_delta) if period_ugl_delta is not None else None,
            period_unrealized_breakdown=engine_facts._unrealized_breakdown_rows(engine_result, date_from, valuation_date, base_currency) if period_ugl_delta is not None else [],
            period_realized_gain_loss=Currency(code=base_currency, amount=period_realized_val) if period_realized_val is not None else None,
            period_income=Currency(code=base_currency, amount=period_income_val) if period_income_val is not None else None,
            period_fees_taxes=Currency(code=base_currency, amount=period_fees_taxes_val) if period_fees_taxes_val is not None else None,
            period_fees=Currency(code=base_currency, amount=_fees_accum) if _fees_accum else None,
            period_taxes=Currency(code=base_currency, amount=_taxes_accum) if _taxes_accum else None,
            period_other_result=Currency(code=base_currency, amount=period_other_result_val) if period_other_result_val is not None else None,
            twrr_percent=twrr_result,
            mwrr_annualized_percent=mwrr_result,
            mwrr_cumulative_percent=mwrr_cumulative,
            mwrr_period_days=mwrr_period_days,
            timing_effect_percent=timing_effect(mwrr_cumulative, twrr_result),
            pnl_change_1d=Currency(code=base_currency, amount=day_change.pnl_change) if day_change is not None else None,
            pnl_change_1d_vs_nav_percent=day_change.vs_nav if day_change is not None else None,
            simple_roi_percent=simple_roi,
            allocation_by_type=_alloc_from_engine(alloc_type),
            allocation_by_sector=_alloc_from_engine(alloc_sector),
            allocation_by_geography=_alloc_from_engine(alloc_geo),
            allocation_by_asset=_asset_alloc_from_engine(alloc_asset),
            holdings=all_holdings,
            holding_groups=holding_groups,
            by_broker=by_broker_list if include_breakdown else None,
            missing_fx_pairs=merged_missing_fx_pairs,
            missing_price_assets=missing_price_assets,
            data_quality=data_quality,
        )
