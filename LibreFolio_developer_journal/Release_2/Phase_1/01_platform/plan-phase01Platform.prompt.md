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

| CP | Contenuto | Sblocca | Dipende da |
|---|---|---|---|
| CP1 | **Rinomina** (`git mv`) verso `services/platform/` e `services/files/`, più gli import, le patch dei test, le stringhe del runner, `coverage_analysis.py:71`, la doc per sviluppatori, la mappa in `backend.instructions.md` e le tabelle delle fonti della wiki (17 pagine, 35 citazioni) | Z (scheduler), B (backup), percorsi stabili per tutti | niente (né il commit del coordinatore su `main.py` né npm) |
| CP2 | **Taglio di `main.py`**: lifecycle, database_bootstrap, middleware, static_site. Configurazione unica (pacchetto `config/`, D2) con le letture spostate e la guardia su `os.environ`. Patch dei test su `lifecycle` con `raising=True` | A, Z, B, X (agganci senza toccare `main.py`, sezioni di config) | il commit del coordinatore su `main.py` + aggiornamento di base |
| CP3 | **Segreti (F03)**: sorgente `_FILE`, `JWT_SECRET_FILE` (e `dev.py`), `instance_key`, `config_audit` nei log, `.env.example` completo e a sezioni con la guardia «ogni variabile è in `.env.example`», doc admin (configuration, filesystem) | B, X (chiave), E | CP2 |
| CP4 | **Config pubblica e avvisi**: due endpoint, `features/instance/`, layout, interceptor, i18n, Vitest, `api sync` | A (login, link), Z, X | CP3; `npm ci` approvato |
| CP5 | **Prontezza e versione (F08)**: `/system/ready`, `/system/info` minimo senza sessione (D14 modificata), R2, C-84. CP5a backend, CP5b frontend | pannello di controllo | CP2a |
| CP6 | **Blocco dell'istanza (D4)**: variabili, guardia sul router v1 con un elenco corto di permessi, `/system/block`, pagina di blocco; (C) `JWT_SECRET` corto fatale nel profilo gestito; pagina admin per gli hoster | il pannello del cloud (blocco) | CP4, CP5 |
| CP7a | **Lotto Docker**: P-4, M-25, C-37, N-8, 32-3, istruzioni per C-26. Poi i file Docker passano a B | B (Litestream) | Docker acceso; anticipabile subito dopo CP3 |
| CP7b | **Lotto HTTP**: cache di `/_app` (F28), default di 60 s nel profilo gestito (F27), header con CSP in sola segnalazione (F15) | — | CP6 |
| TS1 | Decisione sui test speculari, con i numeri (§13) | — | riordino del backend finito |

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
