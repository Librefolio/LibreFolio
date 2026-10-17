"""
MF-C (workstream MF, developer's decision D-MF7): weights and concentration, one module.

Module under test: ``backend/app/services/financial_math/weights.py``, new. Five functions:

* ``share_of(part, total)``: ``part / total``, unrounded; None when the total is zero or negative;
* ``percent_of(part, total)``: the same share × 100, unrounded; None where ``share_of`` is None;
* ``slice_percents(amounts)``: the slices of an allocation as percentages of their **signed** sum,
  unrounded, in the mapping's order; a sum of zero divides by 1 (so an empty or all-zero allocation
  is all zeros). This is the old ``derived_views._alloc`` rule kept as it was: cash below zero is a
  slice below zero and the others then add up to more than 100;
* ``gross_weights(values)``: ``|value| / Σ |value|`` per key, in the mapping's order; ``{}`` on a
  zero total (short positions weigh by their size);
* ``concentration(weights_percent)``: the largest absolute weight and the Herfindahl index
  ``Σ w²`` over every weight given; ``(None, None)`` without weights.

Its callers, each of which wrote its own formula in place before MF-C: ``portfolio_service.get_summary``
(a holding's ``allocation_percent`` and ``nav_weight_percent``), ``financial_math/portfolio/derived_views``
(``_alloc`` in ``build_allocation_current`` and ``build_allocation_history``), ``risk/scope`` (the
current-composition weights, in ``risk/service`` before CP-9a), ``ai_export/components/technical_shared.compute_nav_weights``,
``ai_export/components/broker_financial._concentration_metrics`` and
``ai_export/components/broker_concentration_context.concentration_metrics``.

D-MF7 changes one thing: a holding's weight on a total at or below zero is None («—») — the NAV for
``nav_weight_percent`` (before: ``value / 1 × 100``) and the holdings' market total for
``allocation_percent`` (before: a division by that negative total, or by 1 on a zero total). Every
other number must stay byte-identical, so ``TestParityWithTheOldFormulas`` writes each old formula
inline, as it stood at HEAD, and compares ``str()`` — value *and* exponent — with the new function,
rounded where the caller rounds and unrounded too. ``TestDMF7Divergence`` pins the only difference,
next to the number HEAD gave.

Red by absence before MF-C: the module is imported while each test runs (``_weights()``), never at
module level, so the file collects on HEAD and every test fails on ``ModuleNotFoundError``.

Pure: no database, no server, no network.
"""

from __future__ import annotations

import importlib
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal
from types import ModuleType

import pytest

WEIGHTS_MODULE = "backend.app.services.financial_math.weights"

CENT = Decimal("0.01")

#: Totals with no share: zero in every spelling, and below zero.
NON_POSITIVE_TOTALS = ("0", "0.00", "-0", "-0.01", "-70", "-1000.50")


def _weights() -> ModuleType:
    """``financial_math/weights.py``, imported when a test runs: until MF-C it does not exist."""
    return importlib.import_module(WEIGHTS_MODULE)


def _d(text: str) -> Decimal:
    return Decimal(text)


def _shown(mapping: Mapping[object, Decimal]) -> list[tuple[object, str]]:
    """Keys in order with each value's ``str()``: equal only if order, value and exponent all agree."""
    return [(key, str(value)) for key, value in mapping.items()]


# =============================================================================
# The old formulas, as they stood at HEAD (before MF-C)
# =============================================================================


def _old_alloc_percents(amounts: dict[str, Decimal]) -> dict[str, Decimal]:
    """``derived_views._alloc`` and ``build_allocation_history``, before rounding:
    ``total = sum(d.values()) or Decimal("1")``, then ``amt / total * 100``."""
    total = sum(amounts.values()) or Decimal("1")
    return {name: amt / total * 100 for name, amt in amounts.items()}


def _old_allocation_percent(value: Decimal, holding_values: Sequence[Decimal | None]) -> Decimal:
    """``portfolio_service.get_summary`` step 4, ``allocation_percent`` of a holding with a value."""
    total_market = sum(h for h in holding_values if h) or Decimal("1")
    return (value / total_market * 100).quantize(CENT)


def _old_nav_weight_percent(value: Decimal, engine_nav: Decimal) -> Decimal:
    """``portfolio_service.get_summary`` step 4, ``nav_weight_percent`` of a holding with a value."""
    nav_denominator = engine_nav if engine_nav > 0 else Decimal("1")
    return (value / nav_denominator * 100).quantize(CENT)


