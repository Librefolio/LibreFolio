---
title: "Browser autofill on numeric transaction fields"
category: problem
status: resolved
date: 2026-04-28
tags: [frontend, ux, browser, autofill, chrome, transactions]
related: [features/F-048]
---

# Problem: Browser Autofill on Numeric Transaction Fields

## Symptom

Chrome proposed "save identity data" suggestions on decimal values in quantity/cash inputs. The browser treated `<input type="text">` fields containing numbers like `5` or `1050.00` as potential address/identity fields.

## Root Cause

Inputs had predictable `name` attributes and no `autocomplete` attribute, causing Chrome's autofill heuristics to match them as identity-related fields.

## Solution

Combined approach on all numeric inputs (quantity, cash amount):
- `autocomplete="off"` — disables Chrome autofill
- `name="qty-{randomId}"` — randomised name prevents pattern matching across page loads
- Kept `type="text" inputmode="decimal"` — avoids locale issues with `type="number"` while showing numeric soft keyboard on mobile

## Prevention

All new numeric inputs in editable cells and form modals should follow this pattern. Documented in the `CompactCashCell.svelte` component as the reference implementation.

## Source files

| Role | Path |
|------|------|
| Reference component | `frontend/src/lib/components/ui/CompactCashCell.svelte` |
| FormModal application | `frontend/src/lib/components/transactions/TransactionFormModal.svelte` |
| BulkModal application | `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` |

