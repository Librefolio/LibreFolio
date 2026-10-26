"""
Red tests for the ratio a stock split implies from a broker's import (workstream MF, lot MF-SPL1).

Module under test: ``backend/app/services/financial_math/splits.py`` — new names ``ImpliedSplitRatio`` and
``implied_split_ratio``, pure, next to ``is_valid_split_ratio``.

Why: a broker import (Revolut, Trading 212) sees a stock split only as shares added to a position, and files a
``possible_split`` todo for it. To label that todo the import needs the split the numbers imply — «3:1», «3:2» — and
how far the broker's added quantity is from the one that split would give, since brokers round fractional shares (the
Revolut TSLA 3-for-1 sample: 0.0822 held, 0.1643 added, where 3:1 gives 0.1644).

The contract pinned here:

* ``implied_split_ratio(held, added, *, max_denominator=10) -> ImpliedSplitRatio | None``;
* ``None`` when ``held <= 0`` or ``added <= 0`` (a reverse split, a missing position, nothing added), and when the
  snapped fraction is not above 1 (an added amount too small for any split of denominator ≤ ``max_denominator``);
* ``exact_ratio = (held + added) / held`` in the default Decimal context;
* ``numerator / denominator = Fraction(exact_ratio).limit_denominator(max_denominator)``, from the Decimal, exact,
  reduced, as ``int``;
* ``ratio = Decimal(numerator) / Decimal(denominator)``;
* ``rounding_gap = added - held * (numerator - denominator) / denominator``, Decimals, evaluated in that order: what the
  broker's number differs from the split's, ``0`` when exact;
* ``ImpliedSplitRatio`` is a frozen, slotted dataclass of those five fields.

Every expected value below is a literal worked out once from the formulas above in the default context (precision 28):
a test never recomputes the expectation with the formula it checks.

Red by absence until MF-SPL1: ``splits.py`` exists, the names do not. Each test reads them off the module when it runs
(``_implied_split_ratio()`` / ``_implied_split_ratio_class()``), never at module level, so the file collects on HEAD and
every test fails on ``AttributeError``. PURE: no database, no server, no network.
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
from collections.abc import Callable
from decimal import Decimal
from types import ModuleType
from typing import Any

import pytest

SPLITS_MODULE = "backend.app.services.financial_math.splits"

IMPLIED_FIELDS = ("numerator", "denominator", "ratio", "exact_ratio", "rounding_gap")


def _splits() -> ModuleType:
    return importlib.import_module(SPLITS_MODULE)


def _implied_split_ratio() -> Callable[..., Any]:
    """``splits.implied_split_ratio``, read when a test runs: until MF-SPL1 the module has no such name."""
    return _splits().implied_split_ratio


def _implied_split_ratio_class() -> type:
    """``splits.ImpliedSplitRatio``, read when a test runs."""
    return _splits().ImpliedSplitRatio


def _implied(held: str, added: str, **kwargs: Any) -> Any:
    return _implied_split_ratio()(Decimal(held), Decimal(added), **kwargs)


def _assert_split(result: Any, *, numerator: int, denominator: int, ratio: str, exact_ratio: str, rounding_gap: str) -> None:
    assert result is not None, "a multiplicative split was expected, got None"
    assert isinstance(result, _implied_split_ratio_class())
    assert (result.numerator, result.denominator) == (numerator, denominator)
    assert type(result.numerator) is int and type(result.denominator) is int
    for name, expected in (("ratio", ratio), ("exact_ratio", exact_ratio), ("rounding_gap", rounding_gap)):
        value = getattr(result, name)
        assert isinstance(value, Decimal), f"{name} is {type(value).__name__}, not Decimal"
        assert value == Decimal(expected), f"{name}: {value!r} != Decimal({expected!r})"


# =============================================================================
# The Revolut sample
# =============================================================================


class TestRevolutSample:
    """TSLA 3-for-1 as Revolut exports it: 0.0822 held, 0.1643 added — the split is 3:1, the broker rounded down."""

    def test_snaps_to_three_for_one(self) -> None:
        result = _implied("0.0822", "0.1643")
        _assert_split(result, numerator=3, denominator=1, ratio="3", exact_ratio="2.998783454987834549878345499", rounding_gap="-0.0001")

    def test_exact_ratio_is_the_default_context_quotient(self) -> None:
        # (0.0822 + 0.1643) / 0.0822 = 0.2465 / 0.0822, 28 significant digits, the last one rounded half-even.
        result = _implied("0.0822", "0.1643")
        assert result.exact_ratio.as_tuple() == Decimal("2.998783454987834549878345499").as_tuple()

    def test_rounding_gap_is_minus_one_ten_thousandth_exactly(self) -> None:
        # 3:1 on 0.0822 adds 0.0822 × 2 = 0.1644; the broker wrote 0.1643.
        result = _implied("0.0822", "0.1643")
        assert result.rounding_gap == Decimal("-0.0001")
        assert result.rounding_gap.is_signed()


# =============================================================================
# Exact splits: gap 0
# =============================================================================


class TestExactSplits:
    @pytest.mark.parametrize(
        ("held", "added", "numerator", "denominator", "ratio", "exact_ratio"),
        [
            pytest.param("10", "20", 3, 1, "3", "3", id="3:1"),
            pytest.param("100", "50", 3, 2, "1.5", "1.5", id="3:2-reduced-from-150/100"),
            pytest.param("7", "63", 10, 1, "10", "10", id="10:1"),
            pytest.param("8", "2", 5, 4, "1.25", "1.25", id="5:4"),
            pytest.param("1", "19", 20, 1, "20", "20", id="20:1"),
            pytest.param("10", "4", 7, 5, "1.4", "1.4", id="7:5"),
            pytest.param("0.3333", "0.3333", 2, 1, "2", "2", id="2:1-on-fractional-0.3333"),
        ],
    )
    def test_exact_split_has_zero_gap(self, held: str, added: str, numerator: int, denominator: int, ratio: str, exact_ratio: str) -> None:
        result = _implied(held, added)
        _assert_split(result, numerator=numerator, denominator=denominator, ratio=ratio, exact_ratio=exact_ratio, rounding_gap="0")

    def test_whole_ratio_ignores_max_denominator(self) -> None:
        """20:1 has denominator 1: any ``max_denominator`` finds it."""
        for max_denominator in (1, 2, 10, 100):
            result = _implied("1", "19", max_denominator=max_denominator)
            _assert_split(result, numerator=20, denominator=1, ratio="20", exact_ratio="20", rounding_gap="0")


# =============================================================================
# Fractional shares, broker rounding
# =============================================================================


class TestBrokerRounding:
    """Brokers round the added fractional quantity to 4 or 6 decimals, up or down: the split still snaps, the gap shows it."""

    @pytest.mark.parametrize(
        ("held", "added", "numerator", "denominator", "ratio", "exact_ratio", "rounding_gap"),
        [
            # 6 decimals: 3:1 on 0.123457 adds 0.246914.
            pytest.param("0.123457", "0.246915", 3, 1, "3", "3.000008099986230023408960205", "0.000001", id="6dp-3:1-rounded-up"),
            pytest.param("0.123457", "0.246913", 3, 1, "3", "2.999991900013769976591039795", "-0.000001", id="6dp-3:1-rounded-down"),
            # 4 decimals: 4:1 on 0.0457 adds 0.1371.
            pytest.param("0.0457", "0.1372", 4, 1, "4", "4.002188183807439824945295405", "0.0001", id="4dp-4:1-rounded-up"),
            pytest.param("0.0457", "0.1370", 4, 1, "4", "3.997811816192560175054704595", "-0.0001", id="4dp-4:1-rounded-down"),
            # 4 decimals: 3:2 on 0.0333 adds 0.01665, which the broker writes as 0.0167.
            pytest.param("0.0333", "0.0167", 3, 2, "1.5", "1.501501501501501501501501502", "0.00005", id="4dp-3:2-half-up"),
            pytest.param("0.0333", "0.0166", 3, 2, "1.5", "1.498498498498498498498498498", "-0.00005", id="4dp-3:2-half-down"),
            # 2:1 on 0.3333 adds 0.3333; written 0.3334.
            pytest.param("0.3333", "0.3334", 2, 1, "2", "2.000300030003000300030003000", "0.0001", id="4dp-2:1-on-0.3333-rounded-up"),
        ],
    )
    def test_rounded_quantity_snaps_and_reports_gap(self, held: str, added: str, numerator: int, denominator: int, ratio: str, exact_ratio: str, rounding_gap: str) -> None:
        result = _implied(held, added)
        _assert_split(result, numerator=numerator, denominator=denominator, ratio=ratio, exact_ratio=exact_ratio, rounding_gap=rounding_gap)


# =============================================================================
# None: no multiplicative split to label
# =============================================================================


class TestNoSplit:
    @pytest.mark.parametrize(
        ("held", "added"),
        [
            pytest.param("0", "10", id="held-zero"),
            pytest.param("0.000000", "10", id="held-zero-with-exponent"),
            pytest.param("-5", "10", id="held-negative"),
            pytest.param("10", "0", id="added-zero"),
            pytest.param("10", "-5", id="added-negative-reverse-split"),
            pytest.param("-5", "-5", id="both-negative"),
        ],
    )
    def test_non_positive_input_gives_none(self, held: str, added: str) -> None:
        assert _implied(held, added) is None

    def test_added_too_small_to_snap_above_one_gives_none(self) -> None:
        """100 held, 0.01 added: exact ratio 1.0001, nearest fraction with denominator ≤ 10 is 1/1 — not a split."""
        assert _implied("100", "0.01") is None

    def test_added_too_small_with_a_larger_max_denominator_is_a_split(self) -> None:
        """The snap decides, not a fixed threshold: 1.0001 with max_denominator 10000 is 10001:10000, gap 0."""
        result = _implied("100", "0.01", max_denominator=10000)
        _assert_split(result, numerator=10001, denominator=10000, ratio="1.0001", exact_ratio="1.0001", rounding_gap="0")


# =============================================================================
# max_denominator
# =============================================================================


class TestMaxDenominator:
    def test_default_is_ten_and_keyword_only(self) -> None:
        parameter = inspect.signature(_implied_split_ratio()).parameters["max_denominator"]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default == 10

    def test_seven_for_five_found_with_the_default(self) -> None:
        result = _implied("10", "4")
        _assert_split(result, numerator=7, denominator=5, ratio="1.4", exact_ratio="1.4", rounding_gap="0")

    def test_seven_for_five_not_found_with_max_denominator_four(self) -> None:
        """1.4 with denominators ≤ 4: 4/3 (off by 0.0667) beats 3/2 (off by 0.1); the gap is 4 − 10 × 1 / 3."""
        result = _implied("10", "4", max_denominator=4)
        _assert_split(
            result,
            numerator=4,
            denominator=3,
            ratio="1.333333333333333333333333333",
            exact_ratio="1.4",
            rounding_gap="0.666666666666666666666666667",
        )
        assert abs(result.rounding_gap) > abs(_implied("10", "4").rounding_gap)


# =============================================================================
# Types and shape
# =============================================================================


class TestTypes:
    def test_three_for_one_ratio_is_decimal_three(self) -> None:
        result = _implied("10", "20")
        assert result.ratio.as_tuple() == Decimal("3").as_tuple()

    def test_three_for_two_ratio_is_the_default_context_quotient(self) -> None:
        result = _implied("100", "50")
        assert result.ratio.as_tuple() == Decimal("1.5").as_tuple()

    def test_fields_in_order(self) -> None:
        cls = _implied_split_ratio_class()
        assert dataclasses.is_dataclass(cls)
        assert tuple(field.name for field in dataclasses.fields(cls)) == IMPLIED_FIELDS

    def test_frozen_and_slotted(self) -> None:
        cls = _implied_split_ratio_class()
        assert "__slots__" in vars(cls)
        result = _implied("10", "20")
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.numerator = 4  # type: ignore[misc]