def _old_concentration(weights: Iterable[Decimal | None]) -> tuple[Decimal | None, Decimal | None]:
    """``broker_financial._concentration_metrics`` (and its copy in ``broker_concentration_context``)."""
    kept = [weight for weight in weights if weight is not None]
    if not kept:
        return None, None
    largest = max(abs(weight) for weight in kept)
    herfindahl = sum(weight * weight for weight in kept)
    return largest, herfindahl


def _gross_by_asset(positions: Sequence[tuple[int, Decimal | None]]) -> dict[int, Decimal]:
    """``technical_shared.compute_nav_weights``'s accumulation, unchanged by MF-C: |end value| per asset."""
    gross: dict[int, Decimal] = {}
    for asset_id, end_value in positions:
        if end_value is None:
            continue
        gross[asset_id] = gross.get(asset_id, Decimal(0)) + abs(end_value)
    return gross


def _old_nav_weights_tail(gross_by_asset: dict[int, Decimal]) -> dict[int, Decimal]:
    """``technical_shared.compute_nav_weights`` after the accumulation, before MF-C."""
    total = sum(gross_by_asset.values(), Decimal(0))
    if total <= 0:
        return {}
    return {asset_id: gross_value / total for asset_id, gross_value in sorted(gross_by_asset.items())}


def _old_risk_weights(asset_values: dict[int, Decimal], scope_value: Decimal) -> dict[int, float]:
    """``RiskService``'s current-composition weights, before MF-C."""
    if scope_value > 0:
        return {asset_id: float(value / scope_value) for asset_id, value in asset_values.items() if value >= 0}
    return {}


# =============================================================================
# share_of / percent_of
# =============================================================================


class TestShareOf:
    def test_part_over_total_unrounded(self):
        weights = _weights()
        assert weights.share_of(_d("1"), _d("4")) == _d("0.25")
        third = weights.share_of(_d("1"), _d("3"))
        assert str(third) == str(Decimal(1) / Decimal(3)), f"share_of must not round: {third}"

    @pytest.mark.parametrize("total", NON_POSITIVE_TOTALS)
    @pytest.mark.parametrize("part", ["630", "0", "-80"])
    def test_no_share_of_a_total_at_or_below_zero(self, part, total):
        assert _weights().share_of(_d(part), _d(total)) is None

    def test_a_zero_part_is_a_zero_share_not_none(self):
        share = _weights().share_of(_d("0"), _d("100"))
        assert share is not None and share == 0

    def test_the_part_keeps_its_sign_and_may_exceed_the_total(self):
        weights = _weights()
        assert weights.share_of(_d("-50"), _d("200")) == _d("-0.25")
        assert weights.share_of(_d("300"), _d("200")) == _d("1.5")


class TestPercentOf:
    def test_share_times_one_hundred_unrounded(self):
        weights = _weights()
        assert weights.percent_of(_d("1"), _d("4")) == _d("25")
        third = weights.percent_of(_d("1"), _d("3"))
        assert str(third) == str(Decimal(1) / Decimal(3) * Decimal(100)), f"percent_of must not round: {third}"

    def test_a_hand_computed_weight(self):
        """1130 of 2015, rounded to 0.01 by the caller: 56.0794… → 56.08."""
        assert _weights().percent_of(_d("1130"), _d("2015")).quantize(CENT) == _d("56.08")

    @pytest.mark.parametrize("total", NON_POSITIVE_TOTALS)
    def test_no_percent_of_a_total_at_or_below_zero(self, total):
        assert _weights().percent_of(_d("630"), _d(total)) is None

    def test_leverage_above_one_hundred_is_kept(self):
        """A total above zero has a share, however large: 1510 on a NAV of 510 is 296.08 %."""
        assert _weights().percent_of(_d("1510"), _d("510")).quantize(CENT) == _d("296.08")

    def test_a_negative_part_on_a_positive_total(self):
        assert _weights().percent_of(_d("-80"), _d("770")).quantize(CENT) == _d("-10.39")


# =============================================================================
# slice_percents
# =============================================================================


