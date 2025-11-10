"""
FX Providers package.

This package contains concrete implementations of FX rate providers.
Each provider represents a central bank or financial data source.

Providers are auto-discovered and registered via the FXProviderRegistry.
No manual imports needed - use FXProviderRegistry.get_provider(code) to access them.

Available providers:
- ECBProvider: European Central Bank (EUR base) - code: "ECB"
- FEDProvider: Federal Reserve (USD base) - code: "FED"
- BOEProvider: Bank of England (GBP base) - code: "BOE"
- SNBProvider: Swiss National Bank (CHF base) - code: "SNB"
"""

# No imports needed - providers are auto-discovered by FXProviderRegistry

