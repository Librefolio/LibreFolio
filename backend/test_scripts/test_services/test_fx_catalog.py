"""X-R8: the cached supported-currency catalog of the FX providers (``backend/app/services/fx/catalog.py``).

``GET /fx/providers`` used to ask every provider for its currency list on every request, and showed a provider with no
currencies whenever that fetch failed. ``get_supported_currencies_cached`` answers from a named TTL cache instead, and
these tests pin what that design promises:

  * a list that came back is sorted, cached for 24 hours and handed out as a copy;
  * a fetch that fails or exceeds ``timeout`` answers with the last list that provider returned (empty before its first
    success), cached for 5 minutes so the next requests neither retry nor wait;
  * clearing the cache from the cache panel forces a new fetch but keeps the last known lists;
  * concurrent calls on an empty cache fetch once, in every event loop of the process;
  * the cache is registered as ``fx_provider_currencies``, so the cache panel lists and clears it.

No network, no database, no server: every provider is a fake whose async ``get_supported_currencies`` counts its calls.
The only shared surface is this process's catalog cache and last known lists, emptied before and after every test by
an autouse fixture; each test also uses provider codes of its own.

The TTL of a stored entry is not readable through ``NamedCache`` (nor through theine's public API), so the TTLs are
pinned through the module constants, the cache's default TTL (what the panel shows) and the ``ttl`` each write asks
for, seen by a wrapper that delegates every call to the real cache. theine's internals are not touched.
"""

from __future__ import annotations

import asyncio
import time
from datetime import timedelta

import pytest

from backend.app.services.fx import catalog
from backend.app.utils.runtime.cache import clear_cache, list_caches
from backend.test_scripts.test_utils import print_section, print_success

CACHE_NAME = "fx_provider_currencies"
CONCURRENT_CALLERS = 8
# A deadline for a barrier, not a wait: the callers reach it within one turn of the event loop.
BARRIER_TIMEOUT_S = 10.0
# The gated fetch must never time out while the barrier fills, however loaded the machine.
GATED_FETCH_TIMEOUT_S = 30.0
# A provider that answers after SLOW_PROVIDER_S, asked with a timeout of FAST_TIMEOUT_S, has to be given up promptly:
# PROMPT_BOUND_S is a hundred times the timeout and still a sixth of the provider's delay.
SLOW_PROVIDER_S = 30.0
FAST_TIMEOUT_S = 0.05
PROMPT_BOUND_S = 5.0


class _FakeProvider:
    """An FX provider reduced to ``get_supported_currencies``: it counts its calls, then answers, fails or is slow."""

    def __init__(self, currencies: list[str] | None = None, *, error: Exception | None = None) -> None:
        self.currencies = list(currencies or [])
        self.error = error
        self.delay_s = 0.0
        self.gate: asyncio.Event | None = None
        self.calls = 0

    async def get_supported_currencies(self) -> list[str]:
        self.calls += 1
        if self.gate is not None:
            await self.gate.wait()
        if self.delay_s:
            # The slow provider being simulated, not a wait of the test: the catalog has to abandon it.
            await asyncio.sleep(self.delay_s)
        if self.error is not None:
            raise self.error
        return list(self.currencies)


class _ObservedCache:
    """The catalog's real cache seen through a window: which tasks found it empty, how long each write asked to be kept.

    Every call reaches the real ``NamedCache``, so the catalog behaves exactly as it does without the window.
    """

    def __init__(self, real) -> None:
        self._real = real
        self.missed_by: set[asyncio.Task] = set()
        self.kept_for: dict[str, timedelta] = {}

    def get(self, key):
        value, found = self._real.get(key)
        if not found:
            self.missed_by.add(asyncio.current_task())
        return value, found

    def set(self, key, value, *, ttl: timedelta | None = None) -> None:
        # NamedCache.set keeps an entry for ``ttl``, or for the cache's default TTL when the write gives none.
        self.kept_for[key] = ttl or timedelta(seconds=self._real.ttl)
        self._real.set(key, value, ttl=ttl)

    def __getattr__(self, name):
        return getattr(self._real, name)


