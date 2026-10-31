"""MF-K3 (workstream MF, wave 6) — the Dashboard's TWRR and simple ROI: one rule for the card and the line.

Module under test: ``backend/app/services/financial_math/returns.py``. New in the working tree (HEAD ``f33d91b4f`` has
none of them):

* ``PeriodTWRRPoint`` and ``period_twrr_series(navs, flows)``: at every snapshot after the first the cumulative TWRR
  (``calculate_twrr_series``), but None where that snapshot's NAV is at or below zero — an emptied portfolio has no
  time-weighted return to show, as the MWRR has none (D-MF5). The sub-periods after it keep compounding (a sub-period
  starting from 0 returns 0), so a portfolio filled again shows its TWRR again. Empty without two snapshots or without
  flows;
* ``period_twrr(navs, flows)``: the last point of that series — the card is the line's last point;
* ``period_roi_cash_flows(navs, flows, date_from)``: the flows the period's simple ROI counts its capital from: the
  rebased ones (``rebase_to_period``), except when ``date_from`` precedes every snapshot — then every flow, the first
  day's deposit included (the rebase leaves it out, being inside the first NAV);
* ``annualizes(days)``: the floor of ``cumulative_to_annualized`` as a predicate.

Red on HEAD ``f33d91b4f``: the whole file fails at collection, ``ImportError: cannot import name 'PeriodTWRRPoint' from
'backend.app.services.financial_math.returns'`` — new API. ``TestHeadSeriesForReference`` states what HEAD's
``calculate_twrr_series`` gave on the same book (a flat number on the emptied day), the reason for the change.

Isolation: PURE — no database, no server, no network, no clock. Runs in ``./dev.py test services financial-math``;
alone: ``./dev.py test services financial-math test_period_twrr_and_roi_flows``.

Reference: backend/app/services/financial_math/returns.py (period_twrr_series, period_twrr, period_roi_cash_flows,
rebase_to_period, calculate_twrr_series, calculate_simple_roi_series).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.app.services.financial_math.returns import (
    CashFlowInput,
    NAVSnapshot,
    PeriodTWRRPoint,
    annualizes,
    calculate_twrr_series,
    period_roi_cash_flows,
    period_twrr,
    period_twrr_series,
    rebase_to_period,
)

D = Decimal

D1, D2, D3, D4, D5 = (date(2025, 3, day) for day in (3, 4, 5, 6, 7))

#: Deposit 1 000 on D1, +10 % to D2, everything withdrawn on D3 (NAV 0), 500 deposited again on D4, +10 % to D5.
REFILLED_NAVS = [NAVSnapshot(D1, D("1000")), NAVSnapshot(D2, D("1100")), NAVSnapshot(D3, D("0")), NAVSnapshot(D4, D("500")), NAVSnapshot(D5, D("550"))]
REFILLED_FLOWS = [CashFlowInput(D1, D("-1000")), CashFlowInput(D3, D("1100")), CashFlowInput(D4, D("-500"))]


def _by_date(points: list[PeriodTWRRPoint]) -> dict[date, Decimal | None]:
    return {point.date: point.twrr for point in points}


class TestPeriodTwrrSeries:
    def test_none_on_an_emptied_day_and_compounding_after_a_refill(self):
        """D2 +10 %; D3 the NAV is 0: None; D4 refilled, the TWRR shows again (still 10 %: the emptied sub-periods
        returned 0); D5 another +10 %: 21 %."""
        series = _by_date(period_twrr_series(REFILLED_NAVS, REFILLED_FLOWS))
        assert series == {D2: D("0.1"), D3: None, D4: D("0.1"), D5: D("0.21")}, series

    def test_a_negative_value_has_no_twrr(self):
        navs = [NAVSnapshot(D1, D("1000")), NAVSnapshot(D2, D("-5"))]
        flows = [CashFlowInput(D1, D("-1000"))]
        assert _by_date(period_twrr_series(navs, flows)) == {D2: None}

    def test_the_points_are_house_points(self):
        points = period_twrr_series(REFILLED_NAVS, REFILLED_FLOWS)
        assert all(isinstance(point, PeriodTWRRPoint) for point in points)
        assert [point.date for point in points] == [D2, D3, D4, D5], "one point per snapshot after the first"

    def test_where_the_value_is_positive_the_series_is_calculate_twrr_series(self):
        expected = {point.date: point.twrr for point in calculate_twrr_series(REFILLED_NAVS, REFILLED_FLOWS)}
        for day, twrr in _by_date(period_twrr_series(REFILLED_NAVS, REFILLED_FLOWS)).items():
            if twrr is not None:
                assert twrr == expected[day] and str(twrr) == str(expected[day]), day

    def test_empty_without_two_snapshots(self):
        assert period_twrr_series(REFILLED_NAVS[:1], REFILLED_FLOWS) == []
        assert period_twrr_series([], REFILLED_FLOWS) == []

    def test_empty_without_flows(self):
        assert period_twrr_series(REFILLED_NAVS, []) == []


class TestPeriodTwrrIsTheLastPoint:
    def test_card_on_a_refilled_book(self):
        assert period_twrr(REFILLED_NAVS, REFILLED_FLOWS) == period_twrr_series(REFILLED_NAVS, REFILLED_FLOWS)[-1].twrr == D("0.21")

    def test_card_on_an_emptied_book(self):
        """Ending on the emptied day: the card is «—», as its last point."""
        navs, flows = REFILLED_NAVS[:3], REFILLED_FLOWS[:2]
        assert period_twrr_series(navs, flows)[-1].twrr is None
        assert period_twrr(navs, flows) is None

    def test_no_card_without_a_line(self):
        assert period_twrr(REFILLED_NAVS[:1], REFILLED_FLOWS) is None
        assert period_twrr(REFILLED_NAVS, []) is None


class TestHeadSeriesForReference:
    """Guard: HEAD's line was ``calculate_twrr_series`` — on the emptied day it showed a flat 10 %, the reason for
    MF-K3."""

    def test_calculate_twrr_series_is_flat_on_the_emptied_day(self):
        head = {point.date: point.twrr for point in calculate_twrr_series(REFILLED_NAVS, REFILLED_FLOWS)}
        assert head[D3] == D("0.1"), head


class TestPeriodRoiCashFlows:
    #: Deposit 1 000 on D1, another 200 on D3; snapshots D1 … D5.
    NAVS = [NAVSnapshot(D1, D("1000")), NAVSnapshot(D2, D("1050")), NAVSnapshot(D3, D("1260")), NAVSnapshot(D4, D("1300")), NAVSnapshot(D5, D("1320"))]
    FLOWS = [CashFlowInput(D1, D("-1000")), CashFlowInput(D3, D("-200"))]

    def test_no_date_from_every_flow(self):
        assert period_roi_cash_flows(self.NAVS, self.FLOWS, None) == tuple(self.FLOWS)

    def test_date_from_inside_the_rebased_flows(self):
        """From D2: the opening NAV 1 050 as a synthetic deposit on D2, and the D3 deposit — the rebase's own flows."""
        flows = period_roi_cash_flows(self.NAVS, self.FLOWS, D2)
        assert flows == rebase_to_period(self.NAVS, self.FLOWS, D2).cash_flows
        assert flows == (CashFlowInput(D2, D("-1050")), CashFlowInput(D3, D("-200")))

    def test_date_from_on_the_first_snapshot_is_the_rebase(self):
        """On the first snapshot (not before it): the rebase, the D1 NAV as the opening deposit."""
        assert period_roi_cash_flows(self.NAVS, self.FLOWS, D1) == rebase_to_period(self.NAVS, self.FLOWS, D1).cash_flows

    def test_date_from_before_every_snapshot_every_flow(self):
        """From 03-01, before the portfolio: every flow, the first day's deposit included. The rebase would open empty
        and leave the D1 deposit out — an ROI with no capital at all."""
        before = date(2025, 3, 1)
        rebased = rebase_to_period(self.NAVS, self.FLOWS, before).cash_flows
        assert CashFlowInput(D1, D("-1000")) not in rebased, f"precondition: the rebase leaves the first day's deposit out, {rebased}"
        assert period_roi_cash_flows(self.NAVS, self.FLOWS, before) == tuple(self.FLOWS)

    def test_without_snapshots_the_rebase(self):
        assert period_roi_cash_flows([], self.FLOWS, date(2025, 3, 1)) == tuple(self.FLOWS)


class TestAnnualizes:
    def test_the_floor(self):
        assert [annualizes(days) for days in (-1, 0, 29, 30, 365)] == [False, False, False, True, True]
        assert annualizes(5, min_days=5) is True
        assert annualizes(0, min_days=0) is False
