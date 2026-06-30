# 📥 Importazione da Broker (BRIM)

**BRIM** (Broker Report Import Module) ti consente di importare le transazioni direttamente dai file esportati dal tuo broker, evitando l'inserimento manuale. Carica un report CSV e LibreFolio eseguirà il parsing, l'abbinamento e l'importazione di tutte le transazioni in un unico flusso.

---

## 🚀 Come Importare

1. Esporta un report delle transazioni dal tuo broker (solitamente un file CSV o PDF — consulta il centro assistenza del tuo broker).
2. In LibreFolio, vai alla pagina delle **[Transazioni](../index.md)**.
3. Fai clic sul pulsante **Importa** (:material-file-upload:) nell'intestazione della pagina, oppure trascina e rilascia il file direttamente sulla tabella delle transazioni.
4. Si aprirà il **Wizard di Importazione**.
5. Controlla l'anteprima, verificando che date, importi e nomi degli asset siano corretti.
6. Fai clic su **Importa** per salvare tutte le transazioni nel portafoglio.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Modal di Importazione Rapida" alt="Quick Import Modal">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Step 1: Caricamento File" alt="Wizard Step 1">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Step 2: Configurazione Parser" alt="Wizard Step 2">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Step 3: Analisi" alt="Wizard Step 3">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🔍 Step 4: Risoluzione Asset" alt="Wizard Step 4">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Step 4: Rilevamento Duplicati" alt="Duplicate Detection">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Step 5: Revisione Finale" alt="Bulk Staging">
</div>

!!! tip "Creazione al Volo di Broker e Asset"

    Se il report importato contiene un conto broker o degli asset non ancora creati in LibreFolio, non è necessario uscire dal flusso di importazione! Il wizard ti guiderà nella creazione dei **[Broker](../../brokers/index.md)** e degli **[Asset](../../assets/index.md)** mancanti al volo, precompilando i dettagli con i dati rilevati dall'estratto conto.

!!! tip "Puoi anche usare la sezione File"

    La sezione **[File](../../files/index.md)** (scheda Report dei Broker) ti consente di gestire centralmente i report caricati, ri-elaborarli o eliminarli.

---

## 🧙 I Passaggi del Wizard di Importazione

Il wizard guidato contiene 5 passaggi operativi progettati per analizzare, validare, risolvere e importare lo storico delle transazioni in sicurezza.

### 🧙 Step 1: Caricamento File

Questo passaggio accetta i report CSV, XLSX o PDF esportati dal tuo broker. Puoi selezionare i file manualmente o trascinarli (drag-and-drop) direttamente nel wizard.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Wizard Step 1: Caricamento" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### ⚙️ Step 2: Configurazione Parser

Il sistema rileva automaticamente il formato del broker (ad es. Degiro, Directa, Interactive Brokers). Se carichi un foglio di calcolo generico, puoi utilizzare il parser **Generic CSV** per mappare manualmente le colonne (data, tipo, quantità, strumento, importo netto) sui campi di LibreFolio.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Wizard Step 2: Configurazione Parser" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🧠 Step 3: Analisi & Parsing

Il sistema elabora i file, validando date, numeri e valute. Verrà mostrata una barra di avanzamento che indica la velocità e lo stato di elaborazione. Al termine dell'analisi, verrà visualizzato un riepilogo di eventuali avvisi o errori di parsing prima di procedere.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Wizard Step 3: Analisi" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Al termine del parsing, la tabella mostra il riepilogo dell'elaborazione per ciascun file con le seguenti colonne statistiche contrassegnate da emoji:

| Emoji / Colonna | Nome Metrica | Significato e Regole di Popolamento |
| :--- | :--- | :--- |
| `📊` | **Transazioni** | Il numero totale di transazioni finanziarie lette e identificate all'interno del file. |
| `🏦` | **Asset Identificati** | Il numero di strumenti finanziari (azioni, ETF, ecc.) trovati all'interno delle transazioni analizzate. |
| `✗` | **Asset non Risolti** | Il numero di strumenti presenti nel file che non sono stati trovati nel database di LibreFolio (indicato in rosso se > 0, richiede mappatura nello Step 4). |
| `🔴` | **Problemi di Convalida** | Errori formali rilevati nei dati (es. formati non validi, date non corrette, dati mancanti). |
| `🔧` | **Azioni Necessarie (TODO)** | Campi o attributi che richiedono revisione (rosso se bloccanti, arancione per avvertenze/informazioni). Non indicano necessariamente un errore: indicano la presenza di dati mancanti e non estraibili automaticamente dal solo report, che potrai inserire manualmente nel modulo di transazione massivo alla fine del processo. |
| `⚠️` | **Avvisi** | Segnalazioni generali o note di avvertimento generate dal parser durante l'elaborazione. |

