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

- **Regola fissa (15/10)**: ogni lotto che tocca `frontend/src/lib/i18n/email/` fa girare anche `front-utility core-unit`
  (gate di markup, ICU e lingua) e `i18n check`.

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

#### E2b.6 — Base `da3e06e1c` e tre correzioni ✅ (2026-10-15)
> **Note implementazione**: E2b committato (`fab8e2d09`, `f4f995ce7`). Merge di base aperto dal coordinatore
> (`dev_release2` `a718e5281`: A6a, H billing e link, Z7a, J, il banner del Lab), un conflitto in
> `scripts/test_runner/_backend_services.py`: due funzioni nello stesso punto, tenute entrambe (`services_email_flows`,
> poi `services_provider_cooldown`), nessun nome doppio (105 azioni); in stage solo quel file. Controllati i file fusi
> da git: `billing_url` di H sta in `InstanceBlockResponse`, `/system/instance` resta `{profile, accounts, email}`;
> `*EMAIL_CONFIG_CHECKS` resta l'ultima riga; `security.md`, `configuration.en.md`, CHANGELOG con i due lati.
> Merge committato: `da3e06e1c`.
>
> Le tre correzioni chieste dal coordinatore (dopo A6b di A):
> 1. ordine della scheda Email **130** (110 è Users di A6b, 120 Backup di B): `settingsTabs.ts` e le due pagine
>    sviluppatore che lo citavano;
> 2. lo scatto `email (admin)` contro la checklist di G (via `test-author`): rotta registrata prima della navigazione,
>    solo `GET` del suo path, il resto `route.fallback()`, nessun `unroute`, corpo validato con
>    `schemas.EmailStatusResponse.parse` in un file nuovo `e2e/fixtures/galleryEmail.ts`, i passi e la cornice di G,
>    tolti gli attesi in più già coperti da `screenshot()`. Lo stesso filtro di metodo e la stessa validazione
>    nell'E2E `email-tab.spec.ts`;
> 3. CHANGELOG: tolta la mia voce (superficie del coordinatore), il testo va nel messaggio.
>
> Prove, una alla volta con `nice -n 10`: `api sync`; `front check` 0/0; `api system` 117, `api instance-block` 54,
> `services config-audit` 90; Vitest `settingsTabs` 18, `page.tabs` 18; `check-orphans` (124 spec, 413 unità);
> `tsc -p tsconfig.e2e.json` con i soli 2 errori di base (`onboarding-tour.spec.ts:863`, `src/lib/types/files.ts:9`);
> `prettier --check`. **Slot pesante 1**: `front-utility email-tab` con `--workers 2`: 5 passati in 34 s; porta 6188
> libera prima e dopo. Log `/tmp/libreFolio_e2b2_*.log`. Resta lo scatto della galleria, due volte con il diff vuoto,
> nello slot che assegna il coordinatore.

### E3 — le email con un link

#### E3.0 — Via, decisioni e disegno ✅ (2026-10-15)
> **Note implementazione**: E2 entrato in `dev_release2` (`755158aad`, CHANGELOG `6c427eb4e`); avanzamento veloce del
> mio ramo a `6c427eb4e`. Via del coordinatore (18:28): «Via a E3–E5, nell'ordine del tuo piano, con le decisioni 44 e
> 45 e il contratto della sonda concordato con A. L'helper di A arriva con A6b, verso le 19:30–19:45: la parte della
> scheda che lo usa falla dopo».
>
> **Decisioni del developer** (15/10, 17:55):
> - **44 (D-E7) approvata**: chi si è registrato e prova il login prima di cliccare il link vede «verifica la tua email»,
>   con «rispedisci» (E5).
> - **45 (D-E3), l'alternativa**: ogni link dentro un'email, anche quelle mandate dall'admin, si costruisce solo con
>   `LIBREFOLIO_PUBLIC_URL`; senza la variabile non partono email con link; i link copiati dalla UI restano come oggi.
>   Il controllo lo fa il browser dell'admin con la sonda di A6a (`POST /users/address-probe`, poi
>   `GET <PUBLIC_URL>/api/v1/auth/address-probe?nonce=…`); l'avviso dice che vale per questo dispositivo (DNS o rete).
>
> **Contratto con A** (risposta di A, 15/10): l'helper è `frontend/src/lib/features/settings/users/addressProbe.ts`
> (A6b), TS puro: `normalizeBase(input): string | null`, `checkAddress(base, {issueNonce, fetchImpl?, timeoutMs?})
> → 'match' | 'mismatch' | 'unverifiable'`, mai eccezioni; il nonce lo passo io (`issue_address_probe_…_post`). Una
> pagina HTTPS verso `http://` la controllo prima. `LIBREFOLIO_PUBLIC_URL` nel browser non c'è: la base la dà
> `/email/status`. Le azioni in più dei link: `users/linkShareActions.ts` (`LINK_SHARE_ACTIONS`, props
> `{link, purpose, context}`).
>
> **Disegno di E3** (backend ora; la scheda con la sonda dopo A6b; l'attivazione dell'admin dopo A7, che porta F02):
> - `services/email/links.py`: `links_state()` (`ready`, `base`, `problem`: `PUBLIC_URL_MISSING` o
>   `PUBLIC_URL_INVALID`), `email_link(purpose, token)` solo con `public_link(token_path(…))` di A, l'etichetta
>   dell'istanza nelle email = l'host di `LIBREFOLIO_PUBLIC_URL` (niente che venga dalla richiesta).
> - `POST /email/links` (admin, D-E10/D-E15): riceve il token in chiaro che le rotte di A gli hanno appena dato
>   (nel corpo, mai nel log), lo verifica per il suo scopo (`inspect_token`: solo `valid`), costruisce il link da sé,
>   e spedisce: l'invito all'indirizzo scelto dall'admin (o a quello dell'invito), il reset solo all'email
>   dell'account. Lingua: invito → quella chiesta (la UI dell'admin), poi `default_language`; reset → la lingua
>   dell'account. Errori: 409 `EMAIL_UNAVAILABLE`, 409 `EMAIL_LINKS_UNAVAILABLE`, 409 `EMAIL_LINK_INVALID` (con lo
>   stato), 422 sul destinatario, 429, 502.
> - `POST /email/password-reset` (anonimo, D-E16): 409 se l'email o i link non sono pronti (dipende solo dalla
>   configurazione, che `/system/instance` già pubblica); limiti prima di ogni ricerca: per indirizzo
>   (`request.client.host`, cioè la vista di uvicorn che rispetta `FORWARDED_ALLOW_IPS`; un `X-Forwarded-For`
>   falsificato non lo sposta) 5 ogni 15 minuti, per identificativo scritto (minuscolo) 3 l'ora, budget d'istanza
>   finito → 429 per tutti; poi **202** sempre uguale e il lavoro in background con una sessione propria: ricerca come
>   il login, account attivo, al più un reset ogni 5 minuti e 3 l'ora contati sulle righe dei token (in silenzio),
>   `create_password_reset` di A, email nella lingua dell'account.
> - `/system/instance.email` (D-E17): costruito da una sola funzione mia, `email_instance_config()` (una riga di H
>   cambia una volta, i campi futuri non la toccano più), con `links` (email pronta e link pronti): servirà al login
>   per offrire «password dimenticata» (E4).
> - `/email/status` (D-E18): `links: {ready, base, problem}`, solo admin: la base serve alla sonda della scheda.

#### E3.1 — Backend dei link per email ✅ scritto (2026-10-15), test ⏳
> **Note implementazione**:
> - Nuovo `services/email/links.py`: `links_state()` / `require_links()` (`LIBREFOLIO_PUBLIC_URL` pronta, mancante o
>   non valida; `EmailLinksUnavailableError`), `email_link(purpose, token)` con `public_link(token_path(…))` di A,
>   `LinksState.instance` (l'host della base, con la porta), `email_instance_config()` (la parte email di
>   `/system/instance`: `available` e `links`).
> - `services/email/flows.py`: `instance_language()`; `send_link_email()` (l'email di un link appena creato
>   dall'admin: `inspect_token` solo `valid`, invito a `to` o all'indirizzo dell'invito nella lingua chiesta o
>   dell'istanza, reset solo all'email dell'account nella sua lingua; errori `EmailLinkInvalidError`,
>   `EmailRecipientRequiredError`, `EmailRecipientNotAllowedError`); `admit_forgotten_password()` (configurazione,
>   poi i limitatori per indirizzo 5/15 min e per identificativo 3/h, poi il budget d'istanza letto senza spenderlo);
>   `forgotten_password_work()` (in background, sessione propria sul motore della richiesta, ricerca come il login,
>   account attivo, al più un reset ogni 5 minuti e 3 l'ora contati su tutte le righe di reset dell'account,
>   `create_password_reset` di A, email; ogni esito in silenzio nel log, senza l'identificativo, mai eccezioni).
> - `api/v1/email.py`: `GET /email/status` con `links`; `POST /email/links` (admin); `POST /email/password-reset`
>   (anonimo, 202 sempre uguale, il lavoro in `BackgroundTasks`; i 409 anonimi senza il `problem`).
> - Schemi nuovi in `schemas/email.py`, ciascuno con una docstring su una riga (E-5): `EmailLinksRead` (in
>   `EmailStatusResponse.links`, con default), `EmailInstanceConfig.links`, `EmailLinkRequest`/`Response`,
>   `PasswordResetEmailRequest`, `PasswordResetEmailAccepted`.
> - `api/v1/system/instance.py` (H): `email=await asyncio.to_thread(email_instance_config)`; tolti l'import di
>   `EmailInstanceConfig` e `email_available` (che sparisce da `delivery.py`): un campo futuro non tocca più il file.
> - `.env.example`, sezione Email: tre righe di commento su `LIBREFOLIO_PUBLIC_URL`.
> - `ruff`/`black` puliti; l'import funziona con `email.links`, `main` e `config_audit` per primi.

#### Correzione fuori lotto — un rosso di E2 in `dev_release2` ✅ (2026-10-15)
> **Note implementazione**: T dei colori ha trovato `core-unit` a 4 880 verdi su 4 881 in `dev_release2`:
> `src/htmlInterpolation.gate.test.ts` («finds no markup in any translation outside the reviewed sanit…») sulla chiave
> `email.problems.SMTP_FROM_INVALID`, il cui esempio `LibreFolio <noreply@example.com>` porta un `<` (il gate vieta ogni
> `<` nei cataloghi: alcune traduzioni finiscono in HTML fatto a mano senza `escapeHtml`). Riformulata nelle 4 lingue
> senza `<` né `>` («… such as noreply@example.com, optionally after a name, with the address in angle brackets»),
> invece di aggiungerla all'elenco rivisto del gate. Prove: il gate da solo 26/26; `front-utility core-unit` intero
> nello slot pesante 1: 153 file, 4 863 test verdi; `i18n build` + `check` stretti; `prettier --check`.
>
> **⚠️ Fuori pista / lezione**: un lotto che cambia i cataloghi i18n fa girare anche `front-utility core-unit` (i gate
> di markup, ICU e lingua stanno lì): da ora è nelle mie prove fisse (§9) ogni volta che tocco `lib/i18n/email/`.

#### E3.2 — Il terzo controllo, `email.links` ✅ scritto (2026-10-15), test ⏳
> **Note implementazione**: dalla revisione di `docs-writer`: con l'email pronta, una `LIBREFOLIO_PUBLIC_URL`
> mancante o sbagliata non diceva niente da nessuna parte (né all'avvio né nella scheda). Nuovo
> `checks.check_email_links` (id `email.links`), terzo in `EMAIL_CONFIG_CHECKS` e quindi in fondo a `CONFIG_CHECKS`:
> `ok` con l'email spenta o i link pronti; `info` («emails work, but none with a link can go out») con la variabile
> mancante; `warning` con un valore non http(s). Importa `links_state` solo quando gira (come `ConfigCheck`), così
> `config_audit` non tira dentro i servizi degli account all'import. Chiavi `email.checks.links.{ok,missing,invalid}`
> nelle 4 lingue, senza `<` né `>`; la scheda le mostra fra gli avvisi senza cambiare codice. Provati i quattro stati
> (con `email_instance_config()` accanto). Test e doc affidati (`test-author`: EMK, `CHECK_IDS` di H; `docs-writer`:
> pagine email e `configuration.en.md`).
>
> Decisioni sulle altre osservazioni di `docs-writer`: un link di reset non accetta `to` (E4 non lo manderà); una
> richiesta «password dimenticata» revoca anche un link di reset dell'admin vecchio di più di 5 minuti (è la semantica
> di `create_password_reset` di A; la regola dei 5 minuti protegge un link appena dato): voluto, documentato, da
> guardare nella revisione di sicurezza finale.

#### E3.3 — Test di E3 e quattro correzioni dalla revisione di `test-author` ✅ scritte (2026-10-15), prove ⏳
> **Note implementazione**: `test-author` ha scritto `test_services/test_email_links.py` (EML-001…010, voce nuova
> `services email-links`, pure), EMF-011…031, EMK-016/017 e gli adattamenti a tre controlli, EMA-023…041 (ogni link
> confrontato con quello di `LIBREFOLIO_PUBLIC_URL` mentre la richiesta porta Host, Origin, X-Forwarded-Host e
> Referer falsi); `CHECK_IDS` di H con `check_email_links`; in `test_system_api.py` di H le righe 880 e 913
> (`set(body["email"]) == {"available", "links"}`). Primo giro: `email-links` 30, `email-flows` 91, `api email` 137,
> `email-checks` 79, `config-env-example` 36, `config-audit` 90.
>
> **⚠️ Fuori pista** — difetti trovati, corretti:
> - una `LIBREFOLIO_PUBLIC_URL` malformata contava come pronta (`public_url()` di A guarda solo il prefisso): con
>   `https://` o un indirizzo con uno spazio, `POST /email/links` rispondeva 500 e «password dimenticata» creava una
>   riga di reset e falliva in silenzio. Ora `links_state()` valida la base (`_usable_base`: http(s), un host, niente
>   spazi, query o frammento), ed `email_link()` passa da `require_links()`;
> - `forgotten_password_work()` creava la riga di reset (revocando i link vivi) prima di sapere se l'email poteva
>   partire: ora riverifica configurazione, link e budget prima di crearla, e revoca il token nuovo se l'invio fallisce;
> - D-E13 «un'istanza bloccata non spedisce niente» valeva solo per le rotte (CP6): ora `send_email()` rifiuta per primo
>   con `INSTANCE_BLOCKED`, anche con un `LIBREFOLIO_BLOCKED` illeggibile;
> - senza indirizzo del client (socket unix) il limite per indirizzo sarebbe stato un conteggio unico per tutti: ora
>   in quel caso si salta, restano i limiti per identificativo, per account e il budget.
> - Osservato, lasciato: un admin può spedire il link di reset di un account disattivo (A crea quei link); «password
>   dimenticata» li salta. `black` segnala una riga di A in `_backend_services.py` (preesistente, non mia).
>
> Secondo giro con le correzioni: `email-links` 52, `email-flows` 98, `email-delivery` 97, `email-checks` 84,
> `api email` 145, `config-audit` 90, `api system` 117 (le righe 880/913 di H girate e verdi; porta libera).
>
> **⚠️ Fuori pista** — altri quattro casi trovati da `test-author`, corretti:
> - `_usable_base` rifiuta anche un `?` o un `#` vuoti in fondo (inghiottirebbero il percorso), una porta non valida
>   (letta in un `try`) e le credenziali nell'indirizzo (finirebbero in ogni link e nel testo dell'email); un IPv6 fra
>   parentesi resta valido;
> - `delivery.sending_blocked()` (bloccata, o `LIBREFOLIO_BLOCKED` illeggibile) vale per `send_email` e per
>   `flows._require_email()`: su un'istanza bloccata nessuna riga di reset viene creata, nessun link revocato;
> - il `try` dopo il commit del link copre ogni errore (`Exception`: rollback, revoca del token nuovo, commit) e
>   comprende `account_language()`;
> - `/system/instance` dice `available` e `links` falsi a istanza bloccata (la pagina di login non offrirà «password
>   dimenticata» a vuoto).
> Gate i18n come file singoli: `htmlInterpolation.gate` 26, `catalogIcuLocale` 17, `emailText` 106.
>
> Terzo giro, dopo i quattro casi: `email-links` 71, `email-delivery` 104 verdi; `email-flows` 4 rossi e `api email`
> 5 rossi, tutti sulla revoca del token dopo un invio fallito.
>
> **⚠️ Fuori pista**: la correzione «ogni errore revoca» aveva un difetto: il `session.rollback()` scade ogni oggetto
> caricato, e rileggere `issued.record.id` nel gestore chiede un refresh che la sessione asincrona rifiuta
> (`MissingGreenlet`): il gestore stesso crollava, e il link restava vivo. `test-author` l'ha visto con una
> riproduzione usa e getta. Ora l'id si legge subito dopo il commit (`token_id`). `email-flows` 104 e `api email`
> 154 verdi.

#### E3.4 — Giro finale ✅ (2026-10-15)
> Corsia 6188, una prova alla volta, `nice -n 10`, log `/tmp/libreFolio_e3f_*.log`: `services email-config` 144,
> `email-messages` 245, `email-delivery` 104, `email-checks` 84, `email-flows` 104, `email-links` 71, `config-audit` 90,
> `config-package` 649, `config-env-example` 36; `utils rate-window` 26, `gate-i18n-usage` 195; `api email` 154
> (`--no-shared-server`), `api system` 117, `api instance-block` 54 (su DB ripopolato); `check-orphans` verde;
> `front check` 0/0; `i18n build` + `check` (4 485 chiavi, 20 sottosistemi, stretto); Vitest `EmailSettingsTab` 29,
> `emailApi` 62, `htmlInterpolation.gate` 26, `catalogIcuLocale` 17, `emailText` 106; `prettier --check`;
> `mkdocs build` stretto senza `WARNING`/`ERROR`, `check-links` 96; `ruff`/`black` sui file miei; `git diff --check`;
> porta 6188 libera. Manca `front-utility core-unit` intero (i cataloghi i18n sono cambiati): chiesto lo slot.
> `front-utility core-unit` intero nello slot pesante (contato come slot 2 dal coordinatore): 153 file, 4 863 test verdi;
> slot liberato subito.

### Checkpoint E3 🧊 (2026-10-15) — FROZEN, in attesa del commit del coordinatore
> **Base**: HEAD `7f735af7c`. Delta: 22 file tracciati modificati, 2 nuovi (`services/email/links.py`,
> `test_services/test_email_links.py`). Righe nei file altrui dichiarate nel messaggio di consegna. Restano di E3: la
> verifica dell'indirizzo nella scheda Email con l'helper di A6b; l'email d'attivazione dell'admin iniziale dopo A7.

### E3 — revisione di sicurezza (cancello di rilascio)

#### E3.5 — `security-review` sulle superfici nuove ✅ (2026-10-15), correzioni ✅, prove ✅ (2026-10-15, 21:20)
> **Note implementazione**: E3 committato (`fd530372d`, `cf12cac9c`), base aggiornata dal coordinatore
> (`cc4758dce`: CP2b di H, B, B8, W N2, Z6b parte 1). Giro leggero sulla base unita, tutto verde: `email-links` 71,
> `email-flows` 104, `config-audit` 90, `api email` 154, `api system` 117, `api instance-block` 60, `check-orphans`.
> Revisione di sicurezza chiesta dal coordinatore (agente `security-review`, sola lettura) su
> `POST /email/password-reset`, `POST /email/links`, `links.py` e i limiti, con i tre punti già segnalati.
>
> Esito e decisioni:
> - **Alert 1, MEDIA (fiducia 8), verificato**: `PUT /auth/profile` cambia l'email con il solo cookie (niente password
>   attuale, nessun avviso, sessioni aperte); con «password dimenticata» un momento dentro la sessione di un altro
>   diventerebbe una presa permanente dell'account. **Decisione del coordinatore** (15/10): (a) A chiede la password
>   attuale per cambiare l'email e chiude le altre sessioni, lotto piccolo dopo A6d; E4 aggiungerà l'avviso al vecchio
>   indirizzo; (b) **subito**: `POST /email/password-reset` risponde 409 `FORGOT_PASSWORD_DISABLED` finché (a) non è
>   entrato (`flows.FORGOT_PASSWORD_HELD`), e lo tolgo con E4.
> - **Alert 2, BASSA**: con la registrazione aperta, un account con l'email di un altro e uno username di phishing fa
>   partire email vere verso il terzo. In E: ogni valore nel testo delle email su una riga (`messages._one_line`:
>   caratteri di controllo e separatori di riga → spazio, controlli bidi tolti); un limite per casella di posta
>   (`FORGOT_BY_MAILBOX`, 3/h). In A (backlog, deciso dal coordinatore): i caratteri dello username.
> - **Punto 1** (revoca del link dell'admin): il flusso anonimo non manda niente mentre un link di reset creato da un
>   admin è vivo (`_admin_link_live`).
> - **Punto 2** (reset di un account disattivo): `POST /email/links` risponde 409 `EMAIL_ACCOUNT_INACTIVE`.
> - **Punto 3** (limite per indirizzo): 10 ogni 15 minuti, IPv6 per /64 (`address_key`); nella doc
>   `FORWARDED_ALLOW_IPS` con gli indirizzi esatti dei proxy, mai `*`.
> - Altri: il conteggio per account si rifà dentro la transazione di scrittura dopo la creazione (due richieste
>   simultanee non mandano due email; un link dell'admin revocato dalla creazione torna con il rollback); il log
>   d'errore del lavoro in background senza traceback (i parametri SQL avrebbero mostrato l'identificativo);
>   `urlsplit` dentro il `try` (`https://[::1` non dà più 500).
> - Verificato dalla revisione senza rilievi: avvelenamento dei link, fuga dei token, enumerazione, iniezione di
>   intestazioni e di HTML, confusione degli scopi, CSRF (cookie SameSite=Lax, nessun CORS), istanza bloccata.
>
> **⚠️ Fuori pista** (autorevisione durante la seconda pausa, 21:00): due difetti nelle correzioni appena scritte,
> trovati prima di ogni prova.
> - `address_key` leggeva `ip.ipv4_mapped` anche su un `IPv4Address`, che non l'ha: ogni client IPv4 avrebbe preso
>   un 500 a feature aperta (la sospensione lo nascondeva). Ora: IPv4 così com'è, IPv4 mappato → l'IPv4, IPv6 → il
>   suo /64 calcolato dall'intero (la zona di `fe80::1%eth0` non disturba), `None` o `""` → `None`, il resto com'è
>   scritto. Verificato con uno snippet sui nove casi; i casi sono girati a test-author.
> - Nel ramo della corsa, dopo `session.rollback()`, `logger.info(..., user_id=user.id)` avrebbe ricaricato `user`
>   scaduto → `MissingGreenlet` → il catch-all avrebbe loggato «the request failed» al posto della riga giusta (niente
>   inviato comunque). Ora `user_id` si legge subito dopo la ricerca dell'account e si usa ovunque dopo.
>
> Doc (docs-writer, solo EN, nessuno stamp): `admin/email.en.md` e `developer/backend/email.md` coprono sospensione e
> motivo, limiti nuovi, `EMAIL_ACCOUNT_INACTIVE`, `FORWARDED_ALLOW_IPS` mai `*`, log senza traceback, valori su una
> riga; in più l'istanza bloccata e le regole intere di `_usable_base` (già nel codice di E3, non ancora scritte).
>
> **Rimandato al lotto della scheda Email (sonda)**: il testo dell'avviso `email.links` «non è un indirizzo http(s)» è
> più stretto di `_usable_base`, che rifiuta anche credenziali, `?`/`#`, spazi, host mancante o porta sbagliata. Va
> riscritto («non si può usare per i link nelle email») nel log, nei 4 cataloghi `email.checks.links.invalid` e nelle
> due righe di `admin/configuration.en.md`: tocca i cataloghi, quindi `core-unit`, che quel lotto fa comunque.
>
> **Test** (test-author, scritti durante le pause, nessuno lanciato prima della ripresa delle 21:09):
> - nuovi: EMF-035 (la sospensione per prima, in ogni stato; esce `True`), EMF-036 (`address_key`), EMF-037 (10 per
>   /64; IPv4 e la sua forma mappata, un conteggio), EMF-038 (casella di posta, 4 account e 4 maiuscole), EMF-039
>   (link vivo dell'admin; consumato, revocato o scaduto no), EMF-040 (corsa: link rivale fatto da un'altra sessione
>   dentro `create_password_reset` → rollback, il rivale di nuovo vivo), EMF-041 (account disattivo), EMF-042 (errore
>   del DB con l'identificativo nei parametri → solo `error="OperationalError"`); EMA-046 (sospesa: stessa 409 per
>   tre account, niente contato né programmato), EMA-047 (/64 dalla rotta), EMA-048 (`EMAIL_ACCOUNT_INACTIVE`);
>   EMM-031…033 (una riga per valore, bidi tolti, markup spezzato ancora escapato);
> - adattati: EMF-021/024/027/029/030/031/032/033, EMA-035/041/042/043, EML-011/012 (`https://[::1`); i moduli
>   flows e api tolgono la sospensione con una fixture autouse, i test della sospensione la rimettono;
> - runner (file condivisi, solo le descrizioni delle mie voci): `_backend_api.py:900`, `_backend_services.py:490,
>   1335, 1363, 1373`.
> - EMF-040 regge su un'ipotesi verificata: il motore del test passa dal listener `connect` globale (WAL,
>   `busy_timeout`), e pysqlite apre la transazione solo prima di una scrittura, quindi le letture del lavoro non
>   tengono lock quando il rivale fa commit.
>
> Doc: tabella Testing di `developer/backend/email.md` aggiornata (EMF-042, EMA-048, EMM-033, la parentesi IPv6, la
> fixture della sospensione); «Coming Next» con la decisione 44 al posto di «ancora da decidere».
>
> **Prove** (dopo la ripresa delle 21:09, una alla volta, `nice -n 10`, corsia 6188, carico sotto 70 a ogni lancio):
>
> | Comando | Esito |
> |---|---|
> | `services email-links` | 74 ✅ (71 + 3) |
> | `services email-flows` | 132 ✅ (104 + 28), EMF-040 compreso, le due forme della corsa |
> | `services email-messages` | 267 ✅ (245 + 22) |
> | `services email-delivery` | 104 ✅ |
> | `--no-shared-server api email` | 160 ✅ (154 + 6) |
> | `services config-audit` | 90 ✅ |
> | `check-orphans` | ✅ (316 file backend raggiungibili) |
> | `dev.py mkdocs build` (stretto) | uscita 0, nessuna riga `WARNING`/`ERROR`, 3 044 URL risolti |
> | `dev.py mkdocs check-links` | 96 link validi |
>
> - `ruff` e `black --check` puliti sui file di produzione e sui test; `black` segnala in `_backend_services.py` solo
>   la riga lunga di A (già girata ad A dal coordinatore). `git diff --check` pulito, porta 6188 libera, nessun file
>   nuovo né ignorato da escludere oltre ai log di `/tmp` e allo snapshot del DB nella cartella dei log del runner.
> - **Non rieseguiti**: `api system` e `api instance-block`, verdi sulla revisione combinata `cc4758dce` prima delle
>   correzioni; il delta non tocca i loro percorsi (senza `LIBREFOLIO_PUBLIC_URL` `links_state` esce prima di
>   `_usable_base`; su un'istanza bloccata le rotte email rispondono 423 dal middleware prima del gestore). Nessun
>   catalogo i18n toccato → niente `core-unit`.

### Checkpoint E3s 🧊 (2026-10-15) — FROZEN, in attesa del commit del coordinatore
> **Base**: HEAD `cc4758dce`. Delta: 13 file tracciati modificati, nessuno nuovo. Codice: `services/email/{flows,
> messages,links}.py`, `api/v1/email.py`. Test: `test_email_{flows,messages,links}.py`, `test_email_api.py`; runner
> (solo descrizioni delle voci E): `_backend_api.py`, `_backend_services.py`. Doc EN: `admin/email.en.md` (senza
> traduzioni), `developer/backend/email.md`. Questo piano. Resta aperta la sospensione di «password dimenticata»
> (409 `FORGOT_PASSWORD_DISABLED`) fino al lotto di A sulla password attuale per cambiare l'email; la toglie E4.
>
> **Committato** dal coordinatore: `5608193b5` fix(email) e `734bb6706` docs(journal).
>
> **Merge di base** (2026-10-15, 21:20): `dev_release2` `b09776a3d` (A6b, X CP10, J CP-4c, lo scatto di B), commit del
> coordinatore `cd12482fc`. Un conflitto, `admin/configuration.en.md`: le righe di `LIBREFOLIO_PUBLIC_URL` riscritte da
> A6b (dialoghi di Users, «Server address») + le mie frasi sulle email con un link; `LIBREFOLIO_BILLING_URL` di
> `dev_release2`; la sezione Plugin Settings di X e le mie righe `email.links` unite da git, senza doppioni. Controllo
> di significato: il filtro di mascheramento di X agisce solo sui segreti «in volo» di una chiamata di plugin, mai
> attivi nel codice email. Prove sulla revisione unita, una alla volta, `nice -n 10`: `services email-flows` 132 ✅,
> `email-delivery` 104 ✅, `email-messages` 267 ✅, `--no-shared-server api email` 160 ✅, `api system` 117 ✅ (server
> di corsia, spento a fine run), `check-orphans` ✅ (325 file backend, 428 unit, 128 E2E raggiungibili). Porta 6188
> libera.
>
> **Entrato** in `dev_release2` = `8f908623b` (E3 + E3s); CHANGELOG `1d74e212e`. Ramo portato avanti a `1d74e212e`.

### E3 — la sonda nella scheda Email (lotto E3p)

Via del coordinatore alle 21:31, con la decisione 45 e il contratto della sonda concordato con A (A6b in base da
`1d74e212e`).

#### E3.6 — Disegno ✅ (2026-10-15)
> - **Quando**: solo con l'email `ready` e `links.ready`, sulla base di `/email/status.links.base` (la stessa delle
>   email). Una volta per base: la rilettura dello stato dopo l'email di prova non rilancia la sonda; «Verifica di
>   nuovo» la rilancia; una risposta superata (contatore di generazione, come A) si scarta.
> - **Come**: `emailLinks.probeEmailLinks(base, {pageProtocol, issueNonce})`, TS puro sopra l'helper di A
>   (`settings/users/addressProbe.ts`: `normalizeBase`, `checkAddress`), nessuna copia. Il nonce da
>   `emailApi.issueProbeNonce()` (`POST /users/address-probe`, solo admin). Esiti: `normalizeBase` → `null`:
>   `invalid`; pagina `https:` e base `http:`: `insecure`, prima di ogni richiesta (il browser la bloccherebbe:
>   contenuto misto); poi `match` → `match`, `mismatch` → `otherInstance`, `unverifiable` → `unreachable`.
> - **Dove**: un riquadro «link nelle email» nella scheda, dopo gli avvisi di configurazione: la base, poi l'esito.
>   `checking` e `match` su una riga tenue o di successo; gli altri come avviso (classi `NOTICE_CLASSES.warning`), con
>   il testo che dice che la verifica vale solo per questo dispositivo e può dipendere da DNS o rete, e il pulsante
>   «Verifica di nuovo».
> - **Testo di `email.links` più ampio**: il log e `email.checks.links.invalid` dicono «non si può usare per i link»
>   e le regole intere (http(s), un host, niente utente, password, `?` o `#`), non solo «non è http(s)». Doc: le due
>   righe di `admin/configuration.en.md`, le pagine email.
> - **Fuori**: la galleria (lo stato servito non ha `links`, lo scatto non cambia); un E2E nuovo (la sonda di A ha già
>   il suo contro il backend vero; qui bastano Vitest e il test del componente).
> - **Prove**: `services email-checks`, `config-audit`; Vitest dei file email con il binario bloccato; `i18n build` +
>   `check`; `front check`; `prettier --check`; poi `front-utility core-unit` nello slot pesante (cataloghi).

