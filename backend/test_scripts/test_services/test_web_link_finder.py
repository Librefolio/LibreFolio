"""web_link_finder unit tests + search orchestration augmentation.

The external engine is always MOCKED — no live DuckDuckGo call is made.
"""

import pytest

from backend.app.services import web_link_finder as wlf
from backend.app.services.asset_source import AssetSearchService


class _FakeEngine:
    """Returns a fixed raw URL list and records how many times it was queried."""

    def __init__(self, urls):
        self.urls = urls
        self.calls = 0

    def search(self, query, *, timeout, max_results):
        self.calls += 1
        return list(self.urls)


class _RaisingEngine:
    def search(self, query, *, timeout, max_results):
        raise RuntimeError("simulated rate-limit / anomaly page")


@pytest.fixture(autouse=True)
def _clear_cache():
    wlf.clear_cache()
    yield
    wlf.clear_cache()


@pytest.mark.asyncio
async def test_filter_dedup_and_cache(monkeypatch):
    raw = [
        "https://www.borsaitaliana.it/borsa/fondi/dettaglio/2FADB602822.html",
        "https://www.borsaitaliana.it/borsa/fondi/dettaglio/2FADB602822.html#frag",  # dup after # strip
        "https://evil.example.com/phish",  # off-domain -> dropped
        "https://finance.yahoo.com/quote/X",  # off-domain -> dropped
        "https://borsaitaliana.it/borsa/fondi/dettaglio/OTHER.html",  # bare domain kept
    ]
    eng = _FakeEngine(raw)
    monkeypatch.setattr(wlf, "_build_engine", lambda: eng)

    out = await wlf.find_candidate_urls("EURIZON NEXT 2.0", ["borsaitaliana.it"], max_results=5, path_hint="borsa/fondi/dettaglio")

    assert eng.calls == 1
    assert all("borsaitaliana.it" in u for u in out)
    assert "https://evil.example.com/phish" not in out
    assert "https://finance.yahoo.com/quote/X" not in out
    assert out.count("https://www.borsaitaliana.it/borsa/fondi/dettaglio/2FADB602822.html") == 1
    assert len(out) == 2

    # identical second call is served from cache (engine not re-invoked)
    out2 = await wlf.find_candidate_urls("EURIZON NEXT 2.0", ["borsaitaliana.it"], max_results=5, path_hint="borsa/fondi/dettaglio")
    assert eng.calls == 1
    assert out2 == out


@pytest.mark.asyncio
async def test_max_results_cap(monkeypatch):
    eng = _FakeEngine([f"https://borsaitaliana.it/p/{i}.html" for i in range(10)])
    monkeypatch.setattr(wlf, "_build_engine", lambda: eng)

    out = await wlf.find_candidate_urls("q", ["borsaitaliana.it"], max_results=3)
    assert len(out) == 3


@pytest.mark.asyncio
async def test_engine_error_is_best_effort(monkeypatch):
    monkeypatch.setattr(wlf, "_build_engine", lambda: _RaisingEngine())
    assert await wlf.find_candidate_urls("q", ["borsaitaliana.it"]) == []


@pytest.mark.asyncio
async def test_disabled_via_env(monkeypatch):
    monkeypatch.setenv("LIBREFOLIO_WEB_LINK_FINDER_ENABLED", "0")
    assert wlf.is_enabled() is False
    assert await wlf.find_candidate_urls("q", ["borsaitaliana.it"]) == []


@pytest.mark.asyncio
async def test_guards_empty_query_and_no_domains():
    assert await wlf.find_candidate_urls("", ["borsaitaliana.it"]) == []
    assert await wlf.find_candidate_urls("q", []) == []


def test_matches_allowed_subdomain_rule():
    assert wlf._matches_allowed("https://www.borsaitaliana.it/x", ["borsaitaliana.it"]) is True
    assert wlf._matches_allowed("https://borsaitaliana.it/x", ["borsaitaliana.it"]) is True
    assert wlf._matches_allowed("https://notborsaitaliana.it/x", ["borsaitaliana.it"]) is False
    assert wlf._matches_allowed("https://evil.com/borsaitaliana.it", ["borsaitaliana.it"]) is False


# ── orchestration: AssetSearchService._augment_with_link_finder ──────────


class _FakeProvider:
    supports_url_resolution = True
    resolvable_url_domains = ["example.com"]

    async def resolve_url(self, url):
        if url.endswith("/good"):
            return {"identifier": "LU000", "identifier_type": "ISIN", "display_name": "Fund X", "currency": "EUR", "type": "FUND", "provider_params": {"codice_fondo": "ABC"}}
        return None


class _NoSupportProvider:
    supports_url_resolution = False
    resolvable_url_domains = []

    async def resolve_url(self, url):  # pragma: no cover - never called
        return None


@pytest.mark.asyncio
async def test_augment_with_link_finder_resolves(monkeypatch):
    async def fake_find(query, domains, **kw):
        assert domains == ["example.com"]
        return ["https://example.com/good", "https://example.com/bad"]

    monkeypatch.setattr(wlf, "find_candidate_urls", fake_find)
    monkeypatch.setattr(wlf, "is_enabled", lambda: True)

    items = await AssetSearchService._augment_with_link_finder("fake", _FakeProvider(), "some query")
    assert len(items) == 1
    assert items[0]["identifier"] == "LU000"
    assert items[0]["provider_params"]["codice_fondo"] == "ABC"


@pytest.mark.asyncio
async def test_augment_short_circuits_when_unsupported(monkeypatch):
    monkeypatch.setattr(wlf, "is_enabled", lambda: True)
    items = await AssetSearchService._augment_with_link_finder("ns", _NoSupportProvider(), "q")
    assert items == []
