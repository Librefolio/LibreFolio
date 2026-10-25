"""Views derived from the daily states: history, per-broker P&L, candles, acquisition funding, performance inputs, allocation; and the cost positions."""

from __future__ import annotations

import bisect
import calendar
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import date as date_type
from datetime import timedelta
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
from backend.app.services.financial_math.portfolio.models import ClassifiedTransaction, DailyPortfolioState, DailyStates
from backend.app.services.financial_math.returns import CashFlowInput, NAVSnapshot
from backend.app.services.financial_math.series_steps import steps_from_rows
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


#: A step of the history longer than this many days gets a true MWRR point at each month end inside it (D-P4, §2)
MWRR_LONG_STEP_DAYS = 62
#: At most this many monthly MWRR points a step, evenly spread over its month ends
MWRR_MAX_MONTHLY_POINTS = 24


def _month_ends_inside(first: date_type, last: date_type) -> list[date_type]:
    """The last day of each calendar month strictly between ``first`` and ``last``."""
    ends: list[date_type] = []
    year, month = first.year, first.month
    while True:
        end = date_type(year, month, calendar.monthrange(year, month)[1])
        if end >= last:
            return ends
        if end > first:
            ends.append(end)
        if year == date_type.max.year and month == 12:
            return ends
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def mwrr_line_days(steps: Iterable[Any]) -> list[date_type]:
    """The days of the history's MWRR line (D-P4, contract §2): each step's ``date`` and ``through``, plus, in a step
    longer than :data:`MWRR_LONG_STEP_DAYS` days, the month ends strictly inside it — at most
    :data:`MWRR_MAX_MONTHLY_POINTS`, evenly spread when there are more. Sorted, no duplicate."""
    days: set[date_type] = set()
    for step in steps:
        first, last = (step["date"], step["through"]) if isinstance(step, Mapping) else (step.date, step.through)
        days.update((first, last))
        if (last - first).days + 1 > MWRR_LONG_STEP_DAYS:
            ends = _month_ends_inside(first, last)
            if len(ends) > MWRR_MAX_MONTHLY_POINTS:
                ends = [ends[index * (len(ends) - 1) // (MWRR_MAX_MONTHLY_POINTS - 1)] for index in range(MWRR_MAX_MONTHLY_POINTS)]
            days.update(ends)
    return sorted(days)


def _amount_or_none(amount: Decimal) -> Decimal | None:
    """The history's optional amounts: None when zero, as the point has always given them."""
    return amount if amount else None


#: The history point's money fields, each with the state's amount it shows (an optional one is None when zero)
_HISTORY_AMOUNTS: tuple[tuple[str, Callable[[DailyPortfolioState], Decimal | None]], ...] = (
    ("cash_value", lambda s: s.cash_value),
    ("market_value", lambda s: s.market_value),
    ("broker_nav_value", lambda s: s.broker_nav_value),
    ("in_transit_cash_value", lambda s: _amount_or_none(s.in_transit_cash_value)),
    ("in_transit_asset_market_value", lambda s: _amount_or_none(s.in_transit_asset_market_value)),
    ("in_transit_market_value", lambda s: _amount_or_none(s.in_transit_market_value)),
    ("nav_value", lambda s: s.nav_value),
    ("open_cost_basis", lambda s: _amount_or_none(s.open_cost_basis)),
    ("in_transit_asset_cost_basis", lambda s: _amount_or_none(s.in_transit_asset_cost_basis)),
    ("in_transit_book_value", lambda s: _amount_or_none(s.in_transit_book_value)),
    ("book_value", lambda s: _amount_or_none(s.book_value)),
    ("capital_baseline", lambda s: s.cumulative_external_cash_flow),
    ("book_asset_like", lambda s: s.book_asset_like),
    ("cash_from_contributed_capital", lambda s: s.cash_from_contributed_capital),
    ("cash_from_generated_returns", lambda s: s.cash_from_generated_returns),
    ("total_pnl", lambda s: s.total_pnl),
    ("unrealized_gain_loss", lambda s: _amount_or_none(s.unrealized_gain_loss)),
)


# =============================================================================
# DERIVED VIEWS BUILDER — Converts DailyPortfolioState[] into API DTOs
# =============================================================================


class DerivedViewsBuilder:
    """Derives summary, history, allocation, and performance views from daily states.

    Pure function — no I/O.
    """

    def __init__(
        self,
        daily_states: Sequence[DailyPortfolioState],
        target_currency: str,
    ) -> None:
        self.daily_states = daily_states
        self.target_currency = target_currency
        # One state a day, ascending: the engine's DailyStates finds a day by date arithmetic (P4), any other sequence
        # by bisection over its dates
        self._dates = None if isinstance(daily_states, DailyStates) else [state.date for state in daily_states]

    def _bisect_left(self, day: date_type) -> int:
        """The index of the first state dated on or after ``day``."""
        if self._dates is not None:
            return bisect.bisect_left(self._dates, day)
        first = self.daily_states.first_date
        return 0 if first is None else min(max((day - first).days, 0), len(self.daily_states))

    def _bisect_right(self, day: date_type) -> int:
        """The index of the first state dated after ``day``."""
        if self._dates is not None:
            return bisect.bisect_right(self._dates, day)
        first = self.daily_states.first_date
        return 0 if first is None else min(max((day - first).days + 1, 0), len(self.daily_states))

    def _window(self, date_from: date_type | None, date_to: date_type | None, *, exclusive_start: bool = False) -> list[DailyPortfolioState]:
        """The states of ``[date_from, date_to]`` (``(date_from, date_to]`` with ``exclusive_start``), an open bound
        reaching the end of the history: a view built for a window builds only its days (P2, N74). On the engine's
        DailyStates it builds every quiet day: the step views read :meth:`_change_rows` instead (D-P4)."""
        start = 0 if date_from is None else (self._bisect_right if exclusive_start else self._bisect_left)(date_from)
        end = len(self.daily_states) if date_to is None else self._bisect_right(date_to)
        return list(self.daily_states[start:end])

    def window_range(self, date_from: date_type | None, date_to: date_type | None) -> tuple[date_type, date_type] | None:
        """The report's ``range`` (D-P4): the days of ``[date_from, date_to]`` that have a state, as ``(start, end)``; an
        open bound reaches the history's end. None when the window holds no state."""
        if not self.daily_states:
            return None
        first, last = (self._dates[0], self._dates[-1]) if self._dates is not None else (self.daily_states.first_date, self.daily_states.last_date)
        start = first if date_from is None else max(date_from, first)
        end = last if date_to is None else min(date_to, last)
        return (start, end) if start <= end else None

    def _change_rows(self, start: date_type, end: date_type, extra_days: Iterable[date_type] = ()) -> list[tuple[date_type, DailyPortfolioState]]:
        """The days of ``[start, end]`` on which a view may change, each with the state it reads, in order: ``start``,
        every engine segment start inside, and ``extra_days`` inside (D-P4). Any other sequence gives every state.

        The state is the segment's own, read-only and never built for the day: its ``date``, ``external_cash_flow`` and
        ``acquisition_funding`` are its segment start's, which no step view reads.
        """
        if self._dates is not None:
            return [(state.date, state) for state in self._window(start, end)]
        rows: dict[date_type, DailyPortfolioState] = {}
        segments = self.daily_states.segments
        first = max(bisect.bisect_right(segments, start, key=lambda segment: segment.start) - 1, 0)
        for segment in segments[first:]:
            if segment.start > end:
                break
            if segment.end >= start:
                rows[max(segment.start, start)] = segment.state
        for day in extra_days:
            if start <= day <= end and day not in rows:
                rows[day] = self.daily_states.segment_at(day).state
        return sorted(rows.items(), key=lambda row: row[0])

    def change_days(self, start: date_type, end: date_type, extra_days: Iterable[date_type] = ()) -> list[date_type]:
        """The days of :meth:`_change_rows`: where a step of a view built over ``[start, end]`` may begin."""
        return [day for day, _state in self._change_rows(start, end, extra_days)]

    def build_history(
        self,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        *,
        metrics: Callable[[date_type], Mapping[str, Any]] | None = None,
        extra_days: Iterable[date_type] = (),
    ) -> list[dict]:
        """The history of ``[date_from, date_to]`` in steps (D-P4): PortfolioHistoryPoint-compatible dicts, each holding
        from its ``date`` to its ``through``.

        ``metrics(day)``: more fields of a change day (the service's TWRR and ROI), part of the step's values; a day where
        they change is in ``extra_days``. Two consecutive change days with the same values — Decimals with their
        exponent — make one step. Returns dicts (not PortfolioHistoryPoint) to avoid a circular import; the API adapter
        converts them.
        """
        window = self.window_range(date_from, date_to)
        if window is None:
            return []
        start, end = window
        rows = []
        for day, state in self._change_rows(start, end, extra_days):
            amounts = tuple(amount(state) for _name, amount in _HISTORY_AMOUNTS)
            extra = dict(metrics(day)) if metrics is not None else {}
            rows.append((day, amounts, extra))
        steps = steps_from_rows(rows, day=lambda row: row[0], values=lambda row: (row[1], tuple(row[2].items())), range_start=start, range_end=end)
        code = self.target_currency
        return [
            {
                "date": step.date,
                "through": step.through,
                **{name: (CurrencySchema(code=code, amount=amount) if amount is not None else None) for (name, _amount), amount in zip(_HISTORY_AMOUNTS, step.row[1], strict=True)},
                **step.row[2],
            }
            for step in steps
        ]

    def build_broker_pnl_history(self, date_from: date_type | None = None, date_to: date_type | None = None) -> dict[int, list[dict]]:
        """Per-broker additive P&L history in steps: broker_id -> [{date, through, total_pnl}, ...] (D-P4).

        Derived from DailyPortfolioState.broker_contributions (see G1a/§4.2), which
        is built additively in the same daily replay as the scope-aggregate
        total_pnl, so for every day sum(value of each broker's step) == aggregate total_pnl.
        Each broker's steps are maximal: they end where its own P&L changes. A day a broker is not in the state is a gap
        in its series. Returns raw dicts (not BrokerPnlHistory) to avoid circular import, mirroring
        build_history()'s adapter-conversion pattern.
        """
        window = self.window_range(date_from, date_to)
        if window is None:
            return {}
        start, end = window
        rows: list[tuple[date_type, int, Decimal | None]] = []
        seen: dict[int, None] = {}
        for day, state in self._change_rows(start, end):
            for bid, contribution in state.broker_contributions.items():
                seen.setdefault(bid)
                rows.append((day, bid, contribution.pnl_contribution))
            rows.extend((day, bid, None) for bid in seen if bid not in state.broker_contributions)
        steps = steps_from_rows(rows, day=lambda row: row[0], values=lambda row: row[2], key=lambda row: row[1], is_gap=lambda row: row[2] is None, range_start=start, range_end=end)
        by_broker: dict[int, list[dict]] = {}
        for step in steps:
            by_broker.setdefault(step.key, []).append({"date": step.date, "through": step.through, "total_pnl": CurrencySchema(code=self.target_currency, amount=step.row[2])})
        return by_broker

    def build_pnl_candles(self, date_from: date_type | None = None, date_to: date_type | None = None) -> list[dict]:
        """Synthetic total-P&L candle series (G1b) in steps: [{date, through, open, high, low, close}, ...] (D-P4).

        Days whose candle is unavailable (DailyPortfolioState.pnl_candle is None — a held
        asset's valuation was MISSING that day) are a gap: no step covers them, rather than a
        guessed/zeroed candle. A quiet day carries the candle of the last computed day, as it always did, so a step has
        one candle. ``close`` reproduces the canonical PortfolioHistoryPoint.total_pnl of
        the same day exactly (see PnlCandleContribution / DailyStateBuilder §4.3). Returns raw dicts, mirroring
        build_history()'s adapter-conversion pattern (avoids a circular import on the API schema).
        """
        window = self.window_range(date_from, date_to)
        if window is None:
            return []
        start, end = window
        rows = [(day, state.pnl_candle) for day, state in self._change_rows(start, end)]
        steps = steps_from_rows(
            rows,
            day=lambda row: row[0],
            values=lambda row: (row[1].open, row[1].high, row[1].low, row[1].close),
            is_gap=lambda row: row[1] is None,
            range_start=start,
            range_end=end,
        )
        code = self.target_currency
        return [
            {
                "date": step.date,
                "through": step.through,
                "open": CurrencySchema(code=code, amount=step.row[1].open),
                "high": CurrencySchema(code=code, amount=step.row[1].high),
                "low": CurrencySchema(code=code, amount=step.row[1].low),
                "close": CurrencySchema(code=code, amount=step.row[1].close),
            }
            for step in steps
        ]

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
        # A flow series: a BUY dated date_from belongs to the previous period, (date_from, date_to]. A quiet day acquires
        # nothing (P4): only a segment's start can carry funding
        if self._dates is not None:
            states = self._window(date_from, date_to, exclusive_start=True)
        else:
            states = [segment.state for segment in self.daily_states.segments if (date_from is None or segment.start > date_from) and (date_to is None or segment.start <= date_to)]
        for s in states:
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
        *,
        days: Iterable[date_type] | None = None,
    ) -> tuple[list, list]:
        """Extract NAV snapshots and the invested-capital flow series for ROI/TWRR/MWRR.

        Returns (nav_snapshots, cash_flows) compatible with the ``returns`` functions.

        With ``date_from`` (P2, N74), only what ``returns.rebase_to_period`` keeps of them for that period: the snapshots
        from the period's opening state on (the last one dated on or before ``date_from``, else the first) and the flows
        dated after it, so the rebase gives the same period without building the history before it.

        On the engine's DailyStates (D-P4) the snapshots are not one a day: the opening day, then ``days`` after it —
        by default every segment start and the last day. A quiet day changes neither the NAV nor the baseline, so each
        TWRR, ROI and MWRR value the ``returns`` functions give on a snapshot's day is the one the daily series gives on
        that day, bit for bit (a quiet sub-period's factor is exactly 1; the flows are dated on segment starts and the
        MWRR solves each day alone). Any other sequence gives one snapshot a day.

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
        if not self.daily_states:
            return [], []
        if self._dates is None:
            return self._sparse_performance_inputs(date_from, days)
        prev_baseline = Decimal("0")
        states = self._window(self._opening_day(date_from), None) if date_from is not None else list(self.daily_states)
        nav_snapshots = [NAVSnapshot(date=s.date, nav=s.nav_value) for s in states]
        if date_from is not None and states:
            # The opening state: its baseline is where the period's flows start from
            prev_baseline = states[0].cumulative_external_cash_flow
            states = states[1:]
        cash_flows: list[CashFlowInput] = []
        for s in states:
            delta = s.cumulative_external_cash_flow - prev_baseline
            prev_baseline = s.cumulative_external_cash_flow
            if delta != 0:
                cash_flows.append(CashFlowInput(date=s.date, amount=-delta))
        return nav_snapshots, cash_flows

    def _sparse_performance_inputs(self, date_from: date_type | None, days: Iterable[date_type] | None) -> tuple[list, list]:
        """:meth:`build_performance_inputs` on the engine's DailyStates: the snapshots of the opening day and of ``days``
        after it (default: every segment start and the last day), the flows of the segment starts (D-P4)."""
        states = self.daily_states
        opening = self._opening_day(date_from) if date_from is not None else states.first_date
        last = states.last_date
        segments = states.segments
        opening_index = max(bisect.bisect_right(segments, opening, key=lambda segment: segment.start) - 1, 0)
        later = segments[opening_index + 1 :]  # the segments starting after the opening day
        snapshot_days = {opening}
        if days is None:
            snapshot_days.update(segment.start for segment in later)
            snapshot_days.add(last)
        else:
            snapshot_days.update(day for day in days if opening < day <= last)
        nav_snapshots = [NAVSnapshot(date=day, nav=states.segment_at(day).state.nav_value) for day in sorted(snapshot_days)]
        # The opening state's baseline is where the period's flows start from; without date_from the first day's own
        # baseline is its flow
        prev_baseline = segments[opening_index].state.cumulative_external_cash_flow if date_from is not None else Decimal("0")
        cash_flows: list[CashFlowInput] = []
        for segment in later if date_from is not None else segments:
            delta = segment.state.cumulative_external_cash_flow - prev_baseline
            prev_baseline = segment.state.cumulative_external_cash_flow
            if delta != 0:
                cash_flows.append(CashFlowInput(date=segment.start, amount=-delta))
        return nav_snapshots, cash_flows

    def _opening_day(self, date_from: date_type) -> date_type:
        """The day of the period's opening state: the last one on or before ``date_from``, else the first."""
        opening = max(self._bisect_right(date_from) - 1, 0)
        if self._dates is not None:
            return self._dates[opening]
        return self.daily_states.first_date + timedelta(days=opening)

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
        """Build allocation history series for a given dimension, in steps (D-P4).

        Returns list of {date, through, components: [{name, value, amount}]} dicts.
        """
        attr_map = {"type": "by_type", "sector": "by_sector", "geography": "by_geography"}
        attr = attr_map.get(dimension, "by_type")

        def components(state: DailyPortfolioState) -> list[dict]:
            d = getattr(state, attr, {})
            percents = slice_percents(d)
            return [{"name": name, "value": percents[name].quantize(Decimal("0.01")), "amount": amt} for name, amt in sorted(d.items(), key=lambda x: -x[1])]

        return self._component_steps(components, date_from)

    def _component_steps(self, components: Callable[[DailyPortfolioState], list[dict]], date_from: date_type | None) -> list[dict]:
        """``{date, through, components}`` steps from ``date_from`` to the end: one per run of identical components."""
        window = self.window_range(date_from or None, None)
        if window is None:
            return []
        start, end = window
        rows = [(day, components(state)) for day, state in self._change_rows(start, end)]
        steps = steps_from_rows(rows, day=lambda row: row[0], values=lambda row: row[1], range_start=start, range_end=end)
        return [{"date": step.date, "through": step.through, "components": step.row[1]} for step in steps]

    @staticmethod
    def _asset_components(state: DailyPortfolioState, names: Mapping[int, str], *, with_emoji: bool) -> list[dict]:
        """The asset dimension of one day: a slice per held asset (``by_asset``) and the Liquidity slice, as by_type's
        (the cash and the cash in transit), with their shares of the total, largest first."""
        slices: dict[int | None, Decimal] = dict(state.by_asset)
        slices[None] = state.cash_value + state.in_transit_cash_value
        percents = slice_percents(slices)
        components = []
        for asset_id, amount in sorted(slices.items(), key=lambda item: -item[1]):
            component = {
                "name": "Liquidity" if asset_id is None else names.get(asset_id, f"Asset {asset_id}"),
                "id": asset_id,
                "value": percents[asset_id].quantize(Decimal("0.01")),
                "amount": amount,
            }
            if with_emoji:
                component["emoji"] = None
            components.append(component)
        return components

    def allocation_asset_ids(self, date_from: date_type | None = None) -> set[int]:
        """The assets with a slice in the asset dimension from ``date_from`` on (to name them)."""
        if self._dates is None:
            return {asset_id for segment in self.daily_states.iter_segments(date_from, None) for asset_id in segment.state.by_asset}
        return {asset_id for state in self._window(date_from, None) for asset_id in state.by_asset}

    def build_asset_allocation_current(self, names: Mapping[int, str]) -> list[dict]:
        """The asset dimension of the allocation on the last day (AllocationItem-like dicts, ``id`` = the asset's)."""
        if not self.daily_states:
            return []
        return self._asset_components(self.daily_states[-1], names, with_emoji=True)

    def build_asset_allocation_history(self, names: Mapping[int, str], date_from: date_type | None = None) -> list[dict]:
        """The asset dimension's history from ``date_from``: ``{date, through, components}`` steps, as
        build_allocation_history."""
        return self._component_steps(lambda state: self._asset_components(state, names, with_emoji=False), date_from)

    def build_data_quality_report(self, **kwargs: Any) -> DataQualityReport:
        """The data-quality report of these daily states: see ``data_quality.build_data_quality_report``."""
        return build_data_quality_report(self.daily_states, **kwargs)
