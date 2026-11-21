"""CBN FX provider: the Central Bank of Nigeria exchange rates, naira per foreign unit (no network, no DB, no server).

Lane 75, wave 2, lot L30 (plan ``plan-phase02FxCentralBanksOndata2.prompt.md``). Measured on the real feed on 19/11/2026:

- ``GetAllExchangeRates`` answers the whole history: 62 696 rows from 2001-12-10, ~8 MB, ~4 s, behind Cloudflare.
  ``GetAllExchangeRatesGRAPH`` answers about the last month: 240 rows, 23/10 to 18/11, ~32 KB. Neither has a date
  filter, so the plugin filters the asked range itself.
- The answer is a JSON list, newest first; each row has ``currency``, ``ratedate``, ``buyingrate``, ``centralrate`` and
  ``sellingrate`` (numbers as text). The plugin reads the central rate.
- Currency names carry trailing spaces or tabs and variants (POUND/POUNDS STERLING, DANISH KRONA/KRONER, JAPANESE
  YEN), the SDR (named SDR, served as XDR) and noise (WAUA, NAIRA, POESO).
- 97 duplicate day+currency keys, 64 of them with different central rates (e.g. JPY 2017-10-09: 2.7072 and 46.0795).
- No terms of use found; the endpoint is undocumented (decision D10 c of the lane).

Every answer here is synthetic, written by hand in the feed's shape, never data downloaded from the CBN.

Isolation: PURE. ``fetch_rates`` and ``get_supported_currencies`` run whole, their module's ``httpx`` replaced for the
test by the real module whose ``AsyncClient`` answers through an ``httpx.MockTransport`` (``_route``, from
``test_rate_limit_http_providers.py``). No real sleep.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import httpx
import pytest

from backend.app.services.fx.base import FXRateLimitedError, FXServiceError
from backend.app.services.fx_providers.cbn import plugin as cbn_mod
from backend.app.services.fx_providers.cbn.plugin import CBNProvider
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

ALL_URL = "https://www.cbn.gov.ng/api/GetAllExchangeRates"
RECENT_URL = "https://www.cbn.gov.ng/api/GetAllExchangeRatesGRAPH"
RECENT_RANGE = (date(2026, 11, 5), date(2026, 11, 18))  # 14 days, inside the last month
OLD_RANGE = (date(2015, 6, 1), date(2015, 6, 15))  # 14 days, far back
LONG_RANGE = (date(2026, 9, 19), date(2026, 11, 18))  # 60 days


def _row(currency: str, day: str, central: str, buying: str | None = None, selling: str | None = None) -> dict:
    """One row as the feed writes it; the buying and selling rates differ from the central one on purpose."""
    try:
        central_value = Decimal(central)
        default_buying, default_selling = str(central_value - 1), str(central_value + 1)
    except InvalidOperation:  # a central rate that is no number: the other two are written as it is
        default_buying = default_selling = central
    return {
        "id": 1,
        "currency": currency,
        "ratedate": day,
        "buyingrate": buying if buying is not None else default_buying,
        "centralrate": central,
        "sellingrate": selling if selling is not None else default_selling,
    }


def _answer(rows: object, status: int = 200) -> httpx.Response:
    """A JSON body as the endpoint sends it."""
    return httpx.Response(status, headers={"content-type": "application/json"}, content=json.dumps(rows).encode())


def _by_url(recent: object = None, everything: object = None):
    """A handler that answers each endpoint with its own rows (404 for an endpoint left as None).

    A non-empty recent answer gets one more row, a WAUA (a name the plugin discards) on 2026-10-23: the real recent feed
    reaches back about a month, so a short range of November is served by it alone.
    """
    if isinstance(recent, list) and recent:
        recent = [*recent, _row("WAUA", "2026-10-23", "2000.0000")]

    def handle(request: httpx.Request) -> httpx.Response:
        path = f"{request.url.scheme}://{request.url.host}{request.url.path}"
        if path == RECENT_URL and recent is not None:
            return _answer(recent)
        if path == ALL_URL and everything is not None:
            return _answer(everything)
        return httpx.Response(404)

    return handle


def _urls(asked: list[httpx.Request]) -> list[str]:
    """The asked URLs without their query string, in order."""
    return [f"{r.url.scheme}://{r.url.host}{r.url.path}" for r in asked]


# The last month, newest first: 2026-11-18 back to 2026-10-23.
RECENT = [_row("US DOLLAR", (date(2026, 11, 18) - timedelta(days=i)).isoformat(), "1353.4741") for i in range(27)]
USD_DAY = [_row("US DOLLAR", "2026-11-18", "1353.4741", buying="1352.9741", selling="1353.9741")]


# ── Values and mapping ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cbn_central_rate_of_usd_is_naira_per_dollar(monkeypatch: pytest.MonkeyPatch):
    """The central rate is used, never the buying or the selling one: 1 USD = 1353.4741 NGN."""
    _route(monkeypatch, cbn_mod, _by_url(recent=USD_DAY))

    rates = await CBNProvider().fetch_rates(RECENT_RANGE, ["USD"])

    assert rates["USD"] == [(date(2026, 11, 18), "USD", "NGN", Decimal("1353.4741"))]


@pytest.mark.asyncio
async def test_cbn_yen_and_cfa_map_to_jpy_and_xof(monkeypatch: pytest.MonkeyPatch):
    """«YEN» and «CFA» are the bank's names for JPY and XOF; the value is naira per 1 unit."""
    rows = [_row("YEN", "2026-11-18", "8.4608"), _row("CFA", "2026-11-18", "2.2796")]
    _route(monkeypatch, cbn_mod, _by_url(recent=rows))

    rates = await CBNProvider().fetch_rates(RECENT_RANGE, ["JPY", "XOF"])

    assert rates["JPY"] == [(date(2026, 11, 18), "JPY", "NGN", Decimal("8.4608"))]
    assert rates["XOF"] == [(date(2026, 11, 18), "XOF", "NGN", Decimal("2.2796"))]


