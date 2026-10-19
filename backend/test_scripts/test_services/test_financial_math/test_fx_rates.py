"""
J-1, item 4 (workstream MF; the developer's go of 19/10): the orientation of a stored FX rate gets one home,
``financial_math/fx_rates.py::oriented_rate``. No value changes.

``fx_rates`` keeps each pair once, its codes in alphabetical order, with the rate of the first in the second. Four sites
read such a rate from a source to a destination, and until J-1 each wrote the rule again (HEAD ``8eb783b0b``):

* ``fx/conversion.py::compute_chain_rate``, the step of a route: ``composite *= rate`` when ``fc < tc``, else
  ``composite *= Decimal("1") / rate``;
* ``fx/storage.py::normalize_rate_for_storage``: ``(base, quote, rate)`` when ``base < quote``, else
  ``(quote, base, Decimal("1") / rate)`` — so equal codes took the second branch, ``(b, b, 1 / rate)``. Now
  ``(min, max, oriented_rate(rate, base, quote))``: the same, equal codes included;
* ``pac_allocator/evaluation/scenario.py::fx_rate``, on the PAC's exact ``ExactRatio``:
  ``rate if source_currency < destination_currency else _EXACT_ONE / rate`` (equal codes answer ``_EXACT_ONE`` first);
* ``pac_allocator/source/wac.py::build_planner_wac_contexts``, the saved rate as evidence of a WAC conversion:
  ``Decimal("1") / saved_row.rate if inverted else saved_row.rate``, ``inverted`` from
  ``normalized_fx_pair(source_currency, target_currency)``, which is ``not source < target`` (equal codes never get
  there: the loop skips them).

Now each calls ``oriented_rate(rate, source, destination)``: ``rate`` when ``source < destination``, else
``type(rate)(1) / rate``, in the rate's own number type and without importing the PAC.

What is tested:

* parity with each HEAD expression, verbatim copies as oracles (``*_today``): currency pairs in both orders and equal
  codes where the site lets them through, ``Decimal`` rates with long digits (``str`` compared: digits and exponent),
  ``ExactRatio`` rates for the PAC (``==`` and type) — once on ``oriented_rate`` itself, once on the sites' functions;
* the involution: exact on ``ExactRatio``; on ``Decimal``, ``1 / (1 / r)`` rounds twice to the context's 28
  significant digits, so it is ``r`` within two roundings and not always ``r`` (``7`` comes back as
  ``6.999999999999999999999999998``) — asserted as such;
* a zero rate: the same exception class as HEAD's expression (``decimal.DivisionByZero``, ``ExactDivisionByZeroError``),
  and a zero read in its stored direction comes back as it is, as before;
* the call sites: ``oriented_rate`` replaced in each site's module by a recorder that delegates, then
  ``compute_chain_rate``, ``normalize_rate_for_storage``, ``scenario.fx_rate`` and ``build_planner_wac_contexts`` driven
  directly — each must call it with ``(rate, source, destination)`` and answer with what it returns. The WAC builder has
  no pure helper for the orientation; it is driven as ``test_portfolio_allocation_source.py`` drives it, with the WAC
  runtime and the saved-row reader replaced (``session`` is never touched);
* structure: the four modules hold the house's function, none of the four functions divides a one by a rate any more,
  ``oriented_rate`` is defined once in ``backend/app``, and ``financial_math/fx_rates.py`` imports nothing from the
  services — neither ``fx`` nor ``pac_allocator`` (the layer under them).

Red before J-1, each test on its own: the house's module is imported when a test runs (``ModuleNotFoundError``), and a
recorder cannot replace a name the site's module does not have (``AttributeError``); the structural guards find HEAD's
divisions. Green on both sides by design, parity guards of the sites' own functions: ``test_a_route_composes_as_today``,
``test_storage_normalizes_as_today``, ``test_storage_inverts_equal_codes_as_today``,
``test_the_pac_scenario_reads_a_pair_as_today``, ``test_a_zero_rate_fails_at_the_sites_as_today``, and the detector
self-checks.

Pure: no database, no server, no network. The structural guards parse source files with ``ast`` and never import them.
"""

from __future__ import annotations

