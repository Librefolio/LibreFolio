"""MF-E2b — a cash flow on a day without NAV counts on the first snapshot on or after it (``financial_math/returns.py``).

Workstream MF, lot E2b. Developer's decision A, through the coordinator (20/10, 10:39): «Il difetto è nel calcolo, non nella
transazione, che resta al suo giorno. Quando il calcolo salta un giorno senza valore, i flussi di quel giorno passano al primo
giorno calcolabile. Nell'esempio: il 7/1 dà (1500 − 500)/1000 − 1 = 0 %, e il ROI ha capitale 1500 e guadagno 0.»

THE DEFECT. ``calculate_simple_roi_series`` and ``calculate_twrr_period_series`` (so ``calculate_twrr`` and
``calculate_twrr_series``) add only the flows dated on a snapshot: a flow on a day without one is never counted, while
what it bought or sold is in the next snapshot's NAV. 10 bought at 100 on 5 Jan, 5 more at 100 on 6 Jan (no snapshot),
NAV 1 500 on 7 Jan at the same price: ROI and TWRR read +50% (``test_roi_utils.py::TestSimpleROISeries`` pinned the
dropping as documented behaviour until this lot).

THE RULE (the cure, coordinator). One rule for both functions: every flow counts on the first snapshot dated on or after
it; a flow after the last snapshot counts nowhere, as today; a flow before the first snapshot lands on the first — ROI
counts it there (today it does not), TWRR never reads the first snapshot's flow (unchanged). ``exposure_by_date`` and
``capital_by_date`` read the same moved flows. A caller with a snapshot on every flow date — the Dashboard's summary and
history — gets today's output, bit for bit.

THE ORACLE (``_oracle``): the rule in plain Decimal, reading nothing from returns.py — each flow summed, in the order
given, onto its snapshot; then today's formulas, in today's order of operations. With every flow on a snapshot date it
performs exactly today's operations, so it also serves the Dashboard guarantee, compared digit by digit
(``Decimal.as_tuple``). Elsewhere values are compared as Decimals.

Isolation: PURE — no database, server or network. Each docstring says what today's functions give (HEAD 2e23bd03c).
"""

import random
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

import pytest

from backend.app.services.financial_math.returns import CashFlowInput, NAVSnapshot, calculate_simple_roi_series, calculate_twrr, calculate_twrr_period_series, calculate_twrr_series

D = Decimal
_PCT = D("0.000001")  # six decimals, half up: returns.py's public rounding, restated
JAN_5, JAN_6, JAN_7, JAN_8, JAN_9 = (date(2025, 1, day) for day in range(5, 10))


def _oracle(navs: Sequence[tuple[date, Decimal]], flows: Sequence[tuple[date, Decimal]], *, capital: Mapping[date, Decimal] | None = None, exposure: Mapping[date, Decimal] | None = None) -> tuple[list[tuple[date, Decimal]], list[tuple[date, Decimal, Decimal, Decimal]]]:
    """(ROI points, TWRR sub-periods (date, period return, wealth index, cumulative TWRR)) of ``navs`` and ``flows`` by the rule.

    Each flow is added, in the order given, to the first snapshot on or after its date (none after the last). ROI walks the
    snapshots adding their flows: the capital is ``capital`` when given (ROI = (NAV + flows so far) / capital, 0 on 0),
    otherwise the net deposit, max(0, −flows so far) (ROI = (NAV − it) / it, 0 on 0). TWRR compounds, from the second
    snapshot, (NAV + its flows − previous NAV) / base, the base the previous NAV or ``exposure`` of the previous date, 0 on 0.
    """
    days = sorted(day for day, _ in navs)
    nav_of = dict(navs)
    on: dict[date, Decimal] = {}
    for day, amount in flows:
        target = next((snapshot for snapshot in days if snapshot >= day), None)
        if target is not None:
            on[target] = on.get(target, D("0")) + amount
    rois: list[tuple[date, Decimal]] = []
    cumulative = D("0")
    for day in days:
        cumulative += on.get(day, D("0"))
        if capital is not None:
            roi = D("0") if capital[day] == D("0") else ((nav_of[day] + cumulative) / capital[day]).quantize(_PCT, rounding=ROUND_HALF_UP)
        else:
            invested = -cumulative if cumulative < D("0") else D("0")
            roi = D("0") if invested == D("0") else ((nav_of[day] - invested) / invested).quantize(_PCT, rounding=ROUND_HALF_UP)
        rois.append((day, roi))
    periods: list[tuple[date, Decimal, Decimal, Decimal]] = []
    compound = D("1")
    for previous, current in zip(days, days[1:], strict=False):
        before_flow = nav_of[current] + on.get(current, D("0"))
        base = nav_of[previous] if exposure is None else exposure[previous]
        period_return = D("0") if base == D("0") else (before_flow - nav_of[previous]) / base
        compound *= D("1") + period_return
        periods.append((current, period_return, compound, compound - D("1")))
    return rois, periods


