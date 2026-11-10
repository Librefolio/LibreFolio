# 📧 Email

LibreFolio invia email tramite un server SMTP che indichi in alcune variabili d'ambiente.
L'email è **facoltativa**: senza di essa non cambia nulla, non viene inviato nulla e i link di invito e di
reimpostazione della password vengono copiati a mano.

Cosa invia LibreFolio:

- **Un'email di prova**, che un amministratore invia al proprio indirizzo da
  **Impostazioni › Amministrazione › Email**.
- **I link di invito e di reimpostazione della password creati da un amministratore**, con **Invia via email** nei
  rispettivi dialoghi: [Link inviati da un amministratore](email_flows.md#admin-links).
- **Un link di reimpostazione per una password dimenticata**, a chi ne richiede uno dalla pagina di accesso:
  [Password dimenticate](email_flows.md#forgot-password).
- **Il link di configurazione dell'amministratore iniziale**, una volta, quando LibreFolio crea quell'amministratore
  da `LIBREFOLIO_ADMIN_EMAIL` e genera il link da solo: [L'amministratore iniziale](configuration_accounts.md#initial-admin).
- **Un link per confermare l'indirizzo email di un nuovo account**, quando **Richiedi verifica email** è
  attivo: [Verifica dell'email](email_flows.md#verification).
- **Un avviso al vecchio indirizzo e una conferma al nuovo** quando qualcuno cambia l'indirizzo email del proprio account:
  [Cambi di indirizzo email](email_flows.md#email-change-notice).

Le email con un link richiedono anche `LIBREFOLIO_PUBLIC_URL`: [Email con un link](email_flows.md#public-url).

Per configurare l'email:

1. **Nel `.env` di LibreFolio**, sezione `# Email`: scrivi le variabili `LIBREFOLIO_SMTP_*`, almeno il server e il
   mittente, più il login quando il server lo richiede. Copia l'[esempio](#examples) del tuo caso.
2. **Nello stesso `.env`**, per le email con un link: `LIBREFOLIO_PUBLIC_URL` ([Email con un link](email_flows.md#public-url)).
3. **Da terminale**: riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`.
4. **In LibreFolio**, **Impostazioni › Amministrazione › Email**: lo stato indica **Pronto**. Invia a te stesso
   un'[email di prova](#test-email).

!!! info "📚 Questa guida è divisa in più pagine"

    Questa pagina configura l'email: le variabili, esempi per i server usuali, la scheda **Email** di Impostazioni e la sua email di prova. Il resto della guida:

    - [Email: link e messaggi](email_flows.md): le email con un link, le password dimenticate, i loro limiti, la verifica dell'email e l'avviso di un cambio di indirizzo.
    - [Email: quando non funziona](email_troubleshooting.md): gli errori, cosa dice il log e le note di sicurezza della configurazione SMTP.

---

## 🔐 Dove si trova la configurazione {: #where-it-lives }

**Solo da variabili d'ambiente**, scritte nel `.env` come le altre [opzioni](configuration.md): `./dev.py` e
Docker Compose (`env_file: .env`) le passano al server. La password anche in un file segreto.

- **Mai memorizzata.** Non è nel database e un backup di LibreFolio non la contiene: conserva una tua copia di
  `.env` e del file della password.
- **Mai mostrata.** Nessuna pagina dell'interfaccia mostra server, porta, utente, mittente o password.
  [Impostazioni › Amministrazione › Email](#email-tab) dice se l'email funziona e, se no, quale variabile
  correggere; dei valori `LIBREFOLIO_SMTP_*` mostra solo il limite orario.
- **Pubblico: solo se l'email è pronta.** `/api/v1/system/instance`, leggibile da chiunque raggiunga il server,
  dice `"available": true` quando lo stato è **Pronto** e `"links": true` quando, in più, le email possono
  portare un link ([Email con un link](email_flows.md#public-url)). Nient'altro.
- **Riavvia dopo una modifica.** Con Docker Compose, esegui `docker compose up -d`.

Per disattivare l'email: **nel `.env`** rimuovi `LIBREFOLIO_SMTP_HOST` o lasciala vuota, poi riavvia. Le altre
variabili possono restare: senza un server, LibreFolio le ignora.

---

## 📋 Le variabili {: #variables }

**Nel `.env`**, sezione `# Email`. `.env.example` le elenca commentate: copia le righe che ti servono.

| Variabile | Predefinito | Valori accettati |
| --- | --- | --- |
| `LIBREFOLIO_SMTP_HOST` | _non impostato_: email disattivata | Il server SMTP: un nome host, come `smtp.example.com`, o un indirizzo IP, e nient'altro: niente `smtp://`, niente `user@`, niente `:587`, niente percorso. Un indirizzo IPv6 senza parentesi quadre, come `fd00::25`. |
| `LIBREFOLIO_SMTP_TLS` | `starttls` | `starttls`, `tls` o `none`, in maiuscolo o no: [Modalità di crittografia](#encryption-modes). |
| `LIBREFOLIO_SMTP_PORT` | `587` con `starttls`, `465` con `tls`, `25` con `none` | Un numero intero da 1 a 65535. Impostala solo se il server usa una porta diversa da quella della sua modalità. |
| `LIBREFOLIO_SMTP_USER` | _non impostato_: nessun login | Il login del tuo account sul server SMTP. |
| `LIBREFOLIO_SMTP_PASSWORD` | _non impostato_ | La password di quel login, usata esattamente come scritta, spazi inclusi. Oppure `LIBREFOLIO_SMTP_PASSWORD_FILE`: il percorso di un file che la contiene. |
| `LIBREFOLIO_SMTP_FROM` | _obbligatorio_ con un server | Il mittente: un indirizzo, con o senza nome, come `LibreFolio <noreply@example.com>` o `noreply@example.com`. |
| `LIBREFOLIO_SMTP_REPLY_TO` | _non impostato_: le risposte vanno al mittente | L'indirizzo a cui vanno le risposte. |
| `LIBREFOLIO_SMTP_MAX_PER_HOUR` | `50` | Quante email LibreFolio può inviare in un'ora, per processo del server: un numero intero, almeno 1. |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` | `20` | Quante email di registrazione può attivare un indirizzo client in un'ora, per processo del server: un numero intero, almeno 1. Oltre il limite, i nuovi account vengono creati e restano in attesa, ma le loro email vengono trattenute: [Limiti delle email di verifica](email_flows.md#verification-limits). Non è una variabile SMTP (il nome non inizia con `LIBREFOLIO_SMTP_`), ma viene controllata con loro e letta solo quando un server è impostato. |

- **Vuoto equivale a non impostato**: un valore vuoto, o di soli spazi, conta come non impostato.
- **Il login va in coppia**: `LIBREFOLIO_SMTP_USER` insieme a una password, o nessuno dei due per un server che
  accetta posta senza login.
- **La password in un file**: `LIBREFOLIO_SMTP_PASSWORD_FILE` segue [Segreti nei file](configuration_secrets.md#secret-files).
  La password è il testo del file così com'è, qualunque carattere contenga, senza le interruzioni di riga alla
  fine. Imposta una sola delle due: se sono impostate entrambe, vince `LIBREFOLIO_SMTP_PASSWORD`, il file viene
  ignorato e il log di avvio contiene un avviso. A differenza di `JWT_SECRET_FILE`, un file della password che
  non può essere letto non blocca il server: l'email resta disattivata finché non viene corretto.
- **I limiti orari contano per processo del server**, sugli ultimi 60 minuti, in memoria:
  `LIBREFOLIO_SMTP_MAX_PER_HOUR` e `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` allo stesso modo. Un riavvio
  riparte da zero. `./dev.py server --workers 4` esegue quattro processi, ciascuno con il proprio conteggio:
  l'istanza può inviare fino a quattro volte il limite ([Avviare il server](cli_tools.md#start-the-server)).
  L'immagine Docker esegue un solo processo.

### 🔑 Modalità di crittografia {: #encryption-modes }

| `LIBREFOLIO_SMTP_TLS` | Cosa fa | Porta usuale |
| --- | --- | --- |
| `starttls` (predefinito) | Si connette, poi passa alla crittografia prima di inviare qualsiasi cosa. Un server che non lo offre viene rifiutato: nulla esce in chiaro. | 587 |
| `tls` | Crittografato dal primo byte, detto anche SSL/TLS o SMTPS. | 465 |
| `none` | Nessuna crittografia: messaggi, link e password viaggiano in chiaro. Solo per un relay sulla stessa macchina o sulla tua rete locale. | 25 |

- Con `starttls` e `tls`, LibreFolio controlla il certificato del server: deve essere valido ed emesso per il
  nome in `LIBREFOLIO_SMTP_HOST`. Scrivi il nome per cui è emesso il certificato, di solito non l'indirizzo IP.
- La porta segue la modalità, non il contrario: `LIBREFOLIO_SMTP_PORT=465` da sola mantiene `starttls`, che un
  server sulla porta 465 non si aspetta. Per la porta 465, imposta `LIBREFOLIO_SMTP_TLS=tls`.

---

## 💡 Esempi {: #examples }

**Nel `.env` di LibreFolio**, nella sezione che inizia con `# Email`: l'`.env.example` di questa versione la
contiene. Se il tuo `.env` è vecchio e non ha quella sezione, aggiungi in fondo il blocco dell'esempio.
Sostituisci `smtp.example.com`, gli indirizzi e la password con i tuoi, poi riavvia LibreFolio.

=== "Docker Compose + file segreto"

    La password resta fuori da `.env` e dall'ambiente del container, in un segreto Docker.

    1. **In un file accanto a `docker-compose.yml`**, come `smtp_password.txt`: salva la password. Un'interruzione
       di riga alla fine non conta; gli spazi sì.
    2. **Da terminale**, nella stessa cartella: il container vede il file con il proprietario e i permessi che ha
       sull'host, quindi rendilo leggibile all'utente che esegue LibreFolio. Con l'immagine ufficiale è `1000:1000`:

        ```bash
        sudo chown 1000:1000 smtp_password.txt
        sudo chmod 600 smtp_password.txt
        ```

        Un'immagine costruita da te può usare altri id: mettili nel comando `chown`
        ([Docker avanzato](docker_advanced.md)).

    3. **In `docker-compose.yml`**: aggiungi le righe contrassegnate e lascia il resto del servizio com'è. Se il
       file ha già elenchi `secrets:`, come l'esempio `JWT_SECRET_FILE` di [Segreti](configuration_secrets.md#secrets),
       aggiungi le nuove righe a quegli elenchi:

        ```yaml
        services:
          librefolio:
            secrets:                         # added
              - smtp_password                # added
        secrets:                             # added
          smtp_password:                     # added
            file: ./smtp_password.txt        # added
        ```

    4. **Nel `.env`**: aggiungi le variabili. Se c'è una riga `LIBREFOLIO_SMTP_PASSWORD` con un valore, rimuovila:
       avrebbe la meglio sul file.

        ```env
        LIBREFOLIO_SMTP_HOST=smtp.example.com
        LIBREFOLIO_SMTP_USER=noreply@example.com
        LIBREFOLIO_SMTP_PASSWORD_FILE=/run/secrets/smtp_password
        LIBREFOLIO_SMTP_FROM=LibreFolio <noreply@example.com>
        ```

        Nessun `LIBREFOLIO_SMTP_TLS` e nessuna porta: `starttls` sulla porta 587 è il valore predefinito.

    5. **Da terminale**: esegui `docker compose up -d`. Lo stato in
       [Impostazioni › Amministrazione › Email](#email-tab) indica **Pronto**.

=== "Provider di posta"

    Il tuo account sul server SMTP di un provider di posta.

    1. **Nel `.env`**, sezione `# Email`:

        ```env
        LIBREFOLIO_SMTP_HOST=smtp.example.com
        LIBREFOLIO_SMTP_USER=you@example.com
        LIBREFOLIO_SMTP_PASSWORD=your-app-password
        LIBREFOLIO_SMTP_FROM=LibreFolio <you@example.com>
        ```

        - È `starttls` sulla porta 587, i valori predefiniti. Se il provider indica la porta 465, aggiungi
          `LIBREFOLIO_SMTP_TLS=tls`: la porta segue.
        - Usa una **password per app**, non la password con cui accedi: il provider la crea per una singola
          applicazione e puoi revocarla senza toccare il tuo account.
        - Le pagine di aiuto del provider indicano nome del server, porta e crittografia, e quali indirizzi
          mittente può usare il tuo account.
        - Meglio ancora, conserva la password in un file, come nella scheda Docker Compose.

    2. Riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`. Lo stato in
       [Impostazioni › Amministrazione › Email](#email-tab) indica **Pronto**.

=== "Gmail"

    Il tuo account Gmail, o di Google Workspace, tramite il server SMTP di Gmail. LibreFolio accede solo con
    utente e password, non con «Accedi con Google»: serve una **password per app**, non la password del tuo
    account Google.

    1. **Nel tuo account Google**: attiva la **Verifica in due passaggi**, se non lo è già. Le password per app
       esistono solo con essa.
    2. **Su [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)**: crea una password
       per app, con un nome come `LibreFolio`. Google la mostra come un codice di 16 caratteri, in quattro gruppi
       da quattro: copiala. Se la pagina non offre alcun modo per crearne una,
       [la pagina di aiuto di Google](https://support.google.com/accounts/answer/185833) spiega perché. Un account
       di lavoro o scolastico potrebbe aver bisogno del suo amministratore.
    3. **Nel `.env`**, sezione **Email**, o in fondo se il tuo `.env` non ce l'ha:

        ```env
        # =============================================================================
        # Email config gmail
        # =============================================================================
        LIBREFOLIO_SMTP_HOST=smtp.gmail.com
        LIBREFOLIO_SMTP_USER=you@gmail.com
        LIBREFOLIO_SMTP_PASSWORD=abcdefghijklmnop
        LIBREFOLIO_SMTP_FROM=LibreFolio <you@gmail.com>
        ```

        - `you@gmail.com` sta per il tuo indirizzo Gmail completo, o quello di lavoro con Google Workspace.
        - `abcdefghijklmnop` sta per la password per app: i suoi 16 caratteri **senza gli spazi**, perché LibreFolio
          usa la password esattamente come scritta, spazi inclusi. Meglio ancora, conservala in un file della
          password come nella scheda Docker Compose, anche lì senza gli spazi.
        - **Gli spazi vanno bene nel mittente, non nella password.**
        - Il mittente è lo stesso indirizzo, con o senza un nome davanti. Gmail invia solo dal tuo indirizzo, o da
          uno che hai aggiunto e confermato in **Invia messaggi come** nelle impostazioni di Gmail.
        - Nessun `LIBREFOLIO_SMTP_TLS` e nessuna porta: `starttls` sulla porta 587 è il predefinito e una delle due
          modalità di Gmail. Per l'altra, la porta 465, aggiungi `LIBREFOLIO_SMTP_TLS=tls`: la porta segue.

    4. Riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`.
    5. **In LibreFolio**, **Impostazioni › Amministrazione › Email**: lo stato indica **Pronto**. Fai clic su
       **Invia un'email di prova**: va all'indirizzo del tuo account ([L'email di prova](#test-email)).

    Per mantenerlo funzionante:

    - Un account Gmail personale invia circa 500 email al giorno: oltre, Gmail rifiuta per un periodo da 1 a 24
      ore. Un account Google Workspace ne ha 2.000 al giorno tramite `smtp.gmail.com`. Sono
      [i limiti di Google](https://support.google.com/mail/answer/22839), e Google può cambiarli. Quando Gmail
      rifiuta, l'email di prova e il log riportano il rifiuto ([Errori di invio](email_troubleshooting.md#sending-errors)).
    - Il limite di LibreFolio è di 50 email all'ora per impostazione predefinita: fino a 1.200 in un giorno. Per
      restare sotto il limite personale, **nel `.env`** aggiungi `LIBREFOLIO_SMTP_MAX_PER_HOUR=20`, cioè 480 al
      giorno, e riavvia. Il conteggio è per processo del server: [Le variabili](#variables).
    - Google revoca le password per app quando cambi la password del tuo account Google: creane una nuova,
      scrivila al posto della vecchia nel `.env` e riavvia. Anche rimuovere la password per app, nella pagina in
      cui l'hai creata, impedisce a LibreFolio di inviare.

=== "Relay locale"

    Un relay come Postfix, sulla stessa macchina o sulla tua rete, accetta posta senza login e la consegna per
    LibreFolio. Tre casi; in ognuno le variabili vanno **nel `.env`**, sezione `# Email`, poi riavvia.

    **LibreFolio sull'host, relay sulla stessa macchina:**

    ```env
    LIBREFOLIO_SMTP_HOST=localhost
    LIBREFOLIO_SMTP_TLS=none
    LIBREFOLIO_SMTP_FROM=LibreFolio <noreply@example.com>
    ```

    **LibreFolio in Docker, relay in un altro container sulla stessa rete Docker**, qui un servizio Compose
    chiamato `smtp-relay`:

    ```env
    LIBREFOLIO_SMTP_HOST=smtp-relay
    LIBREFOLIO_SMTP_TLS=none
    LIBREFOLIO_SMTP_FROM=LibreFolio <noreply@example.com>
    ```

    **LibreFolio in Docker, relay sull'host:** dentro un container, `localhost` è il container, non l'host.

    1. **In `docker-compose.yml`**: aggiungi le righe contrassegnate.

        ```yaml
        services:
          librefolio:
            extra_hosts:                                # added
              - "host.docker.internal:host-gateway"     # added
        ```

    2. **Nel `.env`**: `LIBREFOLIO_SMTP_HOST=host.docker.internal`, con `LIBREFOLIO_SMTP_TLS=none` e il mittente
       come sopra.
    3. **Nel relay**: lascia che accetti posta dalla rete Docker (in Postfix: `inet_interfaces` e `mynetworks`).

    In tutti i casi:

    - La porta 25 è la predefinita con `none`: imposta `LIBREFOLIO_SMTP_PORT` solo se il relay ascolta su un'altra.
    - Nessun utente e nessuna password: un relay senza login non li richiede.
    - Il relay consegna la posta: deve essere autorizzato a inviare per il dominio di `LIBREFOLIO_SMTP_FROM`.
    - `none` invia in chiaro: usalo solo verso la tua macchina o la tua rete. Verso qualsiasi altro server,
      Impostazioni › Amministrazione › Email e il log di avvio mostrano un [avviso](email_troubleshooting.md#security).

---

## 🖥️ Impostazioni › Amministrazione › Email {: #email-tab }

**In LibreFolio**: **Impostazioni** (icona dell'ingranaggio nella barra laterale) › **Amministrazione** › scheda
**Email**, dopo **Backup** (su un telefono: icona dello scudo, poi icona della busta). Solo gli amministratori la
vedono. L'icona del libro in alto apre questa pagina.

### 🚦 Lo stato {: #state }

| Stato | Cosa significa | Cosa mostra la scheda |
| --- | --- | --- |
| **Disattivato** | `LIBREFOLIO_SMTP_HOST` non è impostata: non viene inviato nulla. È l'impostazione predefinita. | Una breve spiegazione e un rimando a questa guida. |
| **Pronto** | Ogni variabile è utilizzabile. | Le email rimaste in quest'ora, gli avvisi applicabili, l'indirizzo con cui iniziano i link inviati via email e [il relativo controllo](#links-check), e **Invia un'email di prova**. |
| **Non funzionante** | Una variabile non è utilizzabile: l'email resta disattivata finché non viene corretta. | Il problema, con il nome della variabile responsabile, e un promemoria a riavviare dopo la correzione. |

!!! note "✅ Pronto non significa che un'email sia già stata consegnata"

    **Pronto** significa che ogni variabile è utilizzabile. LibreFolio non contatta il server finché non invia
    un'email: solo un'email di prova dimostra che il server accetta la tua posta.

- **Non funzionante** indica un problema alla volta, il primo che trova: correggilo nel `.env`, riavvia, poi
  controlla di nuovo. [Problemi di configurazione](email_troubleshooting.md#configuration-problems) dice cosa
  verificare per ciascuno.
- Con **Pronto**, la scheda conta le email rimaste, per esempio **48 di 50 email rimaste in quest'ora**: gli ultimi
  60 minuti, non l'ora di orologio. Quando non ne resta nessuna, indica tra quanti minuti può partire la
  successiva. Con più processi del server, ciascuno conta le proprie: la scheda mostra il conteggio del processo
  che ha risposto.
- L'avviso sulla crittografia compare quando `LIBREFOLIO_SMTP_TLS=none` punta a un server fuori dalla tua rete
  locale: [Note di sicurezza](email_troubleshooting.md#security).
- Un avviso su `LIBREFOLIO_PUBLIC_URL` compare quando non è impostata (informazione: le email funzionano, ma non
  può partire nessuna email con un link) o non può essere usata come base di un link (avviso):
  [Email con un link](email_flows.md#public-url).

### 🧭 L'indirizzo nei link inviati via email {: #links-check }

Con lo stato **Pronto** e una `LIBREFOLIO_PUBLIC_URL` utilizzabile, la scheda mostra *I link nelle email iniziano
con …*, seguito da quell'indirizzo, e verifica da questo browser che **questa** istanza risponda lì. È lo stesso
controllo firmato dei dialoghi di invito e di reimpostazione ([L'indirizzo del server di un link](users.md#server-address)).

| Messaggio | Cosa significa |
| --- | --- |
| *Controllo in corso da questo dispositivo per verificare che questa istanza risponda lì…* | La verifica è in corso. |
| *Questa istanza risponde lì, da questo dispositivo.* | Bene: i link raggiungono questa istanza di LibreFolio, almeno da qui. |
| *Da questo dispositivo, a quell'indirizzo risponde un altro server, non questa istanza.* … | Qualcosa risponde lì, ma non questa istanza di LibreFolio. |
| *Questo dispositivo non riesce a raggiungere questa istanza a quell'indirizzo.* … | Nessuna risposta che questo browser potesse leggere: un indirizzo sbagliato o chiuso, un nome che questo dispositivo non risolve, nessuna risposta entro 8 secondi, un browser che impedisce a una pagina pubblica di raggiungere un indirizzo locale o che chiede prima il tuo permesso, oppure una versione precedente di LibreFolio che non può rispondere al controllo. |
| *Questa pagina usa https:// mentre LIBREFOLIO_PUBLIC_URL inizia con http://* … | Questo browser non può controllare un indirizzo `http://` da una pagina `https://`, e i link nelle email viaggerebbero non crittografati: imposta la variabile sull'indirizzo `https://`. |
| *Questo browser non riesce a leggere LIBREFOLIO_PUBLIC_URL come indirizzo* … | Il browser legge gli indirizzi con un po' più di severità del server: i link potrebbero non aprirsi. Controlla il valore. |

!!! warning "📱 Solo questo dispositivo"

    Il controllo viene eseguito dal browser che stai usando, quindi dice ciò che vede questo dispositivo. Una VPN,
    un indirizzo IP diretto, il suo DNS o la sua rete possono essere diversi da quelli dei tuoi utenti: dopo un
    avviso, controlla da un altro dispositivo prima di cambiare la variabile. **Controlla di nuovo** ripete il
    controllo, per esempio dopo che hai cambiato rete.

- Il controllo viene eseguito una volta all'apertura della scheda, non dopo ogni email di prova. **Controlla di
  nuovo** compare con un avviso.
- Non viene controllato nulla con lo stato **Disattivato** o **Non funzionante**, né quando `LIBREFOLIO_PUBLIC_URL`
  non è impostata o non può essere usata, cosa che segnala l'avviso sopra.

### ✉️ L'email di prova {: #test-email }

**In LibreFolio**, **Impostazioni › Amministrazione › Email**, con lo stato **Pronto**: **Invia un'email di prova**
invia un'email a te stesso.

- **Al tuo indirizzo**: l'email del tuo account, come in [Profilo](../user/settings/profile.md). Non c'è un campo
  per digitarne un altro.
- **Nella tua lingua**: quella nelle tue [Preferenze](../user/settings/preferences.md), altrimenti la **Lingua
  predefinita** dell'istanza ([Impostazioni globali](settings.md)), altrimenti l'inglese.
- **Cosa dice**: l'oggetto è **LibreFolio test email** in inglese. Il messaggio nomina la tua istanza con
  l'indirizzo tramite cui il browser l'ha raggiunta, non con `LIBREFOLIO_PUBLIC_URL`, e dice che, se riesci a
  leggerlo, LibreFolio può inviare email. Arriva come testo semplice con una versione HTML.
- **Concorre al limite orario**, anche quando il server la rifiuta.

Il risultato compare sotto il pulsante. **Email di prova inviata al tuo indirizzo**: il server SMTP ha accettato il
messaggio; controlla la posta in arrivo e la cartella spam. Altrimenti la scheda dice cosa è andato storto:
[Errori di invio](email_troubleshooting.md#sending-errors). Mentre LibreFolio comunica con il server, il pulsante
indica **Invio in corso…**: LibreFolio attende fino a 20 secondi per ogni passaggio, quindi un server che non
risponde impiega un po' prima di fallire.

---

## 🔗 Voci correlate

- 📄 **[Email: link e messaggi](email_flows.md)** — Email con un link, Link inviati da un amministratore, Password dimenticate, …
- 📄 **[Email: quando non funziona](email_troubleshooting.md)** — Quando non funziona, Note di sicurezza
- 📝 **[Configurazione](configuration.md)** — Il file `.env` e le sue opzioni principali, e
  `LIBREFOLIO_PUBLIC_URL`
- 🔐 **[Configurazione: segreti e impostazioni dei plugin](configuration_secrets.md)** — Segreti nei file,
  come la password SMTP
- 🩺 **[Configurazione: controlli e protezioni](configuration_security.md)** — I controlli all'avvio
- ⚙️ **[Impostazioni globali](settings.md)** — L'interruttore **Richiedi verifica email**
- 👥 **[Utenti e inviti](users.md)** — Account in attesa e come consentirne l'accesso a uno
- 🛠️ **[Strumenti da riga di comando](cli_tools.md)** — Link di invito e di reimpostazione della password dalla riga
  di comando
- 🐳 **[Docker avanzato](docker_advanced.md)** — Il file Compose e l'utente che esegue LibreFolio
  nel container
- 📂 **[Struttura del filesystem](filesystem.md)** — Dove viene conservato il log
- 👤 **[Profilo](../user/settings/profile.md)** — L'indirizzo email del tuo account
- 🧑‍💻 Per gli sviluppatori: **[Servizio email (SMTP)](../developer/backend/email.md)** — Come funziona
  il servizio al suo interno
