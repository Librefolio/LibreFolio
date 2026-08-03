---
title: "AI Export technical scope stays complete while detail owns public density"
category: decision
status: resolved
date: 2026-07-30
updated: 2026-08-03
mkdocs: "developer/architecture/patterns/ai_export_sampling.md"
tags: [ai-export, signals, portfolio, broker, asset, fx, timeseries, payload-size, sampling, events, risk]
related:
  - decisions/ai-export-versioned-snapshot-boundary
  - decisions/signal-backend-plugin-architecture
  - entities/ai-export-snapshot-service
  - entities/portfolio-engine
  - problems/ai-export-drawdown-selected-history-fallback
  - sources/phase00-ai-export-backend-snapshot
  - domains/signals
---

# Decision: AI Export technical scope stays complete while detail owns public density

## Context

The Phase 0 technical-density audit found correctness risks hidden by Portfolio/Broker position legs, currency conversion, bucket compaction, carry-forward observations, and a very large Full technical payload. These concerns must not be solved by feeding mixed financial series into the Signal System or by silently reducing the public export.

## Decision

- **Separate technical and financial series.** Asset, Portfolio, and Broker technical analysis uses homogeneous native-market price series. Asset market snapshots and Portfolio/Broker valuation remain separate target-currency financial resources. A mixed-currency series is retained for non-technical consumers with an explicit error, but an empty series is sent to signal calculation so indicators become unavailable rather than mathematically invalid.
- **Deduplicate the technical universe, not the books.** Portfolio/Broker position legs remain financial records. Technical prices, signals, events, and breadth run once per unique `asset_id`; gross exposure is summed across all broker legs for that asset before weights are normalized.
- **Use inter-bucket anchors.** Price/FX returns compare each non-empty bucket close with the previous non-empty close. The first populated bucket is null when no deterministic pre-period observation was loaded. Portfolio/Broker buckets derive period return from cumulative TWRR and derive P&L/external flow from Portfolio Engine fields; internal bucket first/last values are descriptive, not the return anchor.
- **Generate annotations from observations only.** AI Export crossings use absolute and relative epsilon `1e-12`, with `max(abs_epsilon, rel_epsilon * max(abs(left), abs(right)))`. Represented carry-forward days cannot emit events and do not reset a real Friday-to-Monday state transition; an unrepresented gap still resets it. FX carry-forward observations are excluded from returns and volatility.
- **Keep the public scope complete while reducing historical density.** Signal Density V2 and its 2026-08-03 amendment change deterministic history/event density, not the selected Asset/Signal scope, price/rate precision, calculable indicators, canonical outputs, `period_summary`, or latest state. They do not use size-triggered truncation, segmentation, pagination, automatic detail downgrade, Asset removal, or indicator-dimension removal.
- **Suspend premature drawdown analysis.** `asset.drawdown_recovery` is removed from the public catalog until Risk supplies deterministic drawdown episodes. This supersedes its earlier public applicability while preserving the historical selected-period fallback record in [[problems/ai-export-drawdown-selected-history-fallback]].

## Signal Density V2 completion

- **Migrate the beta contract in place.** Component, dataset, analysis, sampling, manifest, and response contract IDs remain v1. There is no legacy payload, compatibility fallback, parallel runtime, or silent downgrade.
- **Leave price/rate sampling unchanged.** Asset prices, FX rates, and equivalent reference series retain the existing detail-only P/M/K policy; signal temporal classes affect indicator history only.
- **Combine plugin-owned meaning with a central matrix.** Each signal plugin resolves exactly one `SignalTemporalClass`; the central `detail_level + temporal_class` matrix owns P/M/K. All **18/18** official detail/class combinations are valid, and all **54/54** theory/runtime bucket counts match for 90, 180, and 365 days.
- **Preserve observation-level semantics.** `period_summary` and latest value/date remain calculated from the full observation-level period. Multi-output indicators share one temporal grid per signal instance.
- **Select events independently per entity and annotation.** For each `entity_id + annotation_key`, Compact exports the complete latest 7 calendar days and at least the latest 3 events when available; Standard exports the complete latest 21 calendar days and at least the latest 10; Full exports the complete latest 30 calendar days and at least the latest 20. There is no ranking, relevance score, family quota, or hard cap inside the complete recent window. Each group reports full detected/recent/exported counts and detected/exported date ranges.
- **Expose the effective policy.** The snapshot response publishes `technical_sampling` and `event_selection`; the frontend copies both into the Snapshot Metadata and Dataset Manifest block.
- **Keep exclusions explicit.** This work makes no price-policy change, segmentation, token/character truncation, Drawdown Recovery reinstatement, FX coupling repair, or opportunistic P1 change.

## 2026-08-03 approved and applied density policy

- The backend now keeps every Signal and eligible Asset but emits a deterministic
  uniform sample of non-empty indicator buckets per entity/instance: Compact 5,
  Standard 10, Full all. First/last rows remain represented; latest values and
  `period_summary` still use the complete exported period.
- `technical_sampling.indicator_history_row_limit` makes the policy public.
  Indicator payloads retain source bucket and source non-empty row counts.
- Empty indicator rows are omitted from the payload while their counts remain
  auditable. No observed zero is converted to absence.
- The public renderer also omits a financial temporal row only when it is completely
  empty. Observed zero, flow, P&L, extrema, reconciliation, economic dates, and
  explicit state remain public; backend buckets, calculations, frequency, and
  sampling are unchanged.