@pytest.mark.asyncio
async def test_cbn_sdr_maps_to_xdr(monkeypatch: pytest.MonkeyPatch):
    """The bank's «SDR» is the IMF's unit: ``1848.9020`` naira per SDR, served as XDR."""
    _route(monkeypatch, cbn_mod, _by_url(recent=[_row("SDR", "2026-11-18", "1848.9020")]))

    rates = await CBNProvider().fetch_rates(RECENT_RANGE, ["XDR"])

    assert rates["XDR"] == [(date(2026, 11, 18), "XDR", "NGN", Decimal("1848.9020"))]


@pytest.mark.asyncio
async def test_cbn_names_with_trailing_spaces_or_tabs_are_stripped(monkeypatch: pytest.MonkeyPatch):
    """«EURO\\t» and «YEN » find their code after ``strip()``."""
    rows = [_row("EURO\t", "2026-11-18", "1570.5"), _row("YEN ", "2026-11-18", "8.46")]
    _route(monkeypatch, cbn_mod, _by_url(recent=rows))

    rates = await CBNProvider().fetch_rates(RECENT_RANGE, ["EUR", "JPY"])

    assert [r[3] for r in rates["EUR"]] == [Decimal("1570.5")]
    assert [r[3] for r in rates["JPY"]] == [Decimal("8.46")]


@pytest.mark.asyncio
async def test_cbn_name_variants_reach_the_same_code(monkeypatch: pytest.MonkeyPatch):
    """POUND/POUNDS STERLING, DANISH KRONA/KRONER and JAPANESE YEN are one currency each, on different days."""
    rows = [
        _row("POUNDS STERLING", "2026-11-17", "1800.1"),
        _row("POUND STERLING", "2026-11-18", "1801.2"),
        _row("DANISH KRONA", "2026-11-17", "210.1"),
        _row("DANISH KRONER", "2026-11-18", "210.2"),
        _row("JAPANESE YEN", "2026-11-18", "8.5"),
    ]
    _route(monkeypatch, cbn_mod, _by_url(recent=rows))

    rates = await CBNProvider().fetch_rates(RECENT_RANGE, ["GBP", "DKK", "JPY"])

    assert [(r[0], r[3]) for r in rates["GBP"]] == [
        (date(2026, 11, 17), Decimal("1800.1")),
        (date(2026, 11, 18), Decimal("1801.2")),
    ]
    assert [(r[0], r[3]) for r in rates["DKK"]] == [
        (date(2026, 11, 17), Decimal("210.1")),
        (date(2026, 11, 18), Decimal("210.2")),
    ]
    assert [r[3] for r in rates["JPY"]] == [Decimal("8.5")]


