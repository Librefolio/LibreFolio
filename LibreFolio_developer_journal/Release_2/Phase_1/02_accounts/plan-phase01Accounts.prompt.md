# Piano — fase 01, sessione A: account e accessi (1.3.0)

> - **Sessione**: «A - Account e accessi», ramo `e-alfy-a-account-e-accessi`, worktree
>   `LibreFolio-worktrees/e-alfy-legendary-winner`, corsia 6182 con `/tmp/librefolio-r13-a`.
> - **Coordinatore**: «Release 1.3 planning» (`928ffa97-f0c3-4975-a442-3de0c2c20fc7`).
> - **Piano generale**: [`plan-phase01Release13.prompt.md`](../plan-phase01Release13.prompt.md), §4 «A · Account e
>   accessi», §6, §7. **Decisioni**: [`decisioni-analisi-20261014.md`](../decisioni-analisi-20261014.md), §2
>   «Account e accessi».
> - **Stato**: A1 (CP1) consegnato, FROZEN in attesa del commit del coordinatore; i lotti dopo aspettano il suo via
>   (§15–§17).
>
> Le sezioni 0–13 sono l'analisi consegnata il 14/10, con le correzioni del §14: restano come cronaca. Dove le
> decisioni del developer (§15) e le dipendenze confermate (§16) la cambiano, valgono queste.

## Autorizzazione (14/10/2026, ~22:55)

- **Analisi** consegnata al coordinatore il 14/10, poi la correzione di D-A1 (§14). Sessione FROZEN fino
  all'autorizzazione.
- **Chi ha approvato**: l'approvazione del piano nella sessione A l'ha data il coordinatore 1.3, su delega esplicita
  del developer; non è un'approvazione diretta del developer.
- **Parole del developer, alla lettera** (inoltrate dal coordinatore): «chat, sto leggendo
  LibreFolio_developer_journal/Release_2/Phase_1/decisioni-analisi-20261014.md — ho appena finito le prime 11
  domande e sto iniziando piattaforma, ma ho già messo varie note dev, leggi intanto quelle, vedi se con quelle
  risposte devi aggiornare quello che viene dopo e poi vedi tu se aspettare che leggo tutto, o intanto grazie a queste
  riesci ad avviare qualche lavoro»
- **Decisione del coordinatore** su quella delega, alla lettera: «parte SOLO il tuo primo checkpoint, che è riordino
  puro. Il resto del piano aspetta le risposte del developer ai punti aperti qui sotto: il via te lo do io.»
