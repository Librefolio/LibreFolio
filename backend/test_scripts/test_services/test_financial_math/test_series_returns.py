"""
MF-D1 (workstream MF, lot D, part 1): the return of a series and its observed annualization get their home in
``returns.py``.

Module under test: ``backend/app/services/financial_math/returns.py``, two functions the series statistics read:

* ``float_price_return(start, end) -> float`` = ``float(price_return(start, end))``: the price return computed in
  Decimal, then rounded to a float once, which is what a return series carries. A series never carries an unavailable
  return, so where ``price_return`` answers None (a price missing, a zero start) this raises ``ValueError``. It
  replaces ``series_preparation._price_return_value``, which was the same function under a private name. The sign of the
  prices is NOT checked here: ``price_return`` divides whatever it gets, and the series callers validate positivity
  before calling (``series_preparation``'s valuation points are ``AssetValuationPoint``, whose ``target_close`` is
  ``gt=0``; the AI Export drawdown snapshot refuses a close ``<= 0`` as ``invalid_observed_prices``);
* ``observed_annualization(n_observations, baseline_date, final_date) -> tuple[int, float | None]``, moved verbatim from
  ``series_preparation.py``: the calendar span of the series and ``observations × 365 / days``.

And the parity guard: ``series_preparation`` keeps neither definition and does not re-export the moved name, so the
risk results and the comparison plugin import it from the house. ``series_preparation`` imports both names from the house
with ``from ... import``, which binds them in its namespace: whatever it binds must be the house's own object, never a
second implementation.

Red on HEAD (b05b80201): both names are imported at module level, so the whole file fails at collection with an
``ImportError`` (``cannot import name 'float_price_return'``).

MF-D3 (rule 10, the formula has one home): ``observations_per_year(n_observations, calendar_days) -> float`` is
``n_observations × 365 / calendar_days`` itself, ValueError for a span that is not positive; ``observed_annualization``
computes its factor with it, and the risk schemas' validators check a contract's factor against it (their guard is in
``test_schemas/test_risk_schemas.py``). Its tests read it as ``returns.observations_per_year`` inside the test body, never
with a module-level import, so the file still collects where the function does not exist: red on HEAD (f252acb4a) is an
``AttributeError`` in each of them, the MF-D1 tests above staying green.

Pure: no database, no server, no network.
"""

from __future__ import annotations

import ast
import math
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

import backend.app.services.series_preparation as series_preparation
from backend.app.services.financial_math import returns
from backend.app.services.financial_math.returns import float_price_return, observed_annualization, price_return

SERIES_PREPARATION_SOURCE = Path(series_preparation.__file__)

# =============================================================================
# observed_annualization — moved from test_series_preparation.py with its assertions unchanged
# =============================================================================


def test_observed_annualization_guards_empty_and_invalid_spans():
    assert observed_annualization(0, None, None) == (0, None)
    assert observed_annualization(
        64,
        date(2026, 1, 1),
        date(2026, 4, 1),
    ) == pytest.approx((90, 64 * 365 / 90))
    with pytest.raises(ValueError, match="cannot be negative"):
        observed_annualization(-1, None, None)
    with pytest.raises(ValueError, match="must follow"):
        observed_annualization(
            1,
            date(2026, 1, 1),
            date(2026, 1, 1),
        )


def test_observed_annualization_of_a_year_of_trading_days():
    # 252 observations over a 365-day calendar year: the factor is the observation count itself.
    assert observed_annualization(252, date(2025, 1, 1), date(2026, 1, 1)) == (365, 252.0)


def test_observed_annualization_factor_is_a_float_even_when_the_quotient_is_whole():
    # 365 observations over 365 days divide exactly: the factor is still the float 365.0, never the int 365. The span
    # stays an int — a count of days.
    calendar_days, factor = observed_annualization(365, date(2025, 1, 1), date(2026, 1, 1))

    assert type(calendar_days) is int
    assert calendar_days == 365
    assert type(factor) is float
    assert factor == 365.0


# =============================================================================
# observations_per_year — the one home of the annualization formula (MF-D3)
# =============================================================================


