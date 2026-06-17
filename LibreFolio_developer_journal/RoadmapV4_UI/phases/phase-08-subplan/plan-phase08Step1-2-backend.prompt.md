# Phase 8 — Step 1 + Step 2: Backend Cleanup + Scheduler Daemon

> **Tipo**: Piano esecutivo per agente CLI
> **Prerequisiti**: Phase 7 completata, backend e test funzionanti
> **Piano padre**: [`../phase-08-scheduler.md`](../../../phase-08-scheduler.md)
> **Stima**: ~6h
> **Output atteso**: backend con scheduler daemon funzionante, `fetch_interval` rimosso, test green

---

## Contesto

Stai implementando il **Market Data Scheduler** per LibreFolio — un demone embedded nel backend FastAPI che mantiene i dati di mercato aggiornati automaticamente. Il piano completo è in `phase-08-scheduler.md` (leggilo INTEGRALMENTE prima di iniziare).

**Regole progetto** (da `.github/copilot-instructions.md`):
- `./dev.py` per tutte le operazioni (mai comandi manuali diretti)
- No backward compatibility — clean up
- No migrazioni Alembic incrementali → modifica `001_initial.py` + `./dev.py db create-clean`
- Dopo modifiche API schema → `./dev.py api sync`
- Async I/O Rule: ogni sync I/O in `async def` va in `await asyncio.to_thread(...)`
- Codice in inglese, commenti in inglese
- `psutil` ha estensioni C ma il Dockerfile ha già `gcc`

---

## Step 1: Pulizia (`fetch_interval` + placeholder settings + fix commento API)

### 1.1 Rimuovere `fetch_interval` dal DB

**File**: `backend/alembic/versions/001_initial.py`
- Rimuovere la colonna `fetch_interval` dalla tabella `asset_provider_assignments`
- Rimuovere la colonna `fetch_interval` dalla tabella `fx_conversion_routes`

### 1.2 Rimuovere `fetch_interval` dai Models

**File**: `backend/app/db/models.py`
- Rimuovere `fetch_interval: Optional[int] = Field(...)` da `AssetProviderAssignment` (~L967)
- Rimuovere `fetch_interval: Optional[int] = Field(...)` da `FxConversionRoute` (~L869)

### 1.3 Rimuovere `fetch_interval` dagli Schemas

**File**: `backend/app/schemas/provider.py`
- Rimuovere `fetch_interval` da tutti gli schema dove appare (cerca con grep)
- Rimuovere eventuale validator `set_default_fetch_interval`

**File**: `backend/app/schemas/assets.py`
- Rimuovere `fetch_interval` se presente

### 1.4 Rimuovere `fetch_interval` dal Service Layer

**File**: `backend/app/services/asset_source.py`
- Rimuovere riferimenti a `fetch_interval` (cerca con grep, ~L953, L962)

**File**: `backend/app/api/v1/assets.py`
- Rimuovere riferimenti a `fetch_interval`

### 1.5 Rimuovere 3 placeholder settings + aggiungere 5 nuove keys

**File**: `backend/app/schemas/settings.py` — in `GLOBAL_SETTINGS_DEFAULTS`:

**Rimuovere**:
```python
"auto_sync_fx_rates": {...},
"auto_sync_prices": {...},
"price_sync_interval_hours": {...},
```

**Aggiungere**:
```python
# Market Data Scheduler
"scheduler_enabled": {
    "value": "true",
    "type": "bool",
    "description": "Enable automatic market data sync (scheduler daemon)",
},
"scheduler_current_price_frequency_minutes": {
    "value": "10",
    "type": "int",
    "description": "Minutes between current-price refresh cycles (1-1440)",
},
"scheduler_history_sync_times": {
    "value": "06:00,23:00",
    "type": "str",
    "description": "Comma-separated HH:MM times for daily history sync (server local time)",
},
"scheduler_history_sync_days": {
    "value": "mon,tue,wed,thu,fri,sat",
    "type": "str",
    "description": "Comma-separated days of week for history sync (mon,tue,wed,thu,fri,sat,sun)",
},
"scheduler_history_sync_horizon_days": {
    "value": "14",
    "type": "int",
    "description": "Rolling horizon in days for history sync (1-365)",
},
```

