# 🧙 Come importare le transazioni

La **Procedura guidata di importazione** trasforma i report che scarichi dal tuo broker in
transazioni. Controlli ciò che ha letto e risolvi i suoi dubbi; nulla viene salvato finché non premi
**Salva tutto**.

---

## 🚀 Guida passo per passo

1. Esporta un report delle transazioni dal tuo broker: la sua pagina in **[Broker supportati](index.md)**
   indica quale file.
2. Nella pagina **[Transazioni](../index.md)**, clicca **Importa** (:material-file-upload:).
3. Trascina il report nella procedura guidata, assegnalo al suo broker e segui i passaggi seguenti.
4. Clicca **Importa N transazioni**: le righe si aprono nel workspace bulk, non ancora salvate.
5. Dagli un'ultima occhiata e clicca **Salva tutto**.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Modale di importazione rapida" alt="Modale di importazione rapida">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Passaggio 1: Carica il file del report" alt="Passaggio 1 della procedura guidata">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Passaggio 2: Seleziona i file e il parser" alt="Passaggio 2 della procedura guidata">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Passaggio 3: Analisi e parsing" alt="Passaggio 3 della procedura guidata">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🗂️ Risoluzione degli asset" alt="Risoluzione degli asset">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Rilevamento dei duplicati" alt="Rilevamento dei duplicati">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Passaggio 4: Revisione e importazione" alt="Revisione e importazione">
</div>

---

## 🧙 I passaggi della procedura guidata di importazione

Quattro passaggi ci sono sempre; gli altri compaiono solo quando i tuoi file ne hanno bisogno, e la
barra di avanzamento mostra soltanto i passaggi dell'importazione corrente.

| Passaggio | Quando lo vedi |
| :--- | :--- |
| 1 · **Carica** | Sempre |
| 2 · **Seleziona File** | Sempre |
| 3 · **Analizza** | Sempre |
| 🧬 **Unifica asset** | Lo stesso titolo compare con più di un nome o codice |
| 🔧 **Correzioni** | L'importatore ha registrato righe che non è riuscito a comprendere del tutto |
| 🧹 **Duplicati** | Lo stesso movimento è presente in due dei file che importi insieme |
| 4 · **Revisione** | Sempre |
| ⚖️ **Allinea con la banca** | Solo per i set di report, quando le cifre della banca differiscono da quelle di LibreFolio |

### 📤 Passaggio 1: Carica

Trascina i tuoi report nella procedura guidata, oppure clicca per sceglierli (CSV o XLSX), e assegna
ciascuno al suo broker — oppure tutti in una volta con **Broker per i caricamenti**. Un
broker mancante può essere creato dalla stessa lista (**Crea nuovo**).

- Ogni report che carichi viene conservato: per riutilizzarne uno, salta questo passaggio con
  **Avanti: Seleziona File**.
- Quando un conto arriva in più esportazioni (ad es. [Danske Bank](danske-bank.md)), caricale
  insieme: se ne manca una, la procedura guidata resta qui e la nomina.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Passaggio 1 della procedura guidata: Caricamento" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

#### 🧭 Un file nel broker sbagliato {: #wrong-broker }

Quando clicchi **Avanti: Seleziona File**, la procedura guidata verifica ogni file appena caricato
rispetto al **Plugin di Import Predefinito** del suo broker. Se quel plugin non riesce a
leggere un file, il file probabilmente appartiene a un altro broker, e la procedura guidata te lo
chiede prima di procedere (*Questo file potrebbe appartenere a un altro broker*). Dall'alto verso il
basso, mostra:

- **Assegnato a** — il broker in cui si trova il file, con la sua icona, e il suo plugin predefinito,
  contrassegnato *non sa leggerlo*;
- **Note dal plugin** — perché quel plugin non riesce a leggere il file, quando ne indica il motivo:
  nella tua lingua quando esiste una traduzione;
- **Spostalo in** — il broker il cui plugin predefinito *sa leggerlo*. Quando i plugin
  predefiniti di più broker lo leggono, la richiesta elenca invece quei broker: scegline uno, il
  primo è già selezionato.

Poi scegli:

- **Sposta**, con l'icona del broker scelto in **Spostalo in** — il file viene caricato su quel
  broker, nella stessa sessione, e rimosso da quello sbagliato. Se lo spostamento fallisce, un errore
  lo segnala e il file resta dov'era;
- **Tienilo qui** — il file resta, e la procedura guidata lo legge con un altro plugin in grado di
  farlo, come prima: lo vedi nella colonna **Plugin** di **Seleziona File**;
