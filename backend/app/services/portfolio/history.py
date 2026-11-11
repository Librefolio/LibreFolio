"""The history series of ``PortfolioService``: value, P&L candles, income, cost, deposits and acquisition funding."""

from __future__ import annotations

import asyncio
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    TransactionType,
)
from backend.app.schemas.common import Currency, DateSpan
from backend.app.schemas.portfolio.history import (
    AcquisitionFundingPoint,
    AcquisitionFundingSeries,
    BrokerPnlHistory,
    BrokerPnlHistoryPoint,
    CostHistoryPoint,
    CostHistorySeries,
    DepositHistoryPoint,
    DepositHistorySeries,
    IncomeHistoryPoint,
    IncomeHistorySeries,
    MwrrLinePoint,
    PnlCandlePoint,
    PnlCandleSeries,
    PortfolioHistoryPoint,
)
from backend.app.services.financial_math.native_cash import NativeCash, broker_shares, cash_movement_from_transaction, compute_native_cash
from backend.app.services.financial_math.portfolio.models import DailyStates
from backend.app.services.financial_math.returns import (
    annualized_to_cumulative,
    calculate_simple_roi_series,
    period_mwrr_series,
    period_twrr_series,
    rebase_to_period,
)
from backend.app.services.portfolio import engine_facts


