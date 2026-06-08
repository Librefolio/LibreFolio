# Phase 8 — Market Data Scheduler

> **Status**: ✅ Completata (2026-06-08). Step 1+2 (backend) + Step 3 (UI) tutti implementati.
> **Giorni stimati**: 2–3
> **Origine**: side-quest emersa durante Phase 7 dalla convergenza dei sistemi FX (Phase 5) e Asset (Phase 6). Con entrambi i pipeline di sync collaudati e stabili, ha senso automatizzare l'esecuzione periodica invece di lasciarla manuale.
> **Ultimo aggiornamento**: 2026-06-08 — Tutti gli step completati, testati manualmente e verificati.

---

## 🎯 Obiettivo

Introdurre un **demone embedded nel backend FastAPI** che mantiene i dati di mercato aggiornati senza intervento utente:

1. **Current-price refresh** a frequenza configurabile (default 10 min) — include upsert OHLC intra-day (F.2/F.3, già nel service layer).
2. **History sync** con scheduling granulare: frequenza configurabile (N volte al giorno) + selezione giorni della settimana (default: Lun–Ven + Sab mattina) con orizzonte rolling (default 14 gg indietro, `end_date = today`).

Parametri configurabili runtime da un amministratore tramite `GlobalSettingsTab.svelte`, persistiti in `GlobalSetting`, riletti dal demone ad ogni tick senza restart.

In aggiunta: **rimozione di `fetch_interval` per-provider** su `AssetProviderAssignment` e `FxConversionRoute`. Con uno scheduler globale il campo è ridondante, fragile e complica la UX del form provider.

**Pulizia**: rimozione dei 3 placeholder settings mai utilizzati (`auto_sync_fx_rates`, `auto_sync_prices`, `price_sync_interval_hours`) da `GLOBAL_SETTINGS_DEFAULTS`, sostituiti dalle nuove keys.

---

## 🧱 Decisioni architetturali

| Tema | Scelta | Motivazione |
|------|--------|-------------|
| **Tech demone** | Loop `asyncio` nativo, tick 1 min, rilegge settings ogni tick | Zero dipendenze, 0 accoppiamento settings↔scheduler, setting update entra in vigore entro 60s |
| **APScheduler** | ❌ scartato | Overhead ingiustificato per 2 job, richiederebbe `reschedule_job()` su ogni update settings |
| **Multi-worker** | `psutil` + elezione **lowest-PID** rivalutata ad ogni tick | Cross-platform (Win/macOS/Linux), self-healing, no stale lock, promozione automatica <60s se il leader crasha. **Nota**: lo scheduler è un `asyncio.Task` (non un thread) sul medesimo event loop del worker — ogni worker uvicorn ne lancia uno, ma solo il lowest-PID esegue i job |
| **`am_i_leader()` e async I/O rule** | Chiamato direttamente (sync, <1ms) | `psutil` fa sync I/O ma è <1ms. `to_thread` rimosso perché aggiungeva complessità senza beneficio. In dev mode (`--reload`): detect parent cmdline → always leader (fix PID stale con watchfiles) |
| **`AssetProviderAssignment.is_active`** | ❌ non esiste | Relazione 1-to-1: se l'assignment esiste, l'asset ha un provider attivo. Rimosso il filtro `.where(is_active == True)` dal piano originale |
| **Session management scheduler** | Sessione fresca autonoma per ogni job | Il scheduler non è un request handler → non ha la sessione FastAPI DI. Ogni job crea la propria sessione via `AsyncSession(get_async_engine())`, pattern identico a `_initialize_global_settings()` in `main.py`. Sessione **mai riusata** tra job consecutivi per evitare stale state post-rollback |
| **Mutex globale DB** | ❌ non necessario | DB serializza le write; doppia write (edge case) innocua — i service layer sono idempotenti (upsert) |
| **Stato persistente** | JSON file `backend/data/<env>/scheduler_state.json` scritto atomicamente (write-then-rename) | Sopravvive al restart; zero migrazioni; basta per "quando è stata l'ultima run?" |
| **Nuova tabella `SyncJobRun`** | ❌ scartato | Retention + peso DB non giustificati per info riassuntiva già nel JSON |
| **Chiamate sync** | Il demone invoca **direttamente i service layer esistenti** (`AssetSourceManager.get_current_prices_bulk`, `AssetSourceManager.bulk_refresh_prices`, `sync_pairs_bulk`) | Nessun HTTP interno, nessuna reimplementazione, riusa i test già green |
| **Nuovi endpoint** | **Due**: `GET /api/v1/settings/scheduler/state` (read-only, admin-gated) + `GET /api/v1/settings/scheduler/log` (JSONL job log, paginato, admin-gated) | State serve al `GlobalSettingsTab` per l'hint "Last execution"; log serve per dettaglio per-item (quale asset/pair ha fallito e perché) |
| **Job Log** | JSONL file `data/<env>/logs/scheduler_jobs.jsonl` con rotation a 500 entries | Dettaglio per-item per ogni run (asset name, status, errors). Il `scheduler_state.json` resta per i conteggi aggregati. Il JSONL serve alla UI per mostrare lo storico runs con errori evidenziati |
| **Timezone** | Ora locale del server (stessa del container Docker) | Per un self-hosted singolo utente è la semantica più naturale; documentato nell'hint UI |
| **Nuova dipendenza** | `psutil` | Cross-platform process introspection; ha estensioni C (`.so`), ma il Dockerfile ha già `gcc`; disponibile via `pip install` su tutte le piattaforme |
| **Current-price upsert** | ✅ confermato nel service layer | `get_current_prices_bulk()` in `AssetSourceManager` (L2823–2910) include upsert OHLC F.2/F.3. Il commento "read-only" nell'API endpoint `assets.py:706` è **errato** e va corretto |
| **History end_date** | `today` (non `today - 1`) | Dati parziali intra-day accettabili: si correggono al ciclo successivo. Hint UI per suggerire orario post-chiusura mercati |
| **Concorrenza scheduler+utente** | Scenario considerato, non grave | Il sistema di cache in-process (`_asset_current_cache` TTL 2min, `_asset_history_cache` TTL 15min) protegge nativamente: se lo scheduler gira e l'utente clicca refresh subito dopo → cache HIT, nessuna chiamata provider. Il doppio fetch reale avviene solo se le chiamate partono nello stesso millisecondo. I service sono idempotenti (upsert). Lo scheduler usa `concurrency=3` (conservativo vs default 5) |
| **FX pairs filtering** | Tutte le route configurate | `FxConversionRoute` non ha campo `active`. Le route configurate sono tipicamente poche (<20). Se un utente non vuole più una pair, la rimuove |
| **Logging** | `DEBUG` per tick/dettagli, `INFO` solo 1 riga summary per job eseguito | Nessun log per tick idle — solo quando il daemon esegue, leader election cambia, o eccezione |
| **Placeholder settings** | 🗑️ rimossi | `auto_sync_fx_rates`, `auto_sync_prices`, `price_sync_interval_hours` — mai chiamati, erano placeholder. Sostituiti dalle nuove scheduler keys |