@pytest.mark.parametrize(
    ("n_observations", "calendar_days", "expected"),
    [
        pytest.param(252, 365, 252.0, id="a-year-of-trading-days"),
        pytest.param(10, 7, 521.4285714285714, id="ten-in-a-week"),
        pytest.param(64, 90, 259.55555555555554, id="a-quarter"),
        pytest.param(253, 366, 252.3087431693989, id="a-leap-year"),
        pytest.param(7, 3, 851.6666666666666, id="more-observations-than-days"),
        pytest.param(365, 365, 365.0, id="one-a-day"),
    ],
)
def test_observations_per_year_is_the_observations_times_365_over_the_span(n_observations, calendar_days, expected):
    factor = returns.observations_per_year(n_observations, calendar_days)

    # A float even where the quotient is whole (252.0, 365.0): the factor a contract carries, never an int.
    assert type(factor) is float
    # The contract, to the bit: the expression the validators and observed_annualization used to write themselves.
    assert factor == n_observations * 365 / calendar_days
    assert factor == expected


@pytest.mark.parametrize(
    ("n_observations", "calendar_days"),
    [
        pytest.param(252, 365, id="a-year-of-trading-days"),
        pytest.param(7, 3, id="more-observations-than-days"),
    ],
)
def test_observations_per_year_multiplies_before_it_divides(n_observations, calendar_days):
    # The trap is real: dividing first gives another float on these spans (252.00000000000003 and 851.6666666666667), so
    # the equality to the expression above does tell a reordered formula apart.
    assert n_observations / calendar_days * 365 != n_observations * 365 / calendar_days

    assert returns.observations_per_year(n_observations, calendar_days) == n_observations * 365 / calendar_days


@pytest.mark.parametrize("calendar_days", [0, -1, -365])
def test_observations_per_year_refuses_a_span_that_is_not_positive(calendar_days):
    with pytest.raises(ValueError, match="calendar_days"):
        returns.observations_per_year(10, calendar_days)


@pytest.mark.parametrize(
    ("n_observations", "baseline_date", "final_date", "calendar_days"),
    [
        pytest.param(252, date(2025, 1, 1), date(2026, 1, 1), 365, id="a-year"),
        pytest.param(253, date(2024, 1, 1), date(2025, 1, 1), 366, id="a-leap-year"),
        pytest.param(64, date(2026, 1, 1), date(2026, 4, 1), 90, id="a-quarter"),
        pytest.param(10, date(2026, 1, 1), date(2026, 1, 8), 7, id="a-week"),
        pytest.param(7, date(2026, 1, 1), date(2026, 1, 4), 3, id="more-observations-than-days"),
    ],
)
def test_observed_annualization_factor_is_observations_per_year_of_its_span(n_observations, baseline_date, final_date, calendar_days):
    span, factor = observed_annualization(n_observations, baseline_date, final_date)

    assert span == calendar_days
    assert factor == returns.observations_per_year(n_observations, calendar_days)


def test_observed_annualization_computes_its_factor_with_observations_per_year(monkeypatch):
    # Equal values could still be two copies of one formula: with the house function replaced, observed_annualization
    # must answer the replacement's value for the span it measured. raising=True (the default): where the function does
    # not exist, the patch itself fails.
    calls: list[tuple[int, int]] = []

    def stub(n_observations: int, calendar_days: int) -> float:
        calls.append((n_observations, calendar_days))
        return 42.0

    monkeypatch.setattr(returns, "observations_per_year", stub)

    assert observed_annualization(64, date(2026, 1, 1), date(2026, 4, 1)) == (90, 42.0)
    assert calls == [(64, 90)]


# =============================================================================
# float_price_return
# =============================================================================


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        pytest.param(Decimal("120"), Decimal("90"), -0.25, id="a-fall"),
        pytest.param(Decimal("100"), Decimal("110"), 0.1, id="a-rise"),
        pytest.param(Decimal("101.37"), Decimal("101.37"), 0.0, id="an-equal-pair-is-zero"),
        pytest.param(Decimal("0.1"), Decimal("0.3"), 2.0, id="a-tripling-exact-in-decimal"),
        pytest.param(Decimal("99.993"), Decimal("100.0001"), 7.100497034792435e-05, id="high-precision"),
    ],
)
def test_float_price_return_is_the_decimal_price_return_as_a_float(start, end, expected):
    result = float_price_return(start, end)

    assert type(result) is float
    # The contract, to the bit: the Decimal return of the house, rounded once.
    assert result == float(price_return(start, end))
    assert result == expected