### 🔍 Step 4: Risoluzione Asset & Rilevamento Duplicati

Questa è la fase di riconciliazione. Il wizard esegue due controlli principali:

#### 🗂️ Risoluzione degli Asset

Se l'estratto conto contiene ticker o codici ISIN che non sono presenti nella tua libreria, il wizard li segnala. Puoi:
- Abbinarli a uno strumento già esistente nel database.
- Creare il nuovo strumento **al volo** direttamente all'interno del wizard.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Wizard Step 4: Risoluzione Asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

#### ⚠️ Rilevamento Duplicati

Il sistema confronta le transazioni del file con quelle presenti nel database per identificare potenziali doppioni in base a tipo, data, importo, quantità e descrizione.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Wizard Step 4: Rilevamento Duplicati" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

I duplicati vengono raggruppati nell'interfaccia utente in due badge di stato basandosi su 4 livelli di confidenza:

| Badge UI | Livello di Confidenza | Criterio / Regole di Abbinamento |
| :--- | :--- | :--- |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY_WITH_ASSET` | Campi base e descrizione corrispondono, ed asset risolto automaticamente (duplicato altamente probabile). |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY` | Campi base e descrizione corrispondono, ma l'asset non è risolto. |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE_WITH_ASSET` | Campi base corrispondono, ed asset risolto automaticamente (ma la descrizione differisce o è vuota). |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE` | Campi base (tipo, data, quantità, importo) corrispondono, ma l'asset non è risolto. |
| <span style="background-color: rgba(16, 185, 129, 0.15); color: #10b981; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">✅ UNICO</span> | — | La transazione non presenta alcuna corrispondenza nel database e viene considerata come nuova (duplicazione esclusa). |
| <span style="background-color: rgba(239, 68, 68, 0.15); color: #ef4444; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">❌ NON RISOLTO</span> | — | Il broker o lo strumento finanziario non sono stati abbinati a entità esistenti nel database (richiede risoluzione nello Step 4 prima di poter importare). |

Di default, il wizard deseleziona automaticamente le transazioni considerate come duplicati "Probabili" per evitare inserimenti doppi, ma l'utente può sovrascrivere tale scelta.

### 📦 Step 5: Staging e Revisione Finale

La revisione finale mostra l'elenco delle transazioni elaborate in una tabella interattiva simile a un foglio di calcolo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Wizard Step 5: Revisione Finale" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La tabella mostra:

- **Date**: La data di esecuzione.
- **Type**: ACQUISTO, VENDITA, DIVIDENDO, VERSAMENTO, ecc.
- **Asset**: L'asset corrispondente presente in LibreFolio.
- **Quantity**: Il numero di quote/unità.
- **Price**: Il prezzo unitario.
- **Net Amount**: L'impatto di cassa totale della transazione sul conto.
- **Fees/Taxes**: Commissioni e tasse incluse.

Fai clic su **Importa** per finalizzare l'importazione e salvare le transazioni nel portafoglio.

---

