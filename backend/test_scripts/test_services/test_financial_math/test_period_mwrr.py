"""
MF-K1 (workstream MF, developer's decision D-MF5 (b)): the period MWRR — the Dashboard card's rule,
moved into the house — and its history line, which has no value where the card has none.

Module under test: ``backend/app/services/financial_math/returns.py``. Two new functions:

* ``period_mwrr(nav_snapshots, cash_flows, end_date, end_nav) -> MWRRPoint``: the card's MWRR. No
  value (``MWRRPoint(end_date, None)``) without snapshots, without cash flows, with an end NAV ≤ 0,
  or with a net invested ≤ 0. Otherwise ``calculate_mwrr(cash_flows, first.nav, end_nav,
  first.date, end_date)``, ``first`` being the first snapshot by date. The net invested is the
  capital that solve sees: ``first.nav + Σ −amount`` over the flows with ``first.date < date ≤
  end_date`` (deposits are negative). A flow of the first date is inside ``first.nav``, and a flow
  before it is outside the window, so neither counts — for the solve as for the guard.
* ``period_mwrr_series(nav_snapshots, cash_flows) -> list[MWRRPoint]``: the line. ``[]`` with fewer
  than two snapshots or without cash flows; otherwise one point per snapshot after the first (by
  date), each ``period_mwrr`` of the snapshots up to and including it, on its date and NAV. Its last
  point is the card.

The rule as the Dashboard wrote it (``portfolio_service.py``, the summary's performance block): an
MWRR only with snapshots and flows in the period, an end NAV > 0 and a net invested > 0, the start
NAV being the first snapshot's. The history (``calculate_mwrr_series``) had no such guard: on a
period where more came out than went in, the line had values the card does not show.

MF-K1 follow-up, the capital the solve sees. The first version of the guard took the net invested as
−Σ amount over every flow dated on or before ``end_date``. A period that ``rebase_to_period`` opens
before the portfolio's first day starts at NAV 0 and drops the first day's deposit (it is inside the
first snapshot's NAV), so that guard saw no capital and took the value away from a portfolio with a
single deposit — the card, and with D-MF5 the whole line. Section 7 pins the new rule: the young
portfolio, flows before the first snapshot ignored in both directions, the first NAV rather than the
first day's flows, and a rebase inside the history, where both rules agree.

Also from MF-K1, checked here through both functions:

* one flow builder: the flows of a date are summed in Decimal before the conversion to float, in
  ``calculate_mwrr`` as in ``calculate_mwrr_series`` (before MF-K1 ``calculate_mwrr`` passed them
  one by one, and summed those of the end date as floats);
* one root policy: every point of ``calculate_mwrr_series`` starts from 0.1, so it is
  ``calculate_mwrr`` on the data up to its snapshot;
* the edges of a period: a flow on the end date joins the final value, and a flow on the first
  snapshot's date is already inside the first NAV and is not counted again (``rebase_to_period``
  documents why).

Expected rates are literal only where a closed form gives them: one amount in, one amount out
``days`` later, rate = (out / in) ** (365 / days) − 1, which over 365 days is exactly out / in − 1.
Elsewhere the tests assert the contract's identities, and prove on their own data that the XIRR has
a root where the rule takes the value away: the None comes from the rule, not from the solver.

Red by absence before MF-K1: ``returns.period_mwrr`` and ``returns.period_mwrr_series`` are read
while each test runs, never imported at module level, so the file collects and each test that needs
them fails on the missing attribute. ``TestOneFlowBuilder.test_one_flow_per_date_summed_in_decimal``
needs neither and was red before MF-K1 on its own (flows of a date passed one by one, and the warm
start's second guess).

Pure: no database, no server, no network.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

import pytest

from backend.app.services.financial_math import returns
from backend.app.services.financial_math.returns import CashFlowInput, MWRRPoint, NAVSnapshot, calculate_mwrr, calculate_mwrr_series

# The precision of a rate: 6 decimals, so a closed form and a solved rate agree within one quantum.
QUANTUM = 1e-6


def _navs(text: str) -> list[NAVSnapshot]:
    words = text.split()
    return [NAVSnapshot(date.fromisoformat(day), Decimal(value)) for day, value in zip(words[::2], words[1::2], strict=True)]


def _flows(text: str) -> list[CashFlowInput]:
    words = text.split()
    return [CashFlowInput(date.fromisoformat(day), Decimal(value)) for day, value in zip(words[::2], words[1::2], strict=True)]


def _closed_form(amount_in: float, amount_out: float, days: int) -> float:
    """The rate of one amount in and one amount out ``days`` later."""
    return (amount_out / amount_in) ** (365 / days) - 1


def _close_to(rate: Decimal | None, expected: float) -> bool:
    return rate is not None and abs(float(rate) - expected) <= QUANTUM


def _by_date(navs: Sequence[NAVSnapshot]) -> list[NAVSnapshot]:
    return sorted(navs, key=lambda snapshot: snapshot.date)


def _single_on_prefix(navs: Sequence[NAVSnapshot], cash_flows: Sequence[CashFlowInput], index: int) -> MWRRPoint:
    """``calculate_mwrr`` from the first snapshot to the snapshot ``index``, both by date."""
    ordered = _by_date(navs)
    return calculate_mwrr(list(cash_flows), ordered[0].nav, ordered[index].nav, ordered[0].date, ordered[index].date)


def _card_on_prefix(navs: Sequence[NAVSnapshot], cash_flows: Sequence[CashFlowInput], index: int) -> MWRRPoint:
    """``period_mwrr`` of the snapshots up to the snapshot ``index`` (by date), on its date and NAV,
    with every flow: what the line's point there must be."""
    ordered = _by_date(navs)
    return returns.period_mwrr(ordered[: index + 1], cash_flows, ordered[index].date, ordered[index].nav)


