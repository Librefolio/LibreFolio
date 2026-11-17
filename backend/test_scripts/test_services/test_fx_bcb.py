"""BCB FX provider: the PTAX closing CSV per currency (feed C), types A and B, BRL, SLL as SLE, and what it refuses (no network, no DB, no server).

Lane 75, wave 1, lot L11 (plan ``plan-phase02FxCentralBanks.prompt.md``, study ``studio-BCB.md``; developer decisions
16/11/2026: feed C under the PTAX dataset's ODbL, SLL stored as SLE ÷ 1000). Measured on the real feed:

- ``ptax_internet/consultaBoletim.do?method=gerarCSVFechamentoMoedaNoPeriodo&ChkMoeda=<id>&DATAINI=dd/mm/yyyy
  &DATAFIM=dd/mm/yyyy`` answers a CSV with no header, one row per Brazilian business day:
  ``ddmmyyyy;<BCB code>;<A|B>;<symbol>;<cotação compra>;<cotação venda>;<paridade compra>;<paridade venda>``, decimal
  comma, the BCB code without leading zeros (``5`` for AFN), the SDR written ``XDR``.
- Type A: paridade = units per 1 USD; type B: USD per 1 unit; cotação = BRL per 1 unit. The type is read row by row
  (NGN was B until 04/08/1998).
- No data in the range (a weekend, an unknown id) is HTTP 200 with an HTML page (``msgErro``, «Não existe informação
  para a pesquisa efetuada!»).
- SLL is published in old leones: 22 683–22 908 per USD on 13/11/2026; 1 SLE = 1 000 SLL.

Every answer here is synthetic, written by hand in the feed's shape, never data downloaded from the bank.

Isolation: PURE. ``fetch_rates`` runs whole, its module's ``httpx`` replaced for the test by the real module whose
``AsyncClient`` answers through an ``httpx.MockTransport`` (``_route``, from ``test_rate_limit_http_providers.py``);
the pause between requests is set to zero.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import httpx
import pytest
from structlog.testing import capture_logs

from backend.app.services.fx.base import FXRateLimitedError
from backend.app.services.fx_providers.bcb import plugin as bcb_mod
from backend.app.services.fx_providers.bcb.plugin import SLL_PER_SLE, BCBProvider
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

RANGE = (date(2026, 11, 9), date(2026, 11, 13))

#: ChkMoeda id -> rows, in the feed's shape (synthetic values).
USD_ROWS = ["13112026;220;A;USD;5,6512;5,6518;1,0000;1,0000"]
NGN_ROWS = ["13112026;630;A;NGN;0,004175;0,004189;1345,0000;1345,6000"]
EUR_ROWS = ["13112026;978;B;EUR;6,2321;6,2334;1,1028;1,1029"]
SLL_ROWS = ["13112026;500;A;SLL;0,000247;0,000248;22683,0000;22908,0000"]
XDR_ROWS = ["13112026;138;B;XDR;7,5705;7,5713;1,3559;1,3559"]
BY_ID = {61: USD_ROWS, 138: NGN_ROWS, 222: EUR_ROWS, 107: SLL_ROWS, 41: XDR_ROWS}

NO_DATA_PAGE = '<html><head><title>Cotações</title></head><body><div class="msgErro">Não existe informação para a pesquisa efetuada!</div></body></html>'


@pytest.fixture(autouse=True)
def _no_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(BCBProvider, "PAUSE_SECONDS", 0.0)


def _csv(rows: list[str]) -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "application/vnd.ms-excel"}, text="\n".join(rows) + "\n")


def _html(body: str = NO_DATA_PAGE) -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "text/html;charset=ISO-8859-1"}, content=body.encode("latin-1"))


def _by_id(rows_by_id: dict[int, list[str]] = BY_ID):
    return lambda request: _csv(rows_by_id[int(request.url.params["ChkMoeda"])]) if int(request.url.params["ChkMoeda"]) in rows_by_id else _html()


# ── Direction: types A and B, BRL, SLL, the SDR ──────────────────────────────────


@pytest.mark.asyncio
async def test_bcb_type_a_is_units_per_usd_and_type_b_usd_per_unit(monkeypatch: pytest.MonkeyPatch):
    """Type A (NGN): «1 USD = 1345.3 NGN», the mean of the paridade compra and venda. Type B (EUR): «1 EUR = 1.10285 USD».
    Never the other way round (the FED mistake of wave 0)."""
    _route(monkeypatch, bcb_mod, _by_id())

    rates = await BCBProvider().fetch_rates(RANGE, ["NGN", "EUR"])

    assert rates["NGN"] == [(date(2026, 11, 13), "USD", "NGN", Decimal("1345.3"))]
    assert rates["EUR"] == [(date(2026, 11, 13), "EUR", "USD", Decimal("1.10285"))]


@pytest.mark.asyncio
async def test_bcb_brl_is_the_mean_cotacao_of_the_dollar(monkeypatch: pytest.MonkeyPatch):
    """BRL comes from the USD series' cotação (BRL per 1 USD): «1 USD = 5.6515 BRL»."""
    asked = _route(monkeypatch, bcb_mod, _by_id())

    rates = await BCBProvider().fetch_rates(RANGE, ["BRL"])

    assert [int(r.url.params["ChkMoeda"]) for r in asked] == [61]
    assert rates["BRL"] == [(date(2026, 11, 13), "USD", "BRL", Decimal("5.6515"))]


