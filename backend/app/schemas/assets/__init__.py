"""Asset schemas (FA), one module per theme (C3). The package re-exports nothing: import each class from the module
that defines it. The hub ``backend/app/schemas/__init__.py`` keeps exporting the public names.

- ``assets.py``: the asset and its CRUD: provider assignment, create, read, delete, patch, merge.
- ``metadata.py``: classification and metadata: the geographic and sector distributions, the classification
  parameters, the metadata response and the metadata refresh results.
- ``scheduled_investment.py``: the financial enums and the interest schedule of scheduled investments.
- ``events.py``: the asset event point and the event CRUD of ``/assets/events``.
"""
