# 🕐 Market Data Scheduler

LibreFolio embeds an automatic background daemon to fetch current prices, historical pricing, and exchange rates without requiring external scheduler systems (like crontab or Celery).

---

## 🏗️ Overview

The scheduler runs as an independent `asyncio.Task` inside the FastAPI lifespan. Every run goes through one function, `run_due_jobs(reason)`, which checks whether the configured sync jobs are due and runs those that are: at startup, at each 60-second tick, when a user comes back after a silence, and on a wake-up, through the scheduled wake-up route, coming next.

```mermaid
graph TD
    Start["🚀 Server Lifespan Startup"] --> FirstWait["⏳ Wait 5s or a nudge"]
    FirstWait -->|startup| Run["⚙️ run_due_jobs(reason)"]
    User["👤 User request after 60s of silence"] -.->|nudge| Wait
    Wake["⏰ Scheduled wake-up route, coming next"] -.->|wake| Run
    Run -->|"return, wake: wait 2s first"| Lock["🔒 Run lock"]
    Lock --> Checks{"🚦 May it run?"}
    Checks -->|"No: disabled, blocked or not_leader"| Report["📋 RunReport"]
    Checks -->|Yes| Jobs["⚡ Each due job in turn: current price, then history sync"]
    Jobs --> Report
    Report -->|"startup, tick, return"| Wait["💤 Wait 60s, a nudge or the shutdown"]
    Wait -->|"60s: tick"| Run
    Wait -->|"nudge: return"| Run
    Wait -->|shutdown| Stop["🛑 Loop stopped"]
```

---

## 🔄 Async Loop Daemon (`scheduler.py`)

The main entry point is `scheduler_loop()` located in `backend/app/services/platform/scheduler/scheduler.py`. Every run of the jobs goes through `run_due_jobs(reason)`, in the same module: the loop calls it, and so will the scheduled wake-up route, coming next.

