# 📁 File e Caricamenti

La pagina **File** (`/files`) è il tuo hub centrale per la gestione di tutti i contenuti caricati in LibreFolio. È composta da due sezioni distinte con diverse regole di visibilità.

---

## 📂 Due Schede, Due Scopi

### 📁 Risorse Statiche

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="files" data-name="static-tab" alt="Static Files Tab" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Le risorse statiche sono **visibili a tutti gli utenti** del sistema. Qui troverai:

- 🖼️ **Avatar** e immagini del profilo utente
- 🏷️ **Icone** e loghi dei broker
- 📄 Qualsiasi **documento condiviso** o immagine caricata dagli utenti

Questi file risiedono nella directory `custom-uploads/` sul server.

Puoi passare dalla **visualizzazione a elenco** alla **visualizzazione a griglia** per un'anteprima visiva dei file immagine:

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="files" data-name="static-grid" alt="Static Files Grid View" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📊 Report dei Broker

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="files" data-name="brim-tab" alt="Broker Reports Tab" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

I report dei broker hanno una **visibilità ristretta**: puoi vedere solo i report dei broker a cui hai accesso (come proprietario, editor o visualizzatore). Questi file includono:

- 📋 **Esportazioni transazioni** in CSV o Excel dal tuo broker
- ✅ **Risultati del parsing** dal sistema di importazione automatica (BRIM)
- ❌ File il cui **parsing è fallito** (conservati per il debugging)

---

## ⬆️ Caricare File

Per caricare un file:

1. Clicca l'**area di caricamento** o **trascina e rilascia** i file direttamente
2. Per i **file immagine**, lo [strumento di ritaglio immagini](../misc/image-crop.md) si apre automaticamente, permettendoti di ridimensionare e ritagliare prima del caricamento
3. Per i **file non immagine** (CSV, PDF, ecc.), puoi rinominare il file prima di confermare

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
 <img class="gallery-img" data-category="media" data-name="file-uploader-empty" alt="File Upload Drop Zone" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! tip "Limite Dimensioni File"

    La dimensione massima di caricamento è configurata dall'amministratore di sistema nelle [Impostazioni Globali](../../admin/settings.md). Il valore predefinito è solitamente 10 MB.

---

## 📤 Caricare Report dei Broker

Se desideri importare le transazioni dal tuo broker:

1. Vai alla scheda **Report dei Broker**
2. Carica il file CSV o Excel esportato dal tuo broker (Degiro, Interactive Brokers, eToro, Directa, ecc.)
3. Scegli quale **broker associare** al file: è qui che verranno memorizzate le transazioni importate
4. Il sistema tenterà successivamente di **rilevare automaticamente** il formato del file tramite il sistema di importazione BRIM e di effettuare il parsing delle transazioni

!!! info "Associazione ≠ Parsing"

    Il broker scelto durante il caricamento serve solo per l'**associazione**: determina quale account broker riceve le transazioni importate. Il rilevamento del formato e il parsing avvengono in un passaggio separato e sono **indipendenti** dal broker: lo stesso plugin BRIM può funzionare per più broker se esportano nello stesso formato.

!!! note "Lavoro in Corso"

    L'interfaccia utente completa per l'importazione dei report broker (BRIM) è in fase di sviluppo attivo. Attualmente, è possibile caricare i report e associarli ai broker, ma la procedura guidata di importazione non è ancora disponibile.

---

## 🔒 Sicurezza

- 🌐 I **file statici** sono accessibili a chiunque possieda un account LibreFolio
- 🔐 I **report dei broker** rispettano il controllo di accesso del broker: solo gli utenti con accesso a quel broker possono visualizzarne i report
- 🚫 I **file eseguibili** (`.exe`, `.sh`, `.py`, ecc.) sono bloccati per motivi di sicurezza
- 🔍 Il **MIME type** del file viene validato lato server per evitare la falsificazione dell'estensione (es. rinominare un `.exe` in `.jpg`)
