# 📁 File e caricamenti

La pagina **File** conserva tutto ciò che è stato caricato in LibreFolio, in due schede:

- **Risorse statiche** — avatar, icone dei broker e altre immagini o documenti, ciascuno **condiviso** con tutti gli utenti o **personale** per chi lo ha caricato;
- **Report del broker** — i file degli estratti conto da cui importi le transazioni, visibili solo a chi ha accesso al relativo broker.

Gli amministratori vedono anche una terza scheda, [Backup](#backups-tab), e una barra con lo [spazio occupato dall'istanza](#space-used).

---

## 🖼️ Risorse statiche

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-tab" alt="Scheda Risorse statiche" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Qui trovi gli **avatar** degli utenti, le **icone** dei broker e le **immagini e i documenti** caricati dagli utenti: quelli condivisi, che tutti coloro che hanno un account LibreFolio possono vedere, e quelli personali, che solo tu e gli amministratori potete vedere (vedi [Condiviso o personale](#visibility)).

- Passa dalla vista **elenco** alla vista **griglia**: la griglia mostra un'anteprima delle immagini.
- Nell'elenco, fai clic con il pulsante destro su un file per **Anteprima**, **Copia link**, **Scarica** o **Elimina**. Puoi eliminare solo i file che hai caricato tu, quindi **Elimina** compare solo su di essi; un amministratore può eliminare qualsiasi file. Seleziona più file per eliminarli insieme: i file degli altri utenti restano al loro posto e un avviso te lo segnala.
- **Anteprima** mostra un PDF in un visualizzatore in sola lettura: puoi leggerlo, effettuare ricerche al suo interno e copiarne il testo, ma non modificarlo, annotarlo o stamparlo; per conservare il file, usa **Scarica**. Un PDF protetto da password richiede la password, che resta nel tuo browser: non viene mai inviata al server né salvata, e sparisce alla chiusura dell'anteprima.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-grid" alt="Vista a griglia delle risorse statiche" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### ⬆️ Carica un file

1. Fai clic su **Carica**, poi trascina i file nell'area o fai clic su di essa per sfogliare.
2. Prima di caricare, su un'immagine puoi fare clic su ✏️ **Modifica** per ritagliarla con lo [strumento di ritaglio immagini](../misc/image-crop.md), quindi confermare con **Ritaglia**; su qualsiasi altro file, ✏️ **Rinomina** ne cambia il nome. **Ripristina originale** riporta un file allo stato in cui lo hai scelto.
3. Fai clic su **Carica**. I file sono **personali**: solo tu e gli amministratori li vedete, finché non li [condividi](#visibility).

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
    <img class="gallery-img" data-category="media" data-name="file-uploader-empty" alt="Area di trascinamento per il caricamento dei file" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 👥 Condiviso o personale {: #visibility }

Ogni risorsa statica è **Condivisa** o **Personale**, come mostra il suo badge nella colonna **Visibilità** dell'elenco:

- **Condivisa** — ogni utente connesso può vederla;
- **Personale** — solo chi l'ha caricata e gli amministratori possono vederla. Gli altri utenti non la trovano nel proprio elenco e non possono aprirla, vederne l'anteprima o scaricarla.

Un file che carichi è:

- **personale** quando lo carichi da questa pagina;
- **condiviso** quando lo carichi da un selettore di immagini (la tua immagine del profilo, in **Profilo** o nella pagina di benvenuto; l'icona di un broker; l'icona di un asset), perché gli altri utenti vedono l'immagine dove la usi.

I file caricati con una versione precedente di LibreFolio sono condivisi se sono immagini, personali altrimenti.

Puoi cambiare la visibilità dei file che hai caricato; un amministratore può cambiarla per qualsiasi file:

- nell'elenco, fai clic con il pulsante destro sul file: un file personale offre **Condividi con tutti**, uno condiviso **Rendi personale**;
- nella griglia, usa lo stesso interruttore sulla scheda del file: 👥 lo condivide, 🔒 lo rende personale.

La condivisione è immediata. **Rendi personale** ti chiede prima conferma: gli altri utenti non vedranno più il file, anche dove compare come icona o foto.

Il filtro **Visibilità**, nell'intestazione della colonna, mantiene solo i file condivisi o solo quelli personali. Come il filtro [Caricato da](#uploaded-by), si applica anche alla vista a griglia ed è salvato nell'indirizzo della pagina.

La scheda **Esistenti** di un selettore di immagini elenca le immagini condivise e le tue immagini personali, anche per un amministratore. Sceglierne una delle tue immagini personali la rende condivisa, e un avviso te lo segnala: gli altri utenti possono quindi vederla dove l'hai usata.

---

## 📊 Report del broker {: #broker-reports }

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="brim-tab" alt="Scheda Report del broker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Questi sono gli estratti conto esportati dai tuoi broker, in attesa di essere importati o già importati. Vedi i report di ogni broker a cui hai accesso, come proprietario, editor o visualizzatore. I report che una versione precedente di LibreFolio ha memorizzato senza un broker sono visibili solo qui: agli amministratori e alla persona che li ha caricati, quando LibreFolio ha registrato chi lo ha fatto.

La colonna **Stato** ti dice in che condizione si trova ogni file:

- **Caricato** — memorizzato, non ancora analizzato;
- **Analizzato** — la procedura guidata di importazione lo ha letto correttamente;
- **Non riuscito** — l'analisi è fallita; il file resta qui così puoi controllarlo o segnalarlo.

### 📤 Carica un report del broker

1. In **Report del broker**, fai clic su **Carica** e scegli file CSV o Excel.
2. In **Assegna broker**, scegli il broker di ogni file, o uno per tutti con **Assegna tutti a**. **Crea nuovo** aggiunge un broker sul momento; se puoi modificare un solo broker, è già selezionato.
3. Fai clic su **Carica**. I file vengono memorizzati, ma **non viene ancora importato nulla**.

Per importarli, apri la [procedura guidata di importazione](../transactions/import/index.md) (**Transazioni** → **Importa**): il suo passo **Seleziona file** elenca i report che hai caricato.

Il broker che scegli decide solo quale conto riceve le transazioni. L'importatore riconosce da solo il formato del file, e un plugin di importazione può leggere le esportazioni di più broker.

### ⚙️ Gestire i report

Fai clic con il pulsante destro su un report per **Anteprima**, **Scarica** o **Elimina**, oppure seleziona più report per eliminarli insieme. **Elimina** compare solo sui report che puoi eliminare, ed eliminare più report lascia gli altri al loro posto, con un avviso. Eliminare un report non elimina mai le transazioni già importate da esso.

### 🧩 Set di report {: #report-sets }

Alcune banche suddividono un conto in più esportazioni: [Danske Bank](../transactions/import/danske-bank.md), per esempio, richiede un'esportazione dei titoli e un estratto del conto. Le esportazioni di una banca di questo tipo che carichi **insieme** formano un **set di report**, e LibreFolio le importa come un unico insieme, tramite un **file combinato** che costruisce a partire da esse. La colonna **Set di report** ti dice in che condizione si trova ogni file (la stessa colonna compare nei **Report caricati** di un broker):

| Badge | Significato |
|:--|:--|
| **Set del ‹data›** | Il file appartiene al set caricato in quella data, insieme alle altre esportazioni del set. |
| **Incompleto** | Al set manca ancora un'esportazione richiesta: passa il mouse sul badge per vedere quale. Aggiungila dalla scheda del set nella procedura guidata di importazione, con **Carica il file mancante**. |
| **Combinato** | Il file che LibreFolio ha costruito dalle esportazioni di un set — quello che l'importazione legge effettivamente. Passa il mouse sul badge per vedere i file da cui è stato costruito, e quali di essi sono stati eliminati nel frattempo. |
| **Usato in un file combinato** | Questa esportazione è confluita in un file combinato del suo set. |
| **Da ricombinare** | L'importatore è cambiato da quando è stato costruito il file combinato: analizzare di nuovo il set lo ricostruisce. |

Puoi vedere in anteprima, scaricare ed eliminare questi file come qualsiasi altro report. Eliminare un'esportazione di un set lascia il suo file combinato al suo posto, ma per importare di nuovo il set devi prima ricaricare quell'esportazione al suo interno.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="brim-report-sets" alt="Scheda Report del broker con i file Danske Bank, i relativi badge Set di report e il filtro Caricato da aperto" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 👤 Chi ha caricato ogni file {: #uploaded-by }

Entrambe le schede mostrano chi ha caricato ogni file nella colonna **Caricato da**, con l'avatar e il nome della persona:

- fai clic sull'intestazione della colonna per ordinare per autore del caricamento;
- apri il suo filtro per mantenere solo i file di una o più persone: selezionale nell'elenco, o cercale per nome;
- un file il cui autore del caricamento non è stato registrato mostra *Autore del caricamento non registrato*.

Il filtro si applica anche alla vista a griglia delle **Risorse statiche**. È salvato nell'indirizzo della pagina, quindi un segnalibro o un link condiviso si apre con lo stesso filtro.

---

## 🛠️ Per gli amministratori {: #admin-files }

Solo gli amministratori vedono quanto segue; gli altri utenti non trovano nessuna delle due sezioni nella pagina.

### 📊 Lo spazio utilizzato {: #space-used }

Sopra le schede, una barra mostra quanto spazio occupa l'istanza, suddiviso tra il **database**, i **file caricati**, i **report del broker**, i **backup** e gli **altri file di LibreFolio**. Se non è impostato alcun limite, è disegnata rispetto al disco, con gli altri file del disco in grigio; con un limite, rispetto a quel limite. Sotto la barra, nel pannello chiuso **Avanzate**, imposti lo **Spazio totale di LibreFolio (MB)**, `0` per nessun limite; lo stesso campo è nelle [Impostazioni globali](../../admin/settings.md) di un amministratore. Oltre il limite la barra ti avvisa, e LibreFolio rifiuta un nuovo file o report che lo aumenterebbe, dicendo a quanto portare lo spazio totale; nulla viene eliminato. La barra si aggiorna con **Aggiorna**. Come leggerla e cosa imposta il limite: [La barra dello spazio](../../admin/backup_restore.md#space-used).

### 🗃️ La scheda Backup {: #backups-tab }

La scheda **Backup** elenca i backup che LibreFolio conserva sul server, con la loro data, origine, tipo e dimensione. Per ciascuno puoi usare **Scarica** o **Elimina**. Lo stesso elenco è in **Impostazioni › Amministrazione › Backup**, dove imposti anche la pulizia automatica: vedi [Backup conservati sul server](../../admin/backup_restore.md#kept-backups).

---

## 🔒 Accesso e limiti

- 🌐 **Risorse statiche** — ogni utente connesso può vedere quelle condivise; un file personale, solo chi lo ha caricato e gli amministratori (vedi [Condiviso o personale](#visibility)). Eliminare un file e cambiare la sua visibilità spettano a chi lo ha caricato e a un amministratore.
- 🔐 **Report del broker** — solo gli utenti con accesso al broker possono vederli; il caricamento e l'eliminazione richiedono l'accesso come proprietario o editor. Un amministratore può vedere ed eliminare ogni report.
- 📏 **Dimensione** — fino al limite impostato dall'amministratore in [Impostazioni globali](../../admin/settings.md): 10 MB se non modificato.
- 🚫 **Tipi di file** — i programmi e gli script (come file `.exe`, `.sh` o `.py`) sono rifiutati come risorse statiche; i report del broker devono essere file CSV o Excel.

Dove si trovano i file sul server è descritto in [Struttura del filesystem](../../admin/filesystem.md).
