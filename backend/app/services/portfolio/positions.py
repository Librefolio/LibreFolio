"""The per-position views of ``PortfolioService``: period contribution and position series."""

from __future__ import annotations

from collections import defaultdict
from datetime import date as date_type
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Transaction,
)
from backend.app.schemas.common import DateSpan
from backend.app.schemas.portfolio.positions_series import PositionSeries, PositionSeriesPoint, PositionsSeriesQuery, PositionsSeriesResponse
from backend.app.schemas.portfolio.summary import AssetPeriodContribution, OtherPeriodEffect, OtherPeriodEffectCode, PositionsContribution, UnallocatedContribution
from backend.app.services.financial_math.holding_window import closed_position_window, exits_in, oldest_open_lot_date, quantity_moves
from backend.app.services.financial_math.native_cash import CONVERSION_DUST
from backend.app.services.financial_math.portfolio import period as period_math
from backend.app.services.financial_math.portfolio.contributions import (
    annualized_period_return,
    closed_flight_too_short,
    closed_position_annualized,
    closed_position_base,
    period_return_on_start,
    position_period_pnl,
    transfer_costs_moved_out,
    transfer_tract_adjustments,
    transfer_tracts_moved_in,
    window_start,
)
from backend.app.services.financial_math.portfolio.position_series import acquisitions_from_average_costs, build_position_series
from backend.app.services.financial_math.returns import (
    realized_gain,
)
from backend.app.services.financial_math.splits import split_linked_ids
from backend.app.services.portfolio import engine_facts
from backend.app.utils.datetime_utils import latest_range_end


