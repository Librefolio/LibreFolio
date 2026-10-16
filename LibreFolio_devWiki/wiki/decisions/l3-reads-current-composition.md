---
title: "L3 measures the composition held today, replayed over the past, and every card names its mode"
category: decision
status: resolved
date: 2026-09-18
tags: [risk, l3, beta, benchmark, composition, annualization, dashboard, release-1.2]
related:
  - features/F-111
  - decisions/risk-answers-four-questions
  - concepts/risk-binding-decisions
  - sources/phase00-risk-integration-2026-09
---

# Decision: «Am I being paid for this risk?» is asked of what I hold now

## Context

L3 compares the portfolio with the outside world ([[decisions/risk-answers-four-questions]]). In `historical` mode the
portfolio's series is dominated by cash flows — on the test data, 49 % cash — so beta against any benchmark came out
near zero: arithmetically right and meaningless. The first mock benchmark made it worse: a beta of 0.023 with no
warning, a benchmark in name only, until the test indices were rebuilt (`bafa4663b`).

## Decision

S3's «Decisione A» (second round, register entry R2-20): all of L3 reads `current_composition` — today's holdings
replayed over the past — and **every card names its mode**: «Un beta senza il suo modo è un numero senza perimetro.»
Delivered in `afd480a89` («feat(risk): answer L3 on the composition actually held»). The expected return is annualised
arithmetically, `expected_period_return × f`, the convention already in the code (R2-28): with it, the slope of the
risk–return line is exactly the Sharpe ratio.

## Consequences

- A result computed on today's composition is a backtest, and says so (`current_composition_backtest` in the result).
- The benchmark rules that followed — one shared benchmark, an owned asset allowed — are in
  [[concepts/risk-binding-decisions]] (D370, D371, D378).

## Source files

| Role | Path |
|------|------|
| L3 benchmark card (the mode and its reason) | `frontend/src/lib/features/risk/levels/L3Benchmark.svelte` |
| Risk–return plugin | `backend/app/services/risk_plugins/asset_risk_return/plugin.py` |
| Journal (S3) | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/S3-livello-3.md` |
