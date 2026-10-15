# Piano — fase 01, Z · Sospensione e risveglio (F26, F07, C-49)

> Workstream Z della 1.3.0 «Cloud-ready core». Piano generale: [`plan-phase01Release13.prompt.md`](../plan-phase01Release13.prompt.md)
> (§4 «Z · Sospensione e risveglio», §5, §6, §9, §10 n. 10); stato vivo della fase: [README](../README.md); decisioni
> del developer: [`decisioni-analisi-20261014.md`](../decisioni-analisi-20261014.md), punti 31–35; backlog:
> [`BACKLOG_POST_1.2.md`](../../Phase_0/BACKLOG_POST_1.2.md), sezione «Z · Sospensione e risveglio (fase 01)».
>
> - **Sessione**: `Z - Sospensione e risveglio` (`d401e062`), agente `coordinated-workstream`. Coordinatore: «Release 1.3
>   planning» (`928ffa97`).
> - **Ramo**: `e-alfy-z-sospensione-e-risveglio`. Base dell'analisi `459131eb8`; base attuale `1e9e567f7` (avanzamento
>   veloce del coordinatore, 15/10: riordino di X, W, J, A e H, lotti A–D dei colori, Designer Lab, 1.2.1).
> - **Corsia**: porta 6186, data-dir `/tmp/librefolio-r13-z`. Preambolo:
>   `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6186 --data-dir /tmp/librefolio-r13-z <CATEGORIA> <AZIONE>`,
>   una invocazione alla volta, con `nice`.
>
> **Autorizzazione del developer, alla lettera** (15/10 ~12:47, inoltrata dal coordinatore): «Sì: avvia tu Y (i due
> tagli) e Z (Z6a subito, Z1 quando decido il 31)». Autorizzato ora: **Z6a** (prove su C-49, senza codice di prodotto).
> Z1 aspetta il punto 31; i punti 32–35 servono ai lotti dopo.

## Stato dei passi

| Passo | Cosa | Stato |
|---|---|---|
| A | Analisi d'implementazione (sola lettura), inviata al coordinatore | ✅ 14/10 |
| A2 | Riverifica dell'analisi sul codice di `1e9e567f7`, questo piano, la mia sezione del backlog | ✅ 15/10 |
| Z6a | C-49: prove senza codice di prodotto (`npm ci` dal lock, `front build --debug`, tre gate nella mia corsia) | ⏳ autorizzato, dopo la fine della finestra del coordinatore |
| Z1 | Pausa degli aggiornamenti nel frontend (F26) | ⏸ attende il punto 31 |
| Z2 | Attività dell'utente e sospensione su Fly (F26, backend) | ⏸ attende gli agganci di H e il punto 32 |
| Z3 | Scheduler: prossima esecuzione, `next_wake_at`, jitter, spinta, lock | ⏸ |
| Z4 | `POST /system/wake-sync`, `GET /system/next-wake` (F07) | ⏸ attende il punto 33 |
| Z5 | «Aggiornamento prezzi…» | ⏸ attende l'area avvisi e la configurazione pubblica di H |
| Z6b | C-49: la cura | ⏸ attende Z6a e il punto 35 |
| Z7 | Attesa crescente sui 429 | ⏸ attende il punto 34 e il codice d'errore `RATE_LIMITED` di X |

Checkpoint FROZEN a fine Z6a; poi un checkpoint per lotto.

### A — Analisi ✅ (2026-10-14)

> **Note implementazione**: analisi in sola lettura, inviata al coordinatore il 14/10 sera con le decisioni D1–D11.
> Il developer ne ha raccolte cinque nel suo elenco: D2 → punto 31 (🔴, da decidere), D4 → 32, D7 → 33, D9 → 34,
> D10 → 35.
>
> **Fuori pista**: l'app ha rinominato il ramo da `e-alfy-potential-sniffle` a `e-alfy-z-sospensione-e-risveglio`;
> un riavvio dell'app ha interrotto il turno della pausa del 14/10 sera (nessun comando in corso, nessun file toccato);
> l'approvazione del piano nella UI della sessione chiedeva di partire subito, ma vale l'autorizzazione inoltrata dal
> coordinatore: Z1 non è partito.

