"""BNR FX provider: the National Bank of Romania reference rates, lei per foreign unit (no network, no DB, no server).

Lane 75, wave 2 (plan ``plan-phase02FxCentralBanksOndata2.prompt.md``). Measured on the real feed on 19/11/2026:

- ``nbrfxrates10days.xml`` holds the last 10 business days, newest first; ``files/xml/years/nbrfxrates<year>.xml`` holds
  every business day of one year since 2005. A year that does not exist is answered with HTTP 502 and an nginx page.
- A ``Cube date=...`` holds one ``Rate currency=...`` per currency, the text being lei per ``multiplier`` units (default
  1; 100 for HUF, JPY, KRW...). A rate that is not published is the text ``-``. XAU and XDR are in the files, not served.
- The XML namespace differs between files: ``https://www.bnr.ro/xsd`` in the recent ones, ``http://www.bnr.ro/xsd`` in
  the older year files.

Every answer here is synthetic, written by hand in the feed's shape, never data downloaded from the bank.

Isolation: PURE. ``fetch_rates`` and ``get_supported_currencies`` run whole, their module's ``httpx`` replaced for the
test by the real module whose ``AsyncClient`` answers through an ``httpx.MockTransport`` (``_route``, from
``test_rate_limit_http_providers.py``). The pause between requests is zero, or a recorder, never a real sleep.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

import httpx
import pytest

from backend.app.services.fx.base import FXRateLimitedError, FXServiceError
from backend.app.services.fx_providers.bnr import plugin as bnr_mod
from backend.app.services.fx_providers.bnr.plugin import BNRProvider
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

RECENT_URL = "https://curs.bnr.ro/nbrfxrates10days.xml"
YEAR_URL = "https://curs.bnr.ro/files/xml/years/nbrfxrates{year}.xml"
NS_NEW = "https://www.bnr.ro/xsd"
NS_OLD = "http://www.bnr.ro/xsd"

SHORT_RANGE = (date(2026, 11, 9), date(2026, 11, 19))  # 10 days, inside the 10 business days of the recent file
RANGE_2025 = (date(2025, 1, 1), date(2025, 12, 31))
TWO_YEARS = (date(2025, 12, 29), date(2026, 1, 5))  # 7 days, but across two years

SERVED = [
    "AED", "AUD", "BGN", "BRL", "CAD", "CHF", "CNY", "CZK", "DKK", "EGP", "EUR", "GBP", "HKD", "HRK", "HUF", "IDR", "ILS",
    "INR", "ISK", "JPY", "KRW", "MDL", "MXN", "MYR", "NOK", "NZD", "PHP", "PLN", "RSD", "RUB", "SEK", "SGD", "SKK", "THB",
    "TRY", "UAH", "USD", "ZAR",
]  # fmt: skip


@pytest.fixture(autouse=True)
def _no_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test waits between two requests, unless it records the pause itself."""
    monkeypatch.setattr(BNRProvider, "PAUSE_SECONDS", 0)


def _rate(currency: str, text: str, multiplier: int | None = None) -> str:
    """One ``Rate`` element as the feed writes it."""
    attr = f' multiplier="{multiplier}"' if multiplier is not None else ""
    return f'<Rate currency="{currency}"{attr}>{text}</Rate>'


def _cube(day: str, *rates: str) -> str:
    """One ``Cube`` element for a day."""
    return f'<Cube date="{day}">{"".join(rates)}</Cube>'


def _xml(*cubes: str, ns: str | None = NS_NEW, root: str = "DataSet") -> str:
    """A whole file; ``ns=None`` writes no namespace at all."""
    xmlns = f' xmlns="{ns}"' if ns else ""
    return "".join(
        [
            '<?xml version="1.0" encoding="utf-8"?>',
            f"<{root}{xmlns}>",
            "<Header><Publisher>National Bank of Romania</Publisher><PublishingDate>2026-11-19</PublishingDate>",
            "<MessageType>DR</MessageType></Header>",
            "<Body><Subject>Reference rates</Subject><OrigCurrency>RON</OrigCurrency>",
            *cubes,
            f"</Body></{root}>",
        ]
    )


def _answer(body: str, status: int = 200) -> httpx.Response:
    return httpx.Response(status, headers={"content-type": "application/xml"}, content=body.encode())


def _usd(day: str, text: str = "4.5000") -> str:
    return _cube(day, _rate("USD", text))


