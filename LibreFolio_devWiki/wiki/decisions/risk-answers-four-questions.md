---
title: "Risk answers «is my portfolio what I think it is?», not «how much risk do I have?»: four questions, one per level, and a tool sits where it answers one"
category: decision
status: resolved
date: 2026-09-16
tags: [risk, ux, levels, thesis, dashboard, lab, release-1.2]
related:
  - features/F-111
  - features/F-112
  - concepts/risk-binding-decisions
  - sources/phase00-risk-integration-2026-09
---

# Decision: the thesis of the Risk redesign

## Context

Risk Analysis shipped in 1.1.0 as a beta panel of metric cards. Replanning it on 2026-09-16, the folder-02 analysis
found that an isolated risk number leads to no decision: the user reads it, cannot tell whether it is high or low,
and closes the page. Sharpe, Sortino, beta, tracking error and the information ratio sat as orphan cards because they
answered no question the panel asked.

## Decision

The thesis (`01-tesi-e-quattro-domande.md`): «Risk non deve rispondere "quanto rischio ho?" (un numero). Deve rispondere
"il mio portafoglio è quello che credo che sia?" (una sorpresa)». Every Risk view must be able to end with «non lo
sapevo»; a section that cannot produce that sentence is not needed.

| Level | Question | Nature | Tools |
|-------|----------|--------|-------|
| L1 | How much can it hurt? | observed facts, magnitude | CVaR/VaR, max drawdown and its duration, current drawdown |
| L2 | Am I as diversified as I think? | structure | correlation, contribution to risk |
| L3 | Am I being paid for this risk? | relative, comparison | annual volatility, Sortino/Sharpe, beta, active return |
| L4 | What if…? | projection | historical replay, preset shocks, simulation |

L1, L2 and L4 look inside the portfolio; L3 is the only one that looks outward — the question a do-it-yourself
investor rarely says aloud: does all this complexity earn more than a single world ETF?

## Consequences

- The Risk tab of the Dashboard and broker pages renders the four levels (`bf34f3a0a`, [[features/F-111]]); the Lab
  reuses them for a selection of assets ([[features/F-112]]).
- A metric with no question has no home: tracking error and the information ratio stay only on the legacy Asset Detail
  panel ([[features/F-113]]) and in the deferrals.
- The other decisions that bind the work are listed in [[concepts/risk-binding-decisions]].

## Source files

| Role | Path |
|------|------|
| The thesis | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/01-tesi-e-quattro-domande.md` |
| The four levels | `frontend/src/lib/features/risk/levels/RiskLevelsPanel.svelte` |
| L3, the outward question | `frontend/src/lib/features/risk/levels/L3RiskAdjusted.svelte` |
