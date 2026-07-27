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
- ``LIBREFOLIO_WEB_LINK_FINDER_ENGINE``   ``"duckduckgo"`` | ``"apikey"`` (default ``"duckduckgo"``)
- ``LIBREFOLIO_WEB_LINK_FINDER_API_KEY``  key for the ``"apikey"`` engine (default ``""``)
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

try:  # optional web-scraping deps (mirrors css_scraper's defensive import)
    import httpx
    from bs4 import BeautifulSoup

    _WEB_DEPS_OK = True
except ImportError:  # pragma: no cover - optional deps missing
    httpx = None  # type: ignore[assignment]
    BeautifulSoup = None  # type: ignore[assignment]
    _WEB_DEPS_OK = False

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Defaults / module state
# --------------------------------------------------------------------------- #
_DEFAULT_TIMEOUT = 6.0
_DEFAULT_MAX_RESULTS = 5
_CACHE_TTL_SECONDS = 15 * 60
_OVER_FETCH_FACTOR = 4  # fetch more raw hits than needed; the domain filter narrows

_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

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


def _unwrap_ddg(href: str | None) -> str | None:
    """Resolve a DuckDuckGo redirect link (``/l/?uddg=...``) to the real URL."""
    if not href:
        return None
    if href.startswith("//"):
        href = "https:" + href
    try:
        parsed = urllib.parse.urlparse(href)
    except ValueError:
        return None
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        uddg = urllib.parse.parse_qs(parsed.query).get("uddg", [None])[0]
        return urllib.parse.unquote(uddg) if uddg else None
    return href if href.startswith("http") else None


class DuckDuckGoEngine:
    """Free, keyless engine that scrapes the DuckDuckGo HTML endpoint.

    Fragile by nature (may rate-limit or serve an anomaly page); all errors are
    surfaced as exceptions and swallowed by :func:`find_candidate_urls`.
    """

    _ENDPOINT = "https://html.duckduckgo.com/html/"

    def search(self, query: str, *, timeout: float, max_results: int) -> list[str]:
        headers = {"User-Agent": _USER_AGENT, "Accept-Language": "en,it;q=0.8"}
        with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
            resp = client.get(self._ENDPOINT, params={"q": query})
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        urls: list[str] = []

        for anchor in soup.select("a.result__a"):
            real = _unwrap_ddg(anchor.get("href"))
            if real:
                urls.append(real)

        # Fallback: scan every anchor if the primary selector matched nothing.
        if not urls:
            for anchor in soup.find_all("a", href=True):
                real = _unwrap_ddg(anchor["href"])
                if real and real.startswith("http"):
                    urls.append(real)

        return urls[: max_results * _OVER_FETCH_FACTOR]


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
    engine = os.environ.get("LIBREFOLIO_WEB_LINK_FINDER_ENGINE", "duckduckgo").strip().lower()
    if engine in ("", "duckduckgo", "ddg"):
        return DuckDuckGoEngine()
    if engine in ("apikey", "api", "brave", "bing", "serpapi"):
        key = os.environ.get("LIBREFOLIO_WEB_LINK_FINDER_API_KEY", "").strip()
        if not key:
            logger.warning("web_link_finder: engine '%s' requires LIBREFOLIO_WEB_LINK_FINDER_API_KEY; disabling", engine)
            return None
        return ApiKeyEngine(key)
    logger.warning("web_link_finder: unknown engine '%s'; falling back to DuckDuckGo", engine)
    return DuckDuckGoEngine()


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
async def find_candidate_urls(
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
    if not query or not allowed_domains or not is_enabled() or not _WEB_DEPS_OK:
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
