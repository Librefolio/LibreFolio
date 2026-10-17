"""BOE, FED and ECB FX providers: a value in their answer that is no number (no network, no DB, no server).

X-R50 (E's review R13-SEC5 on X-R38; FED has the same hole, though E did not name it). Measured before the cure:
``BOEProvider._parse_response`` and ``FEDProvider._parse_csv`` read each line's value with ``Decimal(...)`` inside a
per-line ``try`` that catches ``ValueError`` and ``IndexError`` (FED also ``ZeroDivisionError``): that is how a line whose
date they cannot read is skipped, logged at debug. A value that is no number (``abc``, ``1.2.3``) makes ``Decimal`` raise
``decimal.InvalidOperation``, which is not a ``ValueError``: it escapes the per-line ``try`` and the parser, and
``fetch_rates`` turns it into «Unexpected BOE response format for USD» (FED: «Unexpected FED/FRED response format for
EUR») and answers the currency with no rate at all: one bad line costs every rate of the fetch.

The cure's contract (X-R50): such a line is skipped like the other invalid lines, logged at debug naming it, and every
other line of the answer is parsed; nothing raises. SNB's JSON parser, with the same hole, is in ``test_snb_errors.py``.

X-R52 (ECB, the case X-R50 left out, believing a bad value made ECB's answer «unexpected format» on purpose: it never
reaches that ``except``). Measured before the cure: ``ECBProvider.fetch_rates`` reads each observation of its SDMX-JSON
answer with ``Decimal(str(value))``, with no per-observation ``try``. A value that is no number (``"abc"``, ``"1.2.3"``, a
JSON ``null``, which becomes ``Decimal("None")``) raises ``decimal.InvalidOperation``, which ``_fetch_one``'s ``except
(KeyError, IndexError, ValueError)`` does not catch; the serial loop's ``except Exception`` logs «ECB fetch failed for
USD, skipping» and answers the currency with no rate at all: every date of the range lost for one bad value. The cure's
contract (X-R52): the observation is skipped, logged at debug naming its value, and every other observation of the
currency is kept; nothing raises. A structural problem of the answer stays as it is (not tested here).

A red whose parser raises today fails naming the exception. Every red says what the user faces. A GUARD passes before
and after the cure: for BOE and FED, a line whose date the parser cannot read is skipped, logged at debug naming it, and
the others are parsed; for ECB, three valid observations are all kept: the frame the reds are held to. A barrier proves
the log capture sees the provider module's debug events, so a missing one is a skip not logged, never a blind capture;
another, for ECB, that the double answered the plugin's one request, for USD.

Isolation: PURE. BOE's and FED's parsers are called directly on a provider instance, on a text of the test's own: no
HTTP client. ECB's ``fetch_rates`` runs whole, its module's ``httpx`` replaced for the test by the real module whose
``AsyncClient`` answers through an ``httpx.MockTransport`` (``_route``, reused from ``test_rate_limit_http_providers.py``):
its request, parameters and ``raise_for_status()`` run unchanged and never leave the process. No session, no server; the
log capture is structlog's, in process.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import httpx
import pytest
from structlog.testing import capture_logs

from backend.app.services.fx_providers.boe import plugin as boe_mod
from backend.app.services.fx_providers.boe.plugin import BOEProvider
from backend.app.services.fx_providers.ecb import plugin as ecb_mod
from backend.app.services.fx_providers.ecb.plugin import ECBProvider
from backend.app.services.fx_providers.fed import plugin as fed_mod
from backend.app.services.fx_providers.fed.plugin import FEDProvider
from backend.test_scripts.test_services.test_rate_limit_http_providers import _ecb_currency, _route

_XR50_BARRIER = "X-R50 capture barrier"
#: A value that is no number, in the place of a rate.
_XR50_NOT_A_NUMBER = [pytest.param("abc", id="abc"), pytest.param("1.2.3", id="1.2.3")]


def _xr50_parsed(module, parse, story: str) -> tuple[list, list[dict]]:
    """``parse()``, the provider module's log captured: (what it parsed, the events). An exception fails the test naming
    it: ``fetch_rates`` answers the currency with no rate at all."""
    with capture_logs() as events:
        module.logger.debug(_XR50_BARRIER)
        try:
            parsed = parse()
        except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
            pytest.fail(f"{story} raised {exc!r}: fetch_rates answers the currency with no rate at all, one bad line costing every rate of the fetch (X-R50: the line is skipped, the others parsed)")
    assert any(event.get("event") == _XR50_BARRIER and event.get("log_level") == "debug" for event in events), f"barrier: the log capture saw no debug event of {module.__name__}'s logger: {events}"
    return parsed, events


def _xr50_debug_naming(events: list[dict], text: str) -> list[dict]:
    """The debug events naming ``text``, the barrier left out."""
    return [event for event in events if event.get("log_level") == "debug" and event.get("event") != _XR50_BARRIER and text in str(event)]


# ── BOE: "DD Mon YYYY,value", 1 GBP = value USD ─────────────────────────────

#: The two valid lines around the line under test, and what they parse to.
_BOE_AROUND = ("06 Jan 1997,1.6950", "08 Jan 1997,1.7050")
_BOE_EXPECTED = [(date(1997, 1, 6), "GBP", "USD", Decimal("1.6950")), (date(1997, 1, 8), "GBP", "USD", Decimal("1.7050"))]


def _boe_answer(line: str) -> str:
    """A BOE answer for USD: its header, a valid line, ``line``, a valid line."""
    return "\n".join(("DATE,XUDLUSS", _BOE_AROUND[0], line, _BOE_AROUND[1])) + "\n"


@pytest.mark.parametrize("bad", _XR50_NOT_A_NUMBER)
def test_xr50_boe_parse_response_skips_a_value_that_is_no_number_and_parses_the_others(bad):
    """Red today: ``Decimal("abc")`` raises ``decimal.InvalidOperation``, which is not a ``ValueError``: it escapes the
    per-line ``try`` and ``_parse_response``, and ``fetch_rates`` answers USD with no rate at all («Unexpected BOE response
    format for USD»): one bad line and a BOE sync loses every rate of the range.

    Contract (X-R50): the line is skipped like the other invalid lines, logged at debug naming it; the two valid lines
    around it are parsed, as they are; nothing raises.
    """
    line = f"07 Jan 1997,{bad}"
    story = f"BOE's parser on a USD answer whose line {line!r} sits between two valid ones"

    parsed, events = _xr50_parsed(boe_mod, lambda: BOEProvider()._parse_response(_boe_answer(line), "USD"), story)

    assert parsed == _BOE_EXPECTED, f"{story} parsed {parsed}: expected the two valid lines alone, {_BOE_EXPECTED} (X-R50: skip the bad line, parse the others)"
    assert _xr50_debug_naming(events, bad), f"{story} logged no debug event naming {bad!r}: expected the skip logged at debug, like the other invalid lines (X-R50): {events}"


def test_xr50_guard_boe_parse_response_skips_a_date_it_cannot_read_and_parses_the_others():
    """Guard: green today and after. A line whose date the parser cannot read (``32 Jan 1997``) raises ``ValueError`` in
    the per-line ``try``: skipped, logged at debug naming it, the two valid lines parsed. The frame the reds are held to."""
    line = "32 Jan 1997,1.7000"
    story = f"BOE's parser on a USD answer whose line {line!r} sits between two valid ones"

    parsed, events = _xr50_parsed(boe_mod, lambda: BOEProvider()._parse_response(_boe_answer(line), "USD"), story)

    assert parsed == _BOE_EXPECTED, f"{story} parsed {parsed}: expected the two valid lines alone, {_BOE_EXPECTED}"
    assert _xr50_debug_naming(events, "32 Jan 1997"), f"{story} logged no debug event naming 32 Jan 1997: expected the skip logged at debug: {events}"


# ── FED (FRED CSV): "YYYY-MM-DD,value", 1 EUR = value USD, within the range asked ──

#: The range asked, the two valid lines around the line under test, and what they parse to.
_FED_RANGE = (date(1999, 1, 4), date(1999, 1, 6))
_FED_AROUND = ("1999-01-04,1.1812", "1999-01-06,1.1743")
_FED_EXPECTED = [(date(1999, 1, 4), "EUR", "USD", Decimal("1.1812")), (date(1999, 1, 6), "EUR", "USD", Decimal("1.1743"))]


def _fed_answer(line: str) -> str:
    """A FRED answer for EUR: its header, a valid line, ``line``, a valid line."""
    return "\n".join(("observation_date,DEXUSEU", _FED_AROUND[0], line, _FED_AROUND[1])) + "\n"


@pytest.mark.parametrize("bad", _XR50_NOT_A_NUMBER)
def test_xr50_fed_parse_csv_skips_a_value_that_is_no_number_and_parses_the_others(bad):
    """Red today: ``Decimal("abc")`` raises ``decimal.InvalidOperation``, which is not a ``ValueError``: it escapes the
    per-line ``try`` and ``_parse_csv``, and ``fetch_rates`` answers EUR with no rate at all («Unexpected FED/FRED
    response format for EUR»): one bad line and a FED sync loses every rate of the range.

    Contract (X-R50): the line is skipped like the other invalid lines, logged at debug naming it; the two valid lines
    around it are parsed, as they are; nothing raises.
    """
    line = f"1999-01-05,{bad}"
    story = f"FED's parser on an EUR answer for {_FED_RANGE[0]}–{_FED_RANGE[1]} whose line {line!r} sits between two valid ones"

    parsed, events = _xr50_parsed(fed_mod, lambda: FEDProvider()._parse_csv(_fed_answer(line), "EUR", *_FED_RANGE), story)

    assert parsed == _FED_EXPECTED, f"{story} parsed {parsed}: expected the two valid lines alone, {_FED_EXPECTED} (X-R50: skip the bad line, parse the others)"
    assert _xr50_debug_naming(events, bad), f"{story} logged no debug event naming {bad!r}: expected the skip logged at debug, like the other invalid lines (X-R50): {events}"


def test_xr50_guard_fed_parse_csv_skips_a_date_it_cannot_read_and_parses_the_others():
    """Guard: green today and after. A line whose date the parser cannot read (``1999-01-32``) raises ``ValueError`` in the
    per-line ``try``: skipped, logged at debug naming it, the two valid lines parsed. The frame the reds are held to."""
    line = "1999-01-32,1.1790"
    story = f"FED's parser on an EUR answer for {_FED_RANGE[0]}–{_FED_RANGE[1]} whose line {line!r} sits between two valid ones"

    parsed, events = _xr50_parsed(fed_mod, lambda: FEDProvider()._parse_csv(_fed_answer(line), "EUR", *_FED_RANGE), story)

    assert parsed == _FED_EXPECTED, f"{story} parsed {parsed}: expected the two valid lines alone, {_FED_EXPECTED}"
    assert _xr50_debug_naming(events, "1999-01-32"), f"{story} logged no debug event naming 1999-01-32: expected the skip logged at debug: {events}"


# ── ECB (SDMX-JSON): observation i on TIME_PERIOD's date i, 1 EUR = value USD (X-R52) ──

#: The range asked, and the three days of the answer: observations "0", "1" and "2".
_ECB_RANGE = (date(2026, 1, 5), date(2026, 1, 7))
_ECB_DAYS = (date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7))
#: The values of the first and third days, around the value under test, as ECB sends them (JSON numbers), and what they parse to.
_ECB_AROUND = (1.1712, 1.1698)
_ECB_EXPECTED = [(_ECB_DAYS[0], "EUR", "USD", Decimal("1.1712")), (_ECB_DAYS[2], "EUR", "USD", Decimal("1.1698"))]


def _ecb_answer(values: list) -> dict:
    """A minimal SDMX-JSON answer for USD: one series whose observation ``i`` is ``[values[i]]``, on ``_ECB_DAYS[i]``."""
    return {
        "dataSets": [{"series": {"0:0:0:0:0": {"observations": {str(index): [value] for index, value in enumerate(values)}}}}],
        "structure": {"dimensions": {"observation": [{"id": "TIME_PERIOD", "values": [{"id": day.isoformat()} for day in _ECB_DAYS]}]}},
    }


async def _xr52_fetched(monkeypatch: pytest.MonkeyPatch, values: list, story: str) -> tuple[dict, list[dict]]:
    """``ECBProvider().fetch_rates`` of USD over ``_ECB_RANGE``, the ECB module's ``httpx`` answering ``_ecb_answer(values)``
    through a ``MockTransport`` (``_route``), the module's log captured: (the rates, the events). An exception fails the
    test naming it. Barriers: the double answered the plugin's one request, for USD; the capture saw the module's debug
    events."""
    asked = _route(monkeypatch, ecb_mod, lambda _request: httpx.Response(200, json=_ecb_answer(values)))
    with capture_logs() as events:
        ecb_mod.logger.debug(_XR50_BARRIER)
        try:
            rates = await ECBProvider().fetch_rates(_ECB_RANGE, ["USD"])
        except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
            pytest.fail(f"{story}: fetch_rates raised {exc!r}: the ECB answer of every currency asked is lost (X-R52: the observation is skipped, the others kept)")
    assert [_ecb_currency(request) for request in asked] == ["USD"], f"barrier: the double answered {[str(request.url) for request in asked]}, not the plugin's one request, for USD"
    assert any(event.get("event") == _XR50_BARRIER and event.get("log_level") == "debug" for event in events), f"barrier: the log capture saw no debug event of {ecb_mod.__name__}'s logger: {events}"
    return rates, events


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [*_XR50_NOT_A_NUMBER, pytest.param(None, id="derived-null")])
async def test_xr52_ecb_fetch_rates_skips_an_observation_that_is_no_number_and_keeps_the_others(monkeypatch, bad):
    """Red today: ``Decimal(str(value))`` raises ``decimal.InvalidOperation`` (a JSON ``null`` too, as ``Decimal("None")``),
    which ``_fetch_one``'s ``except (KeyError, IndexError, ValueError)`` does not catch; the serial loop's ``except
    Exception`` logs «ECB fetch failed for USD, skipping», a warning that never names the value, and answers USD with no
    rate at all: one bad value and an ECB sync loses every date of the range.

    Contract (X-R52): the observation is skipped, logged at debug naming its value; the first and third days are kept, as
    given, in order; nothing raises. The ``derived-`` case reads the same rule.
    """
    story = f"ECB's answer for USD whose observation of {_ECB_DAYS[1]} is {bad!r}, between two valid ones"

    rates, events = await _xr52_fetched(monkeypatch, [_ECB_AROUND[0], bad, _ECB_AROUND[1]], story)

    assert rates == {"USD": _ECB_EXPECTED}, f"{story} gave {rates}: expected the first and third days alone, {_ECB_EXPECTED} (X-R52: skip the bad observation, keep the others)"
    assert _xr50_debug_naming(events, str(bad)), f"{story} logged no debug event naming {bad!r}: expected the skip logged at debug, naming the value (X-R52): {events}"


@pytest.mark.asyncio
async def test_xr52_guard_ecb_fetch_rates_keeps_three_valid_observations(monkeypatch):
    """Guard: green today and after. Three valid observations, as ECB sends them (JSON numbers): all three kept, as given,
    in order. The frame the reds are held to: the double, the answer and its parse are sound."""
    story = "ECB's answer for USD with three valid observations"

    rates, _events = await _xr52_fetched(monkeypatch, [_ECB_AROUND[0], 1.1734, _ECB_AROUND[1]], story)

    expected = [_ECB_EXPECTED[0], (_ECB_DAYS[1], "EUR", "USD", Decimal("1.1734")), _ECB_EXPECTED[1]]
    assert rates == {"USD": expected}, f"{story} gave {rates}: expected all three, {expected}"
