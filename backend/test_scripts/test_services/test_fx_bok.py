"""BOK FX provider: ECOS StatisticSearch, one series per currency, the key in the path, pages, JPY/IDR/VND scale and what it refuses (no network, no DB, no server).

Lane 75, wave 2 (plan ``plan-phase02FxCentralBanksOndata2.prompt.md``). The shape of the API:

- ``GET {API_ROOT}/{KEY}/json/en/{start_row}/{end_row}/731Y001/D/{YYYYMMDD}/{YYYYMMDD}/{item}``: the key travels in the PATH.
- A good answer is ``{"StatisticSearch": {"list_total_count": N, "row": [{"ITEM_CODE1": …, "TIME": "20261118", "DATA_VALUE": "1338.8", …}]}}``
  ascending by ``TIME``; the value is KRW per ``units`` of the foreign currency (100 for JPY, IDR and VND).
- Errors also come as HTTP 200: ``{"RESULT": {"CODE": "INFO-200", "MESSAGE": "…"}}``.

Every answer here is synthetic, written by hand in the feed's shape, never data downloaded from the bank.

Isolation: PURE. ``fetch_rates`` runs whole, its module's ``httpx`` replaced for the test by the real module whose
``AsyncClient`` answers through an ``httpx.MockTransport`` (``_route``, from ``test_rate_limit_http_providers.py``).
The pause between series is zero, or a recorder, never a real sleep.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date
from decimal import Decimal

import httpx
import pytest

from backend.app.services.fx.base import FXNotConfiguredError, FXRateLimitedError, FXServiceError
from backend.app.services.fx_providers.bok import plugin as bok_mod
from backend.app.services.fx_providers.bok.plugin import BOKProvider
from backend.app.services.plugin_settings.contract import BoundSettings
from backend.app.services.plugin_settings.fields import SettingScope, SettingType
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

KEY = "TESTKEY123ABC"
RANGE = (date(2026, 11, 16), date(2026, 11, 19))
ROOT = "https://ecos.bok.or.kr/api/StatisticSearch"

EXPECTED_ITEMS = {
    "USD": ("0000001", 1),
    "CNY": ("0000053", 1),
    "JPY": ("0000002", 100),
    "EUR": ("0000003", 1),
    "GBP": ("0000012", 1),
    "CAD": ("0000013", 1),
    "CHF": ("0000014", 1),
    "AUD": ("0000017", 1),
    "NZD": ("0000026", 1),
    "HKD": ("0000015", 1),
    "TWD": ("0000031", 1),
    "MNT": ("0000032", 1),
    "KZT": ("0000033", 1),
    "THB": ("0000028", 1),
    "SGD": ("0000024", 1),
    "IDR": ("0000029", 100),
    "MYR": ("0000025", 1),
    "PHP": ("0000034", 1),
    "VND": ("0000035", 100),
    "BND": ("0000036", 1),
    "INR": ("0000037", 1),
    "PKR": ("0000038", 1),
    "BDT": ("0000039", 1),
    "MXN": ("0000040", 1),
    "BRL": ("0000041", 1),
    "ARS": ("0000042", 1),
    "SEK": ("0000016", 1),
    "DKK": ("0000018", 1),
    "NOK": ("0000019", 1),
    "RUB": ("0000043", 1),
    "HUF": ("0000044", 1),
    "PLN": ("0000045", 1),
    "CZK": ("0000046", 1),
    "SAR": ("0000020", 1),
    "QAR": ("0000047", 1),
    "ILS": ("0000048", 1),
    "JOD": ("0000049", 1),
    "KWD": ("0000021", 1),
    "BHD": ("0000022", 1),
    "AED": ("0000023", 1),
    "TRY": ("0000050", 1),
    "ZAR": ("0000051", 1),
    "EGP": ("0000052", 1),
}

USD = "0000001"
JPY = "0000002"
EUR = "0000003"
IDR = "0000029"


def _provider(key: str | None = KEY) -> BOKProvider:
    provider = BOKProvider()
    if key is not None:
        provider.bind_settings(BoundSettings(BOKProvider.settings_fields, {}, {"api_key": key}))
    return provider


def _row(item: str, day: str, value: str) -> dict:
    return {
        "STAT_CODE": "731Y001",
        "ITEM_CODE1": item,
        "ITEM_NAME1": f"Won per synthetic {item}",
        "UNIT_NAME": "Won",
        "TIME": day,
        "DATA_VALUE": value,
    }


def _json(body: dict, status: int = 200) -> httpx.Response:
    return httpx.Response(status, headers={"content-type": "application/json"}, text=json.dumps(body))


def _answer(*rows: dict, total: int | None = None) -> httpx.Response:
    return _json({"StatisticSearch": {"list_total_count": len(rows) if total is None else total, "row": list(rows)}})


def _result(code: str, message: str = "synthetic") -> httpx.Response:
    return _json({"RESULT": {"CODE": code, "MESSAGE": message}})


def _item_of(request: httpx.Request) -> str:
    """The item code of a request (the last path segment)."""
    return request.url.path.split("/")[-1]


def _parts(request: httpx.Request) -> list[str]:
    """The path after ``/api/StatisticSearch/``: key, json, en, start_row, end_row, stat, D, start, end, item."""
    return request.url.path.split("/api/StatisticSearch/")[1].split("/")


@pytest.fixture(autouse=True)
def _no_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test waits between two series, unless it records the pause itself."""
    monkeypatch.setattr(BOKProvider, "PAUSE_SECONDS", 0)


