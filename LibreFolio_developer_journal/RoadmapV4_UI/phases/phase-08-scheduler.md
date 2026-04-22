# Phase 8 — Market Data Scheduler

> **Status**: ⏳ Pianificata, avvio previsto dopo la chiusura di tutte le parti di Phase 7 (Transactions).
> **Giorni stimati**: 2
> **Origine**: side-quest emersa durante Phase 7 dalla convergenza dei sistemi FX (Phase 5) e Asset (Phase 6). Con entrambi i pipeline di sync collaudati e stabili, ha senso automatizzare l'esecuzione periodica invece di lasciarla manuale.

---

## 🎯 Obiettivo

Introdurre un **demone embedded nel backend FastAPI** che mantiene i dati di mercato aggiornati senza intervento utente:

1. **Current-price refresh** a frequenza configurabile (default 10 min).
2. **Daily history sync** una volta al giorno (default 23:00 server time) con orizzonte rolling (default 14 gg indietro).

Parametri configurabili runtime da un amministratore tramite `GlobalSettingsTab.svelte`, persistiti in `GlobalSetting`, riletti dal demone ad ogni tick senza restart.

In aggiunta: **rimozione di `fetch_interval` per-provider** su `AssetProviderAssignment` e `FxProviderAssignment`. Con uno scheduler globale il campo è ridondante, fragile e complica la UX del form provider.

---

## 🧱 Decisioni architetturali

| Tema | Scelta | Motivazione |
|------|--------|-------------|
| **Tech demone** | Loop `asyncio` nativo, tick 1 min, rilegge settings ogni tick | Zero dipendenze, 0 accoppiamento settings↔scheduler, setting update entra in vigore entro 60s |
| **APScheduler** | ❌ scartato | Overhead ingiustificato per 2 job, richiederebbe `reschedule_job()` su ogni update settings |
| **Multi-worker** | `psutil` + elezione **lowest-PID** rivalutata ad ogni tick | Cross-platform (Win/macOS/Linux), self-healing, no stale lock, promozione automatica <60s se il leader crasha |
| **Mutex globale DB** | ❌ non necessario | DB serializza le write; doppia write (edge case) innocua come confermato |
| **Stato persistente** | JSON file `backend/data/<env>/scheduler_state.json` scritto atomicamente (write-then-rename) | Sopravvive al restart; zero migrazioni; basta per "quando è stata l'ultima run?" |
| **Nuova tabella `SyncJobRun`** | ❌ scartato | Retention + peso DB non giustificati per info riassuntiva già nel JSON |
| **Chiamate sync** | Il demone invoca **direttamente i service layer esistenti** (`asset_source.sync_asset_prices`, `fx_source.sync_fx_rates`, `current_price_service.fetch_current_price`) | Nessun HTTP interno, nessuna reimplementazione, riusa i test già green |
| **Nuovi endpoint** | **Uno solo**: `GET /api/v1/admin/scheduler/state` (read-only, admin-gated) | Serve al `GlobalSettingsTab` per l'hint "Last execution" sotto ogni input |
| **Timezone** | Ora locale del server (stessa del container Docker) | Per un self-hosted singolo utente è la semantica più naturale; documentato nell'hint UI |
| **Nuova dipendenza** | `psutil` | Cross-platform process introspection; libreria standard de facto |

---

## 🗄️ Nuove `GlobalSetting` keys

| Key | Type | Default | Range / Format | Descrizione |
|-----|------|---------|----------------|-------------|
| `scheduler_enabled` | bool | `true` | — | Master toggle; se `false` il loop gira ma non esegue alcun job |
| `scheduler_current_price_frequency_minutes` | int | `10` | 1–1440 | Interval (minuti) tra due refresh del current-price |
| `scheduler_history_sync_time` | string | `"23:00"` | `HH:MM` server time | Orario daily del sync storico FX + assets |
| `scheduler_history_sync_horizon_days` | int | `14` | 1–365 | Finestra rolling backward per il sync storico |

### 🔁 Interazione con `Asset.active`

