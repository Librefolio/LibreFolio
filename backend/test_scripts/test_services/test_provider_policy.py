"""Where the asset providers stand in the asset search (F21): their tier, their priority, the order of the search.

The contract pinned here, by the module that holds each part:

1. ``config/plugins.py``: ``asset_providers_premium()`` reads ``LIBREFOLIO_ASSET_PROVIDERS_PREMIUM`` and
   ``asset_providers_order()`` reads ``LIBREFOLIO_ASSET_PROVIDERS_ORDER``, at every call: comma-separated codes,
   stripped, lowercased, in order, each once at its first place; ``None`` when the variable is unset, blank, or lists
   no code at all (``,, ,``).
2. ``services/assets/provider_policy.py``:
   - ``provider_tier(code)``: while the PREMIUM variable is set, exactly the registered providers it lists are premium
     and every other one is community, a declared premium included, even when the variable lists no registered code at
     all; without it, the plugin's declared ``tier``, community for a code no provider has;
   - ``provider_priority(code)``: the declared ``search_priority``, 100 for a code no provider has; while the ORDER
     variable is set, the registered providers it lists get 0, 1, 2… in its order, and every other one the length of
     that list plus its declared priority;
   - ``search_order(codes)``: premium first, then lower priority; ties keep the given order, and a code given twice is
     kept at both places. With every value at its default the order is the given one (D-X3): an instance without a
     premium provider searches as before. The PREMIUM list ranks nothing: only ORDER does;
   - a code of either variable that no registered provider has is dropped, and logged once per process: one warning,
     ``Unknown asset providers in the configuration``, with ``variable`` and ``codes``;
   - ``search_rank(code)``, the key that ``search_order`` and the search sort by: ``(0 if premium else 1, priority)``.
3. ``services/assets/base.py``: ``AssetSourceProvider`` declares ``tier`` community and ``search_priority`` 100
   (``DEFAULT_SEARCH_PRIORITY``). Defining a subclass checks its declarations: a valid tier string becomes the
   ``FAProviderTier`` member; an invalid tier, or a priority that is not a whole number of at least 0 (a bool is not
   one), raises ``TypeError`` naming the class.
4. ``services/assets/search.py``: ``AssetSearchService.search`` queries its providers in that order and answers
   provider by provider in it (``asyncio.gather`` keeps the order), in ``providers_queried`` and in ``results`` alike.

Pure: no database, no server, no network. Both variables are removed from this process's environment before each test
and set through ``monkeypatch`` where a test is about them. The cache of ``_report_unknown`` is emptied before and after
each test, so "once per process" starts over in each; the log is read with ``structlog.testing.capture_logs``, behind a
barrier: a canary logged through the module's own logger must reach the capture, or "logged once" would prove nothing.
The cases about declared values give ``provider_policy`` stand-in plugin classes in place of its own
``AssetProviderRegistry`` name; the shared registry, where the search also looks up the URLs of its results, is left as
it is. The search runs against doubles handed out by a replaced ``core.configured_provider``: they are not plugins, so
``core.call_provider`` runs them as they are. Each search test uses a query of its own, whose cache entries are removed
after it. A class with a wrong declaration is defined inside its test and never registered.

Red until the fix of the repeated codes lands: ``search.py`` ranks its providers in a dict keyed by code, where a code
given twice takes the place of its last occurrence, so ``a,b,a`` is searched as ``b,a,a`` with every value at its
default; and ``provider_policy.search_rank`` does not exist yet. The cases about it look it up when they run, so each
fails alone, with an ``AttributeError``, and the rest of the file still runs.
"""

import contextlib
import uuid
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from structlog.testing import capture_logs

from backend.app.config.plugins import asset_providers_order, asset_providers_premium
from backend.app.schemas.provider import DEFAULT_SEARCH_PRIORITY, FAProviderSearchResponse, FAProviderTier
from backend.app.services.assets import core, provider_policy
from backend.app.services.assets.base import AssetSourceProvider
from backend.app.services.assets.provider_policy import provider_priority, provider_tier, search_order
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.assets.search import AssetSearchService

