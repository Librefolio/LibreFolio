---
title: "Phase 0 / 17 — asset data operations: bond categories, distributions CSV, delete result with a transactions link"
category: source
source_type: plan
date_ingested: 2026-10-09
original_path: LibreFolio_developer_journal/Release_2/phases/17_assetDataOperations/plan-phase00AssetDataOperations.prompt.md
tags: [phase0, release2, assets, classification, bonds, csv, delete, transactions]
related:
  - features/F-095
  - features/F-024
  - entities/asset-sources-package
  - problems/sqlite-savepoint-without-write-begins-as-transaction
---

# Source: Phase 0 / 17 — asset data operations

## Summary

One plan (~300 lines), shipped in `e50d66408` (2026-09-10) and polished in `cc57b6a38` (2026-09-11), archived on
2026-10-09. Three small features with strict contracts.

## Key takeaways

- **A1 — bond categories**: the sector taxonomy gained `Corporate Bonds` and `Government Bonds` (with aliases such as
  "corporate", "government"; `backend/app/utils/sector_fin_utils.py`); supranational bonds stay in `Financials`. No
  migration and no reclassification of existing data.
- **A2 — distributions CSV import** (sector and geographic weights, not asset events): columns `name,weight`;
  `weight` is always a percentage 0–100, divided by 100 exactly once — never a guessed 0–1 scale, never rebalanced;
  strict (every row valid or nothing applied); countries match exactly on ISO-2, ISO-3 or the localised name, sectors
  on the canonical key or the localised label, ignoring case and outer spaces — no fuzzy matching. The shared
  `CsvEditor`/`DataImportModal` gained an "identified" mode (next to the dated one), BOM and quoted-field handling and
  an opt-in strict mode (`DistributionDataImportModal.svelte`, opened from `DistributionEditor.svelte`).
- **B3 — a truthful delete result**: [[features/F-095]] (planned since May) shipped — the blocked delete reports the
  global transaction count with a link to the filtered transactions page; one savepoint per item, after a no-op
  write ([[problems/sqlite-savepoint-without-write-begins-as-transaction]]); a failed commit never answers success.
- Off-track: the lane's gates failed with exit 127 because the worktree had no frontend `node_modules` — an
  environment problem, not a product one.

## Residuals

None.

## Wiki pages updated

- [[features/F-095]] — planned → documented, rewritten to the shipped design.

## Source files

| Role | Path |
|------|------|
| Plan | `LibreFolio_developer_journal/Release_2/phases/17_assetDataOperations/plan-phase00AssetDataOperations.prompt.md` |
| Sector taxonomy (bonds) | `backend/app/utils/sector_fin_utils.py` |
| Distributions CSV import | `frontend/src/lib/components/assets/DistributionDataImportModal.svelte` |
| Distribution editor | `frontend/src/lib/components/ui/input/DistributionEditor.svelte` |
| Delete with counts | `backend/app/services/asset_sources/crud.py` |
| User doc (distributions) | `mkdocs_src/docs/user/assets/create-edit.en.md` |
| User doc (delete) | `mkdocs_src/docs/user/assets/index.en.md` |
