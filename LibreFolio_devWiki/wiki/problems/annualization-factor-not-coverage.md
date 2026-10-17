---
title: "A fixed annualisation factor of 252 overstated Sharpe, and measuring «coverage» would have hidden it: the factor is now observed from the data"
category: problem
status: resolved
date: 2026-09-18
tags: [risk, annualization, sharpe, sortino, volatility, calendar, metrics, release-1.2]
related:
  - features/F-110
  - problems/docs-claimed-what-the-code-did-not-do
  - sources/phase00-risk-integration-2026-09
---

# Problem: the reassuring number that was false

## Symptom

Risk metrics annualised every series with a fixed factor of 252, whatever the series' real frequency. Stream A of the
first round measured the effect: a Sharpe ratio overstated by about +0.03 to +0.08.

## Root Cause

The factor `f` and the series' `coverage` are computed over different denominators: on perfectly healthy data
`coverage ≈ 1.000` while `f ≈ 252`. Checking coverage would have produced a figure «rassicurante e falsa» (the stream's
progress log).

## Solution

The factor is observed from the series itself — `observed_annualization` returns `n_observations · 365 /
calendar_days` (`market_series.py`) — and the same `f` scales the volatility and converts the risk-free rate
(`daily_risk_free_rate` in `metrics.py`), so numerator and denominator speak of the same period. The documentation
followed later: the Sharpe and Sortino pages stopped converting with 1/365 (`1fdcaef38`,
[[problems/docs-claimed-what-the-code-did-not-do]]).

## Prevention

A ratio's two sides must use the same period; derive the period from the data, and never validate one quantity by
measuring another with a different denominator.

## Source files

| Role | Path |
|------|------|
| Observed factor | `backend/app/services/market_series.py` |
| Risk-free rate per period | `backend/app/services/risk/metrics.py` |
| Journal (stream A) | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation/progress/A-esecuzione.md` |