@pytest.mark.asyncio
async def test_bcb_stores_sll_as_sle_divided_by_1000(monkeypatch: pytest.MonkeyPatch):
    """BCB publishes the leone in old SLL (22 795.5 per USD); the ISO list has only SLE: stored as «1 USD = 22.7955 SLE»."""
    asked = _route(monkeypatch, bcb_mod, _by_id())

    rates = await BCBProvider().fetch_rates(RANGE, ["SLE"])

    assert SLL_PER_SLE == Decimal(1000)
    assert [int(r.url.params["ChkMoeda"]) for r in asked] == [107]
    assert rates["SLE"] == [(date(2026, 11, 13), "USD", "SLE", Decimal("22.7955"))]
    assert "SLL" not in await BCBProvider().get_supported_currencies()


@pytest.mark.asyncio
async def test_bcb_reads_the_sdr_as_xdr(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, bcb_mod, _by_id())

    rates = await BCBProvider().fetch_rates(RANGE, ["XDR"])

    assert rates["XDR"] == [(date(2026, 11, 13), "XDR", "USD", Decimal("1.3559"))]


def test_bcb_reads_the_type_of_each_row():
    """A currency whose type changed (NGN: B until 04/08/1998, A after): the type comes from each row, never from a
    table, so each row is turned in its own direction. (Read with the parser: ``fetch_rates`` asks nothing before 1999.)"""
    rows = "03081998;630;B;NGN;0,0001;0,0001;0,0117;0,0117\n05081998;630;A;NGN;0,013;0,013;85,5000;85,5000\n"

    rates = BCBProvider._to_rates(BCBProvider._read_rows(rows, BCBProvider.SERIES["NGN"], date(1998, 8, 1), date(1998, 8, 10)), "NGN", BCBProvider.SERIES["NGN"])

    assert rates == [(date(1998, 8, 3), "NGN", "USD", Decimal("0.0117")), (date(1998, 8, 5), "USD", "NGN", Decimal("85.5"))]


# ── Requests, history, days ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bcb_asks_one_range_per_currency_in_series(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, bcb_mod, _by_id())

    rates = await BCBProvider().fetch_rates(RANGE, ["NGN", "USD", "EUR"])

    assert [int(r.url.params["ChkMoeda"]) for r in asked] == [222, 138], "sorted by currency; USD is the base, no request"
    for request in asked:
        assert request.url.params["method"] == "gerarCSVFechamentoMoedaNoPeriodo"
        assert (request.url.params["DATAINI"], request.url.params["DATAFIM"]) == ("09/11/2026", "13/11/2026")
    assert set(rates) == {"NGN", "EUR"}


@pytest.mark.asyncio
async def test_bcb_asks_from_1999_and_ves_from_its_redenomination(monkeypatch: pytest.MonkeyPatch):
    """History from 01/02/1999 (two bulletins a day and cotação not in reais before); VES from 04/10/2021 (÷10⁶ inside the
    same code). A range ending before the currency's first day makes no request."""
    asked = _route(monkeypatch, bcb_mod, lambda request: _csv([]))

    await BCBProvider().fetch_rates(("min", date(2026, 11, 13)), ["NGN"])
    await BCBProvider().fetch_rates((date(2020, 1, 1), date(2026, 11, 13)), ["VES"])
    nothing = await BCBProvider().fetch_rates((date(2020, 1, 1), date(2021, 10, 1)), ["VES"])

    assert [r.url.params["DATAINI"] for r in asked] == ["01/02/1999", "04/10/2021"]
    assert nothing == {"VES": []}


@pytest.mark.asyncio
async def test_bcb_keeps_rows_in_range_under_their_day_and_drops_the_others(monkeypatch: pytest.MonkeyPatch):
    """D2: every row under its date; a row outside the asked range is ignored; a date seen twice loses that day."""
    rows = [
        "06112026;630;A;NGN;0,0041;0,0041;1340,0000;1340,0000",
        "10112026;630;A;NGN;0,0041;0,0041;1341,0000;1341,0000",
        "11112026;630;A;NGN;0,0041;0,0041;1342,0000;1342,0000",
        "11112026;630;A;NGN;0,0041;0,0041;1343,0000;1343,0000",
        "12112026;630;A;NGN;0,0041;0,0041;1344,0000;1344,0000",
    ]
    _route(monkeypatch, bcb_mod, _by_id({138: rows}))

    rates = await BCBProvider().fetch_rates(RANGE, ["NGN"])

    assert [(r[0], r[3]) for r in rates["NGN"]] == [(date(2026, 11, 10), Decimal("1341")), (date(2026, 11, 12), Decimal("1344"))]


