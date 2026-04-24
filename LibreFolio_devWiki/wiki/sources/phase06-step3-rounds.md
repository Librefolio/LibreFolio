---
type: source
group: phase06-step3-rounds
ingested: 2026-05-24
git_hash: e8ab12a
covers: [F-033, F-034]
---

# Source: Phase 06 Step 3 Rounds 1–11 (AssetModal & ScheduledInvestmentEditor Bugfix Iterations)

## What this source covers

Eleven iterative bugfix-and-design rounds covering the creation of `AssetModal.svelte`, `AssetSearchAutocomplete.svelte`, `ProviderAssignmentSection.svelte`, and `ScheduledInvestmentEditor.svelte`. The rounds progressed from initial concept (Round 1) through a complex multi-round design conversation for the scheduled investment editor (F9, Rounds 6-8), culminating in a stable tested state by Round 11.

## Key decisions extracted

- **Asset type normalization belongs in the backend**: `yfinance.search()` returns raw `"EQUITY"` — the backend `AssetSearchService.search()` normalizes to `STOCK`/`ETF`/etc. before returning to frontend. Frontend never needs a `PROVIDER_TYPE_MAP`.
- **`ui_component` inside `params_schema`**: Provider's custom editor is declared via a special entry in `params_schema`, NOT as a top-level `FAProviderInfo.ui_component` field. ScheduledInvestmentEditor is selected when `params_schema` contains the `scheduled_investment` UI component key.
- **INDEX as a no-transaction asset type**: User decision to add `INDEX` as an asset type, but flagged that INDEX assets cannot have transactions attached (they are virtual benchmark signals).
- **`assetTypes.ts` utility**: Central location for `ASSET_TYPES`, `getAssetTypeIconUrl()`, `buildAssetTypeOptions()` — eliminates duplication across `AssetIcon`, `AssetModal`, `AssetTable`.
- **No streaming search (deferred)**: WebSocket/SSE streaming search was explored but deferred; current search uses parallel provider queries with monotonic `searchId` for stale-result protection.
- **classification_params from Day 1**: Must be auto-populated by `fetch_asset_metadata()` (sector, geographic area, description). These feed future dashboard & X-ray calculations.

## Key problems recorded

- **BUG: Create asset 201 but modal doesn't close** (Round 2, BUG-11): Provider assign step failed silently after create succeeded. Fix: separate try/catch for create vs assign, scroll `formError` into view.
- **BUG: SimpleSelect dropdown clipped by overflow** (Round 2, BUG-12): Collapsible panels with `overflow-hidden` clipped select dropdowns. Fix: use `position:fixed` + `getBoundingClientRect()` for dropdown positioning.
- **BUG: ProviderInputType vs IdentifierType mismatch** (Round 10, §1 CRITICAL): `GET /assets/query` returned 500 when an asset had `identifier_type = AUTO_GENERATED`. See [[problems/asset-list-500-provider-input-type]].
- **BUG: Scroll listener closes date picker** (Round 11, §A1): Scroll listener in DateRangePicker/SingleDatePicker/CellDateRange closed the popover on any page scroll, even though `position:fixed` means scroll can't misalign it. Fix: remove the scroll listener entirely.
- **BUG: Changing provider doesn't clear old params** (Round 10, §2): Switching from CSS Scraper to ScheduledInvestment left old params in payload. Fix: clear `providerParams` and `identifier` on provider change.

## Features enriched

- [[F-033]] — AssetModal.svelte implementation details, provider assignment section, asset icon picker, identifier management, duplicate name detection
- [[F-034]] — ScheduledInvestmentEditor F9 details: layout β, merge/split/bulk-delete, late interest row, CellDateRange, contiguity engine

## Source files ingested

| File | Purpose |
|------|---------|
| `plan-phase06Step3AssetModal.prompt.md` | Initial AssetModal design: backend probe endpoint, identifier flow, schema inheritance |
| `bugfix-phase06Step3.md` | Round 1-2 bug list, refactoring R-1/R-2/R-3, design proposals for icon layout |
| `plan-phase06Step3Round2.prompt.md` | Round 2 planning |
| `plan-phase06Step3Round2.implementation.prompt.md` | Round 2 implementation details |
| `plan-phase06Step3Round2Fix.prompt.md` | Round 2 fixes |
| `plan-phase06Step3Round5Fix.prompt.md` | Round 5 fixes |
| `plan-phase06Step3Round5_1Fix.prompt.md` | Round 5.1 fixes |
| `plan-phase06Step3Round6-LayoutPolish.prompt.md` | Layout B + F1–F9 plan (F9 as draft); provider anatomy diagrams |
| `plan-phase06Step3Round7-F9ScheduledInvestmentEditor.prompt.md` | F9 definitive design: layout β, CellDateRange, late interest, contiguity, CRUD |
| `plan-phase06Step3Round8-ModalFix+BulkDeleteRewrite.prompt.md` | F9 impl progress, bulk delete multi-gap §5, ui_component in params_schema |
| `plan-phase06Step3Round9-PolishAndFixes.prompt.md` | Post-F9 polish: DateRangePicker IDE fixes, toolbar alignment, tooltip multi-line |
| `plan-phase06Step3Round10-PostTestingPolish.prompt.md` | 12 issues incl. CRITICAL list_assets 500, provider params clearing, grace period Y/M/D |
| `plan-phase06Step3Round11-BugMitigationAndScheduleRedesign.prompt.md` | Bug mitigations + discovery of scheduled_investment circular dependency → Round 12 |
| `checklist-F9-MergeSplitTest.md` | Test checklist for merge/split operations |