def _line(navs: Sequence[NAVSnapshot], cash_flows: Sequence[CashFlowInput]) -> list[MWRRPoint]:
    """``period_mwrr_series``, once its invariant is checked: one point per snapshot after the first,
    each the card on its prefix, the last one the card of the whole period."""
    ordered = _by_date(navs)
    line = returns.period_mwrr_series(navs, cash_flows)

    assert [point.date for point in line] == [snapshot.date for snapshot in ordered[1:]], "one point per snapshot after the first"
    assert line == [_card_on_prefix(navs, cash_flows, index) for index in range(1, len(ordered))], "each point is the card on its prefix"
    assert line[-1] == returns.period_mwrr(navs, cash_flows, ordered[-1].date, ordered[-1].nav), "the last point is the card"
    return line


def _summed_per_date(cash_flows: Sequence[CashFlowInput]) -> list[CashFlowInput]:
    totals: dict[date, Decimal] = {}
    for flow in cash_flows:
        totals[flow.date] = totals.get(flow.date, Decimal("0")) + flow.amount
    return [CashFlowInput(day, amount) for day, amount in totals.items()]


# =============================================================================
# 1. Net withdrawals: no value on the card, none on the line from that day
# =============================================================================


class TestNetWithdrawals:
    """1000 in on 1 January 2025 (inside the first NAV), 1200 on 1 April, then a withdrawal on 1 July
    that takes the net invested (the first NAV, 1000, less the withdrawal) to zero or below while the
    NAV stays positive. The card has no value; the line has its value on 1 April and none from 1 July on."""

    @pytest.mark.parametrize("withdrawal", [Decimal("1500"), Decimal("1000")], ids=["more-out-than-in", "as-much-out-as-in"])
    def test_no_value_from_the_withdrawal_on(self, withdrawal):
        navs = [
            NAVSnapshot(date(2025, 1, 1), Decimal("1000")),
            NAVSnapshot(date(2025, 4, 1), Decimal("1200")),
            NAVSnapshot(date(2025, 7, 1), Decimal("1700") - withdrawal),
            NAVSnapshot(date(2025, 10, 1), Decimal("1750") - withdrawal),
            NAVSnapshot(date(2026, 1, 1), Decimal("1800") - withdrawal),
        ]
        flows = [CashFlowInput(date(2025, 1, 1), Decimal("-1000")), CashFlowInput(date(2025, 7, 1), withdrawal)]

        # On the test's own data: the NAV stays positive and the XIRR has a root at every point, the
        # last included. The None below is the rule's.
        assert all(snapshot.nav > 0 for snapshot in navs)
        assert all(_single_on_prefix(navs, flows, index).mwrr is not None for index in range(1, len(navs)))

        assert returns.period_mwrr(navs, flows, date(2026, 1, 1), navs[-1].nav) == MWRRPoint(date=date(2026, 1, 1), mwrr=None)

        line = _line(navs, flows)
        # 1 April, day 90: 1000 in, 1200 out. The withdrawal comes after it and does not count.
        assert line[0] == _single_on_prefix(navs, flows, 1)
        assert _close_to(line[0].mwrr, _closed_form(1000, 1200, 90)), line[0]
        assert [point.mwrr for point in line[1:]] == [None, None, None]