def test_an_equal_pair_returns_a_positive_zero():
    # Decimal("101.37") / Decimal("101.37") - 1 is Decimal("0"): its float is 0.0, never a -0.0 a renderer prints as -0 %.
    result = float_price_return(Decimal("101.37"), Decimal("101.37"))

    assert result == 0.0
    assert math.copysign(1.0, result) == 1.0


@pytest.mark.parametrize(
    ("start", "end"),
    [
        pytest.param(Decimal("99.993"), Decimal("100.0001"), id="a-small-rise"),
        pytest.param(Decimal("0.1"), Decimal("0.3"), id="a-tripling"),
    ],
)
def test_float_price_return_rounds_once_and_not_the_float_quotient(start, end):
    # The trap is real: dividing the floats of the two prices and subtracting 1 gives another number on these pairs
    # (7.10049703480653e-05 and 1.9999999999999996), so the equality above does tell the two paths apart.
    naive = float(end) / float(start) - 1

    assert naive != float(price_return(start, end))
    assert float_price_return(start, end) == float(price_return(start, end))


@pytest.mark.parametrize(
    ("start", "end"),
    [
        pytest.param(Decimal("0"), Decimal("110"), id="a-zero-start"),
        pytest.param(Decimal("0.00"), Decimal("110"), id="a-zero-start-with-a-scale"),
        pytest.param(None, Decimal("110"), id="no-start"),
        pytest.param(Decimal("100"), None, id="no-end"),
    ],
)
def test_a_missing_price_or_a_zero_start_is_refused(start, end):
    # Where price_return answers None, a series has no return to carry: the caller's error, never a None in a float list.
    assert price_return(start, end) is None

    with pytest.raises(ValueError):
        float_price_return(start, end)


def test_a_zero_end_price_is_a_total_loss_not_an_error():
    # Only the START is a divisor: an end at 0 is a fall of everything, -1.0.
    assert float_price_return(Decimal("100"), Decimal("0")) == -1.0


def test_a_negative_start_is_not_refused_by_the_house():
    """The house divides what it gets: ``110 / -100 - 1`` is ``-2.1``, returned as is.

    The sign of a price is the series callers' check, made before they call: ``series_preparation`` builds its returns
    from valuation points whose ``target_close`` is validated positive upstream (``AssetValuationPoint``, ``gt=0``), and
    the AI Export drawdown snapshot turns a close ``<= 0`` into ``invalid_observed_prices`` before computing any return.
    Pinned so that a sign check added here later is a decision, not a side effect.
    """
    assert price_return(Decimal("-100"), Decimal("110")) == Decimal("-2.1")
    assert float_price_return(Decimal("-100"), Decimal("110")) == -2.1


# =============================================================================
# Parity guard: series_preparation keeps no copy and re-exports nothing it moved
# =============================================================================


def _top_level_functions(path: Path) -> set[str]:
    return {node.name for node in ast.parse(path.read_text(encoding="utf-8")).body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)}


def test_series_preparation_no_longer_defines_the_moved_functions():
    defined = _top_level_functions(SERIES_PREPARATION_SOURCE)
    # Presence barrier: the scan sees the module's own functions, so an empty set cannot pass for an absence.
    assert {"prepare_asset_series_set", "gap_slots", "fx_content_fingerprint"} <= defined

    assert "observed_annualization" not in defined
    assert "_price_return_value" not in defined


def test_series_preparation_does_not_re_export_observed_annualization():
    # Presence barrier: __all__ is there and still lists what the module does own.
    assert "prepare_asset_series_set" in series_preparation.__all__

    assert "observed_annualization" not in series_preparation.__all__


def test_series_preparation_has_no_private_price_return_left():
    assert not hasattr(series_preparation, "_price_return_value")


@pytest.mark.parametrize("name", ["observed_annualization", "float_price_return"])
def test_what_series_preparation_binds_of_the_house_is_the_house_object(name):
    # ``from ... import`` binds the name in series_preparation's namespace: it may be there, but only as the house's own
    # function — one implementation, never a copy that a later edit could make drift.
    bound = getattr(series_preparation, name, None)

    assert bound is None or bound is getattr(returns, name)
