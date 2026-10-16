"""
CP-13a (workstream J, developer's decision P19): the gain that recovers a drawdown gets its home in ``returns.py``.

Module under test: ``backend/app/services/financial_math/returns.py``,
``required_recovery_return(drawdown: float) -> float | None``.

The gain a value needs, from a low, to climb back to the peak it fell from. Today the frontend computes it
(``frontend/src/lib/features/risk/levels/levelHelpers.ts``, ``requiredRecovery``) and the risk series statistics write
it in place (``backend/app/services/risk/metrics.py``, ``drawdown_episodes``). P19 makes it a backend field computed in
the one home of the financial math: the series statistics call this function (pinned in ``test_risk_metrics.py``), and
the frontend reads the published field later (workstream Y).

The contract:

* ``drawdown`` is a peak-relative decline as a ratio, never positive: ``-0.2`` is a value 20 % below its peak;
* the gain is ``-drawdown / (1 + drawdown)``: ``-0.2 → 0.25``, ``-0.5 → 1.0``, ``-0.8 → 4.0``. That form, and not the
  naive ``1 / (1 + drawdown) - 1``, which subtracts two numbers a hair apart and keeps only the first digits of a small
  gain: at ``-1e-12`` the naive form gives ``1.0000889e-12``, the pinned one ``1.000000000001e-12``;
* no drawdown needs no gain: ``0.0`` and ``-0.0`` give ``0.0``, never ``-0.0``. ``-(0.0) / 1.0`` is a negative zero,
  which ``==`` cannot see and a renderer prints as ``-0 %``;
* a total loss, ``drawdown <= -1``, gives ``None``: no finite gain climbs back from nothing. The bound is exact: the
  float just above ``-1`` still has a finite (huge) gain;
* a positive drawdown is a rise and a non-finite one is no measurement: both raise ``ValueError``, ``-inf`` included,
  which is a broken input and not a total loss.

Red until CP-13a lands: the name is imported at module level, so today the whole file fails at collection with an
``ImportError``.

Pure: no database, no server, no network.
"""

from __future__ import annotations

import math

import pytest

from backend.app.services.financial_math.returns import required_recovery_return


@pytest.mark.parametrize(
    ("drawdown", "gain"),
    [
        pytest.param(-0.2, 0.25, id="a-fifth-down-needs-a-quarter-up"),
        pytest.param(-0.5, 1.0, id="half-down-needs-a-doubling"),
        pytest.param(-0.8, 4.0, id="four-fifths-down-needs-four-hundred-percent"),
        pytest.param(-0.999, 999.0, id="a-thousandth-left-needs-a-thousandfold"),
    ],
)
def test_the_gain_climbs_from_the_low_back_to_the_peak(drawdown, gain):
    result = required_recovery_return(drawdown)

    assert isinstance(result, float)
    assert result == pytest.approx(gain, rel=1e-12)
    # The definition read backwards: the low, (1 + drawdown) of the peak, raised by the gain, is the peak again.
    assert (1.0 + drawdown) * (1.0 + result) == pytest.approx(1.0, rel=1e-12)


def test_a_small_drawdown_keeps_every_digit_of_its_gain():
    expected = 1.000000000001e-12
    # The trap is real: the naive form is wrong from the fifth digit on (1.0000889e-12), so the tolerance used below
    # does tell the two forms apart. abs=0 is what keeps it relative: given only rel, pytest.approx keeps its default
    # absolute tolerance of 1e-12, which at this magnitude accepts anything from 0 to 2e-12.
    naive = 1.0 / (1.0 + -1e-12) - 1.0
    assert naive != pytest.approx(expected, rel=1e-12, abs=0)

    assert required_recovery_return(-1e-12) == pytest.approx(expected, rel=1e-12, abs=0)


@pytest.mark.parametrize("drawdown", [pytest.param(0.0, id="zero"), pytest.param(-0.0, id="negative-zero")])
def test_no_drawdown_needs_no_gain_and_never_a_negative_zero(drawdown):
    result = required_recovery_return(drawdown)

    assert isinstance(result, float)
    assert result == 0.0
    # -0.0 == 0.0: only the sign tells them apart.
    assert math.copysign(1.0, result) == 1.0


@pytest.mark.parametrize("drawdown", [pytest.param(-1.0, id="everything-lost"), pytest.param(-1.5, id="more-than-everything")])
def test_a_total_loss_has_no_finite_gain(drawdown):
    assert required_recovery_return(drawdown) is None


def test_the_total_loss_bound_is_exact():
    # The float just above -1 leaves 2**-53 of the peak. Climbing back from that low takes a gain of 2**53 - 1: finite,
    # the largest this function can return, and a number, not None.
    just_short = math.nextafter(-1.0, 0.0)
    assert just_short == -1.0 + 2.0**-53

    assert required_recovery_return(just_short) == pytest.approx(2.0**53 - 1.0, rel=1e-12)


@pytest.mark.parametrize(
    "drawdown",
    [
        pytest.param(0.1, id="a-rise-is-not-a-drawdown"),
        pytest.param(math.ulp(0.0), id="nor-is-the-smallest-rise"),
        pytest.param(math.nan, id="nan"),
        pytest.param(math.inf, id="inf"),
        pytest.param(-math.inf, id="minus-inf-is-a-broken-input-not-a-total-loss"),
    ],
)
def test_a_rise_or_a_non_finite_drawdown_is_refused(drawdown):
    with pytest.raises(ValueError):
        required_recovery_return(drawdown)
