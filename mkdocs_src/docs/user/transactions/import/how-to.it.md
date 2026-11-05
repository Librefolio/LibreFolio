# 🧙 Come importare le transazioni

La **Procedura guidata di importazione** trasforma i report che scarichi dal tuo broker in transazioni. Controlli ciò che ha letto e risolvi i suoi dubbi; nulla viene salvato finché non premi **Salva tutto**.

---

## 🚀 Guida passo passo

1. Esporta un report delle transazioni dal tuo broker: la sua pagina in **[Broker supportati](index.md)** indica quale file.
2. Nella pagina **[Transazioni](../index.md)**, fai clic su **Importa** (:material-file-upload:).
3. Trascina il report nella procedura guidata, assegnalo al suo broker e segui i passaggi riportati di seguito.
4. Fai clic su **Importa N transazioni**: le righe si aprono nel workspace bulk, non ancora salvate.
5. Dagli un'ultima occhiata e fai clic su **Salva tutto**.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Finestra modale di importazione rapida" alt="Finestra modale di importazione rapida">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Passaggio 1: Carica il file del report" alt="Passaggio 1 della procedura guidata">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Passaggio 2: Seleziona file e parser" alt="Passaggio 2 della procedura guidata">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Passaggio 3: Analisi e parsing" alt="Passaggio 3 della procedura guidata">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🗂️ Risoluzione asset" alt="Risoluzione asset">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Rilevamento duplicati" alt="Rilevamento duplicati">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Passaggio 4: Rivedi e importa" alt="Rivedi e importa">
</div>

---

## 🧙 I passaggi della procedura guidata di importazione

Ci sono sempre quattro passaggi; gli altri compaiono solo quando i tuoi file ne hanno bisogno, e la barra di avanzamento mostra solo i passaggi dell'importazione corrente.

| Passaggio | Quando lo vedi |
| :--- | :--- |
| 1 · **Carica** | Sempre |
| 2 · **Seleziona file** | Sempre |
| 3 · **Analizza** | Sempre |
| 🧬 **Unifica asset** | Lo stesso titolo compare con più di un nome o codice |
| 🔧 **Correzioni** | L'importatore ha registrato righe che non è riuscito a comprendere completamente |
| 🧹 **Duplicati** | Lo stesso movimento è presente in due dei file che importi insieme |
| 4 · **Revisione** | Sempre |
| ⚖️ **Allinea con la banca** | Solo per i set di report, quando i dati della banca differiscono da quelli di LibreFolio |

### 📤 Passaggio 1: Carica

Trascina i tuoi report nella procedura guidata, oppure fai clic per sceglierli (CSV o XLSX), e assegna ciascuno al suo broker — o tutti in una volta con **Assegna broker per i caricamenti**. Un broker mancante può essere creato dallo stesso elenco (**Crea nuovo**).

- Ogni report che carichi viene conservato: per riutilizzarne uno, salta questo passaggio con **Avanti: Seleziona file**.
- Quando un conto arriva in più esportazioni (ad es. [Danske Bank](danske-bank.md)), caricale insieme: se ne manca una, la procedura guidata resta qui e la nomina.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Procedura guidata, passaggio 1: Carica" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

#### 🧭 Un file nel broker sbagliato {: #wrong-broker }

Quando fai clic su **Avanti: Seleziona file**, la procedura guidata controlla ogni file appena caricato rispetto al **Plugin di importazione predefinito** del suo broker. Se quel plugin non riesce a leggere un file, probabilmente il file appartiene a un altro broker, e la procedura guidata te lo chiede prima di proseguire (*Questo file potrebbe appartenere a un altro broker*). Dall'alto verso il basso, mostra:

- **Assegnato a** — il broker in cui si trova il file, con la sua icona, e il suo plugin predefinito, contrassegnato come *non riesce a leggerlo*;
- **Note dal plugin** — perché quel plugin non riesce a leggere il file, quando ne indica il motivo: nella tua lingua quando esiste una traduzione;
- **Spostalo in** — il broker il cui plugin predefinito *riesce a leggerlo*. Quando i plugin predefiniti di più broker riescono a leggerlo, il messaggio elenca invece quei broker: scegline uno, il primo è già selezionato.

