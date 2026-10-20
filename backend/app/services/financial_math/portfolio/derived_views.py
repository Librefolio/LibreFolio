"""Views derived from the daily states: history, per-broker P&L, candles, acquisition funding, performance inputs, allocation; and the cost positions."""

from __future__ import annotations

import bisect
from collections import defaultdict
from collections.abc import Mapping
from datetime import date as date_type
from decimal import Decimal
from typing import Any

from backend.app.schemas.common import Currency as CurrencySchema
from backend.app.schemas.portfolio import (
    DataQualityReport,
)
from backend.app.services.financial_math.average_cost import (
    CostMovement,
    CostPosition,
    cost_movement_from_transaction,
)
from backend.app.services.financial_math.portfolio.data_quality import build_data_quality_report
from backend.app.services.financial_math.portfolio.models import ClassifiedTransaction, DailyPortfolioState
from backend.app.services.financial_math.returns import CashFlowInput, NAVSnapshot
from backend.app.services.financial_math.weights import slice_percents
from backend.app.utils.asset.sector import sector_emoji


def build_cost_positions(
    classified_txs: list[ClassifiedTransaction],
    asset_currencies: Mapping[int, str],
    target_currency: str,
    split_linked_tx_ids: set[int],
    date_to: date_type | None = None,
) -> list[CostPosition]:
    """The average-cost positions of the replay: one per (asset_id, broker_id).

    Movements are the classified transactions that move quantity, scaled by the owner's
    share, in the order DailyStateBuilder replays them (classification order, which is
    date then id); transactions after ``date_to`` are left out.
    """
    movements: dict[tuple[int, int], list[CostMovement]] = defaultdict(list)
    for ctxn in classified_txs:
        tx = ctxn.tx
        if tx.asset_id is None or (date_to is not None and tx.date > date_to):
            continue
        movement = cost_movement_from_transaction(
            tx,
            asset_currency=asset_currencies.get(tx.asset_id, target_currency),
            split_linked=tx.id in split_linked_tx_ids,
            share=ctxn.share,
        )
        if movement is not None:
            movements[(tx.asset_id, tx.broker_id)].append(movement)
    return [CostPosition(key=key, asset_currency=asset_currencies.get(key[0], target_currency), movements=tuple(items)) for key, items in movements.items()]


# =============================================================================
# DERIVED VIEWS BUILDER — Converts DailyPortfolioState[] into API DTOs
# =============================================================================


