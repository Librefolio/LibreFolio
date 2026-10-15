# Piano — fase 01, sessione E: email facoltativa (F04) — 1.3.0

> Sessione E della 1.3.0 «Cloud-ready core». Coordinatore: sessione «Release 1.3 planning»
> (`928ffa97-f0c3-4975-a442-3de0c2c20fc7`). Piano generale: [plan-phase01Release13](../plan-phase01Release13.prompt.md),
> §4 «E · Email», §5 riga «Email (F04)». Decisioni del developer: [decisioni-analisi-20261014](../decisioni-analisi-20261014.md),
> punti 44 e 45. Backlog: [sezione E](../../Phase_0/BACKLOG_POST_1.2.md).

| Voce | Valore |
|---|---|
| Worktree | `LibreFolio-worktrees/e-alfy-stunning-fortnight` |
| Ramo | `e-alfy-e-email` |
| Corsia | porta 6188, data-dir `/tmp/librefolio-r13-e` |
| Base dell'analisi | `380a3e768` (15/10, 08:37) |
| Base del primo via | `23f6578f3` (15/10, 11:23) |

## Autorizzazione (15/10/2026, ~11:08)

> Del developer, alla lettera, inoltrata dal coordinatore: «riguardo b ed e sei tu il coordinatore, a meno che non devo
> qualcosa in particolare, e allora aggiornami, avviali tu.»

**Via del coordinatore (11:23): E0 ed E1**, con tre esclusioni:
- `links.py` passa a E3: dipende dal punto 45 (D-E3), ancora aperto;
- nessuna riga in `services/platform/config_audit.py` in E1 (modifiche in attesa sul ramo di H): i controlli stanno in
  `services/email/checks.py`, la registrazione in `CONFIG_CHECKS` entra in E2, dopo l'aggiornamento di base con H;
- niente aggancio in `scripts/cli_base.py`: C-96 di H toglie dalle corsie ogni `LIBREFOLIO_*`, quindi anche
  `LIBREFOLIO_SMTP_*`. Finché C-96 non è in `dev_release2`, i test di E impostano e tolgono da sé le variabili SMTP
  (`monkeypatch`) e non leggono mai l'ambiente della corsia.

In `.env.example` solo la sezione «Email»: A e H cambiano il file sui loro rami.

**Decisioni** (§4): approvate dal coordinatore D-E1, D-E2, D-E4, D-E5, D-E6, D-E8…D-E14; D-E12 la comunica il
coordinatore ad A (A8 riuserà `rate_window.py`). Aspettano il developer: **punto 45 (D-E3)** per E3, **punto 44
(D-E7)** per E5. E2 aspetta anche A5a in `dev_release2`; il suo frontend entra dopo la finestra della galleria e dopo L.

**Note per E3–E5** (dal coordinatore): con A5b il token viaggia nel frammento, non nella query (`/invite#token=`,
`/reset-password#token=`, `/setup#…`, `/verify-email#…`).
- I link si costruiscono solo con `token_path` e `public_link` di A.
- La pagina `/verify-email` legge `location.hash`, lo toglie con `replaceState` e ascolta `hashchange`, come le pagine
  di A.

## 1. Stato reale (verificato sul codice a `380a3e768`, riverificato a `23f6578f3`)