def _by_item(answers: dict[str, httpx.Response | tuple]):
    """An answer function serving per item code; an unknown item gets INFO-200 like the bank."""

    def route(request: httpx.Request) -> httpx.Response:
        found = answers.get(_item_of(request))
        return found if found is not None else _result("INFO-200", "No data found.")

    return route


# ── Values and direction ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bok_usd_is_krw_per_one_unit_ascending(monkeypatch: pytest.MonkeyPatch):
    """«1 USD = 1338.8 KRW»: ``(d, USD, KRW, value)``, foreign currency first, ascending by day."""
    _route(monkeypatch, bok_mod, _by_item({USD: _answer(_row(USD, "20261118", "1338.8"), _row(USD, "20261119", "1340.1"))}))

    rates = await _provider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [
        (date(2026, 11, 18), "USD", "KRW", Decimal("1338.8")),
        (date(2026, 11, 19), "USD", "KRW", Decimal("1340.1")),
    ]


@pytest.mark.asyncio
async def test_bok_output_is_ascending_even_if_the_feed_is_not(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, bok_mod, _by_item({USD: _answer(_row(USD, "20261119", "3"), _row(USD, "20261116", "1"), _row(USD, "20261118", "2"))}))

    rates = await _provider().fetch_rates(RANGE, ["USD"])

    assert [r[0] for r in rates["USD"]] == [date(2026, 11, 16), date(2026, 11, 18), date(2026, 11, 19)]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("currency", "item", "published", "expected"),
    [
        pytest.param("JPY", JPY, "837.17", Decimal("8.3717"), id="jpy-100"),
        pytest.param("IDR", IDR, "7.32", Decimal("0.0732"), id="idr-100"),
        pytest.param("EUR", EUR, "1552.5", Decimal("1552.5"), id="eur-1"),
    ],
)
async def test_bok_divides_the_value_by_the_units_of_the_quote(monkeypatch: pytest.MonkeyPatch, currency: str, item: str, published: str, expected: Decimal):
    _route(monkeypatch, bok_mod, _by_item({item: _answer(_row(item, "20261119", published))}))

    rates = await _provider().fetch_rates(RANGE, [currency])

    assert rates[currency] == [(date(2026, 11, 19), currency, "KRW", expected)]
    assert isinstance(rates[currency][0][3], Decimal)