#### E3.7 — Codice della sonda e testo di `email.links` ✅ (2026-10-15)
> **Note implementazione**:
> - `features/email/emailLinks.ts` (nuovo, TS puro): `probeEmailLinks()` sopra `normalizeBase`/`checkAddress` di A;
>   `invalid` e `insecure` prima di ogni richiesta; si sonda la base normalizzata.
> - `emailApi.ts`: `EmailStatus.links` ristretto da `linksOf()` (pronto solo con una base); `issueProbeNonce()`.
> - `emailText.ts`: `LINKS_PROBE_KEYS`, `LINKS_PROBE_CLASSES` (solo ruoli), `linksProbeWarns()`.
> - `EmailSettingsTab.svelte`: `linksBase` solo con `ready` + `links.ready`; un `$effect` che sonda una volta per
>   base, il cui cleanup alza la generazione (base cambiata, uscita dalla scheda); «Verifica di nuovo» per i quattro
>   esiti d'avviso; `notify('email.links.checked')`; `data-busy` della scheda invariato, il riquadro ha il suo.
> - Cataloghi `i18n/email/` × 4: `email.links.{base,probe.*,recheck}` (8 chiavi), `email.checks.links.invalid`
>   riscritto con le regole intere; niente `<`/`>`, nessun apostrofo davanti a una graffa.
> - Backend: testo del `warning` di `email.links` (log), messaggio della 409 `EMAIL_LINKS_UNAVAILABLE`, descrizione
>   di `EmailLinksRead.ready`, docstring di `EmailLinksUnavailableError`.
> - Prove leggere: `prettier --check` sui file toccati ✅; `i18n build` + `check` stretto ✅ (4 634 chiavi × 4, 93
>   sorgenti); `ruff`/`black` ✅; `front check`: 11 errori, tutti nei fixture dei test (`EmailStatus` vuole `links`),
>   girati a test-author; il codice di produzione passa.
> - Test a test-author (Vitest `emailLinks.test.ts` nuovo in core-unit, `emailApi`, `emailText`, la scheda; EMK/EMA
>   se toccati); doc a docs-writer (`admin/email.en.md`, `developer/backend/email.md`, la riga di
>   `admin/configuration.en.md`).

#### E3.8 — Test, doc e prove ✅ (2026-10-15)
> **Note implementazione**:
> - test-author: `emailLinks.test.ts` nuovo (ELK-01…09, 34 test, ambiente node, registrato in core-unit in
>   `_frontend_utility.py`, una riga); `emailApi.test.ts` EAP-01…07; `emailText.test.ts` ETX-01…06;
>   `EmailSettingsTab.test.ts` ETB-01…10 per i link; `test_email_checks.py` 3 casi `invalid` in più (`?` vuoto,
>   credenziali, porta 99999). Nessun test asseriva i testi vecchi alla lettera. Limite dichiarato: in jsdom la pagina
>   è sempre `http:`, quindi il caso https è fissato in ELK-02, non nel test della scheda.
> - docs-writer: `admin/email.en.md` nuova sottosezione `#links-check` (esiti, riquadro «solo questo dispositivo»,
>   quando gira), «To check it» senza più «LibreFolio non controlla»; `developer/backend/email.md` (check, 409, la
>   scheda, «Coming Next»); `admin/configuration.en.md` riga `warning` di `email.links` (+1 −1). Tabella Testing
>   aggiornata da me.
> - Prove, una alla volta con `nice -n 10`, carico sotto 70:
>
> | Comando | Esito |
> |---|---|
> | `vitest run src/lib/features/email/` (binario bloccato) | 4 file, 300 ✅ |
> | `services email-checks` | 87 ✅ |
> | `--no-shared-server api email` | 160 ✅ |
> | `dev.py front check` | 0 errori, 0 avvisi |
> | `services config-audit` | 90 ✅ |
> | `check-orphans` | ✅ (429 unit registrati) |
> | `i18n build` + `check` stretto | ✅ 4 634 chiavi × 4 |
> | `dev.py mkdocs build` stretto / `check-links` | uscita 0, nessun WARNING/ERROR / 96 link validi |
>
> - `prettier --check`, `ruff`, `black`, `git diff --check` puliti; porta 6188 libera.
> - `front-utility core-unit` intero nello slot pesante (via del coordinatore, dopo la run di A, 22:09): 158 file,
>   5 248 test ✅ (log `/tmp/libreFolio_e3p_core_unit.log`), gate di markup, ICU e lingua compresi.

### Checkpoint E3p 🧊 (2026-10-15) — FROZEN, in attesa del commit del coordinatore
> **Base**: HEAD `1d74e212e`. Delta: 20 file tracciati modificati, 2 nuovi (`features/email/emailLinks.ts`,
> `emailLinks.test.ts`). Righe condivise: `_frontend_utility.py` (una riga), `admin/configuration.en.md` (+1 −1);
> `addressProbe.ts` di A riusato senza modifiche. Resta di E3: l'email d'attivazione dell'admin iniziale, dopo A7.
>
> **Entrato** in `dev_release2` = `e54ae96bb`; CHANGELOG `2415faf33`. Ramo a `2415faf33`.

### E5 — la verifica dell'email (decisione 44)

