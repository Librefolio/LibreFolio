"""NBP FX provider: the National Bank of Poland tables A and B, zloty per foreign unit (no network, no DB, no server).

Lane 75, wave 2 (plan ``plan-phase02FxCentralBanksOndata2.prompt.md``). Shape of the real API, measured on 19/11/2026:

- ``GET /api/exchangerates/tables/{A|B}/{from}/{to}/?format=json`` answers a JSON list of tables, oldest first; table A is
  daily (32 codes with the SDR, XDR), table B weekly (116). A request spans at most 93 days (HTTP 400 beyond). A range with no table is
  answered with HTTP 404 and the text ``Brak danych``.
- A currency can move between tables: before 2011-09-01 the A currencies were published in table B.
- Old tables carry ``country`` and ``symbol`` where new ones carry ``currency``; only ``code`` and ``mid`` are read.
- VES changed its denomination on 2021-10-13 (a factor of one million); SYP is published again only from 2026-01-07.

Every answer here is synthetic, written by hand in the feed's shape, never data downloaded from the bank.

Isolation: PURE. ``fetch_rates`` and ``get_supported_currencies`` run whole, their module's ``httpx`` replaced for the
test by the real module whose ``AsyncClient`` answers through an ``httpx.MockTransport`` (``_route``, from
``test_rate_limit_http_providers.py``). The pause between requests is zero, or a recorder, never a real sleep.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal

import httpx
import pytest

from backend.app.services.fx.base import FXRateLimitedError, FXServiceError
from backend.app.services.fx_providers.nbp import plugin as nbp_mod
from backend.app.services.fx_providers.nbp.plugin import NBPProvider
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

TABLES_URL = "https://api.nbp.pl/api/exchangerates/tables"
SPAN_2026 = (date(2026, 1, 5), date(2026, 1, 30))
SPAN_2005 = (date(2005, 1, 3), date(2005, 1, 31))
FULL_WINDOW = (date(2026, 1, 1), date(2026, 4, 3))  # exactly 93 days
TWO_WINDOWS = (date(2026, 1, 1), date(2026, 4, 4))  # 94 days: 93 + 1

A_CODES = "AUD BRL CAD CHF CLP CNY CZK DKK EUR GBP HKD HUF IDR ILS INR ISK JPY KRW MXN MYR NOK NZD PHP RON SEK SGD THB TRY UAH USD XDR ZAR".split()  # fmt: skip
B_CODES = (
    "AED AFN ALL AMD AOA ARS AWG AZN BAM BBD BDT BHD BIF BND BOB BSD BWP BYN BZD CDF COP CRC CUP CVE DJF DOP DZD EGP ERN ETB "
    "FJD GEL GHS GIP GMD GNF GTQ GYD HNL HTG IQD IRR JMD JOD KES KGS KHR KMF KWD KZT LAK LBP LKR LRD LSL LYD MAD MDL MGA MKD "
    "MMK MNT MOP MRU MUR MVR MWK MZN NAD NGN NIO NPR OMR PAB PEN PGK PKR PYG QAR RSD RUB RWF SAR SBD SCR SDG SLE SOS SRD SSP "
    "STN SVC SYP SZL TJS TMT TND TOP TTD TWD TZS UGX UYU UZS VES VND VUV WST XAF XCD XCG XOF XPF YER ZMW ZWG"
).split()  # fmt: skip


@pytest.fixture(autouse=True)
def _no_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test waits between two requests, unless it records the pause itself."""
    monkeypatch.setattr(NBPProvider, "PAUSE_SECONDS", 0)


def _table(day: str, no: str = "1/A/NBP/2026", **mids: str) -> str:
    """One table as raw JSON; each keyword is a code, its value the literal text of ``mid`` (``'"x"'`` for a string)."""
    rates = ",".join(f'{{"currency":"synthetic","code":"{code}","mid":{mid}}}' for code, mid in mids.items())
    return f'{{"table":"A","no":"{no}","effectiveDate":"{day}","rates":[{rates}]}}'


def _json(*tables: str, status: int = 200) -> httpx.Response:
    return httpx.Response(status, headers={"content-type": "application/json"}, content=("[" + ",".join(tables) + "]").encode())