* **Lifespan Task:** The `scheduler` startup step, the last of `STARTUP_STEPS` in `backend/app/services/platform/app_lifespan.py`, spawns it with `asyncio.create_task()`. On shutdown, the `scheduler` step, the first of `SHUTDOWN_STEPS`, sets the shutdown event and awaits the task before the providers are shut down, a run in progress included; when the shutdown deadline cuts the step, the task is cancelled (see the [lifecycle contract](../architecture/overview.md#lifecycle-contract)).
* **Shutdown Event:** The loop waits on `shutdown_event: asyncio.Event`, its timer and the return nudge at once, so a shutdown ends a wait immediately. The event does not interrupt a run: the loop stops once the run in progress is over, then removes its return listener.
* **Environment Bypass:** Any non-empty value of `LIBREFOLIO_NO_SCHEDULER` keeps the loop from starting and from registering its return listener; a run asked for anyway answers `disabled`. `./dev.py server --no-scheduler` and the gallery screenshot generation set it to `1`.

### ⏰ When a Run Happens {: #run-reasons }

Each run has a reason (`RunReason`), which its log line carries; any other value is refused with `ValueError` before anything happens.

| Reason | When |
|---|---|
| `startup` | The first run, `FIRST_RUN_DELAY_SECONDS` (5 s) after the loop starts, while the application finishes starting. A nudge brings it forward; a shutdown in the meantime ends the loop without it. |
| `tick` | `TICK_SECONDS` (60 s) after the end of the previous run. |
| `return` | At once, when a user's request comes after at least `CATCH_UP_AFTER_SECONDS` (60 s) of silence: see the nudge below. |
| `wake` | The scheduled wake-up route, coming next. |

**The nudge on return.** The loop registers a return listener, `scheduler-catch-up` (`CATCH_UP_LISTENER`), on the process's activity record (`current_activity()`, in `backend/app/services/platform/sleep_wake/activity.py`). The record calls it at the start of a user's request that comes after at least 60 seconds without one; the health and readiness probes do not count. The listener only sets the loop's nudge event, with `loop.call_soon_threadsafe()` so that it works from any thread, and the waiting loop runs `return` at once. The record measures the silence on the wall clock, so the time a machine spends suspended counts; the loop's own timer runs on the monotonic clock, which does not count it, so after a resume the next tick could still be up to a minute away. The nudge is cleared when a run starts: nudges that arrive during a run make one `return` run right after it.

### 🔒 One Run at a Time {: #run-lock }

* **Run lock:** `run_due_jobs()` takes an `asyncio.Lock`, one per event loop, for its checks and its jobs, so two runs of the process never overlap. The second one waits, then loads the state the first one saved, and does not run again what the first one just ran.
* **Busy work:** from its start to its end — the clock settle and the wait for the lock included, whether it returns, raises or is cancelled — the run is busy work on the activity record (`current_activity().busy("scheduler")`), so that the idle suspension (sleep and wake), when it comes, never stops the machine in the middle of a run.
* **Clock settle:** a `return` or `wake` run first waits `CLOCK_SETTLE_SECONDS` (2 s), before the lock and before it reads the time; `startup` and `tick` never wait. After a Fly.io resume the wall clock is corrected within a few hundred milliseconds, and a request may be served before that: the wait lets the due checks read the corrected time.

### 🚦 Inside a Run {: #run-checks }

Under the lock, a run checks four things, in this order. The first one that stops it gives the run's status: no job runs, and the state is not loaded.

1. The scheduler is off, `LIBREFOLIO_NO_SCHEDULER` (`scheduler_disabled()`): `disabled`.
2. The instance is blocked, `LIBREFOLIO_BLOCKED` (`instance_blocked()`): `blocked`. A blocked instance runs no job at all, so its prices and exchange rates are not updated; once the block is lifted (a restart), the first run catches up the history-sync slot missed in the meantime (decision D-Z3-4, and [missed slots](#history-sync)).
3. This process is not the leader worker (`am_i_leader()`, see [Leader Election](#leader-election)): `not_leader`.
4. The `scheduler_enabled` setting is off: `disabled`. The settings are read from the database (`load_scheduler_settings()`) at each run that gets this far.

Otherwise the run loads the state (`load_state()`), reads the wall clock once (`utc_now()`) for both due checks, and takes the jobs of `JOBS` in order, `current_price` then `history_sync`. A job that is not due is reported `not_due`. A due job runs on the loaded state, and the state is saved right after it (`save_state()`). `am_i_leader()`, `load_state()` and `save_state()` block on the process table or on the disk, so they run off the event loop (`asyncio.to_thread()`).

Each job runs in its own `try`:

* A job that raises, or the save after it, is reported `error` with the exception's class name only. The message and the traceback stay in the server log (`Scheduler job failed`, with `job` and `reason`), never in the outcome, which a caller may pass on. The next job still runs. A job that raised before writing its state is still due, so the next run tries it again.
* A cancellation is not caught: it goes through, and the run releases its lock and its busy span. A job it cuts before its state is saved stays due, so after a shutdown the next start runs it again.
* An exception outside the jobs — the settings or the state cannot be read — leaves `run_due_jobs()`: the loop logs it (`Scheduler run failed`) and goes on.

### 📋 The Run Report {: #run-report }

Each run returns a `RunReport(reason, status, started_at, finished_at, jobs)`. It is generic: a future job — notifications, say — is one more entry of `JOBS`, and one more outcome.

* `status`: `ok` when no job ran or every job that ran is `ok`, `error` when every job that ran is `error`, `partial` otherwise; or the check that stopped the run, `disabled`, `blocked` or `not_leader`, with `jobs` empty.
* `started_at` and `finished_at`: in UTC, from the moment the run holds the lock.
* `jobs`: one `JobOutcome(name, status, started_at, duration_s, items_ok, items_err, error)` per job, in order, with `status` `ok`, `partial`, `error` or `not_due`. A job that ran reports what its `JobState` holds after it: status (`ok` when it wrote none), duration, item counts and error. A job that raised reports `error`, its duration, and the exception's class name in `error`; a job not due, only its name and `not_due`.

The loop logs each report, `Scheduler run finished` with the reason, the status and the jobs that ran: at INFO when a job ran, at DEBUG otherwise, so the runs with nothing due stay out of an INFO log.

---

## 👑 Leader Election (`leader.py`) {: #leader-election }

To prevent multiple processes from running duplicate sync jobs when uvicorn runs several workers, only one process — the leader — executes the jobs. `am_i_leader()` decides at every run with `psutil`, without any lock file; it reads the process table, so `run_due_jobs()` calls it off the event loop (`asyncio.to_thread()`):

* Among the running, non-zombie children of the uvicorn master, the process with the **lowest PID** is the leader. If it dies, the next run promotes the new lowest PID.
* Fast paths return `True`: no parent process (e.g. PID 1 in a container), a parent started with `--reload` (one logical worker), a single sibling, or any introspection error — safe because the jobs are idempotent.
* Another worker answers `not_leader` and runs no job. Each worker has its own loop and its own activity record, so a return nudges only the worker that served the request: when that one is not the leader, the catch-up waits for the leader's next tick, within 60 seconds. A lock shared between the processes is in the backlog (Z-11). The Docker image runs a single worker (its `CMD` starts `uvicorn` without `--workers`); `./dev.py server --workers N` starts several.

---

## 💼 Job Definitions (`jobs.py`)

The scheduler runs two types of background synchronization jobs defined in `backend/app/services/platform/scheduler/jobs.py`:

### ⏱️ 1. Current Price Refresh

* **Purpose:** Keeps the current prices of all active assets that have a price provider up-to-date. This updates the local pricing cache, feeding the frontend's [live prices](../frontend/components/features/live-ticker.md#polling) on the Assets list and the asset detail page.
* **Frequency:** Defined by `scheduler_current_price_frequency_minutes` (default: every 10 minutes).
* **Execution:** Calls `AssetSourceManager.get_current_prices_bulk()` (concurrency 3) on every active asset that has a provider assignment.

### 📅 2. History Sync {: #history-sync }

* **Purpose:** Synchronizes historical price series (closing prices) for assets and FX rates.
* **Frequency:** Configured for specific days of the week (e.g., `mon,tue,wed,thu,fri,sat`) and times of the day (e.g., `06:00` and `23:00`), as local wall-clock values in `scheduler_timezone` (see [Configuration Integration](#configuration-integration)).
* **Missed slots:** After a previous run, the most recent slot of a configured day — today or up to `MISSED_SLOT_LOOKBACK_DAYS` (7) days back, in `scheduler_timezone` — is due when it fell after that run (decision D-Z3-1). A week holds every configured day, so the most recent slot is always found: a slot missed while the server was off, asleep or [blocked](#run-checks) runs at the next run — startup, tick, return or wake-up — instead of at the next slot, and several missed slots make one run. Without a previous run (no `last_run_at`, or one that cannot be read), only today's slots count. An always-on instance, which runs every minute, sees no difference.
* **Example:** slots `06:00` and `23:00`, days Monday to Saturday. The history sync last ran on Saturday at 06:00, and the server was off from Saturday 20:00 to Sunday 10:00. When it starts on Sunday, the `startup` run syncs the history, because Saturday's 23:00 slot fell after the last run; with today's slots only, it would have waited for Monday 06:00, Sunday not being a configured day.
* **Execution:** Calls `AssetSourceManager.bulk_refresh_prices()` for the same assets over `[today − horizon, today]` (`scheduler_history_sync_horizon_days`, default: 14 days), then `sync_pairs_bulk()` for every FX conversion route except those with a `MANUAL` step.

Both jobs classify their run as `ok` (every item succeeded, or there was nothing to process), `partial`, or `error` (no item succeeded).

---

## 📜 Execution Logs (`joblog.py`)

Every job run that completes is appended to `logs/scheduler_jobs.jsonl` in the data directory, one JSON object per run:

* **Header fields:** `ts` (ISO timestamp with offset), `job` (`current_price` or `history_sync`), `duration_s`, and `status` (`ok`, `partial` or `error`).
* **`summary`:** `ok`/`err` counts for the current-price refresh; `assets_ok`, `assets_err`, `fx_ok` and `fx_err` for the history sync.
* **Per-item detail:** `items` for the current-price refresh (asset, `ok`, `error`); `assets` and `fx` for the history sync (status, `provider`, `errors`, and `prices_changed`/`events_changed` or `points_changed`).
* **Rotation:** after each append, the file is trimmed to its last 500 entries (`MAX_ENTRIES`).

A job that raises appends no entry: its failure is in the server log, `Scheduler job failed` (see [Inside a Run](#run-checks)).

The last run of each job is also kept in `scheduler_state.json` at the root of the data directory (`state.py`, atomic write-then-rename). The admin UI reads both through admin-only endpoints: `GET /api/v1/settings/scheduler/state` (last runs, `scheduler_timezone`, the server's UTC clock) and `GET /api/v1/settings/scheduler/log?since=ISO` (newest first).

---

## ⚙️ Configuration Integration

Scheduler options are fully integrated into LibreFolio's database-backed Global Settings system. When an administrator modifies settings in the UI:

1. Settings are saved to the `GlobalSetting` table.
2. The frontend triggers a settings reload.
3. The backend scheduler loop loads the settings dynamically on the next loop iteration (every 60 seconds), adapting the polling frequency and execution times instantly without requiring a server restart.

History-sync times and days are stored as local wall-clock values in `scheduler_timezone`. `due_history_sync()` builds each slot in that timezone, on its own local date, and converts it to a UTC instant only when deciding whether it is due, so the slots follow daylight saving time. A slot is due once its instant has passed and the last history run is older than it; [History Sync](#history-sync) says which slots count. A timezone that `zoneinfo` cannot load falls back to UTC (`_scheduler_zoneinfo()`). `zoneinfo` reads the system's time zone database, since the PyPI `tzdata` package is not a dependency: the Docker image installs Debian's `tzdata` and `tzdata-legacy`, which holds old names such as `Asia/Calcutta` and `US/Eastern` (see [Docker Image](../architecture/overview.md#docker-image)). An empty or invalid day list falls back to Monday–Saturday. The backend does not validate these values: the configuration dialog enforces the ranges (1–1440 minutes, 1–365 days, at least one time and one day).

---

## 🔗 Related

* 📡 **[Live Prices](../frontend/components/features/live-ticker.md)** — How the Assets list and the asset detail page poll current prices
* 💰 **[Asset Architecture](assets/architecture.md)** — Pricing provider pipelines and sync steps
* ⚙️ **[Settings System](../architecture/settings.md)** — Dynamic global configuration variables