import ast
import functools
import importlib
from datetime import date
from decimal import Decimal, DefaultContext, localcontext
from importlib.util import resolve_name
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.app.schemas.common import Currency, FxBackwardFillInfo
from backend.app.schemas.wac import WACPreviewResultItem, WACQualifyingTX
from backend.app.services import portfolio_service
from backend.app.services.fx import conversion as fx_conversion
from backend.app.services.fx import storage as fx_storage
from backend.app.services.pac_allocator.evaluation import scenario
from backend.app.services.pac_allocator.evaluation.errors import ExactScenarioContractError
from backend.app.services.pac_allocator.evaluation.keys import fx_pair_key
from backend.app.services.pac_allocator.numeric import ExactRatio
from backend.app.services.pac_allocator.source import wac as source_wac
from backend.app.services.pac_allocator.source.keys import normalized_fx_pair

REPO_ROOT = Path(__file__).resolve().parents[4]
APP_ROOT = REPO_ROOT / "backend" / "app"
HOME = "services/financial_math/fx_rates.py"
HOME_MODULE = "backend.app.services.financial_math.fx_rates"

CODES = ("BTC", "CHF", "EUR", "GBP", "JPY", "USD")
#: Every pair in both orders.
DISTINCT_PAIRS = tuple((source, destination) for source in CODES for destination in CODES if source != destination)
EQUAL_PAIRS = tuple((code, code) for code in CODES)
DECIMAL_RATES = tuple(
    Decimal(text)
    for text in (
        "1.0823456789",
        "0.000012345",
        "123456.789",
        "0.90",
        "1.00",
        "1",
        "3",
        "7",
        "0.8",
        "60000.50",
        "0.0067",
        "2.5E-7",
        "1E+5",
        "0.3333333333333333333333333333",
        "1.08234567891234567890123456789",
    )
)
EXACT_RATES = (
    ExactRatio.from_decimal(Decimal("1.0823456789")),
    ExactRatio.from_decimal(Decimal("0.000012345")),
    ExactRatio.from_decimal(Decimal("123456.789")),
    ExactRatio(1, 3),
    ExactRatio(22, 7),
    ExactRatio(1),
    ExactRatio(7),
)
DECIMAL_ZEROS = (Decimal("0"), Decimal("0.00"), Decimal("-0"), Decimal("0E-10"))
ON = date(2026, 1, 1)


def _oriented_rate():
    """The house's function, read when a test runs: before J-1 the module does not exist, and only the tests that need it
    fail (``ModuleNotFoundError``), while the parity guards of the four sites still run."""
    return importlib.import_module(HOME_MODULE).oriented_rate


def _shown(value):
    """A value as compared here: a Decimal by its digits and exponent (``str``: ``1.00`` and ``1`` differ), inside a
    tuple too; anything else as it is."""
    if isinstance(value, tuple):
        return tuple(_shown(item) for item in value)
    return str(value) if isinstance(value, Decimal) else value


def _outcome(function, *args):
    """What a call gives: its value as ``_shown`` and its type, or the class and message of what it raises."""
    try:
        value = function(*args)
    except Exception as error:
        return "raises", type(error), str(error)
    return "returns", type(value), _shown(value)


# =============================================================================
# HEAD 8eb783b0b, verbatim (docstrings aside)
# =============================================================================


def _compute_chain_rate_today(steps, leg_rates, target_date):
    """``fx/conversion.py::compute_chain_rate`` at HEAD (its gate ``_usable_rate`` is unchanged by J-1)."""
    composite = Decimal("1")
    for step in steps:
        fc = step["from"]
        tc = step["to"]
        # Normalize alphabetically for lookup
        norm_base = min(fc, tc)
        norm_quote = max(fc, tc)
        key = (norm_base, norm_quote, target_date)
        rate = leg_rates.get(key)
        if not fx_conversion._usable_rate(rate):
            return None
        if fc < tc:
            # Direct order: multiply by rate
            composite *= rate
        else:
            # Inverse order: multiply by 1/rate
            composite *= Decimal("1") / rate
    return composite


