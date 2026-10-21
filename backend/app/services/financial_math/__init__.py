"""Financial math layer: LibreFolio's financial calculations.

Every financial calculation has one implementation, and it lives here. Search this
package before writing a calculation, add a new one next to the calculations it relates
to, and never keep a local or partial copy elsewhere.

A calculation here owns its whole problem. It takes the plain data of the problem
(movements, currencies, dates) and calls the infrastructure it needs to complete it — the
FX service for conversions, the base currency from the settings service, the shared
data-quality thresholds, the cache — instead of receiving values prepared by its caller.
Where a calculation needs its own data from the database, it reads it at named points:
the portfolio engine, with the configured FX pairs its data-quality report names, the
Yield on Cost loaders, the ledger totals and the split links.

Engines, services and API handlers call this layer; it does not depend on them. It never
imports orchestration services (``portfolio_service``, ``broker_service``,
``transaction_service``, ``lots_analysis_service``), the API, AI Export, risk, PAC or
signals. A missing rate, price or cost is reported, never turned into a number. Packages
re-export nothing: import a name from the module that defines it, so that a test patches
the object the code actually reads.

Modules:

* ``average_cost`` — average cost of positions: historical cost in the report and asset
  currencies, the pool after every movement, the unit cost each movement carried, and the
  conversions that could not be made.
* ``native_cash`` — every broker's cash in the currencies it was recorded in: the balances,
  their value in the report currency on any day, and the period flows by type and position.
* ``ledger_totals`` — the control totals of the transaction ledger, with no price, rate or
  cost: cash per broker and currency and quantity per broker and asset, which a backup
  writes and a restore checks.
* ``returns`` — simple ROI, TWRR and MWRR, as point values and daily series (the
  Dashboard's MWRR rule, one for the card and every point of the line, in
  ``period_mwrr`` and ``period_mwrr_series``), the conversion between cumulative and annualized returns, a period's start (rebasing), the
  net return of a holding, a gain or loss as a fraction of its base (of one holding or a
  group), a change as a fraction of its base, the timing effect (MWRR − TWRR), the gain or loss a
  disposal realizes, the return between two prices (also as a float for a return series), the
  observed annualization factor of a return series (with ``DAYS_PER_YEAR``, its validator and
  the conversions between calendar days and observations), the change of a price or rate over the
  fixed periods of the Assets and FX tables, and the gain that recovers a drawdown.
* ``valuation`` — the value of a holding from its quantity, price and quote base quantity.
* ``fx_rates`` — the orientation of a stored FX rate: a pair read from source to destination,
  either way; and the unit rates a calculation reads by day, kept as steps and answered on the asked days only
  (``AskedDayRates``, P3).
* ``interest`` — the time fraction between two dates under a day count convention (ACT/365, ACT/360, ACT/ACT,
  30/360), simple interest and daily compounding over a span in closed form: the primitives the Scheduled
  Investment provider builds its accrual on.
* ``price_marks`` — the daily mark of an asset for valuation: the market quote, the
  same-day trade average, or the last observation carried forward.
* ``yield_on_cost`` — Yield on Cost of holdings, replayed from the transaction ledger.
* ``splits`` — the ADJUSTMENT rows linked to a SPLIT asset event, loaded with one query, the ids
  an average-cost replay marks as a rescale, and the rule for a usable split ratio.
* ``weights`` — a part's share of a total (none on a total at or below zero), the slices of an
  allocation, gross weights, and concentration (largest weight, Herfindahl index).
* ``holding_window`` — how long a position has been held at its broker: the oldest lot still
  open and a closed position's flight time, from its quantity stream (a split rescales the lots).
* ``fifo`` — FIFO lots: custody fragments, closures, transfers, and the allocation of
  income and costs to lots (``models``, ``eligibility``, ``engine``).
* ``portfolio`` — the daily portfolio state (NAV, capital, P&L, per-broker contributions)
  and the views derived from it (``models``, ``classifier``, ``daily_state``,
  ``derived_views``, ``data_quality``, ``period``, ``contributions``, ``engine``).
* ``lots`` — the math of the lots analysis: price lookups, conversions (a closure's legs,
  each at its own date), economic events, lot histories and average cost lines (``prices``, ``conversions``, ``economic_events``,
  ``histories``, ``average_cost_lines``).
"""
