"""web_link_finder unit tests + search orchestration augmentation.

The external engine is always MOCKED — no live ddgs/network call is made.
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


# ── DdgsEngine (ddgs metasearch transport) + engine selector ─────────────


class _FakeDDGS:
    """Stand-in for ``ddgs.DDGS``: records ctor + text() kwargs, returns canned hits."""

    last_init: dict | None = None
    last_text_kwargs: dict | None = None

    def __init__(self, *args, **kwargs):
        type(self).last_init = kwargs

    def text(self, query, **kwargs):
        type(self).last_text_kwargs = {"query": query, **kwargs}
        return [
            {"title": "A", "href": "https://www.borsaitaliana.it/a", "body": "..."},
            {"title": "B", "href": "https://www.borsaitaliana.it/b", "body": "..."},
            {"title": "no-href", "body": "..."},  # dropped: no href key
        ]


def test_ddgs_engine_extracts_hrefs(monkeypatch):
    monkeypatch.setattr(wlf, "DDGS", _FakeDDGS)
    out = wlf.DdgsEngine(region="wt-wt", backend="auto").search("q site:borsaitaliana.it", timeout=6.0, max_results=5)
    assert out == ["https://www.borsaitaliana.it/a", "https://www.borsaitaliana.it/b"]
    # region/backend forwarded; over-fetch factor applied to max_results
    assert _FakeDDGS.last_text_kwargs["region"] == "wt-wt"
    assert _FakeDDGS.last_text_kwargs["backend"] == "auto"
    assert _FakeDDGS.last_text_kwargs["max_results"] == 5 * wlf._OVER_FETCH_FACTOR


def test_ddgs_engine_empty_result(monkeypatch):
    class _EmptyDDGS:
        def __init__(self, *a, **k): ...
        def text(self, query, **k):
            return []

    monkeypatch.setattr(wlf, "DDGS", _EmptyDDGS)
    assert wlf.DdgsEngine(region="wt-wt", backend="auto").search("q", timeout=6.0, max_results=5) == []


@pytest.mark.asyncio
async def test_ddgs_engine_error_is_best_effort(monkeypatch):
    class _ErrDDGS:
        def __init__(self, *a, **k): ...
        def text(self, query, **k):
            raise RuntimeError("ddgs boom / rate-limit")

    monkeypatch.setattr(wlf, "DDGS", _ErrDDGS)
    # the engine surfaces the error…
    with pytest.raises(RuntimeError):
        wlf.DdgsEngine(region="wt-wt", backend="auto").search("q", timeout=6.0, max_results=5)
    # …and find_candidate_urls swallows it -> [] (best-effort, never fatal)
    assert await wlf.find_candidate_urls("q", ["borsaitaliana.it"]) == []


def test_build_engine_default_is_ddgs(monkeypatch):
    for var in ("LIBREFOLIO_WEB_LINK_FINDER_ENGINE", "LIBREFOLIO_WEB_LINK_FINDER_DDGS_REGION", "LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND"):
        monkeypatch.delenv(var, raising=False)
    eng = wlf._build_engine()
    assert isinstance(eng, wlf.DdgsEngine)
    assert eng._region == "wt-wt"
    assert eng._backend == "auto"


def test_build_engine_ddgs_region_backend_override(monkeypatch):
    monkeypatch.setenv("LIBREFOLIO_WEB_LINK_FINDER_ENGINE", "ddgs")
    monkeypatch.setenv("LIBREFOLIO_WEB_LINK_FINDER_DDGS_REGION", "it-it")
    monkeypatch.setenv("LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND", "google,bing")
    eng = wlf._build_engine()
    assert isinstance(eng, wlf.DdgsEngine)
    assert eng._region == "it-it"
    assert eng._backend == "google,bing"


def test_build_engine_apikey_without_key_is_disabled(monkeypatch):
    monkeypatch.setenv("LIBREFOLIO_WEB_LINK_FINDER_ENGINE", "apikey")
    monkeypatch.delenv("LIBREFOLIO_WEB_LINK_FINDER_API_KEY", raising=False)
    assert wlf._build_engine() is None


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


# ── 2-stage query building: rich stringone first, base query fallback ────


def test_build_link_finder_queries_rich_first_then_base():
    """With hints, the rich concatenation (ISIN + names + base) comes first, base last."""
    out = AssetSearchService._build_link_finder_queries(
        "EURIZON NEXT 2.0  DIVERSIFICATO 40 P",  # note the double space
        ["LU2178929613", "Eurizon Next 2.0 Alloc. Divers. 40 P Cap Eur", "EURIZON NEXT 2.0 DIVERSIFICATO 40 P"],
    )
    assert len(out) == 2
    assert out[0].startswith("LU2178929613 ")
    assert "Alloc. Divers. 40 P Cap Eur" in out[0]
    assert "DIVERSIFICATO 40 P" in out[0]  # base terms folded into the rich query too
    assert out[1] == "EURIZON NEXT 2.0 DIVERSIFICATO 40 P"  # base, double space collapsed


def test_build_link_finder_queries_no_hints_is_legacy_single():
    """Without hints the finder behaves exactly as before: a single base query."""
    assert AssetSearchService._build_link_finder_queries("LU2178929613", None) == ["LU2178929613"]


def test_build_link_finder_queries_dedup_when_rich_equals_base():
    """A hint equal to the base collapses rich and base into one candidate (no wasted call)."""
    assert AssetSearchService._build_link_finder_queries("LU2178929613", ["LU2178929613"]) == ["LU2178929613"]


@pytest.mark.asyncio
async def test_augment_uses_rich_query_first(monkeypatch):
    """The rich ISIN+name query is tried first; when it resolves, the base is never queried."""
    seen_queries: list[str] = []

    async def fake_find(query, domains, **kw):
        seen_queries.append(query)
        return ["https://example.com/good"] if ("LU000" in query and "Fund X Name" in query) else ["https://example.com/bad"]

    monkeypatch.setattr(wlf, "find_candidate_urls", fake_find)
    monkeypatch.setattr(wlf, "is_enabled", lambda: True)

    items = await AssetSearchService._augment_with_link_finder("fake", _FakeProvider(), "LU000", hints=["LU000", "Fund X Name"])
    assert len(items) == 1
    assert items[0]["identifier"] == "LU000"
    assert len(seen_queries) == 1
    assert "Fund X Name" in seen_queries[0]


@pytest.mark.asyncio
async def test_augment_falls_back_to_base_query(monkeypatch):
    """When the rich query is over-constrained (0 URLs), the bare base query is tried next."""
    seen_queries: list[str] = []

    async def fake_find(query, domains, **kw):
        seen_queries.append(query)
        return ["https://example.com/good"] if query == "LU000" else []

    monkeypatch.setattr(wlf, "find_candidate_urls", fake_find)
    monkeypatch.setattr(wlf, "is_enabled", lambda: True)

    items = await AssetSearchService._augment_with_link_finder("fake", _FakeProvider(), "LU000", hints=["LU000", "Overly Specific Name"])
    assert len(items) == 1
    assert items[0]["identifier"] == "LU000"
    assert seen_queries == ["LU000 Overly Specific Name", "LU000"]


# ── post-filter: narrow results to known technical identifiers ───────────


def test_filter_items_by_known_identifiers_keeps_only_matches():
    """A known ISIN among the terms keeps only the item(s) carrying it (drops siblings)."""
    items = [{"identifier": "LU2178929613"}, {"identifier": "LU2178929704"}, {"identifier": "LU2178929456"}]
    out = AssetSearchService._filter_items_by_known_identifiers(items, ["LU2178929613", "Some Fund Name"])
    assert out == [{"identifier": "LU2178929613"}]


def test_filter_items_by_known_identifiers_returns_all_when_no_match():
    """When no item identifier matches a known term, every candidate is kept (user chooses)."""
    items = [{"identifier": "LU2178929704"}, {"identifier": "LU2178929456"}]
    out = AssetSearchService._filter_items_by_known_identifiers(items, ["LU2178929613"])
    assert out == items


def test_filter_items_by_known_identifiers_passthrough_without_terms():
    """No known terms → no filtering."""
    items = [{"identifier": "X"}, {"identifier": "Y"}]
    assert AssetSearchService._filter_items_by_known_identifiers(items, None) == items
    assert AssetSearchService._filter_items_by_known_identifiers(items, ["   "]) == items


class _MultiFundProvider:
    """resolve_url returns a fund item whose identifier is the ISIN taken from the URL tail."""

    supports_url_resolution = True
    resolvable_url_domains = ["borsaitaliana.it"]

    async def resolve_url(self, url):
        isin = url.rsplit("/", 1)[-1]
        return {"identifier": isin, "identifier_type": "ISIN", "type": "FUND", "currency": "EUR", "provider_params": {"codice_fondo": isin}}


@pytest.mark.asyncio
async def test_augment_filters_link_finder_results_by_isin(monkeypatch):
    """End-to-end: a bare ISIN whose link-finder surfaces 3 sibling funds is narrowed to 1."""

    async def fake_find(query, domains, **kw):
        return [f"https://www.borsaitaliana.it/borsa/fondi/dettaglio/{isin}" for isin in ("LU2178929613", "LU2178929704", "LU2178929456")]

    monkeypatch.setattr(wlf, "find_candidate_urls", fake_find)
    monkeypatch.setattr(wlf, "is_enabled", lambda: True)

    items = await AssetSearchService._augment_with_link_finder("bi", _MultiFundProvider(), "LU2178929613", hints=["Eurizon Next 2.0"])
    assert [it["identifier"] for it in items] == ["LU2178929613"]


class _PairFundProvider:
    """resolve_url returns the canonical IT+EN pair for the fund (same identifier)."""

    supports_url_resolution = True
    resolvable_url_domains = ["borsaitaliana.it"]

    async def resolve_url(self, url):
        isin = url.rsplit("/", 1)[-1].split("?")[0]
        return [
            {"identifier": isin, "identifier_type": "ISIN", "type": "FUND", "currency": "EUR", "display_name": f"Fund {isin} \U0001f1ee\U0001f1f9", "provider_params": {"codice_fondo": isin, "language": "it"}},
            {"identifier": isin, "identifier_type": "ISIN", "type": "FUND", "currency": "EUR", "display_name": f"Fund {isin} \U0001f1ec\U0001f1e7", "provider_params": {"codice_fondo": isin, "language": "en"}},
        ]


@pytest.mark.asyncio
async def test_augment_flattens_and_dedups_list_resolve_url(monkeypatch):
    """resolve_url returning a list (IT+EN) is flattened; duplicate lang-URLs are de-duped."""

    async def fake_find(query, domains, **kw):
        # two URLs for the SAME fund (it + en language variants)
        return [
            "https://www.borsaitaliana.it/borsa/fondi/dettaglio/LU2178929613?lang=it",
            "https://www.borsaitaliana.it/borsa/fondi/dettaglio/LU2178929613?lang=en",
        ]

    monkeypatch.setattr(wlf, "find_candidate_urls", fake_find)
    monkeypatch.setattr(wlf, "is_enabled", lambda: True)

    items = await AssetSearchService._augment_with_link_finder("bi", _PairFundProvider(), "LU2178929613")
    assert len(items) == 2
    assert {it["provider_params"]["language"] for it in items} == {"it", "en"}
    assert all(it["identifier"] == "LU2178929613" for it in items)