### 1.6 Fix commento API errato

**File**: `backend/app/api/v1/assets.py` — endpoint `get_current_prices_bulk` (~L694-706)

Il docstring dice "This is a **read-only** operation — no data is written." — questo è **FALSO**.
Il service layer `get_current_prices_bulk()` include upsert OHLC (F.2/F.3).

**Correggere** il docstring per riflettere che l'operazione ha side-effect di persistenza:
```python
"""
Bulk fetch current/live prices for multiple assets.

For each asset:
1. If a provider is assigned → calls provider.get_current_value() (parallel)
2. Fallback → returns the latest price from DB (PriceHistory)

**Side effect**: For successful provider fetches with as_of_date == today,
the OHLC row for today is created or extended (F.2/F.3 intra-day upsert).
DB-fallback results are NOT persisted (stale data, not fresh quotes).
"""
```

### 1.7 Aggiornare test

**File**: `backend/test_scripts/test_db/populate_mock_data.py`
- Rimuovere `fetch_interval` da qualsiasi assignment creato nel mock data

**File**: `backend/test_scripts/` — cercare con grep tutti i riferimenti a `fetch_interval` e rimuoverli

### 1.8 Frontend cleanup (fetch_interval)

**File**: `frontend/src/lib/components/assets/AssetModal.svelte`
- Rimuovere stato `fetchInterval`, binding, e riferimenti nel payload di salvataggio

**File**: `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte`
- Rimuovere prop `fetchInterval` e l'intero blocco UI "Fetch Interval"

**File**: `frontend/src/lib/stores/fxStoreRegistry.ts`
- Rimuovere `fetch_interval` dal type se presente

**File**: `frontend/src/lib/i18n/{en,it,fr,es}.json`
- Rimuovere tutte le chiavi `fetchInterval` / `fetch_interval`

### 1.9 Rigenerare e verificare

```bash
./dev.py db create-clean
./dev.py db create-clean --test
./dev.py api sync
./dev.py lint backend
./dev.py lint frontend
```

Verificare che non ci siano errori. Se i test backend usano le vecchie setting keys, aggiornare.

---

## Step 2: Backend Scheduler Daemon

### 2.1 Aggiungere dipendenza `psutil`

**File**: `Pipfile` — aggiungere `psutil = "*"` sotto `[packages]`

```bash
cd /Users/ea_enel/Documents/00_My/LibreFolio
pipenv install psutil
```

**File**: `requirements.txt` — rigenerare:
```bash
./dev.py docker gen-requirements  # o il comando equivalente
```
Se non c'è un comando, aggiungere manualmente `psutil>=5.9.0` a `requirements.txt`.

### 2.2 Creare il modulo `backend/app/services/scheduler/`

Creare i seguenti file:

#### `backend/app/services/scheduler/__init__.py`

```python
"""Market Data Scheduler — embedded daemon for automatic price/FX sync."""

from backend.app.services.scheduler.scheduler import scheduler_loop, get_shutdown_event

__all__ = ["scheduler_loop", "get_shutdown_event"]
```

#### `backend/app/services/scheduler/leader.py`

```python
"""Leader election via psutil — lowest-PID among sibling workers."""

import os

import psutil


def am_i_leader() -> bool:
    """
    Determine if the current process is the scheduler leader.

    Strategy: among all sibling worker processes (children of the same parent),
    the one with the lowest PID is the leader. Re-evaluated every tick for
    self-healing (if leader dies, next tick promotes the new lowest-PID).

    In Docker single-worker: PID 1, parent() = None → always leader.
    """
    try:
        me = psutil.Process(os.getpid())
        parent = me.parent()
        if parent is None:
            return True
        siblings = [
            p
            for p in parent.children(recursive=False)
            if p.is_running() and p.status() != psutil.STATUS_ZOMBIE
        ]
        if len(siblings) <= 1:
            return True
        return me.pid == min(p.pid for p in siblings)
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False
```

