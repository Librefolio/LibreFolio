---
title: "AI Export technical series stay homogeneous, observed-only, and untruncated"
category: decision
status: resolved
date: 2026-07-30
mkdocs: null
tags: [ai-export, signals, portfolio, broker, asset, fx, timeseries, payload-size, risk]
related:
  - decisions/ai-export-versioned-snapshot-boundary
  - decisions/signal-backend-plugin-architecture
  - entities/ai-export-snapshot-service
  - entities/portfolio-engine
  - problems/ai-export-drawdown-selected-history-fallback
  - sources/phase00-ai-export-backend-snapshot
  - domains/signals
---

# Decision: AI Export technical series stay homogeneous, observed-only, and untruncated

## Context

The Phase 0 technical-density audit found correctness risks hidden by Portfolio/Broker position legs, currency conversion, bucket compaction, carry-forward observations, and a very large Full technical payload. These concerns must not be solved by feeding mixed financial series into the Signal System or by silently reducing the public export.

## Decision

- **Separate technical and financial series.** Asset, Portfolio, and Broker technical analysis uses homogeneous native-market price series. Asset market snapshots and Portfolio/Broker valuation remain separate target-currency financial resources. A mixed-currency series is retained for non-technical consumers with an explicit error, but an empty series is sent to signal calculation so indicators become unavailable rather than mathematically invalid.
- **Deduplicate the technical universe, not the books.** Portfolio/Broker position legs remain financial records. Technical prices, signals, events, and breadth run once per unique `asset_id`; gross exposure is summed across all broker legs for that asset before weights are normalized.
- **Use inter-bucket anchors.** Price/FX returns compare each non-empty bucket close with the previous non-empty close. The first populated bucket is null when no deterministic pre-period observation was loaded. Portfolio/Broker buckets derive period return from cumulative TWRR and derive P&L/external flow from Portfolio Engine fields; internal bucket first/last values are descriptive, not the return anchor.
- **Generate annotations from observations only.** AI Export crossings use absolute and relative epsilon `1e-12`, with `max(abs_epsilon, rel_epsilon * max(abs(left), abs(right)))`. Represented carry-forward days cannot emit events and do not reset a real Friday-to-Monday state transition; an unrepresented gap still resets it. FX carry-forward observations are excluded from returns and volatility.
- **Keep the current public payload complete.** Portfolio Full 1Y measures **2,676,781 characters / 669,196 estimated tokens**. Indicator history contributes **73.84%**, events **21.54%**, technical prices **2.86%**, and indicator metadata without rows **1.62%**. Sharing metadata alone saves only **0.82%**. The best offline candidate—latest state, period summary, last five indicator buckets, and all events—saves **70.27%**, but it is not implemented. No truncation or segmentation is permitted by this decision.
- **Suspend premature drawdown analysis.** `asset.drawdown_recovery` is removed from the public catalog until Risk supplies deterministic drawdown episodes. This supersedes its earlier public applicability while preserving the historical selected-period fallback record in [[problems/ai-export-drawdown-selected-history-fallback]].

## Consequences

- Financial valuation and technical interpretation may use different resources by design; their currencies and denominators must be explicit.
- Broker-leg duplication cannot duplicate technical work or distort breadth, while financial attribution remains broker-aware.
- First-bucket nulls and observed-only gaps are intentional audit semantics, not missing-data bugs.
- Payload reduction requires a future versioned contract decision; metadata deduplication is not an adequate remedy.
- The public analysis catalog contains 16 analyses until deterministic Risk drawdown data supports reinstatement.

## Validation

The real-service diagnostic probe completed all 27 Asset/Broker/Portfolio × 3M/6M/1Y × Compact/Standard/Full cases. Its offline scenarios alter copies only and do not modify the serialized public payload.

## Links

- [[decisions/ai-export-versioned-snapshot-boundary]]
- [[decisions/signal-backend-plugin-architecture]]
- [[entities/ai-export-snapshot-service]]
- [[entities/portfolio-engine]]
- [[problems/ai-export-drawdown-selected-history-fallback]]
- [[domains/signals]]

## Source files

| Role | Path |
|------|------|
| Findings and quantitative report | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/report-phase00AiExportSizeAndTechnicalDensity.md` |
| Raw 27-case probe output | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/probe-phase00AiExportTechnicalDensity.json` |
| Reproducible diagnostic probe | `backend/test_scripts/diagnostics/ai_export_technical_density_probe.py` |
| Native series, unique universe, weights, price/FX buckets | `backend/app/services/ai_export/components/technical_shared.py` |
| Observed-only crossings and epsilon policy | `backend/app/services/signal_annotations.py` |
| Portfolio/Broker TWRR, P&L, and flow buckets | `backend/app/services/ai_export/components/payloads/portfolio_broker.py` |
| Public 16-analysis catalog | `backend/app/services/ai_export/analyses/catalog.py` |
