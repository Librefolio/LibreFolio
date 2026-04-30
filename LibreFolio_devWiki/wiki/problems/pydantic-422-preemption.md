---
title: "Pydantic 422 Pre-emption Blocks Service-Layer Validation"
category: problem
status: resolved
date: 2026-04-29
tags: [backend, pydantic, fastapi, validation, transactions, architecture]
related: [decisions/unified-batch-pipeline, features/F-046]
---

# Problem: Pydantic 422 Pre-emption Blocks Service-Layer Validation

## Symptom
When submitting a batch of transactions via `POST /transactions/validate` or `POST /transactions/bulk`, if ANY row had a Pydantic schema error (e.g. missing `asset_id` for BUY), FastAPI returned a raw 422 response BEFORE the handler executed. The service-layer validation (balance checks, access control, pair validation) never ran. Users could only see schema errors, never balance violations in the same response.

## Root Cause
FastAPI deserialises the request body (`List[TXCreateItem]`) in the dependency injection layer before calling the endpoint handler. Pydantic validates all items; if any fail, a `RequestValidationError` is raised and the handler is never invoked. This is by-design FastAPI behaviour, but it creates a problem when the application needs to collect ALL errors (schema + business + balance) in one pass.

## Solution
**Unified Batch Pipeline** (see [[decisions/unified-batch-pipeline]]): Changed request body to `List[dict]` → handler does per-row `model_validate()` in try/except `ValidationError` via `_parse_lenient()`. Valid rows proceed to balance validation while invalid ones are collected as structured issues. Schema errors and balance violations now coexist in one response.

## Prevention
When designing APIs where the service layer needs to see all items regardless of per-item validation errors, accept raw dicts and validate per-item in the handler rather than relying on FastAPI's automatic body deserialization.

## Impact
- ~4h architectural refactor to resolve
- Required migration of all 4 frontend modal consumers
- Led to a net simplification (4 endpoints → 2, −290 lines backend)

