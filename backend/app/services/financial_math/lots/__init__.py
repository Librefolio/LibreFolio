"""Math of the lots analysis, called by ``lots_analysis_service``.

Modules:

* ``prices`` — the daily market prices of an asset, and the reference price of a lot at its
  opening.
* ``conversions`` — the FX resolver, loaded once per request, and the conversions each view needs.
* ``economic_events`` — income and costs as FIFO engine inputs, their allocation to lots, and what
  is withheld when a rate is missing.
* ``histories`` — performance, value, return and price of each lot over time.
* ``summary`` — a lot's figures: the cost of its open quantity, its value and P&L by direction, the summary.
* ``average_cost_lines`` — the per-broker and cumulative average cost history points.

This package re-exports nothing: import a name from the module that defines it.
"""
