"""Cross-provider asset search orchestration."""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator, Optional

import structlog
from pydantic import ValidationError

from backend.app.db.models import (
    AssetType,
)
from backend.app.schemas.provider import (
    FAProviderSearchResponse,
    FAProviderSearchResultItem,
    FAQuoteBaseSuggestion,
)
from backend.app.services.assets import core, provider_policy, web_link_finder
from backend.app.services.assets.base import AssetRateLimitedError, AssetSourceError, AssetSourceProvider
from backend.app.services.assets.registry import AssetProviderRegistry

logger = structlog.get_logger(__name__)


def _quote_base_suggestion(code: str, item: dict) -> FAQuoteBaseSuggestion | None:
    """A search result's quote base suggestion (Z-32 d), from the plugin's key ``quote_base_suggestion``: one that does
    not validate is dropped with a warning, and the result stays."""
    raw = item.get("quote_base_suggestion")
    if raw is None:
        return None
    try:
        return FAQuoteBaseSuggestion.model_validate(raw)
    except ValidationError as error:
        logger.warning("Search result: quote_base_suggestion dropped", provider=code, identifier=item.get("identifier"), error=str(error))
        return None


def _default_search_codes() -> list[str]:
    """The providers a search asks when the request names none: every registered one but the test-only ones (X-R24),
    as ``GET /assets/provider`` lists them. A provider named in the request is asked whatever its flag, and a code the
    registry does not know counts as not test-only."""
    return [p["code"] for p in AssetProviderRegistry.list_providers() if not getattr(AssetProviderRegistry.get_plugin(p["code"]), "test_only", False)]


