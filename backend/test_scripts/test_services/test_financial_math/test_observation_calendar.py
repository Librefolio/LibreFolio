"""
J-1, item 1 (workstream MF; the developer's go of 19/10, with J's six conditions): the conversions between calendar days
and observations move into the one home of the financial math. No value changes.

Module under test: ``backend/app/services/financial_math/returns.py`` —

* ``DAYS_PER_YEAR = 365``: the one constant of the observed annualization. ``observations_per_year`` reads it (it wrote
  the literal before), and so do both conversions: no 365 is written again;
* ``positive_annualization_factor(annualization_factor)``: a factor as a float, refused unless finite and positive
  (``ValueError("annualization_factor must be finite and positive")``). Moved as it was from ``risk/metrics.py``, where
  it was the private ``_positive_annualization_factor`` of seven call sites that now import it from the house;
* ``calendar_days_to_observations(calendar_days, per_year)``: moved as it was from ``risk/metrics.py``,
  ``max(1, round(calendar_days × per_year / DAYS_PER_YEAR))``, ``ValueError("calendar_days must be a positive
  integer")`` for a bool or a count ≤ 0. Its five callers import it from the house: ``risk_plugins/asset_set_var``,
  ``risk_plugins/historical_var``, ``risk_plugins/simulation``, ``risk/quant/models.py``, ``risk/quant/resampling.py``;
* ``observations_to_calendar_days(observations, per_year)``: new, the inverse,
  ``max(1, round(observations × DAYS_PER_YEAR / per_year))``, ``ValueError("observations must be a positive integer")``
  for a bool or a count ≤ 0. Until J-1 it was written in line at ``risk/quant/resampling.py:235``, the block length the
  bootstrap discloses in calendar days: ``"block_length_days": max(1, round(block_length * 365 / steps_per_year))``.

The oracles are verbatim copies of HEAD ``8eb783b0b`` (``*_today``): what ``risk/metrics.py``, ``returns.py`` and the
line of ``resampling.py`` computed before the move. Ints are compared with ``==`` and their type, floats with ``==``,
refusals by class and message.

What reaches the inverse today. ``run_block_bootstrap`` hands it ``block_length`` and ``steps_per_year``:

* ``block_length = resolve_block_length(observations, block_override)``, whose two returns are
  ``max(1, min(override, observations))`` and ``max(2, min(observations, round(observations ** (1 / 3))))``: an ``int``
  of at least 1, never a bool (``round`` of a float is an int, ``shape`` gives ints, and the override is the int
  ``calendar_days_to_observations`` returns). So the count refusal of the inverse never fires on that path;
* ``steps_per_year`` is ``request.effective_steps_per_year``, which already went through the validator of the house at
  ``resampling.py:179`` (``calendar_days_to_observations(horizon_days, steps_per_year)``) before line 235 is reached: a
  factor the inverse refuses was refused there first, with the same ``ValueError``.

So the new refusals of ``observations_to_calendar_days`` refuse nothing the disclosure gets today; the grid of block
lengths 1..400 (and the longest block the path admits, ``MAX_HISTORY_OBSERVATIONS``) proves it on the factors below.

The pins of ``block_length_days`` in the risk suite (``grep -rn block_length_days backend/test_scripts``), all pure
values cross-checked here through the house and through HEAD's line:

* the disclosure (what ``run_block_bootstrap`` returns, in calendar days) —
  ``test_risk_simulation.py::test_the_block_length_is_resolved_in_steps_and_disclosed_in_calendar_days``: 60
  observations, 5 days at 252.0 → 4; 5 days at 365.0 → 5; no override at 252.0 → 6; no override at 365.0 → 4;
  ``::test_block_length_follows_the_cube_root_rule_and_is_disclosed``: 1250 observations at the default 365.0 → 11, an
  override of 25 days → 25; ``::test_with_the_step_frequency_unset_the_bootstrap_gives_the_results_captured_before_it``
  (``CAPTURED_BEFORE_STEPS["…"]["disclosure"]``): the default history of 756 observations at 365.0 → 9, with a 5-day
  block → 5; ``::test_bootstrap_*`` at lines ~807, ~1089, ~1362: ``block_length_days == resolve_block_length(n)`` at
  the default 365.0, i.e. the identity ``observations_to_calendar_days(b, 365.0) == b``;
* the request (days the user declared, converted forward) — ``test_risk_simulation.py``: 40 days at 252.0 → 28
  observations, 50 → 35, 30 at 365.0 → 30, 31 → 31, 900 at 365.0 → 900; ``test_risk_analytics.py``: 40 and 50 days at
  252.0 (28 and 35 observations); ``test_risk_metrics.py``: (1, 252) → 1, (426, 252) → 294, (5, 252) → 3 and the rest
  of its table;
* the other hits are not values: ``test_risk_simulation.py:769`` and ``test_risk_analytics.py:2630`` are fake outputs,
  ``:1034-1056`` the contract that requires the field, ``:1508`` the configuration of the captured pins above,
  ``test_risk_api.py:591`` a ``not None``.

Red before J-1, each test on its own: ``returns`` is imported whole and the new names are read when a test runs, so a
missing one is the ``AttributeError`` of that test, never a collection error of the file; the guard of the callers
finds the old function of ``risk.metrics`` in their namespaces, the structural guards find HEAD's definitions and its
``365``. Green on both sides by design: ``test_observations_per_year_reads_as_today``, a parity guard on a name HEAD has.

Pure: no database, no server, no network. The structural guards parse source files with ``ast`` and never import them.
"""