class _WarningLog:
    """Stands in for the catalog's logger: keeps every warning (event and fields), ignores the other levels."""

    def __init__(self) -> None:
        self.warnings: list[str] = []

    def warning(self, event, *args, **fields) -> None:
        self.warnings.append(" ".join([str(event), *map(str, args), *(f"{key}={value}" for key, value in fields.items())]))

    def debug(self, *_args, **_fields) -> None:
        """Not what these tests look at."""

    info = error = exception = debug


def _observe_cache(monkeypatch) -> _ObservedCache:
    observed = _ObservedCache(catalog._currencies_cache)
    monkeypatch.setattr(catalog, "_currencies_cache", observed)
    return observed


def _record_warnings(monkeypatch) -> _WarningLog:
    log = _WarningLog()
    monkeypatch.setattr(catalog, "logger", log)
    return log


def _panel_entry() -> dict:
    """This cache's row in the cache panel, which lists exactly ``list_caches()`` (GET /settings/cache/status)."""
    entry = next((stats for stats in list_caches() if stats["name"] == CACHE_NAME), None)
    assert entry is not None, f"{CACHE_NAME} is not in list_caches(): the cache panel can neither show nor clear it"
    return entry


async def _concurrent_calls_on_empty_cache(code: str, provider: _FakeProvider, observed: _ObservedCache) -> list[list[str]]:
    """CONCURRENT_CALLERS calls at once; the provider answers only after every caller has found the cache empty.

    The gate is what makes the calls concurrent rather than merely numerous: without it the first caller could fetch,
    store and return before the others even look, and a single provider call would prove nothing.
    """
    observed.missed_by.clear()
    provider.gate = asyncio.Event()
    callers = [asyncio.create_task(catalog.get_supported_currencies_cached(code, provider, timeout=GATED_FETCH_TIMEOUT_S)) for _ in range(CONCURRENT_CALLERS)]
    try:
        async with asyncio.timeout(BARRIER_TIMEOUT_S):
            while len(observed.missed_by) < CONCURRENT_CALLERS:
                await asyncio.sleep(0)  # a yield to the callers: polling a condition under a deadline
    except TimeoutError:
        for caller in callers:
            caller.cancel()
        pytest.fail(f"only {len(observed.missed_by)} of {CONCURRENT_CALLERS} callers found the cache empty within {BARRIER_TIMEOUT_S} s")
    provider.gate.set()
    return await asyncio.gather(*callers)


@pytest.fixture(autouse=True)
def _empty_catalog():
    """Empty the process-wide catalog cache and last known lists before and after every test; nothing else global."""
    cache = catalog._currencies_cache
    cache.clear()
    catalog._last_known.clear()
    yield
    cache.clear()
    catalog._last_known.clear()


@pytest.mark.asyncio
async def test_first_call_fetches_a_sorted_list_then_the_cache_answers_with_copies():
    """X-R8: a fetched list is sorted and cached; later calls are answered by the cache, and no caller can edit it."""
    print_section("X-R8: one fetch, sorted, handed out as copies")
    provider = _FakeProvider(["USD", "EUR", "JPY"])

    first = await catalog.get_supported_currencies_cached("XR8_FRESH", provider)
    assert first == ["EUR", "JPY", "USD"]
    assert provider.calls == 1

    first.append("XXX")  # a caller editing its answer...
    provider.currencies = ["CHF"]  # ...and a provider that would now answer something else
    second = await catalog.get_supported_currencies_cached("XR8_FRESH", provider)
    assert second == ["EUR", "JPY", "USD"], "the cache answered with a list a caller had edited, or asked the provider again"
    assert provider.calls == 1, "the second call reached the provider instead of the cache"

    second.clear()
    assert await catalog.get_supported_currencies_cached("XR8_FRESH", provider) == ["EUR", "JPY", "USD"]
    assert provider.calls == 1
    print_success("Fetched once, sorted, and every answer is a copy of the cached list")


