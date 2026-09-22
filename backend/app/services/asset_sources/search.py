"""Cross-provider asset search orchestration."""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator, Optional

import structlog

from backend.app.db.models import (
    AssetType,
)
from backend.app.schemas.provider import (
    FAProviderSearchResponse,
    FAProviderSearchResultItem,
)
from backend.app.services import web_link_finder
from backend.app.services.asset_sources import core
from backend.app.services.asset_sources.core import AssetSourceProvider
from backend.app.services.provider_registry import AssetProviderRegistry

logger = structlog.get_logger(__name__)


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
                        return await core._run_provider_in_thread(lambda: provider.resolve_url(u), timeout=20.0)
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
    async def search(query: str, provider_codes: Optional[list[str]] = None, hints: Optional[list[str]] = None) -> FAProviderSearchResponse:  # noqa: C901 — per-provider fan-out, error mapping + item packing
        """
        Search for assets across one or more providers in parallel.

        Args:
            query: Search query string
            provider_codes: Optional list of provider codes to query.
                           If None, queries all providers.
            hints: Optional extra search terms (report-extracted identifiers + names).
                   Used only by the link-finder fallback to build a specific query when
                   a provider's on-site search returns nothing.

        Returns:
            FAProviderSearchResponse with aggregated results from all providers.

        Notes:
            - Providers that don't support search are silently skipped
            - Provider errors are logged but don't fail the entire search
            - Results are not deduplicated (same asset may appear from multiple providers)
        """
        # Get provider codes to query
        if not provider_codes:
            all_providers = AssetProviderRegistry.list_providers()
            provider_codes = [p["code"] for p in all_providers]

        # Filter to valid providers that support search
        valid_providers: list[tuple[str, AssetSourceProvider]] = []
        for code in provider_codes:
            provider_instance = AssetProviderRegistry.get_provider_instance(code)
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

        # Create search tasks for parallel execution
        async def search_single_provider(code: str, provider) -> tuple[str, list[dict], str | None]:
            """
            Search a single provider and return (code, results, error).
            Error is None if successful, error message string if failed.
            Uses Layer 2 (query cache) and Layer 1 (item cache) for acceleration.
            """
            query_lower = query.lower().strip()
            query_cache_key = (code, query_lower)

            # Layer 2: exact query cache (15min)
            cached_query, q_ok = core._search_query_cache.get(query_cache_key)
            if q_ok and cached_query is not None:
                logger.debug(f"Search query cache HIT for '{query}' on provider '{code}'")
                return (code, cached_query, None)

            # Layer 1: fuzzy match on cached individual items (24h)
            # Scan core._search_result_cache keys for contains match
            # (theine doesn't expose keys() — we skip Layer 1 fuzzy for now
            #  and rely on Layer 2 for repeated queries)

            try:
                search_results = await core._run_provider_in_thread(
                    lambda: provider.search(query),
                    timeout=30.0,
                )
                # Last-resort: no on-site hits → try the external link-finder + resolve_url.
                if not search_results:
                    search_results = await AssetSearchService._augment_with_link_finder(code, provider, query, hints)
                # Populate Layer 2
                core._search_query_cache.set(query_cache_key, search_results)
                return (code, search_results, None)
            except Exception as e:
                error_str = str(e).lower()
                if "not_supported" in error_str or "not supported" in error_str:
                    logger.debug(f"Provider '{code}' does not support search")
                    return (code, [], None)
                else:
                    logger.exception(f"Search error from provider '{code}': {e}")
                    return (code, [], str(e))

        # Execute all searches in parallel
        tasks = [search_single_provider(code, provider) for code, provider in valid_providers]

        search_results_raw = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        results: list[FAProviderSearchResultItem] = []
        providers_queried: list[str] = []
        providers_with_errors: list[str] = []

        for result in search_results_raw:
            if isinstance(result, Exception):
                # Unexpected exception from gather itself
                logger.error(f"Unexpected error in search task: {result}")
                continue

            code, items, error = result
            providers_queried.append(code)

            if error:
                providers_with_errors.append(code)
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
                        via_web=bool(item.get("_via_web", False)),
                    )
                )

        return FAProviderSearchResponse(
            query=query,
            total_results=len(results),
            results=results,
            providers_queried=providers_queried,
            providers_with_errors=providers_with_errors,
        )

    @staticmethod
    async def search_stream(query: str, provider_codes: Optional[list[str]] = None, hints: Optional[list[str]] = None) -> AsyncGenerator[str]:  # pragma: no cover  # noqa: C901 — SSE fan-out, per-provider error mapping
        """
        Stream search results as SSE events, one event per provider completion.

        Each provider runs concurrently; as each completes, its results are
        yielded immediately as an SSE event.

        SSE events:
        - provider_results: {provider_code, results: [...]}
        - done: {total_results, providers_queried, providers_with_errors}

        Args:
            query: Search query string
            provider_codes: Optional list of provider codes to query.

        Yields:
            SSE-formatted strings: "data: {...}\\n\\n"
        """
        # Resolve providers
        if not provider_codes:
            all_providers = AssetProviderRegistry.list_providers()
            provider_codes = [p["code"] for p in all_providers]

        valid_providers: list[tuple[str, AssetSourceProvider]] = []
        for code in provider_codes:
            instance = AssetProviderRegistry.get_provider_instance(code)
            if instance and instance.supports_search:
                valid_providers.append((code, instance))

        if not valid_providers:
            yield f'data: {json.dumps({"event": "done", "total_results": 0, "providers_queried": [], "providers_with_errors": []})}\n\n'
            return

        queue: asyncio.Queue = asyncio.Queue()
        total_results = 0
        providers_queried: list[str] = []
        providers_with_errors: list[str] = []

        async def _search_one(code: str, provider: object):
            """Run one provider search and put results on the queue."""
            query_lower = query.lower().strip()
            query_cache_key = (code, query_lower)

            # Layer 2: exact query cache (15min)
            cached_query, q_ok = core._search_query_cache.get(query_cache_key)
            if q_ok and cached_query is not None:
                logger.debug(f"Search stream query cache HIT for '{query}' on provider '{code}'")
                await queue.put((code, cached_query, None))
                return

            try:
                items = await core._run_provider_in_thread(
                    lambda: provider.search(query),
                    timeout=20.0,
                )
                # Last-resort: no on-site hits → try the external link-finder + resolve_url.
                if not items:
                    items = await AssetSearchService._augment_with_link_finder(code, provider, query, hints)
                # Populate Layer 2
                core._search_query_cache.set(query_cache_key, items)
                await queue.put((code, items, None))
            except Exception as e:
                logger.warning(f"Search stream: provider '{code}' error: {e}")
                await queue.put((code, [], str(e)))

        # Launch all providers concurrently
        tasks = [asyncio.create_task(_search_one(code, prov)) for code, prov in valid_providers]

        # Yield results as they complete
        completed = 0
        while completed < len(tasks):
            code, items, error = await queue.get()
            completed += 1
            providers_queried.append(code)

            if error:
                providers_with_errors.append(code)
                yield f'data: {json.dumps({"event": "provider_error", "provider_code": code, "error": error})}\n\n'
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
                        "via_web": bool(item.get("_via_web", False)),
                    }
                )

            total_results += len(result_items)

            yield f'data: {json.dumps({"event": "provider_results", "provider_code": code, "results": result_items})}\n\n'

        # Final event
        yield f'data: {json.dumps({"event": "done", "total_results": total_results, "providers_queried": providers_queried, "providers_with_errors": providers_with_errors})}\n\n'

        # Ensure all tasks are awaited
        await asyncio.gather(*tasks, return_exceptions=True)
