"""Best-effort external web link finder.

Turns a free-text query (or ISIN) into candidate **provider-domain** page URLs.
It is used ONLY at asset-search time, as a *last resort*, when a provider's own
on-site search returns nothing. It is deliberately best-effort: any failure
(rate-limit, anomaly page, network/parse error) yields an empty list and is
**never fatal**.

Layering rationale
------------------
This module lives in LibreFolio (NOT inside a scraping library) so that the
choice of external search engine is a LibreFolio concern, kept out of the
per-provider scraping code. Providers consume the URLs it returns via their
``resolve_url`` capability (URL -> search-item), the inverse of ``get_asset_url``.

Key invariant
-------------
Price fetches (frequent, automated) must NEVER call this module. External search
is only ever hit during interactive asset search. Once an asset is created, it is
priced by its stored provider params (e.g. a fund's internal code), not by search.

Configuration (environment variables, all optional)
----------------------------------------------------
- ``LIBREFOLIO_WEB_LINK_FINDER_ENABLED``  ``"1"``/``"0"`` (default ``"1"``)
- ``LIBREFOLIO_WEB_LINK_FINDER_ENGINE``   ``"ddgs"`` | ``"apikey"`` (default ``"ddgs"``)
- ``LIBREFOLIO_WEB_LINK_FINDER_API_KEY``  key for the ``"apikey"`` engine (default ``""``)
- ``LIBREFOLIO_WEB_LINK_FINDER_DDGS_REGION``   ddgs region, e.g. ``"wt-wt"``/``"it-it"`` (default ``"wt-wt"``)
- ``LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND``  ddgs backend(s), e.g. ``"auto"``/``"google,bing"`` (default ``"auto"``)
- ``LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT``  per-request timeout, seconds (default ``"6"``)
- ``LIBREFOLIO_WEB_LINK_FINDER_MAX``      max candidate URLs returned (default ``"5"``)
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import urllib.parse
from typing import Protocol, runtime_checkable

try:  # optional metasearch dep (graceful degradation, mirrors css_scraper's defensive import)
    from ddgs import DDGS

    _DDGS_OK = True
except ImportError:  # pragma: no cover - optional dep missing
    DDGS = None  # type: ignore[assignment,misc]
    _DDGS_OK = False

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Defaults / module state
# --------------------------------------------------------------------------- #
_DEFAULT_TIMEOUT = 6.0
_DEFAULT_MAX_RESULTS = 5
_CACHE_TTL_SECONDS = 15 * 60
_OVER_FETCH_FACTOR = 4  # fetch more raw hits than needed; the domain filter narrows

# Tiny TTL cache keyed by (query, domains, path_hint, max): value = (expires_at, urls).
_cache: dict[tuple, tuple[float, list[str]]] = {}


# --------------------------------------------------------------------------- #
# Search-engine interface + implementations
# --------------------------------------------------------------------------- #
@runtime_checkable
class _SearchEngine(Protocol):
    """A pluggable external search backend.

    ``search`` is **synchronous** (it does blocking I/O) and is always invoked
    from a worker thread via ``asyncio.to_thread``. It must return a list of raw
    result URLs (unfiltered); domain filtering happens in the caller.
    """

    def search(self, query: str, *, timeout: float, max_results: int) -> list[str]: ...


class DdgsEngine:
    """Multi-engine metasearch via the ``ddgs`` library (the maintained successor of
    ``duckduckgo_search``).

    Aggregates several upstream engines (bing / brave / google / duckduckgo /
    startpage / …) behind one synchronous ``text()`` call with ``backend="auto"``,
    so a single rate-limited upstream can no longer starve the result set. Transport
    or library errors are surfaced as exceptions and swallowed by
    :func:`find_candidate_urls`; a legitimate empty result set is returned as ``[]``.
    """

    def __init__(self, *, region: str, backend: str) -> None:
        self._region = region
        self._backend = backend

    def search(self, query: str, *, timeout: float, max_results: int) -> list[str]:
        if DDGS is None:  # pragma: no cover - guarded by _build_engine / find_candidate_urls
            return []
        results = DDGS(timeout=int(timeout) or None).text(
            query,
            region=self._region,
            max_results=max_results * _OVER_FETCH_FACTOR,
            backend=self._backend,
        )
        return [href for href in (r.get("href") for r in results) if href]


class ApiKeyEngine:
    """Seam for a paid search API (Brave / Bing / SerpAPI).

    Intentionally a stub: it establishes the configuration + interface so a real
    implementation can drop in later without touching call sites. Until then it
    returns no results (logged once per call).
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def search(self, query: str, *, timeout: float, max_results: int) -> list[str]:
        logger.warning("web_link_finder: API-key engine selected but not implemented; returning no results")
        return []