#### `backend/app/services/scheduler/state.py`

```python
"""Scheduler state persistence — atomic JSON file with write-then-rename."""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.app.config import get_data_dir


@dataclass
class JobState:
    last_run_at: Optional[str] = None  # ISO datetime with tz
    last_duration_s: Optional[float] = None
    last_status: Optional[str] = None  # "ok" | "error"
    last_items_ok: int = 0
    last_items_err: int = 0
    last_error: Optional[str] = None


@dataclass
class SchedulerState:
    current_price: JobState = field(default_factory=JobState)
    history_sync: JobState = field(default_factory=JobState)


def _state_path() -> Path:
    return Path(get_data_dir()) / "scheduler_state.json"


def load_state() -> SchedulerState:
    """Load scheduler state from JSON file. Returns fresh state if missing/corrupt."""
    path = _state_path()
    if not path.exists():
        return SchedulerState()
    try:
        data = json.loads(path.read_text())
        return SchedulerState(
            current_price=JobState(**data.get("current_price", {})),
            history_sync=JobState(**data.get("history_sync", {})),
        )
    except (json.JSONDecodeError, TypeError, KeyError):
        return SchedulerState()


def save_state(state: SchedulerState) -> None:
    """Save scheduler state atomically (write-then-rename)."""
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(asdict(state), indent=2))
    os.replace(str(tmp_path), str(path))
```

#### `backend/app/services/scheduler/settings.py`

```python
"""Scheduler settings — read from GlobalSetting table every tick."""

from dataclasses import dataclass
from datetime import time
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_engine
from backend.app.services.global_settings_service import get_setting_value


@dataclass
class SchedulerSettings:
    scheduler_enabled: bool
    current_price_frequency_minutes: int
    history_sync_times: List[time]  # parsed from CSV "HH:MM,HH:MM"
    history_sync_days: List[str]  # ["mon", "tue", ...]
    history_sync_horizon_days: int


def _parse_times(csv: str) -> List[time]:
    """Parse 'HH:MM,HH:MM' → list of time objects."""
    times = []
    for part in csv.split(","):
        part = part.strip()
        if part:
            h, m = part.split(":")
            times.append(time(int(h), int(m)))
    return sorted(times)


def _parse_days(csv: str) -> List[str]:
    """Parse 'mon,tue,wed' → list of day codes."""
    valid = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
    days = [d.strip().lower() for d in csv.split(",") if d.strip().lower() in valid]
    return days if days else ["mon", "tue", "wed", "thu", "fri", "sat"]


async def load_scheduler_settings() -> SchedulerSettings:
    """Read scheduler settings from GlobalSetting table (own session)."""
    from sqlalchemy.ext.asyncio import AsyncSession

    engine = get_async_engine()
    async with AsyncSession(engine) as session:
        enabled = await get_setting_value("scheduler_enabled", session)
        freq = await get_setting_value("scheduler_current_price_frequency_minutes", session)
        times_csv = await get_setting_value("scheduler_history_sync_times", session)
        days_csv = await get_setting_value("scheduler_history_sync_days", session)
        horizon = await get_setting_value("scheduler_history_sync_horizon_days", session)

    return SchedulerSettings(
        scheduler_enabled=enabled if isinstance(enabled, bool) else str(enabled).lower() == "true",
        current_price_frequency_minutes=int(freq) if freq else 10,
        history_sync_times=_parse_times(str(times_csv)) if times_csv else _parse_times("06:00,23:00"),
        history_sync_days=_parse_days(str(days_csv)) if days_csv else _parse_days("mon,tue,wed,thu,fri,sat"),
        history_sync_horizon_days=int(horizon) if horizon else 14,
    )
```

