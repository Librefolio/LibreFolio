"""
P1 (workstream MF, N74, «formule veloci»): the Dashboard's MWRR line starts each point's XIRR from the previous point's
rate — and keeps, point by point, exactly the rate the cold solve of today gives. «È imperativo non sbagliare i calcoli,
veloci sì, ma precisi.»

P1b (same workstream, approved by the developer): the two weaknesses of the solve that P1 reproduced on purpose are fixed
in the solve itself. A sign change is read from the signs of the two NPVs, never from their product, which underflows
to −0.0 when both are tiny — both above a noise floor, below which the sign of a subnormal NPV is rounding
(``_opposite_signs``, ``_npv_noise_floor``; at the scan, at P1's interval and in ``_changes_sign_at``). And a root the
bracketing found (the scan's Brent roots, the interval's) is verified when |NPV| ≤ 1e-7 · Σ|amounts| or, where that
fails, when the NPV changes sign within ±1e-9 (relative) of it (``_is_bracketed_xirr_root``): an ill-conditioned NPV,
whose terms are far larger than the flows and cancel at the root, made the first test depend on the root's last bits.
Newton's answer, and an exact zero on a grid point, keep HEAD's test alone (``_is_xirr_root``): with several roots,
which one the solve returns stays HEAD's. The cold solve, the card and the line change together; P1's contract (the
warm path keeps the cold solve's rate bit for bit) is unchanged. The developer's review of P1b's first design (signs
without a floor, the sign test in Newton's verification too) added the two cases of ``TestWhatP1bLeavesAsItWas``.

P1c (MF5-4): a grid point whose NPV is exactly 0.0 is a root only where the NPV changes sign around it
(``_changes_sign_at``), in the scan and in ``_bracketed_xirr_at``. On a period opening at value 0 far from its flows,
every NPV term underflows at the top of the grid and the NPV is exactly 0.0 at rates that solve nothing; HEAD returned
the one nearest 0.1. Those points now have no rate: the 1900 case's 5-8 July (section 6) and the 1720 period (section 7).

Module under test: ``backend/app/services/financial_math/returns.py`` — ``_mwrr_solve``, the solve of a series point,
through ``period_mwrr_series`` (the line) and ``calculate_mwrr_series``; and its helpers ``_flow_sign_changes``,
``_changes_sign_at``, ``_bracketed_xirr_at``, ``_npv_noise_floor``, ``_opposite_signs``, ``_is_xirr_root`` and
``_is_bracketed_xirr_root``.

Before P1 (ff9930b26) every point is ``_solve_xirr(flows, 0.1)``: Newton from 0.1, kept only where the NPV vanishes;
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

1. Units: ``_flow_sign_changes`` (zeros aside, in time order), ``_changes_sign_at`` (a true root, also where the product
   of the two NPVs underflows; not a flat NPV near zero; not where the NPV cannot be evaluated, within 1e-9 of −100 %
   included; not a sign change in the noise), ``_npv_noise_floor`` (subnormal for any realistic portfolio; above the
   noise of an underflowing NPV), ``_opposite_signs`` (read from the signs; a zero, 0.0 or −0.0, is no sign, nor is a
   value below the floor), ``_is_xirr_root`` (HEAD's tolerance test; an ill-conditioned root refused) and
   ``_is_bracketed_xirr_root`` (the same, or the sign test: the ill-conditioned root accepted); neither accepts a rate
   near a root, near a tangency or at a flat maximum, nor where the NPV cannot be evaluated or is not finite;
   ``_bracketed_xirr_at`` (the scan's root bit for bit, its exact zero, None wherever the scan finds nothing in the
   interval).
2. The shortcut is taken, and only where the contract allows it (structural). A recorder wraps ``_solve_xirr``,
   ``_newton_xirr``, ``_bracketed_xirr`` and ``_bracketed_xirr_at``; every solved point's calls must be exactly the
   contract's, the warm start must be the previous point's rate bit for bit, and every rate kept must be the cold
   solve's bit for bit, on every family. Red on HEAD: three of the four functions do not exist there (AttributeError),
   and HEAD starts every point from 0.1.
3. Cost: on a 125-year history and on a value constant since 1900, at most ``COST_BOUND`` NPV evaluations a point.
   Red on HEAD.
4. Parity with the cold solve, on every input of the existing MWRR test files, the database scenarios of
   ``test_portfolio_mwrr_card_and_line.py`` rebuilt as plain inputs, the families found while building P1 and P1b, and a
   random sample of ill-conditioned series. Green before P1 and on P1, the random sample aside (it records the warm path
   and asks for a rate kept by the sign test): that is the guarantee.
5. Why each guard: on the data where it decides, a warm start answers something else than today's solve.
6. The two weaknesses, fixed (P1b): the root of the product-underflow and ill-conditioned families, the lines that had
   no rate, the vanishing NPV, the 1900 case's false root giving way to the true one, the warm path keeping the
   interval's root or, where Newton keeps HEAD's test, running the scan. Red on P1's HEAD (325e78fc8). And what P1b
   leaves as it was: a sign in the noise brackets nothing (the 1720 period's noise interval); Newton keeps HEAD's
   test (a three-root account keeps HEAD's −0.019580). Green on HEAD, red on P1b's first design.
7. The false exact zero, removed (P1c): the 1720 period, whose HEAD answer 12.803843 was a grid point where every NPV
   term underflows, has no rate.

«HEAD» in P1's texts (sections 2 to 5, and the cost figures) is ff9930b26, before P1; in P1b's (section 6, the units and
cases marked P1b) it is 325e78fc8, with P1, before P1b.

The parity oracle. A point of HEAD's series is, by its code, the card on its prefix: ``_mwrr_point`` from the first
snapshot, solved cold. Here the oracle is ``period_mwrr`` (the line) and ``calculate_mwrr`` (the plain series) from the
first snapshot to each point, which P1 still solves through ``_solve_xirr`` from 0.1. Before P1 was committed the oracle
was compared with the HEAD of the time (ff9930b26, ``returns.py`` loaded from git into its own module) on every case
below: identical, by ``str()`` of every point. P1b changes the oracle itself, by design: the points of section 6.
Rates are compared by ``str()``, the exponent included; None with None.

Measured in a harness (plain Python, outside the repository) before writing this file:

* NPV evaluations a point, period line: 125 years, 3 % a year (the case below): HEAD 549.7, P1 22.6; a value constant
  since 1900: HEAD 569.6, P1 13.1. P1b: the same counts as P1 (22.5 and 13.1 in the P1b harness; the sign test runs
  only where the tolerance test fails). On the ill-conditioned family P1b costs 316 a point (P1 691): where the warm
  Newton root misses HEAD's test the whole scan runs (P1b's first design, which let that root through, 99).
* The first P1 design (warm ``_solve_xirr`` before the cold one, only the grid range checked) on the 1900 case of
  section 5: 379.189396 — an exact zero of the grid, 10^(129/50) − 1 — on 380 of 399 points where HEAD differs. The
  second (cold Newton first, then the warm root itself as the answer) differed from HEAD on 212 of 3000 ill-conditioned
  series (section 6) and at the grid's overflow edge (section 5): the warm Newton root passed the verification where
  the scan's Brent root, 6e-16 away, did not. As built: 0 differences on all of them.
* P1b against P1 (325e78fc8), cold solve, card and line, with every value checked at 60 digits (a sign change of the
  NPV within half a quantum of the 6 decimals shown): no change on the inputs of the existing test files and the
  database scenarios; on the P1 families, a rate where P1 had none on 34 points (product underflow 13, ill-conditioned
  7, vanishing NPV 14) and the true root instead of the grid's false one on 3 points of the 1900 case; on 1000 random
  realistic portfolios (1 to 40 years, with their rebased windows) a rate where P1 had none on 2496 of 480 983 points,
  rates of −41 % to −100 % a year after near-total losses (weakness 2), and no other change; on 700 extreme series,
  1997 rates where P1 had none and 282 false grid zeros replaced: 281 by the true root, one by a root located 1.4e-4
  short (84.211901 for 84.212040: an opening value of 0 in 1848, the NPV subnormal near the root). Never a rate taken
  away, never a value in the noise (P1b's first design added 22). P1b's warm path keeps the cold solve's rate bit
  for bit on every point of all of them, and of 3000 ill-conditioned series.

Isolation: pure functions, no database, no server, no network; ``monkeypatch`` restores every wrapped function.
"""

