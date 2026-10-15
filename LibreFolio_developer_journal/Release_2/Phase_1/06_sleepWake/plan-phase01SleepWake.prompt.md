# Piano — fase 01, Z · Sospensione e risveglio (F26, F07, C-49)

> Workstream Z della 1.3.0 «Cloud-ready core». Piano generale: [`plan-phase01Release13.prompt.md`](../plan-phase01Release13.prompt.md)
> (§4 «Z · Sospensione e risveglio», §5, §6, §9, §10 n. 10); stato vivo della fase: [README](../README.md); decisioni
> del developer: [`decisioni-analisi-20261014.md`](../decisioni-analisi-20261014.md), punti 31–35; backlog:
> [`BACKLOG_POST_1.2.md`](../../Phase_0/BACKLOG_POST_1.2.md), sezione «Z · Sospensione e risveglio (fase 01)».
>
> - **Sessione**: `Z - Sospensione e risveglio` (`d401e062`), agente `coordinated-workstream`. Coordinatore: «Release 1.3
>   planning» (`928ffa97`).
> - **Ramo**: `e-alfy-z-sospensione-e-risveglio`. Base dell'analisi `459131eb8`; poi `1e9e567f7` (avanzamento
>   veloce del coordinatore, 15/10: riordino di X, W, J, A e H, lotti A–D dei colori, Designer Lab, 1.2.1); poi il merge
>   di `dev_release2` a `8f1abf89e` dopo Z1 (`4618a2116`, 15/10: H CP6, X FE5b, E1, Y1, A5, commit dei colori).
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
| Z6a | C-49: prove senza codice di prodotto (`npm ci` dal lock, `front build --debug`, tre gate nella mia corsia) | ⏳ passo 1 ✅ (15/10); 9 cicli di vita puliti su spec singole; dal 15/10 l'avviso si cerca nelle run di categoria del coordinatore; lettura del codice nel disegno di Z6b |
| Z1 | Pausa degli aggiornamenti nel frontend (F26) | ✅ 15/10: commit `74d028ec6` (journal `a6199d0e7`); merge di base `4618a2116` con i cancelli d'ingresso verdi; FROZEN di ingresso al coordinatore |
| Z2 | Attività dell'utente e sospensione su Fly (F26, backend) | ⏸ attende gli agganci di H (punto 32 deciso il 15/10) |
| Z3 | Scheduler: recupero immediato al risveglio e lock condiviso con `wake-sync` (`next_wake_at` e jitter nel backlog, punto 33) | ⏸ attende lo scheduler spostato da H |
| Z4 | `POST /system/wake-sync` (F07): token, risposta in streaming; niente `next-wake` (punto 33) | ⏸ attende gli agganci di H |
| Z5 | «Aggiornamento prezzi…» | ⏸ attende l'area avvisi e la configurazione pubblica di H |
| Z6b | C-49: la cura | autorizzato il 15/10; **parte 1 ✅ entrata** (`000090aaf`: variabile, drenaggio da `entrypoint.sh` e `dev.py server`, watchdog e scadenza non ancora cablati, grazie a 10 s); parte 2 (cablaggio in `app_lifespan.py`, test di processo, ciclo vero, doc) allo SHA di CP2b di H — sezione «Z6b — spegnimento con un tempo massimo» |
| Z7 | Attesa crescente sui 429, nello scheduler, nelle richieste dal vivo e nel polling del frontend (punto 34) | 📝 disegnato il 15/10 (sezione «Z7 — disegno»), decisioni D-Z7 prese dal coordinatore; **Z7a ✅ 15/10** (primitiva, configurazione, servizio, test verdi; sezione «Z7a»); poi X con il contratto `RATE_LIMITED` (X1–X8), poi Z7b scheduler e Z7c frontend |

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
  ritorno dell'utente e «Aggiornamento prezzi…» (`next_wake_at` è uscito dal perimetro con il punto 33: Z-7).
- C-49 diceva «nessun endpoint SSE»: falso, `GET /api/v1/assets/search/stream` è SSE
  (`api/v1/assets/providers.py:156`).
- Il docstring dello scheduler dice che l'elezione del leader gira in un thread; gira sul loop (Z-6).
- Fly: la sospensione dall'interno, senza token, è confermata (`POST http://flaps/v1/apps/$FLY_APP_NAME/machines/$FLY_MACHINE_ID/suspend`
  sul socket `/.fly/api`). Il proxy di Fly chiude una connessione che resta 60 s senza byte (punto 33).

### 3. Lotti e superfici

- **Z1 · Pausa degli aggiornamenti (F26)**: `frontend/src/lib/features/live-updates/` (`cadence.ts`,
  `activityTracker.ts`, `activePolling.ts`, `LiveUpdatesStatus.svelte`), sottosistema i18n `lib/i18n/liveUpdates/`;
  C1 sull'helper ogni 60 s, C2 e C3 fusi in un ciclo ogni 30 s con la guardia `isHeadToday` (decisione 31); la pillola
  fuori dalla `PageToolbar`, nella riga d'intestazione delle due pagine. Test: vitest `front-utility core-unit`, jsdom
  `front-utility component-unit`, E2E `e2e/assets/asset-live-pause.spec.ts` (`front-asset live-pause`). Doc EN:
  `live-ticker.md`, `user/assets/index.en.md`.
- **Z2 · Attività e sospensione**: `services/platform/sleep_wake/` (`activity.py`, `idle_monitor.py`, `suspend.py`),
  middleware ASGI puro dagli agganci di H; `LIBREFOLIO_IDLE_SUSPEND_MINUTES` (0), `LIBREFOLIO_IDLE_SUSPEND_MODE=none|fly`.
  Test `services sleep-wake`; pagina admin nuova.
- **Z3 · Scheduler** (ripianificato il 15/10, punto 33): recupero immediato dei giri persi alla prima richiesta dopo
  l'inattività o un risveglio, senza aspettare il giro di 60 s; lock condiviso con `wake-sync` (un job alla volta); stato
  «occupato» per Z2 e cancellazione con un limite per Z6b. Fuori, nel backlog (Z-7): la prossima esecuzione per job,
  `next_wake_at` e il jitter, «quando il pannello terrà un calendario». Test `services scheduler-catchup`.
- **Z4 · `wake-sync`** (ripianificato il 15/10, punto 33): `POST /system/wake-sync` in un router nuovo
  `api/v1/system_wake.py`, attivo solo con `LIBREFOLIO_WAKE_TOKEN(_FILE)` (senza token, 404; token sbagliato, 401);
  esegue subito i lavori in scadenza e risponde con l'esito, in streaming, uno spazio ogni ~15 s per il proxy di Fly e
  alla fine un JSON estendibile: l'esito complessivo e un elenco generico di job (nome, esito, durata, elementi), così
  un job di notifiche futuro è solo un job in più e `next_wake_at` si aggiunge dopo senza rompere niente; un solo
  `wake-sync` alla volta; sospensione dopo la risposta (Z2). Niente `GET /system/next-wake`. Lo chiamerà il pannello del
  cloud, anche a turno ogni 2 ore per le notifiche future (punto 32). Test `api system-wake` (PURE); `security-review`.
- **Z5 · «Aggiornamento prezzi…»**: `GET /system/price-refresh`, avviso nell'area di H, `requestPortfolioRefresh()` a
  fine sincronizzazione; `LIBREFOLIO_CLIENT_IDLE_MINUTES` nella configurazione pubblica.
- **Z6 · C-49**: prove (Z6a), poi la cura (Z6b) con un rosso PURE (`services shutdown-budget`).
- **Z7 · 429** (punto 34): attesa crescente per fornitore, nello scheduler e nelle richieste dal vivo; il polling del
  frontend rispetta `retry_after` e rallenta in modo esponenziale sugli errori; i ritentativi dello scheduler nel suo
  giro (`services scheduler-backoff`). Disegno e contratto per X: sezione «Z7 — disegno» (15/10); la dipendenza si
  rovescia, perché è X ad aspettare la primitiva di Z7a.

### 4. Decisioni

| # | Decisione | Proposta | Stato |
|---|---|---|---|
| D1 | Dove sta «Aggiornamento in pausa» | Locale, vicino al prezzo live; nell'area di H solo «Aggiornamento prezzi…» | proposta |
| D2 | Pausa del client per tutti | Sì, 10 minuti, 0 = mai | ✅ deciso (punto 31, 15/10): **2 minuti**, ripresa automatica, lista 60 s, dettaglio 30 s — sezione «Z1» |
| D3 | C3 senza `isHeadToday` | Guardia aggiunta in Z1 dopo un rosso; fusione C2/C3 a X (FE5) | in Z1: la fusione la fa Z, coordinata con X dal coordinatore (punto 31) |
| D4 | Il polling conta come presenza | Sì (evita sospensioni a raffica) | ✅ deciso (punto 32, 15/10): sì; sospensione dopo **5 minuti** senza richieste come default del cloud |
| D5 | Sospensione e lavoro in corso | Mai con job, `wake-sync`, recupero o richiesta in volo; un solo worker; pannello con `auto_stop_machines="off"` | confermato dal punto 32: «mai mentre c'è lavoro in corso» |
| D6 | `next_wake_at` | Lo legge il pannello (risposta di `wake-sync`, GET a macchina accesa); opzione metadati della macchina Fly | ✅ deciso (punto 33, 15/10): **per ora non si fa**, nel backlog (Z-7); la risposta resta estendibile |
| D7 | Risposta di `wake-sync` oltre 60 s | JSON in streaming con spazi d'attesa | ✅ deciso (punto 33, 15/10): streaming, uno spazio ogni ~15 s |
| D8 | Politica dei risvegli (D-19) | Prossimo slot storico; intraday spento di default; per titolo nel backlog; jitter 0 | superata dal punto 33: senza calendario, i risvegli li decide il pannello; jitter nel backlog (Z-7) |
| D9 | Attesa crescente sui 429 | Accesa di default | ✅ deciso (punto 34, 15/10): sì, nello scheduler **e** nel polling del frontend (Z7 si allarga) |
| D10 | Tempo massimo di spegnimento | Per tutti, circa 8 s, `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS` | ✅ deciso (punto 35, 15/10): sì, per tutti |
| D11 | Configurazione | Solo variabili d'ambiente (`*_FILE` per il token); moduli accanto allo scheduler | proposta |

> **Decisione 32 del developer, alla lettera** (chat, 15/10 14:46, inoltrata dal coordinatore): «riguardo lo scheduler
> mentre dorme l'istanza, è corretto che al risveglio subito ci pensa lui ad aggiornare, lo avevamo progettato sin
> dall'inizio così. serve però lasciarsi aperta la possibilità che il risveglio possa essere chiamato anche
> esternamente, magari a round robin ogni 2 ore, quando implementeremo un sistema di notifiche e avvisi, per dare modo
> alle istanze di elaborare i dati nuovi e capire se ci sono notifiche da mandare». Dalla sua nota nel file delle
> decisioni: «il backend direi che deve spegnersi o comnque andare a riposo, dopo 5 min dall'ultimo pacchetto ricevuto».
>
> Per Z2–Z4 (lettura del coordinatore): sospensione dopo 5 minuti senza richieste dell'utente come default del cloud,
> mai con lavoro in corso, il polling conta come presenza (con la pausa di 2 minuti del 31 il ciclo sospensione e
> risveglio non si forma); al risveglio lo scheduler recupera da solo i giri persi, come oggi; `wake-sync` resta il punto
> d'ingresso dei risvegli esterni e deve reggere un giro a turno ogni 2 ore fatto dal pannello: «esegui i job in
> scadenza, rispondi con l'esito e con `next_wake_at`». Un job di notifiche sarà un job in più: il contratto della
> risposta elenca i job in modo generico, non solo i prezzi.
>
> **Decisione 33 del developer, alla lettera** (chat, 15/10 14:50, dopo una spiegazione): «ok va bene, aggiorna il
> documento, solo, il next_wakeup per ora non serve, giusto, è una cosa per il futuro quando servirà». Lettura del
> coordinatore: `wake-sync` è un endpoint di ogni istanza, attivo solo con `LIBREFOLIO_WAKE_TOKEN` (senza token, 404);
> esegue subito i lavori in scadenza e risponde con l'esito in streaming, uno spazio ogni ~15 s; `next_wake_at` per ora
> non si fa (niente campo, niente `GET next-wake`); di Z3 restano il recupero immediato e il lock condiviso con
> `wake-sync`; prossima esecuzione per job e jitter nel backlog; la risposta resta un JSON estendibile. Z3 e Z4
> ripianificati sopra (§3); al prossimo checkpoint dirò al coordinatore cosa cambia nei lotti.

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

