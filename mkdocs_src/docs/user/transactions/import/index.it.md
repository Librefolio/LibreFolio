# 📥 Importa dal Broker (BRIM)

<style>
/* Importer capabilities table: Broker icon+name on one line, cells vertically centered, Notes 50% wider */
.md-typeset details table th:first-child,
.md-typeset details table td:first-child { min-width: 9rem; white-space: nowrap; }
.md-typeset details .md-typeset__table table td { vertical-align: middle; }
.md-typeset details table th:last-child,
.md-typeset details table td:last-child { min-width: 24rem; }
/* Broker icon fallback: the letter tile sits after the image, hidden; onerror swaps them */
.broker-icon-fallback { display: inline-flex; align-items: center; vertical-align: middle; margin-right: 4px; }
.broker-icon-fallback > span { display: none; width: 16px; height: 16px; align-items: center; justify-content: center; font-size: 9px; font-weight: 700; color: var(--md-accent-fg-color); }
</style>

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
 <span class="card-desc">Importa file CSV dell'estratto conto da eToro.</span>
 </a>
 <a href="directa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.directa.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Directa SIM">
 <span class="card-title" style="margin: 0;">Directa SIM</span>
 </div>
 <span class="card-desc">Importa file CSV o XLSX della cronologia delle transazioni da Directa SIM.</span>
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
 <span class="card-desc">Importa report CSV dell'estratto conto da Revolut.</span>
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
 <img src="https://www.trading212.com/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Trading212">
 <span class="card-title" style="margin: 0;">Trading212</span>
 </div>
 <span class="card-desc">Importa cronologia transazioni CSV da Trading212.</span>
 </a>
 <a href="avanza/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://avanza.se/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Avanza">
 <span class="card-title" style="margin: 0;">Avanza</span>
 </div>
 <span class="card-desc">Importa l'export CSV della cronologia transazioni da Avanza.</span>
 </a>
 <a href="bux/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://bux.com/it/wp-content/themes/vo-theme/assets/images/favicon/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon BUX">
 <span class="card-title" style="margin: 0;">BUX</span>
 </div>
 <span class="card-desc">Importa l'export CSV della cronologia transazioni da BUX.</span>
 </a>
 <a href="disnat/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://disnat.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Disnat">
 <span class="card-title" style="margin: 0;">Disnat</span>
 </div>
 <span class="card-desc">Importa l'export CSV della cronologia transazioni da Disnat.</span>
 </a>
 <a href="investengine/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.investengine.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon InvestEngine">
 <span class="card-title" style="margin: 0;">InvestEngine</span>
 </div>
 <span class="card-desc">Importa l'export CSV della cronologia transazioni da InvestEngine.</span>
 </a>
    <a href="rabobank/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.rabobank.com/static/msp/global-sites/rds/favicons/favicon-svg.svg" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Rabobank">
    <span class="card-title" style="margin: 0;">Rabobank</span>
    </div>
    <span class="card-desc">Importa l'export della cronologia delle transazioni in formato CSV da Rabobank.</span>
    </a>
    <a href="fineco/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://finecobank.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Fineco">
    <span class="card-title" style="margin: 0;">Fineco</span>
    </div>
    <span class="card-desc">Importa l'export CSV "Movimenti Dossier Titoli" da Fineco.</span>
    </a>
    <a href="intesa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.intesasanpaolo.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Intesa Sanpaolo">
    <span class="card-title" style="margin: 0;">Intesa Sanpaolo</span>
    </div>
    <span class="card-desc">Importa i movimenti CSV/XLSX o gli export patrimonio da Intesa Sanpaolo.</span>
    </a>
    <a href="credit_agricole/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.credit-agricole.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Crédit Agricole">
    <span class="card-title" style="margin: 0;">Crédit Agricole</span>
    </div>
    <span class="card-desc">Importa movimenti conto da Crédit Agricole — cassa reale, commissioni, tasse e cedole/dividendi; export titoli opzionale per storico oltre 2 anni.</span>
    </a>
 <a href="traderepublic/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://traderepublic.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Trade Republic">
 <span class="card-title" style="margin: 0;">Trade Republic</span>
 </div>
 <span class="card-desc">Importa l'export CSV della cronologia transazioni da Trade Republic.</span>
 </a>
 <a href="xtb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.xtb.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon XTB">
 <span class="card-title" style="margin: 0;">XTB</span>
 </div>
 <span class="card-desc">Importa l'export CSV della cronologia transazioni da XTB.</span>
 </a>
 <a href="parqet/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://parqet.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Parqet">
 <span class="card-title" style="margin: 0;">Parqet</span>
 </div>
 <span class="card-desc">Importa l'export CSV della cronologia transazioni da Parqet.</span>
 </a>
 <a href="saxo/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://home.saxo/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Saxo">
 <span class="card-title" style="margin: 0;">Saxo</span>
 </div>
 <span class="card-desc">Importa l'export CSV della cronologia transazioni da Saxo.</span>
 </a>
 <a href="swissquote/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.swissquote.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Swissquote">
 <span class="card-title" style="margin: 0;">Swissquote</span>
 </div>
 <span class="card-desc">Importa l'export CSV della cronologia transazioni da Swissquote.</span>
 </a>
 <a href="bitvavo/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://bitvavo.com/favicon-32x32.png?v=7ba51b544a17c10de8defa086df79917" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Bitvavo">
 <span class="card-title" style="margin: 0;">Bitvavo</span>
 </div>
 <span class="card-desc">Importa l'export CSV della cronologia transazioni da Bitvavo (crypto).</span>
 </a>
 <a href="cryptocom/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://crypto.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Crypto.com">
 <span class="card-title" style="margin: 0;">Crypto.com</span>
 </div>
 <span class="card-desc">Importa l'export CSV della cronologia transazioni da Crypto.com (crypto).</span>
 </a>
 <a href="relai/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://relai.app/app/uploads/2023/06/cropped-App-icon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Relai">
 <span class="card-title" style="margin: 0;">Relai</span>
 </div>
 <span class="card-desc">Importa l'export CSV della cronologia transazioni da Relai (crypto).</span>
 </a>
 <a href="cointracking/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://cointracking.info/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon CoinTracking">
 <span class="card-title" style="margin: 0;">CoinTracking</span>
 </div>
 <span class="card-desc">Importa l'export CSV della cronologia transazioni da CoinTracking (crypto).</span>
 </a>
 <a href="delta/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.google.com/s2/favicons?domain=delta.app&amp;sz=64" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Delta">
 <span class="card-title" style="margin: 0;">Delta</span>
 </div>
 <span class="card-desc">Importa l'export CSV della cronologia transazioni da Delta (crypto).</span>
 </a>
 <a href="investimental/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.investimental.ro/wp-content/themes/investimental/img/favicon/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Investimental">
 <span class="card-title" style="margin: 0;">Investimental</span>
 </div>
 <span class="card-desc">Importa l'export CSV della cronologia transazioni da Investimental.</span>
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
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.interactivebrokers.com/favicon.ico" width="16" height="16" style=""><span>IB</span></span> **Interactive Brokers** | 🧪 Beta | CSV (Flex) | ✅ | ✅ | ✅ | ✅ | Ideale per conti in multivaluta |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.degiro.com/favicon.ico" width="16" height="16" style=""><span>DE</span></span> **Degiro** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Supporto per report standard |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.etoro.com/favicon.ico" width="16" height="16" style=""><span>ET</span></span> **eToro** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Supporto per plusvalenze realizzate e dividendi |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.directa.it/favicon.ico" width="16" height="16" style=""><span>DS</span></span> **Directa SIM** | ✅ Stabile | CSV/XLSX | ✅ | ✅ | ✅ | ✅ | Supporto per certificazione fiscale broker italiano |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.schwab.com/favicon.ico" width="16" height="16" style=""><span>CS</span></span> **Charles Schwab** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Report attività broker USA standard |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="16" height="16" style=""><span>RE</span></span> **Revolut** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Supporto per transazioni azionarie e crypto |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.coinbase.com/favicon.ico" width="16" height="16" style=""><span>CO</span></span> **Coinbase** | 🧪 Beta | CSV | ✅ | ❌ | ✅ | ✅ | Report transazioni solo crypto |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="16" height="16" style=""><span>FR</span></span> **Freetrade** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Report brokeraggio UK semplici |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.finpension.ch/favicon.ico" width="16" height="16" style=""><span>FI</span></span> **Finpension** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Report pensione svizzera 3a |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.trading212.com/favicon-32x32.png" width="16" height="16" style=""><span>TR</span></span> **Trading212** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | CSV attività di trading europea |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://avanza.se/favicon.ico" width="16" height="16" style=""><span>AV</span></span> **Avanza** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Scritto sui file di esempio |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://bux.com/it/wp-content/themes/vo-theme/assets/images/favicon/favicon-32x32.png" width="16" height="16" style=""><span>BU</span></span> **BUX** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Scritto sui file di esempio |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://disnat.com/favicon.ico" width="16" height="16" style=""><span>DI</span></span> **Disnat** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Scritto sui file di esempio |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.investengine.com/favicon.ico" width="16" height="16" style=""><span>IN</span></span> **InvestEngine** | 🧪 Beta | CSV | ✅ | ✅ | ❌ | ❌ | Scritto sui file di esempio |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.rabobank.com/static/msp/global-sites/rds/favicons/favicon-svg.svg" width="16" height="16" style=""><span>RA</span></span> **Rabobank** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Scritto sui file di esempio |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://finecobank.com/favicon.ico" width="16" height="16" style=""><span>FI</span></span> **Fineco** | 🧪 Beta | CSV | ✅ | ✅ | ❌ | ✅ | Entrambi i layout di export; importi nella valuta del report |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.intesasanpaolo.com/favicon.ico" width="16" height="16" style=""><span>IS</span></span> **Intesa Sanpaolo** | 🧪 Beta | CSV/XLSX | ❌ | ✅ | ✅ | ✅ | Movimenti cedole/dividendi/commissioni/tasse; snapshot patrimonio alimenta liquidità quando presente + posizioni |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.credit-agricole.it/favicon.ico" width="16" height="16" style=""><span>CA</span></span> **Crédit Agricole** | ✅ Stabile | CSV/XLSX | ✅ | ✅ | ✅ | ✅ | I movimenti del conto portano liquidità reale, commissioni, tasse e cedole/dividendi; l'export titoli opzionale recupera lo storico oltre 2 anni; contro-voci automatiche di cassa, scadenze e rettifiche di successione |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://traderepublic.com/favicon.ico" width="16" height="16" style=""><span>TR</span></span> **Trade Republic** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Scritto sui file di esempio |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.xtb.com/favicon.ico" width="16" height="16" style=""><span>XT</span></span> **XTB** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Scritto sui file di esempio |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://parqet.com/favicon.ico" width="16" height="16" style=""><span>PA</span></span> **Parqet** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Scritto sui file di esempio |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://home.saxo/favicon.ico" width="16" height="16" style=""><span>SA</span></span> **Saxo** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Scritto sui file di esempio |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.swissquote.com/favicon.ico" width="16" height="16" style=""><span>SW</span></span> **Swissquote** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Scritto sui file di esempio |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://bitvavo.com/favicon-32x32.png?v=7ba51b544a17c10de8defa086df79917" width="16" height="16" style=""><span>BI</span></span> **Bitvavo** | 🧪 Beta | CSV | ✅ | ❌ | ✅ | ✅ | Exchange crypto — scritto sui file di esempio |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://crypto.com/favicon.ico" width="16" height="16" style=""><span>CC</span></span> **Crypto.com** | 🧪 Beta | CSV | ✅ | ❌ | ❌ | ❌ | Exchange crypto — scritto sui file di esempio |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://relai.app/app/uploads/2023/06/cropped-App-icon-32x32.png" width="16" height="16" style=""><span>RE</span></span> **Relai** | 🧪 Beta | CSV | ✅ | ❌ | ❌ | ✅ | Exchange crypto — scritto sui file di esempio |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://cointracking.info/favicon.ico" width="16" height="16" style=""><span>CO</span></span> **CoinTracking** | 🧪 Beta | CSV | ✅ | ❌ | ✅ | ✅ | Exchange crypto — scritto sui file di esempio |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.google.com/s2/favicons?domain=delta.app&amp;sz=64" width="16" height="16" style=""><span>DE</span></span> **Delta** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Exchange crypto — scritto sui file di esempio |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.investimental.ro/wp-content/themes/investimental/img/favicon/favicon.ico" width="16" height="16" style=""><span>IN</span></span> **Investimental** | 🧪 Beta | CSV | ✅ | ❌ | ❌ | ✅ | Scritto sui file di esempio |
    | <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" style="color: var(--md-accent-fg-color); vertical-align: middle; margin-right: 4px;"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> **CSV Generico** | ✅ Stabile | CSV | ✅ | ✅ | ✅ | ✅ | Fallback con mappatura manuale |