from __future__ import annotations

import ast
import functools
import math
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from backend.app.services.financial_math import returns
from backend.app.services.risk import metrics as risk_metrics
from backend.app.services.risk.quant import models as quant_models
from backend.app.services.risk.quant import resampling
from backend.app.services.risk_plugins.asset_set_var import plugin as asset_set_var_plugin
from backend.app.services.risk_plugins.historical_var import plugin as historical_var_plugin
from backend.app.services.risk_plugins.simulation import plugin as simulation_plugin

REPO_ROOT = Path(__file__).resolve().parents[4]
APP_ROOT = REPO_ROOT / "backend" / "app"
HOME = "services/financial_math/returns.py"
FORMER_HOME = "services/risk/metrics.py"
RESAMPLER = "services/risk/quant/resampling.py"

#: The test's own year, independent of the constant under test: a house that changed it must disagree with this file.
YEAR = 365

#: The observed factors under test: trading days, a fractional observed factor, weekly, monthly, yearly, denser than daily.
FACTORS = (252, 251.7, 260, 365, 52, 12, 1, 1000)
#: The same, plus the factors as the bootstrap carries them: ``effective_steps_per_year`` is a float
#: (``DEFAULT_STEPS_PER_YEAR = 365.0``).
PATH_FACTORS = (*FACTORS, 252.0, 365.0)
#: Valid but extreme: the inverse overflows on the subnormal one exactly as HEAD's line did.
EXTREME_FACTORS = (1e-300, 5e-324, 1e308, 1.7976931348623157e308)
INVALID_FACTORS = (0, 0.0, -0.0, -1, -252.0, math.inf, -math.inf, math.nan)
INVALID_COUNTS = (True, False, 0, -1, -30)
CALENDAR_DAYS = range(1, 801)
BLOCK_LENGTHS = range(1, 401)

COUNT_MESSAGE = "observations must be a positive integer"
FACTOR_MESSAGE = "annualization_factor must be finite and positive"


# =============================================================================
# HEAD 8eb783b0b, verbatim (docstrings aside)
# =============================================================================


def _positive_annualization_factor_today(annualization_factor: float) -> float:
    """``risk/metrics.py::_positive_annualization_factor`` at HEAD."""
    normalized = float(annualization_factor)
    if normalized <= 0 or not math.isfinite(normalized):
        raise ValueError("annualization_factor must be finite and positive")
    return normalized