def _route_factor_today(rate, fc, tc):
    """What one step of HEAD's ``compute_chain_rate`` multiplies the composite by (``fx/conversion.py:73-78``)."""
    if fc < tc:
        # Direct order: multiply by rate
        return rate
    # Inverse order: multiply by 1/rate
    return Decimal("1") / rate


def _normalize_rate_for_storage_today(base, quote, rate):
    """``fx/storage.py::normalize_rate_for_storage`` at HEAD."""
    if base < quote:
        # Already in correct order
        return base, quote, rate
    else:
        # Invert: swap currencies and invert rate
        return quote, base, Decimal("1") / rate


_EXACT_ONE = ExactRatio(1)


def _scenario_fx_rate_today(fx_rate_by_pair, source_currency, destination_currency):
    """``pac_allocator/evaluation/scenario.py::fx_rate`` at HEAD."""
    if source_currency == destination_currency:
        return _EXACT_ONE
    rate = fx_rate_by_pair.get(fx_pair_key(source_currency, destination_currency))
    if rate is None:
        raise ExactScenarioContractError(f"missing direct FX rate for {source_currency}/{destination_currency}")
    return rate if source_currency < destination_currency else _EXACT_ONE / rate


def _scenario_expression_today(rate, source_currency, destination_currency):
    """The last line of HEAD's ``scenario.fx_rate``, on its own (equal codes included, which the function answers first)."""
    return rate if source_currency < destination_currency else _EXACT_ONE / rate


def _wac_saved_directed_rate_today(saved_rate, source_currency, target_currency):
    """``pac_allocator/source/wac.py:153-157`` at HEAD: the saved row's rate read from source to target."""
    base, quote, inverted = normalized_fx_pair(source_currency, target_currency)
    return Decimal("1") / saved_rate if inverted else saved_rate


# =============================================================================
# oriented_rate against each HEAD expression
# =============================================================================

_DECIMAL_SITES = (
    pytest.param(_route_factor_today, DISTINCT_PAIRS + EQUAL_PAIRS, id="fx-route-step"),
    pytest.param(lambda rate, base, quote: _normalize_rate_for_storage_today(base, quote, rate)[2], DISTINCT_PAIRS + EQUAL_PAIRS, id="fx-storage"),
    pytest.param(_wac_saved_directed_rate_today, DISTINCT_PAIRS, id="pac-wac-evidence"),
)


@pytest.mark.parametrize(("expression_today", "pairs"), _DECIMAL_SITES)
def test_oriented_rate_reads_a_decimal_rate_as_each_fx_site_did(expression_today, pairs):
    oriented_rate = _oriented_rate()
    for source, destination in pairs:
        for rate in DECIMAL_RATES:
            oriented = oriented_rate(rate, source, destination)
            assert type(oriented) is Decimal
            assert str(oriented) == str(expression_today(rate, source, destination)), f"{rate} from {source} to {destination}"


def test_oriented_rate_reads_an_exact_ratio_as_the_pac_scenario_did():
    oriented_rate = _oriented_rate()
    for source, destination in DISTINCT_PAIRS + EQUAL_PAIRS:
        for rate in EXACT_RATES:
            oriented = oriented_rate(rate, source, destination)
            assert type(oriented) is ExactRatio
            assert oriented == _scenario_expression_today(rate, source, destination), f"{rate} from {source} to {destination}"


def test_oriented_rate_returns_the_stored_rate_itself_in_its_stored_direction():
    """No copy, no ``1 × rate`` that would round a rate of more than 28 digits: the object as it was."""
    oriented_rate = _oriented_rate()
    for rate in (*DECIMAL_RATES, *EXACT_RATES):
        assert oriented_rate(rate, "EUR", "USD") is rate


# =============================================================================
# The four sites against HEAD (parity guards, green before and after J-1)
# =============================================================================

_ROUTES = (
    ("USD", "EUR", "JPY"),
    ("JPY", "USD", "EUR"),
    ("CHF", "EUR", "GBP", "USD"),
    ("BTC", "USD", "CHF"),
)


def _legs(route: tuple[str, ...]) -> list[dict]:
    return [{"from": route[index], "to": route[index + 1]} for index in range(len(route) - 1)]