### A2 — Riverifica su `1e9e567f7` ✅ (2026-10-15)

> **Note implementazione**: HEAD `1e9e567f7`, worktree pulito, porta 6186 libera. Rilette sul codice nuovo tutte le
> righe citate (`grep`, `git diff -U0 459131eb8 HEAD`). I tre cicli sono gli stessi; R ha toccato
> `assets/[id]/+page.svelte` in tre punti (r. 496, 2752, 3538) lontani dai cicli, che scendono di 10 righe. Il backend
> è stato riordinato: scheduler in `services/platform/scheduler/`, asset in `services/assets/`, BRIM in
> `services/brim/`, configurazione in `config/`; il lifespan e i middleware sono ancora in `main.py`. Nessuna run.

## Analisi (aggiornata a `1e9e567f7`)

### 1. Stato reale

**Frontend.** Tre cicli, tutti nelle due pagine degli asset, nessun altro polling di rete (`SyncModalBase` conta in
locale, `updateCheck` gira una volta al login con cache di un'ora, `static/sw.js` serve solo il fallback offline,
nessun EventSource né WebSocket, SvelteKit senza `version.pollInterval`).

| Ciclo | Dove | Ritmo | Guardie | Scheda nascosta |
|---|---|---|---|---|
| C1 lista | `routes/(app)/assets/+page.svelte:439-450` | subito, poi 30 s | `isHeadToday`, `liveAssetIdsKey` | nessun controllo |
| C2 dettaglio, riepilogo | `routes/(app)/assets/[id]/+page.svelte:1481-1513` | subito, poi 30 s | `isHeadToday` | nessun controllo |
| C3 dettaglio, grafico | stesso file `:1977-2083` | 60 s, primo dopo 5 s | provider assegnato | salta il giro, il timer resta acceso |

- C3 non ha la guardia `isHeadToday`: chiede il prezzo anche su un intervallo passato, e `mergeChartPointsIncremental`
  (`:2553`) non taglia sull'intervallo, quindi può aggiungere il punto di oggi a un grafico del passato (Z-1).
- Tutti chiamano `POST /api/v1/assets/prices/current`, che scrive l'OHLC di oggi ed è una mutazione del portafoglio
  (`lib/stores/portfolio/portfolioMutation.ts`): nel dettaglio sono tre scritture al minuto (Z-2). C1 e C2 passano da
  `lib/services/livePriceService.ts`, C3 dal client zodios.
- Stub dell'endpoint in `asset-detail`, `toolbar-width-sweep`, onboarding, `app-start-auth`, `fx-detail`;
  `asset-list.spec.ts` e altri spec della categoria asset non lo stubbano e chiamano i provider veri (conta per C-49).
  Nessuno spec avanza `page.clock` di dieci minuti o più.

**Backend.**

- Scheduler `services/platform/scheduler/`: giro di 60 s a passi di 5 s (`scheduler.py:129-132`), attesa iniziale di
  5 s (`:104`), `am_i_leader()` sul loop (`:108`). Recupera già i giri persi: entro 5 s dall'avvio, entro 60 s da una
  ripresa.
- Lifespan in `main.py:243-334`: lo scheduler parte a `:307-308`; allo spegnimento `await shutdown_tool_executor()`
  (`:313`), `shutdown_event.set()` (`:316`), **`await scheduler_task` senza limite** (`:317`), poi provider, pool BRIM
  con `wait=True` (`:328`), pool quant (`:329`), festività (`:331`), cache (`:334`).
- Nessun concetto di attività dell'utente. Docker a un worker, uvicorn PID 1 via `exec gosu` (`entrypoint.sh`).
- `_run_provider_in_thread` (`services/assets/core.py:90`): `asyncio.to_thread` più `wait_for`; allo scadere il thread
  continua.
- uvicorn 0.52 legge `UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN` (`auto_envvar_prefix`); il default attende per sempre le
  richieste in volo. httpx 0.28 parla col socket Unix di Fly senza dipendenze nuove.
- Nessun codice d'errore comune per i 429; gli errori dello storico finiscono nel log.
- Runner (`scripts/test_runner/_server.py`): grazia 5 s, 30 s con coverage (`:50-51`); avviso «Shared backend ignored
  SIGTERM» a `:329`; l'output del backend passa solo in modalità verbosa (`:274`), che è il default.