def _inputs(navs: Sequence[tuple[date, Decimal]], flows: Sequence[tuple[date, Decimal]]) -> tuple[list[NAVSnapshot], list[CashFlowInput]]:
    return [NAVSnapshot(date=day, nav=nav) for day, nav in navs], [CashFlowInput(date=day, amount=amount) for day, amount in flows]


def _observed(navs, flows, **variant) -> dict[str, list]:
    """What the functions under test give: ROI points, TWRR sub-periods, public TWRR points."""
    snapshots, cash_flows = _inputs(navs, flows)
    roi_kwargs = {"capital_by_date": variant["capital"]} if "capital" in variant else {}
    twrr_kwargs = {"exposure_by_date": variant["exposure"]} if "exposure" in variant else {}
    return {
        "roi": [(point.date, point.roi) for point in calculate_simple_roi_series(snapshots, cash_flows, **roi_kwargs)],
        "periods": [(point.date, point.period_return, point.wealth_index, point.cumulative_twrr) for point in calculate_twrr_period_series(snapshots, cash_flows, **twrr_kwargs)],
        "twrr": [(point.date, point.twrr) for point in calculate_twrr_series(snapshots, cash_flows, **twrr_kwargs)],
    }


def _expected(navs, flows, **variant) -> dict[str, list]:
    """The same three, from the oracle; public TWRR rounded as returns.py rounds."""
    rois, periods = _oracle(navs, flows, **variant)
    return {"roi": rois, "periods": periods, "twrr": [(day, cumulative.quantize(_PCT, rounding=ROUND_HALF_UP)) for day, _r, _w, cumulative in periods]}


def _headline(navs, flows, **variant) -> dict[date, tuple[Decimal, Decimal | None]]:
    """(ROI, public TWRR) by date, from the oracle: what each docstring states."""
    expected = _expected(navs, flows, **variant)
    twrr = dict(expected["twrr"])
    return {day: (roi, twrr.get(day)) for day, roi in expected["roi"]}


# --------------------------------------------------------------------------- #
# The developer's example, on every function
# --------------------------------------------------------------------------- #


class TestTheDevelopersExample:
    """10 bought at 100 on 5 Jan (NAV 1 000, −1 000); 5 more at 100 on 6 Jan (−500), a day without a snapshot; NAV on 7 Jan.
    The 6 Jan flow counts on 7 Jan."""

    @staticmethod
    def _book(nav_on_jan_7: str) -> tuple[list, list]:
        return [(JAN_5, D("1000")), (JAN_7, D(nav_on_jan_7))], [(JAN_5, D("-1000")), (JAN_6, D("-500"))]

    @pytest.mark.parametrize(
        ("nav_on_jan_7", "roi", "twrr"),
        [
            pytest.param("1500", "0", "0", id="the-developers-example-flat"),
            pytest.param("1650", "0.1", "0.15", id="priced-110-the-capital-is-1500"),
        ],
    )
    def test_the_gap_flow_counts_on_the_next_snapshot(self, nav_on_jan_7, roi, twrr):
        """Flat (the developer's words): 7 Jan TWRR (1 500 − 500) / 1 000 − 1 = 0, ROI (1 500 − 1 500) / 1 500 = 0 — capital
        1 500, gain 0. Priced at 110 (NAV 1 650), the capital shows: ROI 150 / 1 500 = 10%, TWRR (1 650 − 500 − 1 000) /
        1 000 = 15%. On 5 Jan ROI 0 and no TWRR. Every function: the ROI series, the TWRR sub-periods and public series.

        Today (HEAD 2e23bd03c): the 6 Jan flow is dropped — flat ROI and TWRR 50%; priced 65% and 65%.
        """
        navs, flows = self._book(nav_on_jan_7)
        assert _headline(navs, flows)[JAN_7] == (D(roi), D(twrr)), "precondition: the oracle gives the stated figures"

        assert _observed(navs, flows) == _expected(navs, flows)

    def test_calculate_twrr_reads_the_same_rule(self):
        """``calculate_twrr`` on the flat example: TWRRPoint(7 Jan, 0). Today: 0.5."""
        snapshots, cash_flows = _inputs(*self._book("1500"))

        point = calculate_twrr(snapshots, cash_flows)

        assert (point.date, point.twrr) == (JAN_7, D("0"))