Poi scegli:

- **Sposta**, con l'icona del broker scelto in **Spostalo in** — il file viene caricato su quel broker, nella stessa sessione, e rimosso da quello sbagliato. Se lo spostamento non riesce, un errore lo segnala e il file resta dov'era;
- **Mantienilo qui** — il file resta, e la procedura guidata lo legge con un altro plugin che può farlo, come prima: lo vedi nella colonna **Plugin** di **Seleziona file**;
- **Rimuovi** — il file viene eliminato.

Un messaggio per file, uno alla volta (*File 1 di 3*); chiudendolo il file viene mantenuto. Se rimuovi tutti i file appena caricati, la procedura guidata resta su **Carica**, pronta per altri. Quando nessuno dei tuoi broker ha un plugin predefinito che legga il file, il messaggio indica i plugin che lo leggono — o dice che nessuno può farlo — e offre solo di mantenerlo o rimuoverlo.

I broker senza un plugin di importazione predefinito non vengono mai interrogati, e nemmeno i report che riutilizzi senza caricarli di nuovo.

### 🗂️ Passaggio 2: Seleziona file

Il pannello di ciascun broker elenca i suoi report memorizzati, con i file appena caricati già selezionati. Seleziona i file da leggere e fai clic su **Analizza (N)**.

L'importatore di ciascun file viene rilevato automaticamente: cambialo nella colonna **Plugin** se è sbagliato, e per un CSV creato da te scegli **[CSV generico](generic-csv.md)**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Procedura guidata, passaggio 2: Configurazione del parser" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Ogni **set di report** è un'unica scheda, selezionata nel suo insieme. **Leggi come**, nella sua intestazione, cambia il modo in cui viene letto il set, e il menu **⋮** di ciascun file può rimuoverlo dal set (**Leggi da solo con ‹plugin›**, **Rimuovi dal set**) — [dettagli](danske-bank.md#how-the-set-is-read).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-read-as" alt="Scheda del set di report in Seleziona file con l'elenco Leggi come aperto: Danske Bank (rilevato) e Leggi i file uno alla volta" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-file-menu" alt="Il menu ⋮ di un file di cassa in un set di report: Anteprima, Rimuovi dal set ed Elimina" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Analizza è disattivato?** Un file selezionato non ha un plugin, oppure un set selezionato è incompleto o solo parzialmente selezionato (un trattino nella sua casella di controllo): scegli il plugin, usa **Carica il file mancante**, oppure seleziona o deseleziona l'intero set.

### 🧠 Passaggio 3: Analizza

LibreFolio legge ciascun file, lo controlla e lo riepiloga in una tabella:

| Colonna | Cosa conta |
| :--- | :--- |
| 📊 | Transazioni lette |
| 🏦 | Titoli trovati |
| ✗ | Titoli non ancora abbinati ai tuoi asset — li abbini in **Revisione** |
| 🔴 | Problemi di convalida: righe che non è stato possibile trasformare in transazioni |
| 🔧 | Campi da compilare prima del salvataggio (in rosso quando uno blocca il salvataggio) |
| ⚠️ ℹ️ | Due numeri: gli avvisi (ambra) richiedono un controllo, ad esempio righe saltate; le note (blu) spiegano una scelta fatta dall'importatore, senza nulla da correggere |

I riquadri sotto la tabella contano ciò che verrà realmente importato; **Visualizza tutto**, oppure **Visualizza dettaglio** nel menu **⋮** di una riga, apre i dettagli, con gli avvisi e le note elencati separatamente.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Procedura guidata, passaggio 3: Analisi" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- **Avvisi e note**: **Continua** elenca prima gli avvisi, poi le note; leggili, quindi fai clic su **Continua comunque**. Un avviso sulle righe che l'importatore ha lasciato fuori, perché non le conosce o non riesce a leggerle, ha un link per aprire una issue su GitHub.
- **Elaborazione di un file non riuscita**: un banner ne indica il motivo. Correggi il suo plugin in **Seleziona file**, quindi analizza di nuovo. **Rianalizza tutto** è presente nell'analisi solo dopo che è stato letto almeno un file; se nessuno lo è stato, torna a **Seleziona file** e fai clic su **Analizza (N)**.

### 🧩 Passaggi che compaiono solo quando servono {: #only-when-needed }

A seconda di ciò che trova **Analizza**, fino a tre passaggi possono precedere **Revisione**, in questo ordine. Apri quello che la procedura guidata ti mostra:

??? abstract "🧬 Unifica asset — quando lo stesso titolo compare con più di un nome o codice"

    I tuoi file descrivono lo stesso titolo più di una volta — con due nomi o codici, o in due file.
    Unificalo qui, altrimenti si trasforma in due asset con le transazioni divise tra loro.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-assets-step" alt="Procedura guidata di importazione — passaggio Unifica asset con un gruppo proposto">
    </div>

    Ogni scheda è un titolo: un bordo **verde continuo** indica unificato, un bordo **ambra tratteggiato** indica da
    confermare, un bordo **grigio** indica che non c'è nulla da decidere.

    - **Conferma** o **Dividi** una proposta; unisci o separa le schede con **⋮** (**Unisci con…**,
      **Rimuovi dal gruppo**) oppure tramite trascinamento.
    - **Fai clic su un badge del codice** per renderlo il codice principale (⭐) — scegli quello su cui sono quotati i prezzi; gli
      altri restano come alternative.
    - **Rinomina** con la matita; un titolo già presente nella tua libreria (**in archivio**) mantiene il suo nome.
    - **Continua** attende finché non resta aperta alcuna proposta: **Conferma tutto (N)** le risolve in una volta, e
      **Ripristina raggruppamento automatico** ricomincia da capo.

??? warning "🔧 Correzioni — quando l'importatore ha registrato righe che non è riuscito a comprendere completamente"

    L'importatore ha registrato righe che non è riuscito a comprendere completamente — oggi, righe dai report di
    [Crédit Agricole](credit_agricole.md) e [Danske Bank](danske-bank.md).

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-fix-step" alt="Procedura guidata di importazione — passaggio Correzioni con righe segnalate">
    </div>

    Le righe sono raggruppate per domanda. Dai una risposta a ciascuna:

    - **Correggila**: scegli il tipo e, dove applicabile, il titolo e la quantità, quindi
      **Applica correzione**. Una commissione o un'imposta può appartenere a **Nessuno strumento (addebito del broker)**.
    - **Dividila**: separa il prezzo dalle commissioni, dalle imposte o dagli interessi maturati indicati nella
      nota contrattuale.
    - **Mantieni come registrata**: accetta ciò che ha letto l'importatore.

    **Riga N nel file** mostra la riga originale, e **Ripristina** annulla una risposta. **Continua** attende
    ogni risposta; **Mantieni le restanti N righe come lette** risponde a tutte quelle aperte.

??? note "🧹 Duplicati — quando lo stesso movimento è presente in due dei file che importi insieme"

    Lo stesso movimento è presente in due dei file che importi insieme, ad esempio un estratto conto annuale e uno trimestrale.
    Le corrispondenze con transazioni già salvate non aprono questo passaggio: **Revisione** le segnala.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicates-step" alt="Procedura guidata di importazione — passaggio Duplicati con una coppia di righe da file diversi">
    </div>

    - **Priorità dei file**: trascina i file nell'ordine di cui ti fidi e fai clic su **Ricalcola per priorità**.
      Ogni gruppo mantiene la copia del file con priorità più alta — mai una già salvata o in attesa nel workspace bulk.
    - **Mantieni**: seleziona le copie da importare, riga per riga; **Ripristina valori predefiniti** ripristina la scelta automatica.
    - **Confronta** mostra le copie affiancate, con le differenze evidenziate.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-nway-compare" alt="Finestra modale di confronto a N vie con le differenze per campo evidenziate">
    </div>

    I gruppi sono elencati sotto **Sovrapposizione totale** (copie identiche) e **Sovrapposizione parziale** (qualcosa
    differisce).

### 📦 Passaggio 4: Revisione {: #review }

Ogni riga da importare in un'unica griglia — stato, data, tipo, titolo, broker, quantità, liquidità e tag,
più il file quando ne importi diversi.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Griglia Rivedi e importa" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

#### 🗂️ Abbina ciascun titolo

Il pannello **Risolvi asset** sopra la griglia elenca i titoli dei tuoi file. Abbina ciascuno:

- Cerca **In questa importazione** e **Nell'archivio** (la tua libreria) da un unico campo. Le corrispondenze probabili
  vengono per prime, con un badge di affidabilità (da **Esatta** a **Bassa**); una corrispondenza unica è già selezionata.
- **Crea “…”** apre il modulo del nuovo asset, compilato con il nome e i codici del report.
- ✏️ **Ispeziona / modifica** apre l'asset scelto; **Unisci** compare quando due dei tuoi asset corrispondono.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Pannello di risoluzione degli asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Se il codice del report differisce da quello dell'asset o del provider dei prezzi, LibreFolio chiede quale sia
quello principale. Il codice del provider, quello con i prezzi, è preselezionato; gli altri restano come
alternative. Una nota ambra su un nuovo asset, come una possibile scadenza, è solo un suggerimento.

#### 🚦 Leggi i badge di stato

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Badge di rilevamento dei duplicati" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

| Badge | Significato | Selezionato inizialmente? |
| :--- | :--- | :--- |
| **✓ Unico** | Non è salvato nulla di simile | ✅ |
| **ℹ Possibile duplicato** | Una transazione salvata ha lo stesso tipo, data, quantità e importo, ma un'altra descrizione | ✅ — controllala |
| **⚠ Probabile duplicato** | Una transazione salvata corrisponde, descrizione inclusa | ⬜ |
| **⧉ Duplicato nel lotto** | Copia esatta di un'altra riga di questa importazione, o del workspace bulk | ⬜ |
| **≈ Possibile duplicato nel lotto** | Lo stesso, con un'altra descrizione | ✅ — controllala |
| **✗ Non risolto** | Il suo titolo non è ancora abbinato | ✅ — abbinalo o deselezionalo |
| **⛔ Prima dell'apertura** | Datata prima della data di apertura del broker | Non può essere importata |
| **⏮ Già in LibreFolio** | Set di report: più vecchia della cronologia in possesso di LibreFolio; nascosta dietro un contatore | Non può essere importata |

Fai clic su un badge di duplicato per confrontare la riga con la sua gemella; un banner spiega perché le righe sono deselezionate. Una
conversione di valuta è un'unica riga, importata per intero.

#### ⛔ Righe precedenti alla data di apertura del broker {: #opening-date }

Le righe datate prima della data di apertura del broker non possono essere importate (il giorno di apertura stesso va bene). Se
la data è sbagliata, il banner offre **Imposta apertura a ‹data›** — la data della riga più vecchia — e
**Modifica data broker**; le righe vengono quindi ricontrollate.

#### 📥 Importa le righe

**Importa N transazioni** si attiva una volta che almeno una riga è selezionata e ogni riga selezionata ha il proprio
titolo abbinato. Prima viene eseguito un ultimo controllo dei duplicati: i duplicati modificati tra i file ti riportano a
**Duplicati**, e una selezione modificata ti mantiene qui con un messaggio — controlla le selezioni e fai clic
di nuovo.

??? info "⚖️ Allinea con la banca — dopo la Revisione, solo per un set di report come Danske Bank"

    Per un set di report come [Danske Bank](danske-bank.md#first-import-align-with-the-bank), LibreFolio
    confronta ciò che conterrà con i saldi e le posizioni della banca. Le schede mostrano ciascun punto —
    **Punto di partenza**, **Dopo la lacuna**, **Controllo di fine periodo** — sopra le correzioni proposte,
    tutte selezionate. Deseleziona quelle che non vuoi e fai clic su **Continua**; se il confronto non è riuscito, continua
    senza di esse.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-gapfix-step" alt="Allinea con la banca: le schede Punto di partenza, Dopo la lacuna e Controllo di fine periodo sopra le correzioni proposte contrassegnate gap_fix" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

### 💾 Salva nel workspace bulk

Le righe arrivano nel workspace bulk non ancora salvate. Controllale o modificale, quindi fai clic su **Salva tutto**: attende
le righe elencate in rosso e chiede prima di salvare i valori elencati in ambra che non hai verificato (**Salva comunque**). Una riga la cui quantità ha più di 10 cifre decimali, il cui importo in liquidità
ha più di 6 cifre decimali, o il cui costo di carico per unità ha più di 12 cifre decimali, viene rifiutata in **Salva tutto**, con il
valore massimo nel messaggio (*Quantità: Al massimo 10 cifre decimali*): LibreFolio non arrotonda mai questi valori.
Le date delle transazioni possono risalire fino all'anno 1 e arrivare fino a domani. Una riga datata prima del 1900 è contrassegnata in ambra nella revisione (una nota sopra la tabella ne conta il numero) e il workspace bulk chiede una volta di confermarle, poiché una data del genere è di solito un errore di battitura; una volta confermata, viene salvata come qualsiasi altra. Una riga datata dopo domani viene rifiutata in **Salva tutto**, con l'ultimo giorno consentito nel messaggio (*Data: Non successiva al 2026-10-18* quando oggi è il 17 ottobre 2026).

Una riga che introduce unità — una **Rettifica** che aggiunge unità, o il lato ricevente di un
**Trasferimento asset** — mantiene in **Manuale** il costo scritto nel report, anche 0. Se il report
non ne fornisce alcuno, parte in **Auto** (💡 nella colonna **Sovrascrittura del costo di carico**): **Salva tutto** la salva
al [costo medio](../form.md#cost-basis) delle unità già possedute, a meno che tu non la passi a
**Manuale**. Se non c'è nulla da mediare, la riga viene rifiutata: scegli **Manuale** e digita il suo
costo, 0 per un regalo.

Fanno eccezione le righe il cui costo mancante è segnalato dall'importatore: una posizione aggiunta da
**Allinea con la banca**, una nuova riga di una [scissione](danske-bank.md#demergers) di Danske Bank, una
riga `ADJUSTMENT` di un file [CSV generico](generic-csv.md) che aggiunge unità senza un costo. Sono elencate in rosso,
e il loro modulo si apre in **Manuale** con il costo vuoto: digitalo a mano, anche se è 0 — scegliere
**Auto** non le rimuove dall'elenco.

Quando le righe arrivano, e dopo **⚡ Convalida ora** o un **Salva tutto** rifiutato, la griglia passa alla
pagina della prima riga il cui [costo **Auto** è stato rifiutato](../form.md#cost-basis), e la evidenzia:
la più vecchia per data, poiché correggerla può far passare le righe successive dello stesso asset presso quel broker.
Il controllo automatico eseguito durante la modifica non fa questo.

---

## 🧭 Prima importazione guidata {: #guided-first-import }

La prima volta che apri la procedura guidata, un fumetto guida ti accompagna:

- il suo **Passaggio N di M** conta solo i passaggi che vedi; i suggerimenti per i passaggi facoltativi attendono un'importazione
  che ne abbia bisogno;
- indica soltanto: non fa mai clic, non carica e non modifica al posto tuo;
- termina evidenziando **Salva tutto**, senza premerlo;
- **X** salta solo il suggerimento corrente.

Per rivederla, scegli **Ripeti al prossimo trigger** per la **Guida all'importazione** in
**[Impostazioni → Preferenze → Primo utilizzo e guide](../../settings/preferences.md#onboarding-and-guides)**: inizierà con la tua prossima importazione.

---

## 🔗 Voci correlate

- 🏦 **[Broker supportati](index.md)** — quale file esportare
- 🛠️ **[Dettagli interni della procedura guidata di importazione](../../../developer/frontend/components/features/import-wizard.md)** — per gli sviluppatori
