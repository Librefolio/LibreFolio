# 📝 Configurazione

Le opzioni di avvio risiedono in un file `.env`: porte, la cartella dei dati, logging, sessioni di accesso, registrazioni, segreti e alcune funzionalità opzionali. Si trova nella radice del progetto oppure accanto a `docker-compose.yml` con Docker. Le opzioni che modifichi dall'interno dell'app sono invece le [Impostazioni globali](settings.md).

Questa pagina è l'inizio della guida alla configurazione: come creare il file `.env`, le **opzioni principali** con i relativi valori predefiniti e quale valore prevale quando la stessa opzione è impostata in più punti.

!!! info "📚 Questa guida è in più pagine"

    Il resto della guida approfondisce gli argomenti, una volta acquisite le basi qui presentate:

    - [Configurazione: Segreti e impostazioni dei plugin](configuration_secrets.md): le opzioni che sono segreti, come leggerle dai file, la chiave dell'istanza e le impostazioni dei plugin.
    - [Configurazione: Controlli e protezioni](configuration_security.md): ciò che LibreFolio controlla all'avvio, le protezioni del browser (Content-Security-Policy, protezione dei frame) e come si arresta.
    - [Configurazione: Account e ricerca degli asset](configuration_accounts.md): chi può registrarsi, il limite sugli accessi non riusciti, l'amministratore iniziale, l'ordine dei provider di prezzi nella ricerca e la ricerca web.

---

## 🔧 Creare il file `.env`

Nella cartella del progetto, copia il file di esempio, poi modifica i valori che ti servono:

```bash
cp .env.example .env
```

Con l'immagine Docker precompilata, la guida all'[installazione con Docker](../user/installation.md) scarica lo stesso esempio come `.env`.

- L'esempio raggruppa le opzioni in base a ciò che fanno. Un'opzione commentata, come `# SESSION_COOKIE_SECURE=auto`, mostra il suo valore predefinito: rimuovi il `#` solo per cambiare il valore.
- LibreFolio legge `.env` all'avvio: riavvialo dopo una modifica. Con Docker Compose, esegui `docker compose up -d`, perché `docker compose restart` mantiene i vecchi valori.
- I nomi distinguono maiuscole e minuscole. Nelle opzioni principali e nelle impostazioni di rischio riportate sotto, un valore del tipo sbagliato o fuori intervallo arresta il server all'avvio con un errore.

---

## ✏️ Opzioni principali {: #main-options }

