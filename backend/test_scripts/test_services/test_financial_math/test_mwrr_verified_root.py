"""
CP-4d (workstream J): the rate the MWRR solvers return must be a root of their XIRR NPV.

Module under test: ``backend/app/services/financial_math/returns.py``, ``calculate_mwrr`` (the
summary's MWRR) and ``calculate_mwrr_series`` (the history's).

MF-K1 (workstream MF, one root policy): the series lost its warm start, and the keyword
``use_warm_start`` with it. Every point starts from 0.1 on the flows ``calculate_mwrr`` builds (the
flows of a date summed in Decimal), so each point is the single solve on the data up to its
snapshot. The warm and cold series this file used to check side by side are now one series, and
test 6 states the identity.

The defect (investigation of 15/10, outside the worktree, ``/tmp/libreFolio_j/cp4d/``): both solve
the NPV with scipy's secant method and quantize whatever it stops on. Over 20 000 random scenarios
the single solve returned a rate that is not a root in 818 cases (758 of them exactly 0.100110, the
secant's second start point after an overflow), the warm series' last point in 691. The fix: one
verified solver for both; a rate only if it is a root, None when the NPV has none.

A root, here. The NPV is built as the module builds its flows: −NAV₀ at day 0, the flows strictly
inside the window, the final NAV plus that day's flows at the last day, each amount discounted by
``(1 + r) ** (days / 365)``. A returned rate r is a root when |NPV(r)| ≤ 1e-6 × Σ|amounts|, or when
the NPV changes sign within one quantum (1e-6) of r. The second clause is there because the module
rounds the rate to 6 decimals: where the NPV is steep (short windows, rates near −100 %) the
rounding alone moves |NPV| past the first bound. Measured before writing this file on the first 400
scenarios of the same seed: the prototype verified solver (``proto.py``) had 5 warm and 5 cold
series points past the first bound (up to 9.25e-6 × Σ|amounts|) and none past the second; the code
of the time failed exactly the same rates under either.

Tests:

1. Scenarios #1, #16 and #17 of the investigation, pinned as literal data. Their NPV has one real
   root; before CP-4d the warm series ended on it, the single solve and the cold series returned
   0.100110. Now the single solve and the series both return it.
2. Property, on a fixed-seed sample (the investigation's generator, copied; seed 20261015, its
   first ``SAMPLE_SIZE`` scenarios, #1, #16 and #17 among them): every rate the single solve and
   the series return is a root.
3. Parity, on the same sample: the single solve equals the last point of the series whenever both
   are not None.
4. No root, no rate: where the NPV never changes sign, None from the single solve and for that point
   of the series.
5. A zero rate has no sign: where the MWRR is exactly 0 (flat values, balanced flows), the single
   solve and every series point write "0.000000", never "-0.000000".
6. Prefix identity (MF-K1), on the same sample and on every hand-written data set of this file: each
   point of the series is ``calculate_mwrr`` on the data up to its snapshot — same date, same rate
   or the same None — and ``use_warm_start`` is no longer accepted.

The checks on the test's own data (one real root, no root, the sample holding the pinned
scenarios) come first and pass today. Nothing is imported from ``/tmp``. Pure: no database, no
server, no network.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.services.financial_math.returns import CashFlowInput, MWRRPoint, NAVSnapshot, calculate_mwrr, calculate_mwrr_series

# |NPV(r)| ≤ ROOT_TOLERANCE × Σ|amounts|, or a sign change of the NPV within QUANTUM of r.
ROOT_TOLERANCE = 1e-6
QUANTUM = 1e-6
# 1 + r from 1e-4 to 1e3, geometric: where the checks on the test's data look for sign changes.
RATE_GRID = tuple(10 ** (-4 + step * 7 / 700) - 1.0 for step in range(701))


# =============================================================================
# Pinned scenarios: literal data generated once from the investigation's generator
# =============================================================================

# name -> (snapshots "date NAV", flows "date amount", the one real root at 6 decimals)
PINNED = {
    "scenario-1": (
        """
        2024-01-01 1000  2024-01-31 954.40  2024-03-01 975.09  2024-03-31 1044.13  2024-04-30 1028.45  2024-05-30 958.52
        2024-06-29 954.21  2024-07-29 881.31  2024-08-28 827.64  2024-09-27 1828.88  2024-10-27 1652.94  2024-11-26 49.78
        2024-12-26 45.17  2025-01-25 41.32  2025-02-24 39.52  2025-03-26 88.85  2025-04-25 81.19  2025-05-25 18.09
        2025-06-24 18.45
        """,
        """
        2024-03-01 -100  2024-04-30 -50  2024-09-27 -1000  2024-11-26 1556.05  2025-03-26 -50  2025-05-25 63.41
        """,
        "-0.437404",
    ),
    "scenario-16": (
        """
        2024-01-01 100  2024-01-15 97.89  2024-01-29 37.02  2024-02-12 34.99  2024-02-26 33.54  2024-03-11 33.50
        2024-03-25 31.76  2024-04-08 34.46  2024-04-22 32.84  2024-05-06 35.77  2024-05-20 4.75  2024-06-03 5.17
        2024-06-17 5.79  2024-07-01 5.54  2024-07-15 5.62  2024-07-29 5.86  2024-08-12 6.03  2024-08-26 1006.65
        2024-09-09 907.80  2024-09-23 817.38  2024-10-07 894.54  2024-10-21 933.54  2024-11-04 911.98  2024-11-18 1838.93
        2024-12-02 2025.03  2024-12-16 1941.40  2024-12-30 2128.16  2025-01-13 2301.82  2025-01-27 2106.40  2025-02-10 2182.02
        2025-02-24 2077.94  2025-03-10 2433.32  2025-03-24 2594.41  2025-04-07 2425.77  2025-04-21 7377.01  2025-05-05 6640.78
        2025-05-19 6210.46  2025-06-02 6566.32  2025-06-16 6375.90
        """,
        """
        2024-01-29 53.49  2024-05-20 30.98  2024-08-26 -1000  2024-11-18 -1000  2025-03-10 -500  2025-04-21 -5000
        """,
        "-0.430962",
    ),
    "scenario-17": (
        """
        2024-01-01 1000  2024-01-08 914.60  2024-01-15 904.72  2024-01-22 840.30  2024-01-29 813.75  2024-02-05 909.20
        2024-02-12 75.67  2024-02-19 83.62  2024-02-26 77.81  2024-03-04 70.41  2024-03-11 74.82  2024-03-18 8.66
        2024-03-25 9.03  2024-04-01 59.92  2024-04-08 55.08  2024-04-15 55.60  2024-04-22 59.05  2024-04-29 53.20
        2024-05-06 50.92  2024-05-13 5.64  2024-05-20 5.54  2024-05-27 5.31  2024-06-03 4.86  2024-06-10 5005.35
        2024-06-17 4868.20  2024-06-24 5090.71  2024-07-01 5537.67  2024-07-08 5871.59  2024-07-15 6000.76  2024-07-22 5490.10
        2024-07-29 5384.69  2024-08-05 5189.76  2024-08-12 10703.55  2024-08-19 11599.44  2024-08-26 11143.65  2024-09-02 4046.56
        2024-09-09 4453.24  2024-09-16 4947.10  2024-09-23 4951.55  2024-09-30 9805.48  2024-10-07 9972.99  2024-10-14 2380.75
        2024-10-21 2245.52  2024-10-28 359.79  2024-11-04 397.20  2024-11-11 393.27  2024-11-18 422.65  2024-11-25 1431.53
        2024-12-02 1600.31  2024-12-09 1643.36  2024-12-16 1699.07  2024-12-23 1532.90  2024-12-30 1394.33
        """,
        """
        2024-02-12 870.17  2024-03-18 59.56  2024-04-01 -50  2024-05-13 42.54  2024-06-10 -5000  2024-06-24 -500
        2024-08-12 -5000  2024-08-26 -500  2024-09-02 6019.50  2024-09-30 -5000  2024-10-07 -1000  2024-10-14 6811.35
        2024-10-28 1903.02  2024-11-04 -50  2024-11-25 -1000
        """,
        "-0.560105",
    ),
}
# Where each pinned scenario sits in the sample.
PINNED_INDEX = {"scenario-1": 1, "scenario-16": 16, "scenario-17": 17}


def _pairs(text: str) -> list[tuple[date, Decimal]]:
    words = text.split()
    return [(date.fromisoformat(day), Decimal(value)) for day, value in zip(words[::2], words[1::2], strict=True)]


def _pinned(name: str) -> tuple[list[NAVSnapshot], list[CashFlowInput], Decimal]:
    navs_text, flows_text, root = PINNED[name]
    return [NAVSnapshot(day, nav) for day, nav in _pairs(navs_text)], [CashFlowInput(day, amount) for day, amount in _pairs(flows_text)], Decimal(root)


# =============================================================================
# The NPV, built as the module builds its flows
# =============================================================================


def _single_flows(cash_flows: list[CashFlowInput], initial_nav: Decimal, final_nav: Decimal, start_date: date, end_date: date) -> list[tuple[float, float]]:
    """The flows ``calculate_mwrr`` solves: (days from the start, amount). One per cash flow: every data
    set of this file has at most one flow per date, where MF-K1's per-date sum changes nothing."""
    total_days = (end_date - start_date).days
    final_day_cf = sum(float(cf.amount) for cf in cash_flows if (cf.date - start_date).days == total_days)
    flows = [(0.0, -float(initial_nav)), (float(total_days), float(final_nav) + final_day_cf)]
    flows += [(float((cf.date - start_date).days), float(cf.amount)) for cf in cash_flows if 0 < (cf.date - start_date).days < total_days]
    return flows


