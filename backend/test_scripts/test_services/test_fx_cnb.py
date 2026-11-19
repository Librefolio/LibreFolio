"""CNB FX provider: its yearly text files, the CZK-per-unit direction, its columns that change inside a year and what it refuses (no network, no DB, no server).

Lane 75, wave 2, lot L23 (plan ``plan-phase02FxCentralBanksOndata2.prompt.md``). Measured on the real feed on 19/11/2026:

- ``year.txt?year=YYYY`` is one file per year since 1991; a row is ``dd.mm.yyyy|v1|v2|…`` under a header
  ``Date|1 AUD|100 HUF|1000 IDR|1 USD``: each value is CZK per ``Amount`` units of the currency in its column.
- The columns change between blocks of one file (1993 has three headers: currencies entered and left mid-year).
- ``year=1990`` is answered with the current year's file, not with an error.
- ``daily.txt`` without a date is the last fixing (30 currencies on 19/11/2026, XDR among them): a first line with the
  date and the number, a header ``Country|Currency|Amount|Code|Rate``, then one row per currency.
- Only fixing days are listed (no weekends, no holidays).

Every answer here is synthetic, written by hand in the feed's shape, never data downloaded from the bank.

Isolation: PURE. ``fetch_rates`` and ``get_supported_currencies`` run whole, their module's ``httpx`` replaced for the
test by the real module whose ``AsyncClient`` answers through an ``httpx.MockTransport`` (``_route``, from
``test_rate_limit_http_providers.py``). The pause between years is zero, or a recorder, never a real sleep.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import httpx
import pytest

from backend.app.services.fx.base import FXRateLimitedError, FXServiceError
from backend.app.services.fx_providers.cnb import plugin as cnb_mod
from backend.app.services.fx_providers.cnb.plugin import CNBProvider
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

BASE_URL = "https://www.cnb.cz/en/financial-markets/foreign-exchange-market/central-bank-exchange-rate-fixing/central-bank-exchange-rate-fixing/"
RANGE_2025 = (date(2025, 1, 1), date(2025, 12, 31))

FILE_2025 = "".join(
    [
        "Date|1 AUD|100 HUF|1000 IDR|1 USD\n",
        "02.01.2025|15.145|6.097|1.507|24.398\n",
        "03.01.2025|15.195|6.064|1.510|24.427\n",
    ]
)

DAILY = "".join(
    [
        "19 Nov 2026 #222\n",
        "Country|Currency|Amount|Code|Rate\n",
        "Australia|dollar|1|AUD|14.909\n",
        "Hungary|forint|100|HUF|6.610\n",
        "International Monetary Fund|SDR|1|XDR|30.100\n",
        "USA|dollar|1|USD|22.219\n",
    ]
)


@pytest.fixture(autouse=True)
def _no_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test waits between two years, unless it records the pause itself."""
    monkeypatch.setattr(CNBProvider, "PAUSE_SECONDS", 0)


def _text(body: str, status: int = 200) -> httpx.Response:
    return httpx.Response(status, headers={"content-type": "text/plain"}, text=body)


def _year_of(request: httpx.Request) -> int:
    return int(request.url.params["year"])


# ── Direction, request and days ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cnb_returns_czk_per_one_unit_never_inverted(monkeypatch: pytest.MonkeyPatch):
    """«100 HUF = 6.097 CZK» is 0.06097 per forint, «1000 IDR = 1.507 CZK» is 0.001507, «1 USD = 24.398 CZK» stays."""
    _route(monkeypatch, cnb_mod, lambda request: _text(FILE_2025))

    rates = await CNBProvider().fetch_rates(RANGE_2025, ["USD", "HUF", "IDR"])

    assert rates["USD"][0] == (date(2025, 1, 2), "USD", "CZK", Decimal("24.398"))
    assert rates["HUF"][0] == (date(2025, 1, 2), "HUF", "CZK", Decimal("0.06097"))
    assert rates["IDR"][0] == (date(2025, 1, 2), "IDR", "CZK", Decimal("0.001507"))
    assert [row[0] for row in rates["USD"]] == [date(2025, 1, 2), date(2025, 1, 3)]


@pytest.mark.asyncio
async def test_cnb_asks_one_year_file_with_the_year_query(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, cnb_mod, lambda request: _text(FILE_2025))

    await CNBProvider().fetch_rates(RANGE_2025, ["USD"])

    assert len(asked) == 1
    assert str(asked[0].url).split("?")[0] == f"{BASE_URL}year.txt"
    assert asked[0].url.params["year"] == "2025"