# =============================================================================
# 2. A NAV at or below zero: no value at that point
# =============================================================================


class TestANavNotAboveZero:
    @pytest.mark.parametrize("nav", [Decimal("0"), Decimal("-50")], ids=["zero", "negative"])
    def test_a_point_whose_nav_is_not_positive_has_no_value(self, nav):
        """1000 in on 1 January, 600 out on 1 April (NAV 450 after it), the NAV at ``nav`` on 1 July,
        1000 in on 1 August, 1050 on 1 October. The net invested stays positive (400, then 1400): only
        the NAV of 1 July takes that point's value away, and the next point has its value again."""
        navs = [
            NAVSnapshot(date(2025, 1, 1), Decimal("1000")),
            NAVSnapshot(date(2025, 4, 1), Decimal("450")),
            NAVSnapshot(date(2025, 7, 1), nav),
            NAVSnapshot(date(2025, 10, 1), Decimal("1050")),
        ]
        flows = [
            CashFlowInput(date(2025, 1, 1), Decimal("-1000")),
            CashFlowInput(date(2025, 4, 1), Decimal("600")),
            CashFlowInput(date(2025, 8, 1), Decimal("-1000")),
        ]

        # On the test's own data: −1000 at day 0, +600 at day 90, ``nav`` at day 181 — the NPV
        # changes sign, so the XIRR has a root there. The None below is the rule's.
        assert _single_on_prefix(navs, flows, 2).mwrr is not None

        assert returns.period_mwrr(navs[:3], flows, date(2025, 7, 1), nav) == MWRRPoint(date=date(2025, 7, 1), mwrr=None)

        line = _line(navs, flows)
        # 1 April, day 90: 1000 in, 450 + 600 out.
        assert _close_to(line[0].mwrr, _closed_form(1000, 1050, 90)), line[0]
        assert line[1] == MWRRPoint(date=date(2025, 7, 1), mwrr=None)
        assert line[2] == _single_on_prefix(navs, flows, 3)
        assert line[2].mwrr is not None

    @pytest.mark.parametrize("end_nav", [Decimal("0"), Decimal("-0.01")], ids=["zero", "negative"])
    def test_the_card_reads_the_end_nav_it_is_given(self, end_nav):
        """The card's end NAV is its argument, not the last snapshot's: 1000 in, 600 out on 2 July,
        and an end NAV at or below zero on 1 January 2026 give no value, though the XIRR has a root;
        an end NAV of 500 gives the single solve's."""
        navs = [NAVSnapshot(date(2025, 1, 1), Decimal("1000")), NAVSnapshot(date(2025, 7, 2), Decimal("450")), NAVSnapshot(date(2026, 1, 1), Decimal("500"))]
        flows = [CashFlowInput(date(2025, 1, 1), Decimal("-1000")), CashFlowInput(date(2025, 7, 2), Decimal("600"))]

        assert calculate_mwrr(flows, Decimal("1000"), end_nav, date(2025, 1, 1), date(2026, 1, 1)).mwrr is not None
        assert returns.period_mwrr(navs, flows, date(2026, 1, 1), end_nav) == MWRRPoint(date=date(2026, 1, 1), mwrr=None)

        card = returns.period_mwrr(navs, flows, date(2026, 1, 1), Decimal("500"))
        assert card == calculate_mwrr(flows, Decimal("1000"), Decimal("500"), date(2025, 1, 1), date(2026, 1, 1))
        assert card.mwrr is not None


# =============================================================================
# 3. Nothing to measure
# =============================================================================


class TestNothingToMeasure:
    NAVS = "2025-01-01 1000  2025-07-02 1040  2026-01-01 1080"

    def test_no_cash_flows(self):
        """Without flows there is no card and no line, though 1000 → 1080 over 365 days solves to 8 %."""
        navs = _navs(self.NAVS)

        assert calculate_mwrr([], Decimal("1000"), Decimal("1080"), date(2025, 1, 1), date(2026, 1, 1)).mwrr == Decimal("0.080000")

        assert returns.period_mwrr(navs, [], date(2026, 1, 1), Decimal("1080")) == MWRRPoint(date=date(2026, 1, 1), mwrr=None)
        assert returns.period_mwrr_series(navs, []) == []

    def test_no_snapshots(self):
        flows = _flows("2025-01-01 -1000")

        assert returns.period_mwrr([], flows, date(2026, 1, 1), Decimal("1080")) == MWRRPoint(date=date(2026, 1, 1), mwrr=None)
        assert returns.period_mwrr_series([], flows) == []

    def test_one_snapshot_draws_no_line(self):
        assert returns.period_mwrr_series(_navs("2025-01-01 1000"), _flows("2025-01-01 -1000")) == []