> **Fuori pista** (15/10, prima delle run): il runner avvia il backend condiviso con `verbose=False`
> (`scripts/test_runner/_cli.py:596-599`), quindi il suo stdout e stderr vanno in `/dev/null` (`_server.py:274`): le
> righe di uvicorn sulle fasi dello spegnimento non arrivano in nessun log. Senza toccare codice restano tre fonti:
> (1) il log del runner con i tempi (la riga «Shared backend ignored SIGTERM»); (2) il log dell'app nel data-dir della
> corsia, `/tmp/librefolio-r13-z/logs/librefolio.log` (structlog, ISO in UTC, livello DEBUG in test): «Shutting down
> LibreFolio» compare solo dopo il drenaggio di uvicorn e dopo `shutdown_tool_executor`, quindi la sua assenza indica
> H2 o l'executor dei tool; (3) l'osservatore in sola lettura del gruppo di processi (membri, thread, socket in entrata
> e in uscita, `sample` dei superstiti). Le specifiche per cui servisse il log di uvicorn richiederebbero una modifica
> del runner (superficie del coordinatore): solo con un via esplicito.
>
> Esposizione delle tre spec (grep in sola lettura): `asset-classification` apre `/assets` senza stub di
> `/prices/current`, quindi il poll della lista chiama i provider veri (H1, H2); `asset-detail` stubba l'endpoint solo
> in alcuni test e usa sync e rischio (H1–H4); `dashboard` non chiama né provider né rischio: se l'avviso compare lì da
> solo, la causa non sono i thread dei provider.
>
> Regole del carico del 15/10 (coordinatore): Z è una corsia «altra», quindi ogni E2E richiede il suo via.

**Passi.**