def _summary_flows(navs: list[NAVSnapshot], cash_flows: list[CashFlowInput]) -> list[tuple[float, float]]:
    """The flows of the single solve as the summary calls it: first and last snapshot."""
    return _single_flows(cash_flows, navs[0].nav, navs[-1].nav, navs[0].date, navs[-1].date)


def _summary_mwrr(navs: list[NAVSnapshot], cash_flows: list[CashFlowInput]) -> Decimal | None:
    return calculate_mwrr(cash_flows, navs[0].nav, navs[-1].nav, navs[0].date, navs[-1].date).mwrr


def _series_point_flows(nav_snapshots: list[NAVSnapshot], cash_flows: list[CashFlowInput]) -> list[tuple[date, list[tuple[float, float]]]]:
    """For each point of ``calculate_mwrr_series`` (each snapshot after the first, by date), the
    flows it solves, as it builds them."""
    sorted_navs = sorted(nav_snapshots, key=lambda snapshot: snapshot.date)
    cf_by_date: dict[date, Decimal] = {}
    for cf in cash_flows:
        cf_by_date[cf.date] = cf_by_date.get(cf.date, Decimal("0")) + cf.amount
    start_date, initial_nav = sorted_navs[0].date, sorted_navs[0].nav
    points = []
    for snapshot in sorted_navs[1:]:
        total_days = (snapshot.date - start_date).days
        flows = [(0.0, -float(initial_nav)), (float(total_days), float(snapshot.nav) + float(cf_by_date.get(snapshot.date, Decimal("0"))))]
        flows += [(float((cf_date - start_date).days), float(amount)) for cf_date, amount in cf_by_date.items() if 0 < (cf_date - start_date).days < total_days]
        points.append((snapshot.date, flows))
    return points