# =============================================================================
# 4. An ordinary period: deposits only, the rule never applies
# =============================================================================

# A year of monthly snapshots; 5000 in on the first date (inside the first NAV), then 1000 in three
# times: between two snapshots (15 February, 20 May) and on one (1 September, inside its NAV).
ORDINARY_NAVS = """
    2025-01-01 5000  2025-02-01 5080  2025-03-01 6150  2025-04-01 6090  2025-05-01 6230  2025-06-01 7380
    2025-07-01 7310  2025-08-01 7520  2025-09-01 8610  2025-10-01 8700  2025-11-01 8580  2025-12-01 8840
    2026-01-01 9010
"""
ORDINARY_FLOWS = "2025-01-01 -5000  2025-02-15 -1000  2025-05-20 -1000  2025-09-01 -1000"


class TestAnOrdinaryPeriod:
    def test_the_card_is_the_single_solve(self):
        navs, flows = _navs(ORDINARY_NAVS), _flows(ORDINARY_FLOWS)

        card = returns.period_mwrr(navs, flows, date(2026, 1, 1), Decimal("9010"))

        assert card == calculate_mwrr(flows, Decimal("5000"), Decimal("9010"), date(2025, 1, 1), date(2026, 1, 1))
        assert card.mwrr is not None

    def test_every_point_of_the_line_is_the_card_on_its_prefix(self):
        navs, flows = _navs(ORDINARY_NAVS), _flows(ORDINARY_FLOWS)

        line = _line(navs, flows)

        assert line == [_single_on_prefix(navs, flows, index) for index in range(1, len(navs))]
        assert all(point.mwrr is not None for point in line)

    def test_where_the_rule_never_applies_the_line_is_the_plain_series(self):
        """And the plain series is the single solve on each prefix (MF-K1, one root policy)."""
        navs, flows = _navs(ORDINARY_NAVS), _flows(ORDINARY_FLOWS)

        assert returns.period_mwrr_series(navs, flows) == calculate_mwrr_series(navs, flows)
        assert calculate_mwrr_series(navs, flows) == [_single_on_prefix(navs, flows, index) for index in range(1, len(navs))]

    def test_the_snapshots_are_taken_by_date(self):
        """The first snapshot is the earliest, whatever the order they come in."""
        navs, flows = _navs(ORDINARY_NAVS), _flows(ORDINARY_FLOWS)
        shuffled = navs[6:] + navs[:6][::-1]

        assert returns.period_mwrr(shuffled, flows, date(2026, 1, 1), Decimal("9010")) == returns.period_mwrr(navs, flows, date(2026, 1, 1), Decimal("9010"))
        assert _line(shuffled, flows) == returns.period_mwrr_series(navs, flows)


# =============================================================================
# 5. The edges of the period
# =============================================================================