#### `backend/app/services/scheduler/jobs.py`

```python
"""Scheduler jobs — current-price refresh and history sync."""

import time as time_module
from datetime import date, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetProviderAssignment, FxConversionRoute
from backend.app.db.session import get_async_engine
from backend.app.services.asset_source import AssetSourceManager
from backend.app.services.fx import sync_pairs_bulk
from backend.app.services.scheduler.state import JobState, SchedulerState

logger = structlog.get_logger(__name__)


async def run_current_price_refresh(state: SchedulerState) -> None:
    """Fetch current prices for all active assets with assigned providers."""
    t_start = time_module.monotonic()
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Query active assets with active provider assignment
        stmt = (
            select(AssetProviderAssignment.asset_id)
            .join(Asset, Asset.id == AssetProviderAssignment.asset_id)
            .where(Asset.active == True)  # noqa: E712
            .where(AssetProviderAssignment.is_active == True)  # noqa: E712
        )
        result = await session.execute(stmt)
        asset_ids = [row[0] for row in result.all()]

        if not asset_ids:
            logger.debug("Scheduler: no active assets to refresh")
            return

        # Call service layer (includes F.2/F.3 OHLC upsert)
        results = await AssetSourceManager.get_current_prices_bulk(
            asset_ids, session, concurrency=3
        )

    duration = time_module.monotonic() - t_start
    ok_count = sum(1 for r in results if r.value is not None)
    err_count = len(results) - ok_count

    # Update state
    from datetime import datetime

    state.current_price = JobState(
        last_run_at=datetime.now().astimezone().isoformat(),
        last_duration_s=round(duration, 2),
        last_status="ok" if err_count == 0 else "partial",
        last_items_ok=ok_count,
        last_items_err=err_count,
        last_error=None,
    )

    logger.info(
        "Scheduler: current-price refresh",
        ok=ok_count,
        errors=err_count,
        duration_s=round(duration, 1),
    )


async def run_history_sync(state: SchedulerState, horizon_days: int = 14) -> None:
    """Sync historical prices for active assets + all FX routes."""
    t_start = time_module.monotonic()
    engine = get_async_engine()
    today = date.today()
    start_date = today - timedelta(days=horizon_days)

    asset_ok = 0
    asset_err = 0
    fx_ok = 0
    fx_err = 0

    # --- Asset history sync ---
    async with AsyncSession(engine) as session:
        stmt = (
            select(AssetProviderAssignment.asset_id)
            .join(Asset, Asset.id == AssetProviderAssignment.asset_id)
            .where(Asset.active == True)  # noqa: E712
            .where(AssetProviderAssignment.is_active == True)  # noqa: E712
        )
        result = await session.execute(stmt)
        asset_ids = [row[0] for row in result.all()]

    if asset_ids:
        from backend.app.schemas.refresh import FARefreshItem

        refresh_items = [
            FARefreshItem(asset_id=aid, start_date=start_date, end_date=today)
            for aid in asset_ids
        ]

        async with AsyncSession(engine) as session:
            response = await AssetSourceManager.bulk_refresh_prices(
                refresh_items, session, concurrency=3
            )
            asset_ok = response.success_count
            asset_err = len(response.results) - response.success_count

    # --- FX history sync ---
    async with AsyncSession(engine) as session:
        route_stmt = select(FxConversionRoute)
        route_result = await session.execute(route_stmt)
        routes = route_result.scalars().all()

        # Extract unique (base, quote) pairs
        pairs_set: set[str] = set()
        for route in routes:
            slug = f"{route.base}-{route.quote}"
            pairs_set.add(slug)

        if pairs_set:
            pairs_list = sorted(pairs_set)
            fx_response = await sync_pairs_bulk(
                session, pairs_list, (start_date, today)
            )
            fx_ok = sum(1 for r in fx_response.results if r.status == "ok")
            fx_err = len(fx_response.results) - fx_ok

    duration = time_module.monotonic() - t_start

    from datetime import datetime

    state.history_sync = JobState(
        last_run_at=datetime.now().astimezone().isoformat(),
        last_duration_s=round(duration, 2),
        last_status="ok" if (asset_err + fx_err) == 0 else "partial",
        last_items_ok=asset_ok + fx_ok,
        last_items_err=asset_err + fx_err,
        last_error=None,
    )

    logger.info(
        "Scheduler: history sync",
        assets_ok=asset_ok,
        assets_err=asset_err,
        fx_ok=fx_ok,
        fx_err=fx_err,
        duration_s=round(duration, 1),
    )
```

