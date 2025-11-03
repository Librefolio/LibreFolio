"""
FX Providers package.

This package contains concrete implementations of FX rate providers.
Each provider represents a central bank or financial data source.

Available providers:
- ECBProvider: European Central Bank (EUR base)
- FEDProvider: Federal Reserve (USD base)
- BOEProvider: Bank of England (GBP base)
- SNBProvider: Swiss National Bank (CHF base)
"""

from backend.app.services.fx_providers.ecb import ECBProvider
from backend.app.services.fx_providers.fed import FEDProvider
from backend.app.services.fx_providers.boe import BOEProvider
from backend.app.services.fx_providers.snb import SNBProvider

__all__ = ['ECBProvider', 'FEDProvider', 'BOEProvider', 'SNBProvider']