PREMIUM_VARIABLE = "LIBREFOLIO_ASSET_PROVIDERS_PREMIUM"
ORDER_VARIABLE = "LIBREFOLIO_ASSET_PROVIDERS_ORDER"
PREMIUM = FAProviderTier.PREMIUM
COMMUNITY = FAProviderTier.COMMUNITY

UNKNOWN_EVENT = "Unknown asset providers in the configuration"
LOG_CANARY = "provider policy test: the capture reaches the module's logger"

#: The asset plugins shipped today: a barrier for the cases that read the real registry.
SHIPPED_CODES = frozenset({"borsa_italiana", "css_scraper", "justetf", "mockprov", "scheduled_investment", "yfinance"})
#: A code no registered provider has.
UNKNOWN_CODE = "nosuchprovider"

#: The stand-in codes: registered only in the registry a stand-in case gives provider_policy, never in the shared one.
ALPHA, BETA, GAMMA, DELTA = "standin_alpha", "standin_beta", "standin_gamma", "standin_delta"
STAND_IN_CODES = (ALPHA, BETA, GAMMA, DELTA)


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


@pytest.fixture(autouse=True)
def isolated_policy(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Neither variable inherited from the process, and the once-per-process report starting over in each test."""
    monkeypatch.delenv(PREMIUM_VARIABLE, raising=False)
    monkeypatch.delenv(ORDER_VARIABLE, raising=False)
    provider_policy._report_unknown.cache_clear()
    yield
    provider_policy._report_unknown.cache_clear()


def _plugin(tier: FAProviderTier = COMMUNITY, priority: int = DEFAULT_SEARCH_PRIORITY) -> type:
    """A stand-in plugin class carrying what provider_policy reads of one: ``tier`` and ``search_priority``."""
    return type("StandInPlugin", (), {"tier": tier, "search_priority": priority})


class _StandInRegistry:
    """The registry as provider_policy asks it: ``get_plugin(code)``, the class registered under ``code``, or None."""

    def __init__(self, plugins: dict[str, type]):
        self._plugins = plugins

    def get_plugin(self, code: str) -> type | None:
        return self._plugins.get(code)


def _use_stand_ins(monkeypatch: pytest.MonkeyPatch, plugins: dict[str, type]) -> None:
    """Make ``plugins`` the whole registry provider_policy sees; the shared AssetProviderRegistry is not touched."""
    monkeypatch.setattr(provider_policy, "AssetProviderRegistry", _StandInRegistry(plugins))


def _mixed_stand_ins() -> dict[str, type]:
    """Two community providers, declared at 100 and 7, and two premium ones, declared at 100 and 5."""
    return {ALPHA: _plugin(), BETA: _plugin(priority=7), GAMMA: _plugin(PREMIUM), DELTA: _plugin(PREMIUM, 5)}


def _registered_codes() -> list[str]:
    """The codes of the real registry in its order, behind a barrier: the shipped plugins are there, UNKNOWN_CODE is not."""
    codes = AssetProviderRegistry.list_plugin_codes()
    assert SHIPPED_CODES <= set(codes), f"barrier: the registry must hold the shipped plugins {sorted(SHIPPED_CODES)}: {codes}"
    assert UNKNOWN_CODE not in codes, f"barrier: {UNKNOWN_CODE!r} must be a code no provider has: {codes}"
    return codes


def _declared(code: str) -> tuple[FAProviderTier, int]:
    """The ``tier`` and ``search_priority`` the registered plugin ``code`` declares."""
    plugin = AssetProviderRegistry.get_plugin(code)
    return plugin.tier, plugin.search_priority


@contextlib.contextmanager
def _captured() -> Iterator[list[dict[str, Any]]]:
    """The structlog events of the block, behind a barrier: a canary logged through provider_policy's own logger must be
    among them, or "logged once" would prove nothing."""
    with capture_logs() as events:
        provider_policy.logger.debug(LOG_CANARY)
        yield events
    assert any(event.get("event") == LOG_CANARY for event in events), f"barrier: provider_policy's logger does not reach capture_logs, so what this test reads of the log proves nothing: {events}"


def _unknown_reports(events: list[dict[str, Any]]) -> list[tuple[Any, Any, Any]]:
    """``(level, variable, codes)`` of each report of unknown codes among the captured events, in order."""
    return [(event.get("log_level"), event.get("variable"), event.get("codes")) for event in events if event.get("event") == UNKNOWN_EVENT]


def _items(code: str) -> list[dict[str, Any]]:
    """What the double of ``code`` answers to any query: two items identified by the code."""
    return [{"identifier": f"{code}-{number}", "identifier_type": "TICKER", "display_name": f"{code} {number}"} for number in (1, 2)]


class _SearchDouble:
    """A provider as ``AssetSearchService.search`` uses one: it supports search and answers ``_items(code)``.

    Not a plugin (no ``PluginSettingsMixin``): ``core.call_provider`` runs it as it is, with no settings and no pause.
    """

    supports_search = True

    def __init__(self, code: str):
        self.code = code

    async def search(self, query: str) -> list[dict[str, Any]]:
        return _items(self.code)


def _use_search_doubles(monkeypatch: pytest.MonkeyPatch, plugins: dict[str, type]) -> None:
    """``plugins`` as provider_policy's registry, and a search double for each of their codes from core.configured_provider."""
    _use_stand_ins(monkeypatch, plugins)

    async def configured_provider(code: str, *, user_id: int | None = None) -> _SearchDouble | None:
        return _SearchDouble(code) if code in plugins else None

    monkeypatch.setattr(core, "configured_provider", configured_provider)


@pytest.fixture
def query() -> Iterator[str]:
    """A query of this test alone, so the process's search cache serves it to no other test; its entries go after it."""
    text = f"f21-search-order-{uuid.uuid4().hex}"
    yield text
    for code in STAND_IN_CODES:
        core._search_query_cache.delete((code, text, core.settings_cache_part(_SearchDouble(code))))


def _assert_searched_in(response: FAProviderSearchResponse, expected: list[str]) -> None:
    """No double failed, and the providers and their items come out in ``expected`` order, provider by provider."""
    assert response.providers_with_errors == [], f"barrier: a double failed, so the order proves nothing: {response}"
    assert response.providers_queried == expected
    assert [(item.provider_code, item.identifier) for item in response.results] == [(code, item["identifier"]) for code in expected for item in _items(code)]


# =============================================================================
# 1. THE VARIABLES (config/plugins.py)
# =============================================================================

ACCESSORS = [
    pytest.param(asset_providers_premium, PREMIUM_VARIABLE, id="premium"),
    pytest.param(asset_providers_order, ORDER_VARIABLE, id="order"),
]


@pytest.mark.parametrize(("accessor", "variable"), ACCESSORS)
@pytest.mark.parametrize(
    "value",
    [
        pytest.param(None, id="unset"),
        pytest.param("", id="empty"),
        pytest.param("   ", id="blank"),
        pytest.param(",, ,", id="commas-only"),
    ],
)
def test_a_variable_that_lists_no_code_overrides_nothing(monkeypatch: pytest.MonkeyPatch, accessor: Callable[[], tuple[str, ...] | None], variable: str, value: str | None) -> None:
    """Unset, empty, blank, or commas and spaces only: ``None``, and every provider keeps its declarations."""
    if value is not None:
        monkeypatch.setenv(variable, value)

    assert accessor() is None


@pytest.mark.parametrize(("accessor", "variable"), ACCESSORS)
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(" JustETF ,  YFINANCE ", ("justetf", "yfinance"), id="stripped-and-lowercased"),
        pytest.param("yfinance,css_scraper,justetf", ("yfinance", "css_scraper", "justetf"), id="in-order"),
        pytest.param("yfinance,justetf, YFINANCE ,justetf", ("yfinance", "justetf"), id="each-once-at-its-first-place"),
        pytest.param(",yfinance,, ,justetf,", ("yfinance", "justetf"), id="empty-items-skipped"),
    ],
)
def test_a_variable_lists_its_codes_stripped_lowercased_in_order_once(monkeypatch: pytest.MonkeyPatch, accessor: Callable[[], tuple[str, ...] | None], variable: str, value: str, expected: tuple[str, ...]) -> None:
    """Comma-separated codes, in any case and with spaces around them: stripped, lowercased, in order, each once."""
    monkeypatch.setenv(variable, value)

    assert accessor() == expected


