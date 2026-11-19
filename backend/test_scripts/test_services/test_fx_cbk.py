"""CBK FX provider: the Central Bank of Kenya wpDataTables rate tables, read through ``admin-ajax.php`` (no network, no DB, no server).

Lane 75, wave 2, lot L31 (plan ``plan-phase02FxCentralBanksOndata2.prompt.md``, Q4 (a) of the developer: form tokens
allowed as a browser would send them; here no nonce is needed). Measured on the real feed on 19/11/2026:

- Table 193 (current): 15 078 rows from 05/01/2024, 3 columns (date, name, rate), 21 names, 21 duplicate keys all
  identical, ~600 KB in ~5 s. The date lower bound of the server-side DataTables protocol is honoured (from 10/11/2026:
  168 rows); the upper bound is not, so the plugin cuts the end itself.
- Table 32 (old): 97 606 rows up to 04/01/2024, 5 columns (date, name, mean, buy, sell), names with variants
  (``JPY(100)``, ``KES/USHS``, ``HONGKONG $``...), 21 junk rows on 01/01/1970 (and mis-dated rows before the daily series, which starts on 02/11/2004, and on two Sundays), 250 duplicate keys of which 79
  conflicting, ~5.8 MB in ~10 s. The plugin reads the mean.
- Values have 4 decimals until 2025, 2 decimals in 2026. The names mix three directions: KES per unit, KES per 100 units
  (JPY) and units per KES (UGX, TZS, RWF, BIF).

Every answer here is synthetic, written by hand in the feed's shape, never data downloaded from the bank.

Isolation: PURE. ``fetch_rates`` and ``get_supported_currencies`` run whole, their module's ``httpx`` replaced for the
test by the real module whose ``AsyncClient`` answers through an ``httpx.MockTransport`` (``_route``, from
``test_rate_limit_http_providers.py``). The pause between the two tables is zero, or a recorder, never a real sleep.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from urllib.parse import parse_qs

import httpx
import pytest

from backend.app.services.fx.base import FXRateLimitedError, FXServiceError
from backend.app.services.fx_providers.cbk import plugin as cbk_mod
from backend.app.services.fx_providers.cbk.plugin import CBKProvider
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

AJAX_URL = "https://www.centralbank.go.ke/wp-admin/admin-ajax.php"
CURRENT_RANGE = (date(2026, 11, 5), date(2026, 11, 19))
OLD_RANGE = (date(2023, 12, 20), date(2023, 12, 31))
CROSS_RANGE = (date(2023, 12, 28), date(2024, 1, 10))
D = date(2026, 11, 19)


@pytest.fixture(autouse=True)
def _no_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test waits between the two tables, unless it records the pause itself."""
    monkeypatch.setattr(CBKProvider, "PAUSE_SECONDS", 0)


def _cur(day: str, name: str, rate: str) -> list[str]:
    """One row of the current table (3 cells); ``day`` is ``dd/mm/yyyy`` as the bank writes it."""
    return [day, name, rate]


def _old(day: str, name: str, mean: str, buy: str | None = None, sell: str | None = None) -> list[str]:
    """One row of the old table (5 cells); buy and sell differ from the mean on purpose."""
    return [day, name, mean, buy if buy is not None else "1.0000", sell if sell is not None else "999.0000"]


def _table(rows: list[list[str]]) -> dict:
    """The DataTables answer body of a table, newest first as given."""
    return {"draw": 1, "recordsTotal": str(len(rows)), "recordsFiltered": str(len(rows)), "data": rows}


def _html(body: object, status: int = 200) -> httpx.Response:
    """A body sent as ``text/html``, like wpDataTables does even for JSON."""
    text = body if isinstance(body, str) else json.dumps(body)
    return httpx.Response(status, headers={"content-type": "text/html; charset=UTF-8"}, content=text.encode())


def _form(request: httpx.Request) -> dict[str, str]:
    """The POSTed form fields of a request, one value each."""
    return {key: values[0] for key, values in parse_qs(request.content.decode(), keep_blank_values=True).items()}


