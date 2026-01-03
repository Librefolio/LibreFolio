"""
Broker Report Import Manager (BRIM) Providers.

This package contains plugins for importing transactions from broker report files.

Plugins are auto-discovered by BRIMProviderRegistry when first accessed.
Each plugin must:
1. Extend BRIMProvider from brim_provider.py
2. Use @register_provider(BRIMProviderRegistry) decorator
3. Implement all abstract methods

Available plugins:
- broker_generic_csv: Generic CSV import with auto-column detection
"""

