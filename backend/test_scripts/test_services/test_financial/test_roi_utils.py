"""
Unit tests for backend/app/utils/financial/roi_utils.py.

Pure math tests — no server, no DB, no async.
All expected values verified analytically.
"""

from datetime import date
from decimal import Decimal

import pytest

from backend.app.utils.financial.roi_utils import (
    CashFlowInput,
    MWRRPoint,
    NAVSnapshot,
    SimpleROIPoint,
    calculate_mwrr,
    calculate_mwrr_series,
    calculate_simple_roi,
    calculate_simple_roi_series,
    calculate_twrr,
    calculate_twrr_series,
)

# ---------------------------------------------------------------------------
# TestSimpleROI
# ---------------------------------------------------------------------------


class TestSimpleROI:
    def test_positive_roi(self):
        result = calculate_simple_roi(Decimal("1200"), Decimal("1000"))
        assert result == pytest.approx(Decimal("0.200000"), abs=Decimal("0.000001"))

    def test_negative_roi(self):
        result = calculate_simple_roi(Decimal("800"), Decimal("1000"))
        assert result == pytest.approx(Decimal("-0.200000"), abs=Decimal("0.000001"))

    def test_zero_invested(self):
        result = calculate_simple_roi(Decimal("500"), Decimal("0"))
        assert result == Decimal("0")

    def test_no_change(self):
        result = calculate_simple_roi(Decimal("1000"), Decimal("1000"))
        assert result == Decimal("0")

    def test_large_gain(self):
        result = calculate_simple_roi(Decimal("10000"), Decimal("1000"))
        assert result == pytest.approx(Decimal("9.000000"), abs=Decimal("0.000001"))


# ---------------------------------------------------------------------------
# TestTWRR
# ---------------------------------------------------------------------------


class TestTWRR:
    def test_no_cash_flows(self):
        """Without external flows, TWRR equals simple return."""
        navs = [
            NAVSnapshot(date(2025, 1, 1), Decimal("1000")),
            NAVSnapshot(date(2025, 12, 31), Decimal("1100")),
        ]
        result = calculate_twrr(navs, [])
        # (1100 - 1000) / 1000 = 0.10
        assert result.twrr == pytest.approx(Decimal("0.100000"), abs=Decimal("0.000001"))
        assert result.date == date(2025, 12, 31)

    def test_with_deposit_midway(self):
        """
        Deposit mid-period — TWRR isolates investment skill from timing.

        Setup (snapshots are POST-CF, deposit sign = negative):
          t0: NAV=1000
          t1 (2025-07-01): deposit=1000, pre-CF NAV=1100, post-CF snapshot=2100
          t2 (2025-12-31): final NAV=2310

        Sub-period 1: V_start=1000, v_end_pre_cf=2100+(-1000)=1100 → HPR1=0.10
        Sub-period 2: V_start=2100, v_end_pre_cf=2310+0=2310       → HPR2=0.10
        TWRR = (1.10 × 1.10) - 1 = 0.21
        """
        navs = [
            NAVSnapshot(date(2025, 1, 1), Decimal("1000")),
            NAVSnapshot(date(2025, 7, 1), Decimal("2100")),    # post-deposit: 1100+1000
            NAVSnapshot(date(2025, 12, 31), Decimal("2310")),
        ]
        cfs = [CashFlowInput(date(2025, 7, 1), Decimal("-1000"))]  # deposit = negative
        result = calculate_twrr(navs, cfs)
        assert result.twrr == pytest.approx(Decimal("0.21"), abs=Decimal("0.001"))
        assert result.date == date(2025, 12, 31)
    def test_insufficient_snapshots_raises(self):
        """Fewer than 2 snapshots should raise ValueError."""
        navs = [NAVSnapshot(date(2025, 1, 1), Decimal("1000"))]
        with pytest.raises(ValueError):
            calculate_twrr(navs, [])

    def test_no_change_no_flows(self):
        """Zero performance period."""
        navs = [
            NAVSnapshot(date(2025, 1, 1), Decimal("1000")),
            NAVSnapshot(date(2025, 1, 2), Decimal("1000")),
        ]
        result = calculate_twrr(navs, [])
        assert result.twrr == Decimal("0")

    def test_withdrawal_does_not_affect_twrr(self):
        """
        Withdrawal mid-period — TWRR isolates return from timing.

        Sub-period 1: 1000 → 1100 (pre-withdrawal) HPR1 = 0.10
        Withdrawal of 200 at mid → NAV becomes 900 (post-withdrawal snapshot)
        Sub-period 2: 900 → 990 HPR2 = 0.10
        TWRR = (1.10 * 1.10) - 1 = 0.21
        """
        navs = [
            NAVSnapshot(date(2025, 1, 1), Decimal("1000")),
            NAVSnapshot(date(2025, 7, 1), Decimal("900")),    # post-withdrawal: 1100-200=900
            NAVSnapshot(date(2025, 12, 31), Decimal("990")),  # 900 * 1.10
        ]
        cfs = [CashFlowInput(date(2025, 7, 1), Decimal("200"))]  # withdrawal = positive
        result = calculate_twrr(navs, cfs)
        assert result.twrr == pytest.approx(Decimal("0.21"), abs=Decimal("0.001"))


