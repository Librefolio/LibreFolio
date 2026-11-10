"""
Transactions: the service that validates and writes transactions, and its batch pipeline.

- ``transaction_service``: ``TransactionService``, composed of one mixin per theme — ``access`` (broker access
  checks), ``validation`` (event links, cost basis requirement, linked-pair rules), ``queries``, ``balances``,
  ``event_suggestions``, ``promotion`` (promoting loose rows into pairs, the split and promote type maps) and
  ``auto_cost`` (the Auto cost basis) — with ``delete_by_broker`` and ``execute_batch``;
- the ordered stages of a batch: ``transaction_batch_stages`` (parse, access, balances, response), ``batch_edits``
  (deletes, splits, updates), ``batch_creates`` (creates, promotes, links) and ``batch_costs`` (WAC, FX, cost basis);
- ``transaction_batch_context``: the state a batch carries through its stages, and ``BalanceValidationError``.

The package re-exports nothing: import a name from the module that defines it.
"""
