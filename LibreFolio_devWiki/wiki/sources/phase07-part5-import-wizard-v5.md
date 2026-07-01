---
title: "Phase 07 Part 5 — BRIM Import Wizard v5 (Redesign)"
category: source
source_type: plan
date_ingested: 2026-06-30
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte5/plan-phase07Part5-v5-ImportWizard.prompt.md
tags: [phase07, brim, import-wizard, modal, stepper, multi-file, schwab, workspace-intent, import-todo]
related:
  - entities/import-wizard-modal
  - concepts/workspace-intent-pattern
  - concepts/import-todo-signals
  - decisions/import-wizard-v5-paradigm
  - features/F-048
  - features/F-012
---

# Source: Phase 07 Part 5 — BRIM Import Wizard v5

## Summary

This is the complete v5 redesign of the BRIM Import Wizard, superseding the v4 "ImportBridge" approach. The major paradigm shift moved from single-file-per-cycle (small modal, mode-switching breadcrumb) to multi-file native (wide 6xl modal, numbered 4-step stepper). M1 (parse-and-see), M2 (wide modal + asset resolution), M2-W (asset warnings), M2-FT (file table), M3 (step 3 parse UI), M4 (step 4 review/import), and Schwab parser were all completed and verified. Status at ingest: in review pending user confirmation.

## Key Takeaways

- **4-step stepper**: Step 1 (Upload & Assign Broker) → Step 2 (Select Files) → Step 3 (Parse) → Step 4 (Review & Import). Back navigation via clicking previous step number; state preserved when going back (unless data would be invalidated).
- **Wide modal z-layer**: z:60 BulkModal (background) → z:70 ImportWizardModal → z:80 sub-modals (ConfirmModal, AssetModal, FilePreviewModal).
- **Output contract = `TXCreateItem[]`**: The bridge's only output language. Never touches `DraftFields` or `PendingOp` directly. Bridge → `txCreateItemToPendingOp()` → BulkModal grid rows.
- **`ImportTodo` signals**: Plugin-emitted field blanks (safe placeholder value + `BrimFieldTodo` signal) that the user must resolve before import. Strictly wizard-local — never propagate into `PendingOp`.
- **`WorkspaceIntent`**: Frontend Svelte 5 declarative API inside `TransactionBulkModal` for expressing bulk staging intentions (create/edit/clone/delete/import). NOT a backend concept.
- **4-level data model**: `UploadedFileEntry[]` → `FileSelection[]` → `ParsedFileResult[]` → `MergedTransaction[]` (each with `TXCreateItem` + `todos` + `duplicateStatus`).
- **Schwab parser**: New BRIM plugin for Charles Schwab broker CSV exports.
- **Duplicate detection**: `duplicateStatus: 'unique' | 'possible' | 'likely'` based on backend matching against existing transactions.
- **Plugin sign audit 2026-06-08**: Coinbase INTEREST rows — `quantity` forced to 0 (schema-compliant; token quantity discarded). Open question: future `RECEIVE` transaction type for staking rewards.
- **`AssetMapping` resolution**: Fake asset IDs (negative integers emitted by plugins) resolved to real assets via user selection. Identifier prompt offered after manual asset selection.
- **Per-broker plugin override**: Step 2 allows overriding broker's `default_import_plugin` per session.

## Wiki Pages Created/Updated

- [[entities/import-wizard-modal]] — new: major component entity page
- [[concepts/workspace-intent-pattern]] — new: Svelte 5 frontend-only staging intent pattern
- [[concepts/import-todo-signals]] — new: plugin-emitted field todo signals
- [[decisions/import-wizard-v5-paradigm]] — new: v4→v5 paradigm shift rationale

## Source files

| Role | Path |
|------|------|
| Main v5 plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte5/plan-phase07Part5-v5-ImportWizard.prompt.md` |
| v4 plan (superseded) | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte5/plan-phase07Part5-BRIMImportBridge.prompt.md` |
| M1 milestone plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte5/plan-phase07Part5-M1-ParseAndSee.prompt.md` |
| Final UI polish | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte5/05-ui-final-polish.md` |
| Plugin sign audit | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte5/brim-plugin-sign-audit-2026-06-08.md` |
| Import Wizard Modal | `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` |
| BulkModal (recipient) | `frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte` |
| BRIM providers dir | `backend/app/services/brim_providers/` |
| Schwab plugin | `backend/app/services/brim_providers/broker_schwab.py` |
| Coinbase plugin (fixed) | `backend/app/services/brim_providers/broker_coinbase.py` |
| BRIM API | `backend/app/api/v1/brim.py` |