def test_a_route_composes_as_today():
    """Every single step (pairs both ways and equal codes, which nothing refuses there) and longer routes, with each
    long-digit rate on every leg: the same composite, digit for digit. None never stands for a value: every rate of the
    grid is usable."""
    routes = [[{"from": source, "to": destination}] for source, destination in DISTINCT_PAIRS + EQUAL_PAIRS] + [_legs(route) for route in _ROUTES]
    for rate in DECIMAL_RATES:
        assert fx_conversion._usable_rate(rate), f"{rate} is not a usable leg: the parity below would compare None with None"
        for legs in routes:
            leg_rates = {(min(leg["from"], leg["to"]), max(leg["from"], leg["to"]), ON): rate for leg in legs}
            composed = fx_conversion.compute_chain_rate(legs, leg_rates, ON)
            assert composed is not None
            assert str(composed) == str(_compute_chain_rate_today(legs, leg_rates, ON)), f"{rate} along {legs}"


def test_a_route_of_mixed_rates_composes_as_today():
    for route in _ROUTES:
        legs = _legs(route)
        leg_rates = {(min(leg["from"], leg["to"]), max(leg["from"], leg["to"]), ON): DECIMAL_RATES[index] for index, leg in enumerate(legs)}
        assert str(fx_conversion.compute_chain_rate(legs, leg_rates, ON)) == str(_compute_chain_rate_today(legs, leg_rates, ON)), route


def test_storage_normalizes_as_today():
    for base, quote in DISTINCT_PAIRS + EQUAL_PAIRS:
        for rate in DECIMAL_RATES:
            assert _outcome(fx_storage.normalize_rate_for_storage, base, quote, rate) == _outcome(_normalize_rate_for_storage_today, base, quote, rate), f"{base}/{quote} at {rate}"


def test_storage_inverts_equal_codes_as_today():
    """``base == quote`` took HEAD's second branch, ``(b, b, 1 / rate)``; ``min``, ``max`` and ``oriented_rate`` (not
    ``b < b``) give the same."""
    assert _outcome(fx_storage.normalize_rate_for_storage, "EUR", "EUR", Decimal("1.25")) == ("returns", tuple, ("EUR", "EUR", "0.8"))
    assert _outcome(_normalize_rate_for_storage_today, "EUR", "EUR", Decimal("1.25")) == ("returns", tuple, ("EUR", "EUR", "0.8"))


def test_the_pac_scenario_reads_a_pair_as_today():
    for rate in EXACT_RATES:
        fx_rate_by_pair = {fx_pair_key(source, destination): rate for source, destination in DISTINCT_PAIRS}
        for source, destination in DISTINCT_PAIRS + EQUAL_PAIRS:
            read = scenario.fx_rate(fx_rate_by_pair, source, destination)
            assert type(read) is ExactRatio
            assert read == _scenario_fx_rate_today(fx_rate_by_pair, source, destination), f"{rate} from {source} to {destination}"
    assert _outcome(scenario.fx_rate, {}, "USD", "EUR") == _outcome(_scenario_fx_rate_today, {}, "USD", "EUR")


# =============================================================================
# The involution
# =============================================================================


def test_an_exact_ratio_read_twice_against_its_order_is_itself():
    oriented_rate = _oriented_rate()
    for rate in EXACT_RATES:
        for source, destination in DISTINCT_PAIRS + EQUAL_PAIRS:
            assert oriented_rate(oriented_rate(rate, source, destination), source, destination) == rate
        for source, destination in DISTINCT_PAIRS:
            assert oriented_rate(rate, source, destination) * oriented_rate(rate, destination, source) == _EXACT_ONE


#: Half a unit in the 28th significant digit, relative: the most one rounding of the default context moves a value.
_HALF_UNIT = Decimal("5E-28")


