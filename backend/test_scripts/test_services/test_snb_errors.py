"""SNB FX provider — error and parsing paths (no network, no DB, no server).

The happy path against the live SNB Data Portal is exercised by the network
suite (``external fx-providers``). What is *not* covered there — and is exactly
what a user hits when the portal misbehaves — lives here:

  * a dimensions endpoint that errors → ``FXServiceError`` (cannot load the map);
  * an unsupported base currency (SNB only quotes against CHF);
  * a currency the portal does not know (skipped, empty series);
  * an HTTP error on the data endpoint → ``FXServiceError``;
  * the JSON parser fed monthly points, month-end (10-char) dates, out-of-range
    points, a zero value, a multiplier > 1, and an unrecognised timeseries key;
  * X-R50 (E's review R13-SEC5 on X-R38): a point whose value is no number
    (``"abc"``, ``"1.2.3"``) → skipped, logged at debug, every other point
    parsed (see its block at the end).

Every call that would reach the network is replaced by a fake ``httpx`` bound
into the ``snb`` module only (the global ``httpx`` is left untouched), so the
assertions are on *exact* values rather than "some rate arrived".
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from structlog.testing import capture_logs

from backend.app.services.fx.base import FXServiceError
from backend.app.services.fx_providers.snb import plugin as snb_mod
from backend.app.services.fx_providers.snb.plugin import SNBProvider

# ── httpx double bound into the snb module only ─────────────────────────────


class _FakeResponse:
    def __init__(self, payload=None, status_error: Exception | None = None, json_error: Exception | None = None):
        self._payload = payload
        self._status_error = status_error
        self._json_error = json_error

    def raise_for_status(self):
        if self._status_error is not None:
            raise self._status_error

    def json(self):
        if self._json_error is not None:
            raise self._json_error
        return self._payload


class _FakeAsyncClient:
    """Async-context-manager stand-in for ``httpx.AsyncClient``."""

    def __init__(self, handler, **_kwargs):
        self._handler = handler

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    async def get(self, url, params=None):
        return self._handler(url, params)


def _install_fake_httpx(monkeypatch, handler) -> None:
    """Replace ``snb.httpx`` with a namespace whose AsyncClient uses ``handler``.

    ``HTTPError`` stays the real class so the provider's ``except httpx.HTTPError``
    keeps catching what the fake raises.
    """
    fake = SimpleNamespace(
        AsyncClient=lambda **kwargs: _FakeAsyncClient(handler, **kwargs),
        HTTPError=httpx.HTTPError,
    )
    monkeypatch.setattr(snb_mod, "httpx", fake)


@pytest.fixture(autouse=True)
def _reset_currency_map():
    """Save/restore the process-wide class cache so tests are hermetic."""
    saved_iso = SNBProvider._iso_to_d1
    saved_d1 = SNBProvider._d1_to_iso
    SNBProvider._iso_to_d1 = None
    SNBProvider._d1_to_iso = None
    try:
        yield
    finally:
        SNBProvider._iso_to_d1 = saved_iso
        SNBProvider._d1_to_iso = saved_d1


# Minimal dimensions payload: one group (D1_0) with two real currencies, one
# skipped forward code, and one id the regex rejects. A sibling non-D1 dimension
# exercises the "not the currency dimension" skip.
_DIMENSIONS = {
    "dimensions": [
        {"id": "D0", "dimensionItems": [{"id": "M0"}, {"id": "M1"}]},  # not D1 → skipped
        {
            "id": "D1",
            "dimensionItems": [
                {
                    "id": "D1_0",
                    "dimensionItems": [
                        {"id": "EUR1"},
                        {"id": "CNY100"},
                    ],
                },
                {"id": "USD3M"},  # forward rate → skipped
                {"id": "NOTACODE"},  # regex miss → skipped
            ],
        },
    ]
}


def _preload_map(provider: SNBProvider) -> None:
    """Seed the instance currency map so _ensure_currency_map short-circuits."""
    provider._iso_to_d1 = {"EUR": "EUR1", "CNY": "CNY100"}
    provider._d1_to_iso = {"EUR1": ("EUR", 1), "CNY100": ("CNY", 100)}


# ── metadata / properties ───────────────────────────────────────────────────


def test_metadata_properties():
    p = SNBProvider()
    assert p.code == "SNB"
    assert p.provider_code == "SNB"
    assert p.name == "Swiss National Bank"
    assert p.base_currency == "CHF"
    assert p.icon and p.icon.endswith("favicon.ico")
    assert p.docs_url and "snb" in p.docs_url
    assert p.description
    # i18n dicts carry the four shipped locales
    assert set(p.description_i18n) == {"en", "it", "fr", "es"}
    assert set(p.warning_i18n) == {"en", "it", "fr", "es"}
    assert "CHF" in p.test_currencies


# ── _ensure_currency_map ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_currency_map_loads_and_skips(monkeypatch):
    _install_fake_httpx(monkeypatch, lambda url, params: _FakeResponse(_DIMENSIONS))

    currencies = await SNBProvider().get_supported_currencies()

    # CHF is always present; the two mapped currencies are there; the forward
    # code and the unrecognised id are absent.
    assert "CHF" in currencies
    assert "EUR" in currencies and "CNY" in currencies
    assert "USD" not in currencies  # only USD3M was offered, and it is skipped
    assert SNBProvider._d1_to_iso["CNY100"] == ("CNY", 100)


@pytest.mark.asyncio
async def test_currency_map_http_failure_raises_fx_error(monkeypatch):
    def boom(url, params):
        return _FakeResponse(status_error=httpx.HTTPError("dimensions 503"))

    _install_fake_httpx(monkeypatch, boom)

    with pytest.raises(FXServiceError) as exc:
        await SNBProvider().get_supported_currencies()
    assert "Cannot load SNB currency list" in str(exc.value)


# ── fetch_rates: guard branches that never reach the network ────────────────


@pytest.mark.asyncio
async def test_fetch_rates_rejects_non_chf_base():
    with pytest.raises(ValueError, match="only supports CHF"):
        await SNBProvider().fetch_rates(("min", date(2026, 3, 1)), ["USD"], base_currency="USD")


@pytest.mark.asyncio
async def test_fetch_rates_only_chf_returns_empty(monkeypatch):
    p = SNBProvider()
    _preload_map(p)
    # If any HTTP call were made this would explode; it must not be reached.
    _install_fake_httpx(monkeypatch, lambda url, params: (_ for _ in ()).throw(AssertionError("no HTTP expected")))

    result = await p.fetch_rates((date(2026, 1, 1), date(2026, 3, 1)), ["CHF"])
    assert result == {}


@pytest.mark.asyncio
async def test_fetch_rates_unsupported_currency_skipped(monkeypatch):
    p = SNBProvider()
    _preload_map(p)
    _install_fake_httpx(monkeypatch, lambda url, params: (_ for _ in ()).throw(AssertionError("no HTTP expected")))

    result = await p.fetch_rates((date(2026, 1, 1), date(2026, 3, 1)), ["ZZZ"])
    # Unknown currency yields an explicit empty series, no request issued.
    assert result == {"ZZZ": []}


# ── fetch_rates: full path with the data endpoint mocked ────────────────────

_DATA_PAYLOAD = {
    "timeseries": [
        {
            "metadata": {"key": "EPB@SNB.devkum{M0,EUR1}"},
            "values": [
                {"date": "2026-01", "value": 0.94114},
                {"date": "2026-02", "value": 0.95},
                {"date": "2025-06", "value": 0.90},  # before range → dropped
            ],
        },
        {
            "metadata": {"key": "EPB@SNB.devkum{M0,CNY100}"},
            "values": [
                {"date": "2026-01", "value": 11.18798},  # ÷100 multiplier
                {"date": "2026-02", "value": None},  # missing value → skipped
                {"date": "2026-03", "value": 0},  # zero → skipped
            ],
        },
        {
            "metadata": {"key": "EPB@SNB.devkum{M0,UNKNOWN9}"},  # not in map → skipped
            "values": [{"date": "2026-01", "value": 1.23}],
        },
    ]
}


@pytest.mark.asyncio
async def test_fetch_rates_parses_monthly_points(monkeypatch):
    p = SNBProvider()
    _preload_map(p)
    _install_fake_httpx(monkeypatch, lambda url, params: _FakeResponse(_DATA_PAYLOAD))

    result = await p.fetch_rates((date(2026, 1, 1), date(2026, 3, 31)), ["EUR", "CNY"])

    # EUR: two in-range monthly points assigned to the 1st, out-of-range dropped.
    eur = result["EUR"]
    assert [(d, iso, base) for d, iso, base, _ in eur] == [
        (date(2026, 1, 1), "EUR", "CHF"),
        (date(2026, 2, 1), "EUR", "CHF"),
    ]
    assert eur[0][3] == Decimal("0.94114")

    # CNY: only the January point survives (None + zero dropped); divided by 100.
    cny = result["CNY"]
    assert len(cny) == 1
    assert cny[0][0] == date(2026, 1, 1)
    assert cny[0][3] == Decimal("11.18798") / Decimal("100")


@pytest.mark.asyncio
async def test_fetch_rates_http_error_raises_fx_error(monkeypatch):
    p = SNBProvider()
    _preload_map(p)

    def boom(url, params):
        return _FakeResponse(status_error=httpx.HTTPError("data 500"))

    _install_fake_httpx(monkeypatch, boom)

    with pytest.raises(FXServiceError, match="SNB API error"):
        await p.fetch_rates((date(2026, 1, 1), date(2026, 3, 1)), ["EUR"])


@pytest.mark.asyncio
async def test_fetch_rates_bad_json_raises_unexpected(monkeypatch):
    p = SNBProvider()
    _preload_map(p)

    # A 200 response whose body is not decodable → generic except → "Unexpected".
    def bad_json(url, params):
        return _FakeResponse(json_error=ValueError("not json"))

    _install_fake_httpx(monkeypatch, bad_json)

    with pytest.raises(FXServiceError, match="Unexpected SNB response"):
        await p.fetch_rates((date(2026, 1, 1), date(2026, 3, 1)), ["EUR"])


# ── _parse_json directly: date shapes and edge values ───────────────────────


def test_parse_json_month_end_and_out_of_range():
    p = SNBProvider()
    p._d1_to_iso = {"EUR1": ("EUR", 1), "USD1": ("USD", 1)}
    data = {
        "timeseries": [
            {
                "metadata": {"key": "EPB@SNB.devkum{M0,EUR1}"},
                "values": [
                    {"date": "2026-02-27", "value": 0.9411},  # 10-char ISO date
                    {"date": "2026-99", "value": 1.0},  # malformed → skipped
                    {"date": "bad", "value": 1.0},  # unparseable → skipped
                    {"date": "2030-01", "value": 1.0},  # after end → skipped
                ],
            },
            {
                # A recognised currency whose every point is out of range: the
                # series yields no rates, so it is not added (branch 347->301).
                "metadata": {"key": "EPB@SNB.devkum{M0,USD1}"},
                "values": [{"date": "2020-01", "value": 1.0}],
            },
        ]
    }
    out = p._parse_json(data, date(2026, 1, 1), date(2026, 6, 30))
    assert list(out) == ["EUR"]
    assert out["EUR"] == [(date(2026, 2, 27), "EUR", "CHF", Decimal("0.9411"))]


def test_parse_json_unknown_key_skipped():
    p = SNBProvider()
    p._d1_to_iso = {"EUR1": ("EUR", 1)}
    data = {"timeseries": [{"metadata": {"key": "no-braces-here"}, "values": [{"date": "2026-01", "value": 1.0}]}]}
    assert p._parse_json(data, date(2026, 1, 1), date(2026, 6, 30)) == {}


# ── _extract_d1_from_key ────────────────────────────────────────────────────


def test_extract_d1_from_key_variants():
    assert SNBProvider._extract_d1_from_key("EPB@SNB.devkum{M0,CNY100}") == "CNY100"
    assert SNBProvider._extract_d1_from_key("no braces") is None
    assert SNBProvider._extract_d1_from_key("{onlyone}") is None


# ── X-R50: a point whose value is no number ─────────────────────────────────
#
# Measured before the cure (E's review R13-SEC5 on X-R38): _parse_json reads a point's value with Decimal(str(value))
# inside a per-point try that catches ValueError and ZeroDivisionError, which is how a point whose month it cannot read
# is skipped, logged at debug. A value that is no number ("abc", "1.2.3") makes Decimal raise decimal.InvalidOperation,
# which is not a ValueError: it escapes the per-point try and the parser, which fetch_rates calls outside its own try,
# so fetch_rates raises it as it is: the whole SNB answer is lost, every currency of the fetch with it.
#
# Contract (X-R50): the point is skipped like the other invalid points, logged at debug naming it; every other point of
# the answer is parsed, of every currency; nothing raises.

_XR50_BARRIER = "X-R50 capture barrier"
#: What ``_xr50_answer`` parses to without its point under test: EUR's January and March, CNY's February (÷ 100).
_XR50_EXPECTED = {
    "EUR": [(date(1999, 1, 1), "EUR", "CHF", Decimal("1.6")), (date(1999, 3, 1), "EUR", "CHF", Decimal("1.62"))],
    "CNY": [(date(1999, 2, 1), "CNY", "CHF", Decimal("0.195"))],
}


def _xr50_answer(point: dict) -> dict:
    """An SNB answer for EUR and CNY over the first quarter of 1999, ``point`` between EUR's January and March."""
    return {
        "timeseries": [
            {"metadata": {"key": "EPB@SNB.devkum{M0,EUR1}"}, "values": [{"date": "1999-01", "value": 1.6}, point, {"date": "1999-03", "value": 1.62}]},
            {"metadata": {"key": "EPB@SNB.devkum{M0,CNY100}"}, "values": [{"date": "1999-02", "value": 19.5}]},
        ]
    }