def _npv(flows: list[tuple[float, float]], rate: float) -> float:
    """Σ amount / (1 + r) ** (days / 365); infinite where it cannot be evaluated (1 + r ≤ 0, overflow)."""
    base = 1.0 + rate
    if base <= 0.0:
        return math.inf
    try:
        return math.fsum(amount / base ** (days / 365.0) for days, amount in flows)
    except (OverflowError, ZeroDivisionError, ValueError):
        return math.inf


def _is_root(flows: list[tuple[float, float]], rate: Decimal) -> bool:
    """|NPV(r)| ≤ ROOT_TOLERANCE × Σ|amounts|, or the NPV changes sign within QUANTUM of r."""
    value = _npv(flows, float(rate))
    if math.isfinite(value) and abs(value) <= ROOT_TOLERANCE * math.fsum(abs(amount) for _, amount in flows):
        return True
    below, above = _npv(flows, float(rate) - QUANTUM), _npv(flows, float(rate) + QUANTUM)
    return math.isfinite(below) and math.isfinite(above) and below * above <= 0.0


def _npv_on_grid(flows: list[tuple[float, float]]) -> list[float]:
    """The NPV at every rate of RATE_GRID where it is finite."""
    return [value for value in (_npv(flows, rate) for rate in RATE_GRID) if math.isfinite(value)]