class TestSlicePercents:
    def test_slices_of_a_positive_sum_in_the_mapping_order(self):
        percents = _weights().slice_percents({"Stock": _d("600"), "ETF": _d("300"), "Cash": _d("100")})
        assert list(percents) == ["Stock", "ETF", "Cash"]
        assert percents == {"Stock": _d("60"), "ETF": _d("30"), "Cash": _d("10")}

    def test_cash_below_zero_is_a_slice_below_zero(self):
        """The others then add up to more than 100: the allocation is signed, never gross."""
        percents = _weights().slice_percents({"Stock": _d("1500"), "Cash": _d("-500")})
        assert percents == {"Stock": _d("150"), "Cash": _d("-50")}
        assert sum(percents.values()) == 100

    def test_a_negative_sum_divides_by_the_signed_sum(self):
        """The old ``_alloc`` rule, kept: −200 is the divisor, so every slice changes sign."""
        percents = _weights().slice_percents({"Stock": _d("100"), "Cash": _d("-300")})
        assert percents == {"Stock": _d("-50"), "Cash": _d("150")}

    def test_empty_and_all_zero_allocations_are_zeros_not_none(self):
        weights = _weights()
        assert weights.slice_percents({}) == {}
        percents = weights.slice_percents({"Stock": _d("0"), "Cash": _d("0.00")})
        assert list(percents) == ["Stock", "Cash"]
        assert all(value is not None and value == 0 for value in percents.values()), percents

    def test_a_net_zero_allocation_divides_by_one(self):
        """The old ``or 1``, kept byte-identical on purpose (D-MF7 covers the holdings' weights, not the
        allocation slices): slices that cancel out read as their amounts × 100."""
        percents = _weights().slice_percents({"Stock": _d("500"), "Cash": _d("-500")})
        assert percents == {"Stock": _d("50000"), "Cash": _d("-50000")}

    def test_unrounded(self):
        percents = _weights().slice_percents({"A": _d("1"), "B": _d("2")})
        assert str(percents["A"]) == str(Decimal(1) / Decimal(3) * Decimal(100)), percents


# =============================================================================
# gross_weights
# =============================================================================


class TestGrossWeights:
    def test_shares_of_the_gross_total(self):
        assert _weights().gross_weights({1: _d("300"), 2: _d("100")}) == {1: _d("0.75"), 2: _d("0.25")}

    def test_a_short_position_weighs_by_its_size(self):
        assert _weights().gross_weights({1: _d("300"), 2: _d("-100")}) == {1: _d("0.75"), 2: _d("0.25")}

    @pytest.mark.parametrize("values", [{}, {1: Decimal("0"), 2: Decimal("0.00")}], ids=["empty", "all-zero"])
    def test_a_zero_total_has_no_weights(self, values):
        assert _weights().gross_weights(values) == {}

    def test_keys_and_order_are_kept_a_zero_value_weighs_zero(self):
        result = _weights().gross_weights({3: _d("0"), 1: _d("50"), 2: _d("-50")})
        assert list(result) == [3, 1, 2]
        assert result == {3: _d("0"), 1: _d("0.5"), 2: _d("0.5")}

    def test_unrounded(self):
        result = _weights().gross_weights({1: _d("1"), 2: _d("2")})
        assert str(result[1]) == str(Decimal(1) / Decimal(3)), result


# =============================================================================
# concentration
# =============================================================================


class TestConcentration:
    @pytest.mark.parametrize("wrap", [list, iter], ids=["list", "iterator"])
    def test_no_weights(self, wrap):
        assert _weights().concentration(wrap([])) == (None, None)

    def test_one_position_is_ten_thousand_points(self):
        assert _weights().concentration([_d("100")]) == (_d("100"), _d("10000"))

    def test_largest_is_absolute_and_the_index_squares_signed_weights(self):
        assert _weights().concentration([_d("60"), _d("-30"), _d("10")]) == (_d("60"), _d("4600"))
        assert _weights().concentration([_d("-70"), _d("20")]) == (_d("70"), _d("5300"))

    def test_every_weight_counts_never_a_top_n(self):
        """Fifteen weights of 5 and one of 25: Σ w² = 15 × 25 + 625 = 1000, which a top-10 would miss."""
        weights_percent = [_d("5")] * 15 + [_d("25")]
        assert _weights().concentration(weights_percent) == (_d("25"), _d("1000"))

    def test_a_single_pass_generator_is_enough(self):
        """The callers hand it a generator over their holdings: one pass must feed both numbers."""
        source = [_d("56.08"), None, _d("43.92")]
        largest, herfindahl = _weights().concentration(weight for weight in source if weight is not None)
        assert (largest, herfindahl) == (_d("56.08"), _d("56.08") ** 2 + _d("43.92") ** 2)


# =============================================================================
# Parity with the old formulas: byte-identical wherever D-MF7 does not apply
# =============================================================================