def _no_data() -> httpx.Response:
    return httpx.Response(404, headers={"content-type": "text/plain"}, text="404 NotFound - Not Found - Brak danych")


def _parts(request: httpx.Request) -> tuple[str, str, str]:
    """``(table, from, to)`` of a request."""
    table, start, end = request.url.path.strip("/").split("/")[-3:]
    return table, start, end


def _serve(a: str | None = None, b: str | None = None) -> Callable[[httpx.Request], httpx.Response]:
    """Every window of table A answers ``a`` (a raw JSON list body), every window of B answers ``b``; ``None`` is «Brak danych»."""
    bodies = {"A": a, "B": b}

    def handle(request: httpx.Request) -> httpx.Response:
        body = bodies[_parts(request)[0]]
        if body is None:
            return _no_data()
        return httpx.Response(200, headers={"content-type": "application/json"}, content=body.encode())

    return handle


def _list(*tables: str) -> str:
    return "[" + ",".join(tables) + "]"


def _letters(asked: list[httpx.Request]) -> set[str]:
    return {_parts(r)[0] for r in asked}


def _pairs(rows: list[tuple]) -> list[tuple[date, Decimal]]:
    return [(r[0], r[3]) for r in rows]


# ── Identity and catalogue ───────────────────────────────────────────────────────


def test_nbp_identity_and_constants():
    provider = NBPProvider()
    assert (provider.code, provider.base_currency, provider.warning_level) == ("NBP", "PLN", "warning")
    assert provider.docs_url == "/mkdocs/user/fx/providers/nbp/"
    assert nbp_mod.TABLES_URL == TABLES_URL
    assert nbp_mod.FIRST_DAY == date(2002, 1, 2)
    assert nbp_mod.WINDOW_DAYS == 93
    assert nbp_mod.B_HISTORY_UNTIL == date(2011, 8, 31)
    assert nbp_mod.SERIES_FROM == {"SYP": date(2026, 1, 7)}
    assert nbp_mod.VES_NEW_FROM == date(2021, 10, 13)
    assert nbp_mod.VES_FACTOR == Decimal(10**6)
    assert list(nbp_mod.A_CURRENCIES) == A_CODES and len(nbp_mod.A_CURRENCIES) == 32 and "XDR" in nbp_mod.A_CURRENCIES
    assert list(nbp_mod.B_CURRENCIES) == B_CODES and len(nbp_mod.B_CURRENCIES) == 116


def test_nbp_pause_between_requests_is_a_third_of_a_second_by_default(monkeypatch: pytest.MonkeyPatch):
    """The class default, seen with the fixture's zero undone."""
    monkeypatch.undo()
    assert NBPProvider.PAUSE_SECONDS == 0.3


@pytest.mark.asyncio
async def test_nbp_catalogue_is_both_tables_plus_pln_without_a_request(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, nbp_mod, _serve(a=_list()))

    currencies = await NBPProvider().get_supported_currencies()

    assert currencies == sorted([*A_CODES, *B_CODES, "PLN"])
    assert "XDR" in currencies and len(currencies) == 148 + 1
    assert NBPProvider().fallback_currencies == currencies
    assert asked == []


@pytest.mark.asyncio
async def test_nbp_other_base_currency_is_refused(monkeypatch: pytest.MonkeyPatch):
    """``base_currency`` EUR raises ``ValueError``; None and PLN are fine."""
    _route(monkeypatch, nbp_mod, _serve(a=_list(_table("2026-01-05", USD="4.0"))))

    with pytest.raises(ValueError):
        await NBPProvider().fetch_rates(SPAN_2026, ["USD"], base_currency="EUR")

    assert len((await NBPProvider().fetch_rates(SPAN_2026, ["USD"], base_currency="PLN"))["USD"]) == 1
    assert len((await NBPProvider().fetch_rates(SPAN_2026, ["USD"], base_currency=None))["USD"]) == 1


