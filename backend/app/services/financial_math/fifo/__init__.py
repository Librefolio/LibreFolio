"""FIFO lots: custody fragments, closures, transfers, and the allocation of income and costs to lots.

Modules:

* ``models`` — input transactions, events, lots, fragments, closures, economic allocations, and the
  engine result.
* ``eligibility`` — the quantity a lot held on the record date of an income event.
* ``engine`` — the replay of an asset's transactions into lots (``run_fifo_lot_engine``).

This package re-exports nothing: import a name from the module that defines it.
"""