def _sign_changes(values: list[float]) -> int:
    return sum(1 for left, right in zip(values, values[1:], strict=False) if left * right < 0.0)


# =============================================================================
# The sample: the investigation's generator, copied
# =============================================================================

SAMPLE_SEED = 20261015
SAMPLE_SIZE = 100


def _scenario(rng: random.Random) -> tuple[list[NAVSnapshot], list[CashFlowInput]]:
    """``scenario()`` of the investigation (``/tmp/libreFolio_j/cp4d/search.py``), as written: the
    same draws in the same order, so seed 20261015 gives its scenarios #0, #1, …"""
    start = date(2024, 1, 1)
    days = rng.choice([180, 365, 540, 730])
    step = rng.choice([7, 14, 30])
    nav = Decimal(rng.choice([100, 1000, 10000]))
    navs = [NAVSnapshot(start, nav)]
    flows = []
    for d in range(step, days + 1, step):
        nav = (nav * Decimal(str(round(rng.uniform(0.9, 1.12), 4)))).quantize(Decimal("0.01"))
        day = start + timedelta(days=d)
        r = rng.random()
        if r < 0.12 and nav > 10:  # large withdrawal: the investor takes most of it out
            amount = (nav * Decimal(str(round(rng.uniform(0.5, 0.98), 3)))).quantize(Decimal("0.01"))
            nav -= amount
            flows.append(CashFlowInput(day, amount))
        elif r < 0.24:  # deposit
            amount = Decimal(rng.choice([50, 100, 500, 1000, 5000]))
            nav += amount
            flows.append(CashFlowInput(day, -amount))
        navs.append(NAVSnapshot(day, max(nav, Decimal("0.01"))))
    return navs, flows


@dataclass(frozen=True)
class _Solved:
    """One scenario of the sample with what the two solves return."""

    index: int
    navs: list[NAVSnapshot]
    flows: list[CashFlowInput]
    single: Decimal | None
    series: list[MWRRPoint]


@pytest.fixture(scope="module")
def sample() -> list[_Solved]:
    """The first SAMPLE_SIZE scenarios of seed SAMPLE_SEED, each solved once, as the summary and the history call the module."""
    rng = random.Random(SAMPLE_SEED)
    solved = []
    for index in range(SAMPLE_SIZE):
        navs, flows = _scenario(rng)
        series = calculate_mwrr_series(navs, flows)
        solved.append(_Solved(index=index, navs=navs, flows=flows, single=_summary_mwrr(navs, flows), series=series))
    return solved


# =============================================================================
# 1. The pinned scenarios
# =============================================================================