# ── Which tables ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("currencies", "span", "letters"),
    [
        pytest.param(["USD"], SPAN_2026, {"A"}, id="a-currency-today-only-a"),
        pytest.param(["KES"], SPAN_2026, {"B"}, id="b-currency-today-only-b"),
        pytest.param(["USD"], SPAN_2005, {"A", "B"}, id="a-currency-in-2005-both"),
        pytest.param(["USD", "KES"], SPAN_2026, {"A", "B"}, id="mixed-both"),
        pytest.param(["KES"], SPAN_2005, {"B"}, id="b-currency-in-2005-only-b"),
        pytest.param(["USD"], (date(2011, 8, 31), date(2011, 9, 30)), {"A", "B"}, id="start-on-the-last-b-day"),
        pytest.param(["USD"], (date(2011, 9, 1), date(2011, 9, 30)), {"A"}, id="start-after-the-last-b-day"),
        pytest.param(["USD", "XAU"], SPAN_2026, {"A"}, id="unserved-ignored"),
        pytest.param(["XDR"], SPAN_2026, {"A"}, id="xdr-only-a"),
    ],
)
@pytest.mark.asyncio
async def test_nbp_asks_the_tables_that_can_hold_the_currencies(monkeypatch: pytest.MonkeyPatch, currencies, span, letters):
    """A currency asked from a range that starts on or before 2011-08-31 is also looked up in table B."""
    asked = _route(monkeypatch, nbp_mod, _serve())

    await NBPProvider().fetch_rates(span, currencies)

    assert _letters(asked) == letters


@pytest.mark.asyncio
async def test_nbp_request_shape_is_a_get_with_format_json(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, nbp_mod, _serve())

    await NBPProvider().fetch_rates(SPAN_2026, ["USD"])

    assert len(asked) == 1
    assert asked[0].method == "GET"
    assert str(asked[0].url).startswith(f"{TABLES_URL}/A/2026-01-05/2026-01-30/")
    assert asked[0].url.params["format"] == "json"


# ── Windows ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_nbp_a_range_of_93_days_is_one_window(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, nbp_mod, _serve())

    await NBPProvider().fetch_rates(FULL_WINDOW, ["USD"])

    assert [_parts(r) for r in asked] == [("A", "2026-01-01", "2026-04-03")]


@pytest.mark.asyncio
async def test_nbp_a_range_of_94_days_is_two_windows_oldest_first(monkeypatch: pytest.MonkeyPatch):
    """The second window starts the day after the first ends."""
    asked = _route(monkeypatch, nbp_mod, _serve())

    await NBPProvider().fetch_rates(TWO_WINDOWS, ["USD"])

    assert [_parts(r) for r in asked] == [("A", "2026-01-01", "2026-04-03"), ("A", "2026-04-04", "2026-04-04")]


@pytest.mark.asyncio
async def test_nbp_each_table_walks_its_own_windows(monkeypatch: pytest.MonkeyPatch):
    """USD and KES over 94 days: two windows of A and two of B, each table oldest first."""
    asked = _route(monkeypatch, nbp_mod, _serve())

    await NBPProvider().fetch_rates(TWO_WINDOWS, ["USD", "KES"])

    parts = [_parts(r) for r in asked]
    assert [p for p in parts if p[0] == "A"] == [("A", "2026-01-01", "2026-04-03"), ("A", "2026-04-04", "2026-04-04")]
    assert [p for p in parts if p[0] == "B"] == [("B", "2026-01-01", "2026-04-03"), ("B", "2026-04-04", "2026-04-04")]


@pytest.mark.parametrize("start", ["min", date(1980, 1, 1)])
@pytest.mark.asyncio
async def test_nbp_min_and_an_earlier_start_begin_at_the_first_day(monkeypatch: pytest.MonkeyPatch, start):
    """``"min"`` and any earlier start are raised to 2002-01-02."""
    asked = _route(monkeypatch, nbp_mod, _serve())

    await NBPProvider().fetch_rates((start, date(2002, 3, 1)), ["KES"])

    assert [_parts(r) for r in asked] == [("B", "2002-01-02", "2002-03-01")]


