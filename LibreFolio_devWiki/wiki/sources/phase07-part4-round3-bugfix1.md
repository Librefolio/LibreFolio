---
title: "Phase 7 Part 4 Round 3 Bugfix 1 — Form/Bulk Modal Redesign"
category: source
source_type: plan
date_ingested: 2026-05-25
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round1-3/plan-phase07-transaction-Part4_Round3_Bugfix1-formModalRedesign.prompt.md
tags: [phase07, transactions, frontend, bugfix, formModal, bulkModal, UX, autofill, unsaved-changes, tags-autocomplete, dual-form]
related: [sources/phase07-part4-round3-staging-rewrite, features/F-048, problems/browser-autofill-numeric-fields]
---

# Source: Phase 7 Part 4 Round 3 Bugfix 1 — Form/Bulk Modal Redesign

## Summary

Five walkthrough rounds (Bugfix 1–5) fixing correctness and UX issues in the new modal system. Key fixes: Pydantic 422 error parsing with `loc+msg`, field reset on type change, FormModal redesign with proper UI components (SimpleSelect→SearchSelect, native date→SingleDatePicker, BrokerSearchSelect), unsaved-changes guard, `+ Add transaction` pivot (A1→A3→A4 hybrid: BulkModal as main entry, FormModal as add-row sub-modal with `commitOnSave=false`), decimal formatting, tags autocomplete, and backend Pydantic enforcement of quantity/cash sign per type (Rules 10+11).

## Key Takeaways

- **Pydantic 422 parsing**: `detail[].msg` + `detail[].loc` extracted; field-specific overrides map `broker_id:greater_than` → "Select a broker"
- **Field reset on type change**: When `draft.type` changes, reset fields based on new type's rules
- **`+ Add` pivot history**: FormModal → BulkModal → hybrid (BulkModal + nested FormModal with `commitOnSave=false`)
- **Unsaved changes guard**: `hasUnsavedChanges()` triggers ConfirmModal on close/escape
- **Tags autocomplete**: client-side aggregation from loaded transactions + drafts
- **formatDecimalForDisplay()**: Trims `6.000000` → `6`; preserves crypto precision
- **Backend Rules 10+11**: quantity sign per type + cash sign per type enforced via Pydantic

## Wiki Pages Updated

- [[features/F-048]] — Bugfix rounds 1–5 tracked
- [[problems/browser-autofill-numeric-fields]] — documented
