# Piano — fase 01, sessione A: account e accessi (1.3.0)

> - **Sessione**: «A - Account e accessi», ramo `e-alfy-a-account-e-accessi`, worktree
>   `LibreFolio-worktrees/e-alfy-legendary-winner`, corsia 6182 con `/tmp/librefolio-r13-a`.
> - **Coordinatore**: «Release 1.3 planning» (`928ffa97-f0c3-4975-a442-3de0c2c20fc7`).
> - **Piano generale**: [`plan-phase01Release13.prompt.md`](../plan-phase01Release13.prompt.md), §4 «A · Account e
>   accessi», §6, §7. **Decisioni**: [`decisioni-analisi-20261014.md`](../decisioni-analisi-20261014.md), §2
>   «Account e accessi».
> - **Stato**: A1 (CP1) committato (`b53dfd705`, `fc66f19c8`) e validato sulla revisione combinata `419dab09c`.
>   FROZEN, in attesa dell'integrazione in `dev_release2` e del via per A2 (§15–§17).
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

| Lotto | Contenuto | Checkpoint | Stato (19/10, base `6578f1d75`) |
|---|---|---|---|
| A1 | Rinomina del backend in `services/accounts/`, nessun cambio di comportamento | **CP1**, treno M3 | ✅ 15/10, `769cc31cb` |
| A2 | Rinomina del frontend: auth, settings, support, modali degli aggiornamenti. Aspetta l'elenco del lotto A dei colori | **CP2** | ✅ 15/10, `73b8cbebd` |
| A3 | Registro delle schede (stesse 4 schede), O-15, K-17, L12 | **CP3**, sblocca le schede di B e X | ✅ 15/10, `755eaa27d` |
| A4 | Migrazione 005, modelli, token, `sv` e chiusura delle sessioni, `registration_mode` con il blocco da variabile, `user reset` che alza la versione | — | ✅ 15/10: A4 `75a8af5a7`, A4b (la versione della sessione) `dbf89cdd5` |
| A5 | Inviti, modalità di registrazione, limite utenti, API admin, link di reset, 21-5, CLI; pagine `/invite` e `/reset-password` | **CP4**, «token e inviti»: **sblocca E** | ✅ 15/10, A5a e A5b, ingresso `8bcb23502` |
| A6 | Scheda Utenti, modali dell'invito e del link di reset, banner del limite | **CP5** | ✅ in cinque parti: A6a `1840ebd62` e A6b `09ca36b9d` (15/10); A6d + A6e `19dd8a96d` e A6c `3b3f6a1f0` (16/10) |
| A7 | F02 con `/setup`, `setup-link`, K-5 (`setup_required` e il pulsante nel login), avviso di registrazione aperta ed esposta. Dopo il primo checkpoint di H | — | ✅ in quattro parti: A7a e A7c `68355911f` (16/10); A7b `3e5336a0a` e A7b-2 `90219770c` (17/10) |
| A8 | F15: limite dei tentativi su login e token, 429 nella UI | **CP6** | ✅ 17/10: A8a con N70 ed E-13 `440616c61`; A8b con A-21a `6e2b2c8b7` |
| A9 | F05, parte di A, e F09, dopo la configurazione pubblica di H | **CP7** | ✅ 17/10, `ba8f3b06e`; correzione FPM-08 `cd52e25fc` |
| A10 | Rilettura finale della documentazione (ogni lotto porta la sua), galleria dopo G, catalogo del runner, sezione di `.env.example`, testo per il CHANGELOG, righe del backlog, tabella vecchio → nuovo per lo storico | **Finale** | ⏳ aperto. Fatti lotto per lotto: catalogo del runner, `.env.example`, testi del CHANGELOG, righe del backlog. Restano: la galleria (dopo G), la tabella vecchio → nuovo della devWiki (A-4), la rilettura finale |
| A11 | C-54, se c'è spazio | **CP8** | ✅ 17/10, `630c478cd`; `mark_seen` monotòno `119230f9f` |

Ogni lotto di riordino porta due commit: prima la rinomina, poi gli eventuali cambi.

Lotti nati dopo il piano (14–19/10):

| Lotto | Contenuto | Stato (19/10) |
|---|---|---|
| P18, A-22, A-24, A-27 | Email uniche senza distinzione di maiuscole; i login falliti senza l'identificativo nel log; tre test di E; i link di reset revocati da un cambio d'indirizzo o di password | ✅ 16/10, `68355911f` (con A7a e A7c) |
| A-25 | Il Profilo non chiede la password per un cambio di sole maiuscole | ✅ 16/10, `b7e50b359` |
| A-21a | Niente `@` nei nomi nuovi, la ricerca per indirizzo prima (A-21b aspetta il developer) | ✅ 17/10, `6e2b2c8b7` (con A8b) |
| A-42 + A-43 | Il ciclo di vita del link di setup: la gara col setup, l'annullamento | ✅ 17/10, `7156a24af` |
| Aiuto del profilo + A-50 + SC-LANE-01 | `features/instance/profile.ts`, l'avviso «withdrawn» | ✅ 17/10, `d7641f368` |
| A-46 + A-47 | La lunghezza dei nomi nella CLI; `AccountError` con il codice | ✅ 17/10, `abbe19d37` |
| A-51 + A-45 | L'annullamento e la cancellazione dell'admin in attesa sotto il lock; la riga `/auth` della guida API | ✅ 17/10, `180be0ff1` |
| X-R66 (dalla sezione di X) | Il limite delle sonde dei provider nella lingua dell'utente | ✅ 17/10, `e50c23919` |
| A-11 + A-16 + A-40 + A-26 | Il tema salvato sconosciuto; `LAST_ADMIN` dell'eliminazione di sé; l'avviso del limite in `user activate`; gli indici su espressione della 005 | ✅ 17/10, `250031cd1` |
| A-52…A-56, C-54 nota 1 di E | Le decisioni sugli account sotto il lock di scrittura; `mark_seen` non torna indietro | ✅ 17/10, `119230f9f` |
| A-57 | LGM-E-01/03 leggono il profilo della corsia | ⏸ sospeso dal developer (19/10): analisi e prova 1 fatte |

Le intestazioni di §17 che dicono «in corso» sono lo stato di quando sono state scritte: lo stato vero è in queste due
tabelle.

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

### A1 — servizi account in `services/accounts/` (CP1) ✅ (2026-10-14, integrato il 15/10 in `769cc31cb`)

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
>
> **Esito**: il coordinatore ha committato `b53dfd705` (`refactor(accounts): move services to accounts/`: 6 rinomine
> R097–R100, 1 file aggiunto, 67 modificati) e `fc66f19c8` (`docs(journal): open plan 02_accounts, A backlog`). Poi
> ha aggiornato la base con il merge `419dab09c` di `dev_release2` a `265ae5c6e`, che porta T-1, T-2 e G.

#### A1.9 — Validazione della revisione combinata `419dab09c` ✅ (2026-10-15)
> **Note implementazione** (richiesta del coordinatore, prima di ogni altra modifica):
> - **Base**: HEAD `419dab09c`, con genitori `fc66f19c8` (A) e `265ae5c6e` (`dev_release2`); worktree pulito.
>   - I lock delle dipendenze sono invariati: `node_modules` resta valido.
>   - Il merge porta 30 file frontend (T-1, T-2, G) e, nel backend, solo `scripts/visual_review/`.
> - **`dev.py front build --debug`**: uscita 0 in 1 min 46 s, svelte-check «0 errors and 0 warnings».
> - **`all-backend`** (corsia 6182): uscita 0, 7/7 categorie, 21 min 52 s. 23 righe di riepilogo di pytest: **12 965
>   passati, 28 saltati, 0 falliti**, gli stessi conteggi della run di A1. Log `/tmp/libreFolio_a1v_all_backend.log`.
> - **`dev.py api schema`**:
>   - `openapi.json` è uguale a quello di `265ae5c6e`, escluso `info.version` (`v1.2.0-62-g419dab09c`);
>   - il confronto è contro la mia base `c9bb8f257`, perché `backend/` è identico fra `c9bb8f257` e `265ae5c6e`
>     (`git diff --stat` vuoto);
>   - i contratti dei Tool sono identici (sha256 `202402e592a4…`).
> - Porta 6182 libera, worktree pulito dopo le prove.
>
> **Da sapere per A2 e i lotti dopo** (T-1 e T-2, skill `.github/skills/design-tools/theme-roles/`):
> - **Spostamenti**: uno spostamento o una rinomina pura non ha bisogno di nulla, perché il cricchetto accoppia il file
>   uscito con quello nuovo dello stesso nome. Un taglio invece si dichiara, nello stesso commit, con
>   `node frontend/scripts/theme/theme-roles.mjs --split <vecchio>:<nuovo1>,<nuovo2>`.
> - **File nuovi**: nascono senza classi di palette, solo utility `*-lf-*`. Un elemento migra intero, senza `dark:` sui
>   ruoli.
> - **Schermate d'accesso**: T-2 ha già convertito `LoginCard`, `RegisterCard`, `ForgotPasswordCard` (solo classi),
>   `PasswordInput` (prop `icon`), `PasswordStrength`, il link del caffè di `routes/+page.svelte` e
>   `routes/+error.svelte`, e ha tolto `auth.registerTitle`. Ora A può farci le modifiche funzionali; K-17 si somma
>   alla riga del bottone di `PasswordInput`.
> - **Regole della password**: T-B4 di «T (colori)» è di A. Le copie sono quattro: `PasswordStrength`,
>   `PasswordChangeModal`, `RegisterCard` e `validate_password` di `scripts/user_cli.py`; l'API chiede solo 8
>   caratteri. Va nel backlog come A-6.


### A2 — frontend in `lib/features/` (CP2) — in corso

#### A2.0 — Via, inventario e risposte ✅ (2026-10-15)
> **Note implementazione**:
> - **Via del coordinatore** (15/10, 00:26), alla lettera: «**A1 è in `dev_release2`**: merge `769cc31cb` […]
>   **Via per A2, A3, A4, A5, A6 e A8**, nell'ordine del tuo piano, con un checkpoint FROZEN ciascuno. A2: settings,
>   support e ora anche auth. A7 aspetta i CP2 e CP4 di H; A9 i CP4 e CP6.» Base: HEAD `769cc31cb`, worktree pulito.
> - **Inventario**: `git grep "components/(auth|settings|support)/"` (fuori dal journal) dà 129 righe.
>   - Codice di A, onboarding, rotte e runner: 14 file, 56 righe.
>   - devWiki: 28 righe di tabelle «Source files» in 14 pagine, più 4 righe di prosa che restano (cronaca).
>   - Documentazione per sviluppatori: 9 righe in 5 pagine (`docs-writer`).
>   - File di altri:
>     - lo script del cricchetto colori `frontend/scripts/theme/theme-roles.mjs:75`, `:83`, con un'eccezione legata al
>       percorso esatto `lib/components/support/supportLinks.ts`: spostando il file, G4 e m2 diventerebbero rossi;
>     - il suo gate `themeRoles.gate.test.ts:444`, `:445`, `:478`;
>     - un commento di `gallery.spec.ts:2322`;
>     - `scripts/visual_review/data/navigation_map.it.md:43`;
>     - `layout/ChangelogModal.svelte:17` (H).
>   - Restano di proposito:
>     - la baseline del cricchetto (22 righe): per uno spostamento puro il gate accoppia i file per nome;
>     - il percorso inventato di `test_docs_links_gate.py:87`;
>     - la cache di graphify.
> - **Risposte del coordinatore** (15/10, ~00:40):
>   - AboutTab: «sì, spostalo in `lib/features/settings/tabs/` con il suo test».
>   - `ChangelogModal.svelte:17`: «sì, la riga d'import la cambi tu, come per `main.py` in A1».
>   - Righe del programma colori (eccezione del cricchetto, `gallery.spec.ts:2322`, `navigation_map.it.md:43`): le
>     cambio io, solo il testo del percorso, nello stesso commit di A2, **dopo** l'ok del coordinatore colori,
>     inoltrato dal coordinatore 1.3.
>   - D-A14 cade: le chiavi i18n non contengono i percorsi.
> - **Forma delle cartelle**: cartelle piatte, cambia solo il prefisso e nessun import relativo. Le sottocartelle
>   `components/` del §3.2 sarebbero state una seconda modifica dentro la rinomina.
>   - `lib/features/auth/`: `LoginCard`, `RegisterCard`, `ForgotPasswordCard`;
>   - `lib/features/settings/` e `tabs/`;
>   - `lib/features/support/`, più `DonationPopupModal`;
>   - `lib/features/update-check/`: `UpdateAvailableModal`, `AskAdminModal` (D-A13).
> - **Script**: `/tmp/libreFolio_a2_rewrite.py`, sostituzione dei prefissi; i file d'altri solo con `--extra`. Prova a
>   vuoto in `/tmp/libreFolio_a2_rewrite_dry.log`.

#### A2.1 — Basi prima delle modifiche ✅ (2026-10-15)
> **Note implementazione** (corsia 6182, un'invocazione alla volta, HEAD `769cc31cb`):
> - `front-utility core-unit`: 130 file, 4 245 test.
> - `front-utility component-unit`: 118 file, 3 162 test.
> - `front-utility onboarding-component-unit`: 15 file, 437 test.
> - `node frontend/scripts/theme/theme-roles.mjs --check`: pulito.
> - `check-orphans`: 364 test unitari del frontend, tutti raggiungibili.
> - `dev.py lint --dead-code --scope frontend` (knip): i reperti di oggi, in `/tmp/libreFolio_a2_base_knip.log`.

#### A2.2 — Spostamento ✅ (2026-10-15)
> **Note implementazione**:
> - 44 file spostati con `mv`, senza stage. Nessun file nascosto, nessuna collisione.
>   - `components/auth/{LoginCard,RegisterCard,ForgotPasswordCard}` → `features/auth/`.
>   - `components/auth/DonationPopupModal` → `features/support/`.
>   - `components/auth/{UpdateAvailableModal,AskAdminModal}` → `features/update-check/`.
>   - `components/settings/*` → `features/settings/`, e `tabs/*` → `features/settings/tabs/`.
>   - `components/support/*` → `features/support/`.
>   - I test si spostano con i loro componenti; le cartelle vecchie sono cancellate.
> - Somiglianza: 39 file identici. Cambiano solo righe d'import in `DonationPopupModal` (3 su 84, 96,4 %),
>   `GlobalSettingsTab` (10 su 836), `PreferencesTab` (4 su 357), `AboutTab` (3 su 639) e `ProfileTab` (1 su 595).

#### A2.3 — Riscrittura dei riferimenti ✅ (2026-10-15)
> **Note implementazione**:
> - Con `python3 /tmp/libreFolio_a2_rewrite.py --extra frontend/src/lib/components/layout/ChangelogModal.svelte` (log
>   `/tmp/libreFolio_a2_rewrite.log`): 29 file.
> - **Codice**, 15 file (57 righe):
>   - i 5 spostati qui sopra;
>   - le rotte `routes/+page.svelte` (3) e `routes/(app)/settings/+page.svelte` (4);
>   - l'onboarding: `DeferredAppPopups.svelte` (2), `WelcomeForm.svelte` (2), e un `vi.mock` ciascuno in
>     `WelcomeForm.test.ts` e `WelcomePage.test.ts`;
>   - `layout/ChangelogModal.svelte:17`, autorizzato;
>   - il gate `clipboardSink.gate.test.ts:495`, `:509`;
>   - un commento di `e2e/support-copy-and-go.spec.ts:11`;
>   - i 19 percorsi del runner `_frontend_utility.py`.
> - **devWiki**: 28 righe di tabelle «Source files» in 14 pagine (C6). Le 4 righe di prosa restano (A-4).

#### A2.4 — Righe del programma colori ✅ (2026-10-15)
> **Note implementazione**:
> - **Ok del coordinatore colori**, inoltrato dal coordinatore 1.3 (15/10, ~00:45): «le righe nei loro file le cambi
>   tu, **nello stesso commit dello spostamento**, così i gate restano verdi a ogni commit». Righe autorizzate:
>   `theme-roles.mjs:75`, `:83`; `themeRoles.gate.test.ts:444`, `:445` (anche `otherLinks.ts`, il controllo negativo
>   sul file vicino), `:478`; il commento di `gallery.spec.ts:2380`; `navigation_map.it.md:43`, solo il mio percorso.
>   `themeRoles.baseline.tsv` non si tocca.
> - **Applicato**: `python3 /tmp/libreFolio_a2_rewrite.py --extra` sui 4 file. Il diff ha esattamente quelle 7 righe.
> - **Prima, senza le righe**: il gate dava rosso su `supportLinks.ts`, già accoppiato al file vecchio («was
>   lib/components/support/supportLinks.ts»), con R2 m2 e 11 G4 sui colori dei marchi, più R1 sul totale m2 (da 1 782 a
>   1 793).
> - **Dopo**: `node frontend/scripts/theme/theme-roles.mjs --check` → «Colour gates: clean». `--report` → «Ratchet: 0
>   violations, 0 files dropped (--update tightens), **22 moves recognized**. Grammar: 0 violations.»: sono le 22 righe
>   della baseline.
>
> **⚠️ Fuori pista**: l'inventario non vedeva che lo script del cricchetto lega un'eccezione al percorso esatto di un
> file. Per gli spostamenti puri il gate accoppia le righe della baseline per nome, ma non le sue tabelle di eccezioni.

#### A2.5 — Documentazione per sviluppatori (`docs-writer`) ✅ (2026-10-15)
> **Note implementazione**:
> - **Le 9 citazioni**, in 5 pagine:
>   - `architecture/settings_cache.md:103`;
>   - `frontend/components/core-ui/modals.md:129`;
>   - `frontend/components/features/auth.md:38`, `:71`;
>   - `frontend/components/features/settings.md:43`, `:207`, `:208`;
>   - `frontend/i18n.md:283`, `:314`.
> - **Disegno «Directory Structure»** di `frontend/index.md`: tolte le righe `auth/` e `settings/` sotto
>   `components/`, aggiunto un nodo `features/` con quelle due. Il commento del nodo («One folder per domain: its
>   components, state and logic») l'ho aggiunto io, come le altre voci di `lib/`.
>   - Il disegno era già incompleto: senza `features/`, e con metà delle cartelle di `components/` (segnalato da FE1).
> - **Prove**:
>   - `grep -rn -E "components/(auth|settings|support)/" mkdocs_src/docs/developer`: vuoto;
>   - `dev.py mkdocs build` (strict): exit 0;
>   - `dev.py mkdocs check-links`: exit 0, 95 link validi.

#### A2.6 — Controlli statici ✅ (2026-10-15)
> **Note implementazione**:
> - **Grep dei vecchi percorsi** in `frontend/`, `scripts/`, `.github/`, `backend/` e `mkdocs_src/docs/developer/`: resta
>   solo il percorso inventato `test_docs_links_gate.py:87`, voluto.
> - **`dev.py front build --debug`** (dopo lo spostamento): exit 0, svelte-check «0 errors and 0 warnings».
> - **`dev.py front check`**: exit 0, «0 errors and 0 warnings».
> - **Prettier** (`frontend/node_modules/.bin/prettier --check`), sui file spostati e modificati: tutti a posto.
> - **`check_source_paths.py`**: 5 percorsi mancanti (8 occorrenze), tutti generati e già mancanti
>   (`htmlcov-*`, `frontend/coverage-js/`, una cartella di sonde); nessuno di quelli spostati. Il numero dipende da
>   cosa c'è sul disco: `frontend/build/`, `generated.ts` e `backend/data/prod/` ora esistono.
> - **File**: 44 cancellati, 44 nuovi (esattamente gli spostati), 35 modificati.

#### A2.7 — Test ✅ (2026-10-15)
> **Note implementazione** (corsia 6182):
> - `front-utility core-unit`: 130 file, **4 245 test**, come la base (contiene i gate dei colori).
> - `front-utility component-unit`: 118 file, **3 162 test**, come la base.
> - `front-utility onboarding-component-unit`: 15 file, **437 test**, come la base.
> - E2E (`/tmp/libreFolio_a2_e2e.sh`, sul frontend ricostruito dopo lo spostamento), tutte exit 0:
>   - `front-utility auth`: 29;
>   - `front-utility settings`: 45;
>   - `front-utility scheduler`: 17;
>   - `front-utility support-copy-and-go`: 16;
>   - `front-user account-deletion`: 1;
>   - `front-utility onboarding-tour`: 10;
>   - `front-utility theme-roles`: 8;
>   - `front-utility changelog-locale`: 2.
> - `check-orphans`: 364 test unitari e 118 spec registrati e raggiungibili da `all`.
> - knip (`dev.py lint --dead-code --scope frontend`): identico alla base, una volta normalizzati i prefissi spostati.
>   L'unico reperto nelle cartelle toccate, `isImagePublished` in `update-check/updateCheck.ts`, c'era già.
> - Porta 6182 libera dopo le run.

#### A2.8 — Due commenti sfuggiti ad A1 ✅ (2026-10-15)
> **Note implementazione**:
> - Segnalati da H tramite il coordinatore e corretti in questo lotto:
>   - `frontend/e2e/files-uploader.spec.ts:71` → `backend/app/services/accounts/onboarding_service.py`;
>   - `frontend/src/lib/stores/app/settings.test.ts:18` → `backend/app/services/accounts/global_settings_service.py`.
> - Prettier: a posto.
> - Grep dei percorsi completi dei sei moduli in tutto il repo (fuori dal journal e da `TODO_Completati.md`): restano
>   la cache di graphify, che è generata, e la prosa della devWiki (A-4).
> - Restano due nomi senza cartella, ancora giusti perché il nome non è cambiato: `stores/app/auth.ts:118`
>   (`donation_popup_service.py`) e `stores/app/globalSettings.ts:44` (`global_settings_service.py`).
>
> **⚠️ Fuori pista**: in A1 la riscrittura copriva `backend/`, `scripts/`, `dev.py`, `.github/` e la devWiki, non
> `frontend/`. Il grep di chiusura aveva lo stesso perimetro, quindi non poteva trovarli.

### Checkpoint A2 (CP2) 🧊 (2026-10-15, notte) — FROZEN, in attesa del commit del coordinatore
> - **Delta** (non in stage, sulla base `769cc31cb`):
>   - 44 file spostati;
>   - 36 file di codice, documentazione e devWiki modificati;
>   - in più questo piano e la sezione A del backlog.
> - **Conflitti attesi con `dev_release2`** (`8250d92b3`, che contiene H CP1): due file in comune, nessun conflitto
>   previsto.
>   - `decisions/scheduler-converts-at-decision.md`: H tocca le righe 95-96, A la 99.
>   - Backlog: ognuno scrive nella sua sezione.
> - **Commit proposti**:
>   1. `refactor(frontend): move auth/settings/support UI`;
>   2. `docs(journal): A2 frontend move, A backlog`.
> - **Ingresso in `dev_release2`**: prima delle 08:45 o dopo la finestra della galleria. Fra le 08:00 e le 08:45
>   aspetta il via del coordinatore.
>
> **Esito**: il coordinatore ha committato `73b8cbebd` (`refactor(frontend): move auth/settings/support UI`: 44
> rinomine, 39 al 100 % e le altre fra il 94 % e il 99 %) e `40146a5d9` (journal). Poi ha aggiornato la base con il merge
> `54f872995` di `dev_release2` a `8250d92b3`, che contiene H CP1: unione automatica, worktree pulito.

#### A2.9 — Validazione leggera della revisione combinata `54f872995` ✅ (2026-10-15)
> **Note implementazione** (`bash /tmp/libreFolio_a2v_validate.sh`, corsia 6182):
> - **Cosa porta il merge**: H CP1 cambia 68 file del backend e degli script. Nel frontend cambia solo un commento di
>   `update-check/updateCheck.test.ts`, quindi la build del frontend di A2 resta valida. Lock delle dipendenze
>   invariati.
> - `dev.py front check`: exit 0, «0 errors and 0 warnings».
> - `front-utility core-unit`: 130 file, **4 245 test**, come prima.
> - `node frontend/scripts/theme/theme-roles.mjs --check`: «Colour gates: clean». `--report`: «Ratchet: 0 violations,
>   0 files dropped, 22 moves recognized. Grammar: 0 violations».
> - E2E sul backend riordinato da H: `front-utility auth` 29 passati, `front-utility settings` 45 passati.
> - Porta 6182 libera, worktree pulito dopo le prove.
>
> **Esito**: il coordinatore ha integrato A2 in `dev_release2` con un avanzamento veloce a `76e61889b`, che contiene
> anche questo journal. Il ramo coincide con `dev_release2`.

### A3 — registro delle schede, O-15, K-17, L12 (CP3) — in corso

#### A3.0 — Via e base ✅ (2026-10-15)
> Via del coordinatore (15/10, ~01:04), alla lettera: «**Via per A3**: registro delle schede di Impostazioni, O-15,
> K-17 e L12. Checkpoint FROZEN alla fine. Ricorda le regole di T-1: un file frontend nuovo, come il runtime del
> registro, nasce senza classi di palette. K-17 su `PasswordInput` si somma alla prop `icon` di T.»
>
> **Note implementazione**:
> - HEAD `76e61889b` = `dev_release2` all'integrazione di A2, worktree pulito.
> - Finestra della galleria dalle 09:00: niente `all-backend` né build pesanti; il lotto entra prima delle 08:45 o
>   dopo la chiusura.
> - **TC-6** (programma colori, 15/10): alla prima visita con il browser in `it-IT` il selettore della lingua mostra
>   l'inglese. La riga che la richiama va nella mia sezione del backlog al checkpoint; la correzione va in un lotto
>   che tocca la pagina d'accesso o le preferenze, con il rosso visto prima.

#### A3.1 — Disegno verificato sul codice ✅ (2026-10-15)
> **Note implementazione**:
> - **Registro** `lib/features/settings/settingsTabs.ts`:
>   - campi `{id, labelKey, icon, order, component, visible?(ctx), props?(ctx), alignEnd?}`;
>   - contesto `{isSuperuser}`;
>   - `visibleSettingsTabs(tabs, ctx)` filtra e ordina, e riceve l'elenco in modo esplicito, così un test può dargli
>     un elenco finto.
> - **Le 4 schede di oggi**:
>   - `admin` resta visibile a tutti, modificabile solo dall'admin (`props: ctx => ({canEdit: ctx.isSuperuser})`);
>   - `alignEnd` prende il posto di `className: 'sm:ml-auto'`.
> - **Pagina** in rune, con lo stesso markup e le stesse classi, quindi il cricchetto dei colori non sale.
>   - `?tab=` vale solo per l'id di una scheda visibile, e solo quando cambia.
>   - `$effect.pre`, come il `$:` di prima: la scheda giusta c'è già al primo disegno, e non si monta ProfileTab per
>     un istante.
> - **O-15**: il tipo `AuthError` perde la variante `{message}`, che nessuno produce più.
>
>   | Caso | Chiave |
>   |---|---|
>   | nessuna risposta, 502, 503, 504 | `auth.loginServerUnreachable` |
>   | altri 5xx | `auth.loginServerError` (un 500 non è «non raggiungibile») |
>   | 429 | `auth.tooManyAttempts` (§4.11; A8 aggiungerà il proprio 429) |
>   | ogni altro stato | `auth.loginFailed` |
>
>   401, 403 `ACCOUNT_DISABLED` e 422 restano come oggi.
> - **K-17**: due chiavi, `auth.showPassword` e `auth.hidePassword`.
>   - `aria-label` e `title` cambiano con lo stato; `tabindex="-1"` se ne va.
>   - **Niente `aria-pressed`**: un pulsante a interruttore il cui nome cambia non deve averlo (WAI-ARIA APG), e il
>     nome che dice l'azione è lo schema di GOV.UK. Il §4.11 lo prevedeva: è una correzione del mio disegno.
> - **L12**:
>   - il popolamento di prova crea già ognuno col ruolo giusto (`populate_mock_data.py:481-493`), quindi il
>     `create-superuser` del runner e di `global-setup.ts` vale solo se l'utente manca;
>   - nuovo comando interno `create-user`;
>   - `dev.py user create … [--role admin|user]`, con `admin` di default come oggi;
>   - il runner e `global-setup.ts` creano gli utenti normali con `create-user`.

#### A3.2 — Test rossi (`test-author`) ✅ (2026-10-15)
> **Note implementazione**:
>
> | File | Test | Rossi prima dell'implementazione, e perché |
> |---|---|---|
> | nuovo `features/settings/settingsTabs.test.ts` (`core-unit`) | 16 | tutti: il modulo non esiste |
> | nuovo `routes/(app)/settings/page.tabs.test.ts` (`component-unit`) | 18 | tutti: la pagina disegna le 4 schede a mano |
> | nuovo `__tests__/harness/SettingsTabProbe.svelte` | — | corpo finto delle schede, senza classi di palette |
> | `stores/app/auth.test.ts` | 53 → 74 | 30: il testo grezzo di axios e le 3 chiavi che mancano |
> | `features/auth/LoginCard.test.ts` | 22 → 24 | 0 a runtime; rosso solo per i tipi, finché l'unione delle chiavi non cresce |
> | `components/ui/input/PasswordInput.test.ts` | 8 → 18 | 8: `title` inglese, `tabindex="-1"`, chiavi assenti |
> | `test_dev_cli_image.py` (IMG-011, IMG-012) | 31 → 39 | 6: `--role` e `create-user` sconosciuti (exit 2) |
>
> - I casi che fissano il comportamento che resta sono verdi già sulla base: 401, 422, `ACCOUNT_DISABLED`,
>   ciclo di vita dell'errore, `type="button"`, `create-superuser` e `user create` senza ruolo.
> - `test-author` ha verificato i test su un'implementazione di riferimento usa e getta, poi cancellata.
>   Ha anche rotto quell'implementazione di proposito, un difetto alla volta, e ogni difetto ha fatto
>   cadere il test giusto (per esempio `$effect` al posto di `$effect.pre` fa montare la scheda di default
>   per un istante).
> - Registrazione nel runner e `check-orphans` puliti; nessun test copre `_ensure_test_users`.

#### A3.3 — Implementazione ✅ (2026-10-15)
> **Note implementazione**:
> - **Registro**: nuovo `features/settings/settingsTabs.ts`.
>   - `order`: 10, 20, 30, e 100 per l'admin, con spazi per le schede nuove.
>   - Le schede da `alignEnd` in poi formano il gruppo di destra.
> - **Pagina** `routes/(app)/settings/+page.svelte` in rune: markup e classi identici; `$effect.pre` sceglie la scheda
>   prima del primo disegno, con `untrack` sulla scheda attiva, così un clic non riesegue l'effetto. Se la scheda
>   attiva smette di essere visibile si apre la prima visibile.
> - **O-15**:
>   - `types/user.ts`: `AuthError` = `{key}` e basta, con 3 chiavi nuove;
>   - `stores/app/auth.ts`: la mappatura sta in `loginErrorKey(status, body)`;
>   - `LoginCard.svelte`: `{$_($authError.key)}`.
> - **K-17**: `PasswordInput.svelte`, con `aria-label` e `title` = `$_(auth.showPassword | auth.hidePassword)` e senza
>   `tabindex`; formattato con Prettier.
> - **i18n**: 5 chiavi nella sorgente `auth/` (`/tmp/libreFolio_a3_i18n_add.sh`): `loginServerUnreachable`,
>   `loginServerError`, `tooManyAttempts`, `showPassword`, `hidePassword`.
> - **L12**:
>   - `scripts/user_cli.py`: `cmd_create_user(…, is_superuser)` al posto di `cmd_create_superuser`, comando interno
>     `create-user`, `dev.py user create … [--role admin|user]`;
>   - `_frontend_common.py::_ensure_test_users` e `e2e/global-setup.ts` creano gli utenti normali con `create-user`
>     e solo `e2e_test_admin` con `create-superuser`; il passo `promote` resta.
> - **A-5, la parte di `user_cli.py`**: black, W293 e PLC0415 sistemati (`set_test_mode` importato in cima:
>   `backend.app.config` lo importava già `db.session`).
>
> **⚠️ Fuori pista**:
> - Il ramo in più portava `_dispatch_user_command` a C901 (11 > 10): ora è una tabella comando → azione.
> - Niente `aria-pressed`: lo chiedeva il §4.11, ma un pulsante il cui nome cambia non deve averlo (WAI-ARIA APG).

#### A3.4 — Pagina `admin/cli_tools` in 4 lingue ✅ (2026-10-15)
> **Note implementazione**:
> - en/it/fr/es: un esempio `--role user` e il primo punto riscritto («`user create` crea un amministratore, a meno
>   che tu non aggiunga `--role user`»).
> - Timbro di traduzione legittimo: prima della modifica l'MD5 della cache (`02fa5f95…`) era quello di HEAD,
>   con `langs_done` es/fr/it. `dev.py mkdocs translate-stamp --file admin/cli_tools.en.md` (prova a vuoto prima):
>   `02fa5f95 → df53c747`.

#### A3.5 — Doc per sviluppatori (`docs-writer`) e devWiki ✅ (2026-10-15)
> **Note implementazione** (solo modifiche: build e link li ho lanciati io dopo, perché la corsia era occupata):
> - `frontend/components/features/settings.md`:
>   - sezione nuova «🗂️ Tab registry» (`#tab-registry`), con campi, le 4 schede, il runtime della pagina e la regola
>     di `?tab=`;
>   - «come aggiungere una scheda», con esempio, spazi di `order`, `visible`, `props`, `alignEnd` e la riga nella
>     tabella `TODAY` del test;
>   - il paragrafo di GlobalSettingsTab ora parla delle `props` del registro.
> - `frontend/pages/index.md`: le 4 schede vengono dal registro, più la regola di `?tab=`.
> - `frontend/components/features/auth.md`: la mappatura di `loginErrorKey` (O-15) e il pulsante occhio (K-17).
> - `frontend/components/core-ui/atoms.md`: il pulsante occhio (K-17).
> - `architecture/access_control.md`: `user create` crea un admin solo di default; `--role user` crea un account
>   normale (L12).
> - `architecture/database/users_access.md:66`: lo stesso.
> - devWiki `domains/layout-settings.md`: una decisione («le schede vengono da un registro») e 3 righe nella tabella
>   «Source files».
> - `check_source_paths.py`: gli stessi 5 percorsi generati di A2, nessuno nuovo.
>
> **⚠️ Fuori pista**: `docs-writer` ha trovato delle derive fuori da A3, registrate come A-7 nel backlog:
> - `access_control.md:116-123`, sulle regole dell'ultimo admin e sul 403 `ACCOUNT_DISABLED`: si allinea in A6;
> - il titolo della scheda globale «(Admin only)»: in A6;
> - «JWT tokens» in `state/app-state.md:11`: in A4;
> - la prop `icon` di T che manca nella doc: la segnalo al coordinatore.

#### A3.6 — Controlli statici ✅ (2026-10-15)
> **Note implementazione** (`/tmp/libreFolio_a3_validate1.sh`):
> - `dev.py front check`: «0 errors and 0 warnings».
> - `dev.py i18n check`: pulito, 4 365 chiavi.
> - Cancello dei colori, `--check`: «clean». `--report`: «Ratchet: 0 violations, 0 files dropped, 22 moves
>   recognized. Grammar: 0 violations».
>   - Il file nuovo `settingsTabs.ts` non ha classi.
>   - `SettingsTabProbe.svelte` non ha classi di palette.
>   - La pagina tiene le stesse classi.
> - Prettier: pulito sui file toccati. `PasswordInput.svelte` è stato riformattato: il pulsante va su più righe.
> - ruff e black puliti su `scripts/user_cli.py`, sui file del runner e su `test_dev_cli_image.py`.
> - knip (`dev.py lint --dead-code --scope frontend`): identico allo stato dopo A2 (exit 1 già alla base),
>   nessun reperto nei file nuovi.
> - `check-orphans`: 366 test unitari registrati e raggiungibili.

#### A3.7 — Test ✅ (2026-10-15)
> **Note implementazione** (corsia 6182, una invocazione alla volta; `/tmp/libreFolio_a3_validate1.sh` e `…2.sh`):
>
> | Suite | Esito | Rispetto alla base |
> |---|---|---|
> | `front-utility core-unit` | 131 file, **4 261** test | 130/4 245, più `settingsTabs.test.ts` (16) |
> | `front-utility component-unit` | 119 file, **3 192** test | 118/3 162, più `page.tabs` (18), `PasswordInput` (+10), `LoginCard` (+2) |
> | `front-utility onboarding-component-unit` | 15 file, **437** test | come la base |
> | `front-user user-unit` | 2 file, **78** test | `auth.test.ts` da 53 a 74 |
> | `utils dev-cli-image` | **39** passati | da 31, più IMG-011 e IMG-012 |
>
> - Prima delle E2E: `dev.py front build --debug` (exit 0, svelte-check 0/0), `dev.py mkdocs build` (exit 0) e
>   `mkdocs check-links` (95 link validi).
> - E2E, tutte exit 0:
>   - `front-utility auth`: 29;
>   - `front-utility settings`: 45;
>   - `front-utility app-start-auth`: 3;
>   - `front-utility onboarding-guides`: 24, apre `/settings?tab=preferences`;
>   - `front-utility theme-roles`: 8, legge `PasswordInput`;
>   - `front-user account-deletion`: 1.
> - `_ensure_test_users` è passato con `create-user`: «Test users ready». Nella base della corsia solo
>   `e2e_test_admin` è admin (`user_cli.py --test-db list-users`).
> - Porta 6182 libera dopo le run. `git diff --check` pulito.
> - Non eseguiti:
>   - `all-backend`: il codice dell'app backend non cambia, cambiano solo `scripts/user_cli.py` e un test;
>   - la suite E2E completa e la galleria: il markup della pagina delle impostazioni è lo stesso.

### Checkpoint A3 (CP3) 🧊 (2026-10-15, notte) — FROZEN, in attesa del commit del coordinatore
> - **Delta** sulla base `76e61889b`, non in stage:
>   - 4 file nuovi;
>   - 30 file di codice, test, documentazione e devWiki modificati;
>   - in più questo piano, la sezione A del backlog e le chiusure di O-15, K-17 e L12 nel README del backlog 38.
> - **Conflitti attesi con `dev_release2`** (`75a20ce29`): tre file in comune, su righe diverse.
>   - `BACKLOG_POST_1.2.md`: ognuno scrive nella sua sezione.
>   - `access_control.md`: l'altra parte tocca le righe 87-92, io le 110-115.
>   - `_backend_utils.py`: l'altra parte tocca la riga 112, io le 194 e 422.
>   - Semantica: `user_cli.py` importa `set_test_mode` in cima, e il pacchetto `config` di H lo esporta ancora
>     (`config/__init__.py:63`).
> - **Commit proposti**:
>   1. `feat(accounts): tab registry, O-15, K-17, L12`;
>   2. `docs(journal): A3 progress, A and 38 backlog`.
> - **Ingresso in `dev_release2`**: prima delle 08:45 o dopo la finestra della galleria.
>
> **Esito**: il coordinatore ha committato `755eaa27d` (`feat(accounts): tab registry, O-15, K-17, L12`: 4 file
> aggiunti, 30 modificati) e `a8eefdb44` (journal; le chiusure nel README del 38 vanno bene). Poi ha aggiornato la
> base con il merge `35f1e0a16` di `dev_release2` a `75a20ce29`: unione automatica di backlog, `access_control.md` e
> `_backend_utils.py`, albero uguale alla simulazione, worktree pulito. Il merge porta W1 e W2 (`transactions/`,
> `brokers/`), H CP2a (pacchetto `config/` e guardia su `os.environ`), X CP1 e CP2a (registri per famiglia,
> `services/assets/`).
>
> Indicazioni del coordinatore (15/10, ~02:24):
> - **CHANGELOG**: lo aggiorna lui all'ingresso, con le tre righe proposte.
> - **T-B4 → TC-4**: il coordinatore colori rinomina la sua sezione col prefisso `TC-` il 15/10, con T-3. Poi
>   aggiorno il richiamo in A-6 e in questo piano.
> - **Lotti successivi**, un checkpoint FROZEN ciascuno:
>   - A4: migrazione 005 e token; la parte delle sessioni (`sv`) dopo il CP3 di H, che fa i segreti;
>   - A5: inviti, limite, API admin, link di reset. Le regole uniche della password aspettano la decisione 37 del
>     developer;
>   - A6: scheda Utenti, con l'eliminazione degli utenti;
>   - A8: limite dei tentativi e scheda «Sicurezza».
> - **Contratto della scheda «Sicurezza»** (A8), alla lettera: «un registro aperto di controlli che altre sessioni
>   possono usare. Un controllo è id, gravità, chiave i18n e dettaglio, valutato a richiesta da un endpoint solo per
>   admin. H ci registrerà i suoi avvisi di configurazione: segreto JWT corto, `NOME` e `NOME_FILE` insieme, permessi
>   larghi sulla chiave d'istanza, cookie `never`. Tienilo semplice, ma usabile da un'altra sessione.»
> - H ha preparato `backend/app/config/accounts.py` per A, con `donation_popup_disabled()`: le variabili nuove di A
>   vanno lì. La catena delle migrazioni arriva alla 004: la 005 resta di A.

#### A3.8 — Validazione completa della revisione combinata `35f1e0a16` ✅ (2026-10-15)
> Richiesta del coordinatore: build, `front check`, core-unit, component-unit, cancello dei colori;
> `utils dev-cli-image` e `services config-package` («`user_cli.py` non deve leggere `os.environ` fuori da
> `config/`»); `all-backend`; E2E `auth`, `settings`, `app-start-auth`, `onboarding-guides`.
>
> **Note implementazione**:
> - Il guardiano di `config-package` scandisce solo `backend/app/`, quindi `scripts/user_cli.py` resta fuori dal suo
>   perimetro. L'ho controllato a mano, con il rilevatore del test
>   (`test_config_package._environment_accesses`): `reads=[]`, `writes=[]`.
>   - `user_cli.py` cambia il modo di test solo con `set_test_mode()`, che il pacchetto `config` esporta ancora.
>   - Le letture dell'ambiente in `scripts/test_runner/_frontend_common.py` c'erano già, e la regola vale per
>     `backend/app/`.
> - **Esito** (`bash /tmp/libreFolio_a3c_validate.sh`, corsia 6182, dalle 02:24 alle 02:57, tutto exit 0):
>   - `dev.py front build --debug` e `front check`: svelte-check «0 errors and 0 warnings».
>   - `dev.py mkdocs build`: exit 0, per tenere l'avvio del server dentro i 300 s.
>   - Vitest:
>     - `core-unit`: 131 file, **4 261** test;
>     - `component-unit`: 119 file, **3 192** test;
>     - `user-unit`: 2 file, **78** test.
>
>     Sono gli stessi numeri di A3.7: il merge non tocca i test frontend.
>   - Cancello dei colori: `--check` «clean»; `--report` «Ratchet: 0 violations, 0 files dropped, 22 moves
>     recognized. Grammar: 0 violations».
>   - `check-orphans`: 366 unitari, 118 E2E e 264 file backend registrati e raggiungibili da `all`.
>   - `utils dev-cli-image`: **39** passati. `services config-package`: **472** passati.
>   - **`all-backend`**: uscita 0, **7/7 categorie verdi**, 20 min (02:30 → 02:51).
>     - 23 righe di riepilogo pytest: **13 440 passati, 28 saltati, 0 falliti**.
>     - In A1.9 erano 12 965: la differenza viene dai lotti entrati con il merge (fra cui `config-package`, 472) e
>       dagli 8 test IMG-011 e IMG-012.
>   - E2E sul backend riordinato da W, H e X:
>     - `front-utility auth`: 29;
>     - `front-utility settings`: 45;
>     - `front-utility app-start-auth`: 3;
>     - `front-utility onboarding-guides`: 24.
>   - In ogni run E2E `_ensure_test_users` stampa «Test users ready», senza errori. Nella base della corsia c'è un
>     solo 👑, `e2e_test_admin`.
>   - Porta 6182 libera. Worktree: cambia solo questo piano.
>
> **Esito**: il coordinatore ha committato questo piano in `211a05e0b` (`docs(journal): A3 combined validation`).
> Poi ha aggiornato la base con il merge `d851c39bc` di `dev_release2` a `f39be79b7`, che porta W I1: backend di
> transazioni e broker, `TransactionBulkModal.svelte`, `e2e/transactions/tx-broker-access.spec.ts` e il cancello
> `utils gate-event-loop-io`, unito da solo in `_backend_utils.py`. Merge pulito, worktree pulito.

#### A3.9 — Validazione mirata della revisione `d851c39bc` ✅ (2026-10-15)
> **Note implementazione** (`bash /tmp/libreFolio_a3d_validate.sh`, corsia 6182, dalle 03:06 alle 03:16, tutto exit 0;
> niente `all-backend`, su indicazione del coordinatore: A3 non tocca `backend/app/`, e il backend di W lo valida W):
> - `dev.py front build --debug` e `front check`: svelte-check «0 errors and 0 warnings».
> - Vitest: `core-unit` 131 file e **4 261** test; `component-unit` 119 file e **3 192** test.
> - `theme-roles.mjs --check`: «clean».
> - `check-orphans`: 366 unitari, 118 E2E e **265** file backend (più `test_event_loop_brim_io_gate.py` di W).
> - `utils dev-cli-image`: **39** passati; `utils gate-event-loop-io`: **14** passati.
> - `dev.py mkdocs build`: exit 0, perché il merge cambia due pagine e il server ricostruisce il sito dentro i 300 s.
> - E2E: `front-utility auth` **29**, `front-utility settings` **45**, `front-transaction tx-broker-access` **5**.
> - Tutti i conteggi sono quelli attesi dal coordinatore. `git diff --check` pulito, porta 6182 libera.
>
> **Esito**: il coordinatore ha integrato A3 in `dev_release2` con un avanzamento veloce a `90491071d`, che contiene
> questo journal. Sopra ha messo il suo commit di record `0ddd296a0`, con le 3 righe nel CHANGELOG. Il ramo è
> avanzato a `0ddd296a0`.

### A4 — migrazione 005, modelli e token (CP A4) — in corso

#### A4.0 — Via, base e taglio ✅ (2026-10-15)
> Via del coordinatore (15/10, ~03:19), alla lettera: «**Via per A4**: migrazione 005 e token. La parte delle
> sessioni (`sv`) aspetta il CP3 di H.» Base `0ddd296a0`, worktree pulito, porta 6182 libera.
>
> **Taglio**: l'ho chiesto io (needs_input, 03:25), il coordinatore ha approvato alle 03:3x.
> - **A4 solo backend**: 005 con la tabella `account_tokens` e le colonne nuove di `users`, i modelli e
>   `token_service`.
>   - **`registration_mode` passa in A5**, con la sua migrazione **006** (conversione di `enable_registration`), il
>     codice, l'interfaccia, la doc e la galleria.
>   - Motivo: cambiare nome alla riga obbliga a cambiare insieme codice e dati, frontend compreso, e il blocco da
>     variabile ha bisogno di `/system/instance` (CP4 di H).
> - **Catena**: le impostazioni dei plugin di X diventano la **007**. Regola C7 aggiornata nel piano generale
>   (`ed29f77c2`): chi entra dopo riallinea `down_revision` all'aggiornamento di base.
> - **`email_verified_at`**: `NULL` sugli utenti esistenti, senza riempimento. Come trattarli quando si attiva
>   `require_email_verification` lo decide E, nella logica e non nei dati.
> - **Ingresso**: prima delle 08:45 se `all-backend` è verde entro allora; altrimenti dopo la finestra della galleria.
> - **Per A5**: toccherà `e2e/layout/theme-roles.spec.ts` del programma colori, da segnalare nell'handoff.

#### A4.1 — Disegno verificato sul codice ✅ (2026-10-15)
> **Note implementazione**:
> - **Migrazione `005_accounts_invites`** (20 caratteri), `down_revision = 004_release_1_2_0_schema`.
>   - Segue la 004: `ALTER TABLE users ADD COLUMN` grezzo e idempotente (controllo con `PRAGMA table_info`), mai un
>     batch su `users`; `op.create_table` per la tabella nuova; `ALTER TABLE … DROP COLUMN` nel downgrade.
>   - Le migrazioni girano con `foreign_keys=ON`: il listener delle `PRAGMA` è globale su `Engine`
>     (`db/session.py`).
>   - `users`: `session_version INTEGER NOT NULL DEFAULT 0`, `email_verified_at DATETIME NULL`,
>     `last_seen_version VARCHAR(40) NULL`. `session_version` entra già adesso, anche se la sua logica (`sv`)
>     aspetta il CP3 di H, così A non ha bisogno di un'altra migrazione.
>   - `account_tokens`:
>     - `purpose` (CHECK sui 4 scopi); `token_hash` (SHA-256 esadecimale, unico); `user_id` (FK, CASCADE);
>       `email`; `grants_admin`; `created_by_user_id` (FK, SET NULL); `created_at`, `expires_at`, `consumed_at`,
>       `revoked_at`; `consumed_by_user_id` (FK, SET NULL);
>     - indici su `(purpose, expires_at)` e su `user_id`.
>   - Niente AUTOINCREMENT: il censimento D1 del developer è di 6 tabelle, e `test_autoincrement_schema.py` lo fissa.
>     Gli id non si riusano comunque: i token non si cancellano, si consumano o si revocano. Solo la cancellazione
>     di un utente toglie, a cascata, i suoi token di reset, verifica e setup.
> - **Modelli**: `AccountTokenPurpose` (StrEnum) e `AccountToken`; tre campi nuovi su `User`, senza
>   `server_default`, come `login_count`.
> - **`services/accounts/token_service.py`**:
>   - `issue_token`, `inspect_token`, `consume_token`, `revoke_tokens`, `hash_token`, `token_path`, `DEFAULT_TTL`;
>   - scadenze: invito 7 giorni, reset 30 minuti, setup 72 ore, verifica dell'email 24 ore (E può cambiarla);
>   - flush senza commit: il consumo di un invito e la creazione dell'utente stanno in una sola transazione del
>     chiamante;
>   - il consumo atomico è un solo `UPDATE … WHERE` con `rowcount == 1`. Il DB è in WAL con `busy_timeout`.
>   - Le date: `utcnow()` ha il fuso, SQLite le rilegge senza, e `ensure_utc()` le normalizza.
> - **Test che il cambio rompe**: `db_schema_validate.py::test_onboarding_migration_chain_has_exactly_one_head_at_004`
>   fissa la head alla 004. Va riscritto per controllare solo che la head sia una, così regge anche la 006 e la 007.
> - **vulture**: finché A5 non chiama `token_service`, le sue funzioni finiscono nel gruppo «referenced only by
>   tests». È uno stato di passaggio, da dichiarare nell'handoff.
>
> **Aggiornamento del coordinatore (15/10, ~03:47)**: H CP3 è in `dev_release2` (`d08d9358f`) e arriva nella mia base
> all'aggiornamento del checkpoint di A4. Regole per una variabile d'ambiente nuova (guardie `services config-package`
> e `services config-env-example`):
> - si legge solo in `backend/app/config/accounts.py`, con un accessore;
> - un segreto si chiama `LIBREFOLIO_*` e si legge con `env_secret()`, così vale anche `NOME_FILE`;
> - la variabile va in `.env.example`, nella sezione account, come riga commentata col default.
>
> Per `sv`: CP3 legge il segreto JWT anche da `JWT_SECRET_FILE`, e un valore vuoto o di soli spazi vale come assente.
> Quindi `sv` si fa **dopo** l'aggiornamento di base che porta CP3, sui file di `auth_service` già toccati da H, come
> secondo passo di A4 con un suo checkpoint.

#### A4.2 — Test rossi (`test-author`) ✅ (2026-10-15)
> **Note implementazione**:
>
> | File | Test | Prima dell'implementazione |
> |---|---|---|
> | nuovo `test_db/test_migration_005_accounts.py` (`db migration-005`, anche in `db all`) | 25 | tutti rossi: revisione assente, colonne e tabella mancanti |
> | nuovo `test_services/test_account_tokens.py` (`services account-tokens`) | 64 | errore di raccolta: `AccountToken` non esiste |
> | `test_db/db_schema_validate.py` (contratto B) | 17 | verdi |
>
> - Le due voci nuove sono `isolation="pure"`, con la ragione scritta: ogni DB è un file privato sotto `tmp_path` e
>   non c'è server.
> - **Contratto B**: il test della head ora si chiama
>   `test_migration_chain_has_exactly_one_head_and_004_keeps_its_parent`. Controlla una head sola e il genitore della
>   004, senza nominare la head, così regge la 006 e la 007.
> - **Migrazione**:
>   - Alembic gira nel processo del test, sempre con `-x sqlalchemy.url=`. Un listener rifiuta ogni file diverso dal
>     DB temporaneo e controlla che `PRAGMA foreign_keys` sia 1 in ogni passo.
>   - L'«installazione 1.2» è lo schema reale della v1.1.0 con le sue righe (`_install_v110` di
>     `test_post_migration`), portata alla 004, con `run_post_migration_fixes` e con righe scritte solo dalla 1.2.
> - **Prova dei test**: `test-author` ha scritto un'implementazione di riferimento fuori dal repo, che li passa
>   tutti (89), e 27 sue versioni con un difetto ciascuno, tutte prese da almeno un test. Fra i difetti: un batch su
>   `users` nel downgrade, un consumo non atomico, il confine della scadenza sbagliato di uno, un commit nel servizio,
>   il token in chiaro nei log, modello e migrazione disallineati.

#### A4.3 — Implementazione ✅ (2026-10-15)
> **Note implementazione** (bozze scritte in `/tmp/libreFolio_a4_drafts/` durante il rosso, poi copiate):
> - `backend/alembic/versions/005_accounts_invites.py`: le colonne di `users` con `ALTER TABLE` idempotente, poi
>   `account_tokens` con `op.create_table` e gli indici con `CREATE INDEX IF NOT EXISTS`. Così un'esecuzione
>   interrotta fra la tabella e un indice si può ripetere. Il downgrade fa `DROP TABLE` e `DROP COLUMN`.
> - `backend/app/db/models.py`: `AccountTokenPurpose`, `AccountToken` con indici nominati in `__table_args__` (niente
>   `index=True`, che `create_all` duplicherebbe), tre campi su `User`.
> - `backend/app/services/accounts/token_service.py`:
>   - `consume_token` e `revoke_tokens` sono un solo `UPDATE` condizionato ciascuno;
>   - `_find` rilegge sempre dal DB (`populate_existing`), così la riga restituita non è mai una copia vecchia della
>     sessione;
>   - la scadenza si confronta con `ensure_utc` in Python e con le date SQL in UTC nel DB;
>   - log strutturati senza token, né in chiaro né come hash.
> - ruff e black puliti.

#### A4.4 — Test verdi ✅ (2026-10-15)
> **Note implementazione** (`bash /tmp/libreFolio_a4_green.sh`, corsia 6182):
> - `services account-tokens`: **64** passati. `db migration-005`: **25** passati.
> - `db create` (rifà il DB della corsia alla head), poi:
>   - `db validate`: 17;
>   - `db autoincrement-schema`: 4, quindi niente AUTOINCREMENT su `account_tokens`;
>   - `db post-migration`: 37, l'upgrade della 1.1 ora passa anche dalla 005;
>   - `db referential-integrity`: 17;
>   - `db model-validators`: 36;
>   - `db populate-reset`: 25.
> - **API invariata**: lo schema OpenAPI esportato (113 percorsi, 586 schemi) non contiene nessuno dei nomi nuovi
>   (`session_version`, `email_verified_at`, `last_seen_version`, `AccountToken`, `token_hash`, `grants_admin`, gli
>   scopi). Nessun endpoint espone il modello `User`, quindi non serve `api sync`.
> - **vulture** (`dev.py lint --dead-code --scope backend`): 5 reperti nuovi, le funzioni pubbliche di
>   `token_service` nel gruppo «referenced only by tests». È lo stato di passaggio previsto: le chiama A5. Gli altri
>   reperti c'erano già.

#### A4.5 — Doc per sviluppatori (`docs-writer`) e devWiki ✅ (2026-10-15)
> **Note implementazione**:
> - `architecture/database/index.md`: la riga della 005 nella tabella della catena delle migrazioni. H, in
>   `dev_release2`, tocca solo la tabella dei file della cartella dati, più in basso.
> - `architecture/database/users_access.md`:
>   - schema ER con `ACCOUNT_TOKEN` e le sue tre relazioni con `USER`;
>   - le tre colonne nuove di `USER`;
>   - sezione nuova `ACCOUNT_TOKEN` (`#account-token`): colonne, CHECK, unicità, azioni delle chiavi esterne e
>     perché, indici, perché niente AUTOINCREMENT, cosa prova `db migration-005`.
> - `architecture/security.md`: sezione nuova «🎟️ Single-use Account Tokens» (`#account-tokens`), fra «Endpoint
>   Protection» e «Output Escaping». In `dev_release2` H ha inserito le sue sezioni prima di «Endpoint Protection»,
>   quindi l'unione resta pulita.
>   - Contenuto: generazione e hash, tabella di scopi, durate e link, stato e consumo atomico, revoca, transazioni e
>     log.
>   - Dice che oggi nessun endpoint usa il servizio e che le pagine `/invite`, `/reset-password`, `/setup` e
>     `/verify-email` non esistono ancora.
> - devWiki `domains/auth.md`: una decisione (token monouso, hash, consumo atomico, niente batch su `users`) e 3
>   righe «Source files». `check_source_paths.py` trova i soliti 5 percorsi generati.
>
> **⚠️ Fuori pista**:
> - La docstring della 005 diceva che gli id dei token non si riusano mai. Non è esatto: la cancellazione di un
>   account toglie i suoi token, e se erano gli ultimi i loro id tornano. Mai per un invito, che non ha account.
>   Corretta. La pagina `users_access.md` lo dice già.
> - `patterns/alembic.md` presenta il batch come la via normale, senza avvertire della cascata con `foreign_keys=ON`.
>   La pagina è di tutti: aggiunta ad A-7 nel backlog e segnalata al coordinatore.

#### A4.6 — Validazione del checkpoint ✅ (2026-10-15)
> **Note implementazione** (`bash /tmp/libreFolio_a4_validate.sh`, corsia 6182, dalle 04:20 alle 04:43):
> - `dev.py mkdocs build`: exit 0. `mkdocs check-links`: 95 link validi.
> - `check-orphans`: 366 unitari, 118 E2E, **267** file backend (265 più i 2 nuovi), tutti registrati e
>   raggiungibili da `all`.
> - **`all-backend`**: uscita 0, **7/7 categorie**, 22 min.
>   - 24 righe di riepilogo pytest: **13 556 passati, 28 saltati, 0 falliti**.
>   - In A3.8, su `35f1e0a16`, erano 13 440. A4 aggiunge 89 test (64 più 25); gli altri vengono da W I1, entrato nel
>     frattempo e non misurato a parte.
> - `git diff --check` pulito, porta 6182 libera.
> - Frontend non toccato: niente `front check`, build o E2E.

### Checkpoint A4 (CP A4, migrazione e token) 🧊 (2026-10-15, notte) — FROZEN, in attesa del commit del coordinatore
> - **Delta** sulla base `0ddd296a0`, non in stage:
>   - 4 file nuovi;
>   - 7 file di codice, test, runner, doc e devWiki modificati;
>   - in più questo piano e la sezione A del backlog.
> - **Conflitti attesi con `dev_release2`** (`0229dbc6a`): nessuno testuale.
>   - `models.py`: lì la riga 700 (`Asset`), qui le righe 353, 391 e 510.
>   - `db_schema_validate.py`: lì la riga 286, qui le 533–560.
>   - `_backend_services.py`: lì le righe 712 e 1173, qui le 445 e 1055.
>   - `security.md` e `database/index.md`: H inserisce in punti lontani dai miei.
> - **Commit proposti**:
>   1. `feat(accounts): migration 005 and account tokens`;
>   2. `docs(journal): A4 progress, A backlog`.
> - **Dopo il commit**: l'aggiornamento di base porta il CP3 di H. Poi viene la parte `sv` di A4, con un suo
>   checkpoint.
>
> **Esito**: il coordinatore ha committato `75a8af5a7` (`feat(accounts): migration 005 and account tokens`, 12 file) e
> `a170c68c0` (journal). Prima del commit ha corretto un'attribuzione nella docstring della 005 e in
> `database/users_access.md`: `email_verified_at` a `NULL` è una «coordinator decision», non del developer, perché
> l'ha decisa lui sulla mia proposta.
>
> Poi ha aggiornato la base con il merge `3ebf4c043` di `dev_release2` a `0902524e5`. Il merge porta H CP3 (segreti da
> `*_FILE`, chiave d'istanza, guardie `config-package` e `config-env-example`), X CP2b, W K1, il lotto
> `web_link_finder` di H, J CP-1 e W4 CP6 (BRIM in `services/brim/`).
> - Unione automatica di 6 file: `models.py`, `db_schema_validate.py`, `_backend_services.py`, `security.md`,
>   `database/index.md` e il backlog.
> - Catena delle migrazioni lineare 004 → 005.
> - Su `patterns/alembic.md` (A-7): la corregge chi tocca per primo una migrazione su una tabella referenziata.

#### A4.7 — Validazione completa della revisione combinata `3ebf4c043` ✅ (2026-10-15)
> **Note implementazione** (`bash /tmp/libreFolio_a4c_validate.sh`, corsia 6182, dalle 04:46 alle 05:14, tutto exit 0):
> - `dev.py front build --debug`: svelte-check 0/0. `dev.py mkdocs build`: exit 0. Entrambi prima di `all-backend`, per
>   l'avvio del server.
> - `services account-tokens`: **64**. `db migration-005`: **25**. `db create`, poi `db validate` **17** e
>   `db post-migration` **37**.
> - `services config-package`: **568** passati; la scansione ora comprende `token_service.py`, che non legge
>   l'ambiente. `services config-env-example`: **36**.
> - `check-orphans`: 367 unitari, 118 E2E e 272 file backend, tutti registrati e raggiungibili.
> - **`all-backend`**: uscita 0, **7/7 categorie**, 24 min. 24 righe di riepilogo pytest: **13 960 passati,
>   28 saltati, 0 falliti**.
> - `git diff --check` pulito, porta 6182 libera, worktree pulito prima di questa nota.
>
> **Esito**: il coordinatore ha integrato A4 in `dev_release2` con un avanzamento veloce a `e476d2ed4`, che contiene il
> journal, più il suo commit di record `be2ad6573`. Il ramo è avanzato lì. Nessuna riga nel CHANGELOG: A4 non ha ancora
> niente di visibile.

### A4b — versione della sessione (`sv`) (CP A4b) — in corso

#### A4b.0 — Via e base ✅ (2026-10-15)
> Via del coordinatore (15/10, ~05:17), alla lettera: «Il disegno di A4b va bene così: è la decisione D-A17 del
> developer. **Via per A4b**, con un suo checkpoint FROZEN. Nell'handoff elenca le pagine in 4 lingue che correggi
> (`admin/cli_tools`), e se le timbri; la riga di `TODO_FUTURI.md` che chiudi. Le run pesanti vanno chiuse entro le
> 08:45, oppure dopo l'avviso di fine della finestra della galleria.»
>
> **Note implementazione**:
> - Base `be2ad6573`, worktree pulito, porta libera. Il CP3 di H è nella base: `configured_jwt_secret()` legge anche
>   `JWT_SECRET_FILE`.
> - **Disegno** (§4.5 e D-A17):
>   - il JWT porta il claim `sv`; `decode_jwt_token` restituisce `SessionClaims(user_id, session_version)`, e un cookie
>     senza `sv` vale 0;
>   - `get_current_user` dà 401 «Session expired or invalid» quando la versione non coincide;
>   - la versione sale di 1 con il cambio della password (con il cookie del dispositivo corrente riemesso nella stessa
>     risposta), con `reset_password` (CLI `user reset`, poi il link di A5), con la disattivazione e con il
>     declassamento; mai con un'operazione rifiutata;
>   - A-3: `reset_password` passa bcrypt in `asyncio.to_thread`.
> - **Rischio noto**: una richiesta già in volo dallo stesso dispositivo, col cookie vecchio, può arrivare dopo il
>   commit e prendere 401. L'intercettore (`zodios-client.ts:130`) porta al login, e la radice rientra col cookie nuovo.
> - Il server di test genera il suo segreto JWT all'avvio, quindi un test API non può fabbricare un cookie senza `sv`:
>   quel caso si prova nel processo del test, a livello di servizio e chiamando `get_current_user` direttamente.

#### A4b.1 — Test rossi (`test-author`) ✅ (2026-10-15)
> **Note implementazione**:
>
> | File | Voce del runner | Test | Rossi prima |
> |---|---|---|---|
> | nuovo `test_services/test_session_version.py` | `services session-version` (`pure`) | 47 | 25 |
> | nuovo `test_api/test_session_revocation_api.py` | `api session-revocation` (`write-scoped`, default della categoria) | 3 | 1 |
>
> - **Motivi dei rossi**:
>   - `SessionClaims` e `end_sessions` mancano;
>   - `create_jwt_token` non accetta `session_version`;
>   - un `sv` malformato viene accettato;
>   - un `sub` non numerico fa uscire `ValueError`;
>   - un cookie di un'altra versione viene accettato;
>   - la versione non sale con reset, disattivazione e declassamento;
>   - bcrypt gira sul thread del loop (A-3);
>   - nel test API il cambio della password non emette `Set-Cookie`, e il vecchio cookie e il secondo dispositivo
>     restano a 200.
> - **Verdi già prima** (22 di servizio e 2 API):
>   - token non fidati, cookie alla versione giusta, account disattivato;
>   - attivazione e promozione che non toccano la versione;
>   - i rifiuti;
>   - password sbagliata o uguale: 400 e nessun cookie nuovo.
> - **Fissati oltre la lista**:
>   - il payload esatto `{sub, iat, exp, sv}`;
>   - il controllo di `is_active` prima di quello della versione;
>   - il login successivo emette la versione corrente;
>   - il cookie riemesso ha gli attributi di quello del login.
> - Il test API legge `users.session_version` dei suoi due utenti dal DB della corsia.
> - **⚠️ Fuori pista**: la voce `services` della corsia ha svuotato il DB; `test-author` l'ha ripopolato con
>   `db populate --force`, la stessa chiamata del setup `api`. Ha segnalato anche `LOOP-003` di `test_auth_api.py:1848`,
>   che chiama `change_password` per nome e si rompe con i parametri nuovi.

#### A4b.2 — Implementazione ✅ (2026-10-15)
> **Note implementazione** (script `/tmp/libreFolio_a4b/patch_a4b.py`, provato prima su una copia dei file):
> - `auth_service.py`:
>   - `SessionClaims`;
>   - `create_jwt_token(user_id, ttl_hours, session_version)`, con `sv` nel payload;
>   - `decode_jwt_token` restituisce `SessionClaims`, e un token senza `sv` vale 0;
>   - un `sv` non intero, booleani compresi, dà `None`; un `sub` mancante o non numerico dà `None` invece di
>     un'eccezione;
>   - `_JWT_SECRET` resta del modulo e si legge a ogni chiamata.
> - `api/v1/auth.py`:
>   - `get_current_user` controlla la versione dopo esistenza e attività;
>   - due aiuti, `_session_ttl_hours` e `_issue_session_cookie`, usati da login e cambio password;
>   - `change_password` riceve `response` e `http_request`, alza la versione e riemette il cookie nella stessa
>     risposta.
> - `user_service.py`:
>   - `end_sessions(user)`, senza commit;
>   - chiamata da `reset_password` (che passa bcrypt in `asyncio.to_thread`, chiudendo A-3), da
>     `set_user_active(False)` e da `set_user_admin(False)`;
>   - via il commento «JWT tokens cannot be revoked».
> - ruff e black puliti. `LOOP-003` lo adatta `test-author`.

#### A4b.3 — Doc in 4 lingue, timbri, devWiki ✅ (2026-10-15)
> **Note implementazione**:
> - **Pagine corrette in en, it, fr ed es**, piccole modifiche dello stesso senso:
>   - `admin/cli_tools`: il reset chiude le sessioni aperte e la disattivazione non le fa tornare; anche il
>     declassamento disconnette l'account;
>   - `user/settings/profile`: dopo il cambio della password gli altri dispositivi vengono disconnessi;
>   - `user/connection-security`: cambiare la password disconnette anche gli altri dispositivi.
> - **Timbri** con `dev.py mkdocs translate-stamp --file …` (prova a vuoto prima). Legittimi: prima della modifica la
>   cache delle tre pagine aveva l'MD5 della versione inglese corrente, con es/fr/it fatti.
>   - `cli_tools`: `df53c747 → 36e0f264`;
>   - `profile`: `ee81e8e4 → b0cde443`;
>   - `connection-security`: `95e2f750 → ed3e331c`.
> - devWiki `domains/auth.md`: una decisione sulla revoca per versione.

#### A4b.4 — Doc per sviluppatori (`docs-writer`) ✅ (2026-10-15)
> **Note implementazione**:
> - `architecture/security.md`:
>   - payload `{sub, sv, iat, exp}`;
>   - «Token Expiration» e «Logout» aggiornati;
>   - sezione nuova «🔁 Session Revocation» (`#session-revocation`): cosa alza la versione, cosa la lascia stare, come
>     si decodifica un token, ordine dei controlli in `get_current_user`, il cookie riemesso, la corsa innocua, i test.
>   - Ho cambiato l'emoji della sottosezione «Transactions and Logs» dei token di A4 da 🔁 a 🧾, perché l'emoji era
>     doppia; l'ancora non cambia.
> - `architecture/users_and_brokers.md`: introduzione, passi del login e punti «Stateless», «TTL» e «Revocation».
> - `architecture/access_control.md`: reset, disattivazione e declassamento chiudono le sessioni.
>   - `docs-writer` ha corretto anche due derive di A-7, fuori da A4b ma nelle stesse righe: la regola dell'ultimo
>     admin e il 403 `ACCOUNT_DISABLED`.
> - `database/users_access.md`: `session_version` ora è descritta come in uso.
> - `frontend/state/app-state.md:11`: lo store tiene lo stato della sessione, mentre la sessione è il cookie HttpOnly
>   (A-7).
> - `backend/app/db/models.py`: il commento su `session_version` diceva «il codice arriva dopo». Corretto.
> - Backlog A-7: chiuse tre righe, più una riga nuova (`users_and_brokers.md` dice «via CLI or API»; l'API arriva con
>   A5).

#### A4b.5 — Test verdi e controlli ✅ (2026-10-15)
> **Note implementazione**:
> - `test-author` ha adattato `LOOP-003` in `test_auth_api.py:1848`: alla chiamata di `change_password` passa
>   `response=Response(), http_request=_request("http")`. Nient'altro: il TTL viene dal DB privato (24 h di riserva) e
>   il cookie è firmato col segreto del processo di test.
> - Verdi:
>   - `services session-version`: **47**;
>   - `api session-revocation`: **3**;
>   - `api auth`: **60**, compreso `LOOP-003`.
> - La voce `services` della corsia svuota il DB, e `test-author` l'ha ripopolato con `db populate --force` prima delle
>   voci `api`.
> - **API**: confronto con lo schema esportato in A4. Le 7 rotte `auth` cambiano solo nella `description` di
>   `change-password`, che ora dice che le altre sessioni finiscono. Gli schemi `ChangePassword*`, `AuthUserResponse` e
>   `AuthLoginResponse` sono identici, e nello schema non ci sono `session_version` né `sv`. Il client generato è
>   ignorato da git: niente `api sync` da committare.
> - **vulture**: nessun reperto nuovo; restano le 5 funzioni di `token_service` di A4.
> - **`TODO_FUTURI.md`**: la voce «🔑 Sessioni — il cambio della password non chiude le sessioni già aperte» passa in
>   cima a `TODO_Completati.md`, come «🔑 Il cambio della password chiude le altre sessioni ✅», con data, risultato e
>   origine (la decisione del 09/10 e la D-A17).

#### A4b.6 — Validazione del checkpoint ✅ (2026-10-15)
> **Note implementazione** (`bash /tmp/libreFolio_a4b_validate.sh`, corsia 6182, dalle 05:52 alle 06:13):
> - `dev.py mkdocs build`: exit 0. `mkdocs check-links`: 95 link validi.
> - `check-orphans`: 367 unitari, 118 E2E, **274** file backend (272 più i 2 nuovi), tutti raggiungibili.
> - **`all-backend`**: uscita 0, **7/7 categorie**, 20 min.
>   - 24 riepiloghi pytest: **14 010 passati, 28 saltati, 0 falliti**.
>   - Rispetto ai 13 960 di A4.7 la differenza è di 50, cioè i test nuovi (47 più 3).
> - `git diff --check` pulito, porta 6182 libera. Frontend non toccato.
>
> **⚠️ Fuori pista**: ho lanciato lo script con `&` dentro una chiamata sincrona invece che in modalità asincrona.
> Ho controllato che il processo fosse vivo e unico nella corsia, e l'ho seguito dal suo log. Nessun effetto sulla run.

### Checkpoint A4b (versione della sessione) 🧊 (2026-10-15, mattina) — FROZEN, in attesa del commit del coordinatore
> - **Delta** sulla base `be2ad6573`, non in stage: 2 file nuovi e 30 modificati, fra codice, test, runner, doc, traduzioni, cache
>   di traduzione, devWiki, `TODO_FUTURI.md`, `TODO_Completati.md`, il piano e la sezione A del backlog.
> - **Conflitti attesi con `dev_release2`** (`6d67fdaac`): nessuno testuale.
>   - `TODO_FUTURI.md`: lì le righe 1121 e 2067, qui il blocco 2176–2199.
>   - `security.md`: lì le righe 221 e 266, qui le 11, 30, 78–89 e 347.
>   - `app-state.md`: lì le righe 5, 19 e 75, qui la 11.
>   - `_backend_api.py`: lì la riga 50, qui le 578 e 783.
>   - `_backend_services.py`: lì le righe 173–782, qui l'inserimento dopo la 455 e la 1108.
>   - Backlog: sezioni diverse.
> - **Commit proposti**:
>   1. `feat(accounts): end sessions on password change`;
>   2. `docs(journal): A4b progress, A backlog, TODO`.
>
> **Esito**: il coordinatore ha committato `3ac4114d5` (`feat(accounts): end sessions on password change`, 28 file) e
> `6160a71ce` (journal, backlog, `TODO_FUTURI.md`, `TODO_Completati.md`), dopo aver riletto la logica di
> `get_current_user`, `decode_jwt_token` e `change-password`. Le due righe del CHANGELOG vanno sotto «🔄 Changed».
>
> Poi ha aggiornato la base con il merge `9c3047ce9` di `dev_release2` a `6d67fdaac`. Porta X CP3, W7, X CP3b, J C-93 e
> H CP4: router di sistema per risorsa, `/system/instance` pubblico, area degli avvisi nel layout.
> - Unione automatica di `security.md`, `app-state.md`, `_backend_api.py`, `_backend_services.py`, `TODO_FUTURI.md` e
>   del backlog.
> - `decode_jwt_token` ha un solo chiamante, `auth.py`.
>
> **Nota per A5 e i lotti dopo**, alla lettera: «`GET /api/v1/system/instance` è **pubblico**. Ogni campo che aggiungi in
> `InstanceConfigResponse` deve essere innocuo per un anonimo. `registration_mode` va bene; dati di utenti, email o
> versioni no (decisione 15).»

#### A4b.7 — Validazione completa della revisione combinata `9c3047ce9` ✅ (2026-10-15)
> Richiesta del coordinatore:
> - `services session-version`, `api session-revocation`, `api auth`, `api system`;
> - `all-backend`, con `front build --debug` e `mkdocs build` prima;
> - E2E `front-utility auth` e `front-utility settings`;
> - `api schema` contro `6d67fdaac`;
> - handoff entro le 08:20.
>
> **Note implementazione**:
> - **`api schema`**: l'ho esportato da HEAD e dalla base `6d67fdaac`. La base l'ho estratta con `git archive` in
>   `/tmp` ed esportata con il Python del venv condiviso, senza un altro checkout. Risultato: 114 percorsi e 587 schemi
>   da tutte e due le parti. Cambia solo la `description` di `POST /api/v1/auth/change-password`, e il resto è uguale.
> - **⚠️ Fuori pista**: nessuna E2E invia la modale del cambio password. `settings.spec.ts` la apre, ne controlla i
>   campi e la annulla, quindi le E2E `auth` e `settings` non provano il cookie riemesso nel browser. Ho chiesto a
>   `test-author` un test in `settings.spec.ts`: un utente suo cambia la password dalla modale, il dispositivo resta
>   collegato, un secondo contesto del browser riceve 401. Non è un rosso visto prima: è la prova nel browser,
>   scritta dopo il codice.
> - **Prima parte** (`bash /tmp/libreFolio_a4bc_validate.sh`, corsia 6182, dalle 06:18 alle 06:42, tutto exit 0):
>   - `dev.py front build --debug`: svelte-check 0/0. `dev.py mkdocs build`: exit 0.
>   - Le voci `api` girano prima, sul DB popolato della corsia, perché la voce `services` lo svuota:
>     - `api session-revocation`: **3**;
>     - `api auth`: **60**;
>     - `api system`: **94**;
>     - `services session-version`: **47**.
>   - **`all-backend`**: uscita 0, **7/7 categorie**, 20 min. 24 riepiloghi: **14 046 passati, 28 saltati, 0 falliti**.
>     Rispetto ai 14 010 di A4b.6, i 36 in più vengono dai lotti entrati col merge.
>   - `git diff --check` pulito, porta libera.
> - **E2E del cambio password**: scritta da `test-author` in `frontend/e2e/settings.spec.ts`, nella describe
>   «Password change and sessions».
>   - Usa un utente usa e getta, `registerDisposableUser`, e lo cancella alla fine.
>   - Il dispositivo A cambia la password dalla modale. Il test controlla che il barattolo dei cookie abbia un solo
>     `session`, con un valore nuovo, e che `/dashboard` e `/auth/me` funzionino ancora.
>   - Il dispositivo B riceve 401 e torna al login. La password vecchia viene rifiutata, la nuova entra.
> - **E2E**, lanciate da `test-author` nella corsia dopo `all-backend`, una alla volta:
>
>   | Run | Esito |
>   |---|---|
>   | `front-utility settings "Password change and sessions"` | **1/1**, 6,6 s |
>   | `front-utility settings` | **46/46** (43 più i 3 di `fx/fx-chart-settings.spec.ts`, che il runner prende per sottostringa) |
>   | `front-utility settings` con `--workers 4` | **46/46**; il test nuovo in 14,2 s, su un budget di 90 s |
>   | `front-utility auth` | **29/29** (26 più i 3 di `layout/app-start-auth.spec.ts`) |
>   | `check-orphans` | pulito: 118 spec E2E, 370 file di test unitari |
>   | `dev.py front check` | 0 errori, 0 avvisi |
>
>   - `front check` esclude `e2e/`, quindi `test-author` ha controllato i tipi della spec con il `tsc` del
>     repository, `--noEmit` in modalità strict: 0 errori.
>   - Il log del backend mostra, per ognuno dei tre utenti `guides_pwchange_*`: registrazione, due accessi, «Password
>     changed, other sessions ended», password vecchia rifiutata, cancellazione.
> - Porta 6182 libera. Delta: `frontend/e2e/settings.spec.ts` (il test nuovo, più `type BrowserContext`
>   nell'import) e questo piano.
>
> **Esito**: il coordinatore ha integrato A4b in `dev_release2` come `dbf89cdd5` (merge di `3d6ecb2fe` su
> `e7cf1ae80`, dove erano già entrati J G-8, X CP4 e W K2a), più il suo commit di record `2ee39823b`, con le due righe
> nel CHANGELOG sotto «🔄 Changed». Nessun altro giro di validazione: i test nuovi dei Tool sostituiscono
> `get_current_user`, e `models.py`, `TODO_FUTURI.md` e il backlog si sono fusi da soli.

### A5 — inviti, `registration_mode`, limite, API admin, link di reset — in corso

#### A5.0 — Via e base ✅ (2026-10-15)
> Via del coordinatore (15/10, ~06:55), alla lettera: «**Via per A5**: inviti, `registration_mode` con la migrazione
> **006**, limite, API admin, link di reset. Punti da ricordare: le regole della password uniche aspettano la decisione
> 37 del developer; ogni campo in `/system/instance` deve essere innocuo per un anonimo; A5 tocca il frontend e
> `e2e/layout/theme-roles.spec.ts` del programma colori: entra dopo la chiusura della finestra della galleria. Dalle
> ~08:45 niente run pesanti fino all'avviso di fine.»
>
> **Note implementazione**: base `2ee39823b`, worktree pulito, porta libera.

#### A5.1 — Taglio e contratto di A5a (backend e CLI) ✅ (2026-10-15)
> **Taglio**: A5 è il lotto più grande, quindi lo divido in due, ciascuno col suo checkpoint FROZEN.
> - **A5a**: backend e CLI, descritto qui sotto.
> - **A5b**: frontend.
>   - Lo store `globalSettings` e il selettore a 3 voci in `GlobalSettingsTab`, bloccato quando c'è la variabile;
>   - «Registrati qui» del `LoginCard` solo con `open`;
>   - le pagine `/invite` e `/reset-password`;
>   - i18n, doc utente e galleria;
>   - E2E, compreso `e2e/layout/theme-roles.spec.ts` del programma colori.
> - A5a da solo lascerebbe la UI di `dev_release2` sulla chiave vecchia: conviene integrare A5a e A5b insieme, dopo la
>   finestra della galleria. Lo decide il coordinatore.
>
> **Contratto di A5a**:
> 1. **Migrazione `006_registration_mode`** (21 caratteri), `down_revision = 005_accounts_invites`, solo dati.
>    - Se c'è la riga `enable_registration`, scrive `registration_mode` (se non c'è già) e cancella la vecchia:
>      - valore `open` se il valore vecchio, in minuscolo, è `true`, `1`, `yes` o `on`; ogni altro valore → `disabled`.
>        È come lo leggeva il servizio (`get_setting_value`: `value.lower() in ("true", "1", "yes", "on")`, senza
>        ripulire gli spazi), e quindi chiude nei casi strani. *Correzione delle 07:15: la prima versione diceva il
>        contrario, ed era sbagliata;*
>      - `value_type = string`, descrizione «Who may create an account: open, invite or disabled»;
>      - `updated_at` e `updated_by_user_id` copiati.
>    - Il downgrade fa il contrario: `open` → `"true"`, `invite` e `disabled` → `"false"`, `value_type = bool`,
>      descrizione «Allow new user registration».
>    - Idempotente nei due sensi; nessun'altra riga toccata.
> 2. **Registro delle impostazioni**:
>    - `registration_mode` (default `open`, tipo `string`, `SettingConstraint(choices=("open", "invite",
>      "disabled"))`) prende il posto di `enable_registration`;
>    - `SETTINGS_REGISTRY.global_.REGISTRATION_MODE`; `ENABLE_REGISTRATION` sparisce;
>    - scrivere `registration_mode` quando la variabile la blocca dà 409 `SETTING_LOCKED_BY_ENV`, e non salva niente.
> 3. **Variabili** (`backend/app/config/accounts.py`, un accessore ciascuna, tutte in `.env.example` alla sezione
>    Accounts come righe commentate col default):
>    - `registration_mode_override()`: `LIBREFOLIO_REGISTRATION`, ripulita e minuscola. Non impostata o vuota →
>      `None`. Uno fra `open`, `invite` e `disabled` → quello. Altro → `ValueError` con il nome e i valori ammessi;
>    - `max_users()`: `LIBREFOLIO_MAX_USERS`. Non impostata o vuota → `None`, nessun limite. Un intero ≥ 1 → quello.
>      Altro → `ValueError`;
>    - `public_url()`: `LIBREFOLIO_PUBLIC_URL`, ripulita e senza `/` finale. Non impostata o vuota → `None`. Deve
>      cominciare con `http://` o `https://`, altrimenti `ValueError`;
>    - `billing_url()`: `LIBREFOLIO_BILLING_URL`, stesse regole.
> 4. **`services/accounts/registration_service.py`**:
>    - `effective_registration_mode(session) → RegistrationModeState(mode, locked)`:
>      - con la variabile vale lei, e `locked=True`;
>      - una variabile non valida chiude: `disabled`, `locked=True`, e un errore nel log una volta per processo;
>      - altrimenti vale la riga, `open` di default.
>    - `user_usage(session) → UserUsage(used, max_users)`:
>      - `used` = utenti attivi più inviti vivi (né consumati, né revocati, né scaduti);
>      - un `LIBREFOLIO_MAX_USERS` non valido chiude: `max_users = 0` ed errore nel log.
>    - `create_invite(session, *, created_by_user_id, grants_admin=False, email=None, now=None) → IssuedToken`:
>      rifiuta con `RegistrationError(code)` in modalità `disabled` (`REGISTRATION_DISABLED`) e a limite raggiunto
>      (`USER_LIMIT_REACHED`, quando `used >= max_users`).
>    - `list_pending_invites(session, now=None)` e `revoke_invite(session, invite_id) → bool`.
>    - `register_user(session, *, username, email, password, invite_token=None, now=None) → User` racchiude tutta la
>      regola:
>      - **nessun utente**: il primo diventa admin, in ogni modalità (come oggi);
>      - **`disabled`**: `REGISTRATION_DISABLED`, anche con un invito (D-A3);
>      - **`invite`**: serve un invito valido; senza → `INVITE_REQUIRED`, non valido → `INVITE_INVALID`;
>      - **`open`**: l'invito è facoltativo, ma se c'è dev'essere valido (`INVITE_INVALID`);
>      - **con un invito valido**: il ruolo viene dall'invito (`grants_admin`); il consumo (con
>        `consumed_by_user_id`) e la creazione stanno nella stessa transazione; il posto era già contato, quindi il
>        limite non lo blocca;
>      - **senza invito** (`open`): il limite si controlla dopo aver inserito l'utente, nella stessa transazione. Così
>        due registrazioni in corsa non lo superano: chi ha scritto per primo tiene il blocco. Se superato: rollback e
>        `USER_LIMIT_REACHED`;
>      - bcrypt fuori dal loop degli eventi; nome o email già presi → gli errori di oggi.
> 5. **API**:
>    - `POST /auth/register`: il corpo ha in più `invite_token`. Errori:
>      - 403 `REGISTRATION_DISABLED`; 403 `INVITE_REQUIRED`; 400 `INVITE_INVALID`;
>      - 409 `USER_LIMIT_REACHED`, **senza conteggi né link di fatturazione**: chi chiede è anonimo (decisione 15). È
>        una correzione del §4.6, che metteva `{limit, used}` anche qui.
>    - `POST /auth/tokens/inspect` `{token, purpose: invite|password_reset}` → `{status, purpose}`. Solo se `valid`,
>      anche `expires_at` più `grants_admin` ed `email` (invito) o `username` (reset). Pubblico: risponde solo a chi ha
>      il token.
>    - `POST /auth/password-reset` `{token, new_password}`:
>      - consuma il token di reset e imposta la password (bcrypt fuori dal loop);
>      - `end_sessions(user)` e revoca degli altri link di reset vivi dell'utente;
>      - 200; token non valido → 400 `TOKEN_INVALID`.
>    - `GET /system/instance`: campo `accounts: {registration_mode, registration_locked}`, innocuo per un anonimo.
>      L'endpoint diventa `async` con la sessione del DB.
>    - **Admin** (`require_admin`, `api/v1/users.py`, le rotte statiche prima di `{user_id}`):
>      - `GET /users/invites` → `{items: [{id, grants_admin, email, created_at, expires_at, created_by_user_id}],
>        usage: {used, max_users, billing_url}}`;
>      - `POST /users/invites` `{grants_admin=false, email?}` → 201 `{invite, token, path, url}`, dove `url` è `null`
>        senza `LIBREFOLIO_PUBLIC_URL`. 409 `USER_LIMIT_REACHED` `{limit, used, billing_url}`; 409
>        `REGISTRATION_DISABLED`;
>      - `DELETE /users/invites/{invite_id}` → 204; 404 se l'invito non è vivo;
>      - `GET /users` → `{items: [{id, username, email, is_active, is_superuser, created_at}], usage}`;
>      - `PATCH /users/{user_id}` `{is_active?, is_superuser?}` → 200 con l'utente; 404; 409 `LAST_ADMIN` se si
>        disattiva o declassa l'ultimo admin attivo; 409 `USER_LIMIT_REACHED` se una riattivazione supera il limite. Le
>        sessioni si chiudono come in A4b;
>      - `POST /users/{user_id}/password-reset-link` → 201 `{token, path, url, expires_at}`, revocando prima gli altri
>        link vivi dell'utente; 404;
>      - `POST /users/{user_id}/sessions/revoke` → 204;
>      - `POST /users/{user_id}/onboarding/reset` `{flow?}` → 204: tutti i flussi, passi compresi, o uno solo, tornano
>        `pending` (21-5);
>      - ogni azione scrive un log strutturato, senza token.
> 6. **CLI**:
>    - `dev.py user invite [--admin] [--email E]`, `dev.py user reset-link <username>` e
>      `dev.py user reset-onboarding <username> [--flow F]`;
>    - il link stampato è `LIBREFOLIO_PUBLIC_URL` più il percorso, oppure il solo percorso con una nota;
>    - `invite` rifiuta in `disabled` (❌, exit 1);
>    - al limite la CLI avvisa e prosegue (§4.6), e lo stesso fanno `user create` e `create-user`.
>
> **Rimandato**:
> - Le regole uniche della password aspettano la decisione 37: le pagine e gli endpoint nuovi usano per ora la regola
>   dell'API (almeno 8 caratteri).
> - I controlli di configurazione di A (variabile non valida, registrazione aperta su un indirizzo pubblico, limite
>   dei tentativi spento) entrano in `CONFIG_CHECKS` di H (`services/platform/config_audit.py`), con le loro chiavi
>   i18n, in A8 con la scheda «Sicurezza».
> - `LIBREFOLIO_BILLING_URL` esce da `GET /users` e `GET /users/invites`, solo per l'admin; la UI arriva in A6.
>
> **Decisione del coordinatore** (15/10, ~07:10), alla lettera: «**Insieme**, dopo la chiusura della finestra della
> galleria: A5a e A5b in due commit, un solo ingresso. Una UI incoerente su `dev_release2` non va bene, tanto più
> vicino alla galleria che misura proprio login e impostazioni. E per ora non parte: se parte, lavora sui suoi servizi e
> si aggancia ad A5 dopo.»
> - L'aggancio in `schemas/system.py` e `api/v1/system/instance.py` è quello previsto da H, che il coordinatore
>   avvisa.
> - Il 409 anonimo senza conteggi né link di fatturazione è giusto (decisioni 7 e 15).
> - Una variabile non valida chiude, con l'errore nel log; le voci in `CONFIG_CHECKS` vanno in A8.
> - Un handoff FROZEN per A5a, che il coordinatore committa sul mio ramo, poi uno per A5b, con la validazione sulla
>   combinazione.
>
> **Avviso del coordinatore** (15/10, ~07:19): H CP5a è in `dev_release2` (`9deb0ea08`) e tocca due miei punti
> d'aggancio. Arriva nella mia base al checkpoint di A5a; i conflitti eventuali li risolvo lì.
> - `schemas/system.py`: H aggiunge `SystemInfoPublicResponse`, `ReadinessChecks` e `ReadinessResponse` dopo
>   `SystemInfoResponse` e `HealthCheckResponse`. Il mio campo `accounts` le affianca.
> - `api/v1/system/__init__.py`: si aggiunge `ready.ready_router`. `instance.py` non cambia.
> - `api/v1/system/info.py`: `signed_in_user` chiama `get_current_user(request, session)` direttamente. Un cambio di
>   firma o di comportamento di `get_current_user` vale anche lì, e un override in `dependency_overrides` non ci
>   arriva.
>
> **Dal coordinatore colori, via il coordinatore** (15/10, ~07:51), per A5:
> - A5 non aspetta T: T-2 (le card d'accesso) è in `dev_release2`, e T-3 e T-5 non toccano `LoginCard`, `RegisterCard`
>   né `routes/+page.svelte`.
> - **Condizione**: restano i `data-testid` che usa la E2E `theme-roles`: `login-modal`, `login-username`,
>   `login-submit`, `goto-register`, `register-modal`, `register-password`, `password-requirements`.
> - Nella validazione di A5b va anche `front-utility theme-roles`.
> - Ordine dopo la finestra: entrano prima R e L dei colori, poi i lotti della 1.3, A5 compreso.

#### A5.2 — Test rossi (due `test-author` in parallelo, R1 e R2) ✅ (2026-10-15)
> **Note implementazione**: R1 e R2 hanno scritto in parallelo su file distinti. Hanno girato nella corsia uno dopo
> l'altro: prima R1, poi R2 al mio via.
>
> | File | Voce del runner | Test | Prima dell'implementazione |
> |---|---|---|---|
> | nuovo `test_db/test_migration_006_registration.py` (R1) | `db migration-006` (anche in `db all`, `pure`) | 36 | 36 rossi: la revisione non esiste |
> | nuovo `test_services/test_registration_service.py` (R1) | `services registration` (`pure`) | 122 | errore di raccolta: `billing_url` non esiste |
> | nuovo `test_api/test_registration_api.py` (R1) | `api registration` (`write-scoped`) | 61 | 54 rossi e 3 errori; 4 verdi, il comportamento che c'è già |
> | nuovo `test_api/test_users_admin_api.py` (R2) | `api users-admin` (`write-scoped`) | 53 | 53 rossi: rotte assenti (405, 404) |
> | `test_utilities/test_dev_cli_image.py` (R2: IMG-013…016b) | `utils dev-cli-image` | 22 nuovi | 21 rossi (comandi sconosciuti, avviso assente); IMG-016b verde come guardia |
>
> - **Test esistenti adattati da R1**:
>   - `conftest.py`, `test_global_settings_service.py`, `test_auth_api.py` (helper `set_registration_mode`; REG-006 →
>     403 `REGISTRATION_DISABLED`), `test_settings_api.py`;
>   - `test_system_api.py` di H: cambiano solo le due asserzioni sulla forma esatta di `/system/instance`, ora
>     `{profile, accounts}`;
>   - `test_migration_005_accounts.py`: confronta le righe subito dopo la 005, così regge la 006;
>   - `LOOP-002`: blocca `bcrypt.hashpw`, il punto da cui passa ogni hash;
>   - `test_post_migration.py`: solo un commento.
> - **Isolamento**: ogni caso che cambia modalità, variabili o limite gira nel processo del test, coi router veri su un
>   SQLite privato e le variabili impostate con `monkeypatch`. Sul server della corsia restano solo casi che non
>   cambiano la modalità e toccano solo account e token propri. Per questo le voci `api` restano `write-scoped`.
> - **Prova dei test**: R1 ha verificato i suoi su un'implementazione di riferimento fuori dal repo, con 25 varianti
>   difettose tutte prese.
> - **⚠️ Fuori pista**:
>   - R2 ha chiuso il primo turno senza file; al secondo li ha scritti.
>   - La prima run di R2 era rossa per il motivo sbagliato: il validatore delle email rifiuta il dominio riservato
>     `.test`. Ora i suoi test usano `@example.com`; nei file di R1 non ci sono domini riservati.
> - **Da segnalare**: il runner non toglie `LIBREFOLIO_REGISTRATION` e `LIBREFOLIO_MAX_USERS` dall'ambiente della
>   corsia. Una shell con una delle due impostata cambierebbe la registrazione di tutta la corsia. È infrastruttura dei
>   test (`configure_test_runtime`), da decidere al coordinatore.

#### A5.3 — Implementazione di A5a ✅ (2026-10-15)
> **Note implementazione**: bozze in `/tmp/libreFolio_a5a/`, scritte mentre i test-author lavoravano. Le ho provate
> prima su una copia di HEAD (`git archive`): ancore, ruff, black, import dell'app ed export OpenAPI. Poi le ho applicate
> con `apply_a5a.sh`, che finisce con `ruff --fix` e black.
> - `backend/alembic/versions/006_registration_mode.py`: solo dati. `open` se `lower(value)` è `true`, `1`, `yes` o
>   `on`, altrimenti `disabled`; metadati copiati; idempotente; il downgrade va al contrario.
> - `backend/app/config/accounts.py`:
>   - `registration_mode_override()`, `registration_mode_pinned()`, `max_users()`, `public_url()` e `billing_url()`;
>   - un valore vuoto vale come assente; un valore non valido dà `ValueError`; dagli URL si toglie una sola barra
>     finale.
> - `.env.example`, sezione Accounts: le 4 variabili, commentate, con il loro senso.
> - **Nuovo `services/accounts/registration_service.py`**:
>   - `effective_registration_mode`, `user_usage`, `create_invite` (con `enforce_limit` per la CLI),
>     `list_pending_invites`, `revoke_invite`, `register_user`, più `public_link` e `billing_link`;
>   - un valore non valido chiude, con un errore nel log una volta per processo (`functools.cache`);
>   - `register_user` sta sotto il limite di complessità grazie all'aiuto `_admission`.
> - `user_service.py`:
>   - `create_user(..., commit=True)`, che con `False` fa solo il flush;
>   - `create_password_reset`, che revoca i link vivi e ne emette uno nuovo;
>   - `complete_password_reset`, che consuma il token, imposta la password con bcrypt in un thread, chiama
>     `end_sessions` e revoca gli altri link;
>   - `update_user_status`, tutto o niente, che rifiuta `LAST_ADMIN` e chiude le sessioni.
> - `onboarding_service.py`: `reset_onboarding_progress(session, user_id, flow=None)`.
> - **Impostazioni**:
>   - il registro ha `registration_mode` con le 3 scelte, e `ENABLE_REGISTRATION` sparisce;
>   - `GlobalSettingLockedError` dà 409 `SETTING_LOCKED_BY_ENV`;
>   - via `is_registration_enabled`.
> - **Schemi**:
>   - `auth.py`: `invite_token`, `TokenInspectRequest`/`Response`, `PasswordResetRequest`/`Response`,
>     `AccountsInstanceConfig`;
>   - `users.py`: gli schemi admin. Il 201 dell'invito ha esattamente `{invite, token, path, url}`;
>   - `system.py`: il campo `accounts`.
> - **API**:
>   - `auth.py`: `register` passa per `registration_service`; nuovi `tokens/inspect` e `password-reset`;
>   - `users.py`: le 8 rotte admin, quelle statiche prima di `{user_id}`;
>   - `system/instance.py`: `async`, con la sessione del DB.
> - `scripts/user_cli.py`: `invite`, `reset-link` e `reset-onboarding`, interni e di `dev.py`; avviso del limite su
>   `create` e `create-user`.

#### A5.4 — Test verdi ✅ (2026-10-15)
> **Note implementazione**: corsia 6182, una invocazione alla volta. Script `/tmp/libreFolio_a5a_green.sh` e
> `/tmp/libreFolio_a5a_extra.sh`; log `/tmp/libreFolio_a5ag_*` e `/tmp/libreFolio_a5ax_*`. Ogni voce `services`
> svuota il DB della corsia: prima delle voci `api` c'è sempre `db populate --force`.
>
> | Voce | Esito |
> |---|---|
> | `db migration-006` | 36 ✅ |
> | `db migration-005` | 25 ✅ |
> | `db create`, `db validate` | ✅, 17 ✅ |
> | `db post-migration` | 37 ✅ |
> | `db referential-integrity` | 17 ✅ |
> | `services registration` | 122 ✅ |
> | `services global-settings` | 19 ✅ |
> | `services config-package` | 587 ✅ |
> | `services config-env-example` | 36 ✅ |
> | `services user-profile`, `settings`, `donation-popup` | 36, 23, 19 ✅ |
> | `services account-tokens`, `session-version` | 64, 47 ✅ |
> | `api registration` | 61 ✅ |
> | `api users-admin` | 53 ✅, senza avvisi (dopo la riparazione di UADM-030 e UADM-027) |
> | `api auth` | 60 ✅ |
> | `api settings` | 95 ✅ |
> | `api system` | 94 ✅ |
> | `api account-deletion`, `users-search`, `session-revocation` | 6, 16, 3 ✅ |
> | `utils dev-cli-image` | 66 ✅ (dopo la correzione della CLI) |
>
> Porta 6182 libera alla fine di ogni script.
>
> - **⚠️ Fuori pista**:
>   - **UADM-030 rosso al primo giro.**
>     - I record DEBUG di `aiosqlite` stampano i parametri dell'INSERT in `account_tokens`, cioè l'hash del token.
>     - Il server non li emette: `logging_config.py:138-143` porta `aiosqlite`, `sqlalchemy.engine` e
>       `sqlalchemy.pool` a WARNING. Li vede solo `caplog`, che abbassa il livello.
>     - Il token in chiaro non arriva mai al SQL.
>     - R2 ha ristretto il test a ciò che il prodotto promette. Il token in chiaro non deve stare in nessun record né
>       in nessun evento. L'hash non deve stare in nessun evento structlog, né in nessun record tranne quelli dei
>       logger che `configure_logging` zittisce.
>     - Quei logger li legge dal sorgente di `logging_config.py`, con una premessa che fallisce se la lettura non trova
>       i tre logger SQL.
>   - **CLI, `invite` e `reset-link`: 10 rossi in `dev-cli-image`**, per `MissingGreenlet`.
>     - La CLI apre `AsyncSession(engine)` con `expire_on_commit=True`, il default; l'app usa `False`.
>     - I due comandi leggevano `issued.record.expires_at` dopo il commit. Ora la leggono prima.
>     - La prova a secco su `git archive` importava l'app ma non eseguiva i comandi: i test IMG di R2 hanno preso
>       il difetto.
>   - **UADM-027**: 2 avvisi di Pydantic nati dal test, da `model_dump()` di righe con `purpose` letto come stringa.
>     R2 ora legge le colonne grezze.

#### A5.5 — Controlli statici ✅ (2026-10-15)
> - **ruff e black**: puliti sui 32 file Python toccati, tranne `scripts/test_runner/_backend_db.py`.
>   - Lì restano 3 PLC0415 (`db_create`, `db_all`) e il formato di black, uguali a HEAD: `ruff` e `black --check`
>     sulla versione di HEAD danno lo stesso esito.
>   - Non lo riformatto: è un file condiviso del runner.
> - **`lint --dead-code --scope backend`** (vulture): nessun reperto nuovo.
>   - Spariscono quelli di A4 su `token_service`, ora usato.
>   - `user_service.count_superusers` resta senza chiamanti in produzione, come a HEAD: lo usano solo i test.
> - **`check-orphans`**: tutti i file registrati; 278 file backend raggiungibili da `all`.
> - **`git diff --check`**: pulito.
> - **OpenAPI**: export a `2ee39823b` contro il worktree (`/tmp/libreFolio_a5a_openapi.sh`), da 134 a 144 operazioni.
>   - **Nuove**: `POST /auth/tokens/inspect`, `POST /auth/password-reset`, `GET /users`, `PATCH /users/{user_id}`,
>     `POST /users/{user_id}/password-reset-link`, `POST /users/{user_id}/onboarding/reset`,
>     `POST /users/{user_id}/sessions/revoke`, `GET` e `POST /users/invites`, `DELETE /users/invites/{invite_id}`.
>   - **Schemi nuovi** (15): `AccountsInstanceConfig`, `AdminUserListResponse`, `AdminUserRead`,
>     `AdminUserUpdateRequest`, `InviteCreateRequest`, `InviteCreateResponse`, `InviteListResponse`, `InviteRead`,
>     `LinkTokenResponse`, `OnboardingResetRequest`, `PasswordResetRequest`, `PasswordResetResponse`,
>     `TokenInspectRequest`, `TokenInspectResponse`, `UserUsageRead`.
>   - **Cambiati**: `AuthRegisterRequest` (`invite_token`), `InstanceConfigResponse` (`accounts`) e l'operazione
>     `POST /auth/register`. Nessuna rimozione.
>   - `openapi.json` e `generated.ts` non sono tracciati: `api sync` lo fa A5b, insieme al frontend.
> - **Riferimenti a `enable_registration`** fuori dai test e dal journal:
>   - corretti gli esempi di `exclusive_because` in `.github/instructions/backend-testing.instructions.md` e
>     `.github/agents/test-author.agent.md`: ora sono uguali al testo del runner;
>   - resta, voluto, il commento di `_scheduler.py:98`: racconta un evento passato;
>   - le doc (`developer/architecture/{settings,access_control}.md`, `test-walkthrough/runner_architecture.md`,
>     `admin/service_exposure` nelle 4 lingue) e il frontend vanno in A5b.
> - **Commenti di H in `test_system_api.py`**, solo commenti: l'intestazione («One field today»), la docstring
>   `exactly {"profile": "selfhosted"}` e quella di `_instance_app()`. Ora dicono `profile` più `accounts`, e che
>   `accounts` legge il DB della corsia.

#### A5.6 — Doc e validazione completa: passano in A5b ⏳
> - **Doc**: la finestra della galleria (dalle 08:45 alle ~12:30) vieta le build nella corsia, `mkdocs build`
>   compreso, quindi prima non si possono verificare in modalità strict. A5a e A5b entrano insieme: le doc di A5a
>   viaggiano nel checkpoint di A5b, con quelle della UI.
>   - Per sviluppatori (EN): `access_control`, `security`, `settings`, `database/users_access`, `database/index` (la
>     006), `users_and_brokers` (chiude la riga di A-7), `runner_architecture`.
>   - Admin, nelle 4 lingue: `cli_tools` e `configuration`.
> - **`all-backend`**, con `front build --debug` e `mkdocs build` prima: gira sulla combinazione A5a+A5b, dopo la
>   finestra.
> - **Guardia J-6** (`dev_release2`, `e2cb55054`), controllata a mano:
>   - i motori privati dei test nuovi sono tutti `NullPool`, con `dispose()` in un `finally`;
>   - il motore dell'app è `NullPool`, quindi `/system/instance` nel processo del test non lascia connessioni;
>   - le fixture di modulo sono solo `test_server`.
>
>   Mi aspetto 0 segnalazioni: lo prova la validazione combinata.

### Checkpoint A5a (backend e CLI) 🧊 (2026-10-15, mattina) — FROZEN, in attesa del commit del coordinatore
> - **Base**: HEAD `2ee39823b`; `dev_release2` locale a `380a3e768`.
> - **Delta**, non in stage: 6 file nuovi e 31 modificati, fra codice, test, runner, `.env.example`, `.github`, il
>   piano e la sezione A del backlog (A-6 aggiornata, A-9 nuova).
> - **Conflitti attesi con `dev_release2`** (`380a3e768`):
>   - **uno testuale, in fondo a `test_system_api.py`**. H CP5a aggiunge 215 righe dopo la riga 855 della base, che
>     qui diventa 5 righe (`{profile, accounts}`). Risoluzione: le mie 5 righe, poi le sue;
>   - vicini ma separati:
>     - `.env.example`: lì la riga 47, qui la 129;
>     - `backend-testing.instructions.md`: lì l'aggiunta di J-6 alla 226, qui le 210–211;
>     - `schemas/system.py`: lì le righe 21, 32 e 50, qui l'8 e l'85;
>     - `conftest.py`: lì la 9 e la 103, qui le 23–98;
>     - `_backend_api.py`: lì la 746, qui la 495 e la 768;
>     - `_backend_services.py`: lì la 495, la 764, la 1134 e la 1217; qui la 455, la 480, la 1107 e la 1125;
>     - backlog: sezioni diverse.
> - **Commit proposti**:
>   1. `feat(accounts): invites, registration, admin API`;
>   2. `docs(journal): A5a progress, A backlog`.
>
> **Esito**: il coordinatore ha committato `7da2cd9a2` (`feat(accounts): invites, registration, admin API`, 35 file) e
> `2d4708578` (journal e backlog). Poi ha aperto il merge di `dev_release2` a `380a3e768` nel mio worktree, senza
> commit, con l'unico conflitto previsto da risolvere a me.

#### A5.7 — Risoluzione del merge di `dev_release2` (`380a3e768`) ✅ (2026-10-15)
> **Note implementazione**: HEAD `2d4708578`, MERGE_HEAD `380a3e768`, conflitto solo in `test_system_api.py`.
> - **Risoluzione** (`/tmp/libreFolio_a5a_resolve_system.py`): prima le mie 5 righe (`{profile, accounts}`), poi le
>   214 righe di H CP5a (`/system/info` per anonimi e per utenti), cioè le sue 215 senza la vecchia asserzione
>   `{"profile": profile}`. Lo script si ferma se i marcatori non sono esattamente uno per tipo, o se la vecchia
>   asserzione non apre il lato di H.
> - **Commenti superati**: erano 4, non 3. I tre già noti erano corretti nel commit di A5a. Il quarto è la docstring
>   in cima (`Covers: … /system/instance … {profile}`), ora `{profile, accounts}`. Rispetto a `380a3e768` il file ha
>   17 righe aggiunte e 7 tolte, tutte mie.
> - **File fusi da Git, controllati a mano**:
>   - ruff e black puliti (`schemas/system.py`, `conftest.py`, `_backend_api.py`, `_backend_services.py`);
>   - azioni del runner contate con l'AST: 65 e 94, nessun doppione nuovo. Il doppione `all` di `_backend_api.py`
>     c'è già su entrambi i lati, a `2ee39823b` come a `380a3e768`.
> - **Controlli senza server** (finestra della galleria; `/tmp/libreFolio_a5a_merge_checks.sh`):
>   - `check-orphans` ✅, 281 file backend;
>   - `services registration` 122 ✅, con la guardia J-6 attiva: 0 segnalazioni;
>   - `db migration-006` 36 ✅;
>   - `services config-package` 594 ✅;
>   - `services config-env-example` 36 ✅;
>   - porta 6182 libera.
> - Poi `git add` del solo file risolto. Il coordinatore ha committato il merge: `8e049474e`, genitori `2d4708578` e
>   `380a3e768`.
> - **⚠️ Fuori pista**: il coordinatore aveva letto in `registration_service.py` le due funzioni di reset per E. Sono in
>   `user_service.py` (righe 233 e 247 di `7da2cd9a2`); lui ha corretto il messaggio per E.

### A5b — frontend di A5 (UI della registrazione, pagine dei link), doc di A5a e A5b, A-9 — in corso

#### A5b.0 — Via, base e regole della finestra ✅ (2026-10-15)
> - **Base**: HEAD `8e049474e`, il merge di `dev_release2` a `380a3e768` sopra A5a. Worktree pulito.
> - **Regole del coordinatore per oggi**:
>   - nella finestra della galleria, dalle 08:45 fino all'avviso di fine (verso le 12:30): solo codice e Vitest su
>     singoli file, uno alla volta (carico della macchina 19–22);
>   - `front check`, build, `mkdocs build`, E2E e `all-backend` solo dopo l'avviso;
>   - A5a e A5b entrano insieme dopo la finestra, dopo i lotti R e L dei colori.
> - **A-9 approvata**: la corsia dei test toglie le quattro variabili degli account, come fa con i segreti di H.
> - **`api sync`** (`/tmp/libreFolio_a5b_api_sync.log`): client rigenerato, non tracciato. Ora ha `AccountsInstanceConfig`
>   e gli alias `inspect_link_token_…`, `reset_password_with_link_…` e `register_…`.
> - **Già rotto da A5a da solo**, e il motivo per cui A5a e A5b entrano insieme:
>   - `RegisterCard` capisce solo i `detail` di tipo stringa: con A5a il 403 «registrazione chiusa» diventa
>     `{error_code, message}`, e la card mostrerebbe l'errore generico;
>   - `LoginCard` legge `enable_registration` dallo store, e la chiave non esiste più;
>   - il tipo `InstanceConfig` del frontend ora vuole `accounts`.

#### A5b.1 — Contratto ✅ (2026-10-15)
> **Moduli nuovi**, in `frontend/src/lib/features/auth/`, Svelte 5, solo classi di ruolo `lf-*` (regola T-1):
> - **`authFlash.ts`**: `setAuthFlash(message)` e `takeAuthFlash()`, che restituisce il messaggio una volta e lo
>   cancella (`''` se non c'è). Così una pagina dei link passa al login il messaggio di riuscita.
> - **`linkToken.ts`**:
>   - `takeLinkToken(url, replace)`: legge `token` (vuoto vale come assente) e chiama `replace(url.pathname)` per
>     toglierlo dalla barra degli indirizzi;
>   - `inspectLinkToken(token, purpose)`: chiama `POST /auth/tokens/inspect`.
> - **`registrationErrors.ts`**: `describeRegistrationError(error)` restituisce `{key}` oppure `{raw}`.
>   - `REGISTRATION_DISABLED` → `auth.registrationDisabled`;
>   - `INVITE_REQUIRED` → `auth.registrationInviteOnly`;
>   - `INVITE_INVALID` → `auth.link.unknown`;
>   - `USER_LIMIT_REACHED` → `auth.userLimitReached`, senza conteggi;
>   - le stringhe e gli array Pydantic come oggi: nome o email già presi, email non valida…
> - **`AuthPageFrame.svelte`**: la barra in alto della pagina d'accesso (caffè, tema, lingua, aiuto) e il contenitore
>   centrato, con `testId`. La usano il login e le due pagine dei link: lo stesso DOM di oggi.
> - **`AuthCard.svelte`**: la testata del marchio e il corpo delle card, per le due card nuove (`testId`).
> - **`LinkStatusCard.svelte`**: `data-testid="link-status"`, `data-status` tra `checking`, `expired`, `consumed`,
>   `revoked`, `unknown`, `missing`, `closed` ed `error`.
>   - Pulsanti: `link-status-goto-login` (vai a `/`); `link-status-retry` solo con `error`.
>   - Messaggi: `auth.link.<status>`, più `auth.link.askAdmin`. Per `closed` usa `auth.registrationDisabled`.
> - **`ResetPasswordCard.svelte`**: props `token`, `username`, `ondone`, `oninvalid`.
>   - testid: `reset-password-modal`, `reset-password-account`, `reset-password-new`, `reset-password-confirm`,
>     `reset-password-submit`, `reset-password-error`.
>   - Le regole sono quelle dell'app, lette da `PasswordStrength` con `bind:valid`, una prop nuova: **nessuna quinta
>     copia** (A-6). L'API resta a 8 caratteri finché non arriva la decisione 37.
>   - Un 400 `TOKEN_INVALID` chiama `oninvalid`.
>
> **Rotte nuove** (servite dal fallback `200.html`, senza prerender):
> - `routes/invite/+page.svelte` (`invite-page`):
>   - legge il token e lo toglie dalla barra (`replaceState` di `$app/navigation`, con ripiego su `history`);
>   - ispeziona il token e intanto carica `instanceConfig`;
>   - token valido e registrazione non `disabled` → `RegisterCard` in modalità invito; altrimenti `LinkStatusCard`;
>   - registrazione riuscita → messaggio flash e `goto('/')`.
> - `routes/reset-password/+page.svelte` (`reset-password-page`): stesso schema, con `ResetPasswordCard`.
> - Entrambe hanno `<meta name="referrer" content="no-referrer">`. Il `<title>` resta vietato dalla guardia.
>
> **File che cambiano**:
> - `RegisterCard.svelte`:
>   - props `inviteToken`, `initialEmail` (email precompilata e **modificabile**: D-A16 respinta) e `grantsAdmin`;
>   - avvisi `register-invite-notice` e `register-invite-admin-notice`;
>   - `invite_token` va nel corpo solo con un invito;
>   - errori da `describeRegistrationError`.
> - `LoginCard.svelte`:
>   - «Registrati qui» solo se `instanceConfig.config.accounts.registration_mode === 'open'`, con `instanceConfig.load()`
>     al montaggio e non più `globalSettings.load()`. Senza risposta valgono i default, quindi il link resta;
>   - il messaggio di riuscita prende il testid `login-success`;
>   - restano i testid di `theme-roles`.
> - `routes/+page.svelte`: usa `AuthPageFrame` (testid `login-page` sullo stesso elemento), e `successMessage` parte da
>   `takeAuthFlash()`.
> - `PasswordStrength.svelte`: `export let valid = false`, che rispecchia `allRulesPassed`. È la sola modifica
>   funzionale, nessuna classe.
> - `GlobalSettingsTab.svelte`:
>   - il default `registration_mode: 'open'`; nella categoria security, `registration_mode` al posto di
>     `enable_registration`;
>   - `SettingSelect` con le opzioni `open`, `invite` e `disabled` (`settings.registrationModes.*`);
>   - con `accounts.registration_locked` il controllo si blocca, mostra il modo effettivo di `/system/instance`, ha il
>     suggerimento `settings.lockedByEnv` e `data-locked="true"` sul contenitore `global-setting-registration_mode`, e
>     «Ripristina tutto» lo salta;
>   - il 409 `SETTING_LOCKED_BY_ENV` diventa `settings.lockedByEnv`;
>   - dopo un salvataggio di `registration_mode`, `instanceConfig.load({force: true})`.
> - `stores/app/globalSettings.ts`: via `enable_registration`. Nessuno lo legge più; la chiave nuova arriva come le
>   altre stringhe.
> - `features/instance/instanceConfig.svelte.ts` di H: `DEFAULT_INSTANCE_CONFIG` aggiunge
>   `accounts: {registration_mode: 'open', registration_locked: false}`. È l'aggancio previsto, da segnalare.
> - **i18n** (4 lingue):
>   - settings: `globalSettingNames.registration_mode`, `globalSettingDescriptions.registration_mode`,
>     `registrationModes.{open,invite,disabled}`, `lockedByEnv`; via le due chiavi `enable_registration`;
>   - auth: `registrationInviteOnly`, `userLimitReached`, `invite.{notice,adminNotice}`,
>     `link.{expired,consumed,revoked,unknown,missing,checkFailed,askAdmin}`,
>     `resetPassword.{title,account,submit,done,failed}`.
>
> **A-9**:
> - `config/accounts.py`: `ACCOUNT_POLICY_VARIABLES` = `LIBREFOLIO_REGISTRATION`, `LIBREFOLIO_MAX_USERS`,
>   `LIBREFOLIO_PUBLIC_URL`, `LIBREFOLIO_BILLING_URL`;
> - `scripts/cli_base.py:configure_test_runtime()` le toglie dopo `_load_project_dotenv()`, accanto a
>   `INSTANCE_TRUST_SECRETS`;
> - test in `test_runtime_isolation.py`, sul modello di `TestTestLaneSecrets`.
>
> **⚠️ Fuori pista — A-9 tolta da A5b** (coordinatore, 15/10 ~09:20). E ha trovato che il problema è più largo: ogni
> `LIBREFOLIO_*` del `.env` arriva alle corsie dei test, comprese le future variabili SMTP. La cura generale la
> scrive H come C-96, e copre anche le quattro variabili degli account.
> - Nel worktree non c'era ancora niente di A-9: né codice né test. La bozza di `config/accounts.py` e
>   `cli_base.py` stava solo in `/tmp`, ed è uscita dallo script di applicazione.
> - Il test-author degli E2E l'ho fermato prima che toccasse `test_runtime_isolation.py`.
> - Nel backlog A-9 rimanda a C-96.
>
> **Fuori da A5b**: `ForgotPasswordCard`. I comandi hanno classi di palette, che sono di T, e il link di reset dalla
> UI arriva con A6.
> **E2E**: nessuno cambia il modo di registrazione della corsia; il blocco da variabile si prova con Vitest.

#### A5b.2 — Test rossi (`test-author`: T1 Vitest, T2 E2E; R1 e R2 per le correzioni di A5a) ✅ (2026-10-15)
> **Note implementazione**:
> - **T1, Vitest**: 16 file, red-first, ciascuno lanciato da solo, uno alla volta.
>   - **Nuovi**: `authFlash` (5), `linkToken` (10), `registrationErrors` (26), `AuthCard` (3), `AuthPageFrame` (2),
>     `LinkStatusCard` (38), `ResetPasswordCard` (20), `routes/page.authFlash` (2), `routes/invite/page` (21),
>     `routes/reset-password/page` (18).
>   - **Aggiornati**: `PasswordStrength` (13), `RegisterCard` (76), `LoginCard` (27), `GlobalSettingsTab` (98),
>     `stores/app/settings` (11), `instanceConfig` di H (11; solo la costante `SELFHOSTED` e `MANAGED`).
>   - Tutti rossi per la ragione giusta: modulo o pagina assenti, oppure il comportamento.
>   - Registrati in `_frontend_utility.py`: 10 righe di percorso.
> - **T2, E2E**, nessuna run (finestra):
>   - `auth.spec.ts`: il blocco «Register link and the registration setting» ora serve `GET /system/instance` reale
>     con il solo `registration_mode` cambiato. Tre test: `disabled` e `invite` nascondono il link, il controllo
>     positivo con `open`;
>   - nuovi `auth-links.spec.ts` (9 test) e `fixtures/instance-config.ts`;
>   - `layout/theme-roles.spec.ts`, file del programma colori: solo il commento e il testo di un messaggio
>     d'errore;
>   - la registrazione dell'azione `front-utility auth-links` l'ho applicata io in `_frontend_utility.py`.
> - **R1 e R2**, correzioni di A5a trovate in revisione (§A5b.3), red-first, nessuna run: le ho lanciate io, una alla
>   volta.
>
>   | Voce | Rossi prima dell'implementazione | Dopo |
>   |---|---|---|
>   | `services account-tokens` | 5 su 65 | 65 ✅ |
>   | `db migration-006` | 27 su 37 | 37 ✅ |
>   | `services registration` | 14 su 135 | 135 ✅ |
>   | `utils dev-cli-image`, solo le classi Invitation, ResetLink e UserLimit | 13 su 22 | 22 ✅ |
>
> - **⚠️ Fuori pista**:
>   - A-9 tolta da A5b (vedi sopra): T2 non l'aveva iniziata.
>   - **`ResetPasswordCard`, 1 rosso dopo l'implementazione**. Il test usa un traduttore identità, quindi un nome
>     interpolato nel messaggio ICU non si vede. Ora il nome è un elemento a sé, e `auth.resetPassword.account` è
>     solo l'etichetta («Account:», «Compte :»…). È anche più solido con nomi che contengono caratteri speciali.

#### A5b.3 — Implementazione ✅ (2026-10-15)
> **Note implementazione**:
> - Bozze in `/tmp/libreFolio_a5b/`, provate prima su una copia di HEAD (`git archive`): ancore, Prettier, parse di
>   Svelte, ruff e black. Poi applicate con `apply_a5b.py` (frontend) e `apply_a5b_backend.py`.
> - **Frontend**: tutto il contratto A5b.1, più:
>   - `addressBar.ts`: `replaceState` di SvelteKit, con ripiego su `history` se il router non è ancora partito;
>   - `hashchange` sulle due pagine dei link.
> - **i18n** (`/tmp/libreFolio_a5b/i18n.sh`, un processo alla volta): 22 chiavi nuove in 4 lingue, via le due di
>   `enable_registration`. `dev.py i18n check` è rigoroso e pulito: 4 412 chiavi.
> - **⚠️ Fuori pista — correzioni di A5a**, dalla revisione delle doc di `docs-writer`:
>   1. **Il token passa nel frammento**: `/invite#token=…`, non più `?token=`.
>      - Il motivo: il `CMD` del Docker avvia uvicorn con il log d'accesso acceso, e `logging_config` non zittisce
>        `uvicorn.access`. Ogni apertura di un link avrebbe scritto il token in chiaro nel log, e così il log di un
>        proxy davanti. Il browser non manda mai il frammento al server.
>      - Cambia una riga in `token_service.token_path`, più le descrizioni di `path` in `schemas/users.py`.
>      - Avvisato il coordinatore, per E e per H.
>   2. **`_report_invalid(problem, consequence)`**: un URL non valido non scrive più «registration stays closed».
>   3. **CLI**:
>      - un `LIBREFOLIO_PUBLIC_URL` non valido si distingue da uno non impostato;
>      - `user activate` avvisa al limite, con un aiuto unico `_warn_if_full(usage, action)`. Le righe di `create` e
>        `invite` restano identiche.
>   4. **`value_type` `str`** per `registration_mode`, come gli altri testi (il registro e la 006, non ancora
>      rilasciata).
>      - Valutato prima di cambiarlo: nessun codice confronta con `"str"`, quindi era solo un'incoerenza.
>      - Cambiarlo dopo il rilascio avrebbe chiesto una migrazione.
>   5. Commenti del runner (`services registration`) e il seed `'string'` di `test_dev_cli_image.py:1348`.

> **Conferma del coordinatore** (15/10, ~10:10), alla lettera: «Confermate tutte e due. 1. **Il token nel frammento**
> (`#token=`): giusto. Lo dico a H, per il log di accesso, e a E, quando partirà il suo lotto. […] 2. **Le altre
> correzioni di A5a**, comprese la 006 con `value_type` `str` e i log più veri: vanno bene in A5b. La 006 non è
> uscita.»
> - Nota per dopo A5, da W e J: la conferma della cancellazione dell'account può dichiarare che le metà dei
>   trasferimenti verso broker condivisi diventano righe a sé (V-3). La aggiunge il coordinatore nella sezione A del
>   backlog, insieme all'estrazione del dialogo da `ProfileTab` per la pagina di blocco di H.

#### A5b.4 — Test verdi nella finestra (Vitest su singoli file, backend senza server) ✅ (2026-10-15)
> **Note implementazione**: `/tmp/libreFolio_a5b_vitest.sh` e `/tmp/libreFolio_a5b_backend_runs.sh`, uno alla volta.
> - **Vitest**, tutti verdi:
>   - i 16 file di T1, compresi i 4 test di `hashchange`;
>   - in più: `layout.gate` 3, `layout.authGate` 11, `PasswordChangeModal` 45, `SettingControls` 85,
>     `documentTitle.guard` 5, `catalogIcuLocale` 17.
> - `node frontend/scripts/theme/theme-roles.mjs --check`: pulito.
> - Prettier pulito sui file toccati.
> - **Backend**:
>   - `config-package` 594, `config-env-example` 36, `global-settings` 19, `db validate` 17, `post-migration` 37;
>   - più le quattro voci della tabella di A5b.2;
>   - ruff e black puliti; `git diff --check` pulito; porta 6182 libera.
> - **Dopo la finestra**:
>   - `front check`, `front build --debug`, `mkdocs build`, `check-links`;
>   - `api registration`, `api users-admin`, `api settings`, `api auth`, `api system`;
>   - `utils dev-cli-image` completo, `all-backend`;
>   - E2E `auth`, `auth-links`, `settings`, `theme-roles`;
>   - `core-unit`, `component-unit`; `lint --dead-code` (vulture e knip); `check-orphans`.

#### A5b.5 — Doc (`docs-writer`, due passate) e ultime correzioni dalla revisione ✅ (2026-10-15)
> **Note implementazione**:
> - **`docs-writer`, prima passata** (A5a, 13 pagine EN): sviluppatore (`access_control`, `security`, `settings`,
>   `database/{users_access,index}`, `users_and_brokers`, `runner_architecture`, `frontend/onboarding`), admin
>   (`configuration`, `cli_tools`, `settings`, `service_exposure`), `community/faq`. Nessuna build: finestra.
> - **Seconda passata** (A5b e correzioni, 18 pagine EN):
>   - `?token=` diventato `#token=`, con il motivo scritto una volta in `security.md` «Links in Use»;
>   - frontend: `features/auth.md` (sezione «🔗 Account Link Pages»), `features/settings.md`, `state/app-state.md`,
>     `pages/index.md`, `components/index.md`, `test-walkthrough/front-utility.md`;
>   - utente: `user/getting-started` («✉️ If You Received an Invitation Link», «🔑 If an Administrator Sent You a
>     Password-Reset Link»), `community/faq`;
>   - admin `settings`: l'avviso per un'istanza nuova con la registrazione bloccata su `invite` o `disabled` (il primo
>     admin da `dev.py user create` fino ad A7).
> - **⚠️ Fuori pista — due difetti trovati dalla revisione delle doc**, corretti red-first:
>   1. **Il primo account non spendeva il suo invito.** Su un'istanza vuota `_admission` rispondeva prima di guardare il
>      token, quindi lo stesso link poteva aprire un secondo account, con il suo ruolo, per 7 giorni.
>      - Ora un invito dato con qualunque registrazione, la prima compresa, dev'essere valido e viene speso.
>      - Il primo account resta amministratore, qualunque siano la modalità e il ruolo dell'invito.
>      - R1 ha scritto 8 casi di servizio e 1 di API. `services registration`: 8 rossi, poi 146 ✅. Il caso API gira
>        dopo la finestra.
>   2. **`ResetPasswordCard` non diceva ai gestori di password a quale account va la password nuova.** Ora ha il campo
>      `autocomplete="username"` nascosto, come `PasswordChangeModal`. T1 ha scritto 4 test: 1 rosso, poi 24 ✅.
> - **Debito di traduzione** (IT, FR ed ES in ritardo), sei pagine da tradurre insieme perché si linkano per ancore
>   esplicite: `admin/{configuration,cli_tools,settings,service_exposure}`, `community/faq`, `user/getting-started`.
>   - Senza traduzioni il build strict resta sano: le pagine IT, FR ed ES vecchie non puntano alle ancore nuove.
>   - Proposta al coordinatore: tradurle una volta sola alla fine di A (A10), perché A6–A9 toccheranno di nuovo le
>     stesse pagine.
> - **Segnalazioni fuori dal mio perimetro**:
>   - di T: `features/auth.md` descrive ancora la barra di robustezza a cinque colori (D-T13 l'ha fatta a tre), e
>     `core-ui/atoms.md` non ha la prop `icon` di `PasswordInput`;
>   - `host_installation.en.md:112`, `user/installation.en.md:135` e `docker_advanced.en.md:280` descrivono il primo
>     avvio di default, che non cambia, senza l'avviso per la modalità bloccata. L'avviso sta in `admin/settings`.
> - **devWiki** (`wiki-file`):
>   - nuova [[decisions/link-tokens-in-the-url-fragment]];
>   - aggiornate `domains/auth.md` (modalità, inviti, API admin, limite, K-5 fino ad A7, i lotti seguenti) e
>     `features/F-001.md`;
>   - `check_source_paths.py`: nessun percorso mancante nelle mie pagine; i 5 che segnala sono vecchi;
>   - grafo non aggiornato (P-6).

#### A5b.6 — TC-6 (A-8): il selettore della lingua alla prima visita ✅ (2026-10-15)
> **Note implementazione**: A5b tocca la pagina d'accesso, che è il lotto suggerito dal coordinatore per TC-6.
> - **Causa**: senza preferenza salvata, `currentLanguage.init()` leggeva `locale` di svelte-i18n una volta sola e si
>   disiscriveva. Ma svelte-i18n passa a `it` solo dopo aver caricato il dizionario, quindi al montaggio leggeva ancora
>   `en`, e il selettore restava su 🇬🇧 mentre la pagina era in italiano.
> - **Correzione stretta** (`stores/app/language.ts`):
>   - senza preferenza salvata il negozio segue `locale`, con un solo abbonamento anche se `init()` gira due volte;
>   - smette di seguirlo appena si sceglie una lingua dal negozio (`set`, `cycle`);
>   - con una preferenza salvata non lo segue.
>   - L'anteprima della lingua nella Welcome non è toccata: `persistedLanguage` viene dalle impostazioni dell'utente,
>     non dal negozio.
> - `LanguageSelector.svelte` pubblica `data-language`, una presa stabile per l'E2E.
> - **Test**:
>   - T1 ha scritto `language.test.ts` (7). La prima run è fallita per un'infrastruttura assente (`localStorage` di
>     jsdom nascosto da Node 26) e T1 l'ha sostituito con uno stub. Poi 6 rossi per la ragione giusta e 7 ✅;
>   - T2 ha scritto l'E2E `it-IT` e `fr-FR` in `auth.spec.ts`, che gira dopo la finestra;
>   - vicini verdi: `settings` 11, `PreferencesTab` 58, `WelcomeForm` 14, `uiLocale` 31, `AuthPageFrame` 2, `Header` 28.
> - Backlog A-8 chiusa (✅, commit all'ingresso di A5).

### Checkpoint A5b («prima delle prove») 🧊 (2026-10-15, 10:40) — FROZEN, in attesa del commit del coordinatore
> **Decisioni del coordinatore** (15/10, ~10:30):
> - validazione completa una sola volta, dopo il suo aggiornamento di base con R e L; se dopo entra un altro lotto,
>   basta un controllo leggero;
> - prima, l'handoff FROZEN di A5b, che lui committa sul mio ramo come checkpoint «prima delle prove», così
>   l'aggiornamento di base si fonde su lavoro committato;
> - le traduzioni: tutte insieme dopo A6–A9, solo su richiesta esplicita del developer. Registrate come A-10.
>
> **Stato**:
> - **Base**: HEAD `8e049474e`; `dev_release2` locale a `6ed99c694` (due commit di journal, che toccano il backlog in
>   righe lontane dalla sezione A).
> - **Delta**, non in stage: 24 file nuovi e 65 modificati.
> - **Esclusi**:
>   - gli artefatti ignorati: client API generato, `openapi.json`, il catalogo i18n generato, `.testLog`, le cache;
>   - un vecchio `backend/data/prod/logs/librefolio.log` del worktree, ignorato;
>   - le bozze in `/tmp`.
> - **Prove**: quelle di A5b.2–A5b.6, tutte dentro le regole della finestra.
> - **Da fare dopo l'aggiornamento di base**: lo script `/tmp/libreFolio_a5full.sh`.
> - **Commit proposti**:
>   1. `feat(accounts): invite and reset link pages`: codice, test, runner, doc EN, devWiki;
>   2. `docs(journal): A5b progress, A backlog`: piano e backlog.
>
> **Esito**: il coordinatore ha committato `2b0715532` (`feat(accounts): invite and reset link pages`, 87 file; il corpo
> cita le correzioni di A5a, TC-6 e il debito A-10) e `db887eca3` (journal). Le tre righe del CHANGELOG le scrive lui
> all'ingresso.

#### A5b.7 — Aggiornamento di base con R e L (`246863005`) ✅ (2026-10-15)
> **Note implementazione**:
> - **Nuova regola per tutta la macchina** (coordinatore, 13:01, dopo che il carico era arrivato a 65): al massimo 2
>   suite pesanti alla volta.
>   - Le pesanti (`all-backend`, una categoria `front-*` intera, `utils all`, la galleria) le assegna lui.
>   - Libere, con `nice -n 10`: azioni singole, Vitest, una spec E2E con `--workers 2`, `front build`,
>     `front check`, `mkdocs build`.
>   - Il runner passa `--workers N` a Playwright come `E2E_WORKERS`.
> - **Merge** di `dev_release2` a `13705dd05`, aperto dal coordinatore. Porta R e L dei colori, X-R8, W E0, J-6 e
>   l'analisi di E: 43 commit, 227 file.
>   - **Unico conflitto**: `LibreFolio_devWiki/log.md`. Risolto unendo le due parti in ordine di tempo: la mia voce di
>     A5b (commit delle 10:35), poi quella di R (11:45).
>   - **File fusi da Git che entrambe le parti toccano**, rivisti: `index.md`, il backlog, `runner_architecture.md` e
>     `_frontend_utility.py`. In ognuno ci sono tutte e due le parti, in zone separate.
>     - Il runner non ha azioni doppie, e i percorsi Vitest tornano: 285 della base + 11 miei + 6 loro = 302.
>     - I 16 percorsi elencati due volte c'erano già nella base e nei due genitori.
>   - **Sovrapposizioni che Git non vede**: R e L non toccano nessuno dei componenti né dei moduli che A5b usa o
>     cambia. Cambiano però la baseline del ratchet dei colori e aggiungono tre gate che leggono tutto `src/`.
>   - **Controlli sull'albero fuso**, prima dello stage:
>     - ruff e black sul runner: puliti;
>     - `theme-roles.mjs --check`: pulito. Segnala «81 file sotto il loro record», tutti di R: stringere la baseline
>       spetta al programma colori;
>     - i 9 gate `src/*.gate.test.ts`, ciascuno lanciato da solo, tutti verdi: `themeRoles` 36, `themeTokens` 14,
>       `themeComponentTokens` 18, `themeModeReads` 24, `themeColorMeta` 10, `htmlSink` 7, `htmlInterpolation` 26,
>       `clipboardSink` 11, `flagFont` 13.
>   - Poi `git add` del solo `log.md`. Il coordinatore ha committato il merge: `246863005`, genitori `db887eca3` e
>     `13705dd05`.
> - **T-B4 → TC-4**: nel backlog fuso la sezione «T (colori)» usa ancora T-B4. I richiami di A-6 e del piano restano
>   com'erano fino alla rinomina.
> - **Finestra delle dipendenze** (13:10): il developer installa `cryptography` nell'ambiente condiviso. Niente comandi
>   Python finché il coordinatore non dà la ripresa; dopo, lo script leggero (`/tmp/libreFolio_a5light.sh`).
>   - Lo script parte da `api sync`, perché un merge può lasciare vecchio il client generato. `front build` lo fa già
>     da sé (`dev.py:627`), ma il passo esplicito lascia un log suo.
>   - `all-backend` (`/tmp/libreFolio_a5heavy.sh`) aspetta lo slot del coordinatore, dopo H e X.

#### Nota per A8 — il limitatore di E (coordinatore, 15/10 13:03, D-E12)
> Il limite dei tentativi di A8 **riusa** `backend/app/utils/runtime/rate_window.py`, che entra con E1 nel prossimo
> treno. Non se ne scrive un altro.
> - `SlidingWindowLimiter(limit, window_seconds, *, max_keys=10_000, clock=time.monotonic)`.
> - `hit(key, *, limit=None)` restituisce `RateDecision(allowed, remaining, retry_after)`; un colpo rifiutato non
>   conta.
> - `peek` e `count` non creano chiavi; ci sono anche `reset(key)` e `clear()`.
> - Vale per processo ed è thread-safe.

#### A5b.8 — Validazione della revisione combinata `246863005`: la parte leggera ✅, il resto nello slot ⏳ (2026-10-15)
> **Note implementazione**:
> - Ripresa alle 13:36, dopo la finestra delle dipendenze (`cryptography 50.0.2` nell'ambiente condiviso).
> - Script leggero `/tmp/libreFolio_a5light.sh`, con `nice -n 10`, un passo alla volta; log in
>   `/tmp/libreFolio_a5full_<passo>.log`.
>
>   | Passo | Esito |
>   |---|---|
>   | `api sync` | ✅ |
>   | `front build --debug` | ✅, 0 errori e 0 avvisi |
>   | `front check` | ✅, 0 errori e 0 avvisi |
>   | `mkdocs build` (strict) | ✅, nessuna riga `WARNING`; il riquadro di Material su MkDocs 2.0 è il solito banner |
>   | `mkdocs check-links` | ✅, 95 link validi |
>   | `theme-roles.mjs --check` | ✅ |
>   | `check-orphans` | ✅, tutto registrato |
>   | `front-utility core-unit` | 4 419 ✅ |
>   | `front-utility component-unit` | 3 366 ✅, in 451 s |
>   | `utils gate-i18n-catalog` | 176 ✅ |
>
> - **⚠️ Fuori pista — il carico**: alle 13:56 il carico della macchina era fra 110 e 139.
>   - Il coordinatore ha chiesto di lasciar finire il comando in corso e poi fermarsi. Le categorie Vitest ed E2E
>     sono passate fra le prove pesanti, da fare in uno slot assegnato.
>   - `component-unit` (una dozzina di worker) era pesante, anche se lo script la trattava come leggera.
>   - Ho fermato lo script con `kill` del solo processo bash, lasciando finire `gate-i18n-catalog`. Nessun altro
>     comando mio è in corso; la porta 6182 è libera.
> - **Nello slot del coordinatore**, il terzo, dopo H: `/tmp/libreFolio_a5slot.sh`.
>   - `all-backend` seriale, con `nice -n 10`. Copre tutte le categorie del backend (external, db, services, utils,
>     schemas, api, e2e), quindi anche le azioni `api` di A5 (registration, users-admin, auth, settings, system),
>     `gate-i18n-usage` e `dev-cli-image`. Non le lancio a parte.
>   - Poi le 5 spec E2E, una alla volta, con `--workers 2`: `auth`, `auth-links`, `settings`, `theme-roles`,
>     `app-start-auth`.

#### A5b.9 — Slot pesante 2: `all-backend` ed E2E; riparazione di `settings.spec.ts` ✅ (2026-10-15)
> **Note implementazione**: slot assegnato dal coordinatore alle 14:01; `/tmp/libreFolio_a5slot.sh`, `nice -n 10`, un
> passo alla volta; log in `/tmp/libreFolio_a5full_<passo>.log`.
> - **`all-backend`**, seriale, su `246863005`: exit 0 in 29 min 22 s.
>   - **14 640 ✅**, 28 saltati, 0 falliti, 0 errori; 7 categorie su 7.
>   - **Guardia J-6**: nessuna segnalazione sui test reali. Le due che compaiono vengono da `test_synthetic_leaks.py`,
>     cioè le perdite volute che `gate-aiosqlite-leak` usa per provarsi. «Event loop is closed» compare solo nel
>     testo esplicativo della guardia.
> - **E2E**, una spec alla volta con `--workers 2`:
>
>   | Spec | Esito |
>   |---|---|
>   | `auth` | 33 ✅, compreso TC-6 con `it-IT` e `fr-FR` |
>   | `auth-links` | 9 ✅ |
>   | `theme-roles` | 8 ✅ |
>   | `app-start-auth` | 3 ✅ |
>   | `settings` | 43 ✅ e **3 ❌** |
>
> - **⚠️ Fuori pista — i 3 rossi di `settings` li ha causati A5b** (triage §1: un'ipotesi di posizione).
>   - Il blocco «Toggle & Number Interaction» prendeva il primo interruttore della scheda per posizione (`.first()`).
>     Prima di A5b era «Enable Registration»; ora la registrazione è una select, e il primo interruttore è «Require
>     Email Verification», un segnaposto sempre disabilitato.
>   - «toggles are disabled when locked» passava per il motivo sbagliato, e così il test «non admin».
>   - **Cura**, approvata dal coordinatore:
>     - `GlobalSettingsTab.svelte`: le righe booleane pubblicano `data-testid="global-setting-<key>"`, come già quelle
>       numeriche e di testo. È un attributo aggiunto; nessun test contava questi handle;
>     - un `test-author` nuovo ha riscritto i quattro test e il non-admin su `scheduler_enabled`.
>       - Lo stato si legge da `aria-checked`; si usano `setting-save` e `setting-undo`, mai Save;
>       - «disabled when locked» ora prova anche lo sblocco; `settings.spec.ts` +58/−42, Prettier pulito.
>   - **Verifiche**: Vitest `GlobalSettingsTab` 98 ✅ (`--maxWorkers 2`); `front build --debug` 0 errori e 0 avvisi;
>     `theme-roles.mjs` pulito.
> - **Ripetizione di `settings`** (14:47), senza bisogno del via, come detto dal coordinatore: **45 ✅ e 1 ❌**.
>   - Il rosso: «admin can unlock global settings for editing», che la cura non tocca. Superati i 30 s del test nel
>     `beforeEach`, con la scheda ancora su «Loading...».
>   - Nel mio comando di una riga l'exit stampato era sbagliato: `$(date)` girava prima di `$?` e lo azzerava. Il
>     runner diceva FAILED; da lì in poi `rc=$?` subito dopo il comando.
>   - **Triage** (skill `test-triage`; prove salvate in `/tmp/libreFolio_a5fix_evidence/`):
>     - §1, la forma: non c'entra. Il test aspetta la condizione giusta, le impostazioni caricate, e nessuna posizione;
>     - §2, l'orologio: nessuna attesa fissa. Il tempo è finito nell'insieme login + navigazione + caricamento;
>     - in quella run **ogni** test è stato 4–6 volte più lento dello stesso test alle 14:32 (per esempio «number
>       inputs are disabled when locked»: 1,7 s, poi 7,8 s), e la spec intera è passata da 1,7 a 3,0 minuti;
>     - l'altro test del blocco, partito insieme sull'altro worker, è passato a 27,6 s;
>     - nel log del server, nei minuti del rosso (12:48–12:49 UTC), solo accessi ordinari: nessun errore, nessuna
>       attesa di lock;
>     - la ripetizione (14:53–14:57), con il carico salito da 68 a 86, dà **46 ✅ su 46**; lo stesso test in 4,4 s, il
>       blocco fra 4 e 8 s.
>   - **Verdetto: lentezza da contesa sulla macchina**, non un difetto di A5b né un'ipotesi del test. Nessuna modifica.
>     Il carico della macchina lo governa il coordinatore.
> - **Backlog**:
>   - A-11: il tema non valido che blocca l'accesso, dal `test-author` di E, segnalata dal coordinatore;
>   - A-12: i selettori fragili rimasti in `settings.spec.ts`, notati dal `test-author` della riparazione; si fanno
>     con A6.

### Checkpoint A5 d'ingresso (A5a + A5b) 🧊 (2026-10-15, 15:05) — FROZEN, in attesa del commit e dell'ingresso
> - **Base**: HEAD `246863005` (merge di `dev_release2` a `13705dd05` sopra A5a e A5b).
> - **Delta**, non in stage:
>   - `GlobalSettingsTab.svelte`, l'handle delle righe booleane;
>   - `e2e/settings.spec.ts`, la riparazione;
>   - il piano (da A5b.7 ad A5b.9 e questo checkpoint);
>   - il backlog (A-11 e A-12).
> - **Validazione della combinazione**:
>   - leggera (A5b.8): `api sync`, build, check, mkdocs strict, link, `theme-roles`, `check-orphans`, `core-unit`
>     4 419, `component-unit` 3 366, `gate-i18n-catalog` 176;
>   - pesante (A5b.9): `all-backend` 14 640 ✅ e 0 ❌; E2E `auth` 33, `auth-links` 9, `theme-roles` 8,
>     `app-start-auth` 3, `settings` 46 dopo la riparazione.
> - **Commit proposti**:
>   1. `test(settings): target editable toggle by key`: la riparazione e l'handle;
>   2. `docs(journal): A5 validation, A backlog`.
>
> **Esito**: il coordinatore ha committato `8e78adca6` (`test(settings): target editable toggle by key`) e `650807850`
> (journal). Il CHANGELOG lo scrive lui all'ingresso con il mio testo; `enable_registration` → `registration_mode` va
> sotto ⚠️ Breaking changes.

#### A5b.10 — Secondo aggiornamento di base (`7fa6a14b9`): H CP6, X FE5b, E1, `cryptography` ✅ (2026-10-15)
> **Note implementazione**:
> - **Merge** di `dev_release2` a `8fc44558c`, aperto dal coordinatore: 95 file. Cinque conflitti, risolti tenendo
>   le due parti (`/tmp/libreFolio_a5m3_resolve.py`, che controlla le prime righe attese di ogni blocco):
>   - `schemas/system.py`: il mio campo `accounts` di `InstanceConfigResponse`, poi la classe `InstanceBlockResponse`
>     di H (`GET /system/block`, solo per utenti con sessione);
>   - `security.md`:
>     - H e `docs-writer` avevano scritto la stessa riga pubblica di `GET /settings/global`: ne resta una, quella
>       con il link;
>     - il paragrafo «Private Endpoints» unisce la pagina del blocco di H e la mia frase su `/users` e
>       `require_admin`;
>   - `settings.md`: i moduli di `config/`, con i miei accessori, quelli di X ed `email.py` di E.
>     - La frase finale ora è vera anche per gli URL: un URL non valido non chiude la registrazione.
>   - `_backend_services.py`: la mia `services_registration` e le quattro azioni e-mail di E. Le due chiamate che
>     condividevano la chiusura sono ricostruite: 98 azioni, nessun nome doppio.
>   - `_frontend_utility.py`: nella lista `core-unit`, i miei 3 file e i 2 di H. 28 azioni, nessun doppione.
> - **File fusi da Git che entrambe le parti toccano**, rivisti, tutti in zone separate: `.env.example`, `models.py`,
>   `test_system_api.py`, `admin/configuration`, `app-state.md`, `test-author.agent.md`, `_backend_api.py`.
>   - Nessuna ancora o sezione `.env` doppia.
>   - Prima dello stage: l'app si importa; OpenAPI ha 146 operazioni, con `InstanceConfigResponse` =
>     `profile` + `accounts`.
> - Poi `git add` dei soli 5 file. Il coordinatore ha committato il merge: `7fa6a14b9`, genitori `650807850` e
>   `8fc44558c`.
> - **Validazione** chiesta dal coordinatore, in fila e con `nice -n 10` (`/tmp/libreFolio_a5v3.sh`; log
>   `/tmp/libreFolio_a5v3_<passo>.log`):
>
>   | Passo | Esito |
>   |---|---|
>   | `api sync` | ✅ |
>   | `front check` | ✅, 0 errori e 0 avvisi |
>   | `api registration` | 65 ✅ |
>   | `api users-admin` | 53 ✅ |
>   | `api auth` | 60 ✅ |
>   | `api settings` | 95 ✅ |
>   | `api system` | 117 ✅, con i test del blocco di H |
>   | `services config-package` | 640 ✅ |
>   | `services config-env-example` (mio, `.env.example` fuso da tre parti) | 36 ✅ |
>   | `db populate --force` | ✅ (la categoria `services` svuota il DB della corsia) |
>   | E2E `auth` | 33 ✅ |
>   | E2E `settings` | 46 ✅ |
>   | `theme-roles.mjs --check` | ✅ |
>
>   - Il build del frontend l'ha rifatto l'avvio del server durante `api registration`, alle 15:07:22, sulle
>     sorgenti fuse; le E2E l'hanno trovato «up to date».
>   - L'unico avviso, in `api registration`: `StarletteDeprecationWarning` su `HTTP_422_UNPROCESSABLE_ENTITY`, da
>     un ramo di `api/v1/settings.py` che c'era già (`84d9e3360`, quattro usi in quel file). Non è di A5.
>   - Porta 6182 libera alla fine.
> - **I due punti di CP6**, decisi dal coordinatore:
>   1. le rotte admin di A (inviti, link di reset, `/users`) rispondono 423 sull'istanza bloccata: va bene, coerente
>      con la decisione 12 (D-A15);
>   2. il reset della password resta permesso: H aggiunge `auth.inspect_link_token` e `auth.reset_password_with_link` a
>      `ALLOWED_WHEN_BLOCKED` e al test che fissa l'elenco, in un lotto piccolo dopo A5.
>      - `auth.register` resta fuori.
>      - Oggi un anonimo su una rotta bloccata riceve 401, e sulle pagine dei link l'interceptor del client porta al
>        login, perdendo il token.
> - **Backlog A-13**: su un'istanza bloccata `/invite` mostra il modulo (`tokens/inspect` risponde anche per gli
>   inviti), poi la registrazione finisce al login. Accettato dal coordinatore.
> - **Per A8**: il limitatore `rate_window.py` di E (D-E12) ora è nella base.

### Checkpoint A5, base aggiornata (`7fa6a14b9`) 🧊 (2026-10-15, 15:20) — FROZEN, pronto per l'ingresso
> - **Delta**, non in stage: il piano (A5b.10 e questo checkpoint) e il backlog (A-13).
> - **Commit proposto**: `docs(journal): A5 second base update, CP6 notes`.

### A6 — scheda Utenti: eliminazione da parte dell'admin, verifica dell'indirizzo, UI (CP A6a + A6b) — in corso

#### A6.0 — Via e decisioni ✅ (2026-10-15)
> - **Ordine dei lotti** approvato dal coordinatore: A6, poi A8, poi A7.
> - **Base**: `46c159ebc`, già dentro `dev_release2` (`8bcb23502`), quindi nessun aggiornamento.
> - **Due handoff**: A6a, il backend, FROZEN; poi A6b, il frontend.
> - **Le cinque domande**, risposte del coordinatore:
>   1. **Verifica dell'indirizzo (D-A3, punto 2 del developer)**: «se lo modifica, un controllo dal browser verifica
>      che a quell'indirizzo risponda davvero l'istanza».
>      - Il coordinatore proponeva un `instance_id` stabile in `/system/instance`, con CORS `*`. Ho segnalato il
>        rischio: una pagina qualsiasi, visitata da chi è sulla rete dell'istanza, leggerebbe configurazione e id della
>        LibreFolio in LAN, e riconoscerebbe la stessa istanza a due indirizzi.
>      - **Scelto il nonce firmato**: due rotte in A6a, ciascuna con il suo rosso, compresi un nonce falsificato e uno di
>        un'altra istanza, entrambi `{match: false}`.
>      - H conferma che il `CORSMiddleware` globale lascia passare l'header della mia rotta, e che `derive_key` va bene
>        per questo uso.
>   2. **Eliminare un altro admin**: prima va declassato (punto 8 del developer). Nel cloud l'admin creato dalle
>      variabili, cioè chi paga, non si elimina, non si disattiva e non si declassa: è di A7, e A6 ne prepara il punto
>      d'aggancio.
>   3. **`ProfileTab`**: via del coordinatore colori. T arriva a quel file fra giorni (W2-f1), quindi il taglio lo
>      faccio io.
>      - `AccountDeletionDialog` nasce solo con ruoli `lf-*`, senza letterali, quindi senza `--split`.
>      - Il pulsante rosso usa `bg-lf-danger text-lf-on-status`.
>   4. **«Spedisci per email» di E**: le finestre dell'invito e del reset hanno uno spazio per un'azione in più.
>   5. **Frase V-3**: provvisoria, concordata con W, poi la sua definitiva.

#### A6.1 — Contratto di A6a (backend) ✅ (2026-10-15)
> **Anteprima dell'eliminazione** — `user_service.preview_user_deletion(session, user_id)`:
> - Restituisce `AccountDeletionPreview(user_id, username, brokers_deleted, brokers_left, transfers_unpaired)`, oppure
>   `None` se l'utente non esiste. Non scrive niente.
> - **La regola è quella di `BrokerService.leave_broker`** (`services/brokers/access.py`), applicata da `delete_user`:
>   per ogni broker a cui l'utente accede, se è OWNER e non c'è un altro OWNER il broker sparisce, con le sue
>   transazioni; altrimenti se ne va solo il suo accesso.
>   - Il file di W non si tocca. L'equivalenza la fissa un test: per ogni scenario, gli id previsti sono quelli che
>     `delete_user` cancella davvero.
> - `brokers_deleted`: `{broker_id, name, transactions}`, in ordine di id.
> - `brokers_left`: `{broker_id, name, role}`, in ordine di id.
> - `transfers_unpaired` (V-3): le transazioni che restano e sono collegate, in un verso o nell'altro
>   (`related_transaction_id`), a una transazione che sparisce. Sono le metà che restano da sole.
>
> **Un aiuto unico per eliminare** — `user_service.delete_account(session, user) -> AccountDeletionResult`:
> - `delete_user`, poi i file BRIM dei broker cancellati rimossi dopo il commit (`brim_provider.delete_files_for_brokers`,
>   in un thread);
> - restituisce `deleted_broker_ids` e `files_removed`;
> - lo usano sia la cancellazione del proprio account (`DELETE /auth/users/me`, che non cambia comportamento) sia quella
>   da parte dell'admin.
>
> **Punto d'aggancio per A7** — `user_service.account_protection(user) -> Optional[str]`:
> - oggi restituisce sempre `None`; A7 restituirà un motivo per l'admin creato dalle variabili;
> - `PATCH /users/{id}` (disattivare, declassare) e `DELETE /users/{id}` lo consultano, e con un motivo rispondono 409
>   `ACCOUNT_PROTECTED`;
> - `AdminUserRead.protected: bool`, così la UI di A6b spegne le azioni.
>
> **API**:
> - `GET /users/{user_id}/deletion-preview`, admin: 200 `AccountDeletionPreviewRead`; 404, 401 e 403.
> - `GET /auth/users/me/deletion-preview`, con sessione: la stessa forma per sé. Serve al dialogo estratto e alla
>   pagina di blocco di H, a cui va chiesta la riga in `ALLOWED_WHEN_BLOCKED`.
> - `DELETE /users/{user_id}`, admin, 204:
>   - 404 per un utente che non c'è;
>   - 409 `SELF_DELETION` per se stessi: il proprio account si cancella dal profilo;
>   - 409 `DEMOTE_FIRST` se il bersaglio è un amministratore, attivo o no. Così l'ultimo admin non si cancella mai da
>     qui;
>   - 409 `ACCOUNT_PROTECTED` dall'aggancio di A7;
>   - un errore tecnico dà 500 «nothing was deleted», come nel caso del proprio account;
>   - log strutturato «Account deleted by an administrator», con `user_id`, `username`, `admin_id`, `brokers_deleted` e
>     `files_removed`.
>
> **Verifica dell'indirizzo** — nuovo `services/accounts/address_probe.py`:
> - **Il nonce**: `base64url` senza padding di `rand16 ‖ expiry_be8 ‖ HMAC-SHA256(derive_key("accounts.address-probe.v1"),
>   rand16 ‖ expiry_be8)`, valido 120 s.
> - `issue_probe_nonce(now=None) -> (nonce, expires_at)`.
> - `verify_probe_nonce(nonce, now=None) -> bool`:
>   - `False` per tutto il resto: malformato, troppo lungo (oltre 256 caratteri), firma sbagliata, scaduto, firmato da
>     un'altra istanza;
>   - confronto in tempo costante; non solleva mai.
> - `POST /users/address-probe`, admin: 200 `{nonce, expires_at}`.
> - `GET /auth/address-probe?nonce=…`, pubblica: 200 `{match: bool}` e nient'altro.
>   - Header `Access-Control-Allow-Origin: *`, impostato dalla rotta, e `Cache-Control: no-store`.
>   - Con un'istanza bloccata non serve: resta fuori da `ALLOWED_WHEN_BLOCKED`.
>
> **Prove di A6a**: i test le fissano, compreso un `Origin` estraneo sul server della corsia, perché l'header deve
> sopravvivere al `CORSMiddleware`.
>
> **Fuori da A6a**: la UI (A6b), le traduzioni (A-10), la frase definitiva di V-3 (W).

#### Decisione 37 (A-6): regole della password uniche — lotto **A6c**, dopo A6b e prima di A8 (2026-10-15)
> **Testo del developer**, alla lettera: «si sono daccordi in questa centralizzazione, fai in modo che il backend esponga
> le regole così che il frontend possa correttamente mostrarle e se si aggiornano si aggiorna anche nella ui, però
> teniamo l'indicatore di sicurezza.»
>
> **In sintesi, dal coordinatore**:
> - le regole si scrivono una volta sola nel backend, che le applica anche all'API;
> - un endpoint le espone, e il frontend le mostra da lì: registrazione, cambio password, reset, invito;
> - la riga di comando usa la stessa funzione;
> - l'indicatore di robustezza resta;
> - le password già salvate restano valide.
>
> **Perché un lotto a sé, A6c**: quando l'API applica le regole, ogni test o fixture che registra o cambia una password
> debole via API diventa rosso. Serve una ricognizione di tutta la suite e un `all-backend` suo. Dentro A6, già
> medio-alto, mescolerebbe due rischi in un checkpoint.
>
> **Disegno, da verificare nell'analisi di A6c**:
> - un modulo unico nel backend (`services/accounts/password_rules.py`) con le regole come dati: `id`, tipo e
>   parametro (`min_length` 8, `uppercase`, `lowercase`, `digit`, `symbol` con l'insieme dei simboli);
>   `failed_rules(password)` le valuta;
> - `GET /api/v1/auth/password-rules`, pubblica e innocua (le regole non sono un segreto), le restituisce;
> - **il frontend**: `PasswordStrength` mostra l'elenco ricevuto, valuta dal vivo i tipi che conosce, e un tipo nuovo
>   lo mostra solo come testo (lo controllerà il server all'invio). L'indicatore zxcvbn resta;
> - le quattro copie di oggi spariscono: `PasswordStrength`, `RegisterCard`, `PasswordChangeModal` e
>   `user_cli.validate_password`. Restano le chiavi i18n `auth.passwordStrength.rules.*`;
> - **l'API** (registrazione, cambio password, reset) rifiuta con un codice e l'elenco delle regole mancate;
>   `create_user` del servizio resta permissivo per i dati di prova e per la CLI, che chiama la funzione da sé;
> - il login non controlla le regole: le password già salvate restano valide.
>
> **Dal programma colori (coordinatore, 15/10 16:07, solo informazione)**: T-8 aggiunge a `ui/input/PasswordInput.svelte`
> la direttiva `class:hover:border-lf-input-hover={!hasError}`, l'hover del bordo, accanto a quelle di T-2. Non tocca
> markup né logica; K-17 sta su altre righe. Se A6c passa da quel file, lavora sopra la versione convertita (controllo
> all'aggiornamento di base prima di A6c).

#### Note di H su A5 (15/10, ~15:50), dalla verifica di C-96
> - **LIVE-002** (`test_registration_api.py`) non ha la precondizione che ha `users-admin`. Lanciata da sola su un DB di
>   corsia vuoto fallisce con `assert True is False`, senza messaggio.
>   - Il motivo: dalla correzione di A5b il primo account di un'istanza vuota è sempre admin, anche con un invito.
>   - **Cura, in A6a**: la precondizione va *prima* della registrazione, perché su una corsia vuota il test creerebbe
>     l'admin della corsia. Deve dire che la preparazione `api` (`db populate`) non è girata, come fa `users-admin`.
>     L'asserzione dopo prende un messaggio.
> - **`test_instance_block.py`** fissava il corpo di `/system/instance` a `{"profile": …}` e si era rotto con
>   `accounts`. H l'ha riparato confrontando ogni risposta con quella a blocco spento: i campi che si aggiungono lì non
>   lo rompono più.
> - H è entrato: `dev_release2` = `744f5a0ee`.

#### Conferma di H sul nonce firmato (15/10, ~16:00)
> 1. **CORS: sì.** H l'ha provato in processo con i parametri di `main.py`. Su una GET semplice resta
>    l'`Access-Control-Allow-Origin: *` della rotta; il middleware aggiunge solo `Access-Control-Allow-Credentials: true`,
>    che con `credentials: 'omit'` il browser ignora.
>    - **Vincolo per A6b**: un header custom, `Content-Type: application/json` o un metodo non semplice fanno partire un
>      OPTIONS, che il middleware rifiuta (`400 Disallowed CORS origin`).
>    - Quindi la finestra dell'invito usa `fetch` nudo: `GET <indirizzo>/api/v1/auth/address-probe?nonce=…`, senza
>      header, `credentials: 'omit'`. Non il client Zodios, che aggiunge i suoi header.
> 2. **`derive_key("accounts.address-probe.v1")`: va bene.** Legge la chiave a ogni chiamata e la crea al primo uso.
>    Le due rotte sono già `def` sincrone, quindi FastAPI le esegue in un thread; in una rotta `async` servirebbe
>    `asyncio.to_thread`.
> 3. **Se la chiave d'istanza cambia** i nonce già emessi non valgono più. Per due minuti va bene.
> - `GET /auth/users/me/deletion-preview` (funzione `auth.preview_own_account_deletion`) va in `ALLOWED_WHEN_BLOCKED`
>   nel lotto di H. Chi entra per secondo aggiunge la riga.

#### A6.2 — Test rossi (`test-author`: P per la verifica dell'indirizzo, D per l'eliminazione, L per LIVE-002) ✅ (2026-10-15)
- **P, verifica dell'indirizzo** ✅. Due file nuovi, scritti senza eseguire nulla; i rossi li ho lanciati io.
  - `test_services/test_address_probe.py`: 53 casi, `pure`.
    - Il nonce, la scadenza `expiry >= now` (float) e ogni bit alterato.
    - Le scritture non canoniche: il decoder base64 di Python è permissivo, quindi la verifica deve ricodificare e
      confrontare.
    - Un'altra istanza, `hmac.compare_digest` come solo giudice, nessuna eccezione.
    - `derive_key` chiamato a ogni uso: le spie sostituiscono ogni nome del modulo legato alla funzione.
  - `test_api/test_address_probe_api.py`: 26 casi, write-scoped (il login scrive i contatori di `e2e_test_admin` e
    `e2e_test_user`).
    - 401, 403 e 200 per il nonce; `{match}` pubblico con `Access-Control-Allow-Origin: *` presente una volta sola e
      `no-store`.
    - Un `Origin` di fuori attraverso il `CORSMiddleware`; i cookie non contano; un'altra istanza in processo.
  - Registrati: `services address-probe` (dopo `session-version`) e `api address-probe` (dopo `session-revocation`).
  - **Rossi, per il motivo giusto**:
    - `services address-probe`: errore di raccolta, `cannot import name 'address_probe'`.
    - `db populate --force`, poi `api address-probe`: 26 falliti su 26.
      - `POST /users/address-probe` → 405: cade su `PATCH /users/{user_id}`.
      - `GET /auth/address-probe` → 404 HTML dal catch-all della SPA.
      - I due casi che coniano in processo: `ModuleNotFoundError`.
    - Log: `/tmp/libreFolio_a6a/logs/red_*.log`.
- **D, eliminazione** ⏳: anteprima, `DELETE /users/{id}`, `protected`, uguaglianza fra anteprima ed eliminazione reale.
- **L, LIVE-002** ✅. Solo `test_api/test_registration_api.py` (+19 / −3).
  - Nuovo `_assert_lane_has_an_account()`, letto nel DB della corsia *prima* della registrazione. Controlla
    l'esistenza (`select(User.id).limit(1)`), non il numero.
  - Lo usano LIVE-002 e anche LIVE-003, che su una corsia vuota creerebbe l'admin allo stesso modo. LIVE-001 no: un
    invito non valido viene rifiutato anche lì.
  - L'asserzione di LIVE-002 prende un messaggio, che nomina prima il ruolo dell'invito, poi la corsia vuota.
  - **Prova**, con la corsia svuotata dalla preparazione di `services`, poi `api registration` sui due casi:
    - 2 falliti col messaggio «Precondition: the lane has no account yet…»;
    - nel DB 0 utenti e 0 token: nessun admin creato.
  - Dopo `db populate --force`, gli stessi due: 2 passati.
  - Log: `/tmp/libreFolio_a6a/logs/live_*_lane.log`.
- **D, eliminazione** ✅. Tre file: il nuovo `test_services/test_account_deletion_preview.py` (15 casi, `pure`) e
  l'estensione di `test_api/test_users_admin_api.py` e `test_api/test_account_deletion_api.py`.
  - **Fuori pista (scelta del test-author, accettata)**: niente `create_all`, perché i modelli non dichiarano
    l'`ON DELETE CASCADE` di `broker_user_access` che `delete_user` usa. Al suo posto, un DB portato a head con le
    migrazioni vere, in un processo figlio, una volta per modulo (`_alembic_upgrade_head` di
    `test_db/test_autoincrement_schema.py`), poi copiato per ogni test. Lo stesso fa la fixture `private_head` dei casi
    in processo di `users-admin`.
  - La pulizia dei report BRIM è sempre spiata e la loro cartella è sotto `tmp_path`: gli id dei broker privati
    partono da 1, come quelli della corsia.
  - Registrato `services account-deletion-preview` (dopo `address-probe`).
  - **Rossi, per il motivo giusto**:
    - `services account-deletion-preview`: 15 falliti su 15 (funzioni, dataclass e aggancio mancanti).
    - `api users-admin`: 15 falliti, 49 passati. UADM-001 ×2 (404/405), i quattro casi col campo `protected`,
      UADM-040…043 sulla corsia, UADM-050…054 in processo.
    - `api account-deletion`: 2 falliti, 6 passati (ACCDEL-006/007: 404).
- **Rinumerazione IMG** (richiesta del coordinatore, 15/10 16:2x): in `test_utilities/test_dev_cli_image.py` i miei
  IMG-013…016 diventano IMG-027…030, suffissi compresi, perché la serie IMG è unica con `test_dev_cli_docker.py` di H
  (IMG-013…024) e B ha IMG-025/026. Solo docstring, intestazioni ed etichette: nessun nome di test conteneva l'id.
  - Prova: il file, con gli id normalizzati, è identico a HEAD; `utils dev-cli-image` 71 passati.
  - Il rimando storico in A5.2 qui sopra («IMG-013…016b») resta com'era: ora si chiamano IMG-027…030.

#### A6.3 — Implementazione di A6a ✅ (2026-10-15)
> - Applicata la bozza provata a secco (`/tmp/libreFolio_a6a/apply_a6a.py`), poi black e ruff sui 6 file: puliti.
>   - Nuovo `services/accounts/address_probe.py`.
>   - `user_service`: le quattro dataclass, `_count_unpaired_halves`, `preview_user_deletion`, `delete_account`,
>     `account_protection`.
>   - `schemas/users.py` e `schemas/auth.py`: `AdminUserRead.protected` e le forme di anteprima e sonda.
>   - `api/v1/users.py`: `POST /users/address-probe`, `GET /{id}/deletion-preview`, `DELETE /{id}`, il 409 sul PATCH.
>   - `api/v1/auth.py`: `GET /auth/users/me/deletion-preview`, `GET /auth/address-probe`; `delete_own_account` passa
>     da `user_service.delete_account`.
> - **Fuori pista — ordine dei rifiuti del DELETE**: rispetto ad A6.1, `ACCOUNT_PROTECTED` viene prima di
>   `DEMOTE_FIRST`. Per l'admin pagante di A7 «declassalo prima» sarebbe una strada chiusa, perché anche il
>   declassamento è rifiutato. Nessun test lo fissa oggi: lo fisseranno i test di A7. Nel PATCH `ACCOUNT_PROTECTED`
>   viene prima della regola dell'ultimo admin; promuovere o riattivare un account protetto non è rifiutato.
> - **Fuori pista — pulizia dei file dopo il commit**: in `delete_account` un errore della rimozione dei report viene
>   registrato nel log e non rovescia l'esito. Prima, nell'eliminazione del proprio account, diventava un 500 a
>   eliminazione già fatta.
> - **Fuori pista — difetto trovato da UADM-054** (verdetto: *defect*):
>   - Con un guasto tecnico `delete_user` fa rollback, e il rollback fa scadere ogni oggetto della sessione della
>     richiesta, compreso l'`admin` di `require_admin`, che condivide `get_session_generator`.
>   - L'`except` della rotta leggeva `admin.id` → `MissingGreenlet` al posto del 500 «nothing was deleted».
>   - **Cura**: `username` e `admin_id` letti prima dell'eliminazione. UADM-054 passa.
>   - La rotta del proprio account ha lo stesso difetto latente (`current_user.id` nell'`except`), e nessun test copre
>     quel ramo. Chiesto al test-author D un rosso, ACCDEL-008; la cura arriva dopo il rosso.

#### A6.4 — Test verdi ✅ (2026-10-15)
> Sequenza in serie con `nice -n 10` (`/tmp/libreFolio_a6a/greens.sh`; log `/tmp/libreFolio_a6a/logs/green_*.log`):
>
> | Azione | Esito |
> |---|---|
> | `services address-probe` | 53 passati |
> | `services account-deletion-preview` | 15 passati |
> | `services user-profile` | 36 passati |
> | `services config-package` | 641 passati |
> | `api address-probe` | 26 passati |
> | `api users-admin` | 63 passati, 1 fallito (UADM-054, il difetto qui sopra); dopo la cura, UADM-054 passa |
> | `api account-deletion` | 8 passati |
> | `api registration` | 65 passati (LIVE-002 compreso) |
> | `api auth` | 60 passati |
> | `api instance-block` | 42 passati, 2 falliti: **non di A6a** (vedi sotto) |
> | `api system` | 117 passati |
> | `utils dev-cli-image` | 71 passati (rinumerazione IMG) |
>
> - **I 2 rossi di `instance-block`** (`test_each_allowed_route_answers_a_signed_in_user`,
>   `test_the_allowed_routes_answer_anonymous_callers_as_usual`): confrontano `GET /system/instance` con
>   `{"profile": …}` e trovano anche `accounts`, il campo di A5. È il rosso già trovato da H nella verifica di C-96 e
>   riparato in `dev_release2` (`744f5a0ee`), che la mia base `46c159ebc` non ha ancora. A6a non tocca
>   `/system/instance`. Verdetto: *environment* (base); spariscono all'aggiornamento di base.
> - `lint --dead-code --scope backend`: nessun nuovo risultato da A6a; `derive_key` non compare più.
>   `count_superusers`, usato solo dai test, è di prima (`bfa85b0a8`).
> - `test check-orphans`: tutti i file registrati e raggiungibili da `all`.
> - `api sync`: pulito; le quattro rotte nuove sono in `openapi.json` (il client generato è ignorato da git).
>   `front check`: 0 errori, 0 avvisi. Nessun file tracciato cambiato oltre a quelli del lotto.
> - **ACCDEL-008** (test-author D, gemello di UADM-054 per `DELETE /auth/users/me`):
>   `TestTechnicalFailure::test_a_failure_part_way_answers_500_logs_it_and_deletes_nothing`.
>   - Il guasto colpisce a metà, dopo aver lasciato il broker condiviso di id più basso, nella stessa transazione.
>   - **Rosso, per il motivo previsto**: `MissingGreenlet` esce dall'handler al posto del 500, e manca l'evento
>     «Account deletion failed: nothing was deleted» (l'eccezione nasce mentre si costruiscono gli argomenti del log).
>   - **Cura**: `user_id` e `username` letti prima dell'eliminazione, come nella rotta dell'admin.
> - **Ripetizione sul codice finale**: `api account-deletion` 9 passati (ACCDEL-008 compreso), `api users-admin` 64
>   passati, `api auth` 60 passati. ruff e black puliti.

#### A6.5 — Doc per sviluppatori (`docs-writer`) ✅ (2026-10-15)
> - Tre pagine, senza traduzioni: `access_control.md`, `security.md`, `users_and_brokers.md`.
>   - `access_control.md`: le rotte nuove nella tabella dell'API admin e il campo `protected`. Due sezioni nuove:
>     `#admin-account-deletion` (ordine dei rifiuti, tutto o niente, log, istanza bloccata) e `#account-protection`
>     (l'aggancio di A7).
>   - `security.md`: la sezione `#address-probe`, con il modello di minaccia, il formato del nonce, la verifica, il
>     CORS su una sola rotta e la regola del preflight. Una riga per la sonda nella tabella delle rotte pubbliche e
>     in quella del blocco.
>   - `users_and_brokers.md`: `#account-deletion`, con la regola, l'aiuto unico, l'anteprima e `transfers_unpaired`.
> - **Correzioni del docs-writer al mio brief, verificate**:
>   - con l'istanza bloccata la sonda risponde 401 al chiamante senza sessione, cioè sempre (non 423), e senza
>     `Access-Control-Allow-Origin`: la UI la legge come «non verificabile»;
>   - Chrome ha sostituito il preflight di Private Network Access con un permesso per la rete locale: la pagina
>     cita entrambi.
> - **Per A6b**: con una chiave d'istanza inutilizzabile `POST /users/address-probe` risponde 500, documentato. La
>   finestra dell'invito deve leggere ogni errore della POST, come quelli della GET, come «non verificabile».
> - **Fuori pista — merge con W**: `6be11ecf3` di W, in `dev_release2`, trasforma la metà che resta di una coppia
>   con un broker eliminato (ADJUSTMENT, DEPOSIT o WITHDRAWAL; il ramo che dà di un TRANSFER perde solo il legame).
>   - Il paragrafo su `transfers_unpaired` l'ho scritto in modo che valga da entrambi i lati: rimanda a
>     `delete_by_broker()`.
>   - Il conteggio dell'anteprima resta giusto: sono proprio le metà che perdono il partner.
> - **Fuori dal mio perimetro, segnalato al coordinatore**:
>   - in `access_control.md`, «The last OWNER cannot remove themselves» contraddice «Self-Management», dove
>     l'ultimo OWNER che se ne va elimina il broker;
>   - la docstring di `instance_block.py` (H) elenca come esempi le rotte pubbliche fuori dall'elenco, e la sonda
>     non c'è.
> - **Prove**: `mkdocs build` (strict) pulito, anche dopo il ritocco del paragrafo; `mkdocs check-links`: 95 link
>   validi.

### Checkpoint A6a (backend) 🧊 (2026-10-15, ~17:50) — FROZEN, in attesa del commit del coordinatore
> - Base `46c159ebc`; nessun server attivo, la porta 6182 è libera; `git diff --check` pulito.
> - **Da fare al prossimo aggiornamento di base**:
>   - se H è già entrato, aggiungere `auth.preview_own_account_deletion` a `ALLOWED_WHEN_BLOCKED` e al suo test,
>     dichiarandolo. Insieme vanno aggiornati il punto «Blocked instance» di `access_control.md#admin-account-deletion`
>     e la tabella del blocco in `security.md`;
>   - `users_and_brokers.md#account-deletion`: aggiungere il dettaglio della trasformazione di W (V-3, D-J4);
>   - `security.md#address-probe`: un rimando a `#request-logs` di H. Il suo filtro non maschera `nonce`, che non è
>     una credenziale;
>   - i 2 rossi di `instance-block` devono sparire con il test riparato da H: da verificare.
> - **Committato dal coordinatore** (15/10, 16:56):
>   - `5928176cf` feat(accounts): admin deletion, deletion preview, address probe;
>   - `181096f6e` test(cli): renumber IMG-013..016 to IMG-027..030;
>   - `2545791a4` docs(journal): A6a plan, backlog A-14 A-15.

#### A6.6 — Aggiornamento di base (`4a74a9e7e`) e validazione della revisione combinata ✅ (2026-10-15)
> - Il coordinatore ha unito `dev_release2` (`d22eb6f43`), senza conflitti: HEAD `4a74a9e7e`, genitori `2545791a4` e
>   `d22eb6f43`. Dentro ci sono W (la conversione delle metà orfane), J e il resto. Mancano ancora la riga di H per
>   il blocco (il suo lotto piccolo è in `all-backend`) e la scheda Email di E (E2b non è partito).
> - **Validazione**, una prova alla volta con `nice -n 10` (`/tmp/libreFolio_a6a/combined.sh`; log in
>   `/tmp/libreFolio_a6a/logs/combined/`):
>
> | Azione | Esito |
> |---|---|
> | `services account-deletion-preview` | 15 passati |
> | `services config-package` | 643 passati |
> | `api instance-block` | 44 passati: spariti i 2 rossi di base (test riparato da H) |
> | `api system` | 117 passati |
> | `api account-deletion` | 9 passati (con l'ACCDEL-001 di W) |
> | `api users-admin` | 64 passati |
> | `api registration` | 65 passati (1 avviso: `HTTP_422_UNPROCESSABLE_ENTITY` di `api/v1/settings.py`, di prima) |
> | `api auth` | 60 passati |
> | `api address-probe` | 26 passati |
> | `check-orphans` | tutto registrato e raggiungibile |
> | `api sync` | pulito |
> | `front check` | 0 errori, 0 avvisi |
>
> - **`ALLOWED_WHEN_BLOCKED`**: sono entrato per primo, quindi la riga di `auth.preview_own_account_deletion` la
>   scrive H al suo ingresso. `api instance-block` non segnala rotte non classificate, quindi non la scrivo io.
> - **Doc riallineate alla base**:
>   - `users_and_brokers.md#account-deletion`: la trasformazione di W (V-3, D-J4) e un rimando a
>     `backend/transactions/service.md#broker-deletion`;
>   - `security.md#address-probe`: il nonce arriva nel log delle richieste, e il filtro di `#request-logs` (H) non
>     lo maschera, perché non è una credenziale.
>   - `mkdocs build` (strict) pulito; `check-links`: 95 link validi.
> - **Backlog**: in A-10, la sezione «Accounts and Sign-ups» di `admin/configuration` manca del tutto in IT, FR ed
>   ES (debito di A, confermato dal coordinatore). A-14 è passato a W, A-15 ad H.
> - `all-backend`: nella validazione di A6b, prima del suo ingresso (coordinatore).

### A6b — frontend di A6: scheda Utenti, eliminazione, verifica dell'indirizzo — consegnato (handoff d'ingresso, 15/10 sera)

#### A6b.0 — Via, base e vincoli ✅ (2026-10-15)
> - **A6a è entrato**: `dev_release2` = `1840ebd62` (merge di `5e21149e5`); CHANGELOG `ca4ec658e`.
> - **Via del coordinatore ad A6b** (15/10, 17:18). Base `5e21149e5`, già quella giusta.
> - **Colori**:
>   - `ProfileTab` e i componenti nuovi passano prima da A;
>   - classi colore solo con i ruoli `*-lf-*`;
>   - niente `--split` per i file nati da zero;
>   - il pulsante rosso è `bg-lf-danger text-lf-on-status`.
>   - La riga di `ProfileTab` nella baseline è ancora sul percorso vecchio
>     (`lib/components/settings/tabs/ProfileTab.svelte 180`): il gate accoppia i file spostati per nome.
> - **File di altri**:
>   - B ha messo la riga Backup in `settingsTabs.ts` e nel suo test (`adminOnly` nella riga di `TODAY`). Entra a breve:
>     all'aggiornamento di base tengo le due righe;
>   - E aggiungerà la riga Email.
> - **Prove pesanti**: `all-backend` ed E2E di A6b nello slot pesante, da chiedere al coordinatore.
> - **Ricognizione** (due `explore`, 15/10):
>   - non esistono un menu, una tabella, un aiuto per gli appunti o un costruttore di link riusabili: A6b ne fa di
>     piccoli, solo con i ruoli;
>   - `ModalBase` ha `trapFocus` opzionale;
>   - `ConfirmModal` non ha un campo da digitare;
>   - nessun file di `features/settings/` usa ancora i ruoli `lf-*`;
>   - il delete di `ProfileTab` è inline, senza `ModalBase` né focus trap;
>   - i suoi `data-testid` (`profile-delete-*`, `delete-account-button`) li usano
>     `e2e/brokers/account-deletion.spec.ts`, `e2e/settings.spec.ts` e `ProfileTab.test.ts`.

#### A6b.1 — Contratto ✅ (2026-10-15)
> **File nuovi** (solo ruoli `lf-*`, Svelte 5 runes):
> - `features/settings/tabs/UsersTab.svelte`: la scheda.
> - `features/settings/users/`:
>   - `UserRow.svelte`: la riga, con il pannello delle azioni che si apre e si chiude;
>   - `InvitationsList.svelte`;
>   - `InviteDialog.svelte`;
>   - `ResetLinkDialog.svelte`;
>   - `LinkShare.svelte`;
>   - `linkShare.ts`: puro;
>   - `addressProbe.ts`;
>   - `linkShareActions.ts`: il registro per E;
>   - `accountErrors.ts`.
> - `features/settings/AccountDeletionDialog.svelte`: condiviso da `ProfileTab` e dalla scheda Utenti.
>
> **Registro**:
> - `{id:'users', labelKey:'settings.users', icon: Users, order: 110, component: UsersTab, visible: (ctx) =>
>   ctx.isSuperuser}`.
> - Sta dopo `admin` (100, `alignEnd`), nel gruppo di destra delle schede da amministratore. Va controllato che
>   l'ordine non coincida con quelli di B ed E.
> - `TODAY` del test riceve la riga.
>
> **La scheda** (`users-tab`, con `data-busy` e `aria-busy`): carica `GET /users` e `GET /users/invites` in
> parallelo, e ricarica dopo ogni azione.
> - **Uso**: `users-usage` con `data-used` e `data-max` (vuoto senza limite). Testo «N / max», oppure «N account» senza
>   limite.
>   - «Gestisci abbonamento» (`users-billing-link`, esterno, `rel="noopener noreferrer"`) solo con `usage.billing_url`.
> - **Limite raggiunto** (`max_users` impostato e `used >= max_users`): banner `users-limit-banner`, con il link
>   all'abbonamento se c'è. Il pulsante «Invita» è spento con `data-disabled-reason="limit"`.
> - **Registrazione chiusa** (`instanceConfig.config.accounts.registration_mode === 'disabled'`): «Invita» spento con
>   `data-disabled-reason="registration-disabled"` e il suggerimento `users-invite-blocked`:
>   - se la modalità viene da `LIBREFOLIO_REGISTRATION`, la nomina;
>   - altrimenti rimanda alla scheda Impostazioni globali.
> - **Account** (`users-accounts`): una riga `users-row` per account, con `data-user-id`, `data-username`,
>   `data-active`, `data-admin`, `data-protected` e `data-self` (`"true"`/`"false"`).
>   - Mostra nome utente, email, badge Admin e Disattivato, data di creazione.
>   - `users-row-toggle` (`aria-expanded`) apre il pannello delle azioni.
>   - Riga propria: niente azioni, il suggerimento `users-self-hint` e un link a `?tab=profile`.
> - **Azioni** (pulsanti con `disabled` e `data-disabled-reason`; i motivi, in ordine: `protected`, `last-admin`,
>   `limit`, `demote-first`):
>
>   | Azione | Quando | Cosa fa |
>   |---|---|---|
>   | `users-action-deactivate` | attivo | conferma, poi `PATCH {is_active:false}` |
>   | `users-action-reactivate` | inattivo | `PATCH {is_active:true}`; spenta con `limit` quando l'istanza è piena |
>   | `users-action-promote` | non admin | conferma, poi `PATCH {is_superuser:true}` |
>   | `users-action-demote` | admin | conferma, poi `PATCH {is_superuser:false}` |
>   | `users-action-reset-link` | sempre | apre `ResetLinkDialog` |
>   | `users-action-sign-out` | sempre | conferma, poi `POST /users/{id}/sessions/revoke` |
>   | `users-action-restart-guides` | sempre | conferma, poi `POST /users/{id}/onboarding/reset` con corpo `null` (tutti i flussi) |
>   | `users-action-delete` | non admin | apre `AccountDeletionDialog` in modo admin; per un admin è spenta con `demote-first` |
>
>   - `last-admin`: disattivare o declassare l'unico admin attivo della lista. Il backend resta l'autorità (409
>     `LAST_ADMIN`).
>   - `protected`: `row.protected`, che spegne disattiva, declassa ed elimina.
>   - Le conferme usano `ConfirmModal` (`users-confirm`).
> - **Inviti** (`users-invites`): riga `users-invite-row` con `data-invite-id`, `data-email` e `data-admin`. Mostra
>   email (o «—»), ruolo, creazione e scadenza; la revoca è `users-invite-revoke`, con conferma.
>
> **Finestra dell'invito** (`users-invite-dialog`, `ModalBase` con `trapFocus`):
> 1. **Modulo**: `users-invite-email` (facoltativo), `users-invite-admin` (`grants_admin`), `users-invite-create`,
>    `users-invite-cancel`.
>    - Gli errori `REGISTRATION_DISABLED` e `USER_LIMIT_REACHED` compaiono inline in `users-invite-error`, con
>      `data-error-code`.
> 2. **Link**: `LinkShare` con `purpose="invite"` e scadenza «7 giorni»; si chiude con `users-invite-done`, che
>    ricarica la lista.
>
> **Finestra del reset** (`users-reset-dialog`): conferma («i link di prima smettono di funzionare»), poi
> `users-reset-create` → `LinkShare` con `purpose="password_reset"` (30 minuti), poi `users-reset-close`.
>
> **`LinkShare`** (`link-share`, `data-purpose`): props `purpose`, `path`, `url` (o null), `expiresAt` e `context`
> (`{username?, email?, userId?}`).
> - **Base precompilata**: se `url` finisce con `path`, la parte che precede; altrimenti `window.location.origin`. È
>   il prefill di D-A3: `LIBREFOLIO_PUBLIC_URL` quando c'è, altrimenti l'indirizzo del browser.
> - `link-share-address` è modificabile; il link (`link-share-link`, in sola lettura) è la base normalizzata più
>   `path`.
> - **Verifica** solo se la base normalizzata è diversa da quella precompilata, dopo 500 ms senza digitare.
>   - Stato in `link-share-probe` con `data-state`: `idle`, `checking`, `match`, `mismatch`, `unverifiable` o
>     `invalid`.
>   - Tornare alla base precompilata riporta a `idle`. Un indirizzo non http(s) dà `invalid` e spegne la copia.
>   - Negli altri stati il link si copia sempre (decisione D-A3).
> - **Copia** (`link-share-copy`): `navigator.clipboard`; se non è disponibile, il testo resta selezionato nel campo.
>   Toast ed evento `accounts.link.copied` con `{purpose}`.
> - **Registro per E** (`linkShareActions.ts`):
>   - `LINK_SHARE_ACTIONS: LinkShareAction[]`, vuoto oggi, con `{id, component, visible?(ctx)}`;
>   - `LinkShare` mostra in `link-share-actions` ogni azione visibile, con le props `{link, purpose, context}`;
>   - E aggiunge «Spedisci per email» con una riga.
>
> **`addressProbe.ts`**:
> - `normalizeBase(input)`: toglie gli spazi; solo URL `http`/`https` senza query né fragment; toglie le barre finali e
>   tiene un eventuale prefisso di percorso. Restituisce `null` se non è valido.
> - `probeUrl(base, nonce)` → `${base}/api/v1/auth/address-probe?nonce=${encodeURIComponent(nonce)}`.
> - `checkAddress(base, {issueNonce, fetchImpl = fetch, timeoutMs = 8000})`, che restituisce `match`, `mismatch` o
>   `unverifiable`:
>   - prende il nonce con `POST /users/address-probe` dal client Zodios: un errore dà `unverifiable`;
>   - poi `fetchImpl(probeUrl, {method:'GET', credentials:'omit', cache:'no-store', referrerPolicy:'no-referrer',
>     signal})`, **senza `headers`**: è una richiesta CORS semplice, perché un preflight lo rifiuterebbe il
>     `CORSMiddleware` (H);
>   - `ok` con `match === true` → `match`; `ok` con `match === false` → `mismatch`; tutto il resto → `unverifiable`
>     (errore di rete o CORS, stato non 200, JSON non valido, timeout, contenuto misto, permesso di rete locale).
>
> **`AccountDeletionDialog`** (`ModalBase` con `trapFocus`):
> - Props: `open`, `mode: 'self' | 'admin'`, `account {id, username, is_active}`, `testIdPrefix` (`profile-delete` o
>   `users-delete`), `onClose`, `onDeleted(result)`, `onDeactivate?` (solo admin).
> - **All'apertura** carica l'anteprima: `GET /auth/users/me/deletion-preview` per sé, `GET /users/{id}/deletion-preview`
>   per l'admin. `${p}-dialog` porta `data-busy`.
> - **In modo admin, con l'account attivo**, la prima scelta è «Disattiva invece» (`${p}-deactivate`): tiene tutto e
>   si annulla. Poi l'eliminazione.
> - **Anteprima** (`${p}-preview`):
>   - `${p}-broker-deleted`, con `data-broker-id` e `data-transactions`: i broker che spariscono con le loro
>     transazioni;
>   - `${p}-broker-left`, con `data-broker-id` e `data-role`: i broker da cui sparisce solo l'accesso;
>   - `${p}-unpaired`, con `data-count`, quando `transfers_unpaired > 0`: la frase V-3, provvisoria e concordata con
>     W.
> - **Conferma** col nome utente: `${p}-confirm-input` sblocca `${p}-confirm`, rosso, `bg-lf-danger
>   text-lf-on-status`. `${p}-cancel` annulla; `${p}-error` porta `data-error-code`.
> - **In `ProfileTab`** sostituisce il dialogo inline, con gli stessi `data-testid` (`profile-delete-dialog`,
>   `-confirm-input`, `-cancel`, `-confirm`; il pulsante `delete-account-button` resta). L'esito resta quello di oggi:
>   `auth.logout()` e `goto('/')`.
>
> **Errori** (`accountErrors.ts`: `detail.error_code` → chiave i18n):
> - i codici: `LAST_ADMIN`, `USER_LIMIT_REACHED` (con `billing_url` se c'è), `REGISTRATION_DISABLED`,
>   `ACCOUNT_PROTECTED`, `SELF_DELETION`, `DEMOTE_FIRST`;
> - 404: l'account non c'è più, e la lista si ricarica;
> - 500 dell'eliminazione: «non è stato eliminato niente»;
> - altrimenti un messaggio generico;
> - sempre un toast d'errore ed `accounts.action.failed` con `{action, code}`.
>
> **Eventi** (`notify`, `area.thing.past-tense`):
> - con toast: `accounts.user.sessions-revoked`, `accounts.user.onboarding-reset`, `accounts.user.deleted` (con
>   `brokers_deleted`), `accounts.reset-link.created`, `accounts.link.copied`;
> - senza toast: `accounts.user.deactivated`, `reactivated`, `promoted`, `demoted`, `accounts.invite.created`,
>   `accounts.invite.revoked`, `accounts.address.checked` (con `{state}`).
>
> **i18n** (sorgenti in `lib/i18n/settings/`, EN, IT, FR ed ES): `settings.users` (l'etichetta della scheda),
> `settings.usersTab.*`, `settings.linkShare.*` e `settings.accountDeletion.*`. Per sé restano le chiavi
> `settings.deleteAccount*` di oggi.
>
> **Prove** (rossi dai `test-author`, li lancio io):
> - **V1, Vitest puri** (`core-unit`): `linkShare.test.ts`, `addressProbe.test.ts`, e la riga Utenti in
>   `settingsTabs.test.ts`.
> - **V2, Vitest di componente** (`component-unit`): `LinkShare`, `InviteDialog`, `UsersTab`,
>   `AccountDeletionDialog`, e `ProfileTab.test.ts` adattato.
> - **E1, E2E** `e2e/settings/admin-users.spec.ts` (`front-utility admin-users`), da `e2e_test_admin` su account usa e
>   getta:
>   - disattiva e riattiva, promuovi e declassa;
>   - link di reset;
>   - invito creato e revocato;
>   - verifica dell'indirizzo sull'origine alternativa della corsia (`localhost` contro `127.0.0.1`: `match`, il vero
>     percorso CORS) e su una porta chiusa (`unverifiable`);
>   - eliminazione con anteprima e conferma digitata.
> - **E2, A-12**: i selettori di `e2e/settings.spec.ts`.
>
> **Doc** (`docs-writer`, solo EN):
> - una pagina admin «Utenti», nuova con una riga di nav da dichiarare, oppure una sezione di `admin/settings`;
> - la sezione «Delete Account» di `user/settings/profile`;
> - `admin/cli_tools`, che rimanda alla scheda;
> - per gli sviluppatori, `frontend/components/features/settings.md`, con il titolo di A-7.
>
> **Galleria**: uno scatto della scheda Utenti con dati finti (`page.route` su `/users` e `/users/invites`), nel file
> di G: da concordare.
>
> **Fuori da A6b**: la scheda Sicurezza (A8), le regole della password (A6c), F02 (A7), le traduzioni della doc
> (A-10).
>
> **Risposte del coordinatore** (15/10, ~17:40):
> 1. **Ordine delle schede**: Users 110 va bene; Backup di B = 120 (già nel suo ramo); Email di E = 130. Al merge si
>    tengono tutte le righe.
> 2. **Doc**: una pagina nuova, `admin/users.en.md`, perché è una funzione centrale per chi amministra un'istanza nel
>    cloud. La riga nella nav di `mkdocs.yml` e quella di `nav_translations` le scrivo io e le dichiaro all'handoff.
>    Anche E2b aggiunge una riga di nav: si tengono entrambe.
> 3. **Galleria**: `gallery.spec.ts` è dei colori. Il coordinatore lo chiede al loro coordinatore, insieme allo scatto
>    Backup di B. Intanto non lo tocco.
> 4. **Frase V-3**: girata a W, che la corregge.
> 5. **Aggancio `linkShareActions.ts`**: girato a E così com'è.
> 6. **Runner**: solo righe in aggiunta, dichiarate.

#### A6b.2 — Test rossi (sei `test-author` in parallelo, solo scrittura) e bozza dell'implementazione ✅ (2026-10-15)
> - Il contratto, in inglese per i `test-author`, è nel file di sessione `a6b_contract_en.md`: è la stessa cosa di
>   A6b.1.
> - **Gli autori**:
>   - V1, Vitest puri: `linkShare`, `addressProbe` e la riga in `settingsTabs`;
>   - V2: `LinkShare`, `InviteDialog`, `ResetLinkDialog`;
>   - V3: `UsersTab`;
>   - V4: `AccountDeletionDialog` e `ProfileTab.test`;
>   - E1: E2E `settings/admin-users.spec.ts`;
>   - E2: A-12 in `settings.spec.ts` e `SettingControls.test.ts`.
> - **E2 (A-12)** ✅:
>   - `settings.spec.ts` (+63/−27): `beforeEach` su `data-busy`; sblocco via `settings-lock-toggle`; righe per chiave
>     (`global-setting-session_ttl_hours` + `spinbutton`); `setting-save` e `setting-undo` nella riga; prova della sola
>     lettura per il non admin.
>   - `SettingControls.test.ts` (+29): il segnaposto «Coming soon» (`disabled` con `badge`) e un controllo normale.
>   - Serve un aggancio nel prodotto: `data-testid="settings-readonly-indicator"` sul segno di sola lettura di
>     `GlobalSettingsTab`. Senza, i due test «non admin» restano rossi.
> - **Bozza dell'implementazione** in `/tmp/libreFolio_a6b/`: 12 file nuovi, `apply_a6b.py` per `ProfileTab`,
>   `settingsTabs.ts` e `GlobalSettingsTab` (l'aggancio di E2), `a6b_i18n.py` per 107 chiavi in ciascuna delle 4 lingue.
>   - Prova a secco su una copia `git archive` (`dry_run.sh`): si applica pulita; build del catalogo,
>     `svelte-kit sync`, `svelte-check` 0 errori e 0 avvisi; colori `theme-roles --check` puliti (`ProfileTab` sotto il
>     suo record); prettier pulito.
> - **Rapporti degli autori** (tutti in ordine, nessun test eseguito da loro tranne prettier):
>   - V1: `linkShare.test.ts` (25), `addressProbe.test.ts` (64), `settingsTabs.test.ts` (+60/−16; `UsersTab` mockato
>     come gli altri, riga `adminOnly`).
>   - V2: `users/LinkShare.component.test.ts` (22), `InviteDialog.test.ts` (10), `ResetLinkDialog.test.ts` (8).
>     **Fuori pista**: il nome `LinkShare.component.test.ts`, perché il disco non distingue le maiuscole e
>     `LinkShare.test.ts` coinciderebbe con `linkShare.test.ts`.
>   - V3: `tabs/UsersTab.test.ts` (54 casi, con un piccolo server finto dietro l'API).
>   - V4: `AccountDeletionDialog.test.ts` (49) e `ProfileTab.test.ts` (9 casi sulla cancellazione).
>   - E1: `e2e/settings/admin-users.spec.ts` (10 casi, AUSR-E-01…10).
> - **Correzioni della bozza** dai rapporti:
>   - `LinkShare` copia con `writeTextToClipboard`, perché `clipboardSink.gate.test.ts` lo impone;
>   - il debounce riparte a ogni tasto;
>   - `data-expires-at` su `link-share-expires`.
> - **Fuori pista — regressione evitata** (segnalata da V4): l'unico admin che elimina il proprio account riceve 400
>   con una frase e senza `error_code`. Il vecchio dialogo la mostrava; con la mappa dei codici sarebbe diventata un
>   errore generico. `accountErrors.ts` ora mostra la frase del server per un 400/409 senza codice
>   (`accountErrorText`). Il codice vero è una voce nuova del backlog (A-16).
> - **Rossi** (Vitest, 10 file, `--maxWorkers 2`, prima dell'implementazione), per il motivo giusto:
>   - 7 file falliscono all'import, perché i moduli non esistono;
>   - `settingsTabs`: 5 falliti e 14 passati (manca la riga `users`);
>   - `ProfileTab`: 8 falliti (l'anteprima non viene chiesta) e 48 passati;
>   - `SettingControls` verde (copertura, non un rosso).
>   - **Non lanciati**: i rossi E2E (`admin-users`, `settings`). La scheda non esiste, quindi falliscono per forza;
>     le E2E vanno nello slot pesante del coordinatore.
> - **Registrazioni nel runner** (`_frontend_utility.py`, solo righe in aggiunta):
>   - `core-unit`: +2 file;
>   - `component-unit`: +5 file;
>   - `front_admin_users` + `add_test(..., "admin-users", ...)`.

#### A6b.3 — Implementazione ✅ (2026-10-15)
> - `apply_a6b.py`: 12 file nuovi; `ProfileTab` (`AccountDeletionDialog` al posto del dialogo inline, −69 righe);
>   `settingsTabs.ts` (riga `users`, 110); `GlobalSettingsTab` (`data-testid="settings-readonly-indicator"`).
> - `a6b_i18n.py`: 107 chiavi in EN, IT, FR ed ES. `settings.deleteAccountFailed`, rimasta senza uso, è stata tolta
>   con `dev.py i18n remove`.
> - **Fuori pista**: `src/routes/(app)/settings/page.tabs.test.ts` usa il registro vero e rende inerti i corpi delle
>   schede. Senza il suo `vi.mock` per `UsersTab.svelte`, caricava la scheda vera e non trovava `DEFAULT_LOCALE` nel
>   mock di i18n. Ho aggiunto una riga, sul modello delle altre (B farà lo stesso per Backup) e corretto il commento
>   («the four» → «the»). Ora 18 passati.
> - `mkdocs.yml`: «Users & Invitations: admin/users.md» sotto «⚙️ System Configuration», più le tre righe di
>   `nav_translations`. Da dichiarare all'handoff.

#### A6b.4 — Prove leggere ✅ (2026-10-15)
> - Vitest sui 10 file: **394 passati**, al primo colpo.
> - Gate Vitest: `clipboardSink`, `htmlInterpolation`, `htmlSink`, `themeRoles`, `themeTokens`,
>   `themeComponentTokens`, `themeModeReads` e `flagFont` verdi; `page.tabs` verde dopo il mock.
> - `theme-roles.mjs --check` pulito. Prettier pulito su `features/settings` e `i18n/settings`.
> - `i18n check` pulito (4529 chiavi, strict). `i18n audit`: nessuna traduzione mancante; l'unica chiave senza uso
>   era `deleteAccountFailed`, ora tolta.
> - knip (`lint --dead-code --scope frontend`): niente nei file di A6b; i risultati sono di prima.
> - `front check` (svelte-check): 18 errori di tipo, tutti in `AccountDeletionDialog.test.ts` (i mock di V4), verde a
>   runtime. Richiesta a V4 la sola correzione dei tipi.
> - V4 ha corretto i tipi (`ReturnType<typeof vi.fn>` ovunque, 4 righe): **`front check` 0 errori, 0 avvisi**;
>   `AccountDeletionDialog.test.ts` 49 passati.
> - Chiesto lo slot pesante (15/10, ~18:3x): `all-backend`; `front-utility core-unit` e `component-unit`; le E2E una
>   alla volta con `--workers 2`: `admin-users`, `settings`, `front-user account-deletion`, `auth`, `auth-links`,
>   `app-start-auth`, `theme-roles`.
> - **Frase V-3 definitiva di W** (via coordinatore, 15/10 18:15): EN e IT di W, FR ed ES tradotte da me, in
>   `settings.accountDeletion.unpaired`, con i plurali ICU.
>   - Prova con `intl-messageformat`, `count` 1 e 3, nelle 4 lingue: si formatta (anche con gli apostrofi francesi e
>     italiani). `i18n check` strict: 4528 chiavi.
>   - Nota di W: con la decisione 47 anche le metà in uscita diventeranno rettifiche, in un lotto di J e W più avanti;
>     allora W aggiorna la frase.
>   - **Fuori pista**: l'app in italiano dice «transazioni» (122 volte) e non «movimenti». Le mie 5 stringhe IT
>     (`deactivate.message`, `warningAdmin`, `deactivateText`, `brokersDeleted`, `transactions`) sono allineate.
> - **Scatto della galleria `settings/users`**: le regole e la checklist di G sono nel file di sessione del
>   coordinatore (`gallery-shot-rules.md`). Lo scrive un `test-author` (`gallery.spec.ts`, solo aggiunte):
>   - dati fissi via `page.route` (GET `/users` e `/users/invites`), corpi validati con `schemas.*.parse`;
>   - l'id vero dell'admin da `/auth/me`, per il badge «Tu»; una riga aperta;
>   - desktop con `extendScreenToBlock`.
>   - Date assolute, quindi l'orologio non serve. Le catture A/B e il diff vanno nello slot della galleria (in coda
>     dopo L, T-8b e DV).
> - **Slot pesante 2, mio** (coordinatore, 15/10 ~18:25). Sequenza in `/tmp/libreFolio_a6b/slot.sh`, log in
>   `/tmp/libreFolio_a6b/logs/slot/`, tutto con `nice -n 10`:
>   1. `all-backend`;
>   2. `front-utility core-unit`, poi `component-unit`;
>   3. `db populate --force`;
>   4. le E2E con `--workers 2`, una alla volta: `admin-users`, `settings`, `front-user account-deletion`, `auth`,
>      `auth-links`, `app-start-auth`, `theme-roles`.
> - **Risposta a E** (Email, decisione 45, 15/10 18:20): riusa `users/addressProbe.ts` così com'è.
>   - `normalizeBase` + `checkAddress` (`match | mismatch | unverifiable`), con il nonce passato da fuori.
>   - Il contenuto misto lo controlla E prima della chiamata; un `signal` facoltativo lo può aggiungere E, in aggiunta e
>     dichiarato.
>   - `LIBREFOLIO_PUBLIC_URL` il browser non lo legge: viene da `url` nelle risposte dei link. Per la scheda Email la
>     fonte è il suo `/email/status`, oppure un campo in `/system/instance` (H), se lo decide il coordinatore.

#### A6b.5 — Doc (`docs-writer`, EN) e scatto della galleria ✅ (2026-10-15; il doppio lancio dello scatto è di G-13)
> - **Galleria** (`test-author`): `gallery.spec.ts` +63/−0. L'import di `schemas` (L138) e il test
>   `'users - all languages and themes'` (L2121–2181) dopo `profile tab`: 16 scatti `{desktop,mobile}/{en,it,fr,es}/
>   {light,dark}/settings/users`.
>   - Corpi fissi validati con `schemas.*.parse`.
>   - Rotte con un predicato sul `pathname`, solo GET, il resto `fallback()`.
>   - L'id vero dell'admin da `/auth/me` (sola lettura).
>   - In più: il conteggio delle righe finte (4 account e 2 inviti), che prova che la foto mostra il mock e non la
>     corsia; la riga di `marco` chiusa prima del clic, aperta dopo.
>   - Mobile da verificare alle catture: se il clic sposta lo scroll, serve `frameTarget`.
>   - Ora locale: le date sono assolute, quindi due catture sulla stessa macchina coincidono.
> - **Doc, prima passata** (6 file):
>   - nuovo `admin/users.en.md` (`#open-the-tab`, `#places`, `#accounts`, `#actions`, `#action-off`, `#invitations`,
>     `#open-invitations`, `#reset-links`, `#server-address`, `#delete`);
>   - `user/settings/profile.en.md` «Delete Account»;
>   - `admin/cli_tools.en.md`;
>   - `admin/settings.en.md`;
>   - dev `frontend/components/features/settings.md`, con A-7: titolo «🌍 GlobalSettingsTab (read by everyone, edited
>     by administrators)» e ancora esplicita `#globalsettingstab-admin-only` per i link vecchi;
>   - `security.md#address-probe` («In the app»).
>   - Scelta giusta del docs-writer: nessun link verso ancore che esistono solo in inglese (A-10), perché la pagina
>     nuova senza traduzioni farebbe fallire il build strict nelle altre lingue.
>   - Protezione: oggi `account_protection` restituisce `None` ovunque; la pagina dice che «Protected» è riservato
>     all'admin pagante (A7).
> - **Doc, seconda passata** (in corso), per la deriva trovata: `admin/configuration.en.md` (righe `BILLING_URL` e
>   `PUBLIC_URL`), `user/settings/index.en.md` e `developer/frontend/pages/index.md` («four tabs»), `admin/index.en.md`,
>   `test-walkthrough/front-utility.md` (`admin-users`), `components/index.md`.
> - **Doc, seconda passata** ✅ (6 file):
>   - `admin/configuration.en.md`: righe `PUBLIC_URL` e `BILLING_URL`, più la riga `PUBLIC_URL` della tabella dei
>     valori sbagliati;
>   - `user/settings/index.en.md`: cinque schede, Utenti solo per gli admin;
>   - `developer/frontend/pages/index.md`: 5 schede, `UsersTab`, `ProfileTab` corretto;
>   - `admin/index.en.md`: la pagina nuova e la frase d'introduzione;
>   - `test-walkthrough/front-utility.md`: `#admin-users`, 10 casi;
>   - `components/index.md`.
>   - Il docs-writer ha controllato in sola lettura 229 link e ancore: tutti si risolvono.
> - Le descrizioni del runner (`core-unit`, `component-unit`) ora nominano la scheda Utenti e i suoi moduli:
>   cambiano solo le stringhe `desc`.
> - **Debito di traduzione** (A-10, nessun timbro): `admin/users` è nuova; sono cambiate le sezioni di `profile`,
>   `cli_tools`, `settings`, `configuration` (la cui sezione Accounts manca già in IT, FR ed ES), `admin/index` e
>   `user/settings/index`.

#### A6b.6 — Slot pesante 2: validazione di A6a + A6b ✅ (2026-10-15, 18:22–19:45)
> Base `5e21149e5` (= A6a entrato), nella corsia 6182, con `nice -n 10`; log in `/tmp/libreFolio_a6b/logs/slot/`.
>
> | Prova | Esito |
> |---|---|
> | `all-backend` | ✅ 7/7 categorie (external, db, services, utils, schema, api, e2e), 51 min 50 s |
> | `front-utility core-unit` | prima ❌ 1 su 4728 (vedi sotto); dopo la cura ✅ 4728 su 152 file |
> | `front-utility component-unit` | ✅ 3561 su 134 file |
> | `db populate --force` | ✅ |
> | E2E `admin-users` (`--workers 2`) | ✅ 10 (52 s) |
> | E2E `settings` | ✅ 46 (A-12 compreso) |
> | E2E `front-user account-deletion` | ✅ 1 (i `profile-delete-*` di `ProfileTab` tengono) |
> | E2E `auth`, `auth-links`, `app-start-auth`, `theme-roles` | ✅ 33, 9, 3, 8 |
>
> - **Fuori pista — difetto trovato da `catalogIcuLocale.test.ts`** (verdetto: *defect*, mio):
>   - `settings.accountDeletion.transactions` era identico in EN e FR. svelte-i18n compila un messaggio una volta sola,
>     con la lingua di chi lo chiede per primo, e il francese avrebbe preso le regole plurali inglesi (in francese lo
>     0 è singolare).
>   - **Cura**: un caso `=0` diverso in ogni lingua («no transactions», «nessuna transazione», «aucune transaction»,
>     «ninguna transacción»).
>   - I gate i18n (`src/lib/i18n`, 3 file, 30 test) sono verdi; poi `core-unit` intero verde.
>   - **Lezione**: dopo un cambio di testi ICU, lanciare `vitest run src/lib/i18n`, perché `i18n check` non vede questo
>     caso.
> - Avviso di ambiente nelle E2E: il build non scarica MathJax dal CDN (`CERTIFICATE_VERIFY_FAILED`). Non è di A6b.
> - **Dopo lo slot**: `mkdocs build` strict ✅; `check-links` 95 ✅; `tsc -p tsconfig.e2e.json` ✅ con i soli 2 errori di
>   base (`e2e/onboarding-tour.spec.ts:863`, `src/lib/types/files.ts:9`).
> - **Galleria**: le catture A/B di `settings/users` (desktop e mobile), il diff, `live_price_check` e i controlli i18n
>   negli scatti restano allo slot della galleria (in coda).
> - Backlog: A-7 (titolo del dev `settings.md`) e A-12 chiuse; A-10 con le pagine di A6b; A-16 nuova.

### Checkpoint A6b (frontend) 🧊 (2026-10-15, ~19:50) — FROZEN, in attesa del commit del coordinatore
> - Base `5e21149e5`; 28 file tracciati modificati, 21 nuovi; `git diff --check` pulito; la porta 6182 è libera.
> - **Ancora aperto**: lo slot della galleria (catture e diff di `settings/users`); dopo, la revisione di G in sola
>   lettura.
> - **Committato dal coordinatore** (15/10, sera): `3706a7e19` feat, `1577663c1` test, `38cb2c513` docs, `c576a0499`
>   gallery, `0b8bb863e` journal. Lo scatto `settings/users` passa a G per la revisione; il doppio lancio lo fa G-13.

#### A6b.7 — Aggiornamento di base (`f242cd6f4`): B, E2, J CP-4, Z6b, W E1b e N2, Y2, L ✅ (2026-10-15)
> - Il coordinatore ha aperto il merge di `dev_release2` (`00aa2ab3c`): 6 conflitti, tutti risolti tenendo i due lati.
>   Ho messo in stage solo quei file; il commit del merge è suo, `f242cd6f4`.
>   1. `settingsTabs.ts`: un solo import lucide; gli import di `UsersTab`, `BackupTab` ed `EmailSettingsTab`; le righe
>      users 110, backup 120, email 130.
>   2. `settingsTabs.test.ts`: tenuto il disegno di E, `CONTEXTS` per contesto, con `users` nella lista
>      dell'amministratore; tolti il mio `adminOnly` e `todayFor`.
>      - In `TODAY`, `bodies` e `vi.mock` ci sono le tre schede; STAB-01/02 e i casi di backup ed email restano.
>      - Le intestazioni sono unite.
>   3. `page.tabs.test.ts`: i tre `vi.mock`.
>   4. `_frontend_utility.py`: la lista con le mie 4 righe e `EmailSettingsTab.test.ts`. Le due `desc` le ho ricomposte
>      dall'antenato comune, con le aggiunte di E e poi le mie; il registro dice «users (order 110), backup and email for
>      administrators only».
>   5. `admin/configuration.en.md`: `PUBLIC_URL` è mia. In `BILLING_URL`, **Manage subscription** compare nella scheda
>      Utenti e nella pagina di blocco di H. Nessuna riga doppia nuova: i doppioni ci sono già in entrambi i genitori,
>      perché la variabile sta sia nella tabella delle variabili sia in quella dei valori sbagliati.
>   6. Dev `settings.md`: **sette** schede (il coordinatore aveva scritto sei, poi l'ha confermato) e i tre ordini nel
>      punto `alignEnd`.
> - **Fuori pista — il caso di B riadattato**: «backup comes **right** after admin» (`ids[adminAt + 1]`) con users a 110
>   in mezzo sarebbe rosso. Ora dice «backup comes after admin, in the right-hand group» (`indexOf('backup') > adminAt`).
>   L'ordine esatto resta fissato dal caso `CONTEXTS`. Il coordinatore approva: è la correzione di significato giusta.
> - Prova prima dello stage: Vitest `settingsTabs` e `page.tabs` 41 ✅, prettier pulito, le due righe di nav (Email di
>   E2b, Users) in `mkdocs.yml`.
> - **Validazione della revisione combinata** (in corso, `/tmp/libreFolio_a6b/merge_validation.sh`): `api sync`,
>   `front check`, Vitest (`settingsTabs`, `page.tabs`, `ProfileTab`, `UsersTab`), `db populate`, E2E `admin-users` e
>   `settings`, `mkdocs build`, `check-orphans`. `core-unit` va nello slot 1, dopo J.

#### A6b.8 — Slot pesante 1: `core-unit` della revisione combinata e handoff d'ingresso ✅ (2026-10-15, 20:25–20:35)
> - HEAD `e66334205` (A6b `3706a7e19`…`0b8bb863e`, merge `f242cd6f4`, journal `97fb199f1`, commento della galleria
>   `0cf135997`, journal `e66334205`), worktree pulito. Lo slot 1 me l'ha dato il coordinatore alle 20:25.
> - `nice -n 10 … dev.py test --test-port 6182 --data-dir /tmp/librefolio-r13-a front-utility core-unit`:
>   ✅ **5139 su 157 file**, 1 min 32 s (log `/tmp/libreFolio_a6b/logs/entry/core_unit.log`). Il rosso noto di
>   `htmlInterpolation.gate.test.ts` non compare: nella mia base la chiave `email.problems.SMTP_FROM_INVALID` è già
>   quella corretta da E2 («angle brackets», senza `<`), e il gate è nel giro e passa.
> - Previsione d'ingresso, in sola lettura: `git merge-tree --write-tree dev_release2 (b4597efad) HEAD` → **nessun
>   conflitto** (albero `d59a9d0c8`). Due file toccati dai due lati, uniti da soli e riletti:
>   - `security.md`: H (CP2b) a L320 e L697 (i riferimenti a `main.py` → `services/platform/`), io a L627 (il
>     paragrafo «In the app»); l'ancora `#address-probe-cors` del mio rimando resta;
>   - `BACKLOG_POST_1.2.md`: sezioni diverse.
>   - Dopo `00aa2ab3c` il mio ramo non tocca file del backend: le patch di H su `test_post_migration.py` non lo toccano.
> - Porta 6182 libera (`lsof` vuoto). Artefatti ignorati: `.testLog/` (con `00_archive/test-db_20261015_202730.tar.xz`
>   dello snapshot del runner).
> - Handoff d'ingresso mandato; stato **FROZEN** fino all'ingresso e al via di A6d.

### A6d — Decisione 36: registrazione su invito per le istanze nuove, impostazioni globali solo con il login — in corso

#### A6d.0 — Analisi e risposte del coordinatore ✅ (2026-10-15)
> **La decisione 36** (dal coordinatore):
> 1. **Registrazione**: il default diventa «su invito»; «aperta» solo per scelta dell'admin, segnalata nel pannello
>    Sicurezza. Il primo account resta creabile finché l'istanza non ne ha nessuno. Le istanze già «aperte» tengono la
>    loro scelta, con l'avviso. Se il default cambia, serve una riga ⚠️ nel CHANGELOG.
> 2. **Impostazioni globali solo con il login**, dopo aver verificato che la configurazione pubblica di H porti fuori
>    tutto quello che serve alla pagina di login.
> 3. **Restano visibili** i nomi dei broker e degli utenti, e le email; la ricerca degli utenti non cambia.
>
> **Lo stato trovato** (sola lettura, 15/10):
> - il default di oggi è `open` (`GLOBAL_SETTINGS_DEFAULTS`); la 006 converte solo dove c'è `enable_registration`;
> - il primo account il backend lo crea admin in ogni modalità, ma con `invite`/`disabled` il login nasconde
>   «Register here»;
> - `GET /settings/global` e `/global/{key}` sono pubbliche. Il frontend le legge solo da loggato (`appBootstrap`, le
>   schede Preferenze e Globali, la pagina Files); le pagine pubbliche leggono solo `/system/instance`. Quindi non c'è
>   niente da spostare.
>
> **Il disegno approvato**:
> 1. **Default `invite`** in `GLOBAL_SETTINGS_DEFAULTS`, più una migrazione di soli dati, idempotente: se manca la riga
>    `registration_mode` e `users` ha almeno un account, scrive `open`. Così nessuna istanza esistente cambia in
>    silenzio.
>    - **Numero**: la 007 è di X (`007_plugin_settings`, CP10), che entra prima. La mia sarà la **008**, o il primo
>      numero libero: prima di scriverla controllo la testa di Alembic su `dev_release2`.
> 2. **`accounts.first_account_open`** in `/system/instance`: nessun account e, con A7, nessun bootstrap F02.
>    `LoginCard` mostra «Register here» anche in `invite`/`disabled` quando è vero.
>    - Pubblico va bene (coordinatore): che un'istanza sia vuota lo si scopre comunque provando a registrarsi, e dura
>      pochi minuti; nel cloud F02 lo spegne. **Va scritto nella doc di sicurezza.**
> 3. **L'avviso «registrazione aperta»** arriva con A8 (scheda Sicurezza). Fino ad allora lo dice la doc.
> 4. **Impostazioni globali**: `get_current_user` sulle due GET; la scrittura resta admin.
>    - Il test (`test_instance_block.py`, il parametro `/settings/global` fra le rotte pubbliche) e la docstring di
>      `instance_block.py` di H li faccio io, dichiarati (CP2b di H non tocca quel file).
>    - Da controllare: `test_settings_api.py`, `test_registration_api.py`, `test_uploads_api.py`, `security.md` e le
>      E2E che leggono le impostazioni globali.
> 5. **CHANGELOG ⚠️** approvato: le istanze nuove partono su invito (il primo account si registra comunque); le
>    esistenti tengono la loro scelta; le impostazioni globali solo per chi ha fatto il login.
>
> **Ordine dei lotti**: A6d, poi A6c, poi A7 e A8.
> **Backlog**: A-17 (KeePassXC, Email prima di Username), basso, dopo T-8b dei colori.
> - **Validazione della revisione combinata `f242cd6f4`** (in fila con `nice -n 10`; log in
>   `/tmp/libreFolio_a6b/logs/merge/`):
>   - `api sync` ✅; `front check` 0 errori, 0 avvisi;
>   - Vitest `settingsTabs`, `page.tabs`, `ProfileTab` e `UsersTab`: 151 ✅;
>   - `db populate --force` ✅;
>   - E2E `admin-users` 10 ✅ e `settings` 46 ✅, con `--workers 2`;
>   - `mkdocs build` ✅; `check-orphans` ✅.
>   - Resta `core-unit`, nello slot 1 dopo J, quando lo dà il coordinatore.

#### Nota del coordinatore — `main.py` congelato (15/10, 20:05)
> - `backend/app/main.py` è congelato fino all'ingresso di CP2b di H. CP2b lo divide in `services/platform/`:
>   `lifecycle.py` (avvio e spegnimento), `middleware.py`, `static_site.py` e `database_bootstrap.py`.
> - **Per A**: A6d non tocca l'avvio (default in `schemas/settings.py`, migrazione 008, `LoginCard`, le due GET). A7
>   (admin iniziale F02 all'avvio) e A8 (controlli di sicurezza all'avvio) aspettano CP2b; dopo basta una riga nel
>   modulo giusto.
> - **Rosso preesistente noto** (coordinatore, 15/10 20:08): in `dev_release2`, quindi anche nella mia base dopo il
>   merge, `htmlInterpolation.gate.test.ts` è rosso sulla chiave `email.problems.SMTP_FROM_INVALID` di E2, che contiene
>   `<`. E lo corregge. Se compare in `core-unit` lo segnalo come preesistente; ogni altro rosso va guardato.
> - **Verdetto di G sullo scatto `settings/users`** (`c576a0499`, 15/10 20:09): **ok, può entrare**. Il merge di
>   `gallery.spec.ts` con E2b è pulito. Le note non bloccanti:
>   1. il commento citava «(G-10)», che riguarda l'ordine degli avatar: ora rimanda a `registerGalleryAccount`
>      (`galleryReportSets.ts`). Solo il commento cambia; prettier è pulito;
>   2. «(admin)» nel titolo: tenuto com'è, `'users - all languages and themes'`, come dice la checklist di G e per
>      non cambiare il filtro;
>   3. corpi e rotte in `fixtures/galleryUsers.ts`: rimandato ad A-18, quando lo scatto si ricontrolla comunque.
>   - `tsc -p tsconfig.e2e.json` sulla revisione combinata (HEAD `97fb199f1`, con il client generato dal mio
>     `api sync`): i soli 2 errori di base (`e2e/onboarding-tour.spec.ts:863`, `src/lib/types/files.ts:9`).

#### A6d.1 — Via, base e vincoli ✅ (2026-10-15, 20:30)
> - **Via del coordinatore** (20:30): A6b è entrato (`dev_release2` = `09ca36b9d`, CHANGELOG `e4edb39a2`). HEAD =
>   `e4edb39a2` = base, worktree pulito. Testa di Alembic: `006_registration_mode`.
> - **Le risposte**:
>   1. `populate_mock_data.py` scrive `registration_mode=open`; la guardia di `conftest.py` (L81-92) forza `open` anche
>      quando la riga manca. File condivisi assegnati a me: li dichiaro.
>   2. `DEFAULT_INSTANCE_CONFIG` resta `open`; il lampo di «Register here» va nel backlog (A-19).
>   3. Il ripiego di `effective_registration_mode` e la docstring di `models.py` seguono il default unico.
>   4. `first_account_open` facoltativo, default `false`.
>   5. Migrazione per ultima, sulla testa che trovo: X entra a breve con la 007.
> - **Prove chieste**: rossi prima; `core-unit`; E2E `auth`, `auth-links` e `settings`; `all-backend` su richiesta.
> - **In più** (coordinatore, 20:30, da E): `black` fallisce su `scripts/test_runner/_backend_services.py`, il
>   `print_info` di `services_account_deletion_preview` (305 caratteri, da `5928176cf`): va spezzato in questo lotto
>   (A-20).
> - Carico della macchina ~168: lavoro leggero, un comando alla volta, `nice -n 10`.

#### A6d.2 — Contratto ✅ (2026-10-15)
> **Verificato** in sola lettura su `b4597efad` e poi su `e4edb39a2`:
> - `get_setting_value` ripiega già su `GLOBAL_SETTINGS_DEFAULTS`: il `"open"` letterale di
>   `effective_registration_mode` (`registration_service.py:87`) non si usa mai, e inganna.
> - La corsia è `open` solo perché il default lo è: `populate_mock_data.py` non scrive impostazioni globali, e la
>   guardia di `conftest.py` inserisce il default mancante e calcola `registration_closed` prima dell'inserimento.
> - `test_instance_block.py` registra i suoi utenti sul DB della corsia: regge finché la corsia resta `open`.
> - EMA-022 di E legge solo `["email"]`: il campo nuovo non lo tocca.
> - Nessuna chiave i18n: K-5 si chiude con il flag (il link compare su un'istanza vuota in ogni modalità), e
>   l'etichetta «Crea l'account amministratore» di §4.7 non serve più.
>
> **Il contratto**:
> - **C1 · Default `invite`**: `GLOBAL_SETTINGS_DEFAULTS["registration_mode"]` vale `invite`. Un'installazione nuova lo
>   semina con `value_type` `str`; senza riga e senza variabile `effective_registration_mode` dà `invite`, non bloccato.
>   Una riga presente non cambia mai.
> - **C2 · Il primo account**: su un'istanza senza account si crea comunque, admin, in ogni modalità (già oggi). Dopo,
>   in `invite` una registrazione senza invito risponde 403 `INVITE_REQUIRED`.
> - **C3 · `accounts.first_account_open`** in `GET /system/instance`: `true` se e solo se `users` è vuota (un account
>   disattivo conta; l'admin in attesa di F02, con A7, è una riga di `users`). Facoltativo, default `false`. Pubblico:
>   lo dice `security.md`.
> - **C4 · Impostazioni globali con il login**: `GET /settings/global` e `GET /settings/global/{key}` rispondono 401
>   `{"detail": "Not authenticated"}` senza sessione o con una sessione falsa; 200, con lo stesso corpo di prima, a ogni
>   utente con il login, admin o no. Le scritture restano admin. Su un'istanza bloccata valgono le regole delle rotte
>   protette (401 a chi non ha sessione, 423 a chi ce l'ha).
> - **C5 · La corsia resta `open`**: `populate_mock_data.py` scrive (upsert) `registration_mode=open`; la guardia di
>   `conftest.py`, se la riga manca, la inserisce `open`, e rimette `open` ogni altro valore, come prima.
> - **C6 · `LoginCard`**: «Register here» se `registration_mode === 'open'` **o** `first_account_open === true`. Prima
>   della risposta, i default (`open`): il link c'è, come oggi.
> - **C7 · `GlobalSettingsTab`**: `SETTING_DEFAULTS.registration_mode` = `invite`; «Reset all» manda `invite`.
> - **C8 · Il default unico**: niente ripiego letterale in `effective_registration_mode`; la docstring di `models.py`
>   dice `invite`.
> - **C9 · Migrazione** (ultimo passo, sulla testa che trovo; nome `0NN_registration_invite_default`, 31 caratteri): solo
>   dati, idempotente. Se manca la riga `registration_mode` e `users` ha almeno un account, scrive `open` (`str`, la
>   descrizione congelata, `updated_by_user_id` nullo). Se la riga c'è, non la tocca; senza account non scrive niente.
>   Downgrade: nessuna operazione, documentata (la riga `open` è il default di prima).
> - **C10 · A-20**: il `print_info` sotto i 300 caratteri, nello stile di `black`.
>
> **Superfici dichiarate** (file non miei o condivisi):
> - `backend/test_scripts/conftest.py`, `backend/test_scripts/test_db/populate_mock_data.py`: assegnati dal coordinatore;
> - `backend/test_scripts/test_api/test_instance_block.py` (il parametro `/settings/global` passa da
>   `PUBLIC_READS_OUTSIDE_THE_LIST` a `REFUSED_READS`) e la docstring di `backend/app/api/v1/instance_block.py`: di H,
>   approvati;
> - `frontend/e2e/fixtures/instance-config.ts`: mio di A5b, con `plainInstanceConfig` di G; solo un'opzione in più a
>   `serveRegistrationMode`;
> - `scripts/test_runner/_backend_services.py` (A-20) e `_backend_db.py` (la registrazione della migrazione, alla fine).
>
> **Categorie**: `LoginCard.test.ts` e `GlobalSettingsTab.test.ts` stanno in `component-unit`; `instanceConfig.test.ts`
> in `core-unit`.

#### A6d.3 — Test rossi (tre `test-author` in parallelo, solo scrittura) ✅ (2026-10-15)
> - **B1** (default e primo account): `test_registration_service.py`, `test_global_settings_service.py`,
>   `test_registration_api.py`, `test_auth_api.py` (LOOP-002: riga `open` esplicita). Spazzati senza cambi:
>   `test_users_admin_api.py`, `test_account_deletion_api.py`.
>   - Nuovi: il caso C2 di servizio; SETTING-002 (la semina non tocca una riga che c'è); FIRST-001…005 (istanza
>     vuota: `invite` e `first_account_open`; il primo account admin, il secondo 403 `INVITE_REQUIRED`; il flag in ogni
>     modalità, dalla riga o dalla variabile; un account disattivo conta; un cookie falso non cambia niente).
>   - Riscritti: SETTING-001 (legge la riga dal DB: la GET vuole il login), LOCK-001, URL-001, INSTANCE-001/002, e i
>     casi che contavano su «nessuna riga = open» (riga `open` esplicita).
>   - Le risposte ai suoi dubbi: con una `LIBREFOLIO_REGISTRATION` non valida su un'istanza vuota il flag resta `true`
>     (la regola del primo account del backend); la corsia lasciata `disabled` da `services global-settings` (già
>     così) la ripara la guardia di C5, che ora inserisce `open`.
> - **B2** (letture e forma): `test_settings_api.py` (GSET-001/003 con un utente normale; GSET-002, 002b, 002c: 401
>   come `GET /settings/user`, anche per una chiave che non esiste e con un cookie falso), `test_system_api.py` (tre
>   chiavi in `accounts`; nuovo: il flag facoltativo e `false` per default, anche nell'OpenAPI, come EMA-022),
>   `test_instance_block.py` (il parametro spostato). `test_uploads_api.py` fa già il login: invariato.
>   - Il 401 con un cookie falso ha il corpo di `get_current_user` («Session expired or invalid»), non «Not
>     authenticated»: GSET-002c chiede lo stesso corpo di `GET /settings/user`. Corretto.
> - **F1** (frontend): `LoginCard.test.ts` (il flag con `invite` e `disabled`, `false` esplicito, `open` con `false`,
>   il cambio senza rimontare), `GlobalSettingsTab.test.ts` («Reset all» e il reset di riga propongono `invite`; i casi
>   bloccati partono da `open`), `fixtures/instance-config.ts` (opzione `firstAccountOpen`, solo in aggiunta),
>   `auth.spec.ts` (due caricamenti `invite` che differiscono solo per il flag).
>   - Il limite noto: la scheda non dice quando ha applicato la risposta, quindi il caricamento con `true` può passare
>     per caso nel rosso (finestra di un poll). Va con A-19 (uno stato `data-*` sulla scheda).
> - **Fuori pista — `settings/scheduler.spec.ts`** (segnalato da B2): FSCH-006 e FSCH-006b leggono
>   `GET /settings/global` con il `request` di Playwright prima del login (nessun `storageState`): dopo A6d sarebbe
>   401. Riparazione affidata a F1 (lettura con un contesto API con il login, senza dipendere dal browser). In più la
>   docstring del modulo `test_instance_block.py` (L9-10) elencava le impostazioni globali fra le rotte pubbliche:
>   tolte, dichiarato.
> - **Rossi osservati** (corsia 6182, `nice -n 10`, log in `/tmp/libreFolio_a6d/logs/`):
>   - `services registration`: ❌ 3 su 147, i tre attesi (il registro, `no-row-no-variable-is-invite`, il caso C2);
>   - `services global-settings`: ❌ 1 su 19, `test_registration_mode_default`;
>   - `db populate --force` ✅;
>   - `api registration`: ❌ 21 su 77, i 21 attesi (FIRST-*, INSTANCE-*, SETTING-001, LOCK-001, URL-001).
>   - Fermati dalla seconda pausa del coordinatore (21:00–21:25), con la corsia ferma. Dopo la ripresa (21:09):
>   - `api auth`: ✅ 60 (lo spazzamento di B1 non rompe niente);
>   - `api settings`: ❌ 3 su 97, GSET-002, 002b, 002c;
>   - `api system`: ❌ 6 su 118, le due letture vive, i tre profili in processo, il nuovo caso del flag facoltativo;
>   - `api instance-block`: ❌ 2 su 62, `global-settings` senza cookie e con un cookie falso;
>   - Vitest `LoginCard` e `GlobalSettingsTab`: ❌ 6 su 132, i tre casi del flag e i tre del reset a `invite`;
>   - E2E `auth` (`--workers 2`): ❌ 1 su 34, il nuovo caso A6d, sulla sua precondizione («the stub could not answer
>     … first_account_open false»: il backend non ha ancora il campo).
> - **Interruzione**: il coordinatore manda prima G-15, un lotto piccolo sulla barra delle schede di Settings (sotto).
>   A6d riprende da A6d.4, applicare l'implementazione (bozza pronta: `/tmp/libreFolio_a6d/apply_a6d.py`).

### G-15 — Settings: la barra delle schede non taglia più l'ultima scheda — lotto piccolo, prima di riprendere A6d

#### G-15.0 — Richiesta e analisi ✅ (2026-10-15, 21:25)
> - **Dal coordinatore** (trovato da G nel doppio lancio, da correggere prima di G-13): con le 7 schede dell'admin, su
>   desktop a 1280 px e in spagnolo, «Copia de seguridad» spinge «Correo» fuori dal bordo (se ne vede la «C», anche da
>   attiva); fra 640 e ~1200 px anche in altre lingue (stima di G). La card della barra in
>   `routes/(app)/settings/+page.svelte` ha `overflow-hidden` e `TabBar` non scorre: la scheda si raggiunge solo con
>   `?tab=` o con la tastiera. Proposta: `shrinkLabelsToFit`; se non basta a 640 px, lo scorrimento orizzontale con la
>   scheda attiva sempre in vista. Facoltativo: nello scatto mobile `settings/users` il pannello aperto di marco è
>   tagliato sotto la piega → `frameTarget` sulla riga.
> - **Verificato sul codice**:
>   - sopra `sm` i bottoni di `TabBar` hanno la larghezza naturale (`flex-1 sm:flex-none`): la riga è più larga della
>     card (stima in spagnolo a 1280 px: ~1030 px per 7 schede contro ~960 disponibili), e la card la taglia;
>   - `shrinkLabelsToFit` da solo non basta: misura il riquadro del bottone stesso, che con la larghezza naturale
>     contiene sempre la sua etichetta, quindi non rimpicciolisce mai; e anche al suo minimo (0,75) sette etichette non
>     stanno in 640 px in nessuna lingua;
>   - `fillWidth` romperebbe il gruppo di destra (`sm:ml-auto` della scheda admin: con `flex-1` non resta spazio).
> - **Il disegno**: `TabBar` ha una prop nuova, `scrollable`, facoltativa (default `false`: gli altri 5 usi di `TabBar`
>   non cambiano, markup identico).
>   - Con `scrollable`, la riga sta in un contenitore che scorre di lato (`overflow-x-auto`, barra sottile); la riga è
>     `min-w-full w-max`, così il `ml-auto` del gruppo di destra spinge ancora quando c'è spazio.
>   - La scheda attiva resta intera in vista: alla scelta, al ridimensionamento e al cambio di lingua scorre solo il
>     contenitore (`scrollLeft`), mai la pagina. Una scheda raggiunta con la tastiera la porta in vista il browser.
>   - Settings passa `scrollable`. Nessuna classe di colore cambia (il ratchet dei colori resta uguale).
> - **Prove** (rosse prima): E2E in `e2e/settings.spec.ts` (admin, spagnolo dal selettore della lingua, che scrive solo
>   in `localStorage`; 1280 e 640 px): con `?tab=email` la scheda Email sta intera dentro la barra; ogni scheda o sta
>   nella barra o la barra si può scorrere, e una volta scelta è intera in vista. Vitest `TabBar.test.ts`: senza
>   `scrollable` nessun contenitore in più; con `scrollable` la scheda attiva oltre il bordo fa scorrere il contenitore
>   della differenza. Poi `theme-roles --check`, `front check`, Vitest `TabBar` e `page.tabs`, E2E `settings`,
>   `core-unit` (slot).
> - **Galleria**: `frameTarget` sulla riga di marco nello scatto mobile `settings/users`, dichiarato. Gli scatti desktop
>   spagnoli di Settings e quelli mobile di `users` li rifà G-13.
> - **Commit**: separato da A6d (i file di G-15 non toccano quelli di A6d).

#### G-15.1 — Rossi, implementazione, prove ✅ (2026-10-15, 21:30–22:05)
> - **Rossi** (un `test-author`, solo scrittura):
>   - Vitest `TabBar.test.ts`, describe «scrollable (G-15)»: due guardie (senza `scrollable` nessun contenitore e
>     nessuno scorrimento) e 8 casi del contenitore e del riposizionamento (al montaggio, al cambio di scheda da prop e
>     da clic, una scheda già dentro, il bordo sinistro, il ridimensionamento, il cambio delle etichette), ognuno senza
>     scorrere la pagina. ❌ 8 su 16, i previsti.
>   - E2E `settings.spec.ts`, describe «G-15»: admin, spagnolo dal selettore (solo `localStorage`), 1280×800 e
>     640×800; la scheda aperta con `?tab=email` sta intera nella barra; ogni scheda o sta nella barra o la barra scorre
>     fino a lei, e scelta sta intera in vista. ❌ 4 su 4: a 1280 Email tagliata, a 640 Users ed Email.
> - **Implementazione** (bozza `/tmp/libreFolio_g15/apply_g15.py`): `TabBar` con `scrollable` (uno snippet per la riga,
>   avvolta nel contenitore solo con la prop; `revealActiveTab()` sposta solo `scrollLeft`; ResizeObserver sul
>   contenitore e sulla riga, `requestAnimationFrame` al cambio di scheda o di etichette); Settings passa `scrollable`;
>   nello scatto mobile `settings/users`, `frameTarget` sulla riga di marco.
>   - **Fuori pista** (dal rapporto del test-author): niente `cancelAnimationFrame` (jsdom potrebbe non averlo, e il
>     riposizionamento si può ripetere senza danno); il ResizeObserver guarda anche la riga, che può allargarsi senza
>     che la barra cambi (un font che arriva tardi).
> - **Verdi**: Vitest `TabBar`, `page.tabs`, `settingsTabs` ✅ 57; `theme-roles --check` pulito; `front check` 0 errori, 0
>   avvisi; `tsc` degli e2e con i soli 2 errori di base; E2E `settings` (`--workers 2`) ✅ 50 su 50.
> - **Fuori pista — `scrollable` invece di `shrinkLabelsToFit`** (approvato dal coordinatore, 22:04): la proposta era
>   `shrinkLabelsToFit`, ma misura il riquadro del bottone stesso, che con la larghezza naturale contiene sempre la sua
>   etichetta, quindi non rimpicciolisce mai; e al suo minimo (0,75) sette etichette non stanno in 640 px. Il
>   coordinatore aveva previsto lo scorrimento come ripiego: è diventato la cura.
> - **`core-unit`** (slot del coordinatore, 22:04, `nice -n 10`): ✅ 5139 su 157 file, 56 s.
>   - **Correzione**: `TabBar.test.ts` e `page.tabs.test.ts` stanno in `component-unit`, non in `core-unit` (come
>     avevo scritto al coordinatore): li ho lanciati da soli, ✅ 57 con `settingsTabs`. `component-unit` intera non è
>     stata lanciata: la decide il coordinatore.
> - **Doc**: `docs-writer` su dev `features/settings.md` (la barra) e `core-ui/toolbar.md` (la prop `scrollable`).

#### G-15.2 — Doc e handoff FROZEN ✅ (2026-10-15, 22:10)
> - **Doc** (`docs-writer`): dev `features/settings.md` (la barra è `scrollable`, con il rimando) e `core-ui/toolbar.md`
>   (sezione nuova `#tabbar-scrollable`: facoltativa, cosa fa, perché non `shrinkLabelsToFit` né `fillWidth`; un arco nel
>   mermaid verso Settings). `mkdocs build` strict ✅, `check-links` ✅ 96. Pagine solo inglesi: nessun debito.
> - **Handoff**: i 7 file di G-15 (`TabBar.svelte`, `TabBar.test.ts`, `settings/+page.svelte`, `e2e/settings.spec.ts`,
>   `e2e/gallery.spec.ts`, le due pagine) separati dai file di A6d; `git diff --check` pulito; porta 6182 libera.
> - **Per riprendere A6d** (proposto al coordinatore): `dev_release2` (`209dc6bec`) ha la 007 di X e tocca
>   `test_system_api.py` (E3: la forma di `email`), che è anche fra i miei rossi non committati; un merge della base li
>   troverebbe sporchi. Sequenza proposta: commit di G-15, checkpoint dei rossi di A6d, aggiornamento della base,
>   poi l'implementazione di A6d sui file aggiornati (la bozza combacia ancora: le righe toccate da E3 in `instance.py`
>   non sono le mie) e la 008 sopra la 007.

#### A6d.4 — Base aggiornata e implementazione ✅ (2026-10-15, 22:10–22:20)
> - **Base**: G-15 entrato (`dev_release2` `369204ab5`, registro `2415faf33`); checkpoint dei rossi di A6d `4d6c17427`;
>   merge della base `b953e3ab2` (X CP10 con la 007, E3, E3p, Y8, Z6b). Un solo conflitto, `test_system_api.py`,
>   risolto tenendo i due lati: la mia forma di `accounts` (con `first_account_open`) e quella di E di `email`
>   (`{available, links}`). Riletti i file uniti da soli: portano solo righe di altri.
> - **`component-unit`** sulla base nuova (slot del coordinatore, 22:13): 3689 ✅, 6 ❌ — i 6 rossi attesi di A6d
>   (`LoginCard` 3, `GlobalSettingsTab` 3); `TabBar` e `page.tabs` verdi.
> - **Implementazione** (`/tmp/libreFolio_a6d/apply_a6d.py`, poi `apply_a6d_rest.py`; la bozza combaciava ancora sulla
>   base nuova):
>   - C1 default `invite` (`schemas/settings.py`); C8 niente ripiego letterale in `effective_registration_mode`,
>     docstring di `models.py`;
>   - C3 `first_account_open(session)` in `registration_service.py`, usata anche da `_admission` (una regola sola), e il
>     campo facoltativo in `AccountsInstanceConfig`, riempito da `system/instance.py`;
>   - C4 `get_current_user` sulle due GET di `api/v1/settings.py`; la docstring di `instance_block.py` (di H,
>     dichiarato) non elenca più le impostazioni globali fra le rotte pubbliche;
>   - C5 `conftest.py` (una riga `registration_mode` mancante entra `open`) e `populate_mock_data.py`
>     (`open_lane_registration`, subito dopo la pulizia), condivisi assegnati;
>   - C6 `LoginCard`, C7 `GlobalSettingsTab` (`SETTING_DEFAULTS.registration_mode` = `invite`);
>   - C9 la migrazione `008_registration_invite_default` sopra `007_plugin_settings` (`INSERT … WHERE NOT EXISTS (riga)
>     AND EXISTS (users)`, `CURRENT_TIMESTAMP`; downgrade senza operazioni); la docstring della 006 corretta (diceva
>     che la riga mancante nasce `open`); il runner `db migration-008` (`isolation="pure"`, accanto a 005–007);
>   - C10 A-20: `black` sul solo `print_info` di `services_account_deletion_preview`.
>   - `ruff` e `black` puliti sui file toccati; `api sync`: il client ha `first_account_open?: boolean`
>     (`.optional().default(false)`).
> - **Verdi, primi passi** (`/tmp/libreFolio_a6d/greens.sh`, log in `/tmp/libreFolio_a6d/logs/green/`): `front check`
>   0/0; Vitest `LoginCard`, `GlobalSettingsTab`, `instanceConfig` ✅ 143; `services registration` ✅ 147;
>   `services global-settings` ✅ 19; `db migration-008` ✅ 23, `migration-006` ✅ 37, `migration-007` ✅ 29;
>   `db populate --force` ✅, con la riga della corsia `registration_mode|open|str`, ancora `open` dopo l'avvio del
>   server; `api registration` ✅ 77.

#### A6d.5 — Verdi e doc ✅ (2026-10-15, 22:28–22:45)
> - **API**: `settings` ✅ 97, `system` ✅ 118, `instance-block` ✅ 62, `auth` ✅ 60, `users-admin` ✅ 64.
> - **E2E** (`--workers 2`): `auth` ✅ 34 (il caso A6d compreso), `auth-links` ✅ 9, `settings` ✅ 50; `scheduler`
>   (con la riparazione di FSCH-006/006b) in coda dietro il carico.
> - **Doc** (`docs-writer`, 16 pagine EN): admin `settings` (default «By invitation», il primo account, l'avviso
>   riscritto), `configuration` (`LIBREFOLIO_REGISTRATION`), `service_exposure` (Funnel), `hosting_providers` (le
>   letture pubbliche di un'istanza bloccata), `cli_tools`; utente `installation` (la prima visita mostra il login, già
>   sbagliato prima di A6d); dev `access_control`, `security` (sezione nuova «The First-Account Flag», con la nota
>   approvata), `settings`, `database/users_access`, `database/index` (la 008), `features/auth`, `features/settings`,
>   `state/app-state` (A-19), `pages/index`, `test-walkthrough/runner_architecture` (la corsia resta `open`).
>   `mkdocs build` strict ✅ (al secondo giro: il primo si è fermato su un link verso un'ancora che esiste solo in
>   inglese), `check-links` ✅ 96.
>   - **Debito di traduzione** (A-10, nessun timbro): `admin/settings` (introduzione, la riga, «Who Can Sign Up», che
>     in IT/FR/ES manca del tutto), `configuration`, `service_exposure`, `hosting_providers`, `cli_tools`,
>     `user/installation`.
>   - Tolta dall'avviso la frase «a setup link for this first account is planned for a later version»: è A7, e la
>     doc la scriverà quando c'è.

### A6e — Il cambio dell'email chiede la password (sicurezza, dopo A6d) — in attesa
> - **Dal coordinatore** (22:11; revisione di sicurezza di E3, Alert 1, gravità media, fiducia 8): `PUT /auth/profile`
>   cambia l'email col solo cookie di sessione (niente password, nessun avviso al vecchio indirizzo, le altre sessioni
>   restano). Con la «password dimenticata» di E3, un accesso anche breve a una sessione altrui diventa una presa
>   permanente. Da fare: `current_password` per cambiare l'email (errore a codice se manca o è sbagliata); dopo il cambio
>   si chiudono le altre sessioni (`session_version`), non quella corrente; `ProfileTab` chiede la password quando l'email
>   cambia; prima i rossi; CHANGELOG 🔄. Nell'attesa E tiene spenta `POST /email/password-reset` (409); l'avviso al
>   vecchio indirizzo lo fa E in E4.
> - **Letto finora**: `update_profile` (`api/v1/auth.py`) chiama `user_service.update_profile`, che fa il commit;
>   `change_password` è il modello (`verify_password` in un thread, `end_sessions`, un cookie nuovo con
>   `_issue_session_cookie`); i codici d'errore hanno la forma `detail={"error_code", "message"}`; `ProfileTab` manda
>   `{email}` da solo (`saveField`, e nel salvataggio di tutto); le chiavi `settings.currentPassword` e
>   `settings.currentPasswordIncorrect` esistono già; i test di `PUT /auth/profile` stanno in `test_profile_api.py` (e
>   uno in `test_instance_block.py`); nessuna E2E cambia l'email.

#### A6d.6 — Prove pesanti e handoff FROZEN ✅ (2026-10-15, 23:17–00:00)
> - `core-unit` (via del coordinatore, 22:49): ✅ 5248 su 158 file.
> - `lint --dead-code --scope backend`: nessun reperto nuovo (quelli elencati sono di altri moduli).
> - `all-backend --workers 2` (slot 1, 23:17–23:54, `nice -n 10`): 5 categorie su 7 ✅ (external, db 19/19, utils,
>   schema, e2e). I rossi:
>   - **attesi, A6e** (rossi scritti, non ancora implementati): `services user-profile` 2
>     (`email_verified_at`), `api profile` 7 (PROF-010…013, 016);
>   - **non attesi**: `api pac-planner-tool`, 7 casi di `test_pac_planner_tool_api.py` (ogni `compute` risponde
>     `status: error`, anche una bozza senza prezzo e un'identità vecchia, che non arrivano al solutore). Triage
>     (skill `test-triage`), in corso: la via del calcolo non tocca niente di A6d (`registry.py` parla della
>     registrazione dei plugin, non degli account); il login dei test va (200); il log del server non dice altro.
>     Ipotesi aperte: il carico (due worker e altre corsie: i 7 sono tutti calcoli col tempo del motore) o la base
>     (X CP10). Prossima prova: l'unità da sola, quando il coordinatore la permette (finestra di G-13 dalle 00:00).
>     Nessun verdetto ancora, e niente «flaky».
> - **Handoff FROZEN** mandato al coordinatore, con i file di A6e esclusi.

#### A6e.0 — Contratto breve ✅ (approvato dal coordinatore, 2026-10-15, 22:56)
> **Approvato**, con: C6 (sotto, ex C2b) nei rossi; **una E2E sì**, con un account usa e getta creato dal test; il
> testo del CHANGELOG lo propongo io. Si comincia dopo l'handoff di A6d. Il markup nuovo usa solo i ruoli colore.
> **Base**: T+DV è entrato (`a0915bef9`) e tocca tre miei file (`AuthPageFrame`, `ForgotPasswordCard` senza
> `auth.passwordRecovery`, la direttiva hover di `PasswordInput`); l'aggiornamento arriva al checkpoint di A6d, poi
> `api sync` (cambia `SectorListResponse`).
> - **C1 · Richiesta**: `UpdateProfileRequest` ha `current_password: str | None` (min 1).
> - **C2 · Quando serve**: un cambio d'email (`email` presente e diversa da quella salvata, confronto esatto come in
>   `update_profile`) chiede la password attuale, verificata **prima** di tutto il resto, anche dell'unicità (così chi
>   non ha la password non può sondare se un'email è già usata):
>   - manca → 400 `{error_code: "CURRENT_PASSWORD_REQUIRED"}`;
>   - sbagliata → 400 `{error_code: "CURRENT_PASSWORD_INVALID"}`, con un log di avviso; niente scritto.
>   Solo lo username, o la stessa email: nessuna password, come oggi.
> - **C6 · Verifica dell'email** (coordinatore, 22:51, da E5): quando l'email cambia, `user_service.update_profile`
>   rimette `users.email_verified_at` a NULL, nella stessa transazione. Una riga; nessun flusso di nuova verifica nella 1.3. Prova: con
>   `email_verified_at` impostato, dopo il cambio è NULL; dopo un cambio del solo username resta com'era.
> - **C3 · Sessioni**: dopo un cambio d'email `end_sessions` (nella stessa transazione del cambio) e un cookie nuovo
>   alla sessione corrente, come `change-password`: le altre sessioni finiscono, questa continua. Un cambio del solo
>   username non chiude niente.
> - **C4 · `ProfileTab`**: quando l'email è cambiata compare un campo «password attuale»
>   (`data-testid="profile-email-password"`, `autocomplete="current-password"`) con un suggerimento («per cambiare
>   l'email serve la password attuale; gli altri dispositivi verranno disconnessi»). Salva l'email (e «Salva tutto»)
>   resta spento finché il campo è vuoto; la richiesta manda `{email, current_password}`; il campo si svuota dopo il
>   salvataggio. I due codici diventano testi tradotti (`settings.currentPasswordIncorrect` c'è già; una chiave nuova
>   per «richiesta»); un 400 senza codice (email già usata) mostra la frase del server, come oggi (oggi un `detail` a
>   oggetto finirebbe come «[object Object]»). Il markup nuovo usa solo i ruoli di colore.
> - **C5 · CHANGELOG 🔄** (testo per il coordinatore): cambiare l'email chiede la password attuale e disconnette gli
>   altri dispositivi; `PUT /api/v1/auth/profile` con un'email nuova vuole `current_password`.
> - **Prove** (rossi prima): `test_profile_api.py` (`test_update_email` e `test_update_both` ora senza password → 400;
>   casi nuovi: manca, sbagliata, giusta → 200 con la vecchia sessione chiusa e la corrente viva, solo username senza
>   password, stessa email senza password, la password sbagliata non rivela un'email già usata); Vitest
>   `ProfileTab.test.ts` (il campo compare e sparisce, Salva spento, il payload, i due codici, il campo svuotato); E2E:
>   nessuna cambia l'email oggi; una sola, in `settings.spec.ts`, con un account usa e getta, se il coordinatore la vuole.
> - **Dopo l'ingresso di A6d e A6e** (avviso del coordinatore, 22:51): E5 scriverà agganci dichiarati nei miei file
>   (`register_user`, `user_usage`, `auth.py` con `EMAIL_NOT_VERIFIED`, `schemas/auth.py`, `update_user_status` e
>   `set_user_active`, `settings_service` con un 409, `LoginCard`, `RegisterCard`, `GlobalSettingsTab`): li rivedo io.
> - **Doc**: utente `settings/profile`, dev `security` (la minaccia e la cura), `access_control` (quando finiscono le
>   sessioni). **Fuori**: l'avviso al vecchio indirizzo (E in E4); il limite dei tentativi su questa rotta (A8, nota
>   nel backlog).

#### A6e.1 — Rossi (due `test-author`, solo scrittura, file separati da A6d) ⏳ (2026-10-15, 22:55)
> - Via del coordinatore (22:52): i rossi di A6e si scrivono adesso, prima dell'handoff di A6d; nell'handoff i loro file
>   restano fuori, elencati come esclusi.
> - **Backend**: `test_profile_api.py` (API, sulla corsia) e `test_user_profile.py` (servizio, C6).
> - **Frontend**: `ProfileTab.test.ts` e un describe nuovo in `e2e/settings.spec.ts` con un account usa e getta.
> - **Decisione notturna, da rivedere**: la fine delle sessioni e `email_verified_at = NULL` stanno in
>   `user_service.update_profile`, quando l'email cambia davvero, nello stesso commit della nuova email. Così un cambio
>   rifiutato (email già usata) non chiude nessuna sessione, e ogni chiamante del servizio ha la stessa regola.
>   L'endpoint verifica la password prima di tutto e dà il cookie nuovo alla sessione corrente.
> - **Rossi scritti** (non ancora lanciati; nell'handoff di A6d restano fuori):
>   - `test_profile_api.py`: PROF-002, 003 e 009 mandano ora la password giusta (restano i controlli del successo e
>     dell'unicità); nuovi PROF-010 (senza password, campo assente o `null` → `CURRENT_PASSWORD_REQUIRED`), 011 (sbagliata
>     → `CURRENT_PASSWORD_INVALID`, nessun cookie, la seconda sessione vive), 012 (email di un altro + password mancante o
>     sbagliata → l'errore della password, mai «already registered»), 013 (giusta → 200, un cookie `session` nuovo, la
>     seconda sessione e il vecchio cookie 401, la corrente 200 con l'email nuova), 014 e 015 (guardie: solo username,
>     stessa email), 016 (`""` → 422). Attesi rossi: 7.
>   - `test_user_profile.py`: `email_verified_at` NULL dopo un cambio d'email (×2, rossi), invariato senza cambio
>     d'email (×3) e dopo un cambio rifiutato (guardie).
>   - `ProfileTab.test.ts`: 21 casi nuovi (il campo, il suggerimento, i bottoni spenti, i payload, lo svuotamento, i due
>     codici con `data-error-code`, l'email che resta, il rifiuto senza codice, il codice sconosciuto mai «[object
>     Object]») e 6 casi esistenti che ora riempiono la password.
>   - E2E `settings.spec.ts`, describe «A6e»: un account usa e getta; un secondo dispositivo con la sessione aperta prima;
>     password sbagliata (400, il codice, l'email resta, nulla cambia sul server), poi giusta (200, cookie cambiato,
>     `/auth/me` con l'email nuova, il ricaricamento resta dentro, il secondo dispositivo 401); `finally` cancella.
> - **Decisioni notturne, da rivedere**:
>   - un codice sconosciuto non va su `data-error-code` (vuoto) e mostra un testo generico, come le finestre degli
>     account (`describeAccountError`);
>   - per i due codici noti il banner mostra il testo tradotto, non la frase del server;
>   - una password sbagliata in una richiesta senza cambio d'email (solo username, o la stessa email) si ignora: la
>     password si verifica solo quando l'email cambia;
>   - un'email che differisce solo per maiuscole è un cambio (confronto esatto, come `update_profile`);
>   - un cambio rifiutato (email già usata) non chiude nessuna sessione: la fine delle sessioni è nello stesso commit
>     della nuova email;
>   - l'E2E salva con `profile-save-all`: i bottoni di riga non hanno un testid (il titolo è tradotto).
> - **Bozze pronte**: `/tmp/libreFolio_a6e/apply_a6e_backend.py`, `apply_a6e_frontend.py` (il campo nella colonna
>   sinistra della riga dell'email, sotto il suggerimento; solo ruoli di colore; due chiavi nuove nelle 4 lingue,
>   `settings.currentPasswordRequired` e `settings.emailPasswordHint`).

#### A6d.7 — Commit, base aggiornata, prove leggere durante G-13 ⏳ (2026-10-16, 00:00–)
> - **Commit del coordinatore**: `683b4ff5b` feat, `2ab1d5572` doc, `10cfa4cf2` journal; merge di `dev_release2`
>   (`de349d4c3`) pulito → HEAD `ce4acff6c`. I 4 file rossi di A6e restano non committati.
> - **Riletti i file uniti da soli**: `LoginCard.svelte` (le classi di T su L41/L77, la mia condizione su L112),
>   `security.md` (la sezione «The First-Account Flag» e il paragrafo delle rotte private con il testo di entrambi),
>   `access_control.md`, `database/index.md` (005–008 in ordine), `_backend_services.py` (`black` pulito).
> - **Triage del PAC** (skill `test-triage`), evidenza: nel log della mia run le risposte `compute` hanno
>   `code: worker_crashed`, anche il caso che dovrebbe fermarsi alla validazione (`invalid_parameters`): il processo
>   isolato esce prima del risultato. Coincide con quanto ha visto G alle 23:05 (carico 80–96, swap; 8 su 8 verdi a
>   carico basso). Verdetto candidato: **ambiente** (risorse della macchina), da confermare con l'unità da sola dopo
>   le 01:15, `nice`.
> - **Durante G-13** (00:00–01:15, il carico sotto 70, una alla volta): `api sync`, `front check`,
>   `theme-roles --check`, Vitest `LoginCard` e `GlobalSettingsTab`, `services registration`, `db migration-008`,
>   `mkdocs build` e `check-links`. **Dopo le 01:15**: `api pac-planner-tool` da sola ed E2E `auth`; poi l'ingresso.
> - **Durante G-13, prove leggere ✅** (00:00–00:03, `/tmp/libreFolio_a6d/logs/g13/`): `api sync`; `front check` 0/0;
>   `theme-roles --check` pulito; Vitest `LoginCard` e `GlobalSettingsTab` 132; `services registration` 147;
>   `db migration-008` 23; `mkdocs build` ✅; `check-links` ✅.

#### A6e.2 — Rossi leggeri, implementazione, verdi leggeri ⏳ (2026-10-16, 00:03–)
> - **Rossi osservati**: Vitest `ProfileTab` ❌ 25 su 77 (i 6 casi aggiornati e 19 dei 21 nuovi; le 2 guardie verdi);
>   `services user-profile` ❌ 2 su 42; `api profile` ❌ 7, già visti nell'`all-backend` di A6d (PROF-010…013, 016).
> - **Decisione notturna, da rivedere**: il rosso dell'E2E di A6e non si può vedere prima delle 01:15 (G-13: niente
>   E2E). Applico lo stesso l'implementazione: gli stessi comportamenti sono coperti dai rossi Vitest e API già visti;
>   l'E2E si prova verde dopo le 01:15, e il suo punto di rottura previsto («password field visible») l'ho letto.
> - **Implementazione** (`/tmp/libreFolio_a6e/apply_a6e_backend.py`, `apply_a6e_frontend.py`): `current_password` nella
>   richiesta; l'endpoint verifica la password prima di tutto e dà il cookie nuovo; `update_profile` mette
>   `email_verified_at = NULL` e `end_sessions` nello stesso commit dell'email; `ProfileTab` con il campo, il
>   suggerimento, i bottoni spenti, `describeRefusal` (i due codici tradotti, `data-error-code`, mai «[object
>   Object]»); due chiavi nuove nelle 4 lingue. `ruff`, `black`, prettier puliti; `api sync`.
> - **Verdi leggeri**: Vitest `ProfileTab` e i cancelli i18n ✅ 107; `services user-profile` ✅ 42 (ha ricreato il DB
>   della corsia: prima delle prove API ed E2E serve `db populate --force`).
> - **Verdi leggeri (seguito)**: `front check` 0/0; `theme-roles --check` pulito; `i18n check` ✅.
> - **Doc** (`docs-writer`, 8 pagine EN, senza build): utente `settings/profile` (sezione «Changing Your Email»); dev
>   `security` (sezione `#email-change`, la riga nella tabella della revoca delle sessioni), `access_control`,
>   `users_and_brokers`, `database/users_access` (corretto anche «nessun codice imposta `email_verified_at`»: E5a lo fa),
>   `features/settings` (la riga dell'email di `ProfileTab`), `features/auth` (la riga del contratto dei password
>   manager). **Pagine di E** (`developer/backend/email.md`, `admin/email.en.md`): la ragione della sospensione di
>   «password dimenticata» diceva che l'email si cambia col solo cookie; corretta, dichiarata a parte (decide il
>   coordinatore).
>   - **Fuori pista** (dal rapporto del docs-writer): il campo nuovo non aveva `id`, `name` né un'etichetta, contro il
>     contratto dei password manager (`auth.md#password-manager-contract`). Aggiunti `id="profile-current-password"`,
>     `name="current-password"` e un `<label for>` nascosto con la chiave del segnaposto; Vitest `ProfileTab` ✅ 77,
>     colori puliti.
>   - `mkdocs build` strict ✅, `check-links` ✅ 96. Debito di traduzione (A-10): `user/settings/profile`, `admin/email`.
> - **Dopo le 01:15** (`/tmp/libreFolio_a6e/after_g13.sh`): `db populate --force`, `api pac-planner-tool` da sola
>   (triage A6d), `api profile`, `api auth`, `api instance-block`, E2E `auth` e `settings`.

### A6c — Decisione 37: le regole della password in un posto solo — contratto approvato (2026-10-16, 00:38)
> **Approvato** dal coordinatore, con la decisione notturna sulle classi Unicode «da rivedere». I rossi adesso, in file
> separati da A6e; l'implementazione dopo il commit di A6e. Nel CHANGELOG: la UI e la CLI ora accettano gli stessi
> simboli e le maiuscole non ASCII. Le due frasi nelle pagine di E entrano col commit di doc di A6e, dichiarate.
> **Decisione notturna, da rivedere**: le chiavi della UI restano quelle di oggi (`minLength`, `hasUppercase`…: testid
> `password-rule-<chiave>` e chiavi i18n), con una mappa codice del server → chiave in `passwordRules.ts`, perché
> l'E2E `e2e/layout/theme-roles.spec.ts` dei colori legge quei testid. Un codice che la UI non conosce non blocca
> (`valid` lo ignora): decide il server.
>
> **A6c.1 — Rossi** ⏳: due `test-author`, solo scrittura (backend: `test_password_policy.py` nuovo, `test_auth_api.py`,
> `test_registration_api.py`, `test_system_api.py`, la CLI; frontend: `passwordRules.test.ts` nuovo,
> `PasswordStrength.test.ts`, `RegisterCard.test.ts`, `PasswordChangeModal.test.ts`, `ResetPasswordCard.test.ts`,
> `registrationErrors.test.ts`).
> **Lo stato** (sola lettura): le stesse cinque regole (8 caratteri, maiuscola, minuscola, cifra, simbolo) sono scritte
> in `PasswordStrength.svelte` (classi ASCII e un elenco di simboli; usato dalla modale del cambio password, dalla
> registrazione e dal reset, che legge il suo `valid`) e in `scripts/user_cli.py` `validate_password` (classi Unicode, un
> altro elenco di simboli): divergono già. L'API chiede solo 8 caratteri (`min_length=8` in `schemas/auth.py`).
> L'etichetta «At least 8 characters» ha il numero scritto nel testo.
>
> **Contratto proposto**:
> - **C1 · Una fonte**: `services/accounts/password_policy.py`, le cinque regole di oggi (`min_length` 8, `uppercase`,
>   `lowercase`, `digit`, `special`) e `failed_rules(password) -> list[str]`. **Decisione notturna, da rivedere**: le
>   classi sono Unicode, uguali in Python e in JS (maiuscola `Lu`, minuscola `Ll`, cifra `Nd`; simbolo: ogni carattere
>   che non è lettera, numero o spazio). Oggi la UI accetta solo maiuscole ASCII e un elenco fisso di simboli.
> - **C2 · Dove vale**: ogni password nuova — `POST /auth/register`, `/auth/change-password`, `/auth/password-reset`, la
>   CLI (`user create`, `user reset`: via `validate_password`), poi il `/setup` di A7. Rifiuto: 400
>   `{error_code: "PASSWORD_TOO_WEAK", message, rules: [codici mancati]}`; gli schemi tengono solo «non vuota». Le password
>   già salvate restano valide (il login non controlla le regole).
> - **C3 · Esposte**: `GET /system/instance` → `accounts.password_rules: [{code, value?}]`, pubblico (le pagine di
>   registrazione, invito e reset le leggono prima del login).
> - **C4 · UI**: `PasswordStrength` prende le regole da `instanceConfig` (finché non risponde, le cinque di oggi), le
>   verifica con le stesse classi, un'etichetta per codice (la lunghezza come ICU `{value}`); registrazione e modale
>   legano `valid` come il reset, senza copie proprie; `PASSWORD_TOO_WEAK` del server mostra le regole mancate.
>   L'indicatore di robustezza resta.
> - **Prove** (rossi prima): la politica; le tre rotte per ogni regola; una password debole già salvata entra ancora;
>   la CLI; la forma di `/system/instance` (che tocca di nuovo i test a forma esatta: `test_system_api`,
>   `test_registration_api`); Vitest `PasswordStrength` con un insieme di regole cambiato, registrazione, modale, reset.
> - **Doc**, CHANGELOG 🔄 (il server applica le stesse regole dell'app; un client dell'API riceve
>   `PASSWORD_TOO_WEAK`).
> - **Ordine**: l'implementazione tocca `schemas/auth.py` e `api/v1/auth.py`, come A6e: comincia dopo il commit di A6e.
>   I rossi stanno in file diversi da quelli di A6e: si possono scrivere prima.
>
> **A6c — bozze** (in `/tmp/libreFolio_a6c/`, da applicare dopo il commit di A6e; corsia ferma per la regola delle
> 00:55–01:40):
> - `password_policy.py`: le cinque regole, `failed_rules()`, `password_rules_public()` (`value` nullo per le regole
>   senza valore); `apply_a6c_backend.py` (combacia, a secco): gli schemi tengono solo «non vuota», `PasswordRuleRead` e
>   `accounts.password_rules`, `_refuse_weak_password()` in testa a register, reset e change-password (prima della
>   password attuale), `/system/instance` pubblica le regole, la CLI stampa una frase per regola mancata.
> - **Decisioni notturne, da rivedere**: un elenco di regole vuoto o assente vale come «quelle di oggi» nella UI;
>   `PasswordStrength` passa ai runes per seguire `instanceConfig` (che è stato reattivo) senza rimontarsi;
>   `PasswordChangeModal` legge anche un `detail` a oggetto (oggi lo tratta da stringa: con `PASSWORD_TOO_WEAK` si
>   romperebbe).
>
> **A6c.1 — Rossi scritti** ✅ (non ancora lanciati: la corsia è ferma fino al via del coordinatore, ~01:40):
> - **Backend**: `test_password_policy.py` nuovo (POLICY-000…006, puro; da registrare come `services password-policy`,
>   isolamento PURE); `test_auth_api.py` (REG-004 e CHPWD-005 da 422 a 400 `PASSWORD_TOO_WEAK`; PWD-001…008; le password di
>   preparazione rese forti); `test_registration_api.py` (RESET-004 per regola, RESET-006, RESET-007, RULES-001…003, le
>   forme esatte con `password_rules`); `test_system_api.py` (le due forme); la CLI in
>   `test_utilities/test_dev_cli_image.py` (IMG-031, 031b/c/d). **File di altri, dichiarati**: `test_brim_api.py`,
>   `test_brim_scalable_api.py`, `test_e2e/test_brim_e2e.py` registravano con `testpass123`: ora `TestPass123!`, o dopo
>   A6c fallirebbero alla preparazione. In più una cifra fissa nei modelli `Initial-/Changed-/Invited-{hex12}` dei miei
>   test (una volta su 130 000 non avrebbero una cifra).
> - **Frontend**: `passwordRules.test.ts` nuovo (62 casi; da registrare in `core-unit` accanto a
>   `registrationErrors.test.ts`), `PasswordStrength.test.ts` (14), `RegisterCard.test.ts` (6), `PasswordChangeModal.test.ts`
>   (7), `ResetPasswordCard.test.ts` (5 e una riga), `registrationErrors.test.ts`.
> - **Difetto vero trovato** (frontend): `PasswordChangeModal` tratta ogni `detail` come stringa; con un `detail` a oggetto
>   lancia dentro il `catch` di `trySave` e resta in `isSubmitting`. La cura è nella bozza.
> - **Per la revisione del mattino** (dalla decisione sulle classi Unicode): una password di sole lettere senza maiuscole
>   e minuscole (`漢漢漢漢漢漢12!`) non passa le regole del caso; un accento combinante (U+0301) o un carattere di controllo
>   contano come simboli; nessuna normalizzazione NFC; tab, a capo e U+200B restano non fissati (`isspace` e `\s`
>   divergono su caratteri rari).
> - **Bozze aggiornate**: i messaggi della CLI contengono il codice della regola («min_length: …», «digit: …»), come
>   chiede IMG-031; `password_rules` ha un default vuoto (due test esistenti costruiscono il modello senza), e la UI tratta
>   un elenco vuoto come «quelle di oggi».

#### A6d/A6e — Prove dopo la ripresa (2026-10-16, 01:33–01:44)
> - `db populate --force` ✅ (la riga della corsia `open`).
> - **A6e**: `api profile` ✅ 21 (PROF-001…016); `api instance-block` ✅ 62; `api auth`: 64 ✅ e 24 ❌, **tutti rossi di A6c**
>   attesi (REG-004, CHPWD-005, PWD-001 ×10, PWD-003 ×10, PWD-004, PWD-007): nessuna regressione da A6e.
> - **Triage del PAC chiuso**: `api pac-planner-tool` da sola, col carico a 32: ✅ 12 su 12. **Verdetto: ambiente** (il
>   processo isolato usciva prima del risultato, `worker_crashed`, sotto carico e swap). Nessun cambio di codice.
> - **E2E** (`auth` per A6d, `auth` e `settings` per A6e): dopo la galleria mobile di Y, al via del coordinatore.

#### A6e.3 — E2E (slot pesante 2) e handoff FROZEN ✅ (2026-10-16, 02:03–02:10)
> - E2E `auth` ✅ 34 (il caso di A6d compreso) e `settings` ✅ 51 (il caso nuovo di A6e compreso), `--workers 2`, `nice`,
>   sul worktree con A6e aperto. Porta 6182 libera; `git diff --check` pulito.
> - **Handoff**: A6d può entrare (`ce4acff6c`); il checkpoint di A6e con i suoi file, i rossi di A6c esclusi. Stato
>   FROZEN fino al commit; poi A6c (implementazione sulle bozze in `/tmp/libreFolio_a6c/`).

#### A6d + A6e — Base aggiornata e prove sulla revisione combinata ✅ (2026-10-16, 02:12–02:40)
> - **Merge** di `dev_release2` (`57802d827`) → `340ddc848` (genitori `675f21493` e `57802d827`). Un solo conflitto,
>   `security.md` § «Private Endpoints»: unione dei due lati (le impostazioni globali lette con la sessione, e le due rotte
>   con token Bearer di Z4). Rilette le fusioni automatiche (`instance_block.py`, `test_instance_block.py`,
>   `configuration`, `hosting_providers`, `settings.en.md`, `access_control.md`, `email.md`, `_backend_services.py`):
>   coerenti. Nessuna migrazione nuova: la testa resta la 008 sopra la 007.
> - **Prove**, una alla volta con `nice` e il carico sotto 70 (script `/tmp/libreFolio_a6e/combined.sh`, log in
>   `/tmp/libreFolio_a6e/logs/combined/`): `api sync` ✅ (nessun file tracciato cambiato); `api settings` ✅ 97;
>   `api profile` ✅ 21; `api instance-block` ✅ 62; `db migration-008` ✅ 23; `mkdocs build` ✅; `check-links` ✅.
> - **Rossi: tutti e solo di A6c**, classificati uno per uno dal corpo della traccia:
>   - `front check`: 2 errori, entrambi in `passwordRules.test.ts` (importa `./passwordRules`, che non esiste ancora);
>   - `core-unit`: 5900 ✅ e 4 ❌, tutti in `registrationErrors.test.ts` (`PASSWORD_TOO_WEAK`);
>   - `api registration`: 59 ✅ e 37 ❌: 18 perché `accounts` non ha ancora `password_rules` (INSTANCE-001/002,
>     FIRST-001…005, URL-001), 19 perché l'API non risponde ancora `PASSWORD_TOO_WEAK` (RESET-004 ×5, RESET-006 ×5,
>     RULES-001/002/003);
>   - `api auth`: 64 ✅ e 24 ❌, tutti `PASSWORD_TOO_WEAK` (REG-004, CHPWD-005, PWD-001 ×10, PWD-003 ×10, PWD-004, PWD-007);
>   - `api system`: 113 ✅ e 5 ❌, tutti per `password_rules` (2 live, 3 in-process).
> - Le bozze di A6c (`/tmp/libreFolio_a6c/`) combaciano ancora sulla base nuova (dry run pulito, backend e frontend).
> - Porta 6182 libera. **Esito**: A6d e A6e possono entrare insieme da `340ddc848`.

#### A6c.2 — Registrazioni nel runner e rossi osservati ✅ (2026-10-16, 02:41–02:53)
> - **Runner**: `services password-policy` (isolamento `pure`: funzioni pure, niente DB, server né variabili) in
>   `_backend_services.py`; `passwordRules.test.ts` nella lista di `core-unit` (`_frontend_utility.py`), accanto a
>   `registrationErrors.test.ts`. Nessun altro catalogo da aggiornare.
> - **Rossi osservati**, tutti per le ragioni attese (log in `/tmp/libreFolio_a6c/logs/`):
>   - `services password-policy`: errore di raccolta, `password_policy` non esiste ancora;
>   - `utils dev-cli-image`: 78 ✅ / 7 ❌, tutti IMG-031 (`€` simbolo, `²` non cifra, messaggi col codice della regola,
>     `user create` con `Écrire12€`, `user reset` con `Ecrire²²!`);
>   - Vitest (6 file): 195 ✅ / 26 ❌ e un errore: `PasswordStrength` 9, `RegisterCard` 4, `ResetPasswordCard` 4,
>     `PasswordChangeModal` 5, `registrationErrors` 4, `passwordRules.test.ts` non si carica (modulo mancante). L'errore
>     non gestito è il difetto vero già annotato: `detail.toLowerCase is not a function` con un `detail` a oggetto.
>   - Già visti sulla revisione combinata: `api auth` 24, `api registration` 37, `api system` 5, `front check` 2.
> - I file toccati solo per tenere valide le password esistenti (`test_session_revocation_api.py`,
>   `test_users_admin_api.py`, i tre BRIM): una cifra in più o `TestPass123!`; restano verdi prima e dopo.

#### A6c.3 — Implementazione e verdi ✅ (2026-10-16, 02:53–03:41)
> - **Bozze applicate** (`/tmp/libreFolio_a6c/apply_a6c_backend.py` e `apply_a6c_frontend.py`, combaciavano):
>   `password_policy.py` nuovo; schemi «non vuota»; `PasswordRuleRead` e `accounts.password_rules`;
>   `_refuse_weak_password()` in testa a register, reset e change-password; `/system/instance` pubblica le regole; la
>   CLI su `password_policy`; `passwordRules.ts` nuovo; `PasswordStrength` ai runes; `RegisterCard` e
>   `PasswordChangeModal` legano `valid`; `PASSWORD_TOO_WEAK` in `registrationErrors` e nel reset; l'etichetta della
>   lunghezza ICU `{value}` in 4 lingue. `ruff` e `black` puliti (una riga vuota di troppo in `user_cli.py`, tolta).
> - **Verdi** (una alla volta, `nice`, log in `/tmp/libreFolio_a6c/logs/greens/`): `api sync` ✅; `services
>   password-policy` ✅ 53; `utils dev-cli-image` ✅ 85; Vitest dei 6 file ✅ 283; `i18n check` ✅; `theme-roles --check`
>   ✅; `api auth` ✅ 88; `api registration` ✅ 96; `api system` ✅ 118; `api session-revocation` ✅ 3; `api users-admin`
>   ✅ 64; `api brim-scalable` ✅ 2; `e2e brim-e2e` ✅ 4; `api brim` ✅ 116 (alla seconda, vedi sotto).
> - **Fuori pista — il tipo generato**: dopo `api sync`, `front check` ha dato 1 errore in `PasswordStrength.svelte`:
>   il generatore scrive un `Optional[int]` con descrizione come `number | null | Array<number | null>` (108 campi così
>   in `generated.ts`; lo schema Zod è giusto). **Decisione notturna, da rivedere**: `PasswordStrength` normalizza
>   `value` a numero o null dove legge le regole servite; il generatore non si tocca.
> - **Fuori pista — `api brim` rosso, verdetto: ambiente** (skill test-triage): 5 casi con la premessa
>   «`e2e_test_admin` … 401». Il setup della categoria `services`, anche per un'unità pura, ha cancellato e ricreato il
>   DB della corsia (log: «Removing existing test database», «Create database via Alembic migrations»), e io non ho
>   rilanciato `db populate --force` prima delle unità `api`: nel DB 173 utenti dei test, nessun `e2e_test_*`. Dopo
>   `db populate --force`: ✅ 116. Nessun cambio di codice.
> - **Doc** (`docs-writer`, 9 pagine EN, nessun comando): utente `settings/profile` («🔑 Change Password»), admin
>   `cli_tools` (il punto 🔒); dev `security` (sezione nuova «🔏 Password Rules»), `access_control` (`PASSWORD_TOO_WEAK`
>   prima riga della tabella della registrazione, `accounts.password_rules`, il reset), `settings`,
>   `frontend/components/features/auth.md`, `core-ui/atoms.md`, `features/settings.md`, `state/app-state.md`. Corretti
>   anche due scarti vecchi: la barra di robustezza ha 3 colori da D-T13, non 5; `UsersTab` fra i lettori di `accounts`.
>   Debito di traduzione in A-10: `user/settings/profile` e `admin/cli_tools`. Nessuna frase falsa nelle pagine di E.
> - **Fuori pista — il reset non caricava le regole del server** (trovato dal `docs-writer`): `/reset-password` non
>   chiama mai `instanceConfig.load()` (lo fanno `LoginCard` e `/invite`), quindi un link aperto in una scheda nuova
>   controlla le regole predefinite; nella 1.3 le due liste coincidono, ma il contratto C3 dice che il reset legge
>   quelle del server. **Decisione notturna, da rivedere**: il reset chiede la configurazione al montaggio senza
>   aspettarla (`void instanceConfig.load()`): `PasswordStrength` la segue da solo, e una richiesta lenta o fallita
>   non ritarda il modulo. Rosso scritto da un `test-author` in `routes/reset-password/page.test.ts`.
> - **Limite noto, lasciato** (dal `docs-writer`): se il server mandasse solo codici che la UI non conosce, `valid`
>   sarebbe vero per qualsiasi password; decide comunque il server, che rifiuta.
> - **Il reset, rosso e verde**: il caso 1 nuovo di `routes/reset-password/page.test.ts` (la pagina chiede la
>   configurazione al montaggio) rosso prima della cura, il caso 2 (il modulo si apre anche se la richiesta non risponde
>   mai) verde prima e dopo. Cura: `void instanceConfig.load()` nell'`onMount` di `/reset-password`. Corrette le due
>   frasi della doc che descrivevano il comportamento vecchio (`state/app-state.md`, `features/auth.md`).
> - **Prove finali leggere** (log in `/tmp/libreFolio_a6c/logs/final/`): Vitest dei 7 file ✅ 303; i 19 file che
>   montano `PasswordStrength` di riflesso, più i cancelli sui sorgenti, ✅ 463; `front check` ✅ 0 errori; colori ✅;
>   Prettier ✅; `mkdocs build` ✅; `check-links` ✅; `git diff --check` pulito; porta 6182 libera.
> - **Non lanciati** (slot pesante): `core-unit` e `component-unit` interi; E2E `auth`, `auth-links`, `settings`,
>   `layout/theme-roles` e `layout/header-scroll` (leggono la lista delle regole e il modulo di registrazione);
>   `all-backend`.

#### A6c.4 — Handoff FROZEN 🧊 (2026-10-16, 03:42)
> - Delta: 42 file modificati e 4 nuovi su `340ddc848`. Fuori: il client generato (ignorato), i log, il DB della corsia.
> - **Per la revisione del mattino** (decisioni notturne): le classi Unicode; le chiavi della UI di oggi con la mappa
>   `RULE_UI_KEYS`; `PasswordStrength` ai runes; la lista vuota vale «quelle di oggi»; la normalizzazione di `value` per il
>   tipo generato; il reset che chiede la configurazione senza aspettarla.

#### A6c.5 — Prove pesanti sulla base aggiornata (`7ec0994ed`) ✅ (2026-10-16, 03:49–04:44)
> - **Base**: il coordinatore ha salvato A6c (`4bbc6fbf6` feat, `dc21b189a` doc, `34ae67dab` journal) e fuso
>   `dev_release2` (`503dce683`) → `7ec0994ed`, pulito. Rilette le fusioni automatiche: `admin/cli_tools` (la sezione di
>   B2 sul ripristino; il mio punto 🔒 intatto), `security.md` (il token del pannello dei backup nella frase degli
>   endpoint privati), `profile.en.md` (l'avatar condiviso, separato dal cambio password), i due cataloghi del runner
>   (Z7b, B2, Y4b, X CP11b; le mie due registrazioni intatte). Coerenti.
> - **Slot 1**: `api sync` ✅, poi `all-backend --workers 2` (`nice`, 03:49:57–04:28:27) ✅ rc 0, **0 rossi**: 4 ondate
>   parallele verdi (4871+5882, 85+2801, 726+1087, 862+949); consolidate `services` 246, `api` 109, `e2e` 7,
>   `external` (28, 33, 11; gli skip sono di rete), BRIM (733, 324, 197, 151), `db` (36, 17, 3, 25, 4, 41, 47, migrazioni
>   005–008 25/37/29/23, 17, 6, 28, 7, 12, 36). Log in `/tmp/libreFolio_a6c/logs/slots/`.
> - Prima della prova, una scansione dei test per password letterali deboli verso le rotte che ora applicano le regole:
>   solo `hashed_password` scritti nel DB e i miei casi deboli voluti. Nessuna nelle E2E.
> - **Slot 2**: `core-unit` ✅ 6212/6212 (04:28–04:30); `component-unit` ✅ 3974/3974 (04:30–04:34); le E2E al via del coordinatore, dopo
>   la galleria di X.
> - **E2E** (`--workers 2`, `nice`, dopo `db populate --force`): `auth` ✅ 34, `auth-links` ✅ 9, `settings` ✅ 51,
>   `theme-roles` ✅ 24 (2 saltati per progetto: l'hover del bordo solo su desktop), `header-scroll` ✅ 11 (3 saltati per
>   progetto: mobile o desktop). 04:34–04:44; porta 6182 libera.
> - **Fuori pista — la pausa**: il messaggio «lo slot 2 dopo la galleria di X» è arrivato con la catena già partita;
>   `kill -STOP` sullo script dopo `core-unit`, `component-unit` lasciata finire, `kill -CONT` al via (04:33:49).
> - **Esito**: A6c pronto per l'ingresso.

### A7 — F02 admin iniziale, `/setup`, K-5, avviso di registrazione aperta — contratto approvato (2026-10-16, 04:50)
> **Approvato** dal coordinatore (C1–C8 come proposti; le tre domande vanno al developer come P16). Stanotte si costruisce
> con le mie proposte, ognuna «Decisione notturna, da rivedere». **A7a** (backend, C1–C5) subito, rossi in file nuovi;
> nei file di E5b (`auth.py`, `schemas/auth.py`, `user_usage`) solo aggiunte piccole: E5b entra prima, al mio
> checkpoint il coordinatore aggiorna la base e risolvo io. **A7b** (C6–C8, frontend) dopo l'ingresso di E5b
> (`LoginCard`). File di H assegnati, una riga ciascuno: `app_lifespan.py` (il passo), `config_audit.py`,
> `instance_block.py`. Condivisi: `.env.example` (solo la sezione F02), `backend.instructions.md` («First user =
> automatic admin»), i18n solo nel mio sottosistema. Macchina ferma 05:30–06:45; `all-backend` di A7a dopo le 06:45.
> Tab bar di Impostazioni (nota di G): misure e tre opzioni al developer (P13); `TabBar.svelte` è di T stanotte.
>
> **Stato verificato** (`ef073af86`): `AccountTokenPurpose.ADMIN_SETUP` (72 h, `/setup`) e `build_admin_setup` di E ci
> sono; `issue_token` genera sempre il token; `tokens/inspect` accetta solo `invite|password_reset`; `user_usage` conta
> attivi + inviti vivi; `create_user(..., is_active=False, commit=False)` esiste; lo username unico basta come guardia
> fra due worker (vince chi scrive per primo); `_add_link_commands` dà lo stesso comando a `user_cli.py` e a `dev.py`.
>
> **A7a — contratto dei test**:
> - **C1 · `config/accounts.py`**: `admin_bootstrap_config() -> AdminBootstrapConfig | None` (`email`, `username`,
>   `token`), letta a ogni chiamata; `None` con F02 spento. `AdminBootstrapConfigError(variable, code)` nomina la
>   variabile, mai il token: `ADMIN_BOOTSTRAP_TOKEN_WITHOUT_EMAIL`, `ADMIN_USERNAME_WITHOUT_EMAIL`, `ADMIN_EMAIL_INVALID`,
>   `ADMIN_USERNAME_INVALID` (3–50), `ADMIN_BOOTSTRAP_TOKEN_INVALID_CHARACTERS`, `…_TOO_SHORT` (< 32), `…_TOO_LONG`
>   (> 200); un `_FILE` illeggibile dà `SecretFileError`. Vuoto = non impostata. `log_configuration_audit()` la chiama:
>   un valore rotto ferma l'avvio.
> - **C2 · `services/accounts/bootstrap_admin_service.py`**: `run_admin_bootstrap(session, config, now=)` →
>   `off` | `ignored` (altri account, nessun admin in attesa; INFO) | `created` (istanza vuota: admin disattivo e
>   superuser, segreto casuale, riga `registration_mode=invite`, token `admin_setup` dato o generato, 72 h; una
>   transazione; fra due chiamate concorrenti una sola crea) | per l'admin in attesa (disattivo, con token `admin_setup`
>   mai consumati): `rearmed` (token della variabile mai visto: revoca i vivi, salva il nuovo), `pending` (un link vivo),
>   `expired` (nessun link vivo: WARNING che rimanda a `./dev.py user setup-link` o a un token nuovo); username o email
>   della variabile cambiati: l'account li segue (username occupato: ERROR, invariato). Consegna solo dopo `created`
>   con token generato: il link nel log una volta (WARNING) e per email (`build_admin_setup`, lingua dell'istanza) se
>   l'email funziona e c'è `LIBREFOLIO_PUBLIC_URL`; un errore d'invio è un log, mai un blocco. Token della variabile:
>   nessun log del token, nessuna email.
> - **C3 · `complete_admin_setup(session, token, new_password)`** e `POST /auth/setup` `{token, new_password}`: prima
>   `PASSWORD_TOO_WEAK`; token non valido, o account già attivo → 400 `TOKEN_INVALID` (il token dell'account attivo viene
>   revocato); poi password (bcrypt fuori dal loop), attivo, `end_sessions`, gli altri token di setup revocati, commit; il
>   cookie e la risposta come il login (`AuthLoginResponse`). `tokens/inspect` accetta `admin_setup` (risponde lo
>   username).
> - **C4 · `user_usage`**: conta anche l'admin in attesa (disattivo con un token `admin_setup` mai consumato).
> - **C5 · `./dev.py user setup-link`**: revoca i link vivi dell'admin in attesa, ne emette uno generato (72 h), lo
>   stampa come `reset-link`; senza admin in attesa ❌ e uscita 1.
> - **Passo d'avvio** `admin-bootstrap` dopo `global-settings` (riga in `app_lifespan.py`); l'email parte in background.
>
> **Decisioni notturne, da rivedere** (ognuna facile da cambiare):
> 1. Link generato: nel log una volta **e** per email quando si può (P16, approvata per stanotte).
> 2. Una variabile F02 rotta ferma l'avvio nominandola (P16), anche su un'istanza con account: come `LIBREFOLIO_BLOCKED`.
> 3. L'email dell'admin di bootstrap è trattata come quella di `user create` (P16): l'aggancio di E5 si allinea
>    all'aggiornamento di base dopo E5b.
> 4. Il token della variabile: 32–200 caratteri non riservati di un URL (`A–Z a–z 0–9 - . _ ~`), più stretto del token
>    del pannello dei backup, perché viaggia in un link (`/setup#token=…`).
> 5. `LIBREFOLIO_ADMIN_USERNAME` senza email è un errore: chi la mette vuole F02.
> 6. Il link di setup di un account già attivo è rifiutato, e revocato.
> 7. L'email parte in background dopo l'avvio: un SMTP lento non ritarda il server.
>
> **Domanda per il developer** (in pausa, il resto va avanti): `/auth/setup` su un'istanza bloccata. La decisione 12 ha
> fatto decadere D-A15, e la lista consentita dice «il resto passa prima dal developer». Proposta: ammetterlo come il
> link di reset (non crea account: attiva quello che il fornitore ha preparato), così un cliente bloccato prima del setup
> arriva comunque alla pagina di blocco e a «Gestisci abbonamento». Finché non decide, la riga non c'è.

#### A7a.1 — Rossi (due `test-author`, solo scrittura, file nuovi) ⏳ (2026-10-16, 04:58–)
> - Due `test-author` in parallelo, solo scrittura: `test_services/test_admin_bootstrap.py` (C1, token dato, C2, C3 di
>   servizio, C4, C5, il passo d'avvio) e `test_api/test_admin_setup_api.py` (C3 e `inspect`: in-process su DB privati
>   per tutto ciò che ha un admin in attesa, sul server della corsia solo rifiuti che non scrivono).
> - **Bozze** (solo scrittura, in attesa dei rossi), in `/tmp/libreFolio_a7a/`: `bootstrap_admin_service.py` (nuovo);
>   `apply_a7a_backend.py` (config, `issue_token(token=)`, `user_usage` + `pending_admin_filter`, schemi, `POST
>   /auth/setup` in fondo ad `auth.py`, una riga in `config_audit.py`, il passo in `app_lifespan.py`, `setup-link`);
>   `apply_a7a_runner.py` (`services admin-bootstrap` pure, `api admin-setup`); `apply_a7a_shared.py`
>   (`.env.example`: la sezione F02 e la riga «open by default» di A5, che A6d ha reso falsa; `backend.instructions.md`).
>   Tutte combaciano a secco; il modulo nuovo passa `ruff` e `black`.
> - **Decisione tecnica** (nel mio perimetro): SQLite è in WAL con `busy_timeout` 30 s. Una scrittura come prima
>   istruzione di una transazione aspetta il lock; una lettura seguita da una scrittura può fallire subito con
>   «database is locked» se un altro ha scritto nel frattempo. Quindi la creazione chiude le letture e comincia scrivendo
>   la riga `registration_mode` (prende il lock, poi conta gli account: un solo worker crea); il setup consuma il token
>   per primo, come il reset; al riavvio, il worker che trova il lock occupato mentre l'altro riarma o rinomina risponde
>   `pending`.
> - **Domanda al developer** inviata al coordinatore (05:00): `/auth/setup` sull'istanza bloccata (P16).
> - **Rossi scritti** (05:25–05:35, nessuno lanciato: la macchina è ferma fino alle 06:45):
>   - `test_services/test_admin_bootstrap.py`, 54 test: CFG-001…011 (variabili, codici d'errore, `_FILE`, l'audit
>     d'avvio che si ferma), TOKEN-001…005 (`issue_token(token=)`), BOOT-001…022 (azioni, gara di due motori,
>     scadenza al microsecondo, riarmo, rinomina, consegna: log una volta e email esatta di `build_admin_setup`, mai un
>     token della variabile nei log), SETUP-001…004, USAGE-001…003, CLI-001…006, STEP-001…003.
>   - `test_api/test_admin_setup_api.py`, 42 casi: SETUP-001…013 e INSPECT-010…013; in-process su DB privati, sul
>     server della corsia solo 4 rifiuti che non scrivono.
>   - Scelte dei `test-author` che ho adottato nella bozza: `deliver_setup_link(result, *, engine=None, now=None)` apre
>     una sessione sua, e il passo d'avvio la chiama per nome con `engine=` in un task; il log «non inviata» dice solo il
>     tipo dell'errore. Lasciate come lette: uno spazio intorno al token è `ADMIN_BOOTSTRAP_TOKEN_INVALID_CHARACTERS`;
>     l'admin in attesa con il link scaduto occupa ancora un posto (definizione letterale di D-A10).
> - **Doc** (`docs-writer`, durante la sosta, nessun comando): 18 pagine EN. Admin: `configuration` (sezione nuova
>   «The Initial Administrator», `#initial-admin`), `hosting_providers` (`#initial-admin`, il lato del fornitore),
>   `cli_tools` (`#setup-link`), `settings` (l'eccezione alla regola del primo account), `users` (l'admin in attesa occupa
>   un posto), una frase in `index`, `host_installation`, `docker_advanced`, `user/installation`, `user/getting-started`;
>   una riga nella pagina `admin/email` di E («What LibreFolio sends»). Dev: `access_control` (sezione F02),
>   `security`, `overview` (il passo `admin-bootstrap`), `settings`, `database/users_access`, `users_and_brokers`,
>   `runner_architecture`. Debito di traduzione (A-10): `configuration` e `cli_tools` con le ancore `#initial-admin` e
>   `#setup-link` da tenere uguali; una o due frasi nelle altre.
> - **Da segnalare** (non modificato): nelle pagine di E diventano false «`build_admin_setup()` has no caller», «three
>   emails have a caller», la riga «Coming Next» e «Never logged… the link» (`developer/backend/email.md`), e in
>   `admin/email.en.md` «Emails with a Link» e i `kind` di «Email sent» senza `admin_setup`. In `admin/users.en.md` il
>   badge «Deactivated» «non occupa posti», ma l'admin in attesa è disattivo e lo occupa: per A7b la scheda Utenti deve
>   mostrarlo come «in attesa del setup» (e non offrire «Riattiva», che lascerebbe un account attivo senza password
>   nota). Gli elenchi delle rotte che rispondono 401 sull'istanza bloccata non nominano `/auth/setup`: aspettano la
>   decisione P16.

#### In attesa — la chiave «unpaired» dopo la decisione 47 (nota del coordinatore, 2026-10-16 06:10)
> Quando la decisione 47 è approvata (aspetta J-17, il developer) e **solo al via del coordinatore**: la chiave V-3 di W,
> `settings …unpaired` (anteprima della cancellazione dei broker), prende una frase in più, «assets sent to them leave at
> their average cost» (EN; IT «quelli mandati a questi broker escono al loro costo medio»; FR «ceux envoyés à ces brokers
> sortent à leur coût moyen»; ES «los enviados a estos brókers salen a su coste medio»). Il testo completo in FR ed ES lo
> chiedo a W.

#### A7a.2 — Rossi osservati, implementazione, verdi ✅ (2026-10-16, 06:48–07:42)
> - **Base**: il coordinatore ha salvato i rossi, la doc e il journal (`4f537ab0f`, `8b9ddee11`, `836f0d1a6`) e fuso
>   `dev_release2` (`72e66d1a6`) → `eb1990f31`. Tre conflitti di doc risolti per unione durante la sosta, solo scrivendo:
>   `admin/hosting_providers` (i due punti «For developers»), `admin/index` (la mia riga Hosting, la Sleep and Wake di
>   dev), `developer/architecture/overview` (`admin-bootstrap` al 12, i passi di dev rinumerati 13–16, `idle-monitor` di
>   Z compreso). Rilette le fusioni automatiche (`configuration`, `security`, `settings`): sezioni diverse da F02. Gli
>   script `apply` combaciavano ancora sull'albero fuso.
> - **Registrazioni nel runner** applicate (`apply_a7a_runner.py`): `services admin-bootstrap` (pure), `api admin-setup`.
> - **Rossi osservati** (06:48–07:01, `nice`, log in `/tmp/libreFolio_a7a/logs/`), tutti per ragioni di A7a:
>   - `services admin-bootstrap`: 12 ❌ e 144 errori di preparazione. Errori: 90 «No module named
>     `bootstrap_admin_service`», 54 «`config.accounts` has no ADMIN_…». Fallimenti: 8 su `issue_token(token=)`, 2 su
>     `cmd_setup_link`, 1 `setup-link` non è un sottocomando, 1 il passo `admin-bootstrap` manca;
>   - `api admin-setup`: 7 ❌ e 35 errori: 37 «cannot import `AdminBootstrapConfig`», la rotta manca (404 in-process,
>     405 sul server della corsia, 4 casi), `inspect` rifiuta `admin_setup` (422).
>   - Lo start del server della corsia ha ricostruito la doc (138 s), vecchia dopo il merge: non un difetto.
> - **Decisione tecnica, da rivedere**: su un'istanza vuota, un token della variabile già salvato in passato (un'istanza
>   svuotata dopo un primo setup) non si riusa: si genera un link nuovo, con un avviso che nomina la variabile. Senza
>   questo, il vincolo d'unicità dell'hash fermerebbe l'avvio.
> - **Bozze applicate** (`apply_a7a_backend.py`, `apply_a7a_shared.py`; combaciavano): `config/accounts.py` (le tre
>   variabili, `AdminBootstrapConfig`, `AdminBootstrapConfigError`), `token_service.issue_token(token=)`,
>   `registration_service.pending_admin_filter()` e `user_usage`, `schemas/auth.py` (`AdminSetupRequest`, `admin_setup`
>   nei due `purpose`), `POST /auth/setup` in fondo ad `auth.py`, una riga ciascuno in `config_audit.py` e
>   `app_lifespan.py` (file di H, assegnati), `setup-link` in `user_cli.py`, `bootstrap_admin_service.py` nuovo;
>   `.env.example` (sezione Accounts: F02, e la riga «open by default» di A5 corretta) e `backend.instructions.md`.
>   `ruff` e `black` puliti su 13 file. Dopo i verdi: tolta `wait_for_deliveries()`, senza chiamanti (resta `_DELIVERIES`,
>   che tiene un riferimento ai task in background); una frase in `access_control.md` sul token della variabile già
>   usato.
> - **Verdi** (una alla volta, `nice`, carico sotto 70; log in `/tmp/libreFolio_a7a/logs/greens/` e `final/`):
>   `api sync` ✅; `services admin-bootstrap` ✅ 156 (anche dopo la pulizia); `services registration` ✅ 147;
>   `services account-tokens` ✅ 65; `services config-audit` ✅ 90; `schemas openapi-client-text` ✅ 78; `api
>   admin-setup` ✅ 42; `api registration` ✅ 96; `api auth` ✅ 88; `api system` ✅ 118; `api instance-block` ✅ 62;
>   `api users-admin` ✅ 64; `utils dev-cli-image` ✅ 85; `front check` ✅ 0 errori; `mkdocs build` ✅;
>   `check-links` ✅; `lint --dead-code`: 53 reperti, nessuno nei file di A7a (tutti preesistenti, in altri moduli);
>   `git diff --check` pulito; porta 6182 libera.
> - Le frasi della doc citate fra virgolette (righe di log, errore della CLI) combaciano col codice applicato.

#### A7a.3 — Handoff FROZEN 🧊 (2026-10-16, 07:45)
> - Delta su `eb1990f31`: 14 file modificati e 1 nuovo. Manca solo `all-backend`, primo nella coda degli slot pesanti.
> - **Il link non ha ancora la sua pagina**: `/setup` arriva con A7b (dopo l'ingresso di E5b). Fino ad allora il link
>   apre la pagina d'errore dell'app; l'API e la CLI funzionano. Proposta: le righe del CHANGELOG entrano con A7b, che
>   completa la funzione.
> - **Per A7b** (in più rispetto a C6–C8, dal `docs-writer`): nella scheda Utenti l'admin in attesa compare come
>   «Disattivato», che «non occupa posti»; va mostrato «in attesa del setup», senza «Riattiva» (attiverebbe un account
>   senza una password nota) e con «Nuovo link di setup» al posto del link di reset.

#### Punti di E e di X dopo A7a (2026-10-16, 07:44–07:55)
> - Il coordinatore ha salvato A7a (`a39b67944` feat, `f9d74b808` doc, `c604ffed0` journal). `all-backend` di A7a nello
>   slot 1 verso le 08:50; il CHANGELOG entra con A7b; l'admin in attesa nella scheda Utenti va in A7b.
> - **E · 1, indirizzi nei log**: d'accordo. Uno scan AST di ogni chiamata al logger in `backend/app` e `scripts/` trova
>   solo due righe, mie: `api/v1/auth.py:382` («Profile updated») e `services/accounts/user_service.py:488` («User profile
>   updated»). Proposta: togliere l'indirizzo e scrivere `email_changed`, con un rosso prima. Da fare adesso, prima dello
>   slot, se il coordinatore approva.
> - **E · 2, testo di `auth.emailRecoveryNotAvailable`** (mia chiave, la scrive E in E4b nelle 4 lingue): sì al testo di
>   E; suggerimento facoltativo «…ask your administrator for a password-reset link» (A6b: la scheda Utenti lo crea anche
>   senza email).
> - **E · 3 e X · `_url()`**: messaggi non arrivati, chiesti al coordinatore. Risposta di massima a X: `_url()` condivisa,
>   sì; casa proposta `config/__init__.py` come `env_url(name)`, con l'OK di H.

#### A7c — Nessun indirizzo email nei log del profilo ✅ (2026-10-16, 07:46–08:25)
> - **Approvato** dal coordinatore (07:46): togliere l'indirizzo, `email_changed=True/False`, rosso prima, commit
>   separato prima dello slot di `all-backend` delle 08:50. Regola nuova dei controlli leggeri (07:48): carico a 1 minuto
>   sotto 50, altrimenti 60 s d'attesa; un timeout di Vitest sotto carico si rilancia da solo prima di dirlo rosso.
> - **Rossi** (`test-author`, solo scrittura): `test_services/test_user_profile.py` UPROF-001 (×4: solo email, username
>   ed email, solo username, la stessa email) e UPROF-002 (guardia: il rifiuto «Email already registered»);
>   `test_api/test_profile_api.py` PROF-017, PROF-018 e PROF-019 (guardia: la password sbagliata), in-process su un DB
>   privato con `capture_logs` e `caplog` e un canarino. Osservati (08:11–08:14): `services user-profile` 43 ✅ / 4 ❌,
>   `api profile` 22 ✅ / 2 ❌, tutti sulla verifica «nessun indirizzo» (l'evento portava `email=`); le guardie verdi.
> - **Cura**: `user_service.update_profile()` calcola `email_changed` e lo scrive al posto di `email`; la rotta scrive
>   `email_changed=email_changes`. `ruff` e `black` puliti sui 4 file.
> - **Verdi** (`nice`, carico sotto 50): `services user-profile` ✅ 47; `db populate --force`; `api profile` ✅ 24.
>   Porta 6182 libera.
> - **Doc**: `security.md`, «Changing the Email»: un punto «The log» e la riga dei test (PROF-010…019, UPROF-001/002).
>   Nessun link o ancora nuovi: niente `mkdocs build` (il prossimo lo copre).
> - **Fuori perimetro, trovato dal `test-author`** → backlog **A-22**: i tre «Login failed…» di `auth.py` (~160–167)
>   scrivono `username=request.username`, che può essere un indirizzo (il login accetta l'email). Lo scan AST non lo
>   vedeva (la chiave è `username=`). Proposta al coordinatore: un lotto piccolo subito dopo, o dentro A8.

#### Ripresa dopo lo STOP e il riavvio (2026-10-16, 10:32)
> - STOP del developer alle 08:46: lo script dei controlli era nell'attesa del carico (nessun runner, porta libera); fermato
>   con `kill -TERM` sullo script e sul suo `sleep`. Al via (10:32) HEAD `356a01d4d`, aperto solo il file dei rossi di
>   A-22.
> - **Fuori pista — la macchina è stata riavviata** (uptime 31 minuti alle 10:34): `/tmp` è stata svuotata. Persi gli
>   script e i log di prova (`/tmp/libreFolio_*`, già riassunti in questo piano) e la cartella della corsia
>   `/tmp/librefolio-r13-a`, che `db populate --force` ricrea. Ricreati lo script dei controlli e quello di A-22.

### P18 — Indirizzi email unici senza distinzione di maiuscole — contratto proposto (2026-10-16, 10:45)
> **Decisione del developer** (P18, 10:32): gli indirizzi sono unici indipendentemente dal maiuscolo/minuscolo. Lotto dopo
> A-22, contratto prima del codice.
>
> **Stato verificato** (`356a01d4d`):
> - Database: `users.email` `UNIQUE` più `ix_users_email` (001), tutti e due esatti: `Alice@example.com` e
>   `alice@example.com` oggi sono due account. `EmailStr` toglie gli spazi e mette in minuscolo il dominio, non la parte
>   locale; la CLI `user create` non valida l'indirizzo.
> - Confronti esatti: `user_service.get_user_by_email` (unicità in `create_user`: registrazione, invito, primo account,
>   F02, CLI `create-user`/`create-superuser`; unicità in `update_profile`; F02 `_follow_variables`);
>   `get_user_by_username_or_email` (login, e i flussi di E «password dimenticata» `flows.py:278` e «manda di nuovo il
>   link» `verification.py:371`); il «cambio d'email» deciso con `!=` nella rotta (A6e, la password) e nel servizio
>   (`email_changed`, la verifica, le sessioni); F02 `_follow_variables`.
> - Inviti: nessun confronto (l'indirizzo dell'invito è un suggerimento; la registrazione che lo usa controlla l'unicità).
> - E usa già `strip().casefold()` come chiave della casella in 5 punti (limiti, avviso del cambio, verifica), e non
>   manda l'avviso per un cambio di sole maiuscole (`flows.py:348`).
> - Alembic: tutte le migrazioni di un avvio in una transazione (`env.py`, nessun `transaction_per_migration`); testa 008.
> - Prova a mano (SQLite 3.54, in memoria): un indice unico su `lower(email)` rifiuta `Alice@`/`ALICE@` dopo `alice@`, e
>   la ricerca `lower(email) = lower(?)` lo usa; non vede `Émile@` contro `émile@` (`lower()` di SQLite piega solo A–Z).
>
> **Contratto proposto**:
> - **C1 · La regola, in un posto**: due indirizzi sono lo stesso se coincidono a parte le maiuscole di A–Z, come le piega
>   `lower()` di SQLite; `same_email(a, b)` e `email_fold(address)` in `user_service`. Le lettere fuori da ASCII si
>   confrontano come scritte: limite documentato (Gmail e Outlook non accettano parti locali non ASCII).
> - **C2 · Il database**: un indice unico `ux_users_email_lower` su `lower(email)`, dichiarato sul modello (così
>   `create_all` dei test e il validatore dello schema lo vedono) e creato dalla migrazione 009. Nessuna colonna nuova:
>   ogni scrittura, SQL a mano compreso, è coperta; l'indice esatto di oggi resta.
> - **C3 · Le ricerche**: `get_user_by_email` e la metà email di `get_user_by_username_or_email` confrontano
>   `lower(email) = lower(:valore)`: login, «password dimenticata», «manda di nuovo il link», unicità in registrazione,
>   invito, profilo, F02 e CLI seguono senza toccare i file di E. Lo username resta com'è (esatto).
> - **C4 · Le scritture**: l'indirizzo si salva come scritto. Uno che differisce da quello di un altro account solo per le
>   maiuscole è rifiutato come oggi un duplicato esatto («Email already registered», `ACCOUNT_EXISTS`).
> - **C5 · Un cambio di sole maiuscole del proprio indirizzo** è lo stesso indirizzo, come per l'avviso di E: si salva la
>   forma nuova; niente password, nessuna sessione chiusa, la verifica resta, `email_changed` falso. Alternativa più
>   stretta: trattarlo come un cambio (password, sessioni, verifica). La scheda Profilo chiede la password a ogni
>   modifica del testo: resta così (più stretta, innocua).
> - **C6 · Migrazione `009_users_email_unique_ignoring_case`** (giù 008): prima legge `id`, `username`, `email` di ogni
>   account e li raggruppa con la stessa piega; se un gruppo ha più di un account si ferma e non scrive niente,
>   nominando ogni gruppo per id e username, **mai gli indirizzi** (regola di E), con il rimedio. Altrimenti crea
>   l'indice. Il downgrade lo toglie. Il controllo di B sul ripristino di un backup la esegue anche lui.
> - **C7 · Il rimedio, `./dev.py user set-email <username> <indirizzo>`**: valida l'indirizzo (`EmailStr`), rifiuta uno
>   già di un altro account (C1), lo cambia come un cambio d'email (verifica azzerata, sessioni chiuse: `update_profile`).
>   Funziona anche sul database che la 009 ha rifiutato: il modello non ha colonne nuove.
> - **Rossi** (prima del codice): servizi (`user-profile`, `registration`, `admin-bootstrap`: varianti di maiuscole
>   rifiutate o riconosciute, il cambio di sole maiuscole), API (`registration`, `auth`: login per email in un'altra
>   forma; `profile`; il «password dimenticata» di E in un'altra forma), CLI (`dev-cli-image`: `create-user` e
>   `set-email`), `db migration-009` (DB nuovo con l'indice; DB con duplicati: si ferma, nomina id e username, nessun
>   indirizzo, niente scritto; dopo `set-email` passa), `db schema-validation`.
> - **Doc e CHANGELOG**: `access_control`, `security` (C5), `admin/cli_tools` (`set-email`), la nota d'aggiornamento;
>   ⚠️ «Gli indirizzi email sono unici senza distinzione di maiuscole: un aggiornamento si ferma se due account hanno lo
>   stesso indirizzo a parte le maiuscole, e li nomina; `user set-email` li separa».
> - **Alternativa** (B): una colonna `email_key` = `strip().casefold()` (la chiave di E) con indice unico, tenuta da eventi
>   del modello: unicità completa anche fuori da ASCII, ma una colonna su `users`, il riempimento nella migrazione, e un
>   rimedio che non può usare il modello su un database non migrato.
> - **Domande per il developer** (proposta per prima): C5 (il cambio di sole maiuscole è lo stesso indirizzo);
>   C1 (il limite ASCII, oppure l'alternativa B); lo username resta con le maiuscole che distinguono (Alice ≠ alice),
>   oppure la stessa regola, nel lotto di A-21.
> **Approvato** dal coordinatore (10:49), con i dettagli decisi da lui, «da rivedere» (il developer considera ovvia la
> regola): C5 sì (un cambio di sole maiuscole del proprio indirizzo è lo stesso indirizzo); C1 sì (indice unico su
> `lower(email)`, senza colonna nuova, il limite ASCII accettato e documentato). La **migrazione 009** è riservata ad A
> (nessun altro ramo ha migrazioni dopo la 008). Ordine: A-22, poi P18, poi A-21.
> **A-21 si allarga** (dopo P18): gli username senza distinzione di maiuscole, con la stessa regola; e la nota di E: uno
> username può contenere `@`, quindi il login e la «password dimenticata» per email possono finire sull'account
> sbagliato (`get_user_by_username_or_email` con `.first()` e nessun ordine). Proposta: username nuovi senza `@`, e un
> identificativo con `@` cerca solo l'email; per gli username esistenti con `@` prima un'analisi, nessun cambio
> silenzioso.

#### A-22 — Nessun identificativo digitato nei log dei login falliti ✅ (2026-10-16, 08:25–11:15)
> - **Approvato** (08:24): `user_id` quando l'account esiste, niente quando non esiste; rosso prima.
> - **Rossi** (`test-author`, solo scrittura, avvisato del merge di E5b aperto a metà): `test_auth_api.py`, classe
>   `TestSignInLogsNoTypedIdentifier` in fondo al file (solo aggiunte, +326/−0, le righe di E5b intatte): LOGIN-027
>   (indirizzo sconosciuto), 028 (username sconosciuto), 029 (password sbagliata, per indirizzo), 030 (per username: i
>   campi dell'evento sono esattamente `{user_id}`), 031 (account disattivato, per indirizzo, 403 `ACCOUNT_DISABLED`);
>   guardie LOGIN-032 (login riuscito) e 033 (account in attesa della verifica di E5b, 403 `EMAIL_NOT_VERIFIED`, che
>   logga solo `user_id`). In-process su un DB privato, catture `capture_logs` e `caplog` con canarino; la cache del
>   «dummy hash» di bcrypt isolata, così LOGIN-024 (costo vero) resta valido.
> - **Controlli sulla revisione fusa con E5b** (`356a01d4d`, prima dello STOP e dopo la ripresa, `nice`, carico sotto
>   50): `api sync` ✅; `services registration` ✅ 147, `admin-bootstrap` ✅ 156, `email-verification` ✅ 124;
>   `db populate --force`; `api admin-setup` ✅ 42, `registration` ✅ 96, `email-verification` ✅ 49, `users-admin` ✅
>   64; `front check` ✅ 0 errori; `api auth` 90 ✅ / 5 ❌, i cinque rossi di A-22 e solo loro (l'evento portava
>   `username=`).
> - **Cura**: in `login()` i tre «Login failed…» non portano più `username=request.username`: niente per «user not
>   found», `user_id` per «wrong password» e «user inactive». `ruff` e `black` puliti.
> - **Verde**: `api auth` ✅ 95 (11:10–11:11). Porta 6182 libera.
> - **Doc**: `security.md`, «How Login Works»: un paragrafo sui log dei login rifiutati.
> - **Backlog**: A-22 ✅; A-21 allargata (username senza distinzione di maiuscole, `@`, ricerca per email); A-23 nuova
>   (da H-19, l'«address probe» che risponde 500).

#### P16 — Risposta del developer su A7 (2026-10-16, 11:15)
> - **Cloud**: il token lo crea il pannello, lo passa in `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`, e il pannello costruisce e
>   manda il link lui («ci può aggiungere più informazioni»): A7a lo fa già.
> - **Self-hosted con le variabili**: LibreFolio genera il token, scrive il link nel log una volta, e lo manda per email se
>   c'è l'email. Senza email: il link solo nel log, `./dev.py user setup-link` lo riemette. Verificato sul codice (11:20):
>   `deliver_setup_link()` scrive sempre il link a `WARNING`, poi prova l'email e, se non può, logga «not emailed». In
>   più: l'email chiede anche `LIBREFOLIO_PUBLIC_URL` (regola di E), senza la quale il log porta il solo percorso con la
>   nota; `setup-link` stampa, non manda email. Senza variabili F02 non cambia niente (il primo account è l'admin, A6d).
> - Le decisioni notturne (b) e (c) restano. **(d) No**: `/auth/setup` non entra in `ALLOWED_WHEN_BLOCKED` («bloccata
>   vuol dire bloccata finché non paga», come per il ripristino, P7): sull'istanza bloccata risponde 401.
> - **Doc di (d)** (nel prossimo checkpoint): `admin/hosting_providers` (un punto nella sezione F02, e `POST
>   /api/v1/auth/setup` fra le chiamate aperte che rispondono 401 da bloccata), `security.md` (la riga delle rotte
>   pubbliche fuori dalla lista), `access_control.md` (un paragrafo dopo «The setup»). La docstring di
>   `instance_block.py` (file di H) elenca le stesse rotte: chiesto al coordinatore chi la aggiorna.

#### P18.1 — Rossi scritti, parcheggiati per `all-backend` (2026-10-16, 10:55–11:30)
> - **Rossi** (due `test-author`, solo scrittura):
>   - API: `test_registration_api.py` LIVE-004 ×3 (registrazione con una variante di maiuscole → 400 «Email already
>     registered»), LIVE-005 ×2 (guardie), LIVE-006 (login per indirizzo in un'altra forma); `test_profile_api.py`
>     PROF-020 ×2 (cambio di sole maiuscole del proprio indirizzo: 200, senza password, nessuna sessione chiusa), PROF-021
>     (l'indirizzo di un altro account in un'altra forma → 400), PROF-022 (guardia A6e).
>   - Servizi: `test_services/test_email_case.py` nuovo, ECASE-001…051 (`email_fold`, `same_email`, l'indice, le
>     ricerche, `create_user`, `register_user`, C5, F02).
>   - Migrazione: `test_db/test_migration_009_email_case.py` nuovo, MIG009-001…011 (rifiuto con id e username e nessun
>     indirizzo, niente scritto; il rimedio `cmd_set_email` su un DB a 008; downgrade; un'installazione 1.1).
>   - CLI: `test_dev_cli_image.py` IMG-032, IMG-033 e 033b…e (`create-user`, `set-email`).
> - **Bozze** (cartella di sessione `work/p18/`): `apply_p18.py` (modello: indice `ux_users_email_lower` su
>   `lower(email)`; `user_service`: `email_fold`, `same_email`, ricerche con `lower()`, C5 in `update_profile`; la rotta
>   del profilo con `same_email`; F02 `_follow_variables`; CLI `set-email`) e la migrazione 009. Combaciano a secco. Già
>   coprono i tre contrasti segnalati dai `test-author` (l'unicità che trovava l'account stesso in `update_profile` e in
>   F02, il `!=` della rotta).
> - **Decisione tecnica**: l'id della revisione diventa `009_email_unique_ignoring_case` (30 caratteri): quello del
>   contratto ne aveva 36, oltre il `VARCHAR(32)` di `alembic_version` che le suite di 005 e 008 fissano. Il
>   `test-author` aggiorna la copia parcheggiata del test.
> - **Al coordinatore** (11:32): il ripristino di B esegue le migrazioni sulla copia, quindi un backup con due account con
>   lo stesso indirizzo a parte le maiuscole sarebbe rifiutato dalla 009, e `set-email` non raggiunge la copia; e i
>   cinque `casefold` di E contro la piega solo A–Z di P18 (limite documentato).
> - **Parcheggio** (istruzione del coordinatore, come J): `git diff --binary` dei tre file di test modificati in
>   `work/p18/park/p18_reds_tracked.patch`, le due copie dei file nuovi in `work/p18/park/files/`, gli SHA-256 in
>   `sha256_dirty.txt`; `git apply -R --check`, poi `git apply -R`; i due file nuovi tolti solo dopo `cmp` con le copie.
>   Nel worktree restano solo la doc di P16 (d) e il piano.
> - **`all-backend --workers 2`** (slot 1, `nice`, 11:29–): log per unità in `work/allbackend_1115/units/`.
> - **Il test-author** ha aggiornato la copia parcheggiata di `test_migration_009_email_case.py` con l'id corto
>   (`REV_009`, i docstring, `len(script.revision) <= 32` in MIG009-001 come la suite di 008).
> - **Risposta di B** (11:35): il controllo del ripristino non mostra l'errore della migrazione, solo il codice
>   `upgrade_failed`; il messaggio di 009 sta nel log del server (`stderr`, gli ultimi 4000 caratteri di alembic). B
>   scrive la riga di doc in `admin/backup_restore` e `cli_tools` («separali sull'istanza che ha fatto il backup, poi rifai
>   il backup»); gli ho mandato il testo dell'eccezione e il comando `set-email`. Nessun codice in più in B.
> - **Risposta di E** (11:35): E usa `user_service.same_email()` in `email_changed_work` (stesso indirizzo → nessun
>   avviso) e in `confirm_email` (l'indirizzo del link contro quello dell'account), in un suo lotto dopo l'ingresso di
>   P18; tiene `strip().casefold()` per le chiavi dei limiti. Contratto di `same_email` mandato a E: pura, sincrona, senza
>   `strip`, piega solo A–Z come `lower()` di SQLite; e un cambio di sole maiuscole non raggiunge l'aggancio di E (C5).

#### Slot 1 — `all-backend --workers 2` ✅ (2026-10-16, 11:29:34–12:17:27)
> - **Revisione**: HEAD `946285a91`, con nel worktree solo la doc di P16 (d) e il piano; rossi di P18 parcheggiati.
> - **Comando**: `nice -n 10 env PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port
>   6182 --data-dir /tmp/librefolio-r13-a --workers 2 --log-dir <sessione>/work/allbackend_1115/units all-backend`.
> - **Esito**: rc=0, **7/7** («ALL BACKEND TESTS PASSED»), 47 min 48 s, carico 132 all'avvio. Quattro passate parallele
>   verdi (162 unità in 701,8 s, 48 in 919,8 s, 12 in 7,1 s, 69 API in 768,5 s); tutte le unità seriali PASSED (DB,
>   migrazioni 005–008, post-migrazione, provider FX e asset, BRIM, schema). **20 268 passati** nei log per unità, nessun
>   rosso, nessun `ReadTimeout` noto. Le righe «❌» nel log dei provider FX esterni sono stampe dei test che si
>   aspettano un errore (unità 28 passati, 21 saltati). Snapshot del DB di prova: `00_archive/test-db_20261016_121726.tar.xz`.
> - **Interruzione**: un errore del servizio ha interrotto il mio turno verso le 11:55; la prova è andata avanti da sola
>   (PID 33727) e non è stata riavviata. Porta 6182 libera alla fine (`lsof` rc=1), runner uscito.
> - **⚠️ Fuori pista** (trovato mentre aspettavo, per P18): l'indice `ux_users_email_lower` è un indice su
>   un'espressione, e SQLAlchemy 2.0.52 non lo riflette su SQLite (`get_indexes` lo salta con un avviso; misurato su un DB
>   in memoria). Quindi `db_schema_validate.py::test_indexes`, che prende i nomi attesi dal modello e quelli reali
>   dall'inspector, diventerebbe rosso dopo P18 («Missing indexes: users.ux_users_email_lower») con l'indice presente.
>   Riparazione solo nel test (i nomi reali da `sqlite_master`), affidata a un `test-author` nel lotto P18 (brief in
>   `work/p18/brief_schema_validate_repair.md`). Verificato invece che restano verdi: `test_migration_005_accounts.py`
>   (`_shape` salta l'indice da entrambe le parti, `_index_list` vede `(None,)` da entrambe), la ricostruzione
>   AUTOINCREMENT di `post_migration/autoincrement.py` (riesegue l'SQL di ogni indice da `sqlite_master`), e
>   l'autogenerate di Alembic 1.19.2 (salta gli indici su espressione su SQLite con un avviso: `db migrate` non li
>   ricrea). Nessun confronto di indirizzi negli inviti (l'indirizzo serve solo all'invio).

#### P18.2 — Rossi rimessi e osservati (2026-10-16, 12:20–)
> - **Ripristino**: `git apply --check` poi `git apply` di `park/p18_reds_tracked.patch`; i due file nuovi ricopiati.
>   SHA-256 uguali a `sha256_dirty.txt` per quattro file su cinque; `test_migration_009_email_case.py` diverso come
>   previsto (la copia parcheggiata aggiornata dal `test-author` all'id corto dopo il parcheggio).
> - **Runner** (`apply_p18_runner.py`): `db migration-009` (pure, anche nell'ordine di `db`) e `services email-case`
>   (pure). `ruff`: i 3 PLC0415 di `_backend_db.py` ci sono identici a HEAD, nessuno nuovo.
> - **Rossi osservati** (`work/p18/reds_all.sh`, `nice`, carico < 50 all'avvio; log in `work/p18/logs/`):
>   - `services email-case`: 63 rossi, 4 verdi (le guardie: ricerca per uguaglianza, mai per pattern ×2; F02 col
>     proprio indirizzo in altra forma ×2). Cause giuste: `user_service` senza `email_fold`/`same_email`, ricerche
>     esatte, nessun rifiuto delle varianti, C5 non applicato.
>   - `db migration-009`: 11 rossi su 11, cause giuste (revisione assente, nessun indice, l'upgrade va oltre gli
>     account in collisione).
> - **Riparazione del validatore** (`test-author`, solo `db_schema_validate.py::test_indexes`): i nomi reali da
>   `sqlite_master` (`type = 'index' AND sql IS NOT NULL`, la stessa query di `post_migration/autoincrement.py`) invece
>   di `inspector.get_indexes`. Provato in privato: verde prima e dopo P18 con stampe identiche prima, rosso se l'indice
>   manca davvero. `ruff`/`black` puliti. Nessun altro punto dei test riflette gli indici di `users` in modo cieco.
> - **Verificato**: `./dev.py user …` non esegue migrazioni (`user_cli.py` e `db/session.py` senza Alembic), quindi
>   `set-email` funziona su un database che la 009 ha rifiutato.
> - **Rossi osservati, seguito** (carico tornato sotto 50 alle 12:41 e alle 12:52):
>   - `utils dev-cli-image`: 9 rossi (la classe P18: `set-email` non è un comando ×7, `create` accetta una variante di
>     maiuscole ×2), 85 verdi.
>   - `api registration`: 4 rossi (LIVE-004 ×3: 201 invece di 400; LIVE-006: 401 invece di 200), 98 verdi.
>   - `api profile`: 3 rossi (PROF-020 ×2: 400 `CURRENT_PASSWORD…` invece di 200; PROF-021: 200 invece di 400), 25 verdi.
>   - **Totale 90 rossi**, tutti per la causa attesa; guardie verdi; porta 6182 libera alla fine.

#### P18.3 — Implementazione ✅ (2026-10-16, 12:55)
> - `apply_p18.py` (a secco, poi scritto): `models.py`, `user_service.py`, `auth.py`, `bootstrap_admin_service.py`,
>   `user_cli.py`; creato `backend/alembic/versions/009_email_unique_ignoring_case.py`. `ruff check` e `black --check`
>   puliti sui sei file.
> - Nessun cambio di schema dell'API (solo comportamento): `api sync` e `front check` non servono.

#### P18.4 — Verdi, doc, e tre punti emersi (2026-10-16, 12:55–)
> - **Verdi** (`work/p18/greens_all.sh`, `nice`, carico < 50): `services email-case` 67, `user-profile` 47,
>   `registration` 147, `admin-bootstrap` 156 ✅.
> - **⚠️ Fuori pista — due test di E diventano impossibili**: `services email-flows`
>   (`test_three_reset_emails_an_hour_per_mailbox_whatever_the_account`, `ONE_MAILBOX` l. 1356) e `services
>   email-verification` (`test_a_mailbox_gets_three_registration_emails_an_hour_whatever_the_account`,
>   `MAILBOX_VARIANTS` l. 166) creano quattro account sulla stessa casella in quattro forme ASCII →
>   `UNIQUE constraint failed: index 'ux_users_email_lower'`. È la regola che lavora. Proposta (al coordinatore, file di
>   E): varianti con due lettere non ASCII in maiuscolo/minuscolo diversi (una casella per le chiavi `casefold` di E,
>   quattro righe distinte per l'indice A–Z). In attesa di chi scrive.
> - **Doc** (`docs-writer`, sei pagine EN): `database/users_access.md` (ancora `#user`, regola, indice, limite ASCII, il
>   rifiuto e il rimedio), `database/index.md` (riga 009), `security.md` (sessioni, C5, `400` «in qualunque forma A–Z»,
>   test), `admin/cli_tools.en.md` (`#set-email`, `#email-case-conflict`), `admin/users.en.md` (un punto),
>   `user/settings/profile.en.md` (stessa casella con maiuscole diverse). Debito di traduzione lasciato:
>   `cli_tools`, `profile`.
> - **⚠️ Fuori pista — tre punti del `docs-writer`**:
>   1. `ProfileTab.svelte` l. 89–92 confronta l'indirizzo esatto: su un cambio di sole maiuscole la scheda chiede la
>      password, avvisa della disconnessione e tiene «Salva» spento, mentre il server (C5) non chiede nulla. Correzione
>      solo di logica, area colori IM: chiesto il via al coordinatore.
>   2. Il suggerimento Docker del messaggio di 009 (`docker compose exec`) non regge: una migrazione fallita fa
>      `sys.exit(1)` e con `restart: unless-stopped` il container riparte in ciclo. Va sostituito con `stop` + `run --rm`
>      + `start` (lo schema di `docker_advanced` per le correzioni post-migrazione); il testo nuovo andrà a B.
>   3. «Il rifiuto lascia tutto com'era?» **Verificato in privato** (`work/p18/repro_12_refusal.py`, file temporaneo,
>      motore dell'app come trappola): un'installazione 1.2 (004) con due account in collisione si ferma **a 008**.
>      Alembic su SQLite fa COMMIT dopo ogni migrazione (tracciato con il log di SQLAlchemy), quindi la mia nota «tutte
>      le migrazioni in una transazione» era sbagliata. Nessun account cambiato; `cmd_set_email` funziona a 008 e
>      l'avvio dopo arriva a 009.
> - **Risposte del coordinatore** (13:20):
>   1. I due test di E li adatto io nel lotto P18 con un `test-author`, con le varianti non ASCII, **dopo la conferma di
>      E** (senso dei test e `rcpt_tos` non ASCII nel suo SMTP finto); E mi risponde direttamente.
>   2. `ProfileTab.svelte`: **sì**, solo logica (helper `sameEmail` A–Z, `emailNeedsPassword`, la condizione del blocco
>      della password), rossi prima in `ProfileTab.test.ts`; **dopo l'aggiornamento di base** che porta IM
>      (`1248b7908`), come commit a sé. Conflitti attesi all'aggiornamento: `app_lifespan.py`, `overview.md`,
>      `security.md`, `ProfileTab.svelte`.
>   3. Suggerimento Docker: OK; testo finale mandato a B (13:18).
> - **P13 deciso dal developer: (a) + (b)** — in `TabBar` la barra scorre con la rotella verticale, con una sfumatura
>   sul bordo quando ci sono schede nascoste (maschera alfa, nessun colore); le cinque schede admin raggruppate sotto
>   «Amministrazione» con una seconda barra, tenendo `?tab=users` e gli altri link diretti. È la cornice di A8, dopo P18.
>   `TabBar.svelte` è in un'area colori: avvisare prima di toccarlo.
> - **Verdi, seguito**: `db migration-009` 11/11 ✅ (con il nuovo suggerimento Docker). **⚠️ Fuori pista**: `db
>   migration-005` 1 rosso, `test_the_models_and_the_migration_build_the_same_table[users]`. `_shape` ordina gli insiemi
>   unici di colonne e l'indice su espressione dà `(None,)` da `PRAGMA index_info` → `TypeError` in `sorted()`. Le due
>   parti hanno l'indice: è l'aiutante che si rompe prima di confrontare. L'avevo escluso a torto. Riparazione solo nel
>   test affidata allo stesso `test-author`.
> - **Suggerimento Docker cambiato** in 009: «in Docker, with the container stopped: `docker compose run --rm librefolio
>   python dev.py user set-email <username> <address>`». `ruff`/`black` puliti; testo finale a B (13:18).
> - **Doc, secondo giro** (`docs-writer`): `cli_tools.en.md` (ci si ferma alla 009, i passi prima restano, nessun account
>   cambiato, il riavvio riprende da lì), `users_access.md` e `database/index.md` (COMMIT per revisione su SQLite: resta a
>   008), `users_and_brokers.md` (`user set-email` nell'elenco dei comandi), `docker_advanced.en.md` (un riavvio non
>   aiuta finché gli account non sono separati). Nuovo debito di traduzione: `docker_advanced`, `cli_tools`.

#### ⏸️ PAUSA del developer (2026-10-16, 13:23) — stato congelato
> - **HEAD** `946285a91`, nessun merge aperto, porta 6182 libera; `greens_all.sh` fermato mentre aspettava il carico
>   (nessun test in corso).
> - **Verdi fatti**: `services email-case` 67, `user-profile` 47, `registration` 147, `admin-bootstrap` 156; `db
>   migration-009` 11. **Rossi noti**: `services email-flows` 1 e `email-verification` 1 (test di E, in attesa della
>   conferma di E per le varianti non ASCII); `db migration-005` 1 (`_shape` con `(None,)`, riparazione del
>   `test-author` in corso al momento della pausa).
> - **Da fare alla ripresa** (`greens_all.sh` dal passo `migration-005`): `db migration-005…008`,
>   `autoincrement-schema`, `post-migration`, `create`, `validate`, `populate`, `api registration`/`profile`/`auth`/
>   `users-admin`/`admin-setup`/`email-verification`, `utils dev-cli-image`; poi i due test di E, `mkdocs build` +
>   `check-links`, handoff P18. Dopo l'aggiornamento di base (IM): la correzione di `ProfileTab.svelte`.
> - **Riparazione di 005 alla pausa**: il `test-author` aveva solo letto, nessuna modifica (file intatto e coerente). Il
>   rosso `TypeError` resta. Piano pronto: `_index_list` nomina una chiave su espressione col suo testo da
>   `sqlite_master.sql`. Il suo grep non trova altri punti che ordinano `(None,)` su `users`, da confermare.
> - **Risposta di E** (alla pausa) sui due test: **il senso resta** (chiavi dei limiti `strip().casefold()`, anche dopo
>   E4c; dopo P18 è l'unico modo in cui due account condividono una casella). Usare letterali **NFC** (`\u00e4`
>   precomposta). Però **oggi il finto SMTP di E non riceve indirizzi non ASCII**: non annuncia `SMTPUTF8`, e
>   `smtplib.send_message` (`smtp.py:129`) alza `SMTPNotSupportedError`, che diventa `SEND_FAILED`. **La cura è di E**:
>   `SMTPUTF8`/`8BITMIME` nell'EHLO, i parametri dopo `MAIL FROM`, più un caso che fissa `SEND_FAILED` verso un server
>   senza `SMTPUTF8`. La fa al via; il coordinatore la ordina prima di P18 o insieme. Quindi l'adattamento dei due test
>   di E nel lotto P18 dipende da quel lotto di E.

#### P18.5 — Ripresa (2026-10-16, 14:14–)
> - **Via del developer** (14:14, dal coordinatore): riparazione di 005, il resto dei verdi (carico < 50), i controlli
>   della doc, handoff P18 con i test di E segnati in attesa del mini-lotto `SMTPUTF8` di E; poi ProfileTab dopo
>   l'aggiornamento di base con IM.
> - **Riparazione di 005** (`test-author`, solo `test_migration_005_accounts.py`, +45/−4): `_index_list` dà a una chiave
>   su espressione il suo testo da `sqlite_master.sql` (`_written_keys`, normalizzato come in 009), `(None,)` →
>   `('lower(email)',)`; tutto il resto identico (80 voci su 82 uguali, le 2 diverse sono `ux_users_email_lower`).
>   Provato in privato: il confronto `[users]` passa, e fallisce se manca l'indice da una parte, se non è unico, o se è su
>   `upper(email)`; 007 usa `_shape` solo sulle sue due tabelle; 006/008/009 importano ancora tutti i nomi.
>   `ruff`/`black` puliti. Punto cieco rimasto (non toccato): la chiave `indexes` di `_shape` viene dall'inspector, che salta
>   gli indici su espressione da entrambe le parti (vedi A-26).
> - **Un terzo test di E** impossibile con P18, trovato cercando nei test gli indirizzi uguali a parte le maiuscole:
>   `test_email_verification_api.py` EVA-016 (`MAILBOX_VARIANTS`, quattro account in attesa sulla stessa casella), gemello
>   API di EMV-043. EMA-036 (`api email`, un solo account, quattro grafie): con P18 le richieste 2 e 3 trovano l'account,
>   ma il suo limite (un link ogni intervallo) le ferma, quindi resta «una email in tutto». Nessuna collisione nei dati di
>   `db populate` né nei fixture E2E.
> - **Verdi, parte A** (`work/p18/greens_resume_a.sh`): `db create` ✅, `db validate` 17 ✅ (la riparazione del
>   validatore), `db autoincrement-schema` 4 ✅, `db post-migration` 41 ✅ (la ricostruzione AUTOINCREMENT riporta
>   l'indice), `db populate` ✅; `api registration` 102 ✅ (LIVE-004…006), `api profile` 28 ✅ (PROF-020…022), `api
>   auth` 95 ✅, `api users-admin` 64 ✅, `api admin-setup` 42 ✅, `api email` 160 ✅ (EMA-036 compreso, come previsto),
>   `utils dev-cli-image` 94 ✅ (IMG-032/033); `api email-verification` 48 ✅ + 1 rosso atteso, EVA-016 (`UNIQUE
>   constraint failed: index 'ux_users_email_lower'`, A-24). Porta 6182 libera alla fine (14:50).
> - **Backlog**: A-10 allargata col debito di traduzione di P18; nuove A-24 (i tre test di E), A-25 (ProfileTab), A-26 (il
>   punto cieco di `_shape`).
> - **Verdi, parte B** (`work/p18/greens_resume_b.sh`, dopo la riparazione di 005): `db migration-005` 25 ✅ (il
>   confronto `[users]` compreso), `migration-006` 37 ✅, `migration-007` 29 ✅, `migration-008` 23 ✅, `migration-009` 11
>   ✅. Porta libera (14:51).
> - **Doc** (`work/p18/docs_checks.sh`): `mkdocs build` (`--strict`) ✅ in 39 s, 3 076 URL relativi risolti;
>   `mkdocs check-links` ✅ 97 link. `mkdocs translate-validate` sulle quattro pagine tradotte toccate: 168 errori, quasi
>   tutti debito già noto (A-10: le sezioni di A5–A7a); di P18 le ancore `#set-email` e `#email-case-conflict` (×3
>   lingue), il blocco di codice nuovo di `cli_tools`, la frase di `docker_advanced`, il punto di `profile`. Il build
>   stretto resta verde.
> - `git diff --check` pulito; `ruff`/`black` puliti sui file toccati.

#### P18.6 — Handoff FROZEN 🧊 (2026-10-16, 14:55)
> - HEAD `946285a91`, nessun merge aperto; 24 file modificati + 3 nuovi (923+/46−); porta 6182 libera.
> - Rossi attesi, fuori da questo checkpoint: i tre test di E (A-24), in attesa del mini-lotto `SMTPUTF8` di E.
> - Non eseguiti: `all-backend` (da fare in uno slot dopo l'ingresso, P18 cambia lo schema), E2E e `front check` (nessun
>   cambio del frontend), `api sync` (nessun cambio dello schema dell'API).
> - Dopo l'aggiornamento di base con IM: A-25 (ProfileTab), commit a sé.

#### P18.7 — P18 committato, aggiornamento di base, A-24 (2026-10-16, 15:02–)
> - **Commit del coordinatore**: `1fdeabaa4` (feat, 15 percorsi), `eb419cbcb` (docs, 10), `3376b9203` (journal).
> - **Merge aperto dal coordinatore**: `git merge 12cd3c2e0` (dev con i lotti di H e P17, Z5/Z-13, W-B30/36b, i colori
>   AF/IM/DV/BK/TR, e il finto `SMTPUTF8` di E, `7d51c21af`). Tre conflitti risolti tenendo le due parti:
>   - `services/platform/app_lifespan.py`: dopo `global-settings` sia `admin-bootstrap` (F02) sia
>     `plugin-secrets-check` (H-15), **in quest'ordine**: STEP-001 vuole `admin-bootstrap` subito dopo
>     `global-settings`, e il test di H vuole solo `plugin-secrets-check` fra `global-settings` e `scheduler`. Import di
>     entrambe presenti; `ruff`/`black` puliti.
>   - `developer/architecture/overview.md`: i due passi 12 e 13, numeri seguenti spostati di uno (fino a 17).
>   - `developer/architecture/security.md`: la frase dei segreti di H (con `LIBREFOLIO_WAKE_TOKEN` e le variabili dei
>     plugin) più `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` (letto con `env_secret`, verificato in `config/accounts.py`).
> - **File cambiati dalle due parti, fusi da soli, controllati**: `auth.py` (la riga di H `client_address(http_request)`
>   a 277 e il suo import, il mio `same_email` a 383), i registri del runner (nessuna unità né funzione doppia; il doppio
>   `all` di `_backend_api.py` c'è già in entrambi i genitori), le pagine admin e di architettura (nessuna ancora o titolo
>   doppio, recinti pari, nessun marcatore), `.env.example` (nessuna variabile doppia, le tre di F02 presenti). Alembic:
>   una sola testa, `009_email_unique_ignoring_case`.
> - Messe in stage **solo** le tre risoluzioni; nessun file non fuso.
> - **A-24** (i tre test di E) affidato a un `test-author`, delta a sé non in stage: varianti NFC con le maiuscole
>   diverse solo nelle lettere non ASCII, la costante della casella dal `casefold`, le asserzioni su `rcpt_tos` intatte,
>   EMF-056 non toccato (note di E in `work/p18/a24_adaptation_notes.md`).
> - **Controlli sulla revisione combinata** (`work/p18/greens_combined_c1.sh`, log in `work/p18/logs/combined/`), in
>   corso.
> - **A-24 fatto dal `test-author`** (delta a sé, non in stage, 3 file +24/−12; `ruff`/`black` puliti):
>   - `test_email_flows.py` EMF-038: `ONE_MAILBOX` = quattro grafie di `zq-shäröd@example.com` diverse solo nel
>     maiuscolo di `ä`/`ö` (`\u` escape, come `INTERNATIONAL_RECIPIENT` di E in EMD-046); precondizioni: una chiave
>     `casefold`, quattro chiavi di `user_service.email_fold`.
>   - `test_email_verification.py` EMV-043 e `test_email_verification_api.py` EVA-016: `MAILBOX_VARIANTS` = quattro
>     grafie di `zq-vïç@example.com` (`MAILBOX` è il loro `casefold`), con la precondizione di E
>     `{w.casefold() for w in MAILBOX_VARIANTS} == {MAILBOX}` e quella A–Z; nel file API aggiunto `user_service`
>     all'import esistente.
>   - Asserzioni su `rcpt_tos` intatte. EMV-044 usa `MAILBOX_VARIANTS[0]` e `MAILBOX`: il senso resta (il limite conta
>     la chiave `casefold`). EMF-056 non è in questo albero (è solo nel ramo di E).
>   - Provato in privato: tutte NFC; sullo schema vero quattro righe accettate, le vecchie grafie rifiutate da
>     `ux_users_email_lower`; `EmailStr` le lascia intatte; `smtplib` con `SMTPUTF8` le porta esatte.
> - **Nota di W per la 009** (C-97, issue #43, 16:20, chiesta dal coordinatore): il docstring della 009 diventa due punti
>   numerati come la 004: «1.» P18 (il testo di prima) e «2.» «Quantities keep 10 decimal places and prices 12 (C-97,
>   issue #43): no DDL, no data step», testo di W alla lettera. Prima riga (`script.doc`): «Release 1.3: email addresses
>   unique regardless of case (P18); the decimals of C-97 need no DDL». Nessun test fissa il docstring; `ruff`/`black`
>   puliti, Alembic una testa. Detto a W (senso invariato).
> - **Combinata, parte 1** (`greens_combined_c1.sh`): `services` `email-case` 67, `user-profile` 47, `registration`
>   147, `admin-bootstrap` 156 (l'ordine dei passi), `app-lifecycle` 44; `db` `create`, `validate` 17,
>   `autoincrement-schema` 4, `post-migration` 41, `migration-005…009` 25/37/29/23/11, `populate`; `api`
>   `registration` 102, `profile` 28, `auth` 95, `users-admin` 64, `admin-setup` 42, `email` 160: tutto ✅.
>   **⚠️ Fuori pista**: `utils dev-cli-image` fermato dal runner al tetto di 600 s con il carico a ~65 (80 su 94 passati,
>   nessun rosso; i 14 restanti comprendono la classe P18). Verdetto (test-triage): lentezza dell'ambiente, non un
>   difetto; a carico 48 la stessa unità fa 226 s. Rifatta in coda alla parte 2 con avvio sotto carico 40.
> - **Combinata, parte 2** (`greens_combined_c2.sh`, con A-24 e il docstring nuovo della 009): `db migration-009` 11,
>   `services email-flows` **155/155** e `services email-verification` **124/124** (prima un rosso ciascuna), `db
>   populate`, `api email-verification` **49/49** (EVA-016 verde), `mkdocs build --strict` ✅ (101 s, 3 076 URL),
>   `check-links` ✅ 97, `utils dev-cli-image` **94/94** in 413 s (avvio a carico 37). Porta libera alle 16:55.
>   **Combinata verde.**
> - **A-27** (dalla revisione di sicurezza di E, E6.9, via il coordinatore, 16:50): un cambio dell'indirizzo o della
>   password chiude le sessioni ma non revoca i link di reset vivi. Proposto lotto a sé subito dopo questo giro, prima
>   dello slot `all-backend`; tre punti (`update_profile` su un cambio vero, la rotta `change-password`, e
>   `reset_password` della CLI, che ha lo stesso buco), con `token_service.revoke_tokens(…, purpose=PASSWORD_RESET)`
>   come già fanno `create_password_reset` e `complete_password_reset`.

### A-25 — La scheda Profilo e il cambio di sole maiuscole — contratto (2026-10-16, 15:30)
> Approvato nell'impostazione dal coordinatore (13:20): solo logica, nessuna classe, rossi prima in `ProfileTab.test.ts`,
> dopo l'aggiornamento di base con IM, commit a sé. Area colori IM: il file è libero (IM è entrato).

- **C1 · La regola, una volta sola nel frontend**: `frontend/src/lib/features/auth/emailCase.ts`, accanto a
  `passwordRules.ts` (decisione 37), con `emailFold(address)` (A–Z → a–z e nient'altro, come `lower()` di SQLite e
  `user_service.email_fold`) e `sameEmail(a, b)`. Pura, sincrona, niente `trim`. Test unitari in `emailCase.test.ts`.
- **C2 · Che cosa resta «modificato»**: `emailModified` resta il confronto esatto. Un cambio di sole maiuscole si salva
  (il server conserva la nuova forma), quindi la riga resta evidenziata e «Salva»/«Annulla» restano offerti.
- **C3 · Quando serve la password**: `emailChangesAddress = emailModified && !sameEmail(editedEmail, originalEmail)`.
  - `emailNeedsPassword = emailChangesAddress && emailPassword === ''`.
  - Il blocco della password attuale e il suo avviso («gli altri dispositivi verranno disconnessi», riga ~459) solo con
    `emailChangesAddress`.
  - La password digitata si svuota quando il cambio smette di cambiare l'indirizzo (oggi: quando smette di essere
    modificato).
- **C4 · Che cosa si manda**: per un cambio di sole maiuscole `{email}` senza `current_password`, nel salvataggio della
  riga e in «salva tutto»; per un cambio vero, come oggi `{email, current_password}`.
- **C5 · Il limite ASCII anche qui**: `Émile@` → `émile@` è un indirizzo diverso: la password si chiede.
- **Rossi** (`test-author`, `ProfileTab.test.ts` più `emailCase.test.ts` nuovo): sole maiuscole → nessun campo
  password, «Salva» acceso, payload senza `current_password`; da un cambio vero a uno di sole maiuscole la password si
  svuota e non parte; non ASCII → password chiesta; guardie: un cambio vero chiede ancora la password (i test esistenti).
- **Doc**: una frase in `user/settings/profile.en.md` («Only the capitals changed»: nessuna password). Debito di
  traduzione, nessun timbro.
- **Prove**: `vitest` dei due file, `front check`; E2E `settings` se il cambio dell'indirizzo vi è coperto.

### A-27 — I link di reset vivi muoiono con un cambio dell'indirizzo o della password — contratto (2026-10-16, 17:05)
> Dalla revisione di sicurezza di E (E6.9), tramite il coordinatore; ambito a tre punti approvato dal coordinatore
> (17:00). Base: `e4811dab3` (merge `1ca7a27c8` più A-24, nota C-97, giornale), albero pulito.

- **C1 · Quando**: nella stessa transazione del cambio, in tre punti:
  1. `user_service.update_profile` su un cambio **vero** dell'indirizzo (`not same_email(...)`, P18): vale per
     `PUT /auth/profile` e per `./dev.py user set-email`;
  2. la rotta `POST /auth/change-password` (`auth.py`, prima del `commit`, accanto a `end_sessions`);
  3. `user_service.reset_password` (CLI `user reset`), prima del `commit`.
- **C2 · Che cosa**: ogni link `PASSWORD_RESET` vivo dell'account (non consumato, non revocato), chiunque l'abbia creato
  (la «password dimenticata» o un admin), con `token_service.revoke_tokens(session, user_id=…,
  purpose=AccountTokenPurpose.PASSWORD_RESET)`, come già fanno `create_password_reset` e `complete_password_reset`.
  Nient'altro: inviti, link di verifica e di setup restano (la verifica guarda già l'indirizzo, `confirm_email`).
- **C3 · Quando no**: un cambio di sole maiuscole dell'indirizzo (C5 di P18: non è un cambio), un cambio del solo
  username, un rifiuto (indirizzo occupato, password attuale sbagliata, password debole, stessa password): nessun link
  revocato, nulla scritto.
- **C4 · Log**: quello di `revoke_tokens` («Account tokens revoked», `count`, `user_id`, `purpose`), nessun indirizzo.
- **Rossi** (`test-author`): in-process in `test_services/test_session_version.py` (`reset_password`, `update_profile`);
  via HTTP sulla corsia in `test_api/test_session_revocation_api.py` (`change-password`, `PUT /auth/profile`): un link
  creato prima dall'API admin (`POST /users/{id}/password-reset-link`) dopo il cambio è morto (`POST /auth/tokens/inspect`
  e `POST /auth/password-reset`); guardie C3.
- **Doc**: `developer/architecture/security.md` (tabella delle sessioni, link di reset), `admin/users.en.md` o
  `cli_tools` (`user reset`), `user/settings/profile.en.md` (una frase). CHANGELOG: proposta 🔒.

#### A-27.1 — Rossi scritti (2026-10-16, 16:58–17:20)
> - **`test-author`**, solo scrittura, due file già registrati:
>   - `test_services/test_session_version.py`: contratto 7 nel docstring, sezione «7. A-27». Rossi: `reset_password`;
>     cambio vero dell'indirizzo `[another-address]` e `[a-letter-outside-a-z-in-capitals]` (émile → Émile, un cambio
>     vero per P18). Guardie: le maiuscole dell'indirizzo proprio, lo username da solo, un rifiuto (l'indirizzo di un
>     altro, anche in maiuscole). In ogni test: i due link vivi dell'account (uno suo, uno dell'admin) da revocare; un
>     link speso e uno revocato con i loro tempi, un link di verifica e uno di setup vivi, un invito dell'account e il
>     link vivo di un altro account da lasciare com'erano.
>   - `test_api/test_session_revocation_api.py`: classe `TestTheResetLinksEndWithThePasswordOrTheAddress`, REVOKE-003
>     (`change-password`) e REVOKE-004 (`PUT /auth/profile`) rossi; guardie REVOKE-005 (maiuscole), REVOKE-006 ×3
>     (password attuale sbagliata, debole, uguale), REVOKE-007 ×2. Link creati dall'API admin come `e2e_test_admin`.
> - **Il `test-author` ha confermato in-process che il buco è sfruttabile**: dopo il cambio, `POST /auth/password-reset`
>   col vecchio link risponde 200 e imposta una password nuova.
> - **Nota di W, D5** (17:05): nel punto 2 del docstring della 009 il costo unitario `cost_basis_override` (anche lui
>   `NUMERIC(24, 12)`), alla lettera; il testo di prima era già nel commit `bbe6c35da`, quindi la modifica va nel
>   prossimo checkpoint come commit a sé. `ruff`/`black` puliti.
> - Bozza della correzione pronta (`work/a27/apply_a27.py`, a secco pulita).

#### A-27.2 — Sosta del coordinatore, doc e runner (2026-10-16, 17:22–)
> - **Sosta** (coordinatore, 17:22, fino a ~17:45: gallery completa dei colori, carico 130–170): nessun controllo nuovo.
>   Il mio `units.sh red` stava solo aspettando il carico, nessun test partito: fermato. Porta libera.
> - **Runner**: le descrizioni di `services session-version` e `api session-revocation` nominano A-27 (`ruff` pulito).
> - **Doc** (`docs-writer`, senza build): `security.md` (paragrafo sotto la tabella delle sessioni, «The sessions.» del
>   cambio dell'indirizzo, rimando in «Links in Use», riga dei test), `access_control.md` («Revoked» nei link di reset;
>   più il punto «Password reset» di `user reset`, scritto da me), `admin/users.en.md` (🔒), `admin/cli_tools.en.md`
>   (`user reset`, il ⏱️ dei link, `set-email`), `user/settings/profile.en.md` (una frase per l'indirizzo e una per la
>   password). Debito di traduzione: `cli_tools`, `profile`.
> - **Per E (E4)**: `security.md` «Only an administrator, or whoever runs the server, issues a link» e `access_control.md`
>   «Issued by» saranno incompleti quando E4 accenderà la «password dimenticata» (`FORGOT_PASSWORD_HELD`): da dire nel
>   handoff.

#### A-27.3 — Rossi osservati, correzione, verdi (2026-10-16, 17:52–)
> - **Via** del coordinatore (17:52). **Rossi osservati** (`work/a27/units.sh red`, carico 17 all'avvio): `services
>   session-version` 3 rossi + 51 verdi (i tre del contratto 7, causa giusta: i due link ancora VALID e `revoked_at`
>   vuoto dopo il cambio); `api session-revocation` 2 rossi (REVOKE-003, REVOKE-004) + 9 verdi. Porta libera.
> - **Correzione** (`work/a27/apply_a27.py`, a secco poi scritta): `token_service.revoke_tokens(session, user_id=…,
>   purpose=AccountTokenPurpose.PASSWORD_RESET)` in `update_profile` (dentro `if email_changed:`, dopo `end_sessions`,
>   dopo ogni rifiuto), in `reset_password` (prima del `commit`) e nella rotta `change-password` (prima del `commit`).
>   `ruff`/`black` puliti; 8+/2−.
> - **Verdi** (`work/a27/greens.sh`): in corso. `all-backend` nello slot 1 dopo H (~18:45), sul worktree con A-27 verde,
>   poi l'handoff (coordinatore, 17:56).
> - **Verdi fatti** (17:59–18:23, carico < 50 a ogni avvio): `services session-version` 54 ✅ (i 3 rossi verdi),
>   `services user-profile` 47 ✅, `services email-flows` 155 ✅, `db populate` ✅, `api session-revocation` 11 ✅
>   (REVOKE-003/004 verdi), `api profile` 28 ✅, `api auth` 95 ✅, `api users-admin` 64 ✅, `api email` 160 ✅;
>   `mkdocs build --strict` ✅, `check-links` ✅ 97. Porta libera; `git diff --check` pulito.
> - **`all-backend --workers 2`** nello **slot 2** (il coordinatore l'ha liberato, 18:20), avviato alle 18:24 sul
>   worktree `e4811dab3` + A-27 + la D5 di W nella 009 (`work/allbackend_a27/`).
> - **Esito** (18:23:39–18:53:56): rc=0, **7/7** «ALL BACKEND TESTS PASSED», 30 min 13 s; quattro passate parallele verdi
>   (166 unità in 448 s, 48 in 348 s, 12 in 8 s, API in 507 s), tutte le seriali PASSED; **20 767 passati** nei log per
>   unità, nessun rosso. Copre P18 + A-24 + A-27 (e la 009 con la nota di W). Porta libera.

#### A-27.4 — Handoff FROZEN 🧊 (2026-10-16, 18:56)
> - HEAD `e4811dab3`, nessun merge aperto; delta di A-27 + la D5 di W + giornale, `git diff --check` pulito.
> - Prossimo, dopo il commit del coordinatore: A-25 (ProfileTab), brief dei rossi in `work/a25_brief_reds.md`.

#### A-27.5 — A-27 committato, secondo aggiornamento di base (2026-10-16, 18:55–)
> - **Commit del coordinatore**: `cf6b03b8f` (fix), `2d8f1b449` (docs), `9e9e62175` (009 D5), `546295d77` (giornale).
> - **Merge aperto dal coordinatore**: `dev_release2` `0d20399cc` (C-97a, X-R28, H-12, CP-13a, AF, DV…), MERGE_HEAD
>   `81bc305b9`. Due conflitti, risolti tenendo le due parti:
>   - `backend/app/config/accounts.py`: X ha tolto `_url` per `env_url` (più severo) in `public_url`/`billing_url`; il mio
>     lato aveva il blocco F02 subito dopo `billing_url`. Risoluzione: `billing_url` di X (`env_url`) più tutto F02; i due
>     import da `backend.app.config` uniti in una riga. Nessuna chiamata a `_url` rimasta. `LIBREFOLIO_SUPPORT_URL` sta
>     in `config/platform.py` (di X), non qui. `ruff`/`black` puliti.
>   - `developer/architecture/settings.md`: la frase di X su `LIBREFOLIO_SUPPORT_URL` («does not either») dopo quella
>     delle variabili che non fermano l'avvio, poi la mia sulle `LIBREFOLIO_ADMIN_*` che lo fermano.
> - **Fusi da soli, controllati**: `db/models.py` (`func` e `ux_users_email_lower` accanto ai `RealDecimal` di C-97a),
>   `db_schema_validate.py` (la mia lettura da `sqlite_master` in `test_indexes`), `database/index.md` (riga 009 e
>   C-97), `.env.example` (nessuna variabile doppia), i registri del runner (nessuna unità doppia; `utils real-decimal`
>   c'è). Alembic: una testa, 009. In stage solo le due risoluzioni.
> - **Controlli leggeri** della lista del coordinatore (`work/merge_0d20_checks.sh`, log in `work/merge_0d20/`): in corso.
> - **Esito** (18:57–19:44): `services` `session-version` 54, `user-profile` 47, `email-case` 67, `admin-bootstrap`
>   156, `app-lifecycle` 44; `db` `create`, `validate` 17, `migration-005…009` 25/37/29/23/11 (con la 001 di C-97a),
>   `populate`; `api` `auth` 95, `registration` 102, `profile` 28, `users-admin` 64, `admin-setup` 42, `email` 160;
>   `utils real-decimal` 92; `mkdocs build --strict` ✅, `check-links` ✅ 97: tutto ✅.
>   **⚠️ Fuori pista**: `utils dev-cli-image` di nuovo fermato al tetto di 600 s (83/94 passati, nessun rosso) su
>   `TestBackup::test_create_then_inspect`, con il carico salito da 28 a 176 durante la corsa. Verdetto (test-triage):
>   lentezza dell'ambiente; il merge non tocca il file del test, `user_cli.py`, `dev.py` né il Dockerfile, e la stessa
>   unità era 94/94 alle 16:55. Rifatta da sola sotto carico 40. «Combinata verde» detta al coordinatore (19:46) con
>   questa riserva.
> - **Merge committato** dal coordinatore: `71a92cec9` (genitori `546295d77` + `81bc305b9`). **`utils dev-cli-image`
>   rifatto** su `71a92cec9` (avvio 19:53, carico 32): **94/94 in 336 s** ✅. Porta libera. Revisione combinata tutta
>   verde; pronta per l'ingresso (la simulazione del coordinatore su dev, con MF, O-20, H-21, è pulita).

### Ingresso del treno 131 e ordine dei lotti seguenti (2026-10-16, 20:00–20:10)
> - **Entrata in dev**: giornale `6e7f7f3c7`, merge in `dev_release2` **`68355911f`** (treno 131: P18, A-24, A-27, A7a,
>   A7c, A-22). Righe del CHANGELOG mandate al coordinatore ed entrate (`docs(journal): trains 129-131, changelog A`):
>   🔒 A-22 e A7c (con quella di A-27), ⚠️ P18 (unicità senza maiuscole, l'avvio che si ferma, il ripristino di un backup
>   vecchio), 🔄 P18 (accesso e «password dimenticata» con qualunque maiuscola, cambio di sole maiuscole, API), ✨
>   `user set-email`. **A7a senza riga**: il link `/setup#token=…` non ha ancora la sua pagina (A7b); il testo A7a+A7b del
>   coordinatore entra con A7b.
> - **Ordine deciso dal coordinatore** (20:10): **A-25** (rossi in corso, piccolo) → **A7b** (necessaria in 1.3: F02 è una
>   funzione del Cloud e oggi il link non ha pagina) → **A8** (F15, limite dei tentativi di accesso) → **A9** (F05 parte
>   account + F09 note legali).

#### A-25.1 — Rossi scritti (2026-10-16, 19:45–20:05)
> - **`test-author`**, solo scrittura:
>   - `frontend/src/lib/features/auth/emailCase.test.ts` (nuovo, 23 casi, ambiente node): tutto rosso finché
>     `emailCase.ts` non c'è. Piega solo A–Z (`ÉMILE@X.COM` → `Émile@x.com`, lettere fuori da A–Z intatte, nessun
>     `trim`, nessuna normalizzazione); `sameEmail` vero/falso nei due versi.
>   - `ProfileTab.test.ts`, nuovo blocco «a change of capitals only (P18)»: rossi (nessun campo password né avviso,
>     ogni «Salva» acceso; corpo esattamente `{email}` dalla riga e da «salva tutto»; da un cambio vero a uno di sole
>     maiuscole il campo sparisce e la password non parte); guardia C5 (maiuscole fuori da A–Z: password chiesta).
>   - `emailCase.test.ts` registrato da me in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`).
> - **Punti fuori dal contratto, segnalati dal `test-author`** (da backlog, non in A-25): dopo un salvataggio con il
>   dominio in maiuscole la riga resta «modificata» (il server mette il dominio in minuscolo, l'input tiene quanto
>   scritto); un indirizzo cambiato altrove mentre la scheda è aperta può lasciare un 400 senza campo per la password.
> - Bozza della correzione pronta (`work/a25/apply_a25.py`: `emailCase.ts` nuovo e cinque modifiche di logica di
>   `ProfileTab.svelte`, nessuna classe), a secco pulita.

#### A-25.2 — Rossi osservati, correzione, verdi (2026-10-16, 20:05–)
> - **Rossi** (`work/a25/vitest.sh red`, carico 46): `emailCase.test.ts` rosso intero (`Cannot find module
>   './emailCase'`); `ProfileTab.test.ts` 8 rossi (il campo password ancora lì, il corpo con `current_password`), 80
>   verdi (la guardia C5 compresa).
> - **Correzione** (`work/a25/apply_a25.py`): `frontend/src/lib/features/auth/emailCase.ts` nuovo (`emailFold`,
>   `sameEmail`, A–Z soltanto); in `ProfileTab.svelte` `emailChangesAddress = emailModified && !sameEmail(...)`, che
>   governa `emailNeedsPassword`, lo svuotamento della password e il blocco del campo; `emailPayload()` manda `{email}`
>   da solo per un cambio di sole maiuscole (riga e «salva tutto»). Solo logica, nessuna classe. `prettier`: i due
>   file prodotto puliti; i due di test riformattati con `--write` (solo a capo, la versione HEAD era pulita).
> - **Verdi**: `vitest` dei due file **111/111** (88 + 23).
> - **Doc**: `user/settings/profile.en.md` («is another address»; per le sole maiuscole nessuna password chiesta) e
>   `developer/frontend/components/features/settings.md` (il punto «Only the capitals changed»). Debito di traduzione:
>   `profile`.
> - `front check` (svelte-check) **0 errori, 0 avvisi** ✅; `mkdocs build --strict` ✅ (3 076 URL), `check-links` ✅ 97;
>   `test check-orphans` ✅ (tutti i file di test registrati e raggiungibili da un `all`). Porta libera; `git diff
>   --check` pulito.

#### A-25.3 — Handoff FROZEN 🧊 (2026-10-16, 20:15)
> - HEAD `6e7f7f3c7`; delta: `emailCase.ts` e `emailCase.test.ts` nuovi, `ProfileTab.svelte` (solo logica),
>   `ProfileTab.test.ts`, `_frontend_utility.py` (registrazione), due pagine di doc, piano e backlog (A-25 ✅, A-28
>   nuova).
> - Prossimo: **A7b** (ordine del coordinatore: A-25 → A7b → A8 → A9).

### A7b — Analisi e contratto (2026-10-16, 20:20)
> Base `5a54e23ad` (A-25 entrata in dev, `b7e50b359`). Ordine del coordinatore: A-25 → **A7b** → A8 → A9.

**Stato reale, verificato**:
- **Backend A7a c'è**: `POST /auth/setup` (C3), `tokens/inspect` accetta `admin_setup` e risponde lo username, il link è
  `/setup#token=…` (frammento, come il reset). Il client generato ha già `admin_setup` e `/api/v1/auth/setup`.
- **Frontend**: nessuna rotta `/setup`. `linkToken.ts` ha `LinkPurpose = 'invite' | 'password_reset'`. Il modello c'è:
  `routes/reset-password/+page.svelte` con `AuthPageFrame`, `LinkStatusCard`, `ResetPasswordCard`, `takeLinkToken`,
  `inspectLinkToken`.
- **K-5**: chiusa in A6d dal flag `first_account_open` (C6 di A6d); l'etichetta «Crea l'account amministratore» di §4.7
  lì è caduta. Con F02 l'admin in attesa è una riga di `users`, quindi `first_account_open` è falso e il link «Register
  here» non c'è (modalità `invite`): coerente, niente da costruire.
- **Avviso di registrazione aperta**: l'area di H è `instanceNotices` (registro: chi registra decide chi vede e toglie
  l'avviso; «nessuno tocca il layout»); oggi registra solo `priceRefresh`, agganciato al client. Regola dell'host:
  decisione §10.4 («host della richiesta diverso da localhost e rete locale»), elenco in §4.7.
- **Scheda Utenti**: `holds_place` marca solo gli account in attesa della verifica (E5b), non l'admin in attesa, che
  appare «disattivo» con «Riattiva»: riattivarlo attiverebbe un account con una password che nessuno sa, e C3
  rifiuterebbe poi il suo link di setup (account attivo).
- **P16 (d)**, file delle decisioni (riga P16): «con l'istanza bloccata la creazione dell'admin è bloccata anche lei».
  `tokens/inspect` resta permesso da bloccata (`ALLOWED_WHEN_BLOCKED`), `POST /auth/setup` risponde 401: la pagina
  mostrerebbe il modulo e l'invio finirebbe in 401.

**Contratto proposto (C1–C7)**:
- **C1 · `/setup`** (`routes/setup/+page.svelte`, pubblica, come `/reset-password`): il token dal frammento
  (`takeLinkToken`, indirizzo ripulito), `inspectLinkToken(token, 'admin_setup')`; mancante, non valido, scaduto o usato →
  `LinkStatusCard` con testi propri (cosa fare: chiedere un link nuovo al fornitore, o `./dev.py user setup-link`);
  valido → `SetupCard`.
- **C2 · `SetupCard.svelte`** (`features/auth`): lo username (sola lettura, dall'inspect), password e conferma,
  `PasswordStrength` con le regole del server (decisione 37). Invio `POST /auth/setup {token, new_password}`; riuscito: la
  risposta porta il cookie come il login, `auth.checkAuth()` e dentro l'app. `PASSWORD_TOO_WEAK` → le regole mancanti;
  `TOKEN_INVALID` → lo stato «link non valido»; 401 (istanza bloccata, P16 d) → un messaggio proprio; altro → errore
  generico. Solo ruoli `-lf-` (skill `design-system`), `data-testid` ovunque.
- **C3 · `LinkPurpose`** prende `admin_setup`.
- **C4 · Avviso**: un helper puro `isLocalHost(hostname)` (§4.7: localhost, 127/8, 10/8, 172.16/12, 192.168/16,
  100.64/10, nomi a un'etichetta, `.local`, `.lan`, `.home.arpa`, `.internal`; `*.ts.net` esterno per Funnel; proposta:
  anche IPv6 `::1`, `fc00::/7`, `fe80::/10`) e un modulo che, per un admin, con `registration_mode === 'open'` e
  `location.hostname` non locale, mostra l'avviso `accounts.openRegistration` (warning, chiudibile, azione verso
  l'impostazione della registrazione; se la modalità è fissata da `LIBREFOLIO_REGISTRATION`, nessuna azione e il testo
  nomina la variabile), e lo toglie altrimenti.
- **C5 · L'admin in attesa nella scheda Utenti**: `AdminUserRead.pending_setup: bool` (disattivo con un token
  `admin_setup` vivo, lo stesso filtro di `user_usage`), nella lista e nella risposta della PATCH; nella scheda lo stato
  «In attesa del setup» al posto di «Disattivo», e niente «Riattiva» per lui. Un'azione «nuovo link di setup» dall'API
  admin sarebbe scope nuovo: proposta in backlog.
- **C6 · i18n**: chiavi nuove nel mio sottosistema, nelle 4 lingue.
- **C7 · Doc**: `admin/hosting_providers` (sezione F02: la pagina), `admin/users` (l'admin in attesa), una pagina
  utente sul primo accesso col link, sviluppatori (`security.md`, `access_control.md`). CHANGELOG all'ingresso: il testo
  A7a+A7b del coordinatore.

**Superfici e aree dei colori**: nuovi `routes/setup/+page.svelte` e `features/auth/SetupCard.svelte` (area T, file
nuovi, solo ruoli); `features/settings/users/**` (area IM: da chiedere); `.ts` senza colori (`linkToken.ts`, l'helper,
il modulo dell'avviso); backend `schemas/users.py`, `api/v1/users.py` (più `api sync`).

**Domande al coordinatore**: (1) dove si aggancia il modulo dell'avviso (il layout è di H); (2) via libera per la scheda
Utenti (IM) e conferma che «nuovo link di setup» va in backlog; (3) IPv6 locale in `isLocalHost`; (4) E2E: una per i
link non validi di `/setup` (un admin in attesa sulla corsia non si crea: F02 vuole un'istanza vuota).

**Passi**: rossi (C1–C3, C4 helper) → risposte (1)–(2) → rossi di C4 modulo e C5 → codice → verdi (vitest, `front
check`, `api users-admin`, `api sync`) → doc → handoff.
> **Contratto approvato** (coordinatore, 20:30, C1–C7). Risposte: (1) l'avviso con il meccanismo di registrazione di
> `instanceNotices`, chiamato dalla mia funzione di accesso quando l'utente è noto, senza toccare il layout; (2)
> `features/settings/users/**`: il coordinatore chiede a IM, intanto il backend di C5 (`pending_setup` + `api sync`) e
> i rossi; «nuovo link di setup» dall'API admin in backlog; (3) IPv6 locali `::1`, `fc00::/7`, `fe80::/10`, più
> `127.0.0.0/8` e `::ffff:127.*`; (4) E2E solo per il link non valido; il percorso riuscito e il 401 dell'istanza
> bloccata nel test del componente (API finta).
> **Ancora dal coordinatore** (20:40–20:50): IM libera `features/settings/users/**`, ne sono lo scrittore fino
> all'ingresso; **non toccare `settings/users/linkShareActions.ts`** (lo cambia E: «manda per email»); il distintivo «In
> attesa del setup» sui **ruoli**, un tono di `STATUS_TONES` (`lib/theme/toneClasses.ts`) o un distintivo già usato
> nella scheda (i file non hanno riga nel TSV: una classe di palette fa fallire `--check`). **Aggancio dell'avviso**:
> una riga in `appBootstrap.load()` (`features/onboarding/appBootstrap.svelte.ts`, non toccato dall'8/10, nessun ramo lo
> ha aperto: ne sono lo scrittore per A7b), idempotente e iniettabile come gli altri `load*`, con il test nel test
> esistente del bootstrap (`lib/stores/app/onboarding.test.ts`, `buildBootstrap()`).

#### A7b.1 — Rossi in scrittura (2026-10-16, 20:35–)
> - Tre `test-author` in parallelo, file distinti: (1) `/setup` — `routes/setup/page.test.ts`,
>   `features/auth/SetupCard.test.ts` (nuovi), `LinkStatusCard.test.ts` (prop `hintKey` e `link-status-hint`),
>   `linkToken.test.ts` (`admin_setup`); (2) l'avviso — `features/auth/localHost.test.ts`,
>   `features/auth/openRegistrationNotice.test.ts` (nuovi) e l'aggancio in `lib/stores/app/onboarding.test.ts`; (3) il
>   backend di C5 — `pending_setup` nell'API admin.
> - Interfacce fissate nei brief: `SetupCard` come `ResetPasswordCard` (`token`, `username`, `ondone`, `oninvalid`;
>   `data-testid` `setup-*`, `setup-blocked` per il 401); la rotta dopo `ondone` fa `auth.checkAuth()` e va a
>   `/dashboard`; `LinkStatusCard` prende `hintKey` (la rotta passa `auth.setup.newLinkHint`); `isLocalHost` in
>   `features/auth/localHost.ts`; `openRegistrationNoticeFor(...)` puro e `startOpenRegistrationNotice(deps?)`
>   idempotente in `features/auth/openRegistrationNotice.svelte.ts`, avviso `accounts.openRegistration` verso
>   `/settings?tab=admin` (senza azione se la modalità è fissata dalla variabile).
> - **Scelte di dettaglio** (20:55): i testi i18n nuovi in `auth.setup.*` e `auth.notices.*` (il mio sottosistema
>   `lib/i18n/auth/`; nessuno spazio `accounts` esiste), bozze nelle 4 lingue in `work/a7b/i18n_keys.json`. Nella scheda
>   Utenti `STATUS_TONES` non ha voci sue: il distintivo «In attesa del setup» riusa quello «Disattivo» della scheda
>   (neutro: `border-lf-subtle bg-lf-neutral text-lf-secondary`), al suo posto quando `pending_setup`; nessun «Riattiva»
>   per lui, ma una riga che dice che si attiva col suo link di setup (`./dev.py user setup-link` o il fornitore).
>   `pending_admin_filter` (quello di `user_usage`) vuol dire «disattivo, con un token `admin_setup`, nessuno
>   consumato», senza guardare la scadenza: `pending_setup` usa la stessa nozione.

#### A7b.2 — Rossi scritti (2026-10-16, 20:35–21:05)
> - **`/setup`** (`test-author`, 0 lanci): `routes/setup/page.test.ts` (nuovo, 26 casi), `features/auth/SetupCard.test.ts`
>   (nuovo, 31 casi), `LinkStatusCard.test.ts` (+13, `hintKey` e `link-status-hint`), `linkToken.test.ts` (+1,
>   `admin_setup`: rosso solo al controllo dei tipi). Registrati da me in `front_component_unit`. In più, come il modello
>   del reset: il markup per il gestore di password, le regole del server, «registrazione `disabled` non blocca
>   `/setup`».
> - **Backend C5** (`test-author`): solo `test_users_admin_api.py`, con l'harness privato del file (router veri su un
>   SQLite sotto `tmp_path`, l'admin in attesa fatto da `run_admin_bootstrap` vero): UADM-060 (la lista), UADM-061 (11
>   stati del link di setup), UADM-062 (la PATCH che lo lascia in attesa), UADM-063 (dopo il setup vero il flag è
>   falso), UADM-064 (lo schema, nove campi); UADM-003/007/008/028 rossi perché la lista dei campi prende
>   `pending_setup`. Provati in privato contro cinque implementazioni sbagliate: ognuna cade.
> - **⚠️ Fuori pista — tre punti emersi** (al coordinatore, 21:05): (1) l'intercettore 401 di `lib/api/zodios-client.ts`
>   (di H) manda al login ogni 401 fuori da `/`: su `/setup` il 401 dell'istanza bloccata non arriverebbe mai alla
>   scheda (lo stesso meccanismo di A-13); proposta: le pagine dei link anonime non reindirizzano. (2) La PATCH accetta
>   «Riattiva» sull'admin in attesa: proposta 409 `PENDING_SETUP`. (3) Un 423 sul setup mostra `setup-blocked` come il
>   401 (deciso da me salvo obiezione).
> - **Decisioni del coordinatore** (21:10): (1) l'eccezione nell'intercettore per le pagine anonime dei link (`/setup`,
>   `/invite`, `/reset-password`, `/verify-email`: nessun reindirizzamento al login su un 401) la scrivo io, una
>   condizione e il test in `zodios-client.test.ts`; **H la rivede in sola lettura** prima del checkpoint; il 423 di H
>   resta com'è; **chiude A-13**. (2) 409 `PENDING_SETUP` nella PATCH `{is_active: true}` sull'admin in attesa, rosso
>   prima. (3) 423 → `setup-blocked`. Per chiudere A-13 davvero: `describeRegistrationError` mappa un 401 (e un 423
>   `instance_blocked`) su `auth.instanceBlocked`, altrimenti `/invite` mostrerebbe il «Not authenticated» grezzo.
> - **Rossi osservati, prima parte** (20:40–20:44, carico 37): `api users-admin` **21 rossi**, 59 verdi (UADM-060…064 e
>   i quattro test esistenti che fissano la lista dei campi, tutti per `pending_setup` assente); vitest: `SetupCard` e la
>   rotta rossi interi (import mancante), `LinkStatusCard` 13 rossi, `linkToken` rosso solo ai tipi.
> - **Bozze pronte** (a secco pulite, `work/a7b/`): `apply_backend.py` (`pending_admin_ids`/`is_pending_admin` in
>   `registration_service`, il campo, la lista, la PATCH con il 409 `PENDING_SETUP` prima del controllo del limite, e la
>   risposta col flag calcolato dopo l'aggiornamento), `apply_frontend.py` (tipo del link, `hintKey`, A-13 in
>   `registrationErrors`, l'eccezione nell'intercettore, la riga della scheda Utenti, `PENDING_SETUP` in
>   `accountErrors`; nuovi `SetupCard.svelte`, la rotta, `localHost.ts` — che legge anche la forma esadecimale degli
>   IPv4 mappati, `[::ffff:7f00:1]`, come la scrivono i browser), `i18n_add.py` (16 chiavi nelle 4 lingue con `dev.py i18n
>   add`, poi `build` e `check`). Il modulo dell'avviso e l'aggancio in `appBootstrap` dopo aver letto i loro test.
> - Un quarto `test-author` per la parte UI di C5 (`UserRow.pendingSetup.test.ts`, `accountErrors`).

### A7b.3 — Rossi, seconda parte ✅ (16/10, 20:57–21:15)

- **Test nuovi**, dai quattro `test-author` (sola scrittura, nessuna corsa):
  - `features/auth/localHost.test.ts` (142 casi: i due lati di ogni confine, la forma esadecimale degli IPv4 mappati
    che il browser scrive, i suffissi come etichette intere, i gruppi IPv6 letti come numeri);
  - `features/auth/openRegistrationNotice.test.ts` (66 casi: la tabella di verità, il watcher iniettato, i valori
    predefiniti dell'app — store dell'auth, `instanceConfig`, l'host della pagina, il registro di H —, la chiusura
    dell'utente che sopravvive alle rivalutazioni, le chiavi nelle 4 lingue);
  - `stores/app/onboarding.test.ts` (+8: l'avvio dell'avviso in `load()` subito dopo la guardia dell'utente, prima dei
    caricatori, anche quando falliscono; il predefinito senza argomenti; una guardia senza utente);
  - `SetupCard.test.ts` (35: anche il 423 `instance_blocked` → `setup-blocked`, e tre 423/403 che restano «failed»);
  - `zodios-client.test.ts` (+24: niente login su un 401 dalle quattro pagine dei link, con e senza la barra finale;
    le altre pagine come oggi; il 423 invariato), `registrationErrors.test.ts` (+16: A-13);
  - `test_users_admin_api.py`: UADM-065 (6, il 409 `PENDING_SETUP`, anche a link scaduto), guardie UADM-066/067;
  - `features/settings/users/UserRow.pendingSetup.test.ts` (35) e `accountErrors.test.ts` (32, nuovo).
- **Registrati** nel runner: `localHost`, `openRegistrationNotice`, `accountErrors` in `core-unit`;
  `UserRow.pendingSetup` in `component-unit`.
- **Osservati** (20:57–21:04, carico 45): `api users-admin` **27 rossi** (i 21 di prima + i 6 di UADM-065), 64 verdi
  (+5 guardie); vitest 8 file rossi su 9 — import mancanti (`SetupCard`, la rotta, `localHost`, l'avviso),
  `LinkStatusCard` 13, `registrationErrors` 12, `onboarding` 7: tutti per la ragione giusta.
> **⚠️ Fuori pista**: nel `describe` nuovo di `zodios-client.test.ts` cadevano **anche le 15 guardie** (24 su 24),
> tutte sulla barriera (`error.response` assente). Triage: con `browser: true` l'intercettore della *richiesta* legge
> `localStorage` per `Accept-Language`, e jsdom sotto Node 26 non ne espone uno usabile (la stessa nota di
> `AboutTab.test.ts`): un `TypeError` respinge la richiesta prima dell'adapter. Verdetto **assunzione** del test, non
> difetto del prodotto: il `test-author` aggiunge al solo `describe` un `localStorage` di prova, ripristinato dopo ogni
> caso. `zodios-client.ts` non cambia per questo.
> **Scelte di dettaglio** (non fissate dai test, decise dal titolare):
> - il `config` **predefinito** dell'avviso vale solo a configurazione caricata (`instanceConfig.loaded`): prima della
>   risposta di `/system/instance` vige quella di default, che è `open`, e un'istanza a invito raggiunta da fuori — il
>   caso del cloud — mostrerebbe l'avviso per niente; il `config` iniettato non cambia;
> - l'avviso legge l'utente con `fromStore(currentUser)`, chiama `show`/`hide` fuori dal tracciamento (`untrack`), e un
>   secondo avvio restituisce una funzione vuota;
> - il suggerimento della riga in attesa sta sotto le azioni, come le ragioni dei pulsanti disattivati; nei testi
>   `dev.py user setup-link` senza `./`, giusto sia per l'installazione da sorgente sia per Docker
>   (`python dev.py …`).
- **Terzo giro di rossi** (21:19–21:20, carico 49, dopo la riparazione): `zodios-client` 9 rossi sul `goto`, 15 guardie
  verdi; `UserRow.pendingSetup` 23 rossi, 12 guardie verdi; `accountErrors` 4 rossi, 28 guardie verdi. Tutti per la
  ragione prevista.

### A7b.4 — Codice ✅ (16/10, 21:20–21:45)

- Applicati gli script di `work/a7b/` (`apply_backend.py`, `apply_frontend.py`, `apply_notice.py`): backend 3 file,
  frontend 8 modificati e 4 nuovi (`SetupCard.svelte`, la rotta `/setup`, `localHost.ts`,
  `openRegistrationNotice.svelte.ts`), più `AdminAccount.pending_setup?` in `settings/users/types.ts` (chiesto dai tipi
  dei test della riga).
- `ruff` e `black` puliti; `api sync` (21:22, carico 48) rigenera il client con `pending_setup`, nessun file tracciato
  toccato; `i18n add` di **14** chiavi nelle 4 lingue (non 16: 7 del setup, 3 dell'avviso, `auth.instanceBlocked`, 3
  della scheda Utenti), `i18n build` e `check` verdi (4 800 chiavi); Prettier pulito dopo `--write` sul solo
  `UserRow.svelte` (la riga `<li>` col nuovo attributo, andata a capo).
- Docs (`docs-writer`, 13 pagine EN, nessun timbro: debito A-10): admin `hosting_providers` (§ nuova
  «What Your Customer Sees»), `users` (§ `#pending-setup`), `settings` (§ `#open-registration-warning`),
  `configuration`; utente `getting-started`; developer `features/auth` (`#setupcard`, `#link-page-401`,
  `#open-registration-notice`), `features/settings`, `onboarding`, `state/app-state`, `architecture/security`,
  `access_control`, `pages/index`, `live-ticker` (il motivo per cui il poll evita il client, che dava per scontato il
  401 → login ovunque). Citazioni verificate col catalogo; le etichette «Deactivated» e «Admin» sono quelle reali.
- Commento in testa all'intercettore aggiornato; descrizione di `auth-links` nel runner estesa a `/setup`; richiesta al
  coordinatore della revisione di H (sola lettura) su `zodios-client.ts`.
> **Verificato, non è un buco** (segnalato dal `docs-writer`): `dev.py user activate` non conosce l'admin in attesa e
> lo attiva. Ma `complete_admin_setup` rifiuta e revoca il link di un account già attivo («once the account is set up,
> by any path»): `activate` + `reset` è la via di scorta dell'operatore, e il link muore. Nessuna modifica.

### A7b.5 — Revisione di H su `zodios-client.ts` ✅ (16/10, 21:48)

- **Esito di H**: OK, nessun cambio alla logica (il 423 intatto, i percorsi esatti, le quattro pagine sono quelle di
  `_TOKEN_PATHS` del backend; sana anche il token perso nel frammento). Due richieste non bloccanti, fatte:
  1. il commento prometteva troppo per `/verify-email` (lì il 401 di `confirm` non è riconosciuto da `readLinkRefusal`
     e la pagina mostra l'errore generico: H lo passa a E): ora dice «which the page receives». Le doc lo dicevano già
     giusto («`/verify-email` shows its own failure, with Retry»);
  2. rimando incrociato fra `LINK_PAGES` (frontend) e `_TOKEN_PATHS` (`token_service.py`), con un commento ai due lati,
     e una guardia: un test puro in `test_account_tokens.py` (unità `services account-tokens`, nessuna voce nuova nel
     runner) che legge il letterale TS e lo confronta con le pagine di `token_path` — un `test-author`.
- **Backlog**: A-13 ✅ (con la nota su `/verify-email`); A-29 (sotto `vite dev` `hooks.server.ts` porta le pagine dei
  link al login: segnalato da H, fuori da A7b); A-30 (un nuovo link di setup dall'API e dalla scheda Utenti, deciso dal
  coordinatore).
- Rifiniture dopo la revisione: la docstring di `POST /auth/tokens/inspect` nomina anche il link di setup (segnalata dal
  `test-author` dell'E2E); descrizioni del runner (`auth-links` con `/setup`, `account-tokens` con la guardia).
- **Guardia `LINK_PAGES` = pagine di `token_path`** (`test-author`): `test_token_path_pages_are_the_link_pages_of_the_api_client`
  in `test_account_tokens.py`, con le barriere (il parser su frammenti sintetici, i quattro rifiuti, la differenza che
  nomina la pagina mancante o in più, il file vero non vuoto), verde in processo; provata contro dieci derive simulate.
- **E2E** (`test-author`): in `e2e/auth-links.spec.ts` il `describe` «Setup links (/setup)», 3 casi (un token che
  nessuno ha emesso: esce dalla barra, una sola ispezione `admin_setup`, `unknown` col suggerimento, `no-referrer`,
  si resta su `/setup`; nessun token → `missing` senza ispezioni; un token nella query → `missing`). Nota del
  `test-author`: sulla corsia nessuna chiamata della pagina risponde 401, quindi l'eccezione dell'intercettore la tiene
  solo `zodios-client.test.ts`.

### A7b.6 — Verdi (16/10)

- **Vitest** (21:52–21:56, carico 47): i file di A7b e i vicini (`AuthCard`, `AuthPageFrame`, `LoginCard` ×2,
  `RegisterCard` ×2, `ResetPasswordCard`, `registrationErrors.verification`, `passwordRules`, `instanceBlock`,
  `instanceConfig`, `instanceNotices`, `UserRow.verification`, `InviteDialog`, `ResetLinkDialog`, i due cancelli del
  layout, le pagine `invite`, `reset-password`, `verify-email`): **31 file, 1 009 test verdi**.
- **Backend** sulla corsia: `api users-admin` **91 verdi** (22:03–22:16; la prima corsa dopo il codice ricostruisce
  frontend e sito); `api admin-setup` **42**; `api auth` **95**.
  `api registration` **102** (22:56–22:59; l'unico avviso è la deprecazione di Starlette di sempre, come in P18).
- **Finali** (`work/a7b/final.sh`, 23:01–23:28, ciascuno a carico < 50): `services account-tokens` **66 verdi** (con
  la guardia); `theme-roles.mjs --check` rc 0 e `themeRoles.gate` 80/80; `check-orphans` pulito; E2E
  `front-utility auth-links` **12 verdi** (i 3 nuovi di `/setup` compresi); `mkdocs build` (strict) verde, 3 076 URL
  relativi risolti; `mkdocs check-links` verde; `lint --dead-code`: nessun reperto nei file di A7b (rc 1 per reperti
  preesistenti: dipendenze `@embedpdf/*` non elencate, metodi al 60 % di vulture).
> **⚠️ Fuori pista**: `front check` (23:02) ha trovato **1 errore**, mio: allargare `LinkPurpose` con `'admin_setup'`
> rompeva `features/email/sendLinkApi.ts` (di E), il cui endpoint accetta solo invito e reset. `LinkPurpose` è anche «i
> link che un admin condivide» (`LinkShare`, `linkShareActions`, il mittente delle email): lì il setup non c'entra. Cura
> nel mio file, senza toccare quelli di E e di IM: `LinkPurpose` torna `'invite' | 'password_reset'`, e
> `inspectLinkToken` prende un tipo nuovo, `InspectedLinkPurpose = LinkPurpose | 'admin_setup'`; aggiornati i due
> commenti di `linkToken.test.ts` e una cella di `features/auth.md`. Poi (23:28–23:31) vitest di `linkToken`, la
> pagina `/setup`, `LinkShare` e `linkShare` **84 verdi**, `front check` **0 errori, 0 avvisi**. La cella delle doc
> non tocca link: il `build` strict delle 23:20 resta valido.
- `git diff --check` pulito; porta 6182 libera (`lsof` rc 1).

### A7b — Definizione di fatto ✅ (16/10, 23:35)

C1–C7 consegnati: la pagina `/setup` (C1), `SetupCard` col 423 `instance_blocked` come il 401 (C2), lo scopo
`admin_setup` dell'ispezione (C3 — **non** in `LinkPurpose` ma in `InspectedLinkPurpose`, vedi il «Fuori pista» qui
sopra), l'avviso di registrazione aperta e `localHost` con l'aggancio in `appBootstrap` (C4), `pending_setup` con la
riga della scheda Utenti (C5), le 14 chiavi nelle 4 lingue (C6), le doc (C7). Dalle decisioni del coordinatore:
l'eccezione del 401 nell'intercettore e A-13 in `registrationErrors` (A-13 ✅), il 409 `PENDING_SETUP` della PATCH.
Rossi prima del codice in tre giri, verdi dopo, E2E del link non valido, revisione di H fatta. Resta per dopo: A-29,
A-30 (backlog); per E, il 401 di `confirm` su `/verify-email` (lo passa H).

### Dopo A7b — A-31 (16/10, 23:40)

- Dal coordinatore, per conto di B (ripristino, decisione N57): l'ordine d'avvio diventa `global-settings` →
  `admin-bootstrap` → `restore-commit` → `plugin-secrets-check`. Il passo di A resta prima del commit del ripristino:
  se solleva sui dati ripristinati, il ripristino torna indietro (B lo fissa nel suo test).
- Verificato in sola lettura: sui dati ripristinati con altri account `run_admin_bootstrap` registra e salta; un link
  di setup scaduto dà solo un avviso nel log; l'unica eccezione che lascia passare è un errore del database diverso da
  un lock, e lì il ritorno indietro del ripristino è giusto.
- Il caso limite di B, scritto come **A-31** nel backlog (A-29 e A-30 erano già presi): un archivio con l'admin in
  attesa e un altro admin attivo, ripristinato con `LIBREFOLIO_ADMIN_EMAIL` e un token mai visto. Il bootstrap riarma
  il link, il commit del ripristino revoca ogni link vivo e lo revoca subito; resta `./dev.py user setup-link`.
  Cura possibile di B: il commit risparmia i link emessi dall'avvio in corso.

## A7b-2 — Analisi e contratto (16/10, 23:50)

Lotto piccolo di sicurezza, deciso dal coordinatore prima di A8: **A-32** (il cuore), **A-33** (naturale qui), **A-34**
(solo se costa poco); **A-35** registrato, da collocare (decisione D2 sotto). Base: merge `ec73a49c1` (A7b + dev
`db506eb21`). Prima i rossi.

### Stato reale (codice a `ec73a49c1`)

- **La nozione «in attesa»** (`registration_service.pending_admin_filter`): disattivo, con almeno un link
  `ADMIN_SETUP`, nessuno consumato. Ignora di proposito scadenza e **revoca**: `user setup-link` e il riarmo del
  bootstrap revocano i link vecchi prima di emetterne uno nuovo, e il ripristino (A-31) li revoca tutti — l'account
  deve restare «in attesa» perché `setup-link` lo ritrovi.
- **`complete_admin_setup`** (`bootstrap_admin_service.py:263`): consuma il link, poi rifiuta (e revoca) solo se
  l'account è **attivo**.
- **Le altre vie che attivano o danno una password**, nessuna tocca `ADMIN_SETUP`:
  `user_service.update_user_status` (PATCH; per l'admin in attesa c'è già il 409 `PENDING_SETUP` di A7b, ma la funzione
  no), `set_user_active` (`user activate`), `reset_password` (`user reset`), `complete_password_reset` (il link di
  reset, che l'admin può emettere anche per l'account in attesa: la rotta non lo esclude), la rotta
  `change-password` (`auth.py:352`, account attivo). La conferma dell'email di E (`verification.py:349`) attiva, ma
  per l'admin in attesa **non è raggiungibile**: il bootstrap non emette link di verifica, e il «reinvio» chiede la
  password, che nessuno conosce. Nessuna modifica nei file di E.
- **A-33**: `_follow_variables` (`bootstrap_admin_service.py:140-157`) cambia l'indirizzo dell'account in attesa al
  cambio di `LIBREFOLIO_ADMIN_EMAIL` (non per un cambio di sole maiuscole, P18) e non revoca nulla; il riarmo da
  `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` avviene solo per un token mai visto. Anche `update_profile` (`user set-email`
  sull'account in attesa) revoca i link di reset (A-27) ma non quelli di setup.
- **A-34**: `end_sessions(user)` fa `user.session_version += 1` in memoria; 9 chiamate (6 in `user_service`, la rotta
  `change-password`, `POST /users/{id}/sessions/revoke`, `complete_admin_setup`).
- **A-35**: nessun gestore d'eccezione nell'app; il 422 di FastAPI 0.141.1 porta `input` (provato: `string_too_short`
  → il valore; `missing` → **tutto il corpo**, password compresa). Già protette solo le impostazioni dei plugin
  (`_NoInputEchoRoute`). Chi legge `input`: `eventSaveError.ts` (con un ripiego su `row.type`), un test di
  `plugin_settings` (che ne vuole l'assenza), `test_tools_wire` (errori Pydantic grezzi, non HTTP).

### Decisioni

- **D1 · «Ritirare» il link, non solo revocarlo** (proposta): alla fine del setup per altra via, i link
  `ADMIN_SETUP` non consumati dell'account prendono `revoked_at` **e** `consumed_at` (con `consumed_by_user_id` nullo:
  speso senza il suo portatore). Perché non la sola revoca: la nozione «in attesa» ignora la revoca (sopra), quindi un
  admin attivato per altra via e poi disattivato resterebbe per sempre «Waiting for setup», con «Reactivate»
  rifiutato (409 `PENDING_SETUP`), `setup-link` che gli rilascerebbe un link nuovo e il bootstrap che lo tratterebbe
  da admin in attesa. Con il ritiro: non è più «in attesa» (è un account come gli altri), `inspect_token` legge la
  revoca per prima e la pagina dice «This link has been withdrawn», il consumo atomico lo rifiuta. Nessuna migrazione.
- **D2 · A-35: un gestore globale o la sola `route_class` dell'auth** (da decidere col coordinatore, H): la cura
  solida è un gestore di `RequestValidationError` per tutta l'app che toglie `input` da ogni errore (la stessa regola
  di `_NoInputEchoRoute`), in un modulo nuovo di `api/` più **una riga** di registrazione in `main.py` (di H): copre
  anche le rotte di E (reinvio con password, SMTP), di B e dei plugin. Il ripiego nei soli miei file: la stessa
  `route_class` sul router `auth` (login, registrazione, cambio password, reset, setup, profilo, eliminazione), con la
  classe spostata in un modulo comune invece di copiarla.

### Contratto

- **C1 · Ritiro alla fine del setup per altra via (A-32)**: `token_service.retire_tokens(session, *, user_id, purpose,
  now=None) -> int` (revoca e consumo insieme, non committato). Chiamato con `ADMIN_SETUP`, nella stessa transazione:
  all'attivazione in `update_user_status` e `set_user_active`; a ogni password data in `reset_password`,
  `complete_password_reset`, `change-password`. Log «Setup links retired: the account was set up another way»
  (`user_id`, `count`), nessun token.
- **C2 · Effetti fissati dai test**: dopo ciascuna via, il vecchio link → `inspect` `revoked`, `POST /auth/setup` 400
  `TOKEN_INVALID`, password e stato invariati; lo scenario completo (attiva per altra via → disattiva → il link non
  riattiva). L'account non è più «in attesa»: `pending_setup` falso, PATCH di riattivazione 200, `setup-link` senza
  account, bootstrap `IGNORED`. Guardie: il link dell'admin in attesa senza altro funziona; demozione e
  `{is_active: false}` non ritirano (UADM-062/067).
- **C3 · Indirizzo cambiato (A-33)**: in `_follow_variables` e in `update_profile`, un cambio **vero** dell'indirizzo
  dell'account in attesa **revoca** (non ritira: resta in attesa) i suoi link di setup. Al riavvio con un token
  d'ambiente nuovo il riarmo emette quello (già oggi); altrimenti il log dice, una volta, che il link non vale più e
  come averne uno (`dev.py user setup-link`, o un token nuovo). Un cambio di sole maiuscole non revoca.
- **C4 · A-34 (se costa poco, ultimo passo)**: `end_sessions(session, user)` asincrona con l'incremento in SQL e
  rilettura del valore; le 9 chiamate; un test con due sessioni che arrivano a +2.
- **C5 · A-35**: secondo D2; test API: per le rotte dell'auth, un 422 per campo e uno per campo mancante senza `input`
  e senza il testo della password o del token; `loc`, `msg`, `type` restano.
- **C6 · Doc**: `admin/hosting_providers` (cambio d'indirizzo, setup per altra via), `admin/users`, `admin/cli_tools`
  (`user activate`/`reset` sull'admin in attesa), `developer/architecture/security`, `access_control`.

**Selettori**: `services admin-bootstrap`, `services account-tokens`, `services session-version`, `services
user-profile`, `api admin-setup`, `api users-admin`, `api auth`, `api registration` (+ `utils dev-cli-image` se cambia la
CLI). **Rischi**: il ritiro deve stare nella stessa transazione del cambio; la PATCH resta col 409 prima (difesa in
profondità sotto); A-34 tocca 9 punti delle sessioni, coperti da `session-version`.

### A7b-2 — Decisioni del coordinatore e controlli preliminari (16/10, 23:55)

- **D1 approvata** (decisione notturna N60): «ritiro» (`revoked_at` + `consumed_at`) nei 5 punti, nella stessa
  transazione. **D2**: gestore globale, dentro A7b-2; la riga in `main.py` la scrivo io, H la rivede al checkpoint come
  per `zodios-client`. A-33 come descritto; A-34 per ultimo se c'è tempo. CHANGELOG: una riga 🔒 per A-32+A-33, una per
  A-35, senza dire come sfruttarle.
- **I tre controlli chiesti prima dei rossi di A-35**:
  1. test che leggono `input`/`ctx` in un 422: nel backend nessuno ne vuole la **presenza**; l'unico,
     `test_plugin_settings_api.py:503`, ne vuole l'**assenza** e resta valido. Negli E2E nessuno. Nel frontend
     `eventSaveError.ts` usa `issue.input ?? row.type` (ripiego già lì), i suoi Vitest simulano il 422 da soli;
  2. lo schema OpenAPI `ValidationError` di FastAPI dichiara `input` e `ctx` **facoltativi**, e un gestore d'eccezione
     non lo cambia: `api sync` non tocca `generated.ts` (lo ricontrollo dopo il codice);
  3. `_NoInputEchoRoute` (`api/v1/plugin_settings.py`, commit `efa135c75` del filone plugin): col gestore globale è
     un doppione. **Lo tolgo** (una regola sola, in un posto solo); il suo test resta com'è, perché passa dal server
     vero della corsia (`httpx` senza transport) dove il gestore è registrato; aggiorno la riga di
     `developer/architecture/patterns/plugin_settings.md:425`.
- **Forma**: `backend/app/api/validation_errors.py` con `install_validation_error_handler(app)`, nello stile
  `install_*` di `main.py`; il gestore toglie `input` e passa a quello predefinito di FastAPI
  (`request_validation_exception_handler`), così il resto della risposta resta identico.
- **Test**: tre `test-author` — servizi (A-32/A-33: `test_account_tokens.py`, `test_admin_bootstrap.py`,
  `test_user_profile.py`), API (A-32: `test_admin_setup_api.py`, `test_users_admin_api.py`), A-35 (file nuovo
  `test_validation_errors_api.py`, unità `api validation-errors` da registrare). I primi due **fermi in scrittura**
  durante lo slot 1 (la validazione combinata deve raccogliere i file del commit), il terzo scrive un file nuovo che
  lo slot non raccoglie.
- **Aggiunta al contratto (C1, dal `test-author` delle API)**: quando `complete_admin_setup` rifiuta il link di un
  account già attivo, **ritira** i link di setup dell'account invece di revocare solo quello: altrimenti, disattivato
  dopo, tornerebbe «in attesa» (`pending_setup` vero, 409 alla riattivazione, `setup-link` che gli dà un link nuovo).
  Nessuna migrazione: F02 non è mai uscito (1.3), non c'è una base installata con link vivi su account già attivati.
- **Slot 1, validazione combinata di `ec73a49c1`** (23:48–): `api users-admin` **91**, `api admin-setup` **42**, `api
  auth` **95**, `api registration` **102**, tutti verdi; poi l'E2E `auth-links`. I `test-author` ripartono (GO) dopo le
  unità API: l'E2E non raccoglie i test del backend.
- **Validazione combinata, controlli leggeri** (`work/a7b_merge/light*.sh`, 23:41–00:17): `api sync` ✓; `front check`
  **0/0**; `mkdocs build` strict ✓ (3 084 URL); `check-links` ✓; Vitest dei file di A7b e vicini **32/34 file, 1 063
  verdi**, 20 rossi in `(app)/layout.gate.test.ts` e `layout.authGate.test.ts` (`No "onNavigate" export is defined on
  the "$app/navigation" mock`). Triage: verdetto **assunzione** del test, rotta da un cambio di prodotto di un altro
  filone — il commit `ec018afdf` di dev (`feat(ui): page Refresh spins on big requests`) usa `onNavigate` nel layout
  `(app)`, e i due test (di H) lo simulano senza. Verdi alle 21:56 su A7b prima del merge; non sono file miei:
  segnalato al coordinatore con la cura (`onNavigate: vi.fn()` nei due `vi.mock`).
- **A7b entrato** (17/10, 00:20): merge in dev `3e5336a0a`, CHANGELOG A7a+A7b in `0e83e1cd5` (4 ✨ dopo «Password-reset
  links», 🐛 A-13 in fondo a Fixed). I due rossi del layout sono di Y (`ec018afdf`), che li cura. La base di A resta
  `ec73a49c1` fino al prossimo checkpoint (worktree sporco con A7b-2).
- **Correzione del controllo 3** (dal coordinatore, 00:30): B4 sposta `_NoInputEchoRoute` in
  `backend/app/api/no_echo.py` (`NoInputEchoRoute`): per non collidere il mio gestore sta in un modulo mio
  (`api/validation_errors.py`) e **non tocco** `plugin_settings.py` né la classe; toglierla dopo l'ingresso di entrambi
  è **A-37** (backlog). Tolta da `work/a7b2/apply_a35.py` la parte su `plugin_settings.py`.
- **Revisione in sola lettura di B4** (chiesta dal coordinatore: B scrive nei miei file): `password_policy.py`
  (`failed_rules`/`password_rules_public` con `rules=`, `rules_with_minimum_length`, `_rules()` che legge
  `PASSWORD_RULES` a ogni chiamata), `PasswordStrength.svelte` (prop `rules` facoltativa), i test B4-RULES-01..09 e la
  descrizione `password-policy`: **OK**. Nota non bloccante: il componente legge una lista **vuota** come assente, il
  backend come «nessuna regola»; innocuo, `rules_with_minimum_length` non dà mai una lista vuota.

### A7b-2.1 — Rossi ✅ (17/10, 00:23–)

- **Test** (tre `test-author`, sola scrittura):
  - API (`test_admin_setup_api.py`, `test_users_admin_api.py`): SETUP-014 (×3: link di reset speso, `user reset`,
    `user activate` → `deactivate`), SETUP-015 (cambio password, difesa in profondità), guardia SETUP-016 (×4);
    UADM-068 (×3), UADM-070 (attivazione della PATCH), UADM-071 (link rifiutato di un account attivo: **tutti** i suoi
    link ritirati), guardia UADM-069 (×4);
  - servizi: `test_account_tokens.py` (C1, 10), `test_admin_bootstrap.py` (A32-001…007, A33-001…003: 21 rossi, 13
    guardie; A32-007 è il caso del CLI con un link scaduto, dalla revisione di E), `test_user_profile.py` (UPROF-003…005);
  - A-35: `test_validation_errors_api.py` (nuovo, registrato come `api validation-errors`, write-scoped): parte pura
    (6 rossi, 1 guardia), corsia (22 rossi su 8 rotte, 2 guardie: forma del 422 e schema OpenAPI invariati).
- **Osservati** (corsia, carico < 50): `api admin-setup` **4 rossi** (SETUP-014 ×3, SETUP-015: il setup risponde 200, la
  presa di possesso), 46 verdi; `api users-admin` **5 rossi** (UADM-068 ×3, 070, 071), 95 verdi; `api
  validation-errors` **28 rossi**, 3 verdi. Tutti per la ragione giusta.
- **Revisione di E** su A7b (dal coordinatore): il percorso del CLI e i link scaduti sono già dentro D1; il CLI resta
  permissivo (`user activate` + `user reset` è la via dell'operatore), da documentare in `cli_tools`.
> **Scelta**: il ritiro (e la revoca al cambio d'indirizzo) valgono per **ogni** account, non solo per quello in
> attesa: lo chiedono UADM-070 e SETUP-015. Così cambiano per costruzione cinque test esistenti, aggiornati dal
> `test-author` dei servizi: BOOT-014 `[pending-both]`, `[pending-the-email]` (ora `EXPIRED` e il link revocato) e i tre
> di A-27 in `test_session_version.py` (il link `its-admin-setup` della fixture ora si muove: ritirato dopo una
> password, revocato dopo un indirizzo).
- **Rossi dei servizi** (00:50–00:56): `services account-tokens` **10**, `admin-bootstrap` **23** (21 nuovi + BOOT-014 ×2
  aggiornati), `user-profile` **2**, `session-version` **3** (i tre di A-27 aggiornati). In tutto A7b-2 ha **75 rossi**,
  ciascuno sull'asserzione prevista.

### A7b-2.2 — Codice ✅ (17/10, 00:57)

- Applicati `work/a7b2/apply_a32_a33.py` (`token_service.retire_tokens`; il ritiro in `update_user_status`,
  `set_user_active`, `reset_password`, `complete_password_reset`, `change-password`, e nel rifiuto di
  `complete_admin_setup`; la revoca al cambio vero d'indirizzo in `_follow_variables` — che ora dice anche se
  l'indirizzo è cambiato, per il messaggio del log — e in `update_profile`) e `work/a7b2/apply_a35.py`
  (`api/validation_errors.py` con `install_validation_error_handler`, la riga in `main.py`; `plugin_settings.py`
  intatto). `ruff` pulito, `black` ha unito una riga nuova di `token_service.py`.
- Doc: `docs-writer` su `admin/hosting_providers`, `admin/users`, `admin/cli_tools`, `security`, `access_control` e
  la pagina sul formato degli errori (non `patterns/plugin_settings.md`: A-37).
- Dal `docs-writer` (9 pagine EN, solo lettura del codice): la docstring di `POST /auth/setup` diceva ancora «revoked»
  → ora «setup links are then retired» (`auth.py`); `api sync` cambia `generated.ts` **solo** in quella descrizione (6
  righe di diff), lo schema `ValidationError` resta. Lasciati per il coordinatore: `admin/configuration.en.md` (ha
  traduzioni) dice che ogni avvio senza link scrive l'avviso di scadenza, ma l'avvio che applica un indirizzo nuovo
  scrive quello del cambio d'indirizzo; `user activate` sull'admin in attesa, a istanza piena, avvisa del limite benché
  il suo posto sia già contato (preesistente).

### A7b-2.3 — Verdi ✅ (17/10, 00:58–01:34)

- `api sync` dopo il codice: `generated.ts` identico (hash `0b13c243009e`); dopo la docstring, solo la descrizione di
  `POST /auth/setup`.
- **Servizi**: `account-tokens` **76**, `admin-bootstrap` **190**, `user-profile` **52**, `session-version` **54**.
- **API**: `admin-setup` **50**, `users-admin` **100**, `validation-errors` **31**, `auth` **95**, `registration`
  **102**, e i vicini del 422 globale: `plugin-settings` **14** (il loro test «no echo» passa col gestore globale e con
  la `route_class` ancora lì), `email-verification` **49**, `email-verification-hooks` **16**, `tools` **12**.
- `check-orphans` pulito; `mkdocs build` strict ✓ (3 084 URL); `check-links` ✓; `git diff --check` pulito; porta 6182
  libera.
- **A-34 non fatto, di proposito**: non è «poco costoso». `test_session_version.py` fissa `end_sessions` come funzione
  semplice e sincrona (contratto 5, 30 riferimenti); l'incremento in SQL la rende asincrona con la sessione in 9
  chiamate e riscrive quel contratto. Resta nel backlog, da proporre col lotto A8 (che tocca le sessioni) o da solo.

### A7b-2 — Definizione di fatto ✅ (17/10, 01:35)

A-32 (C1/C2, più il rifiuto di `complete_admin_setup`), A-33 (C3), A-35 (C5, gestore globale in `api/validation_errors.py`
più la riga in `main.py`, da far rivedere ad H), doc (C6). Rossi prima del codice (75), verdi dopo, nessun file di altri
toccato (`plugin_settings.py` intatto: A-37). Restano: A-34 (backlog), A-37 (dopo B4).

### A7b-2 — Dopo il checkpoint (17/10, 01:36–)

- **Commit del coordinatore**: `53c064556` (A-32/A-33), `2a238cf0c` (A-35), `d5f92e26e` (doc), `f5a42a00e` (diario).
  Base aggiornata: merge di dev `b36e3873f`, HEAD **`c9cb27e4c`** (genitori `f5a42a00e` + `b36e3873f`), pulito. La riga
  di `main.py` e il gestore li ha rivisti il coordinatore. `all-backend` su `c9cb27e4c` prima dell'ingresso, nel primo
  slot libero.
- **Il controllo su `ctx` chiesto dal coordinatore** (nota LOW: un `field_validator` con `ValueError(f"… {value}")`):
  provato in processo col gestore vero, `ctx.error` esce come `{}` (un'eccezione si serializza vuota), quindi da lì
  non passa nulla; il valore passa invece da **`msg`** («Value error, …»), che teniamo per scelta. Nessun validatore
  mio né di uno schema con una password mette un valore nel messaggio (`schemas/auth.py`, `users.py` e gli schemi
  email non ne hanno; le regole della password stanno nella rotta, 400 coi soli codici); i messaggi che citano un
  valore (`schemas/settings.py`: orari, giorni, fuso, valuta) non citano segreti. **Niente A-38.** Da aggiungere, alla
  prossima passata di doc, una frase in `security.md#validation-errors`: un validatore non mette mai il valore nel
  messaggio, perché `msg` resta.
- **Backlog**: A-39 (l'avviso del cambio d'indirizzo in `admin/configuration`) e A-40 (l'avviso del limite di
  `user activate` sull'admin in attesa), dalle note del `docs-writer`. A-34 va con A8 (d'accordo il coordinatore).

## A8 — Analisi e contratto (17/10, 02:00; in attesa del via)

Fonti: decisioni del 14/10, punto 4 (D-A5, F15) e P13 (`decisioni-analisi-20261014.md`); §4.8 di questo piano; dal
coordinatore: la sfumatura P13 (a) su `TabBar.svelte` è di A (01:35), A-34 va qui (01:36). Base `c9cb27e4c`.

### Stato reale

- **Il primitivo c'è già**: `utils/runtime/rate_window.py`, `SlidingWindowLimiter` (in memoria, per processo, chiavi
  limitate, orologio iniettabile; un colpo rifiutato non conta), scritto anche per i tentativi di login. E lo usa per
  «password dimenticata» (`FORGOT_BY_ADDRESS` 10/15 min, `FORGOT_BY_IDENTIFIER`) e per la verifica. La chiave per
  indirizzo è di H: `services/platform/client_address.py`, `client_address(request)` (l'header fidato di
  `LIBREFOLIO_CLIENT_IP_HEADER`, altrimenti la connessione) e `client_rate_key()` (IPv6 per /64). Nessuna copia.
- **Login** (`auth.py:~150`): la password si verifica sempre (`verify_password_or_dummy`, stesso costo per un account
  inesistente), poi 401 «Invalid credentials», poi i 403 (`EMAIL_NOT_VERIFIED`, `ACCOUNT_DISABLED`). Nessun limite.
- **Frontend**: il 429 al login è già mappato (`auth.ts:70` → `auth.tooManyAttempts`, A3). `TabBar.svelte` ha già
  `badge` per scheda e la modalità `scrollable` (`tab-bar-scroller`, commit `affae6ffe`), senza sfumatura. Il registro
  `settingsTabs.ts` ha 8 schede; `admin` (impostazioni globali) è **visibile a tutti** (in sola lettura ai non admin),
  `users`, `backup`, `email` solo agli admin.
- **E2E da toccare con P13 (b)**: 8 spec cliccano le schede dell'admin dalla barra (29 clic, 14 via `?tab=`):
  `settings.spec.ts`, `settings/admin-users` (A), `settings/backup` (B), `settings/email-tab`, `email-send-link`,
  `auth-email-verification` (E), `settings/scheduler` (Z), `gallery.spec.ts` (G).

### Proposta: due lotti

**A8a — backend** (F15, controlli di sicurezza, A-34):
- **C1** `services/accounts/login_throttle.py`: `LOGIN_BY_IDENTIFIER` (10 errori in 15 min, identificativo con le sole
  A–Z ripiegate, che l'account esista o no) e `LOGIN_BY_ADDRESS` (50 in 15 min, `client_rate_key`). Prima di bcrypt
  si guarda (`peek`) su entrambe; oltre → **429** `{"error_code": "TOO_MANY_ATTEMPTS"}` con `Retry-After` (secondi,
  il maggiore dei due), la stessa risposta che l'account esista o no. Un errore di password conta su entrambe; un 200
  azzera l'identificativo; i 403 (password giusta, account fermo) non contano.
- **C2** le altre verifiche di password (stesso limite, chiave = l'account): `change-password`, `PUT /auth/profile`
  quando chiede la password attuale, l'eliminazione del proprio account se la chiede. I link (§4.8): un secchio per
  indirizzo dei **token sbagliati** (inspect non valido, setup e reset `TOKEN_INVALID`, invito non valido alla
  registrazione), 50 in 15 min, stesso 429. Il reinvio della verifica di E ha già il suo limite: non lo tocco.
- **C3** `LIBREFOLIO_LOGIN_LIMIT` (`on` predefinito, `off` lo spegne; un altro valore è un errore all'avvio, come
  `LIBREFOLIO_REGISTRATION`), letto in `config/accounts.py`; riga commentata nella sezione di A di `.env.example`; un
  avviso nel log all'avvio se spento. **Corsie di test**: il server di test parte con `off` (file del runner condiviso:
  scrittore da decidere), i test del limite lo accendono in processo con un limitatore e un orologio iniettati.
- **C4** controlli di sicurezza: un registro (`register_security_check(code, fn)`; il primo, di A,
  `LOGIN_LIMIT_DISABLED`, avviso), e `GET /api/v1/security/checks` (solo admin; `{items: [{code, severity,
  params}]}`): file nuovo `api/v1/security.py` più **una riga** in `api/v1/router.py`. Gli altri filoni aggiungono un
  controllo con una riga.
- **C5** A-34: `end_sessions(session, user)` asincrona, `UPDATE … SET session_version = session_version + 1` e
  rilettura del valore; le 9 chiamate; il contratto 5 di `test_session_version.py` riscritto, più un test con due
  sessioni che arrivano a +2.

**A8b — frontend** (scheda «Sicurezza», P13):
- **C6** `features/settings/security/`: `SecurityTab.svelte` e un registro dei controlli del browser (il primo: la
  registrazione aperta su un host non locale, riusando `openRegistrationNoticeFor` di A7b) uniti a quelli del backend;
  ogni avviso con il suo testo (i18n per codice) ed eventuale link; **badge** col numero degli avvisi sulla scheda e sul
  gruppo «Amministrazione».
- **C7** P13 (b): il registro prende `group?: 'administration'` (`admin`, `users`, `backup`, `email`, `security`); la
  barra di sopra mostra le altre schede e una scheda «Amministrazione» (a destra, `settings-tab-administration`); la
  seconda barra mostra quelle del gruppo quando una è attiva; `?tab=users` (e le altre) apre il gruppo su quella
  scheda; gli id `settings-tab-{id}` restano. Un non admin vede nel gruppo solo `admin` (in sola lettura): con una
  scheda sola niente seconda barra, il gruppo la apre direttamente.
- **C8** P13 (a): in `TabBar` (`scrollable`) una `mask-image` con `linear-gradient` sui bordi del contenitore che
  scorre, solo dal lato dove c'è altro da vedere, aggiornata allo scorrimento e al ridimensionamento; nessun colore;
  `data-fade` (`none|start|end|both`) per i test.
- **C9** E2E: un aiuto `openSettingsTab(page, id)` e le 8 spec che cliccano le schede dell'admin passate all'aiuto
  (righe in file di A, B, E, G, Z: scrittore da decidere); la galleria della barra «Amministrazione» dopo G.
- **C10** i18n nelle 4 lingue, doc (admin, utente, developer), riga del CHANGELOG.

**Domande per il coordinatore**: (1) la divisione in A8a/A8b; (2) il nome `LIBREFOLIO_LOGIN_LIMIT`; (3) chi scrive
la riga del runner che spegne il limite sulle corsie e la riga di `router.py`; (4) chi aggiorna le 8 spec E2E (io con
un aiuto comune, oppure ciascun filone); (5) il secchio dei token sbagliati (C2), utile ma non chiesto
esplicitamente.

**Risposte del coordinatore (17/10, 01:41)**: (1) A8a e A8b separati, A8a entra da solo; (2) `LIBREFOLIO_LOGIN_LIMIT`
(`on`/`off`, predefinito `on`) va bene; (3) la riga del runner che spegne il limite sulle corsie la scrivo io e la
rivede H al checkpoint, i miei test API accendono il limite esplicitamente; la riga di `router.py` la scrivo io e la
rivede il coordinatore; (4) le 8 spec E2E le faccio io in A8b con l'aiuto comune `openSettingsTab`, per ultime, dopo
il codice, con un breve congelamento annunciato dal coordinatore ai proprietari (B, E, Z, colori per `gallery`); (5) il
secchio dei token sbagliati **fuori** (token lunghi e casuali: la forza bruta non è praticabile, e un limite per
indirizzo rischia di bloccare utenti dietro lo stesso NAT): backlog **A-41**. `SecurityTab` e la barra
«Amministrazione»: solo ruoli colore, `theme-roles --check` fra i controlli leggeri. Rossi di A8a dopo l'`all-backend`.

**Correzione di C4 (17/10, 01:50), prima dei rossi**: il registro c'è già. `services/platform/config_audit.py` di H
(`ConfigCheck`: `check_id`, `severity` ok/info/warning/error, `i18n_key`, `detail`, `summary`; `CONFIG_CHECKS`,
`run_config_checks()`) è nato **per la scheda «Sicurezza»** («will evaluate the same checks on demand»); E vi aggiunge
`EMAIL_CONFIG_CHECKS` da un suo modulo, H ha anche `check_plugin_secrets(session)` (asincrono, col database). Quindi
niente registro nuovo:
- il controllo di A, `accounts.login_limit` (avviso quando `LIBREFOLIO_LOGIN_LIMIT=off`, i18n
  `auth.checks.loginLimit.*`), sta in un modulo mio (`ACCOUNTS_CONFIG_CHECKS`) ed entra in `CONFIG_CHECKS` con **una
  riga** nel file di H, come quelli di E: così il log dell'avvio lo scrive già `log_configuration_audit()`;
- A8a aggiunge solo l'endpoint che la scheda chiede: `GET /api/v1/security/checks` (solo admin), `run_config_checks()`
  più `check_plugin_secrets(session)`, tutti con la loro gravità (la scheda mostra quelli non `ok`), in
  `api/v1/security.py` più la riga di `router.py`.

### A8a.1 — Rossi (17/10, 01:50–)

- **Dove spegnere il limite sulle corsie**: `dev.py` (~300), dove il server parte in modo test e già mette
  `LIBREFOLIO_DISABLE_DONATION_POPUP=1` per i login degli E2E: `env.setdefault("LIBREFOLIO_LOGIN_LIMIT", "off")`, così
  un valore esplicito vince. Riga per H (revisione al checkpoint). La riga di `config_audit.py` (anche lì H): l'avvio si
  ferma su un valore non valido di `LIBREFOLIO_LOGIN_LIMIT`, accanto a `admin_bootstrap_config()`; e
  `*ACCOUNTS_CONFIG_CHECKS` in `CONFIG_CHECKS`.
- **Due `test-author` su file nuovi** (l'`all-backend` di A7b-2 in corso non li raccoglie: non registrati):
  `test_services/test_login_throttle.py` (C1, C3, C4; puro, orologio e limitatori iniettati) e
  `test_api/test_login_throttle_api.py` (privato: login, indirizzo, cambio password, profilo, interruttore,
  `GET /security/checks`) più `test_api/test_security_checks_api.py` (corsia: `accounts.login_limit` in `warning`, che
  fissa la riga del runner). A-34 (riscrive `test_session_version.py`, già esistente) dopo la fine dell'`all-backend`.
> **⚠️ Fuori pista**: l'`all-backend` di A7b-2 (slot 1, 01:38) ha `--log-dir` nella stessa cartella dove reindirizzavo
> l'uscita: all'avvio il runner archivia quel che trova in `00_archive/` (tar) e il file della redirezione resta senza
> nome. La corsa continua; i risultati si leggono dai log per unità e da `dev.py test --run-status`. D'ora in poi la
> redirezione sta fuori dalla cartella dei log.
- **Rossi dei servizi scritti** (`test-author`, solo file nuovi): `test_login_throttle.py` (LT-001…020) e
  `test_accounts_checks.py` (LE-001…004, LC-001…011, LC-004b): 109 casi, 94 rossi «red until A8a», 15 guardie; provati
  in processo contro una versione di riferimento (106/106) e contro 25 versioni sbagliate (tutte prese). Scelte fissate
  su domanda: il valore non valido in `detail` è quello **senza spazi**; il riassunto di `off` è un testo fisso; l'audit
  si ferma **prima di scrivere qualunque riga**. Da fare dopo l'`all-backend`: `CHECK_IDS` di `test_config_audit.py`
  (di H) prende `check_login_limit`; `*ACCOUNTS_CONFIG_CHECKS` va **prima** di quelli di E (i test di E vogliono la lista
  che finisce con i tre controlli email).
- **Bozze del codice** (`work/a8a/`, a secco pulite, non applicate: il repo non si tocca finché l'`all-backend` gira):
  `login_throttle.py`, `services/accounts/checks.py`, `schemas/security.py`, `api/v1/security.py` (nuovi);
  `apply_a8a.py` per `config/accounts.py` (`login_limit_enabled`), `config_audit.py` (H: import, riga in
  `CONFIG_CHECKS`, la validazione accanto a `admin_bootstrap_config()`), `auth.py` (login, cambio password, profilo),
  `router.py`, `dev.py` (H: `setdefault` del limite spento in modo test), `.env.example` (riga commentata);
  `i18n_add.py` per le tre chiavi `auth.checks.loginLimit.*`.
- **Congelamento della galleria** fino alle ~03:30 (coordinatore, 02:16): niente passi pesanti (`api`, E2E,
  `all-backend`); i rossi delle API di A8a dopo.
- **Rossi delle API scritti** (`test-author`, solo file nuovi): `test_login_throttle_api.py` (privato, 24: LT-API-01…15,
  SC-API-01…06; indirizzi di documentazione per richiesta, orologio finto, bcrypt a costo 4, l'hash fittizio privato)
  e `test_security_checks_api.py` (corsia, 3: SC-LANE-01…03). Oggi: errori di setup (modulo mancante) e 404; contro una
  versione di riferimento in memoria 24/24; dieci varianti sbagliate prese ciascuna dai test giusti.
> **⚠️ Fuori pista (dal `test-author`, punto 5)**: la riga di `dev.py` arriva solo al server della corsia. I processi
> pytest che montano le app in processo (gli harness privati di molti file, consolidati in un processo solo)
> avrebbero il limite **acceso**, con i limitatori del processo e l'orologio vero: dopo 50 errori da `127.0.0.1` fra
> file diversi, 429 spuri in test che si aspettano 401. Cura: anche `backend/test_scripts/conftest.py`
> `os.environ.setdefault("LIBREFOLIO_LOGIN_LIMIT", "off")` (un valore esplicito vince; i test del limite lo accendono
> con monkeypatch). In `apply_a8a.py`; per la revisione di H con la riga di `dev.py`.
- Note del `test-author` per il contratto, nessuna in contrasto: il profilo chiede la password solo per un indirizzo
  davvero nuovo (il resto non si limita); nel cambio di password il limite viene **prima** del controllo della
  password debole (nella bozza è così); l'identificativo come scritto fa del nome utente e dell'email due secchi (~20
  tentativi in 15 minuti per account, sempre sotto i 50 dell'indirizzo): da dire nelle doc.

### A7b-2 — Aggiunta: i numeri non finiti (17/10, 03:02)

- Da X, via coordinatore: un numero non finito in un corpo JSON (`1E+400`, `NaN`) fa portare al 422 di FastAPI
  `input: inf`; il renderer di Starlette (`allow_nan=False`) fallisce e la risposta è un **500**, in tutta l'app.
- **Provato in processo** col gestore vero e un campo `Decimal`: `1E+400`, `-1E+400`, `NaN`, `Infinity` (e `NaN` su un
  `Decimal` con `max_digits`/`decimal_places`) → senza il gestore **500**, col gestore **422** `finite_number`, `msg`
  senza il valore, **nessun `ctx`**. Il gestore di A-35 lo cura già.
- Da aggiungere a `test_validation_errors_api.py` (parte pura: la premessa del 500 e il 422; un caso sulla corsia su una
  rotta vera con un `Decimal`), **dopo** l'`all-backend` in corso, come commit a parte; l'ingresso non lo aspetta.
- Nota fuori da A-35: un campo **`float`** semplice *accetta* `1E+400` (200, `allow_inf_nan=True` predefinito di
  Pydantic); chiesto al coordinatore se serve una riga di backlog e di chi.
- **A-34 in bozza** (`work/a8a/apply_a34.py`, a secco pulito): `end_sessions(session, user)` asincrona con
  `UPDATE … SET session_version = session_version + 1 … RETURNING` e `set_committed_value` (niente `refresh()`, che
  scaricherebbe prima del tempo i campi già cambiati dal chiamante, come `hashed_password`); le 9 chiamate (6 in
  `user_service`, `change-password`, `POST /users/{id}/sessions/revoke`, `complete_admin_setup`). I test: dopo
  l'`all-backend` (riscrive il contratto 5 di `test_session_version.py`, file esistente).
- Il `float` che accetta `1E+400`: riga di backlog di H (H-32), la registra il coordinatore.

### A7b-2 — Revisione di E (17/10, 03:08, «R13-SEC4»)

Le tre note di A sono chiuse; niente sopra la soglia; nulla blocca l'ingresso. Quattro voci basse nel backlog: **A-38**
(`msg`/`ctx` con parti del valore dove un validatore lo formatta: in parte coperto dal test di A-35 su tutta la
risposta delle rotte con credenziali), **A-42** (gara fra un setup e un nuovo link: rifiutare se un altro link di setup è
già consumato), **A-43** (ritirare i link anche alla disattivazione, per i database delle build precedenti), **A-44**
(annullare l'admin iniziale mai attivato).
- **`all-backend` su `c9cb27e4c`** (slot 1, 01:38–03:10): rc 0; API 2 263, servizi 13 774, utils 3 287, schemi 1 833,
  e2e del backend 10, DB/BRIM/migrazioni 1 885: circa 23 050 verdi, 0 rossi; `--run-status` con ogni unità fatta.
- **A7b-2 entrato** (17/10, ~03:12): dev `90219770c` più la cura `28059249a` (conflitto su `overview.md` accanto a H-29,
  sistemato dal coordinatore) e il CHANGELOG 🔒 `81b8db4e1`. La mia base resta `c9cb27e4c` (l'avanzamento rapido non
  passa per il diario sporco): la punta arriva al prossimo checkpoint, quello del seguito di A-35.

### A8a.2 — Rossi osservati (17/10, 03:15–)

- Registrate le quattro unità: `services login-throttle`, `services accounts-checks` (pure), `api login-throttle`
  (pura: app in processo), `api security-checks` (corsia).
- `services login-throttle` **32 rossi**, 1 guardia verde; `services accounts-checks` **62 rossi**, 14 guardie verdi
  (03:12–03:13, carico 46): i 94 + 15 previsti dal `test-author`, ciascuno sul suo messaggio.
- **`test_config_audit.py`** (di H, per la revisione di H): `CHECK_IDS` impara `check_login_limit` con un import pigro;
  ordine e appartenenza di `CONFIG_CHECKS` in un test nuovo, rosso fino ad A8a (i controlli di A subito prima dei tre di
  E); il resto dei 90 casi invariato. In più `_configure` toglie `LIBREFOLIO_LOGIN_LIMIT`, come già le `SMTP_*`: col
  predefinito `off` del `conftest` 16 casi di H che vogliono «tutti ok» sarebbero diventati rossi.
- **Seguito di A-35** (numeri non finiti, `test_validation_errors_api.py` §4): parte pura 20 casi (premessa del 500
  senza il gestore, 422 in JSON stretto con), corsia 2 casi su `POST /fx/currencies/convert` (una lettura, `Decimal`,
  account propri); verdi all'arrivo. Descrizione del runner aggiornata (sette account, i numeri non finiti).
- **Rossi di A-34 scritti** (`test-author`, solo `test_session_version.py`, 03:30): contratto 5 riscritto (incremento
  nella transazione del chiamante, `user not in session.dirty`, una connessione nuova legge ancora il vecchio valore,
  rollback), più due test nuovi: un campo già cambiato dal chiamante (`hashed_password`) resta in sospeso e lo scrive il
  commit del chiamante; **la gara** (due sessioni caricano l'account a 6; cambio password + «esci ovunque» → **8**, il
  cookie riemesso a 7 rifiutato). Ordine fissato, niente thread né attese. La forma (`async`, `(session, user)`) si
  verifica in `_end_sessions()`: oggi 5 rossi su quel messaggio, 51 verdi. In processo: con l'`end_sessions(user)` di
  oggi la gara salva **7**; la versione di riferimento passa tutto; sette versioni sbagliate prese (incremento
  sull'oggetto, `update(User)` ORM che scarica prima, `refresh`, assegnazione normale, commit dentro…).
  `_end_sessions_of(engine, user_id)` mantiene la firma.
> **⚠️ Fuori pista**: `test_backup_apply.py` (di B) importa `_end_sessions_of` da questo file: il suo test (i)
> `test_a_password_change_after_the_restore_raises_that_account_alone_by_one` (unità `services backup-apply`) è rosso
> fino ad A8a sullo stesso messaggio. Decisione: **nessun ripiego** che accetti anche la forma vecchia (codice morto
> dopo A8a); test e codice entrano nello stesso commit, quindi su dev non è mai rosso. `services backup-apply` entra nei
> verdi da provare. Previsione per l'integrazione: chi aggiunge altrove una chiamata `end_sessions(user)` (B, E) ha un
> `TypeError` subito, non un errore silenzioso; da dire nel handoff.
- **Bozze corrette** (03:40): A8a entra senza la scheda «Sicurezza» (è di A8b). Le frasi che la davano per esistente ora
  dicono «i controlli della configurazione» (`login_throttle.py`, `checks.py`, la docstring di `login_limit_enabled`) e,
  in `.env.example`, «il server avvisa nel log a ogni avvio». L'eliminazione del proprio account non chiede la password
  (`auth.py` `delete_own_account`): la clausola di C2 «se la chiede» non si applica, niente da limitare.
- **Per A8b, C11** (trovato rileggendo il frontend): il 429 nuovo del cambio password e del cambio d'indirizzo non ha
  parole sue. `PasswordChangeModal` mostra il `message` inglese del backend (attraverso `trySave`); `ProfileTab`
  (`describeRefusal`) mostra «aggiornamento non riuscito». Raro (10 password attuali sbagliate in 15 minuti), quindi
  accettabile fra l'ingresso di A8a e quello di A8b. In A8b: `TOO_MANY_ATTEMPTS` → un testo tradotto, nelle 4 lingue,
  in entrambi, con i loro Vitest.
- **Doc in scrittura** (`docs-writer`, 03:40, senza comandi `dev.py` per il congelamento): `admin/configuration`
  (variabile, sezione `#login-limit`, controlli d'avvio), `admin/connection_checks` (`#client-address`), utente
  (`getting-started`, `settings/profile`), developer `architecture/security.md` (limite, controlli e endpoint, A-34,
  numeri non finiti e la frase di A-38). Build strict e controllo dei link li lancio io quando il carico lo permette.
> **⚠️ Fuori pista (bozza di A-34 sbagliata, presa rileggendola contro i test)**: la bozza usava `update(User)` ORM con
> `synchronize_session=False` via `session.execute()`. Un UPDATE ORM fa comunque l'**autoflush** prima di partire,
> quindi l'hash già cambiato dal chiamante sarebbe stato scritto da `end_sessions`: il test «un campo cambiato prima resta
> in sospeso» l'avrebbe preso (è la riga «ORM `update(User)`» della matrice del `test-author`). Corretta: istruzione
> Core su `User.__table__` (stile di `models.py`, `# type: ignore[attr-defined]`), eseguita su
> `await session.connection()` (nessun flush), poi `set_committed_value`. Tolto l'import di `update`. Verificati anche
> `expire_on_commit=False` (il cambio password legge `session_version` dopo il commit per il cookie) e nessun
> `onupdate` su `users.updated_at` (un'istruzione Core lo farebbe scattare). Prove a secco dei due script pulite.
- **Rossi dei servizi osservati** (03:40–03:42, carico 31): `services session-version` **5 rossi** / 51 verdi,
  `services config-audit` **1** / 90, `services backup-apply` **1** / 227 (il test (i) di B): ciascuno sul suo
  messaggio («red until A8a (A-34): … a plain function of (user)»; «`accounts.checks` does not exist»). Porta 6182
  libera dopo.
- **Rossi delle API non ripassati dal runner**: ogni `dev.py test api …` avvia il server della corsia
  (`_SERVER_BACKED_CATEGORIES` in `_cli.py`), anche per un'unità pura, quindi è un passo pesante, vietato dal
  congelamento. Prova dei rossi: le corse in processo dei `test-author` (`api login-throttle` 24 errori di setup, modulo
  mancante; `api security-checks` 3 × 404; contro una versione di riferimento 24/24, dieci varianti sbagliate prese).
  Per non fermare il lotto il codice entra ora; i verdi delle API nel primo slot. Da dire nel handoff.

### A8a.3 — Codice ✅ (17/10, 03:44)

- `apply_a8a.py` e `apply_a34.py` applicati (bozze corrette prima: la scheda «Sicurezza» non data per esistente;
  A-34 con l'istruzione Core). `i18n_add.py`: le tre chiavi `auth.checks.loginLimit.*` nelle 4 lingue
  (`frontend/src/lib/i18n/auth/*.json`), `i18n build` e `i18n check` puliti (4 941 chiavi). Nel messaggio `ok`
  «un nome utente» → «un nome utente o un'email» (l'identificativo è quello scritto), in tutte e 4 le lingue.
- `ruff` e `black` puliti su 21 file. `dev.py`: 43 rilievi di ruff e la riformattazione di black **identici a HEAD**
  (preesistenti, le mie 3 righe non ne aggiungono).
> **⚠️ Fuori pista (guardia di H, `services config-package`, regola b)**: nessun modulo di `backend/app/` fuori da
> `config/` legge `os.environ`. La bozza di `checks.py` lo leggeva per mettere il valore non valido in `detail`. Cura:
> accessore `login_limit_value()` in `config/accounts.py` (con `_blank_to_none`, quindi senza spazi), usato da
> `login_limit_enabled()` e da `checks.py` (tolto `import os`). Trovato leggendo le guardie che scorrono i moduli,
> prima dei verdi.

### A8a.4 — Verdi dei servizi ✅ (17/10, 03:46–04:03)

- 13 unità, una alla volta, carico < 50 (lo script aspetta da solo; picchi a 225 fra le 03:56 e le 04:00):
  `login-throttle` 33, `accounts-checks` 76, `config-audit` 91, `config-package` 848, `config-env-example` 38,
  `session-version` 56, `admin-bootstrap` 190, `account-tokens` 76, `user-profile` 52, `registration` 151,
  `email-checks` 87, `plugin-secrets-check` 11, `backup-apply` 228: **1 937 verdi, 0 rossi**. Porta 6182 libera.

### A8a.5 — Doc e un buco trovato dalle doc (17/10, 03:40–04:15)

- `docs-writer` (senza comandi): `admin/configuration` (riga della variabile, «🚦 Failed Sign-ins» `#login-limit`,
  controlli d'avvio), `admin/connection_checks` (`#client-address`), `user/getting-started`, `user/settings/profile`,
  developer `architecture/security.md` (nuove `#login-limit` e `#security-checks-endpoint`, A-34, numeri non finiti e
  A-38), `backend/email.md` (`#rate-window`), `frontend/components/features/auth.md` (frasi diventate false).
> **⚠️ Fuori pista 1 (dal `docs-writer`)**: in `dev.py` «an explicit value still wins» era falso:
> `configure_test_runtime()` toglie ogni `LIBREFOLIO_*` di `.env` e della shell (`scripts/cli_base.py`
> `_test_lane_drops`) prima di `env = os.environ.copy()`. La riga ora è un'assegnazione semplice, `env[...] = "off"`,
> come quella del popup, con il commento giusto (per la revisione di H). Il `setdefault` del `conftest.py` invece
> serve: vale per i processi pytest.
> **⚠️ Fuori pista 2 (dal `docs-writer`, verificato)**: `POST /email/verification/resend` di E
> (`services/email/verification.py` `resend_verification`) controlla la password dell'accesso (sbagliata → 401,
> giusta su un account attivo → 409 `EMAIL_VERIFICATION_NOT_NEEDED`) col solo limite per indirizzo di E: con il limite
> per identificativo di A8a diventava la via per aggirarlo. È il quarto e ultimo controllo di password dell'app (gli
> altri tre ora sono limitati). **Decisione del coordinatore (04:10)**: lo scrivo io in A8a, E rivede (E-R13-SEC6
> aspetta A8a). **Indicazioni di E (04:12)**: `refusal` dopo `RESEND_BY_ADDRESS` e prima della ricerca dell'account;
> `record_failure` nel ramo unico `if not password_ok or user is None:` (altrimenti oracolo d'esistenza);
> `record_success` subito dopo, prima dei controlli `is_active` (come cambio password e profilo; diverso dal login,
> che non azzera sui 403: va bene, serve la password giusta); il 429 resta `EmailRateLimitedError` →
> `EMAIL_RATE_LIMITED`, il frontend non cambia. E pensava che tre punti dei suoi test cambiassero: col predefinito `off`
> del `conftest` (il suo `_no_inherited_variables` toglie solo `SMTP_*` e `INHERITED`) restano come sono; detto al
> coordinatore, da confermare con `services email-verification` e `api email-verification`.
- **Rossi in scrittura** (`test-author`, solo `test_login_throttle_api.py`): R1 resend sbagliati → login 429 (account
  esistente e sconosciuto), R2 login falliti → resend 429 `EMAIL_RATE_LIMITED` senza bcrypt e senza contare, R3 la
  password giusta al resend azzera (409 attivo, 403 disattivato), R4 il resend conta anche sull'indirizzo.
- **Bozza** `work/a8a/apply_resend.py` (a secco pulita): le righe in `resend_verification`, la sua docstring, e la
  docstring della rotta in `api/v1/email.py` (descrizione OpenAPI: il 429 elenca anche il limite dell'accesso).
- **Da fare nelle doc, dopo il resend**: `security.md` (il resend ora è limitato), `backend/email.md`
  (`#verification-resend`), `developer/architecture/settings.md` (gli accessori di `config/accounts.py`:
  `login_limit_value()`, `login_limit_enabled()`) e `developer/api/index.md` (il router `/security`), più l'accessore
  nella sezione dei controlli.

### A8a.6 — Doc ✅ (17/10, 04:17–04:25)

- Seguito del `docs-writer` (stesse regole): il resend come quarto controllo sotto il limite (`security.md`
  `#login-limit`, la tabella delle rotte a quattro righe; `backend/email.md` `#verification-resend`, `#rate-window`,
  `#api-verification-resend`, `#verification-frontend`; `admin/configuration` `#login-limit`; `user/getting-started`
  `#verify-email`), l'accessore `login_limit_value()`, la riga di `dev.py` senza `setdefault`,
  `developer/architecture/settings.md` (accessori e variabile) e `developer/api/index.md` (`/email`, `/security`).
- Io: una riga nella tabella `#verification-limits` di `admin/email.en.md` (di E; pagina senza traduzioni, quindi
  nessun debito; E la vede con il resend).
> **⚠️ Fuori pista**: la build strict è caduta su **quella mia riga**: `admin/email.en.md` non ha traduzioni, quindi
> la build italiana la usa com'è, e il suo link `configuration.md#login-limit` va su `configuration.it.md`, che non ha
> l'ancora (nessuna sezione 1.3 vi è tradotta: mancano anche `#accounts`, `#user-limit`, `#initial-admin`). Le pagine
> solo inglesi infatti non linkano ancore nuove di pagine tradotte. Cura: link alla pagina senza ancora, «see *Failed
> Sign-ins* in [Configuration](configuration.md)».
- `dev.py mkdocs build` (strict) **verde** (3 084 URL relativi risolti); `dev.py mkdocs check-links` **verde** (97
  link validi, nessun link di confine rotto). `translate-validate`: 1 164 errori, il debito di traduzione già noto
  della 1.3 (es. `getting-started` it indietro da A5/A7) più le parti nuove; nessuna traduzione ora (solo su richiesta
  del developer).
- Pagine con debito nuovo: `admin/configuration` (riga, «Failed Sign-ins» `#login-limit`, riga e frase dei controlli
  d'avvio, «Related»), `admin/connection_checks` (`#client-address`), `user/getting-started` (nota del login,
  `#verify-email`), `user/settings/profile` (un punto e un paragrafo). L'ancora `{: #login-limit }` va tenuta nelle 4
  lingue.
- Dal `docs-writer`, fuori perimetro: `developer/api/index.md` dice che `/auth` fa «token refresh», falso → backlog
  **A-45**. A-34 chiusa nel backlog (✅, il SHA lo mette il coordinatore).

### A8a.7 — Il resend sotto il limite: rossi, codice, verdi ✅ (17/10, 04:05–04:26)

- **Rossi** (`test-author`, solo `test_login_throttle_api.py`, sezione 7 `TestResend`, LT-API-16…19, 8 casi): resend
  sbagliati → login 429 (account, nessun account, l'email in maiuscole: l'identificativo come scritto); login bloccato
  (per identificativo e per indirizzo) → resend 429 `EMAIL_RATE_LIMITED` con `retry_after` = `Retry-After` = l'attesa
  esatta, senza bcrypt e senza contare (conteggi dei limitatori uguali prima e dopo), poi l'accesso a tempo scaduto;
  la password giusta al resend azzera (409 attivo, 403 disattivato, tutto scritto come email); un resend sbagliato
  conta sull'indirizzo. `RESEND_BY_ADDRESS` di E sostituito da uno privato sull'orologio finto. Contro una copia in
  memoria della cura 32/32; 15 varianti sbagliate prese (tabella nel resoconto del `test-author`; 4 solo dalle sue
  aggiunte: rifiuto senza indirizzo, rifiuto contato, conteggi per username).
- **Rossi osservati da me** (in processo, senza corsia né conftest: `--noconftest`, `--basetemp` e dati privati,
  `LIBREFOLIO_TEST_MODE=1`, niente bytecode; carico 21): **8 rossi** sui loro messaggi (429 atteso, 200/401/409
  ottenuti; `[401, 429×9]` invece di dieci 401). Il passaggio dal runner (`api login-throttle`) è nello slot: ogni
  `dev.py test api …` avvia il server della corsia.
- **Codice** (`work/a8a/apply_resend.py`): in `resend_verification` (E) `refusal` dopo `RESEND_BY_ADDRESS` e prima
  della ricerca → `EmailRateLimitedError(retry_after)`; `record_failure` nel ramo unico password sbagliata/account
  sconosciuto; `record_success` subito dopo, prima dei controlli `is_active`; docstring del servizio e della rotta
  (`api/v1/email.py`, descrizione OpenAPI). Nessun ciclo d'import nuovo (`verification.py` importava già
  `user_service`). `ruff`/`black` puliti; `api sync` rc 0 (solo la descrizione; il client è ignorato da git).
- **Verdi**: il file intero in processo **32/32**; `services email-verification` (E) **125** verdi, i tre punti dei
  test di E invariati, come previsto (`conftest` → limite spento); `services config-package` 848.
- **Per lo slot** (`work/a8a/slot_api.sh`, un'unità alla volta): `login-throttle`, `security-checks`,
  `validation-errors`, `auth`, `registration`, `admin-setup`, `users-admin`, `session-revocation`, `account-deletion`,
  `plugin-settings`, `email`, `email-verification`, `email-verification-hooks`, `email-change-notice`.
- **Controlli leggeri in più** (04:26–04:28, carico ~20): `dev.py i18n audit` 4 941 chiavi, 0 inutilizzate, 0 mancanti
  (le tre `auth.checks.loginLimit.*` le trova scritte intere in `checks.py`); `utils runtime-isolation` 232 verdi (la
  riga nuova di `dev.py` nell'ambiente del server di test). I file di test che tolgono tutti i `LIBREFOLIO_*`
  (`test_config_audit`, `test_email_checks`, `test_config_secrets`, `test_backup_*`, `test_runtime_isolation`,
  `test_release_image_contract`, `test_rate_limit_*`, `test_plugin_settings_service`) non fanno accessi: il limite
  acceso lì non tocca nessuno.
- **Coordinatore (04:30)**: `all-backend` **non serve** (il suo cancello dopo gli ingressi copre le suite vicine); slot
  tutto mio (il terzo, ~25 min) alla fine del blocco della galleria (~04:35, me lo dice lui), in parallelo a X e Y. La
  riga di `dev.py` (`env[...] = "off"`) va in revisione ad H al checkpoint.
- **Da H, via coordinatore (04:30)**: la docstring di `test_admin_setup_api.py` diceva ancora che `/auth/setup` su
  un'istanza bloccata «aspetta una decisione del developer (A7)». Decisa in P16(d): resta fuori da
  `ALLOWED_WHEN_BLOCKED` e chi non ha sessione riceve il 401 di `get_current_user`. Commento aggiornato (rimanda a
  `test_instance_block.py`, che fissa la lista per nome e per rotta); nessun'altra menzione stantia. `api admin-setup`
  è già nello slot.
- **Congelamento FE8b di W** (04:30, fino al «finito» del coordinatore): transazioni del frontend,
  `CompactCashCell*`, `_frontend_transaction.py`, `_frontend_utility.py`. A8a non li tocca. Per A8b: le righe dei
  Vitest nuovi in `_frontend_utility.py` vanno chieste al coordinatore se il congelamento dura ancora.
  Finito alle 04:31 (`31335fe26`): i file delle transazioni ora stanno in `frontend/src/lib/features/transactions/`.

### A8a.8 — Verdi delle API nello slot 3 ✅ (17/10, 04:38–04:53)

- `work/a8a/slot_api.sh slot3`, un'unità alla volta, corsia 6182, carico 22–56: `login-throttle` 32, `security-checks`
  3, `validation-errors` 53, `auth` 95, `registration` 102, `admin-setup` 50, `users-admin` 100,
  `session-revocation` 11, `account-deletion` 9, `plugin-settings` 14, `email` 158, `email-verification` 49,
  `email-verification-hooks` 16, `email-change-notice` 14: **706 verdi, 0 rossi**. Porta 6182 libera prima e dopo.
- `security-checks` sulla corsia: `accounts.login_limit` è `warning` (il server della corsia gira col limite spento):
  la riga di `dev.py` funziona. `email-verification` invariato con il resend sotto il limite (il `conftest` lo spegne).

### A8a — Definizione di fatto ✅ (17/10, 04:55)

- Test: servizi 15 unità (2 910) + `utils runtime-isolation` 232 + API 14 unità (706), tutti verdi; rossi osservati
  prima del codice (servizi dal runner; resend e API del limite in processo, perché ogni unità `api` avvia il server
  della corsia). `all-backend` non richiesto dal coordinatore.
- Statici: `ruff`/`black` puliti su 23 file Python (`dev.py`: rilievi identici a HEAD); `git diff --check` pulito;
  `i18n check`/`audit` puliti; `api sync` rc 0 (client ignorato da git).
- Doc: build strict e `check-links` verdi; debito di traduzione elencato in A8a.6.
- Revisioni da fare al checkpoint: H (`dev.py`, `config_audit.py`, `conftest.py`, `test_config_audit.py`), il
  coordinatore (`router.py`), E (resend in `verification.py` e `email.py`, le righe delle sue pagine di doc).
- Stato: **FROZEN** 🧊 dopo l'handoff.

### A8a — Committato; aggiornamento di base con un conflitto (17/10, 04:55–05:02)

- Commit del coordinatore: `dc38b9f8c` (test di A-35), `66873b0c9` (feat), `4a93f1f54` (doc), `e7984dd46` (diario);
  `router.py` rivisto da lui, OK. A-36 (backlog) è arrivato dopo il commit del diario: resta da committare.
- Merge di dev (`fd6886bb0`) nel mio ramo, aperto dal coordinatore; un conflitto, `developer/backend/email.md`, con
  E-11 (il 401 del resend col codice `INVALID_CREDENTIALS`, il 502 senza `smtp_code`, il paragrafo sul 401 del
  blocco). Risolto unendo i due lati: la riga di `emailText.ts` di dev **più** «the limit on failed sign-ins» fra i
  429 (prenderla intera da dev avrebbe tolto l'aggiunta di A8a); il 401 codificato di E-11 «counted as a failed
  sign-in» col link; il 429 con i due limiti prima della password, gli altri per account e il budget orario; il 502
  senza `smtp_code`; la frase «Only the 401 and the two 429s before the password…»; il paragrafo di E-11 sul blocco.
- Rivisti anche i file condivisi uniti da Git senza conflitto: `auth.py` (docstring di E-9), `email.py` (401 di E-11;
  le mie righe del 429 intatte), `verification.py` (chiave della casella di E; le mie righe del resend intatte),
  `dev.py` (H-24), `admin/email.en.md` (la riga della casella di E-11 accanto alla mia), `security.md` («Secure
  Backups» di B, «Numbers in Requests» di H-32: coerente col mio paragrafo sui `Decimal` non finiti). I miei test del
  resend guardano solo lo stato, quindi il 401 codificato di E-11 non li tocca.
- Cancelli sull'albero unito: `mkdocs build` strict e `check-links` verdi; `test_login_throttle_api.py` in processo
  32/32; servizi `email-verification` 127, `login-throttle` 33, `accounts-checks` 76, `config-audit` 91,
  `session-version` 56. Porta libera. Messo in stage solo `email.md`; il merge commit lo fa il coordinatore.

## A8b — Contratto (17/10, 05:05; base `125c19f0e`)

Rispetto all'analisi A8 (C6–C10) nulla è cambiato nei file: `settingsTabs.ts`, `TabBar.svelte`, la pagina e i loro test
sono come a `c9cb27e4c`; le spec E2E che cliccano le schede del gruppo sono sempre 8. In più: **C11** (il 429 nuovo
del cambio password e del profilo). Dettagli fissati ora (scelte mie nel perimetro approvato, dette al coordinatore):

- **Registro** (`settingsTabs.ts`): `SettingsTab` prende `group?: 'administration'`, `badge?: (ctx) => number`,
  `prefetch?: (ctx) => void`; `SETTINGS_TAB_GROUPS` = `administration` (`settings.administration`, icona `Shield`,
  `alignEnd`). Membri: `admin` (etichetta ora `settings.globalSettings`, icona `Settings2`, perde `alignEnd`), `users`,
  `backup`, `email`, e la nuova `security` (`settings.security`, `ShieldCheck`, 140, solo admin, badge e prefetch dal
  negozio dei controlli). `settingsBar(tabs, groups, ctx)`, pura: le voci della barra alta (schede senza gruppo, e un
  gruppo dove ha almeno un membro visibile, al posto del suo primo membro).
- **Pagina**: barra alta con `settings-tab-administration` (badge = somma dei membri); seconda barra
  (`settings-subtabs`) solo con ≥ 2 membri visibili, coi `settings-tab-{id}` di oggi; clic sul gruppo → il primo
  membro visibile (nulla se ce n'è già uno attivo); `?tab=<membro>` apre il gruppo su quel membro, `?tab=administration`
  sul primo; un non admin ha solo `admin` → niente seconda barra; `prefetch(ctx)` delle schede visibili all'avvio e a
  ogni cambio di contesto; il titolo del telefono è l'etichetta del membro attivo.
- **Sfumatura** (`TabBar`, solo `scrollable`): `data-fade` = `none|start|end|both` sul contenitore che scorre
  (`start` se c'è altro a sinistra, `end` a destra), aggiornato a scorrimento, ridimensionamento e cambio di schede;
  la maschera con le utilità `mask-l-*`/`mask-r-*` di Tailwind 4.1, nessun colore.
- **Scheda Sicurezza** (`features/settings/security/`): `securityChecksApi.ts` (il client generato),
  `securityFindings.ts` puro (i controlli non `ok` per gravità error > warning > info, poi quelli `ok`; il controllo del
  browser `accounts.openRegistration` da `openRegistrationNoticeFor`; azioni interne: `email.*` → scheda Email,
  `platform.plugin_secrets` → Plugin; `attentionCount` = error + warning), `securityChecks.svelte.ts` (stato, una
  lettura, `reload()`), `SecurityTab.svelte` (caricamento, errore con riprova, elenco, «tutto a posto», i superati in
  un `<details>`, «controlla di nuovo»); solo ruoli colore.
- **C11**: `TOO_MANY_ATTEMPTS` → `settings.tooManyPasswordAttempts` in `PasswordChangeModal` e in `ProfileTab`.
- **i18n** (4 lingue): `settings.administration`, `settings.securityTab.*`, `settings.tooManyPasswordAttempts`.
- **E2E (C9)**: per ultime, con l'aiuto `openSettingsTab`, dopo il congelamento annunciato dal coordinatore.

### A8b.1 — Rossi (17/10, 05:10–)

- Quattro `test-author` in parallelo su file distinti: registro e pagina (`settingsTabs.test.ts`,
  `page.tabs.test.ts`); sfumatura (`TabBar.test.ts`); Sicurezza (nuovi `security/*.test.ts` e le loro righe nel
  runner); C11 (`PasswordChangeModal.test.ts`, `tabs/ProfileTab.test.ts`).
- **Coordinatore (05:12)**: contratto di A8b OK. Ha chiesto alla squadra dei colori («IM», i colori delle impostazioni)
  di `TabBar`, `settingsTabs` e della pagina: i rossi sì, ma **prima di toccare `TabBar` e il markup della pagina**
  aspetto la sua parola. Per prudenza aspetto anche per `settingsTabs.ts`, `PasswordChangeModal` e `ProfileTab` (sono
  impostazioni: potrebbero essere nel lotto IM); i file nuovi di `security/` si possono scrivere.
- **Via della squadra dei colori (05:16)**: IM non ha lotti aperti su `settingsTabs.ts`, `TabBar.svelte`, la pagina e
  `SettingsLayout.svelte` (tutti a zero classi di tavolozza nel ratchet). Regole: `settings-subtabs` con gli stessi
  ruoli della barra principale (un aspetto diverso solo con ruoli esistenti, da dire al coordinatore per il punto 33);
  `SecurityTab` segue la convenzione degli stati di `STATUS_TONES`, scritta nel componente (tinta `bg-lf-X-soft
  text-lf-X-on-soft` + `border-lf-X-line`, chip neutro `bg-lf-neutral text-lf-secondary`), **nessuna tabella nuova**
  in `toneClasses.ts` senza chiedere. All'ingresso il coordinatore avvisa i colori (punto 33, una corsa G filtrata).
- **Bozze del codice** (`work/a8b/`, a secco pulite, non applicate finché i rossi non sono osservati):
  `new/{securityChecksApi.ts, securityFindings.ts, securityChecks.svelte.ts, SecurityTab.svelte}` (tinte per gravità
  `bg-lf-X-soft text-lf-X-on-soft border-lf-X-line` scritte nel componente, chip neutro per i superati, chiavi intere
  per le etichette delle gravità), `new/settingsTabs.ts` (gruppo, `badge`, `prefetch`, `settingsBar`),
  `new/page.svelte` (barra alta, `settings-subtabs`, `?tab=` di gruppo, `prefetch` non tracciato: un prefetch legge lo
  stato che riempie, e un errore persistente lo farebbe ripartire in un ciclo), `apply_a8b.py` (sfumatura di `TabBar`
  con `mask-l-from-[calc(100%-1.5rem)]`/`mask-r-from-…`: verificato col compilatore di Tailwind 4.1.18 che generano
  `linear-gradient(to left|right, black X, transparent 100%)` composte in `intersect`, nessun colore nostro; G4 del
  cancello dei colori guarda solo i valori arbitrari con un colore; C11 in `PasswordChangeModal` e `ProfileTab`),
  `i18n_add.py` (15 chiavi nelle 4 lingue).

## A8a-N70 — Il limite per indirizzo dietro un proxy locale non fidato (17/10, 05:14–)

- **Da E (R13-SEC6, MEDIO 8/10)**: dietro un proxy inverso non configurato (l'immagine Docker: uvicorn senza
  `--forwarded-allow-ips`, `LIBREFOLIO_CLIENT_IP_HEADER` vuota) tutti i visitatori hanno l'indirizzo del proxy: 50
  tentativi sbagliati di chiunque, ~1 al secondo, rifiutano **tutti** gli accessi (anche con la password giusta), il
  cambio password, il cambio d'indirizzo e il resend. A8a resta fuori da dev finché non è curato.
- **Decisione notturna N70** (coordinatore) e **punti vincolanti di E**:
  1. Il limite per indirizzo **non si applica** quando il pari è **locale** (RFC 1918, `fc00::/7`, `127/8`, `::1`,
     `169.254/16`, `fe80::/10`) **e** c'è un'intestazione d'inoltro (`X-Forwarded-For`, `Forwarded`, `X-Real-IP`) che
     uvicorn non ha applicato; valutato per richiesta. Un pari pubblico non lo fa scattare: su un'istanza esposta
     direttamente l'intestazione falsa di un attaccante non cambia nulla (il mio punto 1, uguale a quello di E). Il
     limite per identificativo resta. Un avviso per processo, senza indirizzi.
  2. La rilevazione è di H: `forwarded_by_untrusted_proxy(request)` in `services/platform/client_address.py`, col
     controllo «locale» dentro (H-36). I proxy pubblici restano alla configurazione; il controllo di sicurezza che
     informa quando le intestazioni arrivano da un pari pubblico non fidato è di H.
  3. Mio: `login_throttle.limit_address(request)` = `client_address(request)`, oppure `None` (salta il limite per
     indirizzo) quando l'aiuto di H dice vero, con l'avviso una volta per processo; `auth.py` lo usa nei tre punti, il
     resend di E lo riceve con un kwarg nuovo `limit_address` di `resend_verification` (la rotta lo calcola).
  4. **LRU** in `rate_window.py` (di E, sua revisione): si sfratta la chiave meno usata **non piena** (piena = conteggio
     vivo ≥ il limite predefinito); se tutte sono piene, la più vecchia piena. Mai rifiutare chiavi nuove, mai senza
     limite. Ne beneficiano anche i limitatori di E.
  5. Doc: l'avvertenza del proxy in «Failed Sign-ins» (`admin/configuration.en.md`).
  6. Poi lo slot sulla revisione unita, con anche `services email-verification`, `api email-verification`,
     `api email`, `api email-change-notice` (le mie prove erano prima del merge con E-9/E-11).
- I «cookie del dispositivo» (un browser già entrato salta i limiti): scelta di prodotto, al developer.
- **Coordinatore (05:16)**: punto 1 OK (uguale a E); punto 2 OK, `forwarded_by_untrusted_proxy(request)` nel file di
  H, col controllo locale dentro (lo scrive H); `limit_address(request)` mio, il resend col kwarg; punto 3 OK (LRU nel
  file di E, sua revisione). Via ai rossi di N70.
- **Punti di E su `rate_window.py`** (05:18, li controlla al checkpoint): «piena» solo sui colpi vivi dopo la potatura,
  contro il `limit` del costruttore; **scansione limitata**: al più K voci dal fondo LRU (nuovo parametro solo-chiave
  `eviction_scan=32`, `< 1` → `ValueError`), altrimenti la più vecchia — senza tetto una pioggia di chiavi piene farebbe
  ogni colpo O(`max_keys`) sotto il lucchetto, e i `FORGOT_BY_*` di E contano prima di bcrypt (amplificatore di CPU);
  aggiornare nello stesso lotto il contratto 8 e RWL-014…016 di `test_rate_window.py`, un caso nuovo (spazio per 2, una
  piena e più vecchia, una non piena: la nuova sfratta la non piena), e `developer/backend/email.md` `#rate-window`.
- Rossi in scrittura: `test-author` LRU (`test_rate_window.py`, aggiornato coi punti di E) e `test-author` proxy
  (`test_login_throttle.py` unitario con l'aiuto di H finto, `test_login_throttle_api.py` con l'aiuto vero: rossi
  finché l'aiuto di H non arriva nel mio ramo).
- **Bozza** `work/a8a/apply_n70.py` (a secco pulita): `rate_window.py` (`eviction_scan=32`, `_evict_one()`: la prima
  non piena fra le K meno usate, altrimenti la più vecchia; la chiave nuova mai; `None` è una chiave, quindi un
  segnaposto proprio), `login_throttle.limit_address(request)` (l'aiuto di H cercato sul modulo al momento della
  chiamata: il codice si importa anche prima che l'aiuto arrivi; avviso una volta per processo, senza indirizzi),
  `auth.py` (i tre punti), `verification.py` (`limit_address` con `...` come «non dato» → `address`, così un chiamante
  che lo dimentica resta col limite per indirizzo, il lato sicuro), la rotta di E (`email.py`).
- **Rossi C11 scritti** (`test-author`, 05:28): `PasswordChangeModal.test.ts` (1 rosso: la chiave al posto del
  `message` inglese; guardie: campi intatti e abilitati, nessun successo né toast; un 429 con un altro codice, una frase
  semplice, una pagina HTML di un proxy, e `TOO_MANY_ATTEMPTS` su un 400 restano come oggi), `ProfileTab.test.ts` (2
  rossi, salvataggio della riga e «salva tutto»: `data-error-code="TOO_MANY_ATTEMPTS"`, la chiave, l'indirizzo e la
  password tenuti; 6 guardie). Oggi 3 rossi, 151 verdi. Nella bozza: in `ProfileTab` il 429 tiene **anche la password**
  (oggi ogni rifiuto con codice la svuota): `refusal.code && refusal.code !== 'TOO_MANY_ATTEMPTS'`; il messaggio sparisce
  dopo 5 s come gli altri (non fissato).
- **Rossi della sfumatura scritti** (`test-author`, 05:30): `TabBar.test.ts`, 19 casi in un `describe` annidato nel
  blocco G-15 (ne riusa il modello di layout, il ResizeObserver e i frame finti): 18 rossi (`data-fade` assente), 1
  guardia verde (senza `scrollable` nessun `data-fade`); i 16 casi di prima verdi. Fissano: tolleranza di 1 px ai due
  lati, aggiornamento dopo lo scorrimento dell'utente (senza saltare indietro alla scheda attiva), dopo un
  ridimensionamento **dopo** il riallineamento, dopo un cambio di scheda e di etichette **anche senza scorrimento**;
  maschere `mask-l-`/`mask-r-` presenti solo dal loro lato, ogni classe che cambia contiene `mask`, nessun colore,
  nessun elemento in più. La bozza le rispetta (classi per stato, `updateFade()` dopo `revealActiveTab()` nel
  ResizeObserver e nel frame, `onscroll`).
- **Rossi della LRU scritti e osservati** (`test-author` 05:30; io dal runner 05:31, carico 48): `utils rate-window`
  **12 rossi**, 27 verdi (contratto 2 con `eviction_scan`, contratto 8 riscritto; RWL-002/003, RWL-018…024 nuovi o
  riscritti; RWL-014…016 restano veri, RWL-016 come ripiego). Il `test-author` ha provato in memoria una versione di
  riferimento (39/39) e 12 versioni sbagliate, tutte prese (fra cui «`None` come segnaposto»: la bozza ha `_NO_KEY`).
  Note per l'handoff: la descrizione dell'unità nel runner (`_backend_utils.py`, «LRU eviction at max_keys») e
  `developer/backend/email.md#rate-window` da aggiornare; il prezzo di `eviction_scan=32` (chi blocca 31 identificativi
  suoi subito dopo quello della vittima e poi riempie la mappa la spinge fuori col ripiego: ~310 errori in più contro
  ~100 000 senza tetto; dietro un proxy locale non fidato, dove N70 salta il limite per indirizzo, diventa realistico):
  scelta di E, fissata com'è.
- **Semplificazione del contratto (coordinatore da E, 05:34)**: H aggiunge `client_address.rate_limit_address(request)`
  (`None` dietro un proxy locale non fidato, «locale» = `classify_ip` loopback|vpn|lan, CGNAT compreso; altrimenti
  `client_address`; l'avviso una volta per processo nel suo aiuto). Io lo chiamo nei miei tre punti di `auth.py`; nessun
  `login_throttle.limit_address`, nessun secondo avviso, l'API di `login_throttle` non cambia. **Il resend è di E**
  (E-13, stessa funzione): tolti dalla mia bozza `verification.py` ed `email.py`; detto al `test-author` del proxy di
  togliere il caso del resend e i test unitari di `limit_address`. Bozza divisa: `apply_n70_part.py lru|auth`; la parte
  `auth` aspetta H-36 nel mio ramo (l'import fallirebbe).
- **LRU applicata** (05:35): `rate_window.py` (`eviction_scan`, `_evict_one`), `ruff`/`black` puliti. Verdi:
  `utils rate-window` **39/39**; `services login-throttle` 33, `email-verification` 127, `email-flows` 149,
  `email-delivery` 124, `email-verification-hooks` 32 (tutti gli utenti del limitatore). Descrizione dell'unità
  `rate-window` nel runner aggiornata (revisione di E).
- **Ordine deciso dal coordinatore (05:39, filoni dipendenti)**: 1) entra H-36, il coordinatore me lo porta nel ramo e
  mi dà lo SHA; 2) completo N70 (la parte `auth`) → CHECKPOINT; 3) il coordinatore unisce il mio ramo in quello di E;
  4) E fa E-13 su quella base (resend, «password dimenticata» e la riga di `/auth/register`, che rivedo io); 5) i due
  lotti entrano uno dopo l'altro nello stesso treno, dopo uno slot combinato sul ramo di E (le suite email, le LT-API,
  login-throttle). La nota sul prezzo di `eviction_scan` va a E per la sua revisione.
- **Rossi della scheda Sicurezza scritti** (`test-author`, 05:45): 4 file nuovi in `features/settings/security/`
  (`securityChecksApi` 3, `securityFindings` 33, `securityChecks` 18, `SecurityTab` 16): **70 rossi**, ciascuno per
  conto suo (moduli caricati dentro i test; il primo import del barile delle icone di `lucide-svelte` costa ~27 s col
  carico alto, quindi la scheda li carica una volta in un `beforeAll` da 120 s, come `GapFixStep.test.ts`). Righe nel
  runner (`_frontend_utility.py`: 3 nel core, 1 nel component, una frase in coda alle due `desc`). Letture fissate e
  rispettate dalla bozza: il controllo del browser con `params: {}` e i soli campi del contratto (niente
  `dismissible`); nessun nuovo tentativo automatico dopo un errore; il segnaposto solo prima della prima risposta, il
  «controlla di nuovo» presente e disabilitato durante il primo caricamento; un `info` non è «tutto a posto».
  Aggiunto alla bozza `data-busy`/`aria-busy` sulla radice (regola di casa per i contenitori che ricaricano, non
  fissato). ⚠️ Il `test-author` riporta **una** corsa di Vitest partita a carico 55 (sopra il 50), le altre col
  controllo.
- **Rossi del registro e della pagina scritti** (`test-author`, 05:46): `settingsTabs.test.ts` (24 rossi, 21 verdi;
  STAB-03…13 e SBAR-01…05 nuovi) e `page.tabs.test.ts` (32 rossi, 17 verdi; SPAGE-01…21: barra alta =
  `settingsBar`, gruppo e seconda barra, `?tab=` di membro e di gruppo, distintivi reattivi e sommati sui membri
  visibili, `prefetch` una volta all'avvio e a ogni cambio di contesto e **mai** altrimenti); nuovo aiuto
  `__tests__/harness/SettingsIconProbe.svelte`. Commenti superati segnalati: `settingsTabs.ts:12-13` (la bozza lo
  riscrive), `TabBar.svelte:28` e `:37` (da aggiornare nella bozza).
- **Rossi di A8b osservati da me** (Vitest, 9 file, 05:46–05:47, carico 36): **147 rossi**, 206 verdi (353): C11 3,
  sfumatura 18, Sicurezza 70, registro e pagina 56.
- **Rossi del proxy (N70) scritti e osservati** (`test-author` 05:47; io in processo 05:47–05:48, carico 39):
  `test_login_throttle_api.py` sezione 8 `TestUntrustedLocalProxy`: **12 rossi** (LT-API-20 ×6 pari locali
  lan/loopback/CGNAT con XFF/Forwarded/X-Real-IP, LT-API-24 ×3 e LT-API-25 ×3 i tre punti di `auth.py`), 11 guardie
  (identificativo sempre limitato, pari pubblico e pari locale senza intestazione limitati per indirizzo); tutti
  rossi su 429, nessun errore d'import. `test_login_throttle.py` invariato (LT-010 copre già `address=None`). Per E
  (E-13): il caso del resend dietro proxy deve controllare il conteggio dell'indirizzo, altrimenti passa col solo login.

### A8b.2 — Codice e verdi del frontend ✅ (17/10, 05:50–06:00)

- `apply_a8b.py` applicato (sfumatura, C11, registro, pagina, i 4 file di `security/`, e i commenti superati di
  `TabBar.svelte` :28 e :37); `i18n_add.py`: **14 chiavi** (`settings.administration`, `settings.securityTab.*`,
  `settings.tooManyPasswordAttempts`) in `frontend/src/lib/i18n/settings/*.json`; `settings.admin` («Admin») non era più
  usata (l'`i18n audit` la segnalava): tolta con `dev.py i18n remove` dalle 4 lingue.
- Verdi: i 9 file di Vitest **353/353** al primo colpo; `prettier --check` pulito sui 9 file; `theme-roles.mjs --check`
  «clean»; `i18n check` e `i18n audit` (4 983 chiavi, 0 incomplete, 0 inutilizzate, 0 mancanti).
> **⚠️ Fuori pista**: il primo `front check` dava 13 errori, tutti in `features/backup/*` (endpoint e campi di B4 assenti
> dal client): il mio `generated.ts` era quello di prima del merge di dev. `dev.py api sync` sull'albero unito, poi
> `front check` **0 errori, 0 avvisi**.
- Vitest completo (519 file) lanciato a carico < 45; doc in scrittura (`docs-writer`: «Settings › Admin» → «Settings ›
  Administration › …» in ~11 pagine EN, la sezione `#security-tab` in `admin/settings`, la barra in `user/settings`, il
  429 nel profilo, il registro, la sfumatura e il modulo `security/` nelle pagine developer).
- **Note di H per N70** (via coordinatore, 06:11; H-36 committato, in ingresso): chiamare
  `client_address.rate_limit_address(request)`; testi che diventano falsi dietro un proxy locale non fidato: la riga
  di A sotto «Callers.» in `security.md` (la prima frase ora nomina `rate_limit_address`), il primo paragrafo di
  `connection_checks` e di `configuration.en.md` («50 attempts… would refuse every sign-in»), e la riga dell'`i18n_key`
  dove «15 messages» diventa **18**; un test che manda intestazioni d'inoltro da un pari locale deve svuotare **sul
  posto** `client_address._untrusted_forwarding` prima e dopo (nessuna funzione di reset, per N58).
- **Vitest completo** (519 file, 05:59–06:15, carico 26–45): 17 252 verdi, **1 rosso**:
  `dashboard/growthLadderAxis.test.ts` L14-self.4, «Test timed out in 5000ms» (il file intero 19,4 s). Triage
  (`test-triage` §2, l'orologio): un controllo positivo pesante oltre i 5 s sotto carico, in un file che A8b non tocca;
  rilanciato da solo (carico 39) **138/138** in 19,2 s. Verdetto: **lentezza dell'ambiente**, non un difetto di A8b.
- **H-36 in dev** (`d107b6f26`, 06:20): il coordinatore deve unire dev nel mio ramo, ma tre percorsi aperti si
  sovrappongono (`BACKLOG_POST_1.2.md`, `_backend_utils.py`, `_frontend_utility.py`): chiede un CHECKPOINT a un punto
  stabile con due elenchi separati (N70 finora; A8b finora). Aspetto la fine del `docs-writer` di A8b (sta scrivendo).

### A8b.3 — Doc ✅ e CHECKPOINT (17/10, 06:20–06:35)

- `docs-writer`: 23 pagine EN (utente `settings/index` con `#administration` e `#tabs-overflow`, `settings/profile`;
  admin `settings` con `#administration` e `#security-tab` (+ quattro sotto-ancore), `configuration`, `index`,
  `cli_tools`, e le pagine solo inglesi `email`, `backup_restore`, `hosting_providers`, `users`; developer
  `features/settings` (`#tab-groups`, `#settings-page`, `#securitytab`), `core-ui/toolbar` (`#tabbar-scrollable`, la
  sfumatura), `architecture/security` (la scheda ora esiste), e i percorsi «Settings › Administration › …» in altre
  dieci pagine developer). Le ancore nuove delle pagine tradotte si linkano solo dalla loro pagina.
- Contraddizioni trovate: la descrizione della scheda diceva «controllata quando apri questa scheda», ma la lettura
  avviene all'apertura delle Impostazioni (il prefetch del distintivo) → testo corretto nelle 4 lingue con
  `i18n update` («checked when Settings opens… «Check again» reads it anew»). Fuori da A8b, da dire al coordinatore:
  le stringhe di E `email/en.json:113-114` dicono ancora «Settings › Email» (le doc le citano alla lettera); i commenti
  `BackupTab.svelte:2`, `EmailSettingsTab.svelte:2`, `instance_backup/apply.py:3` nominano i posti vecchi; nessuna
  schermata della galleria per la scheda Sicurezza (G); le righe del limitatore in `security.md:426` e
  `backend/email.md:1335` sono di N70 (dopo il merge).
- `dev.py mkdocs build` strict **verde**, `check-links` **verde** (97). `git diff --check` pulito; porta libera.
- **CHECKPOINT READY** al coordinatore, due elenchi (N70 finora, con diario; A8b finora, sul ramo laterale
  `e-alfy-a-a8b`). Stato: **FROZEN** 🧊.

### A8a-N70 — La parte `auth`, verdi (17/10, 06:32–06:36)

- **Checkpoint del coordinatore**: `b0d3d2d4f` (fix LRU), `806a06823` (i 12 rossi del proxy), `0af0c0f79` (diario);
  A8b sul ramo laterale **`e-alfy-a-a8b` = `4fcf24e10`** (47 file, verificati byte per byte), i suoi file riportati
  qui allo stato di N70; merge di dev `47405701f` (H-36 dentro) → HEAD **`034333294`**, pulito.
- H-36 nel ramo: `client_address.rate_limit_address(request)` (`client_address()` letto prima, così l'avviso di
  un'intestazione malformata non si perde; poi `None` se `forwarded_by_untrusted_proxy()`), `_untrusted_forwarding` =
  `{"local": set(), "public": set()}` (anche le intestazioni da un pari pubblico sono annotate, per il controllo
  `platform.client_address`).
- **Codice** (`apply_n70_part.py auth`): `auth.py` passa `rate_limit_address(http_request)` nei tre punti (import
  accanto a `client_address`); docstring di `login_throttle.py` aggiornata. **Test**: `_start_client_address_over()`
  della sezione 8 svuota sul posto `client_address._untrusted_forwarding` prima e dopo (nota di H: nessuna funzione di
  reset, N58; senza, una nota lasciata da un mio caso farebbe comparire il controllo `platform.client_address` in un
  test successivo dello stesso processo). `ruff`/`black` puliti.
- **Verdi**: `test_login_throttle_api.py` in processo **55/55** (i 12 rossi verdi); `services login-throttle` 33,
  `accounts-checks` 76, `config-audit` 102 (con H-36), `config-package` 861, `client-address` 360 (di H),
  `session-version` 56, `admin-bootstrap` 190, `email-verification` 127; `utils rate-window` 39. Porta libera.
- **Doc in scrittura** (`docs-writer`): le note di H («Callers.», `#login-limit`, «15 messages» → 18, i primi paragrafi
  di `connection_checks` e di `configuration`), l'avvertenza del proxy in «Failed Sign-ins», la LRU in
  `security.md` e in `backend/email.md#rate-window`.
- **Doc di N70** (`docs-writer`, 06:50): `security.md` («Callers.», `#login-limit`: l'indirizzo che ogni chiamante passa,
  il salto dietro un proxy locale non fidato, la LRU che risparmia le chiavi piene e il prezzo del tetto di 32, i test
  LT-API-20…25 e RWL-024; `#configuration-checks`: 18 messaggi), `backend/email.md#rate-window` (`eviction_scan`, la
  regola, i perché), `admin/configuration` («Failed Sign-ins»: la riga della tabella e tre punti sul proxy, il
  riassunto di H citato com'è), `admin/connection_checks` (la frase finale del primo paragrafo). Corretto anche un
  errore di A8a: «`None` come per un client di test» era falso (`testclient` è una chiave). Fuori dal mio perimetro: il
  testo di H dice che «i limiti per indirizzo» saltano queste richieste, vero per tutti solo con E-13 (i tre limiti di
  E usano ancora `client_address()`: `auth.py:299`, `email.py:159`, `email.py:206`). ⚠️ Il `docs-writer` ha creato
  per sbaglio, con un `pipenv run` senza `PIPENV_CUSTOM_VENV_NAME`, un venv vuoto per questo worktree e l'ha tolto
  subito; nessun file del repo toccato (verificato: nessun venv di questo worktree in `~/.local/share/virtualenvs`).
- `dev.py mkdocs build` strict **verde**, `check-links` **verde**; `git diff --check` pulito; porta libera.
- **CHECKPOINT READY** (N70 completo) al coordinatore. Stato: **FROZEN** 🧊.

## A9 — Analisi (17/10, 07:00; solo lettura, nessun file del repo)

Fonti: §4.9, §4.10, §15.1 (D-A7, D-A8 cambiata: niente `LIBREFOLIO_SUPPORT_URL` per le donazioni; D-A9 fatto in
A5/A6; D-A11, D-A13, D-A14 da confermare col coordinatore a questo lotto); specifica SaaS F05 («nessun popup di
donazione, nessun suggerimento docker o di aggiornamento»; link `LIBREFOLIO_TOS_URL`, `LIBREFOLIO_PRIVACY_URL`) e F09.

**Stato reale (HEAD `da640e33a`)**
- H ha già: `LIBREFOLIO_PROFILE` (`selfhosted|managed`), la configurazione pubblica `GET /system/instance`
  (`InstanceConfigResponse`: `profile`, `accounts` di A, `email` di E) e `instanceConfig` nel frontend,
  `instance_links.py` con `LIBREFOLIO_SUPPORT_URL` (il link «segnala» della ricerca asset di X: un'altra cosa rispetto
  a D-A8). Nessun link legale, nessun disclaimer.
- Donazioni: `donation_popup_service.is_donation_popup_disabled()` guarda solo la variabile nascosta (D-A7), non il
  profilo. «Buy me a coffee» in `features/auth/AuthPageFrame.svelte:28` (mio), `layout/Header.svelte:256` e
  `layout/HelpMenu.svelte:23,153` (di H), `features/support/SupportActions.svelte` (mio, nella scheda About; la
  condivisione social resta, D-A8), `supportLinks.ts` (`BUY_ME_A_COFFEE_URL`); il popup (`DonationPopupModal`,
  `donationPopupStore`) parte solo dal segnale del login.
- Aggiornamenti: `features/update-check/` (le modali sono già lì, D-A13 fatta in A2): nessun controllo del profilo.
- «Password dimenticata»: `features/auth/ForgotPasswordCard.svelte:39,41` mostra i comandi docker e `dev.py`; il modulo
  email di E compare quando `instanceConfig.config.email.links`.
- AI Export: le sezioni di `features/ai-export/templates/promptRenderer.ts:50` (`AiExportPromptSectionId`), di J.

**Proposta di contratto**
1. *F05, backend*: `is_donation_popup_disabled()` vero anche col profilo `managed` (il conteggio degli accessi
   continua); la variabile nascosta resta (D-A7).
2. *F05, frontend*: un aiuto unico (`features/instance/`, di H, o mio in `features/support/`) «l'istanza è
   self-hosted, detto dal server»: i «Buy me a coffee» compaiono **solo a configurazione caricata e self-hosted**
   (niente lampo sulle istanze gestite prima della risposta); nascosti nei 4 punti (2 file miei, 2 di H: una
   condizione per file); il controllo degli aggiornamenti non parte nel profilo gestito (dentro il negozio
   dell'update-check, senza toccare il layout di H); `ForgotPasswordCard` nel profilo gestito mostra «chiedi
   all'amministratore» al posto dei comandi docker/CLI (il modulo email resta).
3. *F09, backend*: `LIBREFOLIO_TOS_URL` e `LIBREFOLIO_PRIVACY_URL` (nomi della specifica), solo http(s), sbagliate →
   errore nel log una volta e ignorate (come `LIBREFOLIO_BILLING_URL`); in `config/accounts.py` (o in
   `instance_links.py` di H: da decidere); nella configurazione pubblica un blocco `legal: {terms_url, privacy_url}`
   (schema mio, una riga in `system.py` di H, come `accounts`); righe in `.env.example`.
4. *F09, frontend*: `features/legal/LegalNotice.svelte` (il testo del disclaimer e i link quando ci sono, con
   `rel="noopener noreferrer"`) e `LegalLinks.svelte` (compatto). Posti (D-A11): la scheda About (card «Note
   legali»), il fondo delle pagine d'accesso (`AuthPageFrame`, mio: login, registrazione, setup, invito, reset), la
   Welcome (`WelcomePage`, dell'onboarding: una riga), una riga in fondo alla sidebar (di H: la monta H), ogni output
   dell'AI Export come sezione finale `legal_notice` nella lingua dell'interfaccia (di J: `promptRenderer.ts` e i
   test d'ordine). Nessuna registrazione dell'accettazione (§10.11).
5. i18n: chiavi `legal.*` e la frase «chiedi all'amministratore», nelle 4 lingue; D-A14 (sorgente `support/`) da
   confermare.
6. Doc: `admin/configuration` (le due variabili, gli effetti del profilo gestito: aspetta l'ingresso di A8a, è una
   pagina di A8a), `admin/hosting_providers`, la pagina About dell'utente, le pagine developer.

**Decisioni da chiedere**
- *Developer*: il **testo del disclaimer** (proposta: «LibreFolio ti aiuta a seguire i tuoi investimenti; non dà
  consigli finanziari, fiscali o legali. I numeri possono contenere errori: verificali prima di agire.»); conferma dei
  nomi `LIBREFOLIO_TOS_URL`/`LIBREFOLIO_PRIVACY_URL`.
- *Coordinatore*: D-A11 (i 5 posti) e chi scrive le righe nei file di H (sidebar, Header, HelpMenu, `system.py`),
  dell'onboarding (Welcome) e di J (`promptRenderer.ts`); dove stanno le due variabili (A o `instance_links` di H);
  D-A14; se nel profilo gestito sparisce anche il pulsante «controlla aggiornamenti» del `ChangelogModal` di H.

**Peso e ordine**: medio, molti punti di contatto. Backend prima (config, popup, configurazione pubblica), poi i
componenti legali, poi le righe negli altri file con i loro proprietari, poi le doc (dopo l'ingresso di A8a).
- **Decisioni del coordinatore su A9 (07:05)**: D-A11 i 5 posti **OK**; le righe nei file degli altri le scrivo io, con
  la revisione del proprietario (H: sidebar, `Header`, `HelpMenu`, `system.py`; Welcome dell'onboarding seguendo la
  skill `onboarding-guide`; J: `promptRenderer.ts` e i test d'ordine, con le istruzioni dell'AI Export e la politica
  delle versioni); le due variabili **in `instance_links` di H**, accanto a BILLING (le scrivo io, H rivede); D-A14 a
  mia scelta purché in una sorgente esistente; nel profilo gestito sparisce anche «controlla aggiornamenti» del
  `ChangelogModal`; testo del disclaimer e nomi delle variabili sulla lista del developer (codice con la mia proposta,
  facile da cambiare). **Codice dopo l'ingresso di A8a+N70+E-13**; intanto l'analisi di A-21.

## A-21 — Analisi (17/10, 07:10; solo lettura)

Richiesta (coordinatore, 16/10, dopo P18): nomi utente unici a prescindere dalle maiuscole (la regola di P18), i nomi
nuovi senza `@` e con un insieme di caratteri, un identificativo con `@` cerca solo l'email al login e in «password
dimenticata»; per i nomi esistenti con `@` o con varianti di maiuscole: prima l'analisi, nessun cambio silenzioso.

**Stato reale (HEAD `da640e33a`)**
- `users.username` unico **com'è scritto** (`Field(unique=True)`), 3–50 caratteri, **qualunque carattere** (spazi,
  `@`, accenti); si controlla solo la lunghezza (`AuthRegisterRequest`, `UserProfileUpdate`, il modello,
  `LIBREFOLIO_ADMIN_USERNAME` in `config/accounts.py:103`, la CLI).
- `get_user_by_username_or_email()` (`user_service.py:150-163`): `username == identificativo OR lower(email) ==
  lower(identificativo)`, poi `.first()`. **Difetto**: se il nome utente dell'account A è uguale (o uguale a meno delle
  maiuscole) all'email dell'account B, la ricerca trova due righe e prende la prima: B può non riuscire ad accedere con
  la sua email (la password si confronta con l'hash di A), e «password dimenticata» di B (E, `flows.py:251`) e il
  resend (E) possono trovare A. Basta che A scelga come nome l'email di B. Usata da login, resend e «password
  dimenticata».
- I controlli «nome già preso» della registrazione (`user_service.py:238-241`) e del profilo (`:516`) sono esatti:
  `Alice` e `alice` sono due account possibili. La ricerca per la condivisione dei broker (`search_users`) è già
  `ilike`. La chiave del limite dei tentativi ripiega già A–Z.

**Proposta**
1. *Nomi nuovi* (registrazione, invito, profilo, CLI, `LIBREFOLIO_ADMIN_USERNAME`): 3–50 caratteri fra A–Z, a–z,
   cifre, `.`, `_`, `-`; niente `@`, niente spazi.
2. *Unici a prescindere dalle maiuscole* (A–Z, come P18): migrazione `010_username_unique_ignoring_case` sul modello
   della 009: si ferma prima di scrivere se due account hanno lo stesso nome a meno delle maiuscole, nominandoli per id
   e nome, col rimedio `./dev.py user rename <vecchio> <nuovo>` (comando nuovo, che lavora sul database com'è);
   altrimenti l'indice unico su `lower(username)`. Il downgrade lo toglie. Rilanciabile.
3. *Ricerca*: un identificativo con `@` cerca **solo** l'email; senza `@` solo il nome utente, A–Z ripiegate (senza
   ambiguità grazie all'indice). Una funzione sola: login, resend e «password dimenticata» seguono (le chiamate di E non
   cambiano; E rivede).
4. *Nomi esistenti fuori regola* (con `@`, spazi, accenti): restano come sono; chi ha `@` nel nome accede con la sua
   email (ogni account ne ha una), quindi nessuno resta fuori. Il profilo non chiede di cambiarli; un cambio di nome
   segue la regola nuova. Facoltativo: un controllo `info` nella scheda Sicurezza che li conta.
5. *Maiuscole*: il nome si mostra com'è scritto; l'accesso col nome diventa indifferente alle maiuscole (come le email
   e come la chiave del limite).
6. Test: la migrazione (fermata, rilancio, downgrade), le regole dei nomi in ogni ingresso, la ricerca (`@` → solo
   email, nome indifferente alle maiuscole, l'ambiguità A/B chiusa), il resend e «password dimenticata» di E con un nome
   che contiene `@`. Doc: utente, admin (CLI `rename`, il messaggio della migrazione, la regola di
   `LIBREFOLIO_ADMIN_USERNAME`), developer.

**Decisioni per il developer**: l'insieme di caratteri (proposta: solo ASCII, perché `lower()` di SQLite ripiega solo
A–Z; in alternativa le lettere Unicode); i doppioni esistenti a meno delle maiuscole (proposta: fermare l'upgrade con
`user rename`, come P18; in alternativa un suffisso automatico); i nomi esistenti con `@` (proposta: restano, accesso con
l'email; in alternativa rinomina obbligata all'upgrade).

**Peso**: medio. Tocca `user_service.py` e `schemas/auth.py` (file di A8a: dopo l'ingresso), una migrazione, la CLI.
Il difetto dell'ambiguità A/B è da segnalare alla revisione di sicurezza (E).
- **Coordinatore (06:57)**: le decisioni 1–3 di A-21 vanno sulla lista del developer con le mie proposte; **sì** ai
  rossi di A9 e di A-21 **solo in file di test nuovi**, nessun codice di prodotto fino all'ingresso; il difetto
  dell'ambiguità passa a E per la sicurezza.
- **Rossi in scrittura** (07:15, quattro `test-author`, solo file nuovi, niente runner: le righe le aggiungo col codice):
  A9 backend (`test_donation_managed_profile.py`, `test_legal_links.py`, `test_instance_config_legal_api.py`); A9
  frontend gestito (`donations.test.ts` e sette `*.managed.test.ts`); A9 frontend legale (`LegalNotice`, `LegalLinks`
  e quattro `*.legal.test.ts` dei posti); A-21 (`test_username_rules.py`, `test_username_lookup.py`,
  `test_migration_010.py`, `test_username_rules_api.py`). Nota: le variabili legali vanno in `instance_links` di H
  accanto a SUPPORT (BILLING sta in `config/accounts.py`, di A: il «accanto a BILLING» del coordinatore l'ho letto
  come «nello stesso stile»; `tos_url()`/`privacy_url()` in `config/platform.py`, da dire al coordinatore).
- **A-21 divisa** (coordinatore 07:01, da E: difetto **MEDIO 8/10** — con gli indici veri di SQLite `.first()` restituisce
  sempre l'occupante; non serve la registrazione aperta, perché il profilo cambia il nome **senza password**; B si può
  bloccare dopo 10 tentativi):
  - **A-21a** (sicurezza, la prima dopo l'ingresso di A8a+N70+E-13, prima di A9; asticella di E): 1) niente `@` in ogni
    nome **nuovo** (registrazione, cambio di nome, creazione da CLI, `LIBREFOLIO_ADMIN_USERNAME` con un errore
    chiaro); 2) niente email uguale, a meno delle maiuscole, a un nome esistente; 3) ricerca: con `@` prima l'email,
    poi il nome esatto solo se nessun account ha quell'email; senza `@` solo il nome esatto. Test del punto (c) di E:
    maiuscole esatte e diverse, i due ordini di registrazione, il caso inverso con un nome `@` storico, i rifiuti, e
    come regressione le suite email di E (EMA/EVA/EVH).
  - **A-21b** (unicità a prescindere dalle maiuscole, insieme di caratteri, migrazione 010): aspetta il developer.
    **Non** rendere la ricerca indifferente alle maiuscole prima dell'unicità (punto b di E: ricreerebbe il DoS fra
    «Bob» e «bob»). Facoltativo, per H più avanti: il conteggio delle collisioni storiche nel controllo di Sicurezza.
  - Al `test-author` di A-21: contratto cambiato, solo A-21a (via `test_migration_010.py`).
- **Revisione della riga di E** (07:15, sola lettura): `bfa2729e9` `auth.py:299`
  `registration_email_allowed(rate_limit_address(http_request))` (con `None` nessun conteggio per indirizzo, restano la
  casella e il budget orario: coerente con N70), import a `:51` ridotto a `rate_limit_address` (nessun `client_address`
  rimasto in `auth.py`); `email.py` (forgot `:159`, resend `:206`) su `rate_limit_address`, quindi il resend eredita N70
  senza il kwarg; le tre frasi di `security.md` (`aad2a2bbf`, `:375`, `:411`, `:2301`) corrispondono al codice. **OK**.
  Slot combinato (`8c9550ec6`) in corso sul ramo di E, poi l'ingresso congiunto.

## Ingresso di A8a + N70 + E-13 e ritorno di A8b (17/10, 07:20–07:30)

- **Entrati**: dev `440616c61`, CHANGELOG `45f9c5406` (✨ il limite con la frase di N70, ✨ `security/checks`, 🔒 sessioni
  concorrenti, 🔒 H-36, 🐛 `1E+400`; E-13 accodato alla riga di `CLIENT_IP_HEADER`). Il mio ramo portato in avanti a
  `45f9c5406`.
- **A8b di ritorno**: il coordinatore apre il merge di `e-alfy-a-a8b` (`4fcf24e10`); due conflitti risolti tenendo i due
  lati: `admin/backup_restore.en.md` (il testo di B-16 col percorso di A8b; in più le due righe nuove di B
  `database_damaged`/`database_foreign_objects` portate a «Settings › Administration › Backup:»),
  `developer/architecture/security.md` (18 messaggi di H-36 + la frase di A8b sulla scheda che ora esiste). Restano
  apposta le due citazioni letterali delle stringhe di E in `admin/email.en.md:480,482`.
- Controlli sull'albero unito: `api sync` rc 0; `mkdocs build` strict e `check-links` verdi; `front check` 0/0; Vitest
  dei 9 file di A8b 353/353; `theme-roles --check` pulito; `git diff --cached --check` pulito; porta libera. In stage
  solo i due file (più quello che git aveva già messo); i rossi non tracciati di A9 e A-21a fuori dal merge.
- **Rossi scritti nel frattempo** (file nuovi, non registrati nel runner):
  - **A9 backend** (`test-author`): `test_donation_managed_profile.py` (30: 10 rossi, 20 controlli),
    `test_legal_links.py` (56 rossi), `test_instance_config_legal_api.py` (19: 18 rossi, 1 dal vivo da far girare
    sulla corsia); contro una versione di riferimento tutti verdi, sei versioni sbagliate prese. Da cambiare col
    codice: `test_system_api.py:843` e `test_registration_api.py:895` fissano l'insieme esatto dei campi della
    configurazione pubblica (aggiungere `legal`). Letture: `mailto:` rifiutato per i link legali (come `env_url`), il
    profilo gestito spegne il popup anche con la variabile nascosta a `0`, `" MANAGED "` vale gestito.
  - **A9 frontend legale** (`test-author`): 6 file (`LegalNotice`, `LegalLinks`, `AboutTab.legal`,
    `AuthPageFrame.legal`, `WelcomePage.legal`, `Sidebar.legal`): 50 rossi, 4 guardie. Note: la riga nella sidebar sta
    sulla barra verde (`bg-lf-bar`): `LegalLinks` probabilmente vuole un tono (ruoli `text-lf-bar-*`); LGN-06 diventa
    verde solo dopo `api sync` col backend di A9 (il client scarta i campi che non conosce); `verify-email-page` aggiunta
    ai posti del telaio.
  - **A-21a** (`test-author`): `test_username_rules.py` (25 rossi, 7 guardie), `test_username_lookup.py` (8 rossi, 9
    guardie), `test_username_rules_api.py` (27 rossi, 12 guardie); contro una versione grezza di A-21a tutti verdi (sia
    col rifiuto nel servizio, 400, sia nello schema, 422). Oggi la ricerca trova l'occupante in entrambi gli ordini delle
    righe (SQLite cerca prima nell'indice del nome). Estensione: `user create` con un'email uguale a un nome esistente
    (UNAME-012). Da fare nel frontend: `registrationErrors.ts:33,51` non ha parole giuste per il rifiuto della `@`.
  - **A9 frontend gestito**: in attesa del `test-author`.

### A8b.4 — E2E (17/10, 07:35–)

- Merge di A8b committato dal coordinatore: **`2a8cb8a8a`** (genitori `45f9c5406` + `4fcf24e10`); rossi non tracciati e
  piano fuori, intatti.
- **Uso delle schede del gruppo nelle spec** (23 punti): cambiano i clic su un membro (non più nel DOM se il gruppo è
  chiuso) e i controlli «un utente vede `settings-tab-admin`» (per un non admin non c'è la seconda barra:
  `settings-tab-administration`); restano validi gli `aria-selected` dopo `?tab=<membro>` di un admin. Spec toccate:
  `settings.spec.ts` (parti di A + la sezione G-15, che si aspetta una barra sola con tutte le schede), `admin-users`
  (A), `backup` (B), `email-tab` (E), `scheduler` (Z), `gallery` (G); probabilmente invariate `email-send-link` e
  `auth-email-verification` (E). Nuove (A): l'aiuto `fixtures/settings-tabs.ts` (`openSettingsTab`) e
  `settings/security-tab.spec.ts` (sulla corsia il limite è spento → `accounts.login_limit` in avviso → distintivo
  sul gruppo).
- Chiesto al coordinatore il congelamento delle spec dei proprietari, con l'elenco; `test-author` avviato sulla fase 1
  (solo i file di A), fase 2 dopo il congelamento.
- **Congelamento concesso** (07:30) su `backup.spec.ts` (B), `email-tab.spec.ts` (E), `scheduler.spec.ts` (Z): modifiche
  minime e additive, revisione dei proprietari al checkpoint. **`gallery.spec.ts:1989` e la sezione G-15 di
  `settings.spec.ts`**: aspettano l'OK della squadra dei colori (non toccarle). Detto al `test-author`.
- **OK della squadra dei colori** (07:31) su `gallery.spec.ts:1989` (tenere il contratto d'attesa di
  `openGlobalSettings`: `aria-selected` sulla scheda aperta, poi `global-settings-tab` senza `data-busy`) e su G-15, che
  è codice mio (`affae6ffe`): spagnolo, le larghezze desktop, l'admin, «tutta in vista» con la tolleranza di 1 px, per
  **ogni scheda delle due barre**; **in più (punto 33)**: una scheda scelta non deve stare sotto una sfumatura attiva.
  Passato al `test-author` E2E (fase 2 completa).
> **⚠️ Fuori pista (punto 33)**: oggi `revealActiveTab()` porta la scheda solo fino al bordo («e non di più», G-15):
> con altre schede oltre, i suoi 24 px esterni restano sotto la maschera. Regola nuova del riallineamento: dopo lo
> scorrimento la scheda sta ad almeno 24 px (la larghezza della sfumatura) da ogni lato dove la sfumatura è attiva;
> nessun margine dove non c'è più nulla da scorrere; se lo stato attuale già va bene, nulla si muove. Cambiano i valori
> attesi dei casi di G-15 e di alcuni della sfumatura in `TabBar.test.ts` (es. 80 → 104, 70 → 46, 30 → 54): chiesto al
> `test-author` della sfumatura di riscriverli (rossi prima), poi il codice.
- **Rossi di A9, frontend gestito** (`test-author`, 07:40): 8 file, 51 casi, **42 rossi**, 9 controlli verdi
  (`support/donations.test.ts`, `support/SupportActions.managed`, `auth/AuthPageFrame.managed`,
  `auth/ForgotPasswordCard.managed`, `layout/Header.managed`, `layout/HelpMenu.managed`, `layout/ChangelogModal.managed`,
  `update-check/updateCheck.managed`); contro una versione minima del contratto in una copia usa e getta, tutti verdi e
  le varianti sbagliate prese. Decisioni: la chiave `auth.forgotPassword.askAdmin` non può esistere
  (`auth.forgotPassword` è già una stringa, il catalogo non trasforma una stringa in un gruppo) → **`auth.askAdminToResetPassword`**,
  piatta accanto alle sorelle; il pulsante «controlla aggiornamenti» del changelog si nasconde **solo** col profilo
  gestito (i 24 casi di `ChangelogModal.test.ts` restano verdi); l'intestazione «Run this command on the server:» va
  con i comandi. **Da fare col codice di A9**: `SupportActions.test.ts:32,41,71` e `DonationPopupModal.test.ts:75,92,124`
  vogliono una risposta self-hosted; `forgot-email-unavailable` parla ancora del terminale anche col profilo gestito
  (fuori contratto: da decidere); `/verify-email` non carica la configurazione (il caffè del telaio non comparirebbe
  lì: `load()` nel telaio o in `donations`); una richiesta di configurazione fallita lascia il profilo self-hosted
  (la sonda degli aggiornamenti parte, le donazioni no); il popup stesso dipende dal backend che non lo manda col
  profilo gestito. Registrazione nel runner: `donations` e `updateCheck.managed` in `front_utility_unit`, i sei
  componenti in `front_component_unit`.
- **Punto 33 ✅ (07:48)**: rossi di `TabBar.test.ts` riscritti dal `test-author` della sfumatura (38 casi, **11 rossi**,
  ognuno fermo sul `scrollLeft` di oggi: 80 → 104, 70 → 46, 0 → 4 al montaggio, 30 → 54, 20 → 44, la scheda larga
  80 → 76). Regola applicata in `revealActiveTab()` (`work/a8b/apply_point33.py`): dopo il riallineamento la scheda sta
  ad almeno la larghezza della sfumatura (1,5 × la dimensione del carattere radice, come la maschera `1.5rem`) da ogni
  lato dove resta qualcosa da scorrere; nessun margine dove la barra non scorre oltre; una posizione che già va bene non
  si tocca; una scheda più larga della barra tiene in vista l'inizio (anche nel ramo destro). Anche al montaggio (la
  scheda tre, 160–280 in 300, si sposta di 4 px: inteso). Verdi: Vitest `TabBar.test.ts` **38/38**; Prettier e
  `theme-roles --check` puliti.

## A-21a — Nomi utente senza `@`, ricerca per indirizzo prima (17/10, 07:40–; base `2a8cb8a8a`)

Contratto (coordinatore 07:01, asticella di E): 1) niente `@` nei nomi **nuovi**; 2) niente email uguale, a meno delle
maiuscole A–Z, al nome di un altro account; 3) ricerca: con `@` l'email prima, poi il nome esatto; senza `@` solo il
nome esatto. Nessuna ricerca indifferente alle maiuscole prima dell'indice di A-21b.

### A-21a.1 — Rossi ✅ (07:43)
- Riosservati sulla base `2a8cb8a8a` (in-process, `--noconftest`): **60 rossi, 28 guardie verdi** nei tre file
  (`test_username_rules.py`, `test_username_lookup.py`, `test_username_rules_api.py`), ognuno sulla sua asserzione
  «red until A-21a».
- Rossi del frontend chiesti a un `test-author` (07:45): `registrationErrors.test.ts` (`USERNAME_INVALID` →
  `auth.validation.usernameNoAt`), `RegisterCard.test.ts` (la `@` fermata nel client), `ProfileTab.test.ts` (il 400
  `USERNAME_INVALID` in parole e il campo rimesso).

### A-21a.2 — Codice del backend ✅ (07:44)
`work/a21a/apply_a21a.py --part backend`:
- `config/accounts.py`: la casa unica della regola, `USERNAME_RESERVED_CHARACTER = "@"` e `USERNAME_RESERVED_MESSAGE`;
  `admin_bootstrap_config()` rifiuta `LIBREFOLIO_ADMIN_USERNAME` con `@` (`ADMIN_USERNAME_INVALID`, il messaggio nomina
  la variabile e la `@` e dice che l'amministratore accede comunque con `LIBREFOLIO_ADMIN_EMAIL`).
- `user_service.py`: `get_user_by_username_or_email` riscritta (regola 3, due letture); `address_is_a_username()` nuova
  (`lower(username) = lower(indirizzo)`, l'account stesso escluso); `create_user` (regole 1 e 2: copre registrazione,
  CLI `user create`, F02) e `update_profile` (regola 1 solo se il nome cambia, regola 2 solo se l'indirizzo cambia:
  copre il profilo e la CLI `user set-email`). Il rifiuto dell'indirizzo è la risposta di sempre, «Email already
  registered».
- `registration_service.register_user`: il rifiuto della `@` diventa `RegistrationError("USERNAME_INVALID")`, non
  `ACCOUNT_EXISTS`.
- `api/v1/auth.py`: `USERNAME_INVALID` in `_REGISTRATION_REFUSALS` (400 con codice); il profilo risponde lo stesso
  codice. Un codice solo per i due posti, così il frontend lo dice nella lingua dell'utente.
- Runner: `services username-rules`, `services username-lookup`, `api username-rules` (pure).
> **Note implementazione**: la regola 1 sta nel servizio, non nello schema: un account storico che rimanda il suo nome
> invariato non va rifiutato, e la scheda Profilo manda il nome solo quando cambia. Un 400 con codice al posto di un 422
> perché il frontend legge già i codici in entrambi i posti.

### A-21a.3 — Verdi del backend ✅ (07:45–07:48)
- In-process: i tre file **88/88**; `test_login_throttle_api.py` **55/55**.
- Servizi sulla corsia (`reds.sh a21a`): `username-rules` 32, `username-lookup` 17, `email-case` 67, `registration` 151,
  `admin-bootstrap` 190, `email-flows` 149, `email-verification` 127, `login-throttle` 33, `session-version` 56 →
  **822 passati, 0 rossi**; porta libera. `ruff`/`black` puliti sui sei file.
- Da fare nello slot API: `auth`, `registration`, `admin-setup`, le suite email di E (`email`, `email-verification`,
  `email-verification-hooks`), `users-admin`, `system`, `instance-block`, `validation-errors`, `username-rules`.

### A-21a.4 — Frontend ✅ (07:46–07:59)
- **Rossi** (`test-author`): `registrationErrors.test.ts` (la riga `USERNAME_INVALID` → `auth.validation.usernameNoAt`
  e la chiave nei 4 cataloghi), `RegisterCard.test.ts` (`bob.smith@example.com` e `a@b` fermati nel client, il caso al
  blur, sei guardie senza `@` mandate come scritte), `ProfileTab.test.ts` (Salva della riga e «salva tutto»:
  `data-error-code="USERNAME_INVALID"` e le parole, non la frase del server): **10 rossi**, i 224 casi esistenti verdi.
- **Codice** (`work/a21a/apply_a21a.py --part frontend`, `work/a21a/i18n_add.py`): `USERNAME_INVALID` nella mappa dei
  rifiuti della registrazione e del Profilo; `validateUsername()` della card ferma la `@` dopo la lunghezza; chiave
  `auth.validation.usernameNoAt` in EN/IT/FR/ES (`i18n build`/`check` puliti, 4993 chiavi).
- **Verdi**: Vitest dei tre file **240/240**; Prettier e `theme-roles --check` puliti; `front check` 0 errori, 0 avvisi.
> **Note implementazione**: nessun controllo nel client del Profilo (decisione: il server risponde, la scheda lo dice
> con le sue parole e rimette il campo); con una `@` in un nome corto vince il messaggio della lunghezza (non fissato).
- **Revisione di E-14** (coordinatore 07:57, sola lettura): `login_throttle` invariato (solo `peek`/`hit`/`reset`, contratti
  uguali; `None` = solo l'identificativo); le mie suite contro il `rate_window.py` di `4ec3057ef` caricato al posto
  di quello dell'albero: **127/127**; la frase di E in `security.md:431-438` è esatta. OK mandato.

### A-21a.5 — Doc ✅ (07:47–08:01)
- `docs-writer`: 12 pagine inglesi — `admin/configuration`, `admin/cli_tools`, `admin/users` (nuova sottosezione
  «🔤 Usernames with an @»), `admin/hosting_providers`, `user/getting-started`, `user/settings/profile`,
  `developer/architecture/security.md` (nuova «🪪 Which Account an Identifier Names», righe `USERNAME_INVALID` e regola
  2 nelle tabelle), `access_control.md`, `users_and_brokers.md`, `database/users_access.md`,
  `frontend/components/features/auth.md`, `features/settings.md` (la riga dei rifiuti del Profilo, altrimenti falsa).
  `email.md` di E invariata (dice «come il login», ancora vero). `mkdocs build` strict e `check-links` verdi
  (97 link). Nessun timbro di traduzione: debito reale su `admin/configuration`, `admin/cli_tools`,
  `user/getting-started`, `user/settings/profile`.
> **⚠️ Fuori pista**: (1) `_follow_variables()` di `bootstrap_admin_service.py` cambia l'indirizzo dell'admin in attesa
> senza la regola 2. Non serve: l'admin in attesa esiste solo su un'istanza nata vuota, e ogni nome creato dopo è senza
> `@` (la regola 1), quindi nessun nome può essere un indirizzo; annotato per la revisione di E. (2) `user create` non
> controlla la lunghezza del nome (difetto vecchio, fuori perimetro) → **A-46** nel backlog.
- `.env.example`: la riga di `LIBREFOLIO_ADMIN_USERNAME` dice «senza @».
- **Badge della barra** (A8b, chiesto dal `test-author` E2E): `data-testid="tab-badge"` e `data-badge` sul distintivo
  di `TabBar` al posto della lettura delle cifre; rossi 3 (`TabBar.test.ts`), verdi **41/41**; Vitest di
  `features/settings` e della rotta: 1118 verdi, i soli 5 rossi sono quelli di A9 (`AboutTab.legal.test.ts`, non
  tracciato).
- **A8b.4 — E2E scritti** (`test-author`, niente eseguito): `fixtures/settings-tabs.ts` (`openSettingsTab`),
  `settings/security-tab.spec.ts` (ASEC-E-01..03), `admin-users.spec.ts`, `settings.spec.ts` (clic col aiuto, G-15 sulle
  due barre col controllo della sfumatura), runner `front-utility security-tab`; dei proprietari: `backup.spec.ts` (B),
  `email-tab.spec.ts` (E), `scheduler.spec.ts` (Z), `gallery.spec.ts` (G, `openGlobalSettings`).
- **Slot 1** riservato dal coordinatore (08:00) sulla revisione combinata: prima CHECKPOINT con tre liste, poi il merge
  di dev (E-14, B-30, B-9, X-R43, Y-8, MF-D4), poi E2E + API.

## Checkpoint, due aggiornamenti di base e slot 1 (17/10, 08:05–)

- **Committato** dal coordinatore nell'ordine 2→1→3→diario: `607932c86` (barra delle schede: punto 33 e gancio del
  distintivo), `e9fd90fef` (E2E di A8b), `5da71d037` (A-21a), `db157e297` (diario); 45 file, i 17 di A9 fuori.
- **Merge 1, dev `f4dab3db7`** (E-14, B-30, B-9, X-R43, Y-8, MF-D4) → `ff1c8ddcc`. Un conflitto, `security.md`, la riga
  `i18n_key` di «Configuration Checks»: la riga di dev con la clausola nuova di B (`backup.checks.*`, nove messaggi,
  verificati) e la frase di A8b, ora «all four subsystems'» (verificato: `CONFIG_CHECKS` include
  `BACKUP_CONFIG_CHECKS`, `/security/checks` restituisce `run_config_checks()`, la scheda mostra ogni `i18n_key`). In
  più, frasi di B rese false dal merge: `security.md:1030` («no page shows them until the «Security» tab» → la scheda
  li mostra) e `admin/configuration.en.md` («Settings › Backup» → «Settings › Administration › Backup», incluso dal
  coordinatore nel merge). Strict mkdocs e `check-links` (97) verdi.
- **Merge 2, dev `7f8e69be6`** (H-39: `platform.frame_protection`, `platform.csp_report_only`) → `36ab58445`. Un
  conflitto, la stessa riga: quella di H-39 («24 messages», verificati nel codice e nel catalogo) con la frase di A8b.
  Le spec e i test di `/security/checks` non fissano insiemi esatti: due controlli `ok` in più non li toccano. Strict
  mkdocs e `check-links` verdi.
> **⚠️ Fuori pista (per B)**: `security.md` «Tests: … the order of `CONFIG_CHECKS` included: the platform's checks,
> A's, then E's three» non nomina i due controlli di B: vecchio su dev, non causato dai merge; segnalato.
- **A-21a — Revisione di E** (08:10): **chiusa**, il MEDIO è curato; `_follow_variables` innocuo. Una nota LOW:
  `auth.py` riconosce `USERNAME_INVALID` dal testo del messaggio → **A-47** nel backlog.
- **Revisione di E-14** fatta (sopra, A-21a.4).
- **Slot 1** (08:22–), su `36ab58445`, corsia 6182, un'invocazione alla volta, carico a 5 minuti < 50:
  `work/slot1/slot.sh` — E2E `front-utility` security-tab, settings, admin-users, backup, email-tab, scheduler,
  email-send-link, email-verification, plugin-settings; poi API username-rules, login-throttle, security-checks, auth,
  registration, admin-setup, users-admin, validation-errors, email, email-verification, email-verification-hooks,
  system, instance-block.
- **Slot 1 — E2E ✅** (08:28–08:54, `36ab58445`, il frontend ricostruito dal runner all'inizio): `security-tab` 3,
  `settings` 56 (G-15 sulle due barre col controllo della sfumatura incluso), `admin-users` 10, `backup` 14,
  `email-tab` 5, `scheduler` 17, `email-send-link` 4, `email-verification` 5, `plugin-settings` 5 → **119 passati,
  0 rossi**. API: `username-rules` 39/39 (il resto in corso).
- **Slot 1 — API ✅** (08:55–09:10): `username-rules` 39, `login-throttle` 55, `security-checks` 3, `auth` 95,
  `registration` 102, `admin-setup` 50, `users-admin` 100, `validation-errors` 53, `email` 168, `email-verification` 60,
  `email-verification-hooks` 26, `system` 122, `instance-block` 62 → **935 passati, 0 rossi**. Albero invariato
  (`post-run dirty: 0`), porta 6182 libera. Log: `work/slot1/logs/`.
- **A8b (E2E e seguiti della barra) e A-21a: definizione di fatto ✅** sulla revisione combinata `36ab58445`.

## A9 — Profilo gestito (F05) e note legali (F09) (17/10, 09:12–; base `e58be67fe`)

Ingresso di A8b + A-21a: dev `6e2b2c8b7`, CHANGELOG `e58be67fe`; il mio ramo portato in avanti. Via del coordinatore
(09:11): nei file di H (`config/platform.py`, `instance_links.py`, `schemas/system.py`, `api/v1/system/instance.py`,
Sidebar, Header, HelpMenu, ChangelogModal) scrivo io e H rivede (H non li tocca fino all'ingresso); `WelcomePage` con la
skill `onboarding-guide`; `promptRenderer.ts` di J con le regole dell'AI Export, J rivede; nessuna classe di colore
nuova.

### A9.1 — Rossi ✅ (riosservati 09:15)
- Backend sulla base nuova, in-process: **84 rossi**, 20 controlli verdi (il caso dal vivo deselezionato).
- Frontend: i 14 file scritti prima (gestito 51 casi, legale 54) restano rossi fino al codice.

### A9.2 — Codice del backend ✅ (09:16)
`work/a9/apply_a9_backend.py`: `tos_url()`/`privacy_url()` in `config/platform.py` (regola di `env_url`), accanto a
`support_url()`; `terms_link()`/`privacy_link()` in `instance_links.py` (mai un'eccezione, un indirizzo sbagliato nel
log una volta, con la sua conseguenza); `LegalInstanceConfig` e `InstanceConfigResponse.legal` in `schemas/system.py`;
una riga nella rotta `GET /system/instance`; `is_donation_popup_disabled()` vero anche col profilo `managed` (i
contatori crescono comunque); `.env.example` (le due variabili accanto a SUPPORT); runner `services donation-managed`,
`services legal-links`, `api instance-legal`.
- Verdi: in-process **104/104**; servizi **1.273** (`donation-managed` 30, `legal-links` 56, `donation-popup` 19,
  `config-package` 863, `config-env-example` 38, `profile-defaults` 112, `config-audit` 155); ruff/black puliti;
  `api sync` fatto (il client conosce `legal`).

### A9.3 — Codice del frontend ✅ (09:25)
`work/a9/apply_a9_frontend.py`, `work/a9/i18n_add.py`:
- nuovi: `features/support/donations.svelte.ts` (`donationsVisible()` = configurazione caricata **e** self-hosted),
  `features/legal/LegalNotice.svelte` (disclaimer e link), `features/legal/LegalLinks.svelte` (riga compatta, `tone`
  `page|bar` per la barra verde);
- il caffè solo con `donationsVisible()` in `AuthPageFrame` (test id `auth-donate-link`), `SupportActions` (col divisore
  «Or share»), Header, HelpMenu (`help-donate-link`, col suo divisore);
- `ChangelogModal`: «controlla aggiornamenti» nascosto solo col profilo gestito;
- `checkForNewerRelease()`: aspetta la configurazione e sonda solo un'istanza che il server dice self-hosted (anche una
  richiesta fallita non sonda, come le donazioni);
- `ForgotPasswordCard`: prima della risposta né comandi né avviso col terminale; gestito → «chiedi all'amministratore»
  (`forgot-ask-admin`); il modulo email di E invariato;
- i posti della nota legale: card `about-legal-card` in About (fuori dalla diagnostica), `auth-legal-links` sotto la
  card di ogni pagina d'accesso (il telaio chiama `instanceConfig.load()`: anche `/verify-email` la riceve),
  `LegalNotice` sotto la card della Welcome, `sidebar-legal-links` dopo la versione (tono della barra);
- i18n: `legal.title|disclaimer|disclaimerShort|terms|privacy` nella sorgente `app` (D-A14: una riga `legal` in
  `app/prefixes.txt`, perché il catalogo dà un prefisso nuovo a `base`), `auth.askAdminToResetPassword`; testo del
  disclaimer = la mia proposta, sulla lista del developer;
- runner: le 15 righe Vitest (le unità `core`, `component`, `onboarding-component`, i due elenchi di quest'ultima).
- Verdi: i 14 file rossi **105/105**; Vitest dei file intorno **1.327** verdi e 6 rossi attesi (`SupportActions.test.ts`
  ×3, `DonationPopupModal.test.ts` ×3: vogliono il caffè senza risposta del server) → riparazione a un `test-author`
  con `test_system_api.py:843` (H) e `test_registration_api.py:895` (il blocco `legal` nei campi fissati); Prettier e
  `theme-roles --check` puliti.
> **Note implementazione (onboarding)**: la nota legale della Welcome è contorno della pagina, non contenuto del flusso
> (né ancore né passi): nessun cambio di versione, che riaprirebbe la Welcome a ogni utente. Da confermare dal
> proprietario dell'onboarding.

### A9.4 — AI Export (J) — in attesa di J (09:40)
Proposta mandata al coordinatore per J: sezione `legal_notice` (`legal.title` + `legal.disclaimer` via `translate`,
niente URL: statica e identica fra UI e sonda), ultima nei dati; nelle analisi (a) ultima o (b) prima di «Response
Language» (proposta b). Rossi dopo la risposta.
- **Risposta di J** (09:48): **(b)** — D-A11 per l'AI Export si legge «ultima, **prima di Response Language**» (l'ultima
  parola resta l'istruzione fidata dell'app, dopo le note dell'utente, non fidate); nei dati (`data_only`) ultima. Nello
  stesso lotto: le due liste d'ordine di `developer/architecture/patterns/ai_export_composition.md` (analisi: un passo
  nuovo prima di Response Language; `data_only`: «Legal Notice» come passo 3); un test accanto ai test d'ordine (`:20`,
  `:121`): l'ultima sezione è `response_language` in ogni analisi e `legal_notice` nei dati; il testo sotto un titolo
  suo, mai dentro un blocco recintato; **sonda di prova**: un'analisi e un dataset (skill `ai-export-probe-tuning`),
  nel mio slot. Rossi chiesti a un `test-author` (09:50).
> **⚠️ Fuori pista (sonda)**: `ai_export_real_prompt_probe.py` copia `backend/data/prod/sqlite/app.db` e accede con gli
> account del developer (`alfy`, `marco`, password da `LIBREFOLIO_AI_EXPORT_PROBE_PASSWORD*`): fuori dalla mia corsia.
> Coordinatore (09:58): niente sonda da me; nello slot bastano `promptRenderer.test.ts` (rende con il
> `probeTranslation` del ponte della sonda), il gate `apiClientRuneFree` (`front-utility core-unit`) e
> `utils ai-export-probe-helpers`; **J fa i due casi di prova dopo l'ingresso di A9**.
- E2E di A9 chiesti a un `test-author` (09:57, nulla eseguito): uno stub che corregge la risposta vera di
  `/system/instance` (profilo, `legal`), i cinque casi (pagina d'accesso, link legali, barra laterale e About, gestito
  in app, gestito alla «password dimenticata»), una riga nel runner.

### A9.4 — AI Export ✅ (09:46–09:51; J rivede)
- **Rossi** (`test-author`, solo `__tests__/promptRenderer.test.ts` di J): le due liste d'ordine (`:24` analisi,
  `:126` dati), un test nuovo «l'ultima sezione è `response_language` in ogni analisi, la penultima `legal_notice`; nei
  dati l'ultima è `legal_notice`» (4 analisi con e senza note, 1 dataset), un test di struttura (una sola sezione,
  esattamente `## ⟦legal.title⟧`, riga vuota, `⟦legal.disclaimer⟧`; con i cataloghi veri in EN/IT/FR/ES niente ``` e
  niente `http`): **4 rossi**, 9 casi intatti verdi.
- **Codice** (`work/a9/apply_a9_ai_export.py`): `legal_notice` in `AiExportPromptSectionId`; `renderLegalNotice()`
  (titolo e disclaimer via il `translate` già in ingresso, nessuna URL, nessun dato dell'istantanea, mai in un blocco
  recintato); prima di `response_language` nelle analisi, ultima nei dati.
- **Verdi**: Vitest di `features/ai-export` **194/194** (12 file); il gate `apiClientRuneFree` **16/16** (il ponte della
  sonda non importa nulla di nuovo); `utils ai-export-probe-helpers` **73/73**; Prettier pulito.
> **Note implementazione**: la sonda Python conta ogni sezione non dell'istantanea come «instructions/contracts»
> (`ai_export_real_prompt_probe.py:1555-1559`): nei `data_only` quella quota non sarà più zero, atteso. La
> ricostruzione dalle sezioni copre solo `data_only`; l'identità UI/sonda è provata in entrambi i modi (`:313`, `:396`).
- **Riparazioni dei test esistenti** (`test-author`): `SupportActions.test.ts`, `DonationPopupModal.test.ts` (una
  risposta self-hosted col vero store in un `beforeEach`; nessuna asserzione cambiata) → `features/support` **104/104**;
  `test_system_api.py` (H: `INSTANCE_KEYS` con `legal`, commenti e docstring) e `test_registration_api.py` (il set con
  `legal`): il secondo verde in-process, il primo solo sulla corsia (slot: `api system`).

### A9.5 — Doc ✅, E2E scritti, e il cancello del pulsante del changelog (09:57–)
- **Doc** (`docs-writer`, 19 pagine inglesi): `admin/configuration`, `admin/hosting_providers` (nuova «Your Legal Pages»,
  la tabella del profilo gestito da 7 a 10 voci, corretta la frase «la stessa interfaccia nei due profili»),
  `admin/index`, `admin/cli_tools`, `admin/users`, `admin/email`; `user/settings/about` (nuova «Legal Notice»),
  `user/getting-started`, `community/contribute`; developer `architecture/settings.md` (la tabella diceva «tre campi»:
  ora cinque), `frontend/state/app-state.md`, `features/settings.md` (nuova «The legal notice»), `features/auth.md`
  (`ForgotPasswordCard` come tabella profilo × `email.links`; `/verify-email` mancava fra le pagine del telaio),
  `frontend/onboarding.md` (la nota legale della Welcome non è del flusso: nessuna versione nuova; tolti due rimandi di
  riga vecchi), `security.md` («Container Image Check», ancora nuova), `backend/email.md`, `frontend/i18n.md`,
  `frontend/index.md`, `components/index.md`. Strict build e `check-links` (97) verdi; nessun timbro (debito su
  `user/settings/about`, `community/contribute`, e già indietro `admin/configuration`, `admin/cli_tools`,
  `admin/index`, `user/getting-started`).
> **⚠️ Fuori pista**: il `docs-writer` ha aggiornato per sbaglio la tabella `todos` della sessione (tutte a «done») e le
> ha ripristinate a mano; ricontrollate: `a6-users-tab` → done (resta solo `a6b-gallery-captures`).
- **E2E** (`test-author`, nulla eseguito): `e2e/layout/legal-and-managed.spec.ts` (LGM-E-01..05), `serveInstanceConfig`
  aggiunto alla fixture di A `e2e/fixtures/instance-config.ts` (corregge la risposta vera: `profile`, `legal`), runner
  `front-utility legal-managed`; Prettier, `tsc -p tsconfig.e2e.json` (nessun errore nei file nuovi; 4 errori vecchi
  altrove), ruff/black puliti.
> **⚠️ Fuori pista (trovato da E2E e doc)**: «Check for updates» del changelog era nascosto solo con la risposta
> `managed`: prima della risposta, o per sempre dopo una richiesta fallita, un'istanza gestita lo mostrava e il clic
> sondava GitHub. Decisione: la stessa regola delle donazioni (risposta arrivata **e** self-hosted). Rossi CLM-05/06 e
> riparazione di `ChangelogModal.test.ts` (H) chiesti al `test-author` delle riparazioni; la prova positiva di LGM-E-04
> diventa il link dei termini nella barra laterale (il profilo gestito con `legal` nello stub), senza ganci nuovi nel
> prodotto. Codice pronto: `work/a9/apply_a9_changelog_gate.py`.
- **A-48** nel backlog: la pagina offline statica mostra il caffè anche su un'istanza gestita (della squadra dei
  colori; basso).
- **Cancello del changelog ✅** (10:12): rossi CLM-05 (prima di ogni risposta) e CLM-06 (richiesta fallita) in
  `ChangelogModal.managed.test.ts`, `ChangelogModal.test.ts` (H) con una risposta self-hosted in un `beforeEach`
  (nessuna asserzione cambiata); codice `work/a9/apply_a9_changelog_gate.py` (`loaded && profile === 'selfhosted'`);
  layout e About **176/176**. LGM-E-04 prova il profilo gestito con i link legali dello stub nella barra laterale (e in
  About), senza ganci nuovi.
- **Doc, seguito** (`docs-writer`): `ai_export_composition.md` (le due liste: «Legal Notice» passo 3 nei dati, passo 9
  prima di «Response Language» nelle analisi; il paragrafo nuovo con i test), `user/ai-export/index.en.md` (ogni
  esportazione finisce con la nota, senza link), i posti della nota in About/hosting/settings con l'AI Export, la regola
  del pulsante del changelog (`app-state.md`, `security.md`, `settings.md`), il caffè elencato posto per posto (la
  pagina offline nominata solo nella pagina developer). Strict build e `check-links` verdi.
> **⚠️ Fuori pista**: `front check` ha trovato 4 errori nei due componenti legali: il generatore del client allarga
> `str | None` a `(string | null) | Array<string | null>` (come `support_url` di H). Ristretto come fa H
> (`typeof … === 'string'`), nessun comportamento nuovo. Poi `front check` **0/0**.
- **Regressione Vitest larga** (support, legal, auth, update-check, layout, settings, onboarding, ai-export, instance,
  routes, i gate rune-free e dei colori): **3.013/3.013** (107 file). `theme-roles --check`, ruff/black, `git diff
  --check` puliti; porta libera.
- **FYI dalla squadra dei colori** (10:30): la corsa di G sul punto 33 di A8b è verde (18/18, entrata `e21d5cb11`); alle
  larghezze della galleria nessuna delle due barre scorre (FR/ES desktop compresi), quindi la sfumatura si giudica dal
  vivo in una finestra stretta. Il «1» su «Administration» e «Security» nelle foto admin è il conteggio dei controlli
  della corsia: **G-22** (approvata) li servirà da una fixture con lo schema vero; **i valori li rivedo io** quando è in
  calendario. Slot di A9 chiesto (10:25), in attesa.
- **Revisione di H-19** (10:40, sola lettura, dev `9b23bdbfe`: `48aa7a3ed` + `139ca6129`): **OK**. Ogni chiave
  inutilizzabile (anche un `_FILE` o un file di chiave irraggiungibile, convertiti in `InstanceKeyError`) dà 503
  `INSTANCE_KEY_UNAVAILABLE` con un avviso e `admin_id`; il controllo pubblico resta `{"match": false}`. L'Invite dialog
  resta «unverifiable»: `checkAddress()` intercetta ogni rifiuto di `issueNonce()` e l'intercettore di axios non tocca i
  503 (solo 401 e 423); coperto da APR-19 e LSH-C-06. Nota LOW per E e per me, dopo l'ingresso: il controllo dei link
  della scheda Email mappa `unverifiable` in `unreachable`; col codice nuovo le due UI potrebbero dire «questa istanza
  non può verificare indirizzi: vedi i controlli». Chiude A-23 (era la stessa voce).
- Slot di A9 in coda (10:35): dopo `all-backend` di G, l'API di W-B71 e l'E2E di H-42.
- Backlog (coordinatore 10:32): **A-23 ✅** (fatta come H-19), nuova **A-49** condivisa con E (un messaggio suo per il 503
  `INSTANCE_KEY_UNAVAILABLE` nel dialogo d'invito e nel controllo dei link della scheda Email; dopo la 1.3 salvo che
  venga facile). Vanno nel checkpoint di A9.

## A-42 + A-43 — Il ciclo di vita del link di setup: analisi (17/10, 10:35; solo lettura, A9 congelato)

Fonti: le note 1, 2 e 6 della revisione di E «R13-SEC4» (`08_email/plan-phase01Email.prompt.md` ~:4196–4209), le voci
A-42/A-43 del backlog (A-44 unita in A-43 dal coordinatore, 17/10 03:09: «disattivarlo è l'annullamento: i link si
**revocano**, non si ritirano»).

**Stato reale (HEAD `e58be67fe` + A9 non committato, che non tocca questi file)**
- `token_service`: `revoke_tokens` (vivi → `revoked_at`), `retire_tokens` (mai consumati → revocati **e** consumati:
  contano come usati), `consume_token` (un UPDATE condizionato: il primo che scrive vince).
- `registration_service.pending_admin_filter()`: inattivo, con un link `admin_setup`, nessuno consumato.
- `bootstrap_admin_service`:
  - `issue_setup_link()` (CLI `user setup-link`) e il riarmo all'avvio (`_keep_pending_admin`) decidono «in attesa»
    con una **lettura** (`pending_admin()`), prima della prima scrittura che prende il lock di SQLite (il BEGIN
    differito parte con l'UPDATE di `revoke_tokens`);
  - `complete_admin_setup()`: `consume_token` prima (il lock), rifiuta un account già attivo e ritira i suoi link
    (A-32), altrimenti password, attivo, sessioni chiuse, gli altri link revocati.
- **La gara (A-42)**: un `POST /auth/setup` che si chiude fra quella lettura e la scrittura lascia un link **nuovo e vivo**
  su un account appena attivato. Finché l'account è attivo il link è rifiutato (A-32), ma se poi viene disattivato,
  `complete_admin_setup` con quel link (account inattivo) **imposta la password e lo riattiva**: chi tiene il link (il
  terminale dell'operatore, il pannello che ha dato il token) si riprende l'account.
- **La disattivazione (A-43)**: `update_user_status` (PATCH `/users/{id}`) e `set_user_active` (CLI `user deactivate`)
  non toccano i link di setup: sull'admin in attesa (già inattivo) il PATCH `{is_active: false}` non cambia nulla e il
  link resta buono (UADM-062/067/069 e SETUP-016 lo fissano oggi come guardie di A-32); su un account non in attesa un
  link vivo rimasto (gara, o un database delle build 1.3 precedenti) resta lì.
- **La retrocessione (nota 6 di E, seconda metà, non nel backlog)**: un admin in attesa retrocesso si attiva lo stesso
  col link di setup, come utente normale («un vuoto d'intenzione»).
- UI: la riga dell'admin in attesa (`UserRow.svelte`) non ha «disattiva» (è già inattivo) né «riattiva» (409
  `PENDING_SETUP`); ha «retrocedi», il link di reset, la cancellazione; il suggerimento rimanda a `dev.py user setup-link`.

**Proposta di contratto**
1. *A-42, rilascio*: `issue_setup_link()` e il riarmo fanno prima la scrittura (la revoca dei link vivi), poi
   ricontrollano «in attesa» sotto il lock (`is_pending_admin`); se non lo è più: rollback, nessun link (la CLI dice che
   nessuno aspetta; l'avvio non riarma).
2. *A-42, consumo*: `complete_admin_setup()`, dopo `consume_token`, rifiuta se **un altro** link di setup dell'account è
   già consumato (setup già fatto, o link ritirati): rollback, ritira i link mai consumati dell'account, un avviso nel
   log, 400 `TOKEN_INVALID`. Copre il link rimasto per qualunque via.
3. *A-43, disattivazione*: sull'admin **in attesa** il PATCH `{is_active: false}` e `user deactivate` **revocano** i suoi
   link vivi (l'annullamento: resta in attesa, `user setup-link` gliene dà uno nuovo; un avviso nel log); su un account
   **non** in attesa **ritirano** i link di setup mai consumati.
4. *Retrocessione dell'admin in attesa* (decisione del coordinatore): (a) **proposta**: rifiutata con 409
   `PENDING_SETUP`, come la riattivazione (il suo ruolo resta fino al setup; per annullare: disattivare o cancellare),
   e `user demote` lo stesso; (b) in alternativa la retrocessione annulla come la disattivazione.
5. *UI* (mia, A6): sulla riga dell'admin in attesa un'azione «Annulla il link di setup» (`users-action-cancel-setup`, con
   conferma: il link consegnato smette di funzionare; uno nuovo con `dev.py user setup-link` o dal fornitore) che manda
   `{is_active: false}`; «retrocedi» disabilitato con un motivo (con 4a); chiavi i18n nella sorgente `settings`.
   Nessun «nuovo link di setup» dalla UI (resta della CLI e del pannello: fuori da questo lotto).
6. *Test*: cambiano per costruzione UADM-062, UADM-067, UADM-069 (le varianti disattiva/retrocedi) e SETUP-016 (CLI
   `deactivate`/`demote`); nuovi: la gara del rilascio (una lettura vecchia simulata: `pending_admin` restituisce
   l'account già attivo → nessun link), il link rimasto (righe scritte: un link consumato e uno vivo, account
   disattivato → `/auth/setup` 400, nulla cambiato, il vivo ritirato), l'annullamento (PATCH e CLI: link `revoked`,
   ancora in attesa, `setup-link` ne rilascia uno nuovo), il ritiro alla disattivazione di un account non in attesa,
   la retrocessione rifiutata; UI: Vitest della riga e un E2E sulla corsia se l'account in attesa si può creare lì
   (altrimenti solo Vitest).
7. *Doc*: `security.md` (ciclo di vita del link di setup), `access_control.md` (PATCH: retrocessione rifiutata,
   disattivazione che revoca o ritira), `admin/users.en.md` (annullare un admin in attesa), `admin/cli_tools.en.md`
   (`deactivate`/`demote` sull'admin in attesa), developer `features/settings.md` (la riga).

**Superfici e conflitti**: tutte di A (`bootstrap_admin_service.py`, `user_service.py`, `api/v1/users.py`,
`scripts/user_cli.py`, `UserRow.svelte` e l'handler della scheda Utenti, i18n `settings`, i test di A6/A7). E: la
riga delle verifiche email in `update_user_status` resta com'è (accanto). Le pagine `security.md`, `admin/users`,
`admin/cli_tools` sono toccate anche da A9 (altre sezioni): dopo il checkpoint di A9, nessun conflitto.
**Peso**: medio-basso. **Ordine**: rossi (servizi, API, CLI, UI) → codice → verdi → doc → E2E/slot.
**Decisioni**: del coordinatore — il punto 4 (a/b) e il punto 5 (parole e posto dell'azione); nessuna del developer.
- **Coordinatore (10:36): contratto approvato**, punti 1–5. Punto 4 → **(a)**: la retrocessione dell'admin in attesa è
  rifiutata con 409 `PENDING_SETUP`, nell'API e in `user demote`, come la riattivazione. Punto 5: «Annulla il link di
  setup» con conferma, «Retrocedi» disabilitato con un motivo, nessun rilascio dalla UI. **Dopo il commit del
  checkpoint di A9; rossi prima.** La riga è nell'area del cricchetto dei colori: nessuna classe di palette nuova (ruoli).

### A9.6 — Slot (10:37–; `e58be67fe` + A9 non committato, impronta dell'albero `37bb0f493c0fe652`)
- API: `instance-legal` 19 (col caso dal vivo), `system` 122, `registration` 102, `auth` 95 → **338, 0 rossi**.
- E2E: `legal-managed` 5, `auth` 34, `forgot-password-email` 3, `theme-roles` 22 verdi e **2 rossi** (caso (c),
  desktop e mobile).
> **⚠️ Fuori pista (triage: assunzione, non di A9)**: `layout/theme-roles.spec.ts:613` (c) vuole la card
> `dashboard-cash-balances` ancora «legacy per decisione (D-T3)» (sfondo `--theme-bg-card`), ma `daea7b31c` della squadra
> dei colori (16/10, «dashboard on colour roles») l'ha portata a `bg-lf-card`: lo sfondo è il ruolo (rgb(21,27,25)).
> Il commit è nella base di questo slot e in quella dello slot 1; A9 non tocca né la dashboard né la spec. I 22 casi
> che leggono gli elementi di A9 (caffè dell'header, comandi della «password dimenticata») sono verdi. Da segnalare
> alla squadra dei colori (proprietaria della spec).
- Resto dello slot (fino alle 11:09): E2E `header-scroll` 11, `support-copy-and-go` 16, `changelog-locale` 2; Vitest
  `core-unit` 8.124 (205 file), `component-unit` 4.697 (179), `onboarding-component-unit` 465 (16).
- **Totale**: API **338/338**; E2E **93 verdi** e 2 rossi non di A9 (sopra); Vitest **13.286/13.286**. Impronta
  dell'albero invariata (`37bb0f493c0fe652`), porta 6182 libera.
- **A9: definizione di fatto ✅** (salvo la sonda di prova di J dopo l'ingresso e la galleria di G).

## A9 — Entrato; correzione in avanti FPM-08 (17/10, 11:14–)
- **A9 entrato**: `3c9303cf2`, `b1b647edc`, `2811d5756`, `f6489c75e`, `bda45901c` → dev `ba8f3b06e`, senza conflitti;
  CHANGELOG ✨ + 🔄 `4f46144d4` (il mio ramo portato in avanti). Sulla revisione combinata il coordinatore ha fatto
  `api sync`, `front check` 0/0, `i18n check` stretto. Revisioni dei proprietari dopo l'ingresso (H, J, E; WelcomePage
  OK dal coordinatore). La sonda di prova va sulla lista del developer (servono i suoi account). G rigenera la galleria;
  il rosso di `theme-roles.spec.ts:613` passato alla squadra dei colori.
- **FPM-08** (dal coordinatore, prima del codice di A-42/A-43): una richiesta della configurazione **fallita prima di
  ogni risposta** lasciava la «password dimenticata» senza nulla (solo «torna all'accesso»). Contratto: in quello
  stato «chiedi all'amministratore» (vale per i due profili). Rosso FPM-08 (`test-author`, più le guardie FPM-09/10:
  una risposta dopo il fallimento, gestita o self-hosted, e FPM-11: un fallimento dopo una risposta tiene i comandi).
  Codice `work/a9fix/apply_fpm08.py`: `(loaded && managed) || (!loaded && failed)` → `askAdmin`. Verdi: Vitest
  `features/auth` **660/660**; `front check` 0/0; colori puliti. Doc: una riga in `features/auth.md` (`docs-writer`).
- I rossi di A-42/A-43 (nei file di test dell'area, in corso) restano **fuori** da questo checkpoint.
- **FPM-08 entrato**: `d04ffde90` → dev `cd52e25fc`; il mio ramo portato in avanti, i 5 file rossi di A-42/A-43 intatti.

## A-42 + A-43 — Implementazione (17/10, base `cd52e25fc`)

Aggiunte durante il lavoro, approvate dal coordinatore: l'admin in attesa si **cancella direttamente** (niente
`DEMOTE_FIRST` per lui: non si può retrocedere e non è mai stato un admin attivo; `DEMOTE_FIRST` resta per tutti gli
altri) e un **toast** di successo per l'annullamento (l'esito non si vede: la riga resta uguale).

### A-43.1 — Rossi ✅ (osservati a `4f46144d4`; nessun file rilevante cambiato fino a `cd52e25fc`)
- Servizi `test_admin_bootstrap.py`: **13 rossi** (A42-001..006, A43-001..005; A32-004 ridotto).
- API `test_admin_setup_api.py`: **4 rossi** (SETUP-016 cambiato, 017, 018).
- API `test_users_admin_api.py`: **18 rossi** (UADM-062/067/069 cambiati; 072–078 nuovi, UADM-076 è la cancellazione).
- UI: **18 rossi** (UPS-12..22 in `UserRow.pendingSetup.test.ts`, UTAB-55..60 in `UsersTab.test.ts`).

### A-43.2 — Codice del backend ✅ (`work/a42/apply_a42_backend.py`)
- `bootstrap_admin_service`: `issue_setup_link` e il riarmo (`_keep_pending_admin`) **revocano prima**, poi rileggono
  «in attesa» sotto il lock (`registration_service.is_pending_admin`); se non aspetta più: rollback (CLI: nessun link;
  avvio: `IGNORED`, una riga info senza token). `_setup_spent_before()` nuovo: `complete_admin_setup` rifiuta se un
  **altro** link di setup dell'account è consumato (rollback, ritiro, avviso «…the account was set up before»).
- `user_service`: `_is_pending_admin` (import locale: `registration_service` importa questo modulo) e
  `_end_setup_links` (revoca se in attesa, con un avviso; ritiro altrimenti); `update_user_status` e `set_user_active`
  leggono `waiting` prima di ogni cambio (un account già inattivo passa da `_end_setup_links`); `set_user_admin`
  rifiuta la retrocessione dell'admin in attesa.
- `api/v1/users.py`: `_PENDING_SETUP_DETAIL` condiviso (riattivazione e retrocessione, 409); `delete_account` salta
  `DEMOTE_FIRST` per l'admin in attesa; docstring.

### A-43.3 — Codice del frontend ✅ (`work/a42/apply_a43_frontend.py`, più il pulsante)
- `users/types.ts`: `'cancel-setup'`. `UserRow.svelte`: motivo `pending-setup` («Retrocedi» spento con quel motivo),
  «Elimina» acceso per l'admin in attesa, il pulsante `users-action-cancel-setup` (icona `Link2Off`) al posto di
  «Riattiva». `UsersTab.svelte`: confermabile `cancel-setup` (danger) → PATCH `{is_active:false}`, evento
  `accounts.user.setup-cancelled`, toast `settings.usersTab.toasts.setupCancelled`.
- i18n (`work/a42/i18n_a43.py`, sorgente `settings`): 6 chiavi nuove, `errors.PENDING_SETUP` riformulata (copre anche la
  retrocessione); `i18n build` + `check` stretto puliti (5 036 chiavi).
- `promptRenderer.test.ts`: le 5 etichette «red until A9» → «A9 (legal_notice)» (permesso del coordinatore).

### A-43.4 — Verdi ✅ (fino alle 12:19)
- Vitest `features/settings` + `promptRenderer.test.ts`: **1 121/1 121** (27 file; dentro UPS, UTAB e `accountErrors`).
- In processo (`/tmp/libreFolio_a8a_inproc/run.sh`): `test_admin_bootstrap.py` **207/207**; `test_admin_setup_api.py`
  **48/48** dei casi in processo; `test_users_admin_api.py` **88/88** dei casi in processo. I 38 casi delle classi della
  corsia (4 + 34) vanno nello slot.
- Corsia, servizi: `admin-bootstrap` 207, `registration` 151, `email-verification` 127, `session-version` 56,
  `user-profile` 52, `account-tokens` 76 → **669/669**; porta 6182 libera.
- ruff, black, Prettier, `theme-roles --check` puliti.
> **⚠️ Fuori pista**: lanciati in processo senza `-k`, i due file API hanno preso anche le classi della corsia: la loro
> fixture `test_server` avvia uvicorn in un thread sulla `TEST_PORT` di default, **6041**. Il lifespan è fallito sul DB
> privato vuoto **prima del bind** (`Server.startup` esce dopo `lifespan.startup()`), quindi nessuna socket; `lsof` su
> 6041 e 6182: liberi. Rimedio: `run.sh` ora fissa `TEST_PORT=6182`; nei lanci in processo le classi della corsia
> (`TestOnlyAnAdministrator`, `*OnTheLane`) si deselezionano con `-k` e girano solo nello slot.

### A-43.5 — Revisione di E (dal coordinatore, 12:19): verificata; la protezione (12:22, nessun veto)
1. `revoke_tokens` resta **un solo UPDATE**, senza pre-select: prende il lock di scrittura anche se nessuna riga
   corrisponde, e i chiamanti del setup rileggono sotto quel lock. Commento aggiunto in `token_service.py`.
2. `_setup_spent_before`: `id != spent_id`; conta i ritirati (`consumed_at`), non i soli revocati, quindi «annulla poi
   `setup-link`» funziona. I due rifiuti → `None` → `TOKEN_INVALID`, prima di `hash_password` ✓.
3. L'annullamento ha per chiave `is_active is False` + «in attesa», nel PATCH e nella CLI ✓. **Domanda aperta di E**:
   `_protected` scatta solo su una transizione, quindi un co-admin potrebbe annullare il proprietario protetto in attesa
   (solo se l'operatore ha creato prima un altro admin). **Decisione** (il coordinatore non pone veto): nel PATCH anche
   l'annullamento risponde 409 `ACCOUNT_PROTECTED`, come la cancellazione; la riga spegne «Annulla il link di setup»
   col motivo `protected`; la CLI resta sopra la protezione (potere dell'operatore, come per ogni protezione). Oggi è
   inerte: `account_protection` restituisce None (aggancio di A7). Rossi UADM-079 + UPS-23 (`test-author`).
4. Riarmo: se la rilettura dice no → rollback, una riga info senza token, `IGNORED`; `deliver_setup_link` agisce solo su
   `CREATED`, dopo il commit; la CLI stampa il link solo dopo il suo commit ✓.
- Visto verificando (LOW, backlog **A-50**): dopo un annullamento, riavviare con lo **stesso**
  `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` non lo riarma (il valore è noto): giusto, ma l'avviso dice «has expired».
- Doc (`docs-writer`, in corso): `security.md`, `access_control.md`, `admin/users.en.md`, `admin/cli_tools.en.md`,
  `developer/frontend/components/features/settings.md`.

### A-43.6 — La protezione sull'annullamento ✅ (12:24–12:42)
- Rossi (`test-author`): **UADM-079** (`TestTheSetupLinkLifecycleInTheUsersTab`: l'admin in attesa protetto, il PATCH
  `{is_active:false}` di un co-admin → 409 `ACCOUNT_PROTECTED` con `reason`; nulla cambia, il link resta vivo e completa
  il setup dopo) e **UPS-23** (2 casi: «Annulla il link di setup» spento con `data-disabled-reason="protected"`, il motivo
  sotto la riga, un click non chiama `onAction`). Osservati: 1 rosso (200 invece di 409), 2 rossi (`toBeDisabled`), i
  63 UPS vicini verdi. Guardie già esistenti, non duplicate: UADM-062/074 (il non protetto annulla), UPS-12/13.
  > **Nota del test-author**: UPS-23 clicca con `element.click()` (un browser non clicca un pulsante spento);
  > `fireEvent.click` in jsdom arriva anche al pulsante spento (devWiki «jsdom is not a browser").
- Codice (`work/a42/apply_a43_protect.py`): in `update_account` `pending` letto una volta; `cancel = request.is_active
  is False and pending` entra nel controllo di `_protected` con `deactivate` e `demote`; docstring. `UserRow.svelte`:
  `cancelReason` (`protected` o null) sul pulsante e fra i motivi della riga (al posto di null per l'admin in attesa).
- Verdi: in processo `test_users_admin_api.py` **89/89** (+UADM-079; 34 della corsia deselezionati),
  `test_admin_setup_api.py` **48/48** (4 deselezionati); Vitest `features/settings` **1 110/1 110** (26 file);
  `front check` **0/0**; ruff, black, Prettier, `theme-roles --check` puliti. Porte 6041 e 6182 libere.
- Il runner registra già i file toccati (`_frontend_utility.py:406`, `:426`; `_backend_api.py:603`, `:666`;
  `_backend_services.py:578`): nessuna voce nuova.

### A-43.7 — Doc ✅ e i rilievi del `docs-writer` (12:24–12:51)
- `docs-writer` (strict build ×2 e `check-links` 97 validi, exit 0; nessuna pagina timbrata):
  - `developer/architecture/security.md`: «Session Revocation», la tabella «Revocation», sezione nuova «♻️ The Setup
    Link's Lifecycle» (`#setup-link-lifecycle`), «Links in Use»;
  - `developer/architecture/access_control.md`: «Superusers», la tabella dell'API admin (PATCH, DELETE), «Deleting an
    Account», «Protected Accounts», «The Initial Administrator» (azioni dell'avvio `ignored`/`rearmed`/`expired`;
    corrette due frasi false di prima: «una retrocessione o una disattivazione non ritira nulla» e «una retrocessione lo
    lascia in attesa»; paragrafo nuovo `#setup-cancel`);
  - `admin/users.en.md`: «What Each Action Does», «When an Action Is Off», «Waiting for Its Setup Link», sezione nuova
    «🚫 Cancel Its Setup Link» (`#cancel-setup`), «Delete an Account»;
  - `admin/cli_tools.en.md`: `deactivate` sull'admin in attesa, «A New Setup Link…», `demote` rifiutato. **Non
    timbrata**: aggiunge contenuto, e la pagina aveva già debito (le traduzioni del 10/10 non hanno nulla di
    `setup-link`);
  - `developer/frontend/components/features/settings.md`: UsersTab (confermabile, evento, toast), UserRow (pulsante,
    motivi), «Account Errors».
- Rilievi, verificati e curati (prima dello slot, nessun cambio di comportamento):
  - la protezione sull'annullamento «non c'era»: l'aveva letta prima di A-43.6, ora c'è ✓;
  - `user demote` diceva «…or delete it», ma la CLI non cancella account → «…or delete it from Settings › Users»
    (i test vogliono solo «falso, una riga con ❌»: A43-004/005 **5/5** in processo); la citazione in
    `cli_tools.en.md:164` allineata;
  - docstring: `setup_admin` (`auth.py`: il rifiuto di A-42), `update_user_status` (annullamento e ritiro),
    `set_user_active` (lo stesso; la protezione non conta per l'operatore), `set_user_admin` (l'admin in attesa non si
    retrocede). Guardia dei testi del client `test_openapi_client_text.py` **78/78**; ruff e black puliti.
- Pagine rimaste indietro, fuori dal mandato del primo giro: `admin/hosting_providers.en.md` (la riga «withdrawn» e «A
  New Link»), `developer/architecture/database/users_access.md` (le celle `revoked_at`/`consumed_at` di `admin_setup`),
  `developer/frontend/components/features/auth.md` (lo stato `revoked`); più le citazioni UADM-079/UPS-23. Secondo giro
  del `docs-writer` **dopo lo slot** (ogni unità dello slot ricostruisce `mkdocs_src/site` se un `.md` è più nuovo:
  due build contemporanee nella stessa cartella si pesterebbero).

### A-43.8 — Slot ✅ (12:51–13:03; `cd52e25fc` + A-42/A-43 non committato, impronta dell'albero `076e96d24602ac67`)
- API `users-admin`, `admin-setup`, `auth`, `registration`; E2E `admin-users` (`work/slot_a43/slot.sh`).
- API: `users-admin` **123** (i 34 casi della corsia compresi), `admin-setup` **52** (4 della corsia), `auth` **95**,
  `registration` **102** → **372/372**. E2E `admin-users` **10/10** (regressione della scheda: la corsia ha già utenti,
  quindi nessun admin in attesa; l'annullamento è provato in processo e in Vitest, come previsto al punto 6).
- Impronta dell'albero invariata (`076e96d24602ac67`) prima e dopo ogni parte; porta 6182 libera (`lsof` rc=1).

### A-43.9 — Secondo giro della doc ✅ e chiusura (13:03–13:16)
- `docs-writer`, round 2 (dopo lo slot, nessuna build in corsa):
  - `security.md` («♻️ The Setup Link's Lifecycle»), `access_control.md` («The Initial Administrator») e
    `features/settings.md` allineate alla protezione com'è nel codice, con UADM-079 e UPS-23 citati;
  - le tre pagine rimaste indietro, solo nelle parti del link di setup:
    - `admin/hosting_providers.en.md`: la riga «withdrawn», il paragrafo dell'annullamento in «🔁 A New Link» e il
      punto ⏱️ di «🧾 Create the Administrator» (mancava l'annullamento); le sezioni di H non toccate;
    - `database/users_access.md`: le celle `revoked_at`, `consumed_at` e «Issuing» di `admin_setup`;
    - `features/auth.md`: lo stato `revoked` e la riga `400 TOKEN_INVALID` della SetupCard (il caso di A-42).
  - Build strict e `check-links` (97 validi, 8 risolti a runtime) puliti. Nessuna pagina timbrata; nessun debito di
    traduzione nuovo in questo giro. Il debito di `admin/cli_tools` (round 1 e la riga 164) resta da tradurre.
- **Rilievo del secondo giro, curato**: il messaggio di `user demote` diceva «Settings › Users», ma dalla A8b la scheda
  sta nel gruppo «Administration» → «…or delete it from Settings › Administration › Users», come gli altri messaggi
  (backup); la citazione di `cli_tools.en.md:164` allineata. In processo: A43-004/005 **5/5**, `user-demote-refused`
  di SETUP-016 **1/1**; ruff e black puliti; build strict finale pulita (66 s).
> **⚠️ Fuori pista**: dopo lo slot è cambiata solo la parola «Administration» nella frase di `user demote`: lo slot è
> girato sull'impronta `076e96d24602ac67`, che contiene già le 4 docstring e la frase con «Settings › Users». Nessun
> comportamento cambiato; i test che lanciano `user demote` vogliono solo «falso, una riga con ❌» e sono stati
> rilanciati in processo.
- Nota del `docs-writer`, per dopo: quando l'aggancio di A7 proteggerà il proprietario gestito, l'«altro
  amministratore» di `hosting_providers` non potrà più annullare dalla scheda (solo la CLI); la pagina rimanda già alla
  sezione sulla protezione.
- **A-42 + A-43: definizione di fatto ✅** (revisione di E dopo l'ingresso).

## A-42 + A-43 — Entrato; revisione di E-15 (17/10, 13:17–)
- **Entrato**: `59161e5e2`, `8f8116fce`, `00b1b2e67`, `145adbf27`, `33a617dd0` → dev `7156a24af`; CHANGELOG 🔒 ✨ 🔄
  `289fe26e8` (il mio ramo portato in avanti). Revisioni di E, J e H dopo l'ingresso.
- **Revisione di E-15** (dev `da02ed816`, `d7ae430a9`), `security.md` `:477` e `:655`: **OK**. Verificato nel codice:
  `conftest.py` legge `_SESSION_LOGIN_LIMIT = os.environ.setdefault(…, "off")` all'import e la fixture autouse
  `restore_login_limit` lo rimette, con un `MonkeyPatch` suo, prima di ogni test che non ce l'ha (e lo toglie in
  teardown); `setup_test_database()` → `get_test_data_dir()` → `configure_test_runtime()` lo scarta alla raccolta;
  `login_limit_enabled()` lo legge a ogni chiamata, quindi il ripristino per test vale; le fixture autouse dei moduli e
  `monkeypatch` dei test del limite girano dopo quella del conftest.

## H-nit + A-50 + SC-LANE-01 (17/10, 13:20–; base `289fe26e8`)

Dal coordinatore (13:17): «H's nit (one helper for the «loaded && selfhosted» rule), then A-50 if cheap»; e, facoltativo,
la docstring di SC-LANE-01 dopo E-15.

**Stato reale**
- La regola «il server ha risposto e ha detto X» è scritta a mano in 5 posti: `features/support/donations.svelte.ts:12`
  (`donationsVisible()`, mio), `components/layout/ChangelogModal.svelte:341` (di H), `components/assets/
  AssetSearchAutocomplete.svelte:159` (`githubFallback`, area asset), `features/update-check/updateCheck.ts:242` (mio,
  A9), e la gemella «gestita» in `features/auth/ForgotPasswordCard.svelte:63`, `:80` (mia).
- 28 file di test sostituiscono lo store con `vi.mock('$lib/features/instance/instanceConfig.svelte', …)`: un getter o
  un export nuovo dello store mancherebbe a quei finti, e i chiamanti si romperebbero.
- A-50: `_keep_pending_admin`, senza link vivo, dice «has expired» anche per un link revocato (annullamento, o indirizzo
  cambiato a un avvio precedente). Nessun test fissa quella frase.
- SC-LANE-01 (`test_security_checks_api.py:14-18`): «unset, without a shared backend … ok — what the case pins when the
  module is run alone»; dopo E-15 la variabile c'è (`off`) in ogni test, quindi da solo vuole `warning`. Anche «Red until
  A8a» (`:24`) è vecchia.

**Disegno**
1. Modulo nuovo `frontend/src/lib/features/instance/profile.ts`: `selfHostedConfirmed()` e `managedConfirmed()`
   (`loaded && profile === …`). Un modulo a parte, non un getter dello store: i 28 `vi.mock` restano validi (leggono solo
   `loaded` e `config`), come già `donations.svelte.ts`. I 5 posti lo usano; `donationsVisible()` resta il nome della
   regola delle donazioni e delega.
2. Rossi (`test-author`): `profile.test.ts` (stati: prima della risposta, in volo, risposta selfhosted/managed,
   fallimento prima e dopo una risposta, ricarica forzata) e un test-cancello: nessun sorgente fuori da `profile.ts`
   confronta `.profile` con `'selfhosted'`/`'managed'` (rosso oggi: 5 confronti).
3. A-50: se l'ultimo link di setup dell'account è revocato e mai consumato → «…was withdrawn (cancelled, or its address
   changed)…»; altrimenti «has expired». L'azione resta `EXPIRED`. Rossi in `test_admin_bootstrap.py`.
4. SC-LANE-01: la docstring del modulo dice la regola dopo E-15.

**Revisori**: H (`profile.ts` nella sua cartella, `ChangelogModal`), l'area asset (`AssetSearchAutocomplete`), E (A-50).
- **Coordinatore (13:24): approvato** com'è (il helper in `features/instance/profile.ts`, il cancello, A-50, la docstring
  di SC-LANE-01). `AssetSearchAutocomplete.svelte` è dell'area di X: permesso di scrittura per la riga, X rivede; H
  rivede la posizione del helper dopo l'ingresso; la registrazione nel runner è aggiuntiva.

### HN.1 — SC-LANE-01 ✅ (13:26)
- `test_security_checks_api.py`, docstring del modulo: `dev.py server --test` mette `off` **su ogni corsia** (`dev.py:333`,
  senza condizioni: anche «unless the variable is already set» era vecchia); «Which severity» dice la regola dopo E-15
  (il conftest dà sempre la variabile: `off`, quindi `warning` sotto il runner e da solo; `on` messo a mano vince nei due
  posti; i rami «non impostata» di `_expected_login_limit()` restano per un processo senza quel conftest); tolta «Red
  until A8a». Solo docstring.

### HN.2 — Rossi (13:24–, due `test-author` in parallelo, file distinti)
- Frontend: `features/instance/profile.test.ts` (unità sullo store vero) e il cancello `src/instanceProfile.gate.test.ts`
  (nessun confronto a mano di `.profile` con `'selfhosted'`/`'managed'` fuori da `profile.ts`; rosso oggi sui 6 punti),
  registrati in `_frontend_utility.py`.
- Backend: A50-001…004 in `test_admin_bootstrap.py` («withdrawn» dopo un annullamento, per PATCH e per CLI o link
  generato, e al riavvio dopo un cambio d'indirizzo; guardia: un link scaduto dice ancora «has expired»).
- Codice pronto, non applicato: `work/hnit/apply_hnit.py` (+ `profile.ts`; 6 file, dry-run pulito) e
  `work/hnit/apply_a50.py` (`_latest_setup_withdrawn()`, il ramo nuovo del WARNING; dry-run pulito).
- Doc da allineare dopo il codice (A-50): `access_control.md:511` («the next starts log the expiry»), `security.md:1733`,
  `admin/hosting_providers.en.md` (il paragrafo dell'annullamento rimanda al WARNING della scadenza).

### HN.3 — A-50 ✅ (rossi 13:33, codice 13:36, verdi 13:39)
- Rossi (`test-author`, `test_admin_bootstrap.py` +192 righe, header «Lot A-50» `:79-88`): **A50-001** (annullato per PATCH,
  token nella configurazione), **A50-002** (per `user deactivate`, link generato), **A50-003** (4 varianti: token o link
  generato × riavvio un'ora dopo o dopo le 72 h, dopo l'avvio che ha cambiato l'indirizzo), guardia **A50-004** (3: token,
  link generato, riarmato con il primo revocato e l'ultimo scaduto). Osservati: **6 rossi** sull'asserzione «withdrawn»
  (es. A50-001: «…the warning must say it was withdrawn: "…has expired: run ./dev.py user setup-link, or set a new
  LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN"»), 3 guardie verdi, i 207 di prima invariati (216 in tutto).
  > **Scelte del test-author, approvate**: l'avvio che cambia l'indirizzo dice «address changed» e **non** «withdrawn»
  > (il testo nuovo contiene anch'esso «address changed»); dopo le 72 h un link revocato resta «withdrawn» (la regola non
  > guarda la scadenza: la causa più informativa); decide solo l'ultimo link (un riarmo revoca il precedente).
- Codice (`work/hnit/apply_a50.py`): `_latest_setup_withdrawn()` (l'ultimo link `admin_setup` per `created_at`, `id`:
  revocato e mai consumato) e il ramo `elif` del WARNING: «…setup link was withdrawn (cancelled, or its address
  changed): {remedy}». L'azione resta `EXPIRED`. `black` ha messo la query su una riga (stile del progetto).
- Verdi in processo: `test_admin_bootstrap.py` **216/216**; ruff, black puliti.

### HN.4 — Il helper del profilo ✅ (rossi 13:44, codice 13:45, verdi 13:49)
- Rossi (`test-author`): `features/instance/profile.test.ts` (PRF-01…08, 11 casi, sullo store vero: `vi.resetModules()` e
  un caricamento pigro di `./profile.ts`, così ogni caso nomina il modulo mancante) e il cancello
  `src/instanceProfile.gate.test.ts` (analizza i sorgenti con i parser TS e Svelte, come `financialMathExceptions`:
  commenti, stringhe, tipi e letterali d'oggetto non contano; prende anche `{profile}`, `x['profile']`, backtick,
  parentesi/`as`/`!`/`satisfies`, `switch … case`; un controllo dal vivo vuole in `profile.ts` un confronto diretto con
  ciascun profilo; la lista dei profili è tipata sul client generato). Registrati in `_frontend_utility.py`
  (`core-unit`, `:138` e `:195`, +2 righe). Osservati: `profile.test.ts` **11/11 rossi** (modulo assente); il cancello
  **2 rossi** (i 6 punti esatti, e il controllo dal vivo) e 6 controlli verdi; `instanceConfig.test.ts` 11/11 e
  `donations.test.ts` 8/8 verdi.
  > **Nota del test-author**: ha provato in memoria il codice approvato (verde), un helper senza `loaded` (PRF-02/03/05/08
  > rossi) e uno che azzera la risposta dopo un fallimento (PRF-06/08 rossi), poi ha tolto ogni prova.
- Codice (`work/hnit/apply_hnit.py`): `profile.ts` nuovo (`selfHostedConfirmed()`, `managedConfirmed()`); i 6 punti lo
  usano: `donationsVisible()` delega; `ChangelogModal` (l'import di `instanceConfig` sostituito: era usato solo lì);
  `AssetSearchAutocomplete` (`githubFallback`, permesso del coordinatore, X rivede); `checkForNewerRelease()`;
  `ForgotPasswordCard` ×2 (`managedConfirmed()`; il ramo `!loaded && failed` invariato). Prettier ha ritoccato solo i
  due file di test nuovi.
- Verdi: Vitest su ogni file di test che tocca lo store o un modulo cambiato, più i due nuovi: **58 file, 1 822/1 822**;
  `front check` **0/0**; `theme-roles --check` pulito; `diff --check` pulito.
- Corsia, servizi `admin-bootstrap` col conftest vero (E-15): **216/216**; porta 6182 libera.
- Doc (`docs-writer`, terzo giro, in corso): `app-state.md` («Readers of `profile`»), `search_link_finder.md:337` (di X,
  una frase), `frontend/index.md:52`, eventuali elenchi dei cancelli; per A-50 `access_control.md` (~:495, ~:511, ~:648),
  `security.md` ~:1733, `hosting_providers.en.md` (il paragrafo dell'annullamento).
> **⚠️ Fuori pista (conteggio)**: i file di test che sostituiscono lo store sono **28**, non 10 (il mio `grep` era
> tagliato da `head`; corretto qui sopra, lo ha visto il `docs-writer`). Tutti e 28 erano nel giro Vitest dei 58 file
> (ogni test che nomina `instanceConfig`), verde.

### HN.5 — Doc ✅ (13:52–14:15, `docs-writer`, terzo giro)
- Helper: `developer/frontend/state/app-state.md` «Readers of `profile`» (i helper come unica prova, il perché del
  modulo a parte, ogni lettore riscritto, il cancello, i test `core-unit`, l'esempio di codice);
  `developer/backend/assets/search_link_finder.md` (N61, la sola frase: `githubFallback = selfHostedConfirmed()`, di X);
  `developer/frontend/index.md` (la riga di `instance/`). Nessuna pagina cataloga i cancelli (`designer-lab.md` ne ha
  un elenco parziale, solo del Lab): nessuna aggiunta.
- A-50: `access_control.md` («The Initial Administrator»: la riga `expired`, «A new address», «Cancelling the setup
  link», i test A50-001…004); `security.md` («The Setup Link's Lifecycle»); `admin/hosting_providers.en.md` («A New
  Link»: l'annullamento cita il WARNING *withdrawn*, il cambio d'indirizzo non parla più di scadenza);
  `admin/configuration.en.md` («The Initial Administrator»: le due frasi); `admin/users.en.md` («Cancel Its Setup Link»).
- Build strict (×2) e `check-links` (97 validi) puliti. Nessuna pagina timbrata; debito nuovo: la frase del WARNING in
  `admin/configuration` (le traduzioni non hanno ancora la sezione dell'admin iniziale).
- Lasciate com'erano, ancora esatte: `auth.md` (ForgotPasswordCard) e «Container Image Check» di `security.md`
  descrivono lo stesso comportamento senza nominare i helper.
- **H-nit + A-50 + SC-LANE-01: definizione di fatto ✅** (revisioni dopo l'ingresso: H la posizione del helper, X la riga
  di `AssetSearchAutocomplete` e la frase di `search_link_finder`, E A-50).

## H-nit + A-50 — Entrato; A-46 + A-47 (17/10, 14:02–; base `d9ee72df1`)
- **Entrato**: `9db6cb0be`…`a2e428f35` → dev `d7641f368`, CHANGELOG 🔄 `d9ee72df1`; sulla punta di dev nessun confronto a
  mano del profilo fuori da `profile.ts`. Revisioni di H, X, E dopo l'ingresso. Due messaggi del coordinatore in coda da
  prima (FPM-08, la nota di J) sono arrivati tardi: FPM-08 era già entrato (`d04ffde90`), detto al coordinatore.
- **Nota di J** (A9, AI Export: OK): le 5 etichette «A9 (legal_notice)» di `promptRenderer.test.ts` non dicevano la regola.
  Fatto (solo commenti): tre tolte (il nome del test o il commento seguente dice già la regola), due riscritte («the
  legal notice comes right before response_language, which stays last: the app's trusted instruction»; «Data only: the
  legal notice comes last»). Prettier pulito; Vitest del file **13/13**.

**A-46 + A-47 — contratto** (coordinatore: «Go: A-46 + A-47»; dettagli mandati, nessuna decisione aperta)
- Stato reale: `create_user`/`update_profile` restituiscono `(None, messaggio)`; `auth.py:445` (profilo) e
  `registration_service.py:261` scelgono `USERNAME_INVALID` confrontando il testo con `USERNAME_RESERVED_MESSAGE` (A-47).
  `cmd_create_user` rifiuta la `@` (A-21a) ma non 2 o 60 caratteri (A-46): registrazione e profilo li fermano con lo
  schema (422), `LIBREFOLIO_ADMIN_USERNAME` all'avvio. 58 chiamate nei test confrontano i messaggi come stringhe.
- Cura: `AccountError`, una sottoclasse di `str` con `.code` (il messaggio non cambia, quindi ogni `error == "…"` e
  `(None, "…")` dei test resta valido): `USERNAME_INVALID`, `USERNAME_TAKEN`, `EMAIL_TAKEN`, `USER_NOT_FOUND`;
  `_new_username_refusal()` (prima la `@`, poi 3–50: la regola di A-21a resta identica) in `create_user` e in
  `update_profile` (solo un nome cambiato). La lunghezza ha lo stesso codice `USERNAME_INVALID`: via HTTP lo schema
  risponde 422 prima, e la UI traduce `USERNAME_INVALID` con «niente @» (`registrationErrors.ts:25`). I chiamanti
  guardano `.code`. `ADMIN_USERNAME_MIN/MAX_LENGTH` (usate solo in `config/accounts.py`) → `USERNAME_MIN/MAX_LENGTH`,
  più `USERNAME_LENGTH_MESSAGE`; i letterali degli schemi restano (gli schemi non importano la configurazione).
- Rossi (`test-author`, in corso): `test_username_rules.py` (CLI e servizio: 2/51 caratteri rifiutati, 3/50 passano; i
  codici su ogni rifiuto, e i messaggi di prima) e `test_username_rules_api.py` (il messaggio riformulato nel solo
  `user_service`: profilo e registrazione dicono ancora `USERNAME_INVALID`).
- Codice pronto: `work/a46/apply_a46.py` (4 file, dry-run pulito).

### A46.1 — Rossi ✅ (14:04–14:22, `test-author`)
- `test_username_rules.py`: **UNAME-020** (CLI, 2/51 caratteri × admin/utente, barriera a 3/50), **021** (`create_user`),
  **022** (`update_profile`), guardia **023** (un nome vecchio di 2 o 51 caratteri, scritto come riga, resta), **030**
  (9 casi: ogni rifiuto porta il suo codice e il messaggio di prima; i casi della regola 2 sotto `EMAIL_TAKEN`), **031**
  (`register_user` con il messaggio riformulato nel solo `user_service` → `USERNAME_INVALID`). Osservati: **18 rossi**
  (es. «red until A-46: user create '52', 2 characters, must be refused: the command answered True…»), 2 guardie verdi,
  i 32 di prima verdi.
- `test_username_rules_api.py`: **UNAME-API-12** (profilo e registrazione col messaggio riformulato → `USERNAME_INVALID`;
  oggi «400 {"detail":"Reworded…"}» e `ACCOUNT_EXISTS`), guardie **13** (la `@` → `USERNAME_INVALID`) e **14** (2/51
  caratteri: ancora il 422 dello schema, sulle due rotte). Osservati: **2 rossi**, 6 guardie verdi, i 39 di prima verdi.
  > **Scelte del test-author, approvate**: UNAME-021/022 vogliono A-46 e A-47 insieme (guardano anche il codice); i test
  > della riformulazione controllano prima che il testo riformulato torni davvero (il messaggio va letto a ogni chiamata,
  > non costruito all'import: `_new_username_refusal()` lo legge a ogni chiamata).

### A46.2 — Codice ✅ e verdi (14:24–14:28)
- `work/a46/apply_a46.py`: `config/accounts.py` (`USERNAME_MIN/MAX_LENGTH`, `USERNAME_LENGTH_MESSAGE`; il controllo di
  `LIBREFOLIO_ADMIN_USERNAME` sulle costanti nuove); `user_service.py` (`AccountError`, `_new_username_refusal()`, i 7
  rifiuti di `create_user`/`update_profile` col codice, i tipi di ritorno, le docstring); `auth.py` (il profilo guarda
  `error.code`, `detail=str(error)`; tolto l'import di `USERNAME_RESERVED_MESSAGE`); `registration_service.py` (lo stesso).
- In processo: `test_username_rules.py` **52/52**, `test_username_rules_api.py` **47/47**. Corsia, servizi:
  `username-rules` 52, `username-lookup` 17, `user-profile` 52, `email-case` 67, `registration` 151, `session-version`
  56, `settings` 23, `admin-bootstrap` 216 → **634/634**; porta libera. ruff, black puliti.
- Slot approvato (API `auth`, `registration`, `account-deletion`), dopo il quarto giro del `docs-writer`.

### A46.3 — Doc ✅ (14:29–14:33, `docs-writer`, quarto giro)
- `admin/cli_tools.en.md` («Create and List Users», il punto 🔤: la regola 3–50 dopo la `@`, il messaggio, uscita `1`);
  `developer/architecture/security.md` («Which Account an Identifier Names»: la regola 1 con `_new_username_refusal()`,
  i paragrafi nuovi «The length of a new username» e «Refusals with a code» `#username-refusal-codes`, i test; la
  tabella delle risposte di «Changing the Email»); `access_control.md` («Superusers», la tabella degli esiti della
  registrazione, la riga di `LIBREFOLIO_ADMIN_USERNAME` con le costanti nuove); `database/users_access.md` (`USER`: la
  regola 3–50 su ogni via, un controllo del servizio e non della tabella: SQLite non impone `VARCHAR(50)`).
- Build strict e `check-links` (97 validi) puliti. Nessuna pagina timbrata; debito nuovo: la frase 3–50 di
  `admin/cli_tools`.
- Rilievi: (1) `admin_bootstrap_config()` controlla prima la lunghezza e poi la `@` (il servizio il contrario): un nome
  di 51 caratteri con una `@` ha due messaggi diversi dalla variabile e da `user create`; innocuo, lasciato (la
  configurazione non può importare il servizio). (2) Il commento di `_REGISTRATION_REFUSALS["USERNAME_INVALID"]` in
  `auth.py` diceva solo «holding an @» → riscritto (solo commento, prima dello slot). (3) La doc del frontend dice
  `USERNAME_INVALID` = «niente @»: resta vero finché il 422 dello schema arriva prima (UNAME-API-14).

### A46.4 — Slot ✅ (14:34–14:40; `d9ee72df1` + A-46/A-47 non committato, impronta `8717c06456bc9df2`)
- API `auth`, `registration`, `account-deletion` (`work/slot_a46/slot.sh`): **95**, **102**, **9** → **206/206** (REG-002 e
  PROF-008, i 400 semplici, compresi). Impronta invariata; porta 6182 libera.
- **A-46 + A-47 (+ la nota di J): definizione di fatto ✅** (revisione di E dopo l'ingresso; J per i commenti).

## A-46 + A-47 — Entrato; A-45 e A-51 (17/10, 14:42–; base `f8e1f6aed`)
- **Entrato**: dev `abbe19d37` (`521679986`), CHANGELOG 🐛 `f8e1f6aed`. Due messaggi in coda da prima, arrivati tardi:
  la nota di H sul helper (già fatto ed entrato, `d7641f368`) e la revisione di E di A-42/A-43 (OK; una nota LOW → A-51).
- **A-45** ✅ (14:45): `developer/api/index.md`, la riga di `/auth` («login, token refresh») → le rotte vere (accesso e
  uscita: un cookie che dura `session_ttl_hours`, **nessun refresh token**, con il rimando a «Token Expiration»; `me`,
  registrazione, profilo e password, la cancellazione del proprio account con l'anteprima; i link: `tokens/inspect`,
  `password-reset`, `setup`; l'`address-probe`). Ancore verificate nel sito costruito (`#token-expiration`,
  `#address-probe`). La build strict viaggia con la doc di A-51.

### A-51 — Le decisioni su letture fatte prima del lock (analisi, 14:50)
Dal coordinatore: «A-51: yes, before 1.3, right after A-45 … Reds first for both stale-read paths. The new 409 code gets
its i18n keys in 4 languages, and run the HTML gate/`core-unit` with them. Add the A-51 line in that same lot.»
- **Stato reale (nota di E)**: l'annullamento (PATCH) e la cancellazione diretta decidono da letture fatte prima del
  lock: se l'admin in attesa completa il setup in quel millisecondo, l'annullamento è un no-op con un 200 vecchio
  (`is_active: false` accanto a `pending_setup: false` fresco) e la cancellazione toglie l'admin appena attivato senza
  `DEMOTE_FIRST`.
- **Trovato in più**: il «Cancel setup link» della scheda manda `{is_active:false}`, lo stesso corpo di una
  disattivazione: se il proprietario completa il setup mentre la scheda mostra ancora la riga in attesa, un clic minuti
  dopo **disattiva il proprietario nuovo** (e il toast dice che il link è stato annullato). Il lock da solo non basta:
  serve l'intenzione nella richiesta.
- **Stesso tipo, CLI**: `set_user_active` decide l'ultimo admin con `user.is_active` letto prima (`_is_last_active_admin`):
  un `user deactivate` nel millisecondo del setup su un'istanza F02 nuova può disattivare l'unico admin.
- **Contratto proposto**: PATCH con il campo facoltativo `cancel_setup: true` (solo con `is_active:false`, altrimenti 422);
  `update_user_status` prende prima il lock (`db.session.begin_writes(session, User)`, l'aiuto di W-B20), rinfresca
  l'account e decide tutto sotto il lock; con `cancel_setup` e un account che non aspetta più → rollback, 409
  `SETUP_COMPLETED`; un PATCH semplice resta «disattiva», deciso dallo stato fresco. DELETE: lo schema di A-42 (se la
  prima lettura dice «in attesa»: lock, rinfresco, seconda lettura; se il setup ha vinto → rollback, 409 `DEMOTE_FIRST`).
  CLI `user deactivate`: lock, rinfresco, poi la guardia dell'ultimo admin. UI: `SETUP_COMPLETED` in
  `ACCOUNT_ERROR_CODES`, la chiave `settings.usersTab.errors.SETUP_COMPLETED` in 4 lingue, il corpo
  `{is_active:false, cancel_setup:true}`; `api sync`. Rossi simulati come in A42 (la prima chiamata di
  `is_pending_admin` dà la risposta vecchia). In attesa dell'OK del coordinatore sul campo e sul punto CLI.
- **Coordinatore (14:52): OK** su `cancel_setup` e sul punto CLI: «The intent-carrying body is the right cure. Make the
  field additive and optional, so existing API callers keep working. CHANGELOG 🐛 line in your checkpoint.»
- Riga A-51 aggiunta al backlog (sezione A, prima di X).

### A51.1 — Rossi (14:53–, due `test-author` in parallelo, file distinti)
- Backend: A51-001…006 in `test_users_admin_api.py` (classi in processo: la scheda vecchia e il millisecondo con
  `cancel_setup`, il caso vero di annullamento con il campo, il 422, la risposta uguale al database per il PATCH semplice,
  la DELETE → `DEMOTE_FIRST`), A51-007 (`user deactivate`) e A51-008 (`user demote`, aggiunto: lo stesso difetto,
  `_is_last_active_admin` legge `user.is_active` vecchio) in `test_admin_bootstrap.py`.
- Frontend: UTAB-61/62 in `UsersTab.test.ts` (il corpo `{is_active:false, cancel_setup:true}`; il 409 →
  `settings.usersTab.errors.SETUP_COMPLETED`), `accountErrors.test.ts` (il codice nuovo).
- Codice pronto, non applicato: `work/a51/apply_a51.py` (schema con `cancel_setup` e il validatore; le due rotte;
  `update_user_status`, `set_user_active`, `set_user_admin` con `begin_writes` + `refresh` prima di decidere; la scheda e
  `ACCOUNT_ERROR_CODES`; dry-run pulito) e `work/a51/i18n_a51.py` (la chiave in 4 lingue). La sessione della richiesta
  si chiude con `async with`: una transazione rimasta aperta senza cambi si annulla e libera il lock.
- Frontend, osservati (15:04): `UsersTab.test.ts` **UTAB-61** (rosso: «expected { is_active: false } to deeply equal {…
  cancel_setup }») e **UTAB-62** (rosso su `detail.code` `null`; il resto — nessun successo, la riga ridisegnata come la
  dà il server — già passa oggi), 60 verdi; `accountErrors.test.ts` **AERR-13** (codice) e **AERR-14** (la frase nei
  quattro cataloghi, senza segnaposto) rossi, 33 verdi. **UTAB-56** allentato (il corpo contiene `is_active: false`;
  il corpo esatto lo fissa UTAB-61): approvato. La guardia «Deactivate» → `{is_active:false}` esatto c'era già (UTAB-32).
- Backend, osservati (15:08): `test_users_admin_api.py` **A51-001/002/003** rossi (422 `extra_forbidden` su
  `cancel_setup`), **A51-005** rosso («it answered {'is_active': False, 'pending_setup': False}, the database holds
  {'is_active': True, …}»), **A51-006** rosso («409 DEMOTE_FIRST: got 204»), guardia **A51-004** verde (4 corpi); 89 di
  prima verdi. `test_admin_bootstrap.py` **A51-007** e **A51-008** rossi; 216 di prima verdi.
  > **Scelte del test-author, approvate**: la gara di PATCH/DELETE scatta dentro la prima lettura `is_pending_admin`
  > della rotta (lettura vera, poi il setup completato su un'altra connessione, poi la risposta di prima): presuppone
  > quella lettura prima del lock, come nel codice. La CLI usa un innesco indipendente dall'ordine (dopo il caricamento
  > o prima della prima scrittura, gli aiuti di A42).
  > **⚠️ Trovato dal test-author**: oggi `user deactivate` nel millisecondo **non** disattiva: risponde successo e chiude le
  > sessioni del proprietario nuovo, ma non scrive `is_active` (il valore nuovo uguale a quello vecchio letto: SQLAlchemy
  > non scrive la colonna). `user demote` toglie davvero l'unico admin.

### A51.2 — Codice ✅ e verdi (15:09–15:23)
- `work/a51/apply_a51.py` (5 file) e `work/a51/i18n_a51.py` (`settings.usersTab.errors.SETUP_COMPLETED`, 4 lingue;
  `i18n check` stretto, 5 051 chiavi). `api sync` (il client generato ha `cancel_setup`); `front check` **0/0**;
  Prettier ha ritoccato solo `UsersTab.test.ts`; ruff, black puliti.
- In processo: `test_users_admin_api.py` **98/98** (34 della corsia deselezionati), `test_admin_bootstrap.py` **218/218**,
  `test_admin_setup_api.py` **48/48**.
- Vitest: `features/settings` più gli 11 cancelli dei sorgenti (`htmlInterpolation`, `htmlSink` compresi) → **37 file,
  1 357/1 357**.
- Corsia, servizi: `admin-bootstrap` 218, `user-profile` 52, `session-version` 56, `email-verification` 127,
  `registration` 151, `username-rules` 52 → **656/656**; porta libera.
- Doc: quinto giro del `docs-writer` in corso. Slot chiesto (API `users-admin`, `admin-setup`, `account-deletion`; E2E
  `admin-users`; Vitest `core-unit`, `component-unit`), dopo la doc: `work/slot_a51/slot.sh`.

### A51.3 — Slot, prima parte: Vitest ✅ (15:23–15:33; impronta `95113de0071535d5`)
- Il coordinatore (15:23): API ed E2E in coda (quattro esecuzioni pesanti in corso), i Vitest subito. `core-unit`
  **209 file, 8 459/8 459** (con `instanceProfile`, `htmlInterpolation`, `htmlSink` e gli altri cancelli);
  `component-unit` **179 file, 4 802/4 802** (con `UsersTab.test.ts`). Impronta invariata; porta 6182 libera.

### A51.4 — Doc ✅ (15:20–15:39, `docs-writer`, quinto giro; e A-45)
- `access_control.md` (la riga PATCH con `cancel_setup?`, la DELETE e «Deleting an Account» punto 4, il punto nuovo
  «Decided under the write lock» per `deactivate`/`demote` della CLI, «Cancelling the setup link» col corpo nuovo, il
  paragrafo nuovo «A setup completed meanwhile» `#setup-completed-meanwhile`, i test A51); `security.md` («The Setup
  Link's Lifecycle», la riga della tabella Revocation, «Session Revocation»); `admin/users.en.md` («Cancel Its Setup
  Link»: il messaggio e la riga ricaricata; la DELETE nella stessa gara → *demote first*); `features/settings.md`
  (UsersTab, Account Errors, i test). `admin/cli_tools` senza cambi (tutto ancora vero). La riga di A-45 verificata.
  Build strict e `check-links` (97 validi) puliti; nessun timbro, nessun debito nuovo.
- **Rilievo, curato**: `cancel_setup` su un account che non ha mai aspettato (solo da una chiamata API diretta: la scheda
  manda il campo solo dalle righe in attesa) riceveva «This administrator completed its setup in the meantime». La frase
  dell'API e la riga INFO ora sono neutre («This account does not wait for its setup: nothing was changed»; «Setup
  cancellation refused: the account does not wait for its setup»); la frase della UI (chiave i18n) resta, giusta per le
  righe in attesa. `access_control.md` allineata (la citazione e il perché). Nessun test fissava le due frasi; A51
  ricontrollati in processo **9/9**; build strict pulita (78 s).
- Rilievo lasciato: i controlli della rotta fuori dal lock (protezione, `PENDING_SETUP` di retrocessione e
  riattivazione, il limite) usano la prima lettura; una lettura vecchia lì può solo rifiutare, mai permettere.

### A51.5 — La revisione di E di A-46/A-47: `AccountError` copiabile ✅ (15:40–15:47)
- E (OK, nessun rilievo; una cosa da poco per questo lotto): `AccountError` (sottoclasse di `str`) non si copia, né con
  `deepcopy` né con `pickle`: `str.__getnewargs__` restituisce solo il messaggio e `AccountError.__new__` vuole
  `(code, message)` → `TypeError`. Cura provata da E: `__getnewargs__` → `(self.code, str(self))`.
- Rosso (`test-author`): **UNAME-032** in `test_username_rules.py` (3 casi: `copy.copy`, `copy.deepcopy`, pickle; su un
  rifiuto vero di `create_user`), osservato rosso sul `TypeError` («AccountError.__new__() missing 1 required positional
  argument: 'message'»), i 52 di prima verdi. Nota: i protocolli pickle 0 e 1 passano già (`copyreg._reconstructor`).
- Cura applicata (con `# type: ignore[override]`: `str` dichiara `tuple[str]`); il file **55/55**; ruff, black puliti.
- Slot (GO dalle 15:50): API `users-admin`, `admin-setup`, `account-deletion`, poi E2E `admin-users`. La frase sulla copia
  in `security.md` («Refusals with a code») viene dopo lo slot (un `.md` più nuovo farebbe ricostruire il sito a ogni
  avvio del server dello slot).

### A51.6 — Slot, seconda parte ✅ (GO dalle 15:50; 15:50–16:02; impronta `915a562af5e1b986`)
- API `users-admin` **132** (i 34 casi della corsia compresi), `admin-setup` **52**, `account-deletion` **9** → **193/193**;
  E2E `admin-users` **10/10**. Impronta invariata prima e dopo; porta 6182 libera. (La prima parte, Vitest, era girata
  sull'impronta `95113de0071535d5`: dopo sono cambiati solo file del backend — la frase neutra, `__getnewargs__`.)
- Doc dopo lo slot: `security.md` («Refusals with a code»: `AccountError` sopravvive a copia, deepcopy e pickle con il
  suo codice; UNAME-032 fra i test). Build strict e `check-links` (97 validi) puliti.
- **A-51 (+ A-45, + la cura di E su A-47): definizione di fatto ✅** (revisione di E dopo l'ingresso).

## A-51 — Entrato; A11 / C-54 «Novità dalla tua ultima versione» (17/10, 16:06–; base `15ae6f61e`)
- **Entrato**: dev `180be0ff1` (`86b2f2f47`), CHANGELOG 🐛 ×2 `15ae6f61e`. Revisione di H di A-42/A-43 e A-50: OK, con una
  nota (`hosting_providers.en.md`: «(not for a protected account)») per questo lotto.
- Dal coordinatore: «A11 / C-54 … yes for 1.3, analysis first. On LibreFolio Cloud the operator updates the instance, so
  users otherwise never learn what changed.» Vincoli: `ChangelogModal` è nell'area dei colori (nessuna classe; chiedere
  prima di toccare il markup); il testo del changelog resta quello del bundle, le stringhe del modale in i18n.

### C-54 — Analisi (16:20, sola lettura)
**Stato reale**
- `users.last_seen_version` esiste già (`VARCHAR(40) NULL`, migrazione 005, D-A12): nessuna migrazione. Oggi nessuno lo
  scrive né lo legge.
- Il bundle: `CHANGELOG.md` più le traduzioni `CHANGELOG.{it,fr,es}.md`; `features/changelog/changelog.ts` le analizza
  (`parseChangelog`, `[Unreleased]` tenuto come capitolo) e `localizedChangelog` dà i capitoli nella lingua
  dell'interfaccia, in inglese dove manca la traduzione (con la pastiglia «non ancora tradotto» in `ChangelogModal`).
- `ChangelogModal` (`components/layout/`, area dei colori; montato da Sidebar e About): ricerca, indice a chip, pieghe,
  il pulsante «Controlla aggiornamenti» (solo self-hosted confermato).
- `DeferredAppPopups` (`features/onboarding/components/`): un popup automatico alla volta (oggi `donation`, poi `update`),
  in attesa finché c'è una guida o un modale aperto; una richiesta manuale dell'aggiornamento passa sopra.
- Versioni: backend `get_version()` (`LF_APP_VERSION`, `git describe`, `VERSION`: in corsia `v1.2.1-2106-g…-dirty`);
  frontend `APP_VERSION` (lo stesso build) e `compareVersions()`/`parseVersion()` in `update-check/updateCheck.ts`.
- Al login la risposta porta `show_donation_popup` (deciso dal backend); `AuthUserResponse` (login e `/auth/me`) non ha
  la versione vista.

**Disegno proposto**
1. *Dove*: `users.last_seen_version`, per utente, sempre una release base `X.Y.Z` (la versione in esecuzione senza il
   suffisso di `git describe`; una versione illeggibile → nulla di scritto).
2. *Account nuovi mai*: `user_service.create_user` scrive la release in esecuzione (ogni via di creazione ci passa:
   registrazione, inviti, CLI, admin F02).
3. *Account di prima* (`NULL`): una volta, con il solo capitolo della release in esecuzione (alternativa: scritti in
   silenzio senza mostrare nulla, ma allora chi passa alla 1.3 non vede le novità della 1.3).
4. *Quando*: al primo caricamento dell'app dopo un aggiornamento — login o una sessione sopravvissuta all'aggiornamento —
   via `AuthUserResponse.last_seen_version` (login e `/auth/me`); finché non è segnato visto.
5. *Quali capitoli*: quelli rilasciati con `last_seen < v ≤ release in esecuzione`, dal più nuovo; mai `[Unreleased]`;
   nessun capitolo → nessun modale (le build di sviluppo).
6. *Visto*: alla chiusura (pulsante, Esc, sfondo) `POST /api/v1/auth/whats-new/seen` → il server scrive la sua release
   (mai una versione mandata dal client), 204, idempotente; se fallisce, il modale torna al caricamento dopo.
7. *Profili*: uguale su gestito e self-hosted (niente codice solo cloud); sul gestito è l'unico canale.
8. *UI*: un modale nuovo `features/changelog/WhatsNewModal.svelte` (ModalBase, solo ruoli dei colori, i capitoli col
   cammino Markdown di `ChangelogModal`: `marked` + `sanitizeHtml` + `typesetFrenchMarkdown`; sezioni aperte; un link al
   changelog completo). `ChangelogModal` non si tocca. `DeferredAppPopups` (area dell'onboarding) prende un tipo nuovo
   `whats-new`, prima di `update` e `donation`: uno alla volta, mai sopra una guida o un altro modale. Chiavi i18n
   `changelog.whatsNew.*` nella sorgente `app` (dove vive `changelog`).
9. *Test*: backend (la release base; `create_user` la scrive; `last_seen_version` nella risposta di login e di `/me`;
   `POST …/seen`: 401 anonimo, 204, la release scritta, idempotente); Vitest (la regola dei capitoli: `NULL`, intervallo,
   `[Unreleased]`, downgrade, build di sviluppo; il modale; l'ordine e l'attesa in `DeferredAppPopups`); E2E nuovo in
   `e2e/layout/` con le risposte intercettate (un utente con una versione vista vecchia → i capitoli giusti per
   `data-testid` → chiusura → il POST osservato → ricarica → niente modale; gestito e self-hosted). Slot ~15 min (l'E2E
   nuovo, API `auth`, Vitest `core-unit`/`component-unit`). Galleria (G) dopo l'ingresso.
10. *Doc*: utente (cosa vede al primo accesso dopo un aggiornamento), admin (gestito/self-hosted), developer (API,
    `DeferredAppPopups`, il modale).

**Da decidere (coordinatore)**: (a) il punto 3; (b) i capitoli tradotti del bundle (come `ChangelogModal`) contro il
vincolo «il testo resta inglese»; (c) il permesso su `DeferredAppPopups`; (d) il punto 4 (ogni caricamento vs solo login).
**Conflitti**: `schemas/auth.py` (`AuthUserResponse`, tocchi di E), `DeferredAppPopups` (onboarding), la sorgente i18n
`app`. **Peso**: medio. Più la nota di H (`hosting_providers.en.md`).
- **Coordinatore (16:09): GO**, rossi prima. (a) account `NULL`: una volta, il solo capitolo della release in esecuzione;
  (b) `localizedChangelog` (tradotto dove c'è, inglese altrimenti: «il mio "solo inglese" era sbagliato»); (c) scrittura
  su `DeferredAppPopups.svelte` per il tipo nuovo e l'ordine soltanto; (d) a ogni caricamento finché non è segnato
  visto. `WhatsNewModal` solo ruoli (`theme-roles --check`); riga ✨ al checkpoint; slot ~15 min a richiesta.
- **⚠️ Rischio trovato, e la correzione (coordinatore OK 16:14)**: i DB delle corsie sono popolati da prima, i loro utenti
  hanno `NULL` → con (a) ognuno vedrebbe il modale al primo caricamento e gli E2E di tutte le corsie si fermerebbero.
  Quindi: il backend manda `user.whats_new: {since, release} | null` già deciso (non la colonna grezza); un interruttore
  nascosto `LIBREFOLIO_DISABLE_WHATS_NEW` (come quello delle donazioni, D-A7: solo nella doc dei test, né
  `.env.example` né pagine admin) lo spegne; `dev.py server --test` lo mette su ogni corsia (una riga, permesso del
  coordinatore: E e H toccano `dev.py` altrove); l'E2E del lotto intercetta `/auth/me` e il POST, non scrive mai sugli
  utenti condivisi.
- **Nota di H** applicata: `admin/hosting_providers.en.md` «…but not for a protected account, whose button is off».

### C54.1 — Rossi (16:15–, tre `test-author` in parallelo, file distinti)
- Backend: `test_services/test_whats_new_service.py` (WN-…), `test_api/test_whats_new_api.py` (WN-API-…), unità
  `services whats-new` e `api whats-new`.
- Frontend: `whatsNew.test.ts`, `whatsNewStore.test.ts`, `WhatsNewModal.test.ts`, i casi nuovi di
  `DeferredAppPopups.test.ts`; registrati con `changelog.test.ts`.
- E2E: `e2e/layout/whats-new.spec.ts` (WNE-…), unità `front-utility whats-new`.
- Codice pronto, non applicato (`work/c54/`): `whats_new_service.py` (`release_of`: almeno `X.Y`, così un hash non è una
  release; `current_release` da `config.get_version()` a ogni chiamata; `pending_for`; `mark_seen` idempotente),
  `config.accounts.whats_new_disabled()`, `WhatsNewRead` e `AuthUserResponse.whats_new`, `_auth_user()` per le sei
  risposte con l'utente, `POST /auth/whats-new/seen` (204), `create_user` con la release in esecuzione, la riga di
  `dev.py`; `whatsNew.ts`, `whatsNewStore.svelte.ts` (`fromStore(auth)`), `WhatsNewModal.svelte` (ruoli; lo stile del
  Markdown come in `ChangelogModal`, con le variabili dei ruoli), `DeferredAppPopups` (`whats-new` primo);
  `i18n_c54.py` (5 chiavi `changelog.whatsNew.*`, i termini delle chiavi `changelog.*`). Dry-run pulito.
- E2E (16:35): `e2e/layout/whats-new.spec.ts` (WNE-01…06, solo desktop; le attese dal `CHANGELOG.md` della radice: oggi
  `release` 1.2.1, `since` 1.2.0; `/auth/me` intercettato che cambia `user.whats_new` ma non aggiunge un campo che manca;
  il POST intercettato e contato; ogni caso controlla anche che la corsia dica `whats_new: null`, cioè l'interruttore).
  Registrato (`front-utility whats-new`, accanto a `legal-managed`). Non eseguito (serve lo slot): rosso per
  costruzione finché il backend non manda il campo. tsc e Prettier puliti.
- Backend, osservati (16:49): `test_whats_new_service.py` (WN-001…010, 52 casi) e `test_whats_new_api.py` (WN-API-01…07,
  8 casi; 04 e 07 aggiunti dal test-author) → **57 rossi** (il modulo che non c'è; «create_user must write the running
  release … holds None»; «the answer's user must carry whats_new … it carries ['created_at', …]»; «… must be 401: got
  404»), **3 guardie verdi** (WN-008). Il test-author li ha provati verdi su una controfigura del contratto (60/60) e
  rossi su otto difetti voluti. Registrati: `services whats-new`, `api whats-new`.
- Frontend, osservati (16:50): `whatsNew.test.ts` (WN-01…11, 28 casi), `whatsNewStore.test.ts` (WNS-00…12, 16: WNS-00
  verde di proposito — l'auth vero tiene `whats_new` come arriva), `WhatsNewModal.test.ts` (WNM-01…10, 12),
  `DeferredAppPopups.test.ts` (DAP-WN-01…05) → **60 rossi** per il motivo voluto (i moduli che non ci sono; «nothing
  imports …whatsNewStore.svelte»), i 5 casi di prima verdi. Registrati in `core-unit`, dopo `changelog.test.ts`.
  > **Scelte del test-author, approvate**: il modale prova con lo store e l'auth veri; la pastiglia dentro il blocco del
  > capitolo; i capitoli in inglese subito, senza segnaposto; `chapters` dello store = i capitoli inglesi semplici;
  > DAP-WN-05: una richiesta manuale d'aggiornamento interrompe «What's new» senza chiuderlo, che poi torna.

### C54.2 — Codice ✅ e verdi (16:49–17:04)
- `work/c54/apply_c54.py` (6 file modificati, 4 nuovi; `auth.py`: le sei risposte con l'utente passano da `_auth_user`;
  `black` ha aggiunto una riga vuota) e `work/c54/i18n_c54.py` (5 chiavi; `i18n check` stretto, 5 059 chiavi).
  `api sync`; `front check` **0/0**; `theme-roles --check` pulito; Prettier: niente da cambiare; ruff e black puliti sui
  miei file. `dev.py`: i 43 errori di ruff e il formato non-black sono gli stessi a HEAD (toccata una riga).
- In processo: `test_whats_new_service.py` **52/52**, `test_whats_new_api.py` **8/8**; regressione `test_admin_setup_api.py`
  48, `test_username_rules_api.py` 47, `test_users_admin_api.py` 98, `test_username_rules.py` 55.
- Vitest: i 4 file nuovi o cambiati più ogni test che monta l'ospite dei popup → **347/347**, tranne
  `OnboardingCoachmark.test.ts`, che non si caricava più (atteso: «Denied ID …/CHANGELOG.md?raw» sotto jsdom).
  > **⚠️ Fuori pista (riparazione, `test-author`)**: `OnboardingCoachmark.test.ts` (area dell'onboarding) monta
  > `DeferredAppPopups` per davvero: due mock inerti (lo store mai in attesa; il modulo del changelog con lo stesso stub di
  > `AboutTab.test.ts`), +11 righe, nessuna asserzione cambiata → **176/176**; `features/onboarding` **290/290**.
- Corsia, servizi: `whats-new` 52, `user-profile` 52, `registration` 151, `admin-bootstrap` 218, `email-verification` 127,
  `session-version` 56 → **656/656**; porta libera.
- Doc: sesto giro del `docs-writer` in corso. Slot chiesto (API `auth`, `whats-new`; E2E `whats-new`, `admin-users`;
  Vitest `core-unit`, `component-unit`, `onboarding-component-unit`): `work/slot_c54/slot.sh`.
- Coordinatore (17:04): slot in coda (tre esecuzioni pesanti); la riparazione di `OnboardingCoachmark.test.ts` accettata;
  `WhatsNewModal.test.ts` spostato da `core-unit` a `component-unit` (accanto a `ChangelogModal.test.ts`), prima dello slot.

### C54.3 — Slot ✅ (GO 17:10; 17:10–17:28; impronta `fb4d8d29975cb738`) e le due correzioni del `docs-writer`
- Il `docs-writer` (sesto giro) era a metà: messo in pausa sulle build (le avviate del server dello slot ricostruiscono
  `mkdocs_src/site`), lo slot partito dopo un controllo che nessun `mkdocs build` girasse.
- API `auth` **95**, `whats-new` **8**; E2E `whats-new` **6/6** (la spec nuova, prima osservazione: il rosso era per
  costruzione, senza corsia prima del codice), `admin-users` **10/10**; Vitest `component-unit` **180 file, 4 846**,
  `onboarding-component-unit` **16, 470**; `core-unit` **8 765 verdi e 1 rosso**: `htmlSink.gate.test.ts`. Impronta
  invariata; porta 6182 libera; lane restituita al coordinatore (H dopo).
- **Correzione 1 (il cancello è il rosso)**: `WhatsNewModal` faceva `{@html render(…)}` con `sanitizeHtml` dentro il
  helper; il cancello vuole `sanitizeHtml(…)` diretto nel template → `{@html sanitizeHtml(renderMarkdown(chapter.body))}`
  (stesso risultato). `htmlSink`, `htmlInterpolation` e `features/changelog` **278/278**; `core-unit` rifatto **213 file,
  8 766/8 766**; `front check` **0/0**; colori puliti.
- **Correzione 2 (rosso prima)**: una copia senza tag dà `v0.0.0-g<hash>` (`get_git_version`), che diventava la release
  `0.0.0`: gli account creati lì avrebbero visto tutto il changelog alla prima release vera. Rossi (`test-author`): tre righe
  di WN-001 (`v0.0.0-gabc1234`, `…-dirty`, `0.0.0`) osservate rosse («must be None: got '0.0.0'»). Cura: `release_of`
  dà None per una base 0.0.0. `test_whats_new_service.py` **55/55**, `test_whats_new_api.py` **8/8**.
- Doc del sesto giro (11 pagine, `docs-writer`): `user/settings/about.en.md` (sezione nuova `#whats-new`),
  `user/installation.en.md`, `admin/hosting_providers.en.md`, `developer/frontend/onboarding.md` (l'ordine e la sezione
  `#whats-new`), `state/app-state.md`, `api/index.md`, `database/users_access.md`, `architecture/settings.md` e
  `test-walkthrough/front-overview.md` (l'interruttore nascosto, solo qui), `frontend/index.md`, `access_control.md`.
  Le pagine non inglesi linkano `about.md#changelog-modal` (l'ancora nuova esiste solo in inglese finché non si traduce).
  Debito di traduzione: la sezione nuova di `about` e il punto di `installation`. Build in corso.
- Doc chiusa (17:40): il `docs-writer` ha allineato `onboarding.md` (la release 0.0.0, il `sanitizeHtml` al punto del
  `{@html}`) e `users_access.md`; build strict e `check-links` (97 validi) puliti; nessun timbro; debito: `about` (sezione
  nuova) e `installation` (un punto).
- **C-54 (+ la nota di H): definizione di fatto ✅** (revisione di E, H — `DeferredAppPopups`, onboarding — e della squadra
  dei colori per `WhatsNewModal` dopo l'ingresso; galleria di G dopo). La riga C-54 dell'indice sta nella sezione C (non
  la mia): la chiude il coordinatore.

## C-54 — Entrato; X-R66 (dalla sezione di X) (17/10, 17:48–; base `7f2290ae0`)
- **Entrato**: dev `630c478cd` (`737268864`); CHANGELOG ✨ e C-54 chiusa nella sezione C (`7f2290ae0`). Revisioni: E
  (backend), H (`DeferredAppPopups`, il mock di `OnboardingCoachmark`), la squadra dei colori (`WhatsNewModal`); la foto
  della galleria nella coda di G.
- Dal coordinatore: «Next, from X's section (to lighten X's queue): X-R66, analysis first … X reviews.»

### X-R66 — Il limite delle sonde dei provider nella lingua dell'utente: analisi (17:55, sola lettura)
**Stato reale**
- Backend (MF-SI2, `api/v1/assets/providers.py:243-273`): oltre `LIBREFOLIO_PROBE_RATE_LIMIT` sonde al minuto per
  utente (30 di default) `POST /assets/provider/probe` risponde 429 `{error_code: "PROBE_RATE_LIMITED", retry_after:
  <secondi, ≥ 1>, message: "Too many provider probes: try again later"}` con `Retry-After`. Nulla da cambiare.
- «Test Configuration» (`components/assets/ProviderAssignmentSection.svelte:361`, `buildTestResults`):
  `extractErrorMessage(probe.error, …)` → la frase inglese del backend, e `summarizeProbeError(detail)` → «Error» nel
  riassunto di una riga.
- «Ask Provider» (`components/assets/AssetModal.svelte` `fetchAndCompareMetadata`, ~:976): ogni errore → il toast
  generico `common.errorOccurred`.
- C'è già il modello: `resolveProviderError.ts` traduce il `RATE_LIMITED` dei provider («In pausa … fino alle {time}»,
  `RATE_LIMITED_DAY` quando la fine è un altro giorno, `RATE_LIMITED_NO_TIME`), con `formatResumeTime`/`resumesToday`
  (ora locale, arrotondata al minuto per eccesso), testi entro i 60 caratteri del riassunto. Chiavi nella sorgente i18n
  `assets` (di X).
- Nessun test oggi fissa il 429 della sonda.

**Disegno**
1. Un aiuto in `resolveProviderError.ts`: `probeRateLimitMessage(error: unknown, t): string | null` — per una risposta
   429 con `detail.error_code === "PROBE_RATE_LIMITED"` la frase tradotta con l'ora locale di fine attesa (`retry_after`
   del dettaglio, altrimenti l'intestazione `Retry-After`); `null` per ogni altro errore. Chiavi nuove
   `providerErrors.PROBE_RATE_LIMITED` / `_DAY` / `_NO_TIME`, entro 60 caratteri con l'ora (la sonda conta sia «Test
   Configuration» sia «Ask Provider»: la frase parla di verifiche del provider, non di un solo bottone).
2. «Test Configuration»: il dettaglio e il riassunto di una riga diventano quella frase quando l'aiuto risponde; gli altri
   errori come oggi.
3. «Ask Provider»: il toast d'errore diventa quella frase per il 429; gli altri errori restano il generico.
4. Test (`test-author`, rossi prima): `resolveProviderError.test.ts` (l'aiuto: oggi/altro giorno, senza `retry_after`,
   dall'intestazione, gli altri errori → null, lunghezza ≤ 60 nelle 4 lingue), `ProviderAssignmentSection.test.ts`
   (dettaglio e riassunto tradotti), `AssetModal.test.ts` o `.providerLifecycle.test.ts` (il toast). Niente backend,
   niente E2E (tutto in Vitest: la corsia non serve).
5. Doc: dove MF-SI2 descrive il 429 (sviluppatore), una riga: la UI lo dice tradotto, con l'ora.
**Superfici**: file di X (`ProviderAssignmentSection.svelte`, `AssetModal.svelte` — area dei colori, nessuna classe
toccata —, `resolveProviderError.ts`, la sorgente i18n `assets`); X rivede. **Peso**: basso.
**Fuori**: `summarizeProbeError` dà riassunti inglesi anche per altri errori (timeout, HTTP…): non tradotti oggi, fuori.
- **Coordinatore (17:50): GO**, com'è disegnato, rossi prima; X rivede; riga 🐛 al checkpoint. La sorgente `assets` può
  essere aperta da X (X-R46): le chiavi vanno lì comunque, un'eventuale fusione la risolve il coordinatore all'ingresso
  (non posso guardare l'albero di X; su dev la sorgente è cambiata più volte oggi).

### XR66.1 — Rossi (17:51–, `test-author`) e codice pronto
- Rossi: `resolveProviderError.test.ts` (l'aiuto: oggi, mezzanotte → `_DAY`, solo l'intestazione, nessuna attesa →
  `_NO_TIME`, le chiavi mancanti → `_NO_TIME` poi il `message` del backend, ogni altro errore → null; la lunghezza ≤ 60
  sui cataloghi veri delle 4 lingue), `ProviderAssignmentSection.test.ts` (dettaglio e riassunto), il test di
  `AssetModal` che prova «Ask Provider» (il toast; la guardia: un altro errore resta generico).
- Codice pronto, non applicato: `work/xr66/apply_xr66.py` (`probeRateLimitMessage` con `probeRefusal`/`toSeconds`; le due
  chiamate) e `work/xr66/i18n_xr66.py` (3 chiavi `providerErrors.PROBE_RATE_LIMITED*`, frasi corte: «Too many checks: try
  again at {time}» e simili). Dry-run pulito.

### XR66.2 — Rossi osservati, codice applicato, verdi ✅ (17/10, 18:13–18:40)
- **Rossi osservati prima del codice** (`cd frontend && nice -n 10 node_modules/.bin/vitest run <file> --maxWorkers 2`):
  `resolveProviderError.test.ts` 36 rossi; `ProviderAssignmentSection.test.ts` PAS-RL1 rosso, le guardie PAS-RL2 verdi;
  `AssetModal.providerLifecycle.test.ts` 1 rosso su 56, il toast di «Ask Provider» («An error occurred»), le guardie verdi
  (`/tmp/libreFolio_xr66.log`).
- **Codice** (applicato con `apply_xr66.py` e `i18n_xr66.py`):
  - `resolveProviderError.ts`: `toSeconds`, `ProbeRefusal`, `probeRefusal(error)` e l'esportata
    `probeRateLimitMessage(error, t, now?)`. Un 429 con `detail.error_code === 'PROBE_RATE_LIMITED'` dà
    `providerErrors.PROBE_RATE_LIMITED` (o `_DAY`) con `{time: formatResumeTime(…)}`; l'attesa viene da `retry_after`,
    altrimenti dall'intestazione `retry-after`; senza attesa `_NO_TIME`, senza chiavi il `message` del backend; `null`
    per ogni altro errore;
  - `ProviderAssignmentSection.svelte` (`buildTestResults`): la riga d'errore di una sonda rifiutata ha quella frase come
    dettaglio e come riassunto (prima: la frase inglese del backend e «Error»);
  - `AssetModal.svelte` (`fetchAndCompareMetadata`, il catch): `probeRateLimitMessage(e, $t) ?? $t('common.errorOccurred')`;
  - sorgente i18n `assets`, 4 lingue: `providerErrors.PROBE_RATE_LIMITED`, `_DAY`, `_NO_TIME`.
- **Verdi**:
  - i 3 file: 189/189 (`/tmp/libreFolio_xr66_green.log`);
  - tutta la cartella `components/assets`: 38 file, 1 629 test (`/tmp/libreFolio_xr66_assets.log`);
  - `front-utility core-unit` dal runner (corsia 6182): 213 file, 8 880 test (`/tmp/libreFolio_xr66_core.log`);
  - `front check` 0 errori e 0 avvisi; i18n strict 5 062 chiavi; `theme-roles --check` pulito; Prettier senza cambi.
- **Doc**:
  - `developer/backend/assets/architecture.md` (la sezione della sonda, dopo il 429): una frase su cosa dice la UI;
  - `admin/configuration.en.md:58`, la riga `LIBREFOLIO_PROBE_RATE_LIMIT`: «**Ask Provider** counts too» e «past it,
    the form tells the user when to try again». Nessun timbro: la riga manca ancora nelle traduzioni (debito di MF-SI2,
    che resta visibile);
  - `mkdocs build` strict pulito, `check-links` 97 validi (`/tmp/libreFolio_xr66_mkdocs2.log`, `…_links2.log`).
- **Non eseguiti**: nessun E2E e nessun backend (non toccato). `component-unit` dal runner non lanciato: i due file del lotto
  che ci stanno sono nella cartella `assets`, passata intera.
- **Previsione dei conflitti** con dev `870d519bd` (29 commit avanti; i 7 dopo `0cf8eb4d5`, X-R75, non toccano questi file):
  - 3 file in comune: `ProviderAssignmentSection.svelte` e il suo test (C-97c-3), `architecture.md` (Z-32 (c));
  - la fusione a tre vie simulata in `/tmp` (`git merge-file`) è pulita, e le modifiche sono indipendenti: dev cambia il
    formato del prezzo nel ramo riuscito (`formatPrice`), io aggiungo un ritorno anticipato per la sonda rifiutata; i due
    `describe` nuovi del test hanno aiuti locali; la sezione nuova di Z-32 sta alla riga 285 della doc, la mia frase
    alla 615;
  - la sorgente i18n `assets`: su dev nessun cambio dalla mia base; l'albero di X non lo posso vedere.
- **Note**:
  - la prova della lunghezza (≤ 60 caratteri con l'ora) gira su en-GB, en-US, it, fr, es: fr-CA, es-US ed es-MX restano
    fuori perché i testi X8 che ci sono già superano i 60;
  - restano inglesi gli altri riassunti di `summarizeProbeError` (timeout, HTTP…): fuori, come da analisi.
- **⚠️ Fuori pista**: la riga dell'admin (`admin/configuration`) non era nel disegno. La sonda conta anche «Ask Provider»
  (`AssetModal.svelte:939` chiama lo stesso endpoint), e il messaggio nuovo lo dice: è doc direttamente collegata,
  corretta con una riga e segnalata al coordinatore.
- **X-R66: definizione di fatto ✅** (revisione di X dopo l'ingresso). La riga X-R66 dell'indice sta nella sezione di X: la
  chiude il coordinatore.
- **Indice, sezione A** (pulizia, 17/10): chiuse con ✅ due righe già fatte ma mai registrate, A-3 (A4, `3ac4114d5`) e la
  «Nota per A8» (A8, `66873b0c9`), verificate nel codice. Fusione simulata con dev `870d519bd` (8 commit sull'indice):
  pulita.

## X-R66 — Entrato; lotto A-11 + A-16 + A-40 + A-26 (17/10, 18:37–; base `c5b9cca75`)
- **Entrato**: dev `e50c23919` (`ed5ad328a`); CHANGELOG 🐛 e X-R66 chiusa (`c5b9cca75`), la riga di `admin/configuration`
  tenuta. Revisione di X dopo l'ingresso. Worktree portato avanti: HEAD `c5b9cca75` = dev, albero pulito.
- Dal coordinatore: «A-11 + A-16 + A-40 + A-26 as one lot: GO, reds first, with one API slot. A-11 … first: it's an
  availability bug on the login path. CHANGELOG 🐛 lines for A-11 and A-16.»

### Lotto A-11/A-16/A-40/A-26 — stato reale e disegno (18:40, sola lettura)
**A-11 · Un tema salvato che l'app non conosce blocca l'accesso**
- Verificato nel codice: `settings_service.get_user_settings()` e `update_user_settings()` costruiscono
  `UserSettingsRead(theme=<valore salvato>)`, e `theme` è un `Literal["light", "dark", "auto"]`: un altro valore solleva
  `ValidationError` → 500. Chiamanti: `POST /auth/login` (dopo il commit del login e il cookie: l'utente non entra),
  `POST /auth/setup`, `GET /settings/user` (`get_or_create_user_settings`), `PUT /settings/user` (500 **dopo** il commit).
- Da dove viene un valore così: la colonna `VARCHAR(20)` senza CHECK; una riga scritta a mano; un `default_theme` globale
  scritto a mano, che `get_or_create_user_settings`, `update_user_settings` e il benvenuto di `onboarding_service` copiano
  nelle righe nuove; un ritorno a una versione vecchia dopo un tema nuovo. E lo sa già: `email/flows.py:96`
  («a settings row that no longer validates (an old theme, say) never stops an email»).
- **Cura** (un punto solo, in `settings_service`): un aiuto che dà il tema da mostrare. Il valore salvato se lo schema lo
  conosce (l'insieme letto da `UserSettingsRead`, una fonte sola); altrimenti il `default_theme` dell'istanza se è un tema
  noto, altrimenti `auto`; un avviso nel log (`user_id`, il valore salvato tagliato a 20 caratteri, quello mostrato).
  La lettura non scrive: la riga tiene il suo valore (una versione che lo conosce lo mostra di nuovo); un `PUT` senza
  `theme` lo lascia, uno con `theme` lo sostituisce. Le scritture dei semi restano come sono (la lettura le copre).
- Test (`test-author`): una classe nuova in `test_settings_api.py`, **in-process** (il router di auth e quello delle
  impostazioni su un motore privato sotto `tmp_path`, come `private_sign_in` di `test_auth_api.py`): login 200, `GET` e
  `PUT /settings/user` 200, il tema mostrato secondo la regola (anche con un `default_theme` sconosciuto), la riga intatta,
  l'avviso nel log. Rossi osservabili senza server.

**A-16 · L'unico admin che elimina il proprio account riceve 400 senza `error_code`**
- Verificato: `DELETE /auth/users/me` → `400 "Cannot delete account: you are the only administrator"`; il frontend
  (`accountErrors.ts`) mostra la frase inglese. Esiste già `LAST_ADMIN` (409, `PATCH /users/{id}`), con un testo
  «né disattivare né declassare» che non va bene per un'eliminazione; su un'eliminazione `LAST_ADMIN` può venire solo
  dall'eliminazione di sé (quella di un altro admin risponde `DEMOTE_FIRST`).
- **Cura**: stato **400 invariato**, `detail = {error_code: "LAST_ADMIN", message: "Cannot delete account: you are the
  last active administrator"}` (la frase vecchia diceva «only», ma la regola conta gli admin **attivi**, ACCDEL-003).
  Frontend: `describeAccountError(e, 'delete')` con `LAST_ADMIN` → la chiave nuova
  `settings.usersTab.errors.LAST_ADMIN_DELETION` (4 lingue, con le parole dei bottoni: «Make administrator»…); senza
  `'delete'` resta `…LAST_ADMIN`.
- I test che riconoscono la frase: `SOLE_ADMIN_DELETE_DETAIL` in 6 file (`test_broker_access_api.py`, da cui lo importa
  `test_account_deletion_api.py`, e le pulizie di `test_http_compression_api`, `test_portfolio_wac`, `test_assets_provider`,
  `test_pac_planner_tool_api`, `test_portfolio_api`, nel caso dell'utente di test che resta l'unico admin): la costante
  diventa il dizionario nuovo, una riga per file, il confronto resta. ACCDEL-002/003 diventano i rossi.
- Frontend: `accountErrors.test.ts`, `AccountDeletionDialog.test.ts` (modo self: il testo tradotto, non la frase),
  `ProfileTab.test.ts` (il rifiuto con la forma vera).
- **Fuori, da registrare** (A-52): la guardia legge il conteggio degli admin prima del lock di scrittura (classe A-51):
  due ultimi admin che si eliminano nello stesso istante passerebbero entrambi. Il percorso dell'admin
  (`DELETE /users/{id}`) usa già `begin_writes`.

**A-40 · `user activate` sull'admin in attesa avvisa del limite**
- Verificato: `cmd_set_user_active` avvisa per ogni account inattivo a istanza piena, salvo quello che aspetta la verifica
  dell'email (`holds_place`); l'admin iniziale in attesa è già contato da `user_usage` (`pending_admin_filter`). L'API
  non ha il difetto (risponde 409 `PENDING_SETUP` prima del limite).
- **Cura**: nessun avviso anche quando `registration_service.is_pending_admin(session, user)` (lo stesso filtro del
  conteggio). Test: IMG-030f in `test_dev_cli_image.py` (PURE), accanto a IMG-030c.

**A-26 · Il confronto «modelli = migrazione» di 005 non vede un indice su espressione non unico**
- **Cura** (solo test): in `test_migration_005_accounts.py`, la chiave `indexes (name, columns, unique)` di `_shape` da
  `_index_list` (origine `'c'`) invece che dall'ispettore di SQLAlchemy, che salta gli indici su espressione. Rosso: un
  meta-test di `_shape` su copie di `fresh_head` (un indice su espressione non unico da una parte sola, o con due nomi →
  forme diverse); guardia: due copie uguali → forme uguali; il contratto 3 resta verde.
- Lo stesso punto cieco è in `test_migration_010_reported_currency.py` (di Z): lo segnalo soltanto.

**Corsia**: tutti i rossi si osservano senza server (in-process, PURE, Vitest). Lo slot API (uno) a fine lotto:
`api settings`, `api account-deletion`, `api auth`. Doc (`docs-writer`): sviluppatore (impostazioni, controllo d'accesso,
componenti delle impostazioni), `admin/cli_tools.en.md` (A-40, solo EN: le traduzioni sono già indietro, A-10).

### A52.1 — Rossi (18:45–19:16, due `test-author` in parallelo, file distinti) ✅
- **Backend** (agente `f24a8ad6`; ripetuti da me 19:14–19:16 con `/tmp/libreFolio_a8a_inproc/run.sh`, nessun server):
  - A-11, `test_settings_api.py` classe `TestStoredThemeUnknownToTheApp` (SET-A11-01…07, in-process su un file privato,
    i router veri di auth e impostazioni, `get_async_engine` come trappola): **7 rossi** (`ValidationError` di
    `UserSettingsRead`, `literal_error`, al login, al GET e al PUT), **5 guardie verdi** (01, 05, 06×3);
  - A-16, `test_account_deletion_api.py` ACCDEL-002/003 e la costante `SOLE_ADMIN_DELETE_DETAIL` (una riga in 6 file):
    **2 rossi** sul controllo `error_code` («its detail is 'Cannot delete account: you are the only administrator'»);
  - A-40, `test_dev_cli_image.py` IMG-030f: **1 rosso** («⚠️ The instance is at its limit … reactivates the account
    anyway»), 7 verdi (IMG-030…030e, la guardia 030c compresa);
  - A-26, `test_migration_005_accounts.py` MIG005-A26-01/02 (non unico e unico): **3 rossi** (forme uguali), la guardia
    A26-03 verde.
- **Frontend** (agente `0291b358`; ripetuto da me): `accountErrors.test.ts` AERR-15/16/17 rossi, AERR-18/19 guardie;
  `AccountDeletionDialog.test.ts` ADEL-28 ×4 lingue rossi (chiave mancante; oggi il dialogo mostra il testo di
  `LAST_ADMIN`, «né disattivare né declassare»), ADEL-29 ×4 guardie; `ProfileTab.test.ts` sulla forma nuova (verde prima e
  dopo). **7 rossi, 193 verdi** (`/tmp/libreFolio_a52_front_red.log`).
- **Note dell'agente**: il testo nuovo senza `''` ICU (il test confronta il valore grezzo del catalogo); diverso da quello
  di `LAST_ADMIN` in ogni lingua. Dopo la cura il contratto 3 di 005 confronta per nome anche gli indici creati: da
  verificare verde sul file intero.

### A52.2 — Codice applicato e verdi locali ✅ (19:16–19:30)
- **Codice** (`work/a52/apply_a52.py`, `work/a52/i18n_a52.py`):
  - A-11, `services/accounts/settings_service.py`: `KNOWN_THEMES` (letto dal `Literal` di `UserSettingsRead.theme`),
    `FALLBACK_THEME = "auto"`, `_shown_theme()` (il tema salvato se noto, altrimenti `default_theme` se noto, altrimenti
    `auto`; un WARNING con `user_id`, `stored` tagliato a 20, `shown`) e `_settings_read()`, usato da `get_user_settings()`
    e da `update_user_settings()`; la lettura non scrive;
  - A-16, `api/v1/auth.py` `delete_own_account`: 400 con `{error_code: "LAST_ADMIN", message: "Cannot delete account: you
    are the last active administrator"}`; `accountErrors.ts`: `LAST_ADMIN` con `'delete'` → la chiave nuova
    `settings.usersTab.errors.LAST_ADMIN_DELETION` (4 lingue, sorgente `settings`), il commento falso riscritto;
  - A-40, `scripts/user_cli.py` `cmd_set_user_active`: nessun avviso anche per `registration_service.is_pending_admin`;
  - A-26, `test_migration_005_accounts.py` `_shape`: la chiave `indexes (name, columns, unique)` da `_index_list`
    (origine `c`), la docstring aggiornata.
- **Verdi** (in-process, nessun server): SET-A11 12/12; ACCDEL-002/003 2/2; `TestUserLimitFromTheCommandLine` 8/8;
  `test_migration_005_accounts.py` intero 29/29 (il contratto 3 resta verde confrontando per nome anche gli indici
  creati); `test_dev_cli_image.py` intero 95/95. Vitest dei 3 file 200/200. `ruff` pulito su 13 file, `black` pulito su
  12 (`test_portfolio_api.py` non lo è già a HEAD, 38 righe: tocco solo la costante); Prettier pulito; i18n strict 5 064.
- **⚠️ Fuori pista**: `front check` rosso su `components/fx/FxPairAddModal.svelte:327` (`queries: {replace: true}`, X-R75
  entrata con l'avanzamento): il client generato (ignorato da git) era vecchio. `dev.py api sync` → nessun file tracciato
  cambiato → `front check` 0 errori e 0 avvisi.
- Doc: affidate al `docs-writer` (`3a36f6e7`), solo EN, nessun timbro.
- **Unità leggere della corsia** (19:25–19:36, `work/a8a/reds.sh g52`, nessun server): `services settings` 23/23;
  `front-utility core-unit` 214 file / 8 912; `front-utility component-unit` **rc 1**: 4 785 verdi, 113 saltati, 3 file
  rossi per «Hook timed out in 60000ms» nel `beforeAll` che importa il componente — `changelog/WhatsNewModal.test.ts`
  (C-54), `backup/RestoreCard.test.ts` e `backup/RestoreReportModal.test.ts` (B), nessuno toccato dal lotto.
  - **Triage** (skill `test-triage`): nessuna asserzione eseguita (§1 non applicabile); il tempo dell'import nell'esecuzione
    intera 1 895 s cumulati, il carico salito da 46 a **124** (media a 5 minuti, 19:37: le corse pesanti di altre
    sessioni). I tre file da soli (19:39, carico a 1 minuto < 50): **113/113 in 12,8 s, import 0,4 s** — esattamente i 113
    saltati. **Verdetto: ambiente** (macchina satura oltre il cancello; il mio `reds.sh` controlla il carico a 1 minuto
    solo alla partenza). Rimedio: `component-unit` intera di nuovo dietro il cancello a 5 minuti, dopo lo slot API.

### A52.3 — Doc e indice ✅ (19:20–19:45)
- **Doc** (`docs-writer` `3a36f6e7`, solo EN, nessun timbro): `developer/architecture/settings.md` (paragrafo «A stored
  theme the app does not know», A-11); `developer/architecture/access_control.md` («Superusers…»: il 400 `LAST_ADMIN`;
  la tabella «The User Limit»: `user activate` senza avviso anche per l'admin in attesa, A-40);
  `developer/architecture/users_and_brokers.md` («Deleting an Account»); `developer/frontend/components/features/settings.md`
  (tabella «Account Errors»: la riga `LAST_ADMIN` su un'eliminazione, la riga della frase senza codice ora un ripiego
  senza esempio; l'esito di `AccountDeletionDialog`; i test AERR-15…19 e ADEL-28/29); `admin/cli_tools.en.md` (📏 e 🏁);
  `admin/users.en.md` («Waiting for Its Setup Link»). Verificato da me nel diff.
- **⚠️ Fuori pista**: il `docs-writer` segnala `admin/configuration.en.md` («When the Instance Is Full»: «`user activate`
  print[s] a warning») falso per chi tiene già il posto — già per la verifica dell'email, ora anche per l'admin in attesa:
  corretto da me con una frase (stessa materia di A-40). E `developer/api/curl-testing.md` (~95–99): una rotta che non
  esiste (`PATCH /auth/users/me/preferences`) → **A-53** nell'indice, non toccata.
- `mkdocs build` strict pulito, `check-links` 97 validi (`/tmp/libreFolio_a52_mkdocs.log`, `…_links.log`).
- **Indice** (la mia sezione): ✅ A-11, A-16, A-26, A-40; nuove **A-52** (l'eliminazione di sé conta gli admin attivi prima
  del lock di scrittura, classe A-51) e **A-53**; ad A-10 una nota: in EN cambiano ancora `admin/cli_tools` e
  `admin/configuration` (traduzioni indietro, nessun timbro).

### A52.4 — Slot API (GO del coordinatore, 19:28) ✅ (19:43–19:54)
- `work/slot_a52/slot.sh c5b9cca75 all`, dietro il cancello del carico a 5 minuti (atteso dalle 19:43 alle 19:46): `api
  settings` **110/110** (le classi in-process comprese), `api account-deletion` **9/9**, `api auth` **95/95**;
  `front-utility core-unit` **214 file / 8 912**; `front-utility component-unit` **181 file / 4 898** (i tre file del
  timeout delle 19:36 verdi: verdetto «ambiente» confermato). Impronta dell'albero invariata (`0fdc3b5744821d76`),
  porta 6182 libera.
- **Lotto A-11/A-16/A-40/A-26: definizione di fatto ✅** — rossi osservati prima del codice, verdi locali e di corsia, doc
  EN con build strict e link, indice aggiornato. Non eseguiti: nessun E2E (il lotto non ne tocca), `all-backend`.

## Lotto A-11/A-16/A-40/A-26 — Entrato nel ramo; note di E e di H (17/10, 19:55–)
- **Checkpoint del coordinatore** (6 commit, 30 file): `3e12b09ae` (A-11), `16164411d` (A-16), `87356c8c5` (A-40),
  `f8503b48e` (A-26), `c64d8192b` (doc), `a1b826e42` (journal). HEAD `a1b826e42`, albero pulito.
- **Revisione di E di A-51: OK**, con tre note → indice, sezione A: **A-54** (la `refresh` di una riga cancellata nella
  finestra → 500, quattro punti), **A-55** (la DELETE rilegge sotto il lock solo l'admin in attesa), **A-56** (il limite
  contato prima del lock: la riattivazione dal PATCH e, trovato da me, `create_invite`; la registrazione è già sicura).
  Proposto al coordinatore un lotto «decidere sotto il lock»: A-52 + A-54 + A-55 + A-56 + A-53; in attesa del GO.
- **Da H-43** (dev `a6adb0066`, la corsia gestita), due righe nell'indice: **A-57** (LGM-E-01/03 di
  `legal-and-managed.spec.ts` leggono il profilo della corsia; in 1.3, prima della fase 2 di H-43; dopo il lotto in corso)
  e **A-58** (la metà UX di H-53, dopo la 1.3: cosa vede l'admin quando `connect-src 'self'` blocca la verifica
  dell'indirizzo).

## Lotto «decidere sotto il lock»: A-52 + A-53 + A-54 + A-55 + A-56 (17/10, 20:00–; base `fe42c9a2f`)
- **Entrato** il lotto A-11/A-16/A-40/A-26: dev `250031cd1`, CHANGELOG 🐛 ×2 `d1b2b67f6`; il journal (`72858ed23`) a
  `fe42c9a2f`. Worktree avanzato a `fe42c9a2f`, pulito. Controlli combinati del coordinatore verdi.
- **Coordinatore: GO**, «as you scoped it»; rossi prima, in-process, con la finestra di A-51; uno slot API
  (`users-admin`, `account-deletion`, `registration`). **Il 404 resta la stringa nuda** di `_user_or_404` (una forma
  sola, nessun rimescolamento di altre suite a fine rilascio). Poi A-57.

### Contratto (20:05, sola lettura)
- **Un aiuto solo**, `user_service.refreshed_under_lock(session, user) -> bool`: `begin_writes(session, User)`, poi un
  SELECT dell'id; se la riga non c'è più → rollback, `False`; altrimenti `session.refresh(user)`, `True`. Oggi la
  `refresh` di una riga cancellata nella finestra solleva `InvalidRequestError` → 500.
- **A-54** (la riga sparita): `update_user_status` lo usa e risponde il nuovo esito `"NOT_FOUND"` → il PATCH alza il 404
  di `_user_or_404` (stessa stringa, da un aiuto `_user_not_found()`); `set_user_active` e `set_user_admin` (CLI) → `(False,
  "User '<username>' not found")`, il messaggio del loro primo controllo.
- **A-55** (DELETE di un altro account): dopo `SELF_DELETION` e la protezione, **sempre** l'aiuto (404 se sparita), poi
  `is_superuser` e `is_pending_admin` letti sotto il lock → 409 `DEMOTE_FIRST` per un admin che non aspetta. Un ramo solo
  al posto dei due di A-51.
- **A-52** (DELETE di sé): l'aiuto su `current_user` (404 se sparito), poi `is_superuser` e `count_active_superusers` sotto
  il lock → 400 `LAST_ADMIN` con rollback.
- **A-56** (il limite): nel PATCH, la riattivazione prende il lock (`begin_writes`) **prima** di contare `user_usage` e di
  leggere `holds_place`; rifiuto → rollback → 409 `USER_LIMIT_REACHED`; poi `update_user_status` (il lock è già preso:
  `begin_writes` non cambia nulla, la `refresh` è sotto lo stesso lock). In `create_invite`, con `enforce_limit`,
  `begin_writes(session, AccountToken)` prima del conteggio. La registrazione e la verifica dell'email (E) sono già sicure:
  ricontano dopo la loro scrittura.
- **A-53**: `developer/api/curl-testing.md` (~95–99), l'esempio delle preferenze → `PUT /api/v1/settings/user` con i suoi
  campi veri (`docs-writer`).
- **Rossi** (`test-author`, in-process, la finestra «prima della prima scrittura» di `_rival_before_the_first_write`,
  `test_admin_bootstrap.py`): un rivale su un'altra connessione fa il commit dopo le letture del codice e prima della sua
  prima scrittura; oggi decide su letture vecchie, dopo la cura la prima scrittura è il lock e le decisioni vedono il
  rivale. Casi: PATCH su un account cancellato nella finestra (oggi 500), DELETE ramo in attesa e ramo normale (oggi 500 e
  204), DELETE di un account promosso nella finestra (oggi 204), riattivazione e invito a limite − 1 con un rivale che
  prende l'ultimo posto (oggi oltre il limite), due ultimi admin che si eliminano insieme (oggi nessun admin), CLI
  `set_user_active`/`set_user_admin` su un account cancellato nella finestra (oggi eccezione). Guardie: senza rivale tutto
  come prima.
- **Doc** (`docs-writer`): `developer/architecture/access_control.md` (le decisioni sotto il lock, la tabella delle rotte),
  A-53. **CHANGELOG** 🐛 proposto: una riga sulle azioni contemporanee di due admin.

### LOCK.1 — Rossi (20:05–20:45, due `test-author` in parallelo, file distinti)
- **Self-deletion e CLI** (agente `4303839a`; ripetuti da me 20:40): `test_account_deletion_api.py` classe
  `TestDecidedUnderTheWriteLock` — ACCDEL-LOCK-01 (gli ultimi due admin: oggi A cancellato dopo aver contato B, nessun
  admin), ACCDEL-LOCK-03 ×2 (l'account cancellato nella finestra da un admin o dalla sua seconda scheda: oggi «Account
  deleted successfully» con DELETE che toccano 0 righe) **3 rossi**, ACCDEL-LOCK-02 guardia verde;
  `test_admin_bootstrap.py` LOCK-CLI-01 ×4 (deactivate, activate, promote, demote su un account cancellato nella finestra:
  oggi `InvalidRequestError`) **4 rossi**, LOCK-CLI-02 ×4 guardie verdi. Le due pagine di test ora importano
  `_issuer_engine` e `_rival_before_the_first_write` da `test_admin_bootstrap.py`.
- **Users admin API** (agente `1d3c43d1`): `test_users_admin_api.py` classe `TestDecidedUnderTheWriteLock`, UADM-LOCK-01
  ×4 (PATCH, anche l'annullamento del setup), -02 ×2 (DELETE: in attesa e normale), -03 ×2 (promosso nella finestra:
  oggi 204, account e broker cancellati), -04 ×2 e -05 ×2 (limite: oggi 200/201 e uso (4, 3)) **12 rossi**; -06…-09
  **15 guardie verdi**. Il resto del file invariato (i 34 errori delle classi di corsia sono quelli di sempre senza server).
- **⚠️ Fuori pista (dentro A-54)**: l'agente trova lo stesso difetto in tre altre rotte su un account cancellato nella
  finestra: `POST /users/{id}/password-reset-link` (`IntegrityError`, 500), `…/sessions/revoke` (`NoResultFound`, 500),
  `…/onboarding/reset` (204 su un account che non c'è). Stessa cura (l'aiuto, poi il 404), due righe per rotta: prese nel
  lotto come parte di A-54 (UADM-LOCK-10…12 chiesti all'agente), da dire al coordinatore.
- Codice pronto, non applicato: `work/lock/apply_lock.py` (dry-run pulito): l'aiuto `refreshed_under_lock`, i tre usi nel
  servizio, `_user_not_found()`, il PATCH (il conteggio sotto il lock e `NOT_FOUND`), la DELETE (un ramo solo sotto il
  lock), le tre rotte, la DELETE di sé, `create_invite`. I tre servizi chiamati dalle tre rotte non aprono transazioni
  proprie (`reset_onboarding_progress` fa solo il commit finale).
- **Users admin, seconda passata** (lo stesso agente): UADM-LOCK-10 (link di reset: oggi `IntegrityError` sulla FK), -11
  (revoca delle sessioni: oggi `NoResultFound`), -12 ×2 (reset dell'onboarding, senza corpo e con un `flow`: oggi 204)
  **4 rossi**; guardie -13, -14, -15 ×2 verdi. Ripetuti da me (20:52): la classe **16 rossi**, ognuno sull'asserzione del
  contratto, **19 guardie verdi**. L'istantanea del «nulla è cambiato» ora include anche `user_settings` e le due tabelle
  dell'onboarding (più severa anche per LOCK-01…09, esiti invariati).

### LOCK.2 — Codice applicato e verdi locali ✅ (20:52–20:56)
- **Codice** (`work/lock/apply_lock.py`): `user_service.refreshed_under_lock()` (il lock, un SELECT dell'id, rollback e
  `False` se la riga non c'è più, altrimenti la `refresh`); `update_user_status` → esito `"NOT_FOUND"`; `set_user_active`
  e `set_user_admin` → `(False, "User '<username>' not found")`; `users.py`: `_user_not_found()` (il 404 di
  `_user_or_404`), il PATCH (il conteggio della riattivazione dopo `begin_writes`, `NOT_FOUND` → 404), la DELETE (un ramo
  solo sotto il lock: 404, poi `DEMOTE_FIRST` per un admin che non aspetta), le tre rotte (link di reset, revoca delle
  sessioni, reset dell'onboarding) con l'aiuto prima di scrivere; `auth.py` la DELETE di sé sotto il lock (404, poi il 400
  `LAST_ADMIN` con rollback); `registration_service.create_invite` con `begin_writes(session, AccountToken)` prima del
  conteggio.
- **⚠️ Fuori pista**: `ruff` C901 su `update_user_status` (11 > 10, il ramo del 404). La regola del progetto
  (`pyproject.toml`) ammette il `noqa` solo per i compattatori piatti: estratta la parte di `is_active` in
  `_apply_active_flag()` (stesse chiamate, stesso ordine, stesso `changed`; `work/lock/apply_lock_c901.py`). `ruff` e
  `black` puliti sui 4 file.
- **Verdi** (in-process): `TestDecidedUnderTheWriteLock` di `test_users_admin_api.py` **35/35**; di
  `test_account_deletion_api.py` con ACCDEL-002/003 **6/6**; `test_admin_bootstrap.py` intero **226/226** (A51-007/008 e
  LOCK-CLI compresi). Corsia, senza server: `services user-profile` 52, `registration` 151, `email-verification-hooks` 32,
  `session-version` 56.

### LOCK.3 — Coordinatore e doc (20:56–21:15)
- **Coordinatore (20:56)**: GO per lo slot API dopo il `docs-writer`, dietro il cancello; l'estensione di A-54 alle tre
  rotte e l'estrazione di `_apply_active_flag` approvate; la riga del CHANGELOG approvata. Più: «E's C-54 note 1
  (`mark_seen` monotonic) … fold it into this lot if it fits before the slot». La nota non è nei file che posso leggere:
  il contenuto è nel nome e nel codice — `mark_seen` scrive la release in esecuzione ogni volta che è diversa, quindi la
  abbassa dopo un ritorno indietro o da un worker più vecchio durante un aggiornamento graduale, e decide sull'account
  caricato senza lock. Ci sta prima dello slot (servizio e prove in-process): rossi chiesti a un `test-author`
  (`ae87396f`), cura pronta (`work/lock/apply_c54_mono.py`: `refreshed_under_lock`, poi `release_of` e `_key` come in
  `pending_for`; tenuto → rollback, risposta la release salvata).
- **⚠️ Fuori pista**: un `git fetch` partito per sbaglio in un comando di sola lettura si è bloccato: fermato (non serviva,
  `dev_release2` è un ramo locale). Nessun effetto.
- **Doc** (`docs-writer` `3a36f6e7`): `developer/architecture/access_control.md` (il paragrafo «Decided under the write
  lock», `#decided-under-the-lock`, la sola regola; la tabella delle rotte; la tabella del limite; «Superusers»; il rifiuto
  4 di «Deleting an Account», falso dopo A-55), `developer/architecture/security.md` («A setup completed meanwhile»:
  il punto della DELETE era falso), `developer/api/curl-testing.md` (A-53: `GET`/`PUT /api/v1/settings/user`). Build
  strict e `check-links` (97) puliti; pagine solo EN, nessun debito di traduzione.

### LOCK.4 — C-54, la nota 1 di E: `mark_seen` monotòno ✅ (21:00–21:21)
- **Rossi** (`test-author` `ae87396f`; ripetuti da me 21:18): `test_whats_new_service.py` WN-MONO-01 ×3 (una release
  salvata più nuova: oggi scritta e risposta la più vecchia; anche 1.10.0 contro 1.9.2), -04 ×2 (un worker più nuovo
  scrive 1.4.0 nella finestra: oggi sovrascritto), -06 (l'account cancellato nella finestra: oggi `StaleDataError`)
  **6 rossi**; guardie -02 ×7, -03, -05 verdi. `test_whats_new_api.py` WNAPI-MONO-01 (204 e la riga intatta) e -03 (dopo
  il prossimo aggiornamento il capitolo già visto non torna) **2 rossi**, -02 guardia. L'aiuto `_mark_seen` dei test ora
  legge l'oggetto senza ricaricarlo (una cura che fa rollback lo lascia scaduto).
- **Cura** (`work/lock/apply_c54_mono.py`): `mark_seen` prende il lock e rilegge con `user_service.refreshed_under_lock`
  (import nella funzione: `user_service` importa questo modulo); una release salvata uguale o più nuova resta (rollback,
  risposta quella salvata); un valore che non nomina una release vale «niente visto», come in `pending_for`; l'account
  sparito → None. Doc: due frasi (`developer/frontend/onboarding.md`, `developer/architecture/database/users_access.md`).
- **Verdi**: `test_whats_new_service.py` intero **70/70**, `test_whats_new_api.py` intero **11/11** (in-process);
  `services whats-new` di corsia 70/70; `ruff`/`black` puliti; build strict e `check-links` (97) puliti.
- Lo slot aggiunge `api whats-new` (in-process, pochi secondi) alle tre unità approvate.

### LOCK.5 — Slot API (GO 20:56) e un rosso da riparare (21:20–21:30)
- `work/slot_lock/slot.sh fe42c9a2f api`: `api account-deletion` **13/13**, `api registration` **102/102**; `api
  users-admin` **166/167**: rosso A51-006 (`TestTheSetupCompletedWhileTheUsersTabActs::
  test_a_deletion_in_the_setups_window_asks_to_demote_first`). Lo script si è fermato dopo `registration`: `api
  whats-new` non è partito (da ripetere). Impronta dell'albero invariata, porta libera.
- **Triage** (skill `test-triage`): `sqlite3.OperationalError: database is locked` dentro il rivale
  (`_setup_completed_meanwhile`, l'UPDATE che consuma il link di setup). Il gancio `_setup_lands_after_the_first_read` fa
  atterrare il rivale dopo la PRIMA chiamata di `is_pending_admin` della rotta: con A-55 la DELETE la fa una volta sola,
  **sotto** il lock, e il rivale non può scrivere. **Verdetto: assunzione** — il test fissava l'ordine delle chiamate di
  prima; il comportamento che guarda (un setup completato nella finestra → `DEMOTE_FIRST`) è ancora il contratto, e
  UADM-LOCK-03 lo prova per la promozione. Riparazione chiesta al `test-author` `1d3c43d1`: il rivale prima della prima
  scrittura della rotta, come gli UADM-LOCK.
- **Riparazione** (`test-author` `1d3c43d1`): A51-006 ora fa atterrare il setup (`POST /auth/setup` di un altro worker)
  subito prima della prima scrittura della rotta, dopo la sua lettura dell'account ancora in attesa; stesso ID e stesso
  contratto (409 `DEMOTE_FIRST`, nulla cancellato); il gancio `_setup_lands_after_the_first_read` resta per A51-002/005
  (il PATCH legge ancora `is_pending_admin` prima del lock). In-process 44/44; prova contro una rotta vecchia (fuori dal
  repo): rosso `(204, '')`, il difetto.

### LOCK.6 — Slot API ripetuto sull'albero finale ✅ (21:31–21:34)
- `api users-admin` **167/167**, `api account-deletion` **13/13**, `api registration` **102/102**, `api whats-new`
  **11/11**. Impronta dell'albero invariata (`ab3428512adb3b0d`), porta 6182 libera. `ruff`/`black` puliti su tutti i file
  toccati.
- **Lotto «decidere sotto il lock» + C-54 monotòno: definizione di fatto ✅.** Non eseguiti: E2E (nessuno toccato),
  `all-backend`.

## Lotto «decidere sotto il lock» — Entrato; A-57 (17/10, 21:40–; base `98b0fc974`)
- **Entrato**: dev `119230f9f` (i miei `09ee732e2`, `9e67c0c85`, `089be17d7`, `f83f75ca6`); CHANGELOG 🐛 `98b0fc974` (il
  testo approvato). Controlli combinati del coordinatore verdi. Worktree avanzato a `98b0fc974`, pulito.
- Revisione di E del backend di C-54: nota 1 (`mark_seen` all'indietro) già nel checkpoint (LOCK.4); nota 2 (una
  pre-release vale la sua release: chi ha chiuso la finestra su `1.3.0-rc1` non rivede il capitolo `1.3.0`, anche se è
  cresciuto) → una frase in `developer/frontend/onboarding.md` dopo gli esempi di `release_of()`, **nel checkpoint di
  A-57** (coordinatore). Le note di E su C-54 sono chiuse dal coordinatore.
- Dal coordinatore, per dopo A-57: H prepara `LIBREFOLIO_CSP_ENFORCE` (spento di default; `connect-src` solo `'self'` e
  l'origine di `LIBREFOLIO_PUBLIC_URL`): la verifica dell'indirizzo (F3, A-58) leggerà «non verificabile» ogni altro
  indirizzo. Due cose per me, quando H manda la politica esatta: le parole per l'admin, e le attese di AUSR-E-07 su una
  corsia che la applica (prova apposta altre origini http).
- **Coordinatore: GO per l'analisi di A-57** (serve poi uno slot E2E).

### A-57 — LGM-E-01 e LGM-E-03 leggono il profilo della corsia: analisi (21:45, sola lettura)
**Stato reale**
- `frontend/e2e/layout/legal-and-managed.spec.ts` (lotto A9, mio): LGM-E-01 (senza sessione) e LGM-E-03 (con sessione)
  osservano la risposta della corsia attraverso lo stub con una patch vuota (`serveInstanceConfig(page, {})`) e prendono
  come prova «configurazione applicata» il link della donazione (`auth-donate-link`, `header-donate-link`), poi fissano
  `expectServed(… {profile: 'selfhosted', legal: LANE_LEGAL})`. Su una corsia gestita il link non compare mai: la prova
  scade, il test fallisce per costruzione (H-43, reperto F2). LGM-E-02/04/05 simulano il profilo o i link e girano su ogni
  corsia.
- Una corsia imposta solo `LIBREFOLIO_PROFILE`, `LIBREFOLIO_FRAME_PROTECTION`, `LIBREFOLIO_CSP_REPORT_ONLY`
  (`TEST_LANE_SETTABLE`): **nessuna corsia ha pagine legali**, gestita o no.
- Gli elementi disegnati solo «a server che ha detto gestito» (`managedConfirmed()`): uno solo, in
  `ForgotPasswordCard` (`forgot-ask-admin`, senza sessione). Con la sessione non ce n'è nessuno: ciò che un'istanza
  gestita toglie manca anche prima della risposta.
- `CLOUD_SMOKE_SPECS` (`scripts/test_runner/_frontend_utility.py`, di H) ne è fuori, col commento e la frase in
  `developer/test-walkthrough/front-utility.md:112`; la registrazione `legal-managed` dice «the lane self-hosted
  (LIBREFOLIO_PROFILE unset)» nel `prereq`.

**Disegno** (solo test)
1. Prima di caricare la pagina, il test legge il profilo della corsia: `GET /api/v1/system/instance` (pubblico) con
   `page.request`, `profile` ∈ {`selfhosted`, `managed`} e `legal`; poi la pagina lo rilegge attraverso lo stub, e
   `expectServed` vuole lo stesso.
2. **LGM-E-01**: self-hosted come oggi. Gestita: la prova è `forgot-ask-admin` (login → «password dimenticata» → la prova
   → «torna al login», stessa esecuzione dell'app, marcata); poi la scheda del login con `auth-legal-links` sotto, i link
   come dice il `legal` della corsia (nessuno), nessun `auth-donate-link` e nessun link alla pagina della donazione.
3. **LGM-E-03**: self-hosted come oggi. Gestita: senza un elemento solo-gestito con la sessione, la prova viene da uno stub
   dei soli `legal` (il profilo resta quello vero della corsia), come in LGM-E-04: la riga legale della barra laterale
   punta alla pagina dei termini dello stub = la risposta applicata; poi il contrasto sugli stessi percorsi (niente
   controllo degli aggiornamenti, nessun caffè in intestazione, aiuto e About, la condivisione resta).
4. Stessi ID; l'intestazione della spec («Covered») aggiornata; il `prereq` di `legal-managed` → «either profile».
5. La spec di nuovo in `CLOUD_SMOKE_SPECS` (lista, commento, frase della doc, eventuali conteggi «13») resta di H.
**Superfici**: la spec (mia); una riga del registro in `_frontend_utility.py` (condiviso con H: righe lontane da
`CLOUD_SMOKE_SPECS`); la frase rc in `onboarding.md`; l'indice (A-57 ✅, A-58 con il punto di AUSR-E-07).
**Prove** (slot E2E, ~10 min): (1) la spec di oggi su una corsia gestita → LGM-E-01/03 rossi, gli altri verdi; (2) la
spec nuova su una self-hosted → 5/5; (3) su una gestita → 5/5. La spec nuova scritta da `test-author` nella cartella di
sessione e copiata nell'albero dopo (1). Corsia: la mia (6182, `/tmp/librefolio-r13-a`), gestita con `--lane-setting
LIBREFOLIO_PROFILE=managed`. **Peso**: basso.

### A57.1 — GO, prova 1, poi STOP (17/10, 21:44–21:52); sospeso (19/10)
- **Coordinatore (21:44)**: GO «as designed (test only, same IDs)»; write OK sulla sola riga `prereq` di
  `legal-managed` in `scripts/test_runner/_frontend_utility.py` (W ha lo stesso file aperto, K3, un'altra regione);
  stessa cartella dati per le corse gestite; slot E2E (3 corse) GO; il ritorno in `CLOUD_SMOKE_SPECS` resta di H.
- **Prova 1** (`work/slot_a57/slot.sh 98b0fc974 red`, 21:44–21:51): la spec di oggi su una corsia gestita
  (`--lane-setting LIBREFOLIO_PROFILE=managed front-utility legal-managed`; il runner stampa `Test lane settings:
  LIBREFOLIO_PROFILE=managed`): **2 rossi, 3 verdi**. LGM-E-01 e LGM-E-03 cadono sulla prova di presenza del link della
  donazione (`auth-donate-link`, riga 189; `header-donate-link`, riga 239: «element(s) not found»), come previsto;
  LGM-E-02/04/05 verdi. Impronta dell'albero invariata, porta 6182 libera.
- **STOP del developer** (17/10, ~21:52), subito dopo la prova 1: nulla scritto dopo (né la spec nuova, né la riga
  `prereq`, né la frase rc in `onboarding.md`, né l'indice); nessun `test-author` avviato.
- **Ripartenza 19/10** (coordinatore; regole nuove: nessuna decisione di prodotto dai figli, ogni scelta diventa una
  domanda con opzioni e consiglio; implementazione solo dopo il via esplicito; niente carichi pesanti senza slot):
  **A-57 sospeso** finché il developer non finisce di leggere i lotti piccoli. In attesa con lui: la frase rc in
  `developer/frontend/onboarding.md` (nota 2 di E su C-54, legata al checkpoint di A-57). Il punto AUSR-E-07 di A-58 va
  nella contabilità dell'indice (fase 2).

## Ripartenza del 19/10 — Fase 2 (base `6578f1d75`)
- Coordinatore (11:12): base aggiornata a `6578f1d75` (il mio giornale in `52421559f`, poi il merge di `dev_release2`,
  `ede7adf75`); la frase sulle pre-release resta con A-57, sospesa. Fase 2: prima la contabilità, poi l'analisi N69.
- Regole nuove (19/10): nessuna decisione di prodotto da A, ogni scelta che cambia ciò che l'utente vede, i numeri o i
  dati diventa una domanda per il coordinatore, con le opzioni e un consiglio; implementazione solo dopo il via
  esplicito; niente carichi pesanti senza slot.

### F2.1 — Contabilità ✅ (19/10, 11:15–11:45)
- **Indice, sezione A**: ogni riga aperta confrontata con il codice e con i commit (solo letture e `grep`).
  - Chiuse con ✅, data e commit:
    - A-2 (A6d, `683b4ff5b`);
    - A-5, la parte di A (A3);
    - A-6 (A6c, `4bbc6fbf6`);
    - A-7, i punti di A;
    - A-8 (A5b, `2b0715532`);
    - A-9 (H, C-96, `901fa33f6`);
    - A-12 (A6b, `1577663c1`);
    - A-15 (H, `ef3f29f52`);
    - A-21 (A-21a, `5da71d037`);
    - A-39 in inglese (A-50, `6700a04b4`).
  - Nuova **A-21b**: il resto di A-21, che aspetta il developer. Un tempo prevedeva «la migrazione 010», che ora è di
    Z-32 (c).
  - Aggiornate con lo stato a `6578f1d75`: A-4, A-10, A-37, A-38, A-57, A-58.
    - A-4: 14 righe in 13 pagine.
    - A-10: le pagine dei lotti A8a–C-54.
    - A-37: anche `backup/instance.py` di B usa la classe.
    - A-38: il limite ora è descritto in `security.md`.
    - A-57: sospesa.
    - A-58: AUSR-E-07 e `LIBREFOLIO_CSP_ENFORCE`.
  - Una nota di contabilità in testa alla sezione. Risultato: 41 chiuse, 19 aperte.
- **Fuori dal dominio di A**, da dire al coordinatore:
  - black fallisce ancora su `scripts/coverage_analysis.py` e `test_portfolio_api.py`;
  - due punti di A-7 sono ancora veri: la prop `icon` di `PasswordInput` manca in `core-ui/atoms.md` (T), e
    `patterns/alembic.md` usa ancora il batch senza l'avvertenza.
- **Tabella dei lotti** (§8):
  - una colonna «Stato» con i commit d'ingresso;
  - una seconda tabella con gli 11 lotti nati dopo il piano;
  - una nota: le intestazioni «in corso» di §17 sono storiche.
  - Tutti i commit citati sono antenati di HEAD (`git merge-base --is-ancestor`).
- **⚠️ Fuori pista**: un giro di `git rev-list` per trovare l'ingresso di A4 era lento: fermato, perché non serviva (ho
  citato i commit dei lotti).

### F2.2 — Analisi N69: l'amministrazione, dalle prove del developer (19/10, sola lettura)
Fonte: `risposte-resoconto-20261019.md` del coordinatore, §6 «Cose nuove dalle tue prove», N69; la sua richiesta delle
11:08. Nessun file del repo toccato; skill `design-system` caricata (solo ruoli, contrasti, stato per i test). Ogni scelta
che cambia ciò che l'utente vede è nelle domande in fondo (D1–D11), con le opzioni e il mio consiglio.

| Punto | Cosa | File principali | Costo | Rischio principale |
|---|---|---|---|---|
| 1 | Un puntino sull'icona della connessione; nel pannello «N avvisi di sicurezza» → la lista | `ConnectionSecurityIndicator.svelte`, forse `Header.svelte` | piccolo–medio | la shell, la galleria di ogni pagina admin |
| 2 | Amministrazione solo per gli admin | `settingsTabs.ts` (una riga) | piccolo | due E2E e la doc con traduzioni |
| 3 | «Chi può iscriversi» anche nella scheda Utenti | `UsersTab.svelte`, `GlobalSettingsTab.svelte`, un modulo comune | medio | l'impostazione è condivisa dalla corsia |
| 4 | L'icona dell'utente dopo la freccia | `AdminUserRead`, `UserRow.svelte` | piccolo–medio | la decisione A-1 sui file |
| 5 | L'avviso del proxy spiegato; «Guida» su ogni controllo | `SecurityTab.svelte`, `schemas/security.py`; testi e ancore di H | medio | il contratto con H, le ancore non tradotte |

#### N69-1 · Il puntino degli avvisi di sicurezza sull'icona della connessione
**Stato reale**
- Il «1» che il developer ha visto è il badge della scheda Sicurezza, ripetuto sul gruppo Amministrazione:
  `settingsTabs.ts` (`badge: () => securityChecks.attentionCount`) e la somma del gruppo in
  `routes/(app)/settings/+page.svelte:58-79`. Conta errori e avvisi, non le info (`securityFindings.ts`, `attentionCount`).
- Lo stato è uno store di modulo (`security/securityChecks.svelte.ts`): una lettura di `GET /api/v1/security/checks` (solo
  admin, `api/v1/security.py`) per caricamento di pagina. Oggi la chiede solo la pagina Impostazioni (`prefetch`). La rotta
  valuta i controlli di `services/platform/config_audit.py` (file letti fuori dal loop) e i segreti dei plugin (una
  query): leggera.
- La riga della connessione è `components/layout/ConnectionSecurityIndicator.svelte`, nella barra verde
  (`Sidebar.svelte:280`). Mostra l'icona del livello (scudo in `text-lf-bar-success/warning/danger`). Il pannello contiene
  il motivo, l'avviso del cookie per gli admin e la guida, e si chiude da solo dopo 30 s (piano 48). Con la barra
  compatta, un clic allarga la barra e apre il pannello.
- Sul telefono la barra è fuori schermo. Il pulsante del menu (`Header.svelte:240-251`) ha già un puntino rosso quando la
  connessione è `insecure` (`mobile-menu-security-dot`: `bg-lf-danger ring-2 ring-lf-header`, piano 36): è il precedente
  di questo disegno.

**Disegno proposto**
- Per un admin con almeno un errore o un avviso, un puntino sull'angolo dell'icona della connessione, con la barra larga o
  compatta.
  - Rosso con almeno un errore, ambra con soli avvisi: `bg-lf-bar-danger` / `bg-lf-bar-warning`, con un anello del colore
    della barra che lo stacca dall'icona.
  - Sulla barra verde reggono 3:1, coppie già misurate dal cancello (`bar-danger`, `bar-warning` sulla barra e sul suo
    hover).
- Nel pannello, sotto il motivo, un pulsante «N avvisi di sicurezza» (plurale ICU) che chiude il pannello e porta a
  `/settings?tab=security`.
  - Testo `text-lf-bar-text`, bordo e icona nello stato, come l'avviso del cookie di oggi (`border-lf-bar-warning`).
  - Mai `text-lf-bar-danger` per un testo: sulla barra è misurato a 3:1, non a 4.5.
- Il colore da solo non basta (WCAG 1.4.1): il conteggio entra nel nome accessibile del pulsante della connessione, e nel
  `title` quando la barra è compatta. Per i test, `data-security-attention` con il numero e `data-security-severity`.
- Caricamento: l'indicatore chiama `securityChecks.ensureLoaded()` solo se l'utente è admin, cioè una richiesta in più per
  caricamento di pagina, solo per gli admin. La scheda e i badge leggono lo stesso store: dopo «Controlla di nuovo» il
  puntino segue.
- `components/layout` importa già da `features/` (`Sidebar.svelte`: `features/legal`, `features/onboarding`).

**File e costo**
- `ConnectionSecurityIndicator.svelte` e il suo test; `Header.svelte` se il puntino del menu si allarga (D2); 2–3 chiavi
  i18n nella sorgente `app` (`connectionSecurity.*`).
- Costo piccolo–medio.

**Rischi**
- File della shell: gli ultimi a toccarli sono T (i ruoli) e A9 (la nota legale). Tutti e due già sui ruoli: nessuna
  riga nella baseline del cricchetto.
- La galleria: la barra c'è in ogni scatto di un admin. Se la corsia della galleria ha avvisi, cambiano tutti (G).
- Sul profilo gestito, l'admin del cliente vedrebbe avvisi sulla configurazione che fa l'operatore (D1).

**Test**
- Vitest `ConnectionSecurityIndicator.test.ts`:
  - il puntino solo per un admin e solo con il conteggio maggiore di 0, la gravità via `data-*`;
  - nessuna richiesta per un non admin;
  - il pulsante e la sua destinazione, il nome accessibile, la barra compatta.
- E2E `layout/connection-security.spec.ts`:
  - admin: il puntino c'è se e solo se `GET /security/checks` della corsia ha errori o avvisi, letto prima (write-safe);
  - utente normale: mai.

#### N69-2 · La scheda Amministrazione solo per gli admin
**Stato reale**
- `settingsTabs.ts`: la voce `admin` (Impostazioni globali) è l'unica del gruppo senza `visible`. Un non admin vede quindi
  il gruppo Amministrazione con questa sola scheda, in sola lettura (`canEdit: false`, `settings-readonly-indicator`).
- Un gruppo senza membri visibili sparisce da solo (`settingsBar`). Un `?tab=admin` vecchio cade sulla prima scheda
  visibile (`+page.svelte:32-40`).
- Pochi rimandi a quella scheda:
  - l'unico link interno a `?tab=admin` è l'avviso della registrazione aperta, solo per gli admin
    (`openRegistrationNotice.svelte.ts:30,39`);
  - nessuna guida dell'onboarding punta lì.
- `GET /settings/global` resta leggibile da ogni utente con il login (A6d): lo leggono anche `PreferencesTab.svelte:72` e
  il bootstrap dell'app (`onboarding/appBootstrap.svelte.ts`). Il backend non cambia.

**Disegno**: `visible: (ctx) => ctx.isSuperuser` sulla voce `admin`. Il ramo in sola lettura di `GlobalSettingsTab`
(`canEdit`) non si raggiunge più dalla UI. Proposta: resta, per ora, e si toglie in un lotto di pulizia.

**File e costo**: `settingsTabs.ts`, una riga (mia). Costo piccolo.

**Test**
- `settingsTabs.test.ts` e `routes/(app)/settings/page.tabs.test.ts`.
- E2E `settings.spec.ts`: i due test «non-admin can view but not edit global settings» (:518) e «non-admin sees disabled
  toggles and inputs» (:691) diventano «un non admin non vede Amministrazione», più un `?tab=admin` che cade sul Profilo.

**Doc**
- `user/settings/index.en.md` (:5, :11, :24 «Not an administrator?»), `admin/settings.en.md:4` («every signed-in user can
  read them»).
- `developer/frontend/components/features/settings.md` (il titolo «GlobalSettingsTab (read by everyone, edited by
  administrators)»), `developer/architecture/settings.md` (la scheda no, l'API sì).
- Le prime due hanno IT/FR/ES: il debito di traduzione cresce (A-10).

**Rischi**: gli scatti della galleria di un non admin (G); i test E2E sistemati in A-12, da riscrivere.

#### N69-3 · «Chi può iscriversi» anche nella scheda Utenti
**Stato reale**
- Una fonte sola: l'impostazione globale `registration_mode` (`open`, `invite`, `disabled`), scritta da `PATCH
  /settings/global/bulk`.
- `LIBREFOLIO_REGISTRATION` la blocca: il PATCH risponde 409 `SETTING_LOCKED_BY_ENV`, e `GET /system/instance` porta
  `registration_locked`.
- In `GlobalSettingsTab.svelte`:
  - sta nella categoria «security» con `require_email_verification` di E (:63), una `SettingSelect` dietro il lucchetto
    della pagina (`settings-lock-toggle`);
  - con la variabile, sola lettura e il suggerimento `settings.lockedByEnv` (:86-99, :682-700);
  - dopo il salvataggio rilegge la configurazione pubblica (`instanceConfig.load({force: true})`, :289-291).
- La scheda Utenti legge già quella configurazione. Con `disabled` spegne «Invita» e dice perché (`users-invite-blocked`,
  `UsersTab.svelte:90-93, 245-249`).

**Disegno**
- Nella prima sezione della scheda Utenti, sotto il titolo e l'uso, accanto a «Invita»: «Chi può iscriversi» con le tre
  modalità e le stesse etichette (`settings.registrationModes.*`), bloccato e spiegato quando la variabile lo fissa.
- Una sola fonte anche nel codice: un modulo comune in `features/settings/`, usato da entrambe le schede, con le opzioni,
  «bloccato dalla variabile», il salvataggio e la rilettura della configurazione. Il controllo è la `SettingSelect` che
  c'è già.
- Come si modifica è la domanda D5.

**File e costo**
- `UsersTab.svelte`, `GlobalSettingsTab.svelte` (solo per usare il modulo comune), il modulo nuovo, 1–3 chiavi i18n,
  forse un dialogo di conferma (`ModalBase`).
- Costo medio.

**Rischi**
- `registration_mode` è un'impostazione condivisa da ogni test della corsia: la corsia gira `open` e nessuna E2E la
  cambia (`e2e/fixtures/instance-config.ts`). L'E2E nuova intercetta il PATCH nel suo contesto invece di scriverlo; in
  alternativa gira esclusiva e rimette il valore.
- Nella stessa sezione di `GlobalSettingsTab` c'è la logica di E (`verificationBlocked`).
- L'avviso della registrazione aperta (A7b) e il ritrovamento del browser nella scheda Sicurezza seguono la
  configurazione riletta.

**Test**
- Vitest `UsersTab.test.ts`:
  - mostra la modalità, salva con il PATCH e rilegge la configurazione;
  - bloccata dalla variabile; 409 `SETTING_LOCKED_BY_ENV`;
  - la conferma, se scelta (D5).
- `GlobalSettingsTab.test.ts`: comportamento invariato.
- E2E `settings/admin-users.spec.ts`, con lo stub.

**Doc**: `admin/users.en.md` (senza traduzioni) e `admin/settings.en.md` («Who Can Sign Up», `#registration`: il secondo
punto d'accesso).

#### N69-4 · L'icona dell'utente nella lista degli account
**Stato reale**
- «La freccia» è il `ChevronRight` del pulsante della riga (`UserRow.svelte:65-66`), seguito dal nome e dai badge.
- L'icona è `user_settings.avatar_url`, un'immagine caricata o un indirizzo (al massimo 500 caratteri).
  - `GET /users/search` la dà già (`schemas/users.py:22`, la condivisione dei broker).
  - `AdminUserRead` no (`GET /users` e la risposta del PATCH).
- L'app la disegna già in due modi:
  - `UserSearchSelect.svelte`: `LazyImage` con `?img_preview=48x48`, un cerchio di 24 px, e l'iniziale su
    `bg-lf-neutral` / `text-lf-muted` se manca (solo ruoli);
  - `BrokerSharingPanel.svelte`: lo stesso, ma con classi della palette ambra non ancora migrate.

**Disegno**
- Backend: `avatar_url` in `AdminUserRead`, cioè una query in più per la lista e una per la risposta del PATCH; poi
  `api sync`.
- Frontend:
  - `avatar_url` nel tipo `AdminAccount`;
  - un cerchio di 24 px dopo la freccia, come in `UserSearchSelect`, con l'iniziale se manca (D8).
- Proposta: un piccolo `UserAvatar.svelte`, solo ruoli, usato dalla riga. Le altre due copie si allineano dopo, con i
  loro proprietari.

**File e costo**
- `schemas/users.py`, `api/v1/users.py` (`list_accounts`, `_admin_user_read`), `user_service` (la mappa degli avatar),
  `users/types.ts`, `UserRow.svelte`, forse `components/ui/media/UserAvatar.svelte`.
- Costo piccolo–medio.

**Rischi**
- A-1, decisione aperta: oggi ogni utente con il login legge ogni file caricato. Se si restringe la lettura ai
  proprietari, gli avatar degli altri si rompono qui e nella condivisione dei broker: la decisione di A-1 deve tenerli
  leggibili.
- Con la CSP imposta (`LIBREFOLIO_CSP_ENFORCE` di H) un avatar su un altro sito può essere bloccato (`img-src`). Vale già
  per la condivisione.
- La terza copia, in `BrokerSharingPanel` (palette ambra), è del programma colori.

**Test**
- `test_users_admin_api.py`: `avatar_url` nella lista e nella risposta del PATCH, `null` senza.
- Vitest della riga: l'immagine con `?img_preview`, l'iniziale se manca, l'`alt`.
- La galleria della scheda Utenti (G).

#### N69-5 · L'avviso del proxy spiegato, e «Guida» su ogni controllo
**Stato reale**
- Il controllo è di H: `platform.client_address` in `services/platform/config_audit.py:133-148`.
  - `warning` «untrustedProxy»: un peer locale con header di inoltro di cui LibreFolio non si fida;
  - `info` «publicForwarding»: header di inoltro da peer pubblici;
  - altrimenti `ok`.
  - I testi sono `instance.checks.clientAddress.*` nella sorgente i18n `instance`, di H.
- La guida c'è: `admin/connection_checks.en.md`, «🧭 The Visitor's Address» `{: #client-address }` (:203). IT, FR ed ES
  non hanno ancora l'ancora (debito A-10, da A8a).
- La scheda Sicurezza (`security/SecurityTab.svelte`, mia, A8b):
  - elenca i ritrovamenti, con un link interno dove un'impostazione dell'app li risolve (`SERVER_ACTIONS` di
    `securityFindings.ts`), e piegati i controlli superati;
  - nessun link alla guida.
- Un controllo arriva come `{check_id, severity, i18n_key, detail}` (`schemas/security.py` e `api/v1/security.py`, di A):
  nessun percorso di guida.
- Il componente comune c'è già: `components/ui/DocsLink.svelte` (icona del libro, etichetta visibile, la lingua nell'URL
  `/mkdocs/<lang>/…`, `localizedFallbackPath`).

**Disegno (parte di A)**
- Su ogni riga, ritrovamenti e superati, un pulsante «Guida» (`DocsLink`, libro, etichetta visibile, nuova scheda) verso
  la pagina e l'ancora del controllo, nella lingua dell'utente. Il link interno di oggi resta dov'è.
- Due modi di sapere la guida di un controllo:
  - (a) dal backend: un campo `docs` (percorso con ancora, senza lingua) in `ConfigCheck` e in `SecurityCheckRead`.
    - H lo mette nei suoi controlli, A, B ed E nei propri.
    - Un test del backend controlla che ogni ancora esista nella pagina inglese.
    - Una fonte sola, accanto al controllo.
  - (b) dal frontend: una tabella `check_id → percorso` in `securityFindings.ts`, come `SERVER_ACTIONS`. È più veloce, ma
    un controllo nuovo di H resta senza pulsante finché qualcuno non la aggiorna.
  - Consiglio (a). Il contratto con H passa dal coordinatore: il nome del campo, il formato
    (`admin/connection_checks/#client-address`), chi lo scrive per i controlli di B ed E.
- Il ritrovamento del browser (la registrazione aperta) ha la sua guida in `admin/settings.md#registration`.
- I testi spiegati meglio e le ancore sono di H (stesso compito, N69): A fa solo l'interfaccia.

**File e costo**
- Di A: `schemas/security.py`, `api/v1/security.py`, `SecurityTab.svelte`, `securityFindings.ts`, una chiave i18n.
- Di H: `config_audit.py` e i suoi controlli, i testi, le ancore.
- Costo medio, insieme a H.

**Rischi**
- Le ancore mancanti nelle traduzioni (A-10): in un'altra lingua il link arriva in cima alla pagina tradotta finché non è
  tradotta (D11).
- I moduli dei controlli di B ed E.

**Test**
- Backend: ogni controllo ha `docs`, e l'ancora esiste in `mkdocs_src/docs/<pagina>.en.md`.
- Vitest `SecurityTab.test.ts`: un pulsante per riga, anche fra i superati, con la lingua nell'URL.
- E2E `settings/security-tab.spec.ts`: il pulsante c'è e punta alla guida, senza cliccarlo.

#### Domande (le opzioni e il mio consiglio)
- **D1** (punto 1) Sul profilo gestito il puntino c'è come sul self-hosted? (a) Sì, ovunque, e H dice quali controlli
  l'admin di un'istanza gestita non deve vedere, perché li sistema l'operatore; (b) mai sul profilo gestito.
  **Consiglio (a)**: niente codice «solo cloud», la scelta resta sui controlli (di H).
- **D2** (punto 1) Sul telefono la barra è nascosta: il puntino del pulsante del menu, oggi solo per la connessione
  insicura, vale anche per gli avvisi di sicurezza di un admin? (a) Sì, lo stesso puntino, rosso o ambra; (b) no.
  **Consiglio (a)**, altrimenti sul telefono resta nascosto come prima.
- **D3** (punto 1) Un puntino o un numero? (a) Il puntino, come chiesto, con il numero nel pannello e nel nome
  accessibile; (b) un piccolo numero come il badge della scheda. **Consiglio (a)**.
- **D4** (punto 2) Il non admin perde la vista dell'istanza: durata della sessione, iscrizioni, aggiornamenti
  automatici, limite dei file, valori predefiniti. (a) Va bene così; (b) un riassunto in Informazioni.
  **Consiglio (a)**: niente lì serve a un non admin, e l'API resta com'è.
- **D5** (punto 3) Come si cambia la modalità nella scheda Utenti? (a) Come in Impostazioni globali: lucchetto, poi
  salva o annulla; (b) si salva alla scelta, con una conferma solo per «aperta a tutti»; (c) una scelta e un pulsante
  «Salva». **Consiglio (b)**: è un controllo solo, e la conferma protegge la scelta rischiosa.
- **D6** (punto 3) Solo la modalità, o anche «Richiedi la verifica dell'email» (di E, stessa sezione «Chi può
  iscriversi»)? **Consiglio: solo la modalità** per ora; la verifica ha le sue regole (servono i link dell'email).
- **D7** (punto 3) Dove: nella prima sezione, accanto a «Invita», o in una sezione «Iscrizioni» sua, sopra gli account?
  **Consiglio: nella prima sezione**: il motivo per cui «Invita» è spento sta accanto al controllo che lo riaccende.
- **D8** (punto 4) Senza icona: (a) l'iniziale in un cerchio neutro, come nella ricerca degli utenti; (b) un'icona
  generica; (c) nulla. **Consiglio (a)**.
- **D9** (punto 5) L'etichetta: «Guida» (come nella richiesta) o «Scopri di più» (come nel pannello della connessione)?
  **Consiglio «Guida»**, con il libro.
- **D10** (punto 5, per il coordinatore e H) Il percorso della guida dal backend (a) o da una tabella nel frontend (b)?
  **Consiglio (a)**.
- **D11** (punto 5) Una lingua senza l'ancora (traduzioni indietro): il link porta (a) alla pagina tradotta, in cima, o
  (b) alla sezione inglese? **Consiglio (a)**: la lingua dell'utente; il debito è A-10.

#### Ordine proposto
1. N69-2: piccolo.
2. N69-4: piccolo–medio.
3. N69-1: piccolo–medio.
4. N69-3: medio.
5. N69-5: medio, dopo l'accordo con H.

Ognuno con i rossi prima e uno slot. Uno slot API (`users-admin`) per N69-4 e N69-5. Uno slot E2E (`settings`,
`admin-users`, `security-tab`, `connection-security`) e la galleria con G.

#### Trovato strada facendo (fuori da N69)
- `Header.svelte:241`: il nome accessibile del pulsante del menu è in inglese scritto a mano («Toggle menu»), in ogni
  lingua. File della shell: da girare a chi la tiene.

### A57.2 — VIA del developer (19/10, 11:42; base `d28d0841d`)
- Coordinatore: giornale committato (`d28d0841d`); «VIA per A-57, solo i test: il developer ha detto «ok». Fai leggere a
  LGM-E-01/03 il profilo della corsia, così H rimette la spec nella cloud smoke». Lo slot E2E per le prove dopo le 14:00,
  da chiedere. N69 aspetta le risposte del developer a D1–D11.
- Valgono le autorizzazioni del 17/10 (21:44): il permesso di scrivere la sola riga `prereq` di `legal-managed` in
  `scripts/test_runner/_frontend_utility.py` (W ha lo stesso file aperto, K3, un'altra regione); la stessa cartella dati
  per la corsia gestita. Il ritorno nella cloud smoke (`CLOUD_SMOKE_SPECS`, il commento, `front-utility.md:112`) resta di H.
- Con A-57 entra la frase sulle pre-release in `developer/frontend/onboarding.md` (nota 2 di E su C-54), sospesa con lui.
- Verificato: dalla prova 1 (base `98b0fc974`) la spec, `fixtures/instance-config.ts`, `fixtures/auth-helpers.ts`,
  `ForgotPasswordCard.svelte`, `features/instance/profile.ts` e `features/legal/` non sono cambiati. Il solo commit nel
  mezzo, `81a927681`, cambia una riga di `_frontend_utility.py` che non è la registrazione di `legal-managed`. I rossi
  della prova 1 valgono ancora.
- Passi: spec nuova (`test-author`, solo controlli leggeri: Prettier e tipi, nessuna corsa), riga `prereq`, frase rc,
  poi lo slot (prove 2 e 3: self-hosted e gestita).
- **Frase rc** (11:50): in `developer/frontend/onboarding.md`, dopo gli esempi di `release_of()`: «A pre-release thus
  counts as its release: an account that closed the window on `1.3.0-rc1` does not see the `1.3.0` chapter again at the
  final release, even if that chapter grew in between — acceptable for the instances that run release candidates (E's
  review of C-54).» Verificata nel codice: `release_of('1.3.0-rc1')` → `1.3.0`, `mark_seen` salva la base, e
  `pending_for` alla release finale non trova nulla di più nuovo. `mkdocs build` strict e `check-links` (97) puliti;
  pagina solo EN.
- **Spec** affidata a un `test-author` (`5fc0c272`): solo `frontend/e2e/layout/legal-and-managed.spec.ts`, solo Prettier
  e tipi, nessuna corsa.

### A57.3 — Spec e riga del registro pronte (19/10, 11:45–12:05)
- **Spec** (`test-author` `5fc0c272`, solo `frontend/e2e/layout/legal-and-managed.spec.ts`):
  - `readLaneAnswer(page)` legge la risposta della corsia prima di ogni pagina e di ogni stub
    (`page.request.get('/api/v1/system/instance')`, che non passa da `page.route()`). Vuole 200, `profile`
    `selfhosted` o `managed`, e `legal` con due link, una pagina o null; il profilo finisce nelle annotazioni
    (`lane-profile`).
  - LGM-E-01, ramo self-hosted: come prima.
  - LGM-E-01, ramo gestito:
    - la prova è `forgot-ask-admin` (dopo `goto-forgot`), con la stessa esecuzione marcata;
    - si torna al login con `forgot-back-to-login`, poi la nota sotto la scheda;
    - dietro la barra disegnata: nessun link alla donazione.
  - LGM-E-03, ramo self-hosted: come prima, con i link legali della corsia.
  - LGM-E-03, ramo gestito: uno stub dei soli `legal`, il profilo vero della corsia. La prova e le assenze sono quelle di
    LGM-E-04, fattorizzate in aiuti comuni; LGM-E-04 stessa resta uguale.
  - I link legali seguono la risposta della corsia: un link con esattamente quell'indirizzo, o nessuno.
  - Titoli e intestazione per i due profili; gli ID restano.
  - Prettier pulito; `tsc -p tsconfig.e2e.json --noEmit`: 0 errori.
  - Dubbio dell'agente: con le due corsie di oggi (nessuna pagina legale) il ramo «la corsia ha una pagina» non gira mai.
- **Riga `prereq`** di `legal-managed` (`scripts/test_runner/_frontend_utility.py`, la sola riga autorizzata): «a
  self-hosted lane, or a managed one (--lane-setting LIBREFOLIO_PROFILE=managed): LGM-E-01 and LGM-E-03 read the lane's
  own GET /system/instance and check the matching variant (A-57)». `ruff` e `black` puliti, come a HEAD.
- **Da chiedere**: la riga `desc` della stessa voce descrive ancora la sola corsia self-hosted (la prova
  `auth-donate-link`).
- **Slot** (dopo le 14:00, chiesto al coordinatore): `work/slot_a57/slot.sh d28d0841d green`.
  - Prova 2: `front-utility legal-managed` su corsia self-hosted, 5 attesi.
  - Prova 3: la stessa con `--lane-setting LIBREFOLIO_PROFILE=managed`, 5 attesi.
- **Coordinatore (12:03)**: sì anche alla riga `desc` della stessa voce (una riga sola). Slot E2E in coda **dopo X** (X
  parte alle 14:00 per circa 45 minuti); il «via» lo scrive il coordinatore. Dopo lo slot verde: checkpoint, e il
  coordinatore avvisa H.
- **Riga `desc`** riscritta (12:08): i due profili (A-57), la lettura della corsia di LGM-E-01/03, le prove e le assenze di
  ciascuna variante; il resto (LGM-E-02/04/05) com'era. `ruff` e `black` puliti, il file si analizza; nessun test del
  runner vincola `desc` o `prereq`.

### A57.4 — Slot E2E ✅ (19/10, 12:34–12:39)
- Coordinatore (12:34): «Slot tuo, da adesso, fino alle 13:00, sulla corsia 6182 … ognuna solo con carico a 1 minuto
  sotto 50». Lo script dello slot aspettava il carico a 5 minuti: portato a quello a 1 minuto prima di partire.
- `work/slot_a57/slot.sh d28d0841d green`:
  - prova 2, corsia self-hosted (`front-utility legal-managed`): **5 passed** (23,5 s; 12:35–12:38);
  - prova 3, corsia gestita (`--lane-setting LIBREFOLIO_PROFILE=managed`, il runner stampa `Test lane settings:
    LIBREFOLIO_PROFILE=managed`): **5 passed** (24,5 s; 12:38–12:39).
- Il rapporto HTML della prova 3 (l'ultima; quello della prova 2 l'ha sovrascritto) porta le annotazioni `lane-profile:
  managed` su LGM-E-01 e LGM-E-03: hanno girato le varianti gestite. La prova 2 è la corsia predefinita, senza
  impostazioni di corsia.
- Impronta dell'albero invariata (`da3542669b560ce7`), porta 6182 libera; «slot libero» al coordinatore alle 12:39.
- Con la prova 1 del 17/10 (la spec vecchia su una corsia gestita: LGM-E-01/03 rossi) il ciclo rosso → verde è chiuso.
- **A-57: definizione di fatto ✅** (solo test). Il ritorno della spec in `CLOUD_SMOKE_SPECS` (la lista, il commento,
  `developer/test-walkthrough/front-utility.md:112`) è di H: il coordinatore lo avvisa dopo l'ingresso.
- **Indice**: A-57 chiusa con ✅ nella sezione A (il sotto-punto «Sospesa» riscritto: sospesa, poi l'«ok» delle 11:42).
- **Previsione dei conflitti** con dev `c81389cad`:
  - i miei commit di giornale `52421559f` e `d28d0841d` non sono ancora in dev, quindi la base vera è `ede7adf75`;
  - `git merge-file` con quella base è pulito: l'indice (9 commit di dev) e `_frontend_utility.py` (X-R16 alla riga
    ~116, le mie righe alla 1024–1025);
  - **⚠️ Fuori pista**: una prima simulazione con HEAD come base dava un conflitto falso sull'indice (le righe aggiunte solo
    nel mio ramo sembravano tolte da dev).
- **Checkpoint** mandato al coordinatore (12:50): tre commit proposti, nessuna riga del CHANGELOG (solo test e doc per
  sviluppatori). FROZEN.

## A-CL1 — Il changelog resta «in caricamento» aperto da Impostazioni → Informazioni: analisi (19/10, 14:40–15:40, sola lettura; base `f3805aa09`)
- **Richiesta** (coordinatore, 14:36): difetto visto dal developer sulla nightly `v1.2.1-2591-g5e1a7c3af`. Il clic sulla
  versione sotto il logo apre il changelog, che resta «in caricamento»; dalla versione nella sidebar si apre subito.
  Servono la causa, un rosso Vitest o E2E, la cura proposta e il costo. Niente codice prima del via.
- **Stesso codice**: `5e1a7c3af` è «Merge pull request #53 from Librefolio/dev_release2» (17/10, 20:47Z). Letti via
  `gh api …/contents?ref=` (nessun `git fetch`), sono identici byte per byte al mio albero:
  - `ChangelogModal.svelte`, `changelog.ts`, `AboutTab.svelte`, `Sidebar.svelte`;
  - `WhatsNewModal.svelte`, `ModalBase.svelte`, `package.json`.

### Causa
1. **Lo stato «pronto» legge una cache che non è reattiva.**
   - `ChangelogModal.svelte:43`: `ready = $derived(localizedChangelog.peek(uiLanguage) ?? (loaded?.language ===
     uiLanguage ? loaded.chapters : undefined))`.
   - `peek()` legge `merged`, una `Map` semplice (`changelog.ts:402`), quindi non è una dipendenza.
   - `ready` si ricalcola solo quando cambiano `uiLanguage` o `loaded`.
2. **Il risultato viene scartato alla chiusura.** Se la modale si chiude mentre la traduzione carica, il teardown
   dell'effetto di caricamento (`:47–59`) mette `live = false`: il risultato non arriva mai in `loaded`, ma la cache
   `merged` si riempie lo stesso.
3. **Alla riapertura resta bloccata.**
   - `ready` tiene il suo `undefined` in cache: le sue dipendenze non sono cambiate, e un `$derived` di Svelte 5 resta in
     cache anche attraverso la chiusura e la riapertura del blocco `{#if open}`.
   - L'effetto trova `peek()` pieno ed esce subito, quindi `loaded` non viene mai assegnato.
   - Risultato: «Caricamento…» per sempre, fino a un cambio di lingua o a un ricaricamento.
4. **Perché la sidebar si apre subito**: è un'altra istanza. Il suo `ready` si calcola per la prima volta all'apertura,
   quando la cache è già piena (l'ha riempita il caricamento dell'Informazioni).
5. **Le ipotesi del coordinatore**:
   - *promessa rifiutata o mai risolta*: **no**.
     - `load()` non rifiuta mai (`.catch(() => englishOnly)`).
     - Un chunk appeso bloccherebbe anche la sidebar, che condivide la stessa promessa `pending`.
   - *l'effetto che si riesegue e scarta il risultato*: **sì**, ma a rieseguirlo è la chiusura (`open` falso), non una
     riesecuzione spontanea.
     - La prima apertura, col chunk che arriva a modale aperta, funziona (R0 e M3 verdi).
     - Anche la galleria e `changelog-locale.spec.ts` aprono la modale della sidebar in italiano a ogni giro.
   - *`WhatsNewModal` o la sidebar che precaricano*: **non la causano**. Una cache riempita da altri *prima* della prima
     apertura rende l'apertura immediata, non bloccata.
6. **Il gesto da confermare col developer**:
   - la modale si è chiusa mentre la traduzione caricava;
   - modi possibili: Esc, un clic fuori, o — il più probabile — un secondo clic sulla versione: lo sfondo della modale la
     copre già, e un clic sullo sfondo chiude;
   - poi è stata riaperta dopo l'arrivo del chunk.
   - Non è un difetto solo dell'Informazioni: la stessa sequenza blocca anche la modale della sidebar, se è la prima della
     sessione a caricare la traduzione.
   - Nell'Informazioni è più probabile: la scheda si apre con 7 chiamate API e le icone dei provider in volo, e il chunk
     (~140–150 KB) fa la coda con loro.

### Rossi (scratch, nella cartella di sessione `work/acl1/`)
- **Procedura**: i file venivano copiati nell'albero solo per la corsa, poi tolti (`git status` pulito dopo ogni corsa);
  Vitest con il carico a 1 minuto 28–39.
- **`AboutTab.changelog.acl1.test.ts`**: l'AboutTab vera, la modale vera, e un fake che copia riga per riga
  `createLocalizedChangelog` (cache `Map`, `pending` condiviso).
  - R0, prima apertura, chunk che arriva a modale aperta: ✅.
  - **R1, chiusa mentre carica, chunk che arriva a modale chiusa, riaperta: ✗.** Dopo 1 s c'è ancora
    `changelog-loading`, con `merged.has('it')` vero.
  - R2, una seconda istanza (come la sidebar): si apre subito ✅.
  - R3, chiusa e riaperta mentre carica ancora: ✅.
- **`ChangelogModal.acl1.test.ts`**: la modale da sola, 3 varianti × 3 scenari, nessun avviso di Svelte.
  - Gli scenari:
    - M1: la sequenza R1;
    - M2: un chunk fallito mostra l'inglese, poi un altro consumatore carica l'italiano, e la modale si riapre;
    - M3: il controllo.
  - Esiti:

    | Variante | M1 | M2 | M3 |
    |---|---|---|---|
    | oggi | ✗ | ✗ | ✅ |
    | C4 | ✅ | ✗ | ✅ |
    | C1 | ✅ | ✅ | ✅ |
- **Un test sul modulo vero non è possibile in Vitest**:
  - jsdom rifiuta l'import `?raw` di `CHANGELOG.md` anche con `vi.mock` («Denied ID …/CHANGELOG.md?raw»);
  - in ambiente node, `svelte/reactivity` è la build server, non reattiva.
  - Quindi la reattività del modulo vero si vede solo in un E2E.

### Cura proposta (scelta tecnica: nessun cambiamento visibile oltre al difetto risolto)
- **C1, consigliata: la cache diventa reattiva.**
  - In `changelog.ts`, `merged` diventa una `SvelteMap` (`svelte/reactivity`): +2 righe.
  - Ogni `$derived` o `$effect` che chiama `peek()` segue la cache, e `ready` si ricalcola quando un caricamento
    qualsiasi la riempie.
  - I componenti non cambiano: `loaded` resta per il ripiego inglese di un fallimento.
  - Copre anche M2 (oggi resta in inglese fino al ricaricamento) e `WhatsNewModal`, che ha lo stesso schema.
- **C4, alternativa minima: togliere la guardia `live`.**
  - In `ChangelogModal.svelte`, −4 righe: il risultato arriva sempre in `loaded`.
  - `loaded` porta la sua lingua, quindi `ready` ignora già una risposta tardiva per un'altra lingua.
  - Lascia aperto M2.
- **Non proposta: C2** (copiare `peek()` in `loaded` nel ramo d'uscita dell'effetto). È una scrittura di stato in un
  effetto, e alla riapertura mostrerebbe un fotogramma di «Caricamento…».

### Costo, test, rischi
- **C1**:
  - codice: 2 righe;
  - Vitest: M1 + M2 nella sezione CL di `ChangelogModal.test.ts`, rossi oggi col fake fedele. Nello stesso commit la
    cache del fake (`cached`) diventa una `SvelteMap`, perché rispecchia il modulo. Il fake di `WhatsNewModal.test.ts`
    si allinea pure (facoltativo, senza test nuovi);
  - E2E: un test in `e2e/layout/changelog-locale.spec.ts`, dall'Informazioni in italiano:
    - il chunk della traduzione viene trattenuto con `page.route`; i nomi dei chunk sono hash, quindi si riconosce dal
      corpo, che contiene una riga di `CHANGELOG.it.md`;
    - poi apri, chiudi, rilascia, riapri, e i capitoli devono esserci;
    - rosso oggi, verde dopo: serve uno slot E2E (2 corse, ~5 min);
  - totale ~1–1,5 h con il `test-author`, più una riga 🐛 del CHANGELOG.
- **C4**: codice −4 righe; Vitest M1 (il fake resta com'è: rosso oggi, verde dopo); E2E facoltativo; ~30–45 min.
- **Conflitti**:
  - nessun ramo locale (32) e nemmeno `dev_release2` (`7fa7d4f93`) ha commit oltre il mio HEAD su questi file:
    - `ChangelogModal.svelte` e `ChangelogModal.test.ts`;
    - `features/changelog/` e `AboutTab.svelte`;
    - `changelog-locale.spec.ts`.
  - Altri autori di questi file: CL e M-23 (`changelog.ts`); H e il programma colori (`ChangelogModal.svelte`).
- **Colori**: nessuna classe cambia, quindi nessun effetto sui cancelli.
- **Domanda al developer** (una conferma, non una decisione): la modale si era chiusa e riaperta (Esc, clic fuori,
  secondo clic sulla versione) prima di restare «in caricamento»?
  - Se anche un solo clic, senza chiusura, la blocca, c'è una seconda via che non ho riprodotto.
  - In quel caso il passo successivo è l'E2E sopra, senza la trattenuta, sulla build della nightly.
- Stato: **FROZEN** in attesa del via; nessun file del prodotto toccato.
