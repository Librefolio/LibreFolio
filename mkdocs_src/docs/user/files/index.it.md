# 📁 File e caricamenti

La pagina **File** conserva tutto ciò che è stato caricato su LibreFolio, in due schede:

- **Risorse statiche** — avatar, icone dei broker e altre immagini o documenti, visibili a ogni utente;
- **Report del broker** — i file di estratto conto da cui importi le transazioni, visibili solo alle persone che hanno accesso al relativo broker.

---

## 🖼️ Risorse statiche

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-tab" alt="Scheda File statici" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Qui trovi gli **avatar** degli utenti, le **icone** dei broker e qualsiasi **immagine o documento** condiviso dagli utenti. Chiunque abbia un account LibreFolio può vederli.

- Passa dalla vista **elenco** alla vista **griglia**: la griglia mostra un'anteprima delle immagini.
- Nell'elenco, fai clic con il tasto destro su un file per **Anteprima**, **Copia link**, **Scarica** o **Elimina**. Puoi eliminare solo i file che hai caricato tu; un amministratore può eliminare qualsiasi file.
- **Anteprima** mostra un PDF in un visualizzatore di sola lettura: puoi leggerlo, cercare al suo interno e copiarne il testo, ma non modificarlo, annotarlo o stamparlo; per conservare il file, usa **Scarica**. Un PDF protetto da password ne richiede la password, che resta nel tuo browser: non viene mai inviata al server né salvata, e scompare alla chiusura dell'anteprima.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-grid" alt="Vista griglia dei file statici" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### ⬆️ Caricare un file

1. Fai clic su **Carica**, poi trascina e rilascia i file nell'area oppure fai clic su di essa per sfogliare.
2. Prima di caricare, puoi fare clic su ✏️ **Modifica** su un'immagine per ritagliarla con lo [strumento di ritaglio immagini](../misc/image-crop.md), quindi confermare con **Ritaglia**; su qualsiasi altro file, ✏️ **Rinomina** ne cambia il nome. **Ripristina originale** riporta un file allo stato in cui l'avevi scelto.
3. Fai clic su **Carica**.

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
    <img class="gallery-img" data-category="media" data-name="file-uploader-empty" alt="Area di rilascio per il caricamento dei file" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📊 Report del broker {: #broker-reports }

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="brim-tab" alt="Scheda Report del broker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Questi sono gli estratti conto esportati dai tuoi broker, in attesa di essere importati o già importati. Vedi i report di ogni broker a cui puoi accedere, come Proprietario, Editor o Visualizzatore.

La colonna **Stato** ti dice in che situazione si trova ogni file:

- **Caricato** — memorizzato, non ancora analizzato;
- **Analizzato** — la procedura guidata di importazione lo ha letto correttamente;
- **Non riuscito** — l'analisi è fallita; il file resta qui così puoi controllarlo o segnalarlo.

### 📤 Caricare un report del broker

1. In **Report del broker**, fai clic su **Carica** e scegli file CSV o Excel.
2. In **Assegna broker**, scegli il broker di ciascun file, oppure uno per tutti con **Assegna tutto a**. **Crea nuovo** aggiunge un broker sul momento; se puoi modificare un solo broker, è già selezionato.
3. Fai clic su **Carica**. I file vengono memorizzati, ma **non viene ancora importato nulla**.

Per importarli, apri la [procedura guidata di importazione](../transactions/import/index.md) (**Transazioni** → **Importa**): il suo passaggio **Seleziona file** elenca i report che hai caricato.

Il broker che scegli decide solo quale conto riceve le transazioni. L'importatore riconosce da sé il formato del file, e un singolo plugin di importazione può leggere gli export di più broker.

### ⚙️ Gestire i report

Fai clic con il tasto destro su un report per **Anteprima**, **Scarica** o **Elimina**, oppure seleziona più report per eliminarli insieme. Eliminare un report non elimina mai le transazioni già importate da esso.

### 🧩 Set di report {: #report-sets }

Alcune banche suddividono un conto su più export: [Danske Bank](../transactions/import/danske-bank.md), per esempio, richiede un export dei titoli e un estratto del conto. Gli export di una banca di questo tipo che carichi **insieme** formano un **set di report**, e LibreFolio li importa come un unico report, tramite un **file combinato** che costruisce a partire da essi. La colonna **Set di report** ti dice in che situazione si trova ogni file (la stessa colonna compare nei **Report caricati** di un broker):

| Badge | Significato |
|:--|:--|
| **Set della ‹data›** | Il file appartiene al set caricato in quella data, insieme agli altri export del set. |
| **Incompleto** | Al set manca ancora un export richiesto: passa il mouse sul badge per vedere quale. Aggiungilo dalla scheda del set nella procedura guidata di importazione, con **Carica il file mancante**. |
| **Combinato** | Il file che LibreFolio ha costruito dagli export di un set — quello che l'importazione legge effettivamente. Passa il mouse sul badge per vedere i file da cui è stato costruito e quali di essi sono stati eliminati nel frattempo. |
| **Usato in un file combinato** | Questo export è stato incluso in un file combinato del suo set. |
| **Da ricombinare** | L'importatore è cambiato da quando è stato costruito il file combinato: analizzare di nuovo il set lo ricostruisce. |

Puoi visualizzare in anteprima, scaricare ed eliminare questi file come qualsiasi altro report. Eliminare un export di un set lascia al suo posto il file combinato, ma per importare di nuovo il set devi prima caricare nuovamente quell'export al suo interno.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="brim-report-sets" alt="Scheda Report del broker con i file di Danske Bank, i relativi badge Set di report e il filtro Caricato da aperto" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 👤 Chi ha caricato ciascun file {: #uploaded-by }

Entrambe le schede mostrano chi ha caricato ciascun file nella colonna **Caricato da**, con l'avatar e il nome della persona:

- fai clic sull'intestazione della colonna per ordinare per chi ha caricato;
- apri il relativo filtro per mantenere solo i file di una o più persone: selezionale nell'elenco, oppure cercale per nome;
- un file il cui autore del caricamento non è stato registrato mostra *Autore del caricamento non registrato*.

Il filtro si applica anche alla vista griglia delle **Risorse statiche**. Viene salvato nell'indirizzo della pagina, quindi un segnalibro o un link condiviso si apre con lo stesso filtro.

---

## 🔒 Accesso e limiti

- 🌐 **Risorse statiche** — ogni utente autenticato può vederle.
- 🔐 **Report del broker** — solo gli utenti con accesso al broker possono vederli; caricarli ed eliminarli richiede l'accesso come Proprietario o Editor.
- 📏 **Dimensione** — fino al limite impostato dall'amministratore nelle [Impostazioni globali](../../admin/settings.md): 10 MB se non modificato.
- 🚫 **Tipi di file** — i programmi e gli script (come i file `.exe`, `.sh` o `.py`) vengono rifiutati come risorse statiche; i report del broker devono essere file CSV o Excel.

Il luogo in cui risiedono i file sul server è descritto in [Struttura del filesystem](../../admin/filesystem.md).