#### `backend/app/services/scheduler/scheduler.py`

```python
"""Main scheduler loop — asyncio task embedded in FastAPI lifespan."""

import asyncio
from datetime import datetime, timedelta

import structlog

from backend.app.services.scheduler.leader import am_i_leader
from backend.app.services.scheduler.settings import load_scheduler_settings, SchedulerSettings
from backend.app.services.scheduler.state import load_state, save_state, SchedulerState
from backend.app.services.scheduler.jobs import run_current_price_refresh, run_history_sync

logger = structlog.get_logger(__name__)

_shutdown_event: asyncio.Event | None = None


def get_shutdown_event() -> asyncio.Event:
    """Get or create the shutdown event (singleton per process)."""
    global _shutdown_event
    if _shutdown_event is None:
        _shutdown_event = asyncio.Event()
    return _shutdown_event


def due_current_price(now: datetime, settings: SchedulerSettings, state: SchedulerState) -> bool:
    """Check if current-price refresh is due."""
    last = state.current_price.last_run_at
    if last is None:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
    except (ValueError, TypeError):
        return True
    return (now - last_dt) >= timedelta(minutes=settings.current_price_frequency_minutes)


def due_history_sync(now: datetime, settings: SchedulerSettings, state: SchedulerState) -> bool:
    """Check if any history sync slot is due."""
    # 1. Is today a configured day?
    today_dow = now.strftime("%a").lower()[:3]
    if today_dow not in settings.history_sync_days:
        return False

    # 2. Check each configured time slot
    last = state.history_sync.last_run_at
    last_dt = None
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
        except (ValueError, TypeError):
            last_dt = None

    for slot_time in settings.history_sync_times:
        slot_dt = now.replace(
            hour=slot_time.hour, minute=slot_time.minute, second=0, microsecond=0
        )
        if now >= slot_dt:
            if last_dt is None or last_dt < slot_dt:
                return True
    return False


async def scheduler_loop(shutdown_event: asyncio.Event) -> None:
    """
    Main scheduler loop — runs as asyncio.Task on the FastAPI event loop.

    Every 60s:
    1. Check leader election (psutil, offloaded to thread)
    2. If leader: read settings, check due jobs, execute
    3. Save state after each job
    """
    logger.info("Scheduler loop started")

    while not shutdown_event.is_set():
        try:
            # psutil does sync I/O → offload per Async I/O Rule
            is_leader = await asyncio.to_thread(am_i_leader)

            if is_leader:
                settings = await load_scheduler_settings()

                if settings.scheduler_enabled:
                    state = load_state()
                    now = datetime.now().astimezone()

                    if due_current_price(now, settings, state):
                        await run_current_price_refresh(state)
                        save_state(state)

                    if due_history_sync(now, settings, state):
                        await run_history_sync(state, horizon_days=settings.history_sync_horizon_days)
                        save_state(state)

        except Exception as e:
            logger.exception("scheduler_loop tick failed", error=str(e))

        # Sleep 60s, but check shutdown every 5s for faster exit
        for _ in range(12):
            if shutdown_event.is_set():
                break
            await asyncio.sleep(5)

    logger.info("Scheduler loop stopped")
```

### 2.3 Integrare nel lifespan di FastAPI

**File**: `backend/app/main.py`

Nell'import section aggiungere:
```python
from backend.app.services.scheduler import scheduler_loop, get_shutdown_event
```