def _calendar_days_to_observations_today(calendar_days: int, per_year: float) -> int:
    """``risk/metrics.py::calendar_days_to_observations`` at HEAD."""
    if isinstance(calendar_days, bool) or calendar_days <= 0:
        raise ValueError("calendar_days must be a positive integer")
    return max(1, round(calendar_days * _positive_annualization_factor_today(per_year) / 365))


def _observations_per_year_today(n_observations: int, calendar_days: int) -> float:
    """``financial_math/returns.py::observations_per_year`` at HEAD."""
    if calendar_days <= 0:
        raise ValueError("calendar_days must be positive")
    return n_observations * 365 / calendar_days


def _block_length_days_today(block_length: int, steps_per_year: float) -> int:
    """``risk/quant/resampling.py:235`` at HEAD, the value of ``"block_length_days"`` in the disclosure."""
    return max(1, round(block_length * 365 / steps_per_year))


def _outcome(function, *args):
    """What a call gives: its value and type, or the class and message of what it raises."""
    try:
        value = function(*args)
    except Exception as error:
        return "raises", type(error), str(error)
    return "returns", type(value), value


# =============================================================================
# DAYS_PER_YEAR and observations_per_year
# =============================================================================


def test_a_year_of_the_observed_annualization_is_365_calendar_days():
    assert returns.DAYS_PER_YEAR == YEAR
    assert type(returns.DAYS_PER_YEAR) is int


@pytest.mark.parametrize("n_observations", (0, 1, 2, 21, 30, 251, 252, 253, 365, 1000, 5000))
def test_observations_per_year_reads_as_today(n_observations):
    """A parity guard, green before and after J-1: the factor now reads ``DAYS_PER_YEAR`` instead of the literal."""
    for calendar_days in CALENDAR_DAYS:
        factor = returns.observations_per_year(n_observations, calendar_days)
        assert type(factor) is float
        assert factor == _observations_per_year_today(n_observations, calendar_days), f"{n_observations} observations over {calendar_days} days"
    for calendar_days in (0, -1, -365):
        assert _outcome(returns.observations_per_year, n_observations, calendar_days) == _outcome(_observations_per_year_today, n_observations, calendar_days)


# =============================================================================
# positive_annualization_factor
# =============================================================================

_FACTOR_INPUTS = (
    *(1, 12, 52, 252, 365, 1000, 251.7, *EXTREME_FACTORS),
    *(True, Fraction(1, 3), Decimal("252"), Decimal("251.7"), "252"),
    *(np.float64(252.0), np.float64(251.7), np.int64(252), np.float32(251.7)),
    *INVALID_FACTORS,
    *(np.float64(0.0), np.float64(-1.0), np.float64(np.inf), np.float64(np.nan), Decimal("0"), Decimal("NaN"), Decimal("-Infinity")),
    *(None, "abc", Decimal("sNaN")),
)


@pytest.mark.parametrize("annualization_factor", _FACTOR_INPUTS, ids=repr)
def test_the_factor_validator_answers_as_the_private_one_of_the_risk_module_did(annualization_factor):
    """Same value and type (a float), or same refusal: class and message — its own ``ValueError`` for 0, a negative,
    ``inf`` and ``nan`` in any numeric type, and whatever ``float()`` raises for what is not a number."""
    expected = _outcome(_positive_annualization_factor_today, annualization_factor)
    assert _outcome(returns.positive_annualization_factor, annualization_factor) == expected


@pytest.mark.parametrize("annualization_factor", (*INVALID_FACTORS, np.float64(0.0), np.float64(np.nan)), ids=repr)
def test_the_factor_validator_refuses_a_factor_that_describes_no_year(annualization_factor):
    with pytest.raises(ValueError) as refused:
        returns.positive_annualization_factor(annualization_factor)
    assert str(refused.value) == FACTOR_MESSAGE


# =============================================================================
# calendar_days_to_observations
# =============================================================================