@pytest.mark.asyncio
async def test_cnb_asks_one_file_per_year_in_ascending_order(monkeypatch: pytest.MonkeyPatch):
    """2025-12-29 → 2026-01-05 asks 2025 then 2026, and the days of each file land in the right range."""
    files = {
        2025: "Date|1 USD\n29.12.2025|24.000\n30.12.2025|24.100\n",
        2026: "Date|1 USD\n02.01.2026|24.200\n06.01.2026|24.300\n",
    }
    asked = _route(monkeypatch, cnb_mod, lambda request: _text(files[_year_of(request)]))

    rates = await CNBProvider().fetch_rates((date(2025, 12, 29), date(2026, 1, 5)), ["USD"])

    assert [_year_of(r) for r in asked] == [2025, 2026]
    assert [row[0] for row in rates["USD"]] == [date(2025, 12, 29), date(2025, 12, 30), date(2026, 1, 2)]


@pytest.mark.asyncio
async def test_cnb_reads_blocks_with_different_columns_in_one_year(monkeypatch: pytest.MonkeyPatch):
    """A currency absent from a block has no value in it; the others keep reading with their own column positions."""
    body = "".join(
        [
            "Date|1 AUD|100 HUF|1 USD\n",
            "02.01.2025|15.145|6.097|24.398\n",
            "03.01.2025|15.195|6.064|24.427\n",
            "Date|1 AUD|1 USD|1 XDR\n",
            "06.01.2025|15.195|24.500|31.800\n",
        ]
    )
    _route(monkeypatch, cnb_mod, lambda request: _text(body))

    rates = await CNBProvider().fetch_rates(RANGE_2025, ["USD", "HUF", "XDR"])

    assert [(row[0], row[3]) for row in rates["USD"]] == [
        (date(2025, 1, 2), Decimal("24.398")),
        (date(2025, 1, 3), Decimal("24.427")),
        (date(2025, 1, 6), Decimal("24.500")),
    ]
    assert [row[0] for row in rates["HUF"]] == [date(2025, 1, 2), date(2025, 1, 3)]
    assert rates["XDR"] == [(date(2025, 1, 6), "XDR", "CZK", Decimal("31.800"))]


@pytest.mark.asyncio
async def test_cnb_returns_only_fixing_days_inside_the_range(monkeypatch: pytest.MonkeyPatch):
    """No weekend filling; a fixing before the start or after the end is skipped."""
    body = "Date|1 USD\n02.01.2025|24.0\n03.01.2025|24.1\n06.01.2025|24.2\n"
    _route(monkeypatch, cnb_mod, lambda request: _text(body))

    rates = await CNBProvider().fetch_rates((date(2025, 1, 3), date(2025, 1, 5)), ["USD"])

    assert rates["USD"] == [(date(2025, 1, 3), "USD", "CZK", Decimal("24.1"))]


@pytest.mark.asyncio
async def test_cnb_skips_a_row_of_another_year_than_the_asked_one(monkeypatch: pytest.MonkeyPatch):
    """The CNB answers an unknown year with the current year's file: asking 2025 and getting 2026 yields nothing."""
    body = "Date|1 USD\n02.01.2026|24.0\n05.01.2026|24.1\n"
    asked = _route(monkeypatch, cnb_mod, lambda request: _text(body))

    rates = await CNBProvider().fetch_rates(RANGE_2025, ["USD"])

    assert rates == {"USD": []}
    assert len(asked) == 1


@pytest.mark.asyncio
async def test_cnb_asks_from_1991_for_min_and_for_an_earlier_start(monkeypatch: pytest.MonkeyPatch):
    """``"min"`` and any earlier start begin at 1991-01-01: the first file asked is 1991."""
    asked = _route(monkeypatch, cnb_mod, lambda request: _text("Date|1 USD\n"))

    await CNBProvider().fetch_rates(("min", date(1992, 12, 31)), ["USD"])
    await CNBProvider().fetch_rates((date(1980, 1, 1), date(1992, 12, 31)), ["USD"])

    assert [_year_of(r) for r in asked] == [1991, 1992, 1991, 1992]


@pytest.mark.asyncio
async def test_cnb_every_asked_currency_is_a_key_and_czk_is_none(monkeypatch: pytest.MonkeyPatch):
    """The base currency is no key; a currency absent from the files maps to ``[]``."""
    _route(monkeypatch, cnb_mod, lambda request: _text(FILE_2025))

    rates = await CNBProvider().fetch_rates(RANGE_2025, ["USD", "CZK", "ZAR"])

    assert set(rates) == {"USD", "ZAR"}
    assert rates["ZAR"] == [] and len(rates["USD"]) == 2


