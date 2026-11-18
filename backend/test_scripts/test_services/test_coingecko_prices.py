"""The CoinGecko provider, lot P2: current prices, in bulk too, the daily history, and how long a price stays fresh
(project 76; the P0 trial's recordings, journal ``76_cryptoPrices/prove/``).

The contract pinned here:

1. **A current price** asks ``/simple/price`` with ``ids=<id>``, ``vs_currencies=<vs_currency in lower case>``,
   ``include_last_updated_at=true`` and ``precision=full``, and answers the value **read as a decimal from the
   response's text** (never through a float), the currency in upper case, the UTC day of ``last_updated_at``.
   An id CoinGecko does not know answers NOT_FOUND; a coin without that currency, NO_DATA.
2. **In bulk** (``supports_bulk_current``): ONE request for every item, the ids and the currencies each once; each item
   answered under its key, as the single read would; an unknown id is that item's NOT_FOUND only. A 429 refuses the
   whole call.
3. **The history** asks ``/coins/{id}/market_chart/range`` with ``interval=daily`` and ``precision=full``, from one hour
   before 00:00 UTC of the day after ``start`` to one hour after 00:00 UTC of the day after ``end``: the edges' own
   midnights fall inside, whether CoinGecko's ends are inclusive or not. Its point at 00:00 UTC of day D is the close
   of day D−1; each becomes the close of the day before, in the asset's currency, no volume. A point not at 00:00 UTC
   (a «now» point) is dropped, and so is a day outside ``start``…``end``.
4. **The Demo plan's year:** a start before today − 364 (``"min"`` included) is moved to today − 364, so the request
   never meets 10012; the Pro plan asks from the start it was given.
5. **Freshness:** ``current_min_refresh_seconds`` is the setting ``current_refresh_minutes`` × 60.
6. **The digits** a float would lose come back whole; an identifier CoinGecko cannot have (empty, a path, a query) is
   NOT_FOUND and asks nothing.
7. **The real path** (a private database behind the settings and the counter, the key and the interval in their
   variables): the core's freshness of a configured CoinGecko is the interval's seconds, and a call through the core
   counts on the group ``coingecko``, never on the plugin's own row (the first shipped reader of a credit-sharing group).

Pure: the real SDK on an ``httpx.MockTransport``; the clock of «today» is a test's; no database, no server.
Red on HEAD: the prices answer NOT_IMPLEMENTED (lot P1).
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db import IdentifierType
from backend.app.db.base import SQLModel  # imports every model
from backend.app.schemas.prices import FACurrentValue, FACurrentValueRequest
from backend.app.services.asset_source_providers.coingecko import plugin as coingecko_plugin
from backend.app.services.asset_source_providers.coingecko.plugin import CoinGeckoProvider
from backend.app.services.assets import core
from backend.app.services.assets.base import AssetRateLimitedError, AssetSourceError
from backend.app.services.platform import call_counter, provider_cooldown
from backend.app.services.plugin_settings import readiness, resolver, runtime
from backend.app.services.plugin_settings.fields import env_name
from backend.app.utils.runtime.cooldown import Cooldowns
from backend.test_scripts.test_utils import print_section, print_success

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "coingecko"
KEY = "CG-test-prices-0123456789KEY"
#: «Today» for the history's year: the day of the recording.
TODAY = date(2026, 11, 17)


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _raw_fixture(name: str) -> str:
    """The recorded body as text: the numbers exactly as CoinGecko wrote them."""
    return json.dumps(_fixture(name)["body"])


class _Group:
    def __init__(self, plan: str) -> None:
        self._plan = plan

    def secret(self, name: str) -> str | None:
        return KEY if name == "api_key" else None

    def get(self, name: str) -> Any:
        return self._plan if name == "plan" else None


class _Bound:
    def __init__(self, plan: str = "demo", refresh: str = "30") -> None:
        self._group, self._refresh = _Group(plan), refresh

    def group(self, name: str) -> _Group:
        return self._group

    def get(self, key: str) -> Any:
        return self._refresh if key == "current_refresh_minutes" else None


class _Wire:
    """A fake CoinGecko: every request recorded; the body text the test chose, as CoinGecko would send it."""

    def __init__(self, text: str = "{}", status: int = 200, headers: dict | None = None) -> None:
        self.text, self.status, self.headers = text, status, headers or {}
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self.status, content=self.text.encode(), headers={"content-type": "application/json", **self.headers})

    def query(self, index: int = -1) -> dict[str, str]:
        parsed = urlparse(str(self.requests[index].url))
        return {key: values[0] for key, values in parse_qs(parsed.query).items()}

    def path(self, index: int = -1) -> str:
        return urlparse(str(self.requests[index].url)).path


def _provider(monkeypatch: pytest.MonkeyPatch, wire: _Wire, *, plan: str = "demo", refresh: str = "30") -> CoinGeckoProvider:
    provider = CoinGeckoProvider()
    provider.bind_settings(_Bound(plan, refresh))  # type: ignore[arg-type]
    monkeypatch.setattr(CoinGeckoProvider, "_http_client", httpx.Client(transport=httpx.MockTransport(wire)))
    monkeypatch.setattr(coingecko_plugin, "_utc_today", lambda: TODAY)
    return provider


def _midnight(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, tzinfo=UTC).timestamp())


# =============================================================================
# 1. A CURRENT PRICE
# =============================================================================


@pytest.mark.asyncio
async def test_p2_a_current_price_is_the_decimal_of_the_text_in_the_assets_currency(monkeypatch: pytest.MonkeyPatch):
    print_section("P2 1: a current price")
    wire = _Wire(_raw_fixture("simple_price_bitcoin_pepe_eur.json"))
    provider = _provider(monkeypatch, wire)

    pepe = await provider.get_current_value("pepe", IdentifierType.TICKER, {"vs_currency": "EUR"})

    assert wire.path() == "/api/v3/simple/price"
    assert wire.query() == {"ids": "pepe", "vs_currencies": "eur", "include_last_updated_at": "true", "precision": "full"}
    assert isinstance(pepe, FACurrentValue)
    assert pepe.value == Decimal("3.5142495375280253E-6"), "the text's digits, not a float's"
    assert (pepe.currency, pepe.as_of_date) == ("EUR", datetime.fromtimestamp(1794923960, UTC).date())
    print_success("decimal from the text, EUR, the UTC day")


@pytest.mark.asyncio
async def test_p2_an_unknown_id_is_not_found_a_missing_currency_no_data(monkeypatch: pytest.MonkeyPatch):
    provider = _provider(monkeypatch, _Wire("{}"))
    with pytest.raises(AssetSourceError) as unknown:
        await provider.get_current_value("no-such-coin", IdentifierType.TICKER, {"vs_currency": "EUR"})
    assert unknown.value.error_code == "NOT_FOUND"

    provider = _provider(monkeypatch, _Wire('{"bitcoin": {"last_updated_at": 1794923960}}'))
    with pytest.raises(AssetSourceError) as missing:
        await provider.get_current_value("bitcoin", IdentifierType.TICKER, {"vs_currency": "EUR"})
    assert missing.value.error_code == "NO_DATA"


# =============================================================================
# 2. IN BULK
# =============================================================================


@pytest.mark.asyncio
async def test_p2_in_bulk_one_request_answers_every_item_under_its_key(monkeypatch: pytest.MonkeyPatch):
    print_section("P2 2: in bulk")
    wire = _Wire('{"bitcoin": {"eur": 59222.25827040563, "usd": 64981.5, "last_updated_at": 1794923960}, "pepe": {"eur": 3.5142495375280253e-06, "last_updated_at": 1794923960}}')
    provider = _provider(monkeypatch, wire)
    assert CoinGeckoProvider.supports_bulk_current is True
    items = [
        FACurrentValueRequest(key="a", identifier="bitcoin", identifier_type=IdentifierType.TICKER, provider_params={"vs_currency": "EUR"}),
        FACurrentValueRequest(key="b", identifier="bitcoin", identifier_type=IdentifierType.TICKER, provider_params={"vs_currency": "usd"}),
        FACurrentValueRequest(key="c", identifier="pepe", identifier_type=IdentifierType.TICKER, provider_params={"vs_currency": "EUR"}),
        FACurrentValueRequest(key="d", identifier="no-such-coin", identifier_type=IdentifierType.TICKER, provider_params={"vs_currency": "EUR"}),
    ]

    answers = await provider.get_current_values_bulk(items)

    assert len(wire.requests) == 1, "one request for every item"
    query = wire.query()
    assert sorted(query["ids"].split(",")) == ["bitcoin", "no-such-coin", "pepe"]
    assert sorted(query["vs_currencies"].split(",")) == ["eur", "usd"]
    assert (query["include_last_updated_at"], query["precision"]) == ("true", "full")
    assert (answers["a"].value, answers["a"].currency) == (Decimal("59222.25827040563"), "EUR")
    assert (answers["b"].value, answers["b"].currency) == (Decimal("64981.5"), "USD")
    assert answers["c"].value == Decimal("3.5142495375280253E-6")
    assert isinstance(answers["d"], AssetSourceError) and answers["d"].error_code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_p2_a_429_refuses_the_whole_bulk_call(monkeypatch: pytest.MonkeyPatch):
    wire = _Wire('{"status": {"error_code": 429}}', status=429, headers={"Retry-After": "45"})
    provider = _provider(monkeypatch, wire)
    items = [FACurrentValueRequest(key="a", identifier="bitcoin", identifier_type=IdentifierType.TICKER, provider_params={"vs_currency": "EUR"})]

    with pytest.raises(AssetRateLimitedError) as refused:
        await provider.get_current_values_bulk(items)

    assert refused.value.retry_after == 45.0 and len(wire.requests) == 1


# =============================================================================
# 3–4. THE HISTORY
# =============================================================================


@pytest.mark.asyncio
async def test_p2_the_history_is_the_close_of_the_day_before_each_midnight_point(monkeypatch: pytest.MonkeyPatch):
    print_section("P2 3: the history")
    recorded = _fixture("market_chart_range_bitcoin_eur_10d.json")["body"]["prices"]
    wire = _Wire(_raw_fixture("market_chart_range_bitcoin_eur_10d.json"))
    provider = _provider(monkeypatch, wire)
    start, end = date(2026, 11, 7), date(2026, 11, 16)

    history = await provider.get_history_value("bitcoin", IdentifierType.TICKER, {"vs_currency": "EUR"}, start, end)

    assert wire.path() == "/api/v3/coins/bitcoin/market_chart/range"
    query = wire.query()
    assert (query["vs_currency"], query["interval"], query["precision"]) == ("eur", "daily", "full")
    assert (int(query["from"]), int(query["to"])) == (_midnight(start + timedelta(days=1)) - 3600, _midnight(end + timedelta(days=1)) + 3600)
    expected = [(datetime.fromtimestamp(stamp / 1000, UTC).date() - timedelta(days=1), Decimal(str(value))) for stamp, value in recorded]
    assert [(point.date, point.close) for point in history.prices] == expected
    assert all(point.currency == "EUR" and point.volume is None for point in history.prices)
    assert history.currency == "EUR"
    print_success("D 00:00 UTC is the close of D−1")


@pytest.mark.asyncio
async def test_p2_a_point_not_at_midnight_and_a_day_outside_the_range_are_dropped(monkeypatch: pytest.MonkeyPatch):
    nov_10, nov_11 = _midnight(date(2026, 11, 10)) * 1000, _midnight(date(2026, 11, 11)) * 1000
    now_point = nov_11 + 13 * 3600 * 1000
    beyond = _midnight(date(2026, 11, 13)) * 1000
    body = json.dumps({"prices": [[nov_10, 10.5], [nov_11, 11.5], [now_point, 99.0], [beyond, 12.5]], "market_caps": [], "total_volumes": []})
    provider = _provider(monkeypatch, _Wire(body))

    history = await provider.get_history_value("bitcoin", IdentifierType.TICKER, {"vs_currency": "EUR"}, date(2026, 11, 9), date(2026, 11, 11))

    assert [(point.date, point.close) for point in history.prices] == [(date(2026, 11, 9), Decimal("10.5")), (date(2026, 11, 10), Decimal("11.5"))]


@pytest.mark.asyncio
@pytest.mark.parametrize(("plan", "start", "expected_start"), [("demo", "min", TODAY - timedelta(days=364)), ("demo", date(2024, 1, 1), TODAY - timedelta(days=364)), ("demo", date(2026, 10, 1), date(2026, 10, 1)), ("pro", date(2024, 1, 1), date(2024, 1, 1))])
async def test_p2_the_demo_plans_year_moves_an_earlier_start(monkeypatch: pytest.MonkeyPatch, plan: str, start: Any, expected_start: date):
    wire = _Wire('{"prices": [], "market_caps": [], "total_volumes": []}')
    provider = _provider(monkeypatch, wire, plan=plan)

    await provider.get_history_value("bitcoin", IdentifierType.TICKER, {"vs_currency": "EUR"}, start, TODAY)

    assert int(wire.query()["from"]) == _midnight(expected_start + timedelta(days=1)) - 3600


# =============================================================================
# 5. FRESHNESS
# =============================================================================


@pytest.mark.parametrize(("minutes", "seconds"), [("10", 600.0), ("30", 1800.0), ("240", 14400.0)])
def test_p2_a_price_stays_fresh_for_the_minutes_of_its_setting(monkeypatch: pytest.MonkeyPatch, minutes: str, seconds: float):
    provider = _provider(monkeypatch, _Wire(), refresh=minutes)
    assert provider.current_min_refresh_seconds == seconds
    assert provider.supports_history is True


# =============================================================================
# 6. THE DIGITS, AND IDENTIFIERS COINGECKO CANNOT HAVE
# =============================================================================


@pytest.mark.asyncio
async def test_p2_a_price_keeps_digits_a_float_would_lose(monkeypatch: pytest.MonkeyPatch):
    """A hand-written body (the recordings were saved through Python): 23 significant digits come back whole."""
    provider = _provider(monkeypatch, _Wire('{"bitcoin": {"eur": 59222.258270405631234567890, "last_updated_at": 1794923960}}'))
    quote = await provider.get_current_value("bitcoin", IdentifierType.TICKER, {"vs_currency": "EUR"})
    assert quote.value == Decimal("59222.258270405631234567890")


@pytest.mark.asyncio
@pytest.mark.parametrize("identifier", ["", "  ", "bit/coin", "../bitcoin", "bitcoin?x=1"])
async def test_p2_an_identifier_coingecko_cannot_have_is_not_found_and_asks_nothing(monkeypatch: pytest.MonkeyPatch, identifier: str):
    wire = _Wire("{}")
    provider = _provider(monkeypatch, wire)
    for read in (
        lambda: provider.get_current_value(identifier, IdentifierType.TICKER, {"vs_currency": "EUR"}),
        lambda: provider.get_history_value(identifier, IdentifierType.TICKER, {"vs_currency": "EUR"}, date(2026, 11, 1), TODAY),
    ):
        with pytest.raises(AssetSourceError) as refused:
            await read()
        assert refused.value.error_code == "NOT_FOUND"
    assert wire.requests == []


# =============================================================================
# 7. THE REAL PATH: THE CORE'S FRESHNESS, THE GROUP'S COUNT
# =============================================================================


@pytest_asyncio.fixture
async def configured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncEngine]:
    """A private file with the whole schema behind the settings, the readiness and the counter; the key and the
    interval in their variables; a private pause table."""
    for name in list(os.environ):
        if name.startswith("LIBREFOLIO_PLUGIN_GROUP_COINGECKO_") or name.startswith("LIBREFOLIO_PLUGIN_ASSET_COINGECKO_") or name.endswith("_PROVIDERS_ENABLED"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY_FILE", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", "p2-coingecko-test-instance-key-0123456789")
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "selfhosted")
    monkeypatch.setenv(env_name("group", "coingecko", "api_key"), KEY)
    monkeypatch.setenv(env_name("asset", "coingecko", "current_refresh_minutes"), "60")
    monkeypatch.setattr(resolver, "_warned_unreadable", set())
    monkeypatch.setattr(resolver, "_warned_invalid_env", set())
    monkeypatch.setattr(resolver, "_warned_key_unavailable", [])
    monkeypatch.setattr(provider_cooldown, "PROVIDER_COOLDOWNS", Cooldowns(60, 3600, jitter=0.0))
    path = tmp_path / "p2_coingecko.db"
    sync_engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    try:
        SQLModel.metadata.create_all(sync_engine)
    finally:
        sync_engine.dispose()
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
    for module in (runtime, readiness, call_counter):
        monkeypatch.setattr(module, "get_async_engine", lambda: engine)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_p2_through_the_core_the_interval_is_the_freshness_and_the_group_counts(configured: AsyncEngine, monkeypatch: pytest.MonkeyPatch):
    print_section("P2 7: the real path")
    provider = await core.configured_provider("coingecko")
    assert provider is not None
    assert core.current_cache_ttl(provider) == 3600.0, "the interval from its variable, in seconds"

    wire = _Wire(_raw_fixture("simple_price_bitcoin_pepe_eur.json"))
    monkeypatch.setattr(CoinGeckoProvider, "_http_client", httpx.Client(transport=httpx.MockTransport(wire)))
    quote = await core.call_provider(provider, lambda: provider.get_current_value("bitcoin", IdentifierType.TICKER, {"vs_currency": "EUR"}), timeout=10)

    assert quote.value == Decimal("59222.25827040563")
    assert (await call_counter.read_counts("group", "coingecko")).minute == 1, "counted on the group: one account's credits"
    assert (await call_counter.read_counts("asset", "coingecko")).minute == 0, "never on the plugin's own row"
    print_success("3600 s, one call on the group")
