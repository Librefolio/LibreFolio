# Piano — fase 00, 34, passo 2: l'ultimo amministratore attivo

> **Stato**: ✅ pronto per il checkpoint (2026-10-09), FROZEN dopo l'handoff. Il developer ha deciso tutto (§0.1); le aggiunte del lotto sono il cookie `Secure`, il setup E2E e le configurazioni morte (§7.3–§7.6).
>
> - Viene da: [plan-phase00AccountAndIdReuse.prompt.md](plan-phase00AccountAndIdReuse.prompt.md), la cancellazione dell'account e il rifiuto dell'unico amministratore.
> - Workstream L. Base `9b2acdd5d` (treno 21). Corsia 6156/6166, `/tmp/librefolio-r2-l`.

## 0. Il mandato

- **Il developer** (testuale): «user demote è un problema e va fixato».
- **Il difetto**, segnalato da Q e verificato dal coordinatore: `user demote` non controlla che resti un altro amministratore attivo, perché `set_user_admin` non ha una guardia. Da CLI si lascia l'istanza senza amministratori.
- **Il coordinatore**:
  - un rifiuto con un messaggio chiaro, nel servizio, dove la guardia è più robusta;
  - valutare `deactivate` con lo stesso principio, e dirglielo prima se cambia qualcosa di visibile;
  - i rossi col test-author, solo in file già registrati; per un file del runner si chiede;
  - niente cataloghi i18n, che sono di O;
  - verificare sul tag se il difetto c'è nella v1.1.0;
  - al checkpoint, la riga del CHANGELOG.

### 0.1 Le decisioni del developer (2026-10-09, portate dal coordinatore)

- **Sui tre punti di §3** (testuale): «Sì a tutti e tre (Consigliato)»:
  1. `deactivate` sull'ultimo admin attivo: lo stesso rifiuto;
  2. la cancellazione dell'account conta gli admin attivi, col messaggio di oggi;
  3. la CLI `dev.py user …` esce con 1 quando il comando fallisce.
- **In più, `JWT_SECRET` vuoto** (testuale: «Sì, correggilo (Consigliato)»).
  - `dev.py` usa `env.setdefault("JWT_SECRET", …)`: un `JWT_SECRET=` vuoto in `.env` non viene sostituito.
  - I worker ricevono il vuoto e ognuno si genera il suo segreto (`auth_service.py:84`), quindi con `dev.py server` a più worker gli utenti vengono scollegati a caso.
  - La cura: il vuoto vale come assente. Un segreto nuovo a ogni avvio, quando manca, resta il comportamento voluto.
  - Il rosso si prova senza avviare il server.
- **Il cookie di sessione `Secure` in «auto»**, da fare in questo lotto. Il developer: «mi piace»; e il principio: «il comportamento di default deve essere sicuro, e diventare insicuro solo disattivandolo esplicitamente».
  - `Secure` acceso su ogni richiesta HTTPS, anche dietro un proxy fidato che lo dichiara (`X-Forwarded-Proto`);
  - spento in HTTP, dove impedirebbe il login;
  - una variabile con `auto` (default), `always` e `never`;
  - vale per il `set_cookie` e per le due cancellazioni del cookie, con gli stessi attributi;
  - prima i rossi, poi la doc admin col docs-writer, solo EN.
- **`auto` legge anche l'intestazione del proxy** (coordinatore, 2026-10-09: «Sì alla tua proposta su `auto`»):
  - `Secure` se lo schema è `https`, **oppure** se il primo valore di `X-Forwarded-Proto` è `https`, chiunque lo mandi;
  - l'intestazione può solo accendere `Secure`, mai spegnerlo;
  - `never` è l'uscita documentata per il proxy che dichiara `https` a un browser in HTTP;
  - con 2 casi unitari in più;
  - la doc va col docs-writer, solo EN: `admin/configuration.en.md`, una riga ai livelli 3 e 4 di `admin/service_exposure.en.md`, e la voce commentata in `.env.example`. Q non tocca quelle pagine.
