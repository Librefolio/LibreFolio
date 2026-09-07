---
title: "FIFO income silently dropped when no lot was open (pre-v4 allocator)"
category: "problem"
status: resolved
date: 2026-07-22
tags: ["backend", "fifo", "dividend", "data-quality"]
related: ["decisions/fifo-v4-income-eligibility-d1", "entities/lots-analysis-service", "concepts/asset-orphan-vs-portfolio-level-cost"]
---

# Problem: FIFO income silently dropped when no lot was open

## Symptom
Under the pre-v4 service-level income allocator (`LotsAnalysisService._allocate_asset_income`), a dividend or
interest event for an asset with no currently-open lot (e.g. income posted after the position was fully
closed) simply vanished — no error, no flag, no aggregate, nothing in the UI.

## Root Cause
The old allocator's logic simply **continued** when it found no open lot to allocate to, with no fallback
bucket to catch the amount.

## Solution
The v4 engine replaces this with an explicit fallback: an asset-linked income event that finds no eligible lot
becomes **`asset_orphan_income`**, tagged with a `ASSET_INCOME_NO_ELIGIBLE_LOTS` code and a `DEGRADED` status,
surfaced as a visible aggregate — never dropped, never assigned to the wrong lot. See
[[concepts/asset-orphan-vs-portfolio-level-cost]] and [[decisions/fifo-v4-income-eligibility-d1]].

## Prevention
Any "find a matching X, otherwise do nothing" allocator over financial amounts is a silent-data-loss bug by
construction — every financial pooling/allocation path needs an explicit orphan/fallback bucket, not a bare
`continue`/no-op, precisely so amounts can be reconciled to end up somewhere-traceable even in the no-match
case. This is now the general pattern followed by both the income path and the FEE/TAX cost ladders in
[[entities/fifo-lot-engine]] (see [[concepts/deterministic-cost-matching-ladder]]).

## Impact
Historical amounts affected by this bug were not retroactively recomputed/audited as part of this plan (no
persisted FIFO state exists to correct — see [[decisions/fifo-runtime-decision]], everything is recomputed at
query time) — simply re-running the analysis with the v4 engine now surfaces any such income as
`asset_orphan_income` instead of silently omitting it.

## Source files
| File |
|------|
| `backend/app/services/fifo_lot_engine.py` |
| `backend/app/services/lots_analysis_service.py` |
| `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/implementation-plan-v5.md` Fase 1 "Fuori pista" |
| `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/hig-level-analysis-v5.md` §12, §23.1 |
