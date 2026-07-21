# 📥 Import from Broker (BRIM)

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
        <span class="card-desc">Import account statement XLSX/CSV files from eToro.</span>
    </a>
    <a href="directa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.directa.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Directa SIM favicon">
            <span class="card-title" style="margin: 0;">Directa SIM</span>
        </div>
        <span class="card-desc">Import transaction history CSV files from Directa SIM.</span>
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
        <span class="card-desc">Import account statement PDF/CSV reports from Revolut.</span>
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
            <img src="https://www.trading212.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Trading212 favicon">
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
    | <img src="https://www.interactivebrokers.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Interactive Brokers** | 🧪 Beta | CSV (Flex) | ✅ | ✅ | ✅ | ✅ | Best for multi-currency accounts |
    | <img src="https://www.degiro.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Degiro** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Support for standard account statement |
    | <img src="https://www.etoro.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **eToro** | 🧪 Beta | XLSX/CSV | ✅ | ✅ | ✅ | ✅ | Realized gains and dividends support |
    | <img src="https://www.directa.it/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Directa SIM** | ✅ Stable | CSV | ✅ | ✅ | ✅ | ✅ | Italian broker tax statement support |
    | <img src="https://www.schwab.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Charles Schwab** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Standard US broker activity statement |
    | <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Revolut** | 🧪 Beta | PDF/CSV | ✅ | ✅ | ✅ | ✅ | Stock and crypto transaction support |
    | <img src="https://www.coinbase.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Coinbase** | 🧪 Beta | CSV | ✅ | ❌ | ✅ | ✅ | Crypto-only transaction reports |
    | <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Freetrade** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Simple UK brokerage statements |
    | <img src="https://www.finpension.ch/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Finpension** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Swiss pension 3a statements |
    | <img src="https://www.trading212.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Trading212** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | European trading activity CSV |
    | <img src="https://avanza.se/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Avanza** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Built from sample exports |
    | <img src="https://bux.com/it/wp-content/themes/vo-theme/assets/images/favicon/favicon-32x32.png" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **BUX** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Built from sample exports |
    | <img src="https://disnat.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Disnat** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Built from sample exports |
    | <img src="https://www.investengine.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **InvestEngine** | 🧪 Beta | CSV | ✅ | ✅ | ❌ | ❌ | Built from sample exports |
    | <img src="https://www.rabobank.com/static/msp/global-sites/rds/favicons/favicon-svg.svg" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Rabobank** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Built from sample exports |
    | <img src="https://traderepublic.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Trade Republic** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Built from sample exports |
    | <img src="https://www.xtb.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **XTB** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Built from sample exports |
    | <img src="https://parqet.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Parqet** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Built from sample exports |
    | <img src="https://home.saxo/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Saxo** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Built from sample exports |
    | <img src="https://www.swissquote.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Swissquote** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Built from sample exports |
    | <img src="https://bitvavo.com/favicon-32x32.png?v=7ba51b544a17c10de8defa086df79917" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Bitvavo** | 🧪 Beta | CSV | ✅ | ❌ | ✅ | ✅ | Crypto exchange — built from sample exports |
    | <img src="https://crypto.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Crypto.com** | 🧪 Beta | CSV | ✅ | ❌ | ❌ | ❌ | Crypto exchange — built from sample exports |
    | <img src="https://relai.app/app/uploads/2023/06/cropped-App-icon-32x32.png" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Relai** | 🧪 Beta | CSV | ✅ | ❌ | ❌ | ✅ | Crypto exchange — built from sample exports |
    | <img src="https://cointracking.info/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **CoinTracking** | 🧪 Beta | CSV | ✅ | ❌ | ✅ | ✅ | Crypto exchange — built from sample exports |
    | <img src="https://www.google.com/s2/favicons?domain=delta.app&amp;sz=64" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Delta** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Crypto exchange — built from sample exports |
    | <img src="https://www.investimental.ro/wp-content/themes/investimental/img/favicon/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Investimental** | 🧪 Beta | CSV | ✅ | ❌ | ❌ | ✅ | Built from sample exports |
    | <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" style="color: var(--md-accent-fg-color); vertical-align: middle; margin-right: 4px;"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> **Generic CSV** | ✅ Stable | CSV | ✅ | ✅ | ✅ | ✅ | Manual column mapper fallback |

---

## 🗂️ Asset Mapping {: #asset-mapping }

During the preview step, LibreFolio attempts to **auto-match** each asset name from your report to an asset already in your library.

- ✅ **Matched** — will be imported against the existing asset.
- ⚠️ **Unmatched** — select or create the target asset before importing.
- ❌ **Error** — the row could not be parsed.

---

## ♻️ Duplicate Detection {: #duplicate-detection }

BRIM checks for **duplicate transactions** based on date, type, asset, quantity, and amount. Duplicate rows are flagged in the preview — you can choose to skip or force-import them.

---

## 🔗 Related

- 📋 **[Transaction Table](../index.md)** — View and manage imported transactions
- 🗂️ **[Files](../../files/index.md)** — Manage uploaded broker report files
- 🏦 **[Brokers](../../brokers/index.md)** — Set up your broker accounts first
