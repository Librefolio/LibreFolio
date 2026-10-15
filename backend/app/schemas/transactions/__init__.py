"""Transaction schemas (TX), one module per theme (C3). The package re-exports nothing: import each class from the
module that defines it. The hub ``backend/app/schemas/__init__.py`` keeps exporting the public names.

- ``transactions.py``: the transaction schemas: shared validators, create, read, update, query, delete, the unified
  batch, validation codes and issues, event suggestions, transfer promotion, split and promote items, promote
  suggestions, and the transaction type metadata.
"""
