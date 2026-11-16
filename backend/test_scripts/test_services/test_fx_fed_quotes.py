"""FED FX provider: which FRED series each currency reads, and in which direction (no network, no DB, no server).

Lane 75, wave 0 (research ``ricerca-FX-banche-centrali.md`` §2, run on the real plugin on 16/11/2026). Measured before
the cure:

- FED read every FRED series as «USD per 1 foreign unit» and returned ``(day, CUR, 'USD', value)``. Only the four
  ``DEXUS..`` series are quoted that way (EUR, GBP, AUD, NZD). The sixteen ``DEX..US`` series are «foreign units per
  1 USD» (FRED's own titles: «Japanese Yen to One U.S. Dollar»): ``DEXJPUS`` 158.23 became «1 JPY = 158.23 USD», and
  the service stored it as JPY/USD = 158.23 instead of 1/158.23.
- FED had no series for MYR, LKR and VES, which H.10 publishes (``DEXMAUS``, ``DEXSLUS``, ``DEXVZUS``). ``DEXVZUS``
  joins three units in one column: VEF until 17/08/2018, the 2018 bolívar until 01/10/2021, the 2021 bolívar since
  04/10/2021 (factors of 10^5 and 10^6 at the breaks). Only the last one is today's VES: the provider serves VES from
  04/10/2021 on.
- FED had no warning: H.10 is released once a week, so its newest rate is 3 to about 10 days old.

The expected table is written out by hand, never read from the plugin: a test that derives what it expects from the
code under test agrees with any bug. A guard checks the plugin's table holds exactly these currencies. Every answer is
synthetic (round numbers of the test's own), never data downloaded from FRED.

Isolation: PURE. ``fetch_rates`` runs whole, its module's ``httpx`` replaced for the test by the real module whose
``AsyncClient`` answers through an ``httpx.MockTransport`` (``_route``, from ``test_rate_limit_http_providers.py``):
the plugin's requests, parameters and ``raise_for_status()`` run unchanged and never leave the process.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import httpx
import pytest

from backend.app.services.fx.storage import normalize_storable_rate
from backend.app.services.fx_providers.fed import plugin as fed_mod
from backend.app.services.fx_providers.fed.plugin import FEDProvider
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

#: «1 CUR = value USD»: FRED titles them «U.S. Dollars to One <currency>».
USD_PER_UNIT = "usd_per_unit"
#: «1 USD = value CUR»: FRED titles them «<currency> to One U.S. Dollar».
UNITS_PER_USD = "units_per_usd"

#: Every FED currency: its FRED series and how FRED quotes it. Written by hand from FRED's series titles.
FED_EXPECTED: dict[str, tuple[str, str]] = {
    "EUR": ("DEXUSEU", USD_PER_UNIT),
    "GBP": ("DEXUSUK", USD_PER_UNIT),
    "AUD": ("DEXUSAL", USD_PER_UNIT),
    "NZD": ("DEXUSNZ", USD_PER_UNIT),
    "JPY": ("DEXJPUS", UNITS_PER_USD),
    "CAD": ("DEXCAUS", UNITS_PER_USD),
    "CHF": ("DEXSZUS", UNITS_PER_USD),
    "SEK": ("DEXSDUS", UNITS_PER_USD),
    "DKK": ("DEXDNUS", UNITS_PER_USD),
    "NOK": ("DEXNOUS", UNITS_PER_USD),
    "CNY": ("DEXCHUS", UNITS_PER_USD),
    "INR": ("DEXINUS", UNITS_PER_USD),
    "BRL": ("DEXBZUS", UNITS_PER_USD),
    "MXN": ("DEXMXUS", UNITS_PER_USD),
    "ZAR": ("DEXSFUS", UNITS_PER_USD),
    "SGD": ("DEXSIUS", UNITS_PER_USD),
    "HKD": ("DEXHKUS", UNITS_PER_USD),
    "KRW": ("DEXKOUS", UNITS_PER_USD),
    "TWD": ("DEXTAUS", UNITS_PER_USD),
    "THB": ("DEXTHUS", UNITS_PER_USD),
    "MYR": ("DEXMAUS", UNITS_PER_USD),
    "LKR": ("DEXSLUS", UNITS_PER_USD),
    "VES": ("DEXVZUS", UNITS_PER_USD),
}

#: The first day of today's VES in ``DEXVZUS`` (the 2021 redenomination, 10^6 old bolívares = 1 new).
VES_FIRST_DAY = date(2021, 10, 4)

DAY = date(2026, 1, 5)
RANGE = (date(2026, 1, 2), date(2026, 1, 9))
#: A synthetic value, the same for every series: what it means is the direction under test.
VALUE = Decimal("2.5000")


def _fred_answer(series: str, lines: list[str]) -> httpx.Response:
    return httpx.Response(200, text="\n".join([f"observation_date,{series}", *lines]) + "\n")


def test_guard_fed_serves_exactly_the_currencies_of_the_expected_table():
    """GUARD — the plugin's table and this test's hold the same currencies, each on the same FRED series."""
    served = {currency: FEDProvider.CURRENCY_SERIES[currency].series_id for currency in FEDProvider.CURRENCY_SERIES}
    expected = {currency: series for currency, (series, _direction) in FED_EXPECTED.items()}
    assert served == expected, f"FED's series table differs from H.10's as written in this test: missing {sorted(expected.keys() - served.keys())}, extra {sorted(served.keys() - expected.keys())}, other series {sorted(c for c in served.keys() & expected.keys() if served[c] != expected[c])}"


@pytest.mark.parametrize("currency", sorted(FED_EXPECTED))
@pytest.mark.asyncio
async def test_fed_returns_each_series_in_the_direction_fred_quotes_it(monkeypatch: pytest.MonkeyPatch, currency: str):
    """Each FRED series comes back in the direction FRED publishes it: «1 CUR = v USD» or «1 USD = v CUR».

    Before the cure, the sixteen «CUR per 1 USD» series came back as «1 CUR = v USD»: 1 JPY = 158 USD."""
    series, direction = FED_EXPECTED[currency]
    asked = _route(monkeypatch, fed_mod, lambda request: _fred_answer(request.url.params["id"], [f"{DAY.isoformat()},{VALUE}"]))

    rates = await FEDProvider().fetch_rates(RANGE, [currency])

    assert [request.url.params["id"] for request in asked] == [series], f"FED asked {[r.url.params.get('id') for r in asked]} for {currency}: expected {series}"
    expected = (DAY, currency, "USD", VALUE) if direction == USD_PER_UNIT else (DAY, "USD", currency, VALUE)
    assert rates[currency] == [expected], f"FRED {series} = {VALUE} on {DAY} ({'USD per 1 ' + currency if direction == USD_PER_UNIT else currency + ' per 1 USD'}): FED returned {rates[currency]}, expected [{expected}]"


@pytest.mark.parametrize(("currency", "stored"), [("JPY", ("JPY", "USD", Decimal("0.4"))), ("EUR", ("EUR", "USD", VALUE)), ("CHF", ("CHF", "USD", Decimal("0.4")))])
@pytest.mark.asyncio
async def test_fed_rate_reaches_storage_as_the_right_pair(monkeypatch: pytest.MonkeyPatch, currency: str, stored: tuple[str, str, Decimal]):
    """What the service stores from FED's tuple (alphabetical pair, ``normalize_storable_rate``): 2.5 JPY per USD is
    JPY/USD = 0.4, never 2.5."""
    _route(monkeypatch, fed_mod, lambda request: _fred_answer(request.url.params["id"], [f"{DAY.isoformat()},{VALUE}"]))

    (_day, base, quote, rate), *_rest = (await FEDProvider().fetch_rates(RANGE, [currency]))[currency]

    assert normalize_storable_rate(base, quote, rate) == stored


@pytest.mark.asyncio
async def test_fed_serves_ves_only_in_todays_unit(monkeypatch: pytest.MonkeyPatch):
    """``DEXVZUS`` before 04/10/2021 is in an older bolívar (10^6 or 10^11 of today's): those lines are never VES.
    Asked from ``"min"``, FED asks FRED from 04/10/2021 and drops anything earlier the answer still holds."""
    asked = _route(monkeypatch, fed_mod, lambda request: _fred_answer("DEXVZUS", ["2018-08-17,248209.9219", "2021-10-01,4133444.2500", "2021-10-04,4.1713", "2021-10-05,4.1651"]))

    rates = await FEDProvider().fetch_rates(("min", date(2021, 10, 5)), ["VES"])

    assert [request.url.params["cosd"] for request in asked] == [VES_FIRST_DAY.isoformat()], f"FED asked VES from {[r.url.params.get('cosd') for r in asked]}: expected {VES_FIRST_DAY}"
    assert rates["VES"] == [(date(2021, 10, 4), "USD", "VES", Decimal("4.1713")), (date(2021, 10, 5), "USD", "VES", Decimal("4.1651"))]


@pytest.mark.asyncio
async def test_fed_asks_nothing_for_ves_before_todays_unit(monkeypatch: pytest.MonkeyPatch):
    """A range that ends before 04/10/2021 has no VES in today's unit: no request, no rate."""
    asked = _route(monkeypatch, fed_mod, lambda request: _fred_answer("DEXVZUS", ["2020-01-02,0.5000"]))

    rates = await FEDProvider().fetch_rates((date(2020, 1, 1), date(2020, 1, 31)), ["VES"])

    assert asked == [] and rates["VES"] == []


def test_fed_notes_that_its_daily_rates_are_published_weekly():
    """H.10 holds one rate per US business day, released once a week: the newest FED rate can be ~10 days old. A fact
    to know, not a fault: an «info» note (ℹ️), never a «warning» (⚠️), in the 4 languages."""
    provider = FEDProvider()
    note = provider.warning_i18n
    assert set(note) == {"en", "it", "fr", "es"}, f"FED's note languages: {sorted(note)}"
    assert all(text.strip() for text in note.values())
    assert provider.warning_level == "info", f"FED's note level is {provider.warning_level!r}: the developer asked for info, not warning"