class TestPinnedScenarios:
    """Scenarios #1, #16 and #17 of the investigation. Their NPV has one real root; before CP-4d the
    warm series ended on it, while the single solve and the cold series stopped on 0.100110."""

    @pytest.mark.parametrize("name", PINNED)
    def test_the_npv_has_one_real_root(self, name):
        """On the test's own data: the expected rate is a root, the only sign change of the NPV
        between −99.99 % and +99 900 %, and today's 0.100110 is not one."""
        navs, flows, root = _pinned(name)
        summary_flows = _summary_flows(navs, flows)

        assert _is_root(summary_flows, root)
        assert _sign_changes(_npv_on_grid(summary_flows)) == 1
        assert not _is_root(summary_flows, Decimal("0.100110"))

    def test_the_sample_holds_the_pinned_scenarios(self, sample):
        """The copied generator gives scenarios #1, #16 and #17 exactly as pinned."""
        for name, index in PINNED_INDEX.items():
            navs, flows, _root = _pinned(name)
            assert (sample[index].navs, sample[index].flows) == (navs, flows), name

    @pytest.mark.parametrize("name", PINNED)
    def test_the_single_solve_returns_the_root(self, name):
        navs, flows, root = _pinned(name)

        assert _summary_mwrr(navs, flows) == root

    @pytest.mark.parametrize("name", PINNED)
    def test_the_series_ends_on_the_root(self, name):
        navs, flows, root = _pinned(name)

        assert calculate_mwrr_series(navs, flows)[-1].mwrr == root


# =============================================================================
# 2. Property: every rate returned is a root
# =============================================================================


class TestEveryRateIsARoot:
    """On the sample, every rate the single solve and the series return is a root of its NPV.

    Red before CP-4d: the secant method stopped on rates that are not roots, 0.100110 above all."""

    def test_every_single_solve(self, sample):
        returned = [case for case in sample if case.single is not None]
        failures = [f"#{case.index}: {case.single}" for case in returned if not _is_root(_summary_flows(case.navs, case.flows), case.single)]

        assert returned, "the sample must have rates to check"
        assert not failures, f"{len(failures)} of {len(returned)} single solves return a rate that is not a root: {failures[:10]}"

    def test_every_series_point(self, sample):
        checked, failures = 0, []
        for case in sample:
            series = case.series
            points = _series_point_flows(case.navs, case.flows)
            assert [point.date for point in series] == [day for day, _flows in points], f"#{case.index}: one point per snapshot after the first"
            for point, (_day, flows) in zip(series, points, strict=True):
                if point.mwrr is None:
                    continue
                checked += 1
                if not _is_root(flows, point.mwrr):
                    failures.append(f"#{case.index} {point.date}: {point.mwrr}")

        assert checked, "the sample must have rates to check"
        assert not failures, f"{len(failures)} of {checked} series points are not roots: {failures[:10]}"


# =============================================================================
# 3. Parity: the summary's rate is the history's last point
# =============================================================================


class TestSingleSolveAndSeriesAgree:
    """On the sample, the single solve (the summary) equals the last point of the series (the
    history) whenever both are not None."""

    def test_the_last_point_equals_the_single_solve(self, sample):
        compared, mismatches = 0, []
        for case in sample:
            series = case.series
            last = series[-1].mwrr if series else None
            if case.single is None or last is None:
                continue
            compared += 1
            if case.single != last:
                mismatches.append(f"#{case.index}: single {case.single}, series {last}")

        assert compared, "the sample must have pairs to compare"
        assert not mismatches, f"{len(mismatches)} of {compared} scenarios: {mismatches[:10]}"


# =============================================================================
# 4. No root, no rate
# =============================================================================

# name -> (snapshots "date NAV", flows "date amount")
NO_ROOT = {
    # −1000 at day 0, −500 at days 30 and 60, 50 − 200 at day 90: every flow negative.
    "every-flow-negative": ("2025-01-01 1000  2025-01-31 1450  2025-03-02 1700  2025-04-01 50", "2025-01-31 -500  2025-03-02 -500  2025-04-01 -200"),
    # A total loss: −1000 at day 0, −200 at day 30, nothing left at day 90.
    "total-loss": ("2025-01-01 1000  2025-01-31 600  2025-04-01 0", "2025-01-31 -200"),
}