@pytest.mark.parametrize("per_year", FACTORS)
def test_calendar_days_convert_to_observations_as_the_risk_module_did(per_year):
    for calendar_days in CALENDAR_DAYS:
        converted = returns.calendar_days_to_observations(calendar_days, per_year)
        assert type(converted) is int
        assert converted == _calendar_days_to_observations_today(calendar_days, per_year), f"{calendar_days} days at {per_year} a year"


@pytest.mark.parametrize(
    ("calendar_days", "per_year", "observations"),
    [
        pytest.param(1, 252, 1, id="a-day-of-a-252-a-year-series"),
        pytest.param(426, 252, 294, id="the-prolonged-crisis-in-252-a-year-steps"),
        pytest.param(5, 252, 3, id="a-five-day-block-in-252-a-year-steps"),
        pytest.param(40, 252.0, 28, id="a-40-day-block-fits-30-observations"),
        pytest.param(50, 252.0, 35, id="a-50-day-block-does-not"),
        pytest.param(30, 365.0, 30, id="unset-a-day-is-an-observation"),
        pytest.param(31, 365.0, 31, id="unset-31-days-are-31-observations"),
        pytest.param(900, 365.0, 900, id="the-refused-900-day-block"),
    ],
)
def test_the_pinned_conversions_keep_their_values(calendar_days, per_year, observations):
    assert returns.calendar_days_to_observations(calendar_days, per_year) == observations
    assert _calendar_days_to_observations_today(calendar_days, per_year) == observations


@pytest.mark.parametrize(
    ("calendar_days", "per_year"),
    [
        *[pytest.param(days, 252.0, id=f"days-{days!r}") for days in INVALID_COUNTS],
        *[pytest.param(30, factor, id=f"factor-{factor!r}") for factor in INVALID_FACTORS],
        pytest.param(0, math.nan, id="both-wrong-the-days-are-refused-first"),
        pytest.param(True, 0, id="a-bool-and-a-zero-factor"),
    ],
)
def test_calendar_days_to_observations_refuses_what_it_refused(calendar_days, per_year):
    expected = _outcome(_calendar_days_to_observations_today, calendar_days, per_year)
    assert expected[:2] == ("raises", ValueError)
    assert _outcome(returns.calendar_days_to_observations, calendar_days, per_year) == expected


# =============================================================================
# observations_to_calendar_days
# =============================================================================


@pytest.mark.parametrize("steps_per_year", PATH_FACTORS)
def test_the_disclosed_block_length_reads_as_the_line_of_the_resampler_did(steps_per_year):
    """Exact parity, as an int, with ``max(1, round(block_length * 365 / steps_per_year))`` — the block lengths 1..400 and
    the longest the bootstrap admits (``MAX_HISTORY_OBSERVATIONS``: ``models.py`` refuses a block longer than the
    history, and the history is capped there)."""
    for block_length in (*BLOCK_LENGTHS, quant_models.MAX_HISTORY_OBSERVATIONS):
        disclosed = returns.observations_to_calendar_days(block_length, steps_per_year)
        assert type(disclosed) is int
        assert disclosed == _block_length_days_today(block_length, steps_per_year), f"a block of {block_length} steps at {steps_per_year} a year"