def _table_id(request: httpx.Request) -> str:
    """The ``table_id`` of the query string."""
    return request.url.params["table_id"]


def _by_table(current: list[list[str]] | None = None, old: list[list[str]] | None = None):
    """A handler serving each table its own rows (404 for a table left as None)."""

    def handle(request: httpx.Request) -> httpx.Response:
        if _table_id(request) == "193" and current is not None:
            return _html(_table(current))
        if _table_id(request) == "32" and old is not None:
            return _html(_table(old))
        return httpx.Response(404)

    return handle


def _ids(asked: list[httpx.Request]) -> list[str]:
    """The asked table ids, in order."""
    return [_table_id(r) for r in asked]


USD_NOW = [_cur("19/11/2026", "US DOLLAR", "129.9900")]


# ── Values and directions ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cbk_per_unit_name_is_kes_per_one_unit(monkeypatch: pytest.MonkeyPatch):
    """«US DOLLAR 129.99» is 1 USD = 129.99 KES: ``(d, USD, KES, value)``."""
    _route(monkeypatch, cbk_mod, _by_table(current=USD_NOW))

    rates = await CBKProvider().fetch_rates(CURRENT_RANGE, ["USD"])

    assert rates["USD"] == [(D, "USD", "KES", Decimal("129.9900"))]


@pytest.mark.asyncio
async def test_cbk_per_100_name_is_divided_by_one_hundred(monkeypatch: pytest.MonkeyPatch):
    """«JPY (100) 83.91» is KES per 100 yen: 1 JPY = 0.8391 KES."""
    _route(monkeypatch, cbk_mod, _by_table(current=[_cur("19/11/2026", "JPY (100)", "83.9100")]))

    rates = await CBKProvider().fetch_rates(CURRENT_RANGE, ["JPY"])

    assert len(rates["JPY"]) == 1
    day, source, destination, value = rates["JPY"][0]
    assert (day, source, destination) == (D, "JPY", "KES")
    assert value == Decimal("0.839100")


@pytest.mark.asyncio
async def test_cbk_inverse_name_is_units_per_one_kes(monkeypatch: pytest.MonkeyPatch):
    """«KES / USHS 32.27» is 1 KES = 32.27 UGX: KES is the source, the value is not inverted."""
    _route(monkeypatch, cbk_mod, _by_table(current=[_cur("19/11/2026", "KES / USHS", "32.2700")]))

    rates = await CBKProvider().fetch_rates(CURRENT_RANGE, ["UGX"])

    assert rates["UGX"] == [(D, "KES", "UGX", Decimal("32.2700"))]


@pytest.mark.asyncio
async def test_cbk_the_three_directions_in_one_call(monkeypatch: pytest.MonkeyPatch):
    """USD, JPY and TZS together keep each its own source, destination and scale."""
    rows = [
        _cur("19/11/2026", "US DOLLAR", "129.9900"),
        _cur("19/11/2026", "JPY (100)", "83.9100"),
        _cur("19/11/2026", "KES / TSHS", "19.1000"),
    ]
    _route(monkeypatch, cbk_mod, _by_table(current=rows))

    rates = await CBKProvider().fetch_rates(CURRENT_RANGE, ["USD", "JPY", "TZS"])

    assert [(rates[c][0][1], rates[c][0][2]) for c in ("USD", "JPY", "TZS")] == [("USD", "KES"), ("JPY", "KES"), ("KES", "TZS")]
    assert rates["JPY"][0][3] == Decimal("0.8391")
    assert rates["TZS"][0][3] == Decimal("19.1")


@pytest.mark.asyncio
async def test_cbk_old_table_uses_the_mean_never_buy_or_sell(monkeypatch: pytest.MonkeyPatch):
    """Five cells: the mean (index 2) is the rate; buy and sell are ignored."""
    rows = [_old("04/01/2024", "US DOLLAR", "157.3912", buy="157.0000", sell="157.7824")]
    _route(monkeypatch, cbk_mod, _by_table(old=rows))

    rates = await CBKProvider().fetch_rates(OLD_RANGE[0:1] + (date(2024, 1, 4),), ["USD"])

    assert rates["USD"] == [(date(2024, 1, 4), "USD", "KES", Decimal("157.3912"))]