def test_each_accessor_reads_its_own_variable_at_every_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """Read when called, never cached, and neither accessor reads the other's variable."""
    monkeypatch.setenv(PREMIUM_VARIABLE, "justetf")
    assert (asset_providers_premium(), asset_providers_order()) == (("justetf",), None)

    monkeypatch.setenv(PREMIUM_VARIABLE, "css_scraper")
    monkeypatch.setenv(ORDER_VARIABLE, "yfinance")
    assert (asset_providers_premium(), asset_providers_order()) == (("css_scraper",), ("yfinance",))

    monkeypatch.delenv(PREMIUM_VARIABLE)
    assert (asset_providers_premium(), asset_providers_order()) == (None, ("yfinance",))


# =============================================================================
# 2. THE EFFECTIVE TIER AND PRIORITY (provider_tier, provider_priority)
# =============================================================================


def test_every_shipped_provider_declares_community_at_the_default_priority() -> None:
    """The premise of D-X3 for the plugins shipped today: none declares premium, nor a priority other than 100.

    A plugin that declares otherwise reorders the search of every instance, configured or not: that is a decision, and
    this pin changes with it.
    """
    codes = _registered_codes()

    assert DEFAULT_SEARCH_PRIORITY == 100
    assert {code: _declared(code) for code in codes} == dict.fromkeys(codes, (COMMUNITY, 100))