def _xr50_parsed(point: dict, story: str) -> tuple[dict, list[dict]]:
    """``_parse_json`` of ``_xr50_answer(point)`` over the first quarter of 1999, on a provider with the EUR and CNY map,
    the snb module's log captured: (what it parsed, the events). An exception fails the test naming it."""
    provider = SNBProvider()
    _preload_map(provider)
    with capture_logs() as events:
        snb_mod.logger.debug(_XR50_BARRIER)
        try:
            parsed = provider._parse_json(_xr50_answer(point), date(1999, 1, 1), date(1999, 3, 31))
        except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
            pytest.fail(f"{story} raised {exc!r}: fetch_rates raises it as it is, and the whole SNB answer is lost, every currency of the fetch (X-R50: the point is skipped, the others parsed)")
    assert any(event.get("event") == _XR50_BARRIER and event.get("log_level") == "debug" for event in events), f"barrier: the log capture saw no debug event of the snb module's logger: {events}"
    return parsed, events


def _xr50_debug_naming(events: list[dict], text: str) -> list[dict]:
    """The debug events naming ``text``, the barrier left out."""
    return [event for event in events if event.get("log_level") == "debug" and event.get("event") != _XR50_BARRIER and text in str(event)]


@pytest.mark.parametrize("bad", [pytest.param("abc", id="abc"), pytest.param("1.2.3", id="1.2.3")])
def test_xr50_parse_json_skips_a_value_that_is_no_number_and_parses_the_others(bad):
    """Red today: ``Decimal("abc")`` raises ``decimal.InvalidOperation``, which is not a ``ValueError``: it escapes the
    per-point ``try`` and ``_parse_json``, and ``fetch_rates``, which calls the parser outside its own ``try``, raises it
    as it is: one bad point and the whole SNB answer is lost, CNY's rate with EUR's.

    Contract (X-R50): the point is skipped like the other invalid points, logged at debug naming it; EUR's January and
    March and CNY's February are parsed, as they are; nothing raises.
    """
    point = {"date": "1999-02", "value": bad}
    story = f"SNB's parser on an answer whose EUR point {point} sits between two valid ones, a CNY point beside them"

    parsed, events = _xr50_parsed(point, story)

    assert parsed == _XR50_EXPECTED, f"{story} parsed {parsed}: expected every other point, {_XR50_EXPECTED} (X-R50: skip the bad point, parse the others)"
    assert _xr50_debug_naming(events, bad), f"{story} logged no debug event naming {bad!r}: expected the skip logged at debug, like the other invalid points (X-R50): {events}"


def test_xr50_guard_parse_json_skips_a_month_it_cannot_read_and_parses_the_others():
    """Guard: green today and after. A point whose month the parser cannot read (``1999-13``) raises ``ValueError`` in the
    per-point ``try``: skipped, logged at debug naming it, every other point parsed. The frame the red above is held to."""
    point = {"date": "1999-13", "value": 1.61}
    story = f"SNB's parser on an answer whose EUR point {point} sits between two valid ones, a CNY point beside them"

    parsed, events = _xr50_parsed(point, story)

    assert parsed == _XR50_EXPECTED, f"{story} parsed {parsed}: expected every other point, {_XR50_EXPECTED}"
    assert _xr50_debug_naming(events, "1999-13"), f"{story} logged no debug event naming 1999-13: expected the skip logged at debug: {events}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
