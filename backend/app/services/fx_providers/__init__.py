"""
FX Providers package.

This package contains concrete implementations of FX rate providers.
Each provider represents a central bank or financial data source.

Available providers:
- ECBProvider: European Central Bank
"""

from backend.app.services.fx_providers.ecb import ECBProvider

__all__ = ['ECBProvider']