ALLOCATIONS = {
    "ordinary": {"Stock": Decimal("600"), "ETF": Decimal("300"), "Cash": Decimal("100")},
    "negative-cash": {"Stock": Decimal("1500"), "Bond": Decimal("250.75"), "Cash": Decimal("-500")},
    "negative-sum": {"Stock": Decimal("100"), "Cash": Decimal("-300")},
    "net-zero": {"Stock": Decimal("500"), "Cash": Decimal("-500")},
    "empty": {},
    "all-zero": {"Stock": Decimal("0"), "Cash": Decimal("0.00")},
    "exponents": {"A": Decimal("1E+3"), "B": Decimal("2000.000"), "C": Decimal("-0.001")},
    "half-cent-tie": {"A": Decimal("12.345"), "B": Decimal("87.655")},
    "long-digits": {"A": Decimal("12345678901234567890.123456789"), "B": Decimal("3.3"), "Cash": Decimal("-7.77")},
}

# (holding values, engine NAV), every total above zero: the old and new weights must agree.
HOLDING_SETS = {
    "ordinary": ([Decimal("1130"), Decimal("885")], Decimal("10015")),
    "with-a-valueless-holding": ([Decimal("1130"), None, Decimal("0"), Decimal("885")], Decimal("10015")),
    "long-digits": ([Decimal("1234.567890123"), Decimal("0.01"), Decimal("98765.4321")], Decimal("150000.5")),
    "leveraged": ([Decimal("1510")], Decimal("510")),
    "a-negative-holding": ([Decimal("50"), Decimal("-80"), Decimal("1000")], Decimal("1770")),
    "exponents": ([Decimal("1E+3"), Decimal("250.00")], Decimal("1E+4")),
}

NAV_WEIGHT_SETS = {
    "empty": [],
    "all-none": [None, None],
    "single": [Decimal("100.00")],
    "ordinary": [Decimal("56.08"), None, Decimal("43.92")],
    "negative-weight": [Decimal("-10.39"), Decimal("6.49")],
    "tie-of-two-spellings": [Decimal("5.0"), Decimal("-5.00")],
    "tie-reversed": [Decimal("-5.00"), Decimal("5.0")],
    "exponent": [Decimal("1E+1")],
    "head-huge-weights": [Decimal("63000.00"), Decimal("30000.00")],
}

GROSS_POSITIONS = {
    "long-and-short-on-two-brokers": [(3, Decimal("300")), (1, Decimal("-100")), (2, None), (3, Decimal("50.50")), (7, Decimal("0"))],
    "empty": [],
    "all-zero": [(1, Decimal("0")), (2, Decimal("0.00"))],
    "only-none": [(1, None)],
    "exponents": [(5, Decimal("1E+3")), (2, Decimal("2000.000")), (9, Decimal("-0.001"))],
    "thirds": [(1, Decimal("1")), (2, Decimal("2"))],
}

RISK_SCOPES = {
    "nav-with-cash": ({1: Decimal("600"), 2: Decimal("300"), 3: Decimal("0")}, Decimal("1000")),
    "slice": ({1: Decimal("600"), 2: Decimal("300")}, Decimal("900")),
    "leveraged": ({1: Decimal("1510")}, Decimal("510")),
    "a-negative-value-left-out": ({1: Decimal("500"), 2: Decimal("-100")}, Decimal("600")),
    "thirds": ({1: Decimal("1")}, Decimal("3")),
    "zero-scope": ({1: Decimal("10")}, Decimal("0")),
    "negative-scope": ({1: Decimal("10")}, Decimal("-5")),
}


