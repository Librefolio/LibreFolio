# 📥 Importa dal Broker (BRIM)

**BRIM** (Broker Report Import Module) ti consente di importare transazioni direttamente dai file di esportazione del tuo broker — nessun inserimento manuale necessario. Carica un report CSV e LibreFolio analizza, mappa e importa tutte le transazioni in un unico flusso.

Per istruzioni passo-passo su come funziona la procedura guidata, consulta la **[Guida all'Importazione](how-to.md)**.

---

## 🏦 Broker Supportati

LibreFolio supporta l'importazione di file di report dai seguenti broker:

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
 <a href="ibkr/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.interactivebrokers.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon IBKR">
 <span class="card-title" style="margin: 0;">Interactive Brokers</span>
 </div>
 <span class="card-desc">Importa report di transazioni utilizzando Flex Queries.</span>
 </a>
 <a href="degiro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.degiro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Degiro">
 <span class="card-title" style="margin: 0;">Degiro</span>
 </div>
 <span class="card-desc">Importa export CSV della cronologia delle transazioni da Degiro.</span>
 </a>
 <a href="etoro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.etoro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon eToro">
 <span class="card-title" style="margin: 0;">eToro</span>
 </div>
 <span class="card-desc">Importa file XLSX/CSV del report da eToro.</span>
 </a>
 <a href="directa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.directa.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Directa SIM">
 <span class="card-title" style="margin: 0;">Directa SIM</span>
 </div>
 <span class="card-desc">Importa file CSV della cronologia delle transazioni da Directa SIM.</span>
 </a>
 <a href="schwab/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.schwab.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Charles Schwab">
 <span class="card-title" style="margin: 0;">Charles Schwab</span>
 </div>
 <span class="card-desc">Importa la cronologia delle transazioni CSV da Charles Schwab.</span>
 </a>
 <a href="revolut/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Revolut">
 <span class="card-title" style="margin: 0;">Revolut</span>
 </div>
 <span class="card-desc">Importa report PDF/CSV del report da Revolut.</span>
 </a>
 <a href="coinbase/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.coinbase.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Coinbase">
 <span class="card-title" style="margin: 0;">Coinbase</span>
 </div>
 <span class="card-desc">Importa file CSV della cronologia delle transazioni da Coinbase.</span>
 </a>
 <a href="freetrade/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Freetrade">
 <span class="card-title" style="margin: 0;">Freetrade</span>
 </div>
 <span class="card-desc">Importa estratti conto transazioni CSV da Freetrade.</span>
 </a>
 <a href="finpension/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.finpension.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Finpension">
 <span class="card-title" style="margin: 0;">Finpension</span>
 </div>
 <span class="card-desc">Importa report CSV della cronologia delle transazioni da Finpension.</span>
 </a>
 <a href="trading212/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.trading212.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Trading212">
 <span class="card-title" style="margin: 0;">Trading212</span>
 </div>
 <span class="card-desc">Importa cronologia transazioni CSV da Trading212.</span>
 </a>
 <a href="generic-csv/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" style="color: var(--md-accent-fg-color);"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg>
 <span class="card-title" style="margin: 0;">CSV Generico</span>
 </div>
 <span class="card-desc">Il nostro parser di fallback con mappatura manuale delle colonne.</span>
 </a>
 <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
 <span class="card-title" style="margin: 0;">Richiedi un Nuovo Plugin</span>
 </div>
 <span class="card-desc">Il tuo broker manca? Richiedi un nuovo plugin o contribuisci con il codice!</span>
 </a>
</div>

??? info "📊 Capacità dell'Importatore"

    | Broker | Stato | Formato | Acquisto/Vendita | Dividendi | Depositi/Contante | Commissioni/Imposte | Note |
    | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
    | <img src="https://www.interactivebrokers.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Interactive Brokers** | 🧪 Beta | CSV (Flex) | ✅ | ✅ | ✅ | ✅ | Ideale per conti in multivaluta |
    | <img src="https://www.degiro.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Degiro** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Supporto per report standard |
    | <img src="https://www.etoro.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **eToro** | 🧪 Beta | XLSX/CSV | ✅ | ✅ | ✅ | ✅ | Supporto per plusvalenze realizzate e dividendi |
    | <img src="https://www.directa.it/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Directa SIM** | ✅ Stabile | CSV | ✅ | ✅ | ✅ | ✅ | Supporto per certificazione fiscale broker italiano |
    | <img src="https://www.schwab.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Charles Schwab** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Report attività broker USA standard |
    | <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Revolut** | 🧪 Beta | PDF/CSV | ✅ | ✅ | ✅ | ✅ | Supporto per transazioni azionarie e crypto |
    | <img src="https://www.coinbase.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Coinbase** | 🧪 Beta | CSV | ✅ | ❌ | ✅ | ✅ | Report transazioni solo crypto |
    | <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Freetrade** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Report brokeraggio UK semplici |
    | <img src="https://www.finpension.ch/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Finpension** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Report pensione svizzera 3a |
    | <img src="https://www.trading212.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Trading212** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | CSV attività di trading europea |
    | <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" style="color: var(--md-accent-fg-color); vertical-align: middle; margin-right: 4px;"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> **CSV Generico** | ✅ Stabile | CSV | ✅ | ✅ | ✅ | ✅ | Fallback con mappatura manuale |

---

## 🗂️ Mappatura degli Asset {: #asset-mapping }

Durante il passaggio di anteprima, LibreFolio tenta di **abbinare automaticamente** ogni nome di asset dal tuo report a un asset già presente nella tua libreria.

- ✅ **Abbinato** — verrà importato sull'asset esistente.
- ⚠️ **Non Abbinato** — seleziona o crea l'asset di destinazione prima di importare.
- ❌ **Errore** — la riga non può essere analizzata.

---

## ♻️ Rilevamento dei Duplicati {: #duplicate-detection }

BRIM verifica la presenza di **transazioni duplicate** in base a data, tipo, asset, quantità e importo. Le righe duplicate vengono segnalate nell'anteprima — puoi scegliere di saltarle o forzarne l'importazione.

---

## 🔗 Collegati

- 📋 **[Tabella Transazioni](../index.md)** — Visualizza e gestisci le transazioni importate
- 🗂️ **[File](../../files/index.md)** — Gestisci i file di report del broker caricati
- 🏦 **[Broker](../../brokers/index.md)** — Configura prima i tuoi conti broker