@pytest.mark.asyncio
async def test_cnb_asks_nothing_without_wanted_currencies_or_with_an_inverted_range(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, cnb_mod, lambda request: _text(FILE_2025))

    assert await CNBProvider().fetch_rates(RANGE_2025, ["CZK"]) == {}
    assert await CNBProvider().fetch_rates((date(2025, 12, 31), date(2025, 1, 1)), ["USD"]) == {"USD": []}
    assert asked == []


@pytest.mark.asyncio
async def test_cnb_other_base_currency_is_refused(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, cnb_mod, lambda request: _text(FILE_2025))

    with pytest.raises(ValueError):
        await CNBProvider().fetch_rates(RANGE_2025, ["USD"], base_currency="EUR")

    assert len((await CNBProvider().fetch_rates(RANGE_2025, ["USD"], base_currency="CZK"))["USD"]) == 2
    assert len(asked) == 1


# ── What it skips ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cnb_unreadable_cell_loses_only_that_currency_that_day(monkeypatch: pytest.MonkeyPatch):
    """An empty cell, a non-number, a zero and a negative drop one currency on one day; the other columns stay."""
    body = "".join(
        [
            "Date|1 AUD|1 USD\n",
            "02.01.2025||24.0\n",
            "03.01.2025|abc|24.1\n",
            "06.01.2025|0|24.2\n",
            "07.01.2025|-3.5|24.3\n",
            "08.01.2025|15.0|24.4\n",
        ]
    )
    _route(monkeypatch, cnb_mod, lambda request: _text(body))

    rates = await CNBProvider().fetch_rates(RANGE_2025, ["AUD", "USD"])

    assert rates["AUD"] == [(date(2025, 1, 8), "AUD", "CZK", Decimal("15.0"))]
    assert [row[0] for row in rates["USD"]] == [date(2025, 1, d) for d in (2, 3, 6, 7, 8)]


@pytest.mark.asyncio
async def test_cnb_skips_a_malformed_date_line(monkeypatch: pytest.MonkeyPatch):
    body = "Date|1 USD\nnot-a-date|24.0\n31.02.2025|24.1\n03.01.2025|24.2\n"
    _route(monkeypatch, cnb_mod, lambda request: _text(body))

    rates = await CNBProvider().fetch_rates(RANGE_2025, ["USD"])

    assert rates["USD"] == [(date(2025, 1, 3), "USD", "CZK", Decimal("24.2"))]