@pytest.mark.asyncio
async def test_bcb_unreadable_or_zero_value_loses_only_its_day(monkeypatch: pytest.MonkeyPatch):
    rows = ["10112026;630;A;NGN;0,0041;0,0041;0,0000;0,0000", "11112026;630;A;NGN;0,0041;0,0041;n/d;1342,0000", "12112026;630;A;NGN;0,0041;0,0041;1344,0000;1344,0000"]
    _route(monkeypatch, bcb_mod, _by_id({138: rows}))

    rates = await BCBProvider().fetch_rates(RANGE, ["NGN"])

    assert rates["NGN"] == [(date(2026, 11, 12), "USD", "NGN", Decimal("1344"))]


# ── The no-data page and what it refuses ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_bcb_no_data_page_on_a_short_range_is_no_rate(monkeypatch: pytest.MonkeyPatch):
    """Under 7 days (a weekend, Carnival) the msgErro page means no bulletin: empty, no warning."""
    _route(monkeypatch, bcb_mod, lambda request: _html())

    with capture_logs() as events:
        rates = await BCBProvider().fetch_rates((date(2026, 11, 14), date(2026, 11, 15)), ["NGN"])

    assert rates == {"NGN": []}
    assert not [e for e in events if e.get("log_level") == "warning"]


#: Answers that must skip the currency with one warning (XRL-H09), never store a rate. The first: seven days or more with
#: no bulletin means the ChkMoeda id has probably changed — it must not look like an empty period.
_REFUSED = [
    pytest.param(lambda: _html(), id="no-data-on-a-long-range"),
    pytest.param(lambda: _html("<html><body><h1>Erro interno</h1></body></html>"), id="other-html"),
    pytest.param(lambda: _csv(["13112026;630;A;NGN;0,004;0,004;1345,0"]), id="seven-fields"),
    pytest.param(lambda: _csv(["13112026;978;B;EUR;6,2;6,2;1,1;1,1"]), id="another-currency-code"),
    pytest.param(lambda: _csv(["13112026;630;A;NGX;0,004;0,004;1345,0;1345,0"]), id="another-symbol"),
    pytest.param(lambda: _csv(["13112026;630;C;NGN;0,004;0,004;1345,0;1345,0"]), id="unknown-type"),
    pytest.param(lambda: _csv(["2026-11-13;630;A;NGN;0,004;0,004;1345,0;1345,0"]), id="date-format"),
    pytest.param(lambda: httpx.Response(500, text="erro"), id="server-error"),
]


@pytest.mark.parametrize("answer", _REFUSED)
@pytest.mark.asyncio
async def test_bcb_skips_a_currency_whose_answer_is_not_its_csv(monkeypatch: pytest.MonkeyPatch, answer):
    _route(monkeypatch, bcb_mod, lambda request: answer() if int(request.url.params["ChkMoeda"]) == 138 else _csv(EUR_ROWS))

    with capture_logs() as events:
        rates = await BCBProvider().fetch_rates((date(2026, 11, 2), date(2026, 11, 13)), ["NGN", "EUR"])

    assert rates["NGN"] == [], f"BCB returned {rates['NGN']} from an answer that is not NGN's CSV"
    assert rates["EUR"] == [(date(2026, 11, 13), "EUR", "USD", Decimal("1.10285"))]
    warnings = [e for e in events if e.get("log_level") == "warning" and "NGN" in str(e)]
    assert len(warnings) == 1, f"expected one warning for NGN, got {events}"


@pytest.mark.asyncio
async def test_bcb_too_many_requests_is_a_rate_limit(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, bcb_mod, lambda request: httpx.Response(429, headers={"Retry-After": "60"}))

    with pytest.raises(FXRateLimitedError):
        await BCBProvider().fetch_rates(RANGE, ["NGN", "EUR"])


# ── Catalogue and texts ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bcb_catalogue_is_the_fixed_table(monkeypatch: pytest.MonkeyPatch):
    """The ChkMoeda table is fixed in the plugin: no request; USD (base) and BRL are listed; MRO (stale), XAU (per gram)
    and CNH (not ISO) are not; SLE stands for BCB's SLL."""
    asked = _route(monkeypatch, bcb_mod, lambda request: _html())

    currencies = await BCBProvider().get_supported_currencies()

    assert asked == []
    assert {"USD", "BRL", "NGN", "EUR", "SLE", "XDR", "VES"} <= set(currencies)
    assert not {"MRO", "XAU", "CNH", "SLL", "SDR"} & set(currencies)


def test_bcb_identity_and_texts():
    provider = BCBProvider()
    assert (provider.code, provider.base_currency) == ("BCB", "USD")
    for texts in (provider.description_i18n, provider.warning_i18n):
        assert set(texts) == {"en", "it", "fr", "es"} and all(texts.values())
    for text in provider.description_i18n.values():
        assert "Banco Central do Brasil, PTAX, ODbL" in text, "the ODbL attribution, word for word, in every language"
        assert "Refinitiv" in text