@pytest.mark.asyncio
async def test_bok_unreadable_rows_are_skipped_and_the_others_stay(monkeypatch: pytest.MonkeyPatch):
    """A bad TIME, an empty, a text, a zero and a negative value, another item and days out of range lose their own row only."""
    rows = [
        _row(USD, "20261119", "1340.1"),
        _row(USD, "notadate", "1300"),
        _row(USD, "20261118", ""),
        _row(USD, "20261117", "abc"),
        _row(USD, "20261116", "0"),
        _row(USD, "20261116", "-5"),
        _row(EUR, "20261118", "1552.5"),
        _row(USD, "20261120", "1400"),
        _row(USD, "20261110", "1200"),
    ]
    _route(monkeypatch, bok_mod, _by_item({USD: _answer(*rows)}))

    rates = await _provider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [(date(2026, 11, 19), "USD", "KRW", Decimal("1340.1"))]


@pytest.mark.asyncio
async def test_bok_a_day_with_two_different_values_is_dropped_and_equal_ones_count_once(monkeypatch: pytest.MonkeyPatch):
    rows = [
        _row(USD, "20261117", "1300.0"),
        _row(USD, "20261117", "1301.0"),
        _row(USD, "20261118", "1338.8"),
        _row(USD, "20261118", "1338.8"),
    ]
    _route(monkeypatch, bok_mod, _by_item({USD: _answer(*rows)}))

    rates = await _provider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [(date(2026, 11, 18), "USD", "KRW", Decimal("1338.8"))]


# ── Requests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bok_asks_one_get_per_currency_sorted_with_the_key_in_the_path(monkeypatch: pytest.MonkeyPatch):
    """EUR, JPY, USD asked in that order; the URL is exactly the documented path, no query string."""
    asked = _route(monkeypatch, bok_mod, lambda request: _result("INFO-200"))

    await _provider().fetch_rates(RANGE, ["USD", "JPY", "EUR"])

    tail = f"1/{bok_mod.PAGE_ROWS}/731Y001/D/20261116/20261119"
    assert [str(r.url) for r in asked] == [f"{ROOT}/{KEY}/json/en/{tail}/{item}" for item in (EUR, JPY, USD)]
    assert all(r.method == "GET" and r.url.query == b"" for r in asked)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "start",
    [pytest.param("min", id="min"), pytest.param(date(1900, 1, 1), id="before-first-day")],
)
async def test_bok_asks_from_its_first_day_at_the_earliest(monkeypatch: pytest.MonkeyPatch, start):
    asked = _route(monkeypatch, bok_mod, lambda request: _result("INFO-200"))

    await _provider().fetch_rates((start, date(2026, 11, 19)), ["USD"])

    assert _parts(asked[0])[7:9] == ["19640504", "20261119"]


@pytest.mark.asyncio
async def test_bok_every_asked_currency_is_a_key_and_krw_is_none(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, bok_mod, _by_item({USD: _answer(_row(USD, "20261119", "1340.1"))}))

    rates = await _provider().fetch_rates(RANGE, ["USD", "KRW", "EUR"])

    assert set(rates) == {"USD", "EUR"}
    assert rates["EUR"] == [] and len(rates["USD"]) == 1
    assert sorted(_item_of(r) for r in asked) == sorted([EUR, USD])


@pytest.mark.asyncio
async def test_bok_a_currency_outside_the_items_is_empty_and_not_asked(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, bok_mod, _by_item({USD: _answer(_row(USD, "20261119", "1340.1"))}))

    rates = await _provider().fetch_rates(RANGE, ["XXX", "USD"])

    assert rates["XXX"] == [] and len(rates["USD"]) == 1
    assert len(asked) == 1


