# ℹ️ Informazioni

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="about" alt="Informazioni">
</div>

La scheda **Informazioni** mostra:

- La **versione** attuale di LibreFolio
- La **licenza** (AGPL-3.0)
- I link al **repository GitHub** e alla **documentazione**
- Una scheda **Supporta LibreFolio** con il link del caffè e i pulsanti di condivisione — vedi [Supporta LibreFolio](#support-librefolio) più sotto
- Una griglia di **informazioni di sistema** (versione di Python, sistema operativo, modalità di distribuzione — Docker o locale — browser, viewport, tema e lingua) con un pulsante **copia per la segnalazione** che raccoglie questi dettagli in una segnalazione di bug pronta da incollare
- I **plugin installati**: elenchi comprimibili dei provider di prezzi degli asset, dei provider di tassi FX, dei plugin di importazione dai broker e degli indicatori di segnale rilevati all'avvio, seguiti dalla **Diagnostica plugin**

---

## ❤️ Supporta LibreFolio {: #support-librefolio }

La scheda **Supporta LibreFolio** offre due modi per aiutare il progetto:

- **Buy Me a Coffee** apre la pagina Buy Me a Coffee del progetto in una nuova scheda. Lo stesso link si trova
  nell'intestazione della pagina (l'icona del caffè, con la sua etichetta sugli schermi più larghi) e nel
  menu **Guida e supporto**.
- Sotto **Oppure condividi**, un pulsante per ogni social network: **X**, **Reddit**, **Facebook**,
  **Instagram** e **TikTok**.

Un pulsante di condivisione apre una finestra di dialogo **Condividi su …** con un **Messaggio suggerito** scritto per quel
social network, nella lingua dell'interfaccia. Qualunque sia la lingua, ogni messaggio termina con gli
stessi cinque hashtag: `#LibreFolio #OpenSource #SelfHosted #PortfolioTracker #PersonalFinance`.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="support" data-name="social-share-modal" alt="Finestra di dialogo Condividi su Reddit con il titolo suggerito, un messaggio che termina con i cinque hashtag, e Copia e vai">
</div>

**Copia e vai** copia il messaggio, seguito dal link al sito web pubblico del progetto, e
apre il social network in una nuova scheda: LibreFolio resta aperto nella propria scheda. Ogni social network accetta
una quantità diversa di contenuto preparato, e la finestra di dialogo spiega cosa aspettarsi prima che tu faccia clic:

| Social network | Cosa si apre |
|---|---|
| **X** | Un nuovo post con il messaggio e il link del progetto già compilati. |
| **Reddit** | Un nuovo post di testo, con il **Titolo suggerito** come titolo e il messaggio come corpo. Se Reddit lascia il corpo vuoto, incolla il testo che hai appena copiato. |
| **Facebook** | Un post con la sola anteprima del link: incolla il testo copiato nel messaggio del post. |
| **Instagram** | Instagram stesso, che non può preparare un post da un link: scegli **Crea** (+), seleziona una foto o un video, poi incolla la didascalia copiata. |
| **TikTok** | La pagina di caricamento di TikTok (accedi se richiesto): seleziona il tuo video, poi incolla la didascalia copiata. |

Se il testo non può essere copiato, la finestra di dialogo lo segnala e ti chiede di consentire l'accesso agli appunti. Se il
browser blocca la nuova scheda, la finestra di dialogo indica che il testo è stato copiato ma che non è stato possibile aprire il sito, e ti chiede di consentire i pop-up. LibreFolio non pubblica mai nulla per te: il post è
tuo, da rivedere e pubblicare sul social network.

### ☕ Il popup delle donazioni {: #donation-popup }

Ogni tanto, subito dopo aver effettuato l'accesso, LibreFolio ti ricorda che puoi sostenere il
progetto, con lo stesso link del caffè e gli stessi pulsanti di condivisione.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="support" data-name="donation-popup" alt="Popup delle donazioni dopo l'accesso, con Buy Me a Coffee, i cinque pulsanti di condivisione e Più tardi">
</div>

---

## 🧩 Diagnostica plugin

Il pannello comprimibile **Diagnostica plugin** riporta lo stato di salute dei quattro registri dei plugin — **Asset**
(provider di prezzi), **FX** (provider di tassi), **BRIM** (importatori dai broker) e **Segnali**
(indicatori) — e, sotto di essi, quello degli **Strumenti**.

Ogni registro è contrassegnato come **Tutti caricati** (verde) oppure elenca i **plugin che non è stato possibile importare** (rosso), con il nome del file e l'errore sottostante. Se un provider, un importatore o un indicatore che ti aspettavi manca nel resto dell'applicazione, questo pannello ti dice perché — un plugin che non si carica all'avvio semplicemente non viene registrato.
<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="about-plugin-diagnostics" alt="Diagnostica plugin comprimibile nella scheda Informazioni">
</div>

### 🧰 Strumenti e diagnostica degli strumenti {: #tool-diagnostics }

