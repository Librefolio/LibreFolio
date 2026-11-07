# ⚙️ Impostazioni globali

Le impostazioni globali valgono per l'intera istanza e per ogni utente. Vivono nel database.
Solo gli amministratori hanno la scheda per vederle e modificarle. Non sono segrete: l'app le legge per ogni utente connesso (il limite di caricamento, i valori predefiniti delle [Preferenze](../user/settings/preferences.md)…) e qualsiasi utente connesso può leggerle tramite l'API.

Alcune hanno una variabile nel file `.env` che le fissa o le precede: lo dice la colonna **Dove** di ogni tabella.

---

## 🗂️ Impostazioni › Amministrazione {: #administration }

**Dove:** **Impostazioni** (icona a ingranaggio nella barra laterale) › **Amministrazione**, all'estremità destra della barra delle schede su uno schermo ampio. Solo gli amministratori hanno il gruppo.
Fai clic su **Amministrazione**: apre **Impostazioni globali** e una seconda riga di schede sotto la prima.

| Scheda | A cosa serve |
|---|---|
| ⚙️ **Impostazioni globali** | Le impostazioni di questa pagina |
| 👥 **Utenti** | Gli account, gli inviti e i link per reimpostare la password: [Utenti e inviti](users.md) |
| 💾 **Backup** | L'intera istanza in un unico archivio e il suo ripristino: [Backup, ripristino e spostamento](backup_restore.md) |
| ✉️ **Email** | Se LibreFolio può inviare email e un'email di prova: [Email](email.md) |
| 🛡️ **Sicurezza** | Come è configurata l'istanza e cosa richiede la tua attenzione: [Sicurezza](#security-tab), più sotto |

