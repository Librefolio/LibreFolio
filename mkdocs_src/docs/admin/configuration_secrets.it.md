# 🔐 Configurazione: Segreti e impostazioni dei plugin

Cosa deve restare privato in un'installazione di LibreFolio: le opzioni che sono **segreti** (chiavi, password e token), anche lette da file come i segreti Docker; la **chiave dell'istanza**, che protegge ciò che LibreFolio memorizza; le **impostazioni dei plugin**, chiavi API comprese.

Non conosci il file `.env`? Come crearlo, le opzioni principali e quale valore prevale: [Configurazione](configuration.md).

---

## 🔐 Segreti {: #secrets }

**Dove**: nel `.env` di LibreFolio, oppure nell'ambiente del container (blocco `environment:` di `docker-compose.yml`). Ogni segreto può anche essere letto da un file, con la sua variabile `_FILE` ([Segreti nei file](#secret-files)). Trattali con la stessa riservatezza del database.

| Segreto | Da un file | Che cos'è |
| --- | --- | --- |
| `JWT_SECRET` | `JWT_SECRET_FILE` | La chiave che firma le sessioni di accesso, nelle [opzioni principali](configuration.md). |
| `LIBREFOLIO_INSTANCE_KEY` | `LIBREFOLIO_INSTANCE_KEY_FILE` | La [chiave dell'istanza](#instance-key). Non impostata: LibreFolio ne crea una nella directory dei dati. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` | La chiave di un servizio di ricerca a pagamento, per il motore `apikey` della [ricerca web](configuration_accounts.md#optional-web-search-for-new-assets). |
| `LIBREFOLIO_SMTP_PASSWORD` | `LIBREFOLIO_SMTP_PASSWORD_FILE` | La password del server SMTP che invia le email di LibreFolio: [Email](email.md). |

Un plugin può avere segreti propri, come la chiave API di una fonte dati a pagamento: [Impostazioni dei plugin](#plugin-settings).

### 📄 Segreti nei file {: #secret-files }

Aggiungi `_FILE` al nome del segreto e indica il percorso di un file che lo contiene, ad esempio `/run/secrets/jwt_secret`. È così che Docker e Kubernetes passano i loro segreti: il segreto resta fuori da `.env` e dall'ambiente del container.

Regole del file:

- Il segreto è il testo del file, senza le interruzioni di riga finali e senza il byte order mark che alcuni editor di Windows inseriscono all'inizio. Ogni altro spazio conta, anche all'inizio e alla fine.
- Un percorso relativo parte dalla cartella del progetto.
- Un segreto o la sua variabile `_FILE` vuoti o di soli spazi contano come non impostati: uno spazio accidentale non viene mai usato come chiave.
- Imposta uno dei due. Impostati entrambi: vince la variabile stessa, il file viene ignorato e il log di avvio contiene un [avviso](configuration_security.md#startup-checks).
- `.env` funziona sia con `./dev.py` sia con Docker Compose (`env_file: .env`): entrambi mettono i suoi valori nell'ambiente, da cui LibreFolio legge.

Se il file non fornisce il segreto:

| Variabile | Quando viene letta | Se il file non fornisce il segreto |
| --- | --- | --- |
| `JWT_SECRET_FILE`, `LIBREFOLIO_INSTANCE_KEY_FILE`, `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE` | all'avvio | **Il server si arresta all'avvio.** L'errore indica il nome della variabile e il percorso, mai il segreto. Vale per un file che manca, non può essere letto, è vuoto o in bianco (solo spazi e interruzioni di riga), non è testo UTF-8 o è più grande di 64 KiB. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` | solo quando una ricerca usa il motore `apikey` | Il server non si arresta: la ricerca prosegue senza la ricerca web, con un avviso nel log (`web_link_finder: …; disabling`); la ricerca propria dei provider continua a funzionare. |
| `LIBREFOLIO_SMTP_PASSWORD_FILE` | solo quando `LIBREFOLIO_SMTP_HOST` è impostato | Il server non si arresta: l'email resta disattivata, con un errore nel log (`Email configuration cannot be used: email stays off`). |

??? example "🐳 Un segreto Docker con Docker Compose"

    1. **Da terminale, nella cartella di `docker-compose.yml`**, salva una nuova chiave in un file:

        ```bash
        python3 -c "import secrets; print(secrets.token_urlsafe(64))" > jwt_secret.txt
        ```

        Ottieni `jwt_secret.txt` accanto a `docker-compose.yml`.

    2. **Da terminale**, rendi il file leggibile all'utente dell'immagine, `1000:1000` per quella ufficiale ([Docker avanzato](docker_advanced.md)):

        ```bash
        sudo chown 1000:1000 jwt_secret.txt
        sudo chmod 600 jwt_secret.txt
        ```

        Compose monta il file nel container così com'è sull'host, proprietario e permessi compresi: se l'utente dell'immagine non può leggerlo, il server si arresta all'avvio con `cannot be read` per il file.

    3. **In `docker-compose.yml`**, aggiungi le righe contrassegnate e lascia il resto del servizio com'è:

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

    4. **In `.env`**, se una riga assegna un valore a `JWT_SECRET`, rimuovila: vincerebbe sul file. Una riga `JWT_SECRET=` vuota non fa danni.

    5. Riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`.

    I file di `LIBREFOLIO_INSTANCE_KEY_FILE`, `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` e `LIBREFOLIO_SMTP_PASSWORD_FILE` si montano allo stesso modo; cosa fa ciascuna variabile quando il file non fornisce il segreto: la tabella in [Segreti nei file](#secret-files).

### 🗝️ La chiave dell'istanza {: #instance-key }

Un unico segreto per installazione: LibreFolio ne deriva le proprie chiavi di crittografia. Non c'è nulla da configurare. LibreFolio usa la prima chiave che trova:

1. `LIBREFOLIO_INSTANCE_KEY`, la chiave stessa;
2. `LIBREFOLIO_INSTANCE_KEY_FILE`, un file che la contiene, come un segreto Docker;
3. `secrets/instance.key` nella directory dei dati, che LibreFolio crea la prima volta che ne ha bisogno: 43 caratteri casuali, in una cartella e in un file che solo l'utente che esegue LibreFolio può aprire (`0700` e `0600`).

**Per fornire una chiave tua**, ad esempio in cloud, dall'ambiente o da un segreto Docker invece che dalla directory dei dati. Ogni istanza ha una chiave propria: non condividere mai una chiave tra più istanze.

1. **Da terminale**, genera la chiave:

    ```bash
    python3 -c "import secrets; print(secrets.token_urlsafe(32))"
    ```

    Ottieni una chiave casuale di almeno 32 caratteri, il minimo. Non usare mai una passphrase: le chiavi che LibreFolio ne deriva sono robuste solo quanto la passphrase. Se LibreFolio ha già creato `secrets/instance.key`, non generare nulla: usa il suo contenuto come valore, perché impostare `LIBREFOLIO_INSTANCE_KEY` dove `secrets/instance.key` esiste già cambia la chiave.

2. **In `.env` o nell'ambiente del container**, imposta la chiave, oppure salvala in un file e indica il percorso, come nell'[esempio Docker](#secret-files):

    ```env
    LIBREFOLIO_INSTANCE_KEY=<la chiave>
    # oppure
    LIBREFOLIO_INSTANCE_KEY_FILE=/run/secrets/instance_key
    ```

3. Riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`.

!!! warning "🔑 Non cambiare né eliminare mai la chiave una volta in uso"

    Solo la stessa chiave può rileggere ciò che è stato crittografato con essa.

    - Fai il backup di `secrets/` insieme al resto della directory dei dati e conserva le copie private quanto il database: [Backup](filesystem.md#backup).
    - Una volta che la chiave esiste, LibreFolio non distingue un `instance.key` perduto da un primo utilizzo: crea una nuova chiave, e ciò che la vecchia aveva crittografato non può più essere letto. Quando ripristini i dati, rimetti `secrets/` insieme a essi prima di avviare di nuovo LibreFolio. Non avviare mai LibreFolio su dati ripristinati senza il relativo `secrets/`.
    - Se LibreFolio ha già creato una nuova chiave: arrestalo, metti la tua copia di `instance.key` al posto di quella nuova e avvialo di nuovo, prima che qualcuno inserisca di nuovo un [segreto di plugin](#plugin-secrets): un segreto inserito con la nuova chiave diventerebbe illeggibile una volta ripristinata la vecchia.
    - `instance.key` presente ma danneggiato o irraggiungibile: LibreFolio registra un errore e non lo sostituisce mai. Cosa fare: [Controlli all'avvio](configuration_security.md#startup-checks).

### 🔏 Il controllo della chiave {: #instance-key-check }

Accanto alla chiave, LibreFolio conserva un **valore di controllo**: `secrets/instance.key.check` nella directory dei dati (cartella `0700`, file `0600`), una breve impronta della chiave da cui non si risale alla chiave. A ogni avvio confronta l'impronta della chiave che ha ora con quella memorizzata: differiscono quando si avvia con **una chiave diversa da quella con cui sono stati scritti i dati** (una macchina che ha ricevuto la chiave sbagliata, un file chiave sostituito con uno nuovo).

- **Il primo avvio** scrive il file. Non lo scrive se esistono già segreti di plugin salvati e la chiave attuale non ne legge nessuno: scambierebbe la chiave sbagliata per quella giusta. Il controllo indica allora che la chiave non corrisponde finché non rimetti quella giusta.
- **Con una chiave che non corrisponde**: errore nel log all'avvio, e la scheda **Sicurezza** di Impostazioni › Amministrazione lo indica (il controllo è `platform.instance_key_check`). **L'istanza continua a funzionare**: i tuoi dati non dipendono da questa chiave, solo i segreti di plugin salvati.

**La soluzione è la chiave giusta.**

1. **In `.env` o nell'ambiente del container** (`LIBREFOLIO_INSTANCE_KEY` o il suo `_FILE`), oppure **nella directory dei dati** (`secrets/instance.key`), rimetti la chiave con cui i dati sono stati scritti.
2. Riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`. La risposta successiva è `ok`, senza altro da fare.

**Per cambiare davvero la chiave**, ad esempio quando decidi che i vecchi segreti sono persi e i segreti dei plugin vengono inseriti di nuovo:

1. **In `.env` o nell'ambiente del container**, aggiungi, per **un solo avvio**:

    ```env
    LIBREFOLIO_INSTANCE_KEY_ACCEPT=1
    ```

    Valori: `1` o `0`, `true` o `false`, `yes` o `no`, `on` o `off`; qualsiasi altro valore arresta l'avvio, indicando il nome della variabile.

2. Riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`. Quell'avvio sostituisce il valore di controllo memorizzato con quello della chiave che ha, e registra un avviso.

3. **Rimuovi la variabile e riavvia di nuovo.** Finché è impostata, ogni avvio accetta qualunque chiave abbia e la protezione non fa nulla; l'avviso viene registrato a ogni avvio, come promemoria.

!!! note "📏 Cosa il controllo non può vedere"

    - Senza un valore di controllo memorizzato e senza alcun segreto di plugin salvato non c'è nulla da confrontare: la risposta è `ok`. Il primo avvio di un'istanza la cui chiave era già sbagliata non può essere riconosciuto; da quel momento in poi, il valore memorizzato la protegge.
    - Se i dati tornano senza la loro cartella `secrets/`, il valore viene scritto di nuovo all'avvio successivo; finché manca, decidono i segreti dei plugin.
    - Un valore di controllo che non può essere letto (un permesso, un file danneggiato) non impedisce mai un backup: la risposta è `ok` e il log contiene un avviso, una volta sola.

---

## 🧩 Impostazioni dei plugin {: #plugin-settings }

Un plugin può richiedere impostazioni proprie: la chiave API di una fonte dati a pagamento, una regione, una preferenza. Dei plugin forniti con LibreFolio, due ne richiedono una, una preferenza di ricerca personale ciascuno: justETF e Borsa Italiana. Nessuno richiede un'impostazione a livello di istanza; un plugin che aggiungi potrebbe farlo. Due tipi:

| Tipo | Chi la salva | Chi la legge | Da variabile d'ambiente |
| --- | --- | --- | --- |
| **A livello di istanza** | solo un amministratore | ogni utente legge un valore in chiaro; di un valore segreto, come una chiave API, sa soltanto se è impostato | sì: [Le variabili](#plugin-variables) |
| **Personale** | solo quell'utente | solo quell'utente; gli amministratori non la vedono mai | no |

**Dove si modificano**: in **Impostazioni › Plugin**, una scheda che ogni utente ha: le personali ognuno le proprie, quelle a livello di istanza solo gli amministratori (gli altri utenti le vedono in sola lettura). Nella finestra di dialogo dell'asset, **Configura**, accanto al provider di prezzi scelto, apre lo stesso modulo solo per quel provider. Cosa mostra la scheda, impostazione per impostazione: [Impostazioni dei plugin](../user/settings/plugins.md) nel manuale utente.

I plugin che hanno impostazioni, con le chiavi delle loro impostazioni, sono elencati da `GET /api/v1/settings/plugins` a qualsiasi utente autenticato.

### 🏷️ Le variabili {: #plugin-variables }

**Dove**: in `.env` o nell'ambiente del container, come le altre opzioni; solo per le impostazioni a livello di istanza. Il nome della variabile:

```text
LIBREFOLIO_PLUGIN_<KIND>_<PLUGIN CODE>_<SETTING KEY>
```

- `<KIND>` è `ASSET` per un provider di prezzi e `FX` per un provider di tassi di cambio.
- Tutto in maiuscolo; ogni carattere diverso da una lettera o da una cifra diventa `_`. L'impostazione `api_key` del provider di prezzi `my_provider`:

    ```env
    LIBREFOLIO_PLUGIN_ASSET_MY_PROVIDER_API_KEY=<valore>
    ```

- Ogni variabile ha anche una forma `_FILE`: il percorso di un file che contiene il valore, come un segreto Docker, letto come in [Segreti nei file](#secret-files). Un file che non può essere letto non arresta mai il server: vedi [sotto](#plugin-variable-lock).
- Per un'impostazione segreta, un plugin può accettare anche la variabile che leggeva prima di avere impostazioni, così che un'installazione esistente continui a funzionare. Impostate entrambe, vince il nome qui sopra.

Poi riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`.

### 🔒 Una variabile blocca l'impostazione {: #plugin-variable-lock }

Finché la sua variabile è impostata, un'impostazione prende il valore da lì e nessuno può cambiarla dall'interno di LibreFolio: un salvataggio viene rifiutato (`LOCKED_BY_ENV`), e un valore salvato in precedenza viene ignorato finché non rimuovi la variabile e riavvii. **Impostazioni › Plugin** mostra l'impostazione in sola lettura, un segreto solo come *Impostato*: *Impostato dalla variabile del server* e il nome della variabile per gli amministratori, *Impostato dal server* per gli altri utenti.

**Un valore sbagliato**, uno che l'impostazione non accetta, o un `_FILE` che non può essere letto, blocca comunque l'impostazione, e il plugin risulta non configurato: LibreFolio rifiuta ogni richiesta nei suoi confronti, anche quando l'impostazione è facoltativa, finché non correggi la variabile. Non ripiega mai sul valore salvato né su quello predefinito del plugin.

- Nel log, un avviso una volta per processo del server: `Plugin setting variable invalid: the plugin is not configured until it is fixed`, con la variabile e il motivo, mai il valore.
- In **Impostazioni › Plugin**, il badge del plugin riporta **Da configurare** e l'impostazione dice che la sua variabile non è valida.

Correggi il valore **in `.env` o nell'ambiente del container**, poi riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`.

### 🔐 Segreti salvati e la chiave dell'istanza {: #plugin-secrets }

Un'impostazione salvata dentro LibreFolio è conservata nel database. Una segreta viene prima crittografata (AES-256-GCM) con una chiave derivata dalla [chiave dell'istanza](#instance-key), e non viene mai più mostrata, neppure a chi l'ha salvata: **Impostazioni › Plugin** dice solo se è impostata, *Impostato il* e la data in cui è stata salvata. Un valore fornito da una variabile, segreto o no, non viene mai salvato nel database.

**Se la chiave dell'istanza cambia**, i segreti salvati non possono più essere letti. LibreFolio li conserva, li segnala come illeggibili e non usa mai un valore sbagliato. La scheda lo dice sotto ciascuno: *Salvato, ma la chiave di questa istanza non può leggerlo. Se un amministratore può rimettere la vecchia chiave, quella ha la priorità; altrimenti inseriscilo di nuovo.* Dal primo avvio dopo il cambio, e a ogni avvio finché non vengono inseriti di nuovo o non torna la vecchia chiave, il log contiene un errore che conta quelli a livello di istanza, se ce ne sono: [Controlli all'avvio](configuration_security.md#startup-checks).

| Situazione | Cosa fare |
| --- | --- |
| Hai ancora la vecchia chiave | Rimettila, prima che qualcuno inserisca di nuovo i segreti ([La chiave dell'istanza](#instance-key) spiega perché). |
| Non l'hai più | Inserisci di nuovo ogni segreto in **Impostazioni › Plugin**. |
| Vuoi portarli in un'altra installazione, che conserva una propria chiave | **Da terminale, su quell'installazione**, ripristina un backup con la vecchia chiave: `backup restore` con `--instance-key-file` li ricrittografa con la chiave di quell'installazione ([La chiave dell'istanza di un'altra installazione](cli_tools.md)). |

**Se `secrets/instance.key` è danneggiato o irraggiungibile**, LibreFolio si avvia comunque, con un errore dai [controlli all'avvio](configuration_security.md#startup-checks); una chiave impostata da te che non può essere usata arresta invece l'avvio. Finché non lo correggi:

- ogni segreto salvato viene segnalato come illeggibile, e i plugin funzionano senza di essi: un plugin che ne richiede uno risponde che non è configurato;
- i segreti forniti da variabili continuano a funzionare;
- un nuovo segreto non può essere salvato: la scheda risponde *Impossibile salvare i segreti: la chiave di questa istanza non può essere usata (vedi i controlli di configurazione).*, e nulla di quel salvataggio viene scritto;
- il log contiene un errore in più, la prima volta che ogni processo del server ha bisogno di un segreto salvato: `Plugin secrets unreadable: the instance key cannot be used (see the configuration checks)`.

Correggi il file **nella directory dei dati**, o ripristinalo da un backup: i segreti salvati tornano disponibili. Una nuova chiave non li riporta indietro: bisognerebbe inserirli di nuovo.

!!! warning "🗄️ Il database e la chiave nella stessa cartella"

    Il database (`sqlite/app.db`) e la chiave dell'istanza che LibreFolio genera (`secrets/instance.key`) sono nella stessa [directory dei dati](filesystem.md): chiunque ottenga entrambi, la cartella stessa o una sua copia, può leggere ogni segreto salvato.

    - Mantieni privata la directory dei dati, e ogni sua copia.
    - Meglio ancora, fornisci la chiave dell'istanza da un archivio di segreti, con `LIBREFOLIO_INSTANCE_KEY_FILE` (un segreto Docker) o `LIBREFOLIO_INSTANCE_KEY`: così LibreFolio non la scrive mai nella directory dei dati. Se `secrets/instance.key` esiste già, usa il suo contenuto come valore ([La chiave dell'istanza](#instance-key)): un'altra chiave renderebbe i segreti salvati illeggibili.

---

## 🔗 Correlati

- 📄 **[Configurazione](configuration.md)** — Creare il file `.env`, Opzioni principali, Parametri impostati dagli strumenti, …
- 📄 **[Configurazione: Controlli e protezioni](configuration_security.md)** — Controlli all'avvio, Protezioni del browser, Arresto del server
- 📄 **[Configurazione: Account e ricerca degli asset](configuration_accounts.md)** — Account e registrazioni, L'ordine dei provider di prezzi nella ricerca, Facoltativo: ricerca web per nuovi asset