@pytest.mark.asyncio
async def test_bok_asks_the_next_page_until_every_row_is_read(monkeypatch: pytest.MonkeyPatch):
    """``list_total_count`` 3 and a page of 2 rows: pages 1-2 then 3-4, the three rows joined."""
    monkeypatch.setattr(bok_mod, "PAGE_ROWS", 2)
    every = [_row(USD, "20261117", "1"), _row(USD, "20261118", "2"), _row(USD, "20261119", "3")]
    pages: list[tuple[int, int]] = []

    def route(request: httpx.Request) -> httpx.Response:
        first, last = int(_parts(request)[3]), int(_parts(request)[4])
        pages.append((first, last))
        return _answer(*every[first - 1 : last], total=3)

    _route(monkeypatch, bok_mod, route)

    rates = await _provider().fetch_rates(RANGE, ["USD"])

    assert pages == [(1, 2), (3, 4)]
    assert [r[3] for r in rates["USD"]] == [Decimal("1"), Decimal("2"), Decimal("3")]


@pytest.mark.asyncio
async def test_bok_one_page_is_enough_when_the_total_fits(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, bok_mod, _by_item({USD: _answer(_row(USD, "20261119", "1340.1"), _row(USD, "20261118", "1338.8"))}))

    await _provider().fetch_rates(RANGE, ["USD"])

    assert len(asked) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("currencies", [["USD", "JPY", "CHF", "AUD", "CAD", "EUR"], ["USD", "JPY", "CHF", "AUD", "CAD", "EUR", "GBP"]])
async def test_bok_asks_at_most_three_series_at_once(monkeypatch: pytest.MonkeyPatch, currencies: list[str]):
    in_flight = 0
    peak = 0
    asked: list[str] = []

    async def fake_fetch_one(self, currency: str, start: date, end: date):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        asked.append(currency)
        for _ in range(5):
            await asyncio.sleep(0)
        in_flight -= 1
        return [(end, Decimal("1.0"))]  # (day, KRW per 1 unit): what BOK's _fetch_one returns

    monkeypatch.setattr(BOKProvider, "_fetch_one", fake_fetch_one)

    rates = await _provider().fetch_rates(RANGE, currencies)

    assert BOKProvider.MAX_PARALLEL == 3
    assert peak == 3
    assert sorted(asked) == sorted(currencies)
    assert all(len(rates[c]) == 1 for c in currencies)


