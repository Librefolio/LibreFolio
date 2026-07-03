---
title: "Wiki Audit 2026-06-18 — Transactions, Backend Infra, Assets/BRIM"
category: source
source_type: journal_entry
date_ingested: 2026-06-30
original_path: LibreFolio_developer_journal/RoadmapV4_UI/wiki_audit_2026_06_18/audit_transactions.md
tags: [audit, documentation, mkdocs, transactions, brim, test-runner, workspace-intent, scheduler, gallery]
related:
  - entities/test-runner
  - concepts/workspace-intent-pattern
  - concepts/import-todo-signals
  - entities/market-data-scheduler
  - features/F-012
  - features/F-048
---

# Source: Wiki Audit 2026-06-18

## Summary

A three-area documentation audit conducted on 2026-06-18, covering: (1) Transactions & Events, (2) Backend Architecture & Test Infrastructure, (3) Assets, Brokers & BRIM. The audit found most documentation complete and aligned with code. Two gaps were identified and filled: `WorkspaceIntent` was incorrectly assumed to be a backend multi-tenancy concept (corrected: it is a frontend-only Svelte 5 staging API), and `test_runner.py` was still referenced as a monolithic file (corrected: it is now a modular package at `scripts/test_runner/`). New mkdocs documents were created for: Scheduler daemon, test runner architecture, WorkspaceIntent + ImportTodo in transaction-draft.md, and all 10 broker BRIM import guides. A custom CSS/JS carousel component (`lf-screenshot-carousel`) was built for MkDocs documentation.

## Key Takeaways

### Transactions & Events
- All modal, validation, batch pipeline, context menu, table UX documentation: complete and aligned.
- `split_promote.md` technical doc confirmed complete.
- `transaction-draft.md` updated with WorkspaceIntent + ImportTodo patterns.

### Backend Architecture & Test Infrastructure
- `test_runner` is a **modular package** at `scripts/test_runner/` with 18+ modules and a distributed registry pattern. The file `test_runner.py` no longer exists.
- New doc: `test-walkthrough/runner_architecture.md` — Registry Pattern, suite orchestration, coverage swap-in/swap-out, extension guide.
- Mermaid diagrams updated to ELK layout (`layout: elk`) throughout.
- **WorkspaceIntent clarification**: NOT backend multi-tenancy. It is a Svelte 5 frontend pattern in `TransactionBulkModal.svelte` for bulk staging intentions. Backend multi-tenancy uses JWT + `BrokerUserAccess` filters.

### Assets, Brokers & BRIM
- Scheduler documentation created: `developer/backend/scheduler.md` (daemon lifecycle, leader election, jobs, log rotation).
- All 10 BRIM broker guides extended with step-by-step export instructions and pitfall warnings.
- BRIM architecture doc (`brim/architecture.md`) aligned with v2 parser-only model.
- **New BRIM parser**: `Doubleword.ai` (generic CSV) added as new BRIM provider for imported AI-generated transaction data.
- `lf-screenshot-carousel`: custom CSS/JS carousel for MkDocs documentation pages. Responsive, 3D cover-flow for 3+ items, 180° flip for 2-item carousels. Used in Gallery pages and transaction docs.
- MkDocs Mermaid: ELK layout now standard for all new diagrams.

## Wiki Pages Created/Updated

- [[entities/test-runner]] — new: modular test_runner package structure
- [[concepts/workspace-intent-pattern]] — new: frontend-only WorkspaceIntent clarification
- [[entities/market-data-scheduler]] — cross-reference: scheduler docs confirmed complete
- [[entities/import-wizard-modal]] — cross-reference: BRIM guides complete

## Source files

| Role | Path |
|------|------|
| Transactions audit | `LibreFolio_developer_journal/RoadmapV4_UI/wiki_audit_2026_06_18/audit_transactions.md` |
| Backend infra audit | `LibreFolio_developer_journal/RoadmapV4_UI/wiki_audit_2026_06_18/audit_backend_infra.md` |
| Assets/BRIM audit | `LibreFolio_developer_journal/RoadmapV4_UI/wiki_audit_2026_06_18/audit_assets_brokers_brim.md` |
| test_runner package | `scripts/test_runner/` |
| Runner architecture doc | `mkdocs_src/docs/developer/test-walkthrough/runner_architecture.md` |
| Transaction draft doc | `mkdocs_src/docs/developer/frontend/state/transaction-draft.md` |
| Scheduler doc | `mkdocs_src/docs/developer/backend/scheduler.md` |
| BRIM architecture doc | `mkdocs_src/docs/developer/backend/brim/architecture.md` |
