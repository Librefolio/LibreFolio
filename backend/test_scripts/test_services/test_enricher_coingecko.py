"""The CoinGecko enricher (lane 82, lot CG-B): ``enricher_providers/coingecko/plugin.py``, class ``CoinGeckoEnricher``,
on CoinGecko's official SDK behind the shared door ``services/coingecko/sdk.py``.

The contract pinned here, with no network:

1. **Declarations**: ``code`` ``coingecko``, ``name`` ``CoinGecko``, ``terms`` ``SELF_HOSTED``, ``COINGECKO_ID`` only,
   the settings group ``coingecko``; covers ``CRYPTO`` only (degree 10, ``None`` for every other type), voices
   ``description``, ``website``, ``inception_date``, ``market_cap``, ``crypto_categories``; one parameter ``vs_currency``
   (select over ``VS_CURRENCIES``, default EUR); search on; calls out; not test-only.
2. **recognize**: a coin CoinGecko knows is found, with its name and its page (``coingecko.com/en/coins/<id>``); a 404 is
   «not found», never an error; another identifier type or an id that cannot be CoinGecko's (``../x``, blank) is not found
   and asks nothing; a 429 raises ``AssetRateLimitedError`` with its ``retry_after``; another 5xx raises
   ``AssetSourceError``; the key is in no text of any error.
3. **read**: ``/coins/{id}`` once per coin, ``market_data=true`` (recognize: false) among the flags; ``description`` as plain text (tags
   removed, entities read, ``\\r\\n`` as ``\\n``, blank absent), ``website`` the first ``http(s)`` home page (blank,
   non-string, ``javascript:`` and ``ftp:`` skipped), ``inception_date`` the ISO genesis day (a malformed one, or none,
   leaves the voice out); a 404 is ``NOT_FOUND``; a 429 is ``RATE_LIMITED`` with its ``retry_after`` for that coin and
   for every later one with no request; another failure is that coin's ``SOURCE_ERROR`` (``error_message`` the class
   name) only; items come in the bindings' order; every value is in the catalogue's stored form.
4. **search**: ``/search`` coins sorted by ``market_cap_rank`` (a coin with no rank last), ``Name (SYMBOL)`` rows bound by
   ``COINGECKO_ID`` + id, ``CRYPTO``, with the page; a coin with a bad id is dropped, one with no symbol is the name
   alone; at most 20; a blank text asks nothing; a 429 raises ``EnricherRateLimited`` with its ``retry_after``.
5. **The pace**: the module's ``_PACER`` waits before each request of recognize, read and search.
6. **No key**: ``NOT_CONFIGURED`` and no request. The plan picks the API root (Demo or Pro), as for the price plugin.
7. **Core integration**: with the registry serving it (``LIBREFOLIO_ENRICHERS_ENABLED``), ``default_order(CRYPTO)`` is
   ``["coingecko"]``; the price assignment as a seed asks it first, keeps the declared ``vs_currency`` and drops any
   undeclared parameter.
8. **market_cap** (read only): the capitalisation in the binding's ``vs_currency`` (any case, EUR when missing or blank),
   exact, currency upper-case; a currency outside ``VS_CURRENCIES``, null, non-number, boolean, zero or negative leaves the
   voice out (never another currency); ``source_dates["market_cap"]`` is the UTC day of ``market_data.last_updated``.
9. **crypto_categories** (CG-D): every category, the source's words and order, joined by «; »; what is not a word is skipped,
   none leaves the voice out.

Pure: the real SDK on an ``httpx.MockTransport`` (recorded bodies of ``fixtures/coingecko/``), no database, no server.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

import httpx
import pytest

from backend.app.db.models import AssetType
from backend.app.services.assets.base import AssetRateLimitedError, AssetSourceError
from backend.app.services.assets.profile.catalogue import normalize_value
from backend.app.services.coingecko import sdk
from backend.app.services.coingecko.currencies import DEFAULT_VS_CURRENCY, VS_CURRENCIES
from backend.app.services.enricher_providers.coingecko import plugin as module
from backend.app.services.enricher_providers.coingecko.plugin import CoinGeckoEnricher
from backend.app.services.enrichers.base import RATE_LIMITED, EnricherBinding, EnricherRateLimited, EnricherReadStatus, EnricherTerms
from backend.app.services.enrichers.bindings import default_order
from backend.app.services.enrichers.recognize import Recognized, RecognizeStatus, Seed, recognize_cascade
from backend.app.utils.runtime.pacing import Pacer

_ORIGINAL_PACER = module._PACER
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "coingecko"
KEY = "CG-enr-test-0123456789abcdefKEY"
ROOTS = {"demo": "api.coingecko.com", "pro": "pro-api.coingecko.com"}


def _body(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))["body"]


class _Group:
    def __init__(self, key: str | None, plan: str) -> None:
        self._key, self._plan = key, plan

    def secret(self, name: str) -> str | None:
        return self._key if name == "api_key" else None

    def get(self, name: str):
        return self._plan if name == "plan" else None


class _Bound:
    def __init__(self, key: str | None, plan: str) -> None:
        self._group = _Group(key, plan)

    def group(self, name: str) -> _Group:
        assert name == "coingecko"
        return self._group


class _Wire:
    """A fake CoinGecko: every request recorded; ``routes`` maps a path to (status, body, headers), 200 otherwise."""

    def __init__(self) -> None:
        self.routes: dict[str, tuple[int, object, dict]] = {}
        self.requests: list[httpx.Request] = []

    def answer(self, path: str, body: object, status: int = 200, headers: dict | None = None) -> None:
        self.routes[path] = (status, body, headers or {})

    def coin(self, coin: str, body: object, status: int = 200, headers: dict | None = None) -> None:
        self.answer(f"/api/v3/coins/{coin}", body, status, headers)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = urlparse(str(request.url)).path
        path = path if path.startswith("/api/v3") else "/api/v3" + path
        if path not in self.routes:
            pytest.fail(f"the plugin asked {request.url!s}, which no test answered")
        status, body, headers = self.routes[path]
        return httpx.Response(status, json=body, headers=headers)

    @property
    def paths(self) -> list[str]:
        return [request.url.path for request in self.requests]


class _Pace:
    def __init__(self) -> None:
        self.events: list[str] = []

    def wait(self) -> None:
        self.events.append("wait")


def _make(monkeypatch: pytest.MonkeyPatch, wire: _Wire, *, key: str | None = KEY, plan: str = "demo") -> CoinGeckoEnricher:
    plugin = CoinGeckoEnricher()
    plugin.bind_settings(_Bound(key, plan))  # type: ignore[arg-type]
    monkeypatch.setattr(CoinGeckoEnricher, "_http_client", httpx.Client(transport=httpx.MockTransport(wire)))
    return plugin


@pytest.fixture(autouse=True)
def pace(monkeypatch: pytest.MonkeyPatch) -> _Pace:
    fake = _Pace()
    monkeypatch.setattr(module, "_PACER", fake, raising=True)
    return fake


@pytest.fixture
def wire() -> _Wire:
    return _Wire()


def binding(identifier: str, identifier_type: str = "COINGECKO_ID", **params) -> EnricherBinding:
    return EnricherBinding(identifier_type=identifier_type, identifier=identifier, params=params)


def _texts(error: BaseException) -> str:
    parts: list[str] = []
    seen: BaseException | None = error
    while seen is not None:
        parts += [str(seen), repr(getattr(seen, "details", ""))]
        seen = seen.__cause__ or seen.__context__
    return " ".join(parts)


def _profile(coin: str, **fields) -> dict:
    """A synthetic ``/coins/{id}`` body, with the fields a test sets."""
    return {"id": coin, "name": coin.title(), **fields}


def _accepted(key: str, value) -> None:
    """The catalogue accepts the emitted value; a text is already in its stored form, an amount is the same number."""
    stored = normalize_value(key, value)
    if isinstance(value, dict):
        assert set(stored) == set(value) and stored["currency"] == value["currency"] and Decimal(str(stored["amount"])) == Decimal(str(value["amount"])), (key, value, stored)
    else:
        assert stored == value, f"{key} is in the catalogue's stored form: {value!r}"


def _read_one(plugin: CoinGeckoEnricher, coin: str):
    [item] = list(plugin.read([binding(coin)]))
    return item


# =============================================================================
# 1. Declarations
# =============================================================================


def test_declarations():
    plugin = CoinGeckoEnricher()
    assert (plugin.code, plugin.name) == ("coingecko", "CoinGecko")
    assert plugin.terms is EnricherTerms.SELF_HOSTED
    assert tuple(plugin.accepted_identifier_types) == ("COINGECKO_ID",)
    assert tuple(plugin.settings_groups) == ("coingecko",)
    assert set(plugin.default_priority) == set(AssetType), "a degree for every type, None written out"
    assert plugin.default_priority[AssetType.CRYPTO] == 10
    assert {asset_type for asset_type, degree in plugin.default_priority.items() if degree is not None} == {AssetType.CRYPTO}
    assert all(degree is None for asset_type, degree in plugin.default_priority.items() if asset_type != AssetType.CRYPTO)
    assert plugin.covers(AssetType.CRYPTO) and not plugin.covers(AssetType.STOCK)
    assert plugin.voices == {AssetType.CRYPTO: frozenset({"description", "website", "inception_date", "market_cap", "crypto_categories"})}
    [param] = plugin.params_schema
    assert (param["key"], param["type"], param["default"], list(param["options"])) == ("vs_currency", "select", "EUR", list(VS_CURRENCIES))
    assert DEFAULT_VS_CURRENCY == "EUR" and not param.get("required")
    assert param["x-i18n-key"] == "enrichers.coingecko.params.vs_currency"
    assert plugin.supports_search is True
    assert plugin.calls_external_service is True
    assert getattr(plugin, "test_only", False) is False
    assert [case["binding"]["identifier_type"] for case in plugin.test_cases] == ["COINGECKO_ID"]


def test_the_page_of_a_coin():
    plugin = CoinGeckoEnricher()
    assert plugin.page_url(binding("bitcoin")) == "https://www.coingecko.com/en/coins/bitcoin"
    assert plugin.page_url(binding("bitcoin", "TICKER")) is None
    assert plugin.page_url(binding("../x")) is None


# =============================================================================
# 2. recognize
# =============================================================================


def test_recognize_finds_a_coin_with_its_name_and_page(monkeypatch, wire):
    wire.coin("bitcoin", _body("coin_profile_bitcoin.json"))
    recognition = _make(monkeypatch, wire).recognize(binding("bitcoin"))
    assert recognition.found is True
    assert recognition.name == "Bitcoin"
    assert recognition.page_url == "https://www.coingecko.com/en/coins/bitcoin"
    assert wire.paths[0].endswith("/coins/bitcoin") and len(wire.paths) == 1


def test_recognize_an_unknown_coin_is_not_found_not_an_error(monkeypatch, wire):
    wire.coin("librefolio-no-such-coin", _body("coin_profile_unknown.json"), status=404)
    recognition = _make(monkeypatch, wire).recognize(binding("librefolio-no-such-coin"))
    assert recognition.found is False and recognition.name is None


@pytest.mark.parametrize(("identifier", "identifier_type"), [("bitcoin", "TICKER"), ("bitcoin", "ISIN"), ("../x", "COINGECKO_ID"), ("a/b", "COINGECKO_ID"), ("", "COINGECKO_ID"), ("   ", "COINGECKO_ID")])
def test_recognize_what_cannot_be_a_coin_asks_nothing(monkeypatch, wire, identifier, identifier_type):
    plugin = _make(monkeypatch, wire)
    assert plugin.recognize(binding(identifier, identifier_type)).found is False
    assert wire.requests == []


def test_recognize_a_429_raises_with_its_wait(monkeypatch, wire):
    wire.coin("bitcoin", {"status": {"error_code": 429}}, status=429, headers={"Retry-After": "30"})
    with pytest.raises(AssetRateLimitedError) as raised:
        _make(monkeypatch, wire).recognize(binding("bitcoin"))
    assert raised.value.retry_after == 30.0
    assert len(wire.requests) == 1, "no retry"
    assert KEY not in _texts(raised.value)


def test_recognize_another_5xx_raises_a_source_error_without_the_key(monkeypatch, wire):
    wire.coin("bitcoin", {"error": "boom"}, status=503)
    with pytest.raises(AssetSourceError) as raised:
        _make(monkeypatch, wire).recognize(binding("bitcoin"))
    assert not isinstance(raised.value, AssetRateLimitedError)
    assert KEY not in _texts(raised.value)
    assert raised.value.details["http_status"] == 503
    assert len(wire.requests) == 1


# =============================================================================
# 3. read
# =============================================================================


def _values(plugin: CoinGeckoEnricher, coin: str) -> dict:
    item = _read_one(plugin, coin)
    assert item.status is EnricherReadStatus.OK, item
    for key, value in item.values.items():
        _accepted(key, value)
    return dict(item.values)


def test_read_bitcoin(monkeypatch, wire):
    wire.coin("bitcoin", _body("coin_profile_bitcoin.json"))
    values = _values(_make(monkeypatch, wire), "bitcoin")
    assert set(values) == {"description", "website", "inception_date", "market_cap", "crypto_categories"}
    assert values["market_cap"] == {"amount": 1319697636284, "currency": "EUR"}
    assert values["website"] == "http://www.bitcoin.org"
    assert values["inception_date"] == "2009-01-03"
    assert values["description"].startswith("Bitcoin is the world's first decentralized cryptocurrency")
    assert "<" not in values["description"] and "\r" not in values["description"]


@pytest.mark.parametrize(("coin", "fixture", "website"), [("pepe", "coin_profile_pepe.json", "https://www.pepe.vip/"), ("usd-coin", "coin_profile_usd_coin.json", "https://www.circle.com/en/usdc")])
def test_read_a_token_has_no_inception_date(monkeypatch, wire, coin, fixture, website):
    wire.coin(coin, _body(fixture))
    values = _values(_make(monkeypatch, wire), coin)
    assert "inception_date" not in values
    assert values["website"] == website
    assert values["description"]


def test_read_an_unknown_coin_is_not_found(monkeypatch, wire):
    wire.coin("librefolio-no-such-coin", _body("coin_profile_unknown.json"), status=404)
    assert _read_one(_make(monkeypatch, wire), "librefolio-no-such-coin").status is EnricherReadStatus.NOT_FOUND


def test_read_asks_once_per_coin_with_market_data(monkeypatch, wire):
    wire.coin("bitcoin", _body("coin_profile_bitcoin.json"))
    wire.coin("pepe", _body("coin_profile_pepe.json"))
    items = list(_make(monkeypatch, wire).read([binding("bitcoin"), binding("pepe")]))
    assert [item.status for item in items] == [EnricherReadStatus.OK, EnricherReadStatus.OK]
    assert len(wire.requests) == 2, "one request per coin"
    assert [request.url.path.rsplit("/", 1)[-1] for request in wire.requests] == ["bitcoin", "pepe"]
    for request in wire.requests:
        params = dict(request.url.params)
        assert params["market_data"] == "true"
        assert {params[flag] for flag in ("localization", "tickers", "community_data", "developer_data", "sparkline")} == {"false"}


def test_read_keeps_the_order_and_marks_what_is_not_asked(monkeypatch, wire):
    wire.coin("bitcoin", _body("coin_profile_bitcoin.json"))
    items = list(_make(monkeypatch, wire).read([binding("ethereum", "TICKER"), binding("bitcoin"), binding("../x")]))
    assert [item.index for item in items] == [0, 1, 2]
    assert [item.status for item in items] == [EnricherReadStatus.NOT_FOUND, EnricherReadStatus.OK, EnricherReadStatus.NOT_FOUND]
    assert len(wire.requests) == 1


@pytest.mark.parametrize("genesis", ["not-a-date", "2009-13-45", "", "   ", 20090103, None])
def test_read_a_malformed_genesis_leaves_the_voice_out(monkeypatch, wire, genesis):
    wire.coin("xcoin", _profile("xcoin", genesis_date=genesis, links={"homepage": ["https://x.example"]}))
    values = _values(_make(monkeypatch, wire), "xcoin")
    assert "inception_date" not in values
    assert values["website"] == "https://x.example"


@pytest.mark.parametrize(
    ("homepage", "expected"),
    [
        (["", "  ", "https://good.example"], "https://good.example"),
        ([None, 5, {"a": 1}, "http://second.example"], "http://second.example"),
        (["javascript:alert(1)", "ftp://files.example", "https://after.example"], "https://after.example"),
        (["javascript:alert(1)", "ftp://files.example"], None),
        (["not an address", "https://has space.example"], None),
        (["", ""], None),
        ([], None),
        ("https://string-not-list.example", None),
        (None, None),
    ],
)
def test_read_the_website_is_the_first_http_address(monkeypatch, wire, homepage, expected):
    wire.coin("xcoin", _profile("xcoin", links={"homepage": homepage}))
    values = _values(_make(monkeypatch, wire), "xcoin")
    if expected is None:
        assert "website" not in values
    else:
        assert values["website"] == expected


def test_read_a_body_with_no_links_has_no_website(monkeypatch, wire):
    wire.coin("xcoin", _profile("xcoin", description={"en": "Plain."}))
    assert _values(_make(monkeypatch, wire), "xcoin") == {"description": "Plain."}


def test_read_the_description_is_plain_text(monkeypatch, wire):
    raw = 'Fast &amp; <b>cheap</b>, see <a href="https://x.example">the site</a>.\r\nSecond &quot;line&quot; &lt;kept&gt;\r\n'
    wire.coin("xcoin", _profile("xcoin", description={"en": raw}))
    description = _values(_make(monkeypatch, wire), "xcoin")["description"]
    assert description == 'Fast & cheap, see the site.\nSecond "line" <kept>'
    assert "\r" not in description


@pytest.mark.parametrize("description", [{"en": ""}, {"en": "   \r\n  "}, {"en": "<p> </p>"}, {"en": None}, {"it": "solo italiano"}, {}, "text", None])
def test_read_a_blank_description_is_absent(monkeypatch, wire, description):
    wire.coin("xcoin", _profile("xcoin", description=description, genesis_date="2020-02-29"))
    values = _values(_make(monkeypatch, wire), "xcoin")
    assert "description" not in values
    assert values["inception_date"] == "2020-02-29"


@pytest.mark.parametrize("fixture", ["coin_profile_bitcoin.json", "coin_profile_pepe.json", "coin_profile_usd_coin.json"])
def test_the_categories_are_all_of_the_sources_words_in_its_order(monkeypatch, wire, fixture):
    body = _body(fixture)
    wire.coin("xcoin", body)
    text = _values(_make(monkeypatch, wire), "xcoin")["crypto_categories"]
    assert body["categories"] and text.split("; ") == body["categories"], "none dropped, mapped or reordered"


def test_the_categories_of_pepe_read_as_one_text(monkeypatch, wire):
    wire.coin("pepe", _body("coin_profile_pepe.json"))
    expected = "BNB Chain Ecosystem; Avalanche Ecosystem; Meme; Arbitrum Ecosystem; Ethereum Ecosystem; Frog-Themed; GMCI Meme Index; GMCI Index; The Boy’s Club; 4chan-Themed"
    assert _values(_make(monkeypatch, wire), "pepe")["crypto_categories"] == expected


def test_a_category_that_is_not_a_word_is_skipped(monkeypatch, wire):
    wire.coin("xcoin", _profile("xcoin", categories=[" Meme ", "", None, 7, "  ", ["x"], "Stablecoins"]))
    assert _values(_make(monkeypatch, wire), "xcoin") == {"crypto_categories": "Meme; Stablecoins"}


@pytest.mark.parametrize("listed", [[], [""], [None, "  "], None, "Meme", {"0": "Meme"}, 3])
def test_no_usable_category_is_absent(monkeypatch, wire, listed):
    wire.coin("xcoin", _profile("xcoin", categories=listed, genesis_date="2020-02-29"))
    assert _values(_make(monkeypatch, wire), "xcoin") == {"inception_date": "2020-02-29"}


def test_a_body_without_categories_has_none(monkeypatch, wire):
    wire.coin("xcoin", _profile("xcoin", genesis_date="2020-02-29"))
    assert _values(_make(monkeypatch, wire), "xcoin") == {"inception_date": "2020-02-29"}


def test_read_a_body_without_an_id_is_not_found(monkeypatch, wire):
    wire.coin("xcoin", {"name": "No id"})
    assert _read_one(_make(monkeypatch, wire), "xcoin").status is EnricherReadStatus.NOT_FOUND


def test_read_a_429_refuses_the_rest_with_one_request(monkeypatch, wire):
    wire.coin("pepe", {"status": {"error_code": 429}}, status=429, headers={"Retry-After": "12"})
    items = list(_make(monkeypatch, wire).read([binding("pepe"), binding("bitcoin"), binding("usd-coin")]))
    assert [item.index for item in items] == [0, 1, 2]
    assert all(item.status is EnricherReadStatus.ERROR and item.error_code == RATE_LIMITED and item.retry_after == 12.0 for item in items)
    assert len(wire.requests) == 1, "after a refusal no more requests"


def test_read_another_failure_is_only_its_own(monkeypatch, wire):
    wire.coin("pepe", {"oops": 1}, status=500)
    wire.coin("bitcoin", _body("coin_profile_bitcoin.json"))
    items = list(_make(monkeypatch, wire).read([binding("pepe"), binding("bitcoin")]))
    assert (items[0].status, items[0].error_code) == (EnricherReadStatus.ERROR, module.SOURCE_ERROR)
    assert items[0].error_message == "AssetSourceError"
    assert KEY not in (items[0].error_message or "")
    assert items[1].status is EnricherReadStatus.OK
    assert len(wire.requests) == 2


# =============================================================================
# 3b. market_cap
# =============================================================================


def _cap_body(**market_data) -> dict:
    return _profile("xcoin", market_data=market_data)


def _cap(plugin: CoinGeckoEnricher, params: dict | None = None):
    [item] = list(plugin.read([binding("xcoin", **(params or {}))]))
    assert item.status is EnricherReadStatus.OK, item
    for key, value in item.values.items():
        _accepted(key, value)
    return item


@pytest.mark.parametrize(
    ("params", "amount", "currency"),
    [
        (None, 1319697636284, "EUR"),
        ({}, 1319697636284, "EUR"),
        ({"vs_currency": ""}, 1319697636284, "EUR"),
        ({"vs_currency": "   "}, 1319697636284, "EUR"),
        ({"vs_currency": "EUR"}, 1319697636284, "EUR"),
        ({"vs_currency": "usd"}, 1472339488026, "USD"),
        ({"vs_currency": " Usd "}, 1472339488026, "USD"),
        ({"vs_currency": "CHF"}, 1216676569967, "CHF"),
    ],
)
def test_market_cap_of_bitcoin_in_the_asked_currency(monkeypatch, wire, params, amount, currency):
    wire.coin("xcoin", _body("coin_profile_bitcoin.json"))
    item = _cap(_make(monkeypatch, wire), params)
    assert item.values["market_cap"] == {"amount": amount, "currency": currency}
    assert item.source_dates == {"market_cap": date(2026, 11, 10)}


@pytest.mark.parametrize("currency", ["XXX", "BTC", "GOLD", "EU", "EURO", "12", "../x"])
def test_a_currency_that_is_not_coingeckos_leaves_the_voice_out(monkeypatch, wire, currency):
    wire.coin("xcoin", _body("coin_profile_bitcoin.json"))
    item = _cap(_make(monkeypatch, wire), {"vs_currency": currency})
    assert "market_cap" not in item.values and "market_cap" not in item.source_dates
    assert set(item.values) == {"description", "website", "inception_date", "crypto_categories"}, "the other voices stay"


def test_a_currency_the_body_lacks_is_absent_never_another(monkeypatch, wire):
    wire.coin("xcoin", _cap_body(market_cap={"usd": 5}, last_updated="2026-11-10T16:05:52.000Z"))
    item = _cap(_make(monkeypatch, wire), {"vs_currency": "EUR"})
    assert item.values == {} and item.source_dates == {}


@pytest.mark.parametrize("amount", [None, "123", "abc", True, False, 0, 0.0, -5, -1.5, [], {}])
def test_a_market_cap_that_is_no_positive_number_is_absent(monkeypatch, wire, amount):
    wire.coin("xcoin", _cap_body(market_cap={"eur": amount}, last_updated="2026-11-10T16:05:52.000Z"))
    item = _cap(_make(monkeypatch, wire))
    assert "market_cap" not in item.values and item.source_dates == {}


@pytest.mark.parametrize("market_data", [None, "x", [], {}, {"market_cap": None}, {"market_cap": "x"}, {"market_cap": []}])
def test_a_body_with_no_usable_market_data_has_no_market_cap(monkeypatch, wire, market_data):
    wire.coin("xcoin", _profile("xcoin", market_data=market_data))
    assert _cap(_make(monkeypatch, wire)).values == {}


def test_a_decimal_market_cap_is_exact_not_a_float(monkeypatch, wire):
    # the wire carries the digits CoinGecko wrote; a float would round them
    text = json.dumps(_profile("xcoin")).replace("}", ', "market_data": {"market_cap": {"eur": 1234567890123.456789}, "last_updated": "2026-11-10T16:05:52.000Z"}}')
    plugin = _make(monkeypatch, wire)
    transport = httpx.MockTransport(lambda request: (wire.requests.append(request), httpx.Response(200, content=text, headers={"content-type": "application/json"}))[1])
    monkeypatch.setattr(CoinGeckoEnricher, "_http_client", httpx.Client(transport=transport))
    item = _cap(plugin)
    amount = item.values["market_cap"]["amount"]
    assert isinstance(amount, Decimal) and amount == Decimal("1234567890123.456789")


@pytest.mark.parametrize(
    ("stamp", "day"),
    [
        ("2026-11-10T23:59:59.000Z", date(2026, 11, 10)),
        ("2026-11-10T23:30:00-05:00", date(2026, 11, 11)),
        ("2026-11-10T00:30:00+02:00", date(2026, 11, 9)),
        ("2026-11-10T16:05:52+00:00", date(2026, 11, 10)),
    ],
)
def test_the_market_day_is_the_utc_date(monkeypatch, wire, stamp, day):
    wire.coin("xcoin", _cap_body(market_cap={"eur": 10}, last_updated=stamp))
    assert _cap(_make(monkeypatch, wire)).source_dates == {"market_cap": day}


@pytest.mark.parametrize("stamp", [None, "", "yesterday", 5, "2026-13-45T00:00:00Z"])
def test_an_unreadable_market_day_leaves_the_date_out_not_the_amount(monkeypatch, wire, stamp):
    wire.coin("xcoin", _cap_body(market_cap={"eur": 10}, last_updated=stamp))
    item = _cap(_make(monkeypatch, wire))
    assert item.values["market_cap"] == {"amount": 10, "currency": "EUR"}
    assert item.source_dates == {}


def test_each_binding_of_a_read_uses_its_own_currency(monkeypatch, wire):
    wire.coin("bitcoin", _body("coin_profile_bitcoin.json"))
    wire.coin("pepe", _body("coin_profile_pepe.json"))
    items = list(_make(monkeypatch, wire).read([binding("bitcoin", vs_currency="usd"), binding("pepe")]))
    assert [item.values["market_cap"]["currency"] for item in items] == ["USD", "EUR"]


# =============================================================================
# 4. search
# =============================================================================


def test_search_pepe(monkeypatch, wire):
    wire.answer("/api/v3/search", _body("search_pepe.json"))
    results = _make(monkeypatch, wire).search("  pepe ")
    assert len(wire.requests) == 1 and dict(wire.requests[0].url.params) == {"query": "pepe"}
    assert 0 < len(results) <= 20
    assert results[0].name == "Pepe (PEPE)"
    assert results[0].binding == EnricherBinding(identifier_type="COINGECKO_ID", identifier="pepe")
    assert all(result.asset_type is AssetType.CRYPTO for result in results)
    assert all(result.binding.identifier_type == "COINGECKO_ID" for result in results)
    assert all(result.page_url == f"https://www.coingecko.com/en/coins/{result.binding.identifier}" for result in results)
    source = {coin["id"]: coin for coin in _body("search_pepe.json")["coins"]}
    assert all(result.binding.identifier in source for result in results)
    ranks = [source[result.binding.identifier]["market_cap_rank"] for result in results]
    ranked = [rank for rank in ranks if rank is not None]
    assert ranked == sorted(ranked)
    assert ranks == ranked + [None] * (len(ranks) - len(ranked)), "a coin with no rank is last"


def test_search_orders_by_rank_drops_bad_ids_and_names_without_symbol(monkeypatch, wire):
    coins = [
        {"id": "unranked", "name": "Unranked", "symbol": "unr", "market_cap_rank": None},
        {"id": "second", "name": "Second", "symbol": "two", "market_cap_rank": 20},
        {"id": "../evil", "name": "Evil", "symbol": "evl", "market_cap_rank": 1},
        {"id": "", "name": "Blank", "symbol": "blk", "market_cap_rank": 2},
        {"name": "No id", "symbol": "nid", "market_cap_rank": 3},
        {"id": "first", "name": "First", "symbol": "", "market_cap_rank": 5},
        {"id": "nameless", "symbol": "nmz", "market_cap_rank": 30},
    ]
    wire.answer("/api/v3/search", {"coins": coins})
    results = _make(monkeypatch, wire).search("x")
    assert [result.binding.identifier for result in results] == ["first", "second", "nameless", "unranked"]
    assert [result.name for result in results] == ["First", "Second (TWO)", "nameless (NMZ)", "Unranked (UNR)"]


def test_search_is_capped_at_twenty(monkeypatch, wire):
    wire.answer("/api/v3/search", {"coins": [{"id": f"coin-{n}", "name": f"Coin {n}", "symbol": f"c{n}", "market_cap_rank": 100 - n} for n in range(35)]})
    results = _make(monkeypatch, wire).search("coin")
    assert len(results) == 20
    assert results[0].binding.identifier == "coin-34", "the most capitalised first"


@pytest.mark.parametrize("body", [{}, {"coins": None}, {"coins": "x"}, [], {"coins": [1, None, "a"]}])
def test_search_a_strange_body_is_empty(monkeypatch, wire, body):
    wire.answer("/api/v3/search", body)
    assert _make(monkeypatch, wire).search("x") == []


@pytest.mark.parametrize("text", ["", "   ", "\n"])
def test_search_a_blank_text_asks_nothing(monkeypatch, wire, text):
    assert _make(monkeypatch, wire).search(text) == []
    assert wire.requests == []


def test_search_a_429_is_a_refusal_with_its_wait(monkeypatch, wire):
    wire.answer("/api/v3/search", {"status": {"error_code": 429}}, status=429, headers={"Retry-After": "45"})
    with pytest.raises(EnricherRateLimited) as raised:
        _make(monkeypatch, wire).search("pepe")
    assert raised.value.retry_after == 45.0
    assert KEY not in _texts(raised.value)
    assert len(wire.requests) == 1


def test_search_another_failure_raises_a_source_error(monkeypatch, wire):
    wire.answer("/api/v3/search", {}, status=500)
    with pytest.raises(AssetSourceError) as raised:
        _make(monkeypatch, wire).search("pepe")
    assert not isinstance(raised.value, (AssetRateLimitedError, EnricherRateLimited))


# =============================================================================
# 5. The pace
# =============================================================================


def test_every_request_is_paced_first(monkeypatch, wire, pace):
    wire.coin("bitcoin", _body("coin_profile_bitcoin.json"))
    wire.coin("pepe", _body("coin_profile_pepe.json"))
    wire.answer("/api/v3/search", _body("search_pepe.json"))
    plugin = _make(monkeypatch, wire)

    seen: list[tuple[int, int]] = []

    class Spy:
        def wait(self_inner) -> None:  # noqa: N805
            seen.append((len(wire.requests), len(pace.events)))
            pace.events.append("wait")

    monkeypatch.setattr(module, "_PACER", Spy(), raising=True)
    plugin.recognize(binding("bitcoin"))
    list(plugin.read([binding("bitcoin"), binding("pepe")]))
    plugin.search("pepe")
    assert len(wire.requests) == 4
    assert [requests_before for requests_before, _ in seen] == [0, 1, 2, 3], "each wait comes before its request"
    assert len(seen) == 4


def test_what_asks_nothing_does_not_wait(monkeypatch, wire, pace):
    plugin = _make(monkeypatch, wire)
    plugin.recognize(binding("../x"))
    list(plugin.read([binding("x", "TICKER")]))
    plugin.search("  ")
    assert pace.events == []


def test_the_pace_is_one_module_level_pacer():
    assert isinstance(_ORIGINAL_PACER, Pacer) and _ORIGINAL_PACER.interval_seconds > 0


# =============================================================================
# 6. No key, and the plan's root
# =============================================================================


def test_without_a_key_nothing_leaves(monkeypatch, wire):
    plugin = _make(monkeypatch, wire, key=None)
    with pytest.raises(AssetSourceError) as raised:
        plugin.recognize(binding("bitcoin"))
    assert raised.value.error_code == "NOT_CONFIGURED"
    with pytest.raises(AssetSourceError) as searched:
        plugin.search("pepe")
    assert searched.value.error_code == "NOT_CONFIGURED"
    [item] = list(plugin.read([binding("bitcoin")]))
    assert (item.status, item.error_code) == (EnricherReadStatus.ERROR, module.SOURCE_ERROR)
    assert wire.requests == []


@pytest.mark.parametrize("plan", ["demo", "pro"])
def test_the_plan_picks_the_root_and_the_key_travels_in_a_header(monkeypatch, wire, plan):
    wire.coin("bitcoin", _body("coin_profile_bitcoin.json"))
    plugin = CoinGeckoEnricher()
    plugin.bind_settings(_Bound(KEY, plan))  # type: ignore[arg-type]
    # the SDK builds its base url from the plan; the fake transport records what was asked
    monkeypatch.setattr(CoinGeckoEnricher, "_http_client", httpx.Client(transport=httpx.MockTransport(wire)))
    plugin.recognize(binding("bitcoin"))
    [request] = wire.requests
    assert request.url.host == ROOTS[plan]
    assert KEY not in str(request.url), "the key is never in the address"
    assert KEY in request.headers.values(), "the key travels in a header"


# =============================================================================
# 7. Core integration
# =============================================================================


def test_default_order_of_crypto_when_only_it_is_listed(monkeypatch):
    monkeypatch.setenv("LIBREFOLIO_ENRICHERS_ENABLED", "coingecko")
    assert default_order(AssetType.CRYPTO) == ["coingecko"]
    assert default_order(AssetType.STOCK) == []


def test_the_price_assignment_as_a_seed_asks_it_first_and_drops_the_undeclared_param(monkeypatch, wire):
    wire.coin("bitcoin", _body("coin_profile_bitcoin.json"))
    plugin = _make(monkeypatch, wire)
    asked: list[EnricherBinding] = []
    real = plugin.recognize

    def spy(asked_binding: EnricherBinding):
        asked.append(asked_binding)
        return real(asked_binding)

    monkeypatch.setattr(plugin, "recognize", spy)
    seed = Seed("coingecko", EnricherBinding("COINGECKO_ID", "bitcoin", {"vs_currency": "EUR"}))

    async def run() -> list:
        return [event async for event in recognize_cascade(AssetType.CRYPTO, {}, plugins=[plugin], seeds=[seed])]

    events = asyncio.run(run())
    recognized = [event for event in events if isinstance(event, Recognized)]
    assert [(event.code, event.status) for event in recognized] == [("coingecko", RecognizeStatus.FOUND)]
    assert recognized[0].name == "Bitcoin"
    assert [(b.identifier_type, b.identifier, dict(b.params)) for b in asked] == [("COINGECKO_ID", "bitcoin", {"vs_currency": "EUR"})], "asked first, the declared vs_currency kept"
    assert dict(wire.requests[0].url.params).get("vs_currency") is None, "the currency is read from the answer, never asked"
    assert dict(wire.requests[0].url.params)["market_data"] == "false", "recognize asks no market data"
    assert len(wire.requests) == 1


def test_a_seed_drops_an_undeclared_param_and_keeps_the_declared_one(monkeypatch, wire):
    wire.coin("bitcoin", _body("coin_profile_bitcoin.json"))
    plugin = _make(monkeypatch, wire)
    asked: list[EnricherBinding] = []
    real = plugin.recognize
    monkeypatch.setattr(plugin, "recognize", lambda b: (asked.append(b), real(b))[1])
    seed = Seed("coingecko", EnricherBinding("COINGECKO_ID", "bitcoin", {"vs_currency": "USD", "mic": "XMIL"}))

    async def run() -> list:
        return [event async for event in recognize_cascade(AssetType.CRYPTO, {}, plugins=[plugin], seeds=[seed])]

    asyncio.run(run())
    assert [dict(b.params) for b in asked] == [{"vs_currency": "USD"}]


def test_sdk_door_is_the_shared_one():
    assert module.sdk is sdk
    assert sdk.coin_id("bitcoin") == "bitcoin" and sdk.coin_id("../x") is None and sdk.coin_id("  ") is None
