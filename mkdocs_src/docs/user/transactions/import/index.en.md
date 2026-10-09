# 📥 Import from Broker (BRIM)

**BRIM** (Broker Report Import Module) imports your transactions from the files your broker lets
you download, so you do not have to type them. To run an import, follow the
**[How to Import guide](how-to.md)**.

---

## 🏦 Supported Brokers

Pick your broker to see which file to export and what to watch out for. Importers that are still
maturing carry a label:

- 🔬 **Alpha** — new: expect rough edges and check every row;
- 🧪 **Beta** — tested with sample files: unusual cases may be missed.

Importers without a label are well tested and reliable for the formats they support.

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
    <a href="ibkr/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.interactivebrokers.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="IBKR favicon">
            <span class="card-title" style="margin: 0;">Interactive Brokers</span>
        </div>
        <span class="card-desc">🧪 Beta · CSV trade report from a Flex Query</span>
    </a>
    <a href="degiro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.degiro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Degiro favicon">
            <span class="card-title" style="margin: 0;">Degiro</span>
        </div>
        <span class="card-desc">The Account Statement CSV export</span>
    </a>
    <a href="etoro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.etoro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="eToro favicon">
            <span class="card-title" style="margin: 0;">eToro</span>
        </div>
        <span class="card-desc">🧪 Beta · Account statement CSV</span>
    </a>
    <a href="directa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.directa.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Directa SIM favicon">
            <span class="card-title" style="margin: 0;">Directa SIM</span>
        </div>
        <span class="card-desc">Transaction history, CSV or XLSX</span>
    </a>
    <a href="schwab/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.schwab.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Charles Schwab favicon">
            <span class="card-title" style="margin: 0;">Charles Schwab</span>
        </div>
        <span class="card-desc">🧪 Beta · CSV transaction history</span>
    </a>
    <a href="revolut/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Revolut favicon">
            <span class="card-title" style="margin: 0;">Revolut</span>
        </div>
        <span class="card-desc">🧪 Beta · Account statement CSV</span>
    </a>
    <a href="coinbase/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.coinbase.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Coinbase favicon">
            <span class="card-title" style="margin: 0;">Coinbase</span>
        </div>
        <span class="card-desc">🧪 Beta · CSV transaction history (crypto)</span>
    </a>
    <a href="freetrade/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Freetrade favicon">
            <span class="card-title" style="margin: 0;">Freetrade</span>
        </div>
        <span class="card-desc">🧪 Beta · CSV transaction statement</span>
    </a>
    <a href="finpension/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.finpension.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Finpension favicon">
            <span class="card-title" style="margin: 0;">Finpension</span>
        </div>
        <span class="card-desc">🧪 Beta · CSV transaction history</span>
    </a>
    <a href="trading212/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.trading212.com/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Trading212 favicon">
            <span class="card-title" style="margin: 0;">Trading212</span>
        </div>
        <span class="card-desc">🧪 Beta · CSV transaction history</span>
    </a>
    <a href="avanza/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://avanza.se/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Avanza">
    <span class="card-title" style="margin: 0;">Avanza</span>
    </div>
    <span class="card-desc">🧪 Beta · CSV transaction history</span>
    </a>
    <a href="bux/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://bux.com/it/wp-content/themes/vo-theme/assets/images/favicon/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon BUX">
    <span class="card-title" style="margin: 0;">BUX</span>
    </div>
    <span class="card-desc">🧪 Beta · CSV transaction history</span>
    </a>
    <a href="disnat/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://disnat.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Disnat">
    <span class="card-title" style="margin: 0;">Disnat</span>
    </div>
    <span class="card-desc">🧪 Beta · CSV transaction history</span>
    </a>
    <a href="investengine/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.investengine.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon InvestEngine">
    <span class="card-title" style="margin: 0;">InvestEngine</span>
    </div>
    <span class="card-desc">🧪 Beta · CSV transaction history</span>
    </a>
    <a href="rabobank/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.rabobank.com/static/msp/global-sites/rds/favicons/favicon-svg.svg" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Rabobank">
    <span class="card-title" style="margin: 0;">Rabobank</span>
    </div>
    <span class="card-desc">🧪 Beta · CSV transaction history</span>
    </a>
    <a href="fineco/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://finecobank.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Fineco">
    <span class="card-title" style="margin: 0;">Fineco</span>
    </div>
    <span class="card-desc">🧪 Beta · The "Movimenti Dossier Titoli" CSV export</span>
    </a>
    <a href="intesa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.intesasanpaolo.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Intesa Sanpaolo">
    <span class="card-title" style="margin: 0;">Intesa Sanpaolo</span>
    </div>
    <span class="card-desc">🧪 Beta · Movements or patrimonio snapshot, CSV or XLSX</span>
    </a>
    <a href="credit_agricole/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.credit-agricole.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Crédit Agricole">
    <span class="card-title" style="margin: 0;">Crédit Agricole</span>
    </div>
    <span class="card-desc">Account movements, CSV or XLSX, plus an optional securities export for history older than 2 years</span>
    </a>
    <a href="danske-bank/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://danskebank.fi/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Danske Bank">
    <span class="card-title" style="margin: 0;">Danske Bank</span>
    </div>
    <span class="card-desc">🔬 Alpha · Finnish equity savings account: the securities XLSX and the cash CSV, uploaded together as one report set</span>
    </a>
    <a href="scalable/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="../../../static/icons/brokers/scalable.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Scalable Capital">
    <span class="card-title" style="margin: 0;">Scalable Capital</span>
    </div>
    <span class="card-desc">🔬 Alpha · broker account (Scalable's CSV or the LibreFolio exporter) and overnight account (exporter), as two brokers</span>
    </a>
    <a href="traderepublic/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://traderepublic.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Trade Republic">
    <span class="card-title" style="margin: 0;">Trade Republic</span>
    </div>
    <span class="card-desc">🧪 Beta · CSV transaction history</span>
    </a>
    <a href="xtb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.xtb.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon XTB">
    <span class="card-title" style="margin: 0;">XTB</span>
    </div>
    <span class="card-desc">🧪 Beta · CSV transaction history</span>
    </a>
    <a href="parqet/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://parqet.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Parqet">
    <span class="card-title" style="margin: 0;">Parqet</span>
    </div>
    <span class="card-desc">🧪 Beta · CSV transaction history</span>
    </a>
    <a href="saxo/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://home.saxo/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Saxo">
    <span class="card-title" style="margin: 0;">Saxo</span>
    </div>
    <span class="card-desc">🧪 Beta · CSV transaction history</span>
    </a>
    <a href="swissquote/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.swissquote.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Swissquote">
    <span class="card-title" style="margin: 0;">Swissquote</span>
    </div>
    <span class="card-desc">🧪 Beta · CSV transaction history</span>
    </a>
    <a href="bitvavo/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://bitvavo.com/favicon-32x32.png?v=7ba51b544a17c10de8defa086df79917" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Bitvavo">
    <span class="card-title" style="margin: 0;">Bitvavo</span>
    </div>
    <span class="card-desc">🧪 Beta · CSV transaction history (crypto)</span>
    </a>
    <a href="cryptocom/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://crypto.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Crypto.com">
    <span class="card-title" style="margin: 0;">Crypto.com</span>
    </div>
    <span class="card-desc">🧪 Beta · CSV transaction history (crypto)</span>
    </a>
    <a href="relai/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://relai.app/app/uploads/2023/06/cropped-App-icon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Relai">
    <span class="card-title" style="margin: 0;">Relai</span>
    </div>
    <span class="card-desc">🧪 Beta · CSV transaction history (crypto)</span>
    </a>
    <a href="cointracking/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://cointracking.info/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon CoinTracking">
    <span class="card-title" style="margin: 0;">CoinTracking</span>
    </div>
    <span class="card-desc">🧪 Beta · CSV transaction history (crypto)</span>
    </a>
    <a href="delta/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.google.com/s2/favicons?domain=delta.app&amp;sz=64" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Delta">
    <span class="card-title" style="margin: 0;">Delta</span>
    </div>
    <span class="card-desc">🧪 Beta · CSV transaction history (crypto)</span>
    </a>
    <a href="investimental/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.investimental.ro/wp-content/themes/investimental/img/favicon/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Investimental">
    <span class="card-title" style="margin: 0;">Investimental</span>
    </div>
    <span class="card-desc">🧪 Beta · CSV transaction history</span>
    </a>
    <a href="generic-csv/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" style="color: var(--md-accent-fg-color);"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg>
            <span class="card-title" style="margin: 0;">Generic CSV</span>
        </div>
        <span class="card-desc">Your own CSV: columns recognised by their header names</span>
    </a>
    <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
      <div style="display: flex; align-items: center; gap: 0.75rem;">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
      <span class="card-title" style="margin: 0;">Request New Plugin</span>
      </div>
      <span class="card-desc">Your broker is missing? Request a new plugin or contribute code!</span>
    </a>
</div>

!!! tip "Accented letters, the € sign and semicolons"

    Files written by banks or re-saved with Excel on Windows are read correctly: accented letters,
    the € sign and columns separated by semicolons included (LibreFolio understands the UTF-8,
    Windows-1252 and Latin-1 encodings). Still, upload your files as downloaded whenever you can:
    some broker pages, such as [Danske Bank](danske-bank.md), ask for exactly that.

---

## 🗂️ Asset Mapping {: #asset-mapping }

Each security in your report must be matched to an asset of your library. LibreFolio does it on
its own when exactly one asset fits; for the others you pick the asset — or create it, filled in
from the report — in the **Resolve Assets** panel of the [Review](how-to.md#review) step. Until
then the row shows **✗ Unresolved** and the import waits.

---

## ♻️ Duplicate Detection {: #duplicate-detection }

LibreFolio compares every row with the transactions already saved for the same broker: same type,
date, quantity and amount, small rounding differences ignored.

- If the description matches too, the row is a **⚠ Likely dup** and arrives unticked.
- If the description differs, it is a **ℹ Possible dup** and stays ticked for you to check.

Copies between the files you import together are handled the same way, and the
[Duplicates](how-to.md#only-when-needed) step lets you choose which copy to keep. You can always tick or
untick a row yourself.

---

## ⛔ Before the broker opening date {: #before-opening }

If a broker has an **opening date**, rows dated before it cannot be imported; the opening day
itself is fine. If the date is wrong, correct it from the
[Review](how-to.md#opening-date) step and the rows are checked again.

---

## 🔗 Related

- 🧙 **[How to Import](how-to.md)** — the wizard, step by step
- 📋 **[Transactions](../index.md)** — view and manage imported transactions
- 🏦 **[Brokers](../../brokers/index.md)** — set up your broker accounts first
- 🗂️ **[Files](../../files/index.md)** — your uploaded broker reports
- 🛠️ **[BRIM Providers List](../../../developer/backend/brim/providers_list.md)** — technical notes on each importer, for developers