@pytest.mark.asyncio
async def test_nbp_a_404_with_no_data_means_no_table_and_the_next_window_is_still_asked(monkeypatch: pytest.MonkeyPatch):
    """«Brak danych» on the first window is not an error; the second window's rate comes back."""

    def answer(request: httpx.Request) -> httpx.Response:
        if _parts(request)[1] == "2026-01-01":
            return _no_data()
        return _json(_table("2026-04-04", USD="4.1"))

    asked = _route(monkeypatch, nbp_mod, answer)

    rates = await NBPProvider().fetch_rates(TWO_WINDOWS, ["USD"])

    assert len(asked) == 2
    assert rates["USD"] == [(date(2026, 4, 4), "USD", "PLN", Decimal("4.1"))]


# ── Range and currencies ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("span", "currencies", "expected"),
    [
        pytest.param(SPAN_2026, ["PLN"], {}, id="pln-only"),
        pytest.param(SPAN_2026, ["XAU"], {"XAU": []}, id="xau-not-served"),
        pytest.param(SPAN_2026, ["XYZ"], {"XYZ": []}, id="outside-the-catalogue"),
        pytest.param((date(2026, 1, 30), date(2026, 1, 5)), ["USD"], {"USD": []}, id="inverted-range"),
        pytest.param((date(2001, 1, 1), date(2001, 12, 31)), ["USD"], {"USD": []}, id="end-before-first-day"),
    ],
)
@pytest.mark.asyncio
async def test_nbp_nothing_servable_asks_nothing(monkeypatch: pytest.MonkeyPatch, span, currencies, expected):
    asked = _route(monkeypatch, nbp_mod, _serve())

    assert await NBPProvider().fetch_rates(span, currencies) == expected
    assert asked == []


@pytest.mark.asyncio
async def test_nbp_every_asked_currency_but_pln_is_a_key(monkeypatch: pytest.MonkeyPatch):
    """PLN is no key; served currencies the tables do not hold that day (EUR, KES) are keys with ``[]``."""
    _route(monkeypatch, nbp_mod, _serve(a=_list(_table("2026-01-05", USD="4.0")), b=_list()))

    rates = await NBPProvider().fetch_rates(SPAN_2026, ["PLN", "EUR", "KES", "USD", "XAU"])

    assert set(rates) == {"EUR", "KES", "USD", "XAU"}
    assert rates["EUR"] == [] and rates["KES"] == [] and rates["XAU"] == []
    assert len(rates["USD"]) == 1


@pytest.mark.asyncio
async def test_nbp_sdr_is_served_from_table_a(monkeypatch: pytest.MonkeyPatch):
    """XDR (table A) comes back as zloty per SDR."""
    _route(monkeypatch, nbp_mod, _serve(a=_list(_table("2026-01-05", XDR="5.4103"))))

    rates = await NBPProvider().fetch_rates(SPAN_2026, ["XDR"])

    assert rates["XDR"] == [(date(2026, 1, 5), "XDR", "PLN", Decimal("5.4103"))]


# ── Values ───────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_nbp_returns_zloty_per_unit_as_exact_decimals(monkeypatch: pytest.MonkeyPatch):
    """``4.0176`` is ``Decimal("4.0176")`` and ``0.00000208`` is ``Decimal("0.00000208")``, never a float's rounding."""
    body = _list(_table("2026-01-05", USD="4.0176"), _table("2026-01-06", USD="4.0200"))
    _route(monkeypatch, nbp_mod, _serve(a=body, b=_list(_table("2026-01-05", VND="0.00000208"))))

    rates = await NBPProvider().fetch_rates(SPAN_2026, ["USD", "VND"])

    assert rates["USD"][0] == (date(2026, 1, 5), "USD", "PLN", Decimal("4.0176"))
    assert str(rates["USD"][0][3]) == "4.0176"
    assert rates["VND"] == [(date(2026, 1, 5), "VND", "PLN", Decimal("0.00000208"))]


@pytest.mark.asyncio
async def test_nbp_old_tables_with_country_and_symbol_are_read_by_code_and_mid(monkeypatch: pytest.MonkeyPatch):
    """A 2005 table has ``country`` and ``symbol`` where a new one has ``currency``."""
    old = '{"table":"B","no":"1/B/NBP/2005","effectiveDate":"2005-01-05","rates":[{"country":"Kenia","symbol":"KES","code":"KES","mid":0.0412}]}'
    _route(monkeypatch, nbp_mod, _serve(b=_list(old)))

    rates = await NBPProvider().fetch_rates(SPAN_2005, ["KES"])

    assert rates["KES"] == [(date(2005, 1, 5), "KES", "PLN", Decimal("0.0412"))]


