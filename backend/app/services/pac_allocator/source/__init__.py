"""PAC planner source: the authenticated, read-only snapshot of Portfolio, Broker, Asset, saved-price, WAC and
saved-FX facts behind the planner's copy actions.

It reads the database; the planner engine (normalization, evaluation, solver) never imports it. Import a name from
the module that defines it: this package re-exports nothing.
"""
