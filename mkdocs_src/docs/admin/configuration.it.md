# 📝 Configurazione

Le opzioni di avvio risiedono in un file `.env`: porte, cartella dei dati, registrazione dei log, sessioni di accesso e alcune funzionalità opzionali. Si trova nella radice del progetto, oppure accanto a `docker-compose.yml` con Docker. Le opzioni che modifichi dall'interno dell'app sono invece le [Impostazioni globali](settings.md).

---

## 🔧 Creare il file `.env`

Nella cartella del progetto, copia il file di esempio, poi modifica i valori che ti servono:

```bash
cp .env.example .env
```

Con l'immagine Docker precompilata, la guida [Installazione Docker](../user/installation.md) scarica lo stesso esempio come `.env`.

- LibreFolio legge `.env` all'avvio: riavvialo dopo una modifica. Con Docker Compose, esegui `docker compose up -d`, perché `docker compose restart` mantiene i vecchi valori.
- I nomi distinguono maiuscole e minuscole. Nelle opzioni principali e nelle impostazioni di rischio riportate sotto, un valore del tipo sbagliato o fuori intervallo arresta il server all'avvio con un errore.

---

## ✏️ Opzioni principali

| Variabile | Predefinito | Cosa fa |
| --- | --- | --- |
| `PORT` | `6040` | Porta del server web. Con Docker Compose, la porta aperta sull'host (il container resta sempre in ascolto su `6040`). |
| `TEST_PORT` | `6041` | Porta del server di test (`./dev.py server --test`). |
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Cartella del database, dei caricamenti, dei report del broker e dei log; un percorso relativo parte dalla cartella del progetto. Docker la fissa a `/app/backend/data/prod-docker`: per spostare i dati sull'host, modifica il lato sinistro del volume `./LibreFolio-data` in `docker-compose.yml`. |
| `LOG_LEVEL` | `INFO` | Quanto registra il server: `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR` o `CRITICAL`. |
| `JWT_SECRET` | _non impostato_ | Chiave che firma le sessioni di accesso. Non impostata: una nuova chiave a ogni avvio, quindi tutti devono accedere di nuovo dopo un riavvio. Vedi [Mantieni gli utenti connessi](index.md#session-persistence). |
| `SESSION_COOKIE_SECURE` | `auto` | Quando il cookie di sessione di accesso viene inviato solo via HTTPS: `auto` (se il browser usa HTTPS), `always` o `never`. Vedi [HTTPS e reverse proxy](#session-cookie-secure). |
| `PREVIEW_CACHE_MAX_MB` | `50` | Memoria, in MB, della cache delle anteprime immagini in ciascun processo del server. |

I file `.env` più vecchi possono ancora contenere `PORTFOLIO_BASE_CURRENCY`: LibreFolio la ignora, e i nuovi utenti partono dalla **Valuta predefinita** in [Impostazioni globali](settings.md).

??? info "🔒 HTTPS e reverse proxy — il cookie di sessione"

    `SESSION_COOKIE_SECURE` decide quando il cookie che mantiene gli utenti connessi è `Secure`: il browser lo invia quindi solo via HTTPS, così la sessione non viaggia mai su una connessione non cifrata. Maiuscole/minuscole e spazi attorno al valore non hanno importanza; qualsiasi altro valore arresta il server all'avvio con un errore.
    {: #session-cookie-secure }

    - **`auto`** (predefinito): `Secure` quando il browser ha raggiunto LibreFolio via HTTPS. LibreFolio stesso serve HTTP semplice, quindi HTTPS proviene da un reverse proxy davanti a esso, che lo segnala con l'header `X-Forwarded-Proto: https`; conta solo il suo primo valore. Non c'è un elenco di proxy attendibili da configurare: l'header può solo attivare `Secure`, mai disattivarlo. Su HTTP semplice, come `http://localhost:6040`, un IP LAN o l'IP Tailscale dei livelli 1 e 2 in [Esposizione sicura](service_exposure.md), il cookie non è `Secure`, quindi l'accesso continua a funzionare.
    - **`always`**: sempre `Secure`, per un'installazione raggiunta solo via HTTPS. Su HTTP semplice il browser scarta il cookie, quindi l'accesso non persiste: la pagina successiva riporta l'utente alla pagina di login.
    - **`never`**: mai `Secure`. È la via d'uscita quando un proxy invia `X-Forwarded-Proto: https` a un browser che in realtà usa HTTP semplice, come Nginx con un `proxy_set_header X-Forwarded-Proto https;` codificato in modo fisso in un blocco `server` in HTTP semplice: in `auto`, quel browser verrebbe riportato alla pagina di login dopo ogni accesso. Correggere il proxy è meglio (`$scheme` invece di `https`); `never` è il fallback.

    Dietro un reverse proxy HTTPS, `auto` si affida al suo header `X-Forwarded-Proto`:

    - **Tailscale Serve e Funnel** (livelli 3 e 4 in [Esposizione sicura](service_exposure.md)), **Caddy** e **Traefik** lo inviano da soli: nulla da configurare.
    - **Nginx** no: aggiungi `proxy_set_header X-Forwarded-Proto $scheme;` alla `location` che fa da proxy a LibreFolio.
    - **Qualsiasi altro proxy**: fagli inviare l'header oppure, se LibreFolio è raggiungibile solo attraverso di esso, imposta `SESSION_COOKIE_SECURE=always`.

??? info "🧮 Worker del motore di rischio — ottimizzazione avanzata"

    Le simulazioni di rischio e le ottimizzazioni di portafoglio vengono eseguite in processi worker separati, avviati al primo utilizzo. I valori predefiniti sono adatti alla maggior parte delle installazioni: aggiungi una variabile a `.env` solo per modificarli.

    | Variabile | Predefinito | Cosa fa |
    | --- | --- | --- |
    | `RISK_SIMULATION_WORKERS`, `RISK_OPTIMIZATION_WORKERS` | `1` (1–8) | Processi worker per tipo di attività: più processi eseguono più attività contemporaneamente. |
    | `RISK_SIMULATION_QUEUE_CAPACITY`, `RISK_OPTIMIZATION_QUEUE_CAPACITY` | `2` (0–64) | Attività che possono attendere un worker; oltre tale limite, le nuove richieste vengono rifiutate. |
    | `RISK_SIMULATION_TIMEOUT_SECONDS`, `RISK_OPTIMIZATION_TIMEOUT_SECONDS` | `120` / `60` | Limite di tempo di un'attività, in secondi. |
    | `RISK_SIMULATION_IDLE_TIMEOUT_SECONDS`, `RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS` | `600` | I worker inattivi si fermano dopo questo numero di secondi e si riavviano con l'attività successiva; `0` li mantiene in esecuzione. |

---

## 💻 Parametri impostati dagli strumenti

`./dev.py` e Docker Compose li impostano per te: modificali solo se sai perché.

| Variabile | Predefinito | Cosa fa |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Indirizzo su cui resta in ascolto `./dev.py server`; `127.0.0.1` accetta solo connessioni locali. Docker Compose usa sempre `0.0.0.0`. |
| `LIBREFOLIO_LOG_LEVEL` | — | Sostituisce `LOG_LEVEL` quando impostato; `./dev.py server --debug` lo imposta a `DEBUG`. |
| `LIBREFOLIO_TEST_MODE` | — | `1`, `true` o `yes` passa alla cartella dati di test. Impostato da `./dev.py server --test` e dai runner di test. |
| `LIBREFOLIO_TEST_DATA_DIR` | `./backend/data/test` | Cartella dei dati di test; non può sovrapporsi a quella di produzione. |

---

## 🔎 Opzionale: ricerca web per nuovi asset

Quando crei un asset, anche dalla procedura guidata di importazione del broker, e la ricerca del provider stesso non trova nulla, LibreFolio può trovare la pagina dell'asset con una ricerca web tramite la libreria [`ddgs`](https://pypi.org/project/ddgs/). È attiva per impostazione predefinita e non viene mai usata per gli aggiornamenti dei prezzi. Tutte queste variabili sono opzionali: decommenta una riga di `.env.example` per modificarne una.

| Variabile | Predefinito | Cosa fa |
| --- | --- | --- |
| `LIBREFOLIO_WEB_LINK_FINDER_ENABLED` | `1` | `0` disattiva la ricerca web; la ricerca dei provider stessi continua a funzionare. |
| `LIBREFOLIO_WEB_LINK_FINDER_ENGINE` | `ddgs` | `ddgs` non richiede configurazione. `apikey` è riservata a un servizio di ricerca a pagamento e non restituisce ancora risultati. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_REGION` | `wt-wt` | Regione di ricerca. `wt-wt` (mondiale) evita che i siti nazionali come Borsa Italiana vengano penalizzati. Esempi: `it-it`, `us-en`. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND` | `auto` | Motori che `ddgs` interroga: `auto` li ruota per la copertura più ampia; una lista come `google,bing,duckduckgo` fornisce risultati più costanti. |
| `LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT` | `6` | Limite di tempo per una ricerca, in secondi. |
| `LIBREFOLIO_WEB_LINK_FINDER_MAX` | `5` | Numero massimo di link restituiti da una ricerca. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | _vuota_ | Chiave per il motore `apikey`. |

??? tip "🔁 I risultati cambiano tra un tentativo e l'altro — quando un asset noto a volte non viene trovato"

    Con `auto`, ogni ricerca può raggiungere motori diversi, quindi la stessa query può andare meglio o peggio da un tentativo all'altro. Riprova una volta oppure imposta `LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND=google,bing,duckduckgo`.

---

## 🔝 Quale valore prevale

Dalla priorità più alta alla più bassa:

1. Le opzioni `--host`, `--port` e `--data-dir` di `./dev.py server`.
2. Le variabili impostate nella shell.
3. Il file `.env`.
4. I valori predefiniti elencati in questa pagina.

Con Docker Compose, il blocco `environment:` di `docker-compose.yml` prevale su `.env`: fissa `HOST` e `LIBREFOLIO_DATA_DIR`. Vedi [Docker avanzato](docker_advanced.md#resolution-priority).

---

## 📂 Dove vanno i dati

- **Produzione**: `backend/data/prod/`, oppure `LIBREFOLIO_DATA_DIR`. Contiene il database (`sqlite/app.db`), `custom-uploads/`, `broker_reports/` e `logs/`.
- **Test**: `backend/data/test/`, oppure `LIBREFOLIO_TEST_DATA_DIR`. Stessa struttura, tenuta separata.

[Struttura del filesystem](filesystem.md) descrive in dettaglio ogni cartella e come eseguirne il backup.

---

## 🔗 Correlati

- ⚙️ **[Impostazioni globali](settings.md)** — Opzioni modificate dall'interno dell'app
- 🐳 **[Docker avanzato](docker_advanced.md)** — file Compose, volumi, ID utente e di gruppo
- 🧑‍💻 Per gli sviluppatori: **[Sistema delle impostazioni](../developer/architecture/settings.md)** — Come vengono caricati questi valori