- **L'indicatore di sicurezza della connessione**: l'analisi è stata mandata al coordinatore il 2026-10-09, e il developer l'ha approvata così com'era («Sì, procedi così (Consigliato)»).
  - È un lotto a parte, sopra il commit di questo, con i rossi prima.
  - Le chiavi i18n restano segnaposto finché O non consegna; la pagina di doc la scrive Q.
  - **Revisione approvata dal coordinatore il 2026-10-09** (perché è coerente con l'approvazione del developer e non chiede configurazione):
    - l'endpoint diventa `{client_class, cookie_secure}`;
    - la classe della sorgente viene dall'ultimo `X-Forwarded-For`, altrimenti dal peer TCP; è solo un consiglio, e restituisce solo la classe;
    - un avviso solo per gli admin, quando il browser è in HTTPS ma il cookie non è `Secure`, col rimedio per Nginx o l'uscita da `never`;
    - niente `FORWARDED_ALLOW_IPS`.
    - Il coordinatore avvisa Q.
  - `admin/service_exposure` è di Q: le righe per i livelli 3 e 4 le mando a lui, e le inserisce lui.
- Il coordinatore conferma: i test sul DB temporaneo isolato, nessun runner, nessun catalogo. Al checkpoint le righe del CHANGELOG; `demote`, `deactivate` e la cancellazione erano già nella v1.1.0.

## 1. Stato verificato (2026-10-09, sul codice a `9b2acdd5d`)

- **`set_user_admin`** (`user_service.py:245-279`): controlla solo «già admin» e «non admin». **`set_user_active`** (`:215-242`) non controlla niente.
- **Chi li chiama**: solo la CLI, `scripts/user_cli.py`. `demote` e `promote` passano da `cmd_set_admin` (`:164-177`), `deactivate` e `activate` da `cmd_set_user_active` (`:147-161`).
  - Nessuna API cambia `is_superuser` o `is_active` di un utente: solo la registrazione fa admin il primo utente (`auth.py:200`).
- **Il login** rifiuta un utente inattivo (`auth.py:77`, `:102`). Quindi disattivare l'ultimo amministratore attivo blocca anche lui fuori dall'amministrazione.
- **La cancellazione dell'account** (`auth.py:296-300`) rifiuta l'unico admin con `count_superusers` (`:336-348`), che però conta **anche gli inattivi**. Un admin il cui unico collega è inattivo può cancellarsi, e lasciare l'istanza senza amministratori attivi.
- **La CLI esce sempre con 0**: `_dispatch_user_from_devpy` (`user_cli.py:363-378`) restituisce 0 anche quando il comando stampa ❌. È preesistente, per tutti i comandi `user`.
- **v1.1.0** (sul tag): `set_user_admin` e `set_user_active` sono uguali, senza guardia, e la CLI ha `demote` e `deactivate`. **Il difetto c'è già nella v1.1.0.**
- **I test**: `TestSetUserActive` e `TestSetUserAdmin` in `test_user_profile.py` (`services user-profile`, registrato).
  - Usano il DB **condiviso** della corsia, dove ci sono già altri admin attivi, come `e2e_test_admin`.
  - Così `test_demote_user_from_admin` oggi passa solo perché esistono altri admin.
  - L'ultimo admin attivo si prova solo su un DB isolato: il servizio prende la sessione, quindi un DB temporaneo col suo schema basta.

## 2. Il disegno

- **Una funzione nuova**: `count_active_superusers(session, *, excluding_user_id=None)` (`is_superuser` e `is_active`). `count_superusers` resta com'è.
- **`set_user_admin(…, is_admin=False)`**: se il bersaglio è un admin attivo e non c'è un altro admin attivo, `(False, "User 'X' is the last active administrator: promote another user first")`. Il DB non cambia.
  - Retrocedere un admin inattivo resta permesso, perché non toglie niente agli attivi.
- Il messaggio arriva alla CLI così com'è: `❌ <messaggio>`.

## 3. Le decisioni (✅ prese, §0.1)

1. **`deactivate` sull'ultimo admin attivo**: lo stesso rifiuto, «… is the last active administrator: promote or activate another administrator first». È **visibile**: oggi il comando riesce, e chiude fuori tutti gli amministratori. Consiglio: sì.
2. **La cancellazione dell'account**: allineare la guardia agli admin **attivi**, con `count_active_superusers(excluding=current)`. È **visibile**: un admin il cui unico collega è inattivo oggi può cancellarsi, domani no. Consiglio: sì, è lo stesso principio. Il messaggio resta quello di oggi.
3. **Il codice d'uscita della CLI**: 1 quando un comando `user` fallisce, invece di 0. È **visibile** per chi usa gli script e riguarda tutti i comandi `user`. Consiglio: sì, ma è una decisione a parte.

## 4. I test, rossi prima (test-author, solo file registrati)

In `test_user_profile.py` (`services user-profile`):
- **Un DB temporaneo isolato**, con lo schema da `SQLModel.metadata`. Ci si prova:
  - il rifiuto sull'ultimo admin attivo, anche quando ci sono admin inattivi, e che il DB resti com'era;
  - il permesso quando c'è un altro admin attivo;
  - il permesso di retrocedere un admin inattivo;
  - `count_active_superusers`.
- `test_demote_user_from_admin`: si crea il suo secondo admin attivo, così non dipende dal DB condiviso.
- I casi di §3.1 e §3.2 si aggiungono dopo la decisione. Il §3.2 andrebbe in `test_account_deletion_api.py` (`api account-deletion`, mio).

## 4.1 Il disegno, dopo le decisioni

- **`set_user_active(…, active=False)`** sull'ultimo admin attivo: `(False, "User 'X' is the last active administrator: promote or activate another administrator first")`. Il DB non cambia.
- **`auth.delete_own_account`**: `count_active_superusers(excluding_user_id=current)`. Se è 0, il 400 di oggi, col messaggio di oggi.
  - ACCDEL-002 e REG-007 (`test_auth_api.py`) simulano «l'unico admin» patchando `count_superusers`. Con la cura non simulerebbero più niente: vanno portati sul DB isolato, senza patch sui nomi.
- **La CLI**: `_dispatch_user_command` restituisce l'esito del comando. `_dispatch_user_from_devpy` restituisce 0 o 1, e così fa `user_cli.py` lanciato da solo.
- **`JWT_SECRET`**: `_ensure_shared_jwt_secret(env)` in `dev.py`. Lo stub è il `setdefault` di oggi; la cura scrive un segreto nuovo quando il valore manca, è vuoto o è fatto solo di spazi.

## 5. Superfici

| File | Cosa |
|---|---|
| `backend/app/services/user_service.py` | `count_active_superusers`, le guardie |
| `backend/app/api/v1/auth.py` | §3.2: la guardia sugli admin attivi |
| `scripts/user_cli.py` | §3.3: il codice d'uscita |
| `dev.py` | `_ensure_shared_jwt_secret` |
| `backend/test_scripts/test_services/test_user_profile.py` (test-author) | i test |
| `backend/test_scripts/test_api/test_account_deletion_api.py`, `test_auth_api.py` (REG-007) (test-author) | §3.2, e il passaggio dalla patch al DB isolato |
| `backend/test_scripts/test_utilities/test_dev_cli_image.py` (test-author) | §3.3 e `JWT_SECRET` |
| questo piano | — |

Nessun file del runner, nessun catalogo i18n. I messaggi della CLI e il `detail` dell'API sono in inglese, come oggi.

## 6. Gate

- `services user-profile`; `api account-deletion` e `api auth`, se §3.2.
- Una prova a mano della CLI su un DB temporaneo: `user demote` e `deactivate` sull'ultimo admin.
- ruff e black; `git diff --check`; porte libere.

## 7. Avanzamento

### 7.0 ✅ L'analisi (2026-10-09)

> **Note implementazione**: §1–§3. La base `9b2acdd5d` è verificata e pulita.

### 7.1 ✅ Gli stub e i rossi (2026-10-09)

> **Note implementazione**:
> - **Gli stub**, prima dei rossi:
>   - `count_active_superusers`, con la firma definitiva, che restituisce 0;
>   - `_ensure_shared_jwt_secret(env)` in `dev.py`: il `setdefault` di oggi, spostato dal corpo di `cmd_server` in una funzione che si può testare.
> - **Rossi** (test-author, su 3 file registrati, in parallelo):
>   - `services user-profile` (`test_user_profile.py`): **6 failed, 30 passed**, tutti su `AssertionError`. Sono il conteggio ×2, e il rifiuto di `demote` e di `deactivate` ×2 ciascuno, con e senza un admin inattivo accanto. Tutto su un **DB SQLite temporaneo isolato** creato da `SQLModel.metadata`. `test_demote_user_from_admin` ora si crea il suo secondo admin.
>   - `utils dev-cli-image` (`test_dev_cli_image.py`): **6 failed, 25 passed**:
>     - IMG-006b: un comando fallito esce con 0;
>     - IMG-009 `demote`: retrocede l'ultimo admin, exit 0;
>     - IMG-009 `deactivate`, e IMG-009b: **crash con traceback**, vedi il fuori pista;
>     - IMG-010b ×2: `JWT_SECRET` `''` e `'   '` restano così.
>
> **⚠️ Fuori pista — `user deactivate` e `activate` crollavano già**. `set_user_active` leggeva `user.id` dopo il `commit()` (`user_service.py:241`). La sessione della CLI ha `expire_on_commit=True`, quindi `MissingGreenlet`, traceback ed exit 1, **dopo** aver già salvato la modifica. L'ha previsto il test-author e il rosso l'ha confermato. Il codice sul tag è lo stesso: c'è già nella 1.1.0. Curato nella stessa funzione: l'id si legge prima del commit, come già fa `set_user_admin`.

### 7.2 ✅ La cura (2026-10-09)

> **Note implementazione**:
> - **`user_service.py`**:
>   - `count_active_superusers` (`is_superuser` e `is_active`, con `excluding_user_id`);
>   - `_is_last_active_admin(session, user)`;
>   - `set_user_admin(…, False)` rifiuta l'ultimo admin attivo: «… is the last active administrator: promote another user first»;
>   - `set_user_active(…, False)` rifiuta lo stesso: «… promote or activate another administrator first». E `user_id` si legge prima del commit.
>   - Le docstring dicono la regola.
> - **`user_cli.py`**:
>   - ogni comando restituisce il suo esito (`cmd_list_users` ora `True`);
>   - `_dispatch_user_command` lo restituisce;
>   - `_dispatch_user_from_devpy` e `main()` danno 0 o 1;
>   - lanciato da solo, `sys.exit(main())`.
> - **`dev.py`**: `_ensure_shared_jwt_secret`. Un valore che manca, vuoto o fatto di spazi diventa `secrets.token_urlsafe(64)`; un valore vero resta com'è.
> - **Verdi**: `services user-profile` **36/36**; `utils dev-cli-image` **31/31**.
> - **Lint**:
>   - `user_service.py` pulito;
>   - `user_cli.py` ha gli stessi 2 rilievi di `HEAD` (W293, PLC0415), solo spostati di una riga;
>   - `dev.py` ha gli stessi rilievi di `HEAD`.
> - Manca ancora `auth.py` (§3.2): aspetta il suo rosso.
> - **`auth.py`** (§3.2), dopo il suo rosso:
>   - `delete_own_account` conta gli **altri admin attivi** (`count_active_superusers(excluding_user_id=current)`), col messaggio di oggi;
>   - `count_superusers` non ha più chiamanti nell'app, e resta per i suoi test.
>   - **Rosso** (test-author, `api account-deletion`): **1 failed, 5 passed**. È ACCDEL-003, un admin attivo il cui unico collega è inattivo: oggi la cancellazione passa.
>   - **Verde**: `api account-deletion` **6/6**, `api auth` **24/24**.
>
> **⚠️ Fuori pista — ACCDEL-002 e REG-007 sul DB privato**.
> - ACCDEL-002 patchava `count_superusers`; con la cura non avrebbe simulato più niente. Ora chiama l'handler su un DB privato, senza patch. L'unica patch rimasta porta la cartella dei report BRIM in `tmp_path`: gli id privati partono da 1 come quelli della corsia.
> - REG-007 in realtà patchava `count_users`, non `count_superusers`: la mia ipotesi era sbagliata, l'ha corretta il test-author. L'ha portato comunque sul DB privato, perché a ogni giro lasciava nel DB della corsia un superuser attivo `bootstrapreg_<ms>`.

### 7.3 ✅ Il cookie `Secure` in «auto» (2026-10-09)

> **Note implementazione — lo stub** (il comportamento non cambia):
> - `config.Settings.SESSION_COOKIE_SECURE: Literal["auto","always","never"] = "auto"`, con un validatore che toglie gli spazi e porta in minuscolo. Un valore sbagliato ferma l'avvio col messaggio di pydantic.
> - `auth.py`:
>   - `SESSION_COOKIE_SECURE_MODE`, letto una volta all'import (`get_settings()` non ha cache e rilegge `.env` a ogni chiamata);
>   - `session_cookie_secure(request)`, che per ora restituisce `False`;
>   - `login`, `logout` e `delete_own_account` hanno ora `http_request: Request` (il parametro `request` di `login` è il body) e passano `secure=session_cookie_secure(http_request)` al `set_cookie` e ai due `delete_cookie`;
>   - la costante `SESSION_COOKIE_SECURE = False` non c'è più.
> - **I proxy**: l'app non li gestisce da sé. uvicorn parte sempre dalla sua CLI (Docker `CMD`, `dev.py`), con i proxy-headers attivi, e crede a `X-Forwarded-Proto` solo da `FORWARDED_ALLOW_IPS` (default 127.0.0.1). Quindi dietro un reverse proxy in un altro container `auto` resta senza `Secure`, finché l'admin non imposta `FORWARDED_ALLOW_IPS`: va nella doc.
> - **localhost**: `auto` resta senza `Secure` anche su `http://localhost`. I browser Chromium e Firefox lo accetterebbero, Safari storicamente no, e il traffico non lascia la macchina.
>
> **Note implementazione — l'intestazione del proxy** (dopo il sì del coordinatore):
> - Perché: uvicorn crede a `X-Forwarded-Proto` solo dagli IP di `FORWARDED_ALLOW_IPS`, e il default è 127.0.0.1. Con Docker, ai livelli 3 e 4 di `service_exposure`, la richiesta arriva dal gateway del container, non da 127.0.0.1. Senza questa regola il default restava senza `Secure` proprio nei casi HTTPS documentati.
> - Verificato nei sorgenti:
>   - il reverse proxy di Tailscale imposta `X-Forwarded-Proto: https` quando l'ingresso è TLS: `addProxyForwardedHeaders` in `ipn/ipnlocal/serve.go`, chiamato nel `Rewrite`;
>   - il sidecar del livello 4 esegue `ts funnel 6040` dietro socat, che inoltra in TCP, quindi l'intestazione arriva;
>   - Caddy la imposta da sé («X-Forwarded-For, X-Forwarded-Proto and X-Forwarded-Host are also set implicitly», `reverseproxy.go`);
>   - Traefik anche (`pkg/middlewares/forwardedheaders`);
>   - Nginx no.
>
> **Rossi** (test-author, `test_auth_api.py` e `test_account_deletion_api.py`):
> - COOKIE-001…005, in `TestSessionCookieSecure`, dal vivo su `127.0.0.1`:
>   - login e logout in HTTP senza `Secure`: guardie;
>   - login, logout e cancellazione dell'account con `X-Forwarded-Proto: https`: `Secure`, rossi.
> - COOKIE-010: la matrice dei modi per lo schema, 3×2.
> - COOKIE-011: l'intestazione. Contiene i 3 casi chiesti più 3 del test-author: il primo valore con maiuscole e spazi, l'intestazione che non spegne mai, `always` che la ignora.
> - COOKIE-020…022, la configurazione (guardie): default `auto` con `_env_file=None`; normalizzazione da argomento e da ambiente; `ValidationError` su un valore sbagliato.
> - `test_account_deletion_api.py`: la chiamata in-process passa `http_request=`.
>
> | comando | esito |
> |---|---|
> | `dev.py test --test-port 6156 --data-dir /tmp/librefolio-r2-l api auth` | **10 failed, 34 passed**: i 10 rossi previsti, tutti su asserzioni (`[new] …` / `assert False is True`), nessuno nel setup |
> | `… api account-deletion` | 6 passed |
>
> **La cura** (`auth.py`, `session_cookie_secure`):
> - `always` → True; `never` → False;
> - `auto` → `request.url.scheme == "https"`, oppure il primo valore di `X-Forwarded-Proto`, senza spazi e in minuscolo, è `https`.
>
> | comando | esito |
> |---|---|
> | `ruff check` e `black --check` su `auth.py` | puliti |
> | `… api auth` | **44 passed** |
>
> - **Verifica a mano**:
>   - `SESSION_COOKIE_SECURE=bogus python -c "import backend.app.main"` → exit 1, `ValidationError … Input should be 'auto', 'always' or 'never'`: un valore sbagliato ferma l'avvio;
>   - `" Always "` → `always`.
>   - Data-dir temporanea, vuota e poi cancellata.
> - **`.env.example`**: la sezione «Login Session Cookie», con `# SESSION_COOKIE_SECURE=auto` commentato e le tre modalità. Nessun test né script legge quel file (`grep`).
> - **⚠️ Fuori pista — `FORWARDED_ALLOW_IPS` da `.env`**: arriva a uvicorn anche con `dev.py server`, perché `configure_server_runtime` → `_load_project_dotenv()`. In Docker arriva da `env_file: .env`. Con la regola nuova del cookie non serve; il fatto è passato a Q per la pagina dell'indicatore.

### 7.4 ✅ Gate del lotto (2026-10-09)

I comandi sono tutti `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6156 --data-dir /tmp/librefolio-r2-l <cat> <azione>`, uno alla volta (`/tmp/libreFolio_gates_34s2.sh`).

| gate | esito |
|---|---|
| `services user-profile` | 36 passed |
| `utils dev-cli-image` | 31 passed |
| `api all` | **852 passed, 2 skipped** (7 min 50 s) |
| `front-utility app-start-auth` | ❌ setup: «Failed to create user e2e_test_user:», prima dei test (vedi sotto) |
| `check-orphans` | pulito |

> **⚠️ Fuori pista — il setup degli E2E si ferma, colpa di questo lotto**.
> - Riproduzione: `python scripts/user_cli.py --test-db create-superuser e2e_test_user …` → **exit 1**, stdout «❌ Username already taken», stderr vuoto.
> - `_ensure_test_users` (`scripts/test_runner/_frontend_common.py:192-195`) crea gli 8 utenti E2E con `create-superuser` dopo il populate, che 3 di loro li ha già creati. Tollera l'errore solo con «already exists» in **stderr**; la CLI scrive su stdout e dice «Username already taken» / «Email already registered».
> - Quel controllo non ha mai funzionato: lo nascondeva l'uscita sempre a 0, corretta in questo lotto (decisione 3). Si fermano tutti gli E2E e la gallery (`dev.py:938`, stessa funzione).
> - Verdetto (test-triage): **defect**, nel chiamante.
> - Proposta al coordinatore: il controllo guarda stdout e stderr e accetta le tre frasi; ogni altro errore resta un errore. È un file del runner, quindi in attesa del suo sì.
> - A margine, preesistente: `create-superuser` crea **amministratori** i 5 utenti che il populate non crea (alice…eve). Non toccato.
>
> **La cura del chiamante** (coordinatore: «`_frontend_common.py` è tuo, solo per `_ensure_test_users`»):
> - il controllo guarda stdout e stderr insieme, e accetta «already taken», «already registered» e «already exists»;
> - ogni altro errore resta un errore, e il messaggio mostra stdout quando stderr è vuoto;
> - la CLI non cambia.
> - È un buon esempio di **difetto nascosto dall'uscita a 0**: il ramo di tolleranza esisteva, ma cercava una frase che la CLI non scrive mai, sul flusso sbagliato. Nessuno se n'era accorto, perché il codice d'uscita era sempre 0.

| gate dopo la cura | esito |
|---|---|
| `front-utility app-start-auth` | **3 passed**: il setup degli utenti passa |
| `front-user multi-user` (un'altra categoria, usa più utenti E2E) | **2 passed** |
| `check-orphans` | pulito |

### 7.5 ✅ Le configurazioni morte (2026-10-09)

Aggiunta al lotto, approvata dal developer: «si puliamo le configurazioni morte».

> **Note implementazione**:
> - **`PORTFOLIO_BASE_CURRENCY`**: `git grep` → nessun codice la leggeva. Tolta da:
>   - `config.py`: il campo e la riga del docstring; al suo posto nel docstring `SESSION_COOKIE_SECURE`;
>   - `.env.example`: la sezione «Portfolio»;
>   - `Dockerfile`: dal blocco `ENV`, con la continuazione chiusa su `LOG_LEVEL=INFO`.
>   - Le pagine IT/FR/ES di `configuration` la citano ancora: è debito di traduzione. CHANGELOG, journal e devWiki (F-006, F-062) sono storia, non toccati.
> - **Un vecchio `.env` non rompe l'avvio**: `Settings` ha `extra="ignore"`. Verificato con un file `.env` vero che contiene `PORTFOLIO_BASE_CURRENCY=USD`, più la variabile d'ambiente a `GBP`: nessun errore, il resto letto, nessun attributo.
> - **`SESSION_COOKIE_MAX_AGE`** (`auth.py`): costante senza usi (`git grep`), tolta. La durata vera del cookie viene da `session_ttl_hours`.
> - Il commento di `SESSION_COOKIE_SECURE` in `config.py` diceva «a trusted reverse proxy»: riallineato alla regola nuova.
> - **Doc**: `configuration.en.md` (docs-writer). Tolta la riga; una frase per chi ha ancora la variabile nel suo `.env`.

| gate | esito |
|---|---|
| `ruff check` e `black --check` su `config.py` e `auth.py`; `ruff` su `_frontend_common.py` | puliti |
| `utils release-image-contract` (di M; il `Dockerfile` cambia) | **133 passed** |
| `utils dev-cli-image` | **31 passed** |
| `api auth` | **44 passed** |

### 7.6 ✅ La doc admin e sviluppatore (2026-10-09)

> **Note implementazione** (docs-writer, solo EN, niente stamp: il debito di traduzione resta):
> - `admin/configuration.en.md`:
>   - nell'introduzione «the session key» diventa «login sessions»;
>   - la riga `SESSION_COOKIE_SECURE` dopo `JWT_SECRET`;
>   - tolta la riga `PORTFOLIO_BASE_CURRENCY`, e sotto la tabella una frase per i vecchi `.env`;
>   - il riquadro «🔒 HTTPS and reverse proxies — the session cookie», con ancora `{: #session-cookie-secure }`. Contiene le tre modalità, i proxy che mandano l'intestazione da soli (Tailscale, Caddy, Traefik), la riga per Nginx e l'uscita `never`.
> - Build strict pulito. `check-links` esce con 1 solo per un link rotto preesistente (`user/assets/detail/chart/#rolling-return` in it/fr/es), lo stesso di prima.
> - `translate-validate`: `configuration` passa da 10 a 13 errori per lingua (3 nuovi, tutti del cookie), e la pagina va ritradotta.
>
> **⚠️ Fuori pista — `admin/service_exposure` è passato a Q** a metà lavoro (coordinatore). Il docs-writer ha annullato le sue due frasi: `git diff --quiet` → 0. Le righe dei livelli 3 e 4 le ho mandate a Q; le inserisce lui.
> - L'ancora esiste solo in EN. Ho avvisato Q: nelle versioni IT/FR/ES e nella sua pagina solo EN, che viene costruita in 4 lingue, va linkata la pagina senza ancora, altrimenti il build strict si ferma.
>
> **Doc sviluppatore diventata falsa**, segnalata dal docs-writer; chiesto al coordinatore chi la corregge:
> - `developer/architecture/users_and_brokers.md:19` cita `SESSION_COOKIE_SECURE = False`;
> - `developer/architecture/security.md:231` consiglia un `X-Forwarded-Proto` fisso a `https`.
>
> **La doc sviluppatore** (coordinatore: «Concesso: correggi tu, col docs-writer, solo EN»). I testi sono quelli approvati, byte per byte:
> - `developer/architecture/users_and_brokers.md:19`: il punto `Secure` ora dice che lo decide `session_cookie_secure()` da `SESSION_COOKIE_SECURE` (`auto`, `always`, `never`), con lo stesso comportamento per login, logout e cancellazione dell'account. Il link va a `../../admin/configuration.md`, senza ancora, perché le pagine sviluppatore sono costruite in 4 lingue.
> - `developer/architecture/security.md:231`: `X-Forwarded-Proto` è lo schema usato dal browser (`$scheme` in Nginx), e LibreFolio lo legge per il cookie `Secure`.
> - Build strict pulito; `check-links` rosso solo sul noto `#rolling-return`, che è già nel backlog; `git diff --check` pulito. Sono pagine solo EN, quindi nessun debito di traduzione.

### 7.7 ✅ Il checkpoint (2026-10-09)

I messaggi e i percorsi sono in `/tmp/libreFolio_commits/l-34s2-c{1..4}.{msg,paths}`, in quest'ordine:

| commit | percorsi | dipende da |
|---|---|---|
| C1 `fix(users): keep one active administrator` | `user_service.py`, `test_user_profile.py` | — |
| C2 `fix(auth): Secure cookie, active admin on delete` | `auth.py`, `config.py`, `test_auth_api.py`, `test_account_deletion_api.py`, `.env.example`, `Dockerfile`, `admin/configuration.en.md`, `developer/architecture/users_and_brokers.md`, `developer/architecture/security.md` | C1 (`count_active_superusers`) |
| C3 `fix(cli): exit status, shared JWT secret` | `user_cli.py`, `_frontend_common.py`, `dev.py`, `test_dev_cli_image.py` | C1 (la guardia, provata dalla CLI) |
| C4 `docs(journal): plan 34 step 2, last admin` | questo piano | — |

- I commit si separano per percorso, e ognuno è coerente da solo. La versione HEAD di `test_dev_cli_image.py` non degrada né disattiva nessuno, quindi C1 da solo non la rompe. La tolleranza del runner arriva in C3 insieme alle uscite a 1.
- Porte 6156 e 6166 libere; `git diff --check` pulito.
- Dopo questo checkpoint `dev.py` passa a N (coordinatore): niente altro pianificato su `dev.py`.