class TestParityWithTheOldFormulas:
    @pytest.mark.parametrize("amounts", list(ALLOCATIONS.values()), ids=list(ALLOCATIONS))
    def test_allocation_slices_are_the_old_alloc(self, amounts):
        """``derived_views``: ``slice_percents(d)[name].quantize(0.01)`` is the old ``(amt / (sum or 1) * 100).quantize(0.01)``,
        negative cash, negative and zero sums included — and so is every unrounded value."""
        new = _weights().slice_percents(amounts)
        old = _old_alloc_percents(amounts)
        assert _shown(new) == _shown(old), "unrounded slices differ"
        assert _shown({name: value.quantize(CENT) for name, value in new.items()}) == _shown({name: value.quantize(CENT) for name, value in old.items()})

    @pytest.mark.parametrize("values, engine_nav", list(HOLDING_SETS.values()), ids=list(HOLDING_SETS))
    def test_holding_weights_are_the_old_ones_on_totals_above_zero(self, values, engine_nav):
        """``portfolio_service``: ``percent_of`` rounded to 0.01 is the old weight wherever its total is above zero."""
        weights = _weights()
        total_market = sum((value for value in values if value), Decimal("0"))
        assert total_market > 0 and engine_nav > 0, "precondition: these sets keep both totals above zero"
        for value in values:
            if not value:
                continue
            allocation = weights.percent_of(value, total_market)
            nav_weight = weights.percent_of(value, engine_nav)
            assert allocation is not None and nav_weight is not None
            assert str(allocation.quantize(CENT)) == str(_old_allocation_percent(value, values)), f"allocation of {value}"
            assert str(nav_weight.quantize(CENT)) == str(_old_nav_weight_percent(value, engine_nav)), f"NAV weight of {value}"

    @pytest.mark.parametrize("nav_weights", list(NAV_WEIGHT_SETS.values()), ids=list(NAV_WEIGHT_SETS))
    def test_concentration_is_the_old_largest_and_herfindahl(self, nav_weights):
        """``broker_financial`` / ``broker_concentration_context``: the same pair, called as they call it."""
        new = _weights().concentration(weight for weight in nav_weights if weight is not None)
        old = _old_concentration(nav_weights)
        assert tuple(map(str, new)) == tuple(map(str, old)), f"new {new}, old {old}"

    @pytest.mark.parametrize("positions", list(GROSS_POSITIONS.values()), ids=list(GROSS_POSITIONS))
    def test_gross_weights_are_the_old_nav_weights(self, positions):
        """``technical_shared.compute_nav_weights``: ``gross_weights(dict(sorted(gross.items())))`` is the old tail, in order."""
        gross = _gross_by_asset(positions)
        new = _weights().gross_weights(dict(sorted(gross.items())))
        assert _shown(new) == _shown(_old_nav_weights_tail(gross))

    def test_gross_weights_take_the_absolute_value_themselves(self):
        """Signed values give the weights the old code computed on their absolute values."""
        signed = {1: Decimal("-100"), 2: Decimal("300"), 3: Decimal("-0.5")}
        new = _weights().gross_weights(signed)
        assert _shown(new) == _shown(_old_nav_weights_tail({key: abs(value) for key, value in signed.items()}))

    @pytest.mark.parametrize("asset_values, scope_value", list(RISK_SCOPES.values()), ids=list(RISK_SCOPES))
    def test_risk_weights_are_the_old_floats(self, asset_values, scope_value):
        """``risk/scope.load_scope_inputs``: ``float(share_of(value, scope))`` under the same guard is the old ``float(value / scope)``, to the bit."""
        weights = _weights()
        new = {asset_id: float(weights.share_of(value, scope_value)) for asset_id, value in asset_values.items() if value >= 0} if scope_value > 0 else {}
        old = _old_risk_weights(asset_values, scope_value)
        assert [(key, repr(value)) for key, value in new.items()] == [(key, repr(value)) for key, value in old.items()]


# =============================================================================
# D-MF7: the one intended difference
# =============================================================================


class TestDMF7Divergence:
    @pytest.mark.parametrize(
        "value, engine_nav, head",
        [("630", "-70", "63000.00"), ("700", "0", "70000.00"), ("-80", "-0.01", "-8000.00")],
        ids=["nav-below-zero", "nav-zero", "negative-holding-nav-below-zero"],
    )
    def test_no_nav_weight_where_head_divided_by_one(self, value, engine_nav, head):
        """HEAD: ``value / 1 × 100``. Now: None («—»)."""
        assert _old_nav_weight_percent(_d(value), _d(engine_nav)) == _d(head), "the old formula, as pinned here, gave this"
        assert _weights().percent_of(_d(value), _d(engine_nav)) is None

    @pytest.mark.parametrize(
        "holding_values, head",
        [(["50", "-80"], ["-166.67", "266.67"]), (["50", "-50"], ["5000.00", "-5000.00"])],
        ids=["total-below-zero", "total-zero"],
    )
    def test_no_allocation_where_head_divided_by_a_total_at_or_below_zero(self, holding_values, head):
        """HEAD: a division by the negative total, or by 1 on a zero total. Now: None for every holding."""
        values = [_d(value) for value in holding_values]
        total_market = sum(values, Decimal("0"))
        assert [_old_allocation_percent(value, values) for value in values] == [_d(text) for text in head], "the old formula, as pinned here, gave this"
        assert [_weights().percent_of(value, total_market) for value in values] == [None] * len(values)