def _build_engine() -> _SearchEngine | None:
    """Instantiate the configured engine, or ``None`` if it can't be used."""
    engine = os.environ.get("LIBREFOLIO_WEB_LINK_FINDER_ENGINE", "ddgs").strip().lower()
    if engine in ("apikey", "api", "brave", "bing", "serpapi"):
        key = os.environ.get("LIBREFOLIO_WEB_LINK_FINDER_API_KEY", "").strip()
        if not key:
            logger.warning("web_link_finder: engine '%s' requires LIBREFOLIO_WEB_LINK_FINDER_API_KEY; disabling", engine)
            return None
        return ApiKeyEngine(key)
    if engine == "searxng":
        # Reserved for the deferred SearXNG metasearch adapter (Fase B); until then use ddgs.
        logger.debug("web_link_finder: engine 'searxng' is not implemented yet (Fase B); using ddgs")
    elif engine not in ("", "ddgs", "duckduckgo", "ddg"):
        logger.warning("web_link_finder: unknown engine '%s'; falling back to ddgs", engine)
    if not _DDGS_OK:  # pragma: no cover - ddgs is a hard dependency in the Pipfile
        logger.warning("web_link_finder: ddgs library not importable; link-finder disabled")
        return None
    region = os.environ.get("LIBREFOLIO_WEB_LINK_FINDER_DDGS_REGION", "wt-wt").strip() or "wt-wt"
    backend = os.environ.get("LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND", "auto").strip() or "auto"
    return DdgsEngine(region=region, backend=backend)


# --------------------------------------------------------------------------- #
# Config helpers
# --------------------------------------------------------------------------- #
def is_enabled() -> bool:
    """Whether the link-finder may run (default: on, as a last resort)."""
    return os.environ.get("LIBREFOLIO_WEB_LINK_FINDER_ENABLED", "1").strip().lower() in ("1", "true", "yes", "on")


def _env_float(name: str, default: float) -> float:
    try:
        raw = os.environ.get(name, "").strip()
        return float(raw) if raw else default
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        raw = os.environ.get(name, "").strip()
        return int(raw) if raw else default
    except ValueError:
        return default


# --------------------------------------------------------------------------- #
# URL helpers + cache
# --------------------------------------------------------------------------- #
def _matches_allowed(url: str, allowed_domains: list[str]) -> bool:
    """True if ``url``'s host equals or is a sub-domain of an allowed domain."""
    try:
        netloc = urllib.parse.urlparse(url).netloc.lower()
    except ValueError:
        return False
    # Strip an optional ``user:pass@`` and ``:port`` suffix.
    netloc = netloc.rsplit("@", 1)[-1].split(":", 1)[0]
    return any(netloc == d or netloc.endswith("." + d) for d in (dom.lower() for dom in allowed_domains))


def _cache_get(key: tuple) -> list[str] | None:
    entry = _cache.get(key)
    if not entry:
        return None
    expires_at, urls = entry
    if time.monotonic() > expires_at:
        _cache.pop(key, None)
        return None
    return list(urls)


def _cache_set(key: tuple, urls: list[str]) -> None:
    _cache[key] = (time.monotonic() + _CACHE_TTL_SECONDS, list(urls))


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
async def find_candidate_urls(  # noqa: C901 — guard clauses + URL filter loop, no nested logic
    query: str,
    allowed_domains: list[str],
    *,
    max_results: int | None = None,
    path_hint: str | None = None,
) -> list[str]:
    """Return best-effort provider-domain URLs matching ``query``.

    Args:
        query: Free-text query or ISIN.
        allowed_domains: Domains to keep (e.g. ``["borsaitaliana.it"]``); results
            outside these are discarded. The first domain is also used to scope the
            engine query via ``site:``.
        max_results: Max URLs to return (defaults to the configured value, 5).
        path_hint: Optional path fragment to bias the ``site:`` query
            (e.g. ``"borsa/fondi/dettaglio"``).

    Returns:
        A de-duplicated list of URLs on the allowed domains (possibly empty).
        **Never raises** — any error yields ``[]``.
    """
    query = (query or "").strip()
    if not query or not allowed_domains or not is_enabled() or not _DDGS_OK:
        return []

    if max_results is None:
        max_results = _env_int("LIBREFOLIO_WEB_LINK_FINDER_MAX", _DEFAULT_MAX_RESULTS)

    cache_key = (query.lower(), tuple(sorted(d.lower() for d in allowed_domains)), (path_hint or "").strip("/"), max_results)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    engine = _build_engine()
    if engine is None:
        _cache_set(cache_key, [])
        return []

    timeout = _env_float("LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT", _DEFAULT_TIMEOUT)

    primary = allowed_domains[0].lower()
    site = f"{primary}/{path_hint.strip('/')}" if path_hint else primary
    scoped_query = f"{query} site:{site}"

    try:
        raw = await asyncio.to_thread(engine.search, scoped_query, timeout=timeout, max_results=max_results)
    except Exception as err:  # best-effort: swallow everything
        logger.debug("web_link_finder: engine error for '%s': %s", scoped_query, err)
        _cache_set(cache_key, [])
        return []

    seen: set[str] = set()
    out: list[str] = []
    for url in raw:
        if not _matches_allowed(url, allowed_domains):
            continue
        norm = url.split("#", 1)[0]
        if norm in seen:
            continue
        seen.add(norm)
        out.append(norm)
        if len(out) >= max_results:
            break

    _cache_set(cache_key, out)
    if out:
        logger.info("web_link_finder: %d candidate URL(s) for '%s' on %s", len(out), query, allowed_domains)
    return out


def clear_cache() -> None:
    """Clear the in-memory TTL cache (used by tests)."""
    _cache.clear()
