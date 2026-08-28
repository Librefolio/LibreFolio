"""SNB FX provider — error and parsing paths (no network, no DB, no server).

The happy path against the live SNB Data Portal is exercised by the network
suite (``external fx-providers``). What is *not* covered there — and is exactly
what a user hits when the portal misbehaves — lives here:

  * a dimensions endpoint that errors → ``FXServiceError`` (cannot load the map);
  * an unsupported base currency (SNB only quotes against CHF);
  * a currency the portal does not know (skipped, empty series);
  * an HTTP error on the data endpoint → ``FXServiceError``;
  * the JSON parser fed monthly points, month-end (10-char) dates, out-of-range
    points, a zero value, a multiplier > 1, and an unrecognised timeseries key.

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

from backend.app.services.fx import FXServiceError
from backend.app.services.fx_providers import snb as snb_mod
from backend.app.services.fx_providers.snb import SNBProvider

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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