class TestThePeriodEdges:
    @pytest.mark.parametrize(("end_nav", "end_flow"), [("1580", "-500"), ("580", "500")], ids=["deposit-on-the-end-date", "withdrawal-on-the-end-date"])
    def test_a_flow_on_the_end_date_joins_the_final_value(self, end_nav, end_flow):
        """1000 in on 1 January 2025; 365 days later the NAV after a flow of that day. The flow joins the
        final value: 1580 − 500 or 580 + 500, that is 1080 out for 1000 in, 8 % a year (counted the
        other way it would be +58 % or −42 %). As in ``calculate_mwrr``."""
        navs = [NAVSnapshot(date(2025, 1, 1), Decimal("1000")), NAVSnapshot(date(2025, 7, 2), Decimal("1040")), NAVSnapshot(date(2026, 1, 1), Decimal(end_nav))]
        flows = [CashFlowInput(date(2025, 1, 1), Decimal("-1000")), CashFlowInput(date(2026, 1, 1), Decimal(end_flow))]

        assert calculate_mwrr(flows, Decimal("1000"), Decimal(end_nav), date(2025, 1, 1), date(2026, 1, 1)).mwrr == Decimal("0.080000")
        assert returns.period_mwrr(navs, flows, date(2026, 1, 1), Decimal(end_nav)) == MWRRPoint(date=date(2026, 1, 1), mwrr=Decimal("0.080000"))

        line = _line(navs, flows)
        # 2 July 2025 is day 182: 1000 in, 1040 out.
        assert _close_to(line[0].mwrr, _closed_form(1000, 1040, 182)), line[0]
        assert line[1].mwrr == Decimal("0.080000")

    def test_a_flow_on_the_first_snapshot_date_is_inside_the_first_nav(self):
        """The 600 + 400 deposited on 1 January 2025 are the first snapshot's NAV: the period starts with
        −1000, once, and 1080 a year later is 8 %. Counted again it would start with −2000 (−46 %)."""
        navs = _navs("2025-01-01 1000  2026-01-01 1080")
        flows = _flows("2025-01-01 -600  2025-01-01 -400")

        card = returns.period_mwrr(navs, flows, date(2026, 1, 1), Decimal("1080"))

        assert card == MWRRPoint(date=date(2026, 1, 1), mwrr=Decimal("0.080000"))
        assert _line(navs, flows) == [card]

    def test_a_rebased_period_counts_its_opening_deposit_once(self):
        """The card's inputs come from ``rebase_to_period``: a period opened on 1 January 2025 starts with
        a synthetic deposit of that day's NAV, on that day. 2000 in, 2160 out a year later: 8 %."""
        history_navs = _navs("2024-07-01 1000  2025-01-01 2000  2025-07-02 2100  2026-01-01 2160")
        history_flows = _flows("2024-07-01 -1000  2024-10-01 -900")

        period = returns.rebase_to_period(history_navs, history_flows, date(2025, 1, 1))

        # On the test's own data: the period opens on 1 January with −2000 on that date, and nothing after.
        assert period.cash_flows == (CashFlowInput(date(2025, 1, 1), Decimal("-2000")),)
        card = returns.period_mwrr(period.nav_snapshots, period.cash_flows, date(2026, 1, 1), Decimal("2160"))
        assert card == MWRRPoint(date=date(2026, 1, 1), mwrr=Decimal("0.080000"))
        line = _line(period.nav_snapshots, period.cash_flows)
        # 2 July 2025 is day 182: 2000 in, 2100 out.
        assert _close_to(line[0].mwrr, _closed_form(2000, 2100, 182)), line[0]


# =============================================================================
# 6. The flows of one date
# =============================================================================

# Two flows on each of four dates: the first snapshot's (inside its NAV), a date between two
# snapshots (a deposit and a withdrawal), a snapshot's (inside its NAV) and the last one's.
SAME_DATE_NAVS = "2025-01-01 1000  2025-04-01 1060  2025-07-01 1450  2025-10-01 1500  2026-01-01 1300"
SAME_DATE_FLOWS = "2025-01-01 -600  2025-01-01 -400  2025-05-15 -300  2025-05-15 100  2025-07-01 -150  2025-07-01 -50  2026-01-01 250  2026-01-01 -50"


class TestOneFlowBuilder:
    def test_the_card_and_the_line_see_the_flows_of_a_date_as_their_sum(self):
        """The same answers whether a date's flows come one by one or already summed, from the card, the
        line, the single solve and the plain series alike."""
        navs, flows = _navs(SAME_DATE_NAVS), _flows(SAME_DATE_FLOWS)
        summed = _summed_per_date(flows)
        singles = [_single_on_prefix(navs, flows, index) for index in range(1, len(navs))]

        line = _line(navs, flows)

        assert all(point.mwrr is not None for point in line)
        assert line == singles
        assert line == returns.period_mwrr_series(navs, summed)
        assert singles == [_single_on_prefix(navs, summed, index) for index in range(1, len(navs))]
        assert calculate_mwrr_series(navs, flows) == singles

    def test_one_flow_per_date_summed_in_decimal(self, monkeypatch):
        """What the solver is given, by ``calculate_mwrr`` and by each point of ``calculate_mwrr_series``:
        the same flows, one per date, a date's amounts summed in Decimal before the conversion to float,
        and always the starting guess 0.1.

        −0.10 and −0.20 on 15 May sum to −0.30 in Decimal, which is −0.3 as a float; summed as floats
        they would give −0.30000000000000004. The flows of the first date are inside the first NAV
        (−1000 at day 0, once); those of the end date join the final value."""
        calls: list[tuple[list[tuple[float, float]], float]] = []

        def recording_solver(flows, x0, scale):
            calls.append((sorted(flows), x0))
            return 0.05

        # P1: a series point after the first may solve through the Newton step directly, not through _solve_xirr.
        monkeypatch.setattr(returns, "_newton_xirr", recording_solver)

        navs = _navs("2025-01-01 1000  2025-07-01 1450  2026-01-01 1300")
        flows = _flows("2025-01-01 -600  2025-01-01 -400  2025-05-15 -0.10  2025-05-15 -0.20  2025-07-01 -150  2025-07-01 -50  2026-01-01 250  2026-01-01 -50")
        may_15, july_1 = 134 / 365, 181 / 365  # days from 1 January 2025, in years
        expected = [
            # 1 July: its own two flows join its NAV, 1450 − 200.
            sorted([(0.0, -1000.0), (may_15, -0.3), (july_1, 1250.0)]),
            # 1 January 2026: 1 July is inside the window now, and the end date's flows join 1300.
            sorted([(0.0, -1000.0), (may_15, -0.3), (july_1, -200.0), (1.0, 1500.0)]),
        ]

        series = calculate_mwrr_series(navs, flows)
        series_calls = list(calls)
        calls.clear()
        singles = [_single_on_prefix(navs, flows, index) for index in (1, 2)]
        single_calls = list(calls)

        assert [solved for solved, _x0 in single_calls] == expected
        assert [solved for solved, _x0 in series_calls] == expected
        assert [x0 for _solved, x0 in single_calls + series_calls] == [0.1] * 4
        assert [point.mwrr for point in series] == [Decimal("0.050000")] * 2
        assert series == singles


