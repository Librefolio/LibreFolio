---
title: "Drawdown: full_history warmup (signal toggle) + AI Export always full"
category: decision
date: 2026-09-02
tags: [backend, signals, risk, drawdown, ai-export, warmup]
related:
  - problems/mwrr-pole-dataless-period-start
---

# Drawdown full_history: signal toggle, AI Export always full

## Summary

Underwater drawdown has **unlimited memory**: the relevant peak may predate the
visible range by years, so any points-based warm-up is wrong by construction
(`total_points=2` made the "running peak" collapse to the visible-window max).
Decision (02/09, user): load full history when asked; expose the choice; AI
exports never get the shortened variant.

## Details

- **Signal path**: `DrawdownParams.full_history: bool = True` (user-visible
  toggle — boolean params render as checkboxes via `SignalParamControl`).
  `SignalWarmupRequirement.full_history` → `SignalExecutionPlan.requires_full_history`
  → `get_prices_bulk` loads from `date.min`. `compute()` unchanged; the existing
  post-computation slicing still cuts to the visible window.
- **AI Export path** (`drawdown_context._execute_drawdown`): the risk
  `drawdown_summary` analytic is always called with a full-history range —
  `date.min` for ASSET scope (price loads are sparse-safe: the prepared series
  starts at the first real price), the user's earliest accessible transaction
  (`resolve_date_sentinels`) for PORTFOLIO scope (the engine emits one history
  point per day in range — `date.min` would materialize millennia of empties).
- **Why not a SQL `MAX(close)` pre-seed** (the tempting cheap option): the
  drawdown runs on the **target-currency converted** series, and with variable
  FX `max(converted) ≠ converted(max)`. The seed is correct only at currency
  parity — exactly when you least need the optimization. A page that answers
  "why not just pre-query the max" lives here so nobody re-opens it.
- The discriminating test: absolute peak BEFORE the visible range → first
  visible point must measure against it (`test_risk_signal_plugins.py`).

## Source files

| Role | Path |
|------|------|
| Signal param + warmup | `backend/app/services/signal_plugins/drawdown.py` |
| Warmup contract | `backend/app/schemas/signals.py` (`SignalWarmupRequirement.full_history`) |
| Plan aggregation | `backend/app/services/signal_service.py` (`requires_full_history`) |
| Fetch window | `backend/app/services/asset_source.py` (`get_prices_bulk`) |
| AI Export full-history call | `backend/app/services/ai_export/components/drawdown_context.py` |
| Sentinel resolution | `backend/app/services/date_sentinel.py` |
