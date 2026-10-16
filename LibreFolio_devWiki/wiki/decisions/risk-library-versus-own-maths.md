---
title: "Risk maths: a library only where ours duplicates it badly, our own code where it composes — correctness decides, not speed, and the library is the test oracle"
category: decision
status: resolved
date: 2026-09-16
tags: [risk, metrics, riskfolio, numpy, pandas, cvar, performance, oracle, release-1.2]
related:
  - features/F-110
  - decisions/risk-quant-engine-process-boundary
  - decisions/histogram-grid-pinned-to-var-cut
  - problems/riskfolio-numpy-vectorbt-dependency-trap
  - sources/phase00-risk-integration-2026-09
---

# Decision: when to call riskfolio-lib, when to keep our maths

## Context

The analysis `06-matematica-librerie-e-reimplementazioni.md` (folder 02, September 2026) compared the engine's own
maths with riskfolio-lib. It matched to the eighth decimal on VaR, max drawdown, Sharpe and risk contribution, and found
three real problems: rolling signals computed in a Python loop, up to 1,514 times slower than `pandas.rolling`; a CVaR
from the naive plug-in estimator, always below riskfolio's coherent Acerbi-Tasche one (plus an off-by-one); and pure
Python matrices, O(N²·T), 3.7 s at 100 assets.

## Decision

Move the true duplicates to NumPy, pandas or the library, and keep composed metrics as our own code. The question is
correctness, not speed — our own pure-Python max drawdown was about four times faster than riskfolio's; the document's caution: «usare la
libreria» non equivale a «usare il C». riskfolio-lib serves first as the **test oracle**
(step M4 of its plan), then as an engine only where it is needed, in spawned processes
([[decisions/risk-quant-engine-process-boundary]]).

## Consequences

Checked on the code at `b4acfb250`:

- `historical_var_cvar` returns the empirical VaR and the coherent CVaR (Acerbi-Tasche / Rockafellar-Uryasev) in
  `metrics.py`;
- rolling compounding is vectorised (`np.expm1(np.log1p(series).rolling(window).sum())` in `signal_helpers.py`);
- the oracle pins the hand-written maths before any migration ([[decisions/histogram-grid-pinned-to-var-cut]]).

## Source files

| Role | Path |
|------|------|
| VaR, CVaR, histogram | `backend/app/services/risk/metrics.py` |
| Rolling signals | `backend/app/services/signals/risk_adapters.py` |
| riskfolio-lib in its process | `backend/app/services/risk/quant/riskfolio_worker.py` |
| Journal | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/06-matematica-librerie-e-reimplementazioni.md` |
