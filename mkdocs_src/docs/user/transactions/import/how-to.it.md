# 🧙 Come Importare le Transazioni

Scopri come utilizzare il Modulo di Importazione Report Broker (BRIM) per importare le tue transazioni passo dopo passo.

---

## 🚀 Guida Passo-Passo

1. Esporta un report delle transazioni dal tuo broker (di solito un file CSV — controlla il centro assistenza del tuo broker).
2. In LibreFolio, vai alla pagina **[Transazioni](../index.md)**.
3. Clicca sul pulsante **Importa** (:material-file-upload:) nell'intestazione della pagina, oppure trascina e rilascia il tuo file dell'estratto conto direttamente nell'elenco delle transazioni.
4. Si apre la **Procedura Guidata di Importazione**.
5. Controlla l'anteprima — verifica che date, importi e nomi degli asset siano corretti.
6. Clicca su **Importa** per confermare tutte le transazioni.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Modale di Importazione Rapida" alt="Modale di Importazione Rapida">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Passo 1: Carica il File del Report" alt="Procedura Guidata Passo 1">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Passo 2: Configurazione del Parser" alt="Procedura Guidata Passo 2">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Passo 3: Analisi" alt="Procedura Guidata Passo 3">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🔍 Passo 4: Risoluzione Asset" alt="Procedura Guidata Passo 4">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Passo 4: Rilevamento Duplicati" alt="Rilevamento Duplicati">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Passo 5: Revisione Preparatoria in Blocco" alt="Preparazione in Blocco">
</div>

!!! tip "Creazione al Volo di Broker e Asset"

    Se il report importato contiene un conto broker o asset che non sono ancora stati creati in LibreFolio, non devi uscire dal flusso di importazione! La procedura guidata ti guiderà nella creazione al volo dei **[Broker](../../brokers/index.md)** e degli **[Asset](../../assets/index.md)** mancanti, pre-compilando i dettagli dall'estratto conto.

!!! tip "Puoi anche usare la sezione File"

    La sezione **[File](../../files/index.md)** (scheda BRIM) ti permette di gestire centralmente i report broker caricati, reimportarli o eliminarli.

---

## 🧙 I Passi della Procedura Guidata di Importazione

La procedura guidata contiene 5 passi operativi progettati per analizzare, validare, risolvere e importare la tua cronologia delle transazioni in modo sicuro.

### 🧙 Passo 1: Carica il File del Report

Questo passaggio accetta report CSV, XLSX o PDF esportati dal tuo broker. Puoi selezionare i file manualmente o trascinarli e rilasciarli direttamente nella procedura guidata.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Procedura Guidata Passo 1: Carica" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### ⚙️ Passo 2: Configurazione del Parser

Il sistema rileva automaticamente il formato del broker (es. Degiro, Directa, Interactive Brokers). Se carichi un foglio di calcolo generico, puoi usare il parser **CSV Generico** per mappare manualmente le tue colonne (data, tipo, quantità, asset, importo netto) ai campi di LibreFolio.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Procedura Guidata Passo 2: Configurazione del Parser" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🧠 Passo 3: Analisi e Parsing

Il sistema analizza i file, validando date, numeri e valute. Vedrai una barra di avanzamento che indica la velocità e lo stato dell'analisi. Una volta completata l'analisi, eventuali avvisi o errori di parsing verranno riassunti prima di continuare.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Procedura Guidata Passo 3: Analisi" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Al termine dell'analisi, la tabella mostra un riepilogo dell'elaborazione per ogni file con le seguenti colonne statistiche contrassegnate da emoji:

