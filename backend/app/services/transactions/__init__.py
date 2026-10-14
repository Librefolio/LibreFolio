"""
Transactions: the service that validates and writes transactions, and its batch pipeline.

- ``transaction_service``: ``TransactionService`` — broker access checks, linked pairs, queries, balances, event
  suggestions, transfer promotion and ``execute_batch``;
- ``transaction_batch_stages``: the ordered stages of a batch (parse, access, mutations, links, WAC, cost basis,
  balances, response);
- ``transaction_batch_context``: the state a batch carries through its stages, and ``BalanceValidationError``.

The package re-exports nothing: import a name from the module that defines it.
"""
