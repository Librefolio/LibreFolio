# 📝 Configurazione

Le opzioni di avvio di LibreFolio stanno in un file `.env`: porte, cartella dei dati, logging, sessioni di accesso, registrazioni, segreti e alcune funzionalità opzionali.

**Dove si scrive**: nel file `.env` nella cartella di LibreFolio (la radice del progetto; con Docker, la cartella di `docker-compose.yml`). Con Docker, le stesse variabili valgono anche nel blocco `environment:` di `docker-compose.yml`, che prevale su `.env`. LibreFolio legge `.env` all'avvio.

Le opzioni che modifichi dall'interno dell'app sono invece le [Impostazioni globali](settings.md).

!!! info "📚 Questa guida è in più pagine"

    - [Configurazione: Segreti e impostazioni dei plugin](configuration_secrets.md): le opzioni che sono segreti, come leggerle dai file, la chiave dell'istanza e le impostazioni dei plugin.
    - [Configurazione: Controlli e protezioni](configuration_security.md): ciò che LibreFolio controlla all'avvio, le protezioni del browser (Content-Security-Policy, protezione dei frame) e come si arresta.
    - [Configurazione: Account e ricerca degli asset](configuration_accounts.md): chi può registrarsi, il limite sugli accessi non riusciti, l'amministratore iniziale, l'ordine dei provider di prezzi nella ricerca e la ricerca web.

---

## 🔧 Creare il file `.env`

**Nella cartella di LibreFolio**, da terminale:

1. Copia il file di esempio:

    ```bash
    cp .env.example .env
    ```

    Ottieni un `.env` con tutte le opzioni, raggruppate per ciò che fanno. Con l'immagine Docker precompilata, la guida all'[installazione con Docker](../user/installation.md) scarica lo stesso esempio come `.env`.

2. Modifica i valori che ti servono. Un'opzione commentata, come `# SESSION_COOKIE_SECURE=auto`, mostra il predefinito: rimuovi il `#` solo per cambiare il valore. I nomi distinguono maiuscole e minuscole.

3. Riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`.

---

## ✏️ Opzioni principali {: #main-options }

**Dove**: nel `.env` di LibreFolio, oppure nell'ambiente del container (blocco `environment:` di `docker-compose.yml`). Poi riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`.

Nelle opzioni principali e nelle impostazioni di rischio riportate sotto, un valore del tipo sbagliato o fuori intervallo arresta il server all'avvio con un errore. Le eccezioni sono nei dettagli sotto ogni tabella, con ciò che compare nel log.

**Server, dati e log**

| Variabile | Predefinito | Cosa fa |
| --- | --- | --- |
| `PORT` | `6040` | Porta del server web. Con Docker Compose, la porta aperta sull'host: il container resta sempre in ascolto su `6040`. |
| `TEST_PORT` | `6041` | Porta del server di test (`./dev.py server --test`). |
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Cartella del database, degli upload, dei report del broker e dei log; un percorso relativo parte dalla cartella del progetto. |
| `LOG_LEVEL` | `INFO` | Quanto registra il server nei log: `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR` o `CRITICAL`. |
| `PREVIEW_CACHE_MAX_MB` | `50` | Memoria, in MB, della cache delle anteprime delle immagini, per ciascun processo del server. |

- **`LIBREFOLIO_DATA_DIR` con Docker**: fissata a `/app/backend/data/prod-docker`. Per spostare i dati sull'host, **in `docker-compose.yml`** modifica il lato sinistro del volume `./LibreFolio-data`.
- **`LOG_LEVEL`**: con `DEBUG` o `TRACE`, l'app web scrive nella console del browser anche ogni chiamata al server non riuscita, comprese quelle rifiutate (una risposta `4xx`); agli altri livelli, solo gli errori del server, le chiamate rimaste senza risposta e le risposte che non riesce a leggere.

**Sessioni di accesso e reverse proxy**

