"""
MF-P (workstream MF, lot P, part 1 — R17 and W8): a change as a fraction of its base, the timing effect and the gain or
loss of a group of holdings get their home in ``returns.py``.

Module under test: ``backend/app/services/financial_math/returns.py``, three new pure functions the Dashboard summary
calls (``portfolio_service.get_summary``) instead of leaving the arithmetic to the frontend:

* ``change_ratio(change, base)`` = ``change / |base|``, unrounded; None when either is missing or the base is 0. The
  sign is the change's whatever the base's: a total P&L that goes from −100 to −50 changed by +50 %. It is what
  ``period.day_change`` divides the day's P&L change by, twice: yesterday's total P&L and yesterday's NAV (R17). Unlike
  ``gain_loss_ratio(..., positive_base=False)``, which keeps the base's sign.
* ``timing_effect(mwrr_cumulative, twrr)`` = their difference: what the timing of deposits and withdrawals added to the
  period's return; None when either is missing.
* ``group_gain_loss(pairs)`` over ``(value, gain)`` pairs, one per holding: only the pairs whose value and gain are both
  known count, on both sides; cost = value − gain; returns ``(Σ gain, gain_loss_ratio(Σ gain, Σ cost,
  positive_base=False))`` — a signed base, None on a zero cost — and ``(None, None)`` when no pair counts (W8).

What the frontend computes today for a treemap group (``frontend/src/lib/features/dashboard/ExposureTreemap.svelte``,
``:366-450``): every holding with a value above zero adds that value to the group, its gain only when known, and the
group's ratio is Σ gain / (Σ value − Σ gain). A holding whose gain is unknown — a priced position whose cost is not
known — thus lends its whole value to the base as if it were cost, and a group with no known gain shows 0 %. The
formula is copied below (``_treemap_group_ratio_today``, in Decimal) and contrasted on the same input.

Every figure is compared exactly: a quotient is the context's quotient of the two Decimals, with no rounding step of
its own (``Decimal("70") / Decimal("120")``, 0.58333…3 to 28 digits, never 0.5833).

Red by absence on HEAD (c2feebaa8): every name is read as an attribute of ``returns`` while the test runs, never
imported at module level, so the file collects on HEAD and each test fails there with AttributeError
(``module ... has no attribute 'change_ratio'`` / ``'timing_effect'`` / ``'group_gain_loss'``).

Pure: no database, no server, no network.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

import pytest

from backend.app.services.financial_math import returns

D = Decimal


def _change_ratio(change: Decimal | None, base: Decimal | None) -> Decimal | None:
    """``returns.change_ratio``, read when the test runs: until MF-P it does not exist."""
    return returns.change_ratio(change, base)


def _timing_effect(mwrr_cumulative: Decimal | None, twrr: Decimal | None) -> Decimal | None:
    """``returns.timing_effect``, read when the test runs."""
    return returns.timing_effect(mwrr_cumulative, twrr)


def _group_gain_loss(pairs: Iterable[tuple[Decimal | None, Decimal | None]]) -> tuple[Decimal | None, Decimal | None]:
    """``returns.group_gain_loss``, read when the test runs."""
    return returns.group_gain_loss(pairs)


def _treemap_group_ratio_today(pairs: Iterable[tuple[Decimal | None, Decimal | None]]) -> Decimal | None:
    """The treemap's group ratio as the frontend computes it today (ExposureTreemap.svelte ``:366-450``), in Decimal.

    ``if (val == null || val <= 0) continue``; ``value += val``; ``if (gl != null) gl += gl``; then
    ``aggregateGlPct(value, gl)`` = ``gl / (value - gl)``, null on a zero cost.
    """
    value = D("0")
    gain = D("0")
    for holding_value, holding_gain in pairs:
        if holding_value is None or holding_value <= 0:
            continue
        value += holding_value
        if holding_gain is not None:
            gain += holding_gain
    cost = value - gain
    return gain / cost if cost != 0 else None


# =============================================================================
# change_ratio
# =============================================================================


class TestChangeRatio:
    """``change / |base|``: the change's sign, whatever the base's; None on a missing figure or a zero base."""

    @pytest.mark.parametrize(
        ("change", "base", "expected"),
        [
            ("30", "100", "0.3"),  # 100 → 130
            ("-30", "100", "-0.3"),  # 100 → 70
            ("50", "-100", "0.5"),  # −100 → −50: a loss that shrinks is a rise
            ("-50", "-100", "-0.5"),  # −100 → −150: a loss that deepens is a fall
            ("0", "-100", "0"),
        ],
        ids=["rise-on-a-gain", "fall-on-a-gain", "loss-shrinks", "loss-deepens", "no-change"],
    )
    def test_the_change_over_the_size_of_its_base(self, change, base, expected):
        result = _change_ratio(D(change), D(base))

        assert isinstance(result, Decimal), f"a Decimal, got {result!r}"
        assert result == D(expected), f"{change} / |{base}|: expected {expected}, got {result}"

    def test_the_sign_is_the_change_s_not_the_base_s(self):
        """The reason for a function of its own: ``gain_loss_ratio`` with a signed base gives −0.5 for the loss that
        shrinks from −100 to −50; the change ratio gives +0.5."""
        assert returns.gain_loss_ratio(D("50"), D("-100"), positive_base=False) == D("-0.5"), "precondition: gain_loss_ratio keeps the base's sign"

        assert _change_ratio(D("50"), D("-100")) == D("0.5")

    @pytest.mark.parametrize("base", ["0", "0.00", "-0"], ids=["zero", "zero-with-exponent", "negative-zero"])
    @pytest.mark.parametrize("change", ["30", "0"], ids=["a-change", "no-change"])
    def test_none_on_a_zero_base(self, change, base):
        assert _change_ratio(D(change), D(base)) is None

    @pytest.mark.parametrize(("change", "base"), [(None, D("100")), (D("30"), None), (None, None)], ids=["no-change", "no-base", "neither"])
    def test_none_when_either_is_missing(self, change, base):
        assert _change_ratio(change, base) is None

    @pytest.mark.parametrize("base", ["120", "-120"], ids=["positive-base", "negative-base"])
    def test_unrounded(self, base):
        """70 / |±120| = 0.58333… to the context's precision: no rounding of its own."""
        result = _change_ratio(D("70"), D(base))

        assert result == D("70") / D("120")
        assert result != result.quantize(D("0.000001")), f"rounded: {result}"