**Ancoraggio** (side-note da I-bis #17, Phase 7 — 2026-04-22): il campo
`Asset.active` oggi è usato solo come filtro di lista. Lo scheduler è il
consumer naturale per dare semantica "archiviato" al flag:

- **Current-price refresh**: il demone itera solo su `Asset.active == True` —
  asset inattivi non vengono pollati. Policy speculare per FX: `FxPair.active`
  gating sul medesimo demone.
- **Daily history sync**: stessa logica — inattivi esclusi dal rolling
  horizon.
- **Implementazione**: aggiungere `where(Asset.active == True)` nelle query
  che il demone esegue su `AssetProviderAssignment` (JOIN con `Asset`).

Questo è il reason d'essere del toggle tri-state "Active | Inactive" che
la Phase 7 (I-bis #20) ha introdotto nel `GET /assets/query`: permette
all'utente di archiviare asset "storici" (es. RE Loan chiusi, titoli
delistati) senza perdere l'history, e di escluderli automaticamente dai
cicli di sync senza doverli cancellare.

Nota: fin tanto che il demone non è attivo (Phase 8 non completata), la
semantica di `active` resta puramente "filtro di lista" — nessun effetto
sul sync manuale via pulsante. Tracciato nel Plan-phase07-Part3 I-bis #19
(follow-up).

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
  "daily_history": {
    "last_run_at": "2026-04-19T23:00:15+02:00",
    "last_duration_s": 127.8,
    "last_status": "ok",
    "last_items_ok": 87,
    "last_items_err": 2,
    "last_error": null
  }
}
```

- **Write atomico**: `write to <name>.tmp → os.replace(<name>.tmp, <name>)`.
- **Read resiliente**: se il file manca o è corrotto → stato iniziale tutto null, il demone esegue subito.

---

## 🔁 Logica del loop

```python
async def scheduler_loop(shutdown_event: asyncio.Event):
    while not shutdown_event.is_set():
        try:
            if am_i_leader():  # psutil + lowest PID among live siblings
                settings = await load_scheduler_settings()  # reads GlobalSetting
                if settings.scheduler_enabled:
                    state = load_state_json()
                    now = datetime.now().astimezone()
                    if due_current_price(now, settings, state):
                        await run_current_price_refresh(state)
                        save_state_json(state)
                    if due_daily_history(now, settings, state):
                        await run_daily_history_sync(state)
                        save_state_json(state)
        except Exception as e:
            logger.exception("scheduler_loop tick failed: %s", e)
        await asyncio.sleep(60)
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
- `due_daily_history(now, s, st)`: `True` se (`st.daily_history.last_run_at is None`) **oppure** (`now.date() > last.date()` **and** `now.time() >= s.history_sync_time`).

### Integrazione con FastAPI

- `lifespan()` in `main.py`: `asyncio.create_task(scheduler_loop(shutdown_event))` al startup; `shutdown_event.set()` + `await task` al shutdown.
- Il loop non blocca il server: gira in parallelo sul medesimo event loop (`am_i_leader()` cheap, `sleep(60)` giusto).

---

## 🔥 Rimozione `fetch_interval`

### Backend
1. **DB**: rimuovere campo da `AssetProviderAssignment` e `FxProviderAssignment` in `alembic/versions/001_initial.py` (convenzione progetto: no migrazioni incrementali → `./dev.py db create-clean`).
2. **Schemas**: purgare da `backend/app/schemas/provider.py` (`ProviderAssignmentCreate`, `ProviderAssignmentUpdate`, `ProviderAssignmentOut`) e da `backend/app/schemas/assets.py` L129.
3. **Service**: rimuovere da `asset_source.py` (L788, L797) e `api/v1/assets.py` (L550, L580).
4. **Test**: aggiornare `populate_mock_data.py`, `test_asset_source.py`, `test_db_referential_integrity.py`.

### Frontend
1. `AssetModal.svelte`: drop `fetchInterval` state, binding, payload (L123, L187, L346, L378, L771, L833, L1208).
2. `ProviderAssignmentSection.svelte`: drop prop `fetchInterval` (L79, L85) **e** l'intero blocco `<div>Fetch Interval</div>` (quello nel DOM snippet fornito dall'utente).
3. `fxStoreRegistry.ts`: drop dal type (L59).
4. i18n: rimuovere `fetchInterval` da `en/it/fr/es.json` (es.json L333 + controparti).
5. **Layout**: il grid `grid-cols-[1fr_auto]` nel provider section collassa a `grid-cols-1`. Lasciare senza riempire lo slot (info `last_fetch_at` per-asset già coperta dal pannello scheduler globale).

### Regenerazione API client
Dopo i cambi schema: `./dev.py api sync` per rigenerare `generated.ts` + `openapi.json`.

---

## 🎨 Frontend — GlobalSettingsTab

Nuova sezione **Market Data Scheduler** in `frontend/src/lib/components/settings/tabs/GlobalSettingsTab.svelte`, dopo Security/Uploads, prima di Providers.

### Campi UI

| Campo | Tipo | Validazione | i18n key |
|-------|------|-------------|----------|
| `scheduler_enabled` | toggle | — | `settings.global.scheduler.enabled.{label,hint}` |
| `scheduler_current_price_frequency_minutes` | number | 1–1440 | `settings.global.scheduler.currentPriceFreq.{label,hint,suffix}` |
| `scheduler_history_sync_time` | time picker (`<input type="time">`) | HH:MM | `settings.global.scheduler.historyTime.{label,hint}` |
| `scheduler_history_sync_horizon_days` | number | 1–365 | `settings.global.scheduler.historyHorizon.{label,hint,suffix}` |

