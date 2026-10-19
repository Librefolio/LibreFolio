"""
Pure utility coverage tests for ROI helpers.
"""

import math
from datetime import date
from decimal import Decimal

import pytest

import backend.app.services.financial_math.returns as roi_utils
from backend.app.services.financial_math.returns import NAVSnapshot, annualized_to_cumulative, calculate_mwrr, calculate_mwrr_series


def test_annualized_to_cumulative_negative_days_returns_zero():
    """Non-positive duration returns zero cumulative return."""
    result = annualized_to_cumulative(Decimal("0.10"), -5)

    assert result == Decimal("0")


def test_annualized_to_cumulative_core_branches():
    """Cover common guard and happy-path branches."""
    assert annualized_to_cumulative(None, 365) is None
    assert annualized_to_cumulative(Decimal("-1"), 365) is None
    assert annualized_to_cumulative(Decimal("0.10"), 365) == Decimal("0.100000")


def test_calculate_mwrr_npv_invalid_rate_branch():
    """The XIRR NPV cannot be evaluated where 1 + r ≤ 0: it raises instead of returning a number,
    while a valid rate gives a finite NPV; a real solve of 1000 → 1100 over one year is 10 %."""
    flows = [(0.0, -1000.0), (1.0, 1100.0)]

    for invalid_rate in (-1.1, -1.0):
        with pytest.raises(OverflowError):
            roi_utils._xirr_npv(flows, invalid_rate)
        with pytest.raises(OverflowError):
            roi_utils._xirr_npv_slope(flows, invalid_rate)
    assert math.isfinite(roi_utils._xirr_npv(flows, 0.1))
    assert roi_utils._xirr_npv(flows, 0.1) == pytest.approx(0.0, abs=1e-6)

    result = calculate_mwrr(
        cash_flows=[],
        initial_nav=Decimal("1000"),
        final_nav=Decimal("1100"),
        start_date=date(2025, 1, 1),
        end_date=date(2026, 1, 1),
    )

    assert result.mwrr == Decimal("0.100000")


def test_calculate_mwrr_zero_day_returns_none():
    """Zero-day period has no meaningful annualized result."""
    result = calculate_mwrr(
        cash_flows=[],
        initial_nav=Decimal("1000"),
        final_nav=Decimal("1000"),
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 1),
    )

    assert result.mwrr is None


def test_calculate_mwrr_includes_intermediate_cash_flow(monkeypatch):
    """Intermediate cash flows are part of the flows the solver gets, in years (days / 365)."""
    calls = []

    def fake_solve_xirr(flows, x0):
        calls.append((list(flows), x0))
        return 0.15

    monkeypatch.setattr(roi_utils, "_solve_xirr", fake_solve_xirr)

    result = calculate_mwrr(
        cash_flows=[roi_utils.CashFlowInput(date(2025, 7, 1), Decimal("-100"))],
        initial_nav=Decimal("1000"),
        final_nav=Decimal("1200"),
        start_date=date(2025, 1, 1),
        end_date=date(2026, 1, 1),
    )

    assert len(calls) == 1
    flows, x0 = calls[0]
    assert x0 == 0.1
    # 2025-07-01 is day 181 of the year.
    assert sorted(flows) == sorted([(0.0, -1000.0), (1.0, 1200.0), (181 / 365, -100.0)])
    assert result.mwrr == Decimal("0.150000")


def test_calculate_mwrr_series_keeps_an_extreme_rate_as_the_single_solve_does(monkeypatch):
    """MF-K1, one root policy: a series point is solved once, from 0.1, and the rate the solver returns
    is the point's rate, even an extreme one, as in ``calculate_mwrr``. The warm start's retry from the
    default guess, which preferred a smaller |r| (here the 0.2 a second call would give), is gone."""
    x0_values = []
    returned_rates = iter([3.0, 0.2])

    def fake_solve_xirr(flows, x0):
        x0_values.append(x0)
        return next(returned_rates)

    monkeypatch.setattr(roi_utils, "_solve_xirr", fake_solve_xirr)

    series = calculate_mwrr_series(
        [
            NAVSnapshot(date(2025, 1, 1), Decimal("1000")),
            NAVSnapshot(date(2026, 1, 1), Decimal("1200")),
        ],
        [],
    )

    assert len(series) == 1
    assert series[0].mwrr == Decimal("3.000000")
    assert x0_values == [0.1]


def test_calculate_mwrr_series_short_input_returns_empty():
    """Series needs at least 2 snapshots."""
    assert calculate_mwrr_series([], []) == []
    assert calculate_mwrr_series([NAVSnapshot(date(2025, 1, 1), Decimal("1000"))], []) == []


def test_calculate_mwrr_series_includes_intermediate_cash_flows(monkeypatch):
    """Later snapshots include mid-period cash flows in the flows the solver gets; on its own day a
    flow joins that snapshot's final value."""
    calls = []

    def fake_newton_xirr(flows, x0, scale):
        calls.append((list(flows), x0))
        return 0.1 if len(calls) == 1 else 0.15

    # P1: a series point after the first may solve through the Newton step directly, not through _solve_xirr.
    monkeypatch.setattr(roi_utils, "_newton_xirr", fake_newton_xirr)

    series = calculate_mwrr_series(
        [
            NAVSnapshot(date(2025, 1, 1), Decimal("1000")),
            NAVSnapshot(date(2025, 7, 1), Decimal("1100")),
            NAVSnapshot(date(2026, 1, 1), Decimal("1250")),
        ],
        [roi_utils.CashFlowInput(date(2025, 7, 1), Decimal("-100"))],
    )

    assert [point.mwrr for point in series] == [Decimal("0.100000"), Decimal("0.150000")]
    assert [x0 for _flows, x0 in calls] == [0.1, 0.1]
    # 2025-07-01 is day 181: the last day of the first window, strictly inside the second.
    assert sorted(calls[0][0]) == sorted([(0.0, -1000.0), (181 / 365, 1100.0 - 100.0)])
    assert sorted(calls[1][0]) == sorted([(0.0, -1000.0), (1.0, 1250.0), (181 / 365, -100.0)])


def test_calculate_mwrr_series_starts_every_point_from_the_default_guess(monkeypatch):
    """MF-K1, one root policy: every point starts from 0.1, never from the previous point's rate (the
    warm start, removed), and keeps the rate its one solve returns: 3.0, then 0.3, then 0.2."""
    x0_values = []
    returned_rates = iter([3.0, 0.3, 0.2])

    def fake_newton_xirr(flows, x0, scale):
        x0_values.append(x0)
        return next(returned_rates, 9.9)

    # P1: a series point after the first may solve through the Newton step directly, not through _solve_xirr.
    monkeypatch.setattr(roi_utils, "_newton_xirr", fake_newton_xirr)

    series = calculate_mwrr_series(
        [
            NAVSnapshot(date(2025, 1, 1), Decimal("1000")),
            NAVSnapshot(date(2026, 1, 1), Decimal("1200")),
            NAVSnapshot(date(2027, 1, 1), Decimal("1300")),
            NAVSnapshot(date(2028, 1, 1), Decimal("1400")),
        ],
        [],
    )

    assert [point.mwrr for point in series] == [Decimal("3.000000"), Decimal("0.300000"), Decimal("0.200000")]
    assert x0_values == [0.1, 0.1, 0.1]