| Variabile | Predefinito | Cosa fa |
| --- | --- | --- |
| `JWT_SECRET` | _non impostato_ | Chiave che firma le sessioni di accesso. Vedi [Mantenere gli utenti connessi](index.md#session-persistence). |
| `SESSION_COOKIE_SECURE` | `auto` | Quando il cookie della sessione di accesso viene inviato solo tramite HTTPS: `auto` (se il browser usa HTTPS), `always` o `never`. Vedi [HTTPS e reverse proxy](#session-cookie-secure). |
| `LIBREFOLIO_CLIENT_IP_HEADER` | _non impostato_ | Dietro un reverse proxy, l'header in cui questo trasmette l'indirizzo del visitatore, come `Fly-Client-IP` su Fly.io. Vedi [L'indirizzo del visitatore](connection_proxy.md#client-address). |

- **`JWT_SECRET`** non impostata, vuota o composta solo da spazi: una nuova chiave a ogni avvio, quindi tutti devono accedere di nuovo dopo un riavvio. `JWT_SECRET_FILE` la legge invece da un file: vedi [Segreti](configuration_secrets.md#secrets).
- **`LIBREFOLIO_CLIENT_IP_HEADER`**: impostala solo se ogni richiesta attraversa quel proxy.

**Protezioni del browser e documentazione dell'API**

| Variabile | Predefinito | Cosa fa |
| --- | --- | --- |
| `LIBREFOLIO_FRAME_PROTECTION` | `false` | Lascialo non impostato su un'installazione propria. `true` consente solo alle pagine di LibreFolio di mostrarlo in un frame. Vedi [Protezione dei frame](configuration_security.md#frame-protection). |
| `LIBREFOLIO_CSP_REPORT_ONLY` | `false` | Lascialo non impostato su un'installazione propria. `true` aggiunge alle pagine dell'app web una seconda Content-Security-Policy più ampia, in modalità report-only. Vedi [La policy report-only](configuration_security.md#csp-report-only). |
| `LIBREFOLIO_API_DOCS` | `false` | Lascialo non impostato. `true` fornisce le pagine di documentazione dell'API: Swagger UI su `/api/v1/docs`, ReDoc su `/api/v1/redoc`, schema su `/api/v1/openapi.json`. |

- **`LIBREFOLIO_FRAME_PROTECTION`** non impostata: le dashboard a un altro indirizzo, come i pannelli di Home Assistant, possono mostrare LibreFolio in un frame. `true` aggiunge a ogni risposta `X-Frame-Options: SAMEORIGIN` e `Content-Security-Policy: frame-ancestors 'self'`. Le tre regole `object-src 'none'; base-uri 'self'; form-action 'self'` non dipendono da questa opzione: le pagine di LibreFolio le includono sempre ([La Content-Security-Policy](configuration_security.md#csp)). Valori validi: `true` o `false`; anche `1`/`0`, `yes`/`no` e `on`/`off`, senza distinzione tra maiuscole e minuscole; qualsiasi altro valore arresta il server all'avvio.
- **`LIBREFOLIO_CSP_REPORT_ONLY`**: solo le pagine dell'app web, non la documentazione o l'API. Non blocca nulla: il browser elenca nella console per sviluppatori ciò che quella policy bloccherebbe, senza inviare segnalazioni da nessuna parte. La [Content-Security-Policy](configuration_security.md#csp) applicata resta sempre attiva. Stessi valori di `LIBREFOLIO_FRAME_PROTECTION`.
- **`LIBREFOLIO_API_DOCS`** disattivata: le pagine rispondono `404`, in ogni profilo e anche con Docker (un'istanza in uso non pubblica la mappa della propria API). Un browser che apre uno di questi indirizzi, un altro indirizzo sotto `/api/` o una pagina di documentazione inesistente sotto `/mkdocs/` viene portato all'app (`/`); un programma riceve comunque `404` con `{"detail": "Not Found"}`. Nell'app web, una pagina inesistente ti riporta alla pagina da cui provenivi o alla Dashboard. `./dev.py server --debug` la attiva; le esecuzioni di test di LibreFolio la tengono attiva. Valori validi: `true` o `false`; anche `1` e `0`. La policy delle pagine stesse: [La Content-Security-Policy](configuration_security.md#csp).

**Link dell'istanza: supporto, termini di servizio, privacy**

| Variabile | Predefinito | Cosa fa |
| --- | --- | --- |
| `LIBREFOLIO_SUPPORT_URL` | _non impostato_ | Dove gli utenti dell'istanza chiedono aiuto: una pagina con `http://` o `https://`, oppure un indirizzo email come `mailto:help@example.org`. |
| `LIBREFOLIO_TOS_URL` | _non impostato_ | I termini di servizio dell'istanza: una pagina con `http://` o `https://`, collegata dal link **Termini di servizio** dell'avviso legale. |
| `LIBREFOLIO_PRIVACY_URL` | _non impostato_ | L'informativa sulla privacy dell'istanza, collegata come **Informativa sulla privacy** accanto ai termini di servizio: stesse regole di `LIBREFOLIO_TOS_URL`. |

- **I tre indirizzi sono pubblici**: chiunque possa raggiungere il server può leggerli su `/api/v1/system/instance`.
- **`LIBREFOLIO_SUPPORT_URL`**: ad esempio per un asset che la ricerca non trova ([Segnalacelo](../user/assets/create-edit.md#let-us-know), sotto i risultati della ricerca). Con un indirizzo email, l'app di posta dell'utente apre un messaggio con i dettagli della ricerca. Con una pagina, questa si apre in una nuova scheda e riceve la segnalazione nei parametri di query `title` e `body`, come una issue GitHub precompilata, così che un modulo di supporto possa compilarsi da solo; i dettagli vengono anche copiati, per incollarli lì. Non impostato: su un'installazione propria (il profilo `selfhosted`), si apre una nuova issue pubblica su GitHub di LibreFolio con i dettagli, perché l'utente la riveda prima di inviarla. Qualsiasi altro valore viene ignorato, come se non fosse impostato, e il server lo registra nei log una volta. Anche una pagina il cui indirizzo contiene un nome utente o una password vale come non impostata.
- **`LIBREFOLIO_TOS_URL`**: l'avviso legale che ogni utente vede (Impostazioni › Informazioni, pagina di benvenuto, sotto la scheda di ogni pagina di accesso, in fondo alla barra laterale) rimanda ai termini con il link **Termini di servizio**, aperto in una nuova scheda. Non impostato: nessun link, solo l'avviso. A differenza di `LIBREFOLIO_SUPPORT_URL`, nessun `mailto:`.
- **Valore inutilizzabile in `LIBREFOLIO_TOS_URL` o `LIBREFOLIO_PRIVACY_URL`**, incluso un indirizzo con un nome utente o una password: il server non si arresta mai; quel link resta nascosto e l'avviso legale è mostrato senza di esso. Nel log compare un errore, `Invalid instance link`, la prima volta che ciascun processo del server risponde a `/api/v1/system/instance` (l'app lo legge non appena si apre): la variabile e il suo valore in `problem` (un valore con una `@` non viene mostrato: potrebbe contenere un nome utente o una password) e, in `consequence`, ciò che costa finché non lo correggi, ad esempio `the terms of service link stays hidden until it is fixed: the legal notice shows without it`. Anche una `LIBREFOLIO_SUPPORT_URL` inutilizzabile registra lo stesso errore, con il proprio `consequence`. Correggi il valore, poi riavvia.

**Backup e spazio**

| Variabile | Predefinito | Cosa fa |
| --- | --- | --- |
| `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` | _non impostato_: nessun limite | Lascialo non impostato. Dimensione massima, in megabyte, di un archivio che un amministratore può caricare per verificarlo in vista di un ripristino; `0` significa nessun limite. Vedi [Il limite di caricamento di un ripristino](backup_restore.md#restore-upload-limit). |
| `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` | _non impostato_: nessun limite | Lascialo non impostato. Dimensione massima, in megabyte, a cui un archivio può essere decompresso durante la verifica per un ripristino, secondo le dimensioni dichiarate dal suo manifest; `0` significa nessun limite. |
| `LIBREFOLIO_BACKUP_RECIPIENTS` | _non impostato_ | Una o due chiavi pubbliche age (`age1…`), separate da virgole: `backup create --sealed` crea allora un backup [sigillato](backup_sealed.md#sealed). Non è un segreto. |
| `LIBREFOLIO_STORAGE_LIMIT_MB` | _non impostato_ | Lascialo non impostato su un'installazione propria: il limite si imposta nella barra dello spazio della pagina **File**. Spazio che l'istanza può occupare, in megabyte; `0` significa nessun limite. Vedi [La barra dello spazio](backup_restore.md#space-used). |

- **Tutte e quattro sono lette solo dall'ambiente.**
- **`LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`** con un valore che non è un numero intero: il server non si arresta; i caricamenti rispondono `503` e nel log compare un errore, già dall'avvio ([Controlli all'avvio](configuration_security.md#startup-checks)) e poi ogni volta che il limite viene letto.
- **`LIBREFOLIO_BACKUP_MAX_RESTORE_MB`**: un valore impostato da te prevale sempre, `0` incluso; anche `backup restore` da riga di comando lo rispetta. Un archivio oltre il limite è rifiutato prima di decomprimere qualsiasi cosa (`unpacked_too_large`). Con un valore che non è un numero intero il server non si arresta: i controlli di un ripristino rispondono `503` (`backup_restore_unavailable`), nel log compare un errore già dall'avvio ([Controlli all'avvio](configuration_security.md#startup-checks)) e poi a ogni controllo, e la scheda **Sicurezza** di Impostazioni › Amministrazione lo segnala (`backup.restore_limit`).
- **`LIBREFOLIO_BACKUP_RECIPIENTS`**: le chiavi come le stampano `backup keygen` o `age-keygen`; due solo mentre si cambia una chiave. Il backup sigillato è un `.tar` che aprono solo le chiavi private corrispondenti, mai la chiave dell'istanza. Un valore inutilizzabile (una chiave non `age1…`, più di due, la stessa due volte) non arresta il server: nel log compare un errore e la scheda **Sicurezza** di Impostazioni › Amministrazione lo segnala (`backup.recipients`).
- **`LIBREFOLIO_STORAGE_LIMIT_MB`** impostata: prevale sull'impostazione **Limite di spazio (MB)**, qualunque valore un amministratore abbia salvato, e la blocca: il campo nella barra dello spazio è disattivato (in grigio) e il salvataggio viene rifiutato. Non impostata: decide l'impostazione, `0` finché un amministratore non salva un altro valore. Un valore che non è un numero intero viene ignorato e vale l'impostazione. Oltre il limite, LibreFolio rifiuta un file caricato, un report del broker, un backup avviato a mano e un ripristino che porterebbe i dati oltre; non elimina nulla. L'amministratore non può alzarlo da qui: il messaggio chiede di farlo a chi ospita l'istanza.

**Provider di prezzi e importazione dai broker**

| Variabile | Predefinito | Cosa fa |
| --- | --- | --- |
| `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS` | `60` | La prima pausa di un provider di prezzi che risponde «troppe richieste» (HTTP 429); ogni rifiuto consecutivo raddoppia la pausa successiva. Un numero intero di secondi da `0` a `86400`; `0` disattiva le pause. Vedi [Pause dei provider](settings.md#provider-pauses). |
| `LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS` | `3600` | La pausa più lunga raggiunta dal raddoppio: un numero intero di secondi da `1` a `86400`, non inferiore alla prima pausa mentre le pause sono attive. |
| `LIBREFOLIO_PROBE_RATE_LIMIT` | `30` | Quante volte al minuto un utente può testare le impostazioni di un provider di prezzi (**Verifica configurazione** nel modulo dell'asset; anche **Chiedi al provider** conta). Un numero intero da `0` a `10000`; `0` disattiva il limite. |
| `LIBREFOLIO_BRIM_PREWARM` | `false` (`true` in modalità test) | Opzionale. `true` rende pronti all'avvio i worker per l'importazione dei report dei broker, con i plugin di importazione caricati. Vedi [Architettura BRIM → Precaricamento e riscaldamento](../developer/backend/brim/architecture.md#parse-pool-warm-up). |

- **Pause dei provider**: durante una pausa nessuna richiesta raggiunge il provider. Attive per impostazione predefinita: un'eccezione alla regola secondo cui una nuova opzione lascia un'installazione com'era. Il `Retry-After` di un provider può comunque chiedere di più, fino a un giorno. Un valore inutilizzabile in una delle due variabili non arresta il server: nel log compare un errore e si applicano entrambi i valori predefiniti.
- **`LIBREFOLIO_PROBE_RATE_LIMIT`**: i test possono chiamare il provider; superato il limite, il modulo indica all'utente quando riprovare. `0` solo per un'istanza di test (lo fa `./dev.py server --test`): nel log compare un avviso a ogni avvio. Letta a ogni test: una modifica si applica senza riavvio. Un valore inutilizzabile non arresta il server: nel log compare un errore e si applica `30`.
- **`LIBREFOLIO_BRIM_PREWARM`**: la prima importazione da broker dopo un avvio è circa 4 secondi più veloce, al costo di circa 80 MB di memoria fin dall'avvio e di circa 1,4 secondi di CPU a ogni avvio; su una macchina cloud piccola costano più dei secondi risparmiati, perciò è disattivata. Valori validi: `true` o `false`; anche `1`/`0`, `yes`/`no` e `on`/`off`, senza distinzione tra maiuscole e minuscole. Qualsiasi altro valore non arresta il server, a differenza delle opzioni principali: nel log compare un avviso all'avvio e l'opzione resta disattivata.

**Email**

| Variabile | Predefinito | Cosa fa |
| --- | --- | --- |
| `LIBREFOLIO_SMTP_HOST` | _non impostato_: email disattivata | Opzionale. Il server SMTP che invia le email di LibreFolio, come `smtp.example.com`. |
| `LIBREFOLIO_SMTP_TLS` | `starttls` | Come viene cifrata la connessione al server SMTP: `starttls`, `tls` o `none`. Vedi [Modalità di cifratura](email.md#encryption-modes). |
| `LIBREFOLIO_SMTP_PORT` | `587` con `starttls`, `465` con `tls`, `25` con `none` | La porta del server SMTP, solo quando non è quella consueta della sua modalità di cifratura. |
| `LIBREFOLIO_SMTP_USER` | _non impostato_: nessun login | L'utente per l'accesso al server SMTP, impostato insieme a `LIBREFOLIO_SMTP_PASSWORD` ([Segreti](configuration_secrets.md#secrets)). |
| `LIBREFOLIO_SMTP_FROM` | _non impostato_ | Il mittente delle email, obbligatorio non appena viene impostato un server. |
| `LIBREFOLIO_SMTP_REPLY_TO` | _non impostato_: le risposte vanno al mittente | Dove vanno le risposte alle email di LibreFolio. |
| `LIBREFOLIO_SMTP_MAX_PER_HOUR` | `50` | Quante email l'istanza può inviare in un'ora, per processo del server. |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` | `20` | Quante email di registrazione un indirizzo client può attivare in un'ora, per processo del server: un numero intero, almeno 1. Vedi [Limiti sulle email di attivazione e reimpostazione della password](email_flows.md#activation-limits). |

- **Variabili `LIBREFOLIO_SMTP_*`**: tutte spiegate in [Email](email.md#variables).
- **`LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS`**: un unico conteggio per le registrazioni, **Invia di nuovo il link** e **Password dimenticata?**. Superato il limite, un nuovo account viene creato e resta in attesa, e la sua email viene trattenuta.

I file `.env` più vecchi possono ancora contenere `PORTFOLIO_BASE_CURRENCY`: LibreFolio lo ignora e i nuovi utenti partono dalla **Valuta predefinita** in [Impostazioni globali](settings.md).

??? info "🔒 HTTPS e reverse proxy — il cookie di sessione"

    `SESSION_COOKIE_SECURE` decide quando il cookie che mantiene gli utenti connessi è `Secure`: il browser lo invia allora solo tramite HTTPS. Maiuscole/minuscole e spazi attorno al valore non contano; qualsiasi altro valore arresta il server all'avvio con un errore.
    {: #session-cookie-secure }

    | Valore | Quando usarlo |
    | --- | --- |
    | `auto` (predefinito) | `Secure` quando il browser ha raggiunto LibreFolio tramite HTTPS, cioè quando il reverse proxy lo dichiara con l'header `X-Forwarded-Proto: https` (conta solo il primo valore). Nessun elenco di proxy attendibili da configurare: l'header può solo attivare `Secure`, mai disattivarlo. Su HTTP in chiaro (`http://localhost:6040`, un IP della LAN, l'IP Tailscale dei Livelli 1 e 2 in [Esposizione sicura](service_exposure.md)) il cookie non è `Secure` e l'accesso funziona. |
    | `always` | Sempre `Secure`: installazione raggiunta solo tramite HTTPS. Su HTTP in chiaro il browser scarta il cookie e l'accesso non resta attivo: la pagina successiva riporta al login. |
    | `never` | Mai `Secure`. Via d'uscita quando un proxy invia `X-Forwarded-Proto: https` a un browser che usa HTTP in chiaro, come Nginx con `proxy_set_header X-Forwarded-Proto https;` codificato a mano in un blocco `server` in HTTP in chiaro: con `auto`, quel browser tornerebbe al login dopo ogni accesso. Meglio correggere il proxy (`$scheme` invece di `https`); `never` è il fallback. |

    Con `auto`, dietro un reverse proxy HTTPS il proxy deve inviare `X-Forwarded-Proto`:

    - **Tailscale Serve e Funnel** (Livelli 3 e 4 in [Esposizione sicura](service_exposure.md)), **Caddy** e **Traefik** lo inviano da soli: nulla da configurare.
    - **Nginx** non lo fa. **Nella configurazione di Nginx**, nel blocco `location` che fa da proxy per LibreFolio, aggiungi:

        ```nginx
        proxy_set_header X-Forwarded-Proto $scheme;
        ```

    - **Qualsiasi altro proxy**: fallo inviare l'header. Oppure, se LibreFolio è raggiungibile solo tramite esso, **nel `.env`**:

        ```bash
        SESSION_COOKIE_SECURE=always
        ```

    Per verificare nel browser se il cookie di sessione è `Secure`: [Verifica della sicurezza della connessione](connection_checks.md#session-cookie).

??? info "🧮 Worker del motore di rischio — regolazione avanzata"

    Le simulazioni di rischio e le ottimizzazioni di portafoglio girano in processi worker separati, avviati al primo utilizzo. I predefiniti vanno bene per la maggior parte delle installazioni: aggiungi una variabile **nel `.env`** solo per cambiarli.

    | Variabile | Predefinito | Cosa fa |
    | --- | --- | --- |
    | `RISK_SIMULATION_WORKERS`, `RISK_OPTIMIZATION_WORKERS` | `1` (1–8) | Processi worker per tipo di job: più processi eseguono più job contemporaneamente. |
    | `RISK_SIMULATION_QUEUE_CAPACITY`, `RISK_OPTIMIZATION_QUEUE_CAPACITY` | `2` (0–64) | Job che possono attendere un worker; oltre quel limite, le nuove richieste vengono rifiutate. |
    | `RISK_SIMULATION_TIMEOUT_SECONDS`, `RISK_OPTIMIZATION_TIMEOUT_SECONDS` | `120` / `60` | Limite di tempo di un job, in secondi. |
    | `RISK_SIMULATION_IDLE_TIMEOUT_SECONDS`, `RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS` | `600` | I worker inattivi si arrestano dopo questo numero di secondi e ripartono con il job successivo; `0` li mantiene in esecuzione. |

---

## 💻 Parametri impostati dagli strumenti

`./dev.py` e Docker Compose li impostano per te: modificali solo se sai perché.

| Variabile | Predefinito | Cosa fa |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Indirizzo su cui è in ascolto `./dev.py server`; `127.0.0.1` accetta solo connessioni locali. Docker Compose usa sempre `0.0.0.0`. |
| `LIBREFOLIO_LOG_LEVEL` | — | Sostituisce `LOG_LEVEL` quando impostata; `./dev.py server --debug` e `./dev.py server --test` la impostano su `DEBUG`. |
| `LIBREFOLIO_API_DOCS` | — | Impostata su `1` da `./dev.py server --debug`, che attiva le pagine di documentazione dell'API (la variabile con lo stesso nome, sopra). |
| `LIBREFOLIO_NO_SCHEDULER` | — | Qualsiasi valore non vuoto, `0` incluso, disattiva le sincronizzazioni programmate dei prezzi e dei tassi FX. Impostata da `./dev.py server --no-scheduler`. |
| `LIBREFOLIO_TEST_MODE` | — | `1`, `true` o `yes`, senza distinzione tra maiuscole e minuscole, passa alla cartella dei dati di test. Solo per le esecuzioni di test di LibreFolio: `./dev.py server --test` e i runner di test la impostano, `./dev.py server` la disattiva. Un server avviato senza `./dev.py` (`uvicorn` direttamente, un'unità di servizio) la prende dal proprio ambiente. Su un'istanza in uso, fuori dal runner di test, i [controlli all'avvio](configuration_security.md#startup-checks) la segnalano come errore. |
| `LIBREFOLIO_TEST_DATA_DIR` | `./backend/data/test` | Cartella dei dati di test; non può sovrapporsi a quella di produzione. |

---

## 🔝 Quale valore prevale

Dalla priorità più alta alla più bassa:

1. Le opzioni `--host`, `--port` e `--data-dir` di `./dev.py server`.
2. Le variabili impostate nella shell.
3. Il file `.env`.
4. I valori predefiniti elencati in questa pagina.

Con Docker Compose, il blocco `environment:` di `docker-compose.yml` prevale su `.env`: fissa `HOST`, `LIBREFOLIO_DATA_DIR` e, all'interno del container, `PORT=6040` (il tuo `PORT` continua a impostare la porta sull'host). Vedi [Docker avanzato](docker_advanced.md#resolution-priority).

Per un'[impostazione di un plugin](configuration_secrets.md#plugin-settings), dalla priorità più alta alla più bassa:

1. La sua variabile: `LIBREFOLIO_PLUGIN_…` prima del vecchio nome usato dal plugin per essa, e ciascuna prima della rispettiva forma `_FILE`.
2. Il valore salvato dentro LibreFolio.
3. Il valore predefinito del plugin.

Una variabile con un valore errato prevale comunque e lascia il plugin non configurato. Un'impostazione personale non ha variabile: il valore salvato dall'utente, poi il valore predefinito.

---

## 📂 Dove vanno i dati

- **Produzione**: `backend/data/prod/`, oppure `LIBREFOLIO_DATA_DIR`. Contiene il database (`sqlite/app.db`), `custom-uploads/`, `broker_reports/`, `logs/` e, una volta che LibreFolio ha creato la [chiave dell'istanza](configuration_secrets.md#instance-key), `secrets/`.
- **Test**: `backend/data/test/`, oppure `LIBREFOLIO_TEST_DATA_DIR`. Stessa struttura, tenuta separata.

[Struttura del filesystem](filesystem.md) descrive in dettaglio ogni cartella e come eseguirne il backup.

---

## 🔗 Vedi anche

- 📄 **[Configurazione: Segreti e impostazioni dei plugin](configuration_secrets.md)** — Segreti, impostazioni dei plugin
- 📄 **[Configurazione: Controlli e protezioni](configuration_security.md)** — Controlli all'avvio, Protezioni del browser, Arresto del server
- 📄 **[Configurazione: Account e ricerca degli asset](configuration_accounts.md)** — Account e registrazioni, L'ordine dei provider di prezzi nella ricerca, Opzionale: ricerca web per nuovi asset
- ⚙️ **[Impostazioni globali](settings.md)** — Opzioni modificate dall'interno dell'app
- 🐳 **[Docker avanzato](docker_advanced.md)** — File Compose, volumi, ID utente e gruppo
- 🧑‍💻 Per gli sviluppatori: **[Sistema delle impostazioni](../developer/architecture/settings.md)** — Come vengono caricati questi valori
- 🔒 Per gli sviluppatori: **[Architettura della sicurezza](../developer/architecture/security.md)** — Segreti, la chiave dell'istanza, i controlli all'avvio e il limite sugli accessi non riusciti
- 🧩 Per gli sviluppatori: **[Impostazioni dei plugin](../developer/architecture/patterns/plugin_settings.md)** — Come i plugin dichiarano le impostazioni e come vengono protetti i segreti
