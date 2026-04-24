---
title: "ScheduledInvestment provider redesign — pure deterministic engine"
category: decision
status: resolved
date: 2026-04-01
tags: [assets, providers, scheduled-investment, events, architecture, db]
related: [entities/db-models, decisions/provider-registry-decision]
---

# Decision: ScheduledInvestment Provider Redesign — Pure Deterministic Engine

## Context
Phase 6 Step 3 Round 12 identified a critical circular dependency in the original ScheduledInvestment provider design. The provider read transactions from the DB to compute synthetic yields — creating a dependency loop: transactions → provider → prices → portfolio calculations. Additionally, the `AssetEvent` table needed to be introduced for cross-provider event storage.

## Options Considered
1. **Keep reading from DB** — simple but circular: provider depends on transactions that in turn depend on prices from the provider.
2. **Pure deterministic engine from `provider_params`** — given only the params, the provider computes prices and events without any DB access. Deterministic output for same input.

## Decision
**Pure deterministic engine** in `provider_params` only. The provider:
- Receives everything it needs in `provider_params` (including `initial_value` as a `Currency` object)
- Produces prices and events deterministically — same params → same output
- Has **NO database access** whatsoever during computation
- `AssetEvent` rows are written by the sync service after the provider runs, not by the provider itself

## Consequences

### Schema changes
- `initial_value` (Currency object) added to `provider_params` as a required field
- `AssetProviderAssignment.identifier` made nullable — not needed for `AUTO_GENERATED` type
- `AssetEvent` table added: `id, asset_id, date, type (AssetEventType), value_amount, value_currency, notes, provider_assignment_id`
- `AssetEvent.provider_assignment_id` FK → `asset_provider_assignments.id ON DELETE CASCADE`
- `AssetEventType` enum: `DIVIDEND, INTEREST, PRICE_ADJUSTMENT, SPLIT, MATURITY_SETTLEMENT`

### Financial model
- `maturation_frequency`: `DAILY, MONTHLY, QUARTERLY, SEMI_ANNUAL, ANNUAL, AT_MATURITY`
- Day count conventions: `ACT/365, ACT/360, ACT/ACT, 30/360`
- `InterestType`: `SIMPLE` (I = P₀ × r × Δt) or `COMPOUND` (V_{t-1} × r × Δt)
- `generate_interest=True` → automatic interest events at maturation dates
- `FALateInterestConfig` for post-maturity penalty rates
- Financial math functions (day count, simple/compound interest) live in `scheduled_investment.py` itself

### Caching
- 48h TTL cache keyed by hash of canonical `provider_params` — same params reuse computation

## Links
- [[entities/db-models]]
- Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step3/plan-phase06Step3Round12-AssetEventAndScheduleRedesign.prompt.md`
- Source: `backend/app/services/asset_source_providers/scheduled_investment.py`

## Source files

| Role | Path |
|------|------|
| ScheduledInvestment provider | `backend/app/services/asset_source_providers/scheduled_investment.py` |
| Phase 6 Round 12 plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step3/plan-phase06Step3Round12-AssetEventAndScheduleRedesign.prompt.md` |
| Maturation engine plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step3/plan-phase06Step3Round12Finale-MaturationEngine.prompt.md` |
| DB models | `backend/app/db/models.py` |
| ScheduledInvestment editor | `frontend/src/lib/components/assets/ScheduledInvestmentEditor.svelte` |
