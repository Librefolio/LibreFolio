"""
Pure utility coverage tests for ROI helpers.
"""

from datetime import date
from decimal import Decimal

import pytest

import backend.app.utils.financial.roi_utils as roi_utils
from backend.app.utils.financial.roi_utils import NAVSnapshot, annualized_to_cumulative, calculate_mwrr, calculate_mwrr_series


def test_annualized_to_cumulative_negative_days_returns_zero():
    """Non-positive duration returns zero cumulative return."""
    result = annualized_to_cumulative(Decimal("0.10"), -5)

    assert result == Decimal("0")


def test_annualized_to_cumulative_core_branches():
    """Cover common guard and happy-path branches."""
    assert annualized_to_cumulative(None, 365) is None
    assert annualized_to_cumulative(Decimal("-1"), 365) is None
    assert annualized_to_cumulative(Decimal("0.10"), 365) == Decimal("0.100000")


def test_calculate_mwrr_npv_invalid_rate_branch(monkeypatch):
    """Mock solver to exercise internal NPV guard for invalid rates."""

    def fake_newton(npv, x0, tol, maxiter):
        assert npv(-1.1) == float("inf")
        assert npv(0.1) == pytest.approx(0.0, abs=1e-6)
        return 0.1

    monkeypatch.setattr(roi_utils, "scipy_newton", fake_newton)

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
    """Intermediate cash flows must be part of NPV function."""

    def fake_newton(npv, x0, tol, maxiter):
        assert npv(-1.1) == float("inf")
        assert npv(0.1) != float("inf")
        return 0.15

    monkeypatch.setattr(roi_utils, "scipy_newton", fake_newton)

    result = calculate_mwrr(
        cash_flows=[roi_utils.CashFlowInput(date(2025, 7, 1), Decimal("-100"))],
        initial_nav=Decimal("1000"),
        final_nav=Decimal("1200"),
        start_date=date(2025, 1, 1),
        end_date=date(2026, 1, 1),
    )

    assert result.mwrr == Decimal("0.150000")


def test_calculate_mwrr_series_warm_start_extreme_falls_back(monkeypatch):
    """Warm-start branch retries from default guess when first rate is extreme."""
    call_count = {"value": 0}

    def fake_newton(npv, x0, tol, maxiter):
        call_count["value"] += 1
        assert npv(-1.1) == float("inf")
        if call_count["value"] == 1:
            return 3.0
        return 0.2

    monkeypatch.setattr(roi_utils, "scipy_newton", fake_newton)

    series = calculate_mwrr_series(
        [
            NAVSnapshot(date(2025, 1, 1), Decimal("1000")),
            NAVSnapshot(date(2026, 1, 1), Decimal("1200")),
        ],
        [],
        use_warm_start=True,
    )

    assert len(series) == 1
    assert series[0].mwrr == Decimal("0.200000")
    assert call_count["value"] == 2


def test_calculate_mwrr_series_short_input_returns_empty():
    """Series needs at least 2 snapshots."""
    assert calculate_mwrr_series([], []) == []
    assert calculate_mwrr_series([NAVSnapshot(date(2025, 1, 1), Decimal("1000"))], []) == []


def test_calculate_mwrr_series_includes_intermediate_cash_flows(monkeypatch):
    """Later snapshots include mid-period cash flows in series NPV."""
    x0_values = []

    def fake_newton(npv, x0, tol, maxiter):
        x0_values.append(x0)
        assert npv(-1.1) == float("inf")
        return 0.1 if len(x0_values) == 1 else 0.15

    monkeypatch.setattr(roi_utils, "scipy_newton", fake_newton)

    series = calculate_mwrr_series(
        [
            NAVSnapshot(date(2025, 1, 1), Decimal("1000")),
            NAVSnapshot(date(2025, 7, 1), Decimal("1100")),
            NAVSnapshot(date(2026, 1, 1), Decimal("1250")),
        ],
        [roi_utils.CashFlowInput(date(2025, 7, 1), Decimal("-100"))],
        use_warm_start=False,
    )

    assert [point.mwrr for point in series] == [Decimal("0.100000"), Decimal("0.150000")]
    assert x0_values == [0.1, 0.1]


def test_calculate_mwrr_series_extreme_retry_resets_prev_guess(monkeypatch):
    """If retry still extreme, next point must restart from default guess."""
    x0_values = []
    returned_rates = iter([3.0, 2.5, 0.2])

    def fake_newton(npv, x0, tol, maxiter):
        x0_values.append(x0)
        assert npv(-1.1) == float("inf")
        return next(returned_rates)

    monkeypatch.setattr(roi_utils, "scipy_newton", fake_newton)

    series = calculate_mwrr_series(
        [
            NAVSnapshot(date(2025, 1, 1), Decimal("1000")),
            NAVSnapshot(date(2026, 1, 1), Decimal("1200")),
            NAVSnapshot(date(2027, 1, 1), Decimal("1300")),
        ],
        [],
        use_warm_start=True,
    )

    assert [point.mwrr for point in series] == [Decimal("2.500000"), Decimal("0.200000")]
    assert x0_values == [0.1, 0.1, 0.1]
