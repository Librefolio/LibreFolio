---
title: "Phase 08 — Market Data Scheduler Backend"
category: source
source_type: plan
date_ingested: 2026-06-30
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-08-subplan/plan-phase08Step1-2-backend.prompt.md
tags: [phase08, scheduler, backend, market-data, apscheduler, leader-election, settings, cleanup]
related:
  - entities/market-data-scheduler
  - features/F-052
  - features/F-053
---

# Source: Phase 08 — Market Data Scheduler Backend

## Summary

Phase 08 implemented an embedded market data scheduler daemon in the FastAPI backend. The scheduler runs as a background async loop within the FastAPI lifespan, using a file-lock-based Leader Election algorithm to ensure only one worker process runs jobs in multi-worker deployments. Two job types: current-price refresh (configurable frequency in minutes) and history sync (configurable times + days). The cleanup step removed the `fetch_interval` column from `AssetProviderAssignment` and `FxConversionRoute` tables and replaced 3 placeholder settings with 5 new scheduler-specific settings. A test checkpoint plan covers the full test suite required for Phase 07 Part 5 (Import Wizard) and Phase 08.

## Key Takeaways

- **Scheduler daemon**: Embedded in FastAPI lifespan (`app.on_startup`). Runs on a background async loop, no external process manager needed.
- **Leader Election**: `leader.py` uses `psutil` + file-lock. The worker with the lowest PID wins. Docker PID 1 handled as edge case.
- **Job types**:
  - `current_price`: configurable frequency (1–1440 minutes), default 10 min
  - `history_sync`: configurable times (e.g. "06:00,23:00"), days (e.g. "mon-sat"), rolling horizon (default 14 days)
- **5 new settings**: `scheduler_enabled`, `scheduler_current_price_frequency_minutes`, `scheduler_history_sync_times`, `scheduler_history_sync_days`, `scheduler_history_sync_horizon_days`
- **`fetch_interval` removed**: Column dropped from `AssetProviderAssignment` and `FxConversionRoute`. Per-provider fetch cadence is now globally controlled by scheduler settings.
- **State persistence**: Scheduler state (last run times, next scheduled times) persisted as JSON. Atomic write via `os.replace`.
- **Log rotation**: `scheduler_jobs.jsonl` — JSONL append-only log with ADMIN-only API access (`GET /settings/scheduler/log` + `GET /settings/scheduler/state`).
- **Test checkpoint** (Phase 07-08): 6 backend test files + 3 frontend E2E specs required; Import Wizard backend coverage ~90%, frontend ~60% at checkpoint.

## Wiki Pages Created/Updated

- [[entities/market-data-scheduler]] — new: scheduler daemon entity page

## Source files

| Role | Path |
|------|------|
| Step 1+2 plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-08-subplan/plan-phase08Step1-2-backend.prompt.md` |
| Test checkpoint | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-08-subplan/plan-test-checkpoint-phase07-08.md` |
| Phase 08 README | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-08-subplan/README.md` |
| Scheduler daemon | `backend/app/services/scheduler.py` |
| Leader election | `backend/app/services/scheduler/leader.py` |
| Settings schema | `backend/app/schemas/settings.py` |
| Scheduler API | `backend/app/api/v1/settings.py` |
| mkdocs | `mkdocs_src/docs/developer/backend/scheduler.md` |