- 👤 Un utente non amministratore non ha il gruppo né le sue schede: le sue **Impostazioni** terminano con **Informazioni**, e un link a una scheda del gruppo apre il suo **Profilo**.
- 🔁 Fai clic su **Amministrazione** mentre una sua scheda è aperta: quella scheda resta aperta.
- 🔢 Un numero su **Sicurezza**, ripetuto su **Amministrazione**, conta errori e avvisi dei [controlli di sicurezza](#security-tab).
- 📱 Su un telefono le schede mostrano solo le icone; il titolo della pagina indica la scheda aperta.

---

## ✏️ Modificare un'impostazione

### 🔓 1. Sbloccare la scheda

**Dove:** **Impostazioni › Amministrazione › Impostazioni globali**. Il pannello raggruppa le impostazioni per categoria.
Fai clic sull'**icona a lucchetto** (🔒) nell'intestazione.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Impostazioni globali" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 💾 2. Modificare e salvare

- Nulla viene scritto finché non fai clic su **Salva** accanto a un'impostazione o su **Salva tutto** nell'intestazione. **Annulla** e **Annulla tutto** ripristinano i valori salvati.
- **Ripristina valore predefinito** e **Ripristina tutti i valori predefiniti** inseriscono i predefiniti, pronti per essere salvati.
- I valori salvati si applicano subito, senza riavvio.

??? note "🔒 Blocco con modifiche non salvate — quando una finestra di dialogo chiede prima conferma"

    Fai clic sul lucchetto con modifiche non salvate: ti chiede se scartarle. **Annulla** mantiene le modifiche; **Scarta** ripristina i valori salvati e blocca la scheda.

??? tip "💻 Impostazioni mancanti — ricrearle dalla riga di comando"

    Ogni avvio del server ricrea le impostazioni mancanti con il loro valore predefinito. Per farlo senza riavviare, **nel terminale del server**, con lo [strumento da riga di comando](cli_tools.md):

    ```bash
    pipenv run ./dev.py user init-settings
    ```

    I valori che hai modificato vengono mantenuti.

---

## 📋 Cosa fa ogni impostazione

**Dove:** la categoria indicata della scheda **Impostazioni globali**, salvo dove la tabella dice altro.

| Dove | Impostazione | Predefinito | Cosa fa — quando modificarla |
|---|---|---|---|
| ⏳ Sessione | **Durata sessione** | 24 ore | Per quanto tempo gli utenti restano connessi. Riducila sui dispositivi condivisi. Un nuovo valore vale dal successivo accesso di ogni utente. |
| 🛡️ Sicurezza | **Registrazione** | Su invito | Chi può creare un account: **Aperta**, **Su invito** o **Chiusa**. **Aperta** lascia entrare chiunque raggiunga la pagina di accesso: evitala se l'istanza è raggiungibile da Internet. Modalità, avviso e `LIBREFOLIO_REGISTRATION`: [Chi può registrarsi](#registration). |
| 🛡️ Sicurezza | **Richiedi verifica email** | Disattivata | I nuovi account devono aprire un link inviato al loro indirizzo prima di poter accedere; il primo account non attende mai e gli account esistenti non sono interessati. Si attiva solo mentre l'email funziona e `LIBREFOLIO_PUBLIC_URL` può essere usato: fino ad allora l'interruttore è disabilitato. Vedi *Verifica email* in [Email](email.md). |
| 🔄 Processo di aggiornamento | **Scheduler abilitato** | Attivo | Attiva o disattiva gli aggiornamenti automatici di prezzi e tassi di cambio: [Scheduler dei dati di mercato](#market-data-scheduler). |
| 🧠 Memoria | **Dimensione massima file caricabile** | 10 MB | Il file più grande che gli utenti possono caricare, compresi i report del broker. Aumentala se un'esportazione di grandi dimensioni viene rifiutata. |
| **File › Avanzate** (non in questa scheda) | **Limite di spazio (MB)** | `0`, nessun limite | Il numero massimo di megabyte che l'istanza può occupare: è la linea di riferimento su cui viene tracciata la barra dello spazio di **File**. `0` significa nessun limite: la barra mostra allora il disco. Lo modifichi in quella barra, che solo gli amministratori vedono, non in questa scheda. `LIBREFOLIO_STORAGE_LIMIT_MB`, quando impostato, ha la precedenza e lo blocca ([Variabili d'ambiente](configuration.md)). Vedi [La barra dello spazio](backup_restore.md#space-used). |
| 🌍 Predefiniti | **Valuta predefinita** | `EUR` | La valuta in cui rendicontano i nuovi utenti. Prima del primo salvataggio decide `LIBREFOLIO_DEFAULT_CURRENCY` (sotto). |
| 🌍 Predefiniti | **Lingua predefinita** | `en` | 🇬🇧 `en`, 🇮🇹 `it`, 🇫🇷 `fr` o 🇪🇸 `es`. È anche la lingua delle email inviate a chi non ha ancora un account. Prima del primo salvataggio decide `LIBREFOLIO_DEFAULT_LANGUAGE` (sotto). |
| 🌍 Predefiniti | **Tema predefinito** | `auto` | ☀️ `light`, 🌙 `dark` o 🖥️ `auto`, che segue il dispositivo. |

**Nel file `.env`**, due variabili decidono, se impostate, solo finché non salvi l'impostazione per la prima volta: dal primo salvataggio ha la precedenza il tuo valore, anche quando è di nuovo quello predefinito (`EUR`, `en`). Vedi [Variabili d'ambiente](configuration_accounts.md#accounts).

```env
LIBREFOLIO_DEFAULT_CURRENCY=EUR
LIBREFOLIO_DEFAULT_LANGUAGE=en
```

I nuovi utenti partono dai tre valori predefiniti: la [Configurazione iniziale](../user/getting-started.md#welcome-setup) mostra lingua e valuta già precompilate. Modificare poi un predefinito non tocca le [Preferenze](../user/settings/preferences.md) degli utenti esistenti.

---

## 🚪 Chi può registrarsi {: #registration }

**Dove:** **Impostazioni globali › Sicurezza › Registrazione**, oppure la scheda [Utenti](users.md#registration), accanto a **Invita**: lì la modalità viene salvata subito, con conferma solo per **Aperta**.

| Modalità | Chi può creare un account |
|---|---|
| 🌐 **Aperta** | Chiunque raggiunga la pagina di accesso, con **Registrati qui**. |
| ✉️ **Su invito** (predefinita) | Solo chi ha un link di invito. Crea un link per persona dalla scheda [Utenti](users.md#invitations) o dalla [riga di comando](cli_tools.md#invite), e invialo. La pagina di accesso non mostra **Registrati qui**. |
| 🔒 **Chiusa** | Nessuno, nemmeno con un link di invito. La pagina di accesso non mostra **Registrati qui**. |

- 👑 Il primo account di una nuova istanza può sempre essere creato, qualunque sia la modalità: vedi l'avviso sotto.
- 🆕 Una nuova istanza parte con **Su invito**. Un'istanza aggiornata da una versione precedente mantiene la modalità che aveva: una che era **Aperta**, il precedente predefinito, resta **Aperta** finché non la cambi (**Ripristina valore predefinito** propone **Su invito**). Una volta che tutti hanno un account, scegli **Su invito** o **Chiusa**.
- ✉️ Un link di invito funziona una sola volta, per 7 giorni, e può rendere il nuovo account un amministratore. Con **Aperta** nessuno ne ha bisogno, ma un link assegna comunque il suo ruolo.
- 💻 Qualunque sia la modalità, la [riga di comando](cli_tools.md) può creare account con `user create`.
- 📏 Con un limite di utenti, nessuno può registrarsi senza invito una volta che l'istanza è piena: [Quando l'istanza è piena](configuration_accounts.md#user-limit).
- 🔒 **Nel file `.env`**, `LIBREFOLIO_REGISTRATION` fissa la modalità: il campo la mostra in entrambi i punti, non può essere modificato e dice *Impostato sul server da LIBREFOLIO_REGISTRATION: modificalo lì*. **Ripristina tutti i valori predefiniti** lo lascia invariato. Vedi [Account e registrazioni](configuration_accounts.md#accounts).
- ⬆️ Questa impostazione sostituisce l'interruttore **Abilita registrazione** delle versioni precedenti; l'aggiornamento mantiene la tua scelta: un interruttore attivo diventa **Aperta**, uno disattivo **Chiusa**.

!!! warning "🆕 Una nuova istanza: crea prima il tuo account"

    Finché il primo account non esiste, chiunque raggiunga la pagina di accesso può crearlo con **Registrati qui**, qualunque sia la modalità, compresa `LIBREFOLIO_REGISTRATION`, e quell'account diventa l'amministratore. Registrati appena il server è attivo, prima di renderlo raggiungibile da Internet. Dal secondo account in poi si applica la modalità: con **Su invito**, quella predefinita, la pagina di accesso non mostra più **Registrati qui**.

    Oppure crea il primo amministratore **nel terminale del server**, senza browser ([riga di comando](cli_tools.md)):

    ```bash
    pipenv run ./dev.py user create <username> <email> <password>
    ```

    Con Docker: `docker compose exec librefolio python dev.py user create <username> <email> <password>`.

    Oppure imposta `LIBREFOLIO_ADMIN_EMAIL` **nel file `.env`** prima del primo avvio: LibreFolio crea da sé l'amministratore, con un link di configurazione per te, e nessuno può registrarsi al suo posto ([L'amministratore iniziale](configuration_accounts.md#initial-admin)).

### 📢 L'avviso di registrazione aperta {: #open-registration-warning }

Mentre **Registrazione** è **Aperta**, un amministratore che apre LibreFolio a un indirizzo esterno alla rete locale legge, sopra le pagine dell'app:

*La registrazione è aperta e questa istanza è raggiungibile dall'esterno della tua rete locale: chiunque la trovi può creare un account.*

Il suo link, **Cambia chi può registrarsi**, apre **Impostazioni › Amministrazione › Impostazioni globali**. Quando `LIBREFOLIO_REGISTRATION` fissa la modalità, l'avviso indica invece quella variabile e non ha link: solo la configurazione del server (file `.env`) può cambiarla ([Account e registrazioni](configuration_accounts.md#accounts)).

- 👑 Solo gli amministratori lo vedono.
- 🌐 Decide il tuo browser, dal nome o dall'indirizzo IP nella barra degli indirizzi (la porta non conta). Nulla viene inviato al server e nulla verifica se l'istanza è davvero raggiungibile da Internet. Contano come locali, senza avviso:
    - `localhost` e ogni nome che termina in `.localhost`;
    - un nome senza punto, come `nas`, e ogni nome che termina in `.local`, `.lan`, `.home.arpa` o `.internal`;
    - gli indirizzi IPv4 di `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` e `100.64.0.0/10` (NAT carrier-grade, l'intervallo in cui Tailscale numera i suoi dispositivi);
    - l'indirizzo IPv6 `::1` e quelli di `fc00::/7` e `fe80::/10`; un indirizzo IPv4 scritto come IPv6, come `::ffff:192.168.1.10`, conta come l'indirizzo IPv4 che trasporta.

    Maiuscole e punto finale non cambiano nulla. Ogni altro indirizzo conta come esterno, compresi i nomi Tailscale che terminano in `.ts.net`: Tailscale Funnel può pubblicarli su Internet.
- ✖️ Il pulsante di chiusura lo nasconde finché la pagina non viene caricata di nuovo.
- 🔄 Scompare appena la modalità non è più **Aperta**: salvare **Registrazione** lo aggiorna subito.
- 🛡️ La scheda [Sicurezza](#security-tab) elenca lo stesso avviso tra i suoi rilevamenti finché resta valido, anche dopo che lo hai chiuso.

Come decide, per gli sviluppatori: [L'avviso di registrazione aperta](../developer/architecture/security.md#open-registration-warning).

---

## 🕐 Scheduler dei dati di mercato {: #market-data-scheduler }

Lo scheduler aggiorna da solo prezzi e tassi di cambio, anche quando nessuno è connesso:

- 💰 **Aggiornamento del prezzo corrente** — ogni pochi minuti, l'ultimo prezzo di ogni asset attivo con un provider di prezzi.
- 📊 **Sincronizzazione dello storico** — nei giorni e agli orari che scegli, i prezzi giornalieri di quegli asset e i tassi di ogni coppia FX con un provider, su almeno l'**Orizzonte retrospettivo**, per colmare le lacune. Se l'ultimo prezzo o tasso salvato è più vecchio, risale fino a quel giorno, per un massimo di un anno; un asset senza alcun prezzo salvato riceve solo l'orizzonte: lo scheduler non scarica mai uno storico completo. Le coppie con soli tassi manuali vengono ignorate.

Server spento o in sospensione all'orario di sincronizzazione: la sincronizzazione persa viene eseguita appena il server torna disponibile, senza attendere l'orario successivo. Un server spento per settimane colma l'intera lacuna.

### ⚙️ Configurare la pianificazione

**Dove:** **Impostazioni globali › Processo di aggiornamento › Configurazione della pianificazione › Configura…**, con la scheda sbloccata. La finestra di dialogo ha un proprio pulsante **Salva**.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Modale di configurazione dello scheduler" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

| Campo | Predefinito | Cosa imposta |
|---|---|---|
| **Fuso orario** | `UTC` | Il fuso orario degli orari e dei giorni sottostanti; accanto, l'orologio UTC del server. Prima del primo salvataggio della pianificazione decide `LIBREFOLIO_DEFAULT_TIMEZONE` **nel file `.env`**, se impostato; dal primo salvataggio ha la precedenza il tuo valore, anche quando è di nuovo `UTC` ([Variabili d'ambiente](configuration_accounts.md#accounts)). |
| **Aggiorna ogni** | 10 minuti | Con quale frequenza vengono aggiornati i prezzi correnti, da 1 a 1440 minuti. |
| **Orari di sincronizzazione** | `06:00`, `23:00` | Quando viene eseguita la sincronizzazione dello storico; **Aggiungi orario** aggiunge uno slot. |
| **Giorni di sincronizzazione** | Da lun a sab | I giorni della sincronizzazione dello storico. |
| **Orizzonte retrospettivo** | 14 giorni | Quanti giorni passati controlla almeno ogni sincronizzazione, da 1 a 365. Risale oltre, fino a un anno, quando l'ultimo prezzo o tasso salvato è più vecchio. |

Mantieni almeno un orario e un giorno. Una sincronizzazione dopo la chiusura dei mercati (ad esempio `22:00`) ottiene i dati più completi.

??? warning "🌍 Cambiare il fuso orario — i job si spostano nel tempo"

    Orari e giorni mantengono i loro valori ma contano nel nuovo fuso orario: i job vengono eseguiti in un altro momento. Seguono anche l'ora legale del fuso: `06:00` in `Europe/Rome` viene eseguito alle 05:00 UTC in inverno e alle 04:00 UTC in estate.

### 📜 Leggere il log dello scheduler

**Dove:** **Impostazioni globali › Processo di aggiornamento › Stato dello scheduler**. Solo gli amministratori leggono stato e log.

La riga mostra l'ultimo aggiornamento del prezzo corrente, con un punto per il suo esito. Mentre è in attesa un nuovo tentativo, una riga in più ne indica l'orario: **Non riuscito: prossimo tentativo alle …** dopo un aggiornamento non completato, altrimenti **Elementi in pausa ritentati alle …** per i prezzi differiti perché il loro provider era in pausa.
Fai clic sulla riga (o su **Dettagli…**): si apre il **Log di esecuzione dello scheduler**.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Modale del log dello scheduler" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- Ogni voce è un'esecuzione: job, orario, durata e quanti elementi hanno avuto successo. 🟢 **OK**: tutti, o nulla da fare; 🟡 **Parziale**: alcuni non riusciti, o differiti perché il loro provider è andato in pausa dopo troppe richieste; 🔴 **Errore**: nessuno riuscito e nessuno differito.
- Fai clic su una voce: ogni asset o coppia FX, il suo provider e i prezzi modificati (**Delta**). Passa il mouse su un errore per leggerlo per intero; doppio clic (pressione prolungata su un telefono) per copiarlo.
- Un elemento differito mostra un'icona di pausa e **Differito: provider in pausa**: passa il mouse sull'etichetta per leggere il messaggio del provider. La voce conta i differiti con ⏸, accanto a ✓ e ✗ (ad esempio `3/5 ✓ · 1 ⏸ · 1 ✗`), e **Riprova alle** nell'intestazione indica l'orario del nuovo tentativo.
- Filtra per job, stato o periodo, dall'ultima ora agli ultimi 30 giorni. Vengono conservate solo le esecuzioni più recenti.

---

## ⏸️ Pause dei provider {: #provider-pauses }

Quando un provider di prezzi o di tassi (Yahoo Finance, la Banca centrale europea…) risponde «troppe richieste» (HTTP 429), LibreFolio lo mette in pausa: finché la pausa non termina, nessuna richiesta lo raggiunge, né dallo [scheduler dei dati di mercato](settings.md#market-data-scheduler) né da un utente. Una pausa vale per ogni utente e ogni job del server.

Le pause sono attive per impostazione predefinita. `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS=0` le disattiva, come prima della versione 1.3.

**Dove:** **nel file `.env`** (o nell'ambiente del container). Questi sono i valori predefiniti:

```env
LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS=60
LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS=3600
```

| Variabile | Predefinito | Cosa fa |
| --- | --- | --- |
| `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS` | `60` | La prima pausa, in secondi, raddoppiata a ogni rifiuto consecutivo: un numero intero da `0` a `86400` (un giorno). `0` disattiva le pause. |
| `LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS` | `3600` | La pausa più lunga raggiunta dal raddoppio, in secondi: un numero intero da `1` a `86400`, non inferiore alla prima pausa mentre le pause sono attive. Il `Retry-After` di un provider può comunque richiedere di più, fino a un giorno. |

Riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`.

- Un valore che LibreFolio non può usare non arresta il server: il log contiene un errore ([Nel log](#provider-pauses-log)) e si applicano entrambi i predefiniti, 60 e 3600: le pause restano attive.
- Con le pause disattivate, ogni richiesta viene di nuovo inviata al provider; lo scheduler considera comunque differita una richiesta rifiutata ([sotto](#provider-pauses-effects)).

### ⏱️ Quanto dura una pausa {: #provider-pauses-length }

- **Il primo rifiuto** mette in pausa il provider per `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS`, 60 secondi per impostazione predefinita.
- **Ogni rifiuto consecutivo** raddoppia la pausa, fino a `LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS`. Con i predefiniti: 2 minuti, poi 4, 8, 16 e 32, poi un'ora a ogni ulteriore rifiuto. Le richieste rifiutate insieme contano come un solo rifiuto.
- **Un `Retry-After`**, quando il provider lo invia, è la pausa più breve che LibreFolio adotta: rispettato anche oltre la pausa più lunga, fino a un giorno.
- **Un extra casuale** fino al 10 % viene aggiunto a ogni pausa, mai oltre un giorno.
- **Quando una pausa termina**, una richiesta passa per provare il provider; le altre contano ancora come in pausa finché non ha un esito, al massimo un minuto. Una risposta termina la serie: il rifiuto successivo riparte dalla prima pausa. Lo stesso vale per un rifiuto che arriva, dalla fine della pausa precedente, dopo un intervallo superiore alla pausa più lunga.
- **Una pausa vale per l'intero provider**, tranne con il CSS Scraper: un sito che rifiuta mette in pausa solo le pagine di quel sito; gli altri siti vengono comunque letti.

### 👀 Chi attende e cosa vedi {: #provider-pauses-effects }

| Dove | Durante una pausa |
| --- | --- |
| 🕐 [Scheduler dei dati di mercato](settings.md#market-data-scheduler) | Gli asset e le coppie FX di un provider in pausa sono **differiti**: né aggiornati né non riusciti, e il loro job è **Parziale**. Il job viene eseguito di nuovo quando termina la prima di quelle pause, o al suo orario regolare se arriva prima. Come lo mostrano **Stato dello scheduler** e il **Log di esecuzione dello scheduler**: «Leggere il log dello scheduler», sopra. |
| 💰 Prezzi live, nell'elenco degli asset e nella pagina di un asset | L'ultimo prezzo memorizzato resta, senza nuovi messaggi. Quando ogni asset per cui la pagina effettua richieste ha il provider in pausa, la pagina richiede di nuovo da sola solo quando la prima di quelle pause è terminata; finché un provider risponde ancora, l'aggiornamento prosegue e LibreFolio non chiama quelli in pausa. Dopo un aggiornamento non riuscito, il successivo attende il doppio, e così via fino a dieci minuti, finché uno non funziona di nuovo. |
| 🔌 **Verifica configurazione**, nella finestra di dialogo dell'asset | ⚠️ *In pausa per troppe richieste fino alle …*, con l'orario in cui termina la pausa; il test viene comunque superato. Vedi [Collegare un provider di prezzi](../user/assets/create-edit.md). |
| 🔎 Ricerca asset | Un provider in pausa non restituisce risultati finché la pausa non termina; gli altri rispondono come al solito. |
| 💱 Tassi di cambio | Un provider in pausa conta come una rotta non riuscita: una coppia con un'altra rotta ottiene lì il suo tasso, come quando una banca centrale non risponde ([Configurazione provider](../user/fx/detail/provider.md)). Altrimenti lo scheduler differisce la coppia, come fa con un asset. |

### 💤 In memoria {: #provider-pauses-memory }

- **Ogni processo del server tiene le proprie pause in memoria.** Un riavvio le dimentica, compreso un deploy. Con più processi del server (`--workers N`), ciascuno apprende una pausa da un proprio rifiuto; l'immagine Docker ne esegue uno.

### 📋 Nel log {: #provider-pauses-log }

| Livello | Il log dice | Quando |
| --- | --- | --- |
| ⚠️ `warning` | `Provider refused for too many requests: paused`, con `domain` (`asset` o `fx`), `provider`, `scope` (il sito, con il CSS Scraper), `wait_s`, i secondi di pausa previsti, e `retry_after`, l'attesa richiesta dal provider, se presente | Un provider ha rifiutato una richiesta |
| ℹ️ `info` | `Provider answering again after a pause`, con `refusals`, i rifiuti consecutivi precedenti | La prima risposta dopo una pausa |
| ❌ `error` | `Provider pause settings cannot be used: the defaults apply`, con `variable`, `code` (`PROVIDER_COOLDOWN_BASE_INVALID` o `PROVIDER_COOLDOWN_MAX_INVALID`) e `reason` | Una delle due variabili ha un valore che non può essere usato: una volta per processo del server, la prima volta che LibreFolio sta per chiamare un provider |

A livello `DEBUG`, `Provider call skipped: paused after too many requests`, con `wait_s`, contrassegna ogni richiesta che una pausa ha impedito di inviare. Le righe dello scheduler, `Scheduler: current-price refresh` e `Scheduler: history sync`, indicano gli elementi differiti in `deferred`, con `retry_at`.

---

## 🗄️ Cache del server {: #server-caches }

LibreFolio tiene in memoria le risposte recenti dei provider e i risultati calcolati.

**Dove:** **Impostazioni globali › Memoria › Stato cache**, alla fine della categoria. Il pannello elenca ogni cache con **Dimensione / Max** e **TTL** (per quanto tempo viene conservata una voce). Fai clic sull'intestazione di una colonna per ordinare; **Aggiorna** aggiorna i numeri.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="cache-panel" alt="Pannello delle cache del server in Impostazioni globali (categoria Memoria)">
</div>

Il pannello mostra i numeri anche con la scheda bloccata. Con la scheda sbloccata, **Svuota** svuota una cache e **Svuota tutto** tutte, per forzare dati aggiornati senza riavvio. Anche un riavvio svuota ogni cache.

!!! warning "Svuotare una cache rallenta il recupero successivo"

    Entrambe le azioni chiedono prima conferma. Dopo uno svuotamento, la successiva richiesta di quei dati torna ai provider: aspettati un rallentamento simile a un riavvio del server finché le cache non si riempiono di nuovo.

??? note "🧵 Più worker — quando il server viene eseguito con `--workers`"

    Ogni processo worker ha le proprie cache. Il pannello mostra e svuota quelle del worker che ha risposto; riavvia il server per svuotarle tutte.

---

## 🛡️ Sicurezza {: #security-tab }

**Dove:** **Impostazioni › Amministrazione › Sicurezza**. Solo gli amministratori hanno la scheda. Controlla come è configurata l'istanza ed elenca per prime le cose che richiedono la tua attenzione.
Non è la categoria 🛡️ **Sicurezza** delle Impostazioni globali, che contiene **Registrazione** e **Richiedi verifica email**.

### 🚦 Cosa elenca {: #security-findings }

Ogni rilevamento indica ciò che non va, con icona e colore: ❌ un **errore**, ⚠️ un **avviso** o ℹ️ un'**informazione**. Prima gli errori, poi gli avvisi, poi le informazioni; a pari gravità, l'ordine di questa tabella.

| Controllo | Un rilevamento quando | Il suo link |
|---|---|---|
| Chiave di firma della sessione | ℹ️ La chiave è casuale: ogni riavvio disconnette tutti; imposta `JWT_SECRET` per restare connessi. ⚠️ La chiave è più corta di 32 caratteri. ❌ Il suo `JWT_SECRET_FILE` non può essere letto | — |
| Segreti impostati due volte | ⚠️ Un segreto è impostato sia direttamente sia tramite la sua variabile `_FILE`: vince il valore diretto | — |
| Chiave dell'istanza | ❌ Non può essere usata. ⚠️ La sua cartella o il suo file sono accessibili ad altri utenti | — |
| Cookie di sessione | ⚠️ `SESSION_COOKIE_SECURE=never`: il cookie viaggia anche su HTTP in chiaro | — |
| Indirizzo del visitatore | ⚠️ Dall'avvio, le richieste sono arrivate tramite un reverse proxy di cui LibreFolio non si fida: i limiti per indirizzo del visitatore non si applicano a esse. ℹ️ Dall'avvio, le intestazioni di inoltro provenienti da un indirizzo pubblico sono state ignorate. Cosa fare: [L'indirizzo del visitatore](connection_proxy.md#client-address) | — |
| Livello di log | ℹ️ `DEBUG` o `TRACE` | — |
| Modalità test | ❌ `LIBREFOLIO_TEST_MODE` è attiva al di fuori delle esecuzioni di test di LibreFolio: vengono serviti provider di dati che esistono solo per i test e i dati sono conservati nella cartella dei dati di test | — |
| Limite di caricamento di un ripristino | ❌ `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` non può essere usato (un numero intero di megabyte, `0` per nessun limite): i caricamenti di ripristino vengono rifiutati finché non viene corretto. Superato con un limite, ad esempio *Un ripristino accetta archivi fino a 500 MB.*, o senza alcun limite | — |
| Dimensione decompressa di un ripristino | ❌ `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` non può essere usato (un numero intero di megabyte, `0` per nessun limite): i controlli di ripristino vengono rifiutati finché non viene corretto. Superato con un limite, ad esempio *Un controllo di ripristino accetta archivi che si decomprimono fino a 4000 MB.*, o senza alcun limite | — |
| Accessi non riusciti | ⚠️ Il limite è disattivato: `LIBREFOLIO_LOGIN_LIMIT=off` | — |
| Server email | ❌ Un valore `LIBREFOLIO_SMTP_*` non può essere usato: l'email resta disattivata finché non viene corretto | **Apri la scheda Email** |
| Crittografia email | ⚠️ Le email, i loro link e la password SMTP viaggiano senza crittografia verso un server esterno alla tua rete locale | **Apri la scheda Email** |
| Link nelle email | ℹ️ L'email funziona, ma `LIBREFOLIO_PUBLIC_URL` non è impostato. ⚠️ `LIBREFOLIO_PUBLIC_URL` non può essere usato all'inizio di un link | **Apri la scheda Email** |
| Segreti dei plugin | ❌ I segreti dei plugin a livello di istanza non possono essere letti con la chiave dell'istanza | **Apri le impostazioni dei plugin**, in **Impostazioni › Plugin** |
| Registrazione aperta, verificata dal tuo browser | ⚠️ **Registrazione** è **Aperta** e hai raggiunto LibreFolio a un indirizzo esterno alla tua rete locale, come per [l'avviso sopra le pagine](#open-registration-warning) | **Cambia chi può registrarsi**, in **Impostazioni globali**. Nessuno quando `LIBREFOLIO_REGISTRATION` imposta la modalità: il rilevamento indica invece quella variabile |
| Uno script bloccato, verificato dal tuo browser | ⚠️ Uno script che LibreFolio non ha inviato, aggiunto da un proxy, da una CDN o da un'estensione del browser, è stato bloccato in questa scheda del browser: il rilevamento ne indica le origini. Scompare quando chiudi la scheda. Non si risolve sul server, ma nel proxy, nella CDN o nell'estensione: [Uno script che non hai inviato](configuration_security.md#csp-blocked-script) | — |

Ogni riga ha un pulsante di aiuto, scelto in base a chi può risolvere il controllo:

- 📖 **Guida**: puoi risolverlo da solo, sul server. Il pulsante, mostrato anche sui controlli superati, apre la pagina di questa guida che spiega quel controllo, in una nuova scheda e nella tua lingua quando è tradotta.

Un controllo senza una pagina propria e senza supporto non ha un pulsante.

I rilevamenti senza link si risolvono nella configurazione del server (**file `.env`**) e richiedono un riavvio: cosa fare per ciascuno è nella tabella dei «Controlli all'avvio» in [Configurazione](configuration.md), dove il log del server riporta gli stessi controlli.

### 🔢 Il numero sulla scheda {: #security-badge }

**Sicurezza** mostra quanti errori e avvisi elenca; **Amministrazione** mostra lo stesso numero, visibile da ogni scheda delle Impostazioni. Le informazioni sono elencate ma mai conteggiate: con sole informazioni non c'è alcun numero, e la scheda non dice nemmeno *Nulla richiede la tua attenzione.*

Fuori dalle Impostazioni, lo stesso conteggio ti segue su ogni pagina, come un punto sulla riga di connessione in fondo alla barra laterale: rosso con almeno un errore, ambra con soli avvisi, nessuno con sole informazioni. Fai clic sulla riga: dopo il suo motivo, i dettagli rimandano a questa scheda con il conteggio, ad esempio **2 avvisi di sicurezza**, errori inclusi. Su un telefono, anche il pulsante del menu porta il punto. Com'è fatto: [Avvisi di sicurezza per gli amministratori](../user/connection-security.md#security-warnings).

### 🔄 Quando esegue i controlli {: #security-refresh }

LibreFolio legge i controlli una volta, appena si apre nel tuo browser, qualunque sia la pagina: li richiede la riga di connessione della barra laterale, quindi punto e numero sulla scheda sono già presenti quando apri **Impostazioni**. Se quella lettura fallisce, aprire **Impostazioni** la ritenta. I controlli restano quelli mentre usi l'app: dopo aver modificato la configurazione del server (file `.env`) e riavviato, fai clic su **Controlla di nuovo**, in cima alla scheda, o ricarica la pagina. Il rilevamento sulla registrazione aperta segue **Registrazione** all'istante: salvarla in Impostazioni globali aggiorna elenco, numero e punto.

- ⏳ Fino alla prima risposta, la scheda mostra righe segnaposto.
- ⚠️ Quando i controlli non possono essere letti, la scheda dice *Non è stato possibile caricare i controlli di sicurezza.*, con **Riprova**. Dopo un **Controlla di nuovo** non riuscito, gli ultimi risultati restano elencati sotto.

### ✅ Controlli superati {: #security-passed }

Senza rilevamenti, la scheda dice *Nulla richiede la tua attenzione.* Sotto i rilevamenti, una sezione comprimibile, **N controlli superati**, elenca i controlli superati, ciascuno con la propria frase (ad esempio *Le sessioni sono firmate con una chiave impostata dall'amministratore.*): fai clic per espanderla. L'email disattivata, o inviata senza crittografia a un server della tua rete, conta come superata e lo dice lì.

---

## 🔗 Correlati

- 📝 **[Variabili d'ambiente](configuration.md)** — Le impostazioni che risiedono invece nel file `.env`
- 👥 **[Utenti e inviti](users.md)** — Gli account dell'istanza, gli inviti e i link per reimpostare la password
- 👤 **[Preferenze utente](../user/settings/preferences.md)** — Cosa può cambiare ogni utente per sé
- 🧑‍💻 Per gli sviluppatori: **[Sistema delle impostazioni](../developer/architecture/settings.md)**,
  **[Registro delle cache](../developer/architecture/settings_cache.md)**,
  **[Scheduler dei dati di mercato](../developer/backend/scheduler.md)** e
  **[Controlli di configurazione](../developer/architecture/security.md#configuration-checks)**