@pytest.mark.asyncio
async def test_cbn_the_other_names_of_the_map_reach_their_codes(monkeypatch: pytest.MonkeyPatch):
    """RIYAL, SWISS FRANC, YUAN/RENMINBI, SOUTH AFRICAN RAND and UAE DIRHAM map to SAR, CHF, CNY, ZAR and AED."""
    rows = [
        _row("RIYAL", "2026-11-18", "360.1"),
        _row("SWISS FRANC", "2026-11-18", "1700.2"),
        _row("YUAN/RENMINBI", "2026-11-18", "190.3"),
        _row("SOUTH AFRICAN RAND", "2026-11-18", "78.4"),
        _row("UAE DIRHAM", "2026-11-18", "368.5"),
    ]
    _route(monkeypatch, cbn_mod, _by_url(recent=rows))

    rates = await CBNProvider().fetch_rates(RECENT_RANGE, ["SAR", "CHF", "CNY", "ZAR", "AED"])

    assert {code: [r[3] for r in found] for code, found in rates.items()} == {
        "SAR": [Decimal("360.1")],
        "CHF": [Decimal("1700.2")],
        "CNY": [Decimal("190.3")],
        "ZAR": [Decimal("78.4")],
        "AED": [Decimal("368.5")],
    }


@pytest.mark.asyncio
async def test_cbn_unknown_names_are_discarded(monkeypatch: pytest.MonkeyPatch):
    """WAUA, NAIRA, POESO and a name never seen are no currency: nothing is returned for them."""
    rows = [_row(name, "2026-11-18", "5.5") for name in ("WAUA", "NAIRA", "POESO", "NEW COIN")] + USD_DAY
    _route(monkeypatch, cbn_mod, _by_url(recent=rows))

    rates = await CBNProvider().fetch_rates(RECENT_RANGE, ["USD", "EUR"])

    assert set(rates) == {"USD", "EUR"}
    assert rates["EUR"] == []
    assert len(rates["USD"]) == 1


@pytest.mark.asyncio
async def test_cbn_rows_newest_first_come_out_ascending(monkeypatch: pytest.MonkeyPatch):
    """The feed is newest first; the tuples are ascending by date."""
    rows = [_row("US DOLLAR", f"2026-11-{day}", "1353.4741") for day in (18, 17, 16)]
    _route(monkeypatch, cbn_mod, _by_url(recent=rows + RECENT[10:]))

    rates = await CBNProvider().fetch_rates(RECENT_RANGE, ["USD"])

    days = [d for d, _, _, _ in rates["USD"]]
    assert days == sorted(days)
    assert days[-3:] == [date(2026, 11, 16), date(2026, 11, 17), date(2026, 11, 18)]


# ── Duplicates ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cbn_a_day_with_two_different_rates_is_dropped(monkeypatch: pytest.MonkeyPatch):
    """Two central rates for one day and currency: that day is dropped, never a pick; other days and currencies stay."""
    rows = [
        _row("YEN", "2026-11-17", "2.7072"),
        _row("YEN", "2026-11-17", "46.0795"),
        _row("YEN", "2026-11-18", "8.4608"),
        _row("US DOLLAR", "2026-11-17", "1353.0"),
    ]
    _route(monkeypatch, cbn_mod, _by_url(recent=rows + RECENT[10:]))

    rates = await CBNProvider().fetch_rates(RECENT_RANGE, ["JPY", "USD"])

    assert [r[0] for r in rates["JPY"]] == [date(2026, 11, 18)]
    assert date(2026, 11, 17) in {r[0] for r in rates["USD"]}