# --------------------------------------------------------------------------- #
# The shapes of a gap
# --------------------------------------------------------------------------- #


class TestTheShapesOfAGap:
    @pytest.mark.parametrize(("price", "roi", "twrr"), [pytest.param("100", "0", "0", id="flat"), pytest.param("110", "0.1", "0.05", id="priced-110")])
    def test_a_sale_on_the_gap_day(self, price, roi, twrr):
        """10 bought at 100 on 5 Jan (−1 000, NAV 1 000); 5 sold at 100 on 6 Jan (+500), no snapshot; the 5 left on 7 Jan at
        ``price``. The sale counts on 7 Jan: capital 500. Flat: ROI 0, TWRR (500 + 500 − 1 000) / 1 000 = 0. At 110 (NAV
        550): ROI 50 / 500 = 10%, TWRR 5%.

        Today: the sale is dropped — flat ROI −50%, TWRR −50%; at 110 ROI −45%, TWRR −45%.
        """
        navs = [(JAN_5, D("1000")), (JAN_7, D(price) * 5)]
        flows = [(JAN_5, D("-1000")), (JAN_6, D("500"))]
        assert _headline(navs, flows)[JAN_7] == (D(roi), D(twrr)), "precondition: the oracle gives the stated figures"

        assert _observed(navs, flows) == _expected(navs, flows)

    def test_several_consecutive_gap_days(self):
        """10 bought at 100 on 5 Jan (NAV 1 000); 2 bought on 6 Jan (−200), 1 sold on 7 Jan (+100), 3 bought on 8 Jan (−300) —
        three days without a snapshot —; 14 units at 110 on 9 Jan (NAV 1 540). The three flows, −400 net, count on 9 Jan:
        capital 1 400, ROI 140 / 1 400 = 10%; TWRR (1 540 − 400 − 1 000) / 1 000 = 14%.

        Today: all three dropped — ROI 54%, TWRR 54%.
        """
        navs = [(JAN_5, D("1000")), (JAN_9, D("1540"))]
        flows = [(JAN_5, D("-1000")), (JAN_6, D("-200")), (JAN_7, D("100")), (JAN_8, D("-300"))]
        assert _headline(navs, flows)[JAN_9] == (D("0.1"), D("0.14")), "precondition: the oracle gives the stated figures"

        assert _observed(navs, flows) == _expected(navs, flows)

    def test_a_gap_flow_and_the_snapshots_own_flow_add_up(self):
        """10 bought at 100 on 5 Jan (NAV 1 000); 5 bought on 6 Jan (−500), no snapshot; 3 bought on 7 Jan (−300), a snapshot
        day: 18 units at 110 (NAV 1 980). Both flows count on 7 Jan, −800: capital 1 800, ROI 180 / 1 800 = 10%; TWRR
        (1 980 − 800 − 1 000) / 1 000 = 18%. The flows are given out of date order: each counts by its own date.

        Today: the 6 Jan flow is dropped — ROI 680 / 1 300 = 52.3077%, TWRR 68%.
        """
        navs = [(JAN_5, D("1000")), (JAN_7, D("1980"))]
        flows = [(JAN_7, D("-300")), (JAN_5, D("-1000")), (JAN_6, D("-500"))]
        assert _headline(navs, flows)[JAN_7] == (D("0.1"), D("0.18")), "precondition: the oracle gives the stated figures"

        assert _observed(navs, flows) == _expected(navs, flows)

    def test_a_flow_after_the_last_snapshot_counts_nowhere(self):
        """GUARD (green today and after): 10 bought at 100 on 5 Jan (NAV 1 000), NAV 1 100 on 6 Jan, the last snapshot; 5
        bought on 8 Jan (−500), after it. It counts nowhere: ROI 0 then 10%, TWRR 10% on 6 Jan — as today."""
        navs = [(JAN_5, D("1000")), (JAN_6, D("1100"))]
        flows = [(JAN_5, D("-1000")), (JAN_8, D("-500"))]
        assert _headline(navs, flows) == {JAN_5: (D("0"), None), JAN_6: (D("0.1"), D("0.1"))}, "precondition: the oracle gives the stated figures"

        assert _observed(navs, flows) == _expected(navs, flows)

    def test_roi_counts_the_flows_before_the_first_snapshot_on_it(self):
        """10 bought at 100 on 5 Jan (−1 000), before the first snapshot; 2 more on 6 Jan (−200), the first snapshot (NAV
        1 200); NAV 1 320 on 7 Jan. ROI counts the 5 Jan flow on 6 Jan: capital 1 200, ROI 0 then 120 / 1 200 = 10%.

        Today ROI drops it: capital 200, ROI (1 200 − 200) / 200 = 500% on 6 Jan and 560% on 7 Jan. (The lots' performance
        history already carries such flows onto its first NAV itself: its ROI does not move.)
        """
        navs = [(JAN_6, D("1200")), (JAN_7, D("1320"))]
        flows = [(JAN_5, D("-1000")), (JAN_6, D("-200"))]
        assert [roi for _day, roi in _expected(navs, flows)["roi"]] == [D("0"), D("0.1")], "precondition: the oracle gives the stated figures"

        assert _observed(navs, flows)["roi"] == _expected(navs, flows)["roi"]

    def test_twrr_never_reads_the_first_snapshots_flows(self):
        """GUARD (green today and after): the same book. TWRR starts from the first snapshot: its flows — its own and those
        landed on it from before — are never read. 7 Jan: (1 320 − 1 200) / 1 200 = 10%, as today."""
        navs = [(JAN_6, D("1200")), (JAN_7, D("1320"))]
        flows = [(JAN_5, D("-1000")), (JAN_6, D("-200"))]
        assert _expected(navs, flows)["twrr"] == [(JAN_7, D("0.1"))], "precondition: the oracle gives the stated figures"

        observed = _observed(navs, flows)
        assert (observed["periods"], observed["twrr"]) == (_expected(navs, flows)["periods"], _expected(navs, flows)["twrr"])