### 2. Già fatto o contraddetto

- Già fatto: il recupero dei prezzi dopo un fermo, in background, senza bloccare la UI. Mancano la spinta immediata al
  ritorno dell'utente, «Aggiornamento prezzi…» e `next_wake_at`.
- C-49 diceva «nessun endpoint SSE»: falso, `GET /api/v1/assets/search/stream` è SSE
  (`api/v1/assets/providers.py:156`).
- Il docstring dello scheduler dice che l'elezione del leader gira in un thread; gira sul loop (Z-6).
- Fly: la sospensione dall'interno, senza token, è confermata (`POST http://flaps/v1/apps/$FLY_APP_NAME/machines/$FLY_MACHINE_ID/suspend`
  sul socket `/.fly/api`). Il proxy di Fly chiude una connessione che resta 60 s senza byte (punto 33).

### 3. Lotti e superfici

- **Z1 · Pausa degli aggiornamenti (F26)**: `frontend/src/lib/features/live-updates/` (`activityTracker.ts`,
  `activePolling.svelte.ts`, `LiveUpdatesStatus.svelte`), sottosistema i18n `lib/i18n/liveUpdates/`; C1, C2 e C3
  sull'helper con la stessa cadenza (C3 con `isHeadToday`, D3); la pillola fuori dalla `PageToolbar`, nella riga
  d'intestazione delle due pagine. Test: vitest `front-utility core-unit`, jsdom `front-utility component-unit`, E2E
  `e2e/assets/asset-live-pause.spec.ts` (`front-asset live-pause`). Doc EN: `live-ticker.md`, `user/assets/index.en.md`.
- **Z2 · Attività e sospensione**: `services/platform/sleep_wake/` (`activity.py`, `idle_monitor.py`, `suspend.py`),
  middleware ASGI puro dagli agganci di H; `LIBREFOLIO_IDLE_SUSPEND_MINUTES` (0), `LIBREFOLIO_IDLE_SUSPEND_MODE=none|fly`.
  Test `services sleep-wake`; pagina admin nuova.