def test_a_decimal_read_twice_against_its_order_is_itself_within_two_roundings():
    """``1 / (1 / r)`` rounds twice to 28 significant digits: ``y = (1 / r)(1 + δ₁)``, ``back = (1 / y)(1 + δ₂)``,
    ``|δ| ≤ u = ½ × 10⁻²⁷``, so ``|back − r| ≤ |r| × 2u / (1 − u)``. Not ``r`` itself: ``7`` comes back as
    ``6.999999999999999999999999998``, and ``3`` as ``3.000000000000000000000000000`` (equal, other digits). A rate
    whose inverse terminates within 28 digits comes back exactly: ``0.8`` → ``1.25`` → ``0.8``. HEAD's expressions do
    the same, by parity above; this pins what is true of both."""
    oriented_rate = _oriented_rate()
    with localcontext(DefaultContext):
        backs = {str(rate): oriented_rate(oriented_rate(rate, "USD", "EUR"), "USD", "EUR") for rate in DECIMAL_RATES}
    with localcontext() as exact:
        exact.prec = 200
        for rate in DECIMAL_RATES:
            back = backs[str(rate)]
            assert abs(back - rate) * (1 - _HALF_UNIT) <= abs(rate) * 2 * _HALF_UNIT, f"{rate} came back as {back}"
    assert str(backs["7"]) == "6.999999999999999999999999998"
    assert str(backs["3"]) == "3.000000000000000000000000000"
    assert str(backs["0.8"]) == "0.8"
    assert all(oriented_rate(rate, "EUR", "USD") is rate for rate in DECIMAL_RATES)


# =============================================================================
# A zero rate
# =============================================================================


def test_a_zero_rate_has_no_inverse_as_today():
    """Against its stored order, ``type(rate)(1) / 0`` raises what ``Decimal("1") / 0`` and ``_EXACT_ONE / 0`` raised
    (class and message; the default context traps a division by zero); in its stored order it comes back as it is."""
    oriented_rate = _oriented_rate()
    with localcontext(DefaultContext):
        for zero in DECIMAL_ZEROS:
            for today in (_route_factor_today, lambda rate, base, quote: _normalize_rate_for_storage_today(base, quote, rate)[2], _wac_saved_directed_rate_today):
                inverted = _outcome(oriented_rate, zero, "USD", "EUR")
                assert inverted[0] == "raises" and inverted == _outcome(today, zero, "USD", "EUR")
                assert _outcome(oriented_rate, zero, "EUR", "USD") == _outcome(today, zero, "EUR", "USD") == ("returns", Decimal, str(zero))
    exact_zero = ExactRatio(0)
    inverted = _outcome(oriented_rate, exact_zero, "USD", "EUR")
    assert inverted[0] == "raises" and inverted == _outcome(_scenario_expression_today, exact_zero, "USD", "EUR")
    assert oriented_rate(exact_zero, "EUR", "USD") is exact_zero


def test_a_zero_rate_fails_at_the_sites_as_today():
    """A parity guard, green before and after J-1. The route and the WAC evidence never hand a zero over (the leg gate,
    ``saved_row.rate > 0``); storage and the scenario have no gate of their own."""
    with localcontext(DefaultContext):
        for zero in DECIMAL_ZEROS:
            assert fx_conversion.compute_chain_rate([{"from": "USD", "to": "EUR"}], {("EUR", "USD", ON): zero}, ON) is None
            refused = _outcome(fx_storage.normalize_rate_for_storage, "USD", "EUR", zero)
            assert refused[0] == "raises" and refused == _outcome(_normalize_rate_for_storage_today, "USD", "EUR", zero)
    refused = _outcome(scenario.fx_rate, {"EUR/USD": ExactRatio(0)}, "USD", "EUR")
    assert refused[0] == "raises" and refused == _outcome(_scenario_fx_rate_today, {"EUR/USD": ExactRatio(0)}, "USD", "EUR")


# =============================================================================
# The call sites
# =============================================================================


def _record_oriented_rate(monkeypatch, module, answer=None):
    """Replace ``oriented_rate`` in ``module``'s namespace with a recorder; it delegates to the house, or answers
    ``answer`` when given. ``monkeypatch.setattr`` refuses a name the module does not have: before J-1, that is the red."""
    real = _oriented_rate()
    calls: list[tuple] = []

    def recorder(rate, source, destination):
        calls.append((rate, source, destination))
        return real(rate, source, destination) if answer is None else answer

    monkeypatch.setattr(module, "oriented_rate", recorder)
    return calls


