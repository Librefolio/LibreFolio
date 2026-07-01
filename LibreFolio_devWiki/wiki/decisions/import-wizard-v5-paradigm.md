---
title: "Import Wizard v5 paradigm shift (v4→v5)"
category: decision
status: resolved
date: 2026-06-08
tags: [frontend, brim, import-wizard, ux, modal, stepper, multi-file, paradigm]
related:
  - entities/import-wizard-modal
  - concepts/import-todo-signals
  - concepts/workspace-intent-pattern
  - features/F-012
  - features/F-048
---

# Decision: Import Wizard v5 Paradigm Shift (v4→v5)

## Context

The v4 "ImportBridge" design (`plan-phase07Part5-BRIMImportBridge.prompt.md`) assumed:
- Small modal (maxWidth 2xl)
- Single-file per cycle (re-open wizard for each additional broker)
- Mode-switching via breadcrumb navigation
- User picks broker first, then files appear

User testing revealed this was too restrictive for real-world workflows where users accumulate exports from multiple brokers before running an import session.

## Options Considered

1. **v4 (superseded)** — small single-file modal with breadcrumb mode switching.
   - Pro: simpler state machine.
   - Con: serial re-open for multi-broker, no overview of all files at once, poor UX for power users.

2. **v5 (chosen)** — wide multi-file modal with 4-step numbered stepper + back navigation.
   - Pro: entire import session in one flow; all brokers visible simultaneously; upload-first philosophy; clickable back navigation preserves context.
   - Con: larger component, more complex state machine.

## Decision

**v5 chosen**. Key changes from v4:

| v4 Assumption | v5 Reality |
|---------------|------------|
| Small modal (2xl) | **Wide modal** (6xl) — same overlay, more space |
| Single-file per cycle | **Multi-file native** — N files from M brokers in one flow |
| Broker-first → files appear | **Upload-first** (Step 1) + **broker panels** (Step 2) |
| Mode switching via breadcrumb | **Numbered stepper** (1-2-3-4) with click-back navigation |
| Serial re-open for multi-broker | All brokers visible at once in Step 2 |

## Consequences

- `ImportWizardModal` is now a **4-step stateful wizard** with distinct `UploadedFileEntry[]` → `FileSelection[]` → `ParsedFileResult[]` → `MergedTransaction[]` data pipeline.
- Z-layer stack established: z:60 BulkModal / z:70 ImportWizardModal / z:80 sub-modals.
- `ImportTodo` signals introduced for plugin-emitted field blanks.
- `WorkspaceIntent` pattern clarified as frontend-only (not backend multi-tenancy).
- Schwab broker parser added as part of v5 delivery.
- Back-navigation: clicking a previous step number restores state (with invalidation rules).
- Step 1 is **optional** — user can skip if files already exist on broker servers.

## Links

- [[entities/import-wizard-modal]] — entity page
- [[concepts/import-todo-signals]] — plugin field signals
- [[concepts/workspace-intent-pattern]] — frontend staging intent API
- Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte5/plan-phase07Part5-v5-ImportWizard.prompt.md`
- Superseded source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte5/plan-phase07Part5-BRIMImportBridge.prompt.md`

## Source files

| Role | Path |
|------|------|
| v5 plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte5/plan-phase07Part5-v5-ImportWizard.prompt.md` |
| Component | `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` |
| BRIM API | `backend/app/api/v1/brim.py` |