@pytest.mark.asyncio
async def test_cbn_name_variants_of_one_currency_count_as_the_same_key(monkeypatch: pytest.MonkeyPatch):
    """«POUNDS STERLING» and «POUND STERLING» on one day: different rates drop the day, equal rates keep it once."""
    rows = [
        _row("POUNDS STERLING", "2026-11-16", "1800.0"),
        _row("POUND STERLING", "2026-11-16", "1900.0"),
        _row("POUNDS STERLING", "2026-11-17", "1801.0"),
        _row("POUND STERLING", "2026-11-17", "1801.0"),
    ]
    _route(monkeypatch, cbn_mod, _by_url(recent=rows + RECENT[10:]))

    rates = await CBNProvider().fetch_rates(RECENT_RANGE, ["GBP"])

    assert rates["GBP"] == [(date(2026, 11, 17), "GBP", "NGN", Decimal("1801.0"))]


@pytest.mark.asyncio
async def test_cbn_a_repeated_row_with_the_same_rate_is_kept_once(monkeypatch: pytest.MonkeyPatch):
    """The same central rate twice for one day: one tuple."""
    rows = [_row("EURO", "2026-11-18", "1570.5"), _row("EURO", "2026-11-18", "1570.5", buying="1500")]
    _route(monkeypatch, cbn_mod, _by_url(recent=rows + RECENT[10:]))

    rates = await CBNProvider().fetch_rates(RECENT_RANGE, ["EUR"])

    assert rates["EUR"] == [(date(2026, 11, 18), "EUR", "NGN", Decimal("1570.5"))]


# ── Which endpoint ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cbn_a_short_recent_range_costs_one_request_to_the_recent_feed(monkeypatch: pytest.MonkeyPatch):
    """14 days ending on the last recent day: only ``RECENT_URL``, no query string."""
    asked = _route(monkeypatch, cbn_mod, _by_url(recent=RECENT))

    rates = await CBNProvider().fetch_rates(RECENT_RANGE, ["USD"])

    assert _urls(asked) == [RECENT_URL]
    assert asked[0].method == "GET" and asked[0].url.query == b""
    assert len(rates["USD"]) == 14


@pytest.mark.asyncio
async def test_cbn_a_short_old_range_tries_the_recent_feed_then_the_whole_history(monkeypatch: pytest.MonkeyPatch):
    """14 days in 2015: the recent answer does not reach back, so ``ALL_URL`` follows (2 requests)."""
    old = [_row("US DOLLAR", "2015-06-10", "197.5"), _row("US DOLLAR", "2015-06-01", "197.1")]
    asked = _route(monkeypatch, cbn_mod, _by_url(recent=RECENT, everything=old + RECENT))

    rates = await CBNProvider().fetch_rates(OLD_RANGE, ["USD"])

    assert _urls(asked) == [RECENT_URL, ALL_URL]
    assert [(r[0], r[3]) for r in rates["USD"]] == [
        (date(2015, 6, 1), Decimal("197.1")),
        (date(2015, 6, 10), Decimal("197.5")),
    ]


@pytest.mark.asyncio
async def test_cbn_an_empty_recent_answer_falls_back_to_the_whole_history(monkeypatch: pytest.MonkeyPatch):
    """The recent feed answers ``[]``: nothing to prove its reach, so ``ALL_URL`` is asked."""
    asked = _route(monkeypatch, cbn_mod, _by_url(recent=[], everything=USD_DAY))

    rates = await CBNProvider().fetch_rates(RECENT_RANGE, ["USD"])

    assert _urls(asked) == [RECENT_URL, ALL_URL]
    assert len(rates["USD"]) == 1


@pytest.mark.asyncio
async def test_cbn_a_long_range_asks_only_the_whole_history(monkeypatch: pytest.MonkeyPatch):
    """60 days exceed ``RECENT_SPAN_DAYS``: only ``ALL_URL``."""
    asked = _route(monkeypatch, cbn_mod, _by_url(everything=RECENT))

    rates = await CBNProvider().fetch_rates(LONG_RANGE, ["USD"])

    assert _urls(asked) == [ALL_URL]
    assert len(rates["USD"]) == len(RECENT)