## 🏦 Broker Supportati

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
    <a href="ibkr/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.interactivebrokers.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="IBKR favicon">
            <span class="card-title" style="margin: 0;">Interactive Brokers</span>
        </div>
        <span class="card-desc">Importa i report delle transazioni tramite Flex Queries.</span>
    </a>
    <a href="degiro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.degiro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Degiro favicon">
            <span class="card-title" style="margin: 0;">Degiro</span>
        </div>
        <span class="card-desc">Importa lo storico delle transazioni esportate in formato CSV da Degiro.</span>
    </a>
    <a href="etoro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.etoro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="eToro favicon">
            <span class="card-title" style="margin: 0;">eToro</span>
        </div>
        <span class="card-desc">Importa estratti conto e registri in formato XLSX/CSV da eToro.</span>
    </a>
    <a href="directa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.directa.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Directa SIM favicon">
            <span class="card-title" style="margin: 0;">Directa SIM</span>
        </div>
        <span class="card-desc">Importa lo storico delle transazioni esportate in formato CSV da Directa SIM.</span>
    </a>
    <a href="schwab/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.schwab.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Charles Schwab favicon">
            <span class="card-title" style="margin: 0;">Charles Schwab</span>
        </div>
        <span class="card-desc">Importa lo storico in formato CSV da Charles Schwab.</span>
    </a>
    <a href="revolut/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Revolut favicon">
            <span class="card-title" style="margin: 0;">Revolut</span>
        </div>
        <span class="card-desc">Importa estratti conto e report in PDF/CSV da Revolut.</span>
    </a>
    <a href="coinbase/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.coinbase.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Coinbase favicon">
            <span class="card-title" style="margin: 0;">Coinbase</span>
        </div>
        <span class="card-desc">Importa report storici in formato CSV da Coinbase.</span>
    </a>
    <a href="freetrade/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Freetrade favicon">
            <span class="card-title" style="margin: 0;">Freetrade</span>
        </div>
        <span class="card-desc">Importa report storici in formato CSV da Freetrade.</span>
    </a>
    <a href="finpension/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.finpension.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Finpension favicon">
            <span class="card-title" style="margin: 0;">Finpension</span>
        </div>
        <span class="card-desc">Importa report storici in formato CSV da Finpension.</span>
    </a>
    <a href="trading212/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.trading212.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Trading212 favicon">
            <span class="card-title" style="margin: 0;">Trading212</span>
        </div>
        <span class="card-desc">Importa report storici in formato CSV da Trading212.</span>
    </a>
    <a href="generic-csv/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" style="color: var(--md-accent-fg-color);"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg>
            <span class="card-title" style="margin: 0;">CSV Generico</span>
        </div>
        <span class="card-desc">Parser di riserva con mappatura manuale delle colonne.</span>
    </a>
    <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
      <div style="display: flex; align-items: center; gap: 0.75rem;">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
      <span class="card-title" style="margin: 0;">Richiedi Plugin</span>
      </div>
      <span class="card-desc">Il tuo broker non c'è? Richiedi un nuovo parser o contribuisci al codice!</span>
    </a>
</div>

??? info "📊 Capacità dell'Importer"

    | Broker | Stato | Formato | Acquisto/Vendita | Dividendi | Depositi/Cassa | Commis./Tasse | Note |
    | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
    | <img src="https://www.interactivebrokers.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Interactive Brokers** | 🧪 Beta | CSV (Flex) | ✅ | ✅ | ✅ | ✅ | Ottimo per portafogli multivaluta |
    | <img src="https://www.degiro.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Degiro** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Supporta il resoconto standard di Degiro |
    | <img src="https://www.etoro.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **eToro** | 🧪 Beta | XLSX/CSV | ✅ | ✅ | ✅ | ✅ | Supporto profitti realizzati e dividendi |
    | <img src="https://www.directa.it/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Directa SIM** | ✅ Stable | CSV | ✅ | ✅ | ✅ | ✅ | Supporta lo storico delle transazioni Directa |
    | <img src="https://www.schwab.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Charles Schwab** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Resoconto delle attività standard US |
    | <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Revolut** | 🧪 Beta | PDF/CSV | ✅ | ✅ | ✅ | ✅ | Supporto per transazioni in azioni e crypto |
    | <img src="https://www.coinbase.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Coinbase** | 🧪 Beta | CSV | ✅ | ❌ | ✅ | ✅ | Solo report di transazione di criptovalute |
    | <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Freetrade** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Semplici resoconti dei broker del Regno Unito |
    | <img src="https://www.finpension.ch/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Finpension** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Estratti conto previdenziali pilastro 3a |
    | <img src="https://www.trading212.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Trading212** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Attività di trading europee in formato CSV |
    | <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" style="color: var(--md-accent-fg-color); vertical-align: middle; margin-right: 4px;"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> **Generic CSV** | ✅ Stable | CSV | ✅ | ✅ | ✅ | ✅ | Parser di riserva con mappatura manuale |

---

## 🗂️ Asset Mapping {: #asset-mapping }

Durante la fase di anteprima, LibreFolio tenta l'**abbinamento automatico** del nome di ciascun asset con uno strumento già presente nella tua libreria.

- ✅ **Matched** (Abbinato) — la transazione verrà associata allo strumento esistente.
- ⚠️ **Unmatched** (Non abbinato) — seleziona o crea lo strumento di destinazione prima di importare.
- ❌ **Errore** — la riga non può essere elaborata.

---

## ♻️ Rilevamento Duplicati {: #duplicate-detection }

BRIM controlla la presenza di **transazioni duplicate** basandosi su data, tipo, asset, quantità e importo. Le righe identificate come duplicate vengono evidenziate nell'anteprima, consentendoti di ignorarle o forzarne l'importazione.

---

## 🔗 Correlati

- 📋 **[Tabella delle Transazioni](../index.md)** — Visualizza e gestisci le transazioni importate
- 🗂️ **[File](../../files/index.md)** — Gestisci i file dei report caricati
- 🏦 **[Broker](../../brokers/index.md)** — Configura prima i tuoi conti broker