# =============================================================================
# timing_effect
# =============================================================================


class TestTimingEffect:
    """Cumulative MWRR − TWRR, exact; None when either is missing."""

    @pytest.mark.parametrize(
        ("mwrr_cumulative", "twrr", "expected"),
        [
            ("0.12", "0.10", "0.02"),  # deposits before the rise helped
            ("0.2428", "0.270588", "-0.027788"),  # a top-up after the rise hurt
            ("-0.05", "0.03", "-0.08"),
            ("0.123456789123456789", "0.1", "0.023456789123456789"),  # unrounded
            ("0.07", "0.07", "0"),
        ],
        ids=["helped", "hurt", "opposite-signs", "unrounded", "none-at-all"],
    )
    def test_mwrr_less_twrr(self, mwrr_cumulative, twrr, expected):
        result = _timing_effect(D(mwrr_cumulative), D(twrr))

        assert isinstance(result, Decimal), f"a Decimal, got {result!r}"
        assert result == D(expected), f"{mwrr_cumulative} − {twrr}: expected {expected}, got {result}"

    @pytest.mark.parametrize(("mwrr_cumulative", "twrr"), [(None, D("0.1")), (D("0.1"), None), (None, None)], ids=["no-mwrr", "no-twrr", "neither"])
    def test_none_when_either_is_missing(self, mwrr_cumulative, twrr):
        assert _timing_effect(mwrr_cumulative, twrr) is None


# =============================================================================
# group_gain_loss
# =============================================================================


