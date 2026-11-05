# ℹ️ Informazioni

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="about" alt="Informazioni">
</div>

La scheda **Informazioni** mostra:

- La **versione** corrente di LibreFolio
- La **licenza** (AGPL-3.0)
- I link al **repository GitHub** e alla **documentazione**
- Una scheda **Support LibreFolio** con il link al caffè e i pulsanti di condivisione — vedi [Support LibreFolio](#support-librefolio) qui sotto
- Una scheda **Note legali** — vedi [Note legali](#legal-notice) qui sotto
- Una griglia di **informazioni di sistema** (versione di Python, sistema operativo, modalità di distribuzione — Docker o locale — browser, viewport, tema e lingua) con un pulsante **copia per la segnalazione** che raccoglie questi dettagli in una segnalazione di bug pronta da incollare
- I **plugin installati**: elenchi comprimibili dei provider dei prezzi degli asset, dei provider dei tassi di cambio, dei plugin di importazione dei broker e degli indicatori di segnale rilevati all'avvio, seguiti da **Diagnostica plugin**

---

## ❤️ Support LibreFolio {: #support-librefolio }

La scheda **Support LibreFolio** offre due modi per aiutare il progetto:

- **Buy Me a Coffee** apre la pagina Buy Me a Coffee del progetto in una nuova scheda. Lo stesso link si trova
  nell'intestazione della pagina (l'icona del caffè, con la sua etichetta sugli schermi più larghi), nel
  menu **Aiuto e supporto** e in cima alle pagine di accesso.
- Sotto **Oppure condividi**, un pulsante per ogni social network: **X**, **Reddit**, **Facebook**,
  **Instagram** e **TikTok**.

Un pulsante di condivisione apre una finestra di dialogo **Condividi su …** con un **Messaggio suggerito** scritto per quella
rete, nella lingua dell'interfaccia. Qualunque sia la lingua, ogni messaggio termina con
gli stessi cinque hashtag: `#LibreFolio #OpenSource #SelfHosted #PortfolioTracker #PersonalFinance`.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="support" data-name="social-share-modal" alt="Finestra di dialogo Condividi su Reddit con il titolo suggerito, un messaggio che termina con i cinque hashtag e Copia e vai">
</div>

**Copia e vai** copia il messaggio, seguito dal link al sito web pubblico del progetto, e
apre il social network in una nuova scheda: LibreFolio resta aperto nella propria scheda. Ogni rete accetta
una quantità diversa di contenuto preparato, e la finestra di dialogo spiega cosa aspettarsi prima che tu faccia clic:

| Rete | Cosa si apre |
|---|---|
| **X** | Un nuovo post con il messaggio e il link del progetto già compilati. |
| **Reddit** | Un nuovo post testuale, con il **Titolo suggerito** come titolo e il messaggio come corpo. Se Reddit lascia il corpo vuoto, incolla il testo che hai appena copiato. |
| **Facebook** | Un post con la sola anteprima del link: incolla il testo copiato nel messaggio del post. |
| **Instagram** | Instagram stesso, che non può preparare un post da un link: scegli **Crea** (+), seleziona una foto o un video, poi incolla la didascalia copiata. |
| **TikTok** | La pagina di caricamento di TikTok (accedi se richiesto): seleziona il tuo video, poi incolla la didascalia copiata. |

Se il testo non può essere copiato, la finestra di dialogo lo dice e ti chiede di consentire l'accesso agli appunti. Se il
browser blocca la nuova scheda, la finestra di dialogo dice che il testo è copiato ma il sito non è stato
aperto, e ti chiede di consentire i pop-up. LibreFolio non pubblica mai nulla per te: il post è
tuo da rivedere e pubblicare sul social network.

### ☕ Il popup di donazione {: #donation-popup }

Ogni tanto, subito dopo l'accesso, LibreFolio ti ricorda che puoi sostenere il
progetto, con lo stesso link al caffè e gli stessi pulsanti di condivisione.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="support" data-name="donation-popup" alt="Popup di donazione dopo l'accesso, con Buy Me a Coffee, i cinque pulsanti di condivisione e Magari più tardi">
</div>

---

## ⚖️ Note legali {: #legal-notice }

La scheda **Note legali** contiene una breve avvertenza: LibreFolio ti aiuta a seguire i tuoi investimenti,
e non costituisce consulenza finanziaria. Se la tua istanza le prevede, la scheda collega anche i suoi
**Termini di servizio** e la sua **Informativa sulla privacy**: ciascuno si apre in una nuova scheda.

Trovi la stessa avvertenza sotto la scheda della pagina di benvenuto. Una versione più breve, su una riga con gli
stessi link, si trova sotto la scheda di ogni pagina di accesso e in fondo alla barra laterale, sotto il
numero di versione, mentre la barra laterale è espansa. Anche ogni testo che copi con
[AI Export](../ai-export/index.md) riporta l'avvertenza, verso la fine e senza i link.

---

## 🧩 Diagnostica plugin

Il pannello comprimibile **Diagnostica plugin** riporta lo stato di salute dei quattro registri dei plugin — **Asset**
(provider dei prezzi), **FX** (provider dei tassi di cambio), **BRIM** (importatori di broker) e **Segnali**
(indicatori) — e, sotto di essi, degli **Strumenti**.

Ogni registro è contrassegnato come **Tutto caricato** (verde) oppure elenca i **plugin che non è stato possibile importare** (rosso), con il nome del file e l'errore sottostante. Se un provider, un importatore o un indicatore che ti aspettavi manca dal resto dell'applicazione, questo pannello ti dice perché: un plugin che non si carica all'avvio semplicemente non viene registrato.
<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="about-plugin-diagnostics" alt="Pannello comprimibile Diagnostica plugin nella scheda Informazioni">
</div>

### 🧰 Strumenti e diagnostica degli strumenti {: #tool-diagnostics }

Sotto i registri, il pannello **Strumenti** elenca il catalogo degli [Strumenti](../tools/index.md). È
di sola lettura — non viene eseguito alcun calcolo, verifica o riparazione — e si carica solo quando apri
**Diagnostica plugin**; **Ricarica** lo rilegge. Per ogni strumento vedi il nome e la descrizione,
un link **Documentazione**, il suo codice e `Version: <contract_version>`, e se un'interfaccia compatibile
è inclusa nel frontend che stai usando. La versione dell'implementazione non è mostrata
qui, e la coppia di versioni `Backend/API · UI` appare solo sulle schede della pagina Strumenti e
nell'intestazione di uno strumento aperto.

Apri **Diagnostica strumenti** per caricare un'istantanea del processo server che ha risposto:

- l'**Ambito dell'istantanea** e l'**identificatore del processo API**;
- l'**Istantanea del pool di esecuzione**: se il pool è disponibile, i job attivi, in coda, in attesa,
  completati e falliti, e le corsie degradate;
- gli **Strumenti caricati in questo processo API**, ciascuno con nome, codice e versione del contratto, ed
  eventuali **Errori di rilevamento**;
- i **Limiti effettivi della piattaforma**, in un pannello comprimibile a sé.

L'istantanea descrive un singolo processo server, non l'intera istanza, e non si aggiorna da sola:
ricaricala per rileggerla.

<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="about-tool-diagnostics" alt="Pannello Strumenti in Diagnostica plugin, con l'allocatore PAC e Diagnostica strumenti aperti">
</div>

---

## 📜 Modale del changelog {: #changelog-modal }

La **modale del changelog** integrata nell'app mostra il changelog incluso in LibreFolio, nella lingua della tua interfaccia. Puoi raggiungerla da due punti:

- il **numero di versione in fondo alla barra laterale** (qualsiasi pagina), e
- l'**etichetta della versione subito sotto il titolo di questa pagina Informazioni** (Impostazioni → Informazioni).

Ogni release è mostrata nella tua lingua quando la sua traduzione è disponibile; una release non ancora tradotta appare in inglese, contrassegnata da una piccola etichetta **Non ancora tradotta**.

- Un **pannello comprimibile per release** — solo la release più recente si apre all'inizio; anche sezioni e sotto-sezioni si comprimono.
- Un **indice delle versioni** a chip nella parte superiore: facendo clic su una versione questa si espande e la pagina scorre direttamente fino ad essa.
- Un **campo di ricerca** che scende dentro i pannelli: le sezioni corrispondenti si aprono automaticamente, e i chip dei risultati cliccabili portano al punto esatto.
<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="changelog-modal-search" alt="Ricerca nella modale del changelog che apre i pannelli corrispondenti">
</div>

- Pulsanti **Espandi tutto / Comprimi tutto**, e un link al file del changelog su GitHub.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="changelog-modal" alt="Modale del changelog con release comprimibili e ricerca">
</div>

### 🔄 Controllo degli aggiornamenti

L'intestazione della modale ha anche un pulsante **Controlla aggiornamenti**. Questo chiede al server quale versione è
in esecuzione, rilegge da GitHub l'ultima release **stabile** (invece di riutilizzare il risultato
che il controllo automatico conserva per un'ora) e confronta le due. Una release più recente viene considerata solo
quando la sua immagine Docker è disponibile nel registry, quindi una release la cui build è ancora in corso
non viene ancora proposta — vedi [Notifiche di aggiornamento](../../admin/index.md#update-notifications).

Un controllo avviato qui ti dice sempre com'è andato:

- Se LibreFolio è **aggiornato**, appare un toast di conferma, con la versione rilevata online.
- Se GitHub **non ha release stabili**, o l'**immagine Docker di una release più recente non è ancora disponibile**,
  un avviso lo segnala.
- Se il controllo **fallisce** — per esempio quando GitHub o il registry non sono raggiungibili — un errore
  ti chiede di riprovare. Un controllo fallito non riporta mai che sei aggiornato.
- Se esiste una release più recente e sei un **amministratore**, la modale **Nuova versione disponibile** si apre
  subito, sopra il changelog: versione corrente e ultima versione affiancate, con **Come aggiornare**
  (la [guida all'aggiornamento](../installation.md#updating)) e **Note di rilascio su GitHub**. Puoi
  chiuderla con **Ricordamelo più tardi** (ti verrà ricordato al prossimo accesso) oppure
  **Salta questa versione** (il controllo automatico non ti avviserà più per quella release; un controllo avviato
  qui la mostra comunque). Gli amministratori vengono anche verificati automaticamente all'accesso — vedi
  [Notifiche di aggiornamento](../../admin/index.md#update-notifications) per il flusso lato amministratore.
- Se esiste una release più recente e **non sei un amministratore**, la finestra di dialogo **Aggiornamento disponibile — contatta un amministratore** elenca gli **amministratori** dell'istanza — con gli indirizzi e-mail quando disponibili, ciascuno con un link mailto e un pulsante di copia — così sai a chi chiedere l'aggiornamento. I non amministratori non vengono mai verificati automaticamente.

### ✨ Novità dopo un aggiornamento {: #whats-new }

Quando LibreFolio è stato aggiornato dopo la tua ultima visita, la volta successiva che lo apri una
finestra **Novità in LibreFolio** mostra cosa è cambiato: la parte del changelog relativa a ogni versione
rilasciata dall'ultima versione che hai visto. Se il tuo account è stato creato prima del periodo coperto da questa finestra, mostra la parte
della versione attualmente in esecuzione.

- Ogni parte è nella lingua della tua interfaccia quando la sua traduzione è pronta; altrimenti è in inglese,
  contrassegnata **Non ancora tradotta**, come nel changelog.
- **Changelog completo** apre il changelog completo su GitHub, in una nuova scheda.
- **Ho capito** chiude la finestra, e così fanno <kbd>Esc</kbd> e un clic all'esterno. Non ricompare
  fino al prossimo aggiornamento. Se LibreFolio non riesce a registrare che l'hai chiusa, per esempio perché
  la connessione è caduta, la finestra ricompare la volta successiva che apri LibreFolio.
- Attende che non ci siano guide né altre finestre aperte, e viene prima del
  [popup di donazione](#donation-popup) e dell'avviso di aggiornamento.
- Un nuovo account non la vede mai: parte dalla versione con cui è stato creato.

---

## 🔗 Correlati

- ⚙️ **[Panoramica delle impostazioni](index.md)** — Riepilogo delle impostazioni generali
- 👤 **[Profilo](profile.md)** — Nome utente, email, avatar, password
- 🎛️ **[Preferenze utente](preferences.md)** — Lingua, valuta di base e tema
- 🛡️ **[Impostazioni globali](../../admin/settings.md)** — Opzioni amministratore e scheduler
