---
title: "Every Risk tool was judged by the four questions: core, kept with fixes, cut or deferred — a September verdict that later work partly reversed"
category: decision
status: resolved
date: 2026-09-16
tags: [risk, tools, metrics, levels, verdicts, tracking-error, optimization, monte-carlo, release-1.2]
related:
  - decisions/risk-answers-four-questions
  - features/F-110
  - features/F-111
  - features/F-113
  - sources/phase00-risk-integration-2026-09
---

# Decision: a tool that answers none of the four questions goes

## Context

With the thesis of [[decisions/risk-answers-four-questions]], the analysis `02-verdetti-per-strumento.md` judged every
tool of the 1.1 Risk subsystem by one criterion: «ogni strumento che non risponde a una delle quattro domande viene
tagliato».

## Decision

| Verdict | Tools (level) |
|---------|---------------|
| Core | max drawdown, the most important (L1); current drawdown and underwater (L1); CVaR read as a time scale (L1); correlation and risk contribution (L2); volatility, beta, active return (L3); hypothetical shock and historical replay (L4); data quality (every level) |
| Kept with fixes | Sortino and Sharpe; rolling signals (they stay in Asset Detail); Monte Carlo, to be rebuilt |
| Cut | tracking error and information ratio |
| Deferred | portfolio optimization |

## Consequences — today's code does not follow the verdict everywhere

Checked at `b4acfb250`: the «cut» tracking error and information ratio are still in the contracts (`schemas/risk.py`)
and on the legacy Asset Detail panel ([[features/F-113]]); the «deferred» optimization exists as a plugin
(`portfolio_optimization`, through riskfolio-lib), with its own open item A6 on [[features/F-110]]. Read the table as
the September plan; where later work kept a tool, the binding list is [[concepts/risk-binding-decisions]].

## Source files

| Role | Path |
|------|------|
| Contracts (TE and IR still present) | `backend/app/schemas/risk.py` |
| Optimization plugin | `backend/app/services/risk_plugins/portfolio_optimization/plugin.py` |
| Journal | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/02-verdetti-per-strumento.md` |