# --------------------------------------------------------------------------- #
# The variants of MF-E2 (a short in the lots' scope)
# --------------------------------------------------------------------------- #


class TestTheVariantsReadTheMovedFlows:
    """10 sold short at 100 on 5 Jan (+1 000, NAV −1 000, exposure 1 000); 4 bought back at 100 on 6 Jan (−400), no snapshot;
    the 6 still short at 90 on 7 Jan (NAV −540, exposure 540). The buy-back counts on 7 Jan."""

    NAVS = [(JAN_5, D("-1000")), (JAN_7, D("-540"))]
    FLOWS = [(JAN_5, D("1000")), (JAN_6, D("-400"))]

    def test_twrr_on_the_exposure(self):
        """``exposure_by_date``, read on the previous snapshot's date: 7 Jan (−540 − 400 + 1 000) / 1 000 = 6% — 10 a unit on
        the 6 still short. Today: the buy-back dropped, (−540 + 1 000) / 1 000 = 46%."""
        exposure = {JAN_5: D("1000"), JAN_7: D("540")}
        assert _expected(self.NAVS, self.FLOWS, exposure=exposure)["twrr"] == [(JAN_7, D("0.06"))], "precondition: the oracle gives the stated figures"

        observed = _observed(self.NAVS, self.FLOWS, exposure=exposure)
        expected = _expected(self.NAVS, self.FLOWS, exposure=exposure)
        assert (observed["periods"], observed["twrr"]) == (expected["periods"], expected["twrr"])

    def test_roi_on_the_given_capital(self):
        """``capital_by_date`` (the proceeds, 1 000 both days): the gain reads the moved buy-back. 5 Jan 0; 7 Jan (−540 +
        1 000 − 400) / 1 000 = 6%. Today: (−540 + 1 000) / 1 000 = 46%."""
        capital = {JAN_5: D("1000"), JAN_7: D("1000")}
        assert [roi for _day, roi in _expected(self.NAVS, self.FLOWS, capital=capital)["roi"]] == [D("0"), D("0.06")], "precondition: the oracle gives the stated figures"

        assert _observed(self.NAVS, self.FLOWS, capital=capital)["roi"] == _expected(self.NAVS, self.FLOWS, capital=capital)["roi"]


