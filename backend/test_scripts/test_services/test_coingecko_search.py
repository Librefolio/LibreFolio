"""The CoinGecko provider, lot P3: search, metadata, the asset's page, and the id's own input type (project 76; the
P0 trial's recordings, journal ``76_cryptoPrices/prove/``; the consultant's rule of 17/11 on the provider's own code, ``COINGECKO_ID`` since the developer's
rename of 19/11, N-ID).

The contract pinned here:

1. **The id's type.** CoinGecko's id (``bitcoin``) is CoinGecko's own code, not a ticker: the provider accepts the new
   ``ProviderInputType.COINGECKO_ID`` only, which reaches the plugin as ``IdentifierType.OTHER``, as ``URL`` does. The
   reverse map (``OTHER`` → ``URL``) is untouched: a client that sends ``OTHER`` still stores ``URL``.
2. **Search** asks ``/search?query=…`` and answers its coins only (never its NFTs, exchanges or categories), ordered by
   ``market_cap_rank`` (a coin without a rank last, in CoinGecko's order). A row is ``identifier=<id>``,
   ``identifier_type=OTHER``, the coin's name (as its metadata gives it, TL40), ``type`` CRYPTO, and the user's preferred currency as ``currency`` and as
   ``vs_currency``. A blank query asks nothing.
3. **Metadata** asks ``/coins/{id}`` with the P0 flags (no localization, tickers, market data, community, developer
   data, sparkline) and answers the name, CRYPTO, the logo (``image.large``), the symbol upper-cased as the ticker, and
   ``coingecko:<id>`` among the other identifiers. A symbol longer than a ticker column leaves the ticker out, never
   the rest.
4. **The page** is ``https://www.coingecko.com/en/coins/<id>``, built with no I/O; an id CoinGecko cannot have has none.
5. **Search is on** (``test_search_query``); without a key it answers NOT_CONFIGURED and asks nothing.
6. **The real path** (a private database behind the settings, the counter and the session; the key in its variable):
   an assignment saved as ``COINGECKO_ID`` stays ``COINGECKO_ID``, the plugin receives ``IdentifierType.OTHER``, and the
   refresh stores prices; a search through the service gives a valid row and counts on the group ``coingecko``.

Pure: the real SDK on an ``httpx.MockTransport``; private SQLite files; no server.
Red on HEAD: no ``COINGECKO_ID``, no search, no metadata, no page.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db import IdentifierType
from backend.app.db import session as db_session
from backend.app.db.base import SQLModel  # imports every model
from backend.app.db.models import Asset, AssetProviderAssignment, AssetType, PriceHistory, ProviderInputType
from backend.app.schemas.provider import FAProviderAssignmentItem
from backend.app.schemas.refresh import FARefreshItem, SyncDateRangeModel
from backend.app.services.asset_source_providers.coingecko import plugin as coingecko_plugin
from backend.app.services.asset_source_providers.coingecko.plugin import CoinGeckoProvider
from backend.app.services.assets.base import AssetSourceError, AssetSourceProvider
from backend.app.services.assets.provider_management import ProviderManagementOperations
from backend.app.services.assets.refresh import RefreshOperations
from backend.app.services.assets.search import AssetSearchService
from backend.app.services.platform import call_counter, provider_cooldown
from backend.app.services.plugin_settings import readiness, resolver, runtime
from backend.app.services.plugin_settings.fields import env_name
from backend.app.utils.runtime.cooldown import Cooldowns
from backend.test_scripts.test_utils import print_section, print_success

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "coingecko"
KEY = "CG-test-search-0123456789KEY"
#: «Today» for the Demo plan's year: the day of the recording.
TODAY = date(2026, 11, 17)


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _body(name: str) -> str:
    return json.dumps(_fixture(name)["body"])


class _Group:
    def __init__(self, key: str | None) -> None:
        self._key = key

    def secret(self, name: str) -> str | None:
        return self._key if name == "api_key" else None

    def get(self, name: str) -> Any:
        return "demo" if name == "plan" else None


class _Bound:
    def __init__(self, preferred: str | None = None, key: str | None = KEY) -> None:
        self._group, self._preferred = _Group(key), preferred

    def group(self, name: str) -> _Group:
        return self._group

    def get(self, key: str) -> Any:
        return self._preferred if key == "preferred_currency" else None


class _Wire:
    """A fake CoinGecko: every request recorded; the body the test chose."""

    def __init__(self, text: str = "{}", status: int = 200) -> None:
        self.text, self.status = text, status
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self.status, content=self.text.encode(), headers={"content-type": "application/json"})

    def query(self, index: int = -1) -> dict[str, str]:
        return {key: values[0] for key, values in parse_qs(urlparse(str(self.requests[index].url)).query).items()}

    def path(self, index: int = -1) -> str:
        return urlparse(str(self.requests[index].url)).path


def _provider(monkeypatch: pytest.MonkeyPatch, wire: _Wire, *, preferred: str | None = None, key: str | None = KEY) -> CoinGeckoProvider:
    provider = CoinGeckoProvider()
    provider.bind_settings(_Bound(preferred, key))  # type: ignore[arg-type]
    monkeypatch.setattr(CoinGeckoProvider, "_http_client", httpx.Client(transport=httpx.MockTransport(wire)))
    monkeypatch.setattr(coingecko_plugin, "_utc_today", lambda: TODAY)
    return provider


# =============================================================================
# 1. THE ID'S TYPE
# =============================================================================


def test_p3_coingecko_accepts_its_own_id_which_reaches_it_as_other():
    print_section("P3 1: COINGECKO_ID")
    assert CoinGeckoProvider().accepted_identifier_types == [ProviderInputType.COINGECKO_ID]
    assert AssetSourceProvider.map_input_type_to_identifier_type("COINGECKO_ID") is IdentifierType.OTHER
    # N-ID (developer, 19/11): the type is CoinGecko's own, so the generic name stays free for the future
    assert "PROVIDER_ID" not in ProviderInputType.__members__
    assert AssetSourceProvider.map_identifier_type_to_input_type("OTHER") is ProviderInputType.URL, "the reverse map is unchanged"
    print_success("COINGECKO_ID → OTHER; OTHER → URL as before")


# =============================================================================
# 2. SEARCH
# =============================================================================


@pytest.mark.asyncio
async def test_p3_search_answers_the_coins_by_market_cap_in_the_preferred_currency(monkeypatch: pytest.MonkeyPatch):
    print_section("P3 2: search")
    wire = _Wire(_body("search_pepe.json"))
    provider = _provider(monkeypatch, wire)

    rows = await provider.search("pepe")

    assert len(wire.requests) == 1 and wire.path().endswith("/search") and wire.query() == {"query": "pepe"}
    coins = _fixture("search_pepe.json")["body"]["coins"]
    assert [row["identifier"] for row in rows] == [coin["id"] for coin in sorted(coins, key=lambda c: (c["market_cap_rank"] is None, c["market_cap_rank"] or 0))], "coins only, by rank, a coin without one last"
    assert rows[0] == {
        "identifier": "pepe",
        "identifier_type": IdentifierType.OTHER,
        # TL40 (testlist 23/11): the coin's name alone, as its metadata gives it; the symbol is the ticker (metadata)
        "display_name": "Pepe",
        "currency": "EUR",
        "type": AssetType.CRYPTO.value,
        "provider_params": {"vs_currency": "EUR"},
        # S3 (developer, 20/11): the row carries the coin's logo, the very image its metadata gives (``image.large``)
        "icon_url": next(coin for coin in coins if coin["id"] == "pepe")["large"],
    }
    assert all(row.get("icon_url") == coin.get("large") for row, coin in zip(rows, sorted(coins, key=lambda c: (c["market_cap_rank"] is None, c["market_cap_rank"] or 0)), strict=True)), "each row its own coin's logo"
    print_success(f"{len(rows)} coins, Pepe first")


@pytest.mark.asyncio
async def test_p3_search_keeps_coingeckos_order_among_coins_without_a_rank(monkeypatch: pytest.MonkeyPatch):
    body = {"coins": [{"id": "c", "name": "C", "symbol": "C", "market_cap_rank": None}, {"id": "a", "name": "A", "symbol": "A", "market_cap_rank": 9}, {"id": "b", "name": "B", "symbol": "B", "market_cap_rank": None}], "nfts": [{"id": "n", "name": "N", "symbol": "N"}]}
    provider = _provider(monkeypatch, _Wire(json.dumps(body)))

    assert [row["identifier"] for row in await provider.search("x")] == ["a", "c", "b"]


@pytest.mark.asyncio
async def test_p3_search_prices_in_the_users_preferred_currency(monkeypatch: pytest.MonkeyPatch):
    provider = _provider(monkeypatch, _Wire(_body("search_pepe.json")), preferred="USD")

    first = (await provider.search("pepe"))[0]

    assert (first["currency"], first["provider_params"]) == ("USD", {"vs_currency": "USD"})


@pytest.mark.asyncio
@pytest.mark.parametrize("query", ["", "   "])
async def test_p3_a_blank_search_asks_nothing(monkeypatch: pytest.MonkeyPatch, query: str):
    wire = _Wire(_body("search_pepe.json"))
    provider = _provider(monkeypatch, wire)

    assert await provider.search(query) == []
    assert wire.requests == []


# =============================================================================
# 3. METADATA
# =============================================================================


@pytest.mark.asyncio
async def test_p3_metadata_gives_name_type_logo_ticker_and_the_id_among_the_other_identifiers(monkeypatch: pytest.MonkeyPatch):
    print_section("P3 3: metadata")
    wire = _Wire(_body("coin_pepe.json"))
    provider = _provider(monkeypatch, wire)

    patch = await provider.fetch_asset_metadata("pepe", IdentifierType.OTHER, {"vs_currency": "EUR"})

    assert len(wire.requests) == 1 and wire.path().endswith("/coins/pepe")
    assert wire.query() == dict.fromkeys(("localization", "tickers", "market_data", "community_data", "developer_data", "sparkline"), "false")
    assert patch is not None
    assert (patch.display_name, patch.asset_type, patch.identifier_ticker) == ("Pepe", AssetType.CRYPTO, "PEPE")
    assert patch.icon_url == _fixture("coin_pepe.json")["body"]["image"]["large"]
    assert patch.identifier_other == ["coingecko:pepe"]
    print_success("Pepe, CRYPTO, PEPE, its logo, coingecko:pepe")


@pytest.mark.asyncio
async def test_tl40_a_coin_has_the_same_name_in_the_search_and_in_its_metadata(monkeypatch: pytest.MonkeyPatch):
    """TL40 (the developer's testlist, 23/11): an asset created from a search row is named by the row; «Ask the provider»
    then reads the metadata. The two must give the same name, or the asset window proposes to rename a coin just created
    («Bitcoin (BTC)» → «Bitcoin»). The name is the coin's own, as every other provider names an asset; the symbol is
    the asset's ticker, from the metadata. Both read from the P0 recordings of the same coin."""
    print_section("TL40: one name, from the search and from the metadata")
    search = _provider(monkeypatch, _Wire(_body("search_pepe.json")))
    row = next(row for row in await search.search("pepe") if row["identifier"] == "pepe")
    metadata = await _provider(monkeypatch, _Wire(_body("coin_pepe.json"))).fetch_asset_metadata("pepe", IdentifierType.OTHER, {"vs_currency": "EUR"})

    assert metadata is not None
    assert row["display_name"] == metadata.display_name == "Pepe", f"search {row['display_name']!r}, metadata {metadata.display_name!r}"
    print_success("Pepe in both: nothing to rename after the creation")


@pytest.mark.asyncio
async def test_p3_a_symbol_too_long_for_a_ticker_leaves_the_ticker_out(monkeypatch: pytest.MonkeyPatch):
    body = {**_fixture("coin_pepe.json")["body"], "symbol": "x" * 21}
    provider = _provider(monkeypatch, _Wire(json.dumps(body)))

    patch = await provider.fetch_asset_metadata("pepe", IdentifierType.OTHER)

    assert patch is not None
    assert patch.identifier_ticker is None
    assert (patch.display_name, patch.asset_type) == ("Pepe", AssetType.CRYPTO)


@pytest.mark.asyncio
@pytest.mark.parametrize("identifier", ["", "../pepe", "pepe?x=1"])
async def test_p3_metadata_of_an_id_coingecko_cannot_have_is_not_found_and_asks_nothing(monkeypatch: pytest.MonkeyPatch, identifier: str):
    wire = _Wire(_body("coin_pepe.json"))
    provider = _provider(monkeypatch, wire)

    with pytest.raises(AssetSourceError) as raised:
        await provider.fetch_asset_metadata(identifier, IdentifierType.OTHER)

    assert raised.value.error_code == "NOT_FOUND"
    assert wire.requests == []


# =============================================================================
# 4. THE PAGE
# =============================================================================


@pytest.mark.parametrize(("identifier", "expected"), [("bitcoin", "https://www.coingecko.com/en/coins/bitcoin"), ("../x", None), ("", None)])
def test_p3_the_assets_page(identifier: str, expected: str | None):
    assert CoinGeckoProvider().get_asset_url(identifier, IdentifierType.OTHER) == expected


def test_p6_the_help_link_opens_the_user_page():
    """P6: the provider's help link, beside it where a user picks a source, opens its page in the user guide (the
    contract test checks the page exists)."""
    assert CoinGeckoProvider().provider_help_url == "/mkdocs/user/assets/providers/coingecko/"


# =============================================================================
# 5. SEARCH IS ON; WITHOUT A KEY IT ASKS NOTHING
# =============================================================================


@pytest.mark.asyncio
async def test_p3_search_is_on_and_without_a_key_answers_not_configured(monkeypatch: pytest.MonkeyPatch):
    assert CoinGeckoProvider().test_search_query == "bitcoin"
    assert CoinGeckoProvider().supports_search is True
    wire = _Wire(_body("search_pepe.json"))
    provider = _provider(monkeypatch, wire, key=None)

    with pytest.raises(AssetSourceError) as raised:
        await provider.search("pepe")

    assert raised.value.error_code == "NOT_CONFIGURED"
    assert wire.requests == []


# =============================================================================
# 6. THE REAL PATH
# =============================================================================


@pytest_asyncio.fixture
async def configured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncEngine]:
    """A private file with the whole schema behind the settings, the readiness, the counter and the session; the key in
    its variable; a private pause table."""
    for name in list(os.environ):
        if name.startswith("LIBREFOLIO_PLUGIN_GROUP_COINGECKO_") or name.startswith("LIBREFOLIO_PLUGIN_ASSET_COINGECKO_") or name.endswith("_PROVIDERS_ENABLED"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY_FILE", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", "p3-coingecko-test-instance-key-0123456789")
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "selfhosted")
    monkeypatch.setenv(env_name("group", "coingecko", "api_key"), KEY)
    monkeypatch.setattr(resolver, "_warned_unreadable", set())
    monkeypatch.setattr(resolver, "_warned_invalid_env", set())
    monkeypatch.setattr(resolver, "_warned_key_unavailable", [])
    monkeypatch.setattr(provider_cooldown, "PROVIDER_COOLDOWNS", Cooldowns(60, 3600, jitter=0.0))
    monkeypatch.setattr(coingecko_plugin, "_utc_today", lambda: TODAY)
    path = tmp_path / "p3_coingecko.db"
    sync_engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    try:
        SQLModel.metadata.create_all(sync_engine)
    finally:
        sync_engine.dispose()
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
    for module in (runtime, readiness, call_counter):
        monkeypatch.setattr(module, "get_async_engine", lambda: engine)
    monkeypatch.setattr(db_session, "async_engine", engine)
    try:
        yield engine
    finally:
        await engine.dispose()


