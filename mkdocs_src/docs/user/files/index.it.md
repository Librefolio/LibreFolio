# 📁 File e Caricamenti

La pagina **File** (`/files`) è il tuo centro operativo per gestire tutti i contenuti caricati in LibreFolio. Presenta due sezioni distinte con diverse regole di visibilità.

---

## 📂 Due Schede, Due Scopi

### 📁 Risorse Statiche

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="files" data-name="static-tab" alt="Scheda File Statici" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Le risorse statiche sono **visibili a tutti gli utenti** del sistema. Qui troverai:

- 🖼️ **Avatar** e immagini del profilo degli utenti
- 🏷️ **Icone** e loghi dei broker
- 📄 Eventuali **documenti o immagini condivisi** caricati dagli utenti

Questi file risiedono nella directory `custom-uploads/` sul server.

Puoi passare dalla **visualizzazione elenco** a quella **a griglia** per un'anteprima visiva dei file immagine:

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="files" data-name="static-grid" alt="Vista a Griglia dei File Statici" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📊 Report dei Broker

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="files" data-name="brim-tab" alt="Scheda Report Broker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

I report dei broker hanno **visibilità ristretta** — puoi vedere solo i report dei broker a cui hai accesso (come Proprietario, Editor o Visualizzatore). Questi file includono:

- 📋 Esportazioni **di transazioni** CSV o Excel dal tuo broker
- ✅ **Risultati del parsing** dal sistema di importazione automatica (BRIM)
- ❌ File per i quali il **parsing** è fallito (conservati per il debug)

---

## ⬆️ Caricare File

Per caricare un file:

1. Fai clic sull'**area di caricamento** o **trascina e rilascia** i file direttamente
2. Per i **file immagine**, lo [strumento Ritaglia Immagine](../misc/image-crop.md) si apre automaticamente, permettendoti di ridimensionare e ritagliare prima del caricamento
3. Per i **file non immagine** (CSV, PDF, ecc.), puoi rinominare il file prima di confermare

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
 <img class="gallery-img" data-category="media" data-name="file-uploader-empty" alt="Area di Caricamento File" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! tip "Dimensione Massima dei File"

    La dimensione massima di caricamento è configurata dall'amministratore di sistema in [Impostazioni Globali](../../admin/settings.md). Il valore predefinito è tipicamente 10 MB.

---

## 📤 Caricare Report dei Broker

Se vuoi importare transazioni dal tuo broker:

1. Vai alla scheda **Report Broker**
2. Carica il file CSV o Excel esportato dal tuo broker (Degiro, Interactive Brokers, eToro, Directa, ecc.)
3. Scegli a quale **broker associare** il file — è qui che verranno salvate le transazioni importate
4. Il sistema tenterà successivamente di **rilevare automaticamente** il formato del file tramite il sistema di importazione BRIM e analizzare le transazioni

!!! info "Associazione ≠ Analisi"

    Il broker scelto durante il caricamento serve solo per l'**associazione** — determina quale conto broker riceve le transazioni importate. Il rilevamento del formato e l'analisi avvengono in un passaggio separato e sono **indipendenti** dal broker: lo stesso plugin BRIM può funzionare per più broker se esportano nello stesso formato.

!!! note "Lavori in Corso"

    L'interfaccia utente completa per l'importazione dei report broker (BRIM) è in sviluppo attivo. Attualmente, puoi caricare report e associarli ai broker, ma la procedura guidata di importazione non è ancora disponibile.

---

## 🔒 Sicurezza

- 🌐 I **file statici** sono accessibili a chiunque abbia un account LibreFolio
- 🔐 I report dei broker **seguono le regole di accesso al broker** — solo gli utenti con accesso a quel broker possono visualizzarne i report
- 🚫 I **file eseguibili** (`.exe`, `.sh`, `.py`, ecc.) sono bloccati per sicurezza
- 🔍 Il **tipo MIME** dei file viene validato lato server per prevenire mascheramenti (es. rinominare un `.exe` in `.jpg`)