# ── Range and currencies ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cbn_min_and_an_earlier_start_begin_at_the_first_day(monkeypatch: pytest.MonkeyPatch):
    """``"min"`` and any earlier start are raised to 2001-12-10: a row of 2001-12-09 is never returned."""
    rows = [
        _row("US DOLLAR", "2001-12-09", "100.0"),
        _row("US DOLLAR", "2001-12-10", "111.0"),
        _row("US DOLLAR", "2001-12-11", "112.0"),
    ]
    _route(monkeypatch, cbn_mod, _by_url(recent=RECENT, everything=rows))
    expected = [
        (date(2001, 12, 10), "USD", "NGN", Decimal("111.0")),
        (date(2001, 12, 11), "USD", "NGN", Decimal("112.0")),
    ]

    from_min = await CBNProvider().fetch_rates(("min", date(2001, 12, 11)), ["USD"])
    from_earlier = await CBNProvider().fetch_rates((date(1980, 1, 1), date(2001, 12, 11)), ["USD"])

    assert from_min["USD"] == expected
    assert from_earlier["USD"] == expected


@pytest.mark.asyncio
async def test_cbn_every_asked_currency_but_ngn_is_a_key_and_unpublished_ones_are_empty(monkeypatch: pytest.MonkeyPatch):
    """NGN is no key; a currency the bank does not publish (BRL) is a key with ``[]``."""
    _route(monkeypatch, cbn_mod, _by_url(recent=USD_DAY))

    rates = await CBNProvider().fetch_rates(RECENT_RANGE, ["NGN", "BRL", "USD"])

    assert set(rates) == {"BRL", "USD"}
    assert rates["BRL"] == []


@pytest.mark.asyncio
async def test_cbn_nothing_servable_or_an_inverted_range_asks_nothing(monkeypatch: pytest.MonkeyPatch):
    """BRL alone, NGN alone, or a start after the end: no request."""
    asked = _route(monkeypatch, cbn_mod, _by_url(recent=USD_DAY))

    assert await CBNProvider().fetch_rates(RECENT_RANGE, ["BRL"]) == {"BRL": []}
    assert await CBNProvider().fetch_rates(RECENT_RANGE, ["NGN"]) == {}
    assert await CBNProvider().fetch_rates((RECENT_RANGE[1], RECENT_RANGE[0]), ["USD"]) == {"USD": []}
    assert asked == []


@pytest.mark.asyncio
async def test_cbn_other_base_currency_is_refused(monkeypatch: pytest.MonkeyPatch):
    """``base_currency`` EUR raises ``ValueError``; None and NGN are fine."""
    _route(monkeypatch, cbn_mod, _by_url(recent=USD_DAY))

    with pytest.raises(ValueError):
        await CBNProvider().fetch_rates(RECENT_RANGE, ["USD"], base_currency="EUR")

    assert len((await CBNProvider().fetch_rates(RECENT_RANGE, ["USD"], base_currency="NGN"))["USD"]) == 1
    assert len((await CBNProvider().fetch_rates(RECENT_RANGE, ["USD"], base_currency=None))["USD"]) == 1


@pytest.mark.asyncio
async def test_cbn_unreadable_rows_are_skipped_and_the_others_stay(monkeypatch: pytest.MonkeyPatch):
    """A bad day, a text, a zero, a negative rate and a day outside the range lose only their own row."""
    rows = [
        _row("US DOLLAR", "2026-11-06", "1350.1"),
        _row("US DOLLAR", "not-a-day", "1350.2"),
        _row("US DOLLAR", "2026-11-08", "abc"),
        _row("US DOLLAR", "2026-11-09", "0"),
        _row("US DOLLAR", "2026-11-10", "-5"),
        _row("US DOLLAR", "2026-11-25", "1350.3"),
        _row("US DOLLAR", "2026-11-18", "1353.4741"),
    ] + RECENT[24:]
    _route(monkeypatch, cbn_mod, _by_url(recent=rows))

    rates = await CBNProvider().fetch_rates(RECENT_RANGE, ["USD"])

    assert [(r[0], r[3]) for r in rates["USD"]] == [
        (date(2026, 11, 6), Decimal("1350.1")),
        (date(2026, 11, 18), Decimal("1353.4741")),
    ]


