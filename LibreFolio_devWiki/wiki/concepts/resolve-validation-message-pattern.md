---
title: "Resolve Validation Message Pattern"
category: concept
tags: [frontend, transactions, i18n, validation, error-handling]
related: [features/F-048, concepts/savewithretry-frontend-pattern, decisions/unified-batch-pipeline]
---

# Concept: Resolve Validation Message Pattern

## Definition

Frontend helper `resolveValidationMessage.ts` that transforms backend structured error codes + raw ID params into translated, human-friendly messages by resolving IDs to display names via stores (brokerStore, assetStore) and formatting amounts with `currencyFormat.ts`.

## Where It Applies

- `TransactionFormModal.svelte` — single-row validation/commit error display
- `TransactionBulkModal.svelte` — bulk validation/commit error display (categorised: field errors vs balance errors)

## Resolution Pipeline

```
Backend issue: { code: "balanceCashNegative", params: { brokerId: 3, currency: "USD", balance: "-154.00", date: "2026-04-28" } }
       ↓
1. Enrich params: brokerId 3 → brokerName "Interactive Brokers" (from brokerStore)
2. Format amounts: balance "-154.00" + currency "USD" → formattedBalance "-$154.00 🇺🇸USD"
3. Auto-translate type: params.type "BUY" → $t("transactions.types.BUY") → "Acquisto"
4. Resolve i18n key: $t("transactions.errors.balanceCashNegative", { brokerName, currency, formattedBalance, date })
5. Fallback: if key missing → return issue.error (raw English)
```

## Key Features

- **Field-specific overrides**: `FIELD_ERROR_OVERRIDES` mapping (e.g. `broker_id:greater_than` → `transactions.fieldErrors.selectBroker`)
- **Pydantic built-in mapping**: `PYDANTIC_BUILTIN_KEYS` translates 10 built-in types (`greater_than`, `missing`, `decimal_parsing`, etc.)
- **Field name resolution**: `extractFieldName()` extracts leaf from Pydantic `loc` path → `translateFieldName()` translates via `transactions.fields.*`
- **Multi-error expansion**: recognises `multipleBusinessRuleErrors` wrapper and expands `ctx.errors` into individual issues

## Source files

| Role | Path |
|------|------|
| Resolver helper | `frontend/src/lib/utils/resolveValidationMessage.ts` |
| SaveWithRetry integration | `frontend/src/lib/utils/saveWithRetry.ts` |
| i18n keys | `frontend/src/lib/i18n/{en,it,fr,es}.json` (`transactions.errors.*`, `.pydantic.*`, `.fields.*`, `.fieldErrors.*`) |

