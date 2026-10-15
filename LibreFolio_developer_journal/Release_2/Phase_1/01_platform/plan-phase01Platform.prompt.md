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

- **Endpoint**:
  - `GET /system/ready`: 200 se il DB risponde e la revisione è uguale alla head (calcolata una volta e messa in
    cache); altrimenti 503 con i motivi;
  - `GET /system/version`: `get_version_info()`.
- **R2**:
  - `get_git_version()`: se esiste `.git` (file o cartella) vince `git describe`; `VERSION` vale solo senza `.git` o se
    `git describe` fallisce; altrimenti `unknown`;
  - `dev.py` e la CI continuano a scrivere `VERSION` per l'immagine, che non ha `.git`;
  - `test_version.py:96` va riscritto.
- **C-84** (D6):
  - proposta: `0.0.0` con un commento in `pyproject.toml`; `0.0.0` in `package.json` e nelle due righe radice di
    `package-lock.json`;
  - alternativa: allinearle a ogni rilascio.
- **Facoltativo**: `/metrics` in formato Prometheus scritto a mano, nessuna dipendenza.
  - Spento di default (`LIBREFOLIO_METRICS_ENABLED=0`); token facoltativo con `_FILE`.
  - Contenuto: richieste per classe di stato, job dello scheduler (da `scheduler_state.json`), ultimo aggiornamento
    dei prezzi, dimensione del DB.
- **`/system/info`** oggi è pubblico ed espone le versioni delle dipendenze e dell'OS. Proposta D14: dietro login. Lo
  usano solo pagine con sessione (Informazioni, changelog, layout dell'admin); la versione resta pubblica su
  `/system/version`. Va adattato `test_system_api`.

### 3.6 Profilo gestito e sola lettura (F05, parte H)

- `LIBREFOLIO_PROFILE=selfhosted|managed` risolve i default.
- Middleware ASGI `read_only`, default-deny per i metodi di scrittura sotto `/api/v1`:
  - il middleware gira prima del routing, e FastAPI mette `scope["route"]` solo durante il matching
    (`fastapi/routing.py:836`). Per questo cerca da sé la rotta con `route.matches(scope)`, solo per i metodi di
    scrittura, e confronta metodo e template con una allow-list centrale;
  - risposta 403 `{"detail": "<testo EN>", "code": "instance_read_only"}`;
  - lo scheduler non passa da HTTP, quindi continua a scrivere i prezzi.
- **Guardie**:
  - ogni voce dell'allow-list deve esistere fra le rotte di `app`;
  - ogni rotta di scrittura deve stare in una delle due liste, permesse o bloccate. Chi aggiunge una scrittura la
    classifica nel suo lotto, e intanto resta bloccata.
- **Bozza dell'allow-list**, 32 permessi e 38 bloccati su 70 (decisione §10 n. 1):

| Permessi | Endpoint |
|---|---|
| Accesso | `POST /auth/login`, `/auth/logout`, `/auth/change-password` (D4) |
| Preferenze personali | `PUT /settings/user` (lingua, tema, valuta base, avatar); onboarding ×4 (`complete`/`skip` di flusso e passo) |
| Admin senza dati | `POST /settings/cache/clear-all`, `/settings/cache/clear/{name}` (D4) |
| Letture via POST | `/ai-export/snapshot`; `/portfolio/{wac,allocation-source,report,lots/analysis}`; `/risk/{query,eligibility}`; `/signals/preview`; `/tools/compute`; `/transactions/{validate,events/suggest,promote-suggest}` (`validate` fa sempre rollback); `/brokers/import/{sets/preview,duplicates,asset-candidates,gap-fix}` (`gap-fix` calcola soltanto, verificato); `/assets/prices/query`; `/assets/events/query`; `/fx/currencies/convert`; `/assets/provider/probe` (prova senza salvare, verificato) |
| Dati di mercato | `POST /assets/prices/current` (scrive la barra del giorno, C-83) |
| Export | `POST /backup/export` |
| **Bloccati** | creazione, modifica e cancellazione di asset, broker, accessi, prezzi, eventi, cambi, rotte, transazioni (commit, promote), upload, import (upload, parse, delete, combine), restore, impostazioni globali, registrazione, profilo, cancellazione dell'account; sync manuali di prezzi e cambi e refresh dei provider (D4) |

- **Frontend**: avviso non chiudibile «istanza in sola lettura» nell'area avvisi; toast tradotto sulle scritture
  rifiutate. Disattivare i pulsanti pagina per pagina resta alle sessioni proprietarie, che hanno un `isReadOnly()`.
- **Default `managed`** proposti: idle dei worker di rischio 60 s (F27), CSP in sola segnalazione e frame-ancestors
  `'self'` accesi (D5); popup di donazione spento (decide A).

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
| CP5 | **Prontezza e versione (F08)**, C-84, R2, `/system/info` dietro login (D14); `/metrics` se D9 | pannello di controllo | CP2 |
| CP6 | **Profilo e sola lettura**: `PROFILE_DEFAULTS`, middleware, allow-list e guardia, avviso e toast, pagina admin «profilo gestito per gli hoster» | A e X (default del profilo) | CP4 |
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
- **CP5**: `system.py`, `database_bootstrap.py`, `utils/runtime/version.py`, `test_version.py`, `pyproject.toml`,
  `frontend/package.json` e `package-lock.json` (radice).
- **CP6**: `read_only.py`, `middleware.py`, `config.py`, `features/instance/**`; doc admin (pagina nuova) e sviluppatori.
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