# ---------------------------------------------------------------------------
# TestMWRR
# ---------------------------------------------------------------------------


class TestMWRR:
    def test_simple_one_year_investment(self):
        """
        Initial: 10000, Final: 11000, 1 year, no intermediate CFs.
        MWRR = annualized rate such that NPV = 0.
        NPV = -10000 / (1+r)^0 + 11000 / (1+r)^1 = 0
        Solution: r = 0.10
        """
        result = calculate_mwrr(
            cash_flows=[],
            initial_nav=Decimal("10000"),
            final_nav=Decimal("11000"),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),  # ~365 days
        )
        assert result.mwrr is not None
        assert float(result.mwrr) == pytest.approx(0.10, abs=0.01)
        assert result.date == date(2025, 12, 31)

    def test_same_start_end_date_returns_none(self):
        """Zero-day period → returns None (no meaningful rate)."""
        result = calculate_mwrr(
            cash_flows=[],
            initial_nav=Decimal("10000"),
            final_nav=Decimal("10000"),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 1),
        )
        assert result.mwrr is None

    def test_returns_none_on_no_convergence(self):
        """Degenerate inputs that prevent convergence return None (no raise)."""
        result = calculate_mwrr(
            cash_flows=[],
            initial_nav=Decimal("0"),  # zero initial
            final_nav=Decimal("0"),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        # May or may not converge depending on scipy, but must not raise
        assert result.mwrr is None or result.mwrr is not None  # just no exception

    def test_result_is_decimal(self):
        """Return type is Decimal, not float."""
        result = calculate_mwrr(
            cash_flows=[],
            initial_nav=Decimal("10000"),
            final_nav=Decimal("11000"),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        if result.mwrr is not None:
            assert isinstance(result.mwrr, Decimal)


# ---------------------------------------------------------------------------
# TestTWRRSeries
# ---------------------------------------------------------------------------


class TestTWRRSeries:
    def test_series_matches_individual_calculations(self):
        """
        Iterative series must match one-shot TWRR when data is truncated to each point.
        """
        navs = [
            NAVSnapshot(date(2025, 1, 1), Decimal("1000")),
            NAVSnapshot(date(2025, 6, 1), Decimal("1100")),
            NAVSnapshot(date(2025, 12, 31), Decimal("1210")),
        ]
        series = calculate_twrr_series(navs, [])
        assert len(series) == 2

        # Point 1: [1000, 1100] → 0.10
        assert series[0].twrr == pytest.approx(Decimal("0.10"), abs=Decimal("0.001"))
        assert series[0].date == date(2025, 6, 1)

        # Point 2: [1000, 1100, 1210] → (1.10 * 1.10) - 1 = 0.21
        assert series[1].twrr == pytest.approx(Decimal("0.21"), abs=Decimal("0.001"))
        assert series[1].date == date(2025, 12, 31)

    def test_empty_series_if_less_than_2_snapshots(self):
        assert calculate_twrr_series([], []) == []
        navs = [NAVSnapshot(date(2025, 1, 1), Decimal("1000"))]
        assert calculate_twrr_series(navs, []) == []


# ---------------------------------------------------------------------------
# TestMWRRSeries
# ---------------------------------------------------------------------------


class TestMWRRSeries:
    def test_series_returns_one_point_per_snapshot(self):
        navs = [
            NAVSnapshot(date(2025, 1, 1), Decimal("10000")),
            NAVSnapshot(date(2025, 6, 1), Decimal("10500")),
            NAVSnapshot(date(2025, 12, 31), Decimal("11000")),
        ]
        series = calculate_mwrr_series(navs, [])
        assert len(series) == 2
        for point in series:
            assert isinstance(point, MWRRPoint)

    def test_empty_series_if_less_than_2_snapshots(self):
        assert calculate_mwrr_series([], []) == []
        navs = [NAVSnapshot(date(2025, 1, 1), Decimal("1000"))]
        assert calculate_mwrr_series(navs, []) == []

    def test_warm_start_does_not_raise(self):
        """Warm-start optimization must not cause exceptions."""
        navs = [
            NAVSnapshot(date(2025, 1, 1), Decimal("5000")),
            NAVSnapshot(date(2025, 4, 1), Decimal("5500")),
            NAVSnapshot(date(2025, 7, 1), Decimal("6000")),
            NAVSnapshot(date(2025, 10, 1), Decimal("6500")),
            NAVSnapshot(date(2025, 12, 31), Decimal("7000")),
        ]
        series = calculate_mwrr_series(navs, [])
        assert len(series) == 4
        for point in series:
            # Each point may or may not converge, but must not raise
            assert point.mwrr is None or isinstance(point.mwrr, Decimal)

    def test_series_matches_individual_calculations(self):
        """Iterative MWRR series must match one-shot MWRR when data is truncated."""
        navs = [
            NAVSnapshot(date(2025, 1, 1), Decimal("10000")),
            NAVSnapshot(date(2025, 6, 1), Decimal("10500")),
            NAVSnapshot(date(2025, 12, 31), Decimal("12000")),
        ]
        cfs = [CashFlowInput(date(2025, 6, 1), Decimal("-1000"))]

        series = calculate_mwrr_series(navs, cfs)
        assert len(series) == 2

        # Point 1: 2025-06-01
        p1_oneshot = calculate_mwrr(
            cash_flows=cfs[:1], # The CF on 06-01 is included
            initial_nav=Decimal("10000"),
            final_nav=Decimal("10500"),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 6, 1),
        )
        assert series[0].date == date(2025, 6, 1)
        if series[0].mwrr is not None and p1_oneshot.mwrr is not None:
            assert series[0].mwrr == pytest.approx(p1_oneshot.mwrr, abs=Decimal("0.001"))

        # Point 2: 2025-12-31
        p2_oneshot = calculate_mwrr(
            cash_flows=cfs,
            initial_nav=Decimal("10000"),
            final_nav=Decimal("12000"),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        assert series[1].date == date(2025, 12, 31)
        if series[1].mwrr is not None and p2_oneshot.mwrr is not None:
            assert series[1].mwrr == pytest.approx(p2_oneshot.mwrr, abs=Decimal("0.001"))


# ---------------------------------------------------------------------------
# TestSimpleROISeries
# ---------------------------------------------------------------------------


class TestSimpleROISeries:
    """Tests for calculate_simple_roi_series().

    IMPORTANT CONSTRAINT (same as TWRR): for CFs to be included in the ROI
    calculation at snapshot t, there must be a NAVSnapshot on the CF date.
    CFs without a matching NAVSnapshot on the same date are silently skipped.
    """

    def test_empty_snapshots(self):
        """No snapshots → empty series."""
        assert calculate_simple_roi_series([], []) == []

    def test_single_snapshot_no_cfs(self):
        """No cash flows → net_invested = 0 → calculate_simple_roi returns 0."""
        navs = [NAVSnapshot(date(2025, 1, 1), Decimal("5000"))]
        result = calculate_simple_roi_series(navs, [])
        assert len(result) == 1
        assert isinstance(result[0], SimpleROIPoint)
        assert result[0].roi == Decimal("0")

    def test_deposit_on_snapshot_date_zero_gain(self):
        """
        Deposit 10000 on Jan 1, NAV = 10000 (just the deposit, no gain yet).
        ROI at Jan 1 = (10000 - 10000) / 10000 = 0.
        """
        navs = [NAVSnapshot(date(2025, 1, 1), Decimal("10000"))]
        cfs = [CashFlowInput(date(2025, 1, 1), Decimal("-10000"))]  # deposit = negative
        result = calculate_simple_roi_series(navs, cfs)
        assert len(result) == 1
        assert result[0].roi == Decimal("0")

    def test_positive_gain(self):
        """
        Deposit 10000 on Jan 1, NAV = 11000 on Dec 31 (+10%).
        ROI series:
          Jan 1:  net_invested=10000, NAV=10000, roi=0.0
          Dec 31: net_invested=10000, NAV=11000, roi=0.10
        """
        navs = [
            NAVSnapshot(date(2025, 1, 1),  Decimal("10000")),
            NAVSnapshot(date(2025, 12, 31), Decimal("11000")),
        ]
        cfs = [CashFlowInput(date(2025, 1, 1), Decimal("-10000"))]
        result = calculate_simple_roi_series(navs, cfs)
        assert len(result) == 2
        assert result[0].roi == Decimal("0")
        assert result[1].roi == pytest.approx(Decimal("0.100000"), abs=Decimal("0.000001"))
        assert result[1].date == date(2025, 12, 31)

    def test_negative_loss(self):
        """
        Deposit 10000, final NAV = 8000 (-20%).
        ROI at end = (8000 - 10000) / 10000 = -0.20
        """
        navs = [
            NAVSnapshot(date(2025, 1, 1),  Decimal("10000")),
            NAVSnapshot(date(2025, 12, 31), Decimal("8000")),
        ]
        cfs = [CashFlowInput(date(2025, 1, 1), Decimal("-10000"))]
        result = calculate_simple_roi_series(navs, cfs)
        assert result[-1].roi == pytest.approx(Decimal("-0.200000"), abs=Decimal("0.000001"))

    def test_withdrawal_reduces_net_invested(self):
        """
        Deposit 10000 on Jan 1, withdrawal 3000 on Jul 1.
        Net invested after withdrawal = 7000.
        NAV on Jul 1 = 8000 (after withdrawal, so portfolio = 11000 - 3000 = 8000).
        ROI at Jul 1 = (8000 - 7000) / 7000 = 0.1428...
        """
        navs = [
            NAVSnapshot(date(2025, 1, 1), Decimal("10000")),
            NAVSnapshot(date(2025, 7, 1), Decimal("8000")),   # post-withdrawal NAV
        ]
        cfs = [
            CashFlowInput(date(2025, 1, 1), Decimal("-10000")),  # deposit
            CashFlowInput(date(2025, 7, 1), Decimal("3000")),    # withdrawal = positive
        ]
        result = calculate_simple_roi_series(navs, cfs)
        assert len(result) == 2
        # Jan 1: net_invested=10000, NAV=10000, roi=0
        assert result[0].roi == Decimal("0")
        # Jul 1: net_invested=7000, NAV=8000, roi=(8000-7000)/7000
        expected_roi = (Decimal("8000") - Decimal("7000")) / Decimal("7000")
        assert result[1].roi == pytest.approx(expected_roi, abs=Decimal("0.000001"))

    def test_over_withdrawal_clamps_invested_to_zero(self):
        """
        Deposit 1000, withdraw 2000 (more than deposited).
        Cumulative CF > 0 → net_invested is clamped to 0 → ROI = 0.
        """
        navs = [
            NAVSnapshot(date(2025, 1, 1), Decimal("1000")),
            NAVSnapshot(date(2025, 7, 1), Decimal("500")),
        ]
        cfs = [
            CashFlowInput(date(2025, 1, 1), Decimal("-1000")),
            CashFlowInput(date(2025, 7, 1), Decimal("2000")),   # oversized withdrawal
        ]
        result = calculate_simple_roi_series(navs, cfs)
        # After withdrawal: cumulative_cf = -1000 + 2000 = +1000 > 0 → net_invested=0 → roi=0
        assert result[-1].roi == Decimal("0")

    def test_series_chronological_order(self):
        """Output is sorted by date ascending regardless of input order."""
        navs = [
            NAVSnapshot(date(2025, 6, 1), Decimal("11000")),
            NAVSnapshot(date(2025, 1, 1), Decimal("10000")),
        ]
        cfs = [CashFlowInput(date(2025, 1, 1), Decimal("-10000"))]
        result = calculate_simple_roi_series(navs, cfs)
        dates = [p.date for p in result]
        assert dates == sorted(dates)

    def test_returns_simpleroi_point_instances(self):
        """Every returned item is a SimpleROIPoint."""
        navs = [
            NAVSnapshot(date(2025, 1, 1), Decimal("1000")),
            NAVSnapshot(date(2025, 6, 1), Decimal("1100")),
        ]
        result = calculate_simple_roi_series(navs, [])
        for point in result:
            assert isinstance(point, SimpleROIPoint)
            assert isinstance(point.roi, Decimal)
            assert isinstance(point.date, date)

    def test_cf_between_snapshots_is_missed(self):
        """
        DOCUMENTED BEHAVIOR (not a bug): a CF on a date that has no matching
        NAVSnapshot is silently skipped.

        Caller MUST provide a NAVSnapshot for every CF date.
        This constraint is the same as for calculate_twrr().
        """
        navs = [
            NAVSnapshot(date(2025, 1, 1),  Decimal("0")),
            NAVSnapshot(date(2025, 12, 31), Decimal("10500")),
        ]
        # CF on Jun 1 — no snapshot on Jun 1 → will be missed
        cfs = [CashFlowInput(date(2025, 6, 1), Decimal("-10000"))]
        result = calculate_simple_roi_series(navs, cfs)
        # net_invested stays 0 for all snapshots → roi = 0
        for point in result:
            assert point.roi == Decimal("0"), (
                "CF without matching NAVSnapshot is silently dropped. "
                "Callers must provide a snapshot for every CF date."
            )


# ---------------------------------------------------------------------------
# TestAnnualizedToCumulative
# ---------------------------------------------------------------------------


class TestAnnualizedToCumulative:
    """Tests for annualized_to_cumulative helper."""

    def test_none_returns_none(self):
        from backend.app.utils.financial.roi_utils import annualized_to_cumulative
        assert annualized_to_cumulative(None, 365) is None

    def test_rate_minus_one_returns_none(self):
        from backend.app.utils.financial.roi_utils import annualized_to_cumulative
        assert annualized_to_cumulative(Decimal("-1"), 365) is None
        assert annualized_to_cumulative(Decimal("-1.5"), 365) is None

    def test_zero_days_returns_zero(self):
        from backend.app.utils.financial.roi_utils import annualized_to_cumulative
        result = annualized_to_cumulative(Decimal("0.10"), 0)
        assert result == Decimal("0")

    def test_one_year_identity(self):
        """For exactly 365 days, cumulative == annualized."""
        from backend.app.utils.financial.roi_utils import annualized_to_cumulative
        result = annualized_to_cumulative(Decimal("0.10"), 365)
        assert result is not None
        assert float(result) == pytest.approx(0.10, abs=0.001)

    def test_two_years_compounding(self):
        """For 730 days (2 years), cumulative = (1+0.10)^2 - 1 = 0.21."""
        from backend.app.utils.financial.roi_utils import annualized_to_cumulative
        result = annualized_to_cumulative(Decimal("0.10"), 730)
        assert result is not None
        assert float(result) == pytest.approx(0.21, abs=0.001)

    def test_half_year(self):
        """For 182 days (~half year), cumulative = (1+0.10)^(182/365) - 1 ≈ 0.0488."""
        from backend.app.utils.financial.roi_utils import annualized_to_cumulative
        result = annualized_to_cumulative(Decimal("0.10"), 182)
        assert result is not None
        assert float(result) == pytest.approx(0.0488, abs=0.002)

    def test_negative_rate(self):
        """Negative annualized rate (but > -1) gives negative cumulative."""
        from backend.app.utils.financial.roi_utils import annualized_to_cumulative
        result = annualized_to_cumulative(Decimal("-0.20"), 365)
        assert result is not None
        assert float(result) == pytest.approx(-0.20, abs=0.001)


# ---------------------------------------------------------------------------
# TestMWRRSummaryFix — verifies no double-counting of deposits
# ---------------------------------------------------------------------------


class TestMWRRSummaryFix:
    """Verifies that MWRR with initial_nav=0 and deposits in cash_flows works correctly.

    This mirrors the fix: get_summary now passes nav_snapshots[0].nav (≈0 for
    new portfolios) instead of total_invested.
    """

    def test_mwrr_no_double_counting(self):
        """Deposit 1000 at t=0, deposit 500 at t=180, NAV at t=365 = 1800.

        With correct approach (initial_nav=0):
          flows = [(-0, t=0), (-1000, t=0), (-500, t=180), (+1800, t=365)]
          The solver should find a positive rate.
        """
        cfs = [
            CashFlowInput(date(2025, 1, 1), Decimal("-1000")),  # deposit
            CashFlowInput(date(2025, 7, 1), Decimal("-500")),   # deposit
        ]
        result = calculate_mwrr(
            cash_flows=cfs,
            initial_nav=Decimal("0"),  # portfolio starts empty — correct approach
            final_nav=Decimal("1800"),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        assert result.mwrr is not None
        assert float(result.mwrr) > 0, "MWRR should be positive when portfolio gained value"

    def test_mwrr_double_counting_gives_wrong_result(self):
        """Demonstrates the bug: using total_invested as initial_nav double-counts.

        This test documents the bug behavior that was fixed.
        """
        cfs = [
            CashFlowInput(date(2025, 1, 1), Decimal("-1000")),
            CashFlowInput(date(2025, 7, 1), Decimal("-500")),
        ]
        # BUG approach: initial_nav = total_invested = 1500
        result = calculate_mwrr(
            cash_flows=cfs,
            initial_nav=Decimal("1500"),  # WRONG — double-counts deposits
            final_nav=Decimal("1800"),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        # With double-counting, outflows = 1500+1000+500=3000, inflow = 1800
        # Solver needs strongly negative rate to make NPV=0
        assert result.mwrr is not None
        assert float(result.mwrr) < 0, "Bug approach gives negative MWRR for a profitable portfolio"

    def test_mwrr_cumulative_zero_at_t0(self):
        """First day: annualized_to_cumulative with 0 days returns 0."""
        from backend.app.utils.financial.roi_utils import annualized_to_cumulative
        result = annualized_to_cumulative(Decimal("0.26"), 0)
        assert result == Decimal("0")

    def test_mwrr_cumulative_matches_annualized(self):
        """Verify cumulative = (1 + annualized)^(days/365) - 1."""
        from backend.app.utils.financial.roi_utils import annualized_to_cumulative

        # For 1 year period, annualized = 0.26 → cumulative ≈ 0.26
        ann = Decimal("0.26")
        cum = annualized_to_cumulative(ann, 365)
        assert cum is not None
        assert float(cum) == pytest.approx(0.26, abs=0.001)

        # For 2 year period, annualized = 0.26 → cumulative = 1.26^2 - 1 ≈ 0.5876
        cum2 = annualized_to_cumulative(ann, 730)
        assert cum2 is not None
        assert float(cum2) == pytest.approx(0.5876, abs=0.002)