@pytest.mark.asyncio
async def test_failure_without_a_last_known_list_answers_empty_and_is_not_retried_for_five_minutes(monkeypatch):
    """X-R8: before any success a failing provider answers [] with one warning, and is not asked again until that expires."""
    print_section("X-R8: failure before any success")
    log = _record_warnings(monkeypatch)
    provider = _FakeProvider(error=RuntimeError("ECB unreachable"))

    assert await catalog.get_supported_currencies_cached("XR8_DOWN", provider) == []
    assert provider.calls == 1
    assert len(log.warnings) == 1, log.warnings
    assert "XR8_DOWN" in log.warnings[0] and "ECB unreachable" in log.warnings[0], log.warnings

    # While the 5-minute fallback entry lives it answers: no retry, and no second warning.
    assert await catalog.get_supported_currencies_cached("XR8_DOWN", provider) == []
    assert provider.calls == 1, "a failed provider was asked again while its fallback entry was cached"
    assert len(log.warnings) == 1, log.warnings

    # The fallback entry expires (simulated by deleting it): the next call asks the provider again.
    catalog._currencies_cache.delete("XR8_DOWN")
    provider.error = None
    provider.currencies = ["NOK", "CHF"]
    assert await catalog.get_supported_currencies_cached("XR8_DOWN", provider) == ["CHF", "NOK"]
    assert provider.calls == 2
    print_success("[] and one warning; no retry while the fallback is cached; retried once it expired")


@pytest.mark.asyncio
async def test_failure_after_a_success_answers_the_last_known_list_even_after_a_cache_clear(monkeypatch):
    """X-R8: once a provider has answered, its failures answer with that list, also after the cache panel clears the cache."""
    print_section("X-R8: failure after a success")
    log = _record_warnings(monkeypatch)
    provider = _FakeProvider(["USD", "GBP"])
    assert await catalog.get_supported_currencies_cached("XR8_FLAKY", provider) == ["GBP", "USD"]

    provider.error = ConnectionError("ECB unreachable")
    catalog._currencies_cache.delete("XR8_FLAKY")  # the 24 h entry expires while the provider is down
    stale = await catalog.get_supported_currencies_cached("XR8_FLAKY", provider)
    assert stale == ["GBP", "USD"], "a provider that had answered once fell back to an empty list"
    assert provider.calls == 2
    assert len(log.warnings) == 1, log.warnings

    stale.clear()  # the fallback is handed out as a copy too
    assert await catalog.get_supported_currencies_cached("XR8_FLAKY", provider) == ["GBP", "USD"]
    assert provider.calls == 2, "a failed provider was asked again while its fallback entry was cached"

    # What the cache panel's clear does: a new fetch, which fails again and still has the last known list to give.
    assert clear_cache(CACHE_NAME) is True
    assert await catalog.get_supported_currencies_cached("XR8_FLAKY", provider) == ["GBP", "USD"]
    assert provider.calls == 3, "clearing the cache did not force a new fetch"
    assert len(log.warnings) == 2, log.warnings
    print_success("The last known list answers every failure, and survives a cache clear")


@pytest.mark.asyncio
async def test_a_provider_slower_than_the_timeout_is_given_up_promptly_for_the_last_known_list(monkeypatch):
    """X-R8: a provider slower than ``timeout`` does not hold the catalog: the fallback comes back promptly and stays cached."""
    print_section("X-R8: slow provider")
    log = _record_warnings(monkeypatch)
    provider = _FakeProvider(["USD", "EUR"])
    assert await catalog.get_supported_currencies_cached("XR8_SLOW", provider) == ["EUR", "USD"]

    provider.delay_s = SLOW_PROVIDER_S
    catalog._currencies_cache.delete("XR8_SLOW")
    started = time.monotonic()
    answer = await catalog.get_supported_currencies_cached("XR8_SLOW", provider, timeout=FAST_TIMEOUT_S)
    elapsed = time.monotonic() - started

    assert answer == ["EUR", "USD"]
    assert elapsed < PROMPT_BOUND_S, f"answered after {elapsed:.2f} s with a timeout of {FAST_TIMEOUT_S} s (provider delay {SLOW_PROVIDER_S} s)"
    assert provider.calls == 2
    assert len(log.warnings) == 1 and "XR8_SLOW" in log.warnings[0], log.warnings

    # The fallback entry spares the next request the same wait.
    assert await catalog.get_supported_currencies_cached("XR8_SLOW", provider, timeout=FAST_TIMEOUT_S) == ["EUR", "USD"]
    assert provider.calls == 2
    print_success(f"Fallback after {elapsed:.3f} s instead of {SLOW_PROVIDER_S:.0f} s, and no second wait")