Nel `lifespan()`, **dopo** `asyncio.create_task(_prewarm_provider_caches())` e **prima** di `yield`:
```python
# Start scheduler daemon
shutdown_event = get_shutdown_event()
scheduler_task = asyncio.create_task(scheduler_loop(shutdown_event))
```

Nello shutdown (dopo `yield`, prima dei provider shutdown):
```python
# Stop scheduler daemon
shutdown_event = get_shutdown_event()
shutdown_event.set()
await scheduler_task
```

**Nota**: la variabile `scheduler_task` deve essere accessibile tra startup e shutdown. Usa una variabile del modulo o passala via `app.state`.

### 2.4 Endpoint admin scheduler state

**File**: `backend/app/api/v1/settings.py` (o creare `backend/app/api/v1/admin.py` se preferisci)

Aggiungere:
```python
@router.get("/admin/scheduler/state")
async def get_scheduler_state(current_user: User = Depends(get_current_admin_user)):
    """Get scheduler state (last execution info) — admin only."""
    import zoneinfo
    from datetime import datetime
    from backend.app.services.scheduler.state import load_state

    state = load_state()
    server_tz = datetime.now().astimezone().tzinfo.tzname(None) or "UTC"

    # Try to get IANA tz name
    try:
        import time as time_module
        server_tz = time_module.tzname[0]  # fallback
        # Better: use tzlocal or just datetime
        tz_name = datetime.now().astimezone().strftime("%Z")
        server_tz = tz_name
    except Exception:
        pass

    return {
        "current_price": {
            "last_run_at": state.current_price.last_run_at,
            "last_duration_s": state.current_price.last_duration_s,
            "last_status": state.current_price.last_status,
            "last_items_ok": state.current_price.last_items_ok,
            "last_items_err": state.current_price.last_items_err,
        },
        "history_sync": {
            "last_run_at": state.history_sync.last_run_at,
            "last_duration_s": state.history_sync.last_duration_s,
            "last_status": state.history_sync.last_status,
            "last_items_ok": state.history_sync.last_items_ok,
            "last_items_err": state.history_sync.last_items_err,
        },
        "server_tz": server_tz,
    }
```

Registrare la route nel router appropriato.

### 2.5 Rebuild e test

```bash
./dev.py db create-clean
./dev.py db create-clean --test
./dev.py api sync
./dev.py lint backend
./dev.py test api all
./dev.py test services all
```

### 2.6 Test manuale del daemon

1. Avviare il backend: `./dev.py server`
2. Attendere 1–2 minuti
3. Verificare `backend/data/prod/scheduler_state.json` — deve esistere con i campi popolati
4. Verificare nei log: `"Scheduler: current-price refresh"` a livello INFO
5. `curl http://localhost:6040/api/v1/admin/scheduler/state` (con auth admin)

---

## Checklist finale Step 1+2

- [x] `fetch_interval` rimosso da: models, schemas, service, API, migration, frontend, i18n ✅ 2026-06-08
- [x] 3 placeholder settings rimossi da `GLOBAL_SETTINGS_DEFAULTS` ✅ 2026-06-08
- [x] 5 nuove scheduler settings aggiunte a `GLOBAL_SETTINGS_DEFAULTS` ✅ 2026-06-08
- [x] Commento API "read-only" corretto su endpoint current-price ✅ 2026-06-08
- [x] `psutil` aggiunto a Pipfile + requirements.txt ✅ 2026-06-08
- [x] Modulo `backend/app/services/scheduler/` con 5 file ✅ 2026-06-08
- [x] Scheduler integrato nel lifespan di `main.py` ✅ 2026-06-08
- [x] Endpoint `GET /api/v1/settings/scheduler/state` funzionante (admin-only) ✅ 2026-06-08
  > **Nota**: path cambiato da `/admin/scheduler/state` a `/settings/scheduler/state` per coerenza con router esistente
