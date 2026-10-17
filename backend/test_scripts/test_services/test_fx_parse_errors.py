"""BOE and FED FX providers: a value in their CSV that is no number (no network, no DB, no server).

X-R50 (E's review R13-SEC5 on X-R38; FED has the same hole, though E did not name it). Measured before the cure:
``BOEProvider._parse_response`` and ``FEDProvider._parse_csv`` read each line's value with ``Decimal(...)`` inside a
per-line ``try`` that catches ``ValueError`` and ``IndexError`` (FED also ``ZeroDivisionError``): that is how a line whose
date they cannot read is skipped, logged at debug. A value that is no number (``abc``, ``1.2.3``) makes ``Decimal`` raise
``decimal.InvalidOperation``, which is not a ``ValueError``: it escapes the per-line ``try`` and the parser, and
``fetch_rates`` turns it into «Unexpected BOE response format for USD» (FED: «Unexpected FED/FRED response format for
EUR») and answers the currency with no rate at all: one bad line costs every rate of the fetch.

The cure's contract (X-R50): such a line is skipped like the other invalid lines, logged at debug naming it, and every
other line of the answer is parsed; nothing raises. ECB is not here: a bad value there makes the whole response
«unexpected format» on purpose. SNB's JSON parser, with the same hole, is in ``test_snb_errors.py``.

A red whose parser raises today fails naming the exception. Every red says what the user faces. A GUARD passes before
and after the cure: a line whose date the parser cannot read is skipped, logged at debug naming it, and the others are
parsed, the frame the reds are held to. A barrier proves the log capture sees the provider module's debug events, so a
missing one is a skip not logged, never a blind capture.

Isolation: PURE. The parsers are called directly on a provider instance, on a text of the test's own: no HTTP client,
no session, no server; the log capture is structlog's, in process.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from structlog.testing import capture_logs

from backend.app.services.fx_providers.boe import plugin as boe_mod
from backend.app.services.fx_providers.boe.plugin import BOEProvider
from backend.app.services.fx_providers.fed import plugin as fed_mod
from backend.app.services.fx_providers.fed.plugin import FEDProvider

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
