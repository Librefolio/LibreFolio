---
title: "Phase Final — Bug Vari Report 2026-06-25 (QA Docker)"
category: source
source_type: journal_entry
date_ingested: 2026-06-30
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-final-subplan/bug_vari_report20260625.md
tags: [bugs, qa, docker, broker-icon, plugin-icons, import-wizard, bulk-modal, z-index, race-condition]
related:
  - problems/broker-icon-race-condition
  - problems/import-wizard-identifier-prompt
  - problems/bulk-modal-sticky-z-index
  - entities/import-wizard-modal
  - features/F-048
---

# Source: Phase Final — Bug Report 2026-06-25

## Summary

Static code analysis of the Docker production build conducted on 2026-06-25, identifying 5 categories (A–E) of bugs. No code was modified in this session — pure discovery. Categories A (broker icon race condition), C (import wizard identifier prompt), and D (bulk modal toolbar z-index) are the most impactful and each received a dedicated problem page.

## Key Takeaways

- **Cat-A** (High): `ensurePluginIconsLoaded()` race condition affects 3 pages — `/files`, transactions filter sidebar, dashboard broker filter. The function is called but `getBrokerIconUrl()` may execute synchronously before the Promise resolves.
- **Cat-B** (Medium): `/files` page has no Refresh button. User must reload the entire page to update the file list.
- **Cat-C** (High): `ImportWizardModal.oncreated` path calls `resolveAsset()` but NOT `resolveAssetManual()` — so the identifier prompt never opens for newly created assets. Also: `AssetModal` should open with `providerNoProvider=true` when triggered from import wizard.
- **Cat-D** (Medium): After BRIM import, the BulkModal row-selector toolbar doesn't appear. Root cause: `overflow-y: auto` container clips `position: sticky` / `position: absolute` child elements (toolbar, checkbox, context menu). `isolation: isolate` or `overflow: visible` fix candidate.
- **Cat-E** (Low): Sector emoji absent in Asset Detail chart. Dashboard works correctly because it passes `emoji` field directly; Asset Detail uses `cp.sector_area.distribution` which is `Record<string, number>` only — no emoji field.

## Wiki Pages Created/Updated

- [[problems/broker-icon-race-condition]] — new
- [[problems/import-wizard-identifier-prompt]] — new
- [[problems/bulk-modal-sticky-z-index]] — new

## Source files

| Role | Path |
|------|------|
| Bug report | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-final-subplan/bug_vari_report20260625.md` |
| FilesTable | `frontend/src/lib/components/files/FilesTable.svelte` |
| files page | `frontend/src/routes/(app)/files/+page.svelte` |
| transactions page | `frontend/src/routes/(app)/transactions/+page.svelte` |
| dashboard page | `frontend/src/routes/(app)/dashboard/+page.svelte` |
| ImportWizardModal | `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` |
| TransactionBulkModal | `frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte` |
| brokerHelpers | `frontend/src/lib/utils/brokerHelpers.ts` |
