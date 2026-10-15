"""Transaction schemas (TX), one module per theme (C3). The package re-exports nothing: import each class from the
module that defines it. The hub ``backend/app/schemas/__init__.py`` keeps exporting the public names.

- ``transactions.py``: shared validators and the transaction DTOs: create, read, update (with the type swap groups),
  query, delete.
- ``batch.py``: the unified batch of ``/validate`` and ``/commit``: item operations and statuses, the request body,
  results and response, the validation codes and issue, the split and promote items.
- ``event_suggest.py``: the linkable asset events of ``POST /transactions/events/suggest``.
- ``promotion.py``: transfer promotion and promote suggestions.
- ``type_metadata.py``: the metadata of each transaction type and event type, and the ``GET /transactions/types``
  response.
"""