def _no_root(name: str) -> tuple[list[NAVSnapshot], list[CashFlowInput]]:
    navs_text, flows_text = NO_ROOT[name]
    return [NAVSnapshot(day, nav) for day, nav in _pairs(navs_text)], [CashFlowInput(day, amount) for day, amount in _pairs(flows_text)]


class TestNoRootNoRate:
    """Where the NPV never changes sign there is no rate: None from the single solve, None for that
    point of the series. The earlier points of these series do have a root.

    Green today (the secant gives up on these): they keep the verified solver from inventing a rate."""

    @pytest.mark.parametrize("name", NO_ROOT)
    def test_the_npv_never_changes_sign(self, name):
        """On the test's own data: the NPV is negative wherever it can be evaluated on the grid."""
        navs, flows = _no_root(name)
        values = _npv_on_grid(_summary_flows(navs, flows))

        assert values
        assert all(value < 0.0 for value in values)

    @pytest.mark.parametrize("name", NO_ROOT)
    def test_no_rate_from_the_single_solve(self, name):
        navs, flows = _no_root(name)

        assert _summary_mwrr(navs, flows) is None

    @pytest.mark.parametrize("name", NO_ROOT)
    def test_no_rate_for_that_point_of_the_series(self, name):
        navs, flows = _no_root(name)

        assert calculate_mwrr_series(navs, flows)[-1].mwrr is None


# =============================================================================
# 5. A zero rate has no sign
# =============================================================================

# name -> (snapshots "date NAV", flows "date amount"): the NPV is exactly 0 at r = 0 for the summary
# and for every point of the series, so every rate here is 0.
ZERO_RATE = {
    # 1000 → 1000 over a year, nothing in between.
    "flat-one-year": ("2025-01-01 1000  2026-01-01 1000", ""),
    # The same year with a snapshot every month, all at 1000: the series solves 12 points.
    "flat-monthly": (
        "2025-01-01 1000  2025-02-01 1000  2025-03-01 1000  2025-04-01 1000  2025-05-01 1000  2025-06-01 1000  2025-07-01 1000  2025-08-01 1000  2025-09-01 1000  2025-10-01 1000  2025-11-01 1000  2025-12-01 1000  2026-01-01 1000",
        "",
    ),
    # 500 deposited on day 100 and taken out on day 200; the value is always the money put in.
    "balanced-flows": ("2025-01-01 1000  2025-04-11 1500  2025-07-20 1000  2026-01-01 1000", "2025-04-11 -500  2025-07-20 500"),
}


def _zero_rate(name: str) -> tuple[list[NAVSnapshot], list[CashFlowInput]]:
    navs_text, flows_text = ZERO_RATE[name]
    return [NAVSnapshot(day, nav) for day, nav in _pairs(navs_text)], [CashFlowInput(day, amount) for day, amount in _pairs(flows_text)]


def _unsigned_zero(value: Decimal | None) -> bool:
    return value is not None and str(value) == "0.000000" and not value.is_signed()


