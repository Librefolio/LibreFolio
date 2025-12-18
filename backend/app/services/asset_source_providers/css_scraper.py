"""
CSS Web Scraper provider for asset pricing.

Uses HTTP + BeautifulSoup to extract prices from web pages using CSS selectors.
Supports both US (1,234.56) and EU (1.234,56) number formats.
"""
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Dict

from backend.app.db import IdentifierType
from backend.app.logging_config import get_logger

try:
    import httpx
    from bs4 import BeautifulSoup

    SCRAPER_AVAILABLE = True
except ImportError:
    httpx = None
    BeautifulSoup = None
    SCRAPER_AVAILABLE = False

from backend.app.services.provider_registry import register_provider, AssetProviderRegistry
from backend.app.services.asset_source import AssetSourceProvider, AssetSourceError
from backend.app.schemas.assets import FACurrentValue, FAHistoricalData

logger = get_logger(__name__)


@register_provider(AssetProviderRegistry)
class CSSScraperProvider(AssetSourceProvider):
    """Web scraping provider with CSS selectors."""

    @property
    def provider_code(self) -> str:
        return "cssscraper"

    @property
    def provider_name(self) -> str:
        return "CSS Web Scraper"

    @property
    def test_cases(self) -> list[dict]:
        """
        Test cases with identifier and provider_params.

        Returns two test cases for Borsa Italiana BTP:
        - English version (US decimal format: 100.39)
        - Italian version (EU decimal format: 100,39)
        """
        return [
            {
                'identifier': 'https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0005634800.html?lang=en',
                'provider_params': {
                    'current_css_selector': '.summary-value strong',
                    'currency': 'EUR',
                    'decimal_format': 'us'  # English version uses US format
                    }
                },
            {
                'identifier': 'https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0005634800.html?lang=it',
                'provider_params': {
                    'current_css_selector': '.summary-value strong',
                    'currency': 'EUR',
                    'decimal_format': 'eu'  # Italian version uses EU format
                    }
                }
            ]

    async def get_current_value(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None = None,
        ) -> FACurrentValue:
        """
        Fetch current price by scraping URL with CSS selector.

        Args:
            identifier: URL to scrape (e.g., "https://example.com/price")
            identifier_type: Type of identifier (should be URL)
            provider_params: see self.validate_params()

        Returns:
            FACurrentValue with value, currency, as_of_date, source

        Raises:
            AssetSourceError: If scraping fails or price not found
        """
        if not SCRAPER_AVAILABLE:
            raise AssetSourceError(
                "httpx and beautifulsoup4 not available - install with: pipenv install httpx beautifulsoup4",
                "NOT_AVAILABLE",
                {"identifier": identifier}
                )

        self.validate_params(provider_params)

        url = identifier
        css_selector = provider_params['current_css_selector']
        currency = provider_params['currency']
        decimal_format = provider_params.get('decimal_format', 'us')
        timeout = provider_params.get('timeout', 30)
        user_agent = provider_params.get('user_agent', 'LibreFolio/1.0')

        try:
            # Fetch page
            # TODO: far passare heder e altri parametri di httpx via provider_params e usare quelli sotto come fallback
            headers = {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                }

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, headers=headers, follow_redirects=True)
                response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find price element
            price_element = soup.select_one(css_selector)
            if not price_element:
                raise AssetSourceError(
                    f"Price element not found with selector: {css_selector}",
                    "NOT_FOUND",
                    {
                        "url": url,
                        "selector": css_selector,
                        "status_code": response.status_code
                        }
                    )

            # Extract and parse price
            price_text = price_element.get_text(strip=True)
            logger.debug(f"Extracted price text: '{price_text}' from {url}")

            price_value = self.parse_price(price_text, decimal_format)

            return FACurrentValue(
                value=price_value,
                currency=currency,
                as_of_date=date.today(),
                source=self.provider_name
                )

        except AssetSourceError:
            raise
        except httpx.HTTPStatusError as e:
            raise AssetSourceError(
                f"HTTP error {e.response.status_code}: {e.response.reason_phrase}",
                "HTTP_ERROR",
                {
                    "url": url,
                    "status_code": e.response.status_code,
                    "reason": e.response.reason_phrase
                    }
                )
        except httpx.RequestError as e:
            raise AssetSourceError(
                f"Request failed: {e}",
                "REQUEST_ERROR",
                {"url": url, "error": str(e)}
                )
        except Exception as e:
            raise AssetSourceError(
                f"Scraping failed: {e}",
                "SCRAPE_ERROR",
                {"url": url, "error": str(e)}
                )

    @property
    def supports_history(self) -> bool:
        """Whether this provider supports historical data."""
        return False

    async def get_history_value(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None,
        start_date: date,
        end_date: date,
        ) -> FAHistoricalData:
        """
        Fetch historical prices (NOT IMPLEMENTED for CSS scraper).

        Historical data scraping is complex and site-specific.
        For now, this provider only supports current values.

        Args:
            identifier: URL to scrape
            start_date: Start date
            end_date: End date
            provider_params: Provider parameters
        Returns:
            FAHistoricalData with prices list, currency, source
        Raises:
            AssetSourceError: Always (not implemented)
        """
        raise AssetSourceError(
            "Historical data not supported by CSS scraper provider",
            "NOT_IMPLEMENTED",
            {
                "identifier": identifier,
                "start_date": str(start_date),
                "end_date": str(end_date)
                }
            )

    @property
    def test_search_query(self) -> str | None:
        """Search query to use in tests (not supported for CSS scraper)."""
        return None

    def validate_params(self, params: Dict | None) -> None:
        """
        Validate required parameters.

        Required params:
        - current_css_selector: CSS selector for current price
        - currency: Currency code (e.g., "EUR", "USD")

        Optional params:
        - decimal_format: "us" (default) or "eu" for number parsing
          - US format: 1,234.56 (comma = thousands, dot = decimal)
          - EU format: 1.234,56 (dot = thousands, comma = decimal)
        - history_css_selector: CSS selector for historical prices (not implemented yet)
        - timeout: Request timeout in seconds (default: 30)
        - user_agent: Custom User-Agent header
        """
        if not params:
            raise AssetSourceError(
                "CSS scraper requires provider_params",
                "MISSING_PARAMS",
                {"params": params}
                )

        # Check required params
        required = ['current_css_selector', 'currency']
        missing = [k for k in required if k not in params]
        if missing:
            raise AssetSourceError(
                f"Missing required params: {', '.join(missing)}",
                "MISSING_PARAMS",
                {"missing": missing, "params": params}
                )

        # Validate decimal_format if present
        if 'decimal_format' in params:
            if params['decimal_format'] not in ['us', 'eu']:
                raise AssetSourceError(
                    "decimal_format must be 'us' or 'eu'",
                    "INVALID_PARAMS",
                    {"decimal_format": params['decimal_format']}
                    )

    # ============================================================================
    # HELPER FUNCTIONS
    # ============================================================================

    def parse_price(self, text: str, decimal_format: str = 'us') -> Decimal:
        """
        Parse price from text with robust number format detection.

        Supports:
        - US format: 1,234.56 (comma = thousands, dot = decimal)
        - EU format: 1.234,56 (dot = thousands, comma = decimal)
        - Currency symbols: €$£¥
        - Whitespace
        - Percentage signs (removed)

        Args:
            text: Raw text from web page
            decimal_format: 'us' or 'eu' (default: 'us')

        Returns:
            Decimal value

        Raises:
            AssetSourceError: If parsing fails
        """
        # Remove whitespace and currency symbols
        text = text.strip()
        text = re.sub(r'[€$£¥\s%]', '', text)

        if not text:
            raise AssetSourceError(
                "Empty price text",
                "PARSE_ERROR",
                {"text": text}
                )

        try:
            text = text.replace(' ', '')  # remove spaces if any (like French format: "1 234,56")
            if decimal_format == 'us':
                # US format: 1,234.56
                # Remove commas (thousands separator)
                text = text.replace(',', '')
                return Decimal(text)
            else:
                # EU format: 1.234,56
                # Remove dots (thousands separator), replace comma with dot (decimal)
                text = text.replace('.', '').replace(',', '.')
                return Decimal(text)

        except (InvalidOperation, ValueError) as e:
            # Case like "1,234.56" is too unambiguity and cannot be parsed reliably
            raise AssetSourceError(
                f"Failed to parse price: {text}",
                "PARSE_ERROR",
                {"text": text, "decimal_format": decimal_format, "error": str(e)}
                )