class _Routes:
    """A fake CoinGecko that answers each endpoint with its recording."""

    def __init__(self) -> None:
        self.paths: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = urlparse(str(request.url)).path
        self.paths.append(path)
        name = "market_chart_range_bitcoin_eur_10d.json" if path.endswith("/market_chart/range") else "search_pepe.json" if path.endswith("/search") else "simple_price_bitcoin_pepe_eur.json"
        return httpx.Response(200, content=_body(name).encode(), headers={"content-type": "application/json"})


@pytest.mark.asyncio
async def test_p3_an_assignment_saved_as_provider_id_stays_so_and_is_priced_as_other(configured: AsyncEngine, monkeypatch: pytest.MonkeyPatch):
    print_section("P3 6: the real path")
    routes = _Routes()
    monkeypatch.setattr(CoinGeckoProvider, "_http_client", httpx.Client(transport=httpx.MockTransport(routes)))
    received: list[IdentifierType] = []
    original = CoinGeckoProvider.get_history_value

    async def spy(self, identifier, identifier_type, provider_params, start_date, end_date):
        received.append(identifier_type)
        return await original(self, identifier, identifier_type, provider_params, start_date, end_date)

    monkeypatch.setattr(CoinGeckoProvider, "get_history_value", spy)
    async with AsyncSession(configured, expire_on_commit=False) as session:
        asset = Asset(display_name=f"P3 Bitcoin {uuid.uuid4().hex[:8]}", currency="EUR", asset_type=AssetType.CRYPTO)
        session.add(asset)
        await session.commit()
        await ProviderManagementOperations.bulk_assign_providers([FAProviderAssignmentItem(asset_id=asset.id, provider_code="coingecko", identifier="bitcoin", identifier_type="COINGECKO_ID", provider_params={"vs_currency": "EUR"})], session)
        stored = (await session.execute(select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == asset.id))).scalar_one()
        assert stored.identifier_type == ProviderInputType.COINGECKO_ID

    # The recorded history spans 07…17/11/2026: a range inside it, ended before the real today
    start, end = date(2026, 11, 10), date(2026, 11, 15)
    async with AsyncSession(configured, expire_on_commit=False) as session:
        response = await RefreshOperations.bulk_refresh_prices([FARefreshItem(asset_id=asset.id, date_range=SyncDateRangeModel(start=start, end=end))], session)
    (result,) = response.results
    assert received == [IdentifierType.OTHER], "the plugin receives OTHER"
    assert result.points_fetched > 0, result
    async with AsyncSession(configured) as session:
        days = (await session.execute(select(PriceHistory.date).where(PriceHistory.asset_id == asset.id))).scalars().all()
    assert days and min(days) >= start and max(days) <= end
    print_success(f"COINGECKO_ID kept, OTHER received, {len(days)} days stored")


@pytest.mark.asyncio
async def test_p3_a_search_through_the_service_gives_valid_rows_and_counts_on_the_group(configured: AsyncEngine, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(CoinGeckoProvider, "_http_client", httpx.Client(transport=httpx.MockTransport(_Routes())))

    response = await AssetSearchService.search(f"pepe {uuid.uuid4().hex[:6]}", ["coingecko"])

    assert response.providers_with_errors == [], response
    first = response.results[0]
    assert (first.identifier, first.identifier_type, first.asset_type, first.provider_code) == ("pepe", IdentifierType.OTHER, "CRYPTO", "coingecko")
    assert (await call_counter.read_counts("group", "coingecko")).minute == 1
    assert (await call_counter.read_counts("asset", "coingecko")).minute == 0
