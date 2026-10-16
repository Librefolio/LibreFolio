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
