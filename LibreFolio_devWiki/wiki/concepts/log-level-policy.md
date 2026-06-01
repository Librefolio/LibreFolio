---
title: "Log Level Policy"
category: concept
tags: [backend, logging, structlog, trace, policy]
related: [features/F-076, concepts/async-io-rule]
---

# Concept: Log Level Policy

## Definition

LibreFolio uses a 6-level logging hierarchy with a formal custom TRACE level (5) below DEBUG. The policy is documented in `logging_config.py` header and governs all `logger.*` calls in the backend.

## Level Definitions

| Level | Value | When to use |
|-------|-------|-------------|
| CRITICAL | 50 | Process cannot continue, immediate intervention required |
| ERROR | 40 | Handled error, operation failed or data corrupted |
| WARNING | 30 | Anomaly but recoverable (fallback activated, missing data) |
| INFO | 20 | Significant user operations (sync done, import, login, create) |
| DEBUG | 10 | Operational details (provider used, SQL, intermediate results) |
| TRACE | 5 | High-frequency granular data (single rate, single data point) |

## Practical Rule

- "User did X" → INFO
- "System decided X" → DEBUG
- "Value X for date Y" (repeated N times per operation) → TRACE

## Where It Applies

All `backend/app/` Python code. The TRACE level is registered in both Python stdlib logging and structlog's `LEVEL_TO_NAME` dispatch table.

## Implementation Details

TRACE registration requires three patches in `configure_logging()`:
1. `logging.addLevelName(5, "TRACE")` + `logging.TRACE = 5`
2. `logging.Logger.trace = _trace` method addition
3. `structlog.stdlib.LEVEL_TO_NAME[5] = "trace"` (fixes `KeyError: 5` in structlog 25.5.0)

## Source files

| Role | Path |
|------|------|
| Policy + TRACE registration | `backend/app/logging_config.py` |
| Source plan | `LibreFolio_developer_journal/RoadmapV4_UI/plan-independent-BackendLogAudit.prompt.md` |