| Emoji / Colonna | Nome della Metrica | Significato e Regole di Popolamento |
| :--- | :--- | :--- |
| `📊` | **Transazioni** | Il numero totale di transazioni finanziarie lette e identificate all'interno del file. |
| `🏦` | **Asset Identificati** | Il numero di strumenti finanziari (azioni, ETF, ecc.) trovati nelle transazioni analizzate. |
| `✗` | **Asset Non Risolti** | Il numero di strumenti nel file che non sono stati trovati nel database di LibreFolio (contrassegnato in rosso se > 0, richiede mappatura nel Passo 4). |
| `🔴` | **Problemi di Validazione** | Errori formali rilevati nei dati (es. formati non validi, date errate, dati obbligatori mancanti). |
| `🔧` | **Azione Richiesta (TODO)** | Campi o attributi che richiedono attenzione (rosso se bloccante, arancione per azioni a livello di avviso/informativo). Non sono necessariamente errori: indicano semplicemente dati mancanti che non possono essere estratti automaticamente dal solo estratto conto, che puoi facilmente compilare manualmente nel modulo di transazione bulk alla fine della procedura guidata. |
| `⚠️` | **Avvisi** | Notifiche generali o messaggi di avviso generati dal parser durante l'elaborazione. |

### 🔍 Passo 4: Mappatura Asset e Rilevamento Duplicati

Questa è la fase di riconciliazione. La procedura guidata esegue due controlli fondamentali:

#### 🗂️ Risoluzione Asset

Se l'estratto conto contiene simboli ticker o ISIN che non sono nella tua libreria, la procedura guidata li segnala. Puoi:

- Mapparli a un asset esistente nel tuo database.
- Crearli **al volo** direttamente all'interno della procedura guidata.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Procedura Guidata Passo 4: Risoluzione Asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

#### ⚠️ Rilevamento Duplicati

Il sistema confronta le voci analizzate con il tuo database per trovare potenziali duplicati in base a tipo, data, importo, quantità e descrizione.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Procedura Guidata Passo 4: Rilevamento Duplicati" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

I duplicati vengono segnalati nell'interfaccia utilizzando due badge di stato basati su 4 livelli di confidenza:

| Badge UI | Livello di Confidenza | Criteri / Regole di Corrispondenza |
| :--- | :--- | :--- |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ PROBABILE</span> | `LIKELY_WITH_ASSET` | Campi di base e descrizione corrispondono, e asset auto-risolto (duplicato altamente probabile). |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ PROBABILE</span> | `LIKELY` | Campi di base e descrizione corrispondono, ma asset non risolto. |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBILE</span> | `POSSIBLE_WITH_ASSET` | Campi di base corrispondono, e asset auto-risolto (ma la descrizione differisce o è vuota). |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBILE</span> | `POSSIBLE` | Campi di base (tipo, data, quantità, importo) corrispondono, ma asset non risolto. |
| <span style="background-color: rgba(16, 185, 129, 0.15); color: #10b981; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">✅ UNICO</span> | — | La transazione non ha record corrispondenti nel database ed è classificata come nuova (nessun duplicato rilevato). |
| <span style="background-color: rgba(239, 68, 68, 0.15); color: #ef4444; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">❌ NON RISOLTO</span> | — | Il broker o lo strumento finanziario non è stato associato a un'entità esistente nel database (richiede risoluzione nel Passo 4 prima dell'importazione). |

Per impostazione predefinita, la procedura guidata deseleziona automaticamente i duplicati "Probabili" per evitare la doppia registrazione, ma puoi modificare questa scelta.

### 📦 Passo 5: Revisione Preparatoria in Blocco

La revisione finale mostra l'elenco analizzato in una griglia simile a un foglio di calcolo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Procedura Guidata Passo 5: Revisione Preparatoria in Blocco" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La tabella mostra:

- **Data**: La data di esecuzione.
- **Tipo**: ACQUISTO, VENDITA, DIVIDENDO, DEPOSITO, ecc.
- **Asset**: L'asset corrispondente dalla tua libreria.
- **Quantità**: Il numero di unità/azioni.
- **Prezzo**: Il prezzo unitario.
- **Importo Netto**: L'impatto totale in contanti.
- **Commissioni/Tasse**: Commissioni e tasse incluse.

Clicca su **Importa** per finalizzare l'importazione e scrivere le transazioni nel tuo registro.