class PortfolioPositionsMixin:
    """The per-position views of ``PortfolioService``: period contribution and position series.

    Mixed into ``PortfolioService`` (``portfolio_service.py``), which provides ``db``.
    """

    db: AsyncSession

    async def get_positions_contribution(  # noqa: C901 — TODO(P2-refactor): nested broker/asset accumulation with per-position valuation branches
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        target_currency_override: str | None = None,
        _precomputed_engine_result=None,
        apply_ownership_share: bool = True,
    ) -> PositionsContribution:
        """Compute per-asset period P&L contribution for dashboard Performance view.

        For each (broker_id, asset_id) pair with activity in the period, computes:
        - unrealized_delta: change in unrealized P&L over the period
        - realized_gain_loss: gain/loss from SELLs in the period
        - income: DIVIDEND/INTEREST attributed to this asset
        - fees_taxes: FEE/TAX attributed to this asset
        - period_pnl: total = unrealized_delta + realized + income - fees_taxes

        Fees/taxes without asset_id go to raw unallocated buckets plus UX-ready
        other_effects rows. Each broker's exchange result on foreign cash is an
        other_effects row of its own ("FX on cash"), ahead of the reconciliation residual.
        """
        today = date_type.today()
        effective_end = date_to or today
        base_currency = target_currency_override or await self._get_base_currency(user_id)

        accesses = await self._get_user_broker_access(user_id, broker_ids)
        if not accesses:
            return PositionsContribution(gross_gains=Decimal("0"), gross_losses=Decimal("0"))

        engine_result = _precomputed_engine_result
        # Without a shared run, or with one taken for another period start (no positions at this one's): the page's run.
        if engine_result is None or (date_from is not None and engine_result.position_states_start_date != date_from):
            engine_result = await self._engine_run(user_id=user_id, broker_ids=broker_ids, date_from=date_from, date_to=date_to, target_currency=base_currency, apply_ownership_share=apply_ownership_share)

        # Quantity-affecting transactions: BUY/SELL plus in-kind ADJUSTMENT and TRANSFER,
        # mirroring _LOT_AFFECTING_TYPES / the engine's position model. Restricting this to
        # {BUY, SELL} made ADJUSTMENT/TRANSFER-seeded positions (e.g. in-kind succession
        # transfers) collapse to qty 0 at period end -> reported as fully-sold with no value
        # or annualized return, diverging from the holdings view where they are held.
        _QTY_TYPES = engine_facts._LOT_AFFECTING_TYPES

        # Per-position accumulators
        per_realized: dict[tuple[int, int], Decimal] = defaultdict(Decimal)
        per_cost_sold: dict[tuple[int, int], Decimal] = defaultdict(Decimal)
        per_sales: dict[tuple[int, int], int] = defaultdict(int)

        # ── Income / Fees with asset_id attribution: the period's cash flows of the native
        # cash (financial_math.native_cash), the same the summary's period income and fees
        # read. Signed income keeps legacy negative DIVIDEND/INTEREST corrections (plan §4.4);
        # fees and taxes are absolute. The unallocated sums keep the access order.
        native_cash = engine_facts._engine_native_cash(engine_result, base_currency)
        flows = native_cash.flows(date_from, effective_end)
        per_income = flows.income_by_position
        per_fees_taxes = flows.costs_by_position
        access_order = {access.broker_id: index for index, access in enumerate(accesses)}
        unalloc_income = dict(sorted(flows.unallocated_income.items(), key=lambda item: access_order.get(item[0], len(access_order))))
        unalloc_fees = dict(sorted(flows.unallocated_costs.items(), key=lambda item: access_order.get(item[0], len(access_order))))

        # Track all positions with lot-affecting activity (BUY/SELL/ADJUSTMENT/TRANSFER)
        position_info: dict[tuple[int, int], dict] = {}
        # Holding-transaction streams per (broker, asset) for FIFO oldest-open-lot derivation.
        lot_txns_by_key: dict[tuple[int, int], list[Transaction]] = defaultdict(list)

        for access in accesses:
            broker_id = access.broker_id
            broker = await self._get_broker(broker_id)
            broker_name = broker.name if broker else f"Broker {broker_id}"

            broker_txns = await self._get_transactions(broker_id, date_to=effective_end)

            # ── Positions: every (broker, asset) whose quantity a transaction ever moved ──
            # The owner's share is the engine's: its boundary states are already scaled.
            held_asset_ids: dict[int, None] = {}  # in the order of each asset's first transaction
            for tx in broker_txns:
                if tx.asset_id is not None and tx.type in _QTY_TYPES:
                    lot_txns_by_key[(broker_id, tx.asset_id)].append(tx)
                    held_asset_ids.setdefault(tx.asset_id, None)

            for asset_id in held_asset_ids:
                asset = await self._get_asset(asset_id)
                if not asset:
                    continue
                position_info[(broker_id, asset_id)] = {"asset": asset, "broker_name": broker_name}

        # ── Realized gain/loss from SELLs and outgoing ADJUSTMENTs (proceeds 0, N78-1) in period: proceeds minus the
        # historical cost the engine's average-cost pool gave up (base currency, owner share applied) ──
        for sale in period_math.period_realized_sales(engine_result.realized_sales, date_from, date_to):
            gain = realized_gain(sale.proceeds, sale.cost)
            if gain is None:
                continue
            pos_key = (sale.broker_id, sale.asset_id)
            per_realized[pos_key] += gain
            per_cost_sold[pos_key] += sale.cost
            per_sales[pos_key] += 1

        # ── Unrealized change per position, from the engine's values at the period's boundaries ──
        # The positions held at the end of the period's start day and at its end, valued as the portfolio values them
        # (trade marks, split adjustment, estimate at cost, the boundary day's rate): the rows' unrealized changes add up
        # to the period's ugl_delta. An internal transfer inside the period splits the result between the two brokers.
        contributions: list[AssetPeriodContribution] = []
        start_states = {(ps.broker_id, ps.asset_id): ps for ps in engine_result.position_states_start} if date_from is not None else {}
        end_states = {(ps.broker_id, ps.asset_id): ps for ps in engine_result.position_states_end}
        tract_adjustments = transfer_tract_adjustments(engine_result.internal_asset_transfers, date_from, effective_end)
        moved_out = transfer_costs_moved_out(engine_result.internal_asset_transfers, date_from, effective_end)
        moved_in = transfer_tracts_moved_in(engine_result.internal_asset_transfers, date_from, effective_end)

        lot_split_ids = await split_linked_ids(self.db, [tx for txns in lot_txns_by_key.values() for tx in txns])
        # MF-A10: the moves at the run's share (the owner's, or the whole broker: MF6-3), as the engine's quantities the rows
        # test against the dust threshold
        lot_shares = engine_result.broker_shares
        lot_moves = {key: quantity_moves(txns, lot_split_ids, share=lot_shares[key[0]]) for key, txns in lot_txns_by_key.items()}
        oldest_open_lot_dates: dict[tuple[int, int], Optional[date_type]] = {key: oldest_open_lot_date(moves) for key, moves in lot_moves.items()}
        closings = await self._closing_transactions(user_id, lot_txns_by_key, lot_moves)

        for pos_key, info in position_info.items():
            broker_id, asset_id = pos_key
            asset = info["asset"]
            start_state = start_states.get(pos_key)
            end_state = end_states.get(pos_key)
            qty_at_start = start_state.quantity if start_state is not None else Decimal("0")
            qty_at_end = end_state.quantity if end_state is not None else Decimal("0")
            is_fully_sold = qty_at_end <= engine_facts._QUANTITY_DUST_THRESHOLD

            # A dust residual counts as not held: no value, no unrealized of its own.
            ug_start: Decimal | None = None
            ug_end: Decimal | None = None
            cb_end: Decimal | None = None
            start_value: Decimal | None = Decimal("0") if date_from is None or qty_at_start <= engine_facts._QUANTITY_DUST_THRESHOLD else None
            end_value: Decimal | None = Decimal("0") if qty_at_end <= engine_facts._QUANTITY_DUST_THRESHOLD else None
            if start_state is not None and qty_at_start > engine_facts._QUANTITY_DUST_THRESHOLD:
                start_value = start_state.market_value
                ug_start = start_state.unrealized_pnl
            if end_state is not None and qty_at_end > engine_facts._QUANTITY_DUST_THRESHOLD:
                end_value = end_state.market_value
                ug_end = end_state.unrealized_pnl
                cb_end = end_state.cost_basis if end_state.cost_complete else None

            # The period P&L of the row (financial_math.portfolio.contributions, the one home of the formula)
            realized = per_realized.get(pos_key)
            income = per_income.get(pos_key)
            fees = per_fees_taxes.get(pos_key)
            row_pnl = position_period_pnl(
                held_at_start=qty_at_start > engine_facts._QUANTITY_DUST_THRESHOLD and start_state is not None,
                held_at_end=qty_at_end > engine_facts._QUANTITY_DUST_THRESHOLD,
                unrealized_start=ug_start,
                unrealized_end=ug_end,
                transfer_adjustment=tract_adjustments.get(pos_key),
                realized=realized,
                income=income,
                fees=fees,
            )
            unrealized_delta, period_pnl = row_pnl.unrealized_delta, row_pnl.period_pnl
            has_period_activity = any(value is not None and value != 0 for value in (realized, income, fees))
            has_boundary_position = qty_at_start > engine_facts._QUANTITY_DUST_THRESHOLD or qty_at_end > engine_facts._QUANTITY_DUST_THRESHOLD

            if not has_period_activity and not has_boundary_position and period_pnl is None:
                continue

            # R4 (financial_math.portfolio.contributions): the return on the start value; the annualized return over
            # the position's window, on the end cost for a position opened inside the period; for a position closed in
            # it, the annualized return on the cost it sold over its flight time.
            period_pnl_pct = period_return_on_start(period_pnl, start_value)
            # MF-A9: a position opened in the period that received units by a counted tract, and from which no unit left in
            # the period, counts them, in its fallback base, from their value on arrival, as its result does
            row_moves = lot_moves.get(pos_key, [])
            row_exits = exits_in(row_moves, date_from, effective_end)
            # MF-A5: the cost of every unit that left, sold or moved by a counted tract; a unit that left another way
            # leaves no base. MF-A8: units received by a counted tract enter it at their value on arrival, as they enter
            # the row's result
            exits_base = closed_position_base(
                per_cost_sold.get(pos_key, Decimal("0")),
                per_sales.get(pos_key, 0),
                moved_out.get(pos_key),
                row_exits,
                moved_in.get(pos_key),
            )
            period_annualized = annualized_period_return(
                period_pnl,
                start_value,
                cb_end,
                window_from=window_start(date_from, oldest_open_lot_dates.get(pos_key)),
                end=effective_end,
                moved_in=moved_in.get(pos_key) if row_exits == 0 else None,
            )
            if is_fully_sold:
                opened, closed = closed_position_window(row_moves)
                closed_annualized = closed_position_annualized(period_pnl, exits_base, opened, closed, date_from)
                if closed_annualized is not None:
                    period_annualized = closed_annualized
                elif closed_flight_too_short(opened, closed, date_from):
                    # MF-A3: held too few days in the period to annualize, «—», never the general rule over the period
                    period_annualized = None

            contributions.append(
                AssetPeriodContribution(
                    asset_id=asset_id,
                    asset_name=asset.display_name,
                    asset_ticker=asset.identifier_ticker,
                    asset_type=asset.asset_type.value if asset.asset_type else "Unknown",
                    broker_id=broker_id,
                    broker_name=info["broker_name"],
                    period_unrealized_delta=unrealized_delta,
                    period_realized_gain_loss=realized if realized else None,
                    period_income=income if income else None,
                    period_fees_taxes=fees if fees else None,
                    period_pnl=period_pnl,
                    period_pnl_percent=period_pnl_pct,
                    # Each component on the same base as the row's return (P4, the Performance tooltip).
                    period_unrealized_delta_percent=period_return_on_start(unrealized_delta, start_value),
                    period_realized_gain_loss_percent=period_return_on_start(realized if realized else None, start_value),
                    period_income_percent=period_return_on_start(income if income else None, start_value),
                    period_fees_taxes_percent=period_return_on_start(fees if fees else None, start_value),
                    annualized_return=period_annualized,
                    start_value=start_value,
                    end_value=end_value,
                    is_fully_sold=is_fully_sold,
                    closed_by=closings[pos_key][0] if is_fully_sold and pos_key in closings else None,
                    closed_to_broker_id=closings[pos_key][1] if is_fully_sold and pos_key in closings else None,
                    oldest_open_lot_date=oldest_open_lot_dates.get(pos_key),
                )
            )

        # Include positions with income/fees only (no BUY/SELL)
        for bid, aid in sorted(set(per_income.keys()) | set(per_fees_taxes.keys())):
            if (bid, aid) not in position_info:
                asset = await self._get_asset(aid)
                broker = await self._get_broker(bid)
                income = per_income.get((bid, aid), Decimal("0"))
                fees = per_fees_taxes.get((bid, aid), Decimal("0"))
                # Nonzero, not positive-only: a legacy negative income correction must
                # still surface here, never silently dropped (plan §4.4).
                if income == 0 and fees == 0:
                    continue
                pnl = income - fees
                contributions.append(
                    AssetPeriodContribution(
                        asset_id=aid,
                        asset_name=asset.display_name if asset else f"Asset {aid}",
                        asset_ticker=asset.identifier_ticker if asset else None,
                        asset_type=asset.asset_type.value if asset and asset.asset_type else "Unknown",
                        broker_id=bid,
                        broker_name=broker.name if broker else f"Broker {bid}",
                        period_income=income if income else None,
                        period_fees_taxes=fees if fees > 0 else None,
                        period_pnl=pnl,
                        start_value=Decimal("0"),
                        end_value=Decimal("0"),
                        is_fully_sold=True,
                        oldest_open_lot_date=oldest_open_lot_dates.get((bid, aid)),
                    )
                )

        # Build unallocated
        unallocated: list[UnallocatedContribution] = []
        other_effects: list[OtherPeriodEffect] = []
        for bid in set(unalloc_income.keys()) | set(unalloc_fees.keys()):
            inc = unalloc_income.get(bid)
            fee = unalloc_fees.get(bid)
            # inc: nonzero check (legacy negative corrections must stay visible, plan §4.4).
            # fee: unchanged positive-only check — fee/tax signed corrections are out of
            # this plan's scope.
            if inc or (fee and fee > 0):
                broker = await self._get_broker(bid)
                broker_name = broker.name if broker else f"Broker {bid}"
                unallocated.append(
                    UnallocatedContribution(
                        broker_id=bid,
                        broker_name=broker_name,
                        unallocated_income=inc if inc else None,
                        unallocated_fees_taxes=fee if fee and fee > 0 else None,
                    )
                )
                if inc:
                    other_effects.append(
                        OtherPeriodEffect(
                            description="Unallocated income",
                            category="Income",
                            period_pnl=inc,
                            broker_id=bid,
                            broker_name=broker_name,
                        )
                    )
                if fee and fee > 0:
                    other_effects.append(
                        OtherPeriodEffect(
                            description="Unallocated costs",
                            category="Cost",
                            period_pnl=Decimal("0") - fee,
                            broker_id=bid,
                            broker_name=broker_name,
                        )
                    )

        period_figures = period_math.period_pnl(getattr(engine_result, "daily_states", None) or [], date_from, effective_end)
        period_pnl_total = period_figures.pnl if period_figures is not None else None
        period_ugl_delta = period_figures.ugl_delta if period_figures is not None else None
        period_other_result: Decimal | None = None
        if period_pnl_total is not None and period_ugl_delta is not None:
            total_realized = sum(per_realized.values(), Decimal("0"))
            total_income = sum(per_income.values(), Decimal("0")) + sum(unalloc_income.values(), Decimal("0"))
            total_fees = sum(per_fees_taxes.values(), Decimal("0")) + sum(unalloc_fees.values(), Decimal("0"))
            period_other_result = period_math.period_other_result(period_pnl_total, period_ugl_delta, total_realized, total_income, total_fees)

        if period_other_result is not None:
            # FX on cash (financial_math.native_cash): each broker's exchange result on foreign
            # cash, a row of its own in access order; the residual drops by the same amount.
            # Below CONVERSION_DUST a figure is the rounding of two conversions of the same
            # cash, not a result: with foreign cash in scope neither row shows it. A
            # report-currency-only scope keeps the exact residual rule.
            residual = period_other_result
            exchange_results = native_cash.exchange_results(date_from, effective_end)
            for bid in sorted(exchange_results, key=lambda broker_id: access_order.get(broker_id, len(access_order))):
                exchange_result = exchange_results[bid]
                if abs(exchange_result) < CONVERSION_DUST:
                    continue
                broker = await self._get_broker(bid)
                other_effects.append(
                    OtherPeriodEffect(
                        description="FX on cash",
                        code=OtherPeriodEffectCode.FX_ON_CASH,
                        category="Other",
                        period_pnl=exchange_result,
                        broker_id=bid,
                        broker_name=broker.name if broker else f"Broker {bid}",
                    )
                )
                residual -= exchange_result
            # B5 (financial_math.portfolio.period): the gain securities accrued at a broker outside the view before they
            # crossed its boundary, a row per broker in the same order; the residual drops by the same amount.
            transfer_results = period_math.market_value_transfer_results(getattr(engine_result, "market_value_transfers", None) or [], date_from, effective_end)
            for bid in sorted(transfer_results, key=lambda broker_id: access_order.get(broker_id, len(access_order))):
                transfer_result = transfer_results[bid]
                if abs(transfer_result) < CONVERSION_DUST:
                    continue
                broker = await self._get_broker(bid)
                other_effects.append(
                    OtherPeriodEffect(
                        description="Transfers at market value",
                        category="Other",
                        period_pnl=transfer_result,
                        broker_id=bid,
                        broker_name=broker.name if broker else f"Broker {bid}",
                    )
                )
                residual -= transfer_result
            show_residual = abs(residual) >= CONVERSION_DUST if native_cash.foreign_cash_broker_ids else residual != 0
            if show_residual:
                other_effects.append(
                    OtherPeriodEffect(
                        description="Other / reconciliation residual",
                        category="Other",
                        period_pnl=residual,
                        broker_id=None,
                        broker_name=None,
                    )
                )

        gross_gains = sum(c.period_pnl for c in contributions if c.period_pnl and c.period_pnl > 0) or Decimal("0")
        gross_losses = sum(abs(c.period_pnl) for c in contributions if c.period_pnl and c.period_pnl < 0) or Decimal("0")

        return PositionsContribution(
            positions=contributions,
            unallocated=unallocated,
            other_effects=other_effects,
            gross_gains=gross_gains,
            gross_losses=gross_losses,
        )

    async def get_positions_series(self, user_id: int, query: PositionsSeriesQuery) -> PositionsSeriesResponse:
        """The daily series of the chosen positions: the Dashboard's positions chart (#48).

        The page's engine run (``_engine_run``, FB-14): the same blob-cache key as the report and the Performance table of
        that period, so the chart reads the run the report built, and a change of the selection reuses it. The series are built by ``financial_math.portfolio.position_series``
        from that run's frames, realized sales, internal transfers and average costs, and the native cash's income and costs by
        day; only the asked positions are read. A position of a broker the user cannot read has no frame in the run, so it
        comes back empty. Period figures are those of ``get_positions_contribution`` at each day.
        """
        today = date_type.today()
        base_currency = query.target_currency or await self._get_base_currency(user_id)
        date_from = query.date_range.resolved_start() if query.date_range else None
        date_to = query.date_range.resolved_end() if query.date_range else None
        if date_to is not None:
            date_to = min(date_to, latest_range_end())
        effective_end = date_to or today
        if date_from is not None:
            date_from = min(date_from, effective_end)

        requests = [(key.broker_id, key.asset_id) for key in query.positions]
        accesses = await self._get_user_broker_access(user_id, query.broker_ids)
        series_data = []
        engine_result = None
        if accesses:
            engine_result = await self._engine_run(user_id=user_id, broker_ids=query.broker_ids, date_from=date_from, date_to=date_to, target_currency=base_currency, apply_ownership_share=query.apply_ownership_share)
        if engine_result is not None and engine_result.position_frames is not None:
            frames: dict[tuple[int, int], list] = defaultdict(list)
            for frame in engine_result.position_frames:
                frames[(frame.broker_id, frame.asset_id)].append(frame)
            native_cash = engine_facts._engine_native_cash(engine_result, base_currency)
            transfers = list(engine_result.internal_asset_transfers)
            series_data = build_position_series(
                requests,
                date_from=date_from,
                date_to=effective_end,
                frames=frames,
                realized_sales=period_math.period_realized_sales(engine_result.realized_sales, date_from, effective_end),
                flow_steps=native_cash.position_flow_steps(date_from, effective_end),
                transfers=transfers,
                acquisitions=acquisitions_from_average_costs(engine_result.average_costs, transfers),
            )

        asset_names = await self._get_assets_map({asset_id for _, asset_id in requests})
        out: list[PositionSeries] = []
        for index, (broker_id, asset_id) in enumerate(requests):
            data = series_data[index] if index < len(series_data) else None
            asset = asset_names.get(asset_id)
            broker = await self._get_broker(broker_id) if broker_id is not None else None
            out.append(
                PositionSeries(
                    key=query.positions[index],
                    asset_name=asset.display_name if asset else f"Asset {asset_id}",
                    asset_ticker=asset.identifier_ticker if asset else None,
                    broker_name=broker.name if broker else None,
                    first_date=data.first_date if data else None,
                    last_date=data.last_date if data else None,
                    held_at_start=data.held_at_start if data else False,
                    held_at_end=data.held_at_end if data else False,
                    closed_on=data.closed_on if data else None,
                    complete=data.complete if data else True,
                    points=[
                        PositionSeriesPoint(
                            date=point.date,
                            through=point.through,
                            quantity=point.quantity,
                            market_value=point.market_value,
                            cost_basis=point.cost_basis,
                            pnl=point.pnl,
                            base=point.base,
                            pnl_percent=point.pnl_percent,
                            valuation_source=getattr(point.valuation_source, "value", point.valuation_source),
                            complete=point.complete,
                        )
                        for point in (data.points if data else [])
                    ],
                )
            )
        missing_pairs = engine_facts._engine_missing_fx_pairs(engine_result, date_from, effective_end) if engine_result is not None else []
        window_start = date_from if date_from is not None else (min((p.date for s in out for p in s.points), default=effective_end))
        return PositionsSeriesResponse(
            currency=base_currency,
            date_from=window_start,
            date_to=effective_end,
            range=DateSpan(start=window_start, end=effective_end),
            series=out,
            missing_fx_pairs=[info.pair for info in missing_pairs],
        )
