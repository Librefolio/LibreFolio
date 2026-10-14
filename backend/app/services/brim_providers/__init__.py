"""
Broker Report Import Manager (BRIM) Providers.

This package contains plugins for importing transactions from broker report files.

Plugins are auto-discovered by BRIMProviderRegistry when first accessed.
Each plugin is a folder ``<code>/``: ``plugin.py`` holds the code, which the registry loads, and
``__init__.py`` only its docstring. Helpers shared by several plugins stay here as ``_*.py``.
The plugin class must:
1. Extend BRIMProvider from brim_provider.py
2. Use @register_provider(BRIMProviderRegistry) decorator
3. Implement all abstract methods

Available plugins:
- broker_generic_csv: Generic CSV import with auto-column detection
"""
