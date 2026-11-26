"""The CoinGecko provider, lot P1: the shared group, the plugin's settings and parameters, the SDK behind one door
(project 76; the rules of the P0 trial, journal ``76_cryptoPrices/prove/README.md``).

The contract pinned here:

1. **The group ``coingecko``** is registered by the core, shares one account's credits, and holds the API key (system,
   secret, required, with its own missing phrase, N3a2) and the plan (Demo by default, or Pro). Its variables are
   claimed by the group; it got the five call-limit fields (U4).
2. **The provider ``coingecko``** calls out, reads the group, declares its own refresh interval (system) and preferred
   currency (user), and no call-limit field of its own (the group owns the count).
3. **The vs currencies** are CoinGecko's national ones that are active ISO 4217 codes: exactly the recorded list
   (``fixtures/coingecko/supported_vs_currencies.json``) crossed with pycountry, without gold, silver and XDR.
4. **``vs_currency``** is required and one of them, in any case.
5. **The client** never retries (``max_retries=0``), has a timeout, and takes the root of the plan.
6. **A 429** leaves at once as ``AssetRateLimitedError`` with its ``Retry-After``: one request, no sleep.
7. **The errors**, from the recorded bodies (three shapes): 10012 and 10005 → PLAN_REQUIRED, 10011 → WRONG_PLAN; another
   401 → INVALID_API_KEY, any other status → PROVIDER_ERROR, a timeout → TIMEOUT, no answer → FETCH_ERROR.
8. **The key never leaves**: in no message, no detail, no chained cause's text of the translated error.
9. **Without a key** a call reached past the boundary answers NOT_CONFIGURED, and no request leaves.
10. **A client the provider builds is closed after the call**, error or not; the tests' injected client is not.
11. **The real settings path** (a private database behind the readiness and the runtime): without a key the provider is
    not configured (``coingecko.api_key`` missing, ``missing_fields``); with the key in the group's variable it is,
    and the bound key reaches the request on the Demo root (the plan's default); an invalid plan in its variable is
    ``invalid_locked_setting``.

Pure: the real SDK on an ``httpx.MockTransport``, so no socket opens; no database, no server.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import httpx
import pycountry
import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel  # imports every model
from backend.app.services.asset_source_providers.coingecko.plugin import CoinGeckoProvider
from backend.app.services.assets import core
from backend.app.services.assets.base import AssetRateLimitedError, AssetSourceError
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.coingecko import sdk
from backend.app.services.coingecko.currencies import DEFAULT_VS_CURRENCY, VS_CURRENCIES
from backend.app.services.plugin_settings import readiness, resolver, runtime
from backend.app.services.plugin_settings.call_limits import CALL_LIMIT_KEYS
from backend.app.services.plugin_settings.fields import SettingScope, claimed_env_variables, env_name
from backend.app.services.plugin_settings.groups import get_group
from backend.test_scripts.test_utils import print_section, print_success

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "coingecko"
#: A key of this test only: it must never come back in any text the provider produces.
KEY = "CG-test-0123456789abcdefKEY"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class _Group:
    """The bound settings of the ``coingecko`` group, as the core hands them to the provider."""

    def __init__(self, key: str | None, plan: str = "demo") -> None:
        self._key, self._plan = key, plan

    def secret(self, name: str) -> str | None:
        return self._key if name == "api_key" else None

    def get(self, name: str) -> Any:
        return self._plan if name == "plan" else None


class _Bound:
    def __init__(self, key: str | None, plan: str = "demo") -> None:
        self._group = _Group(key, plan)

    def group(self, name: str) -> _Group:
        assert name == "coingecko"
        return self._group


class _Wire:
    """A fake CoinGecko: every request recorded, the answer the test chose."""

    def __init__(self, status: int = 200, body: object = None, headers: dict | None = None, exc: Exception | None = None) -> None:
        self.status, self.body, self.headers, self.exc = status, body, headers or {}, exc
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.exc is not None:
            raise self.exc
        return httpx.Response(self.status, json=self.body, headers=self.headers)


def _provider(monkeypatch: pytest.MonkeyPatch, wire: _Wire, *, key: str | None = KEY, plan: str = "demo") -> CoinGeckoProvider:
    provider = CoinGeckoProvider()
    provider.bind_settings(_Bound(key, plan))  # type: ignore[arg-type]
    monkeypatch.setattr(CoinGeckoProvider, "_http_client", httpx.Client(transport=httpx.MockTransport(wire)))
    return provider


def _price(provider: CoinGeckoProvider) -> Any:
    return provider._call(lambda client: client.simple.price.get(ids="bitcoin", vs_currencies="eur"))


def _texts(error: BaseException) -> str:
    """Every text an error carries along its chain: the message, the details, the causes."""
    parts: list[str] = []
    seen: BaseException | None = error
    while seen is not None:
        parts += [str(seen), repr(getattr(seen, "details", ""))]
        seen = seen.__cause__ or seen.__context__
    return " ".join(parts)


# =============================================================================
# 1–2. THE GROUP AND THE PROVIDER
# =============================================================================


def test_p1_the_coingecko_group_holds_the_key_and_the_plan_and_shares_credits():
    print_section("P1 1: the group")
    group = get_group("coingecko")
    assert group is not None and not group.test_only and group.shares_credits
    fields = {declared.key: declared for declared in group.fields}
    key = fields["api_key"]
    assert (key.scope, key.secret, key.required) == (SettingScope.SYSTEM, True, True)
    assert key.missing_key == "pluginSettings.group.coingecko.missing.api_key"
    plan = fields["plan"]
    assert (plan.default, [option.value for option in plan.options]) == ("demo", ["demo", "pro"])
    assert set(CALL_LIMIT_KEYS) <= set(fields), "the group owns the count: it got the five call-limit fields"
    claims = claimed_env_variables()
    assert claims.get(env_name("group", "coingecko", "api_key")) == ("group", "coingecko")
    assert claims.get(env_name("group", "coingecko", "plan")) == ("group", "coingecko")
    print_success("key, plan, credits shared")


def test_p1_the_provider_reads_the_group_and_declares_its_own_two_settings():
    AssetProviderRegistry.auto_discover()
    plugin_class = AssetProviderRegistry.get_plugin("coingecko")
    assert plugin_class is CoinGeckoProvider
    assert plugin_class.calls_external_service is True
    assert tuple(plugin_class.settings_groups) == ("coingecko",)
    keys = {declared.key: declared for declared in plugin_class.settings_fields}
    assert set(keys) == {"current_refresh_minutes", "preferred_currency"}, "no call-limit field of its own: the group counts"
    assert (keys["current_refresh_minutes"].scope, keys["current_refresh_minutes"].default) == (SettingScope.SYSTEM, "30")
    assert [option.value for option in keys["current_refresh_minutes"].options] == ["10", "15", "30", "60", "120", "240"]
    assert (keys["preferred_currency"].scope, keys["preferred_currency"].default) == (SettingScope.USER, "EUR")
    assert [option.value for option in keys["preferred_currency"].options] == list(VS_CURRENCIES)
    provider = CoinGeckoProvider()
    assert (provider.provider_code, provider.provider_name) == ("coingecko", "CoinGecko")


# =============================================================================
# 3–4. THE CURRENCIES AND THE PARAMETER
# =============================================================================


def test_p1_the_vs_currencies_are_coingeckos_national_iso_ones():
    recorded = _fixture("supported_vs_currencies.json")["body"]
    active_iso = {currency.alpha_3 for currency in pycountry.currencies}
    expected = sorted(code.upper() for code in recorded if code.upper() in active_iso and code.upper() not in {"XAU", "XAG", "XDR"})
    assert list(VS_CURRENCIES) == expected
    assert DEFAULT_VS_CURRENCY == "EUR" and "EUR" in VS_CURRENCIES
    assert not {"BTC", "ETH", "SATS", "XAU", "XDR", "VEF"} & set(VS_CURRENCIES)


def test_p1_vs_currency_is_required_and_one_of_them():
    provider = CoinGeckoProvider()
    schema = {param["key"]: param for param in provider.params_schema}
    assert (schema["vs_currency"]["required"], schema["vs_currency"]["default"], schema["vs_currency"]["options"]) == (True, "EUR", list(VS_CURRENCIES))
    provider.validate_params({"vs_currency": "EUR"})
    provider.validate_params({"vs_currency": "usd"})
    for params, code in ((None, "MISSING_PARAMS"), ({}, "MISSING_PARAMS"), ({"vs_currency": " "}, "MISSING_PARAMS"), ({"vs_currency": "BTC"}, "INVALID_PARAMS"), ({"vs_currency": "XAU"}, "INVALID_PARAMS")):
        with pytest.raises(AssetSourceError) as refused:
            provider.validate_params(params)
        assert refused.value.error_code == code, params


# =============================================================================
# 5. THE CLIENT
# =============================================================================


@pytest.mark.parametrize(("plan", "root", "header"), [("demo", "https://api.coingecko.com/api/v3/", "x-cg-demo-api-key"), ("pro", "https://pro-api.coingecko.com/api/v3/", "x-cg-pro-api-key")])
def test_p1_the_client_never_retries_and_takes_the_root_of_its_plan(monkeypatch: pytest.MonkeyPatch, plan: str, root: str, header: str):
    wire = _Wire(body=_fixture("simple_price_bitcoin_pepe_eur.json")["body"])
    provider = _provider(monkeypatch, wire, plan=plan)
    client = sdk.build_client(KEY, plan)
    assert (client.max_retries, str(client.base_url), client.timeout) == (0, root, sdk.REQUEST_TIMEOUT_SECONDS)

    _price(provider)

    assert len(wire.requests) == 1
    request = wire.requests[0]
    assert str(request.url).startswith(root) and request.headers.get(header) == KEY


# =============================================================================
# 6–8. THE REFUSAL, THE ERRORS, THE KEY
# =============================================================================


def test_p1_a_429_leaves_at_once_with_its_retry_after(monkeypatch: pytest.MonkeyPatch):
    print_section("P1 6: a 429")
    wire = _Wire(status=429, body={"status": {"error_code": 429, "error_message": "You've exceeded the Rate Limit."}}, headers={"Retry-After": "30"})
    provider = _provider(monkeypatch, wire)
    started = time.monotonic()

    with pytest.raises(AssetRateLimitedError) as refused:
        _price(provider)

    assert time.monotonic() - started < 2, "no sleep on the Retry-After"
    assert len(wire.requests) == 1, "no retry"
    assert (refused.value.error_code, refused.value.retry_after) == ("RATE_LIMITED", 30.0)
    assert KEY not in _texts(refused.value)
    print_success("one request, RATE_LIMITED, 30 s")


@pytest.mark.parametrize(
    ("fixture", "code"),
    [("error_10012_range_over_365d.json", "PLAN_REQUIRED"), ("error_10005_paid_endpoint.json", "PLAN_REQUIRED"), ("error_10011_demo_key_on_pro_root.json", "WRONG_PLAN")],
)
def test_p1_the_recorded_errors_have_codes_of_their_own(monkeypatch: pytest.MonkeyPatch, fixture: str, code: str):
    recorded = _fixture(fixture)
    provider = _provider(monkeypatch, _Wire(status=recorded["status"], body=recorded["body"]))

    with pytest.raises(AssetSourceError) as refused:
        _price(provider)

    assert refused.value.error_code == code
    assert refused.value.details["coingecko_error_code"] == sdk.coingecko_error_code(recorded["body"])
    assert KEY not in _texts(refused.value)


@pytest.mark.parametrize(
    ("wire", "code"),
    [
        (_Wire(status=401, body={"status": {"error_code": 10002, "error_message": "API Key Missing"}}), "INVALID_API_KEY"),
        (_Wire(status=500, body={"error": "boom"}), "PROVIDER_ERROR"),
        (_Wire(exc=httpx.ReadTimeout("slow")), "TIMEOUT"),
        (_Wire(exc=httpx.ConnectError("down")), "FETCH_ERROR"),
    ],
    ids=["401", "500", "timeout", "no-answer"],
)
def test_p1_other_failures_have_the_cores_codes(monkeypatch: pytest.MonkeyPatch, wire: _Wire, code: str):
    provider = _provider(monkeypatch, wire)

    with pytest.raises(AssetSourceError) as refused:
        _price(provider)

    assert refused.value.error_code == code
    assert len(wire.requests) == 1, "no retry"
    assert KEY not in _texts(refused.value)
    if code == "PROVIDER_ERROR":
        assert refused.value.details["detail"] == "CoinGecko HTTP 500", "the interface's text shows the status"


def test_p1_the_error_code_is_found_in_all_three_shapes():
    assert sdk.coingecko_error_code(_fixture("error_10012_range_over_365d.json")["body"]) == 10012
    assert sdk.coingecko_error_code(_fixture("error_10005_paid_endpoint.json")["body"]) == 10005
    assert sdk.coingecko_error_code(_fixture("error_10011_demo_key_on_pro_root.json")["body"]) == 10011
    assert sdk.coingecko_error_code({"status": {"error_code": True}}) is None
    assert sdk.coingecko_error_code("not a body") is None


# =============================================================================
# 9. WITHOUT A KEY
# =============================================================================


def test_p1_without_a_key_no_request_leaves(monkeypatch: pytest.MonkeyPatch):
    wire = _Wire(body={})
    provider = _provider(monkeypatch, wire, key=None)

    with pytest.raises(AssetSourceError) as refused:
        _price(provider)

    assert refused.value.error_code == "NOT_CONFIGURED"
    assert wire.requests == []


# =============================================================================
# 10. THE CLIENT'S CONNECTIONS
# =============================================================================


def test_p1_a_client_the_provider_builds_is_closed_after_the_call_an_injected_one_is_not(monkeypatch: pytest.MonkeyPatch):
    """Every call builds a client with its own connection pool: closed after the call, error or not. The tests'
    injected client belongs to the test, never closed by the provider."""
    built: list[Any] = []
    real_build = sdk.build_client

    def recording_build(api_key: str, plan: str, *, http_client: Any = None) -> Any:
        own = http_client or httpx.Client(transport=httpx.MockTransport(_Wire(body={"bitcoin": {"eur": 1}})))
        client = real_build(api_key, plan, http_client=own)
        built.append(client)
        return client

    monkeypatch.setattr(sdk, "build_client", recording_build)
    provider = CoinGeckoProvider()
    provider.bind_settings(_Bound(KEY))  # type: ignore[arg-type]
    monkeypatch.setattr(CoinGeckoProvider, "_http_client", None)

    _price(provider)
    assert built[-1].is_closed(), "a client the provider built is closed after a call"

    failing = httpx.Client(transport=httpx.MockTransport(_Wire(status=500, body={})))
    monkeypatch.setattr(sdk, "build_client", lambda api_key, plan, *, http_client=None: built.append(real_build(api_key, plan, http_client=http_client or failing)) or built[-1])
    with pytest.raises(AssetSourceError):
        _price(provider)
    assert built[-1].is_closed(), "closed after an error too"

    injected = httpx.Client(transport=httpx.MockTransport(_Wire(body={"bitcoin": {"eur": 1}})))
    monkeypatch.setattr(sdk, "build_client", real_build)
    monkeypatch.setattr(CoinGeckoProvider, "_http_client", injected)
    _price(provider)
    assert not injected.is_closed, "the tests' client is the test's"


# =============================================================================
# 11. THE REAL SETTINGS PATH
# =============================================================================

KEY_VARIABLE = env_name("group", "coingecko", "api_key")
PLAN_VARIABLE = env_name("group", "coingecko", "plan")


@pytest.fixture
def clean_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Test mode, a test instance key, the self-hosted profile, no CoinGecko variable, no allow-list."""
    for name in list(os.environ):
        if name.startswith("LIBREFOLIO_PLUGIN_GROUP_COINGECKO_") or name.startswith("LIBREFOLIO_PLUGIN_ASSET_COINGECKO_") or name.endswith("_PROVIDERS_ENABLED"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY_FILE", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", "p1-coingecko-test-instance-key-0123456789")
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "selfhosted")
    monkeypatch.setattr(resolver, "_warned_unreadable", set())
    monkeypatch.setattr(resolver, "_warned_invalid_env", set())
    monkeypatch.setattr(resolver, "_warned_key_unavailable", [])
    yield