from __future__ import annotations

import math
import random
import sys
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal, localcontext

import pytest
from scipy.optimize import brentq, newton

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
# term underflows: the NPV is exactly 0.0 there, and the scan keeps those grid points as roots. HEAD's answer (325e78fc8)
# on 4-10 July was that grid point; the first P1 design, starting from the previous rate, stayed on it to the end. P1b
# (section 6): on 4, 9 and 10 July the scan now also sees the true root (the NPVs around it are tiny, of opposite signs,
# their product 0.0), nearer 0.1, and keeps it; on 5-8 July the true root lies above 379.19, where every term
# underflows, and P1b's cold solve answered the grid point still. P1c: that exact zero does not change sign, so 5-8 July
# have no rate.
FALSE_ROOT_1900 = _case(
    """
    1900-01-01 0  2025-07-01 10000.00  2025-07-02 10000.00  2025-07-03 10143.83  2025-07-04 10399.90  2025-07-05 10711.12
    2025-07-06 11003.30  2025-07-07 11200.86  2025-07-08 11248.28  2025-07-09 11129.91  2025-07-10 10877.21
    2025-07-11 10558.23  2025-07-12 10254.49  2025-07-13 10037.44  2025-07-14 9953.30  2025-07-15 10017.54
    2025-07-16 10214.98
    """,
    "2025-07-01 -10000",
)
# The day after the grid-point days (P1 used 11 July; with P1b 10 July has its true root). Until P1c its previous
# point's rate was the grid point; with P1c 5-8 July have no rate, and the previous rate is 4 July's true root.
FALSE_ROOT_DAY = date(2025, 7, 9)
# The days whose rate P1b changes, from the grid point to the true root, and the days that kept the grid point (no rate
# since P1c).
FALSE_ROOT_FIXED_DAYS = (date(2025, 7, 4), date(2025, 7, 9), date(2025, 7, 10))
FALSE_ROOT_KEPT_DAYS = (date(2025, 7, 5), date(2025, 7, 6), date(2025, 7, 7), date(2025, 7, 8))

# The grid's overflow edge: 1000 on 1 January 1850 and, 150 years later, a value of about 1e-303. The root (−0.990880)
# lies between the point where the NPV overflows and the first grid point where it does not: the scan cannot bracket
# it, today's answer is None, and Newton from the previous day's rate finds it. The warm path reads the interval, which
# gives nothing (its lower grid point overflows), and runs the whole scan (section 2).
OVERFLOW_EDGE = _case("1850-01-01 1000  1999-11-25 1.0131043591955372E-303  1999-11-26 9.998500111744283E-304", "1850-01-01 -1000")

# Ill-conditioned (weakness 2, fixed by P1b, section 6): 1000 in 1700, 10 000 deposited 240 years later, then about
# −8.75 % a year. The NPV's terms (~1e13) cancel at the root, and whether a root passes |NPV| ≤ 1e-7 · Σ|amounts| depends
# on its last bits: on several points Newton's root passes and the scan's Brent root, a few ulps away, does not. HEAD
# (325e78fc8) had no rate on 7 of the 11 points; P1b accepts a bracketed root across which the NPV changes sign
# (``_is_bracketed_xirr_root``), and has all 11. Newton's answer keeps HEAD's test: on 3 points the warm Newton root misses
# it, and the scan runs (section 6).
ILL_CONDITIONED = _case(
    """
    1700-01-01 1000  1939-12-05 9926.5250  1940-01-04 9853.8303  1940-02-03 9777.4932  1940-03-04 9698.1487
    1940-04-03 9622.3652  1940-05-03 9555.5923  1940-06-02 9494.6690  1940-07-02 9429.1016  1940-08-01 9351.3277
    1940-08-31 9265.9257  1940-09-30 9187.2307
    """,
    "1939-11-05 -10000",
)

# Product underflow (weakness 1, fixed by P1b, section 6): an opening value of 1e-300 in year 1 and 1000 deposited 6000
# years later, the rate drifting up by 0.00002 a day across the grid point 10^(1/50) − 1 = 0.047129 (0.047000 on the
# first point, 0.047380 on the last). Past it the NPVs at the two grid points around the root are about 1e-121 and
# −1e-239: their product underflows to −0.0, and HEAD's scan («previous_npv * npv < 0.0») missed the root, though Newton
# finds it and the NPV changes sign across it: no rate on 13 of the 20 points. P1b reads the signs (``_opposite_signs``),
# both NPVs far above its noise floor (``_npv_noise_floor``, about 4e-320 here).
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

# The NPV vanishing below the step of _changes_sign_at (weakness 1 again, fixed by P1b): an opening value of 1e-300 in
# 1800 and 1000 deposited 200 years later, the rate rising from 300 % to 900 % a year by 25 % a point. From about 500 %
# the NPV's terms are below 1e-150 at the root: on HEAD the NPVs at ±1e-9 of Newton's root multiplied to 0.0,
# _changes_sign_at said no, and the scan ran and found nothing (its grid NPVs underflow the same way): no rate on 14 of
# the 25 points. P1b reads the signs: every point has its rate, the interval's.
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

# A near-total loss: 1000 losing 6.25 % a day for 20 days (to cents), about −100 % a year: 1 + r ≈ 5.9e-11, within 1e-9
# of −100 %. Where the guards of P1 still decide after P1b: Newton from the previous point's rate finds the root, but
# _changes_sign_at cannot evaluate the NPV 1e-9 below it (1 + r − 1e-9 < 0) and says no, so the scan runs; and from 17
# January the scan's Brent root misses |NPV| ≤ 1e-7 · Σ|amounts| (the NPV's slope is about 7e11 there) while the NPV below
# it cannot be evaluated either: no rate, on HEAD as with P1b (the sign test of P1b cannot help within 1e-9 of −1).
NEAR_TOTAL_LOSS = _case(
    """
    2025-01-01 1000.00  2025-01-02 937.50  2025-01-03 878.91  2025-01-04 823.97  2025-01-05 772.48  2025-01-06 724.20
    2025-01-07 678.93  2025-01-08 636.50  2025-01-09 596.72  2025-01-10 559.42  2025-01-11 524.46  2025-01-12 491.68
    2025-01-13 460.95  2025-01-14 432.14  2025-01-15 405.13  2025-01-16 379.81  2025-01-17 356.07  2025-01-18 333.82
    2025-01-19 312.96  2025-01-20 293.40  2025-01-21 275.06
    """,
    "2025-01-01 -1000",
)
NEAR_TOTAL_LOSS_UNVERIFIED_DAY = date(2025, 1, 17)

# Subnormal noise (issue 1 of P1b's first design): a period opening on 1 January 1720 at value 0, 10 000 deposited on 19
# June 2007 and 10 493.87 the next day. The true root, (1.049387)^365 − 1 ≈ 4.4e7, is beyond the grid. Every NPV term
# underflows over 287 years: in the grid interval [11.589254, 12.182567] the NPVs are 1.6e-314 and −1.8e-320, and the
# second's sign is rounding (at 60 digits it is +2.8e-320). Reading the signs alone, P1b's first design bracketed a root
# there and answered 12.182509, which is no root; the noise floor (4.1e-319 for these flows) refuses that pair, and the
# answer is HEAD's own: 12.803843, the grid point 10^(57/50) − 1 where the NPV is exactly 0.0 by underflow. That one is
# HEAD's false exact zero (as in FALSE_ROOT_1900), a weakness P1b does not touch; P1c removes it, and the period has
# no rate (section 7).
SUBNORMAL_NOISE = _case("1720-01-01 0  2007-06-20 10493.87", "2007-06-19 -10000")
SUBNORMAL_NOISE_DAY = date(2007, 6, 20)