- **Z3 · Scheduler**: prossima esecuzione per job (con l'ora legale), `next_wake_at`, jitter per istanza salvato nello
  stato, spinta alla prima richiesta dopo l'inattività, lock condiviso con `wake-sync`, stato «occupato»,
  cancellazione con un limite. Test `services scheduler-next-wake`.
- **Z4 · `wake-sync` e `next-wake`**: router nuovo `api/v1/system_wake.py`; token `LIBREFOLIO_WAKE_TOKEN(_FILE)` (404
  se assente); un solo `wake-sync` alla volta; tolleranza di 120 s; risposta del punto 33; sospensione dopo. Test
  `api system-wake` (PURE); `security-review`.
- **Z5 · «Aggiornamento prezzi…»**: `GET /system/price-refresh`, avviso nell'area di H, `requestPortfolioRefresh()` a
  fine sincronizzazione; `LIBREFOLIO_CLIENT_IDLE_MINUTES` nella configurazione pubblica.
- **Z6 · C-49**: prove (Z6a), poi la cura (Z6b) con un rosso PURE (`services shutdown-budget`).
- **Z7 · 429**: attesa crescente per provider, ritentativi in `next_wake_at` (`services scheduler-backoff`).

### 4. Decisioni

| # | Decisione | Proposta | Stato |
|---|---|---|---|
| D1 | Dove sta «Aggiornamento in pausa» | Locale, vicino al prezzo live; nell'area di H solo «Aggiornamento prezzi…» | proposta |
| D2 | Pausa del client per tutti | Sì, 10 minuti, 0 = mai | **punto 31, 🔴 da decidere** |
| D3 | C3 senza `isHeadToday` | Guardia aggiunta in Z1 dopo un rosso; fusione C2/C3 a X (FE5) | proposta |
| D4 | Il polling conta come presenza | Sì (evita sospensioni a raffica) | punto 32, 🟢 |
| D5 | Sospensione e lavoro in corso | Mai con job, `wake-sync`, recupero o richiesta in volo; un solo worker; pannello con `auto_stop_machines="off"` | proposta |
| D6 | `next_wake_at` | Lo legge il pannello (risposta di `wake-sync`, GET a macchina accesa); opzione metadati della macchina Fly | proposta (§10 n. 10) |
| D7 | Risposta di `wake-sync` oltre 60 s | JSON in streaming con spazi d'attesa | punto 33, 🟢 |
| D8 | Politica dei risvegli (D-19) | Prossimo slot storico; intraday spento di default; per titolo nel backlog; jitter 0 | proposta |
| D9 | Attesa crescente sui 429 | Accesa di default | punto 34, 🟢 |
| D10 | Tempo massimo di spegnimento | Per tutti, circa 8 s, `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS` | punto 35, 🟢 |
| D11 | Configurazione | Solo variabili d'ambiente (`*_FILE` per il token); moduli accanto allo scheduler | proposta |

### 5. Conflitti previsti

H (agganci di `main.py`, lettore dei segreti, configurazione pubblica, area avvisi, `router.py`, `.env.example`,
Dockerfile, `/system/ready`, sola lettura che lascia passare `wake-sync`) · X (le due pagine prima del taglio FE5,
`services/assets/core.py`, `RATE_LIMITED`, `_frontend_asset.py`) · A (import di `SESSION_COOKIE_NAME`) · W (pool BRIM
nella sequenza di spegnimento) · J (solo se C-49 indica gli spawn) · B (Litestream e budget di spegnimento; ripristino
prima dello scheduler) · G (galleria con `page.clock` di dieci minuti o più) · coordinatore (CHANGELOG, nav MkDocs,
`dev.py` e runner se C-49 li tocca).

## Z6a — prove su C-49, senza codice di prodotto

**Obiettivo.** Capire chi trattiene lo spegnimento del backend condiviso oltre la grazia di 5 s del runner
(`_server.py:329`), prima di scegliere la cura (Z6b, punto 35).

**Ipotesi, in ordine.**

1. **H1 · thread dei provider vivi all'uscita.** `asyncio.run` aspetta l'executor fino a 300 s, poi l'atexit di
   `concurrent.futures` unisce i thread senza limite; i thread di `_run_provider_in_thread` sopravvivono ai loro
   timeout (fino a 55-60 s). Gli spec senza stub di `/prices/current` chiamano provider veri.
2. **H2 · richieste in volo.** uvicorn le drena senza limite (SSE della ricerca, provider lenti).
3. **H3 · passi del lifespan senza scadenza** (executor dei tool, pool BRIM con `wait=True`, pool quant, festività).
4. **H4 · altri membri del gruppo di processi** (worker spawn del rischio, build delle festività).
5. **H5 · scrittura della coverage** (solo in modalità coverage: non usata nelle prove).

**Come si legge.** La fase in cui uvicorn resta fermo dice l'ipotesi: «Waiting for connections to close» → H2;
«Waiting for application shutdown» senza «Application shutdown complete» → H3; «Finished server process» seguito
dall'avviso del runner → H1 o H4. I log per unità vanno in `.testLog` (default di `--log-dir`); l'uscita completa di
ogni run in `/tmp/libreFolio_z6a_<gate>_<n>.log`.

**Passi.**

1. Dopo l'avviso di fine finestra del coordinatore: `npm ci` dal lock in `frontend/` (autorizzato il 15/10), poi
   `pipenv run python dev.py front build --debug`.
2. Gate, uno alla volta, con `nice`: `front-asset asset-classification`, `front-asset asset-detail`, poi
   `front-portfolio dashboard` (prima di lanciarlo avviso il coordinatore). L'avviso è intermittente: se non compare,
   ripeto il gate al massimo due volte e registro la frequenza.
3. Verdetto per ipotesi, con le prove; se il log non basta, propongo una diagnostica temporanea (richiede codice:
   serve un via esplicito).
4. Checkpoint FROZEN: porta 6186 libera, nessun file di prodotto toccato.

## Righe nel backlog

Le voci Z-1…Z-6 nella mia sezione di `BACKLOG_POST_1.2.md`; C-49 resta nella sezione C, presa in carico da Z.