---

## 🗄️ Nuove `GlobalSetting` keys

| Key | Type | Default | Range / Format | Descrizione |
|-----|------|---------|----------------|-------------|
| `scheduler_enabled` | bool | `true` | — | Master toggle; se `false` il loop gira ma non esegue alcun job |
| `scheduler_current_price_frequency_minutes` | int | `10` | 1–1440 | Interval (minuti) tra due refresh del current-price |
| `scheduler_history_sync_times` | string | `"06:00,23:00"` | CSV di `HH:MM` server time | Orari giornalieri del sync storico FX + assets (es. `"06:00,12:00,18:00,23:00"` per 4 run/giorno) |
| `scheduler_history_sync_days` | string | `"mon,tue,wed,thu,fri,sat"` | CSV di `mon,tue,wed,thu,fri,sat,sun` | Giorni della settimana in cui il sync storico è attivo |
| `scheduler_history_sync_horizon_days` | int | `14` | 1–365 | Finestra rolling backward per il sync storico |

### Scheduling granulare del history sync

Il vecchio modello "1 orario fisso al giorno" è sostituito da una configurazione più flessibile:

- **Orari multipli**: l'admin può configurare 1–N orari giornalieri (default: 06:00 e 23:00 → sync mattutino pre-apertura + serale post-chiusura europei).
- **Selezione giorni**: l'admin sceglie su quali giorni eseguire (default: Lun–Sab). Tipici scenari:
  - `mon,tue,wed,thu,fri` → solo giorni lavorativi
  - `mon,tue,wed,thu,fri,sat` → + sabato mattina per mercati asiatici
  - `mon,tue,wed,thu,fri,sat,sun` → crypto (24/7)
- **Festivi**: esclusi per ora. Se un sync cade in un giorno festivo, il provider semplicemente non restituisce nuovi dati → noop, nessun danno.

### `due_history_sync` aggiornato

```python
def due_history_sync(now: datetime, settings: SchedulerSettings, state: SchedulerState) -> bool:
    """Check if any history sync slot is due."""
    # 1. Is today a configured day?
    today_dow = now.strftime("%a").lower()[:3]  # "mon", "tue", ...
    if today_dow not in settings.history_sync_days:
        return False
    
    # 2. Parse configured times
    sync_times = sorted(settings.history_sync_times)  # ["06:00", "23:00"]
    
    # 3. Find the latest slot that is <= now
    last_run = state.history_sync.last_run_at
    for slot_time in sync_times:
        slot_dt = now.replace(hour=slot_time.hour, minute=slot_time.minute, second=0, microsecond=0)
        if now >= slot_dt:
            # This slot is due if never run OR last run was before this slot
            if last_run is None or last_run < slot_dt:
                return True
    return False
```

### ⚠️ Limitazione nota: downtime che attraversa la mezzanotte

Se il server è offline durante uno slot (es. `23:00`) e riparte dopo mezzanotte, lo slot perso
**non viene recuperato** — il sistema attende il prossimo slot configurato del giorno corrente.
Con il default `"06:00,23:00"` il massimo ritardo è ~7h. Con `horizon_days=14` il gap storico
si colma comunque al prossimo sync. **Scelta deliberata**: la complessità di un catch-up
retroattivo non è giustificata dal rischio (il rolling horizon copre già il recupero).

### 🔁 Interazione con `Asset.active`