@pytest.mark.asyncio
async def test_cbk_names_are_stripped_before_the_lookup(monkeypatch: pytest.MonkeyPatch):
    """«EURO » and « SA RAND» find their code after ``strip()``."""
    rows = [_cur("19/11/2026", "EURO ", "150.5"), _cur("19/11/2026", " SA RAND", "7.45")]
    _route(monkeypatch, cbk_mod, _by_table(current=rows))

    rates = await CBKProvider().fetch_rates(CURRENT_RANGE, ["EUR", "ZAR"])

    assert [r[3] for r in rates["EUR"]] == [Decimal("150.5")]
    assert [r[3] for r in rates["ZAR"]] == [Decimal("7.45")]


@pytest.mark.asyncio
async def test_cbk_name_variants_reach_the_same_code(monkeypatch: pytest.MonkeyPatch):
    """HONGKONG DOLLAR/$, SINGAPORE DOLLAR/$, KES/RWF with or without spaces: one currency each, on different days."""
    rows = [
        _cur("18/11/2026", "HONGKONG DOLLAR", "16.70"),
        _cur("19/11/2026", "HONGKONG $", "16.71"),
        _cur("18/11/2026", "SINGAPORE $", "100.10"),
        _cur("19/11/2026", "SINGAPORE DOLLAR", "100.20"),
        _cur("18/11/2026", "KES/RWF", "11.1"),
        _cur("19/11/2026", "KES / RWF", "11.2"),
    ]
    _route(monkeypatch, cbk_mod, _by_table(current=rows))

    rates = await CBKProvider().fetch_rates(CURRENT_RANGE, ["HKD", "SGD", "RWF"])

    assert [(r[0], r[3]) for r in rates["HKD"]] == [(date(2026, 11, 18), Decimal("16.70")), (D, Decimal("16.71"))]
    assert [(r[0], r[3]) for r in rates["SGD"]] == [(date(2026, 11, 18), Decimal("100.10")), (D, Decimal("100.20"))]
    assert [(r[0], r[3]) for r in rates["RWF"]] == [(date(2026, 11, 18), Decimal("11.1")), (D, Decimal("11.2"))]


@pytest.mark.asyncio
async def test_cbk_unknown_names_are_discarded(monkeypatch: pytest.MonkeyPatch):
    """A name never seen is no currency: nothing is returned for it and the known rows stay."""
    rows = [_cur("19/11/2026", "NEW COIN", "5.5"), _cur("19/11/2026", "SDR", "5.5")] + USD_NOW
    _route(monkeypatch, cbk_mod, _by_table(current=rows))

    rates = await CBKProvider().fetch_rates(CURRENT_RANGE, ["USD", "EUR"])

    assert set(rates) == {"USD", "EUR"}
    assert rates["EUR"] == []
    assert len(rates["USD"]) == 1


@pytest.mark.asyncio
async def test_cbk_rows_newest_first_come_out_ascending(monkeypatch: pytest.MonkeyPatch):
    """The feed is newest first; the tuples are ascending by date."""
    rows = [_cur(f"{day}/11/2026", "US DOLLAR", "129.9900") for day in (19, 18, 17, 16)]
    _route(monkeypatch, cbk_mod, _by_table(current=rows))

    rates = await CBKProvider().fetch_rates(CURRENT_RANGE, ["USD"])

    days = [r[0] for r in rates["USD"]]
    assert days == [date(2026, 11, 16), date(2026, 11, 17), date(2026, 11, 18), date(2026, 11, 19)]