- The text renderer uses row-relative history dates and definition-owned positional
  event values. These encodings are lossless and remove repeated labels/dates.
- Event density is backend-owned and detail-dependent: Compact uses a complete
  7-day recent window plus minimum latest 3 per entity/annotation; Standard uses
  a complete 21-day recent window plus minimum latest 10; Full uses a complete
  30-day recent window plus minimum latest 20.
- The project owner explicitly approved the Standard 21-day/minimum-10 policy on
  3 August 2026. Indicator history remains Compact 5, Standard 10, and Full all
  non-empty rows.
- Applied-policy run `20260803T164514.504966Z` completed 7/7 prompts with zero
  failures and zero public-output violations, UI/probe equivalence in 7/7,
  a passed secret scan, and unchanged source and production databases.
- Dense Portfolio and Broker exports can exceed 60,000 estimated tokens. The
  20k/60k UI warning remains the user control; density must not be replaced by an
  automatic cap, hidden truncation, or automatic detail downgrade.

## Final hardening approval

On 3 August 2026 the project owner also explicitly approved the final public
empty-temporal-row hardening, the explicit Broker nomenclature, and targeted run
`20260801T085820.657238Z` as the final focused evidence. That run covered 4/4
targeted prompts with no failure, skip, or regression, exact UI/probe
equivalence, a passed secret scan, and unchanged source and production databases.

## Consequences

- Financial valuation and technical interpretation may use different resources by design; their currencies and denominators must be explicit.
- Broker-leg duplication cannot duplicate technical work or distort breadth, while financial attribution remains broker-aware.
- First-bucket nulls and observed-only gaps are intentional audit semantics, not missing-data bugs.
- Signal Density V2 is an auditable beta-v1 sampling contract rather than compatibility fallback or size-triggered truncation. Compact/Standard density is selected by the explicit user detail level; Full remains the complete non-empty history policy.
- Prompt-size severity is advisory. Large, complete Portfolio/Broker exports remain copyable after the existing warning flow rather than being silently capped.
- Portfolio Full 1Y falls from **2,676,781** to **1,990,718** characters (**-25.630151%**). Indicator characters fall **19.934224%** and event characters **49.662553%**; **1,615** events are detected and **707** exported.
- FX remains blocked by the known `fx.rate_ohlc` warm-up coupling; all nine optional FX matrix probes fail before a measurable payload and remain outside this decision's repair scope.
- The public analysis catalog contains 16 analyses until deterministic Risk drawdown data supports reinstatement.

## Validation

The original real-service diagnostic probe completed all 27 Asset/Broker/Portfolio × 3M/6M/1Y × Compact/Standard/Full cases. The completed V2 probe then passed all **27/27** required cases, validated **18/18** temporal-policy combinations and **54/54** theory/runtime counts, and recorded the known non-fatal FX result as **0/9 passed** because `fx.rate_ohlc` fails during warm-up. The final applied-policy authority is `20260803T164514.504966Z`; the final targeted hardening authority is `20260801T085820.657238Z`.

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
| Signal Density V2 report | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/report-phase00AiExportSignalDensityV2.md` |
| Signal Density V2 probe output | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/probe-phase00AiExportSignalDensityV2.json` |
| Cross-domain density audit and applied-policy evidence | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/report-phase00AiExportCrossDomainDensityAuditV1.md` |
| Final hardening approval and targeted evidence | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/report-phase00AiExportFinalHardeningAndDocumentationV1.md` |
| Reproducible diagnostic probe | `backend/test_scripts/diagnostics/ai_export_technical_density_probe.py` |
| Real-prompt validation probe | `backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py` |
| Central indicator sampling matrix | `backend/app/services/ai_export/temporal/policy.py` |
| Plugin-owned temporal-class contract | `backend/app/services/signal_plugins/base.py` |
| Native series, unique universe, weights, price/FX buckets | `backend/app/services/ai_export/components/technical_shared.py` |
| Indicator and event payload contracts | `backend/app/services/ai_export/components/technical_payloads.py` |
| Sampling and event-selection response manifests | `backend/app/services/ai_export/runtime_service.py` |
| Observed-only crossings and epsilon policy | `backend/app/services/signal_annotations.py` |
| Portfolio/Broker TWRR, P&L, and flow buckets | `backend/app/services/ai_export/components/payloads/portfolio_broker.py` |
| Public 16-analysis catalog | `backend/app/services/ai_export/analyses/catalog.py` |
| Frontend metadata rendering | `frontend/src/lib/features/ai-export/templates/promptRenderer.ts` |
| Empty temporal-row renderer hardening | `frontend/src/lib/features/ai-export/templates/snapshotDataRenderer.ts` |
| Broker scope nomenclature | `backend/app/services/ai_export/components/portfolio_financial.py`, `backend/app/services/ai_export/runtime_service.py` |
| 20k/60k warning without automatic cap | `frontend/src/lib/features/ai-export/aiExportOptions.ts`, `frontend/src/lib/features/ai-export/AiExportOptionsPanel.svelte` |
| Snapshot architecture guide | `mkdocs_src/docs/developer/architecture/patterns/ai_export_snapshot.md` |
| Composition and manifest guide | `mkdocs_src/docs/developer/architecture/patterns/ai_export_composition.md` |
| Sampling and event-selection guide | `mkdocs_src/docs/developer/architecture/patterns/ai_export_sampling.md` |