def test_the_route_step_orients_each_leg_with_the_house(monkeypatch):
    calls = _record_oriented_rate(monkeypatch, fx_conversion)
    legs = _legs(("USD", "EUR", "JPY", "GBP"))
    rates = {("EUR", "USD", ON): Decimal("1.0823456789"), ("EUR", "JPY", ON): Decimal("123456.789"), ("GBP", "JPY", ON): Decimal("0.000012345")}

    composed = fx_conversion.compute_chain_rate(legs, rates, ON)

    assert calls == [(Decimal("1.0823456789"), "USD", "EUR"), (Decimal("123456.789"), "EUR", "JPY"), (Decimal("0.000012345"), "JPY", "GBP")]
    assert str(composed) == str(_compute_chain_rate_today(legs, rates, ON))
    calls.clear()
    # A leg the gate refuses never reaches the orientation: the route stops there.
    assert fx_conversion.compute_chain_rate(legs, {**rates, ("EUR", "JPY", ON): Decimal("0")}, ON) is None
    assert calls == [(Decimal("1.0823456789"), "USD", "EUR")]


@pytest.mark.parametrize(("base", "quote"), [("USD", "EUR"), ("EUR", "USD"), ("EUR", "EUR")])
def test_storage_orients_its_rate_with_the_house(monkeypatch, base, quote):
    calls = _record_oriented_rate(monkeypatch, fx_storage)
    rate = Decimal("1.0823456789")

    normalized = fx_storage.normalize_rate_for_storage(base, quote, rate)

    assert calls == [(rate, base, quote)]
    assert _shown(normalized) == _shown(_normalize_rate_for_storage_today(base, quote, rate))


@pytest.mark.parametrize(("source", "destination", "expected_calls"), [("USD", "EUR", 1), ("EUR", "USD", 1), ("EUR", "EUR", 0)])
def test_the_pac_scenario_orients_its_pair_with_the_house(monkeypatch, source, destination, expected_calls):
    """Equal codes answer one before any lookup: no call, as HEAD never reached its expression for them."""
    calls = _record_oriented_rate(monkeypatch, scenario)
    rate = ExactRatio(10823456789, 10**10)
    fx_rate_by_pair = {"EUR/USD": rate}

    read = scenario.fx_rate(fx_rate_by_pair, source, destination)

    assert calls == [(rate, source, destination)] * expected_calls
    assert read == _scenario_fx_rate_today(fx_rate_by_pair, source, destination)


def test_every_site_answers_with_the_rate_the_house_returns(monkeypatch):
    """A site that called the house and then computed the rate itself would pass the recorder; not this."""
    marker = Decimal("0.123456789")
    exact_marker = ExactRatio(123456789, 10**9)
    _record_oriented_rate(monkeypatch, fx_conversion, answer=marker)
    _record_oriented_rate(monkeypatch, fx_storage, answer=marker)
    _record_oriented_rate(monkeypatch, scenario, answer=exact_marker)

    assert str(fx_conversion.compute_chain_rate([{"from": "USD", "to": "EUR"}], {("EUR", "USD", ON): Decimal("1.08")}, ON)) == str(Decimal("1") * marker)
    assert fx_storage.normalize_rate_for_storage("USD", "EUR", Decimal("1.08"))[2] is marker
    assert scenario.fx_rate({"EUR/USD": ExactRatio(108, 100)}, "USD", "EUR") is exact_marker


def _wac_result(*, source_currency: str, rate_used: Decimal) -> WACPreviewResultItem:
    """One BUY in ``source_currency`` converted to EUR at ``rate_used``, on the rate of 2026-01-01."""
    return WACPreviewResultItem(
        wac=Currency(code="EUR", amount=Decimal("80.0000")),
        wac_qualifying_txs=[
            WACQualifyingTX(
                tx_id=1,
                date=date(2026, 1, 3),
                type="BUY",
                quantity=Decimal("2"),
                unit_cost=Decimal("80"),
                currency="EUR",
                effect="add",
                running_wac=Decimal("80.0000"),
                original_unit_cost=Decimal("100"),
                original_currency=source_currency,
                fx_rate_used=rate_used,
                fx_info=FxBackwardFillInfo(fx_rate_date=ON, fx_days_back=2),
            )
        ],
        wac_missing_pairs=[],
    )