class TestGroupGainLoss:
    """``(Σ gain, Σ gain / Σ cost)`` over the holdings whose value and gain are both known."""

    def test_a_holding_without_a_gain_lends_no_value_to_the_base(self):
        """Two holdings bought for 1000 each, now 1130 (+130) and 885 (−115); a third priced at 200 whose cost is not
        known (gain None); a fourth with neither (no price, no cost). Σ gain 15 on a cost of 2000: 0.0075.

        Today's treemap adds the 200 to the base: 15 / (2215 − 15) = 0.0068181…"""
        pairs = [(D("1130"), D("130")), (D("885"), D("-115")), (D("200"), None), (None, None)]
        assert _treemap_group_ratio_today(pairs) == D("15") / D("2200"), "precondition: today's formula on the same input"

        assert _group_gain_loss(pairs) == (D("15"), D("0.0075"))

    def test_a_value_without_a_gain_and_a_gain_without_a_value_do_not_count(self):
        """Both figures or neither, on both sides: (None, 50) adds nothing to the gain, (200, None) nothing to the cost."""
        assert _group_gain_loss([(D("1130"), D("130")), (None, D("50")), (D("200"), None)]) == (D("130"), D("0.13"))

    def test_a_holding_valued_at_cost_counts(self):
        """A holding valued at its cost (ESTIMATED_AT_COST: value 200, gain 0) counts, its cost in the base:
        −80 / (800 + 200) = −0.08, not −80 / 800 = −0.1."""
        assert _group_gain_loss([(D("720"), D("-80")), (D("200"), D("0"))]) == (D("-80"), D("-0.08"))

    def test_a_group_of_holdings_valued_at_cost_has_a_zero_gain(self):
        """Known and zero, not unknown: (0, 0)."""
        result = _group_gain_loss([(D("200"), D("0"))])

        assert result == (D("0"), D("0"))
        assert None not in result, f"a zero gain is known: {result}"

    @pytest.mark.parametrize(
        "pairs",
        [[], [(D("200"), None)], [(D("200"), None), (None, None), (None, D("5"))]],
        ids=["no-holding", "priced-cost-unknown", "nothing-counts"],
    )
    def test_none_when_no_holding_counts(self, pairs):
        """No gain known: (None, None) — today's treemap shows 0 % for a group of priced holdings without a gain."""
        assert _group_gain_loss(pairs) == (None, None)

    @pytest.mark.parametrize(
        "pairs",
        [[(D("100"), D("100"))], [(D("100"), D("100")), (D("40"), D("40"))]],
        ids=["one-gift", "two-gifts"],
    )
    def test_no_ratio_on_a_zero_cost(self, pairs):
        """Holdings that cost nothing (a gift): the gain is known, its fraction of a zero cost is not."""
        gain, ratio = _group_gain_loss(pairs)

        assert gain == sum((pair[1] for pair in pairs), D("0"))
        assert ratio is None

    def test_losses(self):
        """800 (−200) and 450 (−50): −250 on a cost of 1500, −0.1666…7."""
        assert _group_gain_loss([(D("800"), D("-200")), (D("450"), D("-50"))]) == (D("-250"), D("-250") / D("1500"))

    def test_the_cost_keeps_its_sign(self):
        """``gain_loss_ratio`` with ``positive_base=False``: a negative cost (value 50, gain 100: cost −50) is divided by
        as it is, 100 / −50 = −2 — never by its size."""
        assert _group_gain_loss([(D("50"), D("100"))]) == (D("100"), D("-2"))

    def test_exact_and_unrounded(self):
        """Σ gain in Decimal (0.10 + 0.20 is 0.30, not 0.30000000000000004) and the ratio unrounded:
        (0.30 + 100) / (10 + 20 + 3000) = 100.30 / 3030."""
        pairs = [(D("10.10"), D("0.10")), (D("20.20"), D("0.20")), (D("3100"), D("100"))]

        gain, ratio = _group_gain_loss(iter(pairs))

        assert gain == D("100.30")
        assert ratio == D("100.30") / D("3030")
        assert ratio != ratio.quantize(D("0.000001")), f"rounded: {ratio}"