1. Dopo l'avviso di fine finestra del coordinatore: `npm ci` dal lock in `frontend/` (autorizzato il 15/10), poi
   `pipenv run python dev.py front build --debug`. ✅ 2026-10-15

   > **Note implementazione**: `npm ci` alle 13:05, exit 0, 433 pacchetti in 17 s (`/tmp/libreFolio_z6a_npm_ci.log`);
   > l'errore di partenza era `frontend/node_modules/.bin/vitest: No such file or directory`. npm 11 avvisa che gli
   > script d'installazione di 5 pacchetti (`esbuild`, `fsevents`, `es5-ext`) non sono nella sua `allowScripts`: la build
   > funziona comunque. `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc nice -n 10 pipenv run python dev.py front build --debug`:
   > exit 0, vite 1 min 18 s + 1 min 52 s, svelte-check senza errori (`/tmp/libreFolio_z6a_front_build.log`). Worktree
   > pulito dopo entrambi.
   >
   > Strumenti delle prove, fuori dal repo: `/tmp/libreFolio_z6a_watch.sh` osserva in sola lettura il gruppo di processi
   > del backend della corsia (membri, thread, socket TCP; un `sample` di macOS per ogni superstite a +2 s dallo
   > spegnimento); `/tmp/libreFolio_z6a_run.sh <categoria> <azione> <n>` lancia un gate con `--workers 2`, l'osservatore e
   > il log completo con i tempi al millisecondo (`/tmp/libreFolio_z6a_<azione>_<n>.log`, `PYTHONUNBUFFERED=1` perché le
   > righe arrivino in ordine).
   >
   > **Fuori pista**: alle 13:10 il coordinatore ha aperto la finestra delle dipendenze (il developer installa
   > `cryptography` nell'ambiente condiviso): nessun comando Python fino al suo via. La build era già finita; nessun
   > comando in corso.
2. Gate, uno alla volta, con `nice`: `front-asset asset-classification`, `front-asset asset-detail`, poi
   `front-portfolio dashboard` (prima di lanciarlo avviso il coordinatore). L'avviso è intermittente: se non compare,
   ripeto il gate al massimo due volte e registro la frequenza.

   > **Via del coordinatore** (15/10, 13:38): «Ti do un via unico per le tre, di fila, con `nice -n 15`, `--workers 2`
   > e al massimo due ripetizioni per gate. Non serve che mi scrivi a ogni avvio: mandami un messaggio solo alla fine,
   > con le prove. Se alla partenza il carico (`uptime`) è sopra 30, aspetta qualche minuto.»

   | Gate | Run | Inizio | Esito | Avviso «ignored SIGTERM» | Spegnimento osservato | Carico all'avvio (1 min) |
   |---|---|---|---|---|---|---|
   | `front-asset asset-classification` | 1 | 13:39 | 4/4 in 28 s; invocazione 3 min 27 s | no | gruppo vuoto 338 ms dopo la chiusura del listener; nel log dell'app 0,3 s fra «Shutting down LibreFolio» e «All caches closed on shutdown» | 27,99 |

   > **Note implementazione** (run 1): il backend condiviso ha impiegato 2 min a rispondere (13:39:00 → 13:40:59),
   > di cui 1 min 50 s prima di «Starting LibreFolio»: è `dev.py server` che prepara frontend e documentazione prima di
   > uvicorn, non lo spegnimento. Popolamento del DB (31 s) e utenti (25 s) dopo l'avvio del backend, nello stesso ciclo
   > di vita (un solo ciclo nell'osservatore). Un solo worker uvicorn per 2 client.
   >
   > **Fuori pista**: dalle 13:43 il carico della macchina è salito a 59–265 (1 min), per lavoro di altre corsie. La run 2
   > non è partita: il wrapper `/tmp/libreFolio_z6a_when_calm.sh` aspettava il carico ≤ 30. Alle 13:55 il coordinatore ha
   > rimandato le prove E2E finché non libera lui uno slot: wrapper fermato, nessun processo di Z6a attivo, porta 6186
   > libera.
3. Verdetto per ipotesi, con le prove; se il log non basta, propongo una diagnostica temporanea (richiede codice:
   serve un via esplicito).

   > **Note implementazione** (15/10, ~16:10): oltre alla run 1 del gate 1, i cicli di vita del backend della corsia
   > sono venuti dalle run verdi di Z1 (8) e dal merge di base (1), tutti puliti. Visto che sulle spec singole l'avviso
   > non si riproduce, con il coordinatore si è cambiata strategia: lui cerca `Shared backend ignored SIGTERM for` nelle
   > sue run di categoria a ogni ingresso, e le prove attive restano per uno slot libero con poco carico. Il verdetto
   > provvisorio viene dalla lettura del codice (uvicorn 0.52.4): con SIGTERM l'ipotesi H1 è esclusa, perché uvicorn
   > rilancia il segnale alla fine e il processo esce senza aspettare i thread; restano H2 (la più probabile), H3 e H4.
   > Dettagli e cura: sezione «Z6b — disegno».
4. Checkpoint FROZEN: porta 6186 libera, nessun file di prodotto toccato.

## Righe nel backlog

Le voci Z-1…Z-7 nella mia sezione di `BACKLOG_POST_1.2.md`; C-49 resta nella sezione C, presa in carico da Z.

## Z1 — pausa degli aggiornamenti (F26), autorizzato il 15/10

> **Decisione 31 del developer, alla lettera** (inoltrata dal coordinatore il 15/10 alle 14:18): «mi pare un contro
> senso che in asset global sia ogni 30 e in detail ogni 60, al più lo invertirei. Comunque sono daccordo che a
> schermata nascosta e dopo anche solo 2 min di mouse fermo, la richiesta di aggiornamenti venga mandata in pausa, ma
> appena la schermata ritorna attiva o il mouse si muove, se il tempo passato supera la soglia, mandiamo subito la
> richiesta senza scrivere nulla. e questo per quanto riguarda l'aggiornamento attivo, triggerato dall'utente mentre è
> connesso»
>
> Lettura del coordinatore, che seguo: pausa a scheda nascosta e dopo **2 minuti** senza mouse né tastiera; ripresa
> **automatica** (scheda di nuovo visibile o mouse mosso): se dall'ultima richiesta è passato più dell'intervallo, una
> richiesta subito; la pillola «Aggiornamento in pausa» è un segnale, non un comando; intervalli invertiti: lista
> **60 s**, dettaglio **30 s**, con C2 e C3 fusi in un ciclo solo (la fusione è di X, FE5: la coordina il coordinatore).
> «Senza scrivere nulla» = senza che l'utente debba fare niente; il coordinatore lo sta chiedendo al developer.
>
> Autorizzazione: «Z1 è autorizzato con le regole del 31 qui sopra. Prima i rossi; per Vitest, svelte-check ed E2E
> chiedimi lo slot, come al solito.» Decisioni 34 (attesa crescente anche nel polling del frontend) e 35 (spegnimento
> con tempo massimo per tutti): lotti Z7 e Z6b.
>
> Risposte del coordinatore (15/10, 14:37): il developer conferma la lettura del 31 («senza scrivere nulla» vuol dire
> che la ripresa parte da sola, senza cliccare niente); Vitest su un file singolo libero con `nice -n 15`, lo slot serve
> solo all'E2E; la voce di `STATUS_TONES` la chiede lui al coordinatore dei colori: fino alla risposta le classi della
> pillola stanno in un punto solo, nel componente.

### Contratto

File nuovi in `frontend/src/lib/features/live-updates/`:

- `cadence.ts` — le costanti della decisione 31: `LIVE_UPDATES_IDLE_MS = 120_000`,
  `ASSET_LIST_LIVE_INTERVAL_MS = 60_000`, `ASSET_DETAIL_LIVE_INTERVAL_MS = 30_000`.
- `activityTracker.ts` — `createActivityTracker({target, document, now})` e `getActivityTracker()` (uno per pagina,
  creato al primo uso). Ascolta `pointermove`, `pointerdown`, `keydown`, `wheel`, `touchstart` sul `target` (passivi) e
  `visibilitychange` sul `document`. Espone `lastActivityAt()`, `isVisible()`, `touch()` (segna attività adesso),
  `subscribe(listener)` con i segnali `'activity' | 'visible' | 'hidden'` (ritorna la funzione per disiscriversi),
  `dispose()`. Il ritorno alla scheda (`visible`) conta come attività.
- `activePolling.ts` — `startActivePolling({run, intervalMs, idleMs?, initialDelayMs?, onstatechange?, tracker?})`
  → `{state, pollNow(), stop()}`; stati `'running' | 'paused-idle' | 'paused-hidden' | 'stopped'`.
    1. All'avvio con la scheda visibile: `running`, `tracker.touch()`, primo giro dopo `initialDelayMs` (default 0) da un
       timer, mai dentro la chiamata a `startActivePolling` (così non entra nel tracciamento di un `$effect`). Con la
       scheda nascosta: `paused-hidden`, nessun giro.
    2. I giri partono ogni `intervalMs` dall'inizio del precedente; se un giro è ancora in volo quando scade il
       successivo, quel giro salta (niente sovrapposizioni).
    3. Inattività: nessun giro parte a `lastActivityAt + idleMs` o dopo, finché non arriva un input; lo stato passa a
       `paused-idle` alla soglia. `idleMs = 0` → mai in pausa per inattività.
    4. Scheda nascosta: `paused-hidden` subito, timer cancellati; un giro in volo finisce, nessuno nuovo.
    5. Ripresa (input in `paused-idle`, `visible` in `paused-hidden`): `running`; se dall'inizio dell'ultimo giro è
       passato almeno `intervalMs` (o non c'è stato nessun giro), un giro subito; altrimenti il prossimo
       all'inizio dell'ultimo più `intervalMs`.
    6. `pollNow()`: segna attività, un giro subito (se nessuno è in volo), la cadenza riparte da lì; riprende se in pausa.
    7. `stop()`: `stopped`, nessun giro e nessun ascoltatore dopo; la fine di un giro in volo non cambia nulla.
    8. Un errore di `run` (eccezione o promessa rifiutata) non ferma la cadenza né cambia lo stato.
    9. `onstatechange` riceve lo stato iniziale e ogni cambio.
- `LiveUpdatesStatus.svelte` — prop `state`; solo in `paused-idle` mostra la pillola `data-testid="live-updates-status"`
  con `data-state`, `role="status"`, testo `liveUpdates.paused`, `title` `liveUpdates.pausedHint`; nessun pulsante.
  Colori dai ruoli: una voce nuova in `STATUS_TONES` (R), `liveUpdates: {paused: 'bg-lf-neutral text-lf-secondary'}`,
  senza `dark:` e senza altre classi di colore legacy sull'elemento (G3), come chiesto dal coordinatore dei colori il
  15/10 alle 14:40; contrasto 5,8:1 in chiaro e in scuro. Il chip del tipo accanto resta grigio legacy finché l'ondata
  dei colori non migra la pagina di dettaglio: differenza voluta e temporanea.
- i18n: sottosistema nuovo `frontend/src/lib/i18n/liveUpdates/` (`prefixes.txt` + 4 lingue).

Pagine (solo i cicli di polling e il punto della pillola):

- Lista (`routes/(app)/assets/+page.svelte`): C1 sull'helper ogni 60 s; `refreshLivePricesNow()` → `pollNow()`; la
  radice `assets-page` pubblica `data-live-updates` con lo stato; la pillola accanto al titolo.
- Dettaglio (`routes/(app)/assets/[id]/+page.svelte`): C2 e C3 fusi in un ciclo ogni 30 s, con la guardia di C2
  (`isHeadToday` e asset caricato); una richiesta per giro alimenta il riepilogo (logica di C2) e la testa del grafico
  (logica di C3: solo con un provider e senza un caricamento in corso); la radice `asset-detail-page` pubblica
  `data-live-updates`; la pillola nella riga dei chip dell'intestazione.

### Test (test-author), poi i rossi

- Vitest node `activityTracker.test.ts`, `activePolling.test.ts` (timer finti, ambiente iniettato) in
  `front-utility core-unit`; jsdom `LiveUpdatesStatus.test.ts` in `front-utility component-unit`.
- E2E `frontend/e2e/assets/asset-live-pause.spec.ts`, azione nuova `front-asset live-pause`: `/prices/current` stubbato
  e contato, `page.clock`; lista: un giro ogni 60 s, pausa dopo 2 min senza input e ripresa con una richiesta subito,
  pausa a scheda nascosta e ripresa; dettaglio: una sola richiesta ogni 30 s, pausa per inattività e ripresa, nessuna
  richiesta con un intervallo che finisce nel passato (Z-1).
- Rossi attesi sul codice di oggi: le cadenze (lista 30 s, dettaglio 30 s + 60 s), le richieste durante la pausa,
  quelle con un intervallo passato, la pillola assente; Vitest rosso perché i moduli non esistono.

### Passi di Z1

1. Test scritti da test-author ✅ 2026-10-15

   > **Note implementazione**: `activityTracker.test.ts` (7 test), `activePolling.test.ts` (27 test, le regole 1–11
   > e le costanti), `LiveUpdatesStatus.test.ts` (jsdom, 4 test), `e2e/assets/asset-live-pause.spec.ts` (6 test, solo
   > desktop: (a)–(c) lista, (d)–(f) dettaglio); registrati in `_frontend_utility.py` (`core-unit`, `component-unit`) e
   > in `_frontend_asset.py` (azione nuova `live-pause`). L'E2E ferma l'orologio della pagina dopo la richiesta
   > d'apertura e lo muove solo con `runFor`; uno script iniettato segna l'ora di ogni richiesta sull'orologio della
   > pagina; movimento ridotto emulato (il marquee dei nomi lunghi gira con `requestAnimationFrame`); `/prices/current`
   > stubbato, niente scritture. Riletti da me: lo stato di `displayCurrency` e `assetInfo` cambia in un blocco solo
   > (`loadAssetInfo`), quindi l'apertura del dettaglio fa una richiesta sola; il negozio delle date legge l'URL al
   > caricamento, quindi il test (f) sull'intervallo passato è valido.
   >
   > **Fuori pista**: test-author ha usato due volte `python3` di sistema come strumento di testo (leggere il sorgente
   > dell'orologio di Playwright in un file di `/tmp`, poi cancellato; una sostituzione nella sua spec), contro la
   > regola che gli avevo dato; nessun effetto sull'ambiente condiviso. Ha formattato a mano: `format:check` e
   > `check-orphans` entrano nella run di controllo.
2. Rossi ✅ 2026-10-15

   > **Note implementazione** (Vitest, 15/10, file singoli con `nice -n 15`): i tre file falliscono come atteso
   > con «Cannot find module './activityTracker'», «./activePolling», «Failed to resolve import
   > "./LiveUpdatesStatus.svelte"» (`/tmp/libreFolio_z1_red_vitest_*.log`).
   >
   > E2E (slot del coordinatore, 15:11, carico 26): `/bin/bash /tmp/libreFolio_z6a_run.sh front-asset live-pause red1`,
   > cioè `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc nice -n 15 pipenv run python dev.py test --test-port 6186
   > --data-dir /tmp/librefolio-r13-z --workers 2 front-asset live-pause`: 6 falliti su 6 in 3 min 27 s, tutti sui conteggi
   > delle richieste, cioè sul comportamento di oggi (`/tmp/libreFolio_z6a_live-pause_red1.log`):
   > (a) e (b) la lista chiede a +0 e +30 s (ogni 30 s, non 60); (c) la lista continua ogni 30 s a scheda nascosta
   > (+0…+150 s, 6 richieste); (d) ed (e) il dettaglio chiede a +0 e +4,8/4,9 s (il ciclo di 60 s con il riscaldamento di
   > 5 s); (f) un intervallo passato riceve richieste a +2,1 e +57,1 s (il ciclo di 60 s senza `isHeadToday`). C-49:
   > spegnimento pulito anche qui, gruppo vuoto 128 ms dopo la chiusura del listener.
3. Implementazione ✅ 2026-10-15

   > **Note implementazione**: file nuovi `cadence.ts`, `activityTracker.ts`, `activePolling.ts`,
   > `LiveUpdatesStatus.svelte` in `frontend/src/lib/features/live-updates/`; sottosistema i18n
   > `frontend/src/lib/i18n/liveUpdates/` (`prefixes.txt`, 2 chiavi × 4 lingue); voce `STATUS_TONES.liveUpdates` in
   > `lib/theme/toneClasses.ts` (autorizzata dal coordinatore dei colori). Lista: C1 sull'helper ogni 60 s,
   > `refreshLivePricesNow()` → `pollNow()`, `data-live-updates` sulla radice, pillola accanto al titolo (fuori
   > dall'`h2`), `untrack` tolto dagli import. Dettaglio: C2 e C3 fusi in un effetto e una richiesta per giro
   > (`pollLivePriceOnce` → `applyLiveSummary` con la logica di C2, `applyLiveChartHead` con quella di C3 e il suo
   > perché), guardia `isHeadToday` per entrambi, `data-live-updates` sulla radice, pillola in fondo alla riga dei chip
   > dell'intestazione; `fetchCurrentPrices` non serve più al dettaglio.
   >
   > Controlli (`nice -n 15`, file singoli liberi): Vitest verdi — `activityTracker` 19/19, `activePolling` 28/28,
   > `LiveUpdatesStatus` 6/6 — e il cancello dei colori `src/themeRoles.gate.test.ts` 36/36 (R3: file nuovi senza
   > classi legacy; G1–G3); Prettier pulito sui file toccati; `dev.py i18n check` verde (strict, 4394 chiavi);
   > `dev.py test check-orphans` verde (122 spec, 394 unit, tutti raggiungibili da `all`).
   >
   > **Fuori pista**: un riparo in più nel dettaglio, dentro i cicli: una risposta che arriva dopo che l'effetto è
   > ripartito (valuta cambiata, altro asset) non scrive più (`isCurrent`); prima C2 poteva mostrare un prezzo convertito
   > nella valuta vecchia. La radice del dettaglio è andata a capo per Prettier (attributo nuovo oltre la larghezza).
4. Verdi E2E, svelte-check e codice morto ✅ 2026-10-15 (slot pesante 1 del coordinatore, 15:20–15:47)

   > **Note implementazione** (`nice -n 15`, `--workers 2`, una alla volta, tramite `/tmp/libreFolio_z6a_run.sh` con
   > l'osservatore): `front-asset live-pause` **6/6 verde** in 31 s (invocazione 3 min 45 s; nessun «page timer
   > error»); regressione `front-asset asset-list` 28/28 (2 min 05 s), `front-asset asset-detail` 33/33 (3 min 12 s),
   > `front-utility toolbar-width-sweep` 24/24 (6 min 09 s), `front-portfolio dashboard-cache` 6/6 (3 min 44 s).
   > `dev.py front check`: svelte-check 0 errori, 0 avvisi. `dev.py lint --dead-code --scope frontend`: esce 1 per
   > reperti tutti fuori da Z1 (2 file, 19 export, 28 tipi, 4 devDependencies, 20 dipendenze non elencate; nessuno nei
   > file toccati). Spegnimento del backend pulito in tutte le run (gruppo vuoto dopo 0,09–2,7 s; le due spec degli
   > asset le più lente, 2,3–2,7 s, le più vicine alla grazia di 5 s del runner: dato per C-49).
   >
   > Non eseguiti in questo slot: `mkdocs build` e `check-links` (servono uno slot), le run di categoria, le altre spec
   > che toccano il polling (`risk-lab`, `default-currency`, `onboarding-guides`, `app-start-auth`, che lo stubbano o lo
   > tengono in attesa: alle run di categoria all'ingresso, per decisione del coordinatore), il progetto mobile.
   >
   > **Fuori pista**: nella fusione la guardia del ciclo è quella del vecchio riepilogo (`isHeadToday` e asset caricato),
   > che non guardava il fornitore: un asset manuale chiede ancora il prezzo ogni 30 s (Z-8 nel backlog). Il grafico
   > convertito in un'altra valuta si ricarica intero a ogni tick con prezzo cambiato, ora ogni 30 s invece di 60:
   > conseguenza della decisione 31, invariata la logica.
5. Documentazione EN (docs-writer) ✅ 2026-10-15

   > **Note implementazione**: `developer/frontend/components/features/live-ticker.md` (tabella dei cicli, sezioni
   > lista e dettaglio, sezione nuova «pause and resume» con il tracker, l'helper, gli stati, `data-live-updates`, la
   > pillola e il perché del timer; «How it is tested»; ancore esistenti mantenute), `user/assets/index.en.md` (il punto
   > «Live prices»), `developer/frontend/components/index.md` (la riga di Live Prices diceva 30 s e 60 s),
   > `developer/frontend/i18n.md` (sottosistemi da 18 a 19, riga `liveUpdates`). Restano indietro le traduzioni del
   > punto «Live prices» in `user/assets/index.{it,fr,es}.md` (riga 59): decisione del coordinatore. Build e
   > `check-links` nella run di controllo.
   >
   > **Fuori pista**: anche docs-writer ha usato una volta `python3 -c` di sistema, in sola lettura, per leggere un
   > valore JSON.
6. Merge di base e cancelli d'ingresso ✅ 2026-10-15

   > **Note implementazione**: il coordinatore ha committato Z1 (`74d028ec6`, `feat(assets): pause live prices when
   > idle`; journal `a6199d0e7`) e aperto il merge di `dev_release2` a `8f1abf89e` (H CP6, X FE5b, E1, Y1, A5, commit
   > del programma colori). Due conflitti, risolti tenendo i due lati. In `developer/frontend/components/index.md`,
   > rispetto alla base del merge, ogni lato aveva cambiato una riga sola: Authentication viene dal loro (E1, le pagine
   > dei link dell'account), Live Prices dal mio. In `scripts/test_runner/_frontend_utility.py`: in core-unit le loro 5
   > voci e le mie 2, in component-unit `InstanceBlockedPage` e `LiveUpdatesStatus`; `py_compile` ok. Le traduzioni del
   > punto «Live prices» in `user/assets/index.{it,fr,es}.md:59` sono riscritte a mano sulla frase EN, con le etichette
   > dell'app («Aggiornamento in pausa», «Mises à jour en pause», «Actualizaciones en pausa»), poi
   > `dev.py mkdocs translate-stamp --file user/assets/index.en.md` (md5 `75048ee4` → `dd8e5487`, it, fr ed es timbrati
   > in `mkdocs_src/aphra-pipeline/.translate-hashes.json`). Merge committato dal coordinatore: `4618a2116`.
   >
   > Cancelli sull'albero unito, uno alla volta, con `nice -n 15`: `dev.py api sync` exit 0 in 23 s, nessun file
   > tracciato cambiato; `dev.py front check` exit 0, svelte-check 0 errori e 0 avvisi; Vitest dei tre file 19/28/6, più
   > `themeRoles.gate` 36/36 (il merge porta commit dei colori, il gate non è cambiato); `front-asset live-pause`
   > **6/6** in 24,5 s (invocazione 3 min 42 s, con la build del frontend rifatta all'avvio del backend, non
   > strumentata); `dev.py mkdocs build` exit 0 in 42 s, nessun avviso, 3036 URL relativi risolti;
   > `dev.py mkdocs check-links` exit 0, 95 link validi e gli 8 risolti a runtime di sempre. Porta 6186 libera alla
   > fine. Log in `/tmp/libreFolio_z1merge_*.log` e `/tmp/libreFolio_z6a_live-pause_merge1*.log`.
   >
   > Dato per C-49: nono ciclo di vita del backend della corsia, pulito. Nessun avviso «ignored SIGTERM», gruppo di
   > processi vuoto 123 ms dopo la chiusura del listener, 0,8 ms fra «Shutting down LibreFolio» e «All caches closed on
   > shutdown».
   >
   > Per Z2–Z4, dal codice unito: `backend/app/config/` è l'unica sede delle variabili d'ambiente (un modulo per
   > proprietario, `config/platform.py` di H); il lettore dei segreti `NAME_FILE` c'è (`env_secret`, `read_secret_file`
   > in `config/__init__.py`) e `secrets_set_twice` copre già ogni `LIBREFOLIO_*`; lo scheduler è in
   > `services/platform/scheduler/` (con `leader.py`). Agganci per il ciclo di vita e per il middleware ancora no:
   > `main.py` chiama `add_middleware` direttamente.
   >
   > **Fuori pista**: alle 15:56 il carico (1 min) era salito a 87; prima della spec E2E ho aspettato che tornasse sotto
   > 65, il livello del via del coordinatore (soglia mia): è partita alle 15:57 a 38,8. Nel merge
   > `frontend/package.json` e il lock cambiano solo la versione della radice (1.1.0 → 0.0.0): `node_modules` resta
   > valido, nessun `npm ci`.

## Z7 — disegno: attesa crescente sui 429 (15/10, prima del codice)

> **Via del coordinatore** (15/10 ~16:10): «Va bene: disegno di Z7 adesso, poi quello di Z6b. Quando il contratto di
> `RATE_LIMITED` è pronto, me lo giri e lo assegno a X.» Solo disegno, nessun codice di prodotto: il codice di Z7
> aspetta l'autorizzazione del developer.
>
> **Decisione 34, alla lettera** (nota dev nel file delle decisioni): «si questo retry esponenziale non è male come
> idea, a prescindere, da mettere sia nel frontend che nello scheduler.» Registrata il 15/10: «sì, sia nello scheduler
> sia nel frontend: il polling rispetta la pausa del fornitore e rallenta a ogni errore».

### Stato reale (sola lettura, su `4618a2116`)

- **`RATE_LIMITED` non esiste**, né nel codice né nel piano di X (`03_pluginsAssets`): era un'aspettativa di questa
  analisi (§5), non un lavoro di qualcuno. Da qui il contratto più sotto.
- **Nessun fornitore riconosce davvero un 429, nessuno legge `Retry-After`.** `AssetSourceError(message, error_code,
  details)` (`services/assets/base.py:47-54`) è l'unica classe d'errore degli asset, con codici stringa liberi;
  `FXServiceError` (`services/fx/base.py:318`) è un `Exception` senza codice.
  - yahoo_finance riconosce il 429 dal testo (`_TRANSIENT_KEYWORDS`, `plugin.py:58-86`) e lo **riprova nel thread** 3
    volte con `sleep` bloccanti (1,5 → 3 → 6 s, `_yf_with_retry`, `:89-117`), poi `FETCH_ERROR`: tre colpi in più a un
    fornitore che ha già rifiutato, e un thread fermo fino a ~10 s (tocca anche C-49, ipotesi H1).
  - css_scraper: il 429 diventa `HTTP_ERROR` con `details.status_code` (`:222-231`); chiama URL arbitrari, cioè host
    diversi.
  - justetf e borsa_italiana: le librerie non distinguono il 429 (`FETCH_ERROR`). justetf ha un backoff suo solo per
    la riconnessione del WebSocket (1 → 60 s, `:104-107`).
  - FX (ECB, FED, BOE, SNB): `httpx` più `raise_for_status()`; ogni `HTTPError` diventa `FXServiceError`.
- **Richieste dal vivo** (`POST /assets/prices/current` → `services/assets/price_query.py:701`): cache di 120 s, poi
  il fornitore con `concurrency=5` e `timeout=10`. Ogni errore è inghiottito (`logger.debug`) e si ripiega sull'ultimo
  prezzo salvato (`source="db:last_known"`). `FACurrentPriceItem` (`schemas/prices.py:352-360`) non ha né codice
  d'errore né tempo d'attesa.
- **Scheduler** (`services/platform/scheduler/`):
  - un job che solleva un'eccezione non salva lo stato e riparte al giro dopo, ogni 60 s, senza limite
    (`scheduler.py:123-124`);
  - un job che torna con errori per elemento avanza `last_run_at` e aspetta il suo intervallo (prezzo corrente:
    10 min) o il prossimo slot (storico: anche il giorno dopo);
  - nessun contatore d'errori; `JobState.last_error` resta sempre `None` (`jobs.py:73`, `:162`).
- **Primitive esistenti**: `utils/runtime/rate_window.py` (`SlidingWindowLimiter`, di E per l'email: finestra
  scorrevole in memoria, orologio iniettato, `RateDecision.retry_after` in secondi float). Altri «raffreddamenti» sono
  locali e fatti ognuno a modo suo (`services/fx/catalog.py:25`, `services/assets/market_calendar.py:40`). Non c'è un
  helper generico di backoff o di jitter.
- **Frontend**: `startActivePolling` inghiotte gli errori e non cambia mai cadenza. I due chiamanti (`fetchLivePrices`
  della lista, `pollLivePriceOnce` del dettaglio) inghiottono a loro volta l'errore, quindi l'helper non ne vede
  nessuno. Nessun punto del frontend legge `Retry-After`.

### Principio

Una sola sede della decisione. Il **backend** sa quale fornitore è in pausa e non lo chiama: chiunque passi dal confine
delle chiamate ai fornitori (scheduler, richieste dal vivo, sync manuale, ricerca, metadati, prova della
configurazione) riceve subito `RATE_LIMITED` con il tempo d'attesa, senza I/O. Il **frontend** non tiene uno stato dei
fornitori: rallenta sui propri errori e rispetta il tempo d'attesa che il backend gli comunica.

### Z7a · La primitiva e la configurazione (Z)

- `backend/app/utils/runtime/cooldown.py`, una foglia accanto a `rate_window.py` e nello stesso stile (orologio
  iniettato, thread-safe, in memoria, `max_keys` con LRU):
  - `RateLimitedError`: classe marcatore, con `retry_after: float | None` (secondi) e `scope: str | None`;
  - `retry_after_seconds(value, now) -> float | None`: legge `Retry-After` nelle due forme di RFC 9110 (secondi e
    data HTTP), `None` su un valore assente o sbagliato;
  - `Cooldowns(base_s, max_s, *, hard_max_s=86_400, jitter=0.1, clock=time.time, rng=random.random)`, con chiave
    `(dominio, fornitore, scope)`:
    - `check(key) -> float`: 0 se si può chiamare, altrimenti i secondi che mancano. Alla scadenza passa **un solo
      tentativo** (mezzo aperto) e gli altri chiamanti concorrenti aspettano il suo esito: la lista chiama fino a 5
      asset insieme, lo scheduler 3, e senza questo ogni scadenza moltiplicherebbe i rifiuti;
    - `refused(key, retry_after) -> float`: all'n-esimo rifiuto consecutivo l'attesa è `min(base × 2^(n−1), max)`;
      `Retry-After` vale come minimo e può superare `max` fino a 24 h; si aggiunge un jitter dello 0–10 %, mai sotto
      `Retry-After`. Restituisce l'attesa;
    - `succeeded(key)`: azzera la chiave;
    - `snapshot()`: lo stato per i log e per un pannello futuro.
  - **Orologio di parete, non monotòno.** Su Fly `suspend` congela la VM, e il tempo sospeso può non entrare in
    `time.monotonic()` (su Linux `CLOCK_MONOTONIC` non conta la sospensione): una pausa iniziata prima di una
    sospensione bloccherebbe il fornitore anche dopo il risveglio, proprio quando l'istanza si sveglia per aggiornare.
    Da verificare su Fly in Z2, dove lo stesso tema tocca il timer d'inattività.
- `backend/app/services/platform/provider_cooldown.py`: l'istanza del processo, costruita con i valori letti al
  momento della chiamata (come `INSTANCE_BUDGET` dell'email), più `reset()` per i test. Log: un WARNING quando una
  pausa inizia o cresce (fornitore, scope, attesa, `Retry-After`), un INFO al primo successo dopo una pausa, DEBUG per
  le chiamate saltate.
- `backend/app/config/sleep_wake.py`, la sezione di Z (ci andranno anche le variabili di Z2, Z4, Z5 e Z6b):
  - `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS`, default 60; **0 spegne** e ridà il comportamento di oggi;
  - `LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS`, default 3600;
  - un valore non valido ferma l'avvio con un codice (`PROVIDER_COOLDOWN_INVALID`), come
    `LIBREFOLIO_SMTP_MAX_PER_HOUR`; il controllo si registra negli agganci di H (`config_audit.py`).
  - Acceso di default per la decisione 34 («a prescindere»), che ha scartato l'alternativa «spento di default, alla
    lettera della regola»: è un'eccezione consapevole alla regola della specifica del cloud, da scrivere in
    `.env.example` e nella documentazione.
- Test PURE: crescita 1, 2, 4… e tetto; `Retry-After` in secondi e come data, come minimo e sopra il tetto;
  azzeramento; `base=0` spento; jitter nei limiti (generatore con seme); un solo tentativo alla scadenza; chiavi
  separate per scope; il parser con valori sbagliati.

### Contratto per X: `RATE_LIMITED`

- **X1** · `services/assets/base.py`: `AssetRateLimitedError(AssetSourceError, RateLimitedError)` con
  `error_code="RATE_LIMITED"`, `retry_after` e `scope`. È una sottoclasse: chi prende `AssetSourceError` continua a
  prenderla.
- **X2** · `services/fx/base.py`: `FXRateLimitedError(FXServiceError, RateLimitedError)`, con gli stessi attributi.
- **X3** · Ogni fornitore traduce il suo segnale di «troppe richieste»:
  - yahoo_finance: `YFRateLimitError` di yfinance e le parole chiave di oggi → `AssetRateLimitedError`, **senza
    ritentativi nel thread**; gli altri errori transitori li conservano;
  - css_scraper: 429 → `AssetRateLimitedError(retry_after=<Retry-After>, scope=<host dell'URL>)`, una pausa per sito
    e non per tutto il fornitore;
  - justetf e borsa_italiana: dove la libreria espone lo stato HTTP. `borsa-italiana-scraping` è nostra, quindi lì si
    può aggiungere un'eccezione «troppe richieste»; altrimenti la lacuna resta scritta nella guida;
  - i 4 fornitori FX: 429 → `FXRateLimitedError(retry_after=<Retry-After>)`.
- **X4** · Un solo confine per dominio consulta `provider_cooldown`:
  - asset: `call_provider(provider_code, fn, *, timeout, scope=None)` in `services/assets/core.py`, attorno a
    `_run_provider_in_thread`, usata da **ogni** chiamata ai fornitori (dal vivo, refresh, metadati, ricerca anche in
    streaming, prova della configurazione): prima `check` (in pausa → `AssetRateLimitedError` subito, senza thread),
    poi `refused` o `succeeded`. Un hook facoltativo del plugin, `cooldown_scope(...)`, dà lo scope prima della
    chiamata (css_scraper: l'host; default `None`);
  - FX: `_fetch_provider` in `services/fx/sync.py`. Un fornitore in pausa diventa un errore di gamba senza I/O, e il
    ripiego sulla rotta seguente c'è già;
  - le cache restano prima del confine: un valore in cache si serve anche durante una pausa.
- **X5** · Schemi:
  - `FACurrentPriceItem` + `error_code: str | None` e `retry_after: float | None`; durante una pausa il prezzo salvato
    resta come oggi (`source="db:last_known"`) e la risposta resta HTTP 200;
  - `FARefreshResult` e `FXSyncPairResult` + `error_code` e `retry_after`;
  - poi `api sync`.
- **X6** · Test nel dominio di X:
  - il confine: la seconda chiamata durante la pausa non chiama il fornitore (contatore); dopo la scadenza passa una
    chiamata sola;
  - la risposta dal vivo e il ripiego FX;
  - una modalità «troppe richieste» in `mockprov` e `mockfx`, che serve anche a Z7b.
  - Gli E2E non accendono mai una pausa vera sul backend condiviso della corsia: si stubba l'endpoint.
- **X7** · Guida dei plugin asset e FX: «a un rifiuto per troppe richieste solleva l'eccezione, non riprovare nel
  thread».
- **X8** · La prova della configurazione (aggiunta il 15/10 su richiesta del coordinatore): la risposta porta
  `error_code="RATE_LIMITED"` e `retry_after`, e la UI della prova mostra un messaggio chiaro con l'ora locale di
  ripresa, per esempio «fornitore in pausa fino alle …», con una chiave i18n nuova nelle 4 lingue. Lì l'utente ha
  chiesto un'azione esplicita.
- **Dipendenza**: X parte dopo l'ingresso di Z7a, perché usa `RateLimitedError` e `provider_cooldown`.

### Z7b · Scheduler (Z, dopo Z7a)

- Nei risultati dei job, gli elementi con `error_code == "RATE_LIMITED"` contano come **rimandati**, non come errori.
  `JobState` aggiunge `last_items_deferred` e `retry_at`, cioè la fine più vicina delle pause. Entrambi sono salvati in
  `scheduler_state.json`, che si legge senza errori anche nei file vecchi senza questi campi. Il registro dei job
  aggiunge `deferred` e `retry_at`.
- Un job con elementi rimandati torna dovuto a `retry_at`, prima del suo giro regolare e mai dopo. Esempio: uno
  storico rimandato alle 23:00 riprova alle 23:0x, invece che alle 06:00 del giorno dopo. Il nuovo giro costa poco
  grazie alla cache e al recupero delle sole lacune per asset.
- Un job che solleva un'eccezione oggi riparte ogni 60 s per sempre. Con Z7b `consecutive_failures` e
  `next_attempt_at` lo fanno ripartire dopo 1, 2, 4… minuti, con un tetto di 60 min; per il prezzo corrente il tetto
  è la sua frequenza. I contatori si azzerano al primo successo, e `last_error` viene scritto davvero.
- Con gli altri lotti:
  - Z3 e Z4: il recupero immediato e `wake-sync` usano lo stesso «dovuto». Un job in attesa di `retry_at` compare
    quindi come «rimandato fino a T» nell'esito generico di `wake-sync`.
  - Z2: una pausa non è lavoro in corso, quindi l'istanza può sospendersi.
  - Z-7 (backlog): `retry_at` entrerà nel calcolo di `next_wake_at`.
- Test `services scheduler-backoff`: rimandati e `retry_at`; job dovuto a `retry_at`; eccezioni con attesa crescente e
  azzeramento; stato vecchio letto senza errori. Fino all'ingresso di X5 i test usano risultati finti.

### Z7c · Frontend (Z)

- `activePolling.ts`:
  - `run` può restituire un esito `{ok?: boolean; notBefore?: number}`; un'eccezione vale `{ok: false}`.
  - A ogni fallimento consecutivo il giro dopo si allontana: `min(intervallo × 2^k, LIVE_UPDATES_MAX_BACKOFF_MS)`,
    con il tetto a 10 min in `cadence.ts`. La lista passa da 60 a 120, 240, 480, 600 s; il dettaglio da 30 s a 60 s e
    così via fino a 600 s. Il conteggio si azzera al primo successo.
  - `notBefore` è un minimo: il giro dopo non parte prima.
  - La ripresa dopo una pausa rispetta l'attesa in corso. `pollNow`, chiesto dall'utente, passa sempre, e il suo esito
    aggiorna i contatori.
- `livePriceService.ts`:
  - legge `error_code` e `retry_after`;
  - `livePollOutcome(results)` dà un `notBefore` solo se **tutti** gli asset richiesti sono in pausa. Con fornitori
    misti la lista va avanti: il backend non chiama quelli in pausa, e il giro costa poco;
  - un 429 o un 503 del nostro backend con `Retry-After` dà `{ok: false, notBefore}`.
- Le due pagine: `fetchLivePrices` e `pollLivePriceOnce` restituiscono l'esito invece di inghiottire l'errore, con
  poche righe ciascuna. Si toccano **dopo il taglio FE5c di X**.
- Nessun testo nuovo nella UI: durante una pausa resta l'ultimo prezzo, come oggi (D-Z7-2).
- Test:
  - Vitest con timer finti in `activePolling.test.ts`: crescita, tetto, azzeramento, `notBefore`, ripresa, `pollNow`;
  - `livePriceService.test.ts`, nuovo, nella lista di core-unit;
  - E2E `front-asset live-pause` con due casi nuovi: (g) un endpoint che risponde 500 dà richieste a intervalli che
    raddoppiano fino al tetto; (h) con tutti gli asset `RATE_LIMITED` e `retry_after` 300 s, nessuna richiesta prima
    di +300 s.

### Decisioni (prese dal coordinatore il 15/10, attuazione della 34)

> **Coordinatore, 15/10** (sintesi del suo messaggio): le decisioni D-Z7 sono l'attuazione della 34, già approvata dal
> developer. I valori proposti vanno bene; durante la pausa resta l'ultimo prezzo, senza testi nuovi; la prova della
> configurazione e la ricerca rispettano la pausa, e nella prova serve un messaggio chiaro, tipo «fornitore in pausa
> fino alle …» (X8); lo scheduler di Z7b va bene così; l'eccezione alla regola «default invariato» si scrive in
> `.env.example`, citando la decisione 34.

| # | Domanda | Decisione |
|---|---|---|
| D-Z7-1 | Valori | ✅ Backend: base 60 s, tetto 1 h, `Retry-After` rispettato fino a 24 h, jitter 0–10 % fisso. Frontend: raddoppio fino a 10 min |
| D-Z7-2 | Cosa vede l'utente durante una pausa | ✅ Niente di nuovo: l'ultimo prezzo salvato, come oggi |
| D-Z7-3 | Prova della configurazione e ricerca | ✅ Rispettano la pausa: nessuna chiamata, rispondono `RATE_LIMITED` con l'attesa; nella prova un messaggio con l'ora di ripresa (X8) |
| D-Z7-4 | Scheduler | ✅ Elementi rimandati riprovati a `retry_at`, entro il giro regolare; eccezioni con attesa crescente, tetto 60 min |

### Rischi

- Lo stato è per processo: con N worker ognuno impara la pausa da sé, al più un rifiuto in più per worker. L'immagine
  Docker avvia un worker solo.
- Le parole chiave di yfinance possono dare falsi positivi: al peggio una pausa di 1 min, con un WARNING nel log.
- Il singleton vive nel backend condiviso dei test: una pausa non deve passare da un test all'altro. Per questo i test
  della pausa sono PURE, in processo, con `reset()`, e gli E2E stubbano l'endpoint (classe d'isolamento da dichiarare).
- Togliere i ritentativi nel thread di yfinance sul 429 ha un costo: un'ondata breve che oggi passava al terzo
  tentativo aspetterà 1 minuto. In cambio spariscono i `sleep` bloccanti nel thread (C-49, H1).

### Lotti e superfici

| Lotto | Chi | Superfici | Dipende da | Checkpoint |
|---|---|---|---|---|
| Z7a | Z | `utils/runtime/cooldown.py`, `services/platform/provider_cooldown.py`, `config/sleep_wake.py`, `.env.example` (sezione Z), test PURE, doc dev della primitiva | autorizzazione al codice; agganci di H solo per il controllo d'avvio | ingresso subito: sblocca X |
| X-RL | X | X1–X7 | Z7a | di X |
| Z7b | Z | `services/platform/scheduler/` | Z7a; X5 per i campi | dopo X-RL |
| Z7c | Z | `live-updates/`, `livePriceService.ts`, le due pagine | helper subito; servizio e pagine dopo X5 + `api sync` e dopo FE5c | dopo X-RL |

**Conflitti.**

- X: le pagine dopo FE5c, `services/assets/*`, gli schemi, i fornitori. Sono tutti di X, e il contratto separa le parti.
- H: `config_audit.py` per il controllo d'avvio, `.env.example`.
- E: nessuno. `rate_window.py` resta com'è, e la primitiva nuova gli sta accanto.
- Colori: nessuna UI nuova.

**Documentazione** (docs-writer):

- `developer/backend/assets/architecture.md`: il confine e le pause;
- le guide dei plugin asset e FX (X7);
- la pagina dello scheduler: rimandati e attesa crescente;
- `live-ticker.md`: il rallentamento;
- la pagina delle variabili d'ambiente.

**Definizione di fatto.**

- Un 429 di un fornitore lo mette in pausa per tutti i chiamanti, e durante la pausa non parte nessuna chiamata
  (contatore nei test).
- Lo scheduler rimanda gli elementi e li riprova a `retry_at`.
- Il polling raddoppia l'attesa sugli errori e rispetta `notBefore`.
- Con `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS=0` il backend torna al comportamento di oggi.
- Doc EN e `.env.example` aggiornati.

## Z6b — disegno: spegnimento con un tempo massimo (15/10, prima del codice)

> **Via del coordinatore** (15/10 ~16:10): «disegno di Z7 adesso, poi quello di Z6b». **Decisione 35, alla lettera**
> (nota dev): «si mi pare un ottima idea di coerenza.» Quindi circa 8 s per tutte le installazioni. Solo disegno: il
> codice aspetta l'autorizzazione del developer, come Z7a.

### Prove di Z6a finora

- 9 cicli di vita del backend della corsia, su spec singole, tutti puliti: gruppo vuoto in 0,09–2,7 s, e le più lente
  sono le spec degli asset (2,3–2,7 s). L'avviso non è mai comparso.
- Dal 15/10 il coordinatore cerca `Shared backend ignored SIGTERM for` nelle sue run di categoria.

### Cosa dice il codice (verificato il 15/10 su `ef5e96eb5`, uvicorn 0.52.4, Python 3.13.16)

1. **Runner** (`scripts/test_runner/_server.py:312-334`): manda SIGTERM a tutto il gruppo di processi, aspetta il
   processo principale fino a 5 s, poi il gruppo per altri 5 s. L'avviso compare se un membro del gruppo è ancora vivo.
   La grazia è di 5 s, 30 s con coverage (`:49-51`).
2. **uvicorn, al primo SIGTERM o SIGINT** (`uvicorn/server.py:342-347`): smette di accettare connessioni e aspetta le
   richieste in corso **senza limite**, perché `timeout_graceful_shutdown` di default è `None` (`:287-298`); poi
   esegue lo spegnimento del lifespan. Un secondo SIGINT forza l'uscita (`force_exit`), un secondo SIGTERM no.
3. **Alla fine** uvicorn ripristina i gestori originali e rilancia il segnale (`capture_signals`, `:323-340`):
   - con SIGTERM e il gestore di default il processo finisce subito, senza aspettare i thread. Nel caso del runner
     l'ipotesi H1 (thread dei fornitori) è quindi esclusa;
   - con SIGINT (Ctrl+C, e il default di Fly) arriva un `KeyboardInterrupt`: `asyncio.Runner` aspetta i thread
     dell'executor fino a 300 s (`THREAD_JOIN_TIMEOUT`), poi l'uscita dell'interprete li unisce senza limite. Qui H1
     vale: un thread di `_run_provider_in_thread` (timeout di 10–60 s, e il thread prosegue dopo il suo `wait_for`)
     tiene vivo il processo.
4. **Lifespan** (`backend/app/main.py:310-334`), in quest'ordine:
   - `shutdown_tool_executor()`;
   - `shutdown_event.set()` e `await scheduler_task` **senza limite**: un job in corso finisce prima;
   - i registri dei fornitori;
   - `shutdown_brim_parse_pool(wait=True)`, che aspetta i parse in corso. Il commento spiega perché: un SIGKILL
     salterebbe l'atexit e lascerebbe orfani i worker;
   - `shutdown_quant_worker_pools()`, che aspetta `pool.shutdown()`;
   - `shutdown_market_holidays()`, che chiude subito il suo processo;
   - `close_all_caches()`.
5. **Avvio**:
   - Docker usa `CMD ["uvicorn", …]` dietro `entrypoint.sh` (`exec gosu`), senza `--timeout-graceful-shutdown` e senza
     `STOPSIGNAL`; i file compose non hanno `stop_grace_period` (Docker manda SIGTERM, poi SIGKILL dopo 10 s);
   - `dev.py server` usa la CLI di uvicorn (`dev.py:370-401`);
   - la CLI legge le opzioni anche dall'ambiente (`auto_envvar_prefix="UVICORN"`, `uvicorn/main.py:61`), quindi
     `UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN` vale in Docker, in `dev.py` e sotto coverage.
6. **Fly**: `kill_signal` di default è SIGINT, `kill_timeout` 5 s (fino a 300 s sulle CPU condivise).

### Ipotesi riviste per C-49

- **H2 · richieste in volo**: la più probabile. Le spec degli asset chiamano i fornitori veri, e uvicorn aspetta il
  gestore anche quando il client se n'è andato. Una `POST /prices/current` (timeout di 10 s per fornitore) o una sync
  (fino a 55–60 s) ancora aperta a fine run supera i 5 s.
- **H3 · passi del lifespan senza scadenza**: nei test lo scheduler è spento (`LIBREFOLIO_NO_SCHEDULER`). Restano i pool
  BRIM, quant e tool, se c'è un lavoro in corso.
- **H4 · altri membri del gruppo**: ricevono anch'essi SIGTERM dal runner. Contano solo se lo ignorano o se nascono
  durante lo spegnimento, per esempio un worker `spawn` che sta ancora importando l'app.
- **H1 · thread dei fornitori**: esclusa per il runner (SIGTERM), valida con SIGINT: Fly con il default, e Ctrl+C in
  sviluppo.
- **H5 · coverage**: solo con la coverage attiva, che ha una grazia di 30 s.

### Disegno

- **Una manopola**: `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS` in `config/sleep_wake.py`, default 8 (decisione 35, per
  tutti); 0 vuol dire nessun limite, come oggi, per il debug.
- **Il drenaggio (H2)**: `timeout_graceful_shutdown` vale 3/8 del budget, cioè 3 s con 8. Si passa a uvicorn come
  `UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN` quando non è già impostata:
  - in `entrypoint.sh`, con l'aritmetica della shell e senza avviare Python in più;
  - nell'ambiente di `dev.py server`, calcolata da `config/sleep_wake.py`.
  Alla scadenza uvicorn cancella le richieste rimaste, anche lo SSE della ricerca: la cancellazione arriva al gestore,
  e una transazione SQLite aperta si annulla.
- **Il lifespan (H3)**: i passi condividono una scadenza, il resto del budget (5 s con 8). Ogni passo riceve il tempo
  che resta e non lo supera:
  - scheduler: `shutdown_event.set()`, poi `wait_for(scheduler_task, restante)`; alla scadenza, `cancel()`. Il job
    interrotto non salva lo stato e riparte al prossimo avvio (i job sono idempotenti, `leader.py`); il registro dei
    job scrive «interrotto»;
  - tool, BRIM e quant: un'attesa limitata, poi `terminate`, poi `kill` dei loro processi. Così resta coperto il motivo
    del `wait=True` di BRIM: niente processi orfani;
  - l'ordine: prima il lavoro (scheduler e tool), poi i fornitori, i pool, le festività e le cache.
- **La rete di sicurezza (H1, H4 e ogni caso nuovo)**: un watchdog in `services/platform/shutdown_budget.py`, armato al
  primo SIGTERM o SIGINT. Avvolge il gestore che uvicorn ha installato prima dell'avvio del lifespan, e continua a
  chiamarlo. Allo scadere del budget, contato dal segnale:
  - scrive nel log i superstiti: i thread vivi, i processi figli, la fase in corso;
  - termina i figli (psutil: `terminate`, poi `kill` dopo 0,5 s);
  - salva la coverage se è attiva, svuota i log;
  - poi `os._exit(1)`, perché l'uscita è forzata e il codice lo deve dire.
  Copre anche SIGINT, dove oggi i thread dei fornitori possono tenere vivo il processo per minuti. Se avvolgere il
  gestore si rivelasse fragile, il ripiego è armare il watchdog all'inizio dello spegnimento del lifespan, con il
  budget meno il drenaggio.
- **Il runner** (superficie del coordinatore): la grazia normale passa da 5 a 10 s, come Docker. Con il budget di 8 s
  garantito dall'app, l'avviso «ignored SIGTERM» diventa un segnale vero: vuol dire che l'app ha mancato il suo budget.
- **Deploy**:
  - nei file compose, `stop_grace_period: 10s` esplicito;
  - per Fly, nella documentazione del profilo managed: `kill_signal = "SIGTERM"` e `kill_timeout = 10`. Il fly.toml del
    pannello è fuori dal repo, e con i default di Fly (SIGINT, 5 s) il budget di 8 s non basta.

### Test (i rossi prima)

- **`services shutdown-budget`**, azione nuova, PURE: avvia un suo processo su una porta libera, senza il backend
  condiviso. Un'app minima parte con la CLI di uvicorn e con il modulo del budget. I casi:
  - (a) al SIGTERM una richiesta di 30 s è in volo: il processo esce entro budget + 1 s, e il gestore riceve la
    cancellazione;
  - (b) un passo del lifespan non finisce: il processo esce entro budget + 1 s, e il log nomina il passo;
  - (c) SIGINT con un thread non daemon bloccato: esce entro budget + 1 s, mentre oggi resterebbe vivo;
  - (d) un processo figlio che ignora SIGTERM: viene terminato prima dell'uscita, senza orfani;
  - (e) budget 0: nessun limite; si controlla solo che il watchdog non intervenga entro un tempo breve.
  I rossi: oggi (a)–(d) falliscono.
- Unit PURE delle scadenze, con un orologio finto: la ripartizione del budget, e un tempo restante mai negativo.
- Evidenza nel runner: dopo l'ingresso, le run di categoria del coordinatore, con la grazia nuova.

### Superfici e dipendenze

| Superficie | Di chi | Cosa |
|---|---|---|
| `services/platform/shutdown_budget.py`, `config/sleep_wake.py` | Z | il watchdog, la ripartizione del budget, la manopola |
| `backend/app/main.py`, la sequenza di spegnimento | H, attraverso i suoi agganci (CP2b) | i passi con la scadenza |
| `entrypoint.sh`, `docker-compose*.yml` | H e B | la variabile di uvicorn, `stop_grace_period` |
| `dev.py server`, `scripts/test_runner/_server.py` | coordinatore | la variabile di uvicorn, la grazia a 10 s |
| `services/brim/brim_parse_pool.py` | W | l'attesa limitata |
| `services/risk/quant/workers.py` | J | l'attesa limitata |
| `services/tools/executor.py` | il proprietario di `services/tools/` | l'attesa limitata |
| doc di deploy (Docker, Fly) e delle variabili | docs-writer | `stop_grace_period`, `kill_signal`, `kill_timeout`, la manopola |

Z6b dipende dagli agganci di H in `main.py` (CP2b). Per ridurre i passaggi di mano propongo che i limiti dei tre pool
li scriva Z, con un'interfaccia comune `shutdown(deadline)` concordata dal coordinatore con W, J e il proprietario dei
tool.

### Rischi

- Cancellare le richieste dopo 3 s può interrompere una scrittura lunga, come un import BRIM o una sync: la transazione
  si annulla e l'utente rifà l'operazione. Oggi, con Docker, la stessa scrittura muore dopo 10 s per un SIGKILL, che è
  peggio.
- `os._exit` salta gli atexit. Per questo il watchdog chiude i figli, salva la coverage e svuota i log prima di uscire.
- Avvolgere il gestore dei segnali dipende dal comportamento di `capture_signals` in uvicorn 0.52.4: un test lo blocca
  alla versione fissata, e c'è il ripiego descritto sopra.
- Il budget di 8 s supera il `kill_timeout` di default di Fly (5 s): senza la configurazione consigliata, Fly uccide
  prima, come oggi.

### Definizione di fatto

- Con il budget di default il processo esce entro 8 s da SIGTERM o da SIGINT in tutti i casi di prova, senza figli
  orfani.
- Con la grazia di 10 s il runner non mostra l'avviso nelle run di categoria.
- `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS=0` ridà il comportamento di oggi.
- Doc EN aggiornata: variabili d'ambiente, deploy con Docker e con Fly; `.env.example` aggiornato.

## Z7a — la primitiva delle pause (codice, autorizzato il 15/10)

> **Autorizzazione del developer, alla lettera** (15/10 16:3x, inoltrata dal coordinatore; risposta alla domanda
> «Posso far partire Z con il codice di Z7a?»): «Sì, Z parta con Z7a».
>
> - **Base**: piano committato in `4992b864b`, poi il merge di `dev_release2` a `dae4de4fa` (W, i colori di L-10, i
>   journal del coordinatore): HEAD `42713788e`, senza conflitti.
> - **Superfici**: `backend/app/utils/runtime/cooldown.py`, `backend/app/services/platform/provider_cooldown.py`,
>   `backend/app/config/sleep_wake.py`, la sezione di Z in `.env.example` con l'eccezione della decisione 34, i test e
>   le loro voci nel catalogo del runner.
> - X fa nascere `call_provider` nel suo CP10 con la firma di questo disegno, e aggancia il registro in X1–X8: Z non
>   tocca `services/assets/` né `services/fx/`.

### Contratto del codice

- `utils/runtime/cooldown.py` (foglia, nessun import dai servizi o dalla configurazione):
  - `RateLimitedError(Exception)`, il marcatore: `__init__(*args, retry_after=None, scope=None)`, con gli attributi
    omonimi; si combina con le eccezioni di dominio (`AssetSourceError` chiama `super().__init__(message)`);
  - `retry_after_seconds(value, *, now=None) -> float | None`: secondi (anche decimali) o data HTTP; una data passata
    vale 0; `None` su un valore assente, vuoto, negativo, non finito o illeggibile;
  - `CooldownState(key, refusals, remaining, trial_in_flight)`, immutabile, per `snapshot()`;
  - `Cooldowns(base_seconds, max_seconds, *, hard_max_seconds=86_400, jitter=0.1, trial_seconds=60, max_keys=10_000,
    clock=time.time, rng=random.random)`; argomenti fuori dominio → `ValueError`. I metodi:
    - `check(key) -> float`: 0 se si può chiamare. Durante una pausa restituisce il tempo che manca; alla scadenza dà
      il posto di prova a un chiamante solo, e agli altri il tempo che resta alla prova;
    - `refused(key, retry_after=None, *, base_seconds=None, max_seconds=None) -> float`: l'attesa
      `max(min(base × 2^(n−1), max), min(retry_after, hard_max))`, più un jitter in `[0, jitter]` della stessa,
      dentro `hard_max`. Un rifiuto che arriva più di `max` dopo la fine della pausa precedente riparte da n = 1. Un
      rifiuto che arriva **mentre la pausa è in corso** viene da una chiamata già partita: non conta e non accorcia la
      pausa, e solo un `Retry-After` che finisce dopo la allunga. Così una raffica di chiamate concorrenti rifiutate
      insieme mette in pausa una volta sola (regola aggiunta il 15/10, su una domanda di test-author: senza, 5 chiamate
      in parallelo partivano da n = 5, cioè 960 s invece di 60);
    - `succeeded(key) -> int`: dimentica la chiave e restituisce i rifiuti che aveva. Durante una pausa in corso non fa
      niente e restituisce 0, perché la risposta viene da una chiamata già partita;
    - `released(key)`: libera il posto di prova di un esito senza verdetto (un altro errore, un timeout);
    - `snapshot()`, `reset(key)`, `clear()`, `len()`.
  - Se l'orologio va indietro, il tempo che manca non supera mai l'attesa registrata. Il limite `max_keys` è LRU.
    Thread-safe.
- `config/sleep_wake.py`, la sezione di Z:
  - `SleepWakeConfigError(variable, code, message)`;
  - `provider_cooldown_base_seconds()`: `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS`, un intero ≥ 0, default 60, con 0
    spento; altrimenti `PROVIDER_COOLDOWN_BASE_INVALID`;
  - `provider_cooldown_max_seconds()`: `LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS`, un intero da 1 a 86 400, default
    3600; altrimenti `PROVIDER_COOLDOWN_MAX_INVALID`;
  - `provider_cooldown_settings()`: le due insieme, `ProviderCooldownSettings(base_seconds, max_seconds)` con
    `enabled`; un tetto sotto la base, con le pause accese, dà `PROVIDER_COOLDOWN_MAX_INVALID`.
- `services/platform/provider_cooldown.py`:
  - l'istanza `PROVIDER_COOLDOWNS`, letta al momento della chiamata, così un test la sostituisce;
  - la chiave `(dominio, fornitore, scope)`;
  - `wait_before_call`, `record_refusal(…, retry_after=None)`, `record_success`, `record_no_verdict`,
    `cooldown_snapshot`, `reset_provider_cooldowns`;
  - la configurazione si legge a ogni chiamata; con le pause spente non si registra nulla e non si salta nulla;
  - log: WARNING a ogni pausa che inizia o cresce, INFO al primo successo dopo una pausa, DEBUG per le chiamate
    saltate.

> **Fuori pista (decisione)**: un valore non valido delle due variabili non ferma l'avvio, come diceva il disegno:
> scrive un errore nel log, una volta per valore, e si usano i default, come fa l'email. Due motivi: il controllo
> d'avvio sta in `config_audit.py` di H, fuori dalle superfici assegnate; e un valore sbagliato qui non mette a
> rischio niente. Se servirà, un `ConfigCheck` si aggiunge dopo, con H.

### Passi di Z7a

1. Test di `test-author`:
   - `backend/test_scripts/test_utilities/test_cooldown.py`, azione `utils cooldown`;
   - `backend/test_scripts/test_services/test_provider_cooldown.py`, azione `services provider-cooldown`;
   - entrambi registrati nel catalogo, PURE. ✅ 2026-10-15

   > **Note implementazione**: 41 test (CDW-001…041, 112 casi) e 23 test (PCD-001…023, 66 casi). Le voci sono in
   > `scripts/test_runner/_backend_utils.py` e `_backend_services.py`, solo aggiunte, con `isolation="pure"` e il
   > perché in un commento. Il log «una volta per variabile e codice» si prova in un interprete nuovo (PCD-022,
   > `structlog.testing.capture_logs`), come `test_jwt_secret_blank.py`. `check-orphans` verde: 299 test raggiungibili.
   > black pulito; ruff segnala un I001 per file finché i moduli non esistono.
   >
   > **Fuori pista**: test-author ha trovato un difetto del contratto. Un rifiuto durante una pausa in corso contava
   > come consecutivo, quindi 5 chiamate in parallelo partivano da n = 5 (960 s). Il contratto è corretto sopra, con la
   > regola della pausa in corso; i test sono stati rivisti (CDW-036…041, PCD-023). Le letture fissate da test-author:
   > - il jitter sopra il tetto, fino a 3960 s, è voluto;
   > - il decadimento si misura dalla fine estesa;
   > - un rifiuto che non conta segna comunque la chiave come usata (LRU);
   > - con una configurazione non valida si usa la coppia di default intera.
2. Rossi: i moduli non esistono, i test non importano. ✅ 2026-10-15

   > **Note implementazione**: `dev.py test --test-port 6186 --data-dir /tmp/librefolio-r13-z utils cooldown` →
   > exit 1, `ModuleNotFoundError: No module named 'backend.app.utils.runtime.cooldown'`;
   > `… services provider-cooldown` → exit 1, `No module named 'backend.app.config.sleep_wake'`. Entrambi alla raccolta,
   > nessun test eseguito. Log: `/tmp/libreFolio_z7a_red_*.log`.
3. Codice dei tre moduli. ✅ 2026-10-15

   > **Note implementazione**: scritti prima in bozza fuori dal repo (cartella di sessione `files/z7a-draft/`), così i
   > rossi restavano veri. Una prova mia in `/tmp` copriva crescita, raffica, estensione, prova unica, LRU, thread e
   > `Retry-After`. Poi copiati in `backend/app/utils/runtime/cooldown.py`, `backend/app/config/sleep_wake.py` e
   > `backend/app/services/platform/provider_cooldown.py`. Sono gli unici file di prodotto toccati: niente in
   > `services/assets/` né in `services/fx/`. Le docstring di modulo dicono il perché dell'orologio di parete, della
   > prova unica e della regola della pausa in corso.
4. Verdi, più ruff e black sui file nuovi. ✅ 2026-10-15

   > **Note implementazione** (corsia 6186, `nice -n 15`, un file alla volta):
   > - `utils cooldown` **112 passati** in 1,6 s; `services provider-cooldown` **66 passati** in 3,2 s;
   > - le guardie toccate dal lotto: `services config-env-example` 36/36, `utils runtime-isolation` 195/195;
   > - ruff e black puliti sui 7 file del lotto (3 moduli, 2 test, 2 file del runner);
   > - `dev.py lint --dead-code --scope backend` esce 1 come prima, per i reperti già presenti. Di nuovi ce ne sono 8,
   >   tutti nei due moduli: le sei funzioni del servizio, `RateLimitedError` e `retry_after_seconds`. Li usano solo i
   >   test finché X non aggancia il confine (X1–X4); vale lo stesso per le funzioni dell'email di E;
   > - porta 6186 libera.
5. `.env.example`, poi la doc dev della primitiva (`docs-writer`). ✅ 2026-10-15 (`.env.example`); doc rimandata

   > **Note implementazione**: nella sezione «Sleep and Wake» di `.env.example` le due variabili, commentate,
   > sostituiscono «No options yet.»: default, 0 per spegnere, `Retry-After` fino a un giorno, e l'eccezione alla
   > regola del default invariato, con la decisione 34 citata.
   >
   > **Fuori pista**: la doc (la pagina admin `configuration.en.md`, che ha le traduzioni, e quella d'architettura) non
   > l'ho scritta ora. Descriverebbe un comportamento che non esiste finché X non aggancia il confine: senza X1–X4 le
   > variabili non hanno effetto. È nel backlog come Z-9, da fare con l'aggancio.
6. Checkpoint FROZEN. ✅ 2026-10-15
7. Ingresso: base aggiornata, file condivisi, revisione combinata. ✅ 2026-10-15

   > **Note implementazione**:
   > - il coordinatore ha committato Z7a (`9dbd1cc34` codice, `ce2763c4c` journal) e approvato le scelte 1–3: un
   >   valore non valido finisce nel log senza fermare l'avvio, la doc va con l'aggancio (Z-9), il CHANGELOG con X o
   >   con Z7b. Poi ha fuso `dev_release2` a `a4d1884b4` (J, A6a, il banner del Lab): HEAD `ef013ba18`, senza
   >   conflitti, con le mie voci del catalogo intatte accanto alle loro;
   > - file condivisi, scritti su suo via: le docstring di `utils/runtime/__init__.py` (con `rate_window`, che mancava)
   >   e di `services/platform/__init__.py` (con la sonda di prontezza, che mancava), e
   >   `.github/instructions/backend.instructions.md`, nei tre punti che elencano quei pacchetti;
   > - revisione combinata, una prova alla volta con `nice -n 15`: `check-orphans` verde (410 frontend, 304
   >   backend); `utils cooldown` 112/112; `services provider-cooldown` 66/66; `services config-env-example` 36/36;
   >   `utils runtime-isolation` 195/195; ruff e black puliti sui due `__init__`; porta 6186 libera.

## Z6b — spegnimento con un tempo massimo (codice, autorizzato il 15/10)

> **Autorizzazione del developer, alla lettera** (15/10 17:3x, inoltrata dal coordinatore; risposta alla domanda
> «Posso far partire Z con il codice di Z6b?»): «Sì, Z parta con Z6b».
>
> - **Base**: avanzamento veloce a `9c8ee20c3`, uguale a `dev_release2`. Dentro ci sono Z7a (`2ab8a3a43`) e H.
>   `main.py` è ancora senza gli agganci di CP2b.
> - **Perimetro**, dal disegno:
>   - `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS=8`, con 0 per nessun limite;
>   - il drenaggio a 3/8 del budget, passato come `UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN` da `entrypoint.sh` e da
>     `dev.py server`;
>   - i passi del lifespan con una scadenza comune;
>   - il watchdog;
>   - la grazia del runner da 5 a 10 s;
>   - l'interfaccia comune per le attese dei pool.
> - **Superfici d'altri, dichiarate**:
>   - in `dev.py`, solo il punto in cui `cmd_server` prepara l'ambiente di uvicorn, senza toccare `--build-only` (J,
>     C-94) né il banner del Lab;
>   - `entrypoint.sh`;
>   - `scripts/test_runner/_server.py`;
>   - `backend/app/main.py`, prima di CP2b di H: le righe della sequenza di spegnimento, da comunicare al
>     coordinatore;
>   - `frontend/playwright.config.ts:199`, la grazia del webServer da 5000 a 10000 ms: lo stesso caso del runner, da
>     dichiarare.
> - **Restano ad altri**: `stop_grace_period` nei compose (H, CP7b) e la nota per Fly nella doc del profilo gestito
>   (X, CP6).

### Contratto del codice

- `config/sleep_wake.py`, nella sezione di Z:
  - `shutdown_timeout_seconds()`: `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS`, default 8; 0 vuol dire nessun limite;
    altrimenti un intero da 2 a 600. Un valore fuori da queste regole dà `SHUTDOWN_TIMEOUT_INVALID`;
  - `shutdown_drain_seconds(budget)`: 3/8 del budget, almeno 1 s; `None` con il budget a 0;
  - `uvicorn_drain_env(environ)`: la variabile che un lanciatore aggiunge per uvicorn,
    `{"UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN": "<n>"}`. È vuota se la variabile è già impostata o se il budget è 0; un
    budget inutilizzabile vale il default.
- `services/platform/shutdown_budget.py`:
  - `ShutdownStep(name, run, blocking=False)`: `run` restituisce `None` oppure qualcosa da attendere. Un passo
    `blocking` gira in un thread;
  - `StepOutcome(name, finished, seconds, error)`;
  - `ShutdownWatchdog(budget, *, clock, exit, terminate_children)`:
    - `arm()` è idempotente, e il primo armo fissa la scadenza;
    - alla scadenza scrive nel log la fase e i superstiti (thread e figli), termina i figli, salva la coverage se è
      attiva, svuota i log, poi `exit(1)`;
  - `install_shutdown_watchdog()`: avvolge i gestori di SIGTERM e SIGINT installati da uvicorn, e li chiama ancora.
    Funziona solo nel thread principale, con un gestore chiamabile e un budget maggiore di 0. **Mai nel processo di
    pytest**, dove i test API avviano uvicorn in un thread;
  - `ShutdownSequence.begin()` fissa la scadenza:
    - con il watchdog armato, la sua scadenza meno 0,75 s per la pulizia;
    - senza watchdog, adesso più il budget meno il drenaggio;
    - con il budget a 0, nessuna scadenza;
  - `ShutdownSequence.run(*steps, final=False)`:
    - ogni passo riceve il tempo che resta, almeno 0,2 s; quello che lo supera viene cancellato e segnato nel log, e
      la sequenza continua;
    - un errore finisce nel log e non ferma la sequenza;
    - con `final=True`, alla fine termina i processi figli rimasti, tranne il resource tracker di
      `multiprocessing`;
  - `terminate_child_processes(timeout, keep=None)`: `terminate`, poi `kill`, sui figli ricorsivi (psutil).
- **L'interfaccia comune dei pool**: nessuna riga nei file di W e di J. Ogni pool resta un passo della sequenza con il
  suo tempo; i figli rimasti si terminano alla fine. Il motivo del `wait=True` di BRIM (niente orfani) resta coperto
  anche quando l'attesa viene tagliata.
- In `main.py`:
  - prima dello `yield`, `install_shutdown_watchdog()`;
  - nel `finally`, il passo del `tool executor`;
  - dopo, nello stesso ordine di oggi: lo scheduler (il task, cancellato alla scadenza), i tre registri dei fornitori,
    il pool BRIM (`blocking`), i pool quant, le festività, le cache, con `final=True`.

### Passi di Z6b

> **Accordo con H** (15/10, ~18:00, messaggio di H; firma fissata da lì, codice nel suo CP2b, SHA al checkpoint):
> `main.py` lo divide H in CP2b, e nessun altro lo tocca. Il meccanismo sta in `services/platform/lifecycle.py` (di H):
> - `Step(name, run, blocking=False)`; un awaitable lo attende `asyncio.wait_for`, e un `Task` tagliato viene
>   cancellato; `blocking=True` va in un thread solo quando c'è una scadenza;
> - `StepOutcome(name, finished, seconds, error)` e `MIN_STEP_SECONDS = 0.2`;
> - `current_step()`, che vale `"startup:<nome>"` o `"shutdown:<nome>"`;
> - `run_startup_steps(steps)` e `run_shutdown_steps(steps, deadline=None) -> list[StepOutcome]`, con la scadenza
>   assoluta su `time.monotonic()`; un passo tagliato va nel log in WARNING, uno che solleva in ERROR, e si prosegue.
>
> Il cablaggio sta in `services/platform/app_lifespan.py` (di H): `STARTUP_STEPS`, `FINALLY_STEPS = (tool-executor,)`,
> `SHUTDOWN_STEPS` nell'ordine di oggi, e `shutdown_deadline()`, chiamata una volta all'inizio del `finally`. Z6b ci
> aggiunge una riga per ciascuno di questi:
> - `Step("shutdown-watchdog", lambda: install_shutdown_watchdog())`, primo passo d'avvio;
> - `shutdown_deadline` collegata alla mia;
> - `child_processes_step()`, ultimo di `SHUTDOWN_STEPS`.
>
> Di conseguenza:
> - il mio `ShutdownStep`/`ShutdownSequence` del contratto sopra non si fa, perché il runner è quello di H;
> - `child_processes_step()` non fa niente senza un watchdog installato nel processo: nel processo di pytest, dove i
>   test API avviano uvicorn in un thread, non deve terminare i figli di pytest;
> - finché CP2b non entra, `shutdown_budget.py` importa `lifecycle` solo dentro le funzioni. All'ingresso di CP2b gli
>   import passano in cima al modulo.
>
> **Firma definitiva** (H, 15/10 ~18:05; `lifecycle.py` entra nel commit di taglio di CP2b):
> - con la scadenza ogni passo è limitato da `asyncio.timeout(max(deadline − now, MIN_STEP_SECONDS))`, e i passi
>   `blocking` girano in `asyncio.to_thread`;
> - un passo tagliato dà `finished=False` e un WARNING «Shutdown step cut by the deadline»;
> - un passo che solleva, anche con un suo `TimeoutError`, dà `error=repr(exc)` e `logger.exception`;
> - `current_step()` torna `None` dopo ogni passo;
> - per collegare la mia `shutdown_deadline` basta sostituire la `def` di `app_lifespan.py` con l'import;
> - il test `services app-lifecycle` di H fissa l'ordine come sottosequenza; i due vincoli di Z6b (il watchdog primo
>   passo d'avvio, `child-processes` ultimo passo di spegnimento) li fissa un test mio.
>
> **Avviso di H**: un passo `blocking` tagliato lascia vivo il suo thread. Lo coprono tre cose:
> - con SIGTERM uvicorn rilancia il segnale con il gestore di default, e il processo esce senza aspettare i thread;
> - con SIGINT, dove `asyncio.run` aspetterebbe l'executor fino a 300 s, l'uscita forzata del watchdog;
> - per il pool BRIM, il passo dei processi figli, che termina i worker e fa tornare `shutdown(wait=True)`.

1. Test di `test-author`, rossi: le unità, i processi veri con l'app minima su un socket Unix, `entrypoint.sh` e la
   grazia del runner. ⏳ (parte 1 ✅ 2026-10-15: unità, `entrypoint.sh` e grazie; i test di processo dopo CP2b)

   > **Note implementazione** (parte 1): `backend/test_scripts/test_services/test_shutdown_budget.py`, SDB-001…041,
   > 178 casi, azione `services shutdown-budget` (PURE):
   > - la configurazione: 62 casi;
   > - `entrypoint.sh` sotto `sh` e sotto `dash`: 50 casi, saltati da root;
   > - la grazia del runner e del webServer di Playwright: 2 casi;
   > - il modulo: 64 casi, con il watchdog e i suoi falsi `exit` e `terminate_children`, i gestori dei segnali salvati e
   >   rimessi a posto, e i figli veri.
   >
   > Tre rilievi di test-author sono adottati:
   > - `arm()` può essere rientrato da un gestore di segnale sullo stesso thread: con un `Lock` si bloccherebbe, e
   >   con un controllo seguito da un'assegnazione partirebbero due thread. Ora c'è un `dict.setdefault` con una tupla
   >   nuova a ogni chiamata;
   > - `exit(1)` gira anche quando falliscono il rapporto, i figli o la coverage;
   > - gli spazi in shell valgono come in Python (`sed`, e una `UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN` vuota conta come non
   >   impostata).
   >
   > **Parte 2 in bozza** (15/10 ~19:30, test-author, non lanciata):
   > - `backend/test_scripts/test_services/_shutdown_budget_app.py`: l'app di prova. Usa i pezzi veri (il watchdog
   >   come primo passo d'avvio, `shutdown_deadline()` una volta nel `finally`, `child_processes_step()` per ultimo) e
   >   ha degli interruttori `Z6B_APP_*`;
   > - `test_shutdown_budget_process.py`: SDP-001…007, cioè i casi (a)–(f) su processi veri e (g) il cablaggio;
   >   azione `services shutdown-process` (PURE). Il socket sta in `/tmp/lf-z6b-*`, perché macOS limita il percorso a
   >   104 byte; il server gira nella sua sessione e la pulizia ne uccide il gruppo;
   > - i codici d'uscita, letti nei sorgenti di uvicorn 0.52.4 e Python 3.13:
   >   - con SIGTERM, uvicorn rilancia il segnale e si esce con −SIGTERM;
   >   - con SIGINT, il `KeyboardInterrupt` viene inghiottito e l'interprete aspetterebbe per sempre il thread non
   >     daemon: lo chiude solo il watchdog, con 1;
   >   - (a), (b) e (d) accettano −SIGTERM o 1, ma 1 solo con «Shutdown budget exhausted» nel log;
   > - la registrazione fa diventare rosso `services all` finché CP2b non entra: si committa con la parte 2.
   >
   > Rischi segnalati da test-author:
   > 1. il passo d'avvio del watchdog restituisce un oggetto che non si può attendere, quindi `run_startup_steps` deve
   >    attendere solo gli awaitable. **Chiuso** da H il 15/10: il risultato di `run()` passa per `_completed()`, che
   >    lo attende solo se `inspect.isawaitable(result)`, all'avvio come allo spegnimento, e un suo test lo prova;
   > 2. `child_processes_step()` è sincrono sul loop e con un figlio testardo dura fino a ~1 s, più del margine di
   >    0,75 s; anche i passi dopo un taglio ricevono 0,2 s ciascuno. Nel caso peggiore il watchdog scatta durante
   >    l'ultimo passo: termina comunque i figli e si esce con 1. È accettato, perché il processo esce nel budget.
2. Rossi. ✅ 2026-10-15 (parte 1)

   > `services shutdown-budget` → exit 1, `ImportError: cannot import name 'DEFAULT_SHUTDOWN_TIMEOUT_SECONDS'`, alla
   > raccolta. Log: `/tmp/libreFolio_z6b_red_unit.log`.
3. Codice. ✅ 2026-10-15 (senza il cablaggio, che aspetta CP2b)

   > **Note implementazione**:
   > - `config/sleep_wake.py`: la variabile, `shutdown_drain_seconds`, `uvicorn_drain_env`. `_value` legge
   >   l'ambiente del processo ancora come `os.environ.get(name)`, la forma che la guardia di `.env.example` segue:
   >   un'espressione condizionale l'avrebbe resa cieca anche alle variabili di Z7a;
   > - `services/platform/shutdown_budget.py`: il watchdog, l'installazione, la scadenza, i figli, e
   >   `child_processes_step()`. Senza watchdog non fa niente. Importa `lifecycle` dentro le funzioni finché CP2b non
   >   entra;
   > - `entrypoint.sh`: il blocco del drenaggio, in shell POSIX. Gli zeri iniziali si tolgono con l'espansione dei
   >   parametri, perché `expr` esce con 1 su un risultato 0 e con `set -e` fermerebbe l'avvio;
   > - righe dichiarate in altri file:
   >   - `dev.py`: due righe dopo `_ensure_shared_jwt_secret(env)`, lontano da `--build-only` e dal banner del Lab;
   >   - `scripts/test_runner/_server.py`: `SHUTDOWN_GRACE_PLAIN` da 5 a 10, con il perché;
   >   - `frontend/playwright.config.ts:199`: da 5000 a 10000 ms;
   > - `.env.example`: la variabile, nella sezione «Sleep and Wake», con la decisione 35 citata.
   >
   > ruff e black puliti sui file del lotto. In `dev.py` ruff conta gli stessi 42 reperti di prima, e nessuno è sulle
   > mie righe. Black segnala riformattazioni già presenti in `dev.py` e in `_server.py`, e nessuna tocca le mie
   > righe.
4. Verdi e guardie; poi, su uno slot del coordinatore, un ciclo di vita vero del backend della corsia. ⏳ (parte 1 ✅
   2026-10-15)

   > **Note implementazione** (parte 1; corsia 6186, `nice -n 15`, una prova alla volta):
   > - `services shutdown-budget` **178/178** in 11,3 s;
   > - `check-orphans` verde, 305 file backend;
   > - `services config-env-example` 36/36; `services provider-cooldown` 66/66 (la sezione `sleep_wake` è cambiata);
   > - `utils runtime-isolation` **195/195** dopo la riparazione qui sotto;
   > - porta 6186 libera.
   >
   > **Fuori pista**: con la grazia a 10 s, `utils runtime-isolation` ha dato due rossi e poi è rimasto appeso.
   > Tre orologi finti dei test del runner erano tarati sui 5 s: valori 6.0 e 12.0, cioè grazia + 1. In
   > `[group-ignores-sigterm]` l'orologio fermo a 12, sotto la scadenza di 16, con la `sleep` finta che torna subito,
   > girava in tondo. Ho fermato la run, senza processi rimasti.
   >
   > Riparazione di test-author in `test_runtime_isolation.py`:
   > - gli orologi derivano da `SHUTDOWN_GRACE_PLAIN` (`PLAIN_GRACE_S + 1.0`, `2 * PLAIN_GRACE_S + 2.0`), come il
   >   file già faceva per `STARTUP_TIMEOUT`;
   > - un'asserzione era giusta solo per coincidenza: in quel caso l'unica attesa è la raccolta dopo il SIGKILL, scritta
   >   5 in `_server.py`, che per caso valeva quanto la vecchia grazia. Ora ha il suo valore atteso,
   >   `SIGKILL_REAP_TIMEOUT_S = 5`.
   >
   > Nel file non ci sono altri valori tarati sulla grazia.
   >
   > Restano per la parte 2, dopo CP2b: i test di processo, le tre righe in `app_lifespan.py`, gli import di
   > `lifecycle` in cima al modulo e il ciclo di vita vero.
   >
   > **Ingresso della parte 1** (15/10, 18:41–18:56). Il coordinatore ha committato `f0b9bcad2` e `a014ec482`, poi ha
   > fuso `dev_release2` a `bcd680868` (Y2, W E1b, J CP-4, E2): HEAD `c92fe1a93`. Le prove sulla revisione combinata,
   > una alla volta con `nice -n 10`:
   > - `utils test-server-preparation` 63/63, `utils runtime-isolation` 195/195, `services shutdown-budget` 178/178;
   > - `api system` 117/117, con un ciclo di vita vero del backend condiviso:
   >   - nell'ambiente del processo uvicorn c'è `UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=3`, letto con `ps eww` sul listener;
   >   - il gruppo di processi si svuota 760 ms dopo la chiusura del listener;
   >   - nel log dell'app «Shutting down LibreFolio» e «All caches closed on shutdown»;
   >   - nessun avviso «Shared backend ignored SIGTERM»;
   > - `front-utility settings` 46/46 con `--workers 2`: stessa variabile nel processo, gruppo vuoto dopo 109 ms, nessun
   >   avviso;
   > - `check-orphans` verde: 126 spec, 415 file Vitest, 308 file backend;
   > - porta 6186 libera.
   >
   > Il carico era alto (fino a 95 al minuto): prima delle due run col backend ho aspettato che scendesse sotto 60.
   > Strumenti fuori dal repo: `/tmp/libreFolio_z6b_run.sh` e l'osservatore di Z6a. Log in `/tmp/libreFolio_z6b_*`.
   >
   > **Parte 1 entrata** in `dev_release2` a `000090aaf` (15/10 ~18:57). Avanzamento veloce del mio ramo a `10d5ccd2d`.
   > Il CHANGELOG lo scrive il coordinatore con la parte 2, quando tutto il budget è acceso. In attesa dello SHA di
   > CP2b, i test di processo si scrivono in bozza e non si lanciano.
   >
   > **Checkpoint della bozza della parte 2** (15/10 ~20:00). CP2b è entrato (`4fb017a9a`) e il coordinatore ha dato
   > il via alla parte 2. Il merge di `dev_release2` (`9b82187f6`) però si sarebbe fermato sulle mie modifiche aperte
   > al backlog e a `_backend_services.py`. Quindi: commit delle modifiche aperte (bozza dei test di processo, doc EN,
   > registrazione, journal), poi il merge. I blocchi non si sovrappongono: nel runner sono a 535 e 1336 contro 413,
   > 902, 1242 e 1501; nel backlog Z-10 sta 7 righe sopra le 49 aggiunte alla sezione B. Il punto fermo ha ruff e black
   > puliti sui file nuovi, le ammonizioni a posto e `git diff --check` pulito. In quel commit `services
   > shutdown-process` è rosso, perché `lifecycle` non c'è ancora; dopo il merge resta rosso solo SDP-007, il
   > cablaggio, fino alle 3 righe.
5. `.env.example`, la doc admin (`docs-writer`), il CHANGELOG proposto. ⏳ (`.env.example` ✅ con la parte 1; doc
   in bozza ✅ 2026-10-15, entra con la parte 2)

   > **Note implementazione** (doc, da `docs-writer`, solo EN, nessuna build, niente stamp):
   > - `admin/configuration.en.md`: sezione nuova «⏹️ Stopping the Server» `{: #shutdown }`, fra «Startup Checks» e
   >   «Parameters Set by the Tools». Contiene la tabella delle due variabili, i tre tempi dello spegnimento e un
   >   avviso: chi alza il budget alzi `stop_grace_period`, con un esempio YAML. Fly.io resta fuori (lo documenta X).
   >   Nessuna riga in «Main Options», perché lì un valore sbagliato ferma il server, e questo no;
   > - `developer/test-walkthrough/index.md` (453, 458–465) e `runner_architecture.md:802`: la grazia senza coverage è
   >   10 s, e l'avviso «ignored SIGTERM» vuol dire budget mancato;
   > - debito di traduzione vero sulle pagine admin IT, FR ed ES: la sezione nuova manca e deve tenere `{: #shutdown }`;
   > - le pagine descrivono il comportamento completo, che c'è solo dopo il cablaggio: entrano con la parte 2.
   >
   > **Fuori pista**: docs-writer ha segnalato, dal codice, che Ctrl+C su `./dev.py server` uccide il server dopo
   > 0,25 s (`subprocess.run` in `run_command_live`). Ho verificato la lettura nel codice: è un difetto che c'era già,
   > in una superficie del coordinatore, ed è finito nel backlog come Z-10. Fuori regola: una volta docs-writer ha
   > lanciato un `python3.14 -c` di sistema, in sola lettura.
6. Checkpoint FROZEN. ⏳