@pytest.mark.asyncio
async def test_concurrent_calls_on_an_empty_cache_fetch_once(monkeypatch):
    """X-R8: callers that all find the cache empty at once cause a single provider call, and all get the same list."""
    print_section("X-R8: concurrent calls on an empty cache")
    observed = _observe_cache(monkeypatch)
    provider = _FakeProvider(["SEK", "NOK", "DKK"])

    answers = await _concurrent_calls_on_empty_cache("XR8_RUSH", provider, observed)

    assert provider.calls == 1, f"{provider.calls} fetches for {CONCURRENT_CALLERS} concurrent callers"
    assert answers == [["DKK", "NOK", "SEK"]] * CONCURRENT_CALLERS
    print_success(f"{CONCURRENT_CALLERS} concurrent callers, one fetch, one answer")


def test_concurrent_calls_fetch_once_in_a_second_event_loop_too(monkeypatch):
    """X-R8: the fetch lock belongs to one event loop; a second loop gets its own instead of tripping over the first.

    A process runs more than one event loop (pytest-asyncio gives each test its own). One asyncio.Lock shared by all of
    them binds to the loop of its first contended acquire, and the next contended acquire from another loop raises
    "is bound to a different event loop". So: contend in a first loop, let the entry expire, contend in a second one.
    """
    print_section("X-R8: concurrent calls in two event loops")
    observed = _observe_cache(monkeypatch)
    for loop_number in (1, 2):
        provider = _FakeProvider(["SEK", "NOK", "DKK"])
        answers = asyncio.run(_concurrent_calls_on_empty_cache("XR8_LOOPS", provider, observed))
        assert provider.calls == 1, f"event loop {loop_number}: {provider.calls} fetches for {CONCURRENT_CALLERS} concurrent callers"
        assert answers == [["DKK", "NOK", "SEK"]] * CONCURRENT_CALLERS
        catalog._currencies_cache.delete("XR8_LOOPS")  # the entry expires: the next loop has to fetch, and contend, again
    print_success("One fetch per event loop, and no lock shared between loops")


@pytest.mark.asyncio
async def test_the_cache_panel_lists_and_clears_the_catalog_cache():
    """X-R8: the cache is registered as fx_provider_currencies, so the cache panel counts its entries and can clear them."""
    print_section("X-R8: visible in the cache panel")
    panel = _panel_entry()
    assert panel["ttl"] == 24 * 3600, panel
    provider = _FakeProvider(["EUR", "CHF"])

    await catalog.get_supported_currencies_cached("XR8_PANEL", provider)
    assert _panel_entry()["current_size"] == panel["current_size"] + 1, "the panel does not count the entry the catalog just stored"

    assert clear_cache(CACHE_NAME) is True
    assert _panel_entry()["current_size"] == 0
    await catalog.get_supported_currencies_cached("XR8_PANEL", provider)
    assert provider.calls == 2, "the panel's clear did not reach the cache the catalog reads"
    print_success(f"{CACHE_NAME} is listed with a 24 h TTL, counts the catalog's entries, and its clear forces a fetch")


@pytest.mark.asyncio
async def test_a_list_is_kept_for_a_day_and_a_fallback_for_five_minutes(monkeypatch):
    """X-R8: a fetched list is stored with the cache's 24 h default, a fallback with the 5-minute retry delay.

    The TTL of a stored entry is not readable through NamedCache, so this pins the constants and the ttl each write
    asks for (none meaning the cache default), observed through a wrapper around the real cache.
    """
    print_section("X-R8: 24 h for a list, 5 minutes for a fallback")
    assert catalog.SUPPORTED_CURRENCIES_TTL_S == 24 * 3600
    assert catalog.RETRY_AFTER_FAILURE_S == 5 * 60
    _record_warnings(monkeypatch)  # the failure below warns; keep it out of the output
    observed = _observe_cache(monkeypatch)

    await catalog.get_supported_currencies_cached("XR8_TTL_OK", _FakeProvider(["EUR"]))
    await catalog.get_supported_currencies_cached("XR8_TTL_KO", _FakeProvider(error=RuntimeError("provider down")))

    assert observed.kept_for == {"XR8_TTL_OK": timedelta(hours=24), "XR8_TTL_KO": timedelta(minutes=5)}
    print_success("A fetched list is kept 24 h, a fallback 5 minutes")