# Newton's own test (issue 2 of P1b's first design): a 25.5-year account, 50 000 at the start, 2594 at the end, and 14
# flows in between (shrunk from a random realistic portfolio of the P1b harness). The flows change sign three times and
# the NPV has three roots: −0.754735, −0.019580 and 1.304648. Newton from 0.1 lands on −0.754735, where the NPV's terms
# are ~1e10 and cancel: |NPV| = 1582, far above 1e-7 · Σ|amounts|, although the NPV changes sign across it. HEAD refuses
# it, the scan runs, and the answer is its root nearest 0.1, −0.019580. With the sign test in Newton's verification too,
# P1b's first design answered −0.754735. Newton keeps HEAD's test (``_is_xirr_root``): the answer stays −0.019580.
NEWTON_ILL_CONDITIONED = _case(
    "1976-05-20 50000  2001-11-20 2594",
    """
    1976-08-20 -21463  1976-09-20 84753  1978-08-20 22434  1988-02-20 -5000  1990-06-20 -5000  1994-04-20 -5000
    1996-01-20 -5000  1996-05-20 -3361  1996-10-20 -1649  2000-12-20 -500  2001-03-20 -1000  2001-08-20 -500
    2001-09-20 -871  2001-10-20 -1153
    """,
)
NEWTON_ILL_CONDITIONED_DAY = date(2001, 11, 20)


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
    """The test's own check, with the NPV only: finite NPVs of opposite signs 1e-9 (relative) on either side of ``rate``,
    read from their signs (P1b: their product can underflow to 0.0)."""
    step = 1e-9 * max(1.0, abs(rate))
    try:
        below, above = returns._xirr_npv(year_flows, rate - step), returns._xirr_npv(year_flows, rate + step)
    except OverflowError:
        return False
    return math.isfinite(below) and math.isfinite(above) and below != 0.0 and above != 0.0 and (below < 0.0) != (above < 0.0)


def _exact_npv(year_flows: Sequence[tuple[float, float]], rate: float) -> Decimal:
    """The test's own NPV at 60 digits, of the same float flows and rate: no term underflows, no rounding to speak of. The
    reference for an NPV whose float value is subnormal, where its sign can be rounding."""
    with localcontext() as context:
        context.prec = 60
        base = Decimal(1) + Decimal(rate)
        return sum((Decimal(amount) * base ** -Decimal(years) for years, amount in year_flows), Decimal(0))


def _grid_interval(rate: float) -> tuple[float, float]:
    """The two grid rates around ``rate``, as the scan computes them."""
    index = next(index for index, base in enumerate(returns._XIRR_GRID) if base >= 1.0 + rate)
    return returns._XIRR_GRID[index - 1] - 1.0, returns._XIRR_GRID[index] - 1.0


def _scan_brent(year_flows: Sequence[tuple[float, float]], low: float, high: float) -> float:
    """The scan's Brent call on one grid interval."""
    return brentq(lambda rate: returns._xirr_npv(year_flows, rate), low, high, xtol=1e-14, maxiter=200)


def _scipy_newton(year_flows: Sequence[tuple[float, float]], start: float) -> float:
    """Newton's call of ``_newton_xirr``, without its verification: where Newton stops."""
    return float(newton(lambda rate: returns._xirr_npv(year_flows, rate), start, fprime=lambda rate: returns._xirr_npv_slope(year_flows, rate), tol=1e-12, maxiter=100))