class AssetSearchService:
    """
    Service for searching assets across multiple providers.

    Features:
    - Parallel execution using asyncio.gather for performance
    - Graceful error handling per provider (errors don't fail entire search)
    - Provider filtering support
    - Aggregated results with metadata
    """

    @staticmethod
    def _build_link_finder_queries(query: str, hints: Optional[list[str]] = None) -> list[str]:
        """Ordered web-search queries for the link-finder: rich stringone first, base query last.

        The rich query concatenates every hint (all report-extracted identifiers +
        candidate names) together with the base ``query``, in the order supplied, deduped
        and whitespace-collapsed. Nothing is sanitised, truncated or reordered — the whole
        concatenation is handed to the web search, which is left to do the ranking. If the rich
        query yields no URLs the finder falls back to the bare base query. When no hints
        are supplied this returns just the base query (legacy behaviour).
        """
        base = " ".join((query or "").split())
        terms: list[str] = []
        seen: set[str] = set()

        def _add(value: str) -> None:
            value = " ".join((value or "").split())
            key = value.lower()
            if value and key not in seen:
                seen.add(key)
                terms.append(value)

        for hint in hints or []:
            _add(hint)
        _add(base)  # keep the base query terms inside the rich string too

        rich = " ".join(terms).strip()

        candidates: list[str] = []
        seen_candidates: set[str] = set()
        for candidate in (rich, base):
            candidate = candidate.strip()
            if candidate and candidate.lower() not in seen_candidates:
                seen_candidates.add(candidate.lower())
                candidates.append(candidate)
        return candidates

    @staticmethod
    async def _augment_with_link_finder(code: str, provider: AssetSourceProvider, query: str, hints: Optional[list[str]] = None) -> list[dict]:  # noqa: C901 — best-effort fallback pipeline, nested dedup loops
        """Last-resort fallback when a provider's on-site search yields nothing.

        Uses the external :mod:`web_link_finder` to turn a query into candidate
        provider-domain URLs, then asks the provider to ``resolve_url`` each into a
        search-item dict. Best-effort: any failure returns ``[]`` and is never fatal.

        When ``hints`` are supplied (report-extracted identifiers + names) the finder
        tries a rich concatenated query first and falls back to the bare ``query`` — a
        specific ISIN+name query resolves to a single fund page, whereas a bare ISIN can
        surface several sibling share classes.

        Only runs for providers that opt in via ``supports_url_resolution`` and only
        when the link-finder is enabled. Provider ``resolve_url`` calls go through the
        dedicated provider thread, like every other provider method.
        """
        try:
            if not getattr(provider, "supports_url_resolution", False) or not web_link_finder.is_enabled():
                return []

            for candidate_query in AssetSearchService._build_link_finder_queries(query, hints):
                urls = await web_link_finder.find_candidate_urls(candidate_query, provider.resolvable_url_domains)
                if not urls:
                    continue

                items: list[dict] = []
                seen_items: set[tuple[str, str]] = set()

                async def _resolve_one(u: str):
                    try:
                        return await core.call_provider(provider, lambda: provider.resolve_url(u), timeout=20.0)
                    except Exception as e:
                        logger.debug(f"link-finder: resolve_url failed for '{u}' on provider '{code}': {e}")
                        return None

                # Resolve candidate URLs concurrently — this was a sequential ``for url in urls``
                # loop whose per-URL latencies (each up to the 20s provider timeout) SUMMED, the
                # dominant cost of a web-fallback search. ``asyncio.to_thread`` runs each provider
                # call on its own worker thread, so total time ≈ the slowest URL instead of the sum.
                # ``gather`` preserves argument order, so dedup priority (first URL wins) is unchanged.
                resolved_list = await asyncio.gather(*[_resolve_one(u) for u in urls])
                for resolved in resolved_list:
                    if not resolved:
                        continue
                    # resolve_url may return one item or the full canonical set (list),
                    # e.g. one row per language. Flatten and de-dup by (identifier, language)
                    # so sibling language-URLs of the same instrument don't pile up.
                    for it in resolved if isinstance(resolved, list) else [resolved]:
                        if not it:
                            continue
                        key = (str(it.get("identifier", "")).strip().upper(), str((it.get("provider_params") or {}).get("language", "")).strip().lower())
                        if key in seen_items:
                            continue
                        seen_items.add(key)
                        items.append(it)

                if items:
                    items = AssetSearchService._filter_items_by_known_identifiers(items, [*(hints or []), query])
                    for it in items:
                        it["_via_web"] = True
                    logger.info(f"link-finder: provider '{code}' resolved {len(items)} item(s) via web for '{candidate_query}'")
                    return items

            return []
        except Exception as e:
            logger.debug(f"link-finder: augmentation error on provider '{code}': {e}")
            return []

    @staticmethod
    def _filter_items_by_known_identifiers(items: list[dict], known_terms: Optional[list[str]]) -> list[dict]:
        """Narrow link-finder results to those whose identifier matches a known one.

        The web link-finder can surface sibling instruments (e.g. a bare ISIN search on
        Borsa Italiana returns every share class of a fund family). When we already hold
        technical identifiers — the searched query and any report-extracted ``hints`` —
        and at least one resolved item's ``identifier`` matches one of them, only the
        matching items are kept. If nothing matches (the terms were only free-text names,
        or none of the pages carried a known identifier) every item is returned so the
        user still gets candidates to choose from. Matching is case-insensitive and
        whitespace-trimmed; non-identifier terms (names) are inert because they never
        equal an ISIN/ticker identifier.
        """
        if not items or not known_terms:
            return items
        known = {t.strip().upper() for t in known_terms if t and t.strip()}
        if not known:
            return items
        matching = [it for it in items if str(it.get("identifier", "")).strip().upper() in known]
        return matching or items

    @staticmethod
    def _provider_url_for_item(code: str, item: dict) -> Optional[str]:
        """Compute a search result's ``provider_url`` via the provider's ``get_asset_url``.

        ``provider_params`` MUST be forwarded: some providers (e.g. Borsa Italiana funds)
        derive the correct page URL from params such as ``codice_fondo`` rather than from
        the identifier alone. Dropping the params yields a wrong/dead link for those assets.
        """
        provider_instance = AssetProviderRegistry.get_provider_instance(code)
        if not provider_instance:
            return None
        return provider_instance.get_asset_url(
            item.get("identifier", ""),
            item.get("identifier_type"),
            item.get("provider_params"),
        )

    @staticmethod
    async def search(query: str, provider_codes: Optional[list[str]] = None, hints: Optional[list[str]] = None, *, user_id: int | None = None) -> FAProviderSearchResponse:  # noqa: C901 — per-provider fan-out, error mapping + item packing
        """
        Search for assets across one or more providers in parallel.

        Args:
            query: Search query string
            provider_codes: Optional list of provider codes to query.
                           If None, queries all providers.
            hints: Optional extra search terms (report-extracted identifiers + names).
                   Used only by the link-finder fallback to build a specific query when
                   a provider's on-site search returns nothing.
            user_id: The user searching: the providers receive that user's settings too.

        Returns:
            FAProviderSearchResponse with aggregated results from all providers.

        Notes:
            - Providers that don't support search are silently skipped
            - Provider errors are logged but don't fail the entire search
            - Results are not deduplicated (same asset may appear from multiple providers)
        """
        # Get provider codes to query
        if not provider_codes:
            provider_codes = _default_search_codes()

        # Filter to valid providers that support search
        valid_providers: list[tuple[str, AssetSourceProvider]] = []
        for code in provider_codes:
            provider_instance = await core.configured_provider(code, user_id=user_id)
            if provider_instance:
                if provider_instance.supports_search:
                    valid_providers.append((code, provider_instance))
                else:
                    logger.debug(f"Provider '{code}' does not support search, skipping")
            else:
                logger.warning(f"Provider '{code}' not found, skipping")

        if not valid_providers:
            return FAProviderSearchResponse(
                query=query,
                total_results=0,
                results=[],
                providers_queried=[],
                providers_with_errors=[],
            )

        # F21: premium providers first, then lower priority. The sort is stable: ties, a repeated code included, keep the
        # order of today, so with every value at its default the order does not change (D-X3). The results keep the
        # providers' order (asyncio.gather).
        valid_providers.sort(key=lambda pair: provider_policy.search_rank(pair[0]))

        # Create search tasks for parallel execution
        async def search_single_provider(code: str, provider) -> tuple[str, list[dict], str | None, str | None]:
            """
            Search a single provider and return (code, results, error, error code).
            Error is None if successful, error message string if failed; the error code is NOT_CONFIGURED or None.
            Uses Layer 2 (query cache) and Layer 1 (item cache) for acceleration.
            """
            query_lower = query.lower().strip()
            # The settings the provider received change its answer: a cached answer serves the same settings only.
            query_cache_key = (code, query_lower, core.settings_cache_part(provider))

            # Layer 2: exact query cache (15min)
            cached_query, q_ok = core._search_query_cache.get(query_cache_key)
            if q_ok and cached_query is not None:
                logger.debug(f"Search query cache HIT for '{query}' on provider '{code}'")
                return (code, cached_query, None, None)

            # Layer 1: fuzzy match on cached individual items (24h)
            # Scan core._search_result_cache keys for contains match
            # (theine doesn't expose keys() — we skip Layer 1 fuzzy for now
            #  and rely on Layer 2 for repeated queries)

            try:
                search_results = await core.call_provider(provider, lambda: provider.search(query), timeout=30.0)
                # Last-resort: no on-site hits → try the external link-finder + resolve_url.
                if not search_results:
                    search_results = await AssetSearchService._augment_with_link_finder(code, provider, query, hints)
                # Populate Layer 2
                core._search_query_cache.set(query_cache_key, search_results)
                return (code, search_results, None, None)
            except Exception as e:
                error_str = str(e).lower()
                # The typed refusals first: their messages carry plugin-declared names, which a text test could match.
                if isinstance(e, AssetSourceError) and e.error_code == "NOT_CONFIGURED":
                    logger.info("Search skipped: provider not configured", provider=code, missing=e.details.get("missing"))
                    return (code, [], str(e), "NOT_CONFIGURED")
                elif isinstance(e, AssetRateLimitedError):
                    logger.info("Search skipped: provider paused after too many requests", provider=code, retry_after=e.retry_after)
                    return (code, [], str(e), None)
                elif "not_supported" in error_str or "not supported" in error_str:
                    logger.debug(f"Provider '{code}' does not support search")
                    return (code, [], None, None)
                else:
                    logger.exception(f"Search error from provider '{code}': {e}")
                    return (code, [], str(e), None)

        # Execute all searches in parallel
        tasks = [search_single_provider(code, provider) for code, provider in valid_providers]

        search_results_raw = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        results: list[FAProviderSearchResultItem] = []
        providers_queried: list[str] = []
        providers_with_errors: list[str] = []
        providers_not_configured: list[str] = []

        for result in search_results_raw:
            if isinstance(result, Exception):
                # Unexpected exception from gather itself
                logger.error(f"Unexpected error in search task: {result}")
                continue

            code, items, error, error_code = result
            providers_queried.append(code)

            if error:
                providers_with_errors.append(code)
                if error_code == "NOT_CONFIGURED":
                    providers_not_configured.append(code)
                continue

            # Convert provider results to response schema
            for item in items:
                # Compute provider_url (forwards provider_params for fund-style URLs)
                item_provider_url = AssetSearchService._provider_url_for_item(code, item)

                # Validate asset_type: fallback to OTHER if unknown
                raw_asset_type = item.get("type")
                if raw_asset_type and raw_asset_type not in AssetType.__members__:
                    logger.warning(f"Unknown asset_type '{raw_asset_type}' from provider '{code}', " f"falling back to OTHER")
                    raw_asset_type = "OTHER"

                results.append(
                    FAProviderSearchResultItem(
                        identifier=item.get("identifier", ""),
                        identifier_type=item.get("identifier_type"),
                        display_name=item.get("display_name", item.get("name", "")),
                        provider_code=code,
                        currency=item.get("currency"),
                        asset_type=raw_asset_type,
                        provider_url=item_provider_url,
                        provider_params=item.get("provider_params"),
                        quote_base_suggestion=_quote_base_suggestion(code, item),
                        via_web=bool(item.get("_via_web", False)),
                    )
                )

        return FAProviderSearchResponse(
            query=query,
            total_results=len(results),
            results=results,
            providers_queried=providers_queried,
            providers_with_errors=providers_with_errors,
            providers_not_configured=providers_not_configured,
        )

    @staticmethod
    async def search_stream(query: str, provider_codes: Optional[list[str]] = None, hints: Optional[list[str]] = None, *, user_id: int | None = None) -> AsyncGenerator[str]:  # pragma: no cover  # noqa: C901 — SSE fan-out, per-provider error mapping
        """
        Stream search results as SSE events, one event per provider completion.

        Each provider runs concurrently; as each completes, its results are
        yielded immediately as an SSE event.

        SSE events:
        - provider_results: {provider_code, results: [...]}
        - provider_error: {provider_code, error, error_code?, retry_after?} — ``error_code`` for an ``AssetSourceError``:
          ``NOT_CONFIGURED`` (a required setting has no value; the plugin's settings are in
          ``GET /api/v1/settings/plugins``), ``RATE_LIMITED`` with ``retry_after`` (the seconds of pause), or the
          provider's own code
        - done: {total_results, providers_queried, providers_with_errors}

        Args:
            query: Search query string
            provider_codes: Optional list of provider codes to query.
            user_id: The user searching: the providers receive that user's settings too.

        Yields:
            SSE-formatted strings: "data: {...}\\n\\n"
        """
        # Resolve providers
        if not provider_codes:
            provider_codes = _default_search_codes()

        valid_providers: list[tuple[str, AssetSourceProvider]] = []
        for code in provider_codes:
            instance = await core.configured_provider(code, user_id=user_id)
            if instance and instance.supports_search:
                valid_providers.append((code, instance))

        if not valid_providers:
            yield f'data: {json.dumps({"event": "done", "total_results": 0, "providers_queried": [], "providers_with_errors": []})}\n\n'
            return

        queue: asyncio.Queue = asyncio.Queue()
        total_results = 0
        providers_queried: list[str] = []
        providers_with_errors: list[str] = []

        async def _search_one(code: str, provider: AssetSourceProvider):
            """Run one provider search and put results on the queue."""
            query_lower = query.lower().strip()
            # The settings the provider received change its answer: a cached answer serves the same settings only.
            query_cache_key = (code, query_lower, core.settings_cache_part(provider))

            # Layer 2: exact query cache (15min)
            cached_query, q_ok = core._search_query_cache.get(query_cache_key)
            if q_ok and cached_query is not None:
                logger.debug(f"Search stream query cache HIT for '{query}' on provider '{code}'")
                await queue.put((code, cached_query, None, {}))
                return

            try:
                items = await core.call_provider(provider, lambda: provider.search(query), timeout=20.0)
                # Last-resort: no on-site hits → try the external link-finder + resolve_url.
                if not items:
                    items = await AssetSearchService._augment_with_link_finder(code, provider, query, hints)
                # Populate Layer 2
                core._search_query_cache.set(query_cache_key, items)
                await queue.put((code, items, None, {}))
            except AssetRateLimitedError as e:
                logger.info("Search stream: provider paused after too many requests", provider=code, retry_after=e.retry_after)
                await queue.put((code, [], str(e), {"error_code": e.error_code, "retry_after": e.retry_after}))
            except AssetSourceError as e:
                if e.error_code == "NOT_CONFIGURED":
                    logger.info("Search stream: provider not configured", provider=code, missing=e.details.get("missing"))
                else:
                    logger.warning(f"Search stream: provider '{code}' error: {e}")
                await queue.put((code, [], str(e), {"error_code": e.error_code}))
            except Exception as e:
                logger.warning(f"Search stream: provider '{code}' error: {e}")
                await queue.put((code, [], str(e), {}))

        # Launch all providers concurrently
        tasks = [asyncio.create_task(_search_one(code, prov)) for code, prov in valid_providers]

        # Yield results as they complete
        completed = 0
        while completed < len(tasks):
            code, items, error, error_fields = await queue.get()
            completed += 1
            providers_queried.append(code)

            if error:
                providers_with_errors.append(code)
                yield f'data: {json.dumps({"event": "provider_error", "provider_code": code, "error": error, **error_fields})}\n\n'
                continue

            # Convert items to serializable dicts
            result_items = []
            for item in items:
                # Compute provider_url (forwards provider_params for fund-style URLs)
                item_provider_url = AssetSearchService._provider_url_for_item(code, item)

                # Validate asset_type
                raw_asset_type = item.get("type")
                if raw_asset_type and raw_asset_type not in AssetType.__members__:
                    raw_asset_type = "OTHER"

                # Extract enum .value to avoid "IdentifierType.TICKER" serialization
                raw_id_type = item.get("identifier_type", "")
                id_type_str = raw_id_type.value if hasattr(raw_id_type, "value") else str(raw_id_type)
                suggestion = _quote_base_suggestion(code, item)

                result_items.append(
                    {
                        "identifier": item.get("identifier", ""),
                        "identifier_type": id_type_str,
                        "display_name": item.get("display_name", item.get("name", "")),
                        "provider_code": code,
                        "currency": item.get("currency"),
                        "asset_type": raw_asset_type,
                        "provider_url": item_provider_url,
                        "provider_params": item.get("provider_params"),
                        "quote_base_suggestion": suggestion.model_dump(mode="json") if suggestion else None,
                        "via_web": bool(item.get("_via_web", False)),
                    }
                )

            total_results += len(result_items)

            yield f'data: {json.dumps({"event": "provider_results", "provider_code": code, "results": result_items})}\n\n'

        # Final event
        yield f'data: {json.dumps({"event": "done", "total_results": total_results, "providers_queried": providers_queried, "providers_with_errors": providers_with_errors})}\n\n'

        # Ensure all tasks are awaited
        await asyncio.gather(*tasks, return_exceptions=True)