### Hint "Last execution"

Sotto ogni setting correlato, mostrare testo readonly derivato da `GET /api/v1/admin/scheduler/state`:

- Sotto `currentPriceFreq`:
  > *Last current-price run: 2026-04-20 14:20 — 42 assets synced, 0 errors (server time)*
- Sotto `historyTime` e `historyHorizon`:
  > *Last history sync: 2026-04-19 23:00 — 87 items synced, 2 errors (server time)*

Se `last_run_at` è null: `"Never run yet"`.

### Server time disclaimer

Sezione header con hint globale:
> *ⓘ All times refer to the **server's local time zone** (currently: {server_tz}).*

`server_tz` ottenibile da `Intl.DateTimeFormat().resolvedOptions().timeZone` **solo se il server == client**. Per essere corretti, esporre la tz server dal nuovo endpoint `/admin/scheduler/state` (`server_tz: "Europe/Rome"`).

### i18n (EN/IT/FR/ES)

Tutti i nuovi messaggi aggiunti via `./dev.py i18n add` nei 4 locali.

---

## 🧪 Test

### Backend
1. **Unit**: `test_scheduler_state.py` (load/save JSON, atomic write, corruption recovery).
2. **Unit**: `test_scheduler_due.py` (`due_current_price`, `due_daily_history` con edge case).
3. **Unit**: `test_scheduler_leader.py` (mock `psutil`, scenari single/multi-worker/zombie).
4. **Integration**: `test_scheduler_loop.py` (mock time + mock service layer, verifica che un run completo scriva lo state).
5. **API**: `test_admin_scheduler_state.py` (endpoint read-only, auth admin-only).
6. **Settings**: test update di ciascuna delle 4 nuove keys con validazione range.

### Frontend
1. **E2E**: `scheduler-settings.spec.ts` — admin modifica i 4 settings, verifica persistenza + visibilità hint "Last execution".
2. **E2E**: verifica che `ProviderAssignmentSection` non mostri più il campo Fetch Interval (post-rimozione).

### Manuale
1. Avviare backend, attendere 1–2 cicli, ispezionare `scheduler_state.json`.
2. Cambiare `scheduler_current_price_frequency_minutes` a 2, attendere 2 min, verificare nuovo run.
3. Toggle `scheduler_enabled = false`, attendere >10 min, verificare che non ci siano nuove run.

---

## 🗂️ Struttura piani

```
phase-08-subplan/
├── plan-phase08-scheduler.prompt.md              # piano principale (questa phase)
├── plan-phase08Step1-remove-fetch-interval.prompt.md
│   # Step 1: rimozione DB + schemas + frontend + i18n (self-contained, breaking change isolato)
├── plan-phase08Step2-backend-daemon.prompt.md
│   # Step 2: GlobalSetting keys + scheduler_loop + psutil leader + JSON state + lifespan hook
└── plan-phase08Step3-global-settings-ui.prompt.md
    # Step 3: UI scheduler section + endpoint /admin/scheduler/state + hint "Last execution" + i18n 4 lingue
```

### Ordine di esecuzione

1. **Step 1** (rimozione `fetch_interval`): self-contained, pulisce il terreno.
2. **Step 2** (backend demone): foundation per la UI.
3. **Step 3** (UI settings + stato): chiude il loop.

---

## ✅ Deliverable

- Demone embedded nel backend che aggiorna current-price e history senza intervento utente.
- 4 nuove `GlobalSetting` keys configurabili runtime.
- Endpoint `GET /api/v1/admin/scheduler/state` per la UI.
- Campo `fetch_interval` completamente rimosso (DB + schemas + frontend + i18n).
- UI `GlobalSettingsTab` con sezione Scheduler + "Last execution" hint.
- Multi-worker safe via lowest-PID election con `psutil`.
- Test suite backend + E2E frontend green.

---

## 🔗 Cross-link

- Origine della side-quest: conversazioni durante implementazione di [`../plan-phase07-transaction-Part1.md`](../plan-phase07-transaction-Part1.md).
- Dipendenze a monte: Phase 5 (FX sync), Phase 6 (Asset sync + current-price service).
- Impatta: `GlobalSettingsTab.svelte` (Phase 3), `AssetModal.svelte` + `ProviderAssignmentSection.svelte` (Phase 6), `FxProviderRegistry` (Phase 5).
- Precede: Phase 9 (Dashboard, ex Phase 8) — la dashboard trarrà beneficio dai dati sempre freschi garantiti dal demone.

