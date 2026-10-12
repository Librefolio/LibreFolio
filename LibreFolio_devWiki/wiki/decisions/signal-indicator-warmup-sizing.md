---
title: "Each signal plugin sizes its own warm-up so the visible range matches the reference library: measured per period, not guessed"
category: decision
status: resolved
date: 2026-07-23
tags: [signals, indicators, warm-up, kama, adx, accuracy, backend, plugins]
related:
  - decisions/signal-backend-plugin-architecture
  - decisions/drawdown-full-history-warmup
---

# Decision: warm-up points are a measured property of each indicator

## Context

When the technical-analysis signals moved to backend plugins (folder `01_signalMigration`, July 2026), each plugin
had to fetch enough history before the visible range for its values to match the reference library's. A recursive
indicator such as ADX or KAMA converges slowly, and a fixed «a few times the period» is wrong somewhere.

## Decision

Each plugin declares its own `minimum_points` and warm-up, and the values were measured across periods 2–200 against
the reference, with a tolerance of 1e-6. The audits corrected two plugins (`5b9dddb45`, «feat: add backend signals and
isolate sessions»):

- **KAMA**: `minimum_points` was one short for periods of 30 and more; it is now `max(30, period + 1)`;
- **ADX**: a warm-up of 16 × period missed the tolerance on 32 intermediate periods; it is now 18 × period (worst
  error measured about 2.7e-7), with tests at periods 95, 150 and 200.

A single OBV point is reported as `partial`, not as an error.

## Consequences

A new indicator plugin states its warm-up from a measurement against its reference, across the whole period range,
and pins the extreme periods in tests; the same idea, for drawdowns, is [[decisions/drawdown-full-history-warmup]].

## Source files

| Role | Path |
|------|------|
| KAMA (`minimum_points`) | `backend/app/services/signal_plugins/kama/plugin.py` |
| ADX (warm-up) | `backend/app/services/signal_plugins/adx/plugin.py` |
| Journal | `LibreFolio_developer_journal/Release_2/phases/01_signalMigration/plan-phase00SignalsBackendMigrationImplementation.prompt.md` |
