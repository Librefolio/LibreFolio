---
title: "Asset onboarding flow"
category: workflow
tags: [assets, providers, frontend, ux, api]
related: [entities/db-models, decisions/scheduled-investment-redesign]
---

# Workflow: Asset Onboarding Flow

## Overview
End-to-end steps to add a new asset to LibreFolio, from the initial database record through provider assignment, price sync, and viewing.

## Steps

### 1. Create the asset record
**API**: `POST /api/v1/assets`
**Payload**: `display_name`, `currency`, `asset_type`, optional identifiers (`identifier_isin`, `identifier_ticker`, …)
**Frontend entry point**: Assets list page `frontend/src/routes/(app)/assets/+page.svelte` → click "Add Asset" → `AssetModal.svelte` opens

### 2. Auto-fill via search
`AssetSearchAutocomplete.svelte` triggers parallel provider searches (yfinance, JustETF, etc.) as the user types.
Selecting a search result auto-fills: `display_name`, `currency`, `asset_type`, identifiers, and suggests a provider.

### 3. Assign a provider
**API**: `POST /api/v1/assets/{id}/providers`
**Payload**: `provider_code`, `identifier`, `identifier_type`, `provider_params` (dynamic — from provider's `params_schema`)
**Frontend**: `ProviderAssignmentSection.svelte` renders the dynamic form from `params_schema`

#### Special case — ScheduledInvestment
`ScheduledInvestmentEditor.svelte` (1412 lines) opens for `SCHEDULED_YIELD` assets.
The editor defines: `initial_value`, interest schedule (date ranges + rates), `maturation_frequency`, `InterestType`, day count convention, optional `FALateInterestConfig`.

### 4. Sync prices
**API**: `POST /api/v1/assets/{id}/refresh`
The provider fetches/computes price history. Results stored in `PriceHistory` with `currency` per row.
**Frontend**: Sync triggered from asset detail page via sync button (similar pattern to `FxSyncModal`).

### 5. View asset
**Route**: `frontend/src/routes/(app)/assets/[id]/+page.svelte`
**Components**:
- `PriceChartFull.svelte` — full chart with signals overlay
- `AssetDataEditorSection.svelte` — 2-tab editor (Prices + Events)
- `ProviderAssignmentSection.svelte` — manage/reassign provider
- `ProviderComparisonModal.svelte` — diff between provider data and DB

## Involved APIs
| Step | Method | Endpoint |
|------|--------|----------|
| Create | POST | `/api/v1/assets` |
| Assign provider | POST | `/api/v1/assets/{id}/providers` |
| Sync | POST | `/api/v1/assets/{id}/refresh` |
| Get detail | GET | `/api/v1/assets/{id}` |
| Get prices | GET | `/api/v1/assets/{id}/prices` |
| Get events | GET | `/api/v1/assets/{id}/events` |

## Source files

| Role | Path |
|------|------|
| Assets list page | `frontend/src/routes/(app)/assets/+page.svelte` |
| Asset detail page | `frontend/src/routes/(app)/assets/[id]/+page.svelte` |
| AssetModal | `frontend/src/lib/components/assets/AssetModal.svelte` |
| AssetSearchAutocomplete | `frontend/src/lib/components/assets/AssetSearchAutocomplete.svelte` |
| ProviderAssignmentSection | `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte` |
| ScheduledInvestmentEditor | `frontend/src/lib/components/assets/ScheduledInvestmentEditor.svelte` |
| PriceChartFull | `frontend/src/lib/components/charts/PriceChartFull.svelte` |
| AssetDataEditorSection | `frontend/src/lib/components/assets/AssetDataEditorSection.svelte` |
| Assets API | `backend/app/api/v1/assets.py` |
