---
title: "Phase 7 Part 4 Round 3 Bugfix 2 — i18n Validation Errors"
category: source
source_type: plan
date_ingested: 2026-05-25
original_path: LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round3_Bugfix2-i18nValidationErrors.prompt.md
tags: [phase07, transactions, backend, frontend, i18n, validation, pydantic, structured-errors]
related: [sources/phase07-part4-round3-bugfix1, features/F-048, concepts/resolve-validation-message-pattern, decisions/unified-batch-pipeline]
---

# Source: Phase 7 Part 4 Round 3 Bugfix 2 — i18n Validation Errors

## Summary
Replaced free-form English validation error strings with structured error codes + params (~25 codes). Backend sends `code`, `params` (IDs only), `field` on `TXValidationIssue`. Frontend resolves names via stores and translates via `transactions.errors.<code>` keys. Introduced `PydanticCustomError` and the `multipleBusinessRuleErrors` wrapper. This plan also identified the **Pydantic 422 pre-emption problem** (W21–W23) that motivated the Unified Batch Pipeline decision.

## Key Takeaways
- **Structured error codes**: `TXValidationIssue` extended with `code`, `params`, `field` — backward compatible
- **PydanticCustomError**: Replaces `ValueError` in model_validator
- **multipleBusinessRuleErrors**: Pydantic v2 workaround to collect all business rule errors
- **`resolveIssueMessage()`**: code → i18n key → fallback to raw; auto-enriches with store data
- **Pydantic 422 pre-emption**: Schema errors block service-layer validation → led to Unified Batch Pipeline

## Wiki Pages Updated
- [[concepts/resolve-validation-message-pattern]] — new concept page
- [[decisions/unified-batch-pipeline]] — origin story