def test_the_inverse_refuses_nothing_the_disclosure_receives_today():
    """The argument of the module docstring, run.

    1. ``resolve_block_length`` hands over an int of at least 1, never a bool: every history length up to 400 (and the
       cap), with no override and with overrides below, at and above it.
    2. The factors: the inverse refuses exactly the factors ``calendar_days_to_observations`` refuses at
       ``resampling.py:179``, with the same ``ValueError``; a factor the validator lets through is never refused by
       the inverse, and every one answers as HEAD's line did — the extreme ones included: the subnormal ``5e-324``
       overflows ``round`` on the way back in both (and ``1e308`` already overflows forward, at line 179, as before).
    """
    for observations in (*range(0, 401), quant_models.MAX_HISTORY_OBSERVATIONS):
        for override in (None, 1, 2, max(1, observations - 1), observations + 1, 10**6):
            block_length = resampling.resolve_block_length(observations, override)
            assert type(block_length) is int and block_length >= 1, f"resolve_block_length({observations}, {override}) = {block_length!r}"
    for factor in INVALID_FACTORS:
        at_line_179 = _outcome(returns.calendar_days_to_observations, 30, factor)
        assert at_line_179[:2] == ("raises", ValueError)
        assert _outcome(returns.observations_to_calendar_days, 3, factor) == at_line_179
    for factor in (*PATH_FACTORS, *EXTREME_FACTORS):
        assert _outcome(returns.positive_annualization_factor, factor)[0] == "returns"
        for block_length in (1, 2, 400):
            back = _outcome(returns.observations_to_calendar_days, block_length, factor)
            assert back[:2] != ("raises", ValueError), f"{block_length} at {factor!r}: {back}"
            assert back == _outcome(_block_length_days_today, block_length, factor), f"{block_length} at {factor!r}"


@pytest.mark.parametrize("per_year", FACTORS)
def test_days_to_observations_and_back_is_within_one_rounding(per_year):
    """``observations_to_calendar_days(calendar_days_to_observations(d, s), s)`` is not ``d``: each way rounds.

    The bound proved, for ``x = d × s / 365``:

    * when ``round(x) ≥ 1``, ``o = round(x)`` is within ½ of ``x``, so ``o × 365 / s`` is within ``365 / (2s)`` of ``d``,
      and the second rounding adds ½: ``|back − d| ≤ 365 / (2s) + ½``. ``max(1, …)`` never binds on the way back: with
      ``o ≥ 1``, ``o × 365 / s ≥ 1`` when ``s ≤ 365``, and above 365 it is more than ``d − ½ ≥ ½``. At 252 a year the
      bound is one day, at 365 one day (in fact zero: both ways multiply and divide by the same 365), at 12 a year 15;
    * when ``round(x) = 0`` (the span is at most half an observation, which needs ``s ≤ 182.5``), ``max(1, …)`` counts
      one observation, and it comes back as the days of one observation, ``max(1, round(365 / s))``, never fewer than
      ``d`` (``d ≤ 365 / (2s) ≤ round(365 / s)``): the round trip lengthens a span shorter than its series can see, it
      never shortens it. Here the first bound does not hold — 1 day at 12 a year comes back as 30.

    The grid is 1..800 days; ``1e-9`` absorbs the floating rounding of ``d × s / 365``.
    """
    one_observation = max(1, round(YEAR / per_year))
    for calendar_days in CALENDAR_DAYS:
        observations = returns.calendar_days_to_observations(calendar_days, per_year)
        back = returns.observations_to_calendar_days(observations, per_year)
        if round(calendar_days * per_year / YEAR) == 0:
            assert observations == 1 and calendar_days <= back == one_observation, f"{calendar_days} days at {per_year} a year came back as {back}"
        else:
            assert abs(back - calendar_days) <= YEAR / (2 * per_year) + 0.5 + 1e-9, f"{calendar_days} days at {per_year} a year came back as {back}"


@pytest.mark.parametrize(
    ("observations", "per_year", "message"),
    [
        *[pytest.param(count, 252.0, COUNT_MESSAGE, id=f"observations-{count!r}") for count in (*INVALID_COUNTS, -400)],
        *[pytest.param(3, factor, FACTOR_MESSAGE, id=f"factor-{factor!r}") for factor in INVALID_FACTORS],
        pytest.param(0, math.nan, COUNT_MESSAGE, id="both-wrong-the-count-is-refused-first"),
    ],
)
def test_the_inverse_refuses_a_count_or_a_factor_that_describes_no_span(observations, per_year, message):
    with pytest.raises(ValueError) as refused:
        returns.observations_to_calendar_days(observations, per_year)
    assert str(refused.value) == message


