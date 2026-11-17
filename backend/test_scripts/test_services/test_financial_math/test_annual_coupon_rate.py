"""
The annual coupon rate from the period coupon (plan 68, lot C2): ``financial_math/interest.py``.

A bond sheet may give only the coupon of one period (an ordinary BTP on Borsa Italiana: «cedola periodale» 3.00, paid
twice a year, no annual rate). The annual rate is then the period rate times the coupons in a year — a financial formula,
so it has one home, here (plan: «la cedola annua mancante si calcola in ``financial_math/``»).

Pinned:

1. ``COUPONS_PER_YEAR``, a ``Mapping[str, int]``: the ``coupon_frequency`` choice codes of the profile catalogue with a
   fixed count — ``monthly`` 12, ``quarterly`` 4, ``semiannual`` 2, ``annual`` 1 — and nothing else: ``at_maturity`` has
   no count (one coupon at the end, not a yearly rate), so its keys are exactly the catalogue's choices minus it.
2. ``annual_coupon_rate(period_rate, frequency) -> Decimal | None``: ``period_rate × COUPONS_PER_YEAR[frequency]``,
   an exact ``Decimal`` (no rounding, no quantize: every value here fits the default 28-digit context, so the exact
   product is what the context gives); the same on a percent or a fraction (it is a product, the unit passes through);
   zero stays zero. ``None`` for ``at_maturity`` and for any other text that is not one of the codes — a page's own
   wording («Quarterly», «Semestrale») is the enricher's to translate first.

Red before C2: neither name exists. They are imported in a fixture, so each test fails on its own (``ImportError``) and
the directory run of ``services financial-math`` still collects the other files.

PURE: no database, no server, no network.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, localcontext
from types import SimpleNamespace

import pytest

from backend.app.services.assets.profile.catalogue import get_voice

EXPECTED_COUNTS = {"monthly": 12, "quarterly": 4, "semiannual": 2, "annual": 1}


@pytest.fixture
def interest() -> SimpleNamespace:
    """The two names under test, imported in the test's own setup (never at collection)."""
    from backend.app.services.financial_math.interest import COUPONS_PER_YEAR, annual_coupon_rate  # noqa: PLC0415 — red per test, not at collection

    return SimpleNamespace(COUPONS_PER_YEAR=COUPONS_PER_YEAR, annual_coupon_rate=annual_coupon_rate)


def _exact(a: Decimal, b: int) -> Decimal:
    """The exact product, in a context wide enough never to round."""
    with localcontext() as context:
        context.prec = 80
        return a * b


# =============================================================================
# 1. COUPONS_PER_YEAR
# =============================================================================


def test_coupons_per_year_counts(interest):
    counts = interest.COUPONS_PER_YEAR
    assert isinstance(counts, Mapping), f"a Mapping: {type(counts).__name__}"
    assert dict(counts) == EXPECTED_COUNTS
    assert all(type(count) is int for count in counts.values()), f"int counts: {dict(counts)}"


def test_coupons_per_year_are_the_catalogue_codes_but_at_maturity(interest):
    choices = set(get_voice("coupon_frequency").choices)
    assert "at_maturity" in choices, f"barrier: the catalogue lists at_maturity: {sorted(choices)}"
    assert set(interest.COUPONS_PER_YEAR) == choices - {"at_maturity"}


# =============================================================================
# 2. annual_coupon_rate
# =============================================================================


@pytest.mark.parametrize(
    ("period_rate", "frequency", "annual"),
    [
        # the recorded BTPs, in percent as the page gives them
        (Decimal("3.00"), "semiannual", Decimal("6")),  # btp_ord: «Btp-1mg31 6%»
        (Decimal("1.075"), "semiannual", Decimal("2.15")),  # btp_2072: «Btp Tf 2,15% Mz72»
        (Decimal("1.125"), "quarterly", Decimal("4.5")),  # btp_valore, which also gives 4.50
        (Decimal("0.925"), "semiannual", Decimal("1.85")),  # btp_italia, which also gives 1.85
        (Decimal("2.10"), "annual", Decimal("2.1")),  # austria_2117, which also gives 2.10
        (Decimal("0.5"), "monthly", Decimal("6")),
        # the same as fractions
        (Decimal("0.03"), "semiannual", Decimal("0.06")),
        (Decimal("0.01075"), "semiannual", Decimal("0.0215")),
        (Decimal("0.01125"), "quarterly", Decimal("0.045")),
        # zero coupon per period
        (Decimal("0"), "quarterly", Decimal("0")),
    ],
)
def test_annual_rate_is_period_times_coupons_per_year(interest, period_rate, frequency, annual):
    result = interest.annual_coupon_rate(period_rate, frequency)
    assert isinstance(result, Decimal), f"a Decimal, not {type(result).__name__}"
    assert result == annual, f"{period_rate} × {EXPECTED_COUNTS[frequency]}: {result}"


@pytest.mark.parametrize(
    ("period_rate", "frequency"),
    [
        (Decimal("1.03125"), "semiannual"),  # 2.0625: two decimals would lose it
        (Decimal("0.0001"), "monthly"),  # 0.0012
        (Decimal("1.0416666667"), "monthly"),  # 12.5000000004: no rounding to a «nice» rate
        (Decimal("0.123456789012345678901"), "quarterly"),  # 21 decimals kept
    ],
)
def test_annual_rate_is_exact(interest, period_rate, frequency):
    count = EXPECTED_COUNTS[frequency]
    expected = _exact(period_rate, count)
    assert len(expected.as_tuple().digits) <= 28, "barrier: the exact product fits the default context"
    assert interest.annual_coupon_rate(period_rate, frequency) == expected


@pytest.mark.parametrize("frequency", sorted(EXPECTED_COUNTS))
def test_percent_and_fraction_give_the_same_rate(interest, frequency):
    percent = Decimal("1.125")
    fraction = percent / 100
    on_percent = interest.annual_coupon_rate(percent, frequency)
    on_fraction = interest.annual_coupon_rate(fraction, frequency)
    assert on_percent is not None and on_fraction is not None
    assert on_fraction * 100 == on_percent, f"{frequency}: {on_fraction} × 100 ≠ {on_percent}"


@pytest.mark.parametrize("frequency", ["at_maturity", "", "biennial", "Quarterly", "Semestrale", "12 Months", " quarterly"])
def test_no_annual_rate_for_at_maturity_or_an_unknown_code(interest, frequency):
    assert interest.annual_coupon_rate(Decimal("1.5"), frequency) is None