# ── Duplicates ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cbk_a_day_with_two_different_values_is_dropped(monkeypatch: pytest.MonkeyPatch):
    """Two values for one day and currency: that day is dropped, never a pick; other days and currencies stay."""
    rows = [
        _old("20/12/2023", "US DOLLAR", "155.0000"),
        _old("20/12/2023", "US DOLLAR", "156.0000"),
        _old("21/12/2023", "US DOLLAR", "157.0000"),
        _old("20/12/2023", "EURO", "170.0000"),
    ]
    _route(monkeypatch, cbk_mod, _by_table(old=rows))

    rates = await CBKProvider().fetch_rates(OLD_RANGE, ["USD", "EUR"])

    assert [(r[0], r[3]) for r in rates["USD"]] == [(date(2023, 12, 21), Decimal("157.0000"))]
    assert [r[0] for r in rates["EUR"]] == [date(2023, 12, 20)]


@pytest.mark.asyncio
async def test_cbk_name_variants_count_as_the_same_key(monkeypatch: pytest.MonkeyPatch):
    """«JPY (100)» and «JPY(100)» on one day: different values drop the day, equal values keep it once."""
    rows = [
        _cur("18/11/2026", "JPY (100)", "83.00"),
        _cur("18/11/2026", "JPY(100)", "84.00"),
        _cur("19/11/2026", "JPY (100)", "83.91"),
        _cur("19/11/2026", "JPY(100)", "83.91"),
    ]
    _route(monkeypatch, cbk_mod, _by_table(current=rows))

    rates = await CBKProvider().fetch_rates(CURRENT_RANGE, ["JPY"])

    assert len(rates["JPY"]) == 1
    assert rates["JPY"][0][0] == D
    assert rates["JPY"][0][3] == Decimal("0.8391")


@pytest.mark.asyncio
async def test_cbk_a_repeated_row_with_the_same_value_is_kept_once(monkeypatch: pytest.MonkeyPatch):
    """The same value twice for one day: one tuple."""
    _route(monkeypatch, cbk_mod, _by_table(current=USD_NOW + USD_NOW))

    rates = await CBKProvider().fetch_rates(CURRENT_RANGE, ["USD"])

    assert rates["USD"] == [(D, "USD", "KES", Decimal("129.9900"))]


# ── Which tables, and how they are asked ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_cbk_a_current_range_asks_only_table_193_with_the_server_side_form(monkeypatch: pytest.MonkeyPatch):
    """One POST to ``AJAX_URL?action=get_wdtable&table_id=193`` with the DataTables form and the start day as lower bound."""
    asked = _route(monkeypatch, cbk_mod, _by_table(current=USD_NOW))

    await CBKProvider().fetch_rates(CURRENT_RANGE, ["USD"])

    assert len(asked) == 1
    request = asked[0]
    assert request.method == "POST"
    assert f"{request.url.scheme}://{request.url.host}{request.url.path}" == AJAX_URL
    assert request.url.params["action"] == "get_wdtable"
    assert _table_id(request) == "193"
    form = _form(request)
    assert (form["draw"], form["start"], form["length"]) == ("1", "0", "100000")
    assert (form["order[0][column]"], form["order[0][dir]"]) == ("0", "desc")
    for i in range(3):
        assert (form[f"columns[{i}][data]"], form[f"columns[{i}][searchable]"], form[f"columns[{i}][orderable]"]) == (str(i), "true", "true")
    assert "columns[3][data]" not in form
    assert form["columns[0][search][value]"] == "05/11/2026|"


@pytest.mark.asyncio
async def test_cbk_an_old_range_asks_only_table_32_with_five_columns(monkeypatch: pytest.MonkeyPatch):
    """The range ends before 2024-01-05: one POST on table 32, five columns, lower bound = the range start."""
    asked = _route(monkeypatch, cbk_mod, _by_table(old=[_old("21/12/2023", "US DOLLAR", "157.0000")]))

    rates = await CBKProvider().fetch_rates(OLD_RANGE, ["USD"])

    assert _ids(asked) == ["32"]
    form = _form(asked[0])
    assert form["columns[0][search][value]"] == "20/12/2023|"
    assert all(f"columns[{i}][data]" in form for i in range(5)) and "columns[5][data]" not in form
    assert len(rates["USD"]) == 1