class TestAZeroRateHasNoSign:
    """A zero rate is written "0.000000", never "-0.000000".

    The solver can stop a hair below zero (Newton's last step leaves about −1e-16 on these cases),
    and the 6-decimal quantization keeps the sign: the native-cash golden showed "-0.000000" for
    ``mwrr_annualized`` in three places. Red today."""

    @pytest.mark.parametrize("name", ZERO_RATE)
    def test_the_rate_is_exactly_zero(self, name):
        """On the test's own data: the NPV at r = 0 is exactly 0 for the summary and every series point."""
        navs, flows = _zero_rate(name)

        assert _npv(_summary_flows(navs, flows), 0.0) == 0.0
        assert [_npv(point_flows, 0.0) for _day, point_flows in _series_point_flows(navs, flows)] == [0.0] * (len(navs) - 1)

    @pytest.mark.parametrize("name", ZERO_RATE)
    def test_the_single_solve_writes_zero_without_a_sign(self, name):
        navs, flows = _zero_rate(name)

        value = _summary_mwrr(navs, flows)

        assert value is not None
        assert str(value) == "0.000000", repr(value)
        assert not value.is_signed()

    @pytest.mark.parametrize("name", ZERO_RATE)
    def test_the_series_writes_zero_without_a_sign(self, name):
        """The last point, as the history ends; then every point, whose rate is 0 as well."""
        navs, flows = _zero_rate(name)

        series = calculate_mwrr_series(navs, flows)

        assert _unsigned_zero(series[-1].mwrr), f"last point: {series[-1].mwrr!r}"
        assert [f"{point.date}: {point.mwrr!r}" for point in series if not _unsigned_zero(point.mwrr)] == []


# =============================================================================
# 6. Prefix identity: each point of the series is the single solve up to its snapshot (MF-K1)
# =============================================================================


def _single_solves_on_prefixes(navs: list[NAVSnapshot], cash_flows: list[CashFlowInput]) -> list[MWRRPoint]:
    """``calculate_mwrr`` from the first snapshot to each later one, by date: what MF-K1 says the series is."""
    ordered = sorted(navs, key=lambda snapshot: snapshot.date)
    return [calculate_mwrr(cash_flows, ordered[0].nav, snapshot.nav, ordered[0].date, snapshot.date) for snapshot in ordered[1:]]


# Every hand-written data set of this file: name -> (snapshots, flows).
HAND_WRITTEN = {
    **{f"pinned/{name}": _pinned(name)[:2] for name in PINNED},
    **{f"no-root/{name}": _no_root(name) for name in NO_ROOT},
    **{f"zero-rate/{name}": _zero_rate(name) for name in ZERO_RATE},
}


class TestEverySeriesPointIsTheSingleSolveOnItsPrefix:
    """MF-K1, one root policy: every point of ``calculate_mwrr_series`` starts from 0.1 on the flows
    ``calculate_mwrr`` builds, so it equals ``calculate_mwrr`` on the same data up to its snapshot —
    same date, and the same rate or the same None.

    Before MF-K1, red on the sample only where the warm start (the previous point's rate as the
    starting guess, the adaptive cap, the retry from 0.1 that prefers the smaller |r|) landed on
    another root, or another quantum of the same one, than a start from 0.1: the sample has one flow
    per date, so a start from 0.1 saw exactly the single solve's flows."""

    def test_every_point_equals_the_single_solve_on_its_prefix(self, sample):
        compared, mismatches = 0, []
        for case in sample:
            expected = _single_solves_on_prefixes(case.navs, case.flows)
            assert [point.date for point in case.series] == [point.date for point in expected], f"#{case.index}: one point per snapshot after the first"
            for point, single in zip(case.series, expected, strict=True):
                compared += 1
                if point.mwrr != single.mwrr:
                    mismatches.append(f"#{case.index} {point.date}: series {point.mwrr}, single {single.mwrr}")

        assert compared, "the sample must have points to compare"
        assert not mismatches, f"{len(mismatches)} of {compared} series points differ from the single solve on their prefix: {mismatches[:10]}"

    @pytest.mark.parametrize("name", HAND_WRITTEN)
    def test_every_point_of_the_hand_written_data(self, name):
        navs, flows = HAND_WRITTEN[name]

        assert calculate_mwrr_series(navs, flows) == _single_solves_on_prefixes(navs, flows)

    def test_the_warm_start_keyword_is_gone(self):
        """One root policy, no switch back to the warm start."""
        navs, flows = _zero_rate("flat-one-year")

        with pytest.raises(TypeError):
            calculate_mwrr_series(navs, flows, use_warm_start=True)