class DerivedViewsBuilder:
    """Derives summary, history, allocation, and performance views from daily states.

    Pure function — no I/O.
    """

    def __init__(
        self,
        daily_states: list[DailyPortfolioState],
        target_currency: str,
    ) -> None:
        self.daily_states = daily_states
        self.target_currency = target_currency
        # The states' dates, in the engine's order (ascending, one state a day): a window is found by bisection
        self._dates = [state.date for state in daily_states]

    def _window(self, date_from: date_type | None, date_to: date_type | None, *, exclusive_start: bool = False) -> list[DailyPortfolioState]:
        """The states of ``[date_from, date_to]`` (``(date_from, date_to]`` with ``exclusive_start``), an open bound
        reaching the end of the history: a view built for a window builds only its days (P2, N74)."""
        start = 0 if date_from is None else (bisect.bisect_right if exclusive_start else bisect.bisect_left)(self._dates, date_from)
        end = len(self._dates) if date_to is None else bisect.bisect_right(self._dates, date_to)
        return self.daily_states[start:end]

    def build_history(self, date_from: date_type | None = None, date_to: date_type | None = None) -> list[dict]:
        """Build PortfolioHistoryPoint-compatible dicts from the daily states of ``[date_from, date_to]``.

        Returns dicts (not PortfolioHistoryPoint) to avoid circular import.
        The API adapter converts these to PortfolioHistoryPoint.
        """
        return [
            {
                "date": s.date,
                "cash_value": CurrencySchema(code=self.target_currency, amount=s.cash_value),
                "market_value": CurrencySchema(code=self.target_currency, amount=s.market_value),
                "broker_nav_value": CurrencySchema(code=self.target_currency, amount=s.broker_nav_value),
                "in_transit_cash_value": CurrencySchema(code=self.target_currency, amount=s.in_transit_cash_value) if s.in_transit_cash_value else None,
                "in_transit_asset_market_value": CurrencySchema(code=self.target_currency, amount=s.in_transit_asset_market_value) if s.in_transit_asset_market_value else None,
                "in_transit_market_value": CurrencySchema(code=self.target_currency, amount=s.in_transit_market_value) if s.in_transit_market_value else None,
                "nav_value": CurrencySchema(code=self.target_currency, amount=s.nav_value),
                "open_cost_basis": CurrencySchema(code=self.target_currency, amount=s.open_cost_basis) if s.open_cost_basis else None,
                "in_transit_asset_cost_basis": CurrencySchema(code=self.target_currency, amount=s.in_transit_asset_cost_basis) if s.in_transit_asset_cost_basis else None,
                "in_transit_book_value": CurrencySchema(code=self.target_currency, amount=s.in_transit_book_value) if s.in_transit_book_value else None,
                "book_value": CurrencySchema(code=self.target_currency, amount=s.book_value) if s.book_value else None,
                "capital_baseline": CurrencySchema(code=self.target_currency, amount=s.cumulative_external_cash_flow),
                "book_asset_like": CurrencySchema(code=self.target_currency, amount=s.book_asset_like),
                "cash_from_contributed_capital": CurrencySchema(code=self.target_currency, amount=s.cash_from_contributed_capital),
                "cash_from_generated_returns": CurrencySchema(code=self.target_currency, amount=s.cash_from_generated_returns),
                "total_pnl": CurrencySchema(code=self.target_currency, amount=s.total_pnl),
                "unrealized_gain_loss": CurrencySchema(code=self.target_currency, amount=s.unrealized_gain_loss) if s.unrealized_gain_loss else None,
            }
            for s in self._window(date_from, date_to)
        ]

    def build_broker_pnl_history(self, date_from: date_type | None = None, date_to: date_type | None = None) -> dict[int, list[dict]]:
        """Per-broker additive P&L history: broker_id -> [{date, total_pnl}, ...].

        Derived from DailyPortfolioState.broker_contributions (see G1a/§4.2), which
        is built additively in the same daily replay as the scope-aggregate
        total_pnl, so for every date sum(points[bid].total_pnl) == aggregate total_pnl.
        Returns raw dicts (not BrokerPnlHistory) to avoid circular import, mirroring
        build_history()'s adapter-conversion pattern.
        """
        by_broker: dict[int, list[dict]] = defaultdict(list)
        for s in self._window(date_from, date_to):
            for bid, contribution in s.broker_contributions.items():
                by_broker[bid].append({"date": s.date, "total_pnl": CurrencySchema(code=self.target_currency, amount=contribution.pnl_contribution)})
        return dict(by_broker)

    def build_pnl_candles(self, date_from: date_type | None = None, date_to: date_type | None = None) -> list[dict]:
        """Synthetic total-P&L candle series (G1b): [{date, open, high, low, close}, ...].

        Days whose candle is unavailable (DailyPortfolioState.pnl_candle is None — a held
        asset's valuation was MISSING that day) are omitted entirely, a genuine gap rather
        than a guessed/zeroed candle. ``close`` reproduces the canonical
        PortfolioHistoryPoint.total_pnl for the same date exactly (see PnlCandleContribution
        / DailyStateBuilder §4.3). Returns raw dicts, mirroring build_history()'s
        adapter-conversion pattern (avoids a circular import on the API schema).
        """
        points: list[dict] = []
        for s in self._window(date_from, date_to):
            if s.pnl_candle is None:
                continue
            points.append(
                {
                    "date": s.date,
                    "open": CurrencySchema(code=self.target_currency, amount=s.pnl_candle.open),
                    "high": CurrencySchema(code=self.target_currency, amount=s.pnl_candle.high),
                    "low": CurrencySchema(code=self.target_currency, amount=s.pnl_candle.low),
                    "close": CurrencySchema(code=self.target_currency, amount=s.pnl_candle.close),
                }
            )
        return points

    def build_acquisition_funding(self, date_from: date_type | None = None, date_to: date_type | None = None) -> list[dict]:
        """New-vs-reinvested BUY funding split (batch 2): [{date, from_new_capital,
        from_reinvested}, ...].

        Days with no BUY activity (DailyPortfolioState.acquisition_funding is None) are
        omitted entirely — a genuine "nothing acquired that day" gap, not a zeroed row
        (mirrors build_pnl_candles's own omission convention). from_new_capital +
        from_reinvested reproduces that day's total BUY cash outflow exactly, by
        construction (see AcquisitionFundingContribution). Returns raw dicts, mirroring
        build_history()'s adapter-conversion pattern.
        """
        points: list[dict] = []
        # A flow series: a BUY dated date_from belongs to the previous period, (date_from, date_to]
        for s in self._window(date_from, date_to, exclusive_start=True):
            if s.acquisition_funding is None:
                continue
            points.append(
                {
                    "date": s.date,
                    "from_new_capital": CurrencySchema(code=self.target_currency, amount=s.acquisition_funding.from_new_capital),
                    "from_reinvested": CurrencySchema(code=self.target_currency, amount=s.acquisition_funding.from_reinvested),
                }
            )
        return points

    def build_performance_inputs(
        self,
        date_from: date_type | None = None,
    ) -> tuple[list, list]:
        """Extract NAV snapshots and the invested-capital flow series for ROI/TWRR/MWRR.

        Returns (nav_snapshots, cash_flows) compatible with the ``returns`` functions.

        With ``date_from`` (P2, N74), only what ``returns.rebase_to_period`` keeps of them for that period: the snapshots
        from the period's opening state on (the last one dated on or before ``date_from``, else the first) and the flows
        dated after it, so the rebase gives the same period without building the history before it.

        The capital flow is derived from the day-over-day change in
        ``cumulative_external_cash_flow`` (the *capital baseline*), NOT from the
        cash-only ``external_cash_flow`` field. The baseline already folds in
        priced in-kind ADJUSTMENT capital — opening equity / succession / transfer
        that injects book value with no cash counterpart — via the engine's
        capital-adjustment routing (see ``_is_capital_adjustment``). Using the
        cash-only field here would omit that in-kind capital from the invested
        denominator, inflating ROI to thousands of percent whenever a portfolio is
        seeded in kind, and would spuriously count a mid-series in-kind injection as
        TWRR return. Feeding the baseline delta keeps every return metric coherent.

        Sign convention: CashFlowInput uses investor perspective (deposit = negative).
        The baseline uses portfolio perspective (contribution = positive), so we
        negate the delta when passing to performance functions.
        """
        states = self.daily_states
        prev_baseline = Decimal("0")
        if date_from is not None and states:
            opening = max(bisect.bisect_right(self._dates, date_from) - 1, 0)
            prev_baseline = states[opening].cumulative_external_cash_flow
            nav_snapshots = [NAVSnapshot(date=states[opening].date, nav=states[opening].nav_value)] + [NAVSnapshot(date=s.date, nav=s.nav_value) for s in states[opening + 1 :]]
            states = states[opening + 1 :]
        else:
            nav_snapshots = [NAVSnapshot(date=s.date, nav=s.nav_value) for s in states]
        cash_flows: list[CashFlowInput] = []
        for s in states:
            delta = s.cumulative_external_cash_flow - prev_baseline
            prev_baseline = s.cumulative_external_cash_flow
            if delta != 0:
                cash_flows.append(CashFlowInput(date=s.date, amount=-delta))
        return nav_snapshots, cash_flows

    def build_allocation_current(
        self,
    ) -> tuple[list[dict], list[dict], list[dict]]:
        """Build current allocation from the last daily state.

        Returns (by_type, by_sector, by_geography) as lists of AllocationItem-like dicts.
        """
        if not self.daily_states:
            return [], [], []

        last = self.daily_states[-1]

        def _alloc(d: dict[str, Decimal], use_sector_emoji: bool = False) -> list[dict]:
            percents = slice_percents(d)
            return [
                {
                    "name": name,
                    "value": percents[name].quantize(Decimal("0.01")),
                    "amount": amt,
                    "emoji": sector_emoji(name) if use_sector_emoji else None,
                }
                for name, amt in sorted(d.items(), key=lambda x: -x[1])
            ]

        return _alloc(last.by_type), _alloc(last.by_sector, use_sector_emoji=True), _alloc(last.by_geography)

    def build_allocation_history(self, dimension: str, date_from: date_type | None = None) -> list[dict]:
        """Build allocation history series for a given dimension.

        Returns list of {date, components: [{name, value, amount}]} dicts.
        """
        attr_map = {"type": "by_type", "sector": "by_sector", "geography": "by_geography"}
        attr = attr_map.get(dimension, "by_type")

        result = []
        for s in self.daily_states:
            if date_from and s.date < date_from:
                continue
            d = getattr(s, attr, {})
            percents = slice_percents(d)
            components = [
                {
                    "name": name,
                    "value": percents[name].quantize(Decimal("0.01")),
                    "amount": amt,
                }
                for name, amt in sorted(d.items(), key=lambda x: -x[1])
            ]
            result.append({"date": s.date, "components": components})
        return result

    def build_data_quality_report(self, **kwargs: Any) -> DataQualityReport:
        """The data-quality report of these daily states: see ``data_quality.build_data_quality_report``."""
        return build_data_quality_report(self.daily_states, **kwargs)
