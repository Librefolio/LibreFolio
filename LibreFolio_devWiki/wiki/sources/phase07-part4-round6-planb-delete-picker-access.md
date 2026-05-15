---
title: "Phase 07 Part 4 Round 6 Plan B + B1 — Delete, Picker, Broker Access"
category: source
source_type: plan
date_ingested: 2026-05-28
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanB_DeletePickerAccess.prompt.md
tags: [phase07, transactions, delete-modal, picker-modal, broker-access, partner-broker-id, role-icon, paired-access]
related:
  - sources/phase07-part4-round6-context-menu-delete
  - decisions/broker-access-min-paired
  - features/F-047
  - features/F-048
  - features/F-010
---

# Source: Phase 07 Part 4 Round 6 Plan B + B1 — Delete, Picker, Broker Access

## Summary
Plan B implements broker access visibility (role icons, access-gated actions), TransactionDeleteModal (3 layouts), and TransactionPickerModal. Plan B1 is a bugfix round fixing 16+ bugs and adding E2E tests (48+ tests across 5 suites). Major backend change: `partner_broker_id` added to `TXReadItem`, `GET /brokers` changed from JOIN to LEFT JOIN to return ALL brokers (with `user_role=null` for inaccessible ones).

## Key Takeaways
- **Broker access visibility**: `brokerRoleHelpers.ts` extracted from BrokerSharingModal with `getRoleIcon()`, `getRoleIconColor()`, `canEditWithRole()`. `BrokerBadge.svelte` extended with `showRole` prop
- **Paired access = min(role_A, role_B)**: `getPairedAccessLevel()` returns `'full'|'viewer'|'none'`; row actions (edit/delete/clone) gated by level. See [[decisions/broker-access-min-paired]]
- **GET /brokers LEFT JOIN**: returns ALL brokers, `user_role=null` for inaccessible. Enables showing broker names in locked placeholders. `brokerStore` exposes `getAccessibleBrokers()` and `getEditableBrokers()`
- **partner_broker_id**: new field in `TXReadItem` — batch lookup via `SELECT id, broker_id WHERE id IN (partner_ids)`, 1 extra query. Enables tooltip and form display for inaccessible partners
- **TransactionDeleteModal**: 3 layouts: A (standalone recap), B (paired dual-column, always delete both, "use Split first" hint), C (paired blocked — delete button hidden, "Contact owner" message)
- **TransactionPickerModal**: reuses TransactionsTable with `pickerMode`, `excludeIds`, auto-partner fetch. Button `[🔍 Search & add]` in BulkModal toolbar
- **BrokerSearchSelect**: now shows only `getEditableBrokers()` for forms (OWNER/EDITOR only)
- **FormModal paired view cases**: 4 cases (a=Owner+Owner, b=Owner+Editor, c=Owner+Viewer, d=Owner+None) with locked placeholder for inaccessible partner
- **Backend enforce**: `_check_paired_access()` guard on update/delete of paired transactions
- **Plan B1 — 16 bugs fixed**: form broker dropdown (Bug 1), paired edit UUID preservation (Bug 14), clone INTEREST qty reset (Bug 6), flat mode paired adjacency (Bug 7), tooltip favicon+SVG role (Bug 8), hidden broker lock display (Bug 13), partner_broker_id backend (Bug 4), BulkModal asset icon fallback (Bug 11), description truncation+tooltip (Bug 12), and more
- **E2E tests**: 5 suites, 48+ tests — `tx-broker-access.spec.ts`, `tx-paired-edit.spec.ts`, `tx-tooltips.spec.ts`, plus updated `transactions-modals.spec.ts` and `transactions-table.spec.ts`
- **Mock data**: 4 asymmetric paired transactions for access testing (OWNER+EDITOR, OWNER+EDITOR, OWNER+VIEWER, OWNER+Hidden)
- **Description column**: new column in main table with truncation, tooltip, URL sync, filterable/sortable

## Wiki Pages Updated
- [[features/F-047]] — description column, broker access, flat mode adjacency
- [[features/F-048]] — broker access gating, PickerModal, DeleteModal layouts
- [[decisions/broker-access-min-paired]] — created