@pytest.mark.parametrize(
    ("observations", "steps_per_year", "override_days", "disclosed_days"),
    [
        pytest.param(60, 252.0, 5, 4, id="five-days-are-three-steps-which-span-four-days"),
        pytest.param(60, 365.0, 5, 5, id="five-days-of-a-daily-series"),
        pytest.param(60, 252.0, None, 6, id="the-cube-root-rule-counts-steps-and-discloses-days"),
        pytest.param(60, 365.0, None, 4, id="the-cube-root-rule-of-a-daily-series"),
        pytest.param(1250, 365.0, None, 11, id="the-cube-root-of-1250-observations"),
        pytest.param(1250, 365.0, 25, 25, id="an-override-of-25-days"),
        pytest.param(756, 365.0, None, 9, id="captured-before-steps-the-default-history"),
        pytest.param(756, 365.0, 5, 5, id="captured-before-steps-a-five-day-block"),
    ],
)
def test_the_pinned_disclosures_of_the_risk_suite_read_the_same_through_the_house(observations, steps_per_year, override_days, disclosed_days):
    """The pins of ``test_risk_simulation.py``, recomputed as ``run_block_bootstrap`` computes them: the override
    converted forward, the block resolved, the block disclosed backward — through the house and through HEAD's line."""
    override = None if override_days is None else returns.calendar_days_to_observations(override_days, steps_per_year)
    block_length = resampling.resolve_block_length(observations, override)
    assert returns.observations_to_calendar_days(block_length, steps_per_year) == disclosed_days
    assert _block_length_days_today(block_length, steps_per_year) == disclosed_days


def test_a_daily_series_discloses_its_block_in_as_many_days_as_steps():
    """The identity the pins ``block_length_days == resolve_block_length(n)`` rely on, at the default frequency."""
    assert quant_models.DEFAULT_STEPS_PER_YEAR == 365.0
    for block_length in range(1, quant_models.MAX_HISTORY_OBSERVATIONS + 1):
        assert returns.observations_to_calendar_days(block_length, quant_models.DEFAULT_STEPS_PER_YEAR) == block_length


# =============================================================================
# One home: no shim, one validator, the callers on the house
# =============================================================================


def test_the_risk_module_keeps_no_copy_of_the_conversion_nor_of_the_validator():
    assert not hasattr(risk_metrics, "calendar_days_to_observations"), "risk.metrics still binds calendar_days_to_observations: a shim, or the old definition"
    assert not hasattr(risk_metrics, "_positive_annualization_factor"), "risk.metrics still binds _positive_annualization_factor"
    assert "calendar_days_to_observations" not in risk_metrics.__all__
    assert "positive_annualization_factor" not in risk_metrics.__all__
    assert risk_metrics.positive_annualization_factor is returns.positive_annualization_factor


@pytest.mark.parametrize("module", (asset_set_var_plugin, historical_var_plugin, simulation_plugin, quant_models, resampling), ids=lambda module: module.__name__.removeprefix("backend.app.services."))
def test_every_caller_converts_with_the_house(module):
    assert module.calendar_days_to_observations is returns.calendar_days_to_observations


def test_the_resampler_discloses_its_block_with_the_inverse_of_the_house():
    assert resampling.observations_to_calendar_days is returns.observations_to_calendar_days
    assert "* 365 /" not in (APP_ROOT / RESAMPLER).read_text(encoding="utf-8")


# A number 365 in code: an int or a float, never a bool, a string or a docstring that mentions it.
_YEAR_SHAPES = (
    ("max(1, round(block_length * 365 / steps_per_year))\n", [1]),
    ("x = 1\ny = days / 365.0\n", [2]),
    ("def f(days):\n    return max(1, round(days * factor / 365))\n", [2]),
)
_NOT_YEAR_SHAPES = (
    '"""holds about 252 of them a year, not 365."""\n',
    "x = '365'\n",
    "x = 366\ny = DAYS_PER_YEAR\n",
)


def _year_literals(source: str) -> list[int]:
    return sorted(node.lineno for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Constant) and type(node.value) in (int, float) and node.value == YEAR)


