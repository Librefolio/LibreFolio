"""The first-order price change of a bond for a parallel move of its yield: −modified duration × Δy (RN-25).

The rising-rates scenario of an asset's «What if…?» reads it: a BTP with a modified duration of 1.8 years, rates up by
one point, the price falls by about 1.8 %; rates down by one point, it rises by the same. A first-order figure: no
convexity, no coupons received meanwhile.
"""

from __future__ import annotations

import math

import pytest

from backend.app.services.financial_math.bond_duration import duration_price_change


def test_rates_up_one_point_on_a_duration_of_one_point_eight_lose_one_point_eight_percent():
    assert duration_price_change(1.8, 0.01) == pytest.approx(-0.018, abs=1e-15)


def test_rates_down_give_the_opposite_figure():
    for duration in (0.4, 1.8, 7.25):
        for shift in (0.005, 0.01, 0.02):
            assert duration_price_change(duration, -shift) == pytest.approx(-duration_price_change(duration, shift), abs=1e-15)


def test_no_duration_or_no_move_changes_nothing():
    assert duration_price_change(0.0, 0.01) == 0.0
    assert duration_price_change(1.8, 0.0) == 0.0


@pytest.mark.parametrize("duration", [-0.1, math.nan, math.inf])
def test_a_duration_that_is_not_one_is_refused(duration):
    with pytest.raises(ValueError):
        duration_price_change(duration, 0.01)


@pytest.mark.parametrize("shift", [math.nan, math.inf, -math.inf])
def test_a_yield_move_that_is_not_a_number_is_refused(shift):
    with pytest.raises(ValueError):
        duration_price_change(1.8, shift)