# =============================================================================
# 7. The capital the solve sees (MF-K1 follow-up)
# =============================================================================


def _capital_first_guard(cash_flows: Sequence[CashFlowInput], end_date: date) -> Decimal:
    """The net invested as the first version of the guard read it: −Σ amount over the flows dated up to ``end_date``."""
    return -sum((cf.amount for cf in cash_flows if cf.date <= end_date), Decimal("0"))


def _capital_the_solve_sees(first: NAVSnapshot, cash_flows: Sequence[CashFlowInput], end_date: date) -> Decimal:
    """The net invested as the guard reads it now: the first NAV plus −Σ amount over the flows after it, up to ``end_date``."""
    return first.nav - sum((cf.amount for cf in cash_flows if first.date < cf.date <= end_date), Decimal("0"))


def _expected_line(navs: Sequence[NAVSnapshot], cash_flows: Sequence[CashFlowInput], has_value: list[bool]) -> list[MWRRPoint]:
    """The single solve on each prefix where the point has a value, None on its date where it has none."""
    singles = [_single_on_prefix(navs, cash_flows, index) for index in range(1, len(navs))]
    assert len(singles) == len(has_value), "one flag per point"
    return [single if keep else MWRRPoint(date=single.date, mwrr=None) for single, keep in zip(singles, has_value, strict=True)]


# 1000 deposited on 1 January 2025, the portfolio's first day, and nothing after; the NAV moves above
# and below the deposit.
YOUNG_NAVS = "2025-01-01 1000  2025-04-01 1050  2025-07-02 980  2026-01-01 1080"
YOUNG_FLOWS = "2025-01-01 -1000"

# A history with two deposits (1000, then 900), then two withdrawals inside the year that starts on
# 1 January 2025 (1800 on 1 July, 300 on 1 October) that take more out than the period opened with.
HISTORY_NAVS = "2024-07-01 1000  2024-10-01 1950  2025-01-01 2000  2025-04-01 2100  2025-07-01 350  2025-10-01 70  2026-01-01 75"
HISTORY_FLOWS = "2024-07-01 -1000  2024-10-01 -900  2025-07-01 1800  2025-10-01 300"


