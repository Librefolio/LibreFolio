"""Asset domain services.

The package re-exports nothing: import every name from the module that defines it.

- ``base.py`` holds ``AssetSourceProvider``, the base class of the pricing plugins in
  ``services/asset_source_providers/``, with ``AssetSourceError``; ``core.py`` holds the provider
  caches and ``_run_provider_in_thread``.
- ``registry.py`` holds ``AssetProviderRegistry``, which discovers those plugins.
- ``manager.py`` composes ``AssetSourceManager`` from ``provider_management.py``, ``metadata.py``,
  ``price_store.py``, ``price_query.py`` and ``refresh.py``.
- ``crud.py`` holds ``AssetCRUDService``; ``search.py`` holds ``AssetSearchService``, with
  ``web_link_finder.py`` as its last-resort web lookup.
- ``market_calendar.py`` holds the market holidays and the carry-versus-quote rule.
"""