@pytest.mark.asyncio
async def test_cbk_a_range_across_the_cut_asks_old_first_then_current_with_a_pause(monkeypatch: pytest.MonkeyPatch):
    """Two requests, old before current, ``PAUSE_SECONDS`` (0.3) once between them; the current lower bound is 2024-01-05."""
    monkeypatch.setattr(CBKProvider, "PAUSE_SECONDS", 0.3)
    slept: list[float] = []

    async def record(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(cbk_mod.asyncio, "sleep", record)
    old = [_old("04/01/2024", "US DOLLAR", "157.3912"), _old("29/12/2023", "US DOLLAR", "156.0000")]
    current = [_cur("08/01/2024", "US DOLLAR", "157.5000"), _cur("05/01/2024", "US DOLLAR", "157.4000")]
    asked = _route(monkeypatch, cbk_mod, _by_table(current=current, old=old))

    rates = await CBKProvider().fetch_rates(CROSS_RANGE, ["USD"])

    assert _ids(asked) == ["32", "193"]
    assert _form(asked[0])["columns[0][search][value]"] == "28/12/2023|"
    assert _form(asked[1])["columns[0][search][value]"] == "05/01/2024|"
    assert slept == [0.3]
    assert [(r[0], r[3]) for r in rates["USD"]] == [
        (date(2023, 12, 29), Decimal("156.0000")),
        (date(2024, 1, 4), Decimal("157.3912")),
        (date(2024, 1, 5), Decimal("157.4000")),
        (date(2024, 1, 8), Decimal("157.5000")),
    ]


@pytest.mark.asyncio
async def test_cbk_one_table_needs_no_pause(monkeypatch: pytest.MonkeyPatch):
    """A single request is not preceded or followed by a pause."""
    monkeypatch.setattr(CBKProvider, "PAUSE_SECONDS", 0.3)
    slept: list[float] = []

    async def record(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(cbk_mod.asyncio, "sleep", record)
    _route(monkeypatch, cbk_mod, _by_table(current=USD_NOW))

    await CBKProvider().fetch_rates(CURRENT_RANGE, ["USD"])

    assert slept == []


@pytest.mark.asyncio
async def test_cbk_each_table_owns_its_period(monkeypatch: pytest.MonkeyPatch):
    """An old-table row after 2024-01-04 and a current-table row before 2024-01-05 are ignored."""
    old = [_old("05/01/2024", "US DOLLAR", "999.0000"), _old("04/01/2024", "US DOLLAR", "157.3912")]
    current = [_cur("05/01/2024", "US DOLLAR", "157.4000"), _cur("04/01/2024", "US DOLLAR", "888.0000")]
    _route(monkeypatch, cbk_mod, _by_table(current=current, old=old))

    rates = await CBKProvider().fetch_rates(CROSS_RANGE, ["USD"])

    assert [(r[0], r[3]) for r in rates["USD"]] == [
        (date(2024, 1, 4), Decimal("157.3912")),
        (date(2024, 1, 5), Decimal("157.4000")),
    ]


# ── Range and currencies ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cbk_min_and_an_earlier_start_begin_at_the_daily_series(monkeypatch: pytest.MonkeyPatch):
    """``"min"`` and any earlier start ask from 02/11/2004; the mis-dated rows before it (2003, 1970, 01/11/2004) are never returned."""
    rows = [
        _old("03/11/2004", "US DOLLAR", "78.5000"),
        _old("02/11/2004", "US DOLLAR", "78.0000"),
        _old("01/11/2004", "US DOLLAR", "77.0000"),
        _old("12/09/2003", "US DOLLAR", "76.0000"),
        _old("01/01/1970", "US DOLLAR", "1.0000"),
    ]
    asked = _route(monkeypatch, cbk_mod, _by_table(old=rows))
    end = date(2004, 11, 30)
    expected = [(date(2004, 11, 2), "USD", "KES", Decimal("78.0000")), (date(2004, 11, 3), "USD", "KES", Decimal("78.5000"))]

    from_min = await CBKProvider().fetch_rates(("min", end), ["USD"])
    from_earlier = await CBKProvider().fetch_rates((date(1970, 1, 1), end), ["USD"])

    assert from_min["USD"] == expected
    assert from_earlier["USD"] == expected
    assert [_form(r)["columns[0][search][value]"] for r in asked] == ["02/11/2004|"] * 2


@pytest.mark.asyncio
async def test_cbk_old_table_weekend_rows_are_skipped_but_current_table_ones_are_kept(monkeypatch: pytest.MonkeyPatch):
    """Table 32 has mis-dated rows on Sundays: a Saturday or Sunday row of it is dropped; table 193 keeps its weekend rows."""
    old = [
        _old("13/04/2015", "US DOLLAR", "100.0000"),  # Monday
        _old("12/04/2015", "US DOLLAR", "101.0000"),  # Sunday
        _old("11/04/2015", "US DOLLAR", "102.0000"),  # Saturday
        _old("10/04/2015", "US DOLLAR", "103.0000"),  # Friday
    ]
    current = [_cur("08/01/2024", "US DOLLAR", "157.5000"), _cur("06/01/2024", "US DOLLAR", "157.4000")]  # Monday, Saturday
    _route(monkeypatch, cbk_mod, _by_table(current=current, old=old))

    old_rates = await CBKProvider().fetch_rates((date(2015, 4, 1), date(2015, 4, 30)), ["USD"])
    current_rates = await CBKProvider().fetch_rates((date(2024, 1, 5), date(2024, 1, 10)), ["USD"])

    assert [(r[0], r[3]) for r in old_rates["USD"]] == [
        (date(2015, 4, 10), Decimal("103.0000")),
        (date(2015, 4, 13), Decimal("100.0000")),
    ]
    assert [(r[0], r[3]) for r in current_rates["USD"]] == [
        (date(2024, 1, 6), Decimal("157.4000")),
        (date(2024, 1, 8), Decimal("157.5000")),
    ]


@pytest.mark.asyncio
async def test_cbk_every_asked_currency_but_kes_is_a_key_and_unpublished_ones_are_empty(monkeypatch: pytest.MonkeyPatch):
    """KES is no key; a currency the bank does not publish (BRL) is a key with ``[]``."""
    _route(monkeypatch, cbk_mod, _by_table(current=USD_NOW))

    rates = await CBKProvider().fetch_rates(CURRENT_RANGE, ["KES", "BRL", "USD"])

    assert set(rates) == {"BRL", "USD"}
    assert rates["BRL"] == []


@pytest.mark.asyncio
async def test_cbk_nothing_servable_or_an_inverted_range_asks_nothing(monkeypatch: pytest.MonkeyPatch):
    """BRL alone, KES alone, or a start after the end: no request."""
    asked = _route(monkeypatch, cbk_mod, _by_table(current=USD_NOW, old=USD_NOW))

    assert await CBKProvider().fetch_rates(CURRENT_RANGE, ["BRL"]) == {"BRL": []}
    assert await CBKProvider().fetch_rates(CURRENT_RANGE, ["KES"]) == {}
    assert await CBKProvider().fetch_rates((CURRENT_RANGE[1], CURRENT_RANGE[0]), ["USD"]) == {"USD": []}
    assert asked == []


@pytest.mark.asyncio
async def test_cbk_other_base_currency_is_refused(monkeypatch: pytest.MonkeyPatch):
    """``base_currency`` EUR raises ``ValueError``; None and KES are fine."""
    _route(monkeypatch, cbk_mod, _by_table(current=USD_NOW))

    with pytest.raises(ValueError):
        await CBKProvider().fetch_rates(CURRENT_RANGE, ["USD"], base_currency="EUR")

    assert len((await CBKProvider().fetch_rates(CURRENT_RANGE, ["USD"], base_currency="KES"))["USD"]) == 1
    assert len((await CBKProvider().fetch_rates(CURRENT_RANGE, ["USD"], base_currency=None))["USD"]) == 1


@pytest.mark.asyncio
async def test_cbk_unreadable_rows_are_skipped_and_the_others_stay(monkeypatch: pytest.MonkeyPatch):
    """A bad day, a text, an empty, a zero, a negative value, a day after the end and one before the start lose only their row."""
    rows = [
        _cur("19/11/2026", "US DOLLAR", "129.9900"),
        _cur("not-a-day", "US DOLLAR", "129.1"),
        _cur("18/11/2026", "US DOLLAR", "abc"),
        _cur("17/11/2026", "US DOLLAR", ""),
        _cur("16/11/2026", "US DOLLAR", "0"),
        _cur("15/11/2026", "US DOLLAR", "-5"),
        _cur("20/11/2026", "US DOLLAR", "130.5"),
        _cur("04/11/2026", "US DOLLAR", "128.5"),
        _cur("10/11/2026", "US DOLLAR", "129.5"),
    ]
    _route(monkeypatch, cbk_mod, _by_table(current=rows))

    rates = await CBKProvider().fetch_rates(CURRENT_RANGE, ["USD"])

    assert [(r[0], r[3]) for r in rates["USD"]] == [
        (date(2026, 11, 10), Decimal("129.5")),
        (D, Decimal("129.9900")),
    ]


# ── Errors ───────────────────────────────────────────────────────────────────────


def _failing_on(table: str, failure):
    """A handler answering well on every table but ``table``, where ``failure(request)`` decides."""

    def handle(request: httpx.Request) -> httpx.Response:
        if _table_id(request) == table:
            return failure(request)
        return _html(_table([]))

    return handle


@pytest.mark.parametrize("table", ["32", "193"])
@pytest.mark.asyncio
async def test_cbk_too_many_requests_on_either_request_is_a_rate_limit(monkeypatch: pytest.MonkeyPatch, table: str):
    """HTTP 429 on the old or on the current request raises ``FXRateLimitedError`` for the whole call."""
    _route(monkeypatch, cbk_mod, _failing_on(table, lambda request: httpx.Response(429, headers={"Retry-After": "30"})))

    with pytest.raises(FXRateLimitedError):
        await CBKProvider().fetch_rates(CROSS_RANGE, ["USD"])


@pytest.mark.parametrize("table", ["32", "193"])
@pytest.mark.asyncio
async def test_cbk_http_500_on_either_request_is_a_service_error(monkeypatch: pytest.MonkeyPatch, table: str):
    """500 on one of the two tables: ``FXServiceError`` for the whole call, not the rate-limit subclass."""
    _route(monkeypatch, cbk_mod, _failing_on(table, lambda request: httpx.Response(500, text="Internal error")))

    with pytest.raises(FXServiceError) as refused:
        await CBKProvider().fetch_rates(CROSS_RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.parametrize("table", ["32", "193"])
@pytest.mark.asyncio
async def test_cbk_unreachable_on_either_request_is_a_service_error(monkeypatch: pytest.MonkeyPatch, table: str):
    """A transport failure on one of the two tables is ``FXServiceError``."""

    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    _route(monkeypatch, cbk_mod, _failing_on(table, refuse))

    with pytest.raises(FXServiceError):
        await CBKProvider().fetch_rates(CROSS_RANGE, ["USD"])


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("", id="empty-body-nonce-required"),
        pytest.param("<!DOCTYPE html><html><body>Forbidden</body></html>", id="html-page"),
        pytest.param("not json at all", id="non-json"),
        pytest.param('{"draw": 1, "recordsTotal": "0"}', id="json-without-data"),
        pytest.param('{"data": "oops"}', id="data-not-a-list"),
    ],
)
@pytest.mark.asyncio
async def test_cbk_a_body_that_is_not_a_table_is_a_service_error(monkeypatch: pytest.MonkeyPatch, body: str):
    """An empty body (a nonce is required), an HTML page, non-JSON text or JSON without a ``data`` list: ``FXServiceError``."""
    _route(monkeypatch, cbk_mod, lambda request: _html(body))

    with pytest.raises(FXServiceError) as refused:
        await CBKProvider().fetch_rates(CURRENT_RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.asyncio
async def test_cbk_an_answer_cut_at_the_page_length_is_a_service_error(monkeypatch: pytest.MonkeyPatch):
    """``recordsFiltered`` above the rows sent means the page was cut: the oldest days would be lost, so ``FXServiceError``."""
    rows = [_cur("19/11/2026", "US DOLLAR", "129.9900"), _cur("18/11/2026", "US DOLLAR", "129.5000")]
    _route(monkeypatch, cbk_mod, lambda request: _html({**_table(rows), "recordsFiltered": "3"}))

    with pytest.raises(FXServiceError, match="cut") as refused:
        await CBKProvider().fetch_rates(CURRENT_RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.asyncio
async def test_cbk_records_filtered_equal_to_the_rows_works_as_before(monkeypatch: pytest.MonkeyPatch):
    """``recordsFiltered`` equal to the number of rows (as an int too) is a whole answer."""
    rows = [_cur("19/11/2026", "US DOLLAR", "129.9900"), _cur("18/11/2026", "US DOLLAR", "129.5000")]
    _route(monkeypatch, cbk_mod, lambda request: _html({**_table(rows), "recordsFiltered": 2}))

    rates = await CBKProvider().fetch_rates(CURRENT_RANGE, ["USD"])

    assert [r[0] for r in rates["USD"]] == [date(2026, 11, 18), D]


# ── Catalogue and identity ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cbk_catalogue_is_the_mapped_currencies_plus_kes_without_a_request(monkeypatch: pytest.MonkeyPatch):
    """22 sorted ISO codes including KES, and not one request made."""
    asked = _route(monkeypatch, cbk_mod, _by_table(current=USD_NOW))

    currencies = await CBKProvider().get_supported_currencies()

    assert currencies == [
        "AED", "AUD", "BIF", "CAD", "CHF", "CNY", "DKK", "EUR", "GBP", "HKD", "INR",
        "JPY", "KES", "NOK", "RWF", "SAR", "SEK", "SGD", "TZS", "UGX", "USD", "ZAR",
    ]  # fmt: skip
    assert CBKProvider().fallback_currencies == currencies
    assert asked == []


def test_cbk_identity_urls_tables_and_name_map():
    """Code, base, level, docs page, URL, tables, first days, page length and some entries of the name map."""
    provider = CBKProvider()
    assert (provider.code, provider.base_currency, provider.warning_level) == ("CBK", "KES", "warning")
    assert provider.docs_url == "/mkdocs/user/fx/providers/cbk/"
    assert cbk_mod.AJAX_URL == AJAX_URL
    assert (cbk_mod.CURRENT_TABLE, cbk_mod.OLD_TABLE) == ("193", "32")
    assert cbk_mod.CURRENT_FIRST_DAY == date(2024, 1, 5)
    assert cbk_mod.FIRST_DAY == date(2004, 11, 2)
    assert cbk_mod.PAGE_LENGTH == 100000
    names = cbk_mod.CURRENCY_NAMES
    assert names["US DOLLAR"] == ("USD", "per_unit")
    assert names["HONGKONG $"] == ("HKD", "per_unit")
    assert names["JPY (100)"] == names["JPY(100)"] == ("JPY", "per_100")
    assert names["KES / USHS"] == names["KES/USHS"] == ("UGX", "inverse")
    assert names["KES/BIF"] == ("BIF", "inverse")
    assert "SDR" not in names


def test_cbk_pause_between_tables_is_a_third_of_a_second_by_default(monkeypatch: pytest.MonkeyPatch):
    """The class default, seen with the fixture's zero undone."""
    monkeypatch.undo()
    assert CBKProvider.PAUSE_SECONDS == 0.3