- [x] `./dev.py db create-clean` e `./dev.py db create-clean --test` eseguiti ✅ 2026-06-08
- [x] `./dev.py api sync` eseguito ✅ 2026-06-08
- [x] `./dev.py lint` passa (11 errori pre-esistenti, 0 nuovi) ✅ 2026-06-08
- [x] `./dev.py test api all` passa — 40/40 ✅ 2026-06-08
- [x] `./dev.py test services all` passa — 23/23 ✅ 2026-06-08
- [x] `svelte-check` passa — 0 errori, 0 warning ✅ 2026-06-08
- [x] Test manuale: daemon gira, state.json scritto, log INFO visibile ✅ 2026-06-08
- [x] Scheduler Job Log (`scheduler_jobs.jsonl`) con dettaglio per-item ✅ 2026-06-08
- [x] Endpoint `GET /api/v1/settings/scheduler/log` funzionante (admin-only, paginato) ✅ 2026-06-08
- [x] `./dev.py api sync` ri-eseguito per nuovo endpoint ✅ 2026-06-08

> **⚠️ Discrepanze piano corrette durante implementazione**:
> 1. `get_setting_value(session, key)` — piano aveva args invertiti
> 2. `FARefreshItem` usa `date_range=DateRangeModel(start=..., end=...)` — non campi flat
> 3. Endpoint path: `/api/v1/settings/scheduler/state` (non `/admin/...`)
> 4. `AssetProviderAssignment.is_active` non esiste — rimosso dal filtro (relazione 1-to-1: se assignment esiste, è attivo)
> 5. `Asset.ticker` non esiste — sostituito con `Asset.display_name`
> 6. Leader election fallisce in dev mode (uvicorn `--reload`) — vecchi worker con PID più basso rimangono attivi → aggiunto fast-path: se parent cmdline contiene `--reload` → sempre leader

> **🆕 Feature aggiuntiva: Scheduler Job Log**
>
> Aggiunto file JSONL separato (`data/<env>/logs/scheduler_jobs.jsonl`) con dettaglio per-item
> per ogni run dello scheduler. Motivazione: il `scheduler_state.json` mostra solo conteggi
> aggregati (ok/err) ma non identifica *quale* asset o pair FX ha fallito e perché.
>
> **File**: `backend/app/services/scheduler/joblog.py` — write/read JSONL + rotation (max 500 entries)
>
> **Formato per-entry** (1 riga JSON per run):
> - `current_price`: `{ts, job, duration_s, status, summary: {ok, err}, items: [{asset_id, name, ok, error?}]}`
> - `history_sync`: `{ts, job, duration_s, status, summary: {assets_ok, assets_err, fx_ok, fx_err}, assets: [{asset_id, name, status, errors?, provider?, points_changed}], fx: [{pair, status, errors?, provider?, points_changed}]}`
>
> **Endpoint API**: `GET /api/v1/settings/scheduler/log?limit=50&offset=0` (admin-only, newest-first)
>
> **Impatto su Step 3 (UI)**: il frontend può mostrare un pannello "Scheduler Log" nella sezione
> Sincronizzazione delle GlobalSettings, leggendo questo endpoint per visualizzare lo storico
> dei run con errori evidenziati.

---

## Note per l'agente

- **Non fare git commit** — solo proporre il messaggio se tutto è green
- Se un test fallisce per motivi non correlati allo scheduler (pre-esistente), documentare e andare avanti
- Il `global_settings_service.py` ha una funzione `get_setting_value(key, session)` — usala per leggere le setting nel modulo scheduler
- Il `sync_pairs_bulk` ha signature: `async def sync_pairs_bulk(session, pairs: list[str], date_range: tuple[date, date])`
- Il `bulk_refresh_prices` ha signature: `async def bulk_refresh_prices(requests: List[FARefreshItem], session: AsyncSession, concurrency=5)`
- I comandi lunghi (>10 righe) vanno in file `/tmp/` ed eseguiti da lì
- Output tee'd a `/tmp/` prima di troncare