def _one_deposit_rate(case: Case, end_date: date) -> str:
    """The rate in closed form of a case whose one flow is a deposit grown to the value of ``end_date``, at 6 decimals:
    (value / deposit) ** (365 / days) − 1, the days counted from the deposit. The opening value, before the deposit (0,
    1e-300, or 1000 two centuries earlier), is left out: it moves the root by less than 1e-9."""
    navs, flows = case
    (deposit,) = flows
    value = next(snapshot.nav for snapshot in navs if snapshot.date == end_date)
    rate = (float(value) / float(-deposit.amount)) ** (365 / (end_date - deposit.date).days) - 1.0
    return str(Decimal(repr(rate)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


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

    def test_a_sign_change_whose_product_underflows(self):
        """P1b: two centuries after an opening of 1e-300, a root of 900 % a year (Brent between 8.9 and 9.1). The NPVs
        1e-9 (relative) on either side of it are tiny, of opposite signs, their product 0.0. A sign change, read from the
        signs. Red on HEAD, which multiplied them."""
        year_flows = _point_flows(VANISHING_NPV, date(2001, 12, 3))
        root = _scan_brent(year_flows, 8.9, 9.1)
        step = 1e-9 * root
        below, above = returns._xirr_npv(year_flows, root - step), returns._xirr_npv(year_flows, root + step)

        assert abs(root - 9.0) < 1e-9
        assert below > 0.0 > above and below * above == 0.0
        assert returns._changes_sign_at(year_flows, root)

    def test_within_1e_9_of_minus_100_percent(self):
        """A near-total loss: Newton from the previous point's rate finds the root, 1 + r ≈ 5.9e-11, and the NPV 1e-9 below
        it cannot be evaluated (1 + r − 1e-9 < 0): no sign change can be shown, with P1b as on HEAD."""
        day = date(2025, 1, 3)
        year_flows = _point_flows(NEAR_TOTAL_LOSS, day)
        root = returns._newton_xirr(year_flows, _previous_cold_rate(NEAR_TOTAL_LOSS, day), _scale(year_flows))

        assert root is not None and 0.0 < 1.0 + root < 1e-9
        with pytest.raises(OverflowError):
            returns._xirr_npv(year_flows, root - 1e-9)
        assert not returns._changes_sign_at(year_flows, root)

    def test_a_sign_change_in_the_noise_is_not_a_root(self):
        """P1b: the period opening in 1720 at value 0 (``SUBNORMAL_NOISE``). Brent between the grid points 11.589254 and
        12.182567, whose float NPVs are 1.6e-314 and −1.8e-320, stops on 12.182509; ±1e-9 around it the float NPVs are
        3.4e-320 and −1.8e-320, both below the noise floor (4.1e-319): no sign change. At 60 digits the NPV is positive at
        both grid points: there is no root in that interval. (The tolerance test accepts the rate, as it accepts any rate
        where every term underflows: hence the noise must not bracket a root.)"""
        year_flows = _point_flows(SUBNORMAL_NOISE, SUBNORMAL_NOISE_DAY)
        low, high = _grid_interval(12.18)
        noise_root = _scan_brent(year_flows, low, high)
        step = 1e-9 * noise_root
        below, above = returns._xirr_npv(year_flows, noise_root - step), returns._xirr_npv(year_flows, noise_root + step)
        floor = returns._npv_noise_floor(year_flows)

        assert str(returns._rate_decimal(noise_root)) == "12.182509"
        assert below > 0.0 > above and max(abs(below), abs(above)) < floor
        assert _exact_npv(year_flows, low) > 0 and _exact_npv(year_flows, high) > 0
        assert returns._is_xirr_root(year_flows, noise_root, _scale(year_flows))
        assert not returns._changes_sign_at(year_flows, noise_root)


def _realistic_floor() -> float:
    """The noise floor of 1000 in and 1100 out a year later: about 4e-320."""
    return returns._npv_noise_floor([(0.0, -1000.0), (1.0, 1100.0)])


class TestNpvNoiseFloor:
    """``_npv_noise_floor`` (P1b): the size below which an NPV's sign is rounding noise, 4 · (Σ|amount| + terms) smallest
    subnormals."""

    def test_its_size(self):
        assert returns._npv_noise_floor([(0.0, -1000.0), (1.0, 1100.0)]) == 4.0 * (2100.0 + 2) * math.ulp(0.0)

    def test_it_is_subnormal_for_any_realistic_portfolio(self):
        """Up to 1e12 of flows, or a thousand of them: below the smallest normal float, so it never refuses an NPV that has
        not underflowed."""
        assert returns._npv_noise_floor([(0.0, -1e12), (40.0, 1e12)]) < sys.float_info.min
        assert returns._npv_noise_floor([(day / 365, -1e6) for day in range(1000)]) < sys.float_info.min

    def test_it_covers_the_noise_of_an_underflowing_npv(self):
        """The 1720 period at the grid point 12.182567: the float NPV is −1.8e-320, the NPV at 60 digits +2.8e-320. The
        sign is wrong, and both the value and its error are below the floor."""
        year_flows = _point_flows(SUBNORMAL_NOISE, SUBNORMAL_NOISE_DAY)
        _low, high = _grid_interval(12.18)
        float_npv, exact = returns._xirr_npv(year_flows, high), _exact_npv(year_flows, high)
        floor = returns._npv_noise_floor(year_flows)

        assert float_npv < 0 < exact
        assert abs(float_npv) < floor and float(abs(Decimal(float_npv) - exact)) < floor

    def test_the_underflow_pair_is_far_above_it(self):
        """28 August 6001 (``PRODUCT_UNDERFLOW``): the grid NPVs around the root, 1.3e-121 and −2.0e-239, against a floor of
        4.0e-320 — their sign is not noise."""
        year_flows = _point_flows(PRODUCT_UNDERFLOW, date(6001, 8, 28))
        low, high = _grid_interval(0.04738)
        floor = returns._npv_noise_floor(year_flows)

        assert floor < 1e-318
        assert returns._xirr_npv(year_flows, low) > 1e-122 and -1e-238 < returns._xirr_npv(year_flows, high) < -1e-240


class TestOppositeSigns:
    """``_opposite_signs`` (P1b): both above the noise floor and of opposite signs, read from the signs, never from the
    product."""

    @pytest.mark.parametrize(
        ("first", "second"),
        [(1e-200, -1e-200), (-1e-121, 1e-239), (1.0, -2.0), (-3.5, 1e300)],
        ids=["product-underflows", "the-scan-s-6001-pair", "plain", "wide-apart"],
    )
    def test_opposite_signs(self, first, second):
        floor = _realistic_floor()

        assert returns._opposite_signs(first, second, floor) and returns._opposite_signs(second, first, floor)

    def test_their_product_can_underflow(self):
        """The reason: on these pairs the product HEAD tested is −0.0, not below 0.0."""
        assert 1e-200 * -1e-200 == 0.0 and not 1e-200 * -1e-200 < 0.0
        assert returns._opposite_signs(1e-200, -1e-200, _realistic_floor())

    @pytest.mark.parametrize(
        ("first", "second"),
        [(1.6e-314, -1.8e-320), (3.4e-320, -1.8e-320), (-1.8e-320, 1.0)],
        ids=["the-1720-grid-pair", "the-1720-pair-around-brent-s-stop", "noise-and-a-normal-value"],
    )
    def test_a_sign_below_the_noise_floor_is_no_sign(self, first, second):
        """The subnormal NPVs of the 1720 period, against its floor (4.1e-319): refused. HEAD's product accepted the last
        pair (−1.8e-320 < 0.0): there P1b is stricter than HEAD. Next to each other on the grid such NPVs need one of at
        least 1e-5 beside a subnormal one: a grid step changes a term by a factor 10^(years/50), so only flows more than
        15 000 years apart, or larger terms cancelling exactly, could produce it."""
        floor = returns._npv_noise_floor(_point_flows(SUBNORMAL_NOISE, SUBNORMAL_NOISE_DAY))

        assert abs(first) < floor or abs(second) < floor
        assert not returns._opposite_signs(first, second, floor) and not returns._opposite_signs(second, first, floor)

    def test_the_floor_itself_is_noise(self):
        """Strictly above: a value equal to the floor is refused, the next float above it is not."""
        floor = 1e-300

        assert not returns._opposite_signs(floor, -1.0, floor)
        assert returns._opposite_signs(math.nextafter(floor, 1.0), -1.0, floor)

    @pytest.mark.parametrize(
        ("first", "second"),
        [(0.0, -1.0), (-1.0, 0.0), (0.0, 1.0), (0.0, 0.0), (-0.0, 1.0), (1.0, -0.0), (-0.0, -1.0), (-0.0, 0.0), (-0.0, -0.0)],
        ids=["zero-negative", "negative-zero", "zero-positive", "zeros", "minus-zero-positive", "positive-minus-zero", "minus-zero-negative", "minus-zero-zero", "minus-zeros"],
    )
    @pytest.mark.parametrize("floor", [0.0, 4e-320], ids=["no-floor", "realistic-floor"])
    def test_a_zero_is_no_sign(self, first, second, floor):
        """0.0 and −0.0 alike, even with a floor of 0.0: an exact zero is a root the callers handle before (the scan keeps
        it), never a sign change. −0.0 is not read as negative: the comparison, not the sign bit, decides."""
        assert not returns._opposite_signs(first, second, floor)

    @pytest.mark.parametrize(
        ("first", "second"),
        [(1.0, 2.0), (-1.0, -2.0), (1e-200, 1e-200), (-1e-200, -1e300)],
        ids=["positive", "negative", "tiny-positive", "tiny-and-huge-negative"],
    )
    def test_the_same_sign(self, first, second):
        assert not returns._opposite_signs(first, second, _realistic_floor())


def _head_tolerance_test(year_flows: Sequence[tuple[float, float]], rate: float) -> bool:
    """The test's own copy of HEAD's verification: a finite rate whose NPV can be evaluated and is within 1e-7 of Σ|amounts|."""
    if not math.isfinite(rate):
        return False
    try:
        return abs(returns._xirr_npv(year_flows, rate)) <= 1e-7 * _scale(year_flows)
    except (OverflowError, ZeroDivisionError):
        return False


class _RefusedByEitherTest:
    """What both verifications refuse, the tolerance test alone (``_is_xirr_root``) and with the sign test
    (``_is_bracketed_xirr_root``): the subclass names its predicate."""

    PREDICATE = ""

    def _accepts(self, year_flows: Sequence[tuple[float, float]], rate: float) -> bool:
        return getattr(returns, self.PREDICATE)(year_flows, rate, _scale(year_flows))

    def test_a_rate_near_a_root_is_not_a_root(self):
        """1000 in, 1100 out a year later: the root is 0.1. At 0.1 ± 1e-6 the NPV is ∓9.1e-4, above 1e-7 · 2100, and it
        does not change sign within ±1.1e-9: refused, as on HEAD. A wider step would take it for the root."""
        year_flows = [(0.0, -1000.0), (1.0, 1100.0)]

        for rate in (0.1 + 1e-6, 0.1 - 1e-6):
            assert abs(returns._xirr_npv(year_flows, rate)) > returns._XIRR_ROOT_TOLERANCE * _scale(year_flows)
            assert not self._accepts(year_flows, rate), rate
        assert self._accepts(year_flows, 0.1)

    def test_near_a_tangency_without_a_crossing(self):
        """−1, 2.1 and −1.1025 a year apart: the NPV −(1.05 · v − 1)² touches 0 at 5 % and never crosses it. 1e-3 away from
        the tangency the NPV is about −9e-7, above 1e-7 · Σ|amounts|, and negative on both sides: refused."""
        year_flows = [(0.0, -1.0), (1.0, 2.1), (2.0, -1.1025)]

        for rate in (0.05 - 1e-3, 0.05 + 1e-3):
            assert returns._xirr_npv(year_flows, rate) < -returns._XIRR_ROOT_TOLERANCE * _scale(year_flows)
            assert not _npv_changes_sign(year_flows, rate)
            assert not self._accepts(year_flows, rate), rate

    def test_a_flat_maximum_below_zero(self):
        """−1, 2.1 and −1.1026 a year apart: no root, the NPV's maximum (at 5.01 %) is −9.1e-5, flat there: refused, and
        the solve has no rate."""
        year_flows = [(0.0, -1.0), (1.0, 2.1), (2.0, -1.1026)]
        top = 2 * 1.1026 / 2.1 - 1.0

        assert -1e-4 < returns._xirr_npv(year_flows, top) < -returns._XIRR_ROOT_TOLERANCE * _scale(year_flows)
        assert not self._accepts(year_flows, top)
        assert returns._solve_xirr(year_flows, COLD_GUESS) is None

    @pytest.mark.parametrize(
        ("year_flows", "rate"),
        [
            ([(0.0, -1000.0), (1.0, 1100.0)], -1.5),
            ([(0.0, -1000.0), (1.0, 1100.0)], -1.0),
            ([(0.0, -1000.0), (150.0, 1e-303)], -0.9999),
            ([(0.0, -1000.0), (1.0, 1100.0)], math.inf),
            ([(0.0, -1000.0), (1.0, 1100.0)], -math.inf),
            ([(0.0, -1000.0), (1.0, 1100.0)], math.nan),
        ],
        ids=["base-negative", "base-zero", "overflow", "infinite-rate", "minus-infinite-rate", "nan-rate"],
    )
    def test_where_the_npv_cannot_be_evaluated(self, year_flows, rate):
        assert not self._accepts(year_flows, rate)

    @pytest.mark.parametrize(
        "year_flows",
        [[(0.0, -1e300), (2.0, 1e300)], [(2.0, 1e300), (3.0, -1e300)]],
        ids=["infinite-npv", "nan-npv"],
    )
    def test_where_the_npv_is_not_finite(self, year_flows):
        """At 1 + r = 1e-5 the discounted 1e300 overflows to ±inf without an error (and inf − inf is nan), at the rate as
        1e-9 on either side of it: refused by both tests."""
        rate = -0.99999

        assert not math.isfinite(returns._xirr_npv(year_flows, rate))
        assert not returns._changes_sign_at(year_flows, rate)
        assert not self._accepts(year_flows, rate)


class TestIsXirrRoot(_RefusedByEitherTest):
    """``_is_xirr_root``: |NPV| ≤ 1e-7 · Σ|amounts|, HEAD's test, unchanged by P1b. Newton's answer is verified by it alone
    (cold and warm), and so is an exact zero on a grid point."""

    PREDICATE = "_is_xirr_root"

    @pytest.mark.parametrize(
        ("case", "day", "rate"),
        [
            (None, None, 0.1),
            (None, None, 0.1 + 1e-6),
            (ILL_CONDITIONED, date(1940, 1, 4), -0.08568138471785151),
            (ILL_CONDITIONED, date(1940, 1, 4), -0.08568138471784965),
            (NEWTON_ILL_CONDITIONED, NEWTON_ILL_CONDITIONED_DAY, -0.7547347541646361),
            (NEWTON_ILL_CONDITIONED, NEWTON_ILL_CONDITIONED_DAY, -0.01957950701762048),
            (SUBNORMAL_NOISE, SUBNORMAL_NOISE_DAY, 12.182508633409459),
            (PRODUCT_UNDERFLOW, date(6001, 8, 28), 0.0473800000000315),
        ],
        ids=["root", "near-root", "ill-brent-root", "ill-newton-root", "newton-ill-root", "newton-ill-scan-root", "subnormal-noise", "underflow-root"],
    )
    def test_it_is_head_s_tolerance_test(self, case, day, rate):
        """On the roots, near-roots and noise of this file, the test's own copy of HEAD's verification decides the same."""
        year_flows = [(0.0, -1000.0), (1.0, 1100.0)] if case is None else _point_flows(case, day)

        assert returns._is_xirr_root(year_flows, rate, _scale(year_flows)) == _head_tolerance_test(year_flows, rate)

    def test_an_ill_conditioned_root_is_refused(self):
        """4 January 1940: the scan's Brent root misses the tolerance by its last bits (the NPV's terms, ~1e13, cancel),
        although the NPV changes sign across it: refused, as on HEAD. Newton's root, a few ulps away, passes."""
        year_flows = _point_flows(ILL_CONDITIONED, date(1940, 1, 4))
        root = _scan_brent(year_flows, *_grid_interval(-0.0857))
        newton = returns._newton_xirr(year_flows, _previous_cold_rate(ILL_CONDITIONED, date(1940, 1, 4)), _scale(year_flows))

        assert abs(returns._xirr_npv(year_flows, root)) > returns._XIRR_ROOT_TOLERANCE * _scale(year_flows)
        assert _npv_changes_sign(year_flows, root)
        assert not returns._is_xirr_root(year_flows, root, _scale(year_flows))
        assert newton is not None and abs(newton - root) < 1e-12 and returns._is_xirr_root(year_flows, newton, _scale(year_flows))


class TestIsBracketedXirrRoot(_RefusedByEitherTest):
    """``_is_bracketed_xirr_root`` (P1b): the tolerance test, or the NPV changing sign within ±1e-9 (relative) of the
    rate. Only for a root the bracketing found (the scan's Brent roots, ``_bracketed_xirr_at``'s): it only ever accepts
    more than ``_is_xirr_root``; these are the ones it must still refuse, above."""

    PREDICATE = "_is_bracketed_xirr_root"

    def test_an_ill_conditioned_root_is_accepted(self):
        """4 January 1940: the scan's Brent root misses the tolerance, and the NPV changes sign across it. Red on HEAD."""
        year_flows = _point_flows(ILL_CONDITIONED, date(1940, 1, 4))
        root = _scan_brent(year_flows, *_grid_interval(-0.0857))

        assert not returns._is_xirr_root(year_flows, root, _scale(year_flows)) and _npv_changes_sign(year_flows, root)
        assert returns._is_bracketed_xirr_root(year_flows, root, _scale(year_flows))

    def test_it_accepts_whatever_the_tolerance_test_accepts(self):
        """A flat NPV near zero (about −1 against a tolerance of 1e20, no sign change) and an exact zero on a grid point
        (a value constant for 125 years): as ``_is_xirr_root``."""
        flat, constant = [(0.0, -1.0), (125.0, 1e27)], [(0.0, -1000.0), (125.0, 1000.0)]
        flat_rate = returns._XIRR_GRID[729] - 1.0

        assert not returns._changes_sign_at(flat, flat_rate)
        assert returns._is_xirr_root(flat, flat_rate, _scale(flat)) and returns._is_bracketed_xirr_root(flat, flat_rate, _scale(flat))
        assert returns._is_xirr_root(constant, 0.0, _scale(constant)) and returns._is_bracketed_xirr_root(constant, 0.0, _scale(constant))

    def test_newton_s_ill_conditioned_root_would_pass(self):
        """``NEWTON_ILL_CONDITIONED``: Newton from 0.1 lands on −0.754735, a true root (at 60 digits the NPV is +1.1e10 and
        −1.1e10 at ±1e-9) whose |NPV| is 1582. This test accepts it, the tolerance test does not: Newton must keep the
        tolerance test, or the solve would answer that root instead of the scan's nearest 0.1 (section 6)."""
        year_flows = _point_flows(NEWTON_ILL_CONDITIONED, NEWTON_ILL_CONDITIONED_DAY)
        root = _scipy_newton(year_flows, COLD_GUESS)

        assert str(returns._rate_decimal(root)) == "-0.754735"
        assert _exact_npv(year_flows, root - 1e-9) > 0 > _exact_npv(year_flows, root + 1e-9)
        assert abs(returns._xirr_npv(year_flows, root)) > 1000 * returns._XIRR_ROOT_TOLERANCE * _scale(year_flows)
        assert returns._is_bracketed_xirr_root(year_flows, root, _scale(year_flows))
        assert not returns._is_xirr_root(year_flows, root, _scale(year_flows))


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
        """Outside the grid; in an interval without a sign change; at the overflow edge; where the Brent root fails the
        verification: within 1e-9 of −100 %, its |NPV| above the tolerance and the NPV below it beyond evaluation; where
        the float NPVs change sign only in the noise (the 1720 period, ``SUBNORMAL_NOISE``). (Until P1b this test also had
        the sign product underflowing and an ill-conditioned Brent root: section 6 now asserts their roots.)"""
        long_flows = _point_flows(_long_history(0.03), _long_history(0.03)[0][1200].date)
        assert returns._bracketed_xirr_at(long_flows, 2e4, _scale(long_flows)) is None
        assert returns._bracketed_xirr_at(long_flows, -1.0 + 1e-13, _scale(long_flows)) is None
        assert returns._bracketed_xirr_at(long_flows, 5.0, _scale(long_flows)) is None

        edge = _point_flows(OVERFLOW_EDGE, date(1999, 11, 26))
        assert returns._bracketed_xirr_at(edge, -0.990880, _scale(edge)) is None

        near_total = _point_flows(NEAR_TOTAL_LOSS, NEAR_TOTAL_LOSS_UNVERIFIED_DAY)
        rate = math.expm1(365 / 16 * math.log(356.07 / 1000))  # the closed form, 16 days at 356.07 for 1000
        low, high = _grid_interval(rate)
        brent = _scan_brent(near_total, low, high)
        assert returns._xirr_npv(near_total, low) > 0.0 > returns._xirr_npv(near_total, high), "the interval holds the root"
        assert abs(returns._xirr_npv(near_total, brent)) > returns._XIRR_ROOT_TOLERANCE * _scale(near_total)
        with pytest.raises(OverflowError):
            returns._xirr_npv(near_total, brent - 1e-9)
        assert returns._bracketed_xirr_at(near_total, rate, _scale(near_total)) is None
        assert returns._bracketed_xirr(near_total, COLD_GUESS, _scale(near_total)) is None

        noise = _point_flows(SUBNORMAL_NOISE, SUBNORMAL_NOISE_DAY)
        low, high = _grid_interval(12.18)
        assert returns._xirr_npv(noise, low) > 0.0 > returns._xirr_npv(noise, high), "a float sign change, in the noise"
        assert returns._bracketed_xirr_at(noise, 12.18, _scale(noise)) is None


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

    @pytest.mark.parametrize("case", [OVERFLOW_EDGE], ids=["overflow-edge"])
    def test_an_interval_without_a_verified_root_goes_to_the_scan(self, monkeypatch, case):
        """The warm root passes the guards, the interval gives nothing (its lower grid point overflows: the scan cannot
        bracket the root either): the whole scan runs, from 0.1. Until P1b the ill-conditioned and product-underflow
        families were the cases here (the Brent root failing the verification, the sign product underflowing): P1b gives
        their interval's root, section 6."""
        kinds, kept = _record(monkeypatch, case, line=False)

        fallbacks = [calls for calls, _rate in kept if [call.name for call in calls] == ["_newton_xirr", "_newton_xirr", "_bracketed_xirr_at", "_bracketed_xirr"]]
        assert fallbacks, kinds
        assert all(calls[2].result is None and calls[3].start == COLD_GUESS for calls in fallbacks)

    def test_no_sign_change_at_the_warm_root_goes_to_the_scan(self, monkeypatch):
        """A near-total loss, 1 + r ≈ 5.9e-11: Newton from the previous point's rate finds the root, on the grid, but the
        NPV 1e-9 below it cannot be evaluated, _changes_sign_at says no, and the scan runs without reading the interval.
        (Until P1b the case here was the vanishing NPV, whose «no» was the product of two tiny NPVs underflowing.)"""
        _kinds, kept = _record(monkeypatch, NEAR_TOTAL_LOSS, line=False)

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
        [_long_history(0.03), _constant_value(), ILL_CONDITIONED, PRODUCT_UNDERFLOW, OVERFLOW_EDGE, _long_history(0.06), _ten_years(), MULTI_ROOT, OUT_OF_GRID, FALSE_ROOT_1900, VANISHING_NPV, NEAR_TOTAL_LOSS],
        ids=["long-history", "constant-value", "ill-conditioned", "product-underflow", "overflow-edge", "long-history-6%", "ten-years", "multi-root", "out-of-grid", "false-root-1900", "vanishing-npv", "near-total-loss"],
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
    "near-total-loss": lambda: NEAR_TOTAL_LOSS,
}

# A fresh random sample of ill-conditioned series (P1b): the family whose verification P1b widens, where the first P1
# designs differed from HEAD on 212 of 3000 series.
ILL_SAMPLE_SEED = 20261019
ILL_SAMPLE_SIZE = 200


def _ill_conditioned(rng: random.Random) -> Case:
    """An opening of 1 to 5000 in 1600-1800, one deposit 150 to 300 years later, then a value every 30 days for 8 to 14
    points at −40 % to +40 % a year (±1 % a point): the NPV's terms are as large as (1 + r) ** −300 makes them, and cancel
    at the root."""
    open_year = rng.randint(1600, 1800)
    opening = Decimal(rng.choice([1, 10, 100, 1000, 5000]))
    deposit_day = date(open_year + rng.randint(150, 300), rng.randint(1, 12), rng.randint(1, 28))
    deposit = Decimal(rng.choice([1000, 5000, 10000, 50000]))
    annual = rng.uniform(-0.4, 0.4)
    navs, value, day = [NAVSnapshot(date(open_year, 1, 1), opening)], float(deposit), deposit_day
    for _point in range(rng.randint(8, 14)):
        day += timedelta(days=30)
        value *= (1 + annual) ** (30 / 365) * (1 + rng.uniform(-0.01, 0.01))
        navs.append(NAVSnapshot(day, Decimal(repr(value)).quantize(Decimal("0.0001"))))
    return navs, [CashFlowInput(deposit_day, -deposit)]


class TestParityWithTheColdSolve:
    """Every point of the line and of the plain series is today's cold solve, by ``str()``. Green on HEAD and on P1 (P1b's
    random sample aside: its barrier asks for a rate kept by the sign test)."""

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

    def test_a_random_sample_of_ill_conditioned_series(self, monkeypatch):
        """P1b, seed 20261019, 200 series: every point of the line and of the plain series is the cold solve's by
        ``str()``, and every raw rate the warm path keeps is ``_solve_xirr`` from 0.1, bit for bit, by the contract's
        calls. The sample does reach what P1b changed: some of its points have their rate only by the sign test."""
        rng = random.Random(ILL_SAMPLE_SEED)
        kept_rates, by_the_sign_test = 0, 0
        for _index in range(ILL_SAMPLE_SIZE):
            case = _ill_conditioned(rng)
            _assert_parity(case)
            _kinds, kept = _record(monkeypatch, case, line=False)
            monkeypatch.undo()
            differing = [f"{rate!r} vs {cold!r}" for calls, rate in kept if rate != (cold := returns._solve_xirr(calls[0].flows, COLD_GUESS))]
            assert not differing, f"{case[0][0].date}: {differing[:3]}"
            for calls, rate in kept:
                if rate is not None:
                    kept_rates += 1
                    by_the_sign_test += abs(returns._xirr_npv(calls[0].flows, rate)) > returns._XIRR_ROOT_TOLERANCE * _scale(calls[0].flows)
        assert kept_rates > 1000 and by_the_sign_test > 0, (kept_rates, by_the_sign_test)

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
    ``_solve_xirr`` from 0.1 (today's), and the series gives today's. Green on HEAD: it documents the data — except the
    opening value of zero, whose day P1b moved (on HEAD the cold solve of 9 July is the grid point itself)."""

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
        """The developer's 1900 case. Until P1c, on 9 July 2025 the previous rate was 379.189396, a grid point where every
        term underflows, and a solve from it stayed there (the first P1 design did, on every later point). P1c: 5-8 July
        have no rate, so the previous rate is 4 July's true root, 116.999874; from it the solve lands on 131.184839 by
        other bits than today's cold solve (the contract is bit for bit). Today's is the true root, 131.184839, proved by
        the NPV's sign change at 60 digits; the line gives it. Hence the opening value checked as a float. (P1 showed it
        on 11 July, whose previous point, 10 July, had the grid point too until P1b gave it its true root, section 6.)"""
        flows = _point_flows(FALSE_ROOT_1900, FALSE_ROOT_DAY)
        previous = _previous_cold_rate(FALSE_ROOT_1900, FALSE_ROOT_DAY)
        cold = returns._solve_xirr(flows, COLD_GUESS)
        warm = returns._solve_xirr(flows, previous)

        assert str(returns._rate_decimal(previous)) == "116.999874" == _one_deposit_rate(FALSE_ROOT_1900, date(2025, 7, 4))
        assert _npv_changes_sign(_point_flows(FALSE_ROOT_1900, date(2025, 7, 4)), previous)
        assert warm is not None and warm != cold and str(returns._rate_decimal(warm)) == "131.184839"
        assert _npv_changes_sign(flows, cold) and _exact_npv(flows, cold - 1e-6) > 0 > _exact_npv(flows, cold + 1e-6)
        assert str(returns._rate_decimal(cold)) == "131.184839" == _one_deposit_rate(FALSE_ROOT_1900, FALSE_ROOT_DAY)
        assert next(point for point in returns.period_mwrr_series(*FALSE_ROOT_1900) if point.date == FALSE_ROOT_DAY).mwrr == Decimal("131.184839")
        # P1's day, 11 July: today's answer there is unchanged by P1b.
        eleventh = date(2025, 7, 11)
        assert str(returns._rate_decimal(returns._solve_xirr(_point_flows(FALSE_ROOT_1900, eleventh), COLD_GUESS))) == "6.262327"
        assert next(point for point in returns.period_mwrr_series(*FALSE_ROOT_1900) if point.date == eleventh).mwrr == Decimal("6.262327")

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
# 6. The two weaknesses, fixed (P1b)
# =============================================================================


class TestTheTwoWeaknessesFixed:
    """P1 reproduced two weaknesses of the solve on purpose (its contract was HEAD's answer); P1b fixes them in the solve
    itself, so the cold solve, the card and the line change together, and the warm path still keeps the cold solve's
    rate bit for bit (section 2). Red on HEAD (325e78fc8).

    1. The sign product. The scan tested a sign change with ``previous_npv * npv < 0.0``, P1's interval and
       ``_changes_sign_at`` the same way; with both NPVs tiny the product underflows to −0.0 and a true root was missed.
       P1b reads the signs (``_opposite_signs``) of NPVs both above a noise floor (``_npv_noise_floor``, a few smallest
       subnormals per unit of amount): below it a sign is rounding, ``TestWhatP1bLeavesAsItWas``.
    2. The verification of an ill-conditioned root. ``_is_xirr_root`` asks |NPV| ≤ 1e-7 · Σ|amounts|; where the NPV's
       terms are far larger than the flows and cancel at the root, that depended on the root's last bits. P1b also
       accepts a root the bracketing found (the scan's Brent roots, ``_bracketed_xirr_at``'s) across which the NPV
       changes sign within ±1e-9 (relative): a true root that close (``_is_bracketed_xirr_root``). Newton's answer keeps
       HEAD's test alone, ``TestWhatP1bLeavesAsItWas``.

    Every rate asserted here is a root bracketed by a sign change of the NPV, and the rate the data was built with: the
    closed form of its one deposit (``_one_deposit_rate``)."""

    def test_weakness_1_the_scan_reads_the_signs(self):
        """28 August 6001: the NPVs at the grid points around the root are nonzero, of opposite signs, their product 0.0.
        Brent in that interval finds the root, which the NPV changes sign across; HEAD's answer, and its line's, was
        None. It is now the cold solve's answer, the interval's and the line's: 0.047380."""
        day = date(6001, 8, 28)
        flows = _point_flows(PRODUCT_UNDERFLOW, day)
        warm = returns._solve_xirr(flows, _previous_cold_rate(PRODUCT_UNDERFLOW, day))
        low, high = _grid_interval(warm)
        low_npv, high_npv = returns._xirr_npv(flows, low), returns._xirr_npv(flows, high)
        missed = _scan_brent(flows, low, high)

        assert low_npv > 0.0 > high_npv and low_npv * high_npv == 0.0
        assert min(abs(low_npv), abs(high_npv)) > returns._npv_noise_floor(flows)
        assert returns._is_xirr_root(flows, missed, _scale(flows)) and _npv_changes_sign(flows, missed)
        assert returns._solve_xirr(flows, COLD_GUESS) == missed
        assert str(returns._rate_decimal(missed)) == "0.047380" == _one_deposit_rate(PRODUCT_UNDERFLOW, day)
        assert returns._bracketed_xirr_at(flows, 0.04738, _scale(flows)) == missed
        line = returns.period_mwrr_series(*PRODUCT_UNDERFLOW)
        assert next(point for point in line if point.date == day).mwrr == Decimal("0.047380")

    def test_weakness_2_an_ill_conditioned_root_is_verified_by_its_sign_change(self):
        """4 January 1940: Newton's root from the previous rate passes |NPV| ≤ 1e-7 · Σ|amounts|, the scan's Brent root a
        few ulps away does not (its NPV is 0.0039, the bound 0.0021); the NPV changes sign across both. HEAD's answer,
        and its line's, was None. The Brent root passes the bracketed verification, and is now the cold solve's answer,
        the interval's and the line's: −0.085681."""
        day = date(1940, 1, 4)
        flows = _point_flows(ILL_CONDITIONED, day)
        warm = returns._solve_xirr(flows, _previous_cold_rate(ILL_CONDITIONED, day))
        low, high = _grid_interval(warm)
        scanned = _scan_brent(flows, low, high)

        assert warm is not None and returns._is_xirr_root(flows, warm, _scale(flows)) and _npv_changes_sign(flows, warm)
        assert abs(scanned - warm) < 1e-12 and abs(returns._xirr_npv(flows, scanned)) > returns._XIRR_ROOT_TOLERANCE * _scale(flows)
        assert returns._xirr_npv(flows, low) > 0.0 > returns._xirr_npv(flows, high) and _npv_changes_sign(flows, scanned)
        assert not returns._is_xirr_root(flows, scanned, _scale(flows))
        assert returns._is_bracketed_xirr_root(flows, scanned, _scale(flows))
        assert returns._solve_xirr(flows, COLD_GUESS) == scanned
        assert str(returns._rate_decimal(scanned)) == "-0.085681" == _one_deposit_rate(ILL_CONDITIONED, day)
        assert returns._bracketed_xirr_at(flows, -0.0857, _scale(flows)) == scanned
        line = returns.period_mwrr_series(*ILL_CONDITIONED)
        assert next(point for point in line if point.date == day).mwrr == Decimal("-0.085681")

    @pytest.mark.parametrize(
        ("case", "head_none"),
        [(PRODUCT_UNDERFLOW, 13), (ILL_CONDITIONED, 7), (VANISHING_NPV, 14)],
        ids=["product-underflow", "ill-conditioned", "vanishing-npv"],
    )
    def test_the_line_has_a_rate_on_every_point(self, case, head_none):
        """HEAD's lines had no rate on 13 of the 20 points (product underflow, weakness 1), 7 of the 11 (ill-conditioned,
        weakness 2), 14 of the 25 (the vanishing NPV: weakness 1 in ``_changes_sign_at`` and in the scan). P1b's have a
        rate on every point, the closed form of the data."""
        line = returns.period_mwrr_series(*case)

        assert [point.date for point in line if point.mwrr is None] == [], f"HEAD had {head_none} points without a rate"
        assert [str(point.mwrr) for point in line] == [_one_deposit_rate(case, point.date) for point in line]

    def test_the_vanishing_npv_is_a_root_by_its_signs(self):
        """3 December 2001, 900 % a year: the NPVs at ±1e-9 of the root are of opposite signs, their product 0.0 (HEAD's
        ``_changes_sign_at`` said no there, and the grid's NPVs underflowed the same way in the scan). The cold solve now
        answers 9.000000."""
        day = date(2001, 12, 3)
        flows = _point_flows(VANISHING_NPV, day)
        root = returns._solve_xirr(flows, COLD_GUESS)
        step = 1e-9 * root
        below, above = returns._xirr_npv(flows, root - step), returns._xirr_npv(flows, root + step)

        assert below > 0.0 > above and below * above == 0.0
        assert returns._changes_sign_at(flows, root) and _npv_changes_sign(flows, root)
        assert str(returns._rate_decimal(root)) == "9.000000" == _one_deposit_rate(VANISHING_NPV, day)

    def test_a_false_root_gives_way_to_the_true_root(self):
        """The 1900 case (opening value 0). On 4, 9 and 10 July HEAD's scan saw no sign change around the true root (the
        NPVs at the grid points around it are below 1e-180, their product 0.0, though far above the noise floor and of the
        signs the NPV has at 60 digits) and kept the exact zero of the grid nearest 0.1, 379.189396, where every term
        underflows. P1b sees the sign change, and the true root is nearer 0.1:
        116.999874, 131.184839 and 29.268301, the closed forms. On 5-8 July the true root (460 % to 1075 %) is above
        379.19, where every term underflows: P1b kept the grid point there, the cold solve's answer as on HEAD. P1c: an
        exact zero counts only where the NPV changes sign around it, and it does not at the grid point, so those days have
        no rate (the line, like the card, shows «—»)."""
        line = {point.date: point.mwrr for point in returns.period_mwrr_series(*FALSE_ROOT_1900)}
        grid_point = returns._XIRR_GRID[729] - 1.0

        for day, expected in zip(FALSE_ROOT_FIXED_DAYS, ("116.999874", "131.184839", "29.268301"), strict=True):
            flows = _point_flows(FALSE_ROOT_1900, day)
            root = returns._solve_xirr(flows, COLD_GUESS)
            low, high = _grid_interval(root)
            low_npv, high_npv = returns._xirr_npv(flows, low), returns._xirr_npv(flows, high)
            assert low_npv > 0.0 > high_npv and low_npv * high_npv == 0.0, day
            assert min(abs(low_npv), abs(high_npv)) > returns._npv_noise_floor(flows), day
            assert _exact_npv(flows, low) > 0 > _exact_npv(flows, high), day
            assert _npv_changes_sign(flows, root) and returns._xirr_npv(flows, grid_point) == 0.0, day
            assert str(line[day]) == str(returns._rate_decimal(root)) == expected == _one_deposit_rate(FALSE_ROOT_1900, day)
        for day in FALSE_ROOT_KEPT_DAYS:
            flows = _point_flows(FALSE_ROOT_1900, day)
            assert returns._xirr_npv(flows, grid_point) == 0.0 and not _npv_changes_sign(flows, grid_point), day
            assert line[day] is None and returns._solve_xirr(flows, COLD_GUESS) is None, day
            assert Decimal(_one_deposit_rate(FALSE_ROOT_1900, day)) > Decimal("379.19"), day

    @pytest.mark.parametrize("case", [PRODUCT_UNDERFLOW, VANISHING_NPV], ids=["product-underflow", "vanishing-npv"])
    def test_the_warm_path_keeps_the_interval_s_root(self, monkeypatch, case):
        """The families of weakness 1 sent P1's warm path to the whole scan (section 2): every point after the first now
        reads its interval and keeps the root there, which is the cold solve's (section 2's bit-for-bit test)."""
        kinds, kept = _record(monkeypatch, case, line=False)

        assert "scan-after-warm" not in kinds and kinds["warm-interval"] >= 10, kinds
        assert all(rate is not None for _calls, rate in kept)

    def test_the_ill_conditioned_warm_path(self, monkeypatch):
        """Weakness 2 on the warm path. Where the warm Newton root passes HEAD's test (7 points), the interval is read and
        its Brent root kept by the bracketed verification. Where Newton stops on a root that misses it (3 points: |NPV|
        0.0039 or 0.0156 against about 0.0021; Newton's answer keeps HEAD's test alone), Newton from the previous rate
        gives nothing and the whole scan runs, which finds the root by the same verification. Every point has its rate,
        the cold solve's (section 2), and 7 of the 10 pass only by the sign test."""
        kinds, kept = _record(monkeypatch, ILL_CONDITIONED, line=False)

        through_the_interval = [calls for calls, _rate in kept if calls[-1].name == "_bracketed_xirr_at"]
        refused_newton = [calls for calls, _rate in kept if [(call.name, call.result is None) for call in calls] == [("_newton_xirr", True), ("_newton_xirr", True), ("_bracketed_xirr", False)]]
        assert len(through_the_interval) == 7 and len(refused_newton) == 3, kinds
        for calls in refused_newton:
            flows, stop = calls[0].flows, _scipy_newton(calls[0].flows, calls[1].start)
            assert abs(returns._xirr_npv(flows, stop)) > returns._XIRR_ROOT_TOLERANCE * _scale(flows) and _npv_changes_sign(flows, stop)
            assert returns._is_bracketed_xirr_root(flows, calls[-1].result, _scale(flows))
        assert all(rate is not None for _calls, rate in kept)
        by_the_sign_test = [rate for calls, rate in kept[1:] if not returns._is_xirr_root(calls[0].flows, rate, _scale(calls[0].flows))]
        assert len(by_the_sign_test) == 7 and all(returns._is_bracketed_xirr_root(calls[0].flows, rate, _scale(calls[0].flows)) for calls, rate in kept)


class TestWhatP1bLeavesAsItWas:
    """Two answers of P1b's first design that were not HEAD's, and should not have changed (the developer's review of the
    P1b harness): green on HEAD (325e78fc8), red on that first design.

    1. A sign in the noise. Reading the signs of two NPVs, it trusted the sign of a subnormal one, which is rounding: on
       a period opening at value 0 in 1720, it bracketed a root where there is none. ``_opposite_signs`` now asks both
       NPVs to be above ``_npv_noise_floor``.
    2. Newton's verification. With the sign test in ``_is_xirr_root``, Newton from 0.1 kept an ill-conditioned root far
       from 0.1 where HEAD refused it and the scan answered the root nearest 0.1. The sign test is now only for roots the
       bracketing found (``_is_bracketed_xirr_root``): with several roots, which one the solve returns stays HEAD's."""

    def test_a_sign_in_the_noise_brackets_nothing(self):
        """``SUBNORMAL_NOISE``: in the grid interval [11.589254, 12.182567] the float NPVs are 1.6e-314 and −1.8e-320, of
        opposite signs, but the second is below the noise floor and its sign is rounding (at 60 digits both are
        positive): the interval brackets nothing, and the answer is never 12.182509, the Brent stop between them
        (``TestChangesSignAt``). What the solve answers instead was HEAD's false exact zero, which P1c removes: section 7."""
        flows = _point_flows(SUBNORMAL_NOISE, SUBNORMAL_NOISE_DAY)
        low, high = _grid_interval(12.0)
        low_npv, high_npv = returns._xirr_npv(flows, low), returns._xirr_npv(flows, high)

        assert low_npv > 0.0 > high_npv and abs(high_npv) < returns._npv_noise_floor(flows)
        assert _exact_npv(flows, low) > 0 and _exact_npv(flows, high) > 0
        assert not returns._opposite_signs(low_npv, high_npv, returns._npv_noise_floor(flows))
        assert returns._bracketed_xirr_at(flows, 12.0, _scale(flows)) is None
        assert str(returns._rate_decimal(_scan_brent(flows, low, high))) == "12.182509"
        assert returns._solve_xirr(flows, COLD_GUESS) != _scan_brent(flows, low, high)

    def test_newton_keeps_head_s_test(self):
        """``NEWTON_ILL_CONDITIONED``: Newton from 0.1 stops on −0.754735, a true root that HEAD's test refuses (|NPV| =
        1582); the scan runs, and the answer is its root nearest 0.1, −0.019580, as on HEAD. Card and plain series: the
        line has no value there (more came out than went in)."""
        flows = _point_flows(NEWTON_ILL_CONDITIONED, NEWTON_ILL_CONDITIONED_DAY)
        navs, cash_flows = NEWTON_ILL_CONDITIONED
        stop = _scipy_newton(flows, COLD_GUESS)
        scanned = returns._bracketed_xirr(flows, COLD_GUESS, _scale(flows))

        assert _sign_changes(flows) == 3
        assert str(returns._rate_decimal(stop)) == "-0.754735" and _npv_changes_sign(flows, stop)
        assert returns._newton_xirr(flows, COLD_GUESS, _scale(flows)) is None
        assert str(returns._rate_decimal(scanned)) == "-0.019580" and _npv_changes_sign(flows, scanned)
        assert returns._solve_xirr(flows, COLD_GUESS) == scanned
        assert returns.calculate_mwrr(cash_flows, navs[0].nav, navs[1].nav, navs[0].date, navs[1].date).mwrr == Decimal("-0.019580")
        assert [str(point.mwrr) for point in returns.calculate_mwrr_series(*NEWTON_ILL_CONDITIONED)] == ["-0.019580"]
        assert returns.period_mwrr(navs, cash_flows, navs[1].date, navs[1].nav).mwrr is None


# =============================================================================
# 7. The false exact zero, removed (P1c)
# =============================================================================


class TestTheFalseExactZeroGivesWay:
    """P1c: the scan and ``_bracketed_xirr_at`` keep a grid point whose NPV is exactly 0.0 only where the NPV changes
    sign around it (``_changes_sign_at``). On a period that opens at value 0, far from t=0 every NPV term underflows,
    and the NPV is exactly 0.0 at grid rates that solve nothing: HEAD (and P1b) returned the one nearest 0.1. The 1900
    case's 5-8 July are in section 6; ``test_mwrr_false_grid_zero.py`` holds the solver's own cases."""

    def test_the_1720_period_has_no_rate(self):
        """``SUBNORMAL_NOISE``: HEAD's card and line were 12.803843 — the Dashboard's «12.80» — the grid point
        10^(57/50) − 1 where the NPV is exactly 0.0 by underflow and does not change sign. The true root, about 4.4e7, is
        beyond the grid, so there is no rate to give: the card and the line have none."""
        flows = _point_flows(SUBNORMAL_NOISE, SUBNORMAL_NOISE_DAY)
        grid_point = returns._XIRR_GRID[657] - 1.0
        (end,) = [snapshot for snapshot in SUBNORMAL_NOISE[0] if snapshot.date == SUBNORMAL_NOISE_DAY]

        assert str(returns._rate_decimal(grid_point)) == "12.803843"
        assert returns._xirr_npv(flows, grid_point) == 0.0 and not _npv_changes_sign(flows, grid_point)
        assert returns._solve_xirr(flows, COLD_GUESS) is None
        assert returns._bracketed_xirr(flows, COLD_GUESS, _scale(flows)) is None
        assert returns._bracketed_xirr_at(flows, grid_point, _scale(flows)) is None
        assert returns.period_mwrr(*SUBNORMAL_NOISE, end.date, end.nav).mwrr is None
        assert [str(point.mwrr) for point in returns.period_mwrr_series(*SUBNORMAL_NOISE)] == ["None"]
        assert float(_one_deposit_rate(SUBNORMAL_NOISE, SUBNORMAL_NOISE_DAY)) > returns._XIRR_GRID_RATES[1]