async def _wac_evidence(monkeypatch, *, source_currency: str, stored_rate: Decimal, rate_used: Decimal):
    """Drive ``build_planner_wac_contexts`` on one holding: the WAC runtime and the saved-row reader replaced, the session
    a bare object that nothing reads. Returns the one evidence line."""
    base, quote, _inverted = normalized_fx_pair(source_currency, "EUR")
    monkeypatch.setattr(portfolio_service, "compute_wac_iterative", AsyncMock(return_value=_wac_result(source_currency=source_currency, rate_used=rate_used)))
    monkeypatch.setattr(source_wac, "_load_wac_fx_rows", AsyncMock(return_value={(base, quote, ON): SimpleNamespace(rate=stored_rate, source="MANUAL_WAC_FX")}))
    rows = await source_wac.build_planner_wac_contexts(
        object(),
        holding_rows=[(7, 11, Decimal("2"))],
        selected_asset_ids={11},
        assets_by_id={11: SimpleNamespace(currency=source_currency)},
        as_of=date(2026, 9, 15),
        target_currency="EUR",
        issues=[],
    )
    (row,) = rows
    (evidence,) = row.fx_evidence
    return evidence


@pytest.mark.asyncio
@pytest.mark.parametrize(("source_currency", "inverted"), [("USD", True), ("CHF", False)])
async def test_the_wac_evidence_orients_the_saved_rate_with_the_house(monkeypatch, source_currency, inverted):
    """USD → EUR reads the stored EUR/USD row inverted, CHF → EUR the stored CHF/EUR row as it is."""
    calls = _record_oriented_rate(monkeypatch, source_wac)
    stored = Decimal("1.0823456789")
    directed_today = _wac_saved_directed_rate_today(stored, source_currency, "EUR")

    evidence = await _wac_evidence(monkeypatch, source_currency=source_currency, stored_rate=stored, rate_used=directed_today)

    assert calls == [(stored, source_currency, "EUR")]
    assert (evidence.status, evidence.inverted, str(evidence.rate)) == ("available", inverted, str(directed_today))


@pytest.mark.asyncio
async def test_the_wac_evidence_answers_with_the_rate_the_house_returns(monkeypatch):
    """The house answers a marker; the cost used that marker, the saved row says otherwise: only a site that takes the
    house's answer finds them matching."""
    marker = Decimal("0.123456789")
    _record_oriented_rate(monkeypatch, source_wac, answer=marker)

    evidence = await _wac_evidence(monkeypatch, source_currency="USD", stored_rate=Decimal("1.0823456789"), rate_used=marker)

    assert (evidence.status, evidence.rate) == ("available", marker)


# =============================================================================
# Structure
# =============================================================================

_SITES = (
    pytest.param(fx_conversion, "services/fx/conversion.py", "compute_chain_rate", id="fx-conversion"),
    pytest.param(fx_storage, "services/fx/storage.py", "normalize_rate_for_storage", id="fx-storage"),
    pytest.param(scenario, "services/pac_allocator/evaluation/scenario.py", "fx_rate", id="pac-scenario"),
    pytest.param(source_wac, "services/pac_allocator/source/wac.py", "build_planner_wac_contexts", id="pac-wac"),
)


@pytest.mark.parametrize(("module", "path", "function"), _SITES)
def test_the_four_sites_hold_the_house_function(module, path, function):
    assert module.oriented_rate is _oriented_rate()


#: The names a one is written with at the four sites.
_ONES = {"_EXACT_ONE", "ONE"}


def _is_one(node: ast.expr) -> bool:
    """``1``, ``Decimal("1")``, ``Decimal(1)``, ``ExactRatio(1)``, ``type(rate)(1)`` and the named ones."""
    if isinstance(node, ast.Constant):
        return type(node.value) is int and node.value == 1
    if isinstance(node, ast.Name):
        return node.id in _ONES
    if isinstance(node, ast.Call) and len(node.args) == 1 and not node.keywords:
        argument = node.args[0]
        return isinstance(argument, ast.Constant) and argument.value in (1, "1") and type(argument.value) is not bool
    return False


def _inversions(source: str, function: str) -> list[int]:
    """Lines where ``function`` (any definition of that name in ``source``) divides a one by something."""
    lines = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == function:
            lines.extend(inner.lineno for inner in ast.walk(node) if isinstance(inner, ast.BinOp) and isinstance(inner.op, ast.Div) and _is_one(inner.left))
    return sorted(lines)


