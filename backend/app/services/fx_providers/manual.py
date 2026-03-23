"""
Manual FX rate provider — sentinel for manually-managed currency pairs.

This provider does NOT fetch any rates from external sources.
It serves as a placeholder in pair-sources to make the pair visible
in the system when no automatic provider is configured.

During sync, this provider is silently skipped (returns empty results).
The backend automatically manages this provider:
- Inserted with priority=999 when a pair has no real providers
- Removed when a real provider is added to the pair
- Re-inserted when the last real provider is removed from the pair
"""

from datetime import date
from decimal import Decimal

from backend.app.logging_config import get_logger
from backend.app.services.fx import FXRateProvider
from backend.app.services.provider_registry import register_provider, FXProviderRegistry

logger = get_logger(__name__)

# Sentinel priority value for MANUAL provider
MANUAL_PRIORITY = 999


@register_provider(FXProviderRegistry)
class ManualProvider(FXRateProvider):
    """
    Sentinel FX provider for manually-managed currency pairs.

    This provider accepts any currency pair but never fetches rates.
    It exists solely to mark a pair as "configured" in the pair-sources table,
    enabling it to appear in the FX list and be managed by the user.

    The backend auto-manages this provider:
    - Auto-inserted when no real providers are configured for a pair
    - Auto-removed when a real provider is added
    - Auto-re-inserted when the last real provider is removed
    """

    @property
    def code(self) -> str:
        return "MANUAL"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "Manual Entry"

    @property
    def icon(self) -> str | None:
        return None

    @property
    def base_currency(self) -> str:
        """Wildcard — accepts any base currency."""
        return "*"

    @property
    def base_currencies(self) -> list[str]:
        """Override to accept any base currency."""
        return ["*"]

    @property
    def description(self) -> str:
        return "Manually managed exchange rates (no automatic sync)"

    @property
    def test_currencies(self) -> list[str]:
        """No test currencies — this provider doesn't fetch anything."""
        return []

    async def get_supported_currencies(self) -> list[str]:
        """
        Returns empty list — MANUAL provider accepts any pair
        but doesn't provide currency discovery.
        """
        return []

    async def fetch_rates(
        self,
        date_range: tuple[date, date],
        currencies: list[str],
        base_currency: str | None = None,
    ) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        No-op: manual pairs don't auto-sync.

        Returns empty dict — the user must insert rates manually
        via the rate upsert endpoint or CSV import.
        """
        logger.info(
            f"MANUAL provider: skipping sync for currencies={currencies}, "
            f"date_range={date_range} (manual-only pair)"
        )
        return {}