@pytest.mark.parametrize("mid", ["0", "0.0", "-1.5", '"abc"', "null", '""'])
@pytest.mark.asyncio
async def test_nbp_an_unusable_mid_loses_only_that_currency_that_day(monkeypatch: pytest.MonkeyPatch, mid: str):
    """A zero, a negative, a string or a null is skipped; the other rate of the day stays."""
    _route(monkeypatch, nbp_mod, _serve(a=_list(_table("2026-01-05", EUR=mid, USD="4.0"))))

    rates = await NBPProvider().fetch_rates(SPAN_2026, ["EUR", "USD"])

    assert rates["EUR"] == []
    assert [r[0] for r in rates["USD"]] == [date(2026, 1, 5)]


@pytest.mark.asyncio
async def test_nbp_currencies_not_asked_are_left_out(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, nbp_mod, _serve(a=_list(_table("2026-01-05", EUR="4.3", USD="4.0"))))

    rates = await NBPProvider().fetch_rates(SPAN_2026, ["USD"])

    assert set(rates) == {"USD"}
    assert [r[1] for r in rates["USD"]] == ["USD"]


@pytest.mark.asyncio
async def test_nbp_tables_outside_the_range_or_with_a_bad_date_are_skipped(monkeypatch: pytest.MonkeyPatch):
    """A day after the end, a day before the start and an unreadable date lose only their own table."""
    body = _list(
        _table("2026-01-02", USD="9.1"),
        _table("2026-01-06", USD="4.1"),
        _table("not-a-day", USD="9.2"),
        _table("2026-02-02", USD="9.3"),
        _table("2026-01-30", USD="4.2"),
    )
    _route(monkeypatch, nbp_mod, _serve(a=body))

    rates = await NBPProvider().fetch_rates(SPAN_2026, ["USD"])

    assert _pairs(rates["USD"]) == [(date(2026, 1, 6), Decimal("4.1")), (date(2026, 1, 30), Decimal("4.2"))]


@pytest.mark.asyncio
async def test_nbp_output_is_ascending_across_windows_and_tables(monkeypatch: pytest.MonkeyPatch):
    """Windows and tables answer out of order: the series of one currency comes out by date."""

    def answer(request: httpx.Request) -> httpx.Response:
        table, start, _ = _parts(request)
        if table == "A":
            return _json(_table("2026-04-04", USD="4.4")) if start == "2026-04-04" else _json(_table("2026-03-02", USD="4.3"), _table("2026-01-05", USD="4.0"))
        return _json(_table("2026-02-02", USD="4.2"))

    _route(monkeypatch, nbp_mod, answer)

    rates = await NBPProvider().fetch_rates(TWO_WINDOWS, ["USD", "KES"])

    days = [r[0] for r in rates["USD"]]
    assert days == [date(2026, 1, 5), date(2026, 2, 2), date(2026, 3, 2), date(2026, 4, 4)]  # A, B, A, A by date


@pytest.mark.asyncio
async def test_nbp_the_same_day_from_both_tables_with_equal_mids_is_kept_once(monkeypatch: pytest.MonkeyPatch):
    """In 2005 USD can be in table A and in table B on one day."""
    _route(monkeypatch, nbp_mod, _serve(a=_list(_table("2005-01-05", USD="3.0100")), b=_list(_table("2005-01-05", USD="3.0100"))))

    rates = await NBPProvider().fetch_rates(SPAN_2005, ["USD"])

    assert rates["USD"] == [(date(2005, 1, 5), "USD", "PLN", Decimal("3.0100"))]


@pytest.mark.asyncio
async def test_nbp_the_same_day_from_both_tables_with_different_mids_is_dropped(monkeypatch: pytest.MonkeyPatch):
    """The two tables disagree on 01-05 (dropped); 01-12 is single and stays."""
    a = _list(_table("2005-01-05", USD="3.01"), _table("2005-01-12", USD="3.02"))
    b = _list(_table("2005-01-05", USD="3.05"))
    _route(monkeypatch, nbp_mod, _serve(a=a, b=b))

    rates = await NBPProvider().fetch_rates(SPAN_2005, ["USD"])

    assert _pairs(rates["USD"]) == [(date(2005, 1, 12), Decimal("3.02"))]


