---
title: "Dual-Transaction Form — TransactionFormModal paired mode (R6-B.1–B.3)"
category: decision
status: resolved
date: 2026-05-25
tags: [frontend, transactions, modal, dual-form, fx, transfer, pair, svelte5]
related:
  - decisions/tx-link-uuid-semantics
  - decisions/multi-broker-atomic-tx
  - concepts/always-pair-adjacent
  - features/F-047
  - features/F-046
---

# Decision: Dual-Transaction Form — single modal, two payloads

## Context

TRANSFER and FX_CONVERSION transactions always exist as **pairs** linked by `link_uuid`. Before this work, users had to create each side individually and then use TransferPromoteModal to link them. This was error-prone and unintuitive. The `transactionTypeStore` already exposes `pairFormLayout` (server-driven via `GET /transactions/types`) with three layout modes: `fx`, `transfer_asset`, `transfer_cash`.

The question: how should the form modal handle paired transactions — open two modals, or redesign the single modal to handle both sides?

## Options Considered

1. **Two sequential modals** — create "From" first, then auto-open "To" form pre-filled with shared fields. Pro: simpler code. Con: disjointed UX, easy to abandon halfway, hard to validate cross-side constraints (same currency, same broker error).

2. **Single dual-form modal** — when `pairLayout !== null`, the TransactionFormModal switches from single-form to a stacked From/To layout within one modal. Pro: atomic UX, validates both sides together, shared fields visible at a glance. Con: more complex state management.

## Decision

**Option 2 — Single dual-form modal.** When `getPairFormLayout(draft.type) !== null`, TransactionFormModal enters dual mode with three layout variants:

| Layout | `pairFormLayout` value | Shared fields | Per-side fields |
|--------|----------------------|---------------|-----------------|
| FX Conversion | `fx` | date, broker | cash amount + currency (CompactCashCell × 2) |
| Transfer Asset | `transfer_asset` | date, asset, quantity | broker select × 2 |
| Transfer Cash | `transfer_cash` | date, cash amount + currency | broker select × 2 |

### Key design choices

1. **Da/A detection on edit** — when editing an existing paired transaction, the modal auto-fetches the partner row via `GET /transactions?ids=...` and determines which side is "From" (Da) vs "To" (A) by examining the row values:
   - **FX**: negative `cash_amount` = From, positive = To
   - **Transfer Asset**: negative `quantity` = From, positive = To
   - **Transfer Cash**: type `WITHDRAWAL` = From, type `DEPOSIT` = To

2. **Swap normalisation** — if the clicked row is the "To" side, `draft` and `dualTo` are swapped so "From" is always in the main draft (left/top in the UI). This keeps all `collectDualCreates` logic unidirectional.

3. **Type selector readonly** — in dual mode the transaction type is implicit from the layout (FX_CONVERSION, TRANSFER_IN/OUT), so the type selector is rendered as readonly.

4. **Advanced section hidden** — dual mode hides the collapsible advanced section. `cost_basis_override` is shown inline for `transfer_asset` layout only.

5. **Tags and description shared** — both sides of the pair share tags and description (entered once, applied to both payloads).

6. **Save button gating** — disabled while loading the partner row (edit mode) or when a dual validation error is present (same currency for FX, same broker for transfers).

### State management

- `dualTo: DualDraftTo` — a `$state` object holding the "To" side's per-layout fields (broker, cash, currency, quantity)
- `partnerRow: TXReadItem | null` — the fetched partner row in edit mode (null for create)
- `collectDualCreates()` — builds 2 `TXCreateItem` payloads from `draft` + `dualTo`, linking them with a shared `link_uuid`
- `collectDualUpdates()` — maps `initialRow`/`partnerRow` IDs to the From/To payloads built by `collectDualCreates()`

### Client-side validation (dual-specific)

- **Same currency error** (FX layout) — "From" and "To" can't use the same currency
- **Same broker error** (transfer layouts) — "From" and "To" must use different brokers

## Consequences

- Users can create/edit paired transactions in a single modal action — no more dangling halves
- `collectDualCreates()` always produces exactly 2 items for `POST /transactions/commit`, respecting `link_uuid` semantics ([[decisions/tx-link-uuid-semantics]])
- i18n: 7 new keys added per locale (`from`, `to`, `fxTitle`, `transferAssetTitle`, `transferCashTitle`, `sameCurrencyError`, `sameBrokerError`) in all 4 languages (EN, IT, FR, ES)
- The TransferPromoteModal remains available for linking already-existing unpaired transactions

## Source files

| Role | Path |
|------|------|
| TransactionFormModal (dual-form logic) | `frontend/src/lib/components/transactions/TransactionFormModal.svelte` |
| Transaction type store (pairFormLayout) | `frontend/src/lib/stores/transactionTypeStore.ts` |
| i18n EN | `frontend/src/lib/i18n/en.json` |
| i18n IT | `frontend/src/lib/i18n/it.json` |
| i18n FR | `frontend/src/lib/i18n/fr.json` |
| i18n ES | `frontend/src/lib/i18n/es.json` |
| Plan file | `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md` |

## Links

- [[decisions/tx-link-uuid-semantics]] — link_uuid pairing rules this form implements
- [[decisions/multi-broker-atomic-tx]] — the bulk commit endpoint accepts multi-broker pairs atomically
- [[concepts/always-pair-adjacent]] — once committed, pairs render adjacently in the DataTable