---

## 🗂️ Mappatura degli Asset {: #asset-mapping }

Durante il passaggio di anteprima, LibreFolio tenta di **abbinare automaticamente** ogni nome di asset dal tuo report a un asset già presente nella tua libreria.

- ✅ **Abbinato** — verrà importato sull'asset esistente.
- ⚠️ **Non Abbinato** — seleziona o crea l'asset di destinazione prima di importare.
- ❌ **Errore** — la riga non può essere analizzata.

---

## ♻️ Rilevamento dei Duplicati {: #duplicate-detection }

BRIM verifica la presenza di **transazioni duplicate** all'interno dello stesso broker confrontando **tipo, data, quantità e importo/valuta di cassa** (con piccole tolleranze per gli arrotondamenti). Una **descrizione** corrispondente porta una segnalazione da *possibile* a *probabile*; un **asset** corrispondente — quando la riga del report è stata abbinata automaticamente alla tua libreria — aumenta a sua volta il livello di confidenza. Le righe duplicate vengono segnalate nell'anteprima — puoi scegliere di saltarle o forzarne l'importazione.

---

## ⛔ Prima della data di apertura del broker {: #before-opening }

Se un broker ha una **data di apertura** impostata, qualsiasi transazione con data **antecedente** viene contrassegnata nell'anteprima come **"Prima dell'apertura"** e non può essere importata (la relativa casella di spunta è disabilitata). Il giorno dell'apertura rimane valido. Se una riga è segnalata per errore, usa l'azione **Modifica data broker**, quindi **ricontrolla / aggiorna** per rivalutare le righe.

---

## 🔗 Collegati

- 📋 **[Tabella Transazioni](../index.md)** — Visualizza e gestisci le transazioni importate
- 🗂️ **[File](../../files/index.md)** — Gestisci i file di report del broker caricati
- 🏦 **[Broker](../../brokers/index.md)** — Configura prima i tuoi conti broker
