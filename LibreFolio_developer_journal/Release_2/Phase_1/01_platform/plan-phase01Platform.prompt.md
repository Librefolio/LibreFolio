# H · Piattaforma — analisi d'implementazione (fase 01, 1.3.0)

> **Piano della sessione H · Piattaforma** (fase 01, 1.3.0).
>
> - L'analisi è del 14/10 ed è stata consegnata al coordinatore della 1.3.
> - Via libera parziale il 14/10 alle 22:55: per ora solo CP1 (§14 «Avanzamento»).
>
> - Worktree `LibreFolio-worktrees/e-alfy-sturdy-memory`, ramo `e-alfy-h-piattaforma` (l'app lo ha rinominato all'avvio).
> - Base dell'analisi `459131eb8`; base di CP1 `c9bb8f257`.
> - Corsia: porta 6181, data-dir `/tmp/librefolio-r13-h`. Coordinatore: «Release 1.3 planning».
> - Il grafo della devWiki manca, come previsto. Ho letto le pagine committate: `domains/infrastructure`,
>   `domains/scheduler`, `domains/auth`, `features/F-062`, `problems/stale-frontend-after-update-html-cached` e
>   `problems/stale-version-file-shadows-git-describe`.

## 0. Dipendenza in arrivo

Il CP2 dipende da un commit del coordinatore su `main.py`, da integrare prima del taglio.

- Il taglio di `main.py` (CP2) parte dopo quel commit e dopo l'aggiornamento di base. Se, quando CP1 è integrato, il
  commit non c'è ancora, proseguo con i lotti che non toccano i gestori statici e il lifespan di `main.py`.
- La rinomina (CP1) non ne dipende: in `main.py` cambia solo due import in testa.

## 1. Stato reale (verificato sul codice, 14/10)

| Tema | Cosa c'è | Riga |
|---|---|---|
| `services/` in cima | 47 voci. Le mie: `scheduler/` (7 file, 705 righe), `container_registry.py` 225, `date_sentinel.py` 74, `data_quality_thresholds.py` 48 (solo costanti), `backup_service.py` 183, `static_uploads.py` 534, `file_preview.py` 316 | — |
| `main.py` (523 righe) | Bootstrap del DB (`_alembic_head_revision` :83, `ensure_database_exists` :101, `run_post_migration_fixes_at_startup` :222); `lifespan` :244-333; seed delle impostazioni e prewarm :336-354; app :357; CORS :367; GZip :379; router :382; serving di MkDocs e della SPA :385-523 (`ImmutableStaticFiles` :473-480) | — |
| Letture di env fuori da `config.py` | `main.py:70` (TEST_MODE); `auth_service.py:104` (JWT_SECRET, A); `web_link_finder.py:124-162` (7 letture, X); `donation_popup_service.py:39` (A); `scheduler.py:97` (NO_SCHEDULER); `system.py:260` (lane id dei test, resta) | — |
| `config.py` | `Settings` (pydantic-settings, legge `.env`); `get_settings()` costruisce una nuova istanza a ogni chiamata; RISK idle 600 s (:131-132) | — |
| Segreti | Nessun `*_FILE`. JWT casuale per processo se manca (`auth_service.py:104`); `dev.py:160-168` lo genera una volta e lo passa ai worker. Nessuna chiave d'istanza, nessuna `secrets/`, `cryptography` assente dal lock | — |
| `.env.example` | 84 righe, incompleto: mancano JWT_SECRET, RISK_*, NO_SCHEDULER, DISABLE_DONATION_POPUP. **Il Dockerfile lo copia come `/app/.env`**: ogni variabile nuova deve restare commentata | `Dockerfile` `COPY .env.example ./.env` |
| `system.py` | info (pubblico: versioni delle dipendenze e dell'OS), plugin-diagnostics, container-image-status, connection, health, test-lane-health. Niente ready, version, config pubblica | — |
| Versione | `utils/runtime/version.py:41-49` legge `VERSION` prima di `git describe` (R2). `dev.py:1626-1641` e `release.yml:123-141` lo scrivono. `pyproject.toml:7` e `package.json:4` dicono ancora 1.1.0 (C-84) | — |
| Scritture HTTP | **70** endpoint POST/PUT/PATCH/DELETE: 64, più 6 in `fx.py`, i cui router hanno nomi diversi | — |
| Frontend | `routes/(app)/+layout.svelte` (274 righe, legacy `$:`); interceptor centrale in `lib/api/zodios-client.ts:122`; toast via `notify()`; banner ambra già esistente (`OnboardingBootstrapBanner`); i18n per sottosistema (`lib/i18n/<sub>/`) | — |
| Docker | `EXPOSE 6040 6041`; compose espone `${TEST_PORT:-6041}:6041` (C-37); `env_file` porta `PORT` nel container (N-8); `cmd_docker_exec` senza `--user` (`dev.py:1803`, 32-3) | — |
| Registro | GHCR (lettura anonima, 14/10): il tag `test` c'è ancora, insieme a latest, nightly, nightly-light e 7 numerici (C-26) | — |
| Fuso orario (P-4) | `tzdata` non è nel lock. `python:3.13-slim` (trixie) installa `tzdata` ma non `tzdata-legacy`: alias come `Asia/Calcutta` o `US/Eastern` probabilmente assenti. Da provare nell'immagine (Docker oggi spento). Effetto: un nome legacy salvato su un host e portato nell'immagine fa ricadere lo scheduler in UTC senza avviso (`scheduler.py:21-24`) | — |
| Test accoppiati a `main.py` | `test_post_migration.py` (circa 25 patch su `main`, alcune `raising=False`, cioè mute), `test_market_calendar.py`, `test_signal_runtime.py`, `test_risk_scenario_catalog.py`; `test_db_config.py:124` importa `ensure_database_exists` da `main` | — |

## 2. Già fatto, contraddetto, da sapere

- **F28**: fatto quasi tutto (HTML in revalidate, chunk immutabili). Resta questo: `ImmutableStaticFiles` mette `immutable` su tutto `/_app`,
  anche su `_app/version.json`. Oggi non lo legge nessuno (`updated` non è usato), quindi l'impatto è basso. La cura:
  `immutable` solo sotto `_app/immutable/`.
- **F27**: le variabili esistono già (`config.py:131-132`). Mancano il default di 60 s nel profilo gestito e la doc.
- **D-P7** (developer, 12/10): `utils/runtime/version.py` e `cache.py` restano in `utils/`. Le proposte di P2.3
  (`platform/version.py`, `platform/cache.py`) sono decadute.
- **P2.2** mette anche `provider_registry` in `platform/`, ma quel file è di X (PL2): lo sposta X, se vuole.
- **C-49**: la voce dice «nessun endpoint SSE», ma uno c'è, `/api/v1/assets/provider/search/stream`. Diagnosi nel §12.
- **JWT_SECRET**: la specifica del business (F03) chiede di salvarlo. Vale la regola testuale del developer: resta
  casuale se manca, si aggiunge solo `JWT_SECRET_FILE`.
- **Header nuovi (F15)**: il PDF degli upload si apre in un iframe della stessa origine
  (`FilePreviewModal.svelte:790`). Con X-Frame-Options il valore deve essere `SAMEORIGIN`, mai `DENY`.

## 3. Disegno

### 3.1 Albero di arrivo (backend)

```text
backend/app/
  main.py                      ~40 righe: settings → logging → app → install_middleware → router → static
  config.py                    configurazione unica: Settings a sezioni, sorgente *_FILE, PROFILE_DEFAULTS,
                               env_value()/env_secret() per i nomi dinamici (plugin di X)
  services/platform/           __init__ solo docstring
    lifecycle.py               lifespan + STARTUP_STEPS / SHUTDOWN_STEPS espliciti (nome, chiamata tardiva, timeout facoltativo)
    database_bootstrap.py      ensure_database_exists, head Alembic, post-migration, sonda di prontezza
    middleware.py              MIDDLEWARE_STACK ordinato: CORS, GZip, header di sicurezza, sola lettura
    static_site.py             SPA + MkDocs, politica della cache
    security_headers.py · read_only.py · instance_key.py · config_audit.py · instance_config.py · metrics.py (facoltativo)
    scheduler/ · container_registry.py · date_sentinel.py · data_quality_thresholds.py · backup_service.py   (spostati)
  services/files/              static_uploads.py · file_preview.py   (spostati, nomi invariati)
```

- **Passi d'avvio**: due tuple esplicite e ordinate. Ogni passo chiama la sua funzione con una lambda risolta al
  momento della chiamata, così i `monkeypatch` sul modulo continuano a funzionare.
  - L'ordine d'avvio di oggi, da conservare: log, segnali, catalogo dei tool, cartelle dei dati, scenari, avatar, DB,
    post-migration, impostazioni globali, prewarm dei provider, festività, scheduler.
  - L'ordine di spegnimento è quello di oggi, che non è l'inverso dell'avvio.
  - Le altre sessioni aggiungono una riga: B un passo «ripristino in attesa» prima del DB; Z i suoi passi di risveglio
    e il tempo massimo di spegnimento.
- **Middleware**: una lista ordinata, la prima voce è la più esterna. Z vi aggiunge il tracciamento dell'attività.

### 3.2 Configurazione unica (`config.py`)

- La precedenza: `NOME` (env o `.env`) → `NOME_FILE` → default del profilo → default del codice.
  - `_FILE` vale per i campi segreti (`SecretStr`).
  - Un `_FILE` che manca o non si legge ferma l'avvio con un errore chiaro.
  - Se ci sono sia `NOME` sia `NOME_FILE`, vince `NOME` con un avviso (D3).
- **Ogni variabile tiene la sorgente di oggi**:
  - i campi di `Settings` leggono l'ambiente e `.env`;
  - le variabili lette oggi solo da `os.environ` (`LIBREFOLIO_DATA_DIR`, `_TEST_DATA_DIR`, `_TEST_MODE`,
    `_LOG_LEVEL`, `_NO_SCHEDULER`, `JWT_SECRET`, `_DISABLE_DONATION_POPUP`, `_WEB_LINK_FINDER_*`) restano solo
    ambiente, in un modello senza `env_file`;
  - altrimenti cambierebbero comportamento `uvicorn` lanciato a mano e l'immagine, dove `.env` è la copia di
    `.env.example`.
- `PROFILE_DEFAULTS`: ogni campo dipendente dal profilo dichiara il suo valore `managed`. Si applica solo se il campo
  non è stato impostato (`model_fields_set`).
- **Sezioni per proprietario (D2)**: `config.py` diventa il pacchetto `backend/app/config/`. Il percorso d'import non
  cambia.
  - `__init__.py` è di H: la base comune (sorgente `_FILE`, default del profilo, guardie, `get_settings()`), più le
    funzioni e i campi di oggi, `RISK_*` compresi.
  - Le variabili nuove vanno in un file per sezione, scritto dal proprietario: `platform.py` (H), `accounts.py` (A),
    `plugins.py` (X), `sleep_wake.py` (Z), `backup.py` (B), `email.py` (E).
  - `.env.example` ha le stesse sezioni. Così circa 30 variabili nuove da 5 sessioni non passano da un file con un solo
    scrittore.
- `env_value(name)` ed `env_secret(name)` servono per i nomi dinamici, per esempio gli override dei campi dei plugin
  di X.
- **Guardie**:
  - nessuna lettura di `os.environ` in `backend/app` fuori da `config.py` (eccezioni: lane id dei test, scritture di
    `spawn_worker`);
  - ogni campo di `Settings` compare in `.env.example`.
- **Spostamento delle letture sparse**:
  - `main.py:70` e `scheduler.py:97`, file miei;
  - `auth_service.py:104` e `donation_popup_service.py:39`, di A, una riga ciascuno;
  - `web_link_finder.py`, di X, 7 letture.

### 3.3 Segreti e chiave d'istanza (F03)

- `JWT_SECRET_FILE`: un campo `SecretStr`. Va corretto anche `dev.py:_ensure_shared_jwt_secret`, che non deve
  generare un segreto quando c'è `JWT_SECRET_FILE`, altrimenti `NOME` vincerebbe sul file.
- `instance_key.py`, la chiave d'istanza:
  - precedenza: `LIBREFOLIO_INSTANCE_KEY` → `LIBREFOLIO_INSTANCE_KEY_FILE` → `<DATA_DIR>/secrets/instance.key`;
  - il file si crea **al primo uso**: 32 byte casuali in base64url, cartella 0700, file 0600, scritti in un file
    temporaneo `O_EXCL` e poi `os.link`, sicuro anche con più worker;
  - all'avvio si controllano solo i permessi;
  - `derive_key(purpose)` fa HKDF-SHA256 con la sola libreria standard. Serve a X (cifratura) e a B (backup), senza
    dipendenze nuove per H;
  - `secrets/` entra nei percorsi gestiti dei controlli prod/test (`validate_test_data_dir`).
- `config_audit.py` raccoglie gli avvisi, codice + gravità + parametri. Al via: JWT effimero, JWT corto, NOME insieme a
  `_FILE`, permessi larghi sulla chiave generata (non sui `_FILE` dell'utente: i Docker secrets sono spesso 0444),
  `SESSION_COOKIE_SECURE=never`, metriche senza token, log
  DEBUG/TRACE, sola lettura attiva. A aggiunge «registrazione aperta e istanza pubblica».
  - Gli avvisi vanno nei log all'avvio e alla UI dell'admin (§3.4).

### 3.4 Configurazione pubblica e area avvisi (frontend)

- **Backend**:
  - `GET /api/v1/system/instance`, pubblico: `profile`, `read_only`, più le sezioni dei proprietari (link, flag
    donazione e aggiornamenti, registrazione), secondo D2;
  - `GET /api/v1/system/admin-notices`, solo admin: viene da `config_audit`.
- **Frontend**, nuova feature `lib/features/instance/`:
  - `instanceConfig.svelte.ts`: `load()` idempotente, tollerante agli errori;
  - `instanceNotices.svelte.ts`: registro con `show`, `hide` e `list`; campi id, gravità, chiave i18n, parametri,
    chiudibile, azione, pubblico;
  - `InstanceNotices.svelte`: le classi ambra di `OnboardingBootstrapBanner`, nessun esadecimale; passerà alle funzioni
    di stato di R dopo il loro lotto A;
  - un aggancio nell'interceptor di `zodios-client.ts`: il codice `instance_read_only` diventa un `notify()` tradotto.
- **`(app)/+layout.svelte`**: `<InstanceNotices/>` in `<main>`, sopra lo `<slot/>`. `instanceConfig.load()` parte
  all'`onMount`. Il controllo degli aggiornamenti per l'admin rispetta il flag.
- **i18n**: nuovo sottosistema `lib/i18n/instance/` (prefisso `instance.`), nelle 4 lingue.
- **Test**: i due test del layout (`layout.gate`, `layout.authGate`) mockano ogni import, quindi vanno aggiunti due
  `vi.mock`.

### 3.5 Prontezza e versione (F08), C-84, R2

> Riscritto all'avvio di CP5 (15/10), con le decisioni del developer: D6 sì, D9 rimandata, D14 modificata.

- **`GET /system/ready`**, pubblico (healthcheck di Docker, Uptime Kuma, il pannello):
  - 200 se il DB risponde e la sua revisione Alembic è la head; altrimenti 503;
  - il corpo dà lo stato e un codice per controllo: `database` `ok` o `unreachable`; `migrations` `ok`, `mismatch` o
    `unknown`. Mai un messaggio d'errore, un percorso o un identificativo di revisione;
  - la head si legge dagli script una volta per processo e resta in cache; un errore di lettura non resta in cache;
  - il servizio è `services/platform/readiness.py`, la rotta `api/v1/system/ready.py`;
  - `main.py` non cambia: la sua `_alembic_head_revision` diventa una chiamata al servizio in CP2b, con il taglio.
- **`GET /system/info`** (D14 modificata):
  - senza una sessione valida risponde solo `app_version` (`SystemInfoPublicResponse`);
  - con la sessione, tutto come oggi (`SystemInfoResponse`, invariato);
  - la sessione si verifica con `get_current_user` di A, senza copiarne la logica: il suo 401 vuol dire anonimo;
  - l'endpoint diventa un `def`: legge il Pipfile, `package.json` e i metadati dei pacchetti, I/O sincrono.
- **R2**:
  - con `.git` (cartella o file) vince `git describe`;
  - `VERSION` vale solo senza `.git`, o se `git describe` fallisce; altrimenti `unknown`;
  - `dev.py` e la CI continuano a scrivere `VERSION` per l'immagine, che non ha `.git`.
- **C-84** (D6): `0.0.0` con un commento in `pyproject.toml`; `0.0.0` in `frontend/package.json` e nelle due righe
  radice di `package-lock.json`. Nessuno legge questi numeri.
- **Fuori**: `/system/version` (D14) e `/metrics` (D9).
- **Divisione**: CP5a, il backend, che può entrare a qualunque ora; CP5b, il frontend (`package.json`, il lock e
  `AboutTab`, che deve riconoscere la risposta minima), dopo la finestra della galleria.

### 3.6 Profilo gestito e blocco dell'istanza (F05, parte H)

> Riscritto all'avvio di CP6 (15/10). Il developer ha cambiato D4: niente sola lettura, l'istanza si blocca. Il disegno
> che c'era qui (middleware di sola lettura, 32 permessi) è decaduto.

- **Variabili**, lette solo dall'ambiente in `config/platform.py`:
  - `LIBREFOLIO_BLOCKED`: `1/0`, `true/false`, `yes/no`, `on/off`, in qualunque maiuscolo; vuota o assente = non
    bloccata;
  - `LIBREFOLIO_DELETION_DATE`: data ISO, facoltativa, mostrata nella pagina di blocco;
  - un altro valore ferma l'avvio (`config_audit`);
  - valgono in ogni profilo, perché servono a qualunque hoster.
- **Guardia**: `refuse_when_blocked`, dipendenza del router `/api/v1` (`api/v1/router.py`, una riga a parte dagli
  include). Niente middleware: andrebbe registrato in `main.py`, che resta fermo fino a CP2b.
  - FastAPI 0.141 dà alla dipendenza la funzione dell'endpoint (`scope["endpoint"]`), non il percorso completo. Quindi
    `ALLOWED_WHEN_BLOCKED` (`api/v1/instance_block.py`) è un insieme di funzioni.
  - Rifiuto: `423 Locked` con `{"detail": {"code": "instance_blocked", "message": …}}`, solo a chi ha una sessione
    valida. Gli altri ricevono il 401 di `get_current_user`: una rotta protetta risponde allo stesso modo col blocco e
    senza. Le rotte pubbliche fuori dall'elenco (registrazione, liste di `utilities`, impostazioni globali, catalogo AI
    Export) rispondono 401 solo col blocco: da quelle, chi non ha sessione capisce che l'istanza è bloccata, e nient'altro.
  - La sessione è quella della richiesta, perché FastAPI mette in cache la dipendenza.
- **Permessi** (decisione 12): `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `DELETE /auth/users/me`;
  `GET /system/block`, `/system/instance`; le sonde `/system/health`, `/system/ready`, `/system/info` e
  `/system/test-lane-health`.
  - Ganci di una riga, quando le rotte esistono: il backup completo di B, il risveglio programmato di Z.
  - Il reset della password resta fuori; un'aggiunta passa dal coordinatore al developer.
- **`GET /system/block`**: con sessione, permesso col blocco; `{blocked, deletion_date}`. A ci aggiunge `billing_url`
  solo per l'admin (D-A9), B la disponibilità del backup.
- **`/system/instance` pubblico**: non dice niente del blocco.
- **Frontend**:
  - `instanceBlock`, un flag senza import dell'API, che l'interceptor accende al primo 423;
  - nel layout, un ramo prima di quelli del bootstrap mostra la pagina di blocco a tutta pagina. Il guscio dell'app non
    parte, quindi niente raffica di errori;
  - la pagina dice che l'istanza è bloccata e la data di cancellazione; all'admin il backup e «Gestisci abbonamento»
    quando A e B li danno; agli altri l'invito a chiedere il backup all'admin; «Esci»;
  - la cancellazione del proprio account non c'è nella pagina, né come segnaposto: verrà col dialogo di A, estratto
    dopo A5. L'API resta permessa.
- **(C)**: nel profilo gestito un `JWT_SECRET` sotto i 32 caratteri ferma l'avvio (`WeakSecretError`); il controllo
  per la scheda «Sicurezza» diventa `error`. Nel self-hosted resta un avviso.
- **Lo scheduler** non passa da HTTP e continua: il risveglio programmato resta permesso.
- **Test**: pytest e Vitest, niente E2E (il blocco richiederebbe un server dedicato).
- **Revisione di sicurezza** (`security-review`) alla fine di CP6.
- **Default del profilo gestito** di F27 e D5: in CP7b, dove servono.

### 3.7 Lotto operativo

| Voce | Cura |
|---|---|
| P-4 | Prova nell'immagine (`zoneinfo.available_timezones()`, `Asia/Calcutta`, `US/Eastern`). Se mancano: `tzdata-legacy` via apt nel Dockerfile, così un nome salvato altrove non fa ricadere lo scheduler in UTC. Facoltativo `tzdata` PyPI per le installazioni senza Docker (finestra delle dipendenze) |
| M-25 | `_docker_ensure_assets_built()`: versione congelata all'inizio, `LF_APP_VERSION` passato al build del frontend, `frontend/build/.build-version`, ricostruzione se diversa |
| C-37 | Togliere `${TEST_PORT:-6041}:6041` dal compose e `6041` da `EXPOSE`; verificare i test d'immagine (`utils dev-cli-image`, `release-image-contract`) |
| N-8 | `environment: - PORT=6040` nei due compose |
| 32-3 | `docker compose exec librefolio sh -c 'exec gosu "$LIBREFOLIO_UID:$LIBREFOLIO_GID" python dev.py "$@"' sh …`; commento del compose e doc |
| C-26 | Verificato il 14/10: il tag `test` è su GHCR. Cancellarlo è un'azione remota del developer: istruzioni nell'handoff |
| F28 | `immutable` solo sotto `_app/immutable/`; il resto di `/_app` in `no-cache` |
| F27 | Default `managed` di 60 s, `.env.example`, doc admin. Cosa trattiene AI Export (+265 MB) resta a J |
| F15 | Sempre: `X-Content-Type-Options: nosniff` e `Referrer-Policy: strict-origin-when-cross-origin`. Dietro una variabile (spenti in selfhosted, accesi in managed, D5): `X-Frame-Options: SAMEORIGIN` più `frame-ancestors 'self'`, e `Content-Security-Policy-Report-Only` sull'HTML della SPA, non su `/mkdocs`. La CSP applicata aspetta `app.html` (lotto A dei colori) |

Il lotto si divide in due:

- **CP7a, parte Docker**: P-4, M-25, C-37, N-8, 32-3, C-26. Non dipende dagli altri CP: se B ne ha bisogno prima, la
  anticipo subito dopo CP3. Dopo CP7a i file Docker passano a B.
- **CP7b, parte HTTP**: F28, F27, F15.

## 4. Checkpoint e passi (lotti piccoli)

| CP | Contenuto | Sblocca | Dipende da | Stato (19/10) |
|---|---|---|---|---|
| CP1 | **Rinomina** (`git mv`) verso `services/platform/` e `services/files/`, più gli import, le patch dei test, le stringhe del runner, `coverage_analysis.py:71`, la doc per sviluppatori, la mappa in `backend.instructions.md` e le tabelle delle fonti della wiki (17 pagine, 35 citazioni) | Z (scheduler), B (backup), percorsi stabili per tutti | niente (né il commit del coordinatore su `main.py` né npm) | ✅ in dev `6a605904c` |
| CP2 | **Taglio di `main.py`**: lifecycle, database_bootstrap, middleware, static_site. Configurazione unica (pacchetto `config/`, D2) con le letture spostate e la guardia su `os.environ`. Patch dei test su `lifecycle` con `raising=True` | A, Z, B, X (agganci senza toccare `main.py`, sezioni di config) | il commit del coordinatore su `main.py` + aggiornamento di base | ✅ CP2a `60f8a35ce`, CP2b `4fb017a9a` |
| CP3 | **Segreti (F03)**: sorgente `_FILE`, `JWT_SECRET_FILE` (e `dev.py`), `instance_key`, `config_audit` nei log, `.env.example` completo e a sezioni con la guardia «ogni variabile è in `.env.example`», doc admin (configuration, filesystem) | B, X (chiave), E | CP2 | ✅ `d08d9358f` |
| CP4 | **Config pubblica e avvisi**: due endpoint, `features/instance/`, layout, interceptor, i18n, Vitest, `api sync` | A (login, link), Z, X | CP3; `npm ci` approvato | ✅ `1b3eb54c7` |
| CP5 | **Prontezza e versione (F08)**: `/system/ready`, `/system/info` minimo senza sessione (D14 modificata), R2, C-84. CP5a backend, CP5b frontend | pannello di controllo | CP2a | ✅ CP5a `9deb0ea08`; CP5b con CP6, `83eaa5a28` |
| CP6 | **Blocco dell'istanza (D4)**: variabili, guardia sul router v1 con un elenco corto di permessi, `/system/block`, pagina di blocco; (C) `JWT_SECRET` corto fatale nel profilo gestito; pagina admin per gli hoster | il pannello del cloud (blocco) | CP4, CP5 | ✅ `83eaa5a28` |
| CP7a | **Lotto Docker**: P-4, M-25, C-37, N-8, 32-3, istruzioni per C-26. Poi i file Docker passano a B | B (Litestream) | Docker acceso; anticipabile subito dopo CP3 | 🟡 `744f5a0ee`; manca la prova dell'immagine a runtime (Docker spento, H-11) |
| CP7b | **Lotto HTTP**: cache di `/_app` (F28), default di 60 s nel profilo gestito (F27), header con CSP in sola segnalazione (F15) | — | CP6 | ✅ CP7b-1 `1f4c5aeca`, CP7b-2 `d8549c69a` |
| TS1 | Decisione sui test speculari, con i numeri (§13) | — | riordino del backend finito | ⏳ aspetta la decisione P23 del developer |

**Lotti dopo i CP** (§14), entrati in dev (riconciliazione del 19/10; gli SHA delle singole voci H-NN sono nel backlog):

| Lotti | In dev |
|---|---|
| `web_link_finder` (le ultime letture d'ambiente in `config/`) | `9dda5ccd9` |
| C-96 (le corsie ignorano la configurazione dell'istanza), filtro delle credenziali nel log d'accesso, G-10 | `744f5a0ee` (con CP7a) |
| `billing_url` e rotte dei link nel blocco, H-12 (porta), l'anteprima della cancellazione da bloccata (A6a) | `eacc34784` |
| Scopo dei file caricati: CP-U1, CP-U2 | `6a3a2a1cc`, `2d1eee33a` |
| H-17, b-doc-notes (B-4, B-5), H-1, H-4, H-6, H-9, H-3 opzione B | `0ecc5ed27` |
| P17 (l'indirizzo del client dietro un proxy fidato); TC-16 | `b1df87bd4`; `65fc63e7e` |
| H-12 (log condiviso), H-21, H-22, la docstring di `instance_block.py`, H-23, H-24, H-25 | `7ac8b17de`, `946e02d55`, `fa16ce787`, `3f561e204`, `9eb934218`, `4bf824362`, `9839ea00b` |
| H-26 con il residuo di H-24 e H-28; H-27; H-29 e H-30 | `40a76bf1a`; `bfdc1f72c`; `1b11869f7` |
| H-32, H-33, il wiki-file della notte, H-36, H-37 | `ec6aa2007`, `5bba93280`, `1937e6cf4`, `d107b6f26`, `b37e926af` |
| Z-24 con la regola di review di H-39; H-34; H-39; H-35 | `36a487e84`; `75bfac237`; `0403b5eb7`; `d28a6d7df` |
| H-19; H-42; H-46; H-45; H-49 | `9b23bdbfe`; `3b0af4094`; `b7dcd3a25`; `d617cb406`; `96da36422` |
| X-R62 (dalla coda di X); W-B75 (dalla coda di W); H-51; H-47, solo il disegno | `907fb3b97`; `9ba7ef9d3`; `70ab2fcc6`; `13b6cfde1` |
| H-43, fase 1; H-52; H-54 | `d3212e9f2` e `a6adb0066`; `ca7ba117c`; `d6c252ec4` |

Aperti: TS1 (P23), la prova dell'immagine di CP7a (H-11), H-55 (sospesa, §14), H-53 (con H-55); dopo la 1.3: H-47 (il
codice), H-48, H-50, H-56. Il resto delle voci aperte è nella sezione H del backlog.

**Primo treno (M3)**: H CP1 → X CP1 → A A1, integrati in quest'ordine, con gli aggiornamenti di base in mezzo. CP2
segue appena il commit del coordinatore su `main.py` è in `dev_release2`. Insieme danno
percorsi stabili e agganci ad A, Z, B e X. Ogni CP riparte solo dopo il commit del coordinatore, verificato lo SHA.

Passi interni di ogni CP: prima i test rossi (se cambia il comportamento), poi la cura, i verdi mirati, la suite intera,
gli statici, la doc, il piano aggiornato e infine FROZEN.

## 5. Superfici esatte

- **CP1, app**:
  - `main.py` (2 import);
  - `api/v1/{system,uploads,backup}.py`, file miei;
  - `api/v1/settings.py`, di A (2 righe);
  - `api/v1/brokers.py`, di W (1 riga);
  - `api/v1/portfolio_api.py`, di J (2 import pigri);
  - `ai_export/components/drawdown_context.py`, di J;
  - con D1 sì, anche 17 file di J (11 plugin di rischio, `risk/service.py`, `risk/eligibility.py`,
    `financial_math/portfolio/daily_state.py`, `portfolio_service.py` ×2, `series_preparation.py`,
    `portfolio_allocation_source.py`) e `asset_sources/crud.py` di X.
- **CP1, test**:
  - 9 file dello scheduler;
  - 8 delle soglie, compresa la guardia `test_layer_boundaries.py:168` di J;
  - `test_static_uploads`, `populate_mock_data.py:80`, `test_file_preview`, `test_date_sentinel`,
    `test_container_registry`, `test_asset_prices_export`, `test_backup_export_extras`;
  - un commento in `updateCheck.test.ts:326`, di A.
- **CP1, doc**:
  - `developer/frontend/components/core-ui/file-upload.md`, `developer/frontend/data-quality-banner.md`,
    `developer/backend/fx/configuration.md`, `developer/backend/scheduler.md`, `developer/backend/risk/architecture.md`
    (×3), `developer/architecture/database/index.md` (×3), `developer/architecture/overview.md`,
    `developer/architecture/security.md`;
  - `.github/instructions/backend.instructions.md`.
- **CP2**:
  - `main.py`, `config.py` (`git mv` in `config/__init__.py`) e i moduli nuovi di `platform/`;
  - le patch sul lifespan: `test_post_migration.py`, `test_market_calendar.py`, `test_signal_runtime.py`,
    `test_risk_scenario_catalog.py`; l'import in `test_db_config.py:124`;
  - `auth_service.py`, `donation_popup_service.py`, `web_link_finder.py`;
  - la doc che descrive il lifespan: `overview.md`, `database/index.md`, `settings.md`, `registry_pattern.md`,
    `tool_plugins.en.md`, `api/overview.md`, `scheduler.md`, `provider_justetf.md`, `risk/architecture.md`,
    `brim/architecture.md`, `assets/architecture.md`;
  - `.github/instructions/backend-db.instructions.md:126`.
- **CP3**: `config.py`, `instance_key.py`, `config_audit.py`, `dev.py` (`_ensure_shared_jwt_secret`), `.env.example`;
  doc `admin/configuration.en.md`, `admin/filesystem.en.md`, `developer/architecture/security.md`.
- **CP4**: `system.py`, `schemas/` (instance), `frontend/src/lib/features/instance/**`, `routes/(app)/+layout.svelte`
  e i suoi due test, `lib/api/zodios-client.ts` (aggancio), `lib/i18n/instance/**`.
- **CP5**:
  - CP5a: `api/v1/system/{__init__,info,ready}.py`, `services/platform/readiness.py`, `schemas/system.py`,
    `utils/runtime/version.py`, `pyproject.toml`, un commento di `dev.py`; i test di versione e di sistema; la doc;
  - CP5b: `frontend/package.json`, le due righe radice di `package-lock.json`, `AboutTab.svelte`.
- **CP6**: `config/platform.py`, `api/v1/instance_block.py`, `api/v1/router.py` (una riga), `api/v1/system/block.py`,
  `schemas/system.py`, `services/platform/config_audit.py`, `.env.example`; `lib/api/zodios-client.ts` (il ramo 423),
  `features/instance/**`, `routes/(app)/+layout.svelte`, `lib/i18n/instance/**`; doc admin (pagina nuova) e
  sviluppatori.
- **CP7a e CP7b**: `Dockerfile`, `docker-compose*.yml`, `entrypoint.sh` (se serve), `dev.py` (docker build ed exec),
  `scripts/cli_base.py` (solo se serve per N-8), `static_site.py`, `security_headers.py`; test
  `utils dev-cli-image`, `release-image-contract`; doc `admin/docker_advanced.en.md`,
  `developer/dev_workflow.en.md`.
- **Condivisi da chiedere al coordinatore**: `dev.py` (CP3, CP7a), `scripts/test_runner/_backend_*.py` (voci mie, in
  aggiunta), `backend.instructions.md`, `backend-db.instructions.md`, `zodios-client.ts`. Propongo il testo per
  `CHANGELOG` e per la navigazione di MkDocs.

## 6. Conflitti previsti

| Con | Dove | Gestione |
|---|---|---|
| J | `data_quality_thresholds` (17 file), `date_sentinel` (3), 2 test che fanno patch sul lifespan, la guardia del layer | CP1 integrato prima che J cominci il codice; altrimenti D1 = lo sposta J |
| X | `asset_sources/crud.py` (1 import), `web_link_finder.py` (CP2), `test_market_calendar.py` (patch sul lifespan); `provider_registry` (lo decide X); la chiave d'istanza | X sposta `web_link_finder` in `assets/`: rinomina e modifica si uniscono, oppure applico la modifica sul nuovo percorso all'aggiornamento di base |
| A | `auth_service.py:104`, `donation_popup_service.py:39`, `api/v1/settings.py` (import), `updateCheck.test.ts` (commento), il layout (flag degli aggiornamenti), la pagina di login che usa `instanceConfig` | A sposta i servizi in `accounts/`: stessa gestione. D2 per chi definisce le variabili F05 |
| W | `api/v1/brokers.py:89` (1 import) | banale |
| Z | `scheduler/` (dopo CP1 è di Z), passi e middleware, sezione di config | Z non tocca lo scheduler prima di CP1 |
| B | `backup_service`, un passo prima del DB, `secrets/` dentro i backup, i file Docker dopo CP7a | sequenza CP1 → CP3 → CP7a → B |
| Coordinatore | un commit su `main.py` | CP2 dopo il suo ingresso; i gestori statici passano com'erano in `static_site.py` |
| A (dal treno) | `main.py:58` (import), `services/scheduler/settings.py:11`, `api/v1/uploads.py:39` | previsti dal coordinatore; A integra dopo H e X |
| Colori | `app.html` e i file del lotto A: non li tocco. `app.css` congelato. L'area avvisi usa classi esistenti; poi le funzioni di stato di R. Galleria: l'area avvisi non deve comparire negli scatti; il run di test non genera avvisi (dev.py passa `JWT_SECRET`) | da verificare con G |

## 7. Decisioni aperte (proposta in grassetto)

> **Esito (coordinatore, 14/10 alle 22:55).**
>
> - **Approvate come decisioni di coordinamento**: D1, D3 (vince `NOME`, con un avviso), D7, D8, D10, D11, D12 e D13.
> - **D2, nella forma più semplice**, da fare nel CP2: `config.py` passa a `config/__init__.py` con una rinomina pura, e
>   le sezioni nuove vanno in `config/<proprietario>.py` (platform H, accounts A, plugins X, sleep_wake Z, backup B,
>   email E).
> - **Sempre nel CP2**, `api/v1/system.py` diventa un pacchetto (regola C2), con `system/wake.py` di Z.
> - **Ancora aperte**, in lettura dal developer: le decisioni di prodotto D4, D5, D6, D9, D14 e TS1.
>
> **Decisioni del developer sui punti 12–17** (14/10, testo completo in `decisioni-analisi-20261014.md` a `5b0cea661`):
>
> - **D4, cambiata: niente sola lettura dentro l'app.** Quando l'abbonamento non è pagato, l'istanza si blocca.
>   - Dopo il login, l'admin vede una pagina di blocco con «Gestisci abbonamento» e lo scarico del backup completo.
>   - Gli altri utenti vedono una pagina che spiega la situazione e li invita a chiedere il backup all'admin. Non c'è
>     un export per utente.
>   - Restano permessi solo: accesso e uscita, la pagina di blocco, il backup per l'admin, la cancellazione del
>     proprio account e il risveglio programmato.
>   - La data di cancellazione arriva dal pannello, e l'istanza la mostra. Il nome della variabile lo sceglie H.
> - **D5**: sì, come proposto. **D6**: sì.
> - **D14, modificata**: niente `/system/version`. `/system/info` senza login risponde col minimo, cioè la versione;
>   con il login risponde tutto, come oggi.
> - **D9** (`/metrics`): rimandata, fuori dalla 1.3.
> - **TS1**: respinta. I test restano a strati, al più con i file divisi meglio.
> - L'avviso «registrazione aperta su un indirizzo pubblico» va nella nuova scheda «Sicurezza» di A, il registro
>   aperto dei controlli per l'admin, e non nell'area avvisi di H.
>
> **Effetti sul piano**:
>
> - CP5 perde `/system/version` e `/metrics` e guadagna la risposta minima di `/system/info`.
> - CP6 diventa il blocco dell'istanza: un elenco corto di permessi e una pagina al posto di avvisi e toast.
> - §3.5, §3.6 e §4 si riscrivono all'avvio di quei CP.
> - Il §13 è chiuso.

1. **D1**: `data_quality_thresholds` va in `platform/` in CP1, come dice P2.2, oppure lo lascio a J. **In CP1, se J e X
   non hanno ancora toccato quelle righe.**
2. **D2**, chi scrive la configurazione:
   - **pacchetto `config/`, un file per sezione scritto dal proprietario** (§3.2). H tiene la base, il profilo, la
     sola lettura e `/system/instance`, che compone un sotto-oggetto tipato per proprietario (link e flag di A, elenchi
     dei fornitori di X);
   - in alternativa: `config.py` unico, scritto solo da H su richiesta delle altre sessioni.
3. **D3**: con sia `NOME` sia `NOME_FILE`: **vince `NOME`, con un avviso** (come dice il piano), oppure errore, come fa
   postgres.
4. **D4**: sola lettura.
   - **Permessi**: change-password, la pulizia delle cache, `prices/current`.
   - **Bloccati**: i sync manuali dei prezzi, il profilo, la cancellazione dell'account.
   - Risposta: **403 con `code`**.
5. **D5**: header. **`nosniff` e `Referrer-Policy` sempre; frame e CSP-RO spenti in selfhosted** (iframe di Home
   Assistant e dei pannelli homelab) **e accesi in managed**.
6. **D6**: C-84. **`0.0.0` più commento**, oppure allineare le versioni a ogni rilascio.
7. **D7**: R2 come §10 n. 12. **Confermata.**
8. **D8**: 32-3. **gosu con gli id numerici**, oppure solo documentarlo.
9. **D9**: `/metrics`. **Dentro CP5, spento di default**, oppure rimandato.
10. **D10**: E2E dell'avviso di sola lettura. **Solo Vitest + pytest**: l'E2E richiederebbe un server dedicato o un
    interruttore solo per i test.
11. **D11**: P-4. **`tzdata-legacy` via apt**; `tzdata` PyPI facoltativo.
12. **D12**: i nomi `/system/instance`, `/system/admin-notices`, `/system/ready`, `/system/version`, `/metrics`.
13. **D13**: i nomi dei moduli spostati restano invariati, anche `backup_service.py`, che poi decide B.
14. **D14**: `/system/info` è pubblico ed espone le versioni delle dipendenze e dell'OS. **Dietro login, in CP5**: lo
    usano solo pagine con sessione; la versione resta pubblica su `/system/version`.

## 8. Rischi

- **Patch mute** nei test del lifespan (`raising=False`): diventano `raising=True` e una guardia controlla che i
  bersagli esistano.
- Import pigri dimenticati: grep dei vecchi percorsi a zero, `python -c "import backend.app.main"`, suite intera.
- Le tuple dei passi catturerebbero le funzioni all'import: per questo si chiamano con lambda risolte al momento.
- `.env.example` copiato nell'immagine: niente righe nuove non commentate.
- Un default di profilo sbagliato cambierebbe il self-hosted: test «selfhosted = come oggi» per ogni campo.
- Sola lettura: falsi blocchi su una POST che legge. Si previene con l'allow-list rivista, la guardia sulle rotte e la
  revisione di sicurezza (agente `security-review`) in CP6.
- Chiave d'istanza: corsa fra worker (si previene con `O_EXCL` e `link`); file vuoto dopo un crash, che va rifiutato,
  non rigenerato.
- Galleria e E2E: una richiesta in più all'avvio (`/system/instance`). Uno spec che conta tutte le richieste potrebbe
  accorgersene.
- **La doc admin è tradotta**: lascio debito di traduzione, perché traduco solo su richiesta esplicita.
- **Sorgente delle variabili**: una variabile letta oggi solo dall'ambiente non deve cominciare a leggere `.env`
  (§3.2). Un test per variabile lo verifica.
- `PROJECT_ROOT` si calcola dalla posizione del file: con `config/__init__.py` cambia la profondità.
- `nosniff`: un file servito con il tipo MIME sbagliato smetterebbe di caricarsi. Lo controllano la suite E2E e la
  galleria.

## 9. Test e selettori

Il preambolo è sempre lo stesso:
`PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6181 --data-dir /tmp/librefolio-r13-h …`

- **Base** prima di CP1: `all-backend` (conteggi), `lint`, `lint --dead-code`, l'hash di `api schema`, `mkdocs build`,
  `check-links`, `check_source_paths.py` (oggi 10 percorsi, 16 occorrenze, su 3844).
- **CP1**:
  - `services scheduler-state|scheduler-settings|scheduler-due|scheduler-leader|scheduler-loop|scheduler-jobs|scheduler-joblog-misc|scheduler-joblog-builders|scheduler-settings-misc`;
  - `services static-uploads|file-preview|date-sentinel|risk-all|financial-math`;
  - `utils container-registry`;
  - `api backup|backup-export-extras|asset-prices-export|uploads|uploads-serve-file|scheduler|system|risk`;
  - `test db populate --force --clean` sulla corsia (`--data-dir /tmp/librefolio-r13-h`): serve perché CP1 cambia un
    import di `populate_mock_data.py`;
  - poi `all-backend`.
- **CP2**: `db post-migration`, `services signal-runtime|risk-all|config-misc`, `api http-compression`, le guardie
  nuove (`services platform-*`), poi `all-backend`.
- **CP3**: `services config-misc` più i nuovi (`platform-config`, `platform-instance-key`, `platform-config-audit`),
  `utils dev-port-check`.
- **CP4**: `api system`, Vitest dei file toccati (`features/instance`, `routes/(app)/layout.*`), `front check`.
- **CP5**: `utils version`, `api system`, i nuovi `api system-ready`.
- **CP6**: i nuovi `services platform-read-only` (guardia delle rotte) e `api read-only`, Vitest.
- **CP7a e CP7b**: `utils dev-cli-image|release-image-contract|check-frontend-build`, `api http-compression`; prova Docker
  (build, avvio, healthcheck, `docker stop`) con il daemon acceso.
- **Registrazioni**: le voci nuove vanno nel catalogo del runner, in aggiunta, nelle mie sezioni.

## 10. Definizione di fatto

- **Per ogni CP**:
  - verdi mirati e `all-backend` con gli stessi conteggi della base (rinomina e taglio) o la base più i nuovi
    (funzioni);
  - `ruff` e `black` puliti; `--dead-code` senza reperti nuovi;
  - `api schema` invariato per i lotti di riordino; `api sync` pulito per i lotti con API;
  - `mkdocs build` stretto e `check-links` se cambia la doc; `check_source_paths.py` ≤ 10/16;
  - grep dei vecchi percorsi a zero in `backend/`, `scripts/`, `.github/`, `mkdocs_src/docs/developer/`;
  - rinomine con somiglianza ≥ 95 % in `git diff -M`;
  - piano aggiornato a ogni passo; porta 6181 libera; handoff FROZEN.
- **Di tutto il workstream**:
  - `main.py` di circa 40 righe;
  - zero `os.environ` fuori da `config.py`, salvo le eccezioni;
  - `.env.example` completo;
  - `*_FILE` per ogni segreto;
  - chiave d'istanza 0600;
  - prontezza e versione;
  - profilo e sola lettura con avviso;
  - lotto operativo chiuso;
  - righe del backlog (sezione H) per i residui.

## 11. Specialisti, dipendenze, runtime

- `test-author`: le patch del lifespan e la guardia, i test di config, `_FILE`, chiave, audit, sola lettura, header,
  ready/version, i Vitest e i mock del layout, `dev.py` docker.
- `docs-writer`: pagina nuova `developer/backend/platform.md` e aggiornamenti delle pagine per sviluppatori (EN);
  pagine admin EN (configuration, filesystem, docker_advanced, service_exposure, una nuova sul profilo gestito). Le
  traduzioni solo su richiesta.
- `security-review` alla fine di CP3 e CP6.
- **Skill** da caricare all'avvio del codice: `lint-format`, `testing-backend`, `testing-frontend`,
  `lint-format-frontend`, `devpy-i18n`, `devpy-docker`; `test-triage` quando un rosso non è ovvio.
- **Python**: nessuna dipendenza obbligatoria. Facoltativa: `tzdata` (PyPI).
- **`npm ci`**: serve prima della base completa e per CP4. Senza `node_modules` non ci sono build del frontend, Vitest
  e `api sync`, e `api http-compression` fallisce. Lo chiederò dopo l'errore confermato.
- **Docker**: daemon acceso per la prova di P-4 e di CP7a, oppure la esegue il developer.

## 12. C-49: diagnosi per Z (lettura del codice; la cura è di Z)

1. `scheduler_loop` (`scheduler.py:96-134`):
   - all'avvio dorme 5 s senza ascoltare lo shutdown;
   - poi controlla `shutdown_event` ogni 5 s (`sleep(5)` ×12).
   - Dopo `set()`, `await scheduler_task` (`main.py:315-316`) aspetta quindi fino a 5 s: tutta la tolleranza del
     runner. Basta questo a spiegare il sintomo.
   - Cura: `asyncio.wait_for(shutdown_event.wait(), timeout)`.
2. Un job dello scheduler in corso (refresh dei prezzi o storico) si aspetta senza limite.
3. Uvicorn non ha `--timeout-graceful-shutdown`. Lo stream SSE di ricerca e le richieste lente trattengono lo
   spegnimento, e `docker stop` manda SIGKILL dopo 10 s.
4. `shutdown_brim_parse_pool(wait=True)` e i pool quantistici aspettano il lavoro che è in corso.

H offre nel lifecycle un timeout facoltativo per passo, con default nessuno, cioè come oggi.

## 13. TS1: numeri per la decisione

- 266 file di test in 6 cartelle per livello: api 58, services 141, utilities 34, schemas 11, db 10, external 7, e2e 2.
- Il runner codifica 236 percorsi di test; l'app ha 348 moduli `.py` di servizio.
- Lo specchio sposterebbe circa 266 file e riscriverebbe 236 voci del runner, più la doc dei test, senza nessun guadagno
  di comportamento.
- Proposta: decidere dopo CP2 e dopo i riordini di A, X, W, J. Il default che propongo è **no**, con solo le cartelle
  `test_services/platform/` e `files/` per i test nuovi, se il developer vuole la vicinanza.

## 14. Avanzamento

### Analisi ✅ (2026-10-14)

> **Note implementazione**:
>
> - L'analisi è stata consegnata al coordinatore, con la sintesi e il piano completo (§0–§13) e le decisioni D1–D14.
> - Ci sono state due riletture. La seconda ha corretto i percorsi completi nell'allow-list (`/assets/...`,
>   `/brokers/import/...`) e il numero dei file di J (17). Ha anche diviso CP7 in 7a e 7b e aggiunto D14.
>
> **Fuori pista**:
>
> - All'avvio della sessione l'app ha rinominato il ramo da `e-alfy-sturdy-memory` a `e-alfy-h-piattaforma`.
> - Il developer ha chiesto uno STOP (FROZEN). Dopo la ripresa, l'app si è riavviata e ha interrotto il turno: la
>   bozza dell'analisi, salvata nella cartella di sessione, non si è persa.

### Via libera parziale: solo CP1 (coordinatore, 2026-10-14 alle 22:55)

> Parole del developer, alla lettera, mentre leggeva il documento delle decisioni: «chat, sto leggendo
> LibreFolio_developer_journal/Release_2/Phase_1/decisioni-analisi-20261014.md — ho appena finito le prime 11 domande e
> sto iniziando piattaforma, ma ho già messo varie note dev, leggi intanto quelle, vedi se con quelle risposte devi
> aggiornare quello che viene dopo e poi vedi tu se aspettare che leggo tutto, o intanto grazie a queste riesci ad
> avviare qualche lavoro».
>
> **Decisione del coordinatore** su questa delega:
>
> - parte solo CP1, che è riordino puro e non dipende da decisioni di prodotto ancora aperte;
> - il resto aspetta la lettura completa del developer.
>
> **Base**: `c9bb8f257643c0b770788033789425b41ba16715`. È un fast-forward da `459131eb8` che porta solo il journal,
> `scripts/visual_review/gallery_snapshot.sh` e `TODO_FUTURI.md`. Base verificata, worktree pulito.

### CP1 passo 0 — prerequisiti della corsia ✅ (2026-10-14)

> **Note implementazione**: `npm ci --no-audit --no-fund` in `frontend/`, dal lock (regola C5), rc 0.
>
> - npm 11 non ha eseguito gli script d'installazione di `esbuild` e `fsevents`, che chiede di approvare.
> - Nessun file tracciato è cambiato.
>
> **Fuori pista**: la prima prova
> (`PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6181 --data-dir /tmp/librefolio-r13-h api system`)
> si è fermata prima della raccolta dei test: «Shared backend exited during startup (code 1)».
>
> - **Causa**: senza `node_modules`, `dev.py server --test` ricostruisce il frontend. `api sync` lancia
>   `npm run generate-api`, e quello chiama `npx openapi-zod-client`.
> - **Cosa ha toccato**:
>   - nessun file tracciato, nessun DB, nessuna porta;
>   - solo artefatti ignorati: il client generato in `frontend/src/lib/api/`, `frontend/static/fonts/`,
>     `mkdocs_src/docs/javascripts/vendor/`, `scripts/test_runner/.campaign.json`.
> - **La cache di npx dell'utente**: la voce esisteva dall'8/09 con la versione del lock; è cambiata solo la data della
>   cartella (verificato dal coordinatore, che ha detto di lasciarla).
> - **Regola aggiornata**: il coordinatore ha aggiunto il caso «`npm ci` anche prima dei test del solo backend col
>   server condiviso» alle istruzioni e al §6 del piano generale (`793395913`).
>
> **Fuori pista 2 (seconda trappola della base, trovata da J e riportata dal coordinatore)**: anche con `node_modules`,
> il primo `all-backend` di un worktree nuovo può cadere con «Shared backend did not answer within 300s». Il server
> condiviso costruisce prima il frontend in debug e il sito MkDocs, e lo fa dentro il limite di 300 s
> (`scripts/test_runner/_server.py:48`).
>
> - La mia prima base era ancora nei `services`, e il server condiviso non era partito: l'ho fermata io.
> - Ho fatto le due build:
>   - `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front build --debug`, rc 0: svelte-check
>     0 errori e 0 avvisi, vite 2 min 19 s e 3 min 4 s;
>   - `pipenv run python dev.py mkdocs build`, già fatta per la base statica.
> - Poi ho rilanciato la base da capo, con `--fresh-run`.

### Base di CP1 (2026-10-14, notte) — in corso

> **Statici**, sulla base `c9bb8f257`. Log in `/tmp/librefolio-r13-h-base/`.
>
> - `dev.py lint` (ruff): «All checks passed!».
> - `black --check backend scripts dev.py`: 29 file da riformattare, già alla base. Non li tocco: black si applica solo
>   ai file che CP1 modifica e che erano già puliti.
> - `lint --dead-code --scope backend`: 10 non referenziati, 26 referenziati solo dai test.
> - `dev.py api schema`, senza `info.version`:
>   - `openapi.json`: 113 percorsi, sha256 `1da07e609d1ffad8…`;
>   - `tool-contracts.openapi.json`: sha256 `238c1e4b84afdbdc…`.
> - `mkdocs build`: rc 0, con 3012 URL relativi risolti. `mkdocs check-links`: 95 link validi.
> - `check_source_paths.py`: 7 percorsi inesistenti (10 occorrenze) su 3844 citati, in 6 pagine.
> - **`all-backend`**: con `--workers 2`, sulla corsia 6181.
> - **`all-backend` ✅**:
>   - comando: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test -q --fresh-run --workers 2 --test-port 6181 --data-dir /tmp/librefolio-r13-h all-backend`;
>   - esito: 7/7 categorie verdi in 23 min 22 s. Dai log per unità, **11 351 passed, 3 skipped, 0 failed**; il DB ha
>     13/13 azioni del runner;
>   - porta 6181 libera alla fine.

### CP1 passo 1 — rinomina e riferimenti ✅ (2026-10-14, notte)

> **Note implementazione**:
>
> - **Spostamenti**, sette `git mv`: `scheduler/`, `container_registry.py`, `date_sentinel.py`,
>   `data_quality_thresholds.py` e `backup_service.py` in `services/platform/`; `static_uploads.py` e `file_preview.py`
>   in `services/files/`.
>   - I due `__init__.py` nuovi hanno solo la docstring.
>   - Nomi invariati (C1). Niente shim e niente barili nuovi.
> - **Riferimenti**: 82 file e 137 righe, con una sostituzione esatta sui percorsi puntati e su quelli con la barra.
>   - Codice, test, patch dei test, stringhe del runner, `coverage_analysis.py`, doc per sviluppatori e un commento
>     in `updateCheck.test.ts`.
>   - Nella devWiki, solo le righe delle tabelle «Source files» (C6, come B4 di T-1). La prosa resta: 9 menzioni in
>     8 pagine, voce nel backlog.
> - **`.github/instructions/backend.instructions.md`**: `platform/` e `files/` nella mappa e nella tabella «Where to
>   Find Things».
> - **Lint**:
>   - ruff ha trovato 10 import fuori ordine (I001), corretti con `--select I --fix`: solo righe d'import spostate;
>   - black sui 66 file `.py` toccati, nessuna modifica. `scripts/coverage_analysis.py` resta fuori da black: era già
>     sporco alla base;
>   - ruff pulito.
> - **Grep dei vecchi percorsi**: zero in `backend/`, `scripts/`, `.github/`, `mkdocs_src/docs/`, `frontend/`,
>   `dev.py`, `pyproject.toml`, `README.md`, `CHANGELOG.md`, `TODO_FUTURI.md`.
>   - Restano la prosa della wiki (voluta) e la cache di graphify tracciata in `LibreFolio_devWiki/graphify-out/`,
>     che è generata e si rigenera.
> - **`git diff -M`**: tutte le rinomine sono al 97–100 %, salvo due.
>   - `scheduler/scheduler.py` è al 91 %: 4 import interni, righe lunghe in 134.
>   - `scheduler/__init__.py` git lo vede come cancellato e ricreato: 2 delle sue 6 righe sono gli import.
>   - È inevitabile, perché qualunque forma dell'import cambia quelle righe.
> - **Import di prova**: `import backend.app.main` passa.
>
> **Mirati** (corsia 6181), tutti PASSED: `services scheduler-loop`, `scheduler-leader`, `scheduler-jobs`,
> `static-uploads`, `file-preview`, `date-sentinel`, `financial-math` (la guardia dello strato); `utils container-registry`.
> Il popolamento del DB della corsia lo copre l'azione `db populate` dentro `all-backend`.
>
> **Fuori pista 3**: il commento corretto in `updateCheck.test.ts` rende il frontend «da ricostruire», perché
> `check_frontend_needs_build` confronta le date di tutti i file di `frontend/src`, anche quelle dei test.
>
> - Il server condiviso lo avrebbe ricostruito dentro i suoi 300 s d'avvio.
> - Ho fermato la run appena partita, rifatto `dev.py front build --debug` (rc 0, svelte-check 0 errori) e rilanciato.
>
> **Fuori pista 4**: la prima `all-backend` dopo CP1 ha chiuso 6/7, con 2 rossi in `test_data_quality_thresholds.py`.
>
> - **Causa**: il test costruiva il percorso del modulo a pezzi, `APP_ROOT / "services" / "data_quality_thresholds.py"`
>   (r. 38), e la sostituzione dei percorsi non lo vede.
> - **Cura**: `"services" / "platform" / ...`.
> - Ho cercato i nomi dei moduli spostati come stringhe in `backend/`, `scripts/`, `dev.py` e `frontend/`: nessun
>   altro caso.
> - `services risk-all`: 896 passed.

### CP1 passo 2 — i verdi, confrontati con la base ✅ (2026-10-15, notte)

> **Note implementazione**:
>
> - **`all-backend`**, con gli stessi flag della base: 7/7 verdi in 13 min 19 s. **11 351 passed, 3 skipped, 0
>   failed**, gli stessi conteggi della base; DB 13/13.
> - **Statici**:
>   - ruff pulito;
>   - black invariato (i file toccati e già puliti restano puliti);
>   - dead code identico alla base (10 + 26), con i percorsi nuovi;
>   - `dev.py api schema` scritto in `/tmp`: `openapi.json` e `tool-contracts.openapi.json` identici alla base, senza
>     `info.version`.
> - **Doc**: `mkdocs build` rc 0 (3012 URL relativi risolti, lo stesso avviso di Material della base); `check-links`
>   95 link validi.
> - **devWiki**: `check_source_paths.py` dà 5 percorsi inesistenti (8 occorrenze). Sono quelli della base meno
>   `frontend/build/` e `mkdocs_src/site/`, che ora esistono perché li ho costruiti: nessun buco nuovo.
> - `git diff --check` pulito; porta 6181 libera.

### Checkpoint CP1 🧊 (2026-10-15) — FROZEN, in attesa del coordinatore

> Handoff inviato al coordinatore: 13 rinomine, 80 file modificati, 3 nuovi. Commit proposto:
> `refactor(services): move platform and file modules`. Nella sezione H del backlog: H-1 e H-2.

### Aggiornamento di base con A1 ✅ (2026-10-15, notte)

> **Note implementazione**:
>
> - Il coordinatore ha aperto `git merge --no-ff --no-commit 769cc31cb` (A1) sul mio `7366c0355`: 6 conflitti, tutti
>   d'import fra i percorsi miei (`platform/`, `files/`) e quelli di A (`accounts/`).
> - I file risolti tengono i percorsi nuovi di tutti e due: `main.py`, `api/v1/settings.py`, `api/v1/uploads.py`,
>   `portfolio_service.py`, `test_layer_boundaries.py`, `coverage_analysis.py`.
>   - In `settings.py` e `uploads.py` c'erano due righe vecchie fuori dai marcatori: le ho corrette.
>   - `platform/scheduler/settings.py:11` si era fuso da solo, sul percorso giusto.
> - **Revisione combinata**:
>   - `front build --debug` ok;
>   - `all-backend` 7/7, **11 351 passed, 3 skipped, 0 failed**, uguale alla base;
>   - `api schema` uguale a quello di `769cc31cb`, escluso `info.version`;
>   - ruff pulito; grep dei vecchi percorsi, miei e di A, a zero.
> - **Integrazione**: merge `79b866f9a` (coordinatore), poi CP1 in `dev_release2` con `6a605904c`. Il mio ramo è
>   avanzato in fast-forward a `6a605904c`.

### CP2 diviso — via per CP2a (coordinatore, 2026-10-15 alle 00:49)

> **Ordine approvato**: CP2a → CP3 → CP4 → CP2b (dopo il commit del coordinatore su `main.py`) → CP5 → CP6 → CP7a e
> CP7b, ciascuno con il suo checkpoint FROZEN.
>
> **Precauzioni per CP2a**:
>
> - `web_link_finder.py` non si tocca: X lo sta spostando in `services/assets/`. Le sue 7 letture le sposto sul
>   percorso nuovo dopo l'ingresso di X, in CP3 o in un lotto a parte.
> - Nei file di A, `accounts/auth_service.py:104` e `accounts/donation_popup_service.py:39`, va bene una riga
>   ciascuno; `platform/scheduler/scheduler.py:97` va bene anche lui, perché Z non è partito.
>
> **Mia decisione**: il pacchetto `api/v1/system/` (C2) esce da CP2a e va all'inizio di CP4. Il CP1 di X, committato
> sul suo ramo ma non ancora in `dev_release2`, cambia probabilmente l'import di `system.py:26`. Dividere ora il file
> metterebbe X in conflitto su una riga spostata in un altro modulo.

### CP2a — il pacchetto `config/` e le letture d'ambiente (2026-10-15) — in corso

> **Disegno**, in due commit:
>
> - **Rinomina**: `git mv backend/app/config.py backend/app/config/__init__.py`. L'unica riga cambiata è
>   `PROJECT_ROOT` (`parents[3]`), più i riferimenti al percorso nei commenti, nella doc e nelle tabelle della wiki.
> - **Sezioni e letture**:
>   - `config/platform.py` (H): `scheduler_disabled()`, `configured_jwt_secret()`, `owning_test_lane_id()`;
>   - `config/accounts.py` (A, creato da H): `donation_popup_disabled()`;
>   - le cinque letture sparse passano da quelle funzioni: `main.py:70` usa `is_test_mode()`;
>   - ogni variabile tiene la sorgente di oggi, solo ambiente e mai `.env`, con la stessa semantica.
>   - La guardia: nessuna lettura d'ambiente in `backend/app` fuori da `config/`, salvo `web_link_finder.py`. Le
>     scritture di `spawn_worker` sono ammesse.

#### CP2a passo 1 — rinomina del pacchetto ✅ (2026-10-15)

> **Note implementazione**:
>
> - `git mv backend/app/config.py backend/app/config/__init__.py`. Cambiano due righe: `PROJECT_ROOT =
>   Path(__file__).parents[3]` e il suo commento, che diceva «two levels up» ed era sbagliato già prima.
> - Verifiche: `PROJECT_ROOT` è la radice del repo; `.env`, `DEFAULT_PROD_DATA_DIR` e `import backend.app.main` sono
>   invariati.
> - **Riferimenti al percorso**:
>   - commenti in `alembic/env.py` e `alembic/check_constraints_hook.py`;
>   - docstring in `test_server_helper.py` e `test_dev_cli_db_path.py`;
>   - doc `developer/architecture/database/index.md` e `developer/backend/risk/architecture.md` (×2);
>   - 15 righe di tabelle «Source files» della devWiki (C6). Il controllo dei percorsi resta a 5/8. La prosa va in
>     H-1.

#### CP2a passo 2 — sezioni e letture spostate ✅ (2026-10-15)

> **Note implementazione**:
>
> - **Sezioni nuove**:
>   - `config/platform.py` (H): `scheduler_disabled()`, `configured_jwt_secret()`, `owning_test_lane_id()`;
>   - `config/accounts.py` (A): `donation_popup_disabled()`.
>   - Solo ambiente, con la semantica di prima: `LIBREFOLIO_NO_SCHEDULER` disattiva con qualunque valore non vuoto,
>     anche `0`; un `JWT_SECRET` vuoto conta come assente.
> - **Letture spostate**:
>   - `main.py`: via `import os` (r. 8); la r. 70 usa `is_test_mode()`, che era già importata;
>   - `api/v1/system.py`: via `import os`, un import nuovo, `owning_test_lane_id()`;
>   - `platform/scheduler/scheduler.py` (Z): via `import os`, un import, `scheduler_disabled()`;
>   - `accounts/auth_service.py` (A): via `import os`, un import, `configured_jwt_secret()`;
>   - `accounts/donation_popup_service.py` (A): via `import os`, un import, `donation_popup_disabled()` e la docstring
>     di due righe.
> - **Fuori da `config/`**: restano le letture di `web_link_finder.py` (eccezione dichiarata) e le scritture di
>   `spawn_worker`.
> - **Doc e istruzioni**:
>   - `.github/instructions/backend.instructions.md`: la mappa e la riga «Config & Data Paths»;
>   - `developer/architecture/settings.md` (docs-writer): l'admonition del terzo livello, con il pacchetto, le
>     sezioni e la regola con la sua guardia. `mkdocs build` passa.
> - **Mirati**, tutti PASSED: `services config-misc` (4), `donation-popup` (19), `scheduler-loop` (5);
>   `utils runtime-isolation` (167), `dev-cli-db-path` (15); `db post-migration` (37).
> - **Fuori pista**: nessuno.

#### CP2a passo 3 — la guardia e i verdi ✅ (2026-10-15, notte)

> **Note implementazione**:
>
> - **Guardia** (test-author): `backend/test_scripts/test_services/test_config_package.py`, 451 test puri.
>   - Il rilevatore AST si prova da solo: 34 forme di lettura, 11 ammesse.
>   - Un caso per ognuno dei 421 file di `backend/app` fuori da `config/`.
>   - L'eccezione `web_link_finder.py` è legata al nome del file, a cricchetto: quando il file non legge più, o non
>     esiste più, la voce va tolta.
>   - Le quattro funzioni conservano anche le stranezze di prima.
>   - Il test controlla che `PROJECT_ROOT` sia la radice.
>   - Sui file di `HEAD`, il rilevatore trova le 5 letture di prima alla riga giusta.
> - **Runner**: `services config-package`, `isolation="pure"`, dopo `config-misc`. Aggiornato il `print_info` di
>   `config-misc`.
> - **`all-backend`**, con i flag della base: 7/7 in 11 min 55 s; **11 802 passed, 3 skipped, 0 failed**. Sono 451 in
>   più rispetto a CP1 + A1: esattamente i test nuovi.
> - **Statici**:
>   - ruff pulito; black invariato sui 14 `.py` toccati;
>   - dead code identico, salvo il percorso di `user_service` che ha spostato A1;
>   - `api schema` identico alla base.
> - **Doc e wiki**: `mkdocs build` passa (docs-writer); `check_source_paths.py` dà 5/8, invariato.
> - **Altro**: rinomina al 99 %; grep di `app/config.py` a zero fuori dal journal e dalla prosa della wiki;
>   `git diff --check` pulito; porta 6181 libera.

### Checkpoint CP2a 🧊 (2026-10-15) — FROZEN, in attesa del coordinatore

> Handoff inviato; il coordinatore ha committato CP2a in tre commit: `88bb9d346` (rinomina), `103489f3f` (sezioni e
> letture), `b884efcb7` (journal).

### Aggiornamento di base con A2, W1 e W2 ✅ (2026-10-15, notte)

> **Note implementazione**:
>
> - Il coordinatore ha fuso `dev_release2` a `e0816ec9c` nel mio ramo: merge `60f8a35ce`, senza conflitti.
>   `_backend_services.py` e il backlog si sono fusi da soli. Porta A2 (frontend in `lib/features/`), W1 e W2
>   (`services/transactions/`, `services/brokers/`).
> - **Revisione combinata `60f8a35ce`**:
>   - `services config-package`: 465 passed. Sono 14 casi in più, uno per ogni modulo nuovo di W, e nessuno legge
>     l'ambiente;
>   - `api schema` uguale a quello di `e0816ec9c`, escluso `info.version` (`1da07e609d1ffad8` e
>     `238c1e4b84afdbdc`);
>   - `front build --debug` rc 0, svelte-check 0 errori: serviva, perché A2 ha cambiato `frontend/src`;
>   - `all-backend` (`-q --fresh-run --workers 2`, corsia 6181): 7/7 in 12 min 06 s, **11 816 passed, 3 skipped, 0
>     failed**. Rispetto a CP2a sono i 14 casi della guardia: W1 e W2 hanno modificato 12 file di test senza
>     aggiungerne.
> - **Integrazione**: `dev_release2` = `60f8a35ce` in fast-forward (coordinatore). Il mio ramo coincide.

### CP3 — segreti e chiave d'istanza (F03) (2026-10-15) — in corso

> **Via** del coordinatore (2026-10-15, notte), subito dopo l'ingresso di CP2a. Le 7 letture di `web_link_finder.py`
> si spostano quando X ha portato il file in `services/assets/`.
>
> **Avvisi all'admin: la scheda «Sicurezza» di A** (decisione del developer, punto 4: un posto solo per le cose
> sospette). A definisce il registro dei controlli nel suo A8: un controllo è id, gravità, chiave i18n e dettaglio,
> valutato a richiesta da un endpoint solo per admin. In CP3 i controlli vanno solo nei log, scritti come funzioni che
> rendono lo stato; li registro nel registro di A quando A8 è entrato. `/system/admin-notices` (D12) non si fa.
>
> **Disegno**:
>
> - **Base di `config/`** (H): `env_secret(nome)` legge `NOME`, se non vuoto, altrimenti il file indicato da
>   `NOME_FILE`.
>   - Del file si tolgono solo gli a capo finali. Un percorso relativo parte dalla cartella del progetto.
>   - File mancante, illeggibile, vuoto, non UTF-8 o più grande di 64 KiB: `SecretFileError`, con la variabile e il
>     percorso, mai il contenuto.
>   - Con `NOME` e `NOME_FILE` insieme vince `NOME` (D3), e il controllo lo segnala. Vale per `JWT_SECRET` e per ogni
>     variabile `LIBREFOLIO_*`, quindi anche per i segreti che le altre sessioni aggiungeranno.
>   - Come `JWT_SECRET` oggi, si legge solo dall'ambiente: `dev.py` e Compose ci mettono `.env`.
> - **`config/platform.py`**: `configured_jwt_secret()` passa da `env_secret`; nuovo `configured_instance_key()`.
>   La semantica di `JWT_SECRET` resta quella di CP2a.
> - **`services/platform/instance_key.py`**: la chiave d'istanza.
>   - Da `LIBREFOLIO_INSTANCE_KEY`, poi da `LIBREFOLIO_INSTANCE_KEY_FILE`, poi da `<DATA_DIR>/secrets/instance.key`.
>   - Il file si genera al primo uso: 32 byte casuali in base64url, cartella 0700, file 0600. Viene scritto in un file
>     temporaneo e pubblicato con `os.link`, così fra più worker vince una chiave sola. Dove i link fisici non ci sono,
>     si crea con `O_EXCL`.
>   - Una chiave è un testo di almeno 32 caratteri. Un file vuoto o corto è un errore e non si rigenera mai.
>   - I consumatori non vedono la chiave: `derive_key(scopo)` è HKDF-SHA256 (RFC 5869) con la sola libreria standard.
>     Serve a X (segreti dei plugin) e a B (backup). Finché non lo chiamano, il dead code lo segnala come «usato solo
>     dai test».
> - **`services/platform/config_audit.py`**: i controlli, ognuno una funzione che rende id, gravità, chiave i18n,
>   dettaglio e sintesi inglese per il log.
>   - JWT effimero (info) o corto (warning); `NOME` insieme a `NOME_FILE` (warning); chiave d'istanza illeggibile
>     (error) o con permessi larghi (warning); `SESSION_COOKIE_SECURE=never` (warning); log `DEBUG` o `TRACE` (info).
>   - All'avvio, una riga nel lifespan di `main.py`: un segreto configurato ma rotto ferma l'avvio. Un file generato
>     rovinato invece si scrive come errore, e l'avvio continua.
> - **`dev.py`**: `_ensure_shared_jwt_secret` non genera niente con `JWT_SECRET_FILE`, e toglie un `JWT_SECRET` vuoto
>   che nasconderebbe il file.
> - **`validate_test_data_dir`**: `secrets/` e `secrets/instance.key` fra i percorsi gestiti.
> - **`.env.example`**: completo e diviso per funzione.
>   - Sezioni nuove: segreti, motori di rischio, le sezioni vuote di A, X, Z, B ed E, le variabili impostate dagli
>     strumenti.
>   - Le righe non commentate restano quelle di oggi, perché il file diventa `/app/.env` nell'immagine.
>   - `LIBREFOLIO_DISABLE_DONATION_POPUP` resta fuori, per scelta di A.
>   - Una guardia controlla che ogni variabile letta in `config/`, ogni campo di `Settings` e ogni variabile del
>     compose sia documentata, e che l'insieme delle righe non commentate non cambi.

#### CP3 passo 1 — il codice ✅ (2026-10-15, notte)

> **Note implementazione**:
>
> - **`config/__init__.py`**:
>   - nuova sezione «Secrets»: `SecretFileError`, `env_secret()`, `read_secret_file()`, `secrets_set_twice()`;
>   - `secrets/` e `secrets/instance.key` fra i percorsi gestiti di `validate_test_data_dir`;
>   - la docstring del modulo cita `secrets/` e la regola `NOME_FILE`.
> - **`config/platform.py`**: `configured_jwt_secret()` passa da `env_secret("JWT_SECRET")`, con la stessa semantica di
>   prima quando `_FILE` manca; nuovo `configured_instance_key()`.
> - **Moduli nuovi in `services/platform/`**: `instance_key.py` (`derive_key`, `hkdf_sha256`, `instance_key_status`,
>   `InstanceKeyError`) e `config_audit.py` (`ConfigCheck`, cinque controlli, `run_config_checks`,
>   `log_configuration_audit`). Aggiornata la docstring del pacchetto.
> - **`main.py`**: un import e una riga nel lifespan, dopo «Starting LibreFolio»:
>   `await asyncio.to_thread(log_configuration_audit)`. Righe lontane dai gestori statici.
> - **`dev.py`**: `_ensure_shared_jwt_secret` gestisce `JWT_SECRET_FILE`.
> - **`.env.example`**: diviso in sezioni, 167 righe. Le 9 righe non commentate sono quelle di prima, con gli stessi
>   valori.
> - **`.github/instructions/backend.instructions.md`**: la mappa di `platform/` e la riga «Config & Data Paths».
> - **Prove a mano** (script in `/tmp`, dati in una cartella temporanea poi cancellata):
>   - `hkdf_sha256` rende i tre vettori della RFC 5869;
>   - `JWT_SECRET_FILE` funziona, `JWT_SECRET` vince sul file, file mancante o vuoto danno errore;
>   - la chiave nasce 0600 in una cartella 0700, 44 byte, senza file temporanei rimasti, ed è stabile;
>   - con il file a 0644 il controllo dà `warning`; una chiave configurata corta ferma `log_configuration_audit`.
> - **Statici**: `import backend.app.main` passa. ruff e black puliti sui file del backend. `dev.py` era già sporco per
>   black alla base, quindi non lo riformatto; ruff non lo controlla (`dev.py lint` guarda solo `backend/`).
>   `api schema` è identico alla base (`1da07e609d1ffad8`, `238c1e4b84afdbdc`).
>
> **Fuori pista**: nessuno. Le scelte rispetto al §3.3:
>
> - `JWT_SECRET_FILE` non è un campo `SecretStr` di `Settings`, ma passa da `env_secret()`, solo dall'ambiente. È la
>   regola di CP2a, che `JWT_SECRET` segue già.
> - Ai `_FILE` che aggiungeranno A, X, Z, B ed E basta chiamare `env_secret()`.
> - Il controllo «metriche senza token» cade con D9, quello «sola lettura» con D4.

> **Dal coordinatore (2026-10-15, notte)**: X CP1 e CP2a sono in `dev_release2` (`64a5a3fe7`). `web_link_finder.py` è
> ora `services/assets/web_link_finder.py`, e la guardia `config-package` lo esenta ancora per nome di file. Le sue 7
> letture si spostano in un lotto a parte, dopo l'aggiornamento di base che il coordinatore fa al checkpoint di CP3:
> CP3 parte da `60f8a35ce`, che non contiene lo spostamento.

#### CP3 passo 2 — test, doc e revisione di sicurezza ✅ (2026-10-15, notte)

> **Note implementazione**:
>
> - **Test** (test-author): quattro file nuovi in `backend/test_scripts/test_services/`.
>   - `test_config_secrets.py` (44), `test_instance_key.py` (75), `test_config_audit.py` (48) e
>     `test_env_example.py` (36).
>   - `test_instance_key.py` copre anche i vettori della RFC 5869, la gara fra 6 processi con e senza link fisici, e
>     l'attesa limitata sul file appena creato.
>   - `test_env_example.py` controlla che ogni variabile letta sia documentata, compresi i campi di `Settings` e le
>     variabili dei compose, e che le righe non commentate restino quelle.
>   - Nei file esistenti: IMG-010e/f/g in `test_dev_cli_image.py`, `secrets/` in `test_runtime_isolation.py`, il test
>     del JWT di `test_config_package.py` reso ermetico.
>   - Nel runner, quattro voci nuove e pure: `services config-secrets`, `config-instance-key`, `config-audit`,
>     `config-env-example`.
>   - Primo giro, tutti verdi: 44, 75, 48, 36; `config-package` 467; `utils dev-cli-image` 35; `runtime-isolation`
>     170.
> - **Doc** (docs-writer), solo inglese, senza timbro: il debito di traduzione resta visibile.
>   - Admin: `configuration.en.md` (segreti, `*_FILE` con l'esempio dei Docker secrets, chiave d'istanza, controlli
>     all'avvio), `filesystem.en.md` (`secrets/`, backup) e `index.en.md`.
>   - Sviluppatori: `security.md`, `settings.md`, `database/index.md`, e in più `overview.md` (il passo nuovo del
>     lifespan) e `users_and_brokers.md`.
>   - `mkdocs build` e `check-links` passano. `translate-validate` dà 63 errori, tutti debito nuovo delle tre pagine
>     admin tradotte.
> - **Revisione di sicurezza** (agente `security-review`): quattro reperti. I dettagli sono solo nei messaggi al
>   coordinatore.
> - **Cambi di comportamento** dopo la revisione e i reperti di test-author:
>   - un segreto vuoto o di soli spazi conta come assente, per `NOME` e per `NOME_FILE`. Cambia la regola di CP2a, per
>     cui un `JWT_SECRET` di soli spazi era la chiave;
>   - un file vuoto o bianco ferma l'avvio;
>   - il BOM UTF-8 iniziale si toglie;
>   - `_ensure_shared_jwt_secret` non toglie più niente dall'ambiente;
>   - una corsia di test firma le sessioni e deriva le chiavi con segreti suoi: `configure_test_runtime` toglie
>     `INSTANCE_TRUST_SECRETS` dal suo ambiente. `scripts/cli_base.py` è condiviso: aspetto l'OK del coordinatore;
>   - `derive_key`: la lunghezza entra nella derivazione, e scopo e lunghezza si validano prima di leggere la chiave;
>   - `_key_file_present()`: una cartella `secrets/` che non si apre è un `InstanceKeyError` chiaro, mai una chiave
>     nuova. Prima era un `PermissionError` di `Path.exists()` su Python 3.13. Un link simbolico rotto conta come
>     presente;
>   - i messaggi indicano la fonte della chiave, compresa la variabile `_FILE` col suo percorso.
>
> **Fuori pista**: il controllo d'isolamento `validate_test_data_dir`, in modalità test, ora controlla anche
> `secrets/instance.key`. Con `secrets/` non attraversabile solleva un `PermissionError` grezzo, come già faceva per
> `sqlite/`. È fail-closed e preesistente: non lo cambio.

> **Decisioni del coordinatore** (2026-10-15, 02:41):
>
> - **(A)** OK a modificare `scripts/cli_base.py` in CP3: le 3 righe più la costante `INSTANCE_TRUST_SECRETS`, con i
>   test in `test_runtime_isolation.py`.
> - **(B)** Le due correzioni stanno in commit separati dal resto di CP3, sopra la base di CP2a: «un segreto vuoto o
>   di soli spazi vale come assente» e «una corsia di test usa segreti suoi».
> - **(C)** Per CP6: nel profilo gestito, un `JWT_SECRET` sotto i 32 caratteri ferma l'avvio; nel self-hosted resta un
>   avviso, che finirà nella scheda «Sicurezza» di A.
> - H-3 confermato nel backlog, da fare con X e B al primo uso di `derive_key`. Le note di progetto per X e B le gira
>   il coordinatore.
>
> **Cambio di semantica rispetto a CP2a**: in CP2a, `configured_jwt_secret()` restituiva un `JWT_SECRET` di soli
> spazi così com'era. Da CP3 un segreto vuoto o di soli spazi vale come assente, quindi a ogni avvio si genera una
> chiave casuale. Il test `config-package` lo dice.

#### CP3 passo 3 — commit separati e verdi ✅ (2026-10-15, notte)

> **Note implementazione**:
>
> - **Le due correzioni in commit separati (decisione B)**: due patch sopra la base di CP2a, in
>   `/tmp/librefolio-r13-h-cp3/split/`, con una copia nella cartella di sessione.
>   - **S1** «un segreto vuoto o di soli spazi vale come assente»: `config/platform.py` e `test_config_package.py`.
>   - **S2** «una corsia di test usa segreti suoi»: la costante `INSTANCE_TRUST_SECRETS = ("JWT_SECRET",)` in
>     `config/__init__.py`, `scripts/cli_base.py` (uguale alla versione finale) e il blocco `TestTestLaneSecrets` di
>     `test_runtime_isolation.py`.
>   - Verifica: `git apply --cached --check` passa sull'indice della base. In un albero esportato con
>     `git archive HEAD`, con le due patch applicate, 647 test passano (`test_config_package.py`,
>     `test_config_misc.py`, `test_runtime_isolation.py`, IMG-010).
>   - Con il `platform.py` della base, il test di S1 dà 2 rossi, come deve. La prova di mutazione di S2 l'ha fatta
>     test-author.
>   - Il commit di CP3 contiene il resto, nelle versioni finali.
> - **Parole neutre**: i commenti, le docstring e la doc dicono «un segreto vuoto o di soli spazi vale come assente»
>   e «una corsia di test usa segreti suoi», senza scenari.
> - **Build**: `front build --debug`, rc 0 e svelte-check 0 errori. Serviva perché `dev.py` è fra le sorgenti dei
>   codec dei Tool. Poi `mkdocs build`, rc 0 (3012 URL relativi risolti), e `check-links`, 95 link validi.
> - **Mirati**, uno alla volta sulla corsia 6181, tutti verdi:
>   - `services`: `config-secrets` 58, `config-instance-key` 98, `config-audit` 65, `config-env-example` 36,
>     `config-package` 468, `config-misc` 4, `donation-popup` 19, `scheduler-loop` 5;
>   - `utils`: `dev-cli-image` 36, `runtime-isolation` 175, `dev-cli-db-path` 15;
>   - `db post-migration`: 37.
> - **`all-backend`**
>   (`PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test -q --fresh-run --workers 2 --log-file /tmp/librefolio-r13-h-cp3/all-backend.log --test-port 6181 --data-dir /tmp/librefolio-r13-h all-backend`):
>   7/7 in 12 min 45 s, **12 089 passed, 3 skipped, 0 failed**.
>   - Sono 273 in più rispetto ai 11 816 della base `60f8a35ce`, cioè esattamente i test nuovi: 58 + 98 + 65 + 36
>     nei quattro file nuovi, 3 in `config-package`, 5 in `dev-cli-image` e 8 in `runtime-isolation`.
> - **Statici**:
>   - ruff e black puliti sui 14 file Python del backend;
>   - in `dev.py` e `scripts/cli_base.py`, che erano già sporchi per black alla base, le righe toccate sono pulite e i
>     reperti di ruff sono gli stessi della base (42 e 0);
>   - `api schema` identico alla base (`1da07e609d1ffad8`, `238c1e4b84afdbdc`);
>   - dead code: un solo reperto nuovo, `derive_key` fra quelli «usati solo dai test». È voluto: è l'API per X e B;
>   - devWiki: `check_source_paths.py` a 5/8, invariato;
>   - `git diff --check` pulito; porta 6181 libera.

### Checkpoint CP3 🧊 (2026-10-15) — FROZEN, in attesa del coordinatore

> Handoff inviato. Il coordinatore ha committato CP3 in quattro commit:
>
> - `8f9e8f018` «un segreto vuoto o di soli spazi vale come assente»;
> - `7640313a4` «una corsia di test usa segreti suoi»;
> - `54fd32def`, il resto di CP3;
> - `32bdb5b95`, il journal.

### Aggiornamento di base con X CP1, CP2a, W I1 e A3 ✅ (2026-10-15, notte)

> **Note implementazione**:
>
> - Il coordinatore ha aperto `git merge --no-ff --no-commit 4696ef699` sopra `32bdb5b95`. Due conflitti, tutti e due
>   additivi:
>   - `backend/app/main.py`, negli import: tenuti `FXProviderRegistry` (X) e `log_configuration_audit` (H). Tolta la
>     mia riga del vecchio `services.market_calendar`: il lato di X lo importa già da `services.assets.market_calendar`;
>   - `test_dev_cli_image.py`: tenuti IMG-010e/f/g (H) e IMG-011/012 di A (`TestAccountRole`), nella docstring e nei
>     test.
> - Fusi da soli e rivisti: `backend.instructions.md`, `settings.md` (la menzione di X su
>   `services/assets/web_link_finder.py`), `_backend_services.py` (89 azioni, nessuna doppia) e il backlog.
> - **Revisione combinata**:
>   - `front build --debug` e `mkdocs build`, rc 0;
>   - mirati tutti verdi: `config-package` 475 (7 casi in più per i moduli spostati da X, con l'eccezione che regge sul
>     percorso nuovo), `dev-cli-image` 44 (8 casi in più, di A);
>   - `api schema` uguale a quello di `4696ef699` (`76085551e2d02d83`, `238c1e4b84afdbdc`);
>   - `all-backend` 7/7 in 12 min 52 s: **12 125 passed, 3 skipped, 0 failed**.
> - **Integrazione**: il merge è `751bf9ab3`, entrato in `dev_release2` con `d08d9358f`. Il coordinatore ha aggiunto i
>   suoi record in `940297265` e ha portato il mio ramo in avanzamento veloce fin lì. Nel CHANGELOG ci sono le quattro
>   righe ✨ e la 🔄.

### Lotto `web_link_finder` — le ultime letture d'ambiente in `config/` ✅ (2026-10-15, notte)

> **Via** del coordinatore (2026-10-15, 03:47): prima la nota del merge, poi questo lotto, poi CP4.
>
> **Note implementazione**:
>
> - **Sezione nuova `config/plugins.py`**, di X secondo D2, scritta da H. Ha sette funzioni con la semantica esatta di
>   prima: `web_link_finder_enabled`, `_engine`, `_api_key`, `_ddgs_region`, `_ddgs_backend`, `_timeout(default)` e
>   `_max_results(default)`.
>   - Unica novità: la chiave API è un segreto e passa da `env_secret()`, quindi vale anche
>     `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE`, come chiede la specifica per tutti i segreti.
> - **`services/assets/web_link_finder.py`**: `is_enabled()` delega alla sua funzione; spariscono `_env_int`,
>   `_env_float` e `import os`.
>   - Un `_FILE` rotto non ferma niente: `_build_engine()` lo scrive come avviso e spegne il motore, così
>     `find_candidate_urls` mantiene la promessa di non sollevare mai.
>   - Il file ora è pulito anche per black.
> - **`.env.example`**: la riga commentata `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE`.
> - **Prova a mano**: 23 casi di semantica uguali a prima, comprese le stranezze (vuoto contro non impostato, `"0"`,
>   `"5.0"`, gli spazi); un `_FILE` rotto dà `None` con l'avviso.
> - **Test** (test-author):
>   - `test_config_package.py`: `ENVIRONMENT_READ_EXCEPTIONS` ora è vuoto. Il meccanismo resta: il cricchetto è un
>     solo test che scorre il dizionario e, quando è vuoto, passa invece di essere saltato. Un test prova il cricchetto
>     su moduli finti. Ci sono 54 casi di semantica per le sette funzioni di `plugins.py`. Totale: 530 (erano 475).
>   - `test_web_link_finder.py`, file di X, solo aggiunte: cinque test. La chiave da `_FILE` costruisce
>     l'`ApiKeyEngine`; un file mancante, vuoto o non UTF-8 spegne il motore con un solo avviso, che non contiene il
>     segreto; `find_candidate_urls` rende `[]` senza sollevare.
>     - Con una copia senza la cattura di `SecretFileError`, i quattro test del file rotto vanno in rosso.
>     - In più c'è una riga che rende ermetico un test esistente, che dipendeva dalla variabile nuova.
>     - Totale: 29 (erano 24).
>   - `test_env_example.py`: solo una docstring. Le otto variabili del motore si trovano soltanto in `config/plugins.py`,
>     tutte documentate.
> - **Doc** (docs-writer):
>   - `settings.md`: la regola vale senza eccezioni; le sezioni sono tre: `platform`, `accounts` e `plugins`;
>   - `configuration.en.md`: i segreti ora sono tre; un `_FILE` rotto della chiave API spegne solo la ricerca web;
>   - `search_link_finder.md`: dove si leggono le variabili;
>   - `security.md`: le corsie di test non ereditano «i segreti che fanno fidare l'istanza di una sessione o le fanno
>     decifrare i dati». La chiave API la ereditano.
>   - `mkdocs build` e `check-links` passano; `translate-validate` dà 3 errori in più per lingua su
>     `configuration.en.md`.
> - **Statici**: ruff e black puliti; `api schema` identico a `940297265`; dead code senza reperti nuovi (le
>   differenze da CP3 sono solo i percorsi spostati da X).
> - **Build e mirati**: `front build --debug` rc 0. Serviva per il `CHANGELOG.md` dei record del coordinatore, che
>   entra nella modale. Poi `services config-package` 530, `config-env-example` 36, `config-secrets` 58, `config-audit`
>   65 e `web-link-finder` 29.
>
> **Fuori pista**: vecchie stranezze del motore, lette nel codice da test-author e lasciate com'erano (sono di X):
>
> - `TIMEOUT` a `nan` o `inf` fa fallire `int(timeout)` in `DdgsEngine.search`, e la ricerca rende `[]`;
> - un valore sotto 1 vuol dire nessun timeout;
> - `MAX=0` rende comunque fino a un URL.
>
> **`all-backend`** (`-q --fresh-run --workers 2`, corsia 6181): 7/7 in 12 min 37 s, **12 185 passed, 3 skipped, 0
> failed**.
>
> - Sono 60 in più rispetto alla revisione combinata di CP3 (12 125): 55 in `config-package` e 5 in `web-link-finder`.
> - Nessun test saltato in più.
> - `git diff --check` pulito; porta 6181 libera.

### Checkpoint del lotto `web_link_finder` 🧊 (2026-10-15) — FROZEN, in attesa del coordinatore

> Handoff inviato. Il coordinatore ha committato il lotto (`fd873f366` e `d495add66`) e ha aggiornato la base a
> `9dda5ccd9`, il merge di `dev_release2` a `0229dbc6a` (X CP2b, W K1), senza conflitti.
>
> - Controllo leggero sulla 6181:
>   - `config-package` 540, cioè 530 più i 12 percorsi nuovi di X, meno i 2 spariti;
>   - `config-env-example` 36, `config-secrets` 58, `web-link-finder` 29;
>   - la raccolta dei test, contro `0229dbc6a` estratto, differisce di +61/−1, solo per i test del lotto;
>   - `api schema` uguale; `mkdocs build` stretto e `check-links` passano.
> - Integrazione: `dev_release2` avanzato in fast-forward a `9dda5ccd9`; poi i record del coordinatore
>   (`11922ee8b`, `d9b853395`).

### CP4 — configurazione pubblica dell'istanza e avvisi (2026-10-15, notte) — in corso

> **Via** del coordinatore (2026-10-15, 04:20): `/system/instance`, gli avvisi d'istanza e i controlli per la scheda
> «Sicurezza» di A. Un lotto che tocca il frontend entra solo prima delle 08:45 o dopo la finestra della galleria.
>
> **Divisione**: CP4a, il backend, che può entrare a qualunque ora; CP4b, il frontend (store, area avvisi, layout,
> i18n, Vitest).

#### CP4a passo 1 — il pacchetto `api/v1/system/` (C2) e `GET /system/instance` (2026-10-15, notte)

> **Note implementazione**:
>
> - **Taglio (C2)**: `api/v1/system.py` diventa il pacchetto `api/v1/system/`, un modulo per risorsa, col codice
>   spostato tale e quale.
>   - I moduli: `info.py`, `diagnostics.py`, `container_image.py`, `connection.py` e `health.py`, cioè `health` e il
>     `test-lane-health` del runner.
>   - L'`__init__.py` compone solo `router` (`/system`, tag `System`) nell'ordine di oggi. `router.py` è intatto.
>   - **Prove**:
>     - `api schema` identico;
>     - la lista effettiva delle rotte (`fastapi.routing.iter_route_contexts`) è identica per ordine, percorso,
>       endpoint, nome, flag dello schema e modello;
>     - l'unica differenza col confronto su `git archive` è il mount statico `/_app`, che `main.py` aggiunge solo
>       quando esiste `frontend/build`.
>   - **Patch dei test sui moduli nuovi**: `info`, `health` e `container_image`. In `test_config_package.py`,
>     `KNOWN_MODULES` cita `api/v1/system/health.py`.
>   - **Percorsi**: 6 righe «Source files» della devWiki (C6) e la tabella di `backend.instructions.md`. La prosa
>     (`F-102.md:24`, `docker-system-info-missing-deps.md:24`) va in H-1. `check_source_paths` resta a 5/8.
> - **`GET /system/instance`**, pubblico, in `api/v1/system/instance.py` e registrato per ultimo. Risponde con
>   `InstanceConfigResponse` (`schemas/system.py`): per ora un solo campo, `profile`.
>   - **Meccanismo per le altre sessioni**: chi possiede una parte della configurazione pubblica aggiunge un campo,
>     tipato con un modello dei suoi schemi, e lo riempie in `get_instance_config()` con una chiamata al suo servizio.
>     Tutto è pubblico e uguale per chiunque chieda. A ci metterà `registration_mode`, `setup_required` e i link.
>   - **`LIBREFOLIO_PROFILE`**: campo di `Settings`, `selfhosted` di default oppure `managed`, indifferente a maiuscole
>     e spazi. Un valore diverso ferma l'avvio.
>     - Oggi decide solo cosa riporta `/system/instance`. I default del profilo gestito arrivano con CP6 e CP7b.
>     - In `.env.example` c'è la sezione «Instance Profile», con la riga commentata.
>
> **Fuori pista**: con FastAPI 0.141 i router inclusi restano involucri (`_IncludedRouter`), quindi
> `router.routes` non contiene più le `APIRoute`. Il test `_route_dependency_calls` di `test_system_api.py` va
> riparato con `iter_route_contexts` (test-author).
>
> **Correzione per l'audit i18n**: `config_audit.py` ora scrive le 13 chiavi `instance.checks.*` per intero, non più
> come `f"{_I18N_PREFIX}…"`. Così l'audit le vede usate: una f-string conta solo se la testa puntata è letterale. I
> valori non cambiano.

#### CP4b passo 1 — il frontend: store, avvisi, layout, i18n (2026-10-15, notte)

> **Note implementazione**:
>
> - **CP4 resta un solo checkpoint**, a commit separati: rinomina, taglio, backend, frontend, journal. Così non ci
>   sono incroci su `settings.md`, che toccano tutti e due.
> - **`features/instance/instanceConfig.svelte.ts`**, store con le rune, di `GET /system/instance`:
>   - `load()` fa una richiesta per caricamento di pagina, condivisa da chi chiama insieme o dopo; `force` richiede di
>     nuovo;
>   - un errore lascia `DEFAULT_INSTANCE_CONFIG` (self-hosted) e consente di riprovare; scrive solo la richiesta più
>     recente;
>   - il tipo viene dal client generato (`z.infer<typeof schemas.InstanceConfigResponse>`).
> - **`features/instance/instanceNotices.svelte.ts`**, registro degli avvisi:
>   - `show` aggiunge, oppure sostituisce sul posto un avviso con lo stesso id; `hide` toglie, e un avviso nascosto
>     torna visibile se rimostrato; `dismiss` chiude un avviso chiudibile fino al prossimo caricamento;
>   - `list` mette prima `danger`, poi `warning`, poi `info`, e dentro ogni gravità l'ordine di arrivo;
>   - all'uscita il registro si svuota (`registerClientSessionReset`).
> - **`features/instance/components/InstanceNotices.svelte`**: sui soli ruoli di colore, con una stringa letterale
>   intera per gravità (`bg-lf-X-soft border-lf-X-line text-lf-X-on-soft`, icona `text-lf-X`), senza `dark:`. Il
>   bordo nomina sempre il suo ruolo. Senza avvisi non rende niente.
> - **`routes/(app)/+layout.svelte`**: tre aggiunte, senza riordinare niente: due import, `void instanceConfig.load()`
>   in cima a `onMount` e `<InstanceNotices />` in `<main>`, dopo il banner dell'onboarding.
> - **i18n**: sottosistema nuovo `lib/i18n/instance/` (prefisso `instance`), scritto con `dev.py i18n add`. Contiene
>   `instance.notices.label` e i 13 messaggi `instance.checks.*` per la scheda «Sicurezza» di A, nelle 4 lingue. Per
>   il pulsante di chiusura si usa il `common.close` che c'era già.
> - **Verifiche**:
>   - `api sync` ok;
>   - prettier sui file nuovi;
>   - `front check`: svelte-check 0 errori e 0 avvisi;
>   - porta dei colori pulita (`theme-roles.mjs --check`);
>   - `i18n check` stretto: 4385 chiavi, 18 sottosistemi;
>   - `i18n audit`: 0 chiavi inutilizzate; le 4 «not verified» erano già alla base.

#### CP4 passo 2 — test, doc e commit separati della divisione (2026-10-15, notte)

> **Note implementazione**:
>
> - **Test di CP4a** (test-author):
>   - riparato `_route_dependency_calls`: ora percorre il `dependant` effettivo del contesto
>     (`iter_route_contexts`), che vede anche una dipendenza aggiunta all'`include_router`. Una prova di mutazione lo
>     dimostra;
>   - aggiunto il perno d'ordine C2, sulle prime sei rotte di `system.py`, nel loro ordine;
>   - test di `/system/instance`: nessuna sessione nel cammino, risposta esatta dal vivo e in processo;
>   - `test_config_misc.py`: la validazione di `LIBREFOLIO_PROFILE`. Un valore vuoto ferma l'avvio, come
>     `SESSION_COOKIE_SECURE`;
>   - risultati: `api system` 94 (+8), `config-misc` 12 (+8), `config-package` 546, `config-env-example` 36 (vede
>     `LIBREFOLIO_PROFILE`), `utils container-registry` 30;
>   - aggiornata la descrizione di `config-misc` nel catalogo del runner.
> - **Doc** (docs-writer):
>   - CP4a: `configuration.en.md` (riga `LIBREFOLIO_PROFILE`), `security.md` (endpoint pubblici), `settings.md`
>     (sezione «Public instance configuration» con la regola per i proprietari), `api/index.md`;
>   - CP4b: `frontend/state/app-state.md` (store e registro degli avvisi, col contratto `data-testid` e i ruoli),
>     `state/index.md`, `frontend/i18n.md` (18 sottosistemi), `settings.md` (l'app la legge all'avvio), `security.md`
>     (le chiavi dei controlli ora sono nel catalogo);
>   - `mkdocs build` e `check-links` passano. Debito di traduzione solo su `configuration.en.md`: 15 errori e 69
>     avvisi per lingua.
> - **Commit separati della divisione (C2)**, patch in `/tmp/librefolio-r13-h-cp4/split/`:
>   - **R**: la rinomina pura `system.py` → `system/__init__.py`;
>   - **C**: il taglio, in 16 file. Sono `__init__` e i 5 moduli; le patch dei test, cioè il perno e la riparazione
>     del cammino, senza la parte di `/system/instance`; le 6 righe della devWiki e la riga delle istruzioni.
>   - Verifica su `git archive HEAD` con R e C applicate:
>     - lista effettiva delle rotte identica;
>     - `api schema` identico (`76085551e2d02d83`, `238c1e4b84afdbdc`);
>     - 653 test senza server passano (`test_config_package.py`, `test_container_registry.py` e
>       `test_system_api.py`). I 9 test dal vivo girano sull'albero finale con `api system`.
> - **knip**: nessun reperto per `features/instance`.
> - **Test di CP4b** (test-author): `instanceConfig.test.ts`, `instanceNotices.test.ts` e
>   `components/InstanceNotices.test.ts`, 35 test.
>   - I due test del layout ora fanno il mock dei moduli nuovi. Verificano anche che `load()` venga chiamato una volta
>     al mount, senza aspettare la risposta e qualunque sia l'esito dell'autenticazione.
>   - Tre righe nel catalogo `_frontend_utility.py`, solo aggiunte.
>   - Risultati: `front-utility core-unit` 134 file / 4290 test, `component-unit` 120 / 3209,
>     `onboarding-component-unit` 15 / 441.
>
> **Fuori pista**: test-author ha trovato due difetti nel mio codice, corretti con un test ciascuno.
>
> - `load()` con un `fetchConfig` che solleva subito non riprovava più. Ora la richiesta parte sempre subito, un
>   errore sincrono diventa una promessa rifiutata, e un fallimento libera `pending` solo se è ancora suo.
> - Una chiusura nascondeva anche un avviso rimostrato come non chiudibile. Ora `list` nasconde un avviso solo
>   finché è chiudibile.

#### CP4 passo 3 — i verdi ✅ (2026-10-15, notte)

> **Note implementazione**:
>
> - **Build**: `front build --debug` rc 0, svelte-check 0 errori e 0 avvisi. `mkdocs build` rc 0, con 3012 URL
>   relativi; `check-links` 95 validi.
> - **Mirati**, uno alla volta sulla corsia 6181, tutti verdi:
>   - `api system` 94, `utils container-registry` 30;
>   - `services config-package` 546, `config-env-example` 36, `config-misc` 12, `config-audit` 65;
>   - `utils gate-i18n-catalog` 176, `gate-i18n-usage` 195.
> - **`api schema`**: rispetto alla base, solo il percorso `/api/v1/system/instance` e lo schema
>   `InstanceConfigResponse` in più. Niente di cambiato o tolto; i contratti dei Tool sono identici. Hash openapi
>   `bf955f7849342437`.
> - **`all-backend`** (`-q --fresh-run --workers 2`, corsia 6181): 7/7 in 12 min 10 s, **12 217 passed, 3 skipped, 0
>   failed**.
>   - Sono 32 in più rispetto al lotto `web_link_finder` (12 185): 10 della guardia sui moduli di X CP2b, entrati con
>     l'aggiornamento di base, e 22 di CP4 (`api system` +8, `config-misc` +8, `config-package` +6).
> - **Statici**:
>   - ruff e black puliti sui 16 file Python; prettier pulito sui file del frontend;
>   - porta dei colori pulita; `i18n check` stretto; knip senza reperti nuovi;
>   - `git diff --check` pulito; porta 6181 libera.
> - **Backlog**: H-1 registra le due menzioni in prosa di `system.py` nella devWiki.

### Checkpoint CP4 🧊 (2026-10-15) — FROZEN, in attesa del coordinatore

> Handoff inviato. Il coordinatore ha committato CP4 in 5 commit: R `c43ea0460` (`R100`), C `27a29af09`, CP4a
> `42af16d54`, CP4b `2069c75cd`, journal `bf085ddb8`. Le patch sono identiche alle copie di sessione. Il suo controllo
> sull'AST del taglio: 16 definizioni su 16 identiche, più i sotto-router.
>
> **Correzione**: nel messaggio di handoff le code delle due impronte erano scambiate. Quelle giuste sono R
> `1107ea92…dfc52a776` e C `aed0e05e…6e2ad22f`.

### Aggiornamento di base con J CP-1, W4 e A4 ✅ (2026-10-15, notte)

> `2f5ce4c36`, merge del coordinatore di `dev_release2` a `be2ad6573`: J CP-1, W4 (BRIM in `services/brim/`), A4 (la
> migrazione 005). Unione automatica, albero uguale alla simulazione.
>
> **Validazione completa** sulla 6181, perché CP4 cambia il layout di ogni pagina:
>
> - galleria: senza avvisi `InstanceNotices` non disegna nessun nodo. L'`{#if}` avvolge l'unica `<section>`, il test
>   del componente lo verifica (`container.querySelector('*')` nullo) e `<main>` non ha `space-y`. Nessun codice di
>   produzione mostra un avviso;
> - `front build --debug` rc 0, svelte-check pulito; `i18n check` stretto (4385 chiavi, 18 sottosistemi);
>   `theme-roles.mjs --check` pulito; `mkdocs build` senza avvisi;
> - Vitest: `core-unit` 4290, `component-unit` 3209, `onboarding-component-unit` 441;
> - E2E, 181 passati:
>   - `front-utility auth` 29, `app-start-auth` 3, `settings` 45, `onboarding-guides` 24;
>   - gli spec che contano le richieste: `front-asset asset-detail` 33, `front-broker broker-recovery` 5,
>     `front-portfolio risk` 38, `front-utility files-pdf-offline` 1, `front-transaction tx-bulk-import-handoff` 3;
> - `api schema` contro `be2ad6573`: solo `+/api/v1/system/instance` e `+InstanceConfigResponse`; Tool contracts
>   identici;
> - `all-backend`: 7/7 in 13 min 49 s, **12 343 passed, 3 skipped, 0 failed**, cioè 126 in più, da J, W4 e A4.

### Aggiornamento di base con X CP3, W7, X CP3b e J C-93 ✅ (2026-10-15, alba)

> `1b3eb54c7`, merge del coordinatore di `dev_release2` a `a628147a0`, senza conflitti. Controllo leggero sulla 6181:
>
> - `services config-package` 584, cioè 498 moduli più 86 casi fissi:
>   - il merge toglie 3 moduli (`api/v1/fx.py`, `schemas/transactions.py`, `services/fx/fx.py`) e ne aggiunge 13
>     (`api/v1/fx/` 3, `schemas/transactions/` 6, `services/fx/` 4);
>   - nessuno dei 13 legge l'ambiente;
> - `api system` 94;
> - raccolta dei test contro `a628147a0` estratto: +23/−1, tutti di CP4;
> - `api schema`: solo le aggiunte di CP4;
> - `front build --debug` e `mkdocs build` puliti; `core-unit` 4290.

### Integrazione di CP4 ✅ (2026-10-15, alba)

> `dev_release2` avanzato in fast-forward a `1b3eb54c7`. Sopra c'è il record del coordinatore `6d67fdaac`, con la riga
> di `/system/instance` nel CHANGELOG.

### CP5 — prontezza e versione (F08) (2026-10-15, alba) — in corso

> **Via** del coordinatore (2026-10-15, 06:08): prontezza, `/system/info` minimo senza login (D14 modificata), R2,
> C-84.
>
> - Un lotto che tocca il frontend entra solo dopo la finestra della galleria.
> - Dalle ~08:45 solo lavoro leggero.
> - `/system/instance` resta pubblico: il coordinatore ricorda ad A che i suoi campi devono restare innocui per un
>   anonimo.
>
> **Disegno**: §3.5, riscritto all'avvio. CP5a, il backend; CP5b, il frontend.

#### CP5a passo 1 — il codice ✅ (2026-10-15, alba)

> **Note implementazione**:
>
> - **`GET /system/ready`**:
>   - servizio `services/platform/readiness.py`: `check_readiness(session)`. `SELECT 1` dice se il DB risponde.
>     `alembic_version` deve avere una riga sola, uguale alla head;
>   - la head la legge `_read_alembic_head()`, in cache per processo. `alembic_head_revision()` rende None su un
>     errore, che non resta in cache;
>   - i dettagli vanno nel log una volta per cambio di stato;
>   - rotta `api/v1/system/ready.py`, registrata per ultima nel pacchetto: 200, oppure 503 con lo stesso corpo;
>   - schemi `ReadinessChecks` e `ReadinessResponse`.
> - **`GET /system/info`**:
>   - la dipendenza `signed_in_user` chiama `get_current_user` e trasforma il suo 401 in None; ogni altro errore
>     passa;
>   - l'endpoint ora è un `def` e risponde `SystemInfoPublicResponse` (solo `app_version`) o `SystemInfoResponse`;
>   - `response_model` è l'unione, con lo schema completo per primo. L'ordine conta: il client generato prova lo
>     `z.union` in ordine, e i suoi oggetti degli schemi `StrictModel` tolgono le chiavi sconosciute. Con lo schema
>     pubblico per primo, una risposta completa arriverebbe ad `AboutTab` con la sola versione. Lo fissa
>     `test_openapi_documents_the_full_answer_first`.
> - **R2**: `version.py` ha `_git_describe()` e `_version_file()`; `get_git_version()` guarda `.git` con
>   `os.path.lexists`.
> - **C-84**: `pyproject.toml` a `0.0.0`, con un commento.
> - **`dev.py`**: solo il commento sopra la scrittura di `VERSION`, che diceva il contrario di R2.
> - **Istruzioni**: `readiness` nella mappa di `backend.instructions.md`.
> - **Prova in processo** (TestClient su un DB temporaneo, poi cancellato):
>   - `/ready` 200 `ok`/`ok`;
>   - `/info` senza sessione e con un cookie falso: solo `app_version`;
>   - la versione viene da `git describe`.
> - **`api schema`** contro `6d67fdaac`:
>   - `+/api/v1/system/ready`;
>   - `/api/v1/system/info` cambiato: risposta `anyOf` e descrizione;
>   - `+ReadinessChecks`, `+ReadinessResponse`, `+SystemInfoPublicResponse`;
>   - `SystemInfoResponse` cambia solo nella descrizione;
>   - Tool contracts identici; hash openapi `cad4535d814b6741`, misurato dopo che la nota sul `def` è passata dalla
>     docstring a un commento.
> - Ruff e black puliti sui file toccati. Gli errori di ruff in `dev.py` c'erano già: lì cambia solo un commento.
>
> **Fuori pista**: la factory di sessione rende l'`AsyncSession` di SQLAlchemy, non quella di SQLModel. Quindi
> `execute` con dei `select` Core: `literal(1)` e una `table("alembic_version")` leggera.
>
> **Fuori pista** (trovato da docs-writer): nel job di rilascio il checkout ha `.git`. Con R2 da solo, i server della
> galleria avrebbero letto `git describe` invece del `VERSION` congelato: gli scatti di Informazioni potevano dire
> `-dirty` se un passo precedente scrive un file tracciato.
>
> - Cura: `get_git_version()` legge per prima `LF_APP_VERSION`, la stessa variabile di `frontend/vite.config.ts`, che
>   la CI esporta da `VERSION` subito dopo averlo scritto.
> - La lettura sta in `config/platform.py` (`frozen_app_version()`, vuota = assente). Si importa dentro la funzione,
>   perché `backend.app.config` importa `version.py`.
> - `.env.example` ha una sezione «App Version» con `# LF_APP_VERSION=` commentata: «lasciala vuota».
> - Senza la variabile, cioè per ogni installazione, l'ordine è quello di R2.
>
> **Per gli altri e per i miei CP**:
>
> - Z (F26): `/system/ready`, `/system/health` e `/system/info` senza sessione non sono attività dell'utente;
> - CP6: nell'elenco corto dei permessi del blocco ci vanno `/system/ready`, `/system/health`, `/system/info` e
>   `/system/instance`;
> - CP7a: proporre `/system/ready` per l'healthcheck del `Dockerfile` e dei compose.

#### CP5a passo 2 — test e doc ✅ (2026-10-15, alba)

> **Note implementazione**:
>
> - **Test** (test-author), sulla corsia 6181, uno alla volta:
>   - `test_version.py` riscritto, da 13 a 51 test:
>     - `LF_APP_VERSION` vince; vuota o di soli spazi non conta;
>     - `.git` cartella, file o link; `git describe` vince su un `VERSION` diverso;
>     - sette modi in cui git fallisce, che ripiegano su `VERSION`;
>     - senza `.git` git non parte. Una prova vera lo verifica: con un repository padre con tag, la risposta è
>       `unknown`;
>     - `VERSION` vuoto o cartella non conta;
>   - nuovo `test_platform_readiness.py`, 13 test, registrato come `services platform-readiness`:
>     - SQLite vero sotto `tmp_path`; pronto, `mismatch`, `unknown` (senza tabella, vuota, due righe),
>       `unreachable`;
>     - la head si legge una volta e un errore non resta;
>     - nessun dettaglio nella risposta; il log una volta per cambio di stato;
>   - `test_system_api.py`, 116 test:
>     - `/system/info` dal vivo senza cookie, con un cookie falso e con una sessione vera;
>     - `signed_in_user`: i quattro 401 danno None, ogni altro errore passa;
>     - l'`anyOf` con lo schema completo per primo;
>     - `/system/ready` pubblico, dal vivo e in processo (200 e 503); l'ordine delle rotte;
>   - `test_config_package.py`: 4 casi per `frozen_app_version()`;
>   - verdi: `utils version` 51, `services platform-readiness` 13, `api system` 116, `services config-package` 590,
>     `services config-env-example` 36; `check-orphans` pulito.
> - **Doc** (docs-writer):
>   - `security.md` (sezione «System Information and Readiness», tabella degli endpoint pubblici);
>   - `api/index.md`, `api/curl-testing.md`;
>   - `release-pipeline.md` (l'ordine delle sorgenti della versione, con `LF_APP_VERSION`);
>   - `brim_plugin_guide.md` (una frase sulla versione);
>   - `admin/docker_advanced.en.md` e `admin/service_exposure.en.md` (un riquadro su `/api/v1/system/ready`);
>   - `mkdocs build` stretto e `check-links` (95) passano.
>   - Debito di traduzione: solo i due riquadri delle pagine admin, 33 errori e 102 avvisi in IT, FR ed ES. Non
>     timbrato, perché è contenuto nuovo.
> - **Ritocchi miei dopo i rapporti**:
>   - la docstring del modulo `version.py`;
>   - la descrizione di `utils version` nel catalogo;
>   - la nota in `signed_in_user`: un override di `get_current_user` non arriva a questa rotta;
>   - il commento del passo «Freeze the app version for the frontend builds» in `release.yml`: anche il backend
>     legge `LF_APP_VERSION`. Il nome del passo non cambia.
>
> **Fuori pista**: test-author ha dovuto copiare `backend/app/config/` nell'albero minimo del test sul layout
> dell'immagine. L'import pigro della configurazione lo richiede; l'immagine vera copia tutto `backend/`.

#### CP5a passo 3 — i verdi ✅ (2026-10-15, alba)

> **Note implementazione**:
>
> - **Build**:
>   - `front build --debug` rc 0, svelte-check 0 errori e 0 avvisi. Il client generato ha
>     `z.union([SystemInfoResponse, SystemInfoPublicResponse])`;
>   - `mkdocs build` rc 0, nessun avviso, 3012 URL relativi; `check-links` 95 validi.
> - **`all-backend`** (`-q --fresh-run --workers 2`, corsia 6181): 7/7 in 12 min 11 s, **12 436 passed, 3 skipped,
>   0 failed**.
>   - Sono 93 in più rispetto a `2f5ce4c36` (12 343). 79 vengono da CP5a: `utils version` +38,
>     `services platform-readiness` +13, `api system` +22, `services config-package` +6. Altri 14 vengono
>     dall'aggiornamento di base `1b3eb54c7`.
> - **`api schema`** contro `6d67fdaac`:
>   - `+/api/v1/system/ready`; `/api/v1/system/info` cambiato (risposta `anyOf` e descrizione);
>   - `+ReadinessChecks`, `+ReadinessResponse`, `+SystemInfoPublicResponse`; `SystemInfoResponse` cambia solo nella
>     descrizione;
>   - Tool contracts identici. Hash openapi `cad4535d814b6741`.
> - **Statici**: ruff e black puliti sui file toccati; il YAML di `release.yml` si legge; `git diff --check` pulito;
>   porta 6181 libera.
> - **Vitest**, perché cambia il client generato: `core-unit` 4290, `component-unit` 3209, invariati.
> - **Backlog**: H-5, il debito di traduzione delle pagine admin.

### Checkpoint CP5a 🧊 (2026-10-15) — FROZEN, in attesa del coordinatore

> Handoff inviato. Il coordinatore ha committato CP5a in tre commit: `e8ceda504` (`feat(system)`, 15 file),
> `6e78b8c96` (`fix(version)`, 11 file) e `2d6d0488d` (journal, 2 file). Poi ha aggiornato la base: `cf6f08856`, merge
> pulito di `dev_release2` a `ee5d81a6f` (G-8, X CP4, W K2a, A4b e i suoi record).
>
> **Nota**: il blocco «Per gli altri e per i miei CP» del passo 1 era finito qui, sotto questo titolo. L'ho riportato
> nel passo 1.

### Correzione prima dell'ingresso: la head fuori dal ciclo di eventi ✅ (2026-10-15, alba)

> **Richiesta** del coordinatore: in `readiness.py`, `_run_checks` chiamava `alembic_head_revision()` dentro la rotta
> `async`. Il primo calcolo legge `alembic.ini` e importa le migrazioni in modo sincrono, e se fallisce lo rifà a ogni
> sonda.
>
> **Note implementazione**:
>
> - `head = await asyncio.to_thread(alembic_head_revision)`. Il nome si risolve alla chiamata, quindi le sostituzioni
>   dei test valgono ancora. La docstring del modulo dice perché.
> - Test (test-author), `test_the_head_is_read_off_the_event_loop`:
>   - un registratore prende il posto di `alembic_head_revision`, nota il thread e verifica che lì non giri un ciclo;
>   - prima, il test controlla che la stessa sonda veda il ciclo dal test stesso;
>   - `services platform-readiness` 14.
> - A4b (`get_current_user`) aggiunge solo un 401, per una versione di sessione superata. Per `signed_in_user` vale
>   come gli altri: una sessione revocata riceve la sola versione.
> - **Controllo leggero della revisione combinata** (corsia 6181, una invocazione alla volta):
>   - `front build --debug` rc 0, svelte-check 0/0; `mkdocs build` stretto senza avvisi; `check-links` 95;
>   - `services platform-readiness` 14, `api system` 116, `api auth` 60, `api session-revocation` 3,
>     `utils version` 51, `services config-env-example` 36;
>   - `services config-package` 592: i 2 casi in più sono i moduli nuovi di X CP4 (`schemas/assets/metadata.py`,
>     `schemas/assets/scheduled_investment.py`), che non leggono l'ambiente;
>   - `check-orphans` pulito;
>   - `api schema` contro `ee5d81a6f`: solo le aggiunte di CP5a; Tool contracts identici;
>   - porta 6181 libera; `git diff --check` pulito.

### Checkpoint della correzione 🧊 (2026-10-15) — FROZEN, in attesa del coordinatore

> Committata dal coordinatore: `d80c0a091` (la correzione) e `5d1242ae5` (journal). CP5a è entrato in `dev_release2`
> con il merge `9deb0ea08`, senza un nuovo controllo: nel frattempo era entrato solo X J-5, che non tocca file miei.
> Il record del coordinatore è `6cd64b71b`: le tre righe del CHANGELOG, R2 chiusa (anche nel piano d'origine 09),
> C-84 chiusa per metà, F08 in giallo nel README. Il mio ramo è avanzato a `6cd64b71b`.

### CP6 — il blocco dell'istanza (D4) (2026-10-15, mattina) — in corso

> **Via** del coordinatore (2026-10-15, 07:19): durante la finestra della galleria si scrive CP6, senza esecuzioni
> pesanti; CP5b dopo l'avviso di fine finestra. CP6 ha una parte frontend, quindi entra dopo la finestra e dopo CP5b.
>
> **Risposte del coordinatore al disegno** (07:40):
>
> - sì a `api/v1/router.py` (solo la riga della dipendenza, separata dagli include, dove poi Z aggiungerà il suo) e al
>   ramo 423 in `lib/api/zodios-client.ts`;
> - (c): la pagina di blocco non offre la cancellazione dell'account, né come segnaposto. Dopo A5 il coordinatore
>   registra ad A l'estrazione del dialogo da `ProfileTab.svelte`, e la pagina lo riuserà allora;
> - il reset della password resta fuori dai permessi; i ganci di B e Z vanno bene;
> - il resto del disegno va bene; alla fine di CP6 c'è la revisione di sicurezza.
>
> **Disegno**: §3.6, riscritto.

#### CP6 passo 1 — il backend ✅ (2026-10-15, mattina)

> **Note implementazione**:
>
> - `config/platform.py`: `instance_blocked()` e `instance_deletion_date()`, lette dall'ambiente; un valore illeggibile
>   solleva `ValueError`.
> - `config_audit.py`:
>   - `log_configuration_audit()` legge le due variabili all'avvio, quindi un valore sbagliato ferma il server;
>   - con il blocco attivo scrive un avviso nel log, con la data;
>   - nel profilo gestito un `JWT_SECRET` corto solleva `WeakSecretError`; `check_jwt_secret()` lo segnala come `error`.
> - `api/v1/instance_block.py`: `ALLOWED_WHEN_BLOCKED`, 10 funzioni, e la dipendenza `refuse_when_blocked`.
> - `api/v1/router.py`: `APIRouter(dependencies=[Depends(refuse_when_blocked)])`, con un commento.
> - `api/v1/system/block.py` (`GET /system/block`, con sessione), registrato per ultimo; schema
>   `InstanceBlockResponse`.
> - `.env.example`: la sezione «Instance Block (hosting providers)», con le due righe commentate.
> - **Prova in processo** (TestClient, DB temporaneo poi cancellato):
>   - senza blocco, `GET /brokers` anonimo dà 401;
>   - col blocco, da anonimo: `GET /brokers` 401 «Not authenticated» e `POST /auth/register` 401;
>   - col blocco, con sessione: `GET /brokers` 423 `instance_blocked`; `/system/block` 200
>     `{blocked: true, deletion_date: 2026-11-14}`; `/auth/me` 200; `/system/info` completo;
>   - sonde, `/system/instance` e il login rispondono come sempre;
>   - `ture` e una data non ISO fermano i controlli d'avvio; `managed` con un segreto di 12 caratteri si ferma.
> - Ruff e black puliti.
>
> **Fuori pista**:
>
> - La prima stesura rifiutava con 423 anche gli anonimi, perché la dipendenza del router gira prima dell'autenticazione
>   della rotta. Così chiunque avrebbe visto da fuori che l'istanza è bloccata. Ora la guardia chiama
>   `get_current_user` prima del 423.
> - Le variabili non sono campi di `Settings`: `get_settings()` costruisce un'istanza nuova, e legge `.env`, a ogni
>   chiamata. Una guardia su ogni richiesta legge invece l'ambiente, che costa una ricerca in un dizionario.
> - In CP4 `zodios-client.ts` non era stato toccato: l'aggancio del §5 non era servito. Il ramo 423 è il primo.

#### CP6 passo 2 — il frontend ✅ (2026-10-15, mattina)

> **Note implementazione**:
>
> - `features/instance/instanceBlock.svelte.ts`:
>   - un flag con `markBlocked()` e `clear()`, e `isInstanceBlockedError(status, data)`: vero solo per un 423 con
>     `detail.code` `instance_blocked`;
>   - nessun import dell'API, quindi l'interceptor lo importa senza ciclo;
>   - un cambio d'account lo spegne (`registerClientSessionReset`).
> - `lib/api/zodios-client.ts`: un ramo nell'interceptor degli errori accende il flag.
> - `features/instance/components/InstanceBlockedPage.svelte`:
>   - pagina a tutta pagina, con soli ruoli di colore;
>   - testo per l'admin o per gli altri utenti, secondo `is_superuser`;
>   - la data di cancellazione nel locale dell'interfaccia, letta e formattata in UTC, così nessun fuso la sposta;
>   - «Esci», con la chiave `auth.logout`;
>   - se `GET /system/block` dice che il blocco è tolto, spegne il flag e ricarica la pagina; se fallisce, la pagina
>     resta senza data.
> - `routes/(app)/+layout.svelte`: il ramo `$isAuthenticated && instanceBlock.blocked` sta prima di quelli del
>   bootstrap.
> - i18n: 4 chiavi `instance.block.*` nelle 4 lingue; `i18n check` stretto, 4396 chiavi.
> - `api sync`, prettier senza modifiche; `front check` con svelte-check 0/0; porta dei colori pulita;
>   `front build --debug` alle 07:36, così le corse di test-author sul server non ricostruiscono il frontend.
> - **Test e doc** affidati a test-author e docs-writer, con la consegna di finire le esecuzioni pesanti entro le 08:40.

#### CP6 passo 3 — revisione di sicurezza ✅ (2026-10-15, mattina)

> **Note implementazione** (`security-review` sul codice di CP6, prima dei test):
>
> - Copertura:
>   - le 133 rotte di `/api/v1` (130 `APIRoute`, 3 `ToolRoute`) hanno `refuse_when_blocked` come prima dipendenza,
>     compresi i router annidati, lo stream SSE e il servizio dei file caricati;
>   - le 10 voci dell'elenco corrispondono esattamente a 10 rotte, e nessuna funzione è registrata due volte;
>   - il 423 arriva prima della validazione e prima delle dipendenze della rotta;
>   - `get_current_user` non scrive niente.
> - Valori non validi delle variabili fermano l'avvio; `WeakSecretError` dice l'origine e la lunghezza, mai il segreto.
>   Nella pagina di blocco non c'è XSS.
> - **Osservazione bassa**: le rotte pubbliche fuori dall'elenco rispondono 401 solo col blocco. Chi non ha sessione può
>   quindi capire che l'istanza è bloccata (nessun dato).
>   - Garanzia ristretta nella docstring di `instance_block.py`, nel §3.6 e nella doc.
>   - **Decisione del coordinatore (08:04): (a), lasciare così.** La decisione 12 non promette che da fuori il blocco non
>     si veda, e il segnale non porta dati. Permettere le GET pubbliche non lo chiuderebbe, perché la registrazione resta.
>     Se il developer le vuole, è un cambio dell'elenco più avanti.
> - FastAPI non dà le dipendenze del router a `Route`, `WebSocketRoute` e `Mount`. Il test della guardia fallisce se ne
>   compare una sotto `/api/v1`.
> - Il revisore ha trovato anche un caso già coperto da un commit del coordinatore in attesa.

#### CP6 passo 4 — test e doc ✅ (2026-10-15, mattina)

> **Note implementazione**:
>
> - **Test** (test-author). Il blocco si attiva solo in processo, con `monkeypatch`: il server della corsia non viene
>   mai bloccato.
>   - `test_config_package.py` +37 (valori accettati, rifiutati e vuoti delle due variabili);
>   - `test_config_audit.py` +25 (gravità per profilo, `WeakSecretError` senza il segreto, arresto sui valori non
>     validi, avviso col blocco);
>   - nuovo `test_instance_block.py`, 44 test, registrato come `api instance-block`:
>     - da anonimo, «stessa risposta col blocco e senza» vale per le rotte protette; un test documenta come sono le
>       rotte pubbliche;
>     - la guardia sulle rotte: fallisce per ogni rotta o mount sotto `/api/v1` che non sia un `APIRoute` con
>       `refuse_when_blocked` per prima. Un'app di prova dimostra che la verifica coglie route semplici, WebSocket,
>       mount e guardie mancanti o al secondo posto;
>     - eccezioni fissate: le tre rotte della documentazione di FastAPI (`/api/v1/openapi.json`, `/docs`, `/redoc`),
>       che portano lo schema e nessun dato;
>   - `test_system_api.py` +1: `/system/block` registrata per ultima;
>   - Vitest: `instanceBlock.test.ts` 21, `zodios-client.test.ts` 6, `InstanceBlockedPage.test.ts` 14. La data esce
>     il 14 nei fusi di Los Angeles, Kiritimati e UTC. `layout.gate.test.ts` +6: la pagina vince su ogni stato del
>     bootstrap;
>   - verdi: `services config-package` 631, `services config-audit` 90, `api instance-block` 44, `api system` 117;
>     `check-orphans` pulito.
> - **Miei**, sulla corsia, prima delle 08:45:
>   - `services config-env-example` 36;
>   - `front check` 0/0; porta dei colori pulita; `i18n check` stretto, 4396 chiavi;
>   - Vitest dal runner: `core-unit` 136 file e 4317 test (+27), `component-unit` 121 e 3223 (+14),
>     `onboarding-component-unit` 15 e 447 (+6).
> - **Doc** (docs-writer):
>   - nuova `admin/hosting_providers.en.md`, nella navigazione di `mkdocs.yml` sotto «Deployment & Exposure»;
>   - `admin/configuration.en.md` (righe delle due variabili, regola del `JWT_SECRET` nel profilo gestito, controlli
>     d'avvio) e `admin/index.en.md`;
>   - `security.md` (sezione «Instance Block», con la garanzia ristretta), `api/index.md`, `app-state.md`;
>   - `mkdocs build` e `check-links` (95) passano. Debito di traduzione non timbrato: `hosting_providers` (solo
>     inglese), `configuration`, `admin/index`.
>
> **Fuori pista**:
>
> - In `.env.example` una riga di prosa cominciava con `# LIBREFOLIO_BLOCKED=true`, e la guardia la leggeva come riga
>   di variabile. Ho rifatto gli a capo.
> - La docstring di `instance_block.py` ora nomina le tre rotte di documentazione di FastAPI come uniche eccezioni.
> - Il database della corsia era vuoto, perché un selettore `api` da solo non lo popola. test-author ha adattato il test
>   e ha tolto l'admin creato dalla prima corsa: la corsia è tornata a 0 utenti.

### CP5b — la metà frontend di C-84 e `AboutTab` (2026-10-15, mattina) — scritto, da validare dopo la finestra

> **Note implementazione**:
>
> - `frontend/package.json` e le due righe radice di `package-lock.json` a `0.0.0`. JSON non ha commenti: la
>   spiegazione sta nel commento di `pyproject.toml` e in `release-pipeline.md`.
> - `AboutTab.svelte`: la risposta di sola versione (senza sessione) non viene presa per il resoconto completo:
>   `systemInfo` resta `null`. Prima la tab l'avrebbe letta come completa, e `backend_dependencies.length` avrebbe
>   sollevato un errore.
> - Il test nuovo in `AboutTab.test.ts` lo ha scritto test-author: «leaves the diagnostics grid out for a version-only
>   answer, and still lists the providers». Il file passa 38 su 38.
>   - Con la risposta di sola versione, l'intestazione mostra `...`: la risposta arriva solo a una sessione scaduta,
>     che va comunque al login.
>   - **Fuori pista**: due controlli d'assenza già presenti nello stesso file non possono fallire (H-6 nel backlog).
> - CP5b e CP6 stanno insieme nel worktree, ma su file diversi: la validazione dopo la finestra vale per tutti e due,
>   e i commit si dividono per percorso.

### Dopo CP6: il lotto `billing_url` (deciso dal coordinatore, 2026-10-15 alle 08:40) — in attesa di A5

> - Nell'ordine: A5a e A5b entrano insieme dopo la finestra, dopo R e L; l'handoff di CP6 arriva prima. Quindi CP6
>   esce senza `billing_url`.
> - Dopo l'aggiornamento di base che porta A5, un lotto piccolo:
>   - `billing_url` in `InstanceBlockResponse`, solo per l'admin, da `registration_service.billing_link()` di A5a;
>   - il link «Gestisci abbonamento» nella pagina di blocco, con la sua chiave i18n e i test;
>   - `api instance-block` ripassato: A5a rende `get_instance_config` un `async` con una sessione del DB, e la guardia
>     deve restare la prima dipendenza.

#### CP5b e CP6 — i verdi prima della finestra ✅ (2026-10-15, mattina)

> **Note implementazione** (corsia 6181, un'invocazione alla volta, tutto finito prima delle 08:45):
>
> - `front build --debug` rc 0, svelte-check 0/0. `mkdocs build` stretto senza avvisi, 3020 URL relativi;
>   `check-links` 95.
> - **`all-backend`** (`-q --fresh-run --workers 2`): 7/7 in 17 min 23 s, con la macchina carica. **12 606 passed, 3
>   skipped, 0 failed**.
>   - Sono 170 in più rispetto a CP5a (12 436). Circa 110 vengono da CP6 e dalla correzione di CP5a:
>     `config-package` +39, `config-audit` +25, `instance-block` +44, `system` +1, `platform-readiness` +1.
>   - Gli altri vengono dagli aggiornamenti di base: G-8, X CP4, W K2a, A4b, X J-5.
> - Vitest: `core-unit` 4317, `component-unit` 3223, `onboarding-component-unit` 447; `AboutTab.test.ts` 38.
> - **`api schema`** contro `6cd64b71b`: solo `+/api/v1/system/block` e `+InstanceBlockResponse`; Tool contracts
>   identici; hash openapi `978bece3d1752e13`.
> - Statici: ruff, black e prettier puliti; porta dei colori pulita; `i18n check` stretto, 4396 chiavi.
> - **Dopo la finestra**: le E2E `front-utility auth`, `app-start-auth` e `settings` (il layout ha un ramo nuovo,
>   l'interceptor un ramo, la scheda Informazioni una guardia).

### Checkpoint CP5b e CP6 🧊 (2026-10-15) — FROZEN, in attesa del coordinatore; E2E dopo la finestra

> Committati dal coordinatore: `87be1e2d8`, `f8b827877` (CP5b), `2c3b00139`, `cb34327e9` (CP6) e `0326a1d02` (journal).
> Base aggiornata: `5b2b9061f`, merge di `dev_release2` a `2338aaf79` (J-6, W E0, X-R8), pulito. Entrano dopo la
> finestra della galleria, dopo R e L. Dopo l'avviso di fine finestra, sulla revisione combinata: `front build --debug`;
> `api instance-block`, `api system`, `services config-audit` e `config-package`, con la guardia di J-6 arrivata con la
> base; `core-unit`, `component-unit`; le E2E `auth`, `app-start-auth` e `settings`; `mkdocs build` stretto.

### CP7a — il lotto Docker (2026-10-15, mattina) — ✅ provato; manca solo la prova dell'immagine a runtime

> **Via** del coordinatore (08:46): durante la finestra si scrive il codice; la prova con Docker si chiede prima, perché
> richiede il daemon acceso. B aspetta CP7a per Litestream.
>
> **Ordine con CP6**: CP6 va validato sulla revisione committata. Prima di quella validazione salvo CP7a come patch nella
> cartella della sessione e lo tolgo con `git apply -R`; dopo, lo riapplico.
>
> **Superato** (coordinatore, 10:04): nessun file si sposta a mano. I tre lotti scritti (CP7a, C-96, il filtro del log)
> entrano come tre checkpoint «prima delle prove» sopra `5b2b9061f`; vedi «Handoff dei tre lotti» in fondo.

#### CP7a passo 1 — il codice ✅ (2026-10-15, mattina)

> **Note implementazione**:
>
> - **P-4** (D11): `tzdata` e `tzdata-legacy` via apt nello stadio finale del `Dockerfile`. `zoneinfo` legge il
>   database del sistema, e `tzdata` di PyPI non è nel lock. Senza `tzdata-legacy`, un fuso salvato con un nome vecchio
>   (`Asia/Calcutta`, `US/Eastern`) farebbe ricadere lo scheduler in UTC (`scheduler.py:20-24`). Da provare
>   nell'immagine.
> - **C-37**: `EXPOSE 6040` soltanto; tolta la mappatura `${TEST_PORT:-6041}:6041` da `docker-compose.yml`.
> - **N-8**: `PORT=6040` fra le `environment` dei due compose, con un commento: `PORT` è il lato host della mappatura,
>   nel container il server ascolta sempre su 6040.
> - **32-3** (D8): `./dev.py docker exec` lancia
>   `sh -c 'exec gosu "$LIBREFOLIO_UID:$LIBREFOLIO_GID" python dev.py "$@"' sh …`. Gli argomenti passano da `"$@"`, gli
>   id numerici vengono dall'ambiente dell'immagine. Corretto il commento del compose, che diceva «the 'librefolio'
>   user».
> - **M-25**:
>   - `_docker_ensure_assets_built()` congela la versione una volta sola, al passo 0, prima che un passo possa scrivere
>     un file tracciato;
>   - il frontend si ricostruisce, con `LF_APP_VERSION` uguale a quella versione, se i sorgenti sono cambiati, se
>     l'ultimo build era di debug o di modo ignoto, o se `frontend/build/.build-version` dice un'altra versione;
>   - `VERSION` riceve la stessa versione. Ogni build svuota `frontend/build/`, quindi il segno esiste solo dopo un build
>     per un'immagine;
>   - la logica sta in `_docker_frontend_stale_reason()` e `_docker_ensure_frontend_built()`: la complessità di
>     `_docker_ensure_assets_built` scende da 14 a 13, e la regola si prova da sola.
> - **C-26**: il tag `test` su GHCR si cancella con un'azione remota del developer; le istruzioni vanno nell'handoff.
>   Lettura anonima del registro (15/10, 08:55): 11 tag, `test` c'è ancora. Il suo digest (`a9cf8f56…`) non è
>   condiviso con nessun altro tag, quindi cancellare la sua versione non tocca `latest`, `nightly` né i rilasci.
> - `dev.py` si importa; i rilievi di ruff sono gli stessi di HEAD, a parte la complessità scesa.

#### CP7a passo 2 — doc, e le correzioni venute dalla sua lettura ✅ (2026-10-15, mattina)

> **Note implementazione**:
>
> - **Doc** (docs-writer, senza build: siamo nella finestra della galleria):
>   - `admin/docker_advanced.en.md`: `docker exec` con gli id numerici, porte, `PORT=6040`, la modalità di test, la
>     tabella e il YAML annotato;
>   - `developer/dev_workflow.en.md` (passi del build con la versione congelata, niente più conflitto sulla 6041);
>   - `release-pipeline.md` (sottosezione «Local image builds»), `architecture/overview.md`, `backend/scheduler.md`
>     (`tzdata-legacy`), `admin/cli_tools.en.md`, `admin/configuration.en.md`;
>   - `- PORT=6040` negli snippet di `user/installation.en.md` e `admin/service_exposure.en.md`;
>   - debito di traduzione in `docker_advanced`, `cli_tools`, `configuration`, `service_exposure` e `installation`, non
>     timbrato.
> - **Correzioni dalla lettura di docs-writer**:
>   - un `.build-version` mancante ora ha il suo motivo («made without a recorded version»), distinto da una versione
>     diversa;
>   - `_get_docker_tag()` rifaceva `git describe` dopo i passi di build, quindi il tag poteva dire `-dirty` mentre
>     `VERSION` e la barra laterale no. Ora legge `VERSION`, scritto con la versione congelata; senza il file la
>     ricalcola;
>   - `_check_env_file()` avvisava anche per `TEST_PORT`, che il compose non usa più: ora solo `PORT`;
>   - l'intestazione di `.env.example` ora dice che il compose fissa anche `PORT=6040`.
>
> **Fuori pista** (fuori dal lotto, nel backlog):
>
> - H-7: senza `tzdata` di PyPI, un'installazione su un sistema senza database dei fusi (Windows) fa ricadere ogni fuso
>   dello scheduler in UTC;
> - H-8: `ForgotPasswordCard.svelte`, di A, mostra ancora un `docker compose exec … user reset`, che gira come root.

### C-96 — le corsie dei test non prendono la configurazione dell'istanza (2026-10-15, mattina) — ✅ provato

> **Richiesta** del coordinatore (09:05), da un difetto trovato da E. `configure_test_runtime()` toglieva solo
> `INSTANCE_TRUST_SECRETS`: ogni altra impostazione del `.env` del developer arrivava alle corsie (SMTP, blocco, profilo
> gestito, le variabili di account di A5a). A-9 di A diventa parte di C-96. Il codice si scrive adesso; le prove complete
> dopo la finestra.
>
> **Disegno**: le vie per cui l'impostazione arrivava sono due.
>
> - L'ambiente. `pipenv run` carica il `.env` prima che `dev.py` parta, e `_load_project_dotenv()` lo completava. La
>   corsia ora toglie, qualunque sia l'origine (`.env` o shell):
>   - ogni chiave del `.env` del developer;
>   - ogni variabile documentata in `.env.example`;
>   - i segreti d'istanza.
>   Restano solo `TEST_LANE_KEEPS` (porte, cartelle dei dati, `HOST`, livello di log) e `TEST_LANE_RUNNER_OWNED` (il
>   token della corsia). Dal `.env` si completa solo quell'elenco.
> - `Settings`, che legge il `.env` da sé (`env_file`). In modalità test, `settings_customise_sources` toglie la fonte
>   dotenv: un `Settings()` diretto obbedisce come `get_settings()`.
> - Una variabile nuova di B o di E è coperta da sola: è documentata in `.env.example`, come esige la guardia, oppure
>   sta nel `.env` del developer.
>
> **Note implementazione**:
>
> - `scripts/cli_base.py`: `TEST_LANE_KEEPS`, `TEST_LANE_RUNNER_OWNED`, `documented_instance_variables()` (le righe
>   variabile di `.env.example`, commentate o no), `_test_lane_drops()`, `_load_project_dotenv(only=…)`;
>   `configure_test_runtime()` toglie le variabili dopo le verifiche, prima di `PIPENV_DONT_LOAD_ENV`.
> - `backend/app/config/__init__.py`: `Settings.settings_customise_sources`.
> - `.env.example`: una nota nella sezione «Test Server».
> - **Prova in processo**: un `.env` temporaneo, più esportazioni della shell.
>   - Tolti: profilo, blocco, SMTP (non documentata, ma nel `.env`), cache delle anteprime, l'interruttore delle
>     donazioni, `JWT_SECRET` e un'esportazione della shell di una variabile documentata.
>   - Restano: livello di log, `HOST`, `PORT`, una variabile estranea a LibreFolio e quelle del runner.
>   - Una seconda chiamata, come quella del server condiviso, tiene lo stesso token.
>   - `Settings` in modalità test non legge il `.env` nemmeno quando glielo si passa; fuori dalla modalità test lo legge.
> - Il server condiviso e il `webServer` di Playwright passano `--no-scheduler`, che `cmd_server` rimette dopo la
>   configurazione della corsia. Toglierla dal `.env` non riaccende quindi lo scheduler.
> - Ruff pulito. Black segnala su `cli_base.py` un debito di formato che c'era già; il file non è nel suo perimetro.
> - **Doc**, mia, pagine solo inglesi:
>   - `developer/architecture/security.md`: la sottosezione «Test lanes and the instance's configuration»;
>   - `developer/test-walkthrough/index.md`: un paragrafo in «Isolated Runtime Lanes»;
>   - `developer/architecture/settings.md`: un rimando.
>   - Build e `check-links` dopo la finestra.
> - **Test** affidati a test-author: il test guidato da `.env.example` che il coordinatore ha chiesto, più le chiavi non
>   documentate, la chiamata annidata, la corsia rifiutata e `Settings` in modalità test.

#### CP7a passo 3 — i test ✅ (2026-10-15, mattina)

> **Note implementazione** (test-author):
>
> - Nuovo `backend/test_scripts/test_utilities/test_dev_cli_docker.py`, IMG-013…024, registrato come
>   `utils dev-cli-docker` (puro). 95 test, circa 3 s; Docker non serve e nel repo non si scrive niente.
>   - Statici, ciascuno con il suo controllo che deve fallire su file sintetici, compreso lo stato prima di CP7a:
>     `tzdata-legacy` nell'immagine finale, `EXPOSE` uguale al `--port` del CMD, il servizio `librefolio` che pubblica
>     solo la 6040, `PORT`/`HOST`/`LIBREFOLIO_DATA_DIR` nei due compose;
>   - `docker exec`: l'argv esatto; gli argomenti ostili restano elementi separati, e una prova con un vero `sh` lo
>     dimostra; gli id dati a gosu vengono da un `ENV` dell'immagine finale;
>   - M-25: i motivi della ricostruzione, `LF_APP_VERSION` messo e rimesso a posto anche su errore ed eccezione, la
>     versione congelata fino a `VERSION` e al tag anche quando git, dopo il passo 0, risponde `-dirty`; `cmd_docker_build`
>     da capo a fondo;
>   - `_check_env_file` avvisa per `PORT` e tace su `TEST_PORT`.
> - `utils dev-cli-docker` 95 passed; `check-orphans` pulito.
>
> **Fuori pista**: lo script di `docker exec` non aveva i valori predefiniti degli id, che `entrypoint.sh` ha
> (`:-1000`): ora li ha, e la doc lo riporta. test-author ha aggiornato l'argv esatto. Il caso nuovo, con un `gosu`
> finto sul `PATH`, verifica che senza le variabili arrivi `1000:1000`, e che `entrypoint.sh` usi gli stessi valori.
> `utils dev-cli-docker` 96 passed.
>
> **Fuori pista** (dal rapporto di test-author, 15 test nuovi, `utils runtime-isolation` 190):
>
> - La prima regola toglieva `LF_APP_VERSION`, documentata in `.env.example`. Così il job di rilascio avrebbe perso,
>   nella galleria, la versione congelata di CP5a.
> - Un `LIBREFOLIO_*` non documentato esportato nella shell restava. Ogni chiave del `.env` veniva tolta, comprese
>   quelle estranee a LibreFolio (un proxy, `PYTHONPATH`).
> - **Regola corretta**:
>   - `kept_in_a_test_lane(name)`: `TEST_LANE_KEEPS` (le due porte, la cartella di produzione, `HOST`, il livello di
>     log, `LF_APP_VERSION` e il `LIBREFOLIO_SERVER_WORKERS` di Playwright) oppure ogni nome `LIBREFOLIO_TEST_*`, cioè
>     quelli del runner e dei test, compreso il token della corsia. `TEST_LANE_RUNNER_OWNED` non serve più;
>   - si toglie ogni variabile documentata, ogni segreto d'istanza e ogni `LIBREFOLIO_*` dell'ambiente, salvo quelli
>     tenuti;
>   - il `.env` si carica per intero come prima, poi si toglie: le chiavi che non sono di LibreFolio restano.
> - Prova in processo ripetuta: `LF_APP_VERSION` resta, come `LIBREFOLIO_TEST_STARTUP_TIMEOUT` e le chiavi estranee del
>   `.env`. Un `LIBREFOLIO_*` nuovo esportato nella shell se ne va. Doc e nota di `.env.example` allineate.
> - Restano due limiti, scritti nel codice e nella doc:
>   - senza `.env.example`, cioè nell'immagine Docker, dove però non gira nessuna corsia, cadono solo i `LIBREFOLIO_*` e
>     i segreti;
>   - un helper dei test che chiama `configure_test_runtime()` toglie anche nel processo del test. Nessun test di oggi
>     imposta una variabile documentata prima di chiamarlo.
> - **Test allineati alla regola corretta** (test-author): `utils runtime-isolation` 194 passed.
>   - Le attese sono costruite con `kept_in_a_test_lane`. Tre controlli nominano i valori direttamente:
>     `LF_APP_VERSION`, i cinque `LIBREFOLIO_TEST_*` e la sonda non documentata.
>   - Dieci regressioni simulate in memoria fanno fallire ciascuna almeno un test.
>   - Chiesto in più un figlio `pipenv run` vero: pipenv carica il `.env` con `override=True`, e solo
>     `PIPENV_DONT_LOAD_ENV` tiene fuori le impostazioni tolte.
>   - Fatto: `test_a_pipenv_run_child_of_the_lane_gets_no_dropped_setting_back`, con il suo controllo. Lo stesso figlio
>     senza la guardia riprende le impostazioni tolte; con la guardia no, e tiene `LF_APP_VERSION`.
>   - Prima dei figli, `pipenv --venv` verifica che pipenv usi questo interprete, e il test salta se no: così pipenv
>     non crea mai un ambiente. La stessa guardia va al test annidato che c'era già e non l'aveva.
>   - `utils runtime-isolation` 195 passed.
>   - Le due prove annidate passano ora da un helper solo, `run_python_in_a_pipenv_child()`. Prima di ogni
>     `pipenv run`, l'helper fa `pipenv --venv`, e salta se l'ambiente non è questo. La verifica con un `subprocess`
>     finto: se l'ambiente è un altro, o se non c'è, parte solo `pipenv --venv` e niente viene creato.
>     `utils runtime-isolation` 195 passed, 0 skipped.

#### C-96 — stato (2026-10-15, mattina)

> Codice, test e doc scritti. Le prove complete dopo la finestra della galleria: `all-backend`, perché
> `configure_test_runtime` e `Settings` toccano ogni corsia; `mkdocs build` e `check-links`.

### Lotto «credenziali nei log di accesso» (2026-10-15, mattina) — ✅ provato

> **Richiesta**: una nota di A5b, girata dal coordinatore alle 09:59. I link di invito, reset, setup e verifica ora
> portano il token nel frammento, che il browser non manda. Resta un `?token=` scritto a mano, che il log di accesso di
> uvicorn scriveva in chiaro. Il posto lo scelgo io: un lotto a parte, dopo CP7a e C-96, prima di CP7b e della
> revisione di sicurezza finale.

#### Passo 1 — il codice e la doc ✅ (2026-10-15, mattina)

> **Note implementazione**:
>
> - `backend/app/logging_config.py`:
>   - `mask_query_credentials(text)` sostituisce con `***` il valore di un parametro di query che si chiama `code`, o il
>     cui nome contiene `token`, `secret`, `password`, `passwd`, `api_key`/`apikey`/`api-key` o `signature`, in
>     qualunque maiuscolo. Il nome si giudica decodificato (`unquote_plus`), come lo legge l'app; il valore no;
>   - `_QueryCredentialFilter` maschera ogni argomento stringa del record, al suo posto: numero e ordine restano, e
>     l'`AccessFormatter` di uvicorn li spacchetta. Un messaggio senza argomenti si maschera da sé; una stringa di
>     formato con argomenti non si tocca, così i segnaposto restano allineati;
>   - `configure_logging()` mette lo stesso oggetto filtro su `uvicorn.access` (HTTP) e su `uvicorn.error` (le strette
>     di mano WebSocket, che portano anche loro percorso e query): le chiamate ripetute non lo duplicano, e ogni worker
>     lo installa importando l'app.
> - Il log resta acceso ovunque: chi ospita da sé lo usa.
> - Nessun reindirizzamento dell'app copia il frammento in una query: `loginUrl()`, `hooks.server.ts` e `returnTo`
>   portano percorso e query, mai il frammento.
> - **Prova in processo**: 13 casi della regola e 6 di record. Fra questi: `GET /setup?token=***&next=/home`;
>   `tok%65n`, `api%5Fkey`, `api-key` mascherati; `currency_code`, `codes` e `q=token` tenuti; la riga WebSocket
>   mascherata; un record senza niente da mascherare tiene lo stesso oggetto. Ruff e black puliti.
> - **Doc**: in `security.md` la sezione nuova «📜 Request Logs», lontana da quella dei token di A.
>
> **Fuori pista** (dal primo rapporto di test-author, 51 test):
>
> - Il primo filtro leggeva solo il terzo argomento, se il record ne aveva almeno tre: diverso da come l'avevo
>   descritto, e legato alla forma di un solo record. Ora ogni argomento stringa, al suo posto.
> - Fuori dalla prima regola: un nome codificato (`tok%65n`), `api-key` con il trattino, e le righe WebSocket su
>   `uvicorn.error`. Ora coperti tutti e tre.
> - Limite scritto nel codice e nella doc: un URL codificato dentro il valore di un altro parametro non si legge.
> - H-9 nel backlog: una seconda chiamata di `configure_logging()` lascia aperti i gestori che toglie. C'era già.

#### Passo 2 — i test ✅ (2026-10-15, mattina)

> **Note implementazione** (test-author):
>
> - `backend/test_scripts/test_services/test_logging_access_filter.py`, selettore puro `services logging-access-filter`
>   in `scripts/test_runner/_backend_services.py`: 96 passed.
>   - (a) la regola, 54 test:
>     - i nomi semplici, quelli codificati (`tok%65n`, `api%5Fkey`, `c%6Fde`) e il trattino;
>     - i nomi tenuti e l'URL annidato non codificato;
>     - il valore vuoto, mascherato;
>     - il valore codificato, fissato come limite: prima il test verifica che lo stesso URL, decodificato, viene
>       mascherato.
>   - (b) il filtro su un record, 30 test:
>     - ogni posizione in una tupla da 1 a 6 argomenti;
>     - lo stesso oggetto quando non c'è niente da mascherare;
>     - bytes, `None`, interi e mappe intatti;
>     - il messaggio senza argomenti mascherato;
>     - la stringa di formato con argomenti mai riscritta.
>   - (c) i record di uvicorn, 11 test, ciascuno con il suo controllo negativo senza filtro:
>     - una richiesta HTTP vera, in memoria, con h11 e con httptools;
>     - una stretta di mano WebSocket vera, rifiutata, con `WebSocketsSansIOProtocol`, quello che `--ws auto` sceglie.
>   - (d) `configure_logging()` chiamata due volte lascia un solo filtro, quello del modulo, su ciascuno dei due logger.
>     Le righe di uvicorn escono mascherate; i logger e structlog vengono rimessi a posto.
> - 13 regressioni simulate, ciascuna presa da almeno un test. Per esempio: il vecchio filtro sul solo terzo argomento
>   fa 26 rossi; i nomi non decodificati 7; `configure_logging` solo su `uvicorn.access` 1.
> - Ruff, black e `check-orphans` puliti.
>
> **Fuori pista**:
>
> - Il test della stringa di formato con argomenti fissava una riga con il valore in chiaro. Ora verifica solo che `msg`
>   e `args` restano intatti e che la formattazione non fallisce.
> - **Residuo**, letto nel sorgente di uvicorn: con `--log-level trace`, `MessageLoggerMiddleware` scrive ogni messaggio
>   ASGI su `uvicorn.asgi`, intestazioni comprese.
>   - uvicorn fissa `uvicorn.error` a INFO, e né `dev.py` né il `Dockerfile` passano `--log-level`: la modalità si
>     accende solo se qualcuno la chiede.
>   - È scritto come limite in `security.md`.

### Handoff dei tre lotti — checkpoint «prima delle prove» 🧊 (2026-10-15, mattina)

> **Decisione del coordinatore** (10:04): nessun file si sposta a mano.
>
> - I tre lotti entrano come tre checkpoint separati sopra `5b2b9061f`, più il journal, con le prove leggere.
> - Dopo la finestra il coordinatore stacca il worktree su `5b2b9061f` per la validazione di CP6, poi lo riattacca al
>   ramo per le prove dei tre lotti.
> - CP6 entra in `dev_release2` da `5b2b9061f`; i tre lotti restano sul ramo finché non sono provati.
>
> **Prove leggere**: corsia 6181, solo selettori puri, uno alla volta, con `nice`. In tutto 1451 passed.
>
> - `utils`: `dev-cli-docker` 96, `dev-cli-image` 44, `release-image-contract` 192, `runtime-isolation` 195.
> - `services`: `config-env-example` 36, `config-package` 632, `config-secrets` 58, `config-audit` 90, `config-misc`
>   12, `logging-access-filter` 96.
> - `check-orphans` e `git diff --check` puliti.
> - Ruff e black:
>   - puliti sui file nuovi e su quelli dei lotti;
>   - su `dev.py` e `cli_base.py`, gli stessi rilievi della base;
>   - la complessità di `_docker_ensure_assets_built` scende da 14 a 13.
>
> **Dopo la finestra**:
>
> - `all-backend`, perché C-96 tocca ogni corsia;
> - `front build --debug`, perché `dev.py` è cambiato;
> - `mkdocs build` stretto e `check-links`;
> - la prova Docker di CP7a, con il via del coordinatore.
>
> **Committati dal coordinatore** (10:48), con `git apply --cached` per patch e le impronte verificate:
> `2e2d7ee70` (CP7a, 16 file), `901fa33f6` (C-96, 7), `4f5757915` (filtro del log, 4), `056ed3897` (journal, 2).

### Validazione di CP5b e CP6 sulla revisione combinata ✅ (2026-10-15, pomeriggio)

> **Come**: dopo la finestra della galleria il coordinatore ha staccato il worktree su una revisione combinata, cioè
> `dev_release2` più `5b2b9061f`, senza i tre lotti. Nessun file modificato, quindi il piano si scrive adesso.
>
> - `64ed18b05` = `13705dd05` + `5b2b9061f` (con R, L, G e la 1.2.1); poi `83eaa5a28` = `dc9a5d232` + `5b2b9061f`,
>   dopo la finestra delle dipendenze (`cryptography` 50.0.2, `pycparser` 3.11). Fra le due cambiano solo `Pipfile` e
>   `Pipfile.lock`.
> - L'altro lato tocca solo `main.py` (il `confined_path` della 1.2.1), il `+layout.svelte` della radice (Designer Lab)
>   e `themeStore.ts`. Non tocca `(app)/+layout.svelte`, `zodios-client.ts`, `features/instance/` né `AboutTab`.
>
> **Esiti** (corsia 6181, un comando alla volta, con `nice`):
>
> - Su `64ed18b05`:
>   - `front build --debug` (con `api sync` dentro, le uscite sono file ignorati): rc 0, svelte-check 0/0;
>   - `npm run check`, cioè `dev.py front check`, lanciato durante la pausa del Python: 0/0;
>   - Vitest con gli elenchi del runner: `core-unit` 4407, `component-unit` 3240 (con `InstanceBlockedPage`,
>     `InstanceNotices` e `AboutTab`), `onboarding-component-unit` 447 (con i gate del layout `(app)`).
> - Su `83eaa5a28`:
>   - `mkdocs build` stretto rc 0; `check-links`: 95 link validi, 3028 URL di asset risolti;
>   - **`all-backend`** (`-q --fresh-run --workers 2`, slot pesante 1): 7/7, **12 725 passed, 3 skipped, 0 failed**, in
>     31 min 32 s;
>   - E2E `front-utility` con `--workers 2`: `auth` 29, `app-start-auth` 3, `settings` 46, tutte passed.
>
> **Fuori pista**: alle 13:54 il carico era a 110–139 su 10 core, con X, A, E, un'altra corsia e il mio `all-backend`.
> L'ho segnalato con i numeri per corsia; il coordinatore ha fermato le prove medie di A e di E.
>
> **Ingresso**: CP5b e CP6 sono in `dev_release2` = `83eaa5a28`, con un avanzamento veloce; sopra è entrato X
> (`ec0dc7ebd`). Il ramo è tornato al suo posto con il merge di `dev_release2` in `aa0e3a49a` (genitori `056ed3897` e
> `ec0dc7ebd`), senza conflitti. CHANGELOG di CP5b e CP6 mandato al coordinatore, che lo scrive.
>
> **Ordine deciso**:
>
> 1. questa nota;
> 2. un lotto piccolo, G-10 e le due note di E, con il rosso prima;
> 3. una validazione unica di CP7a, C-96, filtro del log, G-10 e doc. Per `all-backend` lo slot si chiede al
>    coordinatore;
> 4. la prova Docker. Il daemon è acceso; alla fine si tolgono le immagini e i container creati da H.

### Lotto piccolo: G-10 e due note di E (2026-10-15, pomeriggio) — ✅ provato

> **G-10**, dal programma colori: `list_uploads` (`services/files/static_uploads.py`) ordina solo per `uploaded_at`. Gli
> avatar del seed hanno tutti la stessa data, quindi l'ordine segue quello della cartella, cioè gli UUID casuali, e la
> galleria diventa instabile: `asset-picker-modal` al 24 %, la miniatura di `static-grid`.
>
> - Cura: a parità di data, il nome e poi l'id. L'id da solo non basta: è un UUID nuovo a ogni seed, quindi stabile
>   dentro un DB ma diverso in ogni galleria.
> - `AssetPickerModal` mostra l'ordine dell'API senza riordinare: basta il backend.
>
> **Note di E**:
>
> - Il paragrafo «Secrets» di `.env.example` dice che un `NAME_FILE` illeggibile ferma il server. È già falso oggi per
>   il link finder: `web_link_finder.py` registra un avviso e spegne il link finder, e l'avvio continua.
>   `admin/configuration.en.md` lo dice già bene. Il paragrafo si allinea: si fermano solo `JWT_SECRET_FILE` e
>   `LIBREFOLIO_INSTANCE_KEY_FILE`, un segreto facoltativo spegne solo la sua funzione. Il segreto dell'email di E ci
>   rientra senza nominarlo prima che esista.
> - `settings.md`: all'elenco di `platform.py` mancano `frozen_app_version()` (CP5a), `instance_blocked()` e
>   `instance_deletion_date()` (CP6).
>
> **Note implementazione**:
>
> - **Il rosso prima** (test-author): la classe nuova `TestListUploadsOrder` in `test_static_uploads.py`, 4 test.
>   - `get_uploads_dir` viene sostituita da un `Path` il cui `glob()` dà i file veri in ordine crescente o decrescente;
>     ogni test elenca gli stessi upload nei due ordini, e i due risultati devono essere uguali e quelli attesi. Così il
>     rosso non dipende dal caso. Un'asserzione in più fallisce se `list_uploads` smette di elencare con
>     `get_uploads_dir().glob()`.
>   - Sul codice di prima: 3 rossi (stesso istante e nomi `b`, `A`, `C`, che fissano anche il `casefold`; stesso nome e
>     stesso istante; i 30 avatar del seed) e un controllo verde, il più recente prima.
> - **Cura**, `list_uploads()`: due ordinamenti stabili, prima per `(original_name.casefold(), id)`, poi per
>   `uploaded_at` decrescente. `services static-uploads`: 39 passed. Ruff e black puliti.
> - **Note di E**: il paragrafo «Secrets» di `.env.example` e l'elenco di `platform.py` in `settings.md`, come sopra.
>   `services config-env-example`: 36 passed.
>
> **Fuori pista** (da test-author, nel backlog come H-10): `services static-uploads` è dichiarata `write-scoped`, ma il
> suo fixture autouse cancella e ricrea la cartella `custom-uploads` della corsia, dove stanno anche gli avatar del seed.
> C'era già prima.

### Validazione unica dei quattro lotti e prova Docker (2026-10-15, pomeriggio) — 🧊

> **Revisione**: `aa0e3a49a` più il lotto piccolo, non committato. Corsia 6181, un comando alla volta, con `nice`.
>
> - `front build --debug` rc 0, svelte-check 0/0. `mkdocs build` stretto rc 0. `check-links`: 95 link validi, 3028 URL
>   di asset risolti.
> - **`all-backend`** (`-q --fresh-run --workers 2`, slot pesante 1, 14:37:55–15:00:34): 7/7, **12 941 passed, 3
>   skipped, 0 failed**.
>
> **Prova Docker** (slot 1; il daemon lo accende il developer):
>
> - **Prima**: le immagini `alpine:3.20` e `python:3.13-slim`, nessun container, nessun progetto compose.
> - `dev.py docker build`, con un `.env` temporaneo (`PORT=7001`).
>   - La versione si congela una volta sola: `VERSION`, `frontend/build/.build-version` e il tag
>     `librefolio:v1.2.1-323-gaa0e3a49a-dirty` coincidono, e il bundle di produzione, ricostruito per quella versione,
>     la contiene. È M-25 dal lato host.
>   - Il passo apt dell'immagine finale (`gosu`, `sqlite3`, `tzdata`, `tzdata-legacy`) è andato.
> - **Il build si ferma a `pip install` nello stadio `pybuilder`**: dal container di build, PyPI risponde «self-signed
>   certificate in certificate chain».
>   - Su questa rete un proxy ri-firma il TLS, e il container non ne conosce la CA. Dalla cache di pip arrivano solo le
>     due dipendenze git; `aiosqlite==0.22.1` non c'è.
>   - CP7a non tocca il passo di pip.
> - **Provato senza l'immagine**:
>   - **P-4**, in un container usa e getta sulla stessa base. `python:3.13-slim` (trixie) ha `tzdata` 2026c ma non
>     `tzdata-legacy`: `Asia/Kolkata` ed `Europe/Rome` si risolvono, `Asia/Calcutta` e `US/Eastern` no. Dopo la riga apt
>     del `Dockerfile` si risolvono tutti e quattro.
>   - **N-8**, con `docker compose config`, che non crea niente: con `PORT=7001` nel `.env`, i due compose pubblicano
>     7001 → 6040 e mettono `PORT=6040` nel container.
>   - **C-37 e 32-3** non sono provati a runtime. Li coprono i controlli statici di `utils dev-cli-docker`: `EXPOSE`,
>     l'argv esatto, un vero `sh` con un `gosu` finto.
> - **Pulizia**, confrontata con lo stato di prima:
>   - tolta la rete del progetto `lf-h-cp7a`; nessuna immagine nuova, perché il build non ne ha create;
>   - container, reti e volumi come prima;
>   - tolti `.env`, `VERSION` e `requirements.txt`; il worktree è come prima;
>   - la cache di BuildKit, condivisa, non è stata toccata;
>   - poi `front build --debug`, per rimettere il bundle di debug.
> - **Resta da fare**: la prova a runtime dell'immagine (avvio, healthcheck, `docker exec` come uid:gid, versione nella
>   barra laterale) dove PyPI si raggiunge senza proxy.
>
> **Fuori pista**: H-11 nel backlog. Un build locale dietro un proxy che ri-firma il TLS si ferma a `pip install`.

### Due aggiornamenti di base (E1 e Y1, poi A5) e la verifica di C-96 con le variabili di A5 (2026-10-15, pomeriggio)

> **Committati dal coordinatore**: `b4533a949` (G-10), `064f2ce4b` (doc della configurazione), `831aa4d39` (journal).
>
> - **Merge di `badec1465`** (E1, Y1), committato in `3bd15098a`. Un conflitto in `settings.md`: l'elenco dei moduli di
>   `config/`, con l'`email.py` di E1 e i miei tre accessori di `platform.py`. Risolto tenendo le due parti.
>   - Rivisti i file fusi in automatico: `.env.example`, `security.md`, le registrazioni del runner, il backlog.
>   - Prove: `mkdocs build` stretto, `check-links` 95, `config-env-example` 36, `config-package` 639 (+7, i moduli nuovi
>     di E1), `static-uploads` 39, `runtime-isolation` 195.
> - **Merge di `8bcb23502`** (A5), committato in `9e411c6ec`. Stesso paragrafo di `settings.md`: i cinque accessori nuovi
>   di `accounts.py` e la frase di chiusura di A, più i miei tre. `mkdocs build` stretto e `check-links` puliti.
>
> **Verifica di C-96 con le variabili di A5** (`LIBREFOLIO_REGISTRATION`, `MAX_USERS`, `PUBLIC_URL`, `BILLING_URL`):
>
> - Su ciascuna via, C-96 non c'entra:
>   - i test di A le impostano con `monkeypatch.setenv` dentro il test, dopo che la corsia è stata preparata;
>   - IMG-013…016 le passano nell'ambiente esplicito del sottoprocesso `dev.py user`, che non prepara una corsia.
> - Primo giro, nell'ordine: `services registration` 146, `utils dev-cli-image` 71, `api system` 117; ma
>   `api registration` 1 rosso, `api users-admin` 28 rossi, `api instance-block` server uscito all'avvio.
> - **Causa dei 29 rossi: ambiente.** In un'azione singola il runner non esegue il setup della categoria `api`
>   (`_api_setup` → `db populate`). La mia `services registration` appena prima aveva ricreato vuoto il DB della corsia,
>   quindi il primo account registrato diventa admin (regola di A5). LIVE-002 dà `user_id=1`, `is_superuser` True.
>   `users-admin` lo dice nel suo controllo di precondizione; LIVE-002 non ha quel controllo (file di A).
> - **Conferma**: `test db populate --force` (lo stesso passo di `_api_setup`), poi `api registration` 65 e
>   `api users-admin` 53, tutti passed.
>
> **Fuori pista**:
>
> - **Conflitto semantico CP6 × A5a**, rosso anche in `dev_release2` a `8bcb23502`: `test_instance_block.py` fissava il
>   corpo di `GET /system/instance` a `{"profile": …}`, e A5a ha aggiunto `accounts`.
>   - Riparato da test-author: per ogni rotta permessa il test confronta la risposta bloccata con quella della stessa
>     richiesta a blocco spento, e così regge i campi che le altre sessioni aggiungeranno.
>   - Il controllo negativo (un campo che cambia solo col blocco) dà 2 rossi. `api instance-block`: 44 passed.
>   - Restano fissati i corpi di `/system/block`, che sono di H; si aggiornano con `billing_url`.
> - **Avvio del server condiviso fallito una volta** (codice 1), 0 s dopo la fine di `api users-admin`; non si è
>   ripetuto. L'output del server condiviso è scartato, quindi la causa non si vede. H-12 nel backlog.

### Lotto «billing_url e rotte dei link», H-12 e la regressione di `/system/instance` (2026-10-15, pomeriggio) — ✅ provato

> **Richiesta** del coordinatore (15:54), piano approvato (15:59): quattro punti in ordine. Per H-12 serve
> `all-backend`, perché tocca `dev.py`. Sul mio ramo a `8b5e94be6`, che contiene già A5.
>
> - `deletion-preview` (`auth.preview_own_account_deletion`) arriva con A6a e resta fuori. Se entra prima H, la riga
>   nell'elenco e nel test la aggiunge A; se entra prima A, la aggiunge H.
>
> **Note implementazione**:
>
> 1. **`billing_url`**:
>    - `InstanceBlockResponse.billing_url`, riempito in `system/block.py` da `registration_service.billing_link()`
>      (`LIBREFOLIO_BILLING_URL`, A5) solo per l'admin; `None` per gli altri, e quando la variabile manca o non è
>      http(s).
>    - Nella pagina di blocco, l'admin vede il link «Manage subscription» (`target=_blank`, `noopener noreferrer`,
>      icona `ExternalLink` nascosta agli screen reader).
>    - `httpAddress()` ricontrolla lo schema http(s) prima di farne un `href`.
>    - Chiave `instance.block.manageSubscription` nelle 4 lingue (`dev.py i18n add`); `api sync`.
> 2. **`ALLOWED_WHEN_BLOCKED`**: aggiunti `auth.inspect_link_token` e `auth.reset_password_with_link`.
>    - Così chi ha perso la password può ancora arrivare alla pagina di blocco, alla cancellazione o al backup: i due
>      endpoint consumano solo link già inviati.
>    - `register` resta fuori: un invito si legge ma non si accetta.
> 3. **`settings.md`**: `LF_APP_VERSION`, `LIBREFOLIO_BLOCKED` e `LIBREFOLIO_DELETION_DATE` nell'elenco delle chiavi fuori
>    da `Settings` (docs-writer).
> 4. **H-12**, la metà sul controllo della porta.
>    - Il rosso prima (test-author): il caso (e) in `test_dev_port_check.py`. Un socket che tiene la porta con una
>      connessione accettata, a listener chiuso, veniva riportato: 1 failed e 4 passed sul codice di prima.
>    - Cura: `check_port_in_use` usa `lsof -nP -iTCP:PORT -sTCP:LISTEN -t` dove `lsof` c'è, come `port_holders` del
>      runner; su Linux senza `lsof` resta `fuser` come ripiego.
>    - `utils dev-port-check`: 5 passed.
>    - Ruff: 42 rilievi su `dev.py` come a HEAD; la differenza di black scende da 339 a 322 righe.
>    - Resta aperta l'altra metà: l'output scartato del server condiviso.
> 5. **Regressione `/system/instance`** nelle E2E a insieme chiuso (il coordinatore alle 16:42; l'ha trovata Y).
>    - Lo store di CP4 legge la configurazione d'istanza a ogni caricamento di pagina, e due spec ammettono solo i GET
>      dichiarati: `files-uploader` (0/8) e `layout/header-scroll` (0/4). Le altre spec con una route `**/*` lasciano
>      passare con `route.fallback()`.
>    - Cura (test-author): `plainInstanceConfig()` in `fixtures/instance-config.ts`, un corpo sintetico controllato con lo
>      schema generato, dichiarato nelle due spec.
>    - Dopo: 8/8 e 4/4; `auth` 33 e `auth-links` 9, che importano la stessa fixture.
>
> **Doc**:
>
> - docs-writer: `security.md` («Instance Block»: la riga della tabella, `billing_url`, «Changing the list»),
>   `admin/hosting_providers.en.md` (la frase d'apertura, il link per l'admin, la riga «What Still Answers») e
>   `settings.md`.
> - Io: `admin/configuration.en.md`, la riga di `LIBREFOLIO_BILLING_URL` («the app does not show it yet» non è più vero).
>   IT, FR ed ES non hanno quella riga, che è debito di A5, quindi non ho timbrato.
> - Una riga dichiarata in `access_control.md` (pagina di A): `/system/block` fra i posti del link di fatturazione.
>
> **Risposte ad A6a**, girate dal coordinatore:
>
> - CORS: provato in processo con i parametri di `main.py`. Una GET semplice tiene l'`Access-Control-Allow-Origin: *`
>   della rotta (il middleware aggiunge solo `Allow-Credentials`, ignorato con `credentials: 'omit'`). Un preflight
>   avrebbe un `400 Disallowed CORS origin`: quindi niente header, e il nonce nella query.
> - `derive_key("accounts.address-probe.v1")` va bene, chiamata con `asyncio.to_thread`: legge la chiave a ogni
>   chiamata.
>
> **Prove mirate** (corsia 6181, una alla volta, con `nice`):
>
> - `api instance-block` 53 (era 44: le due rotte dei link, il reset con un link davvero emesso a istanza bloccata,
>   `billing_url` per admin, utente, variabile assente e non valida); `api system` 117; `utils dev-port-check` 5;
> - Vitest `component-unit` 3389 (`InstanceBlockedPage.test.ts` 22, era 14, con il controllo negativo della guardia);
> - `front build --debug` con svelte-check 0/0; `i18n check` stretto, 4417 chiavi; theme-roles pulito;
> - `mkdocs build` stretto e `check-links` 95.
>
> **Fuori pista**:
>
> - docs-writer aveva messo un link `configuration.md#accounts`. Il build stretto lo rifiuta: sul sito IT la pagina
>   inglese di riserva punta a `configuration.it.md`, che non ha ancora la sezione Accounts di A5. Ora il link va alla
>   pagina.
> - test-author ha aggiornato anche `test_openapi_documents_the_block_page`, che fissava le proprietà dello schema.
>
> **`all-backend`** (slot 1, 16:51–17:21): 7/7, **13 792 passed, 3 skipped, 0 failed**. Committato dal coordinatore:
> `eaba49c6e`, `a4e770365`, `87f9ed6b5`, `9893aeb9d`, `530ed9262`.

#### Ingresso dopo A6a: l'anteprima della cancellazione e A-15 ✅ (2026-10-15, sera)

> **Base**: `69a7f0eb4`, merge di `dev_release2` (`ca4ec658e`, con A6a e il C-94 di J in `cmd_server`), senza conflitti.
> A6a è entrato prima di H, quindi la riga la aggiunge H (regola delle 15:58).
>
> **Note implementazione**:
>
> - `auth.preview_own_account_deletion` (`GET /auth/users/me/deletion-preview`) entra in `ALLOWED_WHEN_BLOCKED`, accanto
>   alla cancellazione che descrive; il suo pin, per nome e rotta, in `test_instance_block.py`.
> - **A-15**:
>   - la sonda dell'indirizzo `GET /auth/address-probe` nella docstring di `instance_block.py`, fra le rotte pubbliche
>     fuori dall'elenco: a istanza bloccata risponde 401 senza intestazioni CORS, e il controllo dell'admin la mostra
>     come non verificabile, come voluto da A6a;
>   - la sonda anche fra le letture pubbliche del test (`PUBLIC_READS_OUTSIDE_THE_LIST`), e in
>     `hosting_providers.en.md`. `security.md` la citava già, con A6a.
> - **Prove** (corsia 6181, una alla volta, con `nice`):
>   - `api instance-block` 54, `api system` 117;
>   - `utils dev-port-check` 5, `test-server-preparation` 63, `runtime-isolation` 195;
>   - `api sync`; `front check` 0/0; Vitest `InstanceBlockedPage` 22; `front build --debug`;
>   - E2E `files-uploader` 8/8, `header-scroll` 4/4;
>   - `check-orphans` pulito; `mkdocs build` stretto e `check-links`.
>
> **Fuori pista** (DV-1, girato dal coordinatore alle 17:38): la corsia toglie `LIBREFOLIO_REGEN_NATIVE_CASH_GUARD`, il
> comando documentato per rigenerare il golden di `test_native_cash_guard.py`. È un effetto di C-96, e l'unica variabile
> di rigenerazione del repo. Nel backlog come H-13, con la cura proposta: il prefisso `LIBREFOLIO_TEST_REGEN_*`.
>
> ✅ 15/10, sera: DV-1 chiusa da J in CP-4, con la variabile rinominata `LIBREFOLIO_TEST_REGEN_NATIVE_CASH_GUARD`
> (decisione del coordinatore). H-13 chiusa nel backlog.

### CP2b — il taglio di `main.py` (2026-10-15, sera) — in corso

> **Base**: `9c8ee20c3` (`dev_release2` `eacc34784` con i registri e Z7a, in avanzamento veloce). Worktree pulito, salvo
> le due righe di journal di H-13 e DV-1, che vanno nel commit di journal di CP2b.
>
> **Via del coordinatore**, con le decisioni 1–4 approvate:
>
> 1. niente commit di rinomina per `main.py`: solo il taglio, con la prova AST;
> 2. la scadenza dello spegnimento nasce in CP2b, spenta per default;
> 3. nel `finally` resta solo l'executor dei tool;
> 4. `main.py` congelato per le altre sessioni fino all'ingresso di CP2b.
>
> **Accordi diretti**, su indicazione del coordinatore:
>
> - **Z (Z6b)**:
>   - `Step(name, run, blocking=False)`; `run_shutdown_steps(steps, deadline)`, con la scadenza assoluta su
>     `time.monotonic()`, almeno `MIN_STEP_SECONDS` (0,2 s) per passo, gli esiti per passo; `current_step()`;
>   - il modulo di Z importa `lifecycle.py`, mai il contrario;
>   - Z aggiunge poi in `app_lifespan.py` il watchdog come primo passo d'avvio, la sua `shutdown_deadline()` e il passo dei
>     processi figli come ultimo dello spegnimento.
> - **B**:
>   - `pending-restore` fra `tool-catalog` e `data-directories`: prima di ogni passo che legge o scrive la cartella dati,
>     tranne `logs/` e `secrets/`;
>   - `restore-commit` fra `global-settings` e `provider-prewarm`;
>   - le due righe le aggiunge B con B3; per B nessun passo di spegnimento. All'avvio `blocking` non cambia niente.

#### Passo 1 — il taglio ✅ (2026-10-15, sera)

> **Note implementazione**: lo script `files/` della sessione ritaglia le definizioni da `main.py` per contenuto, non
> per numero di riga, e le porta così com'erano.
>
> - `main.py` passa da 527 a 63 righe: filtro degli avvisi, controllo della modalità di test, `settings`,
>   `configure_logging`, `app`, poi `install_middleware(app)`, il router e `install_static_site(app)`.
>   `backend.app.main:app` resta il punto d'ingresso di uvicorn.
> - `services/platform/lifecycle.py`, nuovo: la macchina dei passi, che non importa niente dell'app.
>   - `Step`, `StepOutcome`, `current_step()`, `run_startup_steps()`, `run_shutdown_steps(steps, deadline)`.
>   - Sotto una scadenza, il tempo di ogni passo è limitato da `asyncio.timeout`, e `expired()` distingue un passo
>     tagliato da un passo che solleva da sé un `TimeoutError`. Un `Task` atteso e tagliato viene cancellato.
> - `services/platform/app_lifespan.py`: `STARTUP_STEPS` (13 passi), `FINALLY_STEPS` (l'executor dei tool),
>   `SHUTDOWN_STEPS` (6), `shutdown_deadline()` che restituisce `None`, e `lifespan`.
>   - Ogni passo chiama la sua funzione con una lambda, risolta al momento della chiamata, così i `monkeypatch` sul
>     modulo funzionano.
>   - Lo stato dello scheduler passa dal passo d'avvio a quello di spegnimento in `_SchedulerRun`.
> - `services/platform/middleware.py`: `MIDDLEWARE_STACK`, la più esterna per prima (GZip, poi CORS), e
>   `install_middleware()`, che le aggiunge in ordine inverso: Starlette mette fuori l'ultima aggiunta.
> - `services/platform/static_site.py`: gli handler di MkDocs e della SPA così com'erano. `install_static_site()` li
>   registra nello stesso ordine: `/mkdocs`, `/mkdocs/{path}`, `/`, il mount `/_app` se c'è la build, il catch-all per
>   ultimo. `ImmutableStaticFiles` passa a livello di modulo.
> - `services/platform/database_bootstrap.py`: `ensure_database_exists()` e `run_post_migration_fixes_at_startup()`.
>   La head viene da `readiness.alembic_head_revision()`, l'unico lettore; l'avviso che il vecchio helper dava quando la
>   head non si legge resta, in `ensure_database_exists()`.
>
> **Prove** (`files/` della sessione: `snapshot_app.py`, `ast_compare.py`):
>
> - **Fotografia dell'app, prima e dopo**: tabella delle rotte (10 voci, in ordine), stack dei middleware con le
>   opzioni, sha256 dello schema OpenAPI (`621989381d73426d…`). Tutto identico.
> - **AST**: 17 definizioni spostate identiche, decoratori esclusi. `ensure_database_exists` differisce solo per la
>   lettura della head e il suo avviso.
> - **Chiamate del lifespan**: le stesse 35, nello stesso ordine, prima e dopo, con le funzioni-passo espanse.
> - Ogni modulo nuovo si importa da solo, senza `main`: niente cicli. `lifecycle` carica 9 moduli di `backend.app`.
> - `ruff` e `black` puliti sui sei file.
>
> **Cambio di comportamento dichiarato**: un passo di spegnimento che solleva va nel log in ERROR, con la traccia, e i
> passi dopo girano lo stesso. Prima, un'eccezione nel `finally` o nello spegnimento saltava il resto. Vale anche per
> lo scheduler: un task finito con un errore non ferma più lo spegnimento dei fornitori.

#### Passo 2 — i riferimenti fuori dai test e dalla doc MkDocs ✅ (2026-10-15, sera)

> **Note implementazione**:
>
> - `.github/instructions/backend.instructions.md`: nell'albero e nella mappa, i cinque moduli nuovi della piattaforma.
>   `backend-db.instructions.md`: la lettura della head è ora `readiness.alembic_head_revision()`, usata all'avvio e
>   da `/system/ready`.
> - Docstring e commenti: `db/post_migration/__init__.py` (il punto d'avvio), `test_db/db_schema_validate.py` (il
>   controllo della head), la stringa del runner per `utils static-route-confinement`, il commento del `Dockerfile`
>   sulle migrazioni all'avvio. Il `Dockerfile` è di B dopo CP7a: sono due righe di commento, da dichiarare.
> - Wiki: 14 righe in 9 pagine, solo dove una pagina cita in `main.py` una funzione spostata. Le citazioni che restano
>   vere (`backend.app.main:app`, il router montato in `main.py`, le pagine di storia) non cambiano.
>   `check_source_paths.py`: 5 percorsi inesistenti su 3 936, tutti artefatti generati preesistenti.
> - `lint --dead-code`: una sola voce nuova, `current_step` senza riferimenti. È l'aggancio del watchdog di Z6b: fino
>   ad allora lo usa solo il test puro.
>
> **Accordi**: a Z la firma definitiva e l'avviso sui thread tagliati, che restano vivi fino all'uscita (`asyncio.run`
> aspetta l'executor di default fino a 300 s). A B dove vanno i suoi due passi, e il fatto che `blocking` all'avvio non
> cambia niente.
>
> **In corso**: test-author (puntamenti dei test di A, X e J, del test di confinamento e di `test_db_config`; test
> puro `services app-lifecycle`), docs-writer (pagine MkDocs per sviluppatori).

#### Passo 3 — i test e la doc ✅ (2026-10-15, sera)

> **Note implementazione** (test-author, docs-writer):
>
> - **Test ripuntati**, nei file di altre sessioni, righe da dichiarare nel checkpoint:
>   - `test_db/test_post_migration.py` (A): 883-884, 887, 894, 897, 1086, 1089, 1097, 1099, 1114, 1138-1152,
>     1154-1157, 1169-1171, 1178-1179, 1182. `run_post_migration_fixes` si sostituisce in `database_bootstrap`, dove
>     l'aggancio lo cerca; le patch sul lifespan vanno su `app_lifespan`; tolti i `raising=False` sui bersagli di `main`.
>   - `test_services/test_market_calendar.py` (X): 530, 544-557, 559-560, 566-567, 585-590, 593.
>   - `test_services/test_signal_runtime.py` (J): 9, 11, 88-89, 92.
>   - `test_services/test_risk_scenario_catalog.py` (J): 12, 14 (tolta la vecchia 11), 211-216, 219.
>   - Miei: `test_static_route_confinement.py` (1, 23-26, 43, 95-96), `test_db_config.py:124`; solo docstring in
>     `test_config_audit.py:7`, `test_http_compression_api.py:1` e `:72`.
> - **Test nuovo** `test_services/test_app_lifecycle.py`, selettore `services app-lifecycle` (isolamento `pure`), 38 casi:
>   - il runner: ordine, attese, tagli, cancellazione del `Task`, errori che non fermano lo spegnimento, thread dei
>     passi `blocking`, `current_step()`, log con `capture_logs`;
>   - il cablaggio: ordine di oggi come **sottosequenza** (`assert_in_relative_order`, `CORE_STARTUP_ORDER`,
>     `CORE_SHUTDOWN_ORDER`, riusabili da B e Z), nomi unici anche fra `FINALLY_STEPS` e `SHUTDOWN_STEPS`, binding
>     tardivo;
>   - lo stack dei middleware; l'ordine delle rotte statiche, con il catch-all ultimo anche sull'app vera.
> - **Doc** (docs-writer), 10 pagine per sviluppatori, nessuna con traduzioni. La pagina principale è `overview.md`, con
>   la sottosezione nuova «Steps and Middleware: the Contract» `{: #lifecycle-contract }`.
>
> **Fuori pista**:
>
> - Segnalato da test-author: un passo `blocking` che restituisce un awaitable, sotto scadenza, non veniva atteso.
>   Corretto nel runner: ciò che `run()` restituisce si attende sempre. Un caso nuovo lo fissa, con un canarino che
>   prova che l'avviso «never awaited» si vede.
> - La nota «Pre-warm» di `provider_justetf.md` era falsa già prima: il prewarm crea solo i fornitori, e la lista degli
>   ETF arriva alla prima ricerca. Corretta invece di spostarla (docs-writer, verificato su `plugin.py:161-168, 448`).
> - `test_db_config.initialize_test_database()` non importa più `main`, quindi non ne subisce gli effetti all'import.
>   Il commento del file chiedeva proprio questo. Effetto visibile: `db populate` non configura il logging dell'app,
>   quindi niente righe INFO del bootstrap del DB in console e nel file di log della corsia; gli avvisi restano.
> - I log dell'avvio e dello spegnimento hanno un logger nuovo (`…platform.app_lifespan`, `…database_bootstrap`).
>   Nessun filtro del repo usa il vecchio nome.
> - `coverage_analysis.py`: i quattro moduli usciti da `main.py` sono `INFRA` come lui; `lifecycle.py` no, perché è
>   coperto dal test puro.
> - `black` segnala `_backend_services.py` e `_backend_utils.py` già alla base, su righe di altri. Non li riformatto.

#### Passo 4 — le prove leggere ✅ (2026-10-15, sera)

> Corsia 6181, una alla volta, con `nice -n 10`; log in `/tmp/librefolio-r13-h-cp2b/`:
>
> - `services app-lifecycle` 38; `db post-migration` 41; `services signal-runtime` 6;
>   `utils static-route-confinement` 26; `services risk-all` filtrato su market-calendar e risk-scenario-catalog 48;
> - `services asset-source-refresh` 12, `asset-sync-counts` 1, `scheduled-investment-param-change` 3: le tre che
>   passano da `initialize_test_database()`; poi `db populate --force`;
> - `api instance-block` 54, `api system` 117, `api http-compression` 10. Nel log del server condiviso, gli avvii e gli
>   spegnimenti passano dai moduli nuovi, senza passi falliti né tagliati;
> - `utils runtime-isolation` 195;
> - E2E `front-utility app-start-auth` 3, `files-pdf-offline` 1, `docs-offline-math` 2;
> - `mkdocs build --strict`, `check-links` (95 link), `check-orphans` puliti; `git diff --check` pulito;
> - grep dei vecchi percorsi a zero; fotografia dell'app ancora identica alla base.
>
> **Prossimo**: `all-backend` nello slot pesante, poi l'handoff FROZEN.

#### Passo 5 — `all-backend` e il caso del watchdog ✅ (2026-10-15, sera)

> - **`all-backend`** (slot pesante 1, 19:06–19:37, `-q --fresh-run --workers 2`, `nice -n 10`, corsia 6181): 7/7,
>   **14 367 passed, 3 skipped, 0 failed**. Comprende i 38 casi di `services app-lifecycle` di quel momento.
> - **Fuori pista** (domanda di Z alle 19:21): il passo d'avvio del watchdog restituisce l'oggetto watchdog o `None`,
>   cioè un valore non attendibile. Il runner lo ignora già, perché attende solo ciò che è awaitable, ma nessun caso lo
>   fissava. test-author lo aggiunge estendendo due test, senza funzioni nuove: un passo `"value"` all'avvio, e
>   `None` o un valore qualunque allo spegnimento, con e senza scadenza, `blocking` o no. Dopo `all-backend`,
>   `services app-lifecycle` dà **43 passed**.
> - `ruff` pulito; `black` segnala solo righe preesistenti di altri (`_backend_services.py`, `_backend_utils.py`,
>   `coverage_analysis.py`), già rosse alla base; `git diff --check` pulito. La porta 6181 è libera.
> - `lint --dead-code`: gli «Unreferenced» restano i 5 della base; `current_step` è fra i «referenziati solo dai
>   test» (42, prima 41) finché il watchdog di Z6b non lo usa.

### Checkpoint CP2b 🧊 (2026-10-15, sera) — FROZEN, in attesa del coordinatore

> **Committato** dal coordinatore: `956789beb` (taglio), `3acb28896` (doc), `6ad489f86` (journal).

#### Aggiornamento di base prima dell'ingresso ✅ (2026-10-15, sera)

> **Merge** di `dev_release2` `00aa2ab3c` (E2, B, J CP-4, Z6b parte 1, W E1b e N2, Y2, L), con due conflitti:
>
> - `.github/instructions/backend.instructions.md`: nell'albero, una riga sola con i due lati; nella mappa, la mia riga
>   sui passi d'avvio più la riga «Platform services» del lato `dev_release2` (`series_export.py`, `instance_backup/`);
> - `scripts/test_runner/_backend_services.py`: `services_app_lifecycle` e le due di B (`backup_archive`,
>   `backup_jobs`). Le registrazioni sono 110, senza nomi doppi.
>
> **Controlli di significato**:
>
> - il merge non tocca `main.py` né i moduli di CP2b;
> - `shutdown_budget.py` di Z legge `current_step` in modo pigro e ora trova il modulo: `services shutdown-budget` 178;
> - `config_audit.py` ha `*EMAIL_CONFIG_CHECKS` di E, e `test_config_audit.py` le righe di E con la mia docstring;
> - il `Dockerfile` non cambia; i riferimenti a `backend.app.main` prendono solo `app`.
>
> **Prove** (corsia 6181, una alla volta): `services app-lifecycle` 43, `shutdown-budget` 178, `db post-migration` 41;
> `db populate --force`; `api system` 117, `instance-block` 56, `backup` 23; `utils runtime-isolation` 195,
> `test-server-preparation` 63; `check-orphans`; E2E `app-start-auth` 3.
>
> **Ingresso**: `dev_release2` = `4fb017a9a` (merge `7fa313269`), CHANGELOG `9b82187f6` con la riga 🐛 sullo
> spegnimento e la 🔄 sui logger. Il mio ramo è avanzato a `9b82187f6`. `main.py` è scongelato. Lo SHA a Z e a B lo
> manda il coordinatore.

### Lotto «scopo dei file caricati» (decisione 36) — analisi (2026-10-15, sera) — FROZEN

> **Base**: `9b82187f6`. Decisione 36 del developer: i file comuni (icone, loghi, foto degli asset, risorse statiche)
> li vede ogni utente con il login; i file personali solo chi li ha caricati e l'admin (elenco, anteprima, scarico).
> Un file caricato da un selettore d'immagine è comune; dalla pagina File è personale, con un interruttore per
> condividerlo. I file già caricati: le immagini diventano comuni, gli altri personali. I file dei broker sono di W.
>
> **Stato reale**:
>
> - Per gli upload non c'è una tabella: ogni file è `<data>/custom-uploads/<uuid><ext>` con i metadati in un file JSON
>   accanto (`services/files/static_uploads.py`). Nei metadati non c'è uno scopo. Il modello d'accesso di oggi non
>   distingue i file: l'elenco e la lettura sono per tutti gli utenti con il login; la cancellazione è del proprietario
>   o dell'admin.
> - Il frontend ha un solo client di caricamento, `lib/utils/files/upload.ts` (`uploadFile`), senza scopo. La pagina
>   File ha le schede «static» e «brim». I selettori d'immagine passano da `ImagePickerWrapper` e `AssetPickerModal`
>   (`AssetModal`, `BrokerForm`, `ProfileTab`, `WelcomePage`). Ritaglio e rinomina caricano un file nuovo.
> - Gli avatar di default hanno `uploaded_by_user_id` 0, cioè il sistema.
>
> **Proposta**:
>
> 1. Un campo `scope` (`common` o `personal`) nei metadati. Quando manca vale la regola d'eredità, calcolata alla
>    lettura: `image/*` è comune, il resto personale. I file esistenti si classificano così senza scrivere niente.
> 2. `POST /uploads` accetta `scope` facoltativo; senza, la stessa regola. I selettori mandano `common`, la pagina File
>    `personal`.
> 3. Elenco: i comuni più i propri personali; l'admin vede tutto, con il proprietario. Lettura, anteprima e scarico di
>    un file personale altrui rispondono 404, admin escluso. I file del sistema sono comuni.
> 4. `PATCH /uploads/{id}` con `{scope}`, per il proprietario o l'admin: è l'interruttore della pagina File.
> 5. Ritaglio e rinomina tengono lo scopo dell'originale.
> 6. `can_delete` per voce nell'elenco; la tabella nasconde «elimina» quando vale false.
> 7. Gli handler toccati rispettano la regola dell'I/O asincrono (`def` o `asyncio.to_thread`).
>
> **Accordo con W** (15/10, sera):
>
> - W aggiunge `can_delete` a ogni voce di `GET /brokers/brim/files`; io cablo la tabella per le due schede;
> - i report senza broker seguono la regola dei personali (chi li ha caricati e l'admin);
> - codici diversi, scelti apposta: `/uploads` 404, i report BRIM 403 (già fissato dai test di W);
> - `file_preview.py` resta comune e puro; la pagina File e i componenti condivisi sono miei.
>
> **Decisioni aperte**: D36-1, un'immagine personale scelta in un selettore per un oggetto condiviso (asset, broker)
> diventa comune con un avviso, oppure il selettore mostra solo le comuni; D36-2, regola d'eredità letta al volo
> (proposta) o correzione dopo le migrazioni che scrive il campo; D36-3, 404 per il file personale altrui (proposta).

> **Via del developer** (15/10, 20:0x, inoltrato dal coordinatore alla lettera): «Approvo le tre proposte».
>
> - D36-1: un'immagine personale scelta per un oggetto condiviso diventa comune, con un avviso.
> - D36-2: la regola d'eredità letta al volo, senza migrazione.
> - D36-3: 404 per il file personale di un altro utente.
>
> **Condizioni del coordinatore**: due checkpoint, prima backend e test, poi frontend; prima i rossi; la correzione
> dell'I/O asincrono entra nel lotto, dichiarata; in `ProfileTab` (di A) cambia solo lo scopo nel caricamento, una riga
> dichiarata; la pagina File e `FilesTable` sono miei, d'accordo con W; revisione di sicurezza mirata prima del secondo
> checkpoint; le prove pesanti si chiedono.

#### CP-U1 — backend e test: il contratto (2026-10-15, sera) — in corso

> **Regola dello scopo** (`static_uploads.py`):
>
> - `effective_scope(metadata)`: vince lo `scope` salvato, se è `common` o `personal`. Altrimenti si applica la regola
>   d'eredità: i file del sistema (id 0) sono comuni, `image/*` è comune, il resto personale.
> - Un caricamento con `scope` lo salva com'è. Senza, salva lo scopo risolto dalla regola: il dato resta esplicito.
> - `UploadFileInfo` porta sempre `scope`, quello effettivo, e `can_delete`, calcolato per chi chiede.
>
> **Accesso** (`uploads.py`), per il proprietario, un altro utente e l'admin:
>
> - Elenco: i comuni di tutti più i propri personali; l'admin vede tutto. `my_files_only` resta: solo i propri.
> - Info, anteprima e `/file/{id}` (scarico, anteprima d'immagine e di testo): un file personale altrui risponde 404,
>   identico a un file che non c'è. Il controllo viene prima della cache delle miniature.
> - `DELETE` e il nuovo `PATCH /uploads/{id}` `{scope}`: il proprietario o l'admin. Un altro utente riceve 403 su un
>   file comune, 404 su uno personale.
> - Le miniature escono con `Cache-Control: private, max-age=3600`, non più `public`: sono contenuti dietro login, e
>   una cache condivisa davanti all'istanza non deve servirle ad altri.
>
> **Coerenza fra processi** (`dev.py server --workers N`): la cache dei metadati, per processo e di un'ora, si convalida
> con l'inode, l'mtime e la dimensione del file JSON. Un cambio di scopo fatto da un altro worker si vede subito. I
> metadati si scrivono in modo atomico (file temporaneo, poi `os.replace`).
>
> **I/O asincrono**: gli handler toccati chiamano le funzioni sincrone del servizio con `asyncio.to_thread`.

##### Passo 1 — i rossi ✅ (2026-10-15, sera)

> test-author, sul codice di prima, una prova alla volta (log in `/tmp/librefolio-r13-h-u1/`):
>
> - `services static-uploads`: 70, di cui 32 rossi nuovi. Le cause: `effective_scope` e `set_upload_scope` che
>   mancano, `scope` né salvato né restituito, la cache servita dopo che il file è cambiato o sparito.
> - `api uploads`: 40, di cui 13 rossi nuovi: elenco e lettura dei personali altrui, 422 mancanti, `PATCH` 405, campi
>   assenti. SCOPE-DEL-1 è verde di proposito (guardia), UPLOAD-013 era già saltato.
> - `api uploads-serve-file`: 12, di cui 4 rossi: i personali altrui serviti in sei modi, anche dalla cache delle
>   miniature, e `public` nel `Cache-Control`. SCOPE-SERVE-2 è verde di proposito (guardia).
> - Test esistenti cambiati: la fixture di `test_static_uploads.py` non svuota più la `custom-uploads/` condivisa della
>   corsia, ma usa `tmp_path`; il test che fissava la cache servita dopo la cancellazione è sostituito; UPLOAD-008 carica
>   il file come `common`; G7§2.4 chiede `private`.
>
> **Fuori pista**: test-author ha segnalato i test che la cura avrebbe rotto fuori dal contratto
> (`TestServeFileOffEventLoop`, UPLOAD-U1/U2, `test_served_content_types.py`, CAPI-008) e l'ordine dei controlli: lo
> scopo va prima dei 400 sul tipo. Riparazioni e casi in più nel passo 3.

##### Passo 2 — la cura ✅ (2026-10-15, sera; senza prove, pausa della macchina)

> **Note implementazione**:
>
> - `schemas/uploads.py`: `UploadScope`; `UploadFileInfo.scope` obbligatorio e `can_delete` (default false);
>   `UploadUpdateRequest`.
> - `static_uploads.py`: `effective_scope`, `can_view_upload`, `can_manage_upload`, `set_upload_scope`,
>   `save_upload(scope=…)`. La cache tiene `(timbro, metadati)` e il timbro si controlla a ogni lettura. La scrittura è
>   atomica: `mkstemp`, poi `os.replace`; il timbro si prende con `fstat` prima della rinomina, così il file messo da
>   un altro worker non lo eguaglia mai.
> - `api/v1/uploads.py`: `_visible_upload` per prima in info, anteprima, `/file`, cancellazione e `PATCH`; `_for_user`
>   imposta `can_delete`; `scope` nel `POST` validato da FastAPI (422); il lavoro su disco va in `asyncio.to_thread`;
>   miniature `private, max-age=3600`.
> - OpenAPI: `PATCH /uploads/{file_id}`; `scope` obbligatorio nelle risposte, `can_delete` no, per via del default.
>   Quindi le risposte finte senza `scope` nelle E2E e nei Vitest vanno aggiornate (passo 3).
>
> **Fuori pista** (docs-writer, 15/10 sera): un `PATCH` in contemporanea con un `DELETE` dello stesso file poteva
> riscrivere il sidecar dopo la cancellazione. `set_upload_scope` ora ricontrolla il contenuto dopo la scrittura e, se
> è sparito, toglie il sidecar e risponde «non trovato». Doc per sviluppatori: `security.md` (sottosezione
> `#upload-scope`), `file-upload.md`, una cella di `database/index.md`. Le tre frasi della pagina utente dei File che
> CP-U1 rende false (`user/files/index.en.md` righe 5, 16, 100) si correggono con CP-U2, insieme all'interfaccia.

### Voci di backlog da X CP10 (2026-10-15, sera)

> Il coordinatore ha girato tre richieste di X (CP10, impostazioni dei plugin), da fare fuori dal lotto 36:
>
> - **H-14**: `derive_key_from(key, purpose)` in `instance_key.py`, per il ripristino di B, che deve cifrare di nuovo i
>   segreti dei plugin con la chiave dell'istanza che ripristina.
> - **H-15**: un controllo d'avvio in `config_audit.py` che usa `plugin_secrets_key_status` di X; con una chiave
>   inutilizzabile restituisce i totali, e gira in `to_thread`.
> - **H-16**: due frasi di `developer/architecture/security.md` superate: l'elenco dei segreti letti con `env_secret()`
>   senza `LIBREFOLIO_PLUGIN_*`, e la «known limitation» che chiama «planned» un controllo che il `key_id` rende
>   possibile.
>
> H-10 è chiusa dal lotto 36: la fixture di `test_static_uploads.py` non svuota più la cartella della corsia.

##### Passo 3 — riparazioni, casi in più e prove ✅ (2026-10-15, sera)

> **Note implementazione** (test-author):
>
> - riparati sui nomi nuovi i test che la cura rompeva fuori dal contratto: `TestServeFileOffEventLoop` (2),
>   UPLOAD-U1/U2, UPLOAD-005G, la fixture di `test_served_content_types.py` (ora un file e un sidecar veri sotto
>   `tmp_path`);
> - casi nuovi: SCOPE-SERVE-5, cioè i modi che non c'entrano col tipo, che per B danno il 404 del file mancante, mai
>   un 400; UPLOAD-U4/U5/U6, una spia che `list_files`, `get_file_info` e `upload_file` lavorano fuori dal ciclo di
>   eventi; la corsa fra `set_upload_scope` e una cancellazione (2 casi);
> - fixture del frontend con `scope`: `e2e/files-uploader.spec.ts`, `FilesTable.test.ts`, `AssetPickerModal.test.ts`;
> - il commento del runner per `served-content-types`.
>
> **Prove** (corsia 6181, una alla volta, `nice -n 10`, carico sotto 70; log in `/tmp/librefolio-r13-h-u1/`):
>
> - `services static-uploads` 72; `api uploads` 42 + 1 saltato (UPLOAD-013, già prima); `api uploads-serve-file` 13;
>   `api preview-cache` 15; `utils served-content-types` 36; `api cache-admin` 8 (CAPI-008 compreso);
> - `api sync`: `scope` obbligatorio e `can_delete` facoltativo nel client generato; `front check` 0 errori, 0 avvisi;
>   Vitest `FilesTable`, `AssetPickerModal`, `FilePreviewModal` 74;
> - E2E `front-utility files-uploader` 8, `files` 28, `files-destructive` 6, `files-pdf-offline` 1;
> - `mkdocs build --strict` e `check-links` (96) puliti.
>
> **Fuori pista**: il primo giro della revisione di sicurezza è fallito per un errore d'infrastruttura («requested model
> is not supported»), non sul merito: rilanciata.

##### Passo 4 — la revisione di sicurezza mirata (2026-10-15, sera)

> **Fuori pista**: l'agente `security-review` è fallito due volte per lo stesso errore d'infrastruttura. Ho fatto io la
> revisione mirata, sui punti del brief. Gli esiti stanno solo nei messaggi al coordinatore.
>
> - Correzione: un id che il filesystem non sa nominare faceva sollevare `ValueError` a `stat()` e dava un 500; ora
>   conta come file mancante, come prima del lotto. test-author aggiunge i due casi.
> - Controllati e a posto: le altre vie verso `custom-uploads/` (il seed degli avatar; il backup, solo admin);
>   l'ordine dei controlli; le chiavi delle cache; la convalida del corpo del `PATCH` e del campo del `POST`; la regola
>   dello scopo; il timbro e la scrittura atomica; il `SameSite=lax` del cookie davanti al nuovo `PATCH`.
> - Casi della correzione (test-author): `services static-uploads` 73, `api uploads` 43 + 1 saltato (UPLOAD-NUL-1).

##### Passo 5 — `all-backend` ✅ (2026-10-15, sera)

> Slot pesante 1, 22:16–22:42 (`-q --fresh-run --workers 2`, `nice -n 10`, corsia 6181): 7/7, **15 181 passed,
> 4 skipped, 0 failed**. I quattro saltati sono i tre di sempre più UPLOAD-013, che saltava già prima del lotto. La
> porta 6181 è libera, `git diff --check` pulito.

#### Checkpoint CP-U1 🧊 (2026-10-15, sera) — FROZEN, in attesa del coordinatore

> **Committato** dal coordinatore: `b9383ecfb` (feat), `ad1aa04bb` (doc), `df672a841` (journal); merge di
> `dev_release2` `45499dec4` pulito, HEAD `57d401a16`. CP-U1 entra da solo, scelta del coordinatore: chiude un buco
> d'accesso, e un treno piccolo rischia meno. La pagina utente dei File si sistema con CP-U2, segnata fra le cose da
> chiudere prima del rilascio.
>
> **Prove d'ingresso** sulla revisione combinata: `api sync`; `front check` 0/0; `db populate --force`; `api uploads`
> 43 + 1 saltato; E2E `files-uploader` 8, `files` 28; Vitest `FilesTable` e `AssetPickerModal` 37.
>
> **Fuori pista**: `api sync` e `front check` sono partite con il carico a 106, sopra la soglia di 70: il carico lo
> stampavo senza usarlo come soglia. Dalle prove successive un ciclo aspetta che scenda sotto 70 prima di ogni lancio.

> **Ingresso**: CP-U1 è in `dev_release2` (treno 66, merge `6a3a2a1cc`, registri `84a18fb4c`), con 2 righe 🔄 e 1 🔒
> nel CHANGELOG. La pagina utente dei File è condizione per il rilascio, e si chiude con CP-U2.

#### CP-U2 — frontend: il contratto (2026-10-15, notte) — in corso

> **Base**: `57d401a16`. L'aggiornamento con T+DV, la palette nuova, lo fa il coordinatore al prossimo checkpoint.
>
> - **Client** (`lib/utils/files/upload.ts`): `uploadFile(file, description?, scope?)` manda `scope` quando c'è;
>   `setUploadScope(fileId, scope)` chiama `PATCH /uploads/{id}` e restituisce il file aggiornato.
>   `UploadScope` in `lib/types/files.ts`.
> - **Chi carica con quale scopo**: la pagina File `personal`; `ImageEditModal` ha la prop `scope`, con default
>   `common` per i selettori d'immagine, e la pagina File gli passa lo scopo del file che modifica; `FileEditModal`,
>   il rinomina della pagina File, tiene lo scopo dell'originale. `ProfileTab` (di A) non cambia: l'avatar passa da
>   `ImageEditModal`, quindi è `common`.
> - **Pagina File**:
>   - in `FilesTable`, scheda static: colonna `scope` con un badge (condiviso `info`, personale `default`) e un filtro;
>     azioni di riga «Condividi con tutti» e «Rendi personale», visibili solo con `can_delete`; «elimina» nascosta
>     quando `can_delete` è falso, in tutte e due le schede;
>   - in `FileGrid`, vista a griglia: lo stesso interruttore fra le azioni della scheda, e «elimina» nascosta come
>     sopra;
>   - «Rendi personale» chiede conferma con `ConfirmModal`, perché gli altri perdono l'accesso, anche dove il file fa
>     da icona o da foto. «Condividi» no;
>   - eventi `file.scope.changed` e `file.scope.change.failed`, con un toast;
>   - la cancellazione multipla salta i file non cancellabili, con un avviso, invece di fermarsi al primo 403.
> - **Selettore** (`AssetPickerModal`, D36-1): la scheda «esistenti» mostra i comuni più i miei. Un mio file
>   personale scelto per un oggetto condiviso diventa comune con `setUploadScope`, con un avviso (evento
>   `file.scope.shared-on-pick`); se il cambio fallisce, niente selezione e un errore.
> - **Colori**: badge e pulsanti riusano la cella `badge` della tabella e le classi `.action-btn` della griglia:
>   nessuna classe di colore nuova.
>
> **Decisioni notturne, da rivedere**: l'interruttore è un'azione di riga e un pulsante della scheda, non uno switch
> in colonna; la conferma solo per «Rendi personale»; nella griglia nessun badge, perché lo scopo si legge
> dall'azione e dalla vista a elenco.
>
> **Correzione del contratto** (dalla lettura della pagina): nella pagina File, `ImageEditModal` e `FileEditModal`
> lavorano su file nuovi, prima o durante il caricamento, non su file già caricati. La pagina passa quindi `personal`,
> non lo scopo di un file esistente. Il contratto dei due modali resta: `scope` con default `common`, che arriva a
> `uploadFile`. In più, il filtro URL `scope` vale anche nella vista a griglia (`urlFilterColumns`,
> `staticGridColumns`).

##### Passo 1 — i rossi ✅ (2026-10-15, notte)

> test-author, sul codice di prima: 92 Vitest in 6 file, 27 rossi nuovi per il motivo atteso, gli esistenti verdi.
> Nuovi `FileGrid.test.ts`, registrato nel runner, e `__tests__/harness/ImageCropperStub.svelte`. Lo scenario E2E in
> `files.spec.ts` è scritto ma non lanciato. Nessun aggancio nuovo nei componenti: le celle hanno già `data-column-id`
> e il badge `data-badge-variant`.

##### Passo 2 — la cura ✅ (2026-10-15, notte)

> **Note implementazione**:
>
> - `upload.ts`: `uploadFile(…, scope)`, `setUploadScope`; `UploadScope` in `lib/types/files.ts`.
> - `FilesTable`: colonna `scope` (badge `info` per i comuni, `default` per i personali; filtro), azioni `share` e
>   `makePersonal`, «elimina» con `visible` su `can_delete`. `FileGrid`: pulsanti `file-grid-scope-<id>` e
>   `file-grid-delete-<id>`.
> - Pagina File: caricamenti `personal`, anche dai due modali; `ConfirmModal` `files-scope-confirm` per «Rendi
>   personale»; eventi `file.scope.changed`, `file.scope.change.failed` e `file.delete.skipped`; filtro URL `scope`
>   anche in griglia.
> - `AssetPickerModal`: i comuni più i miei; una mia immagine personale diventa comune prima della selezione
>   (`file.scope.shared-on-pick`), e se il cambio fallisce non seleziona niente.
> - i18n: 12 chiavi `uploads.scope.*` nelle 4 lingue, nel sottosistema `files`.
>
> **Fuori pista**: test-author ha visto che il selettore ricaricava l'elenco a ciclo quando il risultato era vuoto: la
> condizione reattiva dipendeva da `existingFiles`, che ogni caricamento riassegna. C'era già prima del lotto, ma il
> filtro nuovo rende vuoti più elenchi. Ora l'elenco si carica una volta per apertura, con il flag `existingLoaded`, e
> un caso Vitest lo fissa.
>
> **Prove**: Vitest dei 6 file 93; `i18n check` (4645 chiavi, rigoroso); il cancello dei colori pulito; `front check`
> 0/0. Le E2E (`files`, `files-uploader`, `files-destructive`, `files-pdf-offline`, `image-crop`) aspettano la fine della
> finestra tranquilla delle 00:00–01:15.

##### Passo 3 — doc e ritocchi ✅ (2026-10-16, notte)

> **Note implementazione** (docs-writer):
>
> - utente: `user/files/index.en.md`, condizione per il rilascio (le tre frasi false, la sezione nuova
>   `{: #visibility }`, i caricamenti personali, «elimina» solo dove si può); `user/misc/image-crop.en.md`;
>   `user/settings/profile.en.md`. Debito di traduzione dichiarato: le tre pagine in it/fr/es restano indietro, e
>   devono tenere l'ancora `#visibility`;
> - sviluppatori: `core-ui/file-upload.md` (la sezione nuova `#scope-flow`, gli eventi, il percorso giusto di
>   `upload.ts`), `features/brokers/modals.md`, `features/import-wizard.md`, `pages/index.md`.
>
> **Fuori pista** (dalle note di docs-writer):
>
> - l'avviso della cancellazione multipla vale anche per i report BRIM, dove i file saltati possono essere tuoi, per
>   esempio dopo il passaggio da Editor a Viewer: la chiave diventa `uploads.deleteSkipped`, con un testo generico;
> - «solo a te e agli amministratori» era falso quando un admin rende personale il file di un altro: il toast e il
>   suggerimento della colonna ora dicono «chi l'ha caricato e gli amministratori»;
> - corretti i commenti delle prop `scope` dei due modali: la pagina File passa `personal`;
> - segnalata a W l'incoerenza della cancellazione multipla del suo `BrokerImportFilesModal`, file suo;
> - limite noto, non coperto: incollare nella scheda URL del selettore l'indirizzo di un proprio file personale non lo
>   condivide;
> - le schermate della galleria `files/static-tab` e `files/static-grid` vanno rigenerate: c'è la colonna nuova.
>
> **Prove**: `i18n check`, `front check` 0/0, Prettier pulito. Restano le E2E e `mkdocs build --strict`, dopo la
> finestra tranquilla.

> **Prove leggere finite** (richiesta del coordinatore, 00:02): Vitest dei 6 file 93; `front-utility core-unit` 158 file
> e 5 255 test, cataloghi e cancelli dei colori compresi; `theme-roles --check` pulito; `i18n check`; `front check` 0/0.

### CP7b — analisi (2026-10-16, notte) — sola lettura

> **Stato reale** (base `57d401a16`):
>
> - **F28**: `ImmutableStaticFiles` (`static_site.py:100-104`) mette `public, max-age=31536000, immutable` su tutto
>   `/_app`, anche su `env.js` e `version.json`, che non hanno l'hash nel nome. Nessun codice legge `version.json` e
>   non c'è un service worker: l'impatto oggi è basso.
> - **F15**: nessun `Referrer-Policy`, `X-Frame-Options` o CSP; `nosniff` solo su due risposte di testo. L'unico
>   iframe è il PDF di `FilePreviewModal`, sulla stessa origine. In `app.html` ci sono uno script inline (anti-FOUC) e
>   uno `style=` inline.
> - **F27/D5**: `LIBREFOLIO_PROFILE` esiste, ma non c'è un meccanismo di default del profilo. L'inattività dei
>   worker di rischio è a 600 s.
> - **Spegnimento**: nessuno `stop_grace_period` nei compose. Il budget predefinito di 8 s sta nei 10 s di
>   `docker stop`, e `configuration.en.md` (righe 362-374, di Z) spiega già quando alzare lo `stop_grace_period`.
>   I compose sono di B da CP7a.
> - **Note di X**: non c'è `derive_key_from`; `plugin_secrets_key_status` è asincrona e vuole una sessione del DB,
>   quindi non può stare fra i controlli di `config_audit`, che girano prima del passo `database`; `security.md`,
>   righe 169-171 e 286-288, è superata dal `key_id`.
>
> **Proposta**, in due checkpoint:
>
> - **CP7b-1**, le intestazioni e la cache:
>   - F28: `immutable` solo sotto `_app/immutable/`, `no-cache` per il resto di `/_app`;
>   - F15, sempre (D5): un middleware ASGI `security_headers` in `MIDDLEWARE_STACK`, dopo l'`activity` di Z e prima
>     di `gzip`. Mette `X-Content-Type-Options: nosniff` e `Referrer-Policy: strict-origin-when-cross-origin`, senza
>     sovrascrivere un header già messo da una rotta;
>   - la guardia: `utils served-content-types` esteso a ogni estensione della build e della doc (`.mjs`, `.wasm`,
>     `.woff2`…), perché con `nosniff` un tipo MIME sbagliato blocca il file; le E2E della PWA, del PDF e della doc.
> - **CP7b-2**, il profilo gestito:
>   - un meccanismo generico `PROFILE_DEFAULTS` in `config/` (un default del profilo vale solo per un campo non
>     impostato, `model_fields_set`), con un test «self-hosted invariato» per ogni campo;
>   - F27: inattività dei worker di rischio a 60 s in `managed`;
>   - F15 in `managed` (D5): `X-Frame-Options: SAMEORIGIN`, `Content-Security-Policy: frame-ancestors 'self'`
>     (applicata: tocca solo l'incorniciamento) e una `Content-Security-Policy-Report-Only` completa sull'HTML della
>     SPA, non su `/mkdocs`. Lo script inline di `app.html` verrà segnalato finché il lotto A dei colori non lo sposta;
>   - doc admin (`hosting_providers`, `configuration`, `.env.example`), doc per sviluppatori (`security.md`).
> - **Le note di X** (H-14, H-15, H-16), un lotto piccolo a parte o in coda a CP7b-2:
>   - `derive_key_from(key, purpose, length)`, con `derive_key` che la chiama;
>   - un passo d'avvio `plugin-secrets-check` dopo `global-settings`, cioè a DB pronto: un ERROR con i totali, senza
>     valori. In più la voce per la scheda «Sicurezza» di A, se il suo registro accetta un controllo asincrono;
>   - le due frasi di `security.md`.
>
> **Via del coordinatore** (16/10, 00:09): CP7b approvato, nell'ordine CP7b-1, CP7b-2, poi le note di X. Nel worktree,
> finché CP-U2 non è committato, solo i rossi di CP7b-1, in file di test backend nuovi, scritti e non lanciati. Per
> H-15, il controllo asincrono nella scheda «Sicurezza» si accorda con A e X passando dal coordinatore.
>
> **Decisioni notturne, da rivedere**:
>
> - la CSP in sola segnalazione esce senza endpoint di report: le violazioni finiscono nella console del browser. Un
>   endpoint `/system/csp-report`, con un limite, eventualmente dopo;
> - lo `stop_grace_period` dei compose resta a B, che ne è il proprietario dopo CP7a: al più un commento che rimanda
>   al budget. Glielo comunica il coordinatore.

#### CP7b-1 — i rossi scritti (2026-10-16, notte) — non lanciati, CP-U2 ancora aperto

> test-author: tre file nuovi, puri, registrati in aggiunta; scritti senza lanciarli.
>
> - `test_services/test_static_cache_policy.py` (`services static-cache-policy`): 26 casi, 12 rossi previsti, cioè
>   `env.js`, `version.json` e `immutable.json` sotto `/_app`, e le loro risposte 304.
> - `test_services/test_security_headers.py` (`services security-headers`): 15, tutti rossi finché il modulo
>   `platform/security_headers.py` non esiste.
> - `test_utilities/test_nosniff_content_types.py` (`utils nosniff-content-types`): 30, di cui 8 rossi su questo Mac.
>
> **Da sapere per la cura**:
>
> - `.map` non ha un tipo nella tabella di Python né in quella del sistema; i font (`.woff`, `.woff2`, `.ttf`) li dà
>   solo `/etc/mime.types`, che l'immagine `python:3.13-slim` probabilmente non ha. Con `nosniff` il browser li
>   rifiuterebbe. Cura: l'app registra da sé i tipi che mancano (`mimetypes.add_type`), così i test passano su ogni
>   macchina;
> - il 500 di Starlette nasce in `ServerErrorMiddleware`, fuori dalla pila: `security_headers` deve mandare da sé il
>   500 con le intestazioni, se la risposta non è ancora partita, e poi rilanciare l'eccezione, che così resta nel log;
> - un inizio di risposta senza la chiave `headers` va gestito;
> - due test di `test_app_lifecycle.py` fissano la pila esatta: li porta Z all'ordine relativo nel suo commit; se
>   CP7b-1 entra prima, li cambio io, dichiarati.
>
> **Correzione dell'analisi**: un service worker c'è, `frontend/static/sw.js`, ma dà solo la pagina offline e non mette
> in cache `/_app`: F28 non cambia.

#### CP7b-1 pronto e CP7b-2 in preparazione (2026-10-16, notte) — fuori dal worktree

> **CP7b-1** è in `/tmp/librefolio-r13-h-7b1/`, non applicato: il modulo `security_headers.py`, lo script
> `apply_cp7b1.py` provato a secco su copie dei file, e il `README.md` con le prove, la doc e il CHANGELOG. I tipi MIME
> che mancano li registra l'app (`register_served_types()`, chiamata da `install_static_site`); il middleware manda da
> sé il 500 con gli header.
>
> **CP7b-2**: test-author scrive i rossi in `/tmp/librefolio-r13-h-7b2/`, senza applicarli né lanciarli.
>
> **Decisioni notturne, da rivedere** (dentro D5):
>
> - il meccanismo `PROFILE_DEFAULTS` sta in `config/__init__.py`: un validatore di `Settings` applica il valore del
>   profilo solo ai campi non impostati, né dall'ambiente né da `.env`;
> - due variabili invece di una: `LIBREFOLIO_FRAME_PROTECTION` (`X-Frame-Options: SAMEORIGIN` e la CSP applicata
>   `frame-ancestors 'self'`) e `LIBREFOLIO_CSP_REPORT_ONLY`, entrambe false in self-hosted e vere in managed. Così un
>   self-hosted può proteggersi dall'incorniciamento senza la CSP in prova, e viceversa;
> - gli header del profilo gestito li mette lo stesso middleware, che legge le impostazioni una volta, quando viene
>   costruito; la CSP in sola segnalazione solo sulle risposte HTML fuori da `/mkdocs` e `/api/`.
>
> **I rossi di CP7b-2 sono pronti** in `/tmp/librefolio-r13-h-7b2/`, non applicati: `test_profile_defaults.py` (37
> casi), `test_managed_headers.py` (169), `runner.diff` (si applica pulito sopra le voci di CP7b-1) e un `README.md`.
>
> **Da sapere per la cura**:
>
> - in pydantic 2.13 un `self.X = v` dentro un validatore `after` mette `X` in `model_fields_set` e salta la
>   validazione. La cura imposta il valore del profilo con `object.__setattr__`, senza segnarlo come scelta
>   dell'operatore; i valori della tabella li verifica il test di guardia, in modo rigoroso;
> - un valore impostato uguale al default conta come impostato (`600`, `false`, `0`): niente confronti col default;
> - il middleware si costruisce alla prima chiamata dell'app, quindi i test costruiscono app nuove;
> - `content-security-policy` è un prefisso di `content-security-policy-report-only`: il controllo «header già messo
>   dalla rotta» confronta i nomi interi, cosa che CP7b-1 fa già;
> - `services config-env-example` diventa rosso finché i due campi nuovi non sono in `.env.example`, come righe
>   commentate.

##### Passo 4 di CP-U2 — le prove pesanti ✅ (2026-10-16, notte)

> Dopo la ripresa delle 01:33: `mkdocs build --strict` senza avvisi, `check-links`, `check-orphans` puliti.
> Slot pesante 2 (01:48–02:02), una spec alla volta, `nice`, carico sotto 70: E2E `front-utility files` 29 (con lo
> scenario nuovo: un PNG caricato dalla pagina esce personale, poi «Condividi» e «Rendi personale» con conferma),
> `files-uploader` 8, `files-destructive` 6, `files-pdf-offline` 1, `image-crop` 42. Porta 6181 libera.

#### Checkpoint CP-U2 🧊 (2026-10-16, notte) — FROZEN, in attesa del coordinatore

> **Ingresso**: CP-U2 è in `dev_release2` (treno 79, merge `2d1eee33a`), con 4 righe nel CHANGELOG; la condizione di
> rilascio sulla pagina utente dei File è chiusa. Prima, sulla revisione combinata `b3feddd2c`: `api sync`, `front
> check` 0/0 (al primo giro 12 errori, solo per il client generato non aggiornato dopo il merge), Vitest 93, E2E `files`
> 29. Le registrazioni di CP7b-1 le ho tolte durante il merge, salvate in patch con `git apply -R`, e poi rimesse.

### CP7b-1 — header e cache (2026-10-16, notte) — in corso

#### Passo 1 — la cura ✅

> **Note implementazione** (script `/tmp/librefolio-r13-h-7b1/apply_cp7b1.py`, applicato su `b3feddd2c`):
>
> - `platform/security_headers.py`, nuovo: `SecurityHeadersMiddleware` mette `nosniff` e
>   `Referrer-Policy: strict-origin-when-cross-origin` su ogni risposta HTTP, senza sovrascrivere quelli di una rotta.
>   Se la richiesta fallisce prima che la risposta parta, manda da sé il 500 con gli header e poi rilancia.
>   `register_served_types()` registra i tipi che servono a `nosniff` (font, `.map`, `.mjs`, `.wasm`…).
> - `middleware.py`: la pila è `activity` (Z), `security_headers`, `gzip`, `cors`.
> - `static_site.py`: `immutable` solo sotto `_app/immutable/`, il resto di `/_app` in `no-cache, must-revalidate`,
>   anche sui 304; `install_static_site` chiama `register_served_types()`.
> - `static_uploads.py` (nota di W): il TODO citava `EVENT_COMPATIBLE_TYPES`, che non c'è più. Fatto invece che
>   ripuntato: le due liste di blocco sono `frozenset`.
>
> **Prove**, una alla volta, carico sotto 70; i rossi passano tutti al primo giro:
>
> - `services static-cache-policy` 26, `services security-headers` 15, `utils nosniff-content-types` 30;
> - `utils served-content-types` 36, `services app-lifecycle` 42 (Z ha tolto il caso «nessuna scadenza», come
>   concordato), `utils static-route-confinement` 26, `services static-uploads` 73;
> - `db populate --force`; `api http-compression` 10, `api uploads-serve-file` 13, `api system` 117,
>   `api instance-block` 60.

#### Passo 2 — doc, ritocchi e prove pesanti ✅ (2026-10-16, notte)

> **Note implementazione**:
>
> - doc (docs-writer): `developer/architecture/security.md`, sezione nuova `#response-headers`;
>   `developer/architecture/overview.md`, la pila a quattro voci e un paragrafo sulla cache del browser (HTML e file di
>   `/_app` senza hash revalidati, `/_app/immutable/` per un anno, miniature `private`); `developer/api/overview.md`,
>   il posto di `gzip` nella pila; wiki `problems/stale-frontend-after-update-html-cached.md`. Nessun debito di
>   traduzione;
> - corretti, perché esageravano, i commenti di `security_headers.py`, la docstring di
>   `test_nosniff_content_types.py` (test-author) e due frasi delle mie registrazioni nel runner. Per la specifica
>   Fetch, `nosniff` rifiuta solo script e fogli di stile di un altro tipo, non font e mappe. Registrare i tipi resta
>   giusto: niente esce come `application/octet-stream`. Aggiornata anche la docstring di `middleware.py`, che
>   descriveva la pila di prima.
>
> **Prove** (slot pesante 2): E2E `app-start-auth` 3, `files-pdf-offline` 1, `docs-offline-math` 2; `all-backend`
> 7/7, **17 084 passed, 4 skipped, 0 failed** (02:55–03:28); `utils nosniff-content-types` 30, rilanciato dopo la
> docstring; `mkdocs build --strict` senza avvisi; `check-links`; `check_source_paths` della pagina wiki. Porta 6181
> libera.

#### Checkpoint CP7b-1 🧊 (2026-10-16, notte) — FROZEN, in attesa del coordinatore

> **Ingresso**: commit `04d82ca3a` (feat), `6561e3cce` (doc), `e785691ae` (diario); merge di `dev_release2`
> `503dce683`, pulito, HEAD `dd89398dd` (dentro B2, Z7b, CP11a/b, A6d/e, E-5 e il lotto di T). Prove sulla revisione
> combinata, una alla volta con `nice`, carico sotto 70: `services security-headers` 15, `services app-lifecycle` 42,
> `api http-compression` 10, `api backup-restore` 114 (l'upload del ripristino passa dal middleware), `api system-wake`
> 74 (la risposta in streaming del risveglio), `api system` 118, `mkdocs build --strict`, `check-links`. Entrato nel
> treno 86 (merge `1f4c5aeca`) con le righe 🔒 (header) e 🐛 (cache) nel CHANGELOG.

### CP7b-2 — i default del profilo e gli header del profilo gestito (2026-10-16, notte) — in corso

Via del coordinatore alle 03:48 del 16/10. Il lotto più delicato: ogni campo ha il suo test «self-hosted invariato».

#### Passo 1 — i rossi nel worktree ✅ (2026-10-16, notte)

> **Note implementazione**: copiati da `/tmp/librefolio-r13-h-7b2/` `test_profile_defaults.py` (37 casi) e
> `test_managed_headers.py` (169) in `backend/test_scripts/test_services/`; applicato `runner.diff` a
> `scripts/test_runner/_backend_services.py` (selettori `services profile-defaults` e `services managed-headers`).
> Sul codice di allora: `profile-defaults` 37 rossi (35 per la tabella che manca, 2 per i campi che mancano),
> `managed-headers` 169 rossi (la barriera: i campi non esistono).

#### Passo 2 — la cura ✅ (2026-10-16, notte)

> **Note implementazione**:
>
> - `config/__init__.py`: `PROFILE_DEFAULTS` (`selfhosted` vuoto; `managed`: i due `RISK_*_IDLE_TIMEOUT_SECONDS` a
>   60.0, `LIBREFOLIO_FRAME_PROTECTION` e `LIBREFOLIO_CSP_REPORT_ONLY` a `True`), i due campi booleani nuovi, default
>   `False`, e il validatore `after` `_apply_profile_defaults`. Questo scrive con `object.__setattr__` solo i campi
>   assenti da `model_fields_set`. La docstring del modulo elenca le due variabili e i valori del profilo gestito.
> - `platform/security_headers.py`: `FRAME_HEADERS` (`X-Frame-Options: SAMEORIGIN`, CSP applicata
>   `frame-ancestors 'self'` e nient'altro) su ogni risposta, il 500 e le preflight comprese;
>   `CSP_REPORT_ONLY_POLICY` come `Content-Security-Policy-Report-Only` solo sull'HTML della web app
>   (`_is_web_app_page`: tipo `text/html`, fuori da `/mkdocs` e da `/api`, nudi o con la barra). Le impostazioni si
>   leggono una volta, in `__init__`; nomi degli header confrontati interi.
> - `.env.example`: due righe commentate nella sezione «Instance Profile» e «managed: 60» sui due timeout di inattività.
> - Il motore del rischio legge i timeout solo da `Settings` (`risk/quant/workers.py`), quindi il valore del profilo
>   arriva senza altro codice. Fuori da `config/__init__.py`, nessuno fa `model_copy` o legge `model_fields_set` di
>   `Settings`.
>
> **Prove**, una alla volta, `nice -n 10`, carico sotto 70; i rossi passano al primo giro: `services profile-defaults`
> 37, `services managed-headers` 169, `services security-headers` 15, `services config-env-example` 36, `config-misc`
> 12, `config-package` 691, `config-secrets` 58, `config-instance-key` 98, `config-audit` 90, `services
> app-lifecycle` 42, `utils nosniff-content-types` 30; `db populate --force`; `api system` 118, `api instance-block` 62,
> `api http-compression` 10. Black e ruff puliti. Porta 6181 libera.
>
> **⚠️ Fuori pista**: il default «managed» di B (`MANAGED_MAX_UPLOAD_MB`, 500, in `config/backup.py`) non passa da
> `PROFILE_DEFAULTS`, che copre solo i campi di `Settings`: `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` si legge da `os.environ`.
> Oggi i meccanismi sono due, e la doc lo dice. Residuo leggero **H-17** nel backlog, da concordare con B.

#### Passo 3 — doc e `all-backend` ✅ (2026-10-16, notte)

> `all-backend` nello slot pesante, dalle 03:59, `--workers 2`. **⚠️ Fuori pista**: partito con `nice -n 10`; il
> coordinatore ha chiesto poi `-n 19`, perché T ha E2E a un worker fino alle 05:05. Non l'ho riavviato: ho fatto
> `renice -n 19` per PID su tutto l'albero del runner. Su macOS `-n` è un incremento, quindi i processi Python sono
> scesi al minimo, 20, e i figli che nascono dopo lo ereditano. Doc con docs-writer, senza build mentre la suite gira.
>
> **Note implementazione** (doc, docs-writer, solo inglese):
>
> - `admin/hosting_providers.en.md`: il profilo cambia sette cose, con tre righe nuove nella tabella (inattività dei
>   worker, protezione dei frame, CSP report-only) e tre punti. Un valore impostato vince sempre, anche se è uguale al
>   default; un pannello che incornicia l'app vuole `LIBREFOLIO_FRAME_PROTECTION=false`; la CSP report-only non blocca
>   nulla e non ha un indirizzo di report. Più una riga in «For Each Instance» e un collegamento alla doc developer.
> - `admin/configuration.en.md`: la riga di `LIBREFOLIO_PROFILE`, due righe nuove (valori ammessi; un valore diverso
>   ferma l'avvio, come per `LIBREFOLIO_BLOCKED`), il default di inattività «600 (60 in managed)».
> - `developer/architecture/security.md`: sottosezione nuova `#managed-headers`, con una tabella degli interruttori e una
>   delle direttive. Spiega dove va la CSP report-only e perché, la lettura una tantum, i nomi interi e i test.
> - `developer/architecture/settings.md`: un punto su `PROFILE_DEFAULTS`: il meccanismo, `object.__setattr__`, la
>   guardia sulla tabella, il limite ai campi di `Settings` con l'esempio di `config/backup.py`, come si aggiunge un
>   default (anche in `MANAGED_DEFAULTS` del test).
> - `developer/architecture/overview.md` (la voce `security_headers` della pila) e `developer/backend/risk/architecture.md`
>   (il default di inattività).
> - Codice: il commento della voce `security_headers` in `platform/middleware.py`, solo testo.
>
> Verificati sul codice: EmbedPDF (PDFium in WebAssembly) giustifica `'wasm-unsafe-eval'`; Zod 3.24 non usa `eval`;
> `app.html` registra il service worker; `main.py` chiama `get_settings()` all'import.
>
> **Prove**: `all-backend` 7/7, **17 792 passed, 4 skipped, 0 failed** (03:59–04:36, `--workers 2`, nice 19–20);
> `mkdocs build` strict, senza avvisi; `check-links` 96 validi. `translate-validate --file admin/configuration.en.md`:
> 174 errori, ma il debito c'era già. Le tre traduzioni sono al 25–26% della sorgente; le due righe nuove e la cella
> cambiata vi si aggiungono. Pagina non marcata. Porta 6181 libera.

### Checkpoint CP7b-2 🧊 (2026-10-16, notte) — FROZEN, in attesa del coordinatore

> **Prove d'ingresso**. Commit `c8113aee8` (feat), `59fa4b645` (doc), `cb1c852e8` (diario); merge di `dev_release2`
> `3edfc4b9a` (Z2b e CP-6), pulito, HEAD `887c6dd12`. Riletti i file fusi da soli: `.env.example` (le mie righe e la
> sospensione di Z2b), `configuration.en.md` (le righe di tutti e due), `overview.md` (la riga della pila col mio
> testo, il passo `idle-monitor` di Z), `settings.md`, il runner (nessun doppione, ruff pulito).
>
> Una alla volta, `nice -n 19`, carico sotto 70 (04:40–04:50): `services profile-defaults` 37, `managed-headers` 169,
> `config-env-example` 38, `app-lifecycle` 42; `db populate --force`; `api system` 118; `mkdocs build` strict senza
> avvisi; `check-links` 96 validi. Porta 6181 libera.
>
> **⚠️ Fuori pista**: `services config-package` 692 passati, **1 rosso, non di CP7b-2**. Il caso
> `test_a_module_outside_the_config_package_reads_no_environment_variable[services/platform/sleep_wake/suspend.py]`:
> Z2b (`7080e9f38`) legge `FLY_APP_NAME` e `FLY_MACHINE_ID` con `os.environ` fuori da `backend/app/config/`
> (`suspend.py:48`). È rosso anche su `dev_release2`, dove il test e il file sono identici. La cura è di Z: un accessore
> in `config/sleep_wake.py`. L'ho segnalato al coordinatore, non tocco i file di Z.
>
> **Controllo dei colori** (richiesta del coordinatore: niente classi `-lf-` su un elemento con classi di tavolozza).
> Nessun elemento misto nel mio markup:
>
> - CP-U2 aggiunge solo `action-btn` in `FileGrid`, CSS locale sui token `--lf-cmp-file-grid-*` con le sue regole
>   scure. La colonna `scope` passa solo `variant` a DataTable, che disegna `cell-badge {variant}` da `table.css`;
> - `InstanceNotices` e `InstanceBlockedPage` (15/10) hanno solo ruoli;
> - CP-U1, CP2b, CP7b-1 e CP7b-2 non hanno markup.
>
> Ho guardato anche i punti ciechi di G3: classi composte in script, passate a componenti figli o alle props delle
> colonne.

> **Ingresso**: CP7b-2 è in `dev_release2` (treno 92, merge `d8549c69a`), con le righe 🔒 e 🔄 nel CHANGELOG. Il rosso
> di `config-package` l'ha curato Z (treno 93). Il ramo è stato portato avanti con fast-forward a `34405dfbb`.

### Le note di X: H-14, H-15, H-16 (2026-10-16, notte) — in corso

Approvate con l'analisi di CP7b. Fino alle 05:25 solo prove leggere, poi pausa fino alle 06:45. A7 aggiunge una riga
ciascuno in `app_lifespan.py` (il passo `admin-bootstrap` dopo `global-settings`), `config_audit.py` e `instance_block.py`:
all'aggiornamento di base si tengono entrambe le parti. La cura sta in `/tmp/librefolio-r13-h-xnotes/` (`apply_xnotes.py`,
provato a secco su copie; ruff e black puliti), da applicare dopo il giro dei rossi.

**Disegno**:

- **H-14**: `derive_key_from(key, purpose, length=32)` in `instance_key.py`, con lo stesso HKDF di `derive_key`, che ora
  la usa tramite `_derive`. L'ordine dei controlli: scopo e lunghezza (`ValueError`), poi il tipo della chiave
  (`TypeError`), poi la lunghezza della chiave (`InstanceKeyError`, senza la chiave nel messaggio). Non legge né
  l'ambiente né la cartella dei dati, e non crea il file della chiave. B legge la chiave del backup con
  `read_secret_file()`, come il modulo legge la sua. Tre vettori noti, calcolati col `derive_key` di oggi, fissano la
  derivazione.
- **H-15**: un modulo nuovo, `platform/plugin_secrets_check.py`:
  - `check_plugin_secrets(session)` restituisce un `ConfigCheck` `platform.plugin_secrets`: `ok` senza segreti di
    sistema illeggibili, `error` con `{"count": system}` quando ce ne sono;
  - `log_plugin_secrets_check()` è il passo d'avvio `plugin-secrets-check`, dopo `global-settings`. Non solleva mai: un
    errore del controllo diventa un avviso col solo nome della classe;
  - le chiavi i18n `instance.checks.pluginSecrets.ok` e `.unreadable` (plurale ICU), in 4 lingue.
- **H-16**: le due frasi di `security.md`, con la doc di H-14 e H-15 (docs-writer, dopo le prove).

**Decisioni notturne, da rivedere**:

- solo il conteggio `system`, anche nel log: è la regola del piano di X («mostra all'admin solo il conteggio di
  sistema»). Resta un buco: se sono illeggibili solo segreti di utenti, il controllo dice `ok` e all'avvio l'operatore
  non sa che la chiave è cambiata. Da rivedere con X;
- nessuna voce nell'interfaccia: la scheda «Sicurezza» non esiste ancora (`config_audit.py` dice «will evaluate»). Il
  controllo restituisce già un `ConfigCheck`, con le sue chiavi i18n, pronto per il registro di A.

#### Passo 1 — i rossi ✅ (2026-10-16, notte)

> **Note implementazione** (test-author, 66 casi nuovi, ruff e black puliti):
>
> - `test_instance_key.py`, sezione (g), da 98 a 151 casi. Tre risposte note, l'equivalenza con `derive_key` (chiave
>   configurata e generata), la chiave data che vince su quella dell'istanza, nessun file della chiave creato,
>   l'ambiente e la cartella dei dati mai letti, le sorgenti guaste ignorate, 32 richieste non valide, il `TypeError`, le
>   chiavi corte, quelle da 32 caratteri;
> - `test_plugin_secrets_check.py`, nuovo, 11 casi: `ok`, `error` col solo conteggio `system`, il log, le eccezioni
>   ridotte a un avviso, due casi su un DB SQLite vero. Senza segreti il passo non crea il file della chiave;
> - `test_app_lifecycle.py`, 2 casi: il passo dopo `global-settings` e prima di `scheduler`, in ordine relativo perché
>   A7 aggiunge `admin-bootstrap` nello stesso punto; il suo `run()` restituisce un awaitable;
> - il runner: `services plugin-secrets-check`, `isolation="pure"`.
>
> **Prova dei rossi** (05:10–05:12, uno alla volta, `nice`): `plugin-secrets-check` 11 rossi (`ModuleNotFoundError`),
> `config-instance-key` 53 rossi («derive_key_from is missing»), 98 verdi, `app-lifecycle` 2 rossi (il passo che
> manca), 42 verdi. Ognuno sulla sua barriera.

#### Passo 2 — la cura ✅ (2026-10-16, notte)

> **Note implementazione**: applicato `apply_xnotes.py`: `instance_key.py` (`derive_key_from`, `_check_purpose_and_length`,
> `_derive`), `plugin_secrets_check.py` nuovo, il passo in `app_lifespan.py`, le chiavi i18n nelle sorgenti
> `instance/{en,it,fr,es}.json`. Ruff e black puliti.
>
> **Prove** (05:12–05:13): `plugin-secrets-check` 11, `config-instance-key` 151, `app-lifecycle` 44; `i18n check`
> rigoroso, verde. `config-package`: 694 verdi, compreso il caso del modulo nuovo, e 1 rosso, quello noto di Z2b
> (`sleep_wake/suspend.py`). È curato nel treno 93, che il mio ramo `34405dfbb` non ha ancora. Porta 6181 libera.

#### Passo 3 — la doc (2026-10-16, notte) — scritta, build dopo le 06:45

> **Note implementazione** (docs-writer, solo inglese, nessun comando):
>
> - `developer/architecture/security.md`:
>   - H-16, l'elenco di `env_secret()`: i sei segreti, `LIBREFOLIO_WAKE_TOKEN` compreso, poi «ogni variabile delle
>     impostazioni dei plugin». Due frasi su cosa succede quando il token del risveglio o un `_FILE` di un plugin non
>     si possono usare;
>   - `derive_key_from()`: una riga nella tabella e un paragrafo sui due helper comuni e sull'uso previsto per B;
>   - H-16, la «Known limitation» riscritta: ora un cambio di chiave si vede, grazie al `key_id` e al passo d'avvio;
>   - la riga `i18n_key`, che diceva 13 messaggi, ora ne conta 15;
>   - la sottosezione nuova `#plugin-secrets-check`.
> - `developer/architecture/patterns/plugin_settings.md`: «No startup check calls it yet» sostituita, più una riga nella
>   tabella dei test.
> - `developer/architecture/overview.md`: il passo 12 `plugin-secrets-check`, i seguenti rinumerati fino a 16.
> - `admin/configuration.en.md`: una riga ❌ nella tabella «Startup Checks» e una frase in «Saved Secrets and the
>   Instance Key». È il debito di traduzione (it/fr/es), pagina non marcata.
>
> Verificati da me: `require_wake_token` e `wake_unavailable` (`api/v1/system/wake.py`), le ancore `#secrets`,
> `#environment`, `#startup-checks`, `#plugin-secrets`.
>
> **⚠️ Fuori pista**:
>
> - il docs-writer ha lanciato `python3` due volte, una per leggere `instance/en.json` e una per spostare una riga della
>   tabella. È roba leggera, ma la regola della pausa diceva nessun comando; `git diff --check` pulito;
> - i messaggi i18n `unreadable` rimandavano a «Plugin settings», il titolo della scheda. Li ho corretti col percorso
>   della scheda nello stile della UI: «Settings → Plugins», «Impostazioni → Plugin», «Paramètres → Plugins»,
>   «Configuración → Plugins»;
> - dalla doc: `check_plugin_secrets()` può sollevare su un errore del DB, e la cattura solo il passo d'avvio. Quando A
>   la userà nella scheda «Sicurezza», dovrà gestirlo.
>
> **Da fare dopo le 06:45**: `i18n check` (dopo il ritocco dei messaggi), `mkdocs build --strict`, `check-links`,
> `translate-validate --file admin/configuration.en.md`, poi lo slot pesante di `all-backend` (il passo nuovo gira a
> ogni avvio del server di prova).

> **Checkpoint intermedio**: commit `cb37c79cf` (feat), `3b95550e1` (doc), `dee4dc311` (diario); merge di
> `dev_release2` `72e66d1a6` (il treno 93 con la cura di Z e il secondo lotto di T), pulito, HEAD `af24a61bb`. Restano
> le prove leggere sulla revisione combinata e `all-backend`, dopo il «blocco finito» dei colori.

### La card del backup nella pagina di blocco (2026-10-16, mattina) — preparazione fuori dal worktree

Assegnato dal coordinatore dopo le note di X («then the backup card on the block page»). B ha già consegnato il campo
`backup_available` di `GET /system/block` (vero per gli amministratori, decisione 12), e le rotte del backup completo
sono in `ALLOWED_WHEN_BLOCKED`. Manca il bottone: la doc admin lo dice due volte, «the block page has no button for it
yet».

**Disegno**:

- `InstanceBlockedPage.svelte` legge `backup_available` dalla risposta e, quando è `true`, mostra la
  `BackupDownloadCard` di B, che è autonoma per scelta. La decisione è del server, non del ruolo letto nel client.
- La card sta in un riquadro `bg-lf-card` (`instance-blocked-backup`) sotto l'avviso, **fuori** dalla sezione
  `role="alert"`: un lettore di schermo annuncia il blocco, non tutta la card. Le due cose stanno in un contenitore
  `max-w-lg`. Solo ruoli, nessuna classe di tavolozza.
- Nessun testo nuovo: la card ha già titolo e avvertenze. Quello per gli utenti dice già «chiedi un backup
  all'amministratore».

**Superfici**: il componente; il suo Vitest con uno stub della card (`__tests__/harness/BackupDownloadCardStub.svelte`);
la doc `admin/hosting_providers.en.md` («What Users See», «What Still Answers»), `developer/architecture/security.md`
(la tabella delle rotte ammesse) e `developer/frontend/state/app-state.md` (la pagina di blocco e i suoi test id).
Nessun E2E della pagina di blocco esiste: il Vitest e i test API di B coprono il resto.

**Stato**: la patch `/tmp/librefolio-r13-h-blockcard/apply_blockcard.py` è provata a secco; il test-author scrive i rossi
Vitest in `/tmp`. Si applica dopo `all-backend` delle note di X: un cambio delle sorgenti del frontend farebbe
ricostruire il frontend al server di prova.

> **⚠️ Fuori pista (note di X, dopo il checkpoint intermedio)**: la card di B dice «The logs and the instance key are not
> included». L'archivio del backup dell'istanza non contiene `secrets/instance.key`, quindi tre frasi della mia doc
> rimandavano a un posto dove la chiave non c'è. Corrette, non ancora committate:
>
> - la riga ❌ di «Startup Checks» in `admin/configuration.en.md`: ora parla della propria copia di
>   `secrets/instance.key`, salvata con la cartella dei dati come dice «The Instance Key»;
> - due paragrafi di `developer/architecture/security.md`: il file perso, e l'uso previsto di `derive_key_from()`. La
>   vecchia chiave viene dalla copia dell'amministratore o dal vecchio `LIBREFOLIO_INSTANCE_KEY`;
> - la docstring di `derive_key_from()`, solo il testo.
>
> **Rossi della card** (test-author, in `/tmp/librefolio-r13-h-blockcard/`, non applicati, niente lanciato):
> `InstanceBlockedPage.test.ts` completo, con 7 casi nuovi (11 test con le righe di `it.each`), e lo stub
> `harness/BackupDownloadCardStub.svelte`. I casi negativi montano prima la stessa pagina con `backup_available: true`
> come controllo, così oggi sono rossi per la ragione giusta.
>
> **Rifiniture dalla sua revisione**, nella patch:
>
> - il riquadro è un `<section aria-labelledby>` con un `<h2>` (`instance.block.backupTitle`, 4 lingue), così i titoli
>   vanno h1 → h2 → h3 della card di B e la regione ha un nome;
> - un `ToastContainer` nella pagina di blocco: il layout lo monta solo attorno all'app, quindi i toast della card
>   (errori, «backup parziale») non si vedevano. Sta nel mio componente, senza toccare il layout condiviso.
>
> **Accettati come sono**: la card dentro una card segue i ruoli (un `bg-lf-panel` dentro un `bg-lf-card`, come nella
> scheda Backup); se `GET /system/block` fallisce, la card torna solo ricaricando la pagina; la descrizione segue il
> ruolo nel client, la card il campo del server.

#### Card del backup — passo 1, applicata (2026-10-16, mattina) — prove dopo il «blocco finito»

> Il coordinatore (05:47) ha dato il via a scrivere durante la pausa. B3 (`887a24123`) non tocca il frontend: la
> `BackupDownloadCard` resta quella di dev, e il coordinatore ricontrolla all'ingresso di B5b, il lotto UI di B.
>
> **Note implementazione**:
>
> - applicato `apply_blockcard.py`: `InstanceBlockedPage.svelte` (`backupAvailable`, la `<section>` con `<h2>`, il
>   `ToastContainer`) e `instance.block.backupTitle` nelle 4 sorgenti i18n di `instance`;
> - copiati il Vitest dei rossi e lo stub `__tests__/harness/BackupDownloadCardStub.svelte`;
> - in corso, solo scrittura: il test-author aggiunge i casi per la regione con nome e per i toast; il docs-writer
>   aggiorna `hosting_providers`, `security.md` e `app-state.md`.
>
> **Prove da fare**, una alla volta, dopo il «blocco finito»: `prettier` sul componente, `front check`, il Vitest del
> file (rosso sul componente di HEAD per ragionamento, verde sul nuovo), `i18n check`, `mkdocs build`, `check-links`;
> poi `all-backend` insieme alle note di X, che prende anche la ricostruzione del frontend.

#### Card del backup — passo 2, rossi completati e doc (2026-10-16, mattina) — prove dopo il «blocco finito»

> **Note implementazione**:
>
> - test-author: in `InstanceBlockedPage.test.ts` due casi in più, tre test con le righe di `it.each`. La sezione ha
>   per nome il suo `<h2>`, l'unico della pagina, dopo l'`<h1>`. Un toast spinto dallo store mentre la pagina è montata
>   si vede, per un amministratore con la card e per un utente senza. Ogni test toglie il suo toast con
>   `onTestFinished`. Su HEAD falliscono sull'`<h2>` che manca e sul toast che non compare, per ragionamento: niente
>   lanciato;
> - docs-writer, senza debito di traduzione:
>   - `admin/hosting_providers.en.md`: l'introduzione del blocco, «What Users See» (la card e la copia di
>     `secrets/instance.key`), «What Still Answers»;
>   - `developer/architecture/security.md`: la tabella delle rotte ammesse e `backup_available`;
>   - `developer/frontend/state/app-state.md`: la card, il `ToastContainer`, il link «Manage subscription» che
>     mancava, tutti e sei i test id;
>   - `developer/api/index.md`: il riassunto di `/system/block`;
> - corretto il commento troncato sopra `<ToastContainer />`.
>
> **⚠️ Fuori pista**:
>
> - due errori nel mio brief al docs-writer, corretti da lui. Il selettore del Vitest è `front-utility component-unit`,
>   non `core-unit`. Un link a `configuration.md#instance-key` da una pagina solo inglese avrebbe rotto la build
>   rigorosa delle lingue tradotte, perché `configuration.{it,fr,es}.md` non hanno quell'ancora (decisione
>   `docs-anchors-from-the-render`): ha usato il nome della sezione;
> - il test-author ha visto che `ToastContainer` non ha regione live: nessun toast dell'app arriva ai lettori di schermo.
>   È fuori perimetro: **H-18** nel backlog.

### H-17 — un solo posto per i default del profilo: analisi (2026-10-16, mattina) — sola lettura

Richiesta del coordinatore (06:00). La porta lui a B.

**Oggi**: `backup_max_upload_mb()` (`config/backup.py`, di B) legge `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` da `os.environ` a
ogni chiamata.

- Vuoto o solo spazi equivale a non impostato: `0` in self-hosted, `MANAGED_MAX_UPLOAD_MB` (500) in managed.
- Solo cifre ASCII, con spazi attorno ammessi; tutto il resto solleva `BackupConfigError`
  (`BACKUP_MAX_UPLOAD_MB_INVALID`).
- Chi la usa: solo `_upload_limit()` di `api/v1/backup/restore.py`. Un valore illeggibile scrive un errore nel log e
  fa rispondere 503 `backup_upload_unavailable` al solo upload del ripristino: il resto dell'istanza va avanti.
- Test (`api backup-restore`, sezione (e)): 10 casi sui valori validi e sui due profili, 8 valori illeggibili (segno
  meno, decimale, lettere, cifra araba, apice, segno più, esponente, esadecimale), più un caso che fissa
  costante e variabile.
- Doc: la tabella di `#restore-upload-limit` in `admin/hosting_providers.en.md` («Not set, or empty»), la riga di
  `admin/configuration.en.md` (tradotta) e il mio punto in `developer/architecture/settings.md`, che la cita come
  esempio del secondo meccanismo.

**Opzione 1 — farne un campo di `Settings`** e mettere 500 in `PROFILE_DEFAULTS["managed"]`. Sconsigliata:

- vuoto e solo spazi diventerebbero un errore di validazione, cioè il server non parte. Per tenere «vuoto = non
  impostato» servirebbe un passo `mode="before"` che tolga i valori vuoti dall'input, perché il campo resti fuori da
  `model_fields_set`: un meccanismo in più;
- un valore illeggibile fermerebbe l'avvio dell'istanza, invece di un 503 sul solo upload. B ha scelto apposta il
  contrario, e l'ha documentato;
- il parsing degli interi di pydantic non è la regola «solo cifre ASCII» di B: gli 8 casi illeggibili andrebbero
  rifissati, e qualcuno potrebbe passare;
- tocca `restore.py`, dove B3 aggiunge 118 righe, la sezione (e) dei test di B, due pagine di doc e il debito di
  traduzione di `configuration`.

**Opzione 2 — consigliata: una seconda tabella accanto a `PROFILE_DEFAULTS`**, per le variabili che un modulo di
sezione legge dall'ambiente. Per esempio `ENVIRONMENT_PROFILE_DEFAULTS = {"selfhosted": {}, "managed":
{"LIBREFOLIO_BACKUP_MAX_UPLOAD_MB": 500}}`, con `profile_default(name, fallback)` in `config/__init__.py`.

- **Per B**: in `backup_max_upload_mb()`, `if not raw: return profile_default(MAX_UPLOAD_VARIABLE, 0)` e via
  `MANAGED_MAX_UPLOAD_MB`. Oppure resta come alias del valore della tabella: decide B. Nella sezione (e) cambia solo il
  caso che fissa la costante, che legge la tabella. Il comportamento è identico: vuoto = non impostato, 503 su un valore
  illeggibile.
- **Per H**: la tabella e `profile_default()`. In `test_profile_defaults.py` le stesse guardie della prima tabella:
  una voce per profilo, ogni chiave una variabile letta sotto `backend/app/config/` e documentata in `.env.example`, il
  valore un `int` diverso dal ripiego, un caso «self-hosted invariato» parametrizzato su ogni chiave. Poi il punto di
  `settings.md`: un solo posto per i default del profilo, due tabelle.
- **Doc admin**: nessun cambiamento e nessun debito di traduzione, perché il comportamento non cambia.
- **Peso**: piccolo. Due righe nel file di B, una tabella, un helper e una decina di casi da me, un paragrafo di doc.

**Quando**: B3 (`5f1543e81`, `2c2c8fc3e`) non tocca `config/backup.py`. Tocca però `restore.py` e
`test_backup_restore.py`, che l'opzione 2 non tocca o tocca appena (il caso della costante). Quindi:

- **dopo l'ingresso di B3** basta per l'opzione 2, se B5 non tocca `config/backup.py`; lo verifica il coordinatore sul
  ramo di B;
- non serve aspettare B5 per il meccanismo. Il mio lotto (tabella, helper, test, doc) si può fare prima, e le due righe
  di B arrivano dopo, scritte da B o da me col suo OK.

### H-17 — la seconda tabella dei default del profilo (2026-10-16, mattina) — in corso, solo scrittura

**Via del coordinatore** (06:03): opzione 2 approvata, come lotto a parte. La mia parte: la tabella, `profile_default()`,
le guardie in `test_profile_defaults.py`, `settings.md`. Le due righe di `backup_max_upload_mb()` le scrive B, dopo
l'ingresso di B3.

**Disegno** (cura in `/tmp/librefolio-r13-h-h17/apply_h17.py`, provata a secco su una copia):

- in `config/__init__.py`, sotto `PROFILE_DEFAULTS`: `ENVIRONMENT_PROFILE_DEFAULTS = {"selfhosted": {}, "managed":
  {"LIBREFOLIO_BACKUP_MAX_UPLOAD_MB": 500}}`;
- `profile_default[T](name, fallback) -> T`, subito dopo `get_settings()`. Legge il profilo a ogni chiamata e
  restituisce il valore della tabella, oppure il ripiego del codice. Il modulo di sezione la chiama solo con la variabile
  non impostata, e tiene le sue regole per il vuoto e l'illeggibile;
- la docstring del modulo nomina le due tabelle;
- in attesa delle righe di B, il valore 500 vive in due posti, uguali: la tabella e `MANAGED_MAX_UPLOAD_MB`. La doc non
  dice che `backup_max_upload_mb()` legge la tabella finché non lo fa.

**In corso, solo scrittura**: il test-author scrive i rossi nella sezione nuova di `test_profile_defaults.py`; il
docs-writer aggiorna il punto «Profile defaults» di `settings.md`. Al «blocco finito»: il giro dei rossi, la cura, ruff e
black, il giro dei verdi.

#### H-17 — passo 1, rossi e doc scritti (2026-10-16, mattina) — niente lanciato

> **Note implementazione**:
>
> - test-author: una sezione nuova, (f), in `test_profile_defaults.py`, che passa da 37 a 52 test. Undici funzioni,
>   15 test:
>   - la tabella: una voce per profilo, `selfhosted` vuoto, `managed` uguale a `ENVIRONMENT_MANAGED_DEFAULTS` con i
>     tipi esatti (`exactly()`: `same()` accetterebbe `500.0`), nessun campo di `Settings` fra le chiavi;
>   - ogni chiave letta come costante stringa (AST) da un modulo di sezione, e documentata in `.env.example` con il
>     parser di `test_env_example.py`;
>   - `profile_default()`: il ripiego stesso (`is`) in self-hosted, il valore della tabella in managed, `MANAGED` e
>     ` Managed `, il profilo letto a ogni chiamata.
>
>   Le barriere: «ENVIRONMENT_PROFILE_DEFAULTS is missing» (6 test) e «profile_default is missing» (9), cercati con
>   `getattr` mentre il test gira, così i 37 casi esistenti restano uguali;
> - docs-writer: in `settings.md` il punto «Profile defaults» rimanda al punto nuovo «Profile defaults of the section
>   modules' variables» (la tabella, l'helper, le guardie, come si aggiunge una voce). Non dice che
>   `backup_max_upload_mb()` legge la tabella;
> - runner: la descrizione di `services profile-defaults` nomina H-17.
>
> **Dopo il «blocco finito»**: `services profile-defaults` sul codice di oggi (attesi 15 rossi, 37 verdi), poi
> `apply_h17.py`, ruff e black, `profile-defaults` verde (52), `config-package` e `config-env-example`.

#### Prove leggere delle note di X e della card, sulla revisione combinata ✅ (2026-10-16, mattina)

> Dopo il «blocco finito» (06:48), HEAD `31089e96f`, una alla volta, `nice`, carico sotto 70 (06:48–07:08):
>
> - card: `prettier --check` pulito, cancello dei colori pulito. Il Vitest di `InstanceBlockedPage.test.ts` dà 14 rossi
>   sul componente di prima (`af24a61bb`, rimesso al suo posto e verificato identico a HEAD) e 36 verdi sul nuovo;
> - `front check`: al primo giro 4 errori, tutti in `PasswordStrength.svelte` di A (`password_rules` assente da
>   `AccountsInstanceConfig`). Era il client generato vecchio dopo il merge della base: `api sync`, poi `front check`
>   0/0;
> - `i18n check` rigoroso, verde (4753 chiavi);
> - note di X: `plugin-secrets-check` 11, `config-instance-key` 151, `app-lifecycle` 44, `config-package` 695 (ora
>   verde: dentro c'è la cura di Z del treno 93), `config-audit` 90;
> - doc: `mkdocs build` rigoroso senza avvisi, `check-links` 97. `translate-validate --file admin/configuration.en.md`:
>   192 errori e 501 avvisi, il debito noto (174 e 474 a CP7b-2), più le righe nuove di questa notte e di altri;
> - porta 6181 libera.

#### H-17 — passo 2, rossi, cura e verdi ✅ (2026-10-16, mattina)

> **Prove**: `services profile-defaults` sul codice di prima: 15 rossi (6 «ENVIRONMENT_PROFILE_DEFAULTS is missing», 9
> «profile_default is missing»), 37 verdi. Poi `apply_h17.py`, ruff e black puliti, e i verdi: `profile-defaults` 52,
> `config-package` 695, `config-env-example` 38. La doc di `settings.md` era già nel `mkdocs build` delle 06:59.

### TS1 — i test speculari: numeri aggiornati e proposta (2026-10-16, mattina) — sola lettura

Voce 7 di H nel piano generale, decisione aperta n. 13: si decide a riordino del backend finito, con i numeri in mano.
Richiesta del coordinatore (07:10): l'analisi del prossimo elemento, in sola lettura.

**Numeri di oggi** (HEAD `7caa98c20`; tra parentesi quelli di §13, del 14/10):

- 358 file di test (266): `test_api` 70 (58), `test_services` 200 (141), `test_utilities` 47 (34), `test_db` 16 (10),
  `test_schemas` 12 (11), `test_external` 7, `test_e2e` 2;
- il runner codifica 327 percorsi di test distinti (236);
- l'app ha 322 moduli di servizio in 22 pacchetti, più qualche modulo sciolto in `services/`;
- uno specchio esiste già, solo per la finanza: `test_services/test_financial/` (27 file, più `test_portfolio_engine/`
  con 15) e `test_services/test_financial_math/` (7).

**Cosa costerebbe lo specchio** (`test_services/<pacchetto>/` come `backend/app/services/<pacchetto>/`):

- circa 150 spostamenti da `test_services/`, e la stessa cosa per `test_api/` (70) se lo specchio si estende alle rotte;
- riscrivere le voci del runner, fino a 327 stringhe (una superficie condivisa), più la doc dei test,
  `backend-testing.instructions.md`, la skill `testing-backend` e le istruzioni del `test-author`;
- un conflitto per ogni sessione aperta. Oggi A7, B3/B5, X CP13 e FE5c, E5b, Z, W, J e Y aggiungono o cambiano test
  in queste cartelle: uno spostamento in mezzo ai loro lotti vuol dire file ricreati al posto vecchio e voci del runner
  da rifare a ogni treno;
- nessun guadagno di comportamento: il runner elenca i percorsi uno per uno, pytest non cambia nulla. Si guadagna solo
  nel trovare un test accanto al suo modulo.

**Proposta**:

- **nella 1.3, no**. Restano la struttura piatta e la regola `test_<modulo>.py`. Niente sottocartelle nuove: le due
  della finanza restano dove sono, senza estendere lo schema, così non ci sono due posti in cui cercare;
- **dopo il tag 1.3.0**, se il developer vuole la vicinanza: un lotto solo, scritto da uno script, in una finestra senza
  sessioni parallele, con le regole P2. Prima la rinomina (`git mv` più le voci del runner riscritte dallo script), poi
  il resto; grep dei vecchi percorsi a zero, `all-backend`. Stima: una sessione di poche ore;
- **decisione del developer** (n. 13). Il mio default è il no nella 1.3.

> **Esito**: il coordinatore porta TS1 al developer come **P23**, con la mia proposta.

### Lotto «b-doc-notes»: B-4 e B-5 (2026-10-16, mattina) — in corso

Via del coordinatore (07:13): due lotti di sola scrittura in commit separati. Questo e poi H-1, H-4, H-6, H-9; prove
leggere come al solito. Le due voci erano di B (piano 07, §13 B6a) e il coordinatore le ha passate ad H il 15/10.

> **Note implementazione**:
>
> - io: il commento in testa a `docker-compose.yml` mette `backup` fra i comandi che funzionano nell'immagine, con
>   l'esempio `./dev.py docker exec backup create`. Nessun test ne fissa il testo. Il file è di B dopo CP7a, ma la voce
>   l'ha assegnata il coordinatore;
> - io: l'ancora `{: #what-to-back-up }` sul titolo «✅ What to Back Up» di `admin/filesystem` nelle 4 lingue
>   (`en`, `it`, `fr`, `es`). I titoli tradotti avevano slug diversi;
> - in corso, docs-writer, solo inglese:
>   - `docker_advanced.en.md#docker-exec`: `backup`, più un rimando a `backup create` nella sezione del backup manuale;
>   - `admin/index.en.md`: la riga della CLI;
>   - `filesystem.en.md`: il rimando alla CLI, la nota su `backups/`, `backups/` nell'albero;
>   - `cli_tools.en.md`: il link verso `filesystem.md#what-to-back-up`.

> - docs-writer, fatto: le quattro pagine inglesi come sopra, più l'avviso sui permessi di `filesystem.en.md`, che ora
>   nomina anche `backups/` e `.restore/`. `ensure_private_dir` li crea `0700`, gli archivi sono `0600`: con Docker e
>   un altro utente sull'host, copiare o cancellare un archivio dà `Permission denied`, e si usa `sudo cp -a` o
>   `sudo rm`. Ogni fatto è verificato sul codice.
>
> **Prove leggere** (07:28–07:31): `mkdocs build` rigoroso senza avvisi, `check-links` 97. `translate-validate`:
> `filesystem` 27 errori, `docker_advanced` 42, `index` 15, debito già esistente compreso. Annotato in H-5, con l'ordine
> di traduzione: insieme a B-7 o dopo.

### Lotto H-1, H-4, H-6, H-9 (2026-10-16, mattina) — in corso

> **Note implementazione**:
>
> - **H-1** ✅ (io): corrette 12 pagine vive della devWiki, con i percorsi di oggi:
>   - `services/platform/scheduler/`;
>   - `services/files/static_uploads.py`;
>   - `config/__init__.py`;
>   - `api/v1/system/connection.py` per l'indirizzo di F-102;
>   - `api/v1/system/info.py` per i tre campi di `docker-system-info-missing-deps`;
>   - la riga «(planned) … (not yet created)» di `domains/scheduler.md`, ora vera;
>   - l'albero di `entities/market-data-scheduler.md`.
>
>   Restano come sono, perché raccontano lo stato di allora: le pagine `sources/` (`phase00-brim-danske-bank`,
>   `r2-parallel-features-pwa-borsa-fx`), `features/F-078.md:34` e `decisions/port-6040-scheme.md:34` («were
>   updated»).
>
>   `check_source_paths.py`: nessun percorso nuovo che manchi. I 5 segnalati sono cartelle generate (coverage, output
>   delle sonde) assenti in un worktree nuovo, ed esistevano già prima;
> - **H-4** (cura in `/tmp/librefolio-r13-h-hsmall/apply_h4_h9.py`, provata a secco, ruff e black puliti). In Python
>   3.13 `Path.exists()` ignora solo ENOENT, ENOTDIR, EBADF ed ELOOP (`pathlib/_abc.py`), quindi un EACCES esce. Con
>   `sqlite/` senza attraversamento, `rglob` lo salta in silenzio e poi `nearest_existing(sqlite/app.db)` solleva. La
>   cura: un `OSError` diventa `ValueError("Cannot verify test data path: <relativo> (<strerror>)")` nel ciclo dei
>   percorsi gestiti, e `ValueError("Cannot verify the test data directory: …")` nel controllo degli indicatori
>   degli antenati. Resta fail-closed;
> - **H-9** (stessa patch): `handler.close()` su ogni gestore tolto. `pytest.ini` non ha un `log_file`, quindi chiudere
>   anche i gestori di pytest non perde niente: un `FileHandler` chiuso in modo `w` non si riapre, e uno `StreamHandler`
>   non chiude il suo stream;
> - **H-6**: in corso, test-author, insieme ai rossi di H-4 e H-9.

> **Ingresso del primo lotto**: `b-doc-notes` committato (`d7eb9c5f3`, diario `881bd20c0`), HEAD `881bd20c0`.

#### Lotto H-1, H-4, H-6, H-9 — rossi, cura, verdi ✅ (2026-10-16, mattina)

> **Note implementazione** (test-author, niente lanciato da lui):
>
> - **H-4**, in `test_runtime_isolation.py`, 3 test. `sqlite/` e `secrets/` con modo 000 (dentro, `app.db` e
>   `instance.key`), più la radice dei dati di test con modo 000, per il controllo degli indicatori. Si aspettano un
>   `ValueError` con il prefisso e il percorso, e come causa un `PermissionError`. Saltati da root o su Windows; il modo
>   viene ripristinato in un `finally`;
> - **H-6**, in `AboutTab.test.ts`: i due casi d'assenza ora usano `/settings\.assetProviders/` e i loro gemelli per gli
>   FX e gli import, cinque controlli in tutto, ciascuno con un controllo positivo prima. L'intestazione è
>   «etichetta (n)», quindi il testo esatto non trovava mai nulla. Ora un `{#if assetProviders}` sbagliato li farebbe
>   diventare rossi;
> - **H-9**, sezione (e) di `test_logging_access_filter.py`, 2 test: dopo una seconda chiamata il file di log della
>   prima è chiuso, e un `FileHandler` trovato sulla radice viene chiuso. I file stanno sotto `tmp_path`;
> - io: la descrizione e il commento di `logging-access-filter` nel runner (i file di log della sezione (e) stanno sotto
>   `tmp_path`; H-9).
>
> **Prove**, una alla volta, `nice`:
>
> - rossi (07:41–07:42): `utils runtime-isolation` 3 rossi su 200 («a raw PermissionError escape instead of refusing
>   with a ValueError»); `services logging-access-filter` 2 rossi su 98 (il gestore resta aperto); Vitest `AboutTab` 38
>   verdi, come deve essere per una riparazione;
> - cura applicata (`apply_h4_h9.py`); ruff, black e prettier puliti;
> - verdi (07:45–07:51): `runtime-isolation` 200, `logging-access-filter` 98, `AboutTab` 38, `config-instance-key` 151,
>   `secret-masking` 68, `config-misc` 12, `config-package` 695, `utils dev-cli-db-path` 15. Porta 6181 libera.
>
> **⚠️ Fuori pista**:
>
> - durante i verdi il carico è salito fino a 137, per le corsie degli altri; i miei risultati sono comunque verdi. Dalle
>   07:47 la soglia per le prove leggere è **sotto 50**, con attese di 60 s: aggiornati i miei script;
> - effetto di H-9 notato dal test-author: le chiamate a `configure_logging()` in (d) e in `test_secret_masking.py`
>   non svuotano prima la radice, quindi chiudono anche i gestori di pytest. Oggi non fa danno, perché `pytest.ini` non ha
>   `log_file`; con `pytest --log-file` quel file smetterebbe di ricevere righe dopo il primo test così.

> **Ingresso del lotto 2**: committato (`60f41e18e` fix, `c1ecdc389` test, `1235dd414` wiki, `811ccc4bf` diario), HEAD
> `811ccc4bf`. `all-backend` per tutti i lotti nello slot 1 dopo A7a, verso le 09:30.

### H-3, il resto: niente chiave nuova in silenzio quando il DB ha segreti — analisi (2026-10-16, mattina) — sola lettura

**Oggi** (HEAD `811ccc4bf`):

- chi chiama `derive_key()`:
  - le impostazioni dei plugin (`settings_subkey()` e `fingerprint_subkey()` nel resolver, e `plugin_secrets_key_status`
    di X), con le sole righe cifrate dell'istanza, ognuna col suo `key_id`;
  - il probe dell'indirizzo di A, che non salva nulla. `verify_probe_nonce` tollera una chiave inutilizzabile e
    risponde `False`; `issue_probe_nonce` no;
- gli archivi di B non contengono la chiave (`ManifestInstanceKey.included`, falso). Solo un archivio protetto da password
  potrà contenerla (B4);
- lo scenario: dati ripristinati senza `secrets/`, oppure il file della chiave cancellato. Da H-15 la prima derivazione
  la fa il passo `plugin-secrets-check`, perché la funzione di X deriva quando ci sono righe. La chiave nuova nasce
  quindi all'avvio, e il log ha l'errore col conteggio;
- il rischio che resta: se l'amministratore, prima di accorgersene, inserisce di nuovo dei segreti, questi vengono cifrati
  con la chiave nuova. Rimettere poi la vecchia chiave rende illeggibili proprio quelli. Lo avvisa solo il log.

**Opzione A, la cura vera: nessuna chiave nuova in silenzio se il DB ha segreti.**

- In `plugin-secrets-check`: se `instance_key_status().source == "not_created"` e il DB ha righe con un segreto
  (contate senza derivare), il passo non chiama la funzione di X. Scrive un errore: «il file della chiave manca, ma N
  segreti salvati sono cifrati con una chiave: rimetti `secrets/instance.key`, oppure `./dev.py instance-key new` per
  ripartire con una chiave nuova, e quei segreti vanno inseriti di nuovo». Poi chiama
  `instance_key.forbid_generation(reason)`: per il resto del processo `_instance_key()` solleva `InstanceKeyError`
  invece di creare il file.
- Effetti: le impostazioni dei plugin si comportano come con una chiave inutilizzabile, come X ha già documentato
  (`unreadable` nel catalogo, chiamate senza segreti, scritture con un segreto a 503, un errore nel log).
  `POST /users/address-probe` di A darebbe 500: è un buco che c'è già (H-19). A dovrebbe rispondere 503.
- Il self-hosted resta com'è: cambia solo uno stato già guasto. Un'installazione nuova genera la chiave al primo uso,
  come oggi. Una chiave configurata non può sparire in silenzio: se è inutilizzabile, l'avvio si ferma.
- Superfici: `instance_key.py` (il divieto), `plugin_secrets_check.py` (il ramo), un comando CLI `instance-key new`
  (`dev.py`, superficie condivisa), la doc admin (`configuration`, «The Instance Key» e «Startup Checks», con debito di
  traduzione) e `security.md`, i test (il divieto, la CLI, l'installazione nuova invariata). Peso: un lotto
  piccolo-medio.

**Opzione B, solo doc**: si tiene H-15 com'è e si scrive l'ordine giusto, cioè rimettere il file della chiave **prima**
di inserire di nuovo i segreti, nella riga ❌ di «Startup Checks» e in «The Instance Key». Rischio zero.

**Proposta**: la B adesso, la A come lotto se il developer la vuole nella 1.3, insieme alla piccola correzione di A
(H-19). Per il cloud cambia poco: le istanze gestite hanno una chiave configurata, e un cambio di chiave lo segnala già
H-15. È decisione del developer, perché cambia il comportamento di uno stato guasto e aggiunge un comando.

> **Esito**: il coordinatore vuole **l'opzione B subito** (solo doc, commit separato). L'opzione A va nella lista del
> developer come **P24**; H-19 passa ad A, per il suo backlog, prima di un'eventuale A.

#### H-3, opzione B: l'ordine giusto nella doc ✅ (2026-10-16, mattina)

> **Note implementazione**:
>
> - docs-writer, verificando sul codice: salvare un segreto riscrive `secret_ciphertext` e `key_id` della riga
>   (`plugin_settings/service.py`). In `admin/configuration.en.md`:
>   - il punto dell'avviso di «🗝️ The Instance Key»;
>   - la riga ❌ `platform.plugin_secrets` di «Startup Checks», ora in ordine: prima la chiave vecchia, a LibreFolio
>     fermo, e solo senza una copia i segreti inseriti di nuovo;
>   - «Saved Secrets and the Instance Key», che diceva «enter them again» senza condizioni.
>
>   In `developer/architecture/security.md` una frase nel paragrafo «A lost key file»;
> - io: il punto ⛔ di `admin/filesystem.en.md` («Never edit, replace or delete `instance.key`») contraddiceva
>   l'ordine nuovo, cioè rimettere la copia al posto della chiave generata. Ora dice «the `instance.key` in use», e
>   rimette la copia a LibreFolio fermo, prima di inserire di nuovo un segreto.
>
> **Prove** (08:03): `mkdocs build` rigoroso senza avvisi, `check-links` 97. Debito di traduzione: `configuration`
> (tre punti) e `filesystem` (un punto), senza timbro.
>
> **Da girare a X**: dicono ancora «enter it again» senza l'ordine il suggerimento della UI
> (`frontend/src/lib/i18n/pluginSettings/en.json:31`) e `user/settings/plugins.en.md:117`.

> **Ingresso di H-3 B**: committato (`481a93f1c`, diario `498c5d623`).

### `all-backend` di tutti i lotti aperti (2026-10-16, mattina) — in corso

Lotti: note di X, card del backup, H-17, `b-doc-notes`, H-1/4/6/9, H-3 B. Il coordinatore ha aggiornato la base con il
dev del mattino (`d5c3c3ae3`: E5b, Y, J CP-10a, W, i lotti di T), senza conflitti: HEAD `9ddecbde0`, slot 1.

> **⚠️ Fuori pista — lo stop e il riavvio**:
>
> - il primo giro (dalle 08:34, `--workers 2`, `nice`) ha ricostruito il frontend in debug e il sito MkDocs, cambiati
>   con la base. Alle 08:46:39 si è fermato per un SIGINT arrivato da fuori (uscita 130, `KeyboardInterrupt` nel
>   runner), prima che partisse un solo test: nessun risultato. Porta 6181 libera, verificato dallo script;
> - alle 08:49 lo stop chiesto dal developer: nessun comando, worktree lasciato com'era (pulito);
> - alle 10:03 la macchina si è riavviata, e macOS svuota `/tmp` al riavvio. Sono spariti gli script, le patch già
>   applicate, i log della notte e la cartella dati della corsia, `/tmp/librefolio-r13-h`. Non si perde niente: il
>   lavoro è committato e le prove sono già in questo piano. Il runner ricrea la cartella da sé, come alla prima prova
>   del 14/10;
> - alle 10:32 il coordinatore riprende. Dopo il controllo (HEAD `9ddecbde0`, worktree pulito, porta libera, nessun
>   processo rimasto della corsia), il secondo giro parte alle 10:33 con `--fresh-run`. Script e log ora sono in
>   `/tmp/librefolio-r13-h-runs/`.

> **Esito del secondo giro** (10:33–11:11, HEAD `9ddecbde0`, `--workers 2`, `nice`): **18 266 passati, 7 saltati, 5
> falliti**; 5 categorie su 7 verdi. Log nella cartella della sessione (`files/runs/allbackend-1033/`). Porta 6181
> libera.
>
> **Triage dei 5 rossi** (skill `test-triage`, prima le prove e poi i rilanci):
>
> - tutti e 5 sono `httpx.ReadTimeout` del client del test, che aspetta al massimo 30 s (`TIMEOUT` dei due file), su due
>   rotte lente per natura:
>   - `e2e search-to-prices`, 3 casi, `GET /assets/provider/search` («World», «Apple», «iShares Core MSCI World»);
>   - `api brim`, 2 casi di `TestParseEndpoint`, `POST /brokers/import/files/{id}/parse`;
> - §1, la forma della risposta: non si applica, perché non è arrivata nessuna risposta da confrontare;
> - §2, il tempo: la ricerca dà a ogni fornitore fino a 30 s (`core.call_provider(..., timeout=30.0)` in
>   `services/assets/search.py`), e dopo un risultato vuoto anche il link-finder. Il limite del test è uguale a quello del
>   prodotto, senza margine. Alle 11:13 Yahoo rispondeva 429 a una prova con `curl`; JustETF e Borsa Italiana
>   rispondevano in meno di 1 s. Il parse BRIM lavora nel pool di processi: era il primo giro dopo il riavvio, a cache
>   fredda, e alle 10:45 il carico era a 78 per gli slot pesanti degli altri;
> - rilanci da soli (11:13–11:18, `db populate --force` prima, carico intorno a 45): `api brim` **118 passati** (in
>   158 s), `e2e search-to-prices` **3 passati** (in 20 s);
> - nessuno dei due percorsi passa dal codice dei miei lotti. La ricerca è di X, il parse BRIM è di W.
>
> **Verdetti**:
>
> - ricerca: **assumption**. Il test fissa 30 s, quanto il limite di un solo fornitore nel prodotto, quindi una ricerca
>   corretta con un fornitore lento o rallentato dal 429 lo supera. Cura per X: un limite del client sopra quello del
>   prodotto (30 s più il link-finder, con margine). Da valutare anche se la ricerca vuole un limite complessivo, perché
>   oggi un utente può aspettare più di 30 s quando un fornitore si blocca;
> - parse BRIM: **slowness** sotto concorrenza, da confermare da W con i tempi del primo parse dopo l'avvio, a pool
>   freddo. Voce sua, non da curare in un rosso.
>
> I 7 saltati (stanotte erano 4): i miei 3 casi di H-4 saltano solo da root, su Windows o se il permesso non si può
> togliere, e alle 07:45, da soli, erano passati tutti (200 su 200). La conferma sulla revisione combinata è nelle prove
> leggere che seguono.

> **Esito accettato dal coordinatore** (11:2x): i 5 timeout non sono miei. La ricerca va a X e il parse BRIM a W, li gira
> lui; nessun giro pulito in più. I lotti entrano appena le prove leggere sono verdi.
>
> **Prove leggere sulla revisione combinata** ✅ (HEAD `9ddecbde0`, una alla volta, `nice`, ciascuna partita col carico
> sotto 50, 11:36–11:54; il carico era salito fino a 142 per gli slot degli altri):
>
> - `front check`: svelte-check 0 errori, 0 avvisi;
> - Vitest `InstanceBlockedPage.test.ts`: 36 su 36;
> - `utils runtime-isolation untraversable`: **3 passati**, 197 deselezionati. I casi di H-4 girano e non saltano;
> - porta 6181 libera.
>
> **I 7 saltati di `all-backend`** (erano 4 a CP7b-2): i miei 3 casi di H-4 girano in questo ambiente (sopra). L'unico
> altro punto di salto nuovo, nel delta della base `887c6dd12..9ddecbde0`, è il `pytest.skip` parametrizzato di
> `test_provider_contracts.py` (X): uno per ogni fornitore che non traduce parametri. Molto probabilmente vengono da lì;
> l'elenco esatto dei saltati non c'è, perché i log sono in `-q`.

### I lotti pronti a entrare (2026-10-16, mattina)

Diciassette commit fuori da `dev_release2`, più questo diario: note di X (H-14/15/16), card del backup sulla pagina di
blocco, H-17 (la mia parte), `b-doc-notes` (B-4, B-5), H-1/4/6/9, H-3 opzione B. Nel backlog, all'ingresso il
coordinatore chiude con ✅ H-1, H-4, H-6, H-9, H-14, H-15, H-16. H-17 resta aperta fino alle due righe di B. H-3 resta
aperta per l'opzione A (P24). Restano aperte anche H-5 (traduzioni), H-18 (sezione C, la UI comune) e H-19 (ad A).

> **Ultima validazione e ingresso**: il coordinatore ha committato il diario (`306554879`) e fuso `dev_release2` (merge
> `0d7503098`, pulito: J CP-7a, W-B17, Z7c-1, i ruoli di T). Sulla revisione combinata, una alla volta, carico sotto 50
> (12:03–12:43): `api sync`, `front check` 0/0, Vitest `InstanceBlockedPage` 36, `db populate --force`,
> `api instance-block` 62, `api system` 118. **Entrati nel treno 110** (merge `0ecc5ed27`, registro `0f3b9e3db`),
> con 🔒/✨ per H-15 e la card, e due righe 📚 (`34e1e8092`). Chiuse H-1, H-4, H-6, H-9, H-14, H-15, H-16. Base portata
> avanti con fast-forward a `0f3b9e3db`, eseguito dal coordinatore: le mie regole mi vietano di muovere la storia.

### P17 — l'indirizzo del client dietro un proxy fidato (2026-10-16, pomeriggio) — in corso

Decisione del developer (P17): nel cloud l'indirizzo vero del visitatore si legge da `Fly-Client-IP`. Oggi i limiti per
client (le email di registrazione di E5b, i login falliti di A) vedono solo il proxy di Fly e contano tutti i visitatori
insieme. Il contratto l'ho mandato alle 12:4x e il coordinatore l'ha approvato, **compreso il punto 4**, come sua
decisione da far rivedere al developer.

**Il contratto approvato**:

- `LIBREFOLIO_CLIENT_IP_HEADER`, un campo di `Settings`, vuoto di default e validato all'avvio. Deve essere il nome di
  un header (token HTTP); `X-Forwarded-For` e `Forwarded` sono rifiutati;
- **nessuna voce in `PROFILE_DEFAULTS["managed"]`**: il cloud la imposta nel suo ambiente, come
  `LIBREFOLIO_IDLE_SUSPEND_MODE=fly`;
- `services/platform/client_address.py`:
  - `client_address(request)`: con la variabile vuota, `request.client.host` com'è oggi. Con la variabile impostata e
    l'header presente una volta con un solo IP, quell'IP normalizzato. Senza header, il peer. Con un header malformato,
    il peer e un avviso una volta per processo, mai col valore;
  - `client_rate_key(address)`: la regola di oggi di E (`flows.address_key`). E la toglie dal suo codice nel suo lotto,
    senza shim; fino ad allora le copie sono due, ed è previsto;
  - `mask_client_address(address)`, per il log: IPv4 per /24, IPv6 per /48;
- doc secondo C-99. La spiegazione intera va in `admin/connection_checks.en.md`, «Behind a Reverse Proxy» (pagina con
  traduzioni); una riga in `admin/configuration.en.md`, una riga del cloud in `hosting_providers.en.md`, poi
  `.env.example` e `security.md`;
- chi la chiama, nei propri lotti dopo il mio: E (`api/v1/email.py:157`, `:203`, `auth.py:274`, `address_key`) e A (il
  limitatore dei login falliti).

**Fatti verificati**:

- uvicorn parte coi default (`Dockerfile`: `proxy_headers`, `FORWARDED_ALLOW_IPS=127.0.0.1`), quindi su Fly il peer è
  il proxy;
- la doc di Fly («Request headers») dice che il proxy imposta `Fly-Client-IP` e sovrascrive quello mandato dal client,
  mentre `X-Forwarded-For` si può falsificare;
- `api/v1/system/connection.py` e `utils/runtime/network.py` restano come sono: classificano l'indirizzo dall'ultimo
  `X-Forwarded-For` solo per dare un consiglio, non per una decisione di sicurezza.

**⚠️ Fuori pista**: la riga del docstring di `instance_block.py` per `POST /api/v1/auth/setup` (P16(d)) descriverebbe
una rotta che a `0f3b9e3db` non esiste ancora: A7 non è entrato. La scrivo quando A7 è nella mia base.

#### P17 — passo 1, rossi ✅ (2026-10-16, pomeriggio)

> **Note implementazione** (test-author, niente lanciato da lui): `test_client_address.py`, nuovo, 21 funzioni e 131
> casi, registrato come `services client-address` (`isolation="pure"`). Coprono il campo (vuoto, valori accettati e
> rifiutati, le liste `X-Forwarded-For` e `Forwarded` con `FORWARDED_ALLOW_IPS` nel messaggio, nessun profilo che lo
> imposta) e `client_address()`: variabile vuota, un solo IP normalizzato, header assente, i malformati con un solo
> avviso che non contiene mai il valore, nome senza distinzione di maiuscole, WebSocket, lettura una sola volta e
> `reset_client_address_cache()`. Più `client_rate_key()` e `mask_client_address()`, con valori espliciti.
>
> **Rossi** (13:09–13:11): 131 falliti, 34 sulla barriera del campo e 97 su quella del modulo. Ruff e black puliti.

#### P17 — passo 2, la cura e i chiamanti (2026-10-16, pomeriggio) — verdi in corso

> **⚠️ Fuori pista**: il docs-writer ha visto che la variabile, da sola, non avrebbe fatto niente. I tre punti che
> contano per client leggevano `request.client.host`, quindi le pagine admin avrebbero detto una cosa falsa. Al
> coordinatore ho proposto due strade, e ha scelto la (1) (13:07): cambio io solo le tre chiamate. Ha verificato che
> E4b (`b22747e52`) e A (`946285a91`) hanno quelle righe uguali, solo spostate; E4b aggiunge `flows as email_flows`
> agli import di `auth.py`, quindi al merge si risolvono righe vicine, non il significato. I test API di E e della
> registrazione li lancio io. Il limitatore dei login falliti non esiste ancora: tolto dai testi.
>
> **Note implementazione** (`files/p17/apply_p17.py` della sessione, provato a secco, ruff e black puliti):
>
> - `config/__init__.py`: `import re`, `_HEADER_TOKEN` e `_LIST_HEADERS`, il campo `LIBREFOLIO_CLIENT_IP_HEADER` col
>   validatore `after` (spazi tolti, vuoto ammesso, token HTTP, liste rifiutate, maiuscole conservate). La docstring
>   del modulo lo elenca;
> - `services/platform/client_address.py`, nuovo: il nome dell'header è letto una volta (`functools.cache`),
>   l'avviso una sola volta per processo (una lista come flag, sul modello del resolver di X),
>   `reset_client_address_cache()`, `client_rate_key()` (la regola di `flows.address_key`, nella sua casa nuova),
>   `mask_client_address()`;
> - `.env.example`: la sezione «The Visitor's Address Behind a Reverse Proxy», con la riga commentata e il rimando
>   alla doc;
> - le tre chiamate: `api/v1/email.py` (le due letture `address = request.client.host if request.client else None`)
>   e `api/v1/auth.py` (`registration_email_allowed`), più un import ciascuno;
> - doc (docs-writer, secondo C-99): la sottosezione `#client-address` in `admin/connection_checks.en.md`, con la
>   regola di sicurezza in un riquadro e corretto l'ultimo paragrafo dei «Limits», che diceva che non c'erano proxy
>   fidati da configurare; una riga in `admin/configuration.en.md`; un punto in `admin/hosting_providers.en.md`; la
>   sottosezione `#client-address` in `developer/architecture/security.md`, che io ho corretto sui chiamanti dopo la
>   strada (1). Le pagine solo inglesi puntano a `connection_checks.md#reverse-proxy`, perché `#client-address` non
>   esiste ancora nelle traduzioni.
> - Fly: la doc ufficiale «Request headers» dice che il proxy imposta `Fly-Client-IP`; che sovrascriva quello del
>   client lo dicono fonti esterne. Resta la prova di accettazione del cloud già nel contratto.
>
> **Il ruff della prova a secco**: segnalava I001 sui due import solo perché il modulo nuovo non esisteva ancora nel
> worktree, e quindi non lo riconosceva come modulo del progetto. Applicata la cura, è pulito senza `--fix`.

> **Verdi parziali** (13:11–13:23, una alla volta, carico sotto 50): `services client-address` **131**,
> `config-env-example` 38, `config-package` 694, nessun fallito.
>
> **⏸️ Pausa del developer** (13:22): ho fermato solo lo script che mette in fila le prove (PID 48197, con `kill`), e ho
> lasciato finire il test in corso (`config-package`). Porta 6181 libera. **Restano da lanciare**: `services
> profile-defaults` e `config-misc`; `db populate --force`; `api email`, `email-verification`,
> `email-verification-hooks`, `registration` e `auth`; `mkdocs build` e `check-links`. Lo script è
> `files/runs/p17.sh green` nella cartella della sessione: rilancia anche i tre già verdi. Poi l'handoff, FROZEN.
> Worktree sporco col lotto P17, nessun merge aperto, HEAD `0f3b9e3db`.

> **Ripresa** (14:14, via del developer). B conferma: `RestoreCard` è un componente a parte, montato solo in
> `BackupTab`; la pagina di blocco tiene solo `BackupDownloadCard`, come vuole P7.
>
> **Verdi** (14:14–14:40, una alla volta, carico sotto 50, HEAD `0f3b9e3db`):
>
> - `services profile-defaults` 52 e `config-misc` 12;
> - `db populate --force`, poi `api email` 160, `email-verification` 49, `email-verification-hooks` 16,
>   `registration` 96 e `auth` 88. Sono le rotte con le tre chiamate cambiate: con la variabile vuota, il
>   comportamento di prima;
> - `check-links` 97;
> - insieme ai verdi di prima della pausa: `client-address` 131, `config-env-example` 38, `config-package` 694.
>
> **⚠️ Fuori pista — `mkdocs build` rigoroso rosso, non per il lotto**: un solo avviso, in
> `developer/backend/transactions/wac.md`, il link `split_promote.md#transfer-giving-leg` verso un'ancora che non
> esiste. Il link l'ha messo `54880598b` («fix(transactions): emptied manual cost basis…», treno 111), che è già nella
> base `0f3b9e3db`; io quelle pagine non le tocco. Visto che la build dà solo quell'avviso, le mie quattro pagine non
> ne aggiungono. Va girato al proprietario delle pagine delle transazioni.
>
> **H-5**: aggiunto il debito di traduzione di P17, `connection_checks` e `configuration`, con l'ordine.

#### Checkpoint P17 🧊 (2026-10-16, pomeriggio) — FROZEN, in attesa del coordinatore

> **Ingresso**: P17 committato (`22d6dc84e` feat, `551843bdc` doc, `55a6646ff` diario) e fuso in dev (merge
> `b1df87bd4`, pulito). L'avviso di `mkdocs` in `wac.md` è stato corretto su dev (`ed500643f`). A B5c il coordinatore
> ha chiesto chi scrive la voce `GET /backup/restore/outcome` in `instance_block.py`: la scrive B, nello stesso commit
> della rotta, e io rivedo il diff (ticket confrontato a tempo costante, una volta sola, senza ticket la stessa risposta
> di una rotta che non esiste, solo `{state, reason, waiting}`).

### TC-16 — `FilePreviewModal.test.ts:598`, rosso sotto carico (2026-10-16, pomeriggio) — triage

Viene dai colori: due rossi in un giro con carico fra 41 e 52, verde da solo (37 su 37). Me l'ha dato il coordinatore
come voce H, con il triage prima di tutto.

> **Prove** (skill `test-triage`):
>
> - la riga 598 è il primo `expect` del `waitFor` di `listening()`, nel `describe` «PDF stage state (fake EmbedPDF)».
>   Aspetta che il visore finto abbia registrato i tre ascoltatori del componente, e 14 casi la usano. Il `waitFor` non
>   ha un budget, quindi vale quello di default di testing-library, 1 s;
> - la catena del componente (`FilePreviewModal.svelte`, ~206–232) non ha ritardi fissi: `Promise.all` di due
>   `import()` dinamici (`@embedpdf/snippet` e `pdfViewerAssets`), `pdfViewerAssets(document.baseURI)`,
>   `EmbedPDF.init`, `await viewer.registry`, poi le iscrizioni;
> - il file da solo (15:11, carico 47, `--reporter=verbose`): 37 su 37. I casi del `describe` durano fra 66 e 276 ms; i
>   primi tre (247, 186, 276 ms) sono i più lenti, perché pagano il riscaldamento dei primi `import()` dinamici del file.
>   Il margine di 1 s è quindi circa 4 volte la durata da solo. Nel giro dei colori, con i worker paralleli di Vitest e
>   la macchina carica, la catena lo supera.
>
> **Verdetto: assumption, il tempo** (§2). La condizione aspettata è quella giusta: il test deve sincronizzarsi col
> visore finto prima di mandargli i suoi segnali. Il budget invece è una scommessa sulla velocità della macchina. Non
> c'è uno stato del prodotto da rendere osservabile (§6): quello che vede l'utente, `data-state`, resta `loading` sia
> prima sia dopo le iscrizioni.
>
> **Cura proposta**, solo nel test:
>
> 1. un `beforeAll` nel `describe` che importa una volta `@embedpdf/snippet` e `pdfViewerAssets`, così il riscaldamento
>    si paga fuori da ogni attesa (l'hook ha il suo limite);
> 2. un budget esplicito per le attese della catena del visore nello stesso `describe` (`listening()` e i `waitFor`
>    delle righe ~781, ~795, ~825, ~856): una costante da 3 s, oltre 10 volte il caso più lento misurato da solo, e
>    dentro i 5 s di un test.
>
> Il file sta in `features/files/**`, l'area T dei colori: prima di scriverci chiedo l'OK al coordinatore. La
> riparazione la fa il test-author.

> **Via del coordinatore** (15:19): sì, solo nel test, col test-author. Avvisa lui i colori.
>
> **Note implementazione** (test-author, niente lanciato da lui), solo `FilePreviewModal.test.ts`, nel `describe` «PDF
> stage state»:
>
> - `const VIEWER_WAIT = {timeout: 3_000}`, con il perché nel commento (66–276 ms da solo, 1 s dava un margine di circa
>   4 volte, 3 s più di 10 volte, dentro i 5 s di un test);
> - un `beforeAll` che importa una volta `@embedpdf/snippet` e `pdfViewerAssets`. Sono mock, il secondo parziale con
>   `importOriginal`, e caricarli prima non cambia quello che i test vedono: `pdfViewerAssets.ts` al caricamento
>   definisce solo costanti;
> - `VIEWER_WAIT` su `listening()`, sulle due attese di `registryAsks`, su quella di `tiles` di lunghezza 2 (il secondo
>   visore dopo il `rerender`) e su `findByTestId('file-preview-pdf-fallback')`. Quest'ultima non era nella mia lista,
>   ma aspetta il ramo d'errore della stessa catena: la accetto;
> - lasciata col default l'attesa di `onRequestClose` (~838). Il suo ascoltatore si registra nello stesso passo
>   sincrono dei tre, quindi passa al primo controllo e il tempo non c'entra;
> - limite noto: 3 s valgono per un'attesa, non per un caso. «Stays open when it moves to another file» ha due attese
>   della catena; la seconda trova però i moduli già caricati.
>
> **Prove**: `prettier --check` pulito. Il file da solo (15:33, carico 42): 37 su 37, e i casi del visore ora durano
> 56–135 ms (prima 66–276). Il riscaldamento è uscito dalle attese. Resta la prova a carico crescente, in una finestra
> leggera del coordinatore.

> **Prova sotto carico** (slot 2, 16:03–16:13, chiusura alle 16:15, senza aspettare il carico apposta: nello slot 1
> girava l'`all-backend` di MF):
>
> - `front-utility component-unit` n. 1: **4041 su 4041**, 359 s, carico salito da 46 a circa 106;
> - `front-utility component-unit` n. 2: **4041 su 4041**, 194 s, carico intorno a 66;
> - `FilePreviewModal.test.ts` è nel catalogo (`_frontend_utility.py:285`), quindi i suoi 37 casi sono girati due volte
>   coi worker paralleli e un carico oltre il doppio di quello del giro dei colori (41–52);
> - i tre giri del file da solo non sono partiti: alle 16:13:07 il controllo dello script ha visto troppo vicina la
>   chiusura. Restano le due prove leggere di prima (15:11 e 15:33);
> - slot liberato alle 16:13; porta 6181 libera.
>
> **Verdetto confermato**: assumption, il tempo; curato nel test.

#### Checkpoint TC-16 🧊 (2026-10-16, pomeriggio) — FROZEN, in attesa del coordinatore

> **Ingresso**: TC-16 committato (`03e06e3bd`, `91cfe34b3`) e fuso in dev (merge `65fc63e7e`).

### Cosa resta del piano H — analisi (2026-10-16, pomeriggio) — sola lettura

Richiesta del coordinatore (16:14): proporre un lotto con quello che resta del piano, dire cosa serve dal developer per
CP7a, e dire lo stato di C-96. HEAD `91cfe34b3`.

- **C-96 è chiusa**: `901fa33f6` (15/10, «fix(cli): test lanes ignore the instance's configuration»), provata, poi
  verificata anche con le variabili di A5. Nel backlog la riga è nella sezione C del coordinatore e non ha ancora la ✅.
- **H-2 è chiusa da altri**: `1c67dd5d9` (15/10, «fix(test-runner): build test server before timeout»). Il runner fa
  `dev.py server --build-only` prima del conto alla rovescia, e i log di `all-backend` di oggi lo mostrano («Server
  prerequisites ready (--build-only)»). La chiudo con ✅ nella mia sezione.
- **CP7a**: il codice è entrato. Manca solo la prova a runtime dell'immagine (avvio, healthcheck, `docker exec` come
  uid:gid, versione nella barra laterale). Il 15/10 il build si è fermato a `pip install`, perché il proxy della rete
  aziendale ri-firma il TLS (H-11). Cosa serve dal developer, una delle due:
  - (a) un build fuori dalla VPN, il suo o quello di un'immagine fatta dalla CI, e lo smoke a runtime: lo script c'è
    già nella cartella della sessione (`files/docker-test/run.sh` e `cleanup.sh`);
  - (b) H-11 prima: un secret di build facoltativo con una CA in più per pip (`RUN --mount=type=secret,id=extra_ca,
    required=false`), mai copiato nell'immagine, documentato in `admin/docker_advanced`. Poi la prova dentro la VPN,
    con la CA aziendale esportata dal developer. Il `Dockerfile` è di B dopo CP7a, quindi serve il suo OK; per la prova
    servono il daemon acceso e uno slot pesante.
- **H-12, metà**: la porta del server conta già solo i listener (`dev.py:84`). Resta il motivo di un avvio fallito: in
  `scripts/test_runner/_server.py:318-319` stdout e stderr del server condiviso vanno su `DEVNULL`, se non c'è
  `--verbose`, quindi il runner stampa solo «Shared backend exited during startup (code N)» o «did not answer within
  300s».
- **H-7** (`tzdata` nel Pipfile): finestra delle dipendenze, la fa il developer. **H-8** (`ForgotPasswordCard`): il
  file è di A, nell'area T. **TS1**: P23. **H-3 opzione A**: P24. **H-5**: traduzioni, solo su richiesta del developer.
  **H-18**: sezione C. **H-19**: ad A. **La riga di `instance_block.py` per `/auth/setup`**: con A7. **La revisione
  di B5c**: all'handoff di B.

**Lotto proposto: «H-12, il resto»** (runner e un test, nessuna area dei colori, niente Docker):

- `_server.py`: l'output del server condiviso va in un file di log della corsia, `<log dir>/shared-backend.log`,
  troncato a ogni avvio, al posto di `DEVNULL`. Un file e non una pipe, così un server che scrive molto non si blocca.
  Se l'avvio fallisce (il processo esce, oppure scadono i 300 s) il runner stampa le ultime 30 righe e il percorso del
  file. Con `--verbose` resta tutto com'è oggi;
- un test puro (test-author): un server finto che esce subito scrivendo un errore, e il messaggio del runner che ne
  mostra la coda; un server che non risponde, con un limite di avvio piccolo iniettato; con `--verbose`, nessun file;
- la doc developer del runner, una riga; la chiusura di H-2 e H-12 nel backlog;
- superficie condivisa: `scripts/test_runner/_server.py`, quindi mi serve l'assegnazione di scrittore;
- prove: il test nuovo, `utils runtime-isolation` e i test del runner già esistenti per `_server.py`, poi un
  `all-backend` (il server condiviso lo usano tutte le corsie).

### Lotto «H-12, il resto» e la prova Docker di CP7a (2026-10-16, pomeriggio) — H-12 ✅ provato; CP7a ⏳ (daemon spento)

> **Via** del coordinatore (16:16): H è lo scrittore di `scripts/test_runner/_server.py` per questo lotto; prima i
> rossi col test-author, poi l'`all-backend` in uno slot organizzato da lui. Il ✅ di C-96 e H-2 nel backlog lo mette
> lui. Alle 16:30 due aggiunte: (1) **CP7a**, il developer è a casa senza VPN: build dell'immagine e smoke a runtime
> **nello slot 1** quando MF lo libera (~16:55), prima che H-12 prosegua; (2) la nota di E: il commento di
> `test_client_address.py` (righe 33 e 771) nomina ancora `address_key`, da correggere in H-12.

1. ✅ **Contratto e rossi affidati** (16:20). Il test-author scrive i casi nuovi in
   `backend/test_scripts/test_utilities/test_test_server_preparation.py` (selettore `utils test-server-preparation`,
   già registrato), senza eseguire nulla.
   > **Note implementazione**: il contratto. `SharedTestServer(log_path=None)`. `start()` risolve `self.log_path`:
   > `log_path` se dato, altrimenti `shared_backend_log_path()`; `None` sotto verbose. Con un percorso: file aperto in
   > scrittura (troncato, cartella creata), `stdout` sul file e `stderr=STDOUT`, handle del runner chiuso subito dopo
   > lo spawn. Su un avvio fallito (il processo esce, oppure scade `STARTUP_TIMEOUT`) stampa il percorso e le ultime
   > 30 righe, lette dagli ultimi 64 KiB con `errors="replace"`, oppure «(no output)»; poi `stop()` come oggi. La
   > riga info nomina il file.
   > **⚠️ Fuori pista** (16:25, contratto corretto prima che il test-author finisse): il primo contratto ripiegava
   > su `PROJECT_ROOT/.testLog/shared-backend.log` quando il runner non ha una log dir. Ma `--log-dir` vale
   > `.testLog` per default e `_activate_log_dir()` lo prepara prima di `shared_backend_for()`: il server vivo scrive
   > proprio `<root>/.testLog/shared-backend.log`. Nel pytest dei test di utilità `_common._LOG_DIR` è `None`, quindi
   > ogni `start()` finto già esistente (`test_runtime_isolation.py`, `test_test_server_preparation.py`) avrebbe
   > troncato il log del server vivo a metà di un `all-backend`. Regola corretta: `shared_backend_log_path()` è
   > `get_log_dir()/shared-backend.log`, oppure `None` senza log dir; con `None` lo spawn resta su `DEVNULL` come oggi.
   > Così i test esistenti non cambiano e `_cli.py` non si tocca. L'unico test che tocca `_LOG_DIR` lo mette a `None`
   > via monkeypatch (`test_runtime_isolation.py:1240`).
2. ✅ **Cura provata a secco** (16:28, `files/h12/apply_cure.py`, 13 sostituzioni su ancore uniche, applicata a una
   copia): ruff verde. Black segnala gli stessi 6 blocchi del file a HEAD, cioè codice già esistente, nessuno nuovo.
   La complessità di `start()` resta 8, il cancello è 10.
   > **Note implementazione**: `SHARED_BACKEND_LOG_NAME`, `STARTUP_LOG_TAIL_LINES = 30`,
   > `STARTUP_LOG_TAIL_BYTES = 64 KiB`. Tre funzioni: `shared_backend_log_path()`; `log_tail()`, che scarta la prima
   > riga se il seek l'ha tagliata; `_open_backend_log()`, che su un `OSError` avvisa e scarta l'output, perché il log
   > non deve mai rompere un run. Il context manager `_spawn_output()` dà `stdout`, `stderr` ed `env`: con il file
   > aggiunge `PYTHONUNBUFFERED=1`, così le righe di dev.py arrivano in ordine e sopravvivono al SIGTERM di
   > `stop()`, come già `-u` per la build. Sta sulla stessa riga `with` di `_publish_spawn_ownership()`: il blocco
   > dello spawn non si re-indenta. `_report_startup_log()` è chiamato sui due fallimenti. Docstring di
   > `build_server_prerequisites` aggiornata.
   > **⚠️ Fuori pista**: `shared_backend_for()` passa sempre `verbose=False`, quindi il runner non ha un percorso
   > «verbose». La proposta diceva «con `--verbose` resta com'è»: vale solo per chi costruisce la classe a mano. La
   > doc non lo nomina.
3. ✅ **Commento di E e frase gemella** (16:33): in `test_client_address.py` (f) e `RATE_KEYS` non nominano più
   `address_key`. La stessa frase stantia stava nel mio testo P17 di `developer/architecture/security.md` (~1290):
   affidata al docs-writer, con una formula valida prima e dopo il passaggio di E. Ho segnalato al coordinatore che E
   non deve toccarla.
4. ⏳ **Doc** (docs-writer, senza eseguire nulla): la riga di `_server.py` in `runner_architecture.md`, quella di
   `--log-dir` in `test-walkthrough/index.md`, la frase di `security.md`.
   > **⚠️ Fuori pista** (16:38, segnalato dal docs-writer): `database_file_owned_exclusively()` ferma e riavvia **la
   > stessa istanza** a metà run, attorno a `db create` in `all-backend`. «Troncato a ogni avvio» avrebbe cancellato
   > l'output del primo server. **Cura v2**: il primo avvio dell'istanza svuota il file, un riavvio lo apre in append.
   > `self._log_offset` registra dove comincia l'avvio corrente; la coda di un avvio fallito legge solo da lì, quindi
   > con un avvio che non ha scritto nulla stampa «(no output)» e non le righe dei precedenti. `log_tail(path,
   > offset)`: con il taglio dei 64 KiB legge dal byte prima del taglio e scarta la riga tagliata, tenendola solo se è
   > l'unica. Provata a parte in `files/h12/check_log_tail.py`: 9 casi, tra cui la riga tagliata, il taglio esatto a
   > inizio riga, nessun a capo, l'offset e i byte non UTF-8. Il primo tentativo leggeva un byte di troppo senza a
   > capo: corretto con `partition`. Ruff verde, `start()` resta a complessità 8. Emendamento 2 al test-author: casi
   > «il riavvio aggiunge» e «il riavvio senza output nuovo». Dimensione: il file tiene l'output del server per tutto
   > il run; il log dell'app nella corsia è cresciuto di 3 MB in tutti i verdi di P17, e l'archivio usa xz preset 1,
   > veloce sul testo.
5. ✅ **CP7a, script pronti** (16:40): `files/docker-test/run.sh` e `cleanup.sh`, aggiornati rispetto al 15/10 (le
   versioni vecchie sono in `.bak`). Log e snapshot vanno in `files/docker-test/run-1610/`, perché `cleanup.sh` ne ha
   bisogno anche dopo un riavvio; in `/tmp` restano solo i dati usa e getta del container. In più: il controllo che
   il daemon sia acceso e `docker compose version`; `instance`, `block` e la versione confrontata con VERSION; la
   rimozione di `LibreFolio-data/`, se il run l'ha creata. Dal 15/10 `Dockerfile` e compose hanno cambiato solo
   commenti. Si lancia solo al via del coordinatore.
6. ✅ **Rossi** (16:49, carico 37). Il test-author ha consegnato 20 casi nuovi in 5 classi:
   - `TestSharedBackendLog`, 8 casi;
   - `TestSharedBackendLogTail`, 7;
   - `TestSharedBackendLogRestart`, 3;
   - `TestLogTail`, 1;
   - `TestSharedBackendLogWithARealChild`, 1: un figlio Python di una riga, lanciato davvero tramite
     `exec_unmasked.py`. Le guardie lasciano partire solo quell'argv e segnalare solo il suo gruppo.

   I nomi nuovi si leggono al momento della chiamata, e `_LOG_DIR` è sempre ripristinato via monkeypatch. Ruff
   verde; black lascia il file invariato.
   `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc nice -n 10 pipenv run python dev.py test --test-port 6181 --data-dir
   /tmp/librefolio-r13-h utils test-server-preparation` → **20 failed, 63 passed**: 19 su «H-12: SharedTestServer has
   no log_path», 1 su «H-12: log_tail is missing». Log in `files/runs/h12-red.log`.
7. ✅ **Cura applicata e verdi leggeri** (16:50). `files/h12/apply_cure.py` applicata in posto; il risultato coincide
   byte per byte con la prova a secco e ruff è verde. Risultati, ciascuno col suo log in `files/runs/h12-*.log`:
   - stesso selettore: **83/83**;
   - poi, uno alla volta con `files/runs/h12-greens-related.sh`: `utils runtime-isolation` **200/200**, `utils
     dev-port-check` **5/5**, `services shutdown-budget` **188/188**.

   Il carico è salito a 60–96 durante il run, per lavoro di altre corsie; i miei comandi sono leggeri.
   > **Note implementazione**: il test-author ha segnalato che `patch_clock` di `test_runtime_isolation.py`
   > sostituisce `_server.time` con un oggetto che ha solo `time` e `sleep`. La cura non aggiunge chiamate a `time`:
   > confermato dai 200 verdi.
8. ✅ **Descrizione del selettore** (`scripts/test_runner/_backend_utils.py`, superficie condivisa). **OK del
   coordinatore alle 16:54**, solo per il testo di `test-server-preparation`, attorno alle righe 343 e 737. Anche W ha
   il file aperto (C-97a: una funzione dopo la riga 26 e un blocco di catalogo dopo la ~483); i suoi hunk sono
   disgiunti dai miei. Patch applicata alle 16:54: coincide byte per byte con la prova a secco, ruff verde. La docstring, le due righe info e il `desc` del catalogo parlano solo di C-94. Il commento
   d'isolamento dice «every real process and signal forbidden», non più vero per il caso con il figlio reale; la
   classe resta `pure`. Patch pronta e provata a secco in `files/h12/apply_backend_utils.py`: 5 sostituzioni, ruff
   verde.
9. ⏳ **Prove leggere dopo l'OK** (16:54, `files/runs/h12-light-2.sh`, uno alla volta con carico < 50; log in
   `files/runs/h12-light-2/`). Il daemon Docker è ancora spento, quindi il coordinatore ha anticipato queste prove.
   - `dev.py mkdocs build`: exit 1, solo per l'avviso già noto. `wac.md` linka
     `split_promote.md#transfer-giving-leg`, corretto su dev da `ed500643f`, che non è nella mia base. Le mie tre pagine
     non ne aggiungono: lo strict interrompe dopo aver elaborato tutte le pagine. `check-links`: **97 link validi**.
   - `utils test-server-preparation`: **83/83**, con le righe info nuove.
   - **Prova reale del timeout, 1 s** (`LIBREFOLIO_TEST_STARTUP_TIMEOUT=1 … api system-wake`, 16:55–17:00; 4 min e
     23 s, quasi tutti del passo build-only, che ha ricostruito frontend debug e sito). La riga info nomina
     `.testLog/shared-backend.log`; poi «Shared backend did not answer within 1s», l'intestazione della coda con
     «(no output)» e «shared test backend failed to start». File di 0 byte: in 1 s dev.py non stampa nulla e il
     SIGTERM arriva prima. Porta 6181 libera dopo `stop()`.
   - La prova a 6 s, per vedere righe vere nella coda, aspettava che il carico scendesse sotto 50: è salito a 165.
     **Fermata alle 17:22** su richiesta del coordinatore, la galleria completa dei colori è in corso: niente prove
     nuove fino al suo via, verso le 17:45. Lo script era solo nel `sleep` d'attesa, senza figli di test; porta
     libera, verificato.
10. ✅ **Prova reale a 6 s** (17:53, carico 15, dopo la fine della pausa alle 17:52; `files/runs/h12-timeout-6.sh`,
    log in `files/runs/h12-light-2/api-timeout-6s.log`). Sequenza stampata: «Shared backend did not answer within
    6s», «Shared backend output, last 30 line(s): …/.testLog/shared-backend.log», poi le righe vere di dev.py: la
    cache JS, «Starting LibreFolio API server (TEST MODE)...», database, host, porta 6181, «Log Level: DEBUG»,
    scheduler disabilitato, endpoint, «Frontend build found», infine «shared test backend failed to start». File di 35
    righe e 1563 byte, porta libera dopo `stop()`.
    > **Note implementazione**: il server di test gira a DEBUG, quindi in un `all-backend` il file conterrà tutto il
    > log della console per l'intero run. Lo misuro dopo il run.
11. ⏳ Dopo il via del coordinatore:
   - l'`all-backend` nello slot 1 (~18:05, limite 18:45, poi A), con `files/runs/h12-allbackend.sh`. Prova il log
     vero dall'inizio alla fine del run, compreso l'append al riavvio di `db create`, in
     `.testLog/shared-backend.log`.
     > **⚠️ Fuori pista** (17:58): il controllo dell'orario manda SIGINT al runner, ma una shell non interattiva
     > avvia i comandi con `&` ignorando SIGINT: un Python nato così non installa `KeyboardInterrupt`, e il segnale
     > si sarebbe perso. Verificato con un processo finto: senza `set -m`, sleep fino alla fine; con `set -m`,
     > KeyboardInterrupt e rc 130. Lo script ora usa `set -m` e `kill -INT -- -$RUNNER`: tutto il gruppo del runner,
     > figli pytest compresi, come un Ctrl-C. Il backend condiviso ha la sua sessione e lo ferma `stop()`.
   - la prova Docker di CP7a, se il developer accende il daemon (slot 1), con `files/docker-test/run.sh` e poi
     `cleanup.sh`. Dopo la build di produzione dell'immagine, il prossimo run di test ricostruisce il frontend debug;
   - poi l'handoff FROZEN (bozza in `files/h12/handoff-draft.md`).
12. ✅ **Revisione di B5c** (18:30, durante lo slot, senza interromperlo). Su richiesta esplicita del coordinatore
    l'ho fatta **nel worktree di B**: un'eccezione alla regola d'isolamento concessa da lui. Sola lettura con `git
    --no-optional-locks`, limitata alle due righe dei miei file, alla rotta che espongono, al servizio `outcome.py` e
    allo schema `RestoreOutcome`. La decisione N53 l'ho letta dall'oggetto git `57564d321`, cioè dal journal di B già
    committato. **OK, nessuna modifica**:
    - in `instance_block.py`: l'import, la voce `backup_restore.get_restore_outcome` con il suo commento, la frase
      del docstring. In `test_instance_block.py`: `("GET", "/api/v1/backup/restore/outcome")`;
    - la rotta: biglietto solo nell'header, mai nell'URL; 256 bit, di cui si conserva solo l'SHA-256;
      `hmac.compare_digest` dopo il controllo del formato; un 404 identico per ogni biglietto che non dà l'esito; un
      biglietto sbagliato non cambia nulla; risposta con soli `{state, reason, waiting}` e `extra="forbid"`;
      `no-store`; endpoint `def` sincrono, per I/O leggero;
    - su un'istanza bloccata, chi non ha il biglietto riceve lo stesso 404 di un'istanza sbloccata, quindi la voce
      non rivela il blocco. Solo chi ha il biglietto legge `waiting: "instance_blocked"`.
    > **⚠️ Fuori pista**: la mia condizione «monouso», cioè una sola lettura, è superata da **N53** (decisione del
    > coordinatore, 17:20, da rivedere col developer): «un ripristino, un biglietto», un esito finale rileggibile
    > finché il biglietto non scade, entro un'ora. Accettata: con una lettura sola, se la risposta finale si perde la
    > pagina resta senza esito. Il rischio resta limitato: tre enum, un'ora, solo per chi ha 256 bit.
13. ✅ **`all-backend` nello slot 1** (18:01:29 → 18:33:33, carico 41 → 26; `files/runs/h12-allbackend.sh`, log in
    `files/runs/h12-allbackend/`, copia di `.testLog` in `testlog/`). Comando: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc
    nice -n 10 pipenv run python dev.py test -q --fresh-run --workers 2 --log-file … --test-port 6181 --data-dir
    /tmp/librefolio-r13-h all-backend`. **exit 0: 18 487 passed, 7 skipped, 0 failed.** Il limite delle 18:45 non è
    scattato.
    - Il runner: «Starting shared test backend … — log: …/.testLog/shared-backend.log», «ready». Poi, per `db
      create`, «Pausing the shared backend — creating a clean test database…», un secondo «Starting …» con lo stesso
      file, «ready», «Shared backend resumed».
    - **`shared-backend.log`**: 2 433 490 byte, 15 793 righe. Due avvii: «Starting LibreFolio API server» alle righe
      14 e 15717. Due volte «Application startup complete» e due volte «Finished server process», prima [41600] e
      poi [69888]. **Il riavvio ha aggiunto in coda**: le righe del primo server restano intere, fino al suo
      spegnimento pulito su SIGTERM («Shutting down», «Finished server process»), quindi l'output non bufferizzato
      sopravvive allo `stop()`. Nel log d'accesso il token della sonda della corsia è mascherato (`token=***`). Le 4
      righe «Traceback» vengono tutte da `MOCKFX_FAIL: simulated provider failure for testing`: due episodi indotti
      dai test, ciascuno registrato due volte (campo JSON e traceback in chiaro).
    - **Dimensione**: 2,4 MB per un `all-backend` intero, a livello DEBUG. Molto meno delle «decine di MB» stimate;
      il run successivo lo archivia con i log per unità.
    - Porta 6181 libera alla fine; `git diff --check` pulito.
    > **⚠️ Fuori pista** (fuori perimetro, **H-20** nel backlog): lo stdout del runner rediretto su un file, sia con
    > `>` sia con `--log-file`, è bufferizzato a blocchi. Alle 18:12 `allbackend.log` era fermo da 10 minuti alle
    > righe della build, che escono da un sottoprocesso; le righe del runner sono arrivate solo all'uscita. Il
    > comportamento c'era già prima di H-12, e il run non ne soffre.
14. ✅ **Entrata e nuova voce** (18:39). H-12 è in `dev_release2` con il merge `7ac8b17de` (genitori `5609b16d7` e
    `7f5a28f4f`, nessun conflitto); i miei commit sono `cca1c8b0a` (feat), `3934b4f8a` (docs) e `7f5a28f4f` (journal).
    HEAD verificato, `7f5a28f4f`, albero pulito. Il coordinatore mi assegna **W-B54**, dalla sezione di W (commit
    `d8c2a13c7`, letto dall'oggetto git), come **H-21** nel backlog, priorità bassa.
    > **Note implementazione** (lettura del codice, nessuna modifica): `_api_setup()`
    > (`scripts/test_runner/_backend_api.py:748`) rifà il seed con `db_populate(force=True)`. Lo chiama
    > `run_category_setup("api")` (`_common.py:641`, una volta per invocazione) da `api_test()` (`:770`), cioè la
    > categoria intera, e dal passaggio consolidato (`_cli.py:959-963`). `_run_exclusive_setups()` (`_cli.py:614`)
    > riguarda solo i setup esclusivi. Un'azione singola passa da `dispatch_to_category()`, senza setup. Per la cura
    > servono due cose: sapere se il DB della corsia ha gli utenti di fixture, con una lettura senza scritture, e
    > decidere tra seed automatico e messaggio. Da fare in un lotto con l'assegnazione di scrittore del registro.

### Lotto «H-21: un'azione `api` da sola rifà gli utenti di fixture» (W-B54, 2026-10-16, sera) — ✅ provato

> **Via** del coordinatore (18:41), H scrittore: oggi il problema ha fatto perdere due run, a W e a J. Preferenza: un
> seed con una riga di log visibile piuttosto che «stampa il comando», dentro la data-dir della corsia. Vincoli: A ha
> aperti `_backend_api.py` e `_backend_services.py` (A-27, solo descrizioni), quindi i miei hunk vanno nella logica di
> dispatch e setup, mai nelle righe `add_test`. MF ha in stage, dal merge di base, `_backend_services.py`,
> `_backend_utils.py`, `_frontend_utility.py` e `_server.py`: non li tocco. Prima i rossi, poi prove leggere a carico
> < 50, poi un checkpoint insieme ai due file del journal.

1. ✅ **Contratto e rossi affidati** (18:50). Il test-author scrive in `test_test_runner_cli.py` (selettore `utils
   test-runner-cli`, già registrato: nessuna riga nuova nel catalogo di `_backend_utils.py`), senza eseguire nulla.
   > **Note implementazione**, il contratto:
   > - `make_category(…, setup_needed=None, …)`: chiamabile che restituisce una ragione o `None`; sta in `_meta`
   >   accanto a `setup`. Tutte le 16 chiamate passano argomenti per nome (verificato via AST), quindi aggiungerlo
   >   prima di `default_isolation` è sicuro;
   > - `_common.ensure_category_setup(category)`: niente se non c'è `setup` o `setup_needed`, o se il setup è già
   >   girato in questa invocazione (il predicato non viene chiamato). Con una ragione: una riga `print_info` con
   >   categoria e ragione, poi `run_category_setup()`. Un predicato che solleva vale come ragione;
   > - `_cli.run_test_from_registry`: dopo il ritorno anticipato di `--list` (un elenco non fa seed), per
   >   `action != "all"`; se il setup fallisce, l'azione non parte ed esce un errore con la categoria;
   > - `_backend_api.API_FIXTURE_USERS = ("e2e_test_admin", "e2e_test_user")`, cioè gli utenti con cui entrano i test
   >   API, creati da `populate_mock_data.py`. `_api_fixture_users_missing()` legge `get_test_db_path()`, il DB della
   >   corsia, in `mode=ro` e senza mai crearlo: restituisce una ragione se il file manca, non si legge, o non ha uno
   >   dei due utenti (una tabella `users` assente vale come entrambi mancanti);
   > - `make_category` di `api`: `setup_needed=_api_fixture_users_missing`, accanto a `setup=_api_setup`.
2. ✅ **Cura provata a secco** (18:58; `files/h21/apply_cure.py`, 8 sostituzioni su tre file, copie in
   `files/h21/dry/`). Ruff: `_cli` e `_backend_api` puliti; `_common` ha gli stessi 5 `PLC0415` di HEAD, già
   esistenti: il mio import interno ha `noqa` con il motivo (`_registry` importa il modulo). Black: 0 blocchi
   cambiati su tutti e tre i file. Predicato provato a parte (`files/h21/check_predicate.py`): file mancante (e non
   creato), nessuna tabella `users`, nessuno dei due, solo l'admin, entrambi → `None`, un file che non è un DB, un DB
   WAL con entrambi.
   > **⚠️ Fuori pista**: un DB in WAL aperto con `mode=ro` lascia accanto `-wal` e `-shm` vuoti; il file principale
   > resta intatto. Verificato su file temporanei: rollback nessun file in più, WAL due. Il DB della corsia è in WAL
   > (byte 18–19 dell'header `02 02`, `PRAGMA journal_mode=WAL` in `db/session.py`). Nel flusso normale il backend
   > condiviso è già su quando parte il controllo, quindi `-wal` e `-shm` esistono già e la lettura non crea nulla.
   > Con `--no-shared-server` restano due file vuoti, che il prossimo che apre il DB riusa. Scritto nel docstring.
   > Il test-author verifica l'assenza di file accanto solo su un DB in modalità rollback.
3. ✅ **Doc** (docs-writer, 19:00). In `runner_architecture.md`, sotto «Registry Entry Shape», le chiavi di `_meta`:
   `setup`, `setup_exclusive`, `setup_needed`, `default_isolation`; poi la riga di `_common.py`, con
   `run_category_setup` ed `ensure_category_setup`. In `test-walkthrough/api.md`, un paragrafo in fondo a
   «Prerequisites».
   > **Note implementazione**: il docs-writer ha sistemato anche gli spazi della lista: una riga vuota prima e
   > rientri di 4 spazi. Senza, la lista finiva dentro il paragrafo e i sotto-punti non si annidavano; lo ha
   > verificato sul sorgente di Python-Markdown. Scrive «several units» e non «tutte», perché la maggior parte dei
   > test `api` registra il proprio utente. Ha aggiunto due link interni: `#declaring-a-class-and-earning-it` e
   > `index.md#isolated-runtime-lanes`.
   > **⚠️ Fuori pista** (osservazione del docs-writer, che spiega il caso di W): `_categories_in_scope()` restituisce
   > la categoria qualunque sia l'azione, quindi anche **una singola azione `services`** ricrea il DB vuoto, tramite
   > `_run_exclusive_setups()`. È così che W ha perso gli utenti.
4. ✅ **Rossi** (19:03, carico 44). Il test-author ha consegnato 6 classi, 22 funzioni e 30 casi in
   `test_test_runner_cli.py`: ruff verde; black lascia il file invariato. `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc
   nice -n 10 pipenv run python dev.py test --test-port 6181 --data-dir /tmp/librefolio-r13-h utils test-runner-cli` →
   **30 failed, 36 passed**, tutti sulle barriere `H-21:`. Per messaggio:
   - `_api_fixture_users_missing is missing` ×11;
   - `ensure_category_setup is missing` ×8;
   - `run_test_from_registry ran a single action … without asking its setup_needed first` ×4;
   - `make_category has no setup_needed` ×3;
   - `API_FIXTURE_USERS is missing` ×2;
   - `… did not ask _common.ensure_category_setup at call time` ×1;
   - `the api category declares no setup_needed` ×1.

   Log in `files/runs/h21-red.log`.
   > **Note implementazione**, scelte del test-author dove il contratto lasciava spazio:
   > - senza ragione, o senza una delle due metà, la categoria non va in `_SETUP_DONE`, così un `all` successivo
   >   nella stessa invocazione rifà comunque il suo seed;
   > - utenti simili come `e2e_test_user2` contano come mancanti, quindi niente `LIKE` o prefissi;
   > - con il file mancante non si crea nulla, nemmeno le cartelle;
   > - il caso `--list` passa dal ramo vero dell'elenco;
   > - la costante è confrontata con `test_user_defs` letto con `ast` dal sorgente, senza importarlo.
5. ✅ **Cura e verdi** (19:04–19:16, carico < 50 prima di ogni prova). La cura applicata coincide byte per byte con
   la prova a secco. Prove (script `files/runs/h21-greens.sh`, log in `files/runs/h21-greens/`):
   - `utils test-runner-cli` **66/66**;
   - `utils runtime-isolation` **200/200**: l'altro file che tocca setup e dispatch;
   - `check-orphans` verde.

   **Prova reale dello scenario di W-B54** nella corsia:
   - `db create` lascia 0 utenti di fixture;
   - `api address-probe` stampa «⚙️  api: the test database /private/tmp/librefolio-r13-h/sqlite/app.db has no
     fixture user e2e_test_admin, e2e_test_user — running the category setup before this action», poi «Populating
     test database for API tests…» e «Test database populated»: **26/26**;
   - la stessa azione una seconda volta: **26/26, senza riga di seed**, perché gli utenti ci sono.

   Porta 6181 libera alla fine. `mkdocs build`: solo l'avviso noto di `wac.md`, quindi le due nuove ancore si
   risolvono. `check-links`: 97 link validi.
   > **Note implementazione**: la riga esce come «ℹ️  ⚙️  api: …», con due icone: `print_info` aggiunge la sua.
   > Lasciata così: l'ingranaggio la lega al «⚙️ Populating…» di `_api_setup()` che segue. Nessuna modifica a
   > `_backend_utils.py` (in stage da MF), quindi il `desc` del selettore `test-runner-cli` non nomina i casi nuovi:
   > lo dice la docstring del file di test.
6. ✅ **Entrata** (19:24): commit `74b420db8` (fix), `e0dbc23a2` (docs), `c2a842653` (journal); in `dev_release2` con
   il merge `946e02d55` (treno 126), senza conflitti. HEAD `c2a842653` verificato, albero pulito. Il coordinatore
   chiude W-B54 come «spostato in H-21».

### Revisioni della sera (2026-10-16) — in FROZEN, su richiesta del coordinatore

Tutte in sola lettura. Le due nei worktree di W e di B sono un'eccezione alla regola d'isolamento, concessa dal
coordinatore, con `git --no-optional-locks` e limitata ai file nominati; le altre leggono oggetti git già committati.

1. ✅ **W-B53 / N56** (19:35, worktree di W): il passo `brim-parse-pool`, che avvia il forkserver di BRIM in
   background. **OK**, con due modifiche e alcune prove in più.
   - La posizione è giusta: dopo `market-holidays` e prima di `scheduler`, con gli altri prewarm.
   - Modifica 1: il suo test di posizione usi `assert_in_relative_order(…, ("market-holidays", "brim-parse-pool",
     "scheduler"))`, non `index + 1`.
   - Modifica 2: `LIBREFOLIO_BRIM_PREWARM` riga **commentata** in `.env.example`, con il suo default (regole 1 e 5
     del mio guardiano `services env-example`), e doc secondo C-99. Per la modalità test, `is_test_mode()`.
   - Prontezza e risveglio non ritardati: `/system/ready` controlla solo DB e migrazioni; il risveglio di Fly
     riprende dalla memoria senza rifare il lifespan.
   - Prove in più per W: `services shutdown-budget`, `services shutdown-budget-process` e `services env-example`,
     perché il forkserver ora è un figlio fin dall'avvio. Lo termina il mio passo `child-processes`.
2. ✅ **L'ordine d'avvio con B3** (20:30). Il mio passo `plugin-secrets-check` non vuole commenti: non solleva mai,
   come fissa `test_at_startup_a_check_that_cannot_run_is_a_warning_and_never_raises`.
   - Il punto vero: `admin-bootstrap` (A, su dev da `a39b67944`) e `restore-commit` (B, su un ramo indietro di 49
     commit) entrano entrambi subito dopo `global-settings`, e i pin di B e il mio non decidono quale va prima.
   - Proposta, **adottata come N57**: `global-settings` → `admin-bootstrap` → `restore-commit` →
     `plugin-secrets-check`. Il passo di A legge e scrive i dati ripristinati, e in `run_admin_bootstrap` un
     `OperationalError` che non sia «locked» si propaga. Prima del commit, un errore riporta indietro il ripristino
     all'avvio seguente; dopo, il server cade a ogni avvio.
   - B fissa l'ordine nel suo test e mette un commento sul suo passo; A è informato.
3. ✅ **Revisione di B5c** (18:30): vedi il passo 12 del lotto H-12. OK, con N53 accettata.
4. ✅ **La nota di E sul rapporto dead-code** (20:31) → **H-22** nel backlog. `mask_client_address` e
   `reset_client_address_cache` sono davvero usate solo dai test.
   - Nessun log del codice scrive l'indirizzo di un client (grep su `dev_release2`), quindi la prima non ha
     consumatori; la seconda è un aggancio per i test.
   - Le usa solo `test_client_address.py`, su dev e sui rami di E e di B.
   - `client_rate_key`, `profile_default` e `derive_key_from` sono nello stesso rapporto, ma aspettano un consumatore
     già previsto: E `2ef892b3f`, B per H-17, X per P24.
   - Il rapporto completo: 55 voci in molte aree (5 senza riferimenti, 50 usate solo dai test), quindi non è un
     cancello attivo. Comando: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc nice -n 10 pipenv run python dev.py
     lint --dead-code --scope backend`, carico 31; log in `files/runs/dead-code-backend.log`.
5. ✅ **A7b / A-13** (21:45, worktree di A, `git --no-optional-locks`): in `zodios-client.ts`, un 401 sulle pagine
   anonime dei link (`/setup`, `/invite`, `/reset-password`, `/verify-email`) non manda più al login. **OK, nessuna
   modifica alla logica.**
   - Il 423 è intatto; la corrispondenza è esatta, con al più una barra finale; la query non conta.
   - Le quattro pagine coincidono con `_TOKEN_PATHS` di `token_service.py`. Il token sta nel frammento, che
     `loginUrl(pathname + search)` perdeva.
   - Quelle pagine non fanno chiamate legate alla sessione: `/auth/me` è solo in `(app)/+layout` e in `/`. Gli unici
     401 sono quindi quelli del blocco, su `register`, `setup` ed `email/verification/confirm`.
   - Il test ha controlli positivi e ripristina `localStorage`.
   - **Due richieste non bloccanti**: (1) il commento «which the page says itself» è falso per `/verify-email` (E).
     Un 401 di `confirm` finisce nell'errore generico, con un «riprova» inutile: una voce per E, il 401 come testo del
     blocco; intanto A scriva «which the page receives». (2) `LINK_PAGES` ↔ `_TOKEN_PATHS`: un commento che rimandi
     dall'una all'altra, e un test di confronto se A vuole.
   - Da parte, esisteva già, solo `vite dev`: `hooks.server.ts` `PUBLIC_ROUTES` non elenca le pagine di link.
   - **Dovuto a me**: A7 è su dev (`a39b67944`), quindi la riga della docstring di `instance_block.py` per `/auth/setup`,
     più `/email/verification/confirm`, entra al prossimo lotto, dopo l'aggiornamento della base (368 commit indietro).

### Lotto «H-22: niente funzioni di produzione solo per i test in `client_address.py`» (N58, 2026-10-16, sera) — ✅ provato

> **Via** del coordinatore (20:35), **N58**, convenzione da rivedere col developer:
> - via `mask_client_address`, con i suoi test e le mie due frasi di `security.md`; la regola diventa «un log non
>   contiene mai l'indirizzo di un client»;
> - niente funzioni di produzione che servono solo ai test: un test azzera da sé la cache (`cache_clear()` della
>   funzione in cache, oppure il fixture a livello di modulo); `ignore_names`, con il motivo, solo quando non si può,
>   per esempio uno stato che non è una cache.
>
> Un lotto piccolo, con rossi e verdi, e checkpoint insieme al journal. Z riceve dal coordinatore la stessa nota per
> `reset_provider_cooldowns` e `reset_shutdown_budget_state`.

1. ✅ **Analisi** (20:40, sola lettura).
   - Sulla testa di ogni ramo locale (dev e i 15 rami dei workstream) le due funzioni compaiono solo in
     `client_address.py` e in `test_client_address.py`. Più le descrizioni del selettore in
     `scripts/test_runner/_backend_services.py` (docstring, `print_info`, `desc`), file in stage da MF e aperto da A:
     non lo tocco, e il testo sostitutivo va al coordinatore.
   - La doc admin (`connection_checks`, 4 lingue) e `.env.example` non promettono alcun mascheramento: cambiano solo la
     pagina developer `security.md`, solo in inglese, e la docstring del modulo.
   - Nel test: il fixture `fresh_client_address_cache` e `api.reset()` (11 usi) passano da
     `reset_client_address_cache()`; il blocco (g) ha `MASKS` e un test.
   > **⚠️ Fuori pista**: la regola di N58 detta così è falsa per l'access log di uvicorn. L'immagine lo avvia con i
   > suoi default (`CMD ["uvicorn", …]`), quindi l'access log è attivo, e ogni riga di richiesta porta `ip:porta`:
   > l'ho visto anche in `shared-backend.log` (`127.0.0.1:63629`). Vera invece la versione circoscritta: nessun record
   > che LibreFolio scrive contiene l'indirizzo. Nessun `bind_contextvars` nel backend, nessun log con l'indirizzo
   > (grep su `dev_release2`), e la connessione non registra il peer. La specifica del cloud non parla di indirizzi nei
   > log. In `security.md` va la formula circoscritta, con il fatto dell'access log; lo dico al coordinatore. Se un
   > giorno si vorrà mascherare l'access log, il filtro su `uvicorn.access` (`logging_config.py`) è il posto giusto,
   > e la funzione tornerà con quel primo chiamante.
2. ✅ **Rossi, doc e cura a secco** (20:40–20:47, in parallelo).
   - **Test** (test-author, solo `test_client_address.py`). `start_over()` sostituisce `_reset_if_there()`: chiama
     `module._configured_header.cache_clear()` e `module._warned.clear()`. La usano il fixture
     `fresh_client_address_cache` (prima e dopo ogni test) e `UnderTest.reset`, così i 3 `api.reset()` restano com'erano.
   - Il blocco (g) di `mask_client_address` è tolto: 11 casi di `MASKS`. Al suo posto c'è un (g) nuovo, la guardia
     `test_the_module_has_no_function_only_for_the_tests[reset_client_address_cache|mask_client_address]`, che
     controlla prima che `client_address` e `client_rate_key` ci siano ancora. I contratti (d) ed (e) dicono ora «un
     nuovo processo», riprodotto dai test (N58).
   - Black ha spezzato una sola asserzione, con un messaggio oltre i 300 caratteri: applicato al file, che resta
     pulito con ruff e black.
   - **Doc** (docs-writer, `security.md`): tolta la riga della tabella; in «Read once per process.», «There is no
     reset function: a test itself clears that cache and `_warned`… (decision N58…)»; in «Callers.», «LibreFolio's
     own log records never hold a client's address (a refusal logs at most the account, never the address); uvicorn's
     access log, like any web server's, writes the connection's address on each request line (see Request Logs)».
   > **⚠️ Fuori pista**: il docs-writer aveva tolto anche «and its key from `client_rate_key()`», perché oggi nessun
   > limite lo chiama (usano `flows.address_key`). L'ho rimesso io: è la regola per chi scrive un limite nuovo, e
   > diventa vera alla lettera con `2ef892b3f` di E; «Their key follows the rule of `client_rate_key()`» è già vera.
   > Una riga di 122 colonne c'era già a HEAD, con lo stesso testo: lasciata.
   - **Cura** (`files/h22/apply_cure.py`): 3 sostituzioni in `client_address.py`, +3 −24. Tolte le due funzioni; al
     posto del punto della docstring, la regola «No log record LibreFolio writes holds a client's address (decision
     N58)…». Il controllo sulla fine del file ha fermato il primo tentativo, che lasciava una riga vuota in fondo.
     Ruff e black puliti.
   - **Testo per `_backend_services.py`**, che non tocco: `files/h22/apply_backend_services_desc.py`, 4 sostituzioni su
     ancore di testo (docstring, `print_info`, due tratti del `desc`). Provato a secco sulla mia base e sulla versione
     di `dev_release2`, ruff pulito.
3. ✅ **Rosso** (20:47, carico 34): `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc nice -n 10 pipenv run python dev.py
   test --test-port 6181 --data-dir /tmp/librefolio-r13-h services client-address` → **2 failed, 120 passed**: sono
   solo i due casi della guardia, sui messaggi «still has … (N58, H-22)». Il resto, già sul reset dei test, era verde
   sul modulo invariato. Log in `files/runs/h22-red.log`.
4. ✅ **Cura e verdi** (20:47–20:49, carico < 50; `files/runs/h22-light.sh`, log in `files/runs/h22-light/`).
   - Cura applicata: coincide byte per byte con la prova a secco.
   - `services client-address` **122/122**.
   - L'app si importa (`backend.app.main`, `auth`, `email`).
   - `dev.py lint --dead-code --scope backend`: i simboli usati solo dai test scendono **da 50 a 48**; di
     `client_address.py` resta solo `client_rate_key`, che aspetta E.
   - `mkdocs build`: solo l'avviso noto di `wac.md`, quindi `#request-logs` si risolve. `check-links`: 97.
   - Nessun riferimento alle due funzioni in `backend/app`, `scripts` e `dev.py`, fuori dalle descrizioni di
     `_backend_services.py`.
5. ✅ **Commit e testo del selettore** (20:50–20:54). Il coordinatore ha committato `420cc6d13` (refactor),
   `9afcf93bf` (docs) e `9b6fc7486` (journal), e ha registrato **N58 nella forma circoscritta**: «nessun record che
   LibreFolio scrive contiene l'indirizzo di un client; l'access log di uvicorn sì, vedi Request Logs».
   `_backend_services.py` non lo modificava nessuno (X e W lo avevano solo in stage dai loro merge con dev), quindi
   l'ha dato a me. Ho applicato `files/h22/apply_backend_services_desc.py`: 4 sostituzioni, 3+/3−, coincide byte per
   byte con la prova a secco, ruff e black puliti. Prove a carico < 50: `services client-address` **122/122**, con la
   nuova riga «Testing: … (client_address, client_rate_key)»; `check-orphans` verde. Porta libera.

### Mini-lotto «La docstring di `instance_block.py`: `/auth/setup` ed `/email/verification/confirm`» (2026-10-16, sera) — ✅ provato

> **Via** del coordinatore (21:48), dopo la revisione di A7b. La base è portata in avanti (fast-forward) alla punta di
> dev, `5b916aa28`, 368 commit, con A7 (`POST /auth/setup`, `a39b67944`). La nota non committata della revisione di
> A7b è passata intatta nel fast-forward ed entra con questo checkpoint.

1. ✅ **Analisi** (21:50, sola lettura).
   - `setup_admin` (`auth.py`) e `confirm_email_verification` (`email.py:173`) non dipendono da `get_current_user` e
     sono fuori da `ALLOWED_WHEN_BLOCKED`. Su un'istanza bloccata, quindi, `refuse_when_blocked` dà a un chiamante
     anonimo il 401 di `get_current_user`, e a uno con sessione il 423.
   - Il meccanismo generale, «una rotta pubblica fuori lista risponde 401 solo da bloccata», lo fissa già
     `test_instance_block.py` con la registrazione e le letture pubbliche, e la lista è fissata: **nessun test nuovo**.
   > **⚠️ Fuori pista**: in `test_admin_setup_api.py:31-32`, A scrive ancora che `/auth/setup` su un'istanza bloccata
   > «aspetta una decisione del developer (A7)». La decisione P16(d) l'ha presa: resta fuori lista e risponde 401.
   > Testo di A: lo giro al coordinatore.
2. ✅ **Docstring** (21:51). Nel primo paragrafo: «Registration stays out, and so does the initial administrator's setup
   (decision P16(d))». Nel secondo: `POST /auth/setup` e `POST /email/verification/confirm` tra le rotte pubbliche fuori
   lista, e una frase sulle pagine anonime dei link (`/invite`, `/setup`, `/verify-email`): A7b le tiene sul 401
   invece di mandarle al login (`frontend/src/lib/api/zodios-client.ts`), così la pagina può dire che l'istanza è
   bloccata. Righe entro 120 colonne; la riga 8 da 121 c'era già. Ruff e black puliti; nessun test legge la docstring.
3. ✅ **Prova leggera** (21:52–22:02, partita con carico 47; `files/runs/mini-docstring.sh`, log in
   `files/runs/mini-docstring/`). `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc nice -n 10 pipenv run python dev.py
   test --test-port 6181 --data-dir /tmp/librefolio-r13-h api instance-block` → **62/62**; porta libera.
   - Il passo build-only ha ricostruito frontend debug e sito in **472 s**, in primo piano e fuori dal limite d'avvio
     (C-94).
   - Il backend condiviso ha scritto in `.testLog/shared-backend.log` (H-12) e ha applicato la migrazione `009` senza
     errori.
   - **H-21 in pratica**: «⚙️ api: the test database … has no fixture user e2e_test_admin, e2e_test_user — running the
     category setup before this action», poi il seed.
   > **⚠️ Fuori pista**, la causa e **H-23** nel backlog. Le mie tre corse `services client-address` di H-22
   > avevano svuotato il DB della corsia: ciascuna stampa «Removing existing test database» e `db create`.
   > `_run_exclusive_setups()` esegue il setup esclusivo di `services` anche per una sola azione, perfino `pure`: è la
   > causa iniziale delle corse perse da W e da J. Proposta: per una singola azione, il setup esclusivo solo se
   > l'azione non è `pure`, oppure un `setup_needed` anche per `services`.

### Lotto «H-23: un'azione `pure` da sola non ricrea il DB della corsia» (2026-10-16, sera) — ✅ provato

> **Via** del coordinatore (22:08). H è scrittore del registro del runner per questo lotto, ma non tocca
> `_frontend_transaction.py` e `_frontend_utility.py`, dove W (FE8b) cambia righe di percorso. La voce `.DS_Store`
> che il coordinatore dice di avermi mandato diventa **H-24**, dopo H-23; il messaggio non mi è arrivato.

1. ✅ **Analisi** (22:10, sola lettura; HEAD `3a482b478`, il mio commit di journal del mini-lotto, già in dev).
   - `_run_exclusive_setups()` (`_cli.py`) gira per ogni invocazione: `_categories_in_scope()` restituisce la
     categoria qualunque sia l'azione, e il setup esclusivo di `services` (`_services_setup` → `db_create`) parte
     anche per un solo test `pure`.
   - Le classi sono nel catalogo: `exclusive_because` → `write-global`, altrimenti `isolation` dell'azione,
     altrimenti `default_isolation` della categoria (`build_inventory()` in `_inventory.py`). Senza nulla di
     dichiarato decide `classify()` con la scansione statica.
   - `services` ha `default_isolation="write-scoped"` e 73 azioni dichiarate `pure`: sono queste che smettono di
     svuotare la corsia. `services` è l'unica categoria con un setup esclusivo.
   - I test oggi nominano `_run_exclusive_setups` solo per sostituirlo o per l'ordine (`test_test_runner_cli.py:177`,
     `test_runtime_isolation.py:1222`); la decisione del sollevamento non ha test.
   - **Disegno**: `_inventory.declared_isolation(category, action)`, un'unica definizione della classe dichiarata,
     usata da `build_inventory()` e dal sollevamento. In `_run_exclusive_setups()`, un'azione da sola dichiarata `pure`
     salta il setup esclusivo, con una riga che lo dice; tutto il resto resta com'è: la categoria intera, `all`, un'azione
     non `pure`, o non dichiarata (prudente, come `classify()`).
   > **⚠️ Fuori pista** (fuori perimetro): il pre-passaggio parallelo (`--workers > 1`) non guarda l'azione.
   > `_parallel_for_scope()` → `plan(scope)` pianifica tutta la categoria, a differenza dei pre-passaggi consolidati,
   > che vogliono `action in (None, "all")`; con le classi server (READ, WRITE_SCOPED) chiama anche
   > `run_category_setup("services")`. Quindi `--workers 2 services client-address` gira la categoria e ricrea il
   > DB. Lo segnalo al coordinatore come voce a parte; H-23 copre il percorso normale.
2. ✅ **Rossi, doc e cura a secco** (22:10–22:25, in parallelo).
   - **Test** (test-author, solo `test_test_runner_cli.py`): 37 casi in 4 classi.
     - `TestDeclaredIsolation`, 15: `exclusive_because` vince su un `pure` dichiarato; la classe propria vince sul
       default; il default della categoria; nulla di dichiarato → `None`; categoria o azione sconosciute → `None`; il
       registro letto al momento della chiamata.
     - `TestBuildInventoryClassifiesThroughDeclaredIsolation`, 6: `collect_launches` sostituita da lanci finti;
       `isolation` = `classify(engine, path, declared_isolation(…))`, e un caso in cui `declared_isolation` sostituita
       viene davvero chiamata per nome.
     - `TestRunExclusiveSetupsSparesASinglePureAction`, 13: dai casi (a)–(h) del contratto. Ognuno lancia prima l'azione
       `pure` della stessa categoria, così il «gira ancora» non passa a vuoto oggi.
     - `TestServicesClientAddressKeepsTheLaneDatabase`, 3: `client-address` è `pure` e non arriva al setup;
       `asset-source` (default `write-scoped`) sì.

     I setup veri falliscono se raggiunti: `_services_setup`, `db_create`, `subprocess.run`.
   - **Doc** (docs-writer): la voce `setup_exclusive` di «Registry Entry Shape» in `runner_architecture.md`, con
     l'eccezione e «with `--workers` above 1, the parallel pass may run it as well»: il passaggio parallelo non lo
     chiama con `--no-shared-server` né con un piano di un gruppo o nessuno.
   - **Cura** (`files/h23/apply_cure.py`): `_inventory.declared_isolation()`, che `build_inventory()` ora usa, e in
     `_cli.py` `_single_pure_action()` più il salto con una riga. Ruff come a HEAD (4 `PLC0415` già esistenti in
     `_inventory.py`; il mio import interno ha `noqa` con il motivo); black non tocca le righe nuove.
   > **⚠️ Fuori pista**: il test-author ha seguito il contratto alla lettera, «un'azione sconosciuta → `None`». La mia
   > prima cura per un'azione assente restituiva il default della categoria, perché leggeva `entry = {}`. Corretta:
   > un'azione che il catalogo non ha non dichiara nulla, e anche `_meta` non è un'azione. Per `build_inventory()`
   > non cambia nulla, perché i suoi lanci vengono sempre da azioni del registro.
3. ✅ **Rossi → cura → verdi → prove reali → doc** (22:26–23:11, ogni passo a carico < 50: il carico è salito fino
   a 204 per lavoro di altre corsie; `files/runs/h23-run.sh`, log in `files/runs/h23/`).
   - **Rosso** (`utils test-runner-cli`): **37 failed / 66 passed**: 23 su «H-23: declared_isolation is missing», 14
     su «H-23: the exclusive setup ran for a single pure action».
   - **Cura** applicata, uguale byte per byte alla prova a secco.
   - **Verdi**: `utils test-runner-cli` **103/103**, `utils runtime-isolation` **200/200**, `utils coverage-combine`
     **11/11** (usa `PURE` dell'inventario), `check-orphans` verde.
   - **Prova reale, azione `pure`** (`services client-address`): **122/122**; il DB della corsia è **invariato**
     (inode, mtime e dimensione uguali prima e dopo: `331446094 1792180946 1314816`); stampata la riga «services:
     client-address is pure, it opens no database: the category's setup is skipped and the lane's database is left as
     it is».
   - **Prova reale, azione non `pure`** (`services asset-sync-counts`, default `write-scoped`): **1/1**; il DB è
     **ricreato** («Removing existing test database», inode nuovo), come prima.
   - **Doc**: `mkdocs build` **exit 0**, senza avvisi: la base nuova contiene `ed500643f` per `wac.md`.
     `check-links`: 97. Porta 6181 libera.
4. ✅ **Backlog**: **H-24** (`.DS_Store` e test nel controllo della build vecchia, da E via coordinatore) e **H-25**
   (il pre-passaggio parallelo solo per la categoria intera), approvate dal coordinatore alle 22:14; si fanno in
   quest'ordine dopo H-23.
5. ✅ **Entrata** (23:12): commit `9541c0667` (fix), `d0a349cf3` (docs), `7ea30903e` (journal), entrati in dev.

### Lotto «H-24: un file nascosto o un test non fanno ricostruire il frontend» (2026-10-16, notte) — ✅ provato

> **Via** del coordinatore (23:12): prima H-24, da E (`.DS_Store`), poi H-25. Ci scrivo io: `scripts/cli_base.py`,
> superficie condivisa, è il file della voce stessa.

1. ✅ **Analisi** (23:15, sola lettura; HEAD `7ea30903e`, già in dev).
   - `check_frontend_needs_build()` (`scripts/cli_base.py` ~584): `src_dir.rglob("*")`; ogni file più recente di
     `build/index.html` che non sia in `_BUILD_GENERATED_SOURCES` → rebuild.
   - **Misura reale prima della cura**: build `21:59:40`; l'unico file più recente in `frontend/src` è
     `frontend/src/.DS_Store` (`22:01:48`, Finder, ignorato da git), e `check_frontend_needs_build()` risponde
     **True**. Il prossimo run con server ricostruirebbe a vuoto: 472 s l'ultima volta.
   - File nascosti in `src`: `.DS_Store`, `lib/api/.gitignore`, `lib/i18n/.generated` (lo stamp di
     `scripts/i18n_catalog.py`: generato; i cataloghi `<lang>.json` restano nella scansione). Poi 504 file
     `*.test.*`/`*.spec.*` di Vitest: Vite non li impacchetta e nessun codice dell'app li importa (verificato), ma
     oggi una modifica a un test fa ricostruire il frontend.
   - **Regola**: la scansione salta i percorsi con una parte nascosta, il nome che inizia con `.`, e i file di test,
     `.test.` o `.spec.` nel nome. Tutto il resto conta come oggi: `.ts`, `.svelte`, `.json`, i `prefixes.txt` del
     catalogo i18n, `.css`, `.html`… Una build creduta fresca a torto costa più di una ricostruzione in più.
   - Test esistenti: `TestFrontendBuildStaleness` in `test_runtime_isolation.py` (~2300; radice finta sotto
     `tmp_path`, mtime impostate a mano); selettore `utils runtime-isolation`. Doc: `test-walkthrough/front-overview.md:42`,
     solo in inglese. `dev_workflow.en.md:132`, tradotta, resta vera («sources newer than…»): non la tocco, quindi
     nessun debito di traduzione.
   - Residuo (nel backlog): `_tool_contract_sources()` conta anche le mtime delle cartelle Python, per accorgersi di
     un file tolto; un `.DS_Store` creato lì cambia la mtime della cartella.
2. ✅ **Rossi** (test-author) e **doc** (docs-writer), in parallelo; la cura la preparo io, a secco
   (`files/h24/apply_cure.py`: `_counts_for_the_build()` e `_TEST_ONLY_FOLDERS` accanto a
   `_BUILD_GENERATED_SOURCES`, usate dalla scansione di `src`; ruff pulito, black non tocca le mie righe; la regola
   provata a parte su 24 casi, `files/h24/check_rule.py`).
   > **⚠️ Fuori pista** (23:25, dal docs-writer): restavano 33 file di supporto ai test senza `.test.` nel nome, in
   > `src/__tests__/` (le imbracature dei test dei componenti, l'alias `$test` di `svelte.config.js`),
   > `src/__mocks__/$app/` e le cartelle `__tests__/fixtures`. Ognuno avrebbe ancora fatto ricostruire la build.
   > Nessun codice dell'app li importa, né per percorso né con `$test` (verificato), e `frontend/vitest.config.ts` li
   > esclude già dalla copertura come codice non dell'app. **Regola estesa**: anche un file in una cartella, una parte
   > genitrice e non il nome del file, che si chiama esattamente `__tests__` o `__mocks__`. Emendamento mandato al
   > test-author prima che finisse, con controlli: `lib/my__tests__/x.ts` e il file `lib/__tests__.ts` contano
   > ancora. La riga di doc va adeguata.
   - **Test** (test-author, solo `test_runtime_isolation.py`): 32 casi in `TestFrontendBuildStaleness`.
     - 14 rossi oggi: i nascosti (`.DS_Store` in `src` e in una sottocartella, `._App.svelte`, `lib/api/.gitignore`,
       `lib/i18n/.generated`, file in `lib/.cache/`), i test (`x.test.ts`, `x.dom.test.ts`, `x.spec.ts`,
       `routes/x/page.test.ts`), le cartelle `__tests__`/`__mocks__`.
     - 13 controlli che devono restare True: tra cui `latest.ts`, `contest.svelte`, `x.testing.ts`, `testing/helpers.ts`,
       `lib/tests/x.ts`, `lib/my__tests__/x.ts`, il file `lib/__tests__.ts`, un `prefixes.txt`.
     - 3 casi «salta, non si ferma» e 2 «una cartella sopra `src`»: `.hidden-root` e `__tests__`.

     Il fixture `frontend_project` è diventato `make_frontend_project(monkeypatch, root)`, uguale per i test esistenti.
   - **Doc** (docs-writer): la parentesi in `front-overview.md:42`: «(under `frontend/src/`, hidden files and folders,
     such as the macOS Finder's `.DS_Store`, do not count, nor do `*.test.*` / `*.spec.*` files and the `__tests__/` /
     `__mocks__/` folders, which only the tests use)».
3. ✅ **Rossi → cura → verdi → prova reale → doc** (23:24–23:40, carico < 50; `files/runs/h24-run.sh`, log in
   `files/runs/h24/`).
   - **Prova reale prima**: `check_frontend_needs_build()` → **True**, perché l'unico file più recente della build è
     `frontend/src/.DS_Store`.
   - **Rosso** (`utils runtime-isolation`): **14 failed / 218 passed**, i 14 casi nuovi su «H-24: …».
   - **Cura** applicata, uguale byte per byte alla prova a secco.
   - **Verdi**: `utils runtime-isolation` **232/232**, `utils dev-cli-docker` **96/96**, `utils
     test-server-preparation` **83/83**.
   - **Prova reale dopo**: **False**, con lo stesso `.DS_Store` ancora l'unico file più recente: il caso di E è risolto.
   - `mkdocs build` exit 0; `check-links` 97; porta libera.
4. ✅ **Entrata** (23:45): commit `c53012fcb` (fix), `43ebc1a3f` (docs), `cf6e5e455` (journal), entrati in dev.

### Lotto «H-25: il pre-passaggio parallelo solo per la categoria intera» (2026-10-16, notte) — ✅ provato

> **Via** del coordinatore (23:45), più la regola di `-k` approvata (23:52). Base: fast-forward fatto dal
> coordinatore a `4bf824362`; me l'aveva chiesto come compito mio, ma le mie regole mi vietano di muovere la storia, e
> ho iniziato su `cf6e5e455` senza toccare `BACKLOG_POST_1.2.md`, l'unico mio file cambiato dai 99 commit in arrivo.
> Notte: il developer dorme, quindi una domanda solo sua va nel piano e al coordinatore, e si va avanti.

1. ✅ **Analisi** (23:50, sola lettura).
   - `_run_parallel_prepass()` (`_cli.py` ~926): per una categoria del registro chiama
     `_parallel_for_scope(args, category, …)` qualunque sia `args.action`. `plan(scope)` pianifica tutta la categoria;
     con le classi server (READ, WRITE_SCOPED) c'è anche `run_category_setup(scope)`, cioè per `services` `db create`.
   - I pre-passaggi consolidati invece (`_backend_consolidation_scope`, e il gemello del frontend) girano solo per la
     categoria intera o la suite: con un'azione singola o con `-k` (`test_names`) tengono la forma 1:1.
   - Quindi oggi `--workers 2 services client-address` fa girare i test parallelizzabili di tutto `services` e ricrea
     il DB (contro H-23), e `--workers 4 services all -k foo` li fa girare tutti, ignorando il `-k`.
   - **Cura**: `_parallel_prepass_applies(args)`, la stessa regola dei consolidati: niente con `test_names`, sì solo
     con `action in (None, "all")`. `all` e `all-backend` restano come sono; le categorie frontend già non hanno
     pre-passaggio.
   - Test esistenti: `test_coverage_combine.py` chiama `_parallel_for_scope` direttamente, non toccato;
     `test_runtime_isolation.py:1223` sostituisce `_apply_parallel`. Doc: la riga `--workers` di `index.md` e la
     sezione «`--workers`» di `runner_architecture.md`. La clausola di H-23 «with `--workers` above 1, the parallel
     pass may run it as well» diventa falsa e va tolta.
2. ✅ **Rossi, doc e cura a secco** (23:52–00:10, in parallelo).
   - **Test** (test-author, solo `test_test_runner_cli.py`): 35 casi in 4 classi, 26 rossi oggi.
     - `TestParallelPrepassApplies`, 16 casi, la regola su tutte le forme di `args`: `action` e `test_names` assenti,
       `None`, `[]`.
     - `TestRunParallelPrepassRunsNothingForOneActionOrTestNames`, 8: anche `services asset-source`, `write-scoped`,
       per mostrare che la regola non guarda la classe; due casi «sostituto» fissano che `_run_parallel_prepass`
       chiami `_parallel_prepass_applies` una volta, per nome.
     - `TestRunParallelPrepassStillServesTheWholeCategoryOrSuite`, 8 guardie verdi.
     - `TestApplyParallelLeavesOneActionToTheSerialPass`, 3.

     Un fixture fa fallire, se raggiunti, `run_category_setup`, `plan`, `run_groups` e `subprocess.run`.
   - **Doc** (docs-writer):
     - la riga `--workers` di `index.md`;
     - una voce nella sezione «`--workers`» di `runner_architecture.md` («the same scope rule as the consolidated
       pre-passes»);
     - la clausola di H-23 su `setup_exclusive` sostituita da «The skip holds at any `--workers`, since the parallel
       pass does not run for one action». Il docs-writer ha verificato tutti i punti da cui si raggiunge il setup di
       `services` per un'azione singola.
   - **Cura** (`files/h25/apply_cure.py`): `_parallel_prepass_applies()` prima di `_run_parallel_prepass()`, e un
     ritorno subito all'inizio di quest'ultima. +16/−1; ruff e black puliti; complessità 7.
   > **⚠️ Fuori pista** (dal test-author): l'azione `all` di ogni categoria è registrata con `test_names=False`, quindi
   > il passaggio seriale **scarta i nomi**: `--workers 4 services all foo` li ignorava prima della cura e li ignora
   > dopo. La regola di `-k` approvata stanotte non fa funzionare `-k` su `all`, toglie solo il pre-passaggio
   > parallelo in quella combinazione, che costa velocità senza cambiare cosa gira. La tengo: il pre-passaggio non sa
   > applicare i nomi, quindi con dei nomi si fa da parte, come i consolidati. Se un giorno `all` applicherà i nomi, la
   > regola sarà già quella giusta. Lo scarto silenzioso dei nomi dopo `all` è un difetto a parte: **H-26** nel backlog.
3. ✅ **Rossi → cura → verdi → prove reali → doc** (23:59–00:15, ogni passo a carico < 50; `files/runs/h25-run.sh`,
   log in `files/runs/h25/`). Niente prova reale «prima» sull'azione singola: prima della cura,
   `--workers 2 services client-address` avrebbe fatto girare tutto `services` in parallelo, una prova pesante.
   - **Rosso** (`utils test-runner-cli`): **26 failed / 112 passed**: 16 su «H-25: _parallel_prepass_applies is
     missing», 10 su «H-25: the parallel pre-pass ran for …».
   - **Cura** applicata, uguale byte per byte alla prova a secco.
   - **Verdi**: `utils test-runner-cli` **138/138**, `utils runtime-isolation` **232/232**, `utils coverage-combine`
     **11/11**, `check-orphans` verde.
   - **Prova reale, azione singola** (`dev.py test --workers 2 … services client-address`): **122/122**, **nessun**
     «Parallel pass», la riga di H-23, DB della corsia **invariato** (inode, mtime e dimensione).
   - **Prova reale, categoria intera** (`--workers 2 … schemas all`): exit 0, «Parallel pass — 12 isolation-safe
     unit(s) across 2 worker(s)», **166 + 1667 passed**, verde in 31,6 s.
   - **Doc**: `mkdocs build` exit 0; `check-links` 97; porta libera.

### Lotto «H-26: un'azione registrata senza nomi di test li rifiuta» (2026-10-17, notte) — ✅ provato

> **Via** del coordinatore (00:20): «refuse», exit 2 con «name the action» quando dopo `all` seguono dei nomi. Alla mia
> domanda di perimetro (00:24) ha risposto: **una regola sola per tutte le 36 azioni**, rifiuto prima di ogni effetto
> collaterale, `--list` compreso. Base `9839ea00b`, cioè dev dopo H-25, fast-forward del coordinatore, verificata
> pulita.

1. ✅ **Analisi** (00:20–00:30, sola lettura).
   - Ogni sottoparser di categoria ha il posizionale `test_names` (`nargs="*"`, in `create_subparser_from_registry`).
     Le suite (`all`, `all-backend`, `all-frontend`) non l'hanno, e lì argparse rifiuta già i nomi con exit 2.
   - `run_test_from_registry` inoltra i nomi solo alle azioni registrate con `test_names=True`; alle altre li perde in
     silenzio, e l'azione gira intera.
   - Il registro vivo ha **36** azioni senza nomi: le 16 `all`, `db create`, `db populate` e 18 unità Vitest (10 in
     `front-portfolio`).
   - Verificato col parser vero (`files/h26_parse.py`):
     - `services all test_foo` esegue tutto `services`;
     - `external all yfinance` esegue tutti i provider: sembra un filtro e non lo è;
     - `db populate --force --clean extra` ripopola senza dire niente;
     - `front-portfolio risk-unit nome` esegue tutta l'unità.
   - Effetti collaterali prima del corpo, in entrambi gli ingressi: `_dispatch_test_command` (`dev.py test`) e
     `main()` (`python -m scripts.test_runner`).
     - `_common.tee_output` apre `--log-file`.
     - `_activate_log_dir` archivia il `.testLog` precedente in `00_archive/`.
     - `_timed_run` scrive il record della campagna.
     - `_snapshot_log_dir_db` copia il DB nella cartella dei log.
     - Il rifiuto va prima di tutti.
   - Codice di uscita: `dev.py` fa `sys.exit(main())` con `args.func(args) or 0`, e `__main__` fa `sys.exit(main())`.
     Quindi un `return 2` dei due ingressi arriva alla shell come exit 2.
   - Doc: nessuna frase di H-25 parla dei nomi persi. Un solo comando documentato passa token dopo un'azione senza
     nomi: `external all --exclude-providers yfinance broker_coinbase` (`external.md:54`). È un falso positivo: col
     parser vero i due token vanno a `--exclude-providers` e `test_names=[]`.
   - **Cura**: `_refused_test_names(args) -> str | None` in `_cli.py`. Una sola regola: nomi dati a un'azione del
     registro con `test_names` falso.
     - Il messaggio per `all` dice «name the action» e mostra l'esempio; quello per le altre azioni dice «takes no test
       names: it runs whole».
     - La chiamata sta in cima a `_dispatch_test_command` e `main()`: `print_error`, poi `return 2`.
     - `run_test_from_registry` non cambia: nessun chiamante interno passa nomi a queste azioni.
2. ✅ **Rossi, doc e cura a secco** (00:35–00:45, in parallelo).
   - ✅ **Rossi** (test-author, solo `test_test_runner_cli.py`, +447 righe, 3 import): 533 casi in 4 classi.
     - `TestRefusedTestNames`, 514 casi: uno per ogni azione del catalogo vivo, con id `categoria-azione`, più
       questi:
       - l'ancora (`services all`, `db populate`, `front-portfolio risk-unit` senza nomi, `services client-address` con
         i nomi), senza contare le 36;
       - nessun nome (attributo assente, `None`, `[]`);
       - i 6 sottocomandi che non sono categorie;
       - 4 casi fuori dal catalogo;
       - purezza: la regola non stampa e non tocca `args`;
       - il catalogo letto al momento della chiamata, con una categoria finta registrata dopo l'import.
     - `TestDispatchTestCommandRefusesBeforeAnySideEffect` (9) e `TestMainRefusesBeforeAnySideEffect` (9): `args` dal
       parser vero, 5 invocazioni rifiutate, un caso `--log-file`/`--log-dir` (nessun file scritto) e 3 guardie (nomi a
       un'azione che li prende, `all` senza nomi, `--exclude-providers yfinance broker_coinbase`).
     - `TestDevPyExitsWithTheRefusal` (1): `dev.main()` restituisce 2.
     - Le prove rifiutate chiudono tutte le 11 cuciture (`tee_output`, `_activate_log_dir`, `_timed_run`,
       `_snapshot_log_dir_db`, i due corpi, `_configure_runtime`, `run_test_from_registry`, `dispatch_to_category`,
       `subprocess.run` e `subprocess.Popen`) con sostituti che falliscono se chiamati: nessun rosso arriva mai a una
       corsa vera.
     > **⚠️ Fuori pista** (dal test-author): `_cli` prende `print_error` da `_common`, non da `cli_base`; stampa allo
     > stesso modo su stdout. A parte, non corretto: nel ramo `--log-file` di `main()`, `_snapshot_log_dir_db()` non ha
     > `try/finally`, a differenza di `_dispatch_test_command`.
   - ✅ **Doc** (docs-writer):
     - `index.md`, «Running Tests»: i nomi vanno solo alle azioni che li prendono (`--help` le marca `[TEST_NAME]`);
       `all`, `db create`/`populate` e la maggior parte delle unità Vitest li rifiutano, exit 2, anche con `--list`.
     - `runner_architecture.md`, passo 2 di «Adding a Test Action»: un'azione con `test_names=False` li rifiuta.
     - `runner_architecture.md` ~554: «`--test-names`» non era un flag, ed è stato tolto; ora «Neither `all` nor
       `all-frontend` takes test names».
     - La voce `--workers`: «pytest `-k`, which only a named action takes».
     > **⚠️ Fuori pista** (dal docs-writer): non tutte le unità Vitest rifiutano i nomi. Le tre di `front-utility`
     > (`core-unit`, `component-unit`, `onboarding-component-unit`) li passano a Vitest `-t`. Le 18 che ho contato
     > erano già solo quelle senza nomi; la mia consegna al docs-writer diceva «the Vitest unit actions», ed era
     > imprecisa. La doc dice «most».
   - ✅ **Cura a secco** (`files/h26/apply_cure.py`, +26 righe): `_refused_test_names()` prima di
     `_dispatch_test_command()`, più 4 righe in cima a `_dispatch_test_command()` e a `main()`. ruff e black puliti, con
     il percorso vero via stdin.
3. ✅ **Rosso → cura → verde → prova reale** (00:46–00:58, a carico < 50; `files/runs/h26-lib.sh`, log in
   `files/runs/h26/`).
   - **Rosso** (`utils test-runner-cli`): **526 failed / 145 passed**, la ripartizione prevista.
     - 513 su «H-26: _refused_test_names is missing»;
     - 13 sulla prima cucitura raggiunta: 11 `_activate_log_dir` e 2 `tee_output`, i due casi `--log-file`.
     - Nessun rosso fuori dalle classi H-26; i 138 casi di prima e le 7 guardie sono verdi.
   - **Cura** applicata, uguale byte per byte alla prova a secco (`cmp`).
   - **Verde**: `utils test-runner-cli` **671/671** in 5,3 s. Il rosso aveva impiegato 92 s, quasi tutti per il
     resoconto dei fallimenti.
   - **Prova reale** (`files/runs/h26-refuse.sh`): exit **2** e il messaggio giusto per `services all h26_probe`,
     `services all --list h26_probe`, `db populate --force --clean h26_extra`, `external all yfinance`,
     `front-portfolio risk-unit h26_probe` e `python -m scripts.test_runner services all h26_probe`. **Nulla
     cambiato**: l'archivio di `.testLog` (818 voci), `.run_cache.json`, `.campaign.json` e il DB della corsia (inode,
     mtime, dimensione).
   - Doc: nella riga `--workers` di `index.md` (la mia frase di H-25) la stessa precisazione del docs-writer, «pytest
     `-k`, which only a named action takes».

### Residuo di H-24 (`_tool_contract_sources()` e il `.DS_Store` nelle cartelle Python) e H-28 (2026-10-17, notte) — ✅ provato

> Chiesto dal coordinatore dopo H-25, con il vincolo: ignorare le voci nascoste nella mtime di una cartella senza perdere
> la rilevazione di un file tolto.

- `_tool_contract_sources()` (`cli_base.py` ~580) mette fra gli ingressi della build le 3 cartelle (`schemas`,
  `services/tools`, `tool_plugins`) e le loro sottocartelle, 8 in tutto, per la loro mtime. Serve ad accorgersi di un
  `.py` tolto, rinominato o entrato con una mtime vecchia.
- Verificato su questa macchina (`files/h26/mtime-demo`, poi cancellato):
  - creare `.DS_Store` fa salire la mtime della cartella; riscriverlo sul posto no;
  - creare `__pycache__` la fa salire: anche questo oggi fa ricostruire (in quelle cartelle ce ne sono 6);
  - togliere un `.py` la fa salire.
- **Conclusione: un filtro non può bastare.** Guardando solo le mtime, un `.DS_Store` e un file tolto sono lo stesso
  evento. Serve un ricordo dell'ultima build.
- **Proposta A**, inviata al coordinatore (00:45): un'impronta dell'elenco degli ingressi.
  - `tool_contract_fingerprint()` in `cli_base` è lo sha256 dei percorsi relativi: i `.py` senza parti nascoste né
    `__pycache__`, più i file fissi.
  - `cmd_fe_build` (`dev.py`) calcola l'impronta prima di `api sync` e la scrive in
    `frontend/build/.tool-contract-inputs` solo se la build riesce, accanto a `.build-debug`.
  - `check_frontend_needs_build`:
    - un file più nuovo della build → stale;
    - un'impronta diversa dal marker → stale;
    - senza marker vale la regola di oggi, con le mtime delle cartelle.
  - I tre percorsi di build passano da `cmd_fe_build`: `dev.py`, il runner (`_frontend_common.py:92`, `build_func`) e
    Docker (`_docker_ensure_frontend_built`).
- **Alternativa B, scartata**: un euristico («una cartella più nuova non conta se un suo file nascosto è nuovo almeno
  quanto lei»). Perde la rimozione appena il `.DS_Store` viene toccato dopo.
- **Reperto a parte (basso, `static_site.py`, file mio)**: `frontend_catchall` serve qualunque file della radice di
  `frontend/build/`, dotfile compresi. `GET /.build-debug` e `GET /.build-version` rispondono, anche dall'immagine.
  Proposto come H-27, oppure in coda al lotto.
- ✅ **Decisione** del coordinatore (00:50): disegno A approvato, OK da writer su `dev.py` (`cmd_fe_build` e
  l'import) e su `scripts/cli_base.py`. Il reperto dei dotfile entra **in coda a questo lotto, come H-28**. H-27 è
  un'altra voce: `profile_default` non controlla il tipo (da E, R13-SEC3). È registrata nel backlog e si fa dopo il
  lotto.
- ✅ **Cura a secco** (`files/h24r/apply_cure.py`, 107 righe cambiate su tre file).
  - `cli_base.py`:
    - `_TOOL_CONTRACT_FOLDERS`, `TOOL_CONTRACT_INPUTS_MARKER` e la versione dell'elenco;
    - `_tool_contract_sources()`: stesso nome, ma ora dà solo file che esistono, senza parti nascoste né
      `__pycache__`;
    - `_tool_contract_folders()`, usata solo come ripiego;
    - `tool_contract_fingerprint()` e `record_tool_contract_inputs()`, che scrive con `contextlib.suppress(OSError)`;
    - `_tool_contracts_changed()` al posto del ciclo dentro `check_frontend_needs_build()`.
  - `dev.py`: i due nomi nell'import da `cli_base`. In `cmd_fe_build`, `tool_inputs` si calcola prima di
    `cmd_api_sync` e `record_tool_contract_inputs(PROJECT_ROOT, tool_inputs)` si chiama solo se la build riesce.
  - `static_site.py`: `_hidden_in_build(target)` sulle parti del percorso risolto dentro la build, quindi
    `/assets/../favicon.png` resta servito; più una frase nella docstring del modulo.
    > **⚠️ Fuori pista** (01:00): `_hidden_in_build` risolve una seconda volta la cartella della build. Se la cartella
    > viene sostituita fra le due risoluzioni, `relative_to` alzerebbe un errore, cioè un 500. Ora quel caso conta
    > come nascosto e va al fallback (`not target.is_relative_to(build) or …`). Il percorso `/mkdocs` ha la stessa
    > forma, ma il sito costruito non contiene dotfile (0): resta fuori da H-28, lo segnalo nell'handoff.
  - Le mtime delle cartelle restano solo come ripiego, quando il marker manca.
  - ruff con i percorsi veri via stdin: invariato (`dev.py` ha 10 reperti, gli stessi di prima). black: nessun
    pezzo sulle righe nuove; `cli_base.py` passa da 15 a 14 pezzi, perché il vecchio generatore su più righe era uno
    di quelli.
- ✅ **Rossi** (secondo test-author, file diversi da H-26): 77 test, 67 rossi e 10 verdi previsti.
  - `test_runtime_isolation.py`, 59 test:
    - `TestToolContractListing` (19): l'elenco degli ingressi, l'impronta, il marker e la sua scrittura;
    - `TestToolContractInputsRecorded` (33): i casi da a) a j) del brief, più il cambio vero in mezzo al rumore, il
      marker vuoto e un checkout sotto una cartella nascosta;
    - `TestToolContractInputsWithoutARecord` (7): la regola vecchia come ripiego, verdi prima e dopo.
  - `test_test_server_preparation.py`, 8 test, «Contract 8»:
    - `dev` usa le stesse funzioni di `cli_base`;
    - l'impronta si prende prima di `cmd_api_sync` e si registra dopo la build npm;
    - con 4 passi falliti non si registra niente, e nemmeno con un tool mancante.
    - Ogni passo è sostituito dopo la barriera, e le due funzioni vere di `cli_base` sono vietate: niente scrive nella
      vera `frontend/build/`.
  - `test_static_route_confinement.py`, 10 test: 5 file nascosti, `/assets/../.build-debug`, il caso senza
    `200.html`, più 3 guardie (`robots.txt`, un font, `fonts/v1.2/x.woff2`).
  > **⚠️ Fuori pista** (dal test-author): il mio brief diceva «la cartella lasciata a adesso», ma `BUILD_MTIME` è
  > 1 800 000 000, cioè gennaio 2027, quindi «adesso» è più vecchio della build finta. I test usano date esplicite
  > (`NEWER_MTIME` e `OLDER_MTIME`) e non dipendono dall'orologio.
- ✅ **Rosso → cura → verdi → prova reale** (01:02–01:32, ogni passo a carico < 50; `files/runs/h24r-red.sh`,
  `h26-green.sh`, `h24r-slot.sh`, log in `files/runs/h26/`).
  - **Rosso**:
    - `utils runtime-isolation` **52/239**: 48 su `tool_contract_fingerprint` mancante, 1 su `_tool_contract_folders`, 1
      sul marker, 2 sull'elenco di oggi, che conta le cartelle e i `.py` nascosti;
    - `utils test-server-preparation` **8/83**, tutti sulla barriera;
    - `utils static-route-confinement` **7/29**: il contenuto del file nascosto torna indietro.
    - Nessun rosso fuori dalle classi nuove.
  - **Cura** applicata, uguale byte per byte alla prova a secco (`cmp`, 3 file, +84/−19).
    - Sonda sul vero albero: 69 ingressi, 8 cartelle, nessun nascosto.
    - Un percorso radice che non esiste dà un elenco vuoto, senza errori.
  - **Verdi**:

    | Selettore | Risultato |
    |---|---|
    | `utils test-runner-cli` | 671/671 |
    | `utils runtime-isolation` | 291/291 |
    | `utils test-server-preparation` | 91/91 |
    | `utils static-route-confinement` | 36/36 |
    | `utils check-frontend-build` | 14 |
    | `utils dev-cli-docker` | 96 |
    | `services static-cache-policy` | 26 |
    | `services security-headers` | 15 |
    | `services managed-headers` | 169 |
    | `services app-lifecycle` | 51 |
    | `check-orphans` | verde |
    | `utils nosniff-content-types` | 28/30, poi 30/30 dopo la riparazione |

  > **⚠️ Fuori pista**: `utils nosniff-content-types` ha dato 2 rossi. Verdetto (`test-triage`): **assunzione**. Il
  > campionatore del test sceglie un file per estensione nella vera `frontend/build` e aveva preso `.build-debug` per i
  > file senza estensione; H-28 ora lo rifiuta di proposito. Il `.json` passava solo perché il file più piccolo non era
  > `.cache_manifest.json`. Riparazione (test-author, +9/−2): il campione salta i file nascosti fuori da `_app/`, che
  > il mount serve senza filtro. **30/30** sulla build ricostruita, che contiene tutti e tre i file nascosti.
  - **Prova reale, slot 2 del coordinatore** (01:18–01:28, porta 6181):
    - `api http-compression` **10/10**. Il runner ha ricostruito il frontend con il vero `cmd_fe_build` («Frontend
      sources changed, rebuilding…», build debug come prima) e ha scritto `.tool-contract-inputs`, uguale all'impronta.
    - Sul vero albero:

      | Situazione | Regola nuova | Regola vecchia |
      |---|---|---|
      | subito dopo la build | fresca | fresca |
      | `.DS_Store` creato in `backend/app/schemas` | fresca | stale |
      | `.DS_Store` tolto | fresca | stale |
      | un `.py` aggiunto con data più vecchia della build | stale (solo l'elenco lo vede) | — |
      | quel file tolto | fresca | stale |

    - Il server della corsia (`dev.py server --test`), avviato dopo, non ha ricostruito niente.
    - `GET /.build-debug`, `/.tool-contract-inputs`, `/fonts/noto-color-emoji/.cache_manifest.json` e
      `/assets/../.build-debug` (con `--path-as-is`) danno 200 `text/html` con la pagina della SPA (`200.html`,
      confronto sha256). `/robots.txt` e `/manifest.json` danno il file, con `text/plain` e `application/json`.
    - Server fermato con il gruppo di processi; la porta 6181 ha 0 processi in ascolto.
  - **Statici**:
    - ruff e black sui 5 file di test: 0 → 0, come a HEAD;
    - produzione: `_cli.py` e `static_site.py` puliti; `cli_base.py` ruff pulito, black da 15 a 14 pezzi, e nessuno
      sulle righe nuove; `dev.py` ha gli stessi 10 reperti ruff e gli stessi 41 pezzi black di prima.
- ✅ **Doc** (docs-writer, 01:33–01:40; pagine per sviluppatori senza traduzioni):
  - `test-walkthrough/front-overview.md`, il punto «Builds the frontend, when needed»: gli ingressi dei codec dei Tool
    si confrontano con l'impronta che l'ultima build riuscita ha registrato. Contano un file aggiunto, tolto o
    rinominato, anche con una data vecchia; non contano `.DS_Store`, i file nascosti e `__pycache__/`. Senza la
    registrazione valgono le date delle cartelle.
  - `architecture/overview.md`, «Server Startup»: il catch-all serve il file nominato dopo aver risolto i `..`; un
    percorso fuori dalla build o con un nome nascosto riceve `200.html`.
  - `architecture/security.md`: nel riassunto del test `nosniff-content-types`, i file nascosti fuori da `_app/` non
    vengono campionati.
  - `dev_workflow.en.md:132`: la ragione «missing or outdated» comprende ora un ingresso aggiunto, tolto o
    rinominato.
  - Il docs-writer segnala due imprecisioni di quella pagina che c'erano già prima del lotto: il catalogo i18n
    mancante come motivo, e l'etichetta «built for another version». Restano come sono.
  - **Prove**: `dev.py mkdocs build` exit 0 in 112 s (l'unica riga «Warning» è l'avviso del team di Material);
    `check-links` exit 0, **97** link validi; `git diff --check` pulito.
- **Residui per il backlog**:
  - **H-29**: il mount di `/_app` e `/mkdocs` servono ancora i file nascosti. Nell'immagine non ce ne sono, ma su un
    Mac di sviluppo un `.DS_Store` del Finder dentro `frontend/build/_app/` sarebbe servito.
  - **H-30**: nel ramo `--log-file` di `main()` (`python -m scripts.test_runner`), `_snapshot_log_dir_db()` non ha il
    `try/finally` che ha `_dispatch_test_command`. Lo ha notato il test-author di H-26.
  - Dai test-author: le descrizioni del catalogo dei tre selettori (`_backend_utils.py`) non nominano i contratti
    nuovi. Non le tocco, perché le descrizioni del catalogo non sono mie.

### Revisioni della notte (2026-10-17) — su richiesta del coordinatore, sola lettura

- **B4** (worktree `e-alfy-miniature-telegram`, non committato, letto con `git --no-optional-locks`), alle 00:55:
  **OK sul codice, con 3 correzioni di doc.**
  - `get_instance_backup_options` in `ALLOWED_WHEN_BLOCKED` rispetta le regole.
    - Rientra nella decisione 12 (il backup completo di un amministratore).
    - È una GET `require_admin` che non avvia niente e dà solo le regole della password.
    - Sta in lista per funzione e il test la fissa.
    - Il match regge con `NoInputEchoRoute`: la classe avvolge solo `get_route_handler`, quindi `scope["endpoint"]`
      resta la funzione originale.
  - `secure.py` legge solo con `instance_key_status()` e `read_secret_file`, e non crea mai la chiave.
    - «Never raises» è vero: `read_secret_file` trasforma in `SecretFileError` ogni errore di lettura.
    - Il testo esportato è quello da cui l'istanza deriva le sue chiavi: anche `_read_generated_key` passa da
      `read_secret_file`.
  - Da correggere:
    - `backup/instance.py:15` dice «The four routes» (sono cinque);
    - in `developer/architecture/security.md:751` alla tabella dell'allowlist manca la rotta delle opzioni;
    - in `admin/hosting_providers.en.md:313` le rotte che chiama la card di blocco non nominano
      `GET /backup/instance/options`.
    - Nessuna delle due pagine ha traduzioni.
  - Facoltativa: la docstring di `derive_key_from`. Anche un archivio protetto lascia fuori una chiave data
    dall'ambiente.

### Lotto «H-27: `profile_default` controlla il tipo del valore del profilo» (2026-10-17, notte) — ✅ provato

> **Via** del coordinatore (01:50): «Next is H-27», dopo il commit del lotto H-26/H-24r/H-28 (`b34f5e990` …
> `063d2aa42`, entrato in dev `40a76bf1a`; più la riga del CHANGELOG per H-28 in `5beecac3d`). Base: fast-forward del
> coordinatore a `5beecac3d`, verificato pulito. Origine: E, R13-SEC3; il testo originale non è nel repo, solo le due
> voci del backlog che ne derivano (H-27, X-R36).

1. ✅ **Analisi** (01:50–02:00, sola lettura).
   - `profile_default(name, fallback)` (`config/__init__.py` ~576) restituisce `cast(T, values[name])`: nessun
     controllo. L'unico lettore è `backup_max_upload_mb()` (`config/backup.py:78`, di B), con ripiego `0` = nessun
     limite.
   - I suoi due chiamanti (`api/v1/backup/restore.py`) catturano solo `BackupConfigError`:
     - `_upload_limit()` calcola `limit_mb * _MEGABYTE if limit_mb else None`, quindi con `None` nel profilo non
       applica **nessun limite**: è il «fail-open» di E;
     - `_readable_limit_mb()` lo mostrerebbe come limite illeggibile.
   - **Cosa è già coperto quando girano i test**, per la voce di oggi:
     - `test_managed_lists_the_decided_variables_with_their_types` (`services profile-defaults`) confronta
       `ENVIRONMENT_PROFILE_DEFAULTS["managed"]` con la tabella decisa, valore e tipo esatto: una voce tolta o `None`
       fa diventare rosso il test;
     - le prove API di B (`test_backup_restore.py:535`, `test_backup_restore_apply.py:1162`) fissano «managed-unset →
       500» attraverso l'endpoint.
   - **Cosa non è coperto**:
     - (1) quando l'app gira, niente impedisce a un valore del tipo sbagliato di passare;
     - (2) per un lettore futuro, nessun test confronta il tipo del ripiego con quello della voce. La tabella decisa
       del test fissa il valore che il lavoro dichiara, non il tipo che il lettore si aspetta: una voce `None` scritta
       in entrambe le tabelle passerebbe.
   - **Cura proposta**, solo file miei:
     - `profile_default` controlla il tipo esatto: `type(value) is type(fallback)`, così `True` non vale come `int` e
       `60` non vale come `60.0`, come già la regola stretta di `PROFILE_DEFAULTS`. Un tipo diverso alza
       `ProfileDefaultError(TypeError)`, con un messaggio che nomina variabile, profilo, i due tipi e la tabella; il
       lettore non lo legge mai. Il valore è una costante del codice, mai un segreto: si può citare.
     - Un test statico generico: ogni chiamata `profile_default(NOME, <letterale>)` delle sezioni di `config/` ha un
       ripiego dello stesso tipo esatto della voce di ogni profilo che elenca `NOME`.
     - Più i casi a runtime: `None`, `"500"`, `500.0` e `True` per un ripiego `int`, eccetera; il valore giusto torna
       così com'è; il self-hosted non cambia; più il caso di E, il lettore vero di B con `None` nel profilo, che alza
       invece di dare «nessun limite».
   - **Scelta, documentata**: nessun controllo all'avvio. La proposta del backlog diceva «un errore chiaro
     all'avvio», ma il tipo atteso lo conosce solo il lettore, e i lettori girano quando servono (B ha scelto un 503
     al momento dell'uso per i suoi errori dell'operatore). La tabella è codice: il test statico la ferma prima del
     rilascio, e a runtime il lettore si ferma invece di ripiegare.
     - Con la cura, un valore sbagliato fa rispondere 500 alle due rotte di B, non 503. Se B vuole il suo 503, gli
       basta catturare `ProfileDefaultError` in `_upload_limit()` e in `_readable_limit_mb()`: lo segnalo, il file è
       suo.
   - `PROFILE_DEFAULTS` (i campi di `Settings`): la convalida stretta del test (d) già controlla ogni valore contro il
     tipo del suo campo. A runtime niente, perché `get_settings()` ricostruisce `Settings` a ogni chiamata. Resta
     così: E ha segnalato `profile_default`.
   - Doc: `developer/architecture/settings.md` ~58 («`profile_default()` converts nothing (a `cast`)») e l'elenco
     delle guardie lì vicino. Nessuna traduzione.
   - Selettori: `services profile-defaults` e `services config-env-example`; `api backup-restore` e
     `api backup-restore-apply` solo se la build della corsia è fresca, altrimenti in uno slot.
2. ✅ **Rossi, doc e cura a secco** (02:00–02:08, in parallelo).
   - **Rossi** (test-author, solo `test_profile_defaults.py`): da 52 a 88 casi; previsti 11 rossi e 77 verdi.
     - `test_profile_default_error_is_a_type_error`;
     - (g) 9 tipi sbagliati: `None`, `"500"`, `500.0`, `True` per un ripiego `int`; `1` e `None` per `bool`; `60`
       per `float`; `None` e `0` per `str`. Ognuno deve alzare l'errore, con un messaggio che nomina variabile,
       profilo, i due tipi e la tabella;
     - (g) 18 casi self-hosted o con profilo non impostato, che restituiscono il ripiego stesso;
     - 4 casi del tipo giusto, che restituiscono la voce;
     - il caso di E con il lettore vero `backup_max_upload_mb()` e `None` nel profilo, più la sua guardia (500, un
       `int`);
     - (h) la guardia statica `type_mismatches()` e il suo autotest. Il test-author ha aggiunto anche il controllo
       che ogni voce sia letta da una chiamata trovata.
     - I tre test vecchi con ripiego `object()` per una variabile elencata ora usano `type(expected)()`.
     > **⚠️ Fuori pista** (dal test-author): `None` passa se anche il ripiego è `None`, perché il controllo è sul
     > tipo esatto. Il lettore di oggi usa `0`; la docstring del test lo dice. Inoltre la descrizione del catalogo di
     > `services profile-defaults` nomina solo H-17: non è mia, non la tocco.
   - **Doc** (docs-writer): `developer/architecture/settings.md`, al posto della frase sul `cast`, il controllo
     (tipo esatto, `ProfileDefaultError`, il lettore si ferma; nessun controllo all'avvio, e perché). Nell'elenco
     delle guardie i due controlli nuovi; nell'istruzione per aggiungere una variabile, «un ripiego letterale del tipo
     della variabile».
   - **Cura a secco** (`files/h27/apply_cure.py`): `ProfileDefaultError(TypeError)` e il controllo in
     `profile_default`; ruff e black puliti.
3. ✅ **Rosso → cura → verdi** (02:08–02:09; il resto è fermo per il congelamento della galleria, carico 160).
   - **Rosso**: `services profile-defaults` **11 failed / 77 passed**, la previsione. 9 casi restituiscono il valore
     sbagliato, il lettore restituisce `None` (il fail-open di E), e `ProfileDefaultError` manca.
   - **Cura** applicata, uguale byte per byte alla prova a secco.
   - **Verdi** (gli ultimi due a carico tornato sotto 50, alle 02:28):

     | Selettore | Risultato |
     |---|---|
     | `services profile-defaults` | 88/88 |
     | `services config-env-example` | 38/38 |
     | `services config-misc` | 12/12 |
     | `services config-package` | 843/843 |

   - **Statici** (02:32–02:39, `files/runs/h27-finish.sh`): ruff e black 0 → 0 su `config/__init__.py`,
     `instance_block.py` e `test_profile_defaults.py`; `mkdocs build` exit 0, senza avvisi oltre al banner del team di
     Material; `check-links` **97**; `git diff --check` pulito.
   - Non eseguiti, per scelta: `api backup-restore` e `api backup-restore-apply`. Farebbero ricostruire il frontend
     della corsia, stantio dopo il fast-forward, e sono vietati fino alle 03:30. Il lettore vero è coperto dentro il
     processo.

### Mini-lotto «La docstring di `instance_block.py`: `POST /email/verification/resend`» (2026-10-17, notte) — ✅ provato

> Da E, via coordinatore (02:06): E-11 si appoggia a `POST /email/verification/resend`, che EVA-017 fissa fuori da
> `ALLOWED_WHEN_BLOCKED`, ma la docstring (:21-25) non lo nomina fra le rotte pubbliche che, a istanza bloccata,
> rispondono 401.

- ✅ Verificato: `resend_email_verification` (`email.py:190`) non ha dipendenze di sessione, quindi è pubblico e
  fuori dalla lista. `security.md` non elenca queste rotte per nome; `developer/backend/email.md:935` dice già che
  `/verification/resend` non vuole sessione. `EVA-017` non è ancora in questo albero (ramo di E).
- ✅ Docstring: «the email verification ``POST /email/verification/confirm`` and its new link
  ``POST /email/verification/resend``», con il resto del paragrafo riavvolto a 120 colonne. Uguale alla prova a
  secco; ruff e black puliti. L'insieme delle righe lunghe è invariato.
- ✅ Controllo d'import (02:32): il modulo si importa, `ALLOWED_WHEN_BLOCKED` ha 23 voci, `resend` è nella docstring.
  `api instance-block` non l'ho eseguito: è un passo pesante, vietato fino alle 03:30, e per una docstring non serve.

### Lotto «H-29 e H-30: i dotfile di `/_app` e `/mkdocs`; la fotografia del DB anche quando il corpo fallisce» (2026-10-17, notte) — ✅ provato

> **Via** del coordinatore (02:45): «Next: H-29 and H-30 (small), then the reviews of A8a and Z-20». H-27 è entrato
> (`51dd43926` … `c1c7cea39`, dev `bfdc1f72c`); base fast-forward a `bfdc1f72c`, verificata pulita. **H-31** (E-11,
> `blocked` in `/system/instance`): il coordinatore (02:50) dice di non farlo ora, perché E risolve E-11 nei suoi file
> (un 401 `INVALID_CREDENTIALS` sulla sola `resend`); resta nel backlog come voce bassa e facoltativa.

1. ✅ **Analisi** (02:45–02:55, sola lettura).
   - **H-29**:
     - `install_static_site()` monta `/_app` con `ImmutableStaticFiles(directory=FRONTEND_BUILD_DIR / "_app")`. Starlette
       (`StaticFiles.get_response`) serve qualunque file che trova, nomi nascosti compresi;
     - `mkdocs_static()` serve il file che `confined_path` trova sotto `SITE_DIR`, senza filtro.
     - **Cura**: in `ImmutableStaticFiles` un `get_response` che, per un percorso con una parte nascosta (già
       normalizzato da `get_path`, quindi senza `..`), alza il 404 di Starlette, come per un file che manca. In
       `mkdocs_static()` lo stesso controllo dopo `confined_path`, con il 404 della documentazione.
     - Il controllo si generalizza in `_hidden_below(root, target)`. `_hidden_in_build()` resta, perché doc e test lo
       citano.
     - Test: il mount di `/_app` fissa la sua cartella quando gira `install_static_site()`, quindi
       `test_static_route_confinement.py` non lo copre. I casi nuovi usano un'app fresca su una build finta, come fa
       già `test_nosniff_content_types.py` (~318).
     - Il campionatore del test nosniff toglie l'eccezione `_app/` della riparazione di H-28: nessun file nascosto
       è servito, in nessuno dei due alberi.
   - **H-30**: nel ramo `--log-file` di `main()` va lo stesso `try/finally` di `_dispatch_test_command`, intorno a
     `_timed_run(...)`. Il test riusa la fixture `entry_steps` di H-26 con un corpo che alza.
2. ✅ **Rossi, doc e cure a secco** (02:55–03:00, in parallelo).
   - **Rossi H-29** (test-author, `test_static_route_confinement.py` e `test_nosniff_content_types.py`):
     - 15 casi nuovi:
       - `/mkdocs`: 5 nascosti, `.DS_Store`, `assets/.hidden.css`, `.hidden-dir/page.html`, `.hidden-dir/` e
         `assets/../.DS_Store`, più 3 guardie;
       - `/_app`, su un'app fresca con `install_static_site()` sopra una build finta: 4 nascosti più 3 guardie.
     - Il rifiuto si confronta con la risposta a un file mancante sulla stessa rotta: stato, tipo e corpo uguali,
       nessun testo scritto nel test.
     - Nel test nosniff via `APP_MOUNT_FOLDER`: nessun file nascosto si campiona, in nessuno dei due alberi.
   - **Rossi H-30** (test-author, `test_test_runner_cli.py`): 6 casi, cioè `main()` e `dev.py test`, ciascuno con
     `--log-file` e corpo che alza, `--log-file` e corpo che restituisce 0, senza `--log-file` e corpo che alza.
     Rosso solo il primo su `main()`. La traccia chiede la fotografia **dentro** il `with` di `tee_output`, come in
     `_dispatch_test_command`.
   - **Doc** (docs-writer):
     - `architecture/overview.md:94`: `/_app` e `/mkdocs` rifiutano anche loro un nome nascosto, ciascuno con il suo
       404. La prima stesura diceva che anche il mount usa `_hidden_below()`; corretta, perché il mount guarda da sé
       le parti del percorso che Starlette gli passa.
     - `architecture/security.md:1579`, il riassunto del test nosniff: nessun file nascosto si campiona.
     - **In più, dal coordinatore (02:58, da E, E-11)**: `security.md:801`, la riga «Public routes outside the list»
       nomina ora `POST /email/verification/confirm` e `POST /email/verification/resend`, con i link alle ancore di
       `backend/email.md`, senza codici d'errore.
       - E-11 (`bca4bd6d3`) non è nella mia base, ma non tocca `security.md`.
   - **Cure a secco** (`files/h29/apply_cure.py`):
     - `static_site.py`: `_hidden_below(root, target)`, usata da `_hidden_in_build()` e da `mkdocs_static()`; più
       `ImmutableStaticFiles.get_response()` con il 404 di Starlette e la docstring del modulo;
     - `_cli.py`: il `try/finally` dentro il `with`.
3. ✅ **Rossi → cure → verdi** (03:00–03:08, ogni passo a carico < 50; `files/runs/h29-*.sh`, log in
   `files/runs/h29/`).
   - **Rossi**:
     - `utils test-runner-cli` **1 failed / 676 passed**: la fotografia non viene presa, `assert 0 == 1`;
     - `utils static-route-confinement` **9 failed / 42 passed**: ogni file nascosto torna indietro con 200;
     - `utils nosniff-content-types` 30/30, verde prima e dopo.
   - **Cure** applicate, uguali byte per byte alle prove a secco.
   - **Verdi**:

     | Selettore | Risultato |
     |---|---|
     | `utils static-route-confinement` | 51/51 |
     | `utils nosniff-content-types` | 30/30 |
     | `utils test-runner-cli` | 677/677 |
     | `services static-cache-policy` | 26 |
     | `services security-headers` | 15 |
     | `services app-lifecycle` | 51 |

   - **Statici**: ruff e black 0 → 0 sui 5 file Python; `mkdocs build` exit 0, senza avvisi oltre al banner;
     `check-links` 97; `git diff --check` pulito.
   - Non eseguita: la prova con un server vero e i `curl`, come per H-28. Avviare il server della corsia farebbe
     ricostruire il frontend, stantio dopo il fast-forward: un passo pesante. Le prove ASGI usano già il mount vero
     di Starlette e le rotte vere, su un'app fresca.
- **Backlog**:
  - nuova **H-31** (bassa, facoltativa): `blocked` nel pubblico `/system/instance`;
  - nuova **H-32** (bassa, da A, A-35): i `float` dei corpi accettano `1E+400`.
  - nuova **H-33** (bassa, da E, R13-SEC4): un gestore di `ResponseValidationError` che registra senza il valore.

### Lotto «H-32: i `float` delle richieste e i valori infiniti» (2026-10-17, notte) — ✅ provato

> **Via** del coordinatore (03:11): «H-32 now, analysis first (inventory … and the proposal: `allow_inf_nan=False` in the
> base or field by field), then reds». Da A (A-35): un `float` semplice nel corpo accetta `1E+400` e risponde 200; se
> una rotta lo restituisce, il renderer di Starlette (`allow_nan=False`) fallisce con un 500. Base `8ef48dedb`. H-33
> aspetta l'ingresso di A7b-2, perché tocca `main.py` accanto alla riga di A.

1. ✅ **Analisi** (03:15–03:35, sola lettura; script in `files/h32/`).
   - **Inventario sull'app vera** (`routes_inventory.py`, con `iter_route_contexts`, come `test_instance_block.py`):
     177 rotte API, 67 con un corpo. I `float` raggiungibili da una richiesta (corpi, modelli annidati, parametri di
     query e di percorso) sono **6**:
     - 5 campi dei segnali (`SignalLineCrossoverRequest.epsilon` e `relative_epsilon`,
       `SignalThresholdCrossingRequest.epsilon`, `relative_epsilon` e `threshold`;
       `POST /assets/prices/query` e `POST /fx/currencies/convert`): hanno già `AllowInfNan(False)`, e rifiutano
       `inf`, `nan` e `1E+400`;
     - `PluginSettingWriteItem.value` (`str | int | float | bool | None`, `PATCH /settings/plugins/bulk`, di X): lo
       schema accetta `inf` e `nan`, ma il servizio li rifiuta prima di salvare (`fields.validate_value`:
       `math.isfinite` → `SettingValueError`).
     - Nessun parametro `float` di query o di percorso. `Decimal` rifiuta `inf` e `nan` di default.
     - Gli altri 11 campi `float` degli schemi (17 in tutto, `h32_inventory.py`) servono solo alle risposte o ai
       modelli interni.
   - **Il 500 di A, verificato**: con FastAPI 0.141.1 una rotta **con** `response_model` risponde **200 `{"x": null}`**
     sia a `1E+400` sia a `NaN`, perché la serializzazione passa dal JSON di pydantic, che scrive `null`. Il 500 resta
     solo per una rotta senza `response_model` che restituisce valori grezzi. Il rischio vero di un `float` infinito
     in ingresso è quindi silenzioso: un valore salvato e usato che poi si legge `null`.
   - **Conclusione**: oggi nessun `float` di una richiesta arriva a essere salvato o restituito. Il buco è uno solo, ed
     è nello schema di X, coperto dal servizio.
   - **Reperto per X**, fuori da H-32: un intero di 401 cifre in `value` arriva a `math.isfinite()`, che alza
     `OverflowError`. Il percorso di scrittura (`service.py:255`) cattura solo `SettingValueError`, quindi
     `PATCH /settings/plugins/bulk` risponde 500. Solo per un admin; basso.
   - **Proposta**:
     - (a) **Niente `allow_inf_nan=False` nella base.** `StrictModel` sta sotto centinaia di modelli, quasi tutti di
       risposta o interni (AI Export, rischio): un `NaN` calcolato oggi diventerebbe un'eccezione dentro i servizi.
       Molti rischi, nessun guadagno sulle richieste.
     - (b) **Campo per campo**, più una **guardia generica** (mia): un test che percorre tutte le rotte con
       `iter_route_contexts` e chiede che ogni `float` raggiungibile da una richiesta rifiuti `inf` e `nan` già nello
       schema. Un `float` nuovo senza protezione diventa rosso al momento del test, e il messaggio nomina rotta,
       modello e campo.
     - (c) Per `PluginSettingWriteItem.value`: `AllowInfNan(False)` sul ramo `float` di `PluginSettingPlainValue`,
       una riga nel file di X. Oppure la guardia lo tiene in un elenco di eccezioni motivate («controllato da
       `validate_value`»). Consiglio la riga.
   - Chiesti al coordinatore: chi scrive la riga di X; l'OK da writer per registrare il file nuovo della guardia
     (`services request-float-inputs`, pure, in `_backend_services.py`).
   - **Decisioni** del coordinatore (03:22): (a) no; (b) e (c) sì.
     - La riga di X la scrivo io e X la rivede al checkpoint.
     - Ho l'OK da writer su `_backend_services.py` per `request-float-inputs`, in aggiunta: anche A8a potrebbe
       registrare qualcosa nel runner stanotte.
     - L'`OverflowError` passa a X come X-R43.
   - **Intermezzo, revisione di Z-20** (03:25, in sola lettura, `e-alfy-potential-sniffle` `3235837ad`): **OK**, le
     quattro condizioni dell'opzione A sono rispettate e fissate dai test. Il controllo positivo del gate
     (`verificationApi.ts → instanceBlock.svelte.ts`) regge anche dopo E-11, che è in dev ma non nella base di Z.
     Nota facoltativa: con HMR, in sviluppo, si accumula un listener a ogni ricaricamento (`import.meta.hot?.dispose`).
2. ✅ **Guardia, doc e prove a secco** (03:25–04:05).
   - **Guardia** (test-author, file nuovo `backend/test_scripts/test_services/test_request_float_inputs.py`, 33 test):
     - `collect_request_floats()` percorre tutte le rotte con `iter_route_contexts` e il dependant effettivo: corpi,
       modelli annidati, parametri di query, percorso, header e cookie, alias PEP 695 compresi. Giudica ogni `float`
       con un `TypeAdapter` su tutta l'annotazione, con i metadati del campo e la `allow_inf_nan` del modello.
       Quello che non sa leggere è un «problema», mai saltato.
     - **Barriere**: almeno 150 contesti sotto `/api/v1` e almeno 60 con un corpo; i cinque campi dei segnali
       trovati; nessun problema.
     - **La regola**: un caso per foglia trovata, più un elenco fisso delle sei di oggi come pavimento.
     - **Autotest** su un'app sonda con router inclusi e annidati: 17 casi parametrizzati, più quelli che non sono
       foglie e il caso dataclass.
     - **4 casi end-to-end** in processo.
     - Previsto oggi: 32 verdi e 1 rosso (`PluginSettingWriteItem.value`).
   - **Doc** (docs-writer): `architecture/security.md:714–745`, nuova sottosezione «🔢 Numbers in Requests
     {: #request-numbers }»: la regola, il perché, perché non nella base, la guardia, le sei di oggi. I segnali usano
     `FiniteFloat` di pydantic. Ha due link interni verificati.
   - **Registrazione** (OK da writer, in aggiunta): `services_request_float_inputs()` e
     `add_test(cat, "request-float-inputs", …, isolation="pure")` accanto a `profile-defaults`. Applicata prima del
     rosso, uguale alla prova a secco.
   - **Prove a secco**: la riga di X e la registrazione, ruff e black 0 → 0. Impronta OpenAPI prima della cura:
     `b91bc138f73c0ee0`.
   > **⚠️ Fuori pista**, due reperti accanto a H-32:
   > - **Un 500 al posto del 422** (verificato in processo): con il gestore standard dei 422 di FastAPI, un valore
   >   non finito su un campo già finito (`FiniteFloat`, `AllowInfNan(False)`) dà **500**, perché l'errore ripete
   >   l'`input` (`inf`) e il renderer di Starlette lo rifiuta. Oggi tocca le rotte dei segnali
   >   (`POST /assets/prices/query` e `POST /fx/currencies/convert`, dopo l'autenticazione). Il gestore globale di A
   >   (A7b-2), che toglie l'`input`, lo cura. La rotta dei plugin usa `_NoInputEchoRoute` (`plugin_settings.py:57`):
   >   dopo la riga di X, un valore infinito lì riceve un 422 leggibile.
   > - **JSON libero nelle richieste**: i campi `Any` o `JsonValue` raggiungibili accettano `Infinity` al loro
   >   interno:
   >   - `FAProviderAssignmentItem.provider_params` e `FAProviderProbeRequest.provider_params` (`dict[str, Any]`, di
   >     X: `POST /assets/provider` e `/assets/provider/probe`);
   >   - `RiskAnalyticRequest.parameters` (`JsonValue`, `POST /risk/query`, nessun validatore);
   >   - `ToolComputeItem.parameters` sta in un modello con `allow_inf_nan=False`, da verificare;
   >   - `SignalRequest.params` è già protetto (`ensure_json_safe`).
   >   Sono fuori dalla regola sui `float`: li segnalo al coordinatore per i proprietari.
3. ✅ **Rosso → cura → verdi → prova reale in processo** (04:05–04:16, ogni passo a carico < 50;
   `files/runs/h32-green.sh`, log in `files/runs/h32/`).
   - **Rosso**: `services request-float-inputs` **1 failed / 32 passed**: «PluginSettingWriteItem.value (str | int |
     float | bool | None) lets inf, -inf, nan, 1E+400 through; reached by PATCH /api/v1/settings/plugins/bulk».
     `check-orphans` verde, con il file nuovo registrato.
   - **Cura** applicata, uguale alla prova a secco: `PluginSettingPlainValue = str | int | Annotated[float,
     AllowInfNan(False)] | bool` (file di X; X la rivede).
   - **Verdi**:

     | Selettore | Risultato |
     |---|---|
     | `services request-float-inputs` | 33/33 |
     | `services plugin-settings-contract` | 194 |
     | `services plugin-settings-crypto` | 30 |
     | `services plugin-settings-runtime` | 120 |
     | `services plugin-settings-service` | 96 |
     | `services plugin-settings-guards` | 25 |

   - **OpenAPI invariato**: `b91bc138f73c0ee0`, 823 531 byte, prima e dopo. Niente `api sync`.
   - **Prova sulla rotta vera, in processo** (`files/h32/real_route_probe.py`): `PATCH /api/v1/settings/plugins/bulk`
     sull'app vera, con autenticazione e sessione sostituite. La validazione fallisce prima dell'endpoint, quindi
     nessun DB. `Infinity`, `-Infinity`, `NaN` e `1E+400` → **422**, senza `input` ripetuto (`_NoInputEchoRoute`),
     tipi `bool_type`, `finite_number` e `string_type`, cioè i rami dell'unione.
   - **Statici**: ruff e black 0 → 0 su `plugin_settings.py` e `_backend_services.py`, e 0 sul file nuovo;
     `mkdocs build` exit 0; `check-links` 97; `git diff --check` pulito.
   - Non eseguito: `api plugin-settings`. È un passo pesante: farebbe ricostruire il frontend della corsia, e c'è il
     blocco della galleria fino alle 04:45. Va nel cancello del coordinatore.
- **Backlog**: **H-34** (bassa), il JSON libero delle richieste accetta `Infinity` al suo interno. I proprietari sono X
  (`provider_params` ×2) e J (`RiskAnalyticRequest.parameters`); `ToolComputeItem.parameters` è da verificare.

### Lotto «H-33: una risposta che rompe il suo modello finisce nel log senza il suo contenuto» (2026-10-17, notte) — ✅ provato

> **Via** del coordinatore (04:17): A7b-2 è in dev, quindi H-33 può partire. H-32 è entrato (dev `ec6aa2007`; la riga
> di X l'ha rivista il coordinatore). Base: fast-forward a `ec6aa2007`, verificata pulita. Disegno e OK da writer su
> `_backend_services.py` per `response-validation` (04:25). Origine: E, R13-SEC4.

1. ✅ **Analisi** (04:17–04:25, sola lettura).
   - FastAPI 0.141.1 registra di suo i gestori di `HTTPException`, `RequestValidationError` e WebSocket, non quello di
     `ResponseValidationError`. `ValidationException.__str__` scrive ogni errore con il suo `input`, e l'eccezione
     porta anche `body`.
   - Così, quando un endpoint restituisce ciò che il suo `response_model` rifiuta, `ServerErrorMiddleware` risponde
     500 «Internal Server Error» in testo semplice, e uvicorn scrive nel log un traceback che contiene la risposta:
     i dati dell'utente che l'ha chiesta.
   - A7b-2 ha messo il gestore dei 422 in `backend/app/api/validation_errors.py` (file di A), con una riga in
     `main.py`.
   - **Cura**:
     - `backend/app/api/response_validation.py`, nuovo e mio: `install_response_validation_handler(app)`, più una
       riga in `main.py` subito dopo quella di A, con l'import in ordine alfabetico;
     - il gestore registra in un solo evento di log il metodo, la rotta (il percorso modello) e l'endpoint, e per ogni
       errore solo `type` e `loc`. Mai l'`input`, né il `msg` (un validatore può costruirlo con il valore), né il
       traceback (il suo messaggio è `str(exc)`);
     - risponde lo stesso 500 di oggi.
     - ~~In più, la risposta ora attraversa i middleware dell'utente: il 500 riceve anche gli header di sicurezza e
       il CORS, che il 500 di `ServerErrorMiddleware` non aveva.~~
       > **⚠️ Fuori pista**, corretto dal docs-writer: era sbagliato. `SecurityHeadersMiddleware` risponde già il 500
       > di un'eccezione con gli header di sicurezza (il suo `except Exception:`), e poi la rialza; uvicorn la scrive
       > nel log. Cambia questo: l'eccezione si ferma al gestore, quindi niente traceback nel log, e il 500 diventa la
       > risposta del gestore, che attraversa anche gzip e CORS.
       > Inoltre il gestore usa di proposito `logger.error` e non `logger.exception`, contro la convenzione TRY400 di
       > `lint_gates.md`, perché il traceback riporterebbe `str(exc)` con gli `input`. Un commento nel codice lo
       > dice.
   - Doc: `architecture/security.md` «📜 Request Logs», più la frase di `architecture/overview.md:94` sui passi di
     `main.py`.
2. ✅ **Rossi, doc, cura a secco e registrazione** (04:25–04:40).
   - **Rossi** (test-author, file nuovo `backend/test_scripts/test_services/test_response_validation.py`, 10 casi):
     - il gestore installato una sola volta e senza toccare gli altri, e quello dell'app vera è lo stesso;
     - il gestore dei 422 di A ancora al suo posto;
     - 2 corpi rotti (un testo dove serve un numero; un numero mancante, il caso peggiore, perché l'`input` è
       l'oggetto intero): 500 in testo semplice, un solo evento di log con il logger del modulo, nessun marcatore né
       negli eventi né nei record di `caplog`, e l'eccezione non esce dall'app;
     - la rotta di un router incluso registrata con il percorso modello completo;
     - una risposta valida resta com'è;
     - il controllo senza gestore: il marcatore sta in `str(exc)`, cioè in quello che uvicorn avrebbe scritto;
     - una premessa: solo l'eccezione nomina per intero la rotta inclusa.
   > **⚠️ Fuori pista** (dal test-author, letto nel codice di FastAPI 0.141.1):
   > - `scope["route"]` è l'`APIRoute` del router, **senza** il prefisso di `include_router`: la prima cura avrebbe
   >   scritto `/auth/login` invece di `/api/v1/auth/login`. Il percorso modello completo sta nel pubblico
   >   `exc.endpoint_path` («GET /api/v1/…»): ora si usa quello, tolto il metodo;
   > - `endpoint_function` è una stringa e può valere `None`: il nome ora viene da `scope["endpoint"].__name__`;
   > - fuori perimetro: un endpoint generatore con elementi tipizzati (streaming di FastAPI) fallisce la convalida
   >   dopo l'inizio della risposta, e Starlette alza un `RuntimeError` concatenato, con `str(exc)` nel traceback.
   >   LibreFolio oggi non ne ha.
   - **Doc** (docs-writer):
     - `architecture/security.md:1732–1742`, un paragrafo in «📜 Request Logs»;
     - una frase alla fine della sezione di A sui 422, con il rimando;
     - `architecture/overview.md:94`, la chiamata nuova di `main.py`.
     - Ha corretto la mia analisi sugli header (sopra) e segnalato la trappola TRY400.
   - **Registrazione** (OK da writer): `services_response_validation()` e `add_test(cat, "response-validation", …,
     isolation="pure")` accanto a `request-float-inputs`.
   - **Cura a secco**: il modulo e la riga di `main.py`. Con l'input da stdin, ruff segnava I001 sull'import nuovo
     perché il modulo non esisteva ancora; a cura applicata, l'ordine è quello giusto.
3. ✅ **Rosso → cura → verdi** (04:42–04:45, ogni passo a carico < 50; `files/runs/h33-*.sh`, log in `files/runs/h33/`).
   - **Rosso**: `services response-validation` **6 failed / 4 passed**, tutti e 6 sulla barriera «response_validation.py
     is missing». `check-orphans` verde.
   - **Cura** applicata, uguale alla prova a secco.
   - **Verdi**:

     | Selettore | Risultato |
     |---|---|
     | `services response-validation` | 10/10 |
     | `services app-lifecycle` | 51 |
     | `services security-headers` | 15 |
     | `services request-float-inputs` | 33 |
     | `utils static-route-confinement` | 51 |

   - **Statici**: ruff e black 0 su `main.py`, sul modulo, su `_backend_services.py` e sul test; `mkdocs build` exit 0;
     `check-links` 97; `git diff --check` pulito.
   - Non eseguito: `api validation-errors` di A, un passo pesante che va nel cancello. Il gestore dei 422 è ancora al suo
     posto: lo controlla il caso 3.

### Wiki-file delle scoperte della notte (2026-10-17, mattina presto) — ✅ fatto

> Chiesto dal coordinatore (04:46), dopo l'ingresso di H-33 (dev `5bba93280`, base fast-forward verificata pulita):
> un `wiki-file` delle scoperte della piattaforma, ognuna con il suo perché, con `check_source_paths.py` verde.

- Sei pagine nuove in `LibreFolio_devWiki/wiki/`, in inglese, verificate sul codice a `5bba93280`:
  - `problems/frontend-build-looked-stale-for-files-it-never-bundles` (H-24 e il residuo: l'elenco registrato al
    posto delle date delle cartelle, con la tabella della prova reale);
  - `problems/static-site-served-hidden-build-files` (H-28 e H-29);
  - `decisions/test-runner-refuses-test-names-it-cannot-apply` (H-26, più la nota su H-30);
  - `decisions/request-floats-refuse-inf-and-nan` (H-32: inventario, opzioni, decisione, H-34 e X-R43);
  - `problems/response-validation-error-wrote-the-response-to-the-log` (H-33);
  - `concepts/fastapi-0141-routing-and-validation-gotchas`: i cinque comportamenti di FastAPI 0.141 misurati in
    processo, che stanno dietro H-32 e H-33.
- `index.md`: righe in testa a Decisions, Concepts e Problems, più una riga del registro cronologico per il 17/10.
  `log.md`: una voce `file`.
- `check_source_paths.py`: **7 percorsi inesistenti (12 occorrenze) su 4149**, gli stessi 7/12 di prima (su 4114),
  tutti preesistenti; nessuno in queste pagine.
- **Grafo**: non aggiornato. graphify non è disponibile in questo worktree, e il passo 6 della skill punta al
  checkout principale, che non leggo; la voce del log lo dice.
- Due correzioni prima di consegnare: la rotta dei plugin usa il `NoInputEchoRoute` comune di `api/no_echo.py`
  (portato da B4), non una copia sua; una frase poco chiara nella pagina dei file nascosti, riscritta.

### Lotto «H-36: dietro un proxy che uvicorn non considera fidato, il limite per indirizzo si fa da parte» (R13-SEC6 di E, N70, 2026-10-17, mattina) — in corso

> Chiesto dal coordinatore, urgente, prima dell'ingresso di A8a: dietro un proxy non configurato (l'immagine di
> default) il limite per indirizzo di A8a mette insieme tutti i visitatori, e 50 tentativi sbagliati bloccano
> l'accesso di tutti. Tre consegne: (1) un helper in `client_address.py` che A usa per saltare il limite per indirizzo;
> (2) un controllo di configurazione in `CONFIG_CHECKS`; (3) una frase nei documenti di installazione/Docker. Prima i
> rossi. Entra insieme ad A8a, o appena prima.
>
> **Punti vincolanti di E** (li verifica in review): rilevazione che il client non può provocare (peer privato,
> loopback o link-local **e** un header di inoltro, per richiesta; mai «header da un peer non fidato» da solo); i proxy
> pubblici restano alla configurazione, e il controllo *informa* quando gli header arrivano da un peer pubblico non
> fidato; facoltativo, a mia scelta, la voce più a destra di `X-Forwarded-For` come chiave.
>
> **Contratto concordato con A** (dal coordinatore): `forwarded_by_untrusted_proxy(request: HTTPConnection) -> bool`
> in `client_address.py`, vero quando: c'è `X-Forwarded-For`/`Forwarded`/`X-Real-IP`; `LIBREFOLIO_CLIENT_IP_HEADER` non
> dà l'indirizzo; uvicorn non ha applicato l'inoltro (`request.client.host` non è tra gli indirizzi di XFF); il peer è
> locale (loopback, RFC 1918, link-local, CGNAT 100.64/10, ULA/loopback IPv6). Il controllo del locale sta dentro
> l'helper.

**Analisi** (sola lettura, HEAD `333cead4d`, pulito; A8a = `66873b0c9`, non ancora in HEAD):

1. **uvicorn 0.52.4, verificato nel sorgente installato** (`uvicorn/middleware/proxy_headers.py`):
   - riscrive `scope["client"]` solo se il peer è in `trusted_hosts` (`--forwarded-allow-ips`, o `FORWARDED_ALLOW_IPS`,
     `127.0.0.1` di default); unisce tutte le righe `x-forwarded-for` con `", "`;
   - prende la prima voce non fidata da destra (con `*`, la prima), e la passa a `_parse_host_port`: `1.2.3.4:80` →
     (`1.2.3.4`, 80), `[::1]:80` → (`::1`, 80), un IP nudo → porta 0. Quindi, dopo una riscrittura, `client.host` è
     l'host di una voce di XFF, tolti porta e parentesi;
   - ignora `Forwarded` e `X-Real-IP`; l'app non può leggere la configurazione della fiducia (la flag della CLI non
     arriva all'app): resta il confronto di appartenenza concordato.
2. **Il «locale» ha già una casa**: `utils/runtime/network.py:classify_ip` (piano 36) dà `loopback` (127/8, ::1),
   `vpn` (100.64/10 e il /48 ULA di Tailscale), `lan` (10/8, 172.16/12, 192.168/16, 169.254/16, fe80::/10, fc00::/7),
   `public`, `unknown` (nessuno, non leggibile, non specificato, multicast); normalizza parentesi, zona e IPv4-mapped.
   È esattamente l'insieme concordato (lista di E + CGNAT di A). La usa già il controllo SMTP di E
   (`classify_ip(name) in ("loopback", "lan", "vpn")`). La riuso: nessuna seconda lista.
3. **Parsing delle voci di XFF**: `network._parse_ip` toglie già parentesi, porta (un solo `:`) e zona, come
   `_parse_host_port` di uvicorn. Diventa pubblica (`parse_ip`, 3 righe: la definizione e due chiamate), invece di
   copiare la logica di uvicorn.
4. **Chi chiama oggi**: `client_address(request)` in `auth.py:278` (registrazione, A) e in `email.py:159,204` (E);
   `client_rate_key` in `email/flows.py` e `email/verification.py`. A userà l'helper in `login_throttle`; E può usarlo
   per i suoi limiti per indirizzo (il controllo li copre comunque).
5. **Il controllo è a runtime**: all'avvio non è arrivata nessuna richiesta, quindi il controllo osserva quello che
   l'helper ha visto dall'avvio: solo nomi di header, mai un indirizzo (N58). All'avvio è `ok`; per il log c'è una riga
   per processo, alla prima osservazione di ogni classe.

**Progetto**:

- `client_address.py`:
  - `_FORWARDING_HEADERS = ("X-Forwarded-For", "Forwarded", "X-Real-IP")`;
  - `_untrusted_forwarding: dict[str, set[str]] = {"local": set(), "public": set()}`: i nomi visti, per classe del
    peer; i test lo svuotano come `_warned` (H-22: niente funzione solo per i test);
  - `forwarded_by_untrusted_proxy(request)`: nessun header di inoltro → falso; l'header configurato dà un indirizzo
    (`_one_address`, senza avviso: l'avviso resta di `client_address()`) → falso; peer `unknown` → falso; uvicorn ha
    seguito XFF (`parse_ip(peer)` uguale a `parse_ip` di una voce) → falso; altrimenti annota i nomi sotto `local` o
    `public` e dà vero solo per `local`;
  - la prima annotazione di ogni classe scrive una riga: `warning` per `local`, `info` per `public`, con `headers`
    (nomi) e nient'altro;
  - `untrusted_forwarding_seen(peer_class) -> tuple[str, ...]`: i nomi, nell'ordine di `_FORWARDING_HEADERS`; lo legge il
    controllo.
- `config_audit.py`: `check_client_address()` (`platform.client_address`): `warning`
  `instance.checks.clientAddress.untrustedProxy` se è stato visto un proxy locale non fidato, `info`
  `…publicForwarding` se solo peer pubblici, altrimenti `ok` `…ok`; `detail = {"headers": "X-Forwarded-For, …"}`.
  In `CONFIG_CHECKS` subito dopo `check_session_cookie`.
- i18n: tre chiavi `instance.checks.clientAddress.*` in `frontend/src/lib/i18n/instance/{en,it,fr,es}.json`, poi la
  build del catalogo.
- Documenti (docs-writer, solo inglese): un paragrafo in `admin/connection_checks.en.md#client-address`, una frase in
  `admin/docker_advanced.en.md` §2 che ci rimanda, il contratto in `developer/architecture/security.md`. Nessuno
  stamp: il debito di `connection_checks` è già H-5, `docker_advanced` si aggiunge a H-5.

**Decisioni mie** (dentro il perimetro):

- **CGNAT incluso**: è nel contratto concordato con A, e `classify_ip` lo tratta come `vpn` (Tailscale). Lo segnalo a E.
- **La voce più a destra di XFF come chiave (punto 3 di E): no, per ora.** Dietro un peer privato che non è un proxy
  che aggiunge (un client in LAN, o un proxy che passa l'XFF del client così com'è) quella voce la sceglie il client:
  ruotandola si aggira il limite, scrivendo l'indirizzo di un altro lo si blocca. Il salto non ha la seconda falla. La
  cura vera è configurare la fiducia, e il controllo la chiede.
- **Socket unix e peer senza indirizzo**: `unknown` → falso. LibreFolio gira su TCP (dev.py e Docker).
- **Conflitti con A8a**: A8a tocca `config_audit.py` (righe 19 e 22, gli import; dopo `check_log_level,`;
  `log_configuration_audit`) e `test_config_audit.py` (docstring (c), import, la fine di `CHECK_IDS`, `_configure`,
  `_accounts_checks`, i due test di (c)). Le mie righe stanno lontane da quei pezzi: l'import tra `email.checks` e
  `instance_key`, la funzione prima di `CONFIG_CHECKS`, la registrazione dopo `check_session_cookie,` (una riga
  invariata di distanza), in `CHECK_IDS` dopo `check_session_cookie`, i test in fondo al blocco (a). Il test d'ordine
  di A ricava le piattaforme dall'ordine di `CHECK_IDS`, quindi regge. Verifica con `git merge-file` prima del
  checkpoint.

**Rossi** (test-author, nessun comando lanciato): blocco nuovo in `test_client_address.py` (contratto dell'helper, la
prova con il vero `ProxyHeadersMiddleware` di uvicorn, l'annotazione e il log una volta per classe, nessun indirizzo nei
log) e test del controllo in `test_config_audit.py`.

**Selettori**: `services client-address`, `services config-audit`, `services config-package`,
`services config-env-example`, `utils i18n-*` se servono; ruff/black; `mkdocs build` e `check-links`; la build e il
controllo del catalogo i18n.

> **Aggiunta al contratto** (coordinatore, da E, adottata, 17/10 mattina): tutti i punti di chiamata (login,
> cambio password e profilo di A; resend, forgot e register di E) leggono già un indirizzo `None` come «nessun conteggio
> per indirizzo». Quindi H aggiunge `rate_limit_address(request) -> str | None`: `None` quando il predicato è vero,
> altrimenti `client_address(request)`. A e E lo chiamano al posto di una logica loro; la riga di log una volta per
> processo resta nell'helper di H. Scelta mia: `client_address()` viene letto per primo, così il suo avviso su un
> header configurato ma malformato non sparisce mai dietro il predicato.

1. ✅ **Cura in prova** (17/10, mattina): `files/h36/apply.py`, che scrive le copie in `files/h36/dry/` e niente nel
   worktree senza `--apply`.
   > **Note implementazione**:
   > - Ruff e black sono puliti sulle tre copie, come su HEAD.
   > - `git merge-file` contro `66873b0c9` (A8a) dà 0 conflitti, sia su `config_audit.py` sia su `.env.example`.
   > - Le quattro sorgenti i18n rifatte con `json.dumps(indent=2, ensure_ascii=False)` sono identiche byte per byte
   >   all'originale prima dell'aggiunta: la forma canonica è verificata.
   > - Starlette 1.6.0: `Headers.__contains__` e `getlist` mettono il nome in minuscolo. Il test `name in
   >   request.headers` vale quindi per qualunque maiuscola.
2. ✅ **Rossi** (test-author, che non ha lanciato nulla; 17/10, mattina).
   - `test_client_address.py`: paragrafo (h) nella docstring e un blocco (h) nuovo in fondo, 20 test e 238 casi.
     Coprono: il contratto dell'helper, Request e WebSocket, i peer locali, pubblici e illeggibili, il seguito di
     uvicorn, l'header configurato, la nota e il log una volta per classe, `untrusted_forwarding_seen`,
     `rate_limit_address`, il vero `ProxyHeadersMiddleware` di uvicorn su uno scope grezzo, e il controllo visto da fuori.
   - La barriera è la fixture `fresh_untrusted_forwarding`: rossi solo i test di (h), ognuno per conto suo.
   - `test_config_audit.py`: paragrafo (f), `check_client_address` in `CHECK_IDS` dopo `check_session_cookie`, e un
     blocco (f) in fondo (11 casi). Rosso all'import della raccolta, come accettato.
   - Comando: `files/runs/h36-red-1.sh` (`services client-address`). Esito: **122 passed, 238 errors**. Tutti i 238
     errori hanno lo stesso messaggio, «client_address.py has no _untrusted_forwarding, where
     forwarded_by_untrusted_proxy() notes … (H-36, N70)». I test da (a) a (g) restano verdi.
   > **⚠️ Fuori pista**: ruff I001 vuole l'import `from backend.app.services.platform import client_address as …`
   > subito dopo la riga `email.checks`, che A8a riscrive. Con `git merge-file` contro `4a93f1f54` (il ramo di A, che
   > discende da `66873b0c9`) c'era 1 conflitto. Rimedio: `from backend.app.services.platform.client_address import …`
   > nel posto ordinato, dopo `from backend.app.services.platform import config_audit`, con una riga invariata in
   > mezzo. Lo scrive il test-author.
   > **⚠️ Fuori pista**: sempre in `security.md`, il punto «Callers.» del docs-writer andava in conflitto con
   > `4a93f1f54`, che riscrive l'ultima riga di quel punto. Rimedio: torna il testo di HEAD e cambia solo la prima frase,
   > cioè la regola `rate_limit_address`. Le frasi sui chiamanti di A ed E le aggiornano loro quando passano alla
   > funzione nuova.
   - Dopo il rimedio: `services config-audit` rosso alla raccolta, «ImportError: cannot import name
     'PUBLIC_FORWARDING_SUMMARY' from …client_address» (`files/runs/h36-red-2.sh`). Ruff e black puliti sui due test.
3. ✅ **Cura applicata** (17/10, mattina): `files/h36/apply.py --apply`, poi `cmp` con le copie di prova. Gli 8 file sono
   identici.
   - `network.py`: `_parse_ip` diventa `parse_ip`. Cambiano la definizione, le due chiamate e la docstring del modulo.
   - `client_address.py`:
     - le costanti `UNTRUSTED_PROXY_SUMMARY` e `PUBLIC_FORWARDING_SUMMARY`, e `_FORWARDING_HEADERS`;
     - lo stato `_untrusted_forwarding`;
     - le funzioni `forwarded_by_untrusted_proxy`, `rate_limit_address` (legge prima `client_address`),
       `_followed_by_uvicorn`, `_note_untrusted_forwarding` e `untrusted_forwarding_seen`;
     - la docstring del modulo, e «(a test client)» tolto dalla docstring di `client_address`.
   - `config_audit.py`: `check_client_address` registrato dopo `check_session_cookie`, più una frase nella docstring del
     modulo.
   - `instance/{en,it,fr,es}.json`: `instance.checks.clientAddress.{ok,untrustedProxy,publicForwarding}`, dopo
     `sessionCookie`. I termini seguono i documenti di ogni lingua: «proxy inverse» in FR, «proxy inverso» in ES,
     «reverse proxy» in IT.
   - `.env.example`: quattro righe di commento nella sezione «The Visitor's Address», nessuna variabile nuova.
4. ✅ **Documenti** (docs-writer, solo inglese, nessun comando).
   - `admin/connection_checks.en.md`: un blocco in fondo a `#client-address` su come LibreFolio riconosce un proxy di cui
     non si fida, i limiti per indirizzo, il log, il controllo, il rimedio e gli header da un indirizzo pubblico.
   - `admin/docker_advanced.en.md`: due frasi nel §2.
   - `developer/architecture/security.md`:
     - nella tabella dei controlli, due righe `platform.client_address` e una frase («ok» all'avvio);
     - nella tabella delle funzioni, tre righe;
     - in «Callers.» cambia solo la prima frase (vedi il fuori pista sopra);
     - la sottosezione nuova `#untrusted-proxy`: i cinque passi, il perché del peer locale, Docker Desktop, una sola
       casa per «locale», le note, il controllo, e l'opzione XFF più a destra scartata.
   > **⚠️ Fuori pista** (dal docs-writer, segnalato e non corretto): testi di A ed E diventano falsi per un proxy locale
   > di cui non ci si fida.
   > - A, `4a93f1f54`: il primo paragrafo di `connection_checks` e `configuration.en.md` («50 tentativi… rifiuterebbero
   >   ogni accesso»).
   > - E: `email.en.md:424` («un solo conteggio di 10 richieste») e `:422` («indirizzi esatti»; uvicorn accetta anche
   >   reti); `developer/backend/email.md`, che dice ancora `client_address(request)`.
   > - La riga `i18n_key` di A dice «15 messages»: con le mie tre chiavi diventano 18.
   >
   > Passati al coordinatore.
5. ✅ **Controlli leggeri**, uno alla volta, con il carico sotto 50 (`files/runs/h36-green-1.sh` e `h36-green-2.sh`):

   | Comando | Esito |
   |---------|-------|
   | `services client-address` | 360 passed |
   | `services config-audit` | 101 passed |
   | `services config-env-example` | 38 passed |
   | `services email-checks` | 87 passed |
   | `services config-package` | 853 passed |
   | `dev.py i18n check` | rc 0, 4970 chiavi, strict |
   | `utils gate-i18n-catalog` | 176 passed |
   | `utils gate-i18n-usage` | 195 passed |
   | `dev.py i18n audit` | `clientAddress` non compare tra le chiavi morte o non verificate |
   | sonda in processo su `network.py` | `classify_ip` 12 casi, `client_address` 3, `parse_ip` 3; `_parse_ip` non c'è più |
   | ruff, black (5 file Python) | puliti |
   | `mkdocs build` | rc 0, 0 avvisi |
   | `mkdocs check-links` | 97 link validi |
   | `git diff --check` | pulito |

   - `git merge-file` contro `4a93f1f54` (il ramo di A, che contiene `66873b0c9`), dalla base comune `c9cb27e4c`: **0
     conflitti** su tutti i 10 file condivisi o vicini.
   - Non eseguito: `api system` (contiene i test di `classify_ip`; è un passo pesante con il server, la sonda in
     processo lo sostituisce); la prova combinata con A8a, che spetta al cancello del coordinatore.
6. ✅ **Prova sulla revisione combinata** (17/10, 06:11–06:16), chiesta dal coordinatore prima dell'ingresso. Base
   aggiornata da lui: merge `3c1444e0c` = H-36 (`36cc0119d`, `b3e9f9c8a`, `b36e22454`) + dev `abf8391fb`, pulita.
   - `files/runs/h36-combined.sh`, un comando alla volta: `services client-address` 360, `config-audit` 101,
     `config-env-example` 38, `email-checks` 87, `config-package` 856 (+3 da dev), `i18n check` strict (4973 chiavi),
     `mkdocs build` rigoroso con 0 avvisi, `check-links` 97.
   - Pulita prima e dopo, porta 6181 libera.
   - Il merge di `security.md` è controllato: il pezzo di dev (riga 1388, backup) è lontano dai miei, e non ci sono
     marcatori.
   - La riga della CHANGELOG la scrive il coordinatore all'ingresso di A8a + E-13, quando il salto per indirizzo ha
     effetto.

### Lotto «H-37: `profile_default` fallisce chiuso per una variabile che il profilo non elenca» (R13-SEC7 di E, 2026-10-17, mattina) — in corso

> Chiesto dal coordinatore, dopo H-36: «`profile_default` (`config/__init__.py:584`): una voce `managed` mancante dà 0,
> cioè nessun limite; deve fallire chiuso (rifiutare l'avvio, o un default sicuro dichiarato per campo). Prima i rossi;
> E rivede.» È la nota 5 di R13-SEC7 nel piano di E (`08_email`, «Esito di R13-SEC7»).

**Analisi** (sola lettura, HEAD `3c1444e0c`):

1. `profile_default(name, fallback)` dà il `fallback` quando il profilo attivo non elenca `name`, e questo vale in
   qualunque profilo. Per l'unico lettore, `backup_max_upload_mb()` di B (`config/backup.py:78`, fallback `0`), togliere
   la voce `managed` vuol dire «nessun limite» in managed: un fail-open.
2. **Nessun altro lettore.** Ho cercato `profile_default(` negli alberi di tutti i 31 rami locali: c'è solo quello di B,
   ed è elencato (500). La cura non cambia il comportamento di oggi.
3. **Il test di B fissa apposta il fail-open**: `test_backup_restore.py:1400`,
   `test_the_managed_limit_is_the_entry_of_the_profile_table_read_at_each_call`, controlla che senza la voce il limite
   sia 0. Va riscritto: è un file di B (`api backup-restore`, passo pesante).
4. `test_profile_defaults.py` (mio) fissa la stessa regola: il paragrafo (f) («e in managed per un nome che non
   elenca») e `test_managed_gives_back_the_fallback_itself_for_a_variable_it_does_not_list`.
5. **I documenti**: `developer/architecture/settings.md` (il paragrafo di `ENVIRONMENT_PROFILE_DEFAULTS`, la guardia e
   il «come aggiungere una variabile») e `security.md:1461-1463` (quando il limite «non si può leggere»). La pagina admin
   `hosting_providers#managed-profile` non dice nulla sulle variabili non elencate.
6. Per H-27 `settings.md` dice già: «il controllo gira alla chiamata del lettore, mai all'avvio: solo il lettore sa che
   tipo si aspetta; la tabella è codice, protetta prima del rilascio dai test». Vale lo stesso per una voce mancante:
   solo il lettore sa quale variabile legge.

**Progetto** (la scelta fra le due forme proposte):

- **Fallire chiuso alla chiamata.** Sotto ogni profilo tranne `selfhosted`, un nome che il profilo non elenca solleva
  `ProfileDefaultError`. Il messaggio nomina la variabile, il profilo e `ENVIRONMENT_PROFILE_DEFAULTS`, e dice che ogni
  profilo tranne `selfhosted` deve dare un valore a ogni variabile letta da `profile_default`.
  - Il lettore si ferma: le rotte di B prendono già `ProfileDefaultError` (B-21), quindi l'upload dà 503
    `backup_upload_unavailable` e lo stato `upload_limit_mb: null`, con un errore nel log che nomina la variabile.
  - `selfhosted` resta com'è: il fallback, senza controlli.
- **La stessa regola sul sorgente**, nella guardia (h): ogni chiamata `profile_default(<nome>, …)` di un modulo di
  sezione deve avere il suo nome elencato da ogni profilo tranne `selfhosted`. Un autotest toglie la voce `managed` e
  verifica che la guardia la segnali.
- **Non rifiuto l'avvio.**
  - Per saperlo all'avvio servirebbe un terzo elenco, le variabili lette, oltre alla tabella e ai lettori. Oggi lo
    tiene la guardia (h), sul sorgente.
  - E il raggio d'azione: una voce mancante fermerebbe ogni istanza managed all'aggiornamento, mentre così si chiude
    solo la funzione che legge quel valore.
  - È la stessa scelta che H-27 ha documentato per il tipo.
- **`ProfileDefaultError` resta un `TypeError`** (H-27; B la prende per nome). Cambia la docstring: «manca, oppure è di
  un altro tipo».
- **Fuori perimetro**: `PROFILE_DEFAULTS` (i campi di `Settings`) ha la stessa forma, e senza la voce
  `LIBREFOLIO_FRAME_PROTECTION` un'istanza managed tornerebbe al default del codice (spento). Il test (a) lo fissa
  intero contro `MANAGED_DEFAULTS`. Lo segnalo a E e non propongo nulla.

**Rossi** (test-author): `test_profile_defaults.py`, paragrafi (f), (g) e (h), più il test del lettore vero di B con la
voce tolta. Con l'OK del coordinatore, anche la riga di `test_backup_restore.py:1400` e il caso «missing» nei test
503/null di B-21.

**Selettori**: `services profile-defaults`, `services config-package`, `services config-env-example`; `api
backup-restore` (pesante, serve uno slot); ruff e black; `mkdocs build` e `check-links`.

> **Approvazione** (coordinatore, 17/10 mattina): la scelta va bene, cioè fallire chiuso alla chiamata
> (`ProfileDefaultError` fuori da `selfhosted`), la guardia (h) sul sorgente con il suo autotest e nessun rifiuto
> all'avvio, coerente con H-27. In più:
> - OK di scrittura su `test_api/test_backup_restore.py` di B: si riscrive il test del fail-open e si aggiunge il caso
>   «missing» in `WRONG_TABLE_LIMITS`, con `wrong_table_entry` che impara `delitem`. Lo fa il test-author; B rivede al
>   checkpoint, perché è su B-16, solo frontend.
> - Uno slot per i 3 test di `api backup-restore` per nome: lo chiedo quando la cura è pronta.
>
> **Nota per E** (chiesta dal coordinatore): `PROFILE_DEFAULTS`, i campi di `Settings`, ha la stessa forma. Senza la voce
> managed di `LIBREFOLIO_FRAME_PROTECTION` (o di `LIBREFOLIO_CSP_REPORT_ONLY`, o dei due tempi di riposo), un'istanza
> managed torna in silenzio al default del codice: la protezione dei frame spenta. Oggi lo ferma solo il test (a)
> (`MANAGED_DEFAULTS`, uguaglianza intera), prima del rilascio. Una chiusura a runtime richiederebbe un elenco
> dichiarato dei campi per profilo: non è in H-37, lo decide E.

1. ✅ **Cura in prova** (17/10, mattina): `files/h37/apply.py` scrive `dry/config_init.py`.
   - Cambiano tre pezzi di `config/__init__.py`: il commento sopra `ENVIRONMENT_PROFILE_DEFAULTS`, la docstring di
     `ProfileDefaultError` e `profile_default()`.
   - In `profile_default()`, per un nome non elencato, `selfhosted` dà ancora il fallback; ogni altro profilo solleva
     `ProfileDefaultError`. Il messaggio nomina la variabile, il profilo e `ENVIRONMENT_PROFILE_DEFAULTS`.
   - Il ramo di un nome elencato non cambia: il controllo di tipo di H-27.
   - Ruff e black sono puliti sulla copia di prova, come su HEAD.
2. ✅ **Rossi** (test-author, che non ha lanciato nulla; 17/10, mattina).
   - `test_profile_defaults.py`, 25 casi nuovi e 1 tolto:
     - `test_managed_refuses_a_variable_it_does_not_list`, al posto del vecchio test del fallback in managed; 6
       fallback (`object`, `0`, `0.0`, `""`, `False`, `None`);
     - la variante con il profilo scritto in altro modo (2 casi);
     - il lettore vero di B con la voce tolta (rosso) e lo stesso in self-hosted (verde, 2 casi);
     - la guardia (h) nella direzione nuova, con il suo autotest;
     - `fallback_like`, che ora regge una voce uguale al valore vuoto del suo tipo (dalla review dei documenti: H-37
       rende obbligatoria anche una voce uguale al fallback), con il suo test (8 casi);
     - un caso (g) con la voce uguale al default del lettore (4 casi).
   - Docstring: (f), (g), (h) e «How».
   - `test_backup_restore.py` di B, solo il blocco (e) e il suo paragrafo, con l'OK del coordinatore:
     - il test della guardia B4: con la voce tolta deve dare `ProfileDefaultError`, mai 0;
     - `MISSING` (con `repr` «no entry») in `WRONG_TABLE_LIMITS`;
     - `wrong_table_entry` impara `delitem`.
   - Comando: `files/runs/h37-red-1.sh` (`services profile-defaults`). Esito: **9 failed, 103 passed**, esattamente i 9
     previsti: `test_managed_refuses_…[×6]`, `…another_case_refuses_…[×2]` e
     `test_a_missing_managed_upload_limit_stops_its_reader`. In ognuno il fallback, o lo 0, torna indietro.
   - Ruff pulito. Black voleva andare a capo in tre `pytest.fail` lunghi: applicato al mio file di test, solo
     formattazione.
   - I rossi di B (3 test, 11 casi) aspettano lo slot `api`.
   > **⚠️ Fuori pista** (dal test-author, non corretto): la `desc` del catalogo di `services profile-defaults`
   > (`_backend_services.py`) non nomina né H-27 né H-37. Le etichette «B-21, RED until the routes catch it» nel file di
   > B sono vecchie: lo dico a B.
3. ✅ **Slot 1** (concesso dal coordinatore, 06:38–06:43, corsia 6181), `files/runs/h37-slot.sh`:
   - **Rosso**, prima della cura: `api backup-restore` sui 3 test per nome, **3 failed / 8 passed**.
     - La guardia B4: «backup_max_upload_mb() returns 0, where H's profile_default raises ProfileDefaultError».
     - I due `[missing]` di B-21: «precondition: H's table giving no entry … not 0».
   - **Cura applicata**: `files/h37/apply.py --apply`, identica alla copia di prova (`cmp`).
   - **Verde**: gli stessi 3 test, **11 passed**. Porta libera alla fine.
4. ✅ **Documenti** (docs-writer, solo inglese, pagine per sviluppatori senza traduzioni):
   - `settings.md`, il punto di `ENVIRONMENT_PROFILE_DEFAULTS`: la regola nuova, il perché (anche il raggio d'azione), la
     guardia nelle due direzioni con i due autotest, e «la voce managed è obbligatoria anche al valore del fallback»;
   - `security.md:1461-1463`: «nessun valore (ogni profilo tranne `selfhosted`, H-37) o un valore del tipo sbagliato».
   > **⚠️ Fuori pista** (dal docs-writer): `fallback_like()` non reggeva una voce uguale al valore vuoto del suo tipo,
   > che H-37 rende legittima. Lo ha corretto il test-author, con un test dell'aiuto.
5. ✅ **La riga `desc`** di `services profile-defaults` in `_backend_services.py`, con l'OK del coordinatore, solo
   aggiunta: H-27 e H-37 accodati. `git merge-file` contro dev `0dc58c70b`, che ha già le righe di Z: 0 conflitti.
   Il modulo del runner si carica e la `desc` contiene i due lotti. `services profile-defaults --list` elenca i test
   nuovi.
6. ✅ **Controlli leggeri** dopo la cura (`files/runs/h37-green-light.sh`):

   | Comando | Esito |
   |---------|-------|
   | `services profile-defaults` | 112 passed |
   | `services config-package` | 856 passed |
   | `services config-misc` | 12 passed |
   | `services config-env-example` | 38 passed |
   | ruff, black (4 file) | puliti |
   | `mkdocs build` | rc 0, 0 avvisi |
   | `check-links` | 97 |
   | `git diff --check` | pulito |

   - `git merge-file` di tutti gli 8 file cambiati contro dev `0dc58c70b` (base comune `d107b6f26`): 0 conflitti.
   - Non eseguito: `api backup-restore` intero (bastano i 3 test per nome, come deciso dal coordinatore) e
     `all-backend`, che spettano al cancello.
   > **Note per B**, alla review del suo file:
   > - le etichette «B-21, RED until the routes catch it» nel blocco (e) sono vecchie;
   > - la docstring di `backup_max_upload_mb()` (`config/backup.py:73-74`), «else `0`, the self-hosted default», ora vale
   >   solo per `selfhosted`. Non l'ho toccata: è codice di produzione di B, e non ho l'OK.
7. ✅ **Ingresso** (17/10, 06:47): `1ddd820c7` (fix, documenti, diario) è entrato in dev `b37e926af`, senza riga di
   CHANGELOG. Il mio HEAD è avanzato a `b37e926af`, pulito.
   - E ha rivisto H-37: «sound», nessuna correzione. Ha deciso su `PROFILE_DEFAULTS`: nessuna chiusura a runtime, ma un
     controllo di visibilità, che diventa **H-39** (dopo Z-24).
   - B riceve le mie due note.

### Lotto «Z-24: `.scheduler.lock` fra i percorsi protetti della cartella dati di test» (2026-10-17, mattina) — in corso

> Chiesto dal coordinatore mentre H-35 aspetta A8a. È una voce di Z (Z-11, dal suo test-author), «minimo,
> facoltativo», sul mio file `config/__init__.py`. Prima i rossi.

**Analisi** (sola lettura, HEAD `b37e926af`):

1. `validate_test_data_dir()` (`config/__init__.py:450`) ha in `managed_paths` `scheduler_state.json`, ma non il
   `.scheduler.lock` che Z-11 ha aggiunto (`services/platform/scheduler/run_lock.py`, `LOCK_FILE_NAME`, nella cartella
   dati accanto allo stato).
   - Un symlink al suo posto oggi passa la guardia; lo ferma solo l'`O_NOFOLLOW` di Z quando lo apre.
   - Un hardlink al lock di produzione farebbe aspettare a turno i giri dei due server.
2. **L'inventario dei percorsi fissi sotto la radice dati.** Sono tutti in `managed_paths` tranne il lock: `sqlite/`,
   `custom-uploads/`, `broker_reports/`, `logs/` (anche `scheduler_jobs.jsonl`), `scheduler_state.json`,
   `secrets/instance.key`, `scenario_catalog/`, `backups/` e `.restore/` (B).
3. **Considerati e non aggiunti**: `sqlite/app.db-wal` e `-shm` (WAL attivo, `db/session.py`), e
   `sqlite/app.db.post-migration.lock`. Un alias di uno di questi da solo non è un errore realistico: ogni modo di
   condividere il DB fa alias anche di `app.db`, che è già rifiutato per primo. Se il coordinatore li vuole, sono due
   righe.
4. **Un buco nei test**: il ramo «Test data path aliases production data» (hardlink, `samefile`) non ha nessun test. Il
   test dei symlink (`test_runtime_isolation.py`, `TestDataDirResolution`) copre solo `sqlite`, `sqlite/app.db`,
   `secrets`, `secrets/instance.key`, `backups` e `.restore`.
5. **Documenti**: `database/index.md#data-directory` elenca già `.scheduler.lock`, e descrive la guardia in modo
   generico, come `test-walkthrough` e `security.md:502`. Non serve cambiarli.

**Progetto**:
- `Path(".scheduler.lock")` in `managed_paths`, subito dopo `scheduler_state.json`.
- Rossi (test-author, `test_runtime_isolation.py`):
  - il parametro `.scheduler.lock`, più `scheduler_state.json`, nel test dei symlink;
  - un test nuovo dell'hardlink, con «aliases production data», su `sqlite/app.db`, `secrets/instance.key`,
    `scheduler_state.json` (verdi: coprono il ramo scoperto) e `.scheduler.lock` (rosso);
  - una barriera che il nome sia il `LOCK_FILE_NAME` di Z.
- Backlog: Z-24 è nella sezione di Z, e non la tocco. Lo chiudo nel mio piano e lo segnalo al coordinatore.

**Selettori**: `utils runtime-isolation` (puro), e `services config-package` perché il file è `config/__init__.py`.
1. ✅ **Rossi** (test-author, che non ha lanciato nulla; 17/10, mattina), in `test_runtime_isolation.py`,
   `TestDataDirResolution`:
   - `scheduler_state.json` e `.scheduler.lock` aggiunti al test dei symlink;
   - un test nuovo dell'hardlink («aliases production data»), su `sqlite/app.db`, `secrets/instance.key`,
     `scheduler_state.json` e `.scheduler.lock`, con skip se il filesystem rifiuta gli hard link;
   - la barriera `test_the_scheduler_lock_named_here_is_the_one_the_scheduler_takes`, sulla costante
     `SCHEDULER_LOCK` della classe.
   - Comando: `files/runs/z24-red.sh` (`utils runtime-isolation`). Esito: **2 failed, 296 passed**, i due
     `[.scheduler.lock]`, tutti e due con «DID NOT RAISE ValueError».
   > **⚠️ Fuori pista**: la barriera importava `run_lock`, e l'import si porta dietro l'`__init__` del pacchetto
   > scheduler: 1246 moduli in ~1,9 s (misurato con `-X importtime`), modelli del DB compresi, dentro un'unità pura.
   > Ora legge `LOCK_FILE_NAME` dal sorgente con `ast` (lo schema di `_assigned_value` in `test_test_runner_cli.py`),
   > con `import ast` in cima al file.
2. ✅ **Cura** (`files/z24/apply.py --apply`, identica alla copia di prova): `Path(".scheduler.lock")` in
   `managed_paths` dopo `scheduler_state.json`, con un commento (Z-11, `run_lock.LOCK_FILE_NAME`).
3. ✅ **Controlli leggeri** (`files/runs/z24-green.sh`): `utils runtime-isolation` 298 passed, `services
   config-package` 857, `utils dev-cli-db-path` 15. Ruff e black puliti, `git diff --check` pulito.
   - `git merge-file` contro dev `952c68cd5` (base comune `b37e926af`): 0 conflitti. Dev cambia
     `backend.instructions.md` in un'altra tabella, e il backlog altrove.
   - La voce Z-24 sta nella sezione di Z: la chiude il coordinatore.

> **H-39, la parte già fatta, nello stesso checkpoint**: approvato dal coordinatore (06:52). In managed, la CSP
> report-only spenta è un info e la protezione dei frame spenta un warning; il self-hosted è sempre ok.
> - La regola di review è una riga nella voce «Config & Data Paths» di `.github/instructions/backend.instructions.md`:
>   «un campo `Settings` di sicurezza nuovo dichiara il suo valore `managed` in `PROFILE_DEFAULTS` nello stesso lotto,
>   o perché `managed` tiene il default del codice (H-39)».
> - La riga accanto a C-99 è del coordinatore.
> - I due controlli e le loro chiavi i18n aspettano B-9, che scrive in `config_audit.py`, `test_config_audit.py`,
>   `security.md` e `settings.md`.
>   - La cura in prova è pronta: `files/h39/apply.py`, che scrive le copie in `dry/`. Ruff e black puliti, 0 conflitti
>     con A8a.
>   - Le chiavi restano fuori dal worktree: senza il codice sarebbero morte, e un `instance/*.json` sporco potrebbe
>     fermare l'avanzamento del ramo se B-9 lo tocca.
4. ✅ **Ingresso** (17/10, 07:07): Z-24 e la regola di H-39 sono entrati in dev `36a487e84`. Z-24 è chiusa nel backlog
   dal coordinatore (`b58f22357`), e il mio HEAD è avanzato lì, pulito.
   - Nota di proprietà fino all'ingresso di B-9: B scrive in `config_audit.py`, `test_config_audit.py`, `security.md` e
     `settings.md` (l. 68-70). Li rivedo al suo checkpoint, e non li tocco fino ad allora.
   - Il coordinatore ha dato l'ordine: H-34, poi H-19, poi H-3 (solo l'analisi, se serve una decisione del developer).

### Lotto «H-34: `Infinity` e `NaN` dentro il JSON libero di una richiesta» (2026-10-17, mattina) — in corso

> Residuo di H-32, dal backlog (dal test-author e dal docs-writer di H-32). Ora è assegnato ad H dal coordinatore.

**Analisi** (sola lettura, in processo, HEAD `b58f22357`; `files/h34/inventory.py` e `files/h34/probe.py`):

1. **Inventario delle posizioni libere** (`Any`, `object`, `JsonValue`) che una richiesta dell'app vera raggiunge. Ho
   usato il percorso di H-32 (`_Walk` di `test_request_float_inputs.py`), con un'aggiunta che le annota. Sono **5**,
   nessun problema di percorso:

   | Posizione | Tipo | Rotte |
   |-----------|------|-------|
   | `FAProviderAssignmentItem.provider_params{*}` (X) | `Any` | `POST /assets/provider` |
   | `FAProviderProbeRequest.provider_params{*}` (X) | `Any` | `POST /assets/provider/probe` |
   | `RiskAnalyticRequest.parameters{*}` (J) | `JsonValue` | `POST /risk/query` |
   | `SignalRequest.params{*}` | `JsonValue` | `POST /assets/prices/query`, `/fx/currencies/convert`, `/signals/preview` |
   | `ToolComputeItem.parameters` | `JsonValue` | `POST /tools/compute` |

2. **La prova** (validazione in modalità Python, come fa FastAPI dopo `json.loads`, che trasforma `NaN`, `Infinity` e
   `1e400` in float). Il valore usato è `{"top": inf, "deep": [1, {"x": nan}], "neg": -inf}`:
   - `JsonValue` rispetta l'`allow_inf_nan=False` del modello: `ToolComputeItem` (`ToolTransportModel`, `strict=True,
     allow_inf_nan=False`) dà 422, e in più `services/tools/wire.py` rifiuta le costanti già nel parsing (il campo era
     segnato «da verificare»: è protetto);
   - `SignalRequest.params` ha già `ensure_json_safe`;
   - `RiskAnalyticRequest.parameters`: **accettato**;
   - `FAProviderAssignmentItem`: **accettato** con `borsa_italiana`, `justetf`, `mockprov` e `yfinance`, il cui
     `validate_params` accetta le chiavi in più; `css_scraper` e `scheduled_investment` rifiutano per altri motivi.
     I valori finiscono nel DB come `Infinity` (il JSON di SQLAlchemy usa `json.dumps`), e una lettura con
     `response_model` li ridà come `null` (H-32).
   - `FAProviderProbeRequest`: stessa base, `FAProviderConfigBase`, quindi stesso esito. Nella mia sonda l'operazione
     era sbagliata, e il 422 veniva da quella.
3. Nessun codice interno costruisce questi modelli con valori Python non JSON: l'unico `RiskAnalyticRequest(...)`
   interno (`ai_export/components/drawdown_context.py:348`) non passa `parameters`.
4. Nessun ramo locale cambia `schemas/provider.py` o `schemas/risk.py` rispetto alla sua base con dev.

**Progetto**:
- `FAProviderConfigBase` (`schemas/provider.py`, X) e `RiskAnalyticRequest` (`schemas/risk.py`, J) ricevono un
  `field_validator(mode="before")` che chiama `ensure_json_safe(value, "<campo>")`, come `SignalRequest.params`.
  Risposta 422; il gestore globale di A7b-2 non ripete il valore. Va in tutti e due il proprietario: OK di scrittura
  dal coordinatore, poi review di X e J.
- La guardia nel mio `test_request_float_inputs.py` (lavoro del test-author):
  - la passata trova esattamente le 5 posizioni libere, e una nuova fallisce («aggiungila con la sua sonda»);
  - per ognuna, un corpo minimo valido con un valore non finito annidato dà `ValidationError`, mentre lo stesso corpo
    finito passa (barriera).
- Documenti: il paragrafo va in `security.md#request-numbers`, che è chiuso fino all'ingresso di B-9. Proposta:
  arriva con i documenti di H-39.

> **Approvazione** (coordinatore, 07:2x): OK di scrittura su `schemas/provider.py` (rivede X) e su `schemas/risk.py`
> (rivede J). Il paragrafo di `security.md#request-numbers` arriva con i documenti di H-39, dopo B-9. Questo checkpoint
> è solo codice e test. Per la CHANGELOG il coordinatore vuole una voce 🔒 breve: un `Infinity` o un `NaN` annidato
> nei parametri di un provider veniva salvato e riletto come `null`.

1. ✅ **Rossi** (test-author, che non ha lanciato nulla; 17/10, mattina), solo in `test_request_float_inputs.py`:
   - il paragrafo (g) «H-34: free-form JSON», e la passata ora annota le posizioni libere (`free_form` in
     `RequestFloats`);
   - `KNOWN_FREE_FORM` con le 5 posizioni e le loro sonde. Il provider scelto è `mockprov`, il cui `validate_params`
     non fa nulla per costruzione, con una barriera che sia registrato;
   - 6 posizionamenti: in cima `inf`, `-inf` e `nan`, `inf` in una lista, `nan` in un dizionario annidato, `-inf` in
     un dizionario dentro una lista;
   - 62 casi nuovi: la passata trova esattamente le 5 posizioni; ognuna rifiuta (30); lo stesso corpo finito passa
     (30, la barriera); un autotest della passata su un'app sua.
   - Comando: `files/runs/h34-red.sh`. Esito: **18 failed, 77 passed**, cioè le due posizioni dei provider e quella
     del rischio, ognuna per 6 posizionamenti. Ruff e black puliti.
   > **⚠️ Fuori pista** (dal test-author, poi verificato): `TXMixedBatch` (W) ha i corpi in `List[dict]`, e la
   > passata non apre un contenitore nudo. Le righe vengono validate dopo, una per una, in `TXCreateItem`,
   > `TXUpdateItem`, `TXSplitBatchItem` e `TXPromoteBatchItem` (`files/h34/tx_probe.py`):
   > - nessuna foglia float, e gli importi sono `SafeDecimal`, che rifiuta anche `"Infinity"` scritto come testo;
   > - resta una posizione libera, `TXPromoteBatchItem.resolved_fields{*}`, applicata così com'è:
   >   - `description` va nella colonna `Text` senza controllo di tipo né di lunghezza, e un numero renderebbe ogni
   >     lettura un 500;
   >   - `cost_basis_override` e `date` hanno errori che probabilmente escono come 500.
   >
   > È più largo dei numeri non finiti ed è di W: registrato come **H-41**, da passare a W. Non lo tocco.
2. ✅ **Cura** (`files/h34/apply.py --apply`, identica alla copia di prova): un `field_validator(mode="before")`
   chiama `ensure_json_safe`, in `FAProviderConfigBase.provider_params` e in `RiskAnalyticRequest.parameters`.
3. ✅ **Controlli leggeri** (`files/runs/h34-green.sh`):

   | Comando | Esito |
   |---------|-------|
   | `services request-float-inputs` | 95 passed |
   | `schemas assets` | 70 passed |
   | `schemas risk` | 88 passed |
   | `services risk-asset-set` | 55 passed |
   | `services asset-source-refresh` | 18 passed |
   | `services plugin-settings-runtime` | 120 passed |
   | `utils provider-core-cache` | 46 passed |
   | ruff, black (3 file) | puliti |
   | `git diff --check` | pulito |

   - **OpenAPI invariato.** Ho confrontato, chiave per chiave, il documento dell'app su HEAD (copiata da
     `git archive` nella cartella di sessione) con quello attuale. L'unica differenza è `/info/version` (il
     `git describe` del worktree).
   - Non eseguito: le rotte vere (`api assets…`, `api risk…`), passi pesanti che spettano al cancello.
   - Documenti: il paragrafo di `security.md#request-numbers` arriva con H-39 (deciso dal coordinatore).
   - Backlog: la nota della cura in H-34; nuove **H-40** (IPv6 su Docker Engine, la frase di E) e **H-41**
     (`resolved_fields`, W).
4. ✅ **Ingresso** (17/10, 07:43): H-34 è entrato in dev `75bfac237`, con la riga 🔒 della CHANGELOG `27f948ccd`. Il mio
   HEAD è avanzato a `27f948ccd`, che contiene già B-9 e A8a. X e J rivedono a posteriori; H-41 va a W, dentro SEC7-3.

### Review di B-9 sulle righe nei miei file (2026-10-17, 07:45) — ✅ OK, due note

- Ho letto, solo in lettura, `git diff 45f9c5406 997dc7ecf` di `config_audit.py`, `test_config_audit.py`,
  `security.md` e `settings.md`, più il modulo di B `instance_backup/checks.py`.
- **OK**:
  - in `config_audit.py`, `*BACKUP_CONFIG_CHECKS` sta dopo `check_log_level` e prima di A, con la docstring delle chiavi
    A/B/E. Nessun ciclo: `checks.py` importa `ConfigCheck` solo quando un controllo gira;
  - il test della tupla intera separa `backup` da `platform`, nell'ordine platform → B → A → E;
  - il blocco «Workstream B» di `_configure`: il `_FILE` è coperto dal ciclo che c'era già;
  - in `security.md`, le due righe `backup.*` fra `platform.log_level` e `accounts.login_limit`, e la frase
    sull'ordine.
- **Note**:
  1. la docstring di `checks.py` dice «right before E's email checks», ma in mezzo ci sono quelli di A (è di B);
  2. l'import con i sostituti di B-9 in `test_config_audit.py` ora è impalcatura vecchia: la tolgo in H-35.

### Lotto «H-39: un profilo managed senza protezione dai frame si vede» (decisione di E, 2026-10-17, mattina) — in corso

> Dalla review di H-37 fatta da E: per `PROFILE_DEFAULTS` nessuna chiusura a runtime, ma un controllo che si veda.
> Approvato dal coordinatore (06:52):
> - nel profilo managed, `LIBREFOLIO_FRAME_PROTECTION` spenta è un **warning** e `LIBREFOLIO_CSP_REPORT_ONLY` spenta è
>   un **info**;
> - nel self-hosted sono sempre ok;
> - la regola di review (in `backend.instructions.md`, già entrata) e la riga accanto a C-99, del coordinatore.
>
> Rimandato fino a B-9 (07:43, «go»): i controlli, i test e le chiavi i18n, e un solo giro di documenti con il paragrafo
> di H-34 e la frase di H-40.

**Progetto** (la cura in prova `files/h39/apply.py` si applica pulita sulla base nuova `27f948ccd`):
- `config_audit.py`:
  - `check_frame_protection()` (`platform.frame_protection`) e `check_csp_report_only()` (`platform.csp_report_only`),
    in `CONFIG_CHECKS` dopo `check_client_address` e prima di `check_log_level`;
  - leggono `get_settings()`; l'aspettativa di managed sta nel codice (`MANAGED_PROFILE`), non nella tabella, perché
    una voce persa cambierebbe l'aspettativa insieme al valore;
  - stati: acceso → ok `…on`; spento e self-hosted → ok `…offSelfHosted`; spento e managed → warning
    `frameProtection.offManaged`, oppure info `cspReportOnly.offManaged`, con il suo summary.
- i18n: 6 chiavi `instance.checks.frameProtection.*` e `.cspReportOnly.*`, in 4 lingue. I messaggi di
  `instance.checks` passano da 18 a 24.
- Test (test-author, `test_config_audit.py`): ogni stato, i summary, l'avvio in managed con la protezione spenta (un
  warning e un info nel log), `CHECK_IDS` e l'ordine. In `_configure`, tolte le due variabili.
- Documenti (docs-writer, solo inglese):
  - `security.md`: le righe della tabella d'ordine, «18» che diventa «24», il paragrafo di H-34 in `#request-numbers`;
  - `admin/configuration.en.md#startup-checks`: due righe;
  - `admin/hosting_providers.en.md#managed-profile`: una frase;
  - `settings.md`: una frase, per `PROFILE_DEFAULTS`;
  - `admin/connection_checks.en.md#limits`: la frase di H-40 (IPv6 attraverso `docker-proxy`), da verificare su un host
    Linux come H-38.

1. ✅ **Rossi** (test-author, che non ha lanciato nulla; 17/10, mattina), in `test_config_audit.py`:
   - il paragrafo (g) e la riga d'ordine di (c);
   - `CHECK_IDS` con le due voci dopo `check_client_address`;
   - in `_configure`, le due variabili tolte;
   - 6 test e 53 casi: gli stati, con 5 modi di scrivere il profilo e 6 valori; una voce tolta da
     `PROFILE_DEFAULTS["managed"]` deve risultare ancora `offManaged`; «non cambia nulla», compreso `PROFILE_DEFAULTS`;
     l'ordine dopo il controllo degli indirizzi; all'avvio, in managed, il warning e poi l'info, e la partenza va
     avanti; in self-hosted, niente nel log;
   - un test di H-36 adattato: prima voleva `check_log_level` subito dopo il controllo degli indirizzi.
   - Comando: `files/runs/h39-red.sh`. Esito: **rosso alla raccolta**, «ImportError: cannot import name
     'check_csp_report_only'». Ruff e black puliti sul file di test.
2. ✅ **Cura** (`files/h39/apply.py --apply`, identica alle copie di prova): i due controlli e `MANAGED_PROFILE` in
   `config_audit.py`, più 6 chiavi in `instance/{en,it,fr,es}.json` dopo `clientAddress`.
3. ✅ **Documenti** (docs-writer, solo inglese, due giri):
   - `security.md`:
     - la tabella d'ordine e «24 messages»;
     - un paragrafo con gli stati `ok` e il perché dell'aspettativa scritta nel controllo;
     - la riga «Tests:» con l'ordine platform → B → A → E (ci mancava B);
     - una frase in `#managed-headers`;
     - **il paragrafo di H-34** in `#request-numbers`, con i contenitori nudi non coperti, e la clausola IPv6 in «Why
       only a local peer»;
   - `settings.md`: la frase su `PROFILE_DEFAULTS` e la regola di review;
   - `configuration.en.md`, «Startup Checks»: due righe;
   - `hosting_providers.en.md`: una frase;
   - `connection_checks.en.md`, «Limits»: la frase di **H-40** (IPv4 sì, IPv6 attraverso `docker-proxy` dal gateway),
     scritta come cautela, più una clausola IPv6 nel punto «To fix it» di «The Visitor's Address».
   - In più, il test-author di H-34 ha aggiornato le docstring vecchie di `test_request_float_inputs.py`: (d), (e),
     (g), `FixedValueBody`, `PlainValueBody` e «How to fix a red». Sono solo testo.
   > **⚠️ Fuori pista**: la build rigorosa falliva su un link. `hosting_providers.en.md` non ha traduzioni, quindi il
   > sito IT usa la pagina inglese, e il suo link `configuration.md#startup-checks` cercava l'ancora in
   > `configuration.it.md`, che oggi ha solo `#session-cookie-secure`. Ora il link punta alla pagina,
   > «Startup Checks» in [Configuration].
4. ✅ **Controlli leggeri** (`files/runs/h39-green.sh`, `h39-final.sh`, `h39-docs2.sh`):

   | Comando | Esito |
   |---------|-------|
   | `services config-audit` | 155 passed |
   | `services email-checks` | 87 passed |
   | `services backup-checks` | 57 passed |
   | `services accounts-checks` | 76 passed |
   | `services security-headers` | 15 passed |
   | `services profile-defaults` | 112 passed |
   | `services config-package` | 862 passed |
   | `services request-float-inputs` | 95 passed |
   | `i18n check` | strict, 4995 chiavi |
   | `utils gate-i18n-catalog` | 176 passed |
   | `utils gate-i18n-usage` | 195 passed |
   | `i18n audit` | le 6 chiavi nuove non compaiono: sono usate |
   | ruff, black (3 file) | puliti |
   | `mkdocs build` (rigoroso) | 0 avvisi, dopo il link |
   | `check-links` | 97 |
   | `git diff --check` | pulito |

   - `git merge-file` dei 14 file contro dev `f4dab3db7`: 0 conflitti.
   - Non eseguito: `api security-checks` di A (passo pesante, va nel cancello). L'elenco della scheda Sicurezza avrà due
     controlli in più.
   - Backlog:
     - H-39 chiusa, con il resto: un controllo letto a richiesta dopo una modifica di `.env` senza riavvio può non
       coincidere con gli header;
     - H-40 scritta e da verificare su Linux;
     - H-5, il debito di traduzione di `configuration` e `connection_checks`.
5. ✅ **Ingresso** (comunicato alle 09:08): H-39 è entrato in dev `0403b5eb7`, con la riga 🔒 della CHANGELOG
   `7f8e69be6`. Il mio HEAD è avanzato a `7f8e69be6`, pulito.
   - E ha chiuso H-39 senza reperti.
   - Ha suggerito, LOW, **H-42** (dopo H-35): imporre già, nello stesso header di `frame-ancestors`, `object-src
     'none'; base-uri 'self'; form-action 'self'`, da verificare con gli E2E che aprono i documenti e il visore PDF.
   > **Nota su H-40**: la frase su IPv6 non è verificata su un host Linux (il demone Docker è spento). Viene dalla
   > documentazione di Docker sulla pubblicazione delle porte, come ha riferito il docs-writer. La prova su Linux resta
   > con H-38.

### Lotto «H-35: dopo A8a e B-9, la docstring dell'avvio e la pulizia di `test_config_audit.py`» (2026-10-17, mattina) — in corso

> Dalla review di A8a (coordinatore, notte), con B-9 aggiunto dalla mia review (07:45) e la pulizia di `_configure` di
> H-36 (punto 10 del test-author). Base `7f8e69be6`: A8a e B-9 sono dentro.

**Analisi** (sola lettura):

1. `log_configuration_audit()` (`config_audit.py`) chiama `admin_bootstrap_config()` (F02) e `login_limit_enabled()`
   (F15), che possono sollevare:
   - `AdminBootstrapConfigError`, un `ValueError` che nomina la variabile;
   - `ValueError`, per un `LIBREFOLIO_LOGIN_LIMIT` diverso da `on` e da `off`.

   La docstring non lo dice. La docstring del modulo dice ancora che l'avvio si ferma solo su «un segreto configurato»,
   e che la scheda «Security» valuterà i controlli. Ma `GET /api/v1/security/checks` (A8a, `api/v1/security.py`) li
   valuta già.
2. `test_config_audit.py` ha ancora l'impalcatura di quando A8a e B-9 non c'erano:
   - 9 segni «updated in A8a (accounts check, H reviews)»;
   - `importlib` e `ModuleType`;
   - `ACCOUNTS_CHECKS_MODULE`, `ACCOUNTS_CHECK_IDS` e `_accounts_checks()`, con i rossi «red until A8a»;
   - l'import protetto di B-9, con due sostituti che dicono «B-9 is not written»;
   - la parentesi di (c) che spiega l'impalcatura;
   - in (a), «Everything else is ok», che dopo (f) e (g) non è più vero alla lettera.
3. `_configure` non svuota le note di H-36: se un altro test nello stesso processo lascia una nota (`_untrusted_
   forwarding`), `platform.client_address` diventa un warning, e i test che vogliono tutti i controlli ok, o il log
   vuoto, falliscono.

**Progetto**:
- La cura in `config_audit.py`: le due docstring (della funzione e del modulo). Nessun cambio di comportamento.
- Il test-author, in `test_config_audit.py`:
  - import diretti di `ACCOUNTS_CONFIG_CHECKS`, `check_login_limit`, `BACKUP_CONFIG_CHECKS`, `check_panel_token` e
    `check_upload_limit`;
  - `CHECK_IDS` nell'ordine di `CONFIG_CHECKS`, con l'id di A;
  - via l'impalcatura e i segni;
  - il test della tupla intera sui gruppi importati;
  - `_configure` svuota le note, con `monkeypatch.setitem`;
  - un rosso: una nota lasciata prima di `_configure` non deve arrivare all'audit.
- Selettori: `services config-audit`, `accounts-checks`, `backup-checks`, `email-checks` e `client-address`.

1. ✅ **Test** (test-author, che non ha lanciato nulla; 17/10, mattina), solo in `test_config_audit.py`:
   - import diretti dei gruppi di A, B ed E; `CHECK_IDS` nell'ordine di `CONFIG_CHECKS`, con `accounts.login_limit`;
   - via `importlib`, `ModuleType`, `ACCOUNTS_CHECKS_MODULE`, `ACCOUNTS_CHECK_IDS` e `_accounts_checks()`, l'import
     protetto di B-9 con i due sostituti, e i 9 segni «updated in A8a». Il grep di `A8a`, `B-9`, `red until`,
     `importlib`, `ModuleType` e `ACCOUNTS_CHECK` non trova più nulla;
   - il test della tupla intera sui gruppi importati, più `tuple(CONFIG_CHECKS) == tuple(CHECK_IDS)`, che ora fissa
     anche l'ordine dentro il gruppo di ogni workstream;
   - `_configure` svuota le note di H-36 (`monkeypatch.setitem`, due righe), con un test nuovo in (f);
   - le docstring (a), (c) e (f).
   - Io ho corretto un commento: «its two checks» di E diventa «three», per `email.links`.
2. ✅ **Rosso e verde** (`files/runs/h35-redgreen.sh`):
   - **Rosso**: una copia temporanea con le due righe del reset commentate. `services config-audit` dà **1 failed /
     155 passed**: il test nuovo, «check_client_address() must be (…, 'ok', …), not (…, 'warning', …untrustedProxy,
     {'headers': 'X-Forwarded-For'})». Poi il file è ripristinato (`cmp` uguale).
   - I 155 test di prima ci sono tutti: la pulizia non ne ha perso nessuno.
   - **Cura** (`files/h35/apply.py --apply`, identica alla copia di prova): le due docstring di `config_audit.py`.
     - Il modulo: l'avvio si ferma su una configurazione con cui il server non deve partire, e `GET
       /api/v1/security/checks` li valuta già.
     - La funzione: `AdminBootstrapConfigError` (F02) e il `ValueError` di `LIBREFOLIO_LOGIN_LIMIT` (F15), più i
       controlli del backup fra quelli che si limitano a scrivere nel log.
   - **Verde**:

     | Comando | Esito |
     |---------|-------|
     | `services config-audit` | 156 passed |
     | `services accounts-checks` | 76 passed |
     | `services backup-checks` | 57 passed |
     | `services email-checks` | 87 passed |
     | `services client-address` | 360 passed |
     | ruff, black | puliti |
     | `git diff --check` | pulito |

   - Nessun documento dice ancora che la scheda «valuterà» i controlli.
   - `git merge-file` contro dev `67dd18676`: 0 conflitti. Porta libera.
3. ✅ **Ingresso** (17/10, ~09:35): H-35 è entrato in dev `d28a6d7df`, senza riga di CHANGELOG. Il mio HEAD è avanzato a
   `d28a6d7df`.
   - Il coordinatore ha dato l'OK di scrittura per H-19.
   - Per H-42 vuole prima l'analisi, e per gli E2E preferisce un header vero se il runner lo permette in modo pulito,
     altrimenti `page.route`.

### Lotto «H-42: tre direttive della CSP imposte accanto a `frame-ancestors`» (E, LOW, 2026-10-17, mattina) — ✅ provato

> Suggerimento di E dopo la chiusura di H-39: imporre già, nello stesso header di `frame-ancestors`, `object-src 'none';
> base-uri 'self'; form-action 'self'` (iniezione di `<base>`, esfiltrazione con un form). `script-src` resta in sola
> segnalazione. Da verificare con gli E2E che aprono i documenti e il visore PDF.

**Analisi** (sola lettura, HEAD `d28a6d7df`):

1. `security_headers.py`:
   - con la protezione dai frame accesa (default di managed), `FRAME_HEADERS` mette `X-Frame-Options: SAMEORIGIN` e
     `Content-Security-Policy: frame-ancestors 'self'` su **ogni** risposta: pagine, documenti, API, file;
   - `CSP_REPORT_ONLY_POLICY` contiene già le tre direttive, ma solo in sola segnalazione e solo sulle pagine HTML
     dell'app;
   - nessuna rotta mette una CSP sua.
2. **Chi le userebbe**:
   - l'app (sorgenti): nessun `<object>`, `<embed>` o `<base>`, nessun `formaction` né `<form action=…>`; SvelteKit ha
     `paths.base: ''`;
   - il visore PDF è EmbedPDF: PDFium in WebAssembly, dentro un worker di modulo, e disegna su canvas;
   - i documenti costruiti (`mkdocs_src/site`, 1337 pagine): nessun `<object>`, `<embed>` né `<base>`. Gli unici form
     sono `md-header__option` (la tavolozza) e `md-search__form` (la ricerca), tutti e due senza `action`, gestiti in
     JavaScript e sulla stessa origine;
   - nessun PDF nei documenti.
3. **Un rischio, se le tre direttive vanno su ogni risposta.** Chromium tratta il suo visore PDF integrato come un
   plugin, e `object-src 'none'` *sulla risposta del PDF* può impedirgli di mostrarlo. È da una ricerca web, non
   verificato: in headless il visore non c'è, e nessun E2E potrebbe vederlo. Oggi l'app non apre un PDF navigandoci
   sopra:
   - `uploads/file` risponde sempre `attachment`;
   - `brokers/files/{id}` dà `inline` solo con `download=false`, che il frontend non manda mai.

   Un'apertura in una scheda nuova, domani, si romperebbe in silenzio.
4. **Il runner** non permette una corsia con l'header vero. `configure_test_runtime` toglie ogni `LIBREFOLIO_*` dello
   sviluppatore, salvo `TEST_LANE_KEEPS` e `LIBREFOLIO_TEST_*`, e un run ha un solo backend condiviso. Servirebbe
   un'opzione nuova (per esempio `--lane-setting NOME=VALORE`, con una lista di nomi ammessi), cioè lavoro su `_cli.py`
   e su `cli_base.py`, con i loro test e documenti.
5. **E2E esistenti**: `files-pdf-offline` (il visore PDF) e `docs-offline-math` (una pagina annidata dei documenti)
   usano già `context.route` / `page.route`. Il service worker dell'app (`static/sw.js`) risponde alle navigazioni con
   `respondWith(fetch(…))`: uno spec che inietta header deve bloccarlo (`serviceWorkers: 'block'`), altrimenti la
   navigazione non passa dalla rotta. Nessuno spec ascolta oggi `securitypolicyviolation`.

**Proposta**:
- **Codice** (`security_headers.py`, mio): a protezione accesa, le risposte `text/html` (pagine dell'app e documenti)
  hanno `frame-ancestors 'self'; object-src 'none'; base-uri 'self'; form-action 'self'`; le altre restano con
  `frame-ancestors 'self'` soltanto, così un PDF mostrato inline non subisce mai `object-src`. Il self-hosted non
  cambia (interruttore spento per default), e una CSP messa da una rotta vince ancora.
- **Test backend** (`services security-headers`): i due valori per tipo di contenuto, il self-hosted senza nulla, la
  CSP di una rotta che resta, `/mkdocs` in HTML con la politica intera, il JSON delle API con solo `frame-ancestors`.
- **E2E: `page.route` invece della corsia con l'header vero.** Uno spec nuovo, nella suite normale e quindi una guardia
  permanente:
  - inietta la politica nelle risposte HTML, con i service worker bloccati;
  - controlli positivi: un `<object>` e un `<base>` iniettati devono dare un `securitypolicyviolation`;
  - poi la ricerca dei documenti dà risultati, l'anteprima PDF arriva a `data-state="ready"`, e la dashboard si apre,
    senza nessuna violazione.

  Una corsia vera girerebbe solo quando qualcuno la lancia. La corsia managed per gli E2E del cloud può essere una voce
  del backlog a parte.
- Documenti: `security.md#managed-headers`, la riga di `LIBREFOLIO_FRAME_PROTECTION` in `configuration`,
  `hosting_providers`; CHANGELOG 🔒 (cambia anche il self-hosted di chi accende l'interruttore).
- Serve: l'OK di scrittura sulla registrazione dello spec (`_frontend_utility.py`) e uno slot E2E.

**Via del coordinatore** (17/10, mattina): «OK a 1 e 2».
- Le tre direttive solo su `text/html`, `frame-ancestors` su ogni risposta.
- L'E2E con `page.route` come guardia permanente: `serviceWorkers: 'block'`, prima i controlli positivi con `<object>`
  e `<base>`, poi documenti, PDF e dashboard senza violazioni.
- OK di scrittura su `_frontend_utility.py`, per una registrazione in aggiunta.
- La corsia managed per gli E2E del cloud diventa una riga sua del backlog (**H-43**).
- Lo slot E2E arriva più tardi, in coda.

1. ✅ **Rossi** (test-author, che non ha lanciato nulla), in `test_managed_headers.py`, selettore
   `services managed-headers` (puro, senza slot):
   - `test_page_policy_is_pinned_by_value`: il valore esatto, direttiva per direttiva e nell'ordine. `PAGE_POLICY` si
     legge per nome, con `getattr`: prima della cura fallisce lui solo, nominando H-42, e il resto del file si
     raccoglie e gira;
   - (g) `test_the_enforced_policy_follows_the_type_of_the_response`. I modi sono quelli con l'interruttore acceso
     (managed, e self-hosted con `LIBREFOLIO_FRAME_PROTECTION=true`), per 10 risposte tipizzate:
     - `text/html` in quattro forme (`charset`, maiuscolo, misto; su `/`, una rotta lato client, `/mkdocs/user/` e la
       Swagger UI) prende `PAGE_POLICY`;
     - un PDF dei broker, un'immagine, un chunk JavaScript, un CSS, il JSON delle API e una 204 senza `Content-Type`
       tengono `frame-ancestors 'self'` soltanto;
   - `test_an_html_page_keeps_the_policy_its_route_set`: una CSP messa dalla rotta su una pagina HTML vince ancora;
   - (a) e i test della rotta, aggiornati: le pagine HTML con la politica intera, il resto come prima; l'interruttore
     spento non mette nulla.
   - Rosso (`files/runs/h42/red-managed-headers.log`): **29 failed / 227 passed**:
     - 18 di (a), le pagine HTML;
     - 8 di (g), le quattro forme HTML per due modi;
     - 1 il pin;
     - 2 di `test_a_header_the_route_set_is_kept_and_the_others_are_added`.
   - Già verdi prima della cura, come devono: le 12 risposte non HTML e la CSP della rotta.
2. ✅ **Cura** (`files/h42/apply.py`: prova, poi `--apply`, i tre file identici alle copie di prova):
   - `security_headers.py`: `PAGE_POLICY` (`frame-ancestors 'self'; object-src 'none'; base-uri 'self'; form-action
     'self'`) e `PAGE_FRAME_HEADERS`;
   - `_is_html(headers)`, per `content-type`, che ora usa anche `_is_web_app_page`;
   - il middleware si costruisce `self.page_headers` una volta, accanto a `self.headers`, e a ogni risposta sceglie
     `page_headers` se è HTML. Una CSP messa dalla rotta resta la sua, come prima;
   - docstring del modulo: perché solo l'HTML (il visore PDF di Chromium è un plugin);
   - i commenti di `LIBREFOLIO_FRAME_PROTECTION` in `config/__init__.py` (docstring e campo) e in `.env.example`.
     Le righe non commentate di `.env.example` non cambiano.
3. ✅ **Verdi** (`files/runs/h42-backend.sh`, cancello del carico):

   | Selettore | Esito |
   |---|---|
   | `services managed-headers` | 256 passed |
   | `services security-headers` | 15 |
   | `services config-env-example` | 38 |
   | `services config-package` | 863 |
   | `services config-audit` | 156 |

   - ruff e black puliti sui 3 file Python;
   - porta 6181 libera.
4. ✅ **Documenti per l'admin** (docs-writer, solo inglese, nessun timbro):
   - `configuration.en.md`, la riga di `LIBREFOLIO_FRAME_PROTECTION`;
   - `hosting_providers.en.md`, il punto «Frame protection», con il link alla sola pagina `configuration.md`. Una
     pagina non tradotta che punta a un'ancora di `configuration` rompe la build stretta, perché le traduzioni non
     hanno le ancore nuove.
   - Il debito di traduzione di `configuration` va in H-5.
5. ✅ **Spec E2E** (test-author), `frontend/e2e/layout/page-policy.spec.ts`:
   - `serviceWorkers: 'block'`; la politica iniettata in ogni documento della corsia con `route.fetch({maxRedirects:
     0})`; uno script d'avvio che registra ogni `securitypolicyviolation`, contando solo quelle imposte;
   - **controlli positivi** sulla pagina d'accesso: il documento arriva con la politica; un `<base>` iniettato, un form
     inviato a `https://example.invalid` e un `<object>` sulla corsia danno ciascuno la sua violazione (`base-uri`,
     `form-action`, `object-src`); l'URL base resta quello della corsia; nessuna richiesta di controllo parte;
     nient'altro viola;
   - poi tre flussi, ciascuno con un solo documento che porta la politica e nessuna violazione alla fine:
     - una pagina annidata dei documenti e la ricerca di Material di «conventions», con un risultato a schermo;
     - un PDF di una pagina caricato e aperto in anteprima dalla pagina File, fino a `file-preview-pdf`
       `data-state="ready"`, poi cancellato in `afterEach`;
     - la vista principale della Dashboard (`dashboard-page` assestata, `dashboard-overview-tab`).
6. ✅ **Registrazione** (dopo il ff a `9b23bdbfe`; `files/h42/register.py`: prova, `--apply`, `cmp`):
   - `front_page_policy` dopo `front_docs_offline_math`;
   - `add_test(cat, "page-policy", …)` dopo `docs-offline-math`, con il prerequisito dei documenti costruiti.

   Controlli leggeri (`files/runs/h42-light.sh`, cancello del carico):
   - Prettier pulito sullo spec;
   - `tsc --noEmit`: 0 errori nello spec. Le 61 righe d'errore stanno tutte in file che H-42 non tocca, quindi c'erano
     già;
   - ruff e black puliti su `_frontend_utility.py`;
   - `check-orphans`: 140 spec registrati, tutti raggiungibili da `all`;
   - `front-utility --help` elenca `page-policy`.
   > **⚠️ Fuori pista**: il test-author ha scritto le righe di registrazione senza toccare il file, perché
   > `_frontend_utility.py` arrivava cambiato con il ff di H-19; le ho aggiunte io dopo il ff.
7. ✅ **Documenti per sviluppatori** (docs-writer, solo inglese; `security.md` non ha traduzioni, quindi nessun
   debito):
   - `security.md#managed-headers`:
     - la riga della CSP della tabella diventa due: `PAGE_POLICY` sulle risposte HTML, `frame-ancestors 'self'` sul
       resto;
     - il punto «Frame protection» spiega `_is_html()` (prefisso `text/html`, qualsiasi maiuscola, con parametri);
     - due punti nuovi: «Three more directives on documents (H-42)» e «Why HTML only»;
     - il paragrafo dei test di `managed-headers`, e uno nuovo sullo spec Playwright.
   - Fuori da questa sezione `frame-ancestors` non compariva altrove.
   - Due ritocchi miei:
     - davanti al percorso dello spec il comando del runner, che il docs-writer non poteva citare prima della
       registrazione;
     - «Swagger UI and ReDoc» diventa «the pages FastAPI writes for Swagger UI and ReDoc». L'HTML di FastAPI l'ho
       verificato (`get_swagger_ui_html`, `get_redoc_html`: niente `<object>`, `<embed>`, `<base>`, form né `action`);
       i bundle che caricano da jsDelivr no.
   - Controlli (`files/runs/h42-docs.sh`, cancello del carico):
     - `mkdocs build` stretto: rc 0, nessun warning;
     - `check-links`: 97 link validi;
     - `git diff --check` pulito.
   > **⚠️ Fuori pista: l'analisi, punto 3, era sbagliata sui file dei broker** (trovato dal docs-writer, verificato).
   > `api/v1/brokers.py:750` costruisce lo stesso `source_url` dell'anteprima, `…/download?download=false`, e il
   > frontend lo usa, nei dialoghi d'import dei broker (`BrokerImportFilesModal`, `ImportWizardModal`): il PDF arriva
   > inline. Il caso di un PDF mostrato in un `<iframe>` esiste quindi già oggi, nel ripiego dell'anteprima, e la scelta
   > «solo HTML» lo protegge davvero. Il test (g) usa proprio quella rotta. H-44 precisato nel backlog: riguarda solo la
   > pagina File (`uploads/file`, sempre `attachment`).
   > **Lacuna dichiarata nei documenti** (dal docs-writer): `image/svg+xml` e `application/xhtml+xml`, documenti
   > anche loro, tengono il solo `frame-ancestors`. Gli SVG serviti sono quelli della build e dei documenti, e un SVG
   > dell'utente arriva come `attachment`, dagli upload e dai broker (`INLINE_SAFE_MEDIA_TYPES` di `brokers.py` non ha
   > `image/svg+xml`). Allargare `_is_html` non rientra nel disegno approvato: lo propongo a E come possibile seguito.
8. ⏳ **Slot E2E** («GO 6181», 10:19–10:27, partito con il carico a 5 minuti a 47,7; `files/runs/h42-slot.sh`):
   - la build di debug ricostruita dal runner (era vecchia dal ff);
   - `--fresh-run front-utility page-policy`: **1 failed / 3 passed**; con `--workers 4`: lo stesso. Porta libera.
   - **Verdi in tutti e due**: i tre flussi veri sotto la politica, senza nessuna violazione imposta (la ricerca dei
     documenti, l'anteprima PDF fino a `data-state="ready"`, la Dashboard). È la verifica che conta per H-42.
   - La regressione di `files-pdf-offline` e `docs-offline-math` è tolta (coordinatore: la ragione regge, la corsia
     manda gli stessi header di prima).
   - **Rosso**: il controllo positivo dell'`<object>`. `base-uri` e `form-action` scattano, `object-src` no.
   > **⚠️ Fuori pista: un comportamento di Chromium 149, non della politica.** Sonde fuori corsia
   > (`files/h42/probe/*.cjs`, Playwright 1.61, headless shell; nessuna porta, origine finta servita da `route`):
   > - su una pagina banale ogni `<object>` è controllato, in ogni sequenza, anche fuori schermo
   >   (`object-src.out`, `sequence.out`, `offscreen.out`);
   > - sulla **build vera** della SPA servita dalle rotte (`realapp.out`, `realapp-bisect.out`):
   >   - `<object>` di un'immagine da solo, o con il `<base>`: violazione, nessuna richiesta;
   >   - **`<object>` di un'immagine più `form.submit()` nello stesso task**: nessuna violazione, e il PNG **parte come
   >     immagine** (lo ferma solo la rotta dello spec);
   >   - lo stesso `<object>` col form un secondo dopo: violazione;
   >   - `<object>` tipizzato `application/pdf` o `text/html` nella sequenza esatta dello spec: violazione, nessuna
   >     richiesta.
   >
   > La politica blocca quindi ciò per cui `object-src` esiste (plugin e documenti). Il buco riguarda solo
   > un'immagine, che un `<img>` potrebbe caricare comunque (`img-src` non è nella politica imposta). Lo dico a E.
   - **Riparazione** (test-author, che non ha lanciato nulla): il controllo diventa un `<object>` `application/pdf`
     su `/lf-page-policy-control.pdf?lf-page-policy-control`, con il perché nella JSDoc di `CONTROL_OBJECT_PATH`.
     Stesso ordine, stesse asserzioni. Per l'oggetto la prova è la violazione imposta: nessuna richiesta l'avrebbe
     comunque mostrata, perché il headless non ha il visore PDF.
   - Ritocchi miei:
     - la frase dello spec in `security.md`, con il perché in una riga;
     - la descrizione del runner («an <object> typed application/pdf»).
   - Prettier pulito.
9. ✅ **Secondo slot** («GO 6181», 10:47–10:51, carico a 5 minuti 36,9; `files/runs/h42-slot.sh`; i log del rosso
   tenuti come `e2e-page-policy-{1,4}-red.log`):
   - `--fresh-run front-utility page-policy`: **4 passed**;
   - con `--workers 4`: **4 passed**;
   - nessun retry; porta 6181 libera.
   - Dopo la riparazione: `mkdocs build` stretto pulito, 97 link validi, ruff e black puliti su `_frontend_utility.py`,
     `git diff --check` pulito (`files/runs/h42-docs2.sh`).
   - Il comportamento di Chromium va nel checkpoint, come nota per la revisione di E (coordinatore).

### H-3, opzione A: il contesto per la decisione P24 (2026-10-17, mattina) — analisi, decisione del developer

> Il coordinatore chiede prima l'analisi, e se serve una decisione del developer va registrata. P24 è ancora
> *aperto* (`decisioni-analisi-20261014.md`): il developer vuole più contesto, cioè dove sta la chiave, che cosa
> protegge e perché nel cloud è più sicuro. Qui le risposte, sul codice di oggi (HEAD `d28a6d7df`).

**Dove sta la chiave d'istanza**
- **Configurata**: `LIBREFOLIO_INSTANCE_KEY`, oppure `LIBREFOLIO_INSTANCE_KEY_FILE` (un Docker secret), fuori dalla
  cartella dei dati. Se non si può usare, l'avvio si ferma.
- **Altrimenti generata** al primo uso: `<cartella dati>/secrets/instance.key`, 32 byte casuali, cartella `0700` e file
  `0600`. Sta nello stesso volume dei dati, ma non nel database.

**Che cosa protegge** (le derivazioni di oggi, `derive_key`)
- `plugins.settings.v1` e `plugins.settings.fingerprint.v1` (X): cifrano i **segreti salvati delle impostazioni dei
  plugin**, come le chiavi API dei provider. Ogni riga tiene il `key_id` della chiave che l'ha cifrata.
- `accounts.address-probe.v1` (A): firma il nonce della prova dell'indirizzo; non salva nulla.
- I **backup**: un archivio protetto da password porta con sé la chiave generata (decisione 39, B4), e il ripristino
  ricifra i segreti con la chiave dell'istanza che ripristina. Un archivio in chiaro non la porta.
- **Non** protegge: le password (sono hash), le sessioni (`JWT_SECRET`), i dati finanziari (in chiaro nel DB).

**Che cosa succede se il file sparisce** (self-hosted con la chiave generata)
- Al primo uso ne nasce una nuova, senza avvisi. Con dei segreti salvati, il primo uso è all'avvio (H-15).
- I segreti salvati diventano illeggibili, e l'avvio scrive un **errore con il conteggio** (`platform.plugin_secrets`,
  anche nella scheda Sicurezza).
- La doc dice di rimettere la copia vecchia *prima* di inserire di nuovo i segreti (opzione B, entrata il 16/10).
- **Il rischio che resta**: se l'amministratore inserisce di nuovo i segreti prima di accorgersene, finiscono cifrati
  con la chiave nuova. Rimettere poi la vecchia rende illeggibili proprio quelli.

**Perché nel cloud è più sicuro**
- Il pannello configura la chiave (un `_FILE`), fuori dal volume dei dati: un ripristino dei dati non la tocca, e non
  si genera mai da sola.
- Se manca o è rovinata, l'avvio si ferma: fallisce chiuso.
- Un cambio di chiave lo segnala comunque H-15.

**L'opzione A, da decidere (P24)**: nessuna chiave nuova in silenzio quando il DB ha segreti.
- Il passo d'avvio `plugin-secrets-check` vede che il file della chiave manca e che ci sono righe con un segreto
  (contate senza derivare). Allora vieta la generazione per tutto il processo, e scrive un errore che dice cosa fare.
- Le funzioni con segreti rispondono come con una chiave inutilizzabile: 503. Il 503 della prova dell'indirizzo è H-19,
  in corso.
- Un comando esplicito, `./dev.py instance-key new`, riparte con una chiave nuova.
- Cambia solo uno stato già guasto, e solo nel self-hosted. Un'installazione nuova genera la chiave come oggi.
- Peso: un lotto piccolo-medio, che tocca `instance_key.py`, `plugin_secrets_check.py`, il comando in `dev.py`
  (superficie condivisa), la doc admin (con debito di traduzione) e i test.

**Il mio consiglio**: per la 1.3 basta l'opzione B, già fatta. La A migliora il self-hosted, non il cloud. Proposta:
rimandarla dopo la 1.3, salvo una scelta diversa del developer. Per ora H-3 resta aperta su P24.

### Lotto «H-19: `POST /users/address-probe` risponde 503 se la chiave d'istanza non si può usare» (2026-10-17, mattina) — ✅ provato

> Dall'analisi di H-3 (16/10). Il codice è di A: OK di scrittura del coordinatore su `api/v1/users.py` (solo
> `issue_address_probe`) e su `test_api/test_address_probe_api.py`, e A rivede.

**Analisi** (sola lettura):
- `issue_probe_nonce()` chiama `derive_key(PROBE_PURPOSE)`, che solleva `InstanceKeyError` quando la chiave non si può
  usare. A runtime succede con un file generato rovinato o irraggiungibile; una chiave configurata ferma già l'avvio.
- La rotta non la prende, quindi risponde 500 con il traceback nel log. `verify_probe_nonce()`, il controllo pubblico,
  la tollera già e risponde `False`.
- Il frontend (`checkAddress`) legge già ogni errore della richiesta del nonce come *unverifiable*.
- Lo schema esiste già: `plugin_settings.py` risponde 503 per una chiave inutilizzabile.
- Il ramo di A non tocca la riga: `git merge-file` contro `e58be67fe` dà 0 conflitti su tutti e due i file.

1. ✅ **Rossi** (test-author, che non ha lanciato nulla), nel file di A:
   - AP-API-12: in processo, la `derive_key` del modulo sostituita da una che solleva. Prima una barriera (la stessa
     chiamata con la `derive_key` vera dà 200), poi 503 con il corpo esatto, nessun nonce, un solo warning esatto,
     nessun errore e nessun `exc_info`;
   - AP-API-13: il controllo pubblico, nello stesso stato, risponde 200 `{"match": false}`.
2. ✅ **Slot** (`GO 6181`, 09:50–09:56, con gli E2E di E e J in corso; dentro lo slot senza il cancello del carico),
   `files/runs/h19-slot-go.sh`:
   - **rosso**, per nome: **1 failed / 1 passed**. AP-API-12 dà «InstanceKeyError left the app»: prima della cura,
     un 500 con il traceback;
   - **cura** (`files/h19/apply.py --apply`, identica alla copia di prova): `try` intorno a `issue_probe_nonce()`; per
     un `InstanceKeyError`, `logger.warning("Address probe: the instance key cannot be used, no nonce issued",
     admin_id=…)` e `HTTPException(503, {"error_code": "INSTANCE_KEY_UNAVAILABLE", "message": …}) from None`;
   - **verde**: `api address-probe` intero, **28 passed**. Porta libera.
3. ✅ **Documenti** (docs-writer, solo inglese, pagine per sviluppatori):
   - `access_control.md`, la riga della rotta: `503` `INSTANCE_KEY_UNAVAILABLE`, con il link alla chiave d'istanza;
   - `security.md`, «Verification» dell'Address Probe: «Issuing has no such fallback… 500» diventa il 503 con il
     warning a ogni chiamata rifiutata, e il paragrafo dei test ha il caso in processo.
   > **⚠️ Fuori pista** (dal docs-writer di H-42): il ripiego dell'anteprima PDF (`FilePreviewModal`, un `<iframe>`
   > su `/api/v1/uploads/file/{id}`) riceve sempre `attachment`, quindi probabilmente scarica invece di mostrare. È
   > precedente, senza proprietario: registrato come **H-44** (decisione del coordinatore), con il legame a H-42.

### Review di B-18 (`restore --instance-key-file`, commit `7b1911fd6` sul ramo di B) (2026-10-17, 10:55) — ✅ OK, una nota LOW e due nit

> Chiesta dal coordinatore: blocca l'ingresso di B. Sola lettura (`git show`/`git diff` sul ramo di B), più una sonda
> pura nella cartella della sessione (`files/b18review/probe_not_created.py`, una cartella dati temporanea, nessuna
> porta). B-18 non tocca file di H: usa le mie API, `read_secret_file`, `derive_key_from`, `instance_key_status`.

**Verificato, va bene:**
1. `_refuse_unusable_instance_key` (in `staging.py`), prima del lock e della cartella della copia.
   - Il mio `_checked` solleva `InstanceKeyError` solo per la lunghezza (`_length_problem`), quindi «too short» è
     esatto.
   - `TypeError` e `ValueError` dalla CLI non si raggiungono: la chiave è sempre un testo, scopo e lunghezza sono
     costanti.
   - Il messaggio non porta né la chiave né la sua lunghezza.
2. **D1**: `archive_key = … if INSTANCE_KEY_ENTRY in entries else instance_key`.
   - `instance_key_included` resta `manifest.instance_key.included`: una chiave data non risulta mai «included».
   - `archive_key` serve solo a `_plugin_secrets` e non si scrive mai nella cartella dei dati.
3. **Ordine nella CLI**: `_restore_keys` legge prima il file della chiave, poi la password, e solo dopo
   `_data_dir_for` → `_drop_root_privileges`.
   - `read_secret_file(…, "instance key file")`: i miei messaggi alla lettera, più `(instance_key_unreadable)`; la
     chiave mai stampata.
   - Stessa regola di lettura del file generato e di `LIBREFOLIO_INSTANCE_KEY_FILE` (BOM, a capo finali): la copia di
     `secrets/instance.key` dà lo stesso testo.
4. `instance_key_status()` è usata come documentato (non crea, non solleva). `--test-db` è già impostato da
   `_data_dir_for`, quindi la cartella dei dati è la stessa del controllo.
5. **Test**:
   - solo nomi pubblici miei;
   - il test della CLI confronta il messaggio con quello di `read_secret_file` stessa, non con un letterale copiato;
   - `no_inherited_instance_key` (autouse) toglie `LIBREFOLIO_INSTANCE_KEY(_FILE)`; `setenv` via `monkeypatch`.
6. **Doc**:
   - i messaggi di `cli_tools.en.md` coincidono con `read_secret_file` (65536 = `SECRET_FILE_MAX_BYTES`);
   - `/app/backend/data/prod-docker` è il `LIBREFOLIO_DATA_DIR` del Dockerfile e del compose, dove è montato
     `./LibreFolio-data`;
   - un `old-instance.key` lasciato in `backups/` non si archivia mai (un backup prende solo `sqlite` e
     `ARCHIVED_FOLDERS`) e non si scarica mai (i download vanno per id del job).
7. **Unione con H-42**: si sovrappongono backlog, `security.md` e `_frontend_utility.py` (gli ultimi due arrivano da
   dev nella base di B; B-18 non li tocca). `git merge-file`: 0 conflitti su tutti e tre.

**LOW-1 (codice di B, non blocca)**: la riga D2 accusa la chiave data quando la chiave di questa istanza non si è potuta
*generare*.
- Se l'istanza non ha ancora la chiave (il caso tipico della migrazione dal cloud a un server nuovo, dove la chiave
  nasce al primo uso), il controllo prova a crearla (`settings_subkey` → `_instance_key` → `_create_key_file`).
- Se non ci riesce (`secrets/` non scrivibile, file system in sola lettura), `_plugin_secrets` conta tutto
  illeggibile.
- `instance_key_status()` dice ancora `not_created`, `problem=None`, quindi `_print_given_key` stampa la riga D2.
- Sonda (`probe_not_created.out`): `settings_subkey()` → «the instance key cannot be generated (Permission denied)»;
  `instance_key_status()` prima e dopo → `not_created`, `problem=None` → ramo D2.
- Cura proposta, in una riga: in `_print_given_key`, prendere il ramo dell'eccezione anche per
  `source == "not_created"`, con una frase che nomina la cartella. Quando si arriva a D2 la copia ha segreti, quindi
  il controllo ha già provato a derivare la chiave: se dopo non esiste, non si è potuta generare. Più un caso di test
  accanto a c7.

**Nit di doc** (facoltativi, di B):
- `cli_tools.en.md`, il punto 📄: «The line breaks at its end do not count» → aggiungere che nemmeno un BOM iniziale
  conta, e che gli spazi invece contano. Un vecchio `LIBREFOLIO_INSTANCE_KEY` vale «as written, spaces included»
  (`env_secret`).
- `backup_restore.en.md`: finché sta in `LibreFolio-data/backups/`, il file della chiave vecchia con `chmod 600`.

**Per H** (nessuna richiesta a B): la docstring di `derive_key_from` descrive già questa strada; nominare
`--instance-key-file` lì è un ritocco mio facoltativo, in un lotto futuro.

### Lotto «H-46: `LIBREFOLIO_TEST_MODE` acceso fuori da una corsia di test» (E, review di X-R44, LOW, 2026-10-17) — ✅ provato

> Dal coordinatore (17/10, 10:52), dalla review di X-R44 di E: nessun controllo segnala `LIBREFOLIO_TEST_MODE` su
> un'istanza in esercizio, e da X-R44 (dev `5a8c64c5c`) i doppi di test restano irraggiungibili solo a test mode
> spento. Voce H nuova: un controllo della configurazione, di livello `error` quando test mode è acceso fuori dal
> server di test. Da prendere dopo H-42, se è piccolo.

**Analisi** (sola lettura, dev `1c8eba6f5`):
1. **Cosa cambia `is_test_mode()`** (`1`, `true` o `yes`, letto solo dall'ambiente, mai da `.env`):
   - `get_data_dir()` passa alla cartella di test (`LIBREFOLIO_TEST_DATA_DIR`, o `backend/data/test/`). Nell'immagine
     è `/app/backend/data/test`, **fuori dal volume** `/app/backend/data/prod-docker`: i dati restano nel container e
     si perdono quando lo si ricrea. In più `ensure_data_dirs` non scrive il marcatore di produzione;
   - `Settings` non legge più `.env` (`settings_customise_sources`);
   - X-R44: `mockprov` e `mockfx` (`test_only`) tornano visibili a ricerca, assegnazione, probe, refresh e
     impostazioni. Quindi prezzi e cambi finti in un portafoglio vero, e rifiuti simulati;
   - innocui: il prewarm di BRIM acceso per default, la riga `test_mode=True` del log d'avvio, la stampa di
     `main.py`. `test-lane-health` vuole anche il lane id: senza, risponde 404.
2. **Come ci si arriva in produzione**:
   - `dev.py server` lo spegne sempre: `configure_server_runtime` scrive `LIBREFOLIO_TEST_MODE=0` e toglie
     `LIBREFOLIO_TEST_LANE_ID`;
   - **l'immagine parte invece con `uvicorn` diretto** (il `CMD` del Dockerfile). Un `LIBREFOLIO_TEST_MODE=1`
     nell'ambiente del container lo accende: `environment:` del compose, `env_file: .env` (per esempio un `.env` da
     sviluppatore riusato), il pannello di un hoster, `uvicorn` lanciato a mano;
   - oggi nessun controllo lo dice: solo la riga del log d'avvio.
3. **Il discriminante «server di test»**: `LIBREFOLIO_TEST_LANE_ID` (`owning_test_lane_id()`, `config/platform.py`).
   - Lo mette `configure_test_runtime` → `ensure_test_lane_id()`, per `dev.py test` (il runner, il server condiviso, i
     pytest in processo), per `dev.py server --test` (dev.py:205) e per la galleria;
   - lo toglie `configure_server_runtime`; una produzione avviata con `uvicorn` non lo ha;
   - non ferma un attaccante, perché chi scrive l'ambiente è l'operatore: serve a vedere un errore di configurazione.
4. **Chi se ne accorge nei test**:
   - i test del frontend (`securityChecks*.test.ts`, `SecurityTab.test.ts`) usano liste di controlli loro, e la scheda
     Sicurezza mostra i controlli per chiave i18n, senza codice per id: un id nuovo non tocca il frontend;
   - `test_config_audit.py`: `_configure` fissa `LIBREFOLIO_TEST_MODE` per caso ma eredita il lane id dal runner. Va
     reso esplicito.

**Proposta** (piccola, tutto in file di H):
- `check_test_mode()` in `config_audit.py`, id `platform.test_mode`, dopo `check_log_level` (in fondo al blocco della
  piattaforma, prima di B). In ogni profilo:
  - spento → `ok`, `instance.checks.testMode.off`;
  - acceso, con un lane id non vuoto → `ok`, `instance.checks.testMode.testLane`;
  - acceso senza lane id → **`error`**, `instance.checks.testMode.outsideTestLane`, `detail` `{"data_dir": …}` (la
    cartella di test in uso). Summary: «LIBREFOLIO_TEST_MODE is on outside a test lane: test-only providers are
    served, the data live in the test data directory <path> and .env is not read; unset it on a production
    instance».
  - Il server parte comunque, come per gli altri `error` dei controlli: errore nel log d'avvio e nella scheda
    Sicurezza.
- **Opzione per E**, fuori dal default: nel profilo managed fermare l'avvio, come `WeakSecretError`. H-43 (una corsia
  managed) avrebbe il lane id, quindi non ne sarebbe toccata.
- **i18n**: 3 chiavi nelle 4 lingue, in `lib/i18n/instance/` (`./dev.py i18n add`).
- **Test** (test-author), in `test_config_audit.py`:
  - `CHECK_IDS` +1; `_configure` mette il lane id (non produzione) e lo toglie (produzione);
  - i casi: spento, acceso con il lane id, acceso senza, lane id vuoto, le grafie di `is_test_mode`;
  - il `detail` e il summary esatti; all'avvio una riga `error` e l'avvio che continua.
- **Doc** (docs-writer):
  - `security.md`: una riga della tabella dei controlli e una frase;
  - `configuration.en.md`: la riga di `LIBREFOLIO_TEST_MODE` (pagina tradotta: debito per H-5);
  - il commento di `.env.example`, riga 38.
- **Selettori**: `services config-audit`, `services config-env-example`, `utils gate-i18n-catalog`,
  `utils gate-i18n-usage`, `mkdocs build` stretto. Nessuno slot.

**Via del coordinatore** (17/10, ~11:10): «go», con l'opzione managed già dentro, senza aspettare E. Nel profilo managed,
test mode acceso senza lane id **ferma l'avvio**, come un `JWT_SECRET` corto. Altrove resta un controllo `error` e il
server parte. E lo vede nella revisione del checkpoint.

**Contratto** (`files/h46/apply.py`, provato in copia: le tre copie di prova):
- `config_audit.py`:
  - `check_test_mode()` (`platform.test_mode`) dopo `check_log_level`, con le chiavi `off`, `testLane` e
    `outsideTestLane`; `detail` `{"data_dir": str(get_data_dir())}`; `TEST_MODE_OUTSIDE_LANE_SUMMARY`;
  - `_test_mode_outside_a_lane()`: `is_test_mode()` e un `owning_test_lane_id()` nullo o bianco;
  - `ManagedTestModeError(RuntimeError)`, sollevata in `log_configuration_audit()` subito dopo `WeakSecretError` e
    prima di ogni riga dei controlli, se il profilo è `managed`;
  - `get_data_dir()` senza `try`, come in `check_instance_key`: un server la cui cartella di test è rifiutata
    (`validate_test_data_dir` solleva solo `ValueError`) non parte proprio.
- `.env.example`: due righe di commento sotto quella di test mode; nessuna riga non commentata nuova.
- `config/__init__.py`: la riga di `LIBREFOLIO_TEST_MODE` nella docstring.
- i18n: `files/h46/i18n.sh` (3 chiavi, `dev.py i18n add`, poi `i18n check`). Il tono rispetta le voci vicine: l'IT
  dà del tu («Togli»), il FR del voi («Retirez»), l'ES del tu («Quita»).
- Verificati non toccati:
  - `test_backup_checks.py` di B: la sua fixture `platform` tiene il lane id del runner e i suoi assert filtrano le
    righe del backup;
  - `test_security_checks_api.py` di A: guarda solo che certi id ci siano, una volta ciascuno, sul server della
    corsia, che ha il lane id (lo vuole anche la sonda `test-lane-health` del runner);
  - `test_managed_headers.py` e `test_instance_block.py`: il lifespan non gira.
- In corso: i rossi (test-author, `h46-reds`) e la doc (docs-writer, `h46-docs`), in parallelo su file distinti.

> **⚠️ Fuori pista: la premessa dell'immagine nell'analisi era sbagliata** (trovato dal docs-writer, verificato da me).
> - `backend/data/` non entra nell'immagine (`.dockerignore`), e `entrypoint.sh` crea e cede all'utente del server
>   solo `LIBREFOLIO_DATA_DIR`. Quindi `/app/backend/data` è di root.
> - `configure_logging()` crea `get_data_dir()/logs` mentre si importa `backend.app.main`, senza `try`.
> - Sonda (`files/h46/probe/import_unwritable.sh`, nessuna porta): l'import in test mode, con la cartella madre della
>   cartella di test non scrivibile, si ferma su `PermissionError` in `get_log_directory()`, prima di ogni controllo.
> - Quindi **nell'immagine così com'è test mode ferma il server all'import**: niente doppi serviti, niente dati persi.
>   È dedotto dai file e riprodotto fuori da un container; in un container non è provato (Docker spento): va con CP7a.
> - Il controllo serve dove il server parte: `uvicorn` lanciato a mano o da un'unità di servizio, un'immagine con un
>   suo comando o con una cartella di test scrivibile. Il nome del problema resta giusto.
> - Corretti:
>   - la docstring di `check_test_mode` in `apply.py` (non ancora applicata);
>   - `security.md`, il paragrafo «Where it matters», con l'immagine dichiarata «not yet tried in a container»;
>   - `configuration.en.md`, due righe;
>   - `hosting_providers.en.md`, il punto «Test mode».
>   Il messaggio dell'analisi al coordinatore va corretto nel checkpoint.
> - Residuo per CP7a: provarlo in un container. Se confermato, valutare un messaggio chiaro prima di
>   `configure_logging()`, al posto del traceback di `PermissionError`.

**Documenti** (docs-writer, solo inglese, nessun timbro; più le correzioni sopra, mie, con `files/h46/docs_fix.py`):
- `security.md`:
  - la riga `platform.test_mode` nella tabella dei controlli;
  - il conto dei messaggi `instance.checks.*`, da 24 a 27;
  - due paragrafi dopo quello di H-39;
  - lo stop `ManagedTestModeError` come passo 2 di `log_configuration_audit()`; gli altri passi rinumerati.
- `configuration.en.md` (tradotta: debito per H-5):
  - la riga di `LIBREFOLIO_PROFILE`;
  - una riga ❌ nella tabella «Startup Checks», dopo il livello di log;
  - un paragrafo sullo stop managed;
  - la riga di `LIBREFOLIO_TEST_MODE`.
- `hosting_providers.en.md`: «eight things», una riga della tabella e il punto «Test mode».
- `settings.en.md`, pagina di A (A8b), tradotta: la riga «Test mode» in «What It Lists».
  - Più, mie, le tre righe che mancavano dei miei controlli H-36 e H-39 (`platform.client_address`,
    `platform.frame_protection`, `platform.csp_report_only`), nell'ordine di `CONFIG_CHECKS`: la pagina dice che i
    rilievi seguono l'ordine della tabella.
  - Mancano anche i due controlli di B (`backup.panel_token`, `backup.upload_limit`): li segnalo al coordinatore,
    non li scrivo io.
- Note del docs-writer verificate:
  - X-R44 non è nel mio HEAD. Su dev `plugin_settings.md#test-only` e `system_providers.md:31` dicono già «served only
    when `LIBREFOLIO_TEST_MODE` is on»: coerenti dopo l'aggiornamento di base;
  - un lane id di soli spazi esportato prima di un run romperebbe già la corsia: la sonda `test-lane-health` vuole un
    token di almeno 16 caratteri;
  - «The image has no test mode» (`docker_advanced`, `dev_workflow`): resta vero, anzi lo conferma la sonda.

1. ✅ **Rossi** (test-author, che non ha lanciato nulla), in `test_config_audit.py`:
   - `_configure` mette un lane id finto in test mode e lo toglie in produzione: nessun caso dipende più dall'ambiente
     del runner;
   - `CHECK_IDS` prende `check_test_mode` con `getattr`: il file si raccoglie anche prima della cura;
   - i due test d'ordine in (c) vogliono `platform.test_mode` dopo `platform.log_level`;
   - la sezione nuova (h), 12 funzioni e 47 casi:
     - spento: 7 grafie per 2 stati del lane id;
     - corsia: 5 grafie;
     - fuori dalla corsia: 2 grafie per 3 lane id;
     - lo stesso esito in ogni profilo;
     - nulla creato;
     - l'avvio self-hosted, con una riga `error` che continua;
     - lo stop managed col messaggio esatto, anche con l'istanza bloccata e con `" MANAGED "`;
     - lo stop del JWT corto resta primo.
   - Una barriera prima di ogni stato: `is_test_mode()`, e `get_data_dir()` nel `tmp_path`.
2. ✅ **Run** (`files/runs/h46-backend.sh`, cancello del carico, nessuno slot):

   | Passo | Esito |
   |---|---|
   | rosso `services config-audit` | **49 failed / 155 passed**, tutti col nome di H-46 |
   | cura `files/h46/apply.py --apply` | i tre file identici alle copie di prova |
   | i18n `files/h46/i18n.sh` | 3 chiavi in 4 lingue |
   | verde `config-audit` | **204** |
   | `config-env-example` | 38 |
   | `config-package` | 863 |
   | `backup-checks` (B) | 57 |
   | `accounts-checks` (A) | 76 |
   | `email-checks` (E) | 87 |
   | `gate-i18n-catalog` | 176 |
   | `gate-i18n-usage` | 195 |

   - ruff e black puliti sui 3 file Python; porta libera.
   - B, A ed E restano verdi: i loro test ereditano il lane id del runner.
3. ✅ **Documenti** (sopra): `mkdocs build` stretto pulito, 97 link validi, `git diff --check` pulito
   (`files/runs/h46-docs.sh`). I messaggi `instance.checks.*` sono 27 nelle 4 lingue, come dice `security.md`.
4. **Previsione di unione** con dev `2f4ef68e6`. Base `fb8661dd2`, cioè dev contiene già H-42.
   - 0 conflitti: `.env.example`, backlog, `security.md`.
   - `configuration.en.md`, 1 conflitto: la riga di `LIBREFOLIO_PROFILE`, cambiata da A9 (cosa cambia per gli utenti
     di un'istanza managed). Cura: la riga di dev, più la mia clausola accanto a quella del `JWT_SECRET` corto.
   - `hosting_providers.en.md`, 1 conflitto: «ten things» (dev) contro «eight things» (mio). Cura: «eleven things»;
     le righe della tabella si uniscono da sole.
   - Gli altri file non sono toccati da dev.
5. **Note per E**, dal test-author:
   - un profilo managed scritto solo in `.env` non si vede in test mode, perché `Settings` non legge `.env`: allora
     niente stop, solo l'`error`. I compose mettono `env_file:` nell'ambiente del processo; la doc lo dice;
   - `ensure_test_lane_id()` tiene un lane id di soli spazi, ma la sonda di prontezza del runner vuole almeno 16
     caratteri: una corsia così non partirebbe comunque;
   - `get_data_dir()` può sollevare in test mode (`validate_test_data_dir`), ma allora fallisce già l'import di
     `backend.app.main`: come per `check_instance_key`, nessun caso nuovo.

### Lotto «H-45: la politica delle pagine anche sui documenti SVG e XML; nessuna CSP su un 304» (E, LOW, 2026-10-17) — ✅ provato

> Dal coordinatore (17/10, dopo H-46), con la specifica di E:
> - riconoscere `application/xhtml+xml`, `image/svg+xml`, `application/xml`, `text/xml` e i tipi `+xml`;
> - i PDF restano fuori; il report-only resta su `text/html`;
> - un caso per tipo in `test_managed_headers.py`;
> - facoltativa: nessuna CSP su un 304 (un rischio latente se si aggiorna Starlette), con un test.

**Analisi** (HEAD `3bd1098ad`, dev con H-42 e H-46; Starlette 1.6.0):
1. **Chi risponde 304 oggi**:
   - `/`, la SPA e le pagine di `/mkdocs` passano da `_revalidated_file()`, cioè `FileResponse`. In Starlette 1.6 non
     gestisce `If-None-Match` (gestisce solo `Range` e `If-Range`): risponde sempre 200;
   - solo `StaticFiles` (il mount `/_app`, `ImmutableStaticFiles`) risponde 304, con `NotModifiedResponse`, senza
     `Content-Type`. Sotto `/_app` non ci sono pagine HTML;
   - quindi **H-42 oggi non perde nulla**. Correggo l'avviso che avevo dato al coordinatore al momento dell'unione:
     le pagine dei documenti non ricevono mai un 304.
2. **Il meccanismo è reale** (sonda `files/h45/probe/`: un server di sola libreria standard sulla porta 6181, poi
   Chromium 149, sia col profilo in memoria sia con uno persistente; `run3.out`):
   - una pagina servita 200 con `PAGE_POLICY`, poi rivalidata (`reload`, e `goto` di nuovo) con un 304;
   - 304 con `frame-ancestors 'self'` da solo, cioè quello che il middleware mette oggi su un 304: la pagina presa
     dalla cache **prende la CSP del 304**. Il `<base>` iniettato cambia l'URL base, e nessuna violazione scatta;
   - 304 senza CSP, oppure con `PAGE_POLICY`: la pagina resta protetta;
   - le prime due sonde non vedevano nessun 304: il server rispondeva in HTTP/1.0 e Chromium non mandava
     `If-None-Match`. Con HTTP/1.1 e un'immagine di controllo la cache si vede.
3. **Documenti SVG e XML serviti oggi**:
   - nessun SVG nella build, nei documenti costruiti, né nei plugin;
   - l'unico XML è `sitemap.xml` dei documenti (`FileResponse`, sempre 200);
   - un SVG dell'utente non arriva mai inline:
     - l'originale è sempre `attachment`;
     - l'anteprima `img_preview` passa da Pillow, che non apre gli SVG, e risponde 500;
     - i broker hanno `INLINE_SAFE_MEDIA_TYPES` senza SVG;
   - la rotta degli asset dei plugin (`/api/v1/uploads/plugin/…`) servirebbe inline un SVG fornito con il plugin.
     Oggi non ce n'è nessuno.
   - Quindi H-45 è difesa in profondità, senza effetti visibili oggi.
4. **Con H-45 la guardia del 304 diventa necessaria**, anche se ancora latente:
   - un SVG sotto `/_app`, rivalidato, perderebbe la politica come nella sonda;
   - lo stesso varrebbe per ogni pagina se un aggiornamento di Starlette desse a `FileResponse` i 304.

**Proposta** (solo file di H):
- `security_headers.py`:
  - `_media_type(headers)`: il primo `content-type`, prima del `;`, senza spazi, in minuscolo;
  - `_is_document()`: `text/html`, `application/xhtml+xml`, `image/svg+xml`, `application/xml`, `text/xml`, e ogni
    tipo che finisce in `+xml`. Prende `PAGE_POLICY`;
  - `_is_html()` resta, sul tipo esatto `text/html`, e serve solo al report-only (le pagine della web app);
  - **un 304 non riceve né `Content-Security-Policy` né `Content-Security-Policy-Report-Only`**: il browser tiene
    quella della risposta in cache. `X-Frame-Options`, `nosniff` e `Referrer-Policy` restano come oggi.
- **Test** (test-author), `test_managed_headers.py`:
  - un caso per tipo (con `charset` e maiuscole), i PDF e il JSON fuori;
  - un SVG su un percorso della web app: `PAGE_POLICY` sì, report-only no;
  - il 304 con il middleware da solo, anche con un `Content-Type` HTML (lo Starlette di domani), nei due profili;
  - un 304 vero da `StaticFiles` nello stack.
- **Doc**: `security.md#managed-headers` (anche la frase «Not covered: …» di H-42 e il paragrafo dei test), la riga
  di `LIBREFOLIO_FRAME_PROTECTION` in `configuration.en.md` (debito per H-5), il commento in `.env.example` e in
  `config/__init__.py`.
- **E2E**: nessuno. Lo spec di H-42 copia la regola dell'HTML, che non cambia, e nessun documento XML viene servito
  inline. Lo slot non serve.
- **Selettori**: `services managed-headers`, `security-headers`, `config-env-example`, `config-package`; `mkdocs
  build` stretto e `check-links`.
- **CHANGELOG**: proposta 🔒, ma oggi niente cambia per l'utente: decide il coordinatore.

### Review di A9 (le righe di A nei miei file) e di Z-28 (la parte della post-migrazione) (2026-10-17, 12:10) — ✅ OK

**A9** (`3c9303cf2`, entrato con `ba8f3b06e`): `LIBREFOLIO_TOS_URL` e `LIBREFOLIO_PRIVACY_URL`.
- `config/platform.py`: `tos_url()` e `privacy_url()` passano da `env_url`, come `support_url()`; i nomi sono
  costanti letterali, quindi la guardia di `.env.example` le vede.
- `instance_links.py`: `terms_link()` e `privacy_link()` non sollevano mai e scrivono l'errore una volta per
  processo, con il loro costo, attraverso `_report_invalid` (`functools.cache` sulla coppia problema-costo).
- `schemas/system.py`: `LegalInstanceConfig`, due campi nulli per default; `legal` con `default_factory`.
- `api/v1/system/instance.py`: nessun I/O sull'event loop, perché `env_url` legge solo l'ambiente.
- `.env.example`: due righe commentate accanto a `LIBREFOLIO_SUPPORT_URL`; nessuna riga non commentata nuova.
- Verdi sul HEAD unito (`files/runs/a9review.sh`): `services legal-links` 56, `services config-package` 864 (una più
  di prima di A9). `api instance-legal` non l'ho lanciato: vuole un server di corsia, e A l'ha fatto al suo
  checkpoint.
- **Nota, nessuna richiesta ad A**: `env_url` toglie una barra finale («so a path can be appended»), pensato per
  `LIBREFOLIO_PUBLIC_URL`. Per un link a una pagina (supporto, termini, privacy) `…/terms/` diventa `…/terms`. Quasi
  tutti i server rispondono con un redirect, quindi è innocuo in pratica. È una regola mia (`support_url`): la segnalo
  al coordinatore e non apro una voce.

**Z-28** (`3a3d5ab1c`), il mio pezzo: `_exclusive_run` in `db/post_migration/__init__.py`.
- `os.open(…, O_RDWR | O_CREAT | O_NOFOLLOW, 0o600)`:
  - un link, pendente o no, dà `OSError` prima che si apra il database;
  - dietro un link pendente non si crea nulla;
  - il file nuovo nasce `0600`, e un lock già esistente tiene il suo modo (la doc lo dice: «when missing»);
  - il descrittore si chiude sempre e il `flock` si rilascia nel `finally`;
  - senza POSIX esce prima (`fcntl is None`): `getattr(os, "O_NOFOLLOW", 0)` non serve lì, ma non nuoce.
- Le due frasi della doc sono vere:
  - all'avvio `run_post_migration_fixes_at_startup` (`database_bootstrap.py`, mio) prende ogni `Exception` e scrive
    il WARNING «Post-migration fixes could not run; starting normally»;
  - lo script offline (`__main__.py`, riga 36) chiama fuori da ogni `try`: traceback, uscita 1.
- `O_RDWR` vuole il permesso di scrittura come prima l'`"a+"`: nessuna regressione.
- Verde sul HEAD unito: `db post-migration` 44.

**Via del coordinatore** (17/10, ~12:00): «OK, go», con la guardia del 304 dentro; CHANGELOG 🔒 breve, sì.

1. ✅ **Rossi** (test-author, che non ha lanciato nulla), in `test_managed_headers.py`, 99 casi nuovi:
   - (g) esteso: 11 risposte tipizzate nuove nei 6 modi:
     - 8 documenti: XHTML, SVG anche con `charset` e in maiuscolo, `application/xml`, `text/xml`, Atom, RSS con
       `charset`;
     - 3 no: `application/problem+json`, `text/plain`, `text/htmlx`;
   - il pin di `DOCUMENT_MEDIA_TYPES` e del suffisso, letti con `getattr`;
   - il report-only resta su `text/html` esatto: SVG, XHTML e `text/htmlx` su un percorso della web app;
   - il 304 col middleware da solo, in 4 forme per 6 modi: senza `Content-Type`, HTML, con la CSP della rotta, con il
     report-only della rotta. Prima una barriera a 200;
   - un 304 vero da `ImmutableStaticFiles`, di un chunk JS e di un SVG aggiunto alla build finta
     (`_app/immutable/assets/logo.a1b2.svg`), con le barriere su 304, ETag e `Cache-Control`.
2. ✅ **Run** (`files/runs/h45-backend.sh`, cancello del carico, nessuno slot):

   | Passo | Esito |
   |---|---|
   | rosso `services managed-headers` | **34 failed / 321 passed**, come previsto: 18 (g), 1 pin, 4 report-only, 9 sul 304, 2 sul 304 vero |
   | cura `files/h45/apply.py --apply` | i tre file identici alle copie di prova |
   | verde `managed-headers` | **355** |
   | `security-headers` | 15 |
   | `config-env-example` | 38 |
   | `config-package` | 864 |

   - ruff e black puliti sui 3 file Python; porta libera.
   - La cura, in `security_headers.py`:
     - `DOCUMENT_MEDIA_TYPES` e `DOCUMENT_MEDIA_TYPE_SUFFIX`;
     - `_media_type()`: il primo `content-type`, prima del `;`, senza spazi, minuscolo, decodificato latin-1;
     - `_is_document()`; `_is_html()` esatto;
     - `self.not_modified_headers`: un 304 riceve gli header senza CSP, e nessun report-only;
     - più la docstring del modulo.
   - I commenti di `LIBREFOLIO_FRAME_PROTECTION` in `config/__init__.py` e in `.env.example`.
3. ✅ **Documenti** (docs-writer, solo inglese, nessun timbro):
   - `security.md#managed-headers`:
     - la tabella (documenti; il 304);
     - «Frame protection», con `_media_type`, `_is_document` e `_is_html`;
     - «Why documents only», con ciò che si serve oggi;
     - un punto nuovo «No policy on a `304`», con la sonda;
     - «Where the report-only policy goes»;
     - i test.
   - `configuration.en.md`, la riga di `LIBREFOLIO_FRAME_PROTECTION`: anche SVG e XML, e la nota del 304. Debito di
     traduzione per H-5.
   - `hosting_providers.en.md`: la nota del 304.
   - Controlli (`files/runs/h45-docs.sh`): `mkdocs build` stretto pulito, 97 link validi, Prettier pulito sullo spec,
     `git diff --check` pulito.
4. ✅ **Lo spec di H-42**: solo il commento di `isHtml`. Prima diceva «la regola del server», ma da H-45 il server dà
   `PAGE_POLICY` a ogni documento (`_is_document`). Il codice resta com'è, perché ogni flusso dello spec apre solo
   pagine HTML: lo slot non serve.
   > **⚠️ Fuori pista** (dal docs-writer, verificato): `FileResponse` di Starlette 1.6 non risponde «sempre 200». A un
   > `Range` risponde 206 (`multipart/byteranges` per più intervalli), 416 o 400, e rispetta `If-Range`. **Non risponde
   > mai 304**, che è il punto. Corretti la docstring della cura (prima di applicarla) e questa analisi.
   > - Un 206 con più intervalli prende `frame-ancestors 'self'` da solo, ma i browser non chiedono intervalli di un
   >   documento: nessuna guardia, una nota sola.
   > - `/mkdocs/sitemap.xml.gz` esce come `text/xml`: per `mimetypes` il `.gz` è una codifica, e `FileResponse` tiene
   >   solo il tipo. Con H-45 prende `PAGE_POLICY`: innocuo, ed è documentato.

### Lotto «H-49 e H-48: il lane id nei limiti della sonda; i link tengono la barra finale» (2026-10-17) — H-49 ✅ provato, H-48 rimandato

> Dal coordinatore (17/10, dopo H-45): due voci piccole insieme, se costano poco.
> - Il lane id di almeno 16 caratteri in `platform.test_mode`: è la nota di E su H-46; diventa **H-49**.
> - La barra finale di `env_url` sui link: **H-48**.

**Analisi** (sola lettura, HEAD `77e9611e0`):
- **H-49**:
  - il runner crea il lane id con `secrets.token_hex(16)`, cioè 32 caratteri (`ensure_test_lane_id`,
    `scripts/cli_base.py`);
  - la sonda di prontezza accetta un token da 16 a 128 caratteri (`Query(min_length=16, max_length=128)`,
    `api/v1/system/health.py`);
  - oggi H-46 conta come corsia ogni lane id non bianco: uno di 3 caratteri passerebbe, ma nessun runner potrebbe
    usarlo.
- **H-48**:
  - `env_url` toglie una barra finale («so a path can be appended»). Serve solo a `LIBREFOLIO_PUBLIC_URL` (A, base
    dei link delle email);
  - i quattro lettori di link: `support_url` (H), `tos_url` e `privacy_url` (A9, nel mio `config/platform.py`),
    `billing_url` (A, `config/accounts.py`);
  - i test che fissano il taglio:
    - `test_legal_links.py` (A): le righe `stripped-without-its-trailing-slash` e `ipv4-with-a-port`, più il confronto
      con `env_url`;
    - `test_instance_block.py` (mio, CP6): la riga `https-one-trailing-slash-removed` di `LIBREFOLIO_BILLING_URL`;
  - la doc: `architecture/settings.md` riga ~141 (la regola) e `hosting_providers.en.md` riga ~637 (TOS e privacy).

**Proposta**:
- **H-49**:
  - `TEST_LANE_ID_MIN_LENGTH = 16` e `TEST_LANE_ID_MAX_LENGTH = 128` in `config/platform.py`, accanto a
    `owning_test_lane_id()`. Li usano la sonda (`health.py`, gli stessi valori: OpenAPI invariata, la rotta è fuori
    dallo schema) e `_test_mode_outside_a_lane()`;
  - è una corsia un lane id che, tolti gli spazi, sta fra 16 e 128 caratteri: quello che la sonda accetterebbe.
    Fuori da quei limiti è «fuori corsia»: `error`, e nel profilo managed lo stop.
- **H-48**:
  - `env_link(name)` in `config/__init__.py`: la stessa regola di `env_url` (`http(s)`, host, niente credenziali né
    spazi), ma l'indirizzo resta com'è scritto, tolti solo gli spazi intorno. `env_url` resta com'è per le basi;
  - `support_url`, `tos_url`, `privacy_url` e `billing_url` passano a `env_link`. `public_url` resta su `env_url`.
- **Test** (test-author):
  - H-49 in `test_config_audit.py`;
  - H-48 in `test_config_package.py` (`env_link` e il supporto) e in `test_instance_block.py` (la fatturazione);
  - in `test_legal_links.py`, le due righe e il confronto con `env_link`, con l'OK di A.
- **Doc**: `security.md` (la regola della corsia di H-46), `architecture/settings.md` (`env_link`),
  `hosting_providers.en.md` (TOS e privacy).
- **Selettori**: `services config-audit`, `config-package`, `legal-links`, `config-env-example`, `api instance-block`
  (vuole un server di corsia? da verificare). Altrimenti tutti puri.
- **Serve**: l'OK di scrittura di A su `config/accounts.py` (una riga in `billing_url`) e su `test_legal_links.py`.

**Via del coordinatore** (~12:55): un lotto solo, con l'OK di scrittura di A su `config/accounts.py` (`billing_url`) e su
`test_legal_links.py` (le due righe e `env_link`), e uno slot di ~3 min per `api instance-block`.

1. ✅ **Rossi** (test-author, che non ha lanciato nulla):
   - H-49: la sezione nuova (i) di `test_config_audit.py`:
     - il pin dei due limiti;
     - la sonda che usa gli stessi limiti, letta dai metadati di `Query`;
     - gli id di 15 e 129 caratteri, e uno di 15 con spazi intorno: errore e stop managed;
     - gli id di 16 e 128 caratteri, e uno di 16 con spazi intorno: corsia.
   - H-48: in `test_config_package.py`, `test_instance_block.py` e `test_legal_links.py`.
   > **⚠️ Fuori pista: H-48 non era piccolo.** Dalla test-author: la cura avrebbe fatto diventare rossi altri 9 test,
   > fuori dall'OK:
   > - di A: 2 in `test_legal_links.py`, 2 in `test_instance_config_legal_api.py` (`api instance-legal`) e 4 in
   >   `test_registration_service.py`;
   > - mio: 1 in `test_system_api.py` (`api system`).
   >
   > Più uno slot di ~8 min. **Decisione del coordinatore** (~13:00, la mia strada 2): H-49 da solo ora, H-48 dopo la
   > 1.3, con l'elenco dei test nella sua riga del backlog.
   > - Il lavoro in corso di H-48 (486 righe: i test, la doc e `apply_h48.py`) è salvato fuori dal repo, in
   >   `files/h48-wip/`.
   > - I 5 file sono tornati come in HEAD con `git show HEAD:<file> > <file>`, solo git in lettura: `test_config_package.py`,
   >   `test_instance_block.py`, `test_legal_links.py` di A (toccato solo da me, sotto l'OK), `architecture/settings.md` e
   >   `hosting_providers.en.md`.
   > - La cura è stata divisa in `apply_h49.py` e `apply_h48.py`.
   > **⚠️ Fuori pista: il messaggio dello stop managed** diceva «(no LIBREFOLIO_TEST_LANE_ID)», falso per un id presente
   > ma fuori dai limiti. Ora dice «(no LIBREFOLIO_TEST_LANE_ID of 16 to 128 characters)», costruito dalle costanti.
   > Aggiornati il pin `MANAGED_TEST_MODE_STOP`, `security.md`, `hosting_providers.en.md` e `configuration.en.md`
   > (debito per H-5).
2. ✅ **Run H-49** (`files/runs/h49-run.sh`, cancello del carico, nessuno slot):

   | Passo | Esito |
   |---|---|
   | rosso `services config-audit` | **15 failed / 205 passed**: i 10 di (i), più i 5 stop di H-46 che fissano il messaggio |
   | cura `files/h49/apply_h49.py --apply` | i tre file uguali alle copie di prova; `config/__init__.py` e `accounts.py` riscritti identici, verificato con `git diff` |
   | verde `config-audit` | **220** |
   | `config-package` | 866 |
   | `config-env-example` | 38 |

   - ruff pulito. black voleva andare a capo nel `raise` dello stop (più di 300 caratteri): applicato `black` al file,
     poi ruff e black puliti e `config-audit` di nuovo **220**. Porta libera.
   - La cura:
     - `TEST_LANE_ID_MIN_LENGTH` e `TEST_LANE_ID_MAX_LENGTH` in `config/platform.py`;
     - la sonda di `health.py` li usa: gli stessi valori, quindi niente cambia per la sonda;
     - `_test_mode_outside_a_lane()`, l'id senza spazi fra i due limiti;
     - la docstring di `check_test_mode`;
     - il messaggio dello stop.
3. ✅ **Documenti** (miei, solo inglese, nessun timbro): `security.md` (la riga, il paragrafo della corsia, le sezioni
   (h) e (i), il messaggio), `hosting_providers.en.md` e `configuration.en.md` (il messaggio).
- Note della test-author, nessuna azione:
  - la sonda confronta il token grezzo, il controllo lo prende senza spazi;
  - `ensure_test_lane_id()` tiene un id ereditato di qualsiasi lunghezza (in `scripts/cli_base.py`, condiviso), ma uno
    fuori dai limiti fa fallire la sonda.

### La nota in `settings.md` dopo B-35, la clausola di `--instance-key-file`, la review di B-35 (2026-10-17, 13:15) — ✅

> Dal coordinatore (dopo l'ingresso di H-49, dev `96da36422`):
> - una frase in `developer/architecture/settings.md` (la voce del limite di upload nel profilo managed);
> - la review dopo l'ingresso del lettore di B-35 e della sua modifica alla mappa degli id nel mio
>   `test_config_audit.py`;
> - facoltativa: una clausola in `configuration.en.md` «Saved Secrets and the Instance Key» che rimandi a
>   `--instance-key-file` (B-18).
>
> La richiesta di review di B-18 è arrivata una seconda volta, uguale. B-18 è già entrato (`5c4d7456a`). La mia review
> delle 10:55 vale ancora: il LOW-1 e i due appunti sono la voce B-34 di B, e i cambi successivi sulle mie superfici
> (`max_unpacked` di B-35 in `staging.py`, `_restore_limit` nella CLI) non toccano la strada della chiave d'istanza.

- **Review di B-35** (`32739feaa`): OK.
  - `backup_max_restore_mb()` (`config/backup.py`):
    - non impostato: `0` in `selfhosted`, come prima della 1.3; altrove `RESTORE_TO_UPLOAD_RATIO` (8) volte
      `backup_max_upload_mb()`, quindi 4000 MB in `managed`;
    - fallisce chiuso con gli errori di quel lettore; un valore esplicito vince sempre;
    - la CLI e `check_restore_limit` prendono gli stessi errori;
    - da sapere: in `managed`, un `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB=0` esplicito toglie anche il limite del restore, se
      questo non è impostato. B lo scrive nella docstring; ora lo dice anche `settings.md`.
  - La mappa degli id nel mio test: l'import e `check_restore_limit: "backup.restore_limit"` dopo l'upload, nell'ordine
    di `CONFIG_CHECKS`. I test della tupla leggono `BACKUP_CONFIG_CHECKS`, quindi prendono da sé il terzo controllo.
  - **Reperto mio, corretto**: `_configure` toglieva il token e il limite di upload di B, ma non
    `LIBREFOLIO_BACKUP_MAX_RESTORE_MB`. Un valore rimasto nell'ambiente, fuori dal runner (che lo toglie già), avrebbe
    reso rosso `backup.restore_limit` nei casi «tutto ok». Aggiunto, con il commento «three checks».
- **Doc** (mia, solo inglese, nessun timbro):
  - `architecture/settings.md`, dopo la voce del limite di upload: la frase di B-35;
  - `configuration.en.md`, «Saved Secrets and the Instance Key»: la clausola su `backup restore --instance-key-file`,
    con il link a `cli_tools.md#backup-restore-instance-key`. Debito di traduzione per H-5.
- **Controlli** (`files/runs/b35note.sh`):
  - `services config-audit` 220; ruff e black puliti;
  - `mkdocs build` stretto pulito, 97 link validi, `git diff --check` pulito; porta libera.

### Review allargata di A9 (frontend, test, doc) (2026-10-17, 13:25) — ✅ OK, un appunto

- Verificato:
  - `Header` e `HelpMenu`: le donazioni dentro `{#if donationsVisible()}`, con le classi spostate identiche;
  - `ChangelogModal`: «Check for updates» solo dopo una risposta `selfhosted`; `checkForNewerRelease()` aspetta lo
    store e non fa nessuna richiesta senza quella risposta (`security.md#container-image-check` lo dice, esatto);
  - `ChangelogModal.test.ts`: lo store vero, senza mock del modulo;
  - `Sidebar`: `LegalLinks`; le chiavi `legal.*` nelle 4 lingue, `legal` in `app/prefixes.txt`;
  - `test_system_api.py` (mio): `legal` fra i campi dichiarati;
  - `architecture/settings.md`: cinque campi e i due runner del `legal`.
- **Appunto, fix-forward facoltativo, di A**: la regola `instanceConfig.loaded && profile === 'selfhosted'` è scritta tre
  volte (`donationsVisible()`, `ChangelogModal`, `checkForNewerRelease`). Un helper solo nello store dell'istanza.

### Lotto «X-R62: togliere il provider rifiutato con un 409 se un suo evento ha una transazione collegata» (presa dalla coda di X, 2026-10-17) — analisi

> Dal coordinatore (13:20), con le note di J:
> - «No Provider» (`DELETE /api/v1/assets/provider`, «nessun provider» della modale) cancella l'assegnazione, i cui
>   eventi vanno in CASCADE; una transazione collegata a uno di loro fa fallire il RESTRICT, e la risposta è un 500
>   grezzo con `detail=str(e)`, cioè il testo SQL;
> - succede a ogni piano i cui eventi generati hanno una transazione collegata (un INTEREST su una cedola generata),
>   non solo agli SPLIT.
>
> Cura, come proposta da J: rifiutare **prima** della cancellazione con un 409 con codice, che nomina le righe
> collegate che il chiamante può vedere (lo schema di X-R48/X-R49, la vista del chiamante di `split_guard`), più una
> cattura nel passo 2 di `AssetModal.saveEdit` con una frase tradotta. OK di scrittura sulla logica di
> `AssetModal.svelte` (niente markup né classi). X rivede.

**Analisi** (sola lettura, HEAD `c7f414827`):
1. **Il percorso**:
   - `remove_providers_bulk` (`api/v1/assets/providers.py`, `DELETE ""` con `asset_ids` in query) chiama
     `AssetSourceManager.bulk_remove_providers(asset_ids, session)` e trasforma ogni eccezione in un 500 con
     `detail=str(e)`;
   - `bulk_remove_providers` (`services/assets/provider_management.py`): un solo `DELETE … WHERE asset_id IN (…)`, poi
     il commit. Nessun chiamante passato, nessun controllo;
   - le chiavi (`db/models.py`): `asset_events.provider_assignment_id` → `ON DELETE CASCADE`;
     `transactions.asset_event_id` → `ON DELETE RESTRICT` (r. 964), e SQLite le applica;
   - gli eventi manuali (`provider_assignment_id IS NULL`) non si cancellano, quindi non bloccano.
2. **L'asimmetria da dire a X**: cambiare provider (Policy D, R3-3, `bulk_assign_providers` r. ~215-245)
   **scollega** le transazioni (`SET asset_event_id = NULL`) e cancella gli eventi; rifiuta solo il caso di X-R49
   (SPLIT con rettifiche senza costo). Togliere il provider, con la cura decisa, **rifiuta**. È la decisione del
   coordinatore e di J; X può chiedere la simmetria più avanti.
3. **Il modello da seguire**, X-R49 (`589f15607`):
   - la guardia prima di ogni scrittura: `AssetSourceError(message, code, details)`;
   - la rotta: 409 con `detail = {"error_code", "message", "params": jsonable_encoder(details)}`;
   - la vista del chiamante (`split_guard.py`): gli id delle transazioni su un broker con un `BrokerUserAccess` del
     chiamante, gli altri contati; senza chiamante nessuno è nominato;
   - il frontend: `currencyChangeErrors.ts` (`wipeRefusalMessage`, codice → chiave, `params.splits`) e la cattura nel
     ramo di assegnazione di `saveEdit`.
4. **Il frontend**:
   - l'unico chiamante della rimozione è `AssetModal.svelte` r. ~1387 (passo 2, `providerNoProvider`), senza `try`:
     l'errore risale e la modale mostra la frase generica;
   - il ramo di assegnazione, subito sotto, prende già il 409 di X-R49 con `wipeRefusalMessage`.
5. **I test di X-R49**: `test_services/test_provider_wipe_split_guard.py` (`services provider-wipe-split-guard`,
   scritture con nomi unici, la rotta in processo con `ASGITransport`). Niente slot.
6. **La doc di X-R49**: `developer/backend/assets/events.md` (r. ~317-337) e `architecture.md` (la tabella delle
   rotte, r. ~608).

**Proposta**:
- **Backend** (file di X):
  - un modulo nuovo, `services/assets/event_links.py`:
    - `visible_transaction_ids(session, ids, current_user_id)`: la regola della vista del chiamante (R13-SEC7), che oggi
      sta dentro `split_guard.py` e che `split_guard` importerà: cambiano 3 righe, con lo stesso comportamento, che i
      test di X-R49 sorvegliano;
    - `events_with_linked_transactions(session, events, current_user_id)`: gli eventi con almeno una transazione
      collegata, per (data, id). Ciascuno `{"event_id", "date", "type", "transaction_ids", "hidden_transactions_count"}`;
  - `bulk_remove_providers(asset_ids, session, *, current_user_id=None)`:
    - prima del `DELETE`, nell'ordine della richiesta, per l'assegnazione di ogni asset: gli eventi generati che hanno
      una transazione collegata;
    - al primo asset che ne ha, `AssetSourceError` con il codice **`PROVIDER_REMOVAL_LINKED_TRANSACTIONS`**, `details`
      `{"asset_id", "item_index", "events": [...]}`, e un messaggio che dà solo i totali;
    - niente si scrive, neanche per gli asset prima di quello;
  - la rotta passa `current_user_id` e risponde 409 con `{error_code, message, params}`; tutto il resto come oggi, e
    la docstring lo documenta.
- **Frontend**:
  - `currencyChangeErrors.ts`, il modulo dei rifiuti dei wipe: il codice nuovo dà la chiave
    `assets.modal.providerRemovalLinkedTransactions`, letta da `params.events`. I valori: il tipo del primo evento
    (`assetDetail.eventType.<TYPE>`, prefisso dinamico protetto), la data, quante transazioni ha e quante non si
    vedono, quanti altri eventi;
  - `AssetModal.svelte`, passo 2: un `try` attorno alla rimozione. Un rifiuto va in `formError`, la modale resta
    aperta come nel ramo di assegnazione; ogni altro errore risale. Solo logica;
  - i18n: una chiave nelle 4 lingue (sottosistema `assets`).
- **Test** (test-author):
  - backend, un file nuovo `test_services/test_provider_removal_link_guard.py` (come quello di X-R49):
    - un evento del provider con una transazione collegata (dividendo); una cedola del piano con un INTEREST (il caso
      di J); uno SPLIT;
    - la vista del chiamante; due asset, il secondo bloccato: nessuno dei due rimosso, `item_index` 1;
    - nessun collegamento: la rimozione passa e gli eventi vanno in cascata;
    - un evento manuale collegato non blocca;
    - il 409 della rotta, esatto, senza testo SQL;
  - frontend: casi in `currencyChangeErrors.test.ts` e in `AssetModal.providerLifecycle.test.ts`.
- **Doc** (docs-writer): `developer/backend/assets/events.md`, accanto a X-R49, e la riga del `DELETE` in
  `architecture.md`.
- **CHANGELOG** 🐛: «Removing an asset's provider no longer ends in a server error when an event it generated is
  linked to a transaction: it is refused, naming the transactions.»
- **Selettori** (nessuno slot):
  - `services provider-removal-link-guard` (nuovo) e `provider-wipe-split-guard` (X-R49, per lo spostamento della
    vista);
  - Vitest dei due file;
  - `utils gate-i18n-catalog` e `gate-i18n-usage`;
  - `front check`.
- **Residuo**: una transazione collegata fra la guardia e il `DELETE` darebbe ancora il 500, ed è raro. Facoltativo:
  prendere anche l'`IntegrityError` della cancellazione come 409 generico.
- **Da confermare**:
  - l'OK di scrittura sui file di X: `providers.py`, `provider_management.py`, `split_guard.py` (3 righe), il modulo
    nuovo, `currencyChangeErrors.ts` e i due test del frontend;
  - un `add_test` nel runner (`_backend_services.py`, accanto a `provider-wipe-split-guard`);
  - la doc di X.

> **Conferme del coordinatore** (13:35):
> 1. OK di scrittura sui file di X elencati: il lavoro aperto di X (X-R60) non ne tocca nessuno;
> 2. l'`add_test` in `_backend_services.py`, accanto a `provider-wipe-split-guard`;
> 3. sì: l'`IntegrityError` della cancellazione diventa un 409 generico con codice, **`PROVIDER_REMOVAL_CONFLICT`**,
>    senza SQL nel corpo.
>
> L'asimmetria (cambiare scollega, togliere rifiuta) va nel checkpoint come nota per X.

**Passi**:

1. ✅ (2026-10-17, 13:56) **Rossi**: due test-author in parallelo; nessuno ha eseguito nulla.
   - **Backend**: `test_services/test_provider_removal_link_guard.py`, nuovo, 20 casi: 13 rossi e 7 guardie verdi.
     - Riusa i lettori e due barriere di X-R49, importati da `test_provider_wipe_split_guard`: nel repo ci sono 13
       precedenti di import fra moduli di test.
     - Gli asset sono inattivi, così lo scheduler della corsia non li tocca. Le date sono del 1984.
     - Le assegnazioni si riscrivono a ogni test: la tabella non ha AUTOINCREMENT, quindi un id cancellato può tornare.
   - **Frontend**:
     - `currencyChangeErrors.test.ts`: +56 casi. 50 rossi, perché il modulo risponde `null` ai due codici; 17 di
       questi sono di catalogo;
     - `AssetModal.providerLifecycle.test.ts`: +6 casi. 3 rossi, perché il banner dice «nome duplicato»; 3 guardie;
     - fissato dai test:
       - il nome del tipo si chiede per primo, con la sola chiave;
       - un tipo che non è una stringa diventa `''`;
       - il conflitto si chiede senza valori;
       - ogni codice legge la sua lista, `events` o `splits`;
       - la modale passa `(err, $t, iso => formatDay(iso))`, come X-R49.
   - **Runner**: `services provider-removal-link-guard`, WRITE-SCOPED. È stato applicato prima dei rossi
     (`files/xr62/apply_runner.py`, `cmp` OK).
   - **Evidenza** (`files/runs/xr62-reds.sh`):
     - Prettier, ruff e black puliti sui test e sul runner;
     - services: 13 failed, 7 passed. Tutti FAILED con il messaggio «oggi», nessun ERROR;
     - Vitest: 50 failed / 84 passed e 3 failed / 50 passed;
     - esattamente le previsioni dei test-author.
   > **Note implementazione**: le osservazioni dei test-author da riportare nel checkpoint.
   > - SQLite fa scattare il RESTRICT già sul `DELETE`: il ramo «fallisce il commit» qui non si raggiunge.
   > - Il messaggio conta solo gli eventi collegati; quelli non collegati vanno comunque in cascata.
   > - Un 409 non riconosciuto sulla rimozione si legge ancora «nome duplicato», come oggi.

2. ✅ (2026-10-17, 14:06) **Cura e verdi**.
   - **Applicazione**: `files/xr62/apply_backend.py` e `apply_frontend.py`, prima a secco poi `--apply`; `cmp` OK sui
     6 file. Poi `files/xr62/i18n.sh`: due chiavi in `assets/<lang>.json`, nelle 4 lingue; `i18n check` stretto.
   - **Backend**:
     - `services/assets/event_links.py`, nuovo: `visible_transaction_ids` (la regola di R13-SEC7, tolta da
       `split_guard`) e `events_with_linked_transactions`;
     - `split_guard.py`: importa `visible_transaction_ids`. Cinque righe diventano una, con lo stesso comportamento;
     - `provider_management.py`: `_reject_removals_of_linked_events` prima dell'unica scrittura;
       `bulk_remove_providers(..., *, current_user_id=None)`; l'`IntegrityError` del `DELETE` porta a `rollback`, a un
       avviso nel log del server e a `PROVIDER_REMOVAL_CONFLICT`, senza SQL;
     - `providers.py`: la rotta passa il chiamante e risponde 409 ai due codici; la docstring li documenta.
   - **Frontend**:
     - `currencyChangeErrors.ts`: i due codici in `SENTENCE_KEYS`. La rimozione legge `params.events` e chiede prima il
       nome del tipo; il conflitto si chiede senza valori. X-R48 e X-R49 restano con `{date, n, hidden, more}`;
     - `AssetModal.svelte`, passo 2: un `try/catch` attorno alla rimozione, come il catch di X-R49. Solo logica.
   - **Evidenza** (`files/runs/xr62-greens.sh`, poi `xr62-sync.sh`):
     - ruff, black e Prettier puliti (Prettier anche sui 4 sorgenti i18n);
     - services: `provider-removal-link-guard` 20 passed, `provider-wipe-split-guard` 12, `market-data-wipe-split-guard`
       13, `asset-source` 61;
     - Vitest: `currencyChangeErrors` 134, `AssetModal.providerLifecycle` 53, `AssetModal` 42,
       `AssetCurrencyChangeModal` 23, `currencyBlocker` 7;
     - gate: `gate-i18n-catalog` 176, `gate-i18n-usage` 195;
     - `front check`: 0 errori dopo `api sync`.
   - **Non eseguiti** (serve uno slot): `api assets-provider` e `api assets-crud`. Tolgono un'assegnazione senza
     transazioni collegate, il caso coperto dalle guardie di rotta del test nuovo.
   > **⚠️ Fuori pista**: il primo `front check` ha dato 2 errori in `features/legal/` (A): `legal` mancava in
   > `InstanceConfigResponse`. Il client generato, ignorato da git, era delle 10:20, prima del fast-forward che ha portato
   > il campo di A9. `api sync` lo ha rigenerato, senza toccare file tracciati; il secondo `front check` dà 0 errori. Non
   > è un difetto del prodotto.

3. ✅ (2026-10-17, 14:11) **Doc** (docs-writer, solo lettura e scrittura del Markdown; build e link li ho fatti io).
   - `developer/backend/assets/events.md`: la sezione nuova «🗑️ Provider Removal» (`#provider-removal`), dopo X-R49:
     - cosa cancella il `DELETE`, e il 500 di prima;
     - il controllo, il 409, la vista del chiamante, il conflitto;
     - l'asimmetria, detta come decisione;
     - il frontend e i test;
     - in più, un paragrafo in «Auto-Generated Events».
   - `architecture.md`:
     - la riga del `DELETE` nella tabella delle rotte;
     - nella tabella dei moduli, la riga di `provider_management.py` e una riga nuova per `event_links.py`.
   - Verificato da me sul testo: ogni affermazione corrisponde al codice. docs-writer ha ristretto due punti:
     - l'asimmetria vale per i provider parametrici: un cambio fra provider di mercato non cancella nulla;
     - «Policy D» è tolto, perché nella doc non è definito.
   - **Evidenza** (`files/runs/xr62-docs.sh`): `mkdocs build` stretto rc 0, nessun avviso; `check-links` 97 link
     validi; `git diff --check` pulito.
   > **Note implementazione**: proposte di docs-writer fuori dal mio perimetro, da girare al coordinatore senza
   > modificarle:
   > - `user/assets/create-edit.en.md` dopo r. 180, pagina tradotta;
   > - `developer/backend/transactions/wac.md` r. 602-617, una frase;
   > - `user/assets/detail/events.en.md` r. 39, facoltativa, tradotta;
   > - `provider_policy.py` manca nella tabella dei moduli. Non riguarda X-R62.

4. ✅ (2026-10-17, 14:12) **Checkpoint**.
   - Previsione di merge con `dev_release2` (`f078b766c`): tre file cambiati anche su dev, `providers.py` (MF-SI2,
     il limite delle sonde), `_backend_services.py` e `architecture.md`. `git merge-file` dà 0 conflitti, anche dopo la
     doc. Dev non ha toccato gli helper di X-R49 che il test nuovo importa.
   - Commit proposti:
     - `fix(assets): coded 409 on linked provider removal`: codice, test, i18n, runner;
     - `docs(assets): X-R62 provider removal refusal`: MkDocs e piano.
   - CHANGELOG 🐛, proposta: «Removing an asset's provider (No Provider) no longer fails with a server error showing
     database text when a transaction is linked to an event the provider generated: the removal is refused, and the
     form names the event and how many transactions to unlink first.»
   - Nota per X: cambiare un piano scollega le transazioni, togliere il provider le rifiuta. X può chiedere la simmetria.
   - La riga X-R62 sta nella sezione di X del backlog: la chiude il coordinatore.

### Review di B-36/B-37 (`2eff9e623`, in dev `d1976bca8`) (2026-10-17, 14:40) — ✅ OK, un appunto di testo, un nit, un residuo (→ H-51)

Fatta durante W-B75, su richiesta del coordinatore. Sola lettura; sonde su file temporanei in `files/b36review/`.

- **B-36**: `_quoted` è corretto (doppi apici, con quelli interni raddoppiati). In `post_migration` è l'unico nome che
  arriva dal `sqlite_master` dell'archivio dentro un SQL; `autoincrement.py` interpola solo nomi della tupla fissa
  `AUTOINCREMENT_TABLES`.
  - Nit, per B: due `_quoted` con contratti diversi. `snapshot._quoted` non mette gli apici esterni,
    `post_migration._quoted` sì.
- **B-37**:
  - il PRAGMA è la prima istruzione dopo il connect;
  - la connessione di `_backup` è solo la destinazione della backup API;
  - il listener di `env.py` è registrato prima del primo connect, solo su quel motore, e con `NullPool` vale per ogni
    connessione; la modalità offline non ne apre.
- **Sonde**:
  - SQLAlchemy 2.0.52 registra `regexp` e `floor` in Python su ogni connessione;
  - `trusted_schema` vale 1 di default;
  - prima di B-37, il `regexp` gira da un CHECK dell'archivio;
  - con il listener, ogni istruzione fallisce («malformed database schema … unsafe use of REGEXP()»);
  - la head 009 usa solo `lower()`.
- **Appunto di testo**, per B: la frase «nessuna funzione dell'app è registrata lì» non vale per il motore di Alembic.
  Il listener di `env.py` è quindi una cura vera.
- **Residuo → H-51**: il motore del server vivo ha `trusted_schema` a 1 e i due Python. Un archivio con
  `DEFAULT (regexp(…))` passa il controllo del ripristino (`integrity_check` `ok`; un CHECK invece fallisce, «unknown
  function»). Nel server, a ogni insert che omette quella colonna, gira il `regexp` Python; lo prova anche il motore
  async.
- **Decisioni del coordinatore** (14:45):
  - H-51 è un lotto mio, dopo W-B75, con la riscrittura della frase di `security.md` r.706 (B-18) e la frase su Alembic;
  - nello slot di verifica, le suite delle migrazioni e `api backup-restore`;
  - l'appunto di testo e il nit li passa lui a B.

### Lotto «W-B75: l'errore di campo di un plugin BRIM non rende più il parse non serializzabile» (dalla coda di W, 2026-10-17) — analisi e passi

> Dal coordinatore (14:20), dopo l'entrata di X-R62 (dev `0c035651e`):
> - BRIM `_create_transaction` copia in `params` il contesto di ogni errore singolo, quindi l'oggetto eccezione di un
>   `value_error` renderebbe la risposta del parse un 500;
> - cura come `_lone_error_params` di W-B72: solo il contesto fatto di dati semplici, `None` per gli errori di campo e
>   per `value_error`. Un rosso con un `value_error` forzato.
>
> Analisi prima solo se il lavoro tocca più dei percorsi di creazione di `brim`. W rivede.

**Analisi** (sola lettura, HEAD `0c035651e`):
1. **Un solo punto**: BRIM costruisce issue da errori pydantic solo in `BRIMProvider._create_transaction`
   (`services/brim/brim_provider.py`).
   - Il ramo dell'errore singolo passa `params=err_ctx` così com'è.
   - I sotto-errori di `multipleBusinessRuleErrors` e il ramo `unexpected_error` non c'entrano.
2. **I `value_error` raggiungibili**: `Currency.amount` (`check_decimal_exponent`, R13-SEC7-3, e «Cannot convert»),
   `Currency.code`, i `tags`.
   - Si raggiungono solo quando un plugin passa un dict invece di un'istanza di `Currency`.
   - Oggi i plugin passano istanze, che non si rivalidano: il difetto è latente.
3. **La regola esatta di W-B72** («`None` per gli errori di campo») in BRIM oggi non cambia nulla di visibile:
   - `ParseDetailModal.svelte` risolve con `resolveIssueMessage({code, params, error})`, senza `field`;
   - i soli messaggi che leggono i `params` di un errore di campo sono `transactions.pydantic.{greaterThan,
     greaterThanEqual, lessThan, lessThanEqual}` (`{gt}`…), e nessun campo di `TXCreateItem` o di `Currency` ha
     `gt/ge/lt/le`;
   - gli altri errori di campo raggiungibili non hanno chiave, e si mostra il loro inglese, che ha già il numero:
     `string_too_long` di `description` e `link_uuid`, `literal_error` di `cost_basis_mode`, `enum` di `type`;
   - ogni contesto delle regole di business è fatto di dati semplici (`{type}`, `{type, qty: str}`,
     `{type, allowed}`, `{broker_id}`): un errore singolo tiene i suoi `params`.
4. **Nota per W** (latente; riguarda il batch, ed era così già prima di W-B72, quando si passava `params=None`): con
   la stessa regola, un `greater_than` di campo del batch arriva senza `{gt}`, e `transactions.pydantic.greaterThan`
   lo mostrerebbe grezzo. Succede con `id_a` o `from_tx_id` = 0 in uno split o in una promozione. Si raggiunge solo
   via API.

**Proposta**:
- `BRIMProvider._lone_error_params(err)`, uno staticmethod gemello di `_loc_to_field`, con la regola di W-B72 e
  `_PLAIN_PARAM_TYPES` locali. Il ramo singolo la usa.
- Niente import dal modulo del batch, che è privato e di un altro dominio. Restano due copie piccole e allineate,
  come già per `_loc_to_field`; unificarle è un riordino a parte, da concordare con W.
- **Test** (test-author) nel file esistente `test_services/test_brim_create_transaction.py`
  (`services brim-create-transaction`):
  - rossi: un `value_error` forzato sul plugin finto; un errore di campo con un contesto semplice;
  - la funzione provata su dict sintetici;
  - guardie: la regola singola e i sotto-errori tengono il loro contesto.
- **Doc**: una frase nella riga di `_create_transaction` di `brim_plugin_guide.md`.
- Nessuna API, nessuna i18n, nessuno slot.

**Passi**:

1. ✅ (2026-10-17, 14:35) **Rossi** (test-author, nessuna esecuzione): +18 test in `test_brim_create_transaction.py`.
   - `TestCreateTransactionIssueParams`:
     - un `value_error` forzato da tre fonti: l'esponente di `cash.amount`, il codice vuoto di `cash.code`, `tags` in
       una tupla. Ogni caso ha un solo issue, `params is None` e quattro serializzazioni (`model_dump(mode="json")`,
       `model_dump_json()`, `BRIMParseOutput`, `BRIMParseResponse`);
     - `string_too_long` di `description` dà `params is None`;
     - guardie: due regole singole che tengono il loro contesto (`broker_id`; `{type, qty}`) e le regole impacchettate.
   - `TestLoneErrorParams`: 11 casi sulla funzione, con dict sintetici.
   - **Evidenza** (`files/runs/wb75-reds.sh`): ruff e black puliti; `services brim-create-transaction` 15 failed /
     17 passed. Sono esattamente le previsioni, tutti FAILED e nessun ERROR.
   > **⚠️ Fuori pista**: test-author, verificato da me sul codice. Il parse non dà un 500.
   > - `response.model_dump(mode="json")` (`api/v1/brokers.py` r. 1047) sta dentro il `try` della rotta, e
   >   `PydanticSerializationError` è un `ValueError`: si risponde 400, con il testo «Unable to serialize unknown type:
   >   <class 'ValueError'>».
   > - Il file è già passato in `parsed` (r. 1021), e `move_to_failed` sposta solo da `UPLOADED`: il file resta `PARSED`,
   >   senza risultato salvato.
   > - La riga W-B75 della sezione di W dice «un 500»: lo segnalo, non la tocco.
2. ✅ (2026-10-17, 14:37) **Cura, verdi e doc**.
   - Applicata con `files/wb75/apply.py`, prima a secco poi `--apply`; `cmp` OK.
   - `brim_provider.py`:
     - `_PLAIN_PARAM_TYPES` a livello di modulo;
     - `BRIMProvider._lone_error_params`, uno staticmethod con la regola di W-B72;
     - il ramo singolo la usa, e la docstring di `_create_transaction` lo dice;
     - il ramo `multipleBusinessRuleErrors` resta com'era.
   - `brim_plugin_guide.md`: la riga di `_create_transaction` dice cosa porta ogni issue e rimanda a «Per-type rules».
   - **Evidenza** (`files/runs/wb75-greens.sh`):
     - ruff e black puliti;
     - `services brim-create-transaction` 32 passed, `brim-report-sets` 274, `external brim-providers` 736 passed,
       1 skipped. Lo skip è previsto: un campione che Windows-1252 non sa rappresentare;
     - `mkdocs build` stretto senza avvisi; `check-links` 97; `git diff --check` pulito.
3. ✅ (2026-10-17, 14:40) **Checkpoint**.
   - Commit proposti:
     - `fix(brim): plain-data params on lone parse errors` (codice, test, guida);
     - `docs(journal): W-B75, B-36/B-37 review, H-51` (piano e backlog: H-47 con la corsa, H-51).
   - Nessuna voce nel CHANGELOG: il difetto è latente, e oggi nessun plugin lo raggiunge.
   - Note per W:
     1. Ho applicato la regola esatta di W-B72. Oggi non cambia niente di visibile.
     2. La correzione «400, non 500», con lo stato `PARSED` che resta.
     3. Il ramo impacchettato, qui e nel batch, copia il contesto dei sotto-errori senza filtro. È sicuro finché ogni
        regola usa str e int.
     4. Nel batch un `greater_than` di campo arriva senza `{gt}`, già prima di W-B72.
     5. Ci sono due copie della regola, come per `_loc_to_field`: unificarle si fa a parte.

### Review dell'helper di profilo di A (`9db6cb0be`, doc `6700a04b4`; dev `d7641f368`) (2026-10-17, 14:55) — ✅ OK, nessun reperto

Fatta mentre gli specialisti di H-51 lavoravano, in sola lettura. Chiude il mio nit della review di A9: la regola
`loaded && profile === …` scritta a mano in più posti.

- **Semantica**:
  - `loaded` (`instanceConfig.svelte.ts`) diventa vero solo con una risposta riuscita e resta vero se un
    ricaricamento fallisce dopo. Quindi `selfHostedConfirmed()` e `managedConfirmed()` sono falsi finché il server non
    ha risposto;
  - sono reattivi, perché leggono i getter di `$state`.
- **Siti**: 5 sostituzioni meccaniche. `ForgotPasswordCard` tiene la sua alternativa `!loaded && failed`.
- **Gate** (`instanceProfile.gate.test.ts`):
  - lavora sull'albero sintattico (TypeScript e Svelte) e ha controlli positivi;
  - `profile.ts` è l'unico file esente;
  - dichiara i suoi limiti;
  - è registrato in `core-unit`.
- **Doc**: coerente con il codice.
- **Evidenza**: Vitest del gate e di `profile.test.ts` alla HEAD `9ba7ef9d3`: 2 file, 19 passed.

### Review dei doc di A-42/A-43 (`145adbf27`, dev `7156a24af`; seguito A-50 `6700a04b4`) (2026-10-17, 15:45) — ✅ OK, un nit facoltativo

Fatta durante lo slot di H-51, in sola lettura. Riguarda le sezioni di A in `hosting_providers.en.md` (la riga
«withdrawn», «🔁 A New Link», il punto ⏱️) e in `security.md` («♻️ The Setup Link's Lifecycle» e le righe della
Revocation).

- **Verificato sul codice di `59161e5e2`**:
  - revoke e retire: `retire_tokens()` mette `revoked_at` e poi `consumed_at`;
  - l'emissione sotto il lock, con la nuova lettura di `is_pending_admin()`, il rollback e le due righe INFO;
  - la spesa rifiutata: prima `consume_token()`, poi «già attivo» e `_setup_spent_before()`, poi retire e la WARNING,
    tutto prima di bcrypt;
  - `_end_setup_links()`: revoca per l'admin in attesa, con la WARNING, retire per gli altri;
  - i 409 `PENDING_SETUP` e `ACCOUNT_PROTECTED`;
  - `account_tokens.user_id` è `ON DELETE CASCADE`.
- Gli ID dei test e le ancore esistono. La WARNING «was withdrawn (cancelled, or its address changed)» citata nella
  pagina per i provider è identica a quella del codice (`bootstrap_admin_service.py:205`).
- **Nit**: «Another administrator … can do the same with **Cancel setup link**» non vale per un account protetto, cioè
  l'amministratore che paga un'istanza gestita. La pagina linkata lo dice, e la CLI resta sopra la protezione.

### Lotto «H-51: `trusted_schema` spento anche sui motori del server; la chiave d'istanza nel ripristino, com'è dopo B-18» (2026-10-17) — analisi e passi

> Dal coordinatore (14:45, dopo la review di B-36/B-37), testuale:
> - «`trusted_schema=OFF` nel listener globale di `db/session.py`: lo prendi tu, come lotto H. Rossi prima: l'archivio
>   con `DEFAULT (regexp(…))` fa girare il `regexp` al primo insert. Nel tuo slot di verifica metti anche le suite delle
>   migrazioni e `api backup-restore`, oltre ai tuoi test.»
> - «`security.md`, r.706: la frase è superata, B-18 è entrato (`5c4d7456a`). Riscrivila col percorso vero»:
>   - `dev.py backup restore --instance-key-file FILE`, solo da CLI, mai con un upload dalla UI;
>   - il file è letto da root prima del cambio di utente (B-38);
>   - `stage_archive(..., instance_key=…)` lo controlla prima di creare qualsiasi cosa (`instance_key_invalid`);
>   - se l'archivio porta la sua chiave, vince quella (D1).
>   Nello stesso lotto va la frase sul motore di Alembic.
>
> W-B75 è entrato (`21a2610c8`, dev `9ba7ef9d3`): parto da lì.

**Analisi** (HEAD `9ba7ef9d3`):
- `set_sqlite_pragma()` (`db/session.py`) è un listener `connect` sulla classe `Engine`, quindi vale per ogni motore
  sincrono del processo, compreso quello sotto il motore async. Imposta `foreign_keys`, WAL e `busy_timeout`, ma non
  `trusted_schema`, che vale 1 di default.
- SQLAlchemy 2.0.52 (pysqlite, ereditato da aiosqlite) registra `regexp` e `floor` in Python su ogni connessione.
- L'app non usa `regexp`, `floor` né `create_function` nelle sue query. In ogni caso `trusted_schema` limita solo le
  chiamate che vengono dallo schema.
- Lo schema di LibreFolio (head 009) chiama solo il built-in `lower()` (`ux_users_email_lower`).
- Le prove sono le sonde della review di B-37 (`files/b36review/`).

**Proposta**:
- **Cura**: `PRAGMA trusted_schema=OFF` come prima istruzione di `set_sqlite_pragma()`, con una voce nella sua
  docstring.
- **Test** (test-author): un file nuovo, `test_db/test_session_pragmas.py`, `db session-pragmas`, isolamento pure.
  - Rossi:
    - ogni connessione nuova, sincrona e async, ha `trusted_schema` a 0;
    - un archivio con `DEFAULT (regexp(…))`: l'insert che omette la colonna è rifiutato, e non gira il Python;
    - un CHECK con `regexp`;
    - `floor`.
  - Guardie: gli altri pragma restano come sono; il genere dello schema di LibreFolio (`lower()` in un indice, i
    built-in) funziona; `regexp` e `floor` funzionano ancora nelle query.
- **Runner**: in `_backend_db.py`, la funzione, l'`add_test` e la voce in `db_order`.
- **Doc** (docs-writer):
  - `security.md`: la frase della chiave d'istanza nel ripristino (r. ~706); il punto di B-37 con Alembic e il server;
  - `database/index.md`: r. 52, i pragma del motore.
- **Verifica**:
  - senza slot: `db session-pragmas`, `db migration-005…009`, `db post-migration`, `db autoincrement-schema`,
    `utils dev-cli-db-path`, `services backup-staging`;
  - nello slot: `api backup-restore`.

**Passi**:

1. ✅ (2026-10-17, 15:05) **Runner e doc**.
   - **Runner**: `files/h51/apply.py --runner-only`, `cmp` OK. In `_backend_db.py`: `db_session_pragmas`, l'`add_test`
     «session-pragmas» (isolamento pure) e la voce in `db_order`.
   - **Doc** (docs-writer), verificata da me sul codice:
     - `security.md`, la chiave d'istanza nel ripristino (r. ~707-731): la frase superata è riscritta con il percorso
       vero (i quattro punti del coordinatore, più D2: una chiave abbastanza lunga ma sbagliata non è un errore e il
       comando avvisa). Anche la frase prima è corretta: senza chiave, dell'archivio o data al ripristino;
     - `security.md`, nel punto di B-37: un nuovo punto «Why the upgrade needs it», sul motore di Alembic;
     - `security.md`: una sottosezione nuova, «`trusted_schema` Off in the Server's Engines» (`#trusted-schema-server`);
     - `database/index.md` r. 53: una voce per il pragma.
   - **Due scoperte di docs-writer**, verificate:
     - `env.py` importa `db.base`, che passa per `db/__init__.py` e importa `session.py`. Quindi nelle connessioni
       dell'upgrade il listener globale girava **prima** di `_schema_untrusted`: «before any other statement» non era
       esatto. Con H-51 diventa vero. Le tre istruzioni di prima non valutano lo schema: nessun effetto.
     - Nota per B (basso): `describe_database()` esegue `PRAGMA integrity_check` su una connessione semplice. Su un
       archivio con un CHECK che chiama una funzione sconosciuta, come `regexp`, alza `sqlite3.OperationalError`
       (provato dalla sonda di B-37). Non è uno `StagingError`: `stage_archive()` ripulisce lo stage e la rilancia.
       L'API dice `stage_failed`; la CLI (`_check_on_a_copy()` prende solo `StagingBusyError`, `StagingError` e
       `BackupPathError`) molto probabilmente finisce in un traceback. Cura di B: tradurre `sqlite3.DatabaseError` in
       `database_damaged`, come fa `_refuse_foreign_objects`.
2. ✅ (2026-10-17, 15:17) **Rossi** (test-author, nessuna esecuzione): `test_db/test_session_pragmas.py`, 15 casi.
   - Rossi, per sync e async:
     - H51-1, `trusted_schema` a 0;
     - H51-2 e H51-3, un `DEFAULT` con `regexp` o con `floor`;
     - H51-4, un CHECK con `regexp`, rifiutato a ogni istruzione.
   - Guardie:
     - H51-5, gli altri pragma;
     - H51-6, il genere dello schema di LibreFolio;
     - H51-7, l'SQL di primo livello;
     - H51-8, un database alla head tramite il motore async.
   - **Evidenza** (`files/runs/h51-reds.sh`): 8 failed / 7 passed, come previsto; ruff e black puliti sul test.
   > **⚠️ Fuori pista**: test-author ha previsto, e una sonda (`files/h51/probe_order.py` / `.out`, tre varianti in
   > processi separati) ha confermato, che la cura come l'avevo scritta non basta per il CHECK.
   > - `set_sqlite_pragma()` è un listener di classe: gira **prima** dell'`on_connect` del dialetto che registra
   >   `regexp` e `floor`.
   > - Il suo `journal_mode=WAL` fa leggere lo schema subito, quando la funzione ancora non esiste. SQLite legge allora un
   >   CHECK o un'espressione d'indice senza segnare la chiamata come dello schema, e poi non la ricontrolla.
   > - Risultati:
   >   - oggi, anche sul motore di Alembic con `_schema_untrusted`, un CHECK o un indice con `regexp` **fanno girare** il
   >     Python; solo il DEFAULT è rifiutato;
   >   - con il solo `trusted_schema=OFF` per primo, lo stesso;
   >   - con `PRAGMA writable_schema=RESET` per ultimo, lo schema si rilegge all'istruzione successiva, a funzioni
   >     registrate: CHECK e indice sono rifiutati alla prima istruzione, sui due motori.
   > - Il rifiuto arriva a un'istruzione e non dentro il listener: un listener che alza lascerebbe aperta la connessione.
   >   Il costo è una lettura dello schema in più per connessione (`NullPool`).
   > - Questo corregge la mia review di B-37: la mia prima sonda non importava `db/session.py`, mentre il processo
   >   dell'upgrade lo importa (`env.py` → `db.base` → `db/__init__.py`).
   > - Oggi non si sfrutta attraverso il controllo del ripristino: un archivio così si ferma prima, all'`integrity_check`
   >   di `describe_database()` («unknown function»), anche se con un errore non codificato (la nota per B).
3. ✅ (2026-10-17, 15:38) **Cura e verdi senza slot**.
   - Cura (`files/h51/apply.py --cure-only`, `cmp` OK): in `set_sqlite_pragma()`, `PRAGMA trusted_schema=OFF` per primo
     e `PRAGMA writable_schema=RESET` per ultimo, con il commento che spiega l'ordine; una voce nella docstring.
   - Doc (docs-writer, seconda passata sulla cura vera): in `security.md`, la sottosezione `#trusted-schema-server` con
     «Why the reset, last» e «When SQLite refuses», poi il punto «In the upgrade's process too» e «Why the upgrade needs
     it» corretti; in `database/index.md` r. 53, il reset.
   - Ho corretto i testi rimasti alla prima versione: la docstring del test (r. 5 e 15) e le tre righe del runner, che
     dicevano anche «CHECK con floor», non provato.
   - **Evidenza** (`files/runs/h51-greens.sh`, poi `h51-recheck.sh`):
     - ruff e black puliti. Il runner ha 3 PLC0415, gli stessi già alla HEAD;
     - `db session-pragmas` 15 passed;
     - `db migration-005` 25 (1 avviso già noto: SQLAlchemy non riflette l'indice d'espressione `lower(email)`), `006`
       37, `007` 29, `008` 23, `009` 11;
     - `db post-migration` 45, `db autoincrement-schema` 4, `utils dev-cli-db-path` 17, `services backup-staging` 168;
     - `mkdocs build` stretto senza avvisi; `check-links` 97; `git diff --check` pulito.
4. ✅ (2026-10-17, 15:48) **Slot** (GO del coordinatore alle 15:39, carico 35): `api backup-restore` sul server della
   corsia con la cura, 161 passed. Porta 6181 libera dopo il run (lsof vuoto).
5. ✅ (2026-10-17, 15:50) **Checkpoint**.
   - Commit proposti:
     - `fix(db): untrusted schema on every connection` (`session.py`, il test, il runner);
     - `docs(security): untrusted schema, restore instance key` (`security.md`, `database/index.md`);
     - `docs(journal): H-51, A profile and A-42/A-43 reviews` (piano e backlog).
   - CHANGELOG 🔒, proposta: «A restored backup's database can no longer make the server run code through its
     schema: every database connection turns SQLite's `trusted_schema` off first and reads the schema again last, so a
     `CHECK`, a `DEFAULT` or an index that calls a function the app registers is refused instead of run, in the server
     and in the restore check's upgrade.»
   - Note per B, le passa il coordinatore: l'`OperationalError` grezzo di `describe_database()`; la docstring di
     `env.py`.

### Mini-lotto «H-47 col disegno giusto; la clausola di B-37 in `database/index.md`» (2026-10-17, 16:00) — solo giornale e doc

> Dal coordinatore (15:55, dopo l'entrata di H-51: `2def8f7db`, dev `70ab2fcc6`, CHANGELOG 🔒 `6aa42af1a`): «Next: the
> mini-lot (the H-47 line with the right design, plus the `database/index.md` r.203-204 clause), journal and docs only.
> After it, propose your most valuable open 1.3 item, analysis first.» La riga «H-51» che X ha scritto nella mia
> sezione (i 500 di `providers.py`) diventa X-R74, di X: non la tocco. In dev non c'è.

1. ✅ **H-47** (backlog, sezione H): riscritta col disegno giusto, dopo aver riletto B-38 entrato (`_secret_path()` in
   `scripts/backup_cli.py`).
   - Cosa fa B-38, da root:
     - il giro di `lstat` dentro la cartella dei dati;
     - un'apertura `O_RDONLY|O_NONBLOCK` che **segue** i link, con `fstat` che chiede un file regolare;
     - poi `read_secret_file` riapre per percorso.
   - Il residuo sono quindi tre passi separati.
   - Il disegno: `regular_only`, cioè controllo e lettura sullo stesso descrittore; `no_links_under=<radice>`, cioè
     una discesa con `dir_fd` e `O_NOFOLLOW` per componente sotto la radice. Mai un `O_NOFOLLOW` secco (Kubernetes).
   - Il punto «B mette `O_NOFOLLOW|O_NONBLOCK`» descriveva il piano, non quello che B ha consegnato: è corretto.
2. ✅ **`database/index.md`** r.204: «`run_post_migration_fixes()` works on a direct `sqlite3` connection, with
   `trusted_schema` off before anything else (lot B-37)».
3. ✅ (2026-10-17, 15:54) Verifica (`files/runs/mini47.sh`): `mkdocs build` stretto senza avvisi, `check-links` 97,
   `git diff --check` pulito. Dev è fermo alla HEAD `6aa42af1a`.
   > **⚠️ Fuori pista**: rileggendo la mia sezione per scegliere «il lotto più utile», ho visto che molte righe H già
   > entrate non sono chiuse con ✅, data e commit, come chiede la regola del backlog. Esempi con il commit che le nomina:
   > H-17, H-21…H-25, H-27…H-30, H-32…H-34, H-37, H-39, H-42, H-45, H-46. Altre, come H-19 e H-49, hanno commit che
   > non nominano l'ID. Propongo una riconciliazione, solo giornale.

### Lotto «H-43: una corsia di test con il profilo managed, per gli E2E del cloud» (2026-10-17, 16:10) — analisi

> Dal coordinatore (16:00, dopo l'entrata del mini-lotto, dev `13b6cfde1`): «H-43 analysis (read-only) first, the most
> useful for Cloud». Deve coprire: come la corsia accende il profilo managed senza rompere l'isolamento del runner
> condiviso; quale insieme di E2E ci gira; come le violazioni della CSP report-only si raccolgono e fanno fallire; lo
> `<script>` inline di `app.html` come reperto a parte; il costo in tempo di corsia.

**Stato reale** (sola lettura, HEAD `13b6cfde1`):
1. **La corsia gira sui default.** `configure_test_runtime()` (`scripts/cli_base.py:264`) toglie:
   - ogni variabile documentata in `.env.example`;
   - i segreti dell'istanza (`INSTANCE_TRUST_SECRETS`);
   - ogni `LIBREFOLIO_*`, salvo `TEST_LANE_KEEPS` e il prefisso `LIBREFOLIO_TEST_*` (`kept_in_a_test_lane()`).

   Poi imposta porta, cartella dei dati, lane id e test mode.
2. **La pulizia avviene due volte.** Una nel runner (`scripts/test_runner/_cli.py:547`), una in `dev.py server --test`
   (`dev.py:205`). Quest'ultimo è il backend condiviso, ed è anche il comando del `webServer` di Playwright, che riceve
   in `WEB_SERVER_ENV` solo le quattro variabili della corsia. Un `LIBREFOLIO_PROFILE` messo dal runner sparirebbe
   quindi alla pulizia del server.
3. **Cosa cambia il profilo managed** (`PROFILE_DEFAULTS` ed `ENVIRONMENT_PROFILE_DEFAULTS`, `config/__init__.py`):
   - la protezione dai frame: `X-Frame-Options: SAMEORIGIN` più `PAGE_POLICY` imposta sui documenti;
   - la CSP report-only sulle pagine dell'app;
   - i worker del rischio che si fermano dopo 60 s;
   - un ripristino fino a 500 MB;
   - nel frontend, `selfHostedConfirmed()`/`managedConfirmed()` nascondono quello che vale solo per chi ospita da sé.
4. **Il server managed parte in una corsia.** I blocchi dell'avvio esclusivi del managed sono due:
   - `WeakSecretError`: il `JWT_SECRET` della corsia è generato lungo;
   - `ManagedTestModeError`: la corsia ha il suo lane id di 32 caratteri.
5. **Oggi la UI managed si prova con degli stub** di `/system/instance` (`fixtures/instance-config.ts`), in
   `legal-and-managed`, `theme-roles`, `asset-modal`, `auth-forgot-password-email` e `files-uploader`: la UI è
   coperta, gli header veri no.
   - `page-policy` (H-42) **inietta** la politica con `context.route`.
   - Nessun E2E vede l'header della CSP report-only: nessuno misura cosa romperebbe una CSP applicata.
6. **142 file di spec** importano `test` da `e2e/fixtures/playwright.ts`: un raccoglitore si mette in un punto solo.
   Ci sono circa 1.400 casi, con due progetti (desktop, mobile).

**Disegno: la corsia managed senza rompere l'isolamento**
- **Opzione**: `--lane-setting NOME=VALORE`, ripetibile, su `dev.py test` e su `dev.py server --test`.
- **Lista ammessa**: `TEST_LANE_SETTABLE` in `cli_base.py`, accanto a `TEST_LANE_KEEPS`, con `LIBREFOLIO_PROFILE`,
  `LIBREFOLIO_FRAME_PROTECTION` e `LIBREFOLIO_CSP_REPORT_ONLY`.
  - Mai segreti, porte, cartelle dei dati o nomi `LIBREFOLIO_TEST_*` del runner.
  - Un nome fuori dalla lista dà un errore prima che parta qualsiasi cosa. Il valore lo valida il server all'avvio,
    con un rifiuto netto.
- **Trasporto**: una sola variabile sotto il prefisso tenuto, `LIBREFOLIO_TEST_LANE_SETTINGS`
  (`LIBREFOLIO_PROFILE=managed;…`), messa dal runner.
  - `configure_test_runtime()` riapplica le coppie ammesse dopo la pulizia, in ogni processo dell'albero: runner,
    Playwright, `dev.py server --test`, worker di uvicorn.
  - `WEB_SERVER_ENV` la inoltra.
- **Mai da `.env`**: un `LIBREFOLIO_TEST_*` si tiene dalla configurazione dello sviluppatore, quindi una riga dimenticata
  renderebbe managed ogni corsia, in silenzio. `configure_test_runtime()` rifiuta la variabile quando viene da `.env`, e
  il runner stampa le impostazioni della corsia alla partenza.
- **Isolamento**:
  - le altre corsie non vedono niente: l'ambiente è per albero di processi;
  - la cartella dei dati e il DB della corsia non cambiano, perché il managed non scrive niente di suo;
  - ogni run avvia il suo backend con un lane id nuovo (la sonda di prontezza), quindi un server di un altro profilo
    non viene mai riusato;
  - la build del frontend è la stessa: il profilo si legge a runtime.
- **Test del runner**: la lista ammessa, il trasporto attraverso una pulizia annidata, il rifiuto da `.env`, un nome
  sconosciuto. Nello stile di `utils runtime-isolation` e `test-runner-cli`.

**Quale insieme di E2E**
- **Fase 1**, un'azione «cloud smoke» (per esempio `front-utility cloud-smoke`): 10-12 spec esistenti che coprono le
  pagine principali e le superfici a rischio per le politiche.
  - Pagine: login e layout, dashboard, asset (lista, dettaglio, modale), transazioni e import, File con l'anteprima
    PDF (le politiche su frame e oggetti), broker, impostazioni (utenti, sicurezza), rischio, AI Export,
    `legal-and-managed`, `page-policy` (che, sulla corsia managed, legge l'header vero).
  - Solo desktop, con `--lane-setting LIBREFOLIO_PROFILE=managed`.
- **Fase 2**: tutta la suite sulla corsia managed, in uno slot.
  - Le spec sensibili al profilo usano gli stub, quindi reggono.
  - `gallery` resta self-hosted, perché fotografa i link di donazione.
  - Una spec che si basasse sul profilo vero senza stub va trovata al primo run, e avrà un `test.skip` sul profilo
    letto una volta per worker.

**Le violazioni della CSP report-only: raccolta e fallimento**
- **Un fixture automatico** in `e2e/fixtures/playwright.ts`:
  - `context.addInitScript` registra un listener di `securitypolicyviolation`, che scatta anche in report-only
    (`disposition: 'report'`);
  - `context.exposeBinding` porta ogni violazione al processo del test, anche dopo una navigazione: direttiva, URI
    bloccata, file e riga, campione, URL della pagina.
- **Alla chiusura del test**, le violazioni che non sono in una baseline lo fanno fallire, con un elenco leggibile;
  quelle note si contano.
- **La baseline**: `e2e/csp-baseline.json` (direttiva, sorgente, motivo, proprietario), come un cricchetto: si possono
  solo togliere voci.
- **Su una corsia self-hosted** il fixture non fa niente (nessun header report-only, nessun evento): resta sempre
  acceso, a costo zero. Le righe «[Report Only] Refused…» della console si contano come riserva.
- **Non proposto ora**: un endpoint `report-to`/`report-uri` nel backend. Servirebbe alle operazioni del cloud, perché
  oggi una violazione in produzione non si vede. Però la consegna è asincrona e non va bene per gli E2E, e un
  endpoint non autenticato va irrobustito. È una voce futura a parte.

**Reperto a parte: gli script inline**
- L'`index.html` costruito ha due script inline:
  - quello di `app.html` (1.459 caratteri): l'anti-FOUC del tema, la cattura del prompt d'installazione PWA, la
    registrazione del service worker;
  - quello di avvio di SvelteKit (373 caratteri): `__sveltekit_…` e l'`import()` dell'entry.
- Entrambi violano `script-src 'self' 'wasm-unsafe-eval'`. Su un'istanza managed ogni caricamento di pagina segnala
  oggi due violazioni, che non si vedono perché manca un endpoint, e bloccano una CSP applicata.
- **Cura proposta** (lotto successivo, mio: `static_site.py` e `security_headers.py`): il backend calcola `sha256-…` di
  ogni script inline dell'`index.html` servito, una volta per build (mtime), e lo aggiunge a `script-src` di tutte e
  due le politiche.
  - Non tocca `app.html`, che è del programma colori.
  - Copre anche lo script di SvelteKit, che dall'HTML non può uscire.
  - L'alternativa, spostare lo script di `app.html` in `static/`, lascerebbe comunque quello di SvelteKit.
  - Con la fase 1 di H-43 queste due sono le prime voci della baseline; la cura con gli hash le toglie.

**Costo**
- **Implementazione**:
  - opzione, trasporto e test del runner: mezza giornata;
  - fixture, baseline e doc: mezza giornata;
  - azione smoke e registrazione: un quarto di giornata.
- **Superfici condivise**: `scripts/cli_base.py`, `scripts/test_runner/_cli.py`, `dev.py` (l'opzione di
  `server --test`), `frontend/playwright.config.ts`, `frontend/e2e/fixtures/playwright.ts` (tocca ogni spec),
  `_frontend_utility.py`, la doc dei test.
- **Tempo di corsia**:
  - fase 1: l'avvio del server (1-2 min) più 10-12 spec desktop a 2-4 worker, circa 6-12 min. È una stima, da misurare
    al primo run;
  - fase 2: quanto un run E2E completo self-hosted del treno, con un sovraccosto vicino a zero (un header e un
    listener).
- **Rischi**:
  - il fixture condiviso tocca ogni spec, quindi si prova prima su un piccolo insieme, con un interruttore per
    spegnerlo;
  - se `webServer.env` di Playwright fonde o sostituisce l'ambiente è da verificare (si mette la variabile
    esplicitamente).

**Decisioni** (per il coordinatore):
- D1: la lista ammessa, i tre nomi oppure altri.
- D2: solo la fase 1 nella 1.3, oppure anche la fase 2.
- D3: il raccoglitore sempre acceso (la mia proposta) oppure dietro un flag.
- D4: la cura con gli hash, come lotto H dopo la fase 1.

**Decisioni del coordinatore su H-43** (16:20), testuali in sostanza:
- D1: i tre nomi.
- D2: nella 1.3 la fase 1. La fase 2 gira una volta sola, nel cancello della release candidate, nella corsia del
  coordinatore: non è una corsia ricorrente.
- D3: il raccoglitore sempre acceso, **con un interruttore** (una variabile d'ambiente), provato prima su poche spec.
  Il checkpoint deve mostrare un campione E2E self-hosted verde e l'azione cloud smoke verde.
- D4: la cura con gli hash è un lotto H a parte dopo la fase 1, nella 1.3 se c'è tempo. I due script inline sono le
  prime voci della baseline.
- **OK di scrittura**: `scripts/cli_base.py`, `test_runner/_cli.py`, `dev.py` (l'opzione di `server --test`),
  `playwright.config.ts`, `e2e/fixtures/playwright.ts`, `_frontend_utility.py`, la doc dei test.
  - `dev.py` (E, E-19a) e `_frontend_utility.py` (W, C-97c) sono aperti altrove: le modifiche lì vanno solo aggiunte,
    e per ultime.
- Ordine: prima la riconciliazione del backlog, poi la fase 1 con i rossi. Lo slot va chiesto per il primo cloud smoke.

### Riconciliazione del backlog H (2026-10-17, 16:30) — ✅ solo giornale

- Chiuse con ✅, data e SHA (da `git log`, nella storia di dev, e dalle voci «Ingresso» del piano) le 25 righe già
  entrate: H-12, H-17, H-19, H-21…H-30, H-32…H-37, H-39, H-41, H-42, H-45, H-46, H-49.
  - Il diff cambia solo le loro prime righe (`- **H-NN ·` → `- ✅ **H-NN ·`) e aggiunge una riga di chiusura ciascuna.
  - H-41 (di W, trovata nel lotto H-34) è chiusa da `c0b67f4c8` del lotto R13-SEC7-3, con i rossi in `61acbc16b`.
- Restano aperte:
  - H-3, bloccata da P24;
  - H-5, la traduzione, solo su richiesta;
  - H-7, H-8 e H-11, Docker e dipendenze;
  - H-18, i toast, componente condiviso;
  - H-20;
  - H-31: `blocked` sta solo in `InstanceBlockResponse` (`/system/block`, dietro login), non nel pubblico
    `/system/instance`;
  - H-38 e H-40, Linux e Docker;
  - H-43, in corso;
  - H-44;
  - dopo la 1.3: H-47, H-48 e H-50.

### Lotto «H-43, fase 1: la corsia managed, il raccoglitore della CSP report-only, l'azione cloud smoke» (2026-10-17, 16:40) — passi

> Via del coordinatore (16:35): la riconciliazione è entrata (dev `c3600c247`); HEAD `a84020b09`. Decisioni D1-D4 e OK di
> scrittura: vedi sopra.

**Contratto**:
- **A. La corsia**:
  - `scripts/cli_base.py`: `TEST_LANE_SETTABLE` (i tre nomi), `TEST_LANE_SETTINGS = "LIBREFOLIO_TEST_LANE_SETTINGS"` e
    `parse_lane_settings()`;
  - `configure_test_runtime(…, lane_settings=None)` rifiuta la variabile se viene da `.env` e riapplica le coppie ammesse
    dopo la pulizia;
  - `_cli.py` `_add_runtime_args`: `--lane-setting NOME=VALORE`, ripetibile; `_configure_runtime` lo passa e stampa le
    impostazioni in vigore;
  - `dev.py server`: `--lane-setting`, solo con `--test`;
  - `playwright.config.ts`: `WEB_SERVER_ENV` inoltra la variabile.
- **B. Il raccoglitore**, in `e2e/fixtures/playwright.ts`:
  - un fixture automatico `cspViolations`: `addInitScript` per `securitypolicyviolation` ed `exposeBinding`;
  - l'opzione `cspFailOnUnknown`, vera di default;
  - l'interruttore `E2E_CSP_COLLECTOR=0`;
  - la baseline `e2e/csp-baseline.json`, con i due script inline dell'`index.html` riconosciuti per ordine e risolti
    in righe dall'HTML servito;
  - la logica pura in `e2e/fixtures/csp.ts`.
- **C. Le azioni**, in `_frontend_utility.py`, solo aggiunte e per ultime:
  - `front-utility csp-collector`, che gira anche su una corsia self-hosted perché la spec inietta i suoi header;
  - `front-utility cloud-smoke`, che rifiuta di partire se la corsia non è managed. Contiene 14 spec, desktop: `auth`,
    `layout/legal-and-managed`, `layout/page-policy`, `layout/csp-collector`, `portfolio/dashboard`,
    `portfolio/risk-analysis`, `assets/asset-modal`, `transactions/transactions-table`,
    `transactions/tx-brim-import`, `files`, `brokers/brokers`, `settings/security-tab`, `settings/admin-users`,
    `ai-export/ai-export-panel`.
- **D. Doc** (docs-writer): `test-walkthrough/runner_architecture.md` e `e2e.md`.

**Passi**:
1. Rossi (test-author, in parallelo):
   - ✅ (2026-10-17, 16:35) **Python**: +68 test in `test_runtime_isolation.py`.
     - Classi `TestTestLaneSettings`, `TestParseLaneSettings`, `TestLaneSettingsOnTheCommandLine`, più i controlli
       statici di Playwright.
     - Il `.env` è finto: `PIPENV_DOTENV_LOCATION` punta a `tmp_path`.
     - `dev.main()` gira in processo con l'imbracatura `capture_server_child`.
     - Evidenza: `utils runtime-isolation` 58 failed / 308 passed, come previsto, nessun ERROR; ruff e black puliti.
     - Letture fissate dai test:
       - si valida prima di toccare l'ambiente;
       - il rifiuto da `.env` vale anche con `--lane-setting`;
       - `dev.py server` senza `--test` esce con 1, prima di ogni build;
       - una sola riga `Test lane settings: …`;
       - la variabile non va in `.env.example` né in `TEST_LANE_KEEPS`.
   - ✅ (2026-10-17, 16:45) **E2E**: la spec nuova `layout/csp-collector.spec.ts` (test-author), 9 test per progetto.
     - Logica pura (4): `cspCollectorEnabled`, `inlineScriptLines`, `isKnown`, la baseline ben formata e senza id doppi.
     - Documenti sintetici serviti da `page.route` con una loro `script-src 'self'` report-only (3): una violazione
       registrata una volta e lo script gira lo stesso; due documenti di fila; una violazione ignota che fa fallire il
       test al teardown, segnata `test.fail()`.
     - L'app vera (1): la pagina di accesso con la policy report-only del profilo managed (iniettata dalla spec se la
       corsia non la manda) riporta i suoi due script inline e nient'altro, e la baseline li conosce entrambi.
     - L'interruttore (1): gira solo in un run con `E2E_CSP_COLLECTOR=0`.
     - Evidenza: `front-utility csp-collector` rc=1 con «Test has unknown parameter "cspViolations"», cioè l'errore di
       caricamento previsto prima della cura. Prettier: tre blocchi da riformattare (solo forma), sistemati con
       `prettier --write` da `frontend/`.
2. ✅ (2026-10-17, 16:55) **Cura**: script a secco in `files/h43/` (`apply_core.py`, `apply_shared.py`), poi `--apply`
   e `cmp` file per file con le copie a secco: tutti uguali.
   - `cli_base.py`: `TEST_LANE_SETTABLE`, `TEST_LANE_SETTINGS`, `parse_lane_settings()`; `configure_test_runtime(…,
     lane_settings=None)` controlla l'origine `.env` e valida prima di caricare, poi pulisce, scrive la variabile di
     trasporto ordinata e applica le coppie.
   - `_cli.py`: `--lane-setting` (ripetibile) e la riga `Test lane settings: …`.
   - `playwright.config.ts`: uno spread condizionale in `WEB_SERVER_ENV`.
   - `e2e/fixtures/playwright.ts`: l'opzione `cspFailOnUnknown` e il fixture automatico `cspViolations` (binding e init
     script del contesto, gli script inline di `index.html` letti una volta per worker, un giro nella pagina prima del
     conto, l'allegato `csp-violations`, `expect(…).toEqual([])` sugli ignoti).
   - Nuovi: `e2e/fixtures/csp.ts` (la logica pura) ed `e2e/csp-baseline.json` (le due voci `index-inline-script-0/1`).
   - Per ultimi, solo aggiunte: `_frontend_utility.py` (le due azioni) e `dev.py` (`server --lane-setting`, rifiutato
     senza `--test` prima di ogni build).
   > **⚠️ Fuori pista**: `apply_shared.py` riapplicato dopo la parte del runner avrebbe raddoppiato le sue ancore (le
   > ancore restano vere dopo l'inserimento). Reso idempotente: salta la parte del runner se trova `CLOUD_SMOKE_SPECS`.
   > E un I001 mio in `cli_base.py` (l'import di `Iterable` dopo `pathlib`), corretto a mano.
3. ✅ (2026-10-17, 17:10) **Verdi senza slot** (`files/runs/h43-greens.sh`, `h43-managed-preflight.sh`; log in
   `files/runs/h43/`):
   - ruff pulito su `cli_base.py`, `_cli.py`, `_frontend_utility.py` e sul test; `dev.py` ha gli stessi reperti di HEAD
     (7 C901, 21 PLC0415…, debito vecchio, confrontati via stdin). Black: `cli_base.py` e `dev.py` non sono formattati
     neanche a HEAD; nessun blocco di black tocca le mie righe, che seguono lo stile locale di `dev.py`.
   - Prettier sui cinque file del frontend; `tsc -p tsconfig.e2e.json` 0 errori; `check-orphans` OK (142 spec).
   - `utils runtime-isolation` **366/366** (i 58 rossi verdi), `utils test-runner-cli` 730, `utils dev-cli-image` 94.
   - `front-utility csp-collector`, corsia self-hosted: **8 passed** (uno è il `test.fail()` atteso) e 1 skipped
     (l'interruttore). Svelte-check 0 errori nella preparazione del runner.
   - Pre-volo managed, una spec quindi senza slot: `--lane-setting LIBREFOLIO_PROFILE=managed front-utility
     csp-collector`, 8 passed + 1 skipped; la riga `Test lane settings: LIBREFOLIO_PROFILE=managed`.
     - L'avvio è pulito: niente `ManagedTestModeError` né `WeakSecretError`.
     - L'allegato del test della pagina d'accesso dice «sent by the lane itself»: l'header è uguale a
       `CSP_REPORT_ONLY_POLICY`, con `frame-ancestors 'self'`.
     - Riportati i due script inline alle righe 14 (14–38) e 116 (116–131), entrambi noti; 0 ignoti.
   > **⚠️ Fuori pista**: le due prime corse di `csp-collector` hanno ricostruito il frontend («Frontend sources
   > changed»). Dopo la seconda costruzione `check_frontend_needs_build()` dice `False` e il pre-volo non ha ricostruito:
   > un evento transitorio, non ricostruibile (le date della costruzione precedente sono sovrascritte). Lo guardo nelle
   > corse dello slot.
3b. ✅ (2026-10-17, 17:57) **Tre difetti trovati dal docs-writer**, leggendo il codice per la doc. Lo slot è rimandato
   (via del coordinatore, che ha dato anche l'OK di scrittura su `page-policy.spec.ts`, solo per il describe annidato
   e per il commento di testa):
   1. **`page-policy.spec.ts`**, i controlli positivi (H-42, mio): alzano di proposito tre violazioni enforced
      (`base-uri`, `object-src`, `form-action`) nel contesto del test. Il raccoglitore le registra e la baseline non le
      conosce, quindi il test fallisce al teardown su ogni corsia.
      - Provato: `front-utility page-policy` → 1 failed (quel test, «Content-Security-Policy violations
        e2e/csp-baseline.json does not know (H-43)»), 3 passed. Gli altri tre test passano col raccoglitore.
      - Cura: un `describe` annidato con `test.use({cspFailOnUnknown: false})` per quel test solo (test-author).
   2. **`cloud-smoke` in `all`**: registrata con `in_all` vero di default. Su una corsia self-hosted rifiuta prima di
      `_run_playwright`, quindi il passo consolidato non la copre e il passo seriale la lancia: `front-utility all`,
      `all-frontend` e `all` rossi. Cura: `in_all=False`; ogni sua spec ha già un'azione sua.
   3. **Il rifiuto da `.env` sotto `pipenv run`**: pipenv carica `.env` nell'ambiente (con `override=True`) prima di
      `dev.py`, quindi la variabile sembrava ereditata da un runner e veniva applicata. Il parametro
      `from-the-runner-over-the-dotenv-file` fissava proprio il buco.
      - Cura (regola B): rifiuto ogni volta che `.env` la contiene. I figli del runner non leggono mai `.env`
        (`PIPENV_DONT_LOAD_ENV=1`, messo da `configure_test_runtime` e dal webServer di Playwright).
      - Test (test-author): il parametro riscritto come un figlio vero (con la guardia), più un test nuovo per pipenv
        (`.env` e ambiente con lo stesso valore) e un controllo statico di `in_all`.
   - Note del docs-writer passate nella doc: una frase vecchia di `security.md` (~r.2798, «the runner cannot turn
     frame protection on in a lane»), da correggere.
   - Residuo, da scrivere nel backlog: le voci con `indexInlineScript` si cercano nell'`index.html` servito su `/`,
     mentre i link profondi ricevono `200.html`. Oggi gli script stanno alle stesse righe (stesso `app.html`); la cura
     con gli hash (D4) toglie queste voci.
   - Residuo per la fase 2: `group_frontend_units` (`_consolidate.py`) non guarda `in_all`. In un `all-frontend` su
     una corsia managed, quindi, il gruppo di front-utility rilancia anche le 10 spec del cloud smoke di altre categorie
     (doppioni, ~10–15 min).
   - Previsto per il cloud smoke (lettura della build): il chunk di cheetah-grid include `webpack/buildin/global.js`,
     che in un modulo ES (strict) arriva a `new Function("return this")()`. Ne esce una segnalazione `script-src` eval,
     innocua: se una CSP applicata blocca la chiamata, il try/catch ripiega su `window`. ECharts `parseInput` usa
     `JSON.parse`, quindi non conta. Con `--coverage`, il preambolo di istanbul (`coverageGlobalScopeFunc`, vero di
     default) fa `new Function('return this')()` in ogni modulo, senza try/catch: lo stesso corpo della sonda di
     cheetah-grid, quindi la voce F1 conosce anche quelle (ristretta con `'report-sample'`, conoscerebbe lo stesso
     campione «return this»). Con una CSP applicata una build con copertura si romperebbe, ma è solo una build di test.
   - **Rossi** (test-author, `files/runs/h43-reds2.sh`): `utils runtime-isolation` **4 failed / 367 passed**, esattamente
     i previsti:
     - `test_lane_settings_pipenv_loaded_from_the_dotenv_file_are_refused` ×2 (`.env` e ambiente con lo stesso valore,
       come li esporta `pipenv run`; con e senza `--lane-setting`);
     - `test_the_runner_refuses_a_bad_lane_setting_with_its_error[the-variable-pipenv-loaded-from-the-dotenv-file]`;
     - `test_the_cloud_smoke_is_left_out_of_every_all_and_the_collector_spec_is_not[cloud-smoke]`.
     - Il parametro `from-the-runner-over-the-dotenv-file` è diventato un test suo, un figlio vero con la guardia
       (`test_a_child_of_the_runner_reads_no_dotenv_file_and_sets_the_inherited_settings`): verde prima e dopo.
     - `page-policy.spec.ts`: il describe annidato e il commento di testa (`git diff -w`: il corpo del test è
       invariato). Nessun riferimento al titolo completo del test altrove. Ruff, black, Prettier, tsc e2e puliti.
   - **Cura** (`files/h43/apply_fix2.py`, a secco, `--apply`, `cmp` OK): in `cli_base.py` il rifiuto da `.env` viene
     prima di tutto e non guarda più l'ambiente; in `_frontend_utility.py` `in_all=False` su `cloud-smoke`.
   - **Verdi** (`h43-greens2.sh`): ruff OK; `utils runtime-isolation` **371/371**; `utils test-runner-cli` 730;
     `check-orphans` OK; `front-utility page-policy` **4/4** su corsia self-hosted, con le tre violazioni dei controlli
     registrate e allegate ma non fallite. Nessuna ricostruzione del frontend.
   - **Quarto punto, dopo lo slot** (OK del coordinatore, 17:43, su `_common.py` e `_consolidate.py`): su una corsia
     managed il passo consolidato chiama ogni azione, qualunque sia `in_all`, e lì il controllo del profilo passa.
     `front-utility all` lancerebbe quindi il cloud smoke, e un `all-frontend` (fase 2) farebbe girare due volte 7 spec
     di altre categorie (dashboard, risk-analysis, asset-modal, transactions-table, tx-brim-import, brokers,
     ai-export-panel). Cura preparata: `add_test(..., named_only=True)`, saltato da `group_frontend_units`
     (`files/h43/apply_fix3.py`). Con lei due commenti vecchi della stessa causa: `ServedDocument.lanePolicy` in
     `page-policy.spec.ts` e la descrizione di `page-policy` in `_frontend_utility.py`.
4. ✅ (2026-10-17, 17:59–19:04) **Slot, corsa 1: il cloud smoke** (`files/runs/h43-slot.sh`; rapporto e sintesi in
   `files/runs/h43/slot-cloud.*`): `--lane-setting LIBREFOLIO_PROFILE=managed front-utility cloud-smoke`, **224 passed,
   4 rossi, 1 skipped** (l'interruttore), 17,7 min.
   - Avvio pulito, riga `Test lane settings: LIBREFOLIO_PROFILE=managed`. I due script inline dell'`index.html` sono
     riportati su ogni pagina (`/`, `/dashboard`, `/transactions`, `/files`, `/assets`, `/settings`, `/brokers`…):
     tutti noti.
   - Nessuno dei 4 rossi sta nel codice di H. Il raccoglitore ha funzionato: ogni violazione ignota ha fatto fallire il
     suo test con un elenco leggibile.
   - **F1** `files.spec.ts` › «opens table preview for BRIM files»: `script-src` `eval` dal chunk di cheetah-grid
     (`Cn5CY6Wr.js:758`), come previsto. Entrambe le build della 1.16.7 (es5 e UMD, nessuna ESM) contengono la sonda
     di webpack `new Function("return this")()` dentro un try/catch che ripiega su `window`: innocua anche con una
     policy applicata.
   - **F2** `legal-and-managed.spec.ts` LGM-E-01 e LGM-E-03 (A, `b1b647edc`): «the lane's answer» con la corsia
     self-hosted come precondizione (i link di donazione). Su una corsia managed falliscono per costruzione; le varianti
     managed sono simulate (E-04, E-05) e girano su ogni corsia.
   - **F3** `admin-users.spec.ts` AUSR-E-07 (A): la sonda dell'indirizzo prende l'indirizzo scritto dall'admin, e il test
     ne scrive apposta di altre origini (127.0.0.1 invece di localhost, la porta 1, `probe-mismatch.invalid`). Ne escono
     6 violazioni `connect-src` report-only, con un nonce nell'URL. Per l'applicazione futura della CSP è un reperto
     vero: con `connect-src 'self'` applicata, la sonda di un'origine diversa dalla pagina viene bloccata.
   - Portati al coordinatore (18:25) con le proposte: F1 una voce della baseline ora, ristretta nel lotto D4 con
     `'report-sample'`; F2 la spec fuori da `CLOUD_SMOKE_SPECS` e una riga per A; F3 una voce con un confronto nuovo sul
     percorso dell'URL bloccato e una riga per A e per il lotto dell'applicazione.
   - **Decisioni del coordinatore** (18:30): F1 = la voce ora, ristretta nel lotto D4 (riga H-52); F2 come proposto (la
     riga per A); F3 come proposto, proprietari A + il lotto dell'applicazione: la metà sicurezza è di H (riga H-53), la
     metà esperienza di A.
   - **Corse 2 e 3: il campione self-hosted**, col raccoglitore acceso: `front-broker all` **57 E2E** (2 + 55), ogni
     azione ✓; `front-ai-export all` **18 E2E** (desktop + mobile) + Vitest 616, ogni azione ✓. Slot libero alle 18:29,
     porta 6181 libera.
   > **⚠️ Fuori pista**: la sintesi delle corse 2 e 3 rileggeva il rapporto del cloud smoke, perché il passo consolidato
   > non riscrive `playwright-report/`. Gli esiti veri sono quelli del log del runner (`.testLog/<cat>__e2e-*.log`).
   - **`named_only`** (OK del coordinatore, 17:43): rossi di test-author, `utils test-runner-cli` **14 failed / 737** e
     `utils runtime-isolation` **1 failed / 372**, esattamente i previsti.
     - `add_test` salva `named_only` e `in_all` falso;
     - `group_frontend_units` lascia fuori un'azione `named_only` e tiene un alias `in_all=False` fra i reclamanti;
     - sul catalogo vero, con una corsia managed simulata da entrambe le variabili, il gruppo di front-utility non ha le
       7 spec di altre categorie.
     - Cura `files/h43/apply_fix3.py` (a secco, `--apply`, `cmp` OK), con `# noqa: PLC0415` sull'import pigro nuovo
       (ruff resta a 9, come HEAD). Verdi: `utils test-runner-cli` **751/751**, `utils runtime-isolation` **373/373**,
       `check-orphans` OK.
     > **⚠️ Fuori pista** (test-author): impostare solo `LIBREFOLIO_PROFILE=managed` non riproduce una corsia managed.
     > La raccolta chiama `get_test_db_path()` (le azioni di `db`), che rifà `configure_test_runtime()`, e questo toglie
     > il profilo se `LIBREFOLIO_TEST_LANE_SETTINGS` non lo porta. Il test mette entrambe le variabili, come una corsia
     > vera, e salva e ripristina l'ambiente intero.
   - **F1/F2/F3** (decisioni delle 18:30): rossi di test-author in `csp-collector.spec.ts`, `front-utility
     csp-collector` **2 failed / 8 passed / 1 skipped**, esattamente i previsti: il confronto `blockedPath` e «la
     baseline conosce i reperti del primo cloud smoke». Il controllo «ben formata» vuole ora esattamente uno fra
     `blockedURI` e `blockedPath`.
     - Cura `files/h43/apply_fix4.py` (a secco, `--apply`, `cmp` OK): `csp.ts` (`blockedPath`, `namesBlocked`), due voci
       nella baseline (`cheetah-grid-global-probe`, `address-probe-other-origin`), la regola del cricchetto nel testo
       («una voce si aggiunge solo con una decisione registrata, con ragione e proprietario, mai per zittire un rosso»),
       `CLOUD_SMOKE_SPECS` a 13 (fuori `layout/legal-and-managed.spec.ts`).
     - Verdi: Prettier e tsc e2e puliti, `front-utility csp-collector` **10 passed + 1 skipped**.
   - **Corsa 4: il cloud smoke rifatto**, 13 spec, corsia managed: **225 passed, 0 inattesi, 1 skipped** (più il
     fallimento atteso), 20,0 min. F1 e F3 sono conosciuti (allegati, non falliti); i due script inline su ogni pagina.
     Porta 6181 libera alle 19:04.
5. ✅ (2026-10-17, 19:15) **Doc e chiusura**:
   - Doc (docs-writer, quattro giri): `test-walkthrough/index.md` («Lane Settings», `#lane-settings`, e la riga delle
     opzioni), `e2e.md` (la sezione del raccoglitore `#csp-collector`, la baseline `#csp-baseline` con le quattro voci e
     i due modi di nominare la risorsa), `front-utility.md` (le due azioni, la tabella dei test del raccoglitore, il
     cloud smoke a 13 spec, «solo quando nominata, su ogni corsia»), `runner_architecture.md` (le chiavi `in_all` e
     `named_only`, `#registry-entry-shape`, e il passo 5 della guida), `architecture/security.md` (il punto sulle
     impostazioni di corsia, il paragrafo di `page-policy`, una frase sui reperti del cloud smoke con H-53).
   - Commenti vecchi della stessa causa (OK del coordinatore): la testa e `ServedDocument.lanePolicy` in
     `page-policy.spec.ts`, la descrizione di `page-policy` e la docstring di `add_test` («solo il passo consolidato del
     frontend la legge»).
   - Controlli finali (`files/runs/h43-final.sh`): ruff a 9 come HEAD, black OK sui file formattati, `utils
     test-runner-cli` 751, `check-orphans` OK, `mkdocs build` stretto 0 avvisi, `check-links` 97 link validi,
     `git diff --check` pulito.
   - Previsione del merge con `dev_release2` (`b7f8ebeac`, 129 commit dopo la base): `git merge-file` a tre vie su
     `dev.py`, `_frontend_utility.py`, `security.md` e il backlog, **0 conflitti**. Sul piano del significato: in
     `cmd_server` dev aggiunge solo `LIBREFOLIO_DISABLE_WHATS_NEW=1` (C-54); `legal-and-managed` è invariata in dev;
     l'unica spec di dev che inietta una CSP è `page-policy`, la mia. `asset-modal.spec.ts` (nel cloud smoke) è
     cambiata in dev: la fase 2 la rivede comunque.
   - Backlog: H-43 aggiornata (fase 1 fatta, note per la fase 2), H-52 (D4) e H-53 (F3, metà sicurezza). Le due righe di
     A (F2 e la metà esperienza di F3) vanno al coordinatore: non scrivo nella sezione di A.
   - Entrato il 17/10 (dev `d3212e9f2`, `cd04b17b0` + `11d0bce48`; seguito `3b01fff93` per i due file di test del
     runner, poi `a6adb0066`). Sulla punta: runtime-isolation 373, test-runner-cli 760. Nessuna riga nel CHANGELOG.

### Review di E-19a: il passo `stored-currencies` di `app_lifespan.py` (2026-10-17, 19:20) — ✅ OK, due appunti bassi

- Va bene: il passo gira in un thread, non solleva mai, ha i valori nel log tagliati e con repr, e `mode=rw` più
  `query_only`. Dopo `0d9781f22` sta dopo `lone-transfer-legs`, come dice `overview.md` 12–14.
- LOW-1: `_read_only()` non mette `PRAGMA trusted_schema=OFF` per primo, come fa B-37 in `post_migration`. Oggi è
  innocuo, perché `sqlite3` semplice non registra funzioni Python né carica estensioni.
- LOW-2: i passi d'avvio non hanno un tempo massimo, e le query leggono tabelle intere. Piani sulla DB della corsia:
  `SCAN price_history` e `SCAN transactions` ×2, più B-tree temporanei; `fx_rates` scandito tutto sull'indice. Ogni
  avvio, e ogni risveglio di un'istanza managed, aspetta la lettura. Proposta: misurarlo sulla copia dei dati veri e,
  se pesa, toglierlo dal cammino critico, come `provider-prewarm`.

### Lotto «H-52: gli script inline nella CSP per hash, e `'report-sample'`» (2026-10-17, 19:30) — analisi

> Dal coordinatore (19:15, dopo l'entrata di H-43): «Next: H-52 (the D4 inline-script hashes plus the
> 'report-sample' narrowing), analysis first. Your D4 is in 1.3 if it stays small.»

**Stato vero** (HEAD `a6adb0066`):
- `CSP_REPORT_ONLY_POLICY` (`security_headers.py:73`) è una costante, con `script-src 'self' 'wasm-unsafe-eval'`. Il
  middleware la mette, come header già pronto, sulle risposte `text/html` della web app (non su `/mkdocs` né su
  `/api/`), quando `LIBREFOLIO_CSP_REPORT_ONLY` è acceso (il default di managed).
- La build ha tre file HTML serviti come pagine, con script inline:
  - `index.html`: l'anti-FOUC di `app.html` (1459 caratteri, riga 14) e il bootstrap di SvelteKit (374 caratteri,
    riga 116, `base: new URL(".", location)…`);
  - `200.html`: lo stesso anti-FOUC e un bootstrap **diverso** (330 caratteri, `base: ""`). Per la SPA servono
    quindi tre hash;
  - `offline.html` (da `static/offline.html`, la pagina offline del service worker, servita anche come pagina): uno
    script di 5335 caratteri e un gestore inline `onclick="location.reload()"`. Un gestore inline è
    `script-src-attr`, e un hash di script non lo copre.
  - Il bootstrap contiene nomi della build (`__sveltekit_12g6x0f`, i percorsi del chunk d'ingresso), quindi l'hash
    cambia a ogni build: va calcolato dalla build, non può essere una costante.
- Sonda (Chromium 149, `files/h52/probe-sample.*`): con `'report-sample'` il campione di un eval sono i primi 40
  caratteri del sorgente valutato.
  - `new Function("return this")` dà `"(function anonymous(\n) {\nreturn this\n})"`, sia la sonda di cheetah-grid sia
    il preambolo di istanbul.
  - `eval("1 + 1")` dà `"1 + 1"`; uno script inline dà i suoi primi 40 caratteri.

**Disegno**:
1. Backend (file di H):
   - `static_site.py`: `spa_inline_script_hashes(build_dir)`, pura. Legge ogni `*.html` in cima alla build e ogni
     `<script>` senza `src`, di qualunque tipo (l'hash di un blocco di dati non fa danni). Normalizza gli a capo come il parser
     HTML (CRLF e CR diventano LF), produce `'sha256-<base64>'`, senza doppioni e in ordine.
   - `security_headers.py`: `CSP_REPORT_ONLY_POLICY` tiene la parte fissa, con `'report-sample'` in `script-src`;
     `report_only_policy(hashes)` vi inserisce gli hash.
   - L'header si calcola una volta, quando si costruisce il middleware e solo se la policy è accesa (come gli
     interruttori): nessun I/O sul cammino delle richieste. Una build nuova vuole un riavvio; il runner costruisce
     prima di avviare, un'immagine non cambia mai. Senza build, niente hash.
2. `static/offline.html`: il gestore inline diventa un `addEventListener` nel suo script, due righe. Altrimenti il
   clic su «Riprova» viene segnalato, e con una policy applicata bloccato. L'ultimo a toccare il file è stato il
   programma colori: serve l'OK.
3. E2E (file di H, H-43):
   - la baseline perde `index-inline-script-0/1`, ora permessi. F1 prende `"sample"` esatto e non conosce più ogni
     `eval`;
   - `csp.ts`: un confronto `sample` facoltativo, esatto;
   - D-H52-2: via il meccanismo delle righe (`indexInlineScript`, `inlineScriptLines`, `appIndexInlineScripts()` nella
     fixture). Nessuna voce lo usa più; sparisce anche la differenza fra `/` e `200.html`, e un GET per worker;
   - la spec del raccoglitore:
     - la sua copia della policy prende `'report-sample'`;
     - calcola gli hash di `/`, `/200.html` e `/offline.html` allo stesso modo, e li inietta su una corsia
       self-hosted;
     - su una managed confronta l'header della corsia con la copia più gli hash, alla lettera: una prova da un capo
       all'altro del calcolo del backend;
     - la pagina d'accesso non segnala più **niente**.
4. Test (test-author):
   - backend: un file nuovo per la funzione pura (con o senza `src`, module, blocco di dati, CRLF, doppioni, build
     assente, un vettore noto);
   - `services managed-headers`: `script-src` con `'report-sample'` e gli hash di una build temporanea; il resto
     invariato, e self-hosted invariato;
   - E2E come sopra.
5. Doc: `security.md` (la policy report-only), `e2e.md` (la baseline), `front-utility.md` (i test del raccoglitore).
6. Corsia: leggeri `services managed-headers`, il test nuovo, `front-utility csp-collector` (self-hosted e managed)
   e `page-policy`. Uno slot per un cloud smoke (~20 min): zero violazioni inline, e F1 riconosciuto dal campione.

**Decisioni**: D-H52-1 hash calcolati alla costruzione del middleware (consigliato) oppure un controllo di mtime a ogni
risposta HTML; D-H52-2 via il meccanismo delle righe (consigliato); D-H52-3 il gestore di `offline.html` (consigliato,
serve l'OK); D-H52-4 campione esatto, che vale per Chromium, l'unico browser degli E2E (consigliato).
- Nota: `'report-sample'` oggi non manda niente fuori dal browser (nessun endpoint di report). Se un giorno se ne
  aggiunge uno, i primi 40 caratteri di uno script bloccato uscirebbero.

**Costo**: backend ~60 righe più i test; E2E circa −40/+60 righe; doc. Circa 2,5 ore, slot compreso. Superfici:
`security_headers.py`, `static_site.py` e i file E2E di H-43 sono di H; `offline.html` no; `app.html` non si tocca.

**Via del coordinatore** (19:21): GO su tutte le raccomandazioni.
- D-H52-1: gli hash si calcolano quando si costruisce il middleware.
- D-H52-2: via il meccanismo delle righe.
- D-H52-3: il gestore di `offline.html`, con l'OK di scrittura: solo lo script, nessun markup o classe oltre allo
  spostamento di `onclick` in un listener.
- D-H52-4: campione esatto.
- OK di scrittura sugli altri file elencati. La nota su `'report-sample'` va in `security.md`. Prima i rossi, poi lo
  slot per il cloud smoke.

**Review di B-43** (19:25), in mezzo: ✅ OK, verificata con una sonda su SQLite 3.54.0 (`files/b43review/`). Un appunto
di precisione: in `_stage` la lettura con le funzioni finte (`_refuse_foreign_objects`) viene prima di
`describe_database()`. Un indice o una colonna generata che chiama `regexp` o `floor` si ferma quindi lì, non al
controllo d'integrità; «such as `regexp`» va cambiato.
> **⚠️ Fuori pista**: `pipenv run` lanciato dalla cartella di sessione ha creato un `Pipfile` vuoto lì (fuori dal
> repo). L'ho tolto; il venv condiviso è intatto (sqlalchemy 2.0.52, fastapi 0.141.1). Le sonde si lanciano dal
> worktree.

**Passi di H-52**:
1. ✅ (2026-10-17, 20:01) Rossi (test-author, due in parallelo; `files/runs/h52-reds.sh`):
   - backend in `test_managed_headers.py`: `services managed-headers` **52 failed / 359 passed**;
   - E2E in `layout/csp-collector.spec.ts`: `front-utility csp-collector` self-hosted **5 rossi** (il test della pagina
     d'accesso è verde, come previsto: lì la policy la inietta la spec), managed **6 rossi**; tsc 13 TS2554 (le chiamate
     a due argomenti di `isKnown`). Prettier ha riformattato la spec (solo forma, verificato).
2. ✅ (20:06) Cura (`files/h52/apply_cure.py`, a secco, `--apply`, `cmp` OK sui sei file). Verdi: `services
   managed-headers` **411/411**, `security-headers` 15, `config-audit` 220, `page-policy` 4/4; ruff, black, Prettier, tsc
   puliti. La spec del raccoglitore: verde tranne la pagina offline, su entrambe le corsie.
   > **⚠️ Fuori pista (reperto)**: la corsia serviva una build vecchia. `check_frontend_needs_build()` non guarda
   > `frontend/static/`, che adapter-static copia nella build: `static/offline.html` (20:05) era più recente di
   > `build/index.html` (20:03), eppure la risposta era `False`. Ricostruita a mano (`dev.py server --test --build-only
   > --rebuild`), la spec è **12 passed + 1 skipped** su entrambe le corsie. OK del coordinatore (20:13) per la cura
   > dentro H-52.
3. ✅ (20:30) La cura della build vecchia:
   - rossi di test-author in `TestFrontendBuildStaleness`: `utils runtime-isolation` **7 failed / 380**;
   - cura `files/h52/apply_static.py`: `frontend/static/` entra nella scansione con la regola di `src` (niente di
     nascosto: il `.cache_manifest.json` della cache dei font, riscritto a ogni controllo, non conta);
   - verde **387/387**.
   > **⚠️ Fuori pista (test-author)**: `stamp_service_worker()` (`dev.py`) riscrive `sw.js` sempre, anche uguale; con
   > `static/` guardata, ogni build della doc avrebbe causato una ricostruzione inutile del frontend. E il timbro di
   > `sw.js` (l'md5 di `offline.html`) era vecchio dopo la mia modifica: `test_pwa_assets` rosso, e i browser avrebbero
   > tenuto la vecchia pagina offline. OK del coordinatore (20:28): scrivere solo se cambia, timbrare anche in
   > `cmd_fe_build` prima della build, il timbro nuovo di `sw.js`, e i rossi in `test_pwa_assets.py`.
4. ✅ (20:50) Il timbro:
   - rossi di test-author in `test_pwa_assets.py`: `utils pwa-assets` **4 failed / 22**. Sono i tre nuovi (timbrare due
     volte lascia `sw.js` intatto, bytes e mtime; `cmd_fe_build` timbra prima del comando di build, debug e produzione)
     più quello esistente, rosso per il timbro vecchio di `sw.js`;
   - nell'imbracatura Contract 8 di `test_test_server_preparation.py` (OK delle 20:42) `stamp_service_worker` è finto,
     così nessun caso timbra il `sw.js` vero;
   - `sw.js` ritimbrato con la funzione del progetto (`dev.stamp_service_worker()`): `7e726c69` → `65ba715b`;
   - cura `files/h52/apply_stamp.py` (a secco, `--apply`, `cmp` OK);
   - testo del runner per `pwa-assets` (OK delle 20:42).
   - Verdi (`files/runs/h52-greens-final.sh`): ruff senza reperti nuovi (`dev.py` a 43 come HEAD), black OK; `utils
     pwa-assets` **26**, `test-server-preparation` 91, `runtime-isolation` 387, `test-runner-cli` 760, `services
     managed-headers` 411, `utils dev-cli-image` 94; `mkdocs build` stretto 0 avvisi, **e `sw.js` intatto dopo la build
     della doc** (la prova dal vivo della cura); `check-links` 97 validi; `git diff --check` pulito.
   - Doc della PWA (`developer/frontend/pwa.md`, docs-writer): il timbro scritto solo se cambia, `front build` che
     timbra, i nuovi casi del controllo, e nel passo 1 di «Updating the Offline Page» la regola dei gestori inline.
5. Altri testi: le descrizioni del runner (`_backend_services.py`, `_frontend_utility.py`, OK delle 20:16) applicate
   (`files/h52/apply_texts.py`, `cmp` OK). Doc: docs-writer, 25 modifiche in sei pagine più
   `admin/hosting_providers.en.md` (testo di H, `59fa4b645`). Nessun timbro di traduzione: le pagine per sviluppatori
   sono solo in inglese, e quella pagina admin non ha traduzioni.
2. Cura: `files/h52/apply_cure.py`, a secco (fatto), poi `--apply` e `cmp`. Tocca `static_site.py`
   (`spa_inline_script_hashes`, `HTMLParser` della libreria standard), `security_headers.py` (`'report-sample'`,
   `report_only_policy`, l'header costruito una volta, import pigro di `static_site` per non fare un ciclo), `csp.ts`
   (via le righe, `sample`, `isKnown` a due argomenti), la fixture (via il GET di `/` per worker), la baseline (due
   voci; F1 con `sample`) e `offline.html` (il listener).
3. Verdi leggeri; doc (docs-writer, con la nota su `'report-sample'` in `security.md`); slot per il cloud smoke.
6. ✅ (2026-10-17, 20:50–21:02) **Slot: il cloud smoke** (`files/runs/h52-slot.sh`, `files/runs/h52/s-cloud.*`): corsia
   managed, **227 passed, 0 inattesi, 1 skipped** (più il fallimento atteso), 8,9 min.
   - «Frontend sources changed, rebuilding…» per `sw.js` e `offline.html`: la scansione di `static/` funziona dal vivo.
   - **Nessuna violazione di script inline sulle pagine dell'app**. I test con un allegato `csp-violations` passano da
     218 a 7, tutti attesi: F3 (la sonda dell'indirizzo, 6), F1 (l'eval di cheetah-grid, conosciuto dal campione),
     i documenti sintetici e il controllo della sonda globale della spec, i controlli di `page-policy`.
   - Porta 6181 libera alle 21:02.
7. ✅ (21:05) **Checkpoint**:
   - previsione del merge con `dev_release2` (`e20055213`, 89 commit dopo la base): fra i miei file, dev ha toccato
     solo i tre del runner (`_backend_services.py`, `_backend_utils.py`, `_frontend_utility.py`), con **0 conflitti**
     (le registrazioni degli altri sono aggiunte);
   - backlog: H-52 ✅, e una riga nuova, H-54 (un file tolto da `src/` o da `static/` non si vede);
   - CHANGELOG: proposta una clausola nella voce esistente della policy report-only (r. 361).

### H-52 entrato; review di W-B77 e Z-33; proposta «CSP applicata» (2026-10-17, 21:10–21:40)

- **H-52 entrato**: dev `ca7ba117c` (`aaea0824b`, `cfb59de97`, `70da097fb`), CHANGELOG `1ec74c8e5` con la mia
  clausola. HEAD `1ec74c8e5`, pulito.
- **Review di W-B77** (`utils/pydantic_errors.py`): ✅ OK. Solo una nota: un vincolo scritto con un limite `Decimal`
  porterebbe `params=None`, ma oggi nessuno schema lo fa.
- **Review di Z-33** (migrazione 011 e il passo che sistema le date): la migrazione va bene, con un reperto MEDIO e uno
  BASSO per Z.
  - MEDIO: `_settle_exchange_timezone` si fida di `prep.legacy_check`, letto prima del fetch. Due aggiornamenti dello
    stesso asset (scheduler e sync manuale, nessun lock per asset) fanno rigirare la regola su righe già giuste: con
    `redate_provider_rows` le righe vengono tolte o spostate di un giorno. Cura: ricontrollare il segno sulla riga
    riletta nella transazione.
  - BASSO: un fuso che non si risolve blocca per sempre un asset segnato.
- **Proposta «CSP applicata»** (sola analisi, da portare al developer): sotto.

#### Proposta: la CSP applicata (dopo H-52)

**Cosa blocca oggi una `script-src` applicata** (scansione della build, `files/h52/enforce-scan.txt`, e cloud smoke):
- solo due siti di eval in tutto il bundle:
  - F1, la sonda globale di cheetah-grid, dentro un try/catch: con la policy applicata ripiega su `window`, funziona ma
    segnala ogni volta;
  - il `parseInput` di ECharts, che fa `new Function` solo senza `JSON.parse`: mai nei browser di oggi.
- Nessun timer con stringa, nessun URL `javascript:`, nessun import da `data:`/`blob:`. Script inline: tutti per hash
  (H-52). `wasm-unsafe-eval` resta per PDFium.
- **`connect-src`**:
  - F3, la sonda dell'indirizzo, la sola fetch su un'altra origine in managed. L'endpoint risponde già con CORS `*`;
  - il controllo degli aggiornamenti (`api.github.com`) gira solo in self-hosted.
- **Le build con copertura** (istanbul, `new Function('return this')` in ogni modulo, senza try/catch) si rompono con
  una policy applicata: le corsie con la CSP applicata girano senza `--coverage`.
- **Una build nuova senza riavvio** darebbe pagina bianca (hash vecchi). In managed non succede, l'immagine non cambia;
  in self-hosted da sorgente sì.

**Opzioni e raccomandazioni**:
- E1, l'interruttore: `LIBREFOLIO_CSP_ENFORCE` (bool, default spento; self-hosted invariato).
  - Acceso: le pagine HTML della web app ricevono `Content-Security-Policy` con la policy intera più gli hash (contiene
    le quattro direttive di `PAGE_POLICY`); doc e API HTML tengono `PAGE_POLICY`.
  - Report-only: non più mandato quando si applica (le violazioni non vanno segnalate due volte). In seguito potrà
    portare la prossima policy candidata, più stretta.
  - **Default in managed: decisione del developer** (proposta: acceso nel profilo managed, dopo un cloud smoke verde
    con la policy applicata).
- E2, F1: (a) una trasformazione di Vite limitata a cheetah-grid, `new Function("return this")()` → `globalThis`, così
  zero violazioni (consigliata; `vite.config.ts` è condiviso); oppure (b) un'eccezione documentata (la voce della
  baseline resta).
- E3, F3: (a) l'origine di `LIBREFOLIO_PUBLIC_URL` in `connect-src` (consigliata; un indirizzo diverso risulta «non
  verificabile», decide A per l'esperienza); (b) `connect-src 'self' https:`. Già oggi `img-src https:` permette di far
  uscire dati, e da una pagina https il mixed content blocca comunque `http:`. (c) Una sonda dal server: scartata,
  sarebbe SSRF da un admin-inquilino nel cloud.
- E4, gli hash con la policy applicata: un controllo di (mtime, size) dei file della build per ogni risposta HTML, in
  un thread, che li ricalcola se cambiano (consigliato); oppure solo all'avvio, con il riavvio documentato.
- E5, un endpoint per i report: nessuno (consigliato). Con `'report-sample'` i primi 40 caratteri uscirebbero.
- E6, self-hosted che accende la policy: `connect-src` aggiunge `https://api.github.com` quando il controllo degli
  aggiornamenti è attivo.

**Cosa deve provare l'E2E**:
- `TEST_LANE_SETTABLE` aggiunge `LIBREFOLIO_CSP_ENFORCE`;
- il cloud smoke con `--lane-setting LIBREFOLIO_PROFILE=managed --lane-setting LIBREFOLIO_CSP_ENFORCE=true`, senza
  copertura: verde, nessuna violazione ignota, F1 sparito se E2-a;
- AUSR-E-07 (A) prova di proposito altre origini http: su una corsia con la policy applicata le sue attese cambiano
  (lavoro di A);
- la fase 2 (`all-frontend` managed) nel cancello RC con la policy applicata.

**Dimensione**:
- H: impostazione, middleware, controllo nell'audit, nome di corsia, test, doc; ~3–4 h più uno slot.
- E2-a: ~1 h (Vite, più una scansione della build come guardia).
- E3: H per la policy, A per esperienza e test, ~1–2 h.

**Decisioni del coordinatore sulla CSP applicata** (21:45): GO per l'implementazione, con l'interruttore **spento ovunque**
(il default in managed va nella lista del developer, con la mia proposta).
- E1: `LIBREFOLIO_CSP_ENFORCE`; con la policy applicata niente report-only.
- E2 (b): eccezione documentata per F1; la trasformazione di Vite (a) dopo la 1.3.
- E3 (a): l'origine di `LIBREFOLIO_PUBLIC_URL` in `connect-src`, con A per l'esperienza e AUSR-E-07 (dopo A-57).
- E4: solo all'avvio, con il riavvio documentato. E5: nessun endpoint. E6: `api.github.com` mentre il controllo degli
  aggiornamenti è acceso.
- E2E: il nome in `TEST_LANE_SETTABLE`; un cloud smoke managed con la policy applicata, senza copertura; la fase 2
  applicata nel cancello RC.
- Ordine: prima H-54, poi la CSP applicata.

### Lotto «H-54: un file tolto da `src/` o da `static/` non si vede» (2026-10-17, 21:50) — analisi e passi

**Stato vero**: `check_frontend_needs_build()` confronta solo le date dei file che esistono. Gli input dei contratti
dei Tool hanno già l'impronta del loro elenco: `tool_contract_fingerprint()` è calcolata in `cmd_fe_build` **prima**
della build (`dev.py:712`) e registrata dopo una build riuscita (`record_tool_contract_inputs`, `:750`, nel marcatore
`frontend/build/.tool-contract-inputs`); `_tool_contracts_changed()` la confronta.

**Disegno** (niente `dev.py`, niente imbracatura dei test):
- l'elenco dell'impronta si allarga ai file di `frontend/src` e `frontend/static` che `_counts_for_the_build` conta, tolti i
  cataloghi generati (`generated_catalogs()`): `cmd_fe_build` li scrive dopo l'impronta, e su un clone nuovo
  costerebbero una ricostruzione in più. La loro presenza ha già un controllo suo;
- i file dell'API generati sono già fuori per nome (`_BUILD_GENERATED_SOURCES`); il font scaricato da
  `update_js_cache()` è prima dell'impronta;
- l'etichetta del formato passa a `tool-contract-inputs/2`: un marcatore del formato vecchio non corrisponde più,
  quindi una ricostruzione una volta dopo l'aggiornamento (la regola già scritta);
- i nomi delle funzioni restano (meno rimescolamento); docstring e doc dicono cosa copre l'elenco;
- senza marcatore (una build fatta da `npm run build` da solo) resta il ripiego di oggi.

**Passi**:
1. ✅ (21:34) Rossi (test-author, `files/runs/h54-reds.sh`): +67 test (`TestFrontendInputsListing`,
   `TestFrontendInputsRecorded`), `utils runtime-isolation` **29 failed / 425**, come previsto; ruff e black puliti.
   - Vincolo trovato da test-author: `_tool_contract_sources` deve restare dei soli Tool, perché alimenta anche il
     controllo delle date; quindi una visita a parte dentro `tool_contract_fingerprint`.
   - Caso limite non coperto: `favicon.png` (tracciato) cancellato a mano. La build lo ricrea dopo l'impronta: una
     ricostruzione in più.
2. ✅ (21:34) Cura `files/h54/apply_h54.py` (a secco, `--apply`, `cmp` OK): `_frontend_input_names()` e l'etichetta
   `/2`, più docstring e commento.
3. ✅ (21:38) Verdi: `utils runtime-isolation` **454/454**, `test-server-preparation` 91, `test-runner-cli` 766; ruff
   pulito. L'impronta sul checkout vero: 80 ms per 1014 file.
   - **Prova dal vivo** (`files/runs/h54-live.sh`): `dev.py server --test --build-only` ha ricostruito una volta (il
     marcatore era del formato vecchio). Poi il marcatore è uguale all'impronta attuale e la sonda risponde «fresca»;
     un secondo passaggio non ricostruisce. Niente ciclo.
4. ✅ (21:40) Doc (docs-writer): `test-walkthrough/front-overview.md` («Automated Setup»: l'elenco registrato copre
   anche `src/` e `static/`; senza marcatore, solo le date) e `dev_workflow.en.md` (passo 3). `i18n.md` era già giusta.
   `mkdocs build` stretto 0 avvisi, `check-links` 97 validi, `git diff --check` pulito.
5. ✅ (21:41) Checkpoint inviato (sotto).

### Lotto «H-55: la CSP applicata, `LIBREFOLIO_CSP_ENFORCE`» (2026-10-17, 21:55) — analisi

> Via del coordinatore (21:50, dopo l'entrata di H-54, dev `d6c252ec4`): «GO for the CSP-enforcement lot (E1–E6 as
> decided): analysis to reds». Il nit di B-43 (le frasi «such as `regexp`» in `security.md`) va nel giro di
> `security.md` di questo lotto, sopra il paragrafo B-49 appena entrato.

**Stato vero** (HEAD `d6c252ec4`):
- `LIBREFOLIO_CSP_REPORT_ONLY` e `LIBREFOLIO_FRAME_PROTECTION`: campi bool in `config/__init__.py`, default spenti, accesi
  in `PROFILE_DEFAULTS` managed; righe commentate in `.env.example` (r. 61–64); controlli
  `platform.frame_protection` e `platform.csp_report_only` in `config_audit.py` (chiavi i18n `instance.checks.*`,
  sottosistema `instance`, di H).
- `SecurityHeadersMiddleware`: a protezione accesa i documenti HTML ricevono `PAGE_POLICY` (applicata, H-42); con la
  report-only accesa le pagine della web app ricevono `report_only_policy(hashes)` (H-52), costruita una volta.
- Il controllo degli aggiornamenti: solo nel browser, solo con `selfHostedConfirmed()`, verso `api.github.com`; la sonda
  dell'immagine passa dal backend (stessa origine). `LIBREFOLIO_PUBLIC_URL`: `config/accounts.py::public_url()` (A).
- Riferimenti alla variabile: doc `settings.md`, `overview.md`, `security.md`, `test-walkthrough/{e2e,index,front-utility}.md`,
  admin `hosting_providers.en.md`, `settings.en.md`, `configuration.en.md` (le pagine admin con traduzioni: debito
  vero, nessun timbro); test `test_runtime_isolation.py`, `test_managed_headers.py`, `test_config_audit.py`.

**Disegno** (E1–E6 come deciso; i dettagli sono miei, nel perimetro):
- **E1**: `LIBREFOLIO_CSP_ENFORCE: bool = False`, **nessuna voce in `PROFILE_DEFAULTS`** (spento ovunque, decide il
  developer). Acceso, le pagine HTML della web app ricevono un secondo header `Content-Security-Policy`: la policy della
  web app con gli hash, **senza `frame-ancestors`**. I frame li decide sempre `LIBREFOLIO_FRAME_PROTECTION`, che resta
  com'è (`PAGE_POLICY` e `X-Frame-Options`), così applicare la CSP non accende di nascosto la protezione dai frame.
  - Il browser applica entrambe le policy (l'intersezione).
  - Niente header report-only quando si applica.
  - Restano invariati il 304, l'header di una rotta che lo mette da sé, `/mkdocs` e `/api/`.
- **E3 + E6**: `connect-src` aggiunge le sorgenti calcolate alla costruzione del middleware, nella report-only (che resta
  l'anteprima fedele) e in quella applicata:
  - l'origine di `LIBREFOLIO_PUBLIC_URL`, se c'è;
  - `https://api.github.com` nel profilo self-hosted, dove il controllo degli aggiornamenti può girare.
  - `report_only_policy(hashes, connect_sources=())`, con l'argomento nuovo facoltativo (H-52 resta valida), più
    `enforced_policy(...)`.
- **E2 (b)**: F1 resta una voce documentata della baseline (con la policy applicata cheetah-grid ripiega su `window`).
- **E4**: gli hash solo all'avvio; nella doc, «dopo una build nuova, riavvia».
- **E5**: nessun endpoint.
- **Audit**: un controllo `platform.csp_enforce`, ok acceso («applicata») e ok spento («solo segnalazione o nessuna:
  il default»). Due chiavi i18n in quattro lingue (sottosistema `instance`), la riga nel `.env.example` sotto la
  report-only.
- **Corsia**: `TEST_LANE_SETTABLE` += `LIBREFOLIO_CSP_ENFORCE`. `front-utility cloud-smoke` rifiuta `--coverage`
  quando la corsia applica la CSP: il preambolo di istanbul (`new Function`) si romperebbe.
- **E2E**: la spec del raccoglitore, su una corsia con la policy applicata, confronta l'header `Content-Security-Policy`
  della corsia (quello con `script-src`) con la sua copia più gli hash, senza `frame-ancestors`. AUSR-E-07 (A, dopo
  A-57) cambierà le sue attese. Uno slot per un cloud smoke managed con la policy applicata, senza copertura: finché A
  non adatta AUSR-E-07, quel test è il solo rosso atteso.
- **Doc**: `security.md` (una sezione sulla policy applicata, più il nit di B-43), `hosting_providers.en.md`,
  `configuration.en.md` e `settings.en.md` (admin, debito di traduzione), `settings.md`, `e2e.md`, `front-utility.md`,
  `index.md` (impostazioni di corsia).

**Passi**: 1. rossi (test-author: backend headers, config e audit, corsia; E2E del raccoglitore); 2. cura (script a
secco); 3. verdi leggeri; 4. doc; 5. slot (cloud smoke con la policy applicata); 6. checkpoint.

> **Stato al 17/10, 22:00**: il passo 1 (i rossi) era scritto e non ancora eseguito quando il developer ha fermato
> tutte le sessioni. Il coordinatore ha avuto subito la richiesta del controllo audit `cspReportOnly.enforced` (scelta
> 3) e l'ok sulle quattro scelte (17/10, 22:00).

> **⏸️ Sospeso il 19/10, 11:10** (ripartenza del coordinatore): H-55 è tra gli ampliamenti che il developer sta
> leggendo, interruttore della CSP compreso. Niente cura, niente verdi e niente slot fino al suo via.
> - I rossi, mai eseguiti, sono parcheggiati come patch nella cartella della sessione (`files/parked/`, file
>   `h55-csp-enforce-reds-on-d6c252ec4.patch`, sha256 `d912356d…fc88`), con una copia intera dei quattro file:
>   `test_config_audit.py` (+273), `test_managed_headers.py` (+542), `test_runtime_isolation.py` (+138) e
>   `csp-collector.spec.ts` (+695/−185).
> - Verifiche: `git apply --check --cached` prima, `git apply --check` dopo il ripristino; il risultato della patch su
>   HEAD è uguale byte per byte alle copie. Il worktree è tornato al commit, tranne questo piano.

> **⚠️ Fuori pista** (da rivedere alla ripresa, prima di ogni cura):
> 1. **Il rifiuto di `--coverage` poggia su una premessa sbagliata.** `vite-plugin-istanbul` crea l'instrumenter con
>    `coverageGlobalScopeFunc: false` e `coverageGlobalScope: "globalThis"`: il preambolo legge `globalThis` e non fa
>    `new Function`. Una build con la copertura dovrebbe quindi partire anche con la policy applicata, da misurare.
>    Ne dipendono:
>    - i casi del rifiuto in `test_runtime_isolation.py`;
>    - i due `skip` sotto copertura della spec E2E (test 7 e 8);
>    - la scelta 4, approvata dal coordinatore su quella premessa, che va riproposta.
> 2. **Un `LIBREFOLIO_PUBLIC_URL` non valido**: `public_url()` solleva `ValueError`, e il middleware si costruisce alla
>    prima richiesta. Proposta: registrarlo nel log e non aggiungere l'origine, come fanno gli altri lettori. Oggi
>    nessun test lo copre.
> 3. **Scelte dei test-author da confermare alla ripresa**:
>    - gli hash della build letti una volta sola anche con le due policy accese;
>    - accanto a un header report-only messo dalla rotta, la policy applicata si aggiunge lo stesso;
>    - l'ordine degli header: `PAGE_POLICY` prima, la policy applicata dopo.
> 4. **Segnalati dal test-author E2E**:
>    - `page.waitForFunction` (test 9) sotto la policy applicata potrebbe segnalare un `eval`: in quel caso, rimedio
>      con `expect.poll`;
>    - la rotta di `page-policy.spec.ts` sostituisce tutto l'header e così toglie la policy applicata: su una corsia
>      che applica, quella spec non la prova;
>    - la descrizione di `csp-collector` in `_frontend_utility.py` è da aggiornare.

### Ripartenza del 19/10: pulizia, contabilità, due analisi

> Regole nuove del coordinatore (19/10, 11:08), valide da ora:
> - nessuna decisione di prodotto da parte mia: ogni scelta che cambia ciò che l'utente vede, i numeri o i dati è una
>   domanda, con le opzioni e il mio consiglio;
> - si implementa solo dopo il suo via esplicito;
> - niente carichi pesanti senza uno slot.

- **Fase 1, pulizia ✅** (11:10): H-55 parcheggiato (note «Sospeso» qui sopra). Il coordinatore ha committato il giornale
  in `e48c7de39` e aggiornato la base a `36fe568e3`.
- **La review del fix di Z (`b5da2277d`)**: annullata dal coordinatore. La riparazione D″ esce per decisione del
  developer: resta solo la correzione del plugin.
- **Contabilità ✅** (11:20):
  - backlog: ✅ con i commit su H-43 (la fase 2 resta al cancello della RC), H-51, H-52 e H-54; H-47 ✅ solo il disegno,
    il codice resta aperto;
  - righe nuove: H-55 (sospesa) e H-56 (lo spegnimento non aspetta i compiti in background, nota di E);
  - §4: la colonna dello stato nei CP e la tabella dei lotti dopo i CP, con gli SHA d'ingresso.

#### Analisi: gli indici del DB (19/10, sola lettura) ✅

> La domanda del developer, testuale: «abbiamo creato vari index nel DB per aiutare le query, puoi verificare che servono
> tutte? o al contrario se ne servirebbero altre?»

**Come** (script e uscite nella cartella della sessione, `files/idx/`):
- un DB di test fresco nella corsia (`db populate --force --clean`, 8 s), revisione `011`: 44 indici, autoindex dei
  vincoli compresi;
- un giro in-process, senza server e senza porta, con un listener di SQLAlchemy:
  - 67 endpoint, 150 chiamate, 149 riuscite. Il 503 è il dataset `portfolio.asset_history` di AI Export: nei dati di
    prova c'è un asset in KRW senza cambio;
  - 1727 statement catturati, 192 distinti;
- `EXPLAIN QUERY PLAN` di ciascuno sulla copia intatta del DB;
- un «what-if»: gli indici candidati tolti su una copia, e i 191 piani confrontati;
- un volume sintetico su una copia (200 asset × 5000 giorni = 1 milione di prezzi): pesi (`dbstat`) e tempi;
- grep statici per i percorsi che il giro non tocca: suggerimento degli eventi, split, sentinella delle date, audit di E,
  scheduler.
- Il codice non lancia mai `ANALYZE` né `PRAGMA optimize`. I piani senza statistiche sono quindi quelli dei DB degli
  utenti.

**Doppioni esatti** (stesse colonne, stesso ordine; si toglie l'indice esplicito, il vincolo resta):

| Tabella | Si toglie | Resta | Nota |
|---|---|---|---|
| `price_history` | `idx_price_history_asset_date` | `UNIQUE (asset_id, date)` | il caso visto dal developer; il vincolo serve anche l'`ON CONFLICT` dell'upsert |
| `asset_provider_assignments` | `idx_asset_provider_asset_id` | `UNIQUE (asset_id)` | |
| `assets` | `uq_assets_display_name` (indice) | `UNIQUE (display_name)` | `001` crea sia il vincolo sia un indice con lo stesso nome |
| `brokers` | `ix_brokers_name` | `UNIQUE (name)` | |
| `users` | `ix_users_username` | `UNIQUE (username)` | |
| `users` | `ix_users_email` | `UNIQUE (email)` e `ux_users_email_lower` | nessuna query cerca l'email esatta; l'unicità senza maiuscole è già più forte |

**Prefissi a sinistra di un altro indice** (ogni query li sostituisce con l'indice più lungo):

| Tabella | Si toglie | Coperto da |
|---|---|---|
| `transactions` | `ix_transactions_broker_id` | `idx_transactions_broker_date (broker_id, date, id)` |
| `transactions` | `ix_transactions_asset_id` | `idx_transactions_asset_date (asset_id, date)` |
| `broker_user_access` | `ix_broker_user_access_user_id` | `UNIQUE (user_id, broker_id)` |
| `fx_conversion_routes` | `idx_route_base_quote`, `ix_fx_conversion_routes_base` | `UNIQUE (base, quote, priority)` |

**Senza lettori**:
- `ix_transactions_date`: ogni query sulle transazioni è filtrata per broker o per asset, per il controllo d'accesso;
  la sentinella delle date (`min`/`max`) usa `idx_transactions_broker_date`;
- `ix_fx_conversion_routes_quote`: la coppia si cerca sempre con la base. Solo l'audit di E fa un `GROUP BY quote`, su
  una tabella di poche decine di righe.

**Restano, e servono** (con chi li usa):
- `transactions`: `idx_transactions_broker_date` (21 statement: lista, riepilogo del broker, portafoglio, AI Export) e
  `idx_transactions_asset_date` (lotti, WAC, AI Export); `idx_transactions_asset_event` e `idx_transactions_related`
  (collegamenti e chiavi esterne);
- `asset_events`:
  - `idx_asset_event_asset_date` (grafici ed eventi);
  - `idx_asset_event_asset_type_date`: il giro non lo tocca, ma lo usano il suggerimento degli eventi
    (`event_suggestions.py:67`, asset + tipo + intervallo) e le ricerche per tipo;
  - `idx_asset_event_provider_assignment` (il `CASCADE` dalla tabella delle assegnazioni);
- `fx_rates`: tutti e due. `UNIQUE (date, base, quote)` serve l'upsert e le letture per data; `(base, quote, date)` serve
  gli intervalli di una coppia (613 esecuzioni nel giro). Unirli vorrebbe ricostruire la tabella: non lo propongo;
- `assets`: `ix_assets_identifier_isin` e `ix_assets_identifier_ticker` (ricerca, candidati BRIM);
- `broker_user_access`: `ix_broker_user_access_broker_id` (accessi del broker, chiave esterna);
- `account_tokens`: tutti e tre; gli autoindex dei vincoli `UNIQUE`; `ux_users_email_lower` (accesso per email).

**Verifiche**:
- What-if, togliendo tutti i 13 indici: 50 piani cambiano solo nel nome dell'indice scelto, nessuno peggiora (nessuna
  scansione nuova, nessun B-tree temporaneo in più, nessun indice automatico).
- Le chiavi esterne restano coperte: per ogni colonna figlia resta un indice che comincia con lei. Il controllo di
  SQLite su un `DELETE` del padre non diventa una scansione.
- **Il peso**: a 1 milione di prezzi la tabella occupa 69,3 MB e ciascuno dei due indici gemelli 24,7 MB.
  - Togliere il doppione ne libera circa il 21 % (da 118,7 a 94,0 MB): a 3 milioni di prezzi sono circa 75 MB.
  - Ogni prezzo scritto aggiorna un indice in meno, e il backup e Litestream copiano meno pagine.
  - `DROP INDEX` dura 9 ms.

**Indici mancanti: nessuno.** Nel giro nessuna tabella grande viene scansionata per intero, tranne un caso voluto: la
lista degli asset legge tutte le transazioni con un asset (`assets/crud.py:284`, «detenuto da me / da altri»), e un
indice non lo eviterebbe. Il costo sta invece nella **forma** di due query, che leggono tutto lo storico:
- **«L'ultima data per asset (o per coppia)» con `GROUP BY` e `max`.** Legge ogni voce dell'indice dell'asset fino alla
  data, e non salta all'ultima.
  - Misura: 143 ms per 200 asset su 1 milione di prezzi; 0,8 ms con un `max` scalare per asset nella stessa query, con
    le stesse 200 righe (verificato uguale).
  - Dove:
    - X: `assets/price_query.py:93`, `assets/period_changes.py:37` e `:44`, `assets/refresh.py:103`;
    - W: `brokers/summary.py:245`;
    - J: `pac_allocator/source/loaders.py:55` e `fx_quotes.py:34`;
    - H: `platform/scheduler/jobs.py:87` e `:102` (Z lavora anche sullo scheduler).
- **Le valute distinte dei prezzi** (`financial_math/portfolio/engine.py:134`, MF/J): legge ogni riga fino alla data.
  - 23,6 ms per 50 asset × 5000 giorni.
  - Un indice coprente `(asset_id, date, currency)` lo porta a 14 ms, ma pesa 25,6 MB per milione di prezzi: non ne
    vale la pena.

**Proposte** (domande per il developer, tramite il coordinatore; niente implementato):
- **P-IDX-1, una migrazione incrementale `0NN_drop_redundant_indexes`.**
  - Il numero è il primo libero quando si fa: dipende dal destino di 010 e 011 di Z (D″ esce).
  - `upgrade()`: `DROP INDEX IF EXISTS` dei 13 indici. `downgrade()`: li ricrea con le definizioni esatte
    (`IF NOT EXISTS`). Quelli unici non possono fallire, perché i vincoli restano.
  - I modelli si allineano in `db/models.py`, condiviso:
    - via `index=True` da `transactions.broker_id`, `transactions.asset_id`, `transactions.date`,
      `broker_user_access.user_id`, `fx_conversion_routes.base` e `fx_conversion_routes.quote`;
    - via gli `Index(...)` dei doppioni;
    - `unique=True, index=True` diventa `unique=True` per `users.username`, `users.email` e `brokers.name`.
  - Niente `VACUUM`: le pagine liberate tornano nella lista libera e si riusano. Il file si accorcia solo con un
    `VACUUM`, che riscriverebbe tutto il DB.
  - Test:
    - la migrazione su un DB usa e getta, in su e in giù;
    - l'unicità ancora applicata sui sei gemelli;
    - le chiavi esterne ancora coperte;
    - una guardia nuova in `db validate`: nessun indice uguale a un altro, o prefisso a sinistra di un altro, nella
      stessa tabella, autoindex compresi. Oggi `test_indexes` controlla solo che gli indici dei modelli esistano nel
      DB, ed è così che i gemelli creati dal SQL di `001` sono passati.
  - Taglia S, rischio basso.
- **P-IDX-2, un solo helper per «l'ultima data per asset/coppia»**, e i 9 punti sopra passati a lui. Nessun indice,
  risultati identici.
  - Proprietari: X, W, J e H.
  - Prima conviene misurarlo sui dati veri del developer (copia di lavoro, skill `real-data-copy`).
- **Opzioni**:
  - A) P-IDX-1 nella 1.3, P-IDX-2 dopo (**il mio consiglio**: il guadagno di spazio e di scrittura è sicuro, il rischio
    è basso);
  - B) nella 1.3 solo il doppione di `price_history`;
  - C) tutto dopo la 1.3.
- **Limiti**: il giro copre dell'import BRIM i doppioni (`idx_transactions_broker_date`, broker + data) e i candidati
  degli asset, non il parse. Non tocca lo scheduler, che ho controllato con grep (le due query in `jobs.py`, sopra), né
  il rischio, che legge prezzi e cambi da `market_series.py` e `assets/price_query.py`, come i grafici.

#### Analisi: i testi dei controlli d'istanza e le ancore della guida (19/10, sola lettura) ✅

> Il developer non ha capito l'avviso del reverse proxy («Le richieste passano da un reverse proxy di cui LibreFolio non
> si fida (X-Forwarded-For): i limiti per indirizzo del visitatore non si applicano…»). Chiede un testo più chiaro, che
> dica cosa significa e cosa fare, e un bottone «Guida» su ogni controllo, anche su quelli superati. L'interfaccia è di
> A: ci si accorda tramite il coordinatore.

**Stato vero**:
- I testi sono chiavi `instance.checks.*` nel sottosistema i18n `instance` (mio), in quattro lingue; quelli di A, B ed E
  stanno nei loro sottosistemi (`auth.checks.*`, `backup.checks.*`, `email.checks.*`).
- La scheda Sicurezza è di A (`features/settings/security/`). `securityFindings.ts` ha già una mappa per controllo,
  `SERVER_ACTIONS`, per i link dentro l'app («Apri la scheda Email», «Apri le impostazioni dei plugin»).
- Il frontend costruisce già link localizzati alla guida (`AboutTab.svelte`, `mkdocsUrl()`); i segnali e gli eventi
  tengono il percorso della pagina in una mappa del frontend (`docsPath`).
- La guida admin usa già ancore esplicite (`{: #client-address }`, `{: #security-passed }`…), stabili fra le lingue. Ma
  le sezioni scritte nella 1.3 ci sono **solo nelle pagine inglesi**: le traduzioni IT/FR/ES di `configuration`,
  `connection_checks` e `settings` sono indietro. Così un link localizzato oggi atterra in cima a una pagina che non ha
  la sezione. Fanno eccezione `#session-cookie` e `#reverse-proxy` (`connection_checks`) e `#session-persistence`
  (`index`), presenti in tutte e quattro.
- Perché il testo non si capisce: «di cui non si fida», «header di inoltro» e «limiti per indirizzo del visitatore» sono
  gergo; la conseguenza non è detta in parole semplici; l'azione (dove si scrive la variabile, quale valore) non c'è.

**Proposta di testo** (EN, la fonte, e IT; FR ed ES all'implementazione):

| Chiave | EN | IT |
|---|---|---|
| `clientAddress.untrustedProxy` (⚠️) | Some requests reach LibreFolio through a proxy it was not told about (it sent {headers}). LibreFolio therefore sees every visitor behind it with the same address, and cannot slow down someone who tries many passwords, or asks for many emails, from one address: for those requests only the limits per account and per email address still apply. To fix it, add the proxy's address to FORWARDED_ALLOW_IPS in the .env file (with Docker, the proxy's network, such as 172.18.0.0/16), then restart LibreFolio. No proxy of yours in front of LibreFolio? Then there is nothing to do. | Alcune richieste arrivano a LibreFolio attraverso un proxy che non gli è stato indicato (ha inviato {headers}). Così LibreFolio vede tutti i visitatori dietro di lui con lo stesso indirizzo, e non può frenare chi prova molte password, o chiede molte email, da uno stesso indirizzo: per quelle richieste restano solo i limiti per account e per indirizzo email. Per sistemare, aggiungi l'indirizzo del proxy a FORWARDED_ALLOW_IPS nel file .env (con Docker, la rete del proxy, per esempio 172.18.0.0/16), poi riavvia LibreFolio. Davanti a LibreFolio non hai un tuo proxy? Allora non c'è nulla da fare. |
| `clientAddress.publicForwarding` (ℹ️) | Some requests from the internet carried proxy headers ({headers}), and LibreFolio ignored them, as it should. If your own proxy has a public address, add it to FORWARDED_ALLOW_IPS in the .env file and restart; otherwise there is nothing to do: a visitor's browser, or a proxy of their own, can add these headers. | Alcune richieste da internet avevano intestazioni da proxy ({headers}), e LibreFolio le ha ignorate, com'è giusto. Se il tuo proxy ha un indirizzo pubblico, aggiungilo a FORWARDED_ALLOW_IPS nel file .env e riavvia; altrimenti non c'è nulla da fare: il browser di un visitatore, o un suo proxy, può aggiungere queste intestazioni. |
| `clientAddress.ok` (✅) | Since the last start, no request has arrived through a proxy LibreFolio does not know about. | Dall'ultimo avvio nessuna richiesta è arrivata da un proxy che LibreFolio non conosce. |

- Il testo nomina solo `FORWARDED_ALLOW_IPS`, la cura del caso comune. L'altra strada, `LIBREFOLIO_CLIENT_IP_HEADER`
  (proxy che scrivono un header proprio, come Fly.io), resta nella guida dietro il bottone.
- `ok` non promette «ogni visitatore ha il suo indirizzo»: un proxy che non manda nessuna intestazione non si vede.
- Lo stesso difetto, cioè nessuna azione nel testo, c'è in altri due testi, su cui propongo una frase in più:
  - `sessionCookie.never`: «Set SESSION_COOKIE_SECURE back to auto, unless your proxy really needs never.» / «Rimettilo
    su auto, a meno che il tuo proxy non abbia davvero bisogno di never.»;
  - `jwtSecret.ephemeral`: «To keep users signed in, set JWT_SECRET to 32 or more random characters.» / «Per tenerli
    collegati, imposta JWT_SECRET con almeno 32 caratteri casuali.».
- Variante V2, da decidere: ogni messaggio non `ok` diviso in due chiavi, cosa significa (`…`) e cosa fare
  (`…Action`), e A mostra «Cosa fare» su una riga sua. È più leggibile, ma cambia lo schema per tutti i controlli,
  compresi quelli di A, B ed E.

**Le ancore del bottone «Guida»** (una per controllo, uguale per ogni stato, superato compreso):

| Controllo | Pagina e ancora | Lingue |
|---|---|---|
| `platform.jwt_secret` | `admin/configuration/#secrets` | solo EN |
| `platform.secrets_set_twice` | `admin/configuration/#secret-files` | solo EN |
| `platform.instance_key` | `admin/configuration/#instance-key` | solo EN |
| `platform.session_cookie` | `admin/connection_checks/#session-cookie` | 4 |
| `platform.client_address` | `admin/connection_checks/#client-address`; meglio un'ancora nuova `#untrusted-proxy` sul paragrafo «When LibreFolio does not trust your proxy», che oggi è solo grassetto | solo EN |
| `platform.frame_protection` | **ancora nuova** `admin/configuration/#frame-protection` (oggi è solo una riga di tabella) | — |
| `platform.csp_report_only` | **ancora nuova** `admin/configuration/#csp-report-only` | — |
| `platform.log_level`, `platform.test_mode` | `admin/configuration/#startup-checks` | solo EN |
| `platform.plugin_secrets` | `admin/configuration/#plugin-secrets` | solo EN |
| `backup.panel_token` | `admin/hosting_providers/#panel-token` | pagina solo EN |
| `backup.upload_limit`, `backup.restore_limit` | `admin/hosting_providers/#restore-upload-limit` | pagina solo EN |
| `accounts.login_limit` | `admin/configuration/#login-limit` | solo EN |
| `email.smtp` | `admin/email/#variables` | pagina solo EN |
| `email.smtp_encryption` | `admin/email/#encryption-modes` | pagina solo EN |
| `email.links` | `admin/email/#links-check` | pagina solo EN |
| la registrazione aperta (dal browser) | `admin/settings/#open-registration-warning` | solo EN |

**Domande** (per il developer, tramite il coordinatore):
1. **Il testo**: V1, i tre testi sopra più le due frasi in più (**il mio consiglio**), oppure V2, il «Cosa fare» su una
   riga sua per tutti i controlli.
2. **La lingua dei link «Guida»**, finché le pagine admin non sono tradotte:
   - L1: la pagina nella lingua dell'app. Funziona dopo una traduzione delle pagine admin; prima atterra in cima a una
     pagina vecchia;
   - L2: sempre la pagina inglese, poi L1 dopo la traduzione.
   - **Il mio consiglio**: L1 se la traduzione delle pagine admin è prevista per la 1.3, altrimenti L2. Più un test
     che fallisce se l'ancora di un controllo manca nella pagina che il link apre.
3. **Dove sta la mappa** (da decidere con A):
   - a) nel frontend, accanto a `SERVER_ACTIONS`, con un test Vitest che legge le pagine `.en.md` e verifica ogni
     ancora. È lo schema che la scheda usa già e non cambia l'API (**il mio consiglio**);
   - b) un campo nuovo nella risposta di `GET /security/checks`, scritto da chi possiede ogni controllo (H, A, B, E):
     cambio di schema e `api sync`.

**Lavoro di H, se approvato** (piccolo):
- i testi nelle quattro lingue (`instance/<lang>.json`);
- le tre ancore nuove (`#untrusted-proxy`, `#frame-protection`, `#csp-report-only`), con il docs-writer: in inglese, e
  nelle traduzioni, dove la sezione c'è già, solo la riga dell'ancora;
- la tabella della scheda Sicurezza in `settings.en.md`, con le parole nuove;
- se si sceglie b), il campo in `ConfigCheck`.
- A fa il bottone, il link e il suo test.