def test_the_year_literal_matcher_flags_a_365_in_code_and_nothing_else():
    for source, lines in _YEAR_SHAPES:
        assert _year_literals(source) == lines, source
    for source in _NOT_YEAR_SHAPES:
        assert _year_literals(source) == [], source


@pytest.mark.parametrize("module", (RESAMPLER, FORMER_HOME))
def test_no_365_is_written_again_where_the_conversions_lived(module):
    lines = _year_literals((APP_ROOT / module).read_text(encoding="utf-8"))
    assert lines == [], f"backend/app/{module} writes 365 at lines {lines}: the calendar is returns.DAYS_PER_YEAR, through the conversions of the house"


#: The definitions that have one home: the three public names in returns.py, the private validator nowhere.
_PUBLIC_NAMES = ("positive_annualization_factor", "calendar_days_to_observations", "observations_to_calendar_days")
_GONE_NAMES = ("_positive_annualization_factor",)


def _definitions(source: str, names: tuple[str, ...]) -> list[tuple[int, str]]:
    """``(line, name)`` of every ``def`` / ``async def`` of one of ``names``, at any nesting."""
    return sorted((node.lineno, node.name) for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name in names)


@functools.cache
def _app_modules() -> tuple[str, ...]:
    return tuple(sorted(path.relative_to(APP_ROOT).as_posix() for path in APP_ROOT.rglob("*.py") if "__pycache__" not in path.parts))


@functools.cache
def _backend_definitions() -> dict[str, list[tuple[str, int]]]:
    """Every definition of the moved names in ``backend/app``: ``name → [(module, line), …]``."""
    found: dict[str, list[tuple[str, int]]] = {}
    for module in _app_modules():
        for line, name in _definitions((APP_ROOT / module).read_text(encoding="utf-8"), (*_PUBLIC_NAMES, *_GONE_NAMES)):
            found.setdefault(name, []).append((module, line))
    return found


def test_the_definition_matcher_flags_every_shape_of_a_definition_and_nothing_else():
    shapes = (
        ("def _positive_annualization_factor(x):\n    return float(x)\n", [(1, "_positive_annualization_factor")]),
        ("class Metrics:\n    def calendar_days_to_observations(self, d, f):\n        return d\n", [(2, "calendar_days_to_observations")]),
        ("async def observations_to_calendar_days(o, f):\n    return o\n", [(1, "observations_to_calendar_days")]),
        ("def outer():\n    def positive_annualization_factor(x):\n        return x\n\n    return positive_annualization_factor\n", [(2, "positive_annualization_factor")]),
    )
    for source, found in shapes:
        assert _definitions(source, (*_PUBLIC_NAMES, *_GONE_NAMES)) == found, source
    for source in (
        "from backend.app.services.financial_math.returns import calendar_days_to_observations, positive_annualization_factor\n",
        "calendar_days_to_observations = returns.calendar_days_to_observations\n",
        "steps = calendar_days_to_observations(30, 252.0)\n",
        "def calendar_days_to_observations_of(series):\n    return 0\n",
    ):
        assert _definitions(source, (*_PUBLIC_NAMES, *_GONE_NAMES)) == [], source


def test_the_conversions_and_their_validator_are_defined_once_in_the_house():
    """The presence barrier first: the scan reads the house and the former home, or it would prove nothing."""
    assert {HOME, FORMER_HOME, RESAMPLER} <= set(_app_modules()), f"the scan of {APP_ROOT} missed a module it must read"
    definitions = _backend_definitions()
    problems = []
    for name in _PUBLIC_NAMES:
        places = definitions.get(name, [])
        if [module for module, _line in places] != [HOME]:
            problems.append(f"{name}: defined at {places}, expected once in backend/app/{HOME}")
    for name in _GONE_NAMES:
        problems.extend(f"{name}: defined again at backend/app/{module}:{line}" for module, line in definitions.get(name, []))
    assert not problems, "\n".join(problems)
