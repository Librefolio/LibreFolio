# 📥 Importazione dal Broker (BRIM)

**BRIM** (Broker Report Import Module) ti permette di importare le transazioni direttamente dai file di esportazione del tuo broker — nessun inserimento manuale richiesto. Carica un report CSV e LibreFolio analizzerà, mapperà e importerà tutte le transazioni in un unico flusso.

---

## 🚀 Come Importare

1. Esporta un report delle transazioni dal tuo broker (solitamente un file CSV — consulta il centro assistenza del tuo broker).
2. In LibreFolio, naviga alla pagina del tuo **Broker**.
3. Clicca sul pulsante **Importa** (:material-file-upload:) nell'intestazione del broker.
4. Si apre la **finestra modale di importazione**.
5. **Trascina e rilascia** o clicca per selezionare il tuo file.
6. LibreFolio **rileva automaticamente** il formato del broker e mostra un'**anteprima** delle transazioni analizzate.
7. Rivedi l'anteprima — verifica che date, importi e nomi degli asset siano corretti.
8. Clicca su **Importa** per confermare tutte le transazioni.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Modale di Importazione Rapida" alt="Modale di Importazione Rapida">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Step 1: Caricamento File Report" alt="Wizard Step 1">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Step 2: Configurazione Parser" alt="Wizard Step 2">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🔍 Step 3: Risoluzione Asset" alt="Wizard Step 3">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Rilevamento Duplicati" alt="Rilevamento Duplicati">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Revisione Staging Massivo" alt="Staging Massivo">
</div>

!!! tip "Puoi utilizzare anche la sezione File"

    La sezione **[Files](../../files/index.md)** (scheda BRIM) ti permette di gestire centralmente i report dei broker caricati, re-importarli o eliminarli.

---

## 🏦 Broker Supportati

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
 <a href="ibkr/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.interactivebrokers.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="IBKR favicon">
 <span class="card-title" style="margin: 0;">Interactive Brokers</span>
 </div>
 <span class="card-desc">Importa report di transazione utilizzando le Flex Queries.</span>
 </a>
 <a href="degiro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.degiro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Degiro favicon">
 <span class="card-title" style="margin: 0;">Degiro</span>
 </div>
 <span class="card-desc">Importa esportazioni CSV della cronologia transazioni da Degiro.</span>
 </a>
 <a href="etoro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.etoro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="eToro favicon">
 <span class="card-title" style="margin: 0;">eToro</span>
 </div>
 <span class="card-desc">Importa file XLSX/CSV dell'estratto conto da eToro.</span>
 </a>
 <a href="directa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.directa.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Directa SIM favicon">
 <span class="card-title" style="margin: 0;">Directa SIM</span>
 </div>
 <span class="card-desc">Importa file CSV della cronologia transazioni da Directa SIM.</span>
 </a>
 <a href="schwab/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.schwab.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Charles Schwab favicon">
 <span class="card-title" style="margin: 0;">Charles Schwab</span>
 </div>
 <span class="card-desc">Importa la cronologia transazioni CSV da Charles Schwab.</span>
 </a>
 <a href="revolut/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Revolut favicon">
 <span class="card-title" style="margin: 0;">Revolut</span>
 </div>
 <span class="card-desc">Importa report PDF/CSV dell'estratto conto da Revolut.</span>
 </a>
 <a href="coinbase/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.coinbase.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Coinbase favicon">
 <span class="card-title" style="margin: 0;">Coinbase</span>
 </div>
 <span class="card-desc">Importa file CSV della cronologia transazioni da Coinbase.</span>
 </a>
 <a href="freetrade/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Freetrade favicon">
 <span class="card-title" style="margin: 0;">Freetrade</span>
 </div>
 <span class="card-desc">Importa estratti conto delle transazioni CSV da Freetrade.</span>
 </a>
 <a href="finpension/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.finpension.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Finpension favicon">
 <span class="card-title" style="margin: 0;">Finpension</span>
 </div>
 <span class="card-desc">Importa report CSV della cronologia transazioni da Finpension.</span>
 </a>
 <a href="trading212/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.trading212.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Trading212 favicon">
 <span class="card-title" style="margin: 0;">Trading212</span>
 </div>
 <span class="card-desc">Importa la cronologia transazioni CSV da Trading212.</span>
 </a>
 <a href="generic-csv/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" style="color: var(--md-accent-fg-color);"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg>
 <span class="card-title" style="margin: 0;">CSV Generico</span>
 </div>
 <span class="card-desc">Il nostro parser di fallback con mappatura manuale delle colonne.</span>
 </a>
</div>

### 📊 Capacità dell'Importer

| Broker | Formato | Acquisto/Vendita | Dividendi | Depositi/Cash | Commissioni/Tasse | Note |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **Interactive Brokers** | CSV (Flex) | ✅ | ✅ | ✅ | ✅ | Ideale per conti multi-valuta |
| **Degiro** | CSV | ✅ | ✅ | ✅ | ✅ | Supporto per estratto conto standard |
| **eToro** | XLSX/CSV | ✅ | ✅ | ✅ | ✅ | Supporto per plusvalenze realizzate e dividendi |
| **Directa SIM** | CSV | ✅ | ✅ | ✅ | ✅ | Supporto per estratto conto fiscale broker italiano |
| **Charles Schwab** | CSV | ✅ | ✅ | ✅ | ✅ | Estratto conto attività broker USA standard |
| **Revolut** | PDF/CSV | ✅ | ✅ | ✅ | ✅ | Supporto per transazioni azioni e crypto |
| **Coinbase** | CSV | ✅ | ❌ | ✅ | ✅ | Report transazioni solo crypto |
| **Freetrade** | CSV | ✅ | ✅ | ✅ | ✅ | Estratti conto brokerage UK semplici |
| **Finpension** | CSV | ✅ | ✅ | ✅ | ✅ | Estratti conto pensione svizzera 3a |
| **Trading212** | CSV | ✅ | ✅ | ✅ | ✅ | CSV attività trading europea |
| **CSV Generico** | CSV | ✅ | ✅ | ✅ | ✅ | Fallback con mappatore manuale delle colonne |

!!! note "Tutti i provider sono in Beta"

    I plugin di importazione sono mantenuti dalla community e migliorano nel tempo. Se un formato di report specifico presenta anomalie, il provider **[CSV Generico](generic-csv/)** permette la mappatura manuale delle colonne come soluzione alternativa.

---

## 🗂️ Mappatura Asset

Durante la fase di anteprima, LibreFolio tenta di **abbinare automaticamente** ogni nome di asset dal tuo report a un asset già presente nella tua libreria.

- ✅ **Abbinato** — verrà importato nell'asset esistente.
- ⚠️ **Non abbinato** — seleziona o crea l'asset di destinazione prima dell'importazione.
- ❌ **Errore** — la riga non ha potuto essere analizzata.

---

## ♻️ Rilevamento Duplicati

BRIM verifica la presenza di **transazioni duplicate** in base a data, tipo, asset, quantità e importo. Le righe duplicate vengono segnalate nell'anteprima — puoi scegliere di saltarle o forzarne l'importazione.

---

## 🔗 Correlati

- 📋 **[Tabella Transazioni](../index.md)** — Visualizza e gestisci le transazioni importate
- 🗂️ **[Files](../../files/index.md)** — Gestisci i file dei report dei broker caricati
- 🏦 **[Brokers](../../brokers/index.md)** — Configura prima i tuoi conti broker