class PortfolioHistoryMixin:
    """The history series of ``PortfolioService``: value, P&L candles, income, cost, deposits and acquisition funding.

    Mixed into ``PortfolioService`` (``portfolio_service.py``), which provides ``db``.
    """

    db: AsyncSession

    async def get_history(
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        target_currency_override: str | None = None,
        _precomputed_engine_result=None,
    ) -> list[PortfolioHistoryPoint]:
        """Return the portfolio value series in steps via PortfolioCalculationEngine: see :meth:`get_history_steps`.

        _precomputed_engine_result: if provided by get_report(), skip engine re-run.
        """
        steps = await self.get_history_steps(user_id, broker_ids, date_from, date_to, target_currency_override, _precomputed_engine_result)
        return steps.history

    async def get_history_steps(
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        target_currency_override: str | None = None,
        _precomputed_engine_result=None,
    ) -> engine_facts.HistorySteps:
        """The history of ``[date_from, date_to]`` in steps, its ``range`` and its MWRR line (D-P4, contract §1.2, §2).

        Each point holds from its ``date`` to its ``through``: the values of every day in it, TWRR and ROI included, are
        the daily series' values of that day. The MWRR moves even on a quiet day, so it is not in the steps: the line has
        its true values at each step's ``date`` and ``through``, and at the month ends inside a long step.

        _precomputed_engine_result: if provided by get_report(), skip engine re-run.
        """
        from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder, mwrr_line_days  # noqa: PLC0415
        from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine  # noqa: PLC0415

        base_currency = target_currency_override or await self._get_base_currency(user_id)
        if _precomputed_engine_result is not None:
            result = _precomputed_engine_result
        else:
            engine = PortfolioCalculationEngine(self.db)
            result = await engine.calculate(
                user_id=user_id,
                broker_ids=broker_ids,
                date_from=None,  # Always compute from t=0 for correct cumulative values
                date_to=date_to,
                target_currency=base_currency,
            )

        views = DerivedViewsBuilder(result.daily_states, base_currency)
        window = views.window_range(date_from, date_to) if result.daily_states else None
        if window is None:
            return engine_facts.HistorySteps(range=None, history=[], mwrr_line=[])
        start, end = window

        # The first point pins the TWRR to 0, so the day after it may differ from it even when nothing happens
        pins = (start + timedelta(days=1),) if start < end else ()

        # ── TWRR and ROI on the days a step may start (a quiet day keeps both) ──
        performance_days = [*views.change_days(start, end, pins), end]
        nav_snapshots, cash_flows = views.build_performance_inputs(date_from, days=performance_days)
        period = rebase_to_period(nav_snapshots, cash_flows, date_from)
        period_cash_flows = list(period.cash_flows)
        period_nav_snapshots = list(period.nav_snapshots)
        twrr_map: dict[date_type, Decimal | None] = {}
        roi_map: dict[date_type, Decimal] = {}
        if period_nav_snapshots and period_cash_flows:
            # The card's rules at every point (MF-K3): no TWRR at a value at or below zero; the ROI's capital from the
            # first day with capital when the range starts before the portfolio
            twrr_map = {pt.date: pt.twrr for pt in period_twrr_series(period_nav_snapshots, period_cash_flows)}
            roi_map = {pt.date: pt.roi for pt in calculate_simple_roi_series(period_nav_snapshots, list(views.build_roi_cash_flows(date_from, nav_snapshots, cash_flows, days=performance_days)))}

        # First point pinned to 0% for the TWRR (and the MWRR line): period-relative returns measured from inception are
        # 0 at the period start by definition. ROI is NOT pinned — it is an absolute ratio (NAV − net_invested)/net_invested,
        # so on the very first day it must already reflect any seeded cost-vs-market gap (e.g. an in-kind succession
        # seeded above/below market shows its day-1 gain/loss instead of a flat 0).
        def metrics(day: date_type) -> dict[str, Decimal | None]:
            return {"twrr": Decimal("0") if day == start else twrr_map.get(day), "roi": roi_map.get(day)}

        history_dicts = views.build_history(start, end, metrics=metrics, extra_days=pins)
        history = [PortfolioHistoryPoint(**point) for point in history_dicts]
        mwrr_line = await self._mwrr_line(views, date_from, mwrr_line_days(history_dicts), start)
        return engine_facts.HistorySteps(range=DateSpan(start=start, end=end), history=history, mwrr_line=mwrr_line)

    @staticmethod
    async def _mwrr_line(views: Any, date_from: date_type | None, days: list[date_type], start: date_type) -> list[MwrrLinePoint]:
        """The MWRR line's true points on ``days`` (D-P4, contract §2): each the period MWRR ending that day — the value
        the daily line gives there, bit for bit (:func:`returns.period_mwrr_series`, every point its own solve) — and its
        cumulative form from the period's start; the first day pinned to 0."""
        nav_snapshots, cash_flows = views.build_performance_inputs(date_from, days=days)
        period = rebase_to_period(nav_snapshots, cash_flows, date_from)
        period_nav_snapshots, period_cash_flows = list(period.nav_snapshots), list(period.cash_flows)
        mwrr_map: dict[date_type, Decimal | None] = {}
        if period_nav_snapshots and period_cash_flows:
            # The same rule as the card, at every point (D-MF5): no rate where the card would have none.
            mwrr_series = await asyncio.to_thread(period_mwrr_series, period_nav_snapshots, period_cash_flows)
            mwrr_map = {pt.date: pt.mwrr for pt in mwrr_series}
        period_start = period_nav_snapshots[0].date if period_nav_snapshots else None
        line: list[MwrrLinePoint] = []
        for day in days:
            if day == start:
                line.append(MwrrLinePoint(date=day, annualized=Decimal("0"), cumulative=Decimal("0")))
                continue
            annualized = mwrr_map.get(day)
            line.append(MwrrLinePoint(date=day, annualized=annualized, cumulative=annualized_to_cumulative(annualized, (day - period_start).days if period_start else 0)))
        return line

    async def get_broker_pnl_history(
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        target_currency_override: str | None = None,
        _precomputed_engine_result=None,
    ) -> list[BrokerPnlHistory]:
        """Per-broker additive P&L history for the GrowthChart P&L broker overlay (G1a).

        Each broker's points sum to the scope-aggregate PortfolioHistoryPoint.total_pnl
        for every date, by construction (see DailyStateBuilder §4.2 / BrokerDailyContribution).

        _precomputed_engine_result: if provided by get_report(), skip engine re-run.
        """
        from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder  # noqa: PLC0415
        from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine  # noqa: PLC0415

        base_currency = target_currency_override or await self._get_base_currency(user_id)
        if _precomputed_engine_result is not None:
            result = _precomputed_engine_result
        else:
            engine = PortfolioCalculationEngine(self.db)
            result = await engine.calculate(
                user_id=user_id,
                broker_ids=broker_ids,
                date_from=None,  # Always compute from t=0 for correct cumulative values
                date_to=date_to,
                target_currency=base_currency,
            )

        if not result.daily_states:
            return []

        views = DerivedViewsBuilder(result.daily_states, base_currency)
        by_broker = views.build_broker_pnl_history(date_from, date_to)
        if not by_broker:
            # A window holding no state: the whole-history build still listed every broker, with no point. Otherwise
            # the window lists them all, in the same order: every state carries every broker of the scope (DailyStateBuilder)
            states = (segment.state for segment in result.daily_states.segments) if isinstance(result.daily_states, DailyStates) else result.daily_states
            by_broker = {broker_id: [] for state in states for broker_id in state.broker_contributions}

        broker_pnl_history: list[BrokerPnlHistory] = []
        for broker_id, points in by_broker.items():
            broker = await self._get_broker(broker_id)
            broker_name = broker.name if broker else f"Broker {broker_id}"
            broker_pnl_history.append(BrokerPnlHistory(broker_id=broker_id, broker_name=broker_name, points=[BrokerPnlHistoryPoint(**point) for point in points]))

        return broker_pnl_history

    async def get_pnl_candles(
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        target_currency_override: str | None = None,
        _precomputed_engine_result=None,
    ) -> PnlCandleSeries:
        """Synthetic total-P&L candle series for the GrowthChart P&L candles submode (G1b).

        Requires the engine run itself to have been computed with include_candles=True —
        when called standalone (no _precomputed_engine_result) this runs its own engine pass
        with that flag; when called from get_report() the shared engine result must already
        have been computed with query.include_pnl_candles, or every day comes back with no
        candle (silently empty, not wrong — the L1/L2 cache keys both include the flag so a
        cache hit can never silently return the wrong shape here).
        """
        from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder  # noqa: PLC0415
        from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine  # noqa: PLC0415

        base_currency = target_currency_override or await self._get_base_currency(user_id)
        if _precomputed_engine_result is not None:
            result = _precomputed_engine_result
        else:
            engine = PortfolioCalculationEngine(self.db)
            result = await engine.calculate(
                user_id=user_id,
                broker_ids=broker_ids,
                date_from=None,  # Always compute from t=0 for correct cumulative values
                date_to=date_to,
                target_currency=base_currency,
                include_candles=True,
            )

        if not result.daily_states:
            return PnlCandleSeries(points=[])

        views = DerivedViewsBuilder(result.daily_states, base_currency)
        return PnlCandleSeries(points=[PnlCandlePoint(**point) for point in views.build_pnl_candles(date_from, date_to)])

    async def _signed_transaction_sums_by_date(
        self,
        accesses: list,
        tx_types: set[TransactionType],
        base_currency: str,
        date_from: date_type | None,
        date_to: date_type | None,
        native_cash: NativeCash | None = None,
    ) -> tuple[dict[date_type, dict[str, Decimal]], list[str]]:
        """Signed sums of ``tx_types`` by date in (date_from, date_to], and the pairs left out.

        Read from the native cash (financial_math.native_cash), the same reconstruction the
        engine and get_summary() use: each movement at its broker's share (F2), converted at
        its own date; a movement with no rate is left out of the sums and its pair reported.
        Without date_to the window stops at today, the engine's horizon. ``native_cash`` is
        the engine's own when the caller already ran it (get_report); otherwise one is built
        here from the requested types. Shared by get_income_history/get_cost_history/
        get_deposit_history (G1c, batch 2), which differ only in the types they read and how
        they combine the per-type sums.
        """
        horizon = date_to or date_type.today()
        if native_cash is None:
            movements = []
            shares = broker_shares(accesses)
            for access in accesses:
                for tx in await self._get_transactions(access.broker_id, tx_types=tx_types, date_to=horizon):
                    movement = cash_movement_from_transaction(tx, share=shares[access.broker_id])
                    if movement is not None:
                        movements.append(movement)
            movements.sort(key=lambda movement: (movement.date, movement.movement_id or 0))
            native_cash = await compute_native_cash(self.db, movements, report_currency=base_currency, rates_until=horizon)
        types = {tx_type.value for tx_type in tx_types}
        sums_by_date = native_cash.sums_by_date(date_from, horizon, types)
        missing_fx_pairs = [missing.pair for missing in native_cash.missing_conversions(date_from, horizon, types)]
        return sums_by_date, missing_fx_pairs

    async def get_income_history(
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        target_currency_override: str | None = None,
        _precomputed_native_cash: NativeCash | None = None,
    ) -> IncomeHistorySeries:
        """Signed daily DIVIDEND/INTEREST income history for the GrowthChart P&L income
        submode (G1c, plan §3.4/§4.4).

        Read from the native cash (financial_math.native_cash), the reconstruction
        get_summary() also reads its period income from: same (date_from, date_to]
        boundary, same F2 role-aware share applied once, same conversion at each row's
        own date, so sum(dividend)+sum(interest) reproduces PortfolioSummary.period_income
        exactly for the same scope/window, by construction. get_report() passes the
        engine's own native cash; a standalone call builds one from the income rows.
        """
        base_currency = target_currency_override or await self._get_base_currency(user_id)
        accesses = await self._get_user_broker_access(user_id, broker_ids)
        if not accesses:
            return IncomeHistorySeries(points=[])

        sums_by_date, missing_fx_pairs = await self._signed_transaction_sums_by_date(accesses, {TransactionType.DIVIDEND, TransactionType.INTEREST}, base_currency, date_from, date_to, _precomputed_native_cash)

        # Sparse series: only dates with actual DIVIDEND/INTEREST activity, never a
        # dense day-by-day zero-filled series (plan §3.4 — "sparse economic flows").
        points = [
            IncomeHistoryPoint(
                date=d,
                dividend=Currency(code=base_currency, amount=type_sums.get(TransactionType.DIVIDEND, Decimal("0"))),
                interest=Currency(code=base_currency, amount=type_sums.get(TransactionType.INTEREST, Decimal("0"))),
            )
            for d, type_sums in sorted(sums_by_date.items())
        ]
        return IncomeHistorySeries(points=points, missing_fx_pairs=sorted(missing_fx_pairs))

    async def get_cost_history(
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        target_currency_override: str | None = None,
        _precomputed_native_cash: NativeCash | None = None,
    ) -> CostHistorySeries:
        """Signed daily FEE+TAX cost history for the GrowthChart P&L income submode's
        costs dimension (batch 2). Same native-cash read as get_income_history (see
        _signed_transaction_sums_by_date). FEE and TAX are
        summed together into one "cost" figure — matching the dashboard's existing
        "Fees & taxes" KPI grouping — preserving the raw (negative) Transaction.amount
        sign rather than flipping to a positive magnitude, same signed-fidelity policy
        as income.
        """
        base_currency = target_currency_override or await self._get_base_currency(user_id)
        accesses = await self._get_user_broker_access(user_id, broker_ids)
        if not accesses:
            return CostHistorySeries(points=[])

        sums_by_date, missing_fx_pairs = await self._signed_transaction_sums_by_date(accesses, {TransactionType.FEE, TransactionType.TAX}, base_currency, date_from, date_to, _precomputed_native_cash)

        points = [CostHistoryPoint(date=d, cost=Currency(code=base_currency, amount=sum(type_sums.values(), Decimal("0")))) for d, type_sums in sorted(sums_by_date.items())]
        return CostHistorySeries(points=points, missing_fx_pairs=sorted(missing_fx_pairs))

    async def get_deposit_history(
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        target_currency_override: str | None = None,
        _precomputed_native_cash: NativeCash | None = None,
    ) -> DepositHistorySeries:
        """Daily DEPOSIT history for the GrowthChart P&L income submode's deposit-size
        dimension (batch 2). Same native-cash read as get_income_history
        (see _signed_transaction_sums_by_date).
        """
        base_currency = target_currency_override or await self._get_base_currency(user_id)
        accesses = await self._get_user_broker_access(user_id, broker_ids)
        if not accesses:
            return DepositHistorySeries(points=[])

        sums_by_date, missing_fx_pairs = await self._signed_transaction_sums_by_date(accesses, {TransactionType.DEPOSIT}, base_currency, date_from, date_to, _precomputed_native_cash)

        points = [DepositHistoryPoint(date=d, deposit=Currency(code=base_currency, amount=type_sums.get(TransactionType.DEPOSIT, Decimal("0")))) for d, type_sums in sorted(sums_by_date.items())]
        return DepositHistorySeries(points=points, missing_fx_pairs=sorted(missing_fx_pairs))

    async def get_acquisition_funding_history(
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        target_currency_override: str | None = None,
        _precomputed_engine_result=None,
    ) -> AcquisitionFundingSeries:
        """New-vs-reinvested BUY funding split for the GrowthChart P&L income submode's
        acquisition-size dimension (batch 2, plan §5.2).

        Unlike cost/deposit/income (pure transaction scans), this REQUIRES an engine
        run: the new-vs-reinvested split depends on the running capital/returns pool
        state built up over the ENTIRE prior transaction history, not just the day's
        own transactions in isolation — mirrors get_pnl_candles()'s
        include_candles=True requirement exactly (same
        _precomputed_engine_result/standalone dual-mode, same "flag must be set on
        the shared engine run or every day comes back empty" caveat).
        """
        from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder  # noqa: PLC0415

        base_currency = target_currency_override or await self._get_base_currency(user_id)
        if _precomputed_engine_result is not None:
            result = _precomputed_engine_result
        else:
            result = await self._engine_run(user_id=user_id, broker_ids=broker_ids, date_from=date_from, date_to=date_to, target_currency=base_currency)

        if not result.daily_states:
            return AcquisitionFundingSeries(points=[])

        views = DerivedViewsBuilder(result.daily_states, base_currency)
        raw_points = views.build_acquisition_funding(date_from, date_to)
        # Canonical (date_from, date_to] boundary — exclusive start, inclusive end.
        # NOTE the deliberate difference from get_pnl_candles/get_broker_pnl_history,
        # whose engine-backed slicing this method otherwise mirrors: those two are
        # LEVEL series (a cumulative P&L value per day), so the period's opening day
        # must be shown as the baseline. This one is a FLOW series (that day's own BUY
        # split), so a BUY dated exactly on date_from belongs to the PREVIOUS period —
        # the same rule already applied to its five co-rendered Income-submode
        # siblings (income/cost/deposit). Using >= here would make a BUY on date_from
        # draw a bar while a DIVIDEND on that very same date draws none.
        sliced_points = [AcquisitionFundingPoint(date=p["date"], from_new_capital=p["from_new_capital"], from_reinvested=p["from_reinvested"]) for p in raw_points if (date_from is None or p["date"] > date_from) and (date_to is None or p["date"] <= date_to)]
        return AcquisitionFundingSeries(points=sliced_points)
