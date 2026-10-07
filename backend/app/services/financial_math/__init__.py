"""Financial math layer: LibreFolio's financial calculations.

A calculation here owns its whole problem. It takes the plain data of the problem
(movements, currencies, dates) and calls the services it needs to complete it — the FX
service for conversions, for example — instead of receiving values prepared by its
caller. Engines, services and API handlers call this layer; it does not depend on them.

New financial calculations are born here. The existing pure helpers in
``backend/app/utils/financial`` (``roi_utils``, ``valuation_utils``, …) will move into
this layer in a later refactor, not as part of the work that created it.

Modules:

* ``average_cost`` — average cost of positions: historical cost in the report and asset
  currencies, the pool after every movement, and the conversions that could not be made.
"""