Sotto i registri, il pannello **Strumenti** elenca il catalogo degli [Strumenti](../tools/index.md). È
di sola lettura — non viene eseguito alcun calcolo, sondaggio o riparazione — e si carica solo quando apri
**Diagnostica plugin**; **Ricarica** lo rilegge. Per ogni strumento vedi il nome e la descrizione,
un link **Documentazione**, il suo codice e `Version: <contract_version>`, e se un'interfaccia compatibile è inclusa
nel frontend che stai eseguendo. La versione dell'implementazione non è mostrata
qui, e la coppia di versioni `Backend/API · UI` appare solo sulle schede della pagina Strumenti e
nell'intestazione di uno strumento aperto.

Apri **Diagnostica degli strumenti** per caricare uno snapshot del processo server che ha risposto:

- l'**Ambito dello snapshot** e l'**identificatore del processo API**;
- lo **Snapshot del pool di esecuzione**: se il pool è disponibile, i job attivi, in coda, in attesa,
  completati e falliti, e le corsie degradate;
- gli **Strumenti caricati in questo processo API**, ciascuno con nome, codice e versione del contratto, e
  gli eventuali **Errori di rilevamento**;
- i **Limiti effettivi della piattaforma**, in un pannello comprimibile a parte.

Lo snapshot descrive un singolo processo server, non l'intera istanza, e non si aggiorna da solo:
ricaricalo per rileggerlo.

<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="about-tool-diagnostics" alt="Pannello Strumenti nella Diagnostica plugin, con l'allocatore PAC e la Diagnostica degli strumenti aperta">
</div>

---

## 📜 Modale del changelog {: #changelog-modal }

La **modale del changelog** in-app mostra il file `CHANGELOG.md` incluso. Puoi raggiungerla da due punti:

- il **numero di versione in fondo alla barra laterale** (qualsiasi pagina), e
- l'**etichetta della versione subito sotto il titolo di questa pagina Informazioni** (Impostazioni → Informazioni).

- Un **pannello pieghevole per ogni release** — all'inizio è aperta solo la release più recente; anche le sezioni e le sotto-sezioni si piegano.
- Un **indice delle versioni** a chip lungo la parte superiore: facendo clic su una versione la si espande e si scorre direttamente ad essa.
- Una **casella di ricerca** che scende dentro le pieghe: le sezioni corrispondenti si aprono automaticamente, e le chip dei risultati cliccabili saltano al punto esatto.
<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="changelog-modal-search" alt="Ricerca nella modale del changelog che apre le pieghe corrispondenti">
</div>

- Pulsanti **Espandi tutto / Comprimi tutto**, e un link al file del changelog su GitHub.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="changelog-modal" alt="Modale del changelog con release pieghevoli e ricerca">
</div>

### 🔄 Verifica degli aggiornamenti

L'intestazione della modale ha anche un pulsante **Verifica aggiornamenti**. Chiede al server quale versione è
in esecuzione, rilegge da GitHub l'ultima release **stabile** (invece di riutilizzare il risultato
che il controllo automatico conserva per un'ora), e confronta le due. Una release più recente conta solo
quando la sua immagine Docker è disponibile sul registry, quindi una release la cui build è ancora in corso
non viene ancora proposta — vedi [Notifiche di aggiornamento](../../admin/index.md#update-notifications).

Un controllo avviato qui ti dice sempre com'è andata:

- Se LibreFolio è **aggiornato**, appare un toast di conferma, con la versione rilevata online.
- Se GitHub non ha **nessuna release stabile**, o l'**immagine Docker di una release più recente non è ancora disponibile**,
  un avviso lo segnala.
- Se il controllo **fallisce** — per esempio quando GitHub o il registry non sono raggiungibili — un errore
  ti chiede di riprovare. Un controllo fallito non riporta mai che sei aggiornato.
- Se esiste una release più recente e sei un **admin**, la modale **Nuova versione disponibile** si apre
  subito, sopra il changelog: versione attuale e più recente affiancate, con **Come aggiornare**
  (la [guida all'aggiornamento](../installation.md#updating)) e **Note di rilascio su GitHub**. Puoi
  chiuderla con **Ricordamelo più tardi** (ti verrà ricordato al prossimo accesso) o
  **Salta questa versione** (il controllo automatico non chiede più per quella release; un controllo avviato
  qui la mostra comunque). Gli admin vengono anche verificati automaticamente all'accesso — vedi
  [Notifiche di aggiornamento](../../admin/index.md#update-notifications) per il flusso lato admin.
- Se esiste una release più recente e **non sei un admin**, la finestra di dialogo **Aggiornamento disponibile — contatta un amministratore** elenca gli **amministratori** dell'istanza — con gli indirizzi e-mail quando disponibili, ciascuno con un link mailto e un pulsante di copia — così sai a chi chiedere l'aggiornamento. I non admin non vengono mai verificati automaticamente.

---

## 🔗 Correlati

- ⚙️ **[Panoramica delle impostazioni](index.md)** — Riepilogo delle impostazioni generali
- 👤 **[Profilo](profile.md)** — Nome utente, email, avatar, password
- 🎛️ **[Preferenze utente](preferences.md)** — Lingua, valuta di base e tema
- 🛡️ **[Impostazioni globali](../../admin/settings.md)** — Opzioni dell'amministratore e scheduler
