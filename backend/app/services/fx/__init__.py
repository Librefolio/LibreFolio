"""FX domain services. The package re-exports nothing: import every name from the module that defines it.

- ``base.py``: the ``FXRateProvider`` contract of the rate providers, the history start-date types, the FX errors.
- ``registry.py``: ``FXProviderRegistry``, which discovers the rate providers in ``services/fx_providers/``.
- ``sync.py``: the rate sync from the providers along the user's conversion routes (``sync_pairs_bulk``).
- ``conversion.py``: chained route rates and the bulk conversion of amounts (``convert_bulk``).
- ``storage.py``: the alphabetical normalization of a pair and the bulk upsert and delete of stored rates.
- ``catalog.py``: the supported-currency list of each provider, cached for ``GET /fx/providers``.
"""