| Variabile | Predefinito | Cosa fa |
| --- | --- | --- |
| `PORT` | `6040` | Porta del server web. Con Docker Compose, la porta aperta sull'host (il container resta sempre in ascolto su `6040`). |
| `TEST_PORT` | `6041` | Porta del server di test (`./dev.py server --test`). |
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Cartella del database, degli upload, dei report del broker e dei log; un percorso relativo parte dalla cartella del progetto. Docker la fissa a `/app/backend/data/prod-docker`: per spostare i dati sull'host, modifica il lato sinistro del volume `./LibreFolio-data` in `docker-compose.yml`. |
| `LOG_LEVEL` | `INFO` | Quanto registra il server nei log: `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR` o `CRITICAL`. Con `DEBUG` o `TRACE`, l'app web scrive nella console del browser anche ogni chiamata al server non riuscita, comprese quelle rifiutate (una risposta `4xx`); agli altri livelli, solo gli errori del server, le chiamate rimaste senza risposta e le risposte che non riesce a leggere. |
| `JWT_SECRET` | _non impostato_ | Chiave che firma le sessioni di accesso. Non impostata, vuota o composta solo da spazi: una nuova chiave a ogni avvio, quindi tutti devono accedere di nuovo dopo un riavvio. `JWT_SECRET_FILE` la legge invece da un file: vedi [Segreti](configuration_secrets.md#secrets). Vedi [Mantenere gli utenti connessi](index.md#session-persistence). |
| `SESSION_COOKIE_SECURE` | `auto` | Quando il cookie della sessione di accesso viene inviato solo tramite HTTPS: `auto` (se il browser usa HTTPS), `always` o `never`. Vedi [HTTPS e reverse proxy](#session-cookie-secure). |
| `LIBREFOLIO_CLIENT_IP_HEADER` | _non impostato_ | Dietro un reverse proxy, l'header in cui questo trasmette l'indirizzo del visitatore, come `Fly-Client-IP` su Fly.io: impostalo solo se ogni richiesta attraversa quel proxy. Vedi [L'indirizzo del visitatore](connection_proxy.md#client-address). |
| `PREVIEW_CACHE_MAX_MB` | `50` | Memoria, in MB, della cache delle anteprime delle immagini in ciascun processo del server. |
| `LIBREFOLIO_FRAME_PROTECTION` | `false` | Lascialo non impostato su un'installazione propria: le dashboard a un altro indirizzo, come i pannelli di Home Assistant, possono così mostrare LibreFolio in un frame. `true` consente solo alle pagine di LibreFolio di mostrarlo in un frame, aggiungendo a ogni risposta `X-Frame-Options: SAMEORIGIN` e `Content-Security-Policy: frame-ancestors 'self'`. Le tre regole `object-src 'none'; base-uri 'self'; form-action 'self'` non dipendono da questa opzione: le pagine di LibreFolio le includono sempre ([La Content-Security-Policy](configuration_security.md#csp)). Sono validi `true` o `false`; anche `1`/`0`, `yes`/`no` e `on`/`off`, senza distinzione tra maiuscole e minuscole; qualsiasi altro valore arresta il server all'avvio. Vedi [Protezione dei frame](configuration_security.md#frame-protection). |
| `LIBREFOLIO_CSP_REPORT_ONLY` | `false` | Lascialo non impostato su un'installazione propria. `true` aggiunge una seconda Content-Security-Policy più ampia alle pagine dell'app web, non alla documentazione o all'API, in modalità report-only: non blocca nulla e il browser elenca nella console per sviluppatori ciò che quella policy più ampia bloccherebbe, senza inviare segnalazioni da nessuna parte. La [Content-Security-Policy](configuration_security.md#csp) applicata è sempre attiva, con o senza questa opzione. Stessi valori di `LIBREFOLIO_FRAME_PROTECTION`. Vedi [La policy report-only](configuration_security.md#csp-report-only). |
| `LIBREFOLIO_API_DOCS` | `false` | Lascialo non impostato. `true` fornisce le pagine di documentazione dell'API, Swagger UI su `/api/v1/docs` e ReDoc su `/api/v1/redoc`, con lo schema dell'API su `/api/v1/openapi.json`. Se disattivata, rispondono `404`, in ogni profilo e anche con Docker: un'istanza in uso non pubblica alcuna mappa della propria API. Un browser che apre uno di questi indirizzi, o qualsiasi altro indirizzo sotto `/api/`, o una pagina di documentazione inesistente sotto `/mkdocs/`, viene portato all'app (`/`); un programma che chiama l'API riceve comunque `404` con `{"detail": "Not Found"}`. Nell'app web, una pagina inesistente ti riporta alla pagina da cui provenivi o alla Dashboard. È uno strumento per sviluppatori, quindi `./dev.py server --debug` la attiva, e anche le esecuzioni di test di LibreFolio la tengono attiva. Sono validi `true` o `false`; anche `1` e `0`. La policy delle pagine stesse è in [La Content-Security-Policy](configuration_security.md#csp). |
| `LIBREFOLIO_SUPPORT_URL` | _non impostato_ | Dove gli utenti dell'istanza chiedono aiuto, ad esempio per un asset che la ricerca non trova ([Segnalacelo](../user/assets/create-edit.md#let-us-know), sotto i risultati della ricerca): una pagina con `http://` o `https://`, oppure un indirizzo email come `mailto:help@example.org`. Con un indirizzo email, l'app di posta dell'utente apre un messaggio con i dettagli della ricerca; con una pagina, la pagina si apre in una nuova scheda e riceve la segnalazione nel proprio indirizzo, nei parametri di query `title` e `body`, come una issue GitHub precompilata, così che un modulo di supporto possa compilarsi da solo, e anche i dettagli vengono copiati, per incollarli lì. Non impostato: su un'installazione propria (il profilo `selfhosted`), si apre una nuova issue pubblica su GitHub di LibreFolio con i dettagli, perché l'utente la riveda prima di inviarla. Qualsiasi altro valore viene ignorato, come se non fosse impostato, e il server lo registra nei log una volta. Anche una pagina il cui indirizzo contiene un nome utente o una password vale come non impostata. L'indirizzo è pubblico: chiunque possa raggiungere il server può leggerlo su `/api/v1/system/instance`. |
| `LIBREFOLIO_TOS_URL` | _non impostato_ | I termini di servizio dell'istanza: una pagina con `http://` o `https://`. L'avviso legale che ogni utente vede, in Impostazioni › Informazioni, nella pagina di benvenuto, sotto la scheda presente in ogni pagina di accesso e in fondo alla barra laterale, rimanda ad essi con il link **Termini di servizio**, aperto in una nuova scheda. Non impostato: nessun link, solo l'avviso. A differenza di `LIBREFOLIO_SUPPORT_URL`, nessun `mailto:`. Un valore che LibreFolio non può usare, incluso un indirizzo con un nome utente o una password, non arresta il server: il link resta nascosto e nel log compare un errore (vedi sotto). L'indirizzo è pubblico: chiunque possa raggiungere il server può leggerlo su `/api/v1/system/instance`. |
| `LIBREFOLIO_PRIVACY_URL` | _non impostato_ | L'informativa sulla privacy dell'istanza, collegata come **Informativa sulla privacy** accanto ai termini di servizio: stesse regole di `LIBREFOLIO_TOS_URL`. |
| `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` | _non impostato_ | Lascialo non impostato. La dimensione massima di un archivio che un amministratore può caricare per verificarlo in vista di un ripristino, in megabyte; `0` significa nessun limite. Non impostato: nessun limite. Un valore che non è un numero intero non arresta il server: i caricamenti rispondono `503` e nel log compare un errore, già dall'avvio ([Controlli all'avvio](configuration_security.md#startup-checks)) e poi ogni volta che il limite viene letto. Letto solo dall'ambiente. Vedi [Il limite di caricamento di un ripristino](backup_restore.md#restore-upload-limit). |
| `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` | _non impostato_ | Lascialo non impostato. La dimensione massima a cui un archivio può essere decompresso durante la verifica per un ripristino, in megabyte, secondo le dimensioni dichiarate dal suo manifest; `0` significa nessun limite. Non impostato: nessun limite. Un valore impostato da te prevale sempre, `0` incluso, e anche `backup restore` da riga di comando lo rispetta. Un archivio oltre il limite viene rifiutato prima che qualsiasi cosa venga decompressa (`unpacked_too_large`). Un valore che non è un numero intero non arresta il server: i controlli di un ripristino rispondono `503` (`backup_restore_unavailable`), nel log compare un errore già dall'avvio ([Controlli all'avvio](configuration_security.md#startup-checks)) e poi a ogni controllo, e la scheda **Sicurezza** di Impostazioni › Amministrazione lo segnala (`backup.restore_limit`). Letto solo dall'ambiente. Vedi [Il limite di caricamento di un ripristino](backup_restore.md#restore-upload-limit). |
| `LIBREFOLIO_BACKUP_RECIPIENTS` | _non impostato_ | Una o due chiavi pubbliche age (`age1…`, come le stampano `backup keygen` o `age-keygen`), separate da virgole: due solo mentre si cambia una chiave. Non è un segreto. Se impostato, `backup create --sealed` crea un backup [sigillato](backup_sealed.md#sealed): un `.tar` che solo le chiavi private corrispondenti possono aprire, mai con la chiave dell'istanza. Un valore che LibreFolio non può usare (una chiave non `age1…`, più di due, la stessa due volte) non arresta il server: nel log compare un errore e la scheda **Sicurezza** di Impostazioni › Amministrazione lo segnala (`backup.recipients`). Letto solo dall'ambiente. |
| `LIBREFOLIO_STORAGE_LIMIT_MB` | _non impostato_ | Lascialo non impostato su un'installazione propria: imposti il limite nella barra dello spazio della pagina **File**. Lo spazio che l'istanza può occupare, in megabyte; `0` significa nessun limite. Se impostato, prevale sull'impostazione **Limite di spazio (MB)**, qualunque valore un amministratore abbia salvato prima, e la blocca: il campo nella barra dello spazio è disattivato (in grigio) e il salvataggio viene rifiutato. Non impostato: decide l'impostazione, `0` finché un amministratore non salva un altro valore. Un valore che non è un numero intero viene ignorato e vale l'impostazione. Oltre, LibreFolio rifiuta un file caricato, un report del broker, un backup avviato a mano e un ripristino che porterebbe i dati oltre, e non elimina nulla; poiché l'amministratore non può alzarlo da qui, il messaggio chiede di farlo a chi ospita l'istanza. Letto solo dall'ambiente. Vedi [La barra dello spazio](backup_restore.md#space-used). |
| `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS` | `60` | La prima pausa di un provider di prezzi che risponde «troppe richieste» (HTTP 429): nessuna richiesta lo raggiunge finché la pausa non termina, e ogni rifiuto consecutivo raddoppia la pausa successiva. Un numero intero di secondi da `0` a `86400`; `0` disattiva le pause, come prima della versione 1.3. Attiva per impostazione predefinita, per la decisione dello sviluppatore n. 34: un'eccezione alla regola secondo cui una nuova opzione lascia un'installazione com'era. Anche un valore che non può essere usato non arresta il server: nel log compare un errore e si applicano entrambi i valori predefiniti. Vedi [Pause dei provider](settings.md#provider-pauses). |
| `LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS` | `3600` | La pausa più lunga raggiunta dal raddoppio: un numero intero di secondi da `1` a `86400`, non inferiore alla prima pausa mentre le pause sono attive. Il `Retry-After` di un provider può comunque chiedere di più, fino a un giorno. Anche un valore che non può essere usato non arresta il server: nel log compare un errore e si applicano entrambi i valori predefiniti. Vedi [Pause dei provider](settings.md#provider-pauses). |
| `LIBREFOLIO_PROBE_RATE_LIMIT` | `30` | Quante volte al minuto un utente può testare le impostazioni di un provider di prezzi (**Verifica configurazione** nel modulo dell'asset; anche **Chiedi al provider** conta), con possibili chiamate al provider; superato il limite, il modulo indica all'utente quando riprovare. Un numero intero da `0` a `10000`; `0` disattiva il limite, solo per un'istanza di test (lo fa `./dev.py server --test`), e nel log compare un avviso a ogni avvio. Letto a ogni test: una modifica si applica senza riavvio. Un valore che non può essere usato non arresta il server: nel log compare un errore e si applica `30`. |
| `LIBREFOLIO_BRIM_PREWARM` | `false` (`true` in modalità test) | Opzionale. `true` rende pronti all'avvio i worker per l'importazione dei report dei broker, con i plugin di importazione caricati: la prima importazione da broker dopo un avvio è quindi circa 4 secondi più veloce, al costo di circa 80 MB di memoria occupata fin dall'avvio e di circa 1,4 secondi di CPU a ogni avvio. Disattivata per impostazione predefinita, per la decisione N56: su una macchina cloud di piccole dimensioni, quella memoria e quella CPU costano più dei secondi che fanno risparmiare. Sono validi `true` o `false`; anche `1`/`0`, `yes`/`no` e `on`/`off`, senza distinzione tra maiuscole e minuscole. Qualsiasi altro valore non arresta il server, a differenza delle opzioni principali: nel log compare un avviso all'avvio e l'opzione resta disattivata. Vedi [Architettura BRIM → Precaricamento e riscaldamento](../developer/backend/brim/architecture.md#parse-pool-warm-up). |
| `LIBREFOLIO_SMTP_HOST` | _non impostato_: email disattivata | Opzionale. Il server SMTP che invia le email di LibreFolio, come `smtp.example.com`. Vedi [Email](email.md#variables). |
| `LIBREFOLIO_SMTP_TLS` | `starttls` | Come viene cifrata la connessione al server SMTP: `starttls`, `tls` o `none`. Vedi [Modalità di cifratura](email.md#encryption-modes). |
| `LIBREFOLIO_SMTP_PORT` | `587` con `starttls`, `465` con `tls`, `25` con `none` | La porta del server SMTP, solo quando non è quella consueta della sua modalità di cifratura. Vedi [Email](email.md#variables). |
| `LIBREFOLIO_SMTP_USER` | _non impostato_: nessun login | L'utente per l'accesso al server SMTP, impostato insieme a `LIBREFOLIO_SMTP_PASSWORD` ([Segreti](configuration_secrets.md#secrets)). Vedi [Email](email.md#variables). |
| `LIBREFOLIO_SMTP_FROM` | _non impostato_ | Il mittente delle email, obbligatorio non appena viene impostato un server. Vedi [Email](email.md#variables). |
| `LIBREFOLIO_SMTP_REPLY_TO` | _non impostato_: le risposte vanno al mittente | Dove vanno le risposte alle email di LibreFolio. Vedi [Email](email.md#variables). |
| `LIBREFOLIO_SMTP_MAX_PER_HOUR` | `50` | Quante email l'istanza può inviare in un'ora, per processo del server. Vedi [Email](email.md#variables). |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` | `20` | Quante email di registrazione un indirizzo client può attivare in un'ora, per processo del server: un numero intero, almeno 1. Un unico conteggio per le registrazioni, **Invia di nuovo il link** e **Password dimenticata?**. Superato il limite, un nuovo account viene creato e resta in attesa, e la sua email viene trattenuta. Vedi [Limiti sulle email di attivazione e reimpostazione della password](email_flows.md#activation-limits). |

Un valore che LibreFolio non può usare in `LIBREFOLIO_TOS_URL` o `LIBREFOLIO_PRIVACY_URL` non arresta mai il server: quel link resta nascosto e l'avviso legale viene mostrato senza di esso. La prima volta che ciascun processo del server risponde a `/api/v1/system/instance`, che l'app legge non appena si apre, nel log compare un errore, `Invalid instance link`, con la variabile e il suo valore in `problem` (un valore che contiene una `@` non viene mostrato: potrebbe contenere un nome utente o una password) e, in `consequence`, ciò che costa finché non lo correggi, ad esempio `the terms of service link stays hidden until it is fixed: the legal notice shows without it`. Correggi il valore, poi riavvia. Anche una variabile `LIBREFOLIO_SUPPORT_URL` che non può essere usata registra lo stesso errore, con il proprio `consequence`.

I file `.env` più vecchi possono ancora contenere `PORTFOLIO_BASE_CURRENCY`: LibreFolio lo ignora e i nuovi utenti partono dalla **Valuta predefinita** in [Impostazioni globali](settings.md).

??? info "🔒 HTTPS e reverse proxy — il cookie di sessione"

    `SESSION_COOKIE_SECURE` decide quando il cookie che mantiene gli utenti connessi è `Secure`: il browser lo invia quindi solo tramite HTTPS, così la sessione non viaggia mai su una connessione non cifrata. Maiuscole/minuscole e spazi attorno al valore non contano; qualsiasi altro valore arresta il server all'avvio con un errore.
    {: #session-cookie-secure }

    - **`auto`** (predefinito): `Secure` quando il browser ha raggiunto LibreFolio tramite HTTPS. LibreFolio stesso serve HTTP in chiaro, quindi HTTPS proviene da un reverse proxy davanti a esso, che lo dichiara con l'header `X-Forwarded-Proto: https`; conta solo il suo primo valore. Non c'è alcun elenco di proxy attendibili da configurare: l'header può solo attivare `Secure`, mai disattivarlo. Su HTTP in chiaro, come `http://localhost:6040`, un IP della LAN o l'IP Tailscale dei Livelli 1 e 2 in [Esposizione sicura](service_exposure.md), il cookie non è `Secure`, quindi l'accesso continua a funzionare.
    - **`always`**: sempre `Secure`, per un'installazione raggiunta solo tramite HTTPS. Su HTTP in chiaro il browser scarta il cookie, quindi l'accesso non rimane attivo: la pagina successiva riporta l'utente alla pagina di login.
    - **`never`**: mai `Secure`. È la via d'uscita quando un proxy invia `X-Forwarded-Proto: https` a un browser che in realtà usa HTTP in chiaro, come Nginx con un `proxy_set_header X-Forwarded-Proto https;` codificato a mano in un blocco `server` in HTTP in chiaro: con `auto`, quel browser verrebbe riportato alla pagina di login dopo ogni accesso. Correggere il proxy è meglio (`$scheme` invece di `https`); `never` è il fallback.

    Dietro un reverse proxy HTTPS, `auto` si basa sul suo header `X-Forwarded-Proto`:

    - **Tailscale Serve e Funnel** (Livelli 3 e 4 in [Esposizione sicura](service_exposure.md)), **Caddy** e **Traefik** lo inviano da soli: nulla da configurare.
    - **Nginx** non lo fa: aggiungi `proxy_set_header X-Forwarded-Proto $scheme;` al blocco `location` che fa da proxy per LibreFolio.
    - **Qualsiasi altro proxy**: fallo inviare l'header oppure, se LibreFolio è raggiungibile solo tramite esso, imposta `SESSION_COOKIE_SECURE=always`.

    Per verificare nel browser se il cookie di sessione è contrassegnato come `Secure`, vedi [Verifica della sicurezza della connessione](connection_checks.md#session-cookie).

??? info "🧮 Worker del motore di rischio — regolazione avanzata"

    Le simulazioni di rischio e le ottimizzazioni di portafoglio vengono eseguite in processi worker separati, avviati al primo utilizzo. I valori predefiniti sono adatti alla maggior parte delle installazioni: aggiungi una variabile a `.env` solo per modificarli.

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
| `LIBREFOLIO_TEST_MODE` | — | `1`, `true` o `yes`, senza distinzione tra maiuscole e minuscole, passa alla cartella dei dati di test. Solo per le esecuzioni di test di LibreFolio: `./dev.py server --test` e i runner di test la impostano, mentre `./dev.py server` la disattiva. Un server avviato senza `./dev.py`, ad esempio con `uvicorn` direttamente o da un'unità di servizio, la prende dal proprio ambiente. Su un'istanza in uso, al di fuori del runner di test, i [controlli all'avvio](configuration_security.md#startup-checks) la segnalano come errore. |
| `LIBREFOLIO_TEST_DATA_DIR` | `./backend/data/test` | Cartella dei dati di test; non può sovrapporsi a quella di produzione. |

---

## 🔝 Quale valore prevale

Dalla priorità più alta alla più bassa:

1. Le opzioni `--host`, `--port` e `--data-dir` di `./dev.py server`.
2. Le variabili impostate nella shell.
3. Il file `.env`.
4. I valori predefiniti elencati in questa pagina.

Con Docker Compose, il blocco `environment:` di `docker-compose.yml` prevale su `.env`: fissa `HOST`, `LIBREFOLIO_DATA_DIR` e, all'interno del container, `PORT=6040` (il tuo `PORT` continua a impostare la porta sull'host). Vedi [Docker avanzato](docker_advanced.md#resolution-priority).

Per un'[impostazione di un plugin](configuration_secrets.md#plugin-settings), dalla priorità più alta alla più bassa: la sua variabile (`LIBREFOLIO_PLUGIN_…` prima del vecchio nome usato dal plugin per essa, e ciascuna prima della rispettiva forma `_FILE`), il valore salvato dentro LibreFolio, poi il valore predefinito del plugin. Una variabile con un valore errato prevale comunque e lascia il plugin non configurato. Un'impostazione personale non ha variabile: il valore salvato dall'utente, poi il valore predefinito.

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
