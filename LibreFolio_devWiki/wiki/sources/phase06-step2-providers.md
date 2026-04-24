---
title: "Phase 06 Bugfix Step 2 — Asset Providers (CSS & Scheduled)"
category: source
source_type: plan
date_ingested: 2026-04-24
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step2/
tags: [phase06, providers, assets, css-scraper, scheduled-investment]
related_features: [F-034, F-035, F-025]
related_decisions: [scheduled-investment-redesign]
---

# Source: Phase 06 Bugfix Step 2 — Asset Provider Checklist

## Summary

Comprehensive checklist for CSS Scraper and Scheduled Investment asset providers, covering provider registration, params_schema, backend calculations, frontend editor components, and integration testing. Documents provider icon implementation and UI component patterns.

## Key Insights Extracted

### CSS Scraper Provider Implementation

**Provider Code**: `cssscraper`
**Identifier Type**: `URL` (web page URL to scrape)
**Supports Search**: No (requires manual URL entry)
**Supports History**: No (current value only)

**params_schema**:
- `current_css_selector` (string, required) — CSS selector for price element
- `currency` (string, required) — currency code
- `decimal_format` (select: "us" | "eu", default: "us") — number format
- `timeout` (number, default: 30) — HTTP timeout in seconds
- `user_agent` (string, default: "LibreFolio/1.0") — user agent header

**Parse Logic**: Handles both US (1,234.56) and EU (1.234,56) decimal formats, strips currency symbols and whitespace.

**Use Case**: Scraping financial data from websites without official APIs (e.g., central bank bond pages, broker-specific instruments).

**Icon**: `cssscraper.png` served via `/api/v1/uploads/plugin/asset/cssscraper.png`

### Scheduled Investment Provider Implementation

**Provider Code**: `scheduled_investment`
**Identifier Type**: `AUTO_GENERATED` (calculated, no external source)
**Supports Search**: No
**Supports History**: Yes (synthetic time series calculated from schedule)

**UI Component**: Custom `ScheduledInvestmentEditor.svelte` (1412 lines) — most complex component in the app.

**Schema**: `_ui_component` field in `params_schema` with `type: "ui_component"` signals frontend to render custom editor instead of generic form.

**Calculation Engine**:
- Principal derived from transactions (BUY/SELL/INTEREST)
- Interest modes: SIMPLE (linear) or COMPOUND (monthly/quarterly/annual)
- Day count conventions: ACT/365, ACT/360, 30/360
- Multi-period schedules with date ranges
- Post-maturity handling: grace period + late interest rate

**Editor Features**:
- CRUD periods (add/delete/split/merge)
- Bulk delete with multi-gap boundary date resolution
- Automatic contiguity enforcement (adjacent periods share boundaries)
- Late interest toggle with grace period popover
- Status banner showing N periods, total range, total days

**Related**: [[decisions/scheduled-investment-redesign]] documents the Round 12 redesign that established the maturation engine pattern.

## Frontend Patterns Documented

### Dynamic Form Generation from `params_schema`

**Pattern**: Backend providers expose `params_schema` property (JSON schema-like structure) describing required fields. Frontend `ProviderAssignmentSection.svelte` (724 lines) generates form fields dynamically:

```typescript
// params_schema structure
{
  field_name: {
    type: "string" | "number" | "select" | "ui_component",
    required: boolean,
    default?: any,
    options?: string[],  // for select type
    title?: string,
    description?: string
  }
}
```

**Special handling**:
- `type: "ui_component"` → render custom component (e.g., ScheduledInvestmentEditor)
- Fields prefixed with `_` (e.g., `_ui_component`) are filtered from generic form loop (metadata only)

### Provider Icon Fallback Chain

**Asset providers** (like FX providers):
1. If `icon_url` present → `<img>` with favicon
2. Else → text badge with provider name

**Static icon routing**: `GET /api/v1/uploads/plugin/asset/{filename}` serves PNG files from `backend/app/services/asset_source_providers/static/`.

## Problems Noted (from checklist comments)

### DateRangePicker Scroll Close Issue

**Symptom**: When opening month/year dropdown in DateRangePicker, scrolling causes the dropdown to close immediately.

**Status**: Bug noted in checklist but not fixed in this step (deferred).

### Probe Test Button Missing

**Symptom**: Frontend lacks "Test Connection" button to probe provider configuration before saving.

**Status**: Feature request noted in checklist, not implemented yet.

**Impact**: Users must save assignment and then manually trigger sync to test if provider config works.

### Dark Mode DatePicker Background

**Issue**: In dark mode, DatePicker transparent background makes icons hard to see.

**Proposed Fix**: Change background to white or panna (cream) in dark mode to maintain icon contrast.

**Status**: Noted but not fixed in this step.

### Late Interest Row Clickable When Disabled

**Issue**: Late interest row in ScheduledInvestmentEditor is clickable even when toggle is OFF.

**Expected**: Row should be non-interactive (grayed out, no hover) when late interest is disabled.

**Status**: Bug noted, not fixed.

### Boundary Date Picker — Year/Month/Days Input

**Enhancement Request**: Allow input like "1y 2m 10d" (1 year, 2 months, 10 days) instead of only total days. On reopen, convert back to logical y/m/d (1 year = 365 days, 1 month = 30 days).

**Status**: Enhancement idea, not implemented.

## Testing Coverage (from checklist)

**Backend** (per-provider unit tests):
- CSS Scraper: scrape with US/EU formats, selector not found, URL error, httpx missing, invalid params
- Scheduled Investment: simple/compound interest, multi-period, ACT/360, 30/360, transactions, post-maturity, grace period, late interest

**Frontend**:
- ScheduledInvestmentEditor: CRUD periods, split/merge, bulk delete (multi-gap), contiguity, late interest toggle, JSON round-trip

**Integration**:
- API probe for both providers
- Icon display in provider selector
- Dark mode visibility

## Source Files

| Role | Path |
|------|------|
| Source checklist | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step2/checklist-AssetProviders-CSSandScheduled.md` |
| CSS Scraper provider | `backend/app/services/asset_source_providers/cssscraper.py` |
| Scheduled Investment provider | `backend/app/services/asset_source_providers/scheduled_investment.py` |
| Provider base class | `backend/app/services/asset_source.py` |
| ScheduledInvestmentEditor | `frontend/src/lib/components/assets/ScheduledInvestmentEditor.svelte` |
| ProviderAssignmentSection | `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte` |
| CSS Scraper icon | `backend/app/services/asset_source_providers/static/cssscraper.png` |
| Scheduled Investment icon | `backend/app/services/asset_source_providers/static/scheduled_investment.png` |