# ── VES and SYP ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_nbp_ves_before_the_redenomination_is_multiplied_by_a_million(monkeypatch: pytest.MonkeyPatch):
    """Old bolivares: 9.5E-7 on 2021-10-06 is 0.95."""
    _route(monkeypatch, nbp_mod, _serve(b=_list(_table("2021-10-06", VES="9.5E-7"))))

    rates = await NBPProvider().fetch_rates((date(2021, 10, 1), date(2021, 10, 12)), ["VES"])

    assert rates["VES"] == [(date(2021, 10, 6), "VES", "PLN", Decimal("0.95"))]


@pytest.mark.asyncio
async def test_nbp_ves_from_the_redenomination_day_is_as_published(monkeypatch: pytest.MonkeyPatch):
    """2021-10-13 and later: no factor."""
    _route(monkeypatch, nbp_mod, _serve(b=_list(_table("2021-10-12", VES="9.6E-7"), _table("2021-10-13", VES="0.9"))))

    rates = await NBPProvider().fetch_rates((date(2021, 10, 11), date(2021, 10, 20)), ["VES"])

    assert _pairs(rates["VES"]) == [(date(2021, 10, 12), Decimal("0.96")), (date(2021, 10, 13), Decimal("0.9"))]


@pytest.mark.asyncio
async def test_nbp_syp_before_its_series_start_is_skipped(monkeypatch: pytest.MonkeyPatch):
    """SYP rows before 2026-01-07 are left out, the 07th stays."""
    _route(monkeypatch, nbp_mod, _serve(b=_list(_table("2026-01-06", SYP="0.0003"), _table("2026-01-07", SYP="0.0004"))))

    rates = await NBPProvider().fetch_rates(SPAN_2026, ["SYP"])

    assert _pairs(rates["SYP"]) == [(date(2026, 1, 7), Decimal("0.0004"))]