- **Nessun codice email**: zero `smtplib`, `aiosmtp*`, `send_email` in `backend/`, `scripts/`, `frontend/src`, `dev.py`.
- **Token di A4 (in base)**: `services/accounts/token_service.py` — `issue/inspect/consume/revoke_tokens`, flush senza
  commit; `DEFAULT_TTL`: invito 7 g, reset 30 min, setup 72 h, verifica 24 h. `AccountToken.email` (promemoria
  dell'invito); `users.email_verified_at` NULL sugli account di prima della 005.
- **A5a** (`7da2cd9a2`, sul ramo di A): `registration_service.py` (`create_invite(..., email=)`, `register_user`,
  `public_link(path)`, `billing_link()`), `user_service.py` (`create_password_reset` ~r. 233, `complete_password_reset`
  ~r. 247, `update_user_status`), `config/accounts.py` (`public_url()`).
- **`require_email_verification`**: segnaposto che nessuno legge (`schemas/settings.py:293-298`, `:550`;
  `GlobalSettingsTab.svelte:72`, `:591-592`, «Coming soon»; `admin/settings.en.md:51`). GSET-VAL-007
  (`test_settings_api.py:1589-1595`, `:1770`) lo accende sul server della corsia perché «harmless».
- **Login**: `api/v1/auth.py:158-161` → 403 `ACCOUNT_DISABLED` solo con la password giusta; mappa del frontend in
  `stores/app/auth.ts:48-56`, `types/user.ts:61`.
- **Password dimenticata oggi**: `features/auth/ForgotPasswordCard.svelte` (di A; colori di T-2, blocco terminale
  legacy di proposito), montata da `routes/+page.svelte:130-131`; FAQ `community/faq.en.md:56-58`.
- **Configurazione (H CP3)**: `env_secret()` con `_FILE`; `secrets_set_twice()` copre già ogni `LIBREFOLIO_*`, quindi
  anche `LIBREFOLIO_SMTP_PASSWORD` + `_FILE`; `config_audit.py`: controlli sincroni senza DB nella tupla
  `CONFIG_CHECKS`, chiavi i18n proprie. `.env.example`: sezione «Email» vuota.
- **Lingua**: `UserSettings.language` (creata pigramente con `default_language`); Babel già dipendenza
  (`format_timedelta`: «30 minuti», «1 settimana», «1 giorno», «3 giorni»).
- **Worker**: 1 di default (`dev.py`); `--workers N` moltiplica i limiti in memoria.
- **SPA**: ogni percorso non-API serve `200.html` (`main.py:483-523`).
- **Galleria**: già usa `page.route` per gli stati simulati.
- **i18n**: nessun prefisso `email.*`; i frammenti di backend solo per `*_providers`/`*_plugins`.
- **Dipendenze**: `aiosmtpd` su PyPI dichiara fino al 3.12; `smtplib` della libreria standard basta. `smtplib`, se il
  nome dell'host non ha punti (qui `socket.getfqdn()` è «MacBook Pro di Emanuele (2)»), saluta con `[indirizzo IP]`:
  nessun EHLO non valido.

## 2. Voci già fatte, contraddette o da sapere

- **Contraddetta**: `TODO_FUTURI` «📧 Server email» («SMTP configurabile dalle impostazioni admin», «valutare
  `aiosmtplib`»). Vale F04: solo variabili o file, mai DB, UI né backup; invio con la libreria standard (D-E1).
- **Già coperto da H**: l'avviso «password insieme a `_FILE`» (`check_secrets_set_twice`).
- **Già fatto da A**: link d'invito e di reset da copiare, senza SMTP (A5/A6).
- **F02, decisione 3**: nel cloud il link d'attivazione lo spedisce il pannello; l'istanza solo se il token l'ha
  generato lei (D-E11).
- **GSET-VAL-007** va spostato su un'altra chiave quando la verifica diventa vera (E5).
- **Per B e la revisione di sicurezza**: un ripristino rianima i token vivi al momento del backup (inviti, reset).
- **C-96** (trovata in questa analisi, assegnata ad H): le corsie dei test prendevano la configurazione d'istanza dal
  `.env` del developer.

## 3. Disegno

### 3.1 Configurazione — `backend/app/config/email.py` (sezione E)

| Variabile | Default | Note |
|---|---|---|
| `LIBREFOLIO_SMTP_HOST` | non impostata = email spenta, come oggi | |
| `LIBREFOLIO_SMTP_TLS` | `starttls` | `starttls` \| `tls` (implicito) \| `none`; mai ricaduta in chiaro |
| `LIBREFOLIO_SMTP_PORT` | dalla modalità: 587 / 465 / 25 | 1–65535 |
| `LIBREFOLIO_SMTP_USER` | nessuna autenticazione | insieme alla password, o nessuna delle due |
| `LIBREFOLIO_SMTP_PASSWORD(_FILE)` | — | `env_secret()` |
| `LIBREFOLIO_SMTP_FROM` | — | obbligatoria con HOST: `Nome <indirizzo>` o `indirizzo` |
| `LIBREFOLIO_SMTP_REPLY_TO` | nessuna | per il cloud (`support@librefolio.eu`) |
| `LIBREFOLIO_SMTP_MAX_PER_HOUR` | 50 | intero ≥ 1: il limite d'invio per istanza |

Configurazione non valida → email spenta, errore nel log una volta per processo, controllo `error`; l'avvio continua
(D-E4).

### 3.2 Servizio — `backend/app/services/email/` (`__init__.py` con la sola docstring)

- `smtp.py`: `smtplib` in un thread (regola Async I/O), contesto TLS di default (certificato verificato), `starttls`
  obbligatorio in modalità `starttls`; errori a codice (`CONNECTION_FAILED`, `TLS_FAILED`, `AUTH_FAILED`,
  `SENDER_REFUSED`, `RECIPIENT_REFUSED`, `TIMEOUT`, `SEND_FAILED`), il testo del server solo nel log. Un `QUIT` andato
  male dopo un invio riuscito non è un errore.
- `delivery.py`: stato della configurazione (mai un'eccezione), limite per istanza (finestra mobile di un'ora, in
  memoria), `send_email()` asincrona. Log senza corpo, link né token; destinatario come `user_id` o dominio.
- `messages.py` + `templates/`: un costruttore tipizzato per tipo di email (reset, invito, verifica, attivazione
  dell'admin, prova); testi in `templates/{en,it,fr,es}.json`, layout HTML con valori escapati, parte di testo sempre
  presente; intestazioni `From`, `Reply-To`, `Message-ID`, `Date`, `Content-Language`, `Auto-Submitted`; mai dati
  dell'utente nell'oggetto; durate con Babel.
- `checks.py`: controlli di configurazione (`email.checks.*`), registrati in `CONFIG_CHECKS` in E2.
- `backend/app/utils/runtime/rate_window.py`: primitiva unica a finestra mobile (chiavi limitate, orologio
  iniettabile), riusata da A8 (D-E12).
- E3: `links.py`, `flows.py`; E5: `verification.py`.

### 3.3 API (E2, E3, E5) — `backend/app/api/v1/email.py` + `schemas/email.py`

| Rotta | Chi | Lotto |
|---|---|---|
| `GET /email/status` | admin: stato, problemi, invii/limite; mai host, utente, mittente o password | E2 |
| `POST /email/test` | admin: prova solo verso il proprio indirizzo | E2 |
| `POST /email/links` | admin: spedisce un link appena creato con le rotte di A (invito a un indirizzo scelto; reset solo all'email dell'account) | E3 |
| `POST /email/password-reset` | anonimo: «password dimenticata», 202 sempre uguale | E3 |
| `POST /email/verification/confirm`, `/resend` | anonimo | E5 |

`/system/instance` (di H): campo `email: {available}` con un default nello schema (E2).

### 3.4 Password dimenticata (E3)

Email non pronta → 409 uguale per tutti; limiti per IP e per identificativo scritto (indipendenti dall'esistenza)
→ 429; limite d'istanza → 429 per tutti; poi **202** subito e il lavoro (ricerca come il login, `create_password_reset`
di A, invio) in background con una sessione DB propria. Per account 1 email/5 min e 3/h contate sulle righe dei token,
in silenzio. Lingua salvata dell'account → `default_language` → `en`.

### 3.5 Verifica dell'email (E5, se il punto 44 la approva)

Per le registrazioni fatte mentre l'opzione è accesa (non il primo account): account disattivo in attesa fino al link
(24 h, rispedibile); login → 403 `EMAIL_NOT_VERIFIED` con «rispedisci»; l'admin può attivarlo a mano (i suoi cambi di
stato revocano i token di verifica); account esistenti e da riga di comando mai bloccati; si accende solo con l'email
pronta; nessuna migrazione.

### 3.6 Frontend (E2, E4, E5)

File nuovi a zero classi di palette, solo utility `*-lf-*`: scheda «Email» (solo admin), modulo «password
dimenticata», «Spedisci per email» nelle modali di A6, avviso di verifica nel login, pagina `/verify-email`. Sorgente
i18n nuova `lib/i18n/email/` (prefisso `email`). Galleria con `page.route`.

## 4. Decisioni

| # | Domanda | Scelta | Stato |
|---|---|---|---|
| D-E1 | Invio senza bloccare | `smtplib` in `asyncio.to_thread`, nessuna dipendenza | ✅ coordinatore |
| D-E2 | SMTP finto per i test | scritto nei test (libreria standard, 127.0.0.1, porta effimera); il successo TLS vero solo se arriva `cryptography` | ✅ coordinatore |
| D-E3 | Link | anonimi solo con `LIBREFOLIO_PUBLIC_URL`; invii dell'admin anche con la base che vede nel browser | ⏳ developer, punto 45 |
| D-E4 | Configurazione non valida | email spenta, errore nel log e nei controlli, l'avvio continua | ✅ coordinatore |
| D-E5 | Limite d'invio | in memoria per processo, 50/h di default | ✅ coordinatore |
| D-E6 | Variabili oltre la specifica | `_REPLY_TO`, `_MAX_PER_HOUR`; `_TLS` a tre valori | ✅ coordinatore |
| D-E7 | Senso di `require_email_verification` | account in attesa = disattivo fino al link, senza migrazione; E5 può slittare alla 1.4 | ⏳ developer, punto 44 |
| D-E8 | Testi delle email | catalogo del backend in 4 lingue + guardia pytest | ✅ coordinatore |
| D-E9 | Email di prova | scheda «Email» di Impostazioni, solo admin | ✅ coordinatore |
| D-E10 | Link dell'admin | endpoint di E che spedisce il token appena creato dalle rotte di A | ✅ coordinatore |
| D-E11 | Attivazione dell'admin | email solo se il token l'ha generato l'istanza | ✅ coordinatore |
| D-E12 | Limitatore | `utils/runtime/rate_window.py`, scritto da E, riusato da A8 | ✅ coordinatore (lo comunica ad A) |
| D-E13 | Istanza bloccata | nessuna rotta di E fra i permessi; in più l'invio rifiuta a istanza bloccata (dopo CP6) | ✅ coordinatore |
| D-E14 | E2E | `page.route` per gli stati; la catena vera nei test backend in processo | ✅ coordinatore |

## 5. Righe nei file altrui (chi le scrive lo decide il coordinatore)

- **H**: `config_audit.py` (`CONFIG_CHECKS`, E2; attenzione al ciclo d'import: `email/checks.py` importa `ConfigCheck`
  da `config_audit`); `schemas/system.py` + `api/v1/system/instance.py` (campo `email`, E2, dopo A5a); CP6
  (classificazione delle rotte e accessore del blocco).
- **A backend (E5)**: `register_user` (A5a r. 212-214), `auth.py` register e login `:158-161`, `schemas/auth.py`,
  `update_user_status`, `update_profile` `:348-353`, `update_global_settings`, GSET-VAL-007; A7 (una chiamata).
- **A frontend**: `settingsTabs.ts` (E2), `ForgotPasswordCard` e modali di A6 (E4), `LoginCard`, `stores/app/auth.ts`,
  `types/user.ts`, `RegisterCard`, `GlobalSettingsTab` (E5).
- **Condivise**: `api/v1/router.py` (E2), catalogo del runner (in aggiunta), `gallery.spec.ts`, CHANGELOG e nav MkDocs
  (testo nell'handoff).

## 6. Previsione dei conflitti

| Con | Dove | Gestione |
|---|---|---|
| A5a/A5b, A6–A8 | `register_user`, `auth.py`, `instance.py`, card di accesso, `GlobalSettingsTab`, modali | agganci dopo l'ingresso di A5 e A6 |
| H | `config_audit.py`, `system.py`/`instance.py`, `router.py`, `.env.example` | righe in aggiunta; in `.env.example` solo la sezione «Email» |
| B | nessun file | nota sui token vivi al ripristino |
| Colori | `GlobalSettingsTab` (110 legacy), card di accesso, `gallery.spec.ts` | solo logica nei file legacy; file nuovi a zero |

## 7. Lotti e checkpoint

| Lotto | Contenuto | Dipende da | Stato |
|---|---|---|---|
| E0 | Questo piano, sezione E del backlog | via | ✅ (checkpoint E1) |
| E1 | Configurazione, `.env.example` (sezione Email), `smtp`, `delivery`, `messages` e testi, `checks`, `rate_window`, SMTP finto, test, doc per sviluppatori | niente | 🧊 checkpoint |
| E2 | `GET /email/status`, `POST /email/test`, router, `/system/instance.email`, `CONFIG_CHECKS`, scheda «Email», i18n, Vitest, E2E simulate, galleria, doc admin | A5a in base; H per `config_audit`; frontend dopo la finestra e L | ⏳ |
| E3 | `links.py`, `POST /email/links`, `POST /email/password-reset`, attivazione dell'admin | A5a in base, punto 45 | ⏳ |
| E4 | modulo «password dimenticata», «Spedisci per email» | A5b e A6 in base | ⏳ |
| E5 | verifica dell'email | punto 44, A5a+A5b in base | ⏳ |
| E6 | doc finali, devWiki, `TODO_FUTURI`, testo per il CHANGELOG, `all-backend` + E2E, `security-review` | tutto | ⏳ |

## 8. Definizione di fatto

- Selettori nuovi e toccati verdi; `all-backend` con i conteggi della base più i nuovi; `front check` 0/0; Vitest ed
  E2E del dominio verdi; cricchetto dei colori pulito.
- `ruff`, `black`, Prettier; `lint --dead-code` senza reperti nuovi, salvo i transitori dichiarati; `check-orphans`.
- `api sync` con le sole differenze volute; `i18n check` stretto; `mkdocs build` stretto, `check-links`.
- Senza variabili SMTP nessun comportamento cambiato.
- Galleria con le schermate nuove; porta 6188 libera all'handoff; piano e backlog aggiornati.

## 9. Test e selettori

Preambolo: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6188 --data-dir /tmp/librefolio-r13-e …`

- E1: `services email-config`, `services email-messages`, `services email-delivery`, `services email-checks`,
  `utils rate-window` (tutti `pure`); da rifare `services config-package`, `services config-env-example`.
- Poi: `api email`, `services email-flows`, `services email-verification`, E2E `front-user email`; da rifare `services
  config-audit`, `services registration`, `api registration`, `api auth`, `api users-admin`, `api settings`, `api
  system`, `utils gate-i18n-catalog`, `gate-i18n-usage`, `front-utility core-unit`, `component-unit`, `theme-roles`.
- Nella finestra della galleria solo prove leggere: `nice`, nessun server, una alla volta (le categorie `services` e
  `utils` non avviano il server condiviso; `services` ricrea il DB della corsia).

## 10. Specialisti

`test-author` (file distinti, corsia 6188, nessuna suite senza il via), `docs-writer` (EN), `project-historian` o
`wiki-file` (devWiki), `security-review` a fine lavoro.

## 11. Avanzamento

### E0 — piano e backlog

#### E0.0 — Via e base ✅ (2026-10-15)
> **Note implementazione**: autorizzazione e perimetro come sopra (messaggio del coordinatore delle 11:23). HEAD
> `23f6578f3` = base indicata dal coordinatore, worktree pulito, porta 6188 libera (`lsof` vuoto).

#### E0.1 — Piano nel journal ✅ (2026-10-15)
> **Note implementazione**: questo file, dall'analisi consegnata alle 08:5x (testo intero nella cartella della sessione
> `877410cd`), con l'autorizzazione, le esclusioni del via e lo stato delle decisioni. La sezione E del backlog si
> scrive al checkpoint, con le voci nate nel lotto.

### E1 — il servizio email, senza interfaccia

#### E1.1 — Contratto e test rossi (`test-author`) ✅ (2026-10-15)
> **Note implementazione**: contratto passato a `test-author` (in background, corsia 6188, solo `services` e `utils`,
> con `nice`): `config/email.py`, `utils/runtime/rate_window.py`, `services/email/{messages,smtp,delivery,checks}.py`,
> un server SMTP finto nei test e le voci del runner. Ogni modulo di test toglie da sé le `LIBREFOLIO_SMTP_*` (C-96 non
> è ancora in base).
>
> | File | ID | Casi |
> |---|---|---|
> | `test_services/test_email_config.py` | EMC-001…019 | 140 |
> | `test_utilities/test_rate_window.py` | RWL-001…017 | 26 |
> | `test_services/test_email_messages.py` | EMM-001…030 | 245 |
> | `test_services/test_email_delivery.py` | EMD-001…036 | 75 (EMD-017/018 saltati: niente `cryptography`) |
> | `test_services/test_email_checks.py` | EMK-001…009 | 48 |
> | `fixtures/email/fake_smtp.py` | `FakeSmtpServer`, `ReceivedMessage`, `closed_port()` | — |
>
> - Runner, solo in aggiunta: `services email-config`, `email-messages`, `email-delivery`, `email-checks`
>   (`_backend_services.py`), `utils rate-window` (`_backend_utils.py`), tutte `pure`.
> - Rosso per il motivo giusto, una corsa alla volta: le cinque voci si fermano alla raccolta con `ModuleNotFoundError`
>   sul modulo mancante (log `/tmp/libreFolio_e1_red_<voce>.log`).
> - Scelte dove il contratto era ambiguo, tenute: `SMTP_PASSWORD_UNREADABLE` nomina `LIBREFOLIO_SMTP_PASSWORD_FILE`;
>   un `peek` o un `count` di una chiave sconosciuta non crea la chiave; un `To` con un a-capo anche solo in fondo è
>   rifiutato (niente `strip`); `EMD-018` (opzionale) prova che il certificato è verificato davvero.

#### E1.2 — Bozze dell'implementazione ✅ (2026-10-15)
> **Note implementazione**: scritte fuori dal repo (cartella di sessione, `files/e1/`) mentre `test-author` lavora, così
> i suoi test restano rossi per il motivo giusto. Provate su una copia di HEAD (`git archive` in
> `/tmp/libreFolio_e1_check`), con uno script usa e getta e un server SMTP minimo: accessori e loro errori, finestra
> mobile (scadenza al bordo, chiavi limitate), i 5 tipi di email nelle 4 lingue con escape e intestazioni, consegna in
> chiaro, rifiuto di `starttls` e `tls` verso un server in chiaro (nessun messaggio partito), porta chiusa →
> `CONNECTION_FAILED`, server muto → `TIMEOUT`, `QUIT` con 500 dopo l'invio = inviato, limite d'istanza (2/h: il terzo
> rifiutato con `retry_after` 3600, poi di nuovo libero), i due controlli. Log in `/tmp/libreFolio_e1_smoke.log`.
>
> **⚠️ Fuori pista**:
> - `smtplib` trasforma una lettura scaduta in `SMTPServerDisconnected`: il codice `TIMEOUT` si riconosce risalendo la
>   catena delle eccezioni fino a un `TimeoutError`.
> - In modalità `tls` un rifiuto di connessione non è un problema TLS: la classe dell'errore decide (`ssl.SSLError` →
>   `TLS_FAILED`), non il passo.
> - Prima versione della finestra mobile: un `peek` di una chiave nuova la inseriva, e oltre `max_keys` poteva sfrattare
>   una chiave vera. Ora una chiave entra solo con un colpo contato.

#### E1.3 — Implementazione nel repo e `.env.example` ✅ (2026-10-15)
> **Note implementazione**: le bozze copiate nei percorsi finali, con due correzioni chieste dai test:
> - `compose_message` non ripulisce più il destinatario (`EMM-029`: `alice@example.com\n` va rifiutato, non accorciato);
> - `Content-Language` si scrive dopo il corpo: `set_content` toglie ogni intestazione `Content-*` e la conversione in
>   multipart le sposta nella prima parte (`EMM-025` rosso al primo giro).
>
> `.env.example`: solo la sezione «Email», 9 righe commentate (le 8 variabili più `LIBREFOLIO_SMTP_PASSWORD_FILE`)
> col loro default; le altre sezioni intatte.

#### E1.4 — Test verdi e controlli ✅ (2026-10-15)
> **Note implementazione**: corsia 6188, una invocazione alla volta, con `nice`, nessun server (finestra della
> galleria). Log in `/tmp/libreFolio_e1g_<voce>.log`.
>
> | Voce | Esito |
> |---|---|
> | `utils rate-window` | 26 ✅ |
> | `services email-config` | 140 ✅ |
> | `services email-messages` | 245 ✅ (dopo la correzione di `Content-Language`) |
> | `services email-checks` | 48 ✅ |
> | `services email-delivery` | 73 ✅, 2 saltati (TLS vero senza `cryptography`) |
> | `services config-package` | 599 ✅ (i 6 moduli nuovi non leggono l'ambiente) |
> | `services config-env-example` | 36 ✅ |
> | `utils gate-i18n-usage` | 195 ✅ |
> | `check-orphans` | ✅, 282 file backend raggiungibili |
>
> - `ruff` e `black` puliti sui 16 file Python toccati; `git diff --check` pulito.
> - `lint --dead-code --scope backend`: 7 reperti nuovi, tutti nel gruppo «referenced only by tests»: `send_email`,
>   `budget_status` e i cinque costruttori dei messaggi. È lo stato di passaggio previsto (come `token_service` in A4):
>   li chiamano E2 (`build_test_message`, `send_email`, `budget_status`), E3 (reset, invito, attivazione) ed E5
>   (verifica).
>
> **⚠️ Fuori pista**: `black` ha messo su una riga sola due stringhe concatenate per vicinanza (lo stile del bottone
> HTML): unite in una stringa sola, che si legge meglio.

#### E1.5 — Doc per sviluppatori (`docs-writer`) e due correzioni dalla sua rilettura ✅ (2026-10-15)
> **Note implementazione**: pagina nuova `mkdocs_src/docs/developer/backend/email.md` (EN, solo sviluppatori:
> configurazione, trasporto, invio e limite, messaggi e catalogo, controlli, finestra mobile, test, prossimi lotti);
> due righe in `.github/instructions/backend.instructions.md` (albero di `services/` e «Where to Find Things»). La
> riga di navigazione la propongo al coordinatore. `mkdocs build` stretto e `check-links` dopo la finestra della
> galleria.
>
> **⚠️ Fuori pista** (trovati da `docs-writer` rileggendo il codice, corretti nel lotto):
> - Il log «Email not sent» portava `detail`, le parole del server così come sono: i server veri citano l'indirizzo che
>   rifiutano (`550 5.1.1 <alice@example.com>: …`), quindi l'indirizzo intero poteva finire nel log, contro il §3.2.
>   Ora `detail` nel log maschera la password (`***`) e l'indirizzo (`***@dominio`), senza badare alle maiuscole; il
>   server finto cita l'indirizzo come i server veri, così il test lo vede (`test-author`).
> - `LIBREFOLIO_SMTP_HOST=nome:porta` passava la validazione (i due punti servono a IPv6) e falliva solo all'invio:
>   ora è `SMTP_HOST_INVALID` («la porta va in `LIBREFOLIO_SMTP_PORT`»); gli indirizzi IPv6 senza parentesi restano
>   validi. Tolto da `checks._host_is_local` il taglio delle parentesi, irraggiungibile.
> - Il log «una volta per processo» è per variabile, problema e motivo (non solo variabile e problema, come diceva la
>   docstring di un test): un motivo diverso è un'informazione nuova. Comportamento tenuto, documentato.
> - Doc rimaste indietro per E1, allineate: `developer/architecture/settings.md` (le sezioni del pacchetto `config/`
>   ora sono quattro), `security.md` (il segreto SMTP fra quelli letti da `env_secret()`; un suo `_FILE` illeggibile
>   spegne l'email invece di fermare il server), `backend.instructions.md` (la finestra mobile in `utils/runtime/`).
> - Per H, non mio: il paragrafo generico «Secrets» di `.env.example` dice che un `NAME_FILE` illeggibile ferma il
>   server; per il segreto facoltativo dell'email non è così (D-E4). Segnalato al coordinatore.
> - Per E2: il `summary` dell'avviso di cifratura contiene il nome del server SMTP (va solo nel log): l'endpoint di
>   stato e la scheda «Sicurezza» mostrano solo `i18n_key` e `detail`.

#### E1.6 — Test aggiunti dalla rilettura e validazione finale ✅ (2026-10-15)
> **Note implementazione** (`test-author`, due giri in più, solo file di test):
> - `closed_port()` è un context manager che tiene la porta per tutto il test. Su macOS un socket solo legato, senza
>   `listen()`, non rifiuta la connessione ma la lascia scadere: il socket che tiene la porta è legato e connesso a un
>   ascoltatore privato, poi chiuso; prima di cedere la porta il fixture prova che una connessione è rifiutata.
>   `EMD-038` lo prova; il server finto ascolta senza `SO_REUSEADDR`.
> - Il server finto cita nel 550 l'indirizzo rifiutato, come Postfix; `EMD-037`: nessun evento o record nomina
>   l'indirizzo intero (con un controllo che la ricerca lo vede quando c'è), il rifiutato compare come `***@example.com`.
> - `EMD-039`: lo stesso problema con due motivi diversi si logga due volte, lo stesso motivo una volta sola.
> - `EMD-040`: `_redacted` maschera password (anche con caratteri speciali delle regex) e indirizzo senza badare alle
>   maiuscole; il resto del testo resta intatto.
> - Casi nuovi dell'host: `smtp.example.com:587` e `127.0.0.1:25` rifiutati, `fe80::1` e `2001:db8::25` validi.
>
> **Validazione finale** (corsia 6188, una alla volta, `nice`, nessun server; log `/tmp/libreFolio_e1final_*.log`):
>
> | Voce | Esito |
> |---|---|
> | `utils rate-window` | 26 ✅ |
> | `services email-config` | 144 ✅ |
> | `services email-messages` | 245 ✅ |
> | `services email-checks` | 48 ✅ |
> | `services email-delivery` | 77 ✅, 2 saltati (`EMD-017/018`, senza `cryptography`: E-1) |
> | `services config-package` | 599 ✅ |
> | `services config-env-example` | 36 ✅ |
> | `check-orphans` | ✅ (282 file backend raggiungibili) |
>
> - `ruff` e `black` puliti sui 16 file Python (black applicato a `test_email_delivery.py`, solo formato);
>   `git diff --check` pulito; porta 6188 libera; nessun server avviato in tutto il lotto.
> - **Non eseguiti qui**: `mkdocs build` stretto e `check-links` (finestra della galleria ancora aperta, nessun avviso
>   di fine): link e ancore della pagina nuova e delle tre pagine toccate verificati a mano; eseguiti poi in E1.7.
>   `all-backend`: non serve a un lotto che non tocca codice esistente, salvo le voci del runner; lo fa la validazione
>   combinata.
>
> **⚠️ Fuori pista**: `dev_release2` è andato avanti a `13705dd05` mentre lavoravo; il coordinatore ha riscritto la
> riga d'apertura della sezione E del backlog. Allineata la mia al suo testo, così all'aggiornamento di base resta da
> unire solo la voce E-1.

### Checkpoint E1 🧊 (2026-10-15) — FROZEN, in attesa del commit del coordinatore
> - **Base**: HEAD `23f6578f3`; `dev_release2` locale a `13705dd05`.
> - **Delta**, non in stage: 21 file nuovi e 8 modificati. Nuovi: il servizio (`config/email.py`, `services/email/`
>   con 5 moduli e 5 modelli, `utils/runtime/rate_window.py`), i test (5 file, il server finto), la pagina
>   `developer/backend/email.md`, questo piano. Modificati: `.env.example` (sezione «Email»), `.github/instructions/
>   backend.instructions.md` (3 righe), `developer/architecture/{settings,security}.md` e `developer/index.md` (un
>   passaggio ciascuno), `_backend_services.py` e `_backend_utils.py` (voci nuove, in aggiunta), la sezione E del
>   backlog.
> - **Conflitti attesi con `13705dd05`**: la riga d'apertura della sezione E del backlog (allineata al testo del
>   coordinatore); `_backend_utils.py`, blocchi vicini ma separati. Più avanti, con A5b: passaggi diversi di
>   `settings.md` e `security.md`.
> - **Commit proposti**: `feat(email): add optional SMTP email service core`; `docs(journal): E0-E1 email plan, E
>   backlog`.

#### E1.7 — Navigazione, `mkdocs build` stretto e `check-links` ✅ (2026-10-15)
> **Note implementazione**: via del coordinatore alle 13:03 (finestra della galleria chiusa alle 13:01), che autorizza la
> sola riga di navigazione in `mkdocs_src/mkdocs.yml`, sotto lo Scheduler: `"📧 Email (SMTP)":
> developer/backend/email.md`. Con `nice -n 10`:
> - `dev.py mkdocs build` (stretto): uscita 0 in 33,8 s, nessuna riga `WARNING` o `ERROR`, 3 020 URL relativi risolti,
>   pagina `site/developer/backend/email/index.html` prodotta (log `/tmp/libreFolio_e1_mkdocs_build.log`);
> - `dev.py mkdocs check-links`: 95 link validi, nessuno rotto (log `/tmp/libreFolio_e1_check_links.log`).
>
> `site/` è ignorata; nessun file tracciato cambiato dalla build; porte 6188 e 6042 libere.

#### E1.8 — Aggiornamento di base, validazione combinata, test TLS ✅ (2026-10-15)
> **Note implementazione**:
> - Checkpoint committato dal coordinatore: `2534cbd97` (codice, test, doc, navigazione) e `1e2f4b2f3` (journal).
> - Aggiornamento di base con `dev_release2` (`13705dd05`), aperto dal coordinatore nel mio worktree. Un conflitto,
>   `BACKLOG_POST_1.2.md`: tenuto il file di `dev_release2` più la sola voce E-1 (controllato con un diff contro
>   `MERGE_HEAD`), messo in stage solo lui. Controllati a mano i due fusi da soli: `_backend_utils.py` (le voci dei due
>   lati, AST valido) e `mkdocs.yml` (la riga dell'email e quella del Designer Lab, in punti diversi). Merge del
>   coordinatore: `fc99e9bfe`.
> - Validazione della revisione combinata, prima della pausa delle dipendenze (una alla volta, `nice -n 10`, log
>   `/tmp/libreFolio_e1merge_*.log`): `utils rate-window` 26, `services email-config` 144, `email-messages` 245,
>   `email-checks` 48, `email-delivery` 77 + 2 saltati, `config-package` 600, `config-env-example` 36, `utils
>   gate-i18n-usage` 195, `check-orphans` ✅.
> - Dopo la finestra delle dipendenze (`cryptography` 50.0.2, `dc9a5d232`), su `fc99e9bfe`: `services email-delivery`
>   **79 passati, nessun saltato**; `EMD-017` (STARTTLS, poi autenticazione, poi invio) ed `EMD-018` (certificato non
>   fidato → `TLS_FAILED`, nulla inviato) verdi. Log `/tmp/libreFolio_e1tls_email-delivery.log`. E-1 chiusa nel
>   backlog.

### E2 — stato e email di prova per l'admin (la parte senza A5a)

#### E2.0 — Via e ambiente ✅ (2026-10-15)
> **Note implementazione**: commit di E1 `2534cbd97`, `1e2f4b2f3`, merge di base `fc99e9bfe`, journal `918e8d4f0`; E1
> entra in `dev_release2` dopo CP6 di H. Via del coordinatore (13:37): «preparare E2 solo dove non serve A5a, con prove
> leggere». Risposte alle mie tre domande (13:40):
> - `npm ci` dal lock sì, poi `front build --debug` e `mkdocs build` una volta, con `nice -n 10`, uno alla volta;
> - la voce della scheda «Email» in `features/settings/settingsTabs.ts` la scrivo io nel checkpoint di E2, solo righe
>   aggiunte, **dopo** che A5 è nella mia base (avvisa il coordinatore);
> - la classificazione di `POST /email/test` nel file di CP6 di H (e il test che fissa l'elenco) la scrivo io, appena
>   CP6 è nella mia base.
>
> Fatto, uno alla volta con `nice -n 10`:
> - `npm ci --no-audit --no-fund` in `frontend/`: uscita 0 (log `/tmp/libreFolio_e2_npm_ci.log`); gli stessi avvisi
>   di A sugli script d'installazione (`esbuild`, `fsevents`, `es5-ext`), non approvati;
> - `dev.py front build --debug`: uscita 0, 8 minuti sotto carico (log `/tmp/libreFolio_e2_front_build_debug.log`);
> - `dev.py mkdocs build` sulla base fusa: uscita 0, nessuna riga `WARNING` o `ERROR`, 3 028 URL risolti.
>
> **⚠️ Fuori pista**: dalle 13:55 il carico della macchina è a 110–139; il coordinatore ammette solo test di un file
> (Vitest con `--maxWorkers 2`), niente build, `svelte-check` né categorie, fino al suo prossimo messaggio. Il codice
> si scrive, le prove aspettano.

#### E2.1 — Backend: `GET /email/status`, `POST /email/test` ✅ scritto (2026-10-15), prove ⏳
> **Note implementazione**:
> - `schemas/email.py`: `EmailCheckRead` (mai il `summary` del log, che può nominare il server), `EmailBudgetRead`,
>   `EmailStatusResponse` (`state` off/ready/invalid, `problem`, `variable`, `checks`, `budget` solo se pronta),
>   `EmailTestResponse` (`language`).
> - `api/v1/email.py`, `prefix="/email"`, `require_admin`: lo stato è un `def` (la configurazione può leggere il file
>   della password: gira nel pool di thread); la prova risponde 409 `EMAIL_UNAVAILABLE` con il `problem`, 429
>   `EMAIL_RATE_LIMITED` con `Retry-After`, 502 `EMAIL_DELIVERY_FAILED` con lo `smtp_code`, 422
>   `EMAIL_RECIPIENT_INVALID`. L'istanza nel testo è l'host della richiesta: è un'etichetta, nessun link (punto 45).
> - `services/email/flows.py`: `account_language` (la lingua dell'account, poi `default_language`, poi l'inglese; non
>   crea righe) e `send_test_email`.
> - `delivery.send_email`: la configurazione ora si legge con `asyncio.to_thread` (il file della password non si legge
>   più sul ciclo di eventi).
> - `api/v1/router.py` (condiviso): l'import e `include_router(email.router)`, due righe.
> - `ruff` e `black` puliti; l'OpenAPI ha le due rotte e i 4 schemi.
> - Test affidati a `test-author`: `test_api/test_email_api.py` (app nel processo su un SQLite privato, come i test di
>   A5a) e `test_services/test_email_flows.py`; `api email` aspetta il via sul carico (avvia il server condiviso).

#### E2.2 — Frontend: la scheda «Email» ✅ scritto (2026-10-15), prove ⏳
> **Note implementazione** (file nuovi, solo ruoli `*-lf-*`, nessuna classe di palette né colore scritto a mano):
> - `features/email/emailApi.ts` (la cucitura sul client generato, `readTestFailure`);
> - `features/email/emailText.ts` (codici → chiavi i18n e stati → classi, tutte stringhe intere, per l'audit i18n e le
>   guardie dei colori);
> - `features/email/EmailSettingsTab.svelte` (Svelte 5: stato, problema con la variabile, avvisi dei controlli che non
>   sono `ok`, invii rimasti, «Spedisci un'email di prova» con l'esito in linea; `data-busy`, `data-testid` e `data-*`
>   per i test; `notify` senza toast, perché l'esito si vede);
> - sorgente i18n nuova `lib/i18n/email/` (`prefixes.txt`: `email`), 41 chiavi nelle 4 lingue, in forma canonica,
>   stessi segnaposto (controllo usa e getta).
> - Aspettano: `api sync` (i tipi del client), `svelte-check`, `i18n check`, il Vitest della scheda, la riga del
>   registro (dopo A5), la pagina admin `admin/email.en.md` (`docs-writer`, in corso), la galleria.

#### E2.3 — Doc admin `admin/email.en.md` ✅ scritta (2026-10-15), build ⏳
> **Note implementazione**: `docs-writer` ha scritto la pagina (355 righe, solo EN): dove vive la configurazione, le
> variabili, i modi di cifratura, tre esempi a schede (Docker Compose con segreto, provider, relay locale), la scheda
> Impostazioni › Email, i problemi di configurazione e d'invio, il log, le note di sicurezza. Ho verificato sul codice:
> i messaggi del log, i 20 s per passo, i suffissi e gli intervalli locali, `secrets_set_twice` (generico su
> `LIBREFOLIO_*`: l'avviso «impostata due volte» c'è davvero all'avvio), il caricamento di `.env` da `dev.py`,
> l'utente `1000:1000` dell'entrypoint, il servizio `librefolio` dei compose, la riapertura dello stato dopo ogni prova.
> - Link a `configuration.md` **senza** àncore: le versioni IT/FR/ES di quella pagina non hanno ancora le sezioni
>   (`anchors: warn` + `--strict` farebbe fallire la build).
> - Corretti da me: l'introduzione della scheda (`email.tab.intro`, 4 lingue) non promette più reset, inviti e
>   attivazione, che arrivano con E3/E4; la riga `# Docs: mkdocs_src → admin/email.md` nella sezione Email di
>   `.env.example`; l'esito della prova si rende dallo stato (segue un cambio di lingua).
> - Chiesti a `docs-writer`: il rimando ad Advanced Docker per UID/GID diversi; il riallineamento della pagina
>   sviluppatore `developer/backend/email.md` a E2.
> - Da proporre al coordinatore (pagine condivise e tradotte): la riga di nav «Email: admin/email.md» sotto
>   «Environment Variables» con le `nav_translations` (IT «Email», FR «E-mail», ES «Correo»); una riga in
>   `admin/index.en.md`; in `configuration.en.md` (di H) «tre segreti» → quattro, con il file della password SMTP che
>   non ferma mai il server, e, dopo la registrazione in `CONFIG_CHECKS`, due righe nella tabella dei controlli d'avvio.

#### E2.4 — Test di E2a e correzioni dalla revisione di `test-author` ✅ scritti (2026-10-15), prove ⏳
> **Note implementazione**: `test-author` ha scritto `test_services/test_email_flows.py` (EMF-001…007) e
> `test_api/test_email_api.py` (EMA-001…016, nel processo su un SQLite privato, guardia su `getaddrinfo` che ammette
> solo il loopback) e le voci `services email-flows` e `api email` (entrambe `pure`, con la riga del motivo).
> `services email-flows`: 19 passati in 10,8 s (log `/tmp/libreFolio_e2a_email-flows.log`). `api email` aspetta il via
> sul carico (la categoria `api` avvia il server condiviso). `ruff` e `black` puliti sui 9 file.
>
> **⚠️ Fuori pista** — difetti trovati dalla revisione, corretti:
> - il 422 `EMAIL_RECIPIENT_INVALID` catturava ogni `ValueError` di `send_test_email`: una riga di `user_settings` che
>   non valida più (un tema vecchio) dava «indirizzo non valido». Ora un'eccezione propria,
>   `messages.EmailRecipientError(ValueError)`, e la rotta cattura solo quella;
> - `account_language` leggeva le impostazioni attraverso `UserSettingsRead` (validazione intera): ora legge la sola
>   colonna `language`; una lingua che non nomina nessuna delle quattro vale come assente (→ `default_language` →
>   inglese), come la lingua vuota. Nuovo `messages.supported_email_language`;
> - lo stato leggeva la configurazione quattro volte: `budget_status(max_per_hour)` riusa lo stato già letto.
> Test da adeguare affidati di nuovo a `test-author` (EMF-002 `unknown-de` → la lingua dell'istanza; riga con tema
> fuori elenco → 200; il contratto di `EmailRecipientError`).
>
> Esito (15/10, uno alla volta, `nice -n 10`, corsia 6188):
> - `services email-flows` 42/42, `email-messages` 245/245, `email-delivery` 79/79 (log `/tmp/libreFolio_e2a_*.log`);
> - `api email` 52/52 con `--no-shared-server`: per un'azione sola la categoria `api` non ripopola il DB
>   (`_api_setup` gira solo per `api all` e per il passo consolidato), e senza il server condiviso è una prova di un
>   file solo; la porta 6188 è rimasta libera (`lsof` vuoto). Log `/tmp/libreFolio_e2a_api_email.log`.
>
> **⚠️ Fuori pista**: il primo giro di `api email` dava un avviso di deprecazione di Starlette su
> `status.HTTP_422_UNPROCESSABLE_ENTITY`; nel file nuovo ora c'è `HTTP_422_UNPROCESSABLE_CONTENT` (stesso 422).
> Secondo giro: 52 passati, nessun avviso. Il vecchio nome resta solo in `api/v1/settings.py` (4 risposte): non è il
> mio perimetro, va nel backlog (E-4).
>
> Doc: corretti da me nella pagina sviluppatore la regola della lingua, `EmailRecipientError`, `budget_status`,
> gli EMF/EMA e «Coming next» secondo la tabella dei lotti (§5); aggiunta la riga `email` (19 sottosistemi) in
> `developer/frontend/i18n.md`.

#### E2.5 — Le 4 prove medie e i cancelli leggeri ✅ (2026-10-15)
> **Note implementazione**: via del coordinatore (14:50): «Sì alle 4 prove medie, in fila e con `nice -n 10`»; il
> checkpoint E2a va bene; le righe in `configuration.en.md` di H le scrivo io, dichiarandole. In fila, con
> `nice -n 10`:
> - `api sync`: uscita 0; il client generato ha `get_email_status_api_v1_email_status_get`,
>   `send_test_api_v1_email_test_post` e gli schemi `Email*` (file ignorati da git);
> - `i18n build` e `i18n check`: 4 433 chiavi × 4 lingue da 91 sorgenti, 19 sottosistemi, stretto, uscita 0;
> - `front check` (`svelte-check`): il primo giro dava 10 errori, tutti nella scheda (vedi sotto); dopo la
>   correzione, 0 errori e 0 avvisi;
> - `mkdocs build` (stretto): uscita 0, nessuna riga `WARNING` o `ERROR`; `admin/email.en.md` compare solo nella
>   riga INFO delle pagine fuori dalla nav, finché il coordinatore non aggiunge la riga;
>   `mkdocs check-links`: 96 link validi (95 + il `DocsLink` della scheda verso `admin/email/`);
> - cancelli leggeri: `services config-env-example` 36, `services config-package` 603 (639 sulla base del
>   coordinatore, che ha CP6), `utils gate-i18n-usage` 195, `check-orphans` verde, Vitest
>   `src/themeRoles.gate.test.ts` 36 con `--maxWorkers 2`. Tutti i 25 ruoli `lf-*` dei file nuovi sono dichiarati in
>   `tokens.css`. Log `/tmp/libreFolio_e2a_*.log`.
>
> **⚠️ Fuori pista**: il tipo TypeScript generato per un campo facoltativo (`anyOf [string, null]`) è
> `(string | null) | Array<string | null>`, più largo dello schema zod a runtime (che è giusto). Lo stesso schema c'è
> in altre 315 righe del client: chi lo legge stringe il tipo dove lo usa (`ProfileTab`: `typeof === 'string'`).
> Qui `emailApi.fetchEmailStatus()` normalizza una volta sola la risposta in `EmailStatus` (`problem` e `variable`
> stringa o `null`, `checks` sempre lista, `budget` oggetto o `null`); la scheda legge solo il tipo pulito.
> Il `test-author` della scheda è stato avvisato del contratto nuovo.

#### E2.6 — Vitest della scheda e difetti trovati ✅ (2026-10-15)
> **Note implementazione**: un secondo `test-author` ha scritto `emailText.test.ts` (94 casi, node),
> `emailApi.test.ts` (42, node; il client vero con il solo trasporto finto) ed `EmailSettingsTab.test.ts` (25,
> jsdom), registrati in `front-utility core-unit` e `component-unit` (righe aggiunte, più una frase nelle `desc`).
>
> **⚠️ Fuori pista** — difetti trovati dai test, corretti:
> - **alto**: il client generato rifiuta con l'`AxiosError` di axios (l'intercettore lo lascia passare), non con
>   `ApiError`, che nessuno costruisce; `readTestFailure` leggeva solo `ApiError`, quindi ogni 409/429/502/422 sarebbe
>   apparso come errore generico. Ora `refusalBody()` legge `isAxiosError(error) ? error.response?.data`, come
>   `ProfileTab`, `tools/client.ts` e `aiExportClient.ts`, e regge anche `ApiError`;
> - `problemKey`/`testFailureMessage` cercavano nelle mappe anche i nomi ereditati (`constructor`): ora
>   `Object.hasOwn`;
> - la scheda: `data-busy` copre anche l'invio; il pulsante è spento mentre gira una richiesta qualsiasi (anche la
>   rilettura dopo la prova: un clic, un'email); solo l'ultima lettura scrive (contatore di generazione); una
>   rilettura fallita mostra l'errore sopra l'ultimo stato e lascia l'esito della prova.
> - Decisione: il pulsante resta acceso quando il budget mostrato è finito (il budget è per processo; il 429 lo
>   dice chiaro).
> - Doc sviluppatore allineata (sezione «The Email Tab»). `prettier --check` pulito sui file della scheda.
>
> Esito, uno alla volta con `nice -n 10`, Vitest con `--maxWorkers 2`: `emailText.test.ts` 106, `emailApi.test.ts` 62
> (i quattro rifiuti col client vero, rossi prima della correzione, ora verdi), `EmailSettingsTab.test.ts` 29;
> `prettier --check` pulito; `check-orphans` verde (394 file di unità del frontend registrati); `front check`
> (`svelte-check`, test compresi) 0 errori e 0 avvisi. Log `/tmp/libreFolio_e2a_vitest_*.log`,
> `/tmp/libreFolio_e2a_svelte_check2.log`.
> - Non fissato da un test: il contatore di generazione di `load()`. Dalla scheda due letture non si sovrappongono
>   mai (la prima gira prima che esista il pulsante, la prova parte solo a scheda ferma): è difesa, documentata
>   nell'intestazione del test.
> - Decisione: nessun pulsante «riprova» dopo una prima lettura fallita: la pagina Impostazioni monta solo la scheda
>   attiva (`<active.component>` in `routes/(app)/settings/+page.svelte`), quindi cambiare scheda e tornare rilegge.

### Checkpoint E2a 🧊 (2026-10-15) — FROZEN, in attesa del commit del coordinatore
> **Base**: HEAD `918e8d4f0` (E1 chiuso; `dev_release2` è a `f46a93ffd`, con E1, CP6 di H, FE5b di X e
> `cryptography`). Delta: 12 file tracciati modificati, 17 nuovi.
>
> **Giro finale sull'albero di E2a** (corsia 6188, `/tmp/librefolio-r13-e`, uno alla volta, `nice -n 10`):
> `services email-config` 144, `email-messages` 245, `email-delivery` 79, `email-checks` 48, `email-flows` 42;
> `api email` 52 (`--no-shared-server`); `services config-env-example` 36, `config-package` 603;
> `utils gate-i18n-usage` 195; `check-orphans` verde; Vitest 106 + 62 + 29 e `themeRoles.gate` 36; `front check` 0/0;
> `i18n build` + `check` (stretto, 19 sottosistemi); `api sync`; `mkdocs build` stretto senza `WARNING`/`ERROR`;
> `check-links` 96 validi; `prettier --check`; `ruff` e `black` puliti; `git diff --check` pulito; porta 6188 libera.
>
> **Resta per E2b** (dopo la base con CP6 e A5): `EMAIL_CONFIG_CHECKS` in `CONFIG_CHECKS` (più le due righe nella
> tabella dei controlli d'avvio di `configuration.en.md` e il paragrafo «A secret … stops the start»); la
> classificazione di `POST /email/test` nell'elenco di CP6 e il suo test; la voce della scheda in `settingsTabs.ts`
> con `email.tab.label`; `/system/instance.email`; l'E2E simulato; la galleria; il testo del CHANGELOG (la scheda
> diventa visibile solo allora).

### E2b — registrazioni dopo la base con CP6, A5 e i colori

#### E2b.0 — Base e via ✅ (2026-10-15)
> **Note implementazione**: E2a committato dal coordinatore (`b33654f22`, `c1d1c3c2d`). Merge di base aperto dal
> coordinatore (`dev_release2` `d22eb6f43`: CP6 di H, A5, W, J, i colori), un conflitto in
> `scripts/test_runner/_frontend_utility.py` (lista Vitest di `core-unit`): uniti i due lati, le 7 righe di
> `dev_release2` e poi le mie 2, nessun percorso doppio nuovo (310 + 3 = 313); in stage solo quel file. Merge
> committato: `d42b4c32f`. Giro sulla revisione unita, tutto verde (vedi messaggio al coordinatore):
> `utils rate-window` 26, `gate-i18n-usage` 195, `services email-*` 144/245/79/48/42, `config-package` 645,
> `config-env-example` 36, `api email` 52, `check-orphans`, `api system` 117 (con il server condiviso: il prerequisito
> ha ricostruito frontend e doc in 358 s; avviso esterno: lo scarico di MathJax da jsDelivr fallisce per SSL).
>
> Via del coordinatore per E2b (15:25 e 16:57): la riga `CONFIG_CHECKS`, la classificazione CP6, la voce Email in
> `settingsTabs.ts` (solo righe aggiunte), la riga di nav con le tre `nav_translations`, la riga in
> `admin/index.en.md`, `/system/instance.email`, le E2E (in coda per uno slot pesante), la riga del CHANGELOG, il conto
> dei sottosistemi di `developer/frontend/i18n.md` corretto a 20.
>
> **⚠️ Fuori pista**:
> - nel merge, `developer/frontend/i18n.md` aveva da entrambi i lati «18 → 19» (`liveUpdates` loro, `email` mio):
>   git ha tenuto 19, i sottosistemi sono 20; il loro lato cambiava anche «(18)» nell'albero in cima, che io avevo
>   lasciato. Corretto in E2b, non nel merge;
> - CP6 è un elenco di **permessi** (`ALLOWED_WHEN_BLOCKED`): ogni rotta di `/api/v1` fuori elenco risponde 423 su
>   un'istanza bloccata. Le due rotte email sono quindi già rifiutate, come vuole il piano (niente invii a istanza
>   bloccata): nessuna riga in `instance_block.py` né nel test che fissa l'elenco (aggiungerle vorrebbe dire
>   permetterle). Le copre il test di H che percorre ogni rotta
>   (`test_every_route_under_api_v1_is_an_api_route_resolving_the_block_first`).

