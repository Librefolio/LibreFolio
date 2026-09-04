# 📥 Import from Broker (BRIM)

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


**BRIM** (Broker Report Import Module) lets you import transactions directly from your broker's export files — no manual entry needed. Upload a CSV report and LibreFolio parses, maps, and imports all transactions in one flow.

For step-by-step instructions on how the wizard works, check out the **[How to Import Guide](how-to.md)**.

---

## 🏦 Supported Brokers

LibreFolio supports importing statement files from the following brokers:

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
    <a href="ibkr/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.interactivebrokers.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="IBKR favicon">
            <span class="card-title" style="margin: 0;">Interactive Brokers</span>
        </div>
        <span class="card-desc">Import transaction reports using Flex Queries.</span>
    </a>
    <a href="degiro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.degiro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Degiro favicon">
            <span class="card-title" style="margin: 0;">Degiro</span>
        </div>
        <span class="card-desc">Import transaction history CSV exports from Degiro.</span>
    </a>
    <a href="etoro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.etoro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="eToro favicon">
            <span class="card-title" style="margin: 0;">eToro</span>
        </div>
        <span class="card-desc">Import account statement CSV files from eToro.</span>
    </a>
    <a href="directa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.directa.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Directa SIM favicon">
            <span class="card-title" style="margin: 0;">Directa SIM</span>
        </div>
        <span class="card-desc">Import transaction history CSV or XLSX files from Directa SIM.</span>
    </a>
    <a href="schwab/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.schwab.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Charles Schwab favicon">
            <span class="card-title" style="margin: 0;">Charles Schwab</span>
        </div>
        <span class="card-desc">Import CSV transaction history from Charles Schwab.</span>
    </a>
    <a href="revolut/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Revolut favicon">
            <span class="card-title" style="margin: 0;">Revolut</span>
        </div>
        <span class="card-desc">Import account statement CSV reports from Revolut.</span>
    </a>
    <a href="coinbase/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.coinbase.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Coinbase favicon">
            <span class="card-title" style="margin: 0;">Coinbase</span>
        </div>
        <span class="card-desc">Import transaction history CSV files from Coinbase.</span>
    </a>
    <a href="freetrade/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Freetrade favicon">
            <span class="card-title" style="margin: 0;">Freetrade</span>
        </div>
        <span class="card-desc">Import CSV transaction statements from Freetrade.</span>
    </a>
    <a href="finpension/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.finpension.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Finpension favicon">
            <span class="card-title" style="margin: 0;">Finpension</span>
        </div>
        <span class="card-desc">Import transaction history CSV reports from Finpension.</span>
    </a>
    <a href="trading212/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.trading212.com/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Trading212 favicon">
            <span class="card-title" style="margin: 0;">Trading212</span>
        </div>
        <span class="card-desc">Import CSV transaction history from Trading212.</span>
    </a>
    <a href="avanza/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://avanza.se/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Avanza">
    <span class="card-title" style="margin: 0;">Avanza</span>
    </div>
    <span class="card-desc">Import the CSV transaction history export from Avanza.</span>
    </a>
    <a href="bux/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://bux.com/it/wp-content/themes/vo-theme/assets/images/favicon/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon BUX">
    <span class="card-title" style="margin: 0;">BUX</span>
    </div>
    <span class="card-desc">Import the CSV transaction history export from BUX.</span>
    </a>
    <a href="disnat/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://disnat.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Disnat">
    <span class="card-title" style="margin: 0;">Disnat</span>
    </div>
    <span class="card-desc">Import the CSV transaction history export from Disnat.</span>
    </a>
    <a href="investengine/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.investengine.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon InvestEngine">
    <span class="card-title" style="margin: 0;">InvestEngine</span>
    </div>
    <span class="card-desc">Import the CSV transaction history export from InvestEngine.</span>
    </a>
    <a href="rabobank/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.rabobank.com/static/msp/global-sites/rds/favicons/favicon-svg.svg" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Rabobank">
    <span class="card-title" style="margin: 0;">Rabobank</span>
    </div>
    <span class="card-desc">Import the CSV transaction history export from Rabobank.</span>
    </a>
    <a href="fineco/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://finecobank.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Fineco">
    <span class="card-title" style="margin: 0;">Fineco</span>
    </div>
    <span class="card-desc">Import the "Movimenti Dossier Titoli" CSV export from Fineco.</span>
    </a>
    <a href="intesa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.intesasanpaolo.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Intesa Sanpaolo">
    <span class="card-title" style="margin: 0;">Intesa Sanpaolo</span>
    </div>
    <span class="card-desc">Import CSV/XLSX movements or patrimonio snapshot exports from Intesa Sanpaolo.</span>
    </a>
    <a href="credit_agricole/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.credit-agricole.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Crédit Agricole">
    <span class="card-title" style="margin: 0;">Crédit Agricole</span>
    </div>
    <span class="card-desc">Import account movements from Crédit Agricole — real cash, fees, taxes and coupons/dividends; optional securities export for pre-2-year history.</span>
    </a>
    <a href="traderepublic/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://traderepublic.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Trade Republic">
    <span class="card-title" style="margin: 0;">Trade Republic</span>
    </div>
    <span class="card-desc">Import the CSV transaction history export from Trade Republic.</span>
    </a>
    <a href="xtb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.xtb.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon XTB">
    <span class="card-title" style="margin: 0;">XTB</span>
    </div>
    <span class="card-desc">Import the CSV transaction history export from XTB.</span>
    </a>
    <a href="parqet/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://parqet.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Parqet">
    <span class="card-title" style="margin: 0;">Parqet</span>
    </div>
    <span class="card-desc">Import the CSV transaction history export from Parqet.</span>
    </a>
    <a href="saxo/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://home.saxo/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Saxo">
    <span class="card-title" style="margin: 0;">Saxo</span>
    </div>
    <span class="card-desc">Import the CSV transaction history export from Saxo.</span>
    </a>
    <a href="swissquote/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.swissquote.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Swissquote">
    <span class="card-title" style="margin: 0;">Swissquote</span>
    </div>
    <span class="card-desc">Import the CSV transaction history export from Swissquote.</span>
    </a>
    <a href="bitvavo/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://bitvavo.com/favicon-32x32.png?v=7ba51b544a17c10de8defa086df79917" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Bitvavo">
    <span class="card-title" style="margin: 0;">Bitvavo</span>
    </div>
    <span class="card-desc">Import the CSV transaction history export from Bitvavo (crypto).</span>
    </a>
    <a href="cryptocom/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://crypto.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Crypto.com">
    <span class="card-title" style="margin: 0;">Crypto.com</span>
    </div>
    <span class="card-desc">Import the CSV transaction history export from Crypto.com (crypto).</span>
    </a>
    <a href="relai/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://relai.app/app/uploads/2023/06/cropped-App-icon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Relai">
    <span class="card-title" style="margin: 0;">Relai</span>
    </div>
    <span class="card-desc">Import the CSV transaction history export from Relai (crypto).</span>
    </a>
    <a href="cointracking/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://cointracking.info/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon CoinTracking">
    <span class="card-title" style="margin: 0;">CoinTracking</span>
    </div>
    <span class="card-desc">Import the CSV transaction history export from CoinTracking (crypto).</span>
    </a>
    <a href="delta/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.google.com/s2/favicons?domain=delta.app&amp;sz=64" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Delta">
    <span class="card-title" style="margin: 0;">Delta</span>
    </div>
    <span class="card-desc">Import the CSV transaction history export from Delta (crypto).</span>
    </a>
    <a href="investimental/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.investimental.ro/wp-content/themes/investimental/img/favicon/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Investimental">
    <span class="card-title" style="margin: 0;">Investimental</span>
    </div>
    <span class="card-desc">Import the CSV transaction history export from Investimental.</span>
    </a>
    <a href="generic-csv/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" style="color: var(--md-accent-fg-color);"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg>
            <span class="card-title" style="margin: 0;">Generic CSV</span>
        </div>
        <span class="card-desc">Our fallback parser with manual column mapping.</span>
    </a>
    <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
      <div style="display: flex; align-items: center; gap: 0.75rem;">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
      <span class="card-title" style="margin: 0;">Request New Plugin</span>
      </div>
      <span class="card-desc">Your broker is missing? Request a new plugin or contribute code!</span>
    </a>