Ordine del coordinatore (22:12): E4 aspetta A6e (password attuale per cambiare l'email, poi tolgo la sospensione);
intanto E5, che non ne dipende. L'email d'attivazione dell'admin iniziale resta dopo A7.

#### E5.0 — Analisi sul codice (2026-10-15, base `2415faf33`)
> **Stato reale**:
> - Nessuna migrazione serve: la 005 di A ha già `users.email_verified_at` (NULL per gli account esistenti, «deciso
>   nella logica»), lo scopo `email_verification` nel CHECK, 24 h e `/verify-email` in `token_service`; il testo
>   `build_email_verification` è già nel mio catalogo (E1).
> - L'opzione `require_email_verification` è un segnaposto: `schemas/settings.py` («read nowhere»),
>   `GlobalSettingsTab` la disegna disattiva con un badge (`PLACEHOLDER_KEYS`), GSET-VAL-007 e i casi di
>   `test_settings_api.py:1592-1596` la girano sul DB di corsia perché «nessuno la legge».
> - `register_user` (A) crea l'account attivo e fa commit; `/auth/register` risponde 201 senza sessione, e
>   `RegisterCard` torna al login con `auth.accountCreated`. Il login risponde 403 `ACCOUNT_DISABLED` solo con la
>   password giusta; `stores/app/auth.ts` lo traduce. `user_usage` conta attivi + inviti vivi. `update_user_status` e
>   `set_user_active` cambiano lo stato senza toccare i token. Nessun limitatore sul login (A8 non c'è ancora).
> - Pagine dei token di A: `routes/invite`, `routes/reset-password`, `LinkStatusCard`, `authFlash`, `linkToken.ts`
>   (`LinkPurpose = 'invite' | 'password_reset'`).
>
> **Disegno proposto**:
> - «In attesa» = account disattivo con un token di verifica non consumato né revocato (anche scaduto). Ogni cambio di
>   stato fatto dall'admin revoca i token di verifica: un account disattivato dall'admin non torna attivo con un
>   vecchio link, e il login gli dice `ACCOUNT_DISABLED`, non «verifica».
> - Registrazione con l'opzione accesa (mai il primo account): account disattivo + token (24 h, con l'email
>   dell'account), nella stessa transazione; email in background dopo il commit; la risposta dice
>   `verification_required` e la card mostra «controlla la posta».
> - Login di un account in attesa → 403 `EMAIL_NOT_VERIFIED` (solo con la password giusta) e «rispedisci».
> - `POST /email/verification/confirm {token}` (anonimo): consuma il token, rifiuta se l'email dell'account è cambiata
>   da allora, attiva l'account, `email_verified_at = now`, revoca gli altri token di verifica.
> - `POST /email/verification/resend {username, password}` (anonimo): la stessa prova del login (hash fittizio per
>   chi non esiste), limite per indirizzo (10/15 min, prima della password), per account 1 ogni 5 min e 3/h, budget
>   d'istanza, posto libero; nuovo token (revoca i vecchi) e invio sincrono (502 → token revocato).
> - Opzione: si accende solo con email pronta **e** `LIBREFOLIO_PUBLIC_URL` utilizzabile (il link) → 409 altrimenti;
>   la scheda Impostazioni la abilita da `instanceConfig.email.links`.
> - Pagina `/verify-email` (mia): legge `#token=`, conferma, torna al login con un flash «email verificata».
>
> **Decisioni del coordinatore** (15/10, 22:3x): (1) verifica per tutte le registrazioni tranne il primo account,
> inviti compresi; (2) opzione accesa ma email o link non pronti alla registrazione → 409
> `EMAIL_VERIFICATION_UNAVAILABLE`; (3) gli account in attesa contano per `LIBREFOLIO_MAX_USERS` finché il link è
> vivo; (4) «rispedisci» con nome e password; (5) ad A per A6e: `email_verified_at` a NULL quando l'email cambia;
> (6) spegnere l'opzione lascia gli account in attesa; (7) badge «in attesa» nella scheda Users fuori dalla 1.3
> (backlog E-7). **Le righe nei file di A le scrivo io, dichiarate, A le rivede, ma solo dopo l'ingresso di A6d e
> A6e** (A tocca proprio `registration_service`, `auth.py`, `settings_service`, `LoginCard`, `GlobalSettingsTab`).
> Adesso: le parti solo mie (`email/verification.py`, le due rotte, `/verify-email`, l'i18n).
>
> **Dettaglio del disegno** (deciso scrivendo): il token creato dentro la transazione di `register_user` («tenuta»,
> `email` NULL) segna l'attesa e tiene il posto, ma il suo testo non esce mai; il lavoro in background ne crea uno
> nuovo con l'email dell'account, che revoca la tenuta, e lo spedisce. Se l'invio fallisce il token resta: l'account
> resta in attesa e «rispedisci» funziona. I limiti per account contano solo i token spediti (`email` non NULL); la
> conferma accetta solo un token la cui `email` è quella attuale dell'account.

#### E5.1 — Le parti solo mie (lotto E5a) ✅ scritte (2026-10-15)
> **Note implementazione**:
> - `services/email/verification.py` (nuovo): `verification_required`, `links_can_go`,
>   `ensure_verification_can_be_enabled`, `awaiting_verification`, `hold_for_verification` (lancia
>   `RegistrationError("EMAIL_VERIFICATION_UNAVAILABLE")` con import pigro: `registration_service` lo chiamerà),
>   `registration_email_work` (background, mai un'eccezione), `confirm_email`, `resend_verification` (limite per
>   indirizzo prima della password, `verify_password_or_dummy` di A, limiti per account sui soli token spediti, posto
>   di nuovo se il link è scaduto, riconteggio nella transazione come la password dimenticata).
> - `flows.py`: `_require_email` → `require_email`, `_remaining` → `link_ttl` (pubbliche, le riusa la verifica).
> - Rotte: `POST /email/verification/confirm` (400 `TOKEN_INVALID` con lo `status`) e `/resend` (401 e 403 come il
>   login, 409, 429 con `Retry-After`, 502, 422); schemi con docstring su una riga (backlog E-5).
> - Frontend: `verificationApi.ts`; in `emailApi.ts` `refusalBody`/`refusalStatus`/`refusalDetail`/`retryAfterOf`
>   esportati e riusati da `readTestFailure`; `emailText.ts` `VERIFY_PAGE_KEYS`, `resendFailureMessage`;
>   `VerifyEmailCard.svelte` (sopra `AuthCard` di A: la `LinkStatusCard` di A manda sempre dall'admin, qui invece
>   «accedi e chiedine un altro»); `VerificationNotice.svelte` (il «rispedisci» che `LoginCard` ospiterà con gli
>   agganci); pagina `routes/verify-email/+page.svelte` (come `/reset-password`: token tolto dalla barra, flash al
>   login). Il backend serve `200.html` per ogni percorso: nessuna registrazione della rotta.
> - i18n `email.verification.*` × 4 (19 chiavi); le chiavi degli agganci (messaggio della registrazione, rifiuto
>   della registrazione, opzione nelle Impostazioni) arrivano con gli agganci.
> - Prove leggere: `ruff`/`black` ✅; le rotte si importano ✅; `api sync` ✅ (nessun file tracciato toccato);
>   `prettier --check` ✅; `i18n build` + `check` ✅ (4 653 chiavi); `front check` 0 errori, 0 avvisi.
> - **Atterraggio senza agganci**: le rotte vivono ma nessun token di verifica esiste finché `register_user` non chiama
>   `hold_for_verification`: `confirm` risponde 400, `resend` 401/403/409. Innocuo.
>
> **⚠️ Fuori pista** (rilettura di docs-writer, due difetti nel mio codice, corretti prima dei test):
> - un'email di verifica non partita lasciava il token con l'indirizzo, contato come «spedito»: il «rispedisci» subito
>   dopo un 502 dava 429 «un link è appena partito». Ora il token perde l'indirizzo (`email` NULL) e torna una tenuta:
>   l'account resta in attesa, il link (che non ha raggiunto nessuno) non si conferma, e non conta per i limiti;
> - le 409 `EMAIL_UNAVAILABLE`/`EMAIL_LINKS_UNAVAILABLE` di `/verification/resend` mostravano il `problem` della
>   configurazione a chi non è admin: tolto, come in `/password-reset`.
>
> **Per gli agganci** (lotto E5b, dopo A6d e A6e): `_REGISTRATION_REFUSALS` di `auth.py` non conosce
> `EMAIL_VERIFICATION_UNAVAILABLE` (oggi uscirebbe 400 senza codice: va a 409); il commento «placeholder» di
> `schemas/settings.py:294`; `confirm_email` conta sulla revoca dei token ai cambi di stato dell'admin (aggancio).
> - seconda rilettura di docs-writer: (1) un'email che arriva dopo un errore di connessione (timeout dopo il DATA)
>   lasciava un token senza indirizzo che `confirm_email` revocava: se era l'unico, l'account smetteva di essere in
>   attesa → bloccato. Ora un token senza indirizzo è rifiutato (`revoked`) **senza** revocarlo; (2) il `try` copre
>   tutto quello che segue il commit, non solo `send_email`; (3) `resendErrors.EMAIL_RATE_LIMITED` reso neutro × 4
>   (lo danno anche il limite per indirizzo e il budget). `ruff`/`black`, `i18n build` + `check` ✅.

#### E5.2 — Test e doc di E5a ✅ (2026-10-15)
> **Note implementazione**:
> - test-author: `test_email_verification.py` (EMV-001…042, `services email-verification`, pure);
>   `test_email_verification_api.py` (EVA-001…015, `api email-verification`, pure); Vitest `verificationApi.test.ts`
>   (VFA-01…18, core-unit), `emailApi.test.ts` EAP-08…11, `emailText.test.ts` ETX-07…10; componenti
>   `VerifyEmailCard.test.ts` (VEC), `VerificationNotice.test.ts` (VNT), `routes/verify-email/page.test.ts` (VEP).
>   Registrazioni nel runner: due voci backend, una core-unit, tre component-unit. Primo giro: 6 rossi di EMV-017,
>   colpa del test (id letto dopo il rollback), corretti nel test.
> - Decisione mia su una domanda di test-author: anche la 502 di `resend` perde lo `smtp_code` (chi chiede non è
>   admin), come le 409.
> - docs-writer: sezione `#verification` di `developer/backend/email.md` (attesa, tenuta e link spediti, funzioni,
>   limiti, log, frontend, «non ancora collegato»), le due rotte, `link_ttl`/`require_email`. Tabella Testing mia.
> - Prove (prima della finestra delle 00:00, una alla volta): `services email-verification` 115 ✅,
>   `api email-verification` 48 ✅, `services email-flows` 132 ✅, `api email` 160 ✅, Vitest di
>   `features/email/` + `routes/verify-email/` 523 ✅ (8 file), `front check` 0/0, `prettier`, `ruff`, `black` (solo
>   la riga di A), `check-orphans` ✅.
> - Dopo la decisione sulla 502: `api email-verification` 48 ✅ di nuovo; `mkdocs build` stretto ✅ (nessun
>   WARNING/ERROR), `check-links` 96 ✅; `front-utility core-unit` intero (via del coordinatore, 23:27): 159 file,
>   5 415 test ✅ (`/tmp/libreFolio_e5a_core_unit.log`).

### Checkpoint E5a 🧊 (2026-10-15) — FROZEN, in attesa del commit del coordinatore
> **Base**: HEAD `2415faf33`. Delta: 17 file tracciati modificati, 11 nuovi (`services/email/verification.py`, due
> file di test backend, `verificationApi.ts` e il suo test, `VerifyEmailCard` e `VerificationNotice` con i loro test,
> `routes/verify-email/` con pagina e test). Righe condivise: i tre file del runner (solo voci mie), la riga E-7 del
> backlog. Nessun file di A toccato: gli agganci sono il lotto E5b, dopo A6d e A6e.
>
> **Committato** dal coordinatore: `50fa84159` (feat) e `a77033a9e` (journal); base aggiornata a `89f54be21` (T+DV,
> H CP-U1, X-RL, W F36). Verde sulla revisione unita: `api sync`, `front check` 0/0, `core-unit` 167 file / 5 658,
> `theme-roles.mjs --check` pulito, `services email-verification` 115, `api email-verification` 48, Vitest 523.

### E4 — invio per email, «password dimenticata», avviso al vecchio indirizzo

Ordine del coordinatore (23:30): E4a adesso, solo file miei, come E5a; gli agganci nei file di A in E4b, dopo A6e.

#### E4.0 — Analisi (2026-10-15, base `89f54be21`)
> - Il lato servizio c'è già: `POST /email/links` (E3) e i testi `invite`/`password_reset`; «password dimenticata»
>   (ammissione, limiti, lavoro) tenuta dalla 409. L'email di un account cambia solo da `PUT /auth/profile`: le rotte
>   admin di `users.py` (stato e ruolo, inviti, link di reset, sessioni) non la toccano.
> - **E4a**: `SendLinkByEmail.svelte` (props del registro di A, token dal `#token=`, invito con indirizzo, reset
>   senza), `sendByEmailVisible()` da `instanceConfig.email.links`; tipo `email_changed` nel catalogo × 4,
>   `build_email_changed`, `flows.email_changed_work` (background, senza link); `ForgotPasswordEmailForm.svelte` e i
>   wrapper; i18n `email.sendLink.*`, `email.forgot.*`; test; doc per sviluppatori.
> - **E4b** (dopo A6e): la riga in `LINK_SHARE_ACTIONS`; `ForgotPasswordCard` ospita il modulo con `email.links`;
>   `update_profile` → `email_changed_work` in background; tolta di `FORGOT_PASSWORD_HELD` con test e doc; doc admin e
>   utente; E2E nello slot; CHANGELOG; revisione di sicurezza mirata sulla «password dimenticata» aperta.
> - **Decisioni notturne, da rivedere**: (a) l'avviso mostra il nuovo indirizzo come `***@dominio`; (b) il nome
>   dell'istanza nell'avviso è l'host di `LIBREFOLIO_PUBLIC_URL`, altrimenti «LibreFolio», mai l'host della
>   richiesta; (c) l'avviso va solo all'indirizzo vecchio.
> - **Per la lista del developer** (E4b, file di A): con l'email pronta, `ForgotPasswordCard` mostra il modulo in alto
>   e tiene sotto il riquadro dei comandi (proposta), oppure lo nasconde.
> - **Via del coordinatore** (23:3x) con le decisioni notturne (a), (b), (c); la domanda sul `ForgotPasswordCard` va
>   nella lista del developer, e per E4b vale la mia proposta salvo sua diversa indicazione.

#### E4.1 — Le parti solo mie (lotto E4a) ✅ scritte (2026-10-15)
> **Note implementazione**:
> - Backend: `EmailKind.EMAIL_CHANGED`; `messages.masked_address()` (`***@dominio`) e `build_email_changed()` (il nuovo
>   indirizzo sempre mascherato dal costruttore, nessun link); testi `email_changed` × 4 nel catalogo del backend;
>   `flows.email_changed_work(user_id, old, new)` (background, sessione propria, `require_email`, lingua
>   dell'account, istanza da `LIBREFOLIO_PUBLIC_URL` o `INSTANCE_FALLBACK` = «LibreFolio», solo al vecchio
>   indirizzo, niente se uguali, log senza indirizzi, mai un'eccezione).
> - Frontend: `sendLinkApi.ts` (`tokenFromLink`, `sendByEmailVisible` da `instanceConfig`, `sendLinkByEmail`,
>   `readLinkSendFailure`); `forgotPasswordApi.ts` (`requestPasswordResetEmail`, `readForgotFailure`); in
>   `emailText.ts` `linkSendFailureMessage` (i codici SMTP con le chiavi `email.smtpErrors.*` già esistenti) e
>   `forgotFailureMessage`; `SendLinkByEmail.svelte` (props del registro di A; invito con l'indirizzo modificabile,
>   reset senza); `ForgotPasswordEmailForm.svelte` (202 come avviso informativo, mai «inviato»).
> - i18n `email.sendLink.*` (16) ed `email.forgot.*` (8) × 4.
> - Prove leggere: `ruff`/`black` ✅, resa delle quattro lingue a mano ✅ (l'indirizzo pieno mai nel testo),
>   `prettier` ✅, `i18n build` + `check` ✅ (4 678 chiavi), `front check` 0/0, `theme-roles.mjs --check` pulito.
> - **⚠️ Fuori pista** (autorevisione e rilettura di docs-writer): (1) con l'email spenta, il default del
>   self-hosted, ogni cambio d'email avrebbe scritto un WARNING «notice not sent»: ora una riga `info` e basta, il
>   warning resta per l'email configurata ma inutilizzabile; (2) un indirizzo d'invito scritto male lo rifiuta la
>   validazione di FastAPI (422 con `detail` lista) e l'azione mostrava l'errore generico: ora
>   `readLinkSendFailure` lo legge come `EMAIL_RECIPIENT_INVALID`; (3) commento d'intestazione del modulo «password
>   dimenticata» allineato (ospitato da E4b).
> - **Decisione notturna, da rivedere**: «Invia per email» non sceglie la lingua dell'invito (sempre quella
>   predefinita dell'istanza); backlog E-8.

#### E4.2 — Test e doc di E4a ✅ (2026-10-15), `front check`, `core-unit`, `mkdocs build` ✅ (2026-10-16, 01:3x)
> **Note implementazione**:
> - test-author: `test_email_messages.py` EMM-034…038 (il sesto tipo, i testi × 4, la maschera, `masked_address`,
>   l'escape del dominio); `test_email_flows.py` EMF-043…052 (contratto 14: `email_changed_work`); Vitest
>   `sendLinkApi.test.ts` (SLA-01…14) e `forgotPasswordApi.test.ts` (FPA-01…10) in core-unit, `emailText.test.ts`
>   ETX-11…14; componenti `SendLinkByEmail.test.ts` (SLE-01…09) e `ForgotPasswordEmailForm.test.ts` (FPF-01…06) in
>   component-unit. Nessun difetto trovato nel codice di produzione.
> - docs-writer: `developer/backend/email.md` (i sei tipi `#kinds`, `#flow-email-changed`, `#link-actions` con
>   `#send-by-email` e `#forgot-form`, «non ancora collegato», le decisioni notturne); tabella Testing mia.
> - Prove (prima delle 00:00, una alla volta): `services email-messages` 316 ✅, `services email-flows` 155 ✅,
>   Vitest di `features/email/` 748 ✅ (11 file), `prettier`, `ruff`/`black`, `check-orphans` ✅.
> - **Dopo la finestra**: `front check` (i quattro file di test nuovi), `front-utility core-unit` (cataloghi),
>   `mkdocs build` stretto e `check-links`.

#### E5.3 — Agganci di E5b preparati fuori dal worktree ✅ (2026-10-16, notte)
> **Note implementazione** (richiesta del coordinatore, 23:59, nessuna prova): in `/tmp/libreFolio_e5b/` (copia nella
> cartella della sessione) la patch `e5b_hooks_A6d.patch` su A6d (`ce4acff6c`, 14 file: `registration_service`
> con `user_usage` e la tenuta, `auth.py` login/register, `schemas/auth.py`, `user_service` che revoca i token di
> verifica ai cambi di stato, `settings_service` + `api/v1/settings.py` con la 409, il commento di
> `schemas/settings.py`, GSET-VAL-007 su `scheduler_enabled` e GSET-VAL-011 nuovo, `types/user.ts`,
> `stores/app/auth.ts`, `LoginCard`, `RegisterCard`, `registrationErrors.ts`, `GlobalSettingsTab`); `e5b_i18n.py`
> (quattro chiavi × 4); il README con l'ordine d'applicazione, i test da scrivere e i cancelli. `git apply --check`
> pulito su A6d; `ruff` (con l'estrazione di `_refuse_what_cannot_turn_on`: la funzione superava la complessità
> 10), `black`, `prettier` puliti. Esclusi, per regola: `update_profile` e `ProfileTab` (A6e).
> - **⚠️ Fuori pista** (trovato da docs-writer scrivendo le bozze): con `user_usage` che conta gli account in attesa,
>   su un'istanza piena l'admin non poteva riattivare un account in attesa (409 `USER_LIMIT_REACHED` di
>   `PATCH /users/{id}`), benché il suo posto fosse già contato; `user activate` stampava un avviso falso. Aggiunto
>   `verification.holds_place()` (patch mia, `e5b_mine.patch`) e usato da `api/v1/users.py` e `scripts/user_cli.py`
>   (patch di A, ora 16 file). Ricontrollati `git apply --check`, `ruff` (un import da riordinare), `black`.
> - Bozze di doc (docs-writer, in `docs/` del pacchetto): sezione `#verification` di `admin/email.en.md`, la parte E4b
>   della stessa pagina, la riga di `admin/settings.en.md`, `admin/users.en.md`, `user/getting-started.en.md`, le
>   sostituzioni nelle pagine per sviluppatori, e `extra_pages.md` (pagine tradotte, solo col via del coordinatore).
> - Resta un buco nell'interfaccia (docs-writer): `UserRow` spegne **Riattiva** su un'istanza piena per ogni account
>   disattivo, perché la lista non dice chi è in attesa. Preparata una patch **opzionale** (decide il coordinatore):
>   `AdminUserRead.holds_place` (una query, `verification.place_holders()` in `e5b_mine_optional.patch`),
>   `AdminAccount.holds_place?`, `UserRow` che non spegne il pulsante per quegli account; lo stesso campo porterebbe il
>   badge E-7. Proposta: includerla in E5b. Controllata in sequenza dopo la patch principale (`git apply --check`).
> - **Decisione del coordinatore** (16/10, 00:34, notturna, da rivedere): la patch opzionale entra in E5b (campo
>   `holds_place` e **Riattiva** acceso); il badge E-7 resta fuori dalla 1.3 (il campo c'è, il badge no). Si applica
>   dopo l'ingresso di A6d e A6e e l'aggiornamento della base, con un nuovo `git apply --check` (A6e tocca gli stessi
>   file).
> - **Test di E5b scritti in anticipo** (test-author, in `tests/` del pacchetto, file nuovi di E per non toccare i test
>   di A che A6e può cambiare; non eseguiti): `test_email_verification_hooks_api.py` (EVH-001…010, la catena intera),
>   `test_email_verification_hooks.py` (EVK-001…008), Vitest/componenti `auth.verification`, `registrationErrors
>   .verification`, `LoginCard.verification`, `RegisterCard.verification`, `GlobalSettingsTab.verification`,
>   `UserRow.verification`; `REGISTRATION.md` con le righe del runner. Dai suoi dubbi: (1) nella patch principale la
>   riga di `auth.test.ts` di A (`ENGLISH` è un `Record<AuthErrorKey, string>`: senza, `front check` rosso); (4)
>   `verificationBlocked` legge il valore **salvato**, non quello modificato: acceso e con l'email rotta, l'interruttore
>   resta usabile nei due sensi fino al salvataggio. **Decisione notturna, da rivedere** (2): un account in attesa,
>   già disattivo, non si «disattiva» con il PATCH (nessun cambio); per un'iscrizione indesiderata l'azione è Elimina,
>   o `user deactivate` dalla CLI. Patch principale ora 17 file, opzionale 4; applicate in sequenza su A6d ✅.
> - Ultimo dubbio di test-author: la risposta di `PATCH /users/{id}` non portava il flag (`holds_place: false` anche
>   per un account in attesa), e una riga sostituita da quella risposta avrebbe spento **Riattiva** fino al
>   ricaricamento. Ora la patch opzionale calcola il flag anche lì; nota in `tests/REGISTRATION.md` per il caso EVH da
>   aggiungere all'applicazione. Patch ricontrollate in sequenza su A6d; `ruff`, `black` puliti.
> - **Per il merge con A6e** (avviso del coordinatore, 00:50): A6e corregge «si cambia con la sola sessione» in
>   `developer/backend/email.md` e `admin/email.en.md`. E4a toccava solo la riga accanto nel primo (`lot E4` → `E4b`
>   nel riquadro della tenuta): ripristinata, così E4a non tocca più quel paragrafo e il merge non trova conflitti lì.
>   Il riquadro sparisce comunque con E4b.

#### E4.3 — Agganci di E4b preparati fuori dal worktree ✅ (2026-10-16, finestra senza prove)
> **Note implementazione**: in `/tmp/libreFolio_e4b/` (copia nella cartella della sessione): `e4b_hooks_A.patch` (la
> riga `send-by-email` in `LINK_SHARE_ACTIONS`, il modulo in `ForgotPasswordCard` con `email.links` e il riquadro dei
> comandi sotto) ed `e4b_mine.patch` (la tenuta tolta: costante, errore, 409, caso frontend e chiave i18n × 4).
> **Decisione notturna, da rivedere**: la tenuta si toglie del tutto, non resta come interruttore spento. README con
> l'ordine, i test da togliere e da aggiungere, l'E2E, la doc, i cancelli. Esclusi per regola: l'aggancio in
> `update_profile` e `ProfileTab` (A6e). `git apply --check` pulito sul worktree; `ruff`, `black`, `prettier` puliti.
> - **Test di E4b scritti in anticipo** (test-author, `tests/` del pacchetto E4b, non eseguiti): `e4b_tests_mine.patch`
>   sui miei file di test (via EMF-035, EMA-046 e le fixture che toglievano la tenuta; nuovi EMF-053 ed EMA-049: la
>   rotta aperta come esce, 202 e un'email), `e4b_runner_desc.patch` a parte (descrizioni nel runner condiviso),
>   nuovi `linkShareRegistration.test.ts` (LSR) e `ForgotPasswordCard.email.test.ts` (FCE), le bozze E2E
>   `email-send-link.spec.ts` (ESL-E) e `forgot-password-email.spec.ts` (FPE-E) con `fixtures/instance-email.ts`,
>   `REGISTRATION.md`. Dal suo dubbio 1: `data-testid="forgot-email-unavailable"` sull'avviso della card (patch di A
>   rigenerata). Tutte le patch passano `git apply --check` sul worktree.

#### E4.4 — Le ultime prove di E4a ✅ (2026-10-16, ripresa delle 01:33)
> `dev.py front check` 0 errori, 0 avvisi; `front-utility core-unit` 169 file, 5 867 test ✅
> (`/tmp/libreFolio_e4a_core_unit.log`); `dev.py mkdocs build` stretto ✅ (nessun WARNING/ERROR), `check-links` 96 ✅.
> Una alla volta, `nice -n 10`, carico sotto 70.

### Checkpoint E4a 🧊 (2026-10-16) — FROZEN, in attesa del commit del coordinatore
> **Base**: HEAD `89f54be21`. Codice: `messages.py` (`EMAIL_CHANGED`, `masked_address`, `build_email_changed`), i
> testi `email_changed` × 4 del backend, `flows.py` (`email_changed_work`, `INSTANCE_FALLBACK`); frontend
> `sendLinkApi.ts`, `forgotPasswordApi.ts`, `emailText.ts`, `SendLinkByEmail.svelte`, `ForgotPasswordEmailForm.svelte`;
> i18n `email.sendLink.*`, `email.forgot.*` × 4. Test (EMM-034…038, EMF-043…052, SLA, FPA, ETX-11…14, SLE, FPF);
> doc `developer/backend/email.md`; runner (voci mie); backlog E-8; questo piano. Nessun file di A. I pacchetti E5b ed
> E4b stanno fuori dal worktree (`/tmp/libreFolio_e5b/`, `/tmp/libreFolio_e4b/`, copie nella cartella della sessione).

### E-5 — la guardia sui testi che `api sync` non sfugge (lotto senza A, 2026-10-16)

Via del coordinatore (01:45): prima la diagnosi del caso esatto. Se un caso rompe oggi `generated.ts`, la cura
nell'escape di `frontend/scripts/fix-openapi-discriminators.mjs` più un pytest puro di guardia; se no, solo il pytest.

#### E-5.0 — Diagnosi ✅ (2026-10-16)
> Su `openapi-zod-client` 1.18.3 con i flag di `generate-api` (`--export-types --with-docs --with-description`).
> Fonte: il codice del generatore (`getZodChain`, `default.hbs`, `generateJSDocArray`), poi tre matrici isolate in
> `/tmp/libreFolio_e5_bt/` (`matrix.py`: 14 posizioni × 18 testi; `matrix2.py` e `matrix3.py`: 26 casi su JSDoc,
> parametri `$ref`, ordine, risposte d'errore, corpo). Ogni caso è un OpenAPI con un solo testo in una sola posizione,
> generato e letto dal parser di TypeScript (errori di sintassi, template taggati, sostituzioni).
>
> **Dove il generatore scrive un testo, e cosa lo rompe**
>
> | Dove | Forma | Cosa la rompe |
> |---|---|---|
> | `.describe()` di una proprietà, di `items` e `additionalProperties` in linea, di un parametro | testo con un a capo → template literal crudo | `` ` `` (sintassi; il doppio ``` `` ``` dà un template taggato, il `TypeError` all'import di E2b), `${` (sostituzione), `\` (sintassi con `\x`, `\u`, `\` finale; altrimenti testo alterato) |
> | idem | testo di una riga → `"…"` crudo | `"`, `\` |
> | descrizione dell'endpoint, delle risposte non 2xx (anche senza contenuto), del corpo | Handlebars `` `{{…}}` ``, che sfugge ``& < > " ' ` =`` | `${`, `\` |
> | JSDoc dei campi in linea dei tipi esportati | `/** … */` | `*/` (anche in `pattern`, `enum`, `default`, `example(s)`) |
>
> - Una proprietà `$ref` porta il testo **del componente**, anche se il campo ha una descrizione sua (quella non esce).
> - Mai scritti: membri `$ref` di `anyOf`, `items` `$ref`, corpo e risposte `$ref`, la definizione del componente, le
>   descrizioni delle risposte 2xx e di `default`.
> - La descrizione del parametro passa da `trim()`. Un parametro `$ref` sovrascrive la descrizione del componente
>   condiviso (vuota se il parametro non ne ha): se il testo del componente arrivi a una proprietà dipende allora
>   dall'ordine in cui il generatore visita gli endpoint (GET: no; POST con il corpo che lo contiene: sì).
>
> **Oggi** (HEAD `8915c1b85`, `openapi.json` e `generated.ts` di `api sync` delle 01:39): il client si legge con 0
> errori di sintassi, 0 template taggati, 0 sostituzioni. Il modello delle regole sul documento conta 3 627 punti
> (1 449 tra virgolette, 63 template, 310 Handlebars, 1 805 JSDoc), nessuno con un carattere vietato; copre ogni testo
> distinto del client (0 mancanti; 6 in più, i parametri ripetuti che il generatore raccoglie in una `const`).
> **Latenti**: 49 componenti con backtick in una descrizione su più righe (`AssetType`, i `BRIM*`, `Risk*`…), oggi mai
> referenziati direttamente come proprietà. Basta un campo `x: QuelComponente` perché `api sync` rompa il client.
>
> **Esito**: nessun caso oggi → solo la guardia. `fix-openapi-discriminators.mjs` non si tocca (detto al coordinatore).
>
> **Decisioni notturne, da rivedere**:
> - (d) la guardia fissa la versione del generatore letta da `frontend/package-lock.json` (1.18.3) e i suoi flag: a
>   ogni aggiornamento le regole vanno riverificate prima di spostare la costante;
> - (e) la guardia è prudente: ignora l'effetto d'ordine dei parametri `$ref` e controlla sempre il testo del
>   componente; può segnalare un testo che il client di oggi non porterebbe, non ne perde nessuno;
> - (f) sta in `test_schemas` (categoria `schemas`) e legge `backend.app.main.app.openapi()`, la stessa fonte di
>   `api sync`;
> - (g) il controllo di `*/` è globale: ogni nodo di schema del documento, per ogni chiave che il JSDoc scrive. Oggi
>   `*/` non compare da nessuna parte, quindi costa zero e non perde i nodi dove il JSDoc arriva davvero.
>
> **⚠️ Fuori pista**: la quarta matrice (`matrix4.py`, 10 casi), fatta per verificare il «non ne perde nessuno» prima
> di consegnare il modello, ha trovato due buchi nel primo modello (già passato al test-author, corretto con
> `write_agent`):
> - `items` e `additionalProperties` che sono un `$ref` **con** una `description` accanto scrivono quel testo in
>   `.describe()` (sintassi rotta, verificato). È il contrario delle proprietà, dove il testo accanto al `$ref` si
>   ignora ed esce quello del componente. Senza testo accanto, non esce niente;
> - il JSDoc non sta solo sulle proprietà: il generatore dei tipi lo mette anche su `items` e sui membri di
>   `anyOf`/`oneOf`/`allOf` dentro un tipo esportato (`*/` lì: sintassi rotta, verificato). Da qui la decisione (g).
>
> Confermato: la `.describe()` non scrive la descrizione dei membri in linea di `anyOf`/`oneOf`/`allOf`, ma solo quella
> delle loro proprietà e dei loro `items`. I 49 latenti si referenziano solo come elementi di liste (23), membri di
> `anyOf` (10), risposte (6), membri di `oneOf` (6) e corpi (4).

#### E-5.1 — Il pytest di guardia ✅ (2026-10-16)
> `test-author`: `backend/test_scripts/test_schemas/test_openapi_client_text.py`, 78 test in 15 funzioni.
> - OCT-001: versione e opzioni del generatore. Il lock fissa la 1.18.3; `generate-api` lo lancia una volta sola, con
>   esattamente `--export-types --with-description --with-docs` (il percorso di uscita a parte).
> - OCT-010…018: il modello su documenti piccoli, un caso per ogni verdetto delle matrici. Coprono le forme, i campi,
>   `items` e `additionalProperties` (anche con un `$ref` e un testo accanto), i membri di unione, i parametri e il
>   `trim()` di JavaScript, Handlebars, `*/` su ogni nodo, le forme non verificate e il messaggio d'errore.
> - OCT-020 e 021: FastAPI e Pydantic. `Inner` come campo è segnalato; in `list[Inner]` e in `Inner | None` no, ed è
>   latente.
> - OCT-030…032: il documento vero, `backend.app.main.app.openapi()`. Nessun punto segnalato; le quattro forme sono
>   presenti (una barriera contro un walker che smette di leggere); ci sono solo forme verificate.
>
> Registrato in `scripts/test_runner/_backend_schemas.py`, con la voce additiva `openapi-client-text`, nella classe di
> default della categoria (`write-scoped`): importare `backend.app.main` apre il log della corsia (`configure_logging`).
>
> **Decisioni del test-author, accolte (notturne, da rivedere)**:
> - OCT-001 scatta anche per un'opzione in più o per una seconda esecuzione;
> - OCT-017 e 032 fanno fallire le forme mai verificate invece di saltarle (FastAPI oggi non ne scrive);
> - il `trim()` usa l'insieme di spazi di JavaScript (`str.strip()` ne toglie di più);
> - l'estratto del messaggio è centrato sul primo carattere vietato.
>
> **⚠️ Fuori pista**: `utils static-route-confinement` importa la stessa app ma è dichiarato `pure`. L'incoerenza non
> è nel mio perimetro: la segnalo al coordinatore.
>
> Osservazione fuori perimetro: anche i valori stringa di `enum` escono crudi, in `z.enum(["…"])` e `z.literal("…")`.
> Oggi sono 884, nessuno con `"`, `\` o un a capo. La guardia non li copre. Il client degli strumenti
> (`generate-tools-client.mjs`) genera con `withDescription: false` e `withDocs: false`, quindi le descrizioni non lo
> toccano.

#### E-5.2 — La regola nella documentazione ✅ (2026-10-16)
> La regola 4 di «📜 Contract Rules» in `developer/api/overview.md` (pagina solo inglese) è scritta da `docs-writer`, poi
> rivista da me su questi punti:
> - il nome della colonna da «Breaks the client» a «Must not contain», perché un `\d` non rompe, cambia il testo;
> - liste e dizionari al posto di `items`/`additionalProperties`, e la frase sul loro verso opposto;
> - il JSDoc «dentro un tipo esportato (campi, elementi, membri di unioni)»;
> - «unions» al posto di «optional unions», perché i latenti stanno anche nei `oneOf`;
> - `*/` vietato in «any schema».
>
> L'introduzione della sezione ora dice «Four rules», e solo le prime tre rompono la build. Una tagged template passa
> `vite build`, e `front build` ignora l'uscita di `svelte-check`.

#### E-5.3 — Prove ✅ (2026-10-16)
> Sulla base `a2f658097` (A6d e A6e), arrivata con un fast-forward che non ha toccato i file di E-5. Una prova alla
> volta, con `nice -n 10` e il carico sotto 70.
> - `schemas openapi-client-text`: 78 passati (`/tmp/libreFolio_e5_newbase.log`). Sul documento di oggi ci sono 4 447
>   punti (2 606 JSDoc, 1 463 tra virgolette, 63 template, 315 Handlebars), 157 campi tipizzati con un componente e 49
>   latenti.
> - **Mutazione E2b**, temporanea e poi annullata (verificato con `git diff --quiet`): la docstring di
>   `EmailInstanceConfig` riportata su più righe con ``` ``GET /system/instance`` ```.
>   - Il risultato: rosso solo OCT-030 (1 fallito, 77 passati), sul punto
>     `InstanceConfigResponse.email -> EmailInstanceConfig`, forma template, carattere `` ` ``, con la cura nel
>     messaggio (`/tmp/libreFolio_e5_mutation.log`).
> - `ruff check` e `black --check` (`--config pyproject.toml`) puliti sui due file Python; `git diff --check` pulito.
> - `check-orphans`: tutti i file sono registrati e raggiungibili da `all` (342 file di backend).
> - `mkdocs build` stretto: uscita 0, nessun WARNING o ERROR, 3 068 URL risolti. `check-links`: 96 link validi. La
>   regola 4 esce con la tabella di 4 righe, lo span dei doppi backtick e il blockquote.

### Checkpoint E-5 🧊 (2026-10-16) — FROZEN, in attesa del commit del coordinatore
> **Base**: HEAD `a2f658097`. I file:
> - nuovo `backend/test_scripts/test_schemas/test_openapi_client_text.py`;
> - `scripts/test_runner/_backend_schemas.py`, 19 righe aggiunte;
> - `mkdocs_src/docs/developer/api/overview.md`, la regola 4;
> - il backlog, con E-5 chiuso;
> - questo piano.
>
> Nessun codice dell'applicazione, nessun file di A; `fix-openapi-discriminators.mjs` non è toccato. Le prove della
> diagnosi stanno in `/tmp/libreFolio_e5_bt/`, con una copia nella cartella della sessione (`files/e5_bt/`).
>
> **Ingresso** (2026-10-16): E-5 è salvato in `43ad48952` e `fc418255b`, e la base è fusa in `c47d02a28` (con B2 e
> Y4b).
> - `schemas openapi-client-text`: 78 passati (`/tmp/libreFolio_e5_after_b2.log`). 4 478 punti, nessuno segnalato.
> - I latenti passano da 49 a 52, con tre schemi nuovi di B2: `RestoreUpload`, `RestoreStageReport` e `RestoreStage`
>   (`schemas/backup.py`). Hanno docstring su più righe con doppi backtick, la forma di E2b. Oggi si raggiungono solo
>   come membri di unione e come risposte; un campo tipizzato direttamente con uno di loro romperebbe il client. Li ho
>   segnalati al coordinatore, che decide se girarli a B.
> - ✅ In `dev_release2` al treno 83 (merge `01598f9ad`). I tre latenti di B2 li gira a B il coordinatore.

### E5b — gli agganci della verifica nei file di A (2026-10-16)

Via del coordinatore (02:58): A6d e A6e sono in `dev_release2`; prima chiudere E-5, poi E5b sulla base nuova. Per le
E2E di E5b ed E4b si chiede lo slot. La procedura è quella del pacchetto `/tmp/libreFolio_e5b/README.md` (E5.3).

#### E5b.0 — Base e patch ✅ (2026-10-16)
> Base: HEAD `c47d02a28`, cioè E-5 più la fusione di `dev_release2` (`16cff5610`, con A6d, A6e, B2 e Y4b).
>
> Il controllo (`git apply --check`):
> - le patch sui file di A (`e5b_hooks_A6d.patch`, poi `e5b_users_flag_optional.patch`) passano, con spostamenti di
>   1–3 righe;
> - `e5b_mine.patch` passa da sola. `e5b_mine_optional.patch` da sola no, perché il suo contesto è `holds_place`, che
>   aggiunge la prima: `git apply --check` con due patch sullo stesso file non le concatena.
>
> Applicate in quattro invocazioni separate, solo nel worktree e mai nell'indice: le mie due, poi le due di A. Nessun
> file `.rej` né `.orig`. Il risultato: 21 file di codice; `verification.py` riceve `holds_place` e `place_holders`.
>
> La revisione contro A6e: da `ce4acff6c`, dove le patch erano state preparate, A6e ha cambiato solo `update_profile`,
> in tre file su 19 (`api/v1/auth.py`, `schemas/auth.py`, `user_service.py`). Lì aggiunge la password attuale per
> cambiare l'email, `email_verified_at = None` e la fine delle altre sessioni. Nessun aggancio di E5b tocca
> `update_profile`, e quelli che stanno negli stessi file (login, `register`, `update_user_status`, `set_user_active`)
> convivono senza intrecci.
> - Ogni funzione che gli agganci chiamano esiste in `verification.py`: `awaiting_verification`, `holds_place`,
>   `place_holders`, `registration_email_work` (più quelle importate pigramente).
> - `ruff check` e `black --check` (`--config pyproject.toml`) sono puliti sui 12 file Python; `prettier --check` è
>   pulito sugli 8 file del frontend.

#### E5b.1 — i18n e client ✅ (2026-10-16)
> `e5b_i18n.py` aggiunge `email.verification.{registered, signUpUnavailable, settingNeedsEmail, settingUnavailable}`
> nelle 4 lingue del mio catalogo. Prima di lanciarlo ho verificato due cose:
> - la riscrittura con `indent=2` dà un file identico a quello di oggi, quindi il formato non cambia;
> - «Settings › Email» corrisponde alle etichette vere nelle 4 lingue (Impostazioni/Paramètres/Configuración ›
>   Email/E-mail/Correo).
>
> `dev.py i18n build`: 4 705 chiavi × 4 lingue. `i18n check` passa, in modalità stretta. `dev.py api sync` passa: il
> client rigenerato contiene `verification_required` e `holds_place` e si legge con 0 errori di sintassi e 0 template
> taggati (`ts_scan.cjs` di E-5).

#### E5b.2 — I test al loro posto ✅ (2026-10-16)
> Gli 8 file del pacchetto sono copiati nei loro percorsi (prima nessuno esisteva) e registrati come dice
> `tests/REGISTRATION.md`, in modo additivo:
> - `_backend_api.py`: `api email-verification-hooks`, pura;
> - `_backend_services.py`: `services email-verification-hooks`, pura;
> - `_frontend_utility.py`: 2 file in core-unit e 4 in component-unit.
>
> La prima esecuzione:
> - `services email-verification-hooks`: 25 passati, 2 falliti;
> - `--no-shared-server api email-verification-hooks`: 6 passati, 8 falliti;
> - Vitest dei 6 file più `auth.test.ts`: 114 passati, 2 falliti (UVR-02).
>
> **⚠️ Fuori pista**:
> - I 10 rossi del backend hanno una causa sola, `INVITE_REQUIRED`. Dal commit di A `683b4ff5b` («new instances
>   register by invitation», già dentro A6d) un'istanza nuova parte con `registration_mode = invite`, mentre i test
>   preparati di notte, mai eseguiti, contavano su `open`. La cura è nei test: impostare `open` nei loro DB privati,
>   senza `LIBREFOLIO_REGISTRATION`, che bloccherebbe la modalità.
> - UVR-02: in jsdom `fireEvent.click` arriva anche a un bottone disabilitato, e il gestore delegato di Svelte 5 parte;
>   un browser non manda click a un controllo disabilitato. Lo stile di casa è `toBeDisabled()` senza click.
>
> Correzioni e il caso EVH in più (la risposta del `PATCH` dice `holds_place: true`): `test-author`.
>
> **Note implementazione**: correzioni del `test-author`, solo nei file di test.
> - L'helper `_registration_open(engine)`, fatto come `_option`, aggiorna la riga `registration_mode` a `open` e
>   verifica che una riga sia cambiata.
>   - Nei servizi lo usano EVK-002, nel caso senza invito, ed EVK-003.
>   - Nelle API: EVH-001, i due casi senza invito di EVH-004, EVH-005 e `_registered_and_waiting`, quindi
>     EVH-006/007/008/011.
>   - Restano sul default `invite` EVH-002 (il primo account entra con ogni modalità), EVH-003 (con l'invito) ed
>     EVH-009/010 (nessuna registrazione).
> - UVR-02 non clicca più il bottone disabilitato e tiene `toBeDisabled()`, `data-disabled-reason="limit"` e il testo.
>   La convenzione di A, scritta in `SettingControls.test.ts`, è cliccare un bottone disabilitato solo quando il
>   componente ha una guardia nel gestore; `UserRow` non ne ha su nessun bottone.
> - Nuovo **EVH-012**: la risposta del `PATCH` no-op (`is_active: false`) e quella della promozione di un account in
>   attesa dicono `holds_place: true` (`is_active` resta false, il link è ancora valido), e lo stesso dice
>   `GET /users`. Con il link scaduto, la stessa risposta dice `false`: il flag è calcolato.
> - La descrizione di `api email-verification-hooks` nel runner ora cita il flag nella risposta del `PATCH`.
>
> Le esecuzioni, una alla volta:
> - `services email-verification-hooks`: 27 passati (`/tmp/libreFolio_e5b_svc_hooks_2.log`);
> - `--no-shared-server api email-verification-hooks`: 15 passati (`/tmp/libreFolio_e5b_api_hooks_2.log`);
> - Vitest dei 6 file più `auth.test.ts`: 7 file, 116 passati (`/tmp/libreFolio_e5b_vitest_2.log`);
> - `ruff`, `black` e `prettier` puliti.
>
> Il commento rimasto indietro in `SettingControls.test.ts:239`, punto 3 del README del pacchetto, ora dice che
> `require_email_verification` era un segnaposto fino a E5b.

#### E5b.3 — Documentazione ✅ (2026-10-16; l'esito sotto, in «E5b.3, seguito»)
> `docs-writer` applica le sue bozze E5b (`/tmp/libreFolio_e5b/docs/`):
> - `admin/email.en.md`, la sezione «Email Verification»;
> - `admin/users.en.md`, modifiche 1–3;
> - le pagine developer, le modifiche E5b;
> - la riga EN di `admin/settings.en.md` (IT/FR/ES li allineo io, poi `translate-stamp`);
> - `user/getting-started.en.md`, modifiche 1–3, solo EN (debito di traduzione).
>
> `extra_pages.md` aspetta il via del coordinatore (pagine tradotte di altri).
>
> **Decisione notturna, da rivedere: la riga di `admin/settings`.** Le pagine IT, FR ed ES erano già indietro prima di
> E5b: hanno ancora la riga «Abilita registrazione», che A ha cambiato in inglese. All'HEAD l'MD5 della pagina inglese
> (`ba4a8f…`) non è quello della cache (`07bbf1…`, ultima traduzione il 10/10).
> - Allineo a mano solo la mia riga (IT «Richiedi verifica email», FR «Vérification Email Requise», ES «Verificación
>   Email Requerida»), così chi legge in quelle lingue non trova più «in arrivo».
> - **Nessun `translate-stamp`**: segnerebbe come tradotto anche il debito di A. La pagina resta alla pipeline.
> - Il link resta di pagina, `email.md`, perché `admin/email` è solo in inglese; il testo del link segue la `nav`
>   (Email, E-mail, Correo).

#### E5b.4 — CHANGELOG ✅ scritto (2026-10-16)
> Il coordinatore aveva rimandato la riga di E5a a E5b. Ora c'è:
> - in «✨ Added», «**Email verification at sign-up**», con il comportamento e le rotte;
> - in «🔄 Changed», `LIBREFOLIO_MAX_USERS` che conta gli account in attesa con il link vivo, la riattivazione
>   senza un posto nuovo e la revoca del link quando un account si attiva o con `user deactivate`.

#### E5b.5 — Prove ✅ sulla base `c47d02a28` (2026-10-16, notte), E2E escluse
> Una alla volta, `nice -n 10`, carico sotto 70; gli script sono `/tmp/libreFolio_e5b_gates.sh` e `gates2.sh`.
>
> Backend, primo giro:
>
> | Selettore | Esito |
> |---|---|
> | `services registration` | 147 ✅ |
> | `services email-verification` | 115 ✅ |
> | `services settings` | 23 ✅ |
> | `services global-settings` | 19 ✅ |
> | `services user-profile` | 42 ✅ |
> | `services account-tokens` | 65 ✅ |
> | `api auth` | 58 ✅, 2 ❌ |
> | `api registration` | 77 ✅ (un avviso: `HTTP_422_UNPROCESSABLE_ENTITY`, già nel backlog come E-4) |
> | `api users-admin` | 59 ✅, 5 ❌ |
> | `api settings` | 98 ✅ |
> | `api email-verification` | 48 ✅ |
> | `utils dev-cli-image` | 75 ✅ (il dev.py dell'immagine carica `user_cli` con l'import nuovo) |
>
> **⚠️ Fuori pista**, due test di A da adattare alla firma e al contratto nuovi di E5b (`test-author`, solo modifica):
> - `test_auth_api.py`: `test_register_disabled_allows_bootstrap_when_no_users` e LOOP-002 chiamano la rotta
>   `register` direttamente, con argomenti posizionali `(request, session)`. L'aggancio aggiunge
>   `background: BackgroundTasks` in seconda posizione, così `session` restava al `Depends` di default. Ora passano
>   `background=BackgroundTasks()` e `session=session` per nome, come fa FastAPI. Con l'opzione spenta nessun lavoro
>   viene accodato, quindi il senso dei test non cambia.
> - `test_users_admin_api.py`: `USER_ITEM_KEYS` fissava i 7 campi esatti di un account. Con `holds_place` sono 8, e
>   `_user_item_violations` ora pretende `holds_place: False` per ogni account del file, quindi il contratto resta
>   stretto. Ho corretto anche la docstring di UADM-052, da «seven fields» a «eight».
>
> Rilanciati dopo le correzioni: `api auth` 60 ✅, `api users-admin` 64 ✅.
>
> Frontend e documentazione (`/tmp/libreFolio_e5b_gates2.sh`):
>
> | Prova | Esito |
> |---|---|
> | `dev.py front check` | 1 errore ❌, poi 0/0 ✅ |
> | `front-utility core-unit` | 173 file, 5 926 ✅ |
> | `front-utility component-unit` | 150 file, 3 882 ✅ |
> | `theme-roles.mjs --check` | pulito ✅ |
> | `check-orphans` | ✅ |
> | `mkdocs build` stretto | uscita 0, nessun WARNING o ERROR ✅ |
> | `check-links` | 96 ✅ |
>
> **⚠️ Fuori pista**, un terzo test di A (`test-author`, solo modifica): in `LoginCard.test.ts:459`
> `EMITTED: Record<AuthErrorKey, true>` elenca ogni chiave che lo store emette e la disegna nel riquadro `login-error`.
> - E5b aggiunge `email.verification.loginRequired` ad `AuthErrorKey`, ma per quella chiave `LoginCard` mostra
>   `VerificationNotice` al posto del riquadro.
> - Aggiungerla al record avrebbe spostato il rosso dal type check all'esecuzione. Il record è ora tipato
>   `Record<Exclude<AuthErrorKey, 'email.verification.loginRequired'>, true>`, con il perché nel commento: la chiave è
>   coperta da LVR in `LoginCard.verification.test.ts`.
> - Il controllo resta esaustivo per le chiavi del riquadro.
>
> Rilanciati: `front check` 0 errori e 0 avvisi; Vitest di `LoginCard.test.ts` e `LoginCard.verification.test.ts`,
> 2 file, 39 ✅.
>
> Lint finale sul delta intero: `git diff --check` pulito; `ruff` e `black` puliti sui 19 file Python; `prettier`
> pulito sul frontend. La porta 6188 è libera.
>
> Non ancora fatti: le E2E (serve lo slot dal coordinatore) e la revisione di sicurezza mirata (in E6).

#### E5b.3, seguito — Documentazione applicata ✅ (2026-10-16)
> `docs-writer` ha applicato tutte le sue bozze E5b; le modifiche E4b ed `extra_pages.md` restano fuori.
>
> Le pagine:
> - `admin/email.en.md`: la sezione «✅ Email Verification», con `#verification`, `#verification-switch`,
>   `#verification-waiting` e `#verification-limits`;
> - `admin/users.en.md`: `#waiting`;
> - `admin/settings.en.md`, la riga;
> - `user/getting-started.en.md`: `#verify-email`, solo EN;
> - `developer/backend/email.md`;
> - le pagine developer `architecture/settings`, `security`, `database/users_access` e `access_control`;
> - `frontend/components/features/auth` e `settings`.
>
> Nessuna ancora tolta.
>
> Le verifiche fatte da me sul codice: le email in attesa partono nella lingua dell'istanza, perché la riga
> `UserSettings` nasce solo al primo aggiornamento; `user create` passa da `create_user`, quindi non aspetta mai; i
> limiti sono 10 ogni 15 minuti per indirizzo, con IPv6 per /64, più 5 minuti e 3 all'ora per account. Ho portato
> EVH-001…012 nella tabella «Testing».
>
> Lasciato aperto da `docs-writer`: la bozza E4b di `admin/email` va rifatta sul testo di A6e (il riquadro «Held for
> now» e il punto di sicurezza sono stati riscritti).

### Checkpoint E5b, intermedio 🧊 (2026-10-16) — FROZEN, in attesa del commit del coordinatore
> Avviso del coordinatore (03:45): A6c, con le regole della password, entra prima di E5b, verso le 04:30. Tocca
> `api/v1/auth.py`, `schemas/auth.py` e `RegisterCard.svelte`, gli stessi file di tre agganci. Il checkpoint finale
> arriva dopo il merge con A6c; questo intermedio serve perché il merge parta da un albero committato.
>
> **Base**: HEAD `c47d02a28`. Il delta: 48 file tracciati e 8 nuovi.
> - Il codice degli agganci: 18 file di A (10 del backend, `user_cli.py` compreso, e 8 del frontend) più `verification.py`.
> - I test: gli 8 file nuovi; tre test di A adattati (`test_auth_api.py`, `test_users_admin_api.py`,
>   `LoginCard.test.ts`) più `test_settings_api.py` dalla patch; il commento di `SettingControls.test.ts`.
> - La registrazione nei 3 file del runner.
> - i18n × 4.
> - Le docs: 11 pagine EN più la riga della pagina impostazioni in IT/FR/ES.
> - Il CHANGELOG.
> - Questo piano.
>
> Salvato dal coordinatore: `2d954624e` (feat, 54 percorsi) e `98812863f` (journal). `CHANGELOG.md` è rimasto fuori:
> lo scrive il coordinatore all'ingresso, con le mie due righe (Added e Changed), quindi l'ho riportato a HEAD.

#### E5b.6 — Il merge con A6c ✅ (2026-10-16, 04:40–05:07)
> Il coordinatore ha aperto il merge di `dev_release2` `1704cfcf7` (treno 90, A6c: le regole della password) sopra
> `98812863f`.
>
> Tre conflitti, risolti tenendo entrambi i lati e messi in stage:
> - `registrationErrors.ts`: `REFUSAL_KEYS` ha sia `PASSWORD_TOO_WEAK` (A6c) sia `EMAIL_VERIFICATION_UNAVAILABLE`
>   (E5b);
> - `developer/architecture/security.md`: la frase di A6c (le regole della password pubblicate da `/system/instance`)
>   più `/verify-email` nei punti sul token nel frammento e sulle pagine dei link («All three declare»);
> - `developer/frontend/components/features/auth.md`: le due righe della tabella, prima quella di A6c.
>
> Ho rivisto a occhio i 18 file toccati da entrambi i lati e fusi da soli:
> - `auth.py`, `register`: prima `_refuse_weak_password`, poi `register_user`, poi il mio aggancio; coerente;
> - `schemas/auth.py`, `RegisterCard.svelte`, `test_auth_api.py` (le chiamate per nome; A6c non ne aggiunge di
>   dirette), `test_users_admin_api.py`, `user_cli.py`, le pagine `admin/settings.*`, le pagine developer e i due file
>   del runner: entrambi i lati presenti.
>
> Prove, una alla volta, `nice`:
>
> | Prova | Esito |
> |---|---|
> | `api sync` | ✅ |
> | `i18n build` | 4 754 chiavi ✅ |
> | Vitest del modulo auth | 15 file, 400 ✅ |
> | `front check` | 0/0 ✅ |
> | `api auth` | 88 ✅ |
> | `api registration` | 96 ✅ |
> | guardia E-5 | 78 ✅ |
> | `mkdocs build` stretto | 0 WARNING o ERROR ✅ |
>
> Commit di merge del coordinatore: `f33836892`. Il ramo `dev` era già andato avanti (`72e66d1a6`): il coordinatore
> aggiorna la base al prossimo checkpoint.

#### E5b.7 — Revisione di sicurezza mirata ✅ scritta (2026-10-16), prove dopo le 06:45
> Su richiesta del coordinatore, l'agente `security-review` ha letto, in sola lettura, `98812863f`: il nucleo di E5a
> e gli agganci di E5b.
>
> Nessun modo di aggirare la verifica: login e ogni altra rotta controllano `is_active` (`get_current_user`); il link
> di reset imposta la password ma non attiva e non dà un cookie; gli inviti aspettano anche loro; le sole scritture di
> `is_active=True` sono `confirm_email` e le due dell'admin. Niente di nuovo dice a chi non è entrato se un account
> esiste. Sani anche i token (scopo, uso singolo con UPDATE condizionale, hash), la guardia delle impostazioni (la
> sola rotta che le scrive è la bulk), la pagina `/verify-email` (frammento, `replaceState`, `no-referrer`) e i log.
>
> | # | Gravità | File | Righe | Vulnerabilità | Confidenza |
> |---|---|---|---|---|---|
> | 1 | 🟡 MEDIUM | `services/email/verification.py`, `api/v1/auth.py` | 207–251, 314–347; 263–266 | Con la registrazione `open` e l'opzione accesa, una sola casella si può inondare di email di verifica: nessun limite per destinatario né per client, e il caso dell'indirizzo cambia la casella | 8/10 |
> | 2 | ⚪ LOW | `services/email/verification.py` | 342–347, 207–230 | Corsa sul limite utenti: il `resend` con il link scaduto controlla `full` fuori dalla transazione | 8/10 |
>
> Le cure, nel mio file, applicate in E5b (decisione notturna, da rivedere):
> - `VERIFICATION_BY_MAILBOX`, 3 email all'ora per casella, con l'indirizzo in casefold, come `FORGOT_BY_MAILBOX`:
>   `peek` prima di creare qualcosa e `hit` solo dopo un invio riuscito, quindi un'email fallita non conta. Vale sia
>   per l'email della registrazione (l'account aspetta senza email, si chiede di nuovo il link) sia per il `resend`
>   (429 neutro con `Retry-After`).
> - `needs_place`: con il link scaduto, `user_usage` si riconta dentro la transazione, come fa `register_user`.
> - La prima scrittura è `revoke_tokens`, e se non revoca niente l'account non aspetta più: rollback con
>   `EmailVerificationNotNeededError` o `VerificationAccountDisabledError`, e nessun link nuovo (nota 6 del
>   revisore). Nella registrazione, questo caso dà la stessa riga `info` del controllo iniziale.
> - Un `resend` con credenziali sbagliate ora logga `Verification resend refused: wrong credentials`, senza campi
>   (nota 7).
>
> I test (`test-author`): fixture con un `VERIFICATION_BY_MAILBOX` privato in EMV, EVA ed EVH; nuovi EMV-043…048 ed
> EVA-016; EMV-002 fissa il limite. Le docs (`docs-writer`, 11 blocchi): `admin/email.en.md` con la tabella dei
> limiti, il paragrafo sotto e il log; `developer/backend/email.md` con i passi, i limiti e i log. Ho corretto due
> righe del log per il caso «non aspetta più», che è `info`. Il runner e la tabella «Testing» sono aggiornati.
>
> **Da decidere, nella lista del mattino del coordinatore**:
> - un limite per client sulle email di registrazione (10 all'ora per indirizzo). La mia proposta: oltre, l'account
>   si crea ma l'email non parte; l'alternativa è un 429 sulla registrazione, contratto di A;
> - il `PATCH is_active=false` no-op lascia l'attesa armata: propongo che revochi, come `user deactivate`. Rivede la
>   mia decisione notturna;
> - il link si spende al caricamento della pagina (scanner di posta con JavaScript): propongo un pulsante «Conferma».
>
> Fuori dalla cura, osservazioni del `test-author`:
> - le email non sono uniche senza distinzione di maiuscole (codice e indice di A): il limitatore fa da paracadute, e
>   la cura alla fonte è di A;
> - con richieste in parallelo, tra `peek` e `hit` può passare qualche email in più, comunque limitata dagli altri
>   limiti;
> - i limitatori valgono per processo, come gli altri.

#### E5b.8 — Pagine in più, autorizzate dal coordinatore ✅ (2026-10-16)
> Solo EN:
> - `admin/configuration.en.md`: la riga di `LIBREFOLIO_MAX_USERS` e `#user-limit` (la prima riga e il paragrafo
>   finale);
> - `admin/cli_tools.en.md`: il punto 📬 dopo il 📏 di `activate`;
> - `admin/index.en.md`: la riga Email, nella forma per E5b.
>
> IT, FR ed ES non hanno quelle righe: sono aggiunte di A (e la mia riga Email) non tradotte dal 10/10. Il debito
> c'era già, quindi **nessun timbro**, come dice la regola del coordinatore. Nell'handoff le dichiaro come file di A e
> di H.

#### E5b.9 — E2E al loro posto ✅ (2026-10-16), da eseguire nello slot
> `frontend/e2e/auth-email-verification.spec.ts`, EVE-E-01…05, del `test-author`.
> - 01–03: fuori sessione, su risposte simulate: la registrazione che aspetta, il 409 `EMAIL_VERIFICATION_UNAVAILABLE`,
>   il 403 `EMAIL_NOT_VERIFIED` con il nuovo invio.
> - 04–05: `e2e_test_admin` con `GET /system/instance` simulato: l'interruttore spento con `email.links` falso,
>   usabile con vero; niente salvato.
>
> La modalità `open` si ottiene riscrivendo nel browser la risposta vera (`serveRegistrationMode`), quindi niente
> scrive nel DB condiviso. `fixtures/instance-email.ts` è identico a quello del pacchetto E4b (verificato con `cmp`),
> e l'ho annotato nel README di E4b.
>
> Registrato in `front-utility` come `email-verification`. Ho controllato i `data-testid` contro i componenti dopo
> A6c: ci sono tutti; `info-banner-{variant}` e `settings-tab-${id}` sono dinamici.
>
> **Decisione notturna, da rivedere**: nessun aggancio di test nuovo nel prodotto (eventi `auth.register.*`, oppure
> `data-disabled-reason` sull'interruttore). `RegisterCard` è appena cambiato con A6c, e le chiavi le fissano già i
> Vitest RCV, RVR e GVR.

#### E5b.10 — Regola dei colori ✅ (2026-10-16)
> Uno scanner (`/tmp/libreFolio_mixed_roles.py`, provato su un caso positivo) cerca, in ogni attributo `class` e in
> ogni stringa, un ruolo `-lf-` insieme a classi di tavolozza o a `dark:`. L'ho passato su `features/email/` (E2, E3p,
> E5a, E4a), su `routes/verify-email/` e sui quattro file di A toccati da E5b: 0 elementi misti. Comunicato al
> coordinatore.
>
> **Da fare dopo le 06:45**, una prova alla volta:
> - `services email-verification` ed `email-verification-hooks`;
> - `api email-verification` ed `email-verification-hooks`;
> - `api users-admin`;
> - `check-orphans`;
> - `mkdocs build` e `check-links`;
> - poi le E2E nello slot del coordinatore, e l'handoff finale.

#### E5b.7, seguito — Le decisioni del coordinatore (05:15) e le due cure in più ✅ scritte, prove dopo le 06:45
> Le risposte del coordinatore:
> - il limite per casella, il riconteggio nella transazione e la riga di log: via, già applicati;
> - **limite per client sulle email di registrazione**: via, come proposto (decisione notturna, da rivedere);
> - **punto 1, il `PATCH is_active=false`**: via, revoca come `user deactivate`, per la regola «ogni cambio di stato
>   dell'admin revoca»;
> - **punto 2, il pulsante «Conferma»**: nella lista di domattina, perché cambia l'esperienza.
>
> **Cura A, il limite per client**:
> - In `verification.py`: `REGISTRATION_EMAILS_BY_ADDRESS`, 10 all'ora per indirizzo del client (IPv6 per /64), e
>   `registration_email_allowed()`, che conta solo i passaggi permessi; senza indirizzo non limita.
> - In `auth.py`, `register` riceve `http_request: Request` dopo `background`. Oltre il limite l'account nasce in
>   attesa (201, `verification_required: true`) ma l'email non parte; c'è una riga `info` «Verification email held»,
>   e il titolare chiede di nuovo il link dalla pagina di accesso, con i limiti del `resend`.
> - Niente 429 sulla registrazione: il contratto di A resta com'era.
>
> **Cura B, revisione della mia decisione notturna** (il `PATCH is_active=false` su un account in attesa, che era un
> no-op). In `user_service.update_user_status`, con `is_active is False` su un account già inattivo, si revocano i
> token `EMAIL_VERIFICATION`, e se qualcosa è stato revocato vale come cambio: commit e log. Per un account in attesa
> l'attesa finisce, i link non valgono più, il posto si libera, la risposta dice `holds_place: false` e il login dice
> `ACCOUNT_DISABLED`. Un account inattivo normale resta com'è. La scheda Utenti non mostra «Disattiva» per un account
> inattivo: nell'interfaccia resta «Elimina», mentre API e CLI chiudono l'attesa.
>
> Il resto:
> - `ruff` e `black` puliti sui tre file;
> - le descrizioni del runner aggiornate (EVH, EVK);
> - i test (EVK, EVH ed EVH-012 rivisti, e le due chiamate dirette in `test_auth_api.py` con `http_request=`) al
>   `test-author`, le docs (`admin/email`, `admin/users`, `developer/backend/email.md`, `access_control.md`) al
>   `docs-writer`, solo scrittura.
>
> **Note implementazione**, test e docs delle cure A e B, scritti senza eseguirli. Il `test-author` ha lanciato `ruff`
> e `black` alle 05:23, puliti.
> - EVK:
>   - EVK-004 riscritto: disattivare un account già inattivo che aspetta revoca il link e fa il commit;
>   - EVK-009 nuovo: un account inattivo normale resta com'è, senza commit né log;
>   - EVK-010 nuovo: `registration_email_allowed`, 10 e poi rifiuto (un rifiuto non conta), il /64, `None`, la finestra.
> - EVH:
>   - un `REGISTRATION_EMAILS_BY_ADDRESS` privato;
>   - EVH-011 riscritto: la disattivazione chiude l'attesa (`holds_place: false`, conferma 400 `revoked`, un posto
>     libero in più, login `ACCOUNT_DISABLED`);
>   - EVH-012 riordinato: prima la promozione (`true`), poi la disattivazione (`false`);
>   - EVH-013 nuovo: con il limite a 1, due registrazioni, una sola email; la seconda aspetta con la tenuta, c'è la riga
>     `info`, e il suo `resend` va.
> - `test_auth_api.py` di A: le due chiamate dirette passano `http_request=_register_http_request()`.
> - Le docs (`docs-writer`):
>   - `admin/email.en.md`: la tabella dei limiti, rinominata «📏 Limits of the Verification Emails» con la stessa
>     ancora, con la riga delle registrazioni; il punto «To turn it away»; la riga di log;
>   - `admin/users.en.md`;
>   - `developer/backend/email.md`: gli agganci, le funzioni, i limiti e i log;
>   - `access_control.md`: la riga del `PATCH` e quella di `require_email_verification`.
>
>   Le righe EVK ed EVH della tabella «Testing» le ho aggiornate io.
>
> **Per la lista del mattino**, con la revisione della cura A:
> - un'email trattenuta è silenziosa: la pagina dice «We sent you an email» e il titolare deve pensare da solo a
>   chiedere di nuovo il link;
> - dietro un proxy non fidato (`FORWARDED_ALLOW_IPS`) tutti i client hanno lo stesso indirizzo, quindi dopo 10
>   registrazioni in un'ora ogni email di registrazione è trattenuta. Vale come per gli altri limiti per indirizzo, ma
>   qui senza un rifiuto visibile.

### Dopo E4b — analisi di E6 (2026-10-16, notte, sola lettura)

Su invito del coordinatore (05:25), durante il fermo della macchina. Base `bf1586ddb`: E5b salvato in quattro commit
(`207dfbafd`, `6d6965293`, `33da05e31`, `bf1586ddb`), prove dopo le 06:45. Il pacchetto di E4b resta in `/tmp` finché
le prove di E5b non sono verdi.

#### Prima, E4b (dal pacchetto `/tmp/libreFolio_e4b/`, README aggiornato)
1. `git apply --check` di `e4b_hooks_A.patch`, `e4b_mine.patch` e delle patch dei test sulla base del momento.
   - Dopo A6e e A6c vanno rivisti `ForgotPasswordCard` e `LINK_SHARE_ACTIONS`.
   - `fixtures/instance-email.ts` c'è già, uguale byte per byte: non va ricreato.
2. L'aggancio in `update_profile` (`a6e_hook/e4b_update_profile_hook.patch`, pronto):
   - `background` dopo `http_request`;
   - `old_email` letto prima di `user_service.update_profile`;
   - `email_changed_work` accodato solo al cambio d'email.

   I suoi test sono da scrivere (`test-author`): solo al cambio d'email, non per il solo username né per lo stesso
   indirizzo in casefold, risposta e cookie invariati, nessun indirizzo nei log della rotta.
3. Le E2E ESL-E (`email-send-link.spec.ts`) e FPE-E (`forgot-password-email.spec.ts`) nello slot.
4. Le docs:
   - da rifare sul testo di A6e: `admin_email_e4b.md` (il riquadro «Held for now» e il punto di sicurezza «Forgotten
     passwords are held»);
   - `user/getting-started.en.md`, modifiche 4–6, che sono debito per la pipeline;
   - `user/settings/profile.en.md`, la modifica 5, file di A con la frase di A6e;
   - la riga Email di `admin/index.en.md`, nella forma «entrambi i lotti».
5. La riga del CHANGELOG di E4b, il testo per il coordinatore.
6. Una revisione di sicurezza mirata (`security-review`): il «password dimenticata» aperto, cioè la tenuta tolta, e
   l'avviso al vecchio indirizzo.

#### E6, cosa resta (dal §7 e dal §8)

| # | Voce | Stato oggi | Proposta |
|---|---|---|---|
| 1 | **Galleria**: lo scatto `settings/email` | preparato in E2b, mai eseguito: due giri con il diff vuoto, nello slot del coordinatore | slot della galleria; senza `links` lo scatto non cambia (E3p) |
| 2 | **`all-backend`** con i conteggi della base più i nuovi | mai eseguito su E intero | slot pesante, dopo E4b |
| 3 | **E2E del dominio**: `email-tab`, `email-verification`, le due di E4b, più `auth` e `auth-links` di A (le card toccate) | `email-tab` verde in E2b; le altre da eseguire | uno slot, `--workers 2` |
| 4 | **`lint --dead-code --scope backend`** | in E1, 7 reperti di passaggio, poi chiamati da E2/E3/E5 | rifarlo: nessun reperto nuovo |
| 5 | **`TODO_FUTURI.md`**, la sezione «📧 Server email… (da P2-1)» | ferma: dice «FUTURO» e il segnaposto | segnarla consegnata nella 1.3 con un rimando, e lasciare come futuro E-7 (il segno «in attesa»), E-8 (la lingua dell'invito), le notifiche (F19), il pulsante «Conferma» se rimandato, i limitatori per processo (più worker), il messaggio dell'email trattenuta |
| 6 | **devWiki**: non c'è `wiki/domains/email.md` | il grafo nel worktree non c'è | pagina di dominio, decisioni D-E1…D-E14, problemi risolti (`MissingGreenlet` dopo il rollback, `address_key` IPv4, il blocco della verifica con i token senza indirizzo, i backtick di E-5), con `project-historian`; `index` e `log` sono condivisi, decide il coordinatore |
| 7 | **CHANGELOG** | righe di E5 consegnate (handoff E5b) | il testo complessivo di E per il coordinatore, con E4b |
| 8 | **Docs finali** | `admin/email.en.md` solo EN per scelta; `getting-started` e le pagine di A/H con debito | un giro di coerenza su `admin/email` (ordine delle sezioni, limiti, log); l'elenco del debito di traduzione per la pipeline; tradurre `admin/email` nella 1.3 lo decide il developer |
| 9 | **Revisione di sicurezza finale** del dominio | E3s, E5b (questa notte) | E4b mirata, poi una lettura d'insieme |

#### Il backlog E aperto, proposta per la 1.3
- **E-4**, il nome deprecato del 422 in `api/v1/settings.py`: è un rinomina di 4 righe in un file di A. Si può fare in
  E6, con l'ok di A.
- **E-2**, i tipi del generatore, **E-3**, `ApiError` nel client condiviso, ed **E-6**, il registro delle schede: tutti
  e tre toccano file condivisi (generatore, client, registro di A/B/X). Proposta: 1.4, salvo un via esplicito.
- **E-7**, il segno «in attesa»: fuori dalla 1.3 per decisione. **E-8**, la lingua dell'invito: lista del mattino, poi
  1.4.

#### Decisioni del developer che toccano E6 (lista del mattino)
- Il pulsante «Conferma» su `/verify-email`: se va nella 1.3 è un lotto piccolo (card, i18n, test, E2E).
- Il messaggio dopo un'email trattenuta: serve un campo nella risposta, oppure una frase che nomini il nuovo invio.
- **Il proxy, priorità del coordinatore per il cloud**: su Fly l'indirizzo del client arriva dal proxy, quindi senza
  `FORWARDED_ALLOW_IPS` (o la sua forma per Fly) ogni limite per indirizzo vale per tutta l'istanza. Tocca anche il
  limitatore del login di A. Va documentato nella pagina «Hosting for Others» (di H) e, forse, nel profilo `managed`.
- Le email uniche senza distinzione di maiuscole: codice e indice di A, alla fonte del flood.

#### Ordine proposto
1. Le prove di E5b, alle 06:45.
2. L'E2E di E5b nello slot.
3. L'handoff finale di E5b.
4. E4b, come sopra.
5. E6: prima le scritture (docs, `TODO_FUTURI`, backlog, testo del CHANGELOG), poi gli slot (`all-backend`, E2E del
   dominio, galleria), la revisione di sicurezza finale e la devWiki, se il coordinatore la apre.
>
> **Risposte del coordinatore (05:27)**:
> - la devWiki `domains/email.md` sì, in E6; `index.md` e `log.md` li fonde lui all'ingresso;
> - `TODO_FUTURI.md` sì, ma solo la sezione «📧 Server email»;
> - E-4 in E6, dopo l'ok di A, che chiede lui;
> - E-2, E-3 ed E-6 rimandate alla 1.4, annotato nel backlog;
> - il proxy: il limitatore del login di A è stato aggiunto a P17; la pagina «Hosting for Others» e il profilo
>   `managed` aspettano la decisione del developer;
> - i tre slot di E6 (la galleria `settings/email`, `all-backend` e l'E2E del dominio) sono annotati, dopo E5b.
>
> **Da A, tramite il coordinatore (06:14), per E6 dopo l'ingresso di A7a (non prima)**: A7a dà un chiamante a
> `build_admin_setup()`.
> - In `developer/backend/email.md` diventano false: «`build_admin_setup()` has no caller», «three emails have a
>   caller», la riga di «Coming Next» e «Never logged… the link». Il link di attivazione generato va nel log una volta,
>   per scelta (P16, da rivedere).
> - In `admin/email.en.md`, nelle sezioni «Emails with a Link» e nei `kind` di «Email sent» manca `admin_setup`.
>
> **Regola delle pagine admin (C-99 del developer, `b171c058e`; dal coordinatore, 16/10 12:11)**:
> - Alla fine della 1.3 il coordinatore riorganizza il manuale admin, in un solo lotto di docs dopo i lotti cloud:
>   - le variabili d'ambiente in una pagina per categoria, al posto di `admin/configuration.md`;
>   - le funzioni del cloud sotto «Hosting for Others».
> - **Fino ad allora**: una variabile nuova si spiega per intero nella pagina della sua funzione. In
>   `configuration.md` ha **una riga sola** nella tabella, con il link. Niente sezioni lunghe in `configuration.md`.
>
> Oggi le otto variabili SMTP sono spiegate per intero in `admin/email.en.md#variables`. In `configuration.en.md`:
> - ha una riga solo la password (tabella dei segreti, con il link);
> - le altre sette (`HOST`, `PORT`, `TLS`, `USER`, `FROM`, `REPLY_TO`, `MAX_PER_HOUR`) non ne hanno nessuna;
> - E4b non tocca la pagina.
>
> **In E6**: sette righe di una frase nella tabella «Main Options», ognuna col link a `email.md#variables` (o alla sua
> sezione), nessuna sezione nuova.

#### E5b.11 — Le prove leggere dopo il fermo ✅ (2026-10-16, 06:48–07:11)
> Base `bf1586ddb`, con lo script `/tmp/libreFolio_e5b_final_checks.sh`: una prova alla volta, `nice -n 10`, carico
> sotto 70. Tra `api registration` e `api users-admin` si è aspettato 5 minuti, con il carico tra 97 e 112.
>
> | Prova | Esito |
> |---|---|
> | `services email-verification` | 124 ✅ (con EMV-043…048) |
> | `services email-verification-hooks` | 32 ✅ (con EVK-009 e 010) |
> | `services user-profile` | 42 ✅ |
> | `api email-verification` | 49 ✅ (con EVA-016) |
> | `api email-verification-hooks` | 16 ✅ (con EVH-011…013) |
> | `api auth` | 88 ✅ |
> | `api registration` | 96 ✅ (un avviso: E-4) |
> | `api users-admin` | 64 ✅ |
> | `tsc -p tsconfig.e2e.json` | solo i 2 errori di base (`onboarding-tour.spec.ts:863`, `files.ts:9`, come in E2b): nessuno nuovo dalla spec né dalla fixture |
> | `prettier --check` sui file E2E | ✅ |
> | `check-orphans` | ✅ (353 file backend raggiungibili) |
> | `mkdocs build` stretto | 0 WARNING o ERROR ✅ |
> | `check-links` | 96 ✅ |
>
> Resta l'E2E `front-utility email-verification`: è la terza della coda degli slot pesanti del coordinatore.

#### E5b.12 — E2E ✅ (2026-10-16, slot 2 del coordinatore, 07:59–08:01)
> `dev.py test --test-port 6188 --data-dir /tmp/librefolio-r13-e --workers 2 front-utility email-verification` su
> `bf1586ddb`: EVE-E-01…05, 5 passati in 56,6 s; il giro intero dalle 07:59:38 alle 08:01:29
> (`/tmp/libreFolio_e5b_e2e.log`). La porta 6188 è libera dopo, e lo slot l'ho restituito alle 08:01. L'avviso SSL di
> MathJax è esterno e innocuo.

### Checkpoint E5b, finale 🧊 (2026-10-16) — FROZEN, pronto per l'ingresso
> **Base**: HEAD `bf1586ddb`, sopra il merge con A6c (`f33836892`). Il lotto è in quattro commit del coordinatore:
> `2d954624e` e `98812863f` (il checkpoint intermedio), poi `207dfbafd`, `6d6965293`, `33da05e31` e `bf1586ddb`. Da
> salvare restano solo questo piano e il backlog (E-2, E-3 ed E-6 rimandate alla 1.4).
>
> **Prove sulla base**:
> - leggere: E5b.11, tutte verdi;
> - E2E: E5b.12, 5 su 5;
> - prima del merge, sulla base `c47d02a28`: E5b.5;
> - dopo il merge con A6c: E5b.6.
>
> Il CHANGELOG lo scrive il coordinatore all'ingresso. Il testo gli arriva con l'handoff: le due righe di E5a ed E5b,
> più la frase sui limiti per casella e per rete e quella sull'attivazione o disattivazione che revoca il link.

### E4b — gli agganci nei file di A, la tenuta tolta, l'avviso al cambio d'email (2026-10-16)

Via del coordinatore (08:30): E5b è entrato (treno 103, merge `dbe232723`), e il ramo è stato portato avanti fino a
HEAD `44d4d7e8e`. Applico E4b, faccio le prove leggere con il carico sotto 50, poi l'handoff. E4b tocca `auth.py`
(l'aggancio in `update_profile`), quindi l'ho detto prima al coordinatore. Il suo via (08:31): tutto subito; al
prossimo aggiornamento della base la riga `Profile updated …` diventa quella di A (`email_changed=…`) e vanno tenuti
tutti e due i lati. A ha dato l'ok per `ForgotPasswordCard`, `linkShareActions.ts` e `i18n/auth`.

#### E4b.0 — Applicazione ✅ (2026-10-16, 08:32)
> Il pacchetto `/tmp/libreFolio_e4b/` è stato preparato di notte e ricontrollato stamattina; tutte le patch passano
> `git apply --check` su `44d4d7e8e`. Applicate in sei invocazioni separate, solo nel worktree:
> - `e4b_hooks_A.patch`: `ForgotPasswordCard.svelte` mostra il modulo quando `email.links` è vero, con il riquadro dei
>   comandi sotto e `data-testid="forgot-email-unavailable"`; `linkShareActions.ts` registra «Spedisci per email»;
> - `e4b_mine.patch`: la tenuta tolta del tutto (`FORGOT_PASSWORD_HELD`, il 409 `FORGOT_PASSWORD_DISABLED`), e i
>   lati del frontend (`emailText.ts`, `forgotPasswordApi.ts`, il catalogo email);
> - `e4b_update_profile_hook.patch`: in `auth.py`, `update_profile` riceve `background` dopo `http_request` e legge
>   `old_email` prima del cambio; dopo un cambio vero accoda `email_flows.email_changed_work`;
> - le patch dei test e del runner (`e4b_tests_mine`, `e4b_runner_desc`, `e4b_runner_notice`).
>
> Nuovi:
> - `test_email_change_notice_api.py` (ECN-001…007);
> - `linkShareRegistration.test.ts` (LSR) e `ForgotPasswordCard.email.test.ts` (FCE), registrati in component-unit;
> - le E2E `settings/email-send-link.spec.ts` (ESL-E) e `auth-forgot-password-email.spec.ts` (FPE-E), in
>   `front-utility` come `email-send-link` e `forgot-password-email`.
>
> Il testo nuovo di `auth.emailRecoveryNotAvailable` nelle 4 lingue, con l'ok di A e il suo suggerimento («chiedi
> all'amministratore un link di reset», possibile anche senza email da A6b): `i18n_recovery.py`, una riga per file.
>
> Le docs: le 45 coppie di `docs_v2` del `docs-writer`, scritte sul testo di oggi. Le ha applicate uno script che
> riconosce i blocchi recintati, provato prima a vuoto: ognuna ha un riscontro solo.
> - Pagine: `admin/email.en.md` (con l'ancora nuova `#email-change-notice`), `admin/users.en.md` (`#send-by-email`),
>   `admin/index.en.md`, `user/getting-started.en.md` (`#forgot-password`), `user/settings/profile.en.md` (di A),
>   e le developer `security.md`, `features/auth.md` (`#forgotpasswordcard`), `features/settings.md`,
>   `backend/email.md`.
> - Nella tabella «Testing» ho messo gli ID al posto dei `⟨…⟩`: ECN-001…007, LSR, FCE, ESL-E, FPE-E, EMF-053 ed
>   EMA-049; le voci backend ora sono tredici.
>
> Statiche:
> - `ruff` e `black` puliti sui 9 file Python; `prettier` pulito; `git diff --check` pulito;
> - lo scanner dei colori: 0 elementi misti in `ForgotPasswordCard`, `features/email` e `linkShareActions`.
>
> Traduzioni:
> - `getting-started` ha ora `#forgot-password` (e prima `#verify-email`): debito per la pipeline, senza timbro;
> - in `profile` le pagine IT, FR ed ES non hanno la sottosezione `#email-change` di A6e: debito già esistente,
>   nessun allineamento a mano;
> - `index` IT, FR ed ES non ha la riga Email.

#### E4b.1 — Prove leggere ✅ (2026-10-16, fino alle 11:05; esiti sotto, in «E4b.3»)
> Una alla volta, `nice -n 10`, carico sotto 50 (`/tmp/libreFolio_e4b_checks.sh`, poi `checks2.sh`).
>
> Prima del fermo, su `44d4d7e8e` più E4b:
>
> | Prova | Esito |
> |---|---|
> | `api sync` | ✅ |
> | `i18n build` e `i18n check` stretto | 4 772 chiavi ✅ |
> | `services email-flows` | 151 ✅ (155 − 5 di EMF-035 + EMF-053, come previsto) |
> | `api email` | 158 ✅ (senza EMA-046, con EMA-049) |
> | `api email-change-notice` | 12 ✅ (ECN-001…007, con l'aggancio) |
> | Vitest di `features/email/`, `ForgotPasswordCard.email`, `settings/users/` e `UsersTab` | 20 file, 956 ✅ |
> | `check-orphans` | ✅ (356 file backend raggiungibili) |
> | guardia E-5 (`schemas openapi-client-text`) | 78 ✅ |
>
> **⚠️ Fuori pista: il fermo chiesto dal developer** (coordinatore, verso le 08:45, «STOP»).
> - Lo script era nell'attesa del carico prima di `api profile`, senza runner né server miei attivi. L'ho interrotto
>   con SIGINT (lo script e il suo `sleep`); la porta 6188 era libera.
> - Il worktree è rimasto sporco così com'era, senza modifiche né commit.
> - Ripresa alle 10:32, sul via del developer: HEAD e worktree erano come lasciati.
>
> Dopo la ripresa, in corso: `api profile`, `api auth`, `front check`, `core-unit`, `component-unit`, `theme-roles`,
> `mkdocs build` e `check-links`. In parallelo, la revisione di sicurezza mirata di E4b (`security-review`, sola
> lettura): il «password dimenticata» aperto, l'avviso al vecchio indirizzo e «Spedisci per email».

#### E4b.2 — Revisione di sicurezza mirata ✅ fatta a mano (2026-10-16, 10:40)
> L'agente `security-review` è fallito («400 The requested model is not supported», come per H). Come previsto dal
> coordinatore in quel caso, l'ho fatta io, punto per punto e in sola lettura, su `44d4d7e8e` più E4b.
>
> | # | Gravità | File | Righe | Vulnerabilità | Confidenza |
> |---|---|---|---|---|---|
> | 1 | 🟡 MEDIUM | `services/email/flows.py` | `email_changed_work` | L'avviso al vecchio indirizzo non ha limiti propri, solo il budget orario. Un account (con la registrazione aperta, chiunque) mette come email un indirizzo X qualsiasi (gli basta la sua password), poi la cambia di nuovo, e l'istanza scrive a X, con il suo username (50 caratteri liberi) e un dominio a sua scelta (`***@dominio`). Si ripete fino a esaurire il budget, che poi blocca reset e verifiche. Con la verifica accesa non cambia niente: il cambio d'email non si verifica | 8/10 |
>
> Sani:
> - **presa dell'account tramite il «password dimenticata» aperto: nessuna**. Il link va solo all'indirizzo dell'account
>   trovato; l'unica scrittura di `email` su un account esistente è `update_profile` (`user_service.py:483`), protetta
>   dalla password attuale (A6e); la CLI non cambia email; gli account inattivi o in attesa non ricevono nulla; il link
>   vivo dell'admin non viene annullato;
> - **enumerazione**: lo stesso 202, il lavoro dopo la risposta, i limiti contati comunque;
> - **limiti su ogni percorso**: indirizzo (/64, IPv4 mappato), identificativo in casefold (al massimo 254 caratteri:
>   chiavi limitate), casella, account, budget;
> - **«Spedisci per email»**: solo admin, token controllato dal server (E3), mai in `notify`, nell'URL o in storage;
> - **frontend**: nessun `{@html}`, niente in storage o nell'URL;
> - **log**: le righe di E sono senza indirizzo, identificativo o token.
>
> **Cura proposta** (`/tmp/libreFolio_e4b/sec/e4b_notice_limits.patch`, `ruff` e `black` puliti, non applicata):
> `EMAIL_CHANGE_NOTICES_BY_ACCOUNT` e `EMAIL_CHANGE_NOTICES_BY_MAILBOX`, 3 all'ora ciascuno (la casella in casefold),
> `peek` prima e `hit` solo dopo un invio riuscito. Oltre il limite il cambio d'email passa comunque e l'avviso salta,
> con una riga `info`. Compromesso: chi manda 3 avvisi a una casella sopprime il quarto, ma per farlo deve mandarli alla
> vittima, e prendere l'account della vittima richiede comunque la sua password. Chiesto l'ok al coordinatore; i test
> (fixture con limitatori privati in EMF ed ECN, casi nuovi) li scrive un `test-author` nuovo, in `/tmp`: quello di
> prima non esiste più dopo il fermo.
>
> **Nota per A**: `get_user_by_username_or_email` cerca per username O email con `.first()` senza ORDER BY, e gli
> username non hanno un pattern (possono contenere `@`). Chi registra come username l'indirizzo di un altro account può
> far finire login e «password dimenticata» per email sull'account sbagliato. Non è una presa (il link va all'indirizzo
> dell'account trovato), ma è un fastidio o un DoS. Più le email sensibili alle maiuscole, già note.
>
> **Risposta del coordinatore (10:44)**: la cura entra in E4b (3 avvisi all'ora per account e 3 per vecchia casella; il
> cambio passa comunque; una riga `info`). Il compromesso è accettato, come scritto sopra. La nota su
> `get_user_by_username_or_email` va ad A, in A-21 insieme a P18 (email senza distinzione di maiuscole).
>
> **⚠️ Fuori pista**:
> - `/tmp` è stato cancellato dal riavvio delle 10:03. Si sono persi gli script di supporto (`apply_find_replace.py`,
>   `mixed_roles.py`) e il pacchetto di E4b, che però era già applicato al worktree, con una copia nella cartella della
>   sessione.
> - Da ora le patch, il lavoro parcheggiato, gli script e i log che servono ancora stanno nella cartella della sessione
>   (`files/e4b/sec/`, `files/tools/`). Lì ho ricreato i due script.
> - Il `test-author` scrive anche lui lì.
>
> **Regola dei colori (coordinatore, 10:45)**: prima di scrivere in un `.svelte` delle aree IW, TR, AF, BK, IM, DV e T
> si avvisa il coordinatore. E4b ne tocca uno solo, `features/auth/ForgotPasswordCard.svelte` (area di T), applicato
> prima della regola: l'ho dichiarato. `linkShareActions.ts` resta mio fino all'ingresso. La cura dei limiti non tocca
> nessun `.svelte`.

#### E4b.3 — Le prove leggere dopo la ripresa, la cura applicata ✅ (2026-10-16, 10:33–11:15)
> Prima della cura, su `44d4d7e8e` più E4b (`checks2.sh`, una prova alla volta, `nice`, carico sotto 50):
>
> | Prova | Esito |
> |---|---|
> | `api profile` | 21 ✅ (la build del frontend con `svelte-check` 0/0) |
> | `api auth` | 88 ✅ |
> | `front check` | 0/0 ✅ |
> | `front-utility core-unit` | 178 file, 6 263 ✅ |
> | `front-utility component-unit` | 156 file, 4 050 ✅ |
> | `theme-roles.mjs --check` | pulito ✅ |
> | `mkdocs build` stretto | 0 WARNING o ERROR ✅ |
> | `check-links` | 97 ✅ |
>
> **La cura applicata** dopo l'ok del coordinatore:
> - nel codice, `e4b_notice_limits.patch`, su `flows.py`;
> - nei test, le due patch del nuovo `test-author`: in EMF ed ECN una fixture con i due limitatori privati, e i casi
>   nuovi EMF-054…058 ed ECN-008;
> - nelle docs, `docs_notice_limits.md` (5 modifiche, su `admin/email.en.md` e `developer/backend/email.md`).
>
> Ho tolto il paragrafo ormai falso «Red until …» dalla docstring di ECN e aggiornato la tabella «Testing»
> (EMF-001…058, ECN-001…008, i limiti nelle due righe) e la descrizione del runner di `api email-change-notice`.
> Tutte le patch e gli script stanno nella cartella della sessione.
>
> Prove della cura (`files/tools/e4b_cure_checks.sh`, log in `files/logs/`):
>
> | Prova | Esito |
> |---|---|
> | `ruff` e `black` sui 4 file Python | puliti |
> | `services email-flows` | 156 ✅ (151 più 5, come previsto) |
> | `api email-change-notice` | 13 ✅ (12 più 1) |
> | `mkdocs build` stretto | 0 ✅ |
> | `check-links` | 97 ✅ |
> | `tsc -p tsconfig.e2e.json` | solo i 2 errori di base, niente dalle spec di E4b |
> | `prettier` sulle due spec | ✅ |
>
> **La skill nuova `design-system`** (D-T29, `6e569084a`): letta con `git show` dalla storia, non dal checkout
> principale, che le regole del worktree escludono.
> - Il markup di E4b la rispetta: in `ForgotPasswordCard` il riquadro d'avviso è quello di A, solo ruoli, con un
>   `border` che nomina il suo ruolo, spostato sotto `{:else}` con una testid.
> - Un controllo sui componenti di E per le due regole che il cancello non verifica (il ruolo di testo sulla radice,
>   ogni `border` con il suo ruolo): nessun `border` senza ruolo.
> - `VerificationNotice` (E5a) non ha un ruolo di testo sulla radice. Sullo schermo non cambia niente: ogni figlio ha
>   il suo, e il genitore `LoginCard` mette `text-lf-primary`. La correzione è una classe, nell'area di T: la chiedo al
>   coordinatore.
>
> **Resta**: le E2E nello slot pesante, cioè `email-send-link` (ESL-E) e `forgot-password-email` (FPE-E), più le spec
> di A che incontrano la card e il registro cambiati (`auth`, `admin-users`, `theme-roles`). Poi l'handoff.

#### E4b.4 — La decisione P1 del developer, e il ruolo sulla radice di `VerificationNotice` ✅ scritti (2026-10-16, 11:20), applicati dopo lo slot
> **P1, deciso** (dal coordinatore, 11:20): con l'email che funziona, `ForgotPasswordCard` mostra il modulo, e il
> riquadro dei comandi resta **in un pannello chiuso di default**, che si apre con un clic, con la stessa `data-testid`.
> Così si chiude la domanda della notte («modulo in alto, riquadro dei comandi sotto»).
> - Il codice non ha un componente comprimibile in `components/ui`. Il modello di casa è il `<details>` nativo
>   (`ToolAboutPanel`, `TxFormOptionalSection`, `OnboardingReplaySection`): un `<summary>` con `list-none`, una
>   `ChevronDown` che ruota, una testid sul pannello e una sull'interruttore, il fuoco `focus-visible:outline-lf-focus`.
> - Il riquadro dei comandi diventa uno snippet, mostrato in tutti e due i rami: chiuso in `forgot-commands-panel`
>   (con l'interruttore `forgot-commands-toggle`) quando `email.links` è vero, aperto sotto l'avviso come prima
>   quando è falso. La testid `forgot-reset-commands` non cambia.
> - Solo ruoli: 0 elementi misti. Ho riusato la chiave `auth.serverTerminalInstructions`: nessuna chiave nuova.
>
> **`VerificationNotice`**: `text-lf-primary` sulla radice, con l'ok dei colori (11:16). Le condizioni: nessun altro
> colore di testo sullo stesso elemento, e `theme-roles --check` più il Vitest `themeRoles.gate` verdi.
>
> Lo slot E2E delle 11:15 era in corso, e il runner ricostruisce il frontend se un file di `frontend/src` è più nuovo
> della build: per non cambiare la build tra una spec e l'altra, il worktree non si tocca durante lo slot. Pronti
> nella cartella della sessione (`files/e4b/p1/`):
> - `e4b_p1_and_notice.patch` (le due copie, `prettier` pulito, `git apply --check` pulito);
> - `docs_p1.md`, quattro modifiche provate su copie: `admin/email`, `getting-started`, `features/auth.md`,
>   `backend/email.md`;
> - i test FCE ed FPE-E, che scrive un `test-author` nuovo nella stessa cartella.
>
> Dopo: si applica tutto, poi le prove leggere (`front check`, il Vitest della card, `theme-roles --check` e
> `themeRoles.gate`, `mkdocs build`). Poi un breve slot per rifare FPE-E, l'unica E2E che vede il ramo con l'email.

#### E4b.5 — E2E, slot 2 del coordinatore ✅ (2026-10-16, 11:15–11:26)
> Su `44d4d7e8e` più E4b, prima di P1: `files/tools/e4b_e2e_slot.sh`, `--workers 2`, una spec alla volta; i log stanno in
> `files/logs/`.
>
> | Spec | Esito |
> |---|---|
> | `front-utility email-send-link` | ESL-E-01…04, 4 passati in 44,6 s ✅ |
> | `front-utility forgot-password-email` | FPE-E-01…03, 3 passati in 47,0 s ✅ |
> | `front-utility auth` (di A) | 34 passati ✅ |
> | `front-utility admin-users` (di A) | 10 passati ✅ |
> | `front-utility theme-roles` | 24 passati e 2 saltati di proposito (l'hover sul progetto mobile, «Desktop only», `theme-roles.spec.ts:386`) ✅ |
>
> Lo slot l'ho restituito alle 11:26, con la porta 6188 libera. Dopo P1 serve solo un breve slot per rifare
> `forgot-password-email`. La corsia gira con l'email spenta, quindi `auth` e `theme-roles` vedono l'altro ramo della
> card, il cui DOM non cambia. Lo slot arriva dopo quello di W, entro le 12:00.

#### E4b.6 — P1 e il ruolo della radice applicati, i test al loro posto ✅ (2026-10-16, 11:27–12:33)
> **Applicati alle 11:27**, a slot chiuso: `e4b_p1_and_notice.patch` (`ForgotPasswordCard.svelte`,
> `VerificationNotice.svelte`) e le quattro modifiche di `docs_p1.md`.
>
> **I test di P1** (`files/e4b/p1/tests/e4b_p1_tests.patch`, del `test-author`), applicati alle 11:41 dopo un
> `git apply --check` pulito:
> - `ForgotPasswordCard.email.test.ts`: FCE-01, 02 e 04 seguono il pannello chiuso; **FCE-07**, nuovo: un clic
>   sull'interruttore apre il pannello e mostra il riquadro dei comandi;
> - `auth-forgot-password-email.spec.ts`: FPE-E-01 vede il riquadro nascosto nel pannello chiuso, e l'interruttore
>   lo apre.
>
> `developer/backend/email.md`, riga della tabella dei test: «FCE-01…06» diventa «FCE-01…07», col pannello chiuso di
> default nel ramo con l'email e il riquadro aperto nel ramo senza.
>
> **Prove** (una alla volta, carico sotto 50; log in `files/logs/`):
> - `files/tools/e4b_p1_checks.sh` ✅ (finito alle 11:56):
>
>   | Prova | Esito |
>   |---|---|
>   | `front check` | 0/0 ✅ (partito alle 11:36, prima della patch dei test: si rifà sotto) |
>   | `theme-roles.mjs --check` | pulito ✅ |
>   | Vitest `themeRoles.gate`, `VerificationNotice`, `LoginCard.verification`, `LoginCard` | 4 file, 102 ✅ |
>   | `mkdocs build` stretto | 0 WARNING o ERROR ✅ |
>   | `check-links` | 97 ✅ |
>
>   Le due condizioni dei colori sul ruolo della radice di `VerificationNotice` sono soddisfatte: nessun altro colore
>   di testo sull'elemento, `theme-roles --check` e `themeRoles.gate` verdi.
> - `files/tools/e4b_p1_tests_checks.sh` ✅ (finito alle 12:07):
>
>   | Prova | Esito |
>   |---|---|
>   | Vitest `ForgotPasswordCard.email` (FCE-01…07), `ForgotPasswordEmailForm`, `VerificationNotice`, `LoginCard.verification` | 4 file, 42 ✅ |
>   | `front check`, rifatto dopo la patch dei test | 0/0 ✅ |
>   | `tsc -p tsconfig.e2e.json --noEmit` | solo i 2 errori della base (`onboarding-tour.spec.ts:863`, `files.ts:9`) ✅ |
>   | `prettier --check` sui due file di test | pulito ✅ |
>
> **Lo slot breve** (coordinatore, slot 2, 12:23, taglio alle 12:25 portato alle 12:40):
> `files/tools/e4b_p1_e2e_slot.sh`, `--workers 2`, `nice`. Log: `files/logs/e4b_p1_e2e_forgot-password-email.log`.
>
> | Prova | Esito |
> |---|---|
> | `front-utility forgot-password-email` | FPE-E-01…03, 3 passati in 56,8 s ✅ (exit 0, 575 s in tutto, partita alle 12:23:26) |
>
> La porta 6188 era libera alle 12:33:01, e l'ho detto subito al coordinatore: dopo c'era Y.
>
> **⚠️ Fuori pista: lo slot è sforato.** Il runner ha ricostruito il frontend, perché P1 e i suoi test hanno
> toccato `frontend/src` dopo l'ultima build. Con il carico tra 100 e 120, `svelte-check` (0/0) e le due build di vite
> (1 min 5 s e 2 min 37 s) hanno preso circa 8 minuti. Alle 12:28 l'ho detto al coordinatore, che ha spostato il taglio
> alle 12:40 e l'ha lasciata finire.
>
> **Lezione**: dopo una modifica in `frontend/src`, la build va fatta fuori dallo slot, come prova leggera con il
> carico sotto 50. Allo slot resta così solo la spec.

### Checkpoint E4b 🧊 (2026-10-16, 12:3x) — FROZEN, pronto per l'ingresso
> **Base**: HEAD `44d4d7e8e` (treno 103), mai mossa. Nel worktree, non committati: 35 file modificati e 5 nuovi, 40
> percorsi in tre commit proposti al coordinatore (codice e test, docs, journal). `git diff --check` è pulito, e la
> porta 6188 è libera.
>
> **Prove**: tutte verdi, in E4b.1, E4b.3, E4b.5 ed E4b.6.
>
> **Non eseguiti**:
> - `all-backend`, la galleria `settings/email` e l'E2E dell'intero dominio: in E6;
> - `component-unit` completo dopo P1, con il carico sopra 50: ho fatto girare uno a uno i file che montano la card o
>   l'avviso;
> - `translate-validate`: il debito di traduzione è dichiarato, senza timbro.
>
> **Decisioni da rivedere, nell'handoff**:
> - la tenuta tolta del tutto;
> - la lingua dell'invito, quella dell'istanza (E-8);
> - il compromesso sui limiti dell'avviso;
> - P1 come `<details>` nativo.
>
> Il backlog non cambia. Il CHANGELOG lo scrive il coordinatore all'ingresso, dal testo dell'handoff: tre righe
> `✨ Added`.
>
> **Il conflitto atteso** è con A7a, A7c e P18 in `auth.py::update_profile`: va tenuta ogni riga di A, con le mie
> quattro aggiunte. Le istruzioni sono nell'handoff.
> - Ho letto la punta di A (`4554a77f4`, fuori da `dev_release2`) solo dagli oggetti git: cambia la riga
>   `Profile updated` e basta.
> - Con P18 cambierà anche la riga `email_changes = …`, e le mie due righe di `old_email` vanno subito dopo la sua.
> - Al merge con A7a va tolta da `developer/backend/email.md` (righe 276-279) la frase «Outside this module, workstream
>   A's `Profile updated` … write the account's address…». Diventa falsa con `bde624b38` di A («no email address in
>   profile logs»), che toglie l'indirizzo dalle due righe di log. Se non la tolgo al merge, la tolgo in E6.

#### E4c — «Lo stesso indirizzo» secondo A (P18) ⏳ dopo l'ingresso di A7a/P18
> **La domanda** (coordinatore, 11:35, da A, P18): P18 rende le email uniche senza distinzione di maiuscole con il
> `lower()` di SQLite, che piega solo A–Z. E confronta gli indirizzi con `strip().casefold()`, che piega anche le
> lettere accentate. Per `Émile@` → `émile@`, P18 vede due indirizzi e io lo stesso: l'avviso al vecchio indirizzo non
> partirebbe, e un link di verifica mandato a `Émile@` resterebbe valido per un account ormai a `émile@`.
>
> **Scelta (11:37, accettata la proposta di A)**:
> - dove confronto due indirizzi di account uso `user_service.same_email()` di A, così la regola sta in un posto solo:
>   - `flows.py`, `email_changed_work`, «stesso indirizzo, nessun avviso»;
>   - `verification.py`, `confirm_email`, l'indirizzo del link contro quello dell'account. Qui si diventa più
>     severi: è il lato sicuro;
> - restano `strip().casefold()` le quattro chiavi dei limiti, dove un raggruppamento più largo è più prudente:
>   `FORGOT_BY_IDENTIFIER`, `FORGOT_BY_MAILBOX`, `VERIFICATION_BY_MAILBOX` ed `EMAIL_CHANGE_NOTICES_BY_MAILBOX`.
>
> **Quando**: in un lotto dopo che A7a/P18 è entrato nella mia base, con i test (EMF-046, i casi di conferma di EMV,
> ECN-004 se A cambia anche `update_profile`) e le docs (`developer/backend/email.md`, dove si dice «stripped and
> case-folded»).
>
> Chiesto ad A il contratto esatto di `same_email()`: se è una funzione pura e sincrona, se toglie gli spazi, se piega
> solo A–Z. Chiesto anche se `update_profile` passerà a `same_email()` per `email_changes`.
>
> **Risposta di A (11:33)**:
> - `same_email(first: str, second: str) -> bool` in `services/accounts/user_service.py`: pura e sincrona. **Non toglie
>   gli spazi** (gli indirizzi salvati li toglie già `EmailStr`). **Piega solo A–Z** con `str.translate`, esattamente
>   come `lower()` di SQLite, quindi `Émile@`/`émile@`, il segno Kelvin e `ß` restano distinti. Accanto c'è
>   `email_fold(address) -> str`; li fissano ECASE-001…003, che arrivano con P18.
> - Anche `update_profile` e la rotta `PUT /auth/profile` decidono il cambio con `same_email` (C5). Un cambio solo di
>   maiuscole non è un cambio: la forma nuova si salva, la password non si chiede, nessuna sessione finisce,
>   `email_verified_at` resta, e il log porta `email_changed` False. L'aggancio quindi non parte, e il mio controllo
>   «stesso indirizzo» resta come seconda guardia.
> - La divisione (`same_email` per confrontare indirizzi di account, `casefold` per le chiavi dei limiti) va bene ad A.
>
> **Cosa cambia in E4c**:
> - i due confronti passano a `user_service.same_email()`, senza `strip()`: gli indirizzi arrivano dal database;
> - **ECN-004**: una modifica solo di maiuscole risponde 200 con la forma nuova salvata, senza password, senza cookie
>   nuovo e senza avviso;
> - **EMF-046**: le varianti A–Z restano «stesso indirizzo»; una lettera accentata o uno spazio diventano indirizzi
>   diversi;
> - **le conferme di EMV**: un link mandato a una variante non A–Z si revoca;
> - le docs: «stripped and case-folded» diventa «as `user_service.same_email()` compares them».
>
> **Preparazione** (16/10, 13:05, sola lettura su `b22747e52`):
> - `same_email()` non c'è ancora nel ramo di A: la sua punta, `946285a91`, ha solo il contratto nel journal.
> - Nessun ciclo d'import: `flows.py:25` e `verification.py:35` importano già `user_service`, e `user_service` non
>   importa niente da `services/email`.
> - I confronti da cambiare sono esattamente due:
>   - `flows.py:339`: `old_address.strip().casefold() == new_address.strip().casefold()` diventa
>     `user_service.same_email(old_address, new_address)`;
>   - `verification.py:337`: `record.email.strip().casefold() != user.email.strip().casefold()` diventa
>     `not user_service.same_email(record.email, user.email)`.
> - Le chiavi dei limiti restano `strip().casefold()`: `flows.py:215` (identificativo), `:286` (casella del
>   «password dimenticata»), `:352` (casella dell'avviso) e `verification.py:231` (casella della verifica).

### E6 — la chiusura, senza la galleria (2026-10-16)

E4b è stato committato dal coordinatore (12:37) in tre commit: `a31738e00` (codice), `dfc7847fb` (docs) e
`b22747e52` (journal). L'ingresso segue quest'ordine: H, Z5, A7a con P18, poi E4b. Quando A è entrato, il
coordinatore aggiorna la mia base. Allora risolvo io il merge di `auth.py`, come scritto nell'handoff, e tolgo la
frase falsa di `email.md:276-279`. Poi vengono E4c ed E6.

**Fino ad allora**, sempre su indicazione del coordinatore: E6 senza la galleria, con le sette righe di C-99 in
`configuration.en.md` e tutto ciò che non tocca i file di A.

#### E6.0 — Via, perimetro e regola dei campi nativi ✅ (2026-10-16, 12:40)
> **Base**: HEAD `b22747e52`, worktree pulito.
>
> **Regola nuova dei colori** (T, `a317392d4`, dalla skill `design-system`): un `<input>`, `<select>` o `<textarea>`
> con una classe `-lf-` scrive anche `text-lf-primary` e, se ha un segnaposto, `placeholder:text-lf-placeholder`.
> Il cancello non la controlla; la regola descrive un difetto vero del tema scuro. I due campi nativi di E sono già in
> regola:
> - `SendLinkByEmail.svelte:50`;
> - `ForgotPasswordEmailForm.svelte:44`.
>
> **Il perimetro adesso**:
> - le sette righe C-99;
> - `TODO_FUTURI` → `TODO_Completati` (la sola voce «📧 Server email»);
> - la pagina `domains/email.md` della devWiki (`project-historian`, in sottofondo);
> - il giro di coerenza su `admin/email.en.md`;
> - le prove leggere.
>
> **Dopo l'ingresso di A7a**:
> - le docs di `build_admin_setup()`;
> - la frase di `email.md:276-279`;
> - E4c;
> - E-4, con l'ok di A.
>
> **Dopo E4c**, gli slot (`all-backend`, l'E2E del dominio, la galleria `settings/email`) e la revisione di sicurezza
> finale.

#### E6.1 — Le sette righe di C-99 in `configuration.en.md` ✅ (2026-10-16, 12:47; build ✅, `check-links` ✅)
> **La regola C-99** (developer, `b171c058e`): una variabile nuova si spiega per intero nella pagina della sua funzione;
> in `configuration.md` ha una riga sola nella tabella, con il link.
>
> **Le righe**: sette, in fondo alla tabella «Main Options», nell'ordine di `email.md#variables`: `HOST`, `TLS`,
> `PORT`, `USER`, `FROM`, `REPLY_TO`, `MAX_PER_HOUR`. Ognuna ha una frase e il link a `email.md#variables`; quella di
> `TLS` va a `#encryption-modes`. La password ha già la sua riga nella tabella dei segreti.
>
> **Nessun timbro di traduzione**: la pagina ha già un debito con la pipeline. L'MD5 nella cache
> (`3be3e504…`, 10/10) non è quello di oggi (`16e96a45…`, prima delle mie righe), per il lavoro di più workstream, E
> compresa (`6d6965293`, le docs di E5b): un timbro lo nasconderebbe. Le righe vanno in IT, FR ed ES con la pipeline,
> o col riordino del manuale admin di fine 1.3.

#### E6.2 — `TODO_FUTURI` → `TODO_Completati` ✅ (2026-10-16, 12:50)
> Come per A4b: la voce «📧 Server email — verifica account, inviti, recupero password (da P2-1)» esce da
> `TODO_FUTURI.md`. Entra in cima a `TODO_Completati.md` come «📧 Email del server — prova, link per email, password
> dimenticata, verifica, avviso ✅», con Risultato, Origine e Cosa resta.
>
> **Contraddetti dalla specifica**: l'SMTP dalle impostazioni dell'admin e `aiosmtplib`.
>
> **I residui** puntano al backlog: E-2, E-3, E-4, E-6, E-7, E-8, e F19 fuori dalla 1.3. Nessuna voce futura nuova:
> il coordinatore aveva limitato il lavoro alla sola sezione dell'email.
>
> Nessun link verso la sezione tolta, in docs, codice, `.github` o devWiki.

#### E6.3 — La FAQ «Ho dimenticato la password» ✅ (2026-10-16, 12:53; build ✅, `check-links` ✅)
> `community/faq.en.md:58` diceva «Recovery by e-mail is not available yet», falso dopo E4b.
>
> **Ora**: si clicca *Forgot Password?*; se l'istanza manda email si riceve un link valido 30 minuti (link a
> `getting-started.md#forgot-password`), altrimenti si chiede all'amministratore. La frase di A6 sul link di reset
> dell'admin e sulla riga di comando resta com'era.
>
> **Traduzioni**: solo EN, senza timbro. La pagina ha già un debito: l'MD5 in cache (`db467242…`, 10/10) non è quello
> di oggi, per `2b0715532` di A (le pagine dei link). IT, FR ed ES dicono ancora «non ancora disponibile» e non hanno
> la frase di A6: la pipeline sistemerà tutte e due le cose.
>
> **Già a posto, verificato**: `admin/settings` nelle 4 lingue (riga *Require Email Verification*, da E5b). Nelle docs
> non resta nessun «coming soon» o «not available yet» sull'email, a parte le traduzioni della FAQ.

#### E6.4 — Il debito di traduzione delle pagine di E ✅ (2026-10-16, 12:56)
> **Il metodo**: le pagine `.en.md` toccate dai 13 commit di E sulle docs (`git log --no-merges --grep=email`, da
> `380a3e768`), più `configuration` e la FAQ di oggi. Per ognuna ho confrontato l'MD5 di oggi con la cache di Aphra
> (`mkdocs_src/aphra-pipeline/.translate-hashes.json`), senza `dev.py`. Il log è in
> `files/logs/e6_translation_debt.txt`, nella cartella della sessione.
>
> | Pagina | Traduzioni | Stato |
> |---|---|---|
> | `admin/cli_tools` | IT, FR, ES | debito dal 10/10 |
> | `admin/configuration` | IT, FR, ES | debito dal 10/10 (con le sette righe di C-99) |
> | `admin/index` | IT, FR, ES | debito dal 10/10 (con la riga Email) |
> | `admin/settings` | IT, FR, ES | debito dal 10/10 (la riga di *Require Email Verification* è già nelle 4 lingue) |
> | `community/faq` | IT, FR, ES | debito dal 10/10 (con E6.3) |
> | `user/getting-started` | IT, FR, ES | debito dal 10/10 (con `#verify-email` e `#forgot-password`) |
> | `user/settings/profile` | IT, FR, ES | debito dal 04/09 (di A, con `#email-change`) |
> | `admin/email`, `admin/users` | — | solo EN, per scelta |
>
> Su nessuna di queste pagine il debito è solo di E, quindi **nessun timbro**: la pipeline le rifà intere, quando il
> developer la lancia. Tradurre `admin/email` nella 1.3 resta una sua decisione.

#### E6.5 — `lint --dead-code --scope backend` ✅ (2026-10-16, 12:54)
> `files/tools/e6_dead_code.sh`, con l'attesa del carico sotto 50 (era tra 109 e 167 per dieci minuti). Esito: 5 reperti
> «Unreferenced» e 45 «Referenced only by tests», nessuno nuovo nei file di E salvo il transitorio dichiarato:
> `build_admin_setup` (`services/email/messages.py:177`), che riceve il suo chiamante con A7a.
>
> Dopo A7a si rifà: il reperto deve sparire.

#### E6.6 — La pagina `domains/email.md` della devWiki ✅ (2026-10-16, 13:02)
> Scritta dal `project-historian` in sottofondo, con un perimetro stretto: la pagina nuova, una riga in `index.md` e una
> voce in `log.md`. I due file condivisi li fonde il coordinatore all'ingresso.
>
> **La pagina** (~285 righe, inglese, `features: []`: nessun codice F per l'email; il primo libero è F-115):
> - cosa fa;
> - un grafo mermaid;
> - le decisioni: D-E1…D-E14 con la 44 e la 45, le decisioni di sicurezza di E3s, E5b ed E4b, P1, la regola di E4c;
> - i limiti noti;
> - 16 problemi risolti, presi dai «Fuori pista» con la loro sezione;
> - cosa viene dopo;
> - 50 «Source files».
>
> `check_source_paths.py`: 0 percorsi mancanti nella pagina; nel resto della wiki 5, già prima.
>
> **La mia rilettura**: tre affermazioni verificate sul codice.
> - Il link di verifica usa il frammento (`token_service.py:83`) ✅.
> - L'email di prova prende il nome dell'istanza dall'host della richiesta (`api/v1/email.py:97`, `request.url.netloc`)
>   ✅.
> - **Una correzione**: non è vero che «solo i limiti per account» reggono tra processi. Lo fanno quelli del «password
>   dimenticata» e della verifica, contati sulle righe dei token (`flows.py:49`, `verification.py:53`). Quello per
>   account dell'avviso, invece, è in memoria (`flows.py:55`). Frase corretta.
>
> Ho aggiunto la FAQ (E6.3) al punto di E6.
>
> **Proposte dello storico per altre pagine**, non applicate perché sono condivise (vanno nell'handoff):
> - un punto in `domains/auth.md`, «Key decisions»;
> - `domains/email` nei `related:` di `decisions/link-tokens-in-the-url-fragment.md`;
> - una riga in `problems/generated-client-widens-nullable-scalar.md` (E-2);
> - una riga, facoltativa, in `raw/ingest-registry.md`.

#### E6.7 — Il giro di coerenza su `admin/email.en.md`, e un difetto della UI ✅ (2026-10-16, 13:08; prove ✅)
> **Il giro** l'ha fatto `docs-writer` in sottofondo, senza `dev.py`. Ha controllato contro il codice:
> - i numeri;
> - le 37 righe di log, compresa quella `info` di E4b;
> - i codici d'errore;
> - gli avanzi della tenuta;
> - le ancore;
> - la card di P1.
>
> **Nove modifiche piccole**, ognuna con la prova nel codice:
> - la scheda mostra il limite orario, l'unico valore di `LIBREFOLIO_SMTP_*` che si vede;
> - `"available"` vale anche «nessun blocco del fornitore» (`links.py:101`);
> - la scheda Email viene dopo **Backup**, non dopo **Admin** (`settingsTabs.ts`, ordine 130);
> - un a capo di troppo nella citazione dell'avviso della card;
> - un'email di reset non partita conta lo stesso, per account e per casella (`flows.py:286` e `_recent_resets`, che
>   conta anche le righe revocate: verificato da me);
> - la riga `RECIPIENT_REFUSED` del dialogo;
> - tre righe di log (la casella, e `user_id` in due righe `failed`).
>
> **Le mie modifiche, dalle sue proposte**:
> - **«💡 Examples» spostata** prima di «🌐 Emails with a Link», per seguire i quattro passi dell'introduzione: uno
>   spostamento puro, fatto con `files/tools/e6_move_examples.py`, che controlla intestazioni, separatori e righe (né
>   aggiunte né perse). Nessun riferimento «above» o «below» dipendeva dall'ordine;
> - il link a `hosting_providers.md#instance-block` e quello a `users.md#waiting` (l'ancora c'è, `users.en.md:93`);
> - l'email di prova nomina l'istanza con l'indirizzo che il browser ha raggiunto, non con `LIBREFOLIO_PUBLIC_URL`
>   (`api/v1/email.py:97`).
>
> **Il difetto della UI** (dal suo rapporto): in «Spedisci per email», un `RECIPIENT_REFUSED` diceva «The SMTP server
> refused **your** address.», il testo dell'email di prova. Qui però l'indirizzo rifiutato è quello dell'invitato o
> dell'account.
> - Il test è stato scritto prima, dal `test-author`: in `emailText.test.ts`, la riga di `LINK_SEND_FAILURES` vuole la
>   chiave nuova, e il commento d'intestazione lo dice. Rossi attesi: ETX-11 ed ETX-13. Le tabelle dell'email di prova
>   restano com'erano.
> - La cura:
>   - in `linkSendFailureMessage`, un ramo per `RECIPIENT_REFUSED` verso `email.sendLink.errors.RECIPIENT_REFUSED`;
>   - la chiave nei 4 cataloghi email: «The SMTP server refused the recipient's address.» e le traduzioni, che nominano
>     tutte il destinatario. Il test non controlla il testo: l'ha avvertito il `test-author`.
> - Docs:
>   - `admin/email.en.md`, una riga sua nella tabella del dialogo («the one in **Send to** for an invitation, the email
>     of the account for a reset link»);
>   - `developer/backend/email.md`: la frase di `linkSendFailureMessage()`, e nella tabella «Testing» «ETX-01…10»
>     diventa «ETX-01…14», com'era già da E4a.
>
> **Rimandati dopo l'ingresso di A**, perché stanno in pagine su cui lavora anche A:
> - `admin/users.en.md:205` (la mia sezione di E4b): «`LIBREFOLIO_PUBLIC_URL` set» diventa «set to an address
>   LibreFolio can use» (`links.py`, `_usable_base`);
> - `admin/cli_tools.en.md:107`: la schermata *Forgot Password?* mostra i comandi in un pannello chiuso quando l'email
>   funziona (P1).
>
> **Restano per A7a ed E4c** (dal suo rapporto):
> - A7a: le righe 418-419 e 454 (il primo account non aspetta) e 605 (i `kind` di `Email sent`, senza `admin_setup`);
> - E4c: la riga di log «the link was sent to another address», e una frase sull'avviso che salta quando il vecchio e
>   il nuovo indirizzo sono lo stesso (`flows.py:339`).
>
> **Da sapere**: le quattro citazioni senza ancora (righe 78, 119, 433, 593) sono volute. Le versioni IT, FR ed ES delle
> pagine di arrivo non hanno quelle ancore, e la build stretta delle lingue che mostrano questa pagina inglese
> fallirebbe.

#### ⏸️ Pausa del developer (2026-10-16, 13:23) — FROZEN fino al via del coordinatore
> **Stato**:
> - HEAD `b22747e52`;
> - nel worktree, non committati, 15 file modificati e 1 nuovo: il primo gruppo di E6, cioè E6.1, E6.2, E6.3, E6.6 ed
>   E6.7, più questo piano.
>
> **Le prove di E6** (`files/tools/e6_checks.sh`, carico sotto 50):
>
> | Prova | Esito |
> |---|---|
> | `i18n build` e `i18n check` stretto | 4 773 chiavi (+1) ✅ |
> | Vitest `emailText.test.ts` e `SendLinkByEmail.test.ts` | 289 ✅ |
> | `prettier` | pulito ✅ |
> | `front check` | 0/0 ✅ |
> | `mkdocs build` stretto | 0 WARNING o ERROR, 3 076 URL di asset risolti ✅ |
> | `check-links` | **non eseguito** |
>
> **Perché `check-links` non è partito**: alla pausa la build era già in corsa, e l'ho lasciata finire. Ho fermato lo
> script (`kill` sul suo PID, 44572) prima che lanciasse `check-links`, che è il primo passo alla ripresa.
>
> **La domanda di A su P18** (dal coordinatore, 13:2x), con la risposta mandata direttamente ad A. Con l'indice unico
> su `lower(email)`, i due test con varianti ASCII della stessa casella non si possono più creare: EMF
> `test_three_reset_emails_an_hour_per_mailbox_whatever_the_account` e EMV
> `test_a_mailbox_gets_three_registration_emails_an_hour_whatever_the_account`. A li riscrive con varianti non ASCII.
> - **Il senso resta**: le chiavi dei limiti sono `casefold`, e le varianti non ASCII (NFC) sono una casella sola e
>   quattro account.
> - **Ma il finto SMTP non annuncia `SMTPUTF8`**: `send_message` alza `SMTPNotSupportedError` lato client, cioè
>   `SEND_FAILED`, e niente arriva in `rcpt_tos`. Il test EMV andrebbe rosso, perché il limite conta solo le email
>   partite; in quello EMF cadrebbero le asserzioni sui messaggi consegnati.
> - **La cura, mia**: il finto annuncia `SMTPUTF8` e `8BITMIME` e accetta i parametri dopo `MAIL FROM:<…>`. Va in un
>   mini-lotto al via, prima di P18 o insieme, con un caso che fissa «non ASCII verso un server senza `SMTPUTF8` →
>   `SEND_FAILED`».
>
> **Alla ripresa, in ordine**:
> 1. `check-links`.
> 2. Il checkpoint del primo gruppo di E6 al coordinatore, che lo committa prima di aggiornare la base.
> 3. Il mini-lotto `SMTPUTF8` del finto, prima di P18.
> 4. Dopo l'ingresso di A:
>    - il merge di `auth.py` e la frase di `email.md:276-279`;
>    - E4c;
>    - le docs rimandate (`users.en.md:205`, `cli_tools.en.md:107`, quelle di A7a);
>    - il `lint --dead-code` di nuovo;
>    - E-4, con l'ok di A.
> 5. Gli slot (`all-backend`, l'E2E del dominio, la galleria) e la revisione di sicurezza finale.

#### ▶️ Ripresa (2026-10-16, 14:14)
> Il via del coordinatore, sulla ripresa del developer, in quest'ordine:
> 1. `check-links`;
> 2. il checkpoint di E6 per il suo commit;
> 3. il mini-lotto `SMTPUTF8`, che sblocca P18 di A. Lo dico ad A quando è committato.
>
> **La nota del coordinatore durante la pausa (13:24), per i merge**:
> - **P17 di H** cambia i tre punti che leggono l'indirizzo del client: `email.py` ~157 e ~203, `auth.py` ~274.
>   - Passano da `request.client.host` a `client_address(request)`, con il modulo nuovo
>     `services/platform/client_address.py` e la variabile `LIBREFOLIO_CLIENT_IP_HEADER`.
>   - Quando P17 arriva nella mia base, al merge si tengono le righe di H.
> - **In E4c**, `flows.address_key` va sostituito con `client_rate_key` di H.
>
> **`check-links`** (14:14, `files/tools/e6_check_links.sh`): ✅ 97 link validi, tutti quelli che attraversano i confini.
> Le prove del primo gruppo di E6 sono così complete.

#### E6.8 — Il mini-lotto `SMTPUTF8`, per P18 di A ✅ (2026-10-16, 14:25–14:47)
> Il primo gruppo di E6 è committato (14:2x): `75b8d5c9e` (correzione), `3480cbc53` (docs), `589c72cf7` (TODO e
> devWiki) e `0e0c14868` (journal). La base è `0e0c14868`.
>
> **Perché serve** (la domanda di A, 13:2x): P18 rende l'email unica con l'indice su `lower(email)`, quindi i due test
> «whatever the account» usano varianti non ASCII della stessa casella. Ma il finto SMTP non annuncia `SMTPUTF8`: con un
> indirizzo non ASCII, `smtplib.send_message` si ferma lato client (`SMTPNotSupportedError`, cioè `SEND_FAILED`), e
> niente arriva al finto.
>
> **Il lavoro**:
> - **Il finto e i test** li scrive il `test-author`, in sottofondo, in `fixtures/email/fake_smtp.py` e
>   `test_email_delivery.py`:
>   - l'opzione `smtputf8=True`, con cui l'EHLO annuncia `SMTPUTF8` e `8BITMIME`;
>   - il campo `ReceivedMessage.mail_options`, con i parametri dopo `MAIL FROM:<…>`;
>   - tre o quattro EMD nuovi: il non ASCII consegnato con `SMTPUTF8`, il non ASCII senza `SMTPUTF8` che dà
>     `SEND_FAILED`, l'ASCII senza parametri (la prova che gli altri test non cambiano), più il controllo del finto.
> - **Docs**: in `admin/email.en.md`, la riga `SEND_FAILED` dice che un indirizzo con lettere non ASCII prima della `@`
>   ha bisogno di un server con `SMTPUTF8`, e che il log nomina `SMTPNotSupportedError` (verificato:
>   `smtp._server_words`, senza l'indirizzo). Le docs per sviluppatori (il finto, gli ID EMD) dopo il rapporto del
>   `test-author`.
> - **La devWiki**: le quattro righe dello storico nelle pagine condivise, con il via del coordinatore (14:2x):
>   - un punto in `domains/auth.md`, «Key decisions»;
>   - `domains/email` nei `related:` di `decisions/link-tokens-in-the-url-fragment.md`;
>   - una nota sotto «Impact» in `problems/generated-client-widens-nullable-scalar.md`, più `domains/email` nei
>     `related:`;
>   - la riga del piano 08 in `raw/ingest-registry.md`, a `0e0c14868`.
>
> **Le prove**, poi: `services email-delivery`, e ogni suite che usa il finto, perché l'EHLO cambia per tutte:
> `services email-flows`, `services email-verification`, `api email`, `api email-verification`,
> `api email-verification-hooks`, `api email-change-notice`.
>
> **Il rapporto del `test-author`** (14:3x):
> - **Il finto** (`fake_smtp.py`):
>   - l'opzione `smtputf8: bool = True`: l'EHLO annuncia `8BITMIME` e `SMTPUTF8` prima di `STARTTLS`;
>   - `ReceivedMessage.mail_options`, con i parametri dopo `MAIL FROM:<…>` nell'ordine ricevuto, nessuno rifiutato;
>   - `_reverse_path` restituisce `(indirizzo, parametri)`;
>   - la docstring: un indirizzo internazionale si legge da `rcpt_tos` o da `data`, non dal `message` analizzato, il
>     cui parser trasforma quei byte in escape.
> - **I test nuovi** (`test_email_delivery.py`):
>   - EMD-046: il non ASCII viene consegnato con `SMTPUTF8 BODY=8BITMIME`, con il `To` in UTF-8 dentro `data`;
>   - EMD-047: senza `SMTPUTF8` è `SEND_FAILED`, `detail` nomina `SMTPNotSupportedError`, una connessione e nessun
>     messaggio;
>   - EMD-048: l'ASCII parte con `mail_options == ()`, dopo un controllo che i parametri esistono;
>   - EMD-049: l'EHLO del finto, con l'opzione e senza.
>
> **Le docs per sviluppatori** (`developer/backend/email.md`):
> - il paragrafo del finto: `8BITMIME` e `SMTPUTF8`, `mail_options`, e come leggere un indirizzo internazionale;
> - la riga `SEND_FAILED` della tabella dei codici;
> - la tabella «Testing»: EMD-001…049.
>
> **Prove** (`files/tools/e6s_checks.sh` ed `e6s_docs.sh`, carico sotto 50):
>
> | Prova | Esito |
> |---|---|
> | `ruff` e `black` sui due file | puliti ✅ |
> | `services email-delivery` | 108 ✅, nessuno saltato |
> | `services email-flows` | 156 ✅, invariato |
> | `services email-verification` | 124 ✅ |
> | `api email` | 158 ✅, invariato |
> | `api email-verification` | 49 ✅ |
> | `api email-verification-hooks` | 16 ✅ |
> | `api email-change-notice` | 13 ✅, invariato |
> | `mkdocs build` stretto | 0 WARNING o ERROR ✅ |
> | `check-links` | 97 ✅ |
> | `check_source_paths.py` (devWiki) | 5 mancanti, gli stessi di prima; nessuno nuovo ✅ |
>
> Il finto cambia per tutte le sette suite che lo usano: verdi tutte e sette.
>
> **Committato dal coordinatore (15:02)**:
> - `068d3396f`, il finto e i test;
> - `25cf29e3c`, le docs;
> - `d66d004ab`, la devWiki;
> - `9d27245dd`, il journal.
>
> **Il finto è già in `dev_release2`** con un cherry-pick, `7d51c21af`, così A adatta i miei tre test in P18; le docs
> arrivano con il mio ramo. Ad A ho mandato lo SHA.
>
> **Da A (14:53)**: c'è un terzo test con lo stesso schema, EVA-016 (`test_email_verification_api.py:122`, il gemello
> API di EMV-043). A lo adatta con gli altri due: EMV-043 e la costante `ONE_MAILBOX` di EMF.
> EMA-036 (`api email`) resta verde: con P18 le altre grafie trovano l'account, ma il suo limite sui link le ferma.
>
> **La mia risposta (14:5x)**:
> - le asserzioni leggono `rcpt_tos`, che con `SMTPUTF8` conserva la stringa esatta, quindi restano com'erano;
> - la costante della casella è il `casefold` delle varianti, con la precondizione come in EMF-056;
> - **EMF-056** (`OLD_MAILBOX_VARIANTS`) non va toccato: le varianti vanno a `email_changed_work` solo come vecchio
>   indirizzo, e i quattro account sono `zq-moved-{i}@example.org`, quindi niente conflitto con `ux_users_email_lower`.
>
> **Dopo**: E4c aspetta A7a e P18 nella mia base. Fino ad allora, solo lavoro fuori dai file di A.
>
> **La metà H di E4c, proposta al coordinatore (15:0x).** P17 di H è in `dev_release2` (`b1df87bd4`, commit
> `22d6dc84e`), e `client_rate_key` (`services/platform/client_address.py:91`) è identico byte per byte a
> `flows.address_key` (`flows.py:66`). Lo sostituisce senza cambiare nessuna chiave.
>
> **Se il coordinatore aggiorna la base ora**:
> - risolvo il conflitto sicuro in `api/v1/email.py`, tenendo `client_address(request)` di H, verso la riga 157, e la
>   tenuta tolta da E4b;
> - tolgo `address_key`, e uso `client_rate_key` in `flows.py:215` e in `verification.py:289` e `:366`;
> - sistemo i 14 riferimenti nei test e le docs.
>
> Altrimenti resta tutto per l'arrivo di A7a e P18.

#### E4c-H — La metà H di E4c, sul merge con `dev_release2` ✅ (2026-10-16, 15:11–16:33)
> **Il via del coordinatore** (15:11): una casa sola per la chiave. Aggiorna la mia base con `dev_release2`, che
> contiene P17 di H, e lascia il merge aperto (`git merge 26dda1a26`). HEAD è `9d27245dd`, MERGE_HEAD `26dda1a26`, la
> base comune `44d4d7e8e`; 496 file portati dal merge.
>
> **Il merge**:
> - **Un solo conflitto**, in `admin/configuration.en.md`: le mie sette righe SMTP contro le due di Z5
>   (`LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS` e `…_MAX_SECONDS`). Le ho tenute tutte, prima quelle di Z5, che come le
>   righe di sopra rimandano a `sleep_wake.md`, poi le mie. La riga di H, `LIBREFOLIO_CLIENT_IP_HEADER` (riga 40),
>   era già entrata da sola. Ho messo in stage solo questa risoluzione; il piano resta fuori dal merge.
> - **Gli altri file cambiati da tutte e due le parti**, controllati uno per uno:
>   - `api/v1/email.py`: `client_address(request)` di H alle righe 159 e 203, con il suo import, e nessuna traccia
>     della tenuta tolta da E4b;
>   - `api/v1/auth.py`: la riga di H in `register` (276) e le quattro aggiunte di E4b in `update_profile`;
>   - il finto e EMD-046…049: identici a HEAD, cioè il mio commit e il cherry-pick `7d51c21af`, senza doppioni;
>   - il runner: le registrazioni di E tutte presenti, insieme a `client-address` di H. Nel frontend cambiano solo i
>     percorsi dei broker;
>   - `admin/index`: la riga Email c'è ancora.
>
> **La metà H di E4c**, non in stage e in file fuori dal merge, come chiesto:
> - **Codice**:
>   - `flows.py`: `address_key()` tolto, insieme a `import ipaddress`; `client_rate_key` di H in `FORGOT_BY_ADDRESS`; il
>     commento sull'indirizzo (`client_address()`, `LIBREFOLIO_CLIENT_IP_HEADER`, `FORWARDED_ALLOW_IPS`);
>   - `verification.py`: `client_rate_key` in `registration_email_allowed()` e in `resend_verification()`, più il
>     commento di `RESEND_BY_ADDRESS`.
>   - In `backend/app` non resta nessun `address_key`. Nessun ciclo d'import: il modulo di H importa solo `config` e
>     `logging_config`.
> - **Test** (`test-author`):
>   - EMF-036 cambia senso: ora fissa la casa unica (`flows.client_rate_key is client_rate_key`, nessun
>     `address_key`), e da 12 casi diventa 1, quindi `services email-flows` raccoglie 11 test in meno;
>   - EMV-033 è solo rinominato (`…_keyed_by_client_rate_key`);
>   - EMF-037 ed EVK-010 usano `client_rate_key`;
>   - le docstring dei quattro file sono aggiornate;
>   - EMA-035 resta com'è: con la variabile vuota, il suo testo è ancora vero.
> - **Docs**:
>   - `developer/backend/email.md`:
>     - via la riga `address_key` della tabella di `flows`;
>     - «Why `request.client.host`» diventa «Which client address», con P17 e un link a
>       `security.md#client-address`;
>     - otto punti passano a `client_address(request)` e `client_rate_key()`, compresa la riga di EMF nella tabella
>       «Testing».
>   - `admin/email.en.md`, «Behind a reverse proxy»: la strada di `LIBREFOLIO_CLIENT_IP_HEADER` e quella di uvicorn,
>     con un link a `connection_checks.md#client-address`, la pagina di H.
>   - La devWiki `domains/email.md`: il limite «Behind a proxy» aggiornato a P17, la nota sulla casa unica e
>     `client_address.py` tra i «Source files».
>
> **⚠️ Fuori pista: due file sono anche nel merge**, `security.md` (il punto «Callers» di H dice «Their key is still
> `address_key()` … until the email feature switches») e `_backend_services.py` (le descrizioni di `email-flows` e
> `email-verification`).
> - Una mia modifica lì sarebbe finita sopra il merge in stage (MM). La modifica di `security.md` l'ho salvata come
>   patch (`files/e4c/security_client_rate_key.patch`) e tolta con l'editor, senza comandi git.
> - Tutto si applica dopo il commit del merge (`files/e4c/after_merge_todo.md`), compresa la nota per H:
>   `test_client_address.py`, righe 33 e 771, dice ancora «today's rule of address_key».
>
> **Prove della revisione combinata** (`files/tools/e4ch_checks.sh`, carico sotto 50):
> - `ruff` e `black`;
> - `services`: `client-address`, `email-flows`, `email-verification`, `email-verification-hooks`, `email-delivery`,
>   `registration`;
> - `api`: `email`, `email-verification`, `email-verification-hooks`, `email-change-notice`, `auth`, `profile`,
>   `registration`;
> - la guardia OCT;
> - `api sync`, `i18n`, `front check`, `theme-roles`;
> - `lint --dead-code`;
> - `mkdocs build` e `check-links`.
>
> **⚠️ Fuori pista: la build stretta è fallita alle 16:05.** `admin/email.en.md` puntava a
> `connection_checks.md#client-address`, ma `admin/connection_checks.it.md` non ha quell'ancora: H l'ha aggiunta solo
> in EN. La nostra pagina esiste solo in EN, quindi le build IT, FR ed ES la mostrano in inglese e risolvono il link
> contro le pagine tradotte.
>
> **La cura**: la convenzione della pagina per queste sezioni, cioè il nome della sezione nel testo e il link alla
> pagina senza ancora («*The Visitor's Address* in [Checking Connection Security](connection_checks.md)»). Il link a
> `security.md#client-address` dalla pagina per sviluppatori va bene: il manuale per sviluppatori è solo EN.
>
> **Revisione combinata** (il merge in stage più la metà H di E4c fuori stage), dalle 15:22 alle 16:17, carico sotto 50:
>
> | Prova | Esito |
> |---|---|
> | `ruff`, `black` (7 file) | puliti ✅ |
> | `services client-address` (di H) | 131 ✅ |
> | `services email-flows` | 145 ✅ (156 meno 11: EMF-036 passa da 12 casi a 1) |
> | `services email-verification` | 124 ✅ |
> | `services email-verification-hooks` | 32 ✅ |
> | `services email-delivery` | 108 ✅ |
> | `services registration` | 147 ✅ |
> | `api email` | 158 ✅ |
> | `api email-verification` | 49 ✅ |
> | `api email-verification-hooks` | 16 ✅ |
> | `api email-change-notice` | 13 ✅ |
> | `api auth` | 88 ✅ |
> | `api profile` | 21 ✅ |
> | `api registration` | 96 ✅ |
> | guardia OCT | 78 ✅ |
> | `api sync` | ✅ |
> | `i18n build` e `i18n check` stretto | 4 780 chiavi ✅ |
> | `front check` | 0/0 ✅ |
> | `theme-roles --check` | pulito ✅ |
> | `lint --dead-code` | in E solo il transitorio `build_admin_setup` (A7a) ✅ |
> | `mkdocs build` stretto | rosso alle 16:05 (l'ancora, sopra); 0 dopo la cura, alle 16:17 ✅ |
> | `check-links` | 97 ✅ |
> | `git diff --check` e `git diff --cached --check` | puliti ✅ |
>
> Alla fine la porta 6188 era libera.
>
> **Il merge committato dal coordinatore** (16:26): `57081a85e`, con genitori `9d27245dd` e `26dda1a26`. Poi i due
> ritocchi rimandati:
> - ~~`security.md`, il punto «Callers» di H~~: **tolto su correzione del coordinatore (16:4x)**. H lo riscrive in H-12
>   («Their key follows the rule of `client_rate_key()`»), una frase vera prima e dopo il mio passaggio. Il file è
>   tornato uguale a HEAD;
> - `_backend_services.py`, le descrizioni di `email-flows` ed `email-verification`: «H's client_rate_key».
>
> La nota su `test_client_address.py` (righe 33 e 771) la passa il coordinatore ad H.
>
> **Le prove dei ritocchi**: `ruff` e `black` sul runner puliti; `mkdocs build` stretto a 0 (16:33). Dove si nomina
> ancora `address_key` lo si fa di proposito, come storia: `developer/backend/email.md:609`. Il punto di
> `security.md` è di H, che lo riscrive in H-12.

#### E6.9 — La revisione di sicurezza finale del dominio ✅ (2026-10-16, 16:36–17:0x)
> Col via del coordinatore (16:35): in sola lettura, sulla base `d4c5121ad`, cioè E1–E6 più E4c-H. Questa volta
> l'agente `security-review` ha risposto. Il perimetro e il modello delle minacce sono quelli del lotto, e ho elencato
> i compromessi già decisi perché non tornassero come reperti nuovi.
>
> **Esito: nessuna vulnerabilità sfruttabile sopra la soglia** (CRITICAL da 6, HIGH da 7, MEDIUM da 8, LOW da 9).
>
> **Tre note sotto la soglia**:
> 1. **I limiti per casella non vedono gli alias.** `victim+N@…` e i punti di Gmail fanno caselle diverse per
>    `strip().casefold()` (`flows.py:270` e `:336`, `verification.py:233`). Con la registrazione aperta si può puntare
>    tutto il budget orario su una casella. Ogni email porta lo username, 50 caratteri liberi, URL compresi: spam o DoS,
>    con il tetto di `LIBREFOLIO_SMTP_MAX_PER_HOUR` per processo. → **E-9** nel backlog, dopo la release.
> 2. **Il budget orario come oracolo d'esistenza.** L'ammissione dà 429 a budget finito (`flows.py:206`), e solo un
>    account attivo trovato spende un'unità (`flows.py:293`): con un'unità sola, «202 per X, poi 429» dice che X esiste.
>    Non è praticabile: in modalità invito o chiusa, prosciugare circa 50 email l'ora richiede già account noti; in
>    modalità aperta, `/auth/register` dice già se username o email sono presi. Solo annotato.
> 3. **I link di reset sopravvivono al cambio d'email e di password**, nel codice di A: `update_profile`
>    (`user_service.py:479-487`) e `change_password` (`auth.py:323-349`) chiudono le sessioni ma non revocano i token
>    `PASSWORD_RESET`.
>    - Con il «password dimenticata» aperto, chi controlla la vecchia casella può chiedere un link prima del cambio e
>      usarlo dopo, entro 30 minuti.
>    - La cura sta nel codice di A: revocare i token di reset in tutti e due i punti. → Al coordinatore, per A.
>
> **Sani**, in breve:
> - l'enumerazione: lo stesso 202, il lavoro dopo la risposta, la password prima del resto con un hash finto;
> - l'injection nelle intestazioni e nell'HTML;
> - l'avvelenamento dei link (solo `LIBREFOLIO_PUBLIC_URL`);
> - la fuga dei token (solo hash, frammento, `no-referrer`);
> - le corse (conteggi rifatti nella scrittura, consumo atomico);
> - le chiavi dei limiti (/64, l'header solo quando la variabile c'è);
> - il cambio d'email con la password;
> - nessun aggiramento della verifica;
> - «Spedisci per email»;
> - i segreti, mai nell'API, nei log o nei backup;
> - TLS senza ricaduta in chiaro;
> - `/system/instance` con due booleani;
> - il frontend senza `{@html}`.
>
> **Dopo E4c** resta una revisione delta: le due righe di `same_email`.
