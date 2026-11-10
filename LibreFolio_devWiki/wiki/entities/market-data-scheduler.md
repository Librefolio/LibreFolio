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

An embedded background daemon that automatically keeps market data (asset prices and FX rates) up-to-date without manual user intervention. Runs within the FastAPI lifespan as an async background task. With several uvicorn workers, each worker has its own loop and a cross-process file lock (`run_lock.py`, `flock` on `<data_dir>/.scheduler.lock`, 1.3 Z-11) lets one run of the jobs happen at a time; the psutil leader election (`leader.py`) is the fallback where `fcntl` is missing (Windows).

## Location

```
backend/app/services/platform/scheduler/scheduler.py  # Main daemon loop
backend/app/services/platform/scheduler/
  ├── run_lock.py                        # One run at a time per data directory (flock), 1.3
  ├── leader.py                          # Leader election (psutil, lowest PID) — fallback without fcntl
  ├── settings.py                        # SchedulerSettings, read from GlobalSetting every tick
  ├── state.py                           # State persistence (JSON, atomic write)
  ├── joblog.py                          # JSONL job log with rotation
  └── jobs.py                            # Job implementations
```

## Key Interfaces

### Settings (6 keys in `GLOBAL_SETTINGS_DEFAULTS`, `backend/app/schemas/settings.py`)

| Key | Default | Description |
|-----|---------|-------------|
| `scheduler_enabled` | `true` | Enable/disable the scheduler daemon |
| `scheduler_current_price_frequency_minutes` | `10` | Minutes between current-price refresh cycles (1–1440) |
| `scheduler_history_sync_times` | `"06:00,23:00"` | Comma-separated HH:MM times for daily history sync |
| `scheduler_history_sync_days` | `"mon,tue,wed,thu,fri,sat"` | Days of week for history sync |
| `scheduler_history_sync_horizon_days` | `14` | Rolling horizon (days) for history backfill (1–365) |
| `scheduler_timezone` | `UTC` (`LIBREFOLIO_DEFAULT_TIMEZONE` until an administrator saves it) | IANA timezone of the history-sync slots |

### Admin API Endpoints

```
GET /api/v1/settings/scheduler/state   # Current scheduler state (last/next run times)
GET /api/v1/settings/scheduler/log     # JSONL log viewer (paginated, admin-only)
```

### Job Types

1. **`current_price`** (`run_current_price_refresh()`) — Calls `AssetSourceManager.get_current_prices_bulk()` for all assets with active providers. Runs every `scheduler_current_price_frequency_minutes`.
2. **`history_sync`** (`run_history_sync()`) — Calls `AssetSourceManager.bulk_refresh_prices()` for assets and `sync_pairs_bulk()` for FX. Runs at specified times on specified days; each item starts at the horizon, or at the day after its last saved value when that is older — never more than `HISTORY_CATCH_UP_MAX_DAYS` back (`_history_sync_start()`, 1.3 Z-5) — so a server that was off longer than the horizon fills its gap.

## Design Notes

- **No external scheduler**: No Celery, APScheduler, or cron. Daemon is an `asyncio` background task (`scheduler_loop`) started and stopped by the app lifespan (`backend/app/services/platform/app_lifespan.py`).
- **Leader Election**: `leader.py` (`am_i_leader()`) scans the uvicorn sibling worker PIDs via `psutil`; the lowest PID leads, re-evaluated every tick. PID 1 / no parent (Docker) and `--reload` are fast-paths. Since 1.3 it is the fallback of `run_lock.py` only.
- **Downtime recovery**: State records `last_run_at` (and duration, status, item counts) per job type (`JobState`). On restart, scheduler checks if any time slots were missed and runs them immediately.
- **Session hygiene**: Each job creates a fresh SQLAlchemy session; session closed after job completes. Prevents session leak across cycles.
- **State persistence**: JSON file at a configurable path. Written atomically via `os.replace` to prevent corruption on crash.
- **Log**: JSONL (`<data_dir>/logs/scheduler_jobs.jsonl`, rotated). Each line = one job run with `{ts, job, duration_s, status, summary: {ok, err, deferred}, retry_at, items}`.
- 2026-11-07 lint: settings, jobs, lifespan, lock and log realigned with `services/platform/scheduler/`.

## History

| Date | Change |
|------|--------|
| Phase 08 | Initial implementation: daemon + leader election + 2 job types |
| Phase 08 | `fetch_interval` column removed from `AssetProviderAssignment` and `FxConversionRoute` |
| 2026-06-18 | mkdocs documentation written: `developer/backend/scheduler.md` |

## Source files

| Role | Path |
|------|------|
| Main daemon | `backend/app/services/platform/scheduler/scheduler.py` |
| Run lock (1.3) | `backend/app/services/platform/scheduler/run_lock.py` |
| Leader election | `backend/app/services/platform/scheduler/leader.py` |
| Settings read | `backend/app/services/platform/scheduler/settings.py` |
| Job log | `backend/app/services/platform/scheduler/joblog.py` |
| Lifespan (start/stop) | `backend/app/services/platform/app_lifespan.py` |
| Job implementations | `backend/app/services/platform/scheduler/jobs.py` |
| State persistence | `backend/app/services/platform/scheduler/state.py` |
| Settings schema | `backend/app/schemas/settings.py` |
| Admin API | `backend/app/api/v1/settings.py` |
| mkdocs | `mkdocs_src/docs/developer/backend/scheduler.md` |