</div>

??? info "📊 Importer Capabilities"


    | Broker | Status | Format | Buy/Sell | Dividends | Deposits/Cash | Fees/Taxes | Notes |
    | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.interactivebrokers.com/favicon.ico" width="16" height="16" style=""><span>IB</span></span> **Interactive Brokers** | 🧪 Beta | CSV (Flex) | ✅ | ✅ | ✅ | ✅ | Best for multi-currency accounts |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.degiro.com/favicon.ico" width="16" height="16" style=""><span>DE</span></span> **Degiro** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Support for standard account statement |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.etoro.com/favicon.ico" width="16" height="16" style=""><span>ET</span></span> **eToro** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Realized gains and dividends support |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.directa.it/favicon.ico" width="16" height="16" style=""><span>DS</span></span> **Directa SIM** | ✅ Stable | CSV/XLSX | ✅ | ✅ | ✅ | ✅ | Italian broker tax statement support |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.schwab.com/favicon.ico" width="16" height="16" style=""><span>CS</span></span> **Charles Schwab** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Standard US broker activity statement |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="16" height="16" style=""><span>RE</span></span> **Revolut** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Stock and crypto transaction support |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.coinbase.com/favicon.ico" width="16" height="16" style=""><span>CO</span></span> **Coinbase** | 🧪 Beta | CSV | ✅ | ❌ | ✅ | ✅ | Crypto-only transaction reports |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="16" height="16" style=""><span>FR</span></span> **Freetrade** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Simple UK brokerage statements |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.finpension.ch/favicon.ico" width="16" height="16" style=""><span>FI</span></span> **Finpension** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Swiss pension 3a statements |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.trading212.com/favicon-32x32.png" width="16" height="16" style=""><span>TR</span></span> **Trading212** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | European trading activity CSV |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://avanza.se/favicon.ico" width="16" height="16" style=""><span>AV</span></span> **Avanza** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Built from sample exports |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://bux.com/it/wp-content/themes/vo-theme/assets/images/favicon/favicon-32x32.png" width="16" height="16" style=""><span>BU</span></span> **BUX** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Built from sample exports |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://disnat.com/favicon.ico" width="16" height="16" style=""><span>DI</span></span> **Disnat** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Built from sample exports |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.investengine.com/favicon.ico" width="16" height="16" style=""><span>IN</span></span> **InvestEngine** | 🧪 Beta | CSV | ✅ | ✅ | ❌ | ❌ | Built from sample exports |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.rabobank.com/static/msp/global-sites/rds/favicons/favicon-svg.svg" width="16" height="16" style=""><span>RA</span></span> **Rabobank** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Built from sample exports |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://finecobank.com/favicon.ico" width="16" height="16" style=""><span>FI</span></span> **Fineco** | 🧪 Beta | CSV | ✅ | ✅ | ❌ | ✅ | Both export layouts; amounts in report currency |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.intesasanpaolo.com/favicon.ico" width="16" height="16" style=""><span>IS</span></span> **Intesa Sanpaolo** | 🧪 Beta | CSV/XLSX | ❌ | ✅ | ✅ | ✅ | Movements coupons/dividends/fees/taxes; patrimonio snapshot seeds cash when present + holdings |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.credit-agricole.it/favicon.ico" width="16" height="16" style=""><span>CA</span></span> **Crédit Agricole** | ✅ Stable | CSV/XLSX | ✅ | ✅ | ✅ | ✅ | Account movements bring real cash, fees, taxes and coupons/dividends; optional securities export recovers pre-2-year history; auto cash counter-entries, maturities and succession adjustments |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://traderepublic.com/favicon.ico" width="16" height="16" style=""><span>TR</span></span> **Trade Republic** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Built from sample exports |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.xtb.com/favicon.ico" width="16" height="16" style=""><span>XT</span></span> **XTB** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Built from sample exports |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://parqet.com/favicon.ico" width="16" height="16" style=""><span>PA</span></span> **Parqet** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Built from sample exports |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://home.saxo/favicon.ico" width="16" height="16" style=""><span>SA</span></span> **Saxo** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Built from sample exports |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.swissquote.com/favicon.ico" width="16" height="16" style=""><span>SW</span></span> **Swissquote** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Built from sample exports |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://bitvavo.com/favicon-32x32.png?v=7ba51b544a17c10de8defa086df79917" width="16" height="16" style=""><span>BI</span></span> **Bitvavo** | 🧪 Beta | CSV | ✅ | ❌ | ✅ | ✅ | Crypto exchange — built from sample exports |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://crypto.com/favicon.ico" width="16" height="16" style=""><span>CC</span></span> **Crypto.com** | 🧪 Beta | CSV | ✅ | ❌ | ❌ | ❌ | Crypto exchange — built from sample exports |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://relai.app/app/uploads/2023/06/cropped-App-icon-32x32.png" width="16" height="16" style=""><span>RE</span></span> **Relai** | 🧪 Beta | CSV | ✅ | ❌ | ❌ | ✅ | Crypto exchange — built from sample exports |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://cointracking.info/favicon.ico" width="16" height="16" style=""><span>CO</span></span> **CoinTracking** | 🧪 Beta | CSV | ✅ | ❌ | ✅ | ✅ | Crypto exchange — built from sample exports |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.google.com/s2/favicons?domain=delta.app&amp;sz=64" width="16" height="16" style=""><span>DE</span></span> **Delta** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Crypto exchange — built from sample exports |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.investimental.ro/wp-content/themes/investimental/img/favicon/favicon.ico" width="16" height="16" style=""><span>IN</span></span> **Investimental** | 🧪 Beta | CSV | ✅ | ❌ | ❌ | ✅ | Built from sample exports |
    | <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" style="color: var(--md-accent-fg-color); vertical-align: middle; margin-right: 4px;"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> **Generic CSV** | ✅ Stable | CSV | ✅ | ✅ | ✅ | ✅ | Manual column mapper fallback |

