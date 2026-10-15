"""Asset schemas (FA), one module per theme (C3). The package re-exports nothing: import each class from the module
that defines it. The hub ``backend/app/schemas/__init__.py`` keeps exporting the public names.

- ``assets.py``: asset CRUD, patch, merge, classification and distributions, scheduled investment parameters.
- ``events.py``: the asset event point and the event CRUD of ``/assets/events``.
"""