#### E2b.1 — Backend: `CONFIG_CHECKS` e `/system/instance.email` ✅ scritto (2026-10-15), test ⏳
> **Note implementazione**:
> - `services/email/checks.py` non importa più `config_audit` a livello di modulo: ogni controllo importa
>   `ConfigCheck` quando gira (più un import sotto `TYPE_CHECKING` per l'annotazione). Così `config_audit` (di H)
>   importa `EMAIL_CONFIG_CHECKS` e chiude `CONFIG_CHECKS` con `*EMAIL_CONFIG_CHECKS` (2 righe più un commento):
>   all'avvio `log_configuration_audit()` scrive `email.smtp` (`error`) e `email.smtp_encryption` (`warning`); per
>   l'email non ferma mai l'avvio. Provato l'ordine d'import nei due sensi, più `api.v1.email` e `main` per primi.
>   L'import «come modulo» di E1 bastava solo in un verso: con `email.checks` caricato per primo, `config_audit` avrebbe
>   trovato `EMAIL_CONFIG_CHECKS` non ancora definito.
> - `/system/instance` (file di H): `email: EmailInstanceConfig` (`schemas/email.py`, `available: bool = False`;
>   in `schemas/system.py` con `default_factory`, quindi facoltativo nell'OpenAPI: i finti di `/system/instance` di
>   altri test restano validi e `DEFAULT_INSTANCE_CONFIG` del frontend non cambia), riempito in
>   `api/v1/system/instance.py` con `await asyncio.to_thread(delivery.email_available)`. Nessun consumatore nel
>   frontend fino a E3/E4.
> - Classificazione CP6: nessuna riga (vedi E2b.0).
> - `ruff`/`black` puliti; `api sync`: `InstanceConfigResponse.email?: EmailInstanceConfig`.

#### E2b.2 — Frontend: la scheda nel registro ✅ scritto (2026-10-15), test ⏳
> **Note implementazione**: `features/settings/settingsTabs.ts` (di A), solo righe aggiunte:
> `import {Mail} from 'lucide-svelte';` (riga a sé, per non toccare quella delle icone di A),
> `import EmailSettingsTab from '$lib/features/email/EmailSettingsTab.svelte';` e la voce
> `{id: 'email', labelKey: 'email.tab.label', icon: Mail, order: 110, component: EmailSettingsTab,
> visible: (ctx) => ctx.isSuperuser}` dopo `admin` (gruppo di destra). `email.tab.label`: Email / Email / E-mail /
> Correo. Il test di A che fissa le schede (`settingsTabs.test.ts`), l'E2E `e2e/settings/email-tab.spec.ts` e lo
> scatto della galleria sono affidati a `test-author`; E2E e galleria girano nello slot pesante che assegna il
> coordinatore.

#### E2b.3 — Doc e CHANGELOG ✅ scritto (2026-10-15)
> **Note implementazione**: nav (`Email: admin/email.md` sotto «Environment Variables», `nav_translations` IT «Email»,
> FR «E-mail», ES «Correo»); `admin/index.en.md` (la riga Email); `admin/configuration.en.md` (di H): le due righe dei
> controlli d'avvio e «Some secrets you configured stop the start instead…» (la frase di prima diceva che ogni
> segreto illeggibile ferma l'avvio: non vale per la chiave della ricerca web né per la password SMTP);
> `developer/frontend/i18n.md`: 20 sottosistemi nei due punti; CHANGELOG, `[Unreleased]` › «✨ Added»: la voce
> «Email, optional». Le pagine `admin/email.en.md`, `developer/backend/email.md` e
> `developer/frontend/components/features/settings.md` sono affidate a `docs-writer`.
>
> `docs-writer` (E2b): `admin/email.en.md` (i controlli all'avvio: due righe nel log, quella di `_report_invalid` e
> quella del controllo; la scheda dopo Admin, solo per gli amministratori; un punto su `/api/v1/system/instance`, che
> dice solo se l'email è pronta), `developer/backend/email.md` (registrazione in `CONFIG_CHECKS` e import pigro,
> parte nuova `#instance-email`, la scheda registrata, «Coming Next»),
> `developer/frontend/components/features/settings.md` (cinque schede, la riga `email`). Corretti da me, perché
> resi falsi dal lotto: in `developer/architecture/settings.md` (di H) «two fields» → «three» e la riga `email`;
> in `developer/architecture/security.md` (di H) il file della password SMTP «from a later lot» → mostrato in
> Impostazioni › Email, e «publishes only the registration mode» → «About accounts, … publishes only…».

#### E2b.4 — Test di E2b ✅ (2026-10-15)
> **Note implementazione** — frontend (`test-author`):
> - `settingsTabs.test.ts` (di A): mock del corpo Email, la riga Email in `TODAY`, le schede attese per contesto
>   (utente: profile, preferences, about, admin; amministratore: le stesse e poi email), il caso «email is visible to
>   administrators only and takes no props»; titoli senza «four». 18 passati.
> - `page.tabs.test.ts` (di A): un mock in più (il corpo Email), perché le sue schede finte stanno sul modulo vero del
>   registro, che ora importa la scheda Email. 18 passati (prima del mock il file non si caricava).
> - Nuovi: `e2e/settings/email-tab.spec.ts` (5 test: amministratore e utente sul backend vero, stato `off` come
>   precondizione esplicita; tre flussi con API finte 200/502/429) e la voce `front-utility email-tab`; nella
>   galleria lo scatto `settings/email` dopo «global settings (admin)», con lo stato `ready` finto. Non lanciati:
>   aspettano lo slot pesante.
> - Vitest: `EmailSettingsTab` 29, `emailApi` 62, `settingsTabs` 18, `page.tabs` 18; `prettier --check` pulito.
>
> **⚠️ Fuori pista**: dopo `api sync` il client generato non si caricava più (`TypeError: "The email part of " is not
> a function`): `openapi-zod-client` scrive una descrizione su più righe come template literal senza sfuggire i
> backtick, e la docstring di `EmailInstanceConfig` era su più righe con ``` ``GET /system/instance`` ```. Corretto con
> una docstring su una riga (la spiegazione del default è passata in un commento). Nel backlog: E-5 (il generatore) ed
> E-6 (ogni nuova scheda obbliga i test del registro a un mock in più).
>
> **Note implementazione** — backend (`test-author`):
> - `test_email_checks.py`: EMK-010…015 (i due controlli chiudono `CONFIG_CHECKS`; `run_config_checks()`; i tre
>   ordini d'import in un interprete nuovo; il registro d'avvio: un `error` `email.smtp` senza eccezione, un
>   `warning` `email.smtp_encryption`, niente a email spenta, mai la password). 64 passati.
> - `test_email_api.py`: EMA-019…022 (`/system/instance` senza sessione, `email` esattamente `{available}` in 8
>   stati, mai un valore della configurazione né una ricerca di nomi, il file della password fuori dal ciclo di
>   eventi, `available: false` per una risposta costruita senza). 63 passati.
> - File di H: `test_config_audit.py` (l'import dei due controlli, le due voci di `CHECK_IDS`, in `_configure` la
>   rimozione di ogni `LIBREFOLIO_SMTP_*`): 90 passati; `test_system_api.py` (le chiavi esatte di
>   `/system/instance` con `email`, dal vivo e nel processo): 117 passati. File di A: `test_registration_api.py`
>   (INSTANCE-002, le chiavi esatte): 65 passati.
>
> **⚠️ Fuori pista**: il primo giro di `api registration` dava un rosso
> (`test_an_invitation_opens_its_account_and_is_consumed_by_it`: l'invitato risultava amministratore). Causa: le
> prove `services` ricreano vuoto il DB della corsia, e su un'istanza senza amministratore il primo account lo
> diventa; `api all` ripopola il DB (`_api_setup`), un'azione sola no. Dopo
> `db populate --force` sulla corsia (`/tmp/librefolio-r13-e`): 65 passati. Nessun difetto del prodotto né del lotto.

#### E2b.5 — Giro finale ✅ (2026-10-15)
> Corsia 6188, una prova alla volta, `nice -n 10`, log `/tmp/libreFolio_e2b_*.log`:
> `services email-config` 144, `email-messages` 245, `email-delivery` 79, `email-checks` 64, `email-flows` 42,
> `config-audit` 90, `config-env-example` 36, `config-package` 645; `utils rate-window` 26, `gate-i18n-usage` 195;
> `api email` 63 (`--no-shared-server`), `api system` 117, `api registration` 65, `api instance-block` 44 (su DB
> ripopolato); `check-orphans` verde (124 spec, 413 file di unità); Vitest `EmailSettingsTab` 29, `emailApi` 62,
> `settingsTabs` 18, `page.tabs` 18; `i18n build` + `check` (4 464 chiavi, 20 sottosistemi, stretto); `front check`
> 0/0; `prettier --check`; `api sync`; `mkdocs build` stretto senza `WARNING`/`ERROR` (e `admin/email` ora nella
> nav); `check-links` 96 validi; `ruff`/`black`; `git diff --check`; porta 6188 libera.
> Non lanciati: l'E2E `front-utility email-tab` e lo scatto `settings/email` della galleria (slot pesante del
> coordinatore).

### Checkpoint E2b 🧊 (2026-10-15) — FROZEN, in attesa del commit del coordinatore
> **Base**: HEAD `d42b4c32f`. Delta: 34 file tracciati modificati, 1 nuovo (`e2e/settings/email-tab.spec.ts`).
> Righe nei file altrui dichiarate nel messaggio di consegna. Resta di E2: far girare l'E2E e lo scatto della galleria
> nello slot che assegna il coordinatore, poi la pagina admin può mostrare lo scatto.