class TestTheCapitalTheSolveSees:
    """The guard's net invested is the capital the solve sees: the first snapshot's NAV (what the
    investor "buys" at the start, a deposit of that day included) plus the flows after it, up to the
    end date. Red against the first guard, −Σ amount over every flow up to the end date, except
    ``test_a_rebase_inside_the_history_is_unchanged``, where the two coincide."""

    @pytest.mark.parametrize("date_from", [date(2024, 12, 31), date(2024, 6, 1)], ids=["the-day-before", "months-before"])
    def test_a_young_portfolio_rebased_from_before_its_first_day_has_its_capital(self, date_from):
        """A period chosen before the portfolio existed: ``rebase_to_period`` opens it empty on the
        first day and drops that day's deposit, which is inside the first NAV. The solve still starts
        from the first NAV, 1000: the card has the solve's value (1080 a year later, 8 %), and every
        point of the line has one."""
        navs, flows = _navs(YOUNG_NAVS), _flows(YOUNG_FLOWS)

        period = returns.rebase_to_period(navs, flows, date_from)

        # On the test's own data: the period opens at NAV 0 on the first day, with a synthetic deposit
        # of 0 in place of the dropped 1000 and nothing after. The first guard saw no capital there;
        # the solve sees 1000.
        assert (period.start_date, period.start_nav) == (date(2025, 1, 1), Decimal("0"))
        assert period.nav_snapshots == tuple(navs)
        assert period.cash_flows == (CashFlowInput(date(2025, 1, 1), Decimal("0")),)
        assert _capital_first_guard(period.cash_flows, date(2026, 1, 1)) == 0
        assert _capital_the_solve_sees(period.nav_snapshots[0], period.cash_flows, date(2026, 1, 1)) == Decimal("1000")

        card = returns.period_mwrr(period.nav_snapshots, period.cash_flows, date(2026, 1, 1), Decimal("1080"))

        assert card == calculate_mwrr(list(period.cash_flows), Decimal("1000"), Decimal("1080"), date(2025, 1, 1), date(2026, 1, 1))
        assert card == MWRRPoint(date=date(2026, 1, 1), mwrr=Decimal("0.080000"))

        line = _line(period.nav_snapshots, period.cash_flows)
        assert all(point.mwrr is not None for point in line), line
        assert line == _expected_line(period.nav_snapshots, period.cash_flows, [True, True, True])
        # 1 April is day 90 (1000 in, 1050 out), 2 July day 182 (1000 in, 980 out).
        assert _close_to(line[0].mwrr, _closed_form(1000, 1050, 90)), line[0]
        assert _close_to(line[1].mwrr, _closed_form(1000, 980, 182)), line[1]
        assert line[2] == card

    def test_an_earlier_withdrawal_does_not_take_the_capital_away(self):
        """5000 taken out on 1 October 2024, before the first snapshot: outside the window, for the solve
        as for the guard. Without it or with it, 1000 in on 1 January 2025 and 1080 a year later: 8 %."""
        navs = _navs("2025-01-01 1000  2025-07-02 1040  2026-01-01 1080")
        later = _flows("2025-01-01 -1000")
        flows = _flows("2024-10-01 5000") + later

        # On the test's own data: the first guard counted the earlier withdrawal, −(5000 − 1000) < 0;
        # the solve never sees it.
        assert _capital_first_guard(flows, date(2026, 1, 1)) < 0
        assert [_single_on_prefix(navs, flows, index) for index in (1, 2)] == [_single_on_prefix(navs, later, index) for index in (1, 2)]

        card = returns.period_mwrr(navs, flows, date(2026, 1, 1), Decimal("1080"))

        assert card == MWRRPoint(date=date(2026, 1, 1), mwrr=Decimal("0.080000"))
        assert card == returns.period_mwrr(navs, later, date(2026, 1, 1), Decimal("1080"))
        line = _line(navs, flows)
        assert line == _line(navs, later)
        # 2 July 2025 is day 182: 1000 in, 1040 out.
        assert _close_to(line[0].mwrr, _closed_form(1000, 1040, 182)), line[0]
        assert line[1] == card

    def test_an_earlier_deposit_does_not_add_capital(self):
        """5000 put in on 1 October 2024, before the first snapshot, does not count either: the window
        opens with the first NAV, 1000, and the 1500 taken out on 1 July leaves no capital from that day
        on (1000 − 1500). The first guard counted the 5000 and kept a value to the end."""
        navs = _navs("2025-01-01 1000  2025-04-01 1200  2025-07-01 200  2026-01-01 300")
        later = _flows("2025-01-01 -1000  2025-07-01 1500")
        flows = _flows("2024-10-01 -5000") + later

        # On the test's own data: the first guard's capital stays positive (5000 + 1000 − 1500); the
        # solve never sees the 5000 and has a root at every point. The None below is the rule's.
        assert _capital_first_guard(flows, date(2026, 1, 1)) > 0
        assert [_single_on_prefix(navs, flows, index) for index in (1, 2, 3)] == [_single_on_prefix(navs, later, index) for index in (1, 2, 3)]
        assert all(_single_on_prefix(navs, flows, index).mwrr is not None for index in (1, 2, 3))

        card = returns.period_mwrr(navs, flows, date(2026, 1, 1), Decimal("300"))

        assert card == MWRRPoint(date=date(2026, 1, 1), mwrr=None)
        assert card == returns.period_mwrr(navs, later, date(2026, 1, 1), Decimal("300"))
        line = _line(navs, flows)
        assert line == _line(navs, later)
        assert line == _expected_line(navs, flows, [True, False, False])
        # 1 April is day 90: 1000 in, 1200 out.
        assert _close_to(line[0].mwrr, _closed_form(1000, 1200, 90)), line[0]

    @pytest.mark.parametrize(
        ("navs_text", "withdrawal", "has_value"),
        [
            # 1000 in, worth 1010 at the end of the day; 1005 out on 1 July leaves 5 of capital.
            ("2025-01-01 1010  2025-04-01 1050  2025-07-01 55  2026-01-01 60", "1005", [True, True, True]),
            # 1000 in, worth 990 at the end of the day; 995 out on 1 July leaves −5.
            ("2025-01-01 990  2025-04-01 1030  2025-07-01 45  2026-01-01 50", "995", [True, False, False]),
        ],
        ids=["a-gain-on-the-first-day", "a-loss-on-the-first-day"],
    )
    def test_the_capital_is_the_first_nav_not_the_first_day_flows(self, navs_text, withdrawal, has_value):
        """The first day's deposit is inside the first NAV, and the guard reads the NAV: where the two
        differ by a first day's move, the NAV decides. Each case is the other's mirror: the first guard
        read 1000 − withdrawal, and so gave the other answer from 1 July on."""
        navs = _navs(navs_text)
        flows = [CashFlowInput(date(2025, 1, 1), Decimal("-1000")), CashFlowInput(date(2025, 7, 1), Decimal(withdrawal))]

        # On the test's own data: the XIRR has a root at every point, and the two readings of the
        # capital have opposite signs from 1 July on. The None below is the rule's.
        assert all(_single_on_prefix(navs, flows, index).mwrr is not None for index in range(1, len(navs)))
        first_guard = _capital_first_guard(flows, date(2025, 7, 1))
        capital = _capital_the_solve_sees(navs[0], flows, date(2025, 7, 1))
        assert abs(first_guard) == abs(capital) == Decimal("5")
        assert (first_guard > 0) != (capital > 0)
        assert (capital > 0) == has_value[-1]

        line = _line(navs, flows)

        assert line == _expected_line(navs, flows, has_value)
        assert (returns.period_mwrr(navs, flows, date(2026, 1, 1), navs[-1].nav).mwrr is not None) == has_value[-1]

    @pytest.mark.parametrize(
        ("date_from", "has_value"),
        [
            (date(2025, 1, 1), [True, True, False, False]),
            (date(2025, 2, 15), [True, True, False, False]),
            (date(2025, 4, 1), [True, False, False]),
        ],
        ids=["on-a-snapshot", "between-snapshots", "on-a-later-snapshot"],
    )
    def test_a_rebase_inside_the_history_is_unchanged(self, date_from, has_value):
        """A period opened inside the history starts with a synthetic deposit of the opening NAV on its
        first date and keeps only the flows after it: there the capital the solve sees and the first
        guard's are the same number at every point, and so are the card and the line. Opened on
        1 January (or between snapshots, which opens it there too) the capital is 2000, 200 after the
        1800 out, −100 after the 300 out; opened on 1 April it is 2100, 300, then 0. Green against both
        guards."""
        period = returns.rebase_to_period(_navs(HISTORY_NAVS), _flows(HISTORY_FLOWS), date_from)
        first = period.nav_snapshots[0]

        # On the test's own data: the opening flow is −(the first NAV) on the first date, the earlier
        # flows are gone, and the two readings of the capital agree at every snapshot; the XIRR has a
        # root at every point and every NAV is positive, so the None below is the rule's.
        assert period.cash_flows[0] == CashFlowInput(first.date, -first.nav)
        assert period.start_nav == first.nav > 0
        assert all(flow.date > first.date for flow in period.cash_flows[1:])
        for snapshot in period.nav_snapshots[1:]:
            assert _capital_first_guard(period.cash_flows, snapshot.date) == _capital_the_solve_sees(first, period.cash_flows, snapshot.date), snapshot.date
        assert has_value == [snapshot.nav > 0 and _capital_first_guard(period.cash_flows, snapshot.date) > 0 for snapshot in period.nav_snapshots[1:]]
        assert all(_single_on_prefix(period.nav_snapshots, period.cash_flows, index).mwrr is not None for index in range(1, len(period.nav_snapshots)))

        line = _line(period.nav_snapshots, period.cash_flows)

        assert line == _expected_line(period.nav_snapshots, period.cash_flows, has_value)
        assert returns.period_mwrr(period.nav_snapshots, period.cash_flows, date(2026, 1, 1), Decimal("75")) == MWRRPoint(date=date(2026, 1, 1), mwrr=None)
