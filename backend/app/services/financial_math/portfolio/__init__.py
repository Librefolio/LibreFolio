"""Daily portfolio state: NAV, capital, P&L, per-broker contributions, and the views derived from them.

One engine produces a vector of daily portfolio states, from which every view (summary,
history, allocation, performance) is derived:

1. ``classifier`` — ``ScopeAwareTransactionClassifier`` classifies transactions as internal or
   external to the selected brokers, with the in-transit intervals of transfers.
2. ``daily_state`` — ``DailyStateBuilder`` builds the daily state vector, without I/O.
3. ``derived_views`` — ``DerivedViewsBuilder`` derives history, per-broker P&L, candles,
   acquisition funding, performance inputs and allocation; ``build_cost_positions`` feeds the
   average cost.
4. ``engine`` — ``PortfolioCalculationEngine`` loads the data of a scope, calls 1-3, and caches
   the result.

``models`` holds the data shared by these steps; ``data_quality`` holds the FX pair slug, the
configured pair sets, and the data-quality report.

This package re-exports nothing: import a name from the module that defines it.
"""