def test_without_the_variables_every_registered_provider_has_its_declared_tier_and_priority() -> None:
    """No variable: the effective tier and priority of every registered provider are its declarations, the tier an ``FAProviderTier``."""
    codes = _registered_codes()

    effective = {code: (provider_tier(code), provider_priority(code)) for code in codes}

    assert effective == {code: _declared(code) for code in codes}
    assert all(isinstance(tier, FAProviderTier) for tier, _ in effective.values()), f"a tier must be an FAProviderTier, not a bare string: {effective}"


def test_without_the_variables_a_declared_tier_and_priority_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    """A plugin's declarations are its effective values; a code no provider has is community at 100."""
    _use_stand_ins(monkeypatch, {ALPHA: _plugin(PREMIUM, 40), BETA: _plugin(COMMUNITY, 7)})

    placements = {code: (provider_tier(code), provider_priority(code)) for code in (ALPHA, BETA, UNKNOWN_CODE)}

    assert placements == {ALPHA: (PREMIUM, 40), BETA: (COMMUNITY, 7), UNKNOWN_CODE: (COMMUNITY, 100)}


def test_the_premium_variable_makes_exactly_the_listed_providers_premium(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set, it decides alone: the providers it lists are premium, every other registered provider is community."""
    codes = _registered_codes()
    monkeypatch.setenv(PREMIUM_VARIABLE, " JustETF ,yfinance")

    tiers = {code: provider_tier(code) for code in codes}

    assert tiers == {code: PREMIUM if code in {"justetf", "yfinance"} else COMMUNITY for code in codes}


def test_the_premium_variable_overrides_the_declared_tiers(monkeypatch: pytest.MonkeyPatch) -> None:
    """A listed provider that declares community is premium; an unlisted one that declares premium is community."""
    _use_stand_ins(monkeypatch, {ALPHA: _plugin(PREMIUM), BETA: _plugin(COMMUNITY)})
    monkeypatch.setenv(PREMIUM_VARIABLE, BETA)

    assert {code: provider_tier(code) for code in (ALPHA, BETA)} == {ALPHA: COMMUNITY, BETA: PREMIUM}


def test_an_unknown_premium_code_is_ignored_and_reported_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """A listed code no provider has makes nothing premium, itself included, and is logged once however many calls read the variable."""
    _registered_codes()
    monkeypatch.setenv(PREMIUM_VARIABLE, f"justetf,{UNKNOWN_CODE}")

    with _captured() as events:
        tiers = [provider_tier("justetf"), provider_tier("yfinance"), provider_tier(UNKNOWN_CODE)]

    assert tiers == [PREMIUM, COMMUNITY, COMMUNITY]
    assert _unknown_reports(events) == [("warning", PREMIUM_VARIABLE, [UNKNOWN_CODE])]


def test_a_premium_variable_listing_only_unknown_codes_makes_no_provider_premium(monkeypatch: pytest.MonkeyPatch) -> None:
    """Still set, so still alone to decide: it lists no registered provider, so none is premium, a declared premium demoted
    too; its codes are logged once, and the search keeps the given order."""
    _use_stand_ins(monkeypatch, {ALPHA: _plugin(COMMUNITY), BETA: _plugin(PREMIUM)})
    assert search_order([ALPHA, BETA]) == [BETA, ALPHA], "barrier: without the variable the declared premium leads"
    monkeypatch.setenv(PREMIUM_VARIABLE, "NoSuch_One, nosuch_two")

    with _captured() as events:
        tiers = {code: provider_tier(code) for code in (ALPHA, BETA)}
        order = search_order([ALPHA, BETA])

    assert tiers == {ALPHA: COMMUNITY, BETA: COMMUNITY}
    assert order == [ALPHA, BETA]
    assert _unknown_reports(events) == [("warning", PREMIUM_VARIABLE, ["nosuch_one", "nosuch_two"])]


def test_the_order_variable_numbers_the_listed_providers_and_puts_the_others_after(monkeypatch: pytest.MonkeyPatch) -> None:
    """The listed providers get 0, 1… in the order of the list; every other one the length of the list plus its declared
    priority (100 today, so 102)."""
    codes = _registered_codes()
    monkeypatch.setenv(ORDER_VARIABLE, "css_scraper, JustETF")

    priorities = {code: provider_priority(code) for code in codes}

    assert priorities == {code: 2 + _declared(code)[1] for code in codes} | {"css_scraper": 0, "justetf": 1}


def test_unlisted_providers_keep_their_declared_priorities_behind_the_listed_ones(monkeypatch: pytest.MonkeyPatch) -> None:
    """Behind the listed providers the others keep the order of their declarations: the length of the list plus each one."""
    _use_stand_ins(monkeypatch, {ALPHA: _plugin(priority=5), BETA: _plugin(priority=50), GAMMA: _plugin()})
    monkeypatch.setenv(ORDER_VARIABLE, GAMMA)

    assert {code: provider_priority(code) for code in (ALPHA, BETA, GAMMA)} == {ALPHA: 6, BETA: 51, GAMMA: 0}
    assert search_order([BETA, ALPHA, GAMMA]) == [GAMMA, ALPHA, BETA]


def test_an_unknown_order_code_takes_no_place_and_is_reported_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """A listed code no provider has takes no index and does not count in the length of the list; it is logged once."""
    codes = _registered_codes()
    monkeypatch.setenv(ORDER_VARIABLE, f"{UNKNOWN_CODE},css_scraper,justetf")

    with _captured() as events:
        priorities = {code: provider_priority(code) for code in codes}

    assert priorities == {code: 2 + _declared(code)[1] for code in codes} | {"css_scraper": 0, "justetf": 1}
    assert _unknown_reports(events) == [("warning", ORDER_VARIABLE, [UNKNOWN_CODE])]


def test_each_variable_reports_its_own_unknown_codes_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both variables listing only unknown codes: one report each, however many searches, and the order stays the given one."""
    codes = _registered_codes()
    monkeypatch.setenv(PREMIUM_VARIABLE, UNKNOWN_CODE)
    monkeypatch.setenv(ORDER_VARIABLE, UNKNOWN_CODE)

    with _captured() as events:
        orders = [search_order(codes), search_order(codes[::-1])]

    assert orders == [codes, codes[::-1]]
    assert sorted(_unknown_reports(events), key=lambda report: report[1]) == [("warning", ORDER_VARIABLE, [UNKNOWN_CODE]), ("warning", PREMIUM_VARIABLE, [UNKNOWN_CODE])]


# =============================================================================
# 3. THE SEARCH ORDER (search_order)
# =============================================================================


def test_without_the_variables_the_search_order_is_the_given_one() -> None:
    """D-X3: every shipped provider is at its defaults, so any arrangement of them is searched as given: the registry's
    own, its reverse, an interleaving."""
    codes = _registered_codes()

    for arrangement in (codes, codes[::-1], codes[1::2] + codes[::2]):
        assert search_order(arrangement) == arrangement


def test_premium_providers_from_the_variable_come_first_and_each_group_keeps_the_given_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """The listed providers move ahead and the others keep their order; among themselves the premium providers keep the
    given order too, since the PREMIUM list is a set: only ORDER ranks."""
    _registered_codes()
    monkeypatch.setenv(PREMIUM_VARIABLE, "justetf")
    assert search_order(["yfinance", "borsa_italiana", "justetf", "css_scraper"]) == ["justetf", "yfinance", "borsa_italiana", "css_scraper"]

    monkeypatch.setenv(PREMIUM_VARIABLE, "css_scraper,yfinance")
    assert search_order(["yfinance", "justetf", "css_scraper", "borsa_italiana"]) == ["yfinance", "css_scraper", "justetf", "borsa_italiana"]


def test_the_order_variable_puts_the_listed_providers_first_in_its_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """The listed providers come first, in the order of the list; the others follow in the given order."""
    _registered_codes()
    monkeypatch.setenv(ORDER_VARIABLE, "css_scraper,justetf")

    assert search_order(["yfinance", "justetf", "borsa_italiana", "css_scraper"]) == ["css_scraper", "justetf", "yfinance", "borsa_italiana"]


def test_premium_comes_before_the_order_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    """A premium provider listed last in ORDER still comes before a community one listed first: the tier sorts first."""
    _registered_codes()
    monkeypatch.setenv(PREMIUM_VARIABLE, "yfinance")
    monkeypatch.setenv(ORDER_VARIABLE, "justetf,css_scraper,yfinance")

    assert (provider_priority("justetf"), provider_priority("yfinance")) == (0, 2), "barrier: ORDER lists justetf first and yfinance last"
    assert search_order(["borsa_italiana", "css_scraper", "justetf", "yfinance"]) == ["yfinance", "justetf", "css_scraper", "borsa_italiana"]


def test_declared_tiers_and_priorities_order_the_search(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without the variables the declarations decide: the premium providers first, each tier by declared priority."""
    _use_stand_ins(monkeypatch, {ALPHA: _plugin(), BETA: _plugin(PREMIUM), GAMMA: _plugin(priority=10), DELTA: _plugin(PREMIUM, 5)})

    assert search_order([ALPHA, BETA, GAMMA, DELTA]) == [DELTA, BETA, GAMMA, ALPHA]


def test_repeated_codes_keep_their_places(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every occurrence of a code is kept: at the defaults ``a,b,a`` stays ``a,b,a`` (D-X3), and a premium code moves
    ahead with each of its occurrences."""
    _use_stand_ins(monkeypatch, {ALPHA: _plugin(), BETA: _plugin(), GAMMA: _plugin(PREMIUM)})

    assert search_order([ALPHA, BETA, ALPHA]) == [ALPHA, BETA, ALPHA]
    assert search_order([ALPHA, GAMMA, BETA, GAMMA, ALPHA]) == [GAMMA, GAMMA, ALPHA, BETA, ALPHA]


def test_search_rank_is_the_effective_tier_then_the_effective_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    """``search_rank(code)``: ``(0, priority)`` for a premium provider and ``(1, priority)`` for any other, an unknown code
    included, from the effective values, with the variables or without them.

    Red until ``search_rank`` exists: it is looked up here, when the case runs, so this case fails alone, with an
    ``AttributeError``.
    """
    _use_stand_ins(monkeypatch, _mixed_stand_ins())
    search_rank = provider_policy.search_rank
    codes = (ALPHA, BETA, GAMMA, DELTA, UNKNOWN_CODE)

    assert {code: search_rank(code) for code in codes} == {ALPHA: (1, 100), BETA: (1, 7), GAMMA: (0, 100), DELTA: (0, 5), UNKNOWN_CODE: (1, 100)}

    monkeypatch.setenv(PREMIUM_VARIABLE, ALPHA)
    monkeypatch.setenv(ORDER_VARIABLE, f"{BETA},{DELTA}")

    assert {code: search_rank(code) for code in codes} == {ALPHA: (0, 102), BETA: (1, 0), GAMMA: (1, 102), DELTA: (1, 1), UNKNOWN_CODE: (1, 102)}


def test_search_order_is_a_stable_sort_by_search_rank(monkeypatch: pytest.MonkeyPatch) -> None:
    """``search_order(codes)`` is ``sorted(codes, key=search_rank)``, the key the search sorts its providers by: one order
    for both, a repeated code at each of its places.

    Red until ``search_rank`` exists, as above.
    """
    _use_stand_ins(monkeypatch, _mixed_stand_ins())
    search_rank = provider_policy.search_rank
    given = [ALPHA, GAMMA, BETA, ALPHA, UNKNOWN_CODE, DELTA, GAMMA]

    expected = [DELTA, GAMMA, GAMMA, BETA, ALPHA, ALPHA, UNKNOWN_CODE]
    assert sorted(given, key=search_rank) == expected
    assert search_order(given) == expected

    monkeypatch.setenv(PREMIUM_VARIABLE, ALPHA)
    monkeypatch.setenv(ORDER_VARIABLE, f"{BETA},{DELTA}")

    expected = [ALPHA, ALPHA, BETA, DELTA, GAMMA, UNKNOWN_CODE, GAMMA]
    assert sorted(given, key=search_rank) == expected
    assert search_order(given) == expected


# =============================================================================
# 4. THE DECLARATIONS (AssetSourceProvider.__init_subclass__)
# =============================================================================


def test_a_provider_that_declares_nothing_is_community_at_the_default_priority() -> None:
    """The base class declares community at 100, and a subclass that declares nothing has both."""

    class _UndeclaredProvider(AssetSourceProvider):
        pass

    assert AssetSourceProvider.tier is COMMUNITY
    assert AssetSourceProvider.search_priority == DEFAULT_SEARCH_PRIORITY == 100
    assert (_UndeclaredProvider.tier, _UndeclaredProvider.search_priority) == (COMMUNITY, 100)


def test_valid_declarations_are_kept_and_a_tier_string_becomes_the_enum() -> None:
    """The string ``premium`` is accepted and stored as the ``FAProviderTier`` member; 0 is a valid priority, and so is a larger one."""

    class _StringPremiumProvider(AssetSourceProvider):
        tier = "premium"
        search_priority = 0

    class _EnumCommunityProvider(AssetSourceProvider):
        tier = FAProviderTier.COMMUNITY
        search_priority = 250

    assert _StringPremiumProvider.tier is PREMIUM, f"the tier string must become the enum member: {_StringPremiumProvider.tier!r}"
    assert _StringPremiumProvider.search_priority == 0
    assert (_EnumCommunityProvider.tier, _EnumCommunityProvider.search_priority) == (COMMUNITY, 250)


@pytest.mark.parametrize("value", [pytest.param("gold", id="unknown-tier"), pytest.param(None, id="none")])
def test_an_invalid_tier_stops_the_class_definition(value: object) -> None:
    """An invalid tier raises ``TypeError`` naming the class as soon as the class is defined, before any registration."""
    with pytest.raises(TypeError) as raised:

        class _InvalidTierProvider(AssetSourceProvider):
            tier = value

    assert "_InvalidTierProvider.tier" in str(raised.value), f"the error must name the class and the field: {raised.value}"


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(-1, id="negative"),
        pytest.param(True, id="bool"),
        pytest.param("1", id="string"),
        pytest.param(1.0, id="float"),
    ],
)
def test_an_invalid_search_priority_stops_the_class_definition(value: object) -> None:
    """A priority must be a whole number of at least 0, and a bool is not one: anything else raises ``TypeError`` naming the
    class as soon as the class is defined."""
    with pytest.raises(TypeError) as raised:

        class _InvalidPriorityProvider(AssetSourceProvider):
            search_priority = value

    assert "_InvalidPriorityProvider.search_priority" in str(raised.value), f"the error must name the class and the field: {raised.value}"


