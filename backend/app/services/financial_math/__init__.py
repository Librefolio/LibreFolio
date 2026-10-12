"""Financial math layer: LibreFolio's financial calculations.

Every financial calculation has one implementation, and it lives here. Search this
package before writing a calculation, add a new one next to the calculations it relates
to, and never keep a local or partial copy elsewhere.

A calculation here owns its whole problem. It takes the plain data of the problem
(movements, currencies, dates) and calls the infrastructure it needs to complete it — the
FX service for conversions, the base currency from the settings service, the shared
data-quality thresholds, the cache — instead of receiving values prepared by its caller.
Where a calculation needs its own data from the database, it reads it at named points:
the portfolio engine and the Yield on Cost loaders.

Engines, services and API handlers call this layer; it does not depend on them. It never
imports orchestration services (``portfolio_service``, ``broker_service``,
``transaction_service``, ``lots_analysis_service``), the API, AI Export, risk, PAC or
signals. A missing rate, price or cost is reported, never turned into a number. Packages
re-export nothing: import a name from the module that defines it, so that a test patches
the object the code actually reads.

Modules:

* ``average_cost`` — average cost of positions: historical cost in the report and asset
  currencies, the pool after every movement, and the conversions that could not be made.
* ``native_cash`` — every broker's cash in the currencies it was recorded in: the balances,
  their value in the report currency on any day, and the period flows by type and position.
* ``returns`` — simple ROI, TWRR and MWRR, as point values and daily series, and the
  conversion between cumulative and annualized returns.
* ``valuation`` — the value of a holding from its quantity, price and quote base quantity.
* ``price_marks`` — the daily mark of an asset for valuation: the market quote, the
  same-day trade average, or the last observation carried forward.
* ``yield_on_cost`` — Yield on Cost of holdings, replayed from the transaction ledger.
* ``fifo`` — FIFO lots: custody fragments, closures, transfers, and the allocation of
  income and costs to lots.
* ``portfolio`` — the daily portfolio state (NAV, capital, P&L, per-broker contributions)
  and the views derived from it.
"""
