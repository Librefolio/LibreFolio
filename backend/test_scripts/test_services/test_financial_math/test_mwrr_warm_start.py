"""
P1 (workstream MF, N74, «formule veloci»): the Dashboard's MWRR line starts each point's XIRR from the previous point's
rate — and keeps, point by point, exactly the rate the cold solve of today gives. «È imperativo non sbagliare i calcoli,
veloci sì, ma precisi.»

Module under test: ``backend/app/services/financial_math/returns.py`` — ``_mwrr_solve``, the solve of a series point,
through ``period_mwrr_series`` (the line) and ``calculate_mwrr_series``; and its helpers ``_flow_sign_changes``,
``_changes_sign_at`` and ``_bracketed_xirr_at``.

Today (HEAD ff9930b26) every point is ``_solve_xirr(flows, 0.1)``: Newton from 0.1, kept only where the NPV vanishes;
otherwise a scan of the 801 grid points (1 + r from 1e-12 to 1e4), Brent in every interval where the NPV changes sign or
an exact zero on a grid point, and the verified root nearest 0.1. On a portfolio a century long Newton from 0.1 overflows
and the scan runs at almost every point: about 550 NPV evaluations a point (20 s for the 46 000 points of a 1900 history).

P1, as built. A point after the first solved one, whose flows change sign exactly once and whose opening value is not 0.0
as a float, first runs Newton from 0.1, as today. Only where that fails, Newton from the previous point's rate says
where the one true root is — on the grid's range, the NPV changing sign across it — and the answer is the one the scan
gives in that grid interval, by its own steps and tests (``_bracketed_xirr_at``: an exact zero on a grid point, or the
same Brent call with the same verification). Wherever that interval does not give a root, the whole scan runs, as
today. A solve that cannot take the shortcut (the card, a series' first point, flows with several sign changes or none,
an opening value of 0.0) is ``_solve_xirr`` itself.

Sections:

1. Units: ``_flow_sign_changes`` (zeros aside, in time order), ``_changes_sign_at`` (a true root; not a flat NPV near
   zero; not where the NPV cannot be evaluated), ``_bracketed_xirr_at`` (the scan's root bit for bit, its exact zero,
   None wherever the scan finds nothing in the interval).
2. The shortcut is taken, and only where the contract allows it (structural). A recorder wraps ``_solve_xirr``,
   ``_newton_xirr``, ``_bracketed_xirr`` and ``_bracketed_xirr_at``; every solved point's calls must be exactly the
   contract's, the warm start must be the previous point's rate bit for bit, and every rate kept must be the cold
   solve's bit for bit. Red on HEAD: three of the four functions do not exist there (AttributeError), and HEAD starts
   every point from 0.1.
3. Cost: on a 125-year history and on a value constant since 1900, at most ``COST_BOUND`` NPV evaluations a point.
   Red on HEAD.
4. Parity with the cold solve, on every input of the existing MWRR test files, the database scenarios of
   ``test_portfolio_mwrr_card_and_line.py`` rebuilt as plain inputs, and the families found while building P1. Green
   on HEAD and on P1: that is the guarantee.
5. Why each guard: on the data where it decides, a warm start answers something else than today's solve.
6. HEAD behaviour preserved: two weaknesses of today's solve that P1 must reproduce, not fix (a possible separate lot).

The parity oracle. A point of HEAD's series is, by its code, the card on its prefix: ``_mwrr_point`` from the first
snapshot, solved cold. Here the oracle is ``period_mwrr`` (the line) and ``calculate_mwrr`` (the plain series) from the
first snapshot to each point, which P1 still solves through ``_solve_xirr`` from 0.1. Before this file was committed the
oracle was compared with HEAD's ``returns.py`` (loaded from git into its own module) on every case below: identical, by
``str()`` of every point. Rates are compared by ``str()``, the exponent included; None with None.

Measured in a harness (plain Python, outside the repository) before writing this file:

* NPV evaluations a point, period line: 125 years, 3 % a year (the case below): HEAD 549.7, P1 22.6; a value constant
  since 1900: HEAD 569.6, P1 13.1.
* The first P1 design (warm ``_solve_xirr`` before the cold one, only the grid range checked) on the 1900 case of
  section 5: 379.189396 — an exact zero of the grid, 10^(129/50) − 1 — on 380 of 399 points where HEAD differs. The
  second (cold Newton first, then the warm root itself as the answer) differed from HEAD on 212 of 3000 ill-conditioned
  series (section 6) and at the grid's overflow edge (section 5): the warm Newton root passed the verification where
  the scan's Brent root, 6e-16 away, did not. As built: 0 differences on all of them.

Isolation: pure functions, no database, no server, no network; ``monkeypatch`` restores every wrapped function.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import pytest
from scipy.optimize import brentq

from backend.app.services.financial_math import returns
from backend.app.services.financial_math.returns import CashFlowInput, MWRRPoint, NAVSnapshot
from backend.test_scripts.test_services.test_financial_math import test_mwrr_verified_root as verified_root
from backend.test_scripts.test_services.test_financial_math import test_period_mwrr as period_cases

# Today's starting guess for every MWRR solve.
COLD_GUESS = 0.1
# NPV evaluations a point allowed on the long histories (P1 measured 22.6 and 13.1; HEAD 549.7 and 569.6).
COST_BOUND = 40
CENT = Decimal("0.01")

Case = tuple[list[NAVSnapshot], list[CashFlowInput]]


# =============================================================================
# Inputs
# =============================================================================


def _pairs(text: str) -> list[tuple[date, Decimal]]:
    words = text.split()
    return [(date.fromisoformat(day), Decimal(value)) for day, value in zip(words[::2], words[1::2], strict=True)]


def _case(navs_text: str, flows_text: str) -> Case:
    return [NAVSnapshot(day, nav) for day, nav in _pairs(navs_text)], [CashFlowInput(day, amount) for day, amount in _pairs(flows_text)]


# The long history: 1000 on 1 January 1900, a snapshot every 30 days for 125 years (1521 points), deposits of 500, 2000
# and 5000 after 10, 35 and 70 years, 3000 taken out after 100 years, and after 110 years a deposit and a withdrawal of
# 700 on one day (their sum, 0, is a zero amount in the solve). The value grows ``annual`` a year with a slow wobble; one
# snapshot (the 600th, about 49 years in) reads 0, as a gap in the data would: the line has no rate there, the plain
# series none either (every flow up to it is a deposit). Newton from 0.1 overflows on most of these points.
LONG_GLITCH = 600


def _long_history(annual: float) -> Case:
    start = date(1900, 1, 1)

    def after(years: float) -> date:
        return start + timedelta(days=round(years * 365.25))

    flows = [
        CashFlowInput(after(10), Decimal("-500")),
        CashFlowInput(after(35), Decimal("-2000")),
        CashFlowInput(after(70), Decimal("-5000")),
        CashFlowInput(after(100), Decimal("3000")),
        CashFlowInput(after(110), Decimal("-700")),
        CashFlowInput(after(110), Decimal("700")),
    ]
    navs = [NAVSnapshot(start, Decimal("1000"))]
    value = 1000.0
    for step in range(1, 1522):
        day, previous_day = start + timedelta(days=30 * step), start + timedelta(days=30 * (step - 1))
        years, previous_years = 30 * step / 365.25, 30 * (step - 1) / 365.25
        value *= (1 + annual) ** (30 / 365.25) * (1 + 0.02 * math.sin(years / 3)) / (1 + 0.02 * math.sin(previous_years / 3))
        value -= float(sum((flow.amount for flow in flows if previous_day < flow.date <= day), Decimal("0")))
        navs.append(NAVSnapshot(day, Decimal("0") if step == LONG_GLITCH else Decimal(repr(value)).quantize(CENT)))
    return navs, flows


def _ten_years() -> Case:
    """10 000 on 1 January 2015, 300 deposited on the 15th of every month, 2000 taken out in March 2018 and 5000 in
    June 2023; 0.7 % a month, then six months of −6 % (mid 2019, a third of the value gone) and a year of +2 %."""
    start = date(2015, 1, 1)
    navs, flows, value = [NAVSnapshot(start, Decimal("10000"))], [CashFlowInput(start, Decimal("-10000"))], 10000.0
    for month in range(1, 121):
        flow_day = date(2015 + (month - 1) // 12, (month - 1) % 12 + 1, 15)
        day = date(2015 + month // 12, month % 12 + 1, 1)
        value *= 1 + (-0.06 if 54 <= month < 60 else 0.02 if 60 <= month < 72 else 0.007)
        amount = Decimal("2000") if month == 39 else Decimal("5000") if month == 102 else Decimal("-300")
        flows.append(CashFlowInput(flow_day, amount))
        value -= float(amount)
        navs.append(NAVSnapshot(day, Decimal(repr(value)).quantize(CENT)))
    return navs, flows


def _constant_value() -> Case:
    """1000 on 1 January 1900 and every 30 days after it for 125 years: the rate is exactly 0, the grid point 10^0 − 1,
    where the NPV is exactly 0.0 (the developer's EUR cash, constant since 1900, on a copy of the database)."""
    start = date(1900, 1, 1)
    return [NAVSnapshot(start + timedelta(days=30 * step), Decimal("1000")) for step in range(1522)], [CashFlowInput(start, Decimal("-1000"))]


# Two roots (plain series only: the line has no rate there, more came out than went in). 2500 taken out of 1020 on 29
# June 2020, the value 1.00 from then on, 1300 put in on 26 December. The flows of 26 December change sign twice; the
# NPV has a root at −0.461894, the one nearest 0.1, and one at 2.158683, near the previous point's rate.
MULTI_ROOT = _case(
    """
    2020-01-01 1000  2020-01-31 1004.02  2020-03-01 1008.05  2020-03-31 1012.10  2020-04-30 1016.17  2020-05-30 1020.25
    2020-06-29 1.00  2020-07-29 1.00  2020-08-28 1.00  2020-09-27 1.00  2020-10-27 1.00  2020-11-26 1.00  2020-12-26 1.00
    2021-01-25 1.00  2021-02-24 1.00  2021-03-26 1.00  2021-04-25 1.00  2021-05-25 1.00  2021-06-24 1.00
    """,
    "2020-06-29 2500  2020-12-26 -1300",
)
MULTI_ROOT_DAY = date(2020, 12, 26)

# About 3 % a day: rates of thousands of times a year. On 18 January 2020 Newton from 0.1 fails, and Newton from the
# previous point's rate finds 49991.496589, beyond the grid's last rate (9999): the scan never finds it.
OUT_OF_GRID = _case(
    """
    2020-01-01 1000  2020-01-02 1032.97  2020-01-03 1063.17  2020-01-04 1092.11  2020-01-05 1126.50  2020-01-06 1162.99
    2020-01-07 1195.44  2020-01-08 1229.08  2020-01-09 1269.12  2020-01-10 1308.71  2020-01-11 1344.20  2020-01-12 1383.92
    2020-01-13 1429.59  2020-01-14 1472.01  2020-01-15 1511.88  2020-01-16 1558.87  2020-01-17 1609.74  2020-01-18 1655.21
    2020-01-19 1701.25
    """,
    "2020-01-01 -1000",
)
OUT_OF_GRID_DAY = date(2020, 1, 18)

# The developer's 1900 case, in small: the period opens on 1 January 1900 at value 0 (a BUY of 1900 with no value yet),
# and every flow comes 125.5 years later. From a rate of 379.189396 (the grid point 10^(129/50) − 1) up, every NPV
# term underflows: the NPV is exactly 0.0 there, and the scan keeps those grid points as roots. Today's own answer on
# 4-10 July is that grid point (kept: it is the cold solve's, see section 6); the first P1 design, starting from the
# previous rate, stayed on it to the end.
FALSE_ROOT_1900 = _case(
    """
    1900-01-01 0  2025-07-01 10000.00  2025-07-02 10000.00  2025-07-03 10143.83  2025-07-04 10399.90  2025-07-05 10711.12
    2025-07-06 11003.30  2025-07-07 11200.86  2025-07-08 11248.28  2025-07-09 11129.91  2025-07-10 10877.21
    2025-07-11 10558.23  2025-07-12 10254.49  2025-07-13 10037.44  2025-07-14 9953.30  2025-07-15 10017.54
    2025-07-16 10214.98
    """,
    "2025-07-01 -10000",
)
FALSE_ROOT_DAY = date(2025, 7, 11)

# The grid's overflow edge: 1000 on 1 January 1850 and, 150 years later, a value of about 1e-303. The root (−0.990880)
# lies between the point where the NPV overflows and the first grid point where it does not: the scan cannot bracket
# it, today's answer is None, and Newton from the previous day's rate finds it.
OVERFLOW_EDGE = _case("1850-01-01 1000  1999-11-25 1.0131043591955372E-303  1999-11-26 9.998500111744283E-304", "1850-01-01 -1000")

# Ill-conditioned (HEAD weakness 2, section 6): 1000 in 1700, 10 000 deposited 240 years later, then about −8.75 % a
# year. The NPV's terms (~1e12) cancel at the root, and whether a root passes |NPV| ≤ 1e-7 · Σ|amounts| depends on its
# last bits: on several points Newton's root passes and the scan's Brent root, a few ulps away, does not.
ILL_CONDITIONED = _case(
    """
    1700-01-01 1000  1939-12-05 9926.5250  1940-01-04 9853.8303  1940-02-03 9777.4932  1940-03-04 9698.1487
    1940-04-03 9622.3652  1940-05-03 9555.5923  1940-06-02 9494.6690  1940-07-02 9429.1016  1940-08-01 9351.3277
    1940-08-31 9265.9257  1940-09-30 9187.2307
    """,
    "1939-11-05 -10000",
)

# Product underflow (HEAD weakness 1, section 6): an opening value of 1e-300 in year 1 and 1000 deposited 6000 years
# later, the rate drifting up by 0.00002 a day across the grid point 10^(1/50) − 1 = 0.047129. Past it the NPVs at the
# two grid points around the root are about 1e-121 and −1e-239: their product underflows to −0.0, the scan's
# «previous_npv * npv < 0.0» is False, and today's answer is None, though Newton finds the root and the NPV changes
# sign across it.
PRODUCT_UNDERFLOW = _case(
    """
    0001-01-01 1E-300  6001-08-09 1028.0699318628197  6001-08-10 1028.211196903087  6001-08-11 1028.352588762274
    6001-08-12 1028.4941074842814  6001-08-13 1028.6357531130554  6001-08-14 1028.7775256925868  6001-08-15 1028.919425266911
    6001-08-16 1029.061451880108  6001-08-17 1029.203605576303  6001-08-18 1029.3458863996657  6001-08-19 1029.48829439441
    6001-08-20 1029.6308296047964  6001-08-21 1029.7734920751282  6001-08-22 1029.9162818497553  6001-08-23 1030.059198973071
    6001-08-24 1030.2022434895143  6001-08-25 1030.34541544357  6001-08-26 1030.4887148797657  6001-08-27 1030.632141842676
    6001-08-28 1030.7756963769198
    """,
    "6001-01-01 -1000",
)

# The NPV vanishing below the step of _changes_sign_at: an opening value of 1e-300 in 1800 and 1000 deposited 200 years
# later, the rate rising from 300 % to 900 % a year. From about 500 % the NPV's terms are below 1e-150 at the root: the
# NPVs at ±1e-9 of Newton's root multiply to 0.0, _changes_sign_at says no, and the scan runs (and finds nothing).
VANISHING_NPV = _case(
    """
    1800-01-01 1E-300  1999-12-14 1120.6871257054333  2000-01-13 1268.5185148667636  2000-02-12 1448.992372290727
    2000-03-13 1669.0702314314922  2000-04-12 1937.5278197566183  2000-05-12 2265.4112544563445  2000-06-11 2666.6259146185257
    2000-07-11 3158.694497843209  2000-08-10 3763.7323608870397  2000-09-09 4509.703191118968  2000-10-09 5432.0375171519345
    2000-11-08 6575.722042466516  2000-12-08 7998.001245202878  2001-01-07 9771.876737963725  2001-02-06 11990.647988139763
    2001-03-08 14773.814777354883  2001-04-07 18274.7633878285  2001-05-07 22690.793177200714  2001-06-06 28276.21896246013
    2001-07-06 35359.52224950765  2001-08-05 44365.84064169135  2001-09-04 55846.50637702619  2001-10-04 70517.90772005678
    2001-11-03 89312.69915000351  2001-12-03 113447.39305714943
    """,
    "1999-11-14 -1000",
)


# =============================================================================
# The cold solve, the oracle
# =============================================================================


def _by_date(navs: Sequence[NAVSnapshot]) -> list[NAVSnapshot]:
    return sorted(navs, key=lambda snapshot: snapshot.date)


def _cold_line(navs: Sequence[NAVSnapshot], flows: Sequence[CashFlowInput]) -> list[MWRRPoint]:
    """Today's line: the card of the period from the first snapshot to each later one, solved cold."""
    ordered = _by_date(navs)
    if len(ordered) < 2 or not flows:
        return []
    return [returns.period_mwrr(ordered[:1], flows, snapshot.date, snapshot.nav) for snapshot in ordered[1:]]


def _cold_series(navs: Sequence[NAVSnapshot], flows: Sequence[CashFlowInput]) -> list[MWRRPoint]:
    """Today's plain series: ``calculate_mwrr`` from the first snapshot to each later one, solved cold."""
    ordered = _by_date(navs)
    if len(ordered) < 2:
        return []
    first = ordered[0]
    return [returns.calculate_mwrr(list(flows), first.nav, snapshot.nav, first.date, snapshot.date) for snapshot in ordered[1:]]


def _shown(points: Sequence[MWRRPoint]) -> list[tuple[date, str]]:
    return [(point.date, str(point.mwrr)) for point in points]


def _assert_same(actual: Sequence[MWRRPoint], expected: Sequence[MWRRPoint], what: str) -> None:
    got, wanted = _shown(actual), _shown(expected)
    assert [day for day, _rate in got] == [day for day, _rate in wanted], f"{what}: not the same points"
    mismatches = [f"{day}: {rate} instead of {cold}" for (day, rate), (_day, cold) in zip(got, wanted, strict=True) if rate != cold]
    assert not mismatches, f"{what}: {len(mismatches)} of {len(got)} points differ from the cold solve: {mismatches[:5]}"


def _assert_parity(case: Case) -> None:
    navs, flows = case
    _assert_same(returns.period_mwrr_series(navs, flows), _cold_line(navs, flows), "the line")
    _assert_same(returns.calculate_mwrr_series(navs, flows), _cold_series(navs, flows), "the plain series")


def _point_flows(case: Case, end_date: date) -> list[tuple[float, float]]:
    """The ``(years, amount)`` flows of the point ending on ``end_date``, as the module builds them."""
    navs, flows = case
    ordered = _by_date(navs)
    first, end = ordered[0], next(snapshot for snapshot in ordered if snapshot.date == end_date)
    by_date: dict[date, Decimal] = {}
    for flow in flows:
        by_date[flow.date] = by_date.get(flow.date, Decimal("0")) + flow.amount
    total = (end.date - first.date).days
    year_flows = [(0.0, -float(first.nav)), (total / 365.0, float(end.nav + by_date.get(end.date, Decimal("0"))))]
    year_flows += [((day - first.date).days / 365.0, float(amount)) for day, amount in by_date.items() if 0 < (day - first.date).days < total]
    return year_flows


def _previous_cold_rate(case: Case, end_date: date) -> float:
    """The raw rate today's solve gives the last point before ``end_date`` that has one: a warm start's starting point."""
    for snapshot in reversed([snapshot for snapshot in _by_date(case[0])[1:] if snapshot.date < end_date]):
        rate = returns._solve_xirr(_point_flows(case, snapshot.date), COLD_GUESS)
        if rate is not None:
            return rate
    raise AssertionError(f"no point before {end_date} has a rate")


def _scale(year_flows: Sequence[tuple[float, float]]) -> float:
    return sum(abs(amount) for _years, amount in year_flows) or 1.0


def _sign_changes(year_flows: Sequence[tuple[float, float]]) -> int:
    """The test's own count: the amounts in time order, zeros dropped, and how often the sign flips."""
    amounts = [amount for _years, amount in sorted(year_flows, key=lambda flow: flow[0]) if amount != 0.0]
    return sum(1 for left, right in zip(amounts, amounts[1:], strict=False) if (left > 0) != (right > 0))


def _npv_changes_sign(year_flows: Sequence[tuple[float, float]], rate: float) -> bool:
    """The test's own check, with HEAD's NPV only: finite NPVs of opposite signs 1e-9 (relative) on either side of ``rate``."""
    step = 1e-9 * max(1.0, abs(rate))
    try:
        below, above = returns._xirr_npv(year_flows, rate - step), returns._xirr_npv(year_flows, rate + step)
    except OverflowError:
        return False
    return math.isfinite(below) and math.isfinite(above) and below * above < 0.0


def _grid_interval(rate: float) -> tuple[float, float]:
    """The two grid rates around ``rate``, as the scan computes them."""
    index = next(index for index, base in enumerate(returns._XIRR_GRID) if base >= 1.0 + rate)
    return returns._XIRR_GRID[index - 1] - 1.0, returns._XIRR_GRID[index] - 1.0


def _scan_brent(year_flows: Sequence[tuple[float, float]], low: float, high: float) -> float:
    """The scan's Brent call on one grid interval."""
    return brentq(lambda rate: returns._xirr_npv(year_flows, rate), low, high, xtol=1e-14, maxiter=200)


# =============================================================================
# 1. Units
# =============================================================================


class TestFlowSignChanges:
    """``_flow_sign_changes``: Descartes' count on the amounts in time order, zero amounts aside."""

    @pytest.mark.parametrize(
        ("year_flows", "changes"),
        [
            ([(0.0, -1000.0), (0.5, -500.0), (1.0, -200.0)], 0),
            ([(0.0, 1000.0), (1.0, 50.0)], 0),
            ([(0.0, -1000.0), (0.5, -500.0), (1.0, 1600.0)], 1),
            ([(0.0, -100.0), (1.0, 225.0), (2.0, -123.5)], 2),
            ([(0.0, -1000.0), (0.5, 2500.0), (1.0, -1300.0), (1.5, 1.0)], 3),
        ],
        ids=["none-all-out", "none-all-in", "one", "two", "three"],
    )
    def test_counts(self, year_flows, changes):
        assert returns._flow_sign_changes(year_flows) == changes

    def test_zero_amounts_are_ignored(self):
        """A date whose flows sum to 0, an opening value of 0, a final value of 0: none is a sign."""
        assert returns._flow_sign_changes([(0.0, -1000.0), (0.5, 400.0), (0.7, 0.0), (1.0, 900.0)]) == 1
        assert returns._flow_sign_changes([(0.0, -0.0), (125.5, -10000.0), (126.0, 12000.0)]) == 1
        assert returns._flow_sign_changes([(0.0, -1000.0), (1.0, 0.0)]) == 0
        assert returns._flow_sign_changes([(0.0, 0.0), (1.0, 0.0)]) == 0

    def test_the_amounts_are_read_in_time_order(self):
        """The module lists the final value second: in that order these flows change sign twice, in time order once."""
        year_flows = [(0.0, -1000.0), (2.0, 1500.0), (1.0, -500.0)]

        assert _sign_changes(year_flows) == 1
        assert returns._flow_sign_changes(year_flows) == 1
        assert returns._flow_sign_changes([(0.0, -1.0), (3.0, 1.0), (1.0, 1.0), (2.0, -1.0)]) == 3


class TestChangesSignAt:
    """``_changes_sign_at``: whether the NPV truly changes sign across a rate."""

    def test_a_true_root(self):
        year_flows = [(0.0, -1000.0), (1.0, 1100.0)]
        root = returns._solve_xirr(year_flows, COLD_GUESS)

        assert root is not None and abs(root - 0.1) < 1e-12
        assert returns._changes_sign_at(year_flows, root)

    def test_a_flat_npv_near_zero_is_not_a_root(self):
        """1 in, 1e27 out 125 years later: at 379.19 a year the NPV is about −1, which the verification accepts (1e-7 of
        Σ|amounts| is 1e20), and it does not change sign there."""
        year_flows = [(0.0, -1.0), (125.0, 1e27)]
        rate = returns._XIRR_GRID[729] - 1.0

        assert abs(returns._xirr_npv(year_flows, rate) + 1.0) < 1e-9
        assert returns._is_xirr_root(year_flows, rate, _scale(year_flows))
        assert not returns._changes_sign_at(year_flows, rate)

    def test_an_npv_vanishing_by_underflow_is_not_a_root(self):
        """An opening value of 0 and every flow 125.5 years later: the NPV is exactly 0.0 around 379.19, no sign change."""
        year_flows = [(0.0, -0.0), (125.5, -10000.0), (126.0, 12000.0)]
        rate = returns._XIRR_GRID[729] - 1.0

        assert returns._xirr_npv(year_flows, rate) == 0.0
        assert returns._is_xirr_root(year_flows, rate, _scale(year_flows))
        assert not returns._changes_sign_at(year_flows, rate)

    @pytest.mark.parametrize("rate", [-1.0, -0.9999, -0.999999999999], ids=["base-zero", "overflow", "base-1e-12"])
    def test_where_the_npv_cannot_be_evaluated(self, rate):
        """1 + r ≤ 0 below the rate, or the discount factor overflowing over 150 years."""
        assert not returns._changes_sign_at([(0.0, -1000.0), (150.0, 1e-303)], rate)


class TestBracketedXirrAt:
    """``_bracketed_xirr_at``: what the scan finds in the grid interval holding a rate, or None."""

    def test_the_scan_s_root_bit_for_bit(self):
        """Inside the interval of the root the answer is the scan's own Brent root, whatever rate of it is given."""
        navs, flows = _long_history(0.03)
        year_flows = _point_flows((navs, flows), navs[1200].date)
        scale = _scale(year_flows)
        scanned = returns._bracketed_xirr(year_flows, COLD_GUESS, scale)
        low, high = _grid_interval(scanned)

        assert scanned is not None and returns._newton_xirr(year_flows, COLD_GUESS, scale) is None, "precondition: today's solve scans"
        for rate in (scanned, low + 1e-9, (low + high) / 2, high - 1e-9):
            assert returns._bracketed_xirr_at(year_flows, rate, scale) == scanned, rate

    @pytest.mark.parametrize("near", [0.0, -1e-17, 1e-16, 2.3e-16, 3e-3], ids=["zero", "below", "rounds-to-one", "above", "inside"])
    def test_an_exact_zero_on_a_grid_point(self, near):
        """A value constant for 125 years: the NPV is exactly 0.0 at the grid point 10^0 − 1, kept as the root, as the scan
        keeps it."""
        year_flows = [(0.0, -1000.0), (125.0, 1000.0)]
        scale = _scale(year_flows)

        assert returns._xirr_npv(year_flows, 0.0) == 0.0
        assert returns._bracketed_xirr(year_flows, COLD_GUESS, scale) == 0.0
        assert returns._bracketed_xirr_at(year_flows, near, scale) == 0.0

    def test_none_where_the_scan_finds_nothing(self):
        """Outside the grid; in an interval without a sign change; at the overflow edge; where the sign product
        underflows; where the Brent root fails the verification."""
        long_flows = _point_flows(_long_history(0.03), _long_history(0.03)[0][1200].date)
        assert returns._bracketed_xirr_at(long_flows, 2e4, _scale(long_flows)) is None
        assert returns._bracketed_xirr_at(long_flows, -1.0 + 1e-13, _scale(long_flows)) is None
        assert returns._bracketed_xirr_at(long_flows, 5.0, _scale(long_flows)) is None

        edge = _point_flows(OVERFLOW_EDGE, date(1999, 11, 26))
        assert returns._bracketed_xirr_at(edge, -0.990880, _scale(edge)) is None

        underflow = _point_flows(PRODUCT_UNDERFLOW, date(6001, 8, 28))
        assert returns._bracketed_xirr_at(underflow, 0.04738, _scale(underflow)) is None

        ill = _point_flows(ILL_CONDITIONED, date(1940, 1, 4))
        assert returns._bracketed_xirr_at(ill, -0.0857, _scale(ill)) is None


# =============================================================================
# 2. The shortcut is taken, and only where the contract allows it
# =============================================================================


@dataclass
class _Call:
    name: str
    start: float  # the starting point; for _bracketed_xirr_at, the rate whose grid interval it reads
    flows: list[tuple[float, float]]
    nested: bool  # made by _solve_xirr
    result: float | None = None


class _Recorder:
    """Every call of the four solver functions, in order. Resolved at call time by the module, so wrapping the module's
    attributes sees them all. On HEAD three of them do not exist: AttributeError."""

    NAMES = ("_solve_xirr", "_newton_xirr", "_bracketed_xirr", "_bracketed_xirr_at")

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.calls: list[_Call] = []
        self.recording = True
        self._solving = 0
        for name in self.NAMES:
            monkeypatch.setattr(returns, name, self._wrap(name, getattr(returns, name)))

    def _wrap(self, name: str, real: Callable) -> Callable:
        def recorded(flows, start, *rest):
            if not self.recording:
                return real(flows, start, *rest)
            call = _Call(name=name, start=start, flows=flows, nested=self._solving > 0)
            self.calls.append(call)
            self._solving += name == "_solve_xirr"
            try:
                call.result = real(flows, start, *rest)
            finally:
                self._solving -= name == "_solve_xirr"
            return call.result

        return recorded

    def points(self) -> list[list[_Call]]:
        """The calls of each solved point, top level only: a point's calls share one flows list."""
        groups: list[list[_Call]] = []
        for call in self.calls:
            if call.nested:
                continue
            if groups and groups[-1][0].flows is call.flows:
                groups[-1].append(call)
            else:
                groups.append([call])
        return groups


def _contract_path(calls: list[_Call], previous: float | None) -> list[tuple[str, float]]:
    """The calls the contract asks for at one point, given what each earlier call of it returned."""
    flows = calls[0].flows
    opening = next(amount for years, amount in flows if years == 0.0)
    if previous is None or opening == 0.0 or _sign_changes(flows) != 1:
        return [("_solve_xirr", COLD_GUESS)]
    expected = [("_newton_xirr", COLD_GUESS)]
    if calls[0].result is not None:
        return expected
    expected.append(("_newton_xirr", previous))
    candidate = calls[1].result if len(calls) > 1 else None
    if candidate is not None and returns._XIRR_GRID_RATES[0] <= candidate <= returns._XIRR_GRID_RATES[1] and returns._changes_sign_at(flows, candidate):
        expected.append(("_bracketed_xirr_at", candidate))
        if len(calls) > 2 and calls[2].name == "_bracketed_xirr_at" and calls[2].result is not None:
            return expected
    expected.append(("_bracketed_xirr", COLD_GUESS))
    return expected


def _path_kind(calls: list[_Call]) -> str:
    names = [call.name for call in calls]
    if names == ["_solve_xirr"]:
        return "cold"
    if names == ["_newton_xirr"]:
        return "cold-newton"
    if names[-1] == "_bracketed_xirr_at":
        return "warm-interval"
    return "scan-after-warm"


def _solved_points(series: list[MWRRPoint], case: Case, line: bool) -> list[MWRRPoint]:
    """The points that reached the solver: all of the plain series; on the line, those with a value and capital."""
    if not line:
        return series
    navs, flows = case
    first = _by_date(navs)[0]
    by_day = {snapshot.date: snapshot.nav for snapshot in navs}
    capital = {point.date: first.nav - sum((flow.amount for flow in flows if first.date < flow.date <= point.date), Decimal("0")) for point in series}
    return [point for point in series if by_day[point.date] > 0 and capital[point.date] > 0]


def _record(monkeypatch: pytest.MonkeyPatch, case: Case, line: bool) -> tuple[Counter, list[tuple[list[_Call], float | None]]]:
    """Run the line or the plain series under the recorder and check every solved point against the contract.

    Returns how many points took each path, and every point's calls with the rate it kept."""
    navs, flows = case
    recorder = _Recorder(monkeypatch)
    series = returns.period_mwrr_series(navs, flows) if line else returns.calculate_mwrr_series(navs, flows)
    recorder.recording = False

    points, groups = _solved_points(series, case, line), recorder.points()
    assert len(groups) == len(points), f"{len(groups)} solves for {len(points)} points that need one"
    problems, kinds, kept_rates, previous = [], Counter(), [], None
    for point, calls in zip(points, groups, strict=True):
        actual = [(call.name, call.start) for call in calls]
        expected = _contract_path(calls, previous)
        if actual != expected:
            problems.append(f"{point.date}: calls {actual}, the contract's {expected}")
        kept = calls[-1].result
        if (None if kept is None else str(returns._rate_decimal(kept))) != (None if point.mwrr is None else str(point.mwrr)):
            problems.append(f"{point.date}: the solve kept {kept!r}, the point shows {point.mwrr}")
        kinds[_path_kind(calls)] += 1
        kept_rates.append((calls, kept))
        previous = kept if kept is not None else previous
    assert not problems, f"{len(problems)} of {len(points)} points: {problems[:4]}"
    inner = {call.start for call in recorder.calls if call.nested}
    assert inner <= {COLD_GUESS}, f"_solve_xirr started its steps from {inner}"
    return kinds, kept_rates


class TestTheShortcutIsTakenOnlyWhereTheContractAllows:
    """Every solved point calls exactly what the contract asks: the first solved point, and any point whose flows do not
    change sign exactly once or whose opening value is 0.0, ``_solve_xirr`` from 0.1 alone; any other point Newton from
    0.1, then (only if that failed) Newton from the previous point's rate — the last rate kept, a None point skipped —,
    then (only if that root is on the grid and the NPV changes sign across it) ``_bracketed_xirr_at`` on it, then (only
    if no rate yet) the whole scan from 0.1. Red on HEAD: the functions do not exist, and every point starts from 0.1."""

    @pytest.mark.parametrize("line", [True, False], ids=["line", "plain-series"])
    def test_the_long_history(self, monkeypatch, line):
        """Most points take the warm interval; the gap in the data (0 at the 600th snapshot), the withdrawal and the
        zero-sum date after it do not stop it."""
        kinds, _kept = _record(monkeypatch, _long_history(0.03), line)

        assert kinds["cold"] == 1 + (0 if line else 1), kinds  # the first point; on the plain series the gap as well (no sign change)
        assert kinds["warm-interval"] >= 900, kinds
        assert kinds["scan-after-warm"] <= 5, kinds

    @pytest.mark.parametrize("line", [True, False], ids=["line", "plain-series"])
    def test_a_constant_value(self, monkeypatch, line):
        """After the first 37 years (where Newton from 0.1 still finds the 0), every point: the exact zero of the grid,
        through the warm interval."""
        kinds, _kept = _record(monkeypatch, _constant_value(), line)

        assert kinds["warm-interval"] >= 1000, kinds
        assert kinds["scan-after-warm"] == 0, kinds

    def test_several_sign_changes_solve_cold(self, monkeypatch):
        """The plain series of two roots: from the withdrawal on, the flows change sign twice or three times, and every
        such point is ``_solve_xirr`` from 0.1."""
        _kinds, kept = _record(monkeypatch, MULTI_ROOT, line=False)

        several = [calls for calls, _rate in kept if _sign_changes(calls[0].flows) > 1]
        assert len(several) == 7  # 26 December 2020 to 24 June 2021
        assert all([(call.name, call.start) for call in calls] == [("_solve_xirr", COLD_GUESS)] for calls in several)

    @pytest.mark.parametrize("line", [True, False], ids=["line", "plain-series"])
    def test_an_opening_value_of_zero_solves_cold(self, monkeypatch, line):
        """The 1900 case: the opening value is 0.0, every point is ``_solve_xirr`` from 0.1."""
        kinds, _kept = _record(monkeypatch, FALSE_ROOT_1900, line)

        assert set(kinds) == {"cold"} and kinds["cold"] >= 14, kinds

    def test_a_root_beyond_the_grid_goes_to_the_scan(self, monkeypatch):
        """Newton from the previous rate finds 49991.5, beyond the grid: the scan runs, the interval is not read."""
        _kinds, kept = _record(monkeypatch, OUT_OF_GRID, line=False)

        beyond = [calls for calls, _rate in kept if len(calls) > 1 and calls[1].result is not None and calls[1].result > returns._XIRR_GRID_RATES[1]]
        assert beyond, "no point has a warm root beyond the grid"
        assert all(calls[-1].name == "_bracketed_xirr" and all(call.name != "_bracketed_xirr_at" for call in calls) for calls in beyond)

    @pytest.mark.parametrize("case", [ILL_CONDITIONED, PRODUCT_UNDERFLOW], ids=["ill-conditioned", "product-underflow"])
    def test_an_interval_without_a_verified_root_goes_to_the_scan(self, monkeypatch, case):
        """The warm root passes the guards, the interval gives nothing (the Brent root fails the verification, or the
        sign product underflows): the whole scan runs, from 0.1."""
        kinds, kept = _record(monkeypatch, case, line=False)

        fallbacks = [calls for calls, _rate in kept if [call.name for call in calls] == ["_newton_xirr", "_newton_xirr", "_bracketed_xirr_at", "_bracketed_xirr"]]
        assert fallbacks, kinds
        assert all(calls[2].result is None and calls[3].start == COLD_GUESS for calls in fallbacks)

    def test_no_sign_change_at_the_warm_root_goes_to_the_scan(self, monkeypatch):
        """Rates of 500 % to 900 % over 200 years with an opening of 1e-300: the NPV is below 1e-150 around Newton's root,
        _changes_sign_at says no, and the scan runs without reading the interval."""
        _kinds, kept = _record(monkeypatch, VANISHING_NPV, line=False)

        refused = [calls for calls, _rate in kept if len(calls) > 1 and calls[1].result is not None and returns._XIRR_GRID_RATES[0] <= calls[1].result <= returns._XIRR_GRID_RATES[1] and not returns._changes_sign_at(calls[0].flows, calls[1].result)]
        assert len(refused) >= 5, len(refused)
        assert all([call.name for call in calls] == ["_newton_xirr", "_newton_xirr", "_bracketed_xirr"] for calls in refused)

    @pytest.mark.parametrize("card", ["calculate_mwrr", "period_mwrr"])
    def test_the_card_solves_cold(self, monkeypatch, card):
        """The card has no previous point: one ``_solve_xirr`` from 0.1, on the long history's whole period."""
        navs, flows = _long_history(0.03)
        recorder = _Recorder(monkeypatch)
        if card == "calculate_mwrr":
            point = returns.calculate_mwrr(flows, navs[0].nav, navs[-1].nav, navs[0].date, navs[-1].date)
        else:
            point = returns.period_mwrr(navs, flows, navs[-1].date, navs[-1].nav)

        assert point.mwrr is not None
        assert [(call.name, call.start) for call in recorder.calls if not call.nested] == [("_solve_xirr", COLD_GUESS)]
        assert {call.start for call in recorder.calls if call.nested} == {COLD_GUESS}

    @pytest.mark.parametrize(
        "case",
        [_long_history(0.03), _constant_value(), ILL_CONDITIONED, PRODUCT_UNDERFLOW, OVERFLOW_EDGE],
        ids=["long-history", "constant-value", "ill-conditioned", "product-underflow", "overflow-edge"],
    )
    def test_every_rate_kept_is_the_cold_solve_s_bit_for_bit(self, monkeypatch, case):
        """Not only the 6 decimals: the raw rate each point keeps, the next point's warm start, is the one
        ``_solve_xirr`` from 0.1 returns on its flows, bit for bit (or None with None)."""
        _kinds, kept = _record(monkeypatch, case, line=False)

        differing = [f"{rate!r} vs {cold!r}" for calls, rate in kept if rate != (cold := returns._solve_xirr(calls[0].flows, COLD_GUESS))]
        assert not differing, f"{len(differing)} of {len(kept)} points: {differing[:5]}"


# =============================================================================
# 3. Cost
# =============================================================================


def _npv_evaluations_a_point(monkeypatch: pytest.MonkeyPatch, case: Case) -> float:
    real = returns._xirr_npv
    count = [0]

    def counted(flows, rate):
        count[0] += 1
        return real(flows, rate)

    monkeypatch.setattr(returns, "_xirr_npv", counted)
    line = returns.period_mwrr_series(*case)
    monkeypatch.setattr(returns, "_xirr_npv", real)
    return count[0] / len(line)


class TestCost:
    """NPV evaluations a point of the line: P1 measured 22.6 (125 years, 3 % a year) and 13.1 (a value constant since
    1900), HEAD 549.7 and 569.6. Deterministic counts, no clock. Red on HEAD."""

    @pytest.mark.parametrize("case", [_long_history(0.03), _constant_value()], ids=["long-history", "constant-value"])
    def test_at_most_cost_bound_npv_evaluations_a_point(self, monkeypatch, case):
        per_point = _npv_evaluations_a_point(monkeypatch, case)

        assert per_point <= COST_BOUND, f"{per_point:.1f} NPV evaluations a point (bound {COST_BOUND})"


# =============================================================================
# 4. Parity with the cold solve
# =============================================================================


def _daily(first: date, last: date, levels: dict[date, str]) -> list[NAVSnapshot]:
    """A value every day from ``first`` to ``last``, each level holding from its date."""
    navs, value, day = [], None, first
    while day <= last:
        value = levels.get(day, value)
        navs.append(NAVSnapshot(day, Decimal(value)))
        day += timedelta(days=1)
    return navs


def _window(case: Case, date_from: date | None) -> Case:
    if date_from is None:
        return case
    period = returns.rebase_to_period(case[0], case[1], date_from)
    return list(period.nav_snapshots), list(period.cash_flows)


def _database_scenarios() -> dict[str, Case]:
    """The scenarios of ``test_portfolio_mwrr_card_and_line.py`` (MF-K2), rebuilt as the engine's daily values and
    external flows (deposit < 0, withdrawal > 0), each over its fixed end date; the ``date_from`` windows rebased as the
    Dashboard rebases them. A day's value is cash plus quantity × the last close."""
    d = date
    nw = (_daily(d(2025, 1, 2), d(2025, 9, 30), {d(2025, 1, 2): "1000", d(2025, 6, 30): "1800", d(2025, 7, 15): "300"}), [CashFlowInput(d(2025, 1, 2), Decimal("-1000")), CashFlowInput(d(2025, 7, 15), Decimal("1500"))])
    vg = (_daily(d(2025, 1, 2), d(2025, 9, 30), {d(2025, 1, 2): "1000", d(2025, 6, 30): "500", d(2025, 7, 15): "0"}), [CashFlowInput(d(2025, 1, 2), Decimal("-1000")), CashFlowInput(d(2025, 7, 15), Decimal("500"))])
    do = (
        _daily(d(2025, 1, 2), d(2025, 8, 29), {d(2025, 1, 2): "1000", d(2025, 3, 3): "1200", d(2025, 5, 2): "1700", d(2025, 6, 2): "1800"}),
        [CashFlowInput(d(2025, 1, 2), Decimal("-1000")), CashFlowInput(d(2025, 5, 2), Decimal("-500"))],
    )
    ob = (_daily(d(2025, 3, 3), d(2025, 8, 29), {d(2025, 3, 3): "1000", d(2025, 6, 2): "1150"}), [CashFlowInput(d(2025, 3, 3), Decimal("-1000"))])
    scenarios = {
        "net-withdrawal/whole": nw,
        "net-withdrawal/rebased": _window(nw, d(2025, 1, 15)),
        "value-gone": vg,
        "deposits-only/whole": do,
        "deposits-only/from": _window(do, d(2025, 2, 1)),
        "single-deposit/opens-before": _window(ob, d(2025, 3, 3) - timedelta(days=30)),
        "single-deposit/opens-on": _window(ob, d(2025, 3, 3)),
    }
    for withdrawal in ("300", "1000", "1200"):
        yw = (
            _daily(d(2025, 3, 3), d(2025, 8, 29), {d(2025, 3, 3): "1000", d(2025, 5, 2): "1400", d(2025, 6, 16): str(1400 - int(withdrawal))}),
            [CashFlowInput(d(2025, 3, 3), Decimal("-1000")), CashFlowInput(d(2025, 6, 16), Decimal(withdrawal))],
        )
        scenarios[f"young-withdrawal/{withdrawal}"] = _window(yw, d(2025, 3, 3) - timedelta(days=30))
    return scenarios


def _existing_inputs() -> dict[str, Case]:
    """The series inputs of the existing MWRR tests.

    Imported: every hand-written data set of ``test_mwrr_verified_root.py`` (its ``HAND_WRITTEN``: the pinned
    scenarios, no root, zero rate) and the module constants of ``test_period_mwrr.py``. Rebuilt: the inline data of
    ``test_period_mwrr.py``, ``test_financial/test_roi_utils.py`` and ``test_utilities/test_roi_utils.py``. The
    random sample of ``test_mwrr_verified_root.py`` has its own test below."""
    d = date
    cases: dict[str, Case] = {f"verified-root/{name}": (list(navs), list(flows)) for name, (navs, flows) in verified_root.HAND_WRITTEN.items()}
    cases |= {
        "period/ordinary": (period_cases._navs(period_cases.ORDINARY_NAVS), period_cases._flows(period_cases.ORDINARY_FLOWS)),
        "period/same-date": (period_cases._navs(period_cases.SAME_DATE_NAVS), period_cases._flows(period_cases.SAME_DATE_FLOWS)),
        "period/young": (period_cases._navs(period_cases.YOUNG_NAVS), period_cases._flows(period_cases.YOUNG_FLOWS)),
        "period/history": (period_cases._navs(period_cases.HISTORY_NAVS), period_cases._flows(period_cases.HISTORY_FLOWS)),
    }
    for date_from in (d(2024, 12, 31), d(2024, 6, 1)):
        cases[f"period/young-rebased-{date_from}"] = _window(cases["period/young"], date_from)
    for date_from in (d(2025, 1, 1), d(2025, 2, 15), d(2025, 4, 1)):
        cases[f"period/history-rebased-{date_from}"] = _window(cases["period/history"], date_from)
    for withdrawal in ("1500", "1000"):
        w = Decimal(withdrawal)
        cases[f"period/net-withdrawal-{withdrawal}"] = (
            [NAVSnapshot(d(2025, 1, 1), Decimal("1000")), NAVSnapshot(d(2025, 4, 1), Decimal("1200")), NAVSnapshot(d(2025, 7, 1), 1700 - w), NAVSnapshot(d(2025, 10, 1), 1750 - w), NAVSnapshot(d(2026, 1, 1), 1800 - w)],
            [CashFlowInput(d(2025, 1, 1), Decimal("-1000")), CashFlowInput(d(2025, 7, 1), w)],
        )
    for nav in ("0", "-50"):
        cases[f"period/nav-{nav}"] = _case(f"2025-01-01 1000  2025-04-01 450  2025-07-01 {nav}  2025-10-01 1050", "2025-01-01 -1000  2025-04-01 600  2025-08-01 -1000")
    cases |= {
        "period/end-date-deposit": _case("2025-01-01 1000  2025-07-02 1040  2026-01-01 1580", "2025-01-01 -1000  2026-01-01 -500"),
        "period/end-date-withdrawal": _case("2025-01-01 1000  2025-07-02 1040  2026-01-01 580", "2025-01-01 -1000  2026-01-01 500"),
        "period/first-date-flows": _case("2025-01-01 1000  2026-01-01 1080", "2025-01-01 -600  2025-01-01 -400"),
        "period/rebased-opening": _window(_case("2024-07-01 1000  2025-01-01 2000  2025-07-02 2100  2026-01-01 2160", "2024-07-01 -1000  2024-10-01 -900"), d(2025, 1, 1)),
        "period/earlier-withdrawal": _case("2025-01-01 1000  2025-07-02 1040  2026-01-01 1080", "2024-10-01 5000  2025-01-01 -1000"),
        "period/earlier-deposit": _case("2025-01-01 1000  2025-04-01 1200  2025-07-01 200  2026-01-01 300", "2024-10-01 -5000  2025-01-01 -1000  2025-07-01 1500"),
        "period/gain-on-the-first-day": _case("2025-01-01 1010  2025-04-01 1050  2025-07-01 55  2026-01-01 60", "2025-01-01 -1000  2025-07-01 1005"),
        "period/loss-on-the-first-day": _case("2025-01-01 990  2025-04-01 1030  2025-07-01 45  2026-01-01 50", "2025-01-01 -1000  2025-07-01 995"),
        "period/decimal-sum": _case(
            "2025-01-01 1000  2025-07-01 1450  2026-01-01 1300",
            "2025-01-01 -600  2025-01-01 -400  2025-05-15 -0.10  2025-05-15 -0.20  2025-07-01 -150  2025-07-01 -50  2026-01-01 250  2026-01-01 -50",
        ),
        "roi/no-flows": _case("2025-01-01 10000  2025-06-01 10500  2025-12-31 11000", ""),
        "roi/quarterly": _case("2025-01-01 5000  2025-04-01 5500  2025-07-01 6000  2025-10-01 6500  2025-12-31 7000", ""),
        "roi/mid-deposit": _case("2025-01-01 10000  2025-06-01 10500  2025-12-31 12000", "2025-06-01 -1000"),
        "roi/loud-start": ([NAVSnapshot(d(2025, 1, 1) + timedelta(days=day), Decimal("26000") + 11 * day) for day in range(91)], [CashFlowInput(d(2025, 1, 31), Decimal("-500"))]),
        "roi/loud-first-point": _case("2025-01-01 26000  2025-01-02 26100  2025-04-01 27000", "2025-01-01 -26000"),
        "roi/summary-from-zero": _case("2025-01-01 0  2025-12-31 1800", "2025-01-01 -1000  2025-07-01 -500"),
        "roi/summary-double-counted": _case("2025-01-01 1500  2025-12-31 1800", "2025-01-01 -1000  2025-07-01 -500"),
        "utilities/one-year": _case("2025-01-01 1000  2026-01-01 1200", ""),
        "utilities/mid-flow": _case("2025-01-01 1000  2025-07-01 1100  2026-01-01 1250", "2025-07-01 -100"),
        "utilities/three-years": _case("2025-01-01 1000  2026-01-01 1200  2027-01-01 1300  2028-01-01 1400", ""),
    }
    return cases


EXISTING_INPUTS = _existing_inputs()
DATABASE_SCENARIOS = _database_scenarios()
P1_FAMILIES: dict[str, Callable[[], Case]] = {
    "long-history-3%": lambda: _long_history(0.03),
    "long-history-6%": lambda: _long_history(0.06),
    "ten-years": _ten_years,
    "constant-value": _constant_value,
    "multi-root": lambda: MULTI_ROOT,
    "out-of-grid": lambda: OUT_OF_GRID,
    "false-root-1900": lambda: FALSE_ROOT_1900,
    "overflow-edge": lambda: OVERFLOW_EDGE,
    "ill-conditioned": lambda: ILL_CONDITIONED,
    "product-underflow": lambda: PRODUCT_UNDERFLOW,
    "vanishing-npv": lambda: VANISHING_NPV,
}


class TestParityWithTheColdSolve:
    """Every point of the line and of the plain series is today's cold solve, by ``str()``. Green on HEAD and on P1."""

    @pytest.mark.parametrize("name", EXISTING_INPUTS)
    def test_the_existing_inputs(self, name):
        _assert_parity(EXISTING_INPUTS[name])

    def test_the_random_sample_of_the_verified_root_tests(self):
        """Seed 20261015, its first 100 scenarios (``test_mwrr_verified_root.py``'s generator)."""
        rng = random.Random(verified_root.SAMPLE_SEED)
        for _index in range(verified_root.SAMPLE_SIZE):
            _assert_parity(verified_root._scenario(rng))

    @pytest.mark.parametrize("name", DATABASE_SCENARIOS)
    def test_the_database_scenarios(self, name):
        _assert_parity(DATABASE_SCENARIOS[name])

    @pytest.mark.parametrize("name", P1_FAMILIES)
    def test_the_p1_families(self, name):
        _assert_parity(P1_FAMILIES[name]())

    def test_each_point_is_the_card_of_its_period(self):
        """The oracle itself, on sampled points of the long history: the line's point is ``period_mwrr`` on the
        snapshots up to it, as the card reads them."""
        navs, flows = _long_history(0.03)
        line = returns.period_mwrr_series(navs, flows)

        for index in (1, 2, 30, LONG_GLITCH, LONG_GLITCH + 1, 1000, 1350, len(navs) - 1):
            assert line[index - 1] == returns.period_mwrr(navs[: index + 1], flows, navs[index].date, navs[index].nav), navs[index].date


# =============================================================================
# 5. Why each guard: where a warm start answers something else
# =============================================================================


class TestWhereAWarmStartWouldAnswerSomethingElse:
    """On each family, at one point: ``_solve_xirr`` from the previous point's rate (what a warm start gives) is not
    ``_solve_xirr`` from 0.1 (today's), and the series gives today's. Green on HEAD: it documents the data."""

    def test_several_sign_changes(self):
        """26 December 2020: two roots. From the previous rate (2.16) a solve stays on 2.158683; today's is −0.461894,
        the root nearest 0.1. Hence one sign change, and only one, for the shortcut."""
        flows = _point_flows(MULTI_ROOT, MULTI_ROOT_DAY)
        warm, cold = returns._solve_xirr(flows, _previous_cold_rate(MULTI_ROOT, MULTI_ROOT_DAY)), returns._solve_xirr(flows, COLD_GUESS)

        assert _sign_changes(flows) == 2
        assert str(returns._rate_decimal(warm)) == "2.158683" and str(returns._rate_decimal(cold)) == "-0.461894"
        assert all(_npv_changes_sign(flows, root) for root in (warm, cold))
        assert next(point for point in returns.calculate_mwrr_series(*MULTI_ROOT) if point.date == MULTI_ROOT_DAY).mwrr == Decimal("-0.461894")

    def test_a_root_beyond_the_grid(self):
        """18 January 2020: from the previous rate Newton reaches 49991.496589, beyond the grid's last rate; today's solve
        has no root. Hence the grid range."""
        flows = _point_flows(OUT_OF_GRID, OUT_OF_GRID_DAY)
        warm = returns._solve_xirr(flows, _previous_cold_rate(OUT_OF_GRID, OUT_OF_GRID_DAY))

        assert warm is not None and warm > returns._XIRR_GRID[-1] - 1.0
        assert str(returns._rate_decimal(warm)) == "49991.496589"
        assert returns._solve_xirr(flows, COLD_GUESS) is None
        assert next(point for point in returns.calculate_mwrr_series(*OUT_OF_GRID) if point.date == OUT_OF_GRID_DAY).mwrr is None

    def test_an_opening_value_of_zero(self):
        """The developer's 1900 case. On 11 July 2025 the previous rate is 379.189396, a grid point where every term
        underflows; from it a solve stays there (the first P1 design did, on every later point); today's is 6.262327.
        Hence the opening value checked as a float."""
        flows = _point_flows(FALSE_ROOT_1900, FALSE_ROOT_DAY)
        previous = _previous_cold_rate(FALSE_ROOT_1900, FALSE_ROOT_DAY)

        assert previous == returns._XIRR_GRID[729] - 1.0 and returns._xirr_npv(flows, previous) == 0.0
        assert returns._solve_xirr(flows, previous) == previous
        assert str(returns._rate_decimal(returns._solve_xirr(flows, COLD_GUESS))) == "6.262327"
        assert next(point for point in returns.period_mwrr_series(*FALSE_ROOT_1900) if point.date == FALSE_ROOT_DAY).mwrr == Decimal("6.262327")

    def test_the_grid_s_overflow_edge(self):
        """26 November 1999: from the previous rate Newton finds −0.990880, a true root; the grid point below it
        overflows, the scan cannot bracket it, today's answer is None. Hence the scan's own interval tests."""
        day = date(1999, 11, 26)
        flows = _point_flows(OVERFLOW_EDGE, day)
        warm = returns._solve_xirr(flows, _previous_cold_rate(OVERFLOW_EDGE, day))
        low, _high = _grid_interval(warm)

        assert str(returns._rate_decimal(warm)) == "-0.990880" and _npv_changes_sign(flows, warm)
        with pytest.raises(OverflowError):
            returns._xirr_npv(flows, low)
        assert returns._solve_xirr(flows, COLD_GUESS) is None
        assert [str(point.mwrr) for point in returns.period_mwrr_series(*OVERFLOW_EDGE)] == ["-0.990880", "None"]


# =============================================================================
# 6. HEAD behaviour preserved
# =============================================================================


class TestHeadBehaviourPreserved:
    """Two weaknesses of today's solve, which P1 reproduces on purpose: its contract is today's answer. Each is a
    possible separate lot (it would change numbers the Dashboard shows today). Green on HEAD and on P1."""

    def test_weakness_1_the_scan_s_sign_product_underflows(self):
        """``_bracketed_xirr`` tests a sign change with ``previous_npv * npv < 0.0``; where both NPVs are tiny the product
        underflows to −0.0 and a true root is missed. 28 August 6001: the NPVs at the grid points around the root are
        nonzero, of opposite signs, their product 0.0; Brent in that interval finds a verified root; today's answer,
        and the line's, is None."""
        day = date(6001, 8, 28)
        flows = _point_flows(PRODUCT_UNDERFLOW, day)
        warm = returns._solve_xirr(flows, _previous_cold_rate(PRODUCT_UNDERFLOW, day))
        low, high = _grid_interval(warm)
        low_npv, high_npv = returns._xirr_npv(flows, low), returns._xirr_npv(flows, high)
        missed = _scan_brent(flows, low, high)

        assert low_npv > 0.0 > high_npv and low_npv * high_npv == 0.0
        assert returns._is_xirr_root(flows, missed, _scale(flows)) and _npv_changes_sign(flows, missed)
        assert returns._solve_xirr(flows, COLD_GUESS) is None
        line = returns.period_mwrr_series(*PRODUCT_UNDERFLOW)
        assert next(point for point in line if point.date == day).mwrr is None
        assert sum(point.mwrr is None for point in line) >= 10

    def test_weakness_2_the_verification_of_an_ill_conditioned_root(self):
        """``_is_xirr_root`` asks |NPV| ≤ 1e-7 · Σ|amounts|; where the NPV's terms are ~1e12 and cancel, that depends on
        a root's last bits. 4 January 1940: Newton's root from the previous rate passes, the scan's Brent root a few ulps
        away does not; today's answer, and the line's, is None."""
        day = date(1940, 1, 4)
        flows = _point_flows(ILL_CONDITIONED, day)
        warm = returns._solve_xirr(flows, _previous_cold_rate(ILL_CONDITIONED, day))
        low, high = _grid_interval(warm)
        scanned = _scan_brent(flows, low, high)

        assert warm is not None and returns._is_xirr_root(flows, warm, _scale(flows)) and _npv_changes_sign(flows, warm)
        assert abs(scanned - warm) < 1e-12 and not returns._is_xirr_root(flows, scanned, _scale(flows))
        assert returns._solve_xirr(flows, COLD_GUESS) is None
        line = returns.period_mwrr_series(*ILL_CONDITIONED)
        assert next(point for point in line if point.date == day).mwrr is None
