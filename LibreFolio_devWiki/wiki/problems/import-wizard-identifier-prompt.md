---
title: "Import Wizard: identifier prompt skipped on asset create"
category: problem
status: open
date: 2026-06-25
tags: [frontend, import-wizard, brim, identifier-prompt, asset-modal, svelte5]
related:
  - sources/phase-final-bugs-2026-06-25
  - entities/import-wizard-modal
  - features/F-012
  - features/F-048
---

# Problem: Import Wizard Identifier Prompt Skipped on Asset Create

## Symptom

In the Import Wizard Step 4 (Review & Import), when the user creates a new asset via the `AssetModal` (clicking "+ Create new" from the asset resolution panel), the identifier-mapping prompt does NOT open after the asset is saved. The user can import without being asked "Do you want to associate this identifier with the new asset?"

Expected behavior: after creating a new asset via `oncreated`, the wizard should check if the extracted identifier (ISIN, ticker) should be linked to the new asset and open the prompt if so.

## Root Cause

Two bugs in `ImportWizardModal.svelte`:

**Bug 1 — Wrong resolution path** (line ~2377–2382):
```ts
oncreated={(assetId) => {
    resolveAsset(createAssetForFakeId!, assetId);  // ← only this
    createAssetForFakeId = null;
}}
```
`resolveAsset()` (L352) records the resolution but does NOT call `resolveAssetManual()` (L391). Only `resolveAssetManual()` opens `identifierPromptOpen`. So the `oncreated` path bypasses the identifier prompt entirely.

**Bug 2 — Wrong AssetModal initial state** (L469):
`AssetModal` is opened with `providerNoProvider = false` (default). But when opened from the import wizard, the user is creating a manual asset (no online provider search). The modal should open with `providerNoProvider = true` to pre-select "No provider" and skip the provider search step.

## Solution (proposed)

1. In `oncreated` callback, after `resolveAsset()`, replicate `resolveAssetManual()` logic: check if the asset lacks the extracted identifier and open `identifierPromptOpen` if so.
2. Pass `initialNoProvider={true}` (or equivalent) when opening `AssetModal` from the import wizard context.

## Prevention

When adding new resolution paths for fake asset IDs, always check: does this path need to offer the identifier-link prompt? Use a shared helper (`resolveAssetAndMaybePromptIdentifier()`) to avoid divergent paths.

## Impact

Imported assets from BRIM files may not receive their ISIN/ticker identifiers, breaking future provider lookups and price sync for those assets. User must manually add identifiers post-import.

## Source files

| Role | Path |
|------|------|
| ImportWizardModal | `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` |
| AssetModal | `frontend/src/lib/components/assets/AssetModal.svelte` |