- **Perimetro**, alla lettera: «SOLO A1 = CP1. `git mv` dei 6 servizi in `services/accounts/` con lo stesso nome (~80
  righe d'import), nessun cambio di comportamento. Primo treno: H CP1 → X CP1 → A A1; entri per terzo: i conflitti con
  H su `main.py:58`, `services/scheduler/settings.py:11` e `api/v1/uploads.py:39` li risolvi tu all'aggiornamento di
  base.»
- **Base**: `c9bb8f257643c0b770788033789425b41ba16715`, portata dal coordinatore in fast-forward da `459131eb8`
  (solo journal, `scripts/visual_review/gallery_snapshot.sh`, `TODO_FUTURI.md`). Verificata: HEAD = base, worktree
  pulito.
- **Regole di lavoro** del messaggio:
  - niente commit, merge, rebase, stash o reset;
  - a ogni checkpoint handoff con purpose `handoff`, poi FROZEN;
  - solo la corsia 6182;
  - `npm ci` dal lock permesso (C5), da fare prima della prima run di test;
  - finestra della galleria il 15/10 dalle 09:00, circa 2 ore: nella corsia niente suite complete né build pesanti.

## 0. Contesto verificato

- Worktree `LibreFolio-worktrees/e-alfy-legendary-winner`.
- Ramo `e-alfy-a-account-e-accessi`: l'app l'ha rinominato all'avvio della sessione (era `e-alfy-legendary-winner`), stessi commit.
- HEAD `459131eb86a2810fba9a4f78b230e25f97223fbc` = base `dev_release2` ✓, worktree pulito (riverificato in serata: invariato).
- Corsia 6182, `/tmp/librefolio-r13-a`: nessun test né server lanciato.
- Coordinatore `928ffa97-f0c3-4975-a442-3de0c2c20fc7`.
- Letti:
  - le istruzioni del progetto e quelle di backend, DB, schemi, frontend, AI e AI Export del frontend; la skill `ai-export-probe-tuning`;
  - il piano 1.3 (§2–§10) e il README della fase 01;
  - del piano 43: P2, §1.3, §4, §7.2–7.5;
  - il backlog (21-5, C-54) e il backlog 38 (K-5, O-15, K-17, L12);
  - in `TODO_FUTURI`: 🔑 Sessioni, 📧 Email, 🔐 OIDC;
  - la specifica SaaS (F02, F05, F09, F13, F15), in sola lettura.
- devWiki: il grafo non si può usare. Lette a mano: `domains/auth`, `domains/layout-settings`, `features/F-002`, `problems/login-account-enumeration-before-password`, `decisions/automatic-popups-wait-for-guides`.

## 1. Stato reale (codice a `459131eb8`)

| Tema | Oggi |
|---|---|
| Servizi account | 6 file in cima a `services/`: `auth_service` 151 righe, `user_service` 476, `settings_service` 295, `global_settings_service` 105, `onboarding_service` 407, `donation_popup_service` 102. Nessuno supera le 1 000 righe → **basta la rinomina, nessun taglio** |
| Chi li importa | **App, 13 file**: `api/v1/{auth,users,settings,brokers,uploads}.py`, `main.py:58`, `services/scheduler/settings.py:11`, `lots_analysis_service.py:41`, `portfolio_service.py:106`, `financial_math/portfolio/engine.py:28`, più gli import interni.<br>**Script**: `user_cli.py`, `coverage_analysis.py`, `test_runner/_backend_services.py`.<br>**Test**: 21 file; la guardia `test_layer_boundaries.py:16,167` nomina `settings_service`.<br>**Doc**: 9 pagine developer (~24 righe), 3 file `.github`, 24 pagine della devWiki |
| Primo utente admin (F02, K-5) | `auth.py:206-239`: `is_first_user` (`:214-215`) vince su `enable_registration` (`:217-218`) e dà `is_superuser` (`:227`).<br>`LoginCard.svelte:109` nasconde «Registrati» quando la registrazione è chiusa, e non sa se esistono utenti.<br>REG-007 (`test_auth_api.py:202`) fissa questo comportamento |
| Registrazione | Solo il valore sì/no `enable_registration` (`schemas/settings.py:288`, `:549`). Si legge senza login da `GET /settings/global`, aperto a tutti |
| Gestione utenti | `users.py` ha solo `GET /users/search`; il resto passa dalla CLI. `dev.py user create` crea sempre un admin (`user_cli.py:372`, documentato).<br>Le guardie sull'ultimo admin attivo esistono già (`set_user_active`, `set_user_admin`, `DELETE /auth/users/me`) |
| Reset della password | Solo da CLI. `user_service.py:205` calcola l'hash nel loop, senza `to_thread`. `ForgotPasswordCard` mostra i comandi docker e CLI |
| Sessioni | JWT `sub`/`iat`/`exp` nel cookie `session` (`auth_service.py:108`, `:130`).<br>`get_current_user` (`auth.py:77`) controlla firma, scadenza, utente e `is_active`. Nessuna revoca: un cambio o un reset della password non chiude le sessioni aperte (`user_service.py:210`) |
| Limite dei tentativi di login | Assente: nell'app non c'è nessun 429 |
| Donazioni | Il popup lo decide il backend al login. Si spegne solo con `LIBREFOLIO_DISABLE_DONATION_POPUP`, nascosta per scelta del fondatore (`donation_popup_service.py:39`).<br>Il link «Buy me a coffee» sta in `routes/+page.svelte:116`, `Header.svelte:242`, `HelpMenu.svelte:23` e nella card di About |
| Aggiornamenti | `features/update-check/`. Le modali `UpdateAvailableModal` e `AskAdminModal` stanno in `components/auth/`. Il controllo parte da `routes/(app)/+layout.svelte:150` |
| Disclaimer, footer | Assenti. In fondo alla sidebar ci sono avatar, logout, indicatore di connessione e versione (`Sidebar.svelte:227-280`) |
| AI Export | Il prompt lo costruisce `promptRenderer.ts:343` (`buildAiExportPrompt`), con sezioni dall'id fisso. L'ordine delle sezioni è fissato da `promptRenderer.test.ts:20` e `:121` |
| Frontend | `components/auth` 10 file, `components/settings` 17+8, `components/support` 9: in tutto 44 file.<br>Le 4 schede di Impostazioni sono scritte a mano in `routes/(app)/settings/+page.svelte`, che usa ancora `$:` |
| Migrazioni | La head è `004_release_1_2_0_schema`.<br>⚠️ `PRAGMA foreign_keys=ON` vale per ogni engine (`db/session.py:49-52`): un batch-recreate di `users` cancellerebbe a cascata il progresso dell'onboarding |
| Proxy e IP | uvicorn 0.52.4.<br>`utils/runtime/network.py:client_address` è solo consultivo (indicatore di connessione).<br>Il Docker gira con un solo worker; `dev.py --workers N` ne avvia di più |

## 2. Voci già fatte, contraddette o da sapere

- **O-15**: **in parte contraddetta**.
  - `auth.ts:143` mostra davvero `error.message` di axios.
  - Ma `auth.serverUnreachable` è una coppia {title, body} pensata per il controllo della sessione («non sei stato disconnesso»): al login non si adatta. Serve una chiave nuova, nelle 4 lingue.
  - Già che ci sono, mappo anche il 429 nuovo.
- **K-5**: confermata, ed è fissata da REG-007. Si chiude con F02 e con il flag pubblico `setup_required` (§4.7).
- **K-17**: confermata (`PasswordInput.svelte:47`).
- **L12**: confermata in `_frontend_common.py:192`. Lo stesso difetto c'è anche in `frontend/e2e/global-setup.ts:76`, che il backlog non cita.
  - Su un DB popolato non morde: `populate_mock_data.py:480-493` crea già quegli utenti con il ruolo giusto.
  - Morde su un DB vuoto.
- **21-5**: confermata. Non esiste né un'API né un comando CLI.
- **🔑 Sessioni**: confermata. Il developer il 09/10 aveva scritto «ci devo pensare»; il piano 1.3 approvato la mette nel perimetro di A. **Chiedo conferma esplicita.**
- **Deriva della devWiki**, da segnalare allo storico:
  - `domains/auth.md` dice che gli admin gestiscono gli utenti dalla UI, ed è falso (F-002 lo aveva già corretto);
  - `domains/layout-settings.md` cita «un footer con il ticker», che non esiste;
  - `backend.instructions.md` dice «First user = automatic admin»: va aggiornato con F02.
- **Da sapere**:
  - `GET /settings/global` è leggibile senza login (scheduler, TTL e il resto). Fuori dal mio perimetro: lo segnalo soltanto.
  - Il ramo A modifica una riga d'import in file di H, W e J (§6).

## 3. Superfici

### 3.1 Backend

- **Spostati**: i 6 servizi in `services/accounts/`.
- **Nuovi**, nello stesso stile dei 6 spostati: `accounts/{token_service,invite_service,registration_service,bootstrap_admin_service,account_config,login_throttle}.py`. I contributi di A alla configurazione pubblica e agli avvisi seguono il meccanismo che sceglie H.
- **Modificati**:
  - `api/v1/auth.py`: setup, registrazione con invito, consumo del reset, 429, cookie riemesso dopo il cambio di password;
  - `api/v1/users.py`: endpoint admin, inviti, link di reset, reset dell'onboarding;
  - in `api/v1/settings.py`, la parte globale: il blocco da variabile d'ambiente; `require_admin` passa in `auth.py`;
  - `schemas/{auth,users,settings}.py`;
  - `db/models.py`: le colonne di `User` e `AccountToken`;
  - `alembic/versions/005_*`;
  - `scripts/user_cli.py`: `create --role`, `setup-link`, `invite`, `reset-link`, `reset-onboarding`, `revoke-sessions`; `reset` alza la versione della sessione.

### 3.2 Frontend

- **Cartelle nuove**:
  - `lib/features/auth/components/`: Login, Register e Forgot spostati; Setup, InviteRegister e ResetPassword nuovi; `authErrors.ts`;
  - `lib/features/settings/{components,tabs}/` e `settingsTabs.ts` (il registro), più la scheda nuova `UsersTab`;
  - `lib/features/support/`: social, share e `DonationPopupModal`;
  - `lib/features/legal/` (nuova): `LegalNotice` e `LegalLinks`;
  - `UpdateAvailableModal` e `AskAdminModal` → `features/update-check/components/`.
- **Rotte**: `routes/+page.svelte` (login), `routes/(app)/settings/+page.svelte`; nuove: `routes/setup/`, `routes/invite/`, `routes/reset-password/`.
- **Componenti condivisi**: `ui/input/PasswordInput.svelte` (K-17), `stores/app/{auth,globalSettings}.ts`.
- **Righe nei file degli altri**:
  - onboarding: `DeferredAppPopups.svelte` e `WelcomeForm.svelte` (+2 `vi.mock`); il disclaimer in `WelcomePage`;
  - AI Export: `promptRenderer.ts` (la sezione legale).

### 3.3 Test

- **Backend**, test da adattare:
  - `test_api/test_{auth,settings,account_deletion,users_search,cache_admin,scheduler,portfolio_api,portfolio_wac,broker_access,http_compression,pac_planner_tool}_api.py`;
  - `test_services/test_{user_profile,settings_service,global_settings_service,donation_popup_service}.py`;
  - `test_db/{populate_mock_data,test_db_referential_integrity,test_post_migration}.py`, `conftest.py` (il ripristino della registrazione), la diagnostica dell'AI Export.
- **Backend**, test nuovi: token, registrazione, admin di bootstrap, limite dei tentativi, API admin degli utenti, migrazione 005.
- **Frontend**, test che si spostano con i loro componenti: 17 file Vitest (19 sono le occorrenze dei loro percorsi nel runner: `PreferencesTab.test.ts` compare 3 volte). In più gli `vi.mock` dell'onboarding e `clipboardSink.gate.test.ts`.
- **Frontend**, test nuovi:
  - Vitest per il registro, la scheda Utenti, le pagine pubbliche, `PasswordInput`, `authErrors`, i link legali e il renderer;
  - E2E per invito → registrazione, link di reset, azioni admin, registrazione per modalità.

### 3.4 Doc (EN, docs-writer)

- **Admin**:
  - `admin/{configuration,settings,service_exposure,cli_tools}`;
  - una pagina nuova, `admin/users`: modalità di registrazione, inviti, link di reset, limite, admin iniziale, reset dell'onboarding.
- **Utente**: `user/{getting-started,settings/profile}`, `community/faq`.
- **Developer**:
  - `architecture/{access_control,security,settings,database/users_access,users_and_brokers}`;
  - `frontend/components/features/{auth,settings}`, `frontend/onboarding`;
  - `backend/financial_math`, per il percorso di `settings`;
  - `architecture/patterns/ai_export_composition`, per la sezione legale.

### 3.5 Condivise (le scrive chi indica il coordinatore)

- **Runner**:
  - `_frontend_utility.py`: 19 percorsi;
  - `_backend_services.py`: i `print_info`;
  - `_backend_api.py:757`: il testo di `exclusive_because`;
  - `_frontend_common.py:192` (L12);
  - le voci nuove.
- `frontend/e2e/global-setup.ts:76` (L12).
- `scripts/coverage_analysis.py:58-70`, `:179-180`.
- In `.github`:
  - `backend.instructions.md`;
  - `frontend.instructions.md`;
  - `financial-math.instructions.md`;
  - `backend-testing.instructions.md:210` e `test-author.agent.md:228`, perché citano `enable_registration`;
  - le skill `onboarding-guide` e `lint-format-backend`.
- **Altro**: `.env.example` (la sezione di A), `mkdocs.yml` (la nav), CHANGELOG, la galleria (G).

## 4. Disegno proposto

### 4.1 Riordino del backend

- `git mv` dei 6 servizi in `services/accounts/` **con lo stesso nome** (`auth_service.py`, `user_service.py`, `settings_service.py`, `global_settings_service.py`, `onboarding_service.py`, `donation_popup_service.py`): cambia solo il pacchetto (D-A1, corretta). Il corpo del codice non cambia; cambiano solo ~80 righe d'import.
- Solo import diretti: niente shim, niente barili. `__init__.py` contiene solo la docstring.
- Le patch dei test puntano agli oggetti modulo nuovi.
- Il grep dei vecchi percorsi deve dare zero in `backend/`, `scripts/`, `.github/`, `mkdocs_src/docs/developer/`.

### 4.2 Riordino del frontend e registro delle schede

- `git mv` dei 44 file di §3.2, con import e `vi.mock` riscritti sui percorsi nuovi.
- Niente barili per i moduli che i test prendono con `vi.mock` (D-P4).
- `stores/app/donationPopupStore` resta dov'è: lo importa `stores/app/auth.ts`, e spostarlo romperebbe la regola dei livelli.
- **Registro delle schede**, `features/settings/settingsTabs.ts`. Ogni scheda è un oggetto:
  `{id, labelKey, icon, order, component, visible(ctx), props(ctx), alignEnd}`.
- La pagina diventa un runtime Svelte 5. Restano invariati `?tab=`, `settings-tab-{id}` e le 4 schede di oggi.
- B e X aggiungono la loro scheda con una riga, o due se serve anche l'import.

### 4.3 Migrazione `005_accounts_invites` (20 caratteri ≤ 32)

- **`users`**, colonne nuove:
  - `session_version INT NOT NULL DEFAULT 0`;
  - `email_verified_at DATETIME NULL`, per E;
  - `last_seen_version VARCHAR(40) NULL` per C-54, se D-A12 è sì.
- **Tabella nuova `account_tokens`**:
  - colonne: `id`; `purpose` (con CHECK: invite, password_reset, email_verification, admin_setup); `token_hash` (unico); `user_id` (FK, CASCADE); `email`; `grants_admin`; `created_by_user_id` (FK, SET NULL); `created_at`, `expires_at`, `consumed_at`, `revoked_at`; `consumed_by_user_id` (FK, SET NULL);
  - indice su `(purpose, expires_at)`.
- **Dati**: la riga `enable_registration` diventa `registration_mode` (true → open, false → disabled), con `updated_by_user_id` e `updated_at` copiati.
- **Downgrade**: `invite` diventa `false`.
- **Tecnica**: `ALTER TABLE ADD COLUMN` grezzo e idempotente, come la 004. **Mai** un batch sulla tabella `users` (§1, FK).
- **Prove**:
  - upgrade e downgrade su una copia popolata;
  - upgrade da un DB della 1.2;
  - una sola head.

### 4.4 Token generici (`accounts/token_service.py`)

- Il token è `secrets.token_urlsafe(32)` (256 bit). Nel DB va solo il suo SHA-256.
- Lo scopo è vincolato: un token di reset non vale come invito.
- Scadenze: invito 7 giorni, reset 30 minuti, setup 72 ore, verifica dell'email decisa da E.
- **Consumo atomico**: `UPDATE … SET consumed_at WHERE id=? AND consumed_at IS NULL AND revoked_at IS NULL AND expires_at>now`, con `rowcount == 1`.
- Revoca per id o per utente.
- Aiuti per i percorsi: `/invite?token=`, `/reset-password?token=`, `/setup?token=`, `/verify-email?token=`.
- Il token non finisce mai nei log. Unica eccezione voluta: il link di setup generato dall'istanza.

### 4.5 Sessioni

- Il JWT ha un claim nuovo, `sv`. `get_current_user` lo confronta con `user.session_version`.
- Un token senza `sv` vale come 0: dopo l'upgrade nessuno viene buttato fuori.
- **Cambio della password**: la versione si alza e il cookie della sessione corrente viene riemesso. Oggi la modale resta loggata, quindi senza il cookie nuovo l'utente uscirebbe.
- La versione si alza anche con il link di reset, `user reset` da CLI, la disattivazione e il declassamento.

### 4.6 Registrazione, inviti, limite, utenti (F13 e la parte di F05)

- **Modalità effettiva**: `LIBREFOLIO_REGISTRATION` se è impostata (il campo in UI resta bloccato e il salvataggio dà errore); altrimenti la riga `registration_mode`.
  - `open`: chiunque, e un invito eventuale ne dà il ruolo.
  - `invite`: serve un token valido.
  - `disabled`: nessun account nuovo dalla UI, nemmeno con un invito (D-A3).
- **Invito**:
  - l'email è facoltativa; se c'è, la registrazione usa quella, bloccata nel modulo (D-A16);
  - il ruolo è utente o admin;
  - il link si vede una volta sola;
  - si può revocare.
- **`LIBREFOLIO_MAX_USERS`**:
  - conta gli utenti attivi, gli inviti pendenti e l'admin di setup in attesa;
  - blocca gli inviti, la registrazione aperta e le riattivazioni;
  - risponde `409 USER_LIMIT_REACHED {limit, used}`, con un messaggio generico più il link all'abbonamento se è impostato;
  - la CLI lo supera con un avviso;
  - per la corsa fra due registrazioni, il conteggio si ricontrolla nella stessa transazione.
- **API admin**: `GET /users`, `PATCH /users/{id}` (attivo o admin, con le guardie dell'ultimo admin), `POST /users/{id}/password-reset-link`, `POST /users/{id}/onboarding/reset` (21-5), `POST /users/{id}/sessions/revoke`, `GET|POST /users/invites`, `DELETE /users/invites/{id}`. Le rotte statiche vengono prima di `{id}`.
- **Pubbliche**:
  - `POST /auth/register` con `invite_token`;
  - `POST /auth/tokens/inspect`, che risponde solo a chi ha il token;
  - `POST /auth/password-reset`.
- **Scheda Utenti** (solo admin): utenti, inviti, «N / max», link all'abbonamento, azioni con conferma.
- **Log strutturati** per ogni azione admin: invito creato o revocato, link generato, ruolo o stato cambiato. Nessuna tabella d'audit.

### 4.7 Admin iniziale (F02) e K-5

- **Quando si attiva**: F02 è attivo se `LIBREFOLIO_ADMIN_EMAIL` è impostata. `LIBREFOLIO_ADMIN_USERNAME` vale `admin` di default.
- **Su un'istanza vuota, all'avvio** (aggancio di H, idempotente e sicuro con più worker):
  - crea l'admin in attesa, disattivo, con l'hash bcrypt di un segreto casuale mai rivelato. Non un marcatore non valido: con un hash finto il login risponderebbe senza il costo di bcrypt, e il tempo di risposta rivelerebbe che l'account esiste;
  - porta `registration_mode` a `invite`;
  - prende il token d'ambiente (`…BOOTSTRAP_TOKEN(_FILE)`, almeno 32 caratteri, valido 72 ore dal primo avvio che lo vede) oppure ne genera uno e logga il link una volta sola;
  - `dev.py user setup-link` lo rigenera.
- **Su un'istanza che ha già utenti**: le variabili vengono ignorate, con un log.
- **Errore chiaro all'avvio**: se c'è il token ma manca l'email, o se il token è troppo corto.
- **`/setup`**: si sceglie la password, l'account si attiva, si entra. Username ed email arrivano dalle variabili.
- **Senza F02**: resta il comportamento di oggi.
  - `setup_required` (zero utenti) va nella configurazione pubblica.
  - Il login mostra «Crea l'account amministratore» anche a registrazione chiusa, e questo chiude K-5.
  - Se `registration_mode` è `open` e l'host che l'admin usa per raggiungere l'istanza non è locale (decisione §10.4: non localhost o 127/8, non 10/8, 172.16/12 o 192.168/16, non 100.64/10, non nomi a una sola etichetta, non `.local`, `.lan`, `.home.arpa`, `.internal`; i nomi `ts.net` contano come esterni per via di Funnel), l'admin vede un avviso nell'area degli avvisi di H.

### 4.8 Limite dei tentativi di login (F15)

- In memoria, per processo, con una finestra mobile e un numero di chiavi limitato.
- **Soglie**: 10 errori in 15 minuti per identificativo (normalizzato in minuscolo, che l'account esista o no), 50 per IP.
- Un login riuscito azzera il contatore dell'identificativo.
- **Oltre la soglia**: 429 `TOO_MANY_ATTEMPTS`, con `Retry-After`. Il controllo viene prima di bcrypt e non rivela se un account esiste.
- Lo stesso aiuto, con soglie per IP, protegge setup, registrazione, inspect e reset.
- Con N worker il limite reale diventa N volte tanto: è documentato.
- **IP del client**: una regola unica di H (D-A6).

### 4.9 Profilo gestito, parte di A (F05)

Con il profilo di H uguale a `managed`:

- il backend non manda più il popup delle donazioni (il conteggio dei login continua);
- spariscono tutti i «Buy me a coffee»;
- spariscono il controllo degli aggiornamenti (fermato dentro `checkForNewerRelease`, senza toccare il layout di H) e i suggerimenti docker e CLI della pagina «Password dimenticata», che rimanda all'admin.

I link `LIBREFOLIO_SUPPORT_URL` e `LIBREFOLIO_BILLING_URL` (D-A8, D-A9):

- accettano solo http(s) e vengono validati all'avvio;
- si aprono con `rel="noopener noreferrer"`.

### 4.10 Disclaimer e link legali (F09)

- **Componenti**: `features/legal/LegalNotice` (testo tradotto, link a Termini e Privacy quando sono impostati) e `LegalLinks` (la versione compatta).
- **Dove compare** (D-A11):
  - About, in una card «Note legali»;
  - in fondo alle pagine di login, registrazione, setup, invito e reset;
  - Welcome;
  - una riga in fondo alla sidebar (file di H: una riga di montaggio);
  - in ogni output dell'AI Export (anche «Esporta dati») come sezione finale `legal_notice`, nella lingua dell'interfaccia.
- **Prove dell'AI Export**: cambiano solo `promptRenderer.ts` (la sezione e il tipo `AiExportPromptSectionId`) e i test d'ordine `promptRenderer.test.ts:20` e `:121`.
  - Verificato: la sonda TS carica il catalogo generato completo (`ai-export-render-prompt-probe.ts:183-191`), quindi la chiave legale si traduce come nella UI;
  - la sonda Python non ha un elenco chiuso di sezioni;
  - la sonda smoke la decide J (§5).
- Nessuna registrazione dell'accettazione dei termini (§10.11).

### 4.11 Igiene

- **O-15**: chiave nuova `auth.loginServerUnreachable` per gli errori di rete e i 5xx, più la mappatura del 429.
- **K-17**:
  - `aria-label` e `title` tradotti;
  - `aria-pressed`;
  - via `tabindex="-1"`.
- **L12**: `dev.py user create --role user|admin` (default admin, come oggi), più il comando interno `create-user`; correggo il runner e `global-setup.ts`.
- **21-5**: l'API admin, `dev.py user reset-onboarding <utente> [--flow …]` e un'azione nella scheda Utenti.

### 4.12 C-54, se c'è spazio

- Il login dice da quale versione mostrare le novità.
- `features/changelog/WhatsNewModal` riusa il parser.
- Il popup entra in coda in `DeferredAppPopups`, dopo quello degli aggiornamenti.
- Non tocca `ChangelogModal`, che è di H.

### 4.13 Contratto per E (lo fissa il checkpoint 4)

- **Servizi**: `issue_token`, `inspect_token`, `consume_token`, `revoke_tokens` e gli aiuti per i percorsi.
- **Funzioni**: `create_invite` (restituisce il token in chiaro), `create_password_reset(user)`, `mark_email_verified(user)`, più il limitatore di §4.8 da riusare.
- **Dati**: le colonne `email_verified_at` e `purpose=email_verification`.
- **Pagine pubbliche**: `/invite` e `/reset-password`.
- **Vincolo per «password dimenticata»**: deve rispondere sempre uguale, che l'account esista o no.

## 5. Dipendenze e decisioni

### Dipendenze

- **Da H**:
  - un aiuto per leggere le variabili con la variante `*_FILE`, per il token di bootstrap;
  - un aggancio d'avvio dopo `_initialize_global_settings`;
  - la configurazione pubblica dell'istanza, letta dal frontend: A ci mette `registration_mode`, `setup_required`, i link legali, di supporto e d'abbonamento, e i flag del profilo;
  - il registro degli avvisi d'istanza;
  - `LIBREFOLIO_PROFILE`;
  - la regola per l'IP del client;
  - le sezioni di `.env.example`;
  - `Referrer-Policy: no-referrer` sulle pagine con un token;
  - le eccezioni della sola lettura per gli endpoint di A (D-A15);
  - 4 righe nei suoi file di layout (§6).
- **Da altri**:
  - X mette la 006 sopra la mia 005 e usa il registro delle schede;
  - B usa il registro delle schede;
  - E parte dal checkpoint 4;
  - dal programma colori mi serve **l'elenco esatto dei file del lotto A** che toccano `components/{auth,settings,support}`, `ui/input/Password*`, `routes/+page.svelte` e `routes/(app)/settings/+page.svelte` (l'analisi P cita `style="background:#fff"` in 4 card di auth e in `AboutTab:258`).
  - G: le schermate nuove della galleria vanno aggiunte dopo il suo merge; la scheda Utenti va fotografata con dati finti, perché l'elenco degli utenti della corsia cambia di continuo.

### Decisioni (proposta consigliata in grassetto)

1. **D-A1** (corretta dopo l'invio): **tenere il suffisso `_service`**, cambia solo il pacchetto.
   - Col suffisso cambiano solo ~80 righe d'import.
   - Senza, cambierebbero anche ~150 righe del corpo (o servirebbero alias ovunque).
   - Senza, in 6 funzioni un locale `users` farebbe ombra al modulo (`UnboundLocalError` o `AttributeError`): `scripts/user_cli.py:130` (`users = await users.list_users(session)`) e `test_user_profile.py:594, 609, 918, 969, 1022`. Lo dice un controllo `ast` in sola lettura (uno script usa e getta, fuori dal repo).
   - Suggerimento trasversale al coordinatore: la stessa regola per gli altri pacchetti di dominio.
2. **D-A2**: `enable_registration` diventa `registration_mode`. La variabile d'ambiente vince e blocca il campo; F02 su un'istanza vuota scrive `invite`. Tocca ~30 file di test, documentazione e infrastruttura.
3. **D-A3**: con `disabled` si bloccano **anche** gli inviti.
4. **D-A4**: F02 vale **solo su un'istanza vuota**. Un token senza email dà errore all'avvio; il token deve avere almeno 32 caratteri; un token generato dall'istanza si logga una volta e si rigenera dalla CLI.
5. **D-A5**: il limite dei tentativi è **sempre attivo**, con soglie larghe e nessuna variabile nuova. In alternativa: spento di default e acceso nel profilo gestito.
6. **D-A6**: la regola per l'IP del client la **scrive H**. `FORWARDED_ALLOW_IPS` di uvicorn già esiste; per Fly e Cloudflare si può aggiungere `LIBREFOLIO_CLIENT_IP_HEADER`. A la usa.
7. **D-A7**: `LIBREFOLIO_DISABLE_DONATION_POPUP` **resta com'è**, nascosta, accanto al profilo gestito.
8. **D-A8**: nel profilo gestito spariscono **tutti** gli inviti a donare e al loro posto compare «Supporto», se c'è il suo link. La condivisione social resta.
9. **D-A9**: «Gestisci abbonamento» lo vedono **solo gli admin**. Il messaggio del limite è **generico**: niente «piano Famiglia» nel codice.
10. **D-A10**: il limite conta **gli utenti attivi, gli inviti pendenti e l'admin in attesa**; la CLI lo supera con un avviso.
11. **D-A11**: il disclaimer compare **nei 5 punti di §4.10**; la riga nella sidebar la monta H.
12. **D-A12**: **sì**, `last_seen_version` entra già nella 005.
13. **D-A13**: **sì**, spostare le modali degli aggiornamenti in `features/update-check/`. Costa una riga in `ChangelogModal`, che è di H.
14. **D-A14**: le chiavi i18n `support`, `donationPopup` e `legal` passano in una **sorgente nuova, `lib/i18n/support/`**, con `i18n move` dalla sorgente condivisa `app/`. Lo decide il coordinatore.
15. **D-A15**: in sola lettura restano permessi anche il cambio della password, il consumo di un reset, il setup e la cancellazione del proprio account (GDPR). Da concordare con H.
16. **D-A16**: un invito con email **vincola** l'email della registrazione.
17. **🔑 Sessioni**: la revoca alla modifica della password è **dentro** la 1.3, come dice il piano (il 09/10 il developer aveva scritto «ci devo pensare»).

Sulle decisioni aperte del piano generale (§10):

- **n. 2**: d'accordo, i disattivati non contano;
- **n. 3**: d'accordo;
- **n. 4**: d'accordo, con il dettaglio di §4.7;
- **n. 11**: d'accordo, nessuna casella da spuntare.

## 6. Previsione dei conflitti

| Con | Dove | Come lo gestisco |
|---|---|---|
| H | `main.py:58` (import), `services/scheduler/settings.py:11`, `api/v1/uploads.py:39` | Il rinominare (A1) e gli agganci di H entrano nello stesso treno (M3). Chi arriva secondo rimette a posto la riga d'import quando aggiorna la base |
| H | `accounts/auth.py`: il segreto del JWT di F03 e la mia versione di sessione | A1 è una rinomina pura, con somiglianza ≥ 95 %: Git applica la modifica di H sul percorso nuovo. Il codice delle sessioni arriva solo dopo F03 |
| H | `Header.svelte:242`, `HelpMenu.svelte:23` (donazioni in modalità gestita), `Sidebar.svelte:~280` (riga legale), `ChangelogModal.svelte:17` (import di `AskAdminModal`) | Una riga per file: o la scrive H, o mi dà il permesso tramite il coordinatore |
| W | `api/v1/auth.py:30` (`brim_provider` sta nella stessa riga dei miei servizi), `test_account_deletion_api.py:59`, `accounts/users.py` (importa `BrokerService`), `api/v1/brokers.py:95` (`get_max_upload_mb`) | Prima la mia rinomina, poi PL5 e il taglio dei broker di W, con un aggiornamento della base |
| J | `financial_math/portfolio/engine.py:28`, `portfolio_service.py:106`, `lots_analysis_service.py:41`, `test_layer_boundaries.py:16,167`, `financial-math.instructions.md` | Righe d'import cambiate nel mio commit di rinomina, prima che J tagli `portfolio/`. La guardia vieta prefissi espliciti (`test_layer_boundaries.py:50`): il percorso nuovo resta permesso da solo, si aggiornano solo l'esempio `:167` e la docstring `:16` |
| J | `promptRenderer.ts` (la sezione legale) contro le sue voci di AI Export (T-B7, T-B8) | Lo segnalo: modifiche piccole. La sonda smoke resta sulla corsia di J |
| X | registro delle schede, `down_revision` della 006, schema «bloccato da variabile» condiviso | Il registro entra al checkpoint 3, prima della UI di X |
| Z | `SchedulerConfigModal` e `SchedulerLogModal`, che sposto in `features/settings/components/` | Li sposto subito in A2; Z li tocca solo con F07, più tardi |
| B | la scheda Backup nel registro; gli zip di backup contengono solo gli hash dei token | Nessun conflitto |
| Colori R e G | possibili file del lotto A in auth e settings (inline `#fff`, alfa); `gallery.spec.ts` | Aspetto l'elenco; se un file è nel lotto A, il suo spostamento slitta dopo l'integrazione del lotto |
| Runner e infrastruttura | `_frontend_utility.py` (19 percorsi), `_backend_services.py`, `_frontend_common.py:192`, `_backend_api.py:757`, `conftest.py`, `global-setup.ts:76`, `coverage_analysis.py` | Modifiche solo in aggiunta e solo per il mio dominio, su incarico del coordinatore |

## 7. Complessità e rischi

**Peso dei lotti**:

| Lotto | Peso |
|---|---|
| Rinomine del backend e del frontend | basso-medio |
| Registro delle schede e igiene | basso |
| Migrazione 005 | medio |
| Token, inviti, registrazione e utenti, backend e UI | **medio-alto** (il lotto più grande) |
| F02 | piccolo-medio |
| F15 | piccolo-medio |
| F05 e F09 | piccolo-medio, ma con molti punti di contatto |
| C-54 | medio |

**Rischi di sicurezza**:

- **Enumerazione degli account**:
  - la registrazione aperta rivela già oggi se un nome o un'email sono presi (è inevitabile);
  - inspect, setup e reset rispondono solo a chi ha il token;
  - il limite dei tentativi conta per identificativo scritto, non per account;
  - il futuro «password dimenticata» di E dovrà rispondere sempre uguale.
- **Token**:
  - 256 bit, salvati solo come hash, legati allo scopo, consumati in modo atomico;
  - scadenza e revoca;
  - tolti dalla barra degli indirizzi con `history.replaceState` appena letti;
  - link esterni in `noreferrer`, più l'header di H.
- **Ultimo admin**:
  - le guardie dei servizi vengono riusate e passano dagli id;
  - l'admin in attesa di setup non conta come admin attivo;
  - un link di reset per un altro admin è ammesso: è un potere che l'admin ha già.
- **Sessioni**: i cookie senza `sv` restano validi, così l'upgrade non butta fuori nessuno; dopo il cambio della password il cookie viene riemesso.
- **Limite dei tentativi**:
  - un attaccante può tenere bloccato l'identificativo di qualcuno, ma solo per poco;
  - dietro un proxy non fidato tutti i client sembrano lo stesso IP: per questo le soglie per IP sono larghe e `FORWARDED_ALLOW_IPS` va documentato.
- **Più worker**:
  - il bootstrap gira in ogni lifespan: deve essere idempotente, con una guardia nel DB e il link loggato una sola volta;
  - il limite dei tentativi diventa N volte tanto.
- **Migrazione**: un batch su `users` con le chiavi esterne attive cancellerebbe a cascata. Si usa solo `ALTER TABLE ADD COLUMN`, con un test di upgrade da un DB della 1.2.
- **Isolamento dei test**:
  - la riga `registration_mode` è condivisa da tutta la corsia: i test che la cambiano sono esclusivi;
  - variabili d'ambiente e limite si provano nel processo, con un DB privato, come fa REG-007;
  - chi cambia la password, disattiva o declassa un utente ora ne chiude le sessioni: questi test usano sempre un utente proprio. Oggi è già così (backend `chpwd_{timestamp}`, `test_auth_api.py:658`; l'E2E di Impostazioni non invia mai la modale).

## 8. Passi ordinati, lotti e checkpoint

| Lotto | Contenuto | Checkpoint |
|---|---|---|
| A1 | Rinomina del backend in `services/accounts/`, nessun cambio di comportamento | **CP1**, treno M3 |
| A2 | Rinomina del frontend: auth, settings, support, modali degli aggiornamenti. Aspetta l'elenco del lotto A dei colori | **CP2** |
| A3 | Registro delle schede (stesse 4 schede), O-15, K-17, L12 | **CP3**, sblocca le schede di B e X |
| A4 | Migrazione 005, modelli, token, `sv` e chiusura delle sessioni, `registration_mode` con il blocco da variabile, `user reset` che alza la versione | — |
| A5 | Inviti, modalità di registrazione, limite utenti, API admin, link di reset, 21-5, CLI; pagine `/invite` e `/reset-password` | **CP4**, «token e inviti»: **sblocca E** |
| A6 | Scheda Utenti, modali dell'invito e del link di reset, banner del limite | **CP5** |
| A7 | F02 con `/setup`, `setup-link`, K-5 (`setup_required` e il pulsante nel login), avviso di registrazione aperta ed esposta. Dopo il primo checkpoint di H | — |
| A8 | F15: limite dei tentativi su login e token, 429 nella UI | **CP6** |
| A9 | F05, parte di A, e F09, dopo la configurazione pubblica di H | **CP7** |
| A10 | Rilettura finale della documentazione (ogni lotto porta la sua), galleria dopo G, catalogo del runner, sezione di `.env.example`, testo per il CHANGELOG, righe del backlog, tabella vecchio → nuovo per lo storico | **Finale** |
| A11 | C-54, se c'è spazio | **CP8** |

Ogni lotto di riordino porta due commit: prima la rinomina, poi gli eventuali cambi.

## 9. Definizione di fatto

- **Test**:
  - i selettori del dominio verdi;
  - `all-backend` con gli stessi conteggi della base, più i test nuovi;
  - `front check` a 0 errori;
  - i Vitest coinvolti verdi;
  - `front build` passa;
  - gli E2E del dominio verdi nella corsia.
- **Controlli statici**:
  - `ruff`, `black`, Prettier;
  - `lint --dead-code` senza reperti nuovi (vulture e knip);
  - `api sync`: nessuna differenza nei lotti di rinomina, solo quelle volute negli altri.
- **Rinomine**:
  - il grep dei vecchi percorsi dà zero in `backend/`, `scripts/`, `.github/`, `mkdocs_src/docs/developer/`, `frontend/src`, `frontend/e2e`;
  - `git diff -M` mostra una somiglianza ≥ 95 %.
- **Migrazione 005**: upgrade e downgrade provati, anche da un DB della 1.2; una sola head.
- **Doc**:
  - `mkdocs build` in modalità strict e `check-links` passano;
  - `check_source_paths.py` non peggiora.
- **Galleria**: ci sono le schermate nuove.
- **Diario**:
  - il piano è aggiornato a ogni passo;
  - la sezione A del backlog è aggiornata.
- **Corsia**: la porta 6182 risulta libera alla fine.

## 10. Test e selettori

**Preambolo**:
`PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6182 --data-dir /tmp/librefolio-r13-a <CAT> <AZIONE>`

**Backend, selettori che esistono già**:

- `services user-profile`, `services settings`, `services global-settings`, `services donation-popup`, `services financial-math`;
- `api auth` (esclusivo), `api settings`, `api account-deletion`, `api users-search`, `api cache-admin`, `api scheduler`;
- le voci `db` di `test_post_migration` e `referential-integrity`.

**Backend, selettori nuovi (proposta)**:

- `services account-tokens`, `services registration`, `services bootstrap-admin`, `services login-throttle`;
- `api users-admin`;
- `db migration-005`.

**Frontend**:

- `front-utility core-unit`, `component-unit`, `onboarding-component-unit`;
- gli E2E `auth`, `settings`, `scheduler`, `onboarding-tour`;
- `front-user user-unit`, `account-deletion`;
- nuovi: `front-utility users-admin`, `invite-flow`, `password-reset-link`.

**AI Export**:

- i Vitest del renderer;
- una sonda smoke, solo se J o il coordinatore la chiedono.

**Prima i rossi**: per ogni comportamento nuovo, il test rosso viene scritto prima della cura.

## 11. Specialisti e dipendenze

- `test-author` per ogni test nuovo o riscritto: file distinti, corsia 6182, nessuna suite lanciata senza il mio via.
- `docs-writer` per le pagine EN.
- `project-historian` per la tabella della devWiki, se il coordinatore lo incarica.
- `security-review` al cancello di rilascio, sulle superfici nuove (lo decide il coordinatore).
- **Nessuna dipendenza Python nuova**: `secrets`, `hashlib` e `hmac` sono nella libreria standard.
- Nel worktree manca `node_modules`. Prima dei primi controlli del frontend chiederò il via per `npm ci`, dopo aver visto l'errore.

## 12. Fuori perimetro

- Una tabella d'audit: bastano i log strutturati.
- La cancellazione degli utenti da parte dell'admin.
- `last_login_at`.
- OIDC e 2FA.
- «Password dimenticata» self-service e i flussi di verifica dell'email: sono di E.
- Rendere privato `GET /settings/global`.

## 13. Piano nel journal

`LibreFolio_developer_journal/Release_2/Phase_1/02_accounts/plan-phase01Accounts.prompt.md`: lo creo solo dopo l'autorizzazione.

## 14. Correzioni dopo l'invio (14/10, sera), mandate al coordinatore

- **D-A1 rovesciata**: tenere il suffisso `_service` (§4.1, §5).
- **Moduli nuovi** nello stesso stile (§3.1).
- **Conteggio**: 17 file Vitest, non 19 (§3.3).
- **Verificati, senza cambi al disegno**:
  - le sonde dell'AI Export (§4.10);
  - i test che cambiano la password usano utenti propri (§7);
  - la guardia del livello finanziario (§6);
  - l'admin di bootstrap con un hash bcrypt vero (§4.7).

## 15. Decisioni del developer (14/10, note sul documento delle decisioni, inoltrate dal coordinatore)

> Le note sono alla lettera. ✅ = decisa; ⏳ = punto aperto, in attesa della risposta del developer tramite il
> coordinatore. Non si implementa nulla oltre A1 finché il coordinatore non dà il via.

| Domanda | Nota del developer (alla lettera) | Cosa cambia nel piano | Stato |
|---|---|---|---|
| D-A1 (nomi) | — (deciso dal coordinatore come C1 del piano generale) | Il file tiene il nome, cambia il pacchetto | ✅ |
| 1 · D-A2 (tre modalità) | nessuna nota | Approvata come proposta | ✅ |
| 2 · D-A3 («chiusa» blocca gli inviti) | «gli inviti per iniziare facciamo che sono dei messaggi con un url link e dentro questo url un tocken che il backend si aspetta, una volta usato esso deve scadere, in seguito lo inviamo anche per email ma come primo step facciamo così, potrebbe servire, se il sistema non è in grado di auto scoprirlo, assegnare in una variabile anche l'url esterno del server.» | Inviti = link con un token monouso (già nel disegno §4.4–§4.6). Nuovo: una `LIBREFOLIO_PUBLIC_URL` facoltativa per i link costruiti fuori dal browser (CLI, log, email) | ✅ meccanismo; ⏳ `LIBREFOLIO_PUBLIC_URL` |
| 3 · D-A4 (admin iniziale) | «si mi piace e si sposa bene con quello che dicevo prima sui tocken in url, la logica è che se la variabile viene passata, all'ora la prima iscrizione è su invito e l'invito è quello, così in ottica di librefolio cloud siamo sicuri che a usare l'istanza sia chi ha pagato perchè ha ricevuto il tocken. però bisogna pensare a come fare se scade in quel caso... o forse possiamo pensarci dopo, rifrlettici — cmq se la variabile non è impostata, ovviamente deve funzionare comè ora» | Approvata. Aperta la scadenza del token di setup; proposta del coordinatore: se l'admin non si è ancora attivato, un token nuovo nella variabile, al riavvio, revoca il vecchio e vale altre 72 ore | ✅; ⏳ scadenza |
| 4 · D-A5 (limite dei tentativi) | «è un ottima proposta lato sicurezza, la metterei attiva di default e disattivabile solo tramite variabile di ambiente, principalmente per i test che così possono lavorare indisturbati. Sarebbe da aggiungere nel pannello amministratore una zona con l'audit di sicurezza, dove in generale mettere le cose sospette e come prima cosa, far comparire il messaggio "attenzione ..." se il limiti di login è disattivato, potrebbe essere un errore di configurazione che altrimenti passa inosservato» | Cambiata: attivo di default, spegnibile solo da una variabile d'ambiente pensata per i test. Nuovo nel perimetro: una zona «controlli di sicurezza» per l'admin, con per primo l'avviso «limite dei tentativi disattivato» | ✅ default; ⏳ nome della variabile, posto della zona, altri controlli |
| 5 · D-A7 (variabile nascosta delle donazioni) | «no no è corretto che sia così, quelli selfosted ogni tanto devono vedersi ricordati di contribuire.» | Confermata: resta nascosta e invariata | ✅ |
| 6 · D-A8 (donazioni nel profilo gestito) | «si ok farlo scomparire, non serve mettere supporto, c'è già il bottone alle issue di github, però lascierei nelle impostazioni i link ai social per condividere il prodotto.» | Cambiata: niente `LIBREFOLIO_SUPPORT_URL`. Nel profilo gestito spariscono le donazioni; restano il pulsante delle issue di GitHub e i link social in Impostazioni | ✅ |
| 7 · D-A9 (abbonamento solo per l'admin) | «si ok far vedere il billing solo all'amministratore, colui che paga, non mi è chiaro però come si passa l'url all'istanza e dove l'amministratore vede questa cosa o se la va a cercare.» | Confermata. Aperto il posto di «Gestisci abbonamento»; il link arriva da `LIBREFOLIO_BILLING_URL`, impostata dall'hoster (proposta di A: in testa alla scheda Utenti, accanto a «N / max», e nel messaggio di limite raggiunto) | ✅; ⏳ posto |
| 8 · D-A10 (conteggio del limite) | «serve una ulteriore pagina per l'amministratore che gli permette di elencare gli utenti attivi e gli inviti in volo. può eliminare quando vuole gli inviti in volo e non può creare più inviti di quanti il numero limite prevede. Di default, se la variabile è assente, il numero limite è infinito (caso self hosted) — Dovremmo invece ragionare su come può fare un amministratore ad eliminare un utente in teoria attivo, cosa succede ai suoi broker e alle sue transazioni.» | Confermata, con la scheda Utenti di A6. Nuovo, da decidere: la cancellazione di un utente attivo da parte dell'admin (era fuori perimetro, §12); proposta del coordinatore: riusare `user_service.delete_user` (la regola della cancellazione del proprio account), con l'anteprima di cosa sparisce | ✅; ⏳ cancellazione da parte dell'admin |
| 9 · D-A12 (`last_seen_version` nella 005) | nessuna nota | Approvata | ✅ |
| 10 · D-A16 (invito legato all'email) | «la rimanderei a più avanti, quando integriamo il servizio e mail ma anche fosse non sono convinto serva, anzi, il link è il link, ha una scadenza temporale, e comunque si può usare 1 sola volta, quindi non mi preoccuperei troppo, per altro un nuovo utente di default non vede i dati degli altri, solo nomi broker e nomi utenti.» | Respinta: un invito non vincola l'email. Facoltativo, in sola lettura, per l'handoff: cosa vede oggi un utente nuovo dei dati degli altri, con gli endpoint | ✅ respinta |
| 11 · D-A17 (le sessioni si chiudono) | «capisco che in caso di piscing abbia senso che al cambio pw tutti i device vengano sloggati, per farlo come si potrebbe fare? si invalida il l'oaut eccetto nel client in cui stai facendo il cambio pw, che il backend ti ritorna subito il nuovo o semplicemente ti rilogghi immediatamente, avendo appena mandato la pw i dati li avresti tutti, o come altro?» | Il meccanismo `sv` del §4.5 (versione della sessione nel token, cookie riemesso al dispositivo corrente) è quello che il developer ipotizza: in attesa di conferma | ⏳ meccanismo |
| D-A6, D-A11, D-A13, D-A14, D-A15 | non fra le domande del developer | D-A6 a H (CP6/CP7b); D-A15 nelle eccezioni della sola lettura di H (CP6), domanda 12 della Piattaforma; D-A11, D-A13, D-A14 da confermare dal coordinatore | ⏳ |

### 15.1 Decisioni definitive (14/10, testo completo in `decisioni-analisi-20261014.md` al commit `5b0cea661`)

> Le note del developer sono quelle della tabella qui sopra; i punti ⏳ sono tutti risolti qui. Dove questa tabella
> cambia il §4, vale questa.

| Domanda | Decisione | Cosa cambia nel piano |
|---|---|---|
| D-A1 | C1 del piano generale: il file tiene il nome, cambia il pacchetto | §4.1 com'è (A1) |
| 1 · D-A2 | approvata, senza note | §4.6 com'è |
| 2 · D-A3 | approvata: «chiusa» blocca anche gli inviti. L'invito è un link con un token monouso, da copiare e condividere a mano; poi anche via email | Nella finestra dell'invito l'indirizzo del server è precompilato con quello del browser e modificabile; se l'admin lo cambia, un controllo dal browser verifica che lì risponda l'istanza. `LIBREFOLIO_PUBLIC_URL`, facoltativa, per i link costruiti fuori dal browser (riga di comando, poi email) |
| 3 · D-A4 | approvata | Se il link scade prima dell'attivazione: un token nuovo nella variabile e un riavvio riarmano l'admin in attesa per altre 72 ore (l'istanza è ancora vuota). Senza variabili: tutto come oggi, più K-5. L'avviso «registrazione aperta su un indirizzo pubblico» va nella scheda «Sicurezza», non nell'area avvisi di H. Per il pannello del cloud (repo privato): un'azione «reinvia il link di attivazione» |
| 4 · D-A5 | approvata con due modifiche | Limite attivo di default, spento solo da una variabile d'ambiente pensata per i test (nome da proporre al lotto A8). Nuova scheda **«Sicurezza»** in Impostazioni, solo per l'admin, con un segnale sulla scheda quando c'è un avviso: un registro aperto di controlli, a cui altre sessioni aggiungeranno i loro. Primi due: «limite dei tentativi disattivato» e «registrazione aperta su un indirizzo pubblico» |
| 5 · D-A7 | approvata: la variabile resta nascosta | nessuno |
| 6 · D-A8 | approvata con una modifica | Nel profilo gestito spariscono tutti gli inviti a donare, senza un «Supporto» al loro posto: niente `LIBREFOLIO_SUPPORT_URL`. Restano il pulsante delle issue GitHub e i link social in Impostazioni |
| 7 · D-A9 | approvata | `LIBREFOLIO_BILLING_URL` la imposta il pannello del cloud. «Gestisci abbonamento» solo per l'admin: scheda Utenti accanto a «N / max», messaggio di limite raggiunto, pagina di blocco (punto 12) |
| 8 · D-A10 | approvata, con la pagina Utenti e la cancellazione da parte dell'admin | Scheda Utenti (A6): utenti attivi e inviti in corso, revoca quando vuole, niente inviti oltre il limite, nessun limite senza variabile. **Nuovo: l'admin elimina un utente**, con la regola di `user_service.delete_user` (i broker di cui era l'unico proprietario spariscono con transazioni e file; da quelli condivisi sparisce solo il suo accesso); anteprima di cosa sparisce e conferma con il nome utente; «Disattiva» come prima scelta. Admin: l'ultimo attivo non si elimina, non si disattiva e non si declassa; un altro admin va prima declassato; nel profilo gestito l'admin creato dalle variabili non si elimina, non si disattiva e non si declassa |
| 9 · D-A12 | approvata | `last_seen_version` nella 005 |
| 10 · D-A16 | respinta | Un invito non vincola l'email (§4.6 cambia) |
| 11 · D-A17 | approvata | Il meccanismo `sv` del §4.5: la generazione delle sessioni sta nel cookie firmato; cambio o reset della password la alzano, e la stessa risposta riemette il cookie al dispositivo corrente |
| 12 · D-A15 (Piattaforma) | niente sola lettura: con l'abbonamento non pagato l'istanza si blocca (H, CP6) | Restano permessi accesso e uscita, la pagina di blocco, il backup per l'admin, la cancellazione del proprio account e il risveglio programmato. Le eccezioni di A per la sola lettura (D-A15) decadono |
| D-A6, D-A11, D-A13, D-A14 | non fra le domande del developer | D-A6 a H (CP6/CP7b). D-A11 (posti del disclaimer), D-A13 (modali degli aggiornamenti) e D-A14 (sorgente i18n `support/`) si confermano con il coordinatore al lotto che li tocca (A9, A2) |

## 16. Dipendenze e calendario confermati dal coordinatore (14/10 sera)

- **Lotto A dei colori**: nessun file nelle cartelle di A. Del lotto A, fuori perimetro: `ui/feedback/{ToastContainer,
  DataQualityBanner}` e `stores/app/themeStore.ts`.
- **Schermate di accesso**: le modifiche visive a `LoginCard`, `RegisterCard` e `PasswordStrength`, e la rimozione di
  `auth.registerTitle`, le fa per primo il workstream T dei colori. `features/auth` si sposta dopo i suoi piloti di
  accesso; se T tarda, spostamento puro e T segue sui percorsi nuovi.
  - Con l'approvazione di A, T cambia solo le classi colore di `ForgotPasswordCard`, della barra in alto di
    `routes/+page.svelte` e di `HelpMenu`; riordino, righe funzionali e condizione sulle donazioni restano di A.
  - `PasswordInput`: T aggiunge una prop per l'icona, A fa K-17 su righe diverse.
  - Prima di spostare `settings/tabs/AboutTab.svelte`, A chiede conferma al coordinatore.
- **Meccanismi di H**, per checkpoint (i nomi esatti arrivano quando ognuno entra in `dev_release2`):
  - CP2: pacchetto `config/` con la sezione di A `config/accounts.py`, e avvio a fasi (l'admin iniziale gira dopo le
    impostazioni globali). Sostituisce l'`accounts/account_config.py` del §3.1;
  - CP3: lettore `*_FILE` per ogni segreto, più la guardia «ogni variabile è in `.env.example`»;
  - CP4: `/system/instance` (configurazione pubblica: `registration_mode`, `setup_required`, i link) e l'area avvisi
    in `features/instance/`;
  - CP6: profilo gestito e sola lettura (allow-list, con le eccezioni D-A15);
  - IP del client (D-A6): `FORWARDED_ALLOW_IPS` documentato, più un'eventuale `LIBREFOLIO_CLIENT_IP_HEADER`, in
    CP6/CP7b.
  - Quindi A7 dopo i CP2 e CP4 di H; A9 dopo i CP4 e CP6.
- **Primo treno**: H CP1 → X CP1 → A A1. A entra per terzo; i conflitti con H su `main.py:58`,
  `services/scheduler/settings.py:11` e `api/v1/uploads.py:39` li risolve A all'aggiornamento di base.
- **`npm ci`**: prima della prima run di test, anche solo del backend, perché il server condiviso costruisce il
  frontend se manca (regola scritta in `793395913`).
- **Finestra della galleria**: 15/10 dalle 09:00, circa 2 ore, senza suite complete né build pesanti nella corsia;
  inizio e fine li conferma il coordinatore.
- **Prima trappola dell'ambiente** (trovata da J): il primo `all-backend` in un worktree nuovo cade con «Shared backend
  did not answer within 300s», perché il server condiviso costruisce prima il frontend in modalità debug e il sito
  mkdocs dentro lo stesso limite (`scripts/test_runner/_server.py:48`). Rimedio, una volta sola dopo `npm ci`:
  `dev.py front build --debug` e `dev.py mkdocs build` (regola in `6ab653dd4`).
- **Dopo il commit di A1** (coordinatore, 14/10 sera):
  1. il coordinatore aggiorna la base di A con `dev_release2`, che contiene T-1: i file frontend nuovi nascono senza
     classi di palette (regole nel §6 del piano generale);
  2. poi A2 (impostazioni e supporto; `features/auth` dopo i piloti di T), A3, A4, A5, A6 (con la cancellazione degli
     utenti) e A8 (con la scheda «Sicurezza»), ognuno con il suo checkpoint FROZEN;
  3. A7 aspetta i CP2 e CP4 di H; A9 i CP4 e CP6. Il CP2 di H aspetta un commit del coordinatore.

## 17. Avanzamento

### A1 — servizi account in `services/accounts/` (CP1) — in corso

#### A1.0 — Basi prima delle modifiche ✅ (2026-10-14)
> **Note implementazione**:
> - Comando: `bash /tmp/libreFolio_a1_measure.sh base` (log in `/tmp/libreFolio_a1_measure_base.log`), a HEAD
>   `c9bb8f257`, con `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc`, `LIBREFOLIO_TEST_MODE=1` e
>   `LIBREFOLIO_TEST_DATA_DIR=/tmp/librefolio-r13-a`.
> - `dev.py api schema`: `openapi.json` sha256 `1302530690b5…`, `tool-contracts.openapi.json` `202402e592a4…`; copie
>   in `/tmp/libreFolio_a1/base/`.
> - `pytest --collect-only`: **12 976 test raccolti**.
> - `check_source_paths.py`: 9 percorsi inesistenti (15 occorrenze) su 3 844, in 11 pagine (già presenti).
> - `dev.py lint --dead-code --scope backend`: l'elenco della base, con `user_service.py:352 count_superusers` fra i
>   reperti.
> - Inventario: 314 righe nominano i 6 moduli, 171 con un percorso o un import da cambiare
>   (`/tmp/libreFolio_a1_pathrefs.txt`).

#### A1.1 — Piano nel journal ✅ (2026-10-14)
> **Note implementazione**: questo file, dal piano di sessione, con l'autorizzazione alla lettera, le decisioni del
> developer (§15) e le dipendenze confermate (§16).

#### A1.2 — `npm ci` ✅ (2026-10-14)
> **Note implementazione**: `npm ci --no-audit --no-fund` in `frontend/`, dal lock, uscita 0 (log
> `/tmp/libreFolio_a1_npm_ci.log`).
>
> **⚠️ Fuori pista**: npm 11 non esegue gli script d'installazione di `fsevents` (2.3.2, 2.3.3) ed `esbuild`
> (0.27.2) senza un'approvazione (`npm install-scripts approve`): solo avvisi. Non li ho approvati io; se la build
> del frontend del server condiviso ne soffre, lo segnalo al coordinatore.
>
> Esito: la build di debug del frontend (A1.7) è passata, quindi non c'è stato bisogno di approvarli.

#### A1.3 — Spostamento ✅ (2026-10-14)
> **Note implementazione**:
> - I 6 file sono passati in `backend/app/services/accounts/` con `mv`, con lo stesso nome (C1).
> - Non ho usato `git mv`: il protocollo dei figli vieta lo stage dei file normali. Il coordinatore aggiunge i percorsi
>   vecchi e nuovi, e Git riconosce le rinomine.
> - `accounts/__init__.py` è nuovo e contiene solo la docstring: la mappa dei moduli, nessuna ri-esportazione, come
>   in `financial_math/`.
> - Somiglianza con `HEAD`:
>   - `auth_service` e `donation_popup_service`: 100 %;
>   - `user_service` 99,8 %, `onboarding_service` 99,8 %, `settings_service` 99,7 %, `global_settings_service`
>     99,0 %: una riga d'import ciascuno (per `global_settings_service`, l'esempio d'uso nella docstring).

#### A1.4 — Riscrittura dei riferimenti ✅ (2026-10-14)
> **Note implementazione**:
> - **Script**: usa e getta, `/tmp/libreFolio_a1_rewrite.py`. Prima una prova a vuoto, poi l'applicazione (log
>   `/tmp/libreFolio_a1_rewrite.log`).
> - **Python**, 36 file più i 4 moduli spostati che importano un fratello (+91 −89 righe):
>   - gli import puntati `backend.app.services.<modulo>` diventano `backend.app.services.accounts.<modulo>`;
>   - `from backend.app.services import …` si divide in due righe quando importa anche altri moduli:
>     `brim_provider` in `api/v1/auth.py:30` e in `test_account_deletion_api.py:59`;
>   - percorsi con lo slash nei commenti e nelle stringhe:
>     - `models.py:378` e `schemas/auth.py:73`;
>     - i 4 `print_info` del runner (`_backend_services.py`);
>     - le 3 chiavi di `coverage_analysis.py`;
>     - la forma permessa d'esempio di `test_layer_boundaries.py:167`;
>     - il commento di `test_settings_service.py:597`.
> - **`.github`**: `skills/onboarding-tools/onboarding-guide/SKILL.md:79`.
> - **devWiki**: 30 righe in 24 pagine (+30 −30), tutte righe di tabelle «Source files» (C6). La prosa resta com'è,
>   come in T-1: la cronaca non si riscrive.
> - **Ordine degli import**: `ruff check --select I001 --fix` sui 10 file in cui il percorso nuovo cambiava l'ordine
>   (`accounts` viene prima di `financial_math`, `fx`, `scheduler`…). Ho riletto il diff: cambiano solo righe
>   d'import. In `api/v1/settings.py` scendono anche le due righe di `scheduler`.
>
> **⚠️ Fuori pista**: la mia stima dei conteggi nella prova a vuoto diceva «~312» e «~734» righe per i due file con
> lo split. Era un artefatto del confronto riga per riga: la riga in più sposta tutto il resto. Il diff vero ha 2
> righe per file.

#### A1.5 — Doc per sviluppatori (`docs-writer`) ✅ (2026-10-14)
> **Note implementazione**:
> - 9 righe in 6 pagine (+9 −9): cambia solo `accounts/`, senza riscrivere i paragrafi.
>   - `frontend/components/features/settings.md:81`;
>   - `frontend/components/features/import-wizard.md:914`;
>   - `frontend/onboarding.md:58`, `:139`, `:370`, `:380`;
>   - `architecture/users_and_brokers.md:15`;
>   - `architecture/database/users_access.md:97`;
>   - `architecture/security.md:51`.
> - `dev.py mkdocs build` (strict): uscita 0, «Documentation built in 51.52 seconds», «All 3012 relative asset
>   URL(s) in the built site resolve».
> - `dev.py mkdocs check-links`: uscita 0, «95 valid link(s)».
> - Nessuna traduzione né timbro: sono pagine solo in inglese.
> - **Segnalato, non toccato**: `TODO_Completati.md:507` e `:518` citano ancora il percorso vecchio. È un registro del
>   lavoro passato, fuori dal grep a zero.

#### A1.6 — Controlli statici ✅ (2026-10-14)
> **Note implementazione**:
> - **Grep dei vecchi percorsi** in `backend/`, `scripts/`, `dev.py`, `.github/`, `pyproject.toml` e
>   `mkdocs_src/docs/developer/`:
>   - forma puntata: 0;
>   - `from backend.app.services import <modulo account>`: 0 nei sorgenti (l'unico riscontro è un `.pyc` vecchio in
>     `__pycache__`, ignorato da Git);
>   - forma con lo slash: 0.
> - **Import**: `python -c "import backend.app.main, backend.app.services.accounts.user_service, scripts.user_cli"`
>   riuscito, in modalità test, con la data-dir della corsia.
> - **ruff** sui 43 file Python toccati: nessun reperto nuovo.
>   - `scripts/user_cli.py` ne ha 2, già presenti alla base: W293 `:208` e PLC0415 `:271`.
>   - Alla base i reperti erano 3: il terzo era un ordine di import, che i percorsi nuovi sistemano.
> - **black**: 4 file da riformattare (`test_portfolio_wac.py`, `user_cli.py`, `coverage_analysis.py`,
>   `test_portfolio_api.py`), tutti già così a `HEAD`, controllati via stdin. Non li tocco: fuori lotto.
> - **`py_compile`**: tutto compila.
> - **`bash /tmp/libreFolio_a1_measure.sh after`** (log `/tmp/libreFolio_a1_measure_after.log`):
>   - `openapi.json` uguale alla base tranne `info.version` (`v1.2.0-40-gc9bb8f257` → `…-dirty`);
>   - `tool-contracts.openapi.json` identico (sha256 `202402e592a4…`);
>   - **12 976 test raccolti**, come alla base;
>   - codice morto identico, con il pacchetto normalizzato (`count_superusers` ora è in
>     `accounts/user_service.py:352`);
>   - `check_source_paths.py`: 8 percorsi inesistenti (14 occorrenze), contro i 9 (15) della base.
>
> **⚠️ Fuori pista**: il −1 della devWiki non viene dal lotto. È `mkdocs_src/site/`, citato in
> `decisions/single-docker-image.md:55`, che la build di `docs-writer` ha creato. Gli 8 rimasti sono tutti percorsi
> generati e già presenti alla base: `frontend/build/`, `htmlcov-*`, `generated.ts`, `backend/data/prod/`, una cartella
> di sonde nel journal.

#### A1.7 — Test ✅ (2026-10-14)
> **Note implementazione**, nella corsia 6182 con `/tmp/librefolio-r13-a`, un'invocazione alla volta (preambolo
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6182 --data-dir
> /tmp/librefolio-r13-a …`):
> - `services donation-popup`: 19 passati (7 s);
> - `api auth`: 60 passati (74 s);
> - `dev.py front build --debug` (la trappola dell'ambiente del §16): uscita 0, svelte-check pulito, output in
>   `frontend/build/`;
> - **`all-backend`**: uscita 0, **7/7 categorie verdi**, 28 min 12 s (23:25 → 23:54). Log in
>   `/tmp/libreFolio_a1_all_backend.log`.
>   - Le 23 righe di riepilogo di pytest sommano **12 965 passati, 28 saltati, 0 falliti**. Il database ha 13/13
>     controlli propri.
>   - Le esecuzioni (12 993) superano i 12 976 test raccolti di 17: sono i passaggi ripetuti del runner (isolamento
>     a runtime, consolidamento).
>   - I 28 saltati sono gli stessi del gate di T-1.
> - Porta 6182 libera dopo la run (`lsof -nP -iTCP:6182 -sTCP:LISTEN` vuoto).
>
> **⚠️ Fuori pista**: non ho una run `all-backend` della base. La base l'ho misurata con la raccolta (12 976, uguale
> prima e dopo); per avere una base dei conteggi della suite avrei dovuto annullare lo spostamento. Per una rinomina
> pura, raccolta uguale e zero rossi sono la prova.

### Checkpoint A1 (CP1) 🧊 (2026-10-14, notte) — FROZEN, in attesa del commit del coordinatore
> - **Delta** (non in stage):
>   - 6 file rinominati: `backend/app/services/{auth,user,settings,global_settings,onboarding,donation_popup}_service.py`
>     → `backend/app/services/accounts/`;
>   - 1 file nuovo: `accounts/__init__.py`;
>   - 68 file modificati: 36 Python, 1 `.github`, 6 pagine developer, 24 pagine devWiki, `BACKLOG_POST_1.2.md`;
>   - questo piano.
> - **Commit proposti**:
>   1. `refactor(accounts): move services to accounts/`;
>   2. `docs(journal): open plan 02_accounts, A backlog`.
> - **Prossimo passo**: dopo il commit e l'aggiornamento di base (con T-1), A2 al via del coordinatore.

#### A1.8 — Verifica facoltativa: cosa vede oggi un utente nuovo ✅ (2026-10-14)
> **Note implementazione**, in sola lettura. Il developer pensava «solo nomi broker e nomi utenti». In realtà un utente
> loggato, anche senza broker, vede:
> - **utenti**: con `GET /users/search` username e avatar di tutti gli utenti attivi; con `?admins=true` anche
>   l'**email degli admin** (`schemas/users.py:22`, per il suggerimento «chiedi all'admin» degli aggiornamenti);
> - **broker**: con `GET /brokers?include_inaccessible=true` id, nome e icona di **tutti** i broker a cui non ha
>   accesso (`broker_service.py:318-328`, il «discovery payload»);
> - **file caricati**: `GET /uploads` elenca i file di tutti (con `uploaded_by_user_id`), e dettaglio, anteprima e
>   download (`GET /uploads/file/{id}`) sono aperti a ogni utente loggato. Solo la cancellazione (`uploads.py:322`)
>   controlla proprietario o admin;
> - **catalogo condiviso**, per scelta di prodotto: tutti gli asset con prezzi ed eventi, le coppie FX e i tassi;
> - **senza login**: `GET /settings/global` (già segnalato, §2).
>
> Transazioni, broker accessibili e report BRIM restano legati all'accesso al broker.
