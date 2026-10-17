"""PAC planner source: the authenticated, read-only snapshot of Portfolio, Broker, Asset, saved-price, WAC and
saved-FX facts behind the planner's copy actions.

It reads the database; the planner engine (normalization, evaluation, solver) never imports it. Import a name from
the module that defines it: this package re-exports nothing.

Modules:

* ``portfolio_allocation_source`` — the entry: owner check, selected scope and snapshot assembly
  (``build_portfolio_planner_source``).
* ``keys`` — provenance ids, stable entity keys, currency validation and field issues.
* ``loaders`` — custody quantities, latest saved prices and cash balances, read from the database.
* ``entities`` — the copied assets, brokers, holdings, cash balances and saved prices.
* ``classifications`` — the saved sector, geography and type distributions.
* ``wac`` — average purchase cost contexts and the saved FX evidence behind them.
* ``fx_quotes`` — the latest saved rate of every pair the copied facts need.
* ``distribution`` — the current weight distribution, valued by the portfolio engine.
"""
