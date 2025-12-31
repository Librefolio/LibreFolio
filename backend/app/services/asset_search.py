"""
Asset Search Service.

Provides unified search across multiple asset providers with parallel execution.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from backend.app.logging_config import get_logger
from backend.app.schemas.provider import FAProviderSearchResponse, FAProviderSearchResultItem
from backend.app.services.provider_registry import AssetProviderRegistry

logger = get_logger(__name__)

# TODO: spostare questa classe dentro asset_source e cancellare questo sorgente
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
    async def search(
        query: str,
        provider_codes: Optional[list[str]] = None
        ) -> FAProviderSearchResponse:
        """
        Search for assets across one or more providers in parallel.

        Args:
            query: Search query string
            provider_codes: Optional list of provider codes to query.
                           If None, queries all providers.

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
            provider_codes = [p['code'] for p in all_providers]

        # Filter to valid providers only
        valid_providers: list[tuple[str, object]] = []
        for code in provider_codes:
            provider_instance = AssetProviderRegistry.get_provider_instance(code)
            if provider_instance:
                valid_providers.append((code, provider_instance))
            else:
                logger.warning(f"Provider '{code}' not found, skipping")

        if not valid_providers:
            return FAProviderSearchResponse(
                query=query,
                total_results=0,
                results=[],
                providers_queried=[],
                providers_with_errors=[]
                )

        # Create search tasks for parallel execution
        async def search_single_provider(code: str, provider) -> tuple[str, list[dict], str | None]:
            """
            Search a single provider and return (code, results, error).
            Error is None if successful, error message string if failed.
            """
            try:
                search_results = await provider.search(query)
                return (code, search_results, None)
            except Exception as e:
                error_str = str(e).lower()
                if "not_supported" in error_str or "not supported" in error_str:
                    # Not an error, just unsupported
                    logger.debug(f"Provider '{code}' does not support search")
                    return (code, [], None)
                else:
                    logger.error(f"Search error from provider '{code}': {e}")
                    return (code, [], str(e))

        # Execute all searches in parallel
        tasks = [
            search_single_provider(code, provider)
            for code, provider in valid_providers
            ]

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
                results.append(FAProviderSearchResultItem(
                    identifier=item.get("identifier", ""),
                    identifier_type=item.get("identifier_type"),
                    display_name=item.get("display_name", item.get("name", "")),
                    provider_code=code,
                    currency=item.get("currency"),
                    asset_type=item.get("type")
                    ))

        return FAProviderSearchResponse(
            query=query,
            total_results=len(results),
            results=results,
            providers_queried=providers_queried,
            providers_with_errors=providers_with_errors
            )
