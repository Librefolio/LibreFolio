# 📦 BRIM Providers List

This page lists all the broker import plugins (BRIM Providers) currently available in LibreFolio.

| Provider | Code | Formats | Status | Notes |
|:---------|:-----|:--------|:-------|:------|
| <img src="https://www.interactivebrokers.com/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> [**Interactive Brokers**](../../../user/transactions/import/ibkr.md) | `broker_ibkr` | CSV | 🧪 Beta | Parses standard IBKR activity reports. |
| <img src="https://www.degiro.com/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> [**Degiro**](../../../user/transactions/import/degiro.md) | `broker_degiro` | CSV | 🧪 Beta | Handles multi-language reports (Dutch, English, etc.). |
| <img src="https://www.etoro.com/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> [**eToro**](../../../user/transactions/import/etoro.md) | `broker_etoro` | CSV | 🧪 Beta | Supports stock and CFD transaction reports. |
| <img src="https://www.directa.it/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> [**Directa SIM**](../../../user/transactions/import/directa.md) | `broker_directa` | CSV | ✅ Stable | Italian broker Directa. |
| <img src="https://www.schwab.com/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> [**Charles Schwab**](../../../user/transactions/import/schwab.md) | `broker_schwab` | CSV | 🧪 Beta | Parses US-formatted CSV exports. |
| <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> [**Revolut**](../../../user/transactions/import/revolut.md) | `broker_revolut` | CSV | 🧪 Beta | Handles both Revolut **invest** and **crypto** exports (variant auto-detected by header). |
| <img src="https://www.coinbase.com/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> [**Coinbase**](../../../user/transactions/import/coinbase.md) | `broker_coinbase` | CSV | 🧪 Beta | For crypto transactions from Coinbase. |
| <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> [**Freetrade**](../../../user/transactions/import/freetrade.md) | `broker_freetrade` | CSV | 🧪 Beta | For UK broker Freetrade. |
| <img src="https://www.finpension.ch/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> [**Finpension**](../../../user/transactions/import/finpension.md) | `broker_finpension` | CSV | 🧪 Beta | Swiss pension platform. |
| <img src="https://www.trading212.com/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> [**Trading212**](../../../user/transactions/import/trading212.md) | `broker_trading212` | CSV | 🧪 Beta | Parses Trading212's standard CSV export. |
| <img src="https://avanza.se/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> **Avanza** | `broker_avanza` | CSV | 🧪 Beta | Swedish broker; semicolon CSV, SEK, Swedish transaction types. |
| <img src="https://home.saxo/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> **Saxo Bank** | `broker_saxo` | CSV | 🧪 Beta | Trades, dividends, cash transfers and custody fees; localized trade verbs supported. |
| <img src="https://www.swissquote.com/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> **Swissquote** | `broker_swissquote` | CSV | 🧪 Beta | Swiss broker; forex conversion legs are skipped with warnings. |
| <img src="https://traderepublic.com/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> **Trade Republic** | `broker_traderepublic` | CSV | 🧪 Beta | European neobroker; semicolon CSV, EUR. |
| <img src="https://www.xtb.com/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> **XTB** | `broker_xtb` | CSV | 🧪 Beta | Quantity/price parsed from the transaction comment field. |
| <img src="https://www.investengine.com/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> **InvestEngine** | `broker_investengine` | CSV | 🧪 Beta | UK ETF broker; GBP, combined name/ISIN column. |
| <img src="https://parqet.com/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> **Parqet** | `broker_parqet` | CSV | 🧪 Beta | Portfolio aggregator; semicolon CSV (underlying broker kept in description). |
| <img src="https://disnat.com/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> **Disnat** | `broker_disnat` | CSV | 🧪 Beta | Canadian broker (Desjardins); French headers, CAD. |
| <img src="https://bux.com/it/wp-content/themes/vo-theme/assets/images/favicon/favicon-32x32.png" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> **BUX** | `broker_bux` | CSV | 🧪 Beta | European neobroker; deposits, trades, dividends. |
| <img src="https://www.rabobank.com/static/msp/global-sites/rds/favicons/favicon-svg.svg" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> **Rabobank** | `broker_rabobank` | CSV | 🧪 Beta | Dutch bank investing; EUR, semicolon CSV. |
| <img src="https://www.investimental.ro/wp-content/themes/investimental/img/favicon/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> **Investimental** | `broker_investimental` | CSV | 🧪 Beta | Romanian broker; order-log export — imports final executed orders only. |
| <img src="https://crypto.com/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> **Crypto.com** | `broker_cryptocom` | CSV | 🧪 Beta | Crypto; buys/rewards imported, internal transfers/swaps skipped. |
| <img src="https://cointracking.info/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> **CoinTracking** | `broker_cointracking` | CSV | 🧪 Beta | Crypto tracking export; fiat trades and staking (crypto↔crypto skipped). |
| <img src="https://www.google.com/s2/favicons?domain=delta.app&amp;sz=64" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> **Delta** | `broker_delta` | CSV | 🧪 Beta | Crypto portfolio tracker; crypto↔crypto trades modeled as adjustments. |
| <img src="https://bitvavo.com/favicon-32x32.png?v=7ba51b544a17c10de8defa086df79917" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> **Bitvavo** | `broker_bitvavo` | CSV | 🧪 Beta | Dutch crypto exchange; buys/sells/deposits/withdrawals, staking as adjustment. |
| <img src="https://relai.app/app/uploads/2023/06/cropped-App-icon-32x32.png" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> **Relai** | `broker_relai` | CSV | 🧪 Beta | Bitcoin-only app; CHF fiat. |
| <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" style="width:16px;vertical-align:middle;margin-right:6px"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> [**Generic CSV**](../../../user/transactions/import/generic-csv.md) | `broker_generic_csv` | CSV | ✅ Stable | Fallback provider. Accepts any CSV matching the [Generic CSV spec](generic_csv.md). |

---

### 🧪 Status Levels

| Level | Meaning |
|-------|---------|
| 🔬 **Alpha** | Early development — may have significant bugs |
| 🧪 **Beta** | Tested with sample files — edge cases may exist |
| ✅ **Stable** | Well-tested and reliable for supported formats |