def test_the_inversion_matcher_flags_every_shape_of_heads_expressions_and_nothing_else():
    flagged = (
        "def f(rate):\n    composite = 1\n    composite *= Decimal('1') / rate\n",
        'def f(base, quote, rate):\n    return quote, base, Decimal("1") / rate\n',
        "def f(rate, s, d):\n    return rate if s < d else _EXACT_ONE / rate\n",
        "async def f(saved_row, inverted):\n    return Decimal('1') / saved_row.rate if inverted else saved_row.rate\n",
        "def f(rate):\n    return type(rate)(1) / rate\n",
        "def f(rate):\n    return 1 / rate\n",
        "def f(rate):\n    return ExactRatio(1) / rate\n",
    )
    for source in flagged:
        assert _inversions(source, "f") != [], source
    for source in ("def f(rate):\n    return rate / 2\n", "def f(a, b):\n    return a / b\n", "def f(rate):\n    return Decimal('10') / rate\n", "def g(rate):\n    return 1 / rate\n"):
        assert _inversions(source, "f") == [], source


@pytest.mark.parametrize(("module", "path", "function"), _SITES)
def test_no_site_inverts_a_rate_by_itself(module, path, function):
    source = (APP_ROOT / path).read_text(encoding="utf-8")
    assert f"def {function}(" in source, f"{function} is no longer in backend/app/{path}: point the guard at its new home"
    lines = _inversions(source, function)
    assert lines == [], f"{function} (backend/app/{path}) divides a one by a rate at lines {lines}: the orientation of a stored rate is financial_math.fx_rates.oriented_rate"


@functools.cache
def _oriented_rate_definitions() -> tuple[tuple[str, int], ...]:
    found = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found.extend((path.relative_to(APP_ROOT).as_posix(), node.lineno) for node in ast.walk(tree) if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == "oriented_rate")
    return tuple(found)


def test_oriented_rate_is_defined_once_in_the_house():
    definitions = _oriented_rate_definitions()
    assert [module for module, _line in definitions] == [HOME], f"oriented_rate is defined at {definitions}: once, in backend/app/{HOME}, and imported from there"


def _service_imports(source: str, package: str) -> list[tuple[int, str]]:
    """``(line, module)`` of every import that binds a module of ``backend.app.services`` (``fx``, ``pac_allocator`` and
    every other), at any depth: inside a function, under ``if TYPE_CHECKING:``, relative forms resolved against
    ``package`` as the interpreter does."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            targets = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = resolve_name("." * node.level + (node.module or ""), package)
            targets = [base, *(f"{base}.{alias.name}" for alias in node.names)]
        else:
            continue
        found.extend((node.lineno, target) for target in targets if target == "backend.app.services" or target.startswith("backend.app.services."))
    return sorted(set(found))


def test_the_import_matcher_flags_every_way_into_the_services():
    package = "backend.app.services.financial_math"
    shapes = (
        "from backend.app.services.pac_allocator.numeric import ExactRatio\n",
        "import backend.app.services.fx.storage\n",
        "from ..fx.base import RateNotFoundError\n",
        "from ..pac_allocator import numeric\n",
        "from backend.app import services\n",
        "from .returns import DAYS_PER_YEAR\n",
        "def f():\n    from backend.app.services.fx import conversion\n",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from backend.app.services.pac_allocator.numeric import ExactRatio\n",
    )
    for source in shapes:
        assert _service_imports(source, package) != [], source
    for source in ("from __future__ import annotations\n", "from decimal import Decimal\n", "import math\n", "from backend.app.utils import sql_chunks\n"):
        assert _service_imports(source, package) == [], source


def test_the_house_of_the_orientation_imports_nothing_from_the_services():
    """The house serves ``fx`` and the PAC; it reads neither: ``ExactRatio`` is reached through ``type(rate)``."""
    imports = _service_imports((APP_ROOT / HOME).read_text(encoding="utf-8"), "backend.app.services.financial_math")
    assert imports == [], f"backend/app/{HOME} imports {imports}"
