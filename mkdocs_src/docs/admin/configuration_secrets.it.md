# 🔐 Configurazione: Segreti e impostazioni dei plugin

Questa pagina illustra cosa deve restare privato in un'installazione di LibreFolio: le opzioni che sono **segreti**
(chiavi, password e token), che possono anche essere lette da file come i segreti Docker, la
**chiave dell'istanza** che protegge ciò che LibreFolio memorizza, e le **impostazioni dei plugin**, comprese le chiavi API.

Non conosci il file `.env`? Come crearlo, le opzioni principali e quale valore prevale sono in
[Configurazione](configuration.md); questa pagina approfondisce i segreti.

---

## 🔐 Segreti {: #secrets }

Queste opzioni sono segreti: trattale con la stessa riservatezza del database. Ognuna può essere scritta in `.env` o
letta da un file.

| Segreto | Da un file | Che cos'è |
| --- | --- | --- |
| `JWT_SECRET` | `JWT_SECRET_FILE` | La chiave che firma le sessioni di accesso, nelle [opzioni principali](configuration.md). |
| `LIBREFOLIO_INSTANCE_KEY` | `LIBREFOLIO_INSTANCE_KEY_FILE` | La [chiave dell'istanza](#instance-key). Se non impostata: LibreFolio ne crea una nella directory dei dati. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` | La chiave di un servizio di ricerca a pagamento, per il motore `apikey` della [ricerca web](configuration_accounts.md#optional-web-search-for-new-assets). A differenza delle prime due, un file che non riesce a fornirla non arresta il server: disattiva soltanto la ricerca web. |
| `LIBREFOLIO_SMTP_PASSWORD` | `LIBREFOLIO_SMTP_PASSWORD_FILE` | La password del server SMTP che invia le email di LibreFolio: vedi [Email](email.md). Come per la chiave di ricerca web, un file che non riesce a fornirla non arresta il server: disattiva soltanto l'email. |

Un plugin può avere segreti propri, come la chiave API di una fonte dati a pagamento: vedi
[Impostazioni dei plugin](#plugin-settings).

### 📄 Segreti nei file {: #secret-files }

Aggiungi `_FILE` al nome di un segreto e fornisci il percorso di un file che lo contiene. È così che Docker e
Kubernetes passano i loro segreti, ad esempio `/run/secrets/jwt_secret`: il segreto resta fuori da `.env`
e fuori dall'ambiente del container.

- Il segreto è il testo del file, senza le interruzioni di riga finali e senza il byte order mark che alcuni editor di Windows
  inseriscono all'inizio. Qualsiasi altro spazio conta, anche all'inizio e alla fine.
- Un percorso relativo parte dalla cartella del progetto.
- Un segreto o la sua variabile `_FILE` che siano vuoti o contengano solo spazi contano come non impostati: uno spazio
  accidentale non viene mai usato come chiave.
- Imposta uno dei due. Quando sono impostati entrambi, vince la variabile stessa, il file viene ignorato e il log
  di avvio contiene un [avviso](configuration_security.md#startup-checks).
- Per `JWT_SECRET_FILE`, `LIBREFOLIO_INSTANCE_KEY_FILE` e `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE`,
  un file che manca, non può essere letto, è vuoto o in bianco (solo spazi e interruzioni di riga), non è testo
  UTF-8 o è più grande di 64 KiB arresta il server all'avvio. L'errore indica il nome della variabile e
  il percorso, mai il segreto.
- `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` viene letto solo quando una ricerca usa il motore `apikey`. Un
  file che non riesce a fornire la chiave non arresta il server: la ricerca prosegue senza la ricerca web,
  con un avviso nel log (`web_link_finder: …; disabling`), e la ricerca propria dei provider continua a
  funzionare.
- `LIBREFOLIO_SMTP_PASSWORD_FILE` viene letto solo quando `LIBREFOLIO_SMTP_HOST` è impostato. Come per il file della chiave di ricerca web, un file che non riesce a fornire la password non arresta il server: l'email resta disattivata, con un
  errore nel log (`Email configuration cannot be used: email stays off`).
- LibreFolio legge queste variabili dal proprio ambiente: `./dev.py` e Docker Compose
  (`env_file: .env`) vi inseriscono i valori di `.env`, quindi `.env` funziona con entrambi.

??? example "🐳 Un segreto Docker con Docker Compose"

    1. Salva una nuova chiave in un file accanto a `docker-compose.yml`:

        ```bash
        python3 -c "import secrets; print(secrets.token_urlsafe(64))" > jwt_secret.txt
        ```

    2. Aggiungi le righe contrassegnate a `docker-compose.yml` e lascia il resto del servizio com'è:

        ```yaml
        services:
          librefolio:
            environment:
              - LIBREFOLIO_DATA_DIR=/app/backend/data/prod-docker
              - HOST=0.0.0.0
              - JWT_SECRET_FILE=/run/secrets/jwt_secret  # added
            secrets:                                     # added
              - jwt_secret                               # added
        secrets:                                         # added
          jwt_secret:                                    # added
            file: ./jwt_secret.txt                       # added
        ```

    3. Se `.env` assegna un valore a `JWT_SECRET`, rimuovi quella riga: vincerebbe sul file. Una riga
       `JWT_SECRET=` vuota non fa danni. Poi esegui `docker compose up -d`.

    Compose monta il file nel container così com'è sull'host, con il proprietario e i permessi che ha lì.
    All'interno del container, LibreFolio viene eseguito come utente dell'immagine, `1000:1000` per quella ufficiale (vedi
    [Docker avanzato](docker_advanced.md)), e quell'utente deve poter leggere il file. Con l'immagine
    ufficiale, ad esempio: `sudo chown 1000:1000 jwt_secret.txt`, poi
    `sudo chmod 600 jwt_secret.txt`. Altrimenti il server si arresta all'avvio e l'errore riporta `cannot be read` per il file.

    I file indicati da `LIBREFOLIO_INSTANCE_KEY_FILE`, `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` e
    `LIBREFOLIO_SMTP_PASSWORD_FILE` vengono montati allo stesso modo; ciò che ciascuna variabile fa quando il suo file
    non riesce a fornire il segreto è in [Segreti nei file](#secret-files).

### 🗝️ La chiave dell'istanza {: #instance-key }

La chiave dell'istanza è un unico segreto per installazione: LibreFolio ne deriva le proprie chiavi di crittografia.
Non c'è nulla da configurare. LibreFolio usa la prima chiave che trova:

1. `LIBREFOLIO_INSTANCE_KEY`, la chiave stessa;
2. `LIBREFOLIO_INSTANCE_KEY_FILE`, un file che la contiene, come un segreto Docker;
3. `secrets/instance.key` nella directory dei dati, che LibreFolio crea la prima volta che ha bisogno della
   chiave: 43 caratteri casuali, in una cartella e in un file che solo l'utente che esegue LibreFolio può aprire
   (`0700` e `0600`).

Una chiave scelta da te deve essere casuale e lunga almeno 32 caratteri, come l'output di
`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`. Non usare mai una passphrase: le chiavi
che LibreFolio ne deriva sono robuste solo quanto la passphrase.

In una distribuzione cloud, la chiave può provenire dall'ambiente o da un segreto Docker invece che
dalla directory dei dati. Assegna a ogni istanza una chiave propria: non condividere mai una chiave tra più istanze.

!!! warning "🔑 Non cambiare né eliminare mai la chiave una volta in uso"

    Solo la stessa chiave può rileggere ciò che è stato crittografato con essa.

    - Esegui il backup di `secrets/` insieme al resto della directory dei dati e conserva le copie private quanto il
      database: vedi [Backup](filesystem.md#backup).
    - Una volta che la chiave esiste, LibreFolio non può distinguere un `instance.key` perduto da un primo utilizzo: crea
      una nuova chiave, e ciò che la vecchia aveva crittografato non può più essere letto. Quando ripristini i dati, rimetti
      `secrets/` insieme a essi prima di avviare di nuovo LibreFolio. Non avviare mai LibreFolio su dati ripristinati
      senza il relativo `secrets/`. Se LibreFolio ha già creato una nuova chiave, arrestalo, metti la tua copia di
      `instance.key` al posto di quella nuova e avvialo di nuovo, prima che qualcuno inserisca di nuovo un
      [segreto di plugin](#plugin-secrets): un segreto inserito con la nuova chiave diventerebbe
      illeggibile una volta ripristinata la vecchia chiave.
    - Se `instance.key` è presente ma danneggiato o irraggiungibile, LibreFolio registra un errore e non
      lo sostituisce mai: vedi cosa fare in [Controlli all'avvio](configuration_security.md#startup-checks).
    - Impostare `LIBREFOLIO_INSTANCE_KEY` dove `secrets/instance.key` esiste già cambia la chiave. Per
      spostare la chiave nell'ambiente o in un segreto Docker, usa il contenuto di `secrets/instance.key`
      come valore.

### 🔏 Il controllo della chiave {: #instance-key-check }

LibreFolio conserva, accanto alla chiave, un **valore di controllo**: una breve impronta della chiave nel file
`secrets/instance.key.check` della directory dei dati (cartella `0700`, file `0600`). Non è la chiave e da esso non
si può risalire alla chiave. A ogni avvio, LibreFolio confronta l'impronta della
chiave che ha ora con quella che ha memorizzato. Differiscono quando LibreFolio si avvia con **una chiave diversa da quella con cui
sono stati scritti i dati**: una macchina che ha ricevuto la chiave sbagliata, un file chiave sostituito con uno nuovo.

- **Il primo avvio** scrive il file. Se esistono già segreti di plugin salvati e la chiave attuale non ne legge
  nessuno, LibreFolio non lo scrive: scambierebbe la chiave sbagliata per quella giusta. Il controllo
  allora indica che la chiave non corrisponde finché non rimetti quella giusta.
- **Con una chiave che non corrisponde**, il log presenta un errore all'avvio, la
  scheda Sicurezza di Impostazioni › Amministrazione lo indica (il controllo è `platform.instance_key_check`). **L'istanza continua a funzionare**: i tuoi dati non dipendono da questa
  chiave, solo i segreti di plugin salvati lo fanno.
- **La soluzione è la chiave giusta.** Rimettila, con `LIBREFOLIO_INSTANCE_KEY`, il suo `_FILE` o il
  `secrets/instance.key` dei dati, e avvia di nuovo LibreFolio: la risposta successiva è `ok`, senza altro da fare.
- **Per cambiare davvero la chiave**, ad esempio quando decidi che i vecchi segreti sono persi e i segreti dei plugin
  vengono inseriti di nuovo, imposta `LIBREFOLIO_INSTANCE_KEY_ACCEPT=1` per **un solo avvio**. Quell'avvio sostituisce il valore di controllo
  memorizzato con quello della chiave che ha, e registra un avviso. **Poi rimuovi la variabile e avvia di nuovo**: finché è
  impostata, ogni avvio accetta qualunque chiave abbia, e la protezione non fa nulla (l'avviso viene registrato a ogni avvio, come promemoria).
  I valori sono `1` o `0`, `true` o `false`, `yes` o `no`, `on` o `off`; qualsiasi altro valore arresta l'avvio, indicando il nome della variabile.

!!! note "📏 Cosa il controllo non può vedere"

    Senza un valore di controllo memorizzato e senza alcun segreto di plugin salvato, non c'è nulla da confrontare, quindi
    la risposta è `ok`: il primo avvio di un'istanza la cui chiave era già sbagliata non può essere riconosciuto. Da
    quel momento in poi, il valore memorizzato la protegge. Se i dati tornano senza la loro cartella `secrets/`, il valore
    viene scritto di nuovo all'avvio successivo, e sono i segreti dei plugin a decidere finché manca. Un valore di controllo che non può essere letto
    (un permesso, un file danneggiato) non impedisce mai un backup: la risposta è `ok` e il log contiene un avviso, una volta sola.

---

## 🧩 Impostazioni dei plugin {: #plugin-settings }

Un plugin può richiedere impostazioni proprie: la chiave API di una fonte dati a pagamento, una regione, una
preferenza. Dei plugin forniti con LibreFolio, due ne richiedono una, una preferenza di ricerca personale
ciascuno: justETF e Borsa Italiana. Nessuno richiede un'impostazione a livello di istanza; un plugin che aggiungi potrebbe farlo. Un'impostazione è di due tipi:

- **A livello di istanza**: un valore per l'intera istanza, che solo un amministratore può salvare. Ogni
  utente può leggere un valore in chiaro; di un valore segreto, come una chiave API, può sapere soltanto se è impostato.
- **Personale**: un valore proprio di ogni utente, che solo quell'utente può salvare e leggere. Gli amministratori non
  lo vedono mai.

Le impostazioni personali e quelle a livello di istanza si modificano in **Impostazioni › Plugin**, una scheda che ogni utente ha:
lì ogni utente modifica quelle personali, e gli amministratori modificano anche quelle a livello di istanza, che
gli altri utenti vedono in sola lettura. Nella finestra di dialogo dell'asset, **Configura**, accanto al provider di prezzi
scelto, apre lo stesso modulo solo per quel provider. Cosa mostra la scheda, impostazione per impostazione:
[Impostazioni dei plugin](../user/settings/plugins.md) nel manuale utente.

Un'impostazione a livello di istanza può anche essere fornita da una variabile d'ambiente, in `.env` o nell'ambiente del
container come le altre opzioni; una personale no. I plugin che hanno impostazioni, con le chiavi delle loro impostazioni, sono elencati da `GET /api/v1/settings/plugins` a qualsiasi
utente autenticato.

### 🏷️ Le variabili {: #plugin-variables }

LibreFolio costruisce il nome della variabile dal tipo di plugin, dal codice del plugin e dalla chiave
dell'impostazione:

```text
LIBREFOLIO_PLUGIN_<KIND>_<PLUGIN CODE>_<SETTING KEY>
```

- `<KIND>` è `ASSET` per un provider di prezzi e `FX` per un provider di tassi di cambio.
- L'intero nome è in maiuscolo, e ogni carattere diverso da una lettera o da una cifra diventa `_`:
  l'impostazione `api_key` del provider di prezzi `my_provider` è
  `LIBREFOLIO_PLUGIN_ASSET_MY_PROVIDER_API_KEY`.
- Per un'impostazione segreta, un plugin può anche accettare la variabile che leggeva prima di avere impostazioni, così
  che un'installazione esistente continui a funzionare. Quando sono impostate entrambe, vince il nome qui sopra.
- Ogni variabile ha anche una forma `_FILE`, il percorso di un file che contiene il valore, come un segreto
  Docker. Il file viene letto come in [Segreti nei file](#secret-files), ma uno che non può essere letto non
  arresta mai il server: vedi sotto.

### 🔒 Una variabile blocca l'impostazione {: #plugin-variable-lock }

Finché la sua variabile è impostata, un'impostazione prende il valore da lì, e nessuno può cambiarla
dall'interno di LibreFolio: un salvataggio viene rifiutato (`LOCKED_BY_ENV`), e un valore salvato in precedenza viene ignorato finché
non rimuovi la variabile e riavvii. **Impostazioni › Plugin** mostra l'impostazione in sola lettura, un segreto
solo come *Impostato*: *Impostato dalla variabile del server* e il nome della variabile per gli amministratori, *Impostato dal
server* per gli altri utenti.

- Un valore sbagliato, uno che l'impostazione non accetta, o un `_FILE` che non può essere letto, bloccano comunque
  l'impostazione, e il plugin risulta quindi non configurato: LibreFolio rifiuta ogni richiesta nei suoi confronti, anche quando
  l'impostazione è facoltativa, finché non correggi la variabile. Non ripiega mai sul valore salvato né su
  quello predefinito del plugin. Il log spiega il perché, con un avviso una volta per processo del server:
  `Plugin setting variable invalid: the plugin is not configured until it is fixed`, con la
  variabile e il motivo, mai il valore. In **Impostazioni › Plugin** il badge del plugin riporta
  **Da configurare**, e l'impostazione dice che la sua variabile non è valida. Correggi il valore, poi riavvia.

### 🔐 Segreti salvati e la chiave dell'istanza {: #plugin-secrets }

Un'impostazione salvata dentro LibreFolio è conservata nel database. Una segreta viene prima crittografata
(AES-256-GCM) con una chiave derivata dalla [chiave dell'istanza](#instance-key), e non viene mai più mostrata,
neppure a chi l'ha salvata: LibreFolio dice solo se è impostata (in **Impostazioni › Plugin**,
*Impostato il* e la data in cui è stata salvata). Un valore fornito da una variabile, segreto o no, non viene mai salvato nel
database.

Se la chiave dell'istanza cambia, i segreti salvati non possono più essere letti. LibreFolio li conserva e
li segnala come illeggibili, e non usa mai un valore sbagliato. La scheda lo dice sotto ciascuno:
*Salvato, ma la chiave di questa istanza non può leggerlo. Se un amministratore può rimettere la vecchia chiave,
quella ha la priorità; altrimenti inseriscilo di nuovo.* Se hai ancora la vecchia
chiave, rimettila prima che qualcuno li inserisca di nuovo: un segreto inserito con la nuova chiave diventerebbe
illeggibile una volta ripristinata la vecchia chiave. Per portarli in un'altra installazione, che conserva una propria
chiave, ripristina lì un backup con la vecchia chiave: `backup restore` con `--instance-key-file`
li ricrittografa con la chiave di quell'installazione ([La chiave dell'istanza di un'altra
installazione](cli_tools.md)). Dal primo avvio dopo il cambio, e a ogni avvio
finché non vengono inseriti di nuovo o non torna la vecchia chiave, il log contiene un errore che conta quelli
a livello di istanza, se ce ne sono: vedi [Controlli all'avvio](configuration_security.md#startup-checks).

Se `secrets/instance.key` è danneggiato o irraggiungibile, LibreFolio si avvia comunque, con un errore dai
[controlli all'avvio](configuration_security.md#startup-checks); una chiave impostata da te che non può essere usata arresta invece l'avvio.
Finché non lo correggi:

- ogni segreto salvato viene segnalato come illeggibile, e i plugin funzionano senza di essi: un plugin che ne richiede
  uno risponde che non è configurato;
- i segreti forniti da variabili continuano a funzionare;
- un nuovo segreto non può essere salvato: la scheda risponde *Impossibile salvare i segreti: la chiave di questa istanza non può
  essere usata (vedi i controlli di configurazione).*, e nulla di quel salvataggio viene scritto;
- il log contiene un errore in più, la prima volta che ogni processo del server ha bisogno di un segreto salvato:
  `Plugin secrets unreadable: the instance key cannot be used (see the configuration checks)`.

Correggi il file, o ripristinalo da un backup, e i segreti salvati tornano disponibili. Una nuova chiave non li riporta
indietro: bisognerebbe inserirli di nuovo.

!!! warning "🗄️ Il database e la chiave nella stessa cartella"

    Il database (`sqlite/app.db`) e la chiave dell'istanza che LibreFolio genera
    (`secrets/instance.key`) sono nella stessa [directory dei dati](filesystem.md): chiunque ottenga entrambi, la
    cartella stessa o una sua copia, può leggere ogni segreto salvato.

    - Mantieni privata la directory dei dati, e ogni sua copia.
    - Meglio ancora, fornisci la chiave dell'istanza da un archivio di segreti, con `LIBREFOLIO_INSTANCE_KEY_FILE` (un
      segreto Docker) o `LIBREFOLIO_INSTANCE_KEY`: così LibreFolio non la scrive mai nella directory dei
      dati. Se LibreFolio ha già creato `secrets/instance.key`, usa il suo contenuto come
      valore, come spiega [La chiave dell'istanza](#instance-key): un'altra chiave renderebbe i segreti salvati
      illeggibili.

---

## 🔗 Correlati

- 📄 **[Configurazione](configuration.md)** — Creare il file `.env`, Opzioni principali, Parametri impostati dagli strumenti, …
- 📄 **[Configurazione: Controlli e protezioni](configuration_security.md)** — Controlli all'avvio, Protezioni del browser, Arresto del server
- 📄 **[Configurazione: Account e ricerca degli asset](configuration_accounts.md)** — Account e registrazioni, L'ordine dei provider di prezzi nella ricerca, Facoltativo: ricerca web per nuovi asset