# The 10 business days of the recent file, newest first, USD only.
RECENT_DAYS = ["2026-11-19", "2026-11-18", "2026-11-17", "2026-11-16", "2026-11-13", "2026-11-12", "2026-11-11", "2026-11-10", "2026-11-09", "2026-11-06"]  # fmt: skip
RECENT_FILE = _xml(*[_usd(day) for day in RECENT_DAYS])


def _by_url(recent: str | None = None, years: dict[int, str] | None = None):
    """A handler answering each endpoint with its own file; a year not given is the 502 nginx page of the real site."""
    years = years or {}

    def handle(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == RECENT_URL and recent is not None:
            return _answer(recent)
        found = re.fullmatch(r"https://curs\.bnr\.ro/files/xml/years/nbrfxrates(\d{4})\.xml", url)
        if found and int(found.group(1)) in years:
            return _answer(years[int(found.group(1))])
        return httpx.Response(502, headers={"content-type": "text/html"}, text="<html><body>502 Bad Gateway nginx</body></html>")

    return handle


def _urls(asked: list[httpx.Request]) -> list[str]:
    return [str(r.url) for r in asked]


# ── Values and namespaces ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bnr_returns_lei_per_one_unit_dividing_by_the_multiplier(monkeypatch: pytest.MonkeyPatch):
    """«HUF 1.4619 for 100» is 0.014619 lei per forint; a rate with no multiplier stays as written."""
    body = _xml(_cube("2026-11-19", _rate("EUR", "5.0812"), _rate("HUF", "1.4619", 100)), _usd("2026-11-06"))
    _route(monkeypatch, bnr_mod, _by_url(recent=body))

    rates = await BNRProvider().fetch_rates(SHORT_RANGE, ["EUR", "HUF"])

    assert rates["EUR"] == [(date(2026, 11, 19), "EUR", "RON", Decimal("5.0812"))]
    assert rates["HUF"] == [(date(2026, 11, 19), "HUF", "RON", Decimal("0.014619"))]


@pytest.mark.parametrize(
    "namespace",
    [
        pytest.param(NS_NEW, id="https-namespace"),
        pytest.param(NS_OLD, id="http-namespace"),
        pytest.param(None, id="no-namespace"),
    ],
)
@pytest.mark.asyncio
async def test_bnr_reads_the_file_whatever_its_namespace(monkeypatch: pytest.MonkeyPatch, namespace: str | None):
    """The recent files use ``https://www.bnr.ro/xsd``, the old year files ``http://``, a stray file none."""
    _route(monkeypatch, bnr_mod, _by_url(recent=_xml(_usd("2026-11-19"), _usd("2026-11-06"), ns=namespace)))

    rates = await BNRProvider().fetch_rates(SHORT_RANGE, ["USD"])

    assert rates["USD"] == [(date(2026, 11, 19), "USD", "RON", Decimal("4.5000"))]


@pytest.mark.asyncio
async def test_bnr_gold_and_sdr_are_in_the_files_but_never_returned(monkeypatch: pytest.MonkeyPatch):
    """XAU and XDR are keys with ``[]`` when asked, with others or alone, and asked alone they cost no request."""
    body = _xml(_cube("2026-11-19", _rate("USD", "4.5"), _rate("XAU", "520.1234"), _rate("XDR", "6.2")), _usd("2026-11-06"))
    asked = _route(monkeypatch, bnr_mod, _by_url(recent=body))

    mixed = await BNRProvider().fetch_rates(SHORT_RANGE, ["USD", "XAU", "XDR"])
    alone = await BNRProvider().fetch_rates(SHORT_RANGE, ["XAU", "XDR"])

    assert mixed == {"USD": [(date(2026, 11, 19), "USD", "RON", Decimal("4.5"))], "XAU": [], "XDR": []}
    assert alone == {"XAU": [], "XDR": []}
    assert len(asked) == 1


@pytest.mark.parametrize("text", ["-", "", "abc", "0", "0.0000", "-2.5"])
@pytest.mark.asyncio
async def test_bnr_an_unusable_rate_loses_only_that_currency_that_day(monkeypatch: pytest.MonkeyPatch, text: str):
    """A dash, an empty text, a non-number, a zero or a negative rate is skipped; the other rate of the day stays."""
    body = _xml(_cube("2026-11-19", _rate("RUB", text), _rate("USD", "4.5")), _usd("2026-11-06"))
    _route(monkeypatch, bnr_mod, _by_url(recent=body))

    rates = await BNRProvider().fetch_rates(SHORT_RANGE, ["RUB", "USD"])

    assert rates["RUB"] == []
    assert [r[0] for r in rates["USD"]] == [date(2026, 11, 19)]


@pytest.mark.asyncio
async def test_bnr_currencies_not_asked_are_left_out(monkeypatch: pytest.MonkeyPatch):
    body = _xml(_cube("2026-11-19", _rate("EUR", "5.08"), _rate("USD", "4.5")), _usd("2026-11-06"))
    _route(monkeypatch, bnr_mod, _by_url(recent=body))

    rates = await BNRProvider().fetch_rates(SHORT_RANGE, ["USD"])

    assert set(rates) == {"USD"}
    assert [r[1] for r in rates["USD"]] == ["USD"]


@pytest.mark.asyncio
async def test_bnr_cubes_outside_the_range_or_with_a_bad_date_are_skipped(monkeypatch: pytest.MonkeyPatch):
    """A day after the end, a day before the start and an unreadable date lose only their own cube."""
    body = _xml(
        _usd("2026-11-25", "9.9"),
        _usd("not-a-day", "9.8"),
        _usd("2026-11-19", "4.5"),
        _usd("2026-11-10", "4.4"),
        _usd("2026-11-06", "4.3"),
    )
    _route(monkeypatch, bnr_mod, _by_url(recent=body))

    rates = await BNRProvider().fetch_rates((date(2026, 11, 9), date(2026, 11, 20)), ["USD"])

    assert [(r[0], r[3]) for r in rates["USD"]] == [(date(2026, 11, 10), Decimal("4.4")), (date(2026, 11, 19), Decimal("4.5"))]


@pytest.mark.asyncio
async def test_bnr_cubes_newest_first_come_out_ascending(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, bnr_mod, _by_url(recent=RECENT_FILE))

    rates = await BNRProvider().fetch_rates(SHORT_RANGE, ["USD"])

    days = [r[0] for r in rates["USD"]]
    assert days == sorted(days) and len(days) == 9


# ── Which source ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bnr_a_short_range_reached_by_the_recent_file_costs_one_request(monkeypatch: pytest.MonkeyPatch):
    """The earliest cube (2026-11-06) is before the start: only ``RECENT_URL``, no year file."""
    asked = _route(monkeypatch, bnr_mod, _by_url(recent=RECENT_FILE))

    await BNRProvider().fetch_rates(SHORT_RANGE, ["USD"])

    assert _urls(asked) == [RECENT_URL]
    assert asked[0].method == "GET"


@pytest.mark.asyncio
async def test_bnr_a_recent_file_that_does_not_reach_back_is_followed_by_the_year_file(monkeypatch: pytest.MonkeyPatch):
    """Range of 14 days from 2026-11-05 while the recent file starts on 11-06: recent, then the year 2026."""
    year_file = _xml(_usd("2026-11-05", "4.1"), _usd("2026-11-19", "4.5"))
    asked = _route(monkeypatch, bnr_mod, _by_url(recent=RECENT_FILE, years={2026: year_file}))

    rates = await BNRProvider().fetch_rates((date(2026, 11, 5), date(2026, 11, 19)), ["USD"])

    assert _urls(asked) == [RECENT_URL, YEAR_URL.format(year=2026)]
    assert [(r[0], r[3]) for r in rates["USD"]] == [(date(2026, 11, 5), Decimal("4.1")), (date(2026, 11, 19), Decimal("4.5"))]


@pytest.mark.asyncio
async def test_bnr_a_recent_file_with_no_cube_falls_back_to_the_year_file(monkeypatch: pytest.MonkeyPatch):
    """No cube to prove the reach: the year file is asked."""
    asked = _route(monkeypatch, bnr_mod, _by_url(recent=_xml(), years={2026: _xml(_usd("2026-11-19"))}))

    rates = await BNRProvider().fetch_rates(SHORT_RANGE, ["USD"])

    assert _urls(asked) == [RECENT_URL, YEAR_URL.format(year=2026)]
    assert len(rates["USD"]) == 1


@pytest.mark.parametrize(
    ("span", "expected"),
    [
        pytest.param((date(2026, 11, 5), date(2026, 11, 19)), True, id="14-days-asks-recent"),
        pytest.param((date(2026, 11, 4), date(2026, 11, 19)), False, id="15-days-skips-recent"),
    ],
)
@pytest.mark.asyncio
async def test_bnr_the_recent_file_is_tried_up_to_fourteen_days(monkeypatch: pytest.MonkeyPatch, span, expected: bool):
    """``RECENT_SPAN_DAYS`` is 14: a range of 15 days goes straight to the year file."""
    asked = _route(monkeypatch, bnr_mod, _by_url(recent=RECENT_FILE, years={2026: _xml(_usd("2026-11-19"))}))

    await BNRProvider().fetch_rates(span, ["USD"])

    assert (RECENT_URL in _urls(asked)) is expected


@pytest.mark.asyncio
async def test_bnr_a_long_range_asks_one_year_file_per_year_oldest_first(monkeypatch: pytest.MonkeyPatch):
    """2024-01-01 → 2026-01-01: 2024, 2025, 2026, never the recent file."""
    asked = _route(monkeypatch, bnr_mod, _by_url(years={2024: _xml(), 2025: _xml(), 2026: _xml()}))

    await BNRProvider().fetch_rates((date(2024, 1, 1), date(2026, 1, 1)), ["USD"])

    assert _urls(asked) == [YEAR_URL.format(year=y) for y in (2024, 2025, 2026)]


@pytest.mark.asyncio
async def test_bnr_two_years_merge_into_one_ascending_series(monkeypatch: pytest.MonkeyPatch):
    """The days of each file land in the range; a year file need not be ordered."""
    years = {
        2025: _xml(_usd("2025-12-30", "4.6"), _usd("2025-12-29", "4.5"), _usd("2025-12-01", "4.0")),
        2026: _xml(_usd("2026-01-06", "4.9"), _usd("2026-01-02", "4.7")),
    }
    asked = _route(monkeypatch, bnr_mod, _by_url(recent=RECENT_FILE, years=years))

    rates = await BNRProvider().fetch_rates(TWO_YEARS, ["USD"])

    assert _urls(asked) == [RECENT_URL, YEAR_URL.format(year=2025), YEAR_URL.format(year=2026)]
    assert [(r[0], r[3]) for r in rates["USD"]] == [
        (date(2025, 12, 29), Decimal("4.5")),
        (date(2025, 12, 30), Decimal("4.6")),
        (date(2026, 1, 2), Decimal("4.7")),
    ]


@pytest.mark.asyncio
async def test_bnr_min_and_an_earlier_start_begin_at_2005(monkeypatch: pytest.MonkeyPatch):
    """``"min"`` and any earlier start are raised to 2005-01-01: the first file is 2005."""
    asked = _route(monkeypatch, bnr_mod, _by_url(years={2005: _xml(), 2006: _xml()}))

    await BNRProvider().fetch_rates(("min", date(2006, 12, 31)), ["USD"])
    await BNRProvider().fetch_rates((date(1980, 1, 1), date(2006, 12, 31)), ["USD"])

    assert _urls(asked) == [YEAR_URL.format(year=y) for y in (2005, 2006, 2005, 2006)]


@pytest.mark.asyncio
async def test_bnr_a_day_twice_in_a_year_file_with_different_rates_is_dropped_and_equal_ones_kept_once(monkeypatch: pytest.MonkeyPatch):
    """In one year file 11-19 disagrees (dropped), 11-18 agrees (once), 11-05 is single."""
    year_file = _xml(_usd("2026-11-19", "4.5"), _usd("2026-11-19", "4.6"), _usd("2026-11-18", "4.4"), _usd("2026-11-18", "4.4"), _usd("2026-11-05", "4.2"))
    _route(monkeypatch, bnr_mod, _by_url(recent=RECENT_FILE, years={2026: year_file}))

    rates = await BNRProvider().fetch_rates((date(2026, 11, 5), date(2026, 11, 19)), ["USD"])

    assert [(r[0], r[3]) for r in rates["USD"]] == [(date(2026, 11, 5), Decimal("4.2")), (date(2026, 11, 18), Decimal("4.4"))]


@pytest.mark.asyncio
async def test_bnr_year_files_replace_a_recent_file_that_does_not_reach_back(monkeypatch: pytest.MonkeyPatch):
    """The recent rows are discarded: a day only in the recent file is not returned, a day on which they disagree takes the year's."""
    recent = _xml(_usd("2026-11-19", "4.5"), _usd("2026-11-18", "4.4"), _usd("2026-11-06", "4.3"))
    year_file = _xml(_usd("2026-11-19", "4.6"), _usd("2026-11-05", "4.2"))
    _route(monkeypatch, bnr_mod, _by_url(recent=recent, years={2026: year_file}))

    rates = await BNRProvider().fetch_rates((date(2026, 11, 5), date(2026, 11, 19)), ["USD"])

    assert [(r[0], r[3]) for r in rates["USD"]] == [(date(2026, 11, 5), Decimal("4.2")), (date(2026, 11, 19), Decimal("4.6"))]


@pytest.mark.asyncio
async def test_bnr_a_cube_repeating_a_day_with_the_same_rate_is_kept_once(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, bnr_mod, _by_url(years={2025: _xml(_usd("2025-03-03"), _usd("2025-03-03"))}))

    rates = await BNRProvider().fetch_rates(RANGE_2025, ["USD"])

    assert rates["USD"] == [(date(2025, 3, 3), "USD", "RON", Decimal("4.5000"))]


# ── Range and currencies ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bnr_every_asked_currency_but_ron_is_a_key(monkeypatch: pytest.MonkeyPatch):
    """RON is no key; a served currency absent from the files (BRL) is a key with ``[]``."""
    _route(monkeypatch, bnr_mod, _by_url(recent=RECENT_FILE))

    rates = await BNRProvider().fetch_rates(SHORT_RANGE, ["RON", "BRL", "USD"])

    assert set(rates) == {"BRL", "USD"}
    assert rates["BRL"] == []


@pytest.mark.parametrize(
    ("span", "currencies", "expected"),
    [
        pytest.param(SHORT_RANGE, ["RON"], {}, id="ron-only"),
        pytest.param(SHORT_RANGE, ["XYZ"], {"XYZ": []}, id="unserved-only"),
        pytest.param((date(2026, 11, 19), date(2026, 11, 9)), ["USD"], {"USD": []}, id="inverted-range"),
        pytest.param((date(2004, 1, 1), date(2004, 12, 31)), ["USD"], {"USD": []}, id="end-before-first-day"),
    ],
)
@pytest.mark.asyncio
async def test_bnr_nothing_servable_asks_nothing(monkeypatch: pytest.MonkeyPatch, span, currencies, expected):
    asked = _route(monkeypatch, bnr_mod, _by_url(recent=RECENT_FILE, years={2004: _xml()}))

    assert await BNRProvider().fetch_rates(span, currencies) == expected
    assert asked == []


@pytest.mark.asyncio
async def test_bnr_other_base_currency_is_refused(monkeypatch: pytest.MonkeyPatch):
    """``base_currency`` EUR raises ``ValueError``; None and RON are fine."""
    _route(monkeypatch, bnr_mod, _by_url(recent=RECENT_FILE))

    with pytest.raises(ValueError):
        await BNRProvider().fetch_rates(SHORT_RANGE, ["USD"], base_currency="EUR")

    assert len((await BNRProvider().fetch_rates(SHORT_RANGE, ["USD"], base_currency="RON"))["USD"]) == 9
    assert len((await BNRProvider().fetch_rates(SHORT_RANGE, ["USD"], base_currency=None))["USD"]) == 9


# ── Pause ────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bnr_pauses_before_every_request_but_the_first(monkeypatch: pytest.MonkeyPatch):
    """The recent file plus two year files: three requests, two pauses of ``PAUSE_SECONDS``."""
    monkeypatch.setattr(BNRProvider, "PAUSE_SECONDS", 0.3)
    slept: list[float] = []

    async def record(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(bnr_mod.asyncio, "sleep", record)
    asked = _route(monkeypatch, bnr_mod, _by_url(recent=RECENT_FILE, years={2025: _xml(), 2026: _xml()}))

    await BNRProvider().fetch_rates((date(2025, 12, 31), date(2026, 1, 3)), ["USD"])

    assert _urls(asked) == [RECENT_URL, YEAR_URL.format(year=2025), YEAR_URL.format(year=2026)]
    assert slept == [0.3, 0.3]


@pytest.mark.asyncio
async def test_bnr_one_request_needs_no_pause(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(BNRProvider, "PAUSE_SECONDS", 0.3)
    slept: list[float] = []

    async def record(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(bnr_mod.asyncio, "sleep", record)
    _route(monkeypatch, bnr_mod, _by_url(recent=RECENT_FILE))

    await BNRProvider().fetch_rates(SHORT_RANGE, ["USD"])

    assert slept == []


# ── Errors ───────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bnr_a_missing_year_file_is_a_service_error_naming_the_year(monkeypatch: pytest.MonkeyPatch):
    """The real site answers 502 for a year that does not exist; the message says which year."""
    _route(monkeypatch, bnr_mod, _by_url(years={2025: _xml()}))

    with pytest.raises(FXServiceError) as refused:
        await BNRProvider().fetch_rates((date(2025, 1, 1), date(2026, 12, 31)), ["USD"])

    assert "2026" in str(refused.value)
    assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.parametrize("status", [500, 502])
@pytest.mark.asyncio
async def test_bnr_http_failure_on_the_recent_file_is_a_service_error(monkeypatch: pytest.MonkeyPatch, status: int):
    _route(monkeypatch, bnr_mod, lambda request: httpx.Response(status, text="down"))

    with pytest.raises(FXServiceError) as refused:
        await BNRProvider().fetch_rates(SHORT_RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.asyncio
async def test_bnr_unreachable_is_a_service_error(monkeypatch: pytest.MonkeyPatch):
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    _route(monkeypatch, bnr_mod, refuse)

    for span in (SHORT_RANGE, RANGE_2025):
        with pytest.raises(FXServiceError):
            await BNRProvider().fetch_rates(span, ["USD"])


@pytest.mark.asyncio
async def test_bnr_too_many_requests_is_a_rate_limit_on_any_request(monkeypatch: pytest.MonkeyPatch):
    """HTTP 429 on the recent file, then on the second year file: ``FXRateLimitedError`` both times."""
    _route(monkeypatch, bnr_mod, lambda request: httpx.Response(429))
    with pytest.raises(FXRateLimitedError):
        await BNRProvider().fetch_rates(SHORT_RANGE, ["USD"])

    def answer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429) if str(request.url).endswith("2026.xml") else _answer(_xml())

    _route(monkeypatch, bnr_mod, answer)
    with pytest.raises(FXRateLimitedError):
        await BNRProvider().fetch_rates(TWO_YEARS, ["USD"])


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("<!DOCTYPE html><html><body>Maintenance</body></html>", id="html-page"),
        pytest.param("not xml at all", id="plain-text"),
        pytest.param("", id="empty-body"),
        pytest.param(_xml(_usd("2026-11-19"), root="Other"), id="other-root"),
    ],
)
@pytest.mark.asyncio
async def test_bnr_a_body_that_is_not_the_feed_is_a_service_error(monkeypatch: pytest.MonkeyPatch, body: str):
    """An HTML page, text, an empty body or XML whose root is not ``DataSet``: ``FXServiceError``."""
    _route(monkeypatch, bnr_mod, lambda request: _answer(body))

    with pytest.raises(FXServiceError) as refused:
        await BNRProvider().fetch_rates(SHORT_RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


# ── Catalogue and identity ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bnr_catalogue_is_the_served_currencies_plus_ron_without_a_request(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, bnr_mod, _by_url(recent=RECENT_FILE))

    currencies = await BNRProvider().get_supported_currencies()

    assert currencies == sorted([*SERVED, "RON"])
    assert "XAU" not in currencies and "XDR" not in currencies
    assert BNRProvider().fallback_currencies == currencies
    assert asked == []


def test_bnr_identity_urls_and_constants():
    provider = BNRProvider()
    assert (provider.code, provider.base_currency, provider.warning_level) == ("BNR", "RON", "info")
    assert provider.docs_url == "/mkdocs/user/fx/providers/bnr/"
    assert bnr_mod.RECENT_URL == RECENT_URL
    assert bnr_mod.YEAR_URL.format(year=2024) == YEAR_URL.format(year=2024)
    assert bnr_mod.FIRST_DAY == date(2005, 1, 1)
    assert bnr_mod.RECENT_SPAN_DAYS == 14
    assert sorted(bnr_mod.CURRENCIES) == SERVED and len(bnr_mod.CURRENCIES) == 38


def test_bnr_pause_between_requests_is_a_third_of_a_second_by_default(monkeypatch: pytest.MonkeyPatch):
    """The class default, seen with the fixture's zero undone."""
    monkeypatch.undo()
    assert BNRProvider.PAUSE_SECONDS == 0.3