---

## 🗂️ Asset Mapping {: #asset-mapping }

During the preview step, LibreFolio attempts to **auto-match** each asset name from your report to an asset already in your library.

- ✅ **Matched** — will be imported against the existing asset.
- ⚠️ **Unmatched** — select or create the target asset before importing.
- ❌ **Error** — the row could not be parsed.

---

## ♻️ Duplicate Detection {: #duplicate-detection }

BRIM checks for **duplicate transactions** within the same broker by comparing **type, date, quantity, and cash amount/currency** (with small tolerances for rounding). A matching **description** raises a hit from *possible* to *likely*; a matching **asset** — when the report row was auto-matched to your library — raises the confidence level as well. Duplicate rows are flagged in the preview — you can choose to skip or force-import them.

---

## ⛔ Before the broker opening date {: #before-opening }

If a broker has an **opening date** set, any transaction dated **before** that date is flagged in the preview as **"Before opening"** and cannot be imported (its checkbox is disabled). The opening day itself is still valid. If a row is flagged by mistake, use the **Edit broker date** action, then **re-check / refresh** so the wizard re-evaluates every row against the updated date.

---

## 🔗 Related

- 📋 **[Transaction Table](../index.md)** — View and manage imported transactions
- 🗂️ **[Files](../../files/index.md)** — Manage uploaded broker report files
- 🏦 **[Brokers](../../brokers/index.md)** — Set up your broker accounts first
