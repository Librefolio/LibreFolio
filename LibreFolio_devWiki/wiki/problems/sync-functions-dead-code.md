---
title: "Sync Settings Functions — Dead Code Accumulation"
category: problem
status: resolved
date: 2026-05-10
tags: [backend, settings, dead-code, cleanup]
related_features: []
---

# Problem: Sync Settings Functions — Dead Code Accumulation

## Summary
Three synchronous wrappers for async settings functions accumulated as dead code and were eventually removed:
- `get_session_ttl_hours_sync()`
- `get_max_upload_mb_sync()`
- `is_registration_enabled_sync()`

## Root Cause
These sync wrappers were created alongside their async counterparts in anticipation of sync callers that never materialized. No code outside the functions themselves ever called the sync versions.

## Resolution
Removed all three functions. No callers found. No tests broken.

## Lesson
**Do not create sync wrappers for async functions unless there is an immediate, concrete consumer.** "Might need it later" wrappers become dead code that clutters the codebase and confuses future readers.

## Affected files
- `backend/app/services/global_settings_service.py` (functions removed)