# ── Pause ────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_nbp_pauses_before_every_request_of_a_table_after_its_first(monkeypatch: pytest.MonkeyPatch):
    """A with two windows and B with two windows: four requests, two pauses of ``PAUSE_SECONDS``."""
    monkeypatch.setattr(NBPProvider, "PAUSE_SECONDS", 0.3)
    slept: list[float] = []

    async def record(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(nbp_mod.asyncio, "sleep", record)
    asked = _route(monkeypatch, nbp_mod, _serve())

    await NBPProvider().fetch_rates(TWO_WINDOWS, ["USD", "KES"])

    assert len(asked) == 4
    assert slept == [0.3, 0.3]


@pytest.mark.asyncio
async def test_nbp_one_request_per_table_needs_no_pause(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(NBPProvider, "PAUSE_SECONDS", 0.3)
    slept: list[float] = []

    async def record(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(nbp_mod.asyncio, "sleep", record)
    asked = _route(monkeypatch, nbp_mod, _serve())

    await NBPProvider().fetch_rates(SPAN_2026, ["USD", "KES"])

    assert len(asked) == 2
    assert slept == []


# ── Errors ───────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_nbp_a_404_that_is_not_no_data_is_a_service_error(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, nbp_mod, lambda request: httpx.Response(404, text="404 NotFound - wrong path"))

    with pytest.raises(FXServiceError) as refused:
        await NBPProvider().fetch_rates(SPAN_2026, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.asyncio
async def test_nbp_a_400_is_a_service_error_with_the_server_text(monkeypatch: pytest.MonkeyPatch):
    text = "400 BadRequest - Przekroczony limit 93 dni / Limit of 93 days has been exceeded"
    _route(monkeypatch, nbp_mod, lambda request: httpx.Response(400, headers={"content-type": "text/plain"}, text=text))

    with pytest.raises(FXServiceError) as refused:
        await NBPProvider().fetch_rates(SPAN_2026, ["USD"])

    assert "93" in str(refused.value)
    assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.asyncio
async def test_nbp_a_500_is_a_service_error(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, nbp_mod, lambda request: httpx.Response(500, text="down"))

    with pytest.raises(FXServiceError) as refused:
        await NBPProvider().fetch_rates(SPAN_2026, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.asyncio
async def test_nbp_unreachable_is_a_service_error(monkeypatch: pytest.MonkeyPatch):
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    _route(monkeypatch, nbp_mod, refuse)

    with pytest.raises(FXServiceError):
        await NBPProvider().fetch_rates(SPAN_2026, ["USD"])


@pytest.mark.asyncio
async def test_nbp_too_many_requests_is_a_rate_limit(monkeypatch: pytest.MonkeyPatch):
    """HTTP 429 on the first window, then on the second window only: ``FXRateLimitedError`` both times."""
    _route(monkeypatch, nbp_mod, lambda request: httpx.Response(429))
    with pytest.raises(FXRateLimitedError):
        await NBPProvider().fetch_rates(SPAN_2026, ["USD"])

    def answer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429) if _parts(request)[1] == "2026-04-04" else _json()

    _route(monkeypatch, nbp_mod, answer)
    with pytest.raises(FXRateLimitedError):
        await NBPProvider().fetch_rates(TWO_WINDOWS, ["USD"])


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("<!DOCTYPE html><html><body>Maintenance</body></html>", id="html-page"),
        pytest.param('{"table":"A","rates":[]}', id="json-object"),
        pytest.param('"text"', id="json-string"),
        pytest.param("not json at all", id="plain-text"),
        pytest.param("", id="empty-body"),
    ],
)
@pytest.mark.asyncio
async def test_nbp_a_body_that_is_not_a_list_of_tables_is_a_service_error(monkeypatch: pytest.MonkeyPatch, body: str):
    _route(monkeypatch, nbp_mod, lambda request: httpx.Response(200, content=body.encode()))

    with pytest.raises(FXServiceError) as refused:
        await NBPProvider().fetch_rates(SPAN_2026, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.asyncio
async def test_nbp_a_failure_in_either_table_fails_the_whole_call(monkeypatch: pytest.MonkeyPatch):
    """Table A answers well, table B answers 500: no partial result."""

    def answer(request: httpx.Request) -> httpx.Response:
        if _parts(request)[0] == "B":
            return httpx.Response(500, text="down")
        return _json(_table("2026-01-05", USD="4.0"))

    _route(monkeypatch, nbp_mod, answer)

    with pytest.raises(FXServiceError):
        await NBPProvider().fetch_rates(SPAN_2026, ["USD", "KES"])


# ── Table B only as far as it is needed ──────────────────────────────────────────

ACROSS_B_END = (date(2011, 6, 1), date(2011, 12, 31))


@pytest.mark.asyncio
async def test_nbp_with_only_a_currencies_table_b_stops_at_its_history_end(monkeypatch: pytest.MonkeyPatch):
    """USD alone: B is read from the range start to 2011-08-31 at most, while A covers the whole range."""
    asked = _route(monkeypatch, nbp_mod, _serve())

    await NBPProvider().fetch_rates(ACROSS_B_END, ["USD"])

    b_parts = [_parts(r) for r in asked if _parts(r)[0] == "B"]
    a_parts = [_parts(r) for r in asked if _parts(r)[0] == "A"]
    assert b_parts, "table B must still be asked for the history before 2011-09-01"
    assert b_parts[0][1] == "2011-06-01"
    assert all(date.fromisoformat(p[1]) <= date(2011, 8, 31) for p in b_parts)
    assert all(date.fromisoformat(p[2]) <= date(2011, 8, 31) for p in b_parts)
    assert a_parts[0][1] == "2011-06-01" and a_parts[-1][2] == "2011-12-31"


@pytest.mark.asyncio
async def test_nbp_with_a_b_currency_asked_table_b_covers_the_whole_range(monkeypatch: pytest.MonkeyPatch):
    """USD and KES: B runs to the end of the range."""
    asked = _route(monkeypatch, nbp_mod, _serve())

    await NBPProvider().fetch_rates(ACROSS_B_END, ["USD", "KES"])

    b_parts = [_parts(r) for r in asked if _parts(r)[0] == "B"]
    assert b_parts[0][1] == "2011-06-01" and b_parts[-1][2] == "2011-12-31"