# --------------------------------------------------------------------------- #
# The Dashboard guarantee: every flow on a snapshot date — today's output, digit for digit
# --------------------------------------------------------------------------- #

_AMOUNTS = ("-1500", "-1500.00", "250.123456", "-0.000001", "1E+3", "-2.5E+2", "0", "-333.333333333333")


def _converted(rng: random.Random, low: float, high: float) -> Decimal:
    """An amount converted at a rate, as the Dashboard hands them over: 28 significant digits, so that adding a few of them
    rounds and the order of the additions shows in the last digit."""
    return D(f"{rng.uniform(low, high):.2f}") * (D(1) / D(rng.randint(3, 997)))


def _dashboard_like_book(seed: int) -> dict:
    """A random series whose flows all fall on snapshot dates (``random.Random``, stable across Python 3 versions).

    2–14 snapshots, consecutive or days apart; NAVs that are 0, round, with 2 or 6 decimals, long, or converted; 0–3 flows
    on a snapshot date, in random order, in mixed representations (``1E+3``, ``-1500`` and ``-1500.00``, long fractions,
    converted amounts of 28 digits), so the cumulative flows also turn positive (no capital). With them, random positive
    exposures and capitals for the variants, one per snapshot date.
    """
    rng = random.Random(seed)
    day = date(2024, 1, 1)
    navs: list[tuple[date, Decimal]] = []
    flows: list[tuple[date, Decimal]] = []
    for _ in range(rng.randint(2, 14)):
        day += timedelta(days=rng.choice((1, 1, 2, 5)))
        nav = rng.choice((D("0"), D(rng.randint(0, 5000)), D(f"{rng.uniform(0, 5000):.2f}"), D(f"{rng.uniform(0, 5000):.6f}"), D(f"{rng.uniform(0, 5000):.15f}"), _converted(rng, 0, 5000)))
        navs.append((day, nav))
        for _flow in range(rng.choice((0, 1, 1, 2, 3))):
            kind = rng.random()
            amount = D(rng.choice(_AMOUNTS)) if kind < 0.3 else _converted(rng, -3000, 1500) if kind < 0.7 else D(f"{rng.uniform(-3000, 1500):.{rng.choice((0, 2, 6, 12))}f}")
            flows.append((day, amount))
    rng.shuffle(flows)
    exposure = {snapshot: D(f"{rng.uniform(0, 6000):.4f}") for snapshot, _nav in navs}
    capital = {snapshot: rng.choice((D("0"), D(f"{rng.uniform(1, 6000):.3f}"))) for snapshot, _nav in navs}
    return {"navs": navs, "flows": flows, "exposure": exposure, "capital": capital}


def _digits(series: dict[str, list]) -> dict[str, list]:
    """Every Decimal of the three series as its ``as_tuple()``: sign, digits and exponent, so ``0`` is not ``0.000000``."""
    return {name: [tuple(value.as_tuple() if isinstance(value, Decimal) else value for value in point) for point in points] for name, points in series.items()}


@pytest.mark.parametrize("batch", range(10), ids=lambda batch: f"seeds-{batch * 40}-{batch * 40 + 39}")
def test_the_dashboard_with_every_flow_on_a_snapshot_keeps_todays_output_digit_for_digit(batch):
    """GUARD (green today and after): on 40 random series per batch whose flows all fall on snapshot dates — what the
    Dashboard's summary and history always hand over —, the ROI series, the TWRR sub-periods (period return, wealth
    index, cumulative TWRR, unrounded) and the public TWRR are the oracle's digit for digit, which with no flow to move
    performs today's operations in today's order. The same for the ``exposure_by_date`` and ``capital_by_date`` variants.
    """
    mismatches = []
    for seed in range(batch * 40, batch * 40 + 40):
        book = _dashboard_like_book(seed)
        for variant in ({}, {"exposure": book["exposure"]}, {"capital": book["capital"]}):
            if _digits(_observed(book["navs"], book["flows"], **variant)) != _digits(_expected(book["navs"], book["flows"], **variant)):
                mismatches.append((seed, sorted(variant)))

    assert mismatches == []