**Ancoraggio** (side-note da I-bis #17, Phase 7 — 2026-04-22): il campo
`Asset.active` oggi è usato solo come filtro di lista. Lo scheduler è il
consumer naturale per dare semantica "archiviato" al flag:

- **Current-price refresh**: il demone itera solo su `Asset.active == True` —
  asset inattivi non vengono pollati.
- **Daily history sync**: stessa logica — inattivi esclusi dal rolling
  horizon.
- **FX**: nessun filtro `active` — `FxConversionRoute` non ha il campo.
  Tutte le route configurate vengono sincronizzate. Se l'utente non vuole più
  una pair, la rimuove dalla configurazione.
- **Implementazione**: aggiungere `where(Asset.active == True)` nelle query
  che il demone esegue su `AssetProviderAssignment` (JOIN con `Asset`).

#### Regole definitive per il consumer `Asset.active` (2026-04-22, post-test utente)

| Consumer | Comportamento su `active=False` | Rationale |
|----------|--------------------------------|-----------|
| **Scheduler automatico (questo piano)** — current-price refresh + history sync | **Skip**: l'asset è escluso dal loop del demone (filtro `Asset.active == True` in join con `AssetProviderAssignment`). | Asset archiviati non devono consumare quota provider né inquinare i log periodici. |
| **Sync manuale frontend** — `POST /prices/sync`, `POST /events/sync`, pulsante "Recalculate" | **Consentito**: l'azione esplicita dell'utente bypassa il flag. | Use-case: riattivazione temporanea per refresh puntuale di un asset archiviato. |
| **Dashboard / Portfolio breakdown** (Phase 9) | **Nasconde**: le query di aggregazione filtrano `asset.active == True`. | Gli inattivi non devono contribuire alla vista "live" del patrimonio. |
| **Lista assets** `/assets` | **Tri-state UI**: toggle `[Active] [Inactive]` indipendenti (già implementato in Phase 7). | |

#### 🆕 UI: Toggle Active/Inactive nell'AssetModal + indicatore in pagina detail

Attualmente `Asset.active` è nel DB ma **non è modificabile dall'utente** via UI.

**Dove metterlo**: dentro la modale **"Modifica Asset"** (`AssetModal.svelte`), nella sezione
"Ulteriori Info", come toggle switch. Sfrutta il flusso di salvataggio già configurato
(stesso endpoint `PATCH /api/v1/assets/bulk`). Lo stato visivo (pallina 🟢/🔴) va nel
titolo della pagina detail, come già avviene nella lista globale degli asset.

```
┌─── ✏️ Modifica Asset ─────────────────────────────────── [✕] ───┐
│                                                                   │
│  Nome: [ Apple Inc.                    ]                          │
│  Tipo: [ ETF ▼ ]    Valuta: [ USD ▼ ]                            │
│                                                                   │
│  ━━━ Ulteriori Info ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│                                                                   │
│  Stato:  ● Attivo  ═══╗                                          │
│                   ═══╝                                            │
│  hint: "Gli asset inattivi non vengono sincronizzati              │
│         automaticamente dallo scheduler"                          │
│                                                                   │
│  ... altri campi ...                                              │
│                                                                   │
│  ───────────────────────────────────────────────────────────────  │
│  [ Annulla ]                                    [ 💾 Salva ]      │
└───────────────────────────────────────────────────────────────────┘
```

**Indicatore visivo nella pagina detail** (`/assets/[id]`): nel titolo/header della pagina,
pallina colorata accanto al nome (stesso pattern della lista globale assets):

```
  🟢 Apple Inc.  [ETF] [USD 🇺🇸]  [yfinance]    [✏️ Edit] [🔄 Sync]
```

- `🟢` = attivo (default) — dot `bg-green-500`
- `🔴` = inattivo/archiviato — dot `bg-red-400`

Quando **inattivo**, banner informativo sotto l'header:

```
  ⚠️ 📦 Asset archiviato — non sincronizzato dallo scheduler.
       Il sync manuale via pulsante resta disponibile.
```

- **Patch API**: il toggle nella AssetModal usa lo stesso `PATCH /api/v1/assets/bulk` già cablato nel flusso "Salva"
- **data-testid**: `asset-active-toggle` (nella modale), `asset-status-dot` (nell'header detail), `asset-archived-banner`
- **i18n keys**: `assets.edit.status.label`, `assets.edit.status.hint`, `assets.detail.archivedBanner`
- **Scope**: Step 3 (UI)

---

**Implementazione scheduler (Step 2 di questo piano)**:

```python
# backend/app/services/scheduler/jobs.py (pseudo)
stmt = (
    select(AssetProviderAssignment)
    .join(Asset, Asset.id == AssetProviderAssignment.asset_id)
    .where(Asset.active == True)  # noqa: E712 — SQLAlchemy expression
    .where(AssetProviderAssignment.is_active == True)
)
```

Initialization via `initialize_global_settings()` (stesso pattern di `session_ttl_hours`, `max_file_upload_mb`).

---

## 🧩 File JSON di stato

```
backend/data/<env>/scheduler_state.json
```

```json
{
  "current_price": {
    "last_run_at": "2026-04-20T14:20:00+02:00",
    "last_duration_s": 3.4,
    "last_status": "ok",
    "last_items_ok": 42,
    "last_items_err": 0,
    "last_error": null
  },
  "history_sync": {
    "last_run_at": "2026-04-19T23:00:15+02:00",
    "last_duration_s": 127.8,
    "last_status": "ok",
    "last_items_ok": 87,
    "last_items_err": 2,
    "last_error": null
  }
}
```

- **Write atomico**: `write to <name>.tmp → os.replace(<name>.tmp, <name>)` — atomico sia su POSIX che Windows (Python 3.3+).
- **Read resiliente**: se il file manca o è corrotto → stato iniziale tutto null, il demone esegue subito.
- **Crash mid-job**: se il leader crasha durante un job, lo state non è stato scritto → il nuovo leader (elected al prossimo tick) ri-esegue. Innocuo: i service layer sono idempotenti (upsert).

---

## 🔁 Logica del loop

```python
async def scheduler_loop(shutdown_event: asyncio.Event):
    await asyncio.sleep(5)  # initial delay — let app fully initialize
    while not shutdown_event.is_set():
        try:
            is_leader = am_i_leader()  # <1ms, sync OK (no to_thread needed)
            if is_leader:
                settings = await load_scheduler_settings()  # reads GlobalSetting (own session)
                if settings.scheduler_enabled:
                    state = load_state_json()
                    now = datetime.now().astimezone()
                    if due_current_price(now, settings, state):
                        await run_current_price_refresh(state)  # creates own session
                        save_state_json(state)
                    if due_history_sync(now, settings, state):
                        await run_history_sync(state)  # creates own session
                        save_state_json(state)
        except Exception as e:
            logger.exception("scheduler_loop tick failed: %s", e)
        # Sleep 60s in 5s increments for fast shutdown
        for _ in range(12):
            if shutdown_event.is_set():
                break
            await asyncio.sleep(5)
```

### Leader election (`psutil`)

```python
def am_i_leader() -> bool:
    try:
        me = psutil.Process(os.getpid())
        parent = me.parent()
        if parent is None:
            return True
        siblings = [
            p for p in parent.children(recursive=False)
            if p.is_running() and p.status() != psutil.STATUS_ZOMBIE
        ]
        if len(siblings) <= 1:
            return True
        return me.pid == min(p.pid for p in siblings)
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False
```

### Due-check helpers

- `due_current_price(now, s, st)`: `True` se `st.current_price.last_run_at is None` **oppure** `now - last >= timedelta(minutes=s.current_price_frequency_minutes)`.
- `due_history_sync(now, s, st)`: vedi [sezione scheduling granulare](#scheduling-granulare-del-history-sync) — controlla giorno della settimana + slot orari multipli.

### Integrazione con FastAPI

- `lifespan()` in `main.py`: `asyncio.create_task(scheduler_loop(shutdown_event))` al startup; `shutdown_event.set()` + `await task` al shutdown.
- Il loop non blocca il server: gira in parallelo sul medesimo event loop. `am_i_leader()` è sync ma <1ms (no `to_thread` necessario). `sleep(5)` × 12 = 60s tra tick, con check shutdown ogni 5s per exit rapido.
- In Docker single-worker: PID 1, `parent() = None` → `am_i_leader() = True` immediatamente. Con `--workers N`: il parent è il master uvicorn, i children competono per lowest-PID.
- In dev mode (`--reload`): leader election bypassata — se il parent ha `--reload` nel cmdline → always leader (fix per PID stale con watchfiles reloader).

---

## 🔧 Pre-requisiti: Fix commento API errato

Il commento nell'endpoint `GET /assets/prices/current` (`assets.py:706`) dice "read-only operation — no data is written". Questo è **falso**: il service layer `get_current_prices_bulk()` include upsert OHLC F.2/F.3 (L2823–2910 in `asset_source.py`). Il docstring del service layer è corretto. **Fix**: aggiornare il commento API durante Step 1.

---

## 🔥 Rimozione `fetch_interval`

### Backend
1. **DB**: rimuovere campo da `AssetProviderAssignment` e `FxConversionRoute` in `alembic/versions/001_initial.py` (convenzione progetto: no migrazioni incrementali → `./dev.py db create-clean`).
2. **Models**: rimuovere da `models.py`.
3. **Schemas**: purgare da `backend/app/schemas/provider.py` (`ProviderAssignmentCreate`, `ProviderAssignmentUpdate`, `ProviderAssignmentOut`) e da `backend/app/schemas/assets.py`.
4. **Service**: rimuovere da `asset_source.py` e `api/v1/assets.py`.
5. **Settings**: rimuovere 3 placeholder mai usati da `GLOBAL_SETTINGS_DEFAULTS`: `auto_sync_fx_rates`, `auto_sync_prices`, `price_sync_interval_hours`.
6. **API comment fix**: correggere il docstring "read-only" in `assets.py` endpoint current-price.
7. **Test**: aggiornare `populate_mock_data.py`, `test_asset_source.py`, `test_db_referential_integrity.py`.

### Frontend
1. `AssetModal.svelte`: drop `fetchInterval` state, binding, payload.
2. `ProviderAssignmentSection.svelte`: drop prop `fetchInterval` e l'intero blocco `<div>Fetch Interval</div>`.
3. `fxStoreRegistry.ts`: drop dal type.
4. i18n: rimuovere `fetchInterval` da `en/it/fr/es.json`.
5. **Layout**: il grid nel provider section collassa. Lasciare senza riempire lo slot (info `last_fetch_at` per-asset già coperta dal pannello scheduler globale).

### Regenerazione API client
Dopo i cambi schema: `./dev.py api sync` per rigenerare `generated.ts` + `openapi.json`.

---

## 🎨 Frontend — GlobalSettingsTab + Modale Scheduler

> **Regola componenti**: cercare e usare SEMPRE i componenti custom già sviluppati nel progetto
> (`lib/components/ui/`) prima di ricorrere a elementi HTML nativi. Modali, toggle, input,
> select — tutto deve passare dal design system interno.

Le setting scheduler vivono come **righe normali** nella categoria "Sincronizzazione" della
`GlobalSettingsTab.svelte` (stessa struttura delle altre: sfondo `bg-gray-50 dark:bg-slate-800
rounded-lg px-4`, icona + label + hint a sinistra, controllo a destra). I 3 placeholder
attuali ("Sincronizzazione Tassi FX", "Sincronizzazione Prezzi", "Intervallo Sincronizzazione
Prezzi") vengono **eliminati** e sostituiti dalle nuove righe scheduler.

Per la configurazione complessa (orari, giorni, horizon), una riga-bottone apre una **modale
dedicata** (`SchedulerConfigModal.svelte`).

### Layout in GlobalSettingsTab (categoria "Sincronizzazione")

```
Sidebar:                       Content (righe setting standard):
┌────────────────────────┐
│ Tutte le Impostazioni  │     ┌─ setting-row (toggle) ──────────────────┐
│ Sessione               │     │ 🕐 Scheduler Attivo            ═══╗ ON  │
│ Sicurezza              │     │    "Abilita la sincronizzazione  ═══╝   │
│ ▶ Sincronizzazione     │     │     automatica dei dati di mercato"     │
│ Valori Predefiniti     │     └──────────────────────────────────────────┘
└────────────────────────┘
                               ┌─ setting-row (clickable → apre modale) ──┐
                               │ 📊 Ultimo aggiornamento     [ Dettagli… ] │
                               │    Current-price: 14:20 — 42 ok, 0 err    │
                               │    History sync:  23:00 — 87 ok, 2 err    │
                               │    (server time: Europe/Rome)              │
                               └────────────────────────────────────────────┘

                               ┌─ setting-row (button) ──────────────────┐
                               │ ⚙️ Configurazione Schedule              │
                               │    "Orari, giorni, frequenza"           │
                               │                        [ Configura… ]   │
                               └──────────────────────────────────────────┘
```

### Modale "Configure Schedule" (`SchedulerConfigModal.svelte`)

```
┌─── ⚙️ Configurazione Scheduler ─────────────────────── [✕] ────┐
│                                                                   │
│  ⓘ Tutti gli orari si riferiscono al fuso orario del server      │
│     (attualmente: Europe/Rome)                                    │
│                                                                   │
│  ━━━ Current Price Refresh ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│                                                                   │
│  Frequenza:  [ 10 ▼ ] minuti                                     │
│  hint: "Ogni quanti minuti aggiornare i prezzi live"              │
│                                                                   │
│  ━━━ History Sync ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│                                                                   │
│  Orari sync:  [ 06:00 ✕ ] [ 23:00 ✕ ] [+ Aggiungi]              │
│  hint: "Orari giornalieri per il sync storico prezzi e FX"        │
│                                                                   │
│  Giorni attivi:                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ [✓] Lun [✓] Mar [✓] Mer [✓] Gio [✓] Ven [✓] Sab [ ] Dom  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Orizzonte rolling:  [ 14 ] giorni                                │
│  hint: "Quanti giorni indietro ri-scaricare ad ogni ciclo"        │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ 💡 Suggerimento: pianifica dopo la chiusura dei mercati     │ │
│  │    (23:00 EU, 22:00 US). I dati intra-day incompleti si     │ │
│  │    correggono al ciclo successivo.                           │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ───────────────────────────────────────────────────────────────  │
│  [ Annulla ]                                    [ 💾 Salva ]      │
└───────────────────────────────────────────────────────────────────┘
```

### Componenti coinvolti

| Componente | File | Ruolo |
|------------|------|-------|
| `GlobalSettingsTab.svelte` | esistente | Sostituisce i 3 placeholder sync con le nuove righe scheduler (toggle + info/log button + bottone modale config) |
| `SchedulerConfigModal.svelte` | **nuovo** in `lib/components/settings/` | Modale con tutti i controlli di scheduling. Usa i componenti custom esistenti: modali da `ui/modals/`, toggle da `ui/`, input da `ui/input/` |
| `SchedulerLogModal.svelte` | **nuovo** in `lib/components/settings/` | Modale read-only con storico esecuzioni scheduler. Legge da `GET /settings/scheduler/log`. Entries collapsibili con dettaglio per-item. Filtri job/stato |
| `TimeSlotPicker.svelte` | **nuovo** (opzionale) in `lib/components/ui/` | Mini-componente chip list per aggiungere/rimuovere slot HH:MM (chip con ✕ + bottone [+ Aggiungi]) |

**⚠️ Regola**: nella modale usare SEMPRE i componenti custom del progetto (`lib/components/ui/`)
prima di ricorrere a elementi HTML nativi. Cercare nel codebase i pattern esistenti per:
modali, toggle switch, number input, checkbox, chip/tag list.

### Interazione

1. Admin apre Settings → tab Sync → vede sezione "Market Data Scheduler"
2. Toggle `scheduler_enabled` → salva inline (come gli altri toggle settings)
3. Click "Dettagli…" nella riga "Ultimo aggiornamento" → apre `SchedulerLogModal`
4. Nella modale log: vede storico esecuzioni con dettaglio per-item, filtra per job/stato
5. Click "Configure Schedule..." → apre `SchedulerConfigModal`
6. Nella modale config: modifica frequenza, orari, giorni, horizon
7. Click "Save" → PATCH bulk delle 4 GlobalSetting keys → chiude modale
8. Status hint si aggiorna (polling o refetch dopo save)

### Campi nella modale (riepilogo tecnico)

| Campo | Tipo | Validazione | i18n key |
|-------|------|-------------|----------|
| `scheduler_current_price_frequency_minutes` | number input / select | 1–1440 | `settings.global.scheduler.currentPriceFreq.{label,hint,suffix}` |
| `scheduler_history_sync_times` | chip list + time picker | CSV HH:MM, min 1 | `settings.global.scheduler.historyTimes.{label,hint}` |
| `scheduler_history_sync_days` | 7 checkbox inline | min 1 giorno | `settings.global.scheduler.historyDays.{label,hint,mon,tue,wed,thu,fri,sat,sun}` |
| `scheduler_history_sync_horizon_days` | number input | 1–365 | `settings.global.scheduler.historyHorizon.{label,hint,suffix}` |

**Nota i18n day labels**: la UI mostra nomi localizzati (EN: "Monday", IT: "Lunedì", ecc.) ma il valore salvato in `GlobalSetting` è sempre il codice EN (`"mon,tue,wed,thu,fri,sat"`). Il parsing nel backend è su codici EN, la localizzazione è solo UI.

**`server_tz`** esposto dall'endpoint `GET /api/v1/settings/scheduler/state` → mostrato nel disclaimer della modale.

### Modale "Scheduler Log" (`SchedulerLogModal.svelte`)

Aperta dal bottone "Dettagli…" nella riga "Ultimo aggiornamento". Mostra lo storico delle
esecuzioni dello scheduler con dettaglio per-item, leggendo da
`GET /api/v1/settings/scheduler/log?limit=20`.

```
┌─── 📊 Storico Esecuzioni Scheduler ─────────────────── [✕] ────┐
│                                                                   │
│  ┌─ Filtri ─────────────────────────────────────────────────────┐ │
│  │  Job: [ Tutti ▼ ]   Stato: [ Tutti ▼ ]                      │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─ Run #1 ─────────────────────────────────────────────────────┐ │
│  │ 🟢 current_price — 08 giu 15:26 — 1.35s                     │ │
│  │    22 ok, 2 err                                               │ │
│  │                                                               │ │
│  │  ┌─ Dettaglio (collapsible, aperto se err > 0) ────────────┐ │ │
│  │  │  ✅ Apple Inc.                                           │ │ │
│  │  │  ✅ Vanguard S&P 500                                     │ │ │
│  │  │  ✅ Bitcoin                                              │ │ │
│  │  │  ❌ Test Asset 1  — "No price data available"            │ │ │
│  │  │  ❌ Test Asset 2  — "No price data available"            │ │ │
│  │  │  ... (scrollabile se > 10 items)                         │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─ Run #2 ─────────────────────────────────────────────────────┐ │
│  │ 🟡 history_sync — 08 giu 15:26 — 7.52s                      │ │
│  │    assets: 21 ok, 3 err  |  fx: 0 ok, 0 err                  │ │
│  │                                                               │ │
│  │  ┌─ Assets (collapsible) ──────────────────────────────────┐ │ │
│  │  │  ✅ Apple Inc.        yfinance  +12 pts                  │ │ │
│  │  │  ✅ Vanguard S&P 500  justetf   +14 pts                  │ │ │
│  │  │  ❌ Test Asset 1      yfinance  "No price data from…"    │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  │  ┌─ FX (collapsible, collapsed se 0 errori) ──────────────┐ │ │
│  │  │  (nessuna coppia FX configurata)                         │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─ Run #3 ─────────────────────────────────────────────────────┐ │
│  │ 🟢 current_price — 08 giu 15:16 — 2.09s                     │ │
│  │    14 ok, 0 err                                               │ │
│  │    ▸ Dettaglio (collapsed — click to expand)                  │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ... (scroll / load more)                                         │
│                                                                   │
│  ───────────────────────────────────────────────────────────────  │
│                                             [ Chiudi ]            │
└───────────────────────────────────────────────────────────────────┘
```

#### Parsing del log JSONL (struttura dati)

L'endpoint `GET /api/v1/settings/scheduler/log` restituisce:
```json
{
  "entries": [...],
  "count": 20,
  "offset": 0
}
```

Ogni entry ha una delle due strutture:

**`current_price`**:
```json
{
  "ts": "2026-06-08T15:26:02+02:00",
  "job": "current_price",
  "duration_s": 1.35,
  "status": "ok" | "partial" | "error",
  "summary": { "ok": 22, "err": 2 },
  "items": [
    { "asset_id": 1, "name": "Apple Inc.", "ok": true },
    { "asset_id": 2, "name": "Test Asset", "ok": false, "error": "No price data available" }
  ]
}
```

**`history_sync`**:
```json
{
  "ts": "2026-06-08T15:26:04+02:00",
  "job": "history_sync",
  "duration_s": 7.52,
  "status": "partial",
  "summary": { "assets_ok": 21, "assets_err": 3, "fx_ok": 0, "fx_err": 0 },
  "assets": [
    { "asset_id": 3, "name": "Apple Inc.", "status": "ok", "provider": "yfinance", "points_changed": 12 },
    { "asset_id": 4, "name": "Test Asset", "status": "failed", "errors": ["Provider not found: xyz"], "provider": "xyz", "points_changed": 0 }
  ],
  "fx": [
    { "pair": "EUR-USD", "status": "ok", "provider": "ecb", "points_changed": 14 },
    { "pair": "CHF-CNY", "status": "failed", "errors": ["No FX data"], "points_changed": 0 }
  ]
}
```

#### Logica di rendering

| Campo | Rendering |
|-------|-----------|
| `status` | 🟢 `ok`, 🟡 `partial`, 🔴 `error` |
| `ts` | Formattato locale (es. "08 giu 15:26") tramite `Intl.DateTimeFormat` |
| `duration_s` | Mostrato accanto al timestamp |
| `items` / `assets` / `fx` | Lista collapsible. Se `err > 0` → aperta di default; se tutto ok → collapsed |
| `error` / `errors[]` | Testo rosso dopo il nome asset/pair |
| `points_changed` | Badge grigio "+12 pts" (solo per history_sync) |
| `provider` | Badge neutro accanto al nome (solo per history_sync) |

#### data-testid

- `scheduler-log-modal` — la modale
- `scheduler-log-entry` — ogni run card
- `scheduler-log-entry-status` — icona stato (🟢/🟡/🔴)
- `scheduler-log-detail-toggle` — bottone expand/collapse
- `scheduler-log-item` — ogni riga item dentro il dettaglio
- `scheduler-log-item-error` — messaggio errore

#### i18n keys (namespace `settings.global.scheduler.log.*`)

- `title`, `filterJob`, `filterStatus`, `allJobs`, `allStatuses`
- `currentPrice`, `historySync`, `ok`, `partial`, `error`
- `assetsSection`, `fxSection`, `noEntries`, `loadMore`, `close`
- `pointsChanged` (con placeholder `{n}`)

**Scheduler Log** esposto da `GET /api/v1/settings/scheduler/log?limit=20&offset=0` → paginato, newest-first. Load more incrementa `offset`.

### i18n (EN/IT/FR/ES)

Tutti i nuovi messaggi aggiunti via `./dev.py i18n add` nei 4 locali.

---

## 🧪 Test

### Backend
1. **Unit**: `test_scheduler_state.py` (load/save JSON, atomic write, corruption recovery).
2. **Unit**: `test_scheduler_due.py` (`due_current_price`, `due_history_sync` con edge case: multi-slot, wrong day, already-run slot, never-run, downtime across midnight).
3. **Unit**: `test_scheduler_leader.py` (mock `psutil`, scenari single/multi-worker/zombie, Docker PID 1).
4. **Integration**: `test_scheduler_loop.py` (mock time + mock service layer, verifica che un run completo scriva lo state, verifica sessione fresca per ogni job).
5. **API**: `test_scheduler_state_api.py` (endpoint `/settings/scheduler/state` read-only + `/settings/scheduler/log` paginato, auth admin-only).
6. **Settings**: test update di ciascuna delle 5 nuove keys con validazione range + parsing CSV times/days.

### Frontend
1. **E2E**: `scheduler-settings.spec.ts` — admin modifica le 5 settings, verifica persistenza + visibilità hint "Last execution".
2. **E2E**: verifica che `ProviderAssignmentSection` non mostri più il campo Fetch Interval (post-rimozione).

### Manuale
1. Avviare backend, attendere 1–2 cicli, ispezionare `scheduler_state.json`.
2. Cambiare `scheduler_current_price_frequency_minutes` a 2, attendere 2 min, verificare nuovo run.
3. Toggle `scheduler_enabled = false`, attendere >10 min, verificare che non ci siano nuove run.

---

## 📦 Moduli backend — struttura

```
backend/app/services/scheduler/
├── __init__.py
├── scheduler.py          # scheduler_loop(), startup/shutdown integration
├── leader.py             # am_i_leader() via psutil (with --reload dev mode fix)
├── state.py              # load/save scheduler_state.json (atomic write-then-rename)
├── jobs.py               # run_current_price_refresh(), run_history_sync()
├── joblog.py             # JSONL job log — per-item detail, append, rotation (500 entries), read (paginated)
└── settings.py           # SchedulerSettings dataclass, load_scheduler_settings() da GlobalSetting, parsing CSV
```

### Job: Current-Price Refresh

1. Query asset attivi con provider assegnato:
   ```python
   SELECT a.id, a.display_name FROM asset a
   JOIN asset_provider_assignment apa ON a.id = apa.asset_id
   WHERE a.active = True
   ```
2. Chiama `AssetSourceManager.get_current_prices_bulk(asset_ids, session, concurrency=3)`
3. L'upsert OHLC F.2/F.3 è già incluso nel service layer (nessuna logica aggiuntiva).
4. Log `INFO` 1 riga: `"Scheduler: current-price refresh — {ok} ok, {err} errors, {duration:.1f}s"`

### Job: History Sync

1. **Assets**: stessa query di current-price → `AssetSourceManager.bulk_refresh_prices(refresh_items, session, concurrency=3)` con `start_date = today - horizon_days`, `end_date = today`.
2. **FX**: query tutte le `FxConversionRoute` → extract `(base, quote)` pairs → `sync_pairs_bulk(session, pairs, (start_date, end_date))`.
3. Log `INFO` 1 riga: `"Scheduler: history sync — assets: {ok}/{total}, fx: {ok}/{total}, {duration:.1f}s"`

---

## 🗂️ Struttura piani

```
phase-08-subplan/
├── plan-phase08-scheduler.prompt.md              # piano principale (questa phase)
├── plan-phase08Step1-cleanup.prompt.md
│   # Step 1: rimozione fetch_interval + placeholder settings + fix commento API
│   # Self-contained, eseguibile in ~2h
├── plan-phase08Step2-backend-daemon.prompt.md
│   # Step 2: psutil dep + scheduler/ module + leader election + state JSON + jobs + lifespan hook + GlobalSetting keys
│   # Core più complesso, ~4-6h
└── plan-phase08Step3-admin-ui.prompt.md
    # Step 3: UI GlobalSettingsTab section + SchedulerConfigModal + hint "Last execution" + scheduler log panel + i18n 4 lingue
    # Endpoint backend già pronti: GET /settings/scheduler/state + GET /settings/scheduler/log
    # ~3h
```

### Ordine di esecuzione

1. **Step 1** (pulizia `fetch_interval` + placeholder + fix): ✅ completato.
2. **Step 2** (backend demone): ✅ completato.
3. **Step 3** (UI settings + stato + log modal): ✅ completato (inclusi 5 round di bugfix).

---

## ✅ Deliverable

- ✅ Demone embedded nel backend che aggiorna current-price e history senza intervento utente.
- ✅ 5 nuove `GlobalSetting` keys configurabili runtime (3 placeholder vecchi rimossi).
- ✅ Scheduling history granulare: orari multipli + selezione giorni della settimana.
- ✅ Endpoint `GET /api/v1/settings/scheduler/state` per la UI.
- ✅ Endpoint `GET /api/v1/settings/scheduler/log?since=ISO` per il job log dettagliato (date-based filtering).
- ✅ Job log JSONL (`scheduler_jobs.jsonl`) con dettaglio per-item e rotation (500 entries).
- ✅ Campo `fetch_interval` completamente rimosso (DB + schemas + frontend + i18n).
- ✅ Commento API "read-only" corretto su endpoint current-price.
- ✅ UI `GlobalSettingsTab` con sezione Scheduler + "Last execution" hint + tip orario post-chiusura.
- ✅ `SchedulerConfigModal.svelte`: configurazione frequenza/orari/giorni/horizon, bulk save via `PATCH /global/bulk`.
- ✅ `SchedulerLogModal.svelte`: storico esecuzioni con layout tabellare, filtri job/stato/tempo, tooltip errori con copy-to-clipboard, provider chain con icone (reusa `parseProviderChain`), bandiere valute FX.
- ✅ Vecchio endpoint `PUT /settings/global/{key}` rimosso — bulk è l'unico metodo di aggiornamento.
- ✅ Asset.active toggle in AssetModal + pallina stato + banner archiviato nella detail page.
- ✅ JSONL arricchito: `icon_url` per asset, `prices_changed`/`events_changed` split, `base`/`quote` per FX.
- ✅ Route MANUAL escluse dallo scheduler (NOK-SEK non sincronizzata, non genera errori).
- ✅ Mock data: `populate_mock_data.py` genera `scheduler_jobs.jsonl` (5 entries ieri) + `scheduler_state.json` (last runs ieri → trigger immediato).
- ✅ Multi-worker safe via lowest-PID election con `psutil` (+ fix dev mode `--reload`).
- ✅ Dipendenza `psutil` aggiunta a `Pipfile` + `requirements.txt`.
- ✅ `is_superuser=True` fix per `e2e_test_admin` in `populate_mock_data.py`.
- ⏳ Test suite backend + E2E frontend — non ancora scritti (da fare in round futuro).

---

## 🔗 Cross-link

- Origine della side-quest: conversazioni durante implementazione di [`../plan-phase07-transaction-Part1.md`](../plan-phase07-transaction-Part1.md).
- Dipendenze a monte: Phase 5 (FX sync), Phase 6 (Asset sync + current-price service).
- Impatta: `GlobalSettingsTab.svelte` (Phase 3), `AssetModal.svelte` + `ProviderAssignmentSection.svelte` (Phase 6), `FxProviderRegistry` (Phase 5).
- Precede: Phase 9 (Dashboard, ex Phase 8) — la dashboard trarrà beneficio dai dati sempre freschi garantiti dal demone.
- **Piano esecutivo Step 1+2**: [`../plan-phase08Step1-2-backend.prompt.md`](../plan-phase08Step1-2-backend.prompt.md) — completato 2026-06-08.

---

## 📝 Design Discussion Log (2026-06-05)

Domande borderline emerse durante la sessione di design e relative risposte:

| # | Domanda | Risposta | Impatto |
|---|---------|----------|---------|
| 1 | **Current-price upsert: service o API?** | ✅ Service layer (`get_current_prices_bulk` L2823–2910). Commento API "read-only" errato → fix in Step 1 | Nessun refactor necessario |
| 2 | **History end_date: today o today-1?** | `today` — dati parziali intra-day accettabili, si correggono al ciclo successivo. Hint UI per orario post-chiusura mercati | `end_date = today` |
| 3 | **Scheduling fisso vs granulare?** | Granulare: multi-slot orari + selezione giorni. Es: `"06:00,23:00"` + `"mon,tue,wed,thu,fri,sat"` | 2 nuove keys CSV vs 1 key HH:MM |
| 4 | **Multi-worker race su state JSON** | `os.replace` atomico. Crash mid-job → re-exec al prossimo tick. Service idempotenti (upsert) → innocuo | Nessuna mitigazione necessaria |
| 5 | **Concorrenza scheduler+utente** | Non grave: la cache in-process (current 2min TTL, history 15min TTL) fa da dedup naturale. Scheduler popola cache → utente refresh → cache HIT istantaneo. `concurrency=3` conservativo | Documentato, protetto dalla cache |
| 6 | **FX pairs filtering** | Tutte le route configurate (nessun `active` su `FxConversionRoute`). Pair non desiderate → rimuovere dalla config | Opzione (A) — nessun campo aggiuntivo |
| 7 | **Logging verbosity** | `DEBUG` per dettagli, `INFO` solo 1 riga summary per job. Nessun log per tick idle | Pattern stabilito |
| 8 | **psutil compilazione** | Ha estensioni C (`.so`), ma Dockerfile ha `gcc`. Installabile via `pip install`. Non è stdlib ma è de facto standard | Aggiungere a Pipfile + requirements.txt |
| 9 | **Placeholder settings esistenti** | `auto_sync_fx_rates`, `auto_sync_prices`, `price_sync_interval_hours` — mai chiamati, cancellare | Pulizia in Step 1 |

### Critical Review (2026-06-05, round 2)

Fix integrati dopo analisi critica del piano:

| # | Severità | Issue | Fix applicato |
|---|----------|-------|---------------|
| 10 | 🔴 | **`am_i_leader()` sync I/O in async context** — `psutil` legge `/proc/` o `sysctl`, viola Async I/O Rule | ~~Wrappato con `await asyncio.to_thread(am_i_leader)`~~ → Rimosso in implementazione: <1ms, `to_thread` aggiungeva complessità senza beneficio |
| 11 | 🟡 | **Session management** — lo scheduler non è un request handler, non ha la sessione FastAPI DI | Ogni job crea la propria `AsyncSession(get_async_engine())`, sessione mai riusata tra job (pattern da `_initialize_global_settings()`) |
| 12 | 🟡 | **Downtime across midnight** — slot perso non recuperato se server offline durante lo slot | Documentato come limitazione nota. Con `horizon_days=14` + multi-slot il recupero è naturale |
| 13 | 🟢 | **Nome `daily_history` fuorviante** — il job può girare N volte al giorno | Rinominato → `history_sync` (JSON state key, funzioni, due-check) |
| 14 | 🟢 | **i18n day labels** — la UI deve mostrare nomi localizzati ma salvare codici EN | Aggiunto: i18n keys per ogni giorno, valore DB sempre `"mon,tue,..."` |

### Implementation Findings (2026-06-08, round 4)

Problemi scoperti durante l'implementazione:

| # | Severità | Issue | Fix applicato |
|---|----------|-------|---------------|
| 18 | 🔴 | **`AssetProviderAssignment.is_active` non esiste** — il piano aveva `.where(AssetProviderAssignment.is_active == True)` ma la tabella `asset_provider_assignments` non ha quel campo (relazione 1-to-1: se l'assignment esiste, il provider è attivo). **NB**: `Asset.active` esiste e viene usato correttamente come filtro (`.where(Asset.active == True)`) — non confondere i due | Rimosso solo `.where(AssetProviderAssignment.is_active == True)` dalle query in `jobs.py`. Il filtro `Asset.active` resta |
| 19 | 🔴 | **Leader election fallisce in dev mode** — uvicorn `--reload` usa watchfiles che mantiene vecchi worker subprocess con PID più bassi; il worker corrente pensa di non essere leader | `leader.py`: detect `--reload` nel cmdline del parent → `return True` immediatamente |
| 20 | 🟡 | **`Asset.ticker` non esiste** — il modello usa `identifier_ticker` (opzionale) e `display_name` (obbligatorio) | Query aggiornata a `select(Asset.id, Asset.display_name)`, job log usa `name` (= `display_name`) |
| 21 | 🟡 | **`_shutdown_event` stale dopo hot-reload** — l'evento singleton rimaneva `set()` dal ciclo precedente, impedendo nuovi loop | `get_shutdown_event()`: se `_shutdown_event.is_set()` → crea nuovo `Event()` (reset guard) |
| 22 | 🟢 | **Logging troppo verboso** — stato scoperta/debug visibile in produzione | Rimossi log di debug (leader election, tick count, sleep). Solo `INFO` per loop start/stop + 1 riga per job eseguito |
| 23 | 🟢 | **scheduler_state.json solo conteggi aggregati** — impossible diagnosticare *quale* asset/pair fallisce | Aggiunto `scheduler_jobs.jsonl` con dettaglio per-item + endpoint API paginato + rotation a 500 entries |

### UI Corrections (2026-06-08, round 3)

| # | Severità | Issue | Fix applicato |
|---|----------|-------|---------------|
| 15 | 🟡 | **Toggle Active/Inactive nella pagina errata** — era nel pannello "Metadata & Classification" della detail page | Spostato dentro `AssetModal.svelte` (modale "Modifica Asset") per riusare il flusso "Salva" esistente. Lo stato (pallina 🟢/🔴) nel titolo della pagina detail |
| 16 | 🟡 | **GlobalSettingsTab layout errato** — ASCII art mostrava layout custom non coerente con la struttura reale (righe `bg-gray-50 rounded-lg px-4`) | Riscritto: righe standard nella categoria "Sincronizzazione" (stesse degli altri setting). Bottone "Configura" apre modale. Eliminati i 3 placeholder attuali |
| 17 | 🟢 | **Componenti custom** — piano non specificava di usare i componenti UI interni | Aggiunta regola esplicita: cercare e usare SEMPRE `lib/components/ui/` prima di HTML nativi |

### Step 3 UI Implementation & Bugfix Rounds (2026-06-08)

| # | Severità | Issue | Fix applicato |
|---|----------|-------|---------------|
| 24 | 🔴 | **`is_admin` inesistente in User model** — `populate_mock_data.py` usava `is_admin=True` per e2e_test_admin, silenziosamente ignorato | Corretto a `is_superuser=True` |
| 25 | 🔴 | **SchedulerConfigModal: $effect resetta valori editati** — Svelte 5 tracka `currentValues` (inline object dal parent) dentro `$effect` → ogni re-render resettava timeSlots ai valori originali | Fix: `untrack(() => { ... })` su `currentValues` dentro l'effect. Solo `open` è tracciato come dipendenza |
| 26 | 🔴 | **`datetime` import mancante** in `populate_mock_data.py` — `from datetime import date, timedelta` non includeva `datetime`, crash su `populate_scheduler_mock_log()` | Aggiunto `datetime` all'import |
| 27 | 🟡 | **Vecchio endpoint PUT /settings/global/{key}** — ridondante dopo introduzione PATCH /global/bulk | Rimosso endpoint + schema `GlobalSettingUpdate` + aggiornati 3 test API + migrata `updateSetting()` in globalSettings.ts a bulk |
| 28 | 🟡 | **Scheduler log API: limit/offset inadeguato** — il frontend faceva sempre `?limit=20&offset=0` | Cambiato a `?since=ISO_DATETIME` — filtro temporale, nessun offset. Frontend refetchs con filtro tempo selezionato |
| 29 | 🟡 | **Route MANUAL sincronizzate dallo scheduler** — NOK-SEK (MANUAL) generava errore e stato "partial" | `jobs.py`: filtra `chain_steps` JSON, skip route con `provider == "MANUAL"` |
| 30 | 🟡 | **Provider chain (CHAIN:ECB+SNB) mostrato come testo raw** — nessuna icona o badge | Frontend: usa `parseProviderChain()` + `getFxProviderIconUrl()` + `PROVIDER_COLORS` badge — stesso pattern di `FxSyncModal.svelte` |
| 31 | 🟡 | **Warning banner in fondo e con emoji duplicata** — `GlobalSettingsTab` aveva `⚠️` emoji + SVG icon alert + banner in fondo alla pagina | Spostato in cima, rimossa emoji (solo SVG) |
| 32 | 🟡 | **Modal header/footer non in stile progetto** — SchedulerLogModal e ConfigModal usavano stile diverso | Allineati: `px-6 py-4 border-b/t`, icon badge `w-9 h-9 rounded-lg`, pulsante X, Escape chiude |
| 33 | 🟢 | **Tooltip errori + copy-to-clipboard** — errori mostrati solo con `title=`, nessun copy | Tooltip component con `text` prop, dblclick/long-press copia in clipboard, toast "Copied!" |
| 34 | 🟢 | **Layout dettagli non tabellare** — items in flex rows disallineati | Convertito a `<table>` con colonne: ✓/✗, Name, Provider, Delta, Errors. Headers i18n |
| 35 | 🟢 | **FX senza bandiere valute** — pair mostrate come testo semplice | Aggiunto `getCurrencyInfo(base/quote).flag_emoji` accanto al pair name |
| 36 | 🟢 | **JSONL arricchito** — mancava `icon_url`, `prices_changed`/`events_changed` separati, `base`/`quote` per FX | Backend: `joblog.py` builder aggiornati, `jobs.py` query `Asset.icon_url` |
| 37 | 🟢 | **Mock data con date di oggi** — scheduler non triggera sync dopo populate | Tutte le mock entries datate **ieri** + mock `scheduler_state.json` con last_run ieri → trigger immediato |
| 38 | 🟢 | **Bulk endpoint ignora chiavi inesistenti** — non dava errore se una key non esisteva | Aggiunto `raise HTTPException(404)` se `update_global_setting()` ritorna None |