@pytest_asyncio.fixture
async def private_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clean_environment: None) -> AsyncIterator[AsyncEngine]:
    """A private file with the whole schema behind the readiness and the runtime: no row, so only the variables speak."""
    path = tmp_path / "p1_coingecko.db"
    sync_engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    try:
        SQLModel.metadata.create_all(sync_engine)
    finally:
        sync_engine.dispose()
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
    monkeypatch.setattr(runtime, "get_async_engine", lambda: engine)
    monkeypatch.setattr(readiness, "get_async_engine", lambda: engine)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_p1_without_a_key_the_provider_is_not_configured(private_settings: AsyncEngine):
    print_section("P1 11: the real settings path")
    answer = (await readiness.plugins_readiness("asset", ["coingecko"], user_id=None))["coingecko"]

    assert answer.configured is False
    assert answer.missing == ("coingecko.api_key",)
    assert answer.reason == "missing_fields"


@pytest.mark.asyncio
async def test_p1_with_the_key_in_its_variable_the_key_reaches_the_request_on_the_demo_root(private_settings: AsyncEngine, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(KEY_VARIABLE, KEY)
    assert (await readiness.plugins_readiness("asset", ["coingecko"], user_id=None))["coingecko"].configured is True

    provider = await core.configured_provider("coingecko")
    assert provider is not None
    wire = _Wire(body=_fixture("simple_price_bitcoin_pepe_eur.json")["body"])
    monkeypatch.setattr(CoinGeckoProvider, "_http_client", httpx.Client(transport=httpx.MockTransport(wire)))

    _price(provider)  # type: ignore[arg-type]

    request = wire.requests[0]
    assert str(request.url).startswith("https://api.coingecko.com/api/v3/"), "the plan's default, Demo, really delivered"
    assert request.headers.get("x-cg-demo-api-key") == KEY
    print_success("the key from the variable, on the Demo root")


@pytest.mark.asyncio
async def test_p1_an_invalid_plan_in_its_variable_is_an_invalid_locked_setting(private_settings: AsyncEngine, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(KEY_VARIABLE, KEY)
    monkeypatch.setenv(PLAN_VARIABLE, "gold")

    answer = (await readiness.plugins_readiness("asset", ["coingecko"], user_id=None))["coingecko"]

    assert answer.configured is False
    assert answer.reason == "invalid_locked_setting"
    assert PLAN_VARIABLE in answer.variables


# =============================================================================
# P1b. THE ICON: COINGECKO'S OWN FAVICON, BY URL
# =============================================================================
#
# The developer's choice (P1b-b): the icon points at CoinGecko's favicon, as Yahoo's, justETF's and Borsa Italiana's
# point at theirs, so it follows CoinGecko's own updates. No file is bundled.

COINGECKO_FAVICON = "https://www.coingecko.com/favicon.ico"


def test_p1b_the_icon_is_coingeckos_favicon_by_url():
    assert CoinGeckoProvider().get_icon == COINGECKO_FAVICON


def test_p1b_no_icon_file_is_bundled():
    from backend.app.api.v1.uploads import plugin_static_file  # noqa: PLC0415 — the route's own resolution

    bundled = plugin_static_file("asset", "coingecko.png")
    assert bundled is not None and not bundled.exists(), "the icon is the favicon's URL, not a file of the static folder"