- **Rimuovi** — il file viene eliminato.

Una richiesta per file, a turno (*File 1 di 3*); chiuderla mantiene il file. Se rimuovi tutti i file
appena caricati, la procedura guidata resta su **Carica**, pronta per altri. Quando nessuno dei
tuoi broker ha un plugin predefinito che legge il file, la richiesta nomina i plugin che lo leggono —
o dice che nessuno può farlo — e offre solo di mantenerlo o rimuoverlo.

I broker senza un plugin di importazione predefinito non vengono mai interrogati, e nemmeno i report
che riutilizzi senza caricarli di nuovo.

### 🗂️ Passaggio 2: Seleziona File

Il pannello di ogni broker elenca i suoi report memorizzati, con i file appena caricati già spuntati.
Spunta i file da leggere e clicca **Analizza (N)**.

L'importatore di ogni file viene rilevato automaticamente: cambialo nella colonna **Plugin** se è
sbagliato, e per un CSV che hai creato tu scegli **[CSV generico](generic-csv.md)**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Passaggio 2 della procedura guidata: Configurazione del parser" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

I **set di report** sono una sola scheda, spuntata nel suo complesso. **Letto come**, nella sua
intestazione, cambia il modo in cui il set viene letto, e il menu **⋮** di ogni file può rimuoverlo
dal set (**Leggi da solo con ‹plugin›**, **Togli dal set**) — [dettagli](danske-bank.md#how-the-set-is-read).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-read-as" alt="Scheda del set di report in Seleziona i file con la lista Leggi come aperta: Danske Bank (rilevato) e Leggi i file uno per uno" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-file-menu" alt="Il menu ⋮ di un file di cassa in un set di report: Anteprima, Rimuovi dal set ed Elimina" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Analizza è disattivato?** Un file spuntato non ha un plugin, oppure un set spuntato è incompleto
o solo parzialmente spuntato (un trattino nella sua casella di controllo): scegli il plugin, usa
**Carica il file mancante**, oppure spunta o despunta l'intero set.

### 🧠 Passaggio 3: Analizza

LibreFolio legge ogni file, lo verifica e lo riassume in una tabella:

| Colonna | Cosa conta |
| :--- | :--- |
| 📊 | Transazioni lette |
| 🏦 | Titoli trovati |
| ✗ | Titoli non ancora abbinati ai tuoi asset — li abbini in **Revisione** |
| 🔴 | Problemi di validazione: righe che non è stato possibile convertire in transazioni |
| 🔧 | Campi da compilare prima del salvataggio (in rosso quando uno blocca il salvataggio) |
| ⚠️ ℹ️ | Due numeri: gli avvisi (ambra) vanno guardati, come le righe saltate; le note (blu) spiegano una scelta fatta dall'importatore, senza nulla da correggere |

I riquadri sotto la tabella contano ciò che verrà realmente importato; **Vedi tutto**, o **Vedi Dettaglio**
nel menu **⋮** di una riga, apre i dettagli, con gli avvisi e le note elencati a parte.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Passaggio 3 della procedura guidata: Analisi" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- **Avvisi e note**: **Continua** elenca prima gli avvisi, poi le note; leggili, poi clicca
  **Continua comunque**.
- **Un file non è stato elaborato**: un banner ne indica il motivo. Correggi il suo plugin in
  **Seleziona File**, poi clicca **Rianalizza tutti**.

### 🧩 Passaggi che compaiono solo quando servono {: #only-when-needed }

A seconda di ciò che il passaggio **Analizza** trova, fino a tre passaggi possono precedere la **Revisione**, in
questo ordine. Apri quello che la procedura guidata ti mostra:

??? abstract "🧬 Unifica asset — quando lo stesso titolo compare con più di un nome o codice"

    I tuoi file descrivono lo stesso titolo più di una volta — con due nomi o codici, oppure in due file.
    Unificalo qui, altrimenti si sdoppia in due asset con le sue transazioni divise tra loro.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-assets-step" alt="Procedura guidata di importazione — Passaggio Unifica gli asset con un gruppo proposto">
    </div>

    Ogni scheda è un titolo: un bordo **verde pieno** significa unificato, **ambra tratteggiato**
    significa da confermare, **grigio** significa nulla da decidere.

    - **Conferma** o **Separa** una proposta; unisci o separa le schede con **⋮** (**Unisci con…**,
      **Estrai dal gruppo**) oppure tramite trascinamento.
    - **Clicca un badge di codice** per renderlo il codice principale (⭐) — scegli quello su cui sono
      quotati i prezzi; gli altri restano come alternative.
    - **Rinomina** con la matita; un titolo già nella tua libreria (**in archivio**) mantiene il suo nome.
    - **Continua** attende finché nessuna proposta è aperta: **Conferma tutte (N)** le risolve in una
      volta, e **Ripristina unione automatica** ricomincia da capo.

??? warning "🔧 Correzioni — quando l'importatore ha registrato righe che non è riuscito a comprendere del tutto"

    L'importatore ha registrato righe che non è riuscito a comprendere del tutto — oggi, righe dei
    report di [Crédit Agricole](credit_agricole.md) e [Danske Bank](danske-bank.md).

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-fix-step" alt="Procedura guidata di importazione — Passaggio Correzioni con righe segnalate">
    </div>

    Le righe sono raggruppate per domanda. Dai una risposta a ciascuna:

    - **Correggila**: scegli il tipo e, dove applicabile, il titolo e la quantità, poi
      **Applica la correzione**. Una commissione o un'imposta può appartenere a **Nessuno strumento
      (commissione del broker)**.
    - **Separa**: scorpora il prezzo dalle commissioni, imposte o interessi maturati indicati nella
      tua nota di contratto.
    - **Mantieni come registrato**: accetta ciò che l'importatore ha letto.

    **Riga N nel file** mostra la riga originale, e **Ripristina** annulla una risposta. **Continua**
    attende ogni risposta; **Mantieni le rimanenti N righe come lette** risponde a tutte quelle aperte.

??? note "🧹 Duplicati — quando lo stesso movimento è presente in due dei file che importi insieme"

    Lo stesso movimento è presente in due dei file che importi insieme, come un estratto conto annuale
    e uno trimestrale. Le corrispondenze con transazioni già salvate non aprono questo passaggio: la
    **Revisione** le segnala.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicates-step" alt="Procedura guidata di importazione — Passaggio Duplicati con una coppia tra file">
    </div>

    - **Priorità file**: trascina i file nell'ordine di cui ti fidi e clicca **Ricalcola per priorità**.
      Ogni gruppo mantiene la copia dal file più in alto — mai una già salvata o in attesa nel workspace
      bulk.
    - **Tieni**: spunta le copie da importare, riga per riga; **Ripristina default**
      ripristina la scelta automatica.
    - **Confronta** mostra le copie affiancate, con le differenze evidenziate.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-nway-compare" alt="Modale di confronto a N vie con le differenze per campo evidenziate">
    </div>

    I gruppi sono elencati sotto **Sovrapposizione totale** (copie identiche) e **Sovrapposizione
    parziale** (qualcosa differisce).

### 📦 Passaggio 4: Revisione {: #review }

Ogni riga da importare in un'unica griglia — stato, data, tipo, titolo, broker, quantità, liquidità e
tag, più il file quando ne importi diversi.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Griglia Revisione e importazione" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

#### 🗂️ Abbina ogni titolo

Il pannello **Risolvi Asset** sopra la griglia elenca i titoli dei tuoi file. Abbina ciascuno:

- Cerca **In questo import** e **In archivio** (la tua libreria) da un unico campo. Le
  corrispondenze probabili vengono per prime, con un badge di attendibilità (**Esatta** fino a
  **Bassa**); una corrispondenza unica è già selezionata.
- **Crea "…"** apre il modulo del nuovo asset, compilato con il nome e i codici dal report.
- ✏️ **Ispeziona / modifica** apre l'asset scelto; **Unisci** compare quando due dei tuoi asset
  corrispondono.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Pannello di risoluzione degli asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Se il codice del report differisce da quello dell'asset o del provider dei prezzi, LibreFolio chiede
quale sia quello principale. Il codice del provider, quello con i prezzi, è preselezionato; gli
altri restano come alternative. Una nota ambra su un nuovo asset, come una possibile scadenza, è solo
un consiglio.

#### 🚦 Leggi i badge di stato

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Badge di rilevamento dei duplicati" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

| Badge | Significato | Spuntato all'inizio? |
| :--- | :--- | :--- |
| **✓ Unico** | Nulla di simile è salvato | ✅ |
| **ℹ Possibile dup** | Una transazione salvata ha lo stesso tipo, data, quantità e importo, ma un'altra descrizione | ✅ — controllala |
| **⚠ Probabile dup** | Una transazione salvata corrisponde, descrizione inclusa | ⬜ |
| **⧉ Duplicato nel lotto** | Copia esatta di un'altra riga di questa importazione, o del workspace bulk | ⬜ |
| **≈ Possibile duplicato nel lotto** | Lo stesso, con un'altra descrizione | ✅ — controllala |
| **✗ Non risolto** | Il suo titolo non è ancora abbinato | ✅ — abbinalo o despunta la riga |
| **⛔ Prima dell'apertura** | Datata prima della data di apertura del broker | Non può essere importata |
| **⏮ Già in LibreFolio** | Set di report: più vecchia della cronologia conservata da LibreFolio; nascosta dietro un contatore | Non può essere importata |

Clicca un badge di duplicato per confrontare la riga con la sua gemella; un banner spiega perché le
righe sono deselezionate. Una conversione di valuta è una sola riga, importata per intero.

#### ⛔ Righe precedenti la data di apertura del broker {: #opening-date }

Le righe datate prima della data di apertura del broker non possono essere importate (il giorno di
apertura stesso va bene). Se la data è sbagliata, il banner offre **Imposta l'apertura alla ‹data›** —
la data della riga più antica — e **Modifica data broker**; le righe vengono poi ricontrollate.

#### 📥 Importa le righe

**Importa N transazioni** è attivo una volta che almeno una riga è spuntata e ogni riga spuntata ha
il suo titolo. Prima viene eseguito un ultimo controllo dei duplicati: i duplicati cambiati tra i
file ti riportano a **Duplicati**, e una selezione cambiata ti tiene qui con un messaggio — controlla
le spunte e clicca di nuovo.

??? info "⚖️ Allinea con la banca — dopo la Revisione, solo per un set di report come Danske Bank"

    Per un set di report come [Danske Bank](danske-bank.md#first-import-align-with-the-bank),
    LibreFolio confronta ciò che conterrà con i saldi e le posizioni della banca. Le schede mostrano
    ogni punto — **Punto di partenza**, **Dopo il buco**, **Verifica a fine periodo** — sopra le
    correzioni proposte, tutte spuntate. Despunta quelle che non vuoi e clicca **Continua**; se il
    confronto non è riuscito, prosegui senza di esse.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-gapfix-step" alt="Allinea con la banca: le schede Punto di partenza, Dopo il buco e Verifica a fine periodo sopra le correzioni proposte contrassegnate gap_fix" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

### 💾 Salva nel workspace bulk

Le righe arrivano nel workspace bulk non salvate. Controllale o modificale, poi clicca
**Salva tutto**: attende le righe elencate in rosso, e chiede prima di salvare i valori elencati in
ambra che non hai verificato (**Salva comunque**). Una riga la cui quantità ha più di 10 decimali, il cui
importo ne ha più di 6, o il cui costo di carico per unità ne ha più di 12, è rifiutata a **Salva tutto**, col
massimo nel messaggio (*Quantità: Al massimo 10 decimali*): LibreFolio non la arrotonda mai.
Le date delle transazioni possono risalire fino all'anno 1 e arrivare a domani. Una riga datata prima del 1900 è segnata in ambra nella revisione (una nota sopra la tabella le conta) e lo spazio di lavoro bulk chiede una sola volta di confermarle, perché una data così è di solito un refuso; una volta confermata si salva come le altre. Una riga datata dopo domani è rifiutata a **Salva tutto**, con l'ultimo giorno ammesso nel messaggio (*Data: Non oltre il 2026-10-18* se oggi è il 17 ottobre 2026).

---

## 🧭 Prima importazione guidata {: #guided-first-import }

La prima volta che apri la procedura guidata, una bolla guida ti accompagna:

- il suo **Passo N di M** conta solo i passaggi che vedi; i suggerimenti per i passaggi opzionali
  aspettano un'importazione che ne abbia bisogno;
- si limita a indicare: non clicca, non carica e non modifica mai al posto tuo;
- termina evidenziando **Salva tutto**, senza premerlo;
- **X** salta solo il suggerimento corrente.

Per rivederla, scegli **Ripeti al prossimo ingresso** per la **Guida all'importazione** in
**[Impostazioni → Preferenze → Primo utilizzo e guide](../../settings/preferences.md#onboarding-and-guides)**:
si avvia con la tua prossima importazione.

---

## 🔗 Correlati

- 🏦 **[Broker supportati](index.md)** — quale file esportare
- 🛠️ **[Dettagli interni della procedura guidata di importazione](../../../developer/frontend/components/features/import-wizard.md)** — per gli sviluppatori
