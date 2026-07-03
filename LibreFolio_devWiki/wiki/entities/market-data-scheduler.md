---
title: "Market Data Scheduler"
category: entity
type: service
tags: [backend, scheduler, market-data, async, leader-election, settings, fastapi, lifespan]
related:
  - features/F-052
  - features/F-053
  - concepts/async-io-rule
  - entities/devpy-cli
---

# Market Data Scheduler

## Role

An embedded background daemon that automatically keeps market data (asset prices and FX rates) up-to-date without manual user intervention. Runs within the FastAPI lifespan as an async background task. In multi-worker deployments (gunicorn + uvicorn), uses file-lock-based Leader Election to ensure exactly one worker runs the jobs.

## Location

```
backend/app/services/scheduler.py        # Main daemon loop
backend/app/services/scheduler/
  ├── leader.py                          # Leader election (psutil + file lock)
  ├── state.py                           # State persistence (JSON, atomic write)
  └── jobs.py                            # Job implementations
```

## Key Interfaces

### Settings (5 keys in `GLOBAL_SETTINGS_DEFAULTS`)

| Key | Default | Description |
|-----|---------|-------------|
| `scheduler_enabled` | `true` | Enable/disable the scheduler daemon |
| `scheduler_current_price_frequency_minutes` | `10` | Minutes between current-price refresh cycles (1–1440) |
| `scheduler_history_sync_times` | `"06:00,23:00"` | Comma-separated HH:MM times for daily history sync |
| `scheduler_history_sync_days` | `"mon,tue,wed,thu,fri,sat"` | Days of week for history sync |
| `scheduler_history_sync_horizon_days` | `14` | Rolling horizon (days) for history backfill |

### Admin API Endpoints

```
GET /api/v1/settings/scheduler/state   # Current scheduler state (last/next run times)
GET /api/v1/settings/scheduler/log     # JSONL log viewer (paginated, admin-only)
```

### Job Types

1. **`current_price`** — Calls `AssetSourceManager.get_current_prices()` for all assets with active providers. Runs every `scheduler_current_price_frequency_minutes`.
2. **`history_sync`** — Calls `AssetSourceManager.sync_history()` and `sync_pairs_bulk()` for FX. Runs at specified times on specified days, backfilling the rolling horizon.

## Design Notes

- **No external scheduler**: No Celery, APScheduler, or cron. Daemon is an `asyncio` background task started in `app.on_startup` and cancelled on `app.shutdown`.
- **Leader Election**: `leader.py` scans all uvicorn/gunicorn worker PIDs via `psutil`. Worker with lowest PID becomes leader. Docker PID 1 is handled as special case.
- **Downtime recovery**: State records `last_run_time` per job type. On restart, scheduler checks if any time slots were missed and runs them immediately.
- **Session hygiene**: Each job creates a fresh SQLAlchemy session; session closed after job completes. Prevents session leak across cycles.
- **State persistence**: JSON file at a configurable path. Written atomically via `os.replace` to prevent corruption on crash.
- **Log**: JSONL append-only (`scheduler_jobs.jsonl`). Each line = one job execution with `{job_type, started_at, finished_at, status, error?}`.

## History

| Date | Change |
|------|--------|
| Phase 08 | Initial implementation: daemon + leader election + 2 job types |
| Phase 08 | `fetch_interval` column removed from `AssetProviderAssignment` and `FxConversionRoute` |
| 2026-06-18 | mkdocs documentation written: `developer/backend/scheduler.md` |

## Source files

| Role | Path |
|------|------|
| Main daemon | `backend/app/services/scheduler.py` |
| Leader election | `backend/app/services/scheduler/leader.py` |
| Job implementations | `backend/app/services/scheduler/jobs.py` |
| State persistence | `backend/app/services/scheduler/state.py` |
| Settings schema | `backend/app/schemas/settings.py` |
| Admin API | `backend/app/api/v1/settings.py` |
| mkdocs | `mkdocs_src/docs/developer/backend/scheduler.md` |