# ── Pause between years ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cnb_pauses_between_two_years_but_not_before_the_first(monkeypatch: pytest.MonkeyPatch):
    """Three years: two pauses of ``PAUSE_SECONDS`` (0.3), none before the first request."""
    monkeypatch.setattr(CNBProvider, "PAUSE_SECONDS", 0.3)
    slept: list[float] = []

    async def record(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(cnb_mod.asyncio, "sleep", record)
    asked = _route(monkeypatch, cnb_mod, lambda request: _text("Date|1 USD\n"))

    await CNBProvider().fetch_rates((date(2024, 1, 1), date(2026, 1, 1)), ["USD"])

    assert len(asked) == 3
    assert slept == [0.3, 0.3]


@pytest.mark.asyncio
async def test_cnb_one_year_needs_no_pause(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(CNBProvider, "PAUSE_SECONDS", 0.3)
    slept: list[float] = []

    async def record(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(cnb_mod.asyncio, "sleep", record)
    _route(monkeypatch, cnb_mod, lambda request: _text(FILE_2025))

    await CNBProvider().fetch_rates(RANGE_2025, ["USD"])

    assert slept == []


# ── Errors ───────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cnb_too_many_requests_is_a_rate_limit_and_stops_the_years(monkeypatch: pytest.MonkeyPatch):
    """HTTP 429 on 2025 raises ``FXRateLimitedError``; 2026 is never asked."""

    def answer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429) if _year_of(request) == 2025 else _text("Date|1 USD\n")

    asked = _route(monkeypatch, cnb_mod, answer)

    with pytest.raises(FXRateLimitedError):
        await CNBProvider().fetch_rates((date(2024, 1, 1), date(2026, 1, 1)), ["USD"])

    assert [_year_of(r) for r in asked] == [2024, 2025]


@pytest.mark.asyncio
async def test_cnb_server_error_on_a_later_year_fails_the_whole_call(monkeypatch: pytest.MonkeyPatch):
    """A 500 on the second year raises ``FXServiceError``: no partial result comes back."""

    def answer(request: httpx.Request) -> httpx.Response:
        if _year_of(request) == 2026:
            return _text("Internal error", status=500)
        return _text("Date|1 USD\n02.01.2025|24.0\n")

    _route(monkeypatch, cnb_mod, answer)

    with pytest.raises(FXServiceError) as refused:
        await CNBProvider().fetch_rates((date(2025, 1, 1), date(2026, 12, 31)), ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


_NOT_THE_FILE = [
    pytest.param("<!DOCTYPE html>\n<html><head><title>CNB</title></head></html>", id="html-page"),
    pytest.param("Error: year out of range\n", id="error-text"),
    pytest.param("\n\n19 Nov 2026 #222\nCountry|Currency|Amount|Code|Rate\n", id="daily-file"),
]


@pytest.mark.parametrize("body", _NOT_THE_FILE)
@pytest.mark.asyncio
async def test_cnb_refuses_an_answer_that_is_not_a_year_file(monkeypatch: pytest.MonkeyPatch, body: str):
    """The first non-empty line must start with ``Date|``."""
    _route(monkeypatch, cnb_mod, lambda request: _text(body))

    with pytest.raises(FXServiceError):
        await CNBProvider().fetch_rates(RANGE_2025, ["USD"])


@pytest.mark.asyncio
async def test_cnb_transport_failure_is_a_service_error(monkeypatch: pytest.MonkeyPatch):
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    _route(monkeypatch, cnb_mod, refuse)

    with pytest.raises(FXServiceError):
        await CNBProvider().fetch_rates(RANGE_2025, ["USD"])


# ── Catalogue ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cnb_catalogue_is_the_codes_of_the_daily_file_plus_czk(monkeypatch: pytest.MonkeyPatch):
    """One GET of ``daily.txt`` with no query; the codes of its rows and CZK, sorted."""
    asked = _route(monkeypatch, cnb_mod, lambda request: _text(DAILY))

    currencies = await CNBProvider().get_supported_currencies()

    assert currencies == ["AUD", "CZK", "HUF", "USD", "XDR"]
    assert len(asked) == 1
    assert str(asked[0].url) == f"{BASE_URL}daily.txt"


_BAD_DAILY = [
    pytest.param("19 Nov 2026 #222\nCountry|Currency|Code|Rate\nUSA|dollar|USD|22.2\n", id="other-header"),
    pytest.param("19 Nov 2026 #222\nCountry|Currency|Amount|Code|Rate\n", id="no-row"),
    pytest.param("<!DOCTYPE html>\n<html></html>\n", id="html-page"),
]


@pytest.mark.parametrize("body", _BAD_DAILY)
@pytest.mark.asyncio
async def test_cnb_catalogue_refuses_a_daily_file_of_another_shape(monkeypatch: pytest.MonkeyPatch, body: str):
    _route(monkeypatch, cnb_mod, lambda request: _text(body))

    with pytest.raises(FXServiceError):
        await CNBProvider().get_supported_currencies()


# ── Identity ─────────────────────────────────────────────────────────────────────


def test_cnb_identity_urls_and_fallback_catalogue():
    provider = CNBProvider()
    assert (provider.code, provider.base_currency, provider.warning_level) == ("CNB", "CZK", "info")
    assert provider.docs_url == "/mkdocs/user/fx/providers/cnb/"
    assert CNBProvider.YEAR_URL == f"{BASE_URL}year.txt"
    assert CNBProvider.DAILY_URL == f"{BASE_URL}daily.txt"
    assert CNBProvider.FIRST_DAY == date(1991, 1, 1)
    assert provider.fallback_currencies == [
        "AUD", "BRL", "CAD", "CHF", "CNY", "CZK", "DKK", "EUR", "GBP", "HKD", "HUF", "IDR", "ILS", "INR", "ISK", "JPY",
        "KRW", "MXN", "MYR", "NOK", "NZD", "PHP", "PLN", "RON", "SEK", "SGD", "THB", "TRY", "USD", "XDR", "ZAR",
    ]  # fmt: skip


def test_cnb_pause_between_years_is_a_third_of_a_second_by_default(monkeypatch: pytest.MonkeyPatch):
    """The class default, seen with the fixture's zero undone."""
    monkeypatch.undo()
    assert CNBProvider.PAUSE_SECONDS == 0.3