@pytest.mark.asyncio
async def test_bok_pauses_between_two_starts_but_not_before_the_first(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(BOKProvider, "PAUSE_SECONDS", 0.3)
    slept: list[float] = []

    async def record(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(bok_mod.asyncio, "sleep", record)
    asked = _route(monkeypatch, bok_mod, lambda request: _result("INFO-200"))

    await _provider().fetch_rates(RANGE, ["USD", "EUR", "JPY"])

    assert len(asked) == 3
    assert slept == [0.3, 0.3]


@pytest.mark.asyncio
async def test_bok_one_series_needs_no_pause(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(BOKProvider, "PAUSE_SECONDS", 0.3)
    slept: list[float] = []

    async def record(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(bok_mod.asyncio, "sleep", record)
    _route(monkeypatch, bok_mod, lambda request: _result("INFO-200"))

    await _provider().fetch_rates(RANGE, ["USD"])

    assert slept == []


# ── Key and early exits ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bok_without_a_key_is_not_configured_and_asks_nothing(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, bok_mod, lambda request: _result("INFO-200"))

    with pytest.raises(FXNotConfiguredError) as refused:
        await _provider(key=None).fetch_rates(RANGE, ["USD"])

    assert refused.value.missing == ["api_key"] and asked == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("window", "currencies", "expected"),
    [
        pytest.param(RANGE, ["KRW"], {}, id="krw-only"),
        pytest.param(RANGE, ["XXX", "CHZ"], {"XXX": [], "CHZ": []}, id="outside-items-only"),
        pytest.param((date(2026, 11, 19), date(2026, 11, 16)), ["USD"], {"USD": []}, id="start-after-end"),
        pytest.param((date(1950, 1, 1), date(1960, 1, 1)), ["USD"], {"USD": []}, id="end-before-first-day"),
    ],
)
async def test_bok_nothing_to_ask_needs_no_key_and_makes_no_request(monkeypatch: pytest.MonkeyPatch, window, currencies, expected):
    asked = _route(monkeypatch, bok_mod, lambda request: _result("INFO-200"))

    assert await _provider(key=None).fetch_rates(window, currencies) == expected
    assert asked == []


@pytest.mark.asyncio
async def test_bok_other_base_currency_is_refused_and_krw_or_none_accepted(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, bok_mod, _by_item({USD: _answer(_row(USD, "20261119", "1340.1"))}))

    with pytest.raises(ValueError):
        await _provider().fetch_rates(RANGE, ["USD"], base_currency="EUR")

    assert len((await _provider().fetch_rates(RANGE, ["USD"], base_currency="KRW"))["USD"]) == 1
    assert len((await _provider().fetch_rates(RANGE, ["USD"], base_currency=None))["USD"]) == 1
    assert len(asked) == 2


# ── RESULT codes and HTTP errors ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bok_info_200_is_a_currency_without_rows_not_an_error(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, bok_mod, lambda request: _result("INFO-200", "No data found."))

    assert await _provider().fetch_rates(RANGE, ["USD"]) == {"USD": []}


@pytest.mark.asyncio
async def test_bok_info_100_is_a_refused_key_for_the_whole_call(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, bok_mod, lambda request: _result("INFO-100", "Invalid activation key."))

    with pytest.raises(FXServiceError) as refused:
        await _provider().fetch_rates(RANGE, ["USD", "EUR"])

    assert not isinstance(refused.value, FXRateLimitedError)
    assert "key" in str(refused.value).lower() and KEY not in str(refused.value)
    assert len(asked) <= BOKProvider.MAX_PARALLEL


@pytest.mark.asyncio
async def test_bok_error_602_is_a_rate_limit_for_the_call(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, bok_mod, lambda request: _result("ERROR-602", "Too many calls."))

    with pytest.raises(FXRateLimitedError):
        await _provider().fetch_rates(RANGE, ["USD", "EUR"])


@pytest.mark.asyncio
async def test_bok_http_429_is_a_rate_limit(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, bok_mod, lambda request: httpx.Response(429, headers={"Retry-After": "30"}))

    with pytest.raises(FXRateLimitedError):
        await _provider().fetch_rates(RANGE, ["USD"])


@pytest.mark.asyncio
async def test_bok_another_result_code_skips_that_currency_only(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, bok_mod, _by_item({EUR: _result("ERROR-500", "Server error"), USD: _answer(_row(USD, "20261119", "1340.1"))}))

    rates = await _provider().fetch_rates(RANGE, ["EUR", "USD"])

    assert rates["EUR"] == [] and len(rates["USD"]) == 1


_BROKEN = [
    pytest.param(lambda request: httpx.Response(500, text="Internal error"), id="http-500"),
    pytest.param(lambda request: httpx.Response(200, headers={"content-type": "text/html"}, text="<!DOCTYPE html><html></html>"), id="html-page"),
    pytest.param(lambda request: httpx.Response(200, text="not json at all"), id="non-json"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("broken", _BROKEN)
async def test_bok_one_failed_series_is_empty_and_the_others_are_returned(monkeypatch: pytest.MonkeyPatch, broken):
    def route(request: httpx.Request) -> httpx.Response:
        return broken(request) if _item_of(request) == EUR else _answer(_row(USD, "20261119", "1340.1"))

    _route(monkeypatch, bok_mod, route)

    rates = await _provider().fetch_rates(RANGE, ["EUR", "USD"])

    assert rates["EUR"] == [] and len(rates["USD"]) == 1


@pytest.mark.asyncio
async def test_bok_transport_failure_of_one_series_does_not_lose_the_others(monkeypatch: pytest.MonkeyPatch):
    def route(request: httpx.Request) -> httpx.Response:
        if _item_of(request) == EUR:
            raise httpx.ConnectError("no route", request=request)
        return _answer(_row(USD, "20261119", "1340.1"))

    _route(monkeypatch, bok_mod, route)

    rates = await _provider().fetch_rates(RANGE, ["EUR", "USD"])

    assert rates["EUR"] == [] and len(rates["USD"]) == 1


@pytest.mark.asyncio
async def test_bok_every_series_failing_with_codes_is_a_service_error_naming_them(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, bok_mod, lambda request: _result("ERROR-999", "boom"))

    with pytest.raises(FXServiceError) as refused:
        await _provider().fetch_rates(RANGE, ["USD", "EUR"])

    assert not isinstance(refused.value, FXRateLimitedError)
    assert "ERROR-999" in str(refused.value)


# ── The key never leaks ──────────────────────────────────────────────────────────


def _refuse_connect(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("no route", request=request)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "answer",
    [
        pytest.param(lambda request: _result("INFO-100", "Invalid activation key."), id="info-100"),
        pytest.param(lambda request: httpx.Response(500, text="Internal error"), id="http-500"),
        pytest.param(_refuse_connect, id="connect-error"),
        pytest.param(lambda request: _result("ERROR-999", "boom"), id="all-failed-code"),
    ],
)
async def test_bok_the_key_never_appears_in_a_raised_error(monkeypatch: pytest.MonkeyPatch, answer):
    _route(monkeypatch, bok_mod, answer)

    with pytest.raises(FXServiceError) as refused:
        await _provider().fetch_rates(RANGE, ["USD", "EUR"])

    assert KEY not in str(refused.value)
    assert KEY not in repr(refused.value)


# ── Catalogue and identity ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bok_catalogue_is_the_items_plus_krw_without_request_or_key(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, bok_mod, lambda request: _result("INFO-200"))

    currencies = await _provider(key=None).get_supported_currencies()

    assert currencies == sorted([*bok_mod.ITEMS, "KRW"])
    assert len(currencies) == 44 and "KRW" in currencies
    assert _provider(key=None).fallback_currencies == currencies
    assert asked == []


def test_bok_identity_and_constants():
    provider = BOKProvider()
    assert (provider.code, provider.base_currency, provider.warning_level) == ("BOK", "KRW", "warning")
    assert provider.docs_url == "/mkdocs/user/fx/providers/bok/"
    assert BOKProvider.MAX_PARALLEL == 3
    assert bok_mod.API_ROOT == ROOT
    assert bok_mod.STAT_CODE == "731Y001"
    assert bok_mod.FIRST_DAY == date(1964, 5, 4)
    assert bok_mod.PAGE_ROWS == 10000


def test_bok_pause_between_series_is_a_third_of_a_second_by_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.undo()
    assert BOKProvider.PAUSE_SECONDS == 0.3


def test_bok_items_table_is_exactly_the_43_currencies():
    assert len(bok_mod.ITEMS) == 43
    assert {code: (item, Decimal(units)) for code, (item, units) in bok_mod.ITEMS.items()} == {c: (i, Decimal(u)) for c, (i, u) in EXPECTED_ITEMS.items()}


def test_bok_declares_one_secret_system_api_key_field():
    fields = {field.key: field for field in BOKProvider.settings_fields}
    assert {key for key in fields if key != "api_key"} <= {f"call_limit_{window}" for window in ("minute", "hour", "day", "week", "month")}
    api_key = fields["api_key"]
    assert (api_key.key, api_key.type, api_key.scope, api_key.secret, api_key.required) == ("api_key", SettingType.STRING, SettingScope.SYSTEM, True, True)
    assert api_key.label_key == "pluginSettings.fx.BOK.label.api_key"
    assert api_key.description_key == "pluginSettings.fx.BOK.description.api_key"
    assert api_key.missing_key == "pluginSettings.fx.BOK.missing.api_key"
    assert BOKProvider().settings.missing == ("api_key",)