# =============================================================================
# 5. THE SEARCH (AssetSearchService.search)
# =============================================================================


@pytest.mark.asyncio
async def test_the_search_lists_a_declared_premium_provider_first(monkeypatch: pytest.MonkeyPatch, query: str) -> None:
    """The providers are queried in the search order and answer provider by provider in it: premium first, then the others as given."""
    _use_search_doubles(monkeypatch, {ALPHA: _plugin(), BETA: _plugin(), GAMMA: _plugin(PREMIUM)})

    response = await AssetSearchService.search(query, provider_codes=[ALPHA, BETA, GAMMA])

    _assert_searched_in(response, [GAMMA, ALPHA, BETA])


@pytest.mark.asyncio
async def test_with_every_value_at_its_default_the_search_keeps_the_given_order(monkeypatch: pytest.MonkeyPatch, query: str) -> None:
    """D-X3 through the search itself: no premium provider and no variable, so the providers answer in the given order."""
    _use_search_doubles(monkeypatch, {ALPHA: _plugin(), BETA: _plugin(), GAMMA: _plugin()})

    response = await AssetSearchService.search(query, provider_codes=[GAMMA, ALPHA, BETA])

    _assert_searched_in(response, [GAMMA, ALPHA, BETA])


@pytest.mark.asyncio
async def test_the_search_keeps_a_repeated_provider_at_each_of_its_places(monkeypatch: pytest.MonkeyPatch, query: str) -> None:
    """D-X3 with a code given twice: ``a,b,a`` is searched and answered as ``a,b,a``.

    Red until the fix lands: search.py ranks the providers in a dict keyed by code, where a code given twice keeps the
    place of its last occurrence and takes the first one along, so ``a,b,a`` comes out as ``b,a,a``.
    """
    _use_search_doubles(monkeypatch, {ALPHA: _plugin(), BETA: _plugin()})

    response = await AssetSearchService.search(query, provider_codes=[ALPHA, BETA, ALPHA])

    _assert_searched_in(response, [ALPHA, BETA, ALPHA])


@pytest.mark.asyncio
async def test_the_search_reads_both_variables_at_every_call(monkeypatch: pytest.MonkeyPatch, query: str) -> None:
    """The variables reach the search when it runs: the PREMIUM provider first, then the ORDER one, then the others as
    given; once they are gone, the next search is back to the given order, its items from the cache or not."""
    _use_search_doubles(monkeypatch, {ALPHA: _plugin(), BETA: _plugin(), GAMMA: _plugin()})
    monkeypatch.setenv(PREMIUM_VARIABLE, BETA)
    monkeypatch.setenv(ORDER_VARIABLE, GAMMA)

    _assert_searched_in(await AssetSearchService.search(query, provider_codes=[ALPHA, BETA, GAMMA]), [BETA, GAMMA, ALPHA])

    monkeypatch.delenv(PREMIUM_VARIABLE)
    monkeypatch.delenv(ORDER_VARIABLE)

    _assert_searched_in(await AssetSearchService.search(query, provider_codes=[ALPHA, BETA, GAMMA]), [ALPHA, BETA, GAMMA])