# ── Errors ───────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cbn_too_many_requests_is_a_rate_limit(monkeypatch: pytest.MonkeyPatch):
    """HTTP 429 raises ``FXRateLimitedError``."""
    _route(monkeypatch, cbn_mod, lambda request: httpx.Response(429))

    with pytest.raises(FXRateLimitedError):
        await CBNProvider().fetch_rates(RECENT_RANGE, ["USD"])


@pytest.mark.asyncio
async def test_cbn_http_500_on_either_endpoint_is_a_service_error(monkeypatch: pytest.MonkeyPatch):
    """500 on the recent feed and 500 on the whole history: ``FXServiceError``, not the rate-limit subclass."""
    _route(monkeypatch, cbn_mod, lambda request: httpx.Response(500, text="Internal error"))

    for span in (RECENT_RANGE, LONG_RANGE):
        with pytest.raises(FXServiceError) as refused:
            await CBNProvider().fetch_rates(span, ["USD"])
        assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.asyncio
async def test_cbn_unreachable_is_a_service_error(monkeypatch: pytest.MonkeyPatch):
    """A transport failure is ``FXServiceError``."""

    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    _route(monkeypatch, cbn_mod, refuse)

    with pytest.raises(FXServiceError):
        await CBNProvider().fetch_rates(RECENT_RANGE, ["USD"])


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("<!DOCTYPE html><html><body>Just a moment...</body></html>", id="cloudflare-html"),
        pytest.param("not json at all", id="non-json"),
        pytest.param('{"error": true}', id="json-object"),
        pytest.param('"just a string"', id="json-string"),
    ],
)
@pytest.mark.asyncio
async def test_cbn_a_body_that_is_not_a_list_is_a_service_error(monkeypatch: pytest.MonkeyPatch, body: str):
    """An HTML page, non-JSON text, or JSON that is not a list: ``FXServiceError``, never a rate limit."""
    _route(monkeypatch, cbn_mod, lambda request: httpx.Response(200, content=body.encode()))

    with pytest.raises(FXServiceError) as refused:
        await CBNProvider().fetch_rates(RECENT_RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


# ── Catalogue and identity ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cbn_catalogue_is_the_mapped_currencies_plus_ngn_without_a_request(monkeypatch: pytest.MonkeyPatch):
    """Sorted ISO values plus NGN, and not one request made."""
    asked = _route(monkeypatch, cbn_mod, _by_url(recent=USD_DAY))

    currencies = await CBNProvider().get_supported_currencies()

    assert currencies == ["AED", "CHF", "CNY", "DKK", "EUR", "GBP", "JPY", "NGN", "SAR", "USD", "XDR", "XOF", "ZAR"]
    assert CBNProvider().fallback_currencies == currencies
    assert asked == []


def test_cbn_identity_urls_and_constants():
    """Code, base, level, docs page, the two URLs, the span, the first day and the name map."""
    provider = CBNProvider()
    assert (provider.code, provider.base_currency, provider.warning_level) == ("CBN", "NGN", "warning")
    assert provider.docs_url == "/mkdocs/user/fx/providers/cbn/"
    assert cbn_mod.ALL_URL == ALL_URL
    assert cbn_mod.RECENT_URL == RECENT_URL
    assert cbn_mod.RECENT_SPAN_DAYS == 20
    assert cbn_mod.FIRST_DAY == date(2001, 12, 10)
    names = cbn_mod.CURRENCY_NAMES
    assert names["US DOLLAR"] == "USD" and names["YEN"] == "JPY" and names["CFA"] == "XOF"
    assert names["POUND STERLING"] == names["POUNDS STERLING"] == "GBP"
    assert names["SDR"] == "XDR" and len(names) == 15
    assert "WAUA" not in names and "NAIRA" not in names and "POESO" not in names
